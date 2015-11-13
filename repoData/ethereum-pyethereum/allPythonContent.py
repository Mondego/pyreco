__FILENAME__ = environment
from distutils.util import strtobool as _bool
import os


def auto_discover_hooks():
    from os import path
    import pkgutil

    hooks = {}
    hook_dir = path.join(path.dirname(__file__), 'hooks')
    for finder, name, ispkg in pkgutil.iter_modules(path=[hook_dir]):
        module = finder.find_module(name).load_module(name)
        if not hasattr(module, 'hook'):
            continue
        hooks[name] = getattr(module, 'hook')

    return hooks


def before_all(context):
    context._hooks = auto_discover_hooks()


def before_feature(context, feature):
    hooks = context._hooks
    for tag in feature.tags:
        if tag in hooks:
            if hasattr(hooks[tag], 'before_feature'):
                hooks[tag].before_feature(context, feature)


def after_feature(context, feature):
    hooks = context._hooks
    for tag in feature.tags:
        if tag in hooks:
            if hasattr(hooks[tag], 'after_feature'):
                hooks[tag].after_feature(context, feature)


def before_scenario(context, scenario):
    hooks = context._hooks
    for tag in scenario.feature.tags:
        if tag in hooks:
            if hasattr(hooks[tag], 'before_scenario'):
                hooks[tag].before_scenario(context, scenario)

    for tag in scenario.tags:
        if tag in hooks:
            if hasattr(hooks[tag], 'before_scenario'):
                hooks[tag].before_scenario(context, scenario)


def after_scenario(context, scenario):
    hooks = context._hooks
    for tag in scenario.feature.tags:
        if tag in hooks:
            if hasattr(hooks[tag], 'after_scenario'):
                hooks[tag].after_scenario(context, scenario)

    for tag in scenario.tags:
        if tag in hooks:
            if hasattr(hooks[tag], 'after_scenario'):
                hooks[tag].after_scenario(context, scenario)


# USE: BEHAVE_DEBUG_ON_ERROR=yes     (to enable debug-on-error)
BEHAVE_DEBUG_ON_ERROR = _bool(os.environ.get("BEHAVE_DEBUG_ON_ERROR", "no"))


def after_step(context, step):
    if BEHAVE_DEBUG_ON_ERROR and step.status == "failed":
        # -- ENTER DEBUGGER: Zoom in on failure location.
        # NOTE: Use IPython debugger, same for pdb (basic python debugger).
        import ipdb
        ipdb.post_mortem(step.exc_traceback)

########NEW FILE########
__FILENAME__ = config
import uuid
import mock
import tempfile

from pyethereum.utils import sha3


class ConfigHook(object):
    def before_feature(self, context, feature):
        '''
        .. note::

            `context.conf` is used instead of `context.config` because `config`
            is used internally in `context` by *behave*

        '''
        context.conf = conf = mock.MagicMock()
        node_id = sha3(str(uuid.uuid1())).encode('hex')
        tempdir = tempfile.mkdtemp()

        def get_side_effect(section, option):
            if section == 'network' and option == 'client_id':
                return 'client id'

            if section == 'network' and option == 'listen_host':
                return '0.0.0.0'

            if section == 'network' and option == 'node_id':
                return node_id

            if section == 'wallet' and option == 'coinbase':
                return '0'*40

            if section == 'misc' and option == 'data_dir':
                return tempdir

        def getint_side_effect(section, option):
            if section == 'network' and option == 'listen_port':
                return 1234

            if section == 'network' and option == 'num_peers':
                return 10

        conf.get.side_effect = get_side_effect
        conf.getint.side_effect = getint_side_effect

hook = ConfigHook()

########NEW FILE########
__FILENAME__ = packeter
class PacketerHook(object):
    def before_feature(self, context, feature):
        from pyethereum.packeter import Packeter
        context.packeter = packeter = Packeter()
        packeter.configure(context.conf)

hook = PacketerHook()

########NEW FILE########
__FILENAME__ = peer
import mock
import utils


class PeerHook(object):
    ''' need @config before @peer
    '''
    def before_feature(self, context, feature):
        from pyethereum.packeter import packeter
        context.packeter = packeter
        packeter.configure(context.conf)
        context._connection = utils.mock_connection()

    def before_scenario(self, context, scenario):
        context.peer = utils.mock_peer(context._connection, '127.0.0.1', 1234)
        context.add_recv_packet, context.received_packets = \
            utils.mock_connection_recv(context._connection)
        context.sent_packets = utils.mock_connection_send(context._connection)

        time_sleep_patcher = mock.patch('time.sleep')
        time_sleep_patcher.start()
        context.time_sleep_patcher = time_sleep_patcher

    def after_scenario(self, context, scenario):
        context.time_sleep_patcher.stop()


hook = PeerHook()

########NEW FILE########
__FILENAME__ = peermanager
import mock
import utils


class PeerManagerHook(object):
    ''' need @config before @peermanager
    '''
    def before_feature(self, context, feature):
        from pyethereum.packeter import packeter

        context.packeter = packeter
        packeter.configure(context.conf)

    def before_scenario(self, context, scenario):
        from pyethereum.peermanager import PeerManager
        peer_manager = context.peer_manager = PeerManager()
        peer_manager.configure(context.conf)

        def run_side_effect():
            for i in range(3):
                peer_manager.loop_body()

        peer_manager.run = mock.MagicMock()
        peer_manager.run.side_effect = run_side_effect
        peer_manager.start = peer_manager.run

        def start_peer_side_effect(connection, ip, port):
            peer = utils.mock_peer(connection, ip, port)
            return peer

        peer_manager._start_peer = mock.MagicMock()
        peer_manager._start_peer = start_peer_side_effect

        time_sleep_patcher = mock.patch('time.sleep')
        time_sleep_patcher.start()
        context.time_sleep_patcher = time_sleep_patcher

    def after_scenario(self, context, scenario):
        context.time_sleep_patcher.stop()


hook = PeerManagerHook()

########NEW FILE########
__FILENAME__ = trie
import os
from os import path


class TrieHook(object):
    db_dir = "tmp"
    db_file_name = "trie-test.db"

    def __init__(self):
        self.db_path = path.join(self.db_dir, self.db_file_name)

    def before_feature(self, context, feature):
        from pyethereum import trie
        self._create_dir()
        self._delete_db()

        context.trie = trie.Trie(self.db_path)
        self._load_fixture()

    def after_feature(self, context, feature):
        del context.trie
        self._delete_db()

    def _create_dir(self):
        if not path.exists(self.db_dir):
            os.mkdir(self.db_dir)

    def _delete_db(self):
        import leveldb
        leveldb.DestroyDB(self.db_path)

    def _load_fixture(self):
        pass

    def before_scenario(self, context, scenario):
        pass

    def after_scenario(self, context, scenario):
        pass

hook = TrieHook()

########NEW FILE########
__FILENAME__ = utils
import mock
import socket


def mock_peer(connection, ip, port):
    from pyethereum.peer import Peer
    peer = Peer(connection, ip, port)

    def side_effect():
        for i in range(3):
            peer.loop_body()

    peer.run = mock.MagicMock()
    peer.run.side_effect = side_effect
    peer.start = peer.run
    return peer


def mock_connection():
    return mock.MagicMock(spec=socket.socket)


def mock_connection_recv(connection):
    received_packets = []

    def add_recv_packet(packet):
        received_packets.append(packet)

        def genarator(bufsize):
            for packet in received_packets:
                for i in range(0, len(packet), bufsize):
                    yield packet[i: i + bufsize]
                yield None

        status = dict()

        def side_effect(bufsize):
            if 'genarator' not in status:
                status.update(genarator=genarator(bufsize))

            try:
                buf = status['genarator'].next()
            except:
                buf = None

            if not buf:
                raise socket.error('time out')
            return buf

        connection.recv.side_effect = side_effect

    connection.recv = mock.MagicMock()
    add_recv_packet('')

    return (add_recv_packet, received_packets)


def mock_connection_send(connection):
    sent_packets = []

    def side_effect(packet):
        sent_packets.append(packet)
        return len(packet)

    connection.send = mock.MagicMock(side_effect=side_effect)
    return sent_packets

########NEW FILE########
__FILENAME__ = nibble_packing
from behave import register_type
from .utils import parse_py

from pyethereum import trie

register_type(Py=parse_py)


@given(u'nibbles: {src_nibbles:Py}')  # noqa
def step_impl(context, src_nibbles):
    context.src_nibbles = src_nibbles


@when(u'append a terminator')  # noqa
def step_impl(context):
    context.src_nibbles.append(trie.NIBBLE_TERMINATOR)


@when(u'packed to binary')  # noqa
def step_impl(context):
    context.dst_binary = trie.pack_nibbles(context.src_nibbles)


@then(u'in the binary, the first nibbles should be {first_nibble:Py}')  # noqa
def step_impl(context, first_nibble):
    assert ord(context.dst_binary[0]) & 0xF0 == first_nibble << 4
    context.prefix_nibbles_count = 1


@then(u'the second nibbles should be {second_nibble:Py}')  # noqa
def step_impl(context, second_nibble):
    assert ord(context.dst_binary[0]) & 0x0F == second_nibble
    context.prefix_nibbles_count = 2


@then(u'nibbles after should equal to the original nibbles')  # noqa
def step_impl(context):
    dst_nibbles = trie.unpack_to_nibbles(context.dst_binary)
    assert dst_nibbles == context.src_nibbles


@then(u'unpack the binary will get the original nibbles')  # noqa
def step_impl(context):
    assert context.src_nibbles == trie.unpack_to_nibbles(context.dst_binary)


@then(u'the packed result will be {dst:Py}')  # noqa
def step_impl(context, dst):
    assert context.dst_binary.encode('hex') == dst


@given(u'to be packed nibbles: {nibbles:Py} and terminator: {term:Py}')  # noqa
def step_impl(context, nibbles, term):
    context.src_nibbles = nibbles
    if term:
        context.src_nibbles.append(trie.NIBBLE_TERMINATOR)

########NEW FILE########
__FILENAME__ = packeter
from behave import register_type
from .utils import parse_py

from pyethereum import rlp
from pyethereum.utils import big_endian_to_int, recursive_int_to_big_endian

register_type(Py=parse_py)


@given(u'to be packeted payload data: {data:Py}')  # noqa
def step_impl(context, data):
    context.data = data
    context.encoded_data = rlp.encode(
        recursive_int_to_big_endian(context.data))


@when(u'dump the data to packet')  # noqa
def step_impl(context):
    context.packet = context.packeter.dump_packet(context.data)


@then(u'bytes [0:4) is synchronisation token: (0x22400891)')  # noqa
def step_impl(context):
    assert context.packet[:4] == '22400891'.decode('hex')


@then(u'bytes [4:8) is "payload(rlp serialized data) size" in form of big-endian integer')  # noqa
def step_impl(context):
    length = big_endian_to_int(context.packet[4:8])
    assert length == len(context.encoded_data)


@then(u'bytes [8:] data equal to RLP-serialised payload data')  # noqa
def step_impl(context):
    assert context.packet[8:] == context.encoded_data

########NEW FILE########
__FILENAME__ = peer
from utils import instrument
from pyethereum.utils import recursive_int_to_big_endian
import mock


@given(u'a packet')  # noqa
def step_impl(context):
    context.packet = context.packeter.dump_packet('this is a test packet')


@when(u'peer.send_packet is called')  # noqa
def step_impl(context):
    context.peer.send_packet(context.packet)


@when(u'all data with the peer is processed')  # noqa
def step_impl(context):
    context.peer.run()


@then(u'the packet sent through connection should be the given packet')  # noqa
def step_impl(context):
    assert context.sent_packets == [context.packet]


@when(u'peer.send_Hello is called')  # noqa
def step_impl(context):
    context.peer.send_Hello()


@then(u'the packet sent through connection should be a Hello packet')  # noqa
def step_impl(context):
    packet = context.packeter.dump_Hello()
    assert context.sent_packets == [packet]

@given(u'a valid Hello packet')  # noqa
def step_impl(context):
    context.packet = context.packeter.dump_Hello()

@given(u'a Hello packet with protocol version incompatible')  # noqa
def step_impl(context):
    packeter = context.packeter
    data = [packeter.cmd_map_by_name['Hello'],
            'incompatible_protocal_version',
            packeter.NETWORK_ID,
            packeter.CLIENT_ID,
            packeter.config.getint('network', 'listen_port'),
            packeter.CAPABILITIES,
            packeter.config.get('wallet', 'coinbase')
            ]
    context.packet = packeter.dump_packet(data)


@given(u'a Hello packet with network id incompatible')  # noqa
def step_impl(context):
    packeter = context.packeter
    data = [packeter.cmd_map_by_name['Hello'],
            packeter.PROTOCOL_VERSION,
            'incompatible_network_id',
            packeter.CLIENT_ID,
            packeter.config.getint('network', 'listen_port'),
            packeter.CAPABILITIES,
            packeter.config.get('wallet', 'coinbase')
            ]
    context.packet = packeter.dump_packet(data)


@when(u'peer.send_Hello is instrumented')  # noqa
def step_impl(context):
    context.peer.send_Hello = instrument(context.peer.send_Hello)


@then(u'peer.send_Hello should be called once')  # noqa
def step_impl(context):
    func = context.peer.send_Hello
    assert func.call_count == 1


@when(u'peer.send_Disconnect is instrumented')  # noqa
def step_impl(context):
    context.peer.send_Disconnect = instrument(context.peer.send_Disconnect)


@when(u'the packet is received from peer')  # noqa
def step_impl(context):
    context.add_recv_packet(context.packet)


@then(u'peer.send_Disconnect should be called once with args: reason')  # noqa
def step_impl(context):
    func = context.peer.send_Disconnect
    assert func.call_count == 1
    assert len(func.call_args[0]) == 1 or 'reason' in func.call_args[1]


@when(u'peer.send_Ping is called')  # noqa
def step_impl(context):
    context.peer.send_Ping()


@then(u'the packet sent through connection should be a Ping packet')  # noqa
def step_impl(context):
    packet = context.packeter.dump_Ping()
    assert context.sent_packets == [packet]


@given(u'a Ping packet')  # noqa
def step_impl(context):
    context.packet = context.packeter.dump_Ping()


@when(u'peer.send_Pong is instrumented')  # noqa
def step_impl(context):
    context.peer.send_Pong = instrument(context.peer.send_Pong)


@then(u'peer.send_Pong should be called once')  # noqa
def step_impl(context):
    func = context.peer.send_Pong
    assert func.call_count == 1


@when(u'peer.send_Pong is called')  # noqa
def step_impl(context):
    context.peer.send_Pong()


@then(u'the packet sent through connection should be a Pong packet')  # noqa
def step_impl(context):
    packet = context.packeter.dump_Pong()
    assert context.sent_packets == [packet]


@given(u'a Pong packet')  # noqa
def step_impl(context):
    context.packet = context.packeter.dump_Pong()


@when(u'handler for a disconnect_requested signal is registered')  # noqa
def step_impl(context):
    from pyethereum.signals import peer_disconnect_requested
    context.disconnect_requested_handler = mock.MagicMock()
    peer_disconnect_requested.connect(context.disconnect_requested_handler)


@when(u'peer.send_Disconnect is called')  # noqa
def step_impl(context):
    context.peer.send_Disconnect()


@then(u'the packet sent through connection should be'  # noqa
' a Disconnect packet')
def step_impl(context):
    packet = context.packeter.dump_Disconnect()
    assert context.sent_packets == [packet]


@then(u'the disconnect_requested handler should be called once'  # noqa
' after sleeping for at least 2 seconds')
def step_impl(context):
    import time  # time is already pathced for mocks
    assert context.disconnect_requested_handler.call_count == 1
    sleeping = sum(x[0][0] for x in time.sleep.call_args_list)
    assert sleeping >= 2


@given(u'a Disconnect packet')  # noqa
def step_impl(context):
    context.packet = context.packeter.dump_Disconnect()


@then(u'the disconnect_requested handler should be called once')  # noqa
def step_impl(context):
    assert context.disconnect_requested_handler.call_count == 1


@when(u'peer.send_GetPeers is called')  # noqa
def step_impl(context):
    context.peer.send_GetPeers()


@then(u'the packet sent through connection should be'  # noqa
' a GetPeers packet')
def step_impl(context):
    packet = context.packeter.dump_GetPeers()
    assert context.sent_packets == [packet]


@given(u'a GetPeers packet')  # noqa
def step_impl(context):
    context.packet = context.packeter.dump_GetPeers()


@given(u'peers data')  # noqa
def step_impl(context):
    context.peers_data = [
        ['127.0.0.1', 1234, 'local'],
        ['1.0.0.1', 1234, 'remote'],
    ]


@when(u'getpeers_received signal handler is connected')  # noqa
def step_impl(context):
    from pyethereum.signals import getpeers_received
    handler = mock.MagicMock()
    context.getpeers_received_handler = handler
    getpeers_received.connect(handler)


@then(u'the getpeers_received signal handler should be called once')  # noqa
def step_impl(context):
    assert context.getpeers_received_handler.call_count == 1


@when(u'peer.send_Peers is called')  # noqa
def step_impl(context):
    context.peer.send_Peers(context.peers_data)


@then(u'the packet sent through connection should be a Peers packet'  # noqa
' with the peers data')
def step_impl(context):
    assert context.sent_packets == [
        context.packeter.dump_Peers(context.peers_data)]


@given(u'a Peers packet with the peers data')  # noqa
def step_impl(context):
    context.packet = context.packeter.dump_Peers(context.peers_data)


@when(u'handler for new_peers_received signal is registered')  # noqa
def step_impl(context):
    context.new_peer_received_handler = mock.MagicMock()
    from pyethereum.signals import peer_addresses_received
    peer_addresses_received.connect(context.new_peer_received_handler)


@then(u'the new_peers_received handler should be called once'  # noqa
' with all peers')
def step_impl(context):
    call_args = context.new_peer_received_handler.call_args_list[0]
    call_peers = call_args[1]['addresses']
    assert len(call_peers) == len(context.peers_data)
    pairs = zip(call_peers, context.peers_data)
    for call, peer in pairs:
        assert call == peer
        #assert call[1]['address'] == peer

@when(u'peer.send_GetTransactions is called')  # noqa
def step_impl(context):
    context.peer.send_GetTransactions()


@then(u'the packet sent through connection should be'  # noqa
' a GetTransactions packet')
def step_impl(context):
    packet = context.packeter.dump_GetTransactions()
    assert context.sent_packets == [packet]


@given(u'a GetTransactions packet')  # noqa
def step_impl(context):
    context.packet = context.packeter.dump_GetTransactions()


@given(u'transactions data')  # noqa
def step_impl(context):
    context.transactions_data = [
        ['nonce-1', 'receiving_address-1', 1],
        ['nonce-2', 'receiving_address-2', 2],
        ['nonce-3', 'receiving_address-3', 3],
    ]


@when(u'gettransactions_received signal handler is connected')  # noqa
def step_impl(context):
    from pyethereum.signals import gettransactions_received
    handler = mock.MagicMock()
    context.gettransactions_received_handler = handler
    gettransactions_received.connect(handler)


@then(u'the gettransactions_received signal handler'  # noqa
      ' should be called once')
def step_impl(context):
    assert context.gettransactions_received_handler.call_count == 1


@when(u'peer.send_Transactions is called')  # noqa
def step_impl(context):
    context.peer.send_Transactions(context.transactions_data)


@then(u'the packet sent through connection should be'  # noqa
' a Transactions packet with the transactions data')
def step_impl(context):
    packet = context.packeter.dump_Transactions(context.transactions_data)
    assert context.sent_packets == [packet]


@given(u'a Transactions packet with the transactions data')  # noqa
def step_impl(context):
    packet = context.packeter.dump_Transactions(context.transactions_data)
    context.packet = packet


@when(u'handler for a new_transactions_received signal is registered')  # noqa
def step_impl(context):
    context.new_transactions_received_handler = mock.MagicMock()
    from pyethereum.signals import remote_transactions_received
    remote_transactions_received.connect(
        context.new_transactions_received_handler)


@then(u'the new_transactions_received handler'  # noqa
' should be called once with the transactions data')
def step_impl(context):
    mock = context.new_transactions_received_handler
    assert mock.call_count == 1
    assert mock.call_args[1]['transactions'] == recursive_int_to_big_endian(
        context.transactions_data)


@given(u'blocks data')  # noqa
def step_impl(context):
    # FIXME here we need real blocks.Block objects
    context.blocks_data = [
        ['block_headerA', ['txA1', 'txA2'], ['uncleA1', 'uncleA2']],
        ['block_headerB', ['txB', 'txB'], ['uncleB', 'uncleB2']],
    ]


@when(u'peer.send_Blocks is called')  # noqa
def step_impl(context):
    context.peer.send_Blocks(context.blocks_data)


@then(u'the packet sent through connection should be'  # noqa
' a Blocks packet with the blocks data')
def step_impl(context):
    packet = context.packeter.dump_Blocks(context.blocks_data)
    assert context.sent_packets == [packet]


@given(u'a Blocks packet with the blocks data')  # noqa
def step_impl(context):
    context.packet = context.packeter.dump_Blocks(context.blocks_data)


@when(u'handler for a new_blocks_received signal is registered')  # noqa
def step_impl(context):
    context.new_blocks_received_handler = mock.MagicMock()
    from pyethereum.signals import remote_blocks_received
    remote_blocks_received.connect(context.new_blocks_received_handler)


@then(u'the new_blocks_received handler should be'  # noqa
' called once with the blocks data')
def step_impl(context):
    context.new_blocks_received_handler = mock.MagicMock()
    from pyethereum.signals import remote_blocks_received
    remote_blocks_received.connect(
        context.new_blocks_received_handler)


@given(u'a GetChain request data')  # noqa
def step_impl(context):
    context.request_data = ['Parent1', 'Parent2', 3]


@when(u'peer.send_GetChain is called withe the request data')  # noqa
def step_impl(context):
    context.peer.send_GetChain(context.request_data)


@then(u'the packet sent through connection'  # noqa
' should be a GetChain packet')
def step_impl(context):
    packet = context.packeter.dump_GetChain(context.request_data)
    assert context.sent_packets == [packet]


@given(u'a GetChain packet with the request data')  # noqa
def step_impl(context):
    context.packet = context.packeter.dump_GetChain(context.request_data)


@given(u'a chain data provider')  # noqa
def step_impl(context):
    from pyethereum.signals import (local_chain_requested)

    def handler(sender, **kwargs):
        pass

    context.blocks_requested_handler = handler
    local_chain_requested.connect(handler)


@when(u'peer.send_Blocks is instrumented')  # noqa
def step_impl(context):
    context.peer.send_Blocks = instrument(context.peer.send_Blocks)


@when(u'peer.send_NotInChain is called')  # noqa
def step_impl(context):
    context.peer.send_NotInChain('some hash')


@then(u'the packet sent through connection should'  # noqa
' be a NotInChain packet')
def step_impl(context):
    packet = context.packeter.dump_NotInChain('some hash')
    assert context.sent_packets == [packet]


@given(u'a NotInChain packet')  # noqa
def step_impl(context):
    context.packet = context.packeter.dump_NotInChain('some hash')

########NEW FILE########
__FILENAME__ = peermanager
import utils
import mock
import os
import json
from pyethereum.utils import big_endian_to_int as idec

@given(u'data_dir')
def step_impl(context):
    context.data_dir = context.peer_manager.config.get('misc', 'data_dir')
    assert(not context.data_dir == None)

@given(u'a peers.json file exists')
def step_impl(context):
    peers = set([('12.13.14.15', 2002), ('14.15.16.17', 3003)])
    context.path = os.path.join(context.data_dir, 'peers.json')
    json.dump(list(peers), open(context.path, 'w'))

@given(u'_known_peers is empty')
def step_impl(context):
    assert(len(context.peer_manager._known_peers) == 0)

@when(u'load_saved_peers is called')
def step_impl(context):
    context.peer_manager.load_saved_peers()

@then(u'_known_peers should contain all peers in peers.json with blank node_ids')
def step_impl(context):
    peers = json.load(open(context.path))
    os.remove(context.path)
    for i,p in peers:
        assert((i, p, "") in context.peer_manager._known_peers)

@given(u'a peers.json file does not exist')
def step_impl(context):
    context.path = os.path.join(context.peer_manager.config.get('misc', 'data_dir'), 'peers.json')
    assert (not os.path.exists(context.path))

@then(u'_known_peers should still be empty')
def step_impl(context):
    assert (len(context.peer_manager._known_peers) == 0)

@given(u'peer data of (ip, port, node_id) in _known_peers')
def step_impl(context):
    context.peer_manager._known_peers = set([('12.13.14.15', 2002, "him"), ('14.15.16.17', 3003, "her")])

@when(u'save_peers is called')
def step_impl(context):
    context.peer_manager.save_peers()

@then(u'data_dir/peers.json should contain all peers in _known_peers')
def step_impl(context):
    context.path = os.path.join(context.peer_manager.config.get('misc', 'data_dir'), 'peers.json')
    peers = [(i, p) for i, p in json.load(open(context.path))]
    os.remove(context.path)
    for ip, port, nodeid in context.peer_manager._known_peers:
        assert((ip, port) in peers)

@given(u'peer data of (connection, ip, port) from _known_peers')
def step_impl(context):
    context.peer_manager._known_peers = set([('12.13.14.15', 2002, "him"), ('14.15.16.17', 3003, "her")])
    ip, port, nid = context.peer_manager._known_peers.pop()
    context.peer_data = (utils.mock_connection(), ip, port)

@when(u'add_peer is called with the given peer data')
def step_impl(context):
    context.peer = context.peer_manager.add_peer(*context.peer_data)

@then(u'connected_peers should contain the peer with the peer data')  # noqa
def step_impl(context):
    manager = context.peer_manager
    data = context.peer_data
    assert len(list(p for p in manager.connected_peers
               if p.connection() == data[0])) == 1

@given(u'peer data of (connection, ip, port) from a newly accepted connection')
def step_impl(context):
    context.peer_data = (utils.mock_connection(), '100.100.100.100', 10001)

@then(u'the peer\'s port should be the connection port, not the listen port')
def step_impl(context):
    assert(context.peer_data[2] != 30303) # this is a hack

@then(u'_known_peers should not contain peer (until Hello is received)')
def step_impl(context):
    assert (context.peer_data not in context.peer_manager._known_peers)

@given(u'peer data of (connection, ip, port)')  # noqa
def step_impl(context):
    context.peer_data = (utils.mock_connection(), '127.0.0.1', 1234)


@given(u'peer manager with connected peers')  # noqa
def step_impl(context):
    context.peer_manager.add_peer(utils.mock_connection(), '127.0.0.1', 1234)
    context.peer_manager.add_peer(utils.mock_connection(), '1.1.1.1', 1234)


@when(u'instrument each peer\'s `stop` method')  # noqa
def step_impl(context):
    for peer in context.peer_manager.connected_peers:
        peer.stop = utils.instrument(peer.stop)


@when(u'the peer manager\'s `stop` method is called')  # noqa
def step_impl(context):
    context.peer_manager.stop()


@then(u'each peer\'s `stop` method should be called once')  # noqa
def step_impl(context):
    for peer in context.peer_manager.connected_peers:
        assert peer.stop.call_count == 1


@given(u'connected peer addresses, with each item is (ip, port, node_id)')  # noqa
def step_impl(context):
    context.peer_addresses = (
        ('192.168.1.2', 1234, 'it'),
        ('192.18.1.2', 1234, 'he'),
        ('192.68.1.2', 1234, 'she'),
    )


@given(u'add the connected peer addresses to `connected_peers`')  # noqa
def step_impl(context):
    context.peer_manager.connected_peers = []
    for ip, port, node_id in context.peer_addresses:
        peer = utils.mock_peer(utils.mock_connection(), ip, port)
        peer.node_id = node_id
        context.peer_manager.connected_peers.append(peer)

@given(u'a Hello has been received from the peer')
def step_impl(context):
    for p in context.peer_manager.connected_peers:
        p.hello_received = True

@then(u'get_connected_peer_addresses should'  # noqa
' return the given peer addresses')
def step_impl(context):
    res = context.peer_manager.get_connected_peer_addresses()
    for peer_address in context.peer_addresses:
        assert peer_address in res


@given(u'peer address of (ip, port, node_id)')  # noqa
def step_impl(context):
    context.peer_address = ('192.168.1.1', 1234, 'me')


@when(u'add_known_peer_address is called with the given peer address')  # noqa
def step_impl(context):
    context.peer_manager.add_known_peer_address(*context.peer_address)


@then(u'get_known_peer_addresses should contain the given peer address')  # noqa
def step_impl(context):
    res = context.peer_manager.get_known_peer_addresses()
    assert context.peer_address in res


@given(u'the given peer is added')  # noqa
def step_impl(context):
    context.peer = context.peer_manager.add_peer(*context.peer_data)


@when(u'remove_peer is called with the peer')  # noqa
def step_impl(context):
    context.peer_manager.remove_peer(context.peer)


@then(u'the peer should be stopped')  # noqa
def step_impl(context):
    assert context.peer.stopped()


@then(u'the peer should not present in connected_peers')  # noqa
def step_impl(context):
    assert context.peer not in context.peer_manager.connected_peers


@when(u'_create_peer_sock')  # noqa
def step_impl(context):
    context.res = context.peer_manager._create_peer_sock()


@then(u'return a socket')  # noqa
def step_impl(context):
    assert context.res


@given(u'peer address of (host, port)')  # noqa
def step_impl(context):
    context.peer_address = ('myhost', 1234)


