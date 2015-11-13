__FILENAME__ = config_sample
'''
This is example configuration for Stratum server.
Please rename it to settings.py and fill correct values.
'''

# ******************** GENERAL SETTINGS ***************

# Enable some verbose debug (logging requests and responses).
DEBUG = False

# Destination for application logs, files rotated once per day.
LOGDIR = 'log/'

# Main application log file.
LOGFILE = None#'stratum.log'

# Possible values: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOGLEVEL = 'INFO'

# How many threads use for synchronous methods (services).
# 30 is enough for small installation, for real usage
# it should be slightly more, say 100-300.
THREAD_POOL_SIZE = 10

ENABLE_EXAMPLE_SERVICE = True

# ******************** TRANSPORTS *********************

# Hostname or external IP to expose
HOSTNAME = 'localhost'

# Port used for Socket transport. Use 'None' for disabling the transport.
LISTEN_SOCKET_TRANSPORT = 3333

# Port used for HTTP Poll transport. Use 'None' for disabling the transport
LISTEN_HTTP_TRANSPORT = None

# Port used for HTTPS Poll transport
LISTEN_HTTPS_TRANSPORT = None

# Port used for WebSocket transport, 'None' for disabling WS
LISTEN_WS_TRANSPORT = None

# Port used for secure WebSocket, 'None' for disabling WSS
LISTEN_WSS_TRANSPORT = None

# Hostname and credentials for one trusted Bitcoin node ("Satoshi's client").
# Stratum uses both P2P port (which is 8333 already) and RPC port
BITCOIN_TRUSTED_HOST = 'localhost'
BITCOIN_TRUSTED_PORT = 8332
BITCOIN_TRUSTED_USER = 'user'
BITCOIN_TRUSTED_PASSWORD = 'somepassword'

# Use "echo -n '<yourpassword>' | sha256sum | cut -f1 -d' ' "
# for calculating SHA256 of your preferred password
ADMIN_PASSWORD_SHA256 = None
#ADMIN_PASSWORD_SHA256 = '9e6c0c1db1e0dfb3fa5159deb4ecd9715b3c8cd6b06bd4a3ad77e9a8c5694219' # SHA256 of the password

IRC_NICK = None

'''
DATABASE_DRIVER = 'MySQLdb'
DATABASE_HOST = 'localhost'
DATABASE_DBNAME = 'pooldb'
DATABASE_USER = 'pooldb'
DATABASE_PASSWORD = '**empty**'
'''

# Pool related settings
INSTANCE_ID = 31
CENTRAL_WALLET = 'set_valid_addresss_in_config!'
PREVHASH_REFRESH_INTERVAL = 5 # in sec
MERKLE_REFRESH_INTERVAL = 60 # How often check memorypool
COINBASE_EXTRAS = '/stratum/'

########NEW FILE########
__FILENAME__ = bitcoin_rpc
'''
    Implements simple interface to bitcoind's RPC.
'''

import simplejson as json
import base64
from twisted.internet import defer
from twisted.web import client

import stratum.logger
log = stratum.logger.get_logger('bitcoin_rpc')

class BitcoinRPC(object):

    def __init__(self, host, port, username, password):
        self.bitcoin_url = 'http://%s:%d' % (host, port)
        self.credentials = base64.b64encode("%s:%s" % (username, password))
        self.headers = {
            'Content-Type': 'text/json',
            'Authorization': 'Basic %s' % self.credentials,
        }

    def _call_raw(self, data):
        return client.getPage(
            url=self.bitcoin_url,
            method='POST',
            headers=self.headers,
            postdata=data,
        )

    def _call(self, method, params):
        return self._call_raw(json.dumps({
                'jsonrpc': '2.0',
                'method': method,
                'params': params,
                'id': '1',
            }))

    @defer.inlineCallbacks
    def submitblock(self, block_hex):
        resp = (yield self._call('submitblock', [block_hex,]))
        if json.loads(resp)['result'] == None:
            defer.returnValue(True)
        else:
            defer.returnValue(False)

    @defer.inlineCallbacks
    def getinfo(self):
         resp = (yield self._call('getinfo', []))
         defer.returnValue(json.loads(resp)['result'])

    @defer.inlineCallbacks
    def getblocktemplate(self):
        resp = (yield self._call('getblocktemplate', []))
        defer.returnValue(json.loads(resp)['result'])

    @defer.inlineCallbacks
    def prevhash(self):
        resp = (yield self._call('getwork', []))
        try:
            defer.returnValue(json.loads(resp)['result']['data'][8:72])
        except Exception as e:
            log.exception("Cannot decode prevhash %s" % str(e))
            raise

    @defer.inlineCallbacks
    def validateaddress(self, address):
        resp = (yield self._call('validateaddress', [address,]))
        defer.returnValue(json.loads(resp)['result'])

########NEW FILE########
__FILENAME__ = block_template
import StringIO
import binascii
import struct

import util
import merkletree
import halfnode
from coinbasetx import CoinbaseTransaction

# Remove dependency to settings, coinbase extras should be
# provided from coinbaser
from stratum import settings

class BlockTemplate(halfnode.CBlock):
    '''Template is used for generating new jobs for clients.
    Let's iterate extranonce1, extranonce2, ntime and nonce
    to find out valid bitcoin block!'''

    coinbase_transaction_class = CoinbaseTransaction

    def __init__(self, timestamper, coinbaser, job_id):
        super(BlockTemplate, self).__init__()

        self.job_id = job_id
        self.timestamper = timestamper
        self.coinbaser = coinbaser

        self.prevhash_bin = '' # reversed binary form of prevhash
        self.prevhash_hex = ''
        self.timedelta = 0
        self.curtime = 0
        self.target = 0
        #self.coinbase_hex = None
        self.merkletree = None

        self.broadcast_args = []

        # List of 4-tuples (extranonce1, extranonce2, ntime, nonce)
        # registers already submitted and checked shares
        # There may be registered also invalid shares inside!
        self.submits = []

    def fill_from_rpc(self, data):
        '''Convert getblocktemplate result into BlockTemplate instance'''

        #txhashes = [None] + [ binascii.unhexlify(t['hash']) for t in data['transactions'] ]
        txhashes = [None] + [ util.ser_uint256(int(t['hash'], 16)) for t in data['transactions'] ]
        mt = merkletree.MerkleTree(txhashes)

        coinbase = self.coinbase_transaction_class(self.timestamper, self.coinbaser, data['coinbasevalue'],
                        data['coinbaseaux']['flags'], data['height'], settings.COINBASE_EXTRAS)

        self.height = data['height']
        self.nVersion = data['version']
        self.hashPrevBlock = int(data['previousblockhash'], 16)
        self.nBits = int(data['bits'], 16)
        self.hashMerkleRoot = 0
        self.nTime = 0
        self.nNonce = 0
        self.vtx = [ coinbase, ]

        for tx in data['transactions']:
            t = halfnode.CTransaction()
            t.deserialize(StringIO.StringIO(binascii.unhexlify(tx['data'])))
            self.vtx.append(t)

        self.curtime = data['curtime']
        self.timedelta = self.curtime - int(self.timestamper.time())
        self.merkletree = mt
        self.target = util.uint256_from_compact(self.nBits)

        # Reversed prevhash
        self.prevhash_bin = binascii.unhexlify(util.reverse_hash(data['previousblockhash']))
        self.prevhash_hex = "%064x" % self.hashPrevBlock

        self.broadcast_args = self.build_broadcast_args()

    def register_submit(self, extranonce1, extranonce2, ntime, nonce):
        '''Client submitted some solution. Let's register it to
        prevent double submissions.'''

        t = (extranonce1, extranonce2, ntime, nonce)
        if t not in self.submits:
            self.submits.append(t)
            return True
        return False

    def build_broadcast_args(self):
        '''Build parameters of mining.notify call. All clients
        may receive the same params, because they include
        their unique extranonce1 into the coinbase, so every
        coinbase_hash (and then merkle_root) will be unique as well.'''
        job_id = self.job_id
        prevhash = binascii.hexlify(self.prevhash_bin)
        (coinb1, coinb2) = [ binascii.hexlify(x) for x in self.vtx[0]._serialized ]
        merkle_branch = [ binascii.hexlify(x) for x in self.merkletree._steps ]
        version = binascii.hexlify(struct.pack(">i", self.nVersion))
        nbits = binascii.hexlify(struct.pack(">I", self.nBits))
        ntime = binascii.hexlify(struct.pack(">I", self.curtime))
        clean_jobs = True

        return (job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs)

    def serialize_coinbase(self, extranonce1, extranonce2):
        '''Serialize coinbase with given extranonce1 and extranonce2
        in binary form'''
        (part1, part2) = self.vtx[0]._serialized
        return part1 + extranonce1 + extranonce2 + part2

    def check_ntime(self, ntime):
        '''Check for ntime restrictions.'''
        if ntime < self.curtime:
            return False

        if ntime > (self.timestamper.time() + 1000):
            # Be strict on ntime into the near future
            # may be unnecessary
            return False

        return True

    def serialize_header(self, merkle_root_int, ntime_bin, nonce_bin):
        '''Serialize header for calculating block hash'''
        r  = struct.pack(">i", self.nVersion)
        r += self.prevhash_bin
        r += util.ser_uint256_be(merkle_root_int)
        r += ntime_bin
        r += struct.pack(">I", self.nBits)
        r += nonce_bin
        return r

    def finalize(self, merkle_root_int, extranonce1_bin, extranonce2_bin, ntime, nonce):
        '''Take all parameters required to compile block candidate.
        self.is_valid() should return True then...'''

        self.hashMerkleRoot = merkle_root_int
        self.nTime = ntime
        self.nNonce = nonce
        self.vtx[0].set_extranonce(extranonce1_bin + extranonce2_bin)
        self.sha256 = None # We changed block parameters, let's reset sha256 cache

