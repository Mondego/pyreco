__FILENAME__ = build
#!/usr/bin/env python

import sys

import os
import os.path

from cx_Freeze import setup, Executable

base = None
# if sys.platform == "win32":
#    base = "Win32GUI"

def ls(path):
    for name in os.listdir(path):
        yield os.path.join(path, name)

import itertools

build_exe_options = {
    "include_files": list(itertools.chain(ls('ui/forms'), ls('ui/icons')))
}

setup(
    name='ngcccbase',
    version='0.0.6',
    description='A flexible and modular base for colored coin software.',
    classifiers=[
        "Programming Language :: Python",
    ],
    url='https://github.com/bitcoinx/ngcccbase',
    keywords='bitcoinx bitcoin coloredcoins',
    packages=["ngcccbase", "ngcccbase.services", "ngcccbase.p2ptrade", "ecdsa", "coloredcoinlib", "ui"],
    options = {"build_exe": build_exe_options},
    executables = [
        Executable("ngccc-gui.py", base=base, targetName="chromawallet"),
        Executable("ngccc-cli.py", base=base, targetName="cw-cli"),
    ]
)

########NEW FILE########
__FILENAME__ = chromanode
#!/usr/bin/env python
import os, sys
import json
import hashlib
import threading, time

import web

from coloredcoinlib import BlockchainState, ColorDefinition


urls = (
    '/tx', 'Tx',
    '/publish_tx', 'PublishTx',
    '/tx_blockhash', 'TxBlockhash',
    '/prefetch', 'Prefetch',
    '/blockcount', 'BlockCount',
    '/header', 'Header',
    '/chunk', 'Chunk',
    '/merkle', 'Merkle'
)

testnet = False
if (len(sys.argv) > 2) and (sys.argv[2] == 'testnet'):
    testnet = True

HEADERS_FILE = 'headers.testnet' if testnet else 'headers.mainnet'
if (len(sys.argv) > 3):
    HEADERS_FILE = sys.argv[3]

blockchainstate = BlockchainState.from_url(None, testnet)

my_lock = threading.RLock()
def call_synchronized(f):
    def newFunction(*args, **kw):
        with my_lock:
            return f(*args, **kw)
    return newFunction

blockchainstate.bitcoind._call = call_synchronized(
    blockchainstate.bitcoind._call)
blockchainstate.bitcoind._batch = call_synchronized(
    blockchainstate.bitcoind._batch)

class ErrorThrowingRequestProcessor:
    def require(self, data, key, message):
        value = data.get(key, None)
        if value is None:
            raise web.HTTPError("400 Bad request", 
                                {"content-type": "text/plain"},
                                message)


class Tx(ErrorThrowingRequestProcessor):
    def POST(self):
        # data is sent in as json
        data = json.loads(web.data())
        self.require(data, 'txhash', "TX requires txhash")
        txhash = data.get('txhash')
        print txhash
        return blockchainstate.get_raw(txhash)


class PublishTx(ErrorThrowingRequestProcessor):
    def POST(self):
        txdata = web.data()
        reply = None
        try:
            reply = blockchainstate.bitcoind.sendrawtransaction(txdata)
        except Exception as e:
            reply = ("Error: " + str(e))
        return reply


class TxBlockhash(ErrorThrowingRequestProcessor):
    def POST(self):
        # data is sent in as json
        data = json.loads(web.data())
        self.require(data, 'txhash', "TX requires txhash")
        txhash = data.get('txhash')
        print txhash
        blockhash, in_mempool = blockchainstate.get_tx_blockhash(txhash)
        return json.dumps([blockhash, in_mempool])


class Prefetch(ErrorThrowingRequestProcessor):
    def POST(self):
        # data is sent in as json
        data = json.loads(web.data())
        self.require(data, 'txhash', "Prefetch requires txhash")
        self.require(data, 'output_set', "Prefetch requires output_set")
        self.require(data, 'color_desc', "Prefetch requires color_desc")
        txhash = data.get('txhash')
        output_set = data.get('output_set')
        color_desc = data.get('color_desc')
        limit = data.get('limit')

        # note the id doesn't actually matter we need to add it so
        #  we have a valid color definition
        color_def = ColorDefinition.from_color_desc(9999, color_desc)

        # gather all the transactions and return them
        tx_lookup = {}

        def process(current_txhash, current_outindex):
            """For any tx out, process the colorvalues of the affecting
            inputs first and then scan that tx.
            """
            if limit and len(tx_lookup) > limit:
                return
            if tx_lookup.get(current_txhash):
                return
            current_tx = blockchainstate.get_tx(current_txhash)
            if not current_tx:
                return
            tx_lookup[current_txhash] = blockchainstate.get_raw(current_txhash)

            # note a genesis tx will simply have 0 affecting inputs
            inputs = set()
            inputs = inputs.union(
                color_def.get_affecting_inputs(current_tx,
                                               [current_outindex]))
            for i in inputs:
                process(i.prevout.hash, i.prevout.n)

        for oi in output_set:
            process(txhash, oi)
        return tx_lookup


class BlockCount(ErrorThrowingRequestProcessor):
    def GET(self):
        return str(blockchainstate.get_block_count())


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        import decimal
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


class Header(ErrorThrowingRequestProcessor):
    def POST(self):
        data = json.loads(web.data())
        block_hash = data.get('block_hash')
        if not block_hash:
            self.require(data, 'height', "block_hash or height required")
            height = data.get('height')
            block_hash = blockchainstate.get_block_hash(height)
        block = blockchainstate.get_block(block_hash)
        return json.dumps({
            'block_height':    block['height'],
            'version':         block['version'],
            'prev_block_hash': block['previousblockhash'],
            'merkle_root':     block['merkleroot'],
            'timestamp':       block['time'],
            'bits':            int(block['bits'], 16),
            'nonce':           block['nonce'],
        }, cls=DecimalEncoder)


class ChunkThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.running = False
        self.lock = threading.Lock()
        self.blockchainstate = BlockchainState.from_url(None, testnet)
        self.headers = ''

    def is_running(self):
        with self.lock:
            return self.running

    def stop(self):
        with self.lock:
            self.running = False

    def run(self):
        self.headers = open(HEADERS_FILE, 'ab+').read()

        with self.lock:
            self.running = True

        run_time = time.time()
        while self.is_running():
            if run_time > time.time():
                time.sleep(0.05)
                continue
            run_time = time.time() + 1

            height = self.blockchainstate.get_block_count()
            if height == self.height:
                continue
            if height < self.height:
                self.headers = self.headers[:height*80]
            while height > self.height:
                if not self.is_running():
                    break
                block_height = self.height + 1
                blockhash = self.blockchainstate.get_block_hash(block_height)
                block = self.blockchainstate.get_block(blockhash)

                if block_height == 0:
                    self.headers = self._header_to_string(block)
                else:
                    prev_hash = self._hash_header(self.headers[-80:])
                    if prev_hash == block['previousblockhash']:
                        self.headers += self._header_to_string(block)
                    else:
                        self.headers = self.headers[:-80]
            open(HEADERS_FILE, 'wb').write(self.headers)

    @property
    def height(self):
        return len(self.headers)/80 - 1

    def _rev_hex(self, s):
        return s.decode('hex')[::-1].encode('hex')

    def _int_to_hex(self, i, length=1):
        s = hex(i)[2:].rstrip('L')
        s = "0"*(2*length - len(s)) + s
        return self._rev_hex(s)

    def _header_to_string(self, h):
        s = self._int_to_hex(h.get('version'),4) \
            + self._rev_hex(h.get('previousblockhash', "0"*64)) \
            + self._rev_hex(h.get('merkleroot')) \
            + self._int_to_hex(h.get('time'),4) \
            + self._rev_hex(h.get('bits')) \
            + self._int_to_hex(h.get('nonce'),4)
        return s.decode('hex')

    def _hash_header(self, raw_header):
        return hashlib.sha256(hashlib.sha256(raw_header).digest()).digest()[::-1].encode('hex_codec')

chunkThread = ChunkThread()


class Chunk(ErrorThrowingRequestProcessor):
    def POST(self):
        data = json.loads(web.data())
        self.require(data, 'index', "Chunk requires index")
        index = data.get('index')
        with open(HEADERS_FILE, 'rb') as headers:
            headers.seek(index*2016*80)
            return headers.read(2016*80)


class Merkle(ErrorThrowingRequestProcessor):
    def POST(self):
        data = json.loads(web.data())
        self.require(data, 'txhash', "Merkle requires txhash")
        self.require(data, 'blockhash', "Merkle requires blockhash")
        txhash = data.get('txhash')
        blockhash = data.get('blockhash')

        hash_decode = lambda x: x.decode('hex')[::-1]
        hash_encode = lambda x: x[::-1].encode('hex')
        Hash = lambda x: hashlib.sha256(hashlib.sha256(x).digest()).digest()

        b = blockchainstate.get_block(blockhash)
        tx_list = b.get('tx')
        tx_pos = tx_list.index(txhash)

        merkle = map(hash_decode, tx_list)
        target_hash = hash_decode(txhash)
        s = []
        while len(merkle) != 1:
            if len(merkle) % 2:
                merkle.append(merkle[-1])
            n = []
            while merkle:
                new_hash = Hash(merkle[0] + merkle[1])
                if merkle[0] == target_hash:
                    s.append(hash_encode(merkle[1]))
                    target_hash = new_hash
                elif merkle[1] == target_hash:
                    s.append(hash_encode(merkle[0]))
                    target_hash = new_hash
                n.append(new_hash)
                merkle = merkle[2:]
            merkle = n

        return json.dumps({"block_height": b.get('height'), "merkle": s, "pos": tx_pos})


if __name__ == "__main__":
    import signal
    def sigint_handler(signum, frame):
        print ('exit chunk thread')
        chunkThread.stop()
        print ('done')
        sys.exit(1)
    signal.signal(signal.SIGINT, sigint_handler)

    chunkThread.start()

    app = web.application(urls, globals())
    app.run()

########NEW FILE########
__FILENAME__ = blockchain
"""
Data structures to model bitcoin blockchain objects.
"""

import bitcoin.core
import bitcoin.core.serialize
import bitcoin.rpc

from toposort import toposorted


def script_to_raw_address(script):
    # extract the destination address from the scriptPubkey
    if script[:3] == "\x76\xa9\x14":
        return script[3:23]
    else:
        return None


class COutpoint(object):
    def __init__(self, hash, n):
        self.hash = hash
        self.n = n


class CTxIn(object):
    def __init__(self, op_hash, op_n):
        self.prevout = COutpoint(op_hash, op_n)
        self.nSequence = None

    def get_txhash(self):
        if self.prevout.hash == 'coinbase':
            return self.prevout.hash
        else:
            return self.prevout.hash.decode('hex')[::-1]

    def get_outpoint(self):
        return (self.prevout.hash, self.prevout.n)

    def set_nSequence(self, nSequence):
        self.nSequence = nSequence


class CTxOut(object):
    def __init__(self, value, script):
        self.value = value
        self.script = script
        self.raw_address = script_to_raw_address(script)


class CTransaction(object):

    def __init__(self, bs):
        self.bs = bs
        self.have_input_values = False

    @classmethod
    def from_bitcoincore(klass, txhash, bctx, bs):
        tx = CTransaction(bs)

        tx.raw = bctx
        tx.hash = txhash
        tx.inputs = []
        for i in bctx.vin:
            if i.prevout.is_null():
                tx.inputs.append(CTxIn('coinbase', 0))
            else:
                op = i.prevout
                tx.inputs.append(CTxIn(bitcoin.core.b2lx(op.hash),
                                       op.n))
        tx.outputs = []
        for o in bctx.vout:
            tx.outputs.append(CTxOut(o.nValue, o.scriptPubKey))
        return tx

    def ensure_input_values(self):
        if self.have_input_values:
            return
        for inp in self.inputs:
            prev_tx_hash = inp.prevout.hash
            if prev_tx_hash != 'coinbase':
                prevtx = self.bs.get_tx(prev_tx_hash)
                inp.prevtx = prevtx
                inp.value = prevtx.outputs[inp.prevout.n].value
            else:
                inp.value = 0  # TODO: value of coinbase tx?
        self.have_input_values = True


class BlockchainStateBase(object):
    def sort_txs(self, tx_list):
        block_txs = {h:self.get_tx(h) for h in tx_list}

        def get_dependent_txs(tx):
            """all transactions from current block this transaction
            directly depends on"""
            dependent_txs = []
            for inp in tx.inputs:
                if inp.prevout.hash in block_txs:
                    dependent_txs.append(block_txs[inp.prevout.hash])
            return dependent_txs

        return toposorted(block_txs.values(), get_dependent_txs)


class BlockchainState(BlockchainStateBase):
    """ Represents a blockchain state, using bitcoin-RPC to
    obtain information of transactions, addresses, and blocks. """
    def __init__(self, bitcoind):
        self.bitcoind = bitcoind

    def publish_tx(self, txdata):
        return self.bitcoind.sendrawtransaction(txdata)

    @classmethod
    def from_url(cls, url, testnet=False):
        if testnet:
            bitcoind = bitcoin.rpc.RawProxy(
                service_url=url, service_port=18332)
        else:
            bitcoind = bitcoin.rpc.RawProxy(  # pragma: no cover
                service_url=url)              # pragma: no cover
        return cls(bitcoind)

    def get_block_height(self, blockhash):
        block = self.bitcoind.getblock(blockhash)
        return block['height']

    def get_block_count(self):
        return self.bitcoind.getblockcount()

    def get_block_hash(self, index):
        return self.bitcoind.getblockhash(index)

    def get_block(self, blockhash):
        return self.bitcoind.getblock(blockhash)

    def get_blockhash_at_height(self, height):
        return self.bitcoind.getblockhash(height)

    def get_previous_blockinfo(self, blockhash):
        block_data = self.bitcoind.getblock(blockhash)
        return block_data['previousblockhash'], block_data['height']

    def get_tx_blockhash(self, txhash):
        try:
            raw = self.bitcoind.getrawtransaction(txhash, 1)
        except Exception, e:
            # print txhash, e
            return None, False
        return raw.get('blockhash', None), True

    def get_raw(self, txhash):
        return self.bitcoind.getrawtransaction(txhash, 0)

    def get_tx(self, txhash):
        txhex = self.bitcoind.getrawtransaction(txhash, 0)
        txbin = bitcoin.core.x(txhex)
        tx = bitcoin.core.CTransaction.deserialize(txbin)
        return CTransaction.from_bitcoincore(txhash, tx, self)

    def get_best_blockhash(self):
        try:
            return self.bitcoin.getbestblockhash()
        except:
            # warning: not atomic!
            # remove once bitcoin 0.9 becomes commonplace
            count = self.bitcoind.getblockcount()
            return self.bitcoind.getblockhash(count)

    def iter_block_txs(self, blockhash):
        block_hex = None
        try:
            block_hex = self.bitcoind.getblock(blockhash, False)
        except bitcoin.rpc.JSONRPCException:
            pass

        if block_hex:
            # block at once
            block = bitcoin.core.CBlock.deserialize(bitcoin.core.x(block_hex))
            block_hex = None
            for tx in block.vtx:
                txhash = bitcoin.core.b2lx(
                    bitcoin.core.serialize.Hash(tx.serialize()))
                yield CTransaction.from_bitcoincore(txhash, tx, self)
        else:
            txhashes = self.bitcoind.getblock(blockhash)['tx']
            for txhash in txhashes:
                yield self.get_tx(txhash)

    def sort_txs(self, tx_list):
        block_txs = {h:self.get_tx(h) for h in tx_list}

        def get_dependent_txs(tx):
            """all transactions from current block this transaction
            directly depends on"""
            dependent_txs = []
            for inp in tx.inputs:
                if inp.prevout.hash in block_txs:
                    dependent_txs.append(block_txs[inp.prevout.hash])
            return dependent_txs

        return toposorted(block_txs.values(), get_dependent_txs)

    def get_mempool_txs(self):
        return self.sort_txs(self.bitcoind.getrawmempool())

########NEW FILE########
__FILENAME__ = builder
""" Color data builder objects"""

from logger import log
from explorer import get_spends
from toposort import toposorted
from colorvalue import SimpleColorValue


class ColorDataBuilder(object):
    pass


class ColorDataBuilderManager(object):
    """Manages multiple color data builders, one per color"""
    def __init__(self, colormap, blockchain_state,
                 cdstore, metastore, builder_class):
        self.colormap = colormap
        self.metastore = metastore
        self.blockchain_state = blockchain_state
        self.cdstore = cdstore
        self.builders = {}
        self.builder_class = builder_class

    def get_color_def_map(self, color_id_set):
        """given a set of color_ids <color_id_set>, return
        a dict of color_id to color_def.
        """
        color_def_map = {}
        for color_id in color_id_set:
            color_def_map[color_id] = self.colormap.get_color_def(color_id)
        return color_def_map

    def get_builder(self, color_id):
        if color_id in self.builders:
            return self.builders[color_id]
        colordef = self.colormap.get_color_def(color_id)
        builder = self.builder_class(
            self.cdstore, self.blockchain_state, colordef, self.metastore)
        self.builders[color_id] = builder
        return builder

    def ensure_scanned_upto(self, color_id_set, blockhash):
        """ Ensure color data is available up to a given block"""
        for color_id in color_id_set:
            if color_id == 0:
                continue
            builder = self.get_builder(color_id)
            builder.ensure_scanned_upto(blockhash)

    def scan_txhash(self, color_id_set, txhash, output_indices=None):
        tx = self.blockchain_state.get_tx(txhash)
        self.scan_tx(color_id_set, tx, output_indices)

    def scan_tx(self, color_id_set, tx, output_indices=None):
        with self.cdstore.transaction():
            for color_id in color_id_set:
                if color_id == 0:
                    continue
                builder = self.get_builder(color_id)
                builder.scan_tx(tx, output_indices)


class BasicColorDataBuilder(ColorDataBuilder):
    """ Base class for color data builder algorithms"""
    def __init__(self, cdstore, blockchain_state, colordef, metastore):
        self.cdstore = cdstore
        self.blockchain_state = blockchain_state
        self.colordef = colordef
        self.color_id = colordef.color_id
        self.metastore = metastore

    def scan_tx(self, tx, output_indices=None):
        """ Scan transaction to obtain color data for its outputs. """
        in_colorvalues = []
        empty = True
        for inp in tx.inputs:
            val = self.cdstore.get(
                self.color_id, inp.prevout.hash, inp.prevout.n)
            cv = None
            if val:
                empty = False
                cv = SimpleColorValue(colordef=self.colordef,
                                      value=val[0])
                
            in_colorvalues.append(cv)
        if empty and not self.colordef.is_special_tx(tx):
            return
        out_colorvalues = self.colordef.run_kernel(tx, in_colorvalues)
        for o_index, val in enumerate(out_colorvalues):
            log("%s: %s, %s", o_index, val, output_indices and not (o_index in output_indices))
            if output_indices and not (o_index in output_indices):
                continue
            if val:
                self.cdstore.add(
                    self.color_id, tx.hash, o_index, val.get_value(), val.get_label())


class FullScanColorDataBuilder(BasicColorDataBuilder):
    """Color data builder based on exhaustive blockchain scan,
       for one specific color"""
    def __init__(self, cdstore, blockchain_state, colordef, metastore):
        super(FullScanColorDataBuilder, self).__init__(
            cdstore, blockchain_state, colordef, metastore)
        self.genesis_blockhash = self.blockchain_state.get_blockhash_at_height(
            self.colordef.genesis['height'])

    def scan_block(self, blockhash):
        if self.metastore.did_scan(self.color_id, blockhash):
            return
        log("scan block %s", blockhash)
        for tx in self.blockchain_state.iter_block_txs(blockhash):
            self.scan_tx(tx)
        self.metastore.set_as_scanned(self.color_id, blockhash)

    def scan_blockchain(self, blocklist):
        with self.cdstore.transaction():
            for i, blockhash in enumerate(blocklist):
                self.scan_block(blockhash)
                if i % 25 == 0:  # sync each 25 blocks
                    self.cdstore.sync()

    def ensure_scanned_upto(self, final_blockhash):
        if self.metastore.did_scan(self.color_id, final_blockhash):
            return

        # start from the final_blockhash and go backwards to build up
        #  the list of blocks to scan
        blockhash = final_blockhash
        genesis_height = self.blockchain_state.get_block_height(
            self.genesis_blockhash)
        blocklist = []
        while not self.metastore.did_scan(self.color_id, blockhash):
            log("recon block %s", blockhash)
            blocklist.insert(0, blockhash)
            blockhash, height = self.blockchain_state.get_previous_blockinfo(
                blockhash)
            if blockhash == self.genesis_blockhash:
                break  # pragma: no cover
            # sanity check
            if height < genesis_height:
                break  # pragma: no cover

        self.scan_blockchain(blocklist)


class AidedColorDataBuilder(BasicColorDataBuilder):
    """Color data builder based on following output spending transactions
        from the color's genesis transaction output, for one specific color"""

    def __init__(self, cdstore, blockchain_state, colordef, metastore):
        super(AidedColorDataBuilder, self).__init__(
            cdstore, blockchain_state, colordef, metastore)

    def scan_blockchain(self, blocklist):
        txo = self.colordef.genesis.copy()
        txo["blockhash"] = self.genesis_blockhash
        txo_queue = [txo]
        for blockhash in blocklist:
            if self.metastore.did_scan(self.color_id, blockhash):
                continue
            # remove txs from this block from the queue
            block_txo_queue = [txo for txo in txo_queue
                               if txo.get('blockhash') == blockhash]
            txo_queue = [txo for txo in txo_queue
                         if txo.get('blockhash') != blockhash]

            block_txos = {}
            while block_txo_queue:
                txo = block_txo_queue.pop()
                if txo['txhash'] in block_txos:
                    continue
                block_txos[txo['txhash']] = txo
                spends = get_spends(txo['txhash'], self.blockchain_state)
                for stxo in spends:
                    if stxo['blockhash'] == blockhash:
                        block_txo_queue.append(stxo)
                    else:
                        txo_queue.append(stxo)
            block_txs = {}
            for txhash in block_txos.keys():
                block_txs[txhash] = self.blockchain_state.get_tx(txhash)

            def get_prev_txs(tx):
                """all transactions from current block this transaction
                   directly depends on"""
                prev_txs = []
                for inp in tx.inputs:
                    if inp.prevout.hash in block_txs:
                        prev_txs.append(block_txs[inp.prevout.hash])
                return prev_txs

            sorted_block_txs = toposorted(block_txs.values(), get_prev_txs)

            for tx in sorted_block_txs:
                self.scan_tx(tx)
            self.metastore.set_as_scanned(self.color_id, blockhash)

########NEW FILE########
__FILENAME__ = colordata
""" Color data representation objects."""
import time

from logger import log

from colordef import ColorDefinition
from colorvalue import SimpleColorValue


class UnfoundTransactionError(Exception):
    pass


class ColorData(object):
    """Base color data class"""
    pass


class StoredColorData(ColorData):

    def __init__(self, cdbuilder_manager, blockchain_state, cdstore, colormap):
        self.cdbuilder_manager = cdbuilder_manager
        self.blockchain_state = blockchain_state
        self.cdstore = cdstore
        self.colormap = colormap

    def _fetch_colorvalues(self, color_id_set, txhash, outindex,
                           cvclass=SimpleColorValue):
        """returns colorvalues currently present in cdstore"""
        ret = []
        for entry in self.cdstore.get_any(txhash, outindex):
            color_id, value, label = entry
            if color_id in color_id_set:
                color_def = self.colormap.get_color_def(color_id)
                ret.append(cvclass(colordef=color_def, value=value,
                                   label=label))
        return ret

    def get_colorvalues_raw(self, color_id, ctx):
        """get colorvalues for all outputs of a raw transaction
        (which is, possibly, not in the blockchain yet)
        """
        color_id_set = set([color_id])
        color_def = self.cdbuilder_manager.colormap.get_color_def(color_id)
        in_colorvalues = []
        for inp in ctx.inputs:
            cvs = self.get_colorvalues(color_id_set,
                                       inp.prevout.hash,
                                       inp.prevout.n)
            cv = cvs[0] if cvs else None
            print color_id_set, inp.prevout.hash, inp.prevout.n, cv
            in_colorvalues.append(cv)
        log("GCR in_colorvalues: %s", in_colorvalues)
        return color_def.run_kernel(ctx, in_colorvalues)


class ThickColorData(StoredColorData):
    """ Color data which needs access to the whole blockchain state"""
    def __init__(self, *args, **kwargs):
        super(ThickColorData, self).__init__(*args, **kwargs)
        self.mempool_cache = []

    def get_colorvalues(self, color_id_set, txhash, outindex):
        blockhash, found = self.blockchain_state.get_tx_blockhash(txhash)
        if not found:
            raise UnfoundTransactionError("transaction %s isn't found"
                                          % txhash)
        if blockhash:
            self.cdbuilder_manager.ensure_scanned_upto(color_id_set, blockhash)
            return self._fetch_colorvalues(color_id_set, txhash, outindex)
        else:
            # not in the blockchain, but might be in the memory pool
            best_blockhash = None
            while 1:
                best_blockhash_prev = self.blockchain_state.get_best_blockhash()
                mempool = self.blockchain_state.get_mempool_txs()
                best_blockhash = self.blockchain_state.get_best_blockhash()
                if best_blockhash_prev == best_blockhash:
                    break
            if txhash not in [tx.hash for tx in mempool]:
                raise UnfoundTransactionError("transaction %s isn't found in mempool" % txhash)
            # the preceding blockchain
            self.cdbuilder_manager.ensure_scanned_upto(
                color_id_set, best_blockhash)
            # scan everything in the mempool
            for tx in mempool:
                self.cdbuilder_manager.scan_tx(color_id_set, tx)
            return self._fetch_colorvalues(color_id_set, txhash, outindex)


class ThinColorData(StoredColorData):
    """ Color data which needs access to the blockchain state up to the genesis of
        color."""
    def get_colorvalues(self, color_id_set, txhash, outindex):
        """
        for a given transaction <txhash> and output <outindex> and color
        <color_id_set>, return a list of dicts that looks like this:
        {
        'color_id': <color id>,
        'value': <colorvalue of this output>,
        'label': <currently unused>,
        }
        These correspond to the colorvalues of particular color ids for this
        output. Currently, each output should have a single element in the list.
        """
        color_def_map = self.cdbuilder_manager.get_color_def_map(color_id_set)

        scanned_outputs = set()

        def process(current_txhash, current_outindex):
            """For any tx out, process the colorvalues of the affecting
            inputs first and then scan that tx.
            """
            if (current_txhash, current_outindex) in scanned_outputs:
                return
            scanned_outputs.add((current_txhash, current_outindex))

            if self._fetch_colorvalues(color_id_set, current_txhash, current_outindex):
                return

            current_tx = self.blockchain_state.get_tx(current_txhash)
            if not current_tx:
                raise UnfoundTransactionError("can't find transaction %s" % current_txhash)

            # note a genesis tx will simply have 0 affecting inputs
            inputs = set()
            for color_id, color_def in color_def_map.items():
                inputs = inputs.union(
                    color_def.get_affecting_inputs(current_tx,
                                                   [current_outindex]))
            for i in inputs:
                process(i.prevout.hash, i.prevout.n)
            log("scan %s: %s", current_txhash, current_outindex)
            self.cdbuilder_manager.scan_tx(color_id_set, current_tx, [current_outindex])

        process(txhash, outindex)
        return self._fetch_colorvalues(color_id_set, txhash, outindex)

########NEW FILE########
__FILENAME__ = colordef
""" Color definition schemes """

import txspec
from collections import defaultdict

from colorvalue import SimpleColorValue
from txspec import ColorTarget

from logger import log

class InvalidTargetError(Exception):
    pass


class InvalidColorError(Exception):
    pass


class InvalidColorDefinitionError(Exception):
    pass


def get_color_desc_code(color_desc):
    return color_desc.split(':')[0]


class ColorDefinition(object):
    """ Represents a color definition scheme.
    This means how color exists and is transferred
    in the blockchain"""
    cd_classes = {}
    CLASS_CODE = None

    def __init__(self, color_id):
        self.color_id = color_id

    def get_color_id(self):
        return self.color_id

    def is_special_tx(self):
        raise Exception("Implement is_special_tx method")  # pragma: no cover

    def run_kernel(self, tx, in_colorvalues):
        raise Exception("Implement run_kernel method")  # pragma: no cover

    @classmethod
    def color_to_satoshi(cls, colorvalue):
        return colorvalue.get_value()

    @classmethod
    def get_class_code(cls):
        return cls.CLASS_CODE

    @staticmethod
    def register_color_def_class(cdclass):
        ColorDefinition.cd_classes[cdclass.get_class_code()] = cdclass

    @classmethod
    def from_color_desc(cls, color_id, color_desc):
        code = get_color_desc_code(color_desc)
        cdclass = cls.cd_classes[code]
        return cdclass.from_color_desc(color_id, color_desc)

    @classmethod
    def get_color_def_cls_for_code(cls, code):
        return cls.cd_classes.get(code, None)

    def __repr__(self):
        if self.color_id == 0:
            return ""
        elif self.color_id == -1:
            return "Genesis"
        return "Color Definition with %s" % self.color_id


GENESIS_OUTPUT_MARKER = ColorDefinition(-1)
UNCOLORED_MARKER = ColorDefinition(0)

def group_targets_by_color(targets, compat_cls):
    targets_by_color = defaultdict(list)
    for target in targets:
        color_def = target.get_colordef()
        if color_def == UNCOLORED_MARKER \
                or isinstance(color_def, compat_cls):
            targets_by_color[color_def.color_id].append(target)
        else:
            raise InvalidColorError('incompatible color definition')
    return targets_by_color


class GenesisColorDefinition(ColorDefinition):

    def __init__(self, color_id, genesis):
        super(GenesisColorDefinition, self).__init__(color_id)
        self.genesis = genesis

    def __repr__(self):
        return "%s:%s:%s:%s" % (
            self.CLASS_CODE, self.genesis['txhash'], self.genesis['outindex'],
            self.genesis['height'])

    def is_special_tx(self, tx):
        return tx.hash == self.genesis['txhash']

    @classmethod
    def from_color_desc(cls, color_id, color_desc):
        """ Create a color definition given a
        description string and the blockchain state"""
        code, txhash, outindex, height = color_desc.split(':')
        if (code != cls.CLASS_CODE):
            raise InvalidColorError('wrong color code in from_color_desc')
        genesis = {'txhash': txhash,
                   'height': int(height),
                   'outindex': int(outindex)}
        return cls(color_id, genesis)


class OBColorDefinition(GenesisColorDefinition):
    """Implements order-based coloring scheme"""
    CLASS_CODE = 'obc'

    def run_kernel(self, tx, in_colorvalues):
        out_colorvalues = []
        inp_index = 0
        cur_value = 0
        colored = False

        is_genesis = (tx.hash == self.genesis['txhash'])

        tx.ensure_input_values()

        for out_index in xrange(len(tx.outputs)):
            o = tx.outputs[out_index]
            if cur_value == 0:
                colored = True  # reset
            while cur_value < o.value:
                cur_value += tx.inputs[inp_index].value
                if colored:
                    colored = (in_colorvalues[inp_index] is not None)
                inp_index += 1

            is_genesis_output = is_genesis and (
                out_index == self.genesis['outindex'])

            if colored or is_genesis_output:
                cv = SimpleColorValue(colordef=self, value=o.value)
                out_colorvalues.append(cv)
            else:
                out_colorvalues.append(None)
        return out_colorvalues

    def get_affecting_inputs(self, tx, output_set):
        """Returns a set object consisting of inputs that correspond to the
        output indexes of <output_set> from transaction <tx>
        """
        if self.is_special_tx(tx):
            return set()
        tx.ensure_input_values()
        running_sum_inputs = []
        current_sum = 0
        for txin in tx.inputs:
            current_sum += txin.value
            running_sum_inputs.append(current_sum)
        running_sum_outputs = []
        current_sum = 0
        for output in tx.outputs:
            current_sum += output.value
            running_sum_outputs.append(current_sum)

        matching_input_set = set()

        num_inputs = len(running_sum_inputs)
        num_outputs = len(running_sum_outputs)
        for o in output_set:
            if o == 0:
                o_start = 0
            else:
                o_start = running_sum_outputs[o-1]
            o_end = running_sum_outputs[o]
            for i in range(num_inputs):
                if i == 0:
                    i_start = 0
                else:
                    i_start = running_sum_inputs[i - 1]
                i_end = running_sum_inputs[i]
                # if segments overlap
                if (o_start < i_end and i_end <= o_end) \
                        or (i_start < o_end and o_end <= i_end):
                    matching_input_set.add(tx.inputs[i])
        return matching_input_set

    @classmethod
    def compose_genesis_tx_spec(self, op_tx_spec):
        targets = op_tx_spec.get_targets()
        if len(targets) != 1:
            raise InvalidTargetError(
                'genesis transaction spec needs exactly one target')
        target = targets[0]
        if target.get_colordef() != GENESIS_OUTPUT_MARKER:
            raise InvalidColorError(
                'genesis transaction target should use -1 color_id')
        composed_tx_spec = op_tx_spec.make_composed_tx_spec()
        composed_tx_spec.add_txout(value=target.get_value(),
                                   target_addr=target.get_address())
        uncolored_value = SimpleColorValue(colordef=UNCOLORED_MARKER,
                                           value=target.get_value())
        inputs, total = op_tx_spec.select_coins(uncolored_value, composed_tx_spec)
        composed_tx_spec.add_txins(inputs)
        change = total - uncolored_value - composed_tx_spec.estimate_required_fee()
        if change > op_tx_spec.get_dust_threshold():
            composed_tx_spec.add_txout(value=change,
                                       target_addr=op_tx_spec.get_change_addr(UNCOLORED_MARKER),
                                       is_fee_change=True)
        return composed_tx_spec

    def compose_tx_spec(self, op_tx_spec):
        targets_by_color = group_targets_by_color(op_tx_spec.get_targets(), self.__class__)
        uncolored_targets = targets_by_color.pop(UNCOLORED_MARKER.color_id, [])
        composed_tx_spec = op_tx_spec.make_composed_tx_spec()
        # get inputs for each color
        for color_id, targets in targets_by_color.items():
            color_def = targets[0].get_colordef()
            needed_sum = ColorTarget.sum(targets)
            inputs, total = op_tx_spec.select_coins(needed_sum)
            change = total - needed_sum           
            if change > 0:
                targets.append(
                    ColorTarget(op_tx_spec.get_change_addr(color_def), change))
            composed_tx_spec.add_txins(inputs)
            for target in targets:
                composed_tx_spec.add_txout(value=target.get_value(),
                                           target=target)
        uncolored_needed = ColorTarget.sum(uncolored_targets)
        uncolored_inputs, uncolored_total = op_tx_spec.select_coins(uncolored_needed, composed_tx_spec)
        composed_tx_spec.add_txins(uncolored_inputs)
        fee = composed_tx_spec.estimate_required_fee()
        uncolored_change = uncolored_total - uncolored_needed - fee
        if uncolored_change > op_tx_spec.get_dust_threshold():
            composed_tx_spec.add_txout(value=uncolored_change,
                                       target_addr=op_tx_spec.get_change_addr(UNCOLORED_MARKER),
                                       is_fee_change=True)
        return composed_tx_spec


def uint_to_bit_list(n, bits=32):
    """little-endian"""
    return [1 & (n >> i) for i in range(bits)]

def bit_list_to_uint(bits):
    number = 0
    factor = 1
    for b in bits:
        if b == 1:
            number += factor
        factor *= 2
    return number

class EPOBCColorDefinition(GenesisColorDefinition):
    CLASS_CODE = 'epobc'

    class Tag(object):
        XFER_TAG_BITS = [1, 1, 0, 0, 1, 1]
        GENESIS_TAG_BITS = [1, 0, 1, 0, 0, 1]
        def __init__(self, padding_code, is_genesis):
            self.is_genesis = is_genesis
            self.padding_code = padding_code

        @classmethod
        def closest_padding_code(cls, min_padding):
            if min_padding <= 0:
                return 0
            padding_code = 1
            while 2 ** padding_code < min_padding:
                padding_code += 1
            if padding_code > 63:
                raise Exception('requires too much padding')
            return padding_code

        @classmethod
        def from_nSequence(cls, nSequence):
            bits = uint_to_bit_list(nSequence)
            tag_bits = bits[0:6]
            
            if ((tag_bits != cls.XFER_TAG_BITS) and
                (tag_bits != cls.GENESIS_TAG_BITS)):
                return None
            
            padding_code = bit_list_to_uint(bits[6:12])
            return cls(padding_code, tag_bits == cls.GENESIS_TAG_BITS)
        
        def to_nSequence(self):
            if self.is_genesis:
                bits = self.GENESIS_TAG_BITS[:]
            else:
                bits = self.XFER_TAG_BITS[:]
            bits += uint_to_bit_list(self.padding_code,
                                     6)
            bits += [0] * (32 - 12)
            return bit_list_to_uint(bits)

        def get_padding(self):
            if self.padding_code == 0:
                return 0
            else:
                return 2 ** self.padding_code

    @classmethod
    def get_tag(cls, tx):
        if tx.raw.vin[0].prevout.is_null():
            # coinbase tx is neither genesis nor xfer
            return None
        else:
            return cls.Tag.from_nSequence(tx.raw.vin[0].nSequence)

    @classmethod
    def get_xfer_affecting_inputs(cls, tx, padding, out_index):
        """
        Returns a set of indices that correspond to the inputs
        for an output in the transaction tx with output index out_index
        which has a padding of padding (2^n for some n>0 or 0).
        """
        tx.ensure_input_values()
        out_prec_sum = 0
        for oi in range(out_index):
            value_wop = tx.outputs[oi].value - padding
            if value_wop <= 0:
                return set()
            out_prec_sum += value_wop
        out_value_wop = tx.outputs[out_index].value - padding
        if out_value_wop <= 0:
            return set()
        affecting_inputs = set()
        input_running_sum = 0
        for ii, inp in enumerate(tx.inputs):
            prev_tag = cls.get_tag(inp.prevtx)
            if not prev_tag:
                break
            value_wop = tx.inputs[ii].value - prev_tag.get_padding()
            if value_wop <= 0:
                break
            if ((input_running_sum < (out_prec_sum + out_value_wop)) and
                ((input_running_sum + value_wop) > out_prec_sum)):
                affecting_inputs.add(ii)
            input_running_sum += value_wop
        return affecting_inputs


    def run_kernel(self, tx, in_colorvalues):
        """Given a transaction tx and the colorvalues in a list
        in_colorvalues, output the colorvalues of the outputs in a list
        """
        log("in_colorvalues: %s", in_colorvalues)
        tag = self.get_tag(tx)
        if tag is None:
            return [None] * len(tx.outputs)
        if tag.is_genesis:
            if tx.hash == self.genesis['txhash']:
                value_wop = tx.outputs[0].value - tag.get_padding()
                if value_wop > 0:
                    return ([SimpleColorValue(colordef=self,
                                              value=value_wop)] + 
                            [None] * (len(tx.outputs) - 1))
            # we get here if it is a genesis for a different color
            # or if genesis transaction is misconstructed
            return [None] * len(tx.outputs)

        tx.ensure_input_values()
        padding = tag.get_padding()
        out_colorvalues = []
        for out_idx, output in enumerate(tx.outputs):
            out_value_wop = tx.outputs[out_idx].value - padding
            if out_value_wop <= 0:
                out_colorvalues.append(None)
                continue
            affecting_inputs = self.get_xfer_affecting_inputs(tx, tag.get_padding(),
                                                              out_idx)
            log("affecting inputs: %s", affecting_inputs)
            ai_colorvalue = SimpleColorValue(colordef=self, value=0)
            all_colored = True
            for ai in affecting_inputs:
                if in_colorvalues[ai] is None:
                    all_colored = False
                    break
                ai_colorvalue += in_colorvalues[ai]
            log("all colored: %s, colorvalue:%s", all_colored, ai_colorvalue.get_value())
            if (not all_colored) or (ai_colorvalue.get_value() < out_value_wop):
                out_colorvalues.append(None)
                continue
            out_colorvalues.append(SimpleColorValue(colordef=self, value=out_value_wop))
        log("out_colorvalues: %s", out_colorvalues)
        return out_colorvalues

    def get_affecting_inputs(self, tx, output_set):
        tag = self.get_tag(tx)
        if (tag is None) or tag.is_genesis:
            return set()
        tx.ensure_input_values()
        aii = set()
        for out_idx in output_set:
            aii.update(self.get_xfer_affecting_inputs(
                    tx, tag.get_padding(), out_idx))
        inputs = set([tx.inputs[i] for i in aii])
        return inputs

    def compose_tx_spec(self, op_tx_spec):
        targets_by_color = group_targets_by_color(op_tx_spec.get_targets(), self.__class__)
        uncolored_targets = targets_by_color.pop(UNCOLORED_MARKER.color_id, [])
        composed_tx_spec = op_tx_spec.make_composed_tx_spec()
        if uncolored_targets:
            uncolored_needed = ColorTarget.sum(uncolored_targets)
        else:
            uncolored_needed = SimpleColorValue(colordef=UNCOLORED_MARKER,
                                                value=0)
        dust_threshold = op_tx_spec.get_dust_threshold().get_value()
        inputs_by_color = dict()
        min_padding = 0

        # step 1: get inputs, create change targets, compute min padding
        for color_id, targets in targets_by_color.items():
            color_def = targets[0].get_colordef()
            needed_sum = ColorTarget.sum(targets)
            inputs, total = op_tx_spec.select_coins(needed_sum)
            inputs_by_color[color_id] = inputs
            change = total - needed_sum
            if change > 0:
                targets.append(
                    ColorTarget(op_tx_spec.get_change_addr(color_def), change))
            for target in targets:
                padding_needed = dust_threshold - target.get_value() 
                if padding_needed > min_padding:
                    min_padding = padding_needed

        tag = self.Tag(self.Tag.closest_padding_code(min_padding), False)
        padding = tag.get_padding()

        # step 2: create txins & txouts, compute uncolored requirements
        for color_id, targets in targets_by_color.items():
            color_def = targets[0].get_colordef()
            for inp in inputs_by_color[color_id]:
                composed_tx_spec.add_txin(inp)
                uncolored_needed -= SimpleColorValue(colordef=UNCOLORED_MARKER,
                                               value=inp.value)
            for target in targets:
                svalue = target.get_value() + padding
                composed_tx_spec.add_txout(value=svalue,
                                           target=target)
                uncolored_needed += SimpleColorValue(colordef=UNCOLORED_MARKER,
                                               value=svalue)
                print uncolored_needed

        composed_tx_spec.add_txouts(uncolored_targets)
        fee = composed_tx_spec.estimate_required_fee()

        uncolored_change = None

        if uncolored_needed + fee > 0:
            uncolored_inputs, uncolored_total = op_tx_spec.select_coins(uncolored_needed, composed_tx_spec)
            composed_tx_spec.add_txins(uncolored_inputs)
            fee = composed_tx_spec.estimate_required_fee()
            uncolored_change = uncolored_total - uncolored_needed - fee
        else:
            uncolored_change =  (- uncolored_needed) - fee
            
        if uncolored_change > op_tx_spec.get_dust_threshold():
            composed_tx_spec.add_txout(value=uncolored_change,
                                       target_addr=op_tx_spec.get_change_addr(UNCOLORED_MARKER),
                                       is_fee_change=True)

        composed_tx_spec.txins[0].set_nSequence(tag.to_nSequence())

        return composed_tx_spec

    @classmethod
    def compose_genesis_tx_spec(cls, op_tx_spec):
        if len(op_tx_spec.get_targets()) != 1:
            raise InvalidTargetError(
                'genesis transaction spec needs exactly one target')
        g_target = op_tx_spec.get_targets()[0]
        if g_target.get_colordef() != GENESIS_OUTPUT_MARKER:
            raise InvalidColorError(
                'genesis transaction target should use -1 color_id')
        g_value = g_target.get_value()
        padding_needed = op_tx_spec.get_dust_threshold().get_value() - g_value
        tag = cls.Tag(cls.Tag.closest_padding_code(padding_needed), True)
        padding = tag.get_padding()
        composed_tx_spec = op_tx_spec.make_composed_tx_spec()
        composed_tx_spec.add_txout(value=padding + g_value,
                                   target=g_target)
        uncolored_needed = SimpleColorValue(colordef=UNCOLORED_MARKER,
                                           value=padding + g_value)        
        uncolored_inputs, uncolored_total = op_tx_spec.select_coins(uncolored_needed, 
                                                                    composed_tx_spec)
        composed_tx_spec.add_txins(uncolored_inputs)

        fee = composed_tx_spec.estimate_required_fee()
        change = uncolored_total - uncolored_needed - fee
        if change > op_tx_spec.get_dust_threshold():
            composed_tx_spec.add_txout(value=change,
                                       target_addr=op_tx_spec.get_change_addr(UNCOLORED_MARKER),
                                       is_fee_change=True)
        composed_tx_spec.txins[0].set_nSequence(tag.to_nSequence())
        return composed_tx_spec


ColorDefinition.register_color_def_class(OBColorDefinition)
ColorDefinition.register_color_def_class(EPOBCColorDefinition)

########NEW FILE########
__FILENAME__ = colormap
from colordef import ColorDefinition, UNCOLORED_MARKER
from txspec import InvalidColorIdError


class ColorMap(object):
    """ Manages and obtains color definitions """
    def __init__(self, metastore):
        self.metastore = metastore
        self.colordefs = {}

    def find_color_desc(self, color_id):
        if color_id == 0:
            return ""
        else:
            return self.metastore.find_color_desc(color_id)

    def resolve_color_desc(self, color_desc, auto_add=True):
        if color_desc == "":
            return 0
        else:
            return self.metastore.resolve_color_desc(color_desc, auto_add)

    def get_color_def(self, color_id_or_desc):
        """ Finds a color definition given an id or description """
        if color_id_or_desc == 0 or color_id_or_desc == '':
            return UNCOLORED_MARKER
        color_id = color_id_or_desc
        color_desc = None
        if not isinstance(color_id, (int, long)):
            color_desc = color_id_or_desc
            color_id = self.resolve_color_desc(color_id_or_desc)
        if color_id in self.colordefs:
            return self.colordefs[color_id]
        if not color_desc:
            color_desc = self.find_color_desc(color_id)
            if not color_desc:
                raise InvalidColorIdError("color id not found")
        cd = ColorDefinition.from_color_desc(
            color_id, color_desc)
        self.colordefs[color_id] = cd
        return cd

########NEW FILE########
__FILENAME__ = colorset
import hashlib
import json

from pycoin.encoding import b2a_base58


def deterministic_json_dumps(obj):
    """TODO: make it even more deterministic!"""
    return json.dumps(obj, separators=(',', ':'), sort_keys=True)


class ColorSet(object):
    """A set of colors which belong to certain a asset.
    It can be used to filter addresses and UTXOs
    """
    def __init__(self, colormap, color_desc_list):
        """Creates a new color set given a color map <colormap>
        and color descriptions <color_desc_list>
        """
        self.color_desc_list = color_desc_list
        self.color_id_set = set()
        for color_desc in color_desc_list:
            color_id = colormap.resolve_color_desc(color_desc)
            self.color_id_set.add(color_id)

    def __repr__(self):
        return self.color_desc_list.__repr__()

    def uncolored_only(self):
        return self.color_id_set == set([0])

    def get_data(self):
        """Returns a list of strings that describe the colors.
        e.g. ["obc:f0bd5...a5:0:128649"]
        """
        return self.color_desc_list

    def get_hash_string(self):
        """Returns a deterministic string for this color set.
        Useful for creating deterministic addresses for a given color.
        """
        json = deterministic_json_dumps(sorted(self.color_desc_list))
        return hashlib.sha256(json).hexdigest()

    def get_earliest(self):
        """Returns the color description of the earliest color to
        show in the blockchain. If there's a tie and two are issued
        in the same block, go with the one that has a smaller txhash
        """
        all_descs = self.get_data()
        if not len(all_descs):
            return "\x00\x00\x00\x00"
        best = all_descs[0]
        best_components = best.split(':')
        for desc in all_descs[1:]:
            components = desc.split(':')
            if int(components[3]) < int(best_components[3]):
                best = desc
            elif int(components[3]) == int(best_components[3]):
                if cmp(components[1], best_components[1]) == -1:
                    best = desc
        return best

    def get_color_hash(self):
        """Returns the hash used in color addresses.
        """
        return b2a_base58(self.get_hash_string().decode('hex')[:10])

    def has_color_id(self, color_id):
        """Returns boolean of whether color <color_id> is associated
        with this color set.
        """
        return (color_id in self.color_id_set)

    def intersects(self, other):
        """Given another color set <other>, returns whether
        they share a color in common.
        """
        return len(self.color_id_set & other.color_id_set) > 0

    def equals(self, other):
        """Given another color set <other>, returns whether
        they are the exact same color set.
        """
        return self.color_id_set == other.color_id_set

    @classmethod
    def from_color_ids(cls, colormap, color_ids):
        """Given a colormap <colormap> and a list of colors <color_ids>
        return a ColorSet object.
        """
        color_desc_list = [colormap.find_color_desc(color_id)
                           for color_id in color_ids]
        return cls(colormap, color_desc_list)

########NEW FILE########
__FILENAME__ = colorvalue
from comparable import ComparableMixin


class IncompatibleTypesError(Exception):
    pass


class InvalidValueError(Exception):
    pass


class ColorValue(object):
    def __init__(self, **kwargs):
        self.colordef = kwargs.pop('colordef')

    def get_kwargs(self):
        kwargs = {}
        kwargs['colordef'] = self.get_colordef()
        return kwargs

    def clone(self):
        kwargs = self.get_kwargs()
        return self.__class__(**kwargs)

    def check_compatibility(self, other):
        if self.get_color_id() != other.get_color_id():
            raise IncompatibleTypesError

    def get_colordef(self):
        return self.colordef

    def get_color_id(self):
        return self.colordef.get_color_id()

    def is_uncolored(self):
        return self.get_color_id() == 0


class AdditiveColorValue(ColorValue, ComparableMixin):
    def __init__(self, **kwargs):
        super(AdditiveColorValue, self).__init__(**kwargs)
        self.value = int(kwargs.pop('value'))
        if not isinstance(self.value, int):
            raise InvalidValueError('not an int but a %s'
                                    % self.value.__class__)

    def get_kwargs(self):
        kwargs = super(AdditiveColorValue, self).get_kwargs()
        kwargs['value'] = self.get_value()
        return kwargs

    def get_value(self):
        return self.value

    def get_satoshi(self):
        return self.get_colordef().__class__.color_to_satoshi(self)

    def __add__(self, other):
        if isinstance(other, int) and other == 0:
            return self
        self.check_compatibility(other)
        kwargs = self.get_kwargs()
        kwargs['value'] = self.get_value() + other.get_value()
        return self.__class__(**kwargs)

    def __neg__(self):
        kwargs = self.get_kwargs()
        kwargs['value'] = - self.get_value()
        return self.__class__(**kwargs)

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        if isinstance(other, int) and other == 0:
            return self
        self.check_compatibility(other)
        kwargs = self.get_kwargs()
        kwargs['value'] = self.get_value() - other.get_value()
        return self.__class__(**kwargs)

    def __iadd__(self, other):
        self.check_compatibility(other)
        self.value += other.value
        return self

    def __eq__(self, other):
        if self.get_colordef() != other.get_colordef():
            return False
        else:
            return self.get_value() == other.get_value()

    def __lt__(self, other):
        self.check_compatibility(other)
        return self.get_value() < other.get_value()

    def __gt__(self, other):
        if isinstance(other, int) and other == 0:
            return self.get_value() > 0
        return other < self

    @classmethod
    def sum(cls, items):
        return reduce(lambda x,y:x + y, items)


class SimpleColorValue(AdditiveColorValue):
    def __init__(self, **kwargs):
        super(SimpleColorValue, self).__init__(**kwargs)
        if kwargs.get('label'):
            self.label = kwargs.pop('label')
        else:
            self.label = ''

    def get_kwargs(self):
        kwargs = super(SimpleColorValue, self).get_kwargs()
        kwargs['label'] = self.get_label()
        return kwargs

    def get_label(self):
        return self.label

    def __repr__(self):
        return "%s: %s" % (self.get_label() or self.get_colordef(), self.value)

########NEW FILE########
__FILENAME__ = comparable
class ComparableMixin:
  def __ne__(self, other):
    return not (self == other)

  def __ge__(self, other):
    return not (self < other)

  def __le__(self, other):
    return not (other < self)

########NEW FILE########
__FILENAME__ = explorer

import urllib2
import json

BASE_URL = "http://abe.bitcontracts.org"


def get_spends(tx, blockchain_state):
    """ Returns transactions which spend outputs from a given transaction
    """
    url = '%s/spends/%s' % (BASE_URL, tx)
    response = urllib2.urlopen(url)
    ret = []
    for i, tx_hash, output_n in json.load(response):
        ret.append(
            {'txhash': tx_hash,
             'outindex': output_n,
             'blockhash': blockchain_state.get_tx_blockhash(tx_hash)})
    return ret

########NEW FILE########
__FILENAME__ = logger
import sys


def log(something, *args):
    if args:
        something = something % args
    print >>sys.stderr, something

########NEW FILE########
__FILENAME__ = obsolete_colordefs
# NOTE: these colordefs are unused, untested,
#       and will be deleted in later released


class POBColorDefinition(GenesisColorDefinition):

    CLASS_CODE = 'pobc'
    PADDING = 10000

    def run_kernel(self, tx, in_colorvalues):
        """Computes the output colorvalues"""

        is_genesis = (tx.hash == self.genesis['txhash'])

        # it turns out having a running sum in an array is easier
        #  than constructing segments
        input_running_sums = []
        ZERO_COLORVALUE = SimpleColorValue(colordef=self, value=0)
        running_sum = ZERO_COLORVALUE.clone()
        tx.ensure_input_values()
        for element in tx.inputs:
            colorvalue = self.satoshi_to_color(element.value)
            if colorvalue <= ZERO_COLORVALUE:
                break
            running_sum += colorvalue
            input_running_sums.append(running_sum.clone())

        output_running_sums = []
        running_sum = ZERO_COLORVALUE.clone()
        for element in tx.outputs:
            colorvalue = self.satoshi_to_color(element.value)
            if colorvalue <= ZERO_COLORVALUE:
                break
            running_sum += colorvalue
            output_running_sums.append(running_sum.clone())

        # default is that every output has a null colorvalue
        out_colorvalues = [None for i in output_running_sums]

        # see if this is a genesis transaction
        if is_genesis:
            # adjust the single genesis index to have the right value
            #  and return it
            i = self.genesis['outindex']
            out_colorvalues[i] = self.satoshi_to_color(tx.outputs[i].value)
            return out_colorvalues

        # determine if the in_colorvalues are well-formed:
        # after that, there should be some number of non-null values
        # if another null is hit, there should be no more non-null values
        nonnull_sequences = 0
        if in_colorvalues[0] is None:
            current_sequence_is_null = True
            input_color_start = None
        else:
            current_sequence_is_null = False
            input_color_start = 0
        input_color_end = None
        for i, colorvalue in enumerate(in_colorvalues):
            if colorvalue is not None and current_sequence_is_null:
                current_sequence_is_null = False
                input_color_start = i
            elif colorvalue is None and not current_sequence_is_null:
                current_sequence_is_null = True
                input_color_end = i - 1
                nonnull_sequences += 1
        if not current_sequence_is_null:
            nonnull_sequences += 1
            input_color_end = len(in_colorvalues) - 1

        if nonnull_sequences > 1:
            return out_colorvalues

        # now figure out which segments correspond in the output
        if input_color_start == 0:
            sum_before_sequence = ZERO_COLORVALUE.clone()
        else:
            sum_before_sequence = input_running_sums[input_color_start - 1]
        sum_after_sequence = input_running_sums[input_color_end]

        # the sum of the segment before the sequence must be equal
        #  as the sum of the sequence itself must also be equal
        if (sum_before_sequence != ZERO_COLORVALUE
            and sum_before_sequence not in output_running_sums) or \
                sum_after_sequence not in output_running_sums:
            # this means we don't have matching places to start and/or end
            return out_colorvalues

        # now we know exactly where the output color sequence should start
        #  and end
        if sum_before_sequence == ZERO_COLORVALUE:
            output_color_start = 0
        else:
            output_color_start = output_running_sums.index(
                sum_before_sequence) + 1
        output_color_end = output_running_sums.index(sum_after_sequence)

        # calculate what the color value at that point is
        for i in range(output_color_start, output_color_end + 1):
            previous_sum = ZERO_COLORVALUE if i == 0 \
                else output_running_sums[i - 1]
            out_colorvalues[i] = output_running_sums[i] - previous_sum

        return out_colorvalues

    def satoshi_to_color(self, satoshivalue):
        return SimpleColorValue(colordef=self,
                                value=satoshivalue - self.PADDING)

    @classmethod
    def color_to_satoshi(cls, colorvalue):
        return colorvalue.get_value() + cls.PADDING

    @classmethod
    def compose_genesis_tx_spec(cls, op_tx_spec):
        targets = op_tx_spec.get_targets()[:]
        if len(targets) != 1:
            raise InvalidTargetError(
                'genesis transaction spec needs exactly one target')
        target = targets[0]
        if target.get_colordef() != GENESIS_OUTPUT_MARKER:
            raise InvalidColorError(
                'genesis transaction target should use -1 color_id')
        fee = op_tx_spec.get_required_fee(300)
        amount = target.colorvalue.get_satoshi()
        uncolored_value = SimpleColorValue(colordef=UNCOLORED_MARKER,
                                           value=amount)
        colorvalue = fee + uncolored_value
        inputs, total = op_tx_spec.select_coins(colorvalue)
        change = total - fee - uncolored_value
        if change > 0:
            targets.append(ColorTarget(
                    op_tx_spec.get_change_addr(UNCOLORED_MARKER), change))
        txouts = [txspec.ComposedTxSpec.TxOut(target.get_satoshi(),
                                              target.get_address())
                  for target in targets]
        return txspec.ComposedTxSpec(inputs, txouts)

    def compose_tx_spec(self, op_tx_spec):
        # group targets by color
        targets_by_color = defaultdict(list)
        # group targets by color
        for target in op_tx_spec.get_targets():
            color_def = target.get_colordef()
            if color_def == UNCOLORED_MARKER \
                    or isinstance(color_def, POBColorDefinition):
                targets_by_color[color_def.color_id].append(target)
            else:
                raise InvalidColorError('incompatible color definition')
        uncolored_targets = targets_by_color.pop(UNCOLORED_MARKER.color_id, [])

        # get inputs for each color
        colored_inputs = []
        colored_targets = []
        for color_id, targets in targets_by_color.items():
            color_def = targets[0].get_colordef()
            needed_sum = ColorTarget.sum(targets)
            inputs, total = op_tx_spec.select_coins(needed_sum)
            change = total - needed_sum
            if change > 0:
                targets.append(ColorTarget(
                        op_tx_spec.get_change_addr(color_def), change))
            colored_inputs += inputs
            colored_targets += targets

        # we also need some amount of extra "uncolored" coins
        # for padding purposes, possibly
        padding_needed = (len(colored_targets) - len(colored_inputs)) \
            * self.PADDING
        uncolored_needed = ColorTarget.sum(uncolored_targets) \
            + SimpleColorValue(colordef=UNCOLORED_MARKER, value=padding_needed)
        fee = op_tx_spec.get_required_fee(250 * (len(colored_inputs) + 1))
        amount_needed = uncolored_needed + fee
        zero = SimpleColorValue(colordef=UNCOLORED_MARKER, value=0)
        if amount_needed == zero:
            uncolored_change = zero
            uncolored_inputs = []
        else:
            uncolored_inputs, uncolored_total = op_tx_spec.select_coins(amount_needed)
            uncolored_change = uncolored_total - amount_needed
        if uncolored_change > zero:
            uncolored_targets.append(
                ColorTarget(op_tx_spec.get_change_addr(UNCOLORED_MARKER),
                 uncolored_change))

        # compose the TxIn and TxOut elements
        txins = colored_inputs + uncolored_inputs
        txouts = [
            txspec.ComposedTxSpec.TxOut(target.get_satoshi(),
                                        target.get_address())
            for target in colored_targets]
        txouts += [txspec.ComposedTxSpec.TxOut(target.get_satoshi(),
                                               target.get_address())
                   for target in uncolored_targets]
        return txspec.ComposedTxSpec(txins, txouts)


def ones(n):
    """ finds indices for the 1's in an integer"""
    while n:
        b = n & (~n + 1)
        i = int(math.log(b, 2))
        yield i
        n ^= b


   
class BFTColorDefinition (GenesisColorDefinition):
    CLASS_CODE = 'btfc'

    def run_kernel(self, tx, in_colorvalues):
        """Computes the output colorvalues"""
        # special case: genesis tx output
        tx.ensure_input_values()
        if tx.hash == self.genesis['txhash']:
            return [SimpleColorValue(colordef=self, value=out.value)
                    if self.genesis['outindex'] == i else None \
                        for i, out in enumerate(tx.outputs)]
            
        # start with all outputs having null colorvalue
        nones = [None for _ in tx.outputs]
        out_colorvalues = [None for _ in tx.outputs]
        output_groups = {}
        # go through all inputs
        for inp_index in xrange(len(tx.inputs)):
            # if input has non-null colorvalue, check its nSequence
            color_value = in_colorvalues[inp_index]
            if color_value:
                nSequence = tx.raw.vin[inp_index].nSequence
                # nSequence is converted to a set of output indices
                output_group = list(ones(nSequence))
                
                # exceptions; If exceptional situation is detected, we return a list of null colorvalues.
                # nSequence is 0
                if nSequence == 0:
                    return nones
                
                # nSequence has output indices exceeding number of outputs of this transactions
                for out_idx in output_group:
                    if out_idx >= len(tx.inputs):
                        return nones
                # there are intersecting 'output groups' (i.e output belongs to more than one group)
                if not nSequence in output_groups:
                    for og in output_groups:
                        if len(set(ones(og)).intersection(output_group)) != 0:
                            return nones
                    output_groups[nSequence] = SimpleColorValue(colordef=self,
                                                                value=0)
                        
                # add colorvalue of this input to colorvalue of output group
                output_groups[nSequence] += color_value

        # At this step we have total colorvalue for each output group.
        # For each output group:
        for nSequence in output_groups:
            output_group = list(ones(nSequence))
            in_colorvalue = output_groups[nSequence]
            # sum satoshi-values of outputs in it (let's call it ssvalue)
            ssvalue = sum(tx.outputs[out_idx].value for out_idx in output_group)
            #find n such that 2^n*ssvalue = total colorvalue (loop over all |n|<32, positive and negative)
            for n in xrange(-31,32):
                if ssvalue*2**n == in_colorvalue.get_value():
                    # if n exists, each output of this group is assigned colorvalue svalue*2^n, where svalue is its satoshi-value
                    for out_idx in output_group:
                        svalue = tx.outputs[out_idx].value
                        out_colorvalues[out_idx] = SimpleColorValue(colordef=self, value=svalue*2**n, label=in_colorvalue.get_label())
                    break
            else:
                # if n doesn't exist, we treat is as an exceptional sitation and return a list of None values.
                return nones  # pragma: no cover

        return out_colorvalues

# ColorDefinition.register_color_def_class(POBColorDefinition)
# ColorDefinition.register_color_def_class(BFTColorDefinition)

########NEW FILE########
__FILENAME__ = store
""" sqlite3 implementation of storage for color data """

import sqlite3

from UserDict import DictMixin
import cPickle as pickle


class DataStoreConnection(object):
    """ A database connection """
    def __init__(self, path, autocommit=False):
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        if autocommit:
            self.conn.isolation_level = None

    def __del__(self):
        if self.conn:
            self.conn.commit()
            self.conn.close()


class DataStore(object):
    """ Represents a database and allows it's
    manipulation via queries."""
    def __init__(self, conn):
        self.conn = conn

    def table_exists(self, tablename):
        res = self.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (tablename, )).fetchone()
        return res is not None

    def column_exists(self, tablename, column_name):
        info = self.execute("PRAGMA table_info(tx_data)")
        return any(row[1] == 'block_height' for row in info)

    def execute(self, statement, params=()):
        cur = self.conn.cursor()
        cur.execute(statement, params)
        return cur

    def sync(self):
        self.conn.commit()

    def transaction(self):
        return self.conn


def unwrap1(val):
    if val:
        return val[0]
    else:
        return None


class ColorDataStore(DataStore):
    """ A DataStore for color data storage. """
    def __init__(self, conn, tablename='colordata'):
        super(ColorDataStore, self).__init__(conn)
        self.tablename = tablename
        if not self.table_exists(tablename):
            statement = "CREATE TABLE {0} (color_id INTEGER, txhash TEXT, " \
                "outindex INTEGER, value REAL, label TEXT);".format(tablename)
            self.execute(statement)
            statement = "CREATE UNIQUE INDEX {0}_data_idx on {0}(color_id, " \
                "txhash, outindex)".format(tablename)
            self.execute(statement)
        self.queries = dict()
        self.queries['add'] = "INSERT OR REPLACE INTO {0} VALUES " \
            "(?, ?, ?, ?, ?)".format(self.tablename)
        self.queries['remove'] = "DELETE FROM {0} WHERE color_id = ? " \
            "AND txhash = ? AND outindex = ?".format(self.tablename)
        self.queries['get'] = "SELECT value, label FROM {0} WHERE " \
            "color_id = ? AND txhash = ? AND outindex = ?".format(
                self.tablename)
        self.queries['get_any'] = "SELECT color_id, value, label FROM " \
            "{0} WHERE txhash = ? AND outindex = ?".format(self.tablename)
        self.queries['get_all'] = "SELECT txhash, outindex, value, " \
            "label FROM {0} WHERE color_id = ?".format(self.tablename)

    def add(self, color_id, txhash, outindex, value, label):
        self.execute(
            self.queries['add'], (color_id, txhash, outindex, value, label))

    def remove(self, color_id, txhash, outindex):
        self.execute(self.queries['remove'], (color_id, txhash, outindex))

    def get(self, color_id, txhash, outindex):
        return self.execute(
            self.queries['get'], (color_id, txhash, outindex)).fetchone()

    def get_any(self, txhash, outindex):
        return self.execute(
            self.queries['get_any'], (txhash, outindex)).fetchall()

    def get_all(self, color_id):
        return self.execute(self.queries['get_all'], (color_id,)).fetchall()


class PersistentDictStore(DictMixin, DataStore):
    """ Persistent dict object """

    def __init__(self, conn, dictname):
        super(PersistentDictStore, self).__init__(conn)
        conn.text_factory = str
        self.tablename = dictname + "_dict"
        if not self.table_exists(self.tablename):
            self.execute("CREATE TABLE {0} (key NOT NULL PRIMARY KEY "
                         "UNIQUE, value BLOB)".format(self.tablename))

    def deserialize(self, svalue):
        return pickle.loads(svalue)

    def serialize(self, value):
        return pickle.dumps(value)

    def __getitem__(self, key):
        svalue = self.execute(
            "SELECT value FROM {0} WHERE key = ?".format(self.tablename),
            (key,)).fetchone()
        if svalue:
            return self.deserialize(unwrap1(svalue))
        else:
            raise KeyError()

    def __setitem__(self, key, value):
        self.execute(
            "INSERT OR REPLACE INTO {0} VALUES (?, ?)".format(self.tablename),
            (key, self.serialize(value)))

    def __contains__(self, key):
        svalue = self.execute(
            "SELECT value FROM {0} WHERE key = ?".format(self.tablename),
            (key,)).fetchone()
        return svalue is not None

    def __delitem__(self, key):
        if self.__contains__(key):
            self.execute(
                "DELETE FROM {0} WHERE key = ?".format(self.tablename),
                (key,))
        else:
            raise KeyError()

    def keys(self):
        return map(
            unwrap1,
            self.execute(
                "SELECT key FROM {0}".format(self.tablename)).fetchall())


class ColorMetaStore(DataStore):
    """ A DataStore containing meta-information
    on a coloring scheme, like color ids, how much
    of the blockchain was scanned, etc."""
    def __init__(self, conn):
        super(ColorMetaStore, self).__init__(conn)
        if not self.table_exists('scanned_block'):
            self.execute(
                "CREATE TABLE scanned_block "
                "(color_id INTEGER, blockhash TEXT)")
            self.execute(
                "CREATE UNIQUE INDEX scanned_block_idx "
                "on scanned_block(color_id, blockhash)")
        if not self.table_exists('color_map'):
            self.execute(
                "CREATE TABLE color_map (color_id INTEGER PRIMARY KEY "
                "AUTOINCREMENT, color_desc TEXT)")
            self.execute(
                "CREATE UNIQUE INDEX color_map_idx ON color_map(color_desc)")

    def did_scan(self, color_id, blockhash):
        return unwrap1(
            self.execute(
                "SELECT 1 FROM scanned_block WHERE "
                "color_id = ? AND blockhash = ?",
                (color_id, blockhash)).fetchone())

    def set_as_scanned(self, color_id, blockhash):
        self.execute(
            "INSERT INTO scanned_block (color_id, blockhash) "
            "VALUES (?, ?)",
            (color_id, blockhash))

    def resolve_color_desc(self, color_desc, auto_add):
        q = "SELECT color_id FROM color_map WHERE color_desc = ?"
        res = self.execute(q, (color_desc, )).fetchone()
        if (res is None) and auto_add:
            self.execute(
                "INSERT INTO color_map(color_id, color_desc) VALUES (NULL, ?)",
                (color_desc,))
            self.sync()
            res = self.execute(q, (color_desc, )).fetchone()
        return unwrap1(res)

    def find_color_desc(self, color_id):
        q = "SELECT color_desc FROM color_map WHERE color_id = ?"
        return unwrap1(self.execute(q, (color_id,)).fetchone())

########NEW FILE########
__FILENAME__ = test_blockchain
#!/usr/bin/env python

import unittest

from bitcoin.rpc import RawProxy

from coloredcoinlib.blockchain import BlockchainState, script_to_raw_address


class TestBlockchainState(unittest.TestCase):
    def setUp(self):
        self.bs = BlockchainState.from_url(None, True)
        self.blockhash = '00000000c927c5d0ee1ca362f912f83c462f644e695337ce3731b9f7c5d1ca8c'
        self.previous_blockhash = '000000000001c503d2e3bff1d73eb53213a8d784206a233181ea11f95c5fd097'
        self.txhash = '72386db4bf4ced6380763d3eb09b634771ba519e200b57da765def26219ef508'
        self.height = 154327
        self.coinbase = '4fe45a5ba31bab1e244114c4555d9070044c73c98636231c77657022d76b87f7'
        self.tx = self.bs.get_tx(self.txhash)
        self.coinbasetx = self.bs.get_tx(self.coinbase)

    def test_get_tx(self):
        self.assertEqual(self.tx.inputs[0].get_txhash()[::-1].encode('hex'), 'c6dcb546bfe4e096e2c2e894fb8c95e9615e6df3095db0e59a4f2413e17a76af')
        self.assertEqual(self.tx.inputs[0].get_outpoint()[1], 1)
        self.assertEqual(self.coinbasetx.inputs[0].get_txhash(), 'coinbase')

    def test_script_to_raw_address(self):
        self.assertEqual(script_to_raw_address(''), None)

    def test_get_block_height(self):
        self.assertEqual(self.bs.get_block_height(self.blockhash), self.height)

    def test_get_blockhash_at_height(self):
        self.assertEqual(self.bs.get_blockhash_at_height(self.height),
                         self.blockhash)

    def test_get_tx_blockhash(self):
        self.assertEqual(self.bs.get_tx_blockhash(self.txhash),
                         (self.blockhash, True))
        self.assertEqual(self.bs.get_tx_blockhash(self.txhash[:-1] + '0'),
                         (None, False))

    def test_get_previous_blockinfo(self):
        self.assertEqual(self.bs.get_previous_blockinfo(self.blockhash)[0],
                         self.previous_blockhash)
        
    def test_ensure(self):
        self.tx.ensure_input_values()
        self.assertTrue(self.tx.have_input_values)
        self.tx.ensure_input_values()
        self.assertTrue(self.tx.have_input_values)
        self.coinbasetx.ensure_input_values()
        self.assertTrue(self.coinbasetx.have_input_values)

    def test_get_best(self):
        self.assertTrue(self.bs.get_best_blockhash())
        
    def test_iter_block_txs(self):
        i = 0
        txs = []
        for tx in self.bs.iter_block_txs(self.blockhash):
            i += 1
            tx.ensure_input_values()
            txs.append(tx.hash)
        self.assertEqual(i, 12)
        sorted_txs = [tx.hash for tx in self.bs.sort_txs(txs)]
        self.assertEqual(len(sorted_txs), 12)
        # a should be before b
        a = '5e9762b340e2f72a66dabe16d738a8ae89d71843286e7c9354eaf299d906845c'
        b = '264b174948d0be47d7661b60ecc88b575ab1216617f5298a230c27f7a34f2e40'
        self.assertTrue(a in sorted_txs)
        self.assertTrue(b in sorted_txs)
        self.assertTrue(sorted_txs.index(a) < sorted_txs.index(b))

    def test_mempool(self):
        mempool_txs = self.bs.get_mempool_txs()
        if len(mempool_txs):
            tx = mempool_txs[0]
            bh = self.bs.get_tx_blockhash(tx.hash)
            self.assertTrue(bh)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_builder
#!/usr/bin/env python

import datetime
import unittest

from coloredcoinlib.blockchain import BlockchainState
from coloredcoinlib.builder import (ColorDataBuilderManager,
                                    FullScanColorDataBuilder, AidedColorDataBuilder)
from coloredcoinlib.colordata import ThickColorData, ThinColorData
from coloredcoinlib.colormap import ColorMap
from coloredcoinlib.store import DataStoreConnection, ColorDataStore, ColorMetaStore


class TestAided(unittest.TestCase):

    def makeBuilder(self):
        self.cdbuilder = ColorDataBuilderManager(self.colormap,
                                                 self.blockchain_state,
                                                 self.cdstore,
                                                 self.metastore,
                                                 AidedColorDataBuilder)
        self.colordata = ThinColorData(self.cdbuilder,
                                       self.blockchain_state,
                                       self.cdstore,
                                       self.colormap)

    def setUp(self):
        self.blockchain_state = BlockchainState.from_url(None, True)
        self.store_conn = DataStoreConnection(":memory:")
        self.cdstore = ColorDataStore(self.store_conn.conn)
        self.metastore = ColorMetaStore(self.store_conn.conn)
        self.colormap = ColorMap(self.metastore)
        self.makeBuilder()
        self.blue_desc = "obc:" \
            "b1586cd10b32f78795b86e9a3febe58d" \
            "cb59189175fad884a7f4a6623b77486e" \
            ":0:46442"
        self.red_desc = "obc:" \
            "8f6c8751f39357cd42af97a67301127d" \
            "497597ae699ad0670b4f649bd9e39abf" \
            ":0:46444"
        self.blue_id = self.colormap.resolve_color_desc(self.blue_desc)
        self.red_id = self.colormap.resolve_color_desc(self.red_desc)
        self.bh = "00000000152164fcc3589ef36a0c34c1c821676e5766787a2784a761dd3dbfb5"
        self.bh2 = "0000000001167e13336f386acbc0d9169dd929ecb1e5d44229fc870206e669f8"
        self.bh3 = "0000000002fda52e8ad950d48651b3a86bce6d80eb016dffbec5477f10467541"
    def test_get_color_def_map(self):
        cdm = self.cdbuilder.get_color_def_map(set([self.blue_id,
                                                    self.red_id]))
        self.assertTrue(self.blue_id in cdm.keys())
        self.assertTrue(self.red_id in cdm.keys())

    def test_zero_scan(self):
        color_id_set = set([0])
        self.cdbuilder.ensure_scanned_upto(color_id_set, '')
        self.cdbuilder.scan_tx(color_id_set, '')

    def test_scan_txhash(self):
        # builder
        builder = self.cdbuilder.get_builder(self.blue_id)
        if not builder.metastore.did_scan(self.blue_id, self.bh):
            builder.ensure_scanned_upto(self.bh)
            self.assertTrue(builder.metastore.did_scan(self.blue_id, self.bh))

        # test scans
        blue_set = set([self.blue_id])
        red_set = set([self.red_id])
        br_set = blue_set | red_set
        tx = "b1586cd10b32f78795b86e9a3febe58dcb59189175fad884a7f4a6623b77486e"
        self.cdbuilder.scan_txhash(blue_set, tx)
        self.assertTrue(self.cdbuilder.cdstore.get(self.blue_id, tx, 0))
        tx = "f50f29906ce306be3fc06df74cc6a4ee151053c2621af8f449b9f62d86cf0647"
        self.cdbuilder.scan_txhash(blue_set, tx)
        self.assertTrue(self.cdbuilder.cdstore.get(self.blue_id, tx, 0))
        tx = "8f6c8751f39357cd42af97a67301127d497597ae699ad0670b4f649bd9e39abf" 
        self.cdbuilder.scan_txhash(blue_set, tx)
        self.assertFalse(self.cdbuilder.cdstore.get(self.blue_id, tx, 0))

    def test_scan_blockchain(self):
        builder = self.cdbuilder.get_builder(self.blue_id)
        builder.scan_blockchain([self.bh2, self.bh2])

    def test_sanity(self):
        blue_set = set([self.blue_id])
        red_set = set([self.red_id])
        br_set = blue_set | red_set
        label = {self.blue_id:'Blue', self.red_id:'Red'}

        g = self.colordata.get_colorvalues

        cv = g(
            br_set,
            "b1586cd10b32f78795b86e9a3febe58dcb59189175fad884a7f4a6623b77486e",
            0)[0]
        
        self.assertEqual(cv.get_color_id(), self.blue_id)
        self.assertEqual(cv.get_value(), 1000)


        cv = g(
            br_set,
            "8f6c8751f39357cd42af97a67301127d497597ae699ad0670b4f649bd9e39abf",
            0)[0]
        self.assertEqual(cv.get_color_id(), self.red_id)
        self.assertEqual(cv.get_value(), 1000)

        cvs = g(
            br_set,
            "b1586cd10b32f78795b86e9a3febe58dcb59189175fad884a7f4a6623b77486e",
            1)
        self.assertEqual(len(cvs), 0)

        cvs = g(
            br_set,
            "8f6c8751f39357cd42af97a67301127d497597ae699ad0670b4f649bd9e39abf",
            1)
        self.assertEqual(len(cvs), 0)

        cv = g(
            br_set,
            'c1d8d2fb75da30b7b61e109e70599c0187906e7610fe6b12c58eecc3062d1da5',
            0)[0]
        self.assertEqual(cv.get_color_id(), self.red_id)
        self.assertEqual(cv.get_value(), 500)
        
        cv = g(
            br_set,
            '36af9510f65204ec5532ee62d3785584dc42a964013f4d40cfb8b94d27b30aa1',
            0)[0]
        self.assertEqual(cv.get_color_id(), self.red_id)
        self.assertEqual(cv.get_value(), 150)

        cvs = g(
            br_set,
            '3a60b70d425405f3e45f9ed93c30ca62b2a97e692f305836af38a524997dd01d',
            0)
        self.assertEqual(len(cvs), 0)

        cv = g(
            br_set,
            '8f6c8751f39357cd42af97a67301127d497597ae699ad0670b4f649bd9e39abf',
            0)[0]
        self.assertEqual(cv.get_color_id(), self.red_id)
        self.assertEqual(cv.get_value(), 1000)

        cv = g(
            br_set,
            'f50f29906ce306be3fc06df74cc6a4ee151053c2621af8f449b9f62d86cf0647',
            0)[0]
        self.assertEqual(cv.get_color_id(), self.blue_id)
        self.assertEqual(cv.get_value(), 500)


        self.cdbuilder.scan_txhash(blue_set, '7e40d2f414558be60481cbb976e78f2589bc6a9f04f38836c18ed3d10510dce5')

        cv = g(
            br_set,
            '7e40d2f414558be60481cbb976e78f2589bc6a9f04f38836c18ed3d10510dce5',
            0)[0]
        self.assertEqual(cv.get_color_id(), self.blue_id)
        self.assertEqual(cv.get_value(), 100)

        cv = g(
            br_set,
            '4b60bb49734d6e26d798d685f76a409a5360aeddfddcb48102a7c7ec07243498',
            0)[0]
        self.assertEqual(cv.get_color_id(), self.red_id)

        cvs = g(
            br_set,
            '342f119db7f9989f594d0f27e37bb5d652a3093f170de928b9ab7eed410f0bd1',
            0)
        self.assertEqual(len(cvs), 0)

        cv = g(
            br_set,
            'bd34141daf5138f62723009666b013e2682ac75a4264f088e75dbd6083fa2dba',
            0)[0]
        self.assertEqual(cv.get_color_id(), self.blue_id)

        cvs = g(
            br_set,
            'bd34141daf5138f62723009666b013e2682ac75a4264f088e75dbd6083fa2dba',
            1)
        self.assertEqual(len(cvs), 0)

        cv = g(
            br_set,
            '36af9510f65204ec5532ee62d3785584dc42a964013f4d40cfb8b94d27b30aa1',
            0)[0]
        self.assertEqual(cv.get_color_id(), self.red_id)

        cv = g(
            br_set,
            '741a53bf925510b67dc0d69f33eb2ad92e0a284a3172d4e82e2a145707935b3e',
            0)[0]
        self.assertEqual(cv.get_color_id(), self.red_id)

        cv = g(
            br_set,
            '741a53bf925510b67dc0d69f33eb2ad92e0a284a3172d4e82e2a145707935b3e',
            1)[0]
        self.assertEqual(cv.get_color_id(), self.red_id)


class TestFullScan(TestAided):

    def makeBuilder(self):
        self.cdbuilder = ColorDataBuilderManager(self.colormap,
                                                 self.blockchain_state,
                                                 self.cdstore,
                                                 self.metastore,
                                                 FullScanColorDataBuilder)
        self.colordata = ThickColorData(self.cdbuilder,
                                        self.blockchain_state,
                                        self.cdstore,
                                        self.colormap)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_colordata
#!/usr/bin/env python

import unittest

from coloredcoinlib.colordata import (ThickColorData, ThinColorData,
                                      UnfoundTransactionError)
from test_colormap import MockColorMap
from test_txspec import MockTX


class MockBuilder:
    def ensure_scanned_upto(self, i, j):
        return True
    def scan_tx(self, a, b):
        return
    def scan_txhash(self, a, b):
        return
    def get_color_def_map(self, x):
        m = MockColorMap()
        r = {}
        for k,v in m.d.items():
            r[k] = m.get_color_def(v)
            r[k].genesis = {'txhash': '2'}
        return r


class MockBlockchain:
    def get_tx_blockhash(self, h):
        if h == '':
            return '', False
        elif h == '1':
            return 'tmp', True
        elif h == '2' or h == '9':
            return None, True
        else:
            return 'tmp', True
    def get_tx(self, h):
        if h == 'nope':
            return None
        return MockTX(h, [1,1,1], [1,2])
    def get_best_blockhash(self):
        return '7'
    def get_mempool_txs(self):
        return [MockTX('%s' % i, [1,1,1], [1,2]) for i in range(8)]


class MockStore:
    def get_any(self, a, b):
        return [(1, 5, ''), (1, 6, '')]


class TestColorData(unittest.TestCase):

    def setUp(self):
        builder = MockBuilder()
        blockchain = MockBlockchain()
        store = MockStore()
        colormap = MockColorMap()
        self.thick = ThickColorData(builder, blockchain, store, colormap)
        self.thin = ThinColorData(builder, blockchain, store, colormap)

    def test_thick(self):
        self.assertRaises(UnfoundTransactionError, self.thick.get_colorvalues,
                          set([1,2]), '', 0)
        cvs = self.thick.get_colorvalues(set([1,2]), '1', 0)
        self.assertEquals(cvs[0].get_value(), 5)
        self.assertEquals(cvs[1].get_value(), 6)
        cvs = self.thick.get_colorvalues(set([1,2]), '2', 0)
        self.assertEquals(cvs[0].get_value(), 5)
        self.assertEquals(cvs[1].get_value(), 6)

        self.assertRaises(UnfoundTransactionError, self.thick.get_colorvalues,
                          set([1,2]), '9', 0)

    def test_thin(self):
        self.assertRaises(UnfoundTransactionError, self.thin.get_colorvalues,
                          set([1,2]), 'nope', 0)
        cvs = self.thin.get_colorvalues(set([1,2]), '1', 0)
        self.assertEquals(cvs[0].get_value(), 5)
        self.assertEquals(cvs[1].get_value(), 6)
        cvs = self.thin.get_colorvalues(set([1,2]), '2', 0)
        self.assertEquals(cvs[0].get_value(), 5)
        self.assertEquals(cvs[1].get_value(), 6)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_colordef
#!/usr/bin/env python

import random
import unittest

from coloredcoinlib.colordef import (
    EPOBCColorDefinition, OBColorDefinition,
    ColorDefinition, GenesisColorDefinition, GENESIS_OUTPUT_MARKER,
    UNCOLORED_MARKER, InvalidColorError, InvalidTargetError)
from coloredcoinlib.colorvalue import SimpleColorValue
from coloredcoinlib.txspec import ComposedTxSpec, ColorTarget

from test_txspec import MockTX, MockOpTxSpec, i2seq


class TestColorDefinition(GenesisColorDefinition):
    CLASS_CODE = 'test'


class ColorDefinitionTester():
    def __init__(self, colordef):
        self.colordef = colordef
    def test(self, inputs, outputs, in_colorvalues, txhash="not genesis", inp_seq_indices=None):
        ins = []
        for i in in_colorvalues:
            if i is None:
                ins.append(None)
            else:
                ins.append(SimpleColorValue(colordef=self.colordef, value=i))
        tx = MockTX(txhash, inputs, outputs, inp_seq_indices)
        return [i and i.get_value() for i in self.colordef.run_kernel(tx, ins)]


class TestBaseDefinition(unittest.TestCase):

    def setUp(self):
        ColorDefinition.register_color_def_class(TestColorDefinition)
        self.txhash = 'color_desc_1'
        self.cd = TestColorDefinition(1, {'txhash': self.txhash,
                                          'outindex': 0, 'height':0})
        self.tx = MockTX(self.txhash, [], [])

    def test_markers(self):
        self.assertEqual(GENESIS_OUTPUT_MARKER.__repr__(), 'Genesis')
        self.assertEqual(UNCOLORED_MARKER.__repr__(), '')

    def test_from_color_desc(self):
        cd = ColorDefinition.from_color_desc(1, "test:%s:0:0" % self.txhash)
        self.assertTrue(isinstance(cd, TestColorDefinition))

    def test_get_color_def_cls_for_code(self):
        self.assertEqual(self.cd.get_color_def_cls_for_code('test'),
                         TestColorDefinition)

    def test_is_special_tx(self):
        self.assertTrue(self.cd.is_special_tx(self.tx))

    def test_repr(self):
        a = ColorDefinition(1)
        self.assertEqual(a.__repr__(), "Color Definition with 1")
        self.assertEqual(self.cd.__repr__(), "test:color_desc_1:0:0")


class TestOBC(unittest.TestCase):

    def setUp(self):
        self.obc = OBColorDefinition(1, {'txhash': 'genesis', 'outindex': 0})
        self.genesis_tx = MockTX('genesis', [], [])
        self.tester = ColorDefinitionTester(self.obc)

    def test_run_kernel(self):
        test = self.tester.test

        # genesis
        self.assertEqual(test([1], [1], [1], "genesis"), [1])
        self.assertEqual(test([4], [1, 3], [1], "genesis"), [1, 3])

        # simple transfer
        self.assertEqual(test([1], [1], [1]), [1])
        # canonical split
        self.assertEqual(test([2, 3], [5], [2, 3]), [5])
        # canonical combine
        self.assertEqual(test([5], [2, 3], [5]), [2, 3])
        # screwed up
        self.assertEqual(test([1, 2, 3, 1], [1, 7, 1], [None, 2, 3, None]), [None, None, None])

    def test_affecting_inputs(self):
        self.assertEqual(self.obc.get_affecting_inputs(self.genesis_tx, set()),
                         set())
        tx = MockTX('other', [1,2,4,5], [2,1,7,2])
        self.assertEqual(self.obc.get_affecting_inputs(tx, set([0])),
                         set([tx.inputs[0], tx.inputs[1]]))
        self.assertEqual(self.obc.get_affecting_inputs(tx, set([0, 1])),
                         set([tx.inputs[0], tx.inputs[1]]))
        self.assertEqual(self.obc.get_affecting_inputs(tx, set([1])),
                         set([tx.inputs[1]]))
        self.assertEqual(self.obc.get_affecting_inputs(tx, set([1, 2])),
                         set([tx.inputs[1], tx.inputs[2], tx.inputs[3]]))
        self.assertEqual(self.obc.get_affecting_inputs(tx, set([2])),
                         set([tx.inputs[2], tx.inputs[3]]))
        self.assertEqual(self.obc.get_affecting_inputs(tx, set([3])),
                         set([tx.inputs[3]]))

    def test_compose_genesis_tx_spec(self):
        txspec = MockOpTxSpec([])
        cv = SimpleColorValue(colordef=UNCOLORED_MARKER, value=1)
        self.assertRaises(InvalidTargetError,
                          OBColorDefinition.compose_genesis_tx_spec, txspec)
        target = ColorTarget('addr', cv)
        txspec = MockOpTxSpec([target])
        self.assertRaises(InvalidColorError,
                          OBColorDefinition.compose_genesis_tx_spec, txspec)
        cv = SimpleColorValue(colordef=GENESIS_OUTPUT_MARKER, value=1)
        target = ColorTarget('addr', cv)
        txspec = MockOpTxSpec([target])
        self.assertTrue(isinstance(
                OBColorDefinition.compose_genesis_tx_spec(txspec),
                ComposedTxSpec))

    def test_compose_tx_spec(self):
        cv1 = SimpleColorValue(colordef=UNCOLORED_MARKER, value=1)
        cv2 = SimpleColorValue(colordef=self.obc, value=1)
        target1 = ColorTarget('addr1', cv1)
        target2 = ColorTarget('addr2', cv2)
        targets = [target1, target2]
        txspec = MockOpTxSpec(targets)
        self.assertTrue(isinstance(self.obc.compose_tx_spec(txspec),
                                   ComposedTxSpec))
        non = EPOBCColorDefinition(2, {'txhash': 'something', 'outindex': 0})
        cv3 = SimpleColorValue(colordef=non, value=1)
        target3 = ColorTarget('addr3', cv3)
        targets = [cv3, cv2]
        txspec = MockOpTxSpec(targets)
        self.assertRaises(InvalidColorError, self.obc.compose_tx_spec, txspec)

    def test_from_color_desc(self):
        cd = OBColorDefinition.from_color_desc(1, "obc:doesnmatter:0:0")
        self.assertTrue(isinstance(cd, OBColorDefinition))
        self.assertRaises(InvalidColorError, OBColorDefinition.from_color_desc,
                          1, "blah:doesnmatter:0:0")
        

class TestEPOBC(unittest.TestCase):

    def setUp(self):
        self.epobc = EPOBCColorDefinition(1, {'txhash': 'genesis',
                                              'outindex': 0, 'height': 0})
        self.tester = ColorDefinitionTester(self.epobc)
        self.tag_class = EPOBCColorDefinition.Tag

    def test_tag_closest_padding_code(self):
        self.assertEqual(self.tag_class.closest_padding_code(0), 0)
        for i in range(15):
            if i > 0:
                self.assertEqual(self.tag_class.closest_padding_code(2**i), i)
            self.assertEqual(self.tag_class.closest_padding_code(2**i+1), i+1)
        self.assertRaises(Exception,
                          self.tag_class.closest_padding_code, 2**63+1)

    def test_tag_from_nsequence(self):
        self.assertEqual(self.tag_class.from_nSequence(1), None)
        # xfer is 110011 in binary = 51
        xfer_tag = self.tag_class.from_nSequence(512 + 51)
        self.assertEqual(xfer_tag.is_genesis, False)
        self.assertEqual(xfer_tag.padding_code, 8)
        # genesis is 100101 in binary = 37
        genesis_tag = self.tag_class.from_nSequence(2048 + 37)
        self.assertEqual(genesis_tag.is_genesis, True)
        self.assertEqual(genesis_tag.padding_code, 32)

    def test_tag_to_nsequence(self):
        n = random.randint(0,63) * 64 + 51
        xfer_tag = self.tag_class.from_nSequence(n)
        self.assertEqual(xfer_tag.to_nSequence(), n)

    def test_get_tag(self):
        tx = MockTX("random", [1,1,1], [2,1], [0,1,4,5,9])
        self.assertEqual(EPOBCColorDefinition.get_tag(tx).padding_code, 8)
        def tmp():
            return True
        tx.raw.vin[0].prevout.is_null = tmp
        self.assertEqual(EPOBCColorDefinition.get_tag(tx), None)

    def test_run_kernel(self):
        # test the EPOBC color kernel
        test = self.tester.test

        # genesis
        # pad 8, direct
        self.assertEqual(test([9], [9], [1], "genesis", [0,2,5,6,7]), [1])
        # pad 32, split
        self.assertEqual(test([59], [33, 26], [1], "genesis", [0,2,5,6,8]), [1, None])
        # pad 16, join
        self.assertEqual(test([12, 5], [17], [1], "genesis", [0,2,5,8]), [1])

        # different outindex
#        self.epobc.genesis['outindex'] = 1
#        self.assertEqual(test([30], [27, 3], [1], "genesis", [0,2,5,6]), [None, 1])
#        self.epobc.genesis['outindex'] = 0

        # transfer
        xfer_8 = [0, 1, 4, 5, 6, 7]
        # pad 8, direct
        self.assertEqual(test([9], [9], [1], "xfer", xfer_8), [1])
        # pad 8, join
        self.assertEqual(test([10, 11], [13], [2, 3], "xfer", xfer_8), [5])
        # pad 8, split
        self.assertEqual(test([13], [10, 11], [5], "xfer", xfer_8), [2, 3])

        # 0's all around
        self.assertEqual(test([8, 8, 8], [8, 8, 8], [None, None, None], "xfer", xfer_8), [None, None, None])

        # null values before and after
        self.assertEqual(test([9, 10, 11, 20], [9, 13, 20], [None, 2, 3, None], "xfer", xfer_8), [None, 5, None])

        # ignore below-padding values -- DOES NOT PASS
#        self.assertEqual(test([5, 10, 11, 5], [5, 13, 5], [2, 3, None], "xfer", xfer_8), [None, 5, None])
        # color values don't add up the same
        self.assertEqual(test([9, 10, 11], [13, 15, 0], [1, 2, 3], "xfer", xfer_8), [5, None, None])
        self.assertEqual(test([9, 10, 11], [9, 15, 0], [1, 2, 3], "xfer", xfer_8), [1, None, None])
        self.assertEqual(test([9, 10, 11], [19, 9, 0], [1, 2, 3], "xfer", xfer_8), [None, None, None])

        # sum before color values is not the same
        self.assertEqual(test([5, 10, 11], [6, 13], [None, 2, 3], "xfer", xfer_8), [None, None])
        # nonnull color values are not adjacent
        self.assertEqual(test([10, 10, 10, 12, 10], [10, 32, 10], [None, 2, None, 4, None], "xfer", xfer_8), [None, None, None])
        # sequence before don't add up the same
        self.assertEqual(test([10, 10, 10, 11, 10], [15, 13, 10], [None, None, 2, 3, None], "xfer", xfer_8), [None, None, None])
        # sequence before does add up the same
        self.assertEqual(test([10, 10, 10, 11, 10], [9, 11, 13, 10], [None, None, 2, 3, None], "xfer", xfer_8), [None, None, 5, None])
        # split to many
        self.assertEqual(test([10, 10, 13, 40], [10, 10, 9, 9, 9, 9, 9, 5], [None, None, 5, None], "xfer", xfer_8), [None, None, 1, 1, 1, 1, 1, None])
        # combine many
        self.assertEqual(test([10, 9, 9, 9, 9, 9, 10], [10, 13, 32], [None, 1, 1, 1, 1, 1, None], "xfer", xfer_8), [None, 5, None])
        # split and combine
        self.assertEqual(test([10, 10, 11, 12, 13, 14, 10], [10, 13, 17, 14, 30], [None, 2, 3, 4, 5, 6, None], "xfer", xfer_8), [None, 5, 9, 6, None])
        # combine and split
        self.assertEqual(test([13, 17, 14, 30], [10, 11, 12, 13, 14, 10], [5, 9, 6, None], "xfer", xfer_8), [2, 3, 4, 5, 6, None])

    def test_compose_genesis_tx_spec(self):
        cv = SimpleColorValue(colordef=self.epobc, value=5)
        txspec = MockOpTxSpec([])
        self.assertRaises(InvalidTargetError,
                          EPOBCColorDefinition.compose_genesis_tx_spec, txspec)
        target = ColorTarget('addr', cv)
        txspec = MockOpTxSpec([target])
        self.assertRaises(InvalidColorError,
                          EPOBCColorDefinition.compose_genesis_tx_spec, txspec)

        cv = SimpleColorValue(colordef=GENESIS_OUTPUT_MARKER, value=5)
        target = ColorTarget('addr', cv)
        txspec = MockOpTxSpec([target])
        self.assertTrue(isinstance(
                EPOBCColorDefinition.compose_genesis_tx_spec(txspec),
                ComposedTxSpec))

    def test_compose_tx_spec(self):
        cv1 = SimpleColorValue(colordef=UNCOLORED_MARKER, value=10000)
        cv2 = SimpleColorValue(colordef=self.epobc, value=10000)
        targets = [ColorTarget('addr1', cv1), ColorTarget('addr1', cv2)]
        txspec = MockOpTxSpec(targets)
        self.assertTrue(isinstance(self.epobc.compose_tx_spec(txspec),
                                   ComposedTxSpec))
        cv1 = SimpleColorValue(colordef=UNCOLORED_MARKER, value=20000)
        cv2 = SimpleColorValue(colordef=self.epobc, value=20000)
        targets = [ColorTarget('addr1', cv1), ColorTarget('addr1', cv2)]
        txspec = MockOpTxSpec(targets)
        self.assertTrue(isinstance(self.epobc.compose_tx_spec(txspec),
                                   ComposedTxSpec))
        non = OBColorDefinition(2, {'txhash': 'something', 'outindex': 0})
        cv3 = SimpleColorValue(colordef=non, value=2)
        targets = [ColorTarget('addr1', cv3), ColorTarget('addr1', cv2)]
        txspec = MockOpTxSpec(targets)
        self.assertRaises(InvalidColorError, self.epobc.compose_tx_spec, txspec)

    def test_from_color_desc(self):
        cd = EPOBCColorDefinition.from_color_desc(1, "epobc:doesnmatter:0:0")
        self.assertTrue(isinstance(cd, EPOBCColorDefinition))
        self.assertRaises(InvalidColorError,
                          EPOBCColorDefinition.from_color_desc, 1,
                          "blah:doesnmatter:0:0")



if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_colormap
#!/usr/bin/env python

import unittest

from coloredcoinlib.colormap import ColorMap
from coloredcoinlib.colordef import UNCOLORED_MARKER
from coloredcoinlib.txspec import InvalidColorIdError


class MockStore:
    def __init__(self):
        self.d = {}
        self.r = {}
        for i in range(1,10):
            s = "obc:color_desc_%s:0:%s" % (i,i // 2)
            self.d[i] = s
            self.r[s] = i

    def find_color_desc(self, color_id):
        return self.d.get(color_id)

    def resolve_color_desc(self, color_desc, auto_add=True):
        return self.r.get(color_desc)


class MockColorMap(ColorMap):

    def __init__(self, mockstore=None):
        if mockstore is None:
            mockstore = MockStore()
        super(MockColorMap, self).__init__(mockstore)
        self.d = self.metastore.d


class TestColorMap(unittest.TestCase):

    def setUp(self):
        self.colormap = MockColorMap()

    def test_find_color_desc(self):
        self.assertEqual(self.colormap.find_color_desc(0), "")
        self.assertEqual(self.colormap.find_color_desc(1),
                         "obc:color_desc_1:0:0")

    def test_resolve_color_desc(self):
        self.assertEqual(self.colormap.resolve_color_desc(""), 0)
        self.assertEqual(self.colormap.resolve_color_desc(
                "obc:color_desc_1:0:0"), 1)

    def test_get_color_def(self):
        self.assertEqual(self.colormap.get_color_def(0), UNCOLORED_MARKER)
        self.assertEqual(self.colormap.get_color_def(1).get_color_id(), 1)
        self.assertEqual(self.colormap.get_color_def(
                "obc:color_desc_1:0:0").get_color_id(), 1)
        self.assertRaises(InvalidColorIdError, self.colormap.get_color_def, 11)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_colorset
#!/usr/bin/env python

import unittest

from coloredcoinlib import ColorSet
from test_colormap import MockColorMap


class TestColorSet(unittest.TestCase):

    def setUp(self):
        self.colormap = MockColorMap()
        d = self.colormap.d
        self.colorset0 = ColorSet(self.colormap, [''])
        self.colorset1 = ColorSet(self.colormap, [d[1]])
        self.colorset2 = ColorSet(self.colormap, [d[2]])
        self.colorset3 = ColorSet(self.colormap, [d[1], d[2]])
        self.colorset4 = ColorSet(self.colormap, [d[3], d[2]])
        self.colorset5 = ColorSet(self.colormap, [d[3], d[1]])
        self.colorset6 = ColorSet(self.colormap, [])

    def test_repr(self):
        self.assertEquals(self.colorset0.__repr__(), "['']")
        self.assertEquals(self.colorset1.__repr__(),
                          "['obc:color_desc_1:0:0']")
        self.assertEquals(self.colorset3.__repr__(),
                          "['obc:color_desc_1:0:0', 'obc:color_desc_2:0:1']")

    def test_uncolored_only(self):
        self.assertTrue(self.colorset0.uncolored_only())
        self.assertFalse(self.colorset1.uncolored_only())
        self.assertFalse(self.colorset3.uncolored_only())

    def test_get_data(self):
        self.assertEquals(self.colorset0.get_data(), [""])
        self.assertEquals(self.colorset1.get_data(), ["obc:color_desc_1:0:0"])

    def test_get_hash_string(self):
        self.assertEquals(self.colorset0.get_hash_string(), "055539df4a0b804c58caf46c0cd2941af10d64c1395ddd8e50b5f55d945841e6")
        self.assertEquals(self.colorset1.get_hash_string(), "ca90284eaa79e05d5971947382214044fe64f1bdc2e97040cfa9f90da3964a14")
        self.assertEquals(self.colorset3.get_hash_string(), "09f731f25cf5bfaad512d4ee6f37cb9481f442df3263b15725dd1624b4678557")

    def test_get_earliest(self):
        self.assertEquals(self.colorset5.get_earliest(), "obc:color_desc_1:0:0")
        self.assertEquals(self.colorset4.get_earliest(), "obc:color_desc_2:0:1")
        self.assertEquals(self.colorset6.get_earliest(), "\x00\x00\x00\x00")

    def test_get_color_string(self):
        self.assertEquals(self.colorset1.get_color_hash(), "CP4YWLr8aAe4Hn")
        self.assertEquals(self.colorset3.get_color_hash(), "ZUTSoEEwZY6PB")

    def test_has_color_id(self):
        self.assertTrue(self.colorset0.has_color_id(0))
        self.assertTrue(self.colorset3.has_color_id(1))
        self.assertFalse(self.colorset1.has_color_id(0))
        self.assertFalse(self.colorset4.has_color_id(1))

    def test_intersects(self):
        self.assertFalse(self.colorset0.intersects(self.colorset1))
        self.assertTrue(self.colorset1.intersects(self.colorset3))
        self.assertTrue(self.colorset3.intersects(self.colorset1))
        self.assertTrue(self.colorset4.intersects(self.colorset3))
        self.assertFalse(self.colorset2.intersects(self.colorset0))
        self.assertFalse(self.colorset1.intersects(self.colorset4))

    def test_equals(self):
        self.assertFalse(self.colorset1.equals(self.colorset0))
        self.assertTrue(self.colorset3.equals(self.colorset3))
        self.assertFalse(self.colorset4.equals(self.colorset5))
        
    def test_from_color_ids(self):
        self.assertTrue(self.colorset0.equals(
                ColorSet.from_color_ids(self.colormap, [0])))
        self.assertTrue(self.colorset3.equals(
                ColorSet.from_color_ids(self.colormap, [1,2])))
        tmp = ColorSet.from_color_ids(self.colormap, [1,2,3])
        self.assertTrue(tmp.has_color_id(1))
        self.assertTrue(tmp.has_color_id(2))
        self.assertTrue(tmp.has_color_id(3))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_colorvalue
#!/usr/bin/env python

import unittest

from coloredcoinlib.colorvalue import (SimpleColorValue,
                                       IncompatibleTypesError)
from coloredcoinlib.colordef import POBColorDefinition, OBColorDefinition

 
class TestColorValue(unittest.TestCase):
    def setUp(self):
        self.colordef1 = POBColorDefinition(
            1, {'txhash': 'genesis', 'outindex': 0})
        self.colordef2 = OBColorDefinition(
            2, {'txhash': 'genesis', 'outindex': 0})
        self.cv1 = SimpleColorValue(colordef=self.colordef1,
                                    value=1, label='test')
        self.cv2 = SimpleColorValue(colordef=self.colordef1,
                                    value=2, label='test2')
        self.cv3 = SimpleColorValue(colordef=self.colordef2,
                                    value=1)

    def test_add(self):
        cv4 = self.cv1 + self.cv2
        self.assertEqual(cv4.get_value(), 3)
        cv4 = 0 + self.cv1
        self.assertEqual(cv4.get_value(), 1)
        self.assertRaises(IncompatibleTypesError, self.cv1.__add__,
                          self.cv3)

    def test_iadd(self):
        cv = self.cv1.clone()
        cv += self.cv2
        self.assertEqual(cv.get_value(), 3)

    def test_sub(self):
        cv = self.cv2 - self.cv1
        self.assertEqual(cv.get_value(), 1)

    def test_lt(self):
        self.assertTrue(self.cv1 < self.cv2)
        self.assertTrue(self.cv2 > self.cv1)
        self.assertTrue(self.cv2 >= self.cv1)
        self.assertTrue(self.cv2 > 0)

    def test_eq(self):
        self.assertTrue(self.cv1 == self.cv1)
        self.assertTrue(self.cv1 != self.cv2)
        self.assertTrue(self.cv1 != self.cv3)

    def test_label(self):
        self.assertEqual(self.cv1.get_label(), 'test')

    def test_repr(self):
        self.assertEqual(self.cv1.__repr__(), 'test: 1')

    def test_sum(self):
        cvs = [self.cv1, self.cv2, SimpleColorValue(colordef=self.colordef1,
                                                    value=3)]
        self.assertEqual(SimpleColorValue.sum(cvs).get_value(), 6)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_store
#!/usr/bin/env python

import os
import unittest

from coloredcoinlib.store import (DataStoreConnection, ColorDataStore,
                                  ColorMetaStore, PersistentDictStore)


class TestStore(unittest.TestCase):
    def setUp(self):
        self.dsc = DataStoreConnection(":memory:")
        self.store = ColorDataStore(self.dsc.conn)
        self.persistent = PersistentDictStore(self.dsc.conn, 'per')
        self.meta = ColorMetaStore(self.dsc.conn)

    def test_autocommit(self):
        path = "/tmp/tmp.db"
        c = DataStoreConnection(path, True)
        self.assertFalse(c.conn.isolation_level)
        os.remove(path)

    def test_table_exists(self):
        self.assertFalse(self.store.table_exists('notthere'))

    def test_sync(self):
        self.assertFalse(self.store.sync())

    def test_transaction(self):
        self.assertEqual(self.store.transaction(), self.dsc.conn)

    def test_colordata(self):
        self.assertFalse(self.store.get(1, "1", 0))
        self.assertFalse(self.store.get_any("1", 0))
        self.assertFalse(self.store.get_all(1))
        self.store.add(1, "1", 0, 1, "test0")
        self.assertTrue(self.store.get(1, "1", 0))
        self.assertTrue(self.store.get_any("1", 0))
        self.assertTrue(self.store.get_all(1))
        self.store.remove(1, "1", 0)
        self.assertFalse(self.store.get(1, "1", 0))
        self.assertFalse(self.store.get_any("1", 0))
        self.assertFalse(self.store.get_all(1))

    def test_persistent(self):
        self.assertFalse(self.persistent.get("tmp"))
        self.persistent['tmp'] = 1
        self.assertTrue(self.persistent.get("tmp"))
        self.assertEqual(self.persistent.keys(), ['tmp'])
        del self.persistent['tmp']
        self.assertFalse(self.persistent.get("tmp"))
        self.assertRaises(KeyError, self.persistent.__delitem__, 'tmp')

    def test_meta(self):
        self.assertFalse(self.meta.did_scan(1, "hash"))
        self.meta.set_as_scanned(1, "hash")
        self.assertTrue(self.meta.did_scan(1, "hash"))
        self.assertFalse(self.meta.find_color_desc(1))
        self.meta.resolve_color_desc("color", True)
        self.assertTrue(self.meta.find_color_desc(1))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_toposort
#!/usr/bin/env python

import os
import unittest

from coloredcoinlib.toposort import toposorted


class TestSort(unittest.TestCase):
    def setUp(self):
        self.a = 'a'
        self.b = 'b'
        self.l = [self.a, self.b]

    def test_toposort(self):
        def get_all(x):
            return self.l
        self.assertRaises(ValueError, toposorted, self.l, get_all)
        def get_a(x):
            if x == 'a':
                return ['b']
            return []
        self.assertEquals(toposorted(self.l, get_a), ['b', 'a'])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_txspec
#!/usr/bin/env python

import unittest

from coloredcoinlib.colorvalue import SimpleColorValue
from coloredcoinlib.colordef import (UNCOLORED_MARKER, OBColorDefinition,
                                     EPOBCColorDefinition)
from coloredcoinlib.txspec import (ColorTarget, OperationalTxSpec,
                                   ComposedTxSpec)


class MicroMock(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.prevout = MockTXIn('2', 1)


class MockTXIn(object):
    def __init__(self, h, n):
        self.hash = h
        self.n = n
    def is_null(self):
        return False

class MockTXElement:
    def __init__(self, value, inp_seq_indices=None):
        self.value = value
        self.prevout = MockTXIn('2', 1)
        if inp_seq_indices is None:
            inp_seq_indices = [0,1,4,5,6,7]
        self.prevtx = MockTX('tmp', [], [], inp_seq_indices)
    def __repr__(self):
        return "<MockTXElement: %s>" % self.value


def i2seq(i):
    if i is None:
        return 0
    return 2**(i)


class MockRawTX:
    def __init__(self, inp_seq_indices):
        nSequence = 0
        for i in inp_seq_indices:
            nSequence += i2seq(i)
        self.vin = [MicroMock(nSequence=nSequence)]


class MockTX:
    def __init__(self, h, inputs, outputs, inp_seq_indices=None, prev_seq_indices=None):
        self.hash = h
        self.inputs = [MockTXElement(satoshis, prev_seq_indices) for satoshis in inputs]
        self.outputs = [MockTXElement(satoshis) for satoshis in outputs]
        self.raw = MockRawTX(inp_seq_indices or [None for _ in inputs])
    def ensure_input_values(self):
        pass


class MockUTXO(ComposedTxSpec.TxIn):
    def __init__(self, colorvalues):
        self.colorvalues = colorvalues
        self.value = sum([cv.get_value() for cv in colorvalues])
    def set_nSequence(self, nSequence):
        self.nSequence = nSequence


class MockOpTxSpec(OperationalTxSpec):
    def __init__(self, targets):
        self.targets = targets
    def get_targets(self):
        return self.targets
    def get_required_fee(self, amount):
        return SimpleColorValue(colordef=UNCOLORED_MARKER, value=10000)
    def get_change_addr(self, addr):
        return 'changeaddr'
    def get_dust_threshold(self):
        return SimpleColorValue(colordef=UNCOLORED_MARKER, value=10000)
    def select_coins(self, colorvalue, use_fee_estimator=None):
        cvs = [
            SimpleColorValue(colordef=colorvalue.get_colordef(), value=10000),
            SimpleColorValue(colordef=colorvalue.get_colordef(), value=20000),
            SimpleColorValue(colordef=colorvalue.get_colordef(), value=10000),
            SimpleColorValue(colordef=colorvalue.get_colordef(), value=10000)
            ]
        s = SimpleColorValue.sum(cvs)
        return [MockUTXO([cv]) for cv in cvs], s


class TestTxSpec(unittest.TestCase):
    def setUp(self):
        self.colordef1 = EPOBCColorDefinition(
            1, {'txhash': 'genesis', 'outindex': 0})
        self.colordef2 = OBColorDefinition(
            2, {'txhash': 'genesis', 'outindex': 0})
        self.cv1 = SimpleColorValue(colordef=self.colordef1,
                                    value=1, label='test')
        self.cv2 = SimpleColorValue(colordef=self.colordef1,
                                    value=2, label='test2')
        self.cv3 = SimpleColorValue(colordef=self.colordef2,
                                    value=1)
        self.ct1 = ColorTarget('address1', self.cv1)
        self.ct2 = ColorTarget('address2', self.cv2)
        self.ct3 = ColorTarget('address3', self.cv3)
        self.txspec = MockOpTxSpec([self.ct1, self.ct2])

    def test_repr(self):
        self.assertEqual(self.ct1.__repr__(), 'address1: test: 1')

    def test_get_colordef(self):
        self.assertEqual(self.ct1.get_colordef(), self.colordef1)

    def test_get_value(self):
        self.assertEqual(self.ct1.get_value(), self.cv1.get_value())

    def test_sum(self):
        cts = [self.ct1, self.ct2, ColorTarget('address3',self.cv2)]
        self.assertEqual(ColorTarget.sum(cts).get_value(), 5)
        self.assertEqual(ColorTarget.sum([]), 0)

    def test_opspec(self):
        self.assertTrue(self.txspec.is_monocolor())
        spec = MockOpTxSpec([self.ct1, self.ct2, self.ct3])
        self.assertFalse(spec.is_monocolor())

    def test_cspec(self):
        txo1 = ComposedTxSpec.TxOut(1, 'addr')
        txo2 = ComposedTxSpec.TxOut(2, 'addr2')
        outs = [txo1, txo2]
        c = ComposedTxSpec(None)
        c.add_txins([])
        c.add_txouts([txo1, txo2])
        self.assertEqual(c.get_txins(), [])
        self.assertEqual(c.get_txouts(), outs)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = toposort

def toposorted(graph, parents):
    """
    Returns vertices of a directed acyclic graph in topological order.

    Arguments:
    graph -- vetices of a graph to be toposorted
    parents -- function (vertex) -> vertices to preceed
               given vertex in output
    """
    result = []
    used = set()

    def use(v, top):
        if id(v) in used:
            return
        for parent in parents(v):
            if parent is top:
                raise ValueError('graph is cyclical', graph)
            use(parent, v)
        used.add(id(v))
        result.append(v)
    for v in graph:
        use(v, v)
    return result

########NEW FILE########
__FILENAME__ = txspec
""" Transaction specification language """

from blockchain import CTxIn
from colorvalue import ColorValue


class InvalidColorIdError(Exception):
    pass


class ZeroSelectError(Exception):
    pass


class ColorTarget(object):
    def __init__(self, address, colorvalue):
        self.address = address
        self.colorvalue = colorvalue

    def get_colordef(self):
        return self.colorvalue.get_colordef()

    def get_color_id(self):
        return self.colorvalue.get_color_id()

    def is_uncolored(self):
        return self.colorvalue.is_uncolored()

    def get_address(self):
        return self.address

    def get_value(self):
        return self.colorvalue.get_value()

    def get_satoshi(self):
        return self.colorvalue.get_satoshi()

    def __repr__(self):
        return "%s: %s" % (self.get_address(), self.colorvalue)

    @classmethod
    def sum(cls, targets):
        if len(targets) == 0:
            return 0
        c = targets[0].colorvalue.__class__
        return c.sum([t.colorvalue for t in targets])


class OperationalTxSpec(object):
    """transaction specification which is ready to be operated on
       (has all the necessary data)"""
    def get_targets(self):
        """returns a list of ColorTargets"""
        raise Exception('not implemented')  # pragma: no cover

    def select_coins(self, colorvalue, use_fee_estimator=None):
        """returns a list of UTXO objects with whose colordef is
        the same as <colorvalue> and have a sum colorvalues
        have at least the <colorvalue>.
        For uncolored coins sum of values of UTXO objects must
        also include a fee (if <use_fee_estimator> parameter is 
        provided, usually it is composed_tx_spec)."""
        raise Exception('not implemented')  # pragma: no cover

    def get_change_addr(self, color_def):
        """returns an address which can be used as
           a change for this color_def"""
        raise Exception('not implemented')  # pragma: no cover

    def get_required_fee(self, tx_size):
        """returns ColorValue object representing the fee for
        a certain tx size"""
        raise Exception('not implemented')  # pragma: no cover

    def get_dust_threshold(self):
        """returns ColorValue object representing smallest 
        satoshi value which isn't dust according to current
        parameters"""
        raise Exception('not implemented')  # pragma: no cover

    def is_monocolor(self):
        targets = self.get_targets()
        color_def = targets[0].get_colordef()
        for target in targets[1:]:
            if target.get_colordef() is not color_def:
                return False
        return True

    def make_composed_tx_spec(self):
        return ComposedTxSpec(self)


class ComposedTxSpec(object):
    """specification of a transaction which is already composed,
       but isn't signed yet"""

    class TxIn(CTxIn):
        pass

    class TxOut(object):
        __slots__ = ['value', 'target_addr']

        def __init__(self, value, target_addr):
            self.value = value
            self.target_addr = target_addr

    class FeeChangeTxOut(TxOut):
        pass

    def __init__(self, operational_tx_spec=None):
        self.txins = []
        self.txouts = []
        self.operational_tx_spec = operational_tx_spec

    def add_txin(self, txin):
        assert isinstance(txin, self.TxIn)
        self.txins.append(txin)

    def add_txout(self, txout=None, value=None, target_addr=None, 
                  target=None, is_fee_change=False):
        if not txout:
            if not value:
                if target and target.is_uncolored():
                    value = target.get_value()
                else:
                    raise Exception("error in ComposedTxSpec.add_txout: no\
value is provided and target is not uncolored")
            if isinstance(value, ColorValue):
                if value.is_uncolored():
                    value = value.get_value()
                else:
                    raise Exception("error in ComposedTxSpec.add_txout: no\
value isn't uncolored")
            if not target_addr:
                target_addr = target.get_address()      
            cls = self.FeeChangeTxOut if is_fee_change else self.TxOut
            txout = cls(value, target_addr)
        self.txouts.append(txout)

    def add_txouts(self, txouts):
        for txout in txouts:
            if isinstance(txout, ColorTarget):
                self.add_txout(target=txout)
            elif isinstance(txout, self.TxOut):
                self.add_txout(txout=txout)
            else:
                raise Exception('wrong txout instance')

    def add_txins(self, txins):
        for txin in txins:
            self.add_txin(txin)

    def get_txins(self):
        return self.txins

    def get_txouts(self):
        return self.txouts

    def estimate_size(self, extra_txins=0, extra_txouts=0, extra_bytes=0):
        return (181 * (len(self.txins) + extra_txins) + 
                34 * (len(self.txouts) + extra_txouts) + 
                10 + extra_bytes)

    def estimate_required_fee(self, extra_txins=0, extra_txouts=1, extra_bytes=0):
        return self.operational_tx_spec.get_required_fee(
            self.estimate_size(extra_txins=extra_txins,
                               extra_txouts=extra_txouts,
                               extra_bytes=extra_bytes))

    def get_fee(self):
        sum_txins = sum([inp.value 
                         for inp in self.txins])
        sum_txouts = sum([out.value
                          for out in self.txouts])
        return sum_txins - sum_txouts

########NEW FILE########
__FILENAME__ = install_https
#!/usr/bin/env python
import urllib2
import httplib
import ssl
import socket
import os
import sys

try:
    main_file = os.path.abspath(sys.modules['__main__'].__file__)
except AttributeError:
    main_file = sys.executable
CERT_FILE = os.path.join(os.path.dirname(main_file), 'cacert.pem')


class ValidHTTPSConnection(httplib.HTTPConnection):
        "This class allows communication via SSL."

        default_port = httplib.HTTPS_PORT

        def __init__(self, *args, **kwargs):
            httplib.HTTPConnection.__init__(self, *args, **kwargs)

        def connect(self):
            "Connect to a host on a given (SSL) port."

            sock = socket.create_connection((self.host, self.port),
                                            self.timeout, self.source_address)
            if self._tunnel_host:
                self.sock = sock
                self._tunnel()
            self.sock = ssl.wrap_socket(sock,
                                        ca_certs=CERT_FILE,
                                        cert_reqs=ssl.CERT_REQUIRED)


class ValidHTTPSHandler(urllib2.HTTPSHandler):

    def https_open(self, req):
            return self.do_open(ValidHTTPSConnection, req)

urllib2.install_opener(urllib2.build_opener(ValidHTTPSHandler))

if __name__ == "__main__": 
        def test_access(url):
                print "Acessing", url
                page = urllib2.urlopen(url)
                print page.info()
                data = page.read()
                print "First 100 bytes:", data[0:100]
                print "Done accesing", url
                print ""

        # This should work
        test_access("https://blockchain.info")
        test_access("http://www.google.com")
        # Accessing a page with a self signed certificate should not work
        # At the time of writing, the following page uses a self signed certificate
        test_access("https://tidia.ita.br/")

########NEW FILE########
__FILENAME__ = ngccc-cli
#!/usr/bin/env python

"""
ngccc-cli.py

command-line interface to the Next-Generation Colored Coin Client
You can manage your colored coins using this command.
"""

import install_https
import argparse
import os
import json
import logging

from ngcccbase.wallet_controller import WalletController
from ngcccbase.pwallet import PersistentWallet
from ngcccbase.logger import setup_logging


class _ApplicationHelpFormatter(argparse.HelpFormatter):
    def add_usage(self, usage, actions, groups, prefix=None):
        argparse.HelpFormatter.add_usage(self, usage, None, groups, prefix)

    def add_argument(self, action):
        if isinstance(action, argparse._SubParsersAction):
            self._add_item(self._format_subparsers, [action])
        else:
            argparse.HelpFormatter.add_argument(self, action)

    def _format_subparsers(self, action):
        max_action_width = max(
            [len(x) for x in action._name_parser_map.keys()])

        parts = []
        for name, subaction in action._name_parser_map.items():
            parts.append("  {name: <{max_action_width}}  {desc}".format(
                name=name,
                desc=subaction.description,
                max_action_width=max_action_width))

        return '\n'.join(parts)


class Application(object):
    def __init__(self):
        setup_logging()
        self.data = {}
        self.args = None
        self.parser = argparse.ArgumentParser(
            description="Next-Generation Colored Coin Client "
            "Command-line interface",
            formatter_class=_ApplicationHelpFormatter)

        self.parser.add_argument("--wallet", dest="wallet_path")
        self.parser.add_argument("--testnet", action="store_true")

        subparsers = self.parser.add_subparsers(
            title='subcommands', dest='command')

        parser = subparsers.add_parser(
            'import_config', description="Import json config.")
        parser.add_argument('path', type=self.validate_import_config_path)

        parser = subparsers.add_parser(
            'setval', description="Sets a value in the configuration.")
        parser.add_argument('key')
        parser.add_argument('value', type=self.validate_JSON_decode)

        parser = subparsers.add_parser(
            'getval', description=
            "Returns the value for a given key in the config.")
        parser.add_argument('key')

        parser = subparsers.add_parser(
            'dump_config', description=
            "Returns a JSON dump of the current configuration.")

        parser = subparsers.add_parser(
            'addasset', description="Imports a color definition.")
        parser.add_argument('moniker')
        parser.add_argument('color_desc')
        parser.add_argument('unit', type=int)

        parser = subparsers.add_parser(
            'issue', description="Starts a new color.")
        parser.add_argument('moniker')
        parser.add_argument('coloring_scheme')
        parser.add_argument('units', type=int)
        parser.add_argument('atoms', type=int)

        parser = subparsers.add_parser(
            'newaddr', description=
            "Creates a new bitcoin address for a given asset/color.")
        parser.add_argument('moniker')

        parser = subparsers.add_parser(
            'alladdresses', description=
            "Lists all addresses for a given asset/color.")
        parser.add_argument('moniker')

        parser = subparsers.add_parser(
            'privatekeys', description=
            "Lists all private keys for a given asset/color.")
        parser.add_argument('moniker')

        parser = subparsers.add_parser(
            'allassets', description="Lists all assets registered.")

        parser = subparsers.add_parser(
            'balance', description=
            "Returns the balance in Satoshi for a particular asset/color.")
        parser.add_argument('moniker')
        parser.add_argument('--unconfirmed', action='store_true')
        parser.add_argument('--available', action='store_true')

        parser = subparsers.add_parser(
            'received_by_address', description=
            "Returns total received amount for each address "
            "of a particular asset/color.")
        parser.add_argument('moniker')

        parser = subparsers.add_parser(
            'coinlog', description=
            "Returns the coin transaction log for this wallet.")

        parser = subparsers.add_parser(
            'send', description=
            "Send some amount of an asset/color to an address.")
        parser.add_argument('moniker')
        parser.add_argument('address')
        parser.add_argument('value')

        parser = subparsers.add_parser(
            'scan', description=
            "Check for received payments (unspent transaction outputs).")

        parser = subparsers.add_parser(
            'full_rescan', description=
            "Rebuild information about unspent outputs and wallet transactions.")

        parser = subparsers.add_parser(
            'history', description="Shows the history of transactions "
            "for a particular asset/color in your wallet.")
        parser.add_argument('moniker')

        parser = subparsers.add_parser(
            'p2p_show_orders', description="Show p2ptrade orders")
        parser.add_argument('moniker')

        parser = subparsers.add_parser(
            'p2p_sell', description="sell via p2ptrade")
        parser.add_argument('moniker')
        parser.add_argument('value')
        parser.add_argument('price')

        parser = subparsers.add_parser(
            'p2p_buy', description="buy via p2ptrade")
        parser.add_argument('moniker')
        parser.add_argument('value')
        parser.add_argument('price')

    def __getattribute__(self, name):
        if name in ['controller', 'model', 'wallet']:
            if name in self.data:
                return self.data[name]
            if name == 'wallet':
                wallet = PersistentWallet(self.args.get('wallet_path'),
                                          self.args.get('testnet'))
                self.data['wallet'] = wallet
                return wallet
            else:
                self.wallet.init_model()
                self.data['model'] = self.data['wallet'].get_model()
                self.data['controller'] = WalletController(self.data['model'])
                return self.data[name]
        return object.__getattribute__(self, name)

    def get_asset_definition(self, moniker):
        """Helper method for many other commands.
        Returns an AssetDefinition object from wallet_model.py.
        """
        adm = self.model.get_asset_definition_manager()
        asset = adm.get_asset_by_moniker(moniker)
        if asset:
            return asset
        else:
            raise Exception("asset not found")

    def validate_import_config_path(self, path):
        return self.validate_JSON_decode(self.validate_file_read(path))

    def validate_file_read(self, path):
        try:
            with open(path, 'r') as fp:
                return fp.read()
        except IOError:
            msg = "Can't read file: %s." % path
            raise argparse.ArgumentTypeError(msg)

    def validate_JSON_decode(self, s):
        try:
            return json.loads(s)
        except ValueError:
            msg = "No JSON object could be decoded: %s." % s
            raise argparse.ArgumentTypeError(msg)

    def validate_config_key(self, key):
        wc = self.wallet.wallet_config
        try:
            for name in key.split('.'):
                wc = wc[name]
        except KeyError:
            msg = "Can't find the key: %s." % key
            raise argparse.ArgumentTypeError(msg)
        return key

    def start(self):
        args = vars(self.parser.parse_args())
        self.args = args
        if 'command' in args:
            getattr(self, "command_{command}".format(**args))(**args)

    def command_import_config(self, **kwargs):
        """Special command for importing a JSON config.
        """
        # conversion happens at time of validation
        imp_config = kwargs['path']
        wallet_config = self.wallet.wallet_config
        for k in imp_config:
            wallet_config[k] = imp_config[k]

    def command_setval(self, **kwargs):
        """Sets a value in the configuration.
        Key is expressed like so: key.subkey.subsubkey
        """
        keys = kwargs['key'].split('.')
        value = kwargs['value']
        wc = self.wallet.wallet_config
        if len(keys) > 1:
            branch = wc[keys[0]]
            cdict = branch
            for key in keys[1:-1]:
                cdict = cdict[key]
            cdict[keys[-1]] = value
            value = branch
        wc[keys[0]] = value

    def command_getval(self, **kwargs):
        """Returns the value for a given key in the config.
        Key is expressed like so: key.subkey.subsubkey
        """
        wc = self.wallet.wallet_config
        for name in kwargs['key'].split('.'):
            wc = wc[name]
        print (json.dumps(wc, indent=4))

    def command_dump_config(self, **kwargs):
        """Returns a JSON dump of the current configuration.
        """
        config = self.wallet.wallet_config
        dict_config = dict(config.iteritems())
        print (json.dumps(dict_config, indent=4))

    def command_addasset(self, **kwargs):
        """Imports a color definition. This is useful if someone else has
        issued a color and you want to be able to receive it.
        """
        self.controller.add_asset_definition({
            "monikers": [kwargs['moniker']],
            "color_set": [kwargs['color_desc']],
            "unit": kwargs['unit']
        })

    def command_issue(self, **kwargs):
        """Starts a new color based on <coloring_scheme> with
        a name of <moniker> with <units> per share and <atoms>
        total shares.
        """
        self.controller.issue_coins(
            kwargs['moniker'], kwargs['coloring_scheme'],
            kwargs['units'], kwargs['atoms'])

    def command_newaddr(self, **kwargs):
        """Creates a new bitcoin address for a given asset/color.
        """
        asset = self.get_asset_definition(kwargs['moniker'])
        addr = self.controller.get_new_address(asset)
        print (addr.get_color_address())

    def command_alladdresses(self, **kwargs):
        """Lists all addresses for a given asset/color
        """
        asset = self.get_asset_definition(kwargs['moniker'])
        for addr in self.controller.get_all_addresses(asset):
            print (addr.get_color_address())

    def command_privatekeys(self, **kwargs):
        """Lists all private keys for a given asset/color
        """
        asset = self.get_asset_definition(kwargs['moniker'])
        for addr in self.controller.get_all_addresses(asset):
            print (addr.get_private_key())

    def command_allassets(self, **kwargs):
        """Lists all assets (moniker/color_hash) registered
        """
        for asset in self.controller.get_all_assets():
            print ("%s: %s" % (', '.join(asset.monikers),
                              asset.get_color_set().get_color_hash()))

    def command_received_by_address(self, **kwargs):
        """Returns the balance in Satoshi for a particular asset/color.
        "bitcoin" is the generic uncolored coin.
        """
        asset = self.get_asset_definition(kwargs['moniker'])
        for row in self.controller.get_received_by_address(asset):
            print ("%s: %s" % (row['color_address'],
                              asset.format_value(row['value'])))

    def command_coinlog(self, **kwargs):
        """Returns the entire contents of the coin_data table.
        """
        moniker = ''
        for coin in self.controller.get_coinlog():
            if coin.asset.get_monikers()[0] != moniker:
                moniker = coin.asset.get_monikers()[0]
                print "-" * 79
                print moniker
                print "-" * 79
            print ("%s %s:%s %s (%s) %s %s" % (
                    coin.get_address(), coin.txhash, coin.outindex,
                    coin.colorvalues[0], coin.value,
                    coin.is_confirmed(), coin.get_spending_txs()))

    def command_balance(self, **kwargs):
        """Returns the balance in Satoshi for a particular asset/color.
        "bitcoin" is the generic uncolored coin.
        """
        asset = self.get_asset_definition(kwargs['moniker'])
        fn = self.controller.get_total_balance
        if kwargs['unconfirmed']:
            fn = self.controller.get_unconfirmed_balance
        if kwargs['available']:
            fn = self.controller.get_available_balance
        print (asset.format_value(fn(asset)))

    def command_send(self, **kwargs):
        """Send some amount of an asset/color to an address
        """
        asset = self.get_asset_definition(kwargs['moniker'])
        value = asset.parse_value(kwargs['value'])
        self.controller.send_coins(asset, [kwargs['address']], [value])

    def command_scan(self, **kwargs):
        """Update the database of transactions (amount in each address).
        """
        self.controller.scan_utxos()

    def command_full_rescan(self, **kwargs):
        """Update the database of transactions (amount in each address).
        """
        self.controller.full_rescan()


    def command_history(self, **kwargs):
        """print the history of transactions for this color
        """
        asset = self.get_asset_definition(moniker=kwargs['moniker'])
        history = self.controller.get_history(asset)
        for item in history:
            mempool = "(mempool)" if item['mempool'] else ""
            print ("%s %s %s %s" % (
                item['action'], item['value'], item['address'], mempool))

    def init_p2ptrade(self):
        from ngcccbase.p2ptrade.ewctrl import EWalletController
        from ngcccbase.p2ptrade.agent import EAgent
        from ngcccbase.p2ptrade.comm import HTTPComm

        ewctrl = EWalletController(self.model, self.controller)
        config = {"offer_expiry_interval": 30,
                  "ep_expiry_interval": 30}
        comm = HTTPComm(
            config, 'http://p2ptrade.btx.udoidio.info/messages')
        agent = EAgent(ewctrl, config, comm)
        return agent

    def p2ptrade_make_offer(self, we_sell, params):
        from ngcccbase.p2ptrade.protocol_objects import MyEOffer
        asset = self.get_asset_definition(params['moniker'])
        value = asset.parse_value(params['value'])
        bitcoin = self.get_asset_definition('bitcoin')
        price = bitcoin.parse_value(params['price'])
        total = int(float(value)/float(asset.unit)*float(price))
        color_desc = asset.get_color_set().color_desc_list[0]
        sell_side = {"color_spec": color_desc, "value": value}
        buy_side = {"color_spec": "", "value": total}
        if we_sell:
            return MyEOffer(None, sell_side, buy_side)
        else:
            return MyEOffer(None, buy_side, sell_side)

    def p2ptrade_wait(self, agent):
        #  TODO: use config/parameters
        for _ in xrange(30):
            agent.update()

    def command_p2p_show_orders(self, **kwargs):
        agent = self.init_p2ptrade()
        agent.update()
        for offer in agent.their_offers.values():
            print (offer.get_data())

    def command_p2p_sell(self, **kwargs):
        agent = self.init_p2ptrade()
        offer = self.p2ptrade_make_offer(True, kwargs)
        agent.register_my_offer(offer)
        self.p2ptrade_wait(agent)

    def command_p2p_buy(self, **kwargs):
        agent = self.init_p2ptrade()
        offer = self.p2ptrade_make_offer(False, kwargs)
        agent.register_my_offer(offer)
        self.p2ptrade_wait(agent)


if __name__ == "__main__":
    Application().start()

########NEW FILE########
__FILENAME__ = ngccc-gui
#!/usr/bin/env python

"""
ngccc-gui.py

QT interface to the Next-Generation Colored Coin Client
This command will start a GUI interface.

Note that this requires the install of PyQt4 and PIP.
Neither of those are accessible by pip.
Use this command in ubuntu to install:
   apt-get install python-qtp python-sip
"""

from ngcccbase.logger import setup_logging
import install_https
from ui.qtui import QtUI

def start_ui():
    QtUI()

setup_logging()
start_ui()

########NEW FILE########
__FILENAME__ = ngccc-server
#!/usr/bin/env python

"""
ngccc-server.py

JSON-RPC interface to the Next-Generation Colored Coin Client
This command will start a server at hostname/port that takes
in JSON-RPC commands for execution.
"""

import install_https
from ngcccbase.rpc_interface import RPCRequestHandler
from BaseHTTPServer import HTTPServer
import sys
import getopt

from ngcccbase.logger import setup_logging

setup_logging()

args = []

# grab the hostname and port from the command-line
try:
    opts, args = getopt.getopt(sys.argv[1:], "", "")
except getopt.GetoptError:
    pass

if len(args) != 2:
    print ("Error: parameters are required")
    print ("python ngccc-server.py hostname port")
    sys.exit(2)

hostname = args[0]
port = int(args[1])

# create a server to accept the JSON-RPC requests
http_server = HTTPServer(
    server_address=(hostname, port), RequestHandlerClass=RPCRequestHandler
)

# start the server
print ("Starting HTTP server on http://%s:%s" % (hostname, port))
http_server.serve_forever()

########NEW FILE########
__FILENAME__ = ngccc
ngccc-cli.py
########NEW FILE########
__FILENAME__ = address
from pycoin.ecdsa.secp256k1 import generator_secp256k1 as BasePoint
from pycoin.encoding import (b2a_hashed_base58, from_bytes_32, to_bytes_32, 
                             a2b_hashed_base58, public_pair_to_bitcoin_address,
                             public_pair_to_hash160_sec, secret_exponent_to_wif)


class InvalidAddressError(Exception):
    pass


class AddressRecord(object):
    """Object that holds both address and color information
    Note this is now an Abstract Class.
    """
    def __init__(self, **kwargs):
        self.color_set = kwargs.get('color_set')
        self.testnet = kwargs.get('testnet')
        self.prefix = '\xEF' if self.testnet else '\x80'

    def rawPubkey(self):
        return public_pair_to_hash160_sec(self.publicPoint.pair(), False)

    def get_color_set(self):
        """Access method for the color set associated
        with this address record
        """
        return self.color_set

    def get_data(self):
        """Get this object as a JSON/Storage compatible dict.
        Useful for storage and persistence.
        """
        raw = self.prefix + to_bytes_32(self.rawPrivKey)
        return {"color_set": self.color_set.get_data(),
                "address_data": b2a_hashed_base58(raw)}

    def get_private_key(self):
        return secret_exponent_to_wif(self.rawPrivKey, False, self.testnet)

    def get_address(self):
        """Get the actual bitcoin address
        """
        return self.address

    def get_color_address(self):
        """This is the address that can be used for sending/receiving
        colored coins
        """
        if self.color_set.uncolored_only():
            return self.get_address()
        return "%s@%s" % (self.get_color_set().get_color_hash(),
                          self.get_address())


class LooseAddressRecord(AddressRecord):
    """Subclass of AddressRecord which is entirely imported.
    The address may be an existing one.
    """
    def __init__(self, **kwargs):
        """Create a LooseAddressRecord for a given wallet <model>,
        color <color_set> and address <address_data>. Also let the constructor
        know whether it's on <testnet> (optional).
        <address_data> is the privKey in base58 format
        """
        super(LooseAddressRecord, self).__init__(**kwargs)

        bin_privkey = a2b_hashed_base58(kwargs['address_data'])
        key_type = bin_privkey[0]
        if key_type != self.prefix:
            raise InvalidAddressError
                
        self.rawPrivKey = from_bytes_32(bin_privkey[1:])
        self.publicPoint = BasePoint * self.rawPrivKey
        self.address = public_pair_to_bitcoin_address(
            self.publicPoint.pair(), compressed=False, is_test=self.testnet)

########NEW FILE########
__FILENAME__ = asset
from coloredcoinlib import (ColorSet, IncompatibleTypesError, InvalidValueError, 
                            SimpleColorValue, ColorValue)
from coloredcoinlib.comparable import ComparableMixin


class AssetDefinition(object):
    """Stores the definition of a particular asset, including its color set,
    it's name (moniker), and the wallet model that represents it.
    """
    def __init__(self, colormap, params):
        """Create an Asset for a color map <colormap> and configuration
        <params>. Note params has the color definitions used for this
        Asset.
        """
        self.colormap = colormap
        self.monikers = params.get('monikers', [])
        # currently only single-color assets are supported
        assert len(params.get('color_set')) == 1 
        self.color_set = ColorSet(colormap, params.get('color_set'))
        self.unit = int(params.get('unit', 1))

    def __repr__(self):
        return "%s: %s" % (self.monikers, self.color_set)

    def get_id(self):
        return self.color_set.get_color_hash()

    def get_all_ids(self):
        return [self.get_id()]

    def get_monikers(self):
        """Returns the list of monikers for this asset.
        """
        return self.monikers

    def has_color_id(self, color_id):
        return self.get_color_set().has_color_id(color_id)

    def get_color_set(self):
        """Returns the list of colors for this asset.
        """
        return self.color_set

    def get_null_colorvalue(self):
        color_set = self.get_color_set() 
        assert len(color_set.color_desc_list) == 1
        cd = self.colormap.get_color_def(color_set.color_desc_list[0])
        return SimpleColorValue(colordef=cd, value=0)

    def get_colorvalue(self, utxo):
        """ return colorvalue for a given utxo"""
        if utxo.colorvalues:
            for cv in utxo.colorvalues:
                if self.has_color_id(cv.get_color_id()):
                    return cv
        raise Exception("cannot get colorvalue for UTXO: "
                        "no colorvalues available")

    def parse_value(self, portion):
        """Returns actual number of Satoshis for this Asset
        given the <portion> of the asset.
        """
        return int(float(portion) * self.unit)

    def format_value(self, value):
        """Returns a string representation of the portion of the asset.
        can involve rounding.  doesn't display insignificant zeros
        """
        if isinstance(value, ColorValue) or isinstance(value, AssetValue):
            atoms = value.get_value()
        else:
            atoms = value
        return '{0:g}'.format(atoms / float(self.unit))

    def get_data(self):
        """Returns a JSON-compatible object that represents this Asset
        """
        return {
            "monikers": self.monikers,
            "color_set": self.color_set.get_data(),
            "unit": self.unit
            }


class AssetValue(object):
    def __init__(self, **kwargs):
        self.asset = kwargs.pop('asset')

    def get_kwargs(self):
        kwargs = {}
        kwargs['asset'] = self.get_asset()
        return kwargs

    def clone(self):
        kwargs = self.get_kwargs()
        return self.__class__(**kwargs)

    def check_compatibility(self, other):
        if self.get_color_set() != other.get_color_set():
            raise IncompatibleTypesError        

    def get_asset(self):
        return self.asset

    def get_color_set(self):
        return self.asset.get_color_set()


class AdditiveAssetValue(AssetValue, ComparableMixin):
    def __init__(self, **kwargs):
        super(AdditiveAssetValue, self).__init__(**kwargs)
        self.value = kwargs.pop('value')
        if not isinstance(self.value, int):
            raise InvalidValueError('not an int')

    def get_kwargs(self):
        kwargs = super(AdditiveAssetValue, self).get_kwargs()
        kwargs['value'] = self.get_value()
        return kwargs

    def get_value(self):
        return self.value

    def get_formatted_value(self):
        return self.asset.format_value(self.get_value())

    def __add__(self, other):
        if isinstance(other, int) and other == 0:
            return self
        self.check_compatibility(other)
        kwargs = self.get_kwargs()
        kwargs['value'] = self.get_value() + other.get_value()
        return self.__class__(**kwargs)

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        if isinstance(other, int) and other == 0:
            return self
        self.check_compatibility(other)
        kwargs = self.get_kwargs()
        kwargs['value'] = self.get_value() - other.get_value()
        return self.__class__(**kwargs)

    def __iadd__(self, other):
        self.check_compatibility(other)
        self.value += other.value
        return self

    def __lt__(self, other):
        self.check_compatibility(other)
        return self.get_value() < other.get_value()

    def __eq__(self, other):
        if self.get_color_set() != other.get_color_set():
            return False
        else:
            return self.get_value() == other.get_value()

    def __gt__(self, other):
        if isinstance(other, int) and other == 0:
            return self.get_value() > 0
        return other < self

    def __repr__(self):
        return "Asset Value: %s" % (self.get_value())

    @classmethod
    def sum(cls, items):
        return reduce(lambda x,y:x + y, items)


class AssetTarget(object):
    def __init__(self, address, assetvalue):
        self.address = address
        self.assetvalue = assetvalue

    def get_asset(self):
        return self.assetvalue.get_asset()

    def get_color_set(self):
        return self.assetvalue.get_color_set()

    def get_address(self):
        return self.address

    def get_value(self):
        return self.assetvalue.get_value()

    def get_formatted_value(self):
        return self.assetvalue.get_formatted_value()

    def __repr__(self):
        return "%s: %s" % (self.get_address(), self.assetvalue)

    @classmethod
    def sum(cls, targets):
        if len(targets) == 0:
            return 0
        c = targets[0].assetvalue.__class__
        return c.sum([t.assetvalue for t in targets])


class AssetDefinitionManager(object):
    """Manager for asset definitions. Useful for interacting with
    various Assets.
    """
    def __init__(self, colormap, config):
        """Given a color map <colormap> and a configuration <config>,
        create a new asset definition manager.
        """
        self.config = config
        self.colormap = colormap
        self.asset_definitions = []
        self.lookup_by_moniker = {}
        self.lookup_by_id = {}
        for ad_params in config.get('asset_definitions', []):
            self.register_asset_definition(
                AssetDefinition(self.colormap, ad_params))

        # add bitcoin as a definition
        if "bitcoin" not in self.lookup_by_moniker:
            btcdef = AssetDefinition(
                self.colormap, {
                    "monikers": ["bitcoin"],
                    "color_set": [""],
                    "unit": 100000000,
                    })
            self.lookup_by_moniker["bitcoin"] = btcdef
            self.asset_definitions.append(btcdef)
            self.update_config()

    def register_asset_definition(self, assdef):
        """Given an asset definition <assdef> in JSON-compatible format,
        register the asset with the manager. Note AssetDefinition's
        get_data can be used to get this definition for persistence.
        """
        self.asset_definitions.append(assdef)
        for moniker in assdef.get_monikers():
            if moniker in self.lookup_by_moniker:
                raise Exception(
                    'more than one asset definition have same moniker')
            self.lookup_by_moniker[moniker] = assdef
        for aid in assdef.get_all_ids():
            if aid in self.lookup_by_id:
                raise Exception(
                    'more than one asset definition have same id')
            self.lookup_by_id[aid] = assdef

    def add_asset_definition(self, params):
        """Create a new asset with given <params>.
        params needs the following:
        monikers  - list of names (e.g. ["red", "blue"])
        color_set - list of color sets
                    (e.g. ["obc:f0bd5...a5:0:128649", "obc:a..0:0:147477"])
        """
        assdef = AssetDefinition(self.colormap, params)
        self.register_asset_definition(assdef)
        self.update_config()
        return assdef

    def get_asset_by_moniker(self, moniker):
        """Given a color name <moniker>, return the actual Asset Definition
        """
        return self.lookup_by_moniker.get(moniker)

    def get_asset_by_id(self, asset_id):
        return self.lookup_by_id.get(asset_id)

    def find_asset_by_color_set(self, color_set):
        assets = [asset
                  for asset in self.asset_definitions
                  if asset.color_set.intersects(color_set)]
        assert len(assets) <= 1
        if assets:
            return assets[0]
        else:
            return None        

    def update_config(self):
        """Write the current asset definitions to the persistent data-store
        """
        self.config['asset_definitions'] = \
            [assdef.get_data() for assdef in self.asset_definitions]

    def get_all_assets(self):
        """Returns a list of all assets managed by this manager.
        """
        return self.asset_definitions

    def get_asset_and_address(self, color_address):
        """Given a color address <color_address> return the asset
        and bitcoin address associated with the address. If the color
        described in the address isn't managed by this object,
        throw an exception.
        """
        if color_address.find('@') == -1:
            return (self.lookup_by_moniker.get('bitcoin'), color_address)
        color_set_hash, address = color_address.split('@')
        asset = self.get_asset_by_id(color_set_hash)
        if asset:
            return (asset, address)
        raise Exception("No asset has a color set with this hash: %s"
                        % color_set_hash)

    def get_asset_value_for_colorvalue(self, colorvalue):
        colorset = ColorSet.from_color_ids(self.colormap, 
                                           [colorvalue.get_color_id()])
        asset = self.find_asset_by_color_set(colorset)
        if not asset:
            raise Exception('asset not found')
        return AdditiveAssetValue(asset=asset,
                                  value=colorvalue.get_value())

########NEW FILE########
__FILENAME__ = bip0032
import hashlib
import os

from pycoin.ecdsa.secp256k1 import generator_secp256k1 as BasePoint
from pycoin.encoding import public_pair_to_bitcoin_address
from pycoin.wallet import Wallet

from address import AddressRecord, LooseAddressRecord
from asset import AssetDefinition
from coloredcoinlib import ColorSet
from deterministic import DWalletAddressManager


class BIP0032AddressRecord(AddressRecord):
    """Subclass of AddressRecord which is deterministic and BIP0032 compliant.
    BIP0032AddressRecord will use a pycoin wallet to create addresses
    for specific colors.
    """
    def __init__(self, **kwargs):
        """Create an address for this color <color_set> and index <index>
        with the pycoin_wallet <pycoin_wallet> and on testnet or not
        <testnet>
        The address record returned for the same variables
        will be the same every time, hence "deterministic".
        """
        super(BIP0032AddressRecord, self).__init__(**kwargs)

        pycoin_wallet = kwargs.get('pycoin_wallet')
        color_string = hashlib.sha256(self.color_set.get_earliest()).digest()

        self.index = kwargs.get('index')

        # use the hash of the color string to get the subkey we need
        while len(color_string):
            number = int(color_string[:4].encode('hex'), 16)
            pycoin_wallet = pycoin_wallet.subkey(i=number, is_prime=True,
                                                 as_private=True)
            color_string = color_string[4:]

        # now get the nth address in this wallet
        pycoin_wallet = pycoin_wallet.subkey(i=self.index,
                                             is_prime=True, as_private=True)

        self.rawPrivKey = pycoin_wallet.secret_exponent
        self.publicPoint = BasePoint * self.rawPrivKey
        self.address = public_pair_to_bitcoin_address(self.publicPoint.pair(),
                                                      compressed=False,
                                                      is_test=self.testnet)


class HDWalletAddressManager(DWalletAddressManager):
    """This class manages the creation of new AddressRecords.
    Specifically, it keeps track of which colors have been created
    in this wallet and how many addresses of each color have been
    created in this wallet. This is different from DWalletAddressManager
    in that it is BIP-0032 compliant.
    """
    def __init__(self, colormap, config):
        """Create a deterministic wallet address manager given
        a color map <colormap> and a configuration <config>.
        Note address manager configuration is in the key "hdwam".
        """
        self.config = config
        self.testnet = config.get('testnet', False)
        self.colormap = colormap
        self.addresses = []

        # initialize the wallet manager if this is the first time
        #  this will generate a master key.
        params = config.get('hdwam', None)
        if params is None:
            params = self.init_new_wallet()

        # master key is stored in a separate config entry
        self.master_key = config['hdw_master_key']

        master = hashlib.sha512(self.master_key.decode('hex')).digest()

        # initialize a BIP-0032 wallet
        self.pycoin_wallet = Wallet(is_private=True, is_test=self.testnet,
                                    chain_code=master[32:],
                                    secret_exponent_bytes=master[:32])

        self.genesis_color_sets = params['genesis_color_sets']
        self.color_set_states = params['color_set_states']

        # import the genesis addresses
        for i, color_desc_list in enumerate(self.genesis_color_sets):
            addr = self.get_genesis_address(i)
            addr.color_set = ColorSet(self.colormap,
                                      color_desc_list)
            self.addresses.append(addr)

        # now import the specific color addresses
        for color_set_st in self.color_set_states:
            color_desc_list = color_set_st['color_set']
            max_index = color_set_st['max_index']
            color_set = ColorSet(self.colormap, color_desc_list)
            params = {
                'testnet': self.testnet,
                'pycoin_wallet': self.pycoin_wallet,
                'color_set': color_set
                }
            for index in xrange(max_index + 1):
                params['index'] = index
                self.addresses.append(BIP0032AddressRecord(**params))

        # import the one-off addresses from the config
        for addr_params in config.get('addresses', []):
            addr_params['testnet'] = self.testnet
            addr_params['color_set'] = ColorSet(self.colormap,
                                                addr_params['color_set'])
            address = LooseAddressRecord(**addr_params)
            self.addresses.append(address)

    def init_new_wallet(self):
        """Initialize the configuration if this is the first time
        we're creating addresses in this wallet.
        Returns the "hdwam" part of the configuration.
        """
        if not 'hdw_master_key' in self.config:
            master_key = os.urandom(64).encode('hex')
            self.config['hdw_master_key'] = master_key
        hdwam_params = {
            'genesis_color_sets': [],
            'color_set_states': []
            }
        self.config['hdwam'] = hdwam_params
        return hdwam_params

    def get_new_address(self, asset_or_color_set):
        """Given an asset or color_set <asset_or_color_set>,
        Create a new BIP0032AddressRecord and return it.
        This class will keep that tally and
        persist it in storage, so the address will be available later.
        """
        if isinstance(asset_or_color_set, AssetDefinition):
            color_set = asset_or_color_set.get_color_set()
        else:
            color_set = asset_or_color_set
        index = self.increment_max_index_for_color_set(color_set)
        na = BIP0032AddressRecord(
            pycoin_wallet=self.pycoin_wallet, color_set=color_set,
            index=index, testnet=self.testnet)
        self.addresses.append(na)
        self.update_config()
        return na

    def get_genesis_address(self, genesis_index):
        """Given the index <genesis_index>, will return
        the BIP0032 Address Record associated with that
        index. In general, that index corresponds to the nth
        color created by this wallet.
        """
        return BIP0032AddressRecord(
            pycoin_wallet=self.pycoin_wallet,
            color_set=ColorSet(self.colormap, []),
            index=genesis_index, testnet=self.testnet)

    def update_config(self):
        """Updates the configuration for the address manager.
        The data will persist in the key "dwam" and consists
        of this data:
        genesis_color_sets - Colors created by this wallet
        color_set_states   - How many addresses of each color
        """
        dwam_params = {
            'genesis_color_sets': self.genesis_color_sets,
            'color_set_states': self.color_set_states
            }
        self.config['hdwam'] = dwam_params

########NEW FILE########
__FILENAME__ = blockchain
import os, sys, threading, Queue, time
import traceback
import abc
import hashlib

from coloredcoinlib import BlockchainStateBase
from coloredcoinlib.store import DataStore


class BaseStore(object):
    __metaclass__ = abc.ABCMeta

    def _rev_hex(self, s):
        return s.decode('hex')[::-1].encode('hex')

    def _int_to_hex(self, i, length=1):
        s = hex(i)[2:].rstrip('L')
        s = "0"*(2*length - len(s)) + s
        return self._rev_hex(s)

    def header_to_raw(self, h):
        s = self._int_to_hex(h.get('version'),4) \
            + self._rev_hex(h.get('prev_block_hash', "0"*64)) \
            + self._rev_hex(h.get('merkle_root')) \
            + self._int_to_hex(int(h.get('timestamp')),4) \
            + self._int_to_hex(int(h.get('bits')),4) \
            + self._int_to_hex(int(h.get('nonce')),4)
        return s.decode('hex')

    def header_from_raw(self, s):
        hex_to_int = lambda s: int('0x' + s[::-1].encode('hex'), 16)
        hash_encode = lambda x: x[::-1].encode('hex')
        return {
            'version':         hex_to_int(s[0:4]),
            'prev_block_hash': hash_encode(s[4:36]),
            'merkle_root':     hash_encode(s[36:68]),
            'timestamp':       hex_to_int(s[68:72]),
            'bits':            hex_to_int(s[72:76]),
            'nonce':           hex_to_int(s[76:80]),
        }

    @abc.abstractmethod
    def read_raw_header(self, height):
        pass

    def read_header(self, height):
        data = self.read_raw_header(height)
        if data is not None:
            return self.header_from_raw(data)
        return None


class FileStore(BaseStore):
    def __init__(self, path):
        self.path = path

    def get_height(self):
        try:
            return os.path.getsize(self.path)/80 - 1
        except OSError, e:
            return 0

    def read_raw_header(self, height):
        try:
            with open(self.path, 'rb') as store:
                store.seek(height*80)
                data = store.read(80)
                assert len(data) == 80
                return data
        except (OSError, AssertionError), e:
            return None

    def save_chunk(self, index, chunk):
        with open(self.path, 'ab+') as store:
            store.seek(index*2016*80)
            store.write(chunk)

    def save_chain(self, chain):
        with open(self.path, 'ab+') as store:
            for header in chain:
                store.seek(header['block_height']*80)
                store.write(self.header_to_raw(header))

    def truncate(self, index):
        with open(self.path, 'ab+') as store:
            store.seek(index*80)
            store.truncate()


class SQLStore(DataStore, BaseStore):
    _SQL_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS blockchain_headers (
    height INTEGER,
    version INTEGER,
    prev_block_hash VARCHAR(64),
    merkle_root VARCHAR(64),
    timestamp INTEGER,
    bits INTEGER,
    nonce INTEGER
);
"""

    _SQL_INDEX_HEIGHT = """\
CREATE UNIQUE INDEX IF NOT EXISTS blockchain_headers_height ON blockchain_headers (height);
"""
    _SQL_INDEX_PREV_BLOCK_HASH = """\
CREATE UNIQUE INDEX IF NOT EXISTS blockchain_headers_prev_block_hash ON blockchain_headers (prev_block_hash);
"""

    def __init__(self, conn):
        DataStore.__init__(self, conn)
        self.execute(self._SQL_CREATE_TABLE)
        self.execute(self._SQL_INDEX_HEIGHT)
        self.execute(self._SQL_INDEX_PREV_BLOCK_HASH)

    def get_height(self):
        return (self.execute("SELECT height FROM blockchain_headers ORDER BY height DESC LIMIT 1").fetchone() or [0])[0]

    def read_raw_header(self, height):
        header = self.read_header(height)
        return (None if header is None else self.header_to_raw(header))

    def read_header(self, height):
        data = self.execute("SELECT * FROM blockchain_headers WHERE height = ?",(height, )).fetchone()
        header = {
            'version': data[1],
            'prev_block_hash': data[2],
            'merkle_root': data[3],
            'timestamp': data[4],
            'bits': data[5],
            'nonce': data[6],
        }
        return header

    def _save_header(self, h):
        params = (h['block_height'], h['version'], h['prev_block_hash'], h['merkle_root'], h['timestamp'], h['bits'], h['nonce'])
        self.execute("""\
INSERT INTO blockchain_headers (
    height,
    version,
    prev_block_hash,
    merkle_root,
    timestamp,
    bits,
    nonce
) VALUES (?, ?, ?, ?, ?, ?, ?)""", params)

    def save_chunk(self, index, chunk):
        import time
        print time.time()
        chunk = chunk.encode('hex')
        for i in xrange(2016):
            header = self.header_from_raw(chunk[i*80:(i+1)*80])
            header['block_height'] = index*2016 + i
            self._save_header(header)
        print time.time()

    def save_chain(self, chain):
        pass

    def truncate(self, index):
        self.execute("""DELETE FROM blockchain_headers WHERE height >= ?""", (index,))


class NewBlocks(threading.Thread):
    def __init__(self, bcs, queue):
        threading.Thread.__init__(self)
        self.running = False
        self.lock = threading.Lock()
        self.daemon = True
        self.bcs = bcs
        self.queue = queue

    def run(self):
        with self.lock:
            self.running = True

        run_time = time.time()
        while self.is_running():
            if run_time > time.time():
                time.sleep(0.05)
                continue
            try:
                header = self.bcs.get_header(self.bcs.get_height())
                self.queue.put(header)
            except Exception, e:
                sys.stderr.write('Error! %s: %s\n' % (type(e), e))
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()
            run_time = time.time() + 30

    def is_running(self):
        with self.lock:
            return self.running

    def stop(self):
        with self.lock:
            self.running = False


class BlockHashingAlgorithm(object):
    max_bits = 0x1d00ffff
    max_target = 0x00000000FFFF0000000000000000000000000000000000000000000000000000

    def __init__(self, store, testnet):
        self.store = store
        self.testnet = testnet

    def hash_header(self, raw_header):
        import hashlib
        return hashlib.sha256(hashlib.sha256(raw_header).digest()).digest()[::-1].encode('hex_codec')

    def get_target(self, index, chain=None):
        if chain is None:
            chain = []

        if index == 0:
            return self.max_bits, self.max_target

        first = self.store.read_header((index-1)*2016)
        last = self.store.read_header(index*2016-1)
        if last is None:
            for h in chain:
                if h.get('block_height') == index*2016-1:
                    last = h

        nActualTimespan = last.get('timestamp') - first.get('timestamp')
        nTargetTimespan = 14*24*60*60
        nActualTimespan = max(nActualTimespan, nTargetTimespan/4)
        nActualTimespan = min(nActualTimespan, nTargetTimespan*4)

        bits = last.get('bits')
        # convert to bignum
        MM = 256*256*256
        a = bits%MM
        if a < 0x8000:
            a *= 256
        target = (a) * pow(2, 8 * (bits/MM - 3))

        # new target
        new_target = min( self.max_target, (target * nActualTimespan)/nTargetTimespan )

        # convert it to bits
        c = ("%064X"%new_target)[2:]
        i = 31
        while c[0:2]=="00":
            c = c[2:]
            i -= 1

        c = int('0x'+c[0:6],16)
        if c > 0x800000: 
            c /= 256
            i += 1

        new_bits = c + MM * i
        return new_bits, new_target

    def verify_chunk(self, index, chunk):
        height = index*2016
        num = len(chunk)/80

        if index == 0:  
            prev_hash = ("0"*64)
        else:
            prev_header = self.store.read_header(index*2016-1)
            if prev_header is None:
                raise
            prev_hash = self.hash_header(self.store.header_to_raw(prev_header))

        bits, target = self.get_target(index)

        for i in range(num):
            raw_header = chunk[i*80:(i+1)*80]
            header = self.store.header_from_raw(raw_header)
            _hash = self.hash_header(raw_header)

            assert prev_hash == header.get('prev_block_hash')
            try:
                assert bits == header.get('bits')
                assert int('0x'+_hash, 16) < target
            except AssertionError:
                if self.testnet and header.get('timestamp') - prev_header.get('timestamp') > 1200:
                    assert self.max_bits == header.get('bits')
                    assert int('0x'+_hash, 16) < self.max_target
                else:
                    raise

            prev_header = header
            prev_hash = _hash

    def verify_chain(self, chain):
        prev_header = self.store.read_header(chain[0].get('block_height')-1)
        prev_hash = self.hash_header(self.store.header_to_raw(prev_header))

        for header in chain:
            bits, target = self.get_target(header.get('block_height')/2016, chain)
            _hash = self.hash_header(self.store.header_to_raw(header))

            assert prev_hash == header.get('prev_block_hash')
            try:
                assert bits == header.get('bits')
                assert int('0x'+_hash, 16) < target
            except AssertionError:
                if self.testnet and header.get('timestamp') - prev_header.get('timestamp') > 1200:
                    assert self.max_bits == header.get('bits')
                    assert int('0x'+_hash, 16) < self.max_target
                else:
                    raise

            prev_header = header
            prev_hash = _hash


class VerifiedBlockchainState(BlockchainStateBase, threading.Thread):
    def __init__(self, bcs, txdb, testnet, path):
        threading.Thread.__init__(self)
        self.running = False
        self.sync = False
        self.lock = threading.Lock()
        self.queue = Queue.Queue()
        self.newBlocks = NewBlocks(bcs, self.queue)

        self.bcs = bcs
        self.txdb = txdb
        self.store = FileStore(os.path.join(path, 'blockchain_headers'))
        self.bha = BlockHashingAlgorithm(self.store, testnet)

        self.local_height = 0
        self._set_local_height()
        self.daemon = True

    def run(self):
        with self.lock:
            self.running = True

        self.newBlocks.start()
        while self.is_running():
            try:
                header = self.queue.get_nowait()
            except Queue.Empty:
                time.sleep(0.05)
                continue

            if header['block_height'] == self.height:
                with self.lock:
                    self.sync = True
                continue

            try:
                with self.lock:
                    self.sync = False
                if -50 < header['block_height'] - self.height < 50:
                    retval = self._get_chain(header)
                else:
                    retval = self._get_chunks(header)
                with self.lock:
                    self.sync = retval
                self._set_local_height()
            except Exception, e:
                sys.stderr.write('Error! %s: %s\n' % (type(e), e))
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()

    def is_running(self):
        with self.lock:
            return self.running

    def is_synced(self):
        with self.lock:
            return self.sync

    def stop(self):
        with self.lock:
            self.running = False
        self.newBlocks.stop()

    @property
    def height(self):
        return self.local_height

    def get_header(self, height):
        return self.store.read_header(height)

    def _set_local_height(self):
        h = self.store.get_height()
        if self.local_height != h:
            self.local_height = h

    def _reorg(self, height):
        sys.stderr.write('reorg blockchain from %d\n' % height)
        sys.stderr.flush()
        if hasattr(self.txdb, 'drop_from_height'):
            self.txdb.drop_from_height(height)
        self.txdb.store.drop_from_height(height)

    def _get_chunks(self, header):
        max_index = (header['block_height'] + 1)/2016
        index = min((self.height+1)/2016, max_index)
        reorg_from = None

        while self.is_running():
            if index > max_index:
                return True

            chunk = self.bcs.get_chunk(index)
            if not chunk:
                return False
            chunk = chunk.decode('hex')

            if index == 0:
                prev_hash = "0"*64
                if reorg_from is not None:
                    reorg_from = 0
            else:
                prev_header = self.store.read_raw_header(index*2016-1)
                if prev_header is None:
                    return False
                prev_hash = self.bha.hash_header(prev_header)
            chunk_first_header = self.store.header_from_raw(chunk[:80])
            if chunk_first_header['prev_block_hash'] != prev_hash:
                reorg_from = index*2016
                index -= 1
                continue

            if reorg_from is not None:
                self._reorg(reorg_from)
                reorg_from = None
            try:
                self.bha.verify_chunk(index, chunk)
            except Exception, e:
                sys.stderr.write('Verify chunk failed! (%s: %s)\n' % (type(e), e))
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()
                return False

            self.store.truncate(index*2016)
            self.store.save_chunk(index, chunk)
            index += 1

    def _get_chain(self, header):
        chain = [header]
        requested_height = None
        reorg_from = None

        while self.is_running():
            if requested_height is not None:
                header = self.bcs.get_header(requested_height)
                if not header:
                    return False
                chain = [header] + chain
                requested_height = None
                continue

            prev_height = header.get('block_height') - 1
            prev_header = self.store.read_raw_header(prev_height)
            if prev_header is None:
                requested_height = prev_height
                continue

            prev_hash = self.bha.hash_header(prev_header)
            if prev_hash != header.get('prev_block_hash'):
                requested_height = prev_height
                reorg_from = prev_height
                continue

            if reorg_from is not None:
                self._reorg(reorg_from)
                reorg_from = None
            try:
                self.bha.verify_chain(chain)
            except Exception, e:
                sys.stderr.write('Verify chain failed! (%s: %s)\n' % (type(e), e))
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()
                return False

            self.store.truncate(chain[0]['block_height'])
            self.store.save_chain(chain)
            return True

########NEW FILE########
__FILENAME__ = coindb
"""
coindb.py

Keeps track of transaction outputs (coins) which belong to user's wallet.
CoinQuery is able to find transaction outputs satisfying certain criteria:

 * belonging to a particular color set (incl. uncolored)
 * confirmed/unconfirmed
 * spent/unspent

Information about coins is added either by UTXO fetcher or by wallet
controller through apply_tx.
"""

from coloredcoinlib.store import DataStore, DataStoreConnection, unwrap1
from coloredcoinlib.txspec import ComposedTxSpec
from txcons import RawTxSpec
from coloredcoinlib import UNCOLORED_MARKER, SimpleColorValue

def flatten1(lst):
    return [elt[0] for elt in lst]
        

class CoinStore(DataStore):
    """Storage for Coin (Transaction Objects).
    """
    def __init__(self, conn):
        """Create a unspent transaction out data-store at <dbpath>.
        """
        super(CoinStore, self).__init__(conn)
        if not self.table_exists('coin_data'):
            # create the main table and some useful indexes
            self.execute("""
                CREATE TABLE coin_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, address TEXT,
                    txhash TEXT, outindex INTEGER, value INTEGER,
                    script TEXT)
            """)
            self.execute("CREATE UNIQUE INDEX coin_data_outpoint ON coin_data "
                         "(txhash, outindex)")
            self.execute("CREATE INDEX coin_data_address ON coin_data "
                         "(address)")
        if not self.table_exists('coin_spends'):
            self.execute("""
                 CREATE TABLE coin_spends (coin_id INTEGER, txhash TEXT,
                               FOREIGN KEY (coin_id) REFERENCES coin_data(id))""")
            self.execute("CREATE UNIQUE INDEX coin_spends_id ON coin_spends "
                         "(coin_id, txhash)")
            self.execute("CREATE INDEX coin_spends_txhash ON coin_spends "
                         "(txhash)")

    def purge_coins(self):
        self.execute("DELETE FROM coin_spends")
        self.execute("DELETE FROM coin_data")

    def delete_coin(self, coin_id):
        self.execute("DELETE FROM coin_spends WHERE coin_id = ?", (coin_id,))
        self.execute("DELETE FROM coin_data WHERE id = ?", (coin_id,))

    def add_coin(self, address, txhash, outindex, value, script):
        """Record a coin into the sqlite3 DB. We record the following
        values:
        <address>    - bitcoin address of the coin
        <txhash>     - b58 encoded transaction hash
        <outindex>   - position of the coin within the greater transaction
        <value>      - amount in Satoshi being sent
        <script>     - signature
        """
        self.execute(
            """INSERT INTO coin_data
               (address, txhash, outindex, value, script)
               VALUES (?, ?, ?, ?, ?)""",
            (address, txhash, outindex, value, script))
    
    def add_spend(self, coin_id, spend_txhash):
        self.execute("INSERT OR IGNORE INTO coin_spends (coin_id, txhash) VALUES (?, ?)",
                     (coin_id, spend_txhash))

    def find_coin(self, txhash, outindex):
         return unwrap1(self.execute("SELECT id FROM coin_data WHERE txhash = ? and outindex = ?",
                                     (txhash, outindex)).fetchone())

    def get_coin_spends(self, coin_id):
        return flatten1(self.execute("SELECT txhash FROM coin_spends WHERE coin_id = ?",
                                     (coin_id, )).fetchall())

    def get_coins_for_address(self, address):
        """Return the entire list of coins for a given address <address>
        """
        return self.execute("SELECT * FROM coin_data WHERE address = ?",
                            (address, )).fetchall()

    def get_coin(self, coin_id):
        return self.execute("SELECT * FROM coin_data WHERE id = ?",
                            (coin_id,)).fetchone()

class UTXO(ComposedTxSpec.TxIn):
    def __init__(self, utxo_data):
        super(UTXO, self).__init__(utxo_data['txhash'], utxo_data['outindex'])
        self.txhash = utxo_data['txhash']
        self.outindex = utxo_data['outindex']
        self.value = utxo_data['value']
        self.script = utxo_data['script']
        self.address_rec = None
        self.colorvalues = None

class Coin(UTXO):
    def __init__(self, coin_manager, coin_data):
        super(Coin, self).__init__(coin_data)
        self.coin_id = coin_data['id']
        self.address = coin_data['address']
        self.coin_manager = coin_manager

    def get_address(self):
        if self.address_rec:
            return self.address_rec.get_address()
        else:
            return "not set"

    def get_colorvalues(self):
        if self.colorvalues:
            return self.colorvalues
        else:
            self.colorvalues = self.coin_manager.compute_colorvalues(self)
            return self.colorvalues

    def get_spending_txs(self):
        return self.coin_manager.get_coin_spending_txs(self)

    def is_spent(self):
        return self.coin_manager.is_coin_spent(self)
    
    def is_confirmed(self):
        return self.coin_manager.is_coin_confirmed(self)

    def is_valid(self):
        return self.coin_manager.is_coin_valid(self)
        
class CoinQuery(object):
    """Query object for getting data out of the UTXO data-store.
    """
    def __init__(self, model, color_set, filter_options):
        """Create a query object given a wallet_model <model> and
        a list of colors in <color_set>
        """
        self.model = model
        self.color_set = color_set
        self.coin_manager = model.get_coin_manager()
        self.filter_options = filter_options
        assert 'spent' in filter_options

    def coin_matches_filter(self, coin):
        if not coin.is_valid():
            return False
        if self.filter_options['spent'] != coin.is_spent():
            return False
        if self.filter_options.get('only_unconfirmed', False):
            return not coin.is_confirmed()
        if self.filter_options.get('include_unconfirmed', False):
            return True
        return coin.is_confirmed()    

    def get_coins_for_address(self, address_rec):
        """Given an address <address_rec>, return the list of coin's
        straight from the DB. Note this specifically does NOT return
        COIN objects.
        """
        color_set = self.color_set
        addr_color_set = address_rec.get_color_set()
        all_coins = filter(
            self.coin_matches_filter,
            self.coin_manager.get_coins_for_address(address_rec.get_address()))
        cdata = self.model.ccc.colordata
        address_is_uncolored = addr_color_set.color_id_set == set([0])
        if address_is_uncolored:
            for coin in all_coins:
                coin.address_rec = address_rec
                coin.colorvalues = [SimpleColorValue(colordef=UNCOLORED_MARKER,
                                                     value=coin.value)]
            return all_coins
        for coin in all_coins:
            coin.address_rec = address_rec
            coin.colorvalues = None
            try:
                coin.colorvalues = cdata.get_colorvalues(
                    addr_color_set.color_id_set, coin.txhash, coin.outindex)
            except Exception as e:
                print e
                raise
        def relevant(coin):
            cvl = coin.colorvalues
            if coin.colorvalues is None:
                return False  # None indicates failure
            if cvl == []:
                return color_set.has_color_id(0)
            for cv in cvl:
                if color_set.has_color_id(cv.get_color_id()):
                    return True
                return False
        return filter(relevant, all_coins)

    def get_result(self):
        """Returns all utxos for the color_set defined for this query.
        """
        addr_man = self.model.get_address_manager()
        addresses = addr_man.get_addresses_for_color_set(self.color_set)
        utxos = []
        for address in addresses:
            utxos.extend(self.get_coins_for_address(address))
        return utxos


class CoinManager(object):
    """Object for managing the UTXO data store.
    Note using this manager allows us to create multiple UTXO data-stores.
    """
    def __init__(self, model, config):
        """Creates a UTXO manager given a wallet_model <model>
        and configuration <config>.
        """
        params = config.get('utxodb', {})
        self.model = model
        self.store = CoinStore(self.model.store_conn.conn)

    def compute_colorvalues(self, coin):
        wam = self.model.get_address_manager()
        address_rec = wam.find_address_record(coin.address)
        if not address_rec:
            raise Exception('address record not found')
        color_set = address_rec.get_color_set()
        if color_set.uncolored_only():
            return [SimpleColorValue(colordef=UNCOLORED_MARKER,
                                     value=coin.value)]
        else:
            cdata = self.model.ccc.colordata
            return cdata.get_colorvalues(color_set.color_id_set,
                                         coin.txhash, coin.outindex)

    def purge_coins(self):
        """full rescan"""
        self.store.purge_coins()

    def find_coin(self, txhash, outindex):
        coin_id = self.store.find_coin(txhash, outindex)
        if coin_id:
            return self.get_coin(coin_id)
        else:
            return None

    def get_coin(self, coin_id):
        coin_rec = self.store.get_coin(coin_id)
        if coin_rec:
            return Coin(self, coin_rec)
        else:
            return None

    def is_coin_valid(self, coin):
        return self.model.get_tx_db().is_tx_valid(coin.txhash)

    def get_coin_spending_txs(self, coin):
        return filter(self.model.get_tx_db().is_tx_valid, 
                      self.store.get_coin_spends(coin.coin_id))

    def is_coin_spent(self, coin):
        return len(self.get_coin_spending_txs(coin)) > 0

    def is_coin_confirmed(self, coin):
        return self.model.get_tx_db().is_tx_confirmed(coin.txhash)

    def get_coins_for_address(self, address):
        """Returns a list of UTXO objects for a given address <address>
        """
        coins = []
        for coin_rec in self.store.get_coins_for_address(address):
            coin = Coin(self, coin_rec)
            coins.append(coin)
        return coins

    def add_coin(self, address, txhash, outindex, value, script):
        coin_id = self.store.find_coin(txhash, outindex)
        if coin_id is None:
            self.store.add_coin(address, txhash, outindex, value, script)
            coin_id = self.store.find_coin(txhash, outindex)

    def get_coins_for_transaction(self, raw_tx):
        """all coins referenced by a transaction"""
        spent_coins = []
        for txin in raw_tx.composed_tx_spec.txins:
            prev_txhash, prev_outindex = txin.get_outpoint()
            coin = self.find_coin(prev_txhash, prev_outindex)
            if coin:
                spent_coins.append(coin)
        
        received_coins = []
        txhash = raw_tx.get_hex_txhash()
        for out_idx in range(len(raw_tx.composed_tx_spec.txouts)):
            coin = self.find_coin(txhash, out_idx)
            if coin:
                received_coins.append(coin)
        return spent_coins, received_coins

    def apply_tx(self, txhash, raw_tx):
        """Given a transaction <composed_tx_spec>, delete any
        utxos that it spends and add any utxos that are new
        """

        all_addresses = [a.get_address() for a in
                         self.model.get_address_manager().get_all_addresses()]

        ctxs = raw_tx.composed_tx_spec

        # record spends
        for txin in ctxs.txins:
            prev_txhash, prev_outindex = txin.get_outpoint()
            coin_id = self.store.find_coin(prev_txhash, prev_outindex)
            if coin_id:
                self.store.add_spend(coin_id, txhash)
                
        # put the new utxo into the db
        for i, txout in enumerate(ctxs.txouts):
            script = raw_tx.pycoin_tx.txs_out[i].script.encode('hex')
            if txout.target_addr in all_addresses:
                self.add_coin(txout.target_addr, txhash, i,
                              txout.value, script)
                             

########NEW FILE########
__FILENAME__ = color
from pycoin.encoding import hash160_sec_to_bitcoin_address

from coloredcoinlib import (ColorDataBuilderManager,
                            AidedColorDataBuilder, 
                            FullScanColorDataBuilder, DataStoreConnection,
                            ColorDataStore, ColorMetaStore, ColorMap,
                            ThickColorData, ThinColorData)
from services.electrum import EnhancedBlockchainState


class ColoredCoinContext(object):
    """Interface to the Colored Coin Library's various offerings.
    Specifically, this object provides access to a storage mechanism
    (store_conn, cdstore, metastore), the color mapping (colormap)
    and color data (Thick Color Data)
    """
    def __init__(self, config, blockchain_state):
        """Creates a Colored Coin Context given a config <config>
        """
        params = config.get('ccc', {})
        self.blockchain_state = blockchain_state
        self.testnet = config.get('testnet', False)
        thin = config.get('thin', True)

        if thin:
            color_data_class = ThinColorData
            color_data_builder = AidedColorDataBuilder
        else:
            color_data_class = ThickColorData
            color_data_builder = FullScanColorDataBuilder
            
        self.store_conn = DataStoreConnection(
            params.get("colordb_path", "color.db"))
        self.cdstore = ColorDataStore(self.store_conn.conn)
        self.metastore = ColorMetaStore(self.store_conn.conn)
        self.colormap = ColorMap(self.metastore)
        
        cdbuilder = ColorDataBuilderManager(
            self.colormap, self.blockchain_state, self.cdstore,
            self.metastore, color_data_builder)

        self.colordata = color_data_class(
            cdbuilder, self.blockchain_state, self.cdstore, self.colormap)

    def raw_to_address(self, raw_address):
        return hash160_sec_to_bitcoin_address(raw_address,
                                              is_test=self.testnet)

########NEW FILE########
__FILENAME__ = deterministic
import hashlib
import hmac
import os

from pycoin.ecdsa.secp256k1 import generator_secp256k1 as BasePoint
from pycoin.encoding import from_bytes_32, public_pair_to_bitcoin_address

from address import AddressRecord, LooseAddressRecord
from asset import AssetDefinition
from coloredcoinlib import ColorSet


class DeterministicAddressRecord(AddressRecord):
    """Subclass of AddressRecord which is entirely deterministic.
    DeterministicAddressRecord will use a single master key to
    create addresses for specific colors and bitcoin addresses.
    """
    def __init__(self, **kwargs):
        """Create an address for this color <color_set>
        and index <index> with the master key <master_key>.
        The address record returned for the same three variables
        will be the same every time, hence "deterministic".
        """
        super(DeterministicAddressRecord, self).__init__(**kwargs)

        if len(self.color_set.get_data()) == 0:
            color_string = "genesis block"
        else:
            color_string = self.color_set.get_hash_string()

        self.index = kwargs.get('index')
        h = hmac.new(str(kwargs['master_key']),
                     "%s|%s" % (color_string, self.index), hashlib.sha256)
        string = h.digest()
        self.rawPrivKey = from_bytes_32(string)
        self.publicPoint = BasePoint * self.rawPrivKey
        self.address = public_pair_to_bitcoin_address(self.publicPoint.pair(),
                                                      compressed=False,
                                                      is_test=self.testnet)

class DWalletAddressManager(object):
    """This class manages the creation of new AddressRecords.
    Specifically, it keeps track of which colors have been created
    in this wallet and how many addresses of each color have been
    created in this wallet.
    """
    def __init__(self, colormap, config):
        """Create a deterministic wallet address manager given
        a colormap <colormap> and a configuration <config>.
        Note address manager configuration is in the key "dwam".
        """
        self.config = config
        self.testnet = config.get('testnet', False)
        self.colormap = colormap
        self.addresses = []

        # initialize the wallet manager if this is the first time
        #  this will generate a master key.
        params = config.get('dwam', None)
        if params is None:
            params = self.init_new_wallet()

        # master key is stored in a separate config entry
        self.master_key = config['dw_master_key']

        self.genesis_color_sets = params['genesis_color_sets']
        self.color_set_states = params['color_set_states']

        # import the genesis addresses
        for i, color_desc_list in enumerate(self.genesis_color_sets):
            addr = self.get_genesis_address(i)
            addr.color_set = ColorSet(self.colormap,
                                      color_desc_list)
            self.addresses.append(addr)

        # now import the specific color addresses
        for color_set_st in self.color_set_states:
            color_desc_list = color_set_st['color_set']
            max_index = color_set_st['max_index']
            color_set = ColorSet(self.colormap, color_desc_list)
            params = {
                'testnet': self.testnet,
                'master_key': self.master_key,
                'color_set': color_set
                }
            for index in xrange(max_index + 1):
                params['index'] = index
                self.addresses.append(DeterministicAddressRecord(**params))

        # import the one-off addresses from the config
        for addr_params in config.get('addresses', []):
            addr_params['testnet'] = self.testnet
            addr_params['color_set'] = ColorSet(self.colormap,
                                                addr_params['color_set'])
            address = LooseAddressRecord(**addr_params)
            self.addresses.append(address)

    def init_new_wallet(self):
        """Initialize the configuration if this is the first time
        we're creating addresses in this wallet.
        Returns the "dwam" part of the configuration.
        """
        if not 'dw_master_key' in self.config:
            master_key = os.urandom(64).encode('hex')
            self.config['dw_master_key'] = master_key
        dwam_params = {
            'genesis_color_sets': [],
            'color_set_states': []
            }
        self.config['dwam'] = dwam_params
        return dwam_params

    def increment_max_index_for_color_set(self, color_set):
        """Given a color <color_set>, record that there is one more
        new address for that color.
        """
        # TODO: speed up, cache(?)
        for color_set_st in self.color_set_states:
            color_desc_list = color_set_st['color_set']
            max_index = color_set_st['max_index']
            cur_color_set = ColorSet(self.colormap,
                                     color_desc_list)
            if cur_color_set.equals(color_set):
                max_index += 1
                color_set_st['max_index'] = max_index
                return max_index
        self.color_set_states.append({"color_set": color_set.get_data(),
                                      "max_index": 0})
        return 0

    def get_new_address(self, asset_or_color_set):
        """Given an asset or color_set <asset_or_color_set>,
        Create a new DeterministicAddressRecord and return it.
        The DWalletAddressManager will keep that tally and
        persist it in storage, so the address will be available later.
        """
        if isinstance(asset_or_color_set, AssetDefinition):
            color_set = asset_or_color_set.get_color_set()
        else:
            color_set = asset_or_color_set
        index = self.increment_max_index_for_color_set(color_set)
        na = DeterministicAddressRecord(master_key=self.master_key,
                                        color_set=color_set, index=index,
                                        testnet=self.testnet)
        self.addresses.append(na)
        self.update_config()
        return na

    def get_genesis_address(self, genesis_index):
        """Given the index <genesis_index>, will return
        the Deterministic Address Record associated with that
        index. In general, that index corresponds to the nth
        color created by this wallet.
        """
        return DeterministicAddressRecord(
            master_key=self.master_key,
            color_set=ColorSet(self.colormap, []),
            index=genesis_index, testnet=self.testnet)

    def get_new_genesis_address(self):
        """Create a new genesis address and return it.
        This will necessarily increment the number of genesis
        addresses from this wallet.
        """
        index = len(self.genesis_color_sets)
        self.genesis_color_sets.append([])
        self.update_config()
        address = self.get_genesis_address(index)
        address.index = index
        self.addresses.append(address)
        return address

    def update_genesis_address(self, address, color_set):
        """Updates the genesis address <address> to have a different
        color set <color_set>.
        """
        assert address.color_set.color_id_set == set([])
        address.color_set = color_set
        self.genesis_color_sets[address.index] = color_set.get_data()
        self.update_config()

    def get_some_address(self, color_set):
        """Returns an address associated with color <color_set>.
        This address will be essentially a random address in the
        wallet. No guarantees to what will come out.
        If there is not address corresponding to the color_set,
        thhis method will create one and return it.
        """
        acs = self.get_addresses_for_color_set(color_set)
        if acs:
            # reuse
            return acs[0]
        else:
            return self.get_new_address(color_set)

    def get_change_address(self, color_set):
        """Returns an address that can receive the change amount
        for a color <color_set>
        """
        return self.get_some_address(color_set)

    def get_all_addresses(self):
        """Returns the list of all AddressRecords in this wallet.
        """
        return self.addresses

    def find_address_record(self, address):
        for address_rec in self.addresses:
            if address_rec.get_address() == address:
                return address_rec
        return None

    def get_addresses_for_color_set(self, color_set):
        """Given a color <color_set>, returns all AddressRecords
        that have that color.
        """
        return [addr for addr in self.addresses
                if color_set.intersects(addr.get_color_set())]

    def update_config(self):
        """Updates the configuration for the address manager.
        The data will persist in the key "dwam" and consists
        of this data:
        genesis_color_sets - Colors created by this wallet
        color_set_states   - How many addresses of each color
        """
        dwam_params = {
            'genesis_color_sets': self.genesis_color_sets,
            'color_set_states': self.color_set_states
            }
        self.config['dwam'] = dwam_params

########NEW FILE########
__FILENAME__ = logger
import logging

def setup_logging():
    logger = logging.getLogger('ngcccbase')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())

########NEW FILE########
__FILENAME__ = agent
import Queue
import time

from protocol_objects import MyEOffer, EOffer, MyEProposal, ForeignEProposal
from utils import LOGINFO, LOGDEBUG, LOGERROR


class EAgent(object):
    """implements high-level exchange logic, keeps track of the state
       (offers, propsals)"""

    def __init__(self, ewctrl, config, comm):
        self.ewctrl = ewctrl
        self.my_offers = dict()
        self.their_offers = dict()
        self.active_ep = None
        self.ep_timeout = None
        self.comm = comm
        self.offers_updated = False
        self.config = config
        self.event_handlers = {}
        comm.add_agent(self)

    def set_event_handler(self, event_type, handler):
        self.event_handlers[event_type] = handler

    def fire_event(self, event_type, data):
        eh = self.event_handlers.get(event_type)
        if eh:
            eh(data)

    def set_active_ep(self, ep):
        if ep is None:
            self.ep_timeout = None
            self.match_orders = True
        else:
            self.ep_timeout = time.time() + self.config['ep_expiry_interval']
        self.active_ep = ep

    def has_active_ep(self):
        if self.ep_timeout and self.ep_timeout < time.time():
            self.set_active_ep(None)  # TODO: cleanup?
        return self.active_ep is not None

    def service_my_offers(self):
        for my_offer in self.my_offers.values():
            if my_offer.auto_post:
                if not my_offer.expired():
                    continue
                if self.active_ep and self.active_ep.my_offer.oid == my_offer.oid:
                    continue
                my_offer.refresh(self.config['offer_expiry_interval'])
                self.post_message(my_offer)

    def service_their_offers(self):
        for their_offer in self.their_offers.values():
            if their_offer.expired(-self.config.get('offer_grace_interval', 0)):
                del self.their_offers[their_offer.oid]
                self.fire_event('offers_updated', None)

    def _update_state(self):
        if not self.has_active_ep() and self.offers_updated:
            self.offers_updated = False
            self.match_offers()
        self.service_my_offers()
        self.service_their_offers()

    def register_my_offer(self, offer):
        assert isinstance(offer, MyEOffer)
        self.my_offers[offer.oid] = offer
        self.offers_updated = True
        self.fire_event('offers_updated', offer)
        self.fire_event('register_my_offer', offer)

    def cancel_my_offer(self, offer):
        if self.active_ep and (self.active_ep.offer.oid == offer.oid
                               or self.active_ep.my_offer.oid == offer.oid):
            self.set_active_ep(None)
        if offer.oid in self.my_offers:
            del self.my_offers[offer.oid]
        self.fire_event('offers_updated', offer)
        self.fire_event('cancel_my_offer', offer)

    def register_their_offer(self, offer):
        LOGINFO("register oid %s ", offer.oid)
        self.their_offers[offer.oid] = offer
        offer.refresh(self.config['offer_expiry_interval'])
        self.offers_updated = True
        self.fire_event('offers_updated', offer)

    def match_offers(self):
        if self.has_active_ep():
            return
        for my_offer in self.my_offers.values():
            for their_offer in self.their_offers.values():
                LOGINFO("matches %s", my_offer.matches(their_offer))
                if my_offer.matches(their_offer):
                    success = False
                    try:
                        self.make_exchange_proposal(their_offer, my_offer)
                        success = True
                    except Exception as e:                # pragma: no cover
                        LOGERROR("Exception during "      # pragma: no cover
                                 "matching offer %s", e)  # pragma: no cover
                        raise                             # pragma: no cover
                    if success:
                        return

    def make_exchange_proposal(self, orig_offer, my_offer):
        if self.has_active_ep():
            raise Exception("already have active EP (in makeExchangeProposal")
        ep = MyEProposal(self.ewctrl, orig_offer, my_offer)
        self.set_active_ep(ep)
        self.post_message(ep)
        self.fire_event('make_ep', ep)

    def dispatch_exchange_proposal(self, ep_data):
        ep = ForeignEProposal(self.ewctrl, ep_data)
        LOGINFO("ep oid:%s, pid:%s, ag:%s", ep.offer.oid, ep.pid, self)
        if self.has_active_ep():
            LOGDEBUG("has active EP")
            if ep.pid == self.active_ep.pid:
                return self.update_exchange_proposal(ep)
        else:
            if ep.offer.oid in self.my_offers:
                LOGDEBUG("accept exchange proposal")
                return self.accept_exchange_proposal(ep)
        # We have neither an offer nor a proposal matching
        #  this ExchangeProposal
        if ep.offer.oid in self.their_offers:
            # remove offer if it is in-work
            # TODO: set flag instead of deleting it
            del self.their_offers[ep.offer.oid]
        return None

    def accept_exchange_proposal(self, ep):
        if self.has_active_ep():
            return
        my_offer = self.my_offers[ep.offer.oid]
        reply_ep = ep.accept(my_offer)
        self.set_active_ep(reply_ep)
        self.post_message(reply_ep)
        self.fire_event('accept_ep', [ep, reply_ep])

    def clear_orders(self, ep):
        self.fire_event('trade_complete', ep)

        try:
            if isinstance(ep, MyEProposal):
                if ep.my_offer:
                    del self.my_offers[ep.my_offer.oid]
                del self.their_offers[ep.offer.oid]
            else:
                del self.my_offers[ep.offer.oid]
        except Exception as e:                       # pragma: no cover
            LOGERROR("there was an exception "       # pragma: no cover
                     "when clearing offers: %s", e)  # pragma: no cover
        self.fire_event('offers_updated', None)

    def update_exchange_proposal(self, ep):
        LOGDEBUG("updateExchangeProposal")
        my_ep = self.active_ep
        assert my_ep and my_ep.pid == ep.pid
        my_ep.process_reply(ep)
        if isinstance(my_ep, MyEProposal):
            self.post_message(my_ep)
        # my_ep.broadcast()
        self.clear_orders(my_ep)
        self.set_active_ep(None)

    def post_message(self, obj):
        self.comm.post_message(obj.get_data())

    def dispatch_message(self, content):
        try:
            if 'oid' in content:
                o = EOffer.from_data(content)
                self.register_their_offer(o)
            elif 'pid' in content:
                self.dispatch_exchange_proposal(content)
        except Exception as e:                         # pragma: no cover
            LOGERROR("got exception %s "               # pragma: no cover
                     "when dispatching a message", e)  # pragma: no cover
            raise                                      # pragma: no cover

    def update(self):
        self.comm.poll_and_dispatch()
        self._update_state()

########NEW FILE########
__FILENAME__ = comm
import urllib2
import json
import time
import threading
import Queue

from utils import make_random_id, LOGINFO, LOGDEBUG, LOGERROR


class CommBase(object):
    def __init__(self):
        self.agents = []

    def add_agent(self, agent):
        self.agents.append(agent)


class HTTPComm(CommBase):
    def __init__(self, config, url = 'http://localhost:8080/messages'):
        super(HTTPComm, self).__init__()
        self.config = config
        self.lastpoll = -1
        self.url = url
        self.own_msgids = set()

    def post_message(self, content):
        msgid = make_random_id()
        content['msgid'] = msgid
        self.own_msgids.add(msgid)
        LOGDEBUG( "----- POSTING MESSAGE ----")
        data = json.dumps(content)
        LOGDEBUG(data)
        u = urllib2.urlopen(self.url, data)
        return u.read() == 'Success'

    def poll_and_dispatch(self):
        url = self.url
        if self.lastpoll == -1:
            url = url + "?from_timestamp_rel=%s" % self.config['offer_expiry_interval']
        else:
            url = url + '?from_serial=%s' % (self.lastpoll+1)
        u = urllib2.urlopen(url)
        resp = json.loads(u.read())
        for x in resp:
            if int(x.get('serial',0)) > self.lastpoll: self.lastpoll = int(x.get('serial',0))
            content = x.get('content',None)
            if content and not content.get('msgid', '') in self.own_msgids:
                for a in self.agents:
                    a.dispatch_message(content)


class ThreadedComm(CommBase):
    class AgentProxy(object):
        def __init__(self, tc):
            self.tc = tc
        def dispatch_message(self, content):
            self.tc.receive_queue.put(content)

    def __init__(self, upstream_comm):
        super(ThreadedComm, self).__init__()
        self.upstream_comm = upstream_comm
        self.send_queue = Queue.Queue()
        self.receive_queue = Queue.Queue()
        self.comm_thread = CommThread(self, upstream_comm)
        upstream_comm.add_agent(self.AgentProxy(self))
    
    def post_message(self, content):
        self.send_queue.put(content)

    def poll_and_dispatch(self):
        while not self.receive_queue.empty():
            content = self.receive_queue.get()
            for a in self.agents:
                a.dispatch_message(content)

    def start(self):
        self.comm_thread.start()

    def stop(self):
        self.comm_thread.stop()
        self.comm_thread.join()


class CommThread(threading.Thread):
    def __init__(self, threaded_comm, upstream_comm):
        threading.Thread.__init__(self)
        self._stop = threading.Event()
        self.threaded_comm = threaded_comm
        self.upstream_comm = upstream_comm

    def run(self):
        send_queue = self.threaded_comm.send_queue
        receive_queue = self.threaded_comm.receive_queue
        while not self._stop.is_set():
            while not send_queue.empty():
                self.upstream_comm.post_message(send_queue.get())
            self.upstream_comm.poll_and_dispatch()
            time.sleep(1)

    def stop(self):
        self._stop.set()

########NEW FILE########
__FILENAME__ = ewctrl
from collections import defaultdict

from coloredcoinlib import (ColorSet, ColorTarget, UNCOLORED_MARKER,
                            InvalidColorIdError, ZeroSelectError,
                            SimpleColorValue, CTransaction)
from protocol_objects import ETxSpec
from ngcccbase.asset import AdditiveAssetValue
from ngcccbase.txcons import (BaseOperationalTxSpec,
                              SimpleOperationalTxSpec, InsufficientFundsError)
from ngcccbase.coindb import UTXO

import bitcoin.core
from bitcoin.wallet import CBitcoinAddress


class OperationalETxSpec(SimpleOperationalTxSpec):
    def __init__(self, model, ewctrl):
        self.model = model
        self.ewctrl = ewctrl
        self.our_value_limit = None

    def get_targets(self):
        return self.targets

    def get_change_addr(self, color_def):
        color_id = color_def.color_id
        cs = ColorSet.from_color_ids(self.model.get_color_map(), [color_id])
        wam = self.model.get_address_manager()
        return wam.get_change_address(cs).get_address()

    def set_our_value_limit(self, our):
        our_colordef = self.ewctrl.resolve_color_spec(our['color_spec'])
        self.our_value_limit = SimpleColorValue(colordef=our_colordef,
                                                value=our['value'])      

    def prepare_inputs(self, etx_spec):
        self.inputs = defaultdict(list)
        colordata = self.model.ccc.colordata
        for color_spec, inps in etx_spec.inputs.items():
            colordef = self.ewctrl.resolve_color_spec(color_spec)
            color_id_set = set([colordef.get_color_id()])
            for inp in inps:
                txhash, outindex = inp
                tx = self.model.ccc.blockchain_state.get_tx(txhash)
                prevout = tx.outputs[outindex]
                utxo = UTXO({"txhash": txhash,
                             "outindex": outindex,
                             "value": prevout.value,
                             "script": prevout.script})
                colorvalue = None
                if colordef == UNCOLORED_MARKER:
                    colorvalue = SimpleColorValue(colordef=UNCOLORED_MARKER,
                                                  value=prevout.value)
                else:
                    css = colordata.get_colorvalues(color_id_set,
                                                    txhash,
                                                    outindex)
                    if (css and len(css) == 1):
                        colorvalue = css[0]
                if colorvalue:
                    self.inputs[colordef.get_color_id()].append(
                        (colorvalue, utxo))

    def prepare_targets(self, etx_spec, their):
        self.targets = []
        for address, color_spec, value in etx_spec.targets:
            colordef = self.ewctrl.resolve_color_spec(color_spec)
            self.targets.append(ColorTarget(address, 
                                       SimpleColorValue(colordef=colordef,
                                                        value=value)))
        wam = self.model.get_address_manager()
        colormap = self.model.get_color_map()
        their_colordef = self.ewctrl.resolve_color_spec(their['color_spec'])
        their_color_set = ColorSet.from_color_ids(self.model.get_color_map(),
                                                  [their_colordef.get_color_id()])
        ct = ColorTarget(wam.get_change_address(their_color_set).get_address(),
                         SimpleColorValue(colordef=their_colordef,
                                          value=their['value']))
        self.targets.append(ct)

    def select_uncolored_coins(self, colorvalue, use_fee_estimator):
        selected_inputs = []
        selected_value = SimpleColorValue(colordef=UNCOLORED_MARKER,
                                          value=0)
        needed = colorvalue + use_fee_estimator.estimate_required_fee()
        color_id = 0
        if color_id in self.inputs:
            total = SimpleColorValue.sum([cv_u[0]
                                          for cv_u in self.inputs[color_id]])
            needed -= total
            selected_inputs += [cv_u[1]
                               for cv_u in self.inputs[color_id]]
            selected_value += total
        if needed > 0:
            value_limit = SimpleColorValue(colordef=UNCOLORED_MARKER,
                                           value=10000+8192*2)
            if self.our_value_limit.is_uncolored():
                value_limit += self.our_value_limit
            if needed > value_limit:
                raise InsufficientFundsError("exceeded limits: %s requested, %s found"
                                             % (needed, value_limit))
            our_inputs, our_value = super(OperationalETxSpec, self).\
                select_coins(colorvalue - selected_value, use_fee_estimator)
            selected_inputs += our_inputs
            selected_value += our_value
        return selected_inputs, selected_value

    def select_coins(self, colorvalue, use_fee_estimator=None):
        self._validate_select_coins_parameters(colorvalue, use_fee_estimator)
        colordef = colorvalue.get_colordef()
        if colordef == UNCOLORED_MARKER:
            return self.select_uncolored_coins(colorvalue, use_fee_estimator)

        color_id = colordef.get_color_id()
        if color_id in self.inputs:
            # use inputs provided in proposal
            total = SimpleColorValue.sum([cv_u[0]
                                          for cv_u in self.inputs[color_id]])
            if total < colorvalue:
                raise InsufficientFundsError('not enough coins: %s requested, %s found'
                                             % (colorvalue, total))
            return [cv_u[1] for cv_u in self.inputs[color_id]], total
        
        if colorvalue != self.our_value_limit:
            raise InsufficientFundsError("%s requested, %s found"
                                         % (colorvalue, our_value_limit))
        return super(OperationalETxSpec, self).select_coins(colorvalue)


class EWalletController(object):
    def __init__(self, model, wctrl):
        self.model = model
        self.wctrl = wctrl

    def publish_tx(self, raw_tx, my_offer):
        txhash = raw_tx.get_hex_txhash()
        self.model.tx_history.add_trade_entry(
            txhash,
            self.offer_side_to_colorvalue(my_offer.B),
            self.offer_side_to_colorvalue(my_offer.A))
        self.wctrl.publish_tx(raw_tx)


    def check_tx(self, raw_tx, etx_spec):
        """check if raw tx satisfies spec's targets"""
        bctx = bitcoin.core.CTransaction.deserialize(raw_tx.get_tx_data())
        ctx = CTransaction.from_bitcoincore(raw_tx.get_hex_txhash(),
                                            bctx,
                                            self.model.ccc.blockchain_state)
        color_id_set = set([])
        targets = []
        for target in etx_spec.targets:
            our_address, color_spec, value = target
            raw_addr = CBitcoinAddress(our_address)
            color_def = self.resolve_color_spec(color_spec)
            color_id = color_def.get_color_id()
            color_id_set.add(color_id)
            targets.append((raw_addr, color_id, value))

        used_outputs = set([])
        satisfied_targets = set([])
        
        for color_id in color_id_set:
            if color_id == 0:
                continue
            out_colorvalues = self.model.ccc.colordata.get_colorvalues_raw(
                color_id, ctx)
            print out_colorvalues
            for oi in range(len(ctx.outputs)):
                if oi in used_outputs:
                    continue
                if out_colorvalues[oi]:
                    for target in targets:
                        if target in satisfied_targets:
                            continue
                        raw_address, tgt_color_id, value = target
                        if ((tgt_color_id == color_id) and
                            (value == out_colorvalues[oi].get_value()) and
                            (raw_address == ctx.outputs[oi].raw_address)):
                                satisfied_targets.add(target)
                                used_outputs.add(oi)
        for target in targets:
            if target in satisfied_targets:
                continue
            raw_address, tgt_color_id, value = target
            if tgt_color_id == 0:
                for oi in range(len(ctx.outputs)):
                    if oi in used_outputs:
                        continue
                    if ((value == ctx.outputs[oi].value) and
                        (raw_address == ctx.outputs[oi].raw_address)):
                        satisfied_targets.add(target)
                        used_outputs.add(oi)
        return len(targets) == len(satisfied_targets)

    def resolve_color_spec(self, color_spec):
        colormap = self.model.get_color_map()
        return colormap.get_color_def(color_spec)

    def offer_side_to_colorvalue(self, side):
        colordef = self.resolve_color_spec(side['color_spec'])
        return SimpleColorValue(colordef=colordef,
                                value=side['value'])

    def select_inputs(self, colorvalue):
        op_tx_spec = SimpleOperationalTxSpec(self.model, None)
        if colorvalue.is_uncolored():
            composed_tx_spec = op_tx_spec.make_composed_tx_spec()
            selection, total = op_tx_spec.select_coins(colorvalue, composed_tx_spec)
            change = total - colorvalue - \
                composed_tx_spec.estimate_required_fee(extra_txins=len(selection))
            if change < op_tx_spec.get_dust_threshold():
                change = SimpleColorValue(colordef=UNCOLORED_MARKER,
                                          value=0)
            return selection, change            
        else:
            selection, total = op_tx_spec.select_coins(colorvalue)
            change = total - colorvalue
            return selection, change
    
    def make_etx_spec(self, our, their):
        our_color_def = self.resolve_color_spec(our['color_spec'])
        our_color_set = ColorSet.from_color_ids(self.model.get_color_map(),
                                                  [our_color_def.get_color_id()])
        their_color_def = self.resolve_color_spec(their['color_spec'])
        their_color_set = ColorSet.from_color_ids(self.model.get_color_map(),
                                                  [their_color_def.get_color_id()])
        extra_value = 0
        if our_color_def == UNCOLORED_MARKER:
            # pay fee + padding for one colored outputs
            extra_value = 10000 + 8192 * 1
        c_utxos, c_change = self.select_inputs(
            SimpleColorValue(colordef=our_color_def,
                             value=our['value'] + extra_value))
        inputs = {our['color_spec']: 
                  [utxo.get_outpoint() for utxo in c_utxos]}
        wam = self.model.get_address_manager()
        our_address = wam.get_change_address(their_color_set)
        targets = [(our_address.get_address(),
                    their['color_spec'], their['value'])]
        if c_change > 0:
            our_change_address = wam.get_change_address(our_color_set)
            targets.append((our_change_address.get_address(),
                            our['color_spec'], c_change.get_value()))
        return ETxSpec(inputs, targets, c_utxos)

    def make_reply_tx(self, etx_spec, our, their):
        op_tx_spec = OperationalETxSpec(self.model, self)
        op_tx_spec.set_our_value_limit(our)
        op_tx_spec.prepare_inputs(etx_spec)
        op_tx_spec.prepare_targets(etx_spec, their)
        signed_tx = self.model.transform_tx_spec(op_tx_spec, 'signed')
        return signed_tx

########NEW FILE########
__FILENAME__ = protocol_objects
import time

from coloredcoinlib import IncompatibleTypesError
from ngcccbase.txcons import RawTxSpec

from utils import make_random_id


class EOffer(object):
    """
    A is the offer side's ColorValue
    B is the replyer side's ColorValue
    """
    def __init__(self, oid, A, B):
        self.oid = oid or make_random_id()
        self.A = A
        self.B = B
        self.expires = None

    def expired(self, shift=0):
        return (not self.expires) or (self.expires < time.time() + shift)

    def refresh(self, delta):
        self.expires = time.time() + delta

    def get_data(self):
        return {"oid": self.oid,
                "A": self.A,
                "B": self.B}

    def matches(self, offer):
        """A <=x=> B"""
        return self.A == offer.B and offer.A == self.B

    def is_same_as_mine(self, my_offer):
        return self.A == my_offer.A and self.B == my_offer.B

    @classmethod
    def from_data(cls, data):
        # TODO: verification
        x = cls(data["oid"], data["A"], data["B"])
        return x


class MyEOffer(EOffer):
    def __init__(self, oid, A, B, auto_post=True):
        super(MyEOffer, self).__init__(oid, A, B)
        self.auto_post = auto_post


class ETxSpec(object):
    def __init__(self, inputs, targets, my_utxo_list=None):
        self.inputs = inputs
        self.targets = targets
        self.my_utxo_list = my_utxo_list

    def get_data(self):
        return {"inputs": self.inputs,
                "targets": self.targets}

    @classmethod
    def from_data(cls, data):
        return cls(data['inputs'], data['targets'])


class EProposal(object):
    def __init__(self, pid, ewctrl, offer):
        self.pid = pid
        self.ewctrl = ewctrl
        self.offer = offer

    def get_data(self):
        return {"pid": self.pid,
                "offer": self.offer.get_data()}


class MyEProposal(EProposal):
    def __init__(self, ewctrl, orig_offer, my_offer):
        super(MyEProposal, self).__init__(make_random_id(),
                                          ewctrl, orig_offer)
        self.my_offer = my_offer
        if not orig_offer.matches(my_offer):
            raise Exception("offers are incongruent")
        self.etx_spec = ewctrl.make_etx_spec(self.offer.B, self.offer.A)
        self.etx_data = None

    def get_data(self):
        res = super(MyEProposal, self).get_data()
        if self.etx_data:
            res["etx_data"] = self.etx_data
        else:
            res["etx_spec"] = self.etx_spec.get_data()
        return res

    def process_reply(self, reply_ep):
        rtxs = RawTxSpec.from_tx_data(self.ewctrl.model,
                                      reply_ep.etx_data.decode('hex'))
        if self.ewctrl.check_tx(rtxs, self.etx_spec):
            rtxs.sign(self.etx_spec.my_utxo_list)
            # TODO: ???
            self.ewctrl.publish_tx(rtxs, self.my_offer) 
            self.etx_data = rtxs.get_hex_tx_data()
        else:
            raise Exception('p2ptrade reply tx check failed')


class MyReplyEProposal(EProposal):
    def __init__(self, ewctrl, foreign_ep, my_offer):
        super(MyReplyEProposal, self).__init__(foreign_ep.pid,
                                             ewctrl,
                                             foreign_ep.offer)
        self.my_offer = my_offer
        self.tx = self.ewctrl.make_reply_tx(foreign_ep.etx_spec, 
                                            my_offer.A,
                                            my_offer.B)
        
    def get_data(self):
        data = super(MyReplyEProposal, self).get_data()
        data['etx_data'] = self.tx.get_hex_tx_data()
        return data

    def process_reply(self, reply_ep):
        rtxs = RawTxSpec.from_tx_data(self.ewctrl.model,
                                      reply_ep.etx_data.decode('hex'))
        self.ewctrl.publish_tx(rtxs, self.my_offer) # TODO: ???
        

class ForeignEProposal(EProposal):
    def __init__(self, ewctrl, ep_data):
        offer = EOffer.from_data(ep_data['offer'])
        super(ForeignEProposal, self).__init__(ep_data['pid'], ewctrl, offer)
        self.etx_spec = None
        if 'etx_spec' in ep_data:
            self.etx_spec = ETxSpec.from_data(ep_data['etx_spec'])
        self.etx_data = ep_data.get('etx_data', None)

    def accept(self, my_offer):
        if not self.offer.is_same_as_mine(my_offer):
            raise Exception("incompatible offer")          # pragma: no cover
        if not self.etx_spec:
            raise Exception("need etx_spec")               # pragma: no cover
        return MyReplyEProposal(self.ewctrl, self, my_offer)

########NEW FILE########
__FILENAME__ = test_agent
#!/usr/bin/env python

import time
import unittest

from coloredcoinlib import (SimpleColorValue, UNCOLORED_MARKER, ColorDefinition,
                            AidedColorDataBuilder, ThinColorData,
                            InvalidColorIdError, ZeroSelectError,
                            OBColorDefinition, ColorDataBuilderManager)

from ngcccbase.pwallet import PersistentWallet
from ngcccbase.wallet_controller import WalletController

from ngcccbase.p2ptrade.agent import EAgent
from ngcccbase.p2ptrade.comm import CommBase
from ngcccbase.p2ptrade.ewctrl import EWalletController, OperationalETxSpec
from ngcccbase.p2ptrade.protocol_objects import MyEOffer, EOffer, MyEProposal


class MockComm(CommBase):
    def __init__(self):
        super(MockComm, self).__init__()
        self.agents = []
        self.peers = []
        self.messages_sent = []
    def poll_and_dispatch(self):
        pass
    def add_agent(self, agent):
        self.agents.append(agent)
    def add_peer(self, peer):
        self.peers.append(peer)
    def post_message(self, content):
        print (content)
        for peer in self.peers:
            peer.process_message(content)
    def process_message(self, content):
        for agent in self.agents:
            agent.dispatch_message(content)
        self.messages_sent.append(content)
    def get_messages(self):
        return self.messages_sent


class TestAgent(unittest.TestCase):
    def setUp(self):
        self.path = ":memory:"
        self.config = {
            'hdw_master_key':
                '91813223e97697c42f05e54b3a85bae601f04526c5c053ff0811747db77cfdf5f1accb50b3765377c379379cd5aa512c38bf24a57e4173ef592305d16314a0f4',
            'testnet': True,
            'ccc': {'colordb_path' : self.path},
            }
        self.pwallet = PersistentWallet(self.path, self.config)
        self.pwallet.init_model()
        self.model = self.pwallet.get_model()
        self.wc = WalletController(self.model)
        self.ewc = EWalletController(self.model, self.wc)
        self.econfig = {"offer_expiry_interval": 30,
                        "ep_expiry_interval": 30}
        self.comm0 = MockComm()
        self.comm1 = MockComm()
        self.comm0.add_peer(self.comm1)
        self.comm1.add_peer(self.comm0)
        self.agent0 = EAgent(self.ewc, self.econfig, self.comm0)
        self.agent1 = EAgent(self.ewc, self.econfig, self.comm1)
        self.cspec = "obc:03524a4d6492e8d43cb6f3906a99be5a1bcd93916241f759812828b301f25a6c:0:153267"

    def add_coins(self):
        self.config['asset_definitions'] = [
            {"color_set": [""], "monikers": ["bitcoin"], "unit": 100000000},  
            {"color_set": [self.cspec], "monikers": ['test'], "unit": 1},]
        self.config['hdwam'] = {
            "genesis_color_sets": [ 
                [self.cspec],
                ],
            "color_set_states": [
                {"color_set": [""], "max_index": 1},
                {"color_set": [self.cspec], "max_index": 7},
                ]
            }
        self.config['bip0032'] = True
        self.pwallet = PersistentWallet(self.path, self.config)
        self.pwallet.init_model()
        self.model = self.pwallet.get_model()
        self.ewc.model = self.model
        self.wc.model = self.model
        def null(a):
            pass
        self.wc.publish_tx = null
        # modify model colored coin context, so test runs faster
        ccc = self.model.ccc
        cdbuilder = ColorDataBuilderManager(
            ccc.colormap, ccc.blockchain_state, ccc.cdstore,
            ccc.metastore, AidedColorDataBuilder)

        ccc.colordata = ThinColorData(
            cdbuilder, ccc.blockchain_state, ccc.cdstore, ccc.colormap)

        # need to query the blockchain
        self.model.utxo_man.update_all()

        adm = self.model.get_asset_definition_manager()
        asset = adm.get_asset_by_moniker('test')
        cq = self.model.make_coin_query({"asset": asset})
        utxo_list = cq.get_result()

        self.cd = ColorDefinition.from_color_desc(1, self.cspec)

        self.cv0 = SimpleColorValue(colordef=UNCOLORED_MARKER, value=100)
        self.cv1 = SimpleColorValue(colordef=self.cd, value=200)

        self.offer0 = MyEOffer(None, self.cv0, self.cv1)
        self.offer1 = MyEOffer(None, self.cv1, self.cv0)

    def test_set_event_handler(self):
        tmp = { 'test': 0}
        def handler(val):
            tmp['test'] = val
        self.agent0.set_event_handler('click', handler)
        self.agent0.fire_event('click', 7)
        self.assertEqual(tmp['test'], 7)
        self.agent0.ep_timeout = time.time() - 100
        self.assertFalse(self.agent0.has_active_ep())

    def test_real(self):
        self.add_coins()
        self.assertFalse(self.agent0.has_active_ep())
        self.agent0.register_my_offer(self.offer0)
        self.agent1.register_my_offer(self.offer1)
        for i in range(3):
            self.agent0._update_state()
            self.agent1._update_state()
        self.assertFalse(self.agent0.has_active_ep())
        self.assertFalse(self.agent1.has_active_ep())

        m0 = self.comm0.get_messages()
        m1 = self.comm1.get_messages()
        self.assertEquals(len(m0), 2)
        self.assertEquals(len(m1), 2)

        self.assertEquals(self.offer0.get_data(), m0[1]['offer'])
        self.assertEquals(self.offer0.get_data(), m1[1]['offer'])
        # expire offers
        offer2 = MyEOffer(None, self.cv0, self.cv1)

        self.agent0.register_my_offer(offer2)
        self.agent0.update()
        self.agent0.update()
        self.agent1.update()
        self.agent0.cancel_my_offer(offer2)
        self.agent0.update()
        self.agent1.update()
        self.assertFalse(self.agent0.has_active_ep())
        self.assertFalse(self.agent1.has_active_ep())

        offer3 = MyEOffer(None, self.cv1, self.cv0)
        self.agent0.make_exchange_proposal(offer3, offer2)
        self.assertRaises(Exception, self.agent0.make_exchange_proposal,
                          offer3, offer2)
        ep = MyEProposal(self.ewc, offer3, offer2)
        def raiseException(x):
            raise Exception()
        self.agent0.set_event_handler('accept_ep', raiseException)

        # methods that should do nothing now that we have an active ep
        self.agent0.accept_exchange_proposal(ep)
        self.agent0.match_offers()

        self.agent0.register_their_offer(offer3)
        self.agent0.accept_exchange_proposal(ep)
        ep2 = MyEProposal(self.ewc, offer3, offer2)
        self.agent0.dispatch_exchange_proposal(ep2.get_data())

        # test a few corner cases
        self.agent0.register_my_offer(offer2)
        offer2.refresh(-1000)
        self.assertTrue(offer2.expired())
        self.agent0.service_my_offers()
        self.agent0.cancel_my_offer(offer2)
        self.agent0.register_their_offer(offer3)
        offer3.refresh(-1000)
        self.agent0.service_their_offers()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_basic
from ..ewctrl import EWalletController
from ..protocol_objects import MyEOffer, EOffer
from ..agent import EAgent
from ..comm import CommBase

from coloredcoinlib import (SimpleColorValue,
                            OBColorDefinition, UNCOLORED_MARKER)

import unittest


class MockAddressRecord(object):
    def __init__(self, address):
        self.address = address
    def get_address(self):
        return self.address

class MockWAM(object):
    def get_change_address(self, color_set):
        return MockAddressRecord('addr' + color_set.get_hash_string())
    def get_some_address(self, color_set):
        return self.get_change_address(color_set)


class MockUTXO(object):
    def __init__(self):
        self.value = 100
        self.colorvalues = [SimpleColorValue(colordef=UNCOLORED_MARKER,
                                             value=300000)]
    def get_outpoint(self):
        return ('outp1', 1)

class MockCoinQuery(object):

    def __init__(self, params):
        self.color_set = params['color_set']

    def get_result(self):
        return [MockUTXO()]

class MockColorMap(object):
    def find_color_desc(self, color_id):
        if color_id == 1:
            return 'xxx'
        elif color_id == 2:
            return 'yyy'
        else:
            return ''

    def resolve_color_desc(self, color_desc, auto_add=True):
        if color_desc == 'xxx':
            return 1
        elif color_desc == 'yyy':
            return 2
        else:
            return None

class MockModel(object):
    def get_color_map(self):
        return MockColorMap()
    def make_coin_query(self, params):
        return MockCoinQuery(params)
    def get_address_manager(self):
        return MockWAM()

class MockComm(CommBase):
    def __init__(self):
        super(MockComm, self).__init__()
        self.messages_sent = []
    def poll_and_dispatch(self):
        pass
    def post_message(self, message):
        print (message)
        self.messages_sent.append(message)
    def get_messages(self):
        return self.messages_sent

class TestMockP2PTrade(unittest.TestCase):
    def test_basic(self):
        model = MockModel()
        ewctrl = EWalletController(model, None)
        config = {"offer_expiry_interval": 30,
                  "ep_expiry_interval": 30}
        comm = MockComm()
        agent = EAgent(ewctrl, config, comm)

        # At this point the agent should not have an active proposal
        self.assertFalse(agent.has_active_ep())
        # no messages should have been sent to the network
        self.assertEqual(len(comm.get_messages()), 0)

        self.cd = OBColorDefinition(1, {'txhash': 'xxx',
                                        'outindex': 0, 'height':0})

        cv0 = SimpleColorValue(colordef=UNCOLORED_MARKER, value=100)
        cv1 = SimpleColorValue(colordef=self.cd, value=200)

        my_offer = MyEOffer(None, cv0, cv1)

        their_offer = EOffer('abcdef', cv1, cv0)

        agent.register_my_offer(my_offer)
        agent.register_their_offer(their_offer)
        agent.update()

        # Agent should have an active exchange proposal
        self.assertTrue(agent.has_active_ep())
        # Exchange proposal should have been sent over comm
        # it should be the only message, as we should not resend our offer
        # if their is an active proposal to match it
        self.assertTrue(len(comm.get_messages()), 1)
        [proposal] = comm.get_messages()
        # The offer data should be in the proposal
        their_offer_data = their_offer.get_data()
        self.assertEquals(their_offer_data, proposal["offer"])

########NEW FILE########
__FILENAME__ = test_comm
#!/usr/bin/env python

import SocketServer
import SimpleHTTPServer
import threading
import time
import unittest

from ngcccbase.p2ptrade.comm import HTTPComm, ThreadedComm, CommThread


class MockAgent(object):
    def dispatch_message(self, m):
        pass

class TestServer(threading.Thread):
    def __init__(self, address, port):
        super(TestServer, self).__init__()
        self.httpd = SocketServer.TCPServer((address, port), TestHandler)
    def run(self):
        self.httpd.serve_forever()
    def shutdown(self):
        self.httpd.shutdown()
        self.httpd.socket.close()


class TestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def do_response(self, response):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Content-length", len(response))
        self.end_headers()
        self.wfile.write(response)
        
    def do_POST(self):
        self.do_response("Success")

    def do_GET(self):
        self.do_response('[{"content": {"msgid":1, "a":"blah"}, "serial": 1}]')
        

class TestComm(unittest.TestCase):

    def setUp(self):
        self.config = {"offer_expiry_interval": 30, "ep_expiry_interval": 30}
        self.hcomm = HTTPComm(self.config)
        self.msg = {"msgid": 2, "a": "b"}
        self.httpd = TestServer("localhost", 8080)
        self.httpd.start()
        self.tcomm = ThreadedComm(self.hcomm)
        self.tcomm.add_agent(MockAgent())

    def tearDown(self):
        self.httpd.shutdown()

    def test_post_message(self):
        self.assertTrue(self.hcomm.post_message(self.msg))

    def test_poll_and_dispatch(self):
        self.hcomm.poll_and_dispatch()
        self.assertEqual(self.hcomm.lastpoll, 1)
        self.hcomm.poll_and_dispatch()
        self.assertEqual(self.hcomm.lastpoll, 1)

    def test_threadcomm(self):
        self.tcomm.start()
        time.sleep(2)
        self.hcomm.post_message(self.msg)
        self.tcomm.post_message(self.msg)
        self.tcomm.poll_and_dispatch()
        time.sleep(2)
        self.tcomm.stop()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_ewctrl
#!/usr/bin/env python

import unittest

from coloredcoinlib import (ColorSet, ColorDataBuilderManager, ColorTarget,
                            AidedColorDataBuilder, ThinColorData,
                            InvalidColorIdError, ZeroSelectError,
                            SimpleColorValue, UNCOLORED_MARKER)

from ngcccbase.pwallet import PersistentWallet
from ngcccbase.txcons import InsufficientFundsError, RawTxSpec
from ngcccbase.wallet_controller import WalletController

from ngcccbase.p2ptrade.ewctrl import EWalletController, OperationalETxSpec
from ngcccbase.p2ptrade.protocol_objects import ETxSpec


class TestEWalletController(unittest.TestCase):

    def setUp(self):
        self.path = ":memory:"
        self.config = {
            'hdw_master_key':
                '91813223e97697c42f05e54b3a85bae601f04526c5c053ff0811747db77cfdf5f1accb50b3765377c379379cd5aa512c38bf24a57e4173ef592305d16314a0f4',
            'testnet': True,
            'ccc': {'colordb_path' : self.path},
            }
        self.pwallet = PersistentWallet(self.path, self.config)
        self.pwallet.init_model()
        self.model = self.pwallet.get_model()
        self.wc = WalletController(self.model)

        self.ewc = EWalletController(self.model, self.wc)
        self.bcolorset =self.ewc.resolve_color_spec('')
        self.cspec = "obc:03524a4d6492e8d43cb6f3906a99be5a1bcd93916241f759812828b301f25a6c:0:153267"

    def add_coins(self):
        self.config['asset_definitions'] = [
            {"color_set": [""], "monikers": ["bitcoin"], "unit": 100000000},  
            {"color_set": [self.cspec], "monikers": ['test'], "unit": 1},]
        self.config['hdwam'] = {
            "genesis_color_sets": [ 
                [self.cspec],
                ],
            "color_set_states": [
                {"color_set": [""], "max_index": 1},
                {"color_set": [self.cspec], "max_index": 7},
                ]
            }
        self.config['bip0032'] = True
        self.pwallet = PersistentWallet(self.path, self.config)
        self.pwallet.init_model()
        self.model = self.pwallet.get_model()
        self.ewc.model = self.model
        self.wc.model = self.model
        # modify model colored coin context, so test runs faster
        ccc = self.model.ccc
        cdbuilder = ColorDataBuilderManager(
            ccc.colormap, ccc.blockchain_state, ccc.cdstore,
            ccc.metastore, AidedColorDataBuilder)

        ccc.colordata = ThinColorData(
            cdbuilder, ccc.blockchain_state, ccc.cdstore, ccc.colormap)

        # need to query the blockchain
        self.model.utxo_man.update_all()

        adm = self.model.get_asset_definition_manager()
        asset = adm.get_asset_by_moniker('test')
        cq = self.model.make_coin_query({"asset": asset})
        utxo_list = cq.get_result()


    def test_resolve_color_spec(self):
        self.assertRaises(InvalidColorIdError,
                          self.ewc.resolve_color_spec, 'nonexistent')
        self.assertTrue(isinstance(self.bcolorset, ColorSet))
        self.assertEqual(self.bcolorset.color_id_set, set([0]))

    def test_select_inputs(self):
        cv = SimpleColorValue(colordef=UNCOLORED_MARKER, value=1)
        self.assertRaises(InsufficientFundsError, self.ewc.select_inputs, cv)
        
    def test_tx_spec(self):
        self.add_colors()

        our = SimpleColorValue(colordef=UNCOLORED_MARKER, value=500)
        colormap = self.model.get_color_map()
        colordef = colormap.get_color_def(self.cspec)
        their = SimpleColorValue(colordef=colordef, value=10)
        etx = self.ewc.make_etx_spec(our, their)
        self.assertTrue(isinstance(etx, ETxSpec))
        for target in etx.targets:
            self.assertTrue(isinstance(target, ColorTarget))
        signed = self.ewc.make_reply_tx(etx, our, their)
        self.assertTrue(isinstance(signed, RawTxSpec))

        self.ewc.publish_tx(signed)

        etx = self.ewc.make_etx_spec(their, our)
        self.assertTrue(isinstance(etx, ETxSpec))
        for target in etx.targets:
            self.assertTrue(isinstance(target, ColorTarget))
        signed = self.ewc.make_reply_tx(etx, their, our)
        self.assertTrue(isinstance(signed, RawTxSpec))

        oets = OperationalETxSpec(self.model, self.ewc)
        zero = SimpleColorValue(colordef=UNCOLORED_MARKER, value=0)
        self.assertRaises(ZeroSelectError, oets.select_coins, zero)
        toomuch = SimpleColorValue(colordef=UNCOLORED_MARKER, value=10000000000000)
        self.assertRaises(InsufficientFundsError, oets.select_coins, toomuch)

        


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_protocol_objects
#!/usr/bin/env python

import unittest

from coloredcoinlib import (ColorSet, OBColorDefinition, POBColorDefinition,
                            SimpleColorValue)

from ngcccbase.p2ptrade.protocol_objects import (
    EOffer, MyEOffer, ETxSpec, EProposal, MyEProposal,
    MyReplyEProposal, ForeignEProposal)


class TestEOffer(unittest.TestCase):

    def setUp(self):
        self.colordef0 = POBColorDefinition(
            1, {'txhash': 'genesis', 'outindex': 0})
        self.colordef1 = OBColorDefinition(
            2, {'txhash': 'genesis', 'outindex': 0})
        self.colorvalue0 = SimpleColorValue(colordef=self.colordef0,
                                    value=1, label='test')
        self.colorvalue1 = SimpleColorValue(colordef=self.colordef0,
                                    value=2, label='test2')
        self.colorvalue2 = SimpleColorValue(colordef=self.colordef1,
                                    value=1)

        self.e0 = MyEOffer.from_data({'oid':1,
                                      'A': self.colorvalue0,
                                      'B': self.colorvalue1 })
        self.e1 = MyEOffer.from_data({'oid':2,
                                      'A': self.colorvalue0,
                                      'B': self.colorvalue1 })

    def test_expired(self):
        self.e0.refresh(100000)
        self.assertFalse(self.e0.expired())

    def test_get_data(self):
        self.assertEqual(self.e0.get_data()['A'], self.e1.get_data()['A'])

    def test_matches(self):
        self.assertFalse(self.e0.matches(self.e1))
        self.e1.A = self.colorvalue1
        self.e1.B = self.colorvalue0
        self.assertTrue(self.e0.matches(self.e1))

    def test_is_same(self):
        self.assertTrue(self.e0.is_same_as_mine(self.e1))
        self.e0.A = self.colorvalue2
        self.assertFalse(self.e0.is_same_as_mine(self.e1))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_real
#!/usr/bin/env python

import unittest

from ngcccbase.p2ptrade.ewctrl import EWalletController
from ngcccbase.p2ptrade.protocol_objects import MyEOffer, EOffer
from ngcccbase.p2ptrade.agent import EAgent

class MockComm(object):
    def __init__(self):
        self.agents = []
        self.peers = []
    def add_agent(self, agent):
        self.agents.append(agent)
    def add_peer(self, peer):
        self.peers.append(peer)
    def post_message(self, content):
        print (content)
        for peer in self.peers:
            peer.process_message(content)
    def process_message(self, content):
        for agent in self.agents:
            agent.dispatch_message(content)


class TestRealP2PTrade(unittest.TestCase):

    def setUp(self):
        from ngcccbase.pwallet import PersistentWallet
        from ngcccbase.wallet_controller import WalletController
        self.pwallet = PersistentWallet()
        self.pwallet.init_model()
        self.wctrl = WalletController(self.pwallet.wallet_model)

    def test_real(self):
        ewctrl = EWalletController(self.pwallet.get_model(), self.wctrl)
        config = {"offer_expiry_interval": 30,
                  "ep_expiry_interval": 30}
        comm1 = MockComm()
        comm2 = MockComm()
        comm1.add_peer(comm2)
        comm2.add_peer(comm1)
        agent1 = EAgent(ewctrl, config, comm1)
        agent2 = EAgent(ewctrl, config, comm2)

        frobla_color_desc = "obc:cc8e64cef1a880f5132e73b5a1f52a72565c92afa8ec36c445c635fe37b372fd:0:263370"
        foo_color_desc = "obc:caff27b3fe0a826b776906aceafecac7bb34af16971b8bd790170329309391ac:0:265577"

        self.cd0 = OBColorDefinition(1, {'txhash': 'cc8e64cef1a880f5132e73b5a1f52a72565c92afa8ec36c445c635fe37b372fd',
                                         'outindex': 0, 'height':263370})

        self.cd1 = OBColorDefinition(1, {'txhash': 'caff27b3fe0a826b776906aceafecac7bb34af16971b8bd790170329309391ac',
                                         'outindex': 0, 'height':265577})

        cv0 = SimpleColorValue(colordef=self.cd0, value=100)
        cv1 = SimpleColorValue(colordef=self.cd1, value=200)

        ag1_offer = MyEOffer(None, cv0, cv1)
        ag2_offer = MyEOffer(None, cv0, cv1, False)

        agent1.register_my_offer(ag1_offer)
        agent2.register_my_offer(ag2_offer)
        for _ in xrange(3):
            agent1._update_state()
            agent2._update_state()
        

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = utils
import os
import binascii


def LOGINFO(msg, *params):
    print (msg % params)


def LOGDEBUG(msg, *params):
    print (msg % params)


def LOGERROR(msg, *params):
    print (msg % params)


def make_random_id():
    bits = os.urandom(8)
    return binascii.hexlify(bits)

########NEW FILE########
__FILENAME__ = pwallet
"""
pwallet.py

A colored-coin wallet implementation that uses a persistent
data-store. The actual storage is in sqlite3 db's via coloredcoinlib
"""

from wallet_model import WalletModel
from coloredcoinlib import store
import sqlite3
import os


class PersistentWallet(object):
    """Represents a wallet object that stays persistent.
    That is, it doesn't go away every time you run the program.
    """

    def __init__(self, wallet_path, testnet):
        """Create a persistent wallet. If a configuration is passed
        in, put that configuration into the db by overwriting
        the relevant data, never deleting. Otherwise, load with
        the configuration from the persistent data-store.
        """
        if wallet_path is None:
            if testnet:
                wallet_path = "testnet.wallet"
            else:
                wallet_path = "mainnet.wallet"
        new_wallet = not os.path.exists(wallet_path)
        self.store_conn = store.DataStoreConnection(wallet_path, True)
        self.store_conn.conn.row_factory = sqlite3.Row
        self.wallet_config = store.PersistentDictStore(
            self.store_conn.conn, "wallet")
        if new_wallet:
            self.initialize_new_wallet(testnet)
        if testnet and not self.wallet_config['testnet']:
            raise Exception("not a testnet wallet")
        self.wallet_model = None

    def init_model(self):
        """Associate the wallet model based on the persistent
        configuration.
        """
        self.wallet_model = WalletModel(
            self.wallet_config, self.store_conn)

    def initialize_new_wallet(self, testnet):
        """New wallets are born in testnet mode until we have a version 
        which is safe to be used on mainnet.
        """
        self.wallet_config['testnet'] = testnet

    def get_model(self):
        """Pass back the model associated with the persistent
        wallet.
        """
        return self.wallet_model

########NEW FILE########
__FILENAME__ = pycoin_txcons
"""
pycoin_txcons.py

Construct and sign transactions using pycoin library
"""

from pycoin.encoding import bitcoin_address_to_hash160_sec,\
    wif_to_tuple_of_secret_exponent_compressed
from pycoin.serialize import b2h, b2h_rev

from pycoin.tx import SecretExponentSolver
from pycoin.tx.Tx import Tx, SIGHASH_ALL
from pycoin.tx.TxIn import TxIn
from pycoin.tx.TxOut import TxOut

from pycoin.tx.script import tools
from pycoin.tx.script.vm import verify_script

from io import BytesIO

from coloredcoinlib import txspec
from coloredcoinlib.blockchain import script_to_raw_address


def construct_standard_tx(composed_tx_spec, is_test):
    txouts = []
    STANDARD_SCRIPT_OUT = "OP_DUP OP_HASH160 %s OP_EQUALVERIFY OP_CHECKSIG"
    for txout in composed_tx_spec.get_txouts():
        hash160 = bitcoin_address_to_hash160_sec(txout.target_addr, is_test)
        script_text = STANDARD_SCRIPT_OUT % b2h(hash160)
        script_bin = tools.compile(script_text)
        txouts.append(TxOut(txout.value, script_bin))
    txins = []
    for cts_txin in composed_tx_spec.get_txins():
        txin = TxIn(cts_txin.get_txhash(), cts_txin.prevout.n)
        if cts_txin.nSequence:
            print cts_txin.nSequence
            txin.sequence = cts_txin.nSequence
        txins.append(txin)
    version = 1
    lock_time = 0
    return Tx(version, txins, txouts, lock_time)


def sign_tx(tx, utxo_list, is_test):
    secret_exponents = [utxo.address_rec.rawPrivKey
                        for utxo in utxo_list if utxo.address_rec]
    solver = SecretExponentSolver(secret_exponents)
    txins = tx.txs_in[:]
    hash_type = SIGHASH_ALL
    for txin_idx in xrange(len(txins)):
        blank_txin = txins[txin_idx]
        utxo = None
        for utxo_candidate in utxo_list:
            if utxo_candidate.get_txhash() == blank_txin.previous_hash \
                    and utxo_candidate.outindex == blank_txin.previous_index:
                utxo = utxo_candidate
                break
        if not (utxo and utxo.address_rec):
            continue
        txout_script = utxo.script.decode('hex')
        signature_hash = tx.signature_hash(
            txout_script, txin_idx, hash_type=hash_type)
        txin_script = solver(txout_script, signature_hash, hash_type)
        txins[txin_idx] = TxIn(blank_txin.previous_hash,
                               blank_txin.previous_index,
                               txin_script,
                               blank_txin.sequence)
        if not verify_script(txin_script, txout_script,
                             signature_hash, hash_type=hash_type):
            raise Exception("invalid script")
    tx.txs_in = txins

def deserialize(tx_data):
    return Tx.parse(BytesIO(tx_data))

def reconstruct_composed_tx_spec(model, tx):
    if isinstance(tx, str):
        tx = deserialize(tx)
    if not isinstance(tx, Tx):
        raise Exception('tx is neiether string nor pycoin.tx.Tx')

    pycoin_tx = tx

    composed_tx_spec = txspec.ComposedTxSpec(None)

    for py_txin in pycoin_tx.txs_in:
        # lookup the previous hash and generate the utxo
        in_txhash, in_outindex = py_txin.previous_hash, py_txin.previous_index
        in_txhash = in_txhash[::-1].encode('hex')

        composed_tx_spec.add_txin(
            txspec.ComposedTxSpec.TxIn(in_txhash, in_outindex))
        # in_tx = ccc.blockchain_state.get_tx(in_txhash)
        # value = in_tx.outputs[in_outindex].value
        # raw_address = script_to_raw_address(py_txin.script)
        # address = ccc.raw_to_address(raw_address)

    for py_txout in pycoin_tx.txs_out:
        script = py_txout.script
        raw_address = script_to_raw_address(script)
        if raw_address:
            address = model.ccc.raw_to_address(raw_address)
        else:
            address = None
        composed_tx_spec.add_txout(
            txspec.ComposedTxSpec.TxOut(py_txout.coin_value, address))

    return composed_tx_spec

########NEW FILE########
__FILENAME__ = rpc_interface
"""
rpc_interface.py

This file connects ngccc-server.py to wallet_controller.py
The main functions that this file has are to take the
JSON-RPC commands from the server and pass them through to
the wallet controller.
Note console_interface.py does a similar thing for ngccc.py
to wallet_controller.py
"""

from wallet_controller import WalletController
from pwallet import PersistentWallet
import pyjsonrpc
import json

# create a global wallet for this use.
wallet = PersistentWallet(None, True)
wallet.init_model()
model = wallet.get_model()
controller = WalletController(model)


def get_asset_definition(moniker):
    """Get the asset/color associated with the moniker.
    """
    adm = model.get_asset_definition_manager()
    asset = adm.get_asset_by_moniker(moniker)
    if asset:
        return asset
    else:
        raise Exception("asset %s not found" % moniker)


def balance(moniker):
    """Returns the balance in Satoshi for a particular asset/color.
    "bitcoin" is the generic uncolored coin.
    """
    asset = get_asset_definition(moniker)
    return controller.get_available_balance(asset)


def addressbalance(moniker):
    """Returns the balance in Satoshi for a particular asset/color.
    "bitcoin" is the generic uncolored coin.
    """
    asset = get_asset_definition(moniker)
    return controller.get_address_balance(asset)


def newaddr(moniker):
    """Creates a new bitcoin address for a given asset/color.
    """
    asset = get_asset_definition(moniker)
    addr = controller.get_new_address(asset)
    return addr.get_address()


def alladdresses(moniker):
    """Lists all addresses for a given asset/color
    """
    asset = get_asset_definition(moniker)
    return [addr.get_address()
            for addr in controller.get_all_addresses(asset)]


def addasset(moniker, color_description):
    """Imports a color definition. This is useful if someone else has
    issued a color and you want to be able to receive it.
    """
    controller.add_asset_definition(
        {"monikers": [moniker],
         "color_set": [color_description]}
        )


def dump_config():
    """Returns a JSON dump of the current configuration
    """
    config = wallet.wallet_config
    dict_config = dict(config.iteritems())
    return json.dumps(dict_config, indent=4)


def setval(self, key, value):
    """Sets a value in the configuration.
    Key is expressed like so: key.subkey.subsubkey
    """
    if not (key and value):
        print ("setval command expects:  key value")
        return
    kpath = key.split('.')
    try:
        value = json.loads(value)
    except ValueError:
        print ("didn't understand the value: %s" % value)
        return
    try:
        # traverse the path until we get to the value we
        #  need to set
        if len(kpath) > 1:
            branch = self.wallet.wallet_config[kpath[0]]
            cdict = branch
            for k in kpath[1:-1]:
                cdict = cdict[k]
            cdict[kpath[-1]] = value
            value = branch
        self.wallet.wallet_config[kpath[0]] = value
    except TypeError:
        print ("could not set the key: %s" % key)


def getval(self, key):
    """Returns the value for a given key in the config.
    Key is expressed like so: key.subkey.subsubkey
    """
    if not key:
        print ("getval command expects:  key")
        return
    kpath = key.split('.')
    cv = self.wallet.wallet_config
    try:
        # traverse the path until we get the value
        for k in kpath:
            cv = cv[k]
        print (json.dumps(cv))
    except (KeyError, TypeError):
        print ("could not find the key: %s" % key)


def send(moniker, address, amount):
    """Send some amount of an asset/color to an address
    """
    asset = get_asset_definition(moniker)
    controller.send_coins(address, asset, amount)


def issue(moniker, pck, units, atoms_in_unit):
    """Starts a new color based on <coloring_scheme> with
    a name of <moniker> with <units> per share and <atoms>
    total shares.
    """
    controller.issue_coins(moniker, pck, units, atoms_in_unit)


def scan():
    """Update the database of transactions (amount in each address).
    """
    controller.scan_utxos()


def history(self, **kwargs):
    """print the history of transactions for this color
    """
    asset = self.get_asset_definition(moniker=kwargs['moniker'])
    return self.controller.get_history(asset)


class RPCRequestHandler(pyjsonrpc.HttpRequestHandler):
    """JSON-RPC handler for ngccc's commands.
    The command-set is identical to the console interface.
    """

    methods = {
        "balance": balance,
        "newaddr": newaddr,
        "alladdresses": alladdresses,
        "addasset": addasset,
        "dump_config": dump_config,
        "setval": setval,
        "getval": getval,
        "send": send,
        "issue": issue,
        "scan": scan,
        "history": history,
    }

########NEW FILE########
__FILENAME__ = blockchain
"""
blockchain.py

This is a connector to JSON based URL's such as blockchain.info
For now, the main usage of this file is to grab the utxo's for a
given address.
UTXO's (Unspent Transaction Outputs) are the record of transactions
for an address that haven't been spent yet.
"""
import urllib2
import json


class WebBlockchainInterface(object):
    """Abstract class for processing actual utxo's from a given web
    provider.
    """
    URL_TEMPLATE = None
    REVERSE_TXHASH = False

    def get_utxo(self, address):
        """Returns Unspent Transaction Outputs for a given address
        as an array of arrays. Each array in the array is a list of
        four elements that are necessary to initialize a UTXO object
        from utxodb.py
        """
        url = self.URL_TEMPLATE % address
        try:
            jsonData = urllib2.urlopen(url).read()
            data = json.loads(jsonData)
            utxos = []
            for utxo_data in data['unspent_outputs']:
                txhash = utxo_data['tx_hash']
                if self.REVERSE_TXHASH:
                    txhash = txhash.decode('hex')[::-1].encode('hex')
                utxo = [txhash, utxo_data['tx_output_n'],
                        utxo_data['value'], utxo_data['script']]
                utxos.append(utxo)
            return utxos
        except urllib2.HTTPError as e:
            if e.code == 500:         
                return []             
            raise                       # pragma: no cover

    def get_address_history(self, address):
        raise Exception('not implemented')


class BlockchainInfoInterface(WebBlockchainInterface):
    """Interface for blockchain.info. DO NOT USE FOR TESTNET!
    """
    URL_TEMPLATE = "https://blockchain.info/unspent?active=%s"
    REVERSE_TXHASH = True

    def __init__(self, tx_db=None):
        self.tx_db = tx_db

    def notify_confirmations(self, txhash, confirmations):
        if self.tx_db:
            self.tx_db.notify_confirmations(txhash, confirmations)

    def get_block_count(self):
        return int(urllib2.urlopen("https://blockchain.info/q/getblockcount").read())
    
    def get_tx_confirmations(self, txhash):
        try:
            url = "https://blockchain.info/rawtx/%s" % txhash
            data = json.loads(urllib2.urlopen(url).read())
            if 'block_height' in data:
                block_count = self.get_block_count()
                return block_count - data['block_height'] + 1
            else:
                return 0
        except Exception as e:
            print e
            return None

    def get_address_history(self, address):
        block_count = self.get_block_count()
        url = "https://blockchain.info/rawaddr/%s" % address
        jsonData = urllib2.urlopen(url).read()
        data = json.loads(jsonData)
        return [tx['hash'] for tx in data['txs']]        


class AbeInterface(WebBlockchainInterface):
    """Interface for an Abe server, which is an open-source
    version of block explorer.
    See https://github.com/bitcoin-abe/bitcoin-abe for more information.
    """
    URL_TEMPLATE = "http://abe.bitcontracts.org/unspent/%s"

    def get_address_history(self, address):
        url = "http://abe.bitcontracts.org/unspent/%s" % address
        jsonData = urllib2.urlopen(url).read()
        data = json.loads(jsonData)
        return [tx['hash'] for tx in data['txs']]

########NEW FILE########
__FILENAME__ = chroma
#!/usr/bin/env python

"""
chroma.py

This is a connector to chromawallet's servers to grab transaction details
"""

import bitcoin
import json
import urllib2


from coloredcoinlib import CTransaction, BlockchainStateBase


class UnimplementedError(RuntimeError):
    pass


class ChromaBlockchainState(BlockchainStateBase):

    tx_lookup = {}

    def __init__(self, url_stem="http://localhost:28832", testnet=False):
        """Initialization takes the url and port of the chroma server.
        We have to use the chroma server for everything that we would
        use 
        We use the normal bitcoind interface, except for
        get_raw_transaction, where we have to do separate lookups
        to blockchain and electrum.
        """
        self.url_stem = url_stem

    def publish_tx(self, txdata):
        url = "%s/publish_tx" % self.url_stem
        req = urllib2.Request(url, txdata,
                              {'Content-Type': 'application/json'})
        f = urllib2.urlopen(req)
        reply = f.read()
        f.close()
        if reply[0] == 'E' or (len(reply) != 64):
            raise Exception(reply)
        else:
            return reply            

    def prefetch(self, txhash, output_set, color_desc, limit):
        url = "%s/prefetch" % self.url_stem
        data = {'txhash': txhash, 'output_set': output_set,
                'color_desc': color_desc, 'limit': limit}
        req = urllib2.Request(url, json.dumps(data),
                              {'Content-Type': 'application/json'})
        f = urllib2.urlopen(req)
        txs = json.loads(f.read())
        for txhash, txraw in txs.items():
            self.tx_lookup[txhash] = txraw
        f.close()
        return

    def get_tx_blockhash(self, txhash):
        url = "%s/tx_blockhash" % self.url_stem
        data = {'txhash': txhash}
        req = urllib2.Request(url, json.dumps(data),
                              {'Content-Type': 'application/json'})
        f = urllib2.urlopen(req)
        payload = f.read()
        f.close()
        data = json.loads(payload)
        return data[0], data[1]

    def get_block_count(self):
        url = "%s/blockcount" % self.url_stem
        data = urllib2.urlopen(url).read()
        return int(data)

    def get_height(self):
        return self.get_block_count()

    def get_block_height(self, block_hash):
        url = "%s/header" % self.url_stem
        data = json.dumps({
            'block_hash': block_hash,
        })
        req = urllib2.urlopen(urllib2.Request(url,
            data, {'Content-Type': 'application/json'}))
        return json.loads(req.read())['block_height']        

    def get_header(self, height):
        url = "%s/header" % self.url_stem
        data = json.dumps({
            'height': height,
        })
        req = urllib2.urlopen(urllib2.Request(url,
            data, {'Content-Type': 'application/json'}))
        return json.loads(req.read())

    def get_chunk(self, index):
        url = "%s/chunk" % self.url_stem
        data = json.dumps({
            'index': index,
        })
        req = urllib2.urlopen(urllib2.Request(url,
            data, {'Content-Type': 'application/json'}))
        return req.read().encode('hex')

    def get_merkle(self, txhash):
        url = "%s/merkle" % self.url_stem
        data = json.dumps({
            'txhash': txhash,
            'blockhash': self.get_tx_blockhash(txhash)[0],
        })
        req = urllib2.urlopen(urllib2.Request(url,
            data, {'Content-Type': 'application/json'}))
        return json.loads(req.read())

    def get_raw(self, txhash):
        if self.tx_lookup.get(txhash):
            return self.tx_lookup[txhash]
        url = "%s/tx" % self.url_stem
        data = {'txhash': txhash}
        req = urllib2.Request(url, json.dumps(data),
                              {'Content-Type': 'application/json'})
        f = urllib2.urlopen(req)
        payload = f.read()
        self.tx_lookup[txhash] = payload
        f.close()
        return payload

    def get_tx(self, txhash):
        txhex = self.get_raw(txhash)
        txbin = bitcoin.core.x(txhex)
        tx = bitcoin.core.CTransaction.deserialize(txbin)
        return CTransaction.from_bitcoincore(txhash, tx, self)

    def get_mempool_txs(self):
        return []


########NEW FILE########
__FILENAME__ = electrum
#!/usr/bin/env python

"""
electrum.py

This is a connector to Stratum protocol Electrum servers
For now, the main usage of this file is to grab the utxo's for a
given address.
UTXO's (Unspent Transaction Outputs) are the record of transactions
for an address that haven't been spent yet.
"""

from bitcoin.core import CTransaction
from bitcoin.wallet import CBitcoinAddress
from bitcoin.core import x as to_binary
from bitcoin.core import b2lx as to_little_endian_hex
from bitcoin.core import b2x as to_hex
from coloredcoinlib import blockchain

import json
import socket
import sys
import time
import traceback
import urllib2
import bitcoin.rpc


class ConnectionError(Exception):
    pass


class ElectrumInterface(object):
    """Interface for interacting with Electrum servers using the
    stratum tcp protocol
    """

    def __init__(self, host, port, debug=False):
        """Make an interface object for connecting to electrum server
        """
        self.message_counter = 0
        self.connection = (host, port)
        self.debug = debug
        self.is_connected = False
        self.connect()

    def connect(self):
        """Connects to an electrum server via TCP.
        Uses a socket so we can listen for a response
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        try:
            sock.connect(self.connection)
        except:
            raise ConnectionError("Unable to connect to %s:%s" % self.connection)

        sock.settimeout(60)
        self.sock = sock
        self.is_connected = True
        if self.debug:
            print ("connected to %s:%s" % self.connection ) # pragma: no cover
        return True

    def wait_for_response(self, target_id):
        """Get a response message from an electrum server with
        the id of <target_id>
        """
        try:
            out = ''
            while self.is_connected or self.connect():
                try:
                    msg = self.sock.recv(1024)
                    if self.debug:
                        print (msg)  # pragma: no cover
                except socket.timeout:         # pragma: no cover
                    print ("socket timed out")   # pragma: no cover
                    self.is_connected = False  # pragma: no cover
                    continue                   # pragma: no cover
                except socket.error:                      # pragma: no cover
                    traceback.print_exc(file=sys.stdout)  # pragma: no cover
                    raise                                 # pragma: no cover

                out += msg
                if msg == '':
                    self.is_connected = False  # pragma: no cover

                # get the list of messages by splitting on newline
                raw_messages = out.split("\n")

                # the last one isn't complete
                out = raw_messages.pop()
                for raw_message in raw_messages:
                    message = json.loads(raw_message)

                    id = message.get('id')
                    error = message.get('error')
                    result = message.get('result')

                    if id == target_id:
                        if error:
                            raise Exception(                    # pragma: no cover
                                "received error %s" % message)  # pragma: no cover
                        else:
                            return result
                    else:
                        # just print it for now
                        print (message)                          # pragma: no cover
        except:                                   # pragma: no cover
            traceback.print_exc(file=sys.stdout)  # pragma: no cover

        self.is_connected = False                 # pragma: no cover

    def get_response(self, method, params):
        """Given a message that consists of <method> which
        has <params>,
        Return the string response of the message sent to electrum"""
        current_id = self.message_counter
        self.message_counter += 1
        try:
            self.sock.send(
                json.dumps({
                    'id': current_id,
                    'method': method,
                    'params': params})
                + "\n")
        except socket.error:                       # pragma: no cover
            traceback.print_exc(file=sys.stdout)   # pragma: no cover
            return None                            # pragma: no cover
        return self.wait_for_response(current_id)

    def get_version(self):
        """Get the server version of the electrum server
        that it's connected to.
        """
        return self.get_response('server.version', ["1.9", "0.6"])

    def get_height(self):
        return self.get_response('blockchain.numblocks.subscribe', [])

    def get_merkle(self, tx_hash, height):
        return self.get_response('blockchain.transaction.get_merkle', [tx_hash,
                                                                       height])

    def get_header(self, height):
        return self.get_response('blockchain.block.get_header', [height])

    def get_raw_transaction(self, tx_id, height):
        """Get the raw transaction that has the transaction hash
        of <tx_id> and height <height>.
        Note you may need to use another method to get the height
        from the transaction id hash.
        """
        return self.get_response('blockchain.transaction.get', [tx_id, height])

    def get_utxo(self, address):
        """Gets all the Unspent Transaction Outs from a given <address>
        """
        script_pubkey = CBitcoinAddress(address).to_scriptPubKey()
        txs = self.get_response('blockchain.address.get_history', [address])
        spent = {}
        utxos = []
        for tx in txs:
            raw = self.get_raw_transaction(tx['tx_hash'], tx['height'])
            data = CTransaction.deserialize(to_binary(raw))
            for vin in data.vin:
                spent[(to_little_endian_hex(vin.prevout.hash),
                       vin.prevout.n)] = 1
            for outindex, vout in enumerate(data.vout):
                if vout.scriptPubKey == script_pubkey:
                    utxos += [(tx['tx_hash'], outindex, vout.nValue,
                               to_hex(vout.scriptPubKey))]
        return [u for u in utxos if not u[0:2] in spent]

    def get_chunk(self, index):
        return self.get_response('blockchain.block.get_chunk', [index])


class EnhancedBlockchainState(blockchain.BlockchainState):
    """Subclass of coloredcoinlib's BlockchainState for
    getting the raw transaction from electrum instead of a local
    bitcoind server. This is more convenient than reindexing
    the bitcoind server which can take an hour or more.
    """

    def __init__(self, url, port):
        """Initialization takes the url and port of the electrum server.
        We use the normal bitcoind interface, except for
        get_raw_transaction, where we have to do separate lookups
        to blockchain and electrum.
        """
        self.interface = ElectrumInterface(url, port)
        self.bitcoind = bitcoin.rpc.RawProxy()
        self.cur_height = None

    def get_tx_block_height(self, txhash):
        """Get the tx_block_height given a txhash from blockchain.
        This is necessary since the electrum interface requires
        the height in order to get the raw transaction. The parent
        class, BlockchainStatus, uses get_raw_transaction to get
        the height, which would cause a circular dependency.
        """
        url = "http://blockchain.info/rawtx/%s" % txhash
        jsonData = urllib2.urlopen(url).read()
        if jsonData[0] != '{':
            return (None, False)  # pragma: no cover
        data = json.loads(jsonData)
        return (data.get("block_height", None), True)

    def get_raw_transaction(self, txhash):
        try:
            # first, grab the tx height
            height = self.get_tx_block_height(txhash)[0]
            if not height:
                raise Exception("")  # pragma: no cover
            
            # grab the transaction from electrum which
            #  unlike bitcoind requires the height
            raw = self.interface.get_raw_transaction(txhash, height)
        except:                                              # pragma: no cover
            raise Exception(                                 # pragma: no cover
                "Could not connect to blockchain and/or"     # pragma: no cover
                "electrum server to grab the data we need")  # pragma: no cover
        return raw

    def get_tx(self, txhash):
        """Get the transaction object given a transaction hash.
        """
        txhex = self.get_raw_transaction(txhash)
        tx = CTransaction.deserialize(to_binary(txhex))
        return blockchain.CTransaction.from_bitcoincore(txhash, tx, self)

    def get_height(self):
        """Get the current height at the server
        """
        return self.interface.get_height()

    def get_merkle(self, tx_hash):
        height, _ = self.get_tx_block_height(tx_hash)
        return self.interface.get_merkle(tx_hash, height)

    def get_header(self, height):
        return self.interface.get_header(height)

    def get_chunk(self, index):
        return self.interface.get_chunk(index)

########NEW FILE########
__FILENAME__ = helloblock
import urllib2
import json


class HelloBlockInterface(object):
    def __init__(self, testnet):
        self.net_prefix = "testnet" if testnet else "mainnet"

    def get_tx_confirmations(self, txhash):
        url = "https://%s.helloblock.io/v1/transactions/%s" % \
            (self.net_prefix, txhash)
        try:
            resp = json.loads(urllib2.urlopen(url).read())
            if resp['status'] == 'success':
                return resp['data']['transaction']['confirmations']
        except:
            raise
        return 0

    def get_utxo(self, address):
        url = "https://%s.helloblock.io/v1/addresses/unspents?addresses=%s" % \
            (self.net_prefix, address)
        try:
            resp = json.loads(urllib2.urlopen(url).read())
            if resp['status'] == 'success':
                unspents = resp['data']['unspents']
                utxos = []
                for utxo_data in unspents:
                    utxos.append([utxo_data['txHash'],
                                  utxo_data['index'],
                                  utxo_data['value'],
                                  utxo_data['scriptPubKey']])
                return utxos
        except:
            raise
        return []

    def get_address_history(self, address):
        url = "https://%s.helloblock.io/v1/addresses/%s/transactions?limit=10000" % \
            (self.net_prefix, address)
        resp = json.loads(urllib2.urlopen(url).read())
        if resp['status'] == 'success':
            txs = resp['data']['transactions']
            return [tx['txHash'] for tx in txs]
        raise Exception('error when retrieving history for an address')

########NEW FILE########
__FILENAME__ = test_address
#!/usr/bin/env python

import unittest

from pycoin.encoding import EncodingError, b2a_base58

from coloredcoinlib import ColorSet
from coloredcoinlib.tests.test_colorset import MockColorMap
from ngcccbase.address import LooseAddressRecord, InvalidAddressError


class TestAddress(unittest.TestCase):

    def setUp(self):
        self.colormap = MockColorMap()
        d = self.colormap.d
        self.colorset0 = ColorSet(self.colormap, [self.colormap.get_color_def(0).__repr__()])
        self.colorset1 = ColorSet(self.colormap, [d[1]])
        self.main_p = '5Kb8kLf9zgWQnogidDA76MzPL6TsZZY36hWXMssSzNydYXYB9KF'
        self.main = LooseAddressRecord(address_data=self.main_p,
                                       color_set=self.colorset0,
                                       testnet=False)
        self.test_p = '91avARGdfge8E4tZfYLoxeJ5sGBdNJQH4kvjJoQFacbgyUY4Gk1'
        self.test = LooseAddressRecord(address_data=self.test_p,
                                       color_set=self.colorset1,
                                       testnet=True)


    def test_init(self):
        self.assertEqual(self.main.get_address(),
                         '1CC3X2gu58d6wXUWMffpuzN9JAfTUWu4Kj')
        self.assertEqual(self.test.get_address(),
                         'mo3oihY41iwPco1GKwehHPHmxMT4Ld5W3q')
        self.assertRaises(EncodingError, LooseAddressRecord,
                          address_data=self.main_p[:-2] + '88')
        self.assertRaises(EncodingError, LooseAddressRecord,
                          address_data=self.test_p[:-2] + '88',
                          testnet=True)
        self.assertRaises(InvalidAddressError, LooseAddressRecord,
                          address_data=self.main_p, testnet=True)
        self.assertRaises(InvalidAddressError, LooseAddressRecord,
                          address_data=self.test_p, testnet=False)

    def test_get_color_set(self):
        self.assertEqual(self.main.get_color_set().__repr__(),
                         self.colorset0.__repr__())

    def test_get_color_address(self):
        self.assertEqual(self.main.get_color_address(),
                         '1CC3X2gu58d6wXUWMffpuzN9JAfTUWu4Kj')
        self.assertEqual(self.test.get_color_address(),
                         'CP4YWLr8aAe4Hn@mo3oihY41iwPco1GKwehHPHmxMT4Ld5W3q')

    def test_get_data(self):
        self.assertEqual(self.main.get_data()['color_set'],
                         self.colorset0.get_data())
        self.assertEqual(self.main.get_data()['address_data'],
                         self.main_p)
        self.assertEqual(self.test.get_data()['color_set'],
                         self.colorset1.get_data())
        self.assertEqual(self.test.get_data()['address_data'],
                         self.test_p)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_asset
#!/usr/bin/env python

import unittest

from coloredcoinlib import OBColorDefinition, ColorSet, SimpleColorValue, IncompatibleTypesError
from coloredcoinlib.tests.test_colorset import MockColorMap
from coloredcoinlib.tests.test_txspec import MockUTXO

from ngcccbase.asset import (AssetDefinition, AdditiveAssetValue,
                             AssetTarget, AssetDefinitionManager)


class TestAssetDefinition(unittest.TestCase):

    def setUp(self):
        self.colormap = MockColorMap()
        d = self.colormap.d
        self.colorset0 = ColorSet(self.colormap, [''])
        self.colorset1 = ColorSet(self.colormap, [d[1], d[2]])
        self.colorset2 = ColorSet(self.colormap, [d[3]])
        self.def0 = {'monikers': ['bitcoin'],
                     'color_set': self.colorset0.get_data(),
                     'unit':100000000}
        self.def1 = {'monikers': ['test1'],
                     'color_set': self.colorset1.get_data(),
                     'unit':10}
        self.def2 = {'monikers': ['test2','test2alt'],
                     'color_set': self.colorset2.get_data(),
                     'unit':1}
        self.asset0 = AssetDefinition(self.colormap, self.def0)
        self.asset1 = AssetDefinition(self.colormap, self.def1)
        self.asset2 = AssetDefinition(self.colormap, self.def2)

        self.assetvalue0 = AdditiveAssetValue(asset=self.asset0, value=5)
        self.assetvalue1 = AdditiveAssetValue(asset=self.asset0, value=6)
        self.assetvalue2 = AdditiveAssetValue(asset=self.asset1, value=7)

        self.assettarget0 = AssetTarget('address0', self.assetvalue0)
        self.assettarget1 = AssetTarget('address1', self.assetvalue1)
        self.assettarget2 = AssetTarget('address2', self.assetvalue2)

        config = {'asset_definitions': [self.def1, self.def2]}
        self.adm = AssetDefinitionManager(self.colormap, config)

    def test_repr(self):
        self.assertEquals(self.asset0.__repr__(), "['bitcoin']: ['']")
        self.assertEquals(
            self.asset1.__repr__(),
            "['test1']: ['obc:color_desc_1:0:0', 'obc:color_desc_2:0:1']")
        self.assertEquals(self.asset2.__repr__(),
                          "['test2', 'test2alt']: ['obc:color_desc_3:0:1']")

    def test_get_monikers(self):
        self.assertEquals(self.asset0.get_monikers(), ['bitcoin'])
        self.assertEquals(self.asset1.get_monikers(), ['test1'])
        self.assertEquals(self.asset2.get_monikers(), ['test2', 'test2alt'])

    def test_get_color_set(self):
        self.assertTrue(self.asset0.get_color_set().equals(self.colorset0))
        self.assertTrue(self.asset1.get_color_set().equals(self.colorset1))
        self.assertTrue(self.asset2.get_color_set().equals(self.colorset2))

    def test_get_colorvalue(self):
        g = {'txhash':'blah', 'height':1, 'outindex':0}
        cid0 = list(self.colorset0.color_id_set)[0]
        cdef0 = OBColorDefinition(cid0, g)
        cid1 = list(self.colorset1.color_id_set)[0]
        cdef1 = OBColorDefinition(cid1, g)
        cid2 = list(self.colorset2.color_id_set)[0]
        cdef2 = OBColorDefinition(cid2, g)
        cv0 = SimpleColorValue(colordef=cdef0, value=1)
        cv1 = SimpleColorValue(colordef=cdef1, value=2)
        cv2 = SimpleColorValue(colordef=cdef2, value=3)

        utxo = MockUTXO([cv0, cv1, cv2])

        self.assertEquals(self.asset0.get_colorvalue(utxo), cv0)
        self.assertEquals(self.asset1.get_colorvalue(utxo), cv1)
        self.assertEquals(self.asset2.get_colorvalue(utxo), cv2)

        utxo = MockUTXO([cv0, cv2])
        self.assertRaises(Exception, self.asset1.get_colorvalue, utxo)

    def test_parse_value(self):
        self.assertEquals(self.asset0.parse_value(1.25), 125000000)
        self.assertEquals(self.asset1.parse_value(2), 20)
        self.assertEquals(self.asset2.parse_value(5), 5)

    def test_format_value(self):
        self.assertEquals(self.asset0.format_value(10000),'0.0001')
        self.assertEquals(self.asset1.format_value(2),'0.2')
        self.assertEquals(self.asset2.format_value(5),'5')

    def test_get_data(self):
        self.assertEquals(self.asset0.get_data(), self.def0)
        self.assertEquals(self.asset1.get_data(), self.def1)
        self.assertEquals(self.asset2.get_data(), self.def2)

    def test_register_asset_definition(self):
        self.assertRaises(Exception, self.adm.register_asset_definition,
                          self.asset1)

    def test_add_asset_definition(self):
        colorset3 = ColorSet(self.colormap, [self.colormap.d[4]])
        def4 = {'monikers': ['test3'], 'color_set': colorset3.get_data()}
        self.adm.add_asset_definition(def4)
        self.assertTrue(self.adm.get_asset_by_moniker('test3').get_color_set()
                        .equals(colorset3))

    def test_all_assets(self):
        reprs = [asset.__repr__() for asset in self.adm.get_all_assets()]
        self.assertTrue(self.asset0.__repr__() in reprs)
        self.assertTrue(self.asset1.__repr__() in reprs)
        self.assertTrue(self.asset2.__repr__() in reprs)

    def test_get_asset_and_address(self):
        ch = self.asset1.get_color_set().get_color_hash()
        addr = '1CC3X2gu58d6wXUWMffpuzN9JAfTUWu4Kj'
        coloraddress = "%s@%s" % (ch, addr)
        asset, address = self.adm.get_asset_and_address(coloraddress)
        self.assertEquals(asset.__repr__(), self.asset1.__repr__())
        self.assertEquals(addr, address)
        asset, address = self.adm.get_asset_and_address(addr)
        self.assertEquals(asset.__repr__(), self.asset0.__repr__())
        self.assertEquals(addr, address)
        self.assertRaises(Exception, self.adm.get_asset_and_address, '0@0')

    def test_add(self):
        assetvalue3 = self.assetvalue0 + self.assetvalue1
        self.assertEqual(assetvalue3.get_value(), 11)
        assetvalue3 = 0 + self.assetvalue1
        self.assertEqual(assetvalue3.get_value(), 6)
        self.assertRaises(IncompatibleTypesError, self.assetvalue0.__add__,
                          self.assetvalue2)

    def test_iadd(self):
        assetvalue = self.assetvalue0.clone()
        assetvalue += self.assetvalue1
        self.assertEqual(assetvalue.get_value(), 11)

    def test_sub(self):
        assetvalue = self.assetvalue1 - self.assetvalue0
        self.assertEqual(assetvalue.get_value(), 1)
        assetvalue = self.assetvalue1 - 0
        self.assertEqual(assetvalue.get_value(), self.assetvalue1.get_value())

    def test_lt(self):
        self.assertTrue(self.assetvalue0 < self.assetvalue1)
        self.assertTrue(self.assetvalue1 > self.assetvalue0)
        self.assertTrue(self.assetvalue1 >= self.assetvalue0)
        self.assertTrue(self.assetvalue1 > 0)

    def test_sum(self):
        assetvalues = [self.assetvalue0, self.assetvalue1,
                       AdditiveAssetValue(asset=self.asset0, value=3)]
        self.assertEqual(AdditiveAssetValue.sum(assetvalues).get_value(), 14)

    def test_get_asset(self):
        self.assertEqual(self.assettarget0.get_asset(), self.asset0)

    def test_get_value(self):
        self.assertEqual(self.assettarget0.get_value(), self.assetvalue0.get_value())

    def test_sum(self):
        assettargets = [self.assettarget0, self.assettarget1,
                        AssetTarget('address3',self.assettarget1)]
        self.assertEqual(AssetTarget.sum(assettargets).get_value(), 17)
        self.assertEqual(AssetTarget.sum([]), 0)

    def test_get_address(self):
        self.assertEqual(self.assettarget0.get_address(), 'address0')

    def test_repr(self):
        self.assertEqual(self.assettarget0.__repr__(), 'address0: Asset Value: 5')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_bip0032
#!/usr/bin/env python

import copy
import unittest

from pycoin.encoding import EncodingError

from coloredcoinlib import ColorSet
from coloredcoinlib.tests.test_colorset import MockColorMap
from ngcccbase.address import InvalidAddressError
from ngcccbase.asset import AssetDefinition
from ngcccbase.bip0032 import HDWalletAddressManager
from test_deterministic import TestDeterministic


class TestBIP0032(TestDeterministic):

    def setUp(self):
        super(TestBIP0032, self).setUp()
        c = {
            'hdw_master_key': self.master_key,
            'hdwam': {
                'genesis_color_sets':[self.colorset1.get_data(),
                                      self.colorset2.get_data()],
                'color_set_states':[
                    {'color_set':self.colorset0.get_data(), "max_index":0},
                    {'color_set':self.colorset1.get_data(), "max_index":3},
                    {'color_set':self.colorset2.get_data(), "max_index":2},
                    ],
                },
            'addresses':[{'address_data': self.privkey,
                          'color_set': self.colorset1.get_data(),
                          }],
            'testnet': False,
            }
        self.config = copy.deepcopy(c)
        self.maindwam = HDWalletAddressManager(self.colormap, c)

    def test_init_new_wallet(self):
        c = copy.deepcopy(self.config)
        del c['hdw_master_key']
        del c['hdwam']
        newdwam = HDWalletAddressManager(self.colormap, c)
        params = newdwam.init_new_wallet()
        self.assertNotEqual(self.config['hdw_master_key'],
                            newdwam.config['hdw_master_key'])

        c = copy.deepcopy(self.config)
        c['addresses'][0]['address_data'] = 'notreal'
        self.assertRaises(EncodingError, HDWalletAddressManager,
                          self.colormap, c)



if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_blockchain
import unittest
import os, tempfile, shutil
import time

from ngcccbase.pwallet import PersistentWallet
from ngcccbase.services.chroma import ChromaBlockchainState
from ngcccbase.blockchain import VerifierBlockchainState


class TestVerifierBlockchainState(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import signal
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        #cls.tempdir = tempfile.mkdtemp()
        cls.tempdir = '/path/to/folder'
        cls.pwallet = PersistentWallet(os.path.join(cls.tempdir, 'testnet.wallet'), True)
        cls.pwallet.init_model()
        cls.vbs = VerifierBlockchainState(cls.tempdir, ChromaBlockchainState())

    @classmethod
    def tearDownClass(cls):
        #shutil.rmtree(cls.tempdir)
        pass

    def test_(self):
        pass
        self.vbs.start()
        while self.vbs.is_running():
            time.sleep(0.1)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_color
#!/usr/bin/env python

import os
import unittest

from pycoin.encoding import (a2b_hashed_base58, from_bytes_32,
                             public_pair_to_hash160_sec)
from pycoin.ecdsa.secp256k1 import generator_secp256k1 as BasePoint

from ngcccbase.color import ColoredCoinContext


class TestColor(unittest.TestCase):

    def setUp(self):
        self.path = ":memory:"
        c = {
            'ccc': {'colordb_path': self.path},
            'testnet': False,
            }
        self.address = '5Kb8kLf9zgWQnogidDA76MzPL6TsZZY36hWXMssSzNydYXYB9KF'
        self.ccc = ColoredCoinContext(c)

    def test_init(self):
        self.assertTrue(self.ccc.colordata)

    def test_raw_to_address(self):
        privkey = from_bytes_32(a2b_hashed_base58(self.address)[1:])
        pubkey = BasePoint * privkey
        raw = public_pair_to_hash160_sec(pubkey.pair(), False)
        addr = self.ccc.raw_to_address(raw)
        self.assertEqual(addr,'1CC3X2gu58d6wXUWMffpuzN9JAfTUWu4Kj')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_deterministic
#!/usr/bin/env python

import copy
import unittest

from pycoin.encoding import EncodingError

from coloredcoinlib import ColorSet
from coloredcoinlib.tests.test_colorset import MockColorMap
from ngcccbase.address import InvalidAddressError
from ngcccbase.asset import AssetDefinition
from ngcccbase.deterministic import DWalletAddressManager


class TestDeterministic(unittest.TestCase):

    def setUp(self):
        self.colormap = MockColorMap()
        d = self.colormap.d
        self.colorset0 = ColorSet(self.colormap, [''])
        self.colorset1 = ColorSet(self.colormap, [d[1]])
        self.colorset1alt = ColorSet(self.colormap, [d[1],d[6]])
        self.colorset2 = ColorSet(self.colormap, [d[2]])
        self.colorset3 = ColorSet(self.colormap, [d[3], d[4]])
        self.def1 = {'monikers': ['test1'],
                     'color_set': self.colorset1.get_data(),
                     'unit':10}
        self.asset1 = AssetDefinition(self.colormap, self.def1)
        self.master_key = '265a1a0ad05e82fa321e3f6f6767679df0c68515797e0e4e24be1afc3272ee658ec53cecb683ab76a8377273347161e123fddf5320cbbce8849b0a00557bd12c'
        self.privkey = '5Kb8kLf9zgWQnogidDA76MzPL6TsZZY36hWXMssSzNydYXYB9KF'
        self.pubkey = '1CC3X2gu58d6wXUWMffpuzN9JAfTUWu4Kj'
        c = {
            'dw_master_key': self.master_key,
            'dwam': {
                'genesis_color_sets':[self.colorset1.get_data(),
                                      self.colorset2.get_data()],
                'color_set_states':[
                    {'color_set':self.colorset0.get_data(), "max_index":0},
                    {'color_set':self.colorset1.get_data(), "max_index":3},
                    {'color_set':self.colorset2.get_data(), "max_index":2},
                    ],
                },
            'addresses':[{'address_data': self.privkey,
                          'color_set': self.colorset1.get_data(),
                          }],
            'testnet': False,
            }
        self.config = copy.deepcopy(c)
        self.maindwam = DWalletAddressManager(self.colormap, c)

    def test_init_new_wallet(self):
        c = copy.deepcopy(self.config)
        del c['dw_master_key']
        del c['dwam']
        newdwam = DWalletAddressManager(self.colormap, c)
        params = newdwam.init_new_wallet()
        self.assertNotEqual(self.config['dw_master_key'],
                            newdwam.config['dw_master_key'])

        c = copy.deepcopy(self.config)
        c['addresses'][0]['address_data'] = 'notreal'
        self.assertRaises(EncodingError, DWalletAddressManager,
                          self.colormap, c)

    def test_get_new_address(self):
        self.assertEqual(self.maindwam.get_new_address(self.colorset2).index,
                         3)
        self.assertEqual(self.maindwam.get_new_address(self.asset1).index,
                         4)

    def test_get_new_genesis_address(self):
        addr = self.maindwam.get_new_genesis_address()
        self.assertEqual(addr.index, 2)
        addr2 = self.maindwam.get_new_address(addr.get_color_set())
        self.assertEqual(addr2.index, 0)

    def test_get_update_genesis_address(self):
        addr = self.maindwam.get_genesis_address(0)
        self.maindwam.update_genesis_address(addr, self.colorset1alt)
        self.assertEqual(addr.get_color_set(), self.colorset1alt)

    def test_get_change_address(self):
        addr = self.maindwam.get_change_address(self.colorset0)
        self.assertEqual(addr.get_color_set().__repr__(),
                         self.colorset0.__repr__())
        self.assertEqual(self.maindwam.get_change_address(self.colorset3).index,
                         0)

    def test_get_all_addresses(self):
        addrs = [a.get_address() for a in self.maindwam.get_all_addresses()]
        self.assertTrue(self.pubkey in addrs)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_services
#!/usr/bin/env python

import unittest

from ngcccbase.services.blockchain import BlockchainInfoInterface, AbeInterface
from ngcccbase.services.electrum import (ConnectionError,
                                         ElectrumInterface, EnhancedBlockchainState)


class TestElectrum(unittest.TestCase):

    def setUp(self):
        self.server_url = "electrum.pdmc.net"
        self.ei = ElectrumInterface(self.server_url, 50001)
        self.bcs = EnhancedBlockchainState(self.server_url, 50001)
        self.txhash = 'b1c68049c1349399fb867266fa146a854c16cd8a18a01d3cd7921ab9d5af1a8b'
        self.height = 277287
        self.raw_tx = '01000000010000000000000000000000000000000000000000000000000000000000000000ffffffff4803273b04062f503253482f049fe1bd5208ee5f364f06648bae2e522cfabe6d6de0a3e574e400f64403ea10de4ff3bc0dcb42d49549e273a9faa4eac33b04734804000000000000000000000001cde08d95000000001976a91480ad90d403581fa3bf46086a91b2d9d4125db6c188ac00000000'
        self.address = '1CC3X2gu58d6wXUWMffpuzN9JAfTUWu4Kj'

    def test_connect(self):
        self.assertRaises(ConnectionError, ElectrumInterface, 'cnn.com', 50001)

    def test_get_utxo(self):
        self.assertEqual(self.ei.get_utxo(self.address), [])

    def test_get_version(self):
        self.assertTrue(float(self.ei.get_version()) >= 0.8)

    def test_get_height(self):
        self.assertTrue(self.ei.get_height() > 296217)

    def test_get_header(self):
        result = self.bcs.get_header(self.height)
        self.assertEqual(
            result['merkle_root'],
            'abe428044058494733596dc9477bb4f55a90e5144c122cacb71fa99d85c10d2c')

    def test_get_merkle(self):
        result = self.bcs.get_merkle(self.txhash)
        self.assertEqual(
            result['merkle'][0],
            '6a6daeb0dd244abe80ee740ec8752d18fcdd60247304fd7e2ede371eade2f756')
        self.assertEqual(
            result['merkle'][-1],
            '0a00d7c8fadc81c033c3c8604c4a151186bf733f10948d785a748def401ce3f7')
        self.assertEqual(result['pos'], 0)
        self.assertEqual(result['block_height'], self.height)

    def test_get_raw_transaction(self):
        self.assertEqual(self.ei.get_raw_transaction(self.txhash, self.height),
                         self.raw_tx)

        self.assertEqual(self.bcs.get_raw_transaction(self.txhash), self.raw_tx)

    def test_get_block_height(self):
        self.assertEqual(self.bcs.get_tx_block_height(self.txhash)[0], self.height)

    def test_get_tx(self):
        self.assertEqual(self.bcs.get_tx(self.txhash).hash, self.txhash)


class TestBlockchain(unittest.TestCase):
    def setUp(self):
        self.address = '13ph5zPCBLeZcPph9FBZKeeyDjvU2tvcMY'
        self.txhash = 'd7b9a9da6becbf47494c27e913241e5a2b85c5cceba4b2f0d8305e0a87b92d98'
        self.address2 = '1CC3X2gu58d6wXUWMffpuzN9JAfTUWu4Kj'

    def test_blockchain(self):
        self.assertEqual(BlockchainInfoInterface.get_utxo(self.address)[0][0],
                         self.txhash)
        self.assertEqual(BlockchainInfoInterface.get_utxo(self.address2), [])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_txcons
#!/usr/bin/env python

import os
import unittest

from pycoin.tx.script import opcodes, tools

from coloredcoinlib import (OBColorDefinition, ColorSet,
                            SimpleColorValue, ColorTarget, InvalidColorIdError,
                            UNCOLORED_MARKER, ZeroSelectError)

from ngcccbase.asset import AssetDefinition, AdditiveAssetValue, AssetTarget
from ngcccbase.txcons import (InvalidTargetError, InvalidTransformationError, 
                              InsufficientFundsError, BasicTxSpec,
                              SimpleOperationalTxSpec, RawTxSpec,
                              TransactionSpecTransformer)
from ngcccbase.pwallet import PersistentWallet



class TestTxcons(unittest.TestCase):

    def setUp(self):
        self.path = ":memory:"
        self.pwallet = PersistentWallet(self.path)
        self.config = {'dw_master_key': 'test', 'testnet': True, 'ccc': {
                'colordb_path' : self.path}, 'bip0032': False }
        self.pwallet.wallet_config = self.config
        self.pwallet.init_model()
        self.model = self.pwallet.get_model()
        self.colormap = self.model.get_color_map()

        self.colordesc0 = "obc:color0:0:0"
        self.colordesc1 = "obc:color1:0:0"
        self.colordesc2 = "obc:color2:0:0"

        # add some colordescs
        self.colorid0 = self.colormap.resolve_color_desc(self.colordesc0)
        self.colorid1 = self.colormap.resolve_color_desc(self.colordesc1)
        self.colorid2 = self.colormap.resolve_color_desc(self.colordesc2)

        self.colordef0 = OBColorDefinition(
            self.colorid0, {'txhash': 'color0', 'outindex': 0})
        self.colordef1 = OBColorDefinition(
            self.colorid1, {'txhash': 'color1', 'outindex': 0})
        self.colordef2 = OBColorDefinition(
            self.colorid2, {'txhash': 'color2', 'outindex': 0})

        self.asset_config = {
            'monikers': ['blue'],
            'color_set': [self.colordesc0],
            }
        self.basset_config = {
            'monikers': ['bitcoin'],
            'color_set': [''],
            }
        self.asset = AssetDefinition(self.colormap, self.asset_config)
        self.basset = AssetDefinition(self.colormap, self.basset_config)
        self.basic = BasicTxSpec(self.model)
        self.bbasic = BasicTxSpec(self.model)

        wam = self.model.get_address_manager()
        self.address0 = wam.get_new_address(self.asset.get_color_set())
        self.addr0 = self.address0.get_address()

        self.bcolorset = ColorSet(self.colormap, [''])
        self.baddress = wam.get_new_address(self.bcolorset)
        self.baddr = self.baddress.get_address()

        self.assetvalue0 = AdditiveAssetValue(asset=self.asset, value=5)
        self.assetvalue1 = AdditiveAssetValue(asset=self.asset, value=6)
        self.assetvalue2 = AdditiveAssetValue(asset=self.asset, value=7)
        self.bassetvalue = AdditiveAssetValue(asset=self.basset, value=8)
        self.assettarget0 = AssetTarget(self.addr0, self.assetvalue0)
        self.assettarget1 = AssetTarget(self.addr0, self.assetvalue1)
        self.assettarget2 = AssetTarget(self.addr0, self.assetvalue2)
        self.bassettarget = AssetTarget(self.baddr, self.bassetvalue)

        self.atargets = [self.assettarget0, self.assettarget1, self.assettarget2]

        # add some targets
        self.colorvalue0 = SimpleColorValue(colordef=self.colordef0, value=5)
        self.colortarget0 = ColorTarget(self.addr0, self.colorvalue0)
        self.colorvalue1 = SimpleColorValue(colordef=self.colordef0, value=6)
        self.colortarget1 = ColorTarget(self.addr0, self.colorvalue1)
        self.colorvalue2 = SimpleColorValue(colordef=self.colordef0, value=7)
        self.colortarget2 = ColorTarget(self.addr0, self.colorvalue2)
        self.bcolorvalue = SimpleColorValue(colordef=UNCOLORED_MARKER, value=8)
        self.bcolortarget = ColorTarget(self.baddr, self.bcolorvalue)

        self.targets = [self.colortarget0, self.colortarget1,
                        self.colortarget2]
        self.transformer = TransactionSpecTransformer(self.model, self.config)
        self.blockhash = '00000000c927c5d0ee1ca362f912f83c462f644e695337ce3731b9f7c5d1ca8c'
        self.txhash = '4fe45a5ba31bab1e244114c4555d9070044c73c98636231c77657022d76b87f7'

    def test_basic(self):
        self.assertRaises(InvalidTargetError, self.basic.is_monocolor)
        self.assertRaises(InvalidTargetError,
                          self.basic.add_target, self.colortarget0)
        self.basic.add_target(self.assettarget0)
        self.basic.add_target(self.assettarget1)
        self.basic.add_target(self.assettarget2)
        self.assertEqual(self.basic.is_monocolor(), True)
        self.assertEqual(self.basic.is_monoasset(), True)
        self.assertEqual(self.basic.targets, self.atargets)
        self.basic.add_target(self.bassettarget)
        self.assertEqual(self.basic.is_monoasset(), False)
        self.assertEqual(self.basic.is_monocolor(), False)
        self.assertRaises(InvalidTransformationError,
                          self.basic.make_operational_tx_spec, self.asset)

    def add_coins(self):
        script = tools.compile(
            "OP_DUP OP_HASH160 {0} OP_EQUALVERIFY OP_CHECKSIG".format(
                self.address0.rawPubkey().encode("hex"))).encode("hex")

        self.model.utxo_man.store.add_utxo(self.addr0, self.txhash,
                                           0, 100, script)

        script = tools.compile(
            "OP_DUP OP_HASH160 {0} OP_EQUALVERIFY OP_CHECKSIG".format(
                self.baddress.rawPubkey().encode("hex"))).encode("hex")

        self.model.utxo_man.store.add_utxo(self.baddr, self.txhash,
                                           1, 20000, script)
        self.model.ccc.metastore.set_as_scanned(self.colorid0, self.blockhash)
        self.model.ccc.cdstore.add(self.colorid0, self.txhash, 0, 100, '')


    def test_operational(self):
        self.basic.add_target(self.assettarget0)
        self.basic.add_target(self.assettarget1)
        self.basic.add_target(self.assettarget2)
        op = self.transformer.transform_basic(self.basic, 'operational')
        self.assertTrue(self.transformer.classify_tx_spec(op), 'operational')
        self.assertRaises(InvalidTargetError, op.add_target, 1)
        self.assertEqual(ColorTarget.sum(op.get_targets()),
                         ColorTarget.sum(self.targets))
        self.assertEqual(op.get_change_addr(self.colordef0), self.addr0)
        self.assertEqual(op.get_change_addr(UNCOLORED_MARKER), self.baddr)
        self.assertEqual(op.get_required_fee(1).get_value(), 10000)
        self.assertRaises(InvalidColorIdError, op.get_change_addr,
                          self.colordef1)
        cv = SimpleColorValue(colordef=self.colordef0, value=0)
        self.assertRaises(ZeroSelectError, op.select_coins, cv)
        cv = SimpleColorValue(colordef=self.colordef0, value=5)
        self.assertRaises(InsufficientFundsError, op.select_coins, cv)
        self.add_coins()
        self.assertEqual(op.select_coins(cv)[1].get_value(), 100)


    def test_composed(self):
        self.basic.add_target(self.assettarget0)
        self.basic.add_target(self.assettarget1)
        self.basic.add_target(self.assettarget2)
        self.add_coins()
        op = self.transformer.transform(self.basic, 'operational')
        self.assertEqual(op.get_change_addr(self.colordef0), self.addr0)
        self.assertEqual(op.get_change_addr(UNCOLORED_MARKER), self.baddr)
        comp = self.transformer.transform(op, 'composed')
        self.assertTrue(self.transformer.classify_tx_spec(comp), 'composed')
        signed = self.transformer.transform(comp, 'signed')
        self.assertTrue(self.transformer.classify_tx_spec(signed), 'signed')
        self.assertEqual(len(signed.get_hex_txhash()), 64)
        txdata = signed.get_tx_data()
        same = RawTxSpec.from_tx_data(self.model, txdata)
        self.assertEqual(same.get_hex_tx_data(), signed.get_hex_tx_data())
        self.assertRaises(InvalidTransformationError,
                          self.transformer.transform,
                          signed, '')

    def test_other(self):
        self.assertEqual(self.transformer.classify_tx_spec(1), None)
        self.assertRaises(InvalidTransformationError,
                          self.transformer.transform_basic,
                          self.basic, '')
        self.assertRaises(InvalidTransformationError,
                          self.transformer.transform_operational,
                          self.basic, '')
        self.assertRaises(InvalidTransformationError,
                          self.transformer.transform_composed,
                          self.basic, '')
        self.assertRaises(InvalidTransformationError,
                          self.transformer.transform_signed,
                          self.basic, '')
        self.assertRaises(InvalidTransformationError,
                          self.transformer.transform,
                          '', '')
        self.add_coins()
        self.bbasic.add_target(self.bassettarget)
        signed = self.transformer.transform(self.bbasic, 'signed')
        self.assertEqual(len(signed.get_hex_txhash()), 64)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_txdb
#!/usr/bin/env python

import unittest

import sqlite3

from ngcccbase import txdb, txcons, utxodb
from ngcccbase.address import LooseAddressRecord
from ngcccbase.services.electrum import (ElectrumInterface,
                                         EnhancedBlockchainState)
from ngcccbase.txdb import (TX_STATUS_UNKNOWN, TX_STATUS_UNCONFIRMED,
                            TX_STATUS_CONFIRMED, TX_STATUS_INVALID)
from coloredcoinlib import txspec

from pycoin.tx.script import tools


class TestTxDataStoreInitialization(unittest.TestCase):
    def test_initialization(self):
        connection = sqlite3.connect(":memory:")
        store = txdb.TxDataStore(connection)
        self.assertTrue(store.table_exists("tx_data"))


class MockConn(object):
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")

class MockModel(object):
    def __init__(self):
        self.store_conn = MockConn()

    def is_testnet(self):
        return False
    def get_blockchain_state(self):
        server_url = "electrum.pdmc.net"
        ei = ElectrumInterface(server_url, 50001)
        return EnhancedBlockchainState(server_url, 50001)


def fake_transaction(model=MockModel()):
    key = "5Kb8kLf9zgWQnogidDA76MzPL6TsZZY36hWXMssSzNydYXYB9KF"

    address = LooseAddressRecord(address_data=key)
    script = tools.compile(
        "OP_DUP OP_HASH160 {0} OP_EQUALVERIFY OP_CHECKSIG".format(
            address.rawPubkey().encode("hex"))).encode("hex")

    txin = utxodb.UTXO("D34DB33F", 0, 1, script)
    txin.address_rec = address
    txout = txspec.ComposedTxSpec.TxOut(1, address.get_address())
    composed = txspec.ComposedTxSpec([txin], [txout])
    return txcons.RawTxSpec.from_composed_tx_spec(model, composed), address


class TestTxDataStore(unittest.TestCase):
    def setUp(self):
        connection = sqlite3.connect(":memory:")
        self.store = txdb.TxDataStore(connection)
        self.model = MockModel()

    def test_add_tx(self):
        txhash = "FAKEHASH"
        transaction, address = fake_transaction(self.model)
        txdata = transaction.get_hex_tx_data()
        self.store.add_tx(txhash, txdata)

        stored_id, stored_hash, stored_data, stored_status = \
            self.store.get_tx_by_hash(txhash)

        self.assertEqual(stored_hash, txhash)
        self.assertEqual(stored_data, transaction.get_hex_tx_data())

        self.assertEqual(stored_status, TX_STATUS_UNKNOWN)
        self.store.set_tx_status(txhash, TX_STATUS_CONFIRMED)
        self.assertEqual(self.store.get_tx_status(txhash), TX_STATUS_CONFIRMED)
        self.store.purge_tx_data()
        self.assertEqual(self.store.get_tx_by_hash(txhash), None)


class TestVerifiedTxDb(unittest.TestCase):
    def setUp(self):
        self.model = MockModel()
        self.txdb = txdb.VerifiedTxDb(MockModel(), {})

    def test_identify_tx_status(self):
        status = self.txdb.identify_tx_status(
            'b1c68049c1349399fb867266fa146a854c16cd8a18a01d3cd7921ab9d5af1a8b')
        self.assertEqual(status, TX_STATUS_CONFIRMED)
        status = self.txdb.identify_tx_status(
            'b1c68049c1349399fb867266fa146a854c16cd8a18a01d3cd7921ab9d5af1a8b')
        self.assertEqual(status, TX_STATUS_CONFIRMED)
        status = self.txdb.identify_tx_status(
            'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
        self.assertEqual(status, TX_STATUS_INVALID)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_verifier
#!/usr/bin/env python

import unittest

from ngcccbase.verifier import Verifier, hash_decode
from ngcccbase.services.electrum import (
    ElectrumInterface, EnhancedBlockchainState)

class FakeBlockchainState(object):
    def get_height(self):
        return 100

    def get_merkle(self, tx_hash):
        l = ["3a459eab5f0cf8394a21e04d2ed3b2beeaa59795912e20b9c680e9db74dfb18c",
             "f6ae335dc2d2aecb6a255ebd03caaf6820e6c0534531051066810080e0d822c8",
             "15eca0aa3e2cc2b9b4fbe0629f1dda87f329500fcdcd6ef546d163211266b3b3"]
        return {'merkle': l, 'block_height': 99, 'pos': 1}

    def get_header(self, tx_hash):
        r = "9cdf7722eb64015731ba9794e32bdefd9cf69b42456d31f5e59aedb68c57ed52"
        return {'merkle_root': r, 'timestamp': 123}

class TestVerifier(unittest.TestCase):

    def setUp(self):
        fake_blockchain_state = FakeBlockchainState()
        self.verifier = Verifier(fake_blockchain_state)

    def test_get_confirmations(self):
        self.verifier.verified_tx['test'] = (95, 111, 1)
        self.assertEqual(self.verifier.get_confirmations('test'), 6)
        self.verifier.verified_tx['test'] = (101, 111, 1)
        self.assertEqual(self.verifier.get_confirmations('test'), 0)
        self.assertEqual(self.verifier.get_confirmations(''), None)
        del self.verifier.verified_tx['test']

    def test_get_merkle_root(self):
        # r = root, s = start, l = merkle hash list
        r = "56dee62283a06e85e182e2d0b421aceb0eadec3d5f86cdadf9688fc095b72510"
        self.assertEqual(self.verifier.get_merkle_root([], r, 0), r)

        # example from pycoin/merkle.py
        r = "30325a06daadcefb0a3d1fe0b6112bb6dfef794316751afc63f567aef94bd5c8"
        s = "67ffe41e53534805fb6883b4708fd3744358f99e99bc52111e7a17248effebee"
        l = ["c8b336acfc22d66edf6634ce095b888fe6d16810d9c85aff4d6641982c2499d1"]
        self.assertEqual(self.verifier.get_merkle_root(l, s, 0), r)

        # example from here: https://bitcointalk.org/index.php?topic=44707.0
        r = "9cdf7722eb64015731ba9794e32bdefd9cf69b42456d31f5e59aedb68c57ed52"
        s = "be38f46f0eccba72416aed715851fd07b881ffb7928b7622847314588e06a6b7"
        l = ["3a459eab5f0cf8394a21e04d2ed3b2beeaa59795912e20b9c680e9db74dfb18c",
             "f6ae335dc2d2aecb6a255ebd03caaf6820e6c0534531051066810080e0d822c8",
             "15eca0aa3e2cc2b9b4fbe0629f1dda87f329500fcdcd6ef546d163211266b3b3"]
        self.assertEqual(self.verifier.get_merkle_root(l, s, 1), r)
        s = "59d1e83e5268bbb491234ff23cbbf2a7c0aa87df553484afee9e82385fc7052f"
        l = ["d173f2a12b6ff63a77d9fe7bbb590bdb02b826d07739f90ebb016dc9297332be",
             "13a3595f2610c8e4d727130daade66c772fdec4bd2463d773fd0f85c20ced32d",
             "15eca0aa3e2cc2b9b4fbe0629f1dda87f329500fcdcd6ef546d163211266b3b3"]
        self.assertEqual(self.verifier.get_merkle_root(l, s, 3), r)

    def test_verify_merkle(self):
        h = "be38f46f0eccba72416aed715851fd07b881ffb7928b7622847314588e06a6b7"
        self.verifier.verify_merkle(h)
        self.assertEqual(self.verifier.get_confirmations(h), 2)

    def test_random_merkle(self):
        server_url = "electrum.pdmc.net"
        ei = ElectrumInterface(server_url, 50001)
        bcs = EnhancedBlockchainState(server_url, 50001)
        self.verifier.blockchain_state = bcs
        h = '265db1bc122c4dae20dd0b55d55c7b270fb1378054fe624457b73bc28b5edd55'
        self.verifier.verify_merkle(h)
        self.assertTrue(self.verifier.get_confirmations(h) > 3)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_wallet_controller
#!/usr/bin/env python

import unittest

from pycoin.tx.script import opcodes, tools

from coloredcoinlib import ColorSet, InvalidColorDefinitionError
from ngcccbase.pwallet import PersistentWallet
from ngcccbase.wallet_controller import WalletController, AssetMismatchError


class MockBitcoinD(object):
    def __init__(self, txhash):
        self.txhash = txhash
    def sendrawtransaction(self, x):
        return self.txhash
    def getblockcount(self):
        return 1
    def getrawmempool(self):
        return [self.txhash]
    def getrawtransaction(self, t, n):
        return "0100000002f7876bd7227065771c233686c9734c0470905d55c41441241eab1ba35b5ae44f000000008b483045022100e75c071563c902d021575736209caed88f86817bc1f4f8873bdfee0b00770d64022055d1bacdc16e848c202bf429861de4d853bc3d7a7cc9a8cd71741c20373df4ef01410473930d05b479dc75d8b9ae78663b8685bf3913509d8084b5d0ab24876d740c2c790c1c6050fb78e2c0694ea2604c6529d7dcb48384d8516e582e212d2be713cffffffffff7876bd7227065771c233686c9734c0470905d55c41441241eab1ba35b5ae44f010000008b48304502204200e814121376535732a71fd3afb7613fb09c079289fbfaa47ac4510c11d36c022100a72a6be63f2eb8a6ce62df4df3c3415723e709b4280dc1504c9a123af48f624801410473930d05b479dc75d8b9ae78663b8685bf3913509d8084b5d0ab24876d740c2c790c1c6050fb78e2c0694ea2604c6529d7dcb48384d8516e582e212d2be713cfffffffff0210270000000000001976a914c6add3894dbedcd535f13aa60ef6abbcf05b68b188ac447c9a3b000000001976a914ed2b08274a56573e9af0114822a5e867609b7fa288ac00000000"
    def getblock(self, t):
        return {'blockhash': self.getblockhash(''), 'tx': '', 'height': 1, 'previousblockhash': 'coinbase'}
    def getblockhash(self, h):
        return "11111111111111111111111111111111"


class TestWalletController(unittest.TestCase):

    def setUp(self):
        self.path = ":memory:"
        self.config = {'dw_master_key': 'test', 'testnet': True, 'ccc': {
                'colordb_path' : self.path
                }, 'bip0032': False }
        self.pwallet = PersistentWallet(self.path, self.config)
        self.pwallet.init_model()
        self.model = self.pwallet.get_model()
        self.wc = WalletController(self.model)
        self.wc.testing = True
        self.wc.debug = True
        self.colormap = self.model.get_color_map()
        self.bcolorset = ColorSet(self.colormap, [''])
        wam = self.model.get_address_manager()
        self.baddress = wam.get_new_address(self.bcolorset)
        self.baddr = self.baddress.get_address()

        self.blockhash = '00000000c927c5d0ee1ca362f912f83c462f644e695337ce3731b9f7c5d1ca8c'
        self.txhash = '4fe45a5ba31bab1e244114c4555d9070044c73c98636231c77657022d76b87f7'

        script = tools.compile(
            "OP_DUP OP_HASH160 {0} OP_EQUALVERIFY OP_CHECKSIG".format(
                self.baddress.rawPubkey().encode("hex"))).encode("hex")

        self.model.utxo_man.store.add_utxo(self.baddr, self.txhash,
                                           0, 100, script)

        script = tools.compile(
            "OP_DUP OP_HASH160 {0} OP_EQUALVERIFY OP_CHECKSIG".format(
                self.baddress.rawPubkey().encode("hex"))).encode("hex")

        self.model.utxo_man.store.add_utxo(self.baddr, self.txhash,
                                           1, 1000000000, script)

        self.model.ccc.blockchain_state.bitcoind = MockBitcoinD('test')
        def x(s):
            return self.blockhash, True
        self.model.ccc.blockchain_state.get_tx_blockhash = x
        self.moniker = 'test'
        self.wc.issue_coins(self.moniker, 'obc', 10000, 1)
        self.asset = self.model.get_asset_definition_manager(
            ).get_asset_by_moniker(self.moniker)
        self.basset = self.model.get_asset_definition_manager(
            ).get_asset_by_moniker('bitcoin')
        self.color_id = list(self.asset.color_set.color_id_set)[0]
        self.model.ccc.metastore.set_as_scanned(self.color_id, self.blockhash)

    def test_issue(self):
        self.assertRaises(InvalidColorDefinitionError, self.wc.issue_coins,
                          self.moniker, 'nonexistent', 10000, 1)
        item = self.wc.get_history(self.asset)[0]
        self.assertEqual(item['action'], 'issued')
        self.assertEqual(item['value'], 10000)
        self.wc.scan_utxos()
        item = self.wc.get_history(self.asset)[0]
        self.assertEqual(item['action'], 'issued')
        self.assertEqual(item['value'], 10000)

    def test_new_address(self):
        addr = self.wc.get_new_address(self.asset)
        addrs = self.wc.get_all_addresses(self.asset)
        self.assertEqual(len(addr.get_address()), 34)
        self.assertTrue(addr in addrs)
        for d in self.wc.get_received_by_address(self.asset):
            if d['address'] == addr.get_address():
                self.assertEqual(d['value'], 0)

    def test_get_all_assets(self):
        self.assertTrue(self.asset in self.wc.get_all_assets())

    def test_get_balance(self):
        self.assertEqual(self.wc.get_total_balance(self.asset), 10000)

    def test_add_asset(self):
        moniker = 'addtest'
        params = {"monikers": [moniker],
                  "color_set": ['obc:aaaaaaaaaaaaaaaaa:0:0'], "unit": 1}
        self.wc.add_asset_definition(params)
        asset = self.model.get_asset_definition_manager(
            ).get_asset_by_moniker(moniker)
        
        self.assertEqual(self.wc.get_total_balance(asset), 0)
        self.assertEqual(self.wc.get_history(asset), [])

    def test_send(self):
        addr1 = self.wc.get_new_address(self.asset)
        addr2 = self.wc.get_new_address(self.asset)
        color_addrs = [addr1.get_color_address(), addr2.get_color_address()]
        self.wc.send_coins(self.asset, color_addrs, [1000, 2000])
        self.assertRaises(AssetMismatchError, self.wc.send_coins, self.basset,
                          color_addrs, [1000, 2000])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_wallet_model
#!/usr/bin/env python

import unittest

from coloredcoinlib import (ColorSet, ColorDataBuilderManager,
                            AidedColorDataBuilder, ThinColorData)

from ngcccbase.deterministic import DWalletAddressManager
from ngcccbase.pwallet import PersistentWallet
from ngcccbase.txcons import BasicTxSpec, InvalidTargetError
from ngcccbase.txdb import TxDb
from ngcccbase.utxodb import UTXOQuery
from ngcccbase.wallet_model import CoinQueryFactory
from ngcccbase.wallet_controller import WalletController


class TestWalletModel(unittest.TestCase):

    def setUp(self):
        self.path = ":memory:"
        self.config = {
            'hdw_master_key':
                '91813223e97697c42f05e54b3a85bae601f04526c5c053ff0811747db77cfdf5f1accb50b3765377c379379cd5aa512c38bf24a57e4173ef592305d16314a0f4',
            'testnet': True,
            'ccc': {'colordb_path' : self.path},
            }
        self.pwallet = PersistentWallet(self.path, self.config)
        self.pwallet.init_model()
        self.model = self.pwallet.get_model()
        self.colormap = self.model.get_color_map()
        self.bcolorset = ColorSet(self.colormap, [''])
        self.basset = self.model.get_asset_definition_manager(
            ).get_asset_by_moniker('bitcoin')
        self.cqf = self.model.get_coin_query_factory()

    def test_get_tx_db(self):
        self.assertTrue(isinstance(self.model.get_tx_db(), TxDb))

    def test_is_testnet(self):
        self.assertTrue(self.model.is_testnet())

    def test_get_coin_query_factory(self):
        self.assertTrue(isinstance(self.cqf, CoinQueryFactory))
        self.cqf.make_query({'color_set': self.bcolorset})
        self.cqf.make_query({'color_id_set': self.bcolorset.color_id_set})
        self.cqf.make_query({'asset': self.basset})
        self.assertRaises(Exception, self.cqf.make_query, {})

    def test_transform(self):
        tx_spec = BasicTxSpec(self.model)
        self.assertRaises(InvalidTargetError,
                          self.model.transform_tx_spec, tx_spec, 'signed')

    def test_make_query(self):
        q = self.model.make_coin_query({'color_set': self.bcolorset})
        self.assertTrue(isinstance(q, UTXOQuery))

    def test_get_address_manager(self):
        m = self.model.get_address_manager()
        self.assertTrue(issubclass(m.__class__, DWalletAddressManager))

    def test_get_history(self):
        self.config['asset_definitions'] = [
            {"color_set": [""], "monikers": ["bitcoin"], "unit": 100000000},  
            {"color_set": ["obc:03524a4d6492e8d43cb6f3906a99be5a1bcd93916241f759812828b301f25a6c:0:153267"], "monikers": ['test'], "unit": 1},]
        self.config['hdwam'] = {
            "genesis_color_sets": [ 
                ["obc:03524a4d6492e8d43cb6f3906a99be5a1bcd93916241f759812828b301f25a6c:0:153267"],
                ],
            "color_set_states": [
                {"color_set": [""], "max_index": 1},
                {"color_set": ["obc:03524a4d6492e8d43cb6f3906a99be5a1bcd93916241f759812828b301f25a6c:0:153267"], "max_index": 7},
                ]
            }
        self.config['bip0032'] = True
        self.pwallet = PersistentWallet(self.path, self.config)
        self.pwallet.init_model()
        self.model = self.pwallet.get_model()
        # modify model colored coin context, so test runs faster
        ccc = self.model.ccc
        cdbuilder = ColorDataBuilderManager(
            ccc.colormap, ccc.blockchain_state, ccc.cdstore,
            ccc.metastore, AidedColorDataBuilder)

        ccc.colordata = ThinColorData(
            cdbuilder, ccc.blockchain_state, ccc.cdstore, ccc.colormap)

        wc = WalletController(self.model)

        adm = self.model.get_asset_definition_manager()
        asset = adm.get_asset_by_moniker('test')
        self.model.utxo_man.update_all()
        cq = self.model.make_coin_query({"asset": asset})
        utxo_list = cq.get_result()

        # send to the second address so the mempool has something
        addrs = wc.get_all_addresses(asset)
        wc.send_coins(asset, [addrs[1].get_color_address()], [1000])

        history = self.model.get_history_for_asset(asset)
        self.assertTrue(len(history) > 30)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = txcons
"""
txcons.py

Transaction Constructors for the blockchain.
"""

from asset import AssetTarget
from coloredcoinlib import (ColorSet, ColorTarget, SimpleColorValue,
                            ComposedTxSpec, OperationalTxSpec,
                            UNCOLORED_MARKER, OBColorDefinition,
                            InvalidColorIdError, ZeroSelectError)
from binascii import hexlify
import pycoin_txcons

import io
import math


class InsufficientFundsError(Exception):
    pass


class InvalidTargetError(Exception):
    pass


class InvalidTransformationError(Exception):
    pass


class BasicTxSpec(object):
    """Represents a really simple colored coin transaction.
    Specifically, this particular transaction class has not been
    constructed, composed or signed. Those are done in other classes.
    Note this only supports a single asset.
    """
    def __init__(self, model):
        """Create a BasicTxSpec that has a wallet_model <model>
        for an asset <asset>
        """
        self.model = model
        self.targets = []

    def add_target(self, asset_target):
        """Add a ColorTarget <color_target> which specifies the
        colorvalue and address
        """
        if not isinstance(asset_target, AssetTarget):
            raise InvalidTargetError("Not an asset target")
        self.targets.append(asset_target)

    def is_monoasset(self):
        """Returns a boolean representing if the transaction sends
        coins of exactly 1 color.
        """
        if not self.targets:
            raise InvalidTargetError('basic txs is empty')
        asset = self.targets[0].get_asset()
        for target in self.targets:
            if target.get_asset() != asset:
                return False
        return True

    def is_monocolor(self):
        """Returns a boolean representing if the transaction sends
        coins of exactly 1 color.
        """
        if not self.is_monoasset():
            return False
        asset = self.targets[0].get_asset()
        return len(asset.get_color_set().color_id_set) == 1

    def make_operational_tx_spec(self, asset):
        """Given a <tx_spec> of type BasicTxSpec, return
        a SimpleOperationalTxSpec.
        """
        if not self.is_monocolor():
            raise InvalidTransformationError('tx spec type not supported')
        op_tx_spec = SimpleOperationalTxSpec(self.model, asset)
        color_id = list(asset.get_color_set().color_id_set)[0]
        color_def = self.model.get_color_def(color_id)
        for target in self.targets:
            colorvalue = SimpleColorValue(colordef=color_def,
                                          value=target.get_value())
            colortarget = ColorTarget(target.get_address(), colorvalue)
            op_tx_spec.add_target(colortarget)
        return op_tx_spec


class BaseOperationalTxSpec(OperationalTxSpec):
    def get_required_fee(self, tx_size):
        """Given a transaction that is of size <tx_size>,
        return the transaction fee in Satoshi that needs to be
        paid out to miners.
        """
        base_fee = 10000.0
        fee_value = math.ceil((tx_size * base_fee) / 1000)
        return SimpleColorValue(colordef=UNCOLORED_MARKER, 
                                value=fee_value)

    def get_dust_threshold(self):
        return SimpleColorValue(colordef=UNCOLORED_MARKER, value=5500)

    def _select_enough_coins(self, colordef,
                             utxo_list, required_sum_fn):
        ssum = SimpleColorValue(colordef=colordef, value=0)
        selection = []
        required_sum = None
        for utxo in utxo_list:
            ssum += SimpleColorValue.sum(utxo.colorvalues)
            selection.append(utxo)
            required_sum = required_sum_fn(utxo_list)
            if ssum >= required_sum:
                return selection, ssum
        raise InsufficientFundsError('not enough coins: %s requested, %s found'
                                     % (required_sum, ssum))
    
    def _validate_select_coins_parameters(self, colorvalue, use_fee_estimator):
        colordef = colorvalue.get_colordef()
        if colordef != UNCOLORED_MARKER and use_fee_estimator:
            raise Exception("fee estimator can only be used\
with uncolored coins")


class SimpleOperationalTxSpec(BaseOperationalTxSpec):
    """Subclass of OperationalTxSpec which uses wallet model.
    Represents a transaction that's ready to be composed
    and then signed. The parent is an abstract class.
    """
    def __init__(self, model, asset):
        """Initialize a transaction that uses a wallet model
        <model> and transfers asset/color <asset>.
        """
        super(SimpleOperationalTxSpec, self).__init__()
        self.model = model
        self.targets = []
        self.asset = asset

    def add_target(self, color_target):
        """Add a ColorTarget <color_target> to the transaction
        """
        if not isinstance(color_target, ColorTarget):
            raise InvalidTargetError("Target is not an instance of ColorTarget")
        self.targets.append(color_target)

    def get_targets(self):
        """Get a list of (receiving address, color_id, colorvalue)
        triplets representing all the targets for this tx.
        """
        return self.targets

    def get_change_addr(self, color_def):
        """Get an address associated with color definition <color_def>
        that is in the current wallet for receiving change.
        """
        color_id = color_def.color_id
        wam = self.model.get_address_manager()
        color_set = None
        if color_def == UNCOLORED_MARKER:
            color_set = ColorSet.from_color_ids(self.model.get_color_map(),
                                                [0])
        elif self.asset.get_color_set().has_color_id(color_id):
            color_set = self.asset.get_color_set()
        if color_set is None:
            raise InvalidColorIdError('wrong color id')
        aw = wam.get_change_address(color_set)
        return aw.get_address()

    def select_coins(self, colorvalue, use_fee_estimator=None):
        """Return a list of utxos and sum that corresponds to
        the colored coins identified by <color_def> of amount <colorvalue>
        that we'll be spending from our wallet.
        """
        self._validate_select_coins_parameters(colorvalue, use_fee_estimator)
        def required_sum_fn(selection):
            if use_fee_estimator:
                return colorvalue + use_fee_estimator.estimate_required_fee(
                    extra_txins=len(selection))
            else:
                return colorvalue
        required_sum_0 = required_sum_fn([])
        if required_sum_0.get_value() == 0:
            # no coins need to be selected
            return [], required_sum_0
        colordef = colorvalue.get_colordef()
        color_id = colordef.get_color_id()
        cq = self.model.make_coin_query({"color_id_set": set([color_id])})
        utxo_list = cq.get_result()
        return self._select_enough_coins(colordef, utxo_list, required_sum_fn)



class RawTxSpec(object):
    """Represents a transaction which can be serialized.
    """
    def __init__(self, model, pycoin_tx, composed_tx_spec=None):
        self.model = model
        self.pycoin_tx = pycoin_tx
        self.composed_tx_spec = composed_tx_spec
        self.update_tx_data()
        self.intent = None

    def get_intent(self):
        return self.intent

    def get_hex_txhash(self):
        the_hash = self.pycoin_tx.hash()
        return the_hash[::-1].encode('hex')

    def update_tx_data(self):
        """Updates serialized form of transaction.
        """
        s = io.BytesIO()
        self.pycoin_tx.stream(s)
        self.tx_data = s.getvalue()

    @classmethod
    def from_composed_tx_spec(cls, model, composed_tx_spec):
        testnet = model.is_testnet()
        tx = pycoin_txcons.construct_standard_tx(composed_tx_spec, testnet)
        return cls(model, tx, composed_tx_spec)

    @classmethod
    def from_tx_data(cls, model, tx_data):
        pycoin_tx = pycoin_txcons.deserialize(tx_data)
        composed_tx_spec = pycoin_txcons.reconstruct_composed_tx_spec(
            model, pycoin_tx)
        return cls(model, pycoin_tx, composed_tx_spec)

    def sign(self, utxo_list):
        pycoin_txcons.sign_tx(
            self.pycoin_tx, utxo_list, self.model.is_testnet())
        self.update_tx_data()

    def get_tx_data(self):
        """Returns the signed transaction data.
        """
        return self.tx_data

    def get_hex_tx_data(self):
        """Returns the hex version of the signed transaction data.
        """
        return hexlify(self.tx_data).decode("utf8")

def compose_uncolored_tx(tx_spec):
    """ compose a simple bitcoin transaction """
    composed_tx_spec = tx_spec.make_composed_tx_spec()
    targets = tx_spec.get_targets()
    composed_tx_spec.add_txouts(targets)
    ttotal = ColorTarget.sum(targets)
    sel_utxos, sum_sel_coins = tx_spec.select_coins(ttotal, composed_tx_spec)
    composed_tx_spec.add_txins(sel_utxos)
    fee = composed_tx_spec.estimate_required_fee()
    change = sum_sel_coins - ttotal - fee
    # give ourselves the change
    if change > tx_spec.get_dust_threshold():
        composed_tx_spec.add_txout(value=change,
                                   target_addr=tx_spec.get_change_addr(UNCOLORED_MARKER),
                                   is_fee_change=True)
    return composed_tx_spec


class TransactionSpecTransformer(object):
    """An object that can transform one type of transaction into another.
    Essentially has the ability to take a transaction, compose it
    and sign it by returning the appropriate objects.

    The general flow of transaction types is this:
    BasicTxSpec -> SimpleOperationalTxSpec -> ComposedTxSpec -> SignedTxSpec
    "basic"     -> "operational"           -> "composed"     -> "signed"
    """

    def __init__(self, model, config):
        """Create a transaction transformer object for wallet_model <model>
        and a wallet configuration <config>
        """
        self.model = model
        self.testnet = config.get('testnet', False)

    def get_tx_composer(self, op_tx_spec):
        """Returns a function which is able to convert a given operational
        tx spec <op_tx_spec> into a composed tx spec
        """
        if op_tx_spec.is_monocolor():
            color_def = op_tx_spec.get_targets()[0].get_colordef()
            if color_def == UNCOLORED_MARKER:
                return compose_uncolored_tx
            else:
                return color_def.compose_tx_spec
        else:
            # grab the first color def and hope that its compose_tx_spec
            # will be able to handle it. if transaction has incompatible
            # colors, compose_tx_spec will throw an exception
            for target in op_tx_spec.get_targets():
                tgt_color_def = target.get_colordef()
                if tgt_color_def is UNCOLORED_MARKER:
                    continue
                else:
                    return tgt_color_def.compose_tx_spec
            return None

    def classify_tx_spec(self, tx_spec):
        """For a transaction <tx_spec>, returns a string that represents
        the type of transaction (basic, operational, composed, signed)
        that it is.
        """
        if isinstance(tx_spec, BasicTxSpec):
            return 'basic'
        elif isinstance(tx_spec, OperationalTxSpec):
            return 'operational'
        elif isinstance(tx_spec, ComposedTxSpec):
            return 'composed'
        elif isinstance(tx_spec, RawTxSpec):
            return 'signed'
        else:
            return None

    def transform_basic(self, tx_spec, target_spec_kind):
        """Takes a basic transaction <tx_spec> and returns a transaction
        of type <target_spec_kind> which is one of (operational,
        composed, signed).
        """
        if target_spec_kind in ['operational', 'composed', 'signed']:
            if tx_spec.is_monocolor():
                asset = tx_spec.targets[0].get_asset()
                operational_ts = tx_spec.make_operational_tx_spec(asset)
                return self.transform(operational_ts, target_spec_kind)
        raise InvalidTransformationError('do not know how to transform tx spec')

    def transform_operational(self, tx_spec, target_spec_kind):
        """Takes an operational transaction <tx_spec> and returns a
        transaction of type <target_spec_kind> which is one of
        (composed, signed).
        """
        if target_spec_kind in ['composed', 'signed']:
            composer = self.get_tx_composer(tx_spec)
            if composer:
                composed = composer(tx_spec)
                return self.transform(composed, target_spec_kind)
        raise InvalidTransformationError('do not know how to transform tx spec')

    def transform_composed(self, tx_spec, target_spec_kind):
        """Takes a SimpleComposedTxSpec <tx_spec> and returns
        a signed transaction. For now, <target_spec_kind> must
        equal "signed" or will throw an exception.
        """
        if target_spec_kind in ['signed']:
            rtxs = RawTxSpec.from_composed_tx_spec(self.model, tx_spec)
            rtxs.sign(tx_spec.get_txins())
            return rtxs
        raise InvalidTransformationError('do not know how to transform tx spec')

    def transform_signed(self, tx_spec, target_spec_kind):
        """This method is not yet implemented.
        """
        raise InvalidTransformationError('do not know how to transform tx spec')

    def transform(self, tx_spec, target_spec_kind):
        """Transform a transaction <tx_spec> into another type
        of transaction defined by <target_spec_kind> and returns it.
        """
        spec_kind = self.classify_tx_spec(tx_spec)
        if spec_kind is None:
            raise InvalidTransformationError('spec kind is not recognized')
        if spec_kind == target_spec_kind:
            return tx_spec
        if spec_kind == 'basic':
            return self.transform_basic(tx_spec, target_spec_kind)
        elif spec_kind == 'operational':
            return self.transform_operational(tx_spec, target_spec_kind)
        elif spec_kind == 'composed':
            return self.transform_composed(tx_spec, target_spec_kind)
        elif spec_kind == 'signed':
            return self.transform_signed(tx_spec, target_spec_kind)


########NEW FILE########
__FILENAME__ = txdb
from time import time
from urllib2 import HTTPError
import threading
import os

from pycoin.encoding import double_sha256

from coloredcoinlib.store import DataStore, DataStoreConnection, PersistentDictStore, unwrap1
from ngcccbase.services.blockchain import BlockchainInfoInterface
from txcons import RawTxSpec
from blockchain import VerifiedBlockchainState



TX_STATUS_UNKNOWN = 0
TX_STATUS_UNCONFIRMED = 1
TX_STATUS_CONFIRMED = 2
TX_STATUS_INVALID = 3

create_transaction_table = """\
CREATE TABLE tx_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    txhash TEXT,
    data TEXT,
    status INTEGER,
    block_height INTEGER
);
"""

class TxDataStore(DataStore):
    def __init__(self, conn):
        super(TxDataStore, self).__init__(conn)
        if not self.table_exists('tx_data'):
            self.execute(create_transaction_table)
            self.execute(
                "CREATE UNIQUE INDEX tx_data_txhash ON tx_data (txhash)")
        if not self.column_exists('tx_data', 'block_height'):
            self.execute(
                "ALTER TABLE tx_data ADD COLUMN block_height INTEGER")

    def purge_tx_data(self):
        self.execute("DELETE FROM tx_data")

    def add_tx(self, txhash, txdata, status=TX_STATUS_UNKNOWN):
        return self.execute(
            "INSERT INTO tx_data (txhash, data, status) VALUES (?, ?, ?)",
            (txhash, txdata, status))

    def set_tx_status(self, txhash, status):
        self.execute("UPDATE tx_data SET status = ? WHERE txhash = ?",
                     (status, txhash))
    
    def get_tx_status(self, txhash):
        return unwrap1(self.execute("SELECT status FROM tx_data WHERE txhash = ?",
                                    (txhash, )).fetchone())

    def get_tx_by_hash(self, txhash):
        return self.execute("SELECT * FROM tx_data WHERE txhash = ?",
                            (txhash, )).fetchone()

    def get_all_tx_hashes(self):
        return map(unwrap1,
                   self.execute("SELECT txhash FROM tx_data").fetchall())

    def set_block_height(self, txhash, height):
        self.execute("UPDATE tx_data SET block_height = ? WHERE txhash = ?",
                     (height, txhash))

    def reset_from_height(self, height):
        self.execute("UPDATE tx_data SET status = 0 \
WHERE (block_height >= ?) OR (block_height IS NULL)",
                     (height,))

class BaseTxDb(object):
    def __init__(self, model, config):
        self.model = model
        self.store = TxDataStore(self.model.store_conn.conn)
        self.last_status_check = dict()
        self.recheck_interval = 60
        self.bs = self.model.get_blockchain_state()

    def purge_tx_db(self):
        self.store.purge_tx_data()

    def get_all_tx_hashes(self):
        return self.store.get_all_tx_hashes()

    def get_tx_by_hash(self, txhash):
        return self.store.get_tx_by_hash(txhash)

    def update_tx_block_height(self, txhash, status):
        if status == TX_STATUS_CONFIRMED:
            try:
                block_hash, _ = self.bs.get_tx_blockhash(txhash)
                height = self.bs.get_block_height(block_hash)
            except:
                return
            self.store.set_block_height(txhash, height)

    def add_raw_tx(self, raw_tx, status=TX_STATUS_UNCONFIRMED):
        return self.add_tx(raw_tx.get_hex_txhash(),
                           raw_tx.get_hex_tx_data(),
                           raw_tx,
                           status)

    def add_tx_by_hash(self, txhash, status=None):
        bs = self.model.get_blockchain_state()
        txdata = bs.get_raw(txhash)
        raw_tx = RawTxSpec.from_tx_data(self.model,
                                        txdata.decode('hex'))
        return self.add_tx(txhash, txdata, raw_tx, status)

    def add_tx(self, txhash, txdata, raw_tx, status=None):
        if not self.store.get_tx_by_hash(txhash):
            if not status:
                status = self.identify_tx_status(txhash)
            self.store.add_tx(txhash, txdata, status)
            self.update_tx_block_height(txhash, status)
            self.last_status_check[txhash] = time()
            self.model.get_coin_manager().apply_tx(txhash, raw_tx)
            return True
        else:
            old_status = self.store.get_tx_status(txhash)
            new_status = self.maybe_recheck_tx_status(txhash, old_status)
            return old_status != new_status

    def recheck_tx_status(self, txhash):
        status = self.identify_tx_status(txhash)
        self.store.set_tx_status(txhash, status)
        self.update_tx_block_height(txhash, status)
        return status
   
    def maybe_recheck_tx_status(self, txhash, status):
        if status == TX_STATUS_CONFIRMED:
            # do not recheck those which are already confirmed
            return status
        if (time() - self.last_status_check.get(txhash, 0)) < self.recheck_interval:
            return status
        status = self.recheck_tx_status(txhash)
        self.last_status_check[txhash] = time()
        return status

    def is_tx_valid(self, txhash):
        status = self.store.get_tx_status(txhash)
        if status == TX_STATUS_CONFIRMED:
            return True
        status = self.maybe_recheck_tx_status(txhash, status)
        return status != TX_STATUS_INVALID

    def is_tx_confirmed(self, txhash):
        status = self.store.get_tx_status(txhash)
        if status != TX_STATUS_CONFIRMED:
            status = self.maybe_recheck_tx_status(txhash, status)
        return status == TX_STATUS_CONFIRMED


class NaiveTxDb(BaseTxDb):
    """Native TxDb trusts results of get_blockchain_state"""
    def identify_tx_status(self, txhash):
        block_hash, in_mempool = self.model.get_blockchain_state().\
            get_tx_blockhash(txhash)
        if block_hash:
            return TX_STATUS_CONFIRMED
        elif in_mempool:
            return TX_STATUS_UNCONFIRMED
        else:
            return TX_STATUS_INVALID


class TrustingTxDb(BaseTxDb):
    """TxDb which trusts confirmation data it gets from an external source"""
    
    def __init__(self, model, config, get_tx_confirmations):
        super(TrustingTxDb, self).__init__(model, config)
        self.confirmed_txs = set()
        self.get_tx_confirmations = get_tx_confirmations

    def identify_tx_status(self, txhash):
        if txhash in self.confirmed_txs:
            return TX_STATUS_CONFIRMED
        confirmations = self.get_tx_confirmations(txhash)
        if confirmations > 0:
            self.confirmed_txs.add(txhash)
            return TX_STATUS_CONFIRMED
        elif confirmations == 0:
            return TX_STATUS_UNCONFIRMED
        else:
            # check if BlockchainState is aware of it
            block_hash, in_mempool = self.model.get_blockchain_state().\
                get_tx_blockhash(txhash)
            if block_hash or in_mempool:
                return TX_STATUS_UNCONFIRMED
            else:
                return TX_STATUS_INVALID


class VerifiedTxDb(BaseTxDb):
    def __init__(self, model, config):
        super(VerifiedTxDb, self).__init__(model, config)
        self.bs = self.model.get_blockchain_state()
        self.vbs = VerifiedBlockchainState(
            self.bs,
            self,
            config.get('testnet', False),
            os.path.dirname(self.model.store_conn.path)
        )
        self.vbs.start()
        self.lock = threading.Lock()
        self.verified_tx = {}

    def __del__(self):
        if self.vbs:
            self.vbs.stop()

    def _get_merkle_root(self, merkle_s, start_hash, pos):
        hash_decode = lambda x: x.decode('hex')[::-1]
        hash_encode = lambda x: x[::-1].encode('hex')

        h = hash_decode(start_hash)
        # i is the "level" or depth of the binary merkle tree.
        # item is the complementary hash on the merkle tree at this level
        for i, item in enumerate(merkle_s):
            # figure out if it's the left item or right item at this level
            if pos >> i & 1:
                # right item (odd at this level)
                h = double_sha256(hash_decode(item) + h)
            else:
                # left item (even at this level)
                h = double_sha256(h + hash_decode(item))
        return hash_encode(h)

    def _verify_merkle(self, txhash):
        result = self.bs.get_merkle(txhash)
        merkle, tx_height, pos = result.get('merkle'), \
            result.get('block_height'), result.get('pos')

        merkle_root = self._get_merkle_root(merkle, txhash, pos)
        header = self.vbs.get_header(tx_height)
        if header is None:
            return False
        if header.get('merkle_root') != merkle_root:
            return False

        with self.lock:
            self.verified_tx[txhash] = tx_height
        return True

    def update_tx_block_height(self, txhash, status):
        with self.lock:
            if txhash in self.verified_tx:
                self.store.set_block_height(txhash,
                                            self.verified_tx[txhash])

    def drop_from_height(self, height):
        with self.lock:
            self.verified_tx = {key: value for key, value in self.verified_tx.items() if value < height}

    def get_confirmations(self, txhash):
        with self.lock:
            if txhash in self.verified_tx:
                height = self.verified_tx[txhash]
                return self.vbs.height - height + 1
            else:
                return None

    def identify_tx_status(self, txhash):
        block_hash, in_mempool = self.bs.get_tx_blockhash(txhash)
        if (not block_hash) and (not in_mempool):
            return TX_STATUS_INVALID
        if not block_hash:
            return TX_STATUS_UNCONFIRMED
        confirmations = self.get_confirmations(txhash)
        if confirmations is None:
            verified = self._verify_merkle(txhash)
            if verified:
                return self.identify_tx_status(txhash)
            else:
                return TX_STATUS_UNCONFIRMED
        if confirmations == 0:
            return TX_STATUS_UNCONFIRMED
        return TX_STATUS_CONFIRMED

########NEW FILE########
__FILENAME__ = txhistory
import time
from coloredcoinlib.store import PersistentDictStore
from asset import AdditiveAssetValue, AssetTarget
from txcons import RawTxSpec

def asset_value_to_data(av):
    return (av.get_asset().get_id(),
            av.get_value())

class TxHistoryEntry(object):
    def __init__(self, model, data):
        self.txhash = data['txhash']
        self.txtime = data['txtime']
        self.txtype = data['txtype']
        self.data = data
        self.model = model

    @classmethod
    def from_data(cls, model, data):
        txtype = data['txtype']
        if txtype == 'send':
            return TxHistoryEntry_Send(model, data)
        elif txtype == 'receive':
            return TxHistoryEntry_Receive(model, data)
        elif txtype == 'trade':
            return TxHistoryEntry_Trade(model, data)
        else:
            return TxHistoryEntry(model, data)


class TxHistoryEntry_Send(TxHistoryEntry):
    def __init__(self, model, data):
        super(TxHistoryEntry_Send, self).__init__(model, data)
        self.asset_id = data['asset_id']
        self.targets = data['targets']

    def get_asset(self):
        adm = self.model.get_asset_definition_manager()
        return adm.get_asset_by_id(self.asset_id)

    def get_targets(self):
        asset = self.get_asset()
        asset_targets = []
        for (tgt_addr, tgt_value) in self.targets:
            asset_value = AdditiveAssetValue(asset=asset,
                                             value=tgt_value)
            asset_targets.append(AssetTarget(tgt_addr, 
                                             asset_value))
        return asset_targets

class TxHistoryEntry_Receive(TxHistoryEntry):
    def __init__(self, model, data):
        super(TxHistoryEntry_Receive, self).__init__(model, data)
        self.out_idxs = data['out_idxs']
        
    def get_targets(self):
        targets = []
        coindb = self.model.get_coin_manager()
        adm = self.model.get_asset_definition_manager()
        for out_idx in self.out_idxs:
            coin = coindb.find_coin(self.txhash, out_idx)
            colorvalues = coin.get_colorvalues()
            if not colorvalues:
                continue
            assert len(colorvalues) == 1
            asset_value = adm.get_asset_value_for_colorvalue(
                colorvalues[0])
            targets.append(AssetTarget(coin.address,
                                       asset_value))
        return targets

class TxHistoryEntry_Trade(TxHistoryEntry):
    def __init__(self, model, data):
        TxHistoryEntry.__init__(self, model, data)
        self.in_values = data['in_values']
        self.out_values = data['out_values']
        
    def get_values(self, values):
        adm = self.model.get_asset_definition_manager()
        avalues = []
        for asset_id, value in values:
            asset = adm.get_asset_by_id(asset_id)
            avalues.append(AdditiveAssetValue(asset=asset,
                                             value=value))
        return avalues

    def get_in_values(self):
        return self.get_values(self.in_values)

    def get_out_values(self):
        return self.get_values(self.out_values)

    
class TxHistory(object):
    def __init__(self, model):
        self.model = model
        self.entries = PersistentDictStore(
            self.model.store_conn.conn, "txhistory")
    
    def decode_entry(self, entry_data):
        print ('entry_data', entry_data)
        return TxHistoryEntry.from_data(self.model, entry_data)

    def get_entry(self, txhash):
        entry = self.entries.get(txhash)
        if entry:
            return self.decode_entry(entry)
        else:
            return None

    def add_send_entry(self, txhash, asset, target_addrs, target_values):
        self.entries[txhash] = {"txhash": txhash,
                                "txtype": 'send',
                                "txtime": int(time.time()),
                                "asset_id": asset.get_id(),
                                "targets": zip(target_addrs, target_values)}

    def get_all_entries(self):
        return sorted([self.decode_entry(e) 
                       for e in self.entries.values()],
                      key=lambda txe: txe.txtime)

    def populate_history(self):
        txdb = self.model.get_tx_db()
        for txhash in txdb.get_all_tx_hashes():
            if txhash not in self.entries:
                tx_data = txdb.get_tx_by_hash(txhash)['data']
                raw_tx  = RawTxSpec.from_tx_data(self.model,
                                                 tx_data.decode('hex'))
                self.add_entry_from_tx(raw_tx)

    def add_receive_entry(self, txhash, received_coins):
        out_idxs = [coin.outindex
                    for coin in received_coins]
        self.entries[txhash] = {"txhash": txhash,
                                "txtype": 'receive',
                                "txtime": int(time.time()), # TODO !!!
                                "out_idxs": out_idxs}

    def add_trade_entry(self, txhash, in_colorvalue, out_colorvalue):
        adm = self.model.get_asset_definition_manager()
        in_assetvalue = adm.get_asset_value_for_colorvalue(in_colorvalue)
        out_assetvalue = adm.get_asset_value_for_colorvalue(out_colorvalue)
        self.entries[txhash] = {"txhash": txhash,
                                "txtype": 'trade',
                                "txtime": int(time.time()),
                                "in_values": [asset_value_to_data(in_assetvalue)],
                                "out_values": [asset_value_to_data(out_assetvalue)]}
    
    def add_unknown_entry(self, txhash):
        self.entries[txhash] = {"txhash": txhash,
                                "txtype": 'unknown',
                                "txtime": int(time.time())}        
        
    def add_entry_from_tx(self, raw_tx):
        coindb = self.model.get_coin_manager()
        spent_coins, received_coins = coindb.get_coins_for_transaction(raw_tx)
        if (not spent_coins) and (not received_coins):
            return
        if not spent_coins:
            self.add_receive_entry(raw_tx.get_hex_txhash(),
                                   received_coins)
        else:
            # TODO: classify p2ptrade and send transactions
            self.add_unknown_entry(raw_tx.get_hex_txhash())

########NEW FILE########
__FILENAME__ = utxo_fetcher
"""
UTXO Fetcher:

fetches information about unspent transaction outputs from
external source (according to config) and feeds it to 
CoinManager.
"""

from ngcccbase.services.blockchain import BlockchainInfoInterface, AbeInterface
from ngcccbase.services.electrum import ElectrumInterface
from ngcccbase.services.helloblock import HelloBlockInterface

from time import sleep
import Queue
import threading
import logging

DEFAULT_ELECTRUM_SERVER = "btc.it-zone.org"
DEFAULT_ELECTRUM_PORT = 50001

class BaseUTXOFetcher(object):
    def __init__(self, interface):
        self.interface = interface

    @classmethod
    def make_interface(cls, model, params):
        use = params.get('interface', 'helloblock')
        if model.testnet:
            if use != 'helloblock':
                use = 'abe_testnet'
        if use == 'helloblock':
            return HelloBlockInterface(model.testnet)
        elif use == 'blockchain.info':
            return BlockchainInfoInterface()
        elif use == 'abe_testnet':
            return AbeInterface()
        elif use == 'electrum':
            electrum_server = params.get(
                'electrum_server', DEFAULT_ELECTRUM_SERVER)
            electrum_port = params.get(
                'electrum_port', DEFAULT_ELECTRUM_PORT)
            return ElectrumInterface(electrum_server, electrum_port)
        else:
            raise Exception('unknown service for UTXOFetcher')        

    def scan_address(self, address):
        try:
            for data in self.interface.get_utxo(address):
                self.add_utxo(address, data)
        except Exception as e:
            if "%s" % e != "No JSON object could be decoded":
                print e
                raise

class SimpleUTXOFetcher(BaseUTXOFetcher):
    def __init__(self, model, params):
        """Create a fetcher object given configuration in <params>
        """
        super(SimpleUTXOFetcher, self).__init__(
            self.make_interface(model, params))
        self.model = model

    def add_utxo(self, address, data):
        txhash = data[0]
        self.model.get_tx_db().add_tx_by_hash(txhash)

    def scan_all_addresses(self):
        wam = self.model.get_address_manager()
        for address_rec in wam.get_all_addresses():
            self.scan_address(address_rec.get_address())

class AsyncUTXOFetcher(BaseUTXOFetcher):
    def __init__(self, model, params):
        super(AsyncUTXOFetcher, self).__init__(
            self.make_interface(model, params))
        self.logger = logging.getLogger('ngcccbase.utxo_fetcher.async')
        self.model = model
        self.hash_queue = Queue.Queue()
        self.address_list = []
        self._stop = threading.Event()

    def update(self):
        wam = self.model.get_address_manager()
        self.address_list = [ar.get_address()
                             for ar in wam.get_all_addresses()]
        
        any_got_updates = False
        while not self.hash_queue.empty():
            got_updates = self.model.get_tx_db().add_tx_by_hash(self.hash_queue.get())
            any_got_updates = any_got_updates or got_updates
        return any_got_updates
            
    def add_utxo(self, address, data):
        txhash = data[0]
        self.hash_queue.put(txhash)

    def stop(self):
        self._stop.set()

    def start_thread(self):
        thread = threading.Thread(target=self.thread_loop)
        thread.start()
        
    def thread_loop(self):
        while not self._stop.is_set():
            try:
                address_list = self.address_list
                for address in address_list:
                    self.logger.debug('scanning address %s', address)
                    if self._stop.is_set():
                        break
                    self.scan_address(address)
                    if self._stop.is_set():
                        break
                    sleep(1)
            except Exception as e:
                print (e)
                sleep(20)
    
    

########NEW FILE########
__FILENAME__ = wallet_controller
"""
wallet_controller.py

Controls wallet model in a high level manner
Executes high level tasks such as get balance
"""

from asset import AssetTarget, AdditiveAssetValue
from coindb import CoinQuery
from coloredcoinlib import (InvalidColorDefinitionError, ColorDefinition,
                            GENESIS_OUTPUT_MARKER,
                            ColorTarget, SimpleColorValue)
from txcons import BasicTxSpec, SimpleOperationalTxSpec
from wallet_model import ColorSet


class AssetMismatchError(Exception):
    pass


class WalletController(object):
    """Controller for a wallet. Used for executing tasks related to the wallet.
    """
    def __init__(self, model):
        """Given a wallet model <model>, create a wallet controller.
        """
        self.model = model
        self.debug = False
        self.testing = False

    def publish_tx(self, signed_tx_spec):
        """Given a signed transaction <signed_tx_spec>, publish the transaction
        to the public bitcoin blockchain. Prints the transaction hash as a
        side effect. Returns the transaction hash.
        """
        txhex = signed_tx_spec.get_hex_tx_data()
        print txhex
        txhash = signed_tx_spec.get_hex_txhash()
        r_txhash = None
        blockchain_state = self.model.ccc.blockchain_state
        try:
            r_txhash = blockchain_state.publish_tx(txhex)
        except Exception as e:                      # pragma: no cover
            print ("got error %s from bitcoind" % e)  # pragma: no cover
        
        if r_txhash and (r_txhash != txhash) and not self.testing:
            raise Exception('bitcoind reports different txhash')  # pragma: no cover
        
        """if r_txhash is None:                                      # pragma: no cover
            # bitcoind did not eat our txn, check if it is mempool
            mempool = bitcoind.getrawmempool()                    # pragma: no cover
            if txhash not in mempool:                             # pragma: no cover
                raise Exception(                                  # pragma: no cover
                    "bitcoind didn't accept the transaction")     # pragma: no cover"""

        if signed_tx_spec.composed_tx_spec:
            self.model.txdb.add_raw_tx(signed_tx_spec)
        return txhash

    def full_rescan(self):
        """Updates all Unspent Transaction Outs for addresses associated with
        this wallet."""
        self.model.get_coin_manager().purge_coins()
        self.model.get_tx_db().purge_tx_db()
        wam = self.model.get_address_manager()
        bc_interface = self.model.utxo_fetcher.interface
        tx_hashes = []
        for ar in wam.get_all_addresses():
            tx_hashes.extend(bc_interface.get_address_history(ar.get_address()))
        sorted_txs = self.model.get_blockchain_state().sort_txs(tx_hashes)
        txdb = self.model.get_tx_db()
        for tx in sorted_txs:
            txdb.add_tx_by_hash(tx.hash)
        self.model.tx_history.populate_history()

    def scan_utxos(self):
        self.model.utxo_fetcher.scan_all_addresses()

    def send_coins(self, asset, target_addrs, raw_colorvalues):
        """Sends coins to address <target_addr> of asset/color <asset>
        of amount <colorvalue> Satoshis.
        """
        tx_spec = BasicTxSpec(self.model)
        adm = self.model.get_asset_definition_manager()
        colormap = self.model.get_color_map()
        for target_addr, raw_colorvalue in zip(target_addrs, raw_colorvalues):
            # decode the address
            address_asset, address = adm.get_asset_and_address(target_addr)
            if asset != address_asset:
                raise AssetMismatchError("Address and asset don't match: %s %s" %
                                         (asset, address_asset))
            assettarget = AssetTarget(address,
                                      AdditiveAssetValue(asset=asset,
                                                         value=raw_colorvalue))
            tx_spec.add_target(assettarget)
        signed_tx_spec = self.model.transform_tx_spec(tx_spec, 'signed')
        if self.debug:
            print ("In:")
            for txin in signed_tx_spec.composed_tx_spec.txins:
                print (txin.prevout)
            print ("Out:")
            for txout in signed_tx_spec.composed_tx_spec.txouts:
                print (txout.value)
        txhash = self.publish_tx(signed_tx_spec)
        self.model.tx_history.add_send_entry(txhash, asset, 
                                             target_addrs, raw_colorvalues)

    def issue_coins(self, moniker, pck, units, atoms_in_unit):
        """Issues a new color of name <moniker> using coloring scheme
        <pck> with <units> per share and <atoms_in_unit> total.
        """

        color_definition_cls = ColorDefinition.get_color_def_cls_for_code(pck)
        if not color_definition_cls:
            raise InvalidColorDefinitionError('color scheme %s not recognized' % pck)

        total = units * atoms_in_unit
        op_tx_spec = SimpleOperationalTxSpec(self.model, None)
        wam = self.model.get_address_manager()
        address = wam.get_new_genesis_address()
        colorvalue = SimpleColorValue(colordef=GENESIS_OUTPUT_MARKER,
                                      value=total)
        color_target = ColorTarget(address.get_address(), colorvalue)
        op_tx_spec.add_target(color_target)
        genesis_ctxs = color_definition_cls.compose_genesis_tx_spec(op_tx_spec)
        genesis_tx = self.model.transform_tx_spec(genesis_ctxs, 'signed')
        height = self.model.ccc.blockchain_state.get_block_count() - 1
        genesis_tx_hash = self.publish_tx(genesis_tx)
        color_desc = ':'.join([pck, genesis_tx_hash, '0', str(height)])
        adm = self.model.get_asset_definition_manager()
        asset = adm.add_asset_definition({"monikers": [moniker],
                                          "color_set": [color_desc],
                                          "unit": atoms_in_unit})
        wam.update_genesis_address(address, asset.get_color_set())

        # scan the tx so that the rest of the system knows
        self.model.ccc.colordata.cdbuilder_manager.scan_txhash(
            asset.color_set.color_id_set, genesis_tx_hash)

    def get_new_address(self, asset):
        """Given an asset/color <asset>, create a new bitcoin address
        that can receive it. Returns the AddressRecord object.
        """
        wam = self.model.get_address_manager()
        return wam.get_new_address(asset)

    def get_all_addresses(self, asset):
        """Given an asset/color <asset>, return a list of AddressRecord
        objects that correspond in this wallet.
        """
        wam = self.model.get_address_manager()
        return wam.get_addresses_for_color_set(asset.get_color_set())

    def get_all_assets(self):
        """Return all assets that are currently registered
        """
        adm = self.model.get_asset_definition_manager()
        return adm.get_all_assets()

    def add_asset_definition(self, params):
        """Imports an asset/color with the params <params>.
        The params consist of:
        monikers - List of color names (e.g. "red")
        color_set - List of color definitions (e.g. "obc:f0b...d565:0:128649")
        """
        self.model.get_asset_definition_manager().add_asset_definition(params)

    def get_received_by_address(self, asset):
        utxo_list = \
            (self.model.make_coin_query({"asset": asset, "spent": False}).get_result()
             +
             self.model.make_coin_query({"asset": asset, "spent": True}).get_result())
        ars = self.get_all_addresses(asset)
        addresses = [ar.get_address() for ar in ars]
        retval = [{'address': ar.get_address(),
                   'color_address': ar.get_color_address(),
                   'value': asset.get_null_colorvalue()} for ar in ars]
        for utxo in utxo_list:
            i = addresses.index(utxo.address_rec.get_address())
            retval[i]['value'] += asset.get_colorvalue(utxo)
        return retval

    def get_coinlog(self):
        coinlog = []
        for asset in self.get_all_assets():
            query_1 = CoinQuery(self.model, asset.get_color_set(),
                                {'spent': True, 'include_unconfirmed': True})
            query_2 = CoinQuery(self.model, asset.get_color_set(),
                                {'spent': False, 'include_unconfirmed': True})
            for address in self.get_all_addresses(asset):
                for coin in query_1.get_coins_for_address(address):
                    coin.asset = asset
                    coin.address_rec = address
                    coinlog.append(coin)
                for coin in query_2.get_coins_for_address(address):
                    coin.asset = asset
                    coin.address_rec = address
                    coinlog.append(coin)
        return coinlog

    def _get_balance(self, asset, options):
        """Returns an integer value corresponding to the total number
        of Satoshis owned of asset/color <asset>.
        """
        query = {"asset": asset}
        query.update(options)
        cq = self.model.make_coin_query(query)
        utxo_list = cq.get_result()
        value_list = [asset.get_colorvalue(utxo) for utxo in utxo_list]
        if len(value_list) == 0:
            return 0
        else:
            return SimpleColorValue.sum(value_list).get_value()

    def get_available_balance(self, asset):
        return self._get_balance(asset, {"spent": False})
    
    def get_total_balance(self, asset):
        return self._get_balance(asset, {"spent": False, 
                                        "include_unconfirmed": True})

    def get_unconfirmed_balance(self, asset):
        return self._get_balance(asset, {"spent": False, 
                                        "only_unconfirmed": True})
    

    def get_history(self, asset):
        """Returns the history of an asset for all addresses of that color
        in this wallet
        """
        # update everything first
        self.get_available_balance(asset)
        return self.model.get_history_for_asset(asset)

########NEW FILE########
__FILENAME__ = wallet_model
"""
wallet_model.py

Wallet Model: part of Wallet MVC structure

Model provides facilities for working with addresses, coins and asset
definitions, but it doesn't implement high-level operations
(those are implemented in controller).
"""

from collections import defaultdict

from asset import AssetDefinitionManager
from color import ColoredCoinContext
from coloredcoinlib import ColorSet, toposorted
from txdb import NaiveTxDb, TrustingTxDb, VerifiedTxDb
from txcons import TransactionSpecTransformer
from coindb import CoinQuery, CoinManager
from utxo_fetcher import SimpleUTXOFetcher
from coloredcoinlib import BlockchainState
from ngcccbase.services.chroma import ChromaBlockchainState
from ngcccbase.services.helloblock import HelloBlockInterface
from txhistory import TxHistory


class CoinQueryFactory(object):
    """Object that creates Queries, which in turn query the UTXO store.
    """
    def __init__(self, model, config):
        """Given a wallet <model> and a config <config>,
        create a query factory.
        """
        self.model = model

    def make_query(self, query):
        """Create a CoinQuery from query <query>. Queries are dicts with:
        color_set - color associated with this query
        """
        query = query.copy()
        color_set = query.get('color_set')
        if not color_set:
            if 'color_id_set' in query:
                color_set = ColorSet.from_color_ids(
                    self.model.get_color_map(), query['color_id_set'])
            elif 'asset' in query:
                color_set = query['asset'].get_color_set()
            else:
                raise Exception('color set is not specified')
        if 'spent' not in query:
            query['spent'] = False
        return CoinQuery(self.model, color_set, query)


class WalletModel(object):
    """Represents a colored-coin wallet
    """
    def __init__(self, config, store_conn):
        """Creates a new wallet given a configuration <config>
        """
        self.store_conn = store_conn  # hackish!
        self.testnet = config.get('testnet', False)
        self.init_blockchain_state(config)
        self.init_tx_db(config)
        self.init_utxo_fetcher(config)
        self.ccc = ColoredCoinContext(config, 
                                      self.blockchain_state)
        self.ass_def_man = AssetDefinitionManager(self.ccc.colormap, config)
        self.init_wallet_address_manager(config)
        self.coin_query_factory = CoinQueryFactory(self, config)
        self.coin_man = CoinManager(self, config)
        self.tx_spec_transformer = TransactionSpecTransformer(self, config)
        self.tx_history = TxHistory(self)

    def init_wallet_address_manager(self, config):
        if config.get('bip0032'):
            from bip0032 import HDWalletAddressManager
            self.address_man = HDWalletAddressManager(self.ccc.colormap, config)
        else:
            from deterministic import DWalletAddressManager
            self.address_man = DWalletAddressManager(self.ccc.colormap, config)
            
    def init_tx_db(self, config):
        if self.testnet:
            self.txdb = NaiveTxDb(self, config)
        else:
            #hb_interface = HelloBlockInterface(self.testnet)
            #self.txdb = TrustingTxDb(self, config,
            #                         hb_interface.get_tx_confirmations)
            self.txdb = VerifiedTxDb(self, config)

    def init_utxo_fetcher(self, config):
        self.utxo_fetcher = SimpleUTXOFetcher(
            self, config.get('utxo_fetcher', {}))

    def init_blockchain_state(self, config):
        thin = config.get('thin', True)
        if thin and not config.get('use_bitcoind', False):
            chromanode_url = config.get('chromanode_url', None)
            if not chromanode_url:
                if self.testnet:
                    chromanode_url = "http://chromanode-tn.bitcontracts.org"
                else:
                    chromanode_url = "http://chromanode.bitcontracts.org"
            self.blockchain_state = ChromaBlockchainState(
                chromanode_url,
                self.testnet)
        else:
            self.blockchain_state = BlockchainState.from_url(
                None, self.testnet)

        if not thin and not self.testnet:
            try:
                # try fetching transaction from the second block of
                # the bitcoin blockchain to see whether txindex works
                self.blockchain_state.bitcoind.getrawtransaction(
                    "9b0fc92260312ce44e74ef369f5c66bbb85848f2eddd5"
                    "a7a1cde251e54ccfdd5")
            except Exception as e:
                # use Electrum to request transactions
                self.blockchain_state = EnhancedBlockchainState(
                    "electrum.cafebitcoin.com", 50001)

    def get_blockchain_state(self):
        return self.blockchain_state

    def get_tx_db(self):
        """Access method for transaction data store.
        """
        return self.txdb

    def is_testnet(self):
        """Returns True if testnet mode is enabled.
        """
        return self.testnet

    def transform_tx_spec(self, tx_spec, target_spec_kind):
        """Pass-through for TransactionSpecTransformer's transform
        """
        return self.tx_spec_transformer.transform(tx_spec, target_spec_kind)

    def get_coin_query_factory(self):
        """Access Method for CoinQueryFactory
        """
        return self.coin_query_factory

    def make_coin_query(self, params):
        """Pass-through for CoinQueryFactory's make_query
        """
        return self.coin_query_factory.make_query(params)

    def get_asset_definition_manager(self):
        """Access Method for asset definition manager
        """
        return self.ass_def_man

    def get_address_manager(self):
        """Access method for address manager
        """
        return self.address_man

    def get_coin_manager(self):
        """Access method for coin manager
        """
        return self.coin_man

    def get_history_for_asset(self, asset):
        """Returns the history of how an address got its coins.
        """
        history = []
        address_lookup = {
            a.get_address(): 1 for a in
            self.address_man.get_addresses_for_color_set(
                asset.get_color_set())}

        for color in asset.color_set.color_id_set:
            colordef = self.get_color_def(color)
            color_transactions = self.ccc.cdstore.get_all(color)
            transaction_lookup = {}
            color_record = defaultdict(list)
            for row in color_transactions:
                txhash, outindex, colorvalue, other = row
                mempool = False
                if not transaction_lookup.get(txhash):
                    tx = self.ccc.blockchain_state.get_tx(txhash)
                    blockhash, x = self.ccc.blockchain_state.get_tx_blockhash(
                        txhash)
                    if blockhash:
                        height = self.ccc.blockchain_state.get_block_height(
                            blockhash)
                    else:
                        height = -1
                        mempool = True
                    transaction_lookup[txhash] = (tx, height)
                tx, height = transaction_lookup[txhash]
                output = tx.outputs[outindex]
                address = self.ccc.raw_to_address(output.raw_address)

                if address_lookup.get(address):
                    color_record[txhash].append({
                        'txhash': txhash,
                        'address': address,
                        'value': colorvalue,
                        'height': height,
                        'outindex': outindex,
                        'inindex': -1,
                        'mempool': mempool,
                        })

            # check the inputs
            seen_hashes = {}
            for txhash, tup in transaction_lookup.items():
                tx, height = tup
                mempool = height == -1
                for input_index, input in enumerate(tx.inputs):
                    inhash = input.prevout.hash
                    in_outindex = input.prevout.n
                    intx = self.ccc.blockchain_state.get_tx(inhash)
                    in_raw = intx.outputs[in_outindex]
                    address = self.ccc.raw_to_address(in_raw.raw_address)

                    # find the transaction that corresponds to this input
                    transaction = color_record.get(inhash)
                    if not transaction:
                        continue

                    # find the output transaction corresponding to this input
                    #  index and record it as being spent
                    for item in transaction:
                        if item['outindex'] == in_outindex:
                            color_record[txhash].append({
                                'txhash': txhash,
                                'address': address,
                                'value': -item['value'],
                                'height': height,
                                'inindex': input_index,
                                'outindex': -1,
                                'mempool': mempool,
                                })
                            break

            for txhash, color_record_transaction in color_record.items():
                for item in color_record_transaction:
                    value = item['value']
                    if value < 0:
                        item['action'] = 'sent'
                        item['value'] = -int(value)
                    elif txhash == colordef.genesis['txhash']:
                        item['action'] = 'issued'
                        item['value'] = int(value)
                    else:
                        item['action'] = 'received'
                        item['value'] = int(value)
                    history.append(item)

        def dependent_txs(txhash):
            """all transactions from current block this transaction
            directly depends on"""
            dependent_txhashes = []
            tx, height = transaction_lookup[txhash]
            for inp in tx.inputs:
                if inp.prevout.hash in transaction_lookup:
                    dependent_txhashes.append(inp.prevout.hash)
            return dependent_txhashes

        sorted_txhash_list = toposorted(transaction_lookup.keys(),
                                                 dependent_txs)
        txhash_position = {txhash:i for i, txhash
                           in enumerate(sorted_txhash_list)}

        def compare(a,b):
            """order in which we get back the history
            #1 - whether or not it's a mempool transaction
            #2 - height of the block the transaction is in
            #3 - whatever transaction is least dependent within a block
            #4 - whether we're sending or receiving
            #4 - outindex within a transaction/inindex within a transaction
            """
            return a['mempool'] - b['mempool'] \
                or a['height'] - b['height'] \
                or txhash_position[a['txhash']] - txhash_position[b['txhash']] \
                or a['outindex'] - b['outindex'] \
                or a['inindex'] - b['inindex']

        return sorted(history, cmp=compare)

    def get_coin_manager(self):
        return self.coin_man

    def get_color_map(self):
        """Access method for ColoredCoinContext's colormap
        """
        return self.ccc.colormap

    def get_color_def(self, color):
        return self.ccc.colormap.get_color_def(color)

########NEW FILE########
__FILENAME__ = run
#!/usr/bin/env python

import json
import sys
import web

from coloredcoinlib import BlockchainState, ColorDefinition


blockchainstate = BlockchainState.from_url(None, True)

urls = (
    '/tx', 'Tx',
    '/prefetch', 'Prefetch',
)


class ErrorThrowingRequestProcessor:
    def require(self, data, key, message):
        value = data.get(key)
        if not value:
            raise web.HTTPError("400 Bad request", 
                                {"content-type": "text/plain"},
                                message)


class Tx(ErrorThrowingRequestProcessor):
    def POST(self):
        # data is sent in as json
        data = json.loads(web.data())
        self.require(data, 'txhash', "TX requires txhash")
        txhash = data.get('txhash')
        return blockchainstate.get_raw(txhash)


class Prefetch(ErrorThrowingRequestProcessor):
    def POST(self):
        # data is sent in as json
        data = json.loads(web.data())
        self.require(data, 'txhash', "Prefetch requires txhash")
        self.require(data, 'output_set', "Prefetch requires output_set")
        self.require(data, 'color_desc', "Prefetch requires color_desc")
        txhash = data.get('txhash')
        output_set = data.get('output_set')
        color_desc = data.get('color_desc')
        limit = data.get('limit')

        # note the id doesn't actually matter we need to add it so
        #  we have a valid color definition
        color_def = ColorDefinition.from_color_desc(9999, color_desc)

        # gather all the transactions and return them
        tx_lookup = {}

        def process(current_txhash, current_outindex):
            """For any tx out, process the colorvalues of the affecting
            inputs first and then scan that tx.
            """
            if limit and len(tx_lookup) > limit:
                return
            if tx_lookup.get(current_txhash):
                return
            current_tx = blockchainstate.get_tx(current_txhash)
            if not current_tx:
                return
            tx_lookup[current_txhash] = blockchainstate.get_raw(current_txhash)

            # note a genesis tx will simply have 0 affecting inputs
            inputs = set()
            inputs = inputs.union(
                color_def.get_affecting_inputs(current_tx,
                                               [current_outindex]))
            for i in inputs:
                process(i.prevout.hash, i.prevout.n)

        for oi in output_set:
            process(txhash, oi)
        return tx_lookup


if __name__ == "__main__":
    app = web.application(urls, globals())
    app.run()

########NEW FILE########
__FILENAME__ = assetspage
import json
from PyQt4 import QtCore, QtGui, uic

from wallet import wallet
from tablemodel import TableModel, ProxyModel


class AddAssetDialog(QtGui.QDialog):
    def __init__(self, parent, data=None):
        QtGui.QDialog.__init__(self, parent)
        uic.loadUi(uic.getUiPath('addassetdialog.ui'), self)

        for wname in ['edtMoniker', 'edtColorDesc', 'edtUnit']:
            def clearBackground(event, wname=wname):
                getattr(self, wname).setStyleSheet('')
                QtGui.QLineEdit.focusInEvent(getattr(self, wname), event)
            getattr(self, wname).focusInEvent = clearBackground

        data = data or {}
        self.edtMoniker.setText(data.get('moniker', ''))
        self.edtColorDesc.setText(data.get('color_desc', ''))
        self.edtUnit.setText(data.get('unit', ''))
        self.btnBox.setFocus()

    def isValid(self):
        moniker = self.edtMoniker.text()
        a = bool(moniker)
        if a and moniker in wallet.get_all_monikers():
            QtGui.QMessageBox.warning(
                self, 'Already exists!',
                "Moniker <b>%s</b> already exists!" % moniker,
                QtGui.QMessageBox.Ok)
            a = False
        if not a:
            self.edtMoniker.setStyleSheet('background:#FF8080')

        b = bool(self.edtColorDesc.text())
        if not b:
            self.edtColorDesc.setStyleSheet('background:#FF8080')

        c = str(self.edtUnit.text()).isdigit()
        if not c:
            self.edtUnit.setStyleSheet('background:#FF8080')

        return all([a, b, c])

    def accept(self):
        if self.isValid():
            QtGui.QDialog.accept(self)

    def get_data(self):
        return {
            'moniker': str(self.edtMoniker.text()),
            'color_desc': str(self.edtColorDesc.text()),
            'unit': int(self.edtUnit.text()),
        }


class IssueCoinsDialog(QtGui.QDialog):
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)
        uic.loadUi(uic.getUiPath('issuedialog.ui'), self)

        self.cbScheme.addItem('epobc')
        self.cbScheme.addItem('obc')

        for wname in ['edtMoniker', 'edtUnits', 'edtAtoms']:
            def clearBackground(event, wname=wname):
                getattr(self, wname).setStyleSheet('')
                QtGui.QLineEdit.focusInEvent(getattr(self, wname), event)
            getattr(self, wname).focusInEvent = clearBackground

        self.edtUnits.textChanged.connect(self.changeTotalBTC)
        self.edtAtoms.textChanged.connect(self.changeTotalBTC)

        self.availableBTC = wallet.get_available_balance('bitcoin')
        self.lblTotalBTC.setToolTip('Available: %s bitcoin' % \
            wallet.get_asset_definition('bitcoin').format_value(self.availableBTC))

    def changeTotalBTC(self):
        amount = self.edtUnits.text().toInt()
        units = self.edtAtoms.text().toInt()
        if amount[1] and units[1]:
            need = amount[0] * units[0]
            text = '%s bitcoin' % \
                wallet.get_asset_definition('bitcoin').format_value(need)
            if need > self.availableBTC:
                text = '<font color="#FF3838">%s</font>' % text
            self.lblTotalBTC.setText(text)

    def isValid(self):
        moniker = self.edtMoniker.text()
        a = bool(moniker)
        if a and moniker in wallet.get_all_monikers():
            QtGui.QMessageBox.warning(
                self, 'Already exists!',
                "Moniker <b>%s</b> already exists!" % moniker,
                QtGui.QMessageBox.Ok)
            a = False
        if not a:
            self.edtMoniker.setStyleSheet('background:#FF8080')

        b = self.edtUnits.text().toInt()
        if not b[1]:
            self.edtUnits.setStyleSheet('background:#FF8080')

        c = self.edtAtoms.text().toInt()
        if not c[1]:
            self.edtAtoms.setStyleSheet('background:#FF8080')

        d = False
        if b[1] and c[1] and b[0]*c[0] <= self.availableBTC:
            d = True

        return all([a, b, c, d])

    def accept(self):
        if self.isValid():
            QtGui.QDialog.accept(self)

    def get_data(self):
        return {
            'moniker': str(self.edtMoniker.text()),
            'coloring_scheme': str(self.cbScheme.currentText()),
            'units': self.edtUnits.text().toInt()[0],
            'atoms': self.edtAtoms.text().toInt()[0],
        }


class AssetTableModel(TableModel):
    _columns = ['Moniker', 'Color set', 'Unit']
    _alignment = [
        QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
    ]


class AssetProxyModel(ProxyModel):
    pass


class AssetsPage(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        uic.loadUi(uic.getUiPath('assetspage.ui'), self)

        self.model = AssetTableModel(self)
        self.proxyModel = AssetProxyModel(self)
        self.proxyModel.setSourceModel(self.model)
        self.proxyModel.setDynamicSortFilter(True)
        self.proxyModel.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.proxyModel.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.tableView.setModel(self.proxyModel)
        self.tableView.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.tableView.horizontalHeader().setResizeMode(
            0, QtGui.QHeaderView.Stretch)
        self.tableView.horizontalHeader().setResizeMode(
            1, QtGui.QHeaderView.ResizeToContents)
        self.tableView.horizontalHeader().setResizeMode(
            2, QtGui.QHeaderView.ResizeToContents)

        self.btnAddNewAsset.clicked.connect(self.btnAddNewAssetClicked)
        self.btnAddExistingAsset.clicked.connect(self.btnAddExistingAssetClicked)
        self.btnImportAssetFromJSON.clicked.connect(self.btnImportAssetFromJSONClicked)

    def update(self):
        self.model.removeRows(0, self.model.rowCount())
        for asset in wallet.get_all_asset():
            self.model.addRow(
                [asset['monikers'][0], asset['color_set'][0], asset['unit']])

    def contextMenuEvent(self, event):
        selected = self.tableView.selectedIndexes()
        if not selected:
            return
        actions = [
            self.actionCopyMoniker,
            self.actionCopyColorSet,
            self.actionCopyUnit,
            self.actionCopyAsJSON,
            self.actionShowAddresses,
        ]
        menu = QtGui.QMenu()
        for action in actions:
            menu.addAction(action)
        result = menu.exec_(event.globalPos())
        if result is None or result not in actions:
            return
        if actions.index(result) in [0, 1, 2]:
            index = selected[actions.index(result)]
            QtGui.QApplication.clipboard().setText(
                self.proxyModel.data(index).toString())
        elif actions.index(result) == 3:
            moniker = str(self.proxyModel.data(selected[0]).toString())
            asset = wallet.get_asset_definition(moniker)
            QtGui.QApplication.clipboard().setText(
                json.dumps(asset.get_data()))
        elif actions.index(result) == 4:
            window = self.parentWidget().parentWidget().parentWidget()
            window.gotoReceivePage()
            window.receivepage.setMonikerFilter(
                self.proxyModel.data(selected[0]).toString())

    def selectRowByMoniker(self, moniker):
        moniker = QtCore.QString(moniker)
        for row in xrange(self.proxyModel.rowCount()):
            index = self.proxyModel.index(row, 0)
            if self.proxyModel.data(index).toString() == moniker:
                self.tableView.selectRow(row)
                break

    def btnAddNewAssetClicked(self):
        dialog = IssueCoinsDialog(self)
        if dialog.exec_():
            data = dialog.get_data()
            wallet.issue(data)
            self.update()
            self.selectRowByMoniker(data['moniker'])
            self.parent().parent().parent().update()

    def btnAddExistingAssetClicked(self, data=None):
        dialog = AddAssetDialog(self, data)
        if dialog.exec_():
            data = dialog.get_data()
            wallet.add_asset(data)
            self.update()
            self.selectRowByMoniker(data['moniker'])
            self.parent().parent().parent().update()

    def btnImportAssetFromJSONClicked(self):
        text, ok = QtGui.QInputDialog.getText(self, "Import asset from JSON", "JSON: ")
        if ok:
            try:
                data = json.loads(str(text))
                self.btnAddExistingAssetClicked({
                    'moniker': str(data['monikers'][0]),
                    'color_desc': str(data['color_set'][0]),
                    'unit': str(data['unit']),
                })
            except Exception, e:
                QtGui.QMessageBox.critical(self,
                    '', str(e), QtGui.QMessageBox.Ok)

########NEW FILE########
__FILENAME__ = historypage
from PyQt4 import QtCore, QtGui, uic

from wallet import wallet
from tablemodel import TableModel

class HistoryTableModel(TableModel):
    _columns = ['Time', 'Operation', 'Amount', 'Asset', 'Address']
    _alignment = [
        QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
    ]

class HistoryPage(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        uic.loadUi(uic.getUiPath('historypage.ui'), self)
        
        self.model = HistoryTableModel(self)
        self.tableView.setModel(self.model)

        self.tableView.horizontalHeader().setResizeMode(
            0, QtGui.QHeaderView.Stretch)
        for i in range(4):
            self.tableView.horizontalHeader().setResizeMode(
                i + 1, QtGui.QHeaderView.ResizeToContents)

    def update(self):
        self.model.removeRows(0, self.model.rowCount())
        tx_history = wallet.model.tx_history
        for ent in tx_history.get_all_entries():
            datetime = QtCore.QDateTime.fromTime_t(ent.txtime)
            datetime_str = datetime.toString(QtCore.Qt.DefaultLocaleShortDate)
            if (ent.txtype == 'send') or (ent.txtype == 'receive'):
                for tgt in ent.get_targets():
                    asset = tgt.get_asset()
                    moniker = asset.get_monikers()[0]
                    value_prefix = "-" if ent.txtype == 'send' else '+'
                    self.model.addRow([datetime_str, ent.txtype, 
                                       value_prefix + tgt.get_formatted_value(),
                                       moniker, tgt.get_address()])
            elif ent.txtype == 'trade':
                print ent.get_in_values()
                print ent.get_out_values()
                for val in ent.get_in_values():
                    asset = val.get_asset()
                    moniker = asset.get_monikers()[0]
                    print [datetime_str, ent.txtype, 
                                       "+" + val.get_formatted_value(),
                                       moniker, '']
                    self.model.addRow([datetime_str, ent.txtype, 
                                       "+" + val.get_formatted_value(),
                                       moniker, ''])
                for val in ent.get_out_values():
                    asset = val.get_asset()
                    moniker = asset.get_monikers()[0]
                    print [datetime_str, ent.txtype, 
                                       "-" + val.get_formatted_value(),
                                       moniker, '']
                    self.model.addRow([datetime_str, ent.txtype, 
                                       "-" + val.get_formatted_value(),
                                       moniker, ''])
            else:
                self.model.addRow([datetime_str, ent.txtype, 
                                   '', '', ''])

########NEW FILE########
__FILENAME__ = overviewpage
from PyQt4 import QtCore, QtGui, uic

from wallet import wallet


class OverviewPage(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)

        layout1 = QtGui.QVBoxLayout(self)
        layout1.setMargin(0)

        self.scrollArea = QtGui.QScrollArea(self)
        layout1.addWidget(self.scrollArea)
        self.scrollArea.setLineWidth(1)
        self.scrollArea.setWidgetResizable(True)

    def update(self):
        allowTextSelection = (
            QtCore.Qt.LinksAccessibleByMouse |
            QtCore.Qt.TextSelectableByKeyboard |
            QtCore.Qt.TextSelectableByMouse)

        self.scrollAreaContents = QtGui.QWidget()
        self.scrollArea.setWidget(self.scrollAreaContents)
        self.scrollAreaLayout = QtGui.QVBoxLayout(self.scrollAreaContents)

        hbox = QtGui.QHBoxLayout()
        hbox.addItem(QtGui.QSpacerItem(20, 0))
        hbox.setStretch(0, 1)
        updateButton = QtGui.QPushButton('Update', self.scrollAreaContents)
        updateButton.clicked.connect(self.updateButtonClicked)
        hbox.addWidget(updateButton)
        self.scrollAreaLayout.addLayout(hbox)

        for moniker in wallet.get_all_monikers():
            asset = wallet.get_asset_definition(moniker)
            address = wallet.get_some_address(asset)
            total_balance = wallet.get_total_balance(asset)
            unconfirmed_balance = wallet.get_unconfirmed_balance(asset)

            groupBox = QtGui.QGroupBox(moniker, self.scrollAreaContents)
            layout = QtGui.QFormLayout(groupBox)

            label = QtGui.QLabel(groupBox)
            label.setText('Balance:')
            layout.setWidget(0, QtGui.QFormLayout.LabelRole, label)

            balance_text = asset.format_value(total_balance)
            if not (unconfirmed_balance == 0):
                balance_text += " (%s unconfirmed, %s available)" % \
                    (asset.format_value(unconfirmed_balance),
                     asset.format_value(wallet.get_available_balance(asset)))

            label = QtGui.QLabel(groupBox)
            label.setTextInteractionFlags(allowTextSelection)
            label.setCursor(QtGui.QCursor(QtCore.Qt.IBeamCursor))
            label.setText(balance_text)
            layout.setWidget(0, QtGui.QFormLayout.FieldRole, label)

            label = QtGui.QLabel(groupBox)
            label.setText('Address:')
            layout.setWidget(1, QtGui.QFormLayout.LabelRole, label)

            label = QtGui.QLabel(groupBox)
            label.setTextInteractionFlags(allowTextSelection)
            label.setCursor(QtGui.QCursor(QtCore.Qt.IBeamCursor))
            label.setText(address)
            layout.setWidget(1, QtGui.QFormLayout.FieldRole, label)

            self.scrollAreaLayout.addWidget(groupBox)

        self.scrollAreaLayout.addItem(QtGui.QSpacerItem(20, 0))
        self.scrollAreaLayout.setStretch(self.scrollAreaLayout.count()-1, 1)

    def updateButtonClicked(self):
        self.parent().parent().parent().update()

########NEW FILE########
__FILENAME__ = qtui
from PyQt4 import QtCore, QtGui, uic

import os
import sys
import signal

from overviewpage import OverviewPage
from sendcoinspage import SendcoinsPage
from assetspage import AssetsPage
from receivepage import ReceivePage
from tradepage import TradePage
from historypage import HistoryPage

from wallet import wallet

try:
    main_file = os.path.abspath(sys.modules['__main__'].__file__)
except AttributeError:
    main_file = sys.executable
ui_path = os.path.join(os.path.dirname(main_file), 'ui', 'forms')

def getUiPath(ui_name):
    return os.path.join(ui_path, ui_name)

uic.getUiPath = getUiPath


class Application(QtGui.QApplication):
    def __init__(self):
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        QtGui.QApplication.__init__(self, [])

class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        uic.loadUi(uic.getUiPath('ngccc.ui'), self)

        self.overviewpage = OverviewPage(self)
        self.stackedWidget.addWidget(self.overviewpage)
        self.sendcoinspage = SendcoinsPage(self)
        self.stackedWidget.addWidget(self.sendcoinspage)
        self.assetspage = AssetsPage(self)
        self.stackedWidget.addWidget(self.assetspage)
        self.receivepage = ReceivePage(self)
        self.stackedWidget.addWidget(self.receivepage)
        self.historypage = HistoryPage(self)
        self.stackedWidget.addWidget(self.historypage)
        self.tradepage = TradePage(self)
        self.stackedWidget.addWidget(self.tradepage)

        self.bindActions()

        self.gotoOverviewPage()

        self.utxo_timer = QtCore.QTimer()
        self.utxo_timer.timeout.connect(self.update_utxo_fetcher)
        self.utxo_timer.start(2500)
        wallet.async_utxo_fetcher.start_thread()

    def update_utxo_fetcher(self):
        got_updates = wallet.async_utxo_fetcher.update()
        if got_updates:
            self.currentPage.update()        

    def bindActions(self):
        self.actionRescan.triggered.connect(self.update)
        self.actionExit.triggered.connect(
            lambda: QtCore.QCoreApplication.instance().exit(0))

        self.toolbarActionGroup = QtGui.QActionGroup(self)

        self.toolbarActionGroup.addAction(self.actionGotoOverview)
        self.actionGotoOverview.triggered.connect(self.gotoOverviewPage)

        self.toolbarActionGroup.addAction(self.actionGotoSendcoins)
        self.actionGotoSendcoins.triggered.connect(self.gotoSendcoinsPage)

        self.toolbarActionGroup.addAction(self.actionGotoAssets)
        self.actionGotoAssets.triggered.connect(self.gotoAssetsPage)

        self.toolbarActionGroup.addAction(self.actionGotoReceive)
        self.actionGotoReceive.triggered.connect(self.gotoReceivePage)

        self.toolbarActionGroup.addAction(self.actionGotoHistory)
        self.actionGotoHistory.triggered.connect(self.gotoHistoryPage)

        self.toolbarActionGroup.addAction(self.actionP2PTrade)
        self.actionP2PTrade.triggered.connect(self.gotoP2PTradePage)

    def update(self):
        wallet.scan()
        self.currentPage.update()

    def setPage(self, page):
        page.update()
        self.stackedWidget.setCurrentWidget(page)
        self.currentPage = page

    def gotoOverviewPage(self):
        self.actionGotoOverview.setChecked(True)
        self.setPage(self.overviewpage)

    def gotoSendcoinsPage(self):
        self.actionGotoSendcoins.setChecked(True)
        self.setPage(self.sendcoinspage)

    def gotoAssetsPage(self):
        self.actionGotoAssets.setChecked(True)
        self.setPage(self.assetspage)

    def gotoReceivePage(self):
        self.actionGotoReceive.setChecked(True)
        self.setPage(self.receivepage)

    def gotoHistoryPage(self):
        self.actionGotoHistory.setChecked(True)
        self.setPage(self.historypage)

    def gotoP2PTradePage(self):
        self.actionP2PTrade.setChecked(True)
        self.setPage(self.tradepage)


class QtUI(object):
    def __init__(self):
        global wallet
        app = Application()
        window = MainWindow()
        window.move(QtGui.QApplication.desktop().screen().rect().center()
                    - window.rect().center())
        window.show()
        retcode = app.exec_()
        wallet.stop_all()
        sys.exit(retcode)

########NEW FILE########
__FILENAME__ = receivepage
from PyQt4 import QtCore, QtGui, uic

from wallet import wallet
from tablemodel import TableModel, ProxyModel


class AddressTableModel(TableModel):
    _columns = ['Moniker', 'Address', 'Received']
    _alignment = [
        QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
    ]


class AddressProxyModel(ProxyModel):
    pass


class NewAddressDialog(QtGui.QDialog):
    def __init__(self, moniker, parent):
        QtGui.QDialog.__init__(self, parent)
        uic.loadUi(uic.getUiPath('newaddressdialog.ui'), self)

        monikers = wallet.get_all_monikers()
        self.cbMoniker.addItems(monikers)
        if moniker in monikers:
            self.cbMoniker.setCurrentIndex(monikers.index(moniker))

    def get_data(self):
        return {
            'moniker': str(self.cbMoniker.currentText()),
        }


class ReceivePage(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        uic.loadUi(uic.getUiPath('receivepage.ui'), self)

        self.model = AddressTableModel(self)
        self.proxyModel = AddressProxyModel(self)
        self.proxyModel.setSourceModel(self.model)
        self.proxyModel.setDynamicSortFilter(True)
        self.proxyModel.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.proxyModel.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.tableView.setModel(self.proxyModel)
        self.tableView.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.tableView.horizontalHeader().setResizeMode(
            0, QtGui.QHeaderView.Stretch)
        self.tableView.horizontalHeader().setResizeMode(
            1, QtGui.QHeaderView.ResizeToContents)

        self.cbMoniker.activated.connect(
            lambda *args: self.setMonikerFilter(self.cbMoniker.currentText()))
        self.btnNew.clicked.connect(self.btnNewClicked)
        self.btnCopy.clicked.connect(self.btnCopyClicked)
        self.tableView.selectionModel().selectionChanged.connect(
            self.tableViewSelectionChanged)

    def update(self):
        self.model.removeRows(0, self.model.rowCount())
        for moniker in wallet.get_all_monikers():
            asset = wallet.get_asset_definition(moniker)
            for row in wallet.get_received_by_address(asset):
                self.model.addRow([moniker, row['color_address'], asset.format_value(row['value'])])

        moniker = self.cbMoniker.currentText()
        monikers = [''] + wallet.get_all_monikers()
        self.cbMoniker.clear()
        self.cbMoniker.addItems(monikers)
        if moniker in monikers:
            self.cbMoniker.setCurrentIndex(monikers.index(moniker))
        self.setMonikerFilter(self.cbMoniker.currentText())

    def contextMenuEvent(self, event):
        selected = self.tableView.selectedIndexes()
        if not selected:
            return

        if str(self.proxyModel.data(selected[0]).toString()) == 'bitcoin':
            actions = [
                self.actionCopyAddress,
                self.actionCopyColor,
            ]
        else:
            actions = [
                self.actionCopyAddress,
                self.actionCopyBitcoinAddress,
                self.actionCopyColor,
            ]

        menu = QtGui.QMenu()
        for action in actions:
            menu.addAction(action)
        result = menu.exec_(event.globalPos())
        if result is None or result not in actions:
            return

        if result == self.actionCopyAddress:
            text = self.proxyModel.data(selected[1]).toString()
        if result == self.actionCopyBitcoinAddress:
            text = self.proxyModel.data(selected[1]).toString().split('@')[1]
        elif result == self.actionCopyColor:
            text = self.proxyModel.data(selected[0]).toString()

        QtGui.QApplication.clipboard().setText(text)

    def setMonikerFilter(self, moniker):
        index = self.cbMoniker.findText(moniker)
        if index == -1:
            return
        if moniker != self.cbMoniker.currentText():
            self.cbMoniker.setCurrentIndex(index)
        self.proxyModel.setFilterKeyColumn(0)
        self.proxyModel.setFilterFixedString(moniker)

    def btnNewClicked(self):
        moniker = None
        selected = self.tableView.selectedIndexes()
        if selected:
            moniker = str(self.proxyModel.data(selected[0]).toString())
        dialog = NewAddressDialog(moniker, self)
        if dialog.exec_():
            moniker = dialog.get_data()['moniker']
            addr = wallet.get_new_address(moniker)
            self.parent().parent().parent().update()
            for row in xrange(self.proxyModel.rowCount()):
                index = self.proxyModel.index(row, 1)
                if str(self.proxyModel.data(index).toString()) == addr:
                    self.tableView.selectRow(row)
                    break

    def btnCopyClicked(self):
        selected = self.tableView.selectedIndexes()
        if selected:
            address = str(self.proxyModel.data(selected[1]).toString())
            QtGui.QApplication.clipboard().setText(address)

    def tableViewSelectionChanged(self, selected, deselected):
        if len(selected):
            self.tableView.selectRow(selected.indexes()[0].row())
            self.btnCopy.setEnabled(True)
        else:
            self.btnCopy.setEnabled(False)

########NEW FILE########
__FILENAME__ = sendcoinspage
import collections

from PyQt4 import QtGui, uic

from wallet import wallet


class SendcoinsEntry(QtGui.QFrame):
    def __init__(self, page):
        QtGui.QFrame.__init__(self)
        uic.loadUi(uic.getUiPath('sendcoinsentry.ui'), self)
        self.page = page

        for wname in ['edtAddress', 'edtAmount']:
            def clearBackground(event, wname=wname):
                widget = getattr(self, wname)
                widget.setStyleSheet('')
                widget.__class__.focusInEvent(widget, event)
            getattr(self, wname).focusInEvent = clearBackground

        self.cbMoniker.activated.connect(self.updateAvailableBalance)
        self.btnPaste.clicked.connect(self.btnPasteClicked)
        self.btnDelete.clicked.connect(self.btnDeleteClicked)

        self.update()

    def update(self):
        monikers = wallet.get_all_monikers()
        monikers.remove('bitcoin')
        monikers = ['bitcoin'] + monikers
        comboList = self.cbMoniker
        currentMoniker = str(comboList.currentText())
        comboList.clear()
        comboList.addItems(monikers)
        if currentMoniker and currentMoniker in monikers:
            comboList.setCurrentIndex(monikers.index(currentMoniker))
        self.updateAvailableBalance()

    def updateAvailableBalance(self):
        moniker = str(self.cbMoniker.currentText())
        if moniker:
            asset = wallet.get_asset_definition(moniker)
            balance = wallet.get_available_balance(moniker)
            self.edtAmount.setMaximum(balance)
            self.lblAvailaleBalance.setText(
                '%s %s' % (asset.format_value(balance), moniker))

    def btnPasteClicked(self):
        self.edtAddress.setText(QtGui.QApplication.clipboard().text())

    def btnDeleteClicked(self):
        self.close()
        self.page.entries.takeAt(self.page.entries.indexOf(self))
        self.page.entries.itemAt(0).widget().btnDelete.setEnabled(
            self.page.entries.count() > 1)

    def edtAddressValidate(self):
        valid = True
        if len(str(self.edtAddress.text())) < 30:
            valid = False
            self.edtAddress.setStyleSheet('background:#FF8080')
        else:
            self.edtAddress.setStyleSheet('')
        return valid

    def edtAmountValidate(self):
        valid = True
        if self.edtAmount.value() == 0:
            valid = False
            self.edtAmount.setStyleSheet('background:#FF8080')
        else:
            self.edtAmount.setStyleSheet('')
        return valid

    def isValid(self):
        return all([self.edtAddressValidate(), self.edtAmountValidate()])

    def getData(self):
        moniker = str(self.cbMoniker.currentText())
        asset = wallet.get_asset_definition(moniker)
        value = asset.parse_value(str(self.edtAmount.value()))
        return {
            'address': str(self.edtAddress.text()),
            'value':  value,
            'moniker': moniker,
        }


class SendcoinsPage(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        uic.loadUi(uic.getUiPath('sendcoinspage.ui'), self)

        self.btnAddRecipient.clicked.connect(self.btnAddRecipientClicked)
        self.btnClearAll.clicked.connect(self.btnClearAllClicked)
        self.btnSend.clicked.connect(self.btnSendClicked)

        self.btnAddRecipientClicked()

    def update(self):
        for i in xrange(self.entries.count()):
            self.entries.itemAt(i).widget().update()

    def btnAddRecipientClicked(self):
        self.entries.addWidget(SendcoinsEntry(self))
        self.entries.itemAt(0).widget().btnDelete.setEnabled(
            self.entries.count() > 1)

    def btnClearAllClicked(self):
        while True:
            layout = self.entries.takeAt(0)
            if layout is None:
                break
            layout.widget().close()
        self.btnAddRecipientClicked()

    def btnSendClicked(self):
        entries = [self.entries.itemAt(i).widget()
                    for i in xrange(self.entries.count())]
        if not all([entry.isValid() for entry in entries]):
            return
        data = [entry.getData() for entry in entries]
        message = 'Are you sure you want to send'
        for recipient in data:
            asset = wallet.get_asset_definition(recipient['moniker'])
            value = asset.format_value(recipient['value'])
            message += '<br><b>{value} {moniker}</b> to {address}'.format(**{
                'value': value,
                'moniker': 'BTC' if recipient['moniker'] == 'bitcoin' \
                    else recipient['moniker'],
                'address': recipient['address'],
            })
        message += '?'
        retval = QtGui.QMessageBox.question(
            self, 'Confirm send coins',
            message,
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.Cancel,
            QtGui.QMessageBox.Cancel)
        if retval != QtGui.QMessageBox.Yes:
            return
        # check value exceeds balance
        currency = collections.defaultdict(float)
        for recipient in data:
            currency[recipient['moniker']] += recipient['value']
        for moniker, value in currency.items():
            if value > wallet.get_available_balance(moniker):
                QtGui.QMessageBox.warning(
                    self, 'Send coins',
                    'The amount for <b>%s</b> exceeds your available balance.' % moniker,
                    QtGui.QMessageBox.Ok)
                return
        wallet.send_coins(data)
        self.parent().parent().parent().update()

########NEW FILE########
__FILENAME__ = tablemodel
from PyQt4 import QtCore, QtGui


class TableModel(QtCore.QAbstractTableModel):
    _columns = None
    _alignment = None

    def __init__(self, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self._data = []

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._columns)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.isValid():
            if role == QtCore.Qt.TextAlignmentRole:
                return QtCore.QVariant(self._alignment[index.column()])
            if role == QtCore.Qt.DisplayRole:
                return QtCore.QVariant(self._data[index.row()][index.column()])

        return QtCore.QVariant()

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal \
                and role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant(self._columns[section])

        return QtCore.QVariant()

    def addRow(self, row):
        index = len(self._data)
        self.beginInsertRows(QtCore.QModelIndex(), index, index)
        self._data.append(row)
        self.endInsertRows()

    def removeRows(self, row, count, parent=None):
        self.beginRemoveRows(QtCore.QModelIndex(), row, row+count-1)
        for _ in range(row, row+count):
            self._data.pop(row)
        self.endRemoveRows()


class ProxyModel(QtGui.QSortFilterProxyModel):
    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.isValid() and role == QtCore.Qt.BackgroundRole:
            if index.row() % 2 == 1:
                color = QtGui.QColor(243, 243, 243)
            else:
                color = QtGui.QColor(255, 255, 255)
            return QtCore.QVariant(color)
        return QtGui.QSortFilterProxyModel.data(self, index, role)

########NEW FILE########
__FILENAME__ = tradepage
from PyQt4 import QtCore, QtGui, uic

from wallet import wallet
from tablemodel import TableModel, ProxyModel

import logging


class OffersTableModel(TableModel):
    _columns = ['Price', 'Quantity', 'Total', 'MyOffer']
    _alignment = [
        QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
        0,
    ]


class OffersProxyModel(ProxyModel):
    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.BackgroundRole and index.isValid():
            oid = str(self.data(self.index(index.row(), 3)).toString())
            if oid in wallet.p2p_agent.my_offers:
                return QtCore.QVariant(QtGui.QColor(200, 200, 200))
        return ProxyModel.data(self, index, role)


class TradePage(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        uic.loadUi(uic.getUiPath('tradepage.ui'), self)
        self.logger = logging.getLogger('ngcccbase.ui.trade')

        wallet.p2ptrade_init()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_agent)
        self.timer.start(2500)

        self.modelBuy = OffersTableModel(self)
        self.proxyModelBuy = OffersProxyModel(self)
        self.proxyModelBuy.setSourceModel(self.modelBuy)
        self.proxyModelBuy.setDynamicSortFilter(True)
        self.proxyModelBuy.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.proxyModelBuy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.tvBuy.setModel(self.proxyModelBuy)
        self.tvBuy.hideColumn(3)
        self.tvBuy.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.tvBuy.horizontalHeader().setResizeMode(
            0, QtGui.QHeaderView.Stretch)
        self.tvBuy.horizontalHeader().setResizeMode(
            1, QtGui.QHeaderView.ResizeToContents)

        self.modelSell = OffersTableModel(self)
        self.proxyModelSell = OffersProxyModel(self)
        self.proxyModelSell.setSourceModel(self.modelSell)
        self.proxyModelSell.setDynamicSortFilter(True)
        self.proxyModelSell.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.proxyModelSell.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.tvSell.setModel(self.proxyModelSell)
        self.tvSell.hideColumn(3)
        self.tvSell.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.tvSell.horizontalHeader().setResizeMode(
            0, QtGui.QHeaderView.Stretch)
        self.tvSell.horizontalHeader().setResizeMode(
            1, QtGui.QHeaderView.ResizeToContents)

        self.cbMoniker.currentIndexChanged.connect(self.update_balance)

        for wname in ['edtBuyQuantity', 'edtBuyPrice', 'edtSellQuantity', 'edtSellPrice']:
            def clearBackground(event, wname=wname):
                getattr(self, wname).setStyleSheet('')
                QtGui.QLineEdit.focusInEvent(getattr(self, wname), event)
            getattr(self, wname).focusInEvent = clearBackground

        self.edtBuyQuantity.textChanged.connect(self.lblBuyTotalChange)
        self.edtBuyPrice.textChanged.connect(self.lblBuyTotalChange)
        self.btnBuy.clicked.connect(self.btnBuyClicked)
        self.tvBuy.doubleClicked.connect(self.tvBuyDoubleClicked)

        self.edtSellQuantity.textChanged.connect(self.lblSellTotalChange)
        self.edtSellPrice.textChanged.connect(self.lblSellTotalChange)
        self.btnSell.clicked.connect(self.btnSellClicked)
        self.tvSell.doubleClicked.connect(self.tvSellDoubleClicked)

        self.need_update_offers = False
        def set_need_update_offers(data):
            self.need_update_offers = True
        wallet.p2p_agent.set_event_handler('offers_updated', 
                                           set_need_update_offers)

        def information_about_offer(offer, action, buysell_text):
            A, B = offer.get_data()['A'], offer.get_data()['B']
            bitcoin = wallet.get_asset_definition('bitcoin')
            sell_offer = B['color_spec'] == ''
            asset = wallet.get_asset_definition_by_color_set(
                (A if sell_offer else B)['color_spec'])
            value = (A if sell_offer else B)['value']
            total = (B if sell_offer else A)['value']
            text = '{action} {type} {value} {moniker} @{price} btc ea. (Total: {total} btc)'.format(**{
                'action': action,
                'type': buysell_text[sell_offer],
                'value': asset.format_value(value),
                'moniker': asset.get_monikers()[0],
                'price': bitcoin.format_value(total*asset.unit/value),
                'total': bitcoin.format_value(total),
            })
            self.add_log_entry(text)

        wallet.p2p_agent.set_event_handler(
            'register_my_offer', 
            lambda offer: information_about_offer(offer, 'Created', ("bid", "ask")))
        wallet.p2p_agent.set_event_handler(
            'cancel_my_offer',   
            lambda offer: information_about_offer(offer, 'Canceled', ("bid", "ask")))
        wallet.p2p_agent.set_event_handler(
            'make_ep', 
            lambda ep: information_about_offer(ep.my_offer, 'In progress', 
                                               ('buying', 'selling')))
        wallet.p2p_agent.set_event_handler(
            'accept_ep', 
            lambda eps: information_about_offer(eps[1].my_offer, 'In progress', 
                                                ('buying', 'selling')))
        def on_trade_complete(ep):
            information_about_offer(ep.my_offer, 
                                    'Trade complete:', ('bought', 'sold'))
            self.update_balance()
        wallet.p2p_agent.set_event_handler('trade_complete', on_trade_complete)

    def add_log_entry(self, text):
        self.listEventLog.addItem(text)
        
    def update(self):
        monikers = wallet.get_all_monikers()
        monikers.remove('bitcoin')
        comboList = self.cbMoniker
        currentMoniker = str(comboList.currentText())
        comboList.clear()
        comboList.addItems(monikers)
        if currentMoniker and currentMoniker in monikers:
            comboList.setCurrentIndex(monikers.index(currentMoniker))

    def update_agent(self):
        moniker = str(self.cbMoniker.currentText())
        if moniker == '':
            return
        wallet.p2p_agent.update()
        if self.need_update_offers:
            self.update_offers()

    def update_offers(self):
        self.need_update_offers = False
        moniker = str(self.cbMoniker.currentText())
        if moniker == '':
            return
        bitcoin = wallet.get_asset_definition('bitcoin')
        asset = wallet.get_asset_definition(moniker)
        color_desc = asset.get_color_set().color_desc_list[0]

        selected_oids = [None, None]
        viewsList = [
            [0, self.tvBuy,  self.proxyModelBuy],
            [1, self.tvSell, self.proxyModelSell],
        ]
        for i, view, proxy in viewsList:
            selected = view.selectedIndexes()
            if selected:
                index = proxy.index(selected[0].row(), 3)
                selected_oids[i] = str(proxy.data(index).toString())

        self.modelBuy.removeRows(0, self.modelBuy.rowCount())
        self.modelSell.removeRows(0, self.modelSell.rowCount())
        offers = wallet.p2p_agent.their_offers.items() + wallet.p2p_agent.my_offers.items()
        for i, item in enumerate(offers):
            oid, offer = item
            data = offer.get_data()
            if data['A'].get('color_spec') == color_desc:
                value = data['A']['value']
                total = data['B']['value']
                price = int(total*asset.unit/float(value))
                self.modelSell.addRow([
                    bitcoin.format_value(price),
                    asset.format_value(value),
                    bitcoin.format_value(total),
                    oid,
                ])
            if data['B'].get('color_spec') == color_desc:
                value = data['B']['value']
                total = data['A']['value']
                price = int(total*asset.unit/float(value))
                self.modelBuy.addRow([
                    bitcoin.format_value(price),
                    asset.format_value(value),
                    bitcoin.format_value(total),
                    oid,
                ])

        for i, view, proxy in viewsList:
            for row in xrange(proxy.rowCount()):
                oid = str(proxy.data(proxy.index(row, 3)).toString())
                if oid == selected_oids[i]:
                    view.selectRow(row)

    def update_balance(self):
        moniker = str(self.cbMoniker.currentText())
        if moniker == '':
            return

        asset = wallet.get_asset_definition('bitcoin')
        value = asset.format_value(wallet.get_available_balance(asset))
        self.lblBuy.setText('<b>Buy</b> %s' % moniker)
        self.lblBuyAvail.setText('(Available: %s bitcoin)' % value)

        asset = wallet.get_asset_definition(moniker)
        value = asset.format_value(wallet.get_available_balance(asset))
        self.lblSell.setText('<b>Sell</b> %s' % moniker)
        self.lblSellAvail.setText('(Available: %s %s)' % (value, moniker))

        self.update_offers()

    def lblBuyTotalChange(self):
        self.lblBuyTotal.setText('')
        if self.edtBuyQuantity.text().toDouble()[1] \
                and self.edtBuyPrice.text().toDouble()[1]:
            value = self.edtBuyQuantity.text().toDouble()[0]
            bitcoin = wallet.get_asset_definition('bitcoin')
            price = bitcoin.parse_value(
                self.edtBuyPrice.text().toDouble()[0])
            total = value*price
            self.lblBuyTotal.setText('%s bitcoin' % bitcoin.format_value(total))

    def btnBuyClicked(self):
        valid = True
        if not self.edtBuyQuantity.text().toDouble()[1]:
            self.edtBuyQuantity.setStyleSheet('background:#FF8080')
            valid = False
        if not self.edtBuyPrice.text().toDouble()[1]:
            self.edtBuyPrice.setStyleSheet('background:#FF8080')
            valid = False
        if not valid:
            return
        moniker = str(self.cbMoniker.currentText())
        asset = wallet.get_asset_definition(moniker)
        value = self.edtBuyQuantity.text().toDouble()[0]
        bitcoin = wallet.get_asset_definition('bitcoin')
        price = self.edtBuyPrice.text().toDouble()[0]
        delta = wallet.get_available_balance(bitcoin) - value*bitcoin.parse_value(price)
        if delta < 0:
            message = 'The transaction amount exceeds available balance by %s bitcoin' % \
                bitcoin.format_value(-delta)
            QtGui.QMessageBox.critical(self, '', message, QtGui.QMessageBox.Ok)
            return
        offer = wallet.p2ptrade_make_offer(False, {
            'moniker': moniker,
            'value': value,
            'price': price,
        })
        wallet.p2p_agent.register_my_offer(offer)
        self.update_offers()
        self.edtBuyQuantity.setText('')
        self.edtBuyPrice.setText('')

    def tvBuyDoubleClicked(self):
        """click on bids, colored coins will be sold"""
        selected = self.tvBuy.selectedIndexes()
        if not selected:
            return
        index = self.proxyModelBuy.index(selected[0].row(), 3)
        oid = str(self.proxyModelBuy.data(index).toString())
        if oid in wallet.p2p_agent.their_offers:
            offer = wallet.p2p_agent.their_offers[oid]
            moniker = str(self.cbMoniker.currentText())
            asset = wallet.get_asset_definition(moniker)
            if wallet.get_available_balance(asset) < offer.get_data()['B']['value']:
                self.logger.warn("%s avail <  %s required", 
                                 wallet.get_available_balance(asset),
                                 offer.get_data()['A']['value'])
                msg = "Not enough coins: %s %s needed, %s available" % \
                    (str(self.proxyModelBuy.data(selected[2]).toString()), 
                     moniker,
                     asset.format_value(wallet.get_available_balance(asset)))
                QtGui.QMessageBox.warning(self, '', msg,
                    QtGui.QMessageBox.Ok)
                return
            message = "About to <u>sell</u> <b>{value}</b> {moniker} @ <b>{course}</b> \
bitcoin each. <br> (Total: <b>{total}</b> bitcoin)".format(**{
                'value': self.proxyModelBuy.data(selected[1]).toString(),
                'moniker': str(self.cbMoniker.currentText()),
                'course': self.proxyModelBuy.data(selected[0]).toString(),
                'total': self.proxyModelBuy.data(selected[2]).toString(),
            })
            retval = QtGui.QMessageBox.question(
                self, "Confirm buying asset", message,
                QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel,
                QtGui.QMessageBox.Cancel)
            if retval != QtGui.QMessageBox.Ok:
                return
            new_offer = wallet.p2ptrade_make_mirror_offer(offer)
            wallet.p2p_agent.register_my_offer(new_offer)
        else:
            offer = wallet.p2p_agent.my_offers[oid]
            wallet.p2p_agent.cancel_my_offer(offer)
        self.update_offers()

    def lblSellTotalChange(self):
        self.lblSellTotal.setText('')
        if self.edtSellQuantity.text().toDouble()[1] \
                and self.edtSellPrice.text().toDouble()[1]:
            value = self.edtSellQuantity.text().toDouble()[0]
            bitcoin = wallet.get_asset_definition('bitcoin')
            price = bitcoin.parse_value(
                self.edtSellPrice.text().toDouble()[0])
            total = value*price
            self.lblSellTotal.setText('%s bitcoin' % bitcoin.format_value(total))

    def btnSellClicked(self):
        valid = True
        if not self.edtSellQuantity.text().toDouble()[1]:
            self.edtSellQuantity.setStyleSheet('background:#FF8080')
            valid = False
        if not self.edtSellPrice.text().toDouble()[1]:
            self.edtSellPrice.setStyleSheet('background:#FF8080')
            valid = False
        if not valid:
            return
        moniker = str(self.cbMoniker.currentText())
        asset = wallet.get_asset_definition(moniker)
        value = self.edtSellQuantity.text().toDouble()[0]
        bitcoin = wallet.get_asset_definition('bitcoin')
        price = self.edtSellPrice.text().toDouble()[0]
        delta = wallet.get_available_balance(asset) - asset.parse_value(value)
        if delta < 0:
            message = 'The transaction amount exceeds available balance by %s %s' % \
                (asset.format_value(-delta), moniker)
            QtGui.QMessageBox.critical(self, '', message, QtGui.QMessageBox.Ok)
            return
        offer = wallet.p2ptrade_make_offer(True, {
            'moniker': moniker,
            'value': value,
            'price': price,
        })
        wallet.p2p_agent.register_my_offer(offer)
        self.update_offers()
        self.edtSellQuantity.setText('')
        self.edtSellPrice.setText('')

    def tvSellDoubleClicked(self):
        """"Click on asks, colored coins are going to be bought"""
        selected = self.tvSell.selectedIndexes()
        if not selected:
            return
        index = self.proxyModelSell.index(selected[0].row(), 3)
        oid = str(self.proxyModelSell.data(index).toString())
        if oid in wallet.p2p_agent.their_offers:
            offer = wallet.p2p_agent.their_offers[oid]
            moniker = str(self.cbMoniker.currentText())
            bitcoin = wallet.get_asset_definition('bitcoin')
            if wallet.get_available_balance(bitcoin) < offer.get_data()['B']['value']:
                self.logger.warn("Not enough money: %s <  %s",
                                 wallet.get_available_balance(bitcoin),
                                 offer.get_data()['B']['value'])
                msg = "Not enough money: %s bitcoins needed, %s available" % \
                    (self.proxyModelSell.data(selected[2]).toString(), 
                     bitcoin.format_value(wallet.get_available_balance(bitcoin)))
                QtGui.QMessageBox.warning(self, '', msg,
                                          QtGui.QMessageBox.Ok)
                return
            message = "About to <u>buy</u> <b>{value}</b> {moniker} @ <b>{course}</b> \
bitcoin each. <br> (Total: <b>{total}</b> bitcoin)".format(**{
                'value': self.proxyModelSell.data(selected[1]).toString(),
                'moniker': moniker,
                'course': self.proxyModelSell.data(selected[0]).toString(),
                'total': self.proxyModelSell.data(selected[2]).toString(),
            })
            retval = QtGui.QMessageBox.question(
                self, "Confirm buy coins", message,
                QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel,
                QtGui.QMessageBox.Cancel)
            if retval != QtGui.QMessageBox.Ok:
                return
            new_offer = wallet.p2ptrade_make_mirror_offer(offer)
            wallet.p2p_agent.register_my_offer(new_offer)
        else:
            offer = wallet.p2p_agent.my_offers[oid]
            wallet.p2p_agent.cancel_my_offer(offer)
        self.update_offers()

########NEW FILE########
__FILENAME__ = wallet
from ngcccbase.pwallet import PersistentWallet
from ngcccbase.wallet_controller import WalletController
from ngcccbase.asset import AssetDefinition

from ngcccbase.p2ptrade.ewctrl import EWalletController
from ngcccbase.p2ptrade.agent import EAgent
from ngcccbase.p2ptrade.comm import HTTPComm, ThreadedComm
from ngcccbase.p2ptrade.protocol_objects import MyEOffer

from ngcccbase.utxo_fetcher import AsyncUTXOFetcher

import argparse


class Wallet(object):
    thread_comm = None

    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--wallet", dest="wallet_path")
        parser.add_argument("--testnet", action='store_true')
        parsed_args = vars(parser.parse_args())

        self.wallet = PersistentWallet(parsed_args.get('wallet_path'),
                                       parsed_args.get('testnet'))
        self.wallet.init_model()
        self.model = self.wallet.get_model()
        self.controller = WalletController(self.wallet.get_model())
        self.async_utxo_fetcher = AsyncUTXOFetcher(
            self.model, self.wallet.wallet_config.get('utxo_fetcher', {}))

    def get_asset_definition(self, moniker):
        if isinstance(moniker, AssetDefinition):
            return moniker
        adm = self.wallet.get_model().get_asset_definition_manager()
        asset = adm.get_asset_by_moniker(moniker)
        if asset:
            return asset
        else:
            raise Exception("asset not found")

    def get_asset_definition_by_color_set(self, color_set):
        adm = self.wallet.get_model().get_asset_definition_manager()
        for asset in adm.get_all_assets():
            if color_set in asset.get_color_set().get_data():
                return asset
        raise Exception("asset not found")

    def add_asset(self, params):
        self.controller.add_asset_definition({
            "monikers": [params['moniker']],
            "color_set": [params['color_desc']],
            "unit": params['unit']
        })
        if len(self.get_all_addresses(params['moniker'])) == 0:
            self.get_new_address(params['moniker'])

    def get_all_asset(self):
        return self.wallet.wallet_config['asset_definitions']

    def issue(self, params):
        self.controller.issue_coins(
            params['moniker'], params['coloring_scheme'],
            params['units'], params['atoms'])
        if len(self.get_all_addresses(params['moniker'])) == 0:
            self.get_new_address(params['moniker'])

    def get_all_monikers(self):
        monikers = [asset.get_monikers()[0] for asset in
            self.model.get_asset_definition_manager().get_all_assets()]
        monikers.remove('bitcoin')
        monikers = ['bitcoin'] + monikers
        return monikers

    def get_available_balance(self, color):
        return self.controller.get_available_balance(
            self.get_asset_definition(color))

    def get_total_balance(self, color):
        return self.controller.get_total_balance(
            self.get_asset_definition(color))

    def get_unconfirmed_balance(self, color):
        return self.controller.get_unconfirmed_balance(
            self.get_asset_definition(color))

    def get_all_addresses(self, color):
        return [addr.get_color_address() for addr in
            self.controller.get_all_addresses(self.get_asset_definition(color))]

    def get_received_by_address(self, color):
        asset = self.get_asset_definition(color)
        return self.controller.get_received_by_address(asset)

    def get_some_address(self, color):
        wam = self.model.get_address_manager()
        cs = self.get_asset_definition(color).get_color_set()
        ar = wam.get_some_address(cs)
        return ar.get_color_address()

    def get_new_address(self, color):
        return self.controller. \
            get_new_address(self.get_asset_definition(color)).get_color_address()

    def scan(self):
        self.controller.scan_utxos()

    def send_coins(self, items):
        if isinstance(items, dict):
            items = [items]
        for item in items:
            self.controller.send_coins(
                item['asset'] if 'asset' in item \
                    else self.get_asset_definition(item['moniker']),
                [item['address']],
                [item['value']])

    def p2ptrade_init(self):
        ewctrl = EWalletController(self.model, self.controller)
        config = {"offer_expiry_interval": 30,
                  "ep_expiry_interval": 30}
        comm = HTTPComm(
            config, 'http://p2ptrade.btx.udoidio.info/messages')
        self.thread_comm = ThreadedComm(comm)
        self.p2p_agent = EAgent(ewctrl, config, self.thread_comm)
        self.thread_comm.start()

    def p2ptrade_stop(self):
        if self.thread_comm is not None:
            self.thread_comm.stop()

    def p2ptrade_make_offer(self, we_sell, params):
        asset = self.get_asset_definition(params['moniker'])
        value = asset.parse_value(params['value'])
        bitcoin = self.get_asset_definition('bitcoin')
        price = bitcoin.parse_value(params['price'])
        total = int(float(value)/float(asset.unit)*float(price))
        color_desc = asset.get_color_set().color_desc_list[0]
        sell_side = {"color_spec": color_desc, "value": value}
        buy_side = {"color_spec": "", "value": total}
        if we_sell:
            return MyEOffer(None, sell_side, buy_side)
        else:
            return MyEOffer(None, buy_side, sell_side)

    def p2ptrade_make_mirror_offer(self, offer):
        data = offer.get_data()
        return MyEOffer(None, data['B'], data['A'], False)

    def stop_all(self):
        self.async_utxo_fetcher.stop()
        self.p2ptrade_stop()
        if hasattr(self.model.txdb, 'vbs'):
            self.model.txdb.vbs.stop()
        

wallet = Wallet()

########NEW FILE########
