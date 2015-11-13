__FILENAME__ = bitcoin
# -*- Mode: Python -*-

# A prototype bitcoin implementation.
#
# Author: Sam Rushing. http://www.nightmare.com/~rushing/
# July 2011 - Mar 2013
#
# because we can have forks/orphans, 
# num->block is 1->N and block->num is 1->1
#

# next step: keeping track of all outpoints.
#  consider using leveldb?

import copy
import hashlib
import random
import struct
import socket
import time
import os
import pickle
import string

import coro
import coro.read_stream

from hashlib import sha256
from pprint import pprint as pp

import caesure.proto

from caesure.script import eval_script, verifying_machine, pprint_script
from caesure._script import parse_script

W = coro.write_stderr

# these are overriden for testnet
BITCOIN_PORT = 8333
BITCOIN_MAGIC = '\xf9\xbe\xb4\xd9'
BLOCKS_PATH = 'blocks.bin'
genesis_block_hash = '000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f'

# overridden by commandline argument
MY_PORT = BITCOIN_PORT

from caesure.proto import base58_encode, base58_decode, hexify

def dhash (s):
    return sha256(sha256(s).digest()).digest()

def rhash (s):
    h1 = hashlib.new ('ripemd160')
    h1.update (sha256(s).digest())
    return h1.digest()

def bcrepr (n):
    return '%d.%08d' % divmod (n, 100000000)

# https://en.bitcoin.it/wiki/Proper_Money_Handling_(JSON-RPC)
def float_to_btc (f):
    return long (round (f * 1e8))

class BadAddress (Exception):
    pass
class VerifyError (Exception):
    pass

def key_to_address (s):
    checksum = dhash ('\x00' + s)[:4]
    return '1' + base58_encode (
        int ('0x' + (s + checksum).encode ('hex'), 16)
        )

def address_to_key (s):
    # strip off leading '1'
    s = ('%048x' % base58_decode (s[1:])).decode ('hex')
    hash160, check0 = s[:-4], s[-4:]
    check1 = dhash ('\x00' + hash160)[:4]
    if check0 != check1:
        raise BadAddress (s)
    return hash160

def pkey_to_address (s):
    s = '\x80' + s
    checksum = dhash (s)[:4]
    return base58_encode (
        int ((s + checksum).encode ('hex'), 16)
        )

def unhexify (s, flip=False):
    if flip:
        return s.decode ('hex')[::-1]
    else:
        return s.decode ('hex')

def frob_hash (s):
    r = []
    for i in range (0, len (s), 2):
        r.append (s[i:i+2])
    r.reverse()
    return ''.join (r)

class timer:
    def __init__ (self):
        self.start = time.time()
    def end (self):
        return time.time() - self.start

# --------------------------------------------------------------------------------
#        ECDSA
# --------------------------------------------------------------------------------

# pull in one of the ECDSA key implementations.
# NOTE: as of march 2013, the pure ecdsa verify seems to have a problem. FIXME.

from ecdsa_ssl import KEY
#from ecdsa_pure import KEY

# --------------------------------------------------------------------------------

OBJ_TX    = 1
OBJ_BLOCK = 2

MAX_BLOCK_SIZE = 1000000
COIN           = 100000000
MAX_MONEY      = 21000000 * COIN

def pack_net_addr ((services, (addr, port))):
    addr = pack_ip_addr (addr)
    port = struct.pack ('!H', port)
    return struct.pack ('<Q', services) + addr + port

def make_nonce():
    return random.randint (0, 1<<64L)

NULL_OUTPOINT = ('\x00' * 32, 4294967295)

class TX (caesure.proto.TX):

    def copy (self):
        tx0 = TX()
        tx0.version = self.version
        tx0.lock_time = self.lock_time
        tx0.inputs = self.inputs[:]
        tx0.outputs = self.outputs[:]
        return tx0

    def get_hash (self):
        return dhash (self.render())

    def dump (self):
        print 'hash: %s' % (hexify (dhash (self.render())),)
        print 'inputs: %d' % (len(self.inputs))
        for i in range (len (self.inputs)):
            (outpoint, index), script, sequence = self.inputs[i]
            redeem = pprint_script (parse_script (script))
            print '%3d %s:%d %r %d' % (i, hexify(outpoint), index, redeem, sequence)
        print '%d outputs' % (len(self.outputs))
        for i in range (len (self.outputs)):
            value, pk_script = self.outputs[i]
            pk_script = pprint_script (parse_script (pk_script))
            print '%3d %s %r' % (i, bcrepr (value), pk_script)
        print 'lock_time:', self.lock_time

    def render (self):
        return self.pack()

    # Hugely Helpful: http://forum.bitcoin.org/index.php?topic=2957.20

    def get_ecdsa_hash (self, index, sub_script, hash_type):
        # XXX see script.cpp:SignatureHash() - looks like this is where
        #   we make mods depending on <hash_type>
        tx0 = self.copy()
        for i in range (len (tx0.inputs)):
            outpoint, script, sequence = tx0.inputs[i]
            if i == index:
                script = sub_script
            else:
                script = ''
            tx0.inputs[i] = outpoint, script, sequence
        return tx0.render() + struct.pack ('<I', hash_type)

    # XXX to be removed
    def sign (self, key, index):
        hash, _, pubkey = self.get_ecdsa_hash (index)
        assert (key.get_pubkey() == pubkey)
        # tack on the hash type byte.
        sig = key.sign (hash) + '\x01'
        iscript = make_iscript (sig, pubkey)
        op0, _, seq = self.inputs[index]
        self.inputs[index] = op0, iscript, seq
        return sig

    def verify0 (self, index, prev_outscript):
        outpoint, script, sequence = self.inputs[index]
        m = verifying_machine (prev_outscript, self, index)
        #print 'source script', pprint_script (parse_script (script))
        eval_script (m, parse_script (script))
        m.clear_alt()
        # should terminate with OP_CHECKSIG or its like
        #print 'redeem script', pprint_script (parse_script (prev_outscript))
        r = eval_script (m, parse_script (prev_outscript))
        if r is None:
            # if the script did not end in a CHECKSIG op, we need
            #   to check the top of the stack (essentially, OP_VERIFY)
            m.need (1)
            if not m.truth():
                raise VerifyError
        elif r == 1:
            pass
        else:
            # this can happen if r == 0 (verify failed) or r == -1 (openssl error)
            raise VerifyError

    def verify1 (self, pub_key, sig, vhash):
        if building_txmap:
            return 1
        else:
            k = KEY()
            #W ('pub_key=%r\n' % (pub_key,))
            k.set_pubkey (pub_key)
            r = k.verify (vhash, sig)
            #print 'ecdsa verify...', r
            return r

def read_ip_addr (s):
    r = socket.inet_ntop (socket.AF_INET6, s)
    if r.startswith ('::ffff:'):
        return r[7:]
    else:
        return r

def pack_ip_addr (addr):
    # only v4 right now
    # XXX this is probably no longer true, the dns seeds are returning v6 addrs
    return socket.inet_pton (socket.AF_INET6, '::ffff:%s' % (addr,))

def pack_var_int (n):
    if n < 0xfd:
        return chr(n)
    elif n < 1<<16:
        return '\xfd' + struct.pack ('<H', n)
    elif n < 1<<32:
        return '\xfe' + struct.pack ('<I', n)
    else:
        return '\xff' + struct.pack ('<Q', n)

def pack_var_str (s):
    return pack_var_int (len (s)) + s

def pack_inv (pairs):
    result = [pack_var_int (len(pairs))]
    for objid, hash in pairs:
        result.append (struct.pack ('<I32s', objid, hash))
    return ''.join (result)

class BadBlock (Exception):
    pass

class BLOCK (caesure.proto.BLOCK):

    def make_TX (self):
        return TX()

    def check_bits (self):
        shift  = self.bits >> 24
        target = (self.bits & 0xffffff) * (1 << (8 * (shift - 3)))
        val = int (self.name, 16)
        return val < target

    def get_merkle_hash (self):
        hl = [dhash (t.raw) for t in self.transactions]
        while 1:
            if len(hl) == 1:
                return hl[0]
            if len(hl) % 2 != 0:
                hl.append (hl[-1])
            hl0 = []
            for i in range (0, len (hl), 2):
                hl0.append (dhash (hl[i] + hl[i+1]))
            hl = hl0

    # see https://en.bitcoin.it/wiki/Protocol_rules
    def check_rules (self):
        if not len(self.transactions):
            raise BadBlock ("zero transactions")
        elif not self.check_bits():
            raise BadBlock ("did not achieve target")
        elif (time.time() - self.timestamp) < (-60 * 60 * 2):
            raise BadBlock ("block from the future")
        else:
            for i in range (len (self.transactions)):
                tx = self.transactions[i]
                if i == 0 and (len (tx.inputs) != 1 or tx.inputs[0][0] != NULL_OUTPOINT):
                    raise BadBlock ("first transaction not a generation")
                elif i == 0 and not (2 <= len (tx.inputs[0][1]) <= 100):
                    raise BadBlock ("bad sig_script in generation transaction")
                elif i > 0:
                    for outpoint, sig_script, sequence in tx.inputs:
                        if outpoint == NULL_OUTPOINT:
                            raise BadBlock ("transaction other than the first is a generation")
                for value, _ in tx.outputs:
                    if value > MAX_MONEY:
                        raise BadBlock ("too much money")
                    # XXX not checking SIGOP counts since we don't really implement the script engine.
            # check merkle hash
            if self.merkle_root != self.get_merkle_hash():
                raise BadBlock ("merkle hash doesn't match")
        # XXX more to come...

# --------------------------------------------------------------------------------
# block_db file format: (<8 bytes of size> <block>)+

ZERO_BLOCK = '00' * 32