########NEW FILE########
__FILENAME__ = block_updater
from twisted.internet import reactor, defer
from stratum import settings

import util
from mining.interfaces import Interfaces

import stratum.logger
log = stratum.logger.get_logger('block_updater')

class BlockUpdater(object):
    '''
        Polls upstream's getinfo() and detecting new block on the network.
        This will call registry.update_block when new prevhash appear.

        This is just failback alternative when something
        with ./bitcoind -blocknotify will go wrong.
    '''

    def __init__(self, registry, bitcoin_rpc):
        self.bitcoin_rpc = bitcoin_rpc
        self.registry = registry
        self.clock = None
        self.schedule()

    def schedule(self):
        when = self._get_next_time()
        #log.debug("Next prevhash update in %.03f sec" % when)
        #log.debug("Merkle update in next %.03f sec" % \
        #          ((self.registry.last_update + settings.MERKLE_REFRESH_INTERVAL)-Interfaces.timestamper.time()))
        self.clock = reactor.callLater(when, self.run)

    def _get_next_time(self):
        when = settings.PREVHASH_REFRESH_INTERVAL - (Interfaces.timestamper.time() - self.registry.last_update) % \
               settings.PREVHASH_REFRESH_INTERVAL
        return when

    @defer.inlineCallbacks
    def run(self):
        update = False

        try:
            if self.registry.last_block:
                current_prevhash = "%064x" % self.registry.last_block.hashPrevBlock
            else:
                current_prevhash = None

            prevhash = util.reverse_hash((yield self.bitcoin_rpc.prevhash()))
            if prevhash and prevhash != current_prevhash:
                log.info("New block! Prevhash: %s" % prevhash)
                update = True

            elif Interfaces.timestamper.time() - self.registry.last_update >= settings.MERKLE_REFRESH_INTERVAL:
                log.info("Merkle update! Prevhash: %s" % prevhash)
                update = True

            if update:
                self.registry.update_block()

        except Exception:
            log.exception("UpdateWatchdog.run failed")
        finally:
            self.schedule()



########NEW FILE########
__FILENAME__ = coinbaser
import util
from twisted.internet import defer

import stratum.logger
log = stratum.logger.get_logger('coinbaser')

# TODO: Add on_* hooks in the app

class SimpleCoinbaser(object):
    '''This very simple coinbaser uses constant bitcoin address
    for all generated blocks.'''

    def __init__(self, bitcoin_rpc, address):
        # Fire callback when coinbaser is ready
        self.on_load = defer.Deferred()

        self.address = address
        self.is_valid = False # We need to check if pool can use this address

        self.bitcoin_rpc = bitcoin_rpc
        self._validate()

    def _validate(self):
        d = self.bitcoin_rpc.validateaddress(self.address)
        d.addCallback(self._address_check)
        d.addErrback(self._failure)

    def _address_check(self, result):
        if result['isvalid'] and result['ismine']:
            self.is_valid = True
            log.info("Coinbase address '%s' is valid" % self.address)

            if not self.on_load.called:
                self.on_load.callback(True)

        else:
            self.is_valid = False
            log.error("Coinbase address '%s' is NOT valid!" % self.address)

    def _failure(self, failure):
        log.error("Cannot validate Bitcoin address '%s'" % self.address)
        raise

    #def on_new_block(self):
    #    pass

    #def on_new_template(self):
    #    pass

    def get_script_pubkey(self):
        if not self.is_valid:
            # Try again, maybe bitcoind was down?
            self._validate()
            raise Exception("Coinbase address is not validated!")
        return util.script_to_address(self.address)

    def get_coinbase_data(self):
        return ''

########NEW FILE########
__FILENAME__ = coinbasetx
import binascii
import halfnode
import struct
import util

class CoinbaseTransaction(halfnode.CTransaction):
    '''Construct special transaction used for coinbase tx.
    It also implements quick serialization using pre-cached
    scriptSig template.'''

    extranonce_type = '>Q'
    extranonce_placeholder = struct.pack(extranonce_type, int('f000000ff111111f', 16))
    extranonce_size = struct.calcsize(extranonce_type)

    def __init__(self, timestamper, coinbaser, value, flags, height, data):
        super(CoinbaseTransaction, self).__init__()

        #self.extranonce = 0

        if len(self.extranonce_placeholder) != self.extranonce_size:
            raise Exception("Extranonce placeholder don't match expected length!")

        tx_in = halfnode.CTxIn()
        tx_in.prevout.hash = 0L
        tx_in.prevout.n = 2**32-1
        tx_in._scriptSig_template = (
            util.ser_number(height) + binascii.unhexlify(flags) + util.ser_number(int(timestamper.time())) + \
            chr(self.extranonce_size),
            util.ser_string(coinbaser.get_coinbase_data() + data)
        )

        tx_in.scriptSig = tx_in._scriptSig_template[0] + self.extranonce_placeholder + tx_in._scriptSig_template[1]

        tx_out = halfnode.CTxOut()
        tx_out.nValue = value
        tx_out.scriptPubKey = coinbaser.get_script_pubkey()

        self.vin.append(tx_in)
        self.vout.append(tx_out)

        # Two parts of serialized coinbase, just put part1 + extranonce + part2 to have final serialized tx
        self._serialized = super(CoinbaseTransaction, self).serialize().split(self.extranonce_placeholder)

    def set_extranonce(self, extranonce):
        if len(extranonce) != self.extranonce_size:
            raise Exception("Incorrect extranonce size")

        (part1, part2) = self.vin[0]._scriptSig_template
        self.vin[0].scriptSig = part1 + extranonce + part2

