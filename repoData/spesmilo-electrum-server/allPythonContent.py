__FILENAME__ = blockchain_processor
import ast
import hashlib
from json import dumps, loads
import os
from Queue import Queue
import random
import sys
import time
import threading
import traceback
import urllib

from backends.bitcoind import deserialize
from processor import Processor, print_log
from utils import *

from storage import Storage


class BlockchainProcessor(Processor):

    def __init__(self, config, shared):
        Processor.__init__(self)

        self.mtimes = {} # monitoring
        self.shared = shared
        self.config = config
        self.up_to_date = False

        self.watch_lock = threading.Lock()
        self.watch_blocks = []
        self.watch_headers = []
        self.watched_addresses = {}

        self.history_cache = {}
        self.chunk_cache = {}
        self.cache_lock = threading.Lock()
        self.headers_data = ''
        self.headers_path = config.get('leveldb', 'path_fulltree')

        self.mempool_values = {}
        self.mempool_addresses = {}
        self.mempool_hist = {}
        self.mempool_hashes = set([])
        self.mempool_lock = threading.Lock()

        self.address_queue = Queue()

        try:
            self.test_reorgs = config.getboolean('leveldb', 'test_reorgs')   # simulate random blockchain reorgs
        except:
            self.test_reorgs = False
        self.storage = Storage(config, shared, self.test_reorgs)

        self.dblock = threading.Lock()

        self.bitcoind_url = 'http://%s:%s@%s:%s/' % (
            config.get('bitcoind', 'user'),
            config.get('bitcoind', 'password'),
            config.get('bitcoind', 'host'),
            config.get('bitcoind', 'port'))

        while True:
            try:
                self.bitcoind('getinfo')
                break
            except:
                print_log('cannot contact bitcoind...')
                time.sleep(5)
                continue

        self.sent_height = 0
        self.sent_header = None

        # catch_up headers
        self.init_headers(self.storage.height)

        threading.Timer(0, lambda: self.catch_up(sync=False)).start()
        while not shared.stopped() and not self.up_to_date:
            try:
                time.sleep(1)
            except:
                print "keyboard interrupt: stopping threads"
                shared.stop()
                sys.exit(0)

        print_log("Blockchain is up to date.")
        self.memorypool_update()
        print_log("Memory pool initialized.")

        self.timer = threading.Timer(10, self.main_iteration)
        self.timer.start()



    def mtime(self, name):
        now = time.time()
        if name != '':
            delta = now - self.now
            t = self.mtimes.get(name, 0)
            self.mtimes[name] = t + delta
        self.now = now

    def print_mtime(self):
        s = ''
        for k, v in self.mtimes.items():
            s += k+':'+"%.2f"%v+' '
        print_log(s)


    def bitcoind(self, method, params=[]):
        postdata = dumps({"method": method, 'params': params, 'id': 'jsonrpc'})
        try:
            respdata = urllib.urlopen(self.bitcoind_url, postdata).read()
        except:
            print_log("error calling bitcoind")
            traceback.print_exc(file=sys.stdout)
            self.shared.stop()

        r = loads(respdata)
        if r['error'] is not None:
            raise BaseException(r['error'])
        return r.get('result')


    def block2header(self, b):
        return {
            "block_height": b.get('height'),
            "version": b.get('version'),
            "prev_block_hash": b.get('previousblockhash'),
            "merkle_root": b.get('merkleroot'),
            "timestamp": b.get('time'),
            "bits": int(b.get('bits'), 16),
            "nonce": b.get('nonce'),
        }

    def get_header(self, height):
        block_hash = self.bitcoind('getblockhash', [height])
        b = self.bitcoind('getblock', [block_hash])
        return self.block2header(b)

    def init_headers(self, db_height):
        self.chunk_cache = {}
        self.headers_filename = os.path.join(self.headers_path, 'blockchain_headers')

        if os.path.exists(self.headers_filename):
            height = os.path.getsize(self.headers_filename)/80 - 1   # the current height
            if height > 0:
                prev_hash = self.hash_header(self.read_header(height))
            else:
                prev_hash = None
        else:
            open(self.headers_filename, 'wb').close()
            prev_hash = None
            height = -1

        if height < db_height:
            print_log("catching up missing headers:", height, db_height)

        try:
            while height < db_height:
                height = height + 1
                header = self.get_header(height)
                if height > 1:
                    assert prev_hash == header.get('prev_block_hash')
                self.write_header(header, sync=False)
                prev_hash = self.hash_header(header)
                if (height % 1000) == 0:
                    print_log("headers file:", height)
        except KeyboardInterrupt:
            self.flush_headers()
            sys.exit()

        self.flush_headers()

    def hash_header(self, header):
        return rev_hex(Hash(header_to_string(header).decode('hex')).encode('hex'))

    def read_header(self, block_height):
        if os.path.exists(self.headers_filename):
            with open(self.headers_filename, 'rb') as f:
                f.seek(block_height * 80)
                h = f.read(80)
            if len(h) == 80:
                h = header_from_string(h)
                return h

    def read_chunk(self, index):
        with open(self.headers_filename, 'rb') as f:
            f.seek(index*2016*80)
            chunk = f.read(2016*80)
        return chunk.encode('hex')

    def write_header(self, header, sync=True):
        if not self.headers_data:
            self.headers_offset = header.get('block_height')

        self.headers_data += header_to_string(header).decode('hex')
        if sync or len(self.headers_data) > 40*100:
            self.flush_headers()

        with self.cache_lock:
            chunk_index = header.get('block_height')/2016
            if self.chunk_cache.get(chunk_index):
                self.chunk_cache.pop(chunk_index)

    def pop_header(self):
        # we need to do this only if we have not flushed
        if self.headers_data:
            self.headers_data = self.headers_data[:-40]

    def flush_headers(self):
        if not self.headers_data:
            return
        with open(self.headers_filename, 'rb+') as f:
            f.seek(self.headers_offset*80)
            f.write(self.headers_data)
        self.headers_data = ''

    def get_chunk(self, i):
        # store them on disk; store the current chunk in memory
        with self.cache_lock:
            chunk = self.chunk_cache.get(i)
            if not chunk:
                chunk = self.read_chunk(i)
                self.chunk_cache[i] = chunk

        return chunk

    def get_mempool_transaction(self, txid):
        try:
            raw_tx = self.bitcoind('getrawtransaction', [txid, 0])
        except:
            return None

        vds = deserialize.BCDataStream()
        vds.write(raw_tx.decode('hex'))
        try:
            return deserialize.parse_Transaction(vds, is_coinbase=False)
        except:
            print_log("ERROR: cannot parse", txid)
            return None


    def get_history(self, addr, cache_only=False):
        with self.cache_lock:
            hist = self.history_cache.get(addr)
        if hist is not None:
            return hist
        if cache_only:
            return -1

        with self.dblock:
            try:
                hist = self.storage.get_history(addr)
                is_known = True
            except:
                print_log("error get_history")
                traceback.print_exc(file=sys.stdout)
                raise
            if hist:
                is_known = True
            else:
                hist = []
                is_known = False

        # add memory pool
        with self.mempool_lock:
            for txid, delta in self.mempool_hist.get(addr, []):
                hist.append({'tx_hash':txid, 'height':0})

        # add something to distinguish between unused and empty addresses
        if hist == [] and is_known:
            hist = ['*']

        with self.cache_lock:
            self.history_cache[addr] = hist
        return hist


    def get_unconfirmed_value(self, addr):
        v = 0
        with self.mempool_lock:
            for txid, delta in self.mempool_hist.get(addr, []):
                v += delta
        return v


    def get_status(self, addr, cache_only=False):
        tx_points = self.get_history(addr, cache_only)
        if cache_only and tx_points == -1:
            return -1

        if not tx_points:
            return None
        if tx_points == ['*']:
            return '*'
        status = ''
        for tx in tx_points:
            status += tx.get('tx_hash') + ':%d:' % tx.get('height')
        return hashlib.sha256(status).digest().encode('hex')

    def get_merkle(self, tx_hash, height):

        block_hash = self.bitcoind('getblockhash', [height])
        b = self.bitcoind('getblock', [block_hash])
        tx_list = b.get('tx')
        tx_pos = tx_list.index(tx_hash)

        merkle = map(hash_decode, tx_list)
        target_hash = hash_decode(tx_hash)
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

        return {"block_height": height, "merkle": s, "pos": tx_pos}


    def add_to_history(self, addr, tx_hash, tx_pos, tx_height):
        # keep it sorted
        s = self.serialize_item(tx_hash, tx_pos, tx_height) + 40*chr(0)
        assert len(s) == 80

        serialized_hist = self.batch_list[addr]

        l = len(serialized_hist)/80
        for i in range(l-1, -1, -1):
            item = serialized_hist[80*i:80*(i+1)]
            item_height = int(rev_hex(item[36:39].encode('hex')), 16)
            if item_height <= tx_height:
                serialized_hist = serialized_hist[0:80*(i+1)] + s + serialized_hist[80*(i+1):]
                break
        else:
            serialized_hist = s + serialized_hist

        self.batch_list[addr] = serialized_hist

        # backlink
        txo = (tx_hash + int_to_hex(tx_pos, 4)).decode('hex')
        self.batch_txio[txo] = addr






    def deserialize_block(self, block):
        txlist = block.get('tx')
        tx_hashes = []  # ordered txids
        txdict = {}     # deserialized tx
        is_coinbase = True
        for raw_tx in txlist:
            tx_hash = hash_encode(Hash(raw_tx.decode('hex')))
            vds = deserialize.BCDataStream()
            vds.write(raw_tx.decode('hex'))
            try:
                tx = deserialize.parse_Transaction(vds, is_coinbase)
            except:
                print_log("ERROR: cannot parse", tx_hash)
                continue
            tx_hashes.append(tx_hash)
            txdict[tx_hash] = tx
            is_coinbase = False
        return tx_hashes, txdict



    def import_block(self, block, block_hash, block_height, sync, revert=False):

        touched_addr = set([])

        # deserialize transactions
        tx_hashes, txdict = self.deserialize_block(block)

        # undo info
        if revert:
            undo_info = self.storage.get_undo_info(block_height)
            tx_hashes.reverse()
        else:
            undo_info = {}

        for txid in tx_hashes:  # must be ordered
            tx = txdict[txid]
            if not revert:
                undo = self.storage.import_transaction(txid, tx, block_height, touched_addr)
                undo_info[txid] = undo
            else:
                undo = undo_info.pop(txid)
                self.storage.revert_transaction(txid, tx, block_height, touched_addr, undo)

        if revert: 
            assert undo_info == {}

        # add undo info
        if not revert:
            self.storage.write_undo_info(block_height, self.bitcoind_height, undo_info)

        # add the max
        self.storage.db_undo.put('height', repr( (block_hash, block_height, self.storage.db_version) ))

        for addr in touched_addr:
            self.invalidate_cache(addr)

        self.storage.update_hashes()


    def add_request(self, session, request):
        # see if we can get if from cache. if not, add to queue
        if self.process(session, request, cache_only=True) == -1:
            self.queue.put((session, request))


    def do_subscribe(self, method, params, session):
        with self.watch_lock:
            if method == 'blockchain.numblocks.subscribe':
                if session not in self.watch_blocks:
                    self.watch_blocks.append(session)

            elif method == 'blockchain.headers.subscribe':
                if session not in self.watch_headers:
                    self.watch_headers.append(session)

            elif method == 'blockchain.address.subscribe':
                address = params[0]
                l = self.watched_addresses.get(address)
                if l is None:
                    self.watched_addresses[address] = [session]
                elif session not in l:
                    l.append(session)


    def do_unsubscribe(self, method, params, session):
        with self.watch_lock:
            if method == 'blockchain.numblocks.subscribe':
                if session in self.watch_blocks:
                    self.watch_blocks.remove(session)
            elif method == 'blockchain.headers.subscribe':
                if session in self.watch_headers:
                    self.watch_headers.remove(session)
            elif method == "blockchain.address.subscribe":
                addr = params[0]
                l = self.watched_addresses.get(addr)
                if not l:
                    return
                if session in l:
                    l.remove(session)
                if session in l:
                    print_log("error rc!!")
                    self.shared.stop()
                if l == []:
                    self.watched_addresses.pop(addr)


    def process(self, session, request, cache_only=False):
        
        message_id = request['id']
        method = request['method']
        params = request.get('params', [])
        result = None
        error = None

        if method == 'blockchain.numblocks.subscribe':
            result = self.storage.height

        elif method == 'blockchain.headers.subscribe':
            result = self.header

        elif method == 'blockchain.address.subscribe':
            try:
                address = str(params[0])
                result = self.get_status(address, cache_only)
            except BaseException, e:
                error = str(e) + ': ' + address
                print_log("error:", error)

        elif method == 'blockchain.address.get_history':
            try:
                address = str(params[0])
                result = self.get_history(address, cache_only)
            except BaseException, e:
                error = str(e) + ': ' + address
                print_log("error:", error)

        elif method == 'blockchain.address.get_mempool':
            try:
                address = str(params[0])
                result = self.get_unconfirmed_history(address, cache_only)
            except BaseException, e:
                error = str(e) + ': ' + address
                print_log("error:", error)

        elif method == 'blockchain.address.get_balance':
            try:
                address = str(params[0])
                confirmed = self.storage.get_balance(address)
                unconfirmed = self.get_unconfirmed_value(address)
                result = { 'confirmed':confirmed, 'unconfirmed':unconfirmed }
            except BaseException, e:
                error = str(e) + ': ' + address
                print_log("error:", error)

        elif method == 'blockchain.address.get_proof':
            try:
                address = str(params[0])
                result = self.storage.get_proof(address)
            except BaseException, e:
                error = str(e) + ': ' + address
                print_log("error:", error)

        elif method == 'blockchain.address.listunspent':
            try:
                address = str(params[0])
                result = self.storage.listunspent(address)
            except BaseException, e:
                error = str(e) + ': ' + address
                print_log("error:", error)

        elif method == 'blockchain.utxo.get_address':
            try:
                txid = str(params[0])
                pos = int(params[1])
                txi = (txid + int_to_hex(pos, 4)).decode('hex')
                result = self.storage.get_address(txi)
            except BaseException, e:
                error = str(e)
                print_log("error:", error, params)

        elif method == 'blockchain.block.get_header':
            if cache_only:
                result = -1
            else:
                try:
                    height = int(params[0])
                    result = self.get_header(height)
                except BaseException, e:
                    error = str(e) + ': %d' % height
                    print_log("error:", error)

        elif method == 'blockchain.block.get_chunk':
            if cache_only:
                result = -1
            else:
                try:
                    index = int(params[0])
                    result = self.get_chunk(index)
                except BaseException, e:
                    error = str(e) + ': %d' % index
                    print_log("error:", error)

        elif method == 'blockchain.transaction.broadcast':
            try:
                txo = self.bitcoind('sendrawtransaction', params)
                print_log("sent tx:", txo)
                result = txo
            except BaseException, e:
                result = str(e)  # do not send an error
                print_log("error:", result, params)

        elif method == 'blockchain.transaction.get_merkle':
            if cache_only:
                result = -1
            else:
                try:
                    tx_hash = params[0]
                    tx_height = params[1]
                    result = self.get_merkle(tx_hash, tx_height)
                except BaseException, e:
                    error = str(e) + ': ' + repr(params)
                    print_log("get_merkle error:", error)

        elif method == 'blockchain.transaction.get':
            try:
                tx_hash = params[0]
                result = self.bitcoind('getrawtransaction', [tx_hash, 0])
            except BaseException, e:
                error = str(e) + ': ' + repr(params)
                print_log("tx get error:", error)

        else:
            error = "unknown method:%s" % method

        if cache_only and result == -1:
            return -1

        if error:
            self.push_response(session, {'id': message_id, 'error': error})
        elif result != '':
            self.push_response(session, {'id': message_id, 'result': result})


    def getfullblock(self, block_hash):
        block = self.bitcoind('getblock', [block_hash])

        rawtxreq = []
        i = 0
        for txid in block['tx']:
            rawtxreq.append({
                "method": "getrawtransaction",
                "params": [txid],
                "id": i,
            })
            i += 1

        postdata = dumps(rawtxreq)
        try:
            respdata = urllib.urlopen(self.bitcoind_url, postdata).read()
        except:
            print_log("bitcoind error (getfullblock)")
            traceback.print_exc(file=sys.stdout)
            self.shared.stop()

        r = loads(respdata)
        rawtxdata = []
        for ir in r:
            if ir['error'] is not None:
                self.shared.stop()
                print_log("Error: make sure you run bitcoind with txindex=1; use -reindex if needed.")
                raise BaseException(ir['error'])
            rawtxdata.append(ir['result'])
        block['tx'] = rawtxdata
        return block

    def catch_up(self, sync=True):

        prev_root_hash = None
        while not self.shared.stopped():

            self.mtime('')

            # are we done yet?
            info = self.bitcoind('getinfo')
            self.bitcoind_height = info.get('blocks')
            bitcoind_block_hash = self.bitcoind('getblockhash', [self.bitcoind_height])
            if self.storage.last_hash == bitcoind_block_hash:
                self.up_to_date = True
                break

            # not done..
            self.up_to_date = False
            next_block_hash = self.bitcoind('getblockhash', [self.storage.height + 1])
            next_block = self.getfullblock(next_block_hash)
            self.mtime('daemon')

            # fixme: this is unsafe, if we revert when the undo info is not yet written
            revert = (random.randint(1, 100) == 1) if self.test_reorgs else False

            if (next_block.get('previousblockhash') == self.storage.last_hash) and not revert:

                prev_root_hash = self.storage.get_root_hash()

                self.import_block(next_block, next_block_hash, self.storage.height+1, sync)
                self.storage.height = self.storage.height + 1
                self.write_header(self.block2header(next_block), sync)
                self.storage.last_hash = next_block_hash
                self.mtime('import')
            
                if self.storage.height % 1000 == 0 and not sync:
                    t_daemon = self.mtimes.get('daemon')
                    t_import = self.mtimes.get('import')
                    print_log("catch_up: block %d (%.3fs %.3fs)" % (self.storage.height, t_daemon, t_import), self.storage.get_root_hash().encode('hex'))
                    self.mtimes['daemon'] = 0
                    self.mtimes['import'] = 0

            else:

                # revert current block
                block = self.getfullblock(self.storage.last_hash)
                print_log("blockchain reorg", self.storage.height, block.get('previousblockhash'), self.storage.last_hash)
                self.import_block(block, self.storage.last_hash, self.storage.height, sync, revert=True)
                self.pop_header()
                self.flush_headers()

                self.storage.height -= 1

                # read previous header from disk
                self.header = self.read_header(self.storage.height)
                self.storage.last_hash = self.hash_header(self.header)

                if prev_root_hash:
                    assert prev_root_hash == self.storage.get_root_hash()
                    prev_root_hash = None


        self.header = self.block2header(self.bitcoind('getblock', [self.storage.last_hash]))
        self.header['utxo_root'] = self.storage.get_root_hash().encode('hex')

        if self.shared.stopped(): 
            print_log( "closing database" )
            self.storage.close()


    def memorypool_update(self):
        mempool_hashes = set(self.bitcoind('getrawmempool'))
        touched_addresses = set([])

        # get new transactions
        new_tx = {}
        for tx_hash in mempool_hashes:
            if tx_hash in self.mempool_hashes:
                continue

            tx = self.get_mempool_transaction(tx_hash)
            if not tx:
                continue

            new_tx[tx_hash] = tx
            self.mempool_hashes.add(tx_hash)

        # remove older entries from mempool_hashes
        self.mempool_hashes = mempool_hashes


        # check all tx outputs
        for tx_hash, tx in new_tx.items():
            mpa = self.mempool_addresses.get(tx_hash, {})
            out_values = []
            for x in tx.get('outputs'):
                out_values.append( x['value'] )

                addr = x.get('address')
                if not addr:
                    continue
                v = mpa.get(addr,0)
                v += x['value']
                mpa[addr] = v
                touched_addresses.add(addr)

            self.mempool_addresses[tx_hash] = mpa
            self.mempool_values[tx_hash] = out_values

        # check all inputs
        for tx_hash, tx in new_tx.items():
            mpa = self.mempool_addresses.get(tx_hash, {})
            for x in tx.get('inputs'):
                # we assume that the input address can be parsed by deserialize(); this is true for Electrum transactions
                addr = x.get('address')
                if not addr:
                    continue

                v = self.mempool_values.get(x.get('prevout_hash'))
                if v:
                    value = v[ x.get('prevout_n')]
                else:
                    txi = (x.get('prevout_hash') + int_to_hex(x.get('prevout_n'), 4)).decode('hex')
                    try:
                        value = self.storage.get_utxo_value(addr,txi)
                    except:
                        print_log("utxo not in database; postponing mempool update")
                        return

                v = mpa.get(addr,0)
                v -= value
                mpa[addr] = v
                touched_addresses.add(addr)

            self.mempool_addresses[tx_hash] = mpa


        # remove deprecated entries from mempool_addresses
        for tx_hash, addresses in self.mempool_addresses.items():
            if tx_hash not in self.mempool_hashes:
                self.mempool_addresses.pop(tx_hash)
                self.mempool_values.pop(tx_hash)
                for addr in addresses:
                    touched_addresses.add(addr)

        # rebuild mempool histories
        new_mempool_hist = {}
        for tx_hash, addresses in self.mempool_addresses.items():
            for addr, delta in addresses.items():
                h = new_mempool_hist.get(addr, [])
                if tx_hash not in h:
                    h.append((tx_hash, delta))
                new_mempool_hist[addr] = h

        with self.mempool_lock:
            self.mempool_hist = new_mempool_hist

        # invalidate cache for touched addresses
        for addr in touched_addresses:
            self.invalidate_cache(addr)


    def invalidate_cache(self, address):
        with self.cache_lock:
            if address in self.history_cache:
                print_log("cache: invalidating", address)
                self.history_cache.pop(address)

        with self.watch_lock:
            sessions = self.watched_addresses.get(address)

        if sessions:
            # TODO: update cache here. if new value equals cached value, do not send notification
            self.address_queue.put((address,sessions))

    
    def close(self):
        self.timer.join()
        print_log("Closing database...")
        self.storage.close()
        print_log("Database is closed")


    def main_iteration(self):
        if self.shared.stopped():
            print_log("Stopping timer")
            return

        with self.dblock:
            t1 = time.time()
            self.catch_up()
            t2 = time.time()

        self.memorypool_update()

        if self.sent_height != self.storage.height:
            self.sent_height = self.storage.height
            for session in self.watch_blocks:
                self.push_response(session, {
                        'id': None,
                        'method': 'blockchain.numblocks.subscribe',
                        'params': [self.storage.height],
                        })

        if self.sent_header != self.header:
            print_log("blockchain: %d (%.3fs)" % (self.storage.height, t2 - t1))
            self.sent_header = self.header
            for session in self.watch_headers:
                self.push_response(session, {
                        'id': None,
                        'method': 'blockchain.headers.subscribe',
                        'params': [self.header],
                        })

        while True:
            try:
                addr, sessions = self.address_queue.get(False)
            except:
                break

            status = self.get_status(addr)
            for session in sessions:
                self.push_response(session, {
                        'id': None,
                        'method': 'blockchain.address.subscribe',
                        'params': [addr, status],
                        })

        # next iteration 
        self.timer = threading.Timer(10, self.main_iteration)
        self.timer.start()