class block_db:

    def __init__ (self, read_only=False):
        self.read_only = read_only
        self.blocks = {}
        self.prev = {}
        self.next = {}
        self.block_num = {ZERO_BLOCK: -1}
        self.num_block = {}
        self.last_block = 0
        self.build_block_chain()
        self.file = None

    def get_header (self, name):
        path = os.path.join ('blocks', name)
        return open (path).read (80)

    # block can have only one previous block, but may have multiple
    #  next blocks.
    def build_block_chain (self):
        from caesure.proto import unpack_block_header
        if not os.path.isfile (BLOCKS_PATH):
            open (BLOCKS_PATH, 'wb').write('')
        file = open (BLOCKS_PATH, 'rb')
        print 'reading block headers...'
        file.seek (0)
        i = -1
        name = ZERO_BLOCK
        # first, read all the blocks
        t0 = timer()
        while 1:
            pos = file.tell()
            size = file.read (8)
            if not size:
                break
            else:
                size, = struct.unpack ('<Q', size)
                header = file.read (80)
                (version, prev_block, merkle_root,
                 timestamp, bits, nonce) = unpack_block_header (header)
                # skip the rest of the block
                file.seek (size-80, 1)
                prev_block = hexify (prev_block, True)
                name = hexify (dhash (header), True)
                bn = 1 + self.block_num[prev_block]
                self.prev[name] = prev_block
                self.next.setdefault (prev_block, set()).add (name)
                self.block_num[name] = bn
                self.num_block.setdefault (bn, set()).add (name)
                self.blocks[name] = pos
                self.last_block = max (self.last_block, bn)
        if name != ZERO_BLOCK:
            print 'last block (%d): %r' % (self.last_block, self.num_block[self.last_block])
        file.close()
        print '%.02f secs to load block chain' % (t0.end())
        self.read_only_file = open (BLOCKS_PATH, 'rb')

    def open_for_append (self):
        # reopen in append mode
        self.file = open (BLOCKS_PATH, 'ab')

    def get_block (self, name):
        pos =  self.blocks[name]
        self.read_only_file.seek (pos)
        size = self.read_only_file.read (8)
        size, = struct.unpack ('<Q', size)
        return self.read_only_file.read (size)

    def __getitem__ (self, name):
        b = BLOCK()
        b.unpack (self.get_block (name))
        return b

    def __len__ (self):
        return len (self.blocks)

    def by_num (self, num):
        # fetch *one* of the set, beware all callers of this
        return self[list(self.num_block[num])[0]]

    def add (self, name, block):
        if self.blocks.has_key (name):
            print 'ignoring block we already have:', name
        elif not self.block_num.has_key (block.prev_block) and block.prev_block != ZERO_BLOCK:
            # if we don't have the previous block, there's no
            #  point in remembering it at all.  toss it.
            pass
        else:
            self.write_block (name, block)

    def write_block (self, name, block):
        if self.file is None:
            self.open_for_append()
        size = len (block.raw)
        pos = self.file.tell()
        self.file.write (struct.pack ('<Q', size))
        self.file.write (block.raw)
        self.file.flush()
        self.prev[name] = block.prev_block
        self.next.setdefault (block.prev_block, set()).add (name)
        self.blocks[name] = pos
        if block.prev_block == ZERO_BLOCK:
            i = -1
        else:
            i = self.block_num[block.prev_block]
        self.block_num[name] = i+1
        self.num_block.setdefault (i+1, set()).add (name)
        self.last_block = i+1

    def has_key (self, name):
        return self.prev.has_key (name)

    # see https://en.bitcoin.it/wiki/Satoshi_Client_Block_Exchange
    # "The getblocks message contains multiple block hashes that the
    #  requesting node already possesses, in order to help the remote
    #  note find the latest common block between the nodes. The list of
    #  hashes starts with the latest block and goes back ten and then
    #  doubles in an exponential progression until the genesis block is
    #  reached."

    def set_for_getblocks (self):
        n = self.last_block
        result = []
        i = 0
        step = 1
        while n > 0:
            name = list(self.num_block[n])[0]
            result.append (unhexify (name, flip=True))
            n -= step
            i += 1
            if i >= 10:
                step *= 2
        return result
    
# --------------------------------------------------------------------------------
#                               protocol
# --------------------------------------------------------------------------------

class BadState (Exception):
    pass

class dispatcher:
    def __init__ (self):
        self.known = []
        self.requested = set()
        self.ready = {}
        self.target = 0
        if not the_block_db:
            self.known.append (genesis_block_hash)

    def notify_height (self, height):
        if height > self.target:
            self.target = height
            c = get_random_connection()
            W ('sending getblocks() target=%d\n' % (self.target,))
            c.getblocks()

    def add_inv (self, objid, name):
        if objid == OBJ_BLOCK:
            self.add_to_known (name)
        elif objid == OBJ_TX:
            pass
        else:
            W ('*** strange <inv> of type %r %r\n' % (objid, name))

    def add_block (self, payload):
        db = the_block_db
        b = BLOCK()
        b.unpack (payload)
        self.ready[b.prev_block] = b
        if b.name in self.requested:
            self.requested.remove (b.name)
        # we may have several blocks waiting to be chained
        #  in by the arrival of a missing link...
        while 1:
            if db.has_key (b.prev_block) or (b.prev_block == ZERO_BLOCK):
                del self.ready[b.prev_block]
                self.block_to_db (b.name, b)
                if self.ready.has_key (b.name):
                    b = self.ready[b.name]
                else:
                    break
            else:
                break
        if (db.last_block < self.target) and not len(self.requested):
            c = get_random_connection()
            c.getblocks()
        
    def kick_known (self):
        chunk = min (self.target - the_block_db.last_block, 100)
        if len (self.known) >= chunk:
            c = get_random_connection()
            chunk, self.known = self.known[:100], self.known[100:]
            c.getdata ([(OBJ_BLOCK, name) for name in chunk])
            self.requested.update (chunk)

    def add_to_known (self, name):
        self.known.append (name)
        self.kick_known()

    def block_to_db (self, name, b):
        try:
            b.check_rules()
        except BadState as reason:
            W ('*** bad block: %s %r' % (name, reason))
        else:
            the_block_db.add (name, b)

class base_connection:

    # protocol was changed to reflect *protocol* version, not bitcoin-client-version
    version = 60002 # trying to update protocol from 60001 mar 2013

    def __init__ (self, addr='127.0.0.1', port=BITCOIN_PORT):
        self.addr = addr
        self.port = port
        self.nonce = make_nonce()
        self.conn = coro.tcp_sock()
        self.packet_count = 0
        self.stream = coro.read_stream.sock_stream (self.conn)

    def connect (self):
        self.conn.connect ((self.addr, self.port))

    def send_packet (self, command, payload):
        lc = len(command)
        assert (lc < 12)
        cmd = command + ('\x00' * (12 - lc))
        h = dhash (payload)
        checksum, = struct.unpack ('<I', h[:4])
        packet = struct.pack (
            '<4s12sII',
            BITCOIN_MAGIC,
            cmd,
            len(payload),
            checksum
            ) + payload
        self.conn.send (packet)
        W ('=> %s\n' % (command,))

    def send_version (self):
        data = struct.pack ('<IQQ', self.version, 1, int(time.time()))
        data += pack_net_addr ((1, (self.addr, self.port)))
        data += pack_net_addr ((1, (my_addr, MY_PORT)))
        data += struct.pack ('<Q', self.nonce)
        data += pack_var_str ('/caesure:20130306/')
        start_height = the_block_db.last_block
        if start_height < 0:
            start_height = 0
        # ignore bip37 for now - leave True
        data += struct.pack ('<IB', start_height, 1)
        self.send_packet ('version', data)

    def gen_packets (self):
        while 1:
            data = self.stream.read_exact (24)
            if not data:
                W ('connection closed.\n')
                break
            magic, command, length, checksum = struct.unpack ('<I12sII', data)
            command = command.strip ('\x00')
            W ('[%s]' % (command,))
            self.packet_count += 1
            self.header = magic, command, length
            # XXX verify checksum
            if length:
                payload = self.stream.read_exact (length)
            else:
                payload = ''
            yield (command, payload)

    def getblocks (self):
        hashes = the_block_db.set_for_getblocks()
        hashes.append ('\x00' * 32)
        payload = ''.join ([
            struct.pack ('<I', self.version),
            pack_var_int (len(hashes)-1), # count does not include hash_stop
            ] + hashes
            )
        self.send_packet ('getblocks', payload)

    def getdata (self, what):
        "request (TX|BLOCK)+ from the other side"
        payload = [pack_var_int (len(what))]
        for kind, name in what:
            # decode hash
            h = unhexify (name, flip=True)
            payload.append (struct.pack ('<I32s', kind, h))
        self.send_packet ('getdata', ''.join (payload))

class connection (base_connection):

    def __init__ (self, addr='127.0.0.1', port=BITCOIN_PORT):
        base_connection.__init__ (self, addr, port)
        coro.spawn (self.go)

    def go (self):
        self.connect()
        try:
            the_connection_list.append (self)
            self.send_version()
            for command, payload in self.gen_packets():
                self.do_command (command, payload)
        finally:
            the_connection_list.remove (self)
            self.conn.close()

    def check_command_name (self, command):
        for ch in command:
            if ch not in string.letters:
                return False
        return True

    def do_command (self, cmd, data):
        if self.check_command_name (cmd):
            try:
                method = getattr (self, 'cmd_%s' % cmd,)
            except AttributeError:
                W ('no support for "%s" command\n' % (cmd,))
            else:
                try:
                    method (data)
                except:
                    W ('caesure error: %r\n' % (coro.compact_traceback(),))
                    W ('     ********** problem processing %r command\n' % (cmd,))
        else:
            W ('bad command: "%r", ignoring\n' % (cmd,))

    max_pending = 50

    def cmd_version (self, data):
        self.other_version = caesure.proto.unpack_version (data)
        self.send_packet ('verack', '')
        the_dispatcher.notify_height (self.other_version.start_height)

    def cmd_verack (self, data):
        pass

    def cmd_addr (self, data):
        addr = caesure.proto.unpack_addr (data)
        print addr

    def cmd_inv (self, data):
        pairs = caesure.proto.unpack_inv (data)
        for objid, name in pairs:
            the_dispatcher.add_inv (objid, hexify (name, True))

    def cmd_getdata (self, data):
        return caesure.proto.unpack_getdata (data)

    def cmd_tx (self, data):
        return caesure.proto.make_tx (data)

    def cmd_block (self, data):
        the_dispatcher.add_block (data)

    def cmd_ping (self, data):
        # supposed to do a pong?
        W ('ping: data=%r\n' % (data,))

    def cmd_alert (self, data):
        payload, signature = caesure.proto.unpack_alert (data)
        # XXX verify signature
        W ('alert: sig=%r payload=%r\n' % (signature, payload,))

the_block_db = None
the_connection_list = []

def get_random_connection():
    return random.choice (the_connection_list)

# Mar 2013 fetched from https://github.com/bitcoin/bitcoin/blob/master/src/net.cpp
dns_seeds = [
    "bitseed.xf2.org",
    "dnsseed.bluematt.me",
    "seed.bitcoin.sipa.be",
    "dnsseed.bitcoin.dashjr.org",
    ]

def dns_seed():
    print 'fetching DNS seed addresses...'
    addrs = set()
    for name in dns_seeds:
        for info in socket.getaddrinfo (name, 8333):
            family, type, proto, _, addr = info
            if family == socket.AF_INET and type == socket.SOCK_STREAM and proto == socket.IPPROTO_TCP:
                addrs.add (addr[0])
    print '...done.'
    return addrs

# trying to verify this roll of the dice...
# http://blockchain.info/tx/013108d7408718f2df8c0c66fe1eb615020d08b5d9418c4c330ceb792c72f857
def do_sample_verify():
    db = the_block_db
    b = db.by_num (226670)
    # outputs are from 226670, txn -4
    tx = b.transactions[-4]
    # input 0 is from 226670, txn 142, output 0
    amt, oscript = b.transactions[142].outputs[0]
    tx.verify0 (0, oscript)
    # input 1 is from 226589, txn 344, output 1
    amt, oscript = db.by_num(226589).transactions[344].outputs[1]
    tx.verify0 (1, oscript)

# try to verify the first multisig...
# http://blockchain.info/tx/eb3b82c0884e3efa6d8b0be55b4915eb20be124c9766245bcc7f34fdac32bccb
def do_sample_multi0():
    db = the_block_db
    b = db.by_num (163685) # tx 13
    tx = b.transactions[13]
    if 0:
        # source 0 is from the same block, tx 11, output 0
        amt, oscript = b.transactions[11].outputs[0]
        tx.verify0 (0, oscript)
    # source 1 is from the same block, tx 11, output 1
    amt, oscript = b.transactions[11].outputs[1]
    tx.verify0 (1, oscript)

# 02b038020755f63d45d1c8c7ab495d5d3bbc82113d95fbb964e7f8184e1b27bd
def do_sample_multi():
    db = the_block_db
    b = db.by_num (227878) # tx 139
    tx = b.transactions[139]
    # only one source, block 227861, tx 95, output 0
    amt, oscript = db.by_num (227861).transactions[95].outputs[0]
    tx.verify0 (0, oscript)