########NEW FILE########
__FILENAME__ = exceptions
from stratum.custom_exceptions import ServiceException

class SubmitException(ServiceException):
    pass
########NEW FILE########
__FILENAME__ = extranonce_counter
import struct

class ExtranonceCounter(object):
    '''Implementation of a counter producing
       unique extranonce across all pool instances.
       This is just dumb "quick&dirty" solution,
       but it can be changed at any time without breaking anything.'''

    def __init__(self, instance_id):
        if instance_id < 0 or instance_id > 31:
            raise Exception("Current ExtranonceCounter implementation needs an instance_id in <0, 31>.")

        # Last 5 most-significant bits represents instance_id
        # The rest is just an iterator of jobs.
        self.counter = instance_id << 27
        self.size = struct.calcsize('>L')

    def get_size(self):
        '''Return expected size of generated extranonce in bytes'''
        return self.size

    def get_new_bin(self):
        self.counter += 1
        return struct.pack('>L', self.counter)


########NEW FILE########
__FILENAME__ = halfnode
#!/usr/bin/python
# Public Domain
# Original author: ArtForz
# Twisted integration: slush

import struct
import socket
import binascii
import time
import sys
import random
import cStringIO
from Crypto.Hash import SHA256

from twisted.internet.protocol import Protocol
from util import *

MY_VERSION = 31402
MY_SUBVERSION = ".4"

class CAddress(object):
    def __init__(self):
        self.nTime = 0
        self.nServices = 1
        self.pchReserved = "\x00" * 10 + "\xff" * 2
        self.ip = "0.0.0.0"
        self.port = 0
    def deserialize(self, f):
        #self.nTime = struct.unpack("<I", f.read(4))[0]
        self.nServices = struct.unpack("<Q", f.read(8))[0]
        self.pchReserved = f.read(12)
        self.ip = socket.inet_ntoa(f.read(4))
        self.port = struct.unpack(">H", f.read(2))[0]
    def serialize(self):
        r = ""
        #r += struct.pack("<I", self.nTime)
        r += struct.pack("<Q", self.nServices)
        r += self.pchReserved
        r += socket.inet_aton(self.ip)
        r += struct.pack(">H", self.port)
        return r
    def __repr__(self):
        return "CAddress(nServices=%i ip=%s port=%i)" % (self.nServices, self.ip, self.port)

class CInv(object):
    typemap = {
        0: "Error",
        1: "TX",
        2: "Block"}
    def __init__(self):
        self.type = 0
        self.hash = 0L
    def deserialize(self, f):
        self.type = struct.unpack("<i", f.read(4))[0]
        self.hash = deser_uint256(f)
    def serialize(self):
        r = ""
        r += struct.pack("<i", self.type)
        r += ser_uint256(self.hash)
        return r
    def __repr__(self):
        return "CInv(type=%s hash=%064x)" % (self.typemap[self.type], self.hash)

class CBlockLocator(object):
    def __init__(self):
        self.nVersion = MY_VERSION
        self.vHave = []
    def deserialize(self, f):
        self.nVersion = struct.unpack("<i", f.read(4))[0]
        self.vHave = deser_uint256_vector(f)
    def serialize(self):
        r = ""
        r += struct.pack("<i", self.nVersion)
        r += ser_uint256_vector(self.vHave)
        return r
    def __repr__(self):
        return "CBlockLocator(nVersion=%i vHave=%s)" % (self.nVersion, repr(self.vHave))

class COutPoint(object):
    def __init__(self):
        self.hash = 0
        self.n = 0
    def deserialize(self, f):
        self.hash = deser_uint256(f)
        self.n = struct.unpack("<I", f.read(4))[0]
    def serialize(self):
        r = ""
        r += ser_uint256(self.hash)
        r += struct.pack("<I", self.n)
        return r
    def __repr__(self):
        return "COutPoint(hash=%064x n=%i)" % (self.hash, self.n)

class CTxIn(object):
    def __init__(self):
        self.prevout = COutPoint()
        self.scriptSig = ""
        self.nSequence = 0
    def deserialize(self, f):
        self.prevout = COutPoint()
        self.prevout.deserialize(f)
        self.scriptSig = deser_string(f)
        self.nSequence = struct.unpack("<I", f.read(4))[0]
    def serialize(self):
        r = ""
        r += self.prevout.serialize()
        r += ser_string(self.scriptSig)
        r += struct.pack("<I", self.nSequence)
        return r
    def __repr__(self):
        return "CTxIn(prevout=%s scriptSig=%s nSequence=%i)" % (repr(self.prevout), binascii.hexlify(self.scriptSig), self.nSequence)