########NEW FILE########
__FILENAME__ = deserialize
# this code comes from ABE. it can probably be simplified
#
#

import mmap
import string
import struct
import types

from utils import *


class SerializationError(Exception):
    """Thrown when there's a problem deserializing or serializing."""


class BCDataStream(object):
    """Workalike python implementation of Bitcoin's CDataStream class."""
    def __init__(self):
        self.input = None
        self.read_cursor = 0

    def clear(self):
        self.input = None
        self.read_cursor = 0

    def write(self, bytes):    # Initialize with string of bytes
        if self.input is None:
            self.input = bytes
        else:
            self.input += bytes

    def map_file(self, file, start):    # Initialize with bytes from file
        self.input = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
        self.read_cursor = start

    def seek_file(self, position):
        self.read_cursor = position

    def close_file(self):
        self.input.close()

    def read_string(self):
        # Strings are encoded depending on length:
        # 0 to 252 :    1-byte-length followed by bytes (if any)
        # 253 to 65,535 : byte'253' 2-byte-length followed by bytes
        # 65,536 to 4,294,967,295 : byte '254' 4-byte-length followed by bytes
        # ... and the Bitcoin client is coded to understand:
        # greater than 4,294,967,295 : byte '255' 8-byte-length followed by bytes of string
        # ... but I don't think it actually handles any strings that big.
        if self.input is None:
            raise SerializationError("call write(bytes) before trying to deserialize")

        try:
            length = self.read_compact_size()
        except IndexError:
            raise SerializationError("attempt to read past end of buffer")

        return self.read_bytes(length)

    def write_string(self, string):
        # Length-encoded as with read-string
        self.write_compact_size(len(string))
        self.write(string)

    def read_bytes(self, length):
        try:
            result = self.input[self.read_cursor:self.read_cursor+length]
            self.read_cursor += length
            return result
        except IndexError:
            raise SerializationError("attempt to read past end of buffer")

        return ''

    def read_boolean(self):
        return self.read_bytes(1)[0] != chr(0)

    def read_int16(self):
        return self._read_num('<h')

    def read_uint16(self):
        return self._read_num('<H')

    def read_int32(self):
        return self._read_num('<i')

    def read_uint32(self):
        return self._read_num('<I')

    def read_int64(self):
        return self._read_num('<q')

    def read_uint64(self):
        return self._read_num('<Q')

    def write_boolean(self, val):
        return self.write(chr(1) if val else chr(0))

    def write_int16(self, val):
        return self._write_num('<h', val)

    def write_uint16(self, val):
        return self._write_num('<H', val)

    def write_int32(self, val):
        return self._write_num('<i', val)

    def write_uint32(self, val):
        return self._write_num('<I', val)

    def write_int64(self, val):
        return self._write_num('<q', val)

    def write_uint64(self, val):
        return self._write_num('<Q', val)

    def read_compact_size(self):
        size = ord(self.input[self.read_cursor])
        self.read_cursor += 1
        if size == 253:
            size = self._read_num('<H')
        elif size == 254:
            size = self._read_num('<I')
        elif size == 255:
            size = self._read_num('<Q')
        return size

    def write_compact_size(self, size):
        if size < 0:
            raise SerializationError("attempt to write size < 0")
        elif size < 253:
            self.write(chr(size))
        elif size < 2**16:
            self.write('\xfd')
            self._write_num('<H', size)
        elif size < 2**32:
            self.write('\xfe')
            self._write_num('<I', size)
        elif size < 2**64:
            self.write('\xff')
            self._write_num('<Q', size)

    def _read_num(self, format):
        (i,) = struct.unpack_from(format, self.input, self.read_cursor)
        self.read_cursor += struct.calcsize(format)
        return i

    def _write_num(self, format, num):
        s = struct.pack(format, num)
        self.write(s)


class EnumException(Exception):
    pass


class Enumeration:
    """enum-like type

    From the Python Cookbook, downloaded from http://code.activestate.com/recipes/67107/
    """

    def __init__(self, name, enumList):
        self.__doc__ = name
        lookup = {}
        reverseLookup = {}
        i = 0
        uniqueNames = []
        uniqueValues = []
        for x in enumList:
            if isinstance(x, types.TupleType):
                x, i = x
            if not isinstance(x, types.StringType):
                raise EnumException("enum name is not a string: %r" % x)
            if not isinstance(i, types.IntType):
                raise EnumException("enum value is not an integer: %r" % i)
            if x in uniqueNames:
                raise EnumException("enum name is not unique: %r" % x)
            if i in uniqueValues:
                raise EnumException("enum value is not unique for %r" % x)
            uniqueNames.append(x)
            uniqueValues.append(i)
            lookup[x] = i
            reverseLookup[i] = x
            i = i + 1
        self.lookup = lookup
        self.reverseLookup = reverseLookup

    def __getattr__(self, attr):
        if attr not in self.lookup:
            raise AttributeError
        return self.lookup[attr]

    def whatis(self, value):
        return self.reverseLookup[value]