# chain-walking generators

# these two are mutually recursive.
# whenever a fork is found, we create a generator for each
#  sub-chain and 'race' them against each other.  When only
#  one remains, we return with its name.

def chain_gen (name):
    "generate a series of 1... for each block in this sub-chain"
    db = the_block_db
    while 1:
        if db.next.has_key (name):
            names = db.next[name]
            if len(names) > 1:
                for x in longest (names):
                    yield 1
            else:
                name = list(names)[0]
                yield 1
        else:
            break

def longest (names):
    "find the longest of the chains in <names>"
    gens = [ (name, chain_gen (name)) for name in list (names) ]
    ng = len (gens)
    left = ng
    n = 0
    while left > 1:
        for i in range (ng):
            if gens[i]:
                name, gen = gens[i]
                try:
                    gen.next()
                except StopIteration:
                    gens[i] = None
                    left -= 1
        n += 1
    [(name, _)] = [x for x in gens if x is not None]
    return name, n

# find the 'official' chain starting from the beginning, using
#  longest() to identify the longer of any subchains.
#  something that could be fun here... actually make it an 'infinite'
#  generator - as in it will pause until the next block comes along.
#
# XXX consider how to deal with a fork in real time.

def db_gen():
    db = the_block_db
    name = genesis_block_hash
    while 1:
        yield name
        if db.next.has_key (name):
            names = db.next[name]
            if len(names) == 1:
                name = list(names)[0]
            else:
                name, _ = longest (names)
        else:
            break

class monies:
    def __init__ (self):
        import leveldb
        self.monies = leveldb.LevelDB ('monies')
    def __getitem__ (self, key):
        return self.monies.Get (key)
    def __setitem__ (self, key, val):
        self.monies.Put (key, val)
    def __delitem__ (self, key):
        self.monites.Delete (key)

pack_u64 = caesure.proto.pack_u64

class txmap:
    def __init__ (self):
        import leveldb
        #self.monies = leveldb.LevelDB ('monies')
        self.monies = {}

    def store_outputs (self, tx):
        for i in range (len (tx.outputs)):
            # inputs are referenced by (txhash,index) so we need to store this into db,
            #   and only remove it when it has been spent.  so probably we need (txhash,index)->(amt,script)
            #   alternatively we could store it as an offset,size into the db file... but probably not worth it.
            amt, pk_script = tx.outputs[i]
            self.monies['%s:%d' % (tx.name, i)] = pack_u64(amt) + pk_script

    # failed txn here: https://blockchain.info/block-index/172908
    def initialize (self):
        db = the_block_db
        n = 0
        W ('start: %r\n' % (time.ctime(),))
        for name in db_gen():
            b = db[name]
            # assume coinbase is ok for now
            tx0 = b.transactions[0]
            self.store_outputs (tx0)
            for tx in b.transactions[1:]:
                # verify each transaction
                # first, we need the output script for each of the inputs
                for i in range (len (tx.inputs)):
                    (outpoint, index), script, sequence = tx.inputs[i]
                    key = '%s:%d' % (hexify (outpoint, True), index)
                    pair = self.monies[key]
                    amt, oscript = pair[:8], pair[8:]
                    amt, = struct.unpack ('<Q', amt)
                    try:
                        tx.verify0 (i, oscript)
                    except VerifyError:
                        W ('failed verification: %r:%d\n' % (tx.name,i))
                    except NotImplementedError:
                        W ('not implemented: %r:%d\n' % (tx.name,i))
                    else:
                        del self.monies[key]
                self.store_outputs (tx)
            n += 1
            #if n == 120000:
            #    coro.profiler.start()
            #if n == 130000:
            #    coro.profiler.stop()
            if n % 1000 == 0:
                W ('.')
        W ('done: %r\n' % (time.ctime(),))

# difficult to parallelize the verification, because the transactions in a single
#   block can be dependent on other txns in that same block.  [this must mean that
#   they are ordered?]

building_txmap = False
the_txmap = None

def build_txmap():
    global building_txmap, the_txmap
    tm = txmap()
    building_txmap = True
    try:
        tm.initialize()
    finally:
        building_txmap = False
    the_txmap = tm

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='Caesure: a python bitcoin server/node')
    p.add_argument('-t', '--testnet', action='store_true', help='use Bitcoin testnet')
    p.add_argument('-m', '--monitor', action='store_true', help='run the monitor on /tmp/caesure.bd')
    p.add_argument('-a', '--webadmin', action='store_true', help='run the web admin interface at http://localhost:8380/admin/')
    # We don't listen for connections yet, so no need for this just now
    #p.add_argument('-p', '--port', nargs=1, type=int, help='local TCP port (default: 8333 or 18333 for testnet)')
    g = p.add_mutually_exclusive_group()
    g.add_argument('-c', '--client', nargs=2, help='run as a client of SERVERADDRESS', metavar=('MYADDRESS', 'SERVERADDRESS'))
    g.add_argument('-n', '--network', nargs=1, help='run in network mode at MYADDRESS', metavar='MYADDRESS')
    args = p.parse_args()

    if args.testnet:
        BITCOIN_PORT = 18333
        BITCOIN_MAGIC = '\xfa\xbf\xb5\xda'
        BLOCKS_PATH = 'blocks.testnet.bin'
        genesis_block_hash = '00000007199508e34a9ff81e6ec0c477a4cccff2a4767a8eee39c11db367b008'

    # mount the block database
    the_block_db = block_db()
    the_dispatcher = dispatcher()
    network = False

    #if args.port is not None:
    #    MY_PORT = args.port[0]

    # client mode
    if args.client is not None:
        [my_addr, other_addr] = args.client
        bc = connection (other_addr)
        network = True

    # network mode
    if args.network is not None:
        my_addr = args.network[0]
        addrs = dns_seed()
        for addr in addrs:
            connection (addr)
        network = True

    do_monitor = args.monitor
    do_admin   = args.webadmin

    if network:
        if do_monitor:
            import coro.backdoor
            coro.spawn (coro.backdoor.serve, unix_path='/tmp/caesure.bd')
        if do_admin:
            import coro.http
            import webadmin
            import zlib
            h = coro.http.server()
            coro.spawn (h.start, (('127.0.0.1', 8380)))
            h.push_handler (webadmin.handler())
            h.push_handler (coro.http.handlers.coro_status_handler())
            h.push_handler (coro.http.handlers.favicon_handler (zlib.compress (webadmin.favicon)))
        coro.event_loop()
    else:
        # database browsing mode
        db = the_block_db # alias
        
    # this is just so I can use the coro profiler
    #import coro.profiler
    #coro.spawn (build_txmap)
    #coro.event_loop()

########NEW FILE########
__FILENAME__ = script
# -*- Mode: Python -*-

import hashlib
import struct
from pprint import pprint as pp
import sys

W = sys.stderr.write

# confusion: I believe 'standard' transactions != 'valid scripts', I think They
#  have chosen a subset of legal transactions that are considered 'standard'.

# status: passes the 'valid' unit tests from bitcoin/bitcoin, but does
#   not yet fail all the 'invalid' tests. [mostly constraints like op
#   count, stack size, etc...]

class OPCODES:
    # push value
    OP_0 = 0x00
    OP_FALSE = OP_0
    OP_PUSHDATA1 = 0x4c
    OP_PUSHDATA2 = 0x4d
    OP_PUSHDATA4 = 0x4e
    OP_1NEGATE = 0x4f
    OP_RESERVED = 0x50
    OP_1 = 0x51
    OP_TRUE=OP_1
    OP_2 = 0x52
    OP_3 = 0x53
    OP_4 = 0x54
    OP_5 = 0x55
    OP_6 = 0x56
    OP_7 = 0x57
    OP_8 = 0x58
    OP_9 = 0x59
    OP_10 = 0x5a
    OP_11 = 0x5b
    OP_12 = 0x5c
    OP_13 = 0x5d
    OP_14 = 0x5e
    OP_15 = 0x5f
    OP_16 = 0x60

    # control
    OP_NOP = 0x61
    OP_VER = 0x62
    OP_IF = 0x63
    OP_NOTIF = 0x64
    OP_VERIF = 0x65
    OP_VERNOTIF = 0x66
    OP_ELSE = 0x67
    OP_ENDIF = 0x68
    OP_VERIFY = 0x69
    OP_RETURN = 0x6a

    # stack ops
    OP_TOALTSTACK = 0x6b
    OP_FROMALTSTACK = 0x6c
    OP_2DROP = 0x6d
    OP_2DUP = 0x6e
    OP_3DUP = 0x6f
    OP_2OVER = 0x70
    OP_2ROT = 0x71
    OP_2SWAP = 0x72
    OP_IFDUP = 0x73
    OP_DEPTH = 0x74
    OP_DROP = 0x75
    OP_DUP = 0x76
    OP_NIP = 0x77
    OP_OVER = 0x78
    OP_PICK = 0x79
    OP_ROLL = 0x7a
    OP_ROT = 0x7b
    OP_SWAP = 0x7c
    OP_TUCK = 0x7d

    # splice ops
    OP_CAT = 0x7e
    OP_SUBSTR = 0x7f
    OP_LEFT = 0x80
    OP_RIGHT = 0x81
    OP_SIZE = 0x82

    # bit logic
    OP_INVERT = 0x83
    OP_AND = 0x84
    OP_OR = 0x85
    OP_XOR = 0x86
    OP_EQUAL = 0x87
    OP_EQUALVERIFY = 0x88
    OP_RESERVED1 = 0x89
    OP_RESERVED2 = 0x8a

    # numeric
    OP_1ADD = 0x8b
    OP_1SUB = 0x8c
    OP_2MUL = 0x8d
    OP_2DIV = 0x8e
    OP_NEGATE = 0x8f
    OP_ABS = 0x90
    OP_NOT = 0x91
    OP_0NOTEQUAL = 0x92

    OP_ADD = 0x93
    OP_SUB = 0x94
    OP_MUL = 0x95
    OP_DIV = 0x96
    OP_MOD = 0x97
    OP_LSHIFT = 0x98
    OP_RSHIFT = 0x99
    OP_BOOLAND = 0x9a
    OP_BOOLOR = 0x9b
    OP_NUMEQUAL = 0x9c
    OP_NUMEQUALVERIFY = 0x9d
    OP_NUMNOTEQUAL = 0x9e
    OP_LESSTHAN = 0x9f
    OP_GREATERTHAN = 0xa0
    OP_LESSTHANOREQUAL = 0xa1
    OP_GREATERTHANOREQUAL = 0xa2
    OP_MIN = 0xa3
    OP_MAX = 0xa4
    OP_WITHIN = 0xa5

    # crypto
    OP_RIPEMD160 = 0xa6
    OP_SHA1 = 0xa7
    OP_SHA256 = 0xa8
    OP_HASH160 = 0xa9
    OP_HASH256 = 0xaa
    OP_CODESEPARATOR = 0xab
    OP_CHECKSIG = 0xac
    OP_CHECKSIGVERIFY = 0xad
    OP_CHECKMULTISIG = 0xae
    OP_CHECKMULTISIGVERIFY = 0xaf

    # expansion
    OP_NOP1 = 0xb0
    OP_NOP2 = 0xb1
    OP_NOP3 = 0xb2
    OP_NOP4 = 0xb3
    OP_NOP5 = 0xb4
    OP_NOP6 = 0xb5
    OP_NOP7 = 0xb6
    OP_NOP8 = 0xb7
    OP_NOP9 = 0xb8
    OP_NOP10 = 0xb9

    # template matching params
    OP_SMALLINTEGER = 0xfa
    OP_PUBKEYS = 0xfb
    OP_PUBKEYHASH = 0xfd
    OP_PUBKEY = 0xfe

    OP_INVALIDOPCODE = 0xff