@when(u'socket is mocked')  # noqa
def step_impl(context):
    context.peer_manager._create_peer_sock = mock.MagicMock()
    context.sock = context.peer_manager._create_peer_sock.return_value
    context.sock.getpeername.return_value = ('192.168.1.1', 1234)


@then(u'socket.connect should be called with (host, port)')  # noqa
def step_impl(context):
    assert context.sock.connect.call_args[0][0] == context.peer_address


@when(u'call of socket.connect will success')  # noqa
def step_impl(context):
    pass


@when(u'add_peer is mocked, and the return value is recorded as peer')  # noqa
def step_impl(context):
    context.peer_manager.add_peer = mock.MagicMock()
    context.peer = context.peer_manager.add_peer.return_value


@when(u'send_Hello is mocked')  # noqa
def step_impl(context):
    context.peer_manager.send_Hello = mock.MagicMock()


@when(u'connect_peer is called with the given peer address')  # noqa
def step_impl(context):
    context.res = context.peer_manager.connect_peer(*context.peer_address)


@then(u'add_peer should be called once')  # noqa
def step_impl(context):
    assert context.peer_manager.add_peer.call_count == 1


@then(u'the peer should have send_Hello called once')  # noqa
def step_impl(context):
    assert context.peer.send_Hello.call_count == 1


@then(u'connect_peer should return peer')  # noqa
def step_impl(context):
    assert context.res == context.peer


@when(u'call of socket.connect will fail')  # noqa
def step_impl(context):
    def side_effect():
        raise Exception()
    context.sock.connect.side_effect = side_effect


@then(u'add_peer should not be called')  # noqa
def step_impl(context):
    assert context.peer_manager.add_peer.call_count == 0


@then(u'connect_peer should return None')  # noqa
def step_impl(context):
    assert context.res is None


@when(u'get_known_peer_addresses is mocked')  # noqa
def step_impl(context):
    context.peer_manager.get_known_peer_addresses = mock.MagicMock(
        return_value=set([
            ('192.168.1.1', 1234, 'it'),
            ('1.168.1.1', 1234, 'he'),
            ('1.1.1.1', 1234, context.conf.get('network', 'node_id')),
        ]))


@when(u'get_connected_peer_addresses is mocked')  # noqa
def step_impl(context):
    context.peer_manager.get_connected_peer_addresses = mock.MagicMock(
        return_value=set([
            ('192.168.1.1', 1234, 'it'),
            ('9.168.1.1', 1234, 'she'),
        ]))

@when(u'get_peer_candidates is called')  # noqa
def step_impl(context):
    context.res = context.peer_manager.get_peer_candidates()


@then(u'the result candidates should be right')  # noqa
def step_impl(context):
    right = set([
        ('1.168.1.1', 1234, 'he'),
    ])
    assert right == set(context.res)

@given(u'a mock stopped peer')  # noqa
def step_impl(context):
    from pyethereum.peer import Peer
    context.peer = mock.MagicMock(spec=Peer)
    context.peer.stopped = mock.MagicMock(return_value=True)


@when(u'remove_peer is mocked')  # noqa
def step_impl(context):
    context.peer_manager.remove_peer = mock.MagicMock()


@when(u'_check_alive is called with the peer')  # noqa
def step_impl(context):
    context.peer_manager._check_alive(context.peer)


@then(u'remove_peer should be called once with the peer')  # noqa
def step_impl(context):
    assert context.peer_manager.remove_peer.call_count == 1


@given(u'a mock normal peer')  # noqa
def step_impl(context):
    from pyethereum.peer import Peer
    context.peer = Peer(utils.mock_connection(), '1.1.1.1', 1234)
    context.peer.send_Ping = mock.MagicMock()


@when(u'time.time is patched')  # noqa
def step_impl(context):
    context.time_time_pactcher = mock.patch('pyethereum.peermanager.time.time')
    context.time_time = context.time_time_pactcher.start()
    context.time_time.return_value = 10


@when(u'ping was sent and not responsed in time')  # noqa
def step_impl(context):
    context.peer.last_pinged = 4
    context.peer.last_valid_packet_received = 1
    context.peer_manager.max_ping_wait = 5
    context.peer_manager.max_silence = 2

    now = context.time_time()
    dt_ping = now - context.peer.last_pinged
    dt_seen = now - context.peer.last_valid_packet_received

    assert dt_ping < dt_seen and dt_ping > context.peer_manager.max_ping_wait


@when(u'time.time is unpatched')  # noqa
def step_impl(context):
    context.time_time_pactcher.stop()


@when(u'peer is slient for a long time')  # noqa
def step_impl(context):
    context.peer.last_pinged = 4
    context.peer.last_valid_packet_received = 7
    context.peer_manager.max_ping_wait = 5
    context.peer_manager.max_silence = 2

    now = context.time_time()
    dt_ping = now - context.peer.last_pinged
    dt_seen = now - context.peer.last_valid_packet_received

    assert min(dt_seen, dt_ping) > context.peer_manager.max_silence


@then(u'peer.send_Ping should be called once')  # noqa
def step_impl(context):
    assert context.peer.send_Ping.call_count == 1


@given(u'connected peers')  # noqa
def step_impl(context):
    from pyethereum.peer import Peer
    context.peer_manager.connected_peers = [
        Peer(utils.mock_connection(), '1.1.1.1', 1234),
        Peer(utils.mock_connection(), '2.1.1.1', 1234),
    ]


@when(u'connect_peer is mocked')  # noqa
def step_impl(context):
    context.peer_manager.connect_peer = mock.MagicMock()


@given(u'known peers')  # noqa
def step_impl(context):
    context.peer_manager._known_peers = [
        ('192.168.1.2', 1234, 'it'),
        ('192.18.1.2', 1234, 'he'),
        ('192.68.1.2', 1234, 'she')]


@when(u'connected peers less then configured number of peers')  # noqa
def step_impl(context):
    configured_number = context.conf.getint('network', 'num_peers')
    assert len(context.peer_manager.connected_peers) < configured_number


@when(u'have candidate peer')  # noqa
def step_impl(context):
    candidates = context.peer_manager.get_peer_candidates()
    assert len(candidates)


@when(u'save known_peers count')  # noqa
def step_impl(context):
    context.known_peers_count_saved = len(context.peer_manager._known_peers)


@when(u'_connect_peers is called')  # noqa
def step_impl(context):
    context.peer_manager._connect_peers()


@then(u'connect_peer should be called')  # noqa
def step_impl(context):
    assert context.peer_manager.connect_peer.call_count == 1


@then(u'known_peers should be one less the saved count')  # noqa
def step_impl(context):
    assert context.known_peers_count_saved - 1 == \
        len(context.peer_manager._known_peers)


@when(u'have no candidate peer')  # noqa
def step_impl(context):
    context.peer_manager.get_peer_candidates = mock.MagicMock(
        return_value=[])


@when(u'for each connected peer, send_GetPeers is mocked')  # noqa
def step_impl(context):
    for peer in context.peer_manager.connected_peers:
        peer.send_GetPeers = mock.MagicMock()


@then(u'for each connected peer, send_GetPeers should be called')  # noqa
def step_impl(context):
    for peer in context.peer_manager.connected_peers:
        assert peer.send_GetPeers.call_count == 1


@given(u'a peer in connected_peers')  # noqa
def step_impl(context):
    # a random peer with connection port and no id
    context.peer_data = (utils.mock_connection(), '4.5.6.7', 55555)
    context.peer = context.peer_manager._start_peer(*context.peer_data)
    context.peer.node_id = ""

    context.packeter.NODE_ID = 'this is a different node id'

@when(u'Hello is received from the peer')
def step_impl(context):
    from pyethereum.signals import peer_handshake_success
    from pyethereum.peermanager import new_peer_connected

    peer_handshake_success.disconnect(new_peer_connected)

    def peer_handshake_success_handler(sender, peer, **kwargs):
        ipn = peer.ip, peer.port, peer.node_id
        context.peer_manager.add_known_peer_address(*ipn)
    peer_handshake_success.connect(peer_handshake_success_handler)

    context.packet = context.packeter.dump_Hello()
    decoded_packet = context.packeter.load_packet(context.packet)[1][3]
    context.peer._recv_Hello(decoded_packet)

@then(u'the peers port and node id should be reset to their correct values')  # noqa
def step_impl(context):
    from pyethereum.utils import big_endian_to_int as idec
    decoded_packet = context.packeter.load_packet(context.packet)[1][3]
    port = idec(decoded_packet[3])
    node_id = decoded_packet[5]
    assert(context.peer.port == port)
    assert(context.peer.node_id == node_id)

@then(u'peer_manager._known_peers should contain the peer')  # noqa
def step_impl(context):
    i, p, n = context.peer.ip, context.peer.port, context.peer.node_id
    assert((i, p, n) in context.peer_manager._known_peers)

@when(u'_recv_Peers is called')
def step_impl(context):
    from pyethereum.signals import peer_addresses_received
    from pyethereum.peermanager import peer_addresses_received_handler

    peer_addresses_received.disconnect(peer_addresses_received_handler)

    def peer_addresses_received_handler(sender, addresses, **kwargs):
        for address in addresses:
            context.peer_manager.add_known_peer_address(*address)
        context.peer_manager.save_peers()
    peer_addresses_received.connect(peer_addresses_received_handler)

    context.peers_to_send = [('9.8.7.6', 3000, 'him'), ('10.9.8.7', 4000, 'her'), ('12.11.10.9', 5000, 'she')]
    context.packet = context.packeter.dump_Peers(context.peers_to_send)
    decoded_packet = context.packeter.load_packet(context.packet)[1][3]
    context.peer._recv_Peers(decoded_packet)

@then(u'all received peers should be added to _known_peers and saved to peers.json')
def step_impl(context):
    context.path = os.path.join(context.peer_manager.config.get('misc', 'data_dir'), 'peers.json')
    saved_peers = [(i, p) for i, p in json.load(open(context.path))]
    os.remove(context.path)
    for ip, port, nodeid in context.peers_to_send:
        assert((ip, port) in saved_peers)
        assert((ip, port, nodeid) in context.peer_manager._known_peers)

@given(u'a known connected peer with incompatible protocol version')
def step_impl(context):
    context.peer_data = (utils.mock_connection(), '4.5.6.7', 55555)
    context.peer = context.peer_manager.add_peer(*context.peer_data)
    context.ipn = (context.peer.ip, context.peer.port, context.peer.node_id)
    context.peer_manager._known_peers.add(context.ipn)
    context.peer_protocol_version = 0xff

@when(u'send_Disconnect is called with reason "Incompatible"')
def step_impl(context):
    from pyethereum.signals import peer_disconnect_requested
    from pyethereum.peermanager import disconnect_requested_handler

    peer_disconnect_requested.disconnect(disconnect_requested_handler)

    def disconnect_requested_handler(sender, peer, forget=False, **kwargs):
        context.peer_manager.remove_peer(peer)
        if forget:
            ipn = (peer.ip, peer.port, peer.node_id)
            if ipn in context.peer_manager._known_peers:
                context.peer_manager._known_peers.remove(ipn)
                context.peer_manager.save_peers()

    peer_disconnect_requested.connect(disconnect_requested_handler)
    context.peer.send_Disconnect(reason='Incompatible network protocols')

@then(u'peer should be removed from _known_peers')
def step_impl(context):
    ipn = (context.peer.ip, context.peer.port, context.peer.node_id)
    assert(ipn not in context.peer_manager._known_peers)



########NEW FILE########
__FILENAME__ = processblock
from pyethereum import transactions, blocks, processblock, utils

@given(u'a block')
def step_impl(context):
    context.key = utils.sha3('cows')
    context.addr = utils.privtoaddr(context.key)
    context.gen = blocks.genesis({context.addr: 10**60})

@given(u'a contract which returns the result of the SHA3 opcode')
def step_impl(context):
    '''
    serpent: 'return(sha3(msg.data[0]))'
    assembly: ['$begincode_0.endcode_0', 'DUP', 'MSIZE', 'SWAP', 'MSIZE', '$begincode_0', 'CALLDATACOPY', 'RETURN', '~begincode_0', '#CODE_BEGIN', 32, 'MSIZE', 0L, 'CALLDATALOAD', 'MSIZE', 'MSTORE', 'SHA3', 'MSIZE', 'SWAP', 'MSIZE', 'MSTORE', 32, 'SWAP', 'RETURN', '#CODE_END', '~endcode_0']
     byte code: 6011515b525b600a37f260205b6000355b54205b525b54602052f2
    '''
    code = '6011515b525b600a37f260205b6000355b54205b525b54602052f2'.decode('hex')

    tx_contract = transactions.contract(0,10,10**30, 10**30, code).sign(context.key)
    success, context.contract = processblock.apply_tx(context.gen, tx_contract)
    assert(success)


@when(u'a msg is sent to the contract with msg.data[0] = \'hello\'')
def step_impl(context):
    word = 'hello'
    msg = context.msg = '\x00'*(32-len(word))+word
    tx = transactions.Transaction(1, 100, 10**40, context.contract, 0, msg).sign(context.key)
    success, context.ans = processblock.apply_tx(context.gen, tx)
    assert(success)


@when(u'a msg is sent to the contract with msg.data[0] = 342156')
def step_impl(context):
    word = 342156
    word = hex(word)[2:]
    if len(word)%2 != 0: word = '0' + word
    msg = context.msg = '\x00'*(32-len(word)/2)+word.decode('hex')
    tx = transactions.Transaction(1, 100, 10**40, context.contract, 0, msg).sign(context.key)
    success, context.ans = processblock.apply_tx(context.gen, tx)
    assert(success)

@when(u'a msg is sent to the contract with msg.data[0] = \'a5b2cc1f54\'')
def step_impl(context):
    word = 'a5b2cc1f54'
    msg = context.msg = '\x00'*(32-len(word))+word
    tx = transactions.Transaction(1, 100, 10**40, context.contract, 0, msg).sign(context.key)
    success, context.ans = processblock.apply_tx(context.gen, tx)
    assert(success)

@then(u'the contract should return the result of sha3(msg.data[0])')
def step_impl(context):
    assert (context.ans == utils.sha3(context.msg))

########NEW FILE########
__FILENAME__ = rlp
from behave import register_type
from .utils import parse_py, AssertException

from pyethereum.utils import int_to_big_endian, recursive_int_to_big_endian
from pyethereum import rlp

register_type(Py=parse_py)


@given(u'a to be rlp encoded payload: {src:Py}')  # noqa
def step_impl(context, src):
    context.src = recursive_int_to_big_endian(src)


@when(u'encoded in RLP')  # noqa
def step_impl(context):
    context.dst = rlp.encode(context.src)


@then(u'decode the RLP encoded data will get the original data')  # noqa
def step_impl(context):
    assert context.src == rlp.decode(context.dst)


@then(u'the byte is its own RLP encoding')  # noqa
def step_impl(context):
    assert context.dst == context.src


@then(u'the first byte is 0x80 plus the length of the string')  # noqa
def step_impl(context):
    assert context.dst[0] == chr(0x80 + len(context.src))


@then(u'followed by the string')  # noqa
def step_impl(context):
    assert context.dst[1:] == context.src


@then(u'the first byte is 0xb7 plus the length of the length of the string')  # noqa
def step_impl(context):
    context.length_bin = int_to_big_endian(len(context.src))
    assert context.dst[0] == chr(0xb7 + len(context.length_bin))


@then(u'following bytes are the payload string length')
def step_impl(context):
    assert context.dst[1:1 + len(context.length_bin)] == context.length_bin


@then(u'following bytes are the payload string itself')
def step_impl(context):
    assert context.dst[1 + len(context.length_bin):] == context.src


@then(u'the first byte is 0xc0 plus the length of the list')  # noqa
def step_impl(context):
    total_payload_length = sum(len(rlp.encode(x)) for x in context.src)
    assert context.dst[0] == chr(0xc0 + total_payload_length)


@then(u'following bytes are concatenation of the RLP encodings of the items')  # noqa
def step_impl(context):
    assert context.dst[1:] == ''.join(rlp.encode(x) for x in context.src)


@then(u'the first byte is 0xf7 plus the length of the length of the list')  # noqa
def step_impl(context):
    total_payload_length = sum(len(rlp.encode(x)) for x in context.src)
    context.length_bin = int_to_big_endian(total_payload_length)
    assert context.dst[0] == chr(0xf7 + len(context.length_bin))


@then(u'following bytes are the payload list length')  # noqa
def step_impl(context):
    assert context.dst[1:1 + len(context.length_bin)] == context.length_bin


@then(u'following bytes are the payload list itself')  # noqa
def step_impl(context):
    encodeds = [rlp.encode(x) for x in context.src]
    assert context.dst[1 + len(context.length_bin):] == ''.join(encodeds)


@then(u'raise TypeError')  # noqa
def step_impl(context):
    with AssertException(TypeError):
        rlp.encode(context.src)


@then(u'the rlp encoded result will be equal to {dst:Py}')  # noqa
def step_impl(context, dst):
    assert context.dst.encode('hex') == dst

########NEW FILE########
__FILENAME__ = trie
from behave import register_type
from .utils import parse_py

import random
from pyethereum import trie

register_type(Py=parse_py)


def gen_random_value():
    value = range(random.randint(5, 40))
    value.extend([0]*20)
    random.shuffle(value)
    value = ''.join(str(x) for x in value)
    return value


@when(u'clear trie tree')  # noqa
def step_impl(context):
    context.trie.clear()


@then(u'root will be blank')  # noqa
def step_impl(context):
    assert context.trie.root_hash == trie.BLANK_ROOT


@given(u'pairs with keys: {keys:Py}')  # noqa
def step_impl(context, keys):
    context.pairs = []
    for key in keys:
        context.pairs.append((key, gen_random_value()))


@when(u'insert pairs')  # noqa
def step_impl(context):
    for (key, value) in context.pairs:
        context.trie.update(key, value)


@then(u'for each pair, get with key will return the correct value')  # noqa
def step_impl(context):
    for (key, value) in context.pairs:
        assert context.trie.get(key) == str(value)


@then(u'get by the key: {key:Py} will return BLANK')  # noqa
def step_impl(context, key):
    assert context.trie.get(key) == ''


@when(u'insert pairs except key: {key:Py}')  # noqa
def step_impl(context, key):
    pairs = []
    for k, v in context.pairs:
        if k != key:
            v = gen_random_value()
            context.trie.update(k, v)
            pairs.append((k, v))
    context.pairs = pairs


@when(u'record hash as old hash')  # noqa
def step_impl(context):
    context.old_hash = context.trie.root_hash


@when(u'insert pair with key: {key:Py}')  # noqa
def step_impl(context, key):
    v = gen_random_value()
    context.trie.update(key, v)


@when(u'record hash as new hash')  # noqa
def step_impl(context):
    context.new_hash = context.trie.root_hash


@then(u'for keys except {key:Py}, get with key will'  # noqa
      ' return the correct value')
def step_impl(context, key):
    for k, v in context.pairs:
        if k != key:
            assert context.trie.get(k) == v


@then(u'old hash is the same with new hash')  # noqa
def step_impl(context):
    assert context.old_hash == context.new_hash


@when(u'delete by the key: {key:Py}')  # noqa
def step_impl(context, key):
    context.trie.delete(key)


@when(u'update by the key: {key:Py}')  # noqa
def step_impl(context, key):
    new_pairs = []
    for (k, v) in context.pairs:
        if k == key:
            v = gen_random_value()
            context.trie.update(k, v)
        new_pairs.append((k, v))
    context.pairs = new_pairs


@then(u'get size will return the correct number')  # noqa
def step_impl(context):
    assert len(context.trie) == len(context.pairs)


@then(u'to_dict will return the correct dict')  # noqa
def step_impl(context):
    res = context.trie.to_dict()
    assert dict(context.pairs) == res


@given(u'input dictionary: {input_dict:Py}')  # noqa
def step_impl(context, input_dict):
    context.input_dict = input_dict


@when(u'build trie tree from the input')  # noqa
def step_impl(context):
    if isinstance(context.input_dict, dict):
        dic = context.input_dict.iteritems()
    else:
        dic = context.input_dict
    for key, value in dic:
        context.trie.update(key, value)


@given(u'trie fixtures file path')  # noqa
def step_impl(context):
    context.trie_fixture_path = 'fixtures/trietest.json'


@when(u'load the trie fixtures')  # noqa
def step_impl(context):
    import json
    data = json.load(file(context.trie_fixture_path))
    context.examples = data


@then(u'for each example, then the hash of the tree root'  # noqa
' is the expectation')
def step_impl(context):
    for title, example in context.examples.iteritems():
        context.trie.clear()
        for pair in example['inputs']:
            context.trie.update(pair[0], pair[1])
        hex_hash = context.trie.root_hash.encode('hex')
        assert hex_hash == example['expectation'], '{} fails'.format(title)

########NEW FILE########
__FILENAME__ = utils
import random  # noqa
import math  # noqa
from contextlib import contextmanager
import parse

import mock


@parse.with_pattern(r"[\s\S]+")
def parse_py(text):
    exec("val = {0}".format(text))
    return val  # noqa


@contextmanager
def AssertException(e):
    caught = False
    try:
        yield
    except e:
        caught = True
    assert caught


def instrument(func):
    instrumented = mock.MagicMock()
    instrumented.side_effect = lambda *args, **kwargs: func(*args, **kwargs)
    return instrumented

########NEW FILE########
__FILENAME__ = wireprotocol

########NEW FILE########
__FILENAME__ = apiclient
#!/usr/bin/env python
import sys
import requests
import json
from common import make_pyethereum_avail
make_pyethereum_avail()
import utils
import transactions
from apiserver import base_url
base_url = "http://127.0.0.1:30203" + base_url


k = utils.sha3('heiko')
v = utils.privtoaddr(k)
k2 = utils.sha3('horse')
v2 = utils.privtoaddr(k2)

# Give tx2 some money
# nonce,gasprice,startgas,to,value,data,v,r,s
value = 10 ** 16
print value, 'from', v, 'to', v2

nonce = int(sys.argv[1])

tx = transactions.Transaction(
    nonce, gasprice=10 ** 12, startgas=10000, to=v2, value=10 ** 16, data='').sign(k)

data = tx.hex_serialize()

url = base_url + '/transactions/'
print 'PUT', url, data
r = requests.put(url, data)
print r.status_code, r.reason, r.url

########NEW FILE########
__FILENAME__ = apiserver
import logging
import threading
import json

import bottle

from pyethereum.chainmanager import chain_manager
from pyethereum.peermanager import peer_manager
import pyethereum.dispatch as dispatch
from pyethereum.blocks import block_structure
import pyethereum.signals as signals
from pyethereum.transactions import Transaction

logger = logging.getLogger(__name__)
base_url = '/api/v0alpha'

app = bottle.Bottle()
app.config['autojson'] = True


class ApiServer(threading.Thread):

    def __init__(self):
        super(ApiServer, self).__init__()
        self.daemon = True
        self.listen_host = '127.0.0.1'
        self.port = 30203

    def configure(self, config):
        self.listen_host = config.get('api', 'listen_host')
        self.port = config.getint('api', 'listen_port')

    def run(self):
        middleware = CorsMiddleware(app)
        bottle.run(middleware, server='waitress',
                   host=self.listen_host, port=self.port)

# ###### create server ######

api_server = ApiServer()


@dispatch.receiver(signals.config_ready)
def config_api_server(sender, config, **kwargs):
    api_server.configure(config)


# #######cors##############
class CorsMiddleware:
    HEADERS = [
        ('Access-Control-Allow-Origin', '*'),
        ('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'),
        ('Access-Control-Allow-Headers',
         'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token')
    ]

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        if environ["REQUEST_METHOD"] == "OPTIONS":
            start_response('200 OK',
                           CorsMiddleware.HEADERS + [('Content-Length', "0")])
            return ""
        else:
            def my_start_response(status, headers, exc_info=None):
                headers.extend(CorsMiddleware.HEADERS)

                return start_response(status, headers, exc_info)
            return self.app(environ, my_start_response)


# ######### Utilities ########
def load_json_req():
    json_body = bottle.request.json
    if not json_body:
        json_body = json.load(bottle.request.body)
    return json_body


# ######## Blocks ############
def make_blocks_response(blocks):
    objs = []
    for block in blocks:
        obj = block.to_dict()
        for item_name, item_type, _ in block_structure:
            if item_type in ["bin", "trie_root"]:
                obj[item_name] = obj[item_name].encode('hex')
        objs.append(obj)

    return dict(blocks=objs)


@app.get(base_url + '/blocks/')
def blocks():
    logger.debug('blocks/')
    return make_blocks_response(chain_manager.get_chain(start='', count=20))


@app.get(base_url + '/blocks/<blockhash>')
def block(blockhash=None):
    logger.debug('blocks/%s', blockhash)
    blockhash = blockhash.decode('hex')
    if blockhash in chain_manager:
        return make_blocks_response(chain_manager.get(blockhash))
    else:
        return bottle.abort(404, 'No block with id %s' % blockhash)


# ######## Transactions ############
@app.put(base_url + '/transactions/')
def transactions():
    # request.json FIXME / post json encoded data? i.e. the representation of
    # a tx
    hex_data = bottle.request.body.read()
    logger.debug('PUT transactions/ %s', hex_data)
    tx = Transaction.hex_deserialize(hex_data)
    signals.local_transaction_received.send(sender=None, transaction=tx)
    return bottle.redirect(base_url + '/transactions/' + tx.hex_hash())


# ######## Accounts ############
@app.get(base_url + '/accounts/')
def accounts():
    logger.debug('accounts')
    pass


@app.get(base_url + '/accounts/<address>')
def account(address=None):
    logger.debug('account/%s', address)
    pass


# ######## Peers ###################
def make_peers_response(peers):
    objs = [dict(ip=ip, port=port, node_id=node_id.encode('hex'))
            for (ip, port, node_id) in peers]
    return dict(peers=objs)


@app.get(base_url + '/peers/connected')
def connected_peers():
    return make_peers_response(peer_manager.get_connected_peer_addresses())


@app.get(base_url + '/peers/known')
def known_peers():
    return make_peers_response(peer_manager.get_known_peer_addresses())

########NEW FILE########
__FILENAME__ = blocks
import time
import rlp
import trie
import db
import utils
import processblock
import transactions


INITIAL_DIFFICULTY = 2 ** 22
GENESIS_PREVHASH = '\00' * 32
GENESIS_COINBASE = "0" * 40
GENESIS_NONCE = utils.sha3(chr(42))
GENESIS_GAS_LIMIT = 10 ** 6
MIN_GAS_LIMIT = 10 ** 4
GASLIMIT_EMA_FACTOR = 1024
BLOCK_REWARD = 1500 * utils.denoms.finney
UNCLE_REWARD = 7 * BLOCK_REWARD / 8
BLOCK_DIFF_FACTOR = 1024
GENESIS_MIN_GAS_PRICE = 0
BLKLIM_FACTOR_NOM = 6
BLKLIM_FACTOR_DEN = 5

GENESIS_INITIAL_ALLOC = \
    {"8a40bfaa73256b60764c1bf40675a99083efb075": 2 ** 200,  # (G)
     "e6716f9544a56c530d868e4bfbacb172315bdead": 2 ** 200,  # (J)
     "1e12515ce3e0f817a4ddef9ca55788a1d66bd2df": 2 ** 200,  # (V)
     "1a26338f0d905e295fccb71fa9ea849ffa12aaf4": 2 ** 200,  # (A)
     "2ef47100e0787b915105fd5e3f4ff6752079d5cb": 2 ** 200,  # (M)
     "cd2a3d9f938e13cd947ec05abc7fe734df8dd826": 2 ** 200,  # (R)
     "6c386a4b26f73c802f34673f7248bb118f97424a": 2 ** 200,  # (HH)
     "e4157b34ea9615cfbde6b4fda419828124b70c78": 2 ** 200,  # (CH)
     }

block_structure = [
    ["prevhash", "bin", "\00" * 32],
    ["uncles_hash", "bin", utils.sha3(rlp.encode([]))],
    ["coinbase", "addr", GENESIS_COINBASE],
    ["state_root", "trie_root", trie.BLANK_ROOT],
    ["tx_list_root", "trie_root", trie.BLANK_ROOT],
    ["difficulty", "int", INITIAL_DIFFICULTY],
    ["number", "int", 0],
    ["min_gas_price", "int", GENESIS_MIN_GAS_PRICE],
    ["gas_limit", "int", GENESIS_GAS_LIMIT],
    ["gas_used", "int", 0],
    ["timestamp", "int", 0],
    ["extra_data", "bin", ""],
    ["nonce", "bin", ""],
]

block_structure_rev = {}
for i, (name, typ, default) in enumerate(block_structure):
    block_structure_rev[name] = [i, typ, default]

acct_structure = [
    ["balance", "int", 0],
    ["nonce", "int", 0],
    ["storage", "trie_root", trie.BLANK_ROOT],
    ["code", "hash", ""],
]


acct_structure_rev = {}
for i, (name, typ, default) in enumerate(acct_structure):
    acct_structure_rev[name] = [i, typ, default]


def calc_difficulty(parent, timestamp):
    offset = parent.difficulty / BLOCK_DIFF_FACTOR
    sign = 1 if timestamp - parent.timestamp < 42 else -1
    return parent.difficulty + offset * sign


def calc_gaslimit(parent):
    prior_contribution = parent.gas_limit * (GASLIMIT_EMA_FACTOR - 1)
    new_contribution = parent.gas_used * BLKLIM_FACTOR_NOM / BLKLIM_FACTOR_DEN
    gl = (prior_contribution + new_contribution) / GASLIMIT_EMA_FACTOR
    return max(gl, MIN_GAS_LIMIT)