# This function comes from bitcointools, bct-LICENSE.txt.
def long_hex(bytes):
    return bytes.encode('hex_codec')


# This function comes from bitcointools, bct-LICENSE.txt.
def short_hex(bytes):
    t = bytes.encode('hex_codec')
    if len(t) < 11:
        return t
    return t[0:4]+"..."+t[-4:]


def parse_TxIn(vds):
    d = {}
    d['prevout_hash'] = hash_encode(vds.read_bytes(32))
    d['prevout_n'] = vds.read_uint32()
    scriptSig = vds.read_bytes(vds.read_compact_size())
    d['sequence'] = vds.read_uint32()

    if scriptSig:
        pubkeys, signatures, address = get_address_from_input_script(scriptSig)
    else:
        pubkeys = []
        signatures = []
        address = None

    d['address'] = address
    d['signatures'] = signatures

    return d


def parse_TxOut(vds, i):
    d = {}
    d['value'] = vds.read_int64()
    scriptPubKey = vds.read_bytes(vds.read_compact_size())
    d['address'] = get_address_from_output_script(scriptPubKey)
    d['raw_output_script'] = scriptPubKey.encode('hex')
    d['index'] = i
    return d


def parse_Transaction(vds, is_coinbase):
    d = {}
    start = vds.read_cursor
    d['version'] = vds.read_int32()
    n_vin = vds.read_compact_size()
    d['inputs'] = []
    for i in xrange(n_vin):
            o = parse_TxIn(vds)
            if not is_coinbase:
                    d['inputs'].append(o)
    n_vout = vds.read_compact_size()
    d['outputs'] = []
    for i in xrange(n_vout):
            o = parse_TxOut(vds, i)

            #if o['address'] == "None" and o['value']==0:
            #        print("skipping strange tx output with zero value")
            #        continue
            # if o['address'] != "None":
            d['outputs'].append(o)

    d['lockTime'] = vds.read_uint32()
    return d


opcodes = Enumeration("Opcodes", [
    ("OP_0", 0), ("OP_PUSHDATA1", 76), "OP_PUSHDATA2", "OP_PUSHDATA4", "OP_1NEGATE", "OP_RESERVED",
    "OP_1", "OP_2", "OP_3", "OP_4", "OP_5", "OP_6", "OP_7",
    "OP_8", "OP_9", "OP_10", "OP_11", "OP_12", "OP_13", "OP_14", "OP_15", "OP_16",
    "OP_NOP", "OP_VER", "OP_IF", "OP_NOTIF", "OP_VERIF", "OP_VERNOTIF", "OP_ELSE", "OP_ENDIF", "OP_VERIFY",
    "OP_RETURN", "OP_TOALTSTACK", "OP_FROMALTSTACK", "OP_2DROP", "OP_2DUP", "OP_3DUP", "OP_2OVER", "OP_2ROT", "OP_2SWAP",
    "OP_IFDUP", "OP_DEPTH", "OP_DROP", "OP_DUP", "OP_NIP", "OP_OVER", "OP_PICK", "OP_ROLL", "OP_ROT",
    "OP_SWAP", "OP_TUCK", "OP_CAT", "OP_SUBSTR", "OP_LEFT", "OP_RIGHT", "OP_SIZE", "OP_INVERT", "OP_AND",
    "OP_OR", "OP_XOR", "OP_EQUAL", "OP_EQUALVERIFY", "OP_RESERVED1", "OP_RESERVED2", "OP_1ADD", "OP_1SUB", "OP_2MUL",
    "OP_2DIV", "OP_NEGATE", "OP_ABS", "OP_NOT", "OP_0NOTEQUAL", "OP_ADD", "OP_SUB", "OP_MUL", "OP_DIV",
    "OP_MOD", "OP_LSHIFT", "OP_RSHIFT", "OP_BOOLAND", "OP_BOOLOR",
    "OP_NUMEQUAL", "OP_NUMEQUALVERIFY", "OP_NUMNOTEQUAL", "OP_LESSTHAN",
    "OP_GREATERTHAN", "OP_LESSTHANOREQUAL", "OP_GREATERTHANOREQUAL", "OP_MIN", "OP_MAX",
    "OP_WITHIN", "OP_RIPEMD160", "OP_SHA1", "OP_SHA256", "OP_HASH160",
    "OP_HASH256", "OP_CODESEPARATOR", "OP_CHECKSIG", "OP_CHECKSIGVERIFY", "OP_CHECKMULTISIG",
    "OP_CHECKMULTISIGVERIFY",
    "OP_NOP1", "OP_NOP2", "OP_NOP3", "OP_NOP4", "OP_NOP5", "OP_NOP6", "OP_NOP7", "OP_NOP8", "OP_NOP9", "OP_NOP10",
    ("OP_INVALIDOPCODE", 0xFF),
])


def script_GetOp(bytes):
    i = 0
    while i < len(bytes):
        vch = None
        opcode = ord(bytes[i])
        i += 1

        if opcode <= opcodes.OP_PUSHDATA4:
            nSize = opcode
            if opcode == opcodes.OP_PUSHDATA1:
                nSize = ord(bytes[i])
                i += 1
            elif opcode == opcodes.OP_PUSHDATA2:
                (nSize,) = struct.unpack_from('<H', bytes, i)
                i += 2
            elif opcode == opcodes.OP_PUSHDATA4:
                (nSize,) = struct.unpack_from('<I', bytes, i)
                i += 4
            if i+nSize > len(bytes):
              vch = "_INVALID_"+bytes[i:]
              i = len(bytes)
            else:
             vch = bytes[i:i+nSize]
             i += nSize

        yield (opcode, vch, i)


def script_GetOpName(opcode):
  try:
    return (opcodes.whatis(opcode)).replace("OP_", "")
  except KeyError:
    return "InvalidOp_"+str(opcode)


def decode_script(bytes):
    result = ''
    for (opcode, vch, i) in script_GetOp(bytes):
        if len(result) > 0:
            result += " "
        if opcode <= opcodes.OP_PUSHDATA4:
            result += "%d:" % (opcode,)
            result += short_hex(vch)
        else:
            result += script_GetOpName(opcode)
    return result


def match_decoded(decoded, to_match):
    if len(decoded) != len(to_match):
        return False
    for i in range(len(decoded)):
        if to_match[i] == opcodes.OP_PUSHDATA4 and decoded[i][0] <= opcodes.OP_PUSHDATA4:
            continue    # Opcodes below OP_PUSHDATA4 all just push data onto stack, and are equivalent.
        if to_match[i] != decoded[i][0]:
            return False
    return True



def get_address_from_input_script(bytes):
    try:
        decoded = [ x for x in script_GetOp(bytes) ]
    except:
        # coinbase transactions raise an exception                                                                                                                 
        return [], [], None

    # non-generated TxIn transactions push a signature
    # (seventy-something bytes) and then their public key
    # (33 or 65 bytes) onto the stack:

    match = [ opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4 ]
    if match_decoded(decoded, match):
        return None, None, public_key_to_bc_address(decoded[1][1])

    # p2sh transaction, 2 of n
    match = [ opcodes.OP_0 ]
    while len(match) < len(decoded):
        match.append(opcodes.OP_PUSHDATA4)

    if match_decoded(decoded, match):

        redeemScript = decoded[-1][1]
        num = len(match) - 2
        signatures = map(lambda x:x[1].encode('hex'), decoded[1:-1])
        dec2 = [ x for x in script_GetOp(redeemScript) ]

        # 2 of 2
        match2 = [ opcodes.OP_2, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_2, opcodes.OP_CHECKMULTISIG ]
        if match_decoded(dec2, match2):
            pubkeys = [ dec2[1][1].encode('hex'), dec2[2][1].encode('hex') ]
            return pubkeys, signatures, hash_160_to_bc_address(hash_160(redeemScript), 5)

        # 2 of 3
        match2 = [ opcodes.OP_2, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_3, opcodes.OP_CHECKMULTISIG ]
        if match_decoded(dec2, match2):
            pubkeys = [ dec2[1][1].encode('hex'), dec2[2][1].encode('hex'), dec2[3][1].encode('hex') ]
            return pubkeys, signatures, hash_160_to_bc_address(hash_160(redeemScript), 5)

    return [], [], None


def get_address_from_output_script(bytes):
    try:
        decoded = [ x for x in script_GetOp(bytes) ]
    except:
        return None

    # The Genesis Block, self-payments, and pay-by-IP-address payments look like:
    # 65 BYTES:... CHECKSIG
    match = [opcodes.OP_PUSHDATA4, opcodes.OP_CHECKSIG]
    if match_decoded(decoded, match):
        return public_key_to_bc_address(decoded[0][1])

    # coins sent to black hole
    # DUP HASH160 20 BYTES:... EQUALVERIFY CHECKSIG
    match = [opcodes.OP_DUP, opcodes.OP_HASH160, opcodes.OP_0, opcodes.OP_EQUALVERIFY, opcodes.OP_CHECKSIG]
    if match_decoded(decoded, match):
        return None

    # Pay-by-Bitcoin-address TxOuts look like:
    # DUP HASH160 20 BYTES:... EQUALVERIFY CHECKSIG
    match = [opcodes.OP_DUP, opcodes.OP_HASH160, opcodes.OP_PUSHDATA4, opcodes.OP_EQUALVERIFY, opcodes.OP_CHECKSIG]
    if match_decoded(decoded, match):
        return hash_160_to_bc_address(decoded[2][1])

    # strange tx
    match = [opcodes.OP_DUP, opcodes.OP_HASH160, opcodes.OP_PUSHDATA4, opcodes.OP_EQUALVERIFY, opcodes.OP_CHECKSIG, opcodes.OP_NOP]
    if match_decoded(decoded, match):
        return hash_160_to_bc_address(decoded[2][1])

    # p2sh
    match = [ opcodes.OP_HASH160, opcodes.OP_PUSHDATA4, opcodes.OP_EQUAL ]
    if match_decoded(decoded, match):
        addr = hash_160_to_bc_address(decoded[1][1],5)
        return addr

    return None

########NEW FILE########
__FILENAME__ = storage
import plyvel, ast, hashlib, traceback, os
from processor import print_log
from utils import *


"""
Patricia tree for hashing unspents

"""

DEBUG = 0
KEYLENGTH = 20 + 32 + 4   #56

