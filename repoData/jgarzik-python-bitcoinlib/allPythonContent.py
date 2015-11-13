__FILENAME__ = base58

#
# base58.py
# Original source: git://github.com/joric/brutus.git
# which was forked from git://github.com/samrushing/caesure.git
#
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
#

from __future__ import absolute_import, division, print_function, unicode_literals

from bitcoin.serialize import Hash, ser_uint256

b58_digits = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

from binascii import hexlify, unhexlify

class Base58Error(Exception):
    pass

class InvalidBase58Error(Base58Error):
    pass

def encode(b):
    """Encode bytes to a base58-encoded string"""

    # Convert big-endian bytes to integer
    n = int('0x0' + hexlify(b).decode('utf8'), 16)

    # Divide that integer into bas58
    res = []
    while n > 0:
        n, r = divmod (n, 58)
        res.append(b58_digits[r])
    res = ''.join(res[::-1])

    # Encode leading zeros as base58 zeros
    import sys
    czero = b'\x00'
    if sys.version > '3':
        # In Python3 indexing a bytes returns numbers, not characters.
        czero = 0
    pad = 0
    for c in b:
        if c == czero: pad += 1
        else: break
    return b58_digits[0] * pad + res

def decode(s):
    """Decode a base58-encoding string, returning bytes"""
    if not s:
        return b''

    # Convert the string to an integer
    n = 0
    for c in s:
        n *= 58
        if c not in b58_digits:
            raise InvalidBase58Error('Character %r is not a valid base58 character' % c)
        digit = b58_digits.index(c)
        n += digit

    # Convert the integer to bytes
    h = '%x' % n
    if len(h) % 2:
        h = '0' + h
    res = unhexlify(h.encode('utf8'))

    # Add padding back.
    pad = 0
    for c in s[:-1]:
        if c == b58_digits[0]: pad += 1
        else: break
    return b'\x00' * pad + res


class Base58ChecksumError(Base58Error):
    pass

class CBase58Data(bytes):
    def __new__(cls, data, nVersion):
        self = super(CBase58Data, cls).__new__(cls, data)
        self.nVersion = nVersion
        return self

    def __repr__(self):
        return '%s(%s, %d)' % (self.__class__.__name__, bytes.__repr__(self), self.nVersion)

    def __str__(self):
        vs = chr(self.nVersion) + self
        check = ser_uint256(Hash(vs))[0:4]
        return encode(vs + check)

    @classmethod
    def from_str(cls, s):
        k = decode(s)
        addrbyte, data, check0 = k[0], k[1:-4], k[-4:]
        check1 = ser_uint256(Hash(addrbyte + data))[:4]
        if check0 != check1:
            raise Base58ChecksumError('Checksum mismatch: expected %r, calculated %r' % (check0, check1))
        return cls(data, ord(addrbyte))


class CBitcoinAddress(CBase58Data):
    PUBKEY_ADDRESS = 0
    SCRIPT_ADDRESS = 5
    PUBKEY_ADDRESS_TEST = 111
    SCRIPT_ADDRESS_TEST = 196

########NEW FILE########
__FILENAME__ = bignum

#
# bignum.py
#
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
#

from __future__ import absolute_import, division, print_function, unicode_literals

import struct


# generic big endian MPI format