class UnknownParentException(Exception):
    pass


class TransientBlock(object):

    """
    Read only, non persisted, not validated representation of a block
    """

    def __init__(self, rlpdata):
        self.rlpdata = rlpdata
        self.hash = utils.sha3(rlpdata)
        header_args, transaction_list, uncles = rlp.decode(rlpdata)
        self.transaction_list = transaction_list  # rlp encoded transactions
        self.uncles = uncles
        for i, (name, typ, default) in enumerate(block_structure):
            setattr(self, name, utils.decoders[typ](header_args[i]))

    def __repr__(self):
        return '<TransientBlock(#%d %s %s)>' %\
            (self.number, self.hash.encode('hex')[
             :4], self.prevhash.encode('hex')[:4])


class Block(object):

    def __init__(self,
                 prevhash='\00' * 32,
                 uncles_hash=block_structure_rev['uncles_hash'][2],
                 coinbase=block_structure_rev['coinbase'][2],
                 state_root=trie.BLANK_ROOT,
                 tx_list_root=trie.BLANK_ROOT,
                 difficulty=block_structure_rev['difficulty'][2],
                 number=0,
                 min_gas_price=block_structure_rev['min_gas_price'][2],
                 gas_limit=block_structure_rev['gas_limit'][2],
                 gas_used=0, timestamp=0, extra_data='', nonce='',
                 transaction_list=[],
                 uncles=[]):

        self.prevhash = prevhash
        self.uncles_hash = uncles_hash
        self.coinbase = coinbase
        self.difficulty = difficulty
        self.number = number
        self.min_gas_price = min_gas_price
        self.gas_limit = gas_limit
        self.gas_used = gas_used
        self.timestamp = timestamp
        self.extra_data = extra_data
        self.nonce = nonce
        self.uncles = uncles

        self.transactions = trie.Trie(utils.get_db_path(), tx_list_root)
        self.transaction_count = 0

        self.state = trie.Trie(utils.get_db_path(), state_root)

        if transaction_list:
            # support init with transactions only if state is known
            assert self.state.root_hash_valid()
            for tx_serialized, state_root, gas_used_encoded \
                    in transaction_list:
                self._add_transaction_to_list(
                    tx_serialized, state_root, gas_used_encoded)

        # make sure we are all on the same db
        assert self.state.db.db == self.transactions.db.db

        # Basic consistency verifications
        if not self.state.root_hash_valid():
            raise Exception(
                "State Merkle root not found in database! %r" % self)
        if tx_list_root != self.transactions.root_hash:
            raise Exception("Transaction list root hash does not match!")
        if not self.transactions.root_hash_valid():
            raise Exception(
                "Transactions root not found in database! %r" % self)
        if utils.sha3(rlp.encode(self.uncles)) != self.uncles_hash:
            raise Exception("Uncle root hash does not match!")
        if len(self.uncles) != len(set(self.uncles)):
            raise Exception("Uncle hash not uniqe in uncles list")
        if len(self.extra_data) > 1024:
            raise Exception("Extra data cannot exceed 1024 bytes")
        if self.coinbase == '':
            raise Exception("Coinbase cannot be empty address")
        if not self.is_genesis() and self.nonce and\
                not self.check_proof_of_work(self.nonce):
            raise Exception("PoW check failed")

    def is_genesis(self):
        return self.prevhash == GENESIS_PREVHASH and \
            self.nonce == GENESIS_NONCE

    def check_proof_of_work(self, nonce):
        assert len(nonce) == 32
        rlp_Hn = self.serialize_header_without_nonce()
        # BE(SHA3(SHA3(RLP(Hn)) o n))
        h = utils.sha3(utils.sha3(rlp_Hn) + nonce)
        l256 = utils.big_endian_to_int(h)
        return l256 < 2 ** 256 / self.difficulty

    @classmethod
    def deserialize(cls, rlpdata):
        header_args, transaction_list, uncles = rlp.decode(rlpdata)
        assert len(header_args) == len(block_structure)
        kargs = dict(transaction_list=transaction_list, uncles=uncles)
        # Deserialize all properties
        for i, (name, typ, default) in enumerate(block_structure):
            kargs[name] = utils.decoders[typ](header_args[i])

        # if we don't have the state we need to replay transactions
        _db = db.DB(utils.get_db_path())
        if len(kargs['state_root']) == 32 and kargs['state_root'] in _db:
            return Block(**kargs)
        elif kargs['prevhash'] == GENESIS_PREVHASH:
            return Block(**kargs)
        else:  # no state, need to replay
            try:
                parent = get_block(kargs['prevhash'])
            except KeyError:
                raise UnknownParentException(kargs['prevhash'].encode('hex'))
            return parent.deserialize_child(rlpdata)

    def deserialize_child(self, rlpdata):
        """
        deserialization w/ replaying transactions
        """
        header_args, transaction_list, uncles = rlp.decode(rlpdata)
        assert len(header_args) == len(block_structure)
        kargs = dict(transaction_list=transaction_list, uncles=uncles)
        # Deserialize all properties
        for i, (name, typ, default) in enumerate(block_structure):
            kargs[name] = utils.decoders[typ](header_args[i])

        block = Block.init_from_parent(self, kargs['coinbase'],
                                       extra_data=kargs['extra_data'],
                                       timestamp=kargs['timestamp'])
        block.finalize()  # this is the first potential state change
        # replay transactions
        for tx_serialized, _state_root, _gas_used_encoded in transaction_list:
            tx = transactions.Transaction.deserialize(tx_serialized)
            processblock.apply_tx(block, tx)
            assert _state_root == block.state.root_hash
            assert utils.decode_int(_gas_used_encoded) == block.gas_used

        # checks
        assert block.prevhash == self.hash
        assert block.tx_list_root == kargs['tx_list_root']
        assert block.gas_used == kargs['gas_used']
        assert block.gas_limit == kargs['gas_limit']
        assert block.timestamp == kargs['timestamp']
        assert block.difficulty == kargs['difficulty']
        assert block.number == kargs['number']
        assert block.extra_data == kargs['extra_data']
        assert utils.sha3(rlp.encode(block.uncles)) == kargs['uncles_hash']
        assert block.state.root_hash == kargs['state_root']

        block.uncles_hash = kargs['uncles_hash']
        block.nonce = kargs['nonce']
        block.min_gas_price = kargs['min_gas_price']

        return block

    @classmethod
    def hex_deserialize(cls, hexrlpdata):
        return cls.deserialize(hexrlpdata.decode('hex'))

    def mk_blank_acct(self):
        if not hasattr(self, '_blank_acct'):
            codehash = utils.sha3('')
            self.state.db.put(codehash, '')
            self._blank_acct = [utils.encode_int(0),
                                utils.encode_int(0),
                                trie.BLANK_ROOT,
                                codehash]
        return self._blank_acct[:]

    def get_acct(self, address):
        if len(address) == 40:
            address = address.decode('hex')
        acct = rlp.decode(self.state.get(address)) or self.mk_blank_acct()
        return tuple(utils.decoders[t](acct[i])
                     for i, (n, t, d) in enumerate(acct_structure))

    # _get_acct_item(bin or hex, int) -> bin
    def _get_acct_item(self, address, param):
        ''' get account item
        :param address: account address, can be binary or hex string
        :param param: parameter to get
        '''
        return self.get_acct(address)[acct_structure_rev[param][0]]

    # _set_acct_item(bin or hex, int, bin)
    def _set_acct_item(self, address, param, value):
        ''' set account item
        :param address: account address, can be binary or hex string
        :param param: parameter to set
        :param value: new value
        '''
        if len(address) == 40:
            address = address.decode('hex')
        acct = rlp.decode(self.state.get(address)) or self.mk_blank_acct()
        encoder = utils.encoders[acct_structure_rev[param][1]]
        acct[acct_structure_rev[param][0]] = encoder(value)
        self.state.update(address, rlp.encode(acct))

    # _delta_item(bin or hex, int, int) -> success/fail
    def _delta_item(self, address, param, value):
        ''' add value to account item
        :param address: account address, can be binary or hex string
        :param param: parameter to increase/decrease
        :param value: can be positive or negative
        '''
        value = self._get_acct_item(address, param) + value
        if value < 0:
            return False
        self._set_acct_item(address, param, value)
        return True

    def _add_transaction_to_list(self, tx_serialized,
                                 state_root, gas_used_encoded):
        # adds encoded data # FIXME: the constructor should get objects
        data = [tx_serialized, state_root, gas_used_encoded]
        self.transactions.update(
            utils.encode_int(self.transaction_count), rlp.encode(data))
        self.transaction_count += 1

    def add_transaction_to_list(self, tx):
        # used by processblocks apply_tx only. not atomic!
        self._add_transaction_to_list(tx.serialize(),
                                      self.state_root,
                                      utils.encode_int(self.gas_used))

    def _list_transactions(self):
        # returns [[tx_serialized, state_root, gas_used_encoded],...]
        txlist = []
        for i in range(self.transaction_count):
            txlist.append(rlp.decode(
                self.transactions.get(utils.encode_int(i))))
        return txlist

    def get_transactions(self):
        return [transactions.Transaction.deserialize(tx) for
                tx, s, g in self._list_transactions()]

    def apply_transaction(self, tx):
        return processblock.apply_tx(self, tx)

    def get_nonce(self, address):
        return self._get_acct_item(address, 'nonce')

    def increment_nonce(self, address):
        return self._delta_item(address, 'nonce', 1)

    def get_balance(self, address):
        return self._get_acct_item(address, 'balance')

    def set_balance(self, address, value):
        self._set_acct_item(address, 'balance', value)

    def delta_balance(self, address, value):
        return self._delta_item(address, 'balance', value)

    def get_code(self, address):
        return self._get_acct_item(address, 'code')

    def set_code(self, address, value):
        self._set_acct_item(address, 'code', value)

    def get_storage(self, address):
        storage_root = self._get_acct_item(address, 'storage')
        return trie.Trie(utils.get_db_path(), storage_root)

    def get_storage_data(self, address, index):
        t = self.get_storage(address)
        val = t.get(utils.coerce_to_bytes(index))
        return utils.decode_int(val) if val else 0

    def set_storage_data(self, address, index, val):
        t = self.get_storage(address)
        if val:
            t.update(utils.coerce_to_bytes(index), utils.encode_int(val))
        else:
            t.delete(utils.coerce_to_bytes(index))
        self._set_acct_item(address, 'storage', t.root_hash)

    def account_to_dict(self, address):
        med_dict = {}
        for i, val in enumerate(self.get_acct(address)):
            med_dict[acct_structure[i][0]] = val
        strie = trie.Trie(utils.get_db_path(), med_dict['storage']).to_dict()
        med_dict['storage'] = {utils.decode_int(k): utils.decode_int(v)
                               for k, v in strie.iteritems()}
        return med_dict

    # Revert computation
    def snapshot(self):
        return {
            'state': self.state.root_hash,
            'gas': self.gas_used,
            'txs': self.transactions,
            'txcount': self.transaction_count,
        }

    def revert(self, mysnapshot):
        self.state.root_hash = mysnapshot['state']
        self.gas_used = mysnapshot['gas']
        self.transactions = mysnapshot['txs']
        self.transaction_count = mysnapshot['txcount']

    def finalize(self):
        """
        Apply rewards
        We raise the block's coinbase account by Rb, the block reward,
        and the coinbase of each uncle by 7 of 8 that.
        Rb = 1500 finney
        """
        self.delta_balance(self.coinbase, BLOCK_REWARD)
        for uncle_hash in self.uncles:
            uncle = get_block(uncle_hash)
            self.delta_balance(uncle.coinbase, UNCLE_REWARD)

    def serialize_header_without_nonce(self):
        return rlp.encode(self.list_header(exclude=['nonce']))

    @property
    def state_root(self):
        return self.state.root_hash

    @property
    def tx_list_root(self):
        return self.transactions.root_hash

    def list_header(self, exclude=[]):
        self.uncles_hash = utils.sha3(rlp.encode(self.uncles))
        header = []
        for name, typ, default in block_structure:
            # print name, typ, default , getattr(self, name)
            if name not in exclude:
                header.append(utils.encoders[typ](getattr(self, name)))
        return header

    def serialize(self):
        # Serialization method; should act as perfect inverse function of the
        # constructor assuming no verification failures
        return rlp.encode([self.list_header(),
                           self._list_transactions(),
                           self.uncles])

    def hex_serialize(self):
        return self.serialize().encode('hex')

    def to_dict(self):
        b = {}
        for name, typ, default in block_structure:
            b[name] = getattr(self, name)
        b["state"] = {}
        for address, v in self.state.to_dict().iteritems():
            b["state"][address.encode('hex')] = self.account_to_dict(address)
        # txlist = []
        # for i in range(self.transaction_count):
        #     txlist.append(self.transactions.get(utils.encode_int(i)))
        # b["transactions"] = txlist
        return b

    @property
    def hash(self):
        return utils.sha3(self.serialize())

    def hex_hash(self):
        return self.hash.encode('hex')

    def get_parent(self):
        if self.number == 0:
            raise UnknownParentException('Genesis block has no parent')
        try:
            parent = get_block(self.prevhash)
        except KeyError:
            raise UnknownParentException(self.prevhash.encode('hex'))
        assert parent.state.db.db == self.state.db.db
        return parent

    def has_parent(self):
        try:
            self.get_parent()
            return True
        except UnknownParentException:
            return False

    def chain_difficulty(self):
            # calculate the summarized_difficulty (on the fly for now)
        if self.is_genesis():
            return self.difficulty
        else:
            return self.difficulty + self.get_parent().chain_difficulty()

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.hash == other.hash

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        return self.number > other.number

    def __lt__(self, other):
        return self.number < other.number

    def __repr__(self):
        return '<Block(#%d %s %s)>' % (self.number,
                                       self.hex_hash()[:4],
                                       self.prevhash.encode('hex')[:4])

    @classmethod
    def init_from_parent(cls, parent, coinbase, extra_data='',
                         timestamp=int(time.time())):
        return Block(
            prevhash=parent.hash,
            uncles_hash=utils.sha3(rlp.encode([])),
            coinbase=coinbase,
            state_root=parent.state.root_hash,
            tx_list_root=trie.BLANK_ROOT,
            difficulty=calc_difficulty(parent, timestamp),
            number=parent.number + 1,
            min_gas_price=0,
            gas_limit=calc_gaslimit(parent),
            gas_used=0,
            timestamp=timestamp,
            extra_data=extra_data,
            nonce='',
            transaction_list=[],
            uncles=[])

# put the next two functions into this module to support Block.get_parent
# should be probably be in chainmanager otherwise


def get_block(blockhash):
    return Block.deserialize(db.DB(utils.get_db_path()).get(blockhash))


def has_block(blockhash):
    return blockhash in db.DB(utils.get_db_path())


def genesis(initial_alloc=GENESIS_INITIAL_ALLOC, difficulty=INITIAL_DIFFICULTY):
    # https://ethereum.etherpad.mozilla.org/11
    block = Block(prevhash=GENESIS_PREVHASH, coinbase=GENESIS_COINBASE,
                  tx_list_root=trie.BLANK_ROOT,
                  difficulty=difficulty, nonce=GENESIS_NONCE,
                  gas_limit=GENESIS_GAS_LIMIT)
    for addr, balance in initial_alloc.iteritems():
        block.set_balance(addr, balance)
    block.state.db.commit()
    return block


def dump_genesis_block_tests_data():
    import json
    g = genesis()
    data = dict(
        genesis_state_root=g.state_root.encode('hex'),
        genesis_hash=g.hex_hash(),
        genesis_rlp_hex=g.serialize().encode('hex'),
        initial_alloc=dict()
    )
    for addr, balance in GENESIS_INITIAL_ALLOC.iteritems():
        data['initial_alloc'][addr] = str(balance)

    print json.dumps(data, indent=1)

########NEW FILE########
__FILENAME__ = chainmanager
import logging
import time
import struct
from dispatch import receiver
from stoppable import StoppableLoopThread
import signals
from db import DB
import utils
import rlp
import blocks
import processblock
from transactions import Transaction
import indexdb

logger = logging.getLogger(__name__)

rlp_hash_hex = lambda data: utils.sha3(rlp.encode(data)).encode('hex')


class Miner():

    """
    Mines on the current head
    Stores received transactions
    """

    def __init__(self, parent, uncles, coinbase):
        self.nonce = 0
        block = self.block = blocks.Block.init_from_parent(parent, coinbase)
        block.uncles = [u.hash for u in uncles]
        block.finalize()  # order?
        logger.debug('Mining #%d %s', block.number, block.hex_hash())
        logger.debug('Difficulty %s', block.difficulty)

    def add_transaction(self, transaction):
        """
        (1) The transaction signature is valid;
        (2) the transaction nonce is valid (equivalent to the
            sender accounts current nonce);
        (3) the gas limit is no smaller than the intrinsic gas,
            g0 , used by the transaction;
        (4) the sender account balance contains at least the cost,
            v0, required in up-front payment.
        """
        try:
            success, res = self.block.apply_transaction(transaction)
            assert transaction in self.block.get_transactions()
        except Exception, e:
            logger.debug('rejected transaction %r: %s', transaction, e)
            return False
        if not success:
            logger.debug('transaction %r not applied', transaction)
        else:
            logger.debug(
                'transaction %r applied to %r res: %r',
                transaction, self.block, res)
        return success

    def get_transactions(self):
        return self.block.get_transactions()

    def mine(self, steps=1000):
        """
        It is formally defined as PoW: PoW(H, n) = BE(SHA3(SHA3(RLP(Hn)) o n))
        where:
        RLP(Hn) is the RLP encoding of the block header H, not including the
            final nonce component;
        SHA3 is the SHA3 hash function accepting an arbitrary length series of
            bytes and evaluating to a series of 32 bytes (i.e. 256-bit);
        n is the nonce, a series of 32 bytes;
        o is the series concatenation operator;
        BE(X) evaluates to the value equal to X when interpreted as a
            big-endian-encoded integer.
        """

        nonce_bin_prefix = '\x00' * (32 - len(struct.pack('>q', 0)))
        target = 2 ** 256 / self.block.difficulty
        rlp_Hn = self.block.serialize_header_without_nonce()

        for nonce in range(self.nonce, self.nonce + steps):
            nonce_bin = nonce_bin_prefix + struct.pack('>q', nonce)
            # BE(SHA3(SHA3(RLP(Hn)) o n))
            h = utils.sha3(utils.sha3(rlp_Hn) + nonce_bin)
            l256 = utils.big_endian_to_int(h)
            if l256 < target:
                self.block.nonce = nonce_bin
                assert self.block.check_proof_of_work(self.block.nonce) is True
                assert self.block.get_parent()
                logger.debug(
                    'Nonce found %d %r', nonce, self.block)
                return self.block

        self.nonce = nonce
        return False


class ChainManager(StoppableLoopThread):

    """
    Manages the chain and requests to it.
    """

    def __init__(self):
        super(ChainManager, self).__init__()
        # initialized after configure
        self.miner = None
        self.blockchain = None
        self._children_index = None

    def configure(self, config, genesis=None):
        self.config = config
        logger.info('Opening chain @ %s', utils.get_db_path())
        self.blockchain = DB(utils.get_db_path())
        self._children_index = indexdb.Index('ci')
        if genesis:
            self._initialize_blockchain(genesis)
        logger.debug('Chain @ #%d %s', self.head.number, self.head.hex_hash())
        self.log_chain()
        self.new_miner()

    @property
    def head(self):
        if 'HEAD' not in self.blockchain:
            self._initialize_blockchain()
        ptr = self.blockchain.get('HEAD')
        return blocks.get_block(ptr)

    def _update_head(self, block):
        bh = block.hash
        self.blockchain.put('HEAD', block.hash)
        self.blockchain.commit()
        self.new_miner()  # reset mining

    def get(self, blockhash):
        assert isinstance(blockhash, str)
        assert len(blockhash) == 32
        return blocks.get_block(blockhash)

    def has_block(self, blockhash):
        assert isinstance(blockhash, str)
        assert len(blockhash) == 32
        return blockhash in self.blockchain

    def __contains__(self, blockhash):
        return self.has_block(blockhash)

    def _store_block(self, block):
        self.blockchain.put(block.hash, block.serialize())
        self.blockchain.commit()

    def _initialize_blockchain(self, genesis=None):
        logger.info('Initializing new chain @ %s', utils.get_db_path())
        if not genesis:
            genesis = blocks.genesis()
        self._store_block(genesis)
        self._update_head(genesis)

    def synchronize_blockchain(self):
        logger.info('synchronize requested for head %r', self.head)
        signals.remote_chain_requested.send(
            sender=None, parents=[self.head.hash], count=256)

    def loop_body(self):
        ts = time.time()
        pct_cpu = self.config.getint('misc', 'mining')
        if pct_cpu > 0:
            self.mine()
            delay = (time.time() - ts) * (100. / pct_cpu - 1)
            time.sleep(min(delay, 1.))
        else:
            time.sleep(.01)

    def new_miner(self):
        "new miner is initialized if HEAD is updated"
        uncles = self.get_uncles(self.head)
        miner = Miner(self.head, uncles, self.config.get('wallet', 'coinbase'))
        if self.miner:
            for tx in self.miner.get_transactions():
                miner.add_transaction(tx)
        self.miner = miner

    def mine(self):
        with self.lock:
            block = self.miner.mine()
            if block:
                # create new block
                self.add_block(block)
                logger.debug("broadcasting new %r" % block)
                signals.send_local_blocks.send(
                    sender=None, blocks=[block])

    def receive_chain(self, transient_blocks, disconnect_cb=None):
        old_head = self.head

        # assuming to receive chain order w/ newest block first
        for t_block in reversed(transient_blocks):
            logger.debug('Trying to deserialize %r', t_block)
            try:
                block = blocks.Block.deserialize(t_block.rlpdata)
            except blocks.UnknownParentException:

                number = t_block.number
                if t_block.prevhash == blocks.GENESIS_PREVHASH:
                    logger.debug('Incompatible Genesis %r', t_block)
                    if disconnect_cb:
                        disconnect_cb(reason='Wrong genesis block')
                else:
                    logger.debug('%s with unknown parent', t_block)
                    if number > self.head.number:
                        self.synchronize_blockchain()
                    else:
                        # FIXME synchronize with side chain
                        # check for largest number
                        pass
                break
            if block.hash in self:
                logger.debug('Known %r', block)
            else:
                if block.has_parent():
                    success = self.add_block(block)
                    if success:
                        logger.debug('Added %r', block)
                else:
                    logger.debug('Orphant %r', block)
        if self.head != old_head:
            self.synchronize_blockchain()

    def add_block(self, block):
        "returns True if block was added sucessfully"
        # make sure we know the parent
        if not block.has_parent() and not block.is_genesis():
            logger.debug('Missing parent for block %r', block)
            return False

        # make sure we know the uncles
        for uncle_hash in block.uncles:
            if not uncle_hash in self:
                logger.debug('Missing uncle for block %r', block)
                return False

        # check PoW
        if not len(block.nonce) == 32:
            logger.debug('Nonce not set %r', block)
            return False
        elif not block.check_proof_of_work(block.nonce) and\
                not block.is_genesis():
            logger.debug('Invalid nonce %r', block)
            return False

        with self.lock:
            if block.has_parent():
                try:
                    processblock.verify(block, block.get_parent())
                except AssertionError, e:
                    logger.debug('verification failed: %s', str(e))
                    processblock.verify(block, block.get_parent())
                    return False

            self._children_index.append(block.prevhash, block.hash)
            self._store_block(block)
            # set to head if this makes the longest chain w/ most work
            if block.chain_difficulty() > self.head.chain_difficulty():
                logger.debug('New Head %r', block)
                self._update_head(block)
            return True

    def get_children(self, block):
        return [self.get(c) for c in self._children_index.get(block.hash)]

    def get_uncles(self, block):
        if not block.has_parent():
            return []
        parent = block.get_parent()
        if not parent.has_parent():
            return []
        return [u for u in self.get_children(parent.get_parent())
                if u != parent]

    def add_transaction(self, transaction):
        logger.debug("add transaction %r" % transaction)
        with self.lock:
            res = self.miner.add_transaction(transaction)
            if res:
                logger.debug("broadcasting valid %r" % transaction)
                signals.send_local_transactions.send(
                    sender=None, transactions=[transaction])

    def get_transactions(self):
        logger.debug("get_transactions called")
        return self.miner.get_transactions()

    def get_chain(self, start='', count=256):
        "return 'count' blocks starting from head or start"
        logger.debug("get_chain: start:%s count%d", start.encode('hex'), count)
        blocks = []
        block = self.head
        if start:
            if start not in self:
                return []
            block = self.get(start)
            if not self.in_main_branch(block):
                return []
        for i in range(count):
            blocks.append(block)
            if block.is_genesis():
                break
            block = block.get_parent()
        return blocks

    def in_main_branch(self, block):
        if block.is_genesis():
            return True
        return block == self.get_descendents(block.get_parent(), count=1)[0]

    def get_descendents(self, block, count=1):
        logger.debug("get_descendents: %r ", block)
        assert block.hash in self
        # FIXME inefficient implementation
        res = []
        cur = self.head
        while cur != block:
            res.append(cur)
            if cur.has_parent():
                cur = cur.get_parent()
            else:
                break
            if cur.number == block.number and cur != block:
                # no descendents on main branch
                logger.debug("no descendents on main branch for: %r ", block)
                return []
        res.reverse()
        return res[:count]

    def log_chain(self):
        num = self.head.number + 1
        for b in reversed(self.get_chain(count=num)):
            logger.debug(b)
            for tx in b.get_transactions():
                logger.debug('\t%r', tx)


chain_manager = ChainManager()


@receiver(signals.local_chain_requested)
def handle_local_chain_requested(sender, peer, block_hashes, count, **kwargs):
    """
    [0x14, Parent1, Parent2, ..., ParentN, Count]
    Request the peer to send Count (to be interpreted as an integer) blocks
    in the current canonical block chain that are children of Parent1
    (to be interpreted as a SHA3 block hash). If Parent1 is not present in
    the block chain, it should instead act as if the request were for Parent2
    &c.  through to ParentN.

    If none of the parents are in the current
    canonical block chain, then NotInChain should be sent along with ParentN
    (i.e. the last Parent in the parents list).

    If the designated parent is the present block chain head,
    an empty reply should be sent.

    If no parents are passed, then reply need not be made.
    """
    logger.debug(
        "local_chain_requested: %r %d",
        [b.encode('hex') for b in block_hashes], count)
    found_blocks = []
    for i, b in enumerate(block_hashes):
        if b in chain_manager:
            block = chain_manager.get(b)
            logger.debug("local_chain_requested: found: %r", block)
            found_blocks = chain_manager.get_descendents(block, count=count)
            if found_blocks:
                logger.debug("sending: found: %r ", found_blocks)
                # if b == head: no descendents == no reply
                with peer.lock:
                    peer.send_Blocks(found_blocks)
                return

    if len(block_hashes):
        #  If none of the parents are in the current
        logger.debug(
            "Sending NotInChain: %r", block_hashes[-1].encode('hex')[:4])
        peer.send_NotInChain(block_hashes[-1])
    else:
        # If no parents are passed, then reply need not be made.
        pass


@receiver(signals.config_ready)
def config_chainmanager(sender, config, **kwargs):
    chain_manager.configure(config)


@receiver(signals.peer_handshake_success)
def new_peer_connected(sender, peer, **kwargs):
    logger.debug("received new_peer_connected")
    # request transactions
    with peer.lock:
        logger.debug("send get transactions")
        peer.send_GetTransactions()
    # request chain
    blocks = [b.hash for b in chain_manager.get_chain(count=256)]
    with peer.lock:
        peer.send_GetChain(blocks, count=256)
        logger.debug("send get chain %r", [b.encode('hex') for b in blocks])


@receiver(signals.remote_transactions_received)
def remote_transactions_received_handler(sender, transactions, **kwargs):
    "receives rlp.decoded serialized"
    txl = [Transaction.deserialize(rlp.encode(tx)) for tx in transactions]
    logger.debug('remote_transactions_received: %r', txl)
    for tx in txl:
        chain_manager.add_transaction(tx)


@receiver(signals.local_transaction_received)
def local_transaction_received_handler(sender, transaction, **kwargs):
    "receives transaction object"
    logger.debug('local_transaction_received: %r', transaction)
    chain_manager.add_transaction(transaction)


@receiver(signals.gettransactions_received)
def gettransactions_received_handler(sender, peer, **kwargs):
    transactions = chain_manager.get_transactions()
    transactions = [rlp.decode(x.serialize()) for x in transactions]
    peer.send_Transactions(transactions)


@receiver(signals.remote_blocks_received)
def remote_blocks_received_handler(sender, transient_blocks, peer, **kwargs):
    logger.debug("recv %d remote blocks: %r", len(
        transient_blocks), transient_blocks)
    chain_manager.receive_chain(
        transient_blocks, disconnect_cb=peer.send_Disconnect)

########NEW FILE########
__FILENAME__ = common
import sys
import os


def enable_full_qualified_import():
    ''' so pyethreum.package.module is available'''
    where = os.path.join(__file__, os.path.pardir, os.path.pardir)
    where = os.path.abspath(where)
    for path in sys.path:
        if os.path.abspath(path) == where:
            return
    sys.path.append(where)

########NEW FILE########
__FILENAME__ = db
import leveldb

databases = {}