class Storage(object):

    def __init__(self, config, shared, test_reorgs):

        self.dbpath = config.get('leveldb', 'path_fulltree')
        if not os.path.exists(self.dbpath):
            os.mkdir(self.dbpath)
        self.pruning_limit = config.getint('leveldb', 'pruning_limit')
        self.shared = shared
        self.hash_list = {}
        self.parents = {}

        self.test_reorgs = test_reorgs
        try:
            self.db_utxo = plyvel.DB(os.path.join(self.dbpath,'utxo'), create_if_missing=True, compression=None)
            self.db_addr = plyvel.DB(os.path.join(self.dbpath,'addr'), create_if_missing=True, compression=None)
            self.db_hist = plyvel.DB(os.path.join(self.dbpath,'hist'), create_if_missing=True, compression=None)
            self.db_undo = plyvel.DB(os.path.join(self.dbpath,'undo'), create_if_missing=True, compression=None)
        except:
            traceback.print_exc(file=sys.stdout)
            self.shared.stop()

        self.db_version = 3 # increase this when database needs to be updated
        try:
            self.last_hash, self.height, db_version = ast.literal_eval(self.db_undo.get('height'))
            print_log("Database version", self.db_version)
            print_log("Blockchain height", self.height)
        except:
            #traceback.print_exc(file=sys.stdout)
            print_log('initializing database')
            self.height = 0
            self.last_hash = '000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f'
            db_version = self.db_version
            # write root
            self.put_node('', {})

        # check version
        if self.db_version != db_version:
            print_log("Your database '%s' is deprecated. Please create a new database"%self.dbpath)
            self.shared.stop()
            return


        # compute root hash
        d = self.get_node('')
        self.root_hash, v = self.get_node_hash('',d,None)
        print_log("UTXO tree root hash:", self.root_hash.encode('hex'))
        print_log("Coins in database:", v)

    # convert between bitcoin addresses and 20 bytes keys used for storage. 
    def address_to_key(self, addr):
        return bc_address_to_hash_160(addr)

    def key_to_address(self, addr):
        return hash_160_to_bc_address(addr)


    def get_proof(self, addr):
        key = self.address_to_key(addr)
        i = self.db_utxo.iterator(start=key)
        k, _ = i.next()

        p = self.get_path(k) 
        p.append(k)

        out = []
        for item in p:
            v = self.db_utxo.get(item)
            out.append((item.encode('hex'), v.encode('hex')))

        return out


    def get_balance(self, addr):
        key = self.address_to_key(addr)
        i = self.db_utxo.iterator(start=key)
        k, _ = i.next()
        if not k.startswith(key): 
            return 0
        p = self.get_parent(k)
        d = self.get_node(p)
        letter = k[len(p)]
        return d[letter][1]


    def listunspent(self, addr):
        key = self.address_to_key(addr)

        out = []
        for k, v in self.db_utxo.iterator(start=key):
            if not k.startswith(key):
                break
            if len(k) == KEYLENGTH:
                txid = k[20:52].encode('hex')
                txpos = hex_to_int(k[52:56])
                h = hex_to_int(v[8:12])
                v = hex_to_int(v[0:8])
                out.append({'tx_hash': txid, 'tx_pos':txpos, 'height': h, 'value':v})

        out.sort(key=lambda x:x['height'])
        return out


    def get_history(self, addr):
        out = []

        o = self.listunspent(addr)
        for item in o:
            out.append((item['tx_hash'], item['height']))

        h = self.db_hist.get(addr)
        
        while h:
            item = h[0:80]
            h = h[80:]
            txi = item[0:32].encode('hex')
            hi = hex_to_int(item[36:40])
            txo = item[40:72].encode('hex')
            ho = hex_to_int(item[76:80])
            out.append((txi, hi))
            out.append((txo, ho))

        # sort
        out.sort(key=lambda x:x[1])

        # uniqueness
        out = set(out)

        return map(lambda x: {'tx_hash':x[0], 'height':x[1]}, out)



    def get_address(self, txi):
        return self.db_addr.get(txi)


    def get_undo_info(self, height):
        s = self.db_undo.get("undo_info_%d" % (height % 100))
        if s is None: print_log("no undo info for ", height)
        return eval(s)


    def write_undo_info(self, height, bitcoind_height, undo_info):
        if height > bitcoind_height - 100 or self.test_reorgs:
            self.db_undo.put("undo_info_%d" % (height % 100), repr(undo_info))


    def common_prefix(self, word1, word2):
        max_len = min(len(word1),len(word2))
        for i in range(max_len):
            if word2[i] != word1[i]:
                index = i
                break
        else:
            index = max_len
        return word1[0:index]


    def put_node(self, key, d, batch=None):
        k = 0
        serialized = ''
        for i in range(256):
            if chr(i) in d.keys():
                k += 1<<i
                h, v = d[chr(i)]
                if h is None: h = chr(0)*32
                vv = int_to_hex(v, 8).decode('hex')
                item = h + vv
                assert len(item) == 40
                serialized += item

        k = "0x%0.64X" % k # 32 bytes
        k = k[2:].decode('hex')
        assert len(k) == 32
        out = k + serialized
        if batch:
            batch.put(key, out)
        else:
            self.db_utxo.put(key, out) 


    def get_node(self, key):

        s = self.db_utxo.get(key)
        if s is None: 
            return 

        #print "get node", key.encode('hex'), len(key), s.encode('hex')

        k = int(s[0:32].encode('hex'), 16)
        s = s[32:]
        d = {}
        for i in range(256):
            if k % 2 == 1: 
                _hash = s[0:32]
                value = hex_to_int(s[32:40])
                d[chr(i)] = (_hash, value)
                s = s[40:]
            k = k/2

        #cache
        return d


    def add_address(self, target, value, height):
        assert len(target) == KEYLENGTH

        word = target
        key = ''
        path = [ '' ]
        i = self.db_utxo.iterator()

        while key != target:

            items = self.get_node(key)

            if word[0] in items.keys():
  
                i.seek(key + word[0])
                new_key, _ = i.next()

                if target.startswith(new_key):
                    # add value to the child node
                    key = new_key
                    word = target[len(key):]
                    if key == target:
                        break
                    else:
                        assert key not in path
                        path.append(key)
                else:
                    # prune current node and add new node
                    prefix = self.common_prefix(new_key, target)
                    index = len(prefix)

                    ## get hash and value of new_key from parent (if it's a leaf)
                    if len(new_key) == KEYLENGTH:
                        parent_key = self.get_parent(new_key)
                        parent = self.get_node(parent_key)
                        z = parent[ new_key[len(parent_key)] ]
                        self.put_node(prefix, { target[index]:(None,0), new_key[index]:z } )
                    else:
                        # if it is not a leaf, update the hash of new_key because skip_string changed
                        h, v = self.get_node_hash(new_key, self.get_node(new_key), prefix)
                        self.put_node(prefix, { target[index]:(None,0), new_key[index]:(h,v) } )

                    path.append(prefix)
                    self.parents[new_key] = prefix
                    break

            else:
                assert key in path
                items[ word[0] ] = (None,0)
                self.put_node(key,items)
                break

        # write 
        s = (int_to_hex(value, 8) + int_to_hex(height,4)).decode('hex')
        self.db_utxo.put(target, s)
        # the hash of a node is the txid
        _hash = target[20:52]
        self.update_node_hash(target, path, _hash, value)


    def update_node_hash(self, node, path, _hash, value):
        c = node
        for x in path[::-1]:
            self.parents[c] = x
            c = x

        self.hash_list[node] = (_hash, value)


    def update_hashes(self):

        nodes = {} # nodes to write

        for i in range(KEYLENGTH, -1, -1):

            for node in self.hash_list.keys():
                if len(node) != i: continue

                node_hash, node_value = self.hash_list.pop(node)

                # for each node, compute its hash, send it to the parent
                if node == '':
                    self.root_hash = node_hash
                    self.root_value = node_value
                    break

                parent = self.parents[node]

                # read parent.. do this in add_address
                d = nodes.get(parent)
                if d is None:
                    d = self.get_node(parent)
                    assert d is not None

                letter = node[len(parent)]
                assert letter in d.keys()

                if i != KEYLENGTH and node_hash is None:
                    d2 = self.get_node(node)
                    node_hash, node_value = self.get_node_hash(node, d2, parent)

                assert node_hash is not None
                # write new value
                d[letter] = (node_hash, node_value)
                nodes[parent] = d

                # iterate
                grandparent = self.parents[parent] if parent != '' else None
                parent_hash, parent_value = self.get_node_hash(parent, d, grandparent)
                self.hash_list[parent] = (parent_hash, parent_value)

        
        # batch write modified nodes 
        batch = self.db_utxo.write_batch()
        for k, v in nodes.items():
            self.put_node(k, v, batch)
        batch.write()

        # cleanup
        assert self.hash_list == {}
        self.parents = {}


    def get_node_hash(self, x, d, parent):

        # final hash
        if x != '':
            skip_string = x[len(parent)+1:]
        else:
            skip_string = ''

        d2 = sorted(d.items())
        values = map(lambda x: x[1][1], d2)
        hashes = map(lambda x: x[1][0], d2)
        value = sum( values )
        _hash = self.hash( skip_string + ''.join(hashes) )
        return _hash, value


    def get_path(self, target):
        word = target
        key = ''
        path = [ '' ]
        i = self.db_utxo.iterator(start='')

        while key != target:

            i.seek(key + word[0])
            try:
                new_key, _ = i.next()
                is_child = new_key.startswith(key + word[0])
            except StopIteration:
                is_child = False

            if is_child:
  
                if target.startswith(new_key):
                    # add value to the child node
                    key = new_key
                    word = target[len(key):]
                    if key == target:
                        break
                    else:
                        assert key not in path
                        path.append(key)
                else:
                    print_log('not in tree', self.db_utxo.get(key+word[0]), new_key.encode('hex'))
                    return False
            else:
                assert key in path
                break

        return path


    def delete_address(self, leaf):
        path = self.get_path(leaf)
        if path is False:
            print_log("addr not in tree", leaf.encode('hex'), self.key_to_address(leaf[0:20]), self.db_utxo.get(leaf))
            raise

        s = self.db_utxo.get(leaf)
        
        self.db_utxo.delete(leaf)
        if leaf in self.hash_list:
            self.hash_list.pop(leaf)

        parent = path[-1]
        letter = leaf[len(parent)]
        items = self.get_node(parent)
        items.pop(letter)

        # remove key if it has a single child
        if len(items) == 1:
            letter, v = items.items()[0]

            self.db_utxo.delete(parent)
            if parent in self.hash_list: 
                self.hash_list.pop(parent)

            # we need the exact length for the iteration
            i = self.db_utxo.iterator()
            i.seek(parent+letter)
            k, v = i.next()

            # note: k is not necessarily a leaf
            if len(k) == KEYLENGTH:
                 _hash, value = k[20:52], hex_to_int(v[0:8])
            else:
                _hash, value = None, None

            self.update_node_hash(k, path[:-1], _hash, value)

        else:
            self.put_node(parent, items)
            _hash, value = None, None
            self.update_node_hash(parent, path[:-1], _hash, value)

        return s


    def get_children(self, x):
        i = self.db_utxo.iterator()
        l = 0
        while l <256:
            i.seek(x+chr(l))
            k, v = i.next()
            if k.startswith(x+chr(l)): 
                yield k, v
                l += 1
            elif k.startswith(x): 
                yield k, v
                l = ord(k[len(x)]) + 1
            else: 
                break




    def get_parent(self, x):
        """ return parent and skip string"""
        i = self.db_utxo.iterator()
        for j in range(len(x)):
            p = x[0:-j-1]
            i.seek(p)
            k, v = i.next()
            if x.startswith(k) and x!=k: 
                break
        else: raise
        return k

        
    def hash(self, x):
        if DEBUG: return "hash("+x+")"
        return Hash(x)


    def get_root_hash(self):
        return self.root_hash


    def close(self):
        self.db_utxo.close()
        self.db_addr.close()
        self.db_hist.close()
        self.db_undo.close()


    def add_to_history(self, addr, tx_hash, tx_pos, value, tx_height):
        key = self.address_to_key(addr)
        txo = (tx_hash + int_to_hex(tx_pos, 4)).decode('hex')

        # write the new history
        self.add_address(key + txo, value, tx_height)

        # backlink
        self.db_addr.put(txo, addr)



    def revert_add_to_history(self, addr, tx_hash, tx_pos, value, tx_height):
        key = self.address_to_key(addr)
        txo = (tx_hash + int_to_hex(tx_pos, 4)).decode('hex')

        # delete
        self.delete_address(key + txo)

        # backlink
        self.db_addr.delete(txo)


    def get_utxo_value(self, addr, txi):
        key = self.address_to_key(addr)
        leaf = key + txi
        s = self.db_utxo.get(leaf)
        value = hex_to_int(s[0:8])
        return value


    def set_spent(self, addr, txi, txid, index, height, undo):
        key = self.address_to_key(addr)
        leaf = key + txi

        s = self.delete_address(leaf)
        value = hex_to_int(s[0:8])
        in_height = hex_to_int(s[8:12])
        undo[leaf] = value, in_height

        # delete backlink txi-> addr
        self.db_addr.delete(txi)

        # add to history
        s = self.db_hist.get(addr)
        if s is None: s = ''
        txo = (txid + int_to_hex(index,4) + int_to_hex(height,4)).decode('hex')
        s += txi + int_to_hex(in_height,4).decode('hex') + txo
        s = s[ -80*self.pruning_limit:]
        self.db_hist.put(addr, s)



    def revert_set_spent(self, addr, txi, undo):
        key = self.address_to_key(addr)
        leaf = key + txi

        # restore backlink
        self.db_addr.put(txi, addr)

        v, height = undo.pop(leaf)
        self.add_address(leaf, v, height)

        # revert add to history
        s = self.db_hist.get(addr)
        # s might be empty if pruning limit was reached
        if not s:
            return

        assert s[-80:-44] == txi
        s = s[:-80]
        self.db_hist.put(addr, s)




        

    def import_transaction(self, txid, tx, block_height, touched_addr):

        undo = { 'prev_addr':[] } # contains the list of pruned items for each address in the tx; also, 'prev_addr' is a list of prev addresses
                
        prev_addr = []
        for i, x in enumerate(tx.get('inputs')):
            txi = (x.get('prevout_hash') + int_to_hex(x.get('prevout_n'), 4)).decode('hex')
            addr = self.get_address(txi)
            if addr is not None: 
                self.set_spent(addr, txi, txid, i, block_height, undo)
                touched_addr.add(addr)
            prev_addr.append(addr)

        undo['prev_addr'] = prev_addr 

        # here I add only the outputs to history; maybe I want to add inputs too (that's in the other loop)
        for x in tx.get('outputs'):
            addr = x.get('address')
            if addr is None: continue
            self.add_to_history(addr, txid, x.get('index'), x.get('value'), block_height)
            touched_addr.add(addr)

        return undo


    def revert_transaction(self, txid, tx, block_height, touched_addr, undo):
        #print_log("revert tx", txid)
        for x in reversed(tx.get('outputs')):
            addr = x.get('address')
            if addr is None: continue
            self.revert_add_to_history(addr, txid, x.get('index'), x.get('value'), block_height)
            touched_addr.add(addr)

        prev_addr = undo.pop('prev_addr')
        for i, x in reversed(list(enumerate(tx.get('inputs')))):
            addr = prev_addr[i]
            if addr is not None:
                txi = (x.get('prevout_hash') + int_to_hex(x.get('prevout_n'), 4)).decode('hex')
                self.revert_set_spent(addr, txi, undo)
                touched_addr.add(addr)

        assert undo == {}


########NEW FILE########
__FILENAME__ = composed
import threading
import time

import bitcoin


class ExpiryQueue(threading.Thread):

    def __init__(self):
        self.lock = threading.Lock()
        self.items = []
        threading.Thread.__init__(self)
        self.daemon = True

    def run(self):
        # Garbage collection
        while True:
            with self.lock:
                self.items = [i for i in self.items if not i.stopped()]
            time.sleep(0.1)

    def add(self, item):
        with self.lock:
            self.items.append(item)

expiry_queue = ExpiryQueue()


class StatementLine:

    def __init__(self, output_point):
        self.lock = threading.Lock()
        self.output_point = output_point
        self.output_loaded = None
        self.input_point = None
        self.input_loaded = None
        self.raw_output_script = None

    def is_loaded(self):
        with self.lock:
            if self.output_loaded is None:
                return False
            elif (self.input_point is not False and
                  self.input_loaded is None):
                return False
        return True


