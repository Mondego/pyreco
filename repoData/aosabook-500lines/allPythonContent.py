__FILENAME__ = example
import sys
import logging
from fleet import Ship


def key_value_state_machine(state, input_value):
    print input_value, state
    if input_value[0] == 'get':
        return state, state.get(input_value[1], None)
    elif input_value[0] == 'set':
        state[input_value[1]] = input_value[2]
        return state, input_value[2]


def main():
    logging.basicConfig(format="%(asctime)s - %(name)s - %(message)s", level=logging.WARNING)

    if sys.argv[1] == '--seed':
        sys.argv.pop(1)
        seed = {}
    else:
        seed = None

    ship = Ship(state_machine=key_value_state_machine,
                port=int(sys.argv[1]), peers=['127.0.0.1-%s' % p for p in sys.argv[2:]],
                seed=seed)
    ship.start()

    for event in ship.events():
        print event
        old = ship.invoke(('get', sys.argv[1])) or 0
        print "got", old
        ship.invoke(('set', sys.argv[1], old + 1))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = acceptor
from collections import defaultdict
from . import Ballot
from .member import Component


class Acceptor(Component):

    def __init__(self, member):
        super(Acceptor, self).__init__(member)
        self.ballot_num = Ballot(-1, -1, -1)
        self.accepted = defaultdict()  # { (b, s) : p }

    def do_PREPARE(self, scout_id, ballot_num):  # p1a
        if ballot_num > self.ballot_num:
            self.ballot_num = ballot_num

        self.send([scout_id.address], 'PROMISE',  # p1b
                  scout_id=scout_id,
                  acceptor=self.address,
                  ballot_num=self.ballot_num,
                  accepted=self.accepted)

    def do_ACCEPT(self, commander_id, ballot_num, slot, proposal):  # p2a
        if ballot_num >= self.ballot_num:
            self.ballot_num = ballot_num
            self.accepted[(ballot_num, slot)] = proposal

        self.send([commander_id.address], 'ACCEPTED',  # p2b
                  commander_id=commander_id,
                  acceptor=self.address,
                  ballot_num=self.ballot_num)

########NEW FILE########
__FILENAME__ = bootstrap
from itertools import cycle
from . import JOIN_RETRANSMIT
from .member import Component


class Bootstrap(Component):

    def __init__(self, member, peers, bootstrapped_cb):
        super(Bootstrap, self).__init__(member)
        self.peers_cycle = cycle(peers)
        self.timer = None
        self.bootstrapped_cb = bootstrapped_cb

    def start(self):
        self.join()

    def join(self):
        """Try to join the cluster"""
        self.send([next(self.peers_cycle)], 'JOIN', requester=self.address)
        self.timer = self.set_timer(JOIN_RETRANSMIT, self.join)

    def do_WELCOME(self, state, slot_num, decisions, view_id, peers, peer_history):
        self.bootstrapped_cb(state, slot_num, decisions, view_id, peers, peer_history)
        self.event('view_change', view_id=view_id, peers=peers, slot=slot_num)
        self.event('peer_history_update', peer_history=peer_history)

        if self.timer:
            self.cancel_timer(self.timer)

        self.stop()

########NEW FILE########
__FILENAME__ = client
import sys
from member import Component


class Request(Component):

    client_ids = iter(xrange(1000000, sys.maxint))
    RETRANSMIT_TIME = 0.5

    def __init__(self, member, n, callback):
        super(Request, self).__init__(member)
        self.client_id = self.client_ids.next()
        self.n = n
        self.output = None
        self.callback = callback

    def start(self):
        self.send([self.address], 'INVOKE', caller=self.address, client_id=self.client_id, input_value=self.n)
        self.invoke_timer = self.set_timer(self.RETRANSMIT_TIME, self.start)

    def do_INVOKED(self, client_id, output):
        if client_id != self.client_id:
            return
        self.logger.debug("received output %r" % (output,))
        self.cancel_timer(self.invoke_timer)
        self.callback(output)
        self.stop()

########NEW FILE########
__FILENAME__ = commander
from . import ACCEPT_RETRANSMIT
from .member import Component


class Commander(Component):

    def __init__(self, member, leader, ballot_num, slot, proposal, commander_id, peers):
        super(Commander, self).__init__(member)
        self.leader = leader
        self.ballot_num = ballot_num
        self.slot = slot
        self.proposal = proposal
        self.commander_id = commander_id
        self.accepted = set([])
        self.peers = peers
        self.quorum = len(peers) / 2 + 1
        self.timer = None

    def start(self):
        self.send(set(self.peers) - self.accepted, 'ACCEPT',  # p2a
                  commander_id=self.commander_id,
                  ballot_num=self.ballot_num,
                  slot=self.slot,
                  proposal=self.proposal)
        self.timer = self.set_timer(ACCEPT_RETRANSMIT, self.start)

    def finished(self, ballot_num, preempted):
        self.leader.commander_finished(self.commander_id, ballot_num, preempted)
        if self.timer:
            self.cancel_timer(self.timer)
        self.stop()

    def do_ACCEPTED(self, commander_id, acceptor, ballot_num):  # p2b
        if commander_id != self.commander_id:
            return
        if ballot_num == self.ballot_num:
            self.accepted.add(acceptor)
            if len(self.accepted) < self.quorum:
                return
            # make sure that this node hears about the decision, otherwise the
            # slot can get "stuck" if all of the DECISION messages get lost, or
            # if this node is not in self.peers
            self.event('decision', slot=self.slot, proposal=self.proposal)
            self.send(self.peers, 'DECISION',
                      slot=self.slot,
                      proposal=self.proposal)
            self.finished(ballot_num, False)
        else:
            self.finished(ballot_num, True)

########NEW FILE########
__FILENAME__ = deterministic_network
import copy
import functools
import time
import logging
import heapq
import random


class Node(object):
    # # TODO: consider using itertools.count() instead of iter(xrange(1000)) - 1000 seems ot be a magic number
    unique_ids = iter(xrange(1000))

    def __init__(self, network):
        self.network = network
        self.unique_id = next(self.unique_ids)
        self.address = 'N%d' % self.unique_id
        self.components = []
        self.logger = logging.getLogger(self.address)
        self.logger.info('starting')
        self.now = self.network.now

    def kill(self):
        self.logger.error('node dying')
        if self.address in self.network.nodes:
            del self.network.nodes[self.address]

    def set_timer(self, seconds, callback):
        return self.network.set_timer(seconds, self.address, callback)

    def cancel_timer(self, timer):
        self.network.cancel_timer(timer)

    def send(self, destinations, action, **kwargs):
        self.logger.debug("sending %s with args %s to %s", action, kwargs, destinations)
        self.network.send(destinations, action, **kwargs)

    def register(self, component):
        self.components.append(component)

    def unregister(self, component):
        self.components.remove(component)

    def receive(self, action, kwargs):
        action_handler_name = 'do_%s' % action

        for comp in self.components[:]:
            if not hasattr(comp, action_handler_name):
                continue
            comp.logger.debug("received %r with args %r", action, kwargs)
            fn = getattr(comp, action_handler_name)
            fn(**kwargs)


class Network(object):
    PROP_DELAY = 0.03
    PROP_JITTER = 0.02
    DROP_PROB = 0.05

    def __init__(self, seed, pause=False):
        self.nodes = {}
        self.rnd = random.Random(seed)
        self.pause = pause
        self.timers = []
        self.now = 1000.0
        self.logger = logging.getLogger('network')

    def new_node(self):
        node = Node(self)
        self.nodes[node.address] = node
        return node

    def run(self):
        while self.timers:
            next_timer = self.timers[0][0]
            if next_timer > self.now:
                if self.pause:
                    raw_input()
                else:
                    time.sleep(next_timer - self.now)
                self.now = next_timer
            when, do, address, callback = heapq.heappop(self.timers)
            if do and address in self.nodes:
                callback()

    def stop(self):
        self.timers = []

    def set_timer(self, seconds, address, callback):
        # TODO: return an obj with 'cancel'
        timer = [self.now + seconds, True, address, callback]
        heapq.heappush(self.timers, timer)
        return timer

    def cancel_timer(self, timer):
        timer[1] = False

    def _receive(self, address, action, kwargs):
        if address in self.nodes:
            self.nodes[address].receive(action, kwargs)

    def send(self, destinations, action, **kwargs):
        for dest in destinations:
            if self.rnd.uniform(0, 1.0) > self.DROP_PROB:
                delay = self.PROP_DELAY + self.rnd.uniform(-self.PROP_JITTER, self.PROP_JITTER)
                # copy the kwargs now, before the sender modifies them
                self.set_timer(delay, dest, functools.partial(self._receive, dest, action, copy.deepcopy(kwargs)))

########NEW FILE########
__FILENAME__ = heartbeat
from . import HEARTBEAT_GONE_COUNT, HEARTBEAT_INTERVAL
from .member import Component


class Heartbeat(Component):

    def __init__(self, member, clock):
        super(Heartbeat, self).__init__(member)
        self.running = False
        self.last_heard_from = {}
        self.peers = None
        self.clock = clock

    def on_view_change_event(self, slot, view_id, peers):
        self.peers = set(peers)
        for peer in self.peers:
            self.last_heard_from[peer] = self.clock()
        if not self.running:
            self.heartbeat()
            self.running = True

    def do_HEARTBEAT(self, sender):
        self.last_heard_from[sender] = self.clock()

    def heartbeat(self):
        # send heartbeats to other nodes
        self.send(self.peers, 'HEARTBEAT', sender=self.address)

        # determine if any peers are down, and notify if so; note that this
        # notification will occur repeatedly until a view change
        too_old = self.clock() - HEARTBEAT_GONE_COUNT * HEARTBEAT_INTERVAL
        active_peers = set(p for p in self.last_heard_from if self.last_heard_from[p] >= too_old)
        if active_peers != self.peers:
            self.event('peers_down', down=self.peers - active_peers)

        self.set_timer(HEARTBEAT_INTERVAL, self.heartbeat)

########NEW FILE########
__FILENAME__ = leader
from . import Ballot, ALPHA, CommanderId, view_primary
from .commander import Commander
from .member import Component
from .scout import Scout


class Leader(Component):

    def __init__(self, member, unique_id, peer_history, commander_cls=Commander, scout_cls=Scout):
        super(Leader, self).__init__(member)
        self.ballot_num = Ballot(-1, 0, unique_id)
        self.active = False
        self.proposals = {}
        self.commander_cls = commander_cls
        self.commanders = {}
        self.scout_cls = scout_cls
        self.scout = None
        self.view_id = -1
        self.peers = None
        self.peer_history = peer_history

    def on_update_peer_history_event(self, peer_history):
        self.peer_history = peer_history

    def on_view_change_event(self, slot, view_id, peers):
        self.view_id = view_id
        self.peers = peers

        # we are not an active leader in this new view
        if self.scout:
            self.scout.finished(None, None)  # eventually calls preempted
        elif self.active:
            self.preempted(None)
        elif view_primary(view_id, peers) == self.address:
            self.spawn_scout()

    def spawn_scout(self):
        assert not self.scout
        self.ballot_num = Ballot(
            self.view_id, self.ballot_num.n, self.ballot_num.leader)
        sct = self.scout = self.scout_cls(
            self.member, self, self.ballot_num, self.peers)
        sct.start()

    # TODO: rename pvals to something with semantic meaning
    def scout_finished(self, adopted, ballot_num, pvals):
        self.scout = None
        if adopted:
            # pvals is a defaultdict of proposal by (ballot num, slot); we need the proposal with
            # highest ballot number for each slot.

            # This *will* work since proposals with lower ballot numbers will be overwritten
            # by proposals with higher ballot numbers. It is guaranteed since
            # we sorting pvals items in ascending order.
            last_by_slot = {s: p for (b, s), p in sorted(pvals.items())}
            for slot_id, proposal in last_by_slot.iteritems():
                self.proposals[slot_id] = proposal

            # re-spawn commanders for any potentially outstanding proposals
            for view_slot in sorted(self.peer_history):
                slot = view_slot + ALPHA
                if slot in self.proposals:
                    self.spawn_commander(self.ballot_num, slot, self.proposals[slot])
            # note that we don't re-spawn commanders here; if there are undecided
            # proposals, the replicas will re-propose
            self.logger.info("leader becoming active")
            self.active = True
        else:
            self.preempted(ballot_num)

    def preempted(self, ballot_num):
        # ballot_num is None when we are preempted by a view change
        if ballot_num:
            self.logger.info("leader preempted by %s" % (ballot_num.leader,))
        else:
            self.logger.info("leader preempted by view change")
        self.active = False
        self.ballot_num = Ballot(
            self.view_id, (ballot_num or self.ballot_num).n + 1, self.ballot_num.leader)
        # if we're the primary for this view, re-scout immediately
        if not self.scout and view_primary(self.view_id, self.peers) == self.address:
            self.logger.info("re-scouting as the primary for this view")
            self.spawn_scout()

    def spawn_commander(self, ballot_num, slot, proposal):
        peers = self.peer_history[slot - ALPHA]
        commander_id = CommanderId(self.address, slot, self.proposals[slot])
        if commander_id in self.commanders:
            return
        cmd = self.commander_cls(
            self.member, self, ballot_num, slot, proposal, commander_id, peers)
        self.commanders[commander_id] = cmd
        cmd.start()

    def commander_finished(self, commander_id, ballot_num, preempted):
        del self.commanders[commander_id]
        if preempted:
            self.preempted(ballot_num)

    def do_PROPOSE(self, slot, proposal):
        if slot not in self.proposals:
            if self.active:
                # find the peers ALPHA slots ago, or ignore if unknown
                if slot - ALPHA not in self.peer_history:
                    self.logger.info("slot %d not in peer history %r" %
                                     (slot - ALPHA, sorted(self.peer_history)))
                    return
                self.proposals[slot] = proposal
                self.logger.info("spawning commander for slot %d" % (slot,))
                self.spawn_commander(self.ballot_num, slot, proposal)
            else:
                if not self.scout:
                    self.logger.info("got PROPOSE when not active - scouting")
                    self.spawn_scout()
                else:
                    self.logger.info("got PROPOSE while scouting; ignored")
        else:
            self.logger.info("got PROPOSE for a slot already being proposed")

########NEW FILE########
__FILENAME__ = member
import logging


class Member(object):  # TODO: rename

    def __init__(self, node):
        self.node = node
        self.address = self.node.address
        self.components = []

    def register(self, component):
        self.components.append(component)
        self.node.register(component)

    def unregister(self, component):
        self.components.remove(component)
        self.node.unregister(component)

    def event(self, message, **kwargs):
        method = 'on_' + message + '_event'
        for comp in self.components:
            if hasattr(comp, method):
                getattr(comp, method)(**kwargs)

    def start(self):
        pass


class Component(object):  # TODO: rename

    def __init__(self, member):
        self.member = member
        self.member.register(self)
        self.address = member.address
        self.logger = logging.getLogger("%s.%s" % (self.address, type(self).__name__))

    def event(self, message, **kwargs):
        self.member.event(message, **kwargs)

    def send(self, destinations, action, **kwargs):
        self.member.node.send(destinations, action, **kwargs)

    def set_timer(self, seconds, callback):
        # TODO: refactor to attach timer to this component, not address
        return self.member.node.set_timer(seconds, callback)

    def cancel_timer(self, timer):
        self.member.node.cancel_timer(timer)

    def stop(self):
        self.member.unregister(self)

########NEW FILE########
__FILENAME__ = member_replicated
from .member import Member
from .replica import Replica
from .heartbeat import Heartbeat
from .bootstrap import Bootstrap
from .acceptor import Acceptor
from .leader import Leader
from .scout import Scout
from .commander import Commander
from .seed import Seed


class ClusterMember(Member):

    def __init__(self, node, execute_fn, peers,
                 replica_cls=Replica, acceptor_cls=Acceptor, leader_cls=Leader,
                 commander_cls=Commander, scout_cls=Scout, heartbeat_cls=Heartbeat,
                 bootstrap_cls=Bootstrap):
        super(ClusterMember, self).__init__(node)
        # only start the bootstrap component initially, then hand off to the rest

        def bootstrapped(state, slot_num, decisions, view_id, peers, peer_history):
            self.replica = replica_cls(self, execute_fn)
            self.acceptor = acceptor_cls(self)
            self.leader = leader_cls(self, node.unique_id, peer_history, commander_cls=commander_cls, scout_cls=scout_cls)
            self.heartbeat = heartbeat_cls(self, node.now)
            # start up the replica, now that its information is ready
            self.replica.start(state, slot_num, decisions, view_id, peers, peer_history)

        self.bootstrap = bootstrap_cls(self, peers, bootstrapped)

    def start(self):
        self.bootstrap.start()


class ClusterSeed(Member):

    def __init__(self, node, initial_state, seed_cls=Seed):
        super(ClusterSeed, self).__init__(node)
        self.seed = seed_cls(self, initial_state)

########NEW FILE########
__FILENAME__ = member_single
import logging
from network import Node
from statemachine import sequence_generator

# Remove from final copy:
#  - logging


class Member(Node):

    def __init__(self):
        super(Member, self).__init__()

    def start(self, execute_fn, initial_value=None):
        self.execute_fn = execute_fn
        self.state = initial_value
        self.run()

    def invoke(self, input_value):
        self.state, output = self.execute_fn(self.state, input_value)
        return output

    def do_INVOKE(self, input_value, client_id, caller):
        self.send([caller], 'INVOKED', output=self.invoke(input_value))


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(name)s %(message)s", level=logging.DEBUG)
    member = Member()
    print member.address
    member.start(sequence_generator, initial_value=0)

# tests

import unittest
import threading


class FakeClient(Node):

    def do_INVOKED(self, output):
        self.output = output
        self.stop()


class MemberTests(unittest.TestCase):

    def test_invoke(self):
        member = Member()
        client = FakeClient()
        client.member = member
        memberthd = threading.Thread(target=member.start, args=(sequence_generator, 0,))
        memberthd.daemon = 1
        memberthd.start()
        client.send([member.address], 'INVOKE', input_value=5, caller=client.address)
        client.run()
        self.assertEqual(client.output, [0, 1, 2, 3, 4])

########NEW FILE########
__FILENAME__ = network
import cPickle as pickle
import uuid
import logging
import time
import heapq
import socket


NAMESPACE = uuid.UUID('7e0d7720-fa98-4270-94ff-650a2c25f3f0')


def addr_to_tuple(addr):
    parts = addr.split('-')
    return parts[0], int(parts[1])


def tuple_to_addr(addr):
    if addr[0] == '0.0.0.0':
        addr = socket.gethostbyname(socket.gethostname()), addr[1]
    return '%s-%s' % addr