class DB(object):

    def __init__(self, dbfile):
        self.dbfile = dbfile
        if dbfile not in databases:
            databases[dbfile] = (leveldb.LevelDB(dbfile), dict())
        self.db, self.uncommitted = databases[dbfile]

    def get(self, key):
        if key in self.uncommitted:
            return self.uncommitted[key]
        return self.db.Get(key)

    def put(self, key, value):
        self.uncommitted[key] = value

    def commit(self):
        batch = leveldb.WriteBatch()
        for k, v in self.uncommitted.iteritems():
            batch.Put(k, v)
        self.db.Write(batch, sync=True)
        self.uncommitted.clear()

    def delete(self, key):
        if key in self.uncommitted:
            del self.uncommitted[key]
            if key not in self:
                self.db.Delete(key)
        else:
            self.db.Delete(key)

    def _has_key(self, key):
        try:
            self.get(key)
            return True
        except KeyError:
            return False

    def __contains__(self, key):
        return self._has_key(key)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.db == other.db

########NEW FILE########
__FILENAME__ = dispatcher
import sys
import threading
import weakref

# from django.utils.six.moves import xrange
from six.moves import xrange

if sys.version_info < (3, 4):
    from .weakref_backports import WeakMethod
else:
    from weakref import WeakMethod


def _make_id(target):
    if hasattr(target, '__func__'):
        return (id(target.__self__), id(target.__func__))
    return id(target)
NONE_ID = _make_id(None)

# A marker for caching
NO_RECEIVERS = object()


class Signal(object):
    """
    Base class for all signals

    Internal attributes:

        receivers
            { receiverkey (id) : weakref(receiver) }
    """
    def __init__(self, providing_args=None, use_caching=False):
        """
        Create a new signal.

        providing_args
            A list of the arguments this signal can pass along in a send() call.
        """
        self.receivers = []
        if providing_args is None:
            providing_args = []
        self.providing_args = set(providing_args)
        self.lock = threading.Lock()
        self.use_caching = use_caching
        # For convenience we create empty caches even if they are not used.
        # A note about caching: if use_caching is defined, then for each
        # distinct sender we cache the receivers that sender has in
        # 'sender_receivers_cache'. The cache is cleaned when .connect() or
        # .disconnect() is called and populated on send().
        self.sender_receivers_cache = weakref.WeakKeyDictionary() if use_caching else {}
        self._dead_receivers = False

    def connect(self, receiver, sender=None, weak=True, dispatch_uid=None):
        """
        Connect receiver to sender for signal.

        Arguments:

            receiver
                A function or an instance method which is to receive signals.
                Receivers must be hashable objects.

                If weak is True, then receiver must be weak-referencable.

                Receivers must be able to accept keyword arguments.

                If receivers have a dispatch_uid attribute, the receiver will
                not be added if another receiver already exists with that
                dispatch_uid.

            sender
                The sender to which the receiver should respond. Must either be
                of type Signal, or None to receive events from any sender.

            weak
                Whether to use weak references to the receiver. By default, the
                module will attempt to use weak references to the receiver
                objects. If this parameter is false, then strong references will
                be used.

            dispatch_uid
                An identifier used to uniquely identify a particular instance of
                a receiver. This will usually be a string, though it may be
                anything hashable.
        """
        # from django.conf import settings

        # If DEBUG is on, check that we got a good receiver
        # if settings.configured and settings.DEBUG:
        if True:
            import inspect
            assert callable(receiver), "Signal receivers must be callable."

            # Check for **kwargs
            # Not all callables are inspectable with getargspec, so we'll
            # try a couple different ways but in the end fall back on assuming
            # it is -- we don't want to prevent registration of valid but weird
            # callables.
            try:
                argspec = inspect.getargspec(receiver)
            except TypeError:
                try:
                    argspec = inspect.getargspec(receiver.__call__)
                except (TypeError, AttributeError):
                    argspec = None
            if argspec:
                assert argspec[2] is not None, \
                    "Signal receivers must accept keyword arguments (**kwargs)."

        if dispatch_uid:
            lookup_key = (dispatch_uid, _make_id(sender))
        else:
            lookup_key = (_make_id(receiver), _make_id(sender))

        if weak:
            ref = weakref.ref
            receiver_object = receiver
            # Check for bound methods
            if hasattr(receiver, '__self__') and hasattr(receiver, '__func__'):
                ref = WeakMethod
                receiver_object = receiver.__self__
            if sys.version_info >= (3, 4):
                receiver = ref(receiver)
                weakref.finalize(receiver_object, self._remove_receiver)
            else:
                receiver = ref(receiver, self._remove_receiver)

        with self.lock:
            self._clear_dead_receivers()
            for r_key, _ in self.receivers:
                if r_key == lookup_key:
                    break
            else:
                self.receivers.append((lookup_key, receiver))
            self.sender_receivers_cache.clear()

    def disconnect(self, receiver=None, sender=None, weak=True, dispatch_uid=None):
        """
        Disconnect receiver from sender for signal.

        If weak references are used, disconnect need not be called. The receiver
        will be remove from dispatch automatically.

        Arguments:

            receiver
                The registered receiver to disconnect. May be none if
                dispatch_uid is specified.

            sender
                The registered sender to disconnect

            weak
                The weakref state to disconnect

            dispatch_uid
                the unique identifier of the receiver to disconnect
        """
        if dispatch_uid:
            lookup_key = (dispatch_uid, _make_id(sender))
        else:
            lookup_key = (_make_id(receiver), _make_id(sender))

        with self.lock:
            self._clear_dead_receivers()
            for index in xrange(len(self.receivers)):
                (r_key, _) = self.receivers[index]
                if r_key == lookup_key:
                    del self.receivers[index]
                    break
            self.sender_receivers_cache.clear()

    def has_listeners(self, sender=None):
        return bool(self._live_receivers(sender))

    def send(self, sender, **named):
        """
        Send signal from sender to all connected receivers.

        If any receiver raises an error, the error propagates back through send,
        terminating the dispatch loop, so it is quite possible to not have all
        receivers called if a raises an error.

        Arguments:

            sender
                The sender of the signal Either a specific object or None.

            named
                Named arguments which will be passed to receivers.

        Returns a list of tuple pairs [(receiver, response), ... ].
        """
        responses = []
        if not self.receivers or self.sender_receivers_cache.get(sender) is NO_RECEIVERS:
            return responses

        for receiver in self._live_receivers(sender):
            response = receiver(signal=self, sender=sender, **named)
            responses.append((receiver, response))
        return responses

    def send_robust(self, sender, **named):
        """
        Send signal from sender to all connected receivers catching errors.

        Arguments:

            sender
                The sender of the signal. Can be any python object (normally one
                registered with a connect if you actually want something to
                occur).

            named
                Named arguments which will be passed to receivers. These
                arguments must be a subset of the argument names defined in
                providing_args.

        Return a list of tuple pairs [(receiver, response), ... ]. May raise
        DispatcherKeyError.

        If any receiver raises an error (specifically any subclass of
        Exception), the error instance is returned as the result for that
        receiver.
        """
        responses = []
        if not self.receivers or self.sender_receivers_cache.get(sender) is NO_RECEIVERS:
            return responses

        # Call each receiver with whatever arguments it can accept.
        # Return a list of tuple pairs [(receiver, response), ... ].
        for receiver in self._live_receivers(sender):
            try:
                response = receiver(signal=self, sender=sender, **named)
            except Exception as err:
                responses.append((receiver, err))
            else:
                responses.append((receiver, response))
        return responses

    def _clear_dead_receivers(self):
        # Note: caller is assumed to hold self.lock.
        if self._dead_receivers:
            self._dead_receivers = False
            new_receivers = []
            for r in self.receivers:
                if isinstance(r[1], weakref.ReferenceType) and r[1]() is None:
                    continue
                new_receivers.append(r)
            self.receivers = new_receivers

    def _live_receivers(self, sender):
        """
        Filter sequence of receivers to get resolved, live receivers.

        This checks for weak references and resolves them, then returning only
        live receivers.
        """
        receivers = None
        if self.use_caching and not self._dead_receivers:
            receivers = self.sender_receivers_cache.get(sender)
            # We could end up here with NO_RECEIVERS even if we do check this case in
            # .send() prior to calling _live_receivers() due to concurrent .send() call.
            if receivers is NO_RECEIVERS:
                return []
        if receivers is None:
            with self.lock:
                self._clear_dead_receivers()
                senderkey = _make_id(sender)
                receivers = []
                for (receiverkey, r_senderkey), receiver in self.receivers:
                    if r_senderkey == NONE_ID or r_senderkey == senderkey:
                        receivers.append(receiver)
                if self.use_caching:
                    if not receivers:
                        self.sender_receivers_cache[sender] = NO_RECEIVERS
                    else:
                        # Note, we must cache the weakref versions.
                        self.sender_receivers_cache[sender] = receivers
        non_weak_receivers = []
        for receiver in receivers:
            if isinstance(receiver, weakref.ReferenceType):
                # Dereference the weak reference.
                receiver = receiver()
                if receiver is not None:
                    non_weak_receivers.append(receiver)
            else:
                non_weak_receivers.append(receiver)
        return non_weak_receivers

    def _remove_receiver(self, receiver=None):
        # Mark that the self.receivers list has dead weakrefs. If so, we will
        # clean those up in connect, disconnect and _live_receivers while
        # holding self.lock. Note that doing the cleanup here isn't a good
        # idea, _remove_receiver() will be called as side effect of garbage
        # collection, and so the call can happen while we are already holding
        # self.lock.
        self._dead_receivers = True


def receiver(signal, **kwargs):
    """
    A decorator for connecting receivers to signals. Used by passing in the
    signal (or list of signals) and keyword arguments to connect::

        @receiver(post_save, sender=MyModel)
        def signal_receiver(sender, **kwargs):
            ...

        @receiver([post_save, post_delete], sender=MyModel)
        def signals_receiver(sender, **kwargs):
            ...

    """
    def _decorator(func):
        if isinstance(signal, (list, tuple)):
            for s in signal:
                s.connect(func, **kwargs)
        else:
            signal.connect(func, **kwargs)
        return func
    return _decorator

########NEW FILE########
__FILENAME__ = weakref_backports
"""
weakref_backports is a partial backport of the weakref module for python
versions below 3.4.

Copyright (C) 2013 Python Software Foundation, see license.python.txt for
details.

The following changes were made to the original sources during backporting:

 * Added `self` to `super` calls.
 * Removed `from None` when raising exceptions.

"""
from weakref import ref


class WeakMethod(ref):
    """
    A custom `weakref.ref` subclass which simulates a weak reference to
    a bound method, working around the lifetime problem of bound methods.
    """

    __slots__ = "_func_ref", "_meth_type", "_alive", "__weakref__"

    def __new__(cls, meth, callback=None):
        try:
            obj = meth.__self__
            func = meth.__func__
        except AttributeError:
            raise TypeError("argument should be a bound method, not {}"
                            .format(type(meth)))
        def _cb(arg):
            # The self-weakref trick is needed to avoid creating a reference
            # cycle.
            self = self_wr()
            if self._alive:
                self._alive = False
                if callback is not None:
                    callback(self)
        self = ref.__new__(cls, obj, _cb)
        self._func_ref = ref(func, _cb)
        self._meth_type = type(meth)
        self._alive = True
        self_wr = ref(self)
        return self

    def __call__(self):
        obj = super(WeakMethod, self).__call__()
        func = self._func_ref()
        if obj is None or func is None:
            return None
        return self._meth_type(func, obj)

    def __eq__(self, other):
        if isinstance(other, WeakMethod):
            if not self._alive or not other._alive:
                return self is other
            return ref.__eq__(self, other) and self._func_ref == other._func_ref
        return False

    def __ne__(self, other):
        if isinstance(other, WeakMethod):
            if not self._alive or not other._alive:
                return self is not other
            return ref.__ne__(self, other) or self._func_ref != other._func_ref
        return True

    __hash__ = ref.__hash__


########NEW FILE########
__FILENAME__ = eth
#!/usr/bin/env python
import sys
import time
import uuid
import signal
import ConfigParser
from argparse import ArgumentParser
import logging
import logging.config

# this must be called before all other import to enable full qualified import
from common import enable_full_qualified_import
enable_full_qualified_import()

from pyethereum.utils import configure_logging
from pyethereum.utils import data_dir
from pyethereum.utils import sha3
from pyethereum.signals import config_ready
from pyethereum.tcpserver import tcp_server
from pyethereum.peermanager import peer_manager
from pyethereum.apiserver import api_server
from pyethereum.packeter import Packeter


logger = logging.getLogger(__name__)


def create_default_config():
    config = ConfigParser.ConfigParser()
    # set some defaults, which may be overwritten
    config.add_section('network')
    config.set('network', 'listen_host', '0.0.0.0')
    config.set('network', 'listen_port', '30303')
    config.set('network', 'num_peers', '5')
    config.set('network', 'remote_port', '30303')
    config.set('network', 'remote_host', '')
    config.set('network', 'client_id', Packeter.CLIENT_ID)
    config.set('network', 'node_id', sha3(str(uuid.uuid1())).encode('hex'))

    config.add_section('api')
    config.set('api', 'listen_host', '127.0.0.1')
    config.set('api', 'listen_port', '30203')

    config.add_section('misc')
    config.set('misc', 'verbosity', '1')
    config.set('misc', 'config_file', None)
    config.set('misc', 'logging', None)
    config.set('misc', 'data_dir', data_dir.path)
    config.set('misc', 'mining', '10')

    config.add_section('wallet')
    config.set('wallet', 'coinbase', '0' * 40)

    return config


def create_config():
    config = create_default_config()
    parser = ArgumentParser(version=Packeter.CLIENT_ID)
    parser.add_argument(
        "-l", "--listen",
        dest="listen_port",
        default=config.get('network', 'listen_port'),
        help="<port>  Listen on the given port for incoming"
        " connected (default: 30303).")
    parser.add_argument(
        "-a", "--address",
        dest="coinbase",
        help="Set the coinbase (mining payout) address",
        default=config.get('wallet', 'coinbase'))
    parser.add_argument(
        "-d", "--data_dir",
        dest="data_dir",
        help="<path>  Load database from path (default: %s)" % config.get(
            'misc', 'data_dir'),
        default=config.get('misc', 'data_dir'))
    parser.add_argument(
        "-r", "--remote",
        dest="remote_host",
        help="<host> Connect to remote host"
        " (try: 54.201.28.117 or 54.204.10.41)")
    parser.add_argument(
        "-p", "--port",
        dest="remote_port",
        default=config.get('network', 'remote_port'),
        help="<port> Connect to remote port (default: 30303)"
    )
    parser.add_argument(
        "-V", "--verbose",
        dest="verbosity",
        default=config.get('misc', 'verbosity'),
        help="<0 - 3>  Set the log verbosity from 0 to 3 (default: 1)")
    parser.add_argument(
        "-m", "--mining",
        dest="mining",
        default=config.get('misc', 'mining'),
        help="<0 - 100> Percent CPU used for mining 0==off (default: 10)")
    parser.add_argument(
        "-L", "--logging",
        dest="logging",
        default=config.get('misc', 'logging'),
        help="<logger1:LEVEL,logger2:LEVEL> set the console log level for"
        " logger1, logger2, etc. Empty loggername means root-logger,"
        " e.g. 'pyethereum.wire:DEBUG,:INFO'. Overrides '-V'")
    parser.add_argument(
        "-x", "--peers",
        dest="num_peers",
        default=config.get('network', 'num_peers'),
        help="<number> Attempt to connect to given number of peers"
        "(default: 5)")
    parser.add_argument("-C", "--config",
                        dest="config_file",
                        help="read coniguration")

    options = parser.parse_args()

    # set network options
    for attr in ('listen_port', 'remote_host', 'remote_port', 'num_peers'):
        config.set('network', attr, getattr(
            options, attr) or config.get('network', attr))
    # set misc options
    for attr in ('verbosity', 'config_file', 'logging', 'data_dir', 'mining'):
        config.set(
            'misc', attr, getattr(options, attr) or config.get('misc', attr))

    # set wallet options
    for attr in ('coinbase',):
        config.set(
            'wallet', attr, getattr(options, attr) or config.get('wallet', attr))

    if config.get('misc', 'config_file'):
        config.read(config.get('misc', 'config_file'))

    # set datadir
    if config.get('misc', 'data_dir'):
        data_dir.set(config.get('misc', 'data_dir'))

    # configure logging
    configure_logging(
        config.get('misc', 'logging') or '',
        verbosity=config.getint('misc', 'verbosity'))

    return config


def main():
    config = create_config()

    try:
        import pyethereum.monkeypatch
        logger.info("Loaded your customizations from monkeypatch.py")
    except ImportError, e:
        pass

    config_ready.send(sender=None, config=config)
    # import after logger config is ready
    from pyethereum.chainmanager import chain_manager

    try:
        tcp_server.start()
    except IOError as e:
        logger.error("Could not start TCP server: \"{0}\"".format(str(e)))
        sys.exit(1)

    peer_manager.start()
    chain_manager.start()
    api_server.start()

    # handle termination signals
    def signal_handler(signum=None, frame=None):
        logger.info('Signal handler called with signal {0}'.format(signum))
        peer_manager.stop()
        chain_manager.stop()
        tcp_server.stop()

    for sig in [signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT, signal.SIGINT]:
        signal.signal(sig, signal_handler)

    # connect peer
    if config.get('network', 'remote_host'):
        peer_manager.connect_peer(
            config.get('network', 'remote_host'),
            config.getint('network', 'remote_port'))

    # loop
    while not peer_manager.stopped():
        time.sleep(0.01)

    logger.info('exiting')

    peer_manager.join()

    logger.debug('main thread finished')

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = indexdb
import struct
import db
from utils import get_index_path


class Index(object):

    """
    stores a list of values for a key
    datastructure: namespace|key|valnum > val
    """

    def __init__(self, namespace):
        self.namespace = namespace
        self.db = db.DB(get_index_path())

    def _key(self, key, valnum=None):
        return self.namespace + key + struct.pack('>I', valnum)

    def add(self, key, valnum, value):
        assert isinstance(value, str)
        self.db.put(self._key(key, valnum), value)
        self.db.commit()

    def append(self, key, value):
        self.add(key, self.num_values(key), value)

    def get(self, key, offset=0):
        assert not self.db.uncommitted
        key_from = self._key(key, offset)
        for k, v in self.db.db.RangeIter(include_value=True,
                                         key_from=key_from):
            if k.startswith(self.namespace + key) and struct.unpack('>I', k[-4:]) >= offset:
                yield v

    def delete(self, key, offset=0):
        while self._key(key, offset) in self.db:
            self.db.delete(self._key(key, offset))
            offset += 1

    def keys(self, key_from=''):
        assert not self.db.uncommitted
        zero = struct.pack('>I', 0)
        for key in self.db.db.RangeIter(include_value=False,
                                        key_from=self.namespace + key_from):
            if key.endswith(zero):
                yield key[len(self.namespace):-4]

    def num_values(self, key, start=0):
        if self._key(key, start) not in self.db:
            return start
        test = start + 1
        while self._key(key, test * 2) in self.db:
            test *= 2
        return self.num_values(key, test)


class AccountTxIndex(Index):

    "acct|txnonce > tx"

    def __init__(self):
        super(AccountTxIndex, self).__init__('tx')

    def add_transaction(self, account, nonce, transaction_hash):
        self.add(account, nonce, transaction_hash)

    def get_transactions(self, account, offset=0):
        return self.get(account, offset)

    def delete_transactions(self, account, offset=0):
        self.delete(account, offset)

    def get_accounts(self, account_from=None):
        return self.keys(key_from=account_from)

    def num_transactions(self, account, start=0):
        return self.num_values(account)

########NEW FILE########
__FILENAME__ = opcodes
opcodes = {
    0x00: ['STOP', 0, 0],
    0x01: ['ADD', 2, 1],
    0x02: ['MUL', 2, 1],
    0x03: ['SUB', 2, 1],
    0x04: ['DIV', 2, 1],
    0x05: ['SDIV', 2, 1],
    0x06: ['MOD', 2, 1],
    0x07: ['SMOD', 2, 1],
    0x08: ['EXP', 2, 1],
    0x09: ['NEG', 2, 1],
    0x0a: ['LT', 2, 1],
    0x0b: ['GT', 2, 1],
    0x0c: ['SLT', 2, 1],
    0x0d: ['SGT', 2, 1],
    0x0e: ['EQ', 2, 1],
    0x0f: ['NOT', 1, 1],
    0x10: ['AND', 2, 1],
    0x11: ['OR', 2, 1],
    0x12: ['XOR', 2, 1],
    0x13: ['BYTE', 2, 1],
    0x20: ['SHA3', 2, 1],
    0x30: ['ADDRESS', 0, 1],
    0x31: ['BALANCE', 0, 1],
    0x32: ['ORIGIN', 0, 1],
    0x33: ['CALLER', 0, 1],
    0x34: ['CALLVALUE', 0, 1],
    0x35: ['CALLDATALOAD', 1, 1],
    0x36: ['CALLDATASIZE', 0, 1],
    0x37: ['CALLDATACOPY', 3, 0],
    0x38: ['CODESIZE', 0, 1],
    0x39: ['CODECOPY', 3, 0],
    0x3a: ['GASPRICE', 0, 1],
    0x40: ['PREVHASH', 0, 1],
    0x41: ['COINBASE', 0, 1],
    0x42: ['TIMESTAMP', 0, 1],
    0x43: ['NUMBER', 0, 1],
    0x44: ['DIFFICULTY', 0, 1],
    0x45: ['GASLIMIT', 0, 1],
    0x50: ['POP', 1, 0],
    0x51: ['DUP', 1, 2],
    0x52: ['SWAP', 2, 2],
    0x53: ['MLOAD', 1, 1],
    0x54: ['MSTORE', 2, 0],
    0x55: ['MSTORE8', 2, 0],
    0x56: ['SLOAD', 1, 1],
    0x57: ['SSTORE', 2, 0],
    0x58: ['JUMP', 1, 0],
    0x59: ['JUMPI', 2, 0],
    0x5a: ['PC', 0, 1],
    0x5b: ['MSIZE', 0, 1],
    0x5c: ['GAS', 0, 1],
    0x60: ['PUSH', 0, 1],  # encompasses 96...127
    0xf0: ['CREATE', 4, 1],
    0xf1: ['CALL', 7, 1],
    0xf2: ['RETURN', 2, 1],
    0xff: ['SUICIDE', 1, 1],
}
reverse_opcodes = {}
for o in opcodes:
    reverse_opcodes[opcodes[o][0]] = o

########NEW FILE########
__FILENAME__ = packeter
import logging
import rlp
from utils import big_endian_to_int as idec
from utils import int_to_big_endian4 as ienc4
from utils import int_to_big_endian as ienc
from utils import recursive_int_to_big_endian
import dispatch
import sys
import signals

logger = logging.getLogger(__name__)


def lrlp_decode(data):
    "always return a list"
    d = rlp.decode(data)
    if isinstance(d, str):
        d = [d]
    return d


def load_packet(packet):
    return Packeter.load_packet(packet)


class Packeter(object):

    """
    Translates between the network and the local data
    https://github.com/ethereum/wiki/wiki/%5BEnglish%5D-Wire-Protocol

    stateless!

    .. note::

        #.  Can only be used after the `config` method is called
    '''
    """

    cmd_map = dict(((0x00, 'Hello'),
                   (0x01, 'Disconnect'),
                   (0x02, 'Ping'),
                   (0x03, 'Pong'),
                   (0x10, 'GetPeers'),
                   (0x11, 'Peers'),
                   (0x12, 'Transactions'),
                   (0x13, 'Blocks'),
                   (0x14, 'GetChain'),
                   (0x15, 'NotInChain'),
                   (0x16, 'GetTransactions')))
    cmd_map_by_name = dict((v, k) for k, v in cmd_map.items())

    disconnect_reasons_map = dict((
        ('Disconnect requested', 0x00),
        ('TCP sub-system error', 0x01),
        ('Bad protocol', 0x02),
        ('Useless peer', 0x03),
        ('Too many peers', 0x04),
        ('Already connected', 0x05),
        ('Wrong genesis block', 0x06),
        ('Incompatible network protocols', 0x07),
        ('Client quitting', 0x08)))
    disconnect_reasons_map_by_id = \
        dict((v, k) for k, v in disconnect_reasons_map.items())

    SYNCHRONIZATION_TOKEN = 0x22400891
    PROTOCOL_VERSION = 17

    # is the node s Unique Identifier and is the 512-bit hash that serves to
    # identify the node.
    NETWORK_ID = 0
    CLIENT_ID = 'Ethereum(py)/0.5.2/%s/Protocol:%d' % (sys.platform,
                                                       PROTOCOL_VERSION)
    CAPABILITIES = 0x01 + 0x02 + 0x04  # node discovery + transaction relaying

    def __init__(self):
        pass

    def configure(self, config):
        self.config = config
        self.CLIENT_ID = self.config.get('network', 'client_id') \
            or self.CLIENT_ID
        self.NODE_ID = self.config.get('network', 'node_id')

    @classmethod
    def load_packet(cls, packet):
        '''
        Though TCP provides a connection-oriented medium, Ethereum nodes
        communicate in terms of packets. These packets are formed as a 4-byte
        synchronisation token (0x22400891), a 4-byte "payload size", to be
        interpreted as a big-endian integer and finally an N-byte
        RLP-serialised data structure, where N is the aforementioned
        "payload size". To be clear, the payload size specifies the number of
        bytes in the packet ''following'' the first 8.

        :return: (success, result), where result should be None when fail,
        and (header, payload_len, cmd, data) when success
        '''
        header = idec(packet[:4])
        if header != cls.SYNCHRONIZATION_TOKEN:
            return False, 'check header failed, skipping message,'\
                'sync token was hex: {0:x}'.format(header)

        try:
            payload_len = idec(packet[4:8])
        except Exception as e:
            return False, str(e)

        if len(packet) < payload_len + 8:
            return False, 'Packet is broken'

        try:
            payload = lrlp_decode(packet[8:8 + payload_len])
        except Exception as e:
            return False, str(e)

        if (not len(payload)) or (idec(payload[0]) not in cls.cmd_map):
            return False, 'check cmd failed'

        cmd = Packeter.cmd_map.get(idec(payload[0]))
        remain = packet[8 + payload_len:]
        return True, (header, payload_len, cmd, payload[1:], remain)

    def load_cmd(self, packet):
        success, res = self.load_packet(packet)
        if not success:
            raise Exception(res)
        _, _, cmd, data, remain = res
        return cmd, data, remain

    @classmethod
    def dump_packet(cls, data):
        """
        4-byte synchronisation token, (0x22400891),
        a 4-byte "payload size", to be interpreted as a big-endian integer
        an N-byte RLP-serialised data structure
        """
        payload = rlp.encode(recursive_int_to_big_endian(data))

        packet = ienc4(cls.SYNCHRONIZATION_TOKEN)
        packet += ienc4(len(payload))
        packet += payload
        return packet

    def dump_Hello(self):
        # inconsistency here!
        # spec says CAPABILITIES, LISTEN_PORT but code reverses
        """
        [0x00, PROTOCOL_VERSION, NETWORK_ID, CLIENT_ID, CAPABILITIES,
        LISTEN_PORT, NODE_ID]
        First packet sent over the connection, and sent once by both sides.
        No other messages may be sent until a Hello is received.
        PROTOCOL_VERSION is one of:
            0x00 for PoC-1;
            0x01 for PoC-2;
            0x07 for PoC-3.
            0x08 sent by Ethereum(++)/v0.3.11/brew/Darwin/unknown
        NETWORK_ID should be 0.
        CLIENT_ID Specifies the client software identity, as a human-readable
            string (e.g. "Ethereum(++)/1.0.0").
        LISTEN_PORT specifies the port that the client is listening on
            (on the interface that the present connection traverses).
            If 0 it indicates the client is not listening.
        CAPABILITIES specifies the capabilities of the client as a set of
            flags; presently three bits are used:
            0x01 for peers discovery,
            0x02 for transaction relaying,
            0x04 for block-chain querying.
        NODE_ID is optional and specifies a 512-bit hash, (potentially to be
            used as public key) that identifies this node.
        """
        data = [self.cmd_map_by_name['Hello'],
                self.PROTOCOL_VERSION,
                self.NETWORK_ID,
                self.CLIENT_ID,
                self.config.getint('network', 'listen_port'),
                self.CAPABILITIES,
                self.NODE_ID
                ]
        return self.dump_packet(data)

    def dump_Ping(self):
        data = [self.cmd_map_by_name['Ping']]
        return self.dump_packet(data)

    def dump_Pong(self):
        data = [self.cmd_map_by_name['Pong']]
        return self.dump_packet(data)

    def dump_Disconnect(self, reason=None):
        data = [self.cmd_map_by_name['Disconnect']]
        if reason:
            data.append(self.disconnect_reasons_map[reason])
        return self.dump_packet(data)

    def dump_GetPeers(self):
        data = [self.cmd_map_by_name['GetPeers']]
        return self.dump_packet(data)

    def dump_Peers(self, peers):
        '''
        :param peers: a sequence of (ip, port, pid)
        :return: None if no peers
        '''
        data = [self.cmd_map_by_name['Peers']]
        for ip, port, pid in peers:
            assert ip.count('.') == 3
            ip = ''.join(chr(int(x)) for x in ip.split('.'))
            data.append([ip, port, pid])
        return self.dump_packet(data)

    def dump_Transactions(self, transactions):
        data = [self.cmd_map_by_name['Transactions']] + transactions
        return self.dump_packet(data)

    def dump_GetTransactions(self):
        """
        [0x12, [nonce, receiving_address, value, ... ], ... ]
        Specify (a) transaction(s) that the peer should make sure is included
        on its transaction queue. The items in the list (following the first
        item 0x12) are transactions in the format described in the main
        Ethereum specification.
        """
        data = [self.cmd_map_by_name['GetTransactions']]
        return self.dump_packet(data)

    def dump_Blocks(self, blocks):
        blocks_as_lists = [rlp.decode(b.serialize()) for b in blocks]
        # FIXME, can we have a method to append rlp encoded data
        data = [self.cmd_map_by_name['Blocks']] + blocks_as_lists
        return self.dump_packet(data)

    def dump_GetChain(self, parent_hashes=[], count=1):
        """
        [0x14, Parent1, Parent2, ..., ParentN, Count]
        Request the peer to send Count (to be interpreted as an integer) blocks
        in the current canonical block chain that are children of Parent1
        (to be interpreted as a SHA3 block hash). If Parent1 is not present in
        the block chain, it should instead act as if the request were for
        Parent2 &c. through to ParentN. If the designated parent is the present
        block chain head, an empty reply should be sent. If none of the parents
        are in the current canonical block chain, then NotInChain should be
        sent along with ParentN (i.e. the last Parent in the parents list).
        If no parents are passed, then a reply need not be made.
        """
        data = [self.cmd_map_by_name['GetChain']] + parent_hashes + [count]
        return self.dump_packet(data)

    def dump_NotInChain(self, block_hash):
        data = [self.cmd_map_by_name['NotInChain'], block_hash]
        return self.dump_packet(data)