class PaymentHistory:

    def __init__(self, chain):
        self.chain = chain
        self.lock = threading.Lock()
        self.statement = []
        self._stopped = False

    def run(self, address, handle_finish):
        self.address = address
        self.handle_finish = handle_finish

        pubkey_hash = bitcoin.address_to_short_hash(address)
        self.chain.fetch_outputs(pubkey_hash, self.start_loading)

    def start_loading(self, ec, output_points):
        with self.lock:
            for outpoint in output_points:
                statement_line = StatementLine(outpoint)
                self.statement.append(statement_line)
                self.chain.fetch_spend(
                    outpoint,
                    bitcoin.bind(self.load_spend, bitcoin._1, bitcoin._2, statement_line)
                )
                self.load_tx_info(outpoint, statement_line, False)

    def load_spend(self, ec, inpoint, statement_line):
        with statement_line.lock:
            if ec:
                statement_line.input_point = False
            else:
                statement_line.input_point = inpoint
        self.finish_if_done()
        if not ec:
            self.load_tx_info(inpoint, statement_line, True)

    def finish_if_done(self):
        with self.lock:
            if any(not line.is_loaded() for line in self.statement):
                return
        result = []
        for line in self.statement:
            if line.input_point:
                line.input_loaded["value"] = -line.output_loaded["value"]
                result.append(line.input_loaded)
            else:
                line.output_loaded["raw_output_script"] = line.raw_output_script
            result.append(line.output_loaded)
        self.handle_finish(result)
        self.stop()

    def stop(self):
        with self.lock:
            self._stopped = True

    def stopped(self):
        with self.lock:
            return self._stopped

    def load_tx_info(self, point, statement_line, is_input):
        info = {}
        info["tx_hash"] = str(point.hash)
        info["index"] = point.index
        info["is_input"] = 1 if is_input else 0
        self.chain.fetch_transaction_index(
            point.hash,
            bitcoin.bind(self.tx_index, bitcoin._1, bitcoin._2, bitcoin._3, statement_line, info)
        )

    def tx_index(self, ec, block_depth, offset, statement_line, info):
        info["height"] = block_depth
        self.chain.fetch_block_header_by_depth(
            block_depth,
            bitcoin.bind(self.block_header, bitcoin._1, bitcoin._2, statement_line, info)
        )

    def block_header(self, ec, blk_head, statement_line, info):
        info["timestamp"] = blk_head.timestamp
        info["block_hash"] = str(bitcoin.hash_block_header(blk_head))
        tx_hash = bitcoin.hash_digest(info["tx_hash"])
        self.chain.fetch_transaction(
            tx_hash,
            bitcoin.bind(self.load_tx, bitcoin._1, bitcoin._2, statement_line, info)
        )

    def load_tx(self, ec, tx, statement_line, info):
        outputs = []
        for tx_out in tx.outputs:
            script = tx_out.output_script
            if script.type() == bitcoin.payment_type.pubkey_hash:
                pkh = bitcoin.short_hash(str(script.operations()[2].data))
                outputs.append(bitcoin.public_key_hash_to_address(pkh))
            else:
                outputs.append("Unknown")
        info["outputs"] = outputs
        info["inputs"] = [None for i in range(len(tx.inputs))]
        if info["is_input"] == 1:
            info["inputs"][info["index"]] = self.address
        else:
            our_output = tx.outputs[info["index"]]
            info["value"] = our_output.value
            with statement_line.lock:
                statement_line.raw_output_script = \
                    str(bitcoin.save_script(our_output.output_script))
        if not [empty_in for empty_in in info["inputs"] if empty_in is None]:
            # We have the sole input
            assert(info["is_input"] == 1)
            with statement_line.lock:
                statement_line.input_loaded = info
            self.finish_if_done()
        for tx_idx, tx_in in enumerate(tx.inputs):
            if info["is_input"] == 1 and info["index"] == tx_idx:
                continue
            self.chain.fetch_transaction(
                tx_in.previous_output.hash,
                bitcoin.bind(self.load_input, bitcoin._1, bitcoin._2, tx_in.previous_output.index, statement_line, info, tx_idx)
            )

    def load_input(self, ec, tx, index, statement_line, info, inputs_index):
        script = tx.outputs[index].output_script
        if script.type() == bitcoin.payment_type.pubkey_hash:
            pkh = bitcoin.short_hash(str(script.operations()[2].data))
            info["inputs"][inputs_index] = \
                bitcoin.public_key_hash_to_address(pkh)
        else:
            info["inputs"][inputs_index] = "Unknown"
        if not [empty_in for empty_in in info["inputs"] if empty_in is None]:
            with statement_line.lock:
                if info["is_input"] == 1:
                    statement_line.input_loaded = info
                else:
                    statement_line.output_loaded = info
        self.finish_if_done()


def payment_history(chain, address, handle_finish):
    ph = PaymentHistory(chain)
    expiry_queue.add(ph)
    ph.run(address, handle_finish)


if __name__ == "__main__":
    def finish(result):
        print result

    def last(ec, depth):
        print "D:", depth

    service = bitcoin.async_service(1)
    prefix = "/home/genjix/libbitcoin/database"
    chain = bitcoin.bdb_blockchain(service, prefix)
    chain.fetch_last_depth(last)
    address = "1Pbn3DLXfjqF1fFV9YPdvpvyzejZwkHhZE"
    print "Looking up", address
    payment_history(chain, address, finish)
    raw_input()

########NEW FILE########
__FILENAME__ = h1
import bitcoin
import history1 as history
import membuf


def blockchain_started(ec, chain):
    print "Blockchain initialisation:", ec


def finish(ec, result):
    print "Finish:", ec
    for line in result:
        for k, v in line.iteritems():
            begin = k + ":"
            print begin, " " * (12 - len(begin)), v
        print


a = bitcoin.async_service(1)
chain = bitcoin.bdb_blockchain(a, "/home/genjix/libbitcoin/database",
                               blockchain_started)
txpool = bitcoin.transaction_pool(a, chain)
txdat = bitcoin.data_chunk("0100000001d6cad920a04acd6c0609cd91fe4dafa1f3b933ac90e032c78fdc19d98785f2bb010000008b483045022043f8ce02784bd7231cb362a602920f2566c18e1877320bf17d4eabdac1019b2f022100f1fd06c57330683dff50e1b4571fb0cdab9592f36e3d7e98d8ce3f94ce3f255b01410453aa8d5ddef56731177915b7b902336109326f883be759ec9da9c8f1212c6fa3387629d06e5bf5e6bcc62ec5a70d650c3b1266bb0bcc65ca900cff5311cb958bffffffff0280969800000000001976a9146025cabdbf823949f85595f3d1c54c54cd67058b88ac602d2d1d000000001976a914c55c43631ab14f7c4fd9c5f153f6b9123ec32c8888ac00000000")
ex = bitcoin.satoshi_exporter()
tx = ex.load_transaction(txdat)


def stored(ec):
    print "mbuff", ec

mbuff = membuf.memory_buffer(a.internal_ptr, chain.internal_ptr,
                             txpool.internal_ptr)
mbuff.receive(tx, stored)
address = "1AA6mgxqSrvJTxRrYrikSnLaAGupVzvx4f"
raw_input()
history.payment_history(a, chain, txpool, mbuff, address, finish)
raw_input()

########NEW FILE########
__FILENAME__ = history
import threading
import time

import bitcoin
from bitcoin import bind, _1, _2, _3
import multimap


class ExpiryQueue(threading.Thread):

    def __init__(self):
        self.lock = threading.Lock()
        self.items = []
        threading.Thread.__init__(self)
        self.daemon = True

    def run(self):
        # Garbage collection
        while True:
            with self.lock:
                self.items = [i for i in self.items if not i.stopped()]
            time.sleep(0.1)

    def add(self, item):
        with self.lock:
            self.items.append(item)


expiry_queue = ExpiryQueue()


class MemoryPoolBuffer:

    def __init__(self, txpool, chain, monitor):
        self.txpool = txpool
        self.chain = chain
        self.monitor = monitor
        # prevout: inpoint
        self.lookup_input = {}
        # payment_address: outpoint
        self.lookup_address = multimap.MultiMap()
        # transaction timestamps
        self.timestamps = {}

    def recv_tx(self, tx, handle_store):
        tx_hash = str(bitcoin.hash_transaction(tx))
        desc = (tx_hash, [], [])
        for input in tx.inputs:
            prevout = input.previous_output
            desc[1].append((str(prevout.hash), prevout.index))
        for idx, output in enumerate(tx.outputs):
            address = bitcoin.payment_address()
            if address.extract(output.output_script):
                desc[2].append((idx, str(address)))
        self.txpool.store(
            tx,
            bind(self.confirmed, _1, desc),
            bind(self.mempool_stored, _1, desc, handle_store)
        )

    def mempool_stored(self, ec, desc, handle_store):
        tx_hash, prevouts, addrs = desc
        if ec:
            handle_store(ec)
            return
        for idx, prevout in enumerate(prevouts):
            #inpoint = bitcoin.input_point()
            #inpoint.hash, inpoint.index = tx_hash, idx
            prevout = "%s:%s" % prevout
            self.lookup_input[prevout] = tx_hash, idx
        for idx, address in addrs:
            #outpoint = bitcoin.output_point()
            #outpoint.hash, outpoint.index = tx_hash, idx
            self.lookup_address[str(address)] = tx_hash, idx
        self.timestamps[tx_hash] = int(time.time())
        handle_store(ec)
        self.monitor.tx_stored(desc)

    def confirmed(self, ec, desc):
        tx_hash, prevouts, addrs = desc
        if ec:
            print "Problem confirming transaction", tx_hash, ec
            return
        print "Confirmed", tx_hash
        for idx, prevout in enumerate(prevouts):
            #inpoint = bitcoin.input_point()
            #inpoint.hash, inpoint.index = tx_hash, idx
            prevout = "%s:%s" % prevout
            assert self.lookup_input[prevout] == (tx_hash, idx)
            del self.lookup_input[prevout]
        for idx, address in addrs:
            #outpoint = bitcoin.output_point()
            #outpoint.hash, outpoint.index = tx_hash, idx
            outpoint = tx_hash, idx
            self.lookup_address.delete(str(address), outpoint)
        del self.timestamps[tx_hash]
        self.monitor.tx_confirmed(desc)

    def check(self, output_points, address, handle):
        class ExtendableDict(dict):
            pass
        result = []
        for outpoint in output_points:
            if str(outpoint) in self.lookup_input:
                point = self.lookup_input[str(outpoint)]
                info = ExtendableDict()
                info["tx_hash"] = point[0]
                info["index"] = point[1]
                info["is_input"] = 1
                info["timestamp"] = self.timestamps[info["tx_hash"]]
                result.append(info)
        if str(address) in self.lookup_address:
            addr_points = self.lookup_address[str(address)]
            for point in addr_points:
                info = ExtendableDict()
                info["tx_hash"] = str(point.hash)
                info["index"] = point.index
                info["is_input"] = 0
                info["timestamp"] = self.timestamps[info["tx_hash"]]
                result.append(info)
        handle(result)


class PaymentEntry:

    def __init__(self, output_point):
        self.lock = threading.Lock()
        self.output_point = output_point
        self.output_loaded = None
        self.input_point = None
        self.input_loaded = None
        self.raw_output_script = None

    def is_loaded(self):
        with self.lock:
            if self.output_loaded is None:
                return False
            elif self.has_input() and self.input_loaded is None:
                return False
        return True

    def has_input(self):
        return self.input_point is not False