class CTxOut(object):
    def __init__(self):
        self.nValue = 0
        self.scriptPubKey = ""
    def deserialize(self, f):
        self.nValue = struct.unpack("<q", f.read(8))[0]
        self.scriptPubKey = deser_string(f)
    def serialize(self):
        r = ""
        r += struct.pack("<q", self.nValue)
        r += ser_string(self.scriptPubKey)
        return r
    def __repr__(self):
        return "CTxOut(nValue=%i.%08i scriptPubKey=%s)" % (self.nValue // 100000000, self.nValue % 100000000, binascii.hexlify(self.scriptPubKey))

class CTransaction(object):
    def __init__(self):
        self.nVersion = 1
        self.vin = []
        self.vout = []
        self.nLockTime = 0
        self.sha256 = None
    def deserialize(self, f):
        self.nVersion = struct.unpack("<i", f.read(4))[0]
        self.vin = deser_vector(f, CTxIn)
        self.vout = deser_vector(f, CTxOut)
        self.nLockTime = struct.unpack("<I", f.read(4))[0]
        self.sha256 = None
    def serialize(self):
        r = ""
        r += struct.pack("<i", self.nVersion)
        r += ser_vector(self.vin)
        r += ser_vector(self.vout)
        r += struct.pack("<I", self.nLockTime)
        return r

    def calc_sha256(self):
        if self.sha256 is None:
            self.sha256 = uint256_from_str(SHA256.new(SHA256.new(self.serialize()).digest()).digest())
        return self.sha256

    def is_valid(self):
        self.calc_sha256()
        for tout in self.vout:
            if tout.nValue < 0 or tout.nValue > 21000000L * 100000000L:
                return False
        return True
    def __repr__(self):
        return "CTransaction(nVersion=%i vin=%s vout=%s nLockTime=%i)" % (self.nVersion, repr(self.vin), repr(self.vout), self.nLockTime)

class CBlock(object):
    def __init__(self):
        self.nVersion = 1
        self.hashPrevBlock = 0
        self.hashMerkleRoot = 0
        self.nTime = 0
        self.nBits = 0
        self.nNonce = 0
        self.vtx = []
        self.sha256 = None
    def deserialize(self, f):
        self.nVersion = struct.unpack("<i", f.read(4))[0]
        self.hashPrevBlock = deser_uint256(f)
        self.hashMerkleRoot = deser_uint256(f)
        self.nTime = struct.unpack("<I", f.read(4))[0]
        self.nBits = struct.unpack("<I", f.read(4))[0]
        self.nNonce = struct.unpack("<I", f.read(4))[0]
        self.vtx = deser_vector(f, CTransaction)
    def serialize(self):
        r = []
        r.append(struct.pack("<i", self.nVersion))
        r.append(ser_uint256(self.hashPrevBlock))
        r.append(ser_uint256(self.hashMerkleRoot))
        r.append(struct.pack("<I", self.nTime))
        r.append(struct.pack("<I", self.nBits))
        r.append(struct.pack("<I", self.nNonce))
        r.append(ser_vector(self.vtx))
        return ''.join(r)
    def calc_sha256(self):
        if self.sha256 is None:
            r = []
            r.append(struct.pack("<i", self.nVersion))
            r.append(ser_uint256(self.hashPrevBlock))
            r.append(ser_uint256(self.hashMerkleRoot))
            r.append(struct.pack("<I", self.nTime))
            r.append(struct.pack("<I", self.nBits))
            r.append(struct.pack("<I", self.nNonce))
            self.sha256 = uint256_from_str(SHA256.new(SHA256.new(''.join(r)).digest()).digest())
        return self.sha256

    def is_valid(self):
        self.calc_sha256()
        target = uint256_from_compact(self.nBits)
        if self.sha256 > target:
            return False
        hashes = []
        for tx in self.vtx:
            tx.sha256 = None
            if not tx.is_valid():
                return False
            tx.calc_sha256()
            hashes.append(ser_uint256(tx.sha256))

        while len(hashes) > 1:
            newhashes = []
            for i in xrange(0, len(hashes), 2):
                i2 = min(i+1, len(hashes)-1)
                newhashes.append(SHA256.new(SHA256.new(hashes[i] + hashes[i2]).digest()).digest())
            hashes = newhashes

        if uint256_from_str(hashes[0]) != self.hashMerkleRoot:
            return False
        return True
    def __repr__(self):
        return "CBlock(nVersion=%i hashPrevBlock=%064x hashMerkleRoot=%064x nTime=%s nBits=%08x nNonce=%08x vtx=%s)" % (self.nVersion, self.hashPrevBlock, self.hashMerkleRoot, time.ctime(self.nTime), self.nBits, self.nNonce, repr(self.vtx))

class msg_version(object):
    command = "version"
    def __init__(self):
        self.nVersion = MY_VERSION
        self.nServices = 0
        self.nTime = time.time()
        self.addrTo = CAddress()
        self.addrFrom = CAddress()
        self.nNonce = random.getrandbits(64)
        self.strSubVer = MY_SUBVERSION
        self.nStartingHeight = 0

    def deserialize(self, f):
        self.nVersion = struct.unpack("<i", f.read(4))[0]
        if self.nVersion == 10300:
            self.nVersion = 300
        self.nServices = struct.unpack("<Q", f.read(8))[0]
        self.nTime = struct.unpack("<q", f.read(8))[0]
        self.addrTo = CAddress()
        self.addrTo.deserialize(f)
        self.addrFrom = CAddress()
        self.addrFrom.deserialize(f)
        self.nNonce = struct.unpack("<Q", f.read(8))[0]
        self.strSubVer = deser_string(f)
        self.nStartingHeight = struct.unpack("<i", f.read(4))[0]
    def serialize(self):
        r = []
        r.append(struct.pack("<i", self.nVersion))
        r.append(struct.pack("<Q", self.nServices))
        r.append(struct.pack("<q", self.nTime))
        r.append(self.addrTo.serialize())
        r.append(self.addrFrom.serialize())
        r.append(struct.pack("<Q", self.nNonce))
        r.append(ser_string(self.strSubVer))
        r.append(struct.pack("<i", self.nStartingHeight))
        return ''.join(r)
    def __repr__(self):
        return "msg_version(nVersion=%i nServices=%i nTime=%s addrTo=%s addrFrom=%s nNonce=0x%016X strSubVer=%s nStartingHeight=%i)" % (self.nVersion, self.nServices, time.ctime(self.nTime), repr(self.addrTo), repr(self.addrFrom), self.nNonce, self.strSubVer, self.nStartingHeight)

class msg_verack(object):
    command = "verack"
    def __init__(self):
        pass
    def deserialize(self, f):
        pass
    def serialize(self):
        return ""
    def __repr__(self):
        return "msg_verack()"

class msg_addr(object):
    command = "addr"
    def __init__(self):
        self.addrs = []
    def deserialize(self, f):
        self.addrs = deser_vector(f, CAddress)
    def serialize(self):
        return ser_vector(self.addrs)
    def __repr__(self):
        return "msg_addr(addrs=%s)" % (repr(self.addrs))

class msg_inv(object):
    command = "inv"
    def __init__(self):
        self.inv = []
    def deserialize(self, f):
        self.inv = deser_vector(f, CInv)
    def serialize(self):
        return ser_vector(self.inv)
    def __repr__(self):
        return "msg_inv(inv=%s)" % (repr(self.inv))

class msg_getdata(object):
    command = "getdata"
    def __init__(self):
        self.inv = []
    def deserialize(self, f):
        self.inv = deser_vector(f, CInv)
    def serialize(self):
        return ser_vector(self.inv)
    def __repr__(self):
        return "msg_getdata(inv=%s)" % (repr(self.inv))

class msg_getblocks(object):
    command = "getblocks"
    def __init__(self):
        self.locator = CBlockLocator()
        self.hashstop = 0L
    def deserialize(self, f):
        self.locator = CBlockLocator()
        self.locator.deserialize(f)
        self.hashstop = deser_uint256(f)
    def serialize(self):
        r = []
        r.append(self.locator.serialize())
        r.append(ser_uint256(self.hashstop))
        return ''.join(r)
    def __repr__(self):
        return "msg_getblocks(locator=%s hashstop=%064x)" % (repr(self.locator), self.hashstop)

class msg_tx(object):
    command = "tx"
    def __init__(self):
        self.tx = CTransaction()
    def deserialize(self, f):
        self.tx.deserialize(f)
    def serialize(self):
        return self.tx.serialize()
    def __repr__(self):
        return "msg_tx(tx=%s)" % (repr(self.tx))

class msg_block(object):
    command = "block"
    def __init__(self):
        self.block = CBlock()
    def deserialize(self, f):
        self.block.deserialize(f)
    def serialize(self):
        return self.block.serialize()
    def __repr__(self):
        return "msg_block(block=%s)" % (repr(self.block))

class msg_getaddr(object):
    command = "getaddr"
    def __init__(self):
        pass
    def deserialize(self, f):
        pass
    def serialize(self):
        return ""
    def __repr__(self):
        return "msg_getaddr()"

class msg_ping(object):
    command = "ping"
    def __init__(self):
        pass
    def deserialize(self, f):
        pass
    def serialize(self):
        return ""
    def __repr__(self):
        return "msg_ping()"

class msg_alert(object):
    command = "alert"
    def __init__(self):
        pass
    def deserialize(self, f):
        pass
    def serialize(self):
        return ""
    def __repr__(self):
        return "msg_alert()"

class BitcoinP2PProtocol(Protocol):
    messagemap = {
        "version": msg_version,
        "verack": msg_verack,
        "addr": msg_addr,
        "inv": msg_inv,
        "getdata": msg_getdata,
        "getblocks": msg_getblocks,
        "tx": msg_tx,
        "block": msg_block,
        "getaddr": msg_getaddr,
        "ping": msg_ping,
        "alert": msg_alert,
    }

    def connectionMade(self):
        peer = self.transport.getPeer()
        self.dstaddr = peer.host
        self.dstport = peer.port
        self.recvbuf = ""
        self.last_sent = 0

        t = msg_version()
        t.nStartingHeight = getattr(self, 'nStartingHeight', 0)
        t.addrTo.ip = self.dstaddr
        t.addrTo.port = self.dstport
        t.addrTo.nTime = time.time()
        t.addrFrom.ip = "0.0.0.0"
        t.addrFrom.port = 0
        t.addrFrom.nTime = time.time()
        self.send_message(t)

    def dataReceived(self, data):
        self.recvbuf += data
        self.got_data()

    def got_data(self):
        while True:
            if len(self.recvbuf) < 4:
                return
            if self.recvbuf[:4] != "\xf9\xbe\xb4\xd9":
                raise ValueError("got garbage %s" % repr(self.recvbuf))

            if len(self.recvbuf) < 4 + 12 + 4 + 4:
                return
            command = self.recvbuf[4:4+12].split("\x00", 1)[0]
            msglen = struct.unpack("<i", self.recvbuf[4+12:4+12+4])[0]
            checksum = self.recvbuf[4+12+4:4+12+4+4]
            if len(self.recvbuf) < 4 + 12 + 4 + 4 + msglen:
                return
            msg = self.recvbuf[4+12+4+4:4+12+4+4+msglen]
            th = SHA256.new(msg).digest()
            h = SHA256.new(th).digest()
            if checksum != h[:4]:
                raise ValueError("got bad checksum %s" % repr(self.recvbuf))
            self.recvbuf = self.recvbuf[4+12+4+4+msglen:]

            if command in self.messagemap:
                f = cStringIO.StringIO(msg)
                t = self.messagemap[command]()
                t.deserialize(f)
                self.got_message(t)
            else:
                print "UNKNOWN COMMAND", command, repr(msg)

    def prepare_message(self, message):
        command = message.command
        data = message.serialize()
        tmsg = "\xf9\xbe\xb4\xd9"
        tmsg += command
        tmsg += "\x00" * (12 - len(command))
        tmsg += struct.pack("<I", len(data))
        th = SHA256.new(data).digest()
        h = SHA256.new(th).digest()
        tmsg += h[:4]
        tmsg += data
        return tmsg

    def send_serialized_message(self, tmsg):
        if not self.connected:
            return

        self.transport.write(tmsg)
        self.last_sent = time.time()

    def send_message(self, message):
        if not self.connected:
            return

        #print message.command

        #print "send %s" % repr(message)
        command = message.command
        data = message.serialize()
        tmsg = "\xf9\xbe\xb4\xd9"
        tmsg += command
        tmsg += "\x00" * (12 - len(command))
        tmsg += struct.pack("<I", len(data))
        th = SHA256.new(data).digest()
        h = SHA256.new(th).digest()
        tmsg += h[:4]
        tmsg += data

        #print tmsg, len(tmsg)
        self.transport.write(tmsg)
        self.last_sent = time.time()

    def got_message(self, message):
        if self.last_sent + 30 * 60 < time.time():
            self.send_message(msg_ping())

        mname = 'do_' + message.command
        #print mname
        if not hasattr(self, mname):
            return

        method = getattr(self, mname)
        method(message)

#        if message.command == "tx":
#            message.tx.calc_sha256()
#            sha256 = message.tx.sha256
#            pubkey = binascii.hexlify(message.tx.vout[0].scriptPubKey)
#            txlock.acquire()
#            tx.append([str(sha256), str(time.time()), str(self.dstaddr), pubkey])
#            txlock.release()

    def do_version(self, message):
        #print message
        self.send_message(msg_verack())

    def do_inv(self, message):
        want = msg_getdata()
        for i in message.inv:
            if i.type == 1:
                want.inv.append(i)
            if i.type == 2:
                want.inv.append(i)
        if len(want.inv):
            self.send_message(want)

########NEW FILE########
__FILENAME__ = merkletree
# Eloipool - Python Bitcoin pool server
# Copyright (C) 2011-2012  Luke Dashjr <luke-jr+eloipool@utopios.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from hashlib import sha256
from util import doublesha

class MerkleTree:
    def __init__(self, data, detailed=False):
        self.data = data
        self.recalculate(detailed)
        self._hash_steps = None

    def recalculate(self, detailed=False):
        L = self.data
        steps = []
        if detailed:
            detail = []
            PreL = []
            StartL = 0
        else:
            detail = None
            PreL = [None]
            StartL = 2
        Ll = len(L)
        if detailed or Ll > 1:
            while True:
                if detailed:
                    detail += L
                if Ll == 1:
                    break
                steps.append(L[1])
                if Ll % 2:
                    L += [L[-1]]
                L = PreL + [doublesha(L[i] + L[i + 1]) for i in range(StartL, Ll, 2)]
                Ll = len(L)
        self._steps = steps
        self.detail = detail

    def hash_steps(self):
        if self._hash_steps == None:
            self._hash_steps = doublesha(''.join(self._steps))
        return self._hash_steps

    def withFirst(self, f):
        steps = self._steps
        for s in steps:
            f = doublesha(f + s)
        return f

    def merkleRoot(self):
        return self.withFirst(self.data[0])

# MerkleTree tests
def _test():
    import binascii
    import time

    mt = MerkleTree([None] + [binascii.unhexlify(a) for a in [
        '999d2c8bb6bda0bf784d9ebeb631d711dbbbfe1bc006ea13d6ad0d6a2649a971',
        '3f92594d5a3d7b4df29d7dd7c46a0dac39a96e751ba0fc9bab5435ea5e22a19d',
        'a5633f03855f541d8e60a6340fc491d49709dc821f3acb571956a856637adcb6',
        '28d97c850eaf917a4c76c02474b05b70a197eaefb468d21c22ed110afe8ec9e0',
    ]])
    assert(
        b'82293f182d5db07d08acf334a5a907012bbb9990851557ac0ec028116081bd5a' ==
        binascii.b2a_hex(mt.withFirst(binascii.unhexlify('d43b669fb42cfa84695b844c0402d410213faa4f3e66cb7248f688ff19d5e5f7')))
    )

    print '82293f182d5db07d08acf334a5a907012bbb9990851557ac0ec028116081bd5a'
    txes = [binascii.unhexlify(a) for a in [
        'd43b669fb42cfa84695b844c0402d410213faa4f3e66cb7248f688ff19d5e5f7',
        '999d2c8bb6bda0bf784d9ebeb631d711dbbbfe1bc006ea13d6ad0d6a2649a971',
        '3f92594d5a3d7b4df29d7dd7c46a0dac39a96e751ba0fc9bab5435ea5e22a19d',
        'a5633f03855f541d8e60a6340fc491d49709dc821f3acb571956a856637adcb6',
        '28d97c850eaf917a4c76c02474b05b70a197eaefb468d21c22ed110afe8ec9e0',
    ]]

    s = time.time()
    mt = MerkleTree(txes)
    for x in range(100):
        y = int('d43b669fb42cfa84695b844c0402d410213faa4f3e66cb7248f688ff19d5e5f7', 16)
        #y += x
        coinbasehash = binascii.unhexlify("%x" % y)
        x = binascii.b2a_hex(mt.withFirst(coinbasehash))

    print x
    print time.time() - s

if __name__ == '__main__':
    _test()

########NEW FILE########
__FILENAME__ = template_registry
import weakref
import binascii
import util
import StringIO

from twisted.internet import defer
from lib.exceptions import SubmitException

import stratum.logger
log = stratum.logger.get_logger('template_registry')

from mining.interfaces import Interfaces
from extranonce_counter import ExtranonceCounter

class JobIdGenerator(object):
    '''Generate pseudo-unique job_id. It does not need to be absolutely unique,
    because pool sends "clean_jobs" flag to clients and they should drop all previous jobs.'''
    counter = 0

    @classmethod
    def get_new_id(cls):
        cls.counter += 1
        if cls.counter % 0xffff == 0:
            cls.counter = 1
        return "%x" % cls.counter

class TemplateRegistry(object):
    '''Implements the main logic of the pool. Keep track
    on valid block templates, provide internal interface for stratum
    service and implements block validation and submits.'''

    def __init__(self, block_template_class, coinbaser, bitcoin_rpc, instance_id,
                 on_template_callback, on_block_callback):
        self.prevhashes = {}
        self.jobs = weakref.WeakValueDictionary()

        self.extranonce_counter = ExtranonceCounter(instance_id)
        self.extranonce2_size = block_template_class.coinbase_transaction_class.extranonce_size \
                - self.extranonce_counter.get_size()

        self.coinbaser = coinbaser
        self.block_template_class = block_template_class
        self.bitcoin_rpc = bitcoin_rpc
        self.on_block_callback = on_block_callback
        self.on_template_callback = on_template_callback

        self.last_block = None
        self.update_in_progress = False
        self.last_update = None

        # Create first block template on startup
        self.update_block()

    def get_new_extranonce1(self):
        '''Generates unique extranonce1 (e.g. for newly
        subscribed connection.'''
        return self.extranonce_counter.get_new_bin()

    def get_last_broadcast_args(self):
        '''Returns arguments for mining.notify
        from last known template.'''
        return self.last_block.broadcast_args

    def add_template(self, block):
        '''Adds new template to the registry.
        It also clean up templates which should
        not be used anymore.'''

        prevhash = block.prevhash_hex

        if prevhash in self.prevhashes.keys():
            new_block = False
        else:
            new_block = True
            self.prevhashes[prevhash] = []

        # Blocks sorted by prevhash, so it's easy to drop
        # them on blockchain update
        self.prevhashes[prevhash].append(block)

        # Weak reference for fast lookup using job_id
        self.jobs[block.job_id] = block

        # Use this template for every new request
        self.last_block = block

        # Drop templates of obsolete blocks
        for ph in self.prevhashes.keys():
            if ph != prevhash:
                del self.prevhashes[ph]

        log.info("New template for %s" % prevhash)

        if new_block:
            # Tell the system about new block
            # It is mostly important for share manager
            self.on_block_callback(prevhash)

        # Everything is ready, let's broadcast jobs!
        self.on_template_callback(new_block)


        #from twisted.internet import reactor
        #reactor.callLater(10, self.on_block_callback, new_block)

    def update_block(self):
        '''Registry calls the getblocktemplate() RPC
        and build new block template.'''

        if self.update_in_progress:
            # Block has been already detected
            return

        self.update_in_progress = True
        self.last_update = Interfaces.timestamper.time()

        d = self.bitcoin_rpc.getblocktemplate()
        d.addCallback(self._update_block)
        d.addErrback(self._update_block_failed)

    def _update_block_failed(self, failure):
        log.error(str(failure))
        self.update_in_progress = False

    def _update_block(self, data):
        start = Interfaces.timestamper.time()

        template = self.block_template_class(Interfaces.timestamper, self.coinbaser, JobIdGenerator.get_new_id())
        template.fill_from_rpc(data)
        self.add_template(template)

        log.info("Update finished, %.03f sec, %d txes" % \
                    (Interfaces.timestamper.time() - start, len(template.vtx)))

        self.update_in_progress = False
        return data

    def diff_to_target(self, difficulty):
        '''Converts difficulty to target'''
        diff1 = 0x00000000ffff0000000000000000000000000000000000000000000000000000
        return diff1 / difficulty

    def get_job(self, job_id):
        '''For given job_id returns BlockTemplate instance or None'''
        try:
            j = self.jobs[job_id]
        except:
            log.info("Job id '%s' not found" % job_id)
            return None

        # Now we have to check if job is still valid.
        # Unfortunately weak references are not bulletproof and
        # old reference can be found until next run of garbage collector.
        if j.prevhash_hex not in self.prevhashes:
            log.info("Prevhash of job '%s' is unknown" % job_id)
            return None

        if j not in self.prevhashes[j.prevhash_hex]:
            log.info("Job %s is unknown" % job_id)
            return None

        return j

    def submit_share(self, job_id, worker_name, extranonce1_bin, extranonce2, ntime, nonce,
                     difficulty):
        '''Check parameters and finalize block template. If it leads
           to valid block candidate, asynchronously submits the block
           back to the bitcoin network.

            - extranonce1_bin is binary. No checks performed, it should be from session data
            - job_id, extranonce2, ntime, nonce - in hex form sent by the client
            - difficulty - decimal number from session, again no checks performed
            - submitblock_callback - reference to method which receive result of submitblock()
        '''

        # Check if extranonce2 looks correctly. extranonce2 is in hex form...
        if len(extranonce2) != self.extranonce2_size * 2:
            raise SubmitException("Incorrect size of extranonce2. Expected %d chars" % (self.extranonce2_size*2))

        # Check for job
        job = self.get_job(job_id)
        if job == None:
            raise SubmitException("Job '%s' not found" % job_id)

        # Check if ntime looks correct
        if len(ntime) != 8:
            raise SubmitException("Incorrect size of ntime. Expected 8 chars")

        if not job.check_ntime(int(ntime, 16)):
            raise SubmitException("Ntime out of range")

        # Check nonce
        if len(nonce) != 8:
            raise SubmitException("Incorrect size of nonce. Expected 8 chars")

        # Check for duplicated submit
        if not job.register_submit(extranonce1_bin, extranonce2, ntime, nonce):
            log.info("Duplicate from %s, (%s %s %s %s)" % \
                    (worker_name, binascii.hexlify(extranonce1_bin), extranonce2, ntime, nonce))
            raise SubmitException("Duplicate share")

        # Now let's do the hard work!
        # ---------------------------

        # 0. Some sugar
        extranonce2_bin = binascii.unhexlify(extranonce2)
        ntime_bin = binascii.unhexlify(ntime)
        nonce_bin = binascii.unhexlify(nonce)

        # 1. Build coinbase
        coinbase_bin = job.serialize_coinbase(extranonce1_bin, extranonce2_bin)
        coinbase_hash = util.doublesha(coinbase_bin)

        # 2. Calculate merkle root
        merkle_root_bin = job.merkletree.withFirst(coinbase_hash)
        merkle_root_int = util.uint256_from_str(merkle_root_bin)

        # 3. Serialize header with given merkle, ntime and nonce
        header_bin = job.serialize_header(merkle_root_int, ntime_bin, nonce_bin)

        # 4. Reverse header and compare it with target of the user
        hash_bin = util.doublesha(''.join([ header_bin[i*4:i*4+4][::-1] for i in range(0, 20) ]))
        hash_int = util.uint256_from_str(hash_bin)
        block_hash_hex = "%064x" % hash_int
        header_hex = binascii.hexlify(header_bin)

        target_user = self.diff_to_target(difficulty)
        if hash_int > target_user:
            raise SubmitException("Share is above target")

        # Mostly for debugging purposes
        target_info = self.diff_to_target(100000)
        if hash_int <= target_info:
            log.info("Yay, share with diff above 100000")

        # 5. Compare hash with target of the network
        if hash_int <= job.target:
            # Yay! It is block candidate!
            log.info("We found a block candidate! %s" % block_hash_hex)

            # 6. Finalize and serialize block object
            job.finalize(merkle_root_int, extranonce1_bin, extranonce2_bin, int(ntime, 16), int(nonce, 16))

            if not job.is_valid():
                # Should not happen
                log.error("Final job validation failed!")

            # 7. Submit block to the network
            serialized = binascii.hexlify(job.serialize())
            on_submit = self.bitcoin_rpc.submitblock(serialized)

            return (header_hex, block_hash_hex, on_submit)

        return (header_hex, block_hash_hex, None)

########NEW FILE########
__FILENAME__ = util
'''Various helper methods. It probably needs some cleanup.'''

import struct
import StringIO
import binascii
from hashlib import sha256

def deser_string(f):
    nit = struct.unpack("<B", f.read(1))[0]
    if nit == 253:
        nit = struct.unpack("<H", f.read(2))[0]
    elif nit == 254:
        nit = struct.unpack("<I", f.read(4))[0]
    elif nit == 255:
        nit = struct.unpack("<Q", f.read(8))[0]
    return f.read(nit)

def ser_string(s):
    if len(s) < 253:
        return chr(len(s)) + s
    elif len(s) < 0x10000:
        return chr(253) + struct.pack("<H", len(s)) + s
    elif len(s) < 0x100000000L:
        return chr(254) + struct.pack("<I", len(s)) + s
    return chr(255) + struct.pack("<Q", len(s)) + s

def deser_uint256(f):
    r = 0L
    for i in xrange(8):
        t = struct.unpack("<I", f.read(4))[0]
        r += t << (i * 32)
    return r

def ser_uint256(u):
    rs = ""
    for i in xrange(8):
        rs += struct.pack("<I", u & 0xFFFFFFFFL)
        u >>= 32
    return rs

def uint256_from_str(s):
    r = 0L
    t = struct.unpack("<IIIIIIII", s[:32])
    for i in xrange(8):
        r += t[i] << (i * 32)
    return r

def uint256_from_str_be(s):
    r = 0L
    t = struct.unpack(">IIIIIIII", s[:32])
    for i in xrange(8):
        r += t[i] << (i * 32)
    return r

def uint256_from_compact(c):
    nbytes = (c >> 24) & 0xFF
    v = (c & 0xFFFFFFL) << (8 * (nbytes - 3))
    return v

def deser_vector(f, c):
    nit = struct.unpack("<B", f.read(1))[0]
    if nit == 253:
        nit = struct.unpack("<H", f.read(2))[0]
    elif nit == 254:
        nit = struct.unpack("<I", f.read(4))[0]
    elif nit == 255:
        nit = struct.unpack("<Q", f.read(8))[0]
    r = []
    for i in xrange(nit):
        t = c()
        t.deserialize(f)
        r.append(t)
    return r

def ser_vector(l):
    r = ""
    if len(l) < 253:
        r = chr(len(l))
    elif len(l) < 0x10000:
        r = chr(253) + struct.pack("<H", len(l))
    elif len(l) < 0x100000000L:
        r = chr(254) + struct.pack("<I", len(l))
    else:
        r = chr(255) + struct.pack("<Q", len(l))
    for i in l:
        r += i.serialize()
    return r

def deser_uint256_vector(f):
    nit = struct.unpack("<B", f.read(1))[0]
    if nit == 253:
        nit = struct.unpack("<H", f.read(2))[0]
    elif nit == 254:
        nit = struct.unpack("<I", f.read(4))[0]
    elif nit == 255:
        nit = struct.unpack("<Q", f.read(8))[0]
    r = []
    for i in xrange(nit):
        t = deser_uint256(f)
        r.append(t)
    return r

def ser_uint256_vector(l):
    r = ""
    if len(l) < 253:
        r = chr(len(l))
    elif len(l) < 0x10000:
        r = chr(253) + struct.pack("<H", len(l))
    elif len(l) < 0x100000000L:
        r = chr(254) + struct.pack("<I", len(l))
    else:
        r = chr(255) + struct.pack("<Q", len(l))
    for i in l:
        r += ser_uint256(i)
    return r

__b58chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
__b58base = len(__b58chars)

def b58decode(v, length):
    """ decode v into a string of len bytes
    """
    long_value = 0L
    for (i, c) in enumerate(v[::-1]):
        long_value += __b58chars.find(c) * (__b58base**i)

    result = ''
    while long_value >= 256:
        div, mod = divmod(long_value, 256)
        result = chr(mod) + result
        long_value = div
    result = chr(long_value) + result

    nPad = 0
    for c in v:
        if c == __b58chars[0]: nPad += 1
        else: break

    result = chr(0)*nPad + result
    if length is not None and len(result) != length:
        return None

    return result

def reverse_hash(h):
    # This only revert byte order, nothing more
    if len(h) != 64:
        raise Exception('hash must have 64 hexa chars')

    return ''.join([ h[56-i:64-i] for i in range(0, 64, 8) ])

def doublesha(b):
    return sha256(sha256(b).digest()).digest()

def bits_to_target(bits):
    return struct.unpack('<L', bits[:3] + b'\0')[0] * 2**(8*(int(bits[3], 16) - 3))

def address_to_pubkeyhash(addr):
    try:
        addr = b58decode(addr, 25)
    except:
        return None

    if addr is None:
        return None

    ver = addr[0]
    cksumA = addr[-4:]
    cksumB = doublesha(addr[:-4])[:4]

    if cksumA != cksumB:
        return None

    return (ver, addr[1:-4])

def ser_uint256_be(u):
    '''ser_uint256 to big endian'''
    rs = ""
    for i in xrange(8):
        rs += struct.pack(">I", u & 0xFFFFFFFFL)
        u >>= 32
    return rs

def deser_uint256_be(f):
    r = 0L
    for i in xrange(8):
        t = struct.unpack(">I", f.read(4))[0]
        r += t << (i * 32)
    return r

def ser_number(n):
    # For encoding nHeight into coinbase
    s = bytearray(b'\1')
    while n > 127:
        s[0] += 1
        s.append(n % 256)
        n //= 256
    s.append(n)
    return bytes(s)

def script_to_address(addr):
    d = address_to_pubkeyhash(addr)
    if not d:
        raise ValueError('invalid address')
    (ver, pubkeyhash) = d
    return b'\x76\xa9\x14' + pubkeyhash + b'\x88\xac'

########NEW FILE########
__FILENAME__ = interfaces
'''This module contains classes used by pool core to interact with the rest of the pool.
   Default implementation do almost nothing, you probably want to override these classes
   and customize references to interface instances in your launcher.
   (see launcher_demo.tac for an example).
'''

import time
from twisted.internet import reactor, defer

import stratum.logger
log = stratum.logger.get_logger('interfaces')

class WorkerManagerInterface(object):
    def __init__(self):
        # Fire deferred when manager is ready
        self.on_load = defer.Deferred()
        self.on_load.callback(True)

    def authorize(self, worker_name, worker_password):
        return True

class ShareLimiterInterface(object):
    '''Implement difficulty adjustments here'''

    def submit(self, connection_ref, current_difficulty, timestamp):
        '''connection - weak reference to Protocol instance
           current_difficulty - difficulty of the connection
           timestamp - submission time of current share

           - raise SubmitException for stop processing this request
           - call mining.set_difficulty on connection to adjust the difficulty'''
        pass

class ShareManagerInterface(object):
    def __init__(self):
        # Fire deferred when manager is ready
        self.on_load = defer.Deferred()
        self.on_load.callback(True)

    def on_network_block(self, prevhash):
        '''Prints when there's new block coming from the network (possibly new round)'''
        pass

    def on_submit_share(self, worker_name, block_header, block_hash, shares, timestamp, is_valid):
        log.info("%s %s %s" % (block_hash, 'valid' if is_valid else 'INVALID', worker_name))

    def on_submit_block(self, is_accepted, worker_name, block_header, block_hash, timestamp):
        log.info("Block %s %s" % (block_hash, 'ACCEPTED' if is_accepted else 'REJECTED'))

class TimestamperInterface(object):
    '''This is the only source for current time in the application.
    Override this for generating unix timestamp in different way.'''
    def time(self):
        return time.time()

class PredictableTimestamperInterface(TimestamperInterface):
    '''Predictable timestamper may be useful for unit testing.'''
    start_time = 1345678900 # Some day in year 2012
    delta = 0

    def time(self):
        self.delta += 1
        return self.start_time + self.delta

class Interfaces(object):
    worker_manager = None
    share_manager = None
    share_limiter = None
    timestamper = None
    template_registry = None

    @classmethod
    def set_worker_manager(cls, manager):
        cls.worker_manager = manager

    @classmethod
    def set_share_manager(cls, manager):
        cls.share_manager = manager

    @classmethod
    def set_share_limiter(cls, limiter):
        cls.share_limiter = limiter

    @classmethod
    def set_timestamper(cls, manager):
        cls.timestamper = manager

    @classmethod
    def set_template_registry(cls, registry):
        cls.template_registry = registry

########NEW FILE########
__FILENAME__ = service
import binascii
from twisted.internet import defer

from stratum.services import GenericService, admin
from stratum.pubsub import Pubsub
from interfaces import Interfaces
from subscription import MiningSubscription
from lib.exceptions import SubmitException

import stratum.logger
log = stratum.logger.get_logger('mining')

class MiningService(GenericService):
    '''This service provides public API for Stratum mining proxy
    or any Stratum-compatible miner software.

    Warning - any callable argument of this class will be propagated
    over Stratum protocol for public audience!'''

    service_type = 'mining'
    service_vendor = 'stratum'
    is_default = True

    @admin
    def update_block(self):
        '''Connect this RPC call to 'bitcoind -blocknotify' for
        instant notification about new block on the network.
        See blocknotify.sh in /scripts/ for more info.'''

        log.info("New block notification received")
        Interfaces.template_registry.update_block()
        return True

    def authorize(self, worker_name, worker_password):
        '''Let authorize worker on this connection.'''

        session = self.connection_ref().get_session()
        session.setdefault('authorized', {})

        if Interfaces.worker_manager.authorize(worker_name, worker_password):
            session['authorized'][worker_name] = worker_password
            return True

        else:
            if worker_name in session['authorized']:
                del session['authorized'][worker_name]
            return False

    def subscribe(self, *args):
        '''Subscribe for receiving mining jobs. This will
        return subscription details, extranonce1_hex and extranonce2_size'''

        extranonce1 = Interfaces.template_registry.get_new_extranonce1()
        extranonce2_size = Interfaces.template_registry.extranonce2_size
        extranonce1_hex = binascii.hexlify(extranonce1)

        session = self.connection_ref().get_session()
        session['extranonce1'] = extranonce1
        session['difficulty'] = 1 # Following protocol specs, default diff is 1

        return Pubsub.subscribe(self.connection_ref(), MiningSubscription()) + (extranonce1_hex, extranonce2_size)

    '''
    def submit(self, worker_name, job_id, extranonce2, ntime, nonce):
        import time
        start = time.time()

        for x in range(100):
            try:
                ret = self.submit2(worker_name, job_id, extranonce2, ntime, nonce)
            except:
                pass

        log.info("LEN %.03f" % (time.time() - start))
        return ret
    '''

    def submit(self, worker_name, job_id, extranonce2, ntime, nonce):
        '''Try to solve block candidate using given parameters.'''

        session = self.connection_ref().get_session()
        session.setdefault('authorized', {})

        # Check if worker is authorized to submit shares
        if not Interfaces.worker_manager.authorize(worker_name,
                        session['authorized'].get(worker_name)):
            raise SubmitException("Worker is not authorized")

        # Check if extranonce1 is in connection session
        extranonce1_bin = session.get('extranonce1', None)
        if not extranonce1_bin:
            raise SubmitException("Connection is not subscribed for mining")

        difficulty = session['difficulty']
        submit_time = Interfaces.timestamper.time()

        Interfaces.share_limiter.submit(self.connection_ref, difficulty, submit_time)

        # This checks if submitted share meet all requirements
        # and it is valid proof of work.
        try:
            (block_header, block_hash, on_submit) = Interfaces.template_registry.submit_share(job_id,
                                                worker_name, extranonce1_bin, extranonce2, ntime, nonce, difficulty)
        except SubmitException:
            # block_header and block_hash are None when submitted data are corrupted
            Interfaces.share_manager.on_submit_share(worker_name, None, None, difficulty,
                                                 submit_time, False)
            raise


        Interfaces.share_manager.on_submit_share(worker_name, block_header, block_hash, difficulty,
                                                 submit_time, True)

        if on_submit != None:
            # Pool performs submitblock() to bitcoind. Let's hook
            # to result and report it to share manager
            on_submit.addCallback(Interfaces.share_manager.on_submit_block,
                        worker_name, block_header, block_hash, submit_time)

        return True

    # Service documentation for remote discovery
    update_block.help_text = "Notify Stratum server about new block on the network."
    update_block.params = [('password', 'string', 'Administrator password'),]

    authorize.help_text = "Authorize worker for submitting shares on this connection."
    authorize.params = [('worker_name', 'string', 'Name of the worker, usually in the form of user_login.worker_id.'),
                        ('worker_password', 'string', 'Worker password'),]

    subscribe.help_text = "Subscribes current connection for receiving new mining jobs."
    subscribe.params = []

    submit.help_text = "Submit solved share back to the server. Excessive sending of invalid shares "\
                       "or shares above indicated target (see Stratum mining docs for set_target()) may lead "\
                       "to temporary or permanent ban of user,worker or IP address."
    submit.params = [('worker_name', 'string', 'Name of the worker, usually in the form of user_login.worker_id.'),
                     ('job_id', 'string', 'ID of job (received by mining.notify) which the current solution is based on.'),
                     ('extranonce2', 'string', 'hex-encoded big-endian extranonce2, length depends on extranonce2_size from mining.notify.'),
                     ('ntime', 'string', 'UNIX timestamp (32bit integer, big-endian, hex-encoded), must be >= ntime provided by mining,notify and <= current time'),
                     ('nonce', 'string', '32bit integer, hex-encoded, big-endian'),]


########NEW FILE########
__FILENAME__ = subscription
from stratum.pubsub import Pubsub, Subscription
from mining.interfaces import Interfaces

import stratum.logger
log = stratum.logger.get_logger('subscription')

class MiningSubscription(Subscription):
    '''This subscription object implements
    logic for broadcasting new jobs to the clients.'''

    event = 'mining.notify'

    @classmethod
    def on_template(cls, is_new_block):
        '''This is called when TemplateRegistry registers
           new block which we have to broadcast clients.'''

        start = Interfaces.timestamper.time()

        clean_jobs = is_new_block
        (job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, _) = \
                        Interfaces.template_registry.get_last_broadcast_args()

        # Push new job to subscribed clients
        cls.emit(job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs)

        cnt = Pubsub.get_subscription_count(cls.event)
        log.info("BROADCASTED to %d connections in %.03f sec" % (cnt, (Interfaces.timestamper.time() - start)))

    def _finish_after_subscribe(self, result):
        '''Send new job to newly subscribed client'''
        try:
            (job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, _) = \
                        Interfaces.template_registry.get_last_broadcast_args()
        except Exception:
            log.error("Template not ready yet")
            return result

        # Force set higher difficulty
        # TODO
        #self.connection_ref().rpc('mining.set_difficulty', [2,], is_notification=True)
        #self.connection_ref().rpc('client.get_version', [])

        # Force client to remove previous jobs if any (eg. from previous connection)
        clean_jobs = True
        self.emit_single(job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, True)

        return result

    def after_subscribe(self, *args):
        '''This will send new job to the client *after* he receive subscription details.
        on_finish callback solve the issue that job is broadcasted *during*
        the subscription request and client receive messages in wrong order.'''
        self.connection_ref().on_finish.addCallback(self._finish_after_subscribe)

########NEW FILE########