packeter = Packeter()


@dispatch.receiver(signals.config_ready)
def config_packeter(sender, config, **kwargs):
    packeter.configure(config)

########NEW FILE########
__FILENAME__ = peer
import time
import Queue
import socket
import logging

import signals
from stoppable import StoppableLoopThread
from packeter import packeter
from utils import big_endian_to_int as idec
from utils import recursive_int_to_big_endian
import rlp
import blocks


logger = logging.getLogger(__name__)


class Peer(StoppableLoopThread):

    def __init__(self, connection, ip, port):
        super(Peer, self).__init__()
        self._connection = connection

        assert ip.count('.') == 3
        self.ip = ip
        # None if peer was created in response to external connect
        self.port = port
        self.node_id = ''
        self.response_queue = Queue.Queue()
        self.hello_received = False
        self.hello_sent = False
        self.last_valid_packet_received = time.time()
        self.last_asked_for_peers = 0
        self.last_pinged = 0

        self.recv_buffer = ''

        # connect signals

    def __repr__(self):
        return "<Peer(%s:%r)>" % (self.ip, self.port)

    def __str__(self):
        return "[{0}: {1}]".format(self.ip, self.port)

    def connection(self):
        if self.stopped():
            raise IOError("Connection was stopped")
        else:
            return self._connection

    def stop(self):
        super(Peer, self).stop()

        # shut down
        try:
            self._connection.shutdown(socket.SHUT_RDWR)
        except socket.error as e:
            logger.debug(
                "shutting down failed {0} \"{1}\"".format(repr(self), str(e)))
        self._connection.close()

    def send_packet(self, response):
        logger.debug('sending packet to {0} >>> {1}'.format(
            self, response.encode('hex')))
        self.response_queue.put(response)

    def _process_send(self):
        '''
        :return: size of processed data
        '''
        # send packet
        try:
            packet = self.response_queue.get(block=False)
        except Queue.Empty:
            packet = ''

        while packet:
            try:
                n = self.connection().send(packet)
                packet = packet[n:]
            except socket.error as e:
                logger.debug(
                    '{0}: send packet failed, {1}'
                    .format(self, str(e)))
                self.stop()
                break

        if packet:
            return len(packet)
        else:
            return 0

    def _process_recv(self):
        '''
        :return: size of processed data
        '''
        while True:
            try:
                self.recv_buffer += self.connection().recv(2048)
            except socket.error:
                break
        length = len(self.recv_buffer)
        while self.recv_buffer:
            self._process_recv_buffer()
        return length

    def _process_recv_buffer(self):
        try:
            cmd, data, self.recv_buffer = packeter.load_cmd(self.recv_buffer)
        except Exception as e:
            self.recv_buffer = ''
            logger.warn(e)
            return self.send_Disconnect(reason='Bad protocol')

        # good peer
        self.last_valid_packet_received = time.time()

        logger.debug('receive from {0} <<< cmd: {1}: data: {2}'.format(
            self, cmd,
            rlp.encode(recursive_int_to_big_endian(data)).encode('hex')
        ))

        func_name = "_recv_{0}".format(cmd)
        if not hasattr(self, func_name):
            logger.warn('unknown cmd \'{0}\''.format(func_name))
            return

        getattr(self, func_name)(data)

    def send_Hello(self):
        self.send_packet(packeter.dump_Hello())
        self.hello_sent = True

    def _recv_Hello(self, data):
        # check compatibility
        client_id, peer_protocol_version = data[2], idec(data[0])
        logger.debug('received Hello %s V:%r',client_id, peer_protocol_version)

        if peer_protocol_version != packeter.PROTOCOL_VERSION:
            return self.send_Disconnect(
                reason='Incompatible network protocols')

        if idec(data[1]) != packeter.NETWORK_ID:
            return self.send_Disconnect(reason='Wrong genesis block')

        # add to known peers list in handshake signal
        self.hello_received = True
        if len(data) == 6:
            self.node_id = data[5]
            self.port = idec(data[3]) # replace connection port with listen port

        # reply with hello if not send
        if not self.hello_sent:
            self.send_Hello()

        signals.peer_handshake_success.send(sender=Peer, peer=self)

    def send_Ping(self):
        self.send_packet(packeter.dump_Ping())
        self.last_pinged = time.time()

    def _recv_Ping(self, data):
        self.send_Pong()

    def send_Pong(self):
        self.send_packet(packeter.dump_Pong())

    def _recv_Pong(self, data):
        pass

    reasons_to_forget = ('Bad protocol',
                        'Incompatible network protocols', 
                        'Wrong genesis block')
    
    def send_Disconnect(self, reason=None):
        logger.info('disconnecting {0}, reason: {1}'.format(
            str(self), reason or ''))
        self.send_packet(packeter.dump_Disconnect(reason=reason))
        # end connection
        time.sleep(2)
        forget = reason in self.reasons_to_forget
        signals.peer_disconnect_requested.send(Peer, peer=self, forget=forget)

    def _recv_Disconnect(self, data):
        if len(data):
            reason = packeter.disconnect_reasons_map_by_id[idec(data[0])]
            logger.info('{0} sent disconnect, {1} '.format(repr(self), reason))
            forget = reason in self.reasons_to_forget
        else:
            forget = None
        signals.peer_disconnect_requested.send(
                sender=Peer, peer=self, forget=forget)

    def send_GetPeers(self):
        self.send_packet(packeter.dump_GetPeers())

    def _recv_GetPeers(self, data):
        signals.getpeers_received.send(sender=Peer, peer=self)

    def send_Peers(self, peers):
        if peers:
            packet = packeter.dump_Peers(peers)
            self.send_packet(packet)

    def _recv_Peers(self, data):
        addresses = []
        for ip, port, pid in data:
            assert len(ip) == 4
            ip = '.'.join(str(ord(b)) for b in ip)
            port = idec(port)
            logger.debug('received peer address: {0}:{1}'.format(ip, port))
            addresses.append([ip, port, pid])
        signals.peer_addresses_received.send(sender=Peer, addresses=addresses)

    def send_GetTransactions(self):
        logger.info('asking for transactions')
        self.send_packet(packeter.dump_GetTransactions())

    def _recv_GetTransactions(self, data):
        logger.info('asking for transactions')
        signals.gettransactions_received.send(sender=Peer, peer=self)

    def send_Transactions(self, transactions):
        self.send_packet(packeter.dump_Transactions(transactions))

    def _recv_Transactions(self, data):
        logger.info('received transactions #%d', len(data))
        signals.remote_transactions_received.send(
            sender=Peer, transactions=data)

    def send_Blocks(self, blocks):
        self.send_packet(packeter.dump_Blocks(blocks))

    def _recv_Blocks(self, data):
        transient_blocks = [blocks.TransientBlock(rlp.encode(b)) \
                            for b in data] # FIXME
        signals.remote_blocks_received.send(
            sender=Peer, peer=self, transient_blocks=transient_blocks)

    def send_GetChain(self, parents=[], count=1):
        self.send_packet(packeter.dump_GetChain(parents, count))

    def _recv_GetChain(self, data):
        """
        [0x14, Parent1, Parent2, ..., ParentN, Count]
        Request the peer to send Count (to be interpreted as an integer) blocks
        in the current canonical block chain that are children of Parent1
        (to be interpreted as a SHA3 block hash). If Parent1 is not present in
        the block chain, it should instead act as if the request were for
        Parent2 &c. through to ParentN. If the designated parent is the present
        block chain head, an empty reply should be sent. If none of the parents
        are in the current canonical block chain, then NotInChain should be
        sent along with ParentN (i.e. the last Parent in the parents list).
        If no parents are passed, then reply need not be made.
        """
        signals.local_chain_requested.send(
            sender=Peer, peer=self, block_hashes=data[:-1], count=idec(data[-1]))

    def send_NotInChain(self, block_hash):
        self.send_packet(packeter.dump_NotInChain(block_hash))

    def _recv_NotInChain(self, data):
        pass

    def loop_body(self):
        try:
            send_size = self._process_send()
            recv_size = self._process_recv()
        except IOError:
            self.stop()
            return
        # pause
        if not (send_size or recv_size):
            time.sleep(0.01)

########NEW FILE########
__FILENAME__ = peermanager
import time
import socket
import logging
import json
import os

from dispatch import receiver

from stoppable import StoppableLoopThread
import rlp
import signals
from peer import Peer

logger = logging.getLogger(__name__)

def is_valid_ip(ip): # FIXME, IPV6
    return ip.count('.') == 3