opcode_map_fwd = {}
opcode_map_rev = {}

for name in dir(OPCODES):
    if name.startswith ('OP_'):
        val = getattr (OPCODES, name)
        globals()[name] = val
        opcode_map_fwd[name] = val
        opcode_map_rev[val] = name

def render_int (n):
    # little-endian byte stream
    if n < 0:
        neg = True
        n = -n
    else:
        neg = False
    r = []
    while n:
        r.append (n & 0xff)
        n >>= 8
    if neg:
        if r[-1] & 0x80:
            r.append (0x80)
        else:
            r[-1] |= 0x80
    elif r and (r[-1] & 0x80):
        r.append (0)
    return ''.join ([chr(x) for x in r])

def unrender_int (s):
    n = 0
    ls = len(s)
    neg = False
    for i in range (ls-1,-1,-1):
        b = ord (s[i])
        n <<= 8
        if i == ls-1 and b & 0x80:
            neg = True
            n |= b & 0x7f
        else:
            n |= b
    if neg:
        return -n
    else:
        return n

# I can't tell for sure, but it really looks like the operator<<(vch) in script.h
#  assumes little-endian?
def make_push_str (s):
    ls = len(s)
    if ls < OP_PUSHDATA1:
        return chr(ls) + s
    elif ls < 0xff:
        return chr(OP_PUSHDATA1) + chr(ls) + s
    elif ls < 0xffff:
        return chr(OP_PUSHDATA2) + struct.pack ("<H", ls) + s
    else:
        return chr(OP_PUSHDATA4) + struct.pack ("<L", ls) + s

def make_push_int (n):
    if n == 0:
        return chr(OP_0)
    elif n == 1:
        return chr(OP_1)
    elif n >= 2 and n <= 16:
        return chr(80+n)
    else:
        return make_push_str (render_int (n))

class ScriptError (Exception):
    pass
class ScriptFailure (ScriptError):
    pass
class BadScript (ScriptError):
    pass
class ScriptUnderflow (ScriptError):
    pass
class StackUnderflow (ScriptError):
    pass
class AltStackUnderflow (ScriptError):
    pass
class DisabledError (ScriptError):
    pass
class BadNumber (ScriptError):
    pass

class script_parser:
    def __init__ (self, script):
        self.s = script
        self.pos = 0
        self.length = len (script)

    def peek (self):
        return ord (self.s[self.pos])

    def next (self):
        result = ord (self.s[self.pos])
        self.pos += 1
        return result

    def get_str (self, n=1):
        result = self.s[self.pos:self.pos+n]
        self.pos += n
        if len(result) != n:
            raise ScriptUnderflow (self.pos)
        return result

    def get_int (self, count=4):
        bl = [self.next() for x in range (count)]
        n = 0
        for b in reversed (bl):
            n <<= 8
            n |= b
        return n

    def parse (self):
        code = []
        last_insn = None
        code_sep = None
        while self.pos < self.length:
            insn = self.next()
            if insn >= 0 and insn <= 75:
                code.append ((KIND_PUSH, self.get_str (insn)))
            elif insn == OP_PUSHDATA1:
                size = self.next()
                code.append ((KIND_PUSH, self.get_str (size)))
            elif insn == OP_PUSHDATA2:
                code.append ((KIND_PUSH, self.get_str (self.get_int (2))))
            elif insn == OP_PUSHDATA4:
                code.append ((KIND_PUSH, self.get_str (self.get_int (4))))
            elif insn in (OP_IF, OP_NOTIF):
                sub0, end0 = self.parse()
                sense = insn == OP_IF
                if end0 == OP_ELSE:
                    sub1, end1 = self.parse()
                    if end1 != OP_ENDIF:
                        raise BadScript (self.pos)
                    code.append ((KIND_COND, sense, sub0, sub1))
                elif end0 != OP_ENDIF:
                    raise BadScript (self.pos)
                else:
                    code.append ((KIND_COND, sense, sub0, None))
            elif insn in (OP_ELSE, OP_ENDIF):
                return code, insn
            elif insn == OP_CODESEPARATOR:
                code_sep = self.pos
            elif insn in (OP_CHECKSIG, OP_CHECKSIGVERIFY, OP_CHECKMULTISIG, OP_CHECKMULTISIGVERIFY):
                #code.append ((KIND_CHECK, insn, self.s[code_sep:self.pos]))
                # XXX goes to the end of the script, not stopping at this position.
                code.append ((KIND_CHECK, insn, self.s[code_sep:]))
            elif insn in (OP_VERIF, OP_VERNOTIF):
                raise BadScript (self.pos)
            else:
                if insn in disabled:
                    raise DisabledError (self.pos)
                else:
                    #insn_name = opcode_map_rev.get (insn, insn)
                    code.append ((KIND_OP, insn))
            last_insn = insn
        return code, None

def unparse_script (p):
    r = []
    for insn in p:
        kind = insn[0]
        if kind == KIND_PUSH:
            _, data = insn
            r.append (make_push_str (data))
        elif kind == KIND_COND:
            _, sense, sub0, sub1 = insn
            if sense:
                op = OP_IF
            else:
                op = OP_NOTIF
            r.append (chr (op))
            r.append (unparse_script (sub0))
            if sub1:
                r.append (chr (OP_ELSE))
                r.append (unparse_script (sub1))
            r.append (chr (OP_ENDIF))
        elif kind == KIND_CHECK:
            _, op, _ = insn
            r.append (chr (op))
        elif kind == KIND_OP:
            _, op = insn
            r.append (chr (op))
    return ''.join (r)

KIND_PUSH  = 0
KIND_COND  = 1
KIND_OP    = 2
KIND_CHECK = 3

def pprint_script (p):
    r = []
    for insn in p:
        kind = insn[0]
        if kind == KIND_PUSH:
            _, data = insn
            if not data:
                r.append ('')
            else:
                r.append ('0x' + data.encode ('hex'))
        elif kind == KIND_COND:
            _, sense, sub0, sub1 = insn
            if sense:
                op = 'IF'
            else:
                op = 'NOTIF'
            r.append ([op] + pprint_script (sub0))
            if sub1:
                r.append (['ELSE'] + pprint_script (sub1))
        elif kind == KIND_CHECK:
            _, op, _ = insn
            r.append (opcode_map_rev[op])
        elif kind == KIND_OP:
            _, op = insn
            r.append (opcode_map_rev.get (op, 'OP_INVALID_%x' % (op,)))
    return r

def remove_codeseps (p):
    r = []
    for insn in p:
        if insn[0] == KIND_OP and insn[1] == 'OP_CODESEPARATOR':
            pass
        elif insn[0] == KIND_COND:
            _, sense, sub0, sub1 = insn
            sub0 = remove_codeseps (sub0)
            if sub1:
                sub1 = remove_codeseps (sub1)
            r.append ((KIND_COND, sense, sub0, sub1))
        else:
            r.append (insn)
    return r

def is_true (v):
    # check against the two forms of ZERO
    return v not in ('', '\x80')

lo32 = -(2**31)
hi32 = (2**31)-1

def check_int (n):
    if not (lo32 <= n <= hi32):
        raise BadNumber
    return n

class machine:
    def __init__ (self):
        self.stack = []
        self.altstack = []
        
    def clear_alt (self):
        self.altstack = []

    def top (self):
        return self.stack[-1]

    def pop (self):
        return self.stack.pop()

    def push (self, item):
        self.stack.append (item)

    def push_int (self, n):
        self.stack.append (render_int (n))

    # the wiki says that numeric ops are limited to 32-bit integers,
    #  however at least one of the test cases (which try to enforce this)
    #  seem to violate this:
    # ["2147483647 DUP ADD", "4294967294 EQUAL", ">32 bit EQUAL is valid"],
    # by adding INT32_MAX to itself we overflow a signed 32-bit int.
    # NOTE: according to Gavin Andresen, only the input operands have this limitation,
    #   the output can overflow... a script quirk.

    def pop_int (self, check=True):
        n = unrender_int (self.pop())
        if check:
            check_int (n)
        return n

    def push_alt (self):
        self.altstack.append (self.pop())

    def pop_alt (self):
        self.push (self.altstack.pop())

    def need (self, n):
        if len(self.stack) < n:
            raise StackUnderflow

    def needalt (self, n):
        if len(self.altstack) < n:
            raise AltStackUnderflow

    def dump (self):
        W ('  alt=%r\n' % self.altstack,)
        W ('stack=%r\n' % self.stack,)

    def truth (self):
        return is_true (self.pop())

# machine with placeholders for things we need to perform tx verification

class verifying_machine (machine):

    def __init__ (self, prev_outscript, tx, index):
        machine.__init__ (self)
        self.prev_outscript = prev_outscript
        self.tx = tx
        self.index = index

    def check_sig (self, s):
        pub_key = self.pop()
        sig = self.pop()
        s0 = parse_script (s)
        s1 = remove_codeseps (s0)
        s2 = remove_sigs (s1, [sig]) # rare?
        s3 = unparse_script (s2)
        return self.check_one_sig (pub_key, sig, s3)

    def check_one_sig (self, pub, sig, s):
        sig, hash_type = sig[:-1], ord(sig[-1])
        if hash_type != 1:
            W ('hash_type=%d\n' % (hash_type,))
            raise NotImplementedError
        to_hash = self.tx.get_ecdsa_hash (self.index, s, hash_type)
        vhash = dhash (to_hash)
        return self.tx.verify1 (pub, sig, vhash)

    # having trouble understanding if there is a difference between: CHECKMULTISIG and P2SH.
    # https://en.bitcoin.it/wiki/BIP_0016
    def check_multi_sig (self, s):
        npub = self.pop_int()
        #print 'npub=', npub
        pubs = [self.pop() for x in range (npub)]
        nsig = self.pop_int()
        #print 'nsig=', nsig
        sigs = [self.pop() for x in range (nsig)]
        
        s0 = parse_script (s)
        s1 = remove_codeseps (s0)
        s2 = remove_sigs (s1, sigs) # rare?
        s3 = unparse_script (s2)
        
        for sig in sigs:
            nmatch = 0
            #print 'checking sig...'
            for pub in pubs:
                if self.check_one_sig (pub, sig, s3):
                    nmatch += 1
            if nmatch == 0:
                #print 'sig matched no pubs'
                return 0
        return 1

def remove_sigs (p, sigs):
    "remove any of <sigs> from <p>"
    r = []
    for insn in p:
        kind = insn[0]
        if kind == KIND_PUSH and insn[1] in sigs:
            pass
        else:
            r.append (insn)
    return r

def parse_script (s):
    code, end = script_parser(s).parse()
    assert (end is None)
    return code

from caesure._script import parse_script, unparse_script

def do_equal (m):
    m.need(2)
    v0 = m.pop()
    v1 = m.pop()
    if v0 == v1:
        m.push_int (1)
    else:
        m.push_int (0)
def do_verify (m):
    m.need (1)
    if not m.truth():
        raise ScriptFailure
def do_equalverify (m):
    m.need (2)
    do_equal (m)
    do_verify (m)
def do_1negate (m):
    m.push_int (-1)
def do_nop (m):
    pass