class History:

    def __init__(self, chain, txpool, membuf):
        self.chain = chain
        self.txpool = txpool
        self.membuf = membuf
        self.lock = threading.Lock()
        self._stopped = False

    def start(self, address, handle_finish):
        self.statement = []
        self.membuf_result = None
        self.address = address
        self.handle_finish = handle_finish

        address = bitcoin.payment_address(address)
        # To begin we fetch all the outputs (payments in)
        # associated with this address
        self.chain.fetch_outputs(address, bind(self.check_membuf, _1, _2))

    def stop(self):
        with self.lock:
            assert self._stopped is False
            self._stopped = True

    def stopped(self):
        with self.lock:
            return self._stopped

    def stop_on_error(self, ec):
        if ec:
            self.handle_finish(None)
            self.stop()
        return self.stopped()

    def check_membuf(self, ec, output_points):
        if self.stop_on_error(ec):
            return
        self.membuf.check(output_points, self.address, bind(self.start_loading, _1, output_points))

    def start_loading(self, membuf_result, output_points):
        if len(membuf_result) == 0 and len(output_points) == 0:
            self.handle_finish([])
            self.stopped()
        # Create a bunch of entry lines which are outputs and
        # then their corresponding input (if it exists)
        for outpoint in output_points:
            entry = PaymentEntry(outpoint)
            with self.lock:
                self.statement.append(entry)
            # Attempt to fetch the spend of this output
            self.chain.fetch_spend(outpoint, bind(self.load_spend, _1, _2, entry))
            self.load_tx_info(outpoint, entry, False)
        # Load memory pool transactions
        with self.lock:
            self.membuf_result = membuf_result
        for info in self.membuf_result:
            self.txpool.fetch(bitcoin.hash_digest(info["tx_hash"]), bind(self.load_pool_tx, _1, _2, info))

    def load_spend(self, ec, inpoint, entry):
        # Need a custom self.stop_on_error(...) as a missing spend
        # is not an error in this case.
        if not self.stopped() and ec and ec != bitcoin.error.unspent_output:
            self.handle_finish(None)
            self.stop()
        if self.stopped():
            return
        with entry.lock:
            if ec == bitcoin.error.unspent_output:
                # This particular entry.output_point
                # has not been spent yet
                entry.input_point = False
            else:
                entry.input_point = inpoint
        if ec == bitcoin.error.unspent_output:
            # Attempt to stop if all the info for the inputs and outputs
            # has been loaded.
            self.finish_if_done()
        else:
            # We still have to load at least one more payment outwards
            self.load_tx_info(inpoint, entry, True)

    def finish_if_done(self):
        with self.lock:
            # Still have more entries to finish loading, so return
            if any(not entry.is_loaded() for entry in self.statement):
                return
            # Memory buffer transactions finished loading?
            if any("height" not in info for info in self.membuf_result):
                return
        # Whole operation completed successfully! Finish up.
        result = []
        for entry in self.statement:
            if entry.input_point:
                # value of the input is simply the inverse of
                # the corresponding output
                entry.input_loaded["value"] = -entry.output_loaded["value"]
                # output should come before the input as it's chronological
                result.append(entry.output_loaded)
                result.append(entry.input_loaded)
            else:
                # Unspent outputs have a raw_output_script field
                assert entry.raw_output_script is not None
                entry.output_loaded["raw_output_script"] = \
                    entry.raw_output_script
                result.append(entry.output_loaded)
        mempool_result = []
        for info in self.membuf_result:
            # Lookup prevout in result
            # Set "value" field
            if info["is_input"] == 1:
                prevout_tx = None
                for prevout_info in result:
                    if prevout_info["tx_hash"] == info.previous_output.hash:
                        prevout_tx = prevout_info
                assert prevout_tx is not None
                info["value"] = -prevout_info["value"]
            mempool_result.append(info)
        result.extend(mempool_result)
        self.handle_finish(result)
        self.stop()

    def load_tx_info(self, point, entry, is_input):
        info = {}
        info["tx_hash"] = str(point.hash)
        info["index"] = point.index
        info["is_input"] = 1 if is_input else 0
        # Before loading the transaction, Stratum requires the hash
        # of the parent block, so we load the block depth and then
        # fetch the block header and hash it.
        self.chain.fetch_transaction_index(point.hash, bind(self.tx_index, _1, _2, _3, entry, info))

    def tx_index(self, ec, block_depth, offset, entry, info):
        if self.stop_on_error(ec):
            return
        info["height"] = block_depth
        # And now for the block hash
        self.chain.fetch_block_header_by_depth(block_depth, bind(self.block_header, _1, _2, entry, info))

    def block_header(self, ec, blk_head, entry, info):
        if self.stop_on_error(ec):
            return
        info["timestamp"] = blk_head.timestamp
        info["block_hash"] = str(bitcoin.hash_block_header(blk_head))
        tx_hash = bitcoin.hash_digest(info["tx_hash"])
        # Now load the actual main transaction for this input or output
        self.chain.fetch_transaction(tx_hash, bind(self.load_chain_tx, _1, _2, entry, info))

    def load_pool_tx(self, ec, tx, info):
        if self.stop_on_error(ec):
            return
        # block_hash = mempool:5
        # inputs (load from prevtx)
        # outputs (load from tx)
        # raw_output_script (load from tx)
        # height is always None
        # value (get from finish_if_done)
        self.load_tx(tx, info)
        if info["is_input"] == 0:
            our_output = tx.outputs[info["index"]]
            info["value"] = our_output.value
            # Save serialised output script in case this output is unspent
            info["raw_output_script"] = \
                str(bitcoin.save_script(our_output.output_script))
        else:
            assert(info["is_input"] == 1)
            info.previous_output = tx.inputs[info["index"]].previous_output
        # If all the inputs are loaded
        if self.inputs_all_loaded(info["inputs"]):
            # We are the sole input
            assert(info["is_input"] == 1)
            # No more inputs left to load
            # This info has finished loading
            info["height"] = None
            info["block_hash"] = "mempool"
            self.finish_if_done()
        create_handler = lambda prevout_index, input_index: \
            bind(self.load_input_pool_tx, _1, _2, prevout_index, info, input_index)
        self.fetch_input_txs(tx, info, create_handler)

    def load_tx(self, tx, info):
        # List of output addresses
        outputs = []
        for tx_out in tx.outputs:
            address = bitcoin.payment_address()
            # Attempt to extract address from output script
            if address.extract(tx_out.output_script):
                outputs.append(address.encoded())
            else:
                # ... otherwise append "Unknown"
                outputs.append("Unknown")
        info["outputs"] = outputs
        # For the inputs, we need the originator address which has to
        # be looked up in the blockchain.
        # Create list of Nones and then populate it.
        # Loading has finished when list is no longer all None.
        info["inputs"] = [None for i in tx.inputs]
        # If this transaction was loaded for an input, then we already
        # have a source address for at least one input.
        if info["is_input"] == 1:
            info["inputs"][info["index"]] = self.address

    def fetch_input_txs(self, tx, info, create_handler):
        # Load the previous_output for every input so we can get
        # the output address
        for input_index, tx_input in enumerate(tx.inputs):
            if info["is_input"] == 1 and info["index"] == input_index:
                continue
            prevout = tx_input.previous_output
            handler = create_handler(prevout.index, input_index)
            self.chain.fetch_transaction(prevout.hash, handler)

    def load_chain_tx(self, ec, tx, entry, info):
        if self.stop_on_error(ec):
            return
        self.load_tx(tx, info)
        if info["is_input"] == 0:
            our_output = tx.outputs[info["index"]]
            info["value"] = our_output.value
            # Save serialised output script in case this output is unspent
            with entry.lock:
                entry.raw_output_script = \
                    str(bitcoin.save_script(our_output.output_script))
        # If all the inputs are loaded
        if self.inputs_all_loaded(info["inputs"]):
            # We are the sole input
            assert(info["is_input"] == 1)
            with entry.lock:
                entry.input_loaded = info
            self.finish_if_done()
        create_handler = lambda prevout_index, input_index: \
            bind(self.load_input_chain_tx, _1, _2, prevout_index, entry, info, input_index)
        self.fetch_input_txs(tx, info, create_handler)

    def inputs_all_loaded(self, info_inputs):
        return not [empty_in for empty_in in info_inputs if empty_in is None]

    def load_input_tx(self, tx, output_index, info, input_index):
        # For our input, we load the previous tx so we can get the
        # corresponding output.
        # We need the output to extract the address.
        script = tx.outputs[output_index].output_script
        address = bitcoin.payment_address()
        if address.extract(script):
            info["inputs"][input_index] = address.encoded()
        else:
            info["inputs"][input_index] = "Unknown"

    def load_input_chain_tx(self, ec, tx, output_index,
                            entry, info, input_index):
        if self.stop_on_error(ec):
            return
        self.load_input_tx(tx, output_index, info, input_index)
        # If all the inputs are loaded, then we have finished loading
        # the info for this input-output entry pair
        if self.inputs_all_loaded(info["inputs"]):
            with entry.lock:
                if info["is_input"] == 1:
                    entry.input_loaded = info
                else:
                    entry.output_loaded = info
        self.finish_if_done()

    def load_input_pool_tx(self, ec, tx, output_index, info, input_index):
        if self.stop_on_error(ec):
            return
        self.load_input_tx(tx, output_index, info, input_index)
        if not [inp for inp in info["inputs"] if inp is None]:
            # No more inputs left to load
            # This info has finished loading
            info["height"] = None
            info["block_hash"] = "mempool"
        self.finish_if_done()


def payment_history(chain, txpool, membuf, address, handle_finish):
    h = History(chain, txpool, membuf)
    expiry_queue.add(h)
    h.start(address, handle_finish)


if __name__ == "__main__":
    ex = bitcoin.satoshi_exporter()
    tx_a = bitcoin.data_chunk("0100000003d0406a31f628e18f5d894b2eaf4af719906dc61be4fb433a484ed870f6112d15000000008b48304502210089c11db8c1524d8839243803ac71e536f3d876e8265bbb3bc4a722a5d0bd40aa022058c3e59a7842ef1504b1c2ce048f9af2d69bbf303401dced1f68b38d672098a10141046060f6c8e355b94375eec2cc1d231f8044e811552d54a7c4b36fe8ee564861d07545c6c9d5b9f60d16e67d683b93486c01d3bd3b64d142f48af70bb7867d0ffbffffffff6152ed1552b1f2635317cea7be06615a077fc0f4aa62795872836c4182ca0f25000000008b48304502205f75a468ddb08070d235f76cb94c3f3e2a75e537bc55d087cc3e2a1559b7ac9b022100b17e4c958aaaf9b93359f5476aa5ed438422167e294e7207d5cfc105e897ed91014104a7108ec63464d6735302085124f3b7a06aa8f9363eab1f85f49a21689b286eb80fbabda7f838d9b6bff8550b377ad790b41512622518801c5230463dbbff6001ffffffff01c52914dcb0f3d8822e5a9e3374e5893a7b6033c9cfce5a8e5e6a1b3222a5cb010000008c4930460221009561f7206cc98f40f3eab5f3308b12846d76523bd07b5f058463f387694452b2022100b2684ec201760fa80b02954e588f071e46d0ff16562c1ab393888416bf8fcc44014104a7108ec63464d6735302085124f3b7a06aa8f9363eab1f85f49a21689b286eb80fbabda7f838d9b6bff8550b377ad790b41512622518801c5230463dbbff6001ffffffff02407e0f00000000001976a914c3b98829108923c41b3c1ba6740ecb678752fd5e88ac40420f00000000001976a914424648ea6548cc1c4ea707c7ca58e6131791785188ac00000000")
    tx_a = ex.load_transaction(tx_a)
    assert bitcoin.hash_transaction(tx_a) == "e72e4f025695446cfd5c5349d1720beb38801f329a00281f350cb7e847153397"
    tx_b = bitcoin.data_chunk("0100000001e269f0d74b8e6849233953715bc0be3ba6727afe0bc5000d015758f9e67dde34000000008c4930460221008e305e3fdf4420203a8cced5be20b73738a3b51186dfda7c6294ee6bebe331b7022100c812ded044196132f5e796dbf4b566b6ee3246cc4915eca3cf07047bcdf24a9301410493b6ce24182a58fc3bd0cbee0ddf5c282e00c0c10b1293c7a3567e95bfaaf6c9a431114c493ba50398ad0a82df06254605d963d6c226db615646fadd083ddfd9ffffffff020f9c1208000000001976a91492fffb2cb978d539b6bcd12c968b263896c6aacf88ac8e3f7600000000001976a914654dc745e9237f86b5fcdfd7e01165af2d72909588ac00000000")
    tx_b = ex.load_transaction(tx_b)
    assert bitcoin.hash_transaction(tx_b) == "acfda6dbf4ae1b102326bfb7c9541702d5ebb0339bc57bd74d36746855be8eac"

    def blockchain_started(ec, chain):
        print "Blockchain initialisation:", ec

    def store_tx(ec):
        print "Tx", ec

    def finish(result):
        print "Finish"
        if result is None:
            return
        for line in result:
            for k, v in line.iteritems():
                begin = k + ":"
                print begin, " " * (12 - len(begin)), v
            print

    class FakeMonitor:
        def tx_stored(self, tx):
            pass

        def tx_confirmed(self, tx):
            pass

    service = bitcoin.async_service(1)
    prefix = "/home/genjix/libbitcoin/database"
    chain = bitcoin.bdb_blockchain(service, prefix, blockchain_started)
    txpool = bitcoin.transaction_pool(service, chain)
    membuf = MemoryPoolBuffer(txpool, chain, FakeMonitor())
    membuf.recv_tx(tx_a, store_tx)
    membuf.recv_tx(tx_b, store_tx)

    txdat = bitcoin.data_chunk("0100000001d6cad920a04acd6c0609cd91fe4dafa1f3b933ac90e032c78fdc19d98785f2bb010000008b483045022043f8ce02784bd7231cb362a602920f2566c18e1877320bf17d4eabdac1019b2f022100f1fd06c57330683dff50e1b4571fb0cdab9592f36e3d7e98d8ce3f94ce3f255b01410453aa8d5ddef56731177915b7b902336109326f883be759ec9da9c8f1212c6fa3387629d06e5bf5e6bcc62ec5a70d650c3b1266bb0bcc65ca900cff5311cb958bffffffff0280969800000000001976a9146025cabdbf823949f85595f3d1c54c54cd67058b88ac602d2d1d000000001976a914c55c43631ab14f7c4fd9c5f153f6b9123ec32c8888ac00000000")
    req = {"id": 110, "params": ["1GULoCDnGjhfSWzHs6zDzBxbKt9DR7uRbt"]}
    ex = bitcoin.satoshi_exporter()
    tx = ex.load_transaction(txdat)
    time.sleep(4)
    membuf.recv_tx(tx, store_tx)

    raw_input()
    address = "1Jqu2PVGDvNv4La113hgCJsvRUCDb3W65D", "1GULoCDnGjhfSWzHs6zDzBxbKt9DR7uRbt"
    #address = "1Pbn3DLXfjqF1fFV9YPdvpvyzejZwkHhZE"
    print "Looking up", address
    payment_history(chain, txpool, membuf, address[0], finish)
    #payment_history(chain, txpool, membuf, address[1], finish)
    raw_input()
    print "Stopping..."

########NEW FILE########
__FILENAME__ = multimap
class MultiMap:

    def __init__(self):
        self.multi = {}

    def __getitem__(self, key):
        return self.multi[key]

    def __setitem__(self, key, value):
        if key not in self.multi:
            self.multi[key] = []
        self.multi[key].append(value)

    def delete(self, key, value):
        for i, item in enumerate(self.multi[key]):
            if item == value:
                del self.multi[key][i]
                if not self.multi[key]:
                    del self.multi[key]
                return
        raise IndexError

    def __repr__(self):
        return repr(self.multi)

    def __str__(self):
        return str(self.multi)

    def has_key(self, key):
        return key in self.multi


if __name__ == "__main__":
    m = MultiMap()
    m["foo"] = 1
    m["foo"] = 1
    m["bar"] = 2
    print m["foo"]
    m.delete("foo", 1)
    m.delete("bar", 2)
    print m.multi

########NEW FILE########
__FILENAME__ = trace_test
import bitcoin

import trace_tx


def blockchain_started(ec, chain):
    print "Blockchain initialisation:", ec


def handle_tx(ec, tx):
    if ec:
        print ec
    trace_tx.trace_tx(service.internal_ptr, chain.internal_ptr, tx, finish)


def finish(ec, result):
    print ec
    print result


if __name__ == '__main__':
    service = bitcoin.async_service(1)
    chain = bitcoin.bdb_blockchain(service, "/home/genjix/libbitcoin/database",
                                   blockchain_started)
    chain.fetch_transaction(
        bitcoin.hash_digest("16e3e3bfbaa072e33e6a9be1df7a13ecde5ad46a8d4d4893dbecaf0c0aeeb842"),
        handle_tx
    )

    raw_input()