def bn_bytes(v, have_ext=False):
    ext = 0
    if have_ext:
        ext = 1
    return ((v.bit_length()+7)//8) + ext

def bn2bin(v):
    s = bytearray()
    i = bn_bytes(v)
    while i > 0:
        s.append((v >> ((i-1) * 8)) & 0xff)
        i -= 1
    return s

def bin2bn(s):
    l = 0
    for ch in s:
        l = (l << 8) | ch
    return l

def bn2mpi(v):
    have_ext = False
    if v.bit_length() > 0:
        have_ext = (v.bit_length() & 0x07) == 0

    neg = False
    if v < 0:
        neg = True
        v = -v

    s = struct.pack(b">I", bn_bytes(v, have_ext))
    ext = bytearray()
    if have_ext:
        ext.append(0)
    v_bin = bn2bin(v)
    if neg:
        if have_ext:
            ext[0] |= 0x80
        else:
            v_bin[0] |= 0x80
    return s + ext + v_bin

def mpi2bn(s):
    if len(s) < 4:
        return None
    s_size = str(s[:4])
    v_len = struct.unpack(b">I", s_size)[0]
    if len(s) != (v_len + 4):
        return None
    if v_len == 0:
        return 0

    v_str = bytearray(s[4:])
    neg = False
    i = v_str[0]
    if i & 0x80:
        neg = True
        i &= ~0x80
        v_str[0] = i

    v = bin2bn(v_str)

    if neg:
        return -v
    return v

# bitcoin-specific little endian format, with implicit size
def mpi2vch(s):
    r = s[4:]           # strip size
    r = r[::-1]         # reverse string, converting BE->LE
    return r

def bn2vch(v):
    return str(mpi2vch(bn2mpi(v)))

def vch2mpi(s):
    r = struct.pack(b">I", len(s))   # size
    r += s[::-1]            # reverse string, converting LE->BE
    return r

def vch2bn(s):
    return mpi2bn(vch2mpi(s))


########NEW FILE########
__FILENAME__ = bloom

#
# bloom.py
#
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
#

from __future__ import absolute_import, division, print_function, unicode_literals

import struct
import math
from bitcoin.serialize import *
from bitcoin.coredefs import *
from bitcoin.core import *
from bitcoin.hash import MurmurHash3

class CBloomFilter(object):
    # 20,000 items with fp rate < 0.1% or 10,000 items and <0.0001%
    MAX_BLOOM_FILTER_SIZE = 36000
    MAX_HASH_FUNCS = 50

    UPDATE_NONE = 0
    UPDATE_ALL = 1
    UPDATE_P2PUBKEY_ONLY = 2
    UPDATE_MASK = 3

    def __init__(self, nElements, nFPRate, nTweak, nFlags):
        """Create a new bloom filter

        The filter will have a given false-positive rate when filled with the
        given number of elements.

        Note that if the given parameters will result in a filter outside the
        bounds of the protocol limits, the filter created will be as close to
        the given parameters as possible within the protocol limits. This will
        apply if nFPRate is very low or nElements is unreasonably high.

        nTweak is a constant which is added to the seed value passed to the
        hash function It should generally always be a random value (and is
        largely only exposed for unit testing)

        nFlags should be one of the UPDATE_* enums (but not _MASK)
        """
        LN2SQUARED = 0.4804530139182014246671025263266649717305529515945455
        LN2 = 0.6931471805599453094172321214581765680755001343602552
        self.vData = bytearray(int(min(-1  / LN2SQUARED * nElements * math.log(nFPRate), self.MAX_BLOOM_FILTER_SIZE * 8) / 8))
        self.nHashFuncs = int(min(len(self.vData) * 8 / nElements * LN2, self.MAX_HASH_FUNCS))
        self.nTweak = nTweak
        self.nFlags = nFlags

    def bloom_hash(self, nHashNum, vDataToHash):
        return MurmurHash3(((nHashNum * 0xFBA4C795) + self.nTweak) & 0xFFFFFFFF, vDataToHash) % (len(self.vData) * 8)

    __bit_mask = bytearray([0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80])
    def insert(self, elem):
        """Insert an element in the filter.

        elem may be a COutPoint or bytes
        """
        if isinstance(elem, COutPoint):
            elem = elem.serialize()

        if len(self.vData) == 1 and self.vData[0] == 0xff:
            return

        for i in range(0, self.nHashFuncs):
            nIndex = self.bloom_hash(i, elem)
            # Sets bit nIndex of vData
            self.vData[nIndex >> 3] |= self.__bit_mask[7 & nIndex]

    def contains(self, elem):
        """Test if the filter contains an element

        elem may be a COutPoint or bytes
        """
        if isinstance(elem, COutPoint):
            elem = elem.serialize()

        if len(self.vData) == 1 and self.vData[0] == 0xff:
            return True

        for i in range(0, self.nHashFuncs):
            nIndex = self.bloom_hash(i, elem)
            if not (self.vData[nIndex >> 3] & self.__bit_mask[7 & nIndex]):
                return False
        return True

    def IsWithinSizeConstraints(self):
        return len(self.vData) <= self.MAX_BLOOM_FILTER_SIZE and self.nHashFuncs <= self.MAX_HASH_FUNCS

    def IsRelevantAndUpdate(tx, tx_hash):
        # Not useful for a client, so not implemented yet.
        raise NotImplementedError

    __struct = struct.Struct(b'<IIB')
    def deserialize(self, f):
        self.vData = deser_string(f)
        (self.nHashFuncs,
         self.nTweak,
         self.nFlags) = self.__struct.unpack(f.read(self.__struct.size))

    def serialize(self):
        r = ser_string(self.vData)
        return r + self.__struct.pack(self.nHashFuncs, self.nTweak, self.nFlags)

########NEW FILE########
__FILENAME__ = core

#
# core.py
#
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
#

from __future__ import absolute_import, division, print_function, unicode_literals

import struct
import socket
import binascii
import time
import hashlib
from bitcoin.serialize import *
from bitcoin.coredefs import *
from bitcoin.script import CScript

class CAddress(object):
    def __init__(self, protover=PROTO_VERSION):
        self.protover = protover
        self.nTime = 0
        self.nServices = 1
        self.pchReserved = b"\x00" * 10 + b"\xff" * 2
        self.ip = "0.0.0.0"
        self.port = 0
    def deserialize(self, f):
        if self.protover >= CADDR_TIME_VERSION:
            self.nTime = struct.unpack(b"<I", f.read(4))[0]
        self.nServices = struct.unpack(b"<Q", f.read(8))[0]
        self.pchReserved = f.read(12)
        self.ip = socket.inet_ntoa(f.read(4))
        self.port = struct.unpack(b">H", f.read(2))[0]
    def serialize(self):
        r = b""
        if self.protover >= CADDR_TIME_VERSION:
            r += struct.pack(b"<I", self.nTime)
        r += struct.pack(b"<Q", self.nServices)
        r += self.pchReserved
        r += socket.inet_aton(self.ip)
        r += struct.pack(b">H", self.port)
        return r
    def __repr__(self):
        return "CAddress(nTime=%d nServices=%i ip=%s port=%i)" % (self.nTime, self.nServices, self.ip, self.port)

class CInv(object):
    typemap = {
        0: "Error",
        1: "TX",
        2: "Block"}
    def __init__(self):
        self.type = 0
        self.hash = 0
    def deserialize(self, f):
        self.type = struct.unpack(b"<i", f.read(4))[0]
        self.hash = deser_uint256(f)
    def serialize(self):
        r = b""
        r += struct.pack(b"<i", self.type)
        r += ser_uint256(self.hash)
        return r
    def __repr__(self):
        return "CInv(type=%s hash=%064x)" % (self.typemap[self.type], self.hash)

class CBlockLocator(object):
    def __init__(self):
        self.nVersion = PROTO_VERSION
        self.vHave = []
    def deserialize(self, f):
        self.nVersion = struct.unpack(b"<i", f.read(4))[0]
        self.vHave = deser_uint256_vector(f)
    def serialize(self):
        r = b""
        r += struct.pack(b"<i", self.nVersion)
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
        self.n = struct.unpack(b"<I", f.read(4))[0]
    def serialize(self):
        r = b""
        r += ser_uint256(self.hash)
        r += struct.pack(b"<I", self.n)
        return r
    def set_null(self):
        self.hash = 0
        self.n = 0xffffffff
    def is_null(self):
        return ((self.hash == 0) and (self.n == 0xffffffff))
    def copy(self, old_outpt):
        self.hash = old_outpt.hash
        self.n = old_outpt.n
    def __repr__(self):
        return "COutPoint(hash=%064x n=%i)" % (self.hash, self.n)

class CTxIn(object):
    def __init__(self):
        self.prevout = COutPoint()
        self.scriptSig = b""
        self.nSequence = 0xffffffff
    def deserialize(self, f):
        self.prevout = COutPoint()
        self.prevout.deserialize(f)
        self.scriptSig = deser_string(f)
        self.nSequence = struct.unpack(b"<I", f.read(4))[0]
    def serialize(self):
        r = b""
        r += self.prevout.serialize()
        r += ser_string(self.scriptSig)
        r += struct.pack(b"<I", self.nSequence)
        return r
    def is_final(self):
        return (self.nSequence == 0xffffffff)
    def is_valid(self):
        script = CScript()
        if not script.tokenize(self.scriptSig):
            return False
        return True
    def copy(self, old_txin):
        self.prevout = COutPoint()
        self.prevout.copy(old_txin.prevout)
        self.scriptSig = old_txin.scriptSig
        self.nSequence = old_txin.nSequence
    def __repr__(self):
        return "CTxIn(prevout=%s scriptSig=%s nSequence=%i)" % (repr(self.prevout), binascii.hexlify(self.scriptSig), self.nSequence)

class CTxOut(object):
    def __init__(self):
        self.nValue = -1
        self.scriptPubKey = b""
    def deserialize(self, f):
        self.nValue = struct.unpack(b"<q", f.read(8))[0]
        self.scriptPubKey = deser_string(f)
    def serialize(self):
        r = b""
        r += struct.pack(b"<q", self.nValue)
        r += ser_string(self.scriptPubKey)
        return r
    def is_valid(self):
        if not MoneyRange(self.nValue):
            return False
        script = CScript()
        if not script.tokenize(self.scriptPubKey):
            return False
        return True
    def copy(self, old_txout):
        self.nValue = old_txout.nValue
        self.scriptPubKey = old_txout.scriptPubKey
    def __repr__(self):
        return "CTxOut(nValue=%i.%08i scriptPubKey=%s)" % (self.nValue // 100000000, self.nValue % 100000000, binascii.hexlify(self.scriptPubKey))

class CTransaction(object):
    def __init__(self):
        # serialized
        self.nVersion = 1
        self.vin = []
        self.vout = []
        self.nLockTime = 0

        # used at runtime
        self.sha256 = None
        self.nFeesPaid = 0
        self.dFeePerKB = None
        self.dPriority = None
        self.ser_size = 0
    def deserialize(self, f):
        self.nVersion = struct.unpack(b"<i", f.read(4))[0]
        self.vin = deser_vector(f, CTxIn)
        self.vout = deser_vector(f, CTxOut)
        self.nLockTime = struct.unpack(b"<I", f.read(4))[0]
    def serialize(self):
        r = b""
        r += struct.pack(b"<i", self.nVersion)
        r += ser_vector(self.vin)
        r += ser_vector(self.vout)
        r += struct.pack(b"<I", self.nLockTime)
        return r
    def calc_sha256(self):
        if self.sha256 is None:
            self.sha256 = Hash(self.serialize())
    def is_valid(self):
        self.calc_sha256()
        if not self.is_coinbase():
            for tin in self.vin:
                if not tin.is_valid():
                    return False
        for tout in self.vout:
            if not tout.is_valid():
                return False
        return True
    def is_final(self):
        for tin in self.vin:
            if not tin.is_final():
                return False
        return True
    def is_coinbase(self):
        return len(self.vin) == 1 and self.vin[0].prevout.is_null()

    def copy(self, old_tx):
        self.nVersion = old_tx.nVersion
        self.vin = []
        self.vout = []
        self.nLockTime = old_tx.nLockTime
        self.sha256 = None

        for old_txin in old_tx.vin:
            txin = CTxIn()
            txin.copy(old_txin)
            self.vin.append(txin)

        for old_txout in old_tx.vout:
            txout = CTxOut()
            txout.copy(old_txout)
            self.vout.append(txout)

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
        self.nVersion = struct.unpack(b"<i", f.read(4))[0]
        self.hashPrevBlock = deser_uint256(f)
        self.hashMerkleRoot = deser_uint256(f)
        self.nTime = struct.unpack(b"<I", f.read(4))[0]
        self.nBits = struct.unpack(b"<I", f.read(4))[0]
        self.nNonce = struct.unpack(b"<I", f.read(4))[0]
        self.vtx = deser_vector(f, CTransaction)
    def serialize_hdr(self):
        r = b""
        r += struct.pack(b"<i", self.nVersion)
        r += ser_uint256(self.hashPrevBlock)
        r += ser_uint256(self.hashMerkleRoot)
        r += struct.pack(b"<I", self.nTime)
        r += struct.pack(b"<I", self.nBits)
        r += struct.pack(b"<I", self.nNonce)
        return r
    def serialize(self):
        r = self.serialize_hdr()
        r += ser_vector(self.vtx)
        return r
    def calc_sha256(self):
        if self.sha256 is None:
            self.sha256 = Hash(self.serialize_hdr())
    def calc_merkle(self):
        hashes = []
        for tx in self.vtx:
            if not tx.is_valid():
                return None
            tx.calc_sha256()
            hashes.append(ser_uint256(tx.sha256))
        while len(hashes) > 1:
            newhashes = []
            for i in range(0, len(hashes), 2):
                i2 = min(i+1, len(hashes)-1)
                newhashes.append(hashlib.sha256(hashlib.sha256(hashes[i] + hashes[i2]).digest()).digest())
            hashes = newhashes
        return uint256_from_str(hashes[0])
    def is_valid(self):
        self.calc_sha256()
        target = uint256_from_compact(self.nBits)
        if self.sha256 > target:
            return False
        if self.calc_merkle() != self.hashMerkleRoot:
            return False
        return True
    def __repr__(self):
        return "CBlock(nVersion=%i hashPrevBlock=%064x hashMerkleRoot=%064x nTime=%s nBits=%08x nNonce=%08x vtx=%s)" % (self.nVersion, self.hashPrevBlock, self.hashMerkleRoot, time.ctime(self.nTime), self.nBits, self.nNonce, repr(self.vtx))

class CUnsignedAlert(object):
    def __init__(self):
        self.nVersion = 1
        self.nRelayUntil = 0
        self.nExpiration = 0
        self.nID = 0
        self.nCancel = 0
        self.setCancel = []
        self.nMinVer = 0
        self.nMaxVer = 0
        self.setSubVer = []
        self.nPriority = 0
        self.strComment = b""
        self.strStatusBar = b""
        self.strReserved = b""
    def deserialize(self, f):
        self.nVersion = struct.unpack(b"<i", f.read(4))[0]
        self.nRelayUntil = struct.unpack(b"<q", f.read(8))[0]
        self.nExpiration = struct.unpack(b"<q", f.read(8))[0]
        self.nID = struct.unpack(b"<i", f.read(4))[0]
        self.nCancel = struct.unpack(b"<i", f.read(4))[0]
        self.setCancel = deser_int_vector(f)
        self.nMinVer = struct.unpack(b"<i", f.read(4))[0]
        self.nMaxVer = struct.unpack(b"<i", f.read(4))[0]
        self.setSubVer = deser_string_vector(f)
        self.nPriority = struct.unpack(b"<i", f.read(4))[0]
        self.strComment = deser_string(f)
        self.strStatusBar = deser_string(f)
        self.strReserved = deser_string(f)
    def serialize(self):
        r = b""
        r += struct.pack(b"<i", self.nVersion)
        r += struct.pack(b"<q", self.nRelayUntil)
        r += struct.pack(b"<q", self.nExpiration)
        r += struct.pack(b"<i", self.nID)
        r += struct.pack(b"<i", self.nCancel)
        r += ser_int_vector(self.setCancel)
        r += struct.pack(b"<i", self.nMinVer)
        r += struct.pack(b"<i", self.nMaxVer)
        r += ser_string_vector(self.setSubVer)
        r += struct.pack(b"<i", self.nPriority)
        r += ser_string(self.strComment)
        r += ser_string(self.strStatusBar)
        r += ser_string(self.strReserved)
        return r
    def __repr__(self):
        return "CUnsignedAlert(nVersion %d, nRelayUntil %d, nExpiration %d, nID %d, nCancel %d, nMinVer %d, nMaxVer %d, nPriority %d, strComment %s, strStatusBar %s, strReserved %s)" % (self.nVersion, self.nRelayUntil, self.nExpiration, self.nID, self.nCancel, self.nMinVer, self.nMaxVer, self.nPriority, self.strComment, self.strStatusBar, self.strReserved)

class CAlert(object):
    def __init__(self):
        self.vchMsg = b""
        self.vchSig = b""
    def deserialize(self, f):
        self.vchMsg = deser_string(f)
        self.vchSig = deser_string(f)
    def serialize(self):
        r = b""
        r += ser_string(self.vchMsg)
        r += ser_string(self.vchSig)
        return r
    def __repr__(self):
        return "CAlert(vchMsg.sz %d, vchSig.sz %d)" % (len(self.vchMsg), len(self.vchSig))


########NEW FILE########
__FILENAME__ = coredefs

#
# coredefs.py
#
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
#

from __future__ import absolute_import, division, print_function, unicode_literals

PROTO_VERSION = 60002

CADDR_TIME_VERSION = 31402

MIN_PROTO_VERSION = 209

BIP0031_VERSION = 60000

NOBLKS_VERSION_START = 32000
NOBLKS_VERSION_END = 32400

MEMPOOL_GD_VERSION = 60002

COIN = 100000000
MAX_MONEY = 21000000 * COIN

def MoneyRange(nValue):
    return 0<= nValue <= MAX_MONEY

class NetMagic(object):
    def __init__(self, msg_start, block0, checkpoints):
        self.msg_start = msg_start
        self.block0 = block0
        self.checkpoints = checkpoints

        self.checkpoint_max = 0
        for height in self.checkpoints.keys():
            if height > self.checkpoint_max:
                self.checkpoint_max = height

NETWORKS = {
 'mainnet' : NetMagic(b"\xf9\xbe\xb4\xd9",
    0x000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f,
    {
     0: 0x000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f,
         11111: 0x0000000069e244f73d78e8fd29ba2fd2ed618bd6fa2ee92559f542fdb26e7c1d,
         33333: 0x000000002dd5588a74784eaa7ab0507a18ad16a236e7b1ce69f00d7ddfb5d0a6,
         74000: 0x0000000000573993a3c9e41ce34471c079dcf5f52a0e824a81e7f953b8661a20,
        105000: 0x00000000000291ce28027faea320c8d2b054b2e0fe44a773f3eefb151d6bdc97,
        134444: 0x00000000000005b12ffd4cd315cd34ffd4a594f430ac814c91184a0d42d2b0fe,
        168000: 0x000000000000099e61ea72015e79632f216fe6cb33d7899acb35b75c8303b763,
        193000: 0x000000000000059f452a5f7340de6682a977387c17010ff6e6c3bd83ca8b1317,
    210000: 0x000000000000048b95347e83192f69cf0366076336c639f9b7228e9ba171342e,
    216116: 0x00000000000001b4f4b433e81ee46494af945cf96014816a4e2370f11b23df4e,
    }),
 'testnet3' : NetMagic(b"\x0b\x11\x09\x07",
        0x000000000933ea01ad0ee984209779baaec3ced90fa3f408719526f8d77f4943,
    {
     0: 0x000000000933ea01ad0ee984209779baaec3ced90fa3f408719526f8d77f4943,
    })
}


########NEW FILE########
__FILENAME__ = hash

#
# hash.py
#
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
#

from __future__ import absolute_import, division, print_function, unicode_literals

import struct
from bitcoin.serialize import *
from bitcoin.coredefs import *
from bitcoin.script import CScript

def ROTL32(x, r):
    assert x <= 0xFFFFFFFF
    return ((x << r) & 0xFFFFFFFF) | (x >> (32 - r))

def MurmurHash3(nHashSeed, vDataToHash):
    """MurmurHash3 (x86_32)

    Used for bloom filters. See http://code.google.com/p/smhasher/source/browse/trunk/MurmurHash3.cpp
    """

    assert nHashSeed <= 0xFFFFFFFF

    h1 = nHashSeed
    c1 = 0xcc9e2d51
    c2 = 0x1b873593

    # body
    i = 0
    while i < len(vDataToHash) - len(vDataToHash) % 4 \
          and len(vDataToHash) - i >= 4:

        k1 = struct.unpack(b"<L", vDataToHash[i:i+4])[0]

        k1 = (k1 * c1) & 0xFFFFFFFF
        k1 = ROTL32(k1, 15)
        k1 = (k1 * c2) & 0xFFFFFFFF

        h1 ^= k1
        h1 = ROTL32(h1, 13)
        h1 = (((h1*5) & 0xFFFFFFFF) + 0xe6546b64) & 0xFFFFFFFF

        i += 4

    # tail
    k1 = 0
    j = (len(vDataToHash) // 4) * 4
    import sys
    bord = ord
    if sys.version > '3':
        # In Py3 indexing bytes returns numbers, not characters
        bord = lambda x: x
    if len(vDataToHash) & 3 >= 3:
        k1 ^= bord(vDataToHash[j+2]) << 16
    if len(vDataToHash) & 3 >= 2:
        k1 ^= bord(vDataToHash[j+1]) << 8
    if len(vDataToHash) & 3 >= 1:
        k1 ^= bord(vDataToHash[j])

    k1 &= 0xFFFFFFFF
    k1 = (k1 * c1) & 0xFFFFFFFF
    k1 = ROTL32(k1, 15)
    k1 = (k1 * c2) & 0xFFFFFFFF
    h1 ^= k1

    # finalization
    h1 ^= len(vDataToHash) & 0xFFFFFFFF
    h1 ^= (h1 & 0xFFFFFFFF) >> 16
    h1 *= 0x85ebca6b
    h1 ^= (h1 & 0xFFFFFFFF) >> 13
    h1 *= 0xc2b2ae35
    h1 ^= (h1 & 0xFFFFFFFF) >> 16

    return h1 & 0xFFFFFFFF

########NEW FILE########
__FILENAME__ = key

#
# key.py - OpenSSL wrapper
# Source: git://github.com/joric/brutus.git
# which was forked from git://github.com/samrushing/caesure.git
#

import ctypes
import ctypes.util

ssl = ctypes.cdll.LoadLibrary (ctypes.util.find_library ('ssl') or 'libeay32')

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

class CKey:

    def __init__(self):
        self.POINT_CONVERSION_COMPRESSED = 2
        self.POINT_CONVERSION_UNCOMPRESSED = 4
        self.k = ssl.EC_KEY_new_by_curve_name(NID_secp256k1)

    def __del__(self):
        if ssl:
            ssl.EC_KEY_free(self.k)
        self.k = None

    def generate(self, secret=None):
        if secret:
            self.prikey = secret
            priv_key = ssl.BN_bin2bn(secret, 32, ssl.BN_new())
            group = ssl.EC_KEY_get0_group(self.k)
            pub_key = ssl.EC_POINT_new(group)
            ctx = ssl.BN_CTX_new()
            if not ssl.EC_POINT_mul(group, pub_key, priv_key, None, None, ctx):
                raise ValueError("Could not derive public key from the supplied secret.")
            ssl.EC_POINT_mul(group, pub_key, priv_key, None, None, ctx)
            ssl.EC_KEY_set_private_key(self.k, priv_key)
            ssl.EC_KEY_set_public_key(self.k, pub_key)
            ssl.EC_POINT_free(pub_key)
            ssl.BN_CTX_free(ctx)
            return self.k
        else:
            return ssl.EC_KEY_generate_key(self.k)

    def set_privkey(self, key):
        self.mb = ctypes.create_string_buffer(key)
        ssl.d2i_ECPrivateKey(ctypes.byref(self.k), ctypes.byref(ctypes.pointer(self.mb)), len(key))

    def set_pubkey(self, key):
        self.mb = ctypes.create_string_buffer(key)
        ssl.o2i_ECPublicKey(ctypes.byref(self.k), ctypes.byref(ctypes.pointer(self.mb)), len(key))

    def get_privkey(self):
        size = ssl.i2d_ECPrivateKey(self.k, 0)
        mb_pri = ctypes.create_string_buffer(size)
        ssl.i2d_ECPrivateKey(self.k, ctypes.byref(ctypes.pointer(mb_pri)))
        return mb_pri.raw

    def get_pubkey(self):
        size = ssl.i2o_ECPublicKey(self.k, 0)
        mb = ctypes.create_string_buffer(size)
        ssl.i2o_ECPublicKey(self.k, ctypes.byref(ctypes.pointer(mb)))
        return mb.raw

    def sign(self, hash):
        sig_size0 = ctypes.c_uint32()
        sig_size0.value = ssl.ECDSA_size(self.k)
        mb_sig = ctypes.create_string_buffer(sig_size0.value)
        result = ssl.ECDSA_sign(0, hash, len(hash), mb_sig, ctypes.byref(sig_size0), self.k)
        assert 1 == result
        return mb_sig.raw[:sig_size0.value]

    def verify(self, hash, sig):
        return ssl.ECDSA_verify(0, hash, len(hash), sig, len(sig), self.k) == 1

    def set_compressed(self, compressed):
        if compressed:
            form = self.POINT_CONVERSION_COMPRESSED
        else:
            form = self.POINT_CONVERSION_UNCOMPRESSED
        ssl.EC_KEY_set_conv_form(self.k, form)

if __name__ == '__main__':
    # ethalone keys
    ec_secret = '' + \
        'a0dc65ffca799873cbea0ac274015b9526505daaaed385155425f7337704883e'
    ec_private = '308201130201010420' + \
        'a0dc65ffca799873cbea0ac274015b9526505daaaed385155425f7337704883e' + \
        'a081a53081a2020101302c06072a8648ce3d0101022100' + \
        'fffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f' + \
        '300604010004010704410479be667ef9dcbbac55a06295ce870b07029bfcdb2d' + \
        'ce28d959f2815b16f81798483ada7726a3c4655da4fbfc0e1108a8fd17b448a6' + \
        '8554199c47d08ffb10d4b8022100' + \
        'fffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141' + \
        '020101a14403420004' + \
        '0791dc70b75aa995213244ad3f4886d74d61ccd3ef658243fcad14c9ccee2b0a' + \
        'a762fbc6ac0921b8f17025bb8458b92794ae87a133894d70d7995fc0b6b5ab90'

    k = CKey()
    k.generate (ec_secret.decode('hex'))
    k.set_compressed(True)
    print(k.get_privkey ().encode('hex'))
    print(k.get_pubkey().encode('hex'))
    # not sure this is needed any more: print k.get_secret().encode('hex')

    hash = 'Hello, world!'
    print(k.verify(hash, k.sign(hash)))


########NEW FILE########
__FILENAME__ = messages

#
# messages.py
#
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
#

from __future__ import absolute_import, division, print_function, unicode_literals

import struct
import time
import random
import cStringIO
from bitcoin.coredefs import *
from bitcoin.core import *

MSG_TX = 1
MSG_BLOCK = 2

class msg_version(object):
    command = b"version"
    def __init__(self, protover=PROTO_VERSION):
        self.protover = MIN_PROTO_VERSION
        self.nVersion = protover
        self.nServices = 1
        self.nTime = time.time()
        self.addrTo = CAddress(MIN_PROTO_VERSION)
        self.addrFrom = CAddress(MIN_PROTO_VERSION)
        self.nNonce = random.getrandbits(64)
        self.strSubVer = b'/python-bitcoin-0.0.1/'
        self.nStartingHeight = -1
    def deserialize(self, f):
        self.nVersion = struct.unpack(b"<i", f.read(4))[0]
        if self.nVersion == 10300:
            self.nVersion = 300
        self.nServices = struct.unpack(b"<Q", f.read(8))[0]
        self.nTime = struct.unpack(b"<q", f.read(8))[0]
        self.addrTo = CAddress(MIN_PROTO_VERSION)
        self.addrTo.deserialize(f)
        if self.nVersion >= 106:
            self.addrFrom = CAddress(MIN_PROTO_VERSION)
            self.addrFrom.deserialize(f)
            self.nNonce = struct.unpack(b"<Q", f.read(8))[0]
            self.strSubVer = deser_string(f)
            if self.nVersion >= 209:
                self.nStartingHeight = struct.unpack(b"<i", f.read(4))[0]
            else:
                self.nStartingHeight = None
        else:
            self.addrFrom = None
            self.nNonce = None
            self.strSubVer = None
            self.nStartingHeight = None
    def serialize(self):
        r = b""
        r += struct.pack(b"<i", self.nVersion)
        r += struct.pack(b"<Q", self.nServices)
        r += struct.pack(b"<q", self.nTime)
        r += self.addrTo.serialize()
        r += self.addrFrom.serialize()
        r += struct.pack(b"<Q", self.nNonce)
        r += ser_string(self.strSubVer)
        r += struct.pack(b"<i", self.nStartingHeight)
        return r
    def __repr__(self):
        return "msg_version(nVersion=%i nServices=%i nTime=%s addrTo=%s addrFrom=%s nNonce=0x%016X strSubVer=%s nStartingHeight=%i)" % (self.nVersion, self.nServices, time.ctime(self.nTime), repr(self.addrTo), repr(self.addrFrom), self.nNonce, self.strSubVer, self.nStartingHeight)

class msg_verack(object):
    command = b"verack"
    def __init__(self, protover=PROTO_VERSION):
        self.protover = protover
    def deserialize(self, f):
        pass
    def serialize(self):
        return b""
    def __repr__(self):
        return "msg_verack()"

class msg_addr(object):
    command = b"addr"
    def __init__(self, protover=PROTO_VERSION):
        self.protover = protover
        self.addrs = []
    def deserialize(self, f):
        self.addrs = deser_vector(f, CAddress, self.protover)
    def serialize(self):
        return ser_vector(self.addrs)
    def __repr__(self):
        return "msg_addr(addrs=%s)" % (repr(self.addrs))

class msg_alert(object):
    command = b"alert"
    def __init__(self, protover=PROTO_VERSION):
        self.protover = protover
        self.alert = CAlert()
    def deserialize(self, f):
        self.alert = CAlert()
        self.alert.deserialize(f)
    def serialize(self):
        r = b""
        r += self.alert.serialize()
        return r
    def __repr__(self):
        return "msg_alert(alert=%s)" % (repr(self.alert), )

class msg_inv(object):
    command = b"inv"
    def __init__(self, protover=PROTO_VERSION):
        self.protover = protover
        self.inv = []
    def deserialize(self, f):
        self.inv = deser_vector(f, CInv)
    def serialize(self):
        return ser_vector(self.inv)
    def __repr__(self):
        return "msg_inv(inv=%s)" % (repr(self.inv))

class msg_getdata(object):
    command = b"getdata"
    def __init__(self, protover=PROTO_VERSION):
        self.protover = protover
        self.inv = []
    def deserialize(self, f):
        self.inv = deser_vector(f, CInv)
    def serialize(self):
        return ser_vector(self.inv)
    def __repr__(self):
        return "msg_getdata(inv=%s)" % (repr(self.inv))

class msg_getblocks(object):
    command = b"getblocks"
    def __init__(self, protover=PROTO_VERSION):
        self.protover = protover
        self.locator = CBlockLocator()
        self.hashstop = 0
    def deserialize(self, f):
        self.locator = CBlockLocator()
        self.locator.deserialize(f)
        self.hashstop = deser_uint256(f)
    def serialize(self):
        r = b""
        r += self.locator.serialize()
        r += ser_uint256(self.hashstop)
        return r
    def __repr__(self):
        return "msg_getblocks(locator=%s hashstop=%064x)" % (repr(self.locator), self.hashstop)

class msg_getheaders(object):
    command = b"getheaders"
    def __init__(self, protover=PROTO_VERSION):
        self.protover = protover
        self.locator = CBlockLocator()
        self.hashstop = 0
    def deserialize(self, f):
        self.locator = CBlockLocator()
        self.locator.deserialize(f)
        self.hashstop = deser_uint256(f)
    def serialize(self):
        r = b""
        r += self.locator.serialize()
        r += ser_uint256(self.hashstop)
        return r
    def __repr__(self):
        return "msg_getheaders(locator=%s hashstop=%064x)" % (repr(self.locator), self.hashstop)

class msg_headers(object):
    command = b"headers"
    def __init__(self, protover=PROTO_VERSION):
        self.protover = protover
        self.headers = []
    def deserialize(self, f):
        self.headers = deser_vector(f, CBlock)
    def serialize(self):
        return ser_vector(self.headers)
    def __repr__(self):
        return "msg_headers(headers=%s)" % (repr(self.headers))

class msg_tx(object):
    command = b"tx"
    def __init__(self, protover=PROTO_VERSION):
        self.protover = protover
        self.tx = CTransaction()
    def deserialize(self, f):
        self.tx.deserialize(f)
    def serialize(self):
        return self.tx.serialize()
    def __repr__(self):
        return "msg_tx(tx=%s)" % (repr(self.tx))

class msg_block(object):
    command = b"block"
    def __init__(self, protover=PROTO_VERSION):
        self.protover = protover
        self.block = CBlock()
    def deserialize(self, f):
        self.block.deserialize(f)
    def serialize(self):
        return self.block.serialize()
    def __repr__(self):
        return "msg_block(block=%s)" % (repr(self.block))

class msg_getaddr(object):
    command = b"getaddr"
    def __init__(self, protover=PROTO_VERSION):
        self.protover = protover
    def deserialize(self, f):
        pass
    def serialize(self):
        return b""
    def __repr__(self):
        return "msg_getaddr()"

#msg_checkorder
#msg_submitorder
#msg_reply

class msg_ping(object):
    command = b"ping"
    def __init__(self, protover=PROTO_VERSION, nonce=0):
        self.protover = protover
        self.nonce = nonce
    def deserialize(self, f):
        if self.protover > BIP0031_VERSION:
            self.nonce = struct.unpack(b"<Q", f.read(8))[0]
    def serialize(self):
        r = b""
        if self.protover > BIP0031_VERSION:
            r += struct.pack(b"<Q", self.nonce)
        return r
    def __repr__(self):
        return "msg_ping(0x%x)" % (self.nonce,)

class msg_pong(object):
    command = b"pong"
    def __init__(self, protover=PROTO_VERSION, nonce=0):
        self.protover = protover
        self.nonce = nonce
    def deserialize(self, f):
        self.nonce = struct.unpack(b"<Q", f.read(8))[0]
    def serialize(self):
        r = b""
        r += struct.pack(b"<Q", self.nonce)
        return r
    def __repr__(self):
        return "msg_pong(0x%x)" % (self.nonce,)

class msg_mempool(object):
    command = b"mempool"
    def __init__(self, protover=PROTO_VERSION):
        self.protover = protover
    def deserialize(self, f):
        pass
    def serialize(self):
        return b""
    def __repr__(self):
        return "msg_mempool()"

messagemap = {
    "version": msg_version,
    "verack": msg_verack,
    "addr": msg_addr,
    "alert": msg_alert,
    "inv": msg_inv,
    "getdata": msg_getdata,
    "getblocks": msg_getblocks,
    "tx": msg_tx,
    "block": msg_block,
    "getaddr": msg_getaddr,
    "ping": msg_ping,
    "pong": msg_pong,
    "mempool": msg_mempool
}

def message_read(netmagic, f):
    try:
        recvbuf = f.read(4 + 12 + 4 + 4)
    except IOError:
        return None
    
    # check magic
    if len(recvbuf) < 4:
        return
    if recvbuf[:4] != netmagic.msg_start:
        raise ValueError("got garbage %s" % repr(recvbuf))

    # check checksum
    if len(recvbuf) < 4 + 12 + 4 + 4:
        return

    # remaining header fields: command, msg length, checksum
    command = recvbuf[4:4+12].split(b"\x00", 1)[0]
    msglen = struct.unpack(b"<i", recvbuf[4+12:4+12+4])[0]
    checksum = recvbuf[4+12+4:4+12+4+4]

    # read message body
    try:
        recvbuf += f.read(msglen)
    except IOError:
        return None

    msg = recvbuf[4+12+4+4:4+12+4+4+msglen]
    th = hashlib.sha256(msg).digest()
    h = hashlib.sha256(th).digest()
    if checksum != h[:4]:
        raise ValueError("got bad checksum %s" % repr(recvbuf))
    recvbuf = recvbuf[4+12+4+4+msglen:]

    if command in messagemap:
        f = cStringIO.StringIO(msg)
        t = messagemap[command]()
        t.deserialize(f)
        return t
    else:
        return None

def message_to_str(netmagic, message):
    command = message.command
    data = message.serialize()
    tmsg = netmagic.msg_start
    tmsg += command
    tmsg += b"\x00" * (12 - len(command))
    tmsg += struct.pack(b"<I", len(data))

    # add checksum
    th = hashlib.sha256(data).digest()
    h = hashlib.sha256(th).digest()
    tmsg += h[:4]

    tmsg += data

    return tmsg


########NEW FILE########
__FILENAME__ = rpc


# Copyright 2011 Jeff Garzik
#
# RawProxy has the following improvements over python-jsonrpc's ServiceProxy
# class:
#
# - HTTP connections persist for the life of the RawProxy object (if server
#   supports HTTP/1.1)
# - sends protocol 'version', per JSON-RPC 1.1
# - sends proper, incrementing 'id'
# - sends Basic HTTP authentication headers
# - parses all JSON numbers that look like floats as Decimal
# - uses standard Python json lib
#
# Previous copyright, from python-jsonrpc/jsonrpc/proxy.py:
#
# Copyright (c) 2007 Jan-Klaas Kollhof
#
# This file is part of jsonrpc.
#
# jsonrpc is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 2.1 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this software; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

try:
    import http.client as httplib
except ImportError:
    import httplib
import base64
import decimal
import json
import os
import platform
try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

from bitcoin.coredefs import COIN
from bitcoin.base58 import CBitcoinAddress

USER_AGENT = "AuthServiceProxy/0.1"

HTTP_TIMEOUT = 30


class JSONRPCException(Exception):
    def __init__(self, rpc_error):
        super(JSONRPCException, self).__init__('msg: %r  code: %r' %
                (rpc_error['message'], rpc_error['code']))
        self.error = rpc_error


class RawProxy(object):
    # FIXME: need a CChainParams rather than hard-coded service_port
    def __init__(self, service_url=None,
                       service_port=8332,
                       btc_conf_file=None,
                       timeout=HTTP_TIMEOUT,
                       _connection=None):
        """Low-level JSON-RPC proxy

        Unlike Proxy no conversion is done from the raw JSON objects.
        """

        if service_url is None:
            # Figure out the path to the bitcoin.conf file
            if btc_conf_file is None:
                if platform.system() == 'Darwin':
                    btc_conf_file = os.path.join(os.environ['APPDATA'], 'Bitcoin')
                elif platform.system() == 'Windows':
                    btc_conf_file = os.path.expanduser('~/Library/Application Support/Bitcoin/')
                else:
                    btc_conf_file = os.path.expanduser('~/.bitcoin')
                btc_conf_file = os.path.join(btc_conf_file, 'bitcoin.conf')

            # Extract contents of bitcoin.conf to build service_url
            with open(btc_conf_file, 'r') as fd:
                conf = {}
                for line in fd.readlines():
                    if '#' in line:
                        line = line[:line.index('#')]
                    if '=' not in line:
                        continue
                    k, v = line.split('=', 1)
                    conf[k.strip()] = v.strip()

                conf['rpcport'] = int(conf.get('rpcport', service_port))
                conf['rpcssl'] = conf.get('rpcssl', '0')

                if conf['rpcssl'].lower() in ('0', 'false'):
                    conf['rpcssl'] = False
                elif conf['rpcssl'].lower() in ('1', 'true'):
                    conf['rpcssl'] = True
                else:
                    raise ValueError('Unknown rpcssl value %r' % conf['rpcssl'])

                service_url = ('%s://%s:%s@localhost:%d' %
                    ('https' if conf['rpcssl'] else 'http',
                     conf['rpcuser'], conf['rpcpassword'],
                     conf['rpcport']))

        self.__service_url = service_url
        self.__url = urlparse.urlparse(service_url)
        if self.__url.port is None:
            port = 80
        else:
            port = self.__url.port
        self.__id_count = 0
        authpair = "%s:%s" % (self.__url.username, self.__url.password)
        authpair = authpair.encode('utf8')
        self.__auth_header = b"Basic " + base64.b64encode(authpair)

        if _connection:
            # Callables re-use the connection of the original proxy
            self.__conn = _connection
        elif self.__url.scheme == 'https':
            self.__conn = httplib.HTTPSConnection(self.__url.hostname, port,
                                                  None, None, False,
                                                  timeout)
        else:
            self.__conn = httplib.HTTPConnection(self.__url.hostname, port,
                                                 False, timeout)


    def _call(self, service_name, *args):
        self.__id_count += 1

        postdata = json.dumps({'version': '1.1',
                               'method': service_name,
                               'params': args,
                               'id': self.__id_count})
        self.__conn.request('POST', self.__url.path, postdata,
                            {'Host': self.__url.hostname,
                             'User-Agent': USER_AGENT,
                             'Authorization': self.__auth_header,
                             'Content-type': 'application/json'})

        response = self._get_response()
        if response['error'] is not None:
            raise JSONRPCException(response['error'])
        elif 'result' not in response:
            raise JSONRPCException({
                'code': -343, 'message': 'missing JSON-RPC result'})
        else:
            return response['result']


    def __getattr__(self, name):
        if name.startswith('__') and name.endswith('__'):
            # Python internal stuff
            raise AttributeError

        # Create a callable to do the actual call
        f = lambda *args: self._call(name, *args)

        # Make debuggers show <function bitcoin.rpc.name> rather than <function
        # bitcoin.rpc.<lambda>>
        f.__name__ = name
        return f


    def _batch(self, rpc_call_list):
        postdata = json.dumps(list(rpc_call_list))
        self.__conn.request('POST', self.__url.path, postdata,
                            {'Host': self.__url.hostname,
                             'User-Agent': USER_AGENT,
                             'Authorization': self.__auth_header,
                             'Content-type': 'application/json'})

        return self._get_response()

    def _get_response(self):
        http_response = self.__conn.getresponse()
        if http_response is None:
            raise JSONRPCException({
                'code': -342, 'message': 'missing HTTP response from server'})

        return json.loads(http_response.read().decode('utf8'),
                          parse_float=decimal.Decimal)


class Proxy(RawProxy):
    def __init__(self, service_url=None,
                       service_port=8332,
                       btc_conf_file=None,
                       timeout=HTTP_TIMEOUT,
                       **kwargs):
        """Create a proxy to a bitcoin RPC service

        Unlike RawProxy data is passed as objects, rather than JSON. (not yet
        fully implemented)

        If service_url is not specified the username and password are read out
        of the file btc_conf_file. If btc_conf_file is not specified
        ~/.bitcoin/bitcoin.conf or equivalent is used by default.

        Usually no arguments to Proxy() are needed; the local bitcoind will be
        used.

        timeout - timeout in seconds before the HTTP interface times out
        """
        super(Proxy, self).__init__(service_url=service_url, service_port=service_port, btc_conf_file=btc_conf_file,
                                    timeout=HTTP_TIMEOUT,
                                    **kwargs)

    def getinfo(self):
        """Returns an object containing various state info"""
        r = self._call('getinfo')
        r['balance'] = int(r['balance'] * COIN)
        r['paytxfee'] = int(r['paytxfee'] * COIN)
        return r

    def getnewaddress(self, account=None):
        """Return a new Bitcoin address for receiving payments.

        If account is not None, it is added to the address book so payments
        received with the address will be credited to account.
        """
        r = None
        if account is not None:
            r = self._call('getnewaddress', account)
        else:
            r = self._call('getnewaddress')

        return CBitcoinAddress.from_str(r)

    def getaccountaddress(self, account=None):
        """Return the current Bitcoin address for receiving payments to this account."""
        r = self._call('getaccountaddress', account)
        return CBitcoinAddress.from_str(r)

    def validateaddress(self, address):
        """Return information about an address"""
        r = self._call('validateaddress', str(address))
        r['address'] = CBitcoinAddress.from_str(r['address'])
        return r

########NEW FILE########
__FILENAME__ = script

#
# script.py
#
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
#

from __future__ import absolute_import, division, print_function, unicode_literals

import struct

SIGHASH_ALL = 1
SIGHASH_NONE = 2
SIGHASH_SINGLE = 3
SIGHASH_ANYONECANPAY = 0x80

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

VALID_OPCODES = {
    OP_1NEGATE,
    OP_RESERVED,
    OP_1,
    OP_2,
    OP_3,
    OP_4,
    OP_5,
    OP_6,
    OP_7,
    OP_8,
    OP_9,
    OP_10,
    OP_11,
    OP_12,
    OP_13,
    OP_14,
    OP_15,
    OP_16,

    OP_NOP,
    OP_VER,
    OP_IF,
    OP_NOTIF,
    OP_VERIF,
    OP_VERNOTIF,
    OP_ELSE,
    OP_ENDIF,
    OP_VERIFY,
    OP_RETURN,

    OP_TOALTSTACK,
    OP_FROMALTSTACK,
    OP_2DROP,
    OP_2DUP,
    OP_3DUP,
    OP_2OVER,
    OP_2ROT,
    OP_2SWAP,
    OP_IFDUP,
    OP_DEPTH,
    OP_DROP,
    OP_DUP,
    OP_NIP,
    OP_OVER,
    OP_PICK,
    OP_ROLL,
    OP_ROT,
    OP_SWAP,
    OP_TUCK,

    OP_CAT,
    OP_SUBSTR,
    OP_LEFT,
    OP_RIGHT,
    OP_SIZE,

    OP_INVERT,
    OP_AND,
    OP_OR,
    OP_XOR,
    OP_EQUAL,
    OP_EQUALVERIFY,
    OP_RESERVED1,
    OP_RESERVED2,

    OP_1ADD,
    OP_1SUB,
    OP_2MUL,
    OP_2DIV,
    OP_NEGATE,
    OP_ABS,
    OP_NOT,
    OP_0NOTEQUAL,

    OP_ADD,
    OP_SUB,
    OP_MUL,
    OP_DIV,
    OP_MOD,
    OP_LSHIFT,
    OP_RSHIFT,

    OP_BOOLAND,
    OP_BOOLOR,
    OP_NUMEQUAL,
    OP_NUMEQUALVERIFY,
    OP_NUMNOTEQUAL,
    OP_LESSTHAN,
    OP_GREATERTHAN,
    OP_LESSTHANOREQUAL,
    OP_GREATERTHANOREQUAL,
    OP_MIN,
    OP_MAX,

    OP_WITHIN,

    OP_RIPEMD160,
    OP_SHA1,
    OP_SHA256,
    OP_HASH160,
    OP_HASH256,
    OP_CODESEPARATOR,
    OP_CHECKSIG,
    OP_CHECKSIGVERIFY,
    OP_CHECKMULTISIG,
    OP_CHECKMULTISIGVERIFY,

    OP_NOP1,
    OP_NOP2,
    OP_NOP3,
    OP_NOP4,
    OP_NOP5,
    OP_NOP6,
    OP_NOP7,
    OP_NOP8,
    OP_NOP9,
    OP_NOP10,

    OP_SMALLINTEGER,
    OP_PUBKEYS,
    OP_PUBKEYHASH,
    OP_PUBKEY,
}

OPCODE_NAMES = {
    OP_0 : 'OP_0',
    OP_PUSHDATA1 : 'OP_PUSHDATA1',
    OP_PUSHDATA2 : 'OP_PUSHDATA2',
    OP_PUSHDATA4 : 'OP_PUSHDATA4',
    OP_1NEGATE : 'OP_1NEGATE',
    OP_RESERVED : 'OP_RESERVED',
    OP_1 : 'OP_1',
    OP_2 : 'OP_2',
    OP_3 : 'OP_3',
    OP_4 : 'OP_4',
    OP_5 : 'OP_5',
    OP_6 : 'OP_6',
    OP_7 : 'OP_7',
    OP_8 : 'OP_8',
    OP_9 : 'OP_9',
    OP_10 : 'OP_10',
    OP_11 : 'OP_11',
    OP_12 : 'OP_12',
    OP_13 : 'OP_13',
    OP_14 : 'OP_14',
    OP_15 : 'OP_15',
    OP_16 : 'OP_16',
    OP_NOP : 'OP_NOP',
    OP_VER : 'OP_VER',
    OP_IF : 'OP_IF',
    OP_NOTIF : 'OP_NOTIF',
    OP_VERIF : 'OP_VERIF',
    OP_VERNOTIF : 'OP_VERNOTIF',
    OP_ELSE : 'OP_ELSE',
    OP_ENDIF : 'OP_ENDIF',
    OP_VERIFY : 'OP_VERIFY',
    OP_RETURN : 'OP_RETURN',
    OP_TOALTSTACK : 'OP_TOALTSTACK',
    OP_FROMALTSTACK : 'OP_FROMALTSTACK',
    OP_2DROP : 'OP_2DROP',
    OP_2DUP : 'OP_2DUP',
    OP_3DUP : 'OP_3DUP',
    OP_2OVER : 'OP_2OVER',
    OP_2ROT : 'OP_2ROT',
    OP_2SWAP : 'OP_2SWAP',
    OP_IFDUP : 'OP_IFDUP',
    OP_DEPTH : 'OP_DEPTH',
    OP_DROP : 'OP_DROP',
    OP_DUP : 'OP_DUP',
    OP_NIP : 'OP_NIP',
    OP_OVER : 'OP_OVER',
    OP_PICK : 'OP_PICK',
    OP_ROLL : 'OP_ROLL',
    OP_ROT : 'OP_ROT',
    OP_SWAP : 'OP_SWAP',
    OP_TUCK : 'OP_TUCK',
    OP_CAT : 'OP_CAT',
    OP_SUBSTR : 'OP_SUBSTR',
    OP_LEFT : 'OP_LEFT',
    OP_RIGHT : 'OP_RIGHT',
    OP_SIZE : 'OP_SIZE',
    OP_INVERT : 'OP_INVERT',
    OP_AND : 'OP_AND',
    OP_OR : 'OP_OR',
    OP_XOR : 'OP_XOR',
    OP_EQUAL : 'OP_EQUAL',
    OP_EQUALVERIFY : 'OP_EQUALVERIFY',
    OP_RESERVED1 : 'OP_RESERVED1',
    OP_RESERVED2 : 'OP_RESERVED2',
    OP_1ADD : 'OP_1ADD',
    OP_1SUB : 'OP_1SUB',
    OP_2MUL : 'OP_2MUL',
    OP_2DIV : 'OP_2DIV',
    OP_NEGATE : 'OP_NEGATE',
    OP_ABS : 'OP_ABS',
    OP_NOT : 'OP_NOT',
    OP_0NOTEQUAL : 'OP_0NOTEQUAL',
    OP_ADD : 'OP_ADD',
    OP_SUB : 'OP_SUB',
    OP_MUL : 'OP_MUL',
    OP_DIV : 'OP_DIV',
    OP_MOD : 'OP_MOD',
    OP_LSHIFT : 'OP_LSHIFT',
    OP_RSHIFT : 'OP_RSHIFT',
    OP_BOOLAND : 'OP_BOOLAND',
    OP_BOOLOR : 'OP_BOOLOR',
    OP_NUMEQUAL : 'OP_NUMEQUAL',
    OP_NUMEQUALVERIFY : 'OP_NUMEQUALVERIFY',
    OP_NUMNOTEQUAL : 'OP_NUMNOTEQUAL',
    OP_LESSTHAN : 'OP_LESSTHAN',
    OP_GREATERTHAN : 'OP_GREATERTHAN',
    OP_LESSTHANOREQUAL : 'OP_LESSTHANOREQUAL',
    OP_GREATERTHANOREQUAL : 'OP_GREATERTHANOREQUAL',
    OP_MIN : 'OP_MIN',
    OP_MAX : 'OP_MAX',
    OP_WITHIN : 'OP_WITHIN',
    OP_RIPEMD160 : 'OP_RIPEMD160',
    OP_SHA1 : 'OP_SHA1',
    OP_SHA256 : 'OP_SHA256',
    OP_HASH160 : 'OP_HASH160',
    OP_HASH256 : 'OP_HASH256',
    OP_CODESEPARATOR : 'OP_CODESEPARATOR',
    OP_CHECKSIG : 'OP_CHECKSIG',
    OP_CHECKSIGVERIFY : 'OP_CHECKSIGVERIFY',
    OP_CHECKMULTISIG : 'OP_CHECKMULTISIG',
    OP_CHECKMULTISIGVERIFY : 'OP_CHECKMULTISIGVERIFY',
    OP_NOP1 : 'OP_NOP1',
    OP_NOP2 : 'OP_NOP2',
    OP_NOP3 : 'OP_NOP3',
    OP_NOP4 : 'OP_NOP4',
    OP_NOP5 : 'OP_NOP5',
    OP_NOP6 : 'OP_NOP6',
    OP_NOP7 : 'OP_NOP7',
    OP_NOP8 : 'OP_NOP8',
    OP_NOP9 : 'OP_NOP9',
    OP_NOP10 : 'OP_NOP10',
    OP_SMALLINTEGER : 'OP_SMALLINTEGER',
    OP_PUBKEYS : 'OP_PUBKEYS',
    OP_PUBKEYHASH : 'OP_PUBKEYHASH',
    OP_PUBKEY : 'OP_PUBKEY',
}

TEMPLATES = [
    [ OP_PUBKEY, OP_CHECKSIG ],
    [ OP_DUP, OP_HASH160, OP_PUBKEYHASH, OP_EQUALVERIFY, OP_CHECKSIG ],
]

class CScriptOp(object):
    def __init__(self):
        self.op = OP_INVALIDOPCODE
        self.data = ''
        self.ser_len = 0

class CScript(object):
    def __init__(self, vch=None):
        self.vch = vch

        self.reset()

    def reset(self):
        self.pc = 0
        if self.vch is None:
            self.pend = 0
        else:
            self.pend = len(self.vch)
        self.pbegincodehash = 0
        self.sop = None

    def getchars(self, n):
        if (self.pc + n) > self.pend:
            return None

        s = self.vch[self.pc:self.pc+n]
        self.pc += n

        return s

    def getop(self):
        s = self.getchars(1)
        if s is None:
            return False
        opcode = ord(s)

        sop = CScriptOp()
        sop.op = opcode
        sop.ser_len = 1

        if opcode > OP_PUSHDATA4:
            if opcode not in VALID_OPCODES:
                return False
            self.sop = sop
            return True

        if opcode < OP_PUSHDATA1:
            datasize = opcode

        elif opcode == OP_PUSHDATA1:
            sop.ser_len += 1
            s = self.getchars(1)
            if s is None:
                return False
            datasize = ord(s)

        elif opcode == OP_PUSHDATA2:
            sop.ser_len += 2
            s = self.getchars(2)
            if s is None:
                return False
            datasize = struct.unpack(b"<H", s)[0]

        elif opcode == OP_PUSHDATA4:
            sop.ser_len += 4
            s = self.getchars(4)
            if s is None:
                return False
            datasize = struct.unpack(b"<I", s)[0]

        sop.ser_len += datasize
        sop.data = self.getchars(datasize)
        if sop.data is None:
            return False

        self.sop = sop
        return True

    def tokenize(self, vch_in=None):
        if vch_in is not None:
            self.vch = vch_in

        self.reset()
        while self.pc < self.pend:
            if not self.getop():
                return False

        return True

    def match_temp(self, template, vch_in=None):
        l = []
        i = 0

        if vch_in is not None:
            self.vch = vch_in

        self.reset()
        while self.pc < self.pend:
            if i >= len(template):
                return None
            if not self.getop():
                return None

            expected_op = template[i]
            if expected_op == OP_PUBKEYHASH or expected_op == OP_PUBKEY:
                if self.sop.op > OP_PUSHDATA4:
                    return None
                l.append(self.sop.data)

            elif self.sop.op != expected_op:
                return None

            i += 1

        return l

    def match_alltemp(self, vch_in=None):
        for temp in TEMPLATES:
            l = self.match_temp(temp, vch_in)
            if l is not None:
                return l
        return None

    def __repr__(self):
        return "CScript(vchsz %d)" % (len(self.vch),)


########NEW FILE########
__FILENAME__ = scripteval

#
# scripteval.py
#
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
#

from __future__ import absolute_import, division, print_function, unicode_literals

import sys
if sys.version > '3':
    long = int

import hashlib
from bitcoin.serialize import Hash, Hash160, ser_uint256, ser_uint160
from bitcoin.script import *
from bitcoin.core import CTxOut, CTransaction
from bitcoin.key import CKey
from bitcoin.bignum import bn2vch, vch2bn

def SignatureHash(script, txTo, inIdx, hashtype):
    if inIdx >= len(txTo.vin):
        return (1, "inIdx %d out of range (%d)" % (inIdx, len(txTo.vin)))
    txtmp = CTransaction()
    txtmp.copy(txTo)

    for txin in txtmp.vin:
        txin.scriptSig = b''
    txtmp.vin[inIdx].scriptSig = script.vch

    if (hashtype & 0x1f) == SIGHASH_NONE:
        txtmp.vout = []

        for i in range(len(txtmp.vin)):
            if i != inIdx:
                txtmp.vin[i].nSequence = 0

    elif (hashtype & 0x1f) == SIGHASH_SINGLE:
        outIdx = inIdx
        if outIdx >= len(txtmp.vout):
            return (1, "outIdx %d out of range (%d)" % (outIdx, len(txtmp.vout)))

        tmp = txtmp.vout[outIdx]
        txtmp.vout = []
        for i in range(outIdx):
            txtmp.vout.append(CTxOut())
        txtmp.vout.append(tmp)

        for i in range(len(txtmp.vin)):
            if i != inIdx:
                txtmp.vin[i].nSequence = 0

    if hashtype & SIGHASH_ANYONECANPAY:
        tmp = txtmp.vin[inIdx]
        txtmp.vin = []
        txtmp.vin.append(tmp)

    s = txtmp.serialize()
    s += struct.pack(b"<I", hashtype)

    hash = Hash(s)

    return (hash,)

def CheckSig(sig, pubkey, script, txTo, inIdx, hashtype):
    key = CKey()
    key.set_pubkey(pubkey)

    if len(sig) == 0:
        return False
    if hashtype == 0:
        hashtype = ord(sig[-1])
    elif hashtype != ord(sig[-1]):
        return False
    sig = sig[:-1]

    tup = SignatureHash(script, txTo, inIdx, hashtype)
    return key.verify(ser_uint256(tup[0]), sig)

def CheckMultiSig(opcode, script, stack, txTo, inIdx, hashtype):
    i = 1
    if len(stack) < i:
        return False

    keys_count = CastToBigNum(stack[-i])
    if keys_count < 0 or keys_count > 20:
        return False
    i += 1
    ikey = i
    i += keys_count
    if len(stack) < i:
        return False

    sigs_count = CastToBigNum(stack[-i])
    if sigs_count < 0 or sigs_count > keys_count:
        return False
    i += 1
    isig = i
    i += sigs_count
    if len(stack) < i:
        return False

    for k in range(sigs_count):
        sig = stack[-isig-k]
        # FIXME: find-and-delete sig in script

    success = True

    while success and sigs_count > 0:
        sig = stack[-isig]
        pubkey = stack[-ikey]

        if CheckSig(sig, pubkey, script, txTo, inIdx, hashtype):
            isig += 1
            sigs_count -= 1

        ikey += 1
        keys_count -= 1

        if sigs_count > keys_count:
            success = False

    while i > 0:
        stack.pop()
        i -= 1

    if success:
        stack.append(b"\x01")
    else:
        stack.append(b"\x00")

    if opcode == OP_CHECKMULTISIGVERIFY:
        if success:
            stack.pop()
        else:
            return False

    return True

def dumpstack(msg, stack):
    print("%s stacksz %d" % (msg, len(stack)))
    for i in range(len(stack)):
        vch = stack[i]
        print("#%d: %s" % (i, vch.encode('hex')))

ISA_UNOP = {
    OP_1ADD,
    OP_1SUB,
    OP_2MUL,
    OP_2DIV,
    OP_NEGATE,
    OP_ABS,
    OP_NOT,
    OP_0NOTEQUAL,
}

def UnaryOp(opcode, stack):
    if len(stack) < 1:
        return False
    bn = CastToBigNum(stack.pop())

    if opcode == OP_1ADD:
        bn += 1

    elif opcode == OP_1SUB:
        bn -= 1

    elif opcode == OP_2MUL:
        bn <<= 1

    elif opcode == OP_2DIV:
        bn >>= 1

    elif opcode == OP_NEGATE:
        bn = -bn

    elif opcode == OP_ABS:
        if bn < 0:
            bn = -bn

    elif opcode == OP_NOT:
        bn = long(bn == 0)

    elif opcode == OP_0NOTEQUAL:
        bn = long(bn != 0)

    else:
        return False

    stack.append(bn2vch(bn))

    return True

ISA_BINOP = {
    OP_ADD,
    OP_SUB,
    OP_LSHIFT,
    OP_RSHIFT,
    OP_BOOLAND,
    OP_BOOLOR,
    OP_NUMEQUAL,
    OP_NUMEQUALVERIFY,
    OP_NUMNOTEQUAL,
    OP_LESSTHAN,
    OP_GREATERTHAN,
    OP_LESSTHANOREQUAL,
    OP_GREATERTHANOREQUAL,
    OP_MIN,
    OP_MAX,
}

def BinOp(opcode, stack):
    if len(stack) < 2:
        return False

    bn2 = CastToBigNum(stack.pop())
    bn1 = CastToBigNum(stack.pop())

    if opcode == OP_ADD:
        bn = bn1 + bn2

    elif opcode == OP_SUB:
        bn = bn1 - bn2

    elif opcode == OP_LSHIFT:
        if bn2 < 0 or bn2 > 2048:
            return False
        bn = bn1 << bn2

    elif opcode == OP_RSHIFT:
        if bn2 < 0 or bn2 > 2048:
            return False
        bn = bn1 >> bn2

    elif opcode == OP_BOOLAND:
        bn = long(bn1 != 0 and bn2 != 0)

    elif opcode == OP_BOOLOR:
        bn = long(bn1 != 0 or bn2 != 0)

    elif opcode == OP_NUMEQUAL or opcode == OP_NUMEQUALVERIFY:
        bn = long(bn1 == bn2)

    elif opcode == OP_NUMNOTEQUAL:
        bn = long(bn1 != bn2)

    elif opcode == OP_LESSTHAN:
        bn = long(bn1 < bn2)

    elif opcode == OP_GREATERTHAN:
        bn = long(bn1 > bn2)

    elif opcode == OP_LESSTHANOREQUAL:
        bn = long(bn1 <= bn2)

    elif opcode == OP_GREATERTHANOREQUAL:
        bn = long(bn1 >= bn2)

    elif opcode == OP_MIN:
        if bn1 < bn2:
            bn = bn1
        else:
            bn = bn2

    elif opcode == OP_MAX:
        if bn1 > bn2:
            bn = bn1
        else:
            bn = bn2

    else:
        return False            # unknown binop opcode

    stack.append(bn2vch(bn))

    if opcode == OP_NUMEQUALVERIFY:
        if CastToBool(stack[-1]):
            stack.pop()
        else:
            return False

    return True

def CheckExec(vfExec):
    for b in vfExec:
        if not b:
            return False
    return True

def EvalScript(stack, scriptIn, txTo, inIdx, hashtype):
    altstack = []
    vfExec = []
    script = CScript(scriptIn)
    while script.pc < script.pend:
        if not script.getop():
            return False
        sop = script.sop

        fExec = CheckExec(vfExec)

        if fExec and sop.op <= OP_PUSHDATA4:
            stack.append(sop.data)
            continue

        elif fExec and sop.op == OP_1NEGATE or ((sop.op >= OP_1) and (sop.op <= OP_16)):
            v = sop.op - (OP_1 - 1)
            stack.append(bn2vch(v))

        elif fExec and sop.op in ISA_BINOP:
            if not BinOp(sop.op, stack):
                return False

        elif fExec and sop.op in ISA_UNOP:
            if not UnaryOp(sop.op, stack):
                return False

        elif fExec and sop.op == OP_2DROP:
            if len(stack) < 2:
                return False
            stack.pop()
            stack.pop()

        elif fExec and sop.op == OP_2DUP:
            if len(stack) < 2:
                return False
            v1 = stack[-2]
            v2 = stack[-1]
            stack.append(v1)
            stack.append(v2)

        elif fExec and sop.op == OP_2OVER:
            if len(stack) < 4:
                return False
            v1 = stack[-4]
            v2 = stack[-3]
            stack.append(v1)
            stack.append(v2)

        elif fExec and sop.op == OP_2SWAP:
            if len(stack) < 4:
                return False
            tmp = stack[-4]
            stack[-4] = stack[-2]
            stack[-2] = tmp

            tmp = stack[-3]
            stack[-3] = stack[-1]
            stack[-1] = tmp

        elif fExec and sop.op == OP_3DUP:
            if len(stack) < 3:
                return False
            v1 = stack[-3]
            v2 = stack[-2]
            v3 = stack[-1]
            stack.append(v1)
            stack.append(v2)
            stack.append(v3)

        elif fExec and sop.op == OP_CHECKMULTISIG or sop.op == OP_CHECKMULTISIGVERIFY:
            tmpScript = CScript(script.vch[script.pbegincodehash:script.pend])
            ok = CheckMultiSig(sop.op, tmpScript, stack, txTo,
                       inIdx, hashtype)
            if not ok:
                return False

        elif fExec and sop.op == OP_CHECKSIG or sop.op == OP_CHECKSIGVERIFY:
            if len(stack) < 2:
                return False
            vchPubKey = stack.pop()
            vchSig = stack.pop()
            tmpScript = CScript(script.vch[script.pbegincodehash:script.pend])

            # FIXME: find-and-delete vchSig

            ok = CheckSig(vchSig, vchPubKey, tmpScript,
                      txTo, inIdx, hashtype)
            if ok:
                if sop.op != OP_CHECKSIGVERIFY:
                    stack.append(b"\x01")
            else:
                if sop.op == OP_CHECKSIGVERIFY:
                    return False
                stack.append(b"\x00")

        elif fExec and sop.op == OP_CODESEPARATOR:
            script.pbegincodehash = script.pc

        elif fExec and sop.op == OP_DEPTH:
            bn = len(stack)
            stack.append(bn2vch(bn))

        elif fExec and sop.op == OP_DROP:
            if len(stack) < 1:
                return False
            stack.pop()

        elif fExec and sop.op == OP_DUP:
            if len(stack) < 1:
                return False
            v = stack[-1]
            stack.append(v)

        elif sop.op == OP_ELSE:
            if len(vfExec) == 0:
                return false
            vfExec[-1] = not vfExec[-1]

        elif sop.op == OP_ENDIF:
            if len(vfExec) == 0:
                return false
            vfExec.pop()

        elif fExec and sop.op == OP_EQUAL or sop.op == OP_EQUALVERIFY:
            if len(stack) < 2:
                return False
            v1 = stack.pop()
            v2 = stack.pop()

            is_equal = (v1 == v2)
            if is_equal:
                stack.append(b"\x01")
            else:
                stack.append(b"\x00")

            if sop.op == OP_EQUALVERIFY:
                if is_equal:
                    stack.pop()
                else:
                    return False

        elif fExec and sop.op == OP_FROMALTSTACK:
            if len(altstack) < 1:
                return False
            v = altstack.pop()
            stack.append(v)

        elif fExec and sop.op == OP_HASH160:
            if len(stack) < 1:
                return False
            stack.append(ser_uint160(Hash160(stack.pop())))

        elif fExec and sop.op == OP_HASH256:
            if len(stack) < 1:
                return False
            stack.append(ser_uint256(Hash(stack.pop())))

        elif sop.op == OP_IF or sop.op == OP_NOTIF:
            val = False

            if fExec:
                if len(stack) < 1:
                    return False
                vch = stack.pop()
                val = CastToBool(vch)
                if sop.op == OP_NOTIF:
                    val = not val

            vfExec.append(val)

        elif fExec and sop.op == OP_IFDUP:
            if len(stack) < 1:
                return False
            vch = stack[-1]
            if CastToBool(vch):
                stack.append(vch)

        elif fExec and sop.op == OP_NIP:
            if len(stack) < 2:
                return False
            del stack[-2]

        elif fExec and sop.op == OP_NOP or (sop.op >= OP_NOP1 and sop.op <= OP_NOP10):
            pass

        elif fExec and sop.op == OP_OVER:
            if len(stack) < 2:
                return False
            vch = stack[-2]
            stack.append(vch)

        elif fExec and sop.op == OP_PICK or sop.op == OP_ROLL:
            if len(stack) < 2:
                return False
            n = CastToBigNum(stack.pop())
            if n < 0 or n >= len(stack):
                return False
            vch = stack[-n-1]
            if sop.op == OP_ROLL:
                del stack[-n-1]
            stack.append(vch)

        elif fExec and sop.op == OP_RETURN:
            return False

        elif fExec and sop.op == OP_RIPEMD160:
            if len(stack) < 1:
                return False

            h = hashlib.new('ripemd160')
            h.update(stack.pop())
            stack.append(h.digest())

        elif fExec and sop.op == OP_ROT:
            if len(stack) < 3:
                return False
            tmp = stack[-3]
            stack[-3] = stack[-2]
            stack[-2] = tmp

            tmp = stack[-2]
            stack[-2] = stack[-1]
            stack[-1] = tmp

        elif fExec and sop.op == OP_SIZE:
            if len(stack) < 1:
                return False
            bn = len(stack[-1])
            stack.append(bn2vch(bn))

        elif fExec and sop.op == OP_SHA256:
            if len(stack) < 1:
                return False
            stack.append(hashlib.sha256(stack.pop()).digest())

        elif fExec and sop.op == OP_SWAP:
            if len(stack) < 2:
                return False
            tmp = stack[-2]
            stack[-2] = stack[-1]
            stack[-1] = tmp

        elif fExec and sop.op == OP_TOALTSTACK:
            if len(stack) < 1:
                return False
            v = stack.pop()
            altstack.append(v)

        elif fExec and sop.op == OP_TUCK:
            if len(stack) < 2:
                return False
            vch = stack[-1]
            stack.insert(len(stack) - 2, vch)

        elif fExec and sop.op == OP_VERIFY:
            if len(stack) < 1:
                return False
            v = CastToBool(stack[-1])
            if v:
                stack.pop()
            else:
                return False

        elif fExec and sop.op == OP_WITHIN:
            if len(stack) < 3:
                return False
            bn3 = CastToBigNum(stack.pop())
            bn2 = CastToBigNum(stack.pop())
            bn1 = CastToBigNum(stack.pop())
            v = (bn2 <= bn1) and (bn1 < bn3)
            if v:
                stack.append(b"\x01")
            else:
                stack.append(b"\x00")

        elif fExec:
            #print("Unsupported opcode", OPCODE_NAMES[sop.op])
            return False

    return True

def CastToBigNum(s):
    v = vch2bn(s)
    return v

def CastToBool(s):
    for i in range(len(s)):
        sv = ord(s[i])
        if sv != 0:
            if (i == (len(s) - 1)) and (sv == 0x80):
                return False
            return True

    return False

def VerifyScript(scriptSig, scriptPubKey, txTo, inIdx, hashtype):
    stack = []
    if not EvalScript(stack, scriptSig, txTo, inIdx, hashtype):
        return False
    if not EvalScript(stack, scriptPubKey, txTo, inIdx, hashtype):
        return False
    if len(stack) == 0:
        return False
    return CastToBool(stack[-1])

def VerifySignature(txFrom, txTo, inIdx, hashtype):
    if inIdx >= len(txTo.vin):
        return False
    txin = txTo.vin[inIdx]

    if txin.prevout.n >= len(txFrom.vout):
        return False
    txout = txFrom.vout[txin.prevout.n]

    txFrom.calc_sha256()

    if txin.prevout.hash != txFrom.sha256:
        return False

    if not VerifyScript(txin.scriptSig, txout.scriptPubKey, txTo, inIdx,
                hashtype):
        return False

    return True





########NEW FILE########
__FILENAME__ = serialize

#
# serialize.py
#
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
#

from __future__ import absolute_import, division, print_function, unicode_literals

import struct
import hashlib

# Py3 compatibility
import sys
bchr = chr
if sys.version > '3':
    bchr = lambda x: bytes([x])

def deser_string(f):
    nit = struct.unpack(b"<B", f.read(1))[0]
    if nit == 253:
        nit = struct.unpack(b"<H", f.read(2))[0]
    elif nit == 254:
        nit = struct.unpack(b"<I", f.read(4))[0]
    elif nit == 255:
        nit = struct.unpack(b"<Q", f.read(8))[0]
    return f.read(nit)

def ser_string(s):
    if len(s) < 253:
        return bchr(len(s)) + s
    elif len(s) < 0x10000:
        return bchr(253) + struct.pack(b"<H", len(s)) + s
    elif len(s) < 0x100000000:
        return bchr(254) + struct.pack(b"<I", len(s)) + s
    return bchr(255) + struct.pack(b"<Q", len(s)) + s

def deser_uint256(f):
    r = 0
    for i in range(8):
        t = struct.unpack(b"<I", f.read(4))[0]
        r += t << (i * 32)
    return r

def ser_uint256(u):
    rs = b""
    for i in range(8):
        rs += struct.pack(b"<I", u & 0xFFFFFFFF)
        u >>= 32
    return rs

def ser_uint160(u):
    rs = b""
    for i in range(5):
        rs += struct.pack(b"<I", u & 0xFFFFFFFF)
        u >>= 32
    return rs

def uint160_from_str(s):
    r = 0
    t = struct.unpack(b"<IIIII", s[:20])
    for i in range(5):
        r += t[i] << (i * 32)
    return r

def uint256_from_str(s):
    r = 0
    t = struct.unpack(b"<IIIIIIII", s[:32])
    for i in range(8):
        r += t[i] << (i * 32)
    return r

def uint256_from_compact(c):
    nbytes = (c >> 24) & 0xFF
    v = (c & 0xFFFFFF) << (8 * (nbytes - 3))
    return v

def uint256_to_shortstr(u):
    s = "%064x" % (u,)
    return s[:16]

def deser_vector(f, c, arg1=None):
    nit = struct.unpack(b"<B", f.read(1))[0]
    if nit == 253:
        nit = struct.unpack(b"<H", f.read(2))[0]
    elif nit == 254:
        nit = struct.unpack(b"<I", f.read(4))[0]
    elif nit == 255:
        nit = struct.unpack(b"<Q", f.read(8))[0]
    r = []
    for i in range(nit):
        if arg1 is not None:
            t = c(arg1)
        else:
            t = c()
        t.deserialize(f)
        r.append(t)
    return r

def ser_vector(l):
    r = b""
    if len(l) < 253:
        r = bchr(len(l))
    elif len(l) < 0x10000:
        r = bchr(253) + struct.pack(b"<H", len(l))
    elif len(l) < 0x100000000:
        r = bchr(254) + struct.pack(b"<I", len(l))
    else:
        r = bchr(255) + struct.pack(b"<Q", len(l))
    for i in l:
        r += i.serialize()
    return r

def deser_uint256_vector(f):
    nit = struct.unpack(b"<B", f.read(1))[0]
    if nit == 253:
        nit = struct.unpack(b"<H", f.read(2))[0]
    elif nit == 254:
        nit = struct.unpack(b"<I", f.read(4))[0]
    elif nit == 255:
        nit = struct.unpack(b"<Q", f.read(8))[0]
    r = []
    for i in range(nit):
        t = deser_uint256(f)
        r.append(t)
    return r

def ser_uint256_vector(l):
    r = b""
    if len(l) < 253:
        r = bchr(len(l))
    elif len(s) < 0x10000:
        r = bchr(253) + struct.pack(b"<H", len(l))
    elif len(s) < 0x100000000:
        r = bchr(254) + struct.pack(b"<I", len(l))
    else:
        r = bchr(255) + struct.pack(b"<Q", len(l))
    for i in l:
        r += ser_uint256(i)
    return r

def deser_string_vector(f):
    nit = struct.unpack(b"<B", f.read(1))[0]
    if nit == 253:
        nit = struct.unpack(b"<H", f.read(2))[0]
    elif nit == 254:
        nit = struct.unpack(b"<I", f.read(4))[0]
    elif nit == 255:
        nit = struct.unpack(b"<Q", f.read(8))[0]
    r = []
    for i in range(nit):
        t = deser_string(f)
        r.append(t)
    return r

def ser_string_vector(l):
    r = b""
    if len(l) < 253:
        r = bchr(len(l))
    elif len(s) < 0x10000:
        r = bchr(253) + struct.pack(b"<H", len(l))
    elif len(s) < 0x100000000:
        r = bchr(254) + struct.pack(b"<I", len(l))
    else:
        r = bchr(255) + struct.pack(b"<Q", len(l))
    for sv in l:
        r += ser_string(sv)
    return r

def deser_int_vector(f):
    nit = struct.unpack(b"<B", f.read(1))[0]
    if nit == 253:
        nit = struct.unpack(b"<H", f.read(2))[0]
    elif nit == 254:
        nit = struct.unpack(b"<I", f.read(4))[0]
    elif nit == 255:
        nit = struct.unpack(b"<Q", f.read(8))[0]
    r = []
    for i in range(nit):
        t = struct.unpack(b"<i", f.read(4))[0]
        r.append(t)
    return r

def ser_int_vector(l):
    r = b""
    if len(l) < 253:
        r = bchr(len(l))
    elif len(s) < 0x10000:
        r = bchr(253) + struct.pack(b"<H", len(l))
    elif len(s) < 0x100000000:
        r = bchr(254) + struct.pack(b"<I", len(l))
    else:
        r = bchr(255) + struct.pack(b"<Q", len(l))
    for i in l:
        r += struct.pack(b"<i", i)
    return r

def Hash(s):
    return uint256_from_str(hashlib.sha256(hashlib.sha256(s).digest()).digest())

def Hash160(s):
    h = hashlib.new('ripemd160')
    h.update(hashlib.sha256(s).digest())
    return uint160_from_str(h.digest())


########NEW FILE########
__FILENAME__ = test_base58
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
import unittest

from binascii import unhexlify

from bitcoin.base58 import *


def load_test_vector(name):
    with open(os.path.dirname(__file__) + '/data/' + name, 'r') as fd:
        for testcase in json.load(fd):
            yield testcase

class Test_base58(unittest.TestCase):
    def test_encode_decode(self):
        for exp_bin, exp_base58 in load_test_vector('base58_encode_decode.json'):
            exp_bin = unhexlify(exp_bin.encode('utf8'))

            act_base58 = encode(exp_bin)
            act_bin = decode(exp_base58)

            self.assertEqual(act_base58, exp_base58)
            self.assertEqual(act_bin, exp_bin)

    def test_invalid_base58_exception(self):
        with self.assertRaises(InvalidBase58Error):
            decode('#')

    # FIXME: need to test CBitcoinAddress

########NEW FILE########
__FILENAME__ = test_bloom
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
import unittest

from binascii import unhexlify

from bitcoin.bloom import *

class Test_CBloomFilter(unittest.TestCase):
    def test_create_insert_serialize(self):
        filter = CBloomFilter(3, 0.01, 0, CBloomFilter.UPDATE_ALL)

        def T(elem):
            """Filter contains elem"""
            elem = unhexlify(elem)
            filter.insert(elem)
            self.assertTrue(filter.contains(elem))

        def F(elem):
            """Filter does not contain elem"""
            elem = unhexlify(elem)
            self.assertFalse(filter.contains(elem))

        T(b'99108ad8ed9bb6274d3980bab5a85c048f0950c8')
        F(b'19108ad8ed9bb6274d3980bab5a85c048f0950c8')
        T(b'b5a2c786d9ef4658287ced5914b37a1b4aa32eee')
        T(b'b9300670b4c5366e95b2699e8b18bc75e5f729c5')

        self.assertEqual(filter.serialize(), unhexlify(b'03614e9b050000000000000001'))

    def test_create_insert_serialize_with_tweak(self):
        # Same test as bloom_create_insert_serialize, but we add a nTweak of 100
        filter = CBloomFilter(3, 0.01, 2147483649, CBloomFilter.UPDATE_ALL)

        def T(elem):
            """Filter contains elem"""
            elem = unhexlify(elem)
            filter.insert(elem)
            self.assertTrue(filter.contains(elem))

        def F(elem):
            """Filter does not contain elem"""
            elem = unhexlify(elem)
            self.assertFalse(filter.contains(elem))

        T(b'99108ad8ed9bb6274d3980bab5a85c048f0950c8')
        F(b'19108ad8ed9bb6274d3980bab5a85c048f0950c8')
        T(b'b5a2c786d9ef4658287ced5914b37a1b4aa32eee')
        T(b'b9300670b4c5366e95b2699e8b18bc75e5f729c5')

        self.assertEqual(filter.serialize(), unhexlify(b'03ce4299050000000100008001'))

    def test_bloom_create_insert_key(self):
        filter = CBloomFilter(2, 0.001, 0, CBloomFilter.UPDATE_ALL)

        pubkey = unhexlify(b'045B81F0017E2091E2EDCD5EECF10D5BDD120A5514CB3EE65B8447EC18BFC4575C6D5BF415E54E03B1067934A0F0BA76B01C6B9AB227142EE1D543764B69D901E0')
        pubkeyhash = ser_uint160(Hash160(pubkey))

        filter.insert(pubkey)
        filter.insert(pubkeyhash)

        self.assertEqual(filter.serialize(), unhexlify(b'038fc16b080000000000000001'))

########NEW FILE########
__FILENAME__ = test_hash
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
import unittest

from binascii import unhexlify

from bitcoin.hash import *

class Test_MurmurHash3(unittest.TestCase):
    def test(self):
        def T(expected, seed, data):
            self.assertEqual(MurmurHash3(seed, unhexlify(data)), expected)

        T(0x00000000, 0x00000000, b"");
        T(0x6a396f08, 0xFBA4C795, b"");
        T(0x81f16f39, 0xffffffff, b"");

        T(0x514e28b7, 0x00000000, b"00");
        T(0xea3f0b17, 0xFBA4C795, b"00");
        T(0xfd6cf10d, 0x00000000, b"ff");

        T(0x16c6b7ab, 0x00000000, b"0011");
        T(0x8eb51c3d, 0x00000000, b"001122");
        T(0xb4471bf8, 0x00000000, b"00112233");
        T(0xe2301fa8, 0x00000000, b"0011223344");
        T(0xfc2e4a15, 0x00000000, b"001122334455");
        T(0xb074502c, 0x00000000, b"00112233445566");
        T(0x8034d2a0, 0x00000000, b"0011223344556677");
        T(0xb4698def, 0x00000000, b"001122334455667788");

########NEW FILE########