def do_dup (m):
    m.need (1)
    m.push (m.top())
def do_toaltstack (m):
    m.need (1)
    m.push_alt()
def do_fromaltstack (m):
    m.needalt (1)
    m.pop_alt()
def do_drop (m):
    m.need (1)
    m.pop()
def do_ifdup (m):
    m.need (1)
    v = m.top()
    if is_true (v):
        m.push (v)
def do_depth (m):
    m.push_int (len (m.stack))
def do_nip (m):
    m.need (2)
    v = m.pop()
    m.pop()
    m.push (v)
def do_over (m):
    m.need (2)
    m.push (m.stack[-2])
def do_pick (m):
    m.need (1)
    n = 1 + m.pop_int()
    if n < 1:
        raise BadScript
    m.need (n)
    m.push (m.stack[-n])
def do_roll (m):
    m.need (1)
    n = 1 + m.pop_int()
    if n < 1:
        raise BadScript
    m.need (n)
    v = m.stack[-n]
    del m.stack[-n]
    m.push (v)
def do_rot (m):
    m.need (3)
    v = m.stack[-3]
    del m.stack[-3]
    m.push (v)
def do_swap (m):
    m.need (2)
    m.stack[-1], m.stack[-2] = m.stack[-2], m.stack[-1]
def do_tuck (m):
    m.need (2)
    m.stack.insert (-2, m.top())
def do_2drop (m):
    m.need (2)
    m.pop()
    m.pop()
def do_2dup (m):
    m.need (2)
    v0, v1 = m.stack[-2:]
    m.stack.extend ([v0, v1])
def do_3dup (m):
    m.need (3)
    v0, v1, v2 = m.stack[-3:]
    m.stack.extend ([v0, v1, v2])
def do_2over (m):
    m.need (4)
    v0, v1 = m.stack[-4:-2]
    m.stack.extend ([v0, v1])
def do_2rot (m):
    m.need (6)
    v0, v1 = m.stack[-6:-4]
    del m.stack[-6:-4]
    m.stack.extend ([v0, v1])
def do_2swap (m):
    m.need (4)
    v0, v1 = m.stack[-4:-2]
    del m.stack[-4:-2]
    m.stack.extend ([v0, v1])
def do_cat (m):
    v1 = m.pop()
    v0 = m.pop()
    m.push (v0 + v1)
def do_substr (m):
    m.need (3)
    n = m.pop_int()
    p = m.pop_int()
    s = m.pop()
    if not (n > 0 and n < len (s)):
        raise ScriptFailure
    if not (p >= 0 and p < (len(s)-1)):
        raise ScriptFailure
    m.push (s[p:p+n])
def do_left (m):
    m.need (2)
    n = m.pop_int()
    s = m.pop()
    if n < 0 or n > (len(s)-1):
        raise ScriptFailure
    m.push (s[0:n])
def do_right (m):
    m.need (2)
    n = m.pop_int()
    s = m.pop()
    if n < 0 or n > (len(s)-1):
        raise ScriptFailure
    m.push (s[n:])
def do_size (m):
    m.need (1)
    m.push_int (len (m.top()))
def do_1add (m):
    m.need (1)
    m.push_int (1 + m.pop_int())
def do_1sub (m):
    m.need (1)
    m.push_int (m.pop_int() - 1)
def do_2mul (m):
    m.need (1)
    m.push_int (2 * m.pop_int())
def do_2div (m):
    m.need (1)
    m.push_int (m.pop_int()>>1)
def do_negate (m):
    m.need (1)
    m.push_int (-m.pop_int())
def do_abs (m):
    m.push_int (abs (m.pop_int()))
def do_not (m):
    m.need (1)
    if m.truth():
        m.push_int (0)
    else:
        m.push_int (1)
def do_0notequal (m):
    if m.pop_int() == 0:
        m.push_int (0)
    else:
        m.push_int (1)
def do_add (m):
    m.need (2)
    m.push_int (m.pop_int() + m.pop_int())
def do_sub (m):
    m.need (2)
    v1 = m.pop_int()
    v0 = m.pop_int()
    m.push_int (v0 - v1)
def do_mul (m):
    m.need (2)
    m.push_int (m.pop_int() * m.pop_int())