class Node(object):

    def __init__(self, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', port))
        self.address = tuple_to_addr(self.sock.getsockname())
        self.timers = []
        self.logger = logging.getLogger('node.%s' % (self.address,))
        self.unique_id = uuid.uuid3(NAMESPACE, self.address).int
        self.components = []

    def run(self):
        self.logger.debug("node starting")
        self.running = True
        while self.running:
            if self.timers:
                next_timer = self.timers[0][0]
                if next_timer < time.time():
                    when, do, callback = heapq.heappop(self.timers)
                    if do:
                        callback()
                    continue
            else:
                next_timer = 0
            timeout = max(0.1, next_timer - time.time())
            self.sock.settimeout(timeout)
            try:
                msg, address = self.sock.recvfrom(102400)
            except socket.timeout:
                continue
            action, kwargs = pickle.loads(msg)
            self.logger.debug("received %r with args %r" % (action, kwargs))
            for comp in self.components[:]:
                try:
                    fn = getattr(comp, 'do_%s' % action)
                except AttributeError:
                    continue
                fn(**kwargs)

    def kill(self):
        self.running = False

    def set_timer(self, seconds, callback):
        timer = [time.time() + seconds, True, callback]
        heapq.heappush(self.timers, timer)
        return timer

    def cancel_timer(self, timer):
        timer[1] = False

    def now(self):
        return time.time()

    def send(self, destinations, action, **kwargs):
        self.logger.debug("sending %s with args %s to %s" %
                          (action, kwargs, destinations))
        pkl = pickle.dumps((action, kwargs))
        for dest in destinations:
            self.sock.sendto(pkl, addr_to_tuple(dest))

    def register(self, component):
        self.components.append(component)

    def unregister(self, component):
        self.components.remove(component)


# tests

import unittest
import threading


class TestNode(Node):
    foo_called = False
    bar_called = False

    def do_FOO(self, x, y):
        self.foo_called = True
        self.stop()


class NodeTests(unittest.TestCase):

    def test_comm(self):
        sender = Node()
        receiver = TestNode()
        rxthread = threading.Thread(target=receiver.run)
        rxthread.start()
        sender.send([receiver.address], 'FOO', x=10, y=20)
        rxthread.join()
        self.failUnless(receiver.foo_called)

    def test_timeout(self):
        node = TestNode()

        def cb():
            node.bar_called = True
            node.stop()

        node.set_timer(0.01, cb)
        node.run()
        self.failUnless(node.bar_called)

    def test_cancel_timeout(self):
        node = TestNode()

        def fail():
            raise RuntimeError("nooo")

        nonex = node.set_timer(0.01, fail)

        def cb():
            node.bar_called = True
            node.stop()

        node.set_timer(0.02, cb)
        node.cancel_timer(nonex)
        node.run()
        # this just needs to not crash

########NEW FILE########
__FILENAME__ = replica
from . import Proposal, ViewChange, CATCHUP_INTERVAL, ALPHA, view_primary
from .member import Component


class Replica(Component):

    def __init__(self, member, execute_fn):
        super(Replica, self).__init__(member)
        self.execute_fn = execute_fn
        self.proposals = {}
        self.viewchange_proposal = None

    def start(self, state, slot_num, decisions, view_id, peers, peer_history):
        self.state = state
        self.slot_num = slot_num
        # next slot num for a proposal (may lead slot_num)
        self.next_slot = slot_num
        self.decisions = decisions
        self.view_id = view_id
        self.peers = peers
        self.peers_down = set()
        self.peer_history = peer_history
        self.welcome_peers = set()

        # TODO: Can be replaced with 'assert slot_num not in self._decisions' if decision value cannot be None
        assert decisions.get(slot_num) is None

        self.catchup()

    # creating proposals

    def do_INVOKE(self, caller, client_id, input_value):
        proposal = Proposal(caller, client_id, input_value)
        if proposal not in self.proposals.viewvalues():
            self.propose(proposal)
        else:
            # It's the only drawback of using dict instead of defaultlist
            slot = next(s for s, p in self._proposals.iteritems() if p == proposal)
            self.logger.info("proposal %s already proposed in slot %d", proposal, slot)

    def do_JOIN(self, requester):
        if requester not in self.peers:
            viewchange = ViewChange(self.view_id + 1,
                                    tuple(sorted(set(self.peers) | set([requester]))))
            self.propose(Proposal(None, None, viewchange))

    # injecting proposals

    def propose(self, proposal, slot=None):
        if not slot:
            slot = self.next_slot
            self.next_slot += 1
        self.proposals[slot] = proposal
        # find a leader we think is working, deterministically
        leaders = [view_primary(self.view_id, self.peers)] + \
            list(self.peers)
        leader = (l for l in leaders if l not in self.peers_down).next()
        self.logger.info("proposing %s at slot %d to leader %s" %
                         (proposal, slot, leader))
        self.send([leader], 'PROPOSE', slot=slot, proposal=proposal)

    def catchup(self):
        """Try to catch up on un-decided slots"""
        if self.slot_num != self.next_slot:
            self.logger.debug("catching up on %d .. %d" % (self.slot_num, self.next_slot-1))
        for slot in xrange(self.slot_num, self.next_slot):
            # ask peers for information regardless
            self.send(self.peers, 'CATCHUP', slot=slot, sender=self.address)
            # TODO: Can be replaced with 'if slot in self._proposals and slot not in self._decisions'
            # TODO: if proposal value cannot be None
            if self.proposals.get(slot) and not self.decisions.get(slot):
                # resend a proposal we initiated
                self.propose(self.proposals[slot], slot)
            else:
                # make an empty proposal in case nothing has been decided
                self.propose(Proposal(None, None, None), slot)
        self.set_timer(CATCHUP_INTERVAL, self.catchup)

    # view changes

    def on_view_change_event(self, slot, view_id, peers):
        self.peers = peers
        self.peers_down = set()

    def on_peers_down_event(self, down):
        self.peers_down = down
        if not self.peers_down:
            return
        if self.viewchange_proposal and self.viewchange_proposal not in self.decisions.viewvalues():
            return  # we're still working on a viewchange that hasn't been decided
        new_peers = tuple(sorted(set(self.peers) - set(down)))
        if len(new_peers) < 3:
            self.logger.info("lost peer(s) %s; need at least three peers" % (down,))
            return
        self.logger.info("lost peer(s) %s; proposing new view" % (down,))
        self.viewchange_proposal = Proposal(
                None, None,
                ViewChange(self.view_id + 1, tuple(sorted(set(self.peers) - set(down)))))
        self.propose(self.viewchange_proposal)

    # handling decided proposals

    def do_DECISION(self, slot, proposal):
        # TODO: Can be replaced with 'if slot in self._decisions' if decision value cannot be None
        if self.decisions.get(slot) is not None:
            assert self.decisions[slot] == proposal, \
                "slot %d already decided: %r!" % (
                    slot, self.decisions[slot])
            return
        self.decisions[slot] = proposal
        self.next_slot = max(self.next_slot, slot + 1)

        # execute any pending, decided proposals, eliminating duplicates
        while True:
            commit_proposal = self.decisions.get(self._slot_num)
            if not commit_proposal:
                break  # not decided yet
            commit_slot, self.slot_num = self.slot_num, self.slot_num + 1

            # update the view history *before* committing, so the WELCOME message contains
            # an appropriate history
            self.peer_history[commit_slot] = self.peers
            if commit_slot - ALPHA in self.peer_history:
                del self.peer_history[commit_slot - ALPHA]
            exp_peer_history = list(range(commit_slot - ALPHA + 1, commit_slot + 1))
            assert list(sorted(self.peer_history)) == exp_peer_history, \
                    "bad peer history %s, exp %s" % (self.peer_history, exp_peer_history)
            self.event('update_peer_history', peer_history=self.peer_history)

            self.commit(commit_slot, commit_proposal)

            # re-propose any of our proposals which have lost in their slot
            our_proposal = self.proposals.get(commit_slot)
            if our_proposal is not None and our_proposal != commit_proposal:
                # TODO: filter out unnecessary proposals - no-ops and outdated
                # view changes (proposal.input.view_id <= self.view_id)
                self.propose(our_proposal)
    on_decision_event = do_DECISION

    def commit(self, slot, proposal):
        """Actually commit a proposal that is decided and in sequence"""
        decided_proposals = [p for s, p in self.decisions.iteritems() if s < slot]
        if proposal in decided_proposals:
            self.logger.info("not committing duplicate proposal %r at slot %d", proposal, slot)
            return  # duplicate

        self.logger.info("committing %r at slot %d" % (proposal, slot))
        self.event('commit', slot=slot, proposal=proposal)

        if isinstance(proposal.input, ViewChange):
            self.commit_viewchange(slot, proposal.input)
        elif proposal.caller is not None:
            # perform a client operation
            self.state, output = self.execute_fn(self.state, proposal.input)
            self.send([proposal.caller], 'INVOKED',
                      client_id=proposal.client_id, output=output)

    def send_welcome(self):
        if self.welcome_peers:
            self.send(list(self.welcome_peers), 'WELCOME',
                      state=self.state,
                      slot_num=self.slot_num,
                      decisions=self.decisions,
                      view_id=self.view_id,
                      peers=self.peers,
                      peer_history=self.peer_history)
            self.welcome_peers = set()

    def commit_viewchange(self, slot, viewchange):
        if viewchange.view_id == self.view_id + 1:
            self.logger.info("entering view %d with peers %s" % (viewchange.view_id, viewchange.peers))
            self.view_id = viewchange.view_id

            # now make sure that next_slot is at least slot + ALPHA, so that we don't
            # try to make any new proposals depending on the old view.  The catchup()
            # method will take care of proposing these later.
            self.next_slot = max(slot + ALPHA, self.next_slot)

            # WELCOMEs need to be based on a quiescent state of the replica,
            # not in the middle of a decision-commiting loop, so defer this
            # until the next timer interval.
            self.welcome_peers |= set(viewchange.peers) - set(self.peers)
            self.set_timer(0, self.send_welcome)

            if self.address not in viewchange.peers:
                self.stop()
                return
            self.event('view_change', slot=slot, view_id=viewchange.view_id, peers=viewchange.peers)
        else:
            self.logger.info(
                "ignored out-of-sequence view change operation")

    def do_CATCHUP(self, slot, sender):
        # if we have a decision for this proposal, spread the knowledge
        # TODO: Can be replaced with 'if slot in self._decisions' if decision value cannot be None
        if self.decisions.get(slot):
            self.send([sender], 'DECISION',
                      slot=slot, proposal=self.decisions[slot])

########NEW FILE########
__FILENAME__ = scout
from collections import defaultdict
from . import ScoutId, PREPARE_RETRANSMIT
from .member import Component


class Scout(Component):
    def __init__(self, member, leader, ballot_num, peers):
        super(Scout, self).__init__(member)
        self.leader = leader
        self.scout_id = ScoutId(self.address, ballot_num)
        self.ballot_num = ballot_num
        self.pvals = defaultdict()
        self.accepted = set([])
        self.peers = peers
        self.quorum = len(peers) / 2 + 1
        self.retransmit_timer = None

    def start(self):
        self.logger.info("scout starting")
        self.send_prepare()

    def send_prepare(self):
        self.send(self.peers, 'PREPARE',  # p1a
                  scout_id=self.scout_id,
                  ballot_num=self.ballot_num)
        self.retransmit_timer = self.set_timer(PREPARE_RETRANSMIT, self.send_prepare)

    def finished(self, adopted, ballot_num):
        self.cancel_timer(self.retransmit_timer)
        self.logger.info(
            "finished - adopted" if adopted else "finished - preempted")
        self.leader.scout_finished(adopted, ballot_num, self.pvals)
        if self.retransmit_timer:
            self.cancel_timer(self.retransmit_timer)
        self.stop()

    def do_PROMISE(self, scout_id, acceptor, ballot_num, accepted):  # p1b
        if scout_id != self.scout_id:
            return
        if ballot_num == self.ballot_num:
            self.logger.info("got matching promise; need %d" % self.quorum)
            self.pvals.update(accepted)
            self.accepted.add(acceptor)
            if len(self.accepted) >= self.quorum:
                # We're adopted; note that this does *not* mean that no other leader is active.
                # Any such conflicts will be handled by the commanders.
                self.finished(True, ballot_num)
        else:
            # ballot_num > self.ballot_num; responses to other scouts don't
            # result in a call to this method
            self.finished(False, ballot_num)


########NEW FILE########
__FILENAME__ = seed
from . import ALPHA, JOIN_RETRANSMIT
from .member import Component


class Seed(Component):
    """A component which simply provides an initial state and view.  It waits
    until it has heard JOIN requests from enough nodes to form a cluster, then
    WELCOMEs them all to the same view with the given initial state."""

    def __init__(self, member, initial_state):
        super(Seed, self).__init__(member)
        self.initial_state = initial_state
        self.peers = set([])
        self.exit_timer = None

    def do_JOIN(self, requester):
        # three is the minimum membership for a working cluster, so don't
        # respond until then, but don't expand the peers list beyond 3
        if len(self.peers) < 3:
            self.peers.add(requester)
            if len(self.peers) < 3:
                return

        # otherwise, we have a cluster, but don't welcome any nodes not
        # part of that cluster (the cluster can do that itself)
        if requester not in self.peers:
            return

        peer_history = dict((sl, self.peers) for sl in range(0, ALPHA))
        self.send(self.peers, 'WELCOME',
                  state=self.initial_state,
                  slot_num=ALPHA,
                  decisions={},
                  view_id=0,
                  peers=list(self.peers),
                  peer_history=peer_history.copy())

        # stick around for long enough that we don't hear any new JOINs from
        # the newly formed cluster
        if self.exit_timer:
            self.cancel_timer(self.exit_timer)
        self.exit_timer = self.set_timer(JOIN_RETRANSMIT * 2, self.stop)

########NEW FILE########
__FILENAME__ = ship
import Queue
import threading
from . import client
from . import member
from . import member_replicated
from . import network


class Listener(member.Component):

    def __init__(self, member, event_queue):
        super(Listener, self).__init__(member)
        self.event_queue = event_queue

    def on_view_change_event(self, slot, view_id, peers):
        self.event_queue.put(("membership_change", peers))


class Ship(object):

    def __init__(self, state_machine, port=10001, peers=None, seed=None):
        peers = peers or ['255.255.255.255-%d' % port]
        self.node = network.Node(port)
        if seed is not None:
            self.cluster_member = member_replicated.ClusterSeed(
                self.node, seed)
        else:
            self.cluster_member = member_replicated.ClusterMember(
                self.node, state_machine, peers=peers)
        self.event_queue = Queue.Queue()
        self.current_request = None
        self.listener = Listener(self.cluster_member, self.event_queue)

    def start(self):
        def run():
            self.cluster_member.start()
            self.node.run()

        self.thread = threading.Thread(target=run)
        self.thread.setDaemon(1)
        self.thread.start()

    def invoke(self, input_value):
        assert self.current_request is None
        q = Queue.Queue()

        def done(output):
            self.current_request = None
            q.put(output)
        self.current_request = client.Request(self.cluster_member, input_value, done)
        self.current_request.start()
        return q.get()

    def events(self):
        while True:
            evt = self.event_queue.get()
            yield evt

########NEW FILE########
__FILENAME__ = fake_network
class FakeNode(object):

    def __init__(self):
        self.unique_id = 999
        self.address = 'F999'
        self.component = None
        self.timers = []
        self.sent = []

    def register(self, component):
        assert not self.component
        self.component = component

    def set_timer(self, seconds, callback):
        self.timers.append([seconds, callback, True])
        return self.timers[-1]

    def cancel_timer(self, timer):
        timer[2] = False

    def send(self, destinations, action, **kwargs):
        self.sent.append((destinations, action, kwargs))

    def fake_message(self, action, **kwargs):
        fn = getattr(self.component, 'do_%s' % action)
        fn(**kwargs)

########NEW FILE########
__FILENAME__ = test_acceptor
from .. import acceptor
from .. import Ballot, ScoutId, CommanderId, Proposal
from . import utils


class Tests(utils.ComponentTestCase):

    def setUp(self):
        super(Tests, self).setUp()
        self.ac = acceptor.Acceptor(self.member)

    def assertState(self, ballot_num, accepted):
        self.assertEqual(self.ac.ballot_num, ballot_num)
        self.assertEqual(self.ac.accepted, accepted)

    def test_prepare_new_ballot(self):
        proposal = Proposal('cli', 123, 'INC')
        self.ac.accepted = {(Ballot(7, 19, 19), 33): proposal}
        self.ac.ballot_num = Ballot(7, 10, 10)
        self.node.fake_message('PREPARE',
                               scout_id=ScoutId(address='SC', ballot_num=Ballot(7, 19, 19)),
                               # newer than the acceptor's ballot_num
                               ballot_num=Ballot(7, 19, 19))
        self.assertMessage(['SC'], 'PROMISE',
                           scout_id=ScoutId(address='SC', ballot_num=Ballot(7, 19, 19)),
                           acceptor='F999',
                           # replies with updated ballot_num
                           ballot_num=Ballot(7, 19, 19),
                           # including accepted ballots
                           accepted={(Ballot(7, 19, 19), 33): proposal})
        self.assertState(Ballot(7, 19, 19), {(Ballot(7, 19, 19), 33): proposal})

    def test_prepare_old_ballot(self):
        self.ac.ballot_num = Ballot(7, 10, 10)
        self.node.fake_message('PREPARE',
                               scout_id=ScoutId(address='SC', ballot_num=Ballot(7, 5, 10)),
                               # older than the acceptor's ballot_num
                               ballot_num=Ballot(7, 5, 10))
        self.assertMessage(['SC'], 'PROMISE',
                           scout_id=ScoutId(address='SC', ballot_num=Ballot(7, 5, 10)),
                           acceptor='F999',
                           # replies with newer ballot_num
                           ballot_num=Ballot(7, 10, 10),
                           accepted={})
        self.assertState(Ballot(7, 10, 10), {})

    def test_accept_new_ballot(self):
        proposal = Proposal('cli', 123, 'INC')
        cmd_id = CommanderId(address='CMD', slot=33, proposal=proposal)
        self.ac.ballot_num = Ballot(7, 10, 10)
        self.node.fake_message('ACCEPT',
                               commander_id=cmd_id,
                               ballot_num=Ballot(7, 19, 19),
                               slot=33,
                               proposal=proposal)
        self.assertMessage(['CMD'], 'ACCEPTED',
                           commander_id=cmd_id,
                           acceptor='F999',
                           # replies with updated ballot_num
                           ballot_num=Ballot(7, 19, 19))
        # and state records acceptance of proposal
        self.assertState(Ballot(7, 19, 19), {(Ballot(7, 19, 19), 33): proposal})

    def test_accept_old_ballot(self):
        proposal = Proposal('cli', 123, 'INC')
        cmd_id = CommanderId(address='CMD', slot=33, proposal=proposal)
        self.ac.ballot_num = Ballot(7, 10, 10)
        self.node.fake_message('ACCEPT',
                               commander_id=cmd_id,
                               ballot_num=Ballot(7, 5, 5),
                               slot=33,
                               proposal=proposal)
        self.assertMessage(['CMD'], 'ACCEPTED',
                           commander_id=cmd_id,
                           acceptor='F999',
                           # replies with newer ballot_num
                           ballot_num=Ballot(7, 10, 10))
        # and doesn't accept the proposal
        self.assertState(Ballot(7, 10, 10), {})

########NEW FILE########
__FILENAME__ = utils
from . import fake_network
from .. import member
import unittest


class ComponentTestCase(unittest.TestCase):

    def setUp(self):
        self.node = fake_network.FakeNode()
        self.member = member.Member(self.node)

    def tearDown(self):
        if self.node.sent:
            self.fail("extra messages from node: %r" % (self.node.sent,))

    def assertMessage(self, destinations, action, **kwargs):
        got = self.node.sent.pop(0)
        self.assertEqual((sorted(got[0]), got[1], got[2]), (sorted(destinations), action, kwargs))

########NEW FILE########
__FILENAME__ = crawl
#!/usr/bin/env python3.4

"""A simple web crawler -- main driver program."""

# TODO:
# - Add arguments to specify TLS settings (e.g. cert/key files).

import argparse
import asyncio
import logging
import sys

import crawling
import reporting


ARGS = argparse.ArgumentParser(description="Web crawler")
ARGS.add_argument(
    '--iocp', action='store_true', dest='iocp',
    default=False, help='Use IOCP event loop (Windows only)')
ARGS.add_argument(
    '--select', action='store_true', dest='select',
    default=False, help='Use Select event loop instead of default')
ARGS.add_argument(
    'roots', nargs='*',
    default=[], help='Root URL (may be repeated)')
ARGS.add_argument(
    '--max_redirect', action='store', type=int, metavar='N',
    default=10, help='Limit redirection chains (for 301, 302 etc.)')
ARGS.add_argument(
    '--max_tries', action='store', type=int, metavar='N',
    default=4, help='Limit retries on network errors')
ARGS.add_argument(
    '--max_tasks', action='store', type=int, metavar='N',
    default=100, help='Limit concurrent connections')
ARGS.add_argument(
    '--max_pool', action='store', type=int, metavar='N',
    default=100, help='Limit connection pool size')
ARGS.add_argument(
    '--exclude', action='store', metavar='REGEX',
    help='Exclude matching URLs')
ARGS.add_argument(
    '--strict', action='store_true',
    default=True, help='Strict host matching (default)')
ARGS.add_argument(
    '--lenient', action='store_false', dest='strict',
    default=False, help='Lenient host matching')
ARGS.add_argument(
    '-v', '--verbose', action='count', dest='level',
    default=1, help='Verbose logging (repeat for more verbose)')
ARGS.add_argument(
    '-q', '--quiet', action='store_const', const=0, dest='level',
    default=1, help='Quiet logging (opposite of --verbose)')


def fix_url(url):
    """Prefix a schema-less URL with http://."""
    if '://' not in url:
        url = 'http://' + url
    return url


def main():
    """Main program.

    Parse arguments, set up event loop, run crawler, print report.
    """
    args = ARGS.parse_args()
    if not args.roots:
        print('Use --help for command line help')
        return

    levels = [logging.ERROR, logging.WARN, logging.INFO, logging.DEBUG]
    logging.basicConfig(level=levels[min(args.level, len(levels)-1)])

    if args.iocp:
        from asyncio.windows_events import ProactorEventLoop
        loop = ProactorEventLoop()
        asyncio.set_event_loop(loop)
    elif args.select:
        loop = asyncio.SelectorEventLoop()
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.get_event_loop()

    roots = {fix_url(root) for root in args.roots}

    crawler = crawling.Crawler(roots,
                               exclude=args.exclude,
                               strict=args.strict,
                               max_redirect=args.max_redirect,
                               max_tries=args.max_tries,
                               max_tasks=args.max_tasks,
                               max_pool=args.max_pool,
                               )
    try:
        loop.run_until_complete(crawler.crawl())  # Crawler gonna crawl.
    except KeyboardInterrupt:
        sys.stderr.flush()
        print('\nInterrupted\n')
    finally:
        reporting.report(crawler)
        crawler.close()
        loop.close()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = crawling
"""A simple web crawler -- classes implementing crawling logic."""

import asyncio
import cgi
from http.client import BadStatusLine
import logging
import re
import time
import urllib.parse

logger = logging.getLogger(__name__)


def unescape(s):
    """The inverse of cgi.escape()."""
    s = s.replace('&quot;', '"').replace('&gt;', '>').replace('&lt;', '<')
    return s.replace('&amp;', '&')  # Must be last.


class ConnectionPool:
    """A connection pool.

    To open a connection, use reserve().  To recycle it, use unreserve().

    The pool is mostly just a mapping from (host, port, ssl) tuples to
    lists of Connections.  The currently active connections are *not*
    in the data structure; get_connection() takes the connection out,
    and recycle_connection() puts it back in.  To recycle a
    connection, call conn.close(recycle=True).

    There are limits to both the overall pool and the per-key pool.
    """

    def __init__(self, max_pool=10, max_tasks=5):
        self.max_pool = max_pool  # Overall limit.
        self.max_tasks = max_tasks  # Per-key limit.
        self.loop = asyncio.get_event_loop()
        self.connections = {}  # {(host, port, ssl): [Connection, ...], ...}
        self.queue = []  # [Connection, ...]

    def close(self):
        """Close all connections available for reuse."""
        for conns in self.connections.values():
            for conn in conns:
                conn.close()
        self.connections.clear()
        self.queue.clear()

    @asyncio.coroutine
    def get_connection(self, host, port, ssl):
        """Create or reuse a connection."""
        port = port or (443 if ssl else 80)
        try:
            ipaddrs = yield from self.loop.getaddrinfo(host, port)
        except Exception as exc:
            logger.error('Exception %r for (%r, %r)', exc, host, port)
            raise
        logger.warn('* %s resolves to %s',
                    host, ', '.join(ip[4][0] for ip in ipaddrs))

        # Look for a reusable connection.
        for _, _, _, _, (h, p, *_) in ipaddrs:
            key = h, p, ssl
            conn = None
            conns = self.connections.get(key)
            while conns:
                conn = conns.pop(0)
                self.queue.remove(conn)
                if not conns:
                    del self.connections[key]
                if conn.stale():
                    logger.warn('closing stale connection %r', key)
                    conn.close()  # Just in case.
                else:
                    logger.warn('* Reusing pooled connection %r', key)
                    return conn

        # Create a new connection.
        conn = Connection(self, host, port, ssl)
        yield from conn.connect()
        logger.warn('* New connection %r', conn.key)
        return conn

    def recycle_connection(self, conn):
        """Make a connection available for reuse.

        This also prunes the pool if it exceeds the size limits.
        """
        conns = self.connections.setdefault(conn.key, [])
        conns.append(conn)
        self.queue.append(conn)

        if len(conns) > self.max_tasks:
            victims = conns  # Prune one connection for this key.
        elif len(self.queue) > self.max_pool:
            victims = self.queue  # Prune one connection for any key.
        else:
            return

        for victim in victims:
            if victim.stale():  # Prefer pruning the oldest stale connection.
                logger.warn('closing stale connection %r', victim.key)
                break
        else:
            victim = victims[0]
            logger.warn('closing oldest connection %r', victim.key)

        conns = self.connections[victim.key]
        conns.remove(victim)
        if not conns:
            del self.connections[victim.key]
        self.queue.remove(victim)
        victim.close()


class Connection:
    """A connection that can be recycled to the pool."""

    def __init__(self, pool, host, port, ssl):
        self.pool = pool
        self.host = host
        self.port = port
        self.ssl = ssl
        self.reader = None
        self.writer = None
        self.key = None

    def stale(self):
        return self.reader is None or self.reader.at_eof()

    @asyncio.coroutine
    def connect(self):
        self.reader, self.writer = yield from asyncio.open_connection(
            self.host, self.port, ssl=self.ssl)
        peername = self.writer.get_extra_info('peername')
        if peername:
            self.host, self.port = peername[:2]
        else:
            logger.warn('NO PEERNAME %r %r %r', self.host, self.port, self.ssl)
        self.key = self.host, self.port, self.ssl

    def close(self, recycle=False):
        if recycle and not self.stale():
            self.pool.recycle_connection(self)
        else:
            self.writer.close()
            self.pool = self.reader = self.writer = None


@asyncio.coroutine
def make_request(url, pool, *, method='GET', headers=None, version='1.1'):
    """Start an HTTP request.  Return a Connection."""
    parts = urllib.parse.urlparse(url)
    assert parts.scheme in ('http', 'https'), repr(url)
    ssl = parts.scheme == 'https'
    port = parts.port or (443 if ssl else 80)
    path = parts.path or '/'
    path = '%s?%s' % (path, parts.query) if parts.query else path

    logger.warn('* Connecting to %s:%s using %s for %s',
                parts.hostname, port, 'ssl' if ssl else 'tcp', url)
    conn = yield from pool.get_connection(parts.hostname, port, ssl)

    headers = dict(headers) if headers else {}  # Must use Cap-Words.
    headers.setdefault('User-Agent', 'asyncio-example-crawl/0.0')
    headers.setdefault('Host', parts.netloc)
    headers.setdefault('Accept', '*/*')
    lines = ['%s %s HTTP/%s' % (method, path, version)]
    lines.extend('%s: %s' % kv for kv in headers.items())
    for line in lines + ['']:
        logger.info('> %s', line)
    # TODO: close conn if this fails.
    conn.writer.write('\r\n'.join(lines + ['', '']).encode('latin-1'))

    return conn  # Caller must send body if desired, then call read_response().


@asyncio.coroutine
def read_response(conn):
    """Read an HTTP response from a connection."""

    @asyncio.coroutine
    def getline():
        line = (yield from conn.reader.readline()).decode('latin-1').rstrip()
        logger.info('< %s', line)
        return line

    status_line = yield from getline()
    status_parts = status_line.split(None, 2)
    if len(status_parts) != 3 or not status_parts[1].isdigit():
        logger.error('bad status_line %r', status_line)
        raise BadStatusLine(status_line)
    http_version, status, reason = status_parts
    status = int(status)

    headers = {}
    while True:
        header_line = yield from getline()
        if not header_line:
            break
        key, value = header_line.split(':', 1)
        # TODO: Continuation lines; multiple header lines per key..
        headers[key.lower()] = value.lstrip()

    if 'content-length' in headers:
        nbytes = int(headers['content-length'])
        output = asyncio.StreamReader()
        asyncio.async(length_handler(nbytes, conn.reader, output))
    elif headers.get('transfer-encoding') == 'chunked':
        output = asyncio.StreamReader()
        asyncio.async(chunked_handler(conn.reader, output))
    else:
        output = conn.reader

    return http_version[5:], status, reason, headers, output


@asyncio.coroutine
def length_handler(nbytes, input, output):
    """Async handler for reading a body given a Content-Length header."""
    while nbytes > 0:
        buffer = yield from input.read(min(nbytes, 256*1024))
        if not buffer:
            logger.error('premature end for content-length')
            output.set_exception(EOFError())
            return
        output.feed_data(buffer)
        nbytes -= len(buffer)
    output.feed_eof()


@asyncio.coroutine
def chunked_handler(input, output):
    """Async handler for reading a body using Transfer-Encoding: chunked."""
    logger.info('parsing chunked response')
    nblocks = 0
    nbytes = 0
    while True:
        size_header = yield from input.readline()
        if not size_header:
            logger.error('premature end of chunked response')
            output.set_exception(EOFError())
            return
        logger.debug('size_header = %r', size_header)
        parts = size_header.split(b';')
        size = int(parts[0], 16)
        nblocks += 1
        nbytes += size
        if size:
            logger.debug('reading chunk of %r bytes', size)
            block = yield from input.readexactly(size)
            assert len(block) == size, (len(block), size)
            output.feed_data(block)
        crlf = yield from input.readline()
        assert crlf == b'\r\n', repr(crlf)
        if not size:
            break
    logger.warn('chunked response had %r bytes in %r blocks', nbytes, nblocks)
    output.feed_eof()


class Fetcher:
    """Logic and state for one URL.

    When found in crawler.busy, this represents a URL to be fetched or
    in the process of being fetched; when found in crawler.done, this
    holds the results from fetching it.

    This is usually associated with a task.  This references the
    crawler for the connection pool and to add more URLs to its todo
    list.

    Call fetch() to do the fetching; results are in instance variables.
    """

    def __init__(self, url, crawler, max_redirect=10, max_tries=4):
        self.url = url
        self.crawler = crawler
        # We don't loop resolving redirects here -- we just use this
        # to decide whether to add the redirect URL to crawler.todo.
        self.max_redirect = max_redirect
        # But we do loop to retry on errors a few times.
        self.max_tries = max_tries
        # Everything we collect from the response goes here.
        self.task = None
        self.exceptions = []
        self.tries = 0
        self.conn = None
        self.status = None
        self.headers = None
        self.body = None
        self.next_url = None
        self.ctype = None
        self.pdict = None
        self.encoding = None
        self.urls = None
        self.new_urls = None

    @asyncio.coroutine
    def fetch(self):
        """Attempt to fetch the contents of the URL.

        If successful, and the data is HTML, extract further links and
        add them to the crawler.  Redirects are also added back there.
        """
        while self.tries < self.max_tries:
            self.tries += 1
            conn = None
            try:
                conn = yield from make_request(self.url, self.crawler.pool)
                _, status, _, headers, output = yield from read_response(conn)
                self.status, self.headers = status, headers
                self.body = yield from output.read()
                h_conn = headers.get('connection', '').lower()
                if h_conn != 'close':
                    conn.close(recycle=True)
                    conn = None
                if self.tries > 1:
                    logger.warn('try %r for %r success', self.tries, self.url)
                break
            except (BadStatusLine, OSError) as exc:
                self.exceptions.append(exc)
                logger.warn('try %r for %r raised %r',
                            self.tries, self.url, exc)
            finally:
                if conn is not None:
                    conn.close()
        else:
            # We never broke out of the while loop, i.e. all tries failed.
            logger.error('no success for %r in %r tries',
                         self.url, self.max_tries)
            return
        if status in (300, 301, 302, 303, 307) and headers.get('location'):
            next_url = headers['location']
            self.next_url = urllib.parse.urljoin(self.url, next_url)
            if self.max_redirect > 0:
                logger.warn('redirect to %r from %r', self.next_url, self.url)
                self.crawler.add_url(self.next_url, self.max_redirect-1)
            else:
                logger.error('redirect limit reached for %r from %r',
                             self.next_url, self.url)
        else:
            if status == 200:
                self.ctype = headers.get('content-type')
                self.pdict = {}
                if self.ctype:
                    self.ctype, self.pdict = cgi.parse_header(self.ctype)
                self.encoding = self.pdict.get('charset', 'utf-8')
                if self.ctype == 'text/html':
                    body = self.body.decode(self.encoding, 'replace')
                    # Replace href with (?:href|src) to follow image links.
                    self.urls = set(re.findall(r'(?i)href=["\']?([^\s"\'<>]+)',
                                               body))
                    if self.urls:
                        logger.warn('got %r distinct urls from %r',
                                    len(self.urls), self.url)
                    self.new_urls = set()
                    for url in self.urls:
                        url = unescape(url)
                        url = urllib.parse.urljoin(self.url, url)
                        url, frag = urllib.parse.urldefrag(url)
                        if self.crawler.add_url(url):
                            self.new_urls.add(url)


class Crawler:
    """Crawl a set of URLs.

    This manages three disjoint sets of URLs (todo, busy, done).  The
    data structures actually store dicts -- the values in todo give
    the redirect limit, while the values in busy and done are Fetcher
    instances.
    """
    def __init__(self, roots,
                 exclude=None, strict=True,  # What to crawl.
                 max_redirect=10, max_tries=4,  # Per-url limits.
                 max_tasks=10, max_pool=10,  # Global limits.
                 ):
        self.roots = roots
        self.exclude = exclude
        self.strict = strict
        self.max_redirect = max_redirect
        self.max_tries = max_tries
        self.max_tasks = max_tasks
        self.max_pool = max_pool
        self.todo = {}
        self.busy = {}
        self.done = {}
        self.pool = ConnectionPool(max_pool, max_tasks)
        self.root_domains = set()
        for root in roots:
            parts = urllib.parse.urlparse(root)
            host, port = urllib.parse.splitport(parts.netloc)
            if not host:
                continue
            if re.match(r'\A[\d\.]*\Z', host):
                self.root_domains.add(host)
            else:
                host = host.lower()
                if self.strict:
                    self.root_domains.add(host)
                else:
                    host = host.split('.')[-2:]
                    self.root_domains.add(host)
        for root in roots:
            self.add_url(root)
        self.governor = asyncio.Semaphore(max_tasks)
        self.termination = asyncio.Condition()
        self.t0 = time.time()
        self.t1 = None

    def close(self):
        """Close resources (currently only the pool)."""
        self.pool.close()

    def host_okay(self, host):
        """Check if a host should be crawled.

        A literal match (after lowercasing) is always good.  For hosts
        that don't look like IP addresses, some approximate matches
        are okay depending on the strict flag.
        """
        host = host.lower()
        if host in self.root_domains:
            return True
        if re.match(r'\A[\d\.]*\Z', host):
            return False
        if self.strict:
            return self._host_okay_strictish(host)
        else:
            return self._host_okay_lenient(host)

    def _host_okay_strictish(self, host):
        """Check if a host should be crawled, strict-ish version.

        This checks for equality modulo an initial 'www.' component.
        """
        host = host[4:] if host.startswith('www.') else 'www.' + host
        return host in self.root_domains

    def _host_okay_lenient(self, host):
        """Check if a host should be crawled, lenient version.

        This compares the last two components of the host.
        """
        host = host.split('.')[-2:]
        return host in self.root_domains

    def add_url(self, url, max_redirect=None):
        """Add a URL to the todo list if not seen before."""
        if self.exclude and re.search(self.exclude, url):
            return False
        parts = urllib.parse.urlparse(url)
        if parts.scheme not in ('http', 'https'):
            logger.info('skipping non-http scheme in %r', url)
            return False
        host, port = urllib.parse.splitport(parts.netloc)
        if not self.host_okay(host):
            logger.info('skipping non-root host in %r', url)
            return False
        if max_redirect is None:
            max_redirect = self.max_redirect
        if url in self.todo or url in self.busy or url in self.done:
            return False
        logger.warn('adding %r %r', url, max_redirect)
        self.todo[url] = max_redirect
        return True

    @asyncio.coroutine
    def crawl(self):
        """Run the crawler until all finished."""
        with (yield from self.termination):
            while self.todo or self.busy:
                if self.todo:
                    url, max_redirect = self.todo.popitem()
                    fetcher = Fetcher(url,
                                      crawler=self,
                                      max_redirect=max_redirect,
                                      max_tries=self.max_tries,
                                      )
                    self.busy[url] = fetcher
                    fetcher.task = asyncio.Task(self.fetch(fetcher))
                else:
                    yield from self.termination.wait()
        self.t1 = time.time()

    @asyncio.coroutine
    def fetch(self, fetcher):
        """Call the Fetcher's fetch(), with a limit on concurrency.

        Once this returns, move the fetcher from busy to done.
        """
        url = fetcher.url
        with (yield from self.governor):
            try:
                yield from fetcher.fetch()  # Fetcher gonna fetch.
            finally:
                # Force GC of the task, so the error is logged.
                fetcher.task = None
        with (yield from self.termination):
            self.done[url] = fetcher
            del self.busy[url]
            self.termination.notify()

########NEW FILE########
__FILENAME__ = reporting
"""Reporting subsystem for web crawler."""

import time


class Stats:
    """Record stats of various sorts."""

    def __init__(self):
        self.stats = {}

    def add(self, key, count=1):
        self.stats[key] = self.stats.get(key, 0) + count

    def report(self, file=None):
        for key, count in sorted(self.stats.items()):
            print('%10d' % count, key, file=file)


def report(crawler, file=None):
    """Print a report on all completed URLs."""
    t1 = crawler.t1 or time.time()
    dt = t1 - crawler.t0
    if dt and crawler.max_tasks:
        speed = len(crawler.done) / dt / crawler.max_tasks
    else:
        speed = 0
    stats = Stats()
    print('*** Report ***', file=file)
    try:
        show = []
        show.extend(crawler.done.items())
        show.extend(crawler.busy.items())
        show.sort()
        for url, fetcher in show:
            fetcher_report(fetcher, stats, file=file)
    except KeyboardInterrupt:
        print('\nInterrupted', file=file)
    print('Finished', len(crawler.done),
          'urls in %.3f secs' % dt,
          '(max_tasks=%d)' % crawler.max_tasks,
          '(%.3f urls/sec/task)' % speed,
          file=file)
    stats.report(file=file)
    print('Todo:', len(crawler.todo), file=file)
    print('Busy:', len(crawler.busy), file=file)
    print('Done:', len(crawler.done), file=file)
    print('Date:', time.ctime(), 'local time', file=file)


def fetcher_report(fetcher, stats, file=None):
    """Print a report on the state for this URL.

    Also update the Stats instance.
    """
    if fetcher.task is not None:
        if not fetcher.task.done():
            stats.add('pending')
            print(fetcher.url, 'pending', file=file)
            return
        elif fetcher.task.cancelled():
            stats.add('cancelled')
            print(fetcher.url, 'cancelled', file=file)
            return
        elif fetcher.task.exception():
            stats.add('exception')
            exc = fetcher.task.exception()
            stats.add('exception_' + exc.__class__.__name__)
            print(fetcher.url, exc, file=file)
            return
    if len(fetcher.exceptions) == fetcher.tries:
        stats.add('fail')
        exc = fetcher.exceptions[-1]
        stats.add('fail_' + str(exc.__class__.__name__))
        print(fetcher.url, 'error', exc, file=file)
    elif fetcher.next_url:
        stats.add('redirect')
        print(fetcher.url, fetcher.status, 'redirect', fetcher.next_url,
              file=file)
    elif fetcher.ctype == 'text/html':
        stats.add('html')
        size = len(fetcher.body or b'')
        stats.add('html_bytes', size)
        print(fetcher.url, fetcher.status,
              fetcher.ctype, fetcher.encoding,
              size,
              '%d/%d' % (len(fetcher.new_urls or ()), len(fetcher.urls or ())),
              file=file)
    else:
        size = len(fetcher.body or b'')
        if fetcher.status == 200:
            stats.add('other')
            stats.add('other_bytes', size)
        else:
            stats.add('error')
            stats.add('error_bytes', size)
            stats.add('status_%s' % fetcher.status)
        print(fetcher.url, fetcher.status,
              fetcher.ctype, fetcher.encoding,
              size,
              file=file)

########NEW FILE########
__FILENAME__ = binary_tree
import pickle


from dbdb.tree import Tree, ValueRef


class BinaryNode(object):
    @classmethod
    def from_node(cls, node, **kwargs):
        length = node.length
        if 'left_ref' in kwargs:
            length += kwargs['left_ref'].length - node.left_ref.length
        if 'right_ref' in kwargs:
            length += kwargs['right_ref'].length - node.right_ref.length

        return cls(
            left_ref=kwargs.get('left_ref', node.left_ref),
            key=kwargs.get('key', node.key),
            value_ref=kwargs.get('value_ref', node.value_ref),
            right_ref=kwargs.get('right_ref', node.right_ref),
            length=length,
        )

    def __init__(self, left_ref, key, value_ref, right_ref, length):
        self.left_ref = left_ref
        self.key = key
        self.value_ref = value_ref
        self.right_ref = right_ref
        self.length = length

    def store_refs(self, storage):
        self.value_ref.store(storage)
        self.left_ref.store(storage)
        self.right_ref.store(storage)


class BinaryNodeRef(ValueRef):
    def prepare_to_store(self, storage):
        if self._referent:
            self._referent.store_refs(storage)

    @property
    def length(self):
        if self._referent is None and self._address:
            raise RuntimeError('Asking for BinaryNodeRef length of unloaded node')
        if self._referent:
            return self._referent.length
        else:
            return 0

    @staticmethod
    def referent_to_string(referent):
        return pickle.dumps({
            'left': referent.left_ref.address,
            'key': referent.key,
            'value': referent.value_ref.address,
            'right': referent.right_ref.address,
            'length': referent.length,
        })

    @staticmethod
    def string_to_referent(string):
        d = pickle.loads(string)
        return BinaryNode(
            BinaryNodeRef(address=d['left']),
            d['key'],
            ValueRef(address=d['value']),
            BinaryNodeRef(address=d['right']),
            d['length'],
        )


class BinaryTree(Tree):
    node_ref_class = BinaryNodeRef

    def _get(self, node, key):
        while node is not None:
            if key < node.key:
                node = self._follow(node.left_ref)
            elif node.key < key:
                node = self._follow(node.right_ref)
            else:
                return self._follow(node.value_ref)
        raise KeyError

    def _insert(self, node, key, value_ref):
        if node is None:
            new_node = BinaryNode(
                self.node_ref_class(), key, value_ref, self.node_ref_class(), 1)
        elif key < node.key:
            new_node = BinaryNode.from_node(
                node,
                left_ref=self._insert(
                    self._follow(node.left_ref), key, value_ref))
        elif node.key < key:
            new_node = BinaryNode.from_node(
                node,
                right_ref=self._insert(
                    self._follow(node.right_ref), key, value_ref))
        else:
            new_node = BinaryNode.from_node(node, value_ref=value_ref)
        return self.node_ref_class(referent=new_node)

    def _delete(self, node, key):
        if node is None:
            raise KeyError
        elif key < node.key:
            new_node = BinaryNode.from_node(
                node,
                left_ref=self._delete(
                    self._follow(node.left_ref), key))
        elif node.key < key:
            new_node = BinaryNode.from_node(
                node,
                right_ref=self._delete(
                    self._follow(node.right_ref), key))
        else:
            left = self._follow(node.left_ref)
            right = self._follow(node.right_ref)
            if left and right:
                replacement = self._find_max(left)
                left_ref = self._delete(
                    self._follow(node.left_ref), replacement.key)
                new_node = BinaryNode(
                    left_ref,
                    replacement.key,
                    replacement.value_ref,
                    node.right_ref,
                    left_ref.length + node.right_ref.length + 1,
                )
            elif left:
                return node.left_ref
            else:
                return node.right_ref
        return self.node_ref_class(referent=new_node)

    def _find_max(self, node):
        while True:
            next_node = self._follow(node.right_ref)
            if next_node is None:
                return node
            node = next_node

########NEW FILE########
__FILENAME__ = interface
from dbdb.binary_tree import BinaryTree
from dbdb.storage import Storage


class DBDB(object):
    def __init__(self, f):
        self._storage = Storage(f)
        self._tree = BinaryTree(self._storage)

    def _assert_not_closed(self):
        if self._storage.closed:
            raise ValueError('Database closed.')

    def close(self):
        self._storage.close()

    def commit(self):
        self._assert_not_closed()
        self._tree.commit()

    def __getitem__(self, key):
        self._assert_not_closed()
        return self._tree.get(key)

    def __setitem__(self, key, value):
        self._assert_not_closed()
        return self._tree.set(key, value)

    def __delitem__(self, key):
        self._assert_not_closed()
        return self._tree.pop(key)

    def __contains__(self, key):
        try:
            self[key]
        except KeyError:
            return False
        else:
            return True

    def __len__(self):
        return len(self._tree)

########NEW FILE########
__FILENAME__ = storage
# This started as a very thin wrapper around a file object, with intent to
# provide an object address on write() and a superblock. But as I was writing
# it, I realised that the user really wouldn't want to deal with the lengths of
# the writen chunks (and Pickle won't do it for you), so this module would have
# to abstract the file object into it's own degenerate key/value store.
# (Degenerate because you can't pick the keys, and it never releases storage,
# even when it becomes unreachable!)

import os
import struct

import portalocker


class Storage(object):
    SUPERBLOCK_SIZE = 4096
    INTEGER_FORMAT = "!Q"
    INTEGER_LENGTH = 8

    def __init__(self, f):
        self._f = f
        self.locked = False
        self._ensure_superblock()

    def _ensure_superblock(self):
        self.lock()
        self._seek_end()
        end_address = self._f.tell()
        if end_address < self.SUPERBLOCK_SIZE:
            self._f.write(b'\x00' * (self.SUPERBLOCK_SIZE - end_address))
        self.unlock()

    def lock(self):
        if not self.locked:
            portalocker.lock(self._f, portalocker.LOCK_EX)
            self.locked = True
            return True
        else:
            return False

    def unlock(self):
        if self.locked:
            self._f.flush()
            portalocker.unlock(self._f)
            self.locked = False

    def _seek_end(self):
        self._f.seek(0, os.SEEK_END)

    def _seek_superblock(self):
        self._f.seek(0)

    def _bytes_to_integer(self, integer_bytes):
        return struct.unpack(self.INTEGER_FORMAT, integer_bytes)[0]

    def _integer_to_bytes(self, integer):
        return struct.pack(self.INTEGER_FORMAT, integer)

    def _read_integer(self):
        return self._bytes_to_integer(self._f.read(self.INTEGER_LENGTH))

    def _write_integer(self, integer):
        self.lock()
        self._f.write(self._integer_to_bytes(integer))

    def write(self, data):
        self.lock()
        self._seek_end()
        object_address = self._f.tell()
        self._write_integer(len(data))
        self._f.write(data)
        return object_address

    def read(self, address):
        self._f.seek(address)
        length = self._read_integer()
        data = self._f.read(length)
        return data

    def commit_root_address(self, root_address):
        self.lock()
        self._f.flush()
        self._seek_superblock()
        self._write_integer(root_address)
        self._f.flush()
        self.unlock()

    def get_root_address(self):
        self._seek_superblock()
        root_address = self._read_integer()
        return root_address

    def close(self):
        self.unlock()
        self._f.close()

    @property
    def closed(self):
        return self._f.closed

########NEW FILE########
__FILENAME__ = test_binary_tree
import pickle
import random

from nose.tools import assert_raises, eq_

from dbdb.binary_tree import BinaryNode, BinaryTree, BinaryNodeRef, ValueRef


class StubStorage(object):
    def __init__(self):
        self.d = [0]
        self.locked = False

    def lock(self):
        if not self.locked:
            self.locked = True
            return True
        else:
            return False

    def unlock(self):
        pass

    def get_root_address(self):
        return 0

    def write(self, string):
        address = len(self.d)
        self.d.append(string)
        return address

    def read(self, address):
        return self.d[address]


class TestBinaryTree(object):
    def setup(self):
        self.tree = BinaryTree(StubStorage())

    def test_get_missing_key_raises_key_error(self):
        with assert_raises(KeyError):
            self.tree.get('Not A Key In The Tree')

    def test_set_and_get_key(self):
        self.tree.set('a', 'b')
        eq_(self.tree.get('a'), 'b')

    def test_random_set_and_get_keys(self):
        ten_k = list(range(10000))
        pairs = list(zip(random.sample(ten_k, 10), random.sample(ten_k, 10)))
        for i, (k, v) in enumerate(pairs, start=1):
            self.tree.set(k, v)
            eq_(len(self.tree), i)
        for k, v in pairs:
            eq_(self.tree.get(k), v)
        random.shuffle(pairs)
        for i, (k, v) in enumerate(pairs, start=1):
            self.tree.pop(k)
            eq_(len(self.tree), len(pairs) - i)

    def test_overwrite_and_get_key(self):
        self.tree.set('a', 'b')
        self.tree.set('a', 'c')
        eq_(self.tree.get('a'), 'c')

    def test_pop_non_existent_key(self):
        with assert_raises(KeyError):
            self.tree.pop('Not A Key In The Tree')

    def test_del_leaf_key(self):
        self.tree.set('b', '2')
        self.tree.pop('b')
        with assert_raises(KeyError):
            self.tree.get('b')

    def test_del_left_node_key(self):
        self.tree.set('b', '2')
        self.tree.set('a', '1')
        self.tree.pop('b')
        with assert_raises(KeyError):
            self.tree.get('b')
        self.tree.get('a')

    def test_del_right_node_key(self):
        self.tree.set('b', '2')
        self.tree.set('c', '3')
        self.tree.pop('b')
        with assert_raises(KeyError):
            self.tree.get('b')
        self.tree.get('c')

    def test_del_full_node_key(self):
        self.tree.set('b', '2')
        self.tree.set('a', '1')
        self.tree.set('c', '3')
        self.tree.pop('b')
        with assert_raises(KeyError):
            self.tree.get('b')
        self.tree.get('a')
        self.tree.get('c')


class TestBinaryNodeRef(object):
    def test_to_string_leaf(self):
        n = BinaryNode(BinaryNodeRef(), 'k', ValueRef(address=999), BinaryNodeRef(), 1)
        pickled = BinaryNodeRef.referent_to_string(n)
        d = pickle.loads(pickled)
        eq_(d['left'], 0)
        eq_(d['key'], 'k')
        eq_(d['value'], 999)
        eq_(d['right'], 0)

    def test_to_string_nonleaf(self):
        left_ref = BinaryNodeRef(address=123)
        right_ref = BinaryNodeRef(address=321)
        n = BinaryNode(left_ref, 'k', ValueRef(address=999), right_ref, 3)
        pickled = BinaryNodeRef.referent_to_string(n)
        d = pickle.loads(pickled)
        eq_(d['left'], 123)
        eq_(d['key'], 'k')
        eq_(d['value'], 999)
        eq_(d['right'], 321)

########NEW FILE########
__FILENAME__ = test_integration
import os
import os.path
import shutil
import subprocess
import tempfile

from nose.tools import assert_raises, eq_

import dbdb
import dbdb.tool


class TestDatabase(object):
    def setup(self):
        self.temp_dir = tempfile.mkdtemp()
        self.new_tempfile_name = os.path.join(self.temp_dir, 'new.db')
        self.tempfile_name = os.path.join(self.temp_dir, 'exisitng.db')
        open(self.tempfile_name, 'w').close()

    def teardown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_new_database_file(self):
        db = dbdb.connect(self.new_tempfile_name)
        db['a'] = 'aye'
        db.commit()
        db.close()

    def test_persistence(self):
        db = dbdb.connect(self.tempfile_name)
        db['b'] = 'bee'
        db['a'] = 'aye'
        db['c'] = 'see'
        db.commit()
        db['d'] = 'dee'
        eq_(len(db), 4)
        db.close()
        db = dbdb.connect(self.tempfile_name)
        eq_(db['a'], 'aye')
        eq_(db['b'], 'bee')
        eq_(db['c'], 'see')
        with assert_raises(KeyError):
            db['d']
        eq_(len(db), 3)
        db.close()


class TestTool(object):
    def setup(self):
        with tempfile.NamedTemporaryFile(delete=False) as temp_f:
            self.tempfile_name = temp_f.name

    def teardown(self):
        os.remove(self.tempfile_name)

    def _tool(self, *args):
        return subprocess.check_output(
            ['python', '-m', 'dbdb.tool', self.tempfile_name] + list(args))

    def test_get_non_existent(self):
        with assert_raises(subprocess.CalledProcessError) as raised:
            self._tool('get', 'a')
        eq_(raised.exception.returncode, dbdb.tool.BAD_KEY)

    def test_tool(self):
        expected = b'b'
        self._tool('set', 'a', expected)
        actual = self._tool('get', 'a')
        eq_(actual, expected)

########NEW FILE########
__FILENAME__ = test_storage
import os
import tempfile

from nose.tools import eq_

from dbdb.storage import Storage


class TestStorage(object):

    def setup(self):
        self.f = tempfile.NamedTemporaryFile()
        self.p = Storage(self.f)

    def _get_superblock_and_data(self, value):
        superblock = value[:Storage.SUPERBLOCK_SIZE]
        data = value[Storage.SUPERBLOCK_SIZE:]
        return superblock, data

    def _get_f_contents(self):
        self.f.flush()
        with open(self.f.name, 'rb') as f:
            return f.read()

    def test_init_ensures_superblock(self):
        EMPTY_SUPERBLOCK = (b'\x00' * Storage.SUPERBLOCK_SIZE)
        self.f.seek(0, os.SEEK_END)
        value = self._get_f_contents()
        eq_(value, EMPTY_SUPERBLOCK)

    def test_write(self):
        self.p.write(b'ABCDE')
        value = self._get_f_contents()
        superblock, data = self._get_superblock_and_data(value)
        eq_(data, b'\x00\x00\x00\x00\x00\x00\x00\x05ABCDE')

    def test_read(self):
        self.f.seek(Storage.SUPERBLOCK_SIZE)
        self.f.write(b'\x00\x00\x00\x00\x00\x00\x00\x0801234567')
        value = self.p.read(Storage.SUPERBLOCK_SIZE)
        eq_(value, b'01234567')

    def test_commit_root_address(self):
        self.p.commit_root_address(257)
        root_bytes = self._get_f_contents()[:8]
        eq_(root_bytes, b'\x00\x00\x00\x00\x00\x00\x01\x01')

    def test_get_root_address(self):
        self.f.seek(0)
        self.f.write(b'\x00\x00\x00\x00\x00\x00\x02\x02')
        root_address = self.p.get_root_address()
        eq_(root_address, 514)

    def test_workflow(self):
        a1 = self.p.write(b'one')
        a2 = self.p.write(b'two')
        self.p.commit_root_address(a2)
        a3 = self.p.write(b'three')
        eq_(self.p.get_root_address(), a2)
        a4 = self.p.write(b'four')
        self.p.commit_root_address(a4)
        eq_(self.p.read(a1), b'one')
        eq_(self.p.read(a2), b'two')
        eq_(self.p.read(a3), b'three')
        eq_(self.p.read(a4), b'four')
        eq_(self.p.get_root_address(), a4)

########NEW FILE########
__FILENAME__ = tool
from __future__ import print_function
import sys

import dbdb


OK = 0
BAD_ARGS = 1
BAD_VERB = 2
BAD_KEY = 3


def usage():
    print("Usage:", file=sys.stderr)
    print("\tpython -m dbdb.tool DBNAME get KEY", file=sys.stderr)
    print("\tpython -m dbdb.tool DBNAME set KEY VALUE", file=sys.stderr)


def main():
    if not (4 <= len(sys.argv) <= 5):
        usage()
        return BAD_ARGS
    dbname, verb, key, value = (sys.argv[1:] + [None])[:4]
    if verb not in ('get', 'set'):
        usage()
        return BAD_VERB
    db = dbdb.connect(dbname)
    if verb == 'get':
        try:
            sys.stdout.write(db[key])
        except KeyError:
            print("Key not found", file=sys.stderr)
            return BAD_KEY
    else:
        db[key] = value
        db.commit()
    return OK


if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = tree
class ValueRef(object):
    def prepare_to_store(self, storage):
        pass

    @staticmethod
    def referent_to_string(referent):
        return referent.encode('utf-8')

    @staticmethod
    def string_to_referent(string):
        return string.decode('utf-8')

    def __init__(self, referent=None, address=0):
        self._referent = referent
        self._address = address

    @property
    def address(self):
        return self._address

    def get(self, storage):
        if self._referent is None and self._address:
            self._referent = self.string_to_referent(storage.read(self._address))
        return self._referent

    def store(self, storage):
        if self._referent is not None and not self._address:
            self.prepare_to_store(storage)
            self._address = storage.write(self.referent_to_string(self._referent))


class Tree(object):
    node_ref_class = None
    value_ref_class = ValueRef

    def __init__(self, storage):
        self._storage = storage
        self._refresh_tree_ref()

    def commit(self):
        self._tree_ref.store(self._storage)
        self._storage.commit_root_address(self._tree_ref.address)

    def _refresh_tree_ref(self):
        self._tree_ref = self.node_ref_class(
            address=self._storage.get_root_address())

    def get(self, key):
        if not self._storage.locked:
            self._refresh_tree_ref()
        return self._get(self._follow(self._tree_ref), key)

    def set(self, key, value):
        if self._storage.lock():
            self._refresh_tree_ref()
        self._tree_ref = self._insert(
            self._follow(self._tree_ref), key, self.value_ref_class(value))

    def pop(self, key):
        if self._storage.lock():
            self._refresh_tree_ref()
        self._tree_ref = self._delete(
            self._follow(self._tree_ref), key)

    def _follow(self, ref):
        return ref.get(self._storage)

    def __len__(self):
        if not self._storage.locked:
            self._refresh_tree_ref()
        root = self._follow(self._tree_ref)
        if root:
            return root.length
        else:
            return 0

########NEW FILE########
__FILENAME__ = flow
import sys, os, time, random

from functools import partial
from collections import namedtuple
from itertools import product

import neighbourhood as neigh
import heuristics as heur

##############
## Settings ##
##############
TIME_LIMIT = 300.0 # Time (in seconds) to run the solver
TIME_INCREMENT = 13.0 # Time (in seconds) in between heuristic measurements
DEBUG_SWITCH = False # Displays intermediate heuristic info when True
MAX_LNS_NEIGHBOURHOODS = 1000 # Maximum number of neighbours to explore in LNS


################
## Strategies ##
#################################################
## A strategy is a particular configuration
##  of neighbourhood generator (to compute
##  the next set of candidates) and heuristic
##  computation (to select the best candidate).
##

STRATEGIES = []

# Using a namedtuple is a little cleaner than dictionaries.
#  E.g., strategy['name'] versus strategy.name
Strategy = namedtuple('Strategy', ['name', 'neighbourhood', 'heuristic'])

def initialize_strategies():

    global STRATEGIES

    # Define the neighbourhoods (and parameters) we would like to use
    NEIGHBOURHOODS = [
        ('Random Permutation', partial(neigh.neighbours_random, num=100)),
        ('Swapped Pairs', neigh.neighbours_swap),
        ('Large Neighbourhood Search (2)', partial(neigh.neighbours_LNS, size=2)),
        ('Large Neighbourhood Search (3)', partial(neigh.neighbours_LNS, size=3)),
        ('Idle Neighbourhood (3)', partial(neigh.neighbours_idle, size=3)),
        ('Idle Neighbourhood (4)', partial(neigh.neighbours_idle, size=4)),
        ('Idle Neighbourhood (5)', partial(neigh.neighbours_idle, size=5))
    ]

    # Define the heuristics we would like to use
    HEURISTICS = [
        ('Hill Climbing', heur.heur_hillclimbing),
        ('Random Selection', heur.heur_random),
        ('Biased Random Selection', heur.heur_random_hillclimbing)
    ]

    # Combine every neighbourhood and heuristic strategy
    for (n, h) in product(NEIGHBOURHOODS, HEURISTICS):
        STRATEGIES.append(Strategy("%s / %s" % (n[0], h[0]), n[1], h[1]))



def solve(data):
    """Solves an instance of the flow shop scheduling problem"""

    # We initialize the strategies here to avoid cyclic import issues
    initialize_strategies()
    global STRATEGIES

    # Record the following for each strategy:
    #  improvements: The amount a solution was improved by this strategy
    #  time_spent: The amount of time spent on the strategy
    #  weights: The weights that correspond to how good a strategy is
    #  usage: The number of times we use a strategy
    strat_improvements = {strategy: 0 for strategy in STRATEGIES}
    strat_time_spent = {strategy: 0 for strategy in STRATEGIES}
    strat_weights = {strategy: 1 for strategy in STRATEGIES}
    strat_usage = {strategy: 0 for strategy in STRATEGIES}

    # Start with a random permutation of the jobs
    perm = range(len(data))
    random.shuffle(perm)

    # Keep track of the best solution
    best_make = makespan(data, perm)
    best_perm = perm
    res = best_make

    # Maintain statistics and timing for the iterations
    iteration = 0
    time_limit = time.time() + TIME_LIMIT
    time_last_switch = time.time()

    time_delta = TIME_LIMIT / 10
    checkpoint = time.time() + time_delta
    percent_complete = 10

    print "\nSolving..."

    while time.time() < time_limit:

        if time.time() > checkpoint:
            print " %d %%" % percent_complete
            percent_complete += 10
            checkpoint += time_delta

        iteration += 1

        # Heuristically choose the best strategy
        strategy = pick_strategy(STRATEGIES, strat_weights)

        old_val = res
        old_time = time.time()

        # Use the current strategy's heuristic to pick the next permutation from
        #  the set of candidates generated by the strategy's neighbourhood
        candidates = strategy.neighbourhood(data, perm)
        perm = strategy.heuristic(data, candidates)
        res = makespan(data, perm)

        # Record the statistics on how the strategy did
        strat_improvements[strategy] += res - old_val
        strat_time_spent[strategy] += time.time() - old_time
        strat_usage[strategy] += 1

        if res < best_make:
            best_make = res
            best_perm = perm[:]

        # At regular intervals, switch the weighting on the strategies available.
        #  This way, the search can dynamically shift towards strategies that have
        #  proven more effective recently.
        if time.time() > time_last_switch + TIME_INCREMENT:

            # Normalize the improvements made by the time it takes to make them
            results = sorted([(float(strat_improvements[s]) / max(0.001, strat_time_spent[s]), s)
                              for s in STRATEGIES])

            if DEBUG_SWITCH:
                print "\nComputing another switch..."
                print "Best performer: %s (%d)" % (results[0][1].name, results[0][0])
                print "Worst performer: %s (%d)" % (results[-1][1].name, results[-1][0])

            # Boost the weight for the successful strategies
            for i in range(len(STRATEGIES)):
                strat_weights[results[i][1]] += len(STRATEGIES) - i

                # Additionally boost the unused strategies to avoid starvation
                if 0 == results[i][0]:
                    strat_weights[results[i][1]] += len(STRATEGIES)

            time_last_switch = time.time()

            if DEBUG_SWITCH:
                print results
                print sorted([strat_weights[STRATEGIES[i]] for i in range(len(STRATEGIES))])

            strat_improvements = {strategy: 0 for strategy in STRATEGIES}
            strat_time_spent = {strategy: 0 for strategy in STRATEGIES}


    print " %d %%\n" % percent_complete
    print "\nWent through %d iterations." % iteration

    print "\n(usage) Strategy:"
    results = sorted([(strat_weights[STRATEGIES[i]], i)
                      for i in range(len(STRATEGIES))], reverse=True)
    for (w, i) in results:
        print "(%d) \t%s" % (strat_usage[STRATEGIES[i]], STRATEGIES[i].name)

    return (best_perm, best_make)


def parse_problem(filename, k=1):
    """Parse the kth instance of a Taillard problem file

    The Taillard problem files are a standard benchmark set for the problem
    of flow shop scheduling. They can be found online at the following address:
    - http://mistic.heig-vd.ch/taillard/problemes.dir/ordonnancement.dir/ordonnancement.html"""

    print "\nParsing..."

    with open(filename, 'r') as f:
        # Identify the string that separates instances
        problem_line = '/number of jobs, number of machines, initial seed, upper bound and lower bound :/'

        # Strip spaces and newline characters from every line
        lines = map(str.strip, f.readlines())

        # We prep the first line for later
        lines[0] = '/' + lines[0]

        # We also know '/' does not appear in the files, so we can use it as
        #  a separator to find the right lines for the kth problem instance
        try:
            lines = '/'.join(lines).split(problem_line)[k].split('/')[2:]
        except IndexError:
            max_instances = len('/'.join(lines).split(problem_line)) - 1
            print "\nError: Instance must be within 1 and %d\n" % max_instances
            sys.exit(0)

        # Split every line based on spaces and convert each item to an int
        data = [map(int, line.split()) for line in lines]

    # We return the zipped data to rotate the rows and columns, making each
    #  item in data the durations of tasks for a particular job
    return zip(*data)


def pick_strategy(strategies, weights):
    # Picks a random strategy based on its weight: roulette wheel selection
    #  Rather than selecting a strategy entirely at random, we bias the
    #  random selection towards strategies that have worked well in the
    #  past (according to the weight value).
    total = sum([weights[strategy] for strategy in strategies])
    pick = random.uniform(0, total)
    count = weights[strategies[0]]

    i = 0
    while pick > count:
        count += weights[strategies[i+1]]
        i += 1

    return strategies[i]


def makespan(data, perm):
    """Computes the makespan of the provided solution

    For scheduling problems, the makespan refers to the difference between
    the earliest start time of any job and the latest completion time of
    any job. Minimizing the makespan amounts to minimizing the total time
    it takes to process all jobs from start to finish."""
    return compile_solution(data, perm)[-1][-1] + data[perm[-1]][-1]


def compile_solution(data, perm):
    """Compiles a scheduling on the machines given a permutation of jobs"""

    num_machines = len(data[0])

    # Note that using [[]] * range(k) would be incorrect, as it would simply
    #  copy the same list k times (as opposed to creating k distinct lists).
    machine_times = [[] for _ in range(num_machines)]

    # Assign the initial job to the machines
    machine_times[0].append(0)
    for mach in range(1,num_machines):
        # Start the next task in the job when the previous finishes
        machine_times[mach].append(machine_times[mach-1][0] +
                                   data[perm[0]][mach-1])

    # Assign the remaining jobs
    for i in range(1, len(perm)):

        # The first machine never contains any idle time
        job = perm[i]
        machine_times[0].append(machine_times[0][-1] + data[perm[i-1]][0])

        # For the remaining machines, the start time is the max of when the
        #  previous task in the job completed, or when the current machine
        #  completes the task for the previous job.
        for mach in range(1, num_machines):
            machine_times[mach].append(max(machine_times[mach-1][i] + data[perm[i]][mach-1],
                                        machine_times[mach][i-1] + data[perm[i-1]][mach]))

    return machine_times



def print_solution(data, perm):
    """Prints statistics on the computed solution"""

    sol = compile_solution(data, perm)

    print "\nPermutation: %s\n" % str([i+1 for i in perm])

    print "Makespan: %d\n" % makespan(data, perm)

    row_format ="{:>15}" * 4
    print row_format.format('Machine', 'Start Time', 'Finish Time', 'Idle Time')
    for mach in range(len(data[0])):
        finish_time = sol[mach][-1] + data[perm[-1]][mach]
        idle_time = (finish_time - sol[mach][0]) - sum([job[mach] for job in data])
        print row_format.format(mach+1, sol[mach][0], finish_time, idle_time)

    results = []
    for i in range(len(data)):
        finish_time = sol[-1][i] + data[perm[i]][-1]
        idle_time = (finish_time - sol[0][i]) - sum([time for time in data[perm[i]]])
        results.append((perm[i]+1, sol[0][i], finish_time, idle_time))

    print "\n"
    print row_format.format('Job', 'Start Time', 'Finish Time', 'Idle Time')
    for r in sorted(results):
        print row_format.format(*r)

    print "\n\nNote: Idle time does not include initial or final wait time.\n"


if __name__ == '__main__':

    if 2 == len(sys.argv):
        data = parse_problem(sys.argv[1])
    elif 3 == len(sys.argv):
        data = parse_problem(sys.argv[1], int(sys.argv[2]))
    else:
        print "\nUsage: python flow.py <Taillard problem file> [<instance number>]\n"
        sys.exit(0)

    (perm, ms) = solve(data)
    print_solution(data, perm)

########NEW FILE########
__FILENAME__ = heuristics

import random

import flow

################
## Heuristics ##
################

################################################################
## A heuristic returns a single candidate permutation from
##  a set of candidates that is given. The heuristic is also
##  given access to the problem data in order to evaluate
##  which candidate might be preferred.

def heur_hillclimbing(data, candidates):
    # Returns the best candidate in the list
    scores = [(flow.makespan(data, perm), perm) for perm in candidates]
    return sorted(scores)[0][1]

def heur_random(data, candidates):
    # Returns a random candidate choice
    return random.choice(candidates)

def heur_random_hillclimbing(data, candidates):
    # Returns a candidate with probability proportional to its rank in sorted quality
    scores = [(flow.makespan(data, perm), perm) for perm in candidates]
    i = 0
    while (random.random() < 0.5) and (i < len(scores) - 1):
        i += 1
    return sorted(scores)[i][1]

########NEW FILE########
__FILENAME__ = neighbourhood

import random
from itertools import combinations, permutations

import flow

##############################
## Neighbourhood Generators ##
##############################

def neighbours_random(data, perm, num = 1):
    # Returns <num> random job permutations, including the current one
    candidates = [perm]
    for i in range(num):
        candidate = perm[:]
        random.shuffle(candidate)
        candidates.append(candidate)
    return candidates

def neighbours_swap(data, perm):
    # Returns the permutations corresponding to swapping every pair of jobs
    candidates = [perm]
    for (i,j) in combinations(range(len(perm)), 2):
        candidate = perm[:]
        candidate[i], candidate[j] = candidate[j], candidate[i]
        candidates.append(candidate)
    return candidates

def neighbours_LNS(data, perm, size = 2):
    # Returns the Large Neighbourhood Search neighbours
    candidates = [perm]

    # Bound the number of neighbourhoods in case there are too many jobs
    neighbourhoods = list(combinations(range(len(perm)), size))
    random.shuffle(neighbourhoods)

    for subset in neighbourhoods[:flow.MAX_LNS_NEIGHBOURHOODS]:

        # Keep track of the best candidate for each neighbourhood
        best_make = flow.makespan(data, perm)
        best_perm = perm

        # Enumerate every permutation of the selected neighbourhood
        for ordering in permutations(subset):
            candidate = perm[:]
            for i in range(len(ordering)):
                candidate[subset[i]] = perm[ordering[i]]
            res = flow.makespan(data, candidate)
            if res < best_make:
                best_make = res
                best_perm = candidate

        # Record the best candidate as part of the larger neighbourhood
        candidates.append(best_perm)

    return candidates

def neighbours_idle(data, perm, size=4):
    # Returns the permutations of the most <size> idle jobs
    candidates = [perm]

    # Compute the idle time for each job
    sol = flow.compile_solution(data, perm)
    results = []

    for i in range(len(data)):
        finish_time = sol[-1][i] + data[perm[i]][-1]
        idle_time = (finish_time - sol[0][i]) - sum([time for time in data[perm[i]]])
        results.append((idle_time, perm[i]))

    # Take the <size> most idle jobs
    subset = [job for (idle, job) in list(reversed(results))[:size]]

    # Enumerate the permutations of the idle jobs
    for ordering in permutations(subset):
        candidate = perm[:]
        for i in range(len(ordering)):
            candidate[subset[i]] = perm[ordering[i]]
        candidates.append(candidate)

    return candidates

########NEW FILE########
__FILENAME__ = aabb
from OpenGL.GL import glCallList, glMatrixMode, glPolygonMode, glPopMatrix, glPushMatrix, glTranslated, \
                      GL_FILL, GL_FRONT_AND_BACK, GL_LINE, GL_MODELVIEW
from primitive import G_OBJ_CUBE
import numpy
import math

EPSILON = 0.000001


class AABB(object):

    def __init__(self, center, size):
        """ Axis aligned bounding box.
            This is a box that is aligned with the XYZ axes of the model coordinate space.
            It's used for collision detection with rays for selection.
            It could also be used for rudimentary collision detection between nodes. """
        self.center = numpy.array(center)
        self.size = numpy.array(size)

    def scale(self, scale):
        self.size *= scale

    def ray_hit(self, origin, direction, modelmatrix):
        """ Returns True <=> the ray hits the AABB
            Consumes: origin, direction -> describes the ray
                      modelmatrix       -> the matrix to convert from ray coordinate space to AABB coordinate space """
        aabb_min = self.center - self.size
        aabb_max = self.center + self.size
        tmin = 0.0
        tmax = 100000.0

        obb_pos_worldspace = numpy.array([modelmatrix[0, 3], modelmatrix[1, 3], modelmatrix[2, 3]])
        delta = (obb_pos_worldspace - origin)

        # test intersection with 2 planes perpendicular to OBB's x-axis
        xaxis = numpy.array((modelmatrix[0, 0], modelmatrix[0, 1], modelmatrix[0, 2]))

        e = numpy.dot(xaxis, delta)
        f = numpy.dot(direction, xaxis)
        if math.fabs(f) > 0.0 + EPSILON:
            t1 = (e + aabb_min[0])/f
            t2 = (e + aabb_max[0])/f
            if t1 > t2:
                t1, t2 = t2, t1
            if t2 < tmax:
                tmax = t2
            if t1 > tmin:
                tmin = t1
            if tmax < tmin:
                return (False, 0)
        else:
            if (-e + aabb_min[0] > 0.0 + EPSILON) or (-e+aabb_max[0] < 0.0 - EPSILON):
                return False, 0

        yaxis = numpy.array((modelmatrix[1, 0], modelmatrix[1, 1], modelmatrix[1, 2]))
        e = numpy.dot(yaxis, delta)
        f = numpy.dot(direction, yaxis)
        # intersection in y
        if math.fabs(f) > 0.0 + EPSILON:
            t1 = (e + aabb_min[1])/f
            t2 = (e + aabb_max[1])/f
            if t1 > t2:
                t1, t2 = t2, t1
            if t2 < tmax:
                tmax = t2
            if t1 > tmin:
                tmin = t1
            if tmax < tmin:
                return (False, 0)
        else:
            if (-e + aabb_min[1] > 0.0 + EPSILON) or (-e+aabb_max[1] < 0.0 - EPSILON):
                return False, 0

        # intersection in z
        zaxis = numpy.array((modelmatrix[2, 0], modelmatrix[2, 1], modelmatrix[2, 2]))
        e = numpy.dot(zaxis, delta)
        f = numpy.dot(direction, zaxis)
        if math.fabs(f) > 0.0 + EPSILON:
            t1 = (e + aabb_min[2])/f
            t2 = (e + aabb_max[2])/f
            if t1 > t2:
                t1, t2 = t2, t1
            if t2 < tmax:
                tmax = t2
            if t1 > tmin:
                tmin = t1
            if tmax < tmin:
                return (False, 0)
        else:
            if (-e + aabb_min[2] > 0.0 + EPSILON) or (-e+aabb_max[2] < 0.0 - EPSILON):
                return False, 0

        return True, tmin

    def render(self):
        """ render the AABB. This can be useful for debugging purposes """
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glTranslated(self.center[0], self.center[1], self.center[2])
        glCallList(G_OBJ_CUBE)
        glPopMatrix()
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

########NEW FILE########
__FILENAME__ = color
MAX_COLOR = 9
MIN_COLOR = 0
COLORS = { # RGB Colors
    0:  (1.0, 1.0, 1.0),
    1:  (0.05, 0.05, 0.9),
    2:  (0.05, 0.9, 0.05),
    3:  (0.9, 0.05, 0.05),
    4:  (0.9, 0.9, 0.0),
    5:  (0.1, 0.8, 0.7),
    6:  (0.7, 0.2, 0.7),
    7:  (0.7, 0.7, 0.7),
    8:  (0.4, 0.4, 0.4),
    9:  (0.0, 0.0, 0.0),
}

########NEW FILE########
__FILENAME__ = interaction
from collections import defaultdict
from OpenGL.GLUT import glutGet, glutKeyboardFunc, glutMotionFunc, glutMouseFunc, glutPassiveMotionFunc, \
                        glutPostRedisplay, glutSpecialFunc
from OpenGL.GLUT import GLUT_LEFT_BUTTON, GLUT_RIGHT_BUTTON, GLUT_MIDDLE_BUTTON, \
                        GLUT_WINDOW_HEIGHT, GLUT_WINDOW_WIDTH, \
                        GLUT_DOWN, GLUT_KEY_UP, GLUT_KEY_DOWN, GLUT_KEY_LEFT, GLUT_KEY_RIGHT
import trackball


class Interaction(object):

    def __init__(self):
        """ Handles user interaction """
        # currently pressed mouse button
        self.pressed = None
        # the current location of the camera
        self.translation = [0, 0, 0, 0]
        # the trackball to calculate rotation
        self.trackball = trackball.Trackball(theta = -25, distance=15)
        # the current mouse location
        self.mouse_loc = None
        # Unsophisticated callback mechanism
        self.callbacks = defaultdict(list)
        
        self.register()

    def register(self):
        """ register callbacks with glut """
        glutMouseFunc(self.handle_mouse_button)
        glutMotionFunc(self.handle_mouse_move)
        glutKeyboardFunc(self.handle_keystroke)

        glutSpecialFunc(self.handle_keystroke)
        glutPassiveMotionFunc(None)

    def register_callback(self, name, func):
        """ registers a callback for a certain event """
        self.callbacks[name].append(func)

    def trigger(self, name, *args, **kwargs):
        """ calls a callback, forwards the args """
        for func in self.callbacks[name]:
            func(*args, **kwargs)

    def translate(self, x, y, z):
        """ translate the camera """
        self.translation[0] += x
        self.translation[1] += y
        self.translation[2] += z

    def handle_mouse_button(self, button, mode, x, y):
        """ Called when the mouse button is pressed or released """
        xSize, ySize = glutGet(GLUT_WINDOW_WIDTH), glutGet(GLUT_WINDOW_HEIGHT)
        y = ySize - y  # invert the y coordinate because OpenGL is inverted
        self.mouse_loc = (x, y)

        if mode == GLUT_DOWN:
            self.pressed = button
            if button == GLUT_RIGHT_BUTTON:
                pass
            elif button == GLUT_LEFT_BUTTON:  # pick
                self.trigger('pick', x, y)
            elif button == 3:  # scroll up
                self.translate(0, 0, -1.0)
            elif button == 4:  # scroll up
                self.translate(0, 0, 1.0)
        else:  # mouse button release
            self.pressed = None
        glutPostRedisplay()

    def handle_mouse_move(self, x, screen_y):
        """ Called when the mouse is moved """
        xSize, ySize = glutGet(GLUT_WINDOW_WIDTH), glutGet(GLUT_WINDOW_HEIGHT)
        y = ySize - screen_y  # invert the y coordinate because OpenGL is inverted
        if self.pressed is not None:
            dx = self.mouse_loc[0] - x
            dy = self.mouse_loc[1] - y
            if self.pressed == GLUT_RIGHT_BUTTON and self.trackball is not None:
                # ignore the updated camera loc because we want to always rotate around the origin
                self.trackball.drag_to(self.mouse_loc[0], self.mouse_loc[1], -dx, -dy)
            elif self.pressed == GLUT_LEFT_BUTTON:
                self.trigger('move', x, y)
            elif self.pressed == GLUT_MIDDLE_BUTTON:
                self.translate(dx/60.0, dy/60.0, 0)
            else:
                pass
            glutPostRedisplay()
        self.mouse_loc = (x, y)

    def handle_keystroke(self, key, x, screen_y):
        """ Called on keyboard input from the user """
        xSize, ySize = glutGet(GLUT_WINDOW_WIDTH), glutGet(GLUT_WINDOW_HEIGHT)
        y = ySize - screen_y
        if key == 's':
            self.trigger('place', 'sphere', x, y)
        elif key == 'c':
            self.trigger('place', 'cube', x, y)
        elif key == GLUT_KEY_UP:
            self.trigger('scale', up=True)
        elif key == GLUT_KEY_DOWN:
            self.trigger('scale', up=False)
        elif key == GLUT_KEY_LEFT:
            self.trigger('rotate_color', forward=True)
        elif key == GLUT_KEY_RIGHT:
            self.trigger('rotate_color', forward=False)
        glutPostRedisplay()

########NEW FILE########
__FILENAME__ = node
import random
from OpenGL.GL import glCallList, glColor3f, glMaterialfv, glMultMatrixf, glPopMatrix, glPushMatrix, \
                      GL_EMISSION, GL_FRONT
import numpy

from primitive import G_OBJ_CUBE, G_OBJ_SPHERE
from aabb import AABB
from transformation import scaling, translation
import color


class Node(object):
    """ Base class for scene elements """
    def __init__(self):
        self.location = [0, 0, 0]
        self.color_index = random.randint(color.MIN_COLOR, color.MAX_COLOR)
        self.aabb = AABB([0.0, 0.0, 0.0], [0.5, 0.5, 0.5])
        self.translation = numpy.identity(4)
        self.scalemat = numpy.identity(4)
        self.selected = False
        self.scale_mult = 1.0

    def render(self):
        """ renders the item to the screen """
        raise NotImplementedError("The Abstract Node Class doesn't define 'render'")

    def translate(self, x, y, z):
        self.translation = numpy.dot(self.translation, translation([x, y, z]))

    def rotate_color(self, forwards):
        self.color_index += 1 if forwards else -1
        if self.color_index > color.MAX_COLOR:
            self.color_index = color.MIN_COLOR
        if self.color_index < color.MIN_COLOR:
            self.color_index = color.MAX_COLOR

    def scale(self, up):
        s = self.scale_mult * 1.1 if up else 0.9
        self.scalemat = numpy.dot(self.scalemat, scaling([s, s, s]))
        self.aabb.scale(s)

    def pick(self, start, direction, mat):
        """ Return whether or not the ray hits the object
           Consume:  start, direction    the ray to check
                     mat                 the modelview matrix to transform the ray by """

        # transform the modelview matrix by the current translation
        newmat = numpy.dot(mat, self.translation)
        results = self.aabb.ray_hit(start, direction, newmat)
        return results

    def select(self, select=None):
        """ Toggles or sets selected state """
        if select is not None:
            self.selected = select
        else:
            self.selected = not self.selected

class Primitive(Node):
    def __init__(self):
        super(Primitive, self).__init__()
        self.call_list = None

    def render(self):
        glPushMatrix()
        glMultMatrixf(numpy.transpose(self.translation))
        glMultMatrixf(self.scalemat)
        cur_color = color.COLORS[self.color_index]
        glColor3f(cur_color[0], cur_color[1], cur_color[2])
        if self.selected:  # emit light if the node is selected
            glMaterialfv(GL_FRONT, GL_EMISSION, [0.3, 0.3, 0.3])
        glCallList(self.call_list)
        if self.selected:
            glMaterialfv(GL_FRONT, GL_EMISSION, [0.0, 0.0, 0.0])

        glPopMatrix()



class Sphere(Primitive):
    """ Sphere primitive """
    def __init__(self):
        super(Sphere, self).__init__()
        self.call_list = G_OBJ_SPHERE


class Cube(Primitive):
    """ Cube primitive """
    def __init__(self):
        super(Cube, self).__init__()
        self.call_list = G_OBJ_CUBE

########NEW FILE########
__FILENAME__ = primitive
from OpenGL.GL import glBegin, glColor3f, glEnd, glEndList, glLineWidth, glNewList, glNormal3f, glVertex3f, \
                      GL_COMPILE, GL_LINES, GL_QUADS
from OpenGL.GLU import gluDeleteQuadric, gluNewQuadric, gluSphere

G_OBJ_PLANE = 1
G_OBJ_SPHERE = 2
G_OBJ_CUBE = 3


def make_plane():
    glNewList(G_OBJ_PLANE, GL_COMPILE)
    glBegin(GL_LINES)
    glColor3f(0, 0, 0)
    for i in xrange(41):
        glVertex3f(-10.0 + 0.5 * i, 0, -10)
        glVertex3f(-10.0 + 0.5 * i, 0, 10)
        glVertex3f(-10.0, 0, -10 + 0.5 * i)
        glVertex3f(10.0, 0, -10 + 0.5 * i)

    # Axes
    glEnd()
    glLineWidth(5)

    glBegin(GL_LINES)
    glColor3f(0.5, 0.7, 0.5)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(5, 0.0, 0.0)
    glEnd()

    glBegin(GL_LINES)
    glColor3f(0.5, 0.7, 0.5)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(0.0, 5, 0.0)
    glEnd()

    glBegin(GL_LINES)
    glColor3f(0.5, 0.7, 0.5)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(0.0, 0.0, 5)
    glEnd()

    # Draw the Y.
    glBegin(GL_LINES)
    glColor3f(0.0, 0.0, 0.0)
    glVertex3f(0.0, 5.0, 0.0)
    glVertex3f(0.0, 5.5, 0.0)
    glVertex3f(0.0, 5.5, 0.0)
    glVertex3f(-0.5, 6.0, 0.0)
    glVertex3f(0.0, 5.5, 0.0)
    glVertex3f(0.5, 6.0, 0.0)

    # Draw the Z.
    glVertex3f(-0.5, 0.0, 5.0)
    glVertex3f(0.5, 0.0, 5.0)
    glVertex3f(0.5, 0.0, 5.0)
    glVertex3f(-0.5, 0.0, 6.0)
    glVertex3f(-0.5, 0.0, 6.0)
    glVertex3f(0.5, 0.0, 6.0)

    # Draw the X.
    glVertex3f(5.0, 0.0, 0.5)
    glVertex3f(6.0, 0.0, -0.5)
    glVertex3f(5.0, 0.0, -0.5)
    glVertex3f(6.0, 0.0, 0.5)

    glEnd()
    glLineWidth(1)
    glEndList()


def make_sphere():
    glNewList(G_OBJ_SPHERE, GL_COMPILE)
    quad = gluNewQuadric()
    gluSphere(quad, 0.5, 30, 30)
    gluDeleteQuadric(quad)
    glEndList()


def make_cube():
    glNewList(G_OBJ_CUBE, GL_COMPILE)
    vertices = [((-0.5, -0.5, -0.5), (-0.5, -0.5, 0.5), (-0.5, 0.5, 0.5), (-0.5, 0.5, -0.5)),
                ((-0.5, -0.5, -0.5), (-0.5, 0.5, -0.5), (0.5, 0.5, -0.5), (0.5, -0.5, -0.5)),
                ((0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (0.5, 0.5, 0.5), (0.5, -0.5, 0.5)),
                ((-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5)),
                ((-0.5, -0.5, 0.5), (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, -0.5, 0.5)),
                ((-0.5, 0.5, -0.5), (-0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (0.5, 0.5, -0.5))]
    normals = [(-1.0, 0.0, 0.0), (0.0, 0.0, -1.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0), (0.0, 1.0, 0.0)]

    glBegin(GL_QUADS)
    for i in xrange(6):
        glNormal3f(normals[i][0], normals[i][1], normals[i][2])
        for j in xrange(4):
            glVertex3f(vertices[i][j][0], vertices[i][j][1], vertices[i][j][2])
    glEnd()
    glEndList()


def init_primitives():
    make_plane()
    make_sphere()
    make_cube()

########NEW FILE########
__FILENAME__ = scene
import sys
import numpy
from node import Sphere, Cube


class Scene(object):
    """ Base class for scene nodes.
        Scene nodes currently only include primitives """

    # the default depth from the camera to place an object at
    PLACE_DEPTH = 15.0

    def __init__(self):
        """ Initialize the Scene """
        # The scene keeps a list of nodes that are displayed
        self.node_list = list()
        # Keep track of the currently selected node.
        # Actions may depend on whether or not something is selected
        self.selected_node = None

    def render(self):
        """ Render the scene. This function simply calls the render function for each node. """
        for node in self.node_list:
            node.render()

    def add_node(self, node):
        """ Add a new node to the scene """
        self.node_list.append(node)

    def pick(self, start, direction, mat):
        """ Execute selection.
            Consume: start, direction describing a Ray
                     mat              is the inverse of the current modelview matrix for the scene """
        if self.selected_node is not None:
            self.selected_node.select(False)
            self.selected_node = None

        # Keep track of the closest hit.
        mindist, closest_node = sys.maxint, None
        for node in self.node_list:
            hit, distance = node.pick(start, direction, mat)
            if hit and distance < mindist:
                mindist, closest_node = distance, node

        # If we hit something, keep track of it.
        if closest_node is not None:
            closest_node.select()
            closest_node.depth = mindist
            closest_node.selected_loc = start + direction * mindist
            self.selected_node = closest_node

    def move(self, start, direction, inv_modelview):
        """ Move the selected node, if there is one.
            Consume:  start, direction  describes the Ray to move to
                      mat               is the modelview matrix for the scene """
        if self.selected_node is None: return

        # Find the current depth and location of the selected node
        node = self.selected_node
        depth = node.depth
        oldloc = node.selected_loc

        # The new location of the node is the same depth along the new ray
        newloc = (start + direction * depth)

        # transform the translation with the modelview matrix
        translation = newloc - oldloc
        pre_tran = numpy.array([translation[0], translation[1], translation[2], 0])
        translation = inv_modelview.dot(pre_tran)

        # translate the node and track its location
        node.translate(translation[0], translation[1], translation[2])
        node.selected_loc = newloc

    def place(self, shape, start, direction, inv_modelview):
        """ Place a new node.
            Consume:  shape             the shape to add
                      start, direction  describes the Ray to move to
                      mat               is the modelview matrix for the scene """
        new_node = None
        if shape == 'sphere': new_node = Sphere()
        elif shape == 'cube': new_node = Cube()

        self.add_node(new_node)

        # place the node at the cursor in camera-space
        translation = (start + direction * self.PLACE_DEPTH)

        # convert the translation to world-space
        pre_tran = numpy.array([translation[0], translation[1], translation[2], 1])
        translation = inv_modelview.dot(pre_tran)

        new_node.translate(translation[0], translation[1], translation[2])

    def rotate_color(self, forwards):
        """ Rotate the color of the currently selected node """
        if self.selected_node is None: return
        self.selected_node.rotate_color(forwards)

    def scale(self, up):
        """ Scale the current selection """
        if self.selected_node is None: return
        self.selected_node.scale(up)

########NEW FILE########
__FILENAME__ = trackball
#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c)  2009 Nicolas Rougier
#                2008 Roger Allen
#                1993, 1994, Silicon Graphics, Inc.
# ALL RIGHTS RESERVED
# Permission to use, copy, modify, and distribute this software for
# any purpose and without fee is hereby granted, provided that the above
# copyright notice appear in all copies and that both the copyright notice
# and this permission notice appear in supporting documentation, and that
# the name of Silicon Graphics, Inc. not be used in advertising
# or publicity pertaining to distribution of the software without specific,
# written prior permission.
# 
# THE MATERIAL EMBODIED ON THIS SOFTWARE IS PROVIDED TO YOU "AS-IS"
# AND WITHOUT WARRANTY OF ANY KIND, EXPRESS, IMPLIED OR OTHERWISE,
# INCLUDING WITHOUT LIMITATION, ANY WARRANTY OF MERCHANTABILITY OR
# FITNESS FOR A PARTICULAR PURPOSE.  IN NO EVENT SHALL SILICON
# GRAPHICS, INC.  BE LIABLE TO YOU OR ANYONE ELSE FOR ANY DIRECT,
# SPECIAL, INCIDENTAL, INDIRECT OR CONSEQUENTIAL DAMAGES OF ANY
# KIND, OR ANY DAMAGES WHATSOEVER, INCLUDING WITHOUT LIMITATION,
# LOSS OF PROFIT, LOSS OF USE, SAVINGS OR REVENUE, OR THE CLAIMS OF
# THIRD PARTIES, WHETHER OR NOT SILICON GRAPHICS, INC.  HAS BEEN
# ADVISED OF THE POSSIBILITY OF SUCH LOSS, HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, ARISING OUT OF OR IN CONNECTION WITH THE
# POSSESSION, USE OR PERFORMANCE OF THIS SOFTWARE.
# 
# US Government Users Restricted Rights
# Use, duplication, or disclosure by the Government is subject to
# restrictions set forth in FAR 52.227.19(c)(2) or subparagraph
# (c)(1)(ii) of the Rights in Technical Data and Computer Software
# clause at DFARS 252.227-7013 and/or in similar or successor
# clauses in the FAR or the DOD or NASA FAR Supplement.
# Unpublished-- rights reserved under the copyright laws of the
# United States.  Contractor/manufacturer is Silicon Graphics,
# Inc., 2011 N.  Shoreline Blvd., Mountain View, CA 94039-7311.
#
# Originally implemented by Gavin Bell, lots of ideas from Thant Tessman
# and the August '88 issue of Siggraph's "Computer Graphics," pp. 121-129.
# and David M. Ciemiewicz, Mark Grossman, Henry Moreton, and Paul Haeberli
#
# Note: See the following for more information on quaternions:
# 
# - Shoemake, K., Animating rotation with quaternion curves, Computer
#   Graphics 19, No 3 (Proc. SIGGRAPH'85), 245-254, 1985.
# - Pletinckx, D., Quaternion calculus as a basic tool in computer
#   graphics, The Visual Computer 5, 2-13, 1989.
# -----------------------------------------------------------------------------
''' Provides a virtual trackball for 3D scene viewing

Example usage:
 
   trackball = Trackball(45,45)

   @window.event
   def on_mouse_drag(x, y, dx, dy, button, modifiers):
       x  = (x*2.0 - window.width)/float(window.width)
       dx = 2*dx/float(window.width)
       y  = (y*2.0 - window.height)/float(window.height)
       dy = 2*dy/float(window.height)
       trackball.drag(x,y,dx,dy)

   @window.event
   def on_resize(width,height):
       glViewport(0, 0, window.width, window.height)
       glMatrixMode(GL_PROJECTION)
       glLoadIdentity()
       gluPerspective(45, window.width / float(window.height), .1, 1000)
       glMatrixMode (GL_MODELVIEW)
       glLoadIdentity ()
       glTranslatef (0, 0, -3)
       glMultMatrixf(trackball.matrix)

You can also set trackball orientation directly by setting theta and phi value
expressed in degrees. Theta relates to the rotation angle around X axis while
phi relates to the rotation angle around Z axis.

'''
__docformat__ = 'restructuredtext'
__version__ = '1.0'

import math
import OpenGL.GL as gl
from OpenGL.GL import GLfloat


# Some useful functions on vectors
# -----------------------------------------------------------------------------
def _v_add(v1, v2):
    return [v1[0]+v2[0], v1[1]+v2[1], v1[2]+v2[2]]
def _v_sub(v1, v2):
    return [v1[0]-v2[0], v1[1]-v2[1], v1[2]-v2[2]]
def _v_mul(v, s):
    return [v[0]*s, v[1]*s, v[2]*s]
def _v_dot(v1, v2):
    return v1[0]*v2[0]+v1[1]*v2[1]+v1[2]*v2[2]
def _v_cross(v1, v2):
    return [(v1[1]*v2[2]) - (v1[2]*v2[1]),
            (v1[2]*v2[0]) - (v1[0]*v2[2]),
            (v1[0]*v2[1]) - (v1[1]*v2[0])]
def _v_length(v):
    return math.sqrt(_v_dot(v,v))
def _v_normalize(v):
    try:                      return _v_mul(v,1.0/_v_length(v))
    except ZeroDivisionError: return v

# Some useful functions on quaternions
# -----------------------------------------------------------------------------
def _q_add(q1,q2):
    t1 = _v_mul(q1, q2[3])
    t2 = _v_mul(q2, q1[3])
    t3 = _v_cross(q2, q1)
    tf = _v_add(t1, t2)
    tf = _v_add(t3, tf)
    tf.append(q1[3]*q2[3]-_v_dot(q1,q2))
    return tf
def _q_mul(q, s):
    return [q[0]*s, q[1]*s, q[2]*s, q[3]*s]
def _q_dot(q1, q2):
    return q1[0]*q2[0] + q1[1]*q2[1] + q1[2]*q2[2] + q1[3]*q2[3]
def _q_length(q):
    return math.sqrt(_q_dot(q,q))
def _q_normalize(q):
    try:                      return _q_mul(q,1.0/_q_length(q))
    except ZeroDivisionError: return q
def _q_from_axis_angle(v, phi):
    q = _v_mul(_v_normalize(v), math.sin(phi/2.0))
    q.append(math.cos(phi/2.0))
    return q
def _q_rotmatrix(q):
    m = [0.0]*16
    m[0*4+0] = 1.0 - 2.0*(q[1]*q[1] + q[2]*q[2])
    m[0*4+1] = 2.0 * (q[0]*q[1] - q[2]*q[3])
    m[0*4+2] = 2.0 * (q[2]*q[0] + q[1]*q[3])
    m[0*4+3] = 0.0
    m[1*4+0] = 2.0 * (q[0]*q[1] + q[2]*q[3])
    m[1*4+1] = 1.0 - 2.0*(q[2]*q[2] + q[0]*q[0])
    m[1*4+2] = 2.0 * (q[1]*q[2] - q[0]*q[3])
    m[1*4+3] = 0.0
    m[2*4+0] = 2.0 * (q[2]*q[0] - q[1]*q[3])
    m[2*4+1] = 2.0 * (q[1]*q[2] + q[0]*q[3])
    m[2*4+2] = 1.0 - 2.0*(q[1]*q[1] + q[0]*q[0])
    m[3*4+3] = 1.0
    return m



class Trackball(object):
    ''' Virtual trackball for 3D scene viewing. '''

    def __init__(self, theta=0, phi=0, zoom=1, distance=3):
        ''' Build a new trackball with specified view '''

        self._rotation = [0,0,0,1]
        self.zoom = zoom
        self.distance = distance
        self._count = 0
        self._matrix=None
        self._RENORMCOUNT = 97
        self._TRACKBALLSIZE = 0.8
        self._set_orientation(theta,phi)
        self._x = 0.0
        self._y = 0.0

    def drag_to (self, x, y, dx, dy):
        ''' Move trackball view from x,y to x+dx,y+dy. '''
        viewport = gl.glGetIntegerv(gl.GL_VIEWPORT)
        width,height = float(viewport[2]), float(viewport[3])
        x  = (x*2.0 - width)/width
        dx = (2.*dx)/width
        y  = (y*2.0 - height)/height
        dy = (2.*dy)/height
        q = self._rotate(x,y,dx,dy)
        self._rotation = _q_add(q,self._rotation)
        self._count += 1
        if self._count > self._RENORMCOUNT:
            self._rotation = _q_normalize(self._rotation)
            self._count = 0
        m = _q_rotmatrix(self._rotation)
        self._matrix = (GLfloat*len(m))(*m)

    def zoom_to (self, x, y, dx, dy):
        ''' Zoom trackball by a factor dy '''
        viewport = gl.glGetIntegerv(gl.GL_VIEWPORT)
        height = float(viewport[3])
        self.zoom = self.zoom-5*dy/height

    def pan_to (self, x, y, dx, dy):
        ''' Pan trackball by a factor dx,dy '''
        self.x += dx*0.1
        self.y += dy*0.1


    def push(self):
        viewport = gl.glGetIntegerv(gl.GL_VIEWPORT)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPushMatrix()
        gl.glLoadIdentity ()
        aspect = viewport[2]/float(viewport[3])
        aperture = 35.0
        near = 0.1
        far = 100.0
        top = math.tan(aperture*3.14159/360.0) * near * self._zoom
        bottom = -top
        left = aspect * bottom
        right = aspect * top
        gl.glFrustum (left, right, bottom, top, near, far)
        gl.glMatrixMode (gl.GL_MODELVIEW)
        gl.glPushMatrix()
        gl.glLoadIdentity ()
        # gl.glTranslate (0.0, 0, -self._distance)
        gl.glTranslate (self._x, self._y, -self._distance)
        gl.glMultMatrixf (self._matrix)

    def pop(void):
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPopMatrix()

    def _get_matrix(self):
        return self._matrix
    matrix = property(_get_matrix,
                     doc='''Model view matrix transformation (read-only)''')

    def _get_zoom(self):
        return self._zoom
    def _set_zoom(self, zoom):
        self._zoom = zoom
        if self._zoom < .25: self._zoom = .25
        if self._zoom > 10: self._zoom = 10
    zoom = property(_get_zoom, _set_zoom,
                     doc='''Zoom factor''')

    def _get_distance(self):
        return self._distance
    def _set_distance(self, distance):
        self._distance = distance
        if self._distance < 1: self._distance= 1
    distance = property(_get_distance, _set_distance,
                        doc='''Scene distance from point of view''')

    def _get_theta(self):
        self._theta, self._phi = self._get_orientation()
        return self._theta
    def _set_theta(self, theta):
        self._set_orientation(math.fmod(theta,360.0),
                              math.fmod(self._phi,360.0))
    theta = property(_get_theta, _set_theta,
                     doc='''Angle (in degrees) around the z axis''')


    def _get_phi(self):
        self._theta, self._phi = self._get_orientation()
        return self._phi
    def _set_phi(self, phi):
        self._set_orientation(math.fmod(self._theta,360.),
                              math.fmod(phi,360.0))
    phi = property(_get_phi, _set_phi,
                     doc='''Angle around x axis''')


    def _get_orientation(self):
        ''' Return current computed orientation (theta,phi). ''' 

        q0,q1,q2,q3 = self._rotation
        ax = math.atan(2*(q0*q1+q2*q3)/(1-2*(q1*q1+q2*q2)))*180.0/math.pi
        az = math.atan(2*(q0*q3+q1*q2)/(1-2*(q2*q2+q3*q3)))*180.0/math.pi
        return -az,ax

    def _set_orientation(self, theta, phi):
        ''' Computes rotation corresponding to theta and phi. ''' 

        self._theta = theta
        self._phi = phi
        angle = self._theta*(math.pi/180.0)
        sine = math.sin(0.5*angle)
        xrot = [1*sine, 0, 0, math.cos(0.5*angle)]
        angle = self._phi*(math.pi/180.0)
        sine = math.sin(0.5*angle);
        zrot = [0, 0, sine, math.cos(0.5*angle)]
        self._rotation = _q_add(xrot, zrot)
        m = _q_rotmatrix(self._rotation)
        self._matrix = (GLfloat*len(m))(*m)


    def _project(self, r, x, y):
        ''' Project an x,y pair onto a sphere of radius r OR a hyperbolic sheet
            if we are away from the center of the sphere.
        '''

        d = math.sqrt(x*x + y*y)
        if (d < r * 0.70710678118654752440):    # Inside sphere
            z = math.sqrt(r*r - d*d)
        else:                                   # On hyperbola
            t = r / 1.41421356237309504880
            z = t*t / d
        return z


    def _rotate(self, x, y, dx, dy): 
        ''' Simulate a track-ball.

            Project the points onto the virtual trackball, then figure out the
            axis of rotation, which is the cross product of x,y and x+dx,y+dy.

            Note: This is a deformed trackball-- this is a trackball in the
            center, but is deformed into a hyperbolic sheet of rotation away
            from the center.  This particular function was chosen after trying
            out several variations.
        '''

        if not dx and not dy:
            return [ 0.0, 0.0, 0.0, 1.0]
        last = [x, y,       self._project(self._TRACKBALLSIZE, x, y)]
        new  = [x+dx, y+dy, self._project(self._TRACKBALLSIZE, x+dx, y+dy)]
        a = _v_cross(new, last)
        d = _v_sub(last, new)
        t = _v_length(d) / (2.0*self._TRACKBALLSIZE)
        if (t > 1.0): t = 1.0
        if (t < -1.0): t = -1.0
        phi = 2.0 * math.asin(t)
        return _q_from_axis_angle(a,phi)


    def __str__(self):
        phi = str(self.phi)
        theta = str(self.theta)
        zoom = str(self.zoom)
        return 'Trackball(phi=%s,theta=%s,zoom=%s)' % (phi,theta,zoom)

    def __repr__(self):
        phi = str(self.phi)
        theta = str(self.theta)
        zoom = str(self.zoom)
        return 'Trackball(phi=%s,theta=%s,zoom=%s)' % (phi,theta,zoom)


########NEW FILE########
__FILENAME__ = transformation
import numpy


def translation(displacement):
    t = numpy.identity(4)
    t[0, 3] = displacement[0]
    t[1, 3] = displacement[1]
    t[2, 3] = displacement[2]
    return t


def scaling(scale):
    s = numpy.identity(4)
    s[0, 0] = scale[0]
    s[1, 1] = scale[1]
    s[2, 2] = scale[2]
    s[3, 3] = 1
    return s

########NEW FILE########
__FILENAME__ = viewer
#! /usr/bin/env python
from OpenGL.GL import glCallList, glClear, glClearColor, glColorMaterial, glCullFace, glDepthFunc, glDisable, glEnable,\
                      glFlush, glGetFloatv, glLightfv, glLoadIdentity, glMatrixMode, glMultMatrixf, glPopMatrix, \
                      glPushMatrix, glTranslated, glViewport, \
                      GL_AMBIENT_AND_DIFFUSE, GL_BACK, GL_CULL_FACE, GL_COLOR_BUFFER_BIT, GL_COLOR_MATERIAL, \
                      GL_DEPTH_BUFFER_BIT, GL_DEPTH_TEST, GL_FRONT_AND_BACK, GL_LESS, GL_LIGHT0, GL_LIGHTING, \
                      GL_MODELVIEW, GL_MODELVIEW_MATRIX, GL_POSITION, GL_PROJECTION, GL_SPOT_DIRECTION
from OpenGL.constants import GLfloat_3, GLfloat_4
from OpenGL.GLU import gluPerspective, gluUnProject
from OpenGL.GLUT import glutCreateWindow, glutDisplayFunc, glutGet, glutInit, glutInitDisplayMode, \
                        glutInitWindowSize, glutMainLoop, \
                        GLUT_SINGLE, GLUT_RGB, GLUT_WINDOW_HEIGHT, GLUT_WINDOW_WIDTH

import numpy
from numpy.linalg import norm, inv

from interaction import Interaction
from primitive import init_primitives, G_OBJ_PLANE
from node import Sphere, Cube
from scene import Scene


class Viewer(object):
    def __init__(self):
        """ Initialize the viewer. """
        self.init_interface()
        self.init_opengl()
        self.init_scene()
        self.init_interaction()
        init_primitives()

    def init_interface(self):
        """ initialize the window and register the render function """
        glutInit()
        glutInitWindowSize(640, 480)
        glutCreateWindow("3D Modeller")
        glutInitDisplayMode(GLUT_SINGLE | GLUT_RGB)
        glutDisplayFunc(self.render)

    def init_interaction(self):
        """ init user interaction and callbacks """
        self.interaction = Interaction()
        self.interaction.register_callback('pick', self.pick)
        self.interaction.register_callback('move', self.move)
        self.interaction.register_callback('place', self.place)
        self.interaction.register_callback('rotate_color', self.rotate_color)
        self.interaction.register_callback('scale', self.scale)

    def init_scene(self):
        """ initialize the scene object and initial scene """
        self.scene = Scene()
        self.initial_scene()

    def init_opengl(self):
        """ initialize the opengl settings to render the scene """
        self.inverseModelView = numpy.identity(4)
        self.modelView = numpy.identity(4)

        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)

        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, GLfloat_4(0, 0, 1, 0))
        glLightfv(GL_LIGHT0, GL_SPOT_DIRECTION, GLfloat_3(0, 0, -1))

        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glEnable(GL_COLOR_MATERIAL)
        glClearColor(1.0, 1.0, 1.0, 0.0)

    def main_loop(self):
        glutMainLoop()

    def render(self):
        """ The render pass for the scene """
        self.init_view()

        # Enable lighting and color
        glEnable(GL_LIGHTING)

        glClearColor(0.4, 0.4, 0.4, 0.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Load the modelview matrix from the current state of the trackball
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        loc = self.interaction.translation
        glTranslated(-loc[0], -loc[1], -loc[2])
        glMultMatrixf(self.interaction.trackball.matrix)

        # store the inverse of the current modelview.
        currentModelView = numpy.array(glGetFloatv(GL_MODELVIEW_MATRIX))
        self.modelView = numpy.transpose(currentModelView)
        self.inverseModelView = inv(numpy.transpose(currentModelView))

        # render the scene. This will call the render function for each object in the scene
        self.scene.render()

        # draw the grid
        glDisable(GL_LIGHTING)
        glCallList(G_OBJ_PLANE)
        glPopMatrix()

        # flush the buffers so that the scene can be drawn
        glFlush()

    def init_view(self):
        """ initialize the projection matrix """
        xSize, ySize = glutGet(GLUT_WINDOW_WIDTH), glutGet(GLUT_WINDOW_HEIGHT)
        aspect_ratio = float(xSize) / float(ySize)

        # load the projection matrix. Always the same
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        glViewport(0, 0, xSize, ySize)
        gluPerspective(70, aspect_ratio, 0.1, 1000.0)
        glTranslated(0, 0, -15)

    def initial_scene(self):
        cube_node = Cube()
        cube_node.translate(2, 0, 2)
        cube_node.color_index = 2
        self.scene.add_node(cube_node)

        sphere_node = Sphere()
        sphere_node.translate(-2, 0, 2)
        sphere_node.color_index = 3
        self.scene.add_node(sphere_node)

        sphere_node_2 = Sphere()
        sphere_node_2.translate(-2, 0, -2)
        sphere_node_2.color_index = 1
        self.scene.add_node(sphere_node_2)

    def get_ray(self, x, y):
        """ Generate a ray beginning at the near plane, in the direction that the x, y coordinates are facing
            Consumes: x, y coordinates of mouse on screen
            Return: start, direction of the ray """
        self.init_view()

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # get two points on the line.
        start = numpy.array(gluUnProject(x, y, 0.001))
        end = numpy.array(gluUnProject(x, y, 0.999))

        # convert those points into a ray
        direction = end - start
        direction = direction / norm(direction)

        return (start, direction)

    def pick(self, x, y):
        """ Execute pick of an object. Selects an object in the scene. """
        start, direction = self.get_ray(x, y)
        self.scene.pick(start, direction, self.modelView)

    def move(self, x, y):
        """ Execute a move command on the scene. """
        start, direction = self.get_ray(x, y)
        self.scene.move(start, direction, self.inverseModelView)

    def place(self, shape, x, y):
        """ Execute a placement of a new primitive into the scene. """
        start, direction = self.get_ray(x, y)
        self.scene.place(shape, start, direction, self.inverseModelView)

    def rotate_color(self, forward):
        """ Rotate the color of the selected Node. Boolean 'forward' indicates direction of rotation. """
        self.scene.rotate_color(forward)

    def scale(self, up):
        """ Scale the selected Node. Boolean up indicates scaling larger."""
        self.scene.scale(up)

if __name__ == "__main__":
    viewer = Viewer()
    viewer.main_loop()

########NEW FILE########
__FILENAME__ = objmodel
MISSING = object()

class Base(object):
    """ The base class that all of the object model classes inherit from. """

    def __init__(self, cls):
        """ Every object has a class. """
        self.cls = cls

    def read_attr(self, fieldname):
        """ read field 'fieldname' out of the object """
        return self._read_dict(fieldname)

    def write_attr(self, fieldname, value):
        """ write field 'fieldname' into the object """
        self._write_dict(fieldname, value)

    def isinstance(self, cls):
        """ return True if the object is an instance of class cls """
        return self.cls.issubclass(cls)

    def send(self, methname, *args):
        """ send message 'methname' with arguments `args` to object """
        meth = self.cls._read_from_class(methname)
        return meth(self, *args)

    def _read_dict(self, fieldname):
        """ read an field 'fieldname' out of the object's dict """
        return MISSING

    def _write_dict(self, fieldname, value):
        """ write a field 'fieldname' into the object's dict """
        raise AttributeError


class BaseWithDict(Base):
    def __init__(self, cls, fields):
        Base.__init__(self, cls)
        self._fields = fields

    def _read_dict(self, fieldname):
        return self._fields.get(fieldname, MISSING)

    def _write_dict(self, fieldname, value):
        self._fields[fieldname] = value


class Instance(BaseWithDict):
    """Instance of a user-defined class. """

    def __init__(self, cls):
        assert isinstance(cls, Class)
        BaseWithDict.__init__(self, cls, {})


class Class(BaseWithDict):
    """ A User-defined class. """

    def __init__(self, name, base_class, fields, metaclass):
        BaseWithDict.__init__(self, metaclass, fields)
        self.name = name
        self.base_class = base_class

    def mro(self):
        """ compute the mro (method resolution order) of the class """
        if self.base_class is None:
            return [self]
        else:
            return [self] + self.base_class.mro()

    def issubclass(self, cls):
        """ is self a subclass of cls? """
        return cls in self.mro()

    def _read_from_class(self, methname):
        for cls in self.mro():
            if methname in cls._fields:
                return cls._fields[methname]
        return MISSING

# set up the base hierarchy like in Python (the ObjVLisp model)
# the ultimate base class is OBJECT
OBJECT = Class("object", None, {}, None)
# TYPE is a subclass of OBJECT
TYPE = Class("type", OBJECT, {}, None)
# TYPE is an instance of itself
TYPE.cls = TYPE
# OBJECT is an instance of TYPE
OBJECT.cls = TYPE

########NEW FILE########
__FILENAME__ = test_objmodel
from objmodel import Class, Instance, TYPE, OBJECT

def test_isinstance():
    # Python code
    class A(object):
        pass
    class B(A):
        pass
    b = B()
    assert isinstance(b, B)
    assert isinstance(b, A)
    assert isinstance(b, object)
    assert not isinstance(b, type)

    # Object model code
    A = Class("A", OBJECT, {}, TYPE)
    B = Class("B", A, {}, TYPE)
    b = Instance(B)
    assert b.isinstance(B)
    assert b.isinstance(A)
    assert b.isinstance(OBJECT)
    assert not b.isinstance(TYPE)


def test_read_write_field():
    # Python code
    class A(object):
        pass
    obj = A()
    obj.a = 1
    assert obj.a == 1

    obj.b = 5
    assert obj.a == 1
    assert obj.b == 5

    obj.a = 2
    assert obj.a == 2
    assert obj.b == 5

    # Object model code
    A = Class("A", OBJECT, {}, TYPE)
    obj = Instance(A)
    obj.write_attr("a", 1)
    assert obj.read_attr("a") == 1

    obj.write_attr("b", 5)
    assert obj.read_attr("a") == 1
    assert obj.read_attr("b") == 5

    obj.write_attr("a", 2)
    assert obj.read_attr("a") == 2
    assert obj.read_attr("b") == 5


def test_read_write_field_class():
    # classes are objects too
    # Python code
    class A(object):
        pass
    A.a = 1
    assert A.a == 1
    A.a = 6
    assert A.a == 6

    # Object model code
    A = Class("A", OBJECT, {}, TYPE)
    A.write_attr("a", 1)
    assert A.read_attr("a") == 1
    A.write_attr("a", 5)
    assert A.read_attr("a") == 5


def test_send_simple():
    # Python code
    class A(object):
        def f(self):
            return self.x + 1
    obj = A()
    obj.x = 1
    assert obj.f() == 2

    class B(A):
        pass
    obj = B()
    obj.x = 1
    assert obj.f() == 2 # works on subclass too

    # Object model code
    def f(self):
        return self.read_attr("x") + 1
    A = Class("A", OBJECT, {"f": f}, TYPE)
    obj = Instance(A)
    obj.write_attr("x", 1)
    assert obj.send("f") == 2

    B = Class("B", A, {}, TYPE)
    obj = Instance(B)
    obj.write_attr("x", 2)
    assert obj.send("f") == 3


def test_send_subclassing_and_arguments():
    # Python code
    class A(object):
        def g(self, arg):
            return self.x + arg
    obj = A()
    obj.x = 1
    assert obj.g(4) == 5

    class B(A):
        def g(self, arg):
            return self.x + arg * 2
    obj = B()
    obj.x = 4
    assert obj.g(4) == 12

    # Object model code
    def g_A(self, arg):
        return self.read_attr("x") + arg
    A = Class("A", OBJECT, {"g": g_A}, TYPE)
    obj = Instance(A)
    obj.write_attr("x", 1)
    assert obj.send("g", 4) == 5

    def g_B(self, arg):
        return self.read_attr("x") + arg * 2
    B = Class("B", A, {"g": g_B}, TYPE)
    obj = Instance(B)
    obj.write_attr("x", 4)
    assert obj.send("g", 4) == 12


########NEW FILE########
__FILENAME__ = objmodel
MISSING = object()

class Base(object):
    """ The base class that all of the object model classes inherit from. """

    def __init__(self, cls):
        """ Every object has a class. """
        self.cls = cls

    def read_attr(self, fieldname):
        """ read field 'fieldname' out of the object """
        result = self._read_dict(fieldname)
        if result is not MISSING:
            return result
        result = self.cls._read_from_class(fieldname)
        if callable(result):
            return _make_boundmethod(result, self)
        if result is MISSING:
            raise AttributeError(fieldname)
        return result

    def write_attr(self, fieldname, value):
        """ write field 'fieldname' into the object """
        self._write_dict(fieldname, value)

    def isinstance(self, cls):
        """ return True if the object is an instance of class cls """
        return self.cls.issubclass(cls)

    def send(self, methname, *args):
        """ send message 'methname' with arguments `args` to object """
        meth = self.read_attr(methname)
        return meth(*args)

    def _read_dict(self, fieldname):
        """ read an field 'fieldname' out of the object's dict """
        return MISSING

    def _write_dict(self, fieldname, value):
        """ write a field 'fieldname' into the object's dict """
        raise AttributeError


class BaseWithDict(Base):
    def __init__(self, cls, fields):
        Base.__init__(self, cls)
        self._fields = fields

    def _read_dict(self, fieldname):
        return self._fields.get(fieldname, MISSING)

    def _write_dict(self, fieldname, value):
        self._fields[fieldname] = value


class Instance(BaseWithDict):
    """Instance of a user-defined class. """

    def __init__(self, cls):
        assert isinstance(cls, Class)
        BaseWithDict.__init__(self, cls, {})


def _make_boundmethod(meth, self):
    def bound(*args):
        return meth(self, *args)
    return bound

class Class(BaseWithDict):
    """ A User-defined class. """

    def __init__(self, name, base_class, fields, metaclass):
        BaseWithDict.__init__(self, metaclass, fields)
        self.name = name
        self.base_class = base_class

    def mro(self):
        """ compute the mro (method resolution order) of the class """
        if self.base_class is None:
            return [self]
        else:
            return [self] + self.base_class.mro()

    def issubclass(self, cls):
        """ is self a subclass of cls? """
        return cls in self.mro()

    def _read_from_class(self, methname):
        for cls in self.mro():
            if methname in cls._fields:
                return cls._fields[methname]
        return MISSING

# set up the base hierarchy like in Python (the ObjVLisp model)
# the ultimate base class is OBJECT
OBJECT = Class("object", None, {}, None)
# TYPE is a subclass of OBJECT
TYPE = Class("type", OBJECT, {}, None)
# TYPE is an instance of itself
TYPE.cls = TYPE
# OBJECT is an instance of TYPE
OBJECT.cls = TYPE

########NEW FILE########
__FILENAME__ = test_objmodel
from objmodel import Class, Instance, TYPE, OBJECT

def test_isinstance():
    # Python code
    class A(object):
        pass
    class B(A):
        pass
    b = B()
    assert isinstance(b, B)
    assert isinstance(b, A)
    assert isinstance(b, object)
    assert not isinstance(b, type)

    # Object model code
    A = Class("A", OBJECT, {}, TYPE)
    B = Class("B", A, {}, TYPE)
    b = Instance(B)
    assert b.isinstance(B)
    assert b.isinstance(A)
    assert b.isinstance(OBJECT)
    assert not b.isinstance(TYPE)


def test_read_write_field():
    # Python code
    class A(object):
        pass
    obj = A()
    obj.a = 1
    assert obj.a == 1

    obj.b = 5
    assert obj.a == 1
    assert obj.b == 5

    obj.a = 2
    assert obj.a == 2
    assert obj.b == 5

    # Object model code
    A = Class("A", OBJECT, {}, TYPE)
    obj = Instance(A)
    obj.write_attr("a", 1)
    assert obj.read_attr("a") == 1

    obj.write_attr("b", 5)
    assert obj.read_attr("a") == 1
    assert obj.read_attr("b") == 5

    obj.write_attr("a", 2)
    assert obj.read_attr("a") == 2
    assert obj.read_attr("b") == 5


def test_read_write_field_class():
    # classes are objects too
    # Python code
    class A(object):
        pass
    A.a = 1
    assert A.a == 1
    A.a = 6
    assert A.a == 6

    # Object model code
    A = Class("A", OBJECT, {}, TYPE)
    A.write_attr("a", 1)
    assert A.read_attr("a") == 1
    A.write_attr("a", 5)
    assert A.read_attr("a") == 5


def test_send_simple():
    # Python code
    class A(object):
        def f(self):
            return self.x + 1
    obj = A()
    obj.x = 1
    assert obj.f() == 2

    class B(A):
        pass
    obj = B()
    obj.x = 1
    assert obj.f() == 2 # works on subclass too

    # Object model code
    def f(self):
        return self.read_attr("x") + 1
    A = Class("A", OBJECT, {"f": f}, TYPE)
    obj = Instance(A)
    obj.write_attr("x", 1)
    assert obj.send("f") == 2

    B = Class("B", A, {}, TYPE)
    obj = Instance(B)
    obj.write_attr("x", 2)
    assert obj.send("f") == 3


def test_send_subclassing_and_arguments():
    # Python code
    class A(object):
        def g(self, arg):
            return self.x + arg
    obj = A()
    obj.x = 1
    assert obj.g(4) == 5

    class B(A):
        def g(self, arg):
            return self.x + arg * 2
    obj = B()
    obj.x = 4
    assert obj.g(4) == 12

    # Object model code
    def g_A(self, arg):
        return self.read_attr("x") + arg
    A = Class("A", OBJECT, {"g": g_A}, TYPE)
    obj = Instance(A)
    obj.write_attr("x", 1)
    assert obj.send("g", 4) == 5

    def g_B(self, arg):
        return self.read_attr("x") + arg * 2
    B = Class("B", A, {"g": g_B}, TYPE)
    obj = Instance(B)
    obj.write_attr("x", 4)
    assert obj.send("g", 4) == 12


# ____________________________________________________________
# new tests

def test_bound_method():
    # Python code
    class A(object):
        def f(self, a):
            return self.x + a + 1
    obj = A()
    obj.x = 2
    m = obj.f
    assert m(4) == 7

    class B(A):
        pass
    obj = B()
    obj.x = 1
    m = obj.f
    assert m(10) == 12 # works on subclass too

    # Object model code
    def f(self, a):
        return self.read_attr("x") + a + 1
    A = Class("A", OBJECT, {"f": f}, TYPE)
    obj = Instance(A)
    obj.write_attr("x", 2)
    m = obj.read_attr("f")
    assert m(4) == 7

    B = Class("B", A, {}, TYPE)
    obj = Instance(B)
    obj.write_attr("x", 1)
    m = obj.read_attr("f")
    assert m(10) == 12


########NEW FILE########
__FILENAME__ = objmodel
MISSING = object()

class Base(object):
    """ The base class that all of the object model classes inherit from. """

    def __init__(self, cls):
        """ Every object has a class. """
        self.cls = cls

    def read_attr(self, fieldname):
        """ read field 'fieldname' out of the object """
        result = self._read_dict(fieldname)
        if result is not MISSING:
            return result
        result = self.cls._read_from_class(fieldname)
        if hasattr(result, "__get__"):
            return _make_boundmethod(result, self, self)
        if result is not MISSING:
            return result
        meth = self.cls._read_from_class("__getattr__")
        if meth is MISSING:
            raise AttributeError(fieldname)
        return meth(self, fieldname)

    def write_attr(self, fieldname, value):
        """ write field 'fieldname' into the object """
        meth = self.cls._read_from_class("__setattr__")
        return meth(self, fieldname, value)

    def isinstance(self, cls):
        """ return True if the object is an instance of class cls """
        return self.cls.issubclass(cls)

    def send(self, methname, *args):
        """ send message 'methname' with arguments `args` to object """
        meth = self.read_attr(methname)
        return meth(*args)

    def _read_dict(self, fieldname):
        """ read an field 'fieldname' out of the object's dict """
        return MISSING

    def _write_dict(self, fieldname, value):
        """ write a field 'fieldname' into the object's dict """
        raise AttributeError

def __setattr__OBJECT(self, fieldname, value):
    self._write_dict(fieldname, value)


class BaseWithDict(Base):
    def __init__(self, cls, fields):
        Base.__init__(self, cls)
        self._fields = fields

    def _read_dict(self, fieldname):
        return self._fields.get(fieldname, MISSING)

    def _write_dict(self, fieldname, value):
        self._fields[fieldname] = value


class Instance(BaseWithDict):
    """Instance of a user-defined class. """

    def __init__(self, cls):
        assert isinstance(cls, Class)
        BaseWithDict.__init__(self, cls, {})


def _make_boundmethod(meth, cls, self):
    return meth.__get__(self, cls)

class Class(BaseWithDict):
    """ A User-defined class. """

    def __init__(self, name, base_class, fields, metaclass):
        BaseWithDict.__init__(self, metaclass, fields)
        self.name = name
        self.base_class = base_class

    def mro(self):
        """ compute the mro (method resolution order) of the class """
        if self.base_class is None:
            return [self]
        else:
            return [self] + self.base_class.mro()

    def issubclass(self, cls):
        """ is self a subclass of cls? """
        return cls in self.mro()

    def _read_from_class(self, methname):
        for cls in self.mro():
            if methname in cls._fields:
                return cls._fields[methname]
        return MISSING


# set up the base hierarchy like in Python (the ObjVLisp model)
# the ultimate base class is OBJECT
OBJECT = Class("object", None, {"__setattr__": __setattr__OBJECT}, None)
# TYPE is a subclass of OBJECT
TYPE = Class("type", OBJECT, {}, None)
# TYPE is an instance of itself
TYPE.cls = TYPE
# OBJECT is an instance of TYPE
OBJECT.cls = TYPE

########NEW FILE########
__FILENAME__ = test_objmodel
from objmodel import Class, Instance, TYPE, OBJECT

def test_isinstance():
    # Python code
    class A(object):
        pass
    class B(A):
        pass
    b = B()
    assert isinstance(b, B)
    assert isinstance(b, A)
    assert isinstance(b, object)
    assert not isinstance(b, type)

    # Object model code
    A = Class("A", OBJECT, {}, TYPE)
    B = Class("B", A, {}, TYPE)
    b = Instance(B)
    assert b.isinstance(B)
    assert b.isinstance(A)
    assert b.isinstance(OBJECT)
    assert not b.isinstance(TYPE)


def test_read_write_field():
    # Python code
    class A(object):
        pass
    obj = A()
    obj.a = 1
    assert obj.a == 1

    obj.b = 5
    assert obj.a == 1
    assert obj.b == 5

    obj.a = 2
    assert obj.a == 2
    assert obj.b == 5

    # Object model code
    A = Class("A", OBJECT, {}, TYPE)
    obj = Instance(A)
    obj.write_attr("a", 1)
    assert obj.read_attr("a") == 1

    obj.write_attr("b", 5)
    assert obj.read_attr("a") == 1
    assert obj.read_attr("b") == 5

    obj.write_attr("a", 2)
    assert obj.read_attr("a") == 2
    assert obj.read_attr("b") == 5


def test_read_write_field_class():
    # classes are objects too
    # Python code
    class A(object):
        pass
    A.a = 1
    assert A.a == 1
    A.a = 6
    assert A.a == 6

    # Object model code
    A = Class("A", OBJECT, {}, TYPE)
    A.write_attr("a", 1)
    assert A.read_attr("a") == 1
    A.write_attr("a", 5)
    assert A.read_attr("a") == 5


def test_send_simple():
    # Python code
    class A(object):
        def f(self):
            return self.x + 1
    obj = A()
    obj.x = 1
    assert obj.f() == 2

    class B(A):
        pass
    obj = B()
    obj.x = 1
    assert obj.f() == 2 # works on subclass too

    # Object model code
    def f(self):
        return self.read_attr("x") + 1
    A = Class("A", OBJECT, {"f": f}, TYPE)
    obj = Instance(A)
    obj.write_attr("x", 1)
    assert obj.send("f") == 2

    B = Class("B", A, {}, TYPE)
    obj = Instance(B)
    obj.write_attr("x", 2)
    assert obj.send("f") == 3


def test_send_subclassing_and_arguments():
    # Python code
    class A(object):
        def g(self, arg):
            return self.x + arg
    obj = A()
    obj.x = 1
    assert obj.g(4) == 5

    class B(A):
        def g(self, arg):
            return self.x + arg * 2
    obj = B()
    obj.x = 4
    assert obj.g(4) == 12

    # Object model code
    def g_A(self, arg):
        return self.read_attr("x") + arg
    A = Class("A", OBJECT, {"g": g_A}, TYPE)
    obj = Instance(A)
    obj.write_attr("x", 1)
    assert obj.send("g", 4) == 5

    def g_B(self, arg):
        return self.read_attr("x") + arg * 2
    B = Class("B", A, {"g": g_B}, TYPE)
    obj = Instance(B)
    obj.write_attr("x", 4)
    assert obj.send("g", 4) == 12


def test_bound_method():
    # Python code
    class A(object):
        def f(self, a):
            return self.x + a + 1
    obj = A()
    obj.x = 2
    m = obj.f
    assert m(4) == 7

    class B(A):
        pass
    obj = B()
    obj.x = 1
    m = obj.f
    assert m(10) == 12 # works on subclass too

    # Object model code
    def f(self, a):
        return self.read_attr("x") + a + 1
    A = Class("A", OBJECT, {"f": f}, TYPE)
    obj = Instance(A)
    obj.write_attr("x", 2)
    m = obj.read_attr("f")
    assert m(4) == 7

    B = Class("B", A, {}, TYPE)
    obj = Instance(B)
    obj.write_attr("x", 1)
    m = obj.read_attr("f")
    assert m(10) == 12

# ____________________________________________________________
# new tests

def test_getattr():
    # Python code
    class A(object):
        def __getattr__(self, name):
            if name == "fahrenheit":
                return self.celsius * 9. / 5. + 32
            raise AttributeError(name)

        def __setattr__(self, name, value):
            if name == "fahrenheit":
                self.celsius = (value - 32) * 5. / 9.
            else:
                # call the base implementation
                object.__setattr__(self, name, value)
    obj = A()
    obj.celsius = 30
    assert obj.fahrenheit == 86
    obj.celsius = 40
    assert obj.fahrenheit == 104

    obj.fahrenheit = 86
    assert obj.celsius == 30
    assert obj.fahrenheit == 86

    # Object model code
    def __getattr__(self, name):
        if name == "fahrenheit":
            return self.read_attr("celsius") * 9. / 5. + 32
        raise AttributeError(name)
    def __setattr__(self, name, value):
        if name == "fahrenheit":
            self.write_attr("celsius", (value - 32) * 5. / 9.)
        else:
            # call the base implementation
            OBJECT.read_attr("__setattr__")(self, name, value)

    A = Class("A", OBJECT, {"__getattr__": __getattr__, "__setattr__": __setattr__}, TYPE)
    obj = Instance(A)
    obj.write_attr("celsius", 30)
    assert obj.read_attr("fahrenheit") == 86
    obj.write_attr("celsius", 40)
    assert obj.read_attr("fahrenheit") == 104
    obj.write_attr("fahrenheit", 86)
    assert obj.read_attr("celsius") == 30
    assert obj.read_attr("fahrenheit") == 86


def test_get():
    # Python code
    class FahrenheitGetter(object):
        def __get__(self, inst, cls):
            return inst.celsius * 9. / 5. + 32

    class A(object):
        fahrenheit = FahrenheitGetter()
    obj = A()
    obj.celsius = 30
    assert obj.fahrenheit == 86

    # Object model code
    class FahrenheitGetter(object):
        def __get__(self, inst, cls):
            return inst.read_attr("celsius") * 9. / 5. + 32

    A = Class("A", OBJECT, {"fahrenheit": FahrenheitGetter()}, TYPE)
    obj = Instance(A)
    obj.write_attr("celsius", 30)
    assert obj.read_attr("fahrenheit") == 86


########NEW FILE########
__FILENAME__ = objmodel
MISSING = object()

class Map(object):
    def __init__(self, attrs):
        self.attrs = attrs
        self.next_maps = {}

    def get_index(self, fieldname):
        return self.attrs.get(fieldname, -1)

    def next_map(self, fieldname):
        if fieldname in self.next_maps:
            return self.next_maps[fieldname]
        attrs = self.attrs.copy()
        assert fieldname not in attrs
        attrs[fieldname] = len(attrs)
        result = self.next_maps[fieldname] = Map(attrs)
        return result

EMPTY_MAP = Map({})

class Base(object):
    """ The base class that all of the object model classes inherit from. """

    def __init__(self, cls):
        """ Every object has a class. """
        self.cls = cls

    def read_attr(self, fieldname):
        """ read field 'fieldname' out of the object """
        result = self._read_dict(fieldname)
        if result is not MISSING:
            return result
        result = self.cls._read_from_class(fieldname)
        if hasattr(result, "__get__"):
            return _make_boundmethod(result, self, self)
        if result is not MISSING:
            return result
        meth = self.cls._read_from_class("__getattr__")
        if meth is MISSING:
            raise AttributeError(fieldname)
        return meth(self, fieldname)

    def write_attr(self, fieldname, value):
        """ write field 'fieldname' into the object """
        meth = self.cls._read_from_class("__setattr__")
        return meth(self, fieldname, value)

    def isinstance(self, cls):
        """ return True if the object is an instance of class cls """
        return self.cls.issubclass(cls)

    def send(self, methname, *args):
        """ send message 'methname' with arguments `args` to object """
        meth = self.read_attr(methname)
        return meth(*args)

    def _read_dict(self, fieldname):
        """ read an field 'fieldname' out of the object's dict """
        return MISSING

    def _write_dict(self, fieldname, value):
        """ write a field 'fieldname' into the object's dict """
        raise AttributeError

def __setattr__OBJECT(self, fieldname, value):
    self._write_dict(fieldname, value)


class BaseWithDict(Base):
    def __init__(self, cls, fields):
        Base.__init__(self, cls)
        self._fields = fields

    def _read_dict(self, fieldname):
        return self._fields.get(fieldname, MISSING)

    def _write_dict(self, fieldname, value):
        self._fields[fieldname] = value


class Instance(BaseWithDict):
    """Instance of a user-defined class. """

    def __init__(self, cls):
        assert isinstance(cls, Class)
        Base.__init__(self, cls)
        self.map = EMPTY_MAP
        self.storage = []

    def _read_dict(self, fieldname):
        index = self.map.get_index(fieldname)
        if index == -1:
            return MISSING
        return self.storage[index]

    def _write_dict(self, fieldname, value):
        index = self.map.get_index(fieldname)
        if index != -1:
            self.storage[index] = value
        else:
            new_map = self.map.next_map(fieldname)
            self.storage.append(value)
            self.map = new_map


def _make_boundmethod(meth, cls, self):
    return meth.__get__(self, cls)

class Class(BaseWithDict):
    """ A User-defined class. """

    def __init__(self, name, base_class, fields, metaclass):
        BaseWithDict.__init__(self, metaclass, fields)
        self.name = name
        self.base_class = base_class

    def mro(self):
        """ compute the mro (method resolution order) of the class """
        if self.base_class is None:
            return [self]
        else:
            return [self] + self.base_class.mro()

    def issubclass(self, cls):
        """ is self a subclass of cls? """
        return cls in self.mro()

    def _read_from_class(self, methname):
        for cls in self.mro():
            if methname in cls._fields:
                return cls._fields[methname]
        return MISSING


# set up the base hierarchy like in Python (the ObjVLisp model)
# the ultimate base class is OBJECT
OBJECT = Class("object", None, {"__setattr__": __setattr__OBJECT}, None)
# TYPE is a subclass of OBJECT
TYPE = Class("type", OBJECT, {}, None)
# TYPE is an instance of itself
TYPE.cls = TYPE
# OBJECT is an instance of TYPE
OBJECT.cls = TYPE

########NEW FILE########
__FILENAME__ = test_objmodel
from objmodel import Class, Instance, TYPE, OBJECT

def test_isinstance():
    # Python code
    class A(object):
        pass
    class B(A):
        pass
    b = B()
    assert isinstance(b, B)
    assert isinstance(b, A)
    assert isinstance(b, object)
    assert not isinstance(b, type)

    # Object model code
    A = Class("A", OBJECT, {}, TYPE)
    B = Class("B", A, {}, TYPE)
    b = Instance(B)
    assert b.isinstance(B)
    assert b.isinstance(A)
    assert b.isinstance(OBJECT)
    assert not b.isinstance(TYPE)


def test_read_write_field():
    # Python code
    class A(object):
        pass
    obj = A()
    obj.a = 1
    assert obj.a == 1

    obj.b = 5
    assert obj.a == 1
    assert obj.b == 5

    obj.a = 2
    assert obj.a == 2
    assert obj.b == 5

    # Object model code
    A = Class("A", OBJECT, {}, TYPE)
    obj = Instance(A)
    obj.write_attr("a", 1)
    assert obj.read_attr("a") == 1

    obj.write_attr("b", 5)
    assert obj.read_attr("a") == 1
    assert obj.read_attr("b") == 5

    obj.write_attr("a", 2)
    assert obj.read_attr("a") == 2
    assert obj.read_attr("b") == 5


def test_read_write_field_class():
    # classes are objects too
    # Python code
    class A(object):
        pass
    A.a = 1
    assert A.a == 1
    A.a = 6
    assert A.a == 6

    # Object model code
    A = Class("A", OBJECT, {}, TYPE)
    A.write_attr("a", 1)
    assert A.read_attr("a") == 1
    A.write_attr("a", 5)
    assert A.read_attr("a") == 5


def test_send_simple():
    # Python code
    class A(object):
        def f(self):
            return self.x + 1
    obj = A()
    obj.x = 1
    assert obj.f() == 2

    class B(A):
        pass
    obj = B()
    obj.x = 1
    assert obj.f() == 2 # works on subclass too

    # Object model code
    def f(self):
        return self.read_attr("x") + 1
    A = Class("A", OBJECT, {"f": f}, TYPE)
    obj = Instance(A)
    obj.write_attr("x", 1)
    assert obj.send("f") == 2

    B = Class("B", A, {}, TYPE)
    obj = Instance(B)
    obj.write_attr("x", 2)
    assert obj.send("f") == 3


def test_send_subclassing_and_arguments():
    # Python code
    class A(object):
        def g(self, arg):
            return self.x + arg
    obj = A()
    obj.x = 1
    assert obj.g(4) == 5

    class B(A):
        def g(self, arg):
            return self.x + arg * 2
    obj = B()
    obj.x = 4
    assert obj.g(4) == 12

    # Object model code
    def g_A(self, arg):
        return self.read_attr("x") + arg
    A = Class("A", OBJECT, {"g": g_A}, TYPE)
    obj = Instance(A)
    obj.write_attr("x", 1)
    assert obj.send("g", 4) == 5

    def g_B(self, arg):
        return self.read_attr("x") + arg * 2
    B = Class("B", A, {"g": g_B}, TYPE)
    obj = Instance(B)
    obj.write_attr("x", 4)
    assert obj.send("g", 4) == 12


def test_bound_method():
    # Python code
    class A(object):
        def f(self, a):
            return self.x + a + 1
    obj = A()
    obj.x = 2
    m = obj.f
    assert m(4) == 7

    class B(A):
        pass
    obj = B()
    obj.x = 1
    m = obj.f
    assert m(10) == 12 # works on subclass too

    # Object model code
    def f(self, a):
        return self.read_attr("x") + a + 1
    A = Class("A", OBJECT, {"f": f}, TYPE)
    obj = Instance(A)
    obj.write_attr("x", 2)
    m = obj.read_attr("f")
    assert m(4) == 7

    B = Class("B", A, {}, TYPE)
    obj = Instance(B)
    obj.write_attr("x", 1)
    m = obj.read_attr("f")
    assert m(10) == 12


def test_getattr():
    # Python code
    class A(object):
        def __getattr__(self, name):
            if name == "fahrenheit":
                return self.celsius * 9. / 5. + 32
            raise AttributeError(name)

        def __setattr__(self, name, value):
            if name == "fahrenheit":
                self.celsius = (value - 32) * 5. / 9.
            else:
                # call the base implementation
                object.__setattr__(self, name, value)
    obj = A()
    obj.celsius = 30
    assert obj.fahrenheit == 86
    obj.celsius = 40
    assert obj.fahrenheit == 104

    obj.fahrenheit = 86
    assert obj.celsius == 30
    assert obj.fahrenheit == 86

    # Object model code
    def __getattr__(self, name):
        if name == "fahrenheit":
            return self.read_attr("celsius") * 9. / 5. + 32
        raise AttributeError(name)
    def __setattr__(self, name, value):
        if name == "fahrenheit":
            self.write_attr("celsius", (value - 32) * 5. / 9.)
        else:
            # call the base implementation
            OBJECT.read_attr("__setattr__")(self, name, value)

    A = Class("A", OBJECT, {"__getattr__": __getattr__, "__setattr__": __setattr__}, TYPE)
    obj = Instance(A)
    obj.write_attr("celsius", 30)
    assert obj.read_attr("fahrenheit") == 86
    obj.write_attr("celsius", 40)
    assert obj.read_attr("fahrenheit") == 104
    obj.write_attr("fahrenheit", 86)
    assert obj.read_attr("celsius") == 30
    assert obj.read_attr("fahrenheit") == 86


def test_get():
    # Python code
    class FahrenheitGetter(object):
        def __get__(self, inst, cls):
            return inst.celsius * 9. / 5. + 32

    class A(object):
        fahrenheit = FahrenheitGetter()
    obj = A()
    obj.celsius = 30
    assert obj.fahrenheit == 86

    # Object model code
    class FahrenheitGetter(object):
        def __get__(self, inst, cls):
            return inst.read_attr("celsius") * 9. / 5. + 32

    def __getattr__(self, name):
        if name == "fahrenheit":
            return self.read_attr("celsius") * 9. / 5. + 32
        raise AttributeError(name)

    A = Class("A", OBJECT, {"fahrenheit": FahrenheitGetter()}, TYPE)
    obj = Instance(A)
    obj.write_attr("celsius", 30)
    assert obj.read_attr("fahrenheit") == 86


# ____________________________________________________________
# new tests

def test_maps():
    # white box test inspecting the implementation
    Point = Class("Point", OBJECT, {}, TYPE)
    p1 = Instance(Point)
    p1.write_attr("x", 1)
    p1.write_attr("y", 2)

    p2 = Instance(Point)
    p2.write_attr("x", 5)
    p2.write_attr("y", 6)
    assert p1.map is p2.map
    assert p1.storage == [1, 2]
    assert p2.storage == [5, 6]

    p1.write_attr("x", -1)
    p1.write_attr("y", -2)
    assert p1.map is p2.map
    assert p1.storage == [-1, -2]

########NEW FILE########
__FILENAME__ = countlines
import os
import difflib

currdir = os.path.dirname(os.path.abspath(__file__))

dirs = [p for p in os.listdir(currdir) if os.path.isdir(p)]
dirs.sort()

total = 0

print dirs[0]
prev = {}
for fn in sorted(os.listdir(dirs[0])):
    fulln = os.path.join(dirs[0], fn)
    if not fn.endswith(".py") or not os.path.isfile(fulln):
        continue
    with file(fulln) as f:
        lines = f.readlines()
    print len(lines), fn
    total += len(lines)
    prev[fn] = lines

print
for d in dirs[1:]:
    print d
    for fn, prevlines in sorted(prev.items()):
        fulln = os.path.join(d, fn)
        with file(fulln) as f:
            lines = f.readlines()
        diffsize = len(list(difflib.unified_diff(prevlines, lines)))
        print diffsize, fn
        #print "".join(difflib.unified_diff(prevlines, lines))
        prev[fn] = lines
        total += diffsize
    print

print "------------"
print total, "total"

########NEW FILE########
__FILENAME__ = diff
import os

paths = sorted(p for p in os.listdir(".") if p.startswith("0"))
for i, d1 in enumerate(paths[:-1]):
    d2 = paths[i + 1]
    for fn in ["objmodel.py", "test_objmodel.py"]:
        fn1 = os.path.join(d1, fn)
        fn2 = os.path.join(d2, fn)
        os.system("diff -u %s %s | less" % (fn1, fn2))

########NEW FILE########
__FILENAME__ = neural_network_design
"""
In order to decide how many hidden nodes the hidden layer should have,
split up the data set into training and testing data and create networks
with various hidden node counts (5, 10, 15, ... 45), testing the performance
for each.

The best-performing node count is used in the actual system. If multiple counts
perform similarly, choose the smallest count for a smaller network with fewer computations.
"""

import numpy as np
from ocr import OCRNeuralNetwork
from sklearn.cross_validation import train_test_split

def test(data_matrix, data_labels, test_indices, nn):
    avg_sum = 0
    for j in xrange(100):
        correct_guess_count = 0
        for i in test_indices:
            test = data_matrix[i]
            prediction = nn.predict(test)
            if data_labels[i] == prediction:
                correct_guess_count += 1

        avg_sum += (correct_guess_count / float(len(test_indices)))
    return avg_sum / 100


# Load data samples and labels into matrix
data_matrix = np.loadtxt(open('data.csv', 'rb'), delimiter = ',').tolist()
data_labels = np.loadtxt(open('dataLabels.csv', 'rb')).tolist()

# Create training and testing sets.
train_indices, test_indices = train_test_split(list(range(5000)))

print "PERFORMANCE"
print "-----------"

# Try various number of hidden nodes and see what performs best
for i in xrange(5, 50, 5):
    nn = OCRNeuralNetwork(i, data_matrix, data_labels, train_indices, False)
    performance = str(test(data_matrix, data_labels, test_indices, nn))
    print "{i} Hidden Nodes: {val}".format(i=i, val=performance)
########NEW FILE########
__FILENAME__ = ocr
import csv
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
from numpy import matrix
from math import pow
from collections import namedtuple
import math
import random
import os
import json

"""
This class does some initial training of a neural network for predicting drawn
digits based on a data set in data_matrix and data_labels. It can then be used to
train the network further by calling train() with any array of data or to predict
what a drawn digit is by calling predict().

The weights that define the neural network can be saved to a file, NN_FILE_PATH,
to be reloaded upon initilization.
"""
class OCRNeuralNetwork:
    LEARNING_RATE = 0.1
    WIDTH_IN_PIXELS = 20
    NN_FILE_PATH = 'nn.json'

    def __init__(self, num_hidden_nodes, data_matrix, data_labels, training_indices, use_file=True):
        self.sigmoid = np.vectorize(self._sigmoid_scalar)
        self.sigmoid_prime = np.vectorize(self._sigmoid_prime_scalar)
        self._use_file = use_file
        self.data_matrix = data_matrix
        self.data_labels = data_labels

        if (not os.path.isfile(OCRNeuralNetwork.NN_FILE_PATH) or not use_file):
            # Step 1: Initialize weights to small numbers
            self.theta1 = self._rand_initialize_weights(400, num_hidden_nodes)
            self.theta2 = self._rand_initialize_weights(num_hidden_nodes, 10)
            self.input_layer_bias = self._rand_initialize_weights(1, num_hidden_nodes)
            self.hidden_layer_bias = self._rand_initialize_weights(1, 10)

            # Train using sample data
            TrainData = namedtuple('TrainData', ['y0', 'label'])
            self.train([TrainData(self.data_matrix[i], int(self.data_labels[i])) for i in training_indices])
            self.save()
        else:
            self._load()

    def _rand_initialize_weights(self, size_in, size_out):
        return [((x * 0.12) - 0.06) for x in np.random.rand(size_out, size_in)]

    # The sigmoid activation function. Operates on scalars.
    def _sigmoid_scalar(self, z):
        return 1 / (1 + math.e ** -z)

    def _sigmoid_prime_scalar(self, z):
        return self.sigmoid(z) * (1 - self.sigmoid(z))

    def _draw(self, sample):
        pixelArray = [sample[j:j+self.WIDTH_IN_PIXELS] for j in xrange(0, len(sample), self.WIDTH_IN_PIXELS)]
        plt.imshow(zip(*pixelArray), cmap = cm.Greys_r, interpolation="nearest")
        plt.show()

    def train(self, training_data_array):
        for data in training_data_array:
            # Step 2: Forward propagation
            y1 = np.dot(np.mat(self.theta1), np.mat(data['y0']).T)
            sum1 =  y1 + np.mat(self.input_layer_bias) # Add the bias
            y1 = self.sigmoid(sum1)

            y2 = np.dot(np.array(self.theta2), y1)
            y2 = np.add(y2, self.hidden_layer_bias) # Add the bias
            y2 = self.sigmoid(y2)

            # Step 3: Back propagation
            actual_vals = [0] * 10 # actual_vals is a python list for easy initialization and is later turned into an np matrix (2 lines down).
            actual_vals[data['label']] = 1
            output_errors = np.mat(actual_vals).T - np.mat(y2)
            hiddenErrors = np.multiply(np.dot(np.mat(self.theta2).T, output_errors), self.sigmoid_prime(sum1))

            # Step 4: Update weights
            self.theta1 += self.LEARNING_RATE * np.dot(np.mat(hiddenErrors), np.mat(data['y0']))
            self.theta2 += self.LEARNING_RATE * np.dot(np.mat(output_errors), np.mat(y1).T)
            self.hidden_layer_bias += self.LEARNING_RATE * output_errors
            self.input_layer_bias += self.LEARNING_RATE * hiddenErrors

    def predict(self, test):
        y1 = np.dot(np.mat(self.theta1), np.mat(test).T)
        y1 =  y1 + np.mat(self.input_layer_bias) # Add the bias
        y1 = self.sigmoid(y1)

        y2 = np.dot(np.array(self.theta2), y1)
        y2 = np.add(y2, self.hidden_layer_bias) # Add the bias
        y2 = self.sigmoid(y2)

        results = y2.T.tolist()[0]
        return results.index(max(results))

    def save(self):
        if not self._use_file:
            return

        json_neural_network = {
            "theta1":[np_mat.tolist()[0] for np_mat in self.theta1],
            "theta2":[np_mat.tolist()[0] for np_mat in self.theta2],
            "b1":self.input_layer_bias[0].tolist()[0],
            "b2":self.hidden_layer_bias[0].tolist()[0]
        };
        with open(OCRNeuralNetwork.NN_FILE_PATH,'w') as nnFile:
            json.dump(json_neural_network, nnFile)

    def _load(self):
        if not self._use_file:
            return

        with open(OCRNeuralNetwork.NN_FILE_PATH) as nnFile:
            nn = json.load(nnFile)
        self.theta1 = [np.array(li) for li in nn['theta1']]
        self.theta2 = [np.array(li) for li in nn['theta2']]
        self.input_layer_bias = [np.array(nn['b1'][0])]
        self.hidden_layer_bias = [np.array(nn['b2'][0])]

########NEW FILE########
__FILENAME__ = server
import BaseHTTPServer
import json
from ocr import OCRNeuralNetwork
import numpy as np

HOST_NAME = 'localhost'
PORT_NUMBER = 8000
HIDDEN_NODE_COUNT = 15

# Load data samples and labels into matrix
data_matrix = np.loadtxt(open('data.csv', 'rb'), delimiter = ',')
data_labels = np.loadtxt(open('dataLabels.csv', 'rb'))

# Convert from numpy ndarrays to python lists
data_matrix = data_matrix.tolist()
data_labels = data_labels.tolist()

# If a neural network file does not exist, train it using all 5000 existing data samples.
# Based on data collected from neural_network_design.py, 15 is the optimal number
# for hidden nodes
nn = OCRNeuralNetwork(HIDDEN_NODE_COUNT, data_matrix, data_labels, list(range(5000)));

class JSONHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_POST(s):
        response_code = 200
        response = ""
        varLen = int(s.headers.get('Content-Length'))
        content = s.rfile.read(varLen);
        payload = json.loads(content);

        if payload.get('train'):
            nn.train(payload['trainArray'])
            nn.save()
        elif payload.get('predict'):
            try:
                response = {"type":"test", "result":nn.predict(str(payload['image']))}
            except:
                response_code = 500
        else:
            response_code = 400

        s.send_response(response_code)
        s.send_header("Content-type", "application/json")
        s.send_header("Access-Control-Allow-Origin", "*")
        s.end_headers()
        if response:
            s.wfile.write(json.dumps(response))
        return

if __name__ == '__main__':
    server_class = BaseHTTPServer.HTTPServer;
    httpd = server_class((HOST_NAME, PORT_NUMBER), JSONHandler)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    else:
        print "Unexpected server exception occurred."
    finally:
        httpd.server_close()

########NEW FILE########
__FILENAME__ = color
class Color:
    def __init__(self, r=0, g=0, b=0, a=1, rgb=None):
        self.rgb = rgb or (r, g, b)
        self.a = a
    def draw(self, o):
        if self.a == o.a == 0.0:
            return
        if o.a == 1.0:
            self.rgb = o.rgb
            self.a = 1
        else:
            u = 1.0 - o.a
            self.rgb = (u * self.rgb[0] + o.a * o.rgb[0],
                        u * self.rgb[1] + o.a * o.rgb[1],
                        u * self.rgb[2] + o.a * o.rgb[2])
            self.a = 1.0 - (1.0 - self.a) * (1.0 - o.a)
    def fainter(self, k):
        return Color(rgb=self.rgb, a=self.a*k)
    def as_ppm(self):
        def byte(v):
            return int(v ** (1.0 / 2.2) * 255)
        return "%c%c%c" % (byte(self.rgb[0] * self.a),
                           byte(self.rgb[1] * self.a),
                           byte(self.rgb[2] * self.a))
    def __repr__(self):
        return "[" + str(self.rgb) + "," + str(self.a) + "]"
    @staticmethod
    def hex(code, a=1):
        if len(code) == 4:
            return Color(int(code[1], 16) / 15.0,
                         int(code[2], 16) / 15.0,
                         int(code[3], 16) / 15.0, a)
        elif len(code) == 7:
            return Color(int(code[1:3], 16) / 255.0,
                         int(code[3:5], 16) / 255.0,
                         int(code[5:7], 16) / 255.0, a)

########NEW FILE########
__FILENAME__ = csg
from shape import Shape
from geometry import *

class CSG(Shape):
    def __init__(self, v1, v2, color=None):
        Shape.__init__(self, color or v1.color or v2.color)
        self.v1 = v1
        self.v2 = v2
    def transform(self, t):
        return self.__class__(self.v1.transform(t), self.v2.transform(t),
                              color=self.color)

class Union(CSG):
    def __init__(self, v1, v2, color=None):
        CSG.__init__(self, v1, v2, color=color)
        self.bound = AABox.from_vectors(v1.bound.low, v1.bound.high,
                                        v2.bound.low, v2.bound.high)
    def contains(self, p):
        return self.v1.contains(p) or self.v2.contains(p)
    def signed_distance_bound(self, p):
        b1 = self.v1.signed_distance_bound(p)
        b2 = self.v2.signed_distance_bound(p)
        return b1 if b1 > b2 else b2

class Intersection(CSG):
    def __init__(self, v1, v2, color=None):
        CSG.__init__(self, v1, v2, color=color)
        self.bound = v1.bound.intersection(v2.bound)
    def contains(self, p):
        return self.v1.contains(p) and self.v2.contains(p)
    def signed_distance_bound(self, p):
        b1 = self.v1.signed_distance_bound(p)
        b2 = self.v2.signed_distance_bound(p)
        return b1 if b1 < b2 else b2

class Subtraction(CSG):
    def __init__(self, v1, v2, color=None):
        CSG.__init__(self, v1, v2, color=color)
        self.bound = self.v1.bound
    def contains(self, p):
        return self.v1.contains(p) and not self.v2.contains(p)
    def signed_distance_bound(self, p):
        b1 = self.v1.signed_distance_bound(p)
        b2 = -self.v2.signed_distance_bound(p)
        return b1 if b1 < b2 else b2

########NEW FILE########
__FILENAME__ = ellipse
from shape import Shape
from poly import ConvexPoly
from geometry import Vector, Transform, quadratic, scale, translate, AABox, HalfPlane
from color import Color
import sys

class Ellipse(Shape):
    def __init__(self, a=1.0, b=1.0, c=0.0, d=0.0, e=0.0, f=-1.0, color=None):
        Shape.__init__(self, color)
        if c*c - 4*a*b >= 0:
            raise Exception("Not an ellipse")
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.e = e
        self.f = f
        self.gradient = Transform(2*a, c, d, c, 2*b, e)
        self.center = self.gradient.inverse() * Vector(0, 0)
        y1, y2 = quadratic(b-c*c/4*a, e-c*d/2*a, f-d*d/4*a)
        x1, x2 = quadratic(a-c*c/4*b, d-c*e/2*b, f-e*e/4*b)
        self.bound = AABox.from_vectors(Vector(-(d + c*y1)/2*a, y1),
                                        Vector(-(d + c*y2)/2*a, y2),
                                        Vector(x1, -(e + c*x1)/2*b),
                                        Vector(x2, -(e + c*x2)/2*b))
        if not self.contains(self.center):
            raise Exception("Internal error, center not inside ellipse")
    def value(self, p):
        return self.a*p.x*p.x + self.b*p.y*p.y + self.c*p.x*p.y \
               + self.d*p.x + self.e*p.y + self.f
    def contains(self, p):
        return self.value(p) < 0
    def transform(self, transform):
        i = transform.inverse()
        ((m00, m01, m02), (m10, m11, m12),_) = i.m
        aa = self.a*m00*m00 + self.b*m10*m10 + self.c*m00*m10
        bb = self.a*m01*m01 + self.b*m11*m11 + self.c*m01*m11
        cc = 2*self.a*m00*m01 + 2*self.b*m10*m11 \
             + self.c*(m00*m11 + m01*m10)
        dd = 2*self.a*m00*m02 + 2*self.b*m10*m12 \
             + self.c*(m00*m12 + m02*m10) + self.d*m00 + self.e*m10
        ee = 2*self.a*m01*m02 + 2*self.b*m11*m12 \
             + self.c*(m01*m12 + m02*m11) + self.d*m01 + self.e*m11
        ff = self.a*m02*m02 + self.b*m12*m12 + self.c*m02*m12 \
             + self.d*m02 + self.e*m12 + self.f
        return Ellipse(aa, bb, cc, dd, ee, ff, color=self.color)
    def intersections(self, c, p):
        # returns the two intersections of the line through c and p
        # and the ellipse. Defining a line as a function of a single
        # parameter u, x(u) = c.x + u * (p.x - c.x), (and same for y)
        # this simply solves the quadratic equation f(x(u), y(u)) = 0
        pc = p - c
        u2 = self.a*pc.x**2 + self.b*pc.y**2 + self.c*pc.x*pc.y
        u1 = 2*self.a*c.x*pc.x + 2*self.b*c.y*pc.y \
             + self.c*c.y*pc.x +   self.c*c.x*pc.y + self.d*pc.x \
             + self.e*pc.y
        u0 = self.a*c.x**2 + self.b*c.y**2 + self.c*c.x*c.y \
             + self.d*c.x + self.e*c.y + self.f
        try:
            sols = quadratic(u2, u1, u0)
        except ValueError:
            raise Exception("Internal error, solutions be real numbers")
        return c+pc*sols[0], c+pc*sols[1]
    def signed_distance_bound(self, p):
        v = self.value(p)
        if v == 0:
            return 0
        elif v < 0:
            # if inside the ellipse, create an inscribed quadrilateral
            # that contains the given point and use the minimum distance
            # from the point to the quadrilateral as a bound. Since
            # the quadrilateral lies entirely inside the ellipse, the
            # distance from the point to the ellipse must be smaller.
            v0, v2 = self.intersections(p, p + Vector(1, 0))
            v1, v3 = self.intersections(p, p + Vector(0, 1))
            return abs(ConvexPoly([v0,v1,v2,v3]).signed_distance_bound(p))
        else:
            c = self.center
            crossings = self.intersections(c, p)
            # the surface point we want is the one closest to p
            if (p - crossings[0]).length() < (p - crossings[1]).length():
                surface_pt = crossings[0]
            else:
                surface_pt = crossings[1]
            # n is the normal at surface_pt
            n = self.gradient * surface_pt
            n = n * (1.0 / n.length())
            # returns the length of the projection of p - surface_pt
            # along the normal
            return -abs(n.dot(p - surface_pt))

def Circle(center, radius, color=None):
    return Ellipse(color=color).transform(
        scale(radius, radius)).transform(
        translate(center.x, center.y))

########NEW FILE########
__FILENAME__ = destijl
from .. import *

def painting():
    scene = Scene()
    scene.add(Rectangle(Vector(0.95, 0.0), Vector(1.0, 0.175), Color(0.75, 0.55, 0, 1)))
    scene.add(Rectangle(Vector(0.0, 0.73), Vector(1.0, 0.76), Color(0,0,0,1)))
    scene.add(Rectangle(Vector(0.94, 0), Vector(0.96, 1), Color(0,0,0,1)))
    scene.add(Rectangle(Vector(0.95, 0.16), Vector(1, 0.19), Color(0,0,0,1)))
    scene.add(Rectangle(Vector(0.25, 0.35), Vector(1.0, 1.0), Color(0.75,0,0,1)))
    scene.add(Rectangle(Vector(0.0, 0.0), Vector(0.25, 0.35), Color(0.05,0,0.85,1)))
    scene.add(Rectangle(Vector(0.24, 0.0), Vector(0.26, 1.0), Color(0,0,0,1)))
    scene.add(Rectangle(Vector(0.0, 0.34), Vector(1.0, 0.36), Color(0,0,0,1)))
    return scene

def run(image):
    painting().draw(image)

########NEW FILE########
__FILENAME__ = e1
from .. import *
def run(image):
    scene = Scene()
    scene.add(Triangle([Vector(0.5, 0.5), Vector(0.8, 0.5), Vector(0.5, 0.8)],
                       Color(1,0,0,1)))
    scene.draw(image)

########NEW FILE########
__FILENAME__ = e2
import destijl
from .. import *

def run(image):
    painting = destijl.painting()
    frame = Scene([Rectangle(Vector(-0.025,-0.025), Vector(1.025, 1.025), Color(0,0,0,1)),
                   Rectangle(Vector(0,0), Vector(1, 1), Color(1,1,1,1))])
    small_painting = Scene([frame, painting], scale(0.45, 0.45))
    p1 = Scene([small_painting], translate(0.025, 0.025))
    p2 = Scene([small_painting], translate(0.025, 0.525))
    p3 = Scene([small_painting], translate(0.525, 0.025))
    p4 = Scene([small_painting], translate(0.525, 0.525))
    s = Scene([p1, p2, p3, p4])
    s.draw(image)
   

########NEW FILE########
__FILENAME__ = e3
from .. import *
import math

def run(image):
    s = Scene()
    radius = 0.02
    angle = 1
    distance = 0.02
    colors = [Color.hex("#1f77b4"), Color.hex("#ff7f0e"), Color.hex("#2ca02c"),
              Color.hex("#d62728"), Color.hex("#9467bd"), Color.hex("#8c564b")]
    for i in xrange(500):
        obj = Circle(Vector(0.5, 0.5), radius, colors[i % len(colors)])
        obj = obj.transform(translate(distance, 0))
        obj = obj.transform(around(Vector(0.5, 0.5), rotate(angle)))
        s.add(obj)
        step = 3 * radius / distance
        distance = distance + 0.009 * step
        angle = angle + step
    s.draw(image)

########NEW FILE########
__FILENAME__ = geometry
import random
import math
from itertools import product

# Solves the quadratic equation ax^2 + bx + c = 0
# using a variant of the standard quadratic formula
# that behaves better numerically
def quadratic(a, b, c):
    if a == 0:
        return -c/b, -c/b
    d = (b * b - 4 * a * c) ** 0.5
    if b >= 0:
        return (-b - d) / (2 * a), (2 * c) / (-b - d)
    else:
        return (2 * c) / (-b + d), (-b + d) / (2 * a)

class Vector:
    def __init__(self, *args):
        self.x, self.y = args
    def __add__(self, o):
        return Vector(self.x + o.x, self.y + o.y)
    def __sub__(self, o):
        return Vector(self.x - o.x, self.y - o.y)
    def __mul__(self, k):
        return Vector(self.x * k, self.y * k)
    def dot(self, o):
        return self.x * o.x + self.y * o.y
    def min(self, o):
        return Vector(min(self.x, o.x), min(self.y, o.y))
    def max(self, o):
        return Vector(max(self.x, o.x), max(self.y, o.y))
    def length(self):
        return (self.x * self.x + self.y * self.y) ** 0.5
    def __repr__(self):
        return "[%.3f %.3f]" % (self.x, self.y)

class AABox:
    def __init__(self, p1, p2):
        self.low = p1.min(p2)
        self.high = p1.max(p2)
    def midpoint(self):
        return (self.low + self.high) * 0.5
    def size(self):
        return self.high - self.low
    def contains(self, p):
        return self.low.x <= p.x <= self.high.x and \
               self.low.y <= p.y <= self.high.y
    def overlaps(self, r):
        return not (r.low.x >= self.high.x or r.high.x <= self.low.x or
                    r.low.y >= self.high.y or r.high.y <= self.low.y)
    def intersection(self, other):
        return AABox(self.low.max(other.low), self.high.min(other.high))
    @staticmethod
    def from_vectors(*args):
        return AABox(reduce(Vector.min, args), reduce(Vector.max, args))

class HalfPlane:
    def __init__(self, p1, p2):
        self.v = Vector(-p2.y + p1.y, p2.x - p1.x)
        l = self.v.length()
        self.c = -self.v.dot(p1) / l
        self.v = self.v * (1.0 / l)
    def signed_distance(self, p):
        return self.v.dot(p) + self.c

# Transform represents an affine transformation
# of a 2D vector ("affine" because it's a linear transformation
# combined with a translation)
class Transform:
    def __init__(self, m11, m12, tx, m21, m22, ty):
        self.m = [[m11, m12, tx],
                  [m21, m22, ty],
                  [0, 0, 1]]
    def __mul__(self, other):
        if isinstance(other, Transform):
            # if the other element is also a transform,
            # then return a transform corresponding to the
            # composition of the two transforms
            t = [[0.0] * 3 for i in xrange(3)]
            for i, j, k in product(xrange(3), repeat=3):
                t[i][j] += self.m[i][k] * other.m[k][j]
            return Transform(t[0][0], t[0][1], t[0][2],
                             t[1][0], t[1][1], t[1][2])
        else:
            # if the other element is a vector, then
            # apply the transformation to the vector via
            # a matrix-vector multiplication
            nx = self.m[0][0] * other.x + self.m[0][1] * other.y + self.m[0][2]
            ny = self.m[1][0] * other.x + self.m[1][1] * other.y + self.m[1][2]
            return Vector(nx, ny)
    def det(s):
        return s.m[0][0] * s.m[1][1] - s.m[0][1] * s.m[1][0]
    def inverse(self):
        d = 1.0 / self.det()
        t = Transform(d * self.m[1][1], -d * self.m[0][1], 0,
                      -d * self.m[1][0], d * self.m[0][0], 0)
        v = t * Vector(self.m[0][2], self.m[1][2])
        t.m[0][2] = -v.x
        t.m[1][2] = -v.y
        return t

def identity():
    return Transform(1, 0, 0, 0, 1, 0)

def rotate(theta):
    s = math.sin(theta)
    c = math.cos(theta)
    return Transform(c, -s, 0, s, c, 0)

def translate(tx, ty):
    return Transform(1, 0, tx, 0, 1, ty)

def scale(x, y):
    return Transform(x, 0, 0, 0, y, 0)

# To perform a transformation 'around' some point,
# we first translate that point to the origin, perform a transformation,
# then translate back that same amount
def around(v, t):
    return translate(v.x, v.y) * t * translate(-v.x, -v.y)

########NEW FILE########
__FILENAME__ = image
from color import Color
from geometry import AABox, Vector

class PPMImage:
    def __init__(self, resolution, bg=Color()):
        self.resolution = resolution
        self.pixels = []
        for i in xrange(self.resolution):
            lst = []
            for j in xrange(self.resolution):
                lst.append(Color(rgb=bg.rgb, a=bg.a))
            self.pixels.append(lst)
    def bounds(self):
        return AABox(Vector(0,0), Vector(1,1))
    def __getitem__(self, a):
        return self.pixels[a.y][a.x]
    def __setitem__(self, a, color):
        self.pixels[a.y][a.x] = color
    def write_ppm(self, out):
        n = self.resolution
        out.write("P6\n%s\n%s\n255\n" % (n,n))
        for y in xrange(n-1, -1, -1):
            for x in xrange(n):
                out.write(self.pixels[y][x].as_ppm())

########NEW FILE########
__FILENAME__ = poly
from shape import Shape
from geometry import HalfPlane, Vector, AABox

class ConvexPoly(Shape): # a *convex* poly, in ccw order, with no repeating vertices
    def __init__(self, ps, color=None):
        Shape.__init__(self, color)
        self.vs = ps
        self.bound = AABox.from_vectors(*self.vs)
        self.half_planes = []
        for i in xrange(len(self.vs)):
            h = HalfPlane(self.vs[i], self.vs[(i+1) % len(self.vs)])
            self.half_planes.append(h)
    def signed_distance_bound(self, p):
        plane = self.half_planes[0]
        min_inside = 1e30
        max_outside = -1e30
        for plane in self.half_planes:
            d = plane.signed_distance(p)
            if d <= 0 and d > max_outside:
                max_outside = d
            if d >= 0 and d < min_inside:
                min_inside = d
        return max_outside if max_outside <> -1e30 else min_inside
    def contains(self, p):
        for plane in self.half_planes:
            if plane.signed_distance(p) < 0:
                return False
        return True
    def transform(self, xform):
        return ConvexPoly(list(xform * v for v in self.vs), color=self.color)

Triangle, Quad = ConvexPoly, ConvexPoly

def Rectangle(v1, v2, color=None):
    return Quad([Vector(min(v1.x, v2.x), min(v1.y, v2.y)),
                 Vector(max(v1.x, v2.x), min(v1.y, v2.y)),
                 Vector(max(v1.x, v2.x), max(v1.y, v2.y)),
                 Vector(min(v1.x, v2.x), max(v1.y, v2.y))],
                color=color)

def LineSegment(v1, v2, thickness, color=None):
    d = v2 - v1
    d.x, d.y = -d.y, d.x
    d *= thickness / d.length() / 2
    return Quad([v1 + d, v1 - d, v2 - d, v2 + d], color=color)

# A simple polygon
# It will work by triangulating a polygon (via simple, slow ear-clipping)
# and then rendering it by a CSG union of the triangles
class Poly(Shape):
    def __init__(self, *args, **kwargs):
        raise Exception("Unimplemented")

########NEW FILE########
__FILENAME__ = scene
from geometry import identity
from shape import Shape, SceneObject

class Scene(SceneObject):
    def __init__(self, nodes=None, transform=None):
        if transform is None:
            transform = identity()
        if nodes is None:
            nodes = []
        self.transform = transform
        self.nodes = nodes
    def add(self, node):
        self.nodes.append(node)
    def draw(self, image):
        for scene_object in self.traverse(identity()):
            scene_object.draw(image)
    def traverse(self, xform):
        this_xform = xform * self.transform
        for node in self.nodes:
            if isinstance(node, Scene):
                for n in node.traverse(this_xform):
                    yield n
            elif isinstance(node, Shape):
                yield node.transform(this_xform)

########NEW FILE########
__FILENAME__ = shape
from color import Color
from itertools import product
from geometry import Vector
import random

class SceneObject:
    def draw(self, image):
        raise NotImplementedError("Undefined method")

class Shape(SceneObject):
    def __init__(self, color=None):
        self.color = color if color is not None else Color()
        self.bound = None
    def contains(self, p):
        raise NotImplementedError("Undefined method")
    def signed_distance_bound(self, p):
        raise NotImplementedError("Undefined method")
    def draw(self, image, super_sampling = 6):
        if not self.bound.overlaps(image.bounds()):
            return
        color = self.color
        r = float(image.resolution)
        jitter = [Vector((x + random.random()) / super_sampling / r,
                         (y + random.random()) / super_sampling / r)
                  for (x, y) in product(xrange(super_sampling), repeat=2)]
        lj = len(jitter)
        l_x = max(int(self.bound.low.x * r), 0)
        l_y = max(int(self.bound.low.y * r), 0)
        h_x = min(int(self.bound.high.x * r), r-1)
        h_y = min(int(self.bound.high.y * r), r-1)
        for y in xrange(l_y, int(h_y+1)):
            x = l_x
            while x <= h_x:
                corner = Vector(x / r, y / r)
                b = self.signed_distance_bound(corner)
                pixel_diameter = (2 ** 0.5) / r
                if b > pixel_diameter:
                    steps = int(r * (b - (pixel_diameter - 1.0/r)))
                    for x_ in xrange(x, min(x + steps, int(h_x+1))):
                        image.pixels[y][x_].draw(color)
                    x += steps
                elif b < -pixel_diameter:
                    steps = int(r * (-b - (pixel_diameter - 1.0/r)))
                    x += steps
                else:
                    coverage = 0
                    for j in jitter:
                        if self.contains(corner + j):
                            coverage += 1.0
                    image.pixels[y][x].draw(color.fainter(coverage / lj))
                    x += 1

########NEW FILE########
__FILENAME__ = run_examples
#!/usr/bin/env python

import rasterizer.examples as examples
from rasterizer import *
import subprocess

def run_example(example, filename):
    image = PPMImage(512, Color(1, 1, 1, 1))
    example.run(image)
    image.write_ppm(open(filename + '.ppm', 'w'))
    subprocess.call(["convert", filename + '.ppm', filename + '.png'])

run_example(examples.e1, 'e1')
run_example(examples.destijl, 'destijl')
run_example(examples.e2, 'e2')
run_example(examples.e3, 'e3')


########NEW FILE########
__FILENAME__ = test_rasterizer
from rasterizer import *
import sys
import cProfile
import random
import math

def do_it():
    f = open(sys.argv[1], 'w')
    i = PPMImage(512, Color(1,1,1,1))
    s = Scene()
    s3 = Scene()
    s3.add(Union(Circle(Vector(0.3, 0.1), 0.1),
                 Circle(Vector(0.35, 0.1), 0.1),
                 Color(0,0,0,0.5)))
    s3.add(Intersection(Circle(Vector(0.3, 0.3), 0.1),
                        Circle(Vector(0.35, 0.3), 0.1),
                        Color(0,0.5,0,1)))
    s3.add(Subtraction(Circle(Vector(0.3, 0.5), 0.1),
                       Circle(Vector(0.35, 0.5), 0.1),
                       Color(0,0,0.5,1)))
    s3.add(Subtraction(Circle(Vector(0.35, 0.7), 0.1),
                       Circle(Vector(0.3, 0.7), 0.1),
                       Color(0,0.5,0.5,1)))
    s2 = Scene([
        LineSegment(Vector(0.0,0), Vector(0.0,1), 0.01, Color(1,0,0,1)),
        LineSegment(Vector(0.1,0), Vector(0.1,1), 0.01, Color(1,0,0,1)),
        LineSegment(Vector(0.2,0), Vector(0.2,1), 0.01, Color(1,0,0,1)),
        LineSegment(Vector(0.3,0), Vector(0.3,1), 0.01, Color(1,0,0,1)),
        LineSegment(Vector(0.4,0), Vector(0.4,1), 0.01, Color(1,0,0,1)),
        LineSegment(Vector(0.5,0), Vector(0.5,1), 0.01, Color(1,0,0,1)),
        LineSegment(Vector(0.6,0), Vector(0.6,1), 0.01, Color(1,0,0,1)),
        LineSegment(Vector(0.2,0.1), Vector(0.7, 0.4), 0.01, Color(0,0.5,0,1))])
    for shape in [
        Circle(Vector(0.0, 0.0), 0.8, Color(1,0.5,0,1)).transform(scale(0.05,1)),
        Triangle([Vector(0.2,0.1), Vector(0.9,0.3), Vector(0.1,0.4)],
                 Color(1,0,0,0.5)),
        Triangle([Vector(0.5,0.2), Vector(1,0.4), Vector(0.2,0.7)],
                 Color(0,1,0,0.5)),
        Rectangle(Vector(0.1,0.7), Vector(0.6,0.8),
                  Color(0,0.5,0.8,0.5)),
        Triangle([Vector(-1, 0.6), Vector(0.2, 0.8), Vector(-2, 0.7)],
                 Color(1,0,1,0.9)),
        Circle(Vector(0.5,0.9), 0.2, Color(0,0,0,1)),
        Circle(Vector(0.9, 0.5), 0.2,
               Color(0,1,1,0.5)).transform(around(Vector(0.9, 0.5), scale(1.0, 0.5))),
        s2,
        Scene([s2], around(Vector(0.5, 0.5), rotate(math.radians(90)))),
        Scene([s3], translate(0.5, 0))
        ]:
        s.add(shape)
    s.draw(i)
    i.write_ppm(f)
    f.close()

def test_quadratic():
    for i in xrange(1000):
        a = random.random()
        b = random.random()
        c = random.random()
        if b * b - 4 * a * c >= 0:
            v1, v2 = quadratic(a, b, c)
            if v1 * v1 * a + v1 * b + c > 1e-5:
                raise Exception("fail")
            if v2 * v2 * a + v2 * b + c > 1e-5:
                raise Exception("fail")
    for i in xrange(1000):
        a = 0
        b = random.random()
        c = random.random()
        if b * b - 4 * a * c >= 0:
            v1, v2 = quadratic(a, b, c)
            if v1 * v1 * a + v1 * b + c > 1e-5:
                raise Exception("fail")
            if v2 * v2 * a + v2 * b + c > 1e-5:
                raise Exception("fail")

def test_inverse():
    for i in xrange(10000):
        f = Transform(random.random(), random.random(), random.random(),
                      random.random(), random.random(), random.random())
        v = Vector(random.random(), random.random())
        m = f * f.inverse()
        if (m * v - v).length() > 1e-4:
            print >>sys.stderr, "inverse failed!"
            print f.m
            print m.m
            raise Exception("foo")

if __name__ == '__main__':
    test_inverse()
    test_quadratic()
    do_it()

########NEW FILE########
__FILENAME__ = templite
"""A simple Python template renderer, for a nano-subset of Django syntax."""

# Coincidentally named the same as http://code.activestate.com/recipes/496702/

import re


class CodeBuilder(object):
    """Build source code conveniently."""

    INDENT_STEP = 4      # PEP8 says so!

    def __init__(self, indent=0):
        self.code = []
        self.indent_amount = indent

    def add_line(self, line):
        """Add a line of source to the code.

        Don't include indentations or newlines.

        """
        self.code.extend([" " * self.indent_amount, line, "\n"])

    def add_section(self):
        """Add a section, a sub-CodeBuilder."""
        sect = CodeBuilder(self.indent_amount)
        self.code.append(sect)
        return sect

    def indent(self):
        """Increase the current indent for following lines."""
        self.indent_amount += self.INDENT_STEP

    def dedent(self):
        """Decrease the current indent for following lines."""
        self.indent_amount -= self.INDENT_STEP

    def __str__(self):
        return "".join(str(c) for c in self.code)

    def get_globals(self):
        """Compile the code, and return a dict of globals it defines."""
        # A check that the caller really finished all the blocks they started.
        assert self.indent_amount == 0
        # Get the Python source as a single string.
        python_source = str(self)
        # Execute the source, defining globals, and return them.
        globals = {}
        exec(python_source, globals)
        return globals


class Templite(object):
    """A simple template renderer, for a nano-subset of Django syntax.

    Supported constructs are extended variable access::

        {{var.modifer.modifier|filter|filter}}

    loops::

        {% for var in list %}...{% endfor %}

    and ifs::

        {% if var %}...{% endif %}

    Comments are within curly-hash markers::

        {# This will be ignored #}

    Construct a Templite with the template text, then use `render` against a
    dictionary context to create a finished string.

    """
    def __init__(self, text, *contexts):
        """Construct a Templite with the given `text`.

        `contexts` are dictionaries of values to use for future renderings.
        These are good for filters and global values.

        """
        self.text = text
        self.context = {}
        for context in contexts:
            self.context.update(context)

        self.all_vars = set()
        self.loop_vars = set()

        # We construct a function in source form, then compile it and hold onto
        # it, and execute it to render the template.
        code = CodeBuilder()

        code.add_line("def render(ctx, dot):")
        code.indent()
        vars_code = code.add_section()
        code.add_line("result = []")
        code.add_line("a = result.append")
        code.add_line("e = result.extend")
        code.add_line("s = str")

        buffered = []
        def flush_output():
            """Force `buffered` to the code builder."""
            if len(buffered) == 1:
                code.add_line("a(%s)" % buffered[0])
            elif len(buffered) > 1:
                code.add_line("e([%s])" % ",".join(buffered))
            del buffered[:]

        # Split the text to form a list of tokens.
        tokens = re.split(r"(?s)({{.*?}}|{%.*?%}|{#.*?#})", text)

        ops_stack = []
        for token in tokens:
            if token.startswith('{{'):
                # An expression to evaluate.
                buffered.append("s(%s)" % self.expr_code(token[2:-2].strip()))
            elif token.startswith('{#'):
                # Comment: ignore it and move on.
                continue
            elif token.startswith('{%'):
                # Action tag: split into words and parse further.
                flush_output()
                words = token[2:-2].strip().split()
                if words[0] == 'if':
                    # An if statement: evaluate the expression to determine if.
                    if len(words) != 2:
                        self.syntax_error("Don't understand if", token)
                    ops_stack.append('if')
                    code.add_line("if %s:" % self.expr_code(words[1]))
                    code.indent()
                elif words[0] == 'for':
                    # A loop: iterate over expression result.
                    if len(words) != 4 or words[2] != 'in':
                        self.syntax_error("Don't understand for", token)
                    ops_stack.append('for')
                    self.loop_vars.add(words[1])
                    code.add_line(
                        "for c_%s in %s:" % (
                            words[1],
                            self.expr_code(words[3])
                        )
                    )
                    code.indent()
                elif words[0].startswith('end'):
                    # Endsomething.  Pop the ops stack.
                    end_what = words[0][3:]
                    if ops_stack[-1] != end_what:
                        self.syntax_error("Mismatched end tag", end_what)
                    ops_stack.pop()
                    code.dedent()
                else:
                    self.syntax_error("Don't understand tag", words[0])
            else:
                # Literal content.  If it isn't empty, output it.
                if token:
                    buffered.append("%r" % token)
        flush_output()

        for var_name in self.all_vars - self.loop_vars:
            vars_code.add_line("c_%s = ctx[%r]" % (var_name, var_name))

        if ops_stack:
            self.syntax_error("Unmatched action tag", ops_stack[-1])

        code.add_line("return ''.join(result)")
        code.dedent()
        self.render_function = code.get_globals()['render']

    def syntax_error(self, msg, thing):
        """Raise a syntax error using `msg`, and showing `thing`."""
        raise SyntaxError("%s: %r" % (msg, thing))

    def expr_code(self, expr):
        """Generate a Python expression for `expr`."""
        if "|" in expr:
            pipes = expr.split("|")
            code = self.expr_code(pipes[0])
            for func in pipes[1:]:
                self.all_vars.add(func)
                code = "c_%s(%s)" % (func, code)
        elif "." in expr:
            dots = expr.split(".")
            code = self.expr_code(dots[0])
            args = ", ".join(repr(d) for d in dots[1:])
            code = "dot(%s, %s)" % (code, args)
        else:
            self.all_vars.add(expr)
            code = "c_%s" % expr
        return code

    def render(self, context=None):
        """Render this template by applying it to `context`.

        `context` is a dictionary of values to use in this rendering.

        """
        # Make the complete context we'll use.
        ctx = dict(self.context)
        if context:
            ctx.update(context)
        return self.render_function(ctx, self.do_dots)

    def do_dots(self, value, *dots):
        """Evaluate dotted expressions at runtime."""
        for dot in dots:
            try:
                value = getattr(value, dot)
            except AttributeError:
                value = value[dot]
            if hasattr(value, '__call__'):
                value = value()
        return value

########NEW FILE########
__FILENAME__ = test_templite
"""Tests for templite."""

from templite import Templite
from unittest import TestCase

# pylint: disable=W0612,E1101
# Disable W0612 (Unused variable) and
# E1101 (Instance of 'foo' has no 'bar' member)

class AnyOldObject(object):
    """Simple testing object.

    Use keyword arguments in the constructor to set attributes on the object.

    """
    def __init__(self, **attrs):
        for n, v in attrs.items():
            setattr(self, n, v)


class TempliteTest(TestCase):
    """Tests for Templite."""

    def try_render(self, text, ctx=None, result=None):
        """Render `text` through `ctx`, and it had better be `result`.

        Result defaults to None so we can shorten the calls where we expect
        an exception and never get to the result comparison.
        """
        actual = Templite(text).render(ctx or {})
        if result:
            self.assertEqual(actual, result)

    def test_passthrough(self):
        # Strings without variables are passed through unchanged.
        self.assertEqual(Templite("Hello").render(), "Hello")
        self.assertEqual(
            Templite("Hello, 20% fun time!").render(),
            "Hello, 20% fun time!"
            )

    def test_variables(self):
        # Variables use {{var}} syntax.
        self.try_render("Hello, {{name}}!", {'name':'Ned'}, "Hello, Ned!")

    def test_undefined_variables(self):
        # Using undefined names is an error.
        with self.assertRaises(Exception):
            self.try_render("Hi, {{name}}!")

    def test_pipes(self):
        # Variables can be filtered with pipes.
        data = {
            'name': 'Ned',
            'upper': lambda x: x.upper(),
            'second': lambda x: x[1],
            }
        self.try_render("Hello, {{name|upper}}!", data, "Hello, NED!")

        # Pipes can be concatenated.
        self.try_render("Hello, {{name|upper|second}}!", data, "Hello, E!")

    def test_reusability(self):
        # A single Templite can be used more than once with different data.
        globs = {
            'upper': lambda x: x.upper(),
            'punct': '!',
            }

        template = Templite("This is {{name|upper}}{{punct}}", globs)
        self.assertEqual(template.render({'name':'Ned'}), "This is NED!")
        self.assertEqual(template.render({'name':'Ben'}), "This is BEN!")

    def test_attribute(self):
        # Variables' attributes can be accessed with dots.
        obj = AnyOldObject(a="Ay")
        self.try_render("{{obj.a}}", locals(), "Ay")

        obj2 = AnyOldObject(obj=obj, b="Bee")
        self.try_render("{{obj2.obj.a}} {{obj2.b}}", locals(), "Ay Bee")

    def test_member_function(self):
        # Variables' member functions can be used, as long as they are nullary.
        class WithMemberFns(AnyOldObject):
            """A class to try out member function access."""
            def ditto(self):
                """Return twice the .txt attribute."""
                return self.txt + self.txt
        obj = WithMemberFns(txt="Once")
        self.try_render("{{obj.ditto}}", locals(), "OnceOnce")

    def test_item_access(self):
        # Variables' items can be used.
        d = {'a':17, 'b':23}
        self.try_render("{{d.a}} < {{d.b}}", locals(), "17 < 23")

    def test_loops(self):
        # Loops work like in Django.
        nums = [1,2,3,4]
        self.try_render(
            "Look: {% for n in nums %}{{n}}, {% endfor %}done.",
            locals(),
            "Look: 1, 2, 3, 4, done."
            )
        # Loop iterables can be filtered.
        def rev(l):
            """Return the reverse of `l`."""
            l = l[:]
            l.reverse()
            return l

        self.try_render(
            "Look: {% for n in nums|rev %}{{n}}, {% endfor %}done.",
            locals(),
            "Look: 4, 3, 2, 1, done."
            )

    def test_empty_loops(self):
        self.try_render(
            "Empty: {% for n in nums %}{{n}}, {% endfor %}done.",
            {'nums':[]},
            "Empty: done."
            )

    def test_multiline_loops(self):
        self.try_render(
            "Look: \n{% for n in nums %}\n{{n}}, \n{% endfor %}done.",
            {'nums':[1,2,3]},
            "Look: \n\n1, \n\n2, \n\n3, \ndone."
            )

    def test_multiple_loops(self):
        self.try_render(
            "{% for n in nums %}{{n}}{% endfor %} and "
                                    "{% for n in nums %}{{n}}{% endfor %}",
            {'nums': [1,2,3]},
            "123 and 123"
            )

    def test_comments(self):
        # Single-line comments work:
        self.try_render(
            "Hello, {# Name goes here: #}{{name}}!",
            {'name':'Ned'}, "Hello, Ned!"
            )
        # and so do multi-line comments:
        self.try_render(
            "Hello, {# Name\ngoes\nhere: #}{{name}}!",
            {'name':'Ned'}, "Hello, Ned!"
            )

    def test_if(self):
        self.try_render(
            "Hi, {% if ned %}NED{% endif %}{% if ben %}BEN{% endif %}!",
            {'ned': 1, 'ben': 0},
            "Hi, NED!"
            )
        self.try_render(
            "Hi, {% if ned %}NED{% endif %}{% if ben %}BEN{% endif %}!",
            {'ned': 0, 'ben': 1},
            "Hi, BEN!"
            )
        self.try_render(
            "Hi, {% if ned %}NED{% if ben %}BEN{% endif %}{% endif %}!",
            {'ned': 0, 'ben': 0},
            "Hi, !"
            )
        self.try_render(
            "Hi, {% if ned %}NED{% if ben %}BEN{% endif %}{% endif %}!",
            {'ned': 1, 'ben': 0},
            "Hi, NED!"
            )
        self.try_render(
            "Hi, {% if ned %}NED{% if ben %}BEN{% endif %}{% endif %}!",
            {'ned': 1, 'ben': 1},
            "Hi, NEDBEN!"
            )

    def test_complex_if(self):
        class Complex(AnyOldObject):
            """A class to try out complex data access."""
            def getit(self):
                """Return it."""
                return self.it
        obj = Complex(it={'x':"Hello", 'y': 0})
        self.try_render(
            "@"
            "{% if obj.getit.x %}X{% endif %}"
            "{% if obj.getit.y %}Y{% endif %}"
            "{% if obj.getit.y|str %}S{% endif %}"
            "!",
            { 'obj': obj, 'str': str },
            "@XS!"
            )

    def test_loop_if(self):
        self.try_render(
            "@{% for n in nums %}{% if n %}Z{% endif %}{{n}}{% endfor %}!",
            {'nums': [0,1,2]},
            "@0Z1Z2!"
            )
        self.try_render(
            "X{%if nums%}@{% for n in nums %}{{n}}{% endfor %}{%endif%}!",
            {'nums': [0,1,2]},
            "X@012!"
            )
        self.try_render(
            "X{%if nums%}@{% for n in nums %}{{n}}{% endfor %}{%endif%}!",
            {'nums': []},
            "X!"
            )

    def test_nested_loops(self):
        self.try_render(
            "@"
            "{% for n in nums %}"
                "{% for a in abc %}{{a}}{{n}}{% endfor %}"
            "{% endfor %}"
            "!",
            {'nums': [0,1,2], 'abc': ['a', 'b', 'c']},
            "@a0b0c0a1b1c1a2b2c2!"
            )

    def test_exception_during_evaluation(self):
        # TypeError: Couldn't evaluate {{ foo.bar.baz }}:
        # 'NoneType' object is unsubscriptable
        with self.assertRaises(TypeError):
            self.try_render(
                "Hey {{foo.bar.baz}} there", {'foo': None}, "Hey ??? there"
            )

    def test_bogus_tag_syntax(self):
        msg = "Don't understand tag: 'bogus'"
        with self.assertRaisesRegexp(SyntaxError, msg):
            self.try_render("Huh: {% bogus %}!!{% endbogus %}??")

    def test_malformed_if(self):
        msg = "Don't understand if: '{% if %}'"
        with self.assertRaisesRegexp(SyntaxError, msg):
            self.try_render("Buh? {% if %}hi!{% endif %}")
        msg = "Don't understand if: '{% if this or that %}'"
        with self.assertRaisesRegexp(SyntaxError, msg):
            self.try_render("Buh? {% if this or that %}hi!{% endif %}")

    def test_malformed_for_(self):
        msg = "Don't understand for: '{% for %}'"
        with self.assertRaisesRegexp(SyntaxError, msg):
            self.try_render("Weird: {% for %}loop{% endfor %}")
        msg = "Don't understand for: '{% for x from y %}'"
        with self.assertRaisesRegexp(SyntaxError, msg):
            self.try_render("Weird: {% for x from y %}loop{% endfor %}")
        msg = "Don't understand for: '{% for x, y in z %}'"
        with self.assertRaisesRegexp(SyntaxError, msg):
            self.try_render("Weird: {% for x, y in z %}loop{% endfor %}")

    def test_bad_nesting(self):
        msg = "Unmatched action tag: 'if'"
        with self.assertRaisesRegexp(SyntaxError, msg):
            self.try_render("{% if x %}X")
        msg = "Mismatched end tag: 'for'"
        with self.assertRaisesRegexp(SyntaxError, msg):
            self.try_render("{% if x %}X{% endfor %}")

########NEW FILE########
__FILENAME__ = server
import BaseHTTPServer

class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    '''Handle HTTP requests by returning a fixed 'page'.'''

    # Page to send back.
    Page = '''\
<html>
<body>
<p>Hello, Nitinat!</p>
</body>
</html>
'''

    # Handle a GET request.
    def do_GET(self):
        self.sendPage()

    # Send the page.
    def sendPage(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(len(self.Page)))
        self.end_headers()
        self.wfile.write(self.Page)

#----------------------------------------------------------------------

if __name__ == '__main__':
    serverAddress = ('', 8080)
    server = BaseHTTPServer.HTTPServer(serverAddress, RequestHandler)
    server.serve_forever()

########NEW FILE########
__FILENAME__ = server
import BaseHTTPServer

class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    '''Respond to HTTP requests with info about the request.'''

    # Template for page to send back.
    Page = '''\
<html>
<body>
<h1>Nitinat/Python V1.0 Page</h1>
<table>
<tr>  <td>Date and time</td>  <td>%(date_time)s</td>   </tr>
<tr>  <td>Client host</td>    <td>%(client_host)s</td> </tr>
<tr>  <td>Client port</td>    <td>%(client_port)s</td> </tr>
<tr>  <td>Command</td>        <td>%(command)s</td>     </tr>
<tr>  <td>Path</td>           <td>%(path)s</td>        </tr>
</body>
</html>
'''

    # Handle a request by constructing an HTML page that echoes the
    # request back to the caller.
    def do_GET(self):
        page = self.create_page()
        self.send_page(page)

    # Create an information page to send.
    def create_page(self):
        values = {
            'date_time'   : self.date_time_string(),
            'client_host' : self.client_address[0],
            'client_port' : self.client_address[1],
            'command'     : self.command,
            'path'        : self.path
        }
        page = self.Page % values
        return page

    # Send the created page.
    def send_page(self, page):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

#----------------------------------------------------------------------

if __name__ == '__main__':
    serverAddress = ('', 8080)
    server = BaseHTTPServer.HTTPServer(serverAddress, RequestHandler)
    server.serve_forever()

########NEW FILE########
__FILENAME__ = server
import sys, os, BaseHTTPServer

class ServerException(Exception):
    '''For internal error reporting.'''
    pass

class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    '''
    If the requested path maps to a file, that file is served.  If the
    path maps to a directory, a listing of the directory is
    constructed and served.  If anything goes wrong, an error page is
    constructed.

    This class's RootDirectory variable must be set to the root of the
    files being served before any instances of this class are created.
    '''

    # Root directory (must be set before requests are handled).
    Root_Directory = None

    # How to display a single item in a directory listing.
    Listing_Item = "<li>%s</li>"

    # How to display a whole page of listings.
    Listing_Page = """\
        <html>
        <body>
        <h1>Listing for %(path)s</h1>
        <ul>
        %(filler)s
        </ul>
        </body>
        </html>
        """

    # How to display an error.
    Error_Page = """\
        <html>
        <body>
        <h1>Error accessing %(path)s</h1>
        <p>%(msg)s</p>
        </body>
        </html>
        """

    # Classify and handle request.
    def do_GET(self):

        # Handle any errors that aren't handled elsewhere.
        try:

            # Class not yet initialized.
            if self.Root_Directory is None:
                raise ServerException, "Root directory not set"

            # Figure out what exactly is being requested.
            full_path = self.Root_Directory + self.path

            # It doesn't exist...
            if not os.path.exists(full_path):
                raise ServerException, "'%s' not found" % self.path

            # ...it's a file...
            elif os.path.isfile(full_path):
                self.handle_file(full_path)

            # ...it's a directory...
            elif os.path.isdir(full_path):
                self.handle_dir(full_path)

            # ...we can't tell.
            else:
                raise ServerException, "Unknown object '%s'" % self.path

        # Handle errors.
        except Exception, msg:
            self.handle_error(msg)

    def handle_file(self, full_path):
        try:
            input = file(full_path, "r")
            content = input.read()
            input.close()
            self.send_content(content)
        except IOError, msg:
            msg = "'%s' cannot be read: %s" % (self.path, msg)
            self.handle_error(msg)

    def handle_dir(self, full_path):
        try:
            listing = os.listdir(full_path)
            filler = '\n'.join([(self.Listing_Item % item) for item in listing])
            content = self.Listing_Page % {'path'   : self.path,
                                           'filler' : filler}
            self.send_content(content)
        except IOError, msg:
            msg = "'%s' cannot be listed: %s" % (self.path, msg)
            self.handle_error(msg)

    # Handle unknown objects.
    def handle_error(self, msg):
        content = self.Error_Page % {'path' : self.path,
                                     'msg'  : msg}
        self.send_content(content)

    # Send actual content.
    def send_content(self, content):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

#----------------------------------------------------------------------

if __name__ == '__main__':

    # Set the handler's root directory.
    if len(sys.argv) < 2:
        print >> sys.stderr, "Usage: server.py base_directory"
        sys.exit(1)
    root = os.path.abspath(sys.argv[1])
    if not os.path.isdir(root):
        print >> sys.stderr, "No such directory '%s'" % root
        sys.exit(1)
    RequestHandler.Root_Directory = root

    # Create and run server.
    serverAddress = ('', 8080)
    server = BaseHTTPServer.HTTPServer(serverAddress, RequestHandler)
    server.serve_forever()

########NEW FILE########
__FILENAME__ = server
import sys, os, BaseHTTPServer

class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    # Root of files being served.
    Root_Directory = None

    # Is debugging output on?
    Debug = False

    # HTTP error codes.
    ERR_NO_PERM   = 403
    ERR_NOT_FOUND = 404
    ERR_INTERNAL  = 500

    # How to display a single item in a directory listing.
    Listing_Item = "<li>%s</li>"

    # How to display a whole page of listings.
    Listing_Page = """\
        <html>
        <body>
        <h1>Listing for %(path)s</h1>
        <ul>
        %(filler)s
        </ul>
        </body>
        </html>
        """

    # Classify and handle request.
    def do_GET(self):

        self.log("path is '%s'" % self.path)

        # Handle any errors that arise.
        try:

            # Class not yet initialized.
            if self.Root_Directory is None:
                self.err_internal("Root directory not set")
                return

            # Figure out what exactly is being requested.
            abs_path = self.create_abs_path()
            self.log("abs_path is '%s'" % abs_path)

            # It isn't below the root path.
            if not self.is_parent_dir(self.Root_Directory, abs_path):
                self.log("abs_path not below root directory")
                msg = "Path '%s' not below root directory '%s'" % \
                      (abs_path, self.Root_Directory)
                self.err_no_perm(msg)

            # It doesn't exist.
            elif not os.path.exists(abs_path):
                self.log("abs_path doesn't exist")
                self.err_not_found(abs_path)

            # It's a file.
            elif os.path.isfile(abs_path):
                self.log("abs_path is a file")
                self.handle_file(abs_path)

            # It's a directory.
            elif os.path.isdir(abs_path):
                self.log("abs_path is a directory")
                self.handle_dir(abs_path)

            # ...we can't tell.
            else:
                self.log("can't tell what abs_path is")
                self.err_not_found(abs_path)

        # Handle general errors.
        except Exception, msg:
            self.err_internal("Unexpected exception: %s" % msg)

    def create_abs_path(self):
        head = os.path.abspath(self.Root_Directory)
        result = os.path.normpath(head + self.path)
        return result

    def is_parent_dir(self, left, right):
        return os.path.commonprefix([left, right]) == left

    def handle_file(self, abs_path):
        try:
            input = file(abs_path, "r")
            content = input.read()
            input.close()
            self.send_content(content)
        except IOError, msg:
            msg = "'%s' cannot be read: %s" % (self.path, msg)
            self.err_no_perm(msg)

    def handle_dir(self, abs_path):
        try:
            listing = os.listdir(abs_path)
            filler = '\n'.join([(self.Listing_Item % item) for item in listing])
            content = self.Listing_Page % {'path'   : self.path,
                                           'filler' : filler}
            self.send_content(content)
        except IOError, msg:
            msg = "'%s' cannot be listed: %s" % (self.path, msg)
            self.send_error(ERR_NO_PERM, msg)

    # Send actual content.
    def send_content(self, content):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    # Report internal errors.
    def err_internal(self, msg):
        self.send_error(self.ERR_INTERNAL, msg)

    # Handle missing object errors.
    def err_not_found(self, abs_path):
        self.send_error(self.ERR_NOT_FOUND, "'%s' not found" % self.path)

    # Handle no permission errors.
    def err_no_perm(self, msg):
        self.send_error(self.ERR_NO_PERM, msg)

    # Write a log message if in debugging mode
    def log(self, msg):
        if self.Debug:
            print msg

#----------------------------------------------------------------------

if __name__ == '__main__':

    # Main libraries
    import getopt

    # How to use
    Usage = "server.py [-v] root_directory"

    # Handle command-line arguments
    options, rest = getopt.getopt(sys.argv[1:], "v")

    for (flag, arg) in options:
        if flag == "-v":
            RequestHandler.Debug = True
        else:
            print >> sys.stderr, Usage
            sys.exit(1)

    if not rest:
        print >> sys.stderr, Usage
        sys.exit(1)
    root = os.path.abspath(rest[0])
    if not os.path.isdir(root):
        print >> sys.stderr, "No such directory '%s'" % root
        sys.exit(1)
    RequestHandler.Root_Directory = root

    # Create and run server.
    server_address = ('', 8080)
    server = BaseHTTPServer.HTTPServer(server_address, RequestHandler)
    server.serve_forever()

########NEW FILE########
__FILENAME__ = server
import sys, os, BaseHTTPServer, mimetypes
class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    # Root of files being served.
    Root_Directory = None

    # Is debugging output on?
    Debug = False

    # HTTP error codes.
    ERR_NO_PERM   = 403
    ERR_NOT_FOUND = 404
    ERR_INTERNAL  = 500

    # How to display a single item in a directory listing.
    Listing_Item = "<li>%s</li>"

    # How to display a whole page of listings.
    Listing_Page = """\
        <html>
        <body>
        <h1>Listing for %(path)s</h1>
        <ul>
        %(filler)s
        </ul>
        </body>
        </html>
        """

    # MIME types of files.
    File_Types = mimetypes.types_map

    # Classify and handle request.
    def do_GET(self):

        self.log("path is '%s'" % self.path)

        # Handle any errors that arise.
        try:

            # Class not yet initialized.
            if self.Root_Directory is None:
                self.err_internal("Root directory not set")
                return

            # Figure out what exactly is being requested.
            abs_path = self.create_abs_path()
            self.log("abs_path is '%s'" % abs_path)

            # It isn't below the root path.
            if not self.is_parent_dir(self.Root_Directory, abs_path):
                self.log("abs_path not below root directory")
                msg = "Path '%s' not below root directory '%s'" % \
                      (abs_path, self.Root_Directory)
                self.err_no_perm(msg)

            # It doesn't exist.
            elif not os.path.exists(abs_path):
                self.log("abs_path doesn't exist")
                self.err_not_found(abs_path)

            # It's a file.
            elif os.path.isfile(abs_path):
                self.log("abs_path is a file")
                self.handle_file(abs_path)

            # It's a directory.
            elif os.path.isdir(abs_path):
                self.log("abs_path is a directory")
                self.handle_dir(abs_path)

            # ...we can't tell.
            else:
                self.log("can't tell what abs_path is")
                self.err_not_found(abs_path)

        # Handle general errors.
        except Exception, msg:
            self.err_internal("Unexpected exception: %s" % msg)

    def create_abs_path(self):
        head = os.path.abspath(self.Root_Directory)
        result = os.path.normpath(head + self.path)
        return result

    def is_parent_dir(self, left, right):
        return os.path.commonprefix([left, right]) == left

    # Guess the MIME type of a file from its name.
    def guess_file_type(self, path):
        base, ext = os.path.splitext(path)
        if ext in self.File_Types:
            return self.File_Types[ext]
        ext = ext.lower()
        if ext in self.File_Types:
            return self.File_Types[ext]
        return self.File_Types['']

    # Handle files.  Must read in binary mode!
    def handle_file(self, abs_path):
        try:
            input = file(abs_path, "rb")
            content = input.read()
            input.close()
            fileType = self.guess_file_type(abs_path)
            self.send_content(content, fileType)
        except IOError, msg:
            msg = "'%s' cannot be read: %s" % (self.path, msg)
            self.err_no_perm(msg)

    # Handle directories.
    def handle_dir(self, abs_path):
        try:
            listing = os.listdir(abs_path)
            filler = '\n'.join([(self.Listing_Item % item) for item in listing])
            content = self.Listing_Page % {'path'   : self.path,
                                           'filler' : filler}
            self.send_content(content)
        except IOError, msg:
            msg = "'%s' cannot be listed: %s" % (self.path, msg)
            self.err_no_perm(msg)

    # Send actual content.
    def send_content(self, content, fileType="text/html"):
        length = str(len(content))
        self.log("sending content, fileType '%s', length %s" % (fileType, length))
        self.send_response(200)
        self.send_header("Content-type", fileType)
        self.send_header("Content-Length", length)
        self.end_headers()
        self.wfile.write(content)

    # Report internal errors.
    def err_internal(self, msg):
        self.send_error(self.ERR_INTERNAL, msg)

    # Handle missing object errors.
    def err_not_found(self, abs_path):
        self.send_error(self.ERR_NOT_FOUND, "'%s' not found" % self.path)

    # Handle no permission errors.
    def err_no_perm(self, msg):
        self.send_error(self.ERR_NO_PERM, msg)

    # Write a log message if in debugging mode
    def log(self, msg):
        if self.Debug:
            print msg

#----------------------------------------------------------------------

if __name__ == '__main__':

    # Main libraries
    import getopt

    # How to use
    Usage = "server.py [-v] root_directory"

    # Handle command-line arguments
    options, rest = getopt.getopt(sys.argv[1:], "v")

    for (flag, arg) in options:
        if flag == "-v":
            RequestHandler.Debug = True
        else:
            print >> sys.stderr, Usage
            sys.exit(1)

    if not rest:
        print >> sys.stderr, Usage
        sys.exit(1)
    root = os.path.abspath(rest[0])
    if not os.path.isdir(root):
        print >> sys.stderr, "No such directory '%s'" % root
        sys.exit(1)
    RequestHandler.Root_Directory = root

    # Create and run server.
    server_address = ('', 8080)
    server = BaseHTTPServer.HTTPServer(server_address, RequestHandler)
    server.serve_forever()

########NEW FILE########
__FILENAME__ = server
import sys, os, BaseHTTPServer, mimetypes, gettext

class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    # Root of files being served.
    Root_Directory = None

    # Is debugging output on?
    Debug = False

    # HTTP error codes.
    ERR_NO_PERM   = 403
    ERR_NOT_FOUND = 404
    ERR_INTERNAL  = 500

    # MIME types of files.
    File_Types = mimetypes.types_map

    # Filename extensions that identify executables.
    Exec_Extensions = {
        ".py" : None
    }

    # Classify and handle request.
    def do_GET(self):

        # Handle any errors that arise.
        try:

            # Class not yet initialized.
            if self.Root_Directory is None:
                self.err_internal("Root directory not set")
                return

            # Figure out what exactly is being requested.
            abs_path, query_params = self.parse_path()
            self.log("abs_path is '%s'" % abs_path)
            self.log("query_params is '%s'" % query_params)

            # It isn't below the root path.
            if not self.is_parent_dir(self.Root_Directory, abs_path):
                self.log("abs_path not below root directory")
                self.err_no_perm("Path '%s' not below root directory '%s'" % \
                                 (abs_path, self.Root_Directory))

            # It doesn't exist.
            elif not os.path.exists(abs_path):
                self.log("abs_path doesn't exist")
                self.err_not_found(abs_path)

            # It's a file. (Ignore query parameters if the file is
            # not being executed.)
            elif os.path.isfile(abs_path):
                if self.is_executable(abs_path):
                    self.log("abs_path is an executable")
                    self.handle_executable(abs_path, query_params)
                else:
                    self.log("abs_path is a file")
                    self.handle_static_file(abs_path)

            # It's a directory --- ignore query parameters.
            elif os.path.isdir(abs_path):
                self.log("abs_path is a directory")
                self.handle_dir(abs_path)

            # ...we can't tell.
            else:
                self.log("can't tell what abs_path is")
                self.err_not_found(abs_path)

        # Handle general errors.
        except Exception, msg:
            self.err_internal("Unexpected exception in main despatch: %s" % msg)

    def parse_path(self):
        '''Create the absolute path for a request, and extract the query
        parameter string (if any).'''
        parts = self.path.split("?")
        if len(parts) == 1:
            request_path, queryString = self.path, ""
        elif len(parts) == 2:
            request_path, queryString = parts
        else:
            pass
        head = os.path.abspath(self.Root_Directory)
        result = os.path.normpath(head + request_path)
        return result, queryString

    def is_parent_dir(self, left, right):
        return os.path.commonprefix([left, right]) == left

    def guess_file_type(self, path):
        base, ext = os.path.splitext(path)
        if ext in self.File_Types:
            return self.File_Types[ext]
        ext = ext.lower()
        if ext in self.File_Types:
            return self.File_Types[ext]
        return self.File_Types['']

    def is_executable(self, abs_path):
        '''Does this path map to an executable file?'''
        root, ext = os.path.splitext(abs_path)
        return ext in self.Exec_Extensions

    def handle_static_file(self, abs_path):
        '''Handle static files.  Must read in binary mode!'''
        try:
            input = file(abs_path, "rb")
            content = input.read()
            input.close()
            file_type = self.guess_file_type(abs_path)
            self.send_content(content, file_type)
        except IOError, msg:
            self.err_no_perm("'%s' cannot be read: %s" % (self.path, msg))

    # Handle directories.
    def handle_dir(self, abs_path):

        # How to display a single item in a directory listing.
        listing_item = "<li>%s</li>"

        # How to display a whole page of listings.
        listing_page = \
            "<html>" + \
            "<body>" + \
            "<h1>Listing for " + "%(path)s" + "</h1>" + \
            "<ul>" + \
            "%(filler)s" + \
            "</ul>" + \
            "</body>" + \
            "</html>"

        try:
            listing = os.listdir(abs_path)
            filler = '\n'.join([(listing_item % item) for item in listing])
            content = listing_page % {'path'   : self.path,
                                      'filler' : filler}
            self.send_content(content)
        except IOError, msg:
            self.err_no_perm("'%s' cannot be listed: %s" % msg)

    # Handle executable file.
    def handle_executable(self, abs_path, query_params):
        # Passing query parameters?
        if query_params:
            os.environ["REQUEST_METHOD"] = "GET"
            os.environ["QUERY_STRING"] = query_params
        cmd = "python " + abs_path
        childInput, childOutput = os.popen2(cmd)
        childInput.close()
        response = childOutput.read()
        childOutput.close()
        self.log("handle_executable: response length is %d" % len(response))
        self.send_response(200)
        self.wfile.write(response)

    # Send actual content.
    def send_content(self, content, fileType="text/html"):
        length = str(len(content))
        self.log("sending content, fileType '%s', length %s" % (fileType, length))
        self.send_response(200)
        self.send_header("Content-type", fileType)
        self.send_header("Content-Length", length)
        self.end_headers()
        self.wfile.write(content)

    # Report internal errors.
    def err_internal(self, msg):
        self.send_error(self.ERR_INTERNAL, msg)

    # Handle missing object errors.
    def err_not_found(self, abs_path):
        self.send_error(self.ERR_NOT_FOUND, "'%s' not found" % self.path)

    # Handle no permission errors.
    def err_no_perm(self, msg):
        self.send_error(self.ERR_NO_PERM, msg)

    # Handle execution errors.
    def errExec(self, msg):
        self.send_error(self.ERR_NO_PERM, msg)

    # Write a log message if in debugging mode
    def log(self, msg):
        if self.Debug:
            print "nitinat:", msg

#----------------------------------------------------------------------

if __name__ == '__main__':

    # Main libraries
    import getopt

    # How to handle fatal startup errors
    def fatal(msg):
        print >> sys.stderr, "nitinat:", msg
        sys.exit(1)

    # Defaults
    host = ''
    port = 8080
    root = None

    # How to use
    Usage = "server.py [-h host] [-p port] [-v] -r|Root_Directory"

    # Handle command-line arguments
    options, rest = getopt.getopt(sys.argv[1:], "h:p:rv")

    for (flag, arg) in options:
        if flag == "-h":
            host = arg
            if not arg:
                msg = "No host given with -h"
                fatal(msg)
        elif flag == "-p":
            try:
                port = int(arg)
            except ValueError, msg:
                fatal("Unable to convert '%s' to integer: %s" % (arg, msg))
        elif flag == "-r":
            root = os.getcwd()
        elif flag == "-v":
            RequestHandler.Debug = True
        else:
            fatal(Usage)

    # Make sure root directory is set, and is a directory.
    if (root and rest) or (not root and not rest):
        fatal(Usage)
    if not root:
        root = os.path.abspath(rest[0])
    if not os.path.isdir(root):
        fatal("No such directory '%s'" % root)
    RequestHandler.Root_Directory = root

    # Create and run server.
    server_address = (host, port)
    server = BaseHTTPServer.HTTPServer(server_address, RequestHandler)
    server.serve_forever()

########NEW FILE########
__FILENAME__ = testcgi
# testcgi.py : simple CGI script.

import time

print "Content-type: text/html"
print
print "<html>"
print "<body>"
print "<h1>%s</h1>" % time.asctime()
print "</body>"
print "</html>"

########NEW FILE########
__FILENAME__ = testquery
# testquery.py : CGI script that echoes query parameters.

import time, cgiutil

rawData = cgiutil.getRawCgiData()
params = cgiutil.parseCgiData(rawData)

print "Content-type: text/html"
print
print "<html>"
print "<body>"
print "<h1>Query parameters as of %s</h1>" % time.asctime()
if not params:
    print "<p>No parameters</p>"
else:
    print "<p>%d parameter(s)</p>" % len(params)
    print '<table cellpadding="3" border="1">'
    keys = params.keys()
    keys.sort()
    for k in keys:
        v = cgiutil.htmlEncode('|'.join(params[k]))
        k = cgiutil.htmlEncode(k)
        print "<tr><td>%s</td><td>%s</td></tr>" % (k, v)
    print "</table>"
print "</body>"
print "</html>"

########NEW FILE########
__FILENAME__ = echo-client
'''Simple client that sends data, and waits for an echo.'''

import sys, socket

# How much data to receive at one time?
size = 1024

# Who to talk to, and what to say?
host, port, message = sys.argv[1], int(sys.argv[2]), sys.argv[3]

# Create a socket, and connect to a server.
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((host, port))

# Send message.
s.send(sys.argv[3])

# Wait for it to be echoed back.
data = s.recv(size)
print 'client received', `data`

# Put our toys away.
s.close()

########NEW FILE########
__FILENAME__ = echo-server
'''Simple server that echoes data back.'''

import sys, socket

size = 1024

# Empty string for host means 'this machine'.
host, port = '', int(sys.argv[1])

# Create and bind a socket.
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((host, port))

# Wait for a connection request.
s.listen(True)
conn, addr = s.accept()
print 'Connected by', addr

# Receive and display a message.
data = conn.recv(size)
print 'server saw', `data`

# Echo it back to the sender.
conn.send(data)

# Put our toys away.
conn.close()

########NEW FILE########
__FILENAME__ = telnet-client
'''Simple client that sends data read from standard input.'''

import sys
import socket

# Who to talk to, and what to say?
host, port = '', int(sys.argv[1])

# Create a socket, and connect to a server.
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((host, port))

# Send message.
data = sys.stdin.read()
s.send(data)

# Put our toys away.
s.close()

########NEW FILE########
__FILENAME__ = telnet-server
'''Server that echoes data back until there is no more.'''

import sys, socket

size, host, port = 1024, '', int(sys.argv[1])

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((host, port))
s.listen(True)
conn, addr = s.accept()
print 'Connected by', addr

result = ''
while True:
    data = conn.recv(size)
    print '...server:', `data`
    if not data:
        break
    result += data
print 'server saw', `result`

conn.close()

########NEW FILE########