########NEW FILE########
__FILENAME__ = processor
import json
import Queue as queue
import socket
import threading
import time
import traceback
import sys

from utils import random_string, timestr, print_log


class Shared:

    def __init__(self, config):
        self.lock = threading.Lock()
        self._stopped = False
        self.config = config

    def stop(self):
        print_log("Stopping Stratum")
        with self.lock:
            self._stopped = True

    def stopped(self):
        with self.lock:
            return self._stopped


class Processor(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        self.dispatcher = None
        self.queue = queue.Queue()

    def process(self, session, request):
        pass

    def add_request(self, session, request):
        self.queue.put((session, request))

    def push_response(self, session, response):
        #print "response", response
        self.dispatcher.request_dispatcher.push_response(session, response)

    def close(self):
        pass

    def run(self):
        while not self.shared.stopped():
            try:
                request, session = self.queue.get(True, timeout=1)
            except:
                continue
            try:
                self.process(request, session)
            except:
                traceback.print_exc(file=sys.stdout)

        self.close()


class Dispatcher:

    def __init__(self, config):
        self.shared = Shared(config)
        self.request_dispatcher = RequestDispatcher(self.shared)
        self.request_dispatcher.start()
        self.response_dispatcher = \
            ResponseDispatcher(self.shared, self.request_dispatcher)
        self.response_dispatcher.start()

    def register(self, prefix, processor):
        processor.dispatcher = self
        processor.shared = self.shared
        processor.start()
        self.request_dispatcher.processors[prefix] = processor


class RequestDispatcher(threading.Thread):

    def __init__(self, shared):
        self.shared = shared
        threading.Thread.__init__(self)
        self.daemon = True
        self.request_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.lock = threading.Lock()
        self.idlock = threading.Lock()
        self.sessions = {}
        self.processors = {}

    def push_response(self, session, item):
        self.response_queue.put((session, item))

    def pop_response(self):
        return self.response_queue.get()

    def push_request(self, session, item):
        self.request_queue.put((session, item))

    def pop_request(self):
        return self.request_queue.get()

    def get_session_by_address(self, address):
        for x in self.sessions.values():
            if x.address == address:
                return x

    def run(self):
        if self.shared is None:
            raise TypeError("self.shared not set in Processor")

        lastgc = 0 

        while not self.shared.stopped():
            session, request = self.pop_request()
            try:
                self.do_dispatch(session, request)
            except:
                traceback.print_exc(file=sys.stdout)

            if time.time() - lastgc > 60.0:
                self.collect_garbage()
                lastgc = time.time()

        self.stop()

    def stop(self):
        pass

    def do_dispatch(self, session, request):
        """ dispatch request to the relevant processor """

        method = request['method']
        params = request.get('params', [])
        suffix = method.split('.')[-1]

        if session is not None:
            if suffix == 'subscribe':
                session.subscribe_to_service(method, params)

        prefix = request['method'].split('.')[0]
        try:
            p = self.processors[prefix]
        except:
            print_log("error: no processor for", prefix)
            return

        p.add_request(session, request)

        if method in ['server.version']:
            try:
                session.version = params[0]
                session.protocol_version = float(params[1])
            except:
                pass


    def get_sessions(self):
        with self.lock:
            r = self.sessions.values()
        return r

    def add_session(self, session):
        key = session.key()
        with self.lock:
            self.sessions[key] = session

    def remove_session(self, session):
        key = session.key()
        with self.lock:
            self.sessions.pop(key)

    def collect_garbage(self):
        now = time.time()
        for session in self.sessions.values():
            if (now - session.time) > session.timeout:
                session.stop()



class Session:

    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        self.bp = self.dispatcher.processors['blockchain']
        self._stopped = False
        self.lock = threading.Lock()
        self.subscriptions = []
        self.address = ''
        self.name = ''
        self.version = 'unknown'
        self.protocol_version = 0.
        self.time = time.time()
        threading.Timer(2, self.info).start()


    def key(self):
        return self.name + self.address


    # Debugging method. Doesn't need to be threadsafe.
    def info(self):
        for sub in self.subscriptions:
            #print sub
            method = sub[0]
            if method == 'blockchain.address.subscribe':
                addr = sub[1]
                break
        else:
            addr = None

        if self.subscriptions:
            print_log("%4s" % self.name,
                      "%15s" % self.address,
                      "%35s" % addr,
                      "%3d" % len(self.subscriptions),
                      self.version)

    def stop(self):
        with self.lock:
            if self._stopped:
                return
            self._stopped = True

        self.shutdown()
        self.dispatcher.remove_session(self)
        self.stop_subscriptions()


    def shutdown(self):
        pass


    def stopped(self):
        with self.lock:
            return self._stopped


    def subscribe_to_service(self, method, params):
        with self.lock:
            if self._stopped:
                return
            if (method, params) not in self.subscriptions:
                self.subscriptions.append((method,params))
        self.bp.do_subscribe(method, params, self)


    def stop_subscriptions(self):
        with self.lock:
            s = self.subscriptions[:]
        for method, params in s:
            self.bp.do_unsubscribe(method, params, self)
        with self.lock:
            self.subscriptions = []


class ResponseDispatcher(threading.Thread):

    def __init__(self, shared, request_dispatcher):
        self.shared = shared
        self.request_dispatcher = request_dispatcher
        threading.Thread.__init__(self)
        self.daemon = True

    def run(self):
        while not self.shared.stopped():
            session, response = self.request_dispatcher.pop_response()
            session.send_response(response)

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python
# Copyright(C) 2012 thomasv@gitorious

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.

import ConfigParser
import logging
import socket
import sys
import time
import threading
import traceback

import json
import os

logging.basicConfig()

if sys.maxsize <= 2**32:
    print "Warning: it looks like you are using a 32bit system. You may experience crashes caused by mmap"


def attempt_read_config(config, filename):
    try:
        with open(filename, 'r') as f:
            config.readfp(f)
    except IOError:
        pass


def create_config():
    config = ConfigParser.ConfigParser()
    # set some defaults, which will be overwritten by the config file
    config.add_section('server')
    config.set('server', 'banner', 'Welcome to Electrum!')
    config.set('server', 'host', 'localhost')
    config.set('server', 'report_host', '')
    config.set('server', 'stratum_tcp_port', '50001')
    config.set('server', 'stratum_http_port', '8081')
    config.set('server', 'stratum_tcp_ssl_port', '50002')
    config.set('server', 'stratum_http_ssl_port', '8082')
    config.set('server', 'report_stratum_tcp_port', '')
    config.set('server', 'report_stratum_http_port', '')
    config.set('server', 'report_stratum_tcp_ssl_port', '')
    config.set('server', 'report_stratum_http_ssl_port', '')
    config.set('server', 'ssl_certfile', '')
    config.set('server', 'ssl_keyfile', '')
    config.set('server', 'password', '')
    config.set('server', 'irc', 'no')
    config.set('server', 'irc_nick', '')
    config.set('server', 'coin', '')
    config.set('server', 'datadir', '')

    # use leveldb as default
    config.set('server', 'backend', 'leveldb')
    config.add_section('leveldb')
    config.set('leveldb', 'path_fulltree', '/dev/shm/electrum_db')
    config.set('leveldb', 'pruning_limit', '100')

    for path in ('/etc/', ''):
        filename = path + 'electrum.conf'
        attempt_read_config(config, filename)

    try:
        with open('/etc/electrum.banner', 'r') as f:
            config.set('server', 'banner', f.read())
    except IOError:
        pass

    return config


def run_rpc_command(params):
    cmd = params[0]
    import xmlrpclib
    server = xmlrpclib.ServerProxy('http://localhost:8000')
    func = getattr(server, cmd)
    r = func(*params[1:])

    if cmd == 'info':
        now = time.time()
        print 'type           address         sub  version  time'
        for item in r:
            print '%4s   %21s   %3s  %7s  %.2f' % (item.get('name'),
                                                   item.get('address'),
                                                   item.get('subscriptions'),
                                                   item.get('version'),
                                                   (now - item.get('time')),
                                                   )
    else:
        print r


def cmd_info():
    return map(lambda s: {"time": s.time,
                          "name": s.name,
                          "address": s.address,
                          "version": s.version,
                          "subscriptions": len(s.subscriptions)},
               dispatcher.request_dispatcher.get_sessions())

def cmd_debug(s):
    if s:
        from guppy import hpy
        h = hpy()
        bp = dispatcher.request_dispatcher.processors['blockchain']
        try:
            result = str(eval(s))
        except:
            result = "error"
        return result


def get_port(config, name):
    try:
        return config.getint('server', name)
    except:
        return None

if __name__ == '__main__':
    config = create_config()
    password = config.get('server', 'password')
    host = config.get('server', 'host')
    stratum_tcp_port = get_port(config, 'stratum_tcp_port')
    stratum_http_port = get_port(config, 'stratum_http_port')
    stratum_tcp_ssl_port = get_port(config, 'stratum_tcp_ssl_port')
    stratum_http_ssl_port = get_port(config, 'stratum_http_ssl_port')
    ssl_certfile = config.get('server', 'ssl_certfile')
    ssl_keyfile = config.get('server', 'ssl_keyfile')

    if stratum_tcp_ssl_port or stratum_http_ssl_port:
        assert ssl_certfile and ssl_keyfile

    if len(sys.argv) > 1:
        try:
            run_rpc_command(sys.argv[1:])
        except socket.error:
            print "server not running"
            sys.exit(1)
        sys.exit(0)

    try:
        run_rpc_command(['getpid'])
        is_running = True
    except socket.error:
        is_running = False

    if is_running:
        print "server already running"
        sys.exit(1)


    from processor import Dispatcher, print_log
    from backends.irc import ServerProcessor
    from transports.stratum_tcp import TcpServer
    from transports.stratum_http import HttpServer

    backend_name = config.get('server', 'backend')
    if backend_name == 'libbitcoin':
        from backends.libbitcoin import BlockchainProcessor
    elif backend_name == 'leveldb':
        from backends.bitcoind import BlockchainProcessor
    else:
        print "Unknown backend '%s' specified\n" % backend_name
        sys.exit(1)

    print "\n\n\n\n\n"
    print_log("Starting Electrum server on", host)

    # Create hub
    dispatcher = Dispatcher(config)
    shared = dispatcher.shared

    # handle termination signals
    import signal
    def handler(signum = None, frame = None):
        print_log('Signal handler called with signal', signum)
        shared.stop()
    for sig in [signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT]:
        signal.signal(sig, handler)


    # Create and register processors
    chain_proc = BlockchainProcessor(config, shared)
    dispatcher.register('blockchain', chain_proc)

    server_proc = ServerProcessor(config)
    dispatcher.register('server', server_proc)

    transports = []
    # Create various transports we need
    if stratum_tcp_port:
        tcp_server = TcpServer(dispatcher, host, stratum_tcp_port, False, None, None)
        transports.append(tcp_server)

    if stratum_tcp_ssl_port:
        tcp_server = TcpServer(dispatcher, host, stratum_tcp_ssl_port, True, ssl_certfile, ssl_keyfile)
        transports.append(tcp_server)

    if stratum_http_port:
        http_server = HttpServer(dispatcher, host, stratum_http_port, False, None, None)
        transports.append(http_server)

    if stratum_http_ssl_port:
        http_server = HttpServer(dispatcher, host, stratum_http_ssl_port, True, ssl_certfile, ssl_keyfile)
        transports.append(http_server)

    for server in transports:
        server.start()

    

    from SimpleXMLRPCServer import SimpleXMLRPCServer
    server = SimpleXMLRPCServer(('localhost',8000), allow_none=True, logRequests=False)
    server.register_function(lambda: os.getpid(), 'getpid')
    server.register_function(shared.stop, 'stop')
    server.register_function(cmd_info, 'info')
    server.register_function(cmd_debug, 'debug')
    server.socket.settimeout(1)
 
    while not shared.stopped():
        try:
            server.handle_request()
        except socket.timeout:
            continue
        except:
            shared.stop()

    server_proc.join()
    chain_proc.join()
    print_log("Electrum Server stopped")

########NEW FILE########
__FILENAME__ = stratum_http
#!/usr/bin/env python
# Copyright(C) 2012 thomasv@gitorious

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.
"""
sessions are identified with cookies
 - each session has a buffer of responses to requests


from the processor point of view:
 - the user only defines process() ; the rest is session management.  thus sessions should not belong to processor

"""
import json
import logging
import os
import Queue
import SimpleXMLRPCServer
import socket
import SocketServer
import sys
import time
import threading
import traceback
import types

import jsonrpclib
from jsonrpclib import Fault
from jsonrpclib.jsonrpc import USE_UNIX_SOCKETS
from OpenSSL import SSL

try:
    import fcntl
except ImportError:
    # For Windows
    fcntl = None


from processor import Session
from utils import random_string, print_log


def get_version(request):
    # must be a dict
    if 'jsonrpc' in request.keys():
        return 2.0
    if 'id' in request.keys():
        return 1.0
    return None


def validate_request(request):
    if not isinstance(request, types.DictType):
        return Fault(-32600, 'Request must be {}, not %s.' % type(request))
    rpcid = request.get('id', None)
    version = get_version(request)
    if not version:
        return Fault(-32600, 'Request %s invalid.' % request, rpcid=rpcid)
    request.setdefault('params', [])
    method = request.get('method', None)
    params = request.get('params')
    param_types = (types.ListType, types.DictType, types.TupleType)
    if not method or type(method) not in types.StringTypes or type(params) not in param_types:
        return Fault(-32600, 'Invalid request parameters or method.', rpcid=rpcid)
    return True


class StratumJSONRPCDispatcher(SimpleXMLRPCServer.SimpleXMLRPCDispatcher):

    def __init__(self, encoding=None):
        # todo: use super
        SimpleXMLRPCServer.SimpleXMLRPCDispatcher.__init__(self, allow_none=True, encoding=encoding)

    def _marshaled_dispatch(self, session_id, data, dispatch_method=None):
        response = None
        try:
            request = jsonrpclib.loads(data)
        except Exception, e:
            fault = Fault(-32700, 'Request %s invalid. (%s)' % (data, e))
            response = fault.response()
            return response

        session = self.dispatcher.get_session_by_address(session_id)
        if not session:
            return 'Error: session not found'
        session.time = time.time()

        responses = []
        if not isinstance(request, types.ListType):
            request = [request]

        for req_entry in request:
            result = validate_request(req_entry)
            if type(result) is Fault:
                responses.append(result.response())
                continue

            self.dispatcher.do_dispatch(session, req_entry)

            if req_entry['method'] == 'server.stop':
                return json.dumps({'result': 'ok'})

        r = self.poll_session(session)
        for item in r:
            responses.append(json.dumps(item))

        if len(responses) > 1:
            response = '[%s]' % ','.join(responses)
        elif len(responses) == 1:
            response = responses[0]
        else:
            response = ''

        return response

    def create_session(self):
        session_id = random_string(20)
        session = HttpSession(self.dispatcher, session_id)
        return session_id

    def poll_session(self, session):
        q = session.pending_responses
        responses = []
        while not q.empty():
            r = q.get()
            responses.append(r)
        #print "poll: %d responses"%len(responses)
        return responses


class StratumJSONRPCRequestHandler(SimpleXMLRPCServer.SimpleXMLRPCRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Allow', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Cache-Control, Content-Language, Content-Type, Expires, Last-Modified, Pragma, Accept-Language, Accept, Origin')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        if not self.is_rpc_path_valid():
            self.report_404()
            return
        try:
            session_id = None
            c = self.headers.get('cookie')
            if c:
                if c[0:8] == 'SESSION=':
                    #print "found cookie", c[8:]
                    session_id = c[8:]

            if session_id is None:
                session_id = self.server.create_session()
                #print "setting cookie", session_id

            data = json.dumps([])
            response = self.server._marshaled_dispatch(session_id, data)
            self.send_response(200)
        except Exception, e:
            self.send_response(500)
            err_lines = traceback.format_exc().splitlines()
            trace_string = '%s | %s' % (err_lines[-3], err_lines[-1])
            fault = jsonrpclib.Fault(-32603, 'Server error: %s' % trace_string)
            response = fault.response()
            print "500", trace_string
        if response is None:
            response = ''

        if session_id:
            self.send_header("Set-Cookie", "SESSION=%s" % session_id)

        self.send_header("Content-type", "application/json-rpc")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)
        self.wfile.flush()
        self.shutdown_connection()

    def do_POST(self):
        if not self.is_rpc_path_valid():
            self.report_404()
            return
        try:
            max_chunk_size = 10*1024*1024
            size_remaining = int(self.headers["content-length"])
            L = []
            while size_remaining:
                chunk_size = min(size_remaining, max_chunk_size)
                L.append(self.rfile.read(chunk_size))
                size_remaining -= len(L[-1])
            data = ''.join(L)

            session_id = None
            c = self.headers.get('cookie')
            if c:
                if c[0:8] == 'SESSION=':
                    #print "found cookie", c[8:]
                    session_id = c[8:]

            if session_id is None:
                session_id = self.server.create_session()
                #print "setting cookie", session_id

            response = self.server._marshaled_dispatch(session_id, data)
            self.send_response(200)
        except Exception, e:
            self.send_response(500)
            err_lines = traceback.format_exc().splitlines()
            trace_string = '%s | %s' % (err_lines[-3], err_lines[-1])
            fault = jsonrpclib.Fault(-32603, 'Server error: %s' % trace_string)
            response = fault.response()
            print "500", trace_string
        if response is None:
            response = ''

        if session_id:
            self.send_header("Set-Cookie", "SESSION=%s" % session_id)

        self.send_header("Content-type", "application/json-rpc")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)
        self.wfile.flush()
        self.shutdown_connection()

    def shutdown_connection(self):
        self.connection.shutdown(1)


