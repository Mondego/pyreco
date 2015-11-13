__FILENAME__ = block
# -*- coding: utf-8 -*-
"""
Parse and stream Bitcoin blocks as either Block or BlockHeader structures.


The MIT License (MIT)

Copyright (c) 2013 by Richard Kiss

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import struct

import io

from .encoding import double_sha256
from .merkle import merkle
from .serialize.bitcoin_streamer import parse_struct, stream_struct
from .serialize import b2h, b2h_rev

from .tx import Tx


class BadMerkleRootError(Exception):
    pass


def difficulty_max_mask_for_bits(bits):
    prefix = bits >> 24
    mask = (bits & 0x7ffff) << (8 * (prefix - 3))
    return mask


class BlockHeader(object):
    """A BlockHeader is a block with the transaction data removed. With a
    complete Merkle tree database, it can be reconstructed from the
    merkle_root."""

    @classmethod
    def parse(self, f):
        """Parse the BlockHeader from the file-like object in the standard way
        that blocks are sent in the network (well, except we ignore the
        transaction information)."""
        (version, previous_block_hash, merkle_root,
            timestamp, difficulty, nonce) = struct.unpack("<L32s32sLLL", f.read(4+32+32+4*3))
        return self(version, previous_block_hash, merkle_root, timestamp, difficulty, nonce)

    def __init__(self, version, previous_block_hash, merkle_root, timestamp, difficulty, nonce):
        self.version = version
        self.previous_block_hash = previous_block_hash
        self.merkle_root = merkle_root
        self.timestamp = timestamp
        self.difficulty = difficulty
        self.nonce = nonce

    def hash(self):
        """Calculate the hash for the block header. Note that this has the bytes
        in the opposite order from how the header is usually displayed (so the
        long string of 00 bytes is at the end, not the beginning)."""
        if not hasattr(self, "__hash"):
            s = io.BytesIO()
            self.stream_header(s)
            self.__hash = double_sha256(s.getvalue())
        return self.__hash

    def stream_header(self, f):
        """Stream the block header in the standard way to the file-like object f."""
        stream_struct("L##LLL", f, self.version, self.previous_block_hash,
                      self.merkle_root, self.timestamp, self.difficulty, self.nonce)

    def stream(self, f):
        """Stream the block header in the standard way to the file-like object f.
        The Block subclass also includes the transactions."""
        self.stream_header(f)

    def id(self):
        """Returns the hash of the block displayed with the bytes in the order
        they are usually displayed in."""
        return b2h_rev(self.hash())

    def previous_block_id(self):
        """Returns the hash of the previous block, with the bytes in the order
        they are usually displayed in."""
        return b2h_rev(self.previous_block_hash)

    def __str__(self):
        return "BlockHeader [%s] (previous %s)" % (self.id(), self.previous_block_id())

    def __repr__(self):
        return "BlockHeader [%s] (previous %s)" % (self.id(), self.previous_block_id())


class Block(BlockHeader):
    """A Block is an element of the Bitcoin chain. Generating a block
    yields a reward!"""

    @classmethod
    def parse(self, f):
        """Parse the Block from the file-like object in the standard way
        that blocks are sent in the network."""
        (version, previous_block_hash, merkle_root, timestamp,
            difficulty, nonce, count) = parse_struct("L##LLLI", f)
        txs = []
        for i in range(count):
            txs.append(Tx.parse(f))
        return self(version, previous_block_hash, merkle_root, timestamp, difficulty, nonce, txs)

    def __init__(self, version, previous_block_hash, merkle_root, timestamp, difficulty, nonce, txs):
        self.version = version
        self.previous_block_hash = previous_block_hash
        self.merkle_root = merkle_root
        self.timestamp = timestamp
        self.difficulty = difficulty
        self.nonce = nonce
        self.txs = txs

    def stream(self, f):
        """Stream the block in the standard way to the file-like object f."""
        stream_struct("L##LLLI", f, self.version, self.previous_block_hash,
                      self.merkle_root, self.timestamp, self.difficulty, self.nonce, len(self.txs))
        for t in self.txs:
            t.stream(f)

    def check_merkle_hash(self):
        """Raise a BadMerkleRootError if the Merkle hash of the
        transactions does not match the Merkle hash included in the block."""
        calculated_hash = merkle([tx.hash() for tx in self.txs], double_sha256)
        if calculated_hash != self.merkle_root:
            raise BadMerkleRootError(
                "calculated %s but block contains %s" % (b2h(calculated_hash), b2h(self.merkle_root)))

    def __str__(self):
        return "Block [%s] (previous %s) [tx count: %d]" % (
            self.id(), self.previous_block_id(), len(self.txs))

    def __repr__(self):
        return "Block [%s] (previous %s) [tx count: %d] %s" % (
            self.id(), self.previous_block_id(), len(self.txs), self.txs)

########NEW FILE########
__FILENAME__ = tx_fee

import io

TX_FEE_PER_THOUSAND_BYTES = 10000


def recommended_fee_for_tx(tx):
    """
    Return the recommended transaction fee in satoshis.
    This is a grossly simplified version of this function.
    TODO: improve to consider TxOut sizes.
      - whether the transaction contains "dust"
      - whether any outputs are less than 0.001
      - update for bitcoind v0.90 new fee schedule
    """
    s = io.BytesIO()
    tx.stream(s)
    tx_byte_count = len(s.getvalue())
    tx_fee = TX_FEE_PER_THOUSAND_BYTES * ((999+tx_byte_count)//1000)
    return tx_fee

########NEW FILE########
__FILENAME__ = ecdsa

"""
Some portions adapted from https://github.com/warner/python-ecdsa/ Copyright (c) 2010 Brian Warner
who granted its use under this license:

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.


Portions written in 2005 by Peter Pearson and placed in the public domain.
"""

import hashlib
import hmac

from . import ellipticcurve, intbytes, numbertheory


if hasattr(1, "bit_length"):
    bit_length = lambda v: v.bit_length()
else:
    def bit_length(self):
        # Make this library compatible with python < 2.7
        # https://docs.python.org/3.5/library/stdtypes.html#int.bit_length
        s = bin(self)  # binary representation:  bin(-37) --> '-0b100101'
        s = s.lstrip('-0b')  # remove leading zeros and minus sign
        return len(s)  # len('100101') --> 6


def deterministic_generate_k(generator_order, secret_exponent, val, hash_f=hashlib.sha256):
    """
    Generate K value according to https://tools.ietf.org/html/rfc6979
    """
    n = generator_order
    order_size = (bit_length(n) + 7) // 8
    hash_size = hash_f().digest_size
    v = b'\x01' * hash_size
    k = b'\x00' * hash_size
    priv = intbytes.to_bytes(secret_exponent, length=order_size)
    shift = 8 * hash_size - bit_length(n)
    if shift > 0:
        val >>= shift
    if val > n:
        val -= n
    h1 = intbytes.to_bytes(val, length=order_size)
    k = hmac.new(k, v + b'\x00' + priv + h1, hash_f).digest()
    v = hmac.new(k, v, hash_f).digest()
    k = hmac.new(k, v + b'\x01' + priv + h1, hash_f).digest()
    v = hmac.new(k, v, hash_f).digest()

    while 1:
        t = bytearray()

        while len(t) < order_size:
            v = hmac.new(k, v, hash_f).digest()
            t.extend(v)

        k1 = intbytes.from_bytes(bytes(t))

        k1 >>= (len(t)*8 - bit_length(n))
        if k1 >= 1 and k1 < n:
            return k1

        k = hmac.new(k, v + b'\x00', hash_f).digest()
        v = hmac.new(k, v, hash_f).digest()


def sign(generator, secret_exponent, val):
    """Return a signature for the provided hash, using the provided
    random nonce.  It is absolutely vital that random_k be an unpredictable
    number in the range [1, self.public_key.point.order()-1].  If
    an attacker can guess random_k, he can compute our private key from a
    single signature.  Also, if an attacker knows a few high-order
    bits (or a few low-order bits) of random_k, he can compute our private
    key from many signatures.  The generation of nonces with adequate
    cryptographic strength is very difficult and far beyond the scope
    of this comment.

    May raise RuntimeError, in which case retrying with a new
    random value k is in order.
    """
    G = generator
    n = G.order()
    k = deterministic_generate_k(n, secret_exponent, val)
    p1 = k * G
    r = p1.x()
    if r == 0: raise RuntimeError("amazingly unlucky random number r")
    s = ( numbertheory.inverse_mod( k, n ) * \
          ( val + ( secret_exponent * r ) % n ) ) % n
    if s == 0: raise RuntimeError("amazingly unlucky random number s")
    return (r, s)

def public_pair_for_secret_exponent(generator, secret_exponent):
    return (generator*secret_exponent).pair()

def public_pair_for_x(generator, x, is_even):
    curve = generator.curve()
    p = curve.p()
    alpha = ( pow(x, 3, p)  + curve.a() * x + curve.b() ) % p
    beta = numbertheory.modular_sqrt(alpha, p)
    if is_even == bool(beta & 1):
        return (x, p - beta)
    return (x, beta)

def is_public_pair_valid(generator, public_pair):
    return generator.curve().contains_point(public_pair[0], public_pair[1])

def verify(generator, public_pair, val, signature):
    """
    Verify that signature is a valid signature of hash.
    Return True if the signature is valid.
    """

    # From X9.62 J.3.1.

    G = generator
    n = G.order()
    r, s = signature
    if r < 1 or r > n-1: return False
    if s < 1 or s > n-1: return False
    c = numbertheory.inverse_mod( s, n )
    u1 = ( val * c ) % n
    u2 = ( r * c ) % n
    point = u1 * G + u2 * ellipticcurve.Point( G.curve(), public_pair[0], public_pair[1], G.order() )
    v = point.x() % n
    return v == r

def possible_public_pairs_for_signature(generator, value, signature):
    """ See http://www.secg.org/download/aid-780/sec1-v2.pdf for the math """
    G = generator
    curve = G.curve()
    order = G.order()
    p = curve.p()

    r,s = signature

    possible_points = set()

    #recid = nV - 27
    # 1.1
    inv_r = numbertheory.inverse_mod(r,order)
    minus_e = -value % order
    x = r
    # 1.3
    alpha = ( pow(x,3,p)  + curve.a() * x + curve.b() ) % p
    beta = numbertheory.modular_sqrt(alpha, p)
    for y in [beta, p - beta]:
        # 1.4 the constructor checks that nR is at infinity
        R = ellipticcurve.Point(curve, x, y, order)
        # 1.6 compute Q = r^-1 (sR - eG)
        Q = inv_r * ( s * R + minus_e * G )
        public_pair = (Q.x(), Q.y())
        # check that Q is the public key
        if verify(generator, public_pair, value, signature):
        # check that we get the original signing address
            possible_points.add(public_pair)
    return possible_points

########NEW FILE########
__FILENAME__ = ellipticcurve

#
# Implementation of elliptic curves, for cryptographic applications.
#
# This module doesn't provide any way to choose a random elliptic
# curve, nor to verify that an elliptic curve was chosen randomly,
# because one can simply use NIST's standard curves.
#
# Notes from X9.62-1998 (draft):
#   Nomenclature:
#     - Q is a public key.
#     The "Elliptic Curve Domain Parameters" include:
#     - q is the "field size", which in our case equals p.
#     - p is a big prime.
#     - G is a point of prime order (5.1.1.1).
#     - n is the order of G (5.1.1.1).
#   Public-key validation (5.2.2):
#     - Verify that Q is not the point at infinity.
#     - Verify that X_Q and Y_Q are in [0,p-1].
#     - Verify that Q is on the curve.
#     - Verify that nQ is the point at infinity.
#   Signature generation (5.3):
#     - Pick random k from [1,n-1].
#   Signature checking (5.4.2):
#     - Verify that r and s are in [1,n-1].
#
# Version of 2008.11.25.
#
# Revision history:
#    2005.12.31 - Initial version.
#    2008.11.25 - Change CurveFp.is_on to contains_point.
#
# Written in 2005 by Peter Pearson and placed in the public domain.

from . import numbertheory

class CurveFp( object ):
  """Elliptic Curve over the field of integers modulo a prime."""
  def __init__( self, p, a, b ):
    """The curve of points satisfying y^2 = x^3 + a*x + b (mod p)."""
    self.__p = p
    self.__a = a
    self.__b = b

  def p( self ):
    return self.__p

  def a( self ):
    return self.__a

  def b( self ):
    return self.__b

  def contains_point( self, x, y ):
    """Is the point (x,y) on this curve?"""
    return ( y * y - ( x * x * x + self.__a * x + self.__b ) ) % self.__p == 0



class Point( object ):
  """A point on an elliptic curve. Altering x and y is forbidding,
     but they can be read by the x() and y() methods."""
  def __init__( self, curve, x, y, order = None ):
    """curve, x, y, order; order (optional) is the order of this point."""
    self.__curve = curve
    self.__x = x
    self.__y = y
    self.__order = order
    # self.curve is allowed to be None only for INFINITY:
    if self.__curve: assert self.__curve.contains_point( x, y )
    if order: assert self * order == INFINITY
 
  def __eq__( self, other ):
    """Return 1 if the points are identical, 0 otherwise."""
    if self.__curve == other.__curve \
       and self.__x == other.__x \
       and self.__y == other.__y:
      return 1
    else:
      return 0

  def __add__( self, other ):
    """Add one point to another point."""
    
    # X9.62 B.3:

    if other == INFINITY: return self
    if self == INFINITY: return other
    assert self.__curve == other.__curve
    if self.__x == other.__x:
      if ( self.__y + other.__y ) % self.__curve.p() == 0:
        return INFINITY
      else:
        return self.double()

    p = self.__curve.p()

    l = ( ( other.__y - self.__y ) * \
          numbertheory.inverse_mod( other.__x - self.__x, p ) ) % p

    x3 = ( l * l - self.__x - other.__x ) % p
    y3 = ( l * ( self.__x - x3 ) - self.__y ) % p
    
    return Point( self.__curve, x3, y3 )

  def __mul__( self, other ):
    """Multiply a point by an integer."""

    def leftmost_bit( x ):
      assert x > 0
      result = 1
      while result <= x: result = 2 * result
      return result // 2

    e = other
    if self.__order: e = e % self.__order
    if e == 0: return INFINITY
    if self == INFINITY: return INFINITY
    assert e > 0

    # From X9.62 D.3.2:

    e3 = 3 * e
    negative_self = Point( self.__curve, self.__x, -self.__y, self.__order )
    i = leftmost_bit( e3 ) // 2
    result = self
    # print "Multiplying %s by %d (e3 = %d):" % ( self, other, e3 )
    while i > 1:
      result = result.double()
      if ( e3 & i ) != 0 and ( e & i ) == 0: result = result + self
      if ( e3 & i ) == 0 and ( e & i ) != 0: result = result + negative_self
      # print ". . . i = %d, result = %s" % ( i, result )
      i = i // 2

    return result

  def __rmul__( self, other ):
    """Multiply a point by an integer."""
    
    return self * other

  def __str__( self ):
    if self == INFINITY: return "infinity"
    return "(%d,%d)" % ( self.__x, self.__y )

  def double( self ):
    """Return a new point that is twice the old."""

    if self == INFINITY:
      return INFINITY

    # X9.62 B.3:

    p = self.__curve.p()
    a = self.__curve.a()

    l = ( ( 3 * self.__x * self.__x + a ) * \
          numbertheory.inverse_mod( 2 * self.__y, p ) ) % p

    x3 = ( l * l - 2 * self.__x ) % p
    y3 = ( l * ( self.__x - x3 ) - self.__y ) % p
    
    return Point( self.__curve, x3, y3 )

  def x( self ):
    return self.__x

  def y( self ):
    return self.__y

  def pair( self ):
    return (self.__x, self.__y)

  def curve( self ):
    return self.__curve
  
  def order( self ):
    return self.__order


# This one point is the Point At Infinity for all purposes:
INFINITY = Point( None, None, None )  

def __main__():

  class FailedTest(Exception): pass
  def test_add( c, x1, y1, x2,  y2, x3, y3 ):
    """We expect that on curve c, (x1,y1) + (x2, y2 ) = (x3, y3)."""
    p1 = Point( c, x1, y1 )
    p2 = Point( c, x2, y2 )
    p3 = p1 + p2
    print("%s + %s = %s" % ( p1, p2, p3 ))
    if p3.x() != x3 or p3.y() != y3:
      raise FailedTest("Failure: should give (%d,%d)." % ( x3, y3 ))
    else:
      print(" Good.")

  def test_double( c, x1, y1, x3, y3 ):
    """We expect that on curve c, 2*(x1,y1) = (x3, y3)."""
    p1 = Point( c, x1, y1 )
    p3 = p1.double()
    print("%s doubled = %s" % ( p1, p3 ))
    if p3.x() != x3 or p3.y() != y3:
      raise FailedTest("Failure: should give (%d,%d)." % ( x3, y3 ))
    else:
      print(" Good.")

  def test_double_infinity( c ):
    """We expect that on curve c, 2*INFINITY = INFINITY."""
    p1 = INFINITY
    p3 = p1.double()
    print("%s doubled = %s" % ( p1, p3 ))
    if p3.x() != INFINITY.x() or p3.y() != INFINITY.y():
      raise FailedTest("Failure: should give (%d,%d)." % ( INFINITY.x(), INFINITY.y() ))
    else:
      print(" Good.")

  def test_multiply( c, x1, y1, m, x3, y3 ):
    """We expect that on curve c, m*(x1,y1) = (x3,y3)."""
    p1 = Point( c, x1, y1 )
    p3 = p1 * m
    print("%s * %d = %s" % ( p1, m, p3 ))
    if p3.x() != x3 or p3.y() != y3:
      raise FailedTest("Failure: should give (%d,%d)." % ( x3, y3 ))
    else:
      print(" Good.")


  # A few tests from X9.62 B.3:

  c = CurveFp( 23, 1, 1 )
  test_add( c, 3, 10, 9, 7, 17, 20 )
  test_double( c, 3, 10, 7, 12 )
  test_add( c, 3, 10, 3, 10, 7, 12 )	# (Should just invoke double.)
  test_multiply( c, 3, 10, 2, 7, 12 )

  test_double_infinity(c)

  # From X9.62 I.1 (p. 96):

  g = Point( c, 13, 7, 7 )

  check = INFINITY
  for i in range( 7 + 1 ):
    p = ( i % 7 ) * g
    print("%s * %d = %s, expected %s . . ." % ( g, i, p, check ))
    if p == check:
      print(" Good.")
    else:
      raise FailedTest("Bad.")
    check = check + g

  # NIST Curve P-192:
  p = 6277101735386680763835789423207666416083908700390324961279
  r = 6277101735386680763835789423176059013767194773182842284081
  #s = 0x3045ae6fc8422f64ed579528d38120eae12196d5L
  c = 0x3099d2bbbfcb2538542dcd5fb078b6ef5f3d6fe2c745de65
  b = 0x64210519e59c80e70fa7e9ab72243049feb8deecc146b9b1
  Gx = 0x188da80eb03090f67cbf20eb43a18800f4ff0afd82ff1012
  Gy = 0x07192b95ffc8da78631011ed6b24cdd573f977a11e794811

  c192 = CurveFp( p, -3, b )
  p192 = Point( c192, Gx, Gy, r )

  # Checking against some sample computations presented
  # in X9.62:

  d = 651056770906015076056810763456358567190100156695615665659
  Q = d * p192
  if Q.x() != 0x62B12D60690CDCF330BABAB6E69763B471F994DD702D16A5:
    raise FailedTest("p192 * d came out wrong.")
  else:
    print("p192 * d came out right.")

  k = 6140507067065001063065065565667405560006161556565665656654
  R = k * p192
  if R.x() != 0x885052380FF147B734C330C43D39B2C4A89F29B0F749FEAD \
     or R.y() != 0x9CF9FA1CBEFEFB917747A3BB29C072B9289C2547884FD835:
    raise FailedTest("k * p192 came out wrong.")
  else:
    print("k * p192 came out right.")

  u1 = 2563697409189434185194736134579731015366492496392189760599
  u2 = 6266643813348617967186477710235785849136406323338782220568
  temp = u1 * p192 + u2 * Q
  if temp.x() != 0x885052380FF147B734C330C43D39B2C4A89F29B0F749FEAD \
     or temp.y() != 0x9CF9FA1CBEFEFB917747A3BB29C072B9289C2547884FD835:
    raise FailedTest("u1 * p192 + u2 * Q came out wrong.")
  else:
    print("u1 * p192 + u2 * Q came out right.")

if __name__ == "__main__":
  __main__()

########NEW FILE########
__FILENAME__ = intbytes
"""
Provide the following functions:

bytes_to_ints(bytes):
    yield an iterator of ints. Designed to deal with how
    Python 2 treats bytes[0] as a string while
    Python 3 treats bytes[0] as an int.

to_bytes(v, length, byteorder):
    convert integer v into a bytes object

from_bytes(bytes, byteorder, *, signed=False):
    convert the bytes object into an integer

The last two functions are designed to mimic the methods of the same
name that exist on int in Python 3 only. For Python 3, use
those implementations.
"""

bytes_to_ints = (lambda x: (ord(c) for c in x)) if bytes == str else lambda x: x

if hasattr(int, "to_bytes"):
    to_bytes = lambda v, length, byteorder="big": v.to_bytes(length, byteorder=byteorder)
    from_bytes = lambda bytes, byteorder="big", signed=False: int.from_bytes(bytes, byteorder="big", signed=signed)
else:
    def to_bytes(v, length, byteorder="big"):
        l = bytearray()
        for i in range(length):
            mod = v & 0xff
            v >>= 8
            l.append(mod)
        if byteorder == "big":
            l.reverse()
        return bytes(l)

    def from_bytes(bytes, byteorder="big", signed=False):
        if byteorder != "big":
            bytes = reversed(bytes)
        v = 0
        for c in bytes_to_ints(bytes):
            v <<= 8
            v += c
        if signed and bytes[0] & 0x80:
            v = v - (1<<(8*len(bytes)))
        return v

########NEW FILE########
__FILENAME__ = numbertheory

def inverse_mod( a, m ):
  """Inverse of a mod m."""

  if a < 0 or m <= a: a = a % m

  # From Ferguson and Schneier, roughly:

  c, d = a, m
  uc, vc, ud, vd = 1, 0, 0, 1
  while c != 0:
    q, c, d = divmod( d, c ) + ( c, )
    uc, vc, ud, vd = ud - q*uc, vd - q*vc, uc, vc

  # At this point, d is the GCD, and ud*a+vd*m = d.
  # If d == 1, this means that ud is a inverse.

  assert d == 1
  if ud > 0: return ud
  else: return ud + m

# from http://eli.thegreenplace.net/2009/03/07/computing-modular-square-roots-in-python/