def do_div (m):
    m.need (2)
    v1 = m.pop_int()
    v0 = m.pop_int()
    m.push_int (v0 // v1)
def do_mod (m):
    m.need (2)
    v1 = m.pop_int()
    v0 = m.pop_int()
    m.push_int (v0 % v1)
def do_lshift (m):
    m.need (2)
    n = m.pop_int()
    v = m.pop_int()
    if n < 0 or n > 2048:
        raise ScriptFailure
    m.push_int (v << n)
def do_rshift (m):
    m.need (2)
    n = m.pop_int()
    v = m.pop_int()
    if n < 0 or n > 2048:
        raise ScriptFailure
    m.push_int (v >> n)
def do_booland (m):
    m.need (2)
    v0 = m.pop_int()
    v1 = m.pop_int()
    m.push_int (v0 and v1)
def do_boolor (m):
    m.need (2)
    v0 = m.pop_int()
    v1 = m.pop_int()
    m.push_int (v0 or v1)
def do_numequal (m):
    m.need (2)
    m.push_int (m.pop_int() == m.pop_int())
def do_numequalverify (m):
    do_numequal (m)
    do_verify (m)
def do_numnotequal (m):
    m.need (2)
    m.push_int (m.pop_int() != m.pop_int())
def do_lessthan (m):
    m.need (2)
    v1 = m.pop_int()
    v0 = m.pop_int()
    m.push_int (v0 < v1)
def do_greaterthan (m):
    m.need (2)
    v1 = m.pop_int()
    v0 = m.pop_int()
    m.push_int (v0 > v1)
def do_lessthanorequal (m):
    m.need (2)
    v1 = m.pop_int()
    v0 = m.pop_int()
    m.push_int (v0 <= v1)
def do_greaterthanorequal (m):
    m.need (2)
    v1 = m.pop_int()
    v0 = m.pop_int()
    m.push_int (v0 >= v1)
def do_min (m):
    m.need (2)
    m.push_int (min (m.pop_int(), m.pop_int()))
def do_max (m):
    m.need (2)
    m.push_int (max (m.pop_int(), m.pop_int()))
def do_within (m):
    m.need (3)
    v2 = m.pop_int()
    v1 = m.pop_int()
    v0 = m.pop_int()
    m.push_int (v1 <= v0 < v2)
def do_ripemd160 (m):
    m.need (1)
    s = m.pop()
    h0 = hashlib.new ('ripemd160')
    h0.update (s)
    m.push (h0.digest())
def do_sha1 (m):
    m.need (1)
    s = m.pop()
    h0 = hashlib.new ('sha1')
    h0.update (s)
    m.push (h0.digest())
def do_sha256 (m):
    m.need (1)
    s = m.pop()
    h0 = hashlib.new ('sha256')
    h0.update (s)
    m.push (h0.digest())
def do_hash160 (m):
    m.need (1)
    s = m.pop()
    h0 = hashlib.new ('sha256')
    h0.update (s)
    h1 = hashlib.new ('ripemd160')
    h1.update (h0.digest())
    m.push (h1.digest())
def do_hash256 (m):
    m.need (1)
    s = m.pop()
    h0 = hashlib.new ('sha256')
    h0.update (s)
    h1 = hashlib.new ('sha256')
    h1.update (h0.digest())
    m.push (h1.digest())
def do_nop1 (m):
    pass
do_nop2 = do_nop1
do_nop3 = do_nop1
do_nop4 = do_nop1
do_nop5 = do_nop1
do_nop6 = do_nop1
do_nop7 = do_nop1
do_nop8 = do_nop1
do_nop9 = do_nop1
do_nop10 = do_nop1
    
# these will probably be done inline when the eval engine is moved into cython
def do_1 (m):
    m.push_int (1)
def do_2 (m):
    m.push_int (2)
def do_3 (m):
    m.push_int (3)
def do_4 (m):
    m.push_int (4)
def do_5 (m):
    m.push_int (5)
def do_6 (m):
    m.push_int (6)
def do_7 (m):
    m.push_int (7)
def do_8 (m):
    m.push_int (8)
def do_9 (m):
    m.push_int (9)
def do_10 (m):
    m.push_int (10)
def do_11 (m):
    m.push_int (11)
def do_12 (m):
    m.push_int (12)
def do_13 (m):
    m.push_int (13)
def do_14 (m):
    m.push_int (14)
def do_15 (m):
    m.push_int (15)
def do_16 (m):
    m.push_int (16)

# The disabled opcodes are in a test near the top of EvalScript in script.cpp.
# The unit tests require that these fail.
disabled = set ([
    OP_CAT, OP_SUBSTR, OP_LEFT, OP_RIGHT, OP_INVERT, OP_AND, OP_OR, OP_XOR,
    OP_2MUL, OP_2DIV, OP_MUL, OP_DIV, OP_MOD, OP_LSHIFT, OP_RSHIFT,
    ])

op_funs = {}
g = globals()
for name in g.keys():
    if name.startswith ('do_'):
        opname = ('op_%s' % (name[3:])).upper()
        code = opcode_map_fwd[opname]
        op_funs[code] = g[name]

from hashlib import sha256

def dhash (s):
    return sha256(sha256(s).digest()).digest()

def pinsn (insn):
    kind = insn[0]
    if kind == KIND_PUSH:
        print 'push %r' % (insn[1])
    elif kind == KIND_OP:
        _, op = insn
        print '%s' % (opcode_map_rev.get (op, str(op)))
    elif kind == KIND_COND:
        if insn[1]:
            print 'IF'
        else:
            print 'NOTIF'
    elif kind == KIND_CHECK:
        op = insn[1]
        print '%s' % (opcode_map_rev.get (op, str(op)))

def eval_script (m, s):
    for insn in s:
        #print '---------------'
        #m.dump()
        #pinsn (insn)
        kind = insn[0]
        if kind == KIND_PUSH:
            _, data = insn
            m.push (data)
        elif kind == KIND_OP:
            _, op = insn
            op_funs[op](m)
        elif kind == KIND_COND:
            _, sense, tcode, fcode = insn
            truth = m.truth()
            if (sense and truth) or (not sense and not truth):
                eval_script (m, tcode)
            elif fcode is not None:
                eval_script (m, fcode)
        elif kind == KIND_CHECK:
            _, op, s0 = insn
            if op in (OP_CHECKSIG, OP_CHECKSIGVERIFY):
                result = m.check_sig (s0)
                if op == OP_CHECKSIGVERIFY:
                    do_verify (m)
                return result
            elif op in (OP_CHECKMULTISIG, OP_CHECKMULTISIGVERIFY):
                result = m.check_multi_sig (s0)
                if op == OP_CHECKMULTISIGVERIFY:
                    do_verify (m)
                return result
            else:
                raise NotImplementedError
        else:
            raise ValueError ("unknown kind: %r" % (kind,))
    # notify the caller when the script does *not* end in a CHECKSIG operation.
    return None

########NEW FILE########
__FILENAME__ = wallet
# -*- Mode: Python -*-

# unused - temporary holding spot for the wallet code taken out of
#   caesure.  eventually I'll discover whatever sort of official rpc
#   calls exist to make it possible to have/use light clients and
#   implement whatever side of that I need.

# wallet file format: (<8 bytes of size> <private-key>)+
class wallet:

    # self.keys  : public_key -> private_key
    # self.addrs : addr -> public_key
    # self.value : addr -> { outpoint : value, ... }

    def __init__ (self, path):
        self.path = path
        self.keys = {}
        self.addrs = {}
        self.outpoints = {}
        # these will load from the cache
        self.last_block = 0
        self.total_btc = 0
        self.value = {}
        #
        try:
            file = open (path, 'rb')
        except IOError:
            file = open (path, 'wb')
            file.close()
            file = open (path, 'rb')
        while 1:
            size = file.read (8)
            if not size:
                break
            else:
                size, = struct.unpack ('<Q', size)
                key = file.read (size)
                public_key = key[-65:] # XXX
                self.keys[public_key] = key
                pub0 = rhash (public_key)
                addr = key_to_address (pub0)
                self.addrs[addr] = public_key
                self.value[addr] = {} # overriden by cache if present
        # try to load value from the cache.
        self.load_value_cache()

    def load_value_cache (self):
        db = the_block_db
        cache_path = self.path + '.cache'
        try:
            file = open (cache_path, 'rb')
        except IOError:
            pass
        else:
            self.last_block, self.total_btc, self.value = pickle.load (file)
            file.close()
        db_last = db.last_block
        if not len(self.keys):
            print 'no keys in wallet'
            self.last_block = db_last
            self.write_value_cache()
        elif db_last < self.last_block:
            print 'the wallet is ahead of the block chain.  Disabling wallet for now.'
            global the_wallet
            the_wallet = None
        elif self.last_block < db_last:
            print 'scanning %d blocks from %d-%d' % (db_last - self.last_block, self.last_block, db_last)
            self.scan_block_chain (self.last_block)
            self.last_block = db_last
            # update the cache
            self.write_value_cache()
        else:
            print 'wallet cache is caught up with the block chain'
        # update the outpoint map
        for addr, outpoints in self.value.iteritems():
            for outpoint, value in outpoints.iteritems():
                self.outpoints[outpoint] = value
        print 'total btc in wallet:', bcrepr (self.total_btc)

    def write_value_cache (self):
        cache_path = self.path + '.cache'
        file = open (cache_path, 'wb')
        self.last_block = the_block_db.last_block
        pickle.dump ((self.last_block, self.total_btc, self.value), file)
        file.close()

    def new_key (self):
        k = KEY()
        k.generate()
        key = k.get_privkey()
        size = struct.pack ('<Q', len(key))
        file = open (self.path, 'ab')
        file.write (size)
        file.write (key)
        file.close()
        pubkey = k.get_pubkey()
        addr = key_to_address (rhash (pubkey))
        self.addrs[addr] = pubkey
        self.keys[pubkey] = key
        self.value[addr] = {}
        self.write_value_cache()
        return addr

    def check_tx (self, tx):
        dirty = False
        # did we send money somewhere?
        for outpoint, iscript, sequence in tx.inputs:
            if outpoint == NULL_OUTPOINT:
                # we don't generate coins
                continue
            sig, pubkey = parse_iscript (iscript)
            if sig and pubkey:
                addr = key_to_address (rhash (pubkey))
                if self.addrs.has_key (addr):
                    if not self.value[addr].has_key (outpoint):
                        raise KeyError ("input for send tx missing?")
                    else:
                        value = self.value[addr][outpoint]
                        self.value[addr][outpoint] = 0
                        self.outpoints[outpoint] = 0
                        self.total_btc -= value
                        dirty = True
                    print 'SEND: %s %s' % (bcrepr (value), addr,)
                    #import pdb; pdb.set_trace()
        # did we receive any moneys?
        i = 0
        rtotal = 0
        index = 0
        for value, oscript in tx.outputs:
            kind, addr = parse_oscript (oscript)
            if kind == 'address' and self.addrs.has_key (addr):
                hash = tx.get_hash()
                outpoint = hash, index
                if self.value[addr].has_key (outpoint):
                    raise KeyError ("outpoint already present?")
                else:
                    self.value[addr][outpoint] = value
                    self.outpoints[outpoint] += value
                    self.total_btc += value
                    dirty = True
                print 'RECV: %s %s' % (bcrepr (value), addr)
                rtotal += 1
            index += 1
            i += 1
        if dirty:
            self.write_value_cache()
        return rtotal

    def dump_value (self):
        addrs = self.value.keys()
        addrs.sort()
        sum = 0
        for addr in addrs:
            if len(self.value[addr]):
                print 'addr: %s' % (addr,)
                for (outpoint, index), value in self.value[addr].iteritems():
                    print '  %s %s:%d' % (bcrepr (value), outpoint.encode ('hex'), index)
                    sum += value
        print 'total: %s' % (bcrepr(sum),)

    def scan_block_chain (self, start):
        # scan the whole chain for any TX related to this wallet
        db = the_block_db
        blocks = db.num_block.keys()
        blocks.sort()
        total = 0
        for num in blocks:
            if num >= start:
                names = db.num_block[num]
                for name in names:
                    b = db[name]
                    for tx in b.transactions:
                        try:
                            n = self.check_tx (tx)
                            if len(names) > 1:
                                print 'warning: competing blocks involved in transaction!'
                            total += n
                        except:
                            print '*** bad tx'
                            tx.dump()
        print 'found %d txs' % (total,)

    def new_block (self, block):
        # only scan blocks if we have keys
        if len (self.addrs):
            for tx in block.transactions:
                self.check_tx (tx)

    def __getitem__ (self, addr):
        pubkey = self.addrs[addr]
        key = self.keys[pubkey]
        k = KEY()
        k.set_privkey (key)
        return k
    
    def build_send_request (self, value, dest_addr, fee=0):
        # first, make sure we have enough money.
        total = value + fee
        if total > self.total_btc:
            raise ValueError ("not enough funds")
        elif value <= 0:
            raise ValueError ("zero or negative value?")
        elif value < 1000000 and fee < 50000:
            # any output less than one cent needs a fee.
            raise ValueError ("fee too low")
        else:
            # now, assemble the total
            sum = 0
            inputs = []
            for addr, outpoints in self.value.iteritems():
                for outpoint, v0 in outpoints.iteritems():
                    if v0:
                        sum += v0
                        inputs.append ((outpoint, v0, addr))
                        if sum >= total:
                            break
                if sum >= total:
                    break
            # assemble the outputs
            outputs = [(value, dest_addr)]
            if sum > total:
                # we need a place to dump the change
                change_addr = self.get_change_addr()
                outputs.append ((sum - total, change_addr))
            inputs0 = []
            keys = []
            for outpoint, v0, addr in inputs:
                pubkey = self.addrs[addr]
                keys.append (self[addr])
                iscript = make_iscript ('bogus-sig', pubkey)
                inputs0.append ((outpoint, iscript, 4294967295))
            outputs0 = []
            for val0, addr0 in outputs:
                outputs0.append ((val0, make_oscript (addr0)))
            lock_time = 0
            tx = TX (inputs0, outputs0, lock_time)
            for i in range (len (inputs0)):
                tx.sign (keys[i], i)
            return tx

    def get_change_addr (self):
        # look for an empty key
        for addr, outpoints in self.value.iteritems():
            empty = True
            for outpoint, v0 in outpoints.iteritems():
                if v0 != 0:
                    empty = False
                    break
            if empty:
                # found one
                return addr
        return self.new_key()


########NEW FILE########
__FILENAME__ = ecdsa_pure
# -*- Mode: Python -*-

# Note: The ecsa module now supports secp256k1 natively, so this module needs to be redone.

# If you can't (or don't want to) use the ctypes ssl code, this drop-in
#   replacement uses the pure-python ecdsa package.  Note: it stores private keys
#   using an OID to indicate the curve, while openssl puts the curve parameters
#   in each key.  The ecdsa package doesn't understand that DER, though.  So if you
#   create a wallet using one version, you must continue to use that version.  In an
#   emergency you could write a converter.

#
# https://github.com/warner/python-ecdsa
# $ easy_install ecdsa
#

# curve parameters below were taken from: 
#  http://forum.bitcoin.org/index.php?topic=23241.msg292364#msg292364

# WORRY: are the random numbers from random.SystemRandom() good enough?

import ecdsa
import random

# secp256k1
_p  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2FL
_r  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141L
_b  = 0x0000000000000000000000000000000000000000000000000000000000000007L
_a  = 0x0000000000000000000000000000000000000000000000000000000000000000L
_Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798L
_Gy = 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8L

curve_secp256k1 = ecdsa.ellipticcurve.CurveFp (_p, _a, _b)
generator_secp256k1 = g = ecdsa.ellipticcurve.Point (curve_secp256k1, _Gx, _Gy, _r)
randrange = random.SystemRandom().randrange
secp256k1 = ecdsa.curves.Curve (
    "secp256k1",
    curve_secp256k1,
    generator_secp256k1,
    (1, 3, 132, 0, 10)
    )
# add this to the list of official NIST curves.
ecdsa.curves.curves.append (secp256k1)

class KEY:

    def __init__ (self):
        self.prikey = None
        self.pubkey = None

    def generate (self):
        self.prikey = ecdsa.SigningKey.generate (curve=secp256k1)
        self.pubkey = self.prikey.get_verifying_key()
        return self.prikey.to_der()

    def set_privkey (self, key):
        self.prikey = ecdsa.SigningKey.from_der (key)

    def set_pubkey (self, key):
        key = key[1:]
        self.pubkey = ecdsa.VerifyingKey.from_string (key, curve=secp256k1)

    def get_privkey (self):
        return self.prikey.to_der()

    def get_pubkey (self):
        return self.pubkey.to_der()

    def sign (self, hash):
        sig = self.prikey.sign_digest (hash, sigencode=ecdsa.util.sigencode_der)
        return sig.to_der()

    def verify (self, hash, sig):
        return self.pubkey.verify_digest (sig[:-1], hash, sigdecode=ecdsa.util.sigdecode_der)

########NEW FILE########
__FILENAME__ = ecdsa_ssl
# -*- Mode: Python -*-

import ctypes
import ctypes.util

ssl = ctypes.cdll.LoadLibrary (ctypes.util.find_library ('ssl'))

# this specifies the curve used with ECDSA.
NID_secp256k1 = 714 # from openssl/obj_mac.h

# Thx to Sam Devlin for the ctypes magic 64-bit fix.
def check_result (val, func, args):
    if val == 0:
        raise ValueError
    else:
        return ctypes.c_void_p (val)
ssl.EC_KEY_new_by_curve_name.restype = ctypes.c_void_p
ssl.EC_KEY_new_by_curve_name.errcheck = check_result

class KEY:

    def __init__ (self):
        self.k = ssl.EC_KEY_new_by_curve_name (NID_secp256k1)

    def __del__ (self):
        ssl.EC_KEY_free (self.k)
        self.k = None

    def generate (self):
        return ssl.EC_KEY_generate_key (self.k)

    def set_privkey (self, key):
        self.mb = ctypes.create_string_buffer (key)
        ssl.d2i_ECPrivateKey (ctypes.byref (self.k), ctypes.byref (ctypes.pointer (self.mb)), len(key))

    def set_pubkey (self, key):
        self.mb = ctypes.create_string_buffer (key)
        ssl.o2i_ECPublicKey (ctypes.byref (self.k), ctypes.byref (ctypes.pointer (self.mb)), len(key))

    def get_privkey (self):
        size = ssl.i2d_ECPrivateKey (self.k, 0)
        mb_pri = ctypes.create_string_buffer (size)
        ssl.i2d_ECPrivateKey (self.k, ctypes.byref (ctypes.pointer (mb_pri)))
        return mb_pri.raw

    def get_pubkey (self):
        size = ssl.i2o_ECPublicKey (self.k, 0)
        mb = ctypes.create_string_buffer (size)
        ssl.i2o_ECPublicKey (self.k, ctypes.byref (ctypes.pointer (mb)))
        return mb.raw

    def sign (self, hash):
        sig_size = ssl.ECDSA_size (self.k)
        mb_sig = ctypes.create_string_buffer (sig_size)
        sig_size0 = ctypes.POINTER (ctypes.c_int)()
        assert 1 == ssl.ECDSA_sign (0, hash, len (hash), mb_sig, ctypes.byref (sig_size0), self.k)
        return mb_sig.raw

    def verify (self, hash, sig):
        return ssl.ECDSA_verify (0, hash, len(hash), sig, len(sig), self.k)

########NEW FILE########
__FILENAME__ = monitor
# -*- Mode: Python -*-
#       Author: Sam Rushing <rushing@nightmare.com>

# stealing from myself.  taken from amk's medusa-0.5.4 distribution,
# then hacked about ten years into the future, buncha stuff ripped
# out.
#
# mostly useful for debugging, should not be distributed with the final client!
#

#
# python REPL channel.
#

import socket
import string
import sys
import time

import asyncore
import asynchat

class monitor_channel (asynchat.async_chat):
    try_linemode = 1

    def __init__ (self, server, sock, addr):
        asynchat.async_chat.__init__ (self, sock)
        self.server = server
        self.addr = addr
        self.set_terminator ('\r\n')
        self.data = ''
        # local bindings specific to this channel
        self.local_env = sys.modules['__main__'].__dict__.copy()
        self.push ('Python ' + sys.version + '\r\n')
        self.push (sys.copyright+'\r\n')
        self.push ('Welcome to the Monitor.  You are %r\r\n' % (self.addr,))
        self.prompt()
        self.number = server.total_sessions
        self.line_counter = 0
        self.multi_line = []

    def handle_connect (self):
        # send IAC DO LINEMODE
        self.push ('\377\375\"')

    def close (self):
        self.server.closed_sessions += 1
        asynchat.async_chat.close(self)

    def prompt (self):
        self.push ('>>> ')

    def collect_incoming_data (self, data):
        self.data = self.data + data
        if len(self.data) > 1024:
            # denial of service.
            self.push ('BCNU\r\n')
            self.close_when_done()

    def found_terminator (self):
        line = self.clean_line (self.data)
        self.data = ''
        self.line_counter += 1
        # check for special case inputs...
        if not line and not self.multi_line:
            self.prompt()
            return
        if line in ['\004', 'exit']:
            self.push ('BCNU\r\n')
            self.close_when_done()
            return
        oldout = sys.stdout
        olderr = sys.stderr
        try:
            p = output_producer(self, olderr)
            sys.stdout = p
            sys.stderr = p
            try:
                # this is, of course, a blocking operation.
                # if you wanted to thread this, you would have
                # to synchronize, etc... and treat the output
                # like a pipe.  Not Fun.
                #
                # try eval first.  If that fails, try exec.  If that fails,
                # hurl.
                try:
                    if self.multi_line:
                        # oh, this is horrible...
                        raise SyntaxError
                    co = compile (line, repr(self), 'eval')
                    result = eval (co, self.local_env)
                    method = 'eval'
                    if result is not None:
                        print repr(result)
                    self.local_env['_'] = result
                except SyntaxError:
                    try:
                        if self.multi_line:
                            if line and line[0] in [' ','\t']:
                                self.multi_line.append (line)
                                self.push ('... ')
                                return
                            else:
                                self.multi_line.append (line)
                                line =  string.join (self.multi_line, '\n')
                                co = compile (line, repr(self), 'exec')
                                self.multi_line = []
                        else:
                            co = compile (line, repr(self), 'exec')
                    except SyntaxError, why:
                        if why[0] == 'unexpected EOF while parsing':
                            self.push ('... ')
                            self.multi_line.append (line)
                            return
                        else:
                            t,v,tb = sys.exc_info()
                            del tb
                            raise t,v
                    exec co in self.local_env
                    method = 'exec'
            except:
                method = 'exception'
                self.multi_line = []
                (file, fun, line), t, v, tbinfo = asyncore.compact_traceback()
                self.log_info('%s %s %s' %(t, v, tbinfo), 'warning')
        finally:
            sys.stdout = oldout
            sys.stderr = olderr
        self.push_with_producer (p)
        self.prompt()

    # for now, we ignore any telnet option stuff sent to
    # us, and we process the backspace key ourselves.
    # gee, it would be fun to write a full-blown line-editing
    # environment, etc...
    def clean_line (self, line):
        chars = []
        for ch in line:
            oc = ord(ch)
            if oc < 127:
                if oc in [8,177]:
                    # backspace
                    chars = chars[:-1]
                else:
                    chars.append (ch)
        return string.join (chars, '')

class monitor_server (asyncore.dispatcher):

    SERVER_IDENT = 'Bitcoin Monitor Server'

    channel_class = monitor_channel

    def __init__ (self, hostname='127.0.0.1', port=8023):
        asyncore.dispatcher.__init__ (self, socket.socket (socket.AF_INET, socket.SOCK_STREAM))
        self.hostname = hostname
        self.port = port
        self.set_reuse_addr()
        self.bind ((hostname, port))
        self.log_info('%s started on port %d' % (self.SERVER_IDENT, port))
        self.listen (5)
        self.closed             = 0
        self.failed_auths = 0
        self.total_sessions = 0
        self.closed_sessions = 0

    def writable (self):
        return 0

    def handle_accept (self):
        conn, addr = self.accept()
        self.log_info ('Incoming monitor connection from %s:%d' % addr)
        self.channel_class (self, conn, addr)
        self.total_sessions += 1

# don't try to print from within any of the methods
# of this object. 8^)

class output_producer:
    def __init__ (self, channel, real_stderr):
        self.channel = channel
        self.data = ''
        # use _this_ for debug output
        self.stderr = real_stderr

    def check_data (self):
        if len(self.data) > 1<<16:
            # runaway output, close it.
            self.channel.close()

    def write (self, data):
        lines = string.splitfields (data, '\n')
        data = string.join (lines, '\r\n')
        self.data = self.data + data
        self.check_data()

    def writeline (self, line):
        self.data = self.data + line + '\r\n'
        self.check_data()

    def writelines (self, lines):
        self.data = self.data + string.joinfields (
                lines,
                '\r\n'
                ) + '\r\n'
        self.check_data()

    def flush (self):
        pass

    def softspace (self, *args):
        pass

    def more (self):
        if self.data:
            result = self.data[:512]
            self.data = self.data[512:]
            return result
        else:
            return ''

########NEW FILE########
__FILENAME__ = paper_key
# -*- Mode: Python -*-

# standalone, self-contained paper wallet generator
import ctypes
import ctypes.util
import sys
import hashlib
from hashlib import sha256

ssl = ctypes.cdll.LoadLibrary (ctypes.util.find_library ('ssl'))

# this specifies the curve used with ECDSA.
NID_secp256k1 = 714 # from openssl/obj_mac.h

# Thx to Sam Devlin for the ctypes magic 64-bit fix.
def check_result (val, func, args):
    if val == 0:
        raise ValueError
    else:
        return ctypes.c_void_p (val)

ssl.EC_KEY_new_by_curve_name.restype = ctypes.c_void_p
ssl.EC_KEY_new_by_curve_name.errcheck = check_result
ssl.EC_KEY_get0_private_key.restype = ctypes.c_void_p
ssl.EC_KEY_get0_private_key.errcheck = check_result
ssl.BN_bn2hex.restype = ctypes.c_char_p

class KEY:

    def __init__ (self):
        self.k = ssl.EC_KEY_new_by_curve_name (NID_secp256k1)

    def __del__ (self):
        ssl.EC_KEY_free (self.k)
        self.k = None

    def generate (self):
        return ssl.EC_KEY_generate_key (self.k)

    def get_privkey_bignum (self):
        pk = ssl.EC_KEY_get0_private_key (self.k)
        return ssl.BN_bn2hex (pk).decode ('hex')

    def get_pubkey_bignum (self):
        size = ssl.i2o_ECPublicKey (self.k, 0)
        if size == 0:
            raise SystemError
        else:
            mb = ctypes.create_string_buffer (size)
            ssl.i2o_ECPublicKey (self.k, ctypes.byref (ctypes.pointer (mb)))
            return mb.raw

b58_digits = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def base58_encode (n):
    l = []
    while n > 0:
        n, r = divmod (n, 58)
        l.insert (0, (b58_digits[r]))
    return ''.join (l)

def base58_decode (s):
    n = 0
    for ch in s:
        n *= 58
        digit = b58_digits.index (ch)
        n += digit
    return n

def dhash (s):
    return sha256(sha256(s).digest()).digest()

def rhash (s):
    h1 = hashlib.new ('ripemd160')
    h1.update (sha256(s).digest())
    return h1.digest()

def key_to_address (s):
    checksum = dhash ('\x00' + s)[:4]
    return '1' + base58_encode (
        int ('0x' + (s + checksum).encode ('hex'), 16)
        )

def pkey_to_address (s):
    s = '\x80' + s
    checksum = dhash (s)[:4]
    return base58_encode (
        int ((s + checksum).encode ('hex'), 16)
        )
        
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        nkeys = int (sys.argv[1])
    else:
        nkeys = 1
    for i in range (nkeys):
        k = KEY()
        k.generate()
        pri = k.get_privkey_bignum()
        pub = k.get_pubkey_bignum()
        print 'private:', pkey_to_address (pri)
        print 'public:', key_to_address (rhash (pub))
        k = None

        

########NEW FILE########
__FILENAME__ = webadmin
# -*- Mode: Python -*-

import re
import sys
import time
import zlib
import coro

from urllib import splitquery
from urlparse import parse_qs
from cgi import escape
from caesure._script import parse_script
from caesure.script import pprint_script

favicon = (
    'AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAQAAAAAAAAAAAAAAAAA'
    'AAAAAAD///8A////AP///wD9/f0A2uXsKbTN3FVFqeHlQqfe6mqhva1bsuLKj8Pfhu/v7w////8A'
    '////AP///wD///8A////AP///wD8/f0AabXfuTat7v1lrs26V7Hc0G242LSBxN2cSqvd4E2s3d2K'
    'wNKNv9LYR/z8/AH///8A////AP///wDv8/YSk7zSfkir3uJpt9i5ldToh5XU6IeV1OiHldToh5XU'
    '6IeV1OiHldToh5TU54esydNh+vr6A////wD///8AYLPgxUKo3uqV1OiHldToh5XU6IeV1OiHldTo'
    'h5XU6IeV1OiHldToh5XU6IeV1OiHlNTnh7jP1k////8A/Pz8ATSg2vpqtdW1kM3gipLQ44mV1OiH'
    'ldToh5TU54eQzeCKlNTnh5XU6IeV1OiHjcjbjYa/0ZKSzd+G5unqGY7E4ohqsc+0PVdfzQQFBvoE'
    'Bgb6OFFY0JXU6IeGwNKSAAAA/5DN4IqV1OiHWX+KtQUGBvoJDQ73UXN+vbjR2VI5pOD2WrLcyz1X'
    'X81FYmvHea29mwIDA/2U1OeHhsDSkgAAAP+QzeCKjsvdjAUGB/pql6WqlNPnh4O7zJScx9R1Xq3Y'
    'xXnA26Q9V1/NGiYp6Sc3PN4rPkTbldToh4bA0pIAAAD/kM3ginquvpsCAwP9lNPmh5XU6IeV1OiH'
    'j8LShmGs1cB9wtygPVdfzSw+RNs7VFvPLD9F25XU6IeGwNKSAAAA/5DN4IqDu8yUAAAA/YjC1JGV'
    '1OiHldToh4/D04ZGquHjUK7c2T1XX80kNDjgLkNJ2SU0OeBlkZ6tOFBX0AAAAP87VV3OapinqCU1'
    'OeAlNTrgTG14wFl/iracx9R1rdHlYlut08holaOqSmpzwk9xfL2BucmWbZupp0pqc8JKanPCSmpz'
    'wnKhsaOLx9mOTG12wUJfZ8l8sMCbuNLZU////wBFn9DiXbHYxpXU6IeV1OiHldToh5XU6IeV1OiH'
    'ldToh5XU6IeV1OiHldToh5XU6IeV1OiHk83ghuTn6Rr///8Ah8Likzat7v2GxdqUldToh5XU6IeV'
    '1OiHldToh5XU6IeV1OiHldToh5XU6IeV1OiHlNTnh7fO1lD///8A////AP39/QGtydhdSKHO3lmx'
    '2s2PzeKNldToh5XU6IeV1OiHldToh5XU6IeV1OiHlNTnh6rJ02P6+voD////AP///wD///8A////'
    'AJXH4382quv8VanQzl+028dgtNvEisnekFux2spIq97je7jPnr3R10r6+voD////AP///wD///8A'
    '////AP///wD///8A7/HxD7/P10dSruDVPqbg7mSdu7NKrOHecrrirejr7Rf///8A////AP///wD/'
    '//8A/B8AAOAPAADgBwAAgAMAAIABAAAAAQAAAAEAAAAAAAAAAAAAAAEAAIABAACAAQAAgAMAAOAH'
    'AADwDwAA/B8AAA=='
    ).decode ('base64')

from __main__ import *

# all this CSS magic is stolen from looking at the output from pident.artefact2.com
css = """
<style type="text/css">
body { font-family: monospace; }
table > tbody > tr:nth-child(odd) {
	background-color:#f0f0f0;
}
table > tbody > tr:nth-child(even) {
	background-color:#e0e0e0;
}
table { width:100%; }
tr.inrow { border:1px green; }
tr.plus > td { background-color:#80ff80; }
tr.minus > td { background-color:#ff8080; }
a.alert { color:#ff0000; }
</style>
"""

def shorten (s, w=20):
    if len(s) > w:
        return s[:w] + '&hellip;'
    else:
        return s

def shorthex (s):
    return shorten (hexify (s))

def is_normal_tx (s):
    return len(s) == 5 and s[0] == 'OP_DUP' and s[1] == 'OP_HASH160' and s[-2] == 'OP_EQUALVERIFY' and s[-1] == 'OP_CHECKSIG'

def is_pubkey_tx (s):
    return len(s) == 2 and s[1] == 'OP_CHECKSIG'

def is_p2sh_tx (s):
    return len(s) == 3 and s[0] == 'OP_HASH160' and s[2] == 'OP_EQUAL' and len(s[1]) == 42

class handler:

    def __init__ (self):
        self.pending_send = []

    def match (self, request):
        return request.path.startswith ('/admin/')

    safe_cmd = re.compile ('[a-z]+')

    def handle_request (self, request):
        parts = request.path.split ('/')[2:] # ignore ['', 'admin']
        subcmd = parts[0]
        if not subcmd:
            subcmd = 'status'
        method_name = 'cmd_%s' % (subcmd,)
        if self.safe_cmd.match (subcmd) and hasattr (self, method_name):
            request['content-type'] = 'text/html'
            request.set_deflate()
            method = getattr (self, method_name)
            request.push (
                '\r\n'.join ([
                        '<html><head>',
                        css,
                        '</head><body>',
                        '<h1>caesure admin</h1>',
                        ])
                )
            self.menu (request)
            try:
                method (request, parts)
            except SystemExit:
                raise
            except:
                request.push ('<h1>something went wrong</h1>')
                request.push ('<pre>%r</pre>' % (coro.compact_traceback(),))
            request.push ('<hr>')
            self.menu (request)
            request.push ('</body></html>')
            request.done()
        else:
            request.error (400)

    def menu (self, request):
        request.push (
            '&nbsp;&nbsp;<a href="/admin/reload">reload</a>'
            '&nbsp;&nbsp;<a href="/admin/status">status</a>'
            '&nbsp;&nbsp;<a href="/admin/block/">blocks</a>'
            '&nbsp;&nbsp;<a href="/admin/send/">send</a>'
            '&nbsp;&nbsp;<a href="/admin/connect/">connect</a>'
            '&nbsp;&nbsp;<a href="/admin/shutdown/">shutdown</a>'
            )

    def cmd_status (self, request, parts):
        db = the_block_db
        RP = request.push
        RP ('<h3>last block</h3>')
        RP ('hash[es]: %s' % (escape (repr (db.num_block[db.last_block]))))
        RP ('<br>num: %d' % (db.last_block,))
        RP ('<h3>connections</h3>')
        RP ('<table><thead><tr><th>packets</th><th>address</th><tr></thead>')
        for conn in the_connection_list:
            try:
                addr, port = conn.getpeername()
                RP ('<tr><td>%d</td><td>%s:%d</td></tr>' % (conn.packet_count, addr, port))
            except:
                RP ('<br>dead connection</br>')
        RP ('</table><hr>')

    def dump_block (self, request, b, num, name):
        RP = request.push
        RP ('\r\n'.join ([
            '<br>block: %d' % (num,),
            '<br>version: %d' % (b.version,),
            '<br>name: %s' % (name,),
            '<br>prev: %s' % (b.prev_block,),
            '<br>merk: %s' % (hexify (b.merkle_root),),
            '<br>time: %s (%s)' % (b.timestamp, time.ctime (b.timestamp)),
            '<br>bits: %s' % (b.bits,),
            '<br>nonce: %s' % (b.nonce,),
            '<br><a href="http://blockexplorer.com/b/%d">block explorer</a>' % (num,),
            '<br><a href="http://blockchain.info/block/%s">blockchain.info</a>' % (name,),
        ]))
        #RP ('<pre>%d transactions\r\n' % len(b.transactions))
        RP ('<table><thead><tr><th>num</th><th>ID</th><th>inputs</th><th>outputs</th></tr></thead>')
        for i in range (len (b.transactions)):
            self.dump_tx (request, b.transactions[i], i)
        RP ('</table>')
        #RP ('</pre>')
        
    def cmd_block (self, request, parts):
        db = the_block_db
        RP = request.push
        if len(parts) == 2 and len (parts[1]):
            name = parts[1]
            if len(name) < 64 and db.num_block.has_key (int (name)):
                name = list(db.num_block[int(name)])[0]
        else:
            name = list(db.num_block[db.last_block])[0]
        if db.has_key (name):
            b = db[name]
            num = db.block_num[name]
            RP ('<br>&nbsp;&nbsp;<a href="/admin/block/%s">First Block</a>' % (genesis_block_hash,))
            RP ('&nbsp;&nbsp;<a href="/admin/block/">Last Block</a><br>')
            if name != genesis_block_hash:
                RP ('&nbsp;&nbsp;<a href="/admin/block/%s">Prev Block</a>' % (db.prev[name],))
            else:
                RP ('&nbsp;&nbsp;Prev Block<br>')
            if db.next.has_key (name):
                names = list (db.next[name])
                if len(names) > 1:
                    longer, length = longest (names)
                    for i in range (len (names)):
                        if names[i] != longer:
                            descrip = "Next Block (Orphan Chain)"
                            aclass = ' class="alert" '
                        else:
                            descrip = "Next Block"
                            aclass = ''
                        RP ('&nbsp;&nbsp;<a href="/admin/block/%s" %s>%s</a>' % (names[i], aclass, descrip,))
                else:
                    RP ('&nbsp;&nbsp;<a href="/admin/block/%s">Next Block</a>' % (names[0],))
                RP ('<br>')
            else:
                RP ('&nbsp;&nbsp;Next Block<br>')
            self.dump_block (request, b, num, name)

    def dump_tx (self, request, tx, tx_num):
        RP = request.push
        RP ('<tr><td>%s</td><td>%s</td>\r\n' % (tx_num, shorthex (dhash (tx.raw))))
        RP ('<td><table>')
        for i in range (len (tx.inputs)):
            (outpoint, index), script, sequence = tx.inputs[i]
            RP ('<tr><td>%3d</td><td>%s:%d</td><td>%s</td></tr>' % (
                    i,
                    shorthex (outpoint),
                    index,
                    shorthex (script),
                ))
        RP ('</table></td><td><table>')
        for i in range (len (tx.outputs)):
            value, pk_script = tx.outputs[i]
            script = parse_script (pk_script)
            parsed = pprint_script (script)
            if is_normal_tx (parsed):
                h = script[2][1]
                k = key_to_address (h)
            elif is_pubkey_tx (parsed):
                pk = script[0][1]
                k = 'pk:' + key_to_address (rhash (pk))
            elif is_p2sh_tx (parsed):
                h = script[1][1]
                k = 'p2sh:' + key_to_address (h, 5)
            else:
                k = parsed
            RP ('<tr><td>%s</td><td>%s</td></tr>' % (bcrepr (value), k))
        # lock time seems to always be zero
        #RP ('</table></td><td>%s</td></tr>' % tx.lock_time,)
        RP ('</table></td></tr>')

    def cmd_reload (self, request, parts):
        new_hand = reload (sys.modules['webadmin'])
        hl = sys.modules['__main__'].h.handlers
        for i in range (len (hl)):
            if hl[i] is self:
                del hl[i]
                h0 = new_hand.handler()
                # copy over any pending send txs
                h0.pending_send = self.pending_send
                hl.append (h0)
                break
        request.push ('<h3>[reloaded]</h3>')
        self.cmd_status (request, parts)

    def match_form (self, qparts, names):
        if len(qparts) != len(names):
            return False
        else:
            for name in names:
                if not qparts.has_key (name):
                    return False
        return True

    def cmd_connect (self, request, parts):
        RP = request.push
        if request.query:
            qparts = parse_qs (request.query[1:])
            if self.match_form (qparts, ['host']):
                global bc
                ## if bc:
                ##     bc.close()
                bc = connection (qparts['host'][0])
        RP ('<form>'
            'IP Address: <input type="text" name="host" value="127.0.0.1"/><br/>'
            '<input type="submit" value="Connect"/></form>')

    def cmd_shutdown (self, request, parts):
        request.push ('<h3>Shutting down...</h3>')
        request.done()
        coro.sleep_relative (1)
        coro.set_exit()

def chain_gen (name):
    db = the_block_db
    while 1:
        if db.next.has_key (name):
            names = db.next[name]
            if len(names) > 1:
                for x in longest (names):
                    yield 1
            else:
                name = list(names)[0]
                yield 1
        else:
            break

def longest (names):
    gens = [ (name, chain_gen (name)) for name in list (names) ]
    ng = len (gens)
    left = ng
    n = 0
    while left > 1:
        for i in range (ng):
            if gens[i]:
                name, gen = gens[i]
                try:
                    gen.next()
                except StopIteration:
                    gens[i] = None
                    left -= 1
        n += 1
    [(name, _)] = [x for x in gens if x is not None]
    return name, n


########NEW FILE########