class SSLRequestHandler(StratumJSONRPCRequestHandler):
    def setup(self):
        self.connection = self.request
        self.rfile = socket._fileobject(self.request, "rb", self.rbufsize)
        self.wfile = socket._fileobject(self.request, "wb", self.wbufsize)

    def shutdown_connection(self):
        self.connection.shutdown()


class SSLTCPServer(SocketServer.TCPServer):
    def __init__(self, server_address, certfile, keyfile, RequestHandlerClass, bind_and_activate=True):
        SocketServer.BaseServer.__init__(self, server_address, RequestHandlerClass)
        ctx = SSL.Context(SSL.SSLv23_METHOD)
        ctx.use_privatekey_file(keyfile)
        ctx.use_certificate_file(certfile)
        self.socket = SSL.Connection(ctx, socket.socket(self.address_family, self.socket_type))
        if bind_and_activate:
            self.server_bind()
            self.server_activate()

    def shutdown_request(self, request):
        #request.shutdown()
        pass


class StratumHTTPServer(SocketServer.TCPServer, StratumJSONRPCDispatcher):

    allow_reuse_address = True

    def __init__(self, addr, requestHandler=StratumJSONRPCRequestHandler,
                 logRequests=False, encoding=None, bind_and_activate=True,
                 address_family=socket.AF_INET):
        self.logRequests = logRequests
        StratumJSONRPCDispatcher.__init__(self, encoding)
        # TCPServer.__init__ has an extra parameter on 2.6+, so
        # check Python version and decide on how to call it
        vi = sys.version_info
        self.address_family = address_family
        if USE_UNIX_SOCKETS and address_family == socket.AF_UNIX:
            # Unix sockets can't be bound if they already exist in the
            # filesystem. The convention of e.g. X11 is to unlink
            # before binding again.
            if os.path.exists(addr):
                try:
                    os.unlink(addr)
                except OSError:
                    logging.warning("Could not unlink socket %s", addr)

        SocketServer.TCPServer.__init__(self, addr, requestHandler, bind_and_activate)

        if fcntl is not None and hasattr(fcntl, 'FD_CLOEXEC'):
            flags = fcntl.fcntl(self.fileno(), fcntl.F_GETFD)
            flags |= fcntl.FD_CLOEXEC
            fcntl.fcntl(self.fileno(), fcntl.F_SETFD, flags)


class StratumHTTPSSLServer(SSLTCPServer, StratumJSONRPCDispatcher):

    allow_reuse_address = True

    def __init__(self, addr, certfile, keyfile,
                 requestHandler=SSLRequestHandler,
                 logRequests=False, encoding=None, bind_and_activate=True,
                 address_family=socket.AF_INET):

        self.logRequests = logRequests
        StratumJSONRPCDispatcher.__init__(self, encoding)
        # TCPServer.__init__ has an extra parameter on 2.6+, so
        # check Python version and decide on how to call it
        vi = sys.version_info
        self.address_family = address_family
        if USE_UNIX_SOCKETS and address_family == socket.AF_UNIX:
            # Unix sockets can't be bound if they already exist in the
            # filesystem. The convention of e.g. X11 is to unlink
            # before binding again.
            if os.path.exists(addr):
                try:
                    os.unlink(addr)
                except OSError:
                    logging.warning("Could not unlink socket %s", addr)

        SSLTCPServer.__init__(self, addr, certfile, keyfile, requestHandler, bind_and_activate)

        if fcntl is not None and hasattr(fcntl, 'FD_CLOEXEC'):
            flags = fcntl.fcntl(self.fileno(), fcntl.F_GETFD)
            flags |= fcntl.FD_CLOEXEC
            fcntl.fcntl(self.fileno(), fcntl.F_SETFD, flags)


class HttpSession(Session):

    def __init__(self, dispatcher, session_id):
        Session.__init__(self, dispatcher)
        self.pending_responses = Queue.Queue()
        self.address = session_id
        self.name = "HTTP"
        self.timeout = 60
        self.dispatcher.add_session(self)

    def send_response(self, response):
        raw_response = json.dumps(response)
        self.pending_responses.put(response)



class HttpServer(threading.Thread):
    def __init__(self, dispatcher, host, port, use_ssl, certfile, keyfile):
        self.shared = dispatcher.shared
        self.dispatcher = dispatcher.request_dispatcher
        threading.Thread.__init__(self)
        self.daemon = True
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.certfile = certfile
        self.keyfile = keyfile
        self.lock = threading.Lock()

    def run(self):
        # see http://code.google.com/p/jsonrpclib/
        from SocketServer import ThreadingMixIn
        if self.use_ssl:
            class StratumThreadedServer(ThreadingMixIn, StratumHTTPSSLServer):
                pass
            self.server = StratumThreadedServer((self.host, self.port), self.certfile, self.keyfile)
            print_log("HTTPS server started.")
        else:
            class StratumThreadedServer(ThreadingMixIn, StratumHTTPServer):
                pass
            self.server = StratumThreadedServer((self.host, self.port))
            print_log("HTTP server started.")

        self.server.dispatcher = self.dispatcher
        self.server.register_function(None, 'server.stop')
        self.server.register_function(None, 'server.info')

        self.server.serve_forever()

########NEW FILE########
__FILENAME__ = stratum_tcp
import json
import Queue as queue
import socket
import threading
import time
import traceback, sys

from processor import Session, Dispatcher
from utils import print_log


class TcpSession(Session):

    def __init__(self, dispatcher, connection, address, use_ssl, ssl_certfile, ssl_keyfile):
        Session.__init__(self, dispatcher)
        self.use_ssl = use_ssl
        if use_ssl:
            import ssl
            self._connection = ssl.wrap_socket(
                connection,
                server_side=True,
                certfile=ssl_certfile,
                keyfile=ssl_keyfile,
                ssl_version=ssl.PROTOCOL_SSLv23,
                do_handshake_on_connect=False)
        else:
            self._connection = connection

        self.address = address[0] + ":%d"%address[1]
        self.name = "TCP " if not use_ssl else "SSL "
        self.timeout = 1000
        self.response_queue = queue.Queue()
        self.dispatcher.add_session(self)

    def do_handshake(self):
        if self.use_ssl:
            self._connection.do_handshake()

    def connection(self):
        if self.stopped():
            raise Exception("Session was stopped")
        else:
            return self._connection

    def shutdown(self):
        try:
            self._connection.shutdown(socket.SHUT_RDWR)
        except:
            # print_log("problem shutting down", self.address)
            # traceback.print_exc(file=sys.stdout)
            pass

        self._connection.close()

    def send_response(self, response):
        self.response_queue.put(response)


class TcpClientResponder(threading.Thread):

    def __init__(self, session):
        self.session = session
        threading.Thread.__init__(self)

    def run(self):
        while not self.session.stopped():
            try:
                response = self.session.response_queue.get(timeout=10)
            except queue.Empty:
                continue
            data = json.dumps(response) + "\n"
            try:
                while data:
                    l = self.session.connection().send(data)
                    data = data[l:]
            except:
                self.session.stop()



class TcpClientRequestor(threading.Thread):

    def __init__(self, dispatcher, session):
        self.shared = dispatcher.shared
        self.dispatcher = dispatcher
        self.message = ""
        self.session = session
        threading.Thread.__init__(self)

    def run(self):
        try:
            self.session.do_handshake()
        except:
            self.session.stop()
            return

        while not self.shared.stopped():

            data = self.receive()
            if not data:
                self.session.stop()
                break

            self.message += data
            self.session.time = time.time()

            while self.parse():
                pass


    def receive(self):
        try:
            return self.session.connection().recv(2048)
        except:
            return ''

    def parse(self):
        raw_buffer = self.message.find('\n')
        if raw_buffer == -1:
            return False

        raw_command = self.message[0:raw_buffer].strip()
        self.message = self.message[raw_buffer + 1:]
        if raw_command == 'quit':
            self.session.stop()
            return False

        try:
            command = json.loads(raw_command)
        except:
            self.dispatcher.push_response(self.session, {"error": "bad JSON", "request": raw_command})
            return True

        try:
            # Try to load vital fields, and return an error if
            # unsuccessful.
            message_id = command['id']
            method = command['method']
        except KeyError:
            # Return an error JSON in response.
            self.dispatcher.push_response(self.session, {"error": "syntax error", "request": raw_command})
        else:
            self.dispatcher.push_request(self.session, command)
            # sleep a bit to prevent a single session from DOSing the queue
            time.sleep(0.01)

        return True


class TcpServer(threading.Thread):

    def __init__(self, dispatcher, host, port, use_ssl, ssl_certfile, ssl_keyfile):
        self.shared = dispatcher.shared
        self.dispatcher = dispatcher.request_dispatcher
        threading.Thread.__init__(self)
        self.daemon = True
        self.host = host
        self.port = port
        self.lock = threading.Lock()
        self.use_ssl = use_ssl
        self.ssl_keyfile = ssl_keyfile
        self.ssl_certfile = ssl_certfile

    def run(self):
        print_log( ("SSL" if self.use_ssl else "TCP") + " server started on port %d"%self.port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.listen(5)

        while not self.shared.stopped():

            #if self.use_ssl: print_log("SSL: socket listening")
            try:
                connection, address = sock.accept()
            except:
                traceback.print_exc(file=sys.stdout)
                time.sleep(0.1)
                continue

            #if self.use_ssl: print_log("SSL: new session", address)
            try:
                session = TcpSession(self.dispatcher, connection, address, use_ssl=self.use_ssl, ssl_certfile=self.ssl_certfile, ssl_keyfile=self.ssl_keyfile)
            except BaseException, e:
                error = str(e)
                print_log("cannot start TCP session", error, address)
                connection.close()
                time.sleep(0.1)
                continue

            client_req = TcpClientRequestor(self.dispatcher, session)
            client_req.start()
            responder = TcpClientResponder(session)
            responder.start()

########NEW FILE########
__FILENAME__ = version
VERSION = "0.9"

########NEW FILE########