def modular_sqrt(a, p):
    """ Find a quadratic residue (mod p) of 'a'. p
    must be an odd prime.

    Solve the congruence of the form:
    x^2 = a (mod p)
    And returns x. Note that p - x is also a root.

    0 is returned is no square root exists for
    these a and p.

    The Tonelli-Shanks algorithm is used (except
    for some simple cases in which the solution
    is known from an identity). This algorithm
    runs in polynomial time (unless the
    generalized Riemann hypothesis is false).
    """
    # Simple cases
    #
    if legendre_symbol(a, p) != 1:
        return 0
    elif a == 0:
        return 0
    elif p == 2:
        return p
    elif p % 4 == 3:
        return pow(a, (p + 1) // 4, p)

    # Partition p-1 to s * 2^e for an odd s (i.e.
    # reduce all the powers of 2 from p-1)
    #
    s = p - 1
    e = 0
    while s % 2 == 0:
        s /= 2
        e += 1

    # Find some 'n' with a legendre symbol n|p = -1.
    # Shouldn't take long.
    #
    n = 2
    while legendre_symbol(n, p) != -1:
        n += 1

    # Here be dragons!
    # Read the paper "Square roots from 1; 24, 51,
    # 10 to Dan Shanks" by Ezra Brown for more
    # information
    #

    # x is a guess of the square root that gets better
    # with each iteration.
    # b is the "fudge factor" - by how much we're off
    # with the guess. The invariant x^2 = ab (mod p)
    # is maintained throughout the loop.
    # g is used for successive powers of n to update
    # both a and b
    # r is the exponent - decreases with each update
    #
    x = pow(a, (s + 1) // 2, p)
    b = pow(a, s, p)
    g = pow(n, s, p)
    r = e

    while True:
        t = b
        m = 0
        for m in xrange(r):
            if t == 1:
                break
            t = pow(t, 2, p)

        if m == 0:
            return x

        gs = pow(g, 2 ** (r - m - 1), p)
        g = (gs * gs) % p
        x = (x * gs) % p
        b = (b * g) % p
        r = m

def legendre_symbol(a, p):
    """ Compute the Legendre symbol a|p using
    Euler's criterion. p is a prime, a is
    relatively prime to p (if p divides
    a, then a|p = 0)

    Returns 1 if a has a square root modulo
    p, -1 otherwise.
    """
    ls = pow(a, (p - 1) // 2, p)
    return -1 if ls == p - 1 else ls

########NEW FILE########
__FILENAME__ = secp256k1
from .ellipticcurve import CurveFp, Point

# Certicom secp256-k1
_a  = 0x0000000000000000000000000000000000000000000000000000000000000000
_b  = 0x0000000000000000000000000000000000000000000000000000000000000007
_p  = 0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f
_Gx = 0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798
_Gy = 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8
_r  = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141

generator_secp256k1 = Point( CurveFp( _p, _a, _b ), _Gx, _Gy, _r )

########NEW FILE########
__FILENAME__ = encoding
# -*- coding: utf-8 -*-
"""
Various utilities useful for converting one Bitcoin format to another, including some
the human-transcribable format hashed_base58.


The MIT License (MIT)

Copyright (c) 2013 by Richard Kiss

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import hashlib

bytes_from_int = chr if bytes == str else lambda x: bytes([x])
byte_to_int = ord if bytes == str else lambda x: x

BASE58_ALPHABET = b'123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
BASE58_BASE = len(BASE58_ALPHABET)
BASE58_LOOKUP = dict((c, i) for i, c in enumerate(BASE58_ALPHABET))


class EncodingError(Exception):
    pass


def ripemd160(data):
    return hashlib.new("ripemd160", data)

try:
    ripemd160(b'').digest()
except Exception:
    # stupid Google App Engine hashlib doesn't support ripemd160 for some stupid reason
    # import it from pycrypto. You need to add
    # - name: pycrypto
    #   version: "latest"
    # to the "libraries" section of your app.yaml
    from Crypto.Hash.RIPEMD import RIPEMD160Hash as ripemd160


def to_long(base, lookup_f, s):
    """
    Convert an array to a (possibly bignum) integer, along with a prefix value
    of how many prefixed zeros there are.

    base:
        the source base
    lookup_f:
        a function to convert an element of s to a value between 0 and base-1.
    s:
        the value to convert
    """
    prefix = 0
    v = 0
    for c in s:
        v *= base
        try:
            v += lookup_f(c)
        except Exception:
            raise EncodingError("bad character %s in string %s" % (c, s))
        if v == 0:
            prefix += 1
    return v, prefix


def from_long(v, prefix, base, charset):
    """The inverse of to_long. Convert an integer to an arbitrary base.

    v: the integer value to convert
    prefix: the number of prefixed 0s to include
    base: the new base
    charset: an array indicating what printable character to use for each value.
    """
    l = bytearray()
    while v > 0:
        try:
            v, mod = divmod(v, base)
            l.append(charset(mod))
        except Exception:
            raise EncodingError("can't convert to character corresponding to %d" % mod)
    l.extend([charset(0)] * prefix)
    l.reverse()
    return bytes(l)


def to_bytes_32(v):
    v = from_long(v, 0, 256, lambda x: x)
    if len(v) > 32:
        raise ValueError("input to to_bytes_32 is too large")
    return ((b'\0' * 32) + v)[-32:]

if hasattr(int, "to_bytes"):
    to_bytes_32 = lambda v: v.to_bytes(32, byteorder="big")


def from_bytes_32(v):
    if len(v) != 32:
        raise ValueError("input to from_bytes_32 is wrong length")
    return to_long(256, byte_to_int, v)[0]

if hasattr(int, "from_bytes"):
    from_bytes_32 = lambda v: int.from_bytes(v, byteorder="big")


def double_sha256(data):
    """A standard compound hash."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def hash160(data):
    """A standard compound hash."""
    return ripemd160(hashlib.sha256(data).digest()).digest()


def b2a_base58(s):
    """Convert binary to base58 using BASE58_ALPHABET. Like Bitcoin addresses."""
    v, prefix = to_long(256, byte_to_int, s)
    s = from_long(v, prefix, BASE58_BASE, lambda v: BASE58_ALPHABET[v])
    return s.decode("utf8")


def a2b_base58(s):
    """Convert base58 to binary using BASE58_ALPHABET."""
    v, prefix = to_long(BASE58_BASE, lambda c: BASE58_LOOKUP[c], s.encode("utf8"))
    return from_long(v, prefix, 256, lambda x: x)


def b2a_hashed_base58(data):
    """
    A "hashed_base58" structure is a base58 integer (which looks like a string)
    with four bytes of hash data at the end. Bitcoin does this in several places,
    including Bitcoin addresses.

    This function turns data (of type "bytes") into its hashed_base58 equivalent.
    """
    return b2a_base58(data + double_sha256(data)[:4])


def a2b_hashed_base58(s):
    """
    If the passed string is hashed_base58, return the binary data.
    Otherwise raises an EncodingError.
    """
    data = a2b_base58(s)
    data, the_hash = data[:-4], data[-4:]
    if double_sha256(data)[:4] == the_hash:
        return data
    raise EncodingError("hashed base58 has bad checksum %s" % s)


def is_hashed_base58_valid(base58):
    """Return True if and only if base58 is valid hashed_base58."""
    try:
        a2b_hashed_base58(base58)
    except EncodingError:
        return False
    return True


def wif_to_tuple_of_prefix_secret_exponent_compressed(wif):
    """
    Return a tuple of (prefix, secret_exponent, is_compressed).
    """
    decoded = a2b_hashed_base58(wif)
    actual_prefix, private_key = decoded[:1], decoded[1:]
    compressed = len(private_key) > 32
    return actual_prefix, from_bytes_32(private_key[:32]), compressed


def wif_to_tuple_of_secret_exponent_compressed(wif, allowable_wif_prefixes=[b'\x80']):
    """Convert a WIF string to the corresponding secret exponent. Private key manipulation.
    Returns a tuple: the secret exponent, as a bignum integer, and a boolean indicating if the
    WIF corresponded to a compressed key or not.

    Not that it matters, since we can use the secret exponent to generate both the compressed
    and uncompressed Bitcoin address."""
    actual_prefix, secret_exponent, is_compressed = wif_to_tuple_of_prefix_secret_exponent_compressed(wif)
    if actual_prefix not in allowable_wif_prefixes:
        raise EncodingError("unexpected first byte of WIF %s" % wif)
    return secret_exponent, is_compressed


def wif_to_secret_exponent(wif, allowable_wif_prefixes=[b'\x80']):
    """Convert a WIF string to the corresponding secret exponent."""
    return wif_to_tuple_of_secret_exponent_compressed(wif, allowable_wif_prefixes=allowable_wif_prefixes)[0]


def is_valid_wif(wif, allowable_wif_prefixes=[b'\x80']):
    """Return a boolean indicating if the WIF is valid."""
    try:
        wif_to_secret_exponent(wif, allowable_wif_prefixes=allowable_wif_prefixes)
    except EncodingError:
        return False
    return True


def secret_exponent_to_wif(secret_exp, compressed=True, wif_prefix=b'\x80'):
    """Convert a secret exponent (correspdong to a private key) to WIF format."""
    d = wif_prefix + to_bytes_32(secret_exp)
    if compressed:
        d += b'\01'
    return b2a_hashed_base58(d)


def public_pair_to_sec(public_pair, compressed=True):
    """Convert a public pair (a pair of bignums corresponding to a public key) to the
    gross internal sec binary format used by OpenSSL."""
    x_str = to_bytes_32(public_pair[0])
    if compressed:
        return bytes_from_int((2 + (public_pair[1] & 1))) + x_str
    y_str = to_bytes_32(public_pair[1])
    return b'\4' + x_str + y_str


def sec_to_public_pair(sec):
    """Convert a public key in sec binary format to a public pair."""
    x = from_bytes_32(sec[1:33])
    sec0 = sec[:1]
    if sec0 == b'\4':
        y = from_bytes_32(sec[33:65])
        from .ecdsa import generator_secp256k1, is_public_pair_valid
        public_pair = (x, y)
        # verify this is on the curve
        if not is_public_pair_valid(generator_secp256k1, public_pair):
            raise EncodingError("invalid (x, y) pair")
        return public_pair
    if sec0 in (b'\2', b'\3'):
        from .ecdsa import public_pair_for_x, generator_secp256k1
        return public_pair_for_x(generator_secp256k1, x, is_even=(sec0 == b'\2'))
    raise EncodingError("bad sec encoding for public key")


def is_sec_compressed(sec):
    """Return a boolean indicating if the sec represents a compressed public key."""
    return sec[:1] in (b'\2', b'\3')


def public_pair_to_hash160_sec(public_pair, compressed=True):
    """Convert a public_pair (corresponding to a public key) to hash160_sec format.
    This is a hash of the sec representation of a public key, and is used to generate
    the corresponding Bitcoin address."""
    return hash160(public_pair_to_sec(public_pair, compressed=compressed))


def hash160_sec_to_bitcoin_address(hash160_sec, address_prefix=b'\0'):
    """Convert the hash160 of a sec version of a public_pair to a Bitcoin address."""
    return b2a_hashed_base58(address_prefix + hash160_sec)


def bitcoin_address_to_hash160_sec_with_prefix(bitcoin_address):
    """
    Convert a Bitcoin address back to the hash160_sec format and
    also return the prefix.
    """
    blob = a2b_hashed_base58(bitcoin_address)
    if len(blob) != 21:
        raise EncodingError("incorrect binary length (%d) for Bitcoin address %s" %
                            (len(blob), bitcoin_address))
    if blob[:1] not in [b'\x6f', b'\0']:
        raise EncodingError("incorrect first byte (%s) for Bitcoin address %s" % (blob[0], bitcoin_address))
    return blob[1:], blob[:1]


def bitcoin_address_to_hash160_sec(bitcoin_address, address_prefix=b'\0'):
    """Convert a Bitcoin address back to the hash160_sec format of the public key.
    Since we only know the hash of the public key, we can't get the full public key back."""
    hash160, actual_prefix = bitcoin_address_to_hash160_sec_with_prefix(bitcoin_address)
    if (address_prefix == actual_prefix):
        return hash160
    raise EncodingError("Bitcoin address %s for wrong network" % bitcoin_address)


def public_pair_to_bitcoin_address(public_pair, compressed=True, address_prefix=b'\0'):
    """Convert a public_pair (corresponding to a public key) to a Bitcoin address."""
    return hash160_sec_to_bitcoin_address(public_pair_to_hash160_sec(
        public_pair, compressed=compressed), address_prefix=address_prefix)


def is_valid_bitcoin_address(bitcoin_address, allowable_prefixes=b'\0'):
    """Return True if and only if bitcoin_address is valid."""
    try:
        hash160, prefix = bitcoin_address_to_hash160_sec_with_prefix(bitcoin_address)
    except EncodingError:
        return False
    return prefix in allowable_prefixes

########NEW FILE########
__FILENAME__ = bip32
# -*- coding: utf-8 -*-
"""
A BIP0032-style hierarchical wallet.

Implement a BIP0032-style hierarchical wallet which can create public
or private wallet keys. Each key can create many child nodes. Each node
has a wallet key and a corresponding private & public key, which can
be used to generate Bitcoin addresses or WIF private keys.

At any stage, the private information can be stripped away, after which
descendants can only produce public keys.

Private keys can also generate "hardened" children, which cannot be
generated by the corresponding public keys. This is useful for generating
"change" addresses, for example, which there is no need to share with people
you give public keys to.


The MIT License (MIT)

Copyright (c) 2013 by Richard Kiss

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import hashlib
import hmac
import itertools
import struct

from .. import ecdsa

from ..encoding import public_pair_to_sec, sec_to_public_pair,\
    secret_exponent_to_wif, public_pair_to_bitcoin_address,\
    from_bytes_32, to_bytes_32,\
    public_pair_to_hash160_sec, EncodingError

from ..encoding import a2b_hashed_base58, b2a_hashed_base58
from ..networks import address_prefix_for_netcode, wif_prefix_for_netcode,\
    prv32_prefix_for_netcode, pub32_prefix_for_netcode
from .validate import netcode_and_type_for_data


class PublicPrivateMismatchError(Exception):
    pass


class InvalidKeyGeneratedError(Exception):
    pass


def wallet_iterator_for_wallet_key_path(wallet_key_path):
    subkey_paths = ""
    if "/" in wallet_key_path:
        wallet_key_path, subkey_paths = wallet_key_path.split("/", 1)
    return Wallet.from_wallet_key(wallet_key_path).subkeys_for_path(subkey_paths)


class Wallet(object):
    """
    This is a deterministic wallet that complies with BIP0032
    https://en.bitcoin.it/wiki/BIP_0032
    """
    @classmethod
    def from_master_secret(class_, master_secret, netcode='BTC'):
        """Generate a Wallet from a master password."""
        I64 = hmac.HMAC(key=b"Bitcoin seed", msg=master_secret, digestmod=hashlib.sha512).digest()
        return class_(
            is_private=True, netcode=netcode,
            chain_code=I64[32:], secret_exponent_bytes=I64[:32])

    @classmethod
    def from_wallet_key(class_, b58_str, allow_subkey_suffix=True):
        """Generate a Wallet from a base58 string in a standard way."""
        # TODO: support subkey suffixes

        data = a2b_hashed_base58(b58_str)
        netcode, key_type = netcode_and_type_for_data(data)

        if key_type not in ("pub32", "prv32"):
            raise EncodingError("bad wallet key header")

        is_private = (key_type == 'prv32')
        parent_fingerprint, child_number = struct.unpack(">4sL", data[5:13])

        d = dict(is_private=is_private, netcode=netcode, chain_code=data[13:45],
                 depth=ord(data[4:5]), parent_fingerprint=parent_fingerprint, child_number=child_number)

        if is_private:
            if data[45:46] != b'\0':
                raise EncodingError("private key encoded wrong")
            d["secret_exponent_bytes"] = data[46:]
        else:
            d["public_pair"] = sec_to_public_pair(data[45:])

        return class_(**d)

    def __init__(self, is_private, netcode, chain_code, depth=0, parent_fingerprint=b'\0\0\0\0',
                 child_number=0, secret_exponent_bytes=None, public_pair=None):
        """Don't use this. Use a classmethod to generate from a string instead."""
        if is_private:
            if public_pair:
                raise PublicPrivateMismatchError("can't include public_pair for private key")
        elif secret_exponent_bytes:
            raise PublicPrivateMismatchError("can't include secret_exponent_bytes for public key")
        self.is_private = is_private
        self.netcode = netcode
        if is_private:
            if len(secret_exponent_bytes) != 32:
                raise EncodingError("private key encoding wrong length")
            self.secret_exponent_bytes = secret_exponent_bytes
            self.secret_exponent = from_bytes_32(self.secret_exponent_bytes)
            if self.secret_exponent > ecdsa.generator_secp256k1.order():
                raise InvalidKeyGeneratedError(
                    "this key would produce an invalid secret exponent; please skip it")
            self.public_pair = ecdsa.public_pair_for_secret_exponent(ecdsa.generator_secp256k1,
                                                                     self.secret_exponent)
        else:
            self.public_pair = public_pair
        # validate public_pair is on the curve
        if not ecdsa.is_public_pair_valid(ecdsa.generator_secp256k1, self.public_pair):
            raise InvalidKeyGeneratedError("this key would produce an invalid public pair; please skip it")
        if not isinstance(chain_code, bytes):
            raise ValueError("chain code must be bytes")
        if len(chain_code) != 32:
            raise EncodingError("chain code wrong length")
        self.chain_code = chain_code
        self.depth = depth
        if len(parent_fingerprint) != 4:
            raise EncodingError("parent_fingerprint wrong length")
        self.parent_fingerprint = parent_fingerprint
        self.child_number = child_number
        self.subkey_cache = dict()

    def serialize(self, as_private=None):
        """Yield a 78-byte binary blob corresponding to this node."""
        if as_private is None:
            as_private = self.is_private
        if not self.is_private and as_private:
            raise PublicPrivateMismatchError("public key has no private parts")

        ba = bytearray()
        if as_private:
            ba.extend(prv32_prefix_for_netcode(self.netcode))
        else:
            ba.extend(pub32_prefix_for_netcode(self.netcode))
        ba.extend([self.depth])
        ba.extend(self.parent_fingerprint + struct.pack(">L", self.child_number) + self.chain_code)
        if as_private:
            ba += b'\0' + self.secret_exponent_bytes
        else:
            ba += public_pair_to_sec(self.public_pair, compressed=True)
        return bytes(ba)

    def fingerprint(self):
        return public_pair_to_hash160_sec(self.public_pair, compressed=True)[:4]

    def wallet_key(self, as_private=False):
        """Yield a 111-byte string corresponding to this node."""
        return b2a_hashed_base58(self.serialize(as_private=as_private))

    def wif(self, compressed=True):
        """Yield the WIF corresponding to this node."""
        if not self.is_private:
            raise PublicPrivateMismatchError("can't generate WIF for public key")
        return secret_exponent_to_wif(self.secret_exponent, compressed=compressed,
                                      wif_prefix=wif_prefix_for_netcode(self.netcode))

    def bitcoin_address(self, compressed=True):
        """Yield the Bitcoin address corresponding to this node."""
        return public_pair_to_bitcoin_address(self.public_pair, compressed=compressed,
                                              address_prefix=address_prefix_for_netcode(self.netcode))

    def public_copy(self):
        """Yield the corresponding public node for this node."""
        return self.__class__(is_private=False, netcode=self.netcode, chain_code=self.chain_code,
                              depth=self.depth, parent_fingerprint=self.parent_fingerprint,
                              child_number=self.child_number, public_pair=self.public_pair)

    def _subkey(self, i, is_hardened, as_private):
        """Yield a child node for this node.

        i: the index for this node.
        is_hardened: use "hardened key derivation". That is, the public version
            of this node cannot calculate this child.
        as_private: set to True to get a private subkey.

        Note that setting i<0 uses private key derivation, no matter the
        value for is_hardened."""
        if i > 0xffffffff:
            raise ValueError("i is too big: %d" % i)
        if i < 0:
            is_hardened = True
            i_as_bytes = struct.pack(">l", i)
        else:
            if i >= 0x80000000:
                raise ValueError("subkey index 0x%x too large" % i)
            i &= 0x7fffffff
            if is_hardened:
                i |= 0x80000000
            i_as_bytes = struct.pack(">L", i)
        if is_hardened:
            if not self.is_private:
                raise PublicPrivateMismatchError("can't derive a private key from a public key")
            data = b'\0' + self.secret_exponent_bytes + i_as_bytes
        else:
            data = public_pair_to_sec(self.public_pair, compressed=True) + i_as_bytes
        I64 = hmac.HMAC(key=self.chain_code, msg=data, digestmod=hashlib.sha512).digest()
        I_left_as_exponent = from_bytes_32(I64[:32])
        d = dict(is_private=as_private, netcode=self.netcode, chain_code=I64[32:],
                 depth=self.depth+1, parent_fingerprint=self.fingerprint(), child_number=i)

        if as_private:
            exponent = (I_left_as_exponent + self.secret_exponent) % ecdsa.generator_secp256k1.order()
            d["secret_exponent_bytes"] = to_bytes_32(exponent)
        else:
            x, y = self.public_pair
            the_point = I_left_as_exponent * ecdsa.generator_secp256k1 +\
                ecdsa.Point(ecdsa.generator_secp256k1.curve(), x, y, ecdsa.generator_secp256k1.order())
            d["public_pair"] = the_point.pair()
        return self.__class__(**d)

    def subkey(self, i=0, is_hardened=False, as_private=None):
        if as_private is None:
            as_private = self.is_private
        is_hardened = not not is_hardened
        as_private = not not as_private
        lookup = (i, is_hardened, as_private)
        if lookup not in self.subkey_cache:
            self.subkey_cache[lookup] = self._subkey(i, is_hardened, as_private)
        return self.subkey_cache[lookup]

    def subkey_for_path(self, path):
        """
        path: a path of subkeys denoted by numbers and slashes. Use
            H or i<0 for private key derivation. End with .pub to force
            the key public.

        Examples:
            1H/-5/2/1 would call subkey(i=1, is_hardened=True).subkey(i=-5).
                subkey(i=2).subkey(i=1) and then yield the private key
            0/0/458.pub would call subkey(i=0).subkey(i=0).subkey(i=458) and
                then yield the public key

        You should choose one of the p or the negative number convention for private key
        derivation and stick with it.
        """
        force_public = (path[-4:] == '.pub')
        if force_public:
            path = path[:-4]
        key = self
        if path:
            invocations = path.split("/")
            for v in invocations:
                is_hardened = v[-1] in ("'pH")
                if is_hardened:
                    v = v[:-1]
                v = int(v)
                key = key.subkey(i=v, is_hardened=is_hardened, as_private=key.is_private)
        if force_public and key.is_private:
            key = key.public_copy()
        return key

    def subkeys_for_path(self, path):
        """
        A generalized form that can return multiple subkeys.
        """
        if path == '':
            yield self
            return

        def range_iterator(the_range):
            for r in the_range.split(","):
                is_hardened = r[-1] in "'pH"
                if is_hardened:
                    r = r[:-1]
                hardened_char = "H" if is_hardened else ''
                if '-' in r:
                    low, high = [int(x) for x in r.split("-", 1)]
                    for t in range(low, high+1):
                        yield "%d%s" % (t, hardened_char)
                else:
                    yield "%s%s" % (r, hardened_char)

        def subkey_iterator(subkey_paths):
            # examples:
            #   0/1H/0-4 => ['0/1H/0', '0/1H/1', '0/1H/2', '0/1H/3', '0/1H/4']
            #   0/2,5,9-11 => ['0/2', '0/5', '0/9', '0/10', '0/11']
            #   3H/2/5/15-20p => ['3H/2/5/15p', '3H/2/5/16p', '3H/2/5/17p', '3H/2/5/18p',
            #          '3H/2/5/19p', '3H/2/5/20p']
            #   5-6/7-8p,15/1-2 => ['5/7H/1', '5/7H/2', '5/8H/1', '5/8H/2',
            #         '5/15/1', '5/15/2', '6/7H/1', '6/7H/2', '6/8H/1', '6/8H/2', '6/15/1', '6/15/2']

            components = subkey_paths.split("/")
            iterators = [range_iterator(c) for c in components]
            for v in itertools.product(*iterators):
                yield '/'.join(v)

        for subkey in subkey_iterator(path):
            yield self.subkey_for_path(subkey)

    def children(self, max_level=50, start_index=0, include_hardened=True):
        for i in range(start_index, max_level+start_index+1):
            yield self.subkey(i)
            if include_hardened:
                yield self.subkey(i, is_hardened=True)

    def __repr__(self):
        if self.child_number == 0:
            r = self.wallet_key(as_private=False)
        else:
            r = self.bitcoin_address()
        if self.is_private:
            return "private_for <%s>" % r
        return "<%s>" % r

########NEW FILE########
__FILENAME__ = Key
from pycoin import ecdsa
from pycoin.key.validate import netcode_and_type_for_data
from pycoin.networks import address_prefix_for_netcode, wif_prefix_for_netcode

from pycoin.encoding import a2b_hashed_base58, secret_exponent_to_wif,\
    public_pair_to_sec, hash160,\
    hash160_sec_to_bitcoin_address, sec_to_public_pair,\
    is_sec_compressed, from_bytes_32, EncodingError

from .bip32 import Wallet


class Key(object):
    def __init__(self, hierarchical_wallet=None, secret_exponent=None, public_pair=None, hash160=None,
                 prefer_uncompressed=None, is_compressed=True, netcode='BTC'):
        """
        hierarchical_wallet:
            a bip32 wallet
        secret_exponent:
            a long representing the secret exponent
        public_pair:
            a tuple of long integers on the ecdsa curve
        hash160:
            a hash160 value corresponding to a bitcoin address
        Include at most one of hierarchical_wallet, secret_exponent, public_pair or hash160.
        prefer_uncompressed, is_compressed (booleans) are optional.
        netcode:
            the code for the network (as defined in pycoin.networks)
        """
        if [hierarchical_wallet, secret_exponent, public_pair, hash160].count(None) != 3:
            raise ValueError("exactly one of hierarchical_wallet, secret_exponent, public_pair, hash160"
                             " must be passed.")
        if prefer_uncompressed is None:
            prefer_uncompressed = not is_compressed
        self._prefer_uncompressed = prefer_uncompressed
        self._hierarchical_wallet = hierarchical_wallet
        self._secret_exponent = secret_exponent
        self._public_pair = public_pair
        if hash160:
            if is_compressed:
                self._hash160_compressed = hash160
            else:
                self._hash160_uncompressed = hash160
        self._netcode = netcode
        self._calculate_all()

    @classmethod
    def from_text(class_, text, is_compressed=True):
        """
        This function will accept a BIP0032 wallet string, a WIF, or a bitcoin address.

        The "is_compressed" parameter is ignored unless a public address is passed in.
        """

        data = a2b_hashed_base58(text)
        netcode, key_type = netcode_and_type_for_data(data)
        data = data[1:]

        if key_type in ("pub32", "prv32"):
            hw = Wallet.from_wallet_key(text)
            return Key(hierarchical_wallet=hw, netcode=netcode)

        if key_type == 'wif':
            is_compressed = (len(data) > 32)
            if is_compressed:
                data = data[:-1]
            return Key(
                secret_exponent=from_bytes_32(data),
                prefer_uncompressed=not is_compressed, netcode=netcode)
        if key_type == 'address':
            return Key(hash160=data, is_compressed=is_compressed, netcode=netcode)
        raise EncodingError("unknown text: %s" % text)

    @classmethod
    def from_sec(class_, sec):
        """
        Create a key from an sec bytestream (which is an encoding of a public pair).
        """
        public_pair = sec_to_public_pair(sec)
        return Key(public_pair=public_pair, prefer_uncompressed=not is_sec_compressed(sec))

    def public_copy(self):
        """
        Create a copy of this key with private key information removed.
        """
        if self._hierarchical_wallet:
            return Key(hierarchical_wallet=self._hierarchical_wallet.public_copy())
        if self.public_pair():
            return Key(public_pair=self.public_pair())
        return self

    def _calculate_all(self):
        for attr in "_secret_exponent _public_pair _wif_uncompressed _wif_compressed _sec_compressed" \
                " _sec_uncompressed _hash160_compressed _hash160_uncompressed _address_compressed" \
                " _address_uncompressed _netcode".split():
                setattr(self, attr, getattr(self, attr, None))

        if self._hierarchical_wallet:
            if self._hierarchical_wallet.is_private:
                self._secret_exponent = self._hierarchical_wallet.secret_exponent
            else:
                self._public_pair = self._hierarchical_wallet.public_pair
            self._netcode = self._hierarchical_wallet.netcode

        wif_prefix = wif_prefix_for_netcode(self._netcode)

        if self._secret_exponent:
            self._wif_uncompressed = secret_exponent_to_wif(
                self._secret_exponent, compressed=False, wif_prefix=wif_prefix)
            self._wif_compressed = secret_exponent_to_wif(
                self._secret_exponent, compressed=True, wif_prefix=wif_prefix)
            self._public_pair = ecdsa.public_pair_for_secret_exponent(
                ecdsa.generator_secp256k1, self._secret_exponent)

        if self._public_pair:
            self._sec_compressed = public_pair_to_sec(self._public_pair, compressed=True)
            self._sec_uncompressed = public_pair_to_sec(self._public_pair, compressed=False)
            self._hash160_compressed = hash160(self._sec_compressed)
            self._hash160_uncompressed = hash160(self._sec_uncompressed)

        address_prefix = address_prefix_for_netcode(self._netcode)

        if self._hash160_compressed:
            self._address_compressed = hash160_sec_to_bitcoin_address(
                self._hash160_compressed, address_prefix=address_prefix)

        if self._hash160_uncompressed:
            self._address_uncompressed = hash160_sec_to_bitcoin_address(
                self._hash160_uncompressed, address_prefix=address_prefix)

    def as_text(self):
        """
        Return a textual representation of this key.
        """
        if self._hierarchical_wallet:
            return self._hierarchical_wallet.wallet_key(as_private=self._hierarchical_wallet.is_private)
        if self._secret_exponent:
            return self.wif()
        return self.address()

    def hierarchical_wallet(self):
        return self._hierarchical_wallet

    def hwif(self, as_private=False):
        """
        Return a textual representation of the hiearachical wallet (reduced to public), or None.
        """
        if self._hierarchical_wallet:
            return self._hierarchical_wallet.wallet_key(as_private=as_private)
        return None

    def secret_exponent(self):
        """
        Return an integer representing the secret exponent (or None).
        """
        return self._secret_exponent

    def public_pair(self):
        """
        Return a pair of integers representing the public key (or None).
        """
        return self._public_pair

    def _use_uncompressed(self, use_uncompressed):
        if use_uncompressed:
            return use_uncompressed
        if use_uncompressed is None:
            return self._prefer_uncompressed
        return False

    def wif(self, use_uncompressed=None):
        """
        Return the WIF representation of this key, if available.
        If use_uncompressed is not set, the preferred representation is returned.
        """
        if self._use_uncompressed(use_uncompressed):
            return self._wif_uncompressed
        return self._wif_compressed

    def sec(self, use_uncompressed=None):
        """
        Return the SEC representation of this key, if available.
        If use_uncompressed is not set, the preferred representation is returned.
        """
        if self._use_uncompressed(use_uncompressed):
            return self._sec_uncompressed
        return self._sec_compressed

    def hash160(self, use_uncompressed=None):
        """
        Return the hash160 representation of this key, if available.
        If use_uncompressed is not set, the preferred representation is returned.
        """
        if self._use_uncompressed(use_uncompressed):
            return self._hash160_uncompressed
        return self._hash160_compressed

    def address(self, use_uncompressed=None):
        """
        Return the public address representation of this key, if available.
        If use_uncompressed is not set, the preferred representation is returned.
        """
        if self._use_uncompressed(use_uncompressed):
            return self._address_uncompressed
        return self._address_compressed

    def subkey(self, path_to_subkey):
        """
        Return the Key corresponding to the hierarchical wallet's subkey (or None).
        """
        if self._hierarchical_wallet:
            return Key(hierarchical_wallet=self._hierarchical_wallet.subkey_for_path(path_to_subkey))

    def subkeys(self, path_to_subkeys):
        """
        Return an iterator yielding Keys corresponding to the
        hierarchical wallet's subkey path (or just this key).
        """
        if self._hierarchical_wallet:
            for subwallet in self._hierarchical_wallet.subkeys_for_path(path_to_subkeys):
                yield Key(hierarchical_wallet=subwallet)
        else:
            yield self

########NEW FILE########
__FILENAME__ = validate

from .. import encoding
from .. import networks

DEFAULT_NETCODES = ["BTC"]
DEFAULT_ADDRESS_TYPES = ["address", "pay_to_script"]


def netcode_and_type_for_data(data):
    """
    Given some already-decoded raw data from a base58 string,
    return (N, T) where N is the network code ("BTC" or "LTC") and
    T is the data type ("wif", "address", "prv32", "pub32").
    May also raise EncodingError.
    """
    # TODO: check the data length is within correct range for data type
    INDEX_LIST = [
        ('wif_prefix', "wif"),
        ('address_prefix', "address"),
        ('pay_to_script_prefix', "pay_to_script"),
        ('bip32_pub_prefix', "pub32"),
        ('bip32_priv_prefix', "prv32"),
    ]
    for ni in networks.NETWORKS:
        for attr, name in INDEX_LIST:
            v = getattr(ni, attr, None)
            if v is None:
                continue
            if data.startswith(v):
                return ni.code, name

    raise encoding.EncodingError("unknown prefix")


def _check_against(text, expected_type, allowable_netcodes):
    try:
        data = encoding.a2b_hashed_base58(text)
        netcode, the_type = netcode_and_type_for_data(data)
        if the_type in expected_type and netcode in allowable_netcodes:
            return netcode
    except encoding.EncodingError:
        pass
    return None


def is_address_valid(address, allowable_types=DEFAULT_ADDRESS_TYPES, allowable_netcodes=DEFAULT_NETCODES):
    """
    Accept an address, and a list of allowable address types (a subset of "address" and "pay_to_script"),
    and allowable networks (defaulting to just Bitcoin mainnet), return the network that the address is
    a part of, or None if it doesn't validate.
    """
    return _check_against(address, allowable_types, allowable_netcodes)


def is_wif_valid(wif, allowable_netcodes=DEFAULT_NETCODES):
    """
    Accept a WIF, and a list of allowable networks (defaulting to just Bitcoin mainnet), return
    the network that the wif is a part of, or None if it doesn't validate.
    """
    return _check_against(wif, ["wif"], allowable_netcodes)


def is_public_bip32_valid(hwif, allowable_netcodes=DEFAULT_NETCODES):
    """
    Accept a text representation of a BIP32 public wallet, and a list of allowable networks (defaulting
    to just Bitcoin mainnet), return the network that the wif is a part of, or None if it doesn't validate.
    """
    return _check_against(hwif, ["pub32"], allowable_netcodes)


def is_private_bip32_valid(hwif, allowable_netcodes=DEFAULT_NETCODES):
    """
    Accept a text representation of a BIP32 private wallet, and a list of allowable networks (defaulting
    to just Bitcoin mainnet), return the network that the wif is a part of, or None if it doesn't validate.
    """
    return _check_against(hwif, ["prv32"], allowable_netcodes)

########NEW FILE########
__FILENAME__ = merkle
# -*- coding: utf-8 -*-
"""
Implement Merkle hashing. See http://en.wikipedia.org/wiki/Merkle_tree


The MIT License (MIT)

Copyright (c) 2013 by Richard Kiss

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

from .encoding import double_sha256
from .serialize import h2b_rev


def merkle(hashes, hash_f=double_sha256):
    """Take a list of hashes, and return the root merkle hash."""
    while len(hashes) > 1:
        hashes = merkle_pair(hashes, hash_f)
    return hashes[0]


def merkle_pair(hashes, hash_f):
    """Take a list of hashes, and return the parent row in the tree of merkle hashes."""
    if len(hashes) % 2 == 1:
        hashes = list(hashes)
        hashes.append(hashes[-1])
    l = []
    for i in range(0, len(hashes), 2):
        l.append(hash_f(hashes[i] + hashes[i+1]))
    return l


def test_merkle():
    s1 = h2b_rev("56dee62283a06e85e182e2d0b421aceb0eadec3d5f86cdadf9688fc095b72510")
    assert merkle([s1], double_sha256) == s1
    # from block 71043
    mr = h2b_rev("30325a06daadcefb0a3d1fe0b6112bb6dfef794316751afc63f567aef94bd5c8")
    s1 = h2b_rev("67ffe41e53534805fb6883b4708fd3744358f99e99bc52111e7a17248effebee")
    s2 = h2b_rev("c8b336acfc22d66edf6634ce095b888fe6d16810d9c85aff4d6641982c2499d1")
    assert merkle([s1, s2], double_sha256) == mr

    # from block 71038
    mr = h2b_rev("4f4c8c201e85a64a410cc7272c77f443d8b8df3289c67af9dab1e87d9e61985e")
    s1 = h2b_rev("f484b014c55a43b409a59de3177d49a88149b4473f9a7b81ea9e3535d4b7a301")
    s2 = h2b_rev("7b5636e9bc6ec910157e88702699bc7892675e8b489632c9166764341a4d4cfe")
    s3 = h2b_rev("f8b02b8bf25cb6008e38eb5453a22c502f37e76375a86a0f0cfaa3c301aa1209")
    assert merkle([s1, s2, s3], double_sha256) == mr

if __name__ == "__main__":
    test_merkle()

########NEW FILE########
__FILENAME__ = networks
from collections import namedtuple

from .serialize import h2b

NetworkValues = namedtuple('NetworkValues',
                           ('network_name', 'subnet_name', 'code', 'wif_prefix', 'address_prefix',
                            'pay_to_script_prefix', 'bip32_priv_prefix', 'bip32_pub_prefix'))

NETWORKS = (
    NetworkValues("Bitcoin", "mainnet", "BTC", b'\x80', b'\0', b'\5', h2b("0488ADE4"), h2b("0488B21E")),
    NetworkValues("Bitcoin", "testnet3", "XTN", b'\xef', b'\x6f', b'\xc4',
                  h2b("04358394"), h2b("043587CF")),
    NetworkValues("Litecoin", "mainnet", "LTC", b'\xb0', b'\x30', None, None, None),
    NetworkValues("Dogecoin", "mainnet", "DOGE", b'\x9e', b'\x1e', b'\x16',
                  h2b("02fda4e8"), h2b("02fda923")),
    # BlackCoin: unsure about bip32 prefixes; assuming will use Bitcoin's
    NetworkValues("Blackcoin", "mainnet", "BLK", b'\x99', b'\x19', None, h2b("0488ADE4"), h2b("0488B21E")),
)

# Map from short code to details about that network.
NETWORK_NAME_LOOKUP = dict((i.code, i) for i in NETWORKS)

# All network names, return in same order as list above: for UI purposes.
NETWORK_NAMES = [i.code for i in NETWORKS]


def _lookup(netcode, property):
    # Lookup a specific value needed for a specific network
    network = NETWORK_NAME_LOOKUP.get(netcode)
    if network:
        return getattr(network, property)
    return None


def network_name_for_netcode(netcode):
    return _lookup(netcode, "network_name")


def subnet_name_for_netcode(netcode):
    return _lookup(netcode, "subnet_name")


def full_network_name_for_netcode(netcode):
    network = NETWORK_NAME_LOOKUP[netcode]
    if network:
        return "%s %s" % (network.network_name, network.subnet_name)


def wif_prefix_for_netcode(netcode):
    return _lookup(netcode, "wif_prefix")


def address_prefix_for_netcode(netcode):
    return _lookup(netcode, "address_prefix")


def pay_to_script_prefix_for_netcode(netcode):
    return _lookup(netcode, "pay_to_script_prefix")


def prv32_prefix_for_netcode(netcode):
    return _lookup(netcode, "bip32_priv_prefix")


def pub32_prefix_for_netcode(netcode):
    return _lookup(netcode, "bip32_pub_prefix")

########NEW FILE########
__FILENAME__ = bitcoin_utils
#!/usr/bin/env python

import argparse
import binascii
import sys

from pycoin import ecdsa, encoding
from pycoin.ecdsa import secp256k1

def b2h(b):
    return binascii.hexlify(b).decode("utf8")

def parse_as_number(s):
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return int(s, 16)
    except ValueError:
        pass

def parse_as_private_key(s):
    v = parse_as_number(s)
    if v and v < secp256k1._r:
        return v
    try:
        v = encoding.wif_to_secret_exponent(s)
        return v
    except encoding.EncodingError:
        pass

def parse_as_public_pair(s):
    try:
        if s[:2] in (["02", "03", "04"]):
            return encoding.sec_to_public_pair(encoding.h2b(s))
    except (encoding.EncodingError, binascii.Error):
        pass
    for c in ",/":
        if c in s:
            s0, s1 = s.split(c, 1)
            v0 = parse_as_number(s0)
            if v0:
                if s1 in ("even", "odd"):
                    return ecdsa.public_pair_for_x(ecdsa.generator_secp256k1, v0, is_even=(s1=='even'))
                v1 = parse_as_number(s1)
                if v1:
                    if not ecdsa.is_public_pair_valid(ecdsa.generator_secp256k1, (v0, v1)):
                        sys.stderr.write("invalid (x, y) pair\n")
                        sys.exit(1)
                    return (v0, v1)

def parse_as_address(s):
    try:
        return encoding.bitcoin_address_to_hash160_sec(s)
    except encoding.EncodingError:
        pass
    try:
        v = encoding.h2b(s)
        if len(v) == 20:
            return v
    except binascii.Error:
        pass

def main():
    parser = argparse.ArgumentParser(description="Bitcoin utilities. WARNING: obsolete. Use ku instead.")

    parser.add_argument('-a', "--address", help='show as Bitcoin address', action='store_true')
    parser.add_argument('-1', "--hash160", help='show as hash 160', action='store_true')
    parser.add_argument('-v', "--verbose", help='dump all information available', action='store_true')
    parser.add_argument('-w', "--wif", help='show as Bitcoin WIF', action='store_true')
    parser.add_argument('-n', "--uncompressed", help='show in uncompressed form', action='store_true')
    parser.add_argument('item', help='a WIF, secret exponent, X/Y public pair, SEC (as hex), hash160 (as hex), Bitcoin address', nargs="+")
    args = parser.parse_args()

    for c in args.item:
        # figure out what it is:
        #  - secret exponent
        #  - WIF
        #  - X/Y public key (base 10 or hex)
        #  - sec
        #  - hash160
        #  - Bitcoin address
        secret_exponent = parse_as_private_key(c)
        if secret_exponent:
            public_pair = ecdsa.public_pair_for_secret_exponent(secp256k1.generator_secp256k1, secret_exponent)
            print("secret exponent: %d" % secret_exponent)
            print("  hex:           %x" % secret_exponent)
            print("WIF:             %s" % encoding.secret_exponent_to_wif(secret_exponent, compressed=True))
            print("  uncompressed:  %s" % encoding.secret_exponent_to_wif(secret_exponent, compressed=False))
        else:
            public_pair = parse_as_public_pair(c)
        if public_pair:
            bitcoin_address_uncompressed = encoding.public_pair_to_bitcoin_address(public_pair, compressed=False)
            bitcoin_address_compressed = encoding.public_pair_to_bitcoin_address(public_pair, compressed=True)
            print("public pair x:   %d" % public_pair[0])
            print("public pair y:   %d" % public_pair[1])
            print("  x as hex:      %x" % public_pair[0])
            print("  y as hex:      %x" % public_pair[1])
            print("y parity:        %s" % "odd" if (public_pair[1] & 1) else "even")
            print("key pair as sec: %s" % b2h(encoding.public_pair_to_sec(public_pair, compressed=True)))
            s = b2h(encoding.public_pair_to_sec(public_pair, compressed=False))
            print("  uncompressed:  %s\\\n                   %s" % (s[:66], s[66:]))
            hash160 = encoding.public_pair_to_hash160_sec(public_pair, compressed=True)
            hash160_unc = encoding.public_pair_to_hash160_sec(public_pair, compressed=False)
        else:
            hash160 = parse_as_address(c)
            hash160_unc = None
        if not hash160:
            sys.stderr.write("can't decode input %s\n" % c)
            sys.exit(1)
        print("hash160:         %s" % b2h(hash160))
        if hash160_unc:
            print("  uncompressed:  %s" % b2h(hash160_unc))
        print("Bitcoin address: %s" % encoding.hash160_sec_to_bitcoin_address(hash160))
        if hash160_unc:
            print("  uncompressed:  %s" % encoding.hash160_sec_to_bitcoin_address(hash160_unc))

#   - hash 160 (hex), Bitcoin address


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = block
#!/usr/bin/env python

import argparse
import binascii
import datetime

from pycoin.block import Block
from pycoin.scripts.tx import dump_tx
from pycoin.serialize import b2h_rev, stream_to_bytes


def dump_block(block, network):
    blob = stream_to_bytes(block.stream)
    print("%d bytes   block hash %s" % (len(blob), block.id()))
    print("version %d" % block.version)
    print("prior block hash %s" % b2h_rev(block.previous_block_hash))
    print("merkle root %s" % binascii.hexlify(block.merkle_root).decode("utf8"))
    print("timestamp %s" % datetime.datetime.utcfromtimestamp(block.timestamp).isoformat())
    print("difficulty %d" % block.difficulty)
    print("nonce %s" % block.nonce)
    print("%d transaction%s" % (len(block.txs), "s" if len(block.txs) != 1 else ""))
    for idx, tx in enumerate(block.txs):
        print("Tx #%d:" % idx)
        dump_tx(tx, netcode=network)


def main():
    parser = argparse.ArgumentParser(description="Dump a block in human-readable form.")
    parser.add_argument("block_bin", nargs="+", type=argparse.FileType('rb'),
                        help='The file containing the binary block.')

    args = parser.parse_args()

    for f in args.block_bin:
        block = Block.parse(f)
        dump_block(block, network='BTC')
        print('')

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = cache_tx
#!/usr/bin/env python

import argparse
import codecs
import io
import re

from pycoin.serialize import h2b_rev
from pycoin.services import get_tx_db
from pycoin.tx import Tx


def main():
    parser = argparse.ArgumentParser(description="Add a transaction to tx cache.")
    parser.add_argument("tx_id_or_path", nargs="+",
                        help='The id of the transaction to fetch from web services or the path to it.')

    args = parser.parse_args()

    TX_RE = re.compile(r"^[0-9a-fA-F]{64}$")

    tx_db = get_tx_db()

    for p in args.tx_id_or_path:
        if TX_RE.match(p):
            tx = tx_db.get(h2b_rev(p))
            if not tx:
                parser.error("can't find Tx with id %s" % p)
        else:
            f = open(p, "rb")
            try:
                if f.name.endswith("hex"):
                    f = io.BytesIO(codecs.getreader("hex_codec")(f).read())
                tx = Tx.parse(f)
            except Exception:
                parser.error("can't parse %s" % f.name)

        tx_db[tx.hash()] = tx
        print("cached %s" % tx.id())

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = fetch_unspent
#!/usr/bin/env python

import argparse

from pycoin.services import spendables_for_address
from pycoin.services.providers import message_about_spendables_for_address_env


def main():
    parser = argparse.ArgumentParser(
        description="Create a hex dump of unspent TxOut items for Bitcoin addresses.")
    parser.add_argument("bitcoin_address", help='a bitcoin address', nargs="+")

    args = parser.parse_args()

    m = message_about_spendables_for_address_env()
    if m:
        print("warning: %s" % m)

    for address in args.bitcoin_address:
        spendables = spendables_for_address(address, format="text")
        for spendable in spendables:
            print(spendable)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = genwallet
#!/usr/bin/env python

import argparse
import binascii
import json
import subprocess
import sys

from pycoin.key.bip32 import Wallet, PublicPrivateMismatchError
from pycoin.networks import full_network_name_for_netcode

def gpg_entropy():
    output = subprocess.Popen(["gpg", "--gen-random", "2", "64"], stdout=subprocess.PIPE).communicate()[0]
    return output

def dev_random_entropy():
    return open("/dev/random", "rb").read(64)

def b2h(b):
    return binascii.hexlify(b).decode("utf8")

def main():
    parser = argparse.ArgumentParser(description="Generate a private wallet key. WARNING: obsolete. Use ku instead.")

    parser.add_argument('-a', "--address", help='show as Bitcoin address', action='store_true')
    parser.add_argument('-i', "--info", help='show metadata', action='store_true')
    parser.add_argument('-j', "--json", help='output metadata as JSON', action='store_true')
    parser.add_argument('-w', "--wif", help='show as Bitcoin WIF', action='store_true')
    parser.add_argument('-f', "--wallet-key-file", help='initial wallet key', type=argparse.FileType('r'))
    parser.add_argument('-k', "--wallet-key", help='initial wallet key')
    parser.add_argument('-g', "--gpg", help='use gpg --gen-random to get additional entropy', action='store_true')
    parser.add_argument('-u', "--dev-random", help='use /dev/random to get additional entropy', action='store_true')
    parser.add_argument('-n', "--uncompressed", help='show in uncompressed form', action='store_true')
    parser.add_argument('-p', help='generate wallet key from passphrase. NOT RECOMMENDED', metavar='passphrase')
    parser.add_argument('-s', "--subkey", help='subkey path (example: 0p/2/1)')
    parser.add_argument('-t', help='generate test key', action="store_true")
    parser.add_argument('inputfile', help='source of entropy. stdin by default', type=argparse.FileType(mode='r+b'), nargs='?')
    args = parser.parse_args()

    # args.inputfile doesn't like binary when "-" is passed in. Deal with this.
    if args.inputfile == sys.stdin and hasattr(sys.stdin, "buffer"):
        args.inputfile = sys.stdin.buffer

    network = 'XTN' if args.t else 'BTC'

    entropy = bytearray()
    if args.gpg:
        entropy.extend(gpg_entropy())
    if args.dev_random:
        entropy.extend(dev_random_entropy())
    if args.inputfile:
        entropy.extend(args.inputfile.read())
    if args.p:
        entropy.extend(args.p.encode("utf8"))
    if len(entropy) == 0 and not args.wallet_key and not args.wallet_key_file:
        parser.error("you must specify at least one source of entropy")
    if args.wallet_key and len(entropy) > 0:
        parser.error("don't specify both entropy and a wallet key")
    if args.wallet_key_file:
        wallet = Wallet.from_wallet_key(args.wallet_key_file.readline()[:-1])
    elif args.wallet_key:
        wallet = Wallet.from_wallet_key(args.wallet_key)
    else:
        wallet = Wallet.from_master_secret(bytes(entropy), netcode=network)
    try:
        if args.subkey:
            wallet = wallet.subkey_for_path(args.subkey)
        if wallet.child_number >= 0x80000000:
            wc = wallet.child_number - 0x80000000
            child_index = "%dp (%d)" % (wc, wallet.child_number)
        else:
            child_index = "%d" % wallet.child_number
        if args.json:
            d = dict(
                wallet_key=wallet.wallet_key(as_private=wallet.is_private),
                public_pair_x=wallet.public_pair[0],
                public_pair_y=wallet.public_pair[1],
                tree_depth=wallet.depth,
                fingerprint=b2h(wallet.fingerprint()),
                parent_fingerprint=b2h(wallet.parent_fingerprint),
                child_index=child_index,
                chain_code=b2h(wallet.chain_code),
                bitcoin_addr=wallet.bitcoin_address(),
                bitcoin_addr_uncompressed=wallet.bitcoin_address(compressed=False),
                network="test" if wallet.is_test else "main",
            )
            if wallet.is_private:
                d.update(dict(
                    key="private",
                    secret_exponent=wallet.secret_exponent,
                    WIF=wallet.wif(),
                    WIF_uncompressed=wallet.wif(compressed=False)
                ))
            else:
                d.update(dict(key="public"))
            print(json.dumps(d, indent=3))
        elif args.info:
            print(wallet.wallet_key(as_private=wallet.is_private))
            print(full_network_name_for_netcode(wallet.netcode))
            if wallet.is_private:
                print("private key")
                print("secret exponent: %d" % wallet.secret_exponent)
            else:
                print("public key only")
            print("public pair x:   %d\npublic pair y:   %d" % wallet.public_pair)
            print("tree depth:      %d" % wallet.depth)
            print("fingerprint:     %s" % b2h(wallet.fingerprint()))
            print("parent f'print:  %s" % b2h(wallet.parent_fingerprint))
            print("child index:     %s" % child_index)
            print("chain code:      %s" % b2h(wallet.chain_code))
            if wallet.is_private:
                print("WIF:             %s" % wallet.wif())
                print("  uncompressed:  %s" % wallet.wif(compressed=False))
            print("Bitcoin address: %s" % wallet.bitcoin_address())
            print("  uncompressed:  %s" % wallet.bitcoin_address(compressed=False))
        elif args.address:
            print(wallet.bitcoin_address(compressed=not args.uncompressed))
        elif args.wif:
            print(wallet.wif(compressed=not args.uncompressed))
        else:
            print(wallet.wallet_key(as_private=wallet.is_private))
    except PublicPrivateMismatchError as ex:
        print(ex.args[0])


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = ku
#!/usr/bin/env python

from __future__ import print_function

import argparse
import json
import re
import subprocess
import sys

from pycoin import encoding
from pycoin.ecdsa import is_public_pair_valid, generator_secp256k1, public_pair_for_x, secp256k1
from pycoin.serialize import b2h, h2b
from pycoin.key import Key
from pycoin.key.bip32 import Wallet
from pycoin.networks import full_network_name_for_netcode, NETWORK_NAMES


SEC_RE = re.compile(r"^(0[23][0-9a-fA-F]{64})|(04[0-9a-fA-F]{128})$")
HASH160_RE = re.compile(r"^([0-9a-fA-F]{40})$")


def gpg_entropy():
    try:
        output = subprocess.Popen(
            ["gpg", "--gen-random", "2", "64"], stdout=subprocess.PIPE).communicate()[0]
        return output
    except OSError:
        sys.stderr.write("warning: can't open gpg, can't use as entropy source\n")
    return b''


def get_entropy():
    entropy = bytearray()
    try:
        entropy.extend(gpg_entropy())
    except Exception:
        print("warning: can't use gpg as entropy source", file=sys.stdout)
    try:
        entropy.extend(open("/dev/random", "rb").read(64))
    except Exception:
        print("warning: can't use /dev/random as entropy source", file=sys.stdout)
    entropy = bytes(entropy)
    if len(entropy) < 64:
        raise OSError("can't find sources of entropy")
    return entropy


def parse_as_number(s):
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return int(s, 16)
    except ValueError:
        pass


def parse_as_secret_exponent(s):
    v = parse_as_number(s)
    if v and v < secp256k1._r:
        return v


def parse_as_public_pair(s):
    for c in ",/":
        if c in s:
            s0, s1 = s.split(c, 1)
            v0 = parse_as_number(s0)
            if v0:
                if s1 in ("even", "odd"):
                    return public_pair_for_x(generator_secp256k1, v0, is_even=(s1 == 'even'))
                v1 = parse_as_number(s1)
                if v1:
                    if not is_public_pair_valid(generator_secp256k1, (v0, v1)):
                        sys.stderr.write("invalid (x, y) pair\n")
                        sys.exit(1)
                    return (v0, v1)


def create_output(item, key, subkey_path=None):
    output_dict = {}
    output_order = []

    def add_output(json_key, value=None, human_readable_key=None):
        if human_readable_key is None:
            human_readable_key = json_key.replace("_", " ")
        if value:
            output_dict[json_key.strip().lower()] = value
        output_order.append((json_key.lower(), human_readable_key))

    network_name = full_network_name_for_netcode(key._netcode)
    add_output("input", item)
    add_output("network", network_name)
    add_output("netcode", key._netcode)

    hw = key.hierarchical_wallet()
    if hw:
        if subkey_path:
            add_output("subkey_path", subkey_path)

        add_output("wallet_key", hw.wallet_key(as_private=hw.is_private))
        if hw.is_private:
            add_output("public_version", hw.wallet_key(as_private=False))

        if hw.child_number >= 0x80000000:
            wc = hw.child_number - 0x80000000
            child_index = "%dH (%d)" % (wc, hw.child_number)
        else:
            child_index = "%d" % hw.child_number
        add_output("tree_depth", "%d" % hw.depth)
        add_output("fingerprint", b2h(hw.fingerprint()))
        add_output("parent_fingerprint", b2h(hw.parent_fingerprint), "parent f'print")
        add_output("child_index", child_index)
        add_output("chain_code", b2h(hw.chain_code))

        add_output("private_key", "yes" if hw.is_private else "no")

    secret_exponent = key.secret_exponent()
    if secret_exponent:
        add_output("secret_exponent", '%d' % secret_exponent)
        add_output("secret_exponent_hex", '%x' % secret_exponent, " hex")
        add_output("wif", key.wif(use_uncompressed=False))
        add_output("wif_uncompressed", key.wif(use_uncompressed=True), " uncompressed")

    public_pair = key.public_pair()

    if public_pair:
        add_output("public_pair_x", '%d' % public_pair[0])
        add_output("public_pair_y", '%d' % public_pair[1])
        add_output("public_pair_x_hex", '%x' % public_pair[0], " x as hex")
        add_output("public_pair_y_hex", '%x' % public_pair[1], " y as hex")
        add_output("y_parity", "odd" if (public_pair[1] & 1) else "even")

        add_output("key_pair_as_sec", b2h(key.sec(use_uncompressed=False)))
        add_output("key_pair_as_sec_uncompressed", b2h(key.sec(use_uncompressed=True)), " uncompressed")

    hash160_c = key.hash160(use_uncompressed=False)
    if hash160_c:
        add_output("hash160", b2h(hash160_c))
    hash160_u = key.hash160(use_uncompressed=True)
    if hash160_u:
        add_output("hash160_uncompressed", b2h(hash160_u), " uncompressed")

    if hash160_c:
        add_output("%s_address" % key._netcode,
                key.address(use_uncompressed=False), "%s address" % network_name)

    if hash160_u:
        add_output("%s_address_uncompressed" % key._netcode,
                key.address(use_uncompressed=True), "%s uncompressed" % network_name)

    return output_dict, output_order


def dump_output(output_dict, output_order):
    print('')
    max_length = max(len(v[1]) for v in output_order)
    for key, hr_key in output_order:
        space_padding = ' ' * (1 + max_length - len(hr_key))
        val = output_dict.get(key)
        if val is None:
            print(hr_key)
        else:
            if len(val) > 80:
                val = "%s\\\n%s%s" % (val[:66], ' ' * (5 + max_length), val[66:])
            print("%s%s: %s" % (hr_key, space_padding, val))


def main():
    networks = "MTLD"
    parser = argparse.ArgumentParser(
        description='Crypto coin utility ku ("key utility") to show'
        ' information about Bitcoin or other cryptocoin data structures.',
        epilog='Known networks codes:\n  ' \
                + ', '.join(['%s (%s)'%(i, full_network_name_for_netcode(i)) for i in NETWORK_NAMES])
    )
    parser.add_argument('-w', "--wallet", help='show just Bitcoin wallet key', action='store_true')
    parser.add_argument('-W', "--wif", help='show just Bitcoin WIF', action='store_true')
    parser.add_argument('-a', "--address", help='show just Bitcoin address', action='store_true')
    parser.add_argument(
        '-u', "--uncompressed", help='show output in uncompressed form',
        action='store_true')
    parser.add_argument(
        '-P', "--public", help='only show public version of wallet keys',
        action='store_true')

    parser.add_argument('-j', "--json", help='output as JSON', action='store_true')

    parser.add_argument('-s', "--subkey", help='subkey path (example: 0H/2/15-20)')
    parser.add_argument('-n', "--network", help='specify network (default: BTC = Bitcoin)',
                                default='BTC', choices=NETWORK_NAMES)
    parser.add_argument("--override-network", help='override detected network type',
                                default=None, choices=NETWORK_NAMES)

    parser.add_argument(
        'item', nargs="+", help='a BIP0032 wallet key string;'
        ' a WIF;'
        ' a bitcoin address;'
        ' an SEC (ie. a 66 hex chars starting with 02, 03 or a 130 hex chars starting with 04);'
        ' the literal string "create" to create a new wallet key using strong entropy sources;'
        ' P:wallet passphrase (NOT RECOMMENDED);'
        ' H:wallet passphrase in hex (NOT RECOMMENDED);'
        ' secret_exponent (in decimal or hex);'
        ' x,y where x,y form a public pair (y is a number or one of the strings "even" or "odd");'
        ' hash160 (as 40 hex characters)')

    args = parser.parse_args()

    if args.override_network:
        # force network arg to match override, but also will override decoded data below.
        args.network = args.override_network

    PREFIX_TRANSFORMS = (
        ("P:", lambda s:
            Key(hierarchical_wallet=Wallet.from_master_secret(s.encode("utf8"), netcode=args.network))),
        ("H:", lambda s:
            Key(hierarchical_wallet=Wallet.from_master_secret(h2b(s), netcode=args.network))),
        ("create", lambda s:
            Key(hierarchical_wallet=Wallet.from_master_secret(get_entropy(), netcode=args.network))),
    )

    for item in args.item:
        key = None
        for k, f in PREFIX_TRANSFORMS:
            if item.startswith(k):
                try:
                    key = f(item[len(k):])
                    break
                except Exception:
                    pass
        else:
            try:
                key = Key.from_text(item)
            except encoding.EncodingError:
                pass
        if key is None:
            secret_exponent = parse_as_secret_exponent(item)
            if secret_exponent:
                key = Key(secret_exponent=secret_exponent, netcode=args.network)

        if SEC_RE.match(item):
            key = Key.from_sec(h2b(item))

        if key is None:
            public_pair = parse_as_public_pair(item)
            if public_pair:
                key = Key(public_pair=public_pair, netcode=args.network)

        if HASH160_RE.match(item):
            key = Key(hash160=h2b(item), netcode=args.network)

        if key is None:
            print("can't parse %s" % item, file=sys.stderr)
            continue

        if args.override_network:
            # Override the network value, so we can take the same xpubkey and view what
            # the values would be on each other network type.
            # XXX public interface for this is needed...
            key._netcode = args.override_network
            key._hierarchical_wallet.netcode = args.override_network

        for key in key.subkeys(args.subkey or ""):
            if args.public:
                key = key.public_copy()

            output_dict, output_order = create_output(item, key)

            if args.json:
                print(json.dumps(output_dict, indent=3))
            elif args.wallet:
                print(output_dict["wallet_key"])
            elif args.wif:
                print(output_dict["wif_uncompressed" if args.uncompressed else "wif"])
            elif args.address:
                print(output_dict[ args.network.lower() + "_address" +
                    ("_uncompressed" if args.uncompressed else "")])
            else:
                dump_output(output_dict, output_order)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = spend
#!/usr/bin/env python

# Sample usage (with fake coinbase transaction):
# ./spend.py `./spend.py -c KxwGdpvzjzD5r6Qwg5Ev7gAv2Wn53tmSFfingBThhJEThQFcWPdj/20` 19TKi9Mv8AVLguAVYyCTY5twy5PKoEqrRf/19.9999 -p KxwGdpvzjzD5r6Qwg5Ev7gAv2Wn53tmSFfingBThhJEThQFcWPdj

import argparse
import binascii
import decimal
import io
import itertools
import sys

from pycoin import ecdsa
from pycoin import encoding
from pycoin.convention import tx_fee, btc_to_satoshi, satoshi_to_btc
from pycoin.services import blockchain_info
from pycoin.tx import Tx, UnsignedTx, TxOut, SecretExponentSolver
from pycoin.wallet import Wallet

def roundrobin(*iterables):
    "roundrobin('ABC', 'D', 'EF') --> A D E B F C"
    # Recipe credited to George Sakkis
    pending = len(iterables)
    nexts = itertools.cycle(iter(it).next for it in iterables)
    while pending:
        try:
            for next in nexts:
                yield next()
        except StopIteration:
            pending -= 1
            nexts = itertools.cycle(itertools.islice(nexts, pending))

def secret_exponents_iterator(wif_file, private_keys):
    def private_key_iterator(pk):
        try:
            wallet = Wallet.from_wallet_key(pk)
            return (w.secret_exponent for w in wallet.children(max_level=50, start_index=0))
        except (encoding.EncodingError, TypeError):
            try:
                exp = encoding.wif_to_secret_exponent(pk)
                return [exp]
            except encoding.EncodingError:
                sys.stderr.write('bad value: "%s"\n' % pk)
                sys.exit(1)

    iterables = []
    if wif_file:
        for l in wif_file:
            iterables.append(private_key_iterator(l[:-1]))
    if private_keys:
        for pk in private_keys:
            iterables.append(private_key_iterator(pk))
    for v in roundrobin(*iterables):
        yield v

def calculate_fees(unsigned_tx):
    total_value = sum(unsigned_tx_out.coin_value for unsigned_tx_out in unsigned_tx.unsigned_txs_out)
    total_spent = sum(tx_out.coin_value for tx_out in unsigned_tx.new_txs_out)
    return total_value, total_spent

def check_fees(unsigned_tx):
    total_value, total_spent = calculate_fees(unsigned_tx)
    actual_tx_fee = total_value - total_spent
    recommended_tx_fee = tx_fee.recommended_fee_for_tx(unsigned_tx)
    if actual_tx_fee > recommended_tx_fee:
        print("warning: transaction fee of exceeds expected value of %s BTC" % satoshi_to_btc(recommended_tx_fee))
    elif actual_tx_fee < 0:
        print("not enough source coins (%s BTC) for destination (%s BTC). Short %s BTC" % (satoshi_to_btc(total_value), satoshi_to_btc(total_spent), satoshi_to_btc(-actual_tx_fee)))
    elif actual_tx_fee < recommended_tx_fee:
        print("warning: transaction fee lower than (casually calculated) expected value of %s BTC, transaction might not propogate" % satoshi_to_btc(recommended_tx_fee))
    return actual_tx_fee

def get_unsigned_tx(parser):
    args = parser.parse_args()
    # if there is only one item passed, it's assumed to be hex
    if len(args.txinfo) == 1:
        try:
            s = io.BytesIO(binascii.unhexlify(args.txinfo[0].decode("utf8")))
            return UnsignedTx.parse(s)
        except Exception:
            parser.error("can't parse %s as hex\n" % args.txinfo[0])

    coins_from = []
    coins_to = []
    for txinfo in args.txinfo:
        if '/' in txinfo:
            parts = txinfo.split("/")
            if len(parts) == 2:
                # we assume it's an output
                address, amount = parts
                amount = btc_to_satoshi(amount)
                coins_to.append((amount, address))
            else:
                try:
                    # we assume it's an input of the form
                    #  tx_hash_hex/tx_output_index_decimal/tx_out_val/tx_out_script_hex
                    tx_hash_hex, tx_output_index_decimal, tx_out_val, tx_out_script_hex = parts
                    tx_hash = binascii.unhexlify(tx_hash_hex)
                    tx_output_index = int(tx_output_index_decimal)
                    tx_out_val = btc_to_satoshi(decimal.Decimal(tx_out_val))
                    tx_out_script = binascii.unhexlify(tx_out_script_hex)
                    tx_out = TxOut(tx_out_val, tx_out_script)
                    coins_source = (tx_hash, tx_output_index, tx_out)
                    coins_from.append(coins_source)
                except Exception:
                    parser.error("can't parse %s\n" % txinfo)
        else:
            print("looking up funds for %s from blockchain.info" % txinfo)
            coins_sources = blockchain_info.unspent_tx_outs_info_for_address(txinfo)
            coins_from.extend(coins_sources)

    unsigned_tx = UnsignedTx.standard_tx(coins_from, coins_to)
    return unsigned_tx

def create_coinbase_tx(parser):
    args = parser.parse_args()
    try:
        if len(args.txinfo) != 1:
            parser.error("coinbase transactions need exactly one output parameter (wif/BTC count)")
        wif, btc_amount = args.txinfo[0].split("/")
        satoshi_amount = btc_to_satoshi(btc_amount)
        secret_exponent, compressed = encoding.wif_to_tuple_of_secret_exponent_compressed(wif)
        public_pair = ecdsa.public_pair_for_secret_exponent(ecdsa.secp256k1.generator_secp256k1, secret_exponent)
        public_key_sec = encoding.public_pair_to_sec(public_pair, compressed=compressed)
        coinbase_tx = Tx.coinbase_tx(public_key_sec, satoshi_amount)
        return coinbase_tx
    except Exception:
        parser.error("coinbase transactions need exactly one output parameter (wif/BTC count)")

EPILOG = "If you generate an unsigned transaction, the output is a hex dump that can be used by this script on an air-gapped machine."

def main():
    parser = argparse.ArgumentParser(description="Create a Bitcoin transaction.", epilog=EPILOG)

    parser.add_argument('-g', "--generate-unsigned", help='generate unsigned transaction', action='store_true')
    parser.add_argument('-f', "--private-key-file", help='file containing WIF or BIP0032 private keys', metavar="path-to-file-with-private-keys", type=argparse.FileType('r'))
    parser.add_argument('-p', "--private-key", help='WIF or BIP0032 private key', metavar="private-key", type=str, nargs="+")
    parser.add_argument('-c', "--coinbase", help='Create a (bogus) coinbase transaction. For testing purposes. You must include exactly one WIF in this case.', action='store_true')
    parser.add_argument("txinfo", help='either a hex dump of the unsigned transaction, or a list of bitcoin addresses with optional "/value" if they are destination addresses', nargs="+")

    args = parser.parse_args()
    if args.coinbase:
        new_tx = create_coinbase_tx(parser)
        tx_hash_hex = binascii.hexlify(new_tx.hash())
        tx_output_index = 0
        tx_out_val = str(satoshi_to_btc(new_tx.txs_out[tx_output_index].coin_value))
        tx_out_script_hex = binascii.hexlify(new_tx.txs_out[tx_output_index].script)
        # product output in the form:
        #  tx_hash_hex/tx_output_index_decimal/tx_out_val/tx_out_script_hex
        # which can be used as a fake input to a later transaction
        print("/".join([tx_hash_hex, str(tx_output_index), tx_out_val, tx_out_script_hex]))
        return

    unsigned_tx = get_unsigned_tx(parser)
    actual_tx_fee = check_fees(unsigned_tx)
    if actual_tx_fee < 0:
        sys.exit(1)
    print("transaction fee: %s BTC" % satoshi_to_btc(actual_tx_fee))

    if args.generate_unsigned:
        s = io.BytesIO()
        unsigned_tx.stream(s)
        tx_bytes = s.getvalue()
        tx_hex = binascii.hexlify(tx_bytes).decode("utf8")
        print(tx_hex)
        sys.exit(0)

    secret_exponents = secret_exponents_iterator(args.private_key_file, args.private_key)
    solver = SecretExponentSolver(secret_exponents)
    new_tx = unsigned_tx.sign(solver)
    s = io.BytesIO()
    new_tx.stream(s)
    tx_bytes = s.getvalue()
    tx_hex = binascii.hexlify(tx_bytes).decode("utf8")
    print("copy the following hex to http://blockchain.info/pushtx to put the transaction on the network:\n")
    print(tx_hex)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = tx
#!/usr/bin/env python

from __future__ import print_function

import argparse
import calendar
import codecs
import datetime
import io
import os.path
import re
import subprocess
import sys

from pycoin import encoding
from pycoin.convention import tx_fee, satoshi_to_mbtc
from pycoin.key import Key
from pycoin.networks import address_prefix_for_netcode
from pycoin.serialize import b2h_rev, h2b_rev, stream_to_bytes
from pycoin.services import spendables_for_address, get_tx_db
from pycoin.services.providers import message_about_tx_cache_env, \
    message_about_get_tx_env, message_about_spendables_for_address_env
from pycoin.tx import Spendable, Tx, TxOut
from pycoin.tx.Tx import BadSpendableError
from pycoin.tx.tx_utils import distribute_from_split_pool, sign_tx
from pycoin.tx.TxOut import standard_tx_out_script


DEFAULT_VERSION = 1
DEFAULT_LOCK_TIME = 0
LOCKTIME_THRESHOLD = 500000000


def validate_bitcoind(tx, tx_db, bitcoind_url):
    try:
        from pycoin.services.bitcoind import bitcoind_agrees_on_transaction_validity
        if bitcoind_agrees_on_transaction_validity(bitcoind_url, tx):
            print("interop test passed for %s" % tx.id(), file=sys.stderr)
        else:
            print("tx ==> %s FAILED interop test" % tx.id(), file=sys.stderr)
    except ImportError:
        print("warning: can't talk to bitcoind due to missing library")


def dump_tx(tx, netcode='BTC'):
    address_prefix = address_prefix_for_netcode(netcode)
    tx_bin = stream_to_bytes(tx.stream)
    print("Version: %2d  tx hash %s  %d bytes   " % (tx.version, tx.id(), len(tx_bin)))
    print("TxIn count: %d; TxOut count: %d" % (len(tx.txs_in), len(tx.txs_out)))
    if tx.lock_time == 0:
        meaning = "valid anytime"
    elif tx.lock_time < LOCKTIME_THRESHOLD:
        meaning = "valid after block index %d" % tx.lock_time
    else:
        when = datetime.datetime.utcfromtimestamp(tx.lock_time)
        meaning = "valid on or after %s utc" % when.isoformat()
    print("Lock time: %d (%s)" % (tx.lock_time, meaning))
    print("Input%s:" % ('s' if len(tx.txs_in) != 1 else ''))
    missing_unspents = tx.missing_unspents()
    for idx, tx_in in enumerate(tx.txs_in):
        if tx.is_coinbase():
            print("%3d: COINBASE  %12.5f mBTC" % (idx, satoshi_to_mbtc(tx.total_in())))
        else:
            suffix = ""
            if tx.missing_unspent(idx):
                address = tx_in.bitcoin_address(address_prefix=address_prefix)
            else:
                tx_out = tx.unspents[idx]
                sig_result = " sig ok" if tx.is_signature_ok(idx) else " BAD SIG"
                suffix = " %12.5f mBTC %s" % (satoshi_to_mbtc(tx_out.coin_value), sig_result)
                address = tx_out.bitcoin_address(netcode=netcode)
            print("%3d: %34s from %s:%d%s" % (idx, address, b2h_rev(tx_in.previous_hash),
                  tx_in.previous_index, suffix))
    print("Output%s:" % ('s' if len(tx.txs_out) != 1 else ''))
    for idx, tx_out in enumerate(tx.txs_out):
        amount_mbtc = satoshi_to_mbtc(tx_out.coin_value)
        address = tx_out.bitcoin_address(netcode=netcode) or "(unknown)"
        print("%3d: %34s receives %12.5f mBTC" % (idx, address, amount_mbtc))
    if not missing_unspents:
        print("Total input  %12.5f mBTC" % satoshi_to_mbtc(tx.total_in()))
    print(    "Total output %12.5f mBTC" % satoshi_to_mbtc(tx.total_out()))
    if not missing_unspents:
        print("Total fees   %12.5f mBTC" % satoshi_to_mbtc(tx.fee()))


def check_fees(tx):
    total_in, total_out = tx.total_in(), tx.total_out()
    actual_tx_fee = total_in - total_out
    recommended_tx_fee = tx_fee.recommended_fee_for_tx(tx)
    print("warning: transaction fees recommendations casually calculated and estimates may be incorrect",
          file=sys.stderr)
    if actual_tx_fee > recommended_tx_fee:
        print("warning: transaction fee of %s exceeds expected value of %s mBTC" %
              (satoshi_to_mbtc(actual_tx_fee), satoshi_to_mbtc(recommended_tx_fee)),
              file=sys.stderr)
    elif actual_tx_fee < 0:
        print("not enough source coins (%s mBTC) for destination (%s mBTC)."
              " Short %s mBTC" %
              (satoshi_to_mbtc(total_in),
               satoshi_to_mbtc(total_out), satoshi_to_mbtc(-actual_tx_fee)),
              file=sys.stderr)
    elif actual_tx_fee < recommended_tx_fee:
        print("warning: transaction fee lower than (casually calculated)"
              " expected value of %s mBTC, transaction might not propogate" %
              satoshi_to_mbtc(recommended_tx_fee), file=sys.stderr)
    return actual_tx_fee


EARLIEST_DATE = datetime.datetime(year=2009, month=1, day=1)


def parse_locktime(s):
    s = re.sub(r"[ ,:\-]+", r"-", s)
    for fmt1 in ["%Y-%m-%dT", "%Y-%m-%d", "%b-%d-%Y", "%b-%d-%y", "%B-%d-%Y", "%B-%d-%y"]:
        for fmt2 in ["T%H-%M-%S", "T%H-%M", "-%H-%M-%S", "-%H-%M", ""]:
            fmt = fmt1 + fmt2
            try:
                when = datetime.datetime.strptime(s, fmt)
                if when < EARLIEST_DATE:
                    raise ValueError("invalid date: must be after %s" % EARLIEST_DATE)
                return calendar.timegm(when.timetuple())
            except ValueError:
                pass
    return int(s)


def parse_fee(fee):
    if fee in ["standard"]:
        return fee
    return int(fee)


EPILOG = 'Files are binary by default unless they end with the suffix ".hex".'


def main():
    parser = argparse.ArgumentParser(
        description="Manipulate bitcoin (or alt coin) transactions.",
        epilog=EPILOG)

    parser.add_argument('-t', "--transaction-version", type=int,
                        help='Transaction version, either 1 (default) or 3 (not yet supported).')

    parser.add_argument('-l', "--lock-time", type=parse_locktime, help='Lock time; either a block'
                        'index, or a date/time (example: "2014-01-01T15:00:00"')

    parser.add_argument('-n', "--network", default="BTC",
                        help='Define network code (M=Bitcoin mainnet, T=Bitcoin testnet).')

    parser.add_argument('-a', "--augment", action='store_true',
                        help='augment tx by adding any missing spendable metadata by fetching'
                             ' inputs from cache and/or web services')

    parser.add_argument("-i", "--fetch-spendables", metavar="address", action="append",
                        help='Add all unspent spendables for the given bitcoin address. This information'
                        ' is fetched from web services.')

    parser.add_argument('-f', "--private-key-file", metavar="path-to-private-keys", action="append",
                        help='file containing WIF or BIP0032 private keys. If file name ends with .gpg, '
                        '"gpg -d" will be invoked automatically. File is read one line at a time, and if '
                        'the file contains only one WIF per line, it will also be scanned for a bitcoin '
                        'address, and any addresses found will be assumed to be public keys for the given'
                        ' private key.',
                        type=argparse.FileType('r'))

    parser.add_argument('-g', "--gpg-argument", help='argument to pass to gpg (besides -d).', default='')

    parser.add_argument("--remove-tx-in", metavar="tx_in_index_to_delete", action="append", type=int,
                        help='remove a tx_in')

    parser.add_argument("--remove-tx-out", metavar="tx_out_index_to_delete", action="append", type=int,
                        help='remove a tx_out')

    parser.add_argument('-F', "--fee", help='fee, in satoshis, to pay on transaction, or '
                        '"standard" to auto-calculate. This is only useful if the "split pool" '
                        'is used; otherwise, the fee is automatically set to the unclaimed funds.',
                        default="standard", metavar="transaction-fee", type=parse_fee)

    parser.add_argument('-u', "--show-unspents", action='store_true',
                        help='show TxOut items for this transaction in Spendable form.')

    parser.add_argument('-b', "--bitcoind-url",
                        help='URL to bitcoind instance to validate against (http://user:pass@host:port).')

    parser.add_argument('-o', "--output-file", metavar="path-to-output-file", type=argparse.FileType('wb'),
                        help='file to write transaction to. This supresses most other output.')

    parser.add_argument("argument", nargs="+", help='generic argument: can be a hex transaction id '
                        '(exactly 64 characters) to be fetched from cache or a web service;'
                        ' a transaction as a hex string; a path name to a transaction to be loaded;'
                        ' a spendable 4-tuple of the form tx_id/tx_out_idx/script_hex/satoshi_count '
                        'to be added to TxIn list; an address/satoshi_count to be added to the TxOut '
                        'list; an address to be added to the TxOut list and placed in the "split'
                        ' pool".')

    args = parser.parse_args()

    # defaults

    txs = []
    spendables = []
    payables = []

    key_iters = []

    TX_ID_RE = re.compile(r"^[0-9a-fA-F]{64}$")

    # there are a few warnings we might optionally print out, but only if
    # they are relevant. We don't want to print them out multiple times, so we
    # collect them here and print them at the end if they ever kick in.

    warning_tx_cache = None
    warning_get_tx = None
    warning_spendables = None

    if args.private_key_file:
        wif_re = re.compile(r"[1-9a-km-zA-LMNP-Z]{51,111}")
        # address_re = re.compile(r"[1-9a-kmnp-zA-KMNP-Z]{27-31}")
        for f in args.private_key_file:
            if f.name.endswith(".gpg"):
                gpg_args = ["gpg", "-d"]
                if args.gpg_argument:
                    gpg_args.extend(args.gpg_argument.split())
                gpg_args.append(f.name)
                popen = subprocess.Popen(gpg_args, stdout=subprocess.PIPE)
                f = popen.stdout
            for line in f.readlines():
                # decode
                if isinstance(line, bytes):
                    line = line.decode("utf8")
                # look for WIFs
                possible_keys = wif_re.findall(line)

                def make_key(x):
                    try:
                        return Key.from_text(x)
                    except Exception:
                        return None

                keys = [make_key(x) for x in possible_keys]
                for key in keys:
                    if key:
                        key_iters.append((k.wif() for k in key.subkeys("")))

                # if len(keys) == 1 and key.hierarchical_wallet() is None:
                #    # we have exactly 1 WIF. Let's look for an address
                #   potential_addresses = address_re.findall(line)

    # we create the tx_db lazily
    tx_db = None

    for arg in args.argument:

        # hex transaction id
        if TX_ID_RE.match(arg):
            if tx_db is None:
                warning_tx_cache = message_about_tx_cache_env()
                warning_get_tx = message_about_get_tx_env()
                tx_db = get_tx_db()
            tx = tx_db.get(h2b_rev(arg))
            if not tx:
                for m in [warning_tx_cache, warning_get_tx, warning_spendables]:
                    if m:
                        print("warning: %s" % m, file=sys.stderr)
                parser.error("can't find Tx with id %s" % arg)
            txs.append(tx)
            continue

        # hex transaction data
        try:
            tx = Tx.tx_from_hex(arg)
            txs.append(tx)
            continue
        except Exception:
            pass

        try:
            key = Key.from_text(arg)
            # TODO: check network
            if key.wif() is None:
                payables.append((key.address(), 0))
                continue
            # TODO: support paths to subkeys
            key_iters.append((k.wif() for k in key.subkeys("")))
            continue
        except Exception:
            pass

        if os.path.exists(arg):
            try:
                with open(arg, "rb") as f:
                    if f.name.endswith("hex"):
                        f = io.BytesIO(codecs.getreader("hex_codec")(f).read())
                    tx = Tx.parse(f)
                    txs.append(tx)
                    try:
                        tx.parse_unspents(f)
                    except Exception as ex:
                        pass
                    continue
            except Exception:
                pass

        parts = arg.split("/")
        if len(parts) == 4:
            # spendable
            try:
                spendables.append(Spendable.from_text(arg))
                continue
            except Exception:
                pass

        # TODO: fix allowable_prefixes
        allowable_prefixes = b'\0'
        if len(parts) == 2 and encoding.is_valid_bitcoin_address(
                parts[0], allowable_prefixes=allowable_prefixes):
            try:
                payables.append(parts)
                continue
            except ValueError:
                pass

        parser.error("can't parse %s" % arg)

    if args.fetch_spendables:
        warning_spendables = message_about_spendables_for_address_env()
        for address in args.fetch_spendables:
            spendables.extend(spendables_for_address(address))

    for tx in txs:
        if tx.missing_unspents() and args.augment:
            if tx_db is None:
                warning_tx_cache = message_about_tx_cache_env()
                warning_get_tx = message_about_get_tx_env()
                tx_db = get_tx_db()
            tx.unspents_from_db(tx_db, ignore_missing=True)

    txs_in = []
    txs_out = []
    unspents = []
    # we use a clever trick here to keep each tx_in corresponding with its tx_out
    for tx in txs:
        smaller = min(len(tx.txs_in), len(tx.txs_out))
        txs_in.extend(tx.txs_in[:smaller])
        txs_out.extend(tx.txs_out[:smaller])
        unspents.extend(tx.unspents[:smaller])
    for tx in txs:
        smaller = min(len(tx.txs_in), len(tx.txs_out))
        txs_in.extend(tx.txs_in[smaller:])
        txs_out.extend(tx.txs_out[smaller:])
        unspents.extend(tx.unspents[smaller:])
    for spendable in spendables:
        txs_in.append(spendable.tx_in())
        unspents.append(spendable)
    for address, coin_value in payables:
        script = standard_tx_out_script(address)
        txs_out.append(TxOut(coin_value, script))

    lock_time = args.lock_time
    version = args.transaction_version

    # if no lock_time is explicitly set, inherit from the first tx or use default
    if lock_time is None:
        if txs:
            lock_time = txs[0].lock_time
        else:
            lock_time = DEFAULT_LOCK_TIME

    # if no version is explicitly set, inherit from the first tx or use default
    if version is None:
        if txs:
            version = txs[0].version
        else:
            version = DEFAULT_VERSION

    if args.remove_tx_in:
        s = set(args.remove_tx_in)
        txs_in = [tx_in for idx, tx_in in enumerate(txs_in) if idx not in s]

    if args.remove_tx_out:
        s = set(args.remove_tx_out)
        txs_out = [tx_out for idx, tx_out in enumerate(txs_out) if idx not in s]

    tx = Tx(txs_in=txs_in, txs_out=txs_out, lock_time=lock_time, version=version, unspents=unspents)

    fee = args.fee
    try:
        distribute_from_split_pool(tx, fee)
    except ValueError as ex:
        print("warning: %s" % ex.args[0], file=sys.stderr)

    unsigned_before = tx.bad_signature_count()
    if unsigned_before > 0 and key_iters:
        def wif_iter(iters):
            while len(iters) > 0:
                for idx, iter in enumerate(iters):
                    try:
                        wif = next(iter)
                        yield wif
                    except StopIteration:
                        iters = iters[:idx] + iters[idx+1:]
                        break

        print("signing...", file=sys.stderr)
        sign_tx(tx, wif_iter(key_iters))

    unsigned_after = tx.bad_signature_count()
    if unsigned_after > 0 and key_iters:
        print("warning: %d TxIn items still unsigned" % unsigned_after, file=sys.stderr)

    if len(tx.txs_in) == 0:
        print("warning: transaction has no inputs", file=sys.stderr)

    if len(tx.txs_out) == 0:
        print("warning: transaction has no outputs", file=sys.stderr)

    include_unspents = (unsigned_after > 0)
    tx_as_hex = tx.as_hex(include_unspents=include_unspents)

    if args.output_file:
        f = args.output_file
        if f.name.endswith(".hex"):
            f.write(tx_as_hex)
        else:
            tx.stream(f)
            if include_unspents:
                tx.stream_unspents(f)
        f.close()
    elif args.show_unspents:
        for spendable in tx.tx_outs_as_spendable():
            print(spendable.as_text())
    else:
        if not tx.missing_unspents():
            check_fees(tx)
        dump_tx(tx, args.network)
        if include_unspents:
            print("including unspents in hex dump since transaction not fully signed")
        print(tx_as_hex)

    if args.bitcoind_url:
        if tx_db is None:
            warning_tx_cache = message_about_tx_cache_env()
            warning_get_tx = message_about_get_tx_env()
            tx_db = get_tx_db()
        validate_bitcoind(tx, tx_db, args.bitcoind_url)

    if tx.missing_unspents():
        print("\n** can't validate transaction as source transactions missing", file=sys.stderr)
    else:
        try:
            if tx_db is None:
                warning_tx_cache = message_about_tx_cache_env()
                warning_get_tx = message_about_get_tx_env()
                tx_db = get_tx_db()
            tx.validate_unspents(tx_db)
            print('all incoming transaction values validated')
        except BadSpendableError as ex:
            print("\n**** ERROR: FEES INCORRECTLY STATED: %s" % ex.args[0], file=sys.stderr)
        except Exception as ex:
            print("\n*** can't validate source transactions as untampered: %s" %
                  ex.args[0], file=sys.stderr)

    # print warnings
    for m in [warning_tx_cache, warning_get_tx, warning_spendables]:
        if m:
            print("warning: %s" % m, file=sys.stderr)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = bitcoin_streamer

import struct

from .streamer import Streamer


def parse_bc_int(f):
    v = ord(f.read(1))
    if v == 253:
        v = struct.unpack("<H", f.read(2))[0]
    elif v == 254:
        v = struct.unpack("<L", f.read(4))[0]
    elif v == 255:
        v = struct.unpack("<Q", f.read(8))[0]
    return v


def parse_bc_string(f):
    size = parse_bc_int(f)
    return f.read(size)


def stream_bc_int(f, v):
    if v < 253:
        f.write(struct.pack("<B", v))
    elif v <= 65535:
        f.write(b'\xfd' + struct.pack("<H", v))
    elif v <= 0xffffffff:
        f.write(b'\xfe' + struct.pack("<L", v))
    else:
        f.write(b'\xff' + struct.pack("<Q", v))


def stream_bc_string(f, v):
    stream_bc_int(f, len(v))
    f.write(v)

STREAMER_FUNCTIONS = {
    "I": (parse_bc_int, stream_bc_int),
    "S": (parse_bc_string, stream_bc_string),
    "h": (lambda f: struct.unpack("!H", f.read(2))[0], lambda f, v: f.write(struct.pack("!H", v))),
    "L": (lambda f: struct.unpack("<L", f.read(4))[0], lambda f, v: f.write(struct.pack("<L", v))),
    "Q": (lambda f: struct.unpack("<Q", f.read(8))[0], lambda f, v: f.write(struct.pack("<Q", v))),
    "#": (lambda f: f.read(32), lambda f, v: f.write(v[:32])),
    "@": (lambda f: f.read(16), lambda f, v: f.write(v[:16])),
}

BITCOIN_STREAMER = Streamer()
BITCOIN_STREAMER.register_array_count_parse(parse_bc_int)
BITCOIN_STREAMER.register_functions(STREAMER_FUNCTIONS.items())

parse_struct = BITCOIN_STREAMER.parse_struct
parse_as_dict = BITCOIN_STREAMER.parse_as_dict
stream_struct = BITCOIN_STREAMER.stream_struct
pack_struct = BITCOIN_STREAMER.pack_struct

########NEW FILE########
__FILENAME__ = streamer

import io


class Streamer(object):
    def __init__(self):
        self.parse_lookup = {}
        self.stream_lookup = {}

    def register_functions(self, lookup):
        for c, v in lookup:
            parse_f, stream_f = v
            self.parse_lookup[c] = parse_f
            self.stream_lookup[c] = stream_f

    def register_array_count_parse(self, array_count_parse_f):
        self.array_count_parse_f = array_count_parse_f

    def parse_struct(self, fmt, f):
        l = []
        i = 0
        while i < len(fmt):
            c = fmt[i]
            if c == "[":
                end = fmt.find("]", i)
                if end < 0:
                    raise ValueError("no closing ] character")
                subfmt = fmt[i+1:end]
                count = self.array_count_parse_f(f)
                array = []
                for j in range(count):
                    if len(subfmt) == 1:
                        array.append(self.parse_struct(subfmt, f)[0])
                    else:
                        array.append(self.parse_struct(subfmt, f))
                l.append(tuple(array))
                i = end
            else:
                l.append(self.parse_lookup[c](f))
            i += 1
        return tuple(l)

    def parse_as_dict(self, attribute_list, pack_list, f):
        return dict(list(zip(attribute_list, self.parse_struct(pack_list, f))))

    def stream_struct(self, fmt, f, *args):
        for c, v in zip(fmt, args):
            self.stream_lookup[c](f, v)

    def unpack_struct(self, fmt, b):
        return self.parse_struct(fmt, io.BytesIO(b))

    def pack_struct(self, fmt, *args):
        b = io.BytesIO()
        self.stream_struct(fmt, b, *args)
        return b.getvalue()

########NEW FILE########
__FILENAME__ = bitcoind
from pycoin.serialize import b2h, b2h_rev

try:
    from bitcoinrpc.authproxy import AuthServiceProxy
except ImportError:
    print("This script depends upon python-bitcoinrpc.")
    print("pip install -e git+https://github.com/jgarzik/python-bitcoinrpc#egg=python_bitcoinrpc-master")
    raise


def unspent_to_bitcoind_dict(tx_in, tx_out):
    return dict(
        txid=b2h_rev(tx_in.previous_hash),
        vout=tx_in.previous_index,
        scriptPubKey=b2h(tx_out.script)
    )


def bitcoind_agrees_on_transaction_validity(bitcoind_url, tx):
    connection = AuthServiceProxy(bitcoind_url)
    tx.check_unspents()
    unknown_tx_outs = [unspent_to_bitcoind_dict(tx_in, tx_out)
                       for tx_in, tx_out in zip(tx.txs_in, tx.unspents)]
    signed = connection.signrawtransaction(tx.as_hex(), unknown_tx_outs, [])
    is_ok = [tx.is_signature_ok(idx) for idx in range(len(tx.txs_in))]
    return all(is_ok) == signed.get("complete")

########NEW FILE########
__FILENAME__ = biteasy
import json

try:
    from urllib2 import urlopen, Request
except ImportError:
    from urllib.request import urlopen, Request

from pycoin.serialize import h2b_rev
from pycoin.tx import Spendable
from pycoin.tx.script import tools


def spendables_for_address(bitcoin_address):
    """
    Return a list of Spendable objects for the
    given bitcoin address.
    """
    URL = "https://api.biteasy.com/blockchain/v1/addresses/%s/unspent-outputs" % bitcoin_address
    r = Request(URL,
                headers={"content-type": "application/json", "accept": "*/*", "User-Agent": "curl/7.29.0"})
    d = urlopen(r).read()
    json_response = json.loads(d.decode("utf8"))
    spendables = []
    for tx_out_info in json_response.get("data", {}).get("outputs"):
        if tx_out_info.get("to_address") == bitcoin_address:
            coin_value = tx_out_info["value"]
            script = tools.compile(tx_out_info.get("script_pub_key"))
            previous_hash = h2b_rev(tx_out_info.get("transaction_hash"))
            previous_index = tx_out_info.get("transaction_index")
            spendables.append(Spendable(coin_value, script, previous_hash, previous_index))
    return spendables

########NEW FILE########
__FILENAME__ = blockchain_info
import binascii
import io
import json

try:
    from urllib2 import urlopen, HTTPError
    from urllib import urlencode
except ImportError:
    from urllib.request import urlopen, HTTPError
    from urllib.parse import urlencode

from pycoin.tx import Spendable


def payments_for_address(bitcoin_address):
    "return an array of (TX ids, net_payment)"
    URL = "https://blockchain.info/address/%s?format=json" % bitcoin_address
    d = urlopen(URL).read()
    json_response = json.loads(d.decode("utf8"))
    response = []
    for tx in json_response.get("txs", []):
        total_out = 0
        for tx_out in tx.get("out", []):
            if tx_out.get("addr") == bitcoin_address:
                total_out += tx_out.get("value", 0)
        if total_out > 0:
            response.append((tx.get("hash"), total_out))
    return response


def spendables_for_address(bitcoin_address):
    """
    Return a list of Spendable objects for the
    given bitcoin address.
    """
    URL = "http://blockchain.info/unspent?active=%s" % bitcoin_address
    r = json.loads(urlopen(URL).read().decode("utf8"))
    spendables = []
    for u in r["unspent_outputs"]:
        coin_value = u["value"]
        script = binascii.unhexlify(u["script"])
        previous_hash = binascii.unhexlify(u["tx_hash"])
        previous_index = u["tx_output_n"]
        spendables.append(Spendable(coin_value, script, previous_hash, previous_index))
    return spendables


def send_tx(tx):
    s = io.BytesIO()
    tx.stream(s)
    tx_as_hex = binascii.hexlify(s.getvalue()).decode("utf8")
    data = urlencode(dict(tx=tx_as_hex)).encode("utf8")
    URL = "http://blockchain.info/pushtx"
    try:
        d = urlopen(URL, data=data).read()
        return d
    except HTTPError as ex:
        d = ex.read()
        print(ex)

########NEW FILE########
__FILENAME__ = blockexplorer
import binascii
import json
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

from pycoin.convention import btc_to_satoshi
from pycoin.serialize import b2h_rev, h2b_rev
from pycoin.tx.Tx import Tx, TxIn, TxOut
from pycoin.tx.script import tools


def get_json_for_hash(the_hash):
    d = urlopen("http://blockexplorer.com/rawtx/%s" % b2h_rev(the_hash)).read()
    return json.loads(d.decode("utf8"))


def get_tx(tx_hash):
    """
    Get a Tx by its hash.
    """
    # TODO: fix this
    j = get_json_for_hash(tx_hash)
    txs_in = []
    for j_in in j.get("in"):
        if j_in.get("coinbase"):
            txs_in.append(TxIn.coinbase_tx_in(binascii.unhexlify(j_in["coinbase"])))
        else:
            txs_in.append(TxIn(
                h2b_rev(j_in["prev_out"]["hash"]),
                int(j_in["prev_out"]["n"]),
                tools.compile(j_in["scriptSig"])))

    txs_out = []
    for j_out in j.get("out"):
        txs_out.append(TxOut(int(btc_to_satoshi(j_out["value"])), tools.compile(j_out["scriptPubKey"])))

    tx = Tx(int(j["ver"]), txs_in, txs_out, int(j["lock_time"]))
    assert tx.hash() == tx_hash
    return tx

########NEW FILE########
__FILENAME__ = blockr_io
import binascii
import io
import json

try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen

from pycoin.convention import btc_to_satoshi
from pycoin.tx import Tx, Spendable
from pycoin.serialize import b2h_rev, h2b_rev


def spendables_for_address(bitcoin_address):
    """
    Return a list of Spendable objects for the
    given bitcoin address.
    """
    URL = "http://btc.blockr.io/api/v1/address/unspent/%s" % bitcoin_address
    r = json.loads(urlopen(URL).read().decode("utf8"))
    spendables = []
    for u in r.get("data", {}).get("unspent", []):
        coin_value = btc_to_satoshi(u.get("amount"))
        script = binascii.unhexlify(u.get("script"))
        previous_hash = h2b_rev(u.get("tx"))
        previous_index = u.get("n")
        spendables.append(Spendable(coin_value, script, previous_hash, previous_index))
    return spendables


def get_tx(tx_hash):
    """
    Get a Tx by its hash.
    """
    URL = "http://btc.blockr.io/api/v1/tx/raw/%s" % b2h_rev(tx_hash)
    r = json.loads(urlopen(URL).read().decode("utf8"))
    tx = Tx.parse(io.BytesIO(binascii.unhexlify(r.get("data").get("tx").get("hex"))))
    return tx

########NEW FILE########
__FILENAME__ = env
import os


def service_providers_for_env():
    return os.getenv("PYCOIN_SERVICE_PROVIDERS", '').split(":")


def main_cache_dir():
    p = os.getenv("PYCOIN_CACHE_DIR")
    if p:
        p = os.path.expanduser(p)
    return p


def tx_read_cache_dirs():
    return [p for p in os.getenv("PYCOIN_TX_DB_DIRS", "").split(":") if len(p) > 0]


def tx_writable_cache_dir():
    p = main_cache_dir()
    if p:
        p = os.path.join(main_cache_dir(), "txs")
    return p

########NEW FILE########
__FILENAME__ = providers
import importlib
import random

from .env import main_cache_dir, service_providers_for_env, tx_read_cache_dirs, tx_writable_cache_dir
from .tx_db import TxDb


SERVICE_PROVIDERS = ["BLOCKCHAIN_INFO", "BLOCKEXPLORER", "BLOCKR_IO", "BITEASY"]


class NoServicesSpecifiedError(Exception):
    pass


def service_provider_methods(method_name, service_providers):
    modules = [importlib.import_module("pycoin.services.%s" % p.lower())
               for p in service_providers if p in SERVICE_PROVIDERS]
    methods = [getattr(m, method_name, None) for m in modules]
    methods = [m for m in methods if m]
    return methods


def spendables_for_address(bitcoin_address, format=None):
    """
    Return a list of Spendable objects for the
    given bitcoin address.

    Set format to "text" or "dict" to transform return value
    from an object to a string or dict.

    This is intended to be a convenience function. There is no way to know that
    the list returned is a complete list of spendables for the address in question.

    You can verify that they really do come from the existing transaction
    by calling tx_utils.validate_unspents.
    """
    if format:
        method = "as_%s" % format
    for m in service_provider_methods("spendables_for_address", service_providers_for_env()):
        try:
            spendables = m(bitcoin_address)
            if format:
                spendables = [getattr(s, method)() for s in spendables]
            return spendables
        except Exception:
            pass
    return []


def get_tx_db():
    lookup_methods = service_provider_methods("get_tx", service_providers_for_env())
    read_cache_dirs = tx_read_cache_dirs()
    writable_cache_dir = tx_writable_cache_dir()
    return TxDb(lookup_methods=lookup_methods, read_only_paths=read_cache_dirs,
                writable_cache_path=writable_cache_dir)


def message_about_tx_cache_env():
    if main_cache_dir() is None:
        return "consider setting environment variable PYCOIN_CACHE_DIR=~/.pycoin_cache to"\
               " cache transactions fetched via web services"


def all_providers_message(method):
    if len(service_provider_methods(method, service_providers_for_env())) == 0:
        l = list(SERVICE_PROVIDERS)
        random.shuffle(l)
        return "no service providers found for %s; consider setting environment variable "\
            "PYCOIN_SERVICE_PROVIDERS=%s" % (method, ':'.join(l))


def message_about_spendables_for_address_env():
    return all_providers_message("spendables_for_address")


def message_about_get_tx_env():
    return all_providers_message("get_tx")

########NEW FILE########
__FILENAME__ = tx_db

import os.path

from pycoin.serialize import b2h_rev
from pycoin.tx.Tx import Tx


class TxDb(object):
    """
    This object can be used in many places that expect a dict.
    """
    def __init__(self, lookup_methods=[], read_only_paths=[], writable_cache_path=None):
        self.lookup_methods = lookup_methods
        self.read_only_paths = read_only_paths
        if writable_cache_path:
            self.read_only_paths.append(writable_cache_path)
        self.writable_cache_path = writable_cache_path
        if self.writable_cache_path and not os.path.exists(self.writable_cache_path):
            os.makedirs(self.writable_cache_path)

    def paths_for_hash(self, hash):
        name = b2h_rev(hash)
        for base_dir in self.read_only_paths:
            p = os.path.join(base_dir, "%s_tx.bin" % name)
            if os.path.exists(p):
                yield p

    def put(self, tx):
        name = b2h_rev(tx.hash())
        if self.writable_cache_path:
            try:
                path = os.path.join(self.writable_cache_path, "%s_tx.bin" % name)
                with open(path, "wb") as f:
                    tx.stream(f)
            except IOError:
                pass

    def get(self, key):
        for path in self.paths_for_hash(key):
            try:
                tx = Tx.parse(open(path, "rb"))
                if tx and tx.hash() == key:
                    return tx
            except IOError:
                pass
        for method in self.lookup_methods:
            try:
                tx = method(key)
                if tx and tx.hash() == key:
                    self.put(tx)
                    return tx
            except Exception:
                pass
        return None

    def __getitem__(self, key):
        raise NotImplemented

    def __setitem__(self, key, val):
        if val.hash() != key:
            raise ValueError("bad key %s for %s" % (b2h_rev(key), val))
        self.put(val)

########NEW FILE########
__FILENAME__ = bip32_test
#!/usr/bin/env python

import unittest

from pycoin.key import bip32
from pycoin.serialize import h2b

class Bip0032TestCase(unittest.TestCase):

    def test_vector_1(self):
        master = bip32.Wallet.from_master_secret(h2b("000102030405060708090a0b0c0d0e0f"))
        self.assertEqual(master.wallet_key(as_private=True), "xprv9s21ZrQH143K3QTDL4LXw2F7HEK3wJUD2nW2nRk4stbPy6cq3jPPqjiChkVvvNKmPGJxWUtg6LnF5kejMRNNU3TGtRBeJgk33yuGBxrMPHi")
        self.assertEqual(master.bitcoin_address(), "15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma")
        self.assertEqual(master.wif(), "L52XzL2cMkHxqxBXRyEpnPQZGUs3uKiL3R11XbAdHigRzDozKZeW")

        self.assertEqual(master.wallet_key(), "xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjqJoCu1Rupje8YtGqsefD265TMg7usUDFdp6W1EGMcet8")

        m0p = master.subkey(is_hardened=True)
        self.assertEqual(m0p.wallet_key(), "xpub68Gmy5EdvgibQVfPdqkBBCHxA5htiqg55crXYuXoQRKfDBFA1WEjWgP6LHhwBZeNK1VTsfTFUHCdrfp1bgwQ9xv5ski8PX9rL2dZXvgGDnw")
        self.assertEqual(m0p.wallet_key(as_private=True), "xprv9uHRZZhk6KAJC1avXpDAp4MDc3sQKNxDiPvvkX8Br5ngLNv1TxvUxt4cV1rGL5hj6KCesnDYUhd7oWgT11eZG7XnxHrnYeSvkzY7d2bhkJ7")
        self.assertEqual(master.subkey_for_path("0p").wallet_key(), m0p.wallet_key())

        pub_mp0 = master.subkey(is_hardened=True, as_private=False)
        self.assertEqual(pub_mp0.wallet_key(), m0p.wallet_key())
        self.assertEqual(master.subkey_for_path("0p.pub").wallet_key(), pub_mp0.wallet_key())

        m0p1 = m0p.subkey(i=1)
        self.assertEqual(m0p1.wallet_key(), "xpub6ASuArnXKPbfEwhqN6e3mwBcDTgzisQN1wXN9BJcM47sSikHjJf3UFHKkNAWbWMiGj7Wf5uMash7SyYq527Hqck2AxYysAA7xmALppuCkwQ")
        self.assertEqual(m0p1.wallet_key(as_private=True), "xprv9wTYmMFdV23N2TdNG573QoEsfRrWKQgWeibmLntzniatZvR9BmLnvSxqu53Kw1UmYPxLgboyZQaXwTCg8MSY3H2EU4pWcQDnRnrVA1xe8fs")
        self.assertEqual(master.subkey_for_path("0p/1").wallet_key(), m0p1.wallet_key())

        pub_m0p1 = m0p.subkey(i=1, as_private=False)
        self.assertEqual(pub_m0p1.wallet_key(), m0p1.wallet_key())
        self.assertEqual(master.subkey_for_path("0p/1.pub").wallet_key(), pub_m0p1.wallet_key())

        m0p1_1_2p = m0p1.subkey(i=2, is_hardened=True)
        self.assertEqual(m0p1_1_2p.wallet_key(), "xpub6D4BDPcP2GT577Vvch3R8wDkScZWzQzMMUm3PWbmWvVJrZwQY4VUNgqFJPMM3No2dFDFGTsxxpG5uJh7n7epu4trkrX7x7DogT5Uv6fcLW5")
        self.assertEqual(m0p1_1_2p.wallet_key(as_private=True), "xprv9z4pot5VBttmtdRTWfWQmoH1taj2axGVzFqSb8C9xaxKymcFzXBDptWmT7FwuEzG3ryjH4ktypQSAewRiNMjANTtpgP4mLTj34bhnZX7UiM")
        self.assertEqual(master.subkey_for_path("0p/1/2p").wallet_key(), m0p1_1_2p.wallet_key())

        pub_m0p1_1_2p = m0p1.subkey(i=2, as_private=False, is_hardened=True)
        self.assertEqual(pub_m0p1_1_2p.wallet_key(), m0p1_1_2p.wallet_key())
        self.assertEqual(master.subkey_for_path("0p/1/2p.pub").wallet_key(), pub_m0p1_1_2p.wallet_key())

        m0p1_1_2p_2 = m0p1_1_2p.subkey(i=2)
        self.assertEqual(m0p1_1_2p_2.wallet_key(), "xpub6FHa3pjLCk84BayeJxFW2SP4XRrFd1JYnxeLeU8EqN3vDfZmbqBqaGJAyiLjTAwm6ZLRQUMv1ZACTj37sR62cfN7fe5JnJ7dh8zL4fiyLHV")
        self.assertEqual(m0p1_1_2p_2.wallet_key(as_private=True), "xprvA2JDeKCSNNZky6uBCviVfJSKyQ1mDYahRjijr5idH2WwLsEd4Hsb2Tyh8RfQMuPh7f7RtyzTtdrbdqqsunu5Mm3wDvUAKRHSC34sJ7in334")
        self.assertEqual(master.subkey_for_path("0p/1/2p/2").wallet_key(), m0p1_1_2p_2.wallet_key())

        pub_m0p1_1_2p_2 = m0p1_1_2p.subkey(i=2, as_private=False)
        self.assertEqual(pub_m0p1_1_2p_2.wallet_key(), m0p1_1_2p_2.wallet_key())
        self.assertEqual(master.subkey_for_path("0p/1/2p/2.pub").wallet_key(), pub_m0p1_1_2p_2.wallet_key())

        m0p1_1_2p_2_1000000000 = m0p1_1_2p_2.subkey(i=1000000000)
        self.assertEqual(m0p1_1_2p_2_1000000000.wallet_key(), "xpub6H1LXWLaKsWFhvm6RVpEL9P4KfRZSW7abD2ttkWP3SSQvnyA8FSVqNTEcYFgJS2UaFcxupHiYkro49S8yGasTvXEYBVPamhGW6cFJodrTHy")
        self.assertEqual(m0p1_1_2p_2_1000000000.wallet_key(as_private=True), "xprvA41z7zogVVwxVSgdKUHDy1SKmdb533PjDz7J6N6mV6uS3ze1ai8FHa8kmHScGpWmj4WggLyQjgPie1rFSruoUihUZREPSL39UNdE3BBDu76")
        self.assertEqual(master.subkey_for_path("0p/1/2p/2/1000000000").wallet_key(), m0p1_1_2p_2_1000000000.wallet_key())

        pub_m0p1_1_2p_2_1000000000 = m0p1_1_2p_2.subkey(i=1000000000, as_private=False)
        self.assertEqual(pub_m0p1_1_2p_2_1000000000.wallet_key(), m0p1_1_2p_2_1000000000.wallet_key())
        self.assertEqual(master.subkey_for_path("0p/1/2p/2/1000000000.pub").wallet_key(), pub_m0p1_1_2p_2_1000000000.wallet_key())


    def test_vector_2(self):
        master = bip32.Wallet.from_master_secret(h2b("fffcf9f6f3f0edeae7e4e1dedbd8d5d2cfccc9c6c3c0bdbab7b4b1aeaba8a5a29f9c999693908d8a8784817e7b7875726f6c696663605d5a5754514e4b484542"))
        self.assertEqual(master.wallet_key(as_private=True), "xprv9s21ZrQH143K31xYSDQpPDxsXRTUcvj2iNHm5NUtrGiGG5e2DtALGdso3pGz6ssrdK4PFmM8NSpSBHNqPqm55Qn3LqFtT2emdEXVYsCzC2U")

        self.assertEqual(master.wallet_key(), "xpub661MyMwAqRbcFW31YEwpkMuc5THy2PSt5bDMsktWQcFF8syAmRUapSCGu8ED9W6oDMSgv6Zz8idoc4a6mr8BDzTJY47LJhkJ8UB7WEGuduB")

        m0 = master.subkey()
        self.assertEqual(m0.wallet_key(), "xpub69H7F5d8KSRgmmdJg2KhpAK8SR3DjMwAdkxj3ZuxV27CprR9LgpeyGmXUbC6wb7ERfvrnKZjXoUmmDznezpbZb7ap6r1D3tgFxHmwMkQTPH")
        self.assertEqual(m0.wallet_key(as_private=True), "xprv9vHkqa6EV4sPZHYqZznhT2NPtPCjKuDKGY38FBWLvgaDx45zo9WQRUT3dKYnjwih2yJD9mkrocEZXo1ex8G81dwSM1fwqWpWkeS3v86pgKt")
        pub_m0 = master.subkey(as_private=False)
        self.assertEqual(pub_m0.wallet_key(), m0.wallet_key())

        m0_2147483647p = m0.subkey(i=2147483647, is_hardened=True)
        self.assertEqual(m0_2147483647p.wallet_key(), "xpub6ASAVgeehLbnwdqV6UKMHVzgqAG8Gr6riv3Fxxpj8ksbH9ebxaEyBLZ85ySDhKiLDBrQSARLq1uNRts8RuJiHjaDMBU4Zn9h8LZNnBC5y4a")
        self.assertEqual(m0_2147483647p.wallet_key(as_private=True), "xprv9wSp6B7kry3Vj9m1zSnLvN3xH8RdsPP1Mh7fAaR7aRLcQMKTR2vidYEeEg2mUCTAwCd6vnxVrcjfy2kRgVsFawNzmjuHc2YmYRmagcEPdU9")
        pub_m0_2147483647p = m0.subkey(i=2147483647, is_hardened=True, as_private=False)
        self.assertEqual(pub_m0_2147483647p.wallet_key(), m0_2147483647p.wallet_key())

        m0_2147483647p_1 = m0_2147483647p.subkey(i=1)
        self.assertEqual(m0_2147483647p_1.wallet_key(), "xpub6DF8uhdarytz3FWdA8TvFSvvAh8dP3283MY7p2V4SeE2wyWmG5mg5EwVvmdMVCQcoNJxGoWaU9DCWh89LojfZ537wTfunKau47EL2dhHKon")
        self.assertEqual(m0_2147483647p_1.wallet_key(as_private=True), "xprv9zFnWC6h2cLgpmSA46vutJzBcfJ8yaJGg8cX1e5StJh45BBciYTRXSd25UEPVuesF9yog62tGAQtHjXajPPdbRCHuWS6T8XA2ECKADdw4Ef")
        pub_m0_2147483647p_1 = m0_2147483647p.subkey(i=1, as_private=False)
        self.assertEqual(pub_m0_2147483647p_1.wallet_key(), m0_2147483647p_1.wallet_key())
        pub_m0_2147483647p_1 = pub_m0_2147483647p.subkey(i=1, as_private=False)
        self.assertEqual(pub_m0_2147483647p_1.wallet_key(), m0_2147483647p_1.wallet_key())

        m0_2147483647p_1_2147483646p = m0_2147483647p_1.subkey(i=2147483646, is_hardened=True)
        self.assertEqual(m0_2147483647p_1_2147483646p.wallet_key(), "xpub6ERApfZwUNrhLCkDtcHTcxd75RbzS1ed54G1LkBUHQVHQKqhMkhgbmJbZRkrgZw4koxb5JaHWkY4ALHY2grBGRjaDMzQLcgJvLJuZZvRcEL")
        self.assertEqual(m0_2147483647p_1_2147483646p.wallet_key(as_private=True), "xprvA1RpRA33e1JQ7ifknakTFpgNXPmW2YvmhqLQYMmrj4xJXXWYpDPS3xz7iAxn8L39njGVyuoseXzU6rcxFLJ8HFsTjSyQbLYnMpCqE2VbFWc")
        pub_m0_2147483647p_1_2147483646p = m0_2147483647p_1.subkey(i=2147483646, as_private=False, is_hardened=True)
        self.assertEqual(pub_m0_2147483647p_1_2147483646p.wallet_key(), m0_2147483647p_1_2147483646p.wallet_key())

        m0_2147483647p_1_2147483646p_2 = m0_2147483647p_1_2147483646p.subkey(i=2)
        self.assertEqual(m0_2147483647p_1_2147483646p_2.wif(), "L3WAYNAZPxx1fr7KCz7GN9nD5qMBnNiqEJNJMU1z9MMaannAt4aK")
        self.assertEqual(m0_2147483647p_1_2147483646p_2.wallet_key(), "xpub6FnCn6nSzZAw5Tw7cgR9bi15UV96gLZhjDstkXXxvCLsUXBGXPdSnLFbdpq8p9HmGsApME5hQTZ3emM2rnY5agb9rXpVGyy3bdW6EEgAtqt")
        self.assertEqual(m0_2147483647p_1_2147483646p_2.wallet_key(as_private=True), "xprvA2nrNbFZABcdryreWet9Ea4LvTJcGsqrMzxHx98MMrotbir7yrKCEXw7nadnHM8Dq38EGfSh6dqA9QWTyefMLEcBYJUuekgW4BYPJcr9E7j")
        pub_m0_2147483647p_1_2147483646p_2 = m0_2147483647p_1_2147483646p.subkey(i=2, as_private=False)
        self.assertEqual(pub_m0_2147483647p_1_2147483646p_2.wallet_key(), m0_2147483647p_1_2147483646p_2.wallet_key())
        pub_m0_2147483647p_1_2147483646p_2 = pub_m0_2147483647p_1_2147483646p.subkey(i=2, as_private=False)
        self.assertEqual(pub_m0_2147483647p_1_2147483646p_2.wallet_key(), m0_2147483647p_1_2147483646p_2.wallet_key())
        self.assertEqual(master.subkey_for_path("0/2147483647p/1/2147483646p/2").wallet_key(), m0_2147483647p_1_2147483646p_2.wallet_key())
        self.assertEqual(master.subkey_for_path("0/2147483647p/1/2147483646p/2.pub").wallet_key(), pub_m0_2147483647p_1_2147483646p_2.wallet_key())

    def test_testnet(self):
        # WARNING: these values have not been verified independently. TODO: do so
        master = bip32.Wallet.from_master_secret(h2b("000102030405060708090a0b0c0d0e0f"), netcode='XTN')
        self.assertEqual(master.wallet_key(as_private=True), "tprv8ZgxMBicQKsPeDgjzdC36fs6bMjGApWDNLR9erAXMs5skhMv36j9MV5ecvfavji5khqjWaWSFhN3YcCUUdiKH6isR4Pwy3U5y5egddBr16m")
        self.assertEqual(master.bitcoin_address(), "mkHGce7dctSxHgaWSSbmmrRWsZfzz7MxMk")
        self.assertEqual(master.wif(), "cVPXTF2TnozE1PenpP3x9huctiATZmp27T9Ue1d8nqLSExoPwfN5")

    def test_streams(self):
        m0 = bip32.Wallet.from_master_secret("foo bar baz".encode("utf8"))
        pm0 = m0.public_copy()
        self.assertEqual(m0.wallet_key(), pm0.wallet_key())
        m1 = m0.subkey()
        pm1 = pm0.subkey()
        for i in range(4):
            m = m1.subkey(i=i)
            pm = pm1.subkey(i=i)
            self.assertEqual(m.wallet_key(), pm.wallet_key())
            self.assertEqual(m.bitcoin_address(), pm.bitcoin_address())
            m2 = bip32.Wallet.from_wallet_key(m.wallet_key(as_private=True))
            m3 = m2.public_copy()
            self.assertEqual(m.wallet_key(as_private=True), m2.wallet_key(as_private=True))
            self.assertEqual(m.wallet_key(), m3.wallet_key())
            print(m.wallet_key(as_private=True))
            for j in range(2):
                k = m.subkey(i=j)
                k2 = bip32.Wallet.from_wallet_key(k.wallet_key(as_private=True))
                k3 = bip32.Wallet.from_wallet_key(k.wallet_key())
                k4 = k.public_copy()
                self.assertEqual(k.wallet_key(as_private=True), k2.wallet_key(as_private=True))
                self.assertEqual(k.wallet_key(), k2.wallet_key())
                self.assertEqual(k.wallet_key(), k3.wallet_key())
                self.assertEqual(k.wallet_key(), k4.wallet_key())
                print("   %s %s" % (k.bitcoin_address(), k.wif()))

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = build_tx_test
#!/usr/bin/env python

import io
import unittest

from pycoin.block import Block

from pycoin import ecdsa
from pycoin.encoding import public_pair_to_sec, public_pair_to_bitcoin_address, wif_to_secret_exponent
from pycoin.serialize import h2b

from pycoin.tx import Tx, SIGHASH_ALL
from pycoin.tx.TxIn import TxIn
from pycoin.tx.TxOut import TxOut, standard_tx_out_script
from pycoin.tx.script.solvers import build_hash160_lookup_db


# block 80971
block_80971_cs = h2b('00000000001126456C67A1F5F0FF0268F53B4F22E0531DC70C7B69746AF69DAC')
block_80971_data = h2b('01000000950A1631FB9FAC411DFB173487B9E18018B7C6F7147E78C06258410000000000A881352F97F14B'\
'F191B54915AE124E051B8FE6C3922C5082B34EAD503000FC34D891974CED66471B4016850A040100'\
'0000010000000000000000000000000000000000000000000000000000000000000000FFFFFFFF080'\
'4ED66471B02C301FFFFFFFF0100F2052A01000000434104CB6B6B4EADC96C7D08B21B29D0ADA5F29F937'\
'8978CABDB602B8B65DA08C8A93CAAB46F5ABD59889BAC704925942DD77A2116D10E0274CAD944C71D3D1A'\
'670570AC0000000001000000018C55ED829F16A4E43902940D3D33005264606D5F7D555B5F67EE4C033390'\
'C2EB010000008A47304402202D1BF606648EDCDB124C1254930852D99188E1231715031CBEAEA80CCFD2B39A'\
'02201FA9D6EE7A1763580E342474FC1AEF59B0468F98479953437F525063E25675DE014104A01F763CFBF5E518'\
'C628939158AF3DC0CAAC35C4BA7BC1CE8B7E634E8CDC44E15F0296B250282BD649BAA8398D199F2424FCDCD88'\
'D3A9ED186E4FD3CB9BF57CFFFFFFFFF02404B4C00000000001976A9148156FF75BEF24B35ACCE3C05289A241'\
'1E1B0E57988AC00AA38DF010000001976A914BC7E692A5FFE95A596712F5ED83393B3002E452E88AC000000'\
'0001000000019C97AFDF6C9A31FFA86D71EA79A079001E2B59EE408FD418498219400639AC0A010000008B4'\
'830450220363CFFAE09599397B21E6D8A8073FB1DFBE06B6ACDD0F2F7D3FEA86CA9C3F605022100FA255A6ED'\
'23FD825C759EF1A885A31CAD0989606CA8A3A16657D50FE3CEF5828014104FF444BAC08308B9EC97F56A652A'\
'D8866E0BA804DA97868909999566CB377F4A2C8F1000E83B496868F3A282E1A34DF78565B65C15C3FA21A076'\
'3FD81A3DFBBB6FFFFFFFF02C05EECDE010000001976A914588554E6CC64E7343D77117DA7E01357A6111B798'\
'8AC404B4C00000000001976A914CA6EB218592F289999F13916EE32829AD587DBC588AC00000000010000000'\
'1BEF5C9225CB9FE3DEF929423FA36AAD9980B9D6F8F3070001ACF3A5FB389A69F000000004A493046022100F'\
'B23B1E2F2FB8B96E04D220D385346290A9349F89BBBC5C225D5A56D931F8A8E022100F298EB28294B90C1BAF'\
'319DAB713E7CA721AAADD8FCC15F849DE7B0A6CF5412101FFFFFFFF0100F2052A010000001976A9146DDEA80'\
'71439951115469D0D2E2B80ECBCDD48DB88AC00000000');

block_80971 = Block.parse(io.BytesIO(block_80971_data))

COINBASE_PUB_KEY_FROM_80971 = h2b("04cb6b6b4eadc96c7d08b21b29d0ada5f29f9378978cabdb602b8b65da08c8a93caab46"\
    "f5abd59889bac704925942dd77a2116d10e0274cad944c71d3d1a670570")
COINBASE_BYTES_FROM_80971 = h2b("04ed66471b02c301")

def standard_tx(coins_from, coins_to):
    txs_in = []
    unspents = []
    for h, idx, tx_out in coins_from:
        txs_in.append(TxIn(h, idx))
        unspents.append(tx_out)

    txs_out = []
    for coin_value, bitcoin_address in coins_to:
        txs_out.append(TxOut(coin_value, standard_tx_out_script(bitcoin_address)))

    version, lock_time = 1, 0
    tx = Tx(version, txs_in, txs_out, lock_time)
    tx.set_unspents(unspents)
    return tx

class BuildTxTest(unittest.TestCase):

    def test_signature_hash(self):
        compressed = False
        exponent_2 = int("137f3276686959c82b454eea6eefc9ab1b9e45bd4636fb9320262e114e321da1", 16)
        bitcoin_address_2 = public_pair_to_bitcoin_address(
                ecdsa.public_pair_for_secret_exponent(ecdsa.generator_secp256k1, exponent_2),
                compressed=compressed)
        exponent = wif_to_secret_exponent("5JMys7YfK72cRVTrbwkq5paxU7vgkMypB55KyXEtN5uSnjV7K8Y")

        public_key_sec = public_pair_to_sec(ecdsa.public_pair_for_secret_exponent(ecdsa.generator_secp256k1, exponent), compressed=compressed)

        the_coinbase_tx = Tx.coinbase_tx(public_key_sec, int(50 * 1e8), COINBASE_BYTES_FROM_80971)
        coins_from = [(the_coinbase_tx.hash(), 0, the_coinbase_tx.txs_out[0])]
        coins_to = [(int(50 * 1e8), bitcoin_address_2)]
        unsigned_coinbase_spend_tx = standard_tx(coins_from, coins_to)

        tx_out_script_to_check = the_coinbase_tx.txs_out[0].script
        idx = 0
        actual_hash = unsigned_coinbase_spend_tx.signature_hash(tx_out_script_to_check, idx, hash_type=SIGHASH_ALL)
        self.assertEqual(actual_hash, 29819170155392455064899446505816569230970401928540834591675173488544269166940)

    def test_standard_tx_out(self):
        coin_value = 10
        recipient_bc_address = '1BcJRKjiwYQ3f37FQSpTYM7AfnXurMjezu'
        tx_out = standard_tx([], [(coin_value, recipient_bc_address)]).txs_out[0]
        s = str(tx_out)
        self.assertEqual('TxOut<0.0001 mbtc "OP_DUP OP_HASH160 745e5b81fd30ca1e90311b012badabaa4411ae1a OP_EQUALVERIFY OP_CHECKSIG">', s)

    def test_coinbase_tx(self):
        coinbase_bytes = h2b("04ed66471b02c301")
        tx = Tx.coinbase_tx(COINBASE_PUB_KEY_FROM_80971, int(50 * 1e8), COINBASE_BYTES_FROM_80971)
        s = io.BytesIO()
        tx.stream(s)
        tx1 = s.getvalue()
        s = io.BytesIO()
        block_80971.txs[0].stream(s)
        tx2 = s.getvalue()
        self.assertEqual(tx1, tx2)

    def test_tx_out_bitcoin_address(self):
        coinbase_bytes = h2b("04ed66471b02c301")
        tx = Tx.coinbase_tx(COINBASE_PUB_KEY_FROM_80971, int(50 * 1e8), COINBASE_BYTES_FROM_80971)
        self.assertEqual(tx.txs_out[0].bitcoin_address(), '1DmapcnrJNGeJB13fv9ngRFX1iRvR4zamn')

    def test_build_spends(self):
        # first, here is the tx database
        TX_DB = {}

        # create a coinbase Tx where we know the public & private key

        exponent = wif_to_secret_exponent("5JMys7YfK72cRVTrbwkq5paxU7vgkMypB55KyXEtN5uSnjV7K8Y")
        compressed = False

        public_key_sec = public_pair_to_sec(ecdsa.public_pair_for_secret_exponent(ecdsa.generator_secp256k1, exponent), compressed=compressed)

        the_coinbase_tx = Tx.coinbase_tx(public_key_sec, int(50 * 1e8), COINBASE_BYTES_FROM_80971)
        TX_DB[the_coinbase_tx.hash()] = the_coinbase_tx

        # now create a Tx that spends the coinbase

        compressed = False

        exponent_2 = int("137f3276686959c82b454eea6eefc9ab1b9e45bd4636fb9320262e114e321da1", 16)
        bitcoin_address_2 = public_pair_to_bitcoin_address(
                ecdsa.public_pair_for_secret_exponent(ecdsa.generator_secp256k1, exponent_2),
                compressed=compressed)

        self.assertEqual("12WivmEn8AUth6x6U8HuJuXHaJzDw3gHNZ", bitcoin_address_2)

        coins_from = [(the_coinbase_tx.hash(), 0, the_coinbase_tx.txs_out[0])]
        coins_to = [(int(50 * 1e8), bitcoin_address_2)]
        unsigned_coinbase_spend_tx = standard_tx(coins_from, coins_to)
        solver = build_hash160_lookup_db([exponent])

        coinbase_spend_tx = unsigned_coinbase_spend_tx.sign(solver)

        # now check that it validates
        self.assertEqual(coinbase_spend_tx.bad_signature_count(), 0)

        TX_DB[coinbase_spend_tx.hash()] = coinbase_spend_tx

        ## now try to respend from priv_key_2 to priv_key_3

        compressed = True

        exponent_3 = int("f8d39b8ecd0e1b6fee5a340519f239097569d7a403a50bb14fb2f04eff8db0ff", 16)
        bitcoin_address_3 = public_pair_to_bitcoin_address(
                ecdsa.public_pair_for_secret_exponent(ecdsa.generator_secp256k1, exponent_3),
                compressed=compressed)

        self.assertEqual("13zzEHPCH2WUZJzANymow3ZrxcZ8iFBrY5", bitcoin_address_3)

        coins_from = [(coinbase_spend_tx.hash(), 0, coinbase_spend_tx.txs_out[0])]
        unsigned_spend_tx = standard_tx(coins_from, [(int(50 * 1e8), bitcoin_address_3)])
        solver.update(build_hash160_lookup_db([exponent_2]))
        spend_tx = unsigned_spend_tx.sign(solver)

        # now check that it validates
        self.assertEqual(spend_tx.bad_signature_count(), 0)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ecdsa_test
#!/usr/bin/env python

import hashlib
import unittest

from pycoin.ecdsa import generator_secp256k1, sign, verify, public_pair_for_secret_exponent, intbytes
from pycoin.ecdsa.ecdsa import deterministic_generate_k

class ECDSATestCase(unittest.TestCase):

    def test_sign_verify(self):
        def do_test(secret_exponent, val_list):
            public_point = public_pair_for_secret_exponent(generator_secp256k1, secret_exponent)
            for v in val_list:
                signature = sign(generator_secp256k1, secret_exponent, v)
                r = verify(generator_secp256k1, public_point, v, signature)
                assert r == True
                signature = signature[0],signature[1]+1
                r = verify(generator_secp256k1, public_point, v, signature)
                assert r == False

        val_list = [100,20000,30000000,400000000000,50000000000000000,60000000000000000000000]

        do_test(0x1111111111111111111111111111111111111111111111111111111111111111, val_list)
        do_test(0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd, val_list)
        do_test(0x47f7616ea6f9b923076625b4488115de1ef1187f760e65f89eb6f4f7ff04b012, val_list)

    def test_deterministic_generate_k_A_1(self):
        """
        The example in http://tools.ietf.org/html/rfc6979#appendix-A.1
        """
        h = hashlib.sha256(b'sample').digest()
        val = intbytes.from_bytes(h)
        self.assertEqual(val, 0xAF2BDBE1AA9B6EC1E2ADE1D694F41FC71A831D0268E9891562113D8A62ADD1BF)
        q = 0x4000000000000000000020108A2E0CC0D99F8A5EF
        x = 0x09A4D6792295A7F730FC3F2B49CBC0F62E862272F
        k = deterministic_generate_k(q, x, val)
        self.assertEqual(k, 0x23AF4074C90A02B3FE61D286D5C87F425E6BDD81B)

    def test_deterministic_generate_k_A_2_1(self):
        """
        The example in https://tools.ietf.org/html/rfc6979#appendix-A.2.3
        """
        hashes_values = (
            (hashlib.sha1, 0x37D7CA00D2C7B0E5E412AC03BD44BA837FDD5B28CD3B0021),
            (hashlib.sha224, 0x4381526B3FC1E7128F202E194505592F01D5FF4C5AF015D8),
            (hashlib.sha256, 0x32B1B6D7D42A05CB449065727A84804FB1A3E34D8F261496),
            (hashlib.sha384, 0x4730005C4FCB01834C063A7B6760096DBE284B8252EF4311),
            (hashlib.sha512, 0xA2AC7AB055E4F20692D49209544C203A7D1F2C0BFBC75DB1),
            )
        q = 0xFFFFFFFFFFFFFFFFFFFFFFFF99DEF836146BC9B1B4D22831
        x = 0x6FAB034934E4C0FC9AE67F5B5659A9D7D1FEFD187EE09FD4
        for h, v in hashes_values:
            v_sample = intbytes.from_bytes(h(b'sample').digest())
            k = deterministic_generate_k(q, x, v_sample, h)
            self.assertEqual(k, v)

        hashes_values = (
            (hashlib.sha1, 0xD9CF9C3D3297D3260773A1DA7418DB5537AB8DD93DE7FA25),
            (hashlib.sha224, 0xF5DC805F76EF851800700CCE82E7B98D8911B7D510059FBE),
            (hashlib.sha256, 0x5C4CE89CF56D9E7C77C8585339B006B97B5F0680B4306C6C),
            (hashlib.sha384, 0x5AFEFB5D3393261B828DB6C91FBC68C230727B030C975693),
            (hashlib.sha512, 0x0758753A5254759C7CFBAD2E2D9B0792EEE44136C9480527),
            )
        for h, v in hashes_values:
            v_sample = intbytes.from_bytes(h(b'test').digest())
            k = deterministic_generate_k(q, x, v_sample, h)
            self.assertEqual(k, v)

    def test_deterministic_generate_k_A_2_5(self):
        """
        The example in https://tools.ietf.org/html/rfc6979#appendix-A.2.5
        """
        h = hashlib.sha256(b'sample').digest()
        val = intbytes.from_bytes(h)
        self.assertEqual(val, 0xAF2BDBE1AA9B6EC1E2ADE1D694F41FC71A831D0268E9891562113D8A62ADD1BF)
        generator_order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFF16A2E0B8F03E13DD29455C5C2A3D
        secret_exponent = 0xF220266E1105BFE3083E03EC7A3A654651F45E37167E88600BF257C1
        k = deterministic_generate_k(generator_order, secret_exponent, val)
        self.assertEqual(k, 0xAD3029E0278F80643DE33917CE6908C70A8FF50A411F06E41DEDFCDC)


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = encoding_test
#!/usr/bin/env python

import unittest

from pycoin import encoding
from pycoin.serialize import h2b

class EncodingTestCase(unittest.TestCase):

    def test_to_from_long(self):
        def do_test(as_int, prefix, as_rep, base):
            self.assertEqual((as_int, prefix), encoding.to_long(base, encoding.byte_to_int, as_rep))
            self.assertEqual(as_rep, encoding.from_long(as_int, prefix, base, lambda v:v))

        do_test(10000101, 2, h2b("00009896e5"), 256)
        do_test(10000101, 3, h2b("0000009896e5"), 256)
        do_test(1460765565493402645157733592332121663123460211377, 1, b'\0\xff\xde\xfeOHu\xcf\x11\x9f\xc3\xd8\xf4\xa0\x9a\xe3~\xc4\xccB\xb1', 256)

    def test_to_bytes_32(self):
        for i in range(256):
            v = encoding.to_bytes_32(i)
            self.assertEqual(v, b'\0' * 31 + bytes(bytearray([i])))
        for i in range(256,512):
            v = encoding.to_bytes_32(i)
            self.assertEqual(v, b'\0' * 30 + bytes(bytearray([1, i&0xff])))

    def test_to_from_base58(self):
        def do_test(as_text, as_bin):
            self.assertEqual(as_bin, encoding.a2b_base58(as_text))
            self.assertEqual(as_text, encoding.b2a_base58(as_bin))

        do_test("1abcdefghijkmnpqrst", b'\x00\x01\x93\\|\xf2*\xb9\xbe\x19b\xae\xe4\x8c{')
        do_test("1CASrvcpMMTa4dz4DmYtAqcegCtdkhjvdn", b'\x00zr\xb6\xfac\xde6\xc4\xab\xc6\nh\xb5-\x7f3\xe3\xd7\xcd>\xc4\xba\xbd9')
        do_test("1111111111111111aaaa11aa",
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00CnzQ)\x0b')
        do_test("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz",
            b'\x00\x01\x11\xd3\x8e_\xc9\x07\x1f\xfc\xd2\x0bJv<\xc9\xaeO%+\xb4\xe4\x8f\xd6j\x83^%*\xda\x93\xffH\rm\xd4=\xc6*d\x11U\xa5')

    def test_to_from_hashed_base58(self):
        def do_test(as_text, as_bin):
            self.assertEqual(as_text, encoding.b2a_hashed_base58(as_bin))
            self.assertEqual(as_bin, encoding.a2b_hashed_base58(as_text))
            self.assertTrue(encoding.is_hashed_base58_valid(as_text))
            bogus_text = as_text[:-1] + chr(1+ord(as_text[-1]))
            self.assertFalse(encoding.is_hashed_base58_valid(bogus_text))

        do_test("14nr3dMd4VwNpFhFECU1A6imi", b'\x00\x01\x93\\|\xf2*\xb9\xbe\x19b\xae\xe4\x8c{')
        do_test("1CASrvcpMMTa4dz4DmYtAqcegCtdkhjvdn", b'\x00zr\xb6\xfac\xde6\xc4\xab\xc6\nh\xb5-\x7f3\xe3\xd7\xcd>')
        do_test("11111111111111114njGbaozZJui9o",
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00CnzQ)\x0b')
        do_test("1mLRia5CbfDB9752zxvtrpnkigecaYWUSQNLJGECA8641ywusqomjhfdb6EM7bXGj1Gb",
            b'\x00\x01\x11\xd3\x8e_\xc9\x07\x1f\xfc\xd2\x0bJv<\xc9\xaeO%+\xb4\xe4\x8f\xd6j\x83^%*\xda\x93\xffH\rm\xd4=\xc6*d\x11U\xa5aaaa')

    def test_double_sha256(self):
        def do_test(blob, expected_hash):
            self.assertEqual(encoding.double_sha256(blob), expected_hash)

        do_test(b"This is a test",
            b'\xea\xc6I\xd41\xaa?\xc2\xd5t\x9d\x1aP!\xbb\xa7\x81.\xc8;\x8aY\xfa\x84\x0b\xffu\xc1\x7f\x8af\\')
        do_test(b"The quick brown fox jumps over the lazy dogs",
            b'\x8a5e\x88yz\x90\x1a\x11\x03\x17y\xd4xz\xd0E~\xb0\x82\xc5k\xd9\xb6W\x15z\xcf1\xba\xe6\xc4')
        do_test(b'\x74' * 10000,
            b'nMw6\xaa7<G\x18\xee\xf2\xb9E(\xfe\xd5u\x19\xa0\xbd\xc3\xa8\xf40\n\xee7,\xbe\xde\xa9\xa0')

    def test_hash160(self):
        def do_test(blob, expected_hash):
            self.assertEqual(encoding.hash160(blob), expected_hash)

        do_test(b"This is a test",
            b'\x18\xac\x98\xfa*$\x12\xdd\xb7]\xe6\x04Y\xb5*\xcd\x98\xf2\xd9r')
        do_test(b"The quick brown fox jumps over the lazy dogs",
            b'v\xc9\xd1\xf3\xaaR&UN G_\x91\x9a\xad\xd1t\xf7\xe9\xb7')
        do_test(b'\x74' * 10000,
            b'\xa9a\x07\x02\x96gt\x01\xa5~\xae\r\x96\xd1MZ\x88\n,A')

    def test_wif_to_from_secret_exponent(self):
        def do_test(as_secret_exponent, as_wif, is_compressed):
            self.assertEqual(as_wif, encoding.secret_exponent_to_wif(as_secret_exponent, compressed=is_compressed))
            se, comp = encoding.wif_to_tuple_of_secret_exponent_compressed(as_wif)
            self.assertEqual(se, as_secret_exponent)
            self.assertEqual(comp, is_compressed)
            self.assertTrue(encoding.is_valid_wif(as_wif))

        WIF_LIST = [
            "5HwoXVkHoRM8sL2KmNRS217n1g8mPPBomrY7yehCuXC1115WWsh",
            "5J5KUK3VXP8HUefNVYPxwxVRokScZdWXpu1Tj8LfaAXMqHzMmbk",
            "5JCqR8LhFLuS5yJRDiNVsus5bpkTjsqFswUoUbz8EorifYA4TwJ",
            "5JLMMwdtyJgahHwTwtM2osEjPu4Jv89yvyx9E5dauTC5Vs6EjBA",
            "5JTsJkw6hGTjJcaWg4KZjpcPByNA6NUhz2RUyZH3a6XSL7vAYmy",
            "5JbPFaEJREEsuwDZQEJ6fmz2z3g1GcoS34tpj2vWEjroARtCMBF",
            "5JiuCPXW9C22XFrc8QGdbjMgn7yrSs8A67NAUWZxuPC9ziUizQP",
            "5JrR9Cphs9oB8aVeraFAXgjLaCHhd7St99qWDzDRa2XWq3RVw7d",
            "5Jyw627ub7aKju8hakDhTe6zNGbYoMmcCCJqyTrtEfrsfLDreVt",
            "5K7T2qR7K5MUMDmkJvCEPbUeALuPyc6LFEnBiwWLuKCEVdBp8qV",
            "5KExyeiK338cxYQo36AmKYrHxRDF9rR4JHFXUR9oZxXbKue7gdL",
            "5KNUvU1WkzumZs3qmG9JFWDwkVX6L6jnMKisDtoGEbrxACzxk6T",
            "5KVzsHJiUxgvBBgtVS7qBTbbYZpwWM4WQNCCyNSiuFCJzYMxg8H",
            "5KdWp6bvCvU4nWKwDc6N7QyFLe8ngbPETQfYir6BZtXfpsnSrGS",
        ]
        SE_LIST = [int(c * 64, 16) for c in "123456789abcde"]
        for se, wif in zip(SE_LIST, WIF_LIST):
            do_test(se, wif, is_compressed=False)

    def test_public_pair_to_sec(self):
        def do_test(as_public_pair, as_sec, is_compressed, as_hash160_sec, as_bitcoin_address):
            self.assertEqual(encoding.sec_to_public_pair(as_sec), as_public_pair)
            self.assertEqual(encoding.public_pair_to_sec(as_public_pair, compressed=is_compressed), as_sec)
            self.assertEqual(encoding.is_sec_compressed(as_sec), is_compressed)
            self.assertEqual(encoding.public_pair_to_hash160_sec(as_public_pair, compressed=is_compressed),
                             as_hash160_sec)
            self.assertEqual(encoding.hash160_sec_to_bitcoin_address(as_hash160_sec), as_bitcoin_address)
            self.assertEqual(encoding.public_pair_to_bitcoin_address(as_public_pair, compressed=is_compressed), as_bitcoin_address)
            self.assertTrue(encoding.is_valid_bitcoin_address(as_bitcoin_address))
            bad_address = as_bitcoin_address[:17] + chr(ord(as_bitcoin_address[17]) + 1) + as_bitcoin_address[18:]
            self.assertFalse(encoding.is_valid_bitcoin_address(bad_address))

        SEC_TEST_DATA = [
            ((35826991941973211494003564265461426073026284918572421206325859877044495085994,
                25491041833361137486709012056693088297620945779048998614056404517283089805761),
                "034f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa",
                True,
                "fc7250a211deddc70ee5a2738de5f07817351cef",
                "1Q1pE5vPGEEMqRcVRMbtBK842Y6Pzo6nK9"
            ),
            ((31855367722742370537280679280108010854876607759940877706949385967087672770343,
                46659058944867745027460438812818578793297503278458148978085384795486842595210),
                "02466d7fcae563e5cb09a0d1870bb580344804617879a14949cf22285f1bae3f27",
                True,
                "531260aa2a199e228c537dfa42c82bea2c7c1f4d",
                "18aF6pYXKDSXjXHpidt2G6okdVdBr8zA7z"
            ),
            ((27341391395138457474971175971081207666803680341783085051101294443585438462385,
                26772005640425216814694594224987412261034377630410179754457174380653265224672),
                "023c72addb4fdf09af94f0c94d7fe92a386a7e70cf8a1d85916386bb2535c7b1b1",
                True,
                "3bc28d6d92d9073fb5e3adf481795eaf446bceed",
                "16Syw4SugWs4siKbK8cuxJXM2ukh2GKpRi"
            ),
            ((35826991941973211494003564265461426073026284918572421206325859877044495085994,
                25491041833361137486709012056693088297620945779048998614056404517283089805761),
                "044f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa"\
                  "385b6b1b8ead809ca67454d9683fcf2ba03456d6fe2c4abe2b07f0fbdbb2f1c1",
                False,
                "e4e517ee07984a4000cd7b00cbcb545911c541c4",
                "1MsHWS1BnwMc3tLE8G35UXsS58fKipzB7a"
            ),
            ((31855367722742370537280679280108010854876607759940877706949385967087672770343,
                46659058944867745027460438812818578793297503278458148978085384795486842595210),
                "04466d7fcae563e5cb09a0d1870bb580344804617879a14949cf22285f1bae3f27"\
                  "6728176c3c6431f8eeda4538dc37c865e2784f3a9e77d044f33e407797e1278a",
                False,
                "b256082b934fe782adbacaafeadfca64c52a5384",
                "1HFxLkPTtMZeo5mDpZn6CF9sh4h2ycknwr"
            ),
            ((27341391395138457474971175971081207666803680341783085051101294443585438462385,
                26772005640425216814694594224987412261034377630410179754457174380653265224672),
                "043c72addb4fdf09af94f0c94d7fe92a386a7e70cf8a1d85916386bb2535c7b1b1"\
                  "3b306b0fe085665d8fc1b28ae1676cd3ad6e08eaeda225fe38d0da4de55703e0",
                False,
                "edf6bbd7ba7aad222c2b28e6d8d5001178e3680c",
                "1NhEipumt9Pug6pwTqMNRXhBG84K39Ebbi"
            ),
        ]

        for public_pair, sec, compressed, hash160_sec, bitcoin_address in SEC_TEST_DATA:
            do_test(public_pair, h2b(sec), compressed, h2b(hash160_sec), bitcoin_address)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = key_test
#!/usr/bin/env python

import binascii
import unittest

from pycoin.key import Key

class KeyTest(unittest.TestCase):

    def test_translation(self):
        def do_test(exp_hex, wif, c_wif, public_pair_sec, c_public_pair_sec, address_b58, c_address_b58):

            secret_exponent = int(exp_hex, 16)
            sec = binascii.unhexlify(public_pair_sec)
            c_sec = binascii.unhexlify(c_public_pair_sec)

            keys_wif = [
                Key(secret_exponent=secret_exponent),
                Key.from_text(wif),
                Key.from_text(c_wif),
            ]

            key_sec = Key.from_sec(sec)
            key_sec_c = Key.from_sec(c_sec)
            keys_sec = [key_sec, key_sec_c]

            for key in keys_wif:
                self.assertEqual(key.secret_exponent(), secret_exponent)
                if key._prefer_uncompressed:
                    self.assertEqual(key.wif(), wif)
                else:
                    self.assertEqual(key.wif(), c_wif)
                self.assertEqual(key.wif(use_uncompressed=True), wif)
                self.assertEqual(key.wif(use_uncompressed=False), c_wif)

            for key in keys_wif + keys_sec:
                if key._prefer_uncompressed:
                    self.assertEqual(key.sec(), sec)
                else:
                    self.assertEqual(key.sec(), c_sec)
                self.assertEqual(key.sec(use_uncompressed=True), sec)
                self.assertEqual(key.sec(use_uncompressed=False), c_sec)
                if key._prefer_uncompressed:
                    self.assertEqual(key.address(), address_b58)
                else:
                    self.assertEqual(key.address(), c_address_b58)
                self.assertEqual(key.address(use_uncompressed=False), c_address_b58)
                self.assertEqual(key.address(use_uncompressed=True), address_b58)

            key_pub = Key.from_text(address_b58, is_compressed=False)
            key_pub_c = Key.from_text(c_address_b58, is_compressed=True)

            self.assertEqual(key_pub.address(), address_b58)
            self.assertEqual(key_pub.address(use_uncompressed=True), address_b58)
            self.assertEqual(key_pub.address(use_uncompressed=False), None)

            self.assertEqual(key_pub_c.address(), c_address_b58)
            self.assertEqual(key_pub_c.address(use_uncompressed=True), None)
            self.assertEqual(key_pub_c.address(use_uncompressed=False), c_address_b58)


        do_test("1111111111111111111111111111111111111111111111111111111111111111",
                 "5HwoXVkHoRM8sL2KmNRS217n1g8mPPBomrY7yehCuXC1115WWsh",
                 "KwntMbt59tTsj8xqpqYqRRWufyjGunvhSyeMo3NTYpFYzZbXJ5Hp",
                 "044f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa"\
                   "385b6b1b8ead809ca67454d9683fcf2ba03456d6fe2c4abe2b07f0fbdbb2f1c1",
                 "034f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa",
                 "1MsHWS1BnwMc3tLE8G35UXsS58fKipzB7a",
                 "1Q1pE5vPGEEMqRcVRMbtBK842Y6Pzo6nK9")

        do_test("dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
                    "5KVzsHJiUxgvBBgtVS7qBTbbYZpwWM4WQNCCyNSiuFCJzYMxg8H",
                    "L4ezQvyC6QoBhxB4GVs9fAPhUKtbaXYUn8YTqoeXwbevQq4U92vN",
                    "04ed83704c95d829046f1ac27806211132102c34e9ac7ffa1b71110658e5b9d1bd"\
                      "edc416f5cefc1db0625cd0c75de8192d2b592d7e3b00bcfb4a0e860d880fd1fc",
                    "02ed83704c95d829046f1ac27806211132102c34e9ac7ffa1b71110658e5b9d1bd",
                    "1JyMKvPHkrCQd8jQrqTR1rBsAd1VpRhTiE",
                    "1NKRhS7iYUGTaAfaR5z8BueAJesqaTyc4a")

        do_test("47f7616ea6f9b923076625b4488115de1ef1187f760e65f89eb6f4f7ff04b012",
                "5JMys7YfK72cRVTrbwkq5paxU7vgkMypB55KyXEtN5uSnjV7K8Y",
                "KydbzBtk6uc7M6dXwEgTEH2sphZxSPbmDSz6kUUHi4eUpSQuhEbq",
                "042596957532fc37e40486b910802ff45eeaa924548c0e1c080ef804e523ec3ed3"\
                  "ed0a9004acf927666eee18b7f5e8ad72ff100a3bb710a577256fd7ec81eb1cb3",
                "032596957532fc37e40486b910802ff45eeaa924548c0e1c080ef804e523ec3ed3",
                "1PM35qz2uwCDzcUJtiqDSudAaaLrWRw41L",
                "19ck9VKC6KjGxR9LJg4DNMRc45qFrJguvV")

        # in this case, the public_pair y value is less than 256**31, and so has a leading 00 byte.
        # This triggers a bug in the Python 2.7 version of to_bytes_32.
        do_test("ae2aaef5080b6e1704aab382a40a7c9957a40b4790f7df7faa04b14f4db56361",
                "5K8zSJ4zcV3UfkAKCFY5PomL6SRx2pYjaKfnAtMVh6zbhnAuPon",
                "L34GWeLdHcmw81W7JfAAPfQfH1F7u2s4v5QANdfTe1TEAYpjXoLL",
                "04f650fb572d1475950b63f5175c77e8b5ed9035a209d8fb5af5a04d6bc39b7323"\
                  "00186733fcfe3def4ace6feae8b82dd03cc31b7855307d33b0a039170f374962",
                "02f650fb572d1475950b63f5175c77e8b5ed9035a209d8fb5af5a04d6bc39b7323",
                "18fKPR8s1MQeckAsgya1sx6Z3WmFXd8wv8",
                "1DVJQzgnyCahXdoXdJ3tjGA3hrYVgKpvgK")

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = key_translation_test
#!/usr/bin/env python

import unittest

from pycoin.ecdsa import public_pair_for_secret_exponent, generator_secp256k1

from pycoin.encoding import bitcoin_address_to_hash160_sec, is_sec_compressed, public_pair_to_sec, secret_exponent_to_wif, public_pair_to_bitcoin_address, wif_to_tuple_of_secret_exponent_compressed, sec_to_public_pair, public_pair_to_hash160_sec
from pycoin.serialize import h2b

"""
http://sourceforge.net/mailarchive/forum.php?thread_name=CAPg%2BsBhDFCjAn1tRRQhaudtqwsh4vcVbxzm%2BAA2OuFxN71fwUA%40mail.gmail.com&forum_name=bitcoin-development
"""

class BuildTxTest(unittest.TestCase):

    def test_translation(self):
        def do_test(exp_hex, wif, c_wif, public_pair_sec, c_public_pair_sec, address_b58, c_address_b58):
            secret_exponent = int(exp_hex, 16)
            sec = h2b(public_pair_sec)
            c_sec = h2b(c_public_pair_sec)

            self.assertEqual(secret_exponent_to_wif(secret_exponent, compressed=False), wif)
            self.assertEqual(secret_exponent_to_wif(secret_exponent, compressed=True), c_wif)

            exponent, compressed = wif_to_tuple_of_secret_exponent_compressed(wif)
            self.assertEqual(exponent, secret_exponent)
            self.assertFalse(compressed)

            exponent, compressed = wif_to_tuple_of_secret_exponent_compressed(c_wif)
            self.assertEqual(exponent, secret_exponent)
            self.assertTrue(compressed)

            public_pair = public_pair_for_secret_exponent(generator_secp256k1, secret_exponent)

            pk_public_pair = sec_to_public_pair(sec)
            compressed = is_sec_compressed(sec)
            self.assertEqual(pk_public_pair, public_pair)
            self.assertFalse(is_sec_compressed(sec))
            self.assertEqual(public_pair_to_sec(pk_public_pair, compressed=False), sec)

            pk_public_pair = sec_to_public_pair(c_sec)
            compressed = is_sec_compressed(c_sec)
            self.assertEqual(pk_public_pair, public_pair)
            self.assertTrue(compressed)
            self.assertEqual(public_pair_to_sec(pk_public_pair, compressed=True), c_sec)

            bca = public_pair_to_bitcoin_address(pk_public_pair, compressed=True)
            self.assertEqual(bca, c_address_b58)

            self.assertEqual(bitcoin_address_to_hash160_sec(c_address_b58), public_pair_to_hash160_sec(pk_public_pair, compressed=True))

            bca = public_pair_to_bitcoin_address(pk_public_pair, compressed=False)
            self.assertEqual(bca, address_b58)

            self.assertEqual(bitcoin_address_to_hash160_sec(address_b58), public_pair_to_hash160_sec(pk_public_pair, compressed=False))


        do_test("1111111111111111111111111111111111111111111111111111111111111111",
                 "5HwoXVkHoRM8sL2KmNRS217n1g8mPPBomrY7yehCuXC1115WWsh",
                 "KwntMbt59tTsj8xqpqYqRRWufyjGunvhSyeMo3NTYpFYzZbXJ5Hp",
                 "044f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa"\
                   "385b6b1b8ead809ca67454d9683fcf2ba03456d6fe2c4abe2b07f0fbdbb2f1c1",
                 "034f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa",
                 "1MsHWS1BnwMc3tLE8G35UXsS58fKipzB7a",
                 "1Q1pE5vPGEEMqRcVRMbtBK842Y6Pzo6nK9")

        do_test("dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
                    "5KVzsHJiUxgvBBgtVS7qBTbbYZpwWM4WQNCCyNSiuFCJzYMxg8H",
                    "L4ezQvyC6QoBhxB4GVs9fAPhUKtbaXYUn8YTqoeXwbevQq4U92vN",
                    "04ed83704c95d829046f1ac27806211132102c34e9ac7ffa1b71110658e5b9d1bd"\
                      "edc416f5cefc1db0625cd0c75de8192d2b592d7e3b00bcfb4a0e860d880fd1fc",
                    "02ed83704c95d829046f1ac27806211132102c34e9ac7ffa1b71110658e5b9d1bd",
                    "1JyMKvPHkrCQd8jQrqTR1rBsAd1VpRhTiE",
                    "1NKRhS7iYUGTaAfaR5z8BueAJesqaTyc4a")

        do_test("47f7616ea6f9b923076625b4488115de1ef1187f760e65f89eb6f4f7ff04b012",
                "5JMys7YfK72cRVTrbwkq5paxU7vgkMypB55KyXEtN5uSnjV7K8Y",
                "KydbzBtk6uc7M6dXwEgTEH2sphZxSPbmDSz6kUUHi4eUpSQuhEbq",
                "042596957532fc37e40486b910802ff45eeaa924548c0e1c080ef804e523ec3ed3"\
                  "ed0a9004acf927666eee18b7f5e8ad72ff100a3bb710a577256fd7ec81eb1cb3",
                "032596957532fc37e40486b910802ff45eeaa924548c0e1c080ef804e523ec3ed3",
                "1PM35qz2uwCDzcUJtiqDSudAaaLrWRw41L",
                "19ck9VKC6KjGxR9LJg4DNMRc45qFrJguvV")

        # in this case, the public_pair y value is less than 256**31, and so has a leading 00 byte.
        # This triggers a bug in the Python 2.7 version of to_bytes_32.
        do_test("ae2aaef5080b6e1704aab382a40a7c9957a40b4790f7df7faa04b14f4db56361",
                "5K8zSJ4zcV3UfkAKCFY5PomL6SRx2pYjaKfnAtMVh6zbhnAuPon",
                "L34GWeLdHcmw81W7JfAAPfQfH1F7u2s4v5QANdfTe1TEAYpjXoLL",
                "04f650fb572d1475950b63f5175c77e8b5ed9035a209d8fb5af5a04d6bc39b7323"\
                  "00186733fcfe3def4ace6feae8b82dd03cc31b7855307d33b0a039170f374962",
                "02f650fb572d1475950b63f5175c77e8b5ed9035a209d8fb5af5a04d6bc39b7323",
                "18fKPR8s1MQeckAsgya1sx6Z3WmFXd8wv8",
                "1DVJQzgnyCahXdoXdJ3tjGA3hrYVgKpvgK")

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = key_validate_test
#!/usr/bin/env python

import unittest

from pycoin.block import Block
from pycoin.encoding import hash160_sec_to_bitcoin_address
from pycoin.key import Key
from pycoin.key.bip32 import Wallet
from pycoin.networks import pay_to_script_prefix_for_netcode, prv32_prefix_for_netcode, NETWORK_NAMES
from pycoin.serialize import b2h_rev, h2b

from pycoin.key.validate import is_address_valid, is_wif_valid, is_public_bip32_valid, is_private_bip32_valid

def change_prefix(address, new_prefix):
    return hash160_sec_to_bitcoin_address(Key.from_text(address).hash160(), address_prefix=new_prefix)


PAY_TO_HASH_ADDRESSES = ["1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH", "1EHNa6Q4Jz2uvNExL497mE43ikXhwF6kZm",
                        "1cMh228HTCiwS8ZsaakH8A8wze1JR5ZsP", "1LagHJk2FyCV2VzrNHVqg3gYG4TSYwDV4m",
                        "1CUNEBjYrCn2y1SdiUMohaKUi4wpP326Lb", "1NZUP3JAc9JkmbvmoTv7nVgZGtyJjirKV1"]

PAY_TO_SCRIPT_PREFIX = pay_to_script_prefix_for_netcode("BTC")

PAY_TO_SCRIPT_ADDRESSES = [change_prefix(t, PAY_TO_SCRIPT_PREFIX) for t in PAY_TO_HASH_ADDRESSES]


class KeyUtilsTest(unittest.TestCase):

    def test_address_valid_btc(self):
        for address in PAY_TO_HASH_ADDRESSES:
            self.assertEqual(is_address_valid(address), "BTC")
            a = address[:-1] + chr(ord(address[-1])+1)
            self.assertEqual(is_address_valid(a), None)

        for address in PAY_TO_HASH_ADDRESSES:
            self.assertEqual(is_address_valid(address, allowable_types=["pay_to_script"]), None)
            self.assertEqual(is_address_valid(address, allowable_types=["address"]), "BTC")

        for address in PAY_TO_SCRIPT_ADDRESSES:
            self.assertEqual(address[0], "3")
            self.assertEqual(is_address_valid(address, allowable_types=["pay_to_script"]), "BTC")
            self.assertEqual(is_address_valid(address, allowable_types=["address"]), None)


    def test_is_wif_valid(self):
        WIFS = ["KwDiBf89QgGbjEhKnhXJuH7LrciVrZi3qYjgd9M7rFU73sVHnoWn",
                "5HpHagT65TZzG1PH3CSu63k8DbpvD8s5ip4nEB3kEsreAnchuDf",
                "KwDiBf89QgGbjEhKnhXJuH7LrciVrZi3qYjgd9M7rFU74NMTptX4",
                "5HpHagT65TZzG1PH3CSu63k8DbpvD8s5ip4nEB3kEsreAvUcVfH"]

        for wif in WIFS:
            self.assertEqual(is_wif_valid(wif), "BTC")
            a = wif[:-1] + chr(ord(wif[-1])+1)
            self.assertEqual(is_wif_valid(a), None)

        for netcode in NETWORK_NAMES:
            for se in range(1, 10):
                key = Key(secret_exponent=se, netcode=netcode)
                for tv in [True, False]:
                    wif = key.wif(use_uncompressed=tv)
                    self.assertEqual(is_wif_valid(wif, allowable_netcodes=[netcode]), netcode)
                    a = wif[:-1] + chr(ord(wif[-1])+1)
                    self.assertEqual(is_wif_valid(a, allowable_netcodes=[netcode]), None)


    def test_is_public_private_bip32_valid(self):
        WALLET_KEYS = ["foo", "1", "2", "3", "4", "5"]

        # not all networks support BIP32 yet
        for netcode in "BTC XTN DOGE".split():
            for wk in WALLET_KEYS:
                wallet = Wallet.from_master_secret(wk.encode("utf8"), netcode=netcode)
                text = wallet.wallet_key(as_private=True)
                self.assertEqual(is_private_bip32_valid(text, allowable_netcodes=NETWORK_NAMES), netcode)
                self.assertEqual(is_public_bip32_valid(text, allowable_netcodes=NETWORK_NAMES), None)
                a = text[:-1] + chr(ord(text[-1])+1)
                self.assertEqual(is_private_bip32_valid(a, allowable_netcodes=NETWORK_NAMES), None)
                self.assertEqual(is_public_bip32_valid(a, allowable_netcodes=NETWORK_NAMES), None)
                text = wallet.wallet_key(as_private=False)
                self.assertEqual(is_private_bip32_valid(text, allowable_netcodes=NETWORK_NAMES), None)
                self.assertEqual(is_public_bip32_valid(text, allowable_netcodes=NETWORK_NAMES), netcode)
                a = text[:-1] + chr(ord(text[-1])+1)
                self.assertEqual(is_private_bip32_valid(a, allowable_netcodes=NETWORK_NAMES), None)
                self.assertEqual(is_public_bip32_valid(a, allowable_netcodes=NETWORK_NAMES), None)

########NEW FILE########
__FILENAME__ = parse_block_test
#!/usr/bin/env python

import io
import unittest

from pycoin.block import Block
from pycoin.serialize import b2h_rev, h2b

class BlockTest(unittest.TestCase):
    def test_block(self):
        expected_checksum = '0000000000089F7910F6755C10EA2795EC368A29B435D80770AD78493A6FECF1'.lower()

        block_data = h2b('010000007480150B299A16BBCE5CCDB1D1BBC65CFC5893B01E6619107C55200000000000790'\
        '0A2B203D24C69710AB6A94BEB937E1B1ADD64C2327E268D8C3E5F8B41DBED8796974CED66471B204C3247030'\
        '1000000010000000000000000000000000000000000000000000000000000000000000000FFFFFFFF0804ED6'\
        '6471B024001FFFFFFFF0100F2052A010000004341045FEE68BAB9915C4EDCA4C680420ED28BBC369ED84D48A'\
        'C178E1F5F7EEAC455BBE270DABA06802145854B5E29F0A7F816E2DF906E0FE4F6D5B4C9B92940E4F0EDAC000'\
        '000000100000001F7B30415D1A7BF6DB91CB2A272767C6799D721A4178AA328E0D77C199CB3B57F010000008'\
        'A4730440220556F61B84F16E637836D2E74B8CB784DE40C28FE3EF93CCB7406504EE9C7CAA5022043BD4749D'\
        '4F3F7F831AC696748AD8D8E79AEB4A1C539E742AA3256910FC88E170141049A414D94345712893A828DE57B4C'\
        '2054E2F596CDCA9D0B4451BA1CA5F8847830B9BE6E196450E6ABB21C540EA31BE310271AA00A49ED0BA930743'\
        'D1ED465BAD0FFFFFFFF0200E1F505000000001976A914529A63393D63E980ACE6FA885C5A89E4F27AA08988AC'\
        'C0ADA41A000000001976A9145D17976537F308865ED533CCCFDD76558CA3C8F088AC000000000100000001651'\
        '48D894D3922EF5FFDA962BE26016635C933D470C8B0AB7618E869E3F70E3C000000008B48304502207F5779EB'\
        'F4834FEAEFF4D250898324EB5C0833B16D7AF4C1CB0F66F50FCF6E85022100B78A65377FD018281E77285EFC3'\
        '1E5B9BA7CB7E20E015CF6B7FA3E4A466DD195014104072AD79E0AA38C05FA33DD185F84C17F611E58A8658CE'\
        '996D8B04395B99C7BE36529CAB7606900A0CD5A7AEBC6B233EA8E0FE60943054C63620E05E5B85F0426FFFFF'\
        'FFF02404B4C00000000001976A914D4CAA8447532CA8EE4C80A1AE1D230A01E22BFDB88AC8013A0DE0100000'\
        '01976A9149661A79AE1F6D487AF3420C13E649D6DF3747FC288AC00000000')

        # try to parse a block

        block = Block.parse(io.BytesIO(block_data))

        print(block)
        assert b2h_rev(block.hash()) == expected_checksum

        for tx in block.txs:
            print(tx)
            for t in tx.txs_in:
                print("  %s" % t)
            for t in tx.txs_out:
                print("  %s" % t)

        block.check_merkle_hash()

def main():
    unittest.main()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = scripts_test
#!/usr/bin/env python

import binascii
import unittest
import os
import sys
import tempfile

# binary data with GPG-encrypted WIF KwDiBf89QgGbjEhKnhXJuH7LrciVrZi3qYjgd9M7rFU73sVHnoWn for secret exponent 1
WIF_1_GPG = binascii.unhexlify(
    "8c0d040303026c3030b7518a94eb60c950bc87ab26f0604a37f247f74f88deda10b180bb807"
    "2879b728b8f056808baea0c8e511e7cf2eba77cce937d2f69a67a79e163bf70b57113d27cb6"
    "a1c2390a1e8069b447c34a7c9b5ba268c2beedd85b50")

class ScriptsTest(unittest.TestCase):

    def launch_tool(self, tool):
        # set
        python_path = sys.executable
        script_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
        cwd = os.getcwd()
        os.chdir(script_dir)
        tool = "%s %s" % (python_path, tool)
        os.environ["PYCOIN_SERVICE_PROVIDERS"] = "BLOCKR_IO:BLOCKCHAIN_INFO:BITEASY:BLOCKEXPLORER"
        r = os.system(tool)
        os.chdir(cwd)
        assert r == 0

    def set_cache_dir(self):
        temp_dir = tempfile.mkdtemp()
        os.environ["PYCOIN_CACHE_DIR"] = temp_dir
        return temp_dir

    def test_fetch_unspent(self):
        self.launch_tool("fetch_unspent.py 1KissFDVu2wAYWPRm4UGh5ZCDU9sE9an8T")

    def test_ku(self):
        self.launch_tool("ku.py 1")
        self.launch_tool("ku.py 2")
        self.launch_tool("ku.py -a 1")
        self.launch_tool("ku.py -W 1")
        self.launch_tool("ku.py P:foo")
        self.launch_tool("ku.py -w P:foo -s 5-10")
        self.launch_tool("ku.py -j -w P:foo -s 5-10")
        self.launch_tool("ku.py -n DOGE -j -w P:foo -s 5-10")
        self.launch_tool("ku.py -n BLK -j -w P:foo -s 5-10")

    def test_tx_fetch(self):
        self.launch_tool("tx.py 0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098")

    def test_tx_build(self):
        self.launch_tool("tx.py 0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098/0/410496b538e853519c726a2c91e61ec11600ae1390813a627c66fb8be7947be63c52da7589379515d4e0a604f8141781e62294721166bf621e73a82cbf2342c858eeac/5000000000 1KissFDVu2wAYWPRm4UGh5ZCDU9sE9an8T")

    def test_tx_sign(self):
        self.launch_tool("tx.py 0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098/0/210279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ac/5000000000 1KissFDVu2wAYWPRm4UGh5ZCDU9sE9an8T KwDiBf89QgGbjEhKnhXJuH7LrciVrZi3qYjgd9M7rFU73sVHnoWn")

    def test_tx_from_hex(self):
        # this hex represents a coinbase Tx to KwDiBf89QgGbjEhKnhXJuH7LrciVrZi3qYjgd9M7rFU73sVHnoWn
        self.launch_tool("tx.py 01000000010000000000000000000000000000000000000000000000000000000000000000ffffffff00ffffffff0100f2052a0100000023210279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ac00000000")

    def test_tx_with_gpg(self):
        #gpg_dir = tempfile.mkdtemp()
        #import pdb; pdb.set_trace()
        #os.environ["GNUPGHOME"] = gpg_dir
        ##f = open(os.path.join(gpg_dir, "gpg.conf"), "w")
        #f.write("use-agent\n")
        #f.close()
        gpg_wif = tempfile.NamedTemporaryFile(suffix=".gpg")
        gpg_wif.write(WIF_1_GPG)
        gpg_wif.flush()
        self.launch_tool("tx.py 5564224b6c01dbc2bfad89bfd8038bc2f4ca6c55eb660511d7151d71e4b94b6d/0/210279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ac/5000000000 1KissFDVu2wAYWPRm4UGh5ZCDU9sE9an8T -f %s -g'--passphrase foo'" % gpg_wif.name)

    def test_genwallet(self):
        self.launch_tool("genwallet.py -g")

    def test_cache_tx(self):
        the_dir = self.set_cache_dir()
        tx_id = "0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098"
        self.launch_tool("cache_tx.py %s" % tx_id)
        self.assertTrue(os.path.exists(os.path.join(the_dir, "txs", "%s_tx.bin" % tx_id)))

def main():
    unittest.main()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = signature_test
#!/usr/bin/env python

import unittest

from pycoin.ecdsa import sign, verify, public_pair_for_secret_exponent, possible_public_pairs_for_signature, generator_secp256k1

class SigningTest(unittest.TestCase):
    def test_sign(self):
        for se in ["47f7616ea6f9b923076625b4488115de1ef1187f760e65f89eb6f4f7ff04b012"] + [x * 64 for x in "123456789abcde"]:
            secret_exponent = int(se, 16)
            val = 28832970699858290 #int.from_bytes(b"foo bar", byteorder="big")
            sig = sign(generator_secp256k1, secret_exponent, val)

            public_pair = public_pair_for_secret_exponent(generator_secp256k1, secret_exponent)

            v = verify(generator_secp256k1, public_pair, val, sig)
            self.assertTrue(v)

            sig1 = (sig[0] + 1, sig[1])
            v = verify(generator_secp256k1, public_pair, val, sig1)
            self.assertFalse(v)

            public_pairs = possible_public_pairs_for_signature(generator_secp256k1, val, sig)
            self.assertIn(public_pair, public_pairs)
            print(se)

def main():
    unittest.main()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = tx_test
#!/usr/bin/env python

import unittest

from pycoin.tx.Tx import Tx

TX_E1A18B843FC420734DEEB68FF6DF041A2585E1A0D7DBF3B82AAB98291A6D9952_HEX = ("0100000001a8f57056b016d7d243fc0fc2a73f9146e7e4c7766ec6033b5ac4cb89c"
"64e19d0000000008a4730440220251acb534ba1b8a269260ad3fa80e075cd150d3ff"
"ba76ad20cd2e8178dee98b702202284f9c7eae3adfcf0857a901cd34f0ea338d5744caab88afad5797be643f7b7"
"014104af8385da9dc85aa153f16341a4015bc95e7ff57876b9bde40bd8450a5723a05c1c89ff2d85230d2e62c0c"
"7690b8272cf85868a0a0fc02f99a5b793f22d5c7092ffffffff02bb5b0700000000001976a9145b78716d137e38"
"6ae2befc4296d938372559f37888acdd3c71000000000017a914c6572ee1c85a1b9ce1921753871bda0b5ce889ac8700000000")

class TxTest(unittest.TestCase):

    def test_tx_api(self):
        tx = Tx.tx_from_hex(TX_E1A18B843FC420734DEEB68FF6DF041A2585E1A0D7DBF3B82AAB98291A6D9952_HEX)
        # this transaction is a pay-to-hash transaction
        self.assertEqual(tx.id(), "e1a18b843fc420734deeb68ff6df041a2585e1a0d7dbf3b82aab98291a6d9952")
        self.assertEqual(tx.txs_out[0].bitcoin_address(), "19LemzJ3XPdUxp113uynqCAivDbXZBdBy3")
        # TODO: fix this when pay-to-hash properly parsed
        self.assertEqual(tx.txs_out[1].bitcoin_address(), "3KmkA7hvqG2wKkWUGz1BySioUywvcmdPLR")


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = tx_utils_test
#!/usr/bin/env python

import hashlib
import struct
import unittest

from pycoin.ecdsa import generator_secp256k1, public_pair_for_secret_exponent
from pycoin.encoding import public_pair_to_bitcoin_address, secret_exponent_to_wif

from pycoin.tx.Tx import BadSpendableError
from pycoin.tx.TxOut import standard_tx_out_script
from pycoin.tx.tx_utils import create_signed_tx
from pycoin.tx.Spendable import Spendable


BITCOIN_ADDRESSES = [public_pair_to_bitcoin_address(
    public_pair_for_secret_exponent(generator_secp256k1, i))
    for i in range(1, 21)]

WIFS = [secret_exponent_to_wif(i) for i in range(1, 21)]

FAKE_HASHES = [hashlib.sha256(struct.pack("Q", idx)).digest() for idx in range(100)]


class SpendTest(unittest.TestCase):

    def test_simple_spend(self):

        FEE = 10000

        # create a fake Spendable
        COIN_VALUE = 100000000
        spendables = [Spendable(COIN_VALUE, standard_tx_out_script(BITCOIN_ADDRESSES[0]), FAKE_HASHES[1], 0)]

        EXPECTED_IDS = [
            "d28bff6c4a8a0f9e7d5b7df0670d07b43c5613d8c9b14e84707b1e2c0154a978",
            "7afbe63b00171b18f806ebd48190ebc1c68cadf286a85489c06ebe43d146489e",
            "2b90c150ba1d080a0816952f5d9c2642d408989cbc4d4c540591c8c9241294bd",
            "17b0b5b22887081595c1a9ad153e903f63bb8682ae59d6082df018dc617e5e67",
            "dff1b34c243becb096ad2a2d6119973067a8137cc8bf95615e742bbf6f0944c1",
            "206bbfbb759a8f91901d86b62390d7587f6097a32994ece7752d143fc8a02cee",
            "7841412716ad35cbc9954e547ba85be89e5ed0b34ed5fb8d7594517318dc10d6",
            "8b7e643bf47db46ada7a75b8498990b111fe20917b5610ca6759b8b0078ccd5e",
            "5756f0a6d5a2bbb93a07f0729d3773aaafd21393ede3ec0e20b0b5219ca45548",
            "32dcbb34965ea72d2caa59eb1e907aa28bac2afea43214c1809f5d8ed360f30e",
        ]

        for count in range(1, 11):
            tx = create_signed_tx(spendables, BITCOIN_ADDRESSES[1:count+1], wifs=WIFS[:1])
            self.assertEqual(tx.bad_signature_count(), 0)
            self.assertEqual(tx.fee(), FEE)
            self.assertEqual(tx.id(), EXPECTED_IDS[count-1])
            for idx in range(1, count+1):
                self.assertEqual(tx.txs_out[idx-1].bitcoin_address(), BITCOIN_ADDRESSES[idx])
            # TODO: add check that s + s < generator for each signature
            for i in range(count):
                extra = (1 if i < ((COIN_VALUE - FEE) % count) else 0)
                self.assertEqual(tx.txs_out[i].coin_value, (COIN_VALUE - FEE)//count + extra)

    def test_confirm_input(self):
        FEE = 10000

        # create a fake Spendable
        COIN_VALUE = 100000000
        spendables = [Spendable(COIN_VALUE, standard_tx_out_script(BITCOIN_ADDRESSES[0]), FAKE_HASHES[1], 0)]

        tx_1 = create_signed_tx(spendables, BITCOIN_ADDRESSES[1:2], wifs=WIFS[:1])

        spendables = tx_1.tx_outs_as_spendable()

        tx_db = dict((tx.hash(), tx) for tx in [tx_1])

        tx_2 = create_signed_tx(spendables, BITCOIN_ADDRESSES[2:3], wifs=WIFS[:3])
        tx_2.validate_unspents(tx_db)

        tx_2 = create_signed_tx([s.as_dict() for s in spendables], BITCOIN_ADDRESSES[2:3], wifs=WIFS[:3])
        tx_2.validate_unspents(tx_db)

        tx_2 = create_signed_tx([s.as_text() for s in spendables], BITCOIN_ADDRESSES[2:3], wifs=WIFS[:3])
        tx_2.validate_unspents(tx_db)


    def test_confirm_input_raises(self):
        FEE = 10000

        # create a fake Spendable
        COIN_VALUE = 100000000
        spendables = [Spendable(COIN_VALUE, standard_tx_out_script(BITCOIN_ADDRESSES[0]), FAKE_HASHES[1], 0)]

        tx_1 = create_signed_tx(spendables, BITCOIN_ADDRESSES[1:2], wifs=WIFS[:1])
        spendables = tx_1.tx_outs_as_spendable()
        spendables[0].coin_value += 100

        tx_db = dict((tx.hash(), tx) for tx in [tx_1])
        tx_2 = create_signed_tx(spendables, BITCOIN_ADDRESSES[2:3], wifs=WIFS[:3])

        self.assertRaises(BadSpendableError, tx_2.validate_unspents, tx_db)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = validate_tx_test
#!/usr/bin/env python

import binascii
import io
import unittest

from pycoin.block import Block
from pycoin.serialize import h2b
from pycoin.tx import Tx, ValidationFailureError
from pycoin.tx.script import tools


class ValidatingTest(unittest.TestCase):
    def test_validate(self):
        # block 80971
        block_80971_cs = h2b('00000000001126456C67A1F5F0FF0268F53B4F22E0531DC70C7B69746AF69DAC')
        block_80971_data = h2b('01000000950A1631FB9FAC411DFB173487B9E18018B7C6F7147E78C06258410000000000A881352F97F14B'\
        'F191B54915AE124E051B8FE6C3922C5082B34EAD503000FC34D891974CED66471B4016850A040100'\
        '0000010000000000000000000000000000000000000000000000000000000000000000FFFFFFFF080'\
        '4ED66471B02C301FFFFFFFF0100F2052A01000000434104CB6B6B4EADC96C7D08B21B29D0ADA5F29F937'\
        '8978CABDB602B8B65DA08C8A93CAAB46F5ABD59889BAC704925942DD77A2116D10E0274CAD944C71D3D1A'\
        '670570AC0000000001000000018C55ED829F16A4E43902940D3D33005264606D5F7D555B5F67EE4C033390'\
        'C2EB010000008A47304402202D1BF606648EDCDB124C1254930852D99188E1231715031CBEAEA80CCFD2B39A'\
        '02201FA9D6EE7A1763580E342474FC1AEF59B0468F98479953437F525063E25675DE014104A01F763CFBF5E518'\
        'C628939158AF3DC0CAAC35C4BA7BC1CE8B7E634E8CDC44E15F0296B250282BD649BAA8398D199F2424FCDCD88'\
        'D3A9ED186E4FD3CB9BF57CFFFFFFFFF02404B4C00000000001976A9148156FF75BEF24B35ACCE3C05289A241'\
        '1E1B0E57988AC00AA38DF010000001976A914BC7E692A5FFE95A596712F5ED83393B3002E452E88AC000000'\
        '0001000000019C97AFDF6C9A31FFA86D71EA79A079001E2B59EE408FD418498219400639AC0A010000008B4'\
        '830450220363CFFAE09599397B21E6D8A8073FB1DFBE06B6ACDD0F2F7D3FEA86CA9C3F605022100FA255A6ED'\
        '23FD825C759EF1A885A31CAD0989606CA8A3A16657D50FE3CEF5828014104FF444BAC08308B9EC97F56A652A'\
        'D8866E0BA804DA97868909999566CB377F4A2C8F1000E83B496868F3A282E1A34DF78565B65C15C3FA21A076'\
        '3FD81A3DFBBB6FFFFFFFF02C05EECDE010000001976A914588554E6CC64E7343D77117DA7E01357A6111B798'\
        '8AC404B4C00000000001976A914CA6EB218592F289999F13916EE32829AD587DBC588AC00000000010000000'\
        '1BEF5C9225CB9FE3DEF929423FA36AAD9980B9D6F8F3070001ACF3A5FB389A69F000000004A493046022100F'\
        'B23B1E2F2FB8B96E04D220D385346290A9349F89BBBC5C225D5A56D931F8A8E022100F298EB28294B90C1BAF'\
        '319DAB713E7CA721AAADD8FCC15F849DE7B0A6CF5412101FFFFFFFF0100F2052A010000001976A9146DDEA80'\
        '71439951115469D0D2E2B80ECBCDD48DB88AC00000000');

        # block 80974
        block_80974_cs = h2b('0000000000089F7910F6755C10EA2795EC368A29B435D80770AD78493A6FECF1')
        block_80974_data = h2b('010000007480150B299A16BBCE5CCDB1D1BBC65CFC5893B01E6619107C55200000000000790'\
        '0A2B203D24C69710AB6A94BEB937E1B1ADD64C2327E268D8C3E5F8B41DBED8796974CED66471B204C3247030'\
        '1000000010000000000000000000000000000000000000000000000000000000000000000FFFFFFFF0804ED6'\
        '6471B024001FFFFFFFF0100F2052A010000004341045FEE68BAB9915C4EDCA4C680420ED28BBC369ED84D48A'\
        'C178E1F5F7EEAC455BBE270DABA06802145854B5E29F0A7F816E2DF906E0FE4F6D5B4C9B92940E4F0EDAC000'\
        '000000100000001F7B30415D1A7BF6DB91CB2A272767C6799D721A4178AA328E0D77C199CB3B57F010000008'\
        'A4730440220556F61B84F16E637836D2E74B8CB784DE40C28FE3EF93CCB7406504EE9C7CAA5022043BD4749D'\
        '4F3F7F831AC696748AD8D8E79AEB4A1C539E742AA3256910FC88E170141049A414D94345712893A828DE57B4C'\
        '2054E2F596CDCA9D0B4451BA1CA5F8847830B9BE6E196450E6ABB21C540EA31BE310271AA00A49ED0BA930743'\
        'D1ED465BAD0FFFFFFFF0200E1F505000000001976A914529A63393D63E980ACE6FA885C5A89E4F27AA08988AC'\
        'C0ADA41A000000001976A9145D17976537F308865ED533CCCFDD76558CA3C8F088AC000000000100000001651'\
        '48D894D3922EF5FFDA962BE26016635C933D470C8B0AB7618E869E3F70E3C000000008B48304502207F5779EB'\
        'F4834FEAEFF4D250898324EB5C0833B16D7AF4C1CB0F66F50FCF6E85022100B78A65377FD018281E77285EFC3'\
        '1E5B9BA7CB7E20E015CF6B7FA3E4A466DD195014104072AD79E0AA38C05FA33DD185F84C17F611E58A8658CE'\
        '996D8B04395B99C7BE36529CAB7606900A0CD5A7AEBC6B233EA8E0FE60943054C63620E05E5B85F0426FFFFF'\
        'FFF02404B4C00000000001976A914D4CAA8447532CA8EE4C80A1AE1D230A01E22BFDB88AC8013A0DE0100000'\
        '01976A9149661A79AE1F6D487AF3420C13E649D6DF3747FC288AC00000000')

        block_80971 = Block.parse(io.BytesIO(block_80971_data))
        block_80974 = Block.parse(io.BytesIO(block_80974_data))

        tx_db = { tx.hash(): tx for tx in block_80971.txs }

        tx_to_validate = block_80974.txs[2]
        self.assertEqual("OP_DUP OP_HASH160 d4caa8447532ca8ee4c80a1ae1d230a01e22bfdb OP_EQUALVERIFY OP_CHECKSIG",
            tools.disassemble(tx_to_validate.txs_out[0].script))
        self.assertEqual(tx_to_validate.id(), "7c4f5385050c18aa8df2ba50da566bbab68635999cc99b75124863da1594195b")

        tx_to_validate.unspents_from_db(tx_db)
        self.assertEqual(tx_to_validate.bad_signature_count(), 0)

        # now, let's corrupt the Tx and see what happens
        tx_out = tx_to_validate.txs_out[1]

        disassembly = tools.disassemble(tx_out.script)
        tx_out.script = tools.compile(disassembly)

        self.assertEqual(tx_to_validate.bad_signature_count(), 0)

        disassembly = disassembly.replace("9661a79ae1f6d487af3420c13e649d6df3747fc2", "9661a79ae1f6d487af3420c13e649d6df3747fc3")

        tx_out.script = tools.compile(disassembly)

        self.assertEqual(tx_to_validate.bad_signature_count(), 1)
        self.assertFalse(tx_to_validate.is_signature_ok(0))

    def test_validate_two_inputs(self):
        def tx_from_b64(h):
            f = io.BytesIO(binascii.a2b_base64(h.encode("utf8")))
            return Tx.parse(f)
        # c9989d984c97128b03b9f118481c631c584f7aa42b578dbea6194148701b053d
        # This is the one we're going to validate. It has inputs from
        #  tx_1 = b52201c2741d410b70688335afebba0d58f8675fa9b6c8c54becb0d7c0a75983
        # and tx_2 = 72151f65db1d8594df90778639a4c0c17c1e303af01de0d04af8fac13854bbfd
        #
        TX_0_HEX = """
AQAAAAKDWafA17DsS8XItqlfZ/hYDbrrrzWDaHALQR10wgEitQAAAACLSDBFAiAnyvQ1P7b8
+84JbBUbE1Xtgrd0KNpD4eyVTNU/burbtgIhAOS8T1TrhXkGXQTGbLSEJy5uvZMGEzOjITxO
+DrykiPlAUEE3yJcIB5OCpaDjrop+N3bm8h9PKw8bF/YB4v3yD+VeQf4fXdUZ9hJJSnFeJ+Q
eJrC7q3Y23QSYeYbW/AfA3D5G//////9u1Q4wfr4StDgHfA6MB58wcCkOYZ3kN+UhR3bZR8V
cgAAAACLSDBFAiAN6ZQr+9HTgmF57EsPyXIhQ6J5M4lgwlj/tJTShZ+toQIhAL0U1i9yiCEm
75uCEp8uRaySqS7P4x7A+L2Vr5kS+7ANAUEEkSqVI6gw1scM0GuJWgMh4jpWKJA0yOl03uQa
V/jHURn+HswOIORzvsG9qQY1/9BZgDPaMuI5U5JlyA3WkhLxgf////8CtkSUzxAAAAAZdqkU
LXTu3lp2t/wMSuvqbifOSj9/kvmIrAAoa+4AAAAAGXapFF3ySpVdjz9V8fRKvzDqXQRcmowS
iKwAAAAA"""
        TX_1_HEX = """AQAAAAEL3YmFDcZpf4SH7uN1IBmMoBd4OhmTp4EAQ8A0ZQ3tiwAAAACKRzBEAiA4Fkl8lkJS
eLtWHsp1j0h7y0KKFmqxhDR0CK0HnmZWBQIgDSTDenor3zbNqTs+FApeDl8DKCz1xGQCJQN0
/sp00VABQQQzSNc33wdDXA/F9y9/hAR88q6Se6vRCHEC7dYgbIp1pgxqGzrWXQroGkQLhnAb
n/fDhUoVbCgM/UHXYmjXlhdO/////wI3HGlfEQAAABl2qRRM+dhUVUjeAlb0jEsHJrFClGGS
Z4isMAYVCgAAAAAZdqkUgnSLXoYTeOKFFRdtLYxWcGZ2Ht2IrAAAAAA=
"""
        TX_2_HEX = """AQAAAAFDjBbw61AYUWMx+3moZ2vb9dvLKydOSFIwcfBTjG0QSgEAAACKRzBEAiA5WWKhR48O
I60ZDCXnOru/FH6NvuTGhRLggjbpJB2dhgIgKp0FFL0ClSCxxqGjYneDinvgROGSw6DtVtvf
lrhaom8BQQR50YjAg1e5qRkP4ER29ec5jKfzk3DHJhS7Si0sEbvNIJMfjjbZfZWtJi15wHZh
uHh4e3G6SWMdJLHH5pgbseFh/////wLPE5deAAAAABl2qRSmRdbMvv5fEbgFD1YktaBU9zQT
W4iswJ7mBQAAAAAZdqkU4E5+Is4tr+8bPU6ELYHSvz/Ng0eIrAAAAAA=
"""
        tx_0 = tx_from_b64(TX_0_HEX)
        self.assertEqual(tx_0.id(), "c9989d984c97128b03b9f118481c631c584f7aa42b578dbea6194148701b053d")
        tx_1 = tx_from_b64(TX_1_HEX)
        self.assertEqual(tx_1.id(), "b52201c2741d410b70688335afebba0d58f8675fa9b6c8c54becb0d7c0a75983")
        tx_2 = tx_from_b64(TX_2_HEX)
        self.assertEqual(tx_2.id(), "72151f65db1d8594df90778639a4c0c17c1e303af01de0d04af8fac13854bbfd")

        TX_DB = { tx.hash(): tx for tx in [tx_0, tx_1, tx_2] }

        tx_to_validate = tx_0
        self.assertEqual("OP_DUP OP_HASH160 2d74eede5a76b7fc0c4aebea6e27ce4a3f7f92f9 OP_EQUALVERIFY OP_CHECKSIG",
            tools.disassemble(tx_to_validate.txs_out[0].script))
        self.assertEqual(tx_to_validate.id(), "c9989d984c97128b03b9f118481c631c584f7aa42b578dbea6194148701b053d")

        tx_to_validate.unspents_from_db(TX_DB)
        self.assertEqual(tx_to_validate.bad_signature_count(), 0)

        # now let's mess with signatures
        disassembly = tools.disassemble(tx_to_validate.txs_in[0].script)
        tx_to_validate.txs_in[0].script = tools.compile(disassembly)
        self.assertEqual(tx_to_validate.bad_signature_count(), 0)
        disassembly = disassembly.replace("353fb6fcfbce09", "353fb6fcfbce19")
        tx_to_validate.txs_in[0].script = tools.compile(disassembly)
        self.assertEqual(tx_to_validate.bad_signature_count(), 1)
        self.assertFalse(tx_to_validate.is_signature_ok(0))

        tx_to_validate = tx_from_b64(TX_0_HEX)
        tx_to_validate.unspents_from_db(TX_DB)
        self.assertEqual(tx_to_validate.bad_signature_count(), 0)
        disassembly = tools.disassemble(tx_to_validate.txs_in[1].script)
        disassembly = disassembly.replace("960c258ffb494d2859f", "960d258ffb494d2859f")
        tx_to_validate.txs_in[1].script = tools.compile(disassembly)
        self.assertEqual(tx_to_validate.bad_signature_count(), 1)
        self.assertFalse(tx_to_validate.is_signature_ok(1))

        # futz with signature on tx_1
        tx_to_validate = tx_from_b64(TX_0_HEX)
        original_tx_hash = tx_1.hash()
        disassembly = tools.disassemble(tx_1.txs_out[0].script)
        disassembly = disassembly.replace("4cf9d8545548de0256f48c4b0726b14294619267", "4cf9d8545548de1256f48c4b0726b14294619267")
        tx_1.txs_out[0].script = tools.compile(disassembly)
        TX_DB[original_tx_hash] = tx_1
        tx_to_validate.unspents_from_db(TX_DB, ignore_missing=True)
        self.assertEqual(tx_to_validate.bad_signature_count(), 1)
        self.assertFalse(tx_to_validate.is_signature_ok(0, ))

        # fix it up again
        TX_DB[original_tx_hash] = tx_from_b64(TX_1_HEX)
        tx_to_validate.unspents_from_db(TX_DB)
        self.assertEqual(tx_to_validate.bad_signature_count(), 0)

        # futz with signature on tx_2
        tx_to_validate = tx_from_b64(TX_0_HEX)
        original_tx_hash = tx_2.hash()
        disassembly = tools.disassemble(tx_2.txs_out[0].script)
        disassembly = disassembly.replace("a645d6ccbefe5f11b8050f5624b5a054f734135b", "a665d6ccbefe5f11b8050f5624b5a054f734135b")
        tx_2.txs_out[0].script = tools.compile(disassembly)
        TX_DB[original_tx_hash] = tx_2
        tx_to_validate.unspents_from_db(TX_DB, ignore_missing=True)
        self.assertEqual(tx_to_validate.bad_signature_count(), 1)
        self.assertFalse(tx_to_validate.is_signature_ok(1))

        # fix it up again
        TX_DB[original_tx_hash] = tx_from_b64(TX_2_HEX)
        tx_to_validate.unspents_from_db(TX_DB)
        self.assertEqual(tx_to_validate.bad_signature_count(), 0)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = der
# -*- coding: utf-8 -*-
"""
Deal with DER encoding and decoding.

Adapted from python-ecdsa at https://github.com/warner/python-ecdsa
Copyright (c) 2010 Brian Warner
Portions written in 2005 by Peter Pearson and placed in the public domain.


The MIT License (MIT)

Copyright (c) 2013 by Richard Kiss

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import binascii

bytes_from_int = chr if bytes == str else lambda x: bytes([x])

class UnexpectedDER(Exception):
    pass

def encode_integer(r):
    assert r >= 0 # can't support negative numbers yet
    h = "%x" % r
    if len(h)%2:
        h = "0" + h
    s = binascii.unhexlify(h.encode("utf8"))
    if ord(s[:1]) <= 0x7f:
        return b"\x02" + bytes_from_int(len(s)) + s
    else:
        # DER integers are two's complement, so if the first byte is
        # 0x80-0xff then we need an extra 0x00 byte to prevent it from
        # looking negative.
        return b"\x02" + bytes_from_int(len(s)+1) + b"\x00" + s

def encode_sequence(*encoded_pieces):
    total_len = sum([len(p) for p in encoded_pieces])
    return b"\x30" + encode_length(total_len) + b"".join(encoded_pieces)

def remove_sequence(string):
    if not string.startswith(b"\x30"):
        raise UnexpectedDER("wanted sequence (0x30), got 0x%02x" %
                            ord(string[:1]))
    length, lengthlength = read_length(string[1:])
    endseq = 1+lengthlength+length
    return string[1+lengthlength:endseq], string[endseq:]

def remove_integer(string):
    if not string.startswith(b"\x02"):
        raise UnexpectedDER("wanted integer (0x02), got 0x%02x" %
                            ord(string[:1]))
    length, llen = read_length(string[1:])
    numberbytes = string[1+llen:1+llen+length]
    rest = string[1+llen+length:]
    assert ord(numberbytes[:1]) < 0x80 # can't support negative numbers yet
    return int(binascii.hexlify(numberbytes), 16), rest

def encode_length(l):
    assert l >= 0
    if l < 0x80:
        return bytes_from_int(l)
    s = "%x" % l
    if len(s)%2:
        s = "0"+s
    s = binascii.unhexlify(s)
    llen = len(s)
    return bytes_from_int(0x80|llen) + s

def read_length(string):
    s0 = ord(string[:1])
    if not (s0 & 0x80):
        # short form
        return (s0 & 0x7f), 1
    # else long-form: b0&0x7f is number of additional base256 length bytes,
    # big-endian
    llen = s0 & 0x7f
    if llen > len(string)-1:
        raise UnexpectedDER("ran out of length bytes")
    return int(binascii.hexlify(string[1:1+llen]), 16), 1+llen

def sigencode_der(r, s):
    return encode_sequence(encode_integer(r), encode_integer(s))

def sigdecode_der(sig_der):
    rs_strings, empty = remove_sequence(sig_der)
    if empty != b"":
        raise UnexpectedDER("trailing junk after DER sig: %s" %
                                binascii.hexlify(empty))
    r, rest = remove_integer(rs_strings)
    s, empty = remove_integer(rest)
    if empty != b"":
        raise UnexpectedDER("trailing junk after DER numbers: %s" %
                                binascii.hexlify(empty))
    return r, s

########NEW FILE########
__FILENAME__ = microcode
# -*- coding: utf-8 -*-
"""
Implement instructions of the Bitcoin VM.


The MIT License (MIT)

Copyright (c) 2013 by Richard Kiss

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import binascii
import hashlib

from . import ScriptError

from .opcodes import OPCODE_TO_INT
from .tools import bytes_to_int, int_to_bytes
from ...encoding import hash160, double_sha256, ripemd160
from ...serialize import h2b

bytes_from_ints = (lambda x: ''.join(chr(c) for c in x)) if bytes == str else bytes
bytes_to_ints = (lambda x: (ord(c) for c in x)) if bytes == str else lambda x: x

VCH_TRUE = b'\1\1'
VCH_FALSE = b'\0'

do_OP_NOP = do_OP_NOP1 = do_OP_NOP2 = do_OP_NOP3 = do_OP_NOP4 = do_OP_NOP5 = lambda s: None
do_OP_NOP6 = do_OP_NOP7 = do_OP_NOP8 = do_OP_NOP9 = do_OP_NOP10 = lambda s: None

def do_OP_VERIFY(stack):
    pass

def do_OP_RETURN(stack):
    raise ScriptError("OP_RETURN encountered")

def do_OP_2DROP(stack):
    """
    >>> s = [1, 2, 3]
    >>> do_OP_2DROP(s)
    >>> print(s)
    [1]
    """
    stack.pop()
    stack.pop()

def do_OP_2DUP(stack):
    #// (x1 x2 -- x1 x2 x1 x2)
    """
    >>> s = [1, 2]
    >>> do_OP_2DUP(s)
    >>> print(s)
    [1, 2, 1, 2]
    """
    stack.append(stack[-2])
    stack.append(stack[-2])

def do_OP_3DUP(stack):
    #// (x1 x2 x3 -- x1 x2 x3 x1 x2 x3)
    """
    >>> s = [1, 2, 3]
    >>> do_OP_3DUP(s)
    >>> print(s)
    [1, 2, 3, 1, 2, 3]
    """
    stack.append(stack[-3])
    stack.append(stack[-3])
    stack.append(stack[-3])

def do_OP_2OVER(stack):
    #// (x1 x2 x3 x4 -- x1 x2 x3 x4 x1 x2)
    """
    >>> s = [1, 2, 3, 4]
    >>> do_OP_2OVER(s)
    >>> print(s)
    [1, 2, 3, 4, 1, 2]
    """
    stack.append(stack[-4])
    stack.append(stack[-4])

def do_OP_2ROT(stack):
    """
    >>> s = [1, 2, 3, 4, 5, 6]
    >>> do_OP_2ROT(s)
    >>> print(s)
    [3, 4, 5, 6, 1, 2]
    """
    stack.append(stack.pop(-6))
    stack.append(stack.pop(-6))

def do_OP_2SWAP(stack):
    """
    >>> s = [1, 2, 3, 4]
    >>> do_OP_2SWAP(s)
    >>> print(s)
    [3, 4, 1, 2]
    """
    stack.append(stack.pop(-4))
    stack.append(stack.pop(-4))

def do_OP_IFDUP(stack):
    """
    >>> s = [1, 2]
    >>> do_OP_IFDUP(s)
    >>> print(s)
    [1, 2, 2]
    >>> s = [1, 2, 0]
    >>> do_OP_IFDUP(s)
    >>> print(s)
    [1, 2, 0]
    """
    if stack[-1]:
        stack.append(stack[-1])

def do_OP_DEPTH(stack):
    """
    >>> s = [1, 2, 1, 2, 1, 2]
    >>> do_OP_DEPTH(s)
    >>> print(s)
    [1, 2, 1, 2, 1, 2, 6]
    """
    stack.append(len(stack))

def do_OP_DROP(stack):
    """
    >>> s = [1, 2]
    >>> do_OP_DROP(s)
    >>> print(s)
    [1]
    """
    stack.pop()

def do_OP_DUP(stack):
    """
    >>> s = [1, 2]
    >>> do_OP_DUP(s)
    >>> print(s)
    [1, 2, 2]
    """
    stack.append(stack[-1])

def do_OP_NIP(stack):
    """
    >>> s = [1, 2]
    >>> do_OP_NIP(s)
    >>> print(s)
    [2]
    """
    v = stack.pop()
    stack.pop()
    stack.append(v)

def do_OP_OVER(stack):
    """
    >>> s = [1, 2]
    >>> do_OP_OVER(s)
    >>> print(s)
    [1, 2, 1]
    """
    stack.append(stack[-2])

def do_OP_PICK(stack):
    """
    >>> s = ['a', 'b', 'c', 'd', b'\2']
    >>> do_OP_PICK(s)
    >>> print(s)
    ['a', 'b', 'c', 'd', 'b']
    """
    v = bytes_to_int(stack.pop())
    stack.append(stack[-v-1])

def do_OP_ROLL(stack):
    """
    >>> s = ['a', 'b', 'c', 'd', b'\2']
    >>> do_OP_ROLL(s)
    >>> print(s)
    ['a', 'c', 'd', 'b']
    """
    v = bytes_to_int(stack.pop())
    stack.append(stack.pop(-v-1))

def do_OP_ROT(stack):
    """
    >>> s = [1, 2, 3]
    >>> do_OP_ROT(s)
    >>> print(s)
    [2, 3, 1]
    """
    stack.append(stack.pop(-3))

def do_OP_SWAP(stack):
    """
    >>> s = [1, 2, 3]
    >>> do_OP_SWAP(s)
    >>> print(s)
    [1, 3, 2]
    """
    stack.append(stack.pop(-2))

def do_OP_TUCK(stack):
    """
    >>> s = [1, 2, 3]
    >>> do_OP_TUCK(s)
    >>> print(s)
    [1, 3, 2, 3]
    """
    v1 = stack.pop()
    v2 = stack.pop()
    stack.append(v1)
    stack.append(v2)
    stack.append(v1)

def do_OP_CAT(stack):
    """
    >>> s = ["foo", "bar"]
    >>> do_OP_CAT(s)
    >>> print(s)
    ['foobar']
    """
    v1 = stack.pop()
    v2 = stack.pop()
    stack.append(v2 + v1)

def do_OP_SUBSTR(stack):
    """
    >>> s = ['abcdef', b'\3', b'\2']
    >>> do_OP_SUBSTR(s)
    >>> print(s)
    ['de']
    """
    pos = bytes_to_int(stack.pop())
    length = bytes_to_int(stack.pop())
    stack.append(stack.pop()[length:length+pos])

def do_OP_LEFT(stack):
    """
    >>> s = [b'abcdef', b'\\3']
    >>> do_OP_LEFT(s)
    >>> print(len(s)==1 and s[0]==b'abc')
    True
    >>> s = [b'abcdef', b'\\0']
    >>> do_OP_LEFT(s)
    >>> print(len(s) ==1 and s[0]==b'')
    True
    """
    pos = bytes_to_int(stack.pop())
    stack.append(stack.pop()[:pos])

def do_OP_RIGHT(stack):
    """
    >>> s = [b'abcdef', b'\\3']
    >>> do_OP_RIGHT(s)
    >>> print(s==[b'def'])
    True
    >>> s = [b'abcdef', b'\\0']
    >>> do_OP_RIGHT(s)
    >>> print(s==[b''])
    True
    """
    pos = bytes_to_int(stack.pop())
    if pos > 0:
        stack.append(stack.pop()[-pos:])
    else:
        stack.pop()
        stack.append(b'')

def do_OP_SIZE(stack):
    """
    >>> s = [b'abcdef']
    >>> do_OP_SIZE(s)
    >>> print(s == [b'abcdef', b'\x06'])
    True
    >>> s = [b'abcdef'*1000]
    >>> do_OP_SIZE(s)
    >>> print(binascii.hexlify(s[-1]) == b'1770')
    True
    """
    stack.append(int_to_bytes(len(stack[-1])))

def do_OP_INVERT(stack):
    """
    >>> s = [h2b('5dcf39822aebc166')]
    >>> do_OP_INVERT(s)
    >>> print(binascii.hexlify(s[0]) == b'a230c67dd5143e99')
    True
    """
    v = stack.pop()
    # use bytes_from_ints and bytes_to_ints so it works with
    # Python 2.7 and 3.3. Ugh
    stack.append(bytes_from_ints((s^0xff) for s in bytes_to_ints(v)))

def make_same_size(v1, v2):
    larger = max(len(v1), len(v2))
    nulls = b'\0' * larger
    v1 = (v1 + nulls)[:larger]
    v2 = (v2 + nulls)[:larger]
    return v1, v2

def make_bitwise_bin_op(binop):
    """
    >>> s = [h2b('5dcf39832aebc166'), h2b('ff00f086') ]
    >>> do_OP_AND(s)
    >>> print(binascii.hexlify(s[0]) == b'5d00308200000000')
    True
    >>> s = [h2b('5dcf39832aebc166'), h2b('ff00f086') ]
    >>> do_OP_OR(s)
    >>> print(binascii.hexlify(s[0]) == b'ffcff9872aebc166')
    True
    >>> s = [h2b('5dcf39832aebc166'), h2b('ff00f086') ]
    >>> do_OP_XOR(s)
    >>> print(binascii.hexlify(s[0]) == b'a2cfc9052aebc166')
    True
    >>> s = []
    """
    def f(stack):
        v1 = stack.pop()
        v2 = stack.pop()
        v1, v2 = make_same_size(v1, v2)
        stack.append(bytes_from_ints(binop(c1, c2) for c1, c2 in zip(bytes_to_ints(v1), bytes_to_ints(v2))))
    return f

do_OP_AND = make_bitwise_bin_op(lambda x,y: x & y)
do_OP_OR = make_bitwise_bin_op(lambda x,y: x | y)
do_OP_XOR = make_bitwise_bin_op(lambda x,y: x ^ y)

def make_bool(v):
    if v: return VCH_TRUE
    return VCH_FALSE

def do_OP_EQUAL(stack):
    """
    >>> s = [b'string1', b'string1']
    >>> do_OP_EQUAL(s)
    >>> print(s == [VCH_TRUE])
    True
    >>> s = [b'string1', b'string2']
    >>> do_OP_EQUAL(s)
    >>> print(s == [VCH_FALSE])
    True
    """
    v1 = stack.pop()
    v2 = stack.pop()
    stack.append(make_bool(v1 == v2))

do_OP_EQUALVERIFY = lambda s: do_OP_EQUAL(s)

def make_bin_op(binop):
    def f(stack):
        v1 = bytes_to_int(stack.pop())
        v2 = bytes_to_int(stack.pop())
        stack.append(int_to_bytes(binop(v2, v1)))
    return f

do_OP_ADD = make_bin_op(lambda x,y: x+y)
do_OP_SUB = make_bin_op(lambda x,y: x-y)
do_OP_MUL = make_bin_op(lambda x,y: x*y)
do_OP_DIV = make_bin_op(lambda x,y: x//y)
do_OP_MOD = make_bin_op(lambda x,y: x%y)
do_OP_LSHIFT = make_bin_op(lambda x,y: x<<y)
do_OP_RSHIFT = make_bin_op(lambda x,y: x>>y)
do_OP_BOOLAND = make_bin_op(lambda x,y: x and y)
do_OP_BOOLOR = make_bin_op(lambda x,y: x or y)
do_OP_NUMEQUAL = make_bin_op(lambda x,y: x==y)
do_OP_NUMEQUALVERIFY = make_bin_op(lambda x,y: x==y)
do_OP_NUMNOTEQUAL = make_bin_op(lambda x,y: x!=y)
do_OP_LESSTHAN = make_bin_op(lambda x,y: x<y)
do_OP_GREATERTHAN = make_bin_op(lambda x,y: x>y)
do_OP_LESSTHANOREQUAL = make_bin_op(lambda x,y: x<=y)
do_OP_GREATERTHANOREQUAL = make_bin_op(lambda x,y: x>=y)
do_OP_MIN = make_bin_op(min)
do_OP_MAX = make_bin_op(max)

def do_OP_WITHIN(stack):
    """
    >>> s = [b'c', b'b', b'a']
    >>> do_OP_WITHIN(s)
    >>> print(s == [VCH_TRUE])
    True
    >>> s = [b'b', b'c', b'a']
    >>> do_OP_WITHIN(s)
    >>> print(s == [VCH_FALSE])
    True
    """
    v3 = stack.pop()
    v2 = stack.pop()
    v1 = stack.pop()
    ok = (v3 <= v2 <= v1)
    stack.append(make_bool(ok))

def do_OP_RIPEMD160(stack):
    """
    >>> s = [b'foo']
    >>> do_OP_RIPEMD160(s)
    >>> print(s == [bytearray([66, 207, 162, 17, 1, 142, 164, 146, 253, 238, 69, 172, 99, 123, 121, 114, 160, 173, 104, 115])])
    True
    """
    stack.append(ripemd160(stack.pop()).digest())

def do_OP_SHA1(stack):
    """
    >>> s = [b'foo']
    >>> do_OP_SHA1(s)
    >>> print(s == [bytearray([11, 238, 199, 181, 234, 63, 15, 219, 201, 93, 13, 212, 127, 60, 91, 194, 117, 218, 138, 51])])
    True
    """
    stack.append(hashlib.sha1(stack.pop()).digest())

def do_OP_SHA256(stack):
    """
    >>> s = [b'foo']
    >>> do_OP_SHA256(s)
    >>> print(s == [bytearray([44, 38, 180, 107, 104, 255, 198, 143, 249, 155, 69, 60, 29, 48, 65, 52, 19, 66, 45, 112, 100, 131, 191, 160, 249, 138, 94, 136, 98, 102, 231, 174])])
    True
    """
    stack.append(hashlib.sha256(stack.pop()).digest())

def do_OP_HASH160(stack):
    """
    >>> s = [b'foo']
    >>> do_OP_HASH160(s)
    >>> print(s == [bytearray([225, 207, 124, 129, 3, 71, 107, 109, 127, 233, 228, 151, 154, 161, 14, 124, 83, 31, 207, 66])])
    True
    """
    stack.append(hash160(stack.pop()))

def do_OP_HASH256(stack):
    """
    >>> s = [b'foo']
    >>> do_OP_HASH256(s)
    >>> print(s == [bytearray([199, 173, 232, 143, 199, 162, 20, 152, 166, 165, 229, 195, 133, 225, 246, 139, 237, 130, 43, 114, 170, 99, 196, 169, 164, 138, 2, 194, 70, 110, 226, 158])])
    True
    """
    stack.append(double_sha256(stack.pop()))

def make_unary_num_op(unary_f):
    def f(stack):
        stack.append(int_to_bytes(unary_f(bytes_to_int(stack.pop()))))
    return f

do_OP_1ADD = make_unary_num_op(lambda x: x+1)
do_OP_1SUB = make_unary_num_op(lambda x: x-1)
do_OP_2MUL = make_unary_num_op(lambda x: x<<1)
do_OP_2DIV = make_unary_num_op(lambda x: x>>1)
do_OP_NEGATE = make_unary_num_op(lambda x: -x)
do_OP_ABS = make_unary_num_op(lambda x: abs(x))
do_OP_NOT = make_unary_num_op(lambda x: make_bool(x == 0))
do_OP_0NOTEQUAL = make_unary_num_op(lambda x: make_bool(x != 0))

def build_ops_lookup():
    d = {}
    the_globals = globals()
    for opcode_name, opcode_int in OPCODE_TO_INT.items():
        do_f_name = "do_%s" % opcode_name
        if do_f_name in the_globals:
            d[opcode_int] = the_globals[do_f_name]
    return d

MICROCODE_LOOKUP = build_ops_lookup()

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = opcodes
# -*- coding: utf-8 -*-
"""
Enumerate the opcodes of the Bitcoin VM.


The MIT License (MIT)

Copyright (c) 2013 by Richard Kiss

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

OPCODE_LIST = [
  ("OP_0", 0),
  ("OP_PUSHDATA1", 76),
  ("OP_PUSHDATA2", 77),
  ("OP_PUSHDATA4", 78),
  ("OP_1NEGATE", 79),
  ("OP_RESERVED", 80),
  ("OP_1", 81),
  ("OP_2", 82),
  ("OP_3", 83),
  ("OP_4", 84),
  ("OP_5", 85),
  ("OP_6", 86),
  ("OP_7", 87),
  ("OP_8", 88),
  ("OP_9", 89),
  ("OP_10", 90),
  ("OP_11", 91),
  ("OP_12", 92),
  ("OP_13", 93),
  ("OP_14", 94),
  ("OP_15", 95),
  ("OP_16", 96),
  ("OP_NOP", 97),
  ("OP_VER", 98),
  ("OP_IF", 99),
  ("OP_NOTIF", 100),
  ("OP_VERIF", 101),
  ("OP_VERNOTIF", 102),
  ("OP_ELSE", 103),
  ("OP_ENDIF", 104),
  ("OP_VERIFY", 105),
  ("OP_RETURN", 106),
  ("OP_TOALTSTACK", 107),
  ("OP_FROMALTSTACK", 108),
  ("OP_2DROP", 109),
  ("OP_2DUP", 110),
  ("OP_3DUP", 111),
  ("OP_2OVER", 112),
  ("OP_2ROT", 113),
  ("OP_2SWAP", 114),
  ("OP_IFDUP", 115),
  ("OP_DEPTH", 116),
  ("OP_DROP", 117),
  ("OP_DUP", 118),
  ("OP_NIP", 119),
  ("OP_OVER", 120),
  ("OP_PICK", 121),
  ("OP_ROLL", 122),
  ("OP_ROT", 123),
  ("OP_SWAP", 124),
  ("OP_TUCK", 125),
  ("OP_CAT", 126),
  ("OP_SUBSTR", 127),
  ("OP_LEFT", 128),
  ("OP_RIGHT", 129),
  ("OP_SIZE", 130),
  ("OP_INVERT", 131),
  ("OP_AND", 132),
  ("OP_OR", 133),
  ("OP_XOR", 134),
  ("OP_EQUAL", 135),
  ("OP_EQUALVERIFY", 136),
  ("OP_RESERVED1", 137),
  ("OP_RESERVED2", 138),
  ("OP_1ADD", 139),
  ("OP_1SUB", 140),
  ("OP_2MUL", 141),
  ("OP_2DIV", 142),
  ("OP_NEGATE", 143),
  ("OP_ABS", 144),
  ("OP_NOT", 145),
  ("OP_0NOTEQUAL", 146),
  ("OP_ADD", 147),
  ("OP_SUB", 148),
  ("OP_MUL", 149),
  ("OP_DIV", 150),
  ("OP_MOD", 151),
  ("OP_LSHIFT", 152),
  ("OP_RSHIFT", 153),
  ("OP_BOOLAND", 154),
  ("OP_BOOLOR", 155),
  ("OP_NUMEQUAL", 156),
  ("OP_NUMEQUALVERIFY", 157),
  ("OP_NUMNOTEQUAL", 158),
  ("OP_LESSTHAN", 159),
  ("OP_GREATERTHAN", 160),
  ("OP_LESSTHANOREQUAL", 161),
  ("OP_GREATERTHANOREQUAL", 162),
  ("OP_MIN", 163),
  ("OP_MAX", 164),
  ("OP_WITHIN", 165),
  ("OP_RIPEMD160", 166),
  ("OP_SHA1", 167),
  ("OP_SHA256", 168),
  ("OP_HASH160", 169),
  ("OP_HASH256", 170),
  ("OP_CODESEPARATOR", 171),
  ("OP_CHECKSIG", 172),
  ("OP_CHECKSIGVERIFY", 173),
  ("OP_CHECKMULTISIG", 174),
  ("OP_CHECKMULTISIGVERIFY", 175),
  ("OP_NOP1", 176),
  ("OP_NOP2", 177),
  ("OP_NOP3", 178),
  ("OP_NOP4", 179),
  ("OP_NOP5", 180),
  ("OP_NOP6", 181),
  ("OP_NOP7", 182),
  ("OP_NOP8", 183),
  ("OP_NOP9", 184),
  ("OP_NOP10", 185),
  ("OP_PUBKEYHASH", 253),
  ("OP_PUBKEY", 254),
  ("OP_INVALIDOPCODE", 255),
]

OPCODE_TO_INT = dict(o for o in OPCODE_LIST)

INT_TO_OPCODE = dict(reversed(i) for i in OPCODE_LIST)

def populate_module():
    """Make all the opcodes globals in this module to make it possible to
    use constructs like opcodes.OP_PUBKEY"""
    g = globals()
    for opcode, val in OPCODE_LIST:
        g[opcode] = val

populate_module()

########NEW FILE########
__FILENAME__ = solvers
# -*- coding: utf-8 -*-
"""
Solvers figure out what input script signs a given output script.


The MIT License (MIT)

Copyright (c) 2013 by Richard Kiss

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import binascii

from ... import ecdsa
from ... import networks
from ...encoding import public_pair_to_sec, hash160, is_sec_compressed, sec_to_public_pair,\
    hash160_sec_to_bitcoin_address, public_pair_to_bitcoin_address,\
    public_pair_to_hash160_sec

from . import der
from . import opcodes
from . import tools

bytes_from_int = chr if bytes == str else lambda x: bytes([x])


TEMPLATES = [
    ("coinbase", tools.compile("OP_PUBKEY OP_CHECKSIG")),
    ("standard", tools.compile("OP_DUP OP_HASH160 OP_PUBKEYHASH OP_EQUALVERIFY OP_CHECKSIG")),
    ("pay_to_script", tools.compile("OP_HASH160 OP_PUBKEYHASH OP_EQUAL"))
]


class SolvingError(Exception):
    pass


def match_script_to_templates(script):
    """
    Examine the script passed in by tx_out_script and see if it
    matches the form of one of the templates in TEMPLATES. If so,
    return the form it matches; otherwise, return None.
    """

    for name, template in TEMPLATES:
        r = []
        pc1 = pc2 = 0
        while 1:
            if pc1 == len(script) and pc2 == len(template):
                return name, r
            if pc1 >= len(script) or pc2 >= len(template):
                break
            opcode1, data1, pc1 = tools.get_opcode(script, pc1)
            opcode2, data2, pc2 = tools.get_opcode(template, pc2)
            if opcode2 == opcodes.OP_PUBKEY:
                l1 = len(data1)
                if l1 < 33 or l1 > 120:
                    break
                r.append((opcode2, data1))
            elif opcode2 == opcodes.OP_PUBKEYHASH:
                if len(data1) != 160/8:
                    break
                r.append((opcode2, data1))
            elif (opcode1, data1) != (opcode2, data2):
                break
    raise SolvingError("don't recognize output script")


def script_type_and_hash160(script):
    name, r = match_script_to_templates(script)
    if r[0][0] == opcodes.OP_PUBKEYHASH:
        return name, r[0][1]
    if r[0][0] == opcodes.OP_PUBKEY:
        return name, hash160(r[0][1])
    raise SolvingError("don't recognize output script")


def payable_address_for_script(script, netcode="BTC"):
    """
    Return the payment type and the hash160 for a given script.
    The payment type is one of "coinbase", "standard", "pay_to_script".
    """
    try:
        name, the_hash160 = script_type_and_hash160(script)
    except SolvingError:
        return None

    if name == "pay_to_script":
        address_prefix = networks.pay_to_script_prefix_for_netcode(netcode)
    else:
        address_prefix = networks.address_prefix_for_netcode(netcode)
    return hash160_sec_to_bitcoin_address(the_hash160, address_prefix=address_prefix)


def canonical_solver(tx_out_script, signature_hash, signature_type, hash160_lookup):
    """
    Figure out how to create a signature for the incoming transaction, and sign it.

    tx_out_script: the tx_out script that needs to be "solved"
    signature_hash: the bignum hash value of the new transaction reassigning the coins
    signature_type: always SIGHASH_ALL (1)
    """

    if signature_hash == 0:
        raise SolvingError("signature_hash can't be 0")

    name, opcode_value_list = match_script_to_templates(tx_out_script)

    ba = bytearray()

    order = ecdsa.generator_secp256k1.order()

    compressed = True
    for opcode, v in opcode_value_list:
        if opcode == opcodes.OP_PUBKEY:
            v = hash160(v)
        elif opcode != opcodes.OP_PUBKEYHASH:
            raise SolvingError("can't determine how to sign this script")
        result = hash160_lookup.get(v)
        if result is None:
            bitcoin_address = hash160_sec_to_bitcoin_address(v)
            raise SolvingError("can't determine private key for %s" % bitcoin_address)
        secret_exponent, public_pair, compressed = result
        r,s = ecdsa.sign(ecdsa.generator_secp256k1, secret_exponent, signature_hash)
        if s + s > order:
            s = order - s
        sig = der.sigencode_der(r, s) + bytes_from_int(signature_type)
        ba += tools.compile(binascii.hexlify(sig).decode("utf8"))
        if opcode == opcodes.OP_PUBKEYHASH:
            ba += tools.compile(binascii.hexlify(public_pair_to_sec(public_pair, compressed=compressed)).decode("utf8"))

    return bytes(ba)


def build_hash160_lookup_db(secret_exponents):
    d = {}
    for secret_exponent in secret_exponents:
        public_pair = ecdsa.public_pair_for_secret_exponent(ecdsa.generator_secp256k1, secret_exponent)
        for compressed in (True, False):
            hash160 = public_pair_to_hash160_sec(public_pair, compressed=compressed)
            d[hash160] = (secret_exponent, public_pair, compressed)
    return d

########NEW FILE########
__FILENAME__ = tools
# -*- coding: utf-8 -*-
"""
Some tools for traversing Bitcoin VM scripts.


The MIT License (MIT)

Copyright (c) 2013 by Richard Kiss

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import binascii
import io
import logging

from .opcodes import OPCODE_TO_INT, INT_TO_OPCODE

bytes_from_int = chr if bytes == str else lambda x: bytes([x])
bytes_to_ints = (lambda x: (ord(c) for c in x)) if bytes == str else lambda x: x

if hasattr(int, "to_bytes"):
    int_to_bytes = lambda v: v.to_bytes((v.bit_length()+7)//8, byteorder="big")
else:
    def int_to_bytes(v):
        l = bytearray()
        while v > 0:
            v, mod = divmod(v, 256)
            l.append(mod)
        l.reverse()
        return bytes(l)

if hasattr(int, "from_bytes"):
    bytes_to_int = lambda v: int.from_bytes(v, byteorder="big")
else:
    def bytes_to_int(s):
        v = 0
        b = 0
        for c in bytes_to_ints(s):
            v += (c << b)
            b += 8
        return v

def get_opcode(script, pc):
    """Step through the script, returning a tuple with the next opcode, the next
    piece of data (if the opcode represents data), and the new PC."""
    opcode = ord(script[pc:pc+1])
    pc += 1
    data = b''
    if opcode <= OPCODE_TO_INT["OP_PUSHDATA4"]:
        if opcode < OPCODE_TO_INT["OP_PUSHDATA1"]:
            size = opcode
        elif opcode == OPCODE_TO_INT["OP_PUSHDATA1"]:
            size = bytes_to_int(script[pc:pc+1])
            pc += 1
        elif opcode == OPCODE_TO_INT["OP_PUSHDATA2"]:
            size = bytes_to_int(script[pc:pc+2])
            pc += 2
        elif opcode == OPCODE_TO_INT["OP_PUSHDATA4"]:
            size = bytes_to_int(script[pc:pc+4])
            pc += 4
        data = script[pc:pc+size]
        pc += size
    return opcode, data, pc

def compile(s):
    """Compile the given script. Returns a bytes object with the compiled script."""
    f = io.BytesIO()
    for t in s.split():
        if t in OPCODE_TO_INT:
            f.write(bytes_from_int(OPCODE_TO_INT[t]))
        elif ("OP_%s" % t) in OPCODE_TO_INT:
            f.write(bytes_from_int(OPCODE_TO_INT["OP_%s" % t]))
        else:
            if (t[0], t[-1]) == ('[', ']'):
                t = t[1:-1]
            if len(t) == 1:
                t = "0" + t
            t = binascii.unhexlify(t.encode("utf8"))
            if len(t) == 1 and bytes_to_ints(t)[0] < 16:
                f.write(OPCODE_TO_INT["OP_%d" % t])
            elif len(t) <= 75:
                f.write(bytes_from_int(len(t)))
                f.write(t)
            # BRAIN DAMAGE: if len(t) is too much, we need a different opcode
            # This will never be used in practice as it makes the scripts too long.
    return f.getvalue()

def opcode_list(script):
    """Disassemble the given script. Returns a list of opcodes."""
    opcodes = []
    pc = 0
    while pc < len(script):
        opcode, data, pc = get_opcode(script, pc)
        if len(data) > 0:
            opcodes.append(binascii.hexlify(data).decode("utf8"))
            continue
        if not opcode in INT_TO_OPCODE:
            logging.info("missing opcode %r", opcode)
            continue
        opcodes.append(INT_TO_OPCODE[opcode])
    return opcodes

def disassemble(script):
    """Disassemble the given script. Returns a string."""
    return ' '.join(opcode_list(script))

def delete_subscript(script, subscript):
    """Returns a script with the given subscript removed. The subscript
    must appear in the main script aligned to opcode boundaries for it
    to be removed."""
    new_script = bytearray()
    pc = 0
    size = len(subscript)
    while pc < len(script):
        if script[pc:pc+size] == subscript:
            pc += size
            continue
        opcode, data, pc = get_opcode(script, pc)
        new_script.append(opcode)
        new_script += data
    return bytes(new_script)

########NEW FILE########
__FILENAME__ = vm
# -*- coding: utf-8 -*-
"""
Parse, stream, create, sign and verify Bitcoin transactions as Tx structures.


The MIT License (MIT)

Copyright (c) 2013 by Richard Kiss

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import logging

from ... import ecdsa
from ...encoding import sec_to_public_pair

from . import der
from . import opcodes
from . import ScriptError

from .microcode import MICROCODE_LOOKUP, VCH_TRUE, make_bool
from .tools import get_opcode

VERIFY_OPS = frozenset((opcodes.OPCODE_TO_INT[s] for s in "OP_NUMEQUALVERIFY OP_EQUALVERIFY OP_CHECKSIGVERIFY OP_VERIFY OP_CHECKMULTISIGVERIFY".split()))

INVALID_OPCODE_VALUES = frozenset((opcodes.OPCODE_TO_INT[s] for s in "OP_CAT OP_SUBSTR OP_LEFT OP_RIGHT OP_INVERT OP_AND OP_OR OP_XOR OP_2MUL OP_2DIV OP_MUL OP_DIV OP_MOD OP_LSHIFT OP_RSHIFT".split()))

def check_signature(script, signature_hash, public_key_blob, sig_blob, hash_type):
    """Ensure the given transaction has the correct signature. Invoked by the VM.
    Adapted from official Bitcoin-QT client.

    script: the script that is claimed to unlock the coins used in this transaction
    signature_hash: the signature hash of the transaction being verified
    public_key_blob: the blob representing the SEC-encoded public pair
    sig_blob: the blob representing the DER-encoded signature
    hash_type: expected signature_type (or 0 for wild card)
    """
    signature_type = ord(sig_blob[-1:])
    if signature_type != 1:
        raise ScriptError("unknown signature type %d" % signature_type)
    sig_pair = der.sigdecode_der(sig_blob[:-1])
    if hash_type == 0:
        hash_type = signature_type
    elif hash_type != signature_type:
        raise ScriptError("wrong hash type")
    public_pair = sec_to_public_pair(public_key_blob)
    v = ecdsa.verify(ecdsa.generator_secp256k1, public_pair, signature_hash, sig_pair)
    return make_bool(v)

def eval_script(script, signature_hash, hash_type, stack=[]):
    altstack = []
    if len(script) > 10000:
        return False

    pc = 0
    begin_code_hash = pc
    if_condition = None # or True or False

    try:
        while pc < len(script):
            opcode, data, pc = get_opcode(script, pc)
            if len(data) > 0:
                stack.append(data)
                continue

            # deal with if_condition first

            if if_condition is not None:
                # TODO: fix IF (which doesn't properly nest)
                if opcode == opcodes.OP_ELSE:
                    if_condition = not if_condition
                    continue
                if opcode == opcodes.OP_ENDIF:
                    if_condition = None
                    continue
                if not if_condition:
                    continue
            if opcode in (opcodes.OP_IF, opcodes.OP_NOTIF):
                if_condition = (stack.pop() == VCH_TRUE)
                continue

            if opcode == opcodes.OP_CODESEPARATOR:
                begin_code_hash = pc - 1
                continue

            if opcode in INVALID_OPCODE_VALUES:
                raise ScriptError("invalid opcode %s at %d" % (opcodes.INT_TO_OPCODE[opcode], pc-1))

            if opcode in MICROCODE_LOOKUP:
                MICROCODE_LOOKUP[opcode](stack)
                if opcode in VERIFY_OPS:
                    v = stack.pop()
                    if v != VCH_TRUE:
                        raise ScriptError("VERIFY failed at %d" % (pc-1))
                continue

            if opcode == opcodes.OP_TOALTSTACK:
                altstack.append(stack.pop())
                continue

            if opcode == opcodes.OP_FROMALTSTACK:
                stack.append(altstack.pop())
                continue

            if opcode >= opcodes.OP_1NEGATE and opcode <= opcodes.OP_16:
                stack.append(opcode + 1 - opcodes.OP_1)
                continue

            if opcode in (opcodes.OP_ELSE, opcodes.OP_ENDIF):
                raise ScriptError("%s without OP_IF" % opcodes.INT_TO_OPCODE[opcode])

            if opcode in (opcodes.OP_CHECKSIG, opcodes.OP_CHECKSIGVERIFY):
                public_key_blob = stack.pop()
                sig_blob = stack.pop()
                v = check_signature(script, signature_hash, public_key_blob, sig_blob, hash_type)
                stack.append(v)
                if opcode == opcodes.OP_CHECKSIGVERIFY:
                    if stack.pop() != VCH_TRUE:
                        raise ScriptError("VERIFY failed at %d" % pc-1)
                continue

            # BRAIN DAMAGE -- does it always get down here for each verify op? I think not
            if opcode in VERIFY_OPS:
                v = stack.pop()
                if v != VCH_TRUE:
                    raise ScriptError("VERIFY failed at %d" % pc-1)

            logging.error("can't execute opcode %s", opcode)

    except Exception:
        logging.exception("script failed")

    return len(stack) != 0

def verify_script(script_signature, script_public_key, signature_hash, hash_type=0):
    stack = []
    if not eval_script(script_signature, signature_hash, hash_type, stack):
        logging.debug("script_signature did not evaluate")
        return False
    if not eval_script(script_public_key, signature_hash, hash_type, stack):
        logging.debug("script_public_key did not evaluate")
        return False

    return stack[-1] == VCH_TRUE

########NEW FILE########
__FILENAME__ = Spendable
import binascii

from ..convention import satoshi_to_mbtc
from ..serialize import b2h, b2h_rev, h2b_rev
from ..serialize.bitcoin_streamer import parse_struct, stream_struct

from .TxIn import TxIn
from .TxOut import TxOut


class Spendable(TxOut):
    def __init__(self, coin_value, script, tx_hash, tx_out_index):
        self.coin_value = int(coin_value)
        self.script = script
        self.tx_hash = tx_hash
        self.tx_out_index = tx_out_index

    def stream(self, f, as_spendable=False):
        super(Spendable, self).stream(f)
        if as_spendable:
            stream_struct("#L", f, self.previous_hash, self.previous_index)

    @classmethod
    def parse(class_, f):
        return class_(*parse_struct("QS#L", f))

    def as_dict(self):
        # for use with JSON
        return dict(
            coin_value=self.coin_value,
            script_hex=binascii.hexlify(self.script),
            tx_hash_hex=binascii.hexlify(self.tx_hash),
            tx_out_index=self.tx_out_index
        )

    @classmethod
    def from_dict(class_, d):
        return class_(d["coin_value"], binascii.unhexlify(d["script_hex"]),
                      binascii.unhexlify(d["tx_hash_hex"]), d["tx_out_index"])

    def as_text(self):
        return "/".join([b2h_rev(self.tx_hash), str(self.tx_out_index),
                         b2h(self.script), str(self.coin_value)])

    @classmethod
    def from_text(class_, text):
        tx_hash_hex, tx_out_index_str, script_hex, coin_value = text.split("/")
        tx_hash = h2b_rev(tx_hash_hex)
        tx_out_index = int(tx_out_index_str)
        script = binascii.unhexlify(script_hex)
        coin_value = int(coin_value)
        return class_(coin_value, script, tx_hash, tx_out_index)

    def tx_in(self, script=b'', sequence=4294967295):
        return TxIn(self.tx_hash, self.tx_out_index, script, sequence)

    def __str__(self):
        return 'Spendable<%s mbtc "%s:%d">' % (
            satoshi_to_mbtc(self.coin_value), b2h_rev(self.tx_hash), self.tx_out_index)

    def __repr__(self):
        return str(self)

########NEW FILE########
__FILENAME__ = Tx
# -*- coding: utf-8 -*-
"""
Parse, stream, create, sign and verify Bitcoin transactions as Tx structures.


The MIT License (MIT)

Copyright (c) 2013 by Richard Kiss

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import io

from ..encoding import double_sha256, from_bytes_32
from ..serialize import b2h, b2h_rev, h2b, h2b_rev
from ..serialize.bitcoin_streamer import parse_struct, stream_struct

from .TxIn import TxIn
from .TxOut import TxOut
from .Spendable import Spendable

from .script import opcodes
from .script import tools
from .script.solvers import canonical_solver, SolvingError

SIGHASH_ALL = 1
SIGHASH_NONE = 2
SIGHASH_SINGLE = 3
SIGHASH_ANYONECANPAY = 0x80


class ValidationFailureError(Exception):
    pass


class BadSpendableError(Exception):
    pass


class Tx(object):
    @classmethod
    def coinbase_tx(class_, public_key_sec, coin_value, coinbase_bytes=b'', version=1, lock_time=0):
        """
        Create the special "first in block" transaction that includes the mining fees.
        """
        tx_in = TxIn.coinbase_tx_in(script=coinbase_bytes)
        COINBASE_SCRIPT_OUT = "%s OP_CHECKSIG"
        script_text = COINBASE_SCRIPT_OUT % b2h(public_key_sec)
        script_bin = tools.compile(script_text)
        tx_out = TxOut(coin_value, script_bin)
        return class_(version, [tx_in], [tx_out], lock_time)

    @classmethod
    def parse(class_, f):
        """Parse a Bitcoin transaction Tx from the file-like object f."""
        version, count = parse_struct("LI", f)
        txs_in = []
        for i in range(count):
            txs_in.append(TxIn.parse(f))
        count, = parse_struct("I", f)
        txs_out = []
        for i in range(count):
            txs_out.append(TxOut.parse(f))
        lock_time, = parse_struct("L", f)
        return class_(version, txs_in, txs_out, lock_time)

    @classmethod
    def tx_from_hex(class_, hex_string):
        """Return the Tx for the given hex string."""
        return class_.parse(io.BytesIO(h2b(hex_string)))

    def __init__(self, version, txs_in, txs_out, lock_time=0, unspents=[]):
        self.version = version
        self.txs_in = txs_in
        self.txs_out = txs_out
        self.lock_time = lock_time
        self.unspents = unspents

    def stream(self, f):
        """Stream a Bitcoin transaction Tx to the file-like object f."""
        stream_struct("LI", f, self.version, len(self.txs_in))
        for t in self.txs_in:
            t.stream(f)
        stream_struct("I", f, len(self.txs_out))
        for t in self.txs_out:
            t.stream(f)
        stream_struct("L", f, self.lock_time)

    def as_hex(self, include_unspents=False):
        """Return the transaction as hex."""
        f = io.BytesIO()
        self.stream(f)
        if include_unspents and not self.missing_unspents():
            self.stream_unspents(f)
        return b2h(f.getvalue())

    def hash(self, hash_type=None):
        """Return the hash for this Tx object."""
        s = io.BytesIO()
        self.stream(s)
        if hash_type:
            stream_struct("L", s, hash_type)
        return double_sha256(s.getvalue())

    def id(self):
        """Return the human-readable hash for this Tx object."""
        return b2h_rev(self.hash())

    def signature_hash(self, tx_out_script, unsigned_txs_out_idx, hash_type):
        """
        Return the canonical hash for a transaction. We need to
        remove references to the signature, since it's a signature
        of the hash before the signature is applied.

        tx_out_script: the script the coins for unsigned_txs_out_idx are coming from
        unsigned_txs_out_idx: where to put the tx_out_script
        hash_type: always seems to be SIGHASH_ALL
        """

        # In case concatenating two scripts ends up with two codeseparators,
        # or an extra one at the end, this prevents all those possible incompatibilities.
        tx_out_script = tools.delete_subscript(tx_out_script, [opcodes.OP_CODESEPARATOR])

        # blank out other inputs' signatures
        def tx_in_for_idx(idx, tx_in):
            if idx == unsigned_txs_out_idx:
                return TxIn(tx_in.previous_hash, tx_in.previous_index, tx_out_script, tx_in.sequence)
            return TxIn(tx_in.previous_hash, tx_in.previous_index, b'', tx_in.sequence)

        txs_in = [tx_in_for_idx(i, tx_in) for i, tx_in in enumerate(self.txs_in)]
        txs_out = self.txs_out

        # Blank out some of the outputs
        if (hash_type & 0x1f) == SIGHASH_NONE:
            # Wildcard payee
            txs_out = []

            # Let the others update at will
            for i in range(len(txs_in)):
                if i != unsigned_txs_out_idx:
                    txs_in[i].sequence = 0

        elif (hash_type & 0x1f) == SIGHASH_SINGLE:
            # Only lockin the txout payee at same index as txin
            # BRAIN DAMAGE: this probably doesn't work right
            txs_out = [TxOut(-1, b'')] * unsigned_txs_out_idx
            txs_out.append(self.txs_out[unsigned_txs_out_idx])

            # Let the others update at will
            # BRAIN DAMAGE: this probably doesn't work
            for i in range(len(self.txs_in)):
                if i != unsigned_txs_out_idx:
                    txs_in[i].sequence = 0

        # Blank out other inputs completely, not recommended for open transactions
        if hash_type & SIGHASH_ANYONECANPAY:
            txs_in = [txs_in[unsigned_txs_out_idx]]

        tmp_tx = Tx(self.version, txs_in, txs_out, self.lock_time)
        return from_bytes_32(tmp_tx.hash(hash_type=hash_type))

    def sign_tx_in(self, hash160_lookup, tx_in_idx, tx_out_script, hash_type=SIGHASH_ALL):
        """
        Sign a standard transaction.
        hash160_lookup:
            An object with a get method that accepts a hash160 and returns the
            corresponding (secret exponent, public_pair, is_compressed) tuple or
            None if it's unknown (in which case the script will obviously not be signed).
            A standard dictionary will do nicely here.
        tx_in_idx:
            the index of the tx_in we are currently signing
        tx_out:
            the tx_out referenced by the given tx_in
        """

        tx_in = self.txs_in[tx_in_idx]

        # Leave out the signature from the hash, since a signature can't sign itself.
        # The checksig op will also drop the signatures from its hash.
        signature_hash = self.signature_hash(tx_out_script, tx_in_idx, hash_type=hash_type)
        if tx_in.verify(tx_out_script, signature_hash, hash_type=0):
            return

        tx_in.script = canonical_solver(tx_out_script, signature_hash, hash_type, hash160_lookup)
        if not tx_in.verify(tx_out_script, signature_hash, hash_type=0):
            raise ValidationFailureError(
                "just signed script Tx %s TxIn index %d did not verify" % (
                    b2h_rev(tx_in.previous_hash), tx_in_idx))

    def total_out(self):
        return sum(tx_out.coin_value for tx_out in self.txs_out)

    def tx_outs_as_spendable(self):
        h = self.hash()
        return [
            Spendable(tx_out.coin_value, tx_out.script, h, tx_out_index)
            for tx_out_index, tx_out in enumerate(self.txs_out)]

    def is_coinbase(self):
        return len(self.txs_in) == 1 and self.txs_in[0].is_coinbase()

    def __str__(self):
        return "Tx [%s]" % self.id()

    def __repr__(self):
        return "Tx [%s] (v:%d) [%s] [%s]" % (
            self.id(), self.version, ", ".join(str(t) for t in self.txs_in),
            ", ".join(str(t) for t in self.txs_out))

    """
    The functions below here deal with an optional additional parameter: "unspents".
    This parameter is a list of tx_out objects that are referenced by the
    list of self.tx_in objects.
    """

    def unspents_from_db(self, tx_db, ignore_missing=False):
        unspents = []
        for tx_in in self.txs_in:
            tx = tx_db.get(tx_in.previous_hash)
            if tx and tx.hash() == tx_in.previous_hash:
                unspents.append(tx.txs_out[tx_in.previous_index])
            elif ignore_missing:
                unspents.append(None)
            else:
                raise KeyError(
                    "can't find tx_out for %s:%d" % (b2h_rev(tx_in.previous_hash), tx_in.previous_index))
        self.unspents = unspents

    def set_unspents(self, unspents):
        if len(unspents) != len(self.txs_in):
            raise ValueError("wrong number of unspents")
        self.unspents = unspents

    def missing_unspent(self, idx):
        if self.is_coinbase():
            return True
        if len(self.unspents) <= idx:
            return True
        return self.unspents[idx] is None

    def missing_unspents(self):
        if self.is_coinbase():
            return False
        return (len(self.unspents) != len(self.txs_in) or
                any(self.missing_unspent(idx) for idx, tx_in in enumerate(self.txs_in)))

    def check_unspents(self):
        if self.missing_unspents():
            raise ValueError("wrong number of unspents. Call unspents_from_db or set_unspents.")

    def txs_in_as_spendable(self):
        return [
            Spendable(tx_out.coin_value, tx_out.script, tx_in.previous_hash, tx_in.previous_index)
            for tx_in_index, (tx_in, tx_out) in enumerate(zip(self.txs_in, self.unspents))]

    def stream_unspents(self, f):
        self.check_unspents()
        for tx_out in self.unspents:
            if tx_out is None:
                tx_out = TxOut(0, b'')
            tx_out.stream(f)

    def parse_unspents(self, f):
        unspents = []
        for i in enumerate(self.txs_in):
            tx_out = TxOut.parse(f)
            if tx_out.coin_value == 0:
                tx_out = None
            unspents.append(tx_out)
        self.set_unspents(unspents)

    def is_signature_ok(self, tx_in_idx):
        tx_in = self.txs_in[tx_in_idx]
        if tx_in.is_coinbase():
            return True
        if len(self.unspents) <= tx_in_idx:
            return False
        unspent = self.unspents[tx_in_idx]
        if unspent is None:
            return False
        tx_out_script = self.unspents[tx_in_idx].script
        signature_hash = self.signature_hash(tx_out_script, tx_in_idx, hash_type=SIGHASH_ALL)
        return tx_in.verify(tx_out_script, signature_hash, hash_type=0)

    def sign(self, hash160_lookup, hash_type=SIGHASH_ALL):
        """
        Sign a standard transaction.
        hash160_lookup:
            A dictionary (or another object with .get) where keys are hash160 and
            values are tuples (secret exponent, public_pair, is_compressed) or None
            (in which case the script will obviously not be signed).
        """
        self.check_unspents()
        for idx, tx_in in enumerate(self.txs_in):
            if self.is_signature_ok(idx) or tx_in.is_coinbase():
                continue
            try:
                if self.unspents[idx]:
                    self.sign_tx_in(hash160_lookup, idx, self.unspents[idx].script, hash_type=hash_type)
            except SolvingError:
                pass

        return self

    def bad_signature_count(self):
        count = 0
        for idx, tx_in in enumerate(self.txs_in):
            if not self.is_signature_ok(idx):
                count += 1
        return count

    def total_in(self):
        if self.is_coinbase():
            return self.txs_out[0].coin_value
        self.check_unspents()
        return sum(tx_out.coin_value for tx_out in self.unspents)

    def fee(self):
        return self.total_in() - self.total_out()

    def validate_unspents(self, tx_db):
        """
        Spendable objects returned from blockchain.info or
        similar services contain coin_value information that must be trusted
        on faith. Mistaken coin_value data can result in coins being wasted
        to fees.

        This function solves this problem by iterating over the incoming
        transactions, fetching them from the tx_db in full, and verifying
        that the coin_values are as expected.

        Returns the fee for this transaction. If any of the spendables set by
        tx.set_unspents do not match the authenticated transactions, a
        ValidationFailureError is raised.
        """
        ZERO = b'\0' * 32
        tx_hashes = set((tx_in.previous_hash for tx_in in self.txs_in))

        # build a local copy of the DB
        tx_lookup = {}
        for h in tx_hashes:
            if h == ZERO:
                continue
            the_tx = tx_db.get(h)
            if the_tx is None:
                raise KeyError("hash id %s not in tx_db" % b2h_rev(h))
            if the_tx.hash() != h:
                raise KeyError("attempt to load Tx %s yielded a Tx with id %s" % (h2b_rev(h), the_tx.id()))
            tx_lookup[h] = the_tx

        for idx, tx_in in enumerate(self.txs_in):
            if tx_in.previous_hash == ZERO:
                continue
            if tx_in.previous_hash not in tx_lookup:
                raise KeyError("hash id %s not in tx_lookup" % b2h_rev(tx_in.previous_hash))
            txs_out = tx_lookup[tx_in.previous_hash].txs_out
            if tx_in.previous_index > len(txs_out):
                raise BadSpendableError("tx_out index %d is too big for Tx %s" %
                                        (tx_in.previous_index, b2h_rev(tx_in.previous_hash)))
            tx_out1 = txs_out[tx_in.previous_index]
            tx_out2 = self.unspents[idx]
            if tx_out1.coin_value != tx_out2.coin_value:
                raise BadSpendableError(
                    "unspents[%d] coin value mismatch (%d vs %d)" % (
                        idx, tx_out1.coin_value, tx_out2.coin_value))
            if tx_out1.script != tx_out2.script:
                raise BadSpendableError("unspents[%d] script mismatch!" % idx)

        return self.fee()

########NEW FILE########
__FILENAME__ = TxIn
# -*- coding: utf-8 -*-
"""
Deal with the part of a Tx that specifies where the Bitcoin comes from.


The MIT License (MIT)

Copyright (c) 2013 by Richard Kiss

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import binascii

from .. import encoding

from ..serialize import b2h, b2h_rev
from ..serialize.bitcoin_streamer import parse_struct, stream_struct

from .script.tools import disassemble, opcode_list
from .script.vm import verify_script

ZERO = b'\0' * 32


class TxIn(object):
    """
    The part of a Tx that specifies where the Bitcoin comes from.
    """
    def __init__(self, previous_hash, previous_index, script=b'', sequence=4294967295):
        self.previous_hash = previous_hash
        self.previous_index = previous_index
        self.script = script
        self.sequence = sequence

    @classmethod
    def coinbase_tx_in(self, script):
        tx = TxIn(previous_hash=ZERO, previous_index=4294967295, script=script)
        return tx

    def stream(self, f):
        stream_struct("#LSL", f, self.previous_hash, self.previous_index, self.script, self.sequence)

    @classmethod
    def parse(self, f):
        return self(*parse_struct("#LSL", f))

    def is_coinbase(self):
        return self.previous_hash == ZERO

    def bitcoin_address(self, address_prefix=b'\0'):
        if self.is_coinbase():
            return "(coinbase)"
        # attempt to return the source address, or None on failure
        opcodes = opcode_list(self.script)
        if len(opcodes) == 2 and opcodes[0].startswith("30"):
            # the second opcode is probably the public key as sec
            sec = binascii.unhexlify(opcodes[1])
            bitcoin_address = encoding.hash160_sec_to_bitcoin_address(
                encoding.hash160(sec), address_prefix=address_prefix)
            return bitcoin_address
        return "(unknown)"

    def verify(self, tx_out_script, signature_hash, hash_type=0):
        """
        Return True or False depending upon whether this TxIn verifies.

        tx_out_script: the script of the TxOut that corresponds to this input
        signature_hash: the hash of the partial transaction
        """
        return verify_script(self.script, tx_out_script, signature_hash, hash_type=hash_type)

    def __str__(self):
        if self.is_coinbase():
            return 'TxIn<COINBASE: %s>' % b2h(self.script)
        return 'TxIn<%s[%d] "%s">' % (
            b2h_rev(self.previous_hash), self.previous_index, disassemble(self.script))

########NEW FILE########
__FILENAME__ = TxOut
# -*- coding: utf-8 -*-
"""
Deal with the part of a Tx that specifies where the Bitcoin goes to.


The MIT License (MIT)

Copyright (c) 2013 by Richard Kiss

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

from ..convention import satoshi_to_mbtc
from ..encoding import bitcoin_address_to_hash160_sec_with_prefix

from ..serialize import b2h
from ..serialize.bitcoin_streamer import parse_struct, stream_struct

from .script import tools
from .script.solvers import payable_address_for_script, script_type_and_hash160


class TxOut(object):
    """
    The part of a Tx that specifies where the Bitcoin goes to.
    """
    def __init__(self, coin_value, script):
        self.coin_value = int(coin_value)
        self.script = script

    def stream(self, f):
        stream_struct("QS", f, self.coin_value, self.script)

    @classmethod
    def parse(self, f):
        return self(*parse_struct("QS", f))

    def __str__(self):
        return 'TxOut<%s mbtc "%s">' % (satoshi_to_mbtc(self.coin_value), tools.disassemble(self.script))

    def bitcoin_address(self, netcode="BTC"):
        # attempt to return the destination address, or None on failure
        return payable_address_for_script(self.script, netcode)

    def hash160(self):
        # attempt to return the destination hash160, or None on failure
        r = script_type_and_hash160(self.script)
        if r:
            return r[1]
        return None


def standard_tx_out_script(bitcoin_address):
    hash160, prefix = bitcoin_address_to_hash160_sec_with_prefix(bitcoin_address)
    STANDARD_SCRIPT_OUT = "OP_DUP OP_HASH160 %s OP_EQUALVERIFY OP_CHECKSIG"
    script_text = STANDARD_SCRIPT_OUT % b2h(hash160)
    return tools.compile(script_text)

########NEW FILE########
__FILENAME__ = tx_utils

from ..encoding import wif_to_secret_exponent
from ..convention import tx_fee

from .Spendable import Spendable
from .Tx import Tx
from .TxOut import TxOut, standard_tx_out_script
from .script.solvers import build_hash160_lookup_db


class SecretExponentMissing(Exception):
    pass


class LazySecretExponentDB(object):
    """
    The pycoin pure python implementation that converts secret exponents
    into public pairs is very slow, so this class does the conversion lazily
    and caches the results to optimize for the case of a large number
    of secret exponents.
    """
    def __init__(self, wif_iterable, secret_exponent_db_cache):
        self.wif_iterable = iter(wif_iterable)
        self.secret_exponent_db_cache = secret_exponent_db_cache

    def get(self, v):
        if v in self.secret_exponent_db_cache:
            return self.secret_exponent_db_cache[v]
        for wif in self.wif_iterable:
            secret_exponent = wif_to_secret_exponent(wif)
            d = build_hash160_lookup_db([secret_exponent])
            self.secret_exponent_db_cache.update(d)
            if v in self.secret_exponent_db_cache:
                return self.secret_exponent_db_cache[v]
        self.wif_iterable = []
        return None


def create_tx(spendables, payables, fee="standard", lock_time=0, version=1):
    """
    This function provides the easiest way to create an unsigned transaction.

    All coin values are in satoshis.

    spendables:
        a list of Spendable objects, which act as inputs. These can
        be either a Spendable or a Spendable.as_text or a Spendable.as_dict
        if you prefer a non-object-based input (which might be easier for
        airgapped transactions, for example).
    payables:
        a list where each entry is a bitcoin address, or a tuple of
        (bitcoin address, coin_value). If the coin_value is missing or
        zero, this address is thrown into the "split pool". Funds not
        explicitly claimed by the fee or a bitcoin address are shared as
        equally as possible among the split pool. [Minor point: if the
        amount to be split does not divide evenly, some of the earlier
        bitcoin addresses will get an extra satoshi.]
    fee:
        a value, or "standard" for it to be calculated.
    version:
        the version to use in the transaction. Normally 1.
    lock_time:
        the lock_time to use in the transaction. Normally 0.

    Returns the unsigned Tx transaction. Note that unspents are set, so the
    transaction can be immediately signed.

    Example:

    tx = create_tx(
        spendables_for_address("1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH"),
        ["1cMh228HTCiwS8ZsaakH8A8wze1JR5ZsP"],
        fee=0)

    This will move all available reported funds from 1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH
    to 1cMh228HTCiwS8ZsaakH8A8wze1JR5ZsP, with no transaction fees (which means it might
    take a while to confirm, possibly never).
    """

    def _fix_spendable(s):
        if isinstance(s, Spendable):
            return s
        if isinstance(s, (type(b''), type(u''))):
            return Spendable.from_text(s)
        return Spendable.from_dict(s)

    spendables = [_fix_spendable(s) for s in spendables]
    txs_in = [spendable.tx_in() for spendable in spendables]

    txs_out = []
    for payable in payables:
        if len(payable) == 2:
            bitcoin_address, coin_value = payable
        else:
            bitcoin_address = payable
            coin_value = 0
        script = standard_tx_out_script(bitcoin_address)
        txs_out.append(TxOut(coin_value, script))

    tx = Tx(version=version, txs_in=txs_in, txs_out=txs_out, lock_time=lock_time)
    tx.set_unspents(spendables)

    distribute_from_split_pool(tx, fee)
    return tx


def distribute_from_split_pool(tx, fee):
    """
    This function looks at TxOut items of a transaction tx and
    and puts TxOut items with a coin value of zero into a "split pool".
    Funds not explicitly claimed by the fee or other TxOut items are
    shared as equally as possible among the split pool. If the amount
    to be split does not divide evenly, some of the earlier TxOut items
    will get an extra satoshi.
    tx:
        the transaction
    fee:
        the reserved fee set aside
    """

    # calculate fees
    if fee == 'standard':
        # TODO: improve this
        # 1: the tx is not fully built out, so it will actually be larger than implied at this point
        # 2: recommended_fee_for_tx gives estimates that are too high
        fee = tx_fee.recommended_fee_for_tx(tx)

    zero_count = sum(1 for tx_out in tx.txs_out if tx_out.coin_value == 0)
    if zero_count > 0:
        total_coin_value = sum(spendable.coin_value for spendable in tx.txs_in_as_spendable())
        coins_allocated = sum(tx_out.coin_value for tx_out in tx.txs_out) + fee
        remaining_coins = total_coin_value - coins_allocated
        if remaining_coins < 0:
            raise ValueError("insufficient inputs for outputs")
        value_each, extra_count = divmod(remaining_coins, zero_count)
        if value_each < 1:
            raise ValueError("not enough to pay nonzero amounts to at least one of the unspecified outputs")
        for tx_out in tx.txs_out:
            if tx_out.coin_value == 0:
                tx_out.coin_value = value_each + (1 if extra_count > 0 else 0)
                extra_count -= 1
    return zero_count


def sign_tx(tx, wifs=[], secret_exponent_db={}):
    """
    This function provides an convenience method to sign a transaction.

    The transaction must have "unspents" set by, for example,
    calling tx.unspents_from_db.

    wifs:
        the list of WIFs required to sign this transaction.
    secret_exponent_db:
        an optional dictionary (or any object with a .get method) that contains
        a bitcoin address => (secret_exponent, public_pair, is_compressed)
        tuple. This will be built automatically lazily with the list of WIFs.
        You can pass in an empty dictionary and as WIFs are processed, they
        will be cached here. If you have multiple transactions to sign, each with
        the same WIF list, passing a cache dictionary in may speed things up a bit.

    Returns the signed Tx transaction, or raises an exception.

    At least one of "wifs" and "secret_exponent_db" must be included for there
    to be any hope of signing the transaction.

    Example:

    sign_tx(wifs=["KwDiBf89QgGbjEhKnhXJuH7LrciVrZi3qYjgd9M7rFU73sVHnoWn"])
    """
    tx.sign(LazySecretExponentDB(wifs, secret_exponent_db))


def create_signed_tx(spendables, payables, wifs=[], fee="standard",
                     lock_time=0, version=1, secret_exponent_db={}):
    """
    This function provides an easy way to create and sign a transaction.

    All coin values are in satoshis.

    spendables, payables, fee, lock_time, version are as in create_tx, above.
    wifs, secret_exponent_db are as in sign_tx, above.

    Returns the signed Tx transaction, or raises an exception.

    At least one of "wifs" and "secret_exponent_db" must be included for there
    to be any hope of signing the transaction.

    Example:

    tx = create_signed_tx(
        spendables_for_address("1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH"),
        ["1cMh228HTCiwS8ZsaakH8A8wze1JR5ZsP"],
        wifs=["KwDiBf89QgGbjEhKnhXJuH7LrciVrZi3qYjgd9M7rFU73sVHnoWn"],
        fee=0)

    This will move all available reported funds from 1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH
    to 1cMh228HTCiwS8ZsaakH8A8wze1JR5ZsP, with no transaction fees (which means it might
    take a while to confirm, possibly never).
    """

    tx = create_tx(spendables, payables, fee=fee, lock_time=lock_time, version=version)
    sign_tx(tx, wifs=wifs, secret_exponent_db=secret_exponent_db)
    for idx, tx_out in enumerate(tx.txs_in):
        if not tx.is_signature_ok(idx):
            raise SecretExponentMissing("failed to sign spendable for %s" %
                                        tx.unspents[idx].bitcoin_address())
    return tx

########NEW FILE########