class PeerManager(StoppableLoopThread):

    max_silence = 10  # how long before pinging a peer
    max_ping_wait = 5  # how long to wait before disconenctiong after ping
    max_ask_for_peers_elapsed = 30  # how long before asking for peers

    def __init__(self):
        super(PeerManager, self).__init__()
        self.connected_peers = set()
        self._known_peers = set()  # (ip, port, node_id)
        self.local_ip = '0.0.0.0'
        self.local_port = 0
        self.local_node_id = ''

    def configure(self, config):
        self.config = config
        self.local_node_id = config.get('network', 'node_id')
        self.local_ip = config.get('network', 'listen_host')
        assert is_valid_ip(self.local_ip)
        self.local_port = config.getint('network', 'listen_port')

    def stop(self):
        with self.lock:
            if not self._stopped:
                for peer in self.connected_peers:
                    peer.stop()
        super(PeerManager, self).stop()

    def load_saved_peers(self):
        path = os.path.join(self.config.get('misc', 'data_dir'), 'peers.json')
        if os.path.exists(path):
            peers = set((ip, port, "") for ip, port in json.load(open(path)))
            self._known_peers.update(peers)

    def save_peers(self):
        path = os.path.join(self.config.get('misc', 'data_dir'), 'peers.json')
        json.dump([[i, p] for i, p, n in self._known_peers], open(path, 'w'))

    def add_known_peer_address(self, ip, port, node_id):
        assert is_valid_ip(ip)
        if not ip or not port or not node_id:
            return
        ipn = (ip, port, node_id)
        if node_id not in (self.local_node_id, ""):
            with self.lock:
                if ipn not in self._known_peers:
                    # remove and readd if peer was loaded (without node id)
                    if (ip, port, "") in self._known_peers:
                        self._known_peers.remove((ip, port, ""))
                    self._known_peers.add(ipn)

    def remove_known_peer_address(self, ip, port, node_id):
        self._known_peers.remove((ip, port, node_id))

    def get_known_peer_addresses(self):
        return set(self._known_peers).union(
            self.get_connected_peer_addresses())

    def get_connected_peer_addresses(self):
        "get peers, we connected and have a port"
        return set((p.ip, p.port, p.node_id) for p in self.connected_peers
                   if p.hello_received)

    def remove_peer(self, peer):
        if not peer.stopped():
            peer.stop()
        with self.lock:
            self.connected_peers.remove(peer)
        # connect new peers if there are no candidates

    def _create_peer_sock(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(1)
        return sock

    def connect_peer(self, host, port):
        '''
        :param host:  domain notation or IP
        '''
        sock = self._create_peer_sock()
        logger.debug('connecting {0}:{1}'.format(host, port))
        try:
            sock.connect((host, port))
        except Exception as e:
            logger.debug('Connecting %s:%d failed, %s', host, port, e)
            return None
        ip, port = sock.getpeername()
        logger.debug('connected {0}:{1}'.format(ip, port))
        peer = self.add_peer(sock, ip, port)

        # Send Hello
        peer.send_Hello()
        return peer

    def get_peer_candidates(self):
        candidates = self.get_known_peer_addresses().difference(
            self.get_connected_peer_addresses())
        candidates = [
            ipn for ipn in candidates if ipn[2] != self.local_node_id]
        return candidates

    def _check_alive(self, peer):
        if peer.stopped():
            self.remove_peer(peer)
            return

        now = time.time()
        dt_ping = now - peer.last_pinged
        dt_seen = now - peer.last_valid_packet_received

        # if ping was sent and not returned within last second
        if dt_ping < dt_seen and dt_ping > self.max_ping_wait:
            logger.debug(
                '{0} last ping: {1} last seen: {2}'
                .format(peer, dt_ping, dt_seen))
            logger.debug(
                '{0} did not respond to ping, disconnecting {1}:{2}'
                .format(peer, peer.ip, peer.port))
            self.remove_peer(peer)
        elif min(dt_seen, dt_ping) > self.max_silence:
            # ping silent peer
            logger.debug('pinging silent peer {0}'.format(peer))

            with peer.lock:
                peer.send_Ping()

    def _connect_peers(self):
        num_peers = self.config.getint('network', 'num_peers')
        candidates = self.get_peer_candidates()
        if len(self.connected_peers) < num_peers:
            logger.debug('not enough peers: {0}'.format(
                len(self.connected_peers)))
            logger.debug('num candidates: {0}'.format(len(candidates)))
            if len(candidates):
                ip, port, node_id = candidates.pop()
                self.connect_peer(ip, port)
                # don't use this node again in case of connect error > remove
                self.remove_known_peer_address(ip, port, node_id)
            else:
                for peer in list(self.connected_peers):
                    with peer.lock:
                        peer.send_GetPeers()

    def loop_body(self):
        "check peer health every 10 seconds"
        for peer in list(self.connected_peers):
            self._check_alive(peer)
        self._connect_peers()

        if len(self._known_peers) == 0:
            self.load_saved_peers()

        for i in range(100):
            if not self.stopped():
                time.sleep(.1)

    def _start_peer(self, connection, ip, port):
        peer = Peer(connection, ip, port)
        peer.start()
        return peer

    def add_peer(self, connection, ip, port):
        # check existance first
        for peer in self.connected_peers:
            if (ip, port) == (peer.ip, peer.port):
                return peer
        connection.settimeout(1)
        peer = self._start_peer(connection, ip, port)
        with self.lock:
            self.connected_peers.add(peer)
        return peer

peer_manager = PeerManager()


@receiver(signals.config_ready)
def config_peermanager(sender, config, **kwargs):
    peer_manager.configure(config)


@receiver(signals.peer_connection_accepted)
def connection_accepted_handler(sender, connection, ip, port, **kwargs):
    peer_manager.add_peer(connection, ip, port)


@receiver(signals.send_local_blocks)
def send_blocks_handler(sender, blocks=[], **kwargs):
    for peer in peer_manager.connected_peers:
        peer.send_Blocks(blocks)


@receiver(signals.getpeers_received)
def getaddress_received_handler(sender, peer, **kwargs):
    with peer_manager.lock:
        peers = peer_manager.get_known_peer_addresses()
        assert is_valid_ip(peer_manager.local_ip)
        peers.add((peer_manager.local_ip,
                  peer_manager.local_port,
                  peer_manager.local_node_id))
    peer.send_Peers(peers)


@receiver(signals.peer_disconnect_requested)
def disconnect_requested_handler(sender, peer, forget=False, **kwargs):
    peer_manager.remove_peer(peer)
    if forget:
        ipn = (peer.ip, peer.port, peer.node_id)
        if ipn in peer_manager._known_peers:
            peer_manager.remove_known_peer_address(*ipn)
            peer_manager.save_peers()


@receiver(signals.peer_addresses_received)
def peer_addresses_received_handler(sender, addresses, **kwargs):
    ''' addresses should be (ip, port, node_id)
    '''
    for ip, port, node_id in addresses:
        peer_manager.add_known_peer_address(ip, port, node_id)
    peer_manager.save_peers()


@receiver(signals.send_local_transactions)
def send_transactions(sender, transactions=[], **kwargs):
    transactions = [rlp.decode(t.serialize()) for t in transactions]
    for peer in peer_manager.connected_peers:
        peer.send_Transactions(transactions)


@receiver(signals.remote_chain_requested)
def request_remote_chain(sender, parents=[], count=1, **kwargs):
    for peer in peer_manager.connected_peers:
        peer.send_GetChain(parents, count)


@receiver(signals.peer_handshake_success)
def new_peer_connected(sender, peer, **kwargs):
    logger.debug("received new_peer_connected")
    peer_manager.add_known_peer_address(peer.ip, peer.port, peer.node_id)

########NEW FILE########
__FILENAME__ = processblock
import rlp
from opcodes import opcodes

import utils
import time
import blocks
import transactions
import trie


debug = 0

# params

GSTEP = 1
GSTOP = 0
GSHA3 = 20
GSLOAD = 20
GSSTORE = 100
GBALANCE = 20
GCREATE = 100
GCALL = 20
GMEMORY = 1
GTXDATA = 5
GTXCOST = 500

OUT_OF_GAS = -1


def verify(block, parent):
    if block.timestamp < parent.timestamp:
        print block.timestamp, parent.timestamp
    assert block.timestamp >= parent.timestamp
    assert block.timestamp <= time.time() + 900
    block2 = blocks.Block.init_from_parent(parent,
                                           block.coinbase,
                                           block.extra_data,
                                           block.timestamp)
    assert block2.difficulty == block.difficulty
    assert block2.gas_limit == block.gas_limit
    block2.finalize()  # this is the first potential state change
    for i in range(block.transaction_count):
        tx, s, g = rlp.decode(block.transactions.get(utils.encode_int(i)))
        tx = transactions.Transaction.deserialize(tx)
        assert tx.startgas + block2.gas_used <= block.gas_limit
        apply_tx(block2, tx)
        assert s == block2.state.root_hash
        assert g == utils.encode_int(block2.gas_used)
    assert block2.state.root_hash == block.state.root_hash
    assert block2.gas_used == block.gas_used
    return True


class Message(object):

    def __init__(self, sender, to, value, gas, data):
        assert gas >= 0
        self.sender = sender
        self.to = to
        self.value = value
        self.gas = gas
        self.data = data


def apply_tx(block, tx):
    if not tx.sender:
        raise Exception("Trying to apply unsigned transaction!")
    acctnonce = block.get_nonce(tx.sender)
    if acctnonce != tx.nonce:
        raise Exception("Invalid nonce! sender_acct:%s tx:%s" %
                        (acctnonce, tx.nonce))
    o = block.delta_balance(tx.sender, -tx.gasprice * tx.startgas)
    if not o:
        raise Exception("Insufficient balance to pay fee!")
    if tx.to:
        block.increment_nonce(tx.sender)
    snapshot = block.snapshot()
    message_gas = tx.startgas - GTXDATA * len(tx.serialize()) - GTXCOST
    message = Message(tx.sender, tx.to, tx.value, message_gas, tx.data)
    if tx.to:
        result, gas, data = apply_msg(block, tx, message)
    else:
        result, gas, data = create_contract(block, tx, message)
    if debug:
        print('applied tx, result', result, 'gas', gas, 'data/code',
              ''.join(map(chr, data)).encode('hex'))
    if not result:  # 0 = OOG failure in both cases
        block.revert(snapshot)
        block.gas_used += tx.startgas
        block.delta_balance(block.coinbase, tx.gasprice * tx.startgas)
        output = OUT_OF_GAS
    else:
        block.delta_balance(tx.sender, tx.gasprice * gas)
        block.delta_balance(block.coinbase, tx.gasprice * (tx.startgas - gas))
        block.gas_used += tx.startgas - gas
        output = ''.join(map(chr, data)) if tx.to else result.encode('hex')
    block.add_transaction_to_list(tx)
    success = output is not OUT_OF_GAS
    return success, output if success else ''


class Compustate():

    def __init__(self, **kwargs):
        self.memory = []
        self.stack = []
        self.pc = 0
        self.gas = 0
        for kw in kwargs:
            setattr(self, kw, kwargs[kw])


def decode_datalist(arr):
    if isinstance(arr, list):
        arr = ''.join(map(chr, arr))
    o = []
    for i in range(0, len(arr), 32):
        o.append(utils.big_endian_to_int(arr[i:i + 32]))
    return o


def apply_msg(block, tx, msg):
    snapshot = block.snapshot()
    code = block.get_code(msg.to)
    # Transfer value, instaquit if not enough
    block.delta_balance(msg.to, msg.value)
    o = block.delta_balance(msg.sender, -msg.value)
    if not o:
        return 0, msg.gas, []
    compustate = Compustate(gas=msg.gas)
    # Main loop
    while 1:
        if debug:
            print({
                "Stack": compustate.stack,
                "PC": compustate.pc,
                "Gas": compustate.gas,
                "Memory": decode_datalist(compustate.memory),
                "Storage": block.get_storage(msg.to).to_dict(),
            })
        o = apply_op(block, tx, msg, code, compustate)
        if o is not None:
            if debug:
                print('done', o)
            if o == OUT_OF_GAS:
                block.revert(snapshot)
                return 0, 0, []
            else:
                return 1, compustate.gas, o


def create_contract(block, tx, msg):
    snapshot = block.snapshot()
    sender = msg.sender.decode('hex') if len(msg.sender) == 40 else msg.sender
    nonce = utils.encode_int(block.get_nonce(msg.sender))
    recvaddr = utils.sha3(rlp.encode([sender, nonce]))[12:]
    msg.to = recvaddr
    block.increment_nonce(msg.sender)
    # Transfer value, instaquit if not enough
    block.delta_balance(recvaddr, msg.value)
    o = block.delta_balance(msg.sender, msg.value)
    if not o:
        return 0, msg.gas
    compustate = Compustate(gas=msg.gas)
    # Main loop
    while 1:
        o = apply_op(block, tx, msg, msg.data, compustate)
        if o is not None:
            if o == OUT_OF_GAS:
                block.revert(snapshot)
                return 0, 0, []
            else:
                block.set_code(recvaddr, ''.join(map(chr, o)))
                return recvaddr, compustate.gas, o


def get_op_data(code, index):
    opcode = ord(code[index]) if index < len(code) else 0
    if opcode < 96 or (opcode >= 240 and opcode <= 255):
        if opcode in opcodes:
            return opcodes[opcode]
        else:
            return 'INVALID', 0, 0
    elif opcode < 128:
        return 'PUSH' + str(opcode - 95), 0, 1
    else:
        return 'INVALID', 0, 0


def ceil32(x):
    return x if x % 32 == 0 else x + 32 - (x % 32)


def calcfee(block, tx, msg, compustate, op):
    stk, mem = compustate.stack, compustate.memory
    if op == 'SHA3':
        m_extend = max(0, ceil32(stk[-1] + stk[-2]) - len(mem))
        return GSHA3 + m_extend / 32 * GMEMORY
    elif op == 'SLOAD':
        return GSLOAD
    elif op == 'SSTORE':
        return GSSTORE
    elif op == 'MLOAD':
        m_extend = max(0, ceil32(stk[-1] + 32) - len(mem))
        return GSTEP + m_extend / 32 * GMEMORY
    elif op == 'MSTORE':
        m_extend = max(0, ceil32(stk[-1] + 32) - len(mem))
        return GSTEP + m_extend / 32 * GMEMORY
    elif op == 'MSTORE8':
        m_extend = max(0, ceil32(stk[-1] + 1) - len(mem))
        return GSTEP + m_extend / 32 * GMEMORY
    elif op == 'CALL':
        m_extend = max(0,
                       ceil32(stk[-4] + stk[-5]) - len(mem),
                       ceil32(stk[-6] + stk[-7]) - len(mem))
        return GCALL + stk[-1] + m_extend / 32 * GMEMORY
    elif op == 'CREATE':
        m_extend = max(0, ceil32(stk[-3] + stk[-4]) - len(mem))
        return GCREATE + stk[-2] + m_extend / 32 * GMEMORY
    elif op == 'RETURN':
        m_extend = max(0, ceil32(stk[-1] + stk[-2]) - len(mem))
        return GSTEP + m_extend / 32 * GMEMORY
    elif op == 'CALLDATACOPY':
        m_extend = max(0, ceil32(stk[-1] + stk[-3]) - len(mem))
        return GSTEP + m_extend / 32 * GMEMORY
    elif op == 'STOP' or op == 'INVALID':
        return GSTOP
    else:
        return GSTEP

# Does not include paying opfee


def apply_op(block, tx, msg, code, compustate):
    op, in_args, out_args = get_op_data(code, compustate.pc)
    # empty stack error
    if in_args > len(compustate.stack):
        return []
    # out of gas error
    fee = calcfee(block, tx, msg, compustate, op)
    if fee > compustate.gas:
        if debug:
            print("Out of gas", compustate.gas, "need", fee)
            print(op, list(reversed(compustate.stack)))
        return OUT_OF_GAS
    stackargs = []
    for i in range(in_args):
        stackargs.append(compustate.stack.pop())
    if debug:
        import serpent
        if op[:4] == 'PUSH':
            start, n = compustate.pc + 1, int(op[4:])
            print(op, utils.big_endian_to_int(code[start:start + n]))
        else:
            print(op, ' '.join(map(str, stackargs)),
                  serpent.decode_datalist(compustate.memory))
    # Apply operation
    oldgas = compustate.gas
    oldpc = compustate.pc
    compustate.gas -= fee
    compustate.pc += 1
    stk = compustate.stack
    mem = compustate.memory
    if op == 'STOP':
        return []
    elif op == 'ADD':
        stk.append((stackargs[0] + stackargs[1]) % 2 ** 256)
    elif op == 'SUB':
        stk.append((stackargs[0] - stackargs[1]) % 2 ** 256)
    elif op == 'MUL':
        stk.append((stackargs[0] * stackargs[1]) % 2 ** 256)
    elif op == 'DIV':
        if stackargs[1] == 0:
            return []
        stk.append(stackargs[0] / stackargs[1])
    elif op == 'MOD':
        if stackargs[1] == 0:
            return []
        stk.append(stackargs[0] % stackargs[1])
    elif op == 'SDIV':
        if stackargs[1] == 0:
            return []
        if stackargs[0] >= 2 ** 255:
            stackargs[0] -= 2 ** 256
        if stackargs[1] >= 2 ** 255:
            stackargs[1] -= 2 ** 256
        stk.append((stackargs[0] / stackargs[1]) % 2 ** 256)
    elif op == 'SMOD':
        if stackargs[1] == 0:
            return []
        if stackargs[0] >= 2 ** 255:
            stackargs[0] -= 2 ** 256
        if stackargs[1] >= 2 ** 255:
            stackargs[1] -= 2 ** 256
        stk.append((stackargs[0] % stackargs[1]) % 2 ** 256)
    elif op == 'EXP':
        stk.append(pow(stackargs[0], stackargs[1], 2 ** 256))
    elif op == 'NEG':
        stk.append(2 ** 256 - stackargs[0])
    elif op == 'LT':
        stk.append(1 if stackargs[0] < stackargs[1] else 0)
    elif op == 'GT':
        stk.append(1 if stackargs[0] > stackargs[1] else 0)
    elif op == 'SLT':
        if stackargs[0] >= 2 ** 255:
            stackargs[0] -= 2 ** 256
        if stackargs[1] >= 2 ** 255:
            stackargs[1] -= 2 ** 256
        stk.append(1 if stackargs[0] < stackargs[1] else 0)
    elif op == 'SGT':
        if stackargs[0] >= 2 ** 255:
            stackargs[0] -= 2 ** 256
        if stackargs[1] >= 2 ** 255:
            stackargs[1] -= 2 ** 256
        stk.append(1 if stackargs[0] > stackargs[1] else 0)
    elif op == 'EQ':
        stk.append(1 if stackargs[0] == stackargs[1] else 0)
    elif op == 'NOT':
        stk.append(0 if stackargs[0] else 1)
    elif op == 'AND':
        stk.append(stackargs[0] & stackargs[1])
    elif op == 'OR':
        stk.append(stackargs[0] | stackargs[1])
    elif op == 'XOR':
        stk.append(stackargs[0] ^ stackargs[1])
    elif op == 'BYTE':
        if stackargs[0] >= 32:
            stk.append(0)
        else:
            stk.append((stackargs[1] / 256 ** stackargs[0]) % 256)
    elif op == 'SHA3':
        if len(mem) < ceil32(stackargs[0] + stackargs[1]):
            mem.extend([0] * (ceil32(stackargs[0] + stackargs[1]) - len(mem)))
        data = ''.join(map(chr, mem[stackargs[0]:stackargs[0] + stackargs[1]]))
        stk.append(utils.big_endian_to_int(utils.sha3(data)))
    elif op == 'ADDRESS':
        stk.append(msg.to)
    elif op == 'BALANCE':
        stk.append(block.get_balance(msg.to))
    elif op == 'ORIGIN':
        stk.append(tx.sender)
    elif op == 'CALLER':
        stk.append(utils.coerce_to_int(msg.sender))
    elif op == 'CALLVALUE':
        stk.append(msg.value)
    elif op == 'CALLDATALOAD':
        if stackargs[0] >= len(msg.data):
            stk.append(0)
        else:
            dat = msg.data[stackargs[0]:stackargs[0] + 32]
            stk.append(utils.big_endian_to_int(dat + '\x00' * (32 - len(dat))))
    elif op == 'CALLDATASIZE':
        stk.append(len(msg.data))
    elif op == 'CALLDATACOPY':
        if len(mem) < ceil32(stackargs[1] + stackargs[2]):
            mem.extend([0] * (ceil32(stackargs[1] + stackargs[2]) - len(mem)))
        for i in range(stackargs[2]):
            if stackargs[0] + i < len(msg.data):
                mem[stackargs[1] + i] = ord(msg.data[stackargs[0] + i])
            else:
                mem[stackargs[1] + i] = 0
    elif op == 'GASPRICE':
        stk.append(tx.gasprice)
    elif op == 'CODECOPY':
        if len(mem) < ceil32(stackargs[1] + stackargs[2]):
            mem.extend([0] * (ceil32(stackargs[1] + stackargs[2]) - len(mem)))
        for i in range(stackargs[2]):
            if stackargs[0] + i < len(code):
                mem[stackargs[1] + i] = ord(code[stackargs[0] + i])
            else:
                mem[stackargs[1] + i] = 0
    elif op == 'PREVHASH':
        stk.append(utils.big_endian_to_int(block.prevhash))
    elif op == 'COINBASE':
        stk.append(utils.big_endian_to_int(block.coinbase.decode('hex')))
    elif op == 'TIMESTAMP':
        stk.append(block.timestamp)
    elif op == 'NUMBER':
        stk.append(block.number)
    elif op == 'DIFFICULTY':
        stk.append(block.difficulty)
    elif op == 'GASLIMIT':
        stk.append(block.gaslimit)
    elif op == 'POP':
        pass
    elif op == 'DUP':
        stk.append(stackargs[0])
        stk.append(stackargs[0])
    elif op == 'SWAP':
        stk.append(stackargs[0])
        stk.append(stackargs[1])
    elif op == 'MLOAD':
        if len(mem) < ceil32(stackargs[0] + 32):
            mem.extend([0] * (ceil32(stackargs[0] + 32) - len(mem)))
        data = ''.join(map(chr, mem[stackargs[0]:stackargs[0] + 32]))
        stk.append(utils.big_endian_to_int(data))
    elif op == 'MSTORE':
        if len(mem) < ceil32(stackargs[0] + 32):
            mem.extend([0] * (ceil32(stackargs[0] + 32) - len(mem)))
        v = stackargs[1]
        for i in range(31, -1, -1):
            mem[stackargs[0] + i] = v % 256
            v /= 256
    elif op == 'MSTORE8':
        if len(mem) < ceil32(stackargs[0] + 1):
            mem.extend([0] * (ceil32(stackargs[0] + 1) - len(mem)))
        mem[stackargs[0]] = stackargs[1] % 256
    elif op == 'SLOAD':
        stk.append(block.get_storage_data(msg.to, stackargs[0]))
    elif op == 'SSTORE':
        block.set_storage_data(msg.to, stackargs[0], stackargs[1])
    elif op == 'JUMP':
        compustate.pc = stackargs[0]
    elif op == 'JUMPI':
        if stackargs[1]:
            compustate.pc = stackargs[0]
    elif op == 'PC':
        stk.append(compustate.pc)
    elif op == 'MSIZE':
        stk.append(len(mem))
    elif op == 'GAS':
        stk.append(oldgas)
    elif op[:4] == 'PUSH':
        pushnum = int(op[4:])
        compustate.pc = oldpc + 1 + pushnum
        dat = code[oldpc + 1: oldpc + 1 + pushnum]
        stk.append(utils.big_endian_to_int(dat))
    elif op == 'CREATE':
        if len(mem) < ceil32(stackargs[2] + stackargs[3]):
            mem.extend([0] * (ceil32(stackargs[2] + stackargs[3]) - len(mem)))
        gas = stackargs[0]
        value = stackargs[1]
        data = ''.join(map(chr, mem[stackargs[2]:stackargs[2] + stackargs[3]]))
        if debug:
            print("Sub-contract:", msg.to, value, gas, data)
        addr, gas, code = create_contract(
            block, tx, Message(msg.to, '', value, gas, data))
        if debug:
            print("Output of contract creation:", addr, code)
        if addr:
            stk.append(utils.coerce_to_int(addr))
        else:
            stk.append(0)
    elif op == 'CALL':
        if len(mem) < ceil32(stackargs[3] + stackargs[4]):
            mem.extend([0] * (ceil32(stackargs[3] + stackargs[4]) - len(mem)))
        if len(mem) < ceil32(stackargs[5] + stackargs[6]):
            mem.extend([0] * (ceil32(stackargs[5] + stackargs[6]) - len(mem)))
        gas = stackargs[0]
        to = utils.encode_int(stackargs[1])
        to = (('\x00' * (32 - len(to))) + to)[12:]
        value = stackargs[2]
        data = ''.join(map(chr, mem[stackargs[3]:stackargs[3] + stackargs[4]]))
        if debug:
            print("Sub-call:", utils.coerce_addr_to_hex(msg.to),
                  utils.coerce_addr_to_hex(to), value, gas, data)
        result, gas, data = apply_msg(
            block, tx, Message(msg.to, to, value, gas, data))
        if debug:
            print("Output of sub-call:", result, data, "length", len(data),
                  "expected", stackargs[6])
        for i in range(stackargs[6]):
            mem[stackargs[5] + i] = 0
        if result == 0:
            stk.append(0)
        else:
            stk.append(1)
            compustate.gas += gas
            for i in range(len(data)):
                mem[stackargs[5] + i] = data[i]
    elif op == 'RETURN':
        if len(mem) < ceil32(stackargs[0] + stackargs[1]):
            mem.extend([0] * (ceil32(stackargs[0] + stackargs[1]) - len(mem)))
        return mem[stackargs[0]:stackargs[0] + stackargs[1]]
    elif op == 'SUICIDE':
        to = utils.encode_int(stackargs[0])
        to = (('\x00' * (32 - len(to))) + to)[12:]
        block.delta_balance(to, block.get_balance(msg.to))
        block.state.delete(msg.to)
        return []

########NEW FILE########
__FILENAME__ = pyethtool
#!/usr/bin/python
import processblock
import transactions
import blocks
import utils


def sha3(x):
    return utils.sha3(x).encode('hex')


def privtoaddr(x):
    if len(x) == 64:
        x = x.decode('hex')
    return utils.privtoaddr(x)


def mkgenesis(*args):
    return genesis(*args)


def genesis(*args):
    if len(args) == 2 and ':' not in args[0]:
        return blocks.genesis({
            args[0]: int(args[1])}).hex_serialize()
    else:
        o = {}
        for a in args:
            o[a[:a.find(':')]] = int(a[a.find(':') + 1:])
        return blocks.genesis(o).hex_serialize()


def mktx(nonce, to, value, data):
    return transactions.Transaction(
        int(nonce), 10 ** 12, 10000, to, int(value), data.decode('hex')
    ).hex_serialize(False)


def mkcontract(*args):
    return contract(*args)


def contract(nonce, value, code):
    return transactions.contract(
        int(nonce), 10 ** 12, 10000, int(value), code.decode('hex')
    ).hex_serialize(False)


def sign(txdata, key):
    return transactions.Transaction.hex_deserialize(txdata).sign(key).hex_serialize(True)

def alloc(blockdata, addr, val):
    val = int(val)
    block = blocks.Block.hex_deserialize(blockdata)
    block.delta_balance(addr, val)
    return block.hex_serialize()


def applytx(blockdata, txdata, debug=0, limit=2 ** 100):
    block = blocks.Block.hex_deserialize(blockdata)
    tx = transactions.Transaction.hex_deserialize(txdata)
    if tx.startgas > limit:
        raise Exception("Transaction is asking for too much gas!")
    if debug:
        processblock.debug = 1
    success, o = processblock.apply_tx(block, tx)
    return {
        "block": block.hex_serialize(),
        "result": ''.join(o).encode('hex') if tx.to else ''.join(o)
    }


def getbalance(blockdata, address):
    block = blocks.Block.hex_deserialize(blockdata)
    return block.get_balance(address)


def getcode(blockdata, address):
    block = blocks.Block.hex_deserialize(blockdata)
    return block.get_code(address).encode('hex')


def getstate(blockdata, address=None):
    block = blocks.Block.hex_deserialize(blockdata)
    if not address:
        return block.to_dict()
    else:
        return block.get_storage(address).to_dict()


def account_to_dict(blockdata, address):
    block = blocks.Block.hex_deserialize(blockdata)
    return block.account_to_dict(address)

########NEW FILE########
__FILENAME__ = rlp
def int_to_big_endian(integer):
    '''convert a integer to big endian binary string'''
    # 0 is a special case, treated same as ''
    if integer == 0:
        return ''
    s = '%x' % integer
    if len(s) & 1:
        s = '0' + s
    return s.decode('hex')

def big_endian_to_int(string):
    '''convert a big endian binary string to integer'''
    # '' is a special case, treated same as 0
    string = string or '\x00'
    s = string.encode('hex')
    return long(s, 16)

def __decode(s, pos=0):
    assert pos < len(s), "read beyond end of string in __decode"

    fchar = ord(s[pos])
    if fchar < 128:
        return (s[pos], pos + 1)
    elif fchar < 184:
        b = fchar - 128
        return (s[pos + 1:pos + 1 + b], pos + 1 + b)
    elif fchar < 192:
        b = fchar - 183
        b2 = big_endian_to_int(s[pos + 1:pos + 1 + b])
        return (s[pos + 1 + b:pos + 1 + b + b2], pos + 1 + b + b2)
    elif fchar < 248:
        o = []
        pos += 1
        pos_end = pos + fchar - 192

        while pos < pos_end:
            obj, pos = __decode(s, pos)
            o.append(obj)
        assert pos == pos_end, "read beyond list boundary in __decode"
        return (o, pos)
    else:
        b = fchar - 247
        b2 = big_endian_to_int(s[pos + 1:pos + 1 + b])
        o = []
        pos += 1 + b
        pos_end = pos + b2
        while pos < pos_end:
            obj, pos = __decode(s, pos)
            o.append(obj)
        assert pos == pos_end, "read beyond list boundary in __decode"
        return (o, pos)


def decode(s):
    if s:
        return __decode(s)[0]


def into(data, pos):
    fchar = ord(data[pos])
    if fchar < 192:
        raise Exception("Cannot descend further")
    elif fchar < 248:
        return pos + 1
    else:
        return pos + 1 + (fchar - 247)


def next(data, pos):
    fchar = ord(data[pos])
    if fchar < 128:
        return pos + 1
    elif (fchar % 64) < 56:
        return pos + 1 + (fchar % 64)
    else:
        b = (fchar % 64) - 55
        b2 = big_endian_to_int(data[pos + 1:pos + 1 + b])
        return pos + 1 + b + b2


def descend(data, *indices):
    pos = 0
    for i in indices:
        fin = next(data, pos)
        pos = into(data, pos)
        for j in range(i):
            pos = next(data, pos)
            if pos >= fin:
                raise Exception("End of list")
    return data[pos: fin]


def encode_length(L, offset):
    if L < 56:
        return chr(L + offset)
    elif L < 256 ** 8:
        BL = int_to_big_endian(L)
        return chr(len(BL) + offset + 55) + BL
    else:
        raise Exception("input too long")


def encode(s):
    if isinstance(s, (str, unicode)):
        s = str(s)
        if len(s) == 1 and ord(s) < 128:
            return s
        else:
            return encode_length(len(s), 128) + s
    elif isinstance(s, list):
        output = ''
        for item in s:
            output += encode(item)
        return encode_length(len(output), 192) + output
    raise TypeError("Encoding of %s not supported" % type(s))

########NEW FILE########
__FILENAME__ = signals
from dispatch import Signal

'''
.. note::
    *sender* is used by *receiver* to specify which source to accept signal
    from, usually it's some *class name*.
    if you want to carry a instance arg, don't use it, instead, you can add one
    more arg in the signal's `provoding_args`
'''

config_ready = Signal(providing_args=["config"])

p2p_address_ready = Signal(providing_args=["ip", "port"])

peer_connection_accepted = Signal(providing_args=["connection", "ip", "port"])
peer_disconnect_requested = Signal(providing_args=["peer", "forget"])

peer_addresses_received = Signal(providing_args=["addresses"])
peer_handshake_success = Signal(providing_args=["peer"])

getpeers_received = Signal(providing_args=["peer"])
gettransactions_received = Signal(providing_args=["peer"])

remote_blocks_received = Signal(providing_args=["block_lst", "peer"])
remote_chain_requested = Signal(providing_args=["parents", "count"])
local_chain_requested = Signal(providing_args=["peer", "blocks", "count"])
send_local_blocks = Signal(providing_args=["blocks"])

local_transaction_received = Signal(providing_args=["transaction"])
remote_transactions_received = Signal(providing_args=["transactions"])
send_local_transactions = Signal(providing_args=["transaction"])

########NEW FILE########
__FILENAME__ = stoppable
import threading
import logging

logger = logging.getLogger(__name__)


class StoppableLoopThread(threading.Thread):

    def __init__(self):
        super(StoppableLoopThread, self).__init__()
        self._stopped = False
        self.lock = threading.Lock()

    def stop(self):
        with self.lock:
            self._stopped = True
        logger.debug(
            'Thread {0} is requested to stop'.format(self))

    def stopped(self):
        with self.lock:
            return self._stopped

    def pre_loop(self):
        logger.debug('Thread {0} start to run'.format(self))

    def post_loop(self):
        logger.debug('Thread {0} stopped'.format(self))

    def run(self):
        self.pre_loop()
        while not self.stopped():
            self.loop_body()
        self.post_loop()

    def loop_body(self):
        raise Exception('Not Implemented')

########NEW FILE########
__FILENAME__ = tcpserver
import socket
import time
import sys
import traceback
import logging

from dispatch import receiver

from stoppable import StoppableLoopThread
import signals

logger = logging.getLogger(__name__)


def get_public_ip():
    try:
        # for python3
        from urllib.request import urlopen
    except ImportError:
        # for python2
        from urllib import urlopen
    return urlopen('http://icanhazip.com/').read().strip()


def upnp_add(port):
    '''
    :param port: local port
    :return: `None` if failed, `external_ip, external_port` if succeed
    '''
    logger.debug('Setting UPNP')

    import miniupnpc
    upnpc = miniupnpc.UPnP()
    upnpc.discoverdelay = 200
    ndevices = upnpc.discover()
    logger.debug('%d UPNP device(s) detected', ndevices)

    if not ndevices:
        return None

    upnpc.selectigd()
    external_ip = upnpc.externalipaddress()
    logger.debug('external ip: %s', external_ip)
    logger.debug('status: %s, connection type: %s',
                 upnpc.statusinfo(),
                 upnpc.connectiontype())

    # find a free port for the redirection
    external_port = port
    found = False

    while True:
        redirect = upnpc.getspecificportmapping(external_port, 'TCP')
        if redirect is None:
            found = True
            break
        if external_port >= 65535:
            break
        external_port = external_port + 1

    if not found:
        logger.debug('No redirect candidate %s TCP => %s port %u TCP',
                     external_ip, upnpc.lanaddr, port)
        return None

    logger.debug('trying to redirect %s port %u TCP => %s port %u TCP',
                 external_ip, external_port, upnpc.lanaddr, port)

    res = upnpc.addportmapping(external_port, 'TCP',
                               upnpc.lanaddr, port,
                               'pyethereum p2p port %u' % external_port,
                               '')

    if res:
        logger.info('Success to redirect %s port %u TCP => %s port %u TCP',
                    external_ip, external_port, upnpc.lanaddr, port)
    else:
        return None
    return upnpc, external_ip, external_port


def upnp_delete(upnpc, external_port):
    res = upnpc.deleteportmapping(external_port, 'TCP')
    if res:
        logger.debug('Successfully deleted port mapping')
    else:
        logger.debug('Failed to remove port mapping')


class TcpServer(StoppableLoopThread):

    def __init__(self):
        super(TcpServer, self).__init__()
        self.daemon = True

        self.sock = None
        self.ip = '0.0.0.0'
        self.port = 31033

        self.upnpc = None
        self.external_ip = None
        self.external_port = None

    def configure(self, config):
        self.listen_host = config.get('network', 'listen_host')
        self.port = config.getint('network', 'listen_port')

    def pre_loop(self):
        # start server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.listen_host, self.port))
        sock.listen(5)
        self.sock = sock
        self.ip, self.port = sock.getsockname()
        logger.info("TCP server started {0}:{1}".format(self.ip, self.port))

        # setup upnp
        try:
            upnp_res = upnp_add(self.port)
            if upnp_res:
                self.upnpc, self.external_ip, self.external_port = upnp_res
        except Exception as e:
            logger.debug('upnp failed: %s', e)

        if not self.external_ip:
            try:
                self.external_ip = get_public_ip()
                self.external_port = self.port
            except Exception as e:
                logger.debug('can\'t get public ip')

        if self.external_ip:
            signals.p2p_address_ready.send(sender=None,
                                           ip=self.external_ip,
                                           port=self.external_port)
            logger.info('my public address is %s:%s',
                        self.external_ip, self.external_port)

        super(TcpServer, self).pre_loop()

    def loop_body(self):
        logger.debug('in run loop')
        try:
            connection, (ip, port) = self.sock.accept()
        except IOError:
            traceback.print_exc(file=sys.stdout)
            time.sleep(0.01)
            return
        signals.peer_connection_accepted.send(sender=None,
                                              connection=connection,
                                              ip=ip,
                                              port=port)

    def post_loop(self):
        if self.upnpc:
            upnp_delete(self.upnpc, self.external_port)
        super(TcpServer, self).post_loop()


tcp_server = TcpServer()


@receiver(signals.config_ready)
def config_tcp_server(sender, config, **kwargs):
    tcp_server.configure(config)

########NEW FILE########
__FILENAME__ = transactions
import rlp
from bitcoin import encode_pubkey
from bitcoin import ecdsa_raw_sign, ecdsa_raw_recover
import utils

tx_structure = [
    ["nonce", "int", 0],
    ["gasprice", "int", 0],
    ["startgas", "int", 0],
    ["to", "addr", ''],
    ["value", "int", 0],
    ["data", "bin", ''],
    ["v", "int", 0],
    ["r", "int", 0],
    ["s", "int", 0],
]


class Transaction(object):

    """
    A transaction is stored as:
    [ nonce, gasprice, startgas, to, value, data, v, r, s]

    nonce is the number of transactions already sent by that account, encoded
    in binary form (eg.  0 -> '', 7 -> '\x07', 1000 -> '\x03\xd8').

    (v,r,s) is the raw Electrum-style signature of the transaction without the
    signature made with the private key corresponding to the sending account,
    with 0 <= v <= 3. From an Electrum-style signature (65 bytes) it is
    possible to extract the public key, and thereby the address, directly.

    A valid transaction is one where:
    (i) the signature is well-formed (ie. 0 <= v <= 3, 0 <= r < P, 0 <= s < N,
        0 <= r < P - N if v >= 2), and
    (ii) the sending account has enough funds to pay the fee and the value.
    """

    # nonce,gasprice,startgas,to,value,data,v,r,s
    def __init__(self, nonce, gasprice, startgas, to, value, data, v=0, r=0,
                 s=0):
        self.nonce = nonce
        self.gasprice = gasprice
        self.startgas = startgas
        self.to = to
        self.value = value
        self.data = data
        self.v, self.r, self.s = v, r, s

        # Determine sender
        if self.r and self.s:
            rawhash = utils.sha3(self.serialize(False))
            pub = encode_pubkey(
                ecdsa_raw_recover(rawhash, (self.v, self.r, self.s)),
                'bin')
            self.sender = utils.sha3(pub[1:])[-20:].encode('hex')
        # does not include signature
        else:
            self.sender = 0

    @classmethod
    def deserialize(cls, rlpdata):
        return cls.create(rlp.decode(rlpdata))

    @classmethod
    def create(cls, args):
        kargs = dict()
        assert len(args) in (len(tx_structure), len(tx_structure) - 3)
        # Deserialize all properties
        for i, (name, typ, default) in enumerate(tx_structure):
            if i < len(args):
                kargs[name] = utils.decoders[typ](args[i])
            else:
                kargs[name] = default
        return Transaction(**kargs)

    @classmethod
    def hex_deserialize(cls, hexrlpdata):
        return cls.deserialize(hexrlpdata.decode('hex'))

    def sign(self, key):
        rawhash = utils.sha3(self.serialize(False))
        self.v, self.r, self.s = ecdsa_raw_sign(rawhash, key)
        self.sender = utils.privtoaddr(key)
        return self

    def serialize(self, signed=True):
        o = []
        for i, (name, typ, default) in enumerate(tx_structure):
            o.append(utils.encoders[typ](getattr(self, name)))
        return rlp.encode(o if signed else o[:-3])

    def hex_serialize(self, signed=True):
        return self.serialize(signed).encode('hex')

    @property
    def hash(self):
        return utils.sha3(self.serialize())

    def hex_hash(self):
        return self.hash.encode('hex')

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.hash == other.hash

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return '<Transaction(%s)>' % self.hex_hash()[:4]


def contract(nonce, gasprice, startgas, endowment, code, v=0, r=0, s=0):
    ''' a contract is a special transaction without the `to` arguments
    '''
    tx = Transaction(nonce, gasprice, startgas, '', endowment, code)
    tx.v, tx.r, tx.s = v, r, s
    return tx

########NEW FILE########
__FILENAME__ = trie
#!/usr/bin/env python

import os
import rlp
import utils
import db

DB = db.DB


def bin_to_nibbles(s):
    """convert string s to nibbles (half-bytes)

    >>> bin_to_nibbles("")
    []
    >>> bin_to_nibbles("h")
    [6, 8]
    >>> bin_to_nibbles("he")
    [6, 8, 6, 5]
    >>> bin_to_nibbles("hello")
    [6, 8, 6, 5, 6, 12, 6, 12, 6, 15]
    """
    res = []
    for x in s:
        res += divmod(ord(x), 16)
    return res


def nibbles_to_bin(nibbles):
    if any(x > 15 or x < 0 for x in nibbles):
        raise Exception("nibbles can only be [0,..15]")

    if len(nibbles) % 2:
        raise Exception("nibbles must be of even numbers")

    res = ''
    for i in range(0, len(nibbles), 2):
        res += chr(16 * nibbles[i] + nibbles[i + 1])
    return res


NIBBLE_TERMINATOR = 16


def with_terminator(nibbles):
    nibbles = nibbles[:]
    if not nibbles or nibbles[-1] != NIBBLE_TERMINATOR:
        nibbles.append(NIBBLE_TERMINATOR)
    return nibbles


def without_terminator(nibbles):
    nibbles = nibbles[:]
    if nibbles and nibbles[-1] == NIBBLE_TERMINATOR:
        del nibbles[-1]
    return nibbles


def adapt_terminator(nibbles, has_terminator):
    if has_terminator:
        return with_terminator(nibbles)
    else:
        return without_terminator(nibbles)


def pack_nibbles(nibbles):
    """pack nibbles to binary

    :param nibbles: a nibbles sequence. may have a terminator
    """

    if nibbles[-1:] == [NIBBLE_TERMINATOR]:
        flags = 2
        nibbles = nibbles[:-1]
    else:
        flags = 0

    oddlen = len(nibbles) % 2
    flags |= oddlen   # set lowest bit if odd number of nibbles
    if oddlen:
        nibbles = [flags] + nibbles
    else:
        nibbles = [flags, 0] + nibbles
    o = ''
    for i in range(0, len(nibbles), 2):
        o += chr(16 * nibbles[i] + nibbles[i + 1])
    return o


def unpack_to_nibbles(bindata):
    """unpack packed binary data to nibbles

    :param bindata: binary packed from nibbles
    :return: nibbles sequence, may have a terminator
    """
    o = bin_to_nibbles(bindata)
    flags = o[0]
    if flags & 2:
        o.append(NIBBLE_TERMINATOR)
    if flags & 1 == 1:
        o = o[1:]
    else:
        o = o[2:]
    return o


def starts_with(full, part):
    ''' test whether the items in the part is
    the leading items of the full
    '''
    if len(full) < len(part):
        return False
    return full[:len(part)] == part


(
    NODE_TYPE_BLANK,
    NODE_TYPE_LEAF,
    NODE_TYPE_EXTENSION,
    NODE_TYPE_BRANCH
) = tuple(range(4))


def is_key_value_type(node_type):
    return node_type in [NODE_TYPE_LEAF,
                         NODE_TYPE_EXTENSION]

BLANK_NODE = ''
BLANK_ROOT = ''


class Trie(object):

    def __init__(self, dbfile, root_hash=BLANK_ROOT):
        '''it also present a dictionary like interface

        :param dbfile: key value database
        :root: blank or trie node in form of [key, value] or [v0,v1..v15,v]
        '''
        dbfile = os.path.abspath(dbfile)
        self.db = DB(dbfile)
        self.set_root_hash(root_hash)

    @property
    def root_hash(self):
        '''always empty or a 32 bytes string
        '''
        return self.get_root_hash()

    def get_root_hash(self):
        if self.root_node == BLANK_NODE:
            return BLANK_ROOT
        assert isinstance(self.root_node, list)
        val = rlp.encode(self.root_node)
        key = utils.sha3(val)
        self.db.put(key, val)
        return key

    @root_hash.setter
    def root_hash(self, value):
        self.set_root_hash(value)

    def set_root_hash(self, root_hash):
        if root_hash == BLANK_ROOT:
            self.root_node = BLANK_NODE
            return
        assert isinstance(root_hash, (str, unicode))
        assert len(root_hash) in [0, 32]
        self.root_node = self._decode_to_node(root_hash)

    def clear(self):
        ''' clear all tree data
        '''
        self._delete_child_stroage(self.root_node)
        self._delete_node_storage(self.root_node)
        self.db.commit()
        self.root_node = BLANK_NODE

    def _delete_child_stroage(self, node):
        node_type = self._get_node_type(node)
        if node_type == NODE_TYPE_BRANCH:
            for item in node[:16]:
                self._delete_child_stroage(self._decode_to_node(item))
        elif is_key_value_type(node_type):
            node_type = self._get_node_type(node)
            if node_type == NODE_TYPE_EXTENSION:
                self._delete_child_stroage(self._decode_to_node(node[1]))

    def _encode_node(self, node):
        if node == BLANK_NODE:
            return BLANK_NODE
        assert isinstance(node, list)
        rlpnode = rlp.encode(node)
        if len(rlpnode) < 32:
            return node

        hashkey = utils.sha3(rlpnode)
        self.db.put(hashkey, rlpnode)
        return hashkey

    def _decode_to_node(self, encoded):
        if encoded == BLANK_NODE:
            return BLANK_NODE
        if isinstance(encoded, list):
            return encoded
        return rlp.decode(self.db.get(encoded))

    def _get_node_type(self, node):
        ''' get node type and content

        :param node: node in form of list, or BLANK_NODE
        :return: node type
        '''
        if node == BLANK_NODE:
            return NODE_TYPE_BLANK

        if len(node) == 2:
            nibbles = unpack_to_nibbles(node[0])
            has_terminator = (nibbles and nibbles[-1] == NIBBLE_TERMINATOR)
            return NODE_TYPE_LEAF if has_terminator\
                else NODE_TYPE_EXTENSION
        if len(node) == 17:
            return NODE_TYPE_BRANCH

    def _get(self, node, key):
        """ get value inside a node

        :param node: node in form of list, or BLANK_NODE
        :param key: nibble list without terminator
        :return:
            BLANK_NODE if does not exist, otherwise value or hash
        """
        node_type = self._get_node_type(node)
        if node_type == NODE_TYPE_BLANK:
            return BLANK_NODE

        if node_type == NODE_TYPE_BRANCH:
            # already reach the expected node
            if not key:
                return node[-1]
            sub_node = self._decode_to_node(node[key[0]])
            return self._get(sub_node, key[1:])

        # key value node
        curr_key = without_terminator(unpack_to_nibbles(node[0]))
        if node_type == NODE_TYPE_LEAF:
            return node[1] if key == curr_key else BLANK_NODE

        if node_type == NODE_TYPE_EXTENSION:
            # traverse child nodes
            if starts_with(key, curr_key):
                sub_node = self._decode_to_node(node[1])
                return self._get(sub_node, key[len(curr_key):])
            else:
                return BLANK_NODE

    def _update(self, node, key, value):
        """ update item inside a node

        :param node: node in form of list, or BLANK_NODE
        :param key: nibble list without terminator
            .. note:: key may be []
        :param value: value string
        :return: new node

        if this node is changed to a new node, it's parent will take the
        responsibility to *store* the new node storage, and delete the old
        node storage
        """
        assert value != BLANK_NODE
        node_type = self._get_node_type(node)

        if node_type == NODE_TYPE_BLANK:
            return [pack_nibbles(with_terminator(key)), value]

        elif node_type == NODE_TYPE_BRANCH:
            if not key:
                node[-1] = value
            else:
                new_node = self._update_and_delete_storage(
                    self._decode_to_node(node[key[0]]),
                    key[1:], value)
                node[key[0]] = self._encode_node(new_node)
            return node

        elif is_key_value_type(node_type):
            return self._update_kv_node(node, key, value)

    def _update_and_delete_storage(self, node, key, value):
        old_node = node[:]
        new_node = self._update(node, key, value)
        if old_node != new_node:
            self._delete_node_storage(old_node)
        return new_node

    def _update_kv_node(self, node, key, value):
        node_type = self._get_node_type(node)
        curr_key = without_terminator(unpack_to_nibbles(node[0]))
        is_inner = node_type == NODE_TYPE_EXTENSION

        # find longest common prefix
        prefix_length = 0
        for i in range(min(len(curr_key), len(key))):
            if key[i] != curr_key[i]:
                break
            prefix_length = i + 1

        remain_key = key[prefix_length:]
        remain_curr_key = curr_key[prefix_length:]

        if remain_key == [] == remain_curr_key:
            if not is_inner:
                return [node[0], value]
            new_node = self._update_and_delete_storage(
                self._decode_to_node(node[1]), remain_key, value)

        elif remain_curr_key == []:
            if is_inner:
                new_node = self._update_and_delete_storage(
                    self._decode_to_node(node[1]), remain_key, value)
            else:
                new_node = [BLANK_NODE] * 17
                new_node[-1] = node[1]
                new_node[remain_key[0]] = self._encode_node([
                    pack_nibbles(with_terminator(remain_key[1:])),
                    value
                ])
        else:
            new_node = [BLANK_NODE] * 17
            if len(remain_curr_key) == 1 and is_inner:
                new_node[remain_curr_key[0]] = node[1]
            else:
                new_node[remain_curr_key[0]] = self._encode_node([
                    pack_nibbles(
                        adapt_terminator(remain_curr_key[1:], not is_inner)
                    ),
                    node[1]
                ])

            if remain_key == []:
                new_node[-1] = value
            else:
                new_node[remain_key[0]] = self._encode_node([
                    pack_nibbles(with_terminator(remain_key[1:])), value
                ])

        if prefix_length:
            # create node for key prefix
            return [pack_nibbles(curr_key[:prefix_length]),
                    self._encode_node(new_node)]
        else:
            return new_node

    def _delete_node_storage(self, node):
        '''delete storage
        :param node: node in form of list, or BLANK_NODE
        '''
        if node == BLANK_NODE:
            return
        assert isinstance(node, list)
        encoded = self._encode_node(node)
        if len(encoded) < 32:
            return
        self.db.delete(encoded)

    def _delete(self, node, key):
        """ update item inside a node

        :param node: node in form of list, or BLANK_NODE
        :param key: nibble list without terminator
            .. note:: key may be []
        :return: new node

        if this node is changed to a new node, it's parent will take the
        responsibility to *store* the new node storage, and delete the old
        node storage
        """
        node_type = self._get_node_type(node)
        if node_type == NODE_TYPE_BLANK:
            return BLANK_NODE

        if node_type == NODE_TYPE_BRANCH:
            return self._delete_branch_node(node, key)

        if is_key_value_type(node_type):
            return self._delete_kv_node(node, key)

    def _normalize_branch_node(self, node):
        '''node should have only one item changed
        '''
        not_blank_items_count = sum(1 for x in range(17) if node[x])
        assert not_blank_items_count >= 1

        if not_blank_items_count > 1:
            return node

        # now only one item is not blank
        not_blank_index = [i for i, item in enumerate(node) if item][0]

        # the value item is not blank
        if not_blank_index == 16:
            return [pack_nibbles(with_terminator([])), node[16]]

        # normal item is not blank
        sub_node = self._decode_to_node(node[not_blank_index])
        sub_node_type = self._get_node_type(sub_node)

        if is_key_value_type(sub_node_type):
            # collape subnode to this node, not this node will have same
            # terminator with the new sub node, and value does not change
            new_key = [not_blank_index] + \
                unpack_to_nibbles(sub_node[0])
            return [pack_nibbles(new_key), sub_node[1]]
        if sub_node_type == NODE_TYPE_BRANCH:
            return [pack_nibbles([not_blank_index]),
                    self._encode_node(sub_node)]
        assert False

    def _delete_and_delete_storage(self, node, key):
        old_node = node[:]
        new_node = self._delete(node, key)
        if old_node != new_node:
            self._delete_node_storage(old_node)
        return new_node

    def _delete_branch_node(self, node, key):
        # already reach the expected node
        if not key:
            node[-1] = BLANK_NODE
            return self._normalize_branch_node(node)

        encoded_new_sub_node = self._encode_node(
            self._delete_and_delete_storage(
                self._decode_to_node(node[key[0]]), key[1:])
        )

        if encoded_new_sub_node == node[key[0]]:
            return node

        node[key[0]] = encoded_new_sub_node
        if encoded_new_sub_node == BLANK_NODE:
            return self._normalize_branch_node(node)

        return node

    def _delete_kv_node(self, node, key):
        node_type = self._get_node_type(node)
        assert is_key_value_type(node_type)
        curr_key = without_terminator(unpack_to_nibbles(node[0]))

        if not starts_with(key, curr_key):
            # key not found
            return node

        if node_type == NODE_TYPE_LEAF:
            return BLANK_NODE if key == curr_key else node

        # for inner key value type
        new_sub_node = self._delete_and_delete_storage(
            self._decode_to_node(node[1]), key[len(curr_key):])

        if self._encode_node(new_sub_node) == node[1]:
            return node

        # new sub node is BLANK_NODE
        if new_sub_node == BLANK_NODE:
            return BLANK_NODE

        assert isinstance(new_sub_node, list)

        # new sub node not blank, not value and has changed
        new_sub_node_type = self._get_node_type(new_sub_node)

        if is_key_value_type(new_sub_node_type):
            # collape subnode to this node, not this node will have same
            # terminator with the new sub node, and value does not change
            new_key = curr_key + unpack_to_nibbles(new_sub_node[0])
            return [pack_nibbles(new_key), new_sub_node[1]]

        if new_sub_node_type == NODE_TYPE_BRANCH:
            return [pack_nibbles(curr_key), self._encode_node(new_sub_node)]

        # should be no more cases
        assert False

    def delete(self, key):
        '''
        :param key: a string with length of [0, 32]
        '''
        if not isinstance(key, (str, unicode)):
            raise Exception("Key must be string")

        if len(key) > 32:
            raise Exception("Max key length is 32")

        self.root_node = self._delete_and_delete_storage(
            self.root_node,
            bin_to_nibbles(str(key)))
        self.get_root_hash()
        self.db.commit()

    def _get_size(self, node):
        '''Get counts of (key, value) stored in this and the descendant nodes

        :param node: node in form of list, or BLANK_NODE
        '''
        if node == BLANK_NODE:
            return 0

        node_type = self._get_node_type(node)

        if is_key_value_type(node_type):
            value_is_node = node_type == NODE_TYPE_EXTENSION
            if value_is_node:
                return self._get_size(self._decode_to_node(node[1]))
            else:
                return 1
        elif node_type == NODE_TYPE_BRANCH:
            sizes = [self._get_size(self._decode_to_node(node[x]))
                     for x in range(16)]
            sizes = sizes + [1 if node[-1] else 0]
            return sum(sizes)

    def _to_dict(self, node):
        '''convert (key, value) stored in this and the descendant nodes
        to dict items.

        :param node: node in form of list, or BLANK_NODE

        .. note::

            Here key is in full form, rather than key of the individual node
        '''
        if node == BLANK_NODE:
            return {}

        node_type = self._get_node_type(node)

        if is_key_value_type(node_type):
            nibbles = without_terminator(unpack_to_nibbles(node[0]))
            key = '+'.join([str(x) for x in nibbles])
            if node_type == NODE_TYPE_EXTENSION:
                sub_dict = self._to_dict(self._decode_to_node(node[1]))
            else:
                sub_dict = {str(NIBBLE_TERMINATOR): node[1]}

            # prepend key of this node to the keys of children
            res = {}
            for sub_key, sub_value in sub_dict.iteritems():
                full_key = '{0}+{1}'.format(key, sub_key).strip('+')
                res[full_key] = sub_value
            return res

        elif node_type == NODE_TYPE_BRANCH:
            res = {}
            for i in range(16):
                sub_dict = self._to_dict(self._decode_to_node(node[i]))

                for sub_key, sub_value in sub_dict.iteritems():
                    full_key = '{0}+{1}'.format(i, sub_key).strip('+')
                    res[full_key] = sub_value

            if node[16]:
                res[str(NIBBLE_TERMINATOR)] = node[-1]
            return res

    def to_dict(self):
        d = self._to_dict(self.root_node)
        res = {}
        for key_str, value in d.iteritems():
            if key_str:
                nibbles = [int(x) for x in key_str.split('+')]
            else:
                nibbles = []
            key = nibbles_to_bin(without_terminator(nibbles))
            res[key] = value
        return res

    def get(self, key):
        return self._get(self.root_node, bin_to_nibbles(str(key)))

    def __len__(self):
        return self._get_size(self.root_node)

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        return self.update(key, value)

    def __delitem__(self, key):
        return self.delete(key)

    def __iter__(self):
        return iter(self.to_dict())

    def __contains__(self, key):
        return self.get(key) != BLANK_NODE

    def update(self, key, value):
        '''
        :param key: a string with length of [0, 32]
        :value: a string
        '''
        if not isinstance(key, (str, unicode)):
            raise Exception("Key must be string")

        if len(key) > 32:
            raise Exception("Max key length is 32")

        if not isinstance(value, (str, unicode)):
            raise Exception("Value must be string")

        if value == '':
            return self.delete(key)

        self.root_node = self._update_and_delete_storage(
            self.root_node,
            bin_to_nibbles(str(key)),
            value)
        self.get_root_hash()
        self.db.commit()

    def root_hash_valid(self):
        if self.root_hash == BLANK_ROOT:
            return True
        return self.root_hash in self.db

if __name__ == "__main__":
    import sys

    def encode_node(nd):
        if isinstance(nd, str):
            return nd.encode('hex')
        else:
            return rlp.encode(nd).encode('hex')

    if len(sys.argv) >= 2:
        if sys.argv[1] == 'insert':
            t = Trie(sys.argv[2], sys.argv[3].decode('hex'))
            t.update(sys.argv[4], sys.argv[5])
            print encode_node(t.root_hash)
        elif sys.argv[1] == 'get':
            t = Trie(sys.argv[2], sys.argv[3].decode('hex'))
            print t.get(sys.argv[4])

########NEW FILE########
__FILENAME__ = utils
import logging
import logging.config
from sha3 import sha3_256
from bitcoin import privtopub
import struct
import os
import sys
import rlp
import db
import random
from rlp import big_endian_to_int, int_to_big_endian


logger = logging.getLogger(__name__)


# decorator
def debug(label):
    def deb(f):
        def inner(*args, **kwargs):
            i = random.randrange(1000000)
            print label, i, 'start', args
            x = f(*args, **kwargs)
            print label, i, 'end', x
            return x
        return inner
    return deb


def sha3(seed):
    return sha3_256(seed).digest()


def privtoaddr(x):
    if len(x) > 32:
        x = x.decode('hex')
    return sha3(privtopub(x)[1:])[12:].encode('hex')


def zpad(x, l):
    return '\x00' * max(0, l - len(x)) + x


def coerce_addr_to_bin(x):
    if isinstance(x, (int, long)):
        return zpad(int_to_big_endian(x), 20).encode('hex')
    elif len(x) == 40 or len(x) == 0:
        return x.decode('hex')
    else:
        return zpad(x, 20)[-20:]


def coerce_addr_to_hex(x):
    if isinstance(x, (int, long)):
        return zpad(int_to_big_endian(x), 20).encode('hex')
    elif len(x) == 40 or len(x) == 0:
        return x
    else:
        return zpad(x, 20)[-20:].encode('hex')


def coerce_to_int(x):
    if isinstance(x, (int, long)):
        return x
    elif len(x) == 40:
        return big_endian_to_int(x.decode('hex'))
    else:
        return big_endian_to_int(x)


def coerce_to_bytes(x):
    if isinstance(x, (int, long)):
        return int_to_big_endian(x)
    elif len(x) == 40:
        return x.decode('hex')
    else:
        return x


def int_to_big_endian4(integer):
    ''' 4 bytes big endian integer'''
    return struct.pack('>I', integer)


def recursive_int_to_big_endian(item):
    ''' convert all int to int_to_big_endian recursively
    '''
    if isinstance(item, (int, long)):
        return int_to_big_endian(item)
    elif isinstance(item, (list, tuple)):
        res = []
        for item in item:
            res.append(recursive_int_to_big_endian(item))
        return res
    return item


def rlp_encode(item):
    '''
    item can be nested string/integer/list of string/integer
    '''
    return rlp.encode(recursive_int_to_big_endian(item))

# Format encoders/decoders for bin, addr, int


def decode_hash(v):
    '''decodes a bytearray from hash'''
    return db_get(v)


def decode_bin(v):
    '''decodes a bytearray from serialization'''
    if not isinstance(v, (str, unicode)):
        raise Exception("Value must be binary, not RLP array")
    return v


def decode_addr(v):
    '''decodes an address from serialization'''
    if len(v) not in [0, 20]:
        raise Exception("Serialized addresses must be empty or 20 bytes long!")
    return v.encode('hex')


def decode_int(v):
    '''decodes and integer from serialization'''
    if len(v) > 0 and v[0] == '\x00':
        raise Exception("No leading zero bytes allowed for integers")
    return big_endian_to_int(v)


def decode_root(root):
    if isinstance(root, list):
        if len(rlp.encode(root)) >= 32:
            raise Exception("Direct RLP roots must have length <32")
    elif isinstance(root, (str, unicode)):
        if len(root) != 0 and len(root) != 32:
            raise Exception("String roots must be empty or length-32")
    else:
        raise Exception("Invalid root")
    return root


def encode_hash(v):
    '''encodes a bytearray into hash'''
    k = sha3(v)
    db_put(k, v)
    return k


def encode_bin(v):
    '''encodes a bytearray into serialization'''
    return v


def encode_root(v):
    '''encodes a trie root into serialization'''
    return v


def encode_addr(v):
    '''encodes an address into serialization'''
    if not isinstance(v, (str, unicode)) or len(v) not in [0, 40]:
        raise Exception("Address must be empty or 40 chars long")
    return v.decode('hex')


def encode_int(v):
    '''encodes an integer into serialization'''
    if not isinstance(v, (int, long)) or v < 0 or v >= 2 ** 256:
        raise Exception("Integer invalid or out of range")
    return int_to_big_endian(v)

decoders = {
    "hash": decode_hash,
    "bin": decode_bin,
    "addr": decode_addr,
    "int": decode_int,
    "trie_root": decode_root,
}

encoders = {
    "hash": encode_hash,
    "bin": encode_bin,
    "addr": encode_addr,
    "int": encode_int,
    "trie_root": encode_root,
}


def print_func_call(ignore_first_arg=False, max_call_number=100):
    '''
    :param ignore_first_arg: whether print the first arg or not.
    useful when ignore the `self` parameter of an object method call
    '''
    from functools import wraps

    def display(x):
        x = str(x)
        try:
            x.decode('ascii')
        except:
            return 'NON_PRINTABLE'
        return x

    local = {'call_number': 0}

    def inner(f):

        @wraps(f)
        def wrapper(*args, **kwargs):
            local['call_number'] = local['call_number'] + 1
            tmp_args = args[1:] if ignore_first_arg and len(args) else args
            this_call_number = local['call_number']
            print('{0}#{1} args: {2}, {3}'.format(
                f.__name__,
                this_call_number,
                ', '.join([display(x) for x in tmp_args]),
                ', '.join(display(key) + '=' + str(value)
                          for key, value in kwargs.iteritems())
            ))
            res = f(*args, **kwargs)
            print('{0}#{1} return: {2}'.format(
                f.__name__,
                this_call_number,
                display(res)))

            if local['call_number'] > 100:
                raise Exception("Touch max call number!")
            return res
        return wrapper
    return inner


class DataDir(object):

    ethdirs = {
        "linux2": "~/.pyethereum",
        "darwin": "~/Library/Application Support/Pyethereum/",
        "win32": "~/AppData/Roaming/Pyethereum",
        "win64": "~/AppData/Roaming/Pyethereum",
    }

    def __init__(self):
        self._path = None

    def set(self, path):
        path = os.path.abspath(path)
        if not os.path.exists(path):
            os.makedirs(path)
        assert os.path.isdir(path)
        self._path = path

    def _set_default(self):
        p = self.ethdirs.get(sys.platform, self.ethdirs['linux2'])
        self.set(os.path.expanduser(os.path.normpath(p)))

    @property
    def path(self):
        if not self._path:
            self._set_default()
        return self._path

data_dir = DataDir()


def get_db_path():
    return os.path.join(data_dir.path, 'statedb')


def get_index_path():
    return os.path.join(data_dir.path, 'indexdb')


def db_put(key, value):
    database = db.DB(get_db_path())
    res = database.put(key, value)
    database.commit()
    return res


def db_get(key):
    database = db.DB(get_db_path())
    return database.get(key)


def configure_logging(loggerlevels=':DEBUG', verbosity=1):
    logconfig = dict(
        version=1,
        disable_existing_loggers=False,
        formatters=dict(
            debug=dict(
                format='[%(asctime)s] %(name)s %(levelname)s %(threadName)s:'
                ' %(message)s'
            ),
            minimal=dict(
                format='%(message)s'
            ),
        ),
        handlers=dict(
            default={
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'minimal'
            },
            verbose={
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'debug'
            },
        ),
        loggers=dict()
    )

    for loggerlevel in filter(lambda _: ':' in _, loggerlevels.split(',')):
        name, level = loggerlevel.split(':')
        logconfig['loggers'][name] = dict(
            handlers=['verbose'], level=level, propagate=False)

    if len(logconfig['loggers']) == 0:
        logconfig['loggers'][''] = dict(
            handlers=['default'],
            level={0: 'ERROR', 1: 'WARNING', 2: 'INFO', 3: 'DEBUG'}.get(
                verbosity),
            propagate=True)

    logging.config.dictConfig(logconfig)
    # logging.debug("logging set up like that: %r", logconfig)


class Denoms():
    def __init__(self):
        self.wei = 1
        self.babbage = 10**3
        self.lovelace = 10**6
        self.shannon = 10**9
        self.szabo = 10**12
        self.finney = 10**15
        self.ether = 10**18
        self.turing = 2**256

denoms = Denoms()

########NEW FILE########
__FILENAME__ = test_chain
import os
import pytest
import json
import tempfile
import pyethereum.processblock as processblock
import pyethereum.blocks as blocks
import pyethereum.transactions as transactions
import pyethereum.utils as utils
import pyethereum.rlp as rlp
import pyethereum.trie as trie
from pyethereum.db import DB as DB
from pyethereum.eth import create_default_config
import pyethereum.chainmanager as chainmanager

tempdir = tempfile.mktemp()


@pytest.fixture(scope="module")
def genesis_fixture():
    """
    Read genesis block from fixtures.
    """
    genesis_fixture = None
    with open('fixtures/genesishashestest.json', 'r') as f:
        genesis_fixture = json.load(f)
    assert genesis_fixture is not None, "Could not read genesishashtest.json from fixtures. Make sure you did 'git submodule init'!"
    # FIXME: assert that link is uptodate
    for k in ('genesis_rlp_hex', 'genesis_state_root', 'genesis_hash', 'initial_alloc'):
        assert k in genesis_fixture
    assert utils.sha3(genesis_fixture['genesis_rlp_hex'].decode('hex')).encode('hex') ==\
        genesis_fixture['genesis_hash']
    return genesis_fixture


@pytest.fixture(scope="module")
def accounts():
    k = utils.sha3('cow')
    v = utils.privtoaddr(k)
    k2 = utils.sha3('horse')
    v2 = utils.privtoaddr(k2)
    return k, v, k2, v2


@pytest.fixture(scope="module")
def mkgenesis(initial_alloc={}):
    return blocks.genesis(initial_alloc)


@pytest.fixture(scope="module")
def mkquickgenesis(initial_alloc={}):
    "set INITIAL_DIFFICULTY to a value that is quickly minable"
    return blocks.genesis(initial_alloc, difficulty=2 ** 16)


def mine_next_block(parent, uncles=[], coinbase=None, transactions=[]):
    # advance one block
    coinbase = coinbase or parent.coinbase
    m = chainmanager.Miner(parent, uncles=uncles, coinbase=coinbase)
    for tx in transactions:
        m.add_transaction(tx)
    blk = m.mine(steps=1000 ** 2)
    assert blk is not False, "Mining failed. Use mkquickgenesis!"
    return blk


@pytest.fixture(scope="module")
def get_transaction(gasprice=0, nonce=0):
    k, v, k2, v2 = accounts()
    tx = transactions.Transaction(
        nonce, gasprice, startgas=10000,
        to=v2, value=utils.denoms.finney * 10, data='').sign(k)
    return tx


@pytest.fixture(scope="module")
def get_chainmanager(genesis=None):
    cm = chainmanager.ChainManager()
    cm.configure(config=create_default_config(), genesis=genesis)
    return cm


def set_db(name=''):
    if name:
        utils.data_dir.set(os.path.join(tempdir, name))
    else:
        utils.data_dir.set(tempfile.mktemp())


set_db()


def db_store(blk):
    utils.db_put(blk.hash, blk.serialize())
    assert blocks.get_block(blk.hash) == blk


def test_db():
    set_db()
    db = DB(utils.get_db_path())
    a, b = DB(utils.get_db_path()),  DB(utils.get_db_path())
    assert a == b
    assert a.uncommitted == b.uncommitted
    a.put('a', 'b')
    b.get('a') == 'b'
    assert a.uncommitted == b.uncommitted
    a.commit()
    assert a.uncommitted == b.uncommitted
    assert 'test' not in db
    set_db()
    assert a != DB(utils.get_db_path())


def test_genesis():
    k, v, k2, v2 = accounts()
    set_db()
    blk = blocks.genesis({v: utils.denoms.ether * 1})
    sr = blk.state_root
    db = DB(utils.get_db_path())
    assert blk.state.db.db == db.db
    db.put(blk.hash, blk.serialize())
    blk.state.db.commit()
    assert sr in db
    db.commit()
    assert sr in db
    blk2 = blocks.genesis({v: utils.denoms.ether * 1})
    blk3 = blocks.genesis()
    assert blk == blk2
    assert blk != blk3
    set_db()
    blk2 = blocks.genesis({v: utils.denoms.ether * 1})
    blk3 = blocks.genesis()
    assert blk == blk2
    assert blk != blk3


def test_genesis_db():
    k, v, k2, v2 = accounts()
    set_db()
    blk = blocks.genesis({v: utils.denoms.ether * 1})
    db_store(blk)
    blk2 = blocks.genesis({v: utils.denoms.ether * 1})
    blk3 = blocks.genesis()
    assert blk == blk2
    assert blk != blk3
    set_db()
    blk2 = blocks.genesis({v: utils.denoms.ether * 1})
    blk3 = blocks.genesis()
    assert blk == blk2
    assert blk != blk3


def test_trie_state_root_nodep(genesis_fixture):
    def int_to_big_endian(integer):
        if integer == 0:
            return ''
        s = '%x' % integer
        if len(s) & 1:
            s = '0' + s
        return s.decode('hex')
    EMPTYSHA3 = utils.sha3('')
    assert EMPTYSHA3.encode('hex') == \
        'c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470'
    ZERO_ENC = int_to_big_endian(0)
    assert ZERO_ENC == ''
    state = trie.Trie(tempfile.mktemp())
    for address, value in genesis_fixture['initial_alloc'].items():
        acct = [
            int_to_big_endian(int(value)), ZERO_ENC, trie.BLANK_ROOT, EMPTYSHA3]
        state.update(address.decode('hex'), rlp.encode(acct))
    assert state.root_hash.encode(
        'hex') == genesis_fixture['genesis_state_root']


def test_genesis_state_root(genesis_fixture):
    # https://ethereum.etherpad.mozilla.org/12
    set_db()
    genesis = blocks.genesis()
    for k, v in blocks.GENESIS_INITIAL_ALLOC.items():
        assert genesis.get_balance(k) == v
    assert genesis.state_root.encode(
        'hex') == genesis_fixture['genesis_state_root']


def test_genesis_hash(genesis_fixture):
    set_db()
    genesis = blocks.genesis()
    """
    YP: https://raw.githubusercontent.com/ethereum/latexpaper/master/Paper.tex
    0256 , SHA3RLP(), 0160 , stateRoot, 0256 , 2**22 , 0, 0, 1000000, 0, 0, (),
    SHA3(42), (), ()

    Where 0256 refers to the parent and state and transaction root hashes,
    a 256-bit hash which is all zeroes;
    0160 refers to the coinbase address,
    a 160-bit hash which is all zeroes;
    2**22 refers to the difficulty;
    0 refers to the timestamp (the Unix epoch);
    () refers to the extradata and the sequences of both uncles and
    transactions, all empty.
    SHA3(42) refers to the SHA3 hash of a byte array of length one whose first
    and only byte is of value 42.
    SHA3RLP() values refer to the hashes of the transaction and uncle lists
    in RLP
    both empty.
    The proof-of-concept series include a development premine, making the state
    root hash some value stateRoot. The latest documentation should be
    consulted for the value of the state root.
    """

    h256 = '\00' * 32
    sr = genesis_fixture['genesis_state_root'].decode('hex')
    genesis_block_defaults = [
        ["prevhash", "bin", h256],  # h256()
        ["uncles_hash", "bin", utils.sha3(rlp.encode([]))],  # sha3EmptyList
        ["coinbase", "addr", "0" * 40],  # h160()
        ["state_root", "trie_root", sr],  # stateRoot
        ["tx_list_root", "trie_root", trie.BLANK_ROOT],  # h256()
        ["difficulty", "int", 2 ** 22],  # c_genesisDifficulty
        ["number", "int", 0],  # 0
        ["min_gas_price", "int", 0],  # 0
        ["gas_limit", "int", 10 ** 6],  # 10**6 for genesis
        ["gas_used", "int", 0],  # 0
        ["timestamp", "int", 0],  # 0
        ["extra_data", "bin", ""],  # ""
        ["nonce", "bin", utils.sha3(chr(42))],  # sha3(bytes(1, 42));
    ]

    cpp_genesis_block = rlp.decode(
        genesis_fixture['genesis_rlp_hex'].decode('hex'))
    cpp_genesis_header = cpp_genesis_block[0]

    for i, (name, typ, genesis_default) in enumerate(genesis_block_defaults):
        assert utils.decoders[typ](cpp_genesis_header[i]) == genesis_default
        assert getattr(genesis, name) == genesis_default

    assert genesis.hex_hash() == genesis_fixture['genesis_hash']

    assert genesis.hex_hash() == utils.sha3(
        genesis_fixture['genesis_rlp_hex'].decode('hex')
    ).encode('hex')


def test_mine_block():
    k, v, k2, v2 = accounts()
    set_db()
    blk = mkquickgenesis({v: utils.denoms.ether * 1})
    db_store(blk)
    blk2 = mine_next_block(blk, coinbase=v)
    db_store(blk2)
    assert blk2.get_balance(v) == blocks.BLOCK_REWARD + blk.get_balance(v)
    assert blk.state.db.db == blk2.state.db.db
    assert blk2.get_parent() == blk


def test_block_serialization_with_transaction():
    k, v, k2, v2 = accounts()
    # mine two blocks
    set_db()
    a_blk = mkquickgenesis({v: utils.denoms.ether * 1})
    db_store(a_blk)
    tx = get_transaction()
    a_blk2 = mine_next_block(a_blk, transactions=[tx])
    assert tx in a_blk2.get_transactions()


def test_block_serialization_with_transaction_empty_genesis():
    k, v, k2, v2 = accounts()
    set_db()
    a_blk = mkquickgenesis({})
    db_store(a_blk)
    tx = get_transaction(gasprice=10)  # must fail, as there is no balance
    a_blk2 = mine_next_block(a_blk, transactions=[tx])
    assert tx not in a_blk2.get_transactions()


def test_mine_block_with_transaction():
    k, v, k2, v2 = accounts()
    set_db()
    blk = mkquickgenesis({v: utils.denoms.ether * 1})
    db_store(blk)
    tx = get_transaction()
    blk2 = mine_next_block(blk, coinbase=v, transactions=[tx])
    assert tx in blk2.get_transactions()
    db_store(blk2)
    assert tx in blk2.get_transactions()
    assert blocks.get_block(blk2.hash) == blk2
    assert tx.gasprice == 0
    assert blk2.get_balance(
        v) == blocks.BLOCK_REWARD + blk.get_balance(v) - tx.value
    assert blk.state.db.db == blk2.state.db.db
    assert blk2.get_parent() == blk
    assert tx in blk2.get_transactions()
    assert tx not in blk.get_transactions()


def test_block_serialization_same_db():
    k, v, k2, v2 = accounts()
    set_db()
    blk = mkquickgenesis({v: utils.denoms.ether * 1})
    assert blk.hex_hash() == \
        blocks.Block.deserialize(blk.serialize()).hex_hash()
    db_store(blk)
    blk2 = mine_next_block(blk)
    assert blk.hex_hash() == \
        blocks.Block.deserialize(blk.serialize()).hex_hash()
    assert blk2.hex_hash() == \
        blocks.Block.deserialize(blk2.serialize()).hex_hash()


def test_block_serialization_other_db():
    k, v, k2, v2 = accounts()
    # mine two blocks
    set_db()
    a_blk = mkquickgenesis()
    db_store(a_blk)
    a_blk2 = mine_next_block(a_blk)
    db_store(a_blk2)

    # receive in other db
    set_db()
    b_blk = mkquickgenesis()
    assert b_blk == a_blk
    db_store(b_blk)
    b_blk2 = b_blk.deserialize(a_blk2.serialize())
    assert a_blk2.hex_hash() == b_blk2.hex_hash()
    db_store(b_blk2)
    assert a_blk2.hex_hash() == b_blk2.hex_hash()


def test_block_serialization_with_transaction_other_db():
    k, v, k2, v2 = accounts()
    # mine two blocks
    set_db()
    a_blk = mkquickgenesis({v: utils.denoms.ether * 1})
    db_store(a_blk)
    tx = get_transaction()
    a_blk2 = mine_next_block(a_blk, transactions=[tx])
    assert tx in a_blk2.get_transactions()
    db_store(a_blk2)
    assert tx in a_blk2.get_transactions()
    # receive in other db
    set_db()
    b_blk = mkquickgenesis({v: utils.denoms.ether * 1})
    assert b_blk == a_blk

    db_store(b_blk)
    b_blk2 = b_blk.deserialize(a_blk2.serialize())
    assert a_blk2.hex_hash() == b_blk2.hex_hash()

    assert tx in b_blk2.get_transactions()
    db_store(b_blk2)
    assert a_blk2.hex_hash() == b_blk2.hex_hash()
    assert tx in b_blk2.get_transactions()


def test_transaction():
    k, v, k2, v2 = accounts()
    set_db()
    blk = mkquickgenesis({v: utils.denoms.ether * 1})
    db_store(blk)
    blk = mine_next_block(blk)
    tx = get_transaction()
    assert tx not in blk.get_transactions()
    success, res = processblock.apply_tx(blk, tx)
    assert tx in blk.get_transactions()
    assert blk.get_balance(v) == utils.denoms.finney * 990
    assert blk.get_balance(v2) == utils.denoms.finney * 10


def test_transaction_serialization():
    k, v, k2, v2 = accounts()
    tx = get_transaction()
    assert tx in set([tx])
    assert tx.hex_hash() == \
        transactions.Transaction.deserialize(tx.serialize()).hex_hash()
    assert tx.hex_hash() == \
        transactions.Transaction.hex_deserialize(tx.hex_serialize()).hex_hash()
    assert tx in set([tx])


def test_mine_block_with_transaction():
    k, v, k2, v2 = accounts()
    set_db()
    blk = mkquickgenesis({v: utils.denoms.ether * 1})
    db_store(blk)
    tx = get_transaction()
    blk = mine_next_block(blk, transactions=[tx])
    assert tx in blk.get_transactions()
    assert blk.get_balance(v) == utils.denoms.finney * 990
    assert blk.get_balance(v2) == utils.denoms.finney * 10


def test_invalid_transaction():
    k, v, k2, v2 = accounts()
    set_db()
    blk = mkquickgenesis({v2: utils.denoms.ether * 1})
    db_store(blk)
    tx = get_transaction()
    blk = mine_next_block(blk, transactions=[tx])
    assert blk.get_balance(v) == 0
    assert blk.get_balance(v2) == utils.denoms.ether * 1
    # should invalid transaction be included in blocks?
    assert tx in blk.get_transactions()


def test_add_side_chain():
    """"
    Local: L0, L1, L2
    add
    Remote: R0, R1
    """
    k, v, k2, v2 = accounts()
    # Remote: mine one block
    set_db()
    R0 = mkquickgenesis({v: utils.denoms.ether * 1})
    db_store(R0)
    tx0 = get_transaction(nonce=0)
    R1 = mine_next_block(R0, transactions=[tx0])
    db_store(R1)
    assert tx0 in R1.get_transactions()

    # Local: mine two blocks
    set_db()
    L0 = mkquickgenesis({v: utils.denoms.ether * 1})
    cm = get_chainmanager(genesis=L0)
    tx0 = get_transaction(nonce=0)
    L1 = mine_next_block(L0, transactions=[tx0])
    cm.add_block(L1)
    tx1 = get_transaction(nonce=1)
    L2 = mine_next_block(L1, transactions=[tx1])
    cm.add_block(L2)

    # receive serialized remote blocks, newest first
    transient_blocks = [blocks.TransientBlock(R1.serialize()),
                        blocks.TransientBlock(R0.serialize())]
    cm.receive_chain(transient_blocks=transient_blocks)
    assert L2.hash in cm


def test_add_longer_side_chain():
    """"
    Local: L0, L1, L2
    Remote: R0, R1, R2, R3
    """
    k, v, k2, v2 = accounts()
    # Remote: mine one block
    set_db()
    blk = mkquickgenesis({v: utils.denoms.ether * 1})
    db_store(blk)
    remote_blocks = [blk]
    for i in range(3):
        tx = get_transaction(nonce=i)
        blk = mine_next_block(remote_blocks[-1], transactions=[tx])
        db_store(blk)
        remote_blocks.append(blk)
    # Local: mine two blocks
    set_db()
    L0 = mkquickgenesis({v: utils.denoms.ether * 1})
    cm = get_chainmanager(genesis=L0)
    tx0 = get_transaction(nonce=0)
    L1 = mine_next_block(L0, transactions=[tx0])
    cm.add_block(L1)
    tx1 = get_transaction(nonce=1)
    L2 = mine_next_block(L1, transactions=[tx1])
    cm.add_block(L2)

    # receive serialized remote blocks, newest first
    transient_blocks = [blocks.TransientBlock(b.serialize())
                        for b in reversed(remote_blocks)]
    cm.receive_chain(transient_blocks=transient_blocks)
    assert cm.head == remote_blocks[-1]


@pytest.mark.wip
def test_reward_unlces():
    """
    B0 B1 B2
    B0 Uncle

    We raise the block's coinbase account by Rb, the block reward,
    and the coinbase of each uncle by 7 of 8 that.
    """
    k, v, k2, v2 = accounts()
    set_db()
    blk0 = mkquickgenesis()
    local_coinbase = '1' * 40
    uncle_coinbase = '2' * 40
    cm = get_chainmanager(genesis=blk0)
    blk1 = mine_next_block(blk0, coinbase=local_coinbase)
    cm.add_block(blk1)
    assert blk1.get_balance(local_coinbase) == 1 * blocks.BLOCK_REWARD
    uncle = mine_next_block(blk0, coinbase=uncle_coinbase)
    cm.add_block(uncle)
    assert uncle.hash in cm
    assert cm.head.get_balance(local_coinbase) == 1 * blocks.BLOCK_REWARD
    assert cm.head.get_balance(uncle_coinbase) == 0
    # next block should reward uncles
    blk2 = mine_next_block(blk1, uncles=[uncle], coinbase=local_coinbase)
    cm.add_block(blk2)
    assert blk2.get_parent().prevhash == uncle.prevhash
    assert blk2 == cm.head
    assert cm.head.get_balance(local_coinbase) == 2 * blocks.BLOCK_REWARD
    assert cm.head.get_balance(uncle_coinbase) == blocks.UNCLE_REWARD
    assert 7 * blocks.BLOCK_REWARD / 8 == blocks.UNCLE_REWARD


# blocks 1-3 genereated with Ethereum (++) 0.5.9
# chain order w/ newest block first
cpp_rlp_blocks = ["f8b5f8b1a0cea7b6f4379812715562aaf0f44accf61ece5a2d80fe780d7e173fbbb1b146eaa01dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d49347941315bd599b73fd7b159e23dc75ddef80e7708feaa007e693fe94ea4772ab4c875af6bee3d58c0cab33981a0a336f4ae6cf514c1ee680833feffc038609184e72a000830f36d080845381ae3e80a00000000000000000000000000000000000000000000000000950e155eb5ed4cac0c0",
                  "f8b5f8b1a00c892995c469f57a34447217fc6cebbaf604c9d82d621a6505c7493ac1333e68a01dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d49347941315bd599b73fd7b159e23dc75ddef80e7708feaa0e785df309fbf0289aa9d1c09096c039aa69b880b6c001eb95ec838fb2dcebe5180833fe004028609184e72a000830f3a9f80845381ae3e80a0000000000000000000000000000000000000000000000000b985b7d378a23d84c0c0",
                  "f8b5f8b1a0c305511e7cb9b33767e50f5e94ecd7b1c51359a04f45183860ec6808d80b0d3fa01dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d49347941315bd599b73fd7b159e23dc75ddef80e7708feaa04b6da9af1b96757921ba3a0de69c615fea5482570e37a4d74d051e1e19f996c880833ff000018609184e72a000830f3e6f80845381adf680a00000000000000000000000000000000000000000000000003dfac8aa6e0214b4c0c0"]


def test_receive_cpp_block_1():
    set_db()
    cm = get_chainmanager()
    blk1 = blocks.TransientBlock(cpp_rlp_blocks[-1].decode('hex'))
    assert not blk1.transaction_list
    assert not blk1.uncles
    assert blk1.number == 1
    genesis = cm.head
    assert blk1.prevhash.encode('hex') == genesis.hex_hash()
    local_blk1 = genesis.deserialize_child(blk1.rlpdata)
    assert local_blk1.check_proof_of_work(local_blk1.nonce) == True


def test_receive_cpp_chain():
    set_db()
    cm = get_chainmanager()
    local_blk = cm.head  # genesis
    for i, rlp_block in enumerate(reversed(cpp_rlp_blocks)):
        blk = blocks.TransientBlock(rlp_block.decode('hex'))
        assert not blk.transaction_list
        assert not blk.uncles
        assert blk.number == i + 1
        local_blk = local_blk.deserialize_child(blk.rlpdata)
        assert local_blk.check_proof_of_work(local_blk.nonce) == True


@pytest.mark.wip
def test_deserialize_cpp_block_42():
    # 54.204.10.41 / NEthereum(++)/ZeroGox/v0.5.9/ncurses/Linux/g++ V:17L
    # E       TypeError: ord() expected a character, but string of length 0 found
    # 00bab55f2e230d4d56c7a2c11e7f3132663cc6734a5d4406f2e4359f4ab56593
    """
    RomanJ dumped the block
    BlockData [
  hash=00bab55f2e230d4d56c7a2c11e7f3132663cc6734a5d4406f2e4359f4ab56593
  parentHash=0df28c56b0cc32ceb55299934fca74ff63956ede0ffd430367ebcb1bb94d42fe
  unclesHash=1dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d49347
  coinbase=a70abb9ed4b5d82ed1d82194943349bcde036812
  stateHash=203838e6ea7b03bce4b806ab4e5c069d5cd98ca2ba27a2d343d809cc6365e1ce
  txTrieHash=78aaa0f3b726f8d9273ba145e0efd4a6b21183412582449cc9457f713422b5ae
  difficulty=4142bd
  number=48
  minGasPrice=10000000000000
  gasLimit=954162
  gasUsed=500
  timestamp=1400678342
  extraData=null
  nonce=0000000000000000000000000000000000000000000000007d117303138a74e0

TransactionData [ hash=9003d7211c4b0d123778707fbdcabd93a6184be210390de4f73f89eae847556d  nonce=null, gasPrice=09184e72a000, gas=01f4, receiveAddress=e559de5527492bcb42ec68d07df0742a98ec3f1e, value=8ac7230489e80000, data=null, signatureV=27, signatureR=18d646b8c4f7a804fdf7ba8da4d5dd049983e7d2b652ab902f7d4eaebee3e33b, signatureS=229ad485ef078d6e5f252db58dd2cce99e18af02028949896248aa01baf48b77]
]
    """

    hex_rlp_data = \
        """f9016df8d3a00df28c56b0cc32ceb55299934fca74ff63956ede0ffd430367ebcb1bb94d42fea01dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d4934794a70abb9ed4b5d82ed1d82194943349bcde036812a0203838e6ea7b03bce4b806ab4e5c069d5cd98ca2ba27a2d343d809cc6365e1cea078aaa0f3b726f8d9273ba145e0efd4a6b21183412582449cc9457f713422b5ae834142bd308609184e72a000830e8f328201f484537ca7c680a00000000000000000000000000000000000000000000000007d117303138a74e0f895f893f86d808609184e72a0008201f494e559de5527492bcb42ec68d07df0742a98ec3f1e888ac7230489e80000801ba018d646b8c4f7a804fdf7ba8da4d5dd049983e7d2b652ab902f7d4eaebee3e33ba0229ad485ef078d6e5f252db58dd2cce99e18af02028949896248aa01baf48b77a06e957f0f99502ad60a66a016f72957eff0f3a5bf791ad4a0606a44f35a6e09288201f4c0"""
    header_args, transaction_list, uncles = rlp.decode(
        hex_rlp_data.decode('hex'))
    for tx_serialized, _state_root, _gas_used_encoded in transaction_list:
        tx = transactions.Transaction.create(tx_serialized)


# TODO ##########################################
#
# test for remote block with invalid transaction
# test for multiple transactions from same address received
#    in arbitrary order mined in the same block

########NEW FILE########
__FILENAME__ = test_contracts
import pytest
import serpent
import pyethereum.processblock as pb
import pyethereum.blocks as b
import pyethereum.transactions as t
import pyethereum.utils as u


gasprice = 0
startgas = 10000


@pytest.fixture(scope="module")
def accounts():
    k = u.sha3('cow')
    v = u.privtoaddr(k)
    k2 = u.sha3('horse')
    v2 = u.privtoaddr(k2)
    return k, v, k2, v2


def test_namecoin():
    k, v, k2, v2 = accounts()

    blk = b.genesis({v: u.denoms.ether * 1})

    # tx1
    scode1 = '''
if !contract.storage[msg.data[0]]:
    contract.storage[msg.data[0]] = msg.data[1]
    return(1)
else:
    return(0)
    '''
    code1 = serpent.compile(scode1)
    tx1 = t.contract(0, gasprice, startgas, 0, code1).sign(k)
    s, addr = pb.apply_tx(blk, tx1)

    snapshot = blk.snapshot()

    # tx2
    tx2 = t.Transaction(1, gasprice, startgas, addr, 0,
                        serpent.encode_datalist(['george', 45]))
    tx2.sign(k)
    s, o = pb.apply_tx(blk, tx2)
    assert serpent.decode_datalist(o) == [1]

    # tx3
    tx3 = t.Transaction(2, gasprice, startgas, addr, 0,
                        serpent.encode_datalist(['george', 20])).sign(k)
    s, o = pb.apply_tx(blk, tx3)
    assert serpent.decode_datalist(o) == [0]

    # tx4
    tx4 = t.Transaction(3, gasprice, startgas, addr, 0,
                        serpent.encode_datalist(['harry', 60])).sign(k)
    s, o = pb.apply_tx(blk, tx4)
    assert serpent.decode_datalist(o) == [1]

    blk.revert(snapshot)

    assert blk.to_dict()
    assert blk.to_dict()['state'][addr]['code']


def test_currency():
    k, v, k2, v2 = accounts()
    scode2 = '''
if !contract.storage[1000]:
    contract.storage[1000] = 1
    contract.storage[0x%s] = 1000
    return(1)
elif msg.datasize == 1:
    addr = msg.data[0]
    return(contract.storage[addr])
else:
    from = msg.sender
    fromvalue = contract.storage[from]
    to = msg.data[0]
    value = msg.data[1]
    if fromvalue >= value:
        contract.storage[from] = fromvalue - value
        contract.storage[to] = contract.storage[to] + value
        return(1)
    else:
        return(0)
    ''' % v
    code2 = serpent.compile(scode2)
    blk = b.genesis({v: 10 ** 18})
    tx4 = t.contract(0, gasprice, startgas, 0, code2).sign(k)
    s, addr = pb.apply_tx(blk, tx4)
    tx5 = t.Transaction(1, gasprice, startgas, addr, 0, '').sign(k)
    s, o = pb.apply_tx(blk, tx5)
    assert serpent.decode_datalist(o) == [1]
    tx6 = t.Transaction(2, gasprice, startgas, addr, 0,
                        serpent.encode_datalist([v2, 200])).sign(k)
    s, o = pb.apply_tx(blk, tx6)
    assert serpent.decode_datalist(o) == [1]
    tx7 = t.Transaction(3, gasprice, startgas, addr, 0,
                        serpent.encode_datalist([v2, 900])).sign(k)
    s, o = pb.apply_tx(blk, tx7)
    assert serpent.decode_datalist(o) == [0]
    tx8 = t.Transaction(4, gasprice, startgas, addr, 0,
                        serpent.encode_datalist([v])).sign(k)
    s, o = pb.apply_tx(blk, tx8)
    assert serpent.decode_datalist(o) == [800]
    tx9 = t.Transaction(5, gasprice, startgas, addr, 0,
                        serpent.encode_datalist([v2])).sign(k)
    s, o = pb.apply_tx(blk, tx9)
    assert serpent.decode_datalist(o) == [200]


def test_data_feeds():
    k, v, k2, v2 = accounts()
    scode3 = '''
if !contract.storage[1000]:
    contract.storage[1000] = 1
    contract.storage[1001] = msg.sender
    return(0)
elif msg.sender == contract.storage[1001] and msg.datasize == 2:
    contract.storage[msg.data[0]] = msg.data[1]
    return(1)
else:
    return(contract.storage[msg.data[0]])
'''
    code3 = serpent.compile(scode3)
    # print("AST", serpent.rewrite(serpent.parse(scode3)))
    # print("Assembly", serpent.compile_to_assembly(scode3))
    blk = b.genesis({v: 10 ** 18, v2: 10 ** 18})
    tx10 = t.contract(0, gasprice, startgas, 0, code3).sign(k)
    s, addr = pb.apply_tx(blk, tx10)
    tx11 = t.Transaction(1, gasprice, startgas, addr, 0, '').sign(k)
    s, o = pb.apply_tx(blk, tx11)
    tx12 = t.Transaction(2, gasprice, startgas, addr, 0,
                         serpent.encode_datalist([500])).sign(k)
    s, o = pb.apply_tx(blk, tx12)
    assert serpent.decode_datalist(o) == [0]
    tx13 = t.Transaction(3, gasprice, startgas, addr, 0,
                         serpent.encode_datalist([500, 726])).sign(k)
    s, o = pb.apply_tx(blk, tx13)
    assert serpent.decode_datalist(o) == [1]
    tx14 = t.Transaction(4, gasprice, startgas, addr, 0,
                         serpent.encode_datalist([500])).sign(k)
    s, o = pb.apply_tx(blk, tx14)
    assert serpent.decode_datalist(o) == [726]
    return blk, addr


def test_hedge():
    k, v, k2, v2 = accounts()
    blk, addr = test_data_feeds()
    scode4 = '''
if !contract.storage[1000]:
    contract.storage[1000] = msg.sender
    contract.storage[1002] = msg.value
    contract.storage[1003] = msg.data[0]
    return(1)
elif !contract.storage[1001]:
    ethvalue = contract.storage[1002]
    if msg.value >= ethvalue:
        contract.storage[1001] = msg.sender
    othervalue = ethvalue * call(0x%s,[contract.storage[1003]],1)
    contract.storage[1004] = othervalue
    contract.storage[1005] = block.timestamp + 86400
    return([2,othervalue],2)
else:
    othervalue = contract.storage[1004]
    ethvalue = othervalue / call(0x%s,contract.storage[1003])
    if ethvalue >= contract.balance:
        send(contract.storage[1000],contract.balance)
        return(3)
    elif block.timestamp > contract.storage[1005]:
        send(contract.storage[1001],contract.balance - ethvalue)
        send(contract.storage[1000],ethvalue)
        return(4)
    else:
        return(5)
''' % (addr, addr)
    code4 = serpent.compile(scode4)
    # print("AST", serpent.rewrite(serpent.parse(scode4)))
    # print("Assembly", serpent.compile_to_assembly(scode4))
    # important: no new genesis block
    tx15 = t.contract(5, gasprice, startgas, 0, code4).sign(k)
    s, addr2 = pb.apply_tx(blk, tx15)
    tx16 = t.Transaction(6, gasprice, startgas, addr2, 10 ** 17,
                         serpent.encode_datalist([500])).sign(k)
    s, o = pb.apply_tx(blk, tx16)
    assert serpent.decode_datalist(o) == [1]
    tx17 = t.Transaction(0, gasprice, startgas, addr2, 10 ** 17,
                         serpent.encode_datalist([500])).sign(k2)
    s, o = pb.apply_tx(blk, tx17)
    assert serpent.decode_datalist(o) == [2, 72600000000000000000L]
    snapshot = blk.snapshot()
    tx18 = t.Transaction(7, gasprice, startgas, addr2, 0, '').sign(k)
    s, o = pb.apply_tx(blk, tx18)
    assert serpent.decode_datalist(o) == [5]
    tx19 = t.Transaction(8, gasprice, startgas, addr, 0,
                         serpent.encode_datalist([500, 300])).sign(k)
    s, o = pb.apply_tx(blk, tx19)
    assert serpent.decode_datalist(o) == [1]
    tx20 = t.Transaction(9, gasprice, startgas, addr2, 0, '').sign(k)
    s, o = pb.apply_tx(blk, tx20)
    assert serpent.decode_datalist(o) == [3]
    blk.revert(snapshot)
    blk.timestamp += 200000
    tx21 = t.Transaction(7, gasprice, startgas, addr, 0,
                         serpent.encode_datalist([500, 1452])).sign(k)
    s, o = pb.apply_tx(blk, tx21)
    assert serpent.decode_datalist(o) == [1]
    tx22 = t.Transaction(8, gasprice, 2000, addr2, 0, '').sign(k)
    s, o = pb.apply_tx(blk, tx22)
    assert serpent.decode_datalist(o) == [4]

########NEW FILE########
__FILENAME__ = test_indexdb
import sys
import os
import pytest
import tempfile
import pyethereum.indexdb
import pyethereum.utils
import pyethereum.db

tempdir = tempfile.mktemp()


def act(num):
    return pyethereum.utils.sha3(str(num)).encode('hex')[:40]


def mktx(a, b):
    return 'tx(%d,%d)' % (a, b)


@pytest.fixture(scope="module")
def mkindex():
    idx = pyethereum.indexdb.AccountTxIndex()
    idx.db = pyethereum.db.DB(tempfile.mktemp())
    return idx


def test_appending():
    idx = pyethereum.indexdb.Index('namespace')
    key = 'key'
    vals = ['v0', 'v1']
    for v in vals:
        idx.append(key, v)
    assert idx.num_values(key) == 2
    assert list(idx.get(key)) == vals


def test_adding():
    acct = act(10000)
    acct2 = act(10000)
    tx0 = mktx(0, 0)
    tx1 = mktx(0, 1)
    tx2 = mktx(0, 2)
    tx3 = mktx(0, 3)

    idx = mkindex()

    idx.add_transaction(acct, 0, tx0)
    idx.db.commit()
    txs = list(idx.get_transactions(acct, offset=0))
    assert txs == [tx0]

    idx.add_transaction(acct2, 0, tx0)
    idx.db.commit()
    txs = list(idx.get_transactions(acct2, offset=0))
    assert txs == [tx0]

    idx.add_transaction(acct, 1, tx1)
    idx.db.commit()
    txs = list(idx.get_transactions(acct, offset=0))
    assert txs == [tx0, tx1]

    idx.add_transaction(acct, 2, tx2)
    idx.db.commit()
    txs = list(idx.get_transactions(acct, offset=0))
    assert txs == [tx0, tx1, tx2]

    idx.add_transaction(acct, 3, tx3)
    idx.db.commit()
    txs = list(idx.get_transactions(acct, offset=0))
    assert txs == [tx0, tx1, tx2, tx3]

    txs = list(idx.get_transactions(acct, offset=2))
    assert txs == [tx2, tx3]

    # delete transaction
    for keep in reversed(range(4)):
        idx.delete_transactions(acct, offset=keep)
        idx.db.commit()
        txs = list(idx.get_transactions(acct, offset=0))
        assert txs == [tx0, tx1, tx2, tx3][:keep]


def test_multiple_accounts():
    idx = mkindex()

    NUM_ACCOUNTS = 20

    for i in range(NUM_ACCOUNTS)[1:]:
        acct = act(i)
        for j in range(i * 5):
            idx.add_transaction(acct, j, mktx(i, j))
        idx.db.commit()
        txs = list(idx.get_transactions(acct, offset=0))
        assert len(txs) == j + 1
        for j in range(i * 5):
            tx = mktx(i, j)
            assert tx == txs[j]
        for j in range(i * 5):
            tx = mktx(i, j)
            txs = list(idx.get_transactions(acct, offset=j))
            assert tx == txs[0]

    assert len(
        set(list(idx.get_accounts(account_from='')))) == NUM_ACCOUNTS - 1


def test_num_transactions():
    idx = mkindex()
    acct = act(4200000)
    assert idx.num_transactions(acct) == 0

    for j in range(50):
        idx.add_transaction(acct, j, mktx(j, j))
        assert idx.num_transactions(acct) == j + 1

    idx.delete_transactions(acct, offset=5)
    assert idx.num_transactions(acct) == 5

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# pyethereum is free software: you can redistribute it and/or modify it
# under the terms of the The MIT License


"""Utilities used by more than one test."""


import json
import os


__TESTDATADIR = "../tests"


def load_test_data(fname):
    return json.loads(open(os.path.join(__TESTDATADIR, fname)).read())

########NEW FILE########
__FILENAME__ = fixture_to_example
#!/usr/bin/env python


def fixture_to_tables(fixture):
    ''' convert fixture into *behave* examples
    :param fixture: a dictionary in the following form::

        {
            "test1name":
            {
                "test1property1": ...,
                "test1property2": ...,
                ...
            },
            "test2name":
            {
                "test2property1": ...,
                "test2property2": ...,
                ...
            }
        }

    :return: a list, with each item represent a table: `(caption, rows)`,
    each item in `rows` is `(col1, col2,...)`
    '''

    tables = []
    for (title, content) in fixture.iteritems():
        rows = []

        # header(keyword) row
        keys = content.keys()
        keys.sort()
        rows.append(tuple(keys))

        # item(value) row
        row1 = []
        for col in rows[0]:
            row1.append(content[col])
        rows.append(tuple(row1))

        tables.append((title, tuple(rows)))
    return tables


def format_item(item, py=True):
    '''
    :param py: python format or not
    '''
    # for non python format, just output itself.
    # so the result is `something` instead of `"something"`
    if not py:
        return unicode(item)

    if isinstance(item, (str, unicode)):
        # long int is prefixed by a #
        if item.startswith('#'):
            return unicode(long(item[1:]))
        return u'"{0}"'.format(item)

    return unicode(item)


def format_to_example(table, tabspace=2, indent=2):
    ''' format table to *behave* example
    :param table: `(caption, rows)`, each item in `rows` is `(col1, col2,...)`
    :return
    '''
    from io import StringIO
    output = StringIO()

    caption, rows = table

    # output caption line
    output.write(u'{0}Examples: {1}\n'.format(' ' * indent * tabspace,
                                              caption))

    # calculate max length for each column, for aligning
    cols = zip(*rows)
    col_lengths = []
    for col in cols:
        max_length = max([len(format_item(row)) for row in col])
        col_lengths.append(max_length)

    # output each row
    for r, row in enumerate(rows):
        output.write(u' ' * (indent + 1) * tabspace)
        output.write(u'|')
        for c in range(len(col_lengths)):
            output.write(u' ')
            output.write(format_item(row[c], r))
            output.write(u' ' * (col_lengths[c] - len(format_item(row[c], r))))
            output.write(u' |')
        output.write(u'\n')

    example = output.getvalue()
    output.close()
    return example


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print('Please give the json fixture file path')

    f = sys.argv[1]
    fixture = json.load(file(f))
    tables = fixture_to_tables(fixture)
    for table in tables:
        print(format_to_example(table))

########NEW FILE########
__FILENAME__ = pyethtool_cli
#!/usr/bin/env python
import sys
import re
import json
from pyethereum import pyethtool
import shlex

def smart_print(o):
    if isinstance(o, (list, dict)):
        try:
            print json.dumps(o)
        except:
            print o
    else:
        print o

def main():
    if len(sys.argv) == 1:
        # Shell
        while 1:
            cmdline = raw_input('> ')
            if cmdline in ['quit','exit']:
                break
            tokens = shlex.split(cmdline)
            cmd, args = tokens[0], tokens[1:]
            o = getattr(pyethtool, cmd)(*args)
            smart_print(o)

    else:
        cmd = sys.argv[2] if sys.argv[1][0] == '-' else sys.argv[1]
        if sys.argv[1] == '-s':
            args = re.findall(r'\S\S*', sys.stdin.read()) + sys.argv[3:]
        elif sys.argv[1] == '-B':
            args = [sys.stdin.read()] + sys.argv[3:]
        elif sys.argv[1] == '-b':
            args = [sys.stdin.read()[:-1]] + sys.argv[3:]  # remove trailing \n
        elif sys.argv[1] == '-j':
            args = [json.loads(sys.stdin.read())] + sys.argv[3:]
        elif sys.argv[1] == '-J':
            args = json.loads(sys.stdin.read()) + sys.argv[3:]
        else:
            cmd = sys.argv[1]
            args = sys.argv[2:]
        o = getattr(pyethtool, cmd)(*args)
        smart_print(o)



if __name__ == '__main__':
    main()

########NEW FILE########
