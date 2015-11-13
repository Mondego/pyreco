__FILENAME__ = curves
from __future__ import division

from . import der, ecdsa

class UnknownCurveError(Exception):
    pass

def orderlen(order):
    return (1+len("%x"%order))//2 # bytes

# the NIST curves
class Curve:
    def __init__(self, name, curve, generator, oid):
        self.name = name
        self.curve = curve
        self.generator = generator
        self.order = generator.order()
        self.baselen = orderlen(self.order)
        self.verifying_key_length = 2*self.baselen
        self.signature_length = 2*self.baselen
        self.oid = oid
        self.encoded_oid = der.encode_oid(*oid)

NIST192p = Curve("NIST192p", ecdsa.curve_192, ecdsa.generator_192,
                 (1, 2, 840, 10045, 3, 1, 1))
NIST224p = Curve("NIST224p", ecdsa.curve_224, ecdsa.generator_224,
                 (1, 3, 132, 0, 33))
NIST256p = Curve("NIST256p", ecdsa.curve_256, ecdsa.generator_256,
                 (1, 2, 840, 10045, 3, 1, 7))
NIST384p = Curve("NIST384p", ecdsa.curve_384, ecdsa.generator_384,
                 (1, 3, 132, 0, 34))
NIST521p = Curve("NIST521p", ecdsa.curve_521, ecdsa.generator_521,
                 (1, 3, 132, 0, 35))
SECP256k1 = Curve("SECP256k1",
                  ecdsa.curve_secp256k1, ecdsa.generator_secp256k1,
                  (1, 3, 132, 0, 10))

curves = [NIST192p, NIST224p, NIST256p, NIST384p, NIST521p, SECP256k1]

def find_curve(oid_curve):
    for c in curves:
        if c.oid == oid_curve:
            return c
    raise UnknownCurveError("I don't know about the curve with oid %s."
                            "I only know about these: %s" %
                            (oid_curve, [c.name for c in curves]))

########NEW FILE########
__FILENAME__ = der
from __future__ import division

import binascii
import base64
from .six import int2byte, b, PY3, integer_types, text_type

class UnexpectedDER(Exception):
    pass

def encode_constructed(tag, value):
    return int2byte(0xa0+tag) + encode_length(len(value)) + value
def encode_integer(r):
    assert r >= 0 # can't support negative numbers yet
    h = ("%x" % r).encode()
    if len(h) % 2:
        h = b("0") + h
    s = binascii.unhexlify(h)
    num = s[0] if isinstance(s[0], integer_types) else ord(s[0])
    if num <= 0x7f:
        return b("\x02") + int2byte(len(s)) + s
    else:
        # DER integers are two's complement, so if the first byte is
        # 0x80-0xff then we need an extra 0x00 byte to prevent it from
        # looking negative.
        return b("\x02") + int2byte(len(s)+1) + b("\x00") + s

def encode_bitstring(s):
    return b("\x03") + encode_length(len(s)) + s
def encode_octet_string(s):
    return b("\x04") + encode_length(len(s)) + s
def encode_oid(first, second, *pieces):
    assert first <= 2
    assert second <= 39
    encoded_pieces = [int2byte(40*first+second)] + [encode_number(p)
                                                    for p in pieces]
    body = b('').join(encoded_pieces)
    return b('\x06') + encode_length(len(body)) + body
def encode_sequence(*encoded_pieces):
    total_len = sum([len(p) for p in encoded_pieces])
    return b('\x30') + encode_length(total_len) + b('').join(encoded_pieces)
def encode_number(n):
    b128_digits = []
    while n:
        b128_digits.insert(0, (n & 0x7f) | 0x80)
        n = n >> 7
    if not b128_digits:
        b128_digits.append(0)
    b128_digits[-1] &= 0x7f
    return b('').join([int2byte(d) for d in b128_digits])

def remove_constructed(string):
    s0 = string[0] if isinstance(string[0], integer_types) else ord(string[0])
    if (s0 & 0xe0) != 0xa0:
        raise UnexpectedDER("wanted constructed tag (0xa0-0xbf), got 0x%02x"
                            % s0)
    tag = s0 & 0x1f
    length, llen = read_length(string[1:])
    body = string[1+llen:1+llen+length]
    rest = string[1+llen+length:]
    return tag, body, rest

def remove_sequence(string):
    if not string.startswith(b("\x30")):
        n = string[0] if isinstance(string[0], integer_types) else ord(string[0])
        raise UnexpectedDER("wanted sequence (0x30), got 0x%02x" % n)
    length, lengthlength = read_length(string[1:])
    endseq = 1+lengthlength+length
    return string[1+lengthlength:endseq], string[endseq:]

def remove_octet_string(string):
    if not string.startswith(b("\x04")):
        n = string[0] if isinstance(string[0], integer_types) else ord(string[0])
        raise UnexpectedDER("wanted octetstring (0x04), got 0x%02x" % n)
    length, llen = read_length(string[1:])
    body = string[1+llen:1+llen+length]
    rest = string[1+llen+length:]
    return body, rest

def remove_object(string):
    if not string.startswith(b("\x06")):
        n = string[0] if isinstance(string[0], integer_types) else ord(string[0])
        raise UnexpectedDER("wanted object (0x06), got 0x%02x" % n)
    length, lengthlength = read_length(string[1:])
    body = string[1+lengthlength:1+lengthlength+length]
    rest = string[1+lengthlength+length:]
    numbers = []
    while body:
        n, ll = read_number(body)
        numbers.append(n)
        body = body[ll:]
    n0 = numbers.pop(0)
    first = n0//40
    second = n0-(40*first)
    numbers.insert(0, first)
    numbers.insert(1, second)
    return tuple(numbers), rest

def remove_integer(string):
    if not string.startswith(b("\x02")):
        n = string[0] if isinstance(string[0], integer_types) else ord(string[0])
        raise UnexpectedDER("wanted integer (0x02), got 0x%02x" % n)
    length, llen = read_length(string[1:])
    numberbytes = string[1+llen:1+llen+length]
    rest = string[1+llen+length:]
    nbytes = numberbytes[0] if isinstance(numberbytes[0], integer_types) else ord(numberbytes[0])
    assert nbytes < 0x80 # can't support negative numbers yet
    return int(binascii.hexlify(numberbytes), 16), rest

def read_number(string):
    number = 0
    llen = 0
    # base-128 big endian, with b7 set in all but the last byte
    while True:
        if llen > len(string):
            raise UnexpectedDER("ran out of length bytes")
        number = number << 7
        d = string[llen] if isinstance(string[llen], integer_types) else ord(string[llen])
        number += (d & 0x7f)
        llen += 1
        if not d & 0x80:
            break
    return number, llen

def encode_length(l):
    assert l >= 0
    if l < 0x80:
        return int2byte(l)
    s = ("%x" % l).encode()
    if len(s)%2:
        s = b("0")+s
    s = binascii.unhexlify(s)
    llen = len(s)
    return int2byte(0x80|llen) + s

def read_length(string):
    num = string[0] if isinstance(string[0], integer_types) else ord(string[0])
    if not (num & 0x80):
        # short form
        return (num & 0x7f), 1
    # else long-form: b0&0x7f is number of additional base256 length bytes,
    # big-endian
    llen = num & 0x7f
    if llen > len(string)-1:
        raise UnexpectedDER("ran out of length bytes")
    return int(binascii.hexlify(string[1:1+llen]), 16), 1+llen

def remove_bitstring(string):
    num = string[0] if isinstance(string[0], integer_types) else ord(string[0])
    if not string.startswith(b("\x03")):
        raise UnexpectedDER("wanted bitstring (0x03), got 0x%02x" % num)
    length, llen = read_length(string[1:])
    body = string[1+llen:1+llen+length]
    rest = string[1+llen+length:]
    return body, rest

# SEQUENCE([1, STRING(secexp), cont[0], OBJECT(curvename), cont[1], BINTSTRING)


# signatures: (from RFC3279)
#  ansi-X9-62  OBJECT IDENTIFIER ::= {
#       iso(1) member-body(2) us(840) 10045 }
#
#  id-ecSigType OBJECT IDENTIFIER  ::=  {
#       ansi-X9-62 signatures(4) }
#  ecdsa-with-SHA1  OBJECT IDENTIFIER ::= {
#       id-ecSigType 1 }
## so 1,2,840,10045,4,1
## so 0x42, .. ..

#  Ecdsa-Sig-Value  ::=  SEQUENCE  {
#       r     INTEGER,
#       s     INTEGER  }

# id-public-key-type OBJECT IDENTIFIER  ::= { ansi-X9.62 2 }
#
# id-ecPublicKey OBJECT IDENTIFIER ::= { id-publicKeyType 1 }

# I think the secp224r1 identifier is (t=06,l=05,v=2b81040021)
#  secp224r1 OBJECT IDENTIFIER ::= {
#  iso(1) identified-organization(3) certicom(132) curve(0) 33 }
# and the secp384r1 is (t=06,l=05,v=2b81040022)
#  secp384r1 OBJECT IDENTIFIER ::= {
#  iso(1) identified-organization(3) certicom(132) curve(0) 34 }

def unpem(pem):
    if isinstance(pem, text_type):
        pem = pem.encode()

    d = b("").join([l.strip() for l in pem.split(b("\n"))
                    if l and not l.startswith(b("-----"))])
    return base64.b64decode(d)
def topem(der, name):
    b64 = base64.b64encode(der)
    lines = [("-----BEGIN %s-----\n" % name).encode()]
    lines.extend([b64[start:start+64]+b("\n")
                  for start in range(0, len(b64), 64)])
    lines.append(("-----END %s-----\n" % name).encode())
    return b("").join(lines)


########NEW FILE########
__FILENAME__ = ecdsa
#! /usr/bin/env python

"""
Implementation of Elliptic-Curve Digital Signatures.

Classes and methods for elliptic-curve signatures:
private keys, public keys, signatures,
NIST prime-modulus curves with modulus lengths of
192, 224, 256, 384, and 521 bits.

Example:

  # (In real-life applications, you would probably want to
  # protect against defects in SystemRandom.)
  from random import SystemRandom
  randrange = SystemRandom().randrange

  # Generate a public/private key pair using the NIST Curve P-192:

  g = generator_192
  n = g.order()
  secret = randrange( 1, n )
  pubkey = Public_key( g, g * secret )
  privkey = Private_key( pubkey, secret )

  # Signing a hash value:

  hash = randrange( 1, n )
  signature = privkey.sign( hash, randrange( 1, n ) )

  # Verifying a signature for a hash value:

  if pubkey.verifies( hash, signature ):
    print_("Demo verification succeeded.")
  else:
    print_("*** Demo verification failed.")

  # Verification fails if the hash value is modified:

  if pubkey.verifies( hash-1, signature ):
    print_("**** Demo verification failed to reject tampered hash.")
  else:
    print_("Demo verification correctly rejected tampered hash.")

Version of 2009.05.16.

Revision history:
      2005.12.31 - Initial version.
      2008.11.25 - Substantial revisions introducing new classes.
      2009.05.16 - Warn against using random.randrange in real applications.
      2009.05.17 - Use random.SystemRandom by default.

Written in 2005 by Peter Pearson and placed in the public domain.
"""

from .six import int2byte, b, print_
from . import ellipticcurve
from . import numbertheory
import random



class Signature( object ):
  """ECDSA signature.
  """
  def __init__( self, r, s ):
    self.r = r
    self.s = s



class Public_key( object ):
  """Public key for ECDSA.
  """

  def __init__( self, generator, point ):
    """generator is the Point that generates the group,
    point is the Point that defines the public key.
    """

    self.curve = generator.curve()
    self.generator = generator
    self.point = point
    n = generator.order()
    if not n:
      raise RuntimeError("Generator point must have order.")
    if not n * point == ellipticcurve.INFINITY:
      raise RuntimeError("Generator point order is bad.")
    if point.x() < 0 or n <= point.x() or point.y() < 0 or n <= point.y():
      raise RuntimeError("Generator point has x or y out of range.")


  def verifies( self, hash, signature ):
    """Verify that signature is a valid signature of hash.
    Return True if the signature is valid.
    """

    # From X9.62 J.3.1.

    G = self.generator
    n = G.order()
    r = signature.r
    s = signature.s
    if r < 1 or r > n-1: return False
    if s < 1 or s > n-1: return False
    c = numbertheory.inverse_mod( s, n )
    u1 = ( hash * c ) % n
    u2 = ( r * c ) % n
    xy = u1 * G + u2 * self.point
    v = xy.x() % n
    return v == r



class Private_key( object ):
  """Private key for ECDSA.
  """

  def __init__( self, public_key, secret_multiplier ):
    """public_key is of class Public_key;
    secret_multiplier is a large integer.
    """

    self.public_key = public_key
    self.secret_multiplier = secret_multiplier

  def sign( self, hash, random_k ):
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

    G = self.public_key.generator
    n = G.order()
    k = random_k % n
    p1 = k * G
    r = p1.x()
    if r == 0: raise RuntimeError("amazingly unlucky random number r")
    s = ( numbertheory.inverse_mod( k, n ) * \
          ( hash + ( self.secret_multiplier * r ) % n ) ) % n
    if s == 0: raise RuntimeError("amazingly unlucky random number s")
    return Signature( r, s )



def int_to_string( x ):
  """Convert integer x into a string of bytes, as per X9.62."""
  assert x >= 0
  if x == 0: return b('\0')
  result = []
  while x:
    ordinal = x & 0xFF
    result.append(int2byte(ordinal))
    x >>= 8

  result.reverse()
  return b('').join(result)


def string_to_int( s ):
  """Convert a string of bytes into an integer, as per X9.62."""
  result = 0
  for c in s:
    if not isinstance(c, int): c = ord( c )
    result = 256 * result + c
  return result


def digest_integer( m ):
  """Convert an integer into a string of bytes, compute
     its SHA-1 hash, and convert the result to an integer."""
  #
  # I don't expect this function to be used much. I wrote
  # it in order to be able to duplicate the examples
  # in ECDSAVS.
  #
  from hashlib import sha1
  return string_to_int( sha1( int_to_string( m ) ).digest() )


def point_is_valid( generator, x, y ):
  """Is (x,y) a valid public key based on the specified generator?"""

  # These are the tests specified in X9.62.

  n = generator.order()
  curve = generator.curve()
  if x < 0 or n <= x or y < 0 or n <= y:
    return False
  if not curve.contains_point( x, y ):
    return False
  if not n*ellipticcurve.Point( curve, x, y ) == \
     ellipticcurve.INFINITY:
    return False
  return True



# NIST Curve P-192:
_p = 6277101735386680763835789423207666416083908700390324961279
_r = 6277101735386680763835789423176059013767194773182842284081
# s = 0x3045ae6fc8422f64ed579528d38120eae12196d5L
# c = 0x3099d2bbbfcb2538542dcd5fb078b6ef5f3d6fe2c745de65L
_b = 0x64210519e59c80e70fa7e9ab72243049feb8deecc146b9b1
_Gx = 0x188da80eb03090f67cbf20eb43a18800f4ff0afd82ff1012
_Gy = 0x07192b95ffc8da78631011ed6b24cdd573f977a11e794811

curve_192 = ellipticcurve.CurveFp( _p, -3, _b )
generator_192 = ellipticcurve.Point( curve_192, _Gx, _Gy, _r )


# NIST Curve P-224:
_p = 26959946667150639794667015087019630673557916260026308143510066298881
_r = 26959946667150639794667015087019625940457807714424391721682722368061
# s = 0xbd71344799d5c7fcdc45b59fa3b9ab8f6a948bc5L
# c = 0x5b056c7e11dd68f40469ee7f3c7a7d74f7d121116506d031218291fbL
_b = 0xb4050a850c04b3abf54132565044b0b7d7bfd8ba270b39432355ffb4
_Gx =0xb70e0cbd6bb4bf7f321390b94a03c1d356c21122343280d6115c1d21
_Gy = 0xbd376388b5f723fb4c22dfe6cd4375a05a07476444d5819985007e34

curve_224 = ellipticcurve.CurveFp( _p, -3, _b )
generator_224 = ellipticcurve.Point( curve_224, _Gx, _Gy, _r )

# NIST Curve P-256:
_p = 115792089210356248762697446949407573530086143415290314195533631308867097853951
_r = 115792089210356248762697446949407573529996955224135760342422259061068512044369
# s = 0xc49d360886e704936a6678e1139d26b7819f7e90L
# c = 0x7efba1662985be9403cb055c75d4f7e0ce8d84a9c5114abcaf3177680104fa0dL
_b = 0x5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b
_Gx = 0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296
_Gy = 0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5

curve_256 = ellipticcurve.CurveFp( _p, -3, _b )
generator_256 = ellipticcurve.Point( curve_256, _Gx, _Gy, _r )

# NIST Curve P-384:
_p = 39402006196394479212279040100143613805079739270465446667948293404245721771496870329047266088258938001861606973112319
_r = 39402006196394479212279040100143613805079739270465446667946905279627659399113263569398956308152294913554433653942643
# s = 0xa335926aa319a27a1d00896a6773a4827acdac73L
# c = 0x79d1e655f868f02fff48dcdee14151ddb80643c1406d0ca10dfe6fc52009540a495e8042ea5f744f6e184667cc722483L
_b = 0xb3312fa7e23ee7e4988e056be3f82d19181d9c6efe8141120314088f5013875ac656398d8a2ed19d2a85c8edd3ec2aef
_Gx = 0xaa87ca22be8b05378eb1c71ef320ad746e1d3b628ba79b9859f741e082542a385502f25dbf55296c3a545e3872760ab7
_Gy = 0x3617de4a96262c6f5d9e98bf9292dc29f8f41dbd289a147ce9da3113b5f0b8c00a60b1ce1d7e819d7a431d7c90ea0e5f

curve_384 = ellipticcurve.CurveFp( _p, -3, _b )
generator_384 = ellipticcurve.Point( curve_384, _Gx, _Gy, _r )

# NIST Curve P-521:
_p = 6864797660130609714981900799081393217269435300143305409394463459185543183397656052122559640661454554977296311391480858037121987999716643812574028291115057151
_r = 6864797660130609714981900799081393217269435300143305409394463459185543183397655394245057746333217197532963996371363321113864768612440380340372808892707005449
# s = 0xd09e8800291cb85396cc6717393284aaa0da64baL
# c = 0x0b48bfa5f420a34949539d2bdfc264eeeeb077688e44fbf0ad8f6d0edb37bd6b533281000518e19f1b9ffbe0fe9ed8a3c2200b8f875e523868c70c1e5bf55bad637L
_b = 0x051953eb9618e1c9a1f929a21a0b68540eea2da725b99b315f3b8b489918ef109e156193951ec7e937b1652c0bd3bb1bf073573df883d2c34f1ef451fd46b503f00
_Gx = 0xc6858e06b70404e9cd9e3ecb662395b4429c648139053fb521f828af606b4d3dbaa14b5e77efe75928fe1dc127a2ffa8de3348b3c1856a429bf97e7e31c2e5bd66
_Gy = 0x11839296a789a3bc0045c8a5fb42c7d1bd998f54449579b446817afbd17273e662c97ee72995ef42640c550b9013fad0761353c7086a272c24088be94769fd16650

curve_521 = ellipticcurve.CurveFp( _p, -3, _b )
generator_521 = ellipticcurve.Point( curve_521, _Gx, _Gy, _r )

# Certicom secp256-k1
_a  = 0x0000000000000000000000000000000000000000000000000000000000000000
_b  = 0x0000000000000000000000000000000000000000000000000000000000000007
_p  = 0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f
_Gx = 0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798
_Gy = 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8
_r  = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141

curve_secp256k1 = ellipticcurve.CurveFp( _p, _a, _b)
generator_secp256k1 = ellipticcurve.Point( curve_secp256k1, _Gx, _Gy, _r)



def __main__():
  class TestFailure(Exception): pass

  def test_point_validity( generator, x, y, expected ):
    """generator defines the curve; is (x,y) a point on
       this curve? "expected" is True if the right answer is Yes."""
    if point_is_valid( generator, x, y ) == expected:
      print_("Point validity tested as expected.")
    else:
      raise TestFailure("*** Point validity test gave wrong result.")

  def test_signature_validity( Msg, Qx, Qy, R, S, expected ):
    """Msg = message, Qx and Qy represent the base point on
       elliptic curve c192, R and S are the signature, and
       "expected" is True iff the signature is expected to be valid."""
    pubk = Public_key( generator_192,
                       ellipticcurve.Point( curve_192, Qx, Qy ) )
    got = pubk.verifies( digest_integer( Msg ), Signature( R, S ) )
    if got == expected:
      print_("Signature tested as expected: got %s, expected %s." % \
            ( got, expected ))
    else:
      raise TestFailure("*** Signature test failed: got %s, expected %s." % \
                        ( got, expected ))

  print_("NIST Curve P-192:")

  p192 = generator_192

  # From X9.62:

  d = 651056770906015076056810763456358567190100156695615665659
  Q = d * p192
  if Q.x() != 0x62B12D60690CDCF330BABAB6E69763B471F994DD702D16A5:
    raise TestFailure("*** p192 * d came out wrong.")
  else:
    print_("p192 * d came out right.")

  k = 6140507067065001063065065565667405560006161556565665656654
  R = k * p192
  if R.x() != 0x885052380FF147B734C330C43D39B2C4A89F29B0F749FEAD \
     or R.y() != 0x9CF9FA1CBEFEFB917747A3BB29C072B9289C2547884FD835:
    raise TestFailure("*** k * p192 came out wrong.")
  else:
    print_("k * p192 came out right.")

  u1 = 2563697409189434185194736134579731015366492496392189760599
  u2 = 6266643813348617967186477710235785849136406323338782220568
  temp = u1 * p192 + u2 * Q
  if temp.x() != 0x885052380FF147B734C330C43D39B2C4A89F29B0F749FEAD \
     or temp.y() != 0x9CF9FA1CBEFEFB917747A3BB29C072B9289C2547884FD835:
    raise TestFailure("*** u1 * p192 + u2 * Q came out wrong.")
  else:
    print_("u1 * p192 + u2 * Q came out right.")

  e = 968236873715988614170569073515315707566766479517
  pubk = Public_key( generator_192, generator_192 * d )
  privk = Private_key( pubk, d )
  sig = privk.sign( e, k )
  r, s = sig.r, sig.s
  if r != 3342403536405981729393488334694600415596881826869351677613 \
     or s != 5735822328888155254683894997897571951568553642892029982342:
    raise TestFailure("*** r or s came out wrong.")
  else:
    print_("r and s came out right.")

  valid = pubk.verifies( e, sig )
  if valid: print_("Signature verified OK.")
  else: raise TestFailure("*** Signature failed verification.")

  valid = pubk.verifies( e-1, sig )
  if not valid: print_("Forgery was correctly rejected.")
  else: raise TestFailure("*** Forgery was erroneously accepted.")

  print_("Testing point validity, as per ECDSAVS.pdf B.2.2:")

  test_point_validity( \
    p192, \
    0xcd6d0f029a023e9aaca429615b8f577abee685d8257cc83a, \
    0x00019c410987680e9fb6c0b6ecc01d9a2647c8bae27721bacdfc, \
    False )

  test_point_validity(
    p192, \
    0x00017f2fce203639e9eaf9fb50b81fc32776b30e3b02af16c73b, \
    0x95da95c5e72dd48e229d4748d4eee658a9a54111b23b2adb, \
    False )

  test_point_validity(
    p192, \
    0x4f77f8bc7fccbadd5760f4938746d5f253ee2168c1cf2792, \
    0x000147156ff824d131629739817edb197717c41aab5c2a70f0f6, \
    False )

  test_point_validity(
    p192, \
    0xc58d61f88d905293bcd4cd0080bcb1b7f811f2ffa41979f6, \
    0x8804dc7a7c4c7f8b5d437f5156f3312ca7d6de8a0e11867f, \
    True )

  test_point_validity(
    p192, \
    0xcdf56c1aa3d8afc53c521adf3ffb96734a6a630a4a5b5a70, \
    0x97c1c44a5fb229007b5ec5d25f7413d170068ffd023caa4e, \
    True )

  test_point_validity(
    p192, \
    0x89009c0dc361c81e99280c8e91df578df88cdf4b0cdedced, \
    0x27be44a529b7513e727251f128b34262a0fd4d8ec82377b9, \
    True )

  test_point_validity(
    p192, \
    0x6a223d00bd22c52833409a163e057e5b5da1def2a197dd15, \
    0x7b482604199367f1f303f9ef627f922f97023e90eae08abf, \
    True )

  test_point_validity(
    p192, \
    0x6dccbde75c0948c98dab32ea0bc59fe125cf0fb1a3798eda, \
    0x0001171a3e0fa60cf3096f4e116b556198de430e1fbd330c8835, \
    False )

  test_point_validity(
    p192, \
    0xd266b39e1f491fc4acbbbc7d098430931cfa66d55015af12, \
    0x193782eb909e391a3148b7764e6b234aa94e48d30a16dbb2, \
    False )

  test_point_validity(
    p192, \
    0x9d6ddbcd439baa0c6b80a654091680e462a7d1d3f1ffeb43, \
    0x6ad8efc4d133ccf167c44eb4691c80abffb9f82b932b8caa, \
    False )

  test_point_validity(
    p192, \
    0x146479d944e6bda87e5b35818aa666a4c998a71f4e95edbc, \
    0xa86d6fe62bc8fbd88139693f842635f687f132255858e7f6, \
    False )

  test_point_validity(
    p192, \
    0xe594d4a598046f3598243f50fd2c7bd7d380edb055802253, \
    0x509014c0c4d6b536e3ca750ec09066af39b4c8616a53a923, \
    False )

  print_("Trying signature-verification tests from ECDSAVS.pdf B.2.4:")
  print_("P-192:")
  Msg = 0x84ce72aa8699df436059f052ac51b6398d2511e49631bcb7e71f89c499b9ee425dfbc13a5f6d408471b054f2655617cbbaf7937b7c80cd8865cf02c8487d30d2b0fbd8b2c4e102e16d828374bbc47b93852f212d5043c3ea720f086178ff798cc4f63f787b9c2e419efa033e7644ea7936f54462dc21a6c4580725f7f0e7d158
  Qx = 0xd9dbfb332aa8e5ff091e8ce535857c37c73f6250ffb2e7ac
  Qy = 0x282102e364feded3ad15ddf968f88d8321aa268dd483ebc4
  R = 0x64dca58a20787c488d11d6dd96313f1b766f2d8efe122916
  S = 0x1ecba28141e84ab4ecad92f56720e2cc83eb3d22dec72479
  test_signature_validity( Msg, Qx, Qy, R, S, True )

  Msg = 0x94bb5bacd5f8ea765810024db87f4224ad71362a3c28284b2b9f39fab86db12e8beb94aae899768229be8fdb6c4f12f28912bb604703a79ccff769c1607f5a91450f30ba0460d359d9126cbd6296be6d9c4bb96c0ee74cbb44197c207f6db326ab6f5a659113a9034e54be7b041ced9dcf6458d7fb9cbfb2744d999f7dfd63f4
  Qx = 0x3e53ef8d3112af3285c0e74842090712cd324832d4277ae7
  Qy = 0xcc75f8952d30aec2cbb719fc6aa9934590b5d0ff5a83adb7
  R = 0x8285261607283ba18f335026130bab31840dcfd9c3e555af
  S = 0x356d89e1b04541afc9704a45e9c535ce4a50929e33d7e06c
  test_signature_validity( Msg, Qx, Qy, R, S, True )

  Msg = 0xf6227a8eeb34afed1621dcc89a91d72ea212cb2f476839d9b4243c66877911b37b4ad6f4448792a7bbba76c63bdd63414b6facab7dc71c3396a73bd7ee14cdd41a659c61c99b779cecf07bc51ab391aa3252386242b9853ea7da67fd768d303f1b9b513d401565b6f1eb722dfdb96b519fe4f9bd5de67ae131e64b40e78c42dd
  Qx = 0x16335dbe95f8e8254a4e04575d736befb258b8657f773cb7
  Qy = 0x421b13379c59bc9dce38a1099ca79bbd06d647c7f6242336
  R = 0x4141bd5d64ea36c5b0bd21ef28c02da216ed9d04522b1e91
  S = 0x159a6aa852bcc579e821b7bb0994c0861fb08280c38daa09
  test_signature_validity( Msg, Qx, Qy, R, S, False )

  Msg = 0x16b5f93afd0d02246f662761ed8e0dd9504681ed02a253006eb36736b563097ba39f81c8e1bce7a16c1339e345efabbc6baa3efb0612948ae51103382a8ee8bc448e3ef71e9f6f7a9676694831d7f5dd0db5446f179bcb737d4a526367a447bfe2c857521c7f40b6d7d7e01a180d92431fb0bbd29c04a0c420a57b3ed26ccd8a
  Qx = 0xfd14cdf1607f5efb7b1793037b15bdf4baa6f7c16341ab0b
  Qy = 0x83fa0795cc6c4795b9016dac928fd6bac32f3229a96312c4
  R = 0x8dfdb832951e0167c5d762a473c0416c5c15bc1195667dc1
  S = 0x1720288a2dc13fa1ec78f763f8fe2ff7354a7e6fdde44520
  test_signature_validity( Msg, Qx, Qy, R, S, False )

  Msg = 0x08a2024b61b79d260e3bb43ef15659aec89e5b560199bc82cf7c65c77d39192e03b9a895d766655105edd9188242b91fbde4167f7862d4ddd61e5d4ab55196683d4f13ceb90d87aea6e07eb50a874e33086c4a7cb0273a8e1c4408f4b846bceae1ebaac1b2b2ea851a9b09de322efe34cebe601653efd6ddc876ce8c2f2072fb
  Qx = 0x674f941dc1a1f8b763c9334d726172d527b90ca324db8828
  Qy = 0x65adfa32e8b236cb33a3e84cf59bfb9417ae7e8ede57a7ff
  R = 0x9508b9fdd7daf0d8126f9e2bc5a35e4c6d800b5b804d7796
  S = 0x36f2bf6b21b987c77b53bb801b3435a577e3d493744bfab0
  test_signature_validity( Msg, Qx, Qy, R, S, False )

  Msg = 0x1843aba74b0789d4ac6b0b8923848023a644a7b70afa23b1191829bbe4397ce15b629bf21a8838298653ed0c19222b95fa4f7390d1b4c844d96e645537e0aae98afb5c0ac3bd0e4c37f8daaff25556c64e98c319c52687c904c4de7240a1cc55cd9756b7edaef184e6e23b385726e9ffcba8001b8f574987c1a3fedaaa83ca6d
  Qx = 0x10ecca1aad7220b56a62008b35170bfd5e35885c4014a19f
  Qy = 0x04eb61984c6c12ade3bc47f3c629ece7aa0a033b9948d686
  R = 0x82bfa4e82c0dfe9274169b86694e76ce993fd83b5c60f325
  S = 0xa97685676c59a65dbde002fe9d613431fb183e8006d05633
  test_signature_validity( Msg, Qx, Qy, R, S, False )

  Msg = 0x5a478f4084ddd1a7fea038aa9732a822106385797d02311aeef4d0264f824f698df7a48cfb6b578cf3da416bc0799425bb491be5b5ecc37995b85b03420a98f2c4dc5c31a69a379e9e322fbe706bbcaf0f77175e05cbb4fa162e0da82010a278461e3e974d137bc746d1880d6eb02aa95216014b37480d84b87f717bb13f76e1
  Qx = 0x6636653cb5b894ca65c448277b29da3ad101c4c2300f7c04
  Qy = 0xfdf1cbb3fc3fd6a4f890b59e554544175fa77dbdbeb656c1
  R = 0xeac2ddecddfb79931a9c3d49c08de0645c783a24cb365e1c
  S = 0x3549fee3cfa7e5f93bc47d92d8ba100e881a2a93c22f8d50
  test_signature_validity( Msg, Qx, Qy, R, S, False )

  Msg = 0xc598774259a058fa65212ac57eaa4f52240e629ef4c310722088292d1d4af6c39b49ce06ba77e4247b20637174d0bd67c9723feb57b5ead232b47ea452d5d7a089f17c00b8b6767e434a5e16c231ba0efa718a340bf41d67ea2d295812ff1b9277daacb8bc27b50ea5e6443bcf95ef4e9f5468fe78485236313d53d1c68f6ba2
  Qx = 0xa82bd718d01d354001148cd5f69b9ebf38ff6f21898f8aaa
  Qy = 0xe67ceede07fc2ebfafd62462a51e4b6c6b3d5b537b7caf3e
  R = 0x4d292486c620c3de20856e57d3bb72fcde4a73ad26376955
  S = 0xa85289591a6081d5728825520e62ff1c64f94235c04c7f95
  test_signature_validity( Msg, Qx, Qy, R, S, False )

  Msg = 0xca98ed9db081a07b7557f24ced6c7b9891269a95d2026747add9e9eb80638a961cf9c71a1b9f2c29744180bd4c3d3db60f2243c5c0b7cc8a8d40a3f9a7fc910250f2187136ee6413ffc67f1a25e1c4c204fa9635312252ac0e0481d89b6d53808f0c496ba87631803f6c572c1f61fa049737fdacce4adff757afed4f05beb658
  Qx = 0x7d3b016b57758b160c4fca73d48df07ae3b6b30225126c2f
  Qy = 0x4af3790d9775742bde46f8da876711be1b65244b2b39e7ec
  R = 0x95f778f5f656511a5ab49a5d69ddd0929563c29cbc3a9e62
  S = 0x75c87fc358c251b4c83d2dd979faad496b539f9f2ee7a289
  test_signature_validity( Msg, Qx, Qy, R, S, False )

  Msg = 0x31dd9a54c8338bea06b87eca813d555ad1850fac9742ef0bbe40dad400e10288acc9c11ea7dac79eb16378ebea9490e09536099f1b993e2653cd50240014c90a9c987f64545abc6a536b9bd2435eb5e911fdfde2f13be96ea36ad38df4ae9ea387b29cced599af777338af2794820c9cce43b51d2112380a35802ab7e396c97a
  Qx = 0x9362f28c4ef96453d8a2f849f21e881cd7566887da8beb4a
  Qy = 0xe64d26d8d74c48a024ae85d982ee74cd16046f4ee5333905
  R = 0xf3923476a296c88287e8de914b0b324ad5a963319a4fe73b
  S = 0xf0baeed7624ed00d15244d8ba2aede085517dbdec8ac65f5
  test_signature_validity( Msg, Qx, Qy, R, S, True )

  Msg = 0xb2b94e4432267c92f9fdb9dc6040c95ffa477652761290d3c7de312283f6450d89cc4aabe748554dfb6056b2d8e99c7aeaad9cdddebdee9dbc099839562d9064e68e7bb5f3a6bba0749ca9a538181fc785553a4000785d73cc207922f63e8ce1112768cb1de7b673aed83a1e4a74592f1268d8e2a4e9e63d414b5d442bd0456d
  Qx = 0xcc6fc032a846aaac25533eb033522824f94e670fa997ecef
  Qy = 0xe25463ef77a029eccda8b294fd63dd694e38d223d30862f1
  R = 0x066b1d07f3a40e679b620eda7f550842a35c18b80c5ebe06
  S = 0xa0b0fb201e8f2df65e2c4508ef303bdc90d934016f16b2dc
  test_signature_validity( Msg, Qx, Qy, R, S, False )

  Msg = 0x4366fcadf10d30d086911de30143da6f579527036937007b337f7282460eae5678b15cccda853193ea5fc4bc0a6b9d7a31128f27e1214988592827520b214eed5052f7775b750b0c6b15f145453ba3fee24a085d65287e10509eb5d5f602c440341376b95c24e5c4727d4b859bfe1483d20538acdd92c7997fa9c614f0f839d7
  Qx = 0x955c908fe900a996f7e2089bee2f6376830f76a19135e753
  Qy = 0xba0c42a91d3847de4a592a46dc3fdaf45a7cc709b90de520
  R = 0x1f58ad77fc04c782815a1405b0925e72095d906cbf52a668
  S = 0xf2e93758b3af75edf784f05a6761c9b9a6043c66b845b599
  test_signature_validity( Msg, Qx, Qy, R, S, False )

  Msg = 0x543f8af57d750e33aa8565e0cae92bfa7a1ff78833093421c2942cadf9986670a5ff3244c02a8225e790fbf30ea84c74720abf99cfd10d02d34377c3d3b41269bea763384f372bb786b5846f58932defa68023136cd571863b304886e95e52e7877f445b9364b3f06f3c28da12707673fecb4b8071de06b6e0a3c87da160cef3
  Qx = 0x31f7fa05576d78a949b24812d4383107a9a45bb5fccdd835
  Qy = 0x8dc0eb65994a90f02b5e19bd18b32d61150746c09107e76b
  R = 0xbe26d59e4e883dde7c286614a767b31e49ad88789d3a78ff
  S = 0x8762ca831c1ce42df77893c9b03119428e7a9b819b619068
  test_signature_validity( Msg, Qx, Qy, R, S, False )

  Msg = 0xd2e8454143ce281e609a9d748014dcebb9d0bc53adb02443a6aac2ffe6cb009f387c346ecb051791404f79e902ee333ad65e5c8cb38dc0d1d39a8dc90add5023572720e5b94b190d43dd0d7873397504c0c7aef2727e628eb6a74411f2e400c65670716cb4a815dc91cbbfeb7cfe8c929e93184c938af2c078584da045e8f8d1
  Qx = 0x66aa8edbbdb5cf8e28ceb51b5bda891cae2df84819fe25c0
  Qy = 0x0c6bc2f69030a7ce58d4a00e3b3349844784a13b8936f8da
  R = 0xa4661e69b1734f4a71b788410a464b71e7ffe42334484f23
  S = 0x738421cf5e049159d69c57a915143e226cac8355e149afe9
  test_signature_validity( Msg, Qx, Qy, R, S, False )

  Msg = 0x6660717144040f3e2f95a4e25b08a7079c702a8b29babad5a19a87654bc5c5afa261512a11b998a4fb36b5d8fe8bd942792ff0324b108120de86d63f65855e5461184fc96a0a8ffd2ce6d5dfb0230cbbdd98f8543e361b3205f5da3d500fdc8bac6db377d75ebef3cb8f4d1ff738071ad0938917889250b41dd1d98896ca06fb
  Qx = 0xbcfacf45139b6f5f690a4c35a5fffa498794136a2353fc77
  Qy = 0x6f4a6c906316a6afc6d98fe1f0399d056f128fe0270b0f22
  R = 0x9db679a3dafe48f7ccad122933acfe9da0970b71c94c21c1
  S = 0x984c2db99827576c0a41a5da41e07d8cc768bc82f18c9da9
  test_signature_validity( Msg, Qx, Qy, R, S, False )



  print_("Testing the example code:")

  # Building a public/private key pair from the NIST Curve P-192:

  g = generator_192
  n = g.order()

  # (random.SystemRandom is supposed to provide
  # crypto-quality random numbers, but as Debian recently
  # illustrated, a systems programmer can accidentally
  # demolish this security, so in serious applications
  # further precautions are appropriate.)

  randrange = random.SystemRandom().randrange

  secret = randrange( 1, n )
  pubkey = Public_key( g, g * secret )
  privkey = Private_key( pubkey, secret )

  # Signing a hash value:

  hash = randrange( 1, n )
  signature = privkey.sign( hash, randrange( 1, n ) )

  # Verifying a signature for a hash value:

  if pubkey.verifies( hash, signature ):
    print_("Demo verification succeeded.")
  else:
    raise TestFailure("*** Demo verification failed.")

  if pubkey.verifies( hash-1, signature ):
    raise TestFailure( "**** Demo verification failed to reject tampered hash.")
  else:
    print_("Demo verification correctly rejected tampered hash.")

if __name__ == "__main__":
  __main__()

########NEW FILE########
__FILENAME__ = ellipticcurve
#! /usr/bin/env python
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

from __future__ import division

from .six import print_
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
    """Return True if the points are identical, False otherwise."""
    if self.__curve == other.__curve \
       and self.__x == other.__x \
       and self.__y == other.__y:
      return True
    else:
      return False

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
    # print_("Multiplying %s by %d (e3 = %d):" % ( self, other, e3 ))
    while i > 1:
      result = result.double()
      if ( e3 & i ) != 0 and ( e & i ) == 0: result = result + self
      if ( e3 & i ) == 0 and ( e & i ) != 0: result = result + negative_self
      # print_(". . . i = %d, result = %s" % ( i, result ))
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
    print_("%s + %s = %s" % ( p1, p2, p3 ), end=' ')
    if p3.x() != x3 or p3.y() != y3:
      raise FailedTest("Failure: should give (%d,%d)." % ( x3, y3 ))
    else:
      print_(" Good.")

  def test_double( c, x1, y1, x3, y3 ):
    """We expect that on curve c, 2*(x1,y1) = (x3, y3)."""
    p1 = Point( c, x1, y1 )
    p3 = p1.double()
    print_("%s doubled = %s" % ( p1, p3 ), end=' ')
    if p3.x() != x3 or p3.y() != y3:
      raise FailedTest("Failure: should give (%d,%d)." % ( x3, y3 ))
    else:
      print_(" Good.")

  def test_double_infinity( c ):
    """We expect that on curve c, 2*INFINITY = INFINITY."""
    p1 = INFINITY
    p3 = p1.double()
    print_("%s doubled = %s" % ( p1, p3 ), end=' ')
    if p3.x() != INFINITY.x() or p3.y() != INFINITY.y():
      raise FailedTest("Failure: should give (%d,%d)." % ( INFINITY.x(), INFINITY.y() ))
    else:
      print_(" Good.")

  def test_multiply( c, x1, y1, m, x3, y3 ):
    """We expect that on curve c, m*(x1,y1) = (x3,y3)."""
    p1 = Point( c, x1, y1 )
    p3 = p1 * m
    print_("%s * %d = %s" % ( p1, m, p3 ), end=' ')
    if p3.x() != x3 or p3.y() != y3:
      raise FailedTest("Failure: should give (%d,%d)." % ( x3, y3 ))
    else:
      print_(" Good.")


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
    print_("%s * %d = %s, expected %s . . ." % ( g, i, p, check ), end=' ')
    if p == check:
      print_(" Good.")
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
    print_("p192 * d came out right.")

  k = 6140507067065001063065065565667405560006161556565665656654
  R = k * p192
  if R.x() != 0x885052380FF147B734C330C43D39B2C4A89F29B0F749FEAD \
     or R.y() != 0x9CF9FA1CBEFEFB917747A3BB29C072B9289C2547884FD835:
    raise FailedTest("k * p192 came out wrong.")
  else:
    print_("k * p192 came out right.")

  u1 = 2563697409189434185194736134579731015366492496392189760599
  u2 = 6266643813348617967186477710235785849136406323338782220568
  temp = u1 * p192 + u2 * Q
  if temp.x() != 0x885052380FF147B734C330C43D39B2C4A89F29B0F749FEAD \
     or temp.y() != 0x9CF9FA1CBEFEFB917747A3BB29C072B9289C2547884FD835:
    raise FailedTest("u1 * p192 + u2 * Q came out wrong.")
  else:
    print_("u1 * p192 + u2 * Q came out right.")

if __name__ == "__main__":
  __main__()

########NEW FILE########
__FILENAME__ = keys
import binascii

from . import ecdsa
from . import der
from . import rfc6979
from .curves import NIST192p, find_curve
from .util import string_to_number, number_to_string, randrange
from .util import sigencode_string, sigdecode_string
from .util import oid_ecPublicKey, encoded_oid_ecPublicKey
from .six import PY3, b
from hashlib import sha1

class BadSignatureError(Exception):
    pass
class BadDigestError(Exception):
    pass

class VerifyingKey:
    def __init__(self, _error__please_use_generate=None):
        if not _error__please_use_generate:
            raise TypeError("Please use SigningKey.generate() to construct me")

    @classmethod
    def from_public_point(klass, point, curve=NIST192p, hashfunc=sha1):
        self = klass(_error__please_use_generate=True)
        self.curve = curve
        self.default_hashfunc = hashfunc
        self.pubkey = ecdsa.Public_key(curve.generator, point)
        self.pubkey.order = curve.order
        return self

    @classmethod
    def from_string(klass, string, curve=NIST192p, hashfunc=sha1,
                    validate_point=True):
        order = curve.order
        assert len(string) == curve.verifying_key_length, \
               (len(string), curve.verifying_key_length)
        xs = string[:curve.baselen]
        ys = string[curve.baselen:]
        assert len(xs) == curve.baselen, (len(xs), curve.baselen)
        assert len(ys) == curve.baselen, (len(ys), curve.baselen)
        x = string_to_number(xs)
        y = string_to_number(ys)
        if validate_point:
            assert ecdsa.point_is_valid(curve.generator, x, y)
        from . import ellipticcurve
        point = ellipticcurve.Point(curve.curve, x, y, order)
        return klass.from_public_point(point, curve, hashfunc)

    @classmethod
    def from_pem(klass, string):
        return klass.from_der(der.unpem(string))

    @classmethod
    def from_der(klass, string):
        # [[oid_ecPublicKey,oid_curve], point_str_bitstring]
        s1,empty = der.remove_sequence(string)
        if empty != b(""):
            raise der.UnexpectedDER("trailing junk after DER pubkey: %s" %
                                    binascii.hexlify(empty))
        s2,point_str_bitstring = der.remove_sequence(s1)
        # s2 = oid_ecPublicKey,oid_curve
        oid_pk, rest = der.remove_object(s2)
        oid_curve, empty = der.remove_object(rest)
        if empty != b(""):
            raise der.UnexpectedDER("trailing junk after DER pubkey objects: %s" %
                                    binascii.hexlify(empty))
        assert oid_pk == oid_ecPublicKey, (oid_pk, oid_ecPublicKey)
        curve = find_curve(oid_curve)
        point_str, empty = der.remove_bitstring(point_str_bitstring)
        if empty != b(""):
            raise der.UnexpectedDER("trailing junk after pubkey pointstring: %s" %
                                    binascii.hexlify(empty))
        assert point_str.startswith(b("\x00\x04"))
        return klass.from_string(point_str[2:], curve)

    def to_string(self):
        # VerifyingKey.from_string(vk.to_string()) == vk as long as the
        # curves are the same: the curve itself is not included in the
        # serialized form
        order = self.pubkey.order
        x_str = number_to_string(self.pubkey.point.x(), order)
        y_str = number_to_string(self.pubkey.point.y(), order)
        return x_str + y_str

    def to_pem(self):
        return der.topem(self.to_der(), "PUBLIC KEY")

    def to_der(self):
        order = self.pubkey.order
        x_str = number_to_string(self.pubkey.point.x(), order)
        y_str = number_to_string(self.pubkey.point.y(), order)
        point_str = b("\x00\x04") + x_str + y_str
        return der.encode_sequence(der.encode_sequence(encoded_oid_ecPublicKey,
                                                       self.curve.encoded_oid),
                                   der.encode_bitstring(point_str))

    def verify(self, signature, data, hashfunc=None, sigdecode=sigdecode_string):
        hashfunc = hashfunc or self.default_hashfunc
        digest = hashfunc(data).digest()
        return self.verify_digest(signature, digest, sigdecode)

    def verify_digest(self, signature, digest, sigdecode=sigdecode_string):
        if len(digest) > self.curve.baselen:
            raise BadDigestError("this curve (%s) is too short "
                                 "for your digest (%d)" % (self.curve.name,
                                                           8*len(digest)))
        number = string_to_number(digest)
        r, s = sigdecode(signature, self.pubkey.order)
        sig = ecdsa.Signature(r, s)
        if self.pubkey.verifies(number, sig):
            return True
        raise BadSignatureError

class SigningKey:
    def __init__(self, _error__please_use_generate=None):
        if not _error__please_use_generate:
            raise TypeError("Please use SigningKey.generate() to construct me")

    @classmethod
    def generate(klass, curve=NIST192p, entropy=None, hashfunc=sha1):
        secexp = randrange(curve.order, entropy)
        return klass.from_secret_exponent(secexp, curve, hashfunc)

    # to create a signing key from a short (arbitrary-length) seed, convert
    # that seed into an integer with something like
    # secexp=util.randrange_from_seed__X(seed, curve.order), and then pass
    # that integer into SigningKey.from_secret_exponent(secexp, curve)

    @classmethod
    def from_secret_exponent(klass, secexp, curve=NIST192p, hashfunc=sha1):
        self = klass(_error__please_use_generate=True)
        self.curve = curve
        self.default_hashfunc = hashfunc
        self.baselen = curve.baselen
        n = curve.order
        assert 1 <= secexp < n
        pubkey_point = curve.generator*secexp
        pubkey = ecdsa.Public_key(curve.generator, pubkey_point)
        pubkey.order = n
        self.verifying_key = VerifyingKey.from_public_point(pubkey_point, curve,
                                                            hashfunc)
        self.privkey = ecdsa.Private_key(pubkey, secexp)
        self.privkey.order = n
        return self

    @classmethod
    def from_string(klass, string, curve=NIST192p, hashfunc=sha1):
        assert len(string) == curve.baselen, (len(string), curve.baselen)
        secexp = string_to_number(string)
        return klass.from_secret_exponent(secexp, curve, hashfunc)

    @classmethod
    def from_pem(klass, string, hashfunc=sha1):
        # the privkey pem file has two sections: "EC PARAMETERS" and "EC
        # PRIVATE KEY". The first is redundant.
        if PY3 and isinstance(string, str):
            string = string.encode()
        privkey_pem = string[string.index(b("-----BEGIN EC PRIVATE KEY-----")):]
        return klass.from_der(der.unpem(privkey_pem), hashfunc)
    @classmethod
    def from_der(klass, string, hashfunc=sha1):
        # SEQ([int(1), octetstring(privkey),cont[0], oid(secp224r1),
        #      cont[1],bitstring])
        s, empty = der.remove_sequence(string)
        if empty != b(""):
            raise der.UnexpectedDER("trailing junk after DER privkey: %s" %
                                    binascii.hexlify(empty))
        one, s = der.remove_integer(s)
        if one != 1:
            raise der.UnexpectedDER("expected '1' at start of DER privkey,"
                                    " got %d" % one)
        privkey_str, s = der.remove_octet_string(s)
        tag, curve_oid_str, s = der.remove_constructed(s)
        if tag != 0:
            raise der.UnexpectedDER("expected tag 0 in DER privkey,"
                                    " got %d" % tag)
        curve_oid, empty = der.remove_object(curve_oid_str)
        if empty != b(""):
            raise der.UnexpectedDER("trailing junk after DER privkey "
                                    "curve_oid: %s" % binascii.hexlify(empty))
        curve = find_curve(curve_oid)

        # we don't actually care about the following fields
        #
        #tag, pubkey_bitstring, s = der.remove_constructed(s)
        #if tag != 1:
        #    raise der.UnexpectedDER("expected tag 1 in DER privkey, got %d"
        #                            % tag)
        #pubkey_str = der.remove_bitstring(pubkey_bitstring)
        #if empty != "":
        #    raise der.UnexpectedDER("trailing junk after DER privkey "
        #                            "pubkeystr: %s" % binascii.hexlify(empty))

        # our from_string method likes fixed-length privkey strings
        if len(privkey_str) < curve.baselen:
            privkey_str = b("\x00")*(curve.baselen-len(privkey_str)) + privkey_str
        return klass.from_string(privkey_str, curve, hashfunc)

    def to_string(self):
        secexp = self.privkey.secret_multiplier
        s = number_to_string(secexp, self.privkey.order)
        return s

    def to_pem(self):
        # TODO: "BEGIN ECPARAMETERS"
        return der.topem(self.to_der(), "EC PRIVATE KEY")

    def to_der(self):
        # SEQ([int(1), octetstring(privkey),cont[0], oid(secp224r1),
        #      cont[1],bitstring])
        encoded_vk = b("\x00\x04") + self.get_verifying_key().to_string()
        return der.encode_sequence(der.encode_integer(1),
                                   der.encode_octet_string(self.to_string()),
                                   der.encode_constructed(0, self.curve.encoded_oid),
                                   der.encode_constructed(1, der.encode_bitstring(encoded_vk)),
                                   )

    def get_verifying_key(self):
        return self.verifying_key

    def sign_deterministic(self, data, hashfunc=None, sigencode=sigencode_string):
        hashfunc = hashfunc or self.default_hashfunc
        digest = hashfunc(data).digest()

        return self.sign_digest_deterministic(digest, hashfunc=hashfunc, sigencode=sigencode)

    def sign_digest_deterministic(self, digest, hashfunc=None, sigencode=sigencode_string):
        """
        Calculates 'k' from data itself, removing the need for strong
        random generator and producing deterministic (reproducible) signatures.
        See RFC 6979 for more details.
        """
        secexp = self.privkey.secret_multiplier
        k = rfc6979.generate_k(self.curve.generator, secexp, hashfunc, digest)

        return self.sign_digest(digest, sigencode=sigencode, k=k)

    def sign(self, data, entropy=None, hashfunc=None, sigencode=sigencode_string, k=None):
        """
        hashfunc= should behave like hashlib.sha1 . The output length of the
        hash (in bytes) must not be longer than the length of the curve order
        (rounded up to the nearest byte), so using SHA256 with nist256p is
        ok, but SHA256 with nist192p is not. (In the 2**-96ish unlikely event
        of a hash output larger than the curve order, the hash will
        effectively be wrapped mod n).

        Use hashfunc=hashlib.sha1 to match openssl's -ecdsa-with-SHA1 mode,
        or hashfunc=hashlib.sha256 for openssl-1.0.0's -ecdsa-with-SHA256.
        """

        hashfunc = hashfunc or self.default_hashfunc
        h = hashfunc(data).digest()
        return self.sign_digest(h, entropy, sigencode, k)

    def sign_digest(self, digest, entropy=None, sigencode=sigencode_string, k=None):
        if len(digest) > self.curve.baselen:
            raise BadDigestError("this curve (%s) is too short "
                                 "for your digest (%d)" % (self.curve.name,
                                                           8*len(digest)))
        number = string_to_number(digest)
        r, s = self.sign_number(number, entropy, k)
        return sigencode(r, s, self.privkey.order)

    def sign_number(self, number, entropy=None, k=None):
        # returns a pair of numbers
        order = self.privkey.order
        # privkey.sign() may raise RuntimeError in the amazingly unlikely
        # (2**-192) event that r=0 or s=0, because that would leak the key.
        # We could re-try with a different 'k', but we couldn't test that
        # code, so I choose to allow the signature to fail instead.

        # If k is set, it is used directly. In other cases
        # it is generated using entropy function
        if k is not None:
            _k = k
        else:
            _k = randrange(order, entropy)

        assert 1 <= _k < order
        sig = self.privkey.sign(number, _k)
        return sig.r, sig.s

########NEW FILE########
__FILENAME__ = numbertheory
#! /usr/bin/env python
#
# Provide some simple capabilities from number theory.
#
# Version of 2008.11.14.
#
# Written in 2005 and 2006 by Peter Pearson and placed in the public domain.
# Revision history:
#   2008.11.14: Use pow( base, exponent, modulus ) for modular_exp.
#               Make gcd and lcm accept arbitrarly many arguments.

from __future__ import division

from .six import print_, integer_types
from .six.moves import reduce

import math
import types


class Error( Exception ):
  """Base class for exceptions in this module."""
  pass

class SquareRootError( Error ):
  pass

class NegativeExponentError( Error ):
  pass


def modular_exp( base, exponent, modulus ):
  "Raise base to exponent, reducing by modulus"
  if exponent < 0:
    raise NegativeExponentError( "Negative exponents (%d) not allowed" \
                                 % exponent )
  return pow( base, exponent, modulus )
#   result = 1L
#   x = exponent
#   b = base + 0L
#   while x > 0:
#     if x % 2 > 0: result = (result * b) % modulus
#     x = x // 2
#     b = ( b * b ) % modulus
#   return result


def polynomial_reduce_mod( poly, polymod, p ):
  """Reduce poly by polymod, integer arithmetic modulo p.

  Polynomials are represented as lists of coefficients
  of increasing powers of x."""

  # This module has been tested only by extensive use
  # in calculating modular square roots.

  # Just to make this easy, require a monic polynomial:
  assert polymod[-1] == 1

  assert len( polymod ) > 1

  while len( poly ) >= len( polymod ):
    if poly[-1] != 0:
      for i in range( 2, len( polymod ) + 1 ):
        poly[-i] = ( poly[-i] - poly[-1] * polymod[-i] ) % p
    poly = poly[0:-1]

  return poly



def polynomial_multiply_mod( m1, m2, polymod, p ):
  """Polynomial multiplication modulo a polynomial over ints mod p.

  Polynomials are represented as lists of coefficients
  of increasing powers of x."""

  # This is just a seat-of-the-pants implementation.

  # This module has been tested only by extensive use
  # in calculating modular square roots.

  # Initialize the product to zero:

  prod = ( len( m1 ) + len( m2 ) - 1 ) * [0]

  # Add together all the cross-terms:

  for i in range( len( m1 ) ):
    for j in range( len( m2 ) ):
      prod[i+j] = ( prod[i+j] + m1[i] * m2[j] ) % p

  return polynomial_reduce_mod( prod, polymod, p )


def polynomial_exp_mod( base, exponent, polymod, p ):
  """Polynomial exponentiation modulo a polynomial over ints mod p.

  Polynomials are represented as lists of coefficients
  of increasing powers of x."""

  # Based on the Handbook of Applied Cryptography, algorithm 2.227.

  # This module has been tested only by extensive use
  # in calculating modular square roots.

  assert exponent < p

  if exponent == 0: return [ 1 ]

  G = base
  k = exponent
  if k%2 == 1: s = G
  else:        s = [ 1 ]

  while k > 1:
    k = k // 2
    G = polynomial_multiply_mod( G, G, polymod, p )
    if k%2 == 1: s = polynomial_multiply_mod( G, s, polymod, p )

  return s



def jacobi( a, n ):
  """Jacobi symbol"""

  # Based on the Handbook of Applied Cryptography (HAC), algorithm 2.149.

  # This function has been tested by comparison with a small
  # table printed in HAC, and by extensive use in calculating
  # modular square roots.

  assert n >= 3
  assert n%2 == 1
  a = a % n
  if a == 0: return 0
  if a == 1: return 1
  a1, e = a, 0
  while a1%2 == 0:
    a1, e = a1//2, e+1
  if e%2 == 0 or n%8 == 1 or n%8 == 7: s = 1
  else: s = -1
  if a1 == 1: return s
  if n%4 == 3 and a1%4 == 3: s = -s
  return s * jacobi( n % a1, a1 )



def square_root_mod_prime( a, p ):
  """Modular square root of a, mod p, p prime."""

  # Based on the Handbook of Applied Cryptography, algorithms 3.34 to 3.39.

  # This module has been tested for all values in [0,p-1] for
  # every prime p from 3 to 1229.

  assert 0 <= a < p
  assert 1 < p

  if a == 0: return 0
  if p == 2: return a

  jac = jacobi( a, p )
  if jac == -1: raise SquareRootError( "%d has no square root modulo %d" \
                                       % ( a, p ) )

  if p % 4 == 3: return modular_exp( a, (p+1)//4, p )

  if p % 8 == 5:
    d = modular_exp( a, (p-1)//4, p )
    if d == 1: return modular_exp( a, (p+3)//8, p )
    if d == p-1: return ( 2 * a * modular_exp( 4*a, (p-5)//8, p ) ) % p
    raise RuntimeError("Shouldn't get here.")

  for b in range( 2, p ):
    if jacobi( b*b-4*a, p ) == -1:
      f = ( a, -b, 1 )
      ff = polynomial_exp_mod( ( 0, 1 ), (p+1)//2, f, p )
      assert ff[1] == 0
      return ff[0]
  raise RuntimeError("No b found.")



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


def gcd2(a, b):
  """Greatest common divisor using Euclid's algorithm."""
  while a:
    a, b = b%a, a
  return b


def gcd( *a ):
  """Greatest common divisor.

  Usage: gcd( [ 2, 4, 6 ] )
  or:    gcd( 2, 4, 6 )
  """

  if len( a ) > 1: return reduce( gcd2, a )
  if hasattr( a[0], "__iter__" ): return reduce( gcd2, a[0] )
  return a[0]


def lcm2(a,b):
  """Least common multiple of two integers."""

  return (a*b)//gcd(a,b)


def lcm( *a ):
  """Least common multiple.

  Usage: lcm( [ 3, 4, 5 ] )
  or:    lcm( 3, 4, 5 )
  """

  if len( a ) > 1: return reduce( lcm2, a )
  if hasattr( a[0], "__iter__" ): return reduce( lcm2, a[0] )
  return a[0]



def factorization( n ):
  """Decompose n into a list of (prime,exponent) pairs."""

  assert isinstance( n, integer_types )

  if n < 2: return []

  result = []
  d = 2

  # Test the small primes:

  for d in smallprimes:
    if d > n: break
    q, r = divmod( n, d )
    if r == 0:
      count = 1
      while d <= n:
        n = q
        q, r = divmod( n, d )
        if r != 0: break
        count = count + 1
      result.append( ( d, count ) )

  # If n is still greater than the last of our small primes,
  # it may require further work:

  if n > smallprimes[-1]:
    if is_prime( n ):   # If what's left is prime, it's easy:
      result.append( ( n, 1 ) )
    else:               # Ugh. Search stupidly for a divisor:
      d = smallprimes[-1]
      while 1:
        d = d + 2               # Try the next divisor.
        q, r = divmod( n, d )
        if q < d: break         # n < d*d means we're done, n = 1 or prime.
        if r == 0:              # d divides n. How many times?
          count = 1
          n = q
          while d <= n:                 # As long as d might still divide n,
            q, r = divmod( n, d )       # see if it does.
            if r != 0: break
            n = q                       # It does. Reduce n, increase count.
            count = count + 1
          result.append( ( d, count ) )
      if n > 1: result.append( ( n, 1 ) )

  return result



def phi( n ):
  """Return the Euler totient function of n."""

  assert isinstance( n, integer_types )

  if n < 3: return 1

  result = 1
  ff = factorization( n )
  for f in ff:
    e = f[1]
    if e > 1:
      result = result * f[0] ** (e-1) * ( f[0] - 1 )
    else:
      result = result * ( f[0] - 1 )
  return result


def carmichael( n ):
  """Return Carmichael function of n.

  Carmichael(n) is the smallest integer x such that
  m**x = 1 mod n for all m relatively prime to n.
  """

  return carmichael_of_factorized( factorization( n ) )


def carmichael_of_factorized( f_list ):
  """Return the Carmichael function of a number that is
  represented as a list of (prime,exponent) pairs.
  """

  if len( f_list ) < 1: return 1

  result = carmichael_of_ppower( f_list[0] )
  for i in range( 1, len( f_list ) ):
    result = lcm( result, carmichael_of_ppower( f_list[i] ) )

  return result

def carmichael_of_ppower( pp ):
  """Carmichael function of the given power of the given prime.
  """

  p, a = pp
  if p == 2 and a > 2: return 2**(a-2)
  else: return (p-1) * p**(a-1)



def order_mod( x, m ):
  """Return the order of x in the multiplicative group mod m.
  """

  # Warning: this implementation is not very clever, and will
  # take a long time if m is very large.

  if m <= 1: return 0

  assert gcd( x, m ) == 1

  z = x
  result = 1
  while z != 1:
    z = ( z * x ) % m
    result = result + 1
  return result


def largest_factor_relatively_prime( a, b ):
  """Return the largest factor of a relatively prime to b.
  """

  while 1:
    d = gcd( a, b )
    if d <= 1: break
    b = d
    while 1:
      q, r = divmod( a, d )
      if r > 0:
        break
      a = q
  return a


def kinda_order_mod( x, m ):
  """Return the order of x in the multiplicative group mod m',
  where m' is the largest factor of m relatively prime to x.
  """

  return order_mod( x, largest_factor_relatively_prime( m, x ) )


def is_prime( n ):
  """Return True if x is prime, False otherwise.

  We use the Miller-Rabin test, as given in Menezes et al. p. 138.
  This test is not exact: there are composite values n for which
  it returns True.

  In testing the odd numbers from 10000001 to 19999999,
  about 66 composites got past the first test,
  5 got past the second test, and none got past the third.
  Since factors of 2, 3, 5, 7, and 11 were detected during
  preliminary screening, the number of numbers tested by
  Miller-Rabin was (19999999 - 10000001)*(2/3)*(4/5)*(6/7)
  = 4.57 million.
  """

  # (This is used to study the risk of false positives:)
  global miller_rabin_test_count

  miller_rabin_test_count = 0

  if n <= smallprimes[-1]:
    if n in smallprimes: return True
    else: return False

  if gcd( n, 2*3*5*7*11 ) != 1: return False

  # Choose a number of iterations sufficient to reduce the
  # probability of accepting a composite below 2**-80
  # (from Menezes et al. Table 4.4):

  t = 40
  n_bits = 1 + int( math.log( n, 2 ) )
  for k, tt in ( ( 100, 27 ),
                 ( 150, 18 ),
                 ( 200, 15 ),
                 ( 250, 12 ),
                 ( 300,  9 ),
                 ( 350,  8 ),
                 ( 400,  7 ),
                 ( 450,  6 ),
                 ( 550,  5 ),
                 ( 650,  4 ),
                 ( 850,  3 ),
                 ( 1300, 2 ),
                 ):
    if n_bits < k: break
    t = tt

  # Run the test t times:

  s = 0
  r = n - 1
  while ( r % 2 ) == 0:
    s = s + 1
    r = r // 2
  for i in range( t ):
    a = smallprimes[ i ]
    y = modular_exp( a, r, n )
    if y != 1 and y != n-1:
      j = 1
      while j <= s - 1 and y != n - 1:
        y = modular_exp( y, 2, n )
        if y == 1:
          miller_rabin_test_count = i + 1
          return False
        j = j + 1
      if y != n-1:
        miller_rabin_test_count = i + 1
        return False
  return True


def next_prime( starting_value ):
  "Return the smallest prime larger than the starting value."

  if starting_value < 2: return 2
  result = ( starting_value + 1 ) | 1
  while not is_prime( result ): result = result + 2
  return result


smallprimes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41,
               43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97,
               101, 103, 107, 109, 113, 127, 131, 137, 139, 149,
               151, 157, 163, 167, 173, 179, 181, 191, 193, 197,
               199, 211, 223, 227, 229, 233, 239, 241, 251, 257,
               263, 269, 271, 277, 281, 283, 293, 307, 311, 313,
               317, 331, 337, 347, 349, 353, 359, 367, 373, 379,
               383, 389, 397, 401, 409, 419, 421, 431, 433, 439,
               443, 449, 457, 461, 463, 467, 479, 487, 491, 499,
               503, 509, 521, 523, 541, 547, 557, 563, 569, 571,
               577, 587, 593, 599, 601, 607, 613, 617, 619, 631,
               641, 643, 647, 653, 659, 661, 673, 677, 683, 691,
               701, 709, 719, 727, 733, 739, 743, 751, 757, 761,
               769, 773, 787, 797, 809, 811, 821, 823, 827, 829,
               839, 853, 857, 859, 863, 877, 881, 883, 887, 907,
               911, 919, 929, 937, 941, 947, 953, 967, 971, 977,
               983, 991, 997, 1009, 1013, 1019, 1021, 1031, 1033,
               1039, 1049, 1051, 1061, 1063, 1069, 1087, 1091, 1093,
               1097, 1103, 1109, 1117, 1123, 1129, 1151, 1153, 1163,
               1171, 1181, 1187, 1193, 1201, 1213, 1217, 1223, 1229]

miller_rabin_test_count = 0

def __main__():

  # Making sure locally defined exceptions work:
  # p = modular_exp( 2, -2, 3 )
  # p = square_root_mod_prime( 2, 3 )


  print_("Testing gcd...")
  assert gcd( 3*5*7, 3*5*11, 3*5*13 )     == 3*5
  assert gcd( [ 3*5*7, 3*5*11, 3*5*13 ] ) == 3*5
  assert gcd( 3 ) == 3

  print_("Testing lcm...")
  assert lcm( 3, 5*3, 7*3 )     == 3*5*7
  assert lcm( [ 3, 5*3, 7*3 ] ) == 3*5*7
  assert lcm( 3 ) == 3

  print_("Testing next_prime...")
  bigprimes = ( 999671,
                999683,
                999721,
                999727,
                999749,
                999763,
                999769,
                999773,
                999809,
                999853,
                999863,
                999883,
                999907,
                999917,
                999931,
                999953,
                999959,
                999961,
                999979,
                999983 )

  for i in range( len( bigprimes ) - 1 ):
    assert next_prime( bigprimes[i] ) == bigprimes[ i+1 ]

  error_tally = 0

  # Test the square_root_mod_prime function:

  for p in smallprimes:
    print_("Testing square_root_mod_prime for modulus p = %d." % p)
    squares = []

    for root in range( 0, 1+p//2 ):
      sq = ( root * root ) % p
      squares.append( sq )
      calculated = square_root_mod_prime( sq, p )
      if ( calculated * calculated ) % p != sq:
        error_tally = error_tally + 1
        print_("Failed to find %d as sqrt( %d ) mod %d. Said %d." % \
              ( root, sq, p, calculated ))

    for nonsquare in range( 0, p ):
      if nonsquare not in squares:
        try:
          calculated = square_root_mod_prime( nonsquare, p )
        except SquareRootError:
          pass
        else:
          error_tally = error_tally + 1
          print_("Failed to report no root for sqrt( %d ) mod %d." % \
                ( nonsquare, p ))

  # Test the jacobi function:
  for m in range( 3, 400, 2 ):
    print_("Testing jacobi for modulus m = %d." % m)
    if is_prime( m ):
      squares = []
      for root in range( 1, m ):
        if jacobi( root * root, m ) != 1:
          error_tally = error_tally + 1
          print_("jacobi( %d * %d, %d ) != 1" % ( root, root, m ))
        squares.append( root * root % m )
      for i in range( 1, m ):
        if not i in squares:
          if jacobi( i, m ) != -1:
            error_tally = error_tally + 1
            print_("jacobi( %d, %d ) != -1" % ( i, m ))
    else:       # m is not prime.
      f = factorization( m )
      for a in range( 1, m ):
        c = 1
        for i in f:
          c = c * jacobi( a, i[0] ) ** i[1]
        if c != jacobi( a, m ):
          error_tally = error_tally + 1
          print_("%d != jacobi( %d, %d )" % ( c, a, m ))


# Test the inverse_mod function:
  print_("Testing inverse_mod . . .")
  import random
  n_tests = 0
  for i in range( 100 ):
    m = random.randint( 20, 10000 )
    for j in range( 100 ):
      a = random.randint( 1, m-1 )
      if gcd( a, m ) == 1:
        n_tests = n_tests + 1
        inv = inverse_mod( a, m )
        if inv <= 0 or inv >= m or ( a * inv ) % m != 1:
          error_tally = error_tally + 1
          print_("%d = inverse_mod( %d, %d ) is wrong." % ( inv, a, m ))
  assert n_tests > 1000
  print_(n_tests, " tests of inverse_mod completed.")

  class FailedTest(Exception): pass
  print_(error_tally, "errors detected.")
  if error_tally != 0:
    raise FailedTest("%d errors detected" % error_tally)

if __name__ == '__main__':
  __main__()

########NEW FILE########
__FILENAME__ = rfc6979
'''
RFC 6979:
    Deterministic Usage of the Digital Signature Algorithm (DSA) and
    Elliptic Curve Digital Signature Algorithm (ECDSA)

    http://tools.ietf.org/html/rfc6979

Many thanks to Coda Hale for his implementation in Go language:
    https://github.com/codahale/rfc6979
'''

import hmac
from binascii import hexlify
from .util import number_to_string, number_to_string_crop
from .six import b

try:
    bin(0)
except NameError:
    binmap = {"0": "0000", "1": "0001", "2": "0010", "3": "0011",
              "4": "0100", "5": "0101", "6": "0110", "7": "0111",
              "8": "1000", "9": "1001", "a": "1010", "b": "1011",
              "c": "1100", "d": "1101", "e": "1110", "f": "1111"}
    def bin(value): # for python2.5
        v = "".join(binmap[x] for x in "%x"%abs(value)).lstrip("0")
        if value < 0:
            return "-0b" + v
        return "0b" + v

def bit_length(num):
    # http://docs.python.org/dev/library/stdtypes.html#int.bit_length
    s = bin(num)  # binary representation:  bin(-37) --> '-0b100101'
    s = s.lstrip('-0b')  # remove leading zeros and minus sign
    return len(s)  # len('100101') --> 6

def bits2int(data, qlen):
    x = int(hexlify(data), 16)
    l = len(data) * 8

    if l > qlen:
        return x >> (l-qlen)
    return x

def bits2octets(data, order):
    z1 = bits2int(data, bit_length(order))
    z2 = z1 - order

    if z2 < 0:
        z2 = z1

    return number_to_string_crop(z2, order)

# https://tools.ietf.org/html/rfc6979#section-3.2
def generate_k(generator, secexp, hash_func, data):
    '''
        generator - ECDSA generator used in the signature
        secexp - secure exponent (private key) in numeric form
        hash_func - reference to the same hash function used for generating hash
        data - hash in binary form of the signing data
    '''

    qlen = bit_length(generator.order())
    holen = hash_func().digest_size
    rolen = (qlen + 7) / 8
    bx = number_to_string(secexp, generator.order()) + bits2octets(data, generator.order())

    # Step B
    v = b('\x01') * holen

    # Step C
    k = b('\x00') * holen

    # Step D

    k = hmac.new(k, v+b('\x00')+bx, hash_func).digest()

    # Step E
    v = hmac.new(k, v, hash_func).digest()

    # Step F
    k = hmac.new(k, v+b('\x01')+bx, hash_func).digest()

    # Step G
    v = hmac.new(k, v, hash_func).digest()

    # Step H
    while True:
        # Step H1
        t = b('')

        # Step H2
        while len(t) < rolen:
            v = hmac.new(k, v, hash_func).digest()
            t += v

        # Step H3
        secret = bits2int(t, qlen)

        if secret >= 1 and secret < generator.order():
            return secret

        k = hmac.new(k, v+b('\x00'), hash_func).digest()
        v = hmac.new(k, v, hash_func).digest()

########NEW FILE########
__FILENAME__ = six
"""Utilities for writing code that runs on Python 2 and 3"""

# Copyright (c) 2010-2012 Benjamin Peterson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import operator
import sys
import types

__author__ = "Benjamin Peterson <benjamin@python.org>"
__version__ = "1.2.0"


# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str

    if sys.platform.startswith("java"):
        # Jython always uses 32 bits.
        MAXSIZE = int((1 << 31) - 1)
    else:
        # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
        class X(object):
            def __len__(self):
                return 1 << 31
        try:
            len(X())
        except OverflowError:
            # 32-bit
            MAXSIZE = int((1 << 31) - 1)
        else:
            # 64-bit
            MAXSIZE = int((1 << 63) - 1)
            del X


def _add_doc(func, doc):
    """Add documentation to a function."""
    func.__doc__ = doc


def _import_module(name):
    """Import module, returning the module after the last dot."""
    __import__(name)
    return sys.modules[name]


class _LazyDescr(object):

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, tp):
        result = self._resolve()
        setattr(obj, self.name, result)
        # This is a bit ugly, but it avoids running this again.
        delattr(tp, self.name)
        return result


class MovedModule(_LazyDescr):

    def __init__(self, name, old, new=None):
        super(MovedModule, self).__init__(name)
        if PY3:
            if new is None:
                new = name
            self.mod = new
        else:
            self.mod = old

    def _resolve(self):
        return _import_module(self.mod)


class MovedAttribute(_LazyDescr):

    def __init__(self, name, old_mod, new_mod, old_attr=None, new_attr=None):
        super(MovedAttribute, self).__init__(name)
        if PY3:
            if new_mod is None:
                new_mod = name
            self.mod = new_mod
            if new_attr is None:
                if old_attr is None:
                    new_attr = name
                else:
                    new_attr = old_attr
            self.attr = new_attr
        else:
            self.mod = old_mod
            if old_attr is None:
                old_attr = name
            self.attr = old_attr

    def _resolve(self):
        module = _import_module(self.mod)
        return getattr(module, self.attr)



class _MovedItems(types.ModuleType):
    """Lazy loading of moved objects"""


_moved_attributes = [
    MovedAttribute("cStringIO", "cStringIO", "io", "StringIO"),
    MovedAttribute("filter", "itertools", "builtins", "ifilter", "filter"),
    MovedAttribute("input", "__builtin__", "builtins", "raw_input", "input"),
    MovedAttribute("map", "itertools", "builtins", "imap", "map"),
    MovedAttribute("reload_module", "__builtin__", "imp", "reload"),
    MovedAttribute("reduce", "__builtin__", "functools"),
    MovedAttribute("StringIO", "StringIO", "io"),
    MovedAttribute("xrange", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("zip", "itertools", "builtins", "izip", "zip"),

    MovedModule("builtins", "__builtin__"),
    MovedModule("configparser", "ConfigParser"),
    MovedModule("copyreg", "copy_reg"),
    MovedModule("http_cookiejar", "cookielib", "http.cookiejar"),
    MovedModule("http_cookies", "Cookie", "http.cookies"),
    MovedModule("html_entities", "htmlentitydefs", "html.entities"),
    MovedModule("html_parser", "HTMLParser", "html.parser"),
    MovedModule("http_client", "httplib", "http.client"),
    MovedModule("email_mime_multipart", "email.MIMEMultipart", "email.mime.multipart"),
    MovedModule("email_mime_text", "email.MIMEText", "email.mime.text"),
    MovedModule("email_mime_base", "email.MIMEBase", "email.mime.base"),
    MovedModule("BaseHTTPServer", "BaseHTTPServer", "http.server"),
    MovedModule("CGIHTTPServer", "CGIHTTPServer", "http.server"),
    MovedModule("SimpleHTTPServer", "SimpleHTTPServer", "http.server"),
    MovedModule("cPickle", "cPickle", "pickle"),
    MovedModule("queue", "Queue"),
    MovedModule("reprlib", "repr"),
    MovedModule("socketserver", "SocketServer"),
    MovedModule("tkinter", "Tkinter"),
    MovedModule("tkinter_dialog", "Dialog", "tkinter.dialog"),
    MovedModule("tkinter_filedialog", "FileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_scrolledtext", "ScrolledText", "tkinter.scrolledtext"),
    MovedModule("tkinter_simpledialog", "SimpleDialog", "tkinter.simpledialog"),
    MovedModule("tkinter_tix", "Tix", "tkinter.tix"),
    MovedModule("tkinter_constants", "Tkconstants", "tkinter.constants"),
    MovedModule("tkinter_dnd", "Tkdnd", "tkinter.dnd"),
    MovedModule("tkinter_colorchooser", "tkColorChooser",
                "tkinter.colorchooser"),
    MovedModule("tkinter_commondialog", "tkCommonDialog",
                "tkinter.commondialog"),
    MovedModule("tkinter_tkfiledialog", "tkFileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_font", "tkFont", "tkinter.font"),
    MovedModule("tkinter_messagebox", "tkMessageBox", "tkinter.messagebox"),
    MovedModule("tkinter_tksimpledialog", "tkSimpleDialog",
                "tkinter.simpledialog"),
    MovedModule("urllib_robotparser", "robotparser", "urllib.robotparser"),
    MovedModule("winreg", "_winreg"),
]
for attr in _moved_attributes:
    setattr(_MovedItems, attr.name, attr)
del attr

moves = sys.modules[__name__ + ".moves"] = _MovedItems("moves")


def add_move(move):
    """Add an item to six.moves."""
    setattr(_MovedItems, move.name, move)


def remove_move(name):
    """Remove item from six.moves."""
    try:
        delattr(_MovedItems, name)
    except AttributeError:
        try:
            del moves.__dict__[name]
        except KeyError:
            raise AttributeError("no such move, %r" % (name,))


if PY3:
    _meth_func = "__func__"
    _meth_self = "__self__"

    _func_code = "__code__"
    _func_defaults = "__defaults__"

    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"
else:
    _meth_func = "im_func"
    _meth_self = "im_self"

    _func_code = "func_code"
    _func_defaults = "func_defaults"

    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"


try:
    advance_iterator = next
except NameError:
    def advance_iterator(it):
        return it.next()
next = advance_iterator


try:
    callable = callable
except NameError:
    def callable(obj):
        return any("__call__" in klass.__dict__ for klass in type(obj).__mro__)


if PY3:
    def get_unbound_function(unbound):
        return unbound

    Iterator = object
else:
    def get_unbound_function(unbound):
        return unbound.im_func

    class Iterator(object):

        def next(self):
            return type(self).__next__(self)

    callable = callable
_add_doc(get_unbound_function,
         """Get the function out of a possibly unbound function""")


get_method_function = operator.attrgetter(_meth_func)
get_method_self = operator.attrgetter(_meth_self)
get_function_code = operator.attrgetter(_func_code)
get_function_defaults = operator.attrgetter(_func_defaults)


def iterkeys(d):
    """Return an iterator over the keys of a dictionary."""
    return iter(getattr(d, _iterkeys)())

def itervalues(d):
    """Return an iterator over the values of a dictionary."""
    return iter(getattr(d, _itervalues)())

def iteritems(d):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)())


if PY3:
    def b(s):
        return s.encode("latin-1")
    def u(s):
        return s
    if sys.version_info[1] <= 1:
        def int2byte(i):
            return bytes((i,))
    else:
        # This is about 2x faster than the implementation above on 3.2+
        int2byte = operator.methodcaller("to_bytes", 1, "big")
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    def b(s):
        return s
    def u(s):
        if isinstance(s, unicode):
            return s
        return unicode(s, "unicode_escape")
    int2byte = chr
    import StringIO
    StringIO = BytesIO = StringIO.StringIO
_add_doc(b, """Byte literal""")
_add_doc(u, """Text literal""")


if PY3:
    import builtins
    exec_ = getattr(builtins, "exec")


    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value


    print_ = getattr(builtins, "print")
    del builtins

else:
    def exec_(_code_, _globs_=None, _locs_=None):
        """Execute code in a namespace."""
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec("""exec _code_ in _globs_, _locs_""")


    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")


    def print_(*args, **kwargs):
        """The new-style print function."""
        fp = kwargs.pop("file", sys.stdout)
        if fp is None:
            return
        def write(data):
            if not isinstance(data, basestring):
                data = str(data)
            fp.write(data)
        want_unicode = False
        sep = kwargs.pop("sep", None)
        if sep is not None:
            if isinstance(sep, unicode):
                want_unicode = True
            elif not isinstance(sep, str):
                raise TypeError("sep must be None or a string")
        end = kwargs.pop("end", None)
        if end is not None:
            if isinstance(end, unicode):
                want_unicode = True
            elif not isinstance(end, str):
                raise TypeError("end must be None or a string")
        if kwargs:
            raise TypeError("invalid keyword arguments to print()")
        if not want_unicode:
            for arg in args:
                if isinstance(arg, unicode):
                    want_unicode = True
                    break
        if want_unicode:
            newline = unicode("\n")
            space = unicode(" ")
        else:
            newline = "\n"
            space = " "
        if sep is None:
            sep = space
        if end is None:
            end = newline
        for i, arg in enumerate(args):
            if i:
                write(sep)
            write(arg)
        write(end)

_add_doc(reraise, """Reraise an exception.""")


def with_metaclass(meta, base=object):
    """Create a base class with a metaclass."""
    return meta("NewBase", (base,), {})

########NEW FILE########
__FILENAME__ = test_pyecdsa
from __future__ import with_statement, division

import unittest
import os
import time
import shutil
import subprocess
from binascii import hexlify, unhexlify
from hashlib import sha1, sha256, sha512

from .six import b, print_, binary_type
from .keys import SigningKey, VerifyingKey
from .keys import BadSignatureError
from . import util
from .util import sigencode_der, sigencode_strings
from .util import sigdecode_der, sigdecode_strings
from .curves import Curve, UnknownCurveError
from .curves import NIST192p, NIST224p, NIST256p, NIST384p, NIST521p, SECP256k1
from .ellipticcurve import Point
from . import der
from . import rfc6979

class SubprocessError(Exception):
    pass

def run_openssl(cmd):
    OPENSSL = "openssl"
    p = subprocess.Popen([OPENSSL] + cmd.split(),
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    stdout, ignored = p.communicate()
    if p.returncode != 0:
        raise SubprocessError("cmd '%s %s' failed: rc=%s, stdout/err was %s" %
                              (OPENSSL, cmd, p.returncode, stdout))
    return stdout.decode()

BENCH = False

class ECDSA(unittest.TestCase):
    def test_basic(self):
        priv = SigningKey.generate()
        pub = priv.get_verifying_key()

        data = b("blahblah")
        sig = priv.sign(data)

        self.assertTrue(pub.verify(sig, data))
        self.assertRaises(BadSignatureError, pub.verify, sig, data+b("bad"))

        pub2 = VerifyingKey.from_string(pub.to_string())
        self.assertTrue(pub2.verify(sig, data))

    def test_deterministic(self):
        data = b("blahblah")
        secexp = int("9d0219792467d7d37b4d43298a7d0c05", 16)

        priv = SigningKey.from_secret_exponent(secexp, SECP256k1, sha256)
        pub = priv.get_verifying_key()

        k = rfc6979.generate_k(SECP256k1.generator, secexp, sha256, sha256(data).digest())

        sig1 = priv.sign(data, k=k)
        self.assertTrue(pub.verify(sig1, data))

        sig2 = priv.sign(data, k=k)
        self.assertTrue(pub.verify(sig2, data))

        sig3 = priv.sign_deterministic(data, sha256)
        self.assertTrue(pub.verify(sig3, data))

        self.assertEqual(sig1, sig2)
        self.assertEqual(sig1, sig3)

    def test_bad_usage(self):
        # sk=SigningKey() is wrong
        self.assertRaises(TypeError, SigningKey)
        self.assertRaises(TypeError, VerifyingKey)

    def test_lengths(self):
        default = NIST192p
        priv = SigningKey.generate()
        pub = priv.get_verifying_key()
        self.assertEqual(len(pub.to_string()), default.verifying_key_length)
        sig = priv.sign(b("data"))
        self.assertEqual(len(sig), default.signature_length)
        if BENCH:
            print_()
        for curve in (NIST192p, NIST224p, NIST256p, NIST384p, NIST521p):
            start = time.time()
            priv = SigningKey.generate(curve=curve)
            pub1 = priv.get_verifying_key()
            keygen_time = time.time() - start
            pub2 = VerifyingKey.from_string(pub1.to_string(), curve)
            self.assertEqual(pub1.to_string(), pub2.to_string())
            self.assertEqual(len(pub1.to_string()),
                                 curve.verifying_key_length)
            start = time.time()
            sig = priv.sign(b("data"))
            sign_time = time.time() - start
            self.assertEqual(len(sig), curve.signature_length)
            if BENCH:
                start = time.time()
                pub1.verify(sig, b("data"))
                verify_time = time.time() - start
                print_("%s: siglen=%d, keygen=%0.3fs, sign=%0.3f, verify=%0.3f" \
                      % (curve.name, curve.signature_length,
                         keygen_time, sign_time, verify_time))

    def test_serialize(self):
        seed = b("secret")
        curve = NIST192p
        secexp1 = util.randrange_from_seed__trytryagain(seed, curve.order)
        secexp2 = util.randrange_from_seed__trytryagain(seed, curve.order)
        self.assertEqual(secexp1, secexp2)
        priv1 = SigningKey.from_secret_exponent(secexp1, curve)
        priv2 = SigningKey.from_secret_exponent(secexp2, curve)
        self.assertEqual(hexlify(priv1.to_string()),
                             hexlify(priv2.to_string()))
        self.assertEqual(priv1.to_pem(), priv2.to_pem())
        pub1 = priv1.get_verifying_key()
        pub2 = priv2.get_verifying_key()
        data = b("data")
        sig1 = priv1.sign(data)
        sig2 = priv2.sign(data)
        self.assertTrue(pub1.verify(sig1, data))
        self.assertTrue(pub2.verify(sig1, data))
        self.assertTrue(pub1.verify(sig2, data))
        self.assertTrue(pub2.verify(sig2, data))
        self.assertEqual(hexlify(pub1.to_string()),
                             hexlify(pub2.to_string()))

    def test_nonrandom(self):
        s = b("all the entropy in the entire world, compressed into one line")
        def not_much_entropy(numbytes):
            return s[:numbytes]
        # we control the entropy source, these two keys should be identical:
        priv1 = SigningKey.generate(entropy=not_much_entropy)
        priv2 = SigningKey.generate(entropy=not_much_entropy)
        self.assertEqual(hexlify(priv1.get_verifying_key().to_string()),
                             hexlify(priv2.get_verifying_key().to_string()))
        # likewise, signatures should be identical. Obviously you'd never
        # want to do this with keys you care about, because the secrecy of
        # the private key depends upon using different random numbers for
        # each signature
        sig1 = priv1.sign(b("data"), entropy=not_much_entropy)
        sig2 = priv2.sign(b("data"), entropy=not_much_entropy)
        self.assertEqual(hexlify(sig1), hexlify(sig2))

    def assertTruePrivkeysEqual(self, priv1, priv2):
        self.assertEqual(priv1.privkey.secret_multiplier,
                             priv2.privkey.secret_multiplier)
        self.assertEqual(priv1.privkey.public_key.generator,
                             priv2.privkey.public_key.generator)

    def failIfPrivkeysEqual(self, priv1, priv2):
        self.failIfEqual(priv1.privkey.secret_multiplier,
                         priv2.privkey.secret_multiplier)

    def test_privkey_creation(self):
        s = b("all the entropy in the entire world, compressed into one line")
        def not_much_entropy(numbytes):
            return s[:numbytes]
        priv1 = SigningKey.generate()
        self.assertEqual(priv1.baselen, NIST192p.baselen)

        priv1 = SigningKey.generate(curve=NIST224p)
        self.assertEqual(priv1.baselen, NIST224p.baselen)

        priv1 = SigningKey.generate(entropy=not_much_entropy)
        self.assertEqual(priv1.baselen, NIST192p.baselen)
        priv2 = SigningKey.generate(entropy=not_much_entropy)
        self.assertEqual(priv2.baselen, NIST192p.baselen)
        self.assertTruePrivkeysEqual(priv1, priv2)

        priv1 = SigningKey.from_secret_exponent(secexp=3)
        self.assertEqual(priv1.baselen, NIST192p.baselen)
        priv2 = SigningKey.from_secret_exponent(secexp=3)
        self.assertTruePrivkeysEqual(priv1, priv2)

        priv1 = SigningKey.from_secret_exponent(secexp=4, curve=NIST224p)
        self.assertEqual(priv1.baselen, NIST224p.baselen)

    def test_privkey_strings(self):
        priv1 = SigningKey.generate()
        s1 = priv1.to_string()
        self.assertEqual(type(s1), binary_type)
        self.assertEqual(len(s1), NIST192p.baselen)
        priv2 = SigningKey.from_string(s1)
        self.assertTruePrivkeysEqual(priv1, priv2)

        s1 = priv1.to_pem()
        self.assertEqual(type(s1), binary_type)
        self.assertTrue(s1.startswith(b("-----BEGIN EC PRIVATE KEY-----")))
        self.assertTrue(s1.strip().endswith(b("-----END EC PRIVATE KEY-----")))
        priv2 = SigningKey.from_pem(s1)
        self.assertTruePrivkeysEqual(priv1, priv2)

        s1 = priv1.to_der()
        self.assertEqual(type(s1), binary_type)
        priv2 = SigningKey.from_der(s1)
        self.assertTruePrivkeysEqual(priv1, priv2)

        priv1 = SigningKey.generate(curve=NIST256p)
        s1 = priv1.to_pem()
        self.assertEqual(type(s1), binary_type)
        self.assertTrue(s1.startswith(b("-----BEGIN EC PRIVATE KEY-----")))
        self.assertTrue(s1.strip().endswith(b("-----END EC PRIVATE KEY-----")))
        priv2 = SigningKey.from_pem(s1)
        self.assertTruePrivkeysEqual(priv1, priv2)

        s1 = priv1.to_der()
        self.assertEqual(type(s1), binary_type)
        priv2 = SigningKey.from_der(s1)
        self.assertTruePrivkeysEqual(priv1, priv2)

    def assertTruePubkeysEqual(self, pub1, pub2):
        self.assertEqual(pub1.pubkey.point, pub2.pubkey.point)
        self.assertEqual(pub1.pubkey.generator, pub2.pubkey.generator)
        self.assertEqual(pub1.curve, pub2.curve)

    def test_pubkey_strings(self):
        priv1 = SigningKey.generate()
        pub1 = priv1.get_verifying_key()
        s1 = pub1.to_string()
        self.assertEqual(type(s1), binary_type)
        self.assertEqual(len(s1), NIST192p.verifying_key_length)
        pub2 = VerifyingKey.from_string(s1)
        self.assertTruePubkeysEqual(pub1, pub2)

        priv1 = SigningKey.generate(curve=NIST256p)
        pub1 = priv1.get_verifying_key()
        s1 = pub1.to_string()
        self.assertEqual(type(s1), binary_type)
        self.assertEqual(len(s1), NIST256p.verifying_key_length)
        pub2 = VerifyingKey.from_string(s1, curve=NIST256p)
        self.assertTruePubkeysEqual(pub1, pub2)

        pub1_der = pub1.to_der()
        self.assertEqual(type(pub1_der), binary_type)
        pub2 = VerifyingKey.from_der(pub1_der)
        self.assertTruePubkeysEqual(pub1, pub2)

        self.assertRaises(der.UnexpectedDER,
                              VerifyingKey.from_der, pub1_der+b("junk"))
        badpub = VerifyingKey.from_der(pub1_der)
        class FakeGenerator:
            def order(self): return 123456789
        badcurve = Curve("unknown", None, FakeGenerator(), (1,2,3,4,5,6))
        badpub.curve = badcurve
        badder = badpub.to_der()
        self.assertRaises(UnknownCurveError, VerifyingKey.from_der, badder)

        pem = pub1.to_pem()
        self.assertEqual(type(pem), binary_type)
        self.assertTrue(pem.startswith(b("-----BEGIN PUBLIC KEY-----")), pem)
        self.assertTrue(pem.strip().endswith(b("-----END PUBLIC KEY-----")), pem)
        pub2 = VerifyingKey.from_pem(pem)
        self.assertTruePubkeysEqual(pub1, pub2)

    def test_signature_strings(self):
        priv1 = SigningKey.generate()
        pub1 = priv1.get_verifying_key()
        data = b("data")

        sig = priv1.sign(data)
        self.assertEqual(type(sig), binary_type)
        self.assertEqual(len(sig), NIST192p.signature_length)
        self.assertTrue(pub1.verify(sig, data))

        sig = priv1.sign(data, sigencode=sigencode_strings)
        self.assertEqual(type(sig), tuple)
        self.assertEqual(len(sig), 2)
        self.assertEqual(type(sig[0]), binary_type)
        self.assertEqual(type(sig[1]), binary_type)
        self.assertEqual(len(sig[0]), NIST192p.baselen)
        self.assertEqual(len(sig[1]), NIST192p.baselen)
        self.assertTrue(pub1.verify(sig, data, sigdecode=sigdecode_strings))

        sig_der = priv1.sign(data, sigencode=sigencode_der)
        self.assertEqual(type(sig_der), binary_type)
        self.assertTrue(pub1.verify(sig_der, data, sigdecode=sigdecode_der))

    def test_hashfunc(self):
        sk = SigningKey.generate(curve=NIST256p, hashfunc=sha256)
        data = b("security level is 128 bits")
        sig = sk.sign(data)
        vk = VerifyingKey.from_string(sk.get_verifying_key().to_string(),
                                      curve=NIST256p, hashfunc=sha256)
        self.assertTrue(vk.verify(sig, data))

        sk2 = SigningKey.generate(curve=NIST256p)
        sig2 = sk2.sign(data, hashfunc=sha256)
        vk2 = VerifyingKey.from_string(sk2.get_verifying_key().to_string(),
                                       curve=NIST256p, hashfunc=sha256)
        self.assertTrue(vk2.verify(sig2, data))

        vk3 = VerifyingKey.from_string(sk.get_verifying_key().to_string(),
                                       curve=NIST256p)
        self.assertTrue(vk3.verify(sig, data, hashfunc=sha256))


class OpenSSL(unittest.TestCase):
    # test interoperability with OpenSSL tools. Note that openssl's ECDSA
    # sign/verify arguments changed between 0.9.8 and 1.0.0: the early
    # versions require "-ecdsa-with-SHA1", the later versions want just
    # "-SHA1" (or to leave out that argument entirely, which means the
    # signature will use some default digest algorithm, probably determined
    # by the key, probably always SHA1).
    #
    # openssl ecparam -name secp224r1 -genkey -out privkey.pem
    # openssl ec -in privkey.pem -text -noout # get the priv/pub keys
    # openssl dgst -ecdsa-with-SHA1 -sign privkey.pem -out data.sig data.txt
    # openssl asn1parse -in data.sig -inform DER
    #  data.sig is 64 bytes, probably 56b plus ASN1 overhead
    # openssl dgst -ecdsa-with-SHA1 -prverify privkey.pem -signature data.sig data.txt ; echo $?
    # openssl ec -in privkey.pem -pubout -out pubkey.pem
    # openssl ec -in privkey.pem -pubout -outform DER -out pubkey.der

    def get_openssl_messagedigest_arg(self):
        v = run_openssl("version")
        # e.g. "OpenSSL 1.0.0 29 Mar 2010", or "OpenSSL 1.0.0a 1 Jun 2010",
        # or "OpenSSL 0.9.8o 01 Jun 2010"
        vs = v.split()[1].split(".")
        if vs >= ["1","0","0"]:
            return "-SHA1"
        else:
            return "-ecdsa-with-SHA1"

    # sk: 1:OpenSSL->python  2:python->OpenSSL
    # vk: 3:OpenSSL->python  4:python->OpenSSL
    # sig: 5:OpenSSL->python 6:python->OpenSSL

    def test_from_openssl_nist192p(self):
        return self.do_test_from_openssl(NIST192p, "prime192v1")
    def test_from_openssl_nist224p(self):
        return self.do_test_from_openssl(NIST224p, "secp224r1")
    def test_from_openssl_nist384p(self):
        return self.do_test_from_openssl(NIST384p, "secp384r1")
    def test_from_openssl_nist521p(self):
        return self.do_test_from_openssl(NIST521p, "secp521r1")

    def do_test_from_openssl(self, curve, curvename):
        # OpenSSL: create sk, vk, sign.
        # Python: read vk(3), checksig(5), read sk(1), sign, check
        mdarg = self.get_openssl_messagedigest_arg()
        if os.path.isdir("t"):
            shutil.rmtree("t")
        os.mkdir("t")
        run_openssl("ecparam -name %s -genkey -out t/privkey.pem" % curvename)
        run_openssl("ec -in t/privkey.pem -pubout -out t/pubkey.pem")
        data = b("data")
        with open("t/data.txt","wb") as e: e.write(data)
        run_openssl("dgst %s -sign t/privkey.pem -out t/data.sig t/data.txt" % mdarg)
        run_openssl("dgst %s -verify t/pubkey.pem -signature t/data.sig t/data.txt" % mdarg)
        with open("t/pubkey.pem","rb") as e: pubkey_pem = e.read()
        vk = VerifyingKey.from_pem(pubkey_pem) # 3
        with open("t/data.sig","rb") as e: sig_der = e.read()
        self.assertTrue(vk.verify(sig_der, data, # 5
                                  hashfunc=sha1, sigdecode=sigdecode_der))

        with open("t/privkey.pem") as e: fp = e.read()
        sk = SigningKey.from_pem(fp) # 1
        sig = sk.sign(data)
        self.assertTrue(vk.verify(sig, data))

    def test_to_openssl_nist192p(self):
        self.do_test_to_openssl(NIST192p, "prime192v1")
    def test_to_openssl_nist224p(self):
        self.do_test_to_openssl(NIST224p, "secp224r1")
    def test_to_openssl_nist384p(self):
        self.do_test_to_openssl(NIST384p, "secp384r1")
    def test_to_openssl_nist521p(self):
        self.do_test_to_openssl(NIST521p, "secp521r1")

    def do_test_to_openssl(self, curve, curvename):
        # Python: create sk, vk, sign.
        # OpenSSL: read vk(4), checksig(6), read sk(2), sign, check
        mdarg = self.get_openssl_messagedigest_arg()
        if os.path.isdir("t"):
            shutil.rmtree("t")
        os.mkdir("t")
        sk = SigningKey.generate(curve=curve)
        vk = sk.get_verifying_key()
        data = b("data")
        with open("t/pubkey.der","wb") as e: e.write(vk.to_der()) # 4
        with open("t/pubkey.pem","wb") as e: e.write(vk.to_pem()) # 4
        sig_der = sk.sign(data, hashfunc=sha1, sigencode=sigencode_der)

        with open("t/data.sig","wb") as e: e.write(sig_der) # 6
        with open("t/data.txt","wb") as e: e.write(data)
        with open("t/baddata.txt","wb") as e: e.write(data+b("corrupt"))

        self.assertRaises(SubprocessError, run_openssl,
                              "dgst %s -verify t/pubkey.der -keyform DER -signature t/data.sig t/baddata.txt" % mdarg)
        run_openssl("dgst %s -verify t/pubkey.der -keyform DER -signature t/data.sig t/data.txt" % mdarg)

        with open("t/privkey.pem","wb") as e: e.write(sk.to_pem()) # 2
        run_openssl("dgst %s -sign t/privkey.pem -out t/data.sig2 t/data.txt" % mdarg)
        run_openssl("dgst %s -verify t/pubkey.pem -signature t/data.sig2 t/data.txt" % mdarg)

class DER(unittest.TestCase):
    def test_oids(self):
        oid_ecPublicKey = der.encode_oid(1, 2, 840, 10045, 2, 1)
        self.assertEqual(hexlify(oid_ecPublicKey), b("06072a8648ce3d0201"))
        self.assertEqual(hexlify(NIST224p.encoded_oid), b("06052b81040021"))
        self.assertEqual(hexlify(NIST256p.encoded_oid),
                             b("06082a8648ce3d030107"))
        x = oid_ecPublicKey + b("more")
        x1, rest = der.remove_object(x)
        self.assertEqual(x1, (1, 2, 840, 10045, 2, 1))
        self.assertEqual(rest, b("more"))

    def test_integer(self):
        self.assertEqual(der.encode_integer(0), b("\x02\x01\x00"))
        self.assertEqual(der.encode_integer(1), b("\x02\x01\x01"))
        self.assertEqual(der.encode_integer(127), b("\x02\x01\x7f"))
        self.assertEqual(der.encode_integer(128), b("\x02\x02\x00\x80"))
        self.assertEqual(der.encode_integer(256), b("\x02\x02\x01\x00"))
        #self.assertEqual(der.encode_integer(-1), b("\x02\x01\xff"))

        def s(n): return der.remove_integer(der.encode_integer(n) + b("junk"))
        self.assertEqual(s(0), (0, b("junk")))
        self.assertEqual(s(1), (1, b("junk")))
        self.assertEqual(s(127), (127, b("junk")))
        self.assertEqual(s(128), (128, b("junk")))
        self.assertEqual(s(256), (256, b("junk")))
        self.assertEqual(s(1234567890123456789012345678901234567890),
                             (1234567890123456789012345678901234567890,b("junk")))

    def test_number(self):
        self.assertEqual(der.encode_number(0), b("\x00"))
        self.assertEqual(der.encode_number(127), b("\x7f"))
        self.assertEqual(der.encode_number(128), b("\x81\x00"))
        self.assertEqual(der.encode_number(3*128+7), b("\x83\x07"))
        #self.assertEqual(der.read_number("\x81\x9b"+"more"), (155, 2))
        #self.assertEqual(der.encode_number(155), b("\x81\x9b"))
        for n in (0, 1, 2, 127, 128, 3*128+7, 840, 10045): #, 155):
            x = der.encode_number(n) + b("more")
            n1, llen = der.read_number(x)
            self.assertEqual(n1, n)
            self.assertEqual(x[llen:], b("more"))

    def test_length(self):
        self.assertEqual(der.encode_length(0), b("\x00"))
        self.assertEqual(der.encode_length(127), b("\x7f"))
        self.assertEqual(der.encode_length(128), b("\x81\x80"))
        self.assertEqual(der.encode_length(255), b("\x81\xff"))
        self.assertEqual(der.encode_length(256), b("\x82\x01\x00"))
        self.assertEqual(der.encode_length(3*256+7), b("\x82\x03\x07"))
        self.assertEqual(der.read_length(b("\x81\x9b")+b("more")), (155, 2))
        self.assertEqual(der.encode_length(155), b("\x81\x9b"))
        for n in (0, 1, 2, 127, 128, 255, 256, 3*256+7, 155):
            x = der.encode_length(n) + b("more")
            n1, llen = der.read_length(x)
            self.assertEqual(n1, n)
            self.assertEqual(x[llen:], b("more"))

    def test_sequence(self):
        x = der.encode_sequence(b("ABC"), b("DEF")) + b("GHI")
        self.assertEqual(x, b("\x30\x06ABCDEFGHI"))
        x1, rest = der.remove_sequence(x)
        self.assertEqual(x1, b("ABCDEF"))
        self.assertEqual(rest, b("GHI"))

    def test_constructed(self):
        x = der.encode_constructed(0, NIST224p.encoded_oid)
        self.assertEqual(hexlify(x), b("a007") + b("06052b81040021"))
        x = der.encode_constructed(1, unhexlify(b("0102030a0b0c")))
        self.assertEqual(hexlify(x), b("a106") + b("0102030a0b0c"))

class Util(unittest.TestCase):
    def test_trytryagain(self):
        tta = util.randrange_from_seed__trytryagain
        for i in range(1000):
            seed = "seed-%d" % i
            for order in (2**8-2, 2**8-1, 2**8, 2**8+1, 2**8+2,
                          2**16-1, 2**16+1):
                n = tta(seed, order)
                self.assertTrue(1 <= n < order, (1, n, order))
        # this trytryagain *does* provide long-term stability
        self.assertEqual(("%x"%(tta("seed", NIST224p.order))).encode(),
                             b("6fa59d73bf0446ae8743cf748fc5ac11d5585a90356417e97155c3bc"))

    def test_randrange(self):
        # util.randrange does not provide long-term stability: we might
        # change the algorithm in the future.
        for i in range(1000):
            entropy = util.PRNG("seed-%d" % i)
            for order in (2**8-2, 2**8-1, 2**8,
                          2**16-1, 2**16+1,
                          ):
                # that oddball 2**16+1 takes half our runtime
                n = util.randrange(order, entropy=entropy)
                self.assertTrue(1 <= n < order, (1, n, order))

    def OFF_test_prove_uniformity(self):
        order = 2**8-2
        counts = dict([(i, 0) for i in range(1, order)])
        assert 0 not in counts
        assert order not in counts
        for i in range(1000000):
            seed = "seed-%d" % i
            n = util.randrange_from_seed__trytryagain(seed, order)
            counts[n] += 1
        # this technique should use the full range
        self.assertTrue(counts[order-1])
        for i in range(1, order):
            print_("%3d: %s" % (i, "*"*(counts[i]//100)))

class RFC6979(unittest.TestCase):
    # https://tools.ietf.org/html/rfc6979#appendix-A.1
    def _do(self, generator, secexp, hsh, hash_func, expected):
        actual = rfc6979.generate_k(generator, secexp, hash_func, hsh)
        self.assertEqual(expected, actual)

    def test_SECP256k1(self):
        '''RFC doesn't contain test vectors for SECP256k1 used in bitcoin.
        This vector has been computed by Golang reference implementation instead.'''
        self._do(
            generator = SECP256k1.generator,
            secexp = int("9d0219792467d7d37b4d43298a7d0c05", 16),
            hsh = sha256(b("sample")).digest(),
            hash_func = sha256,
            expected = int("8fa1f95d514760e498f28957b824ee6ec39ed64826ff4fecc2b5739ec45b91cd", 16))

    def test_SECP256k1_2(self):
        self._do(
            generator=SECP256k1.generator,
            secexp=int("cca9fbcc1b41e5a95d369eaa6ddcff73b61a4efaa279cfc6567e8daa39cbaf50", 16),
            hsh=sha256(b("sample")).digest(),
            hash_func=sha256,
            expected=int("2df40ca70e639d89528a6b670d9d48d9165fdc0febc0974056bdce192b8e16a3", 16))

    def test_SECP256k1_3(self):
        self._do(
            generator=SECP256k1.generator,
            secexp=0x1,
            hsh=sha256(b("Satoshi Nakamoto")).digest(),
            hash_func=sha256,
            expected=0x8F8A276C19F4149656B280621E358CCE24F5F52542772691EE69063B74F15D15)

    def test_SECP256k1_4(self):
        self._do(
            generator=SECP256k1.generator,
            secexp=0x1,
            hsh=sha256(b("All those moments will be lost in time, like tears in rain. Time to die...")).digest(),
            hash_func=sha256,
            expected=0x38AA22D72376B4DBC472E06C3BA403EE0A394DA63FC58D88686C611ABA98D6B3)

    def test_SECP256k1_5(self):
        self._do(
            generator=SECP256k1.generator,
            secexp=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140,
            hsh=sha256(b("Satoshi Nakamoto")).digest(),
            hash_func=sha256,
            expected=0x33A19B60E25FB6F4435AF53A3D42D493644827367E6453928554F43E49AA6F90)

    def test_SECP256k1_6(self):
        self._do(
            generator=SECP256k1.generator,
            secexp=0xf8b8af8ce3c7cca5e300d33939540c10d45ce001b8f252bfbc57ba0342904181,
            hsh=sha256(b("Alan Turing")).digest(),
            hash_func=sha256,
            expected=0x525A82B70E67874398067543FD84C83D30C175FDC45FDEEE082FE13B1D7CFDF1)

    def test_1(self):
        # Basic example of the RFC, it also tests 'try-try-again' from Step H of rfc6979
        self._do(
            generator = Point(None, 0, 0, int("4000000000000000000020108A2E0CC0D99F8A5EF", 16)),
            secexp = int("09A4D6792295A7F730FC3F2B49CBC0F62E862272F", 16),
            hsh = unhexlify(b("AF2BDBE1AA9B6EC1E2ADE1D694F41FC71A831D0268E9891562113D8A62ADD1BF")),
            hash_func = sha256,
            expected = int("23AF4074C90A02B3FE61D286D5C87F425E6BDD81B", 16))

    def test_2(self):
        self._do(
            generator=NIST192p.generator,
            secexp = int("6FAB034934E4C0FC9AE67F5B5659A9D7D1FEFD187EE09FD4", 16),
            hsh = sha1(b("sample")).digest(),
            hash_func = sha1,
            expected = int("37D7CA00D2C7B0E5E412AC03BD44BA837FDD5B28CD3B0021", 16))

    def test_3(self):
        self._do(
            generator=NIST192p.generator,
            secexp = int("6FAB034934E4C0FC9AE67F5B5659A9D7D1FEFD187EE09FD4", 16),
            hsh = sha256(b("sample")).digest(),
            hash_func = sha256,
            expected = int("32B1B6D7D42A05CB449065727A84804FB1A3E34D8F261496", 16))

    def test_4(self):
        self._do(
            generator=NIST192p.generator,
            secexp = int("6FAB034934E4C0FC9AE67F5B5659A9D7D1FEFD187EE09FD4", 16),
            hsh = sha512(b("sample")).digest(),
            hash_func = sha512,
            expected = int("A2AC7AB055E4F20692D49209544C203A7D1F2C0BFBC75DB1", 16))

    def test_5(self):
        self._do(
            generator=NIST192p.generator,
            secexp = int("6FAB034934E4C0FC9AE67F5B5659A9D7D1FEFD187EE09FD4", 16),
            hsh = sha1(b("test")).digest(),
            hash_func = sha1,
            expected = int("D9CF9C3D3297D3260773A1DA7418DB5537AB8DD93DE7FA25", 16))

    def test_6(self):
        self._do(
            generator=NIST192p.generator,
            secexp = int("6FAB034934E4C0FC9AE67F5B5659A9D7D1FEFD187EE09FD4", 16),
            hsh = sha256(b("test")).digest(),
            hash_func = sha256,
            expected = int("5C4CE89CF56D9E7C77C8585339B006B97B5F0680B4306C6C", 16))

    def test_7(self):
        self._do(
            generator=NIST192p.generator,
            secexp = int("6FAB034934E4C0FC9AE67F5B5659A9D7D1FEFD187EE09FD4", 16),
            hsh = sha512(b("test")).digest(),
            hash_func = sha512,
            expected = int("0758753A5254759C7CFBAD2E2D9B0792EEE44136C9480527", 16))

    def test_8(self):
        self._do(
            generator=NIST521p.generator,
            secexp = int("0FAD06DAA62BA3B25D2FB40133DA757205DE67F5BB0018FEE8C86E1B68C7E75CAA896EB32F1F47C70855836A6D16FCC1466F6D8FBEC67DB89EC0C08B0E996B83538", 16),
            hsh = sha1(b("sample")).digest(),
            hash_func = sha1,
            expected = int("089C071B419E1C2820962321787258469511958E80582E95D8378E0C2CCDB3CB42BEDE42F50E3FA3C71F5A76724281D31D9C89F0F91FC1BE4918DB1C03A5838D0F9", 16))

    def test_9(self):
        self._do(
            generator=NIST521p.generator,
            secexp = int("0FAD06DAA62BA3B25D2FB40133DA757205DE67F5BB0018FEE8C86E1B68C7E75CAA896EB32F1F47C70855836A6D16FCC1466F6D8FBEC67DB89EC0C08B0E996B83538", 16),
            hsh = sha256(b("sample")).digest(),
            hash_func = sha256,
            expected = int("0EDF38AFCAAECAB4383358B34D67C9F2216C8382AAEA44A3DAD5FDC9C32575761793FEF24EB0FC276DFC4F6E3EC476752F043CF01415387470BCBD8678ED2C7E1A0", 16))

    def test_10(self):
        self._do(
            generator=NIST521p.generator,
            secexp = int("0FAD06DAA62BA3B25D2FB40133DA757205DE67F5BB0018FEE8C86E1B68C7E75CAA896EB32F1F47C70855836A6D16FCC1466F6D8FBEC67DB89EC0C08B0E996B83538", 16),
            hsh = sha512(b("test")).digest(),
            hash_func = sha512,
            expected = int("16200813020EC986863BEDFC1B121F605C1215645018AEA1A7B215A564DE9EB1B38A67AA1128B80CE391C4FB71187654AAA3431027BFC7F395766CA988C964DC56D", 16))

def __main__():
    unittest.main()
if __name__ == "__main__":
    __main__()

########NEW FILE########
__FILENAME__ = util
from __future__ import division

import os
import math
import binascii
from hashlib import sha256
from . import der
from .curves import orderlen
from .six import PY3, int2byte, b, next

# RFC5480:
#   The "unrestricted" algorithm identifier is:
#     id-ecPublicKey OBJECT IDENTIFIER ::= {
#       iso(1) member-body(2) us(840) ansi-X9-62(10045) keyType(2) 1 }

oid_ecPublicKey = (1, 2, 840, 10045, 2, 1)
encoded_oid_ecPublicKey = der.encode_oid(*oid_ecPublicKey)

def randrange(order, entropy=None):
    """Return a random integer k such that 1 <= k < order, uniformly
    distributed across that range. For simplicity, this only behaves well if
    'order' is fairly close (but below) a power of 256. The try-try-again
    algorithm we use takes longer and longer time (on average) to complete as
    'order' falls, rising to a maximum of avg=512 loops for the worst-case
    (256**k)+1 . All of the standard curves behave well. There is a cutoff at
    10k loops (which raises RuntimeError) to prevent an infinite loop when
    something is really broken like the entropy function not working.

    Note that this function is not declared to be forwards-compatible: we may
    change the behavior in future releases. The entropy= argument (which
    should get a callable that behaves like os.entropy) can be used to
    achieve stability within a given release (for repeatable unit tests), but
    should not be used as a long-term-compatible key generation algorithm.
    """
    # we could handle arbitrary orders (even 256**k+1) better if we created
    # candidates bit-wise instead of byte-wise, which would reduce the
    # worst-case behavior to avg=2 loops, but that would be more complex. The
    # change would be to round the order up to a power of 256, subtract one
    # (to get 0xffff..), use that to get a byte-long mask for the top byte,
    # generate the len-1 entropy bytes, generate one extra byte and mask off
    # the top bits, then combine it with the rest. Requires jumping back and
    # forth between strings and integers a lot.

    if entropy is None:
        entropy = os.urandom
    assert order > 1
    bytes = orderlen(order)
    dont_try_forever = 10000 # gives about 2**-60 failures for worst case
    while dont_try_forever > 0:
        dont_try_forever -= 1
        candidate = string_to_number(entropy(bytes)) + 1
        if 1 <= candidate < order:
            return candidate
        continue
    raise RuntimeError("randrange() tried hard but gave up, either something"
                       " is very wrong or you got realllly unlucky. Order was"
                       " %x" % order)

class PRNG:
    # this returns a callable which, when invoked with an integer N, will
    # return N pseudorandom bytes. Note: this is a short-term PRNG, meant
    # primarily for the needs of randrange_from_seed__trytryagain(), which
    # only needs to run it a few times per seed. It does not provide
    # protection against state compromise (forward security).
    def __init__(self, seed):
        self.generator = self.block_generator(seed)

    def __call__(self, numbytes):
        a = [next(self.generator) for i in range(numbytes)]

        if PY3:
            return bytes(a)
        else:
            return "".join(a)


    def block_generator(self, seed):
        counter = 0
        while True:
            for byte in sha256(("prng-%d-%s" % (counter, seed)).encode()).digest():
                yield byte
            counter += 1

def randrange_from_seed__overshoot_modulo(seed, order):
    # hash the data, then turn the digest into a number in [1,order).
    #
    # We use David-Sarah Hopwood's suggestion: turn it into a number that's
    # sufficiently larger than the group order, then modulo it down to fit.
    # This should give adequate (but not perfect) uniformity, and simple
    # code. There are other choices: try-try-again is the main one.
    base = PRNG(seed)(2*orderlen(order))
    number = (int(binascii.hexlify(base), 16) % (order-1)) + 1
    assert 1 <= number < order, (1, number, order)
    return number

def lsb_of_ones(numbits):
    return (1 << numbits) - 1
def bits_and_bytes(order):
    bits = int(math.log(order-1, 2)+1)
    bytes = bits // 8
    extrabits = bits % 8
    return bits, bytes, extrabits

# the following randrange_from_seed__METHOD() functions take an
# arbitrarily-sized secret seed and turn it into a number that obeys the same
# range limits as randrange() above. They are meant for deriving consistent
# signing keys from a secret rather than generating them randomly, for
# example a protocol in which three signing keys are derived from a master
# secret. You should use a uniformly-distributed unguessable seed with about
# curve.baselen bytes of entropy. To use one, do this:
#   seed = os.urandom(curve.baselen) # or other starting point
#   secexp = ecdsa.util.randrange_from_seed__trytryagain(sed, curve.order)
#   sk = SigningKey.from_secret_exponent(secexp, curve)

def randrange_from_seed__truncate_bytes(seed, order, hashmod=sha256):
    # hash the seed, then turn the digest into a number in [1,order), but
    # don't worry about trying to uniformly fill the range. This will lose,
    # on average, four bits of entropy.
    bits, bytes, extrabits = bits_and_bytes(order)
    if extrabits:
        bytes += 1
    base = hashmod(seed).digest()[:bytes]
    base = "\x00"*(bytes-len(base)) + base
    number = 1+int(binascii.hexlify(base), 16)
    assert 1 <= number < order
    return number

def randrange_from_seed__truncate_bits(seed, order, hashmod=sha256):
    # like string_to_randrange_truncate_bytes, but only lose an average of
    # half a bit
    bits = int(math.log(order-1, 2)+1)
    maxbytes = (bits+7) // 8
    base = hashmod(seed).digest()[:maxbytes]
    base = "\x00"*(maxbytes-len(base)) + base
    topbits = 8*maxbytes - bits
    if topbits:
        base = int2byte(ord(base[0]) & lsb_of_ones(topbits)) + base[1:]
    number = 1+int(binascii.hexlify(base), 16)
    assert 1 <= number < order
    return number

def randrange_from_seed__trytryagain(seed, order):
    # figure out exactly how many bits we need (rounded up to the nearest
    # bit), so we can reduce the chance of looping to less than 0.5 . This is
    # specified to feed from a byte-oriented PRNG, and discards the
    # high-order bits of the first byte as necessary to get the right number
    # of bits. The average number of loops will range from 1.0 (when
    # order=2**k-1) to 2.0 (when order=2**k+1).
    assert order > 1
    bits, bytes, extrabits = bits_and_bytes(order)
    generate = PRNG(seed)
    while True:
        extrabyte = b("")
        if extrabits:
            extrabyte = int2byte(ord(generate(1)) & lsb_of_ones(extrabits))
        guess = string_to_number(extrabyte + generate(bytes)) + 1
        if 1 <= guess < order:
            return guess


def number_to_string(num, order):
    l = orderlen(order)
    fmt_str = "%0" + str(2*l) + "x"
    string = binascii.unhexlify((fmt_str % num).encode())
    assert len(string) == l, (len(string), l)
    return string

def number_to_string_crop(num, order):
    l = orderlen(order)
    fmt_str = "%0" + str(2*l) + "x"
    string = binascii.unhexlify((fmt_str % num).encode())
    return string[:l]

def string_to_number(string):
    return int(binascii.hexlify(string), 16)

def string_to_number_fixedlen(string, order):
    l = orderlen(order)
    assert len(string) == l, (len(string), l)
    return int(binascii.hexlify(string), 16)

# these methods are useful for the sigencode= argument to SK.sign() and the
# sigdecode= argument to VK.verify(), and control how the signature is packed
# or unpacked.

def sigencode_strings(r, s, order):
    r_str = number_to_string(r, order)
    s_str = number_to_string(s, order)
    return (r_str, s_str)

def sigencode_string(r, s, order):
    # for any given curve, the size of the signature numbers is
    # fixed, so just use simple concatenation
    r_str, s_str = sigencode_strings(r, s, order)
    return r_str + s_str

def sigencode_der(r, s, order):
    return der.encode_sequence(der.encode_integer(r), der.encode_integer(s))

# canonical versions of sigencode methods
# these enforce low S values, by negating the value (modulo the order) if above order/2
# see CECKey::Sign() https://github.com/bitcoin/bitcoin/blob/master/src/key.cpp#L214
def sigencode_strings_canonize(r, s, order):
    if s > order / 2:
        s = order - s
    return sigencode_strings(r, s, order)

def sigencode_string_canonize(r, s, order):
    if s > order / 2:
        s = order - s
    return sigencode_string(r, s, order)

def sigencode_der_canonize(r, s, order):
    if s > order / 2:
        s = order - s
    return sigencode_der(r, s, order)


def sigdecode_string(signature, order):
    l = orderlen(order)
    assert len(signature) == 2*l, (len(signature), 2*l)
    r = string_to_number_fixedlen(signature[:l], order)
    s = string_to_number_fixedlen(signature[l:], order)
    return r, s

def sigdecode_strings(rs_strings, order):
    (r_str, s_str) = rs_strings
    l = orderlen(order)
    assert len(r_str) == l, (len(r_str), l)
    assert len(s_str) == l, (len(s_str), l)
    r = string_to_number_fixedlen(r_str, order)
    s = string_to_number_fixedlen(s_str, order)
    return r, s

def sigdecode_der(sig_der, order):
    #return der.encode_sequence(der.encode_integer(r), der.encode_integer(s))
    rs_strings, empty = der.remove_sequence(sig_der)
    if empty != b(""):
        raise der.UnexpectedDER("trailing junk after DER sig: %s" %
                                binascii.hexlify(empty))
    r, rest = der.remove_integer(rs_strings)
    s, empty = der.remove_integer(rest)
    if empty != b(""):
        raise der.UnexpectedDER("trailing junk after DER numbers: %s" %
                                binascii.hexlify(empty))
    return r, s


########NEW FILE########
__FILENAME__ = _version

# This file is originally generated from Git information by running 'setup.py
# version'. Distribution tarballs contain a pre-generated copy of this file.

__version__ = '0.11'

########NEW FILE########
__FILENAME__ = environment
from test_util import remove_settings

def before_all(context):
    # -- SET LOG LEVEL: behave --logging-level=ERROR ...
    # on behave command-line or in "behave.ini".
    context.config.setup_logging()

def after_scenario(context, scenario):
    if hasattr(context, 'proc'):
        for i, proc in enumerate(context.proc):
            proc.terminate()
            proc.join()
            remove_settings(i)

########NEW FILE########
__FILENAME__ = p2p
from behave import *
from threading import Thread
from test_util import *

@given('there is a node')
def step_impl(context):
    create_nodes(context, 1)


@when('we connect')
def step_impl(context):
    context.response = ws_connect(0)


@then('it will introduce itself')
def step_impl(context):
    assert context.response['result']['type'] == u'myself'


@given('there are {num_nodes} connected nodes')
def step_impl(context, num_nodes):
    create_connected_nodes(context, int(num_nodes))


@given('there are {num_nodes} nodes')
def step_impl(context, num_nodes):
    create_nodes(context, int(num_nodes))


@when('node {i} connects to node {j}')
def step_impl(context, i, j):
    ws_send(int(i), 'connect', {'uri': node_addr(int(j))})


@then('node {i} is connected to node {j}')
def step_impl(context, i, j):
    pubkey_j = ws_connect(int(j))[u'result'][u'pubkey']

    response = ws_send(int(i), 'peers')[u'result']
    assert response['type'] == 'peers'
    assert {'pubkey': pubkey_j, 'uri': node_addr(int(j))} in response['peers']


@then('node {i} can query page of node {j}')
def step_impl(context, i, j):
    pubkey_j = ws_connect(int(j))[u'result'][u'pubkey']

    response = ws_send(int(i), 'query_page', {'pubkey': pubkey_j})[u'result']
    data = settings(j)
    print pubkey_j
    print response['text']
    print data['storeDescription']

    assert response[u'type'] == u'page'
    assert response[u'text'] == data['storeDescription']

########NEW FILE########
__FILENAME__ = test_util
import json
import time
from multiprocessing import Process

from node.tornadoloop import start_node
from tornado.ioloop import IOLoop
from tornado import gen
from tornado.websocket import websocket_connect
from pymongo import MongoClient


def ws_connect(node_index):
    port = str(node_to_ws_port(node_index))

    @gen.coroutine
    def client():
        client = yield websocket_connect('ws://localhost:%s/ws' % port)
        message = yield client.read_message()
        raise gen.Return(json.loads(message))

    return IOLoop.current().run_sync(client)


def ws_send_raw(port, string):
    @gen.coroutine
    def client():
        client = yield websocket_connect('ws://localhost:%s/ws' % port)
        message = yield client.read_message()
        client.write_message(json.dumps(string))
        message = yield client.read_message()
        raise gen.Return(json.loads(message))

    return IOLoop.current().run_sync(client)


def ws_send(node_index, command, params={}):
    port = str(node_to_ws_port(node_index))
    cmd = {'command': command,
           'id': 1,
           'params': params}
    ret = ws_send_raw(port, cmd)
    time.sleep(0.1)
    return ret


def create_nodes(context, num_nodes):
    proc = []
    for i in range(num_nodes):
        proc.append(Process(target=start_node,
                            args=('127.0.0.%s' % str(i+1),
                                  12345,
                                  None,
                                  'test%s.log' % str(i),
                                  i)))
        proc[i].start()
        time.sleep(1)
        settings_set_page(i)
    context.proc = proc


def create_connected_nodes(context, num_nodes):
    create_nodes(context, num_nodes)
    for i in range(num_nodes-1):
        ws_send(i, 'connect', {'uri': node_addr(i+1)})


def node_addr(node_index):
    return 'tcp://127.0.0.%s:12345' % str(node_index+1)


def node_to_ws_port(node_index):
    return node_index + 8888

def settings(market_id):
        MONGODB_URI = 'mongodb://localhost:27017'
        _dbclient = MongoClient()
        _db = _dbclient.openbazaar

        settings = _db.settings.find_one({'id':str(market_id)})
        return settings

def settings_set_page(market_id):
        # Connect to database
        MONGODB_URI = 'mongodb://localhost:27017'
        _dbclient = MongoClient()
        _db = _dbclient.openbazaar

        _db.settings.update({'id' : str(market_id)}, 
                            # {'$set': setting} , True)
                            {'$set': {'storeDescription':'Market %s' % str(market_id)}} , True)

def remove_settings(market_id):
        MONGODB_URI = 'mongodb://localhost:27017'
        _dbclient = MongoClient()
        _db = _dbclient.openbazaar

        _db.settings.remove({'id': '%s'%market_id})

########NEW FILE########
__FILENAME__ = s3_cache
#!/usr/bin/env python2.7
from __future__ import absolute_import, unicode_literals, print_function, division

from sys import argv
from os import environ, stat, remove as _delete_file
from os.path import isfile, dirname, basename, abspath
from hashlib import sha256
from subprocess import check_call as run

from boto.s3.connection import S3Connection
from boto.s3.key import Key
from boto.exception import S3ResponseError


NEED_TO_UPLOAD_MARKER = '.need-to-upload'
BYTES_PER_MB = 1024 * 1024
try:
    BUCKET_NAME = environ['TWBS_S3_BUCKET']
except KeyError:
    raise SystemExit("TWBS_S3_BUCKET environment variable not set!")


def _sha256_of_file(filename):
    hasher = sha256()
    with open(filename, 'rb') as input_file:
        hasher.update(input_file.read())
    file_hash = hasher.hexdigest()
    print('sha256({}) = {}'.format(filename, file_hash))
    return file_hash


def _delete_file_quietly(filename):
    try:
        _delete_file(filename)
    except (OSError, IOError):
        pass


def _tarball_size(directory):
    kib = stat(_tarball_filename_for(directory)).st_size // BYTES_PER_MB
    return "{} MiB".format(kib)


def _tarball_filename_for(directory):
    return abspath('./{}.tar.gz'.format(basename(directory)))


def _create_tarball(directory):
    print("Creating tarball of {}...".format(directory))
    run(['tar', '-czf', _tarball_filename_for(directory), '-C', dirname(directory), basename(directory)])


def _extract_tarball(directory):
    print("Extracting tarball of {}...".format(directory))
    run(['tar', '-xzf', _tarball_filename_for(directory), '-C', dirname(directory)])


def download(directory):
    _delete_file_quietly(NEED_TO_UPLOAD_MARKER)
    try:
        print("Downloading {} tarball from S3...".format(friendly_name))
        key.get_contents_to_filename(_tarball_filename_for(directory))
    except S3ResponseError as err:
        open(NEED_TO_UPLOAD_MARKER, 'a').close()
        print(err)
        raise SystemExit("Cached {} download failed!".format(friendly_name))
    print("Downloaded {}.".format(_tarball_size(directory)))
    _extract_tarball(directory)
    print("{} successfully installed from cache.".format(friendly_name))


def upload(directory):
    _create_tarball(directory)
    print("Uploading {} tarball to S3... ({})".format(friendly_name, _tarball_size(directory)))
    key.set_contents_from_filename(_tarball_filename_for(directory))
    print("{} cache successfully updated.".format(friendly_name))
    _delete_file_quietly(NEED_TO_UPLOAD_MARKER)


if __name__ == '__main__':
    # Uses environment variables:
    #   AWS_ACCESS_KEY_ID -- AWS Access Key ID
    #   AWS_SECRET_ACCESS_KEY -- AWS Secret Access Key
    argv.pop(0)
    if len(argv) != 4:
        raise SystemExit("USAGE: s3_cache.py <download | upload> <friendly name> <dependencies file> <directory>")
    mode, friendly_name, dependencies_file, directory = argv

    conn = S3Connection()
    bucket = conn.lookup(BUCKET_NAME, validate=False)
    if bucket is None:
        raise SystemExit("Could not access bucket!")

    dependencies_file_hash = _sha256_of_file(dependencies_file)

    key = Key(bucket, dependencies_file_hash)
    key.storage_class = 'REDUCED_REDUNDANCY'

    if mode == 'download':
        download(directory)
    elif mode == 'upload':
        if isfile(NEED_TO_UPLOAD_MARKER):  # FIXME
            upload(directory)
        else:
            print("No need to upload anything.")
    else:
        raise SystemExit("Unrecognized mode {!r}".format(mode))

########NEW FILE########
__FILENAME__ = s3_cache
#!/usr/bin/env python2.7
from __future__ import absolute_import, unicode_literals, print_function, division

from sys import argv
from os import environ, stat, remove as _delete_file
from os.path import isfile, dirname, basename, abspath
from hashlib import sha256
from subprocess import check_call as run

from boto.s3.connection import S3Connection
from boto.s3.key import Key
from boto.exception import S3ResponseError


NEED_TO_UPLOAD_MARKER = '.need-to-upload'
BYTES_PER_MB = 1024 * 1024
try:
    BUCKET_NAME = environ['TWBS_S3_BUCKET']
except KeyError:
    raise SystemExit("TWBS_S3_BUCKET environment variable not set!")


def _sha256_of_file(filename):
    hasher = sha256()
    with open(filename, 'rb') as input_file:
        hasher.update(input_file.read())
    file_hash = hasher.hexdigest()
    print('sha256({}) = {}'.format(filename, file_hash))
    return file_hash


def _delete_file_quietly(filename):
    try:
        _delete_file(filename)
    except (OSError, IOError):
        pass


def _tarball_size(directory):
    kib = stat(_tarball_filename_for(directory)).st_size // BYTES_PER_MB
    return "{} MiB".format(kib)


def _tarball_filename_for(directory):
    return abspath('./{}.tar.gz'.format(basename(directory)))


def _create_tarball(directory):
    print("Creating tarball of {}...".format(directory))
    run(['tar', '-czf', _tarball_filename_for(directory), '-C', dirname(directory), basename(directory)])


def _extract_tarball(directory):
    print("Extracting tarball of {}...".format(directory))
    run(['tar', '-xzf', _tarball_filename_for(directory), '-C', dirname(directory)])


def download(directory):
    _delete_file_quietly(NEED_TO_UPLOAD_MARKER)
    try:
        print("Downloading {} tarball from S3...".format(friendly_name))
        key.get_contents_to_filename(_tarball_filename_for(directory))
    except S3ResponseError as err:
        open(NEED_TO_UPLOAD_MARKER, 'a').close()
        print(err)
        raise SystemExit("Cached {} download failed!".format(friendly_name))
    print("Downloaded {}.".format(_tarball_size(directory)))
    _extract_tarball(directory)
    print("{} successfully installed from cache.".format(friendly_name))


def upload(directory):
    _create_tarball(directory)
    print("Uploading {} tarball to S3... ({})".format(friendly_name, _tarball_size(directory)))
    key.set_contents_from_filename(_tarball_filename_for(directory))
    print("{} cache successfully updated.".format(friendly_name))
    _delete_file_quietly(NEED_TO_UPLOAD_MARKER)


if __name__ == '__main__':
    # Uses environment variables:
    #   AWS_ACCESS_KEY_ID -- AWS Access Key ID
    #   AWS_SECRET_ACCESS_KEY -- AWS Secret Access Key
    argv.pop(0)
    if len(argv) != 4:
        raise SystemExit("USAGE: s3_cache.py <download | upload> <friendly name> <dependencies file> <directory>")
    mode, friendly_name, dependencies_file, directory = argv

    conn = S3Connection()
    bucket = conn.lookup(BUCKET_NAME, validate=False)
    if bucket is None:
        raise SystemExit("Could not access bucket!")

    dependencies_file_hash = _sha256_of_file(dependencies_file)

    key = Key(bucket, dependencies_file_hash)
    key.storage_class = 'REDUCED_REDUNDANCY'

    if mode == 'download':
        download(directory)
    elif mode == 'upload':
        if isfile(NEED_TO_UPLOAD_MARKER):  # FIXME
            upload(directory)
        else:
            print("No need to upload anything.")
    else:
        raise SystemExit("Unrecognized mode {!r}".format(mode))

########NEW FILE########
__FILENAME__ = broadcast
import obelisk
import sys
import threading
import urllib2, re, random
import websocket
import json

"""Broadcast transactions to appropriate gateways

   Currently supported:
	- Blockchain.info
	- Eligius
	- Unsystem gateway
"""

# Makes a request to a given URL (first argument) and optional params (second argument)
def make_request(*args):
    opener = urllib2.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0'+str(random.randrange(1000000)))]
    try:
        return opener.open(*args).read().strip()
    except Exception,e:
        try: p = e.read().strip()
        except: p = e
        raise Exception(p)

def bci_pushtx(tx):
    return make_request('http://blockchain.info/pushtx','tx='+tx)

def eligius_pushtx(tx):
    s = make_request('http://eligius.st/~wizkid057/newstats/pushtxn.php','transaction='+tx+'&send=Push')
    strings = re.findall('string[^"]*"[^"]*"',s)
    for string in strings:
        quote = re.findall('"[^"]*"',string)[0]
        if len(quote) >= 5: return quote[1:-1]

def gateway_broadcast(tx):
	
    ws = websocket.create_connection("ws://gateway.unsystem.net:8888/")
    request = {"id": 110, "command": "broadcast_transaction", "params": [tx]}
    ws.send(json.dumps(request))
    result =  ws.recv()
    response = json.loads(result)
    if response["error"] is not None:
        print >> sys.stderr, "Error broadcasting to gateway:", response["error"]
        return
    print "Sent"
    ws.close()

def broadcast(tx):

    raw_tx = tx.serialize().encode("hex")
    print "Raw transaction data:", raw_tx

    #print "TEMP DISABLED BROADCAST"
    
    # Send tx to Eligius pool through web form
    eligius_pushtx(raw_tx)
    
    # Send through Unsystem gateway
    gateway_broadcast(raw_tx)
    
    # Send through Blockchain.info 
    #bci_pushtx(raw_tx)

if __name__ == "__main__":
    raw_tx = "0100000001a0e98dd6f648975e5dd7f5a2da3f349b452e70f22e31ecdfe8614c0147713d78010000006b483045022100f5c924a09ae4a4516b49d7aecfd73373e08f6e519bb7988bf01076b6f414b181022071023f837404ea1879e38a95340a458edf4afb521775d8dba1f4ccc842514a1d0121034bd380ea13b5871968696d73a56e707859240b098f65b144322beb0e24ff3d3fffffffff020000000000000000166a14910715286f7c16988a5d0ae5a56364d2a01bce2960ea0000000000001976a914f5e58287166b8655c769b6bb6f3e2480a2c8cd2688ac00000000"
    gateway_broadcast(raw_tx)


########NEW FILE########
__FILENAME__ = forge
import obelisk
import broadcast

# TODO: Change this over to development address if using TESTNET

# Private Key HEX
secret = "8cd252b8a48abb98aed387b204a417ae38e4a928b0e997654bdd742dd044659c".decode("hex")
address = "1PRBVdCHoPPD3bz8sCZRTm6iAtuoqFctvx"

# Set up your own Obelisk of Light client
client = None

def hash_transaction(tx):
    return obelisk.Hash(tx.serialize())[::-1]

class HistoryCallback:

    def __init__(self, root_hash, finished_cb):
        self.root_hash = root_hash
        self.finished_cb = finished_cb

    def fetched(self, ec, history):


        if ec is not None:
            print >> sys.stderr, "Error fetching history:", ec
            return

        unspent_rows = [row[:4] for row in history if row[4] is None]
        unspent = build_output_info_list(unspent_rows)
        tx_hash = build_actual_tx(unspent, self.root_hash)
        self.finished_cb(tx_hash)

def send_root_hash(root_hash, finished_cb):
    global client
    if client is None:
        client = obelisk.ObeliskOfLightClient("tcp://obelisk.unsystem.net:8081")

    print "Retrieving History", root_hash.encode("hex")
    cb = HistoryCallback(root_hash, finished_cb)
    client.fetch_history(address, cb.fetched)

def build_actual_tx(unspent, root_hash):
    print "Building...", root_hash.encode("hex")
    fee = 10000
    optimal_outputs = obelisk.select_outputs(unspent, fee)
    tx = obelisk.Transaction()
    for output in optimal_outputs.points:
        add_input(tx, output.point)
    add_return_output(tx, root_hash)
    change = optimal_outputs.change
    add_output(tx, address, change)
    key = obelisk.EllipticCurveKey()
    key.set_secret(secret)
    for i, output in enumerate(optimal_outputs.points):
        obelisk.sign_transaction_input(tx, i, key)
    broadcast.broadcast(tx)
    tx_hash = hash_transaction(tx)
    return tx_hash

def add_input(tx, prevout):
    input = obelisk.TxIn()
    input.previous_output.hash = prevout.hash
    input.previous_output.index = prevout.index
    tx.inputs.append(input)

def add_return_output(tx, data):
    output = obelisk.TxOut()
    output.value = 0
    output.script = "\x6a\x14" + data
    tx.outputs.append(output)

def add_output(tx, address, value):
    output = obelisk.TxOut()
    output.value = value
    output.script = obelisk.output_script(address)
    tx.outputs.append(output)

def build_output_info_list(unspent_rows):
    unspent_infos = []
    for row in unspent_rows:
        assert len(row) == 4
        outpoint = obelisk.OutPoint()
        outpoint.hash = row[0]
        outpoint.index = row[1]
        value = row[3]
        unspent_infos.append(
            obelisk.OutputInfo(outpoint, value))
    return unspent_infos

if __name__ == "__main__":
    from twisted.internet import reactor
    client = obelisk.ObeliskOfLightClient("tcp://obelisk.unsystem.net:8081")
    def history_fetched(self, ec):
        print ec
    client.fetch_history(address, history_fetched)
    reactor.run()

########NEW FILE########
__FILENAME__ = identity
import zmq
import sys
import hashlib
import obelisk
import broadcast
import forge
import shelve
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
import logging
from logging import FileHandler, StreamHandler

class Blockchain:

    def __init__(self):
        self.blocks = []
        self.processor = []
        self.registry = {}
        db = shelve.open("blockchain")
        try:
            for block in db["chain"]:
                self.accept(block)
        except KeyError:
            pass
        db.close()
        self._regenerate_lookup()
        logging.getLogger().info("[Blockchain] Starting identity blockchain %s:" % self.blocks)

	# Accept block(s) for processing
    def accept(self, block):
        self.processor.append(block)

	#
    def update(self):
        process = self.processor
        self.processor = []
        for block in process:
            self.process(block)

    def process(self, block):
        if not block.complete:
            self.postpone(block)
            return
        logging.getLogger().info("Processing block...", block)

        # Check hash of keys + values matches root hash
        if not block.verify():
            # Invalid block so reject it.
            print >> sys.stderr, "Rejecting invalid block."
            return

        # Fetch tx to check it's valid
        assert block.header.tx_hash

        # Forging callback
        def tx_fetched(ec, tx):
            print ec
            if ec is not None:
                print >> sys.stderr, "Block doesn't exist (yet)."
                self.postpone(block)
                return
            self._tx_fetched(block, tx, block.header.tx_hash)

        if forge.client is None:
            forge.client = obelisk.ObeliskOfLightClient("tcp://obelisk.unsystem.net:8081")
        forge.client.fetch_transaction(block.header.tx_hash, tx_fetched)

    def _tx_fetched(self, block, tx, tx_hash):

        # Continuing on with block validation...
        tx = obelisk.Transaction.deserialize(tx)
        if len(tx.outputs) != 2:
            print >> sys.stderr, "Tx outputs not 2, incorrect."
            return

        # Incorrect output size
        if len(tx.outputs[0].script) != 22:
            print >> sys.stderr, "Incorrect output script size."
            return

        # Transaction scriptPubKey doesn't start with OP_RETURN + push
        if tx.outputs[0].script[:2] != "\x6a\x14":
            print >> sys.stderr, "OP_RETURN + push"
            return

        root_hash = tx.outputs[0].script[2:]

        # Root hashes don't match
        if block.header.root_hash != root_hash:
            print >> sys.stderr, "Non matching root hash with tx."
            return

        # Fetch tx height/index associated with block

        # Fetch tx callback
        def txidx_fetched(ec, height, offset):
            if ec is not None:
                print >> sys.stderr, "Dodgy error, couldn't find tx off details."
                return
            self._txidx_fetched(block, height, offset)

        forge.client.fetch_transaction_index(tx_hash, txidx_fetched)

    def _txidx_fetched(self, block, height, offset):

        # Continue on... Block seems fine...
        # Check prev hash is in the list.
        if not self._block_hash_exists(block.prev_hash):
            print >> sys.stderr, "Previous block does not exist. Re-processing later."
            reactor.callLater(5, self.accept, block)
            return

        # Check for duplicate priority
        block.priority = height * 10**8 + offset
        if self._priority_exists(block.priority):
            print >> sys.stderr, "Blocks cannot have matching priorities."
            return

        # Add new block and sort on priority
        self.blocks.append(block)
        self.blocks.sort(key=lambda b: b.priority)
        self._regenerate_lookup()

        # add to blockchain
        logging.getLogger().info("Done!")
        db = shelve.open("blockchain")
        db["chain"] = self.blocks
        db.close()

    def _regenerate_lookup(self):
        for block in self.blocks:
            for name, key in block.txs:
                if name not in self.registry:
                    logging.getLogger().info("Adding:", name)
                    self.registry[name] = key
                else:
                    logging.getLogger().info("Name already in registry")

    def postpone(self, block):
        # read for later processing
        self.accept(block)

    def _priority_exists(self, priority):
        for block in self.blocks:
            if block.priority == priority:
                return True
        return False

    @property
    def genesis_hash(self):
        return "*We are butterflies*"

    @property
    def last_hash(self):
        if not self.blocks:
            return self.genesis_hash
        return self.blocks[-1].header.tx_hash

    def _block_hash_exists(self, block_hash):
        if block_hash == self.genesis_hash:
            return True
        for block in self.blocks:
            if block.header.tx_hash == block_hash:
                return True
        return False

    def lookup(self, name):
        print self.registry
        return self.registry.get(name)

class Pool:

    def __init__(self, chain):
        self.txs = []
        self.chain = chain

    def add(self, tx):

        self.txs.append(tx)

        # TODO: Wait for more registrations and then forge block
        # add timeout/limit logic here.
        # for now create new block for every new registration.

        self.fabricate_block()

    def fabricate_block(self):
        logging.getLogger().info("[Pool] Fabricating new block!")
        txs = self.txs
        self.txs = []
        block = Block(txs, self.chain.last_hash)
        block.register()
        self.chain.accept(block)

class BlockHeader:

    def __init__(self, tx_hash, root_hash):
        self.tx_hash = tx_hash
        self.root_hash = root_hash

class Block:

    def __init__(self, txs, prev_hash, header=None):
        self.txs = txs
        self.prev_hash = prev_hash
        self.header = header
        self.complete = False

    def register(self):

        """Register block in the bitcoin blockchain
        """

        # Calculate Merkle root
        root_hash = self.calculate_root_hash()

        # Create tx with root_hash as output
        self.header = BlockHeader("", root_hash)
        forge.send_root_hash(root_hash, self._registered)

    def _registered(self, tx_hash):
        self.header.tx_hash = tx_hash
        self.complete = True
        logging.getLogger().info("Registered block, awaiting confirmation:", tx_hash.encode("hex"))

    def calculate_root_hash(self):
        h = hashlib.new("ripemd160")
        h.update(self.prev_hash)
        for key, value in self.txs:
            h.update(key)
            h.update(value)
        return h.digest()

    def verify(self):
        if self.header is None:
            return False
        root_hash = self.calculate_root_hash()
        return self.header.root_hash == root_hash

    def is_next(self, block):
        return block.header.tx_hash == self.prev_hash

    def __repr__(self):
        return "<Block tx_hash=%s root_hash=%s prev=%s txs=%s>" % (
            self.header.tx_hash.encode("hex") if self.header else None,
            self.header.root_hash.encode("hex") if self.header else None,
            self.prev_hash.encode("hex"),
            [(k, v.encode("hex")) for k, v in self.txs])

class ZmqPoller:

    def __init__(self, pool, chain):
        self.pool = pool
        self.chain = chain
        self.context = zmq.Context()
        self.recvr = self.context.socket(zmq.PULL)
        self.recvr.bind("tcp://*:5557")
        logging.getLogger().info("Started on port 5557")
        self.query = self.context.socket(zmq.REP)
        self.query.bind("tcp://*:5558")

    def update(self):
        self._recv_tx()
        self._recv_query()

    def _recv_tx(self):
        try:
            name_reg = self.recvr.recv(flags=zmq.NOBLOCK)
        except zmq.ZMQError:
            return
        value = self.recvr.recv()
        self.pool.add((name_reg, value))


    def _recv_query(self):

        """ Receive query for identity
	    """

        try:
            name = self.query.recv(flags=zmq.NOBLOCK)
        except zmq.ZMQError:
            return
        logging.getLogger().info("[ZMQ] Lookup:  %s" % name)
        value = self.chain.lookup(name)
        if value is None:
            self.query.send("__NONE__")
            return
        self.query.send(value)


def main(argv):

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='logs/identity.log')

    chain = Blockchain()
    pool = Pool(chain)
    zmq_poller = ZmqPoller(pool, chain)
    lc_zmq = LoopingCall(zmq_poller.update)
    lc_zmq.start(0.1)
    lc_chain = LoopingCall(chain.update)
    lc_chain.start(6)
    reactor.run()
    logging.getLogger().info("Identity server stopped")

if __name__ == "__main__":
    main(sys.argv)

########NEW FILE########
__FILENAME__ = query_ident
import zmq
c = zmq.Context()
s = c.socket(zmq.REQ)
s.connect("tcp://seed.openbazaar.org:5558")
s.send("default")
key = s.recv()

if key == "__NONE__":
    print "Invalid nick"
else:
    print key.encode("hex")

########NEW FILE########
__FILENAME__ = send_ident
import zmq
c = zmq.Context()
s = c.socket(zmq.PUSH)
s.connect("tcp://localhost:5557")

s.send("default", flags=zmq.SNDMORE)
s.send("03960478444a2c18b0cd82b461c2654fc3b96dd117ddd524558268be3044192b97".decode("hex"))

########NEW FILE########
__FILENAME__ = crypto2crypto
import json
import pyelliptic as ec

from p2p import PeerConnection, TransportLayer
import traceback
from pymongo import MongoClient
from protocol import hello_request, hello_response, proto_response_pubkey
import obelisk
import logging
from market import Market
#from ecdsa import SigningKey,SECP256k1
#import random
from obelisk import bitcoin

class CryptoPeerConnection(PeerConnection):

    def __init__(self, transport, address, pub):
        self._priv = transport._myself
        self._pub = pub
        PeerConnection.__init__(self, transport, address)

    def encrypt(self, data):
        return self._priv.encrypt(data, self._pub)

    def send(self, data):
        self.send_raw(self.encrypt(json.dumps(data)))

    def on_message(self, msg):
        # this are just acks
        pass


class CryptoTransportLayer(TransportLayer):

    def __init__(self, my_ip, my_port, market_id):

        TransportLayer.__init__(self, my_ip, my_port)

        self._myself = ec.ECC(curve='secp256k1')

        self.nick_mapping = {}

        # Connect to database
        MONGODB_URI = 'mongodb://localhost:27017'
        _dbclient = MongoClient()
        self._db = _dbclient.openbazaar

        self.settings = self._db.settings.find_one({'id':"%s"%market_id})
        self.market_id = market_id

        if self.settings:
            self.nickname = self.settings['nickname'] if self.settings.has_key("nickname") else ""
            self.secret = self.settings['secret']
            self.pubkey = self.settings['pubkey']
        else:
            self.nickname = 'Default'
            key = bitcoin.EllipticCurveKey()
            key.new_key_pair()
            hexkey = key.secret.encode('hex')
            self._db.settings.insert({"id":'%s'%market_id, "secret":hexkey, "pubkey":bitcoin.GetPubKey(key._public_key.pubkey, False).encode('hex')})
            self.settings = self._db.settings.find_one({'id':"%s"%market_id})



#        self.nickname, self.secret, self.pubkey = \
#            self.load_crypto_details(store_file)

        self._log = logging.getLogger(self.__class__.__name__)

    # Return data array with details from the crypto file
    # TODO: This needs to be protected better; potentially encrypted file or DB
    def load_crypto_details(self, store_file):
        with open(store_file) as f:
            data = json.loads(f.read())
        assert "nickname" in data
        assert "secret" in data
        assert "pubkey" in data
        assert len(data["secret"]) == 2 * 32
        assert len(data["pubkey"]) == 2 * 33

        return data["nickname"], data["secret"].decode("hex"), \
            data["pubkey"].decode("hex")

    def get_profile(self):
        peers = {}

        self.settings = self._db.settings.find_one({'id':"%s"%self.market_id})
        self._log.info('SETTINGS %s' % self.settings)
        for uri, peer in self._peers.iteritems():
            if peer._pub:
                peers[uri] = peer._pub.encode('hex')
        return {'uri': self._uri, 'pub': self._myself.get_pubkey().encode('hex'),'nickname': self.nickname,
                'peers': peers}

    def respond_pubkey_if_mine(self, nickname, ident_pubkey):

        if ident_pubkey != self.pubkey:
            self._log.info("Public key does not match your identity")
            return

        # Return signed pubkey
        pubkey = self._myself.pubkey
        ec_key = obelisk.EllipticCurveKey()
        ec_key.set_secret(self.secret)
        digest = obelisk.Hash(pubkey)
        signature = ec_key.sign(digest)

        # Send array of nickname, pubkey, signature to transport layer
        self.send(proto_response_pubkey(nickname, pubkey, signature))

    def pubkey_exists(self, pub):

        for uri, peer in self._peers.iteritems():
            self._log.info('PEER: %s Pub: %s' %
                           (peer._pub.encode('hex'), pub.encode('hex')))
            if peer._pub.encode('hex') == pub.encode('hex'):
                return True

        return False

    def create_peer(self, uri, pub):

        if pub:
            pub = pub.decode('hex')

        # Create the peer if public key is not already in the peer list
        # if not self.pubkey_exists(pub):
        self._peers[uri] = CryptoPeerConnection(self, uri, pub)

        # Call 'peer' callbacks on listeners
        self.trigger_callbacks('peer', self._peers[uri])

        # else:
        #    print 'Pub Key is already in peer list'

    def send_enc(self, uri, msg):
        peer = self._peers[uri]
        pub = peer._pub


        # Now send a hello message to the peer
        if pub:
            self._log.info("Sending encrypted [%s] message to %s"
                           % (msg['type'], uri))
            peer.send(msg)
        else:
            # Will send clear profile on initial if no pub
            self._log.info("Sending unencrypted [%s] message to %s"
                           % (msg['type'], uri))
            self._peers[uri].send_raw(json.dumps(msg))

    def init_peer(self, msg):
        self._log.info('Initialize Peer: %s' % msg)

        uri = msg['uri']
        pub = msg.get('pub')
        nickname = msg.get('nickname')
        msg_type = msg.get('type')

        if not self.valid_peer_uri(uri):
            self._log.info("Peer " + uri + " is not valid.")
            return

        if uri not in self._peers:
            # unknown peer
            self._log.info('Create New Peer: %s' % uri)
            self.create_peer(uri, pub)

            if not msg_type:
                self.send_enc(uri, hello_request(self.get_profile()))
            elif msg_type == 'hello_request':
                self.send_enc(uri, hello_response(self.get_profile()))

        else:
            # known peer
            if pub:
                # test if we have to update the pubkey
                if not self._peers[uri]._pub:
                    self._log.info("Setting public key for seed node")
                    self._peers[uri]._pub = pub.decode('hex')
                    self.trigger_callbacks('peer', self._peers[uri])

                if (self._peers[uri]._pub != pub.decode('hex')):
                    self._log.info("Updating public key for node")
                    self._peers[uri]._nickname = nickname
                    self._peers[uri]._pub = pub.decode('hex')

                    self.trigger_callbacks('peer', self._peers[uri])

            if msg_type == 'hello_request':
                # reply only if necessary
                self.send_enc(uri, hello_response(self.get_profile()))

    def on_raw_message(self, serialized):

        try:
            msg = json.loads(serialized)
            self._log.info("receive [%s]" % msg.get('type', 'unknown'))
        except ValueError:
            try:
                msg = json.loads(self._myself.decrypt(serialized))
                self._log.info("Decrypted raw message [%s]"
                               % msg.get('type', 'unknown'))
            except:
                self._log.info("incorrect msg ! %s..."
                               % self._myself.decrypt(serialized))
                traceback.print_exc()
                return

        msg_type = msg.get('type')
        msg_uri = msg.get('uri')

        if msg_type != '':

            if msg_type.startswith('hello') and msg_uri:
                self.init_peer(msg)
                for uri, pub in msg.get('peers', {}).iteritems():
                    # Do not add yourself as a peer
                    if uri != self._uri:
                        self.init_peer({'uri': uri, 'pub': pub})
                self._log.info("Update peer table [%s peers]" % len(self._peers))

            elif msg_type == 'goodbye' and msg_uri:
                self._log.info("Received goodbye from %s" % msg_uri)
                self.remove_peer(msg_uri)

            else:
                self.on_message(msg)

########NEW FILE########
__FILENAME__ = lookup
import zmq
import logging

class QueryIdent:

    def __init__(self):
        self._ctx = zmq.Context()
        self._socket = self._ctx.socket(zmq.REQ)

        # Point to OpenBazaar Identity server for now
        self._socket.connect("tcp://seed.openbazaar.org:5558")

        self._log = logging.getLogger(self.__class__.__name__)

    def lookup(self, user):
        self._socket.send(user)
        key = self._socket.recv()
        self._log.info("Lookup %s" % user)
        if key == "__NONE__":
            return None
        return key

if __name__ == "__main__":
    query = QueryIdent()

########NEW FILE########
__FILENAME__ = market
from protocol import shout, proto_page, query_page
from reputation import Reputation
from orders import Orders
import protocol
import sys
import json
import lookup
from pymongo import MongoClient
import logging
import pyelliptic
import pycountry
from ecdsa import SigningKey,SECP256k1
import random
from obelisk import bitcoin
import base64


class Market(object):

    def __init__(self, transport):

        self._log = logging.getLogger(self.__class__.__name__)
        self._log.info("Initializing")

        # for now we have the id in the transport
        self._myself = transport._myself
        self._peers = transport._peers
        self._transport = transport
        self.query_ident = None

        self.reputation = Reputation(self._transport)
        self.orders = Orders(self._transport)
        self.order_entries = self.orders._orders

        # TODO: Persistent storage of nicknames and pages
        self.nicks = {}
        self.pages = {}

        # Connect to database
        MONGODB_URI = 'mongodb://localhost:27017'
        _dbclient = MongoClient()
        self._db = _dbclient.openbazaar

        self.settings = self._db.settings.find_one()



        welcome = True

        if self.settings:
            if  'welcome' in self.settings.keys() and self.settings['welcome']:
                welcome = False

        # Register callbacks for incoming events
        transport.add_callback('query_myorders', self.on_query_myorders)
        transport.add_callback('peer', self.on_peer)
        transport.add_callback('query_page', self.on_query_page)
        transport.add_callback('page', self.on_page)
        transport.add_callback('negotiate_pubkey', self.on_negotiate_pubkey)
        transport.add_callback('proto_response_pubkey', self.on_response_pubkey)

        self.load_page(welcome)

    def generate_new_secret(self):

        key = bitcoin.EllipticCurveKey()
        key.new_key_pair()
        hexkey = key.secret.encode('hex')

        self._log.info('Pubkey generate: %s' % key._public_key.pubkey)

        self._db.settings.update({}, {"$set": {"secret":hexkey, "pubkey":bitcoin.GetPubKey(key._public_key.pubkey, False).encode('hex')}})


    def lookup(self, msg):

        if self.query_ident is None:
            self._log.info("Initializing identity query")
            self.query_ident = lookup.QueryIdent()

        nickname = str(msg["text"])
        key = self.query_ident.lookup(nickname)
        if key is None:
            self._log.info("Key not found for this nickname")
            return ("Key not found for this nickname", None)

        self._log.info("Found key: %s " % key.encode("hex"))
        if nickname in self._transport.nick_mapping:
            self._log.info("Already have a cached mapping, just adding key there.")
            response = {'nickname': nickname,
                        'pubkey': self._transport.nick_mapping[nickname][1].encode('hex'),
                        'signature': self._transport.nick_mapping[nickname][0].encode('hex'),
                        'type': 'response_pubkey',
                        'signature': 'unknown'}
            self._transport.nick_mapping[nickname][0] = key
            return (None, response)

        self._transport.nick_mapping[nickname] = [key, None]

        self._transport.send(protocol.negotiate_pubkey(nickname, key))

	# Load default information for your market from your file
    def load_page(self, welcome):

        #self._log.info("Loading market config from %s." % self.store_file)

        #with open(self.store_file) as f:
        #    data = json.loads(f.read())

        #self._log.info("Configuration data: " + json.dumps(data))

        #assert "desc" in data
        #nickname = data["nickname"]
        #desc = data["desc"]

        nickname = self.settings['nickname'] if self.settings.has_key("nickname") else ""
        storeDescription = self.settings['storeDescription'] if self.settings.has_key("storeDescription") else ""

        tagline = "%s: %s" % (nickname, storeDescription)
        self.mypage = tagline
        self.nickname = nickname
        self.signature = self._transport._myself.sign(tagline)


        if welcome:
            self._db.settings.update({}, {"$set":{"welcome":"noshow"}})
        else:
            self.welcome = False


        #self._log.info("Tagline signature: " + self.signature.encode("hex"))


    # Products
    def save_product(self, msg):
        self._log.info("Product to save %s" % msg)
        self._log.info(self._transport)

        product_id = msg['id'] if msg.has_key("id") else ""

        if product_id == "":
          product_id = random.randint(0,1000000)

        if not msg.has_key("productPrice") or not msg['productPrice'] > 0:
          msg['productPrice'] = 0

        if not msg.has_key("productQuantity") or not msg['productQuantity'] > 0:
          msg['productQuantity'] = 1

        self._db.products.update({'id':product_id}, {'$set':msg}, True)
        

    def remove_product(self, msg):
        self._log.info("Product to remove %s" % msg)
        self._db.products.remove({'id':msg['productID']})


    def get_products(self):
        self._log.info(self._transport.market_id)
        products = self._db.products.find()
        my_products = []

        for product in products:
          my_products.append({ "productTitle":product['productTitle'] if product.has_key("productTitle") else "",
                        "id":product['id'] if product.has_key("id") else "",
                        "productDescription":product['productDescription'] if product.has_key("productDescription") else "",
                        "productPrice":product['productPrice'] if product.has_key("productPrice") else "",
                        "productShippingPrice":product['productShippingPrice'] if product.has_key("productShippingPrice") else "",
                        "productTags":product['productTags'] if product.has_key("productTags") else "",
                        "productImageData":product['productImageData'] if product.has_key("productImageData") else "",
                        "productQuantity":product['productQuantity'] if product.has_key("productQuantity") else "",
                         })

        return { "products": my_products }


    # SETTINGS

    def save_settings(self, msg):
        self._log.info("Settings to save %s" % msg)
        self._log.info(self._transport)
        self._db.settings.update({'id':'%s'%self._transport.market_id}, {'$set':msg}, True)

    def get_settings(self):
        self._log.info(self._transport.market_id)
        settings = self._db.settings.find_one({'id':'%s'%self._transport.market_id})
        print settings
        if settings:
            return { "bitmessage": settings['bitmessage'] if settings.has_key("bitmessage") else "",
                "email": settings['email'] if settings.has_key("email") else "",
                "PGPPubKey": settings['PGPPubKey'] if settings.has_key("PGPPubKey") else "",
                "pubkey": settings['pubkey'] if settings.has_key("pubkey") else "",
                "nickname": settings['nickname'] if settings.has_key("nickname") else "",
                "secret": settings['secret'] if settings.has_key("secret") else "",
                "welcome": settings['welcome'] if settings.has_key("welcome") else "",
                "escrowAddresses": settings['escrowAddresses'] if settings.has_key("escrowAddresses") else "",
                "storeDescription": settings['storeDescription'] if settings.has_key("storeDescription") else "",
                "city": settings['city'] if settings.has_key("city") else "",
                "stateRegion": settings['stateRegion'] if settings.has_key("stateRegion") else "",
                "street1": settings['street1'] if settings.has_key("street1") else "",
                "street2": settings['street2'] if settings.has_key("street2") else "",
                "countryCode": settings['countryCode'] if settings.has_key("countryCode") else "",
                "zip": settings['zip'] if settings.has_key("zip") else "",
                "arbiterDescription": settings['arbiterDescription'] if settings.has_key("arbiterDescription") else "",
                "arbiter": settings['arbiter'] if settings.has_key("arbiter") else "",
                }




    # PAGE QUERYING

    def query_page(self, pubkey):
        self._transport.send(query_page(pubkey))

    def on_page(self, page):

        self._log.info("Page returned: " + str(page))

        pubkey = page.get('pubkey')
        page = page.get('text')

        if pubkey and page:
            self._log.info(page)
            self.pages[pubkey] = page

    # Return your page info if someone requests it on the network
    def on_query_page(self, peer):
        self._log.info("Someone is querying for your page")
        self.settings = self.get_settings()
        self._log.info(base64.b64encode(self.settings['storeDescription'].encode('ascii')))
        self._transport.send(proto_page(self._transport._myself.get_pubkey().encode('hex'),
                                        self.settings['storeDescription'], self.signature,
                                        self.settings['nickname']))

    def on_query_myorders(self, peer):
        self._log.info("Someone is querying for your page")
        self._transport.send(proto_page(self._transport._myself.get_pubkey(),
                                        self.mypage, self.signature,
                                        self.nickname))

    def on_peer(self, peer):
        pass

    def on_negotiate_pubkey(self, ident_pubkey):
        self._log.info("Someone is asking for your real pubKey")
        assert "nickname" in ident_pubkey
        assert "ident_pubkey" in ident_pubkey
        nickname = ident_pubkey['nickname']
        ident_pubkey = ident_pubkey['ident_pubkey'].decode("hex")
        self._transport.respond_pubkey_if_mine(nickname, ident_pubkey)

    def on_response_pubkey(self, response):
        self._log.info("got a pubkey!")
        assert "pubkey" in response
        assert "nickname" in response
        assert "signature" in response
        pubkey = response["pubkey"].decode("hex")
        signature = response["signature"].decode("hex")
        nickname = response["nickname"]
        # Cache mapping for later.
        if nickname not in self._transport.nick_mapping:
            self._transport.nick_mapping[nickname] = [None, pubkey]
        # Verify signature here...
        # Add to our dict.
        self._transport.nick_mapping[nickname][1] = pubkey
        self._log.info("[market] mappings: ###############")
        for k, v in self._transport.nick_mapping.iteritems():
            self._log.info("'%s' -> '%s' (%s)" % (
                k, v[1].encode("hex") if v[1] is not None else v[1],
                v[0].encode("hex") if v[0] is not None else v[0]))
        self._log.info("##################################")

########NEW FILE########
__FILENAME__ = multisig
import obelisk
from twisted.internet import reactor
import logging

# Create new private key:
#
#   $ sx newkey > key1
#
# Show private secret:
#
#   $ cat key1 | sx wif-to-secret
#
# Show compressed public key:
#
#   $ cat key1 | sx pubkey
#
# You will need 3 keys for buyer, seller and arbitrer

def build_output_info_list(unspent_rows):
    unspent_infos = []
    for row in unspent_rows:
        assert len(row) == 4
        outpoint = obelisk.OutPoint()
        outpoint.hash = row[0]
        outpoint.index = row[1]
        value = row[3]
        unspent_infos.append(
            obelisk.OutputInfo(outpoint, value))
    return unspent_infos

class Multisig:

    def __init__(self, client, number_required, pubkeys):
        if number_required > len(pubkeys):
            raise Exception("number_required > len(pubkeys)")
        self.client = client
        self.number_required = number_required
        self.pubkeys = pubkeys
        self._log = logging.getLogger(self.__class__.__name__)

    @property
    def script(self):
        result = chr(80 + self.number_required)
        for pubkey in self.pubkeys:
            result += chr(33) + pubkey
        result += chr(80 + len(self.pubkeys))
        # checkmultisig
        result += "\xae"
        return result

    @property
    def address(self):
        raw_addr = obelisk.hash_160(self.script)
        return obelisk.hash_160_to_bc_address(raw_addr, addrtype=0x05)

    # 
    def create_unsigned_transaction(self, destination, finished_cb):
        def fetched(ec, history):
            self._log.info(history)
            if ec is not None:
                self._log.error("Error fetching history: %s" % ec)
                return    
            self._fetched(history, destination, finished_cb)
        self.client.fetch_history(self.address, fetched)

    #
    def _fetched(self, history, destination, finished_cb):
        unspent = [row[:4] for row in history if row[4] is None]
        tx = self._build_actual_tx(unspent, destination)
        finished_cb(tx)

    # 
    def _build_actual_tx(self, unspent, destination):
        
        # Send all unspent outputs (everything in the address) minus the fee
        tx = obelisk.Transaction()
        total_amount = 0
        for row in unspent:
            assert len(row) == 4
            outpoint = obelisk.OutPoint()
            outpoint.hash = row[0]
            outpoint.index = row[1]
            value = row[3]
            total_amount += value
            add_input(tx, outpoint)
        
        # Constrain fee so we don't get negative amount to send
        fee = min(total_amount, 10000)
        send_amount = total_amount - fee
        add_output(tx, destination, send_amount)
        return tx

    def sign_all_inputs(self, tx, secret):
        signatures = []
        key = obelisk.EllipticCurveKey()
        key.set_secret(secret)
        for i, input in enumerate(tx.inputs):
            sighash = generate_signature_hash(tx, i, self.script)
            # Add sighash::all to end of signature.
            signature = key.sign(sighash) + "\x01"
            signatures.append(signature)
        return signatures

def add_input(tx, prevout):
    input = obelisk.TxIn()
    input.previous_output.hash = prevout.hash
    input.previous_output.index = prevout.index
    tx.inputs.append(input)

def add_output(tx, address, value):
    output = obelisk.TxOut()
    output.value = value
    output.script = obelisk.output_script(address)
    tx.outputs.append(output)

def generate_signature_hash(parent_tx, input_index, script_code):
    tx = obelisk.copy_tx(parent_tx)
    if input_index >= len(tx.inputs):
        return None
    for input in tx.inputs:
        input.script = ""
    tx.inputs[input_index].script = script_code
    raw_tx = tx.serialize() + "\x01\x00\x00\x00"
    return obelisk.Hash(raw_tx)

class Escrow:

    def __init__(self, client, buyer_pubkey, seller_pubkey, arbit_pubkey):
        pubkeys = (buyer_pubkey, seller_pubkey, arbit_pubkey)
        self.multisig = Multisig(client, 2, pubkeys)

    # 1. BUYER: Deposit funds for seller
    @property
    def deposit_address(self):
        return self.multisig.address

    # 2. BUYER: Send unsigned tx to seller
    def initiate(self, destination_address, finished_cb):
        self.multisig.create_unsigned_transaction(
            destination_address, finished_cb)

    # ...
    # 3. BUYER: Release funds by sending signature to seller
    def release_funds(self, tx, secret):
        return self.multisig.sign_all_inputs(tx, secret)

    # 4. SELLER: Claim your funds by generating a signature.
    def claim_funds(self, tx, secret, buyer_sigs):
        seller_sigs = self.multisig.sign_all_inputs(tx, secret)
        return Escrow.complete(tx, buyer_sigs, seller_sigs,
                               self.multisig.script)

    @staticmethod
    def complete(tx, buyer_sigs, seller_sigs, script_code):
        for i, input in enumerate(tx.inputs):
            sigs = (buyer_sigs[i], seller_sigs[i])
            script = "\x00"
            for sig in sigs:
                script += chr(len(sig)) + sig
            script += "\x4c"
            assert len(script_code) < 255
            script += chr(len(script_code)) + script_code
            tx.inputs[i].script = script
        return tx

def main():

    ##########################################################
    # ESCROW TEST
    ##########################################################
    pubkeys = [
        "035b175132eeb8aa6e8455b6f1c1e4b2784bea1add47a6ded7fc9fc6b7aff16700".decode("hex"),
        "0351e400c871e08f96246458dae79a55a59730535b13d6e1d4858035dcfc5f16e2".decode("hex"),
        "02d53a92e3d43db101db55e351e9b42b4f711d11f6a31efbd4597695330d75d250".decode("hex")
    ]
    client = obelisk.ObeliskOfLightClient("tcp://85.25.198.97:8081")
    escrow = Escrow(client, pubkeys[0], pubkeys[1], pubkeys[2])
    def finished(tx):

        buyer_sigs = escrow.release_funds(tx,
            "b28c7003a7b6541cd1cd881928863abac0eff85f5afb40ff5561989c9fb95fb2".decode("hex"))
        completed_tx = escrow.claim_funds(tx,
            "5b05667dac199c48051932f14736e6f770e7a5917d2994a15a1508daa43bc9b0".decode("hex"),
            buyer_sigs)
        print 'COMPLETED TX: ', completed_tx.serialize().encode("hex")
		
		# TODO: Send to the bitcoin network
		
    escrow.initiate("1Fufjpf9RM2aQsGedhSpbSCGRHrmLMJ7yY", finished)

    ##########################################################
    # MULTISIGNATURE TEST
    ##########################################################
    msig = Multisig(client, 2, pubkeys)
    print "Multisig address: ", msig.address
    def finished(tx):
        print tx
        print ''
        print tx.serialize().encode("hex")
        print ''
        sigs1 = msig.sign_all_inputs(tx, "b28c7003a7b6541cd1cd881928863abac0eff85f5afb40ff5561989c9fb95fb2".decode("hex"))
        sigs3 = msig.sign_all_inputs(tx, "b74dbef0909c96d5c2d6971b37c8c71d300e41cad60aeddd6b900bba61c49e70".decode("hex"))
        for i, input in enumerate(tx.inputs):
            sigs = (sigs1[i], sigs3[i])
            script = "\x00"
            for sig in sigs:
                script += chr(len(sig)) + sig
            script += "\x4c"
            assert len(msig.script) < 255
            script += chr(len(msig.script)) + msig.script
            print "Script:", script.encode("hex")
            tx.inputs[i].script = script
        print tx
        print tx.serialize().encode("hex")
    msig.create_unsigned_transaction("1Fufjpf9RM2aQsGedhSpbSCGRHrmLMJ7yY", finished)
    reactor.run()

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = network_util
import socket
from struct import unpack
import re

def is_loopback_addr(addr):
    return addr.startswith("127.0.0.") or addr == 'localhost'

def is_valid_port(port):
    return int(port) > 0 and int(port) <= 65535

def is_valid_protocol(protocol):
    return protocol == 'tcp'

def is_valid_ip_address(addr):
    try:
        socket.inet_aton(addr)
        return True
    except socket.error:
        return False

def is_private_ip_address(addr):
    if is_loopback_addr(addr):
        return True
    if not is_valid_ip_address(addr):
        return False
    # http://stackoverflow.com/questions/691045/how-do-you-determine-if-an-ip-address-is-private-in-python
    f = unpack('!I',socket.inet_pton(socket.AF_INET,addr))[0]
    private = (
        [ 2130706432, 4278190080 ], # 127.0.0.0,   255.0.0.0   http://tools.ietf.org/html/rfc3330
        [ 3232235520, 4294901760 ], # 192.168.0.0, 255.255.0.0 http://tools.ietf.org/html/rfc1918
        [ 2886729728, 4293918720 ], # 172.16.0.0,  255.240.0.0 http://tools.ietf.org/html/rfc1918
        [ 167772160,  4278190080 ], # 10.0.0.0,    255.0.0.0   http://tools.ietf.org/html/rfc1918
    ) 
    for net in private:
        if (f & net[1] == net[0]):
            return True
    return False

def uri_parts(uri):
    m = re.match(r"(\w+)://([\w\.]+):(\d+)", uri)
    if m is not None:
        return (m.group(1), m.group(2), m.group(3))
    else:
        raise RuntimeError('URI is not valid')

########NEW FILE########
__FILENAME__ = orders
import json
from protocol import proto_reputation, proto_query_reputation, order
from collections import defaultdict
from pyelliptic import ECC
import random
from pymongo import MongoClient
from multisig import Multisig
import logging
import time


class Orders(object):
    def __init__(self, transport):
        self._transport = transport
        self._priv = transport._myself

        # TODO: Make user configurable escrow addresses
        self._escrows = ["02ca0020a9de236b47ca19e147cf2cd5b98b6600f168481da8ec0ca9ec92b59b76db1c3d0020f9038a585b93160632f1edec8278ddaeacc38a381c105860d702d7e81ffaa14d",
                         "02ca0020c0d9cd9bdd70c8565374ed8986ac58d24f076e9bcc401fc836352da4fc21f8490020b59dec0aff5e93184d022423893568df13ec1b8352e5f1141dbc669456af510c"]

        MONGODB_URI = 'mongodb://localhost:27017'
        _dbclient = MongoClient()
        self._db = _dbclient.openbazaar
        self._orders = self.get_orders()
        self.orders = self._db.orders

        transport.add_callback('order', self.on_order)
        self._log = logging.getLogger(self.__class__.__name__)

    def get_order(self, orderId):

        _order = self._db.orders.find_one({"id":orderId})

        # Get order prototype object before storing
        order = {"id":_order['id'],
                                    "state": _order['state'],
                                    "address": _order['address'] if _order.has_key("address") else "",
                                    "buyer": _order['buyer'] if _order.has_key("buyer") else "",
                                    "seller": _order['seller'] if _order.has_key("seller") else "",
                                    "escrows": _order['escrows'] if _order.has_key("escrows") else "",
                                    "text": _order['text'] if _order.has_key("text") else "",
                                    "created": _order['created'] if _order.has_key("created") else ""}
            #orders.append(_order)


        return order

    def get_orders(self):
        orders = []
        for _order in self._db.orders.find().sort([("created",-1)]):

            # Get order prototype object before storing
            orders.append({"id":_order['id'],
                                    "state": _order['state'],
                                    "address": _order['address'] if _order.has_key("address") else "",
                                    "buyer": _order['buyer'] if _order.has_key("buyer") else "",
                                    "seller": _order['seller'] if _order.has_key("seller") else "",
                                    "escrows": _order['escrows'] if _order.has_key("escrows") else "",
                                    "text": _order['text'] if _order.has_key("text") else "",
                                    "created": _order['created'] if _order.has_key("created") else ""})
            #orders.append(_order)


        return orders



    # Create a new order
    def create_order(self, seller, text):
        self._log.info('CREATING ORDER')
        id = random.randint(0,1000000)
        buyer = self._transport._myself.get_pubkey()
        new_order = order(id, buyer, seller, 'new', text, self._escrows)

        # Add a timestamp
        new_order['created'] = time.time()

        self._transport.send(new_order, seller)

        self._db.orders.insert(new_order)


    def accept_order(self, new_order):

    	# TODO: Need to have a check for the vendor to agree to the order

        new_order['state'] = 'accepted'
        seller = new_order['seller'].decode('hex')
        buyer = new_order['buyer'].decode('hex')

        new_order['escrows'] = [new_order.get('escrows')[0]]
        escrow = new_order['escrows'][0].decode('hex')

        # Create 2 of 3 multisig address
        self._multisig = Multisig(None, 2, [buyer, seller, escrow])

        new_order['address'] = self._multisig.address

        self._db.orders.update({ "id":new_order['id']}, {"$set":new_order}, True)

        self._transport.send(new_order, new_order['buyer'].decode('hex'))

    def pay_order(self, new_order): # action
        new_order['state'] = 'paid'
        self._db.orders.update({"id":new_order['id']}, {"$set":new_order}, True)
        new_order['type'] = 'order'
        self._transport.send(new_order, new_order['seller'].decode('hex'))

    def send_order(self, new_order): # action
        new_order['state'] = 'sent'
        self._db.orders.update({"id":new_order['id']}, {"$set":new_order}, True)
        new_order['type'] = 'order'
        self._transport.send(new_order, new_order['buyer'].decode('hex'))

    def receive_order(self, new_order): # action
        new_order['state'] = 'received'
        self._db.orders.update({"id":new_order['id']}, {"$set":new_order}, True)
        self._transport.send(new_order, new_order['seller'].decode('hex'))


    # Order callbacks
    def on_order(self, msg):

        state = msg.get('state')

        buyer = msg.get('buyer').decode('hex')
        seller = msg.get('seller').decode('hex')
        myself = self._transport._myself.get_pubkey()

        if not buyer or not seller or not state:
            self._log.info("Malformed order")
            return

        if not state == 'new' and not msg.get('id'):
            self._log.info("Order with no id")
            return

        # Check order state
        if state == 'new':
            if myself == buyer:
                self.create_order(seller, msg.get('text', 'no comments'))
            elif myself == seller:
                self._log.info(msg)
                self.accept_order(msg)
            else:
                self._log.info("Not a party to this order")

        elif state == 'cancelled':
            if myself == seller or myself == buyer:
                self._log.info('Order cancelled')
            else:
                self._log.info("Order not for us")

        elif state == 'accepted':
            if myself == seller:
                self._log.info("Bad subjects [%s]" % state)
            elif myself == buyer:
                # wait for confirmation
                self._db.orders.update({"id":msg['id']}, {"$set":msg}, True)
                pass
            else:
                self._log.info("Order not for us")
        elif state == 'paid':
            if myself == seller:
                # wait for  confirmation
                pass
            elif myself == buyer:
                self.pay_order(msg)
            else:
                self._log.info("Order not for us")
        elif state == 'sent':
            if myself == seller:
                self.send_order(msg)
            elif myself == buyer:
                # wait for confirmation
                pass
            else:
                self._log.info("Order not for us")
        elif state == 'received':
            if myself == seller:
                pass
                # ok
            elif myself == buyer:
                self.receive_order(msg)
            else:
                self._log.info("Order not for us")

        # Store order
        if msg.get('id'):
            if self.orders.find( {id:msg['id']}):
                self.orders.update({'id':msg['id']}, { "$set": { 'state':msg['state'] } }, True)
            else:
                self.orders.update({'id':msg['id']}, { "$set": { msg } }, True)

if __name__ == '__main__':
    seller = ECC(curve='secp256k1')
    class FakeTransport():
        _myself = ECC(curve='secp256k1')
        def add_callback(self, section, cb):
            pass
        def send(self, msg, to=None):
            print 'sending', msg
        def log(self, msg):
            print msg
    transport = FakeTransport()
    rep = Orders(transport)
    rep.on_order(order(None, transport._myself.get_pubkey(), seller.get_pubkey(), 'new', 'One!', ["dsasd", "deadbeef"]))

########NEW FILE########
__FILENAME__ = p2p
import json
import logging
from collections import defaultdict
import traceback

from zmq.eventloop import ioloop
import zmq
from multiprocessing import Process, Queue
from threading import Thread
ioloop.install()

from protocol import goodbye
import network_util


# Connection to one peer
class PeerConnection(object):
    def __init__(self, transport, address):
        # timeout in seconds
        self._timeout = 10
        self._transport = transport
        self._address = address
        self._log = logging.getLogger(self.__class__.__name__)

    def create_socket(self):
        self._ctx = zmq.Context()
        self._socket = self._ctx.socket(zmq.REQ)
        self._socket.setsockopt(zmq.LINGER, 0)
        self._socket.connect(self._address)

    def cleanup_socket(self):
        self._socket.close()

    # Is this even used?
    def send(self, data):
        self.send_raw(json.dumps(data))

    def send_raw(self, serialized):
        Thread(target=self._send_raw, args=(serialized,)).start()
        pass

    def _send_raw(self, serialized):
        # pyzmq sockets are not threadsafe,
        # they have to run in a separate process
        queue = Queue()
        # queue element is false if something went wrong and the peer
        # has to be removed
        p = Process(target=self._send_raw_process, args=(serialized, queue))
        p.start()
        if not queue.get():
            self._log.info("Peer %s timed out." % self._address)
            self._transport.remove_peer(self._address)
        p.join()

    def _send_raw_process(self, serialized, queue):
        self.create_socket()
        self._socket.send(serialized)

        poller = zmq.Poller()
        poller.register(self._socket, zmq.POLLIN)
        if poller.poll(self._timeout * 5000):
            msg = self._socket.recv()
            self.on_message(msg)
            self.cleanup_socket()
            queue.put(True)

        else:
            self.cleanup_socket()
            queue.put(False)

    def on_message(self, msg):        
        self._log.info("message received! %s" % msg)


# Transport layer manages a list of peers
class TransportLayer(object):
    def __init__(self, my_ip, my_port):
        self._peers = {}
        self._callbacks = defaultdict(list)
        self._port = my_port
        self._ip = my_ip
        self._uri = 'tcp://%s:%s' % (self._ip, self._port)
        self._log = logging.getLogger(self.__class__.__name__)
        # signal.signal(signal.SIGTERM, lambda x, y: self.broadcast_goodbye())

    def add_callback(self, section, callback):
        self._callbacks[section].append(callback)

    def trigger_callbacks(self, section, *data):
        for cb in self._callbacks[section]:
            cb(*data)
        if not section == 'all':
            for cb in self._callbacks['all']:
                cb(*data)

    def get_profile(self):
        return {'type': 'hello_request', 'uri': self._uri}

    def join_network(self, seed_uri):
        self.listen()

        if seed_uri:
            self.init_peer({'uri': seed_uri})

    def listen(self):
        t = Thread(target=self._listen)
        t.setDaemon(True)
        t.start()

    def _listen(self):
        self._log.info("init server %s %s" % (self._ip, self._port))
        self._ctx = zmq.Context()
        self._socket = self._ctx.socket(zmq.REP)

        if network_util.is_loopback_addr(self._ip):
            # we are in local test mode so bind that socket on the
            # specified IP
            self._socket.bind(self._uri)
        else:
            self._socket.bind('tcp://*:%s' % self._port)

        while True:
            message = self._socket.recv()
            self.on_raw_message(message)
            self._socket.send(json.dumps({'type': "ok"}))

    def closed(self, *args):
        self._log.info("client left")

    def _init_peer(self, msg):
        uri = msg['uri']

        if uri not in self._peers:
            self._peers[uri] = PeerConnection(self, uri)

    def remove_peer(self, uri):
        self._log.info("Removing peer %s", uri)
        try:
            del self._peers[uri]
            msg = {
                'type': 'peer_remove',
                'uri': uri
            }
            self.trigger_callbacks(msg['type'], msg)

        except KeyError:
            self._log.info("Peer %s was already removed", uri)

    def send(self, data, send_to=None):

        # self._log.info("Data sent to p2p: %s" % data);

        # directed message
        if send_to:
            for peer in self._peers.values():
                if peer._pub == send_to:
                    if peer.send(data):
                        self._log.info('Success')
                    else:
                        self._log.info('Failed')

                    return

            self._log.info("Peer not found! %s %s",
                           send_to, self._myself.get_pubkey())
            return

        # broadcast
        for peer in self._peers.values():
            try:
                if peer._pub:
                    peer.send(data)
                else:
                    serialized = json.dumps(data)
                    peer.send_raw(serialized)
            except:
                self._log.info("Error sending over peer!")
                traceback.print_exc()

    def broadcast_goodbye(self):
        self._log.info("Broadcast goodbye")
        msg = goodbye({'uri': self._uri})
        self.send(msg)

    def on_message(self, msg):
        # here goes the application callbacks
        # we get a "clean" msg which is a dict holding whatever
        self._log.info("Data received: %s" % msg)
        self.trigger_callbacks(msg.get('type'), msg)

    def on_raw_message(self, serialized):
        self._log.info("connected " + str(len(serialized)))
        try:
            msg = json.loads(serialized[0])
        except:
            self._log.info("incorrect msg! " + serialized)
            return

        msg_type = msg.get('type')
        if msg_type == 'hello_request' and msg.get('uri'):
            self.init_peer(msg)
        else:
            self.on_message(msg)

    def valid_peer_uri(self, uri):
        try:
            [self_protocol, self_addr, self_port] = \
                network_util.uri_parts(self._uri)
            [other_protocol, other_addr, other_port] = \
                network_util.uri_parts(uri)
        except RuntimeError:
            return False

        if not network_util.is_valid_protocol(other_protocol)  \
                or not network_util.is_valid_port(other_port):
            return False

        if network_util.is_private_ip_address(self_addr):
            if not network_util.is_private_ip_address(other_addr):
                self._log.warning(('Trying to connect to external '
                                   'network with a private ip address.'))
        else:
            if network_util.is_private_ip_address(other_addr):
                return False

        return True

########NEW FILE########
__FILENAME__ = protocol
def hello_request(data):
    data['type'] = 'hello_request'
    return data


def hello_response(data):
    data['type'] = 'hello_reply'
    return data


def goodbye(data):
    data['type'] = 'goodbye'
    return data


def ok():
    return {'type': 'ok'}


def shout(data):
    data['type'] = 'shout'
    return data

def proto_welcome():
    return {'type':'welcome'}

def proto_reputation(pubkey, reviews):
    data = {}
    data['type'] = 'reputation'
    data['pubkey'] = pubkey.encode('hex')
    data['reviews'] = reviews
    return data


def proto_query_reputation(pubkey):
    data = {}
    data['type'] = 'query_reputation'
    data['pubkey'] = pubkey.encode('hex')
    return data


def proto_page(pubkey, text, signature, nickname):
    data = {}
    data['type'] = 'page'
    data['pubkey'] = pubkey
    data['signature'] = signature.encode('hex')
    data['text'] = text
    data['nickname'] = nickname
    return data


def query_page(pubkey):
    data = {}
    data['type'] = 'query_page'
    data['pubkey'] = pubkey.encode('hex')
    return data


def order(id, buyer, seller, state, text, escrows=[], tx=None):
    data = {}
    data['type'] = 'order'
    data['id'] = id
    # this is who signs
    data['buyer'] = buyer.encode('hex')
    # this is who the review is about
    data['seller'] = seller.encode('hex')
    # the signature
    data['escrows'] = escrows
    # the signature
    if data.get('tex'):
        data['tx'] = tx.encode('hex')
    # some text
    data['text'] = text
    # some text
    data['address'] = ''
    data['state'] = state
    # new -> accepted/rejected -> payed -> sent -> received
    return data


def negotiate_pubkey(nickname, ident_pubkey):
    data = {}
    data['type'] = 'negotiate_pubkey'
    data['nickname'] = nickname
    data['ident_pubkey'] = ident_pubkey.encode("hex")
    return data


def proto_response_pubkey(nickname, pubkey, signature):
    data = {}
    data['type'] = "proto_response_pubkey"
    data['nickname'] = nickname
    data['pubkey'] = pubkey.encode("hex")
    data['signature'] = signature.encode("hex")
    return data

########NEW FILE########
__FILENAME__ = reputation
import json
from protocol import proto_reputation, proto_query_reputation
from collections import defaultdict
from pyelliptic import ECC
import logging

def review(pubkey, subject, signature, text, rating):
    data = {}
    # this is who signs
    data['pubkey'] = pubkey.encode('hex')
    # this is who the review is about
    data['subject'] = subject.encode('hex')
    # the signature
    data['sig'] = signature.encode('hex')
    # some text
    data['text'] = text
    # rating
    data['rating'] = rating
    return data

class Reputation(object):
    def __init__(self, transport):

        self._transport = transport
        self._priv = transport._myself

        # TODO: Pull reviews out of persistent storage
        self._reviews = defaultdict(list)

        transport.add_callback('reputation', self.on_reputation)
        transport.add_callback('query_reputation', self.on_query_reputation)

        # SAMPLE Review because there is no persistence of reviews ATM
        #self.create_review(self._priv.get_pubkey(), "Initial Review", 10)

        self._log = logging.getLogger(self.__class__.__name__)


    # getting reputation from inside the application
    def get_reputation(self, pubkey):
        return self._reviews[pubkey]


    def get_my_reputation(self):
        return self._reviews[self._priv.get_pubkey()]


    # Create a new review and broadcast to the network
    def create_review(self, pubkey, text, rating):

        signature = self._priv.sign(self._build_review(pubkey, text, rating))

        new_review = review(self._priv.get_pubkey(), pubkey, signature, text, rating)
        self._reviews[pubkey].append(new_review)

        # Broadcast the review
        self._transport.send(proto_reputation(pubkey, [new_review]))


    # Build JSON for review to be signed
    def _build_review(self, pubkey, text, rating):
        return json.dumps([pubkey.encode('hex'),  text, rating])


	# Query reputation for pubkey from the network
    def query_reputation(self, pubkey):
        self._transport.send(proto_query_reputation(pubkey))


	#
    def parse_review(self, msg):

        pubkey = msg['pubkey'].decode('hex')
        subject = msg['subject'].decode('hex')
        signature = msg['sig'].decode('hex')
        text = msg['text']
        rating = msg['rating']

        # check the signature
        valid = ECC(pubkey=pubkey).verify(signature, self._build_review(subject, str(text), rating))

        if valid:
            newreview = review(pubkey, subject, signature, text, rating)

            if newreview not in self._reviews[subject]:
                self._reviews[subject].append(newreview)

        else:
            self._log.info("[reputation] Invalid review!")


    # callbacks for messages
    # a new review has arrived
    def on_reputation(self, msg):
        for review in msg.get('reviews', []):
            self.parse_review(review)

    # query reviews has arrived
    def on_query_reputation(self, msg):
        pubkey = msg['pubkey'].decode('hex')
        if pubkey in self._reviews:
            self._transport.send(proto_reputation(pubkey, self._reviews[pubkey]))


if __name__ == '__main__':
    class FakeTransport():
        _myself = ECC(curve='secp256k1')
        def add_callback(self, section, cb):
            pass
        def send(self, msg):
            print 'sending', msg
        def log(self, msg):
            print msg
    transport = FakeTransport()
    rep = Reputation(transport)
    print rep.get_reputation(transport._myself.get_pubkey())
    print rep.get_my_reputation()

########NEW FILE########
__FILENAME__ = tornadoloop
import sys
import argparse
import tornado.ioloop
import tornado.web
import tornado.ioloop
from zmq.eventloop import ioloop
ioloop.install()
from crypto2crypto import CryptoTransportLayer
from market import Market
from ws import WebSocketHandler
import logging
import signal
import threading


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.redirect("/html/index.html")


class MarketApplication(tornado.web.Application):

    def __init__(self, my_market_ip, my_market_port, seed_uri, market_id):

        self.transport = CryptoTransportLayer(my_market_ip,
                                              my_market_port,
                                              market_id)
        self.transport.join_network(seed_uri)
        self.market = Market(self.transport)

        handlers = [
            (r"/", MainHandler),
            (r"/main", MainHandler),
            (r"/html/(.*)", tornado.web.StaticFileHandler, {'path': './html'}),
            (r"/ws", WebSocketHandler,
                dict(transport=self.transport, node=self.market))
        ]

        # TODO: Move debug settings to configuration location
        settings = dict(debug=True)
        tornado.web.Application.__init__(self, handlers, **settings)

    def get_transport(self):
        return self.transport


def start_node(my_market_ip, my_market_port, seed_uri, log_file, userid):
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s -  \
                                %(levelname)s - %(message)s',
                        filename=log_file)

    application = MarketApplication(my_market_ip,
                                    my_market_port, seed_uri, userid)

    error = True
    port = 8888
    while error and port < 8988:
        try:
            application.listen(port)
            error = False
        except:
            port += 1

    logging.getLogger().info("Started user app at http://%s:%s"
                             % (my_market_ip, port))

    # handle shutdown
    def shutdown(x, y):
        application.get_transport().broadcast_goodbye()
        sys.exit(0)
    try:
        signal.signal(signal.SIGTERM, shutdown)
    except ValueError:
        # not the main thread
        pass

    tornado.ioloop.IOLoop.instance().start()

# Run this if executed directly
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("my_market_ip")
    parser.add_argument("-p", "--my_market_port", type=int, default=12345)
    parser.add_argument("-s", "--seed_uri")
    parser.add_argument("-l", "--log_file", default='node.log')
    parser.add_argument("-u", "--userid", default=1)
    args = parser.parse_args()
    start_node(args.my_market_ip,
               args.my_market_port, args.seed_uri, args.log_file, args.userid)

########NEW FILE########
__FILENAME__ = ws
import tornado.websocket
import threading
import logging
import json
import tornado.ioloop
import random
import protocol
import obelisk
import logging
import pycountry

class ProtocolHandler:
    def __init__(self, transport, node, handler):
        self.node = node
        self._transport = transport
        self._handler = handler

        # register on transport events to forward..
        transport.add_callback('peer', self.on_node_peer)
        transport.add_callback('peer_remove', self.on_node_remove_peer)
        transport.add_callback('page', self.on_node_page)
        transport.add_callback('all', self.on_node_message)

        # handlers from events coming from websocket, we shouldnt need this
        self._handlers = {
            "connect":          self.client_connect,
            "peers":          self.client_peers,
            "query_page":          self.client_query_page,
            "review":          self.client_review,
            "order":          self.client_order,
            "search":          self.client_search,
            "shout":          self.client_shout,
            "query_orders":	  self.client_query_orders,
            "query_products":	  self.client_query_products,
            "update_settings":	self.client_update_settings,
            "query_order":	self.client_query_order,
            "pay_order":	self.client_pay_order,
            "ship_order":	self.client_ship_order,
            "save_product":	self.client_save_product,
            "remove_product":	self.client_remove_product,
            "generate_secret":	self.client_generate_secret,
        }

        self._log = logging.getLogger(self.__class__.__name__)

    def send_opening(self):
        peers = self.get_peers()

        countryCodes = []
        for country in pycountry.countries:
          countryCodes.append({"code":country.alpha2, "name":country.name})

        settings = self.node.get_settings()

        message = {
            'type': 'myself',
            'pubkey': self._transport._myself.get_pubkey().encode('hex'),
            'peers': peers,
            'settings': settings,
            'countryCodes': countryCodes,
            'reputation': self.node.reputation.get_my_reputation()
        }

        self.send_to_client(None, message)

    # Requests coming from the client
    def client_connect(self, socket_handler, msg):
        self._log.info("Connection command: ", msg)
        self._transport.init_peer(msg)
        self.send_ok()

    def client_peers(self, socket_handler, msg):
        self._log.info("Peers command")
        self.send_to_client(None, {"type": "peers", "peers": self.get_peers()})

    def client_query_page(self, socket_handler, msg):
        self._log.info("Message: ", msg)
        pubkey = msg['pubkey'].decode('hex')
        self.node.query_page(pubkey)
        self.node.reputation.query_reputation(pubkey)

    def client_query_orders(self, socket_handler, msg):

        self._log.info("Querying for Orders")

        # Query mongo for orders
        orders = self.node.orders.get_orders()

        self.send_to_client(None, { "type": "myorders", "orders": orders } )

    def client_query_products(self, socket_handler, msg):

        self._log.info("Querying for Products")

        # Query mongo for products
        products = self.node.get_products()

        self.send_to_client(None, { "type": "products", "products": products } )

    # Get a single order's info
    def client_query_order(self, socket_handler, msg):



        # Query mongo for order
        order = self.node.orders.get_order(msg['orderId'])

        self.send_to_client(None, { "type": "orderinfo", "order": order } )


    def client_update_settings(self, socket_handler, msg):
        self._log.info("Updating settings: %s" % msg)

        self.send_to_client(None, { "type": "settings", "values": msg })

        # Update settings in mongo
        self.node.save_settings(msg['settings'])

    def client_save_product(self, socket_handler, msg):
        self._log.info("Save product: %s" % msg)

        # Update settings in mongo
        self.node.save_product(msg)

    def client_remove_product(self, socket_handler, msg):
        self._log.info("Remove product: %s" % msg)

        # Update settings in mongo
        self.node.remove_product(msg)

    def client_pay_order(self, socket_handler, msg):

        self._log.info("Marking Order as Paid: %s" % msg)

        # Update order in mongo
        order = self.node.orders.get_order(msg['orderId'])

        # Send to exchange partner
        self.node.orders.pay_order(order)

    def client_ship_order(self, socket_handler, msg):

        self._log.info("Shipping order out: %s" % msg)

        # Update order in mongo
        order = self.node.orders.get_order(msg['orderId'])

        # Send to exchange partner
        self.node.orders.send_order(order)

    def client_generate_secret(self, socket_handler, msg):

      new_secret = self.node.generate_new_secret()
      self.send_opening()


    def client_order(self, socket_handler, msg):
        self.node.orders.on_order(msg)

    def client_review(self, socket_handler, msg):
        pubkey = msg['pubkey'].decode('hex')
        text = msg['text']
        rating = msg['rating']
        self.node.reputation.create_review(pubkey, text, rating)

    def client_search(self, socket_handler, msg):
        self._log.info("[Search] %s"% msg)
        response = self.node.lookup(msg)
        if response:
            self._log.info(response)
            self.send_to_client(*response)

    def client_shout(self, socket_handler, msg):
        self._transport.send(protocol.shout(msg))

    # messages coming from "the market"
    def on_node_peer(self, peer):
        self._log.info("Add peer")

        response = {'type': 'peer',
                    'pubkey': peer._pub.encode('hex')
                              if peer._pub
                              else 'unknown',
                    #'nickname': peer.
                    'uri': peer._address}
        self.send_to_client(None, response)

    def on_node_remove_peer(self, msg):
        self.send_to_client(None, msg)

    def on_node_page(self, page):
        self.send_to_client(None, page)

    def on_node_message(self, *args):
        first = args[0]
        if isinstance(first, dict):
            self.send_to_client(None, first)
        else:
            self._log.info("can't format")

    # send a message
    def send_to_client(self, error, result):
        assert error is None or type(error) == str
        response = {
            "id": random.randint(0, 1000000),
            "result": result
        }
        if error:
            response["error"] = error
        self._handler.queue_response(response)

    def send_ok(self):
        self.send_to_client(None, {"type": "ok"})

    # handler a request
    def handle_request(self, socket_handler, request):
        command = request["command"]
        if command not in self._handlers:
            return False
        params = request["params"]
        # Create callback handler to write response to the socket.
        handler = self._handlers[command](socket_handler, params)
        return True

    def get_peers(self):
        peers = []
        for uri, peer in self._transport._peers.items():
            peer_item = {'uri': uri}
            if peer._pub:
                peer_item['pubkey'] = peer._pub.encode('hex')
            else:
                peer_item['pubkey'] = 'unknown'
            peers.append(peer_item)

        return peers

class WebSocketHandler(tornado.websocket.WebSocketHandler):

    # Set of WebsocketHandler
    listeners = set()
    # Protects listeners
    listen_lock = threading.Lock()

    def initialize(self, transport, node):
        self._log = logging.getLogger(self.__class__.__name__)
        self._log.info("Initialize websockethandler")
        self._app_handler = ProtocolHandler(transport, node, self)
        self.node = node
        self._transport = transport

    def open(self):
        self._log.info('Websocket open')
        self._app_handler.send_opening()
        with WebSocketHandler.listen_lock:
            self.listeners.add(self)
        self._connected = True

    def on_close(self):
        self._log.info("websocket closed")
        disconnect_msg = {'command': 'disconnect_client', 'id': 0, 'params': []}
        self._connected = False
        self._app_handler.handle_request(self, disconnect_msg)
        with WebSocketHandler.listen_lock:
            self.listeners.remove(self)

    def _check_request(self, request):
        return request.has_key("command") and request.has_key("id") and \
            request.has_key("params") and type(request["params"]) == dict
            #request.has_key("params") and type(request["params"]) == list

    def on_message(self, message):

        self._log.info('Message: %s' % message)

        try:
            request = json.loads(message)
        except:
            logging.error("Error decoding message: %s", message, exc_info=True)

        # Check request is correctly formed.
        if not self._check_request(request):
            logging.error("Malformed request: %s", request, exc_info=True)
            return
        if self._app_handler.handle_request(self, request):
            return

    def _send_response(self, response):
        if self.ws_connection:
            self.write_message(json.dumps(response))
        #try:
        #    self.write_message(json.dumps(response))
        #except tornado.websocket.WebSocketClosedError:
        #    logging.warning("Dropping response to closed socket: %s",
        #       response, exc_info=True)

    def queue_response(self, response):
        ioloop = tornado.ioloop.IOLoop.instance()
        def send_response(*args):
            self._send_response(response)
        try:
            # calling write_message or the socket is not thread safe
            ioloop.add_callback(send_response)
        except:
            logging.error("Error adding callback", exc_info=True)

########NEW FILE########
__FILENAME__ = bitcoin
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2011 thomasv@gitorious
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import hashlib, base64, ecdsa, re
from util import print_error
from config import chain
import models
import numbertheory
import os

def rev_hex(s):
    return s.decode('hex')[::-1].encode('hex')

def int_to_hex(i, length=1):
    s = hex(i)[2:].rstrip('L')
    s = "0"*(2*length - len(s)) + s
    return rev_hex(s)

def var_int(i):
    # https://en.bitcoin.it/wiki/Protocol_specification#Variable_length_integer
    if i<0xfd:
        return int_to_hex(i)
    elif i<=0xffff:
        return "fd"+int_to_hex(i,2)
    elif i<=0xffffffff:
        return "fe"+int_to_hex(i,4)
    else:
        return "ff"+int_to_hex(i,8)

def op_push(i):
    if i<0x4c:
        return int_to_hex(i)
    elif i<0xff:
        return '4c' + int_to_hex(i)
    elif i<0xffff:
        return '4d' + int_to_hex(i,2)
    else:
        return '4e' + int_to_hex(i,4)
    


Hash = lambda x: hashlib.sha256(hashlib.sha256(x).digest()).digest()
hash_encode = lambda x: x[::-1].encode('hex')
hash_decode = lambda x: x.decode('hex')[::-1]


# pywallet openssl private key implementation

def i2d_ECPrivateKey(pkey, compressed=False):
    if compressed:
        key = '3081d30201010420' + \
              '%064x' % pkey.secret + \
              'a081a53081a2020101302c06072a8648ce3d0101022100' + \
              '%064x' % _p + \
              '3006040100040107042102' + \
              '%064x' % _Gx + \
              '022100' + \
              '%064x' % _r + \
              '020101a124032200'
    else:
        key = '308201130201010420' + \
              '%064x' % pkey.secret + \
              'a081a53081a2020101302c06072a8648ce3d0101022100' + \
              '%064x' % _p + \
              '3006040100040107044104' + \
              '%064x' % _Gx + \
              '%064x' % _Gy + \
              '022100' + \
              '%064x' % _r + \
              '020101a144034200'
        
    return key.decode('hex') + i2o_ECPublicKey(pkey.pubkey, compressed)
    
def i2o_ECPublicKey(pubkey, compressed=False):
    # public keys are 65 bytes long (520 bits)
    # 0x04 + 32-byte X-coordinate + 32-byte Y-coordinate
    # 0x00 = point at infinity, 0x02 and 0x03 = compressed, 0x04 = uncompressed
    # compressed keys: <sign> <x> where <sign> is 0x02 if y is even and 0x03 if y is odd
    if compressed:
        if pubkey.point.y() & 1:
            key = '03' + '%064x' % pubkey.point.x()
        else:
            key = '02' + '%064x' % pubkey.point.x()
    else:
        key = '04' + \
              '%064x' % pubkey.point.x() + \
              '%064x' % pubkey.point.y()
            
    return key.decode('hex')
            
# end pywallet openssl private key implementation

                                                
            
############ functions from pywallet ##################### 

def hash_160(public_key):
    try:
        md = hashlib.new('ripemd160')
        md.update(hashlib.sha256(public_key).digest())
        return md.digest()
    except:
        import ripemd
        md = ripemd.new(hashlib.sha256(public_key).digest())
        return md.digest()


def public_key_to_bc_address(public_key):
    h160 = hash_160(public_key)
    return hash_160_to_bc_address(h160)

def hash_160_to_bc_address(h160, addrtype=chain.pubkey_version):
    vh160 = chr(addrtype) + h160
    h = Hash(vh160)
    addr = vh160 + h[0:4]
    return b58encode(addr)

def bc_address_to_hash_160(addr):
    bytes = b58decode(addr, 25)
    return ord(bytes[0]), bytes[1:21]

def encode_point(pubkey, compressed=False):
    order = generator_secp256k1.order()
    p = pubkey.pubkey.point
    x_str = ecdsa.util.number_to_string(p.x(), order)
    y_str = ecdsa.util.number_to_string(p.y(), order)
    if compressed:
        return chr(2 + (p.y() & 1)) + x_str
    else:
        return chr(4) + pubkey.to_string() #x_str + y_str

__b58chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
__b58base = len(__b58chars)

def b58encode(v):
    """ encode v, which is a string of bytes, to base58."""

    long_value = 0L
    for (i, c) in enumerate(v[::-1]):
        long_value += (256**i) * ord(c)

    result = ''
    while long_value >= __b58base:
        div, mod = divmod(long_value, __b58base)
        result = __b58chars[mod] + result
        long_value = div
    result = __b58chars[long_value] + result

    # Bitcoin does a little leading-zero-compression:
    # leading 0-bytes in the input become leading-1s
    nPad = 0
    for c in v:
        if c == '\0': nPad += 1
        else: break

    return (__b58chars[0]*nPad) + result

def b58decode(v, length):
    """ decode v into a string of len bytes."""
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


def EncodeBase58Check(vchIn):
    hash = Hash(vchIn)
    return b58encode(vchIn + hash[0:4])

def DecodeBase58Check(psz):
    vchRet = b58decode(psz, None)
    key = vchRet[0:-4]
    csum = vchRet[-4:]
    hash = Hash(key)
    cs32 = hash[0:4]
    if cs32 != csum:
        return None
    else:
        return key

def PrivKeyToSecret(privkey):
    return privkey[9:9+32]

def SecretToASecret(secret, compressed=False, addrtype=chain.pubkey_version):
    vchIn = chr((addrtype+128)&255) + secret
    if compressed: vchIn += '\01'
    return EncodeBase58Check(vchIn)

def ASecretToSecret(key, addrtype=chain.pubkey_version):
    vch = DecodeBase58Check(key)
    if vch and vch[0] == chr((addrtype+128)&255):
        return vch[1:]
    else:
        return False

def regenerate_key(sec):
    b = ASecretToSecret(sec)
    if not b:
        return False
    b = b[0:32]
    secret = int('0x' + b.encode('hex'), 16)
    return EC_KEY(secret)

def GetPubKey(pubkey, compressed=False):
    return i2o_ECPublicKey(pubkey, compressed)

def GetPrivKey(pkey, compressed=False):
    return i2d_ECPrivateKey(pkey, compressed)

def GetSecret(pkey):
    return ('%064x' % pkey.secret).decode('hex')

def is_compressed(sec):
    b = ASecretToSecret(sec)
    return len(b) == 33


def address_from_private_key(sec):
    # rebuild public key from private key, compressed or uncompressed
    pkey = regenerate_key(sec)
    assert pkey

    # figure out if private key is compressed
    compressed = is_compressed(sec)
        
    # rebuild private and public key from regenerated secret
    private_key = GetPrivKey(pkey, compressed)
    public_key = GetPubKey(pkey.pubkey, compressed)
    address = public_key_to_bc_address(public_key)
    return address


def is_valid(addr):
    ADDRESS_RE = re.compile('[1-9A-HJ-NP-Za-km-z]{26,}\\Z')
    if not ADDRESS_RE.match(addr): return False
    try:
        addrtype, h = bc_address_to_hash_160(addr)
    except:
        return False
    return addr == hash_160_to_bc_address(h, addrtype)


########### end pywallet functions #######################

# secp256k1, http://www.oid-info.com/get/1.3.132.0.10
_p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2FL
_r = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141L
_b = 0x0000000000000000000000000000000000000000000000000000000000000007L
_a = 0x0000000000000000000000000000000000000000000000000000000000000000L
_Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798L
_Gy = 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8L
curve_secp256k1 = ecdsa.ellipticcurve.CurveFp( _p, _a, _b )
generator_secp256k1 = ecdsa.ellipticcurve.Point( curve_secp256k1, _Gx, _Gy, _r )
oid_secp256k1 = (1,3,132,0,10)
SECP256k1 = ecdsa.curves.Curve("SECP256k1", curve_secp256k1, generator_secp256k1, oid_secp256k1 ) 
ec_order = _r

from ecdsa.util import string_to_number, number_to_string

def msg_magic(message):
    return "\x18Bitcoin Signed Message:\n" + chr( len(message) ) + message


class EC_KEY(object):
    def __init__( self, secret ):
        self.pubkey = ecdsa.ecdsa.Public_key( generator_secp256k1, generator_secp256k1 * secret )
        self.privkey = ecdsa.ecdsa.Private_key( self.pubkey, secret )
        self.secret = secret

    def sign_message(self, message, compressed, address):
        private_key = ecdsa.SigningKey.from_secret_exponent( self.secret, curve = SECP256k1 )
        public_key = private_key.get_verifying_key()
        signature = private_key.sign_digest( Hash( msg_magic(message) ), sigencode = ecdsa.util.sigencode_string )
        assert public_key.verify_digest( signature, Hash( msg_magic(message) ), sigdecode = ecdsa.util.sigdecode_string)
        for i in range(4):
            sig = base64.b64encode( chr(27 + i + (4 if compressed else 0)) + signature )
            try:
                self.verify_message( address, sig, message)
                return sig
            except:
                continue
        else:
            raise BaseException("error: cannot sign message")

    @classmethod
    def verify_message(self, address, signature, message):
        """ See http://www.secg.org/download/aid-780/sec1-v2.pdf for the math """
        from ecdsa import numbertheory, ellipticcurve, util
        import msqr
        curve = curve_secp256k1
        G = generator_secp256k1
        order = G.order()
        # extract r,s from signature
        sig = base64.b64decode(signature)
        if len(sig) != 65: raise BaseException("Wrong encoding")
        r,s = util.sigdecode_string(sig[1:], order)
        nV = ord(sig[0])
        if nV < 27 or nV >= 35:
            raise BaseException("Bad encoding")
        if nV >= 31:
            compressed = True
            nV -= 4
        else:
            compressed = False

        recid = nV - 27
        # 1.1
        x = r + (recid/2) * order
        # 1.3
        alpha = ( x * x * x  + curve.a() * x + curve.b() ) % curve.p()
        beta = msqr.modular_sqrt(alpha, curve.p())
        y = beta if (beta - recid) % 2 == 0 else curve.p() - beta
        # 1.4 the constructor checks that nR is at infinity
        R = ellipticcurve.Point(curve, x, y, order)
        # 1.5 compute e from message:
        h = Hash( msg_magic(message) )
        e = string_to_number(h)
        minus_e = -e % order
        # 1.6 compute Q = r^-1 (sR - eG)
        inv_r = numbertheory.inverse_mod(r,order)
        Q = inv_r * ( s * R + minus_e * G )
        public_key = ecdsa.VerifyingKey.from_public_point( Q, curve = SECP256k1 )
        # check that Q is the public key
        public_key.verify_digest( sig[1:], h, sigdecode = ecdsa.util.sigdecode_string)
        # check that we get the original signing address
        addr = public_key_to_bc_address( encode_point(public_key, compressed) )
        if address != addr:
            raise BaseException("Bad signature")


###################################### BIP32 ##############################

random_seed = lambda n: "%032x"%ecdsa.util.randrange( pow(2,n) )
BIP32_PRIME = 0x80000000

def bip32_init(seed):
    import hmac
    seed = seed.decode('hex')        
    I = hmac.new("Bitcoin seed", seed, hashlib.sha512).digest()

    master_secret = I[0:32]
    master_chain = I[32:]

    K, K_compressed = get_pubkeys_from_secret(master_secret)
    return master_secret, master_chain, K, K_compressed


def get_pubkeys_from_secret(secret):
    # public key
    curve = SECP256k1
    private_key = ecdsa.SigningKey.from_string( secret, curve = SECP256k1 )
    public_key = private_key.get_verifying_key()
    K = public_key.to_string()
    K_compressed = GetPubKey(public_key.pubkey,True)
    return K, K_compressed



    
def CKD(k, c, n):
    import hmac
    from ecdsa.util import string_to_number, number_to_string
    order = generator_secp256k1.order()
    keypair = EC_KEY(string_to_number(k))
    K = GetPubKey(keypair.pubkey,True)

    if n & BIP32_PRIME:
        data = chr(0) + k + rev_hex(int_to_hex(n,4)).decode('hex')
        I = hmac.new(c, data, hashlib.sha512).digest()
    else:
        I = hmac.new(c, K + rev_hex(int_to_hex(n,4)).decode('hex'), hashlib.sha512).digest()
        
    k_n = number_to_string( (string_to_number(I[0:32]) + string_to_number(k)) % order , order )
    c_n = I[32:]
    return k_n, c_n


def CKD_prime(K, c, n):
    import hmac
    from ecdsa.util import string_to_number, number_to_string
    order = generator_secp256k1.order()

    if n & BIP32_PRIME: raise

    K_public_key = ecdsa.VerifyingKey.from_string( K, curve = SECP256k1 )
    K_compressed = GetPubKey(K_public_key.pubkey,True)

    I = hmac.new(c, K_compressed + rev_hex(int_to_hex(n,4)).decode('hex'), hashlib.sha512).digest()

    curve = SECP256k1
    pubkey_point = string_to_number(I[0:32])*curve.generator + K_public_key.pubkey.point
    public_key = ecdsa.VerifyingKey.from_public_point( pubkey_point, curve = SECP256k1 )

    K_n = public_key.to_string()
    K_n_compressed = GetPubKey(public_key.pubkey,True)
    c_n = I[32:]

    return K_n, K_n_compressed, c_n



class ElectrumSequence:
    """  Privatekey(type,n) = Master_private_key + H(n|S|type)  """

    def __init__(self, mpk, mpk2 = None, mpk3 = None):
        self.mpk = mpk
        self.mpk2 = mpk2
        self.mpk3 = mpk3
        self.master_public_key = ecdsa.VerifyingKey.from_string( mpk.decode('hex'), curve = SECP256k1 )

    @classmethod
    def mpk_from_seed(klass, seed):
        curve = SECP256k1
        secexp = klass.stretch_key(seed)
        master_private_key = ecdsa.SigningKey.from_secret_exponent( secexp, curve = SECP256k1 )
        master_public_key = master_private_key.get_verifying_key().to_string().encode('hex')
        return master_public_key

    @classmethod
    def stretch_key(self,seed):
        oldseed = seed
        for i in range(100000):
            seed = hashlib.sha256(seed + oldseed).digest()
        return string_to_number( seed )

    def get_sequence(self, sequence, mpk):
        for_change, n = sequence
        return string_to_number( Hash( "%d:%d:"%(n,for_change) + mpk.decode('hex') ) )

    def get_address(self, sequence):
        if not self.mpk2:
            pubkey = self.get_pubkey(sequence)
            address = public_key_to_bc_address( pubkey.decode('hex') )
        elif not self.mpk3:
            pubkey1 = self.get_pubkey(sequence)
            pubkey2 = self.get_pubkey(sequence, mpk = self.mpk2)
            address = Transaction.multisig_script([pubkey1, pubkey2], 2)["address"]
        else:
            pubkey1 = self.get_pubkey(sequence)
            pubkey2 = self.get_pubkey(sequence, mpk = self.mpk2)
            pubkey3 = self.get_pubkey(sequence, mpk = self.mpk3)
            address = Transaction.multisig_script([pubkey1, pubkey2, pubkey3], 2)["address"]
        return address

    def get_pubkey(self, sequence, mpk=None):
        curve = SECP256k1
        if mpk is None: mpk = self.mpk
        z = self.get_sequence(sequence, mpk)
        master_public_key = self.master_public_key
        pubkey_point = master_public_key.pubkey.point + z*curve.generator
        public_key2 = ecdsa.VerifyingKey.from_public_point( pubkey_point, curve = SECP256k1 )
        return '04' + public_key2.to_string().encode('hex')

    def get_private_key_from_stretched_exponent(self, sequence, secexp):
        order = generator_secp256k1.order()
        secexp = ( secexp + self.get_sequence(sequence, self.mpk) ) % order
        pk = number_to_string( secexp, generator_secp256k1.order() )
        compressed = False
        return SecretToASecret( pk, compressed )
        
    def get_private_key(self, sequence, seed):
        secexp = self.stretch_key(seed)
        return self.get_private_key_from_stretched_exponent(sequence, secexp)

    def get_private_keys(self, sequence_list, seed):
        secexp = self.stretch_key(seed)
        return [ self.get_private_key_from_stretched_exponent( sequence, secexp) for sequence in sequence_list]

    def check_seed(self, seed):
        curve = SECP256k1
        secexp = self.stretch_key(seed)
        master_private_key = ecdsa.SigningKey.from_secret_exponent( secexp, curve = SECP256k1 )
        master_public_key = master_private_key.get_verifying_key().to_string().encode('hex')
        if master_public_key != self.mpk:
            print_error('invalid password (mpk)')
            raise BaseException('Invalid password')
        return True

    def get_input_info(self, sequence):
        if not self.mpk2:
            pk_addr = self.get_address(sequence)
            redeemScript = None
        elif not self.mpk3:
            pubkey1 = self.get_pubkey(sequence)
            pubkey2 = self.get_pubkey(sequence,mpk=self.mpk2)
            pk_addr = public_key_to_bc_address( pubkey1.decode('hex') ) # we need to return that address to get the right private key
            redeemScript = Transaction.multisig_script([pubkey1, pubkey2], 2)['redeemScript']
        else:
            pubkey1 = self.get_pubkey(sequence)
            pubkey2 = self.get_pubkey(sequence, mpk=self.mpk2)
            pubkey3 = self.get_pubkey(sequence, mpk=self.mpk3)
            pk_addr = public_key_to_bc_address( pubkey1.decode('hex') ) # we need to return that address to get the right private key
            redeemScript = Transaction.multisig_script([pubkey1, pubkey2, pubkey3], 2)['redeemScript']
        return pk_addr, redeemScript




class BIP32Sequence:

    def __init__(self, mpk, mpk2 = None, mpk3 = None):
        self.mpk = mpk
        self.mpk2 = mpk2
        self.mpk3 = mpk3
    
    @classmethod
    def mpk_from_seed(klass, seed):
        master_secret, master_chain, master_public_key, master_public_key_compressed = bip32_init(seed)
        return master_public_key.encode('hex'), master_chain.encode('hex')

    def get_pubkey(self, sequence, mpk = None):
        if not mpk: mpk = self.mpk
        master_public_key, master_chain = mpk
        K = master_public_key.decode('hex')
        chain = master_chain.decode('hex')
        for i in sequence:
            K, K_compressed, chain = CKD_prime(K, chain, i)
        return K_compressed.encode('hex')

    def get_address(self, sequence):
        if not self.mpk2:
            pubkey = self.get_pubkey(sequence)
            address = public_key_to_bc_address( pubkey.decode('hex') )
        elif not self.mpk3:
            pubkey1 = self.get_pubkey(sequence)
            pubkey2 = self.get_pubkey(sequence, mpk = self.mpk2)
            address = Transaction.multisig_script([pubkey1, pubkey2], 2)["address"]
        else:
            pubkey1 = self.get_pubkey(sequence)
            pubkey2 = self.get_pubkey(sequence, mpk = self.mpk2)
            pubkey3 = self.get_pubkey(sequence, mpk = self.mpk3)
            address = Transaction.multisig_script([pubkey1, pubkey2, pubkey3], 2)["address"]
        return address

    def get_private_key(self, sequence, seed):
        master_secret, master_chain, master_public_key, master_public_key_compressed = bip32_init(seed)
        chain = master_chain
        k = master_secret
        for i in sequence:
            k, chain = CKD(k, chain, i)
        return SecretToASecret(k, True)

    def get_private_keys(self, sequence_list, seed):
        return [ self.get_private_key( sequence, seed) for sequence in sequence_list]

    def check_seed(self, seed):
        master_secret, master_chain, master_public_key, master_public_key_compressed = bip32_init(seed)
        assert self.mpk == (master_public_key.encode('hex'), master_chain.encode('hex'))

    def get_input_info(self, sequence):
        if not self.mpk2:
            pk_addr = self.get_address(sequence)
            redeemScript = None
        elif not self.mpk3:
            pubkey1 = self.get_pubkey(sequence)
            pubkey2 = self.get_pubkey(sequence, mpk=self.mpk2)
            pk_addr = public_key_to_bc_address( pubkey1.decode('hex') ) # we need to return that address to get the right private key
            redeemScript = Transaction.multisig_script([pubkey1, pubkey2], 2)['redeemScript']
        else:
            pubkey1 = self.get_pubkey(sequence)
            pubkey2 = self.get_pubkey(sequence, mpk=self.mpk2)
            pubkey3 = self.get_pubkey(sequence, mpk=self.mpk3)
            pk_addr = public_key_to_bc_address( pubkey1.decode('hex') ) # we need to return that address to get the right private key
            redeemScript = Transaction.multisig_script([pubkey1, pubkey2, pubkey3], 2)['redeemScript']
        return pk_addr, redeemScript

################################## transactions

MIN_RELAY_TX_FEE = 10000

class Transaction:
    
    def __init__(self, raw):
        self.raw = raw
        self.deserialize()
        self.inputs = self.d['inputs']
        self.outputs = self.d['outputs']
        self.outputs = map(lambda x: (x['address'],x['value']), self.outputs)
        self.input_info = None
        self.is_complete = True
        
    @classmethod
    def from_io(klass, inputs, outputs):
        raw = klass.serialize(inputs, outputs, for_sig = -1) # for_sig=-1 means do not sign
        self = klass(raw)
        self.is_complete = False
        self.inputs = inputs
        self.outputs = outputs
        extras = []
        for i in self.inputs:
            e = { 'txid':i['tx_hash'], 'vout':i['index'], 'scriptPubKey':i.get('raw_output_script') }
            extras.append(e)
        self.input_info = extras
        return self

    def __str__(self):
        return self.raw

    @classmethod
    def multisig_script(klass, public_keys, num=None):
        n = len(public_keys)
        if num is None: num = n
        # supports only "2 of 2", and "2 of 3" transactions
        assert num <= n and n in [2,3]
    
        if num==2:
            s = '52'
        elif num == 3:
            s = '53'
        else:
            raise
    
        for k in public_keys:
            s += var_int(len(k)/2)
            s += k
        if n==2:
            s += '52'
        elif n==3:
            s += '53'
        else:
            raise
        s += 'ae'

        out = { "address": hash_160_to_bc_address(hash_160(s.decode('hex')), 5), "redeemScript":s }
        return out

    @classmethod
    def serialize( klass, inputs, outputs, for_sig = None ):

        s  = int_to_hex(1,4)                                         # version
        s += var_int( len(inputs) )                                  # number of inputs
        for i in range(len(inputs)):
            txin = inputs[i]
            s += txin['tx_hash'].decode('hex')[::-1].encode('hex')   # prev hash
            s += int_to_hex(txin['index'],4)                         # prev index

            if for_sig is None:
                pubkeysig = txin.get('pubkeysig')
                if pubkeysig:
                    pubkey, sig = pubkeysig[0]
                    sig = sig + chr(1)                               # hashtype
                    script  = op_push( len(sig))
                    script += sig.encode('hex')
                    script += op_push( len(pubkey))
                    script += pubkey.encode('hex')
                else:
                    signatures = txin['signatures']
                    pubkeys = txin['pubkeys']
                    script = '00'                                    # op_0
                    for sig in signatures:
                        sig = sig + '01'
                        script += op_push(len(sig)/2)
                        script += sig

                    redeem_script = klass.multisig_script(pubkeys,2).get('redeemScript')
                    script += op_push(len(redeem_script)/2)
                    script += redeem_script

            elif for_sig==i:
                if txin.get('redeemScript'):
                    script = txin['redeemScript']                    # p2sh uses the inner script
                else:
                    script = txin['raw_output_script']               # scriptsig
            else:
                script=''
            s += var_int( len(script)/2 )                            # script length
            s += script
            s += "ffffffff"                                          # sequence

        s += var_int( len(outputs) )                                 # number of outputs
        for output in outputs:
            addr, amount = output
            s += int_to_hex( amount, 8)                              # amount
            addrtype, hash_160 = bc_address_to_hash_160(addr)
            if addrtype == chain.pubkey_version:
                script = '76a9'                                      # op_dup, op_hash_160
                script += '14'                                       # push 0x14 bytes
                script += hash_160.encode('hex')
                script += '88ac'                                     # op_equalverify, op_checksig
            elif addrtype == chain.script_version:
                script = 'a9'                                        # op_hash_160
                script += '14'                                       # push 0x14 bytes
                script += hash_160.encode('hex')
                script += '87'                                       # op_equal
            else:
                raise
            
            s += var_int( len(script)/2 )                           #  script length
            s += script                                             #  script
        s += int_to_hex(0,4)                                        #  lock time
        if for_sig is not None and for_sig != -1:
            s += int_to_hex(1, 4)                                   #  hash type
        return s


    def for_sig(self,i):
        return self.serialize(self.inputs, self.outputs, for_sig = i)


    def hash(self):
        return Hash(self.raw.decode('hex') )[::-1].encode('hex')

    def sign(self, private_keys):
        import deserialize

        for i in range(len(self.inputs)):
            txin = self.inputs[i]
            tx_for_sig = self.serialize( self.inputs, self.outputs, for_sig = i )

            if txin.get('redeemScript'):
                # 1 parse the redeem script
                num, redeem_pubkeys = deserialize.parse_redeemScript(txin.get('redeemScript'))
                self.inputs[i]["pubkeys"] = redeem_pubkeys

                # build list of public/private keys
                keypairs = {}
                for sec in private_keys.values():
                    compressed = is_compressed(sec)
                    pkey = regenerate_key(sec)
                    pubkey = GetPubKey(pkey.pubkey, compressed)
                    keypairs[ pubkey.encode('hex') ] = sec

                # list of already existing signatures
                signatures = txin.get("signatures",[])
                print_error("signatures",signatures)

                for pubkey in redeem_pubkeys:
                    public_key = ecdsa.VerifyingKey.from_string(pubkey[2:].decode('hex'), curve = SECP256k1)
                    for s in signatures:
                        try:
                            public_key.verify_digest( s.decode('hex')[:-1], Hash( tx_for_sig.decode('hex') ), sigdecode = ecdsa.util.sigdecode_der)
                            break
                        except ecdsa.keys.BadSignatureError:
                            continue
                    else:
                        # check if we have a key corresponding to the redeem script
                        if pubkey in keypairs.keys():
                            # add signature
                            sec = keypairs[pubkey]
                            compressed = is_compressed(sec)
                            pkey = regenerate_key(sec)
                            secexp = pkey.secret
                            private_key = ecdsa.SigningKey.from_secret_exponent( secexp, curve = SECP256k1 )
                            public_key = private_key.get_verifying_key()
                            sig = private_key.sign_digest( Hash( tx_for_sig.decode('hex') ), sigencode = ecdsa.util.sigencode_der )
                            assert public_key.verify_digest( sig, Hash( tx_for_sig.decode('hex') ), sigdecode = ecdsa.util.sigdecode_der)
                            signatures.append( sig.encode('hex') )
                        
                # for p2sh, pubkeysig is a tuple (may be incomplete)
                self.inputs[i]["signatures"] = signatures
                print_error("signatures",signatures)
                self.is_complete = len(signatures) == num

            else:
                sec = private_keys[txin['address']]
                compressed = is_compressed(sec)
                pkey = regenerate_key(sec)
                secexp = pkey.secret

                private_key = ecdsa.SigningKey.from_secret_exponent( secexp, curve = SECP256k1 )
                public_key = private_key.get_verifying_key()
                pkey = EC_KEY(secexp)
                pubkey = GetPubKey(pkey.pubkey, compressed)
                sig = private_key.sign_digest( Hash( tx_for_sig.decode('hex') ), sigencode = ecdsa.util.sigencode_der )
                assert public_key.verify_digest( sig, Hash( tx_for_sig.decode('hex') ), sigdecode = ecdsa.util.sigdecode_der)

                self.inputs[i]["pubkeysig"] = [(pubkey, sig)]
                self.is_complete = True

        self.raw = self.serialize( self.inputs, self.outputs )


    def deserialize(self):
        import deserialize
        vds = deserialize.BCDataStream()
        vds.write(self.raw.decode('hex'))
        self.d = deserialize.parse_Transaction(vds)
        return self.d
    

    def has_address(self, addr):
        found = False
        for txin in self.inputs:
            if addr == txin.get('address'): 
                found = True
                break
        for txout in self.outputs:
            if addr == txout[0]:
                found = True
                break
        return found


    def get_value(self, addresses, prevout_values):
        # return the balance for that tx
        is_relevant = False
        is_send = False
        is_pruned = False
        is_partial = False
        v_in = v_out = v_out_mine = 0

        for item in self.inputs:
            addr = item.get('address')
            if addr in addresses:
                is_send = True
                is_relevant = True
                key = item['prevout_hash']  + ':%d'%item['prevout_n']
                value = prevout_values.get( key )
                if value is None:
                    is_pruned = True
                else:
                    v_in += value
            else:
                is_partial = True

        if not is_send: is_partial = False
                    
        for item in self.outputs:
            addr, value = item
            v_out += value
            if addr in addresses:
                v_out_mine += value
                is_relevant = True

        if is_pruned:
            # some inputs are mine:
            fee = None
            if is_send:
                v = v_out_mine - v_out
            else:
                # no input is mine
                v = v_out_mine

        else:
            v = v_out_mine - v_in

            if is_partial:
                # some inputs are mine, but not all
                fee = None
                is_send = v < 0
            else:
                # all inputs are mine
                fee = v_out - v_in

        return is_relevant, is_send, v, fee

    def as_dict(self):
        import json
        out = {
            "hex":self.raw,
            "complete":self.is_complete
            }
        if not self.is_complete:
            extras = []
            for i in self.inputs:
                e = { 'txid':i['tx_hash'], 'vout':i['index'],
                      'scriptPubKey':i.get('raw_output_script'),
                      'KeyID':i.get('KeyID'),
                      'redeemScript':i.get('redeemScript'),
                      'signatures':i.get('signatures'),
                      'pubkeys':i.get('pubkeys'),
                      }
                extras.append(e)
            self.input_info = extras

            if self.input_info:
                out['input_info'] = json.dumps(self.input_info).replace(' ','')

        return out


    def requires_fee(self, verifier):
        # see https://en.bitcoin.it/wiki/Transaction_fees
        threshold = 57600000
        size = len(self.raw)/2
        if size >= 10000: 
            return True

        for o in self.outputs:
            value = o[1]
            if value < 1000000:
                return True
        sum = 0
        for i in self.inputs:
            age = verifier.get_confirmations(i["tx_hash"])[0]
            sum += i["value"] * age
        priority = sum / size
        print_error(priority, threshold)
        return priority < threshold 

class HighDefWallet:

    def __init__(self, secret, chain, mpk, mpk_compressed):
        self.secret, self.chain, self.mpk, self.mpk_compressed = \
            secret, chain, mpk, mpk_compressed

    @property
    def key_id(self):
        return hash_160(self.mpk_compressed)

    @property
    def address(self):
        return hash_160_to_bc_address(self.key_id)

    @property
    def secret_key(self):
        return SecretToASecret(self.secret, True)

    def branch(self, n):
        secret, chain = CKD(self.secret, self.chain, n)
        mpk, mpk_compressed = get_pubkeys_from_secret(secret)
        return HighDefWallet(secret, chain, mpk, mpk_compressed)

    def branch_prime(self, n):
        return self.branch(n + BIP32_PRIME)

    @staticmethod
    def root(seed):
        args = bip32_init(seed)
        return HighDefWallet(*args)

class EllipticCurveKey:

    def __init__(self):
        self._secret = None
        self._private_key = None
        self._public_key = None

    def new_key_pair(self):
        secret = os.urandom(32)
        self.set_secret(secret)

    def set_secret(self, secret):
        self._secret = secret
        secret = string_to_number(secret)
        pkey = EC_KEY(secret)

        #sec = "L5KhaMvPYRW1ZoFmRjUtxxPypQ94m6BcDrPhqArhggdaTbbAFJEF"
        #pkey = obelisk.regenerate_key(sec)

        secexp = pkey.secret
        self._private_key = ecdsa.SigningKey.from_secret_exponent(
            secexp, curve=SECP256k1)
        self._public_key = self._private_key.get_verifying_key()

    def sign(self, digest):
        return self._private_key.sign_digest_deterministic(
            digest, hashfunc=hashlib.sha256,
            sigencode=ecdsa.util.sigencode_der)

    def verify(self, digest, signature):
        return self._public_key.verify_digest(
            signature, digest, sigdecode=ecdsa.util.sigdecode_der)

    @property
    def secret(self):
        return self._secret

    @property
    def public_key(self):
        return GetPubKey(self._public_key.pubkey, True)

    @property
    def key_id(self):
        return hash_160(self.public_key)

    @property
    def address(self):
        return hash_160_to_bc_address(self.key_id)

def output_script(address):
    addrtype, hash_160 = bc_address_to_hash_160(address)
    assert addrtype == chain.pubkey_version
    script = '\x76\xa9'                 # op_dup, op_hash_160
    script += '\x14'                    # push 0x14 bytes
    script += hash_160
    script += '\x88\xac'                # op_equalverify, op_checksig
    return script

def input_script(signature, public_key):
    script = op_push(len(signature)).decode("hex")
    script += signature
    script += op_push(len(public_key)).decode("hex")
    script += public_key
    return script

def sign_transaction_input(tx, input_index, key):
    sighash = generate_signature_hash(tx, input_index, key.address)
    # Add sighash::all to end of signature.
    signature = key.sign(sighash) + "\x01"
    public_key = key.public_key
    tx.inputs[input_index].script = input_script(signature, public_key)

def copy_tx(tx):
    # This is a hack.
    raw_tx = tx.serialize()
    return models.Transaction.deserialize(raw_tx)

def generate_signature_hash(parent_tx, input_index, prevout_address):
    script_code = output_script(prevout_address)
    tx = copy_tx(parent_tx)
    if input_index >= len(tx.inputs):
        return None
    for input in tx.inputs:
        input.script = ""
    tx.inputs[input_index].script = script_code
    raw_tx = tx.serialize() + "\x01\x00\x00\x00"
    return Hash(raw_tx)

def _derive_y_from_x(x, is_even):
    alpha = (pow(x, 3, _p)  + _a * x + _b) % _p
    beta = numbertheory.modular_sqrt(alpha, _p)
    if is_even == bool(beta & 1):
        return _p - beta
    return beta

def decompress_public_key(public_key):
    prefix = public_key[0]
    if prefix == "\x04":
        return public_key
    assert prefix == "\x02" or prefix == "\x03"
    x = int("0x" + public_key[1:].encode("hex"), 16)
    y = _derive_y_from_x(x, prefix == "\x02")
    key = '04' + \
          '%064x' % x + \
          '%064x' % y
    return key.decode("hex")

def diffie_hellman(e, Q):
    Q = decompress_public_key(Q)
    curve = SECP256k1
    public_key = ecdsa.VerifyingKey.from_string(Q[1:], curve=curve)
    point = public_key.pubkey.point
    #e_int = int("0x" + e.encode("hex"), 16)
    e_int = string_to_number(e)
    point = e_int * point
    # convert x point to bytes
    result = "\x03" + ("%x" % point.x()).decode("hex")
    assert len(result) == 33
    return result

def convert_point(Q):
    Q = decompress_public_key(Q)[1:]
    assert len(Q) == 64
    Q_x = Q[:32]
    Q_y = Q[32:]
    assert len(Q_x) == 32
    assert len(Q_y) == 32
    Q_x = string_to_number(Q_x)
    Q_y = string_to_number(Q_y)
    curve = curve_secp256k1
    return ecdsa.ellipticcurve.Point(curve, Q_x, Q_y, ec_order)

def point_add(Q, c):
    Q = convert_point(Q)
    c = string_to_number(c)
    return Q + c * generator_secp256k1

def get_point_pubkey(point, compressed=False):
    if compressed:
        if point.y() & 1:
            key = '03' + '%064x' % point.x()
        else:
            key = '02' + '%064x' % point.x()
    else:
        key = '04' + \
              '%064x' % point.x() + \
              '%064x' % point.y()
    return key.decode('hex')

def add_mod_n(d, c):
    assert len(d) == 32
    # Truncate prefix byte
    order = generator_secp256k1.order()
    d = string_to_number(d)
    c = string_to_number(c)
    return number_to_string((d + c) % order, order)


########NEW FILE########
__FILENAME__ = client
import struct
from decimal import Decimal

from twisted.internet import reactor

from zmqbase import ClientBase

import bitcoin
import models
import serialize
import error_code

def unpack_error(data):
    value = struct.unpack_from('<I', data, 0)[0]
    return error_code.error_code.name_from_id(value)

def pack_block_index(index):
    if type(index) == str:
        assert len(index) == 32
        return serialize.ser_hash(index)
    elif type(index) == int:
        return struct.pack('<I', index)
    else:
        raise ValueError("Unknown index type")

class ObeliskOfLightClient(ClientBase):
    valid_messages = ['fetch_block_header', 'fetch_history', 'subscribe',
        'fetch_last_height', 'fetch_transaction', 'fetch_spend',
        'fetch_transaction_index', 'fetch_block_transaction_hashes',
        'fetch_block_height', 'fetch_stealth', 'update', 'renew']

    subscribed = 0
    # Command implementations
    def renew_address(self, address, cb=None):
        address_version, address_hash = \
            bitcoin.bc_address_to_hash_160(address)
        # prepare parameters
        data = struct.pack('B', address_version)          # address version
        data += address_hash[::-1]               # address

        # run command
        self.send_command('address.renew', data, cb)

    def subscribe_address(self, address, notification_cb=None, cb=None):
        address_version, address_hash = \
            bitcoin.bc_address_to_hash_160(address)
        # prepare parameters
        data = struct.pack('B', address_version)          # address version
        data += address_hash[::-1]               # address

        # run command
        self.send_command('address.subscribe', data, cb)
        if notification_cb:
            if not address_hash in self._subscriptions['address']:
                self._subscriptions['address'][address_hash] = []
            if not notification_cb in self._subscriptions['address'][address_hash]:
                self._subscriptions['address'][address_hash].append(notification_cb)

    def unsubscribe_address(self, address, subscribed_cb, cb=None):
        address_version, address_hash = \
            bitcoin.bc_address_to_hash_160(address)

        if address_hash in self._subscriptions['address']:
            if subscribed_cb in self._subscriptions['address'][address_hash]:
               self._subscriptions['address'][address_hash].remove(subscribed_cb)
               if len(self._subscriptions['address'][address_hash]) == 0:
                   self._subscriptions['address'].pop(address_hash)
        if cb:
            cb(None, address)

    def fetch_block_header(self, index, cb):
        """Fetches the block header by height."""
        data = pack_block_index(index)
        self.send_command('blockchain.fetch_block_header', data, cb)

    def fetch_history(self, address, cb, from_height=0):
        """Fetches the output points, output values, corresponding input point
        spends and the block heights associated with a Bitcoin address.
        The returned history is a list of rows with the following fields:
     
            output
            output_height
            value
            spend
            spend_height

        If an output is unspent then the input spend hash will be equivalent
        to null_hash.

        Summing the list of values for unspent outpoints gives the balance
        for an address."""
        address_version, address_hash = \
            bitcoin.bc_address_to_hash_160(address)
        # prepare parameters
        data = struct.pack('B', address_version)    # address version
        data += address_hash[::-1]                  # address
        data += struct.pack('<I', from_height)      # from_height

        # run command
        self.send_command('address.fetch_history', data, cb)

    def fetch_last_height(self, cb):
        """Fetches the height of the last block in our blockchain."""
        self.send_command('blockchain.fetch_last_height', cb=cb)

    def fetch_transaction(self, tx_hash, cb):
        """Fetches a transaction by hash."""
        data = serialize.ser_hash(tx_hash)
        self.send_command('blockchain.fetch_transaction', data, cb)

    def fetch_spend(self, outpoint, cb):
        """Fetches a corresponding spend of an output."""
        data = outpoint.serialize()
        self.send_command('blockchain.fetch_spend', data, cb)

    def fetch_transaction_index(self, tx_hash, cb):
        """Fetch the block height that contains a transaction and its index
        within a block."""
        data = serialize.ser_hash(tx_hash)
        self.send_command('blockchain.fetch_transaction_index', data, cb)

    def fetch_block_transaction_hashes(self, index, cb):
        """Fetches list of transaction hashes in a block by block hash."""
        data = pack_block_index(index)
        self.send_command('blockchain.fetch_block_transaction_hashes',
            data, cb)

    def fetch_block_height(self, blk_hash, cb):
        """Fetches the height of a block given its hash."""
        data = serialize.ser_hash(blk_hash)
        self.send_command('blockchain.fetch_block_height', data, cb)

    def fetch_stealth(self, prefix, cb, from_height=0):
        """Fetch possible stealth results. These results can then be iterated
        to discover new payments belonging to a particular stealth address.
        This is for recipient privacy.
        
        The prefix is a special value that can be adjusted to provide
        greater precision at the expense of deniability.
        
        from_height is not guaranteed to only return results from that
        height, and may also include results from earlier blocks.
        It is provided as an optimisation. All results at and after
        from_height are guaranteed to be returned however."""
        number_bits, bitfield = prefix
        data = struct.pack('<BII', number_bits, bitfield, from_height)
        assert len(data) == 9
        self.send_command('blockchain.fetch_stealth', data, cb)

    # receive handlers
    def _on_fetch_block_header(self, data):
        error = unpack_error(data)
        assert len(data[4:]) == 80
        header = data[4:]
        return (error, header)

    def _on_fetch_history(self, data):
        error = unpack_error(data)
        # parse results
        rows = self.unpack_table("<32sIIQ32sII", data, 4)
        history = []
        for row in rows:
            o_hash, o_index, o_height, value, s_hash, s_index, s_height = row
            o_hash = o_hash[::-1]
            s_hash = s_hash[::-1]
            if s_index == 4294967295:
                s_hash = None
                s_index = None
                s_height = None
            history.append(
                (o_hash, o_index, o_height, value, s_hash, s_index, s_height))
        return (error, history)

    def _on_fetch_last_height(self, data):
        error = unpack_error(data)
        height = struct.unpack('<I', data[4:])[0]
        return (error, height)

    def _on_fetch_transaction(self, data):
        error = unpack_error(data)
        tx = data[4:]
        return (error, tx)

    def _on_fetch_spend(self, data):
        error = unpack_error(data)
        spend = serialize.deser_output_point(data[4:])
        return (error, spend)

    def _on_fetch_transaction_index(self, data):
        error = unpack_error(data)
        height, index = struct.unpack("<II", data[4:])
        return (error, height, index)

    def _on_fetch_block_transaction_hashes(self, data):
        error = unpack_error(data)
        rows = self.unpack_table("32s", data, 4)
        hashes = [row[0][::-1] for row in rows]
        return (error, hashes)

    def _on_fetch_block_height(self, data):
        error = unpack_error(data)
        height = struct.unpack('<I', data[4:])[0]
        return (error, height)

    def _on_fetch_stealth(self, data):
        error = unpack_error(data)
        raw_rows = self.unpack_table("<33sB20s32s", data, 4)
        rows = []
        for ephemkey, address_version, address_hash, tx_hash in raw_rows:
            address = bitcoin.hash_160_to_bc_address(
                address_hash[::-1], address_version)
            tx_hash = tx_hash[::-1]
            rows.append((ephemkey, address, tx_hash))
        return (error, rows)
        
    def _on_subscribe(self, data):
        self.subscribed += 1
        error = unpack_error(data)
        if error:
            print "Error subscribing"
        if not self.subscribed%1000:
            print "Subscribed ok", self.subscribed
        return (error, True)

    def _on_update(self, data):
        address_version = struct.unpack_from('B', data, 0)[0]
        address_hash = data[1:21][::-1]
        address = bitcoin.hash_160_to_bc_address(address_hash, address_version)

        height = struct.unpack_from('I', data, 21)[0]
        block_hash = data[25:57]
        tx = data[57:]

        if address_hash in self._subscriptions['address']:
            for update_cb in self._subscriptions['address'][address_hash]:
                update_cb(address_version, address_hash, height, block_hash, tx)

    def _on_renew(self, data):
        self.subscribed += 1
        error = unpack_error(data)
        if error:
            print "Error subscribing"
        if not self.subscribed%1000:
            print "Renew ok", self.subscribed
        return (error, True)


########NEW FILE########
__FILENAME__ = config
import os

class ChainParameters(object):
    def __init__(self, magic_bytes, pubkey_version, script_version, wif_version, protocol_port):
        self.magic_bytes = magic_bytes
        self.pubkey_version = pubkey_version
        self.script_version = script_version
        self.wif_version = wif_version
        self.protocol_port = protocol_port

testnet_chain = ChainParameters(0x0709110b, 0x6F, 0xC4, 0xEF, 18333)
mainnet_chain = ChainParameters(0xd9b4bef9, 0x00, 0x05, 0x80, 8333)

ENABLE_TESTNET = os.environ.get("ENABLE_TESTNET", False)

if ENABLE_TESTNET:
    chain = testnet_chain
else:
    chain = mainnet_chain

########NEW FILE########
__FILENAME__ = deserialize
# this code comes from ABE. it can probably be simplified
#
#

from bitcoin import public_key_to_bc_address, hash_160_to_bc_address, hash_encode, hash_160
from util import print_error
#import socket
import time
import struct

#
# Workalike python implementation of Bitcoin's CDataStream class.
#
import struct
import StringIO
import mmap

class SerializationError(Exception):
    """ Thrown when there's a problem deserializing or serializing """

class BCDataStream(object):
    def __init__(self):
        self.input = None
        self.read_cursor = 0

    def clear(self):
        self.input = None
        self.read_cursor = 0

    def write(self, bytes):  # Initialize with string of bytes
        if self.input is None:
            self.input = bytes
        else:
            self.input += bytes

    def map_file(self, file, start):  # Initialize with bytes from file
        self.input = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
        self.read_cursor = start

    def seek_file(self, position):
        self.read_cursor = position
        
    def close_file(self):
        self.input.close()

    def read_string(self):
        # Strings are encoded depending on length:
        # 0 to 252 :  1-byte-length followed by bytes (if any)
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

    def read_boolean(self): return self.read_bytes(1)[0] != chr(0)
    def read_int16(self): return self._read_num('<h')
    def read_uint16(self): return self._read_num('<H')
    def read_int32(self): return self._read_num('<i')
    def read_uint32(self): return self._read_num('<I')
    def read_int64(self): return self._read_num('<q')
    def read_uint64(self): return self._read_num('<Q')

    def write_boolean(self, val): return self.write(chr(1) if val else chr(0))
    def write_int16(self, val): return self._write_num('<h', val)
    def write_uint16(self, val): return self._write_num('<H', val)
    def write_int32(self, val): return self._write_num('<i', val)
    def write_uint32(self, val): return self._write_num('<I', val)
    def write_int64(self, val): return self._write_num('<q', val)
    def write_uint64(self, val): return self._write_num('<Q', val)

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

#
# enum-like type
# From the Python Cookbook, downloaded from http://code.activestate.com/recipes/67107/
#
import types, string, exceptions

class EnumException(exceptions.Exception):
    pass

class Enumeration:
    def __init__(self, name, enumList):
        self.__doc__ = name
        lookup = { }
        reverseLookup = { }
        i = 0
        uniqueNames = [ ]
        uniqueValues = [ ]
        for x in enumList:
            if type(x) == types.TupleType:
                x, i = x
            if type(x) != types.StringType:
                raise EnumException, "enum name is not a string: " + x
            if type(i) != types.IntType:
                raise EnumException, "enum value is not an integer: " + i
            if x in uniqueNames:
                raise EnumException, "enum name is not unique: " + x
            if i in uniqueValues:
                raise EnumException, "enum value is not unique for " + x
            uniqueNames.append(x)
            uniqueValues.append(i)
            lookup[x] = i
            reverseLookup[i] = x
            i = i + 1
        self.lookup = lookup
        self.reverseLookup = reverseLookup
    def __getattr__(self, attr):
        if not self.lookup.has_key(attr):
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
    d['pubkeys'] = pubkeys

    return d


def parse_TxOut(vds, i):
    d = {}
    d['value'] = vds.read_int64()
    scriptPubKey = vds.read_bytes(vds.read_compact_size())
    d['address'] = get_address_from_output_script(scriptPubKey)
    d['raw_output_script'] = scriptPubKey.encode('hex')
    d['index'] = i
    return d


def parse_Transaction(vds):
    d = {}
    start = vds.read_cursor
    d['version'] = vds.read_int32()
    n_vin = vds.read_compact_size()
    d['inputs'] = []
    for i in xrange(n_vin):
        d['inputs'].append(parse_TxIn(vds))
    n_vout = vds.read_compact_size()
    d['outputs'] = []
    for i in xrange(n_vout):
        d['outputs'].append(parse_TxOut(vds, i))
    d['lockTime'] = vds.read_uint32()
    return d

def parse_redeemScript(bytes):
    dec = [ x for x in script_GetOp(bytes.decode('hex')) ]

    # 2 of 2
    match = [ opcodes.OP_2, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_2, opcodes.OP_CHECKMULTISIG ]
    if match_decoded(dec, match):
        pubkeys = [ dec[1][1].encode('hex'), dec[2][1].encode('hex') ]
        return 2, pubkeys

    # 2 of 3
    match = [ opcodes.OP_2, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_3, opcodes.OP_CHECKMULTISIG ]
    if match_decoded(dec, match):
        pubkeys = [ dec[1][1].encode('hex'), dec[2][1].encode('hex'), dec[3][1].encode('hex') ]
        return 2, pubkeys



opcodes = Enumeration("Opcodes", [
    ("OP_0", 0), ("OP_PUSHDATA1",76), "OP_PUSHDATA2", "OP_PUSHDATA4", "OP_1NEGATE", "OP_RESERVED",
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
    ("OP_SINGLEBYTE_END", 0xF0),
    ("OP_DOUBLEBYTE_BEGIN", 0xF000),
    "OP_PUBKEY", "OP_PUBKEYHASH",
    ("OP_INVALIDOPCODE", 0xFFFF),
])


def script_GetOp(bytes):
    i = 0
    while i < len(bytes):
        vch = None
        opcode = ord(bytes[i])
        i += 1
        if opcode >= opcodes.OP_SINGLEBYTE_END:
            opcode <<= 8
            opcode |= ord(bytes[i])
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
            vch = bytes[i:i+nSize]
            i += nSize

        yield (opcode, vch, i)


def script_GetOpName(opcode):
    return (opcodes.whatis(opcode)).replace("OP_", "")


def decode_script(bytes):
    result = ''
    for (opcode, vch, i) in script_GetOp(bytes):
        if len(result) > 0: result += " "
        if opcode <= opcodes.OP_PUSHDATA4:
            result += "%d:"%(opcode,)
            result += short_hex(vch)
        else:
            result += script_GetOpName(opcode)
    return result


def match_decoded(decoded, to_match):
    if len(decoded) != len(to_match):
        return False;
    for i in range(len(decoded)):
        if to_match[i] == opcodes.OP_PUSHDATA4 and decoded[i][0] <= opcodes.OP_PUSHDATA4 and decoded[i][0]>0:
            continue  # Opcodes below OP_PUSHDATA4 all just push data onto stack, and are equivalent.
        if to_match[i] != decoded[i][0]:
            return False
    return True

def get_address_from_input_script(bytes):
    try:
        decoded = [ x for x in script_GetOp(bytes) ]
    except:
        # coinbase transactions raise an exception
        print_error("cannot find address in input script", bytes.encode('hex'))
        return [], [], "(None)"

    # non-generated TxIn transactions push a signature
    # (seventy-something bytes) and then their public key
    # (65 bytes) onto the stack:
    match = [ opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4 ]
    if match_decoded(decoded, match):
        return [decoded[1][1].encode('hex')], [decoded[0][1].encode('hex')], public_key_to_bc_address(decoded[1][1])

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

    print_error("cannot find address in input script", bytes.encode('hex'))
    return [], [], "(None)"



def get_address_from_output_script(bytes):
    decoded = [ x for x in script_GetOp(bytes) ]

    # The Genesis Block, self-payments, and pay-by-IP-address payments look like:
    # 65 BYTES:... CHECKSIG
    match = [ opcodes.OP_PUSHDATA4, opcodes.OP_CHECKSIG ]
    if match_decoded(decoded, match):
        return public_key_to_bc_address(decoded[0][1])

    # Pay-by-Bitcoin-address TxOuts look like:
    # DUP HASH160 20 BYTES:... EQUALVERIFY CHECKSIG
    match = [ opcodes.OP_DUP, opcodes.OP_HASH160, opcodes.OP_PUSHDATA4, opcodes.OP_EQUALVERIFY, opcodes.OP_CHECKSIG ]
    if match_decoded(decoded, match):
        return hash_160_to_bc_address(decoded[2][1])

    # p2sh
    match = [ opcodes.OP_HASH160, opcodes.OP_PUSHDATA4, opcodes.OP_EQUAL ]
    if match_decoded(decoded, match):
        return hash_160_to_bc_address(decoded[1][1],5)

    return "(None)"



########NEW FILE########
__FILENAME__ = error_code

class obelisk_exception(Exception):
    pass


class error_code(object):
    
    service_stopped = 1
    operation_failed = 2

    # blockchain errors
    not_found = 3
    duplicate = 4
    unspent_output = 5
    unsupported_payment_type = 6

    # network errors
    resolve_failed = 7
    network_unreachable = 8
    address_in_use = 9
    listen_failed = 10
    accept_failed = 11
    bad_stream = 12
    channel_timeout = 13

    # transaction pool
    blockchain_reorganized = 14
    pool_filled = 15

    # validate tx
    coinbase_transaction = 16
    is_not_standard = 17
    double_spend = 18
    input_not_found = 19

    # check_transaction()
    empty_transaction = 20
    output_value_overflow = 21
    invalid_coinbase_script_size = 22
    previous_output_null = 23

    # validate block
    previous_block_invalid = 24

    # check_block()
    size_limits = 25
    proof_of_work = 26
    futuristic_timestamp = 27
    first_not_coinbase = 28
    extra_coinbases = 29
    too_many_sigs = 30
    merkle_mismatch = 31

    # accept_block()
    incorrect_proof_of_work = 32
    timestamp_too_early = 33
    non_final_transaction = 34
    checkpoints_failed = 35
    old_version_block = 36
    coinbase_height_mismatch = 37

    # connect_block()
    duplicate_or_spent = 38
    validate_inputs_failed = 39
    fees_out_of_range = 40
    coinbase_too_large = 41

    @staticmethod
    def name_from_id(id):
        for key, value in error_code.__dict__.iteritems():
            if value == id:
                return key
        return None


########NEW FILE########
__FILENAME__ = models
import bitcoin
import struct
import serialize

class BlockHeader:

    def __init__(self):
        self.height = None

    @classmethod
    def deserialize(cls, raw):
        assert len(raw) == 80
        self = cls()
        self.version = struct.unpack('<I', raw[:4])[0]
        self.previous_block_hash = raw[4:36][::-1]
        assert len(self.previous_block_hash) == 32
        self.merkle = raw[36:68][::-1]
        assert len(self.merkle) == 32
        self.timestamp, self.bits, self.nonce = struct.unpack('<III', raw[68:])
        return self

    @property
    def hash(self):
        data = struct.pack('<I', self.version)
        data += self.previous_block_hash[::-1]
        data += self.merkle[::-1]
        data += struct.pack('<III', self.timestamp, self.bits, self.nonce)
        return bitcoin.Hash(data)[::-1]

    def __repr__(self):
        return '<BlockHeader %s>' % (self.hash.encode("hex"),)

class OutPoint(object):
    def __init__(self):
        self.hash = None
        self.index = None

    def is_null(self):
        return (len(self.hash) == 0) and (self.index == 0xffffffff)

    def __repr__(self):
        return "OutPoint(hash=%s, index=%i)" % (self.hash.encode("hex"), self.index)

    def serialize(self):
        return serialize.ser_output_point(self)

    @staticmethod
    def deserialize(bytes):
        return serialize.deser_output_point(bytes)

class TxOut(object):
    def __init__(self):
        self.value = None
        self.script = ""

    def __repr__(self):
        return "TxOut(value=%i.%08i script=%s)" % (self.value // 100000000, self.value % 100000000, self.script.encode("hex"))

    def serialize(self):
        return serialize.ser_txout(self)

    @staticmethod
    def deserialize(bytes):
        return serialize.deser_txout(bytes)


class TxIn(object):
    def __init__(self):
        self.previous_output = OutPoint()
        self.script = ""
        self.sequence = 0xffffffff

    def is_final(self):
        return self.sequence == 0xffffffff

    def __repr__(self):
        return "TxIn(previous_output=%s script=%s sequence=%i)" % (repr(self.previous_output), self.script.encode("hex"), self.sequence)

    def serialize(self):
        return serialize.ser_txin(self)

    @staticmethod
    def deserialize(bytes):
        return serialize.deser_txin(bytes)

class Transaction:
    def __init__(self):
        self.version = 1
        self.locktime = 0
        self.inputs = []
        self.outputs = []

    def is_final(self):
        for tin in self.vin:
            if not tin.is_final():
                return False
        return True
    def is_coinbase(self):
        return len(self.vin) == 1 and self.vin[0].prevout.is_null()

    def __repr__(self):
        return "Transaction(version=%i inputs=%s outputs=%s locktime=%i)" % (self.version, repr(self.inputs), repr(self.outputs), self.locktime)

    def serialize(self):
        return serialize.ser_tx(self)

    @staticmethod
    def deserialize(bytes):
        return serialize.deser_tx(bytes)


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
__FILENAME__ = serialize
__author__ = 'bobalot'

import struct
import io
import hashlib
from binascii import hexlify, unhexlify
from hashlib import sha256
import models

from error_code import error_code, obelisk_exception

# Py3 compatibility
import sys
bchr = chr
if sys.version > '3':
    bchr = lambda x: bytes([x])


def deser_uint32(f):
    if type(f) is not io.BytesIO:
        f = io.BytesIO(f)

    return struct.unpack(b"<I", f.read(4))[0]


def ser_uint32(u):
    rs = b""
    rs += struct.pack(b"<I", u & 0xFFFFFFFF)
    return rs


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

def deser_hash(f):
    return f.read(32)

def ser_hash(h):
    return h[::-1]

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

def deser_variable_uint(f):
    length = struct.unpack(b"<B", f.read(1))[0]
    if length < 0xfd:
        return length
    elif length == 0xfd:
        return struct.unpack(b"<H", f.read(2))[0]
    elif length == 0xfe:
        return struct.unpack(b"<I", f.read(4))[0]
    return struct.unpack(b"<Q", f.read(8))[0]

def deser_vector(f, c, arg1=None):
    count = deser_variable_uint(f)
    r = []
    for i in range(count):
        #if arg1 is not None:
        #    t = c(arg1)
        #else:
        #    t = c()

        if c is models.TxIn:
            t = deser_txin(f)
        elif c is models.TxOut:
            t = deser_txout(f)
        elif c is models.Transaction:
            t = deser_tx(f)
        else:
            raise NotImplementedError

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

        if type(i) is models.TxIn:
            r += ser_txin(i)
        elif type(i) is models.TxOut:
            r += ser_txout(i)
        elif type(i) is models.Transaction:
            r += ser_tx(i)
        else:
            raise NotImplementedError

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


def ser_destination(destination):
    if destination is None:
        serialized = ""
    else:
        try:
            serialized = unhexlify(destination)
        except TypeError:
            serialized = destination

    return serialized

def deser_txout(f):
    txout = models.TxOut()
    txout.value = struct.unpack(b"<q", f.read(8))[0]
    txout.script = deser_string(f)
    return txout

def ser_txout(txout):
    r = b""
    r += struct.pack(b"<q", txout.value)
    r += ser_string(txout.script)
    return r


def deser_output_point(f):
    if type(f) is not io.BytesIO:
        f = io.BytesIO(f)

    outpoint = models.OutPoint()
    outpoint.hash = deser_hash(f)[::-1]
    outpoint.index = deser_uint32(f.read(4))
    return outpoint


def ser_output_point(outpoint):
    r = b""
    r += ser_hash(outpoint.hash)
    r += ser_uint32(outpoint.index)
    return r


def deser_txin(f):
    if type(f) is not io.BytesIO:
        f = io.BytesIO(f)

    txin = models.TxIn()
    txin.previous_output = deser_output_point(f)
    txin.script = deser_string(f)
    txin.sequence = deser_uint32(f)
    return txin

def ser_txin(txin):
    r = b""
    r += ser_output_point(txin.previous_output)
    r += ser_string(txin.script)
    r += ser_uint32(txin.sequence)
    return r


def deser_block_header(f):
    if type(f) is not io.BytesIO:
        f = io.BytesIO(f)

    h = models.BlockHeader()

    h.version = deser_uint32(f.read(4))
    h.previous_block_hash = f.read(32)
    h.merkle = f.read(32)
    h.timestamp = deser_uint32(f.read(4))
    h.bits = deser_uint32(f.read(4))
    h.nonce = deser_uint32(f.read(4))

    return h


def ser_block_header(block_header):
    output = b""
    output += ser_uint32(block_header.version)
    output += block_header.previous_block_hash
    output += block_header.merkle
    output += ser_uint32(block_header.timestamp)
    output += ser_uint32(block_header.bits)
    output += ser_uint32(block_header.nonce)

    return output


def deser_tx(f):
    if type(f) is not io.BytesIO:
        f = io.BytesIO(f)

    tx = models.Transaction()
    tx.version = deser_uint32(f.read(4))
    tx.inputs = deser_vector(f, models.TxIn)
    tx.outputs = deser_vector(f, models.TxOut)
    tx.locktime = deser_uint32(f)
    return tx


def ser_tx(tx):
    r = b""
    r += ser_uint32(tx.version)
    r += ser_vector(tx.inputs)
    r += ser_vector(tx.outputs)
    r += ser_uint32(tx.locktime)
    return r


def deser_block(f):
    if type(f) is not io.BytesIO:
        f = io.BytesIO(f)

    blk = models.Block()

    blk.header = deser_block_header(f)
    blk.transactions = deser_vector(f, models.Transaction)
    return Block

def ser_block(blk):
    r = b""
    r += ser_block_header(blk.header)
    r += ser_vector(blk.transaction_list, models.Transaction)

    return r


    #tx.version = struct.unpack(b"<i", f.read(4))[0]
    #tx.vin = deser_vector(f, TxIn)
    #tx.vout = deser_vector(f, TxOut)
    #tx.nLockTime = struct.unpack(b"<I", f.read(4))[0]


def deser_history_row(f):

    if type(f) is not io.BytesIO:
        f = io.BytesIO(f)

    hr = models.history_row()


    hr.output_hash = f.read(32)
    hr.output_index = deser_uint32(f)
    hr.output_height = deser_uint32(f)

    hr.value = struct.unpack(b"<q", f.read(8))[0]
    hr.spend_hash = f.read(32)
    hr.spend_index = deser_uint32(f)
    hr.spend_height = deser_uint32(f)

    return hr

def ser_history_row(hr):
    r = b""

    r += hr.output_hash
    r += ser_uint32(hr.output_index)
    r += ser_uint32(hr.output_height)

    r += struct.pack(b"<q", hr.value & 0xFFFFFFFFFFFFFFFF)
    r += hr.spend_hash
    r += ser_uint32(hr.spend_index)
    r += ser_uint32(hr.spend_height)

    return hr


def deser_history_row_list(bytes):
    row_bytes = 88
    num_rows = len(bytes)/88

    assert(len(bytes) % 88 == 0)

    history_list = []

    for i in range(num_rows):
        history_list.append(deser_history_row(bytes[i*88, i*88+88]))

    return history_list


def dsha256(data):
    return sha256(sha256(data).digest()).digest()[::-1]


def checksum(data):
    return sha256(sha256(data).digest()).digest()[:4]


def hash_block_header(blk_head):
    if type(blk_head) is models.Block:
        blk_head = blk_head.header

    serial = ser_block_header(blk_head)

    return dsha256(serial)


def hash_transaction(tx):
    if type(tx) is not models.Transaction:
        return False

    serial = ser_tx(tx)

    return dsha256(serial)


def ser_data(command, data):
    # This requires command at the moment, for no reason.
    # Fix this.
    #from models import commands
    #if command not in commands:
    #    raise NotImplementedError

    if type(data) is int:
        return ser_uint32(data)
    elif type(data) is str:
        return data

    elif type(data) is tuple:
        r = b""

        for element in data:

            r += ser_data(command, element)

        return r

def deser_address_update(f):
    if type(f) is not io.BytesIO:
        f = io.BytesIO(f)

    update = models.address_update()
    update.address_version_byte = f.read(1)
    update.address_hash = f.read(20)

    update.height = deser_uint32(f)
    update.tx = deser_tx(f)

    return update


#command_data_type = \
#        {"blockchain.fetch_transaction",
#            "blockchain.fetch_last_height",
#            "blockchain.fetch_block_header",
#            "blockchain.fetch_block_transaction_hashes",
#            "transaction_pool.validate",
#            "protocol.broadcast_transaction",
#            "address.fetch_history"]


# deserialize and remove the ec here, this leaves all the other functions able to
# do deserialization on normal bitcoin serials.
def deser_data(command, data_bytes):
    if command == "blockchain.fetch_transaction":
        return data_bytes[:4], deser_tx(data_bytes[4:])

    elif command == "blockchain.fetch_last_height":
        return data_bytes[:4], deser_uint32(data_bytes[4:])

    elif command == "blockchain.fetch_block_header":
        return data_bytes[:4], deser_block_header(data_bytes[4:])

    elif command == "blockchain.fetch_block_transaction_hashes":
        hash_list = []

        print hexlify(data_bytes[4:])

        assert((len(data_bytes)-4) % 32 == 0)

        f = io.BytesIO(data_bytes)
        ec = f.read(4)

        for i in range(data_bytes/32):
            hash_list.append(f.read(32))

        return ec, hash_list

    elif command == "address.fetch_history":
        # history row is 88 bytes long. Assert there is nothing else
        assert((len(data_bytes)-4) % 88 == 0)

        history_list = []

        # use bytesio, as this will probably be a long message
        f = io.BytesIO(data_bytes)
        ec = f.read(4)

        for i in range(len(data_bytes) / 88):
            history_list.append(deser_history_row(f))

        return ec, history_list

    elif command == "address.subscribe":
        if len(data_bytes) == 4:
            ec = deser_uint32(data_bytes)

        return ec, None

    elif command == "address.update":
        # No error code in address.update
        f = io.BytesIO(data_bytes)

        ec = 0
        return ec, deser_address_update(f)








########NEW FILE########
__FILENAME__ = transaction
# Given a list of unspent outputs, return the optimal subset to satisfy
# a given amount (and return the change).

class OutputInfo(object):

    def __init__(self, point, value):
        self.point = point
        self.value = value

    def __repr__(self):
        return "OutputInfo(point=%s, value=%i)" % (self.point, self.value)

class SelectOutputsResult:

    def __init__(self):
        self._points = []
        self.change = 0

    def add_point(self, point):
        self._points.append(point)

    @property
    def points(self):
        return self._points

    def __repr__(self):
        return "SelectOutputsResult(points=%s, change=%i)" % (
            self._points, self.change)

def min_nonthrow(values, key):
    assert values
    if len(values) == 1:
        return values[0]
    return min(values, key=key)

def select_outputs(unspent, min_value):
    if not unspent:
        return None
    greaters = [output for output in unspent if not output.value < min_value]
    if greaters:
        return_value = lambda info: info.value
        min_greater = min_nonthrow(greaters, key=return_value)
        # Return result with single outpoint
        result = SelectOutputsResult()
        result.add_point(min_greater)
        result.change = min_greater.value - min_value
        return result
    # Not found in greaters. Try several lessers instead.
    # Rearrange them from biggest to smallest. We want to use the least
    # amount of inputs as possible.
    lessers = [output for output in unspent if output.value < min_value]
    # Descending sort
    lessers.sort(key=lambda output: output.value, reverse=True)
    accum = 0
    result = SelectOutputsResult()
    for output in lessers:
        result.add_point(output)
        accum += output.value
        if accum >= min_value:
            result.change = accum - min_value
            return result
    return None


########NEW FILE########
__FILENAME__ = util
import os, sys, re
import platform
import shutil
from datetime import datetime
from decimal import Decimal

is_verbose = True

btc = Decimal('1'+'0'*8)


def to_btc(value):
    return Decimal(value)/btc

def set_verbosity(b):
    global is_verbose
    is_verbose = b

def print_error(*args):
    if not is_verbose: return
    args = [str(item) for item in args]
    sys.stderr.write(" ".join(args) + "\n")
    sys.stderr.flush()

def print_msg(*args):
    # Stringify args
    args = [str(item) for item in args]
    sys.stdout.write(" ".join(args) + "\n")
    sys.stdout.flush()

def print_json(obj):
    import json
    s = json.dumps(obj,sort_keys = True, indent = 4)
    sys.stdout.write(s + "\n")
    sys.stdout.flush()


def check_windows_wallet_migration():
    if platform.release() != "XP":
        if os.path.exists(os.path.join(os.environ["LOCALAPPDATA"], "Electrum")):
            if os.path.exists(os.path.join(os.environ["APPDATA"], "Electrum")):
                print_msg("Two Electrum folders have been found, the default Electrum location for Windows has changed from %s to %s since Electrum 1.7, please check your wallets and fix the problem manually." % (os.environ["LOCALAPPDATA"], os.environ["APPDATA"]))
                sys.exit()
            try:
                shutil.move(os.path.join(os.environ["LOCALAPPDATA"], "Electrum"), os.path.join(os.environ["APPDATA"]))
                print_msg("Your wallet has been moved from %s to %s."% (os.environ["LOCALAPPDATA"], os.environ["APPDATA"]))
            except:
                print_msg("Failed to move your wallet.")
    

def user_dir():
    if "HOME" in os.environ:
        return os.path.join(os.environ["HOME"], ".electrum")
    elif "APPDATA" in os.environ:
        return os.path.join(os.environ["APPDATA"], "Electrum")
    elif "LOCALAPPDATA" in os.environ:
        return os.path.join(os.environ["LOCALAPPDATA"], "Electrum")
    else:
        #raise BaseException("No home directory found in environment variables.")
        return 

def appdata_dir():
    """Find the path to the application data directory; add an electrum folder and return path."""
    if platform.system() == "Windows":
        return os.path.join(os.environ["APPDATA"], "Electrum")
    elif platform.system() == "Linux":
        return os.path.join(sys.prefix, "share", "electrum")
    elif (platform.system() == "Darwin" or
          platform.system() == "DragonFly" or
	  platform.system() == "NetBSD"):
        return "/Library/Application Support/Electrum"
    else:
        raise Exception("Unknown system")


def get_resource_path(*args):
    return os.path.join(".", *args)


def local_data_dir():
    """Return path to the data folder."""
    assert sys.argv
    prefix_path = os.path.dirname(sys.argv[0])
    local_data = os.path.join(prefix_path, "data")
    return local_data


def format_satoshis(x, is_diff=False, num_zeros = 0, decimal_point = 8, whitespaces=False):
    from decimal import Decimal
    s = Decimal(x)
    sign, digits, exp = s.as_tuple()
    digits = map(str, digits)
    while len(digits) < decimal_point + 1:
        digits.insert(0,'0')
    digits.insert(-decimal_point,'.')
    s = ''.join(digits).rstrip('0')
    if sign: 
        s = '-' + s
    elif is_diff:
        s = "+" + s

    p = s.find('.')
    s += "0"*( 1 + num_zeros - ( len(s) - p ))
    if whitespaces:
        s += " "*( 1 + decimal_point - ( len(s) - p ))
        s = " "*( 13 - decimal_point - ( p )) + s 
    return s


# Takes a timestamp and returns a string with the approximation of the age
def age(from_date, since_date = None, target_tz=None, include_seconds=False):
    if from_date is None:
        return "Unknown"

    from_date = datetime.fromtimestamp(from_date)
    if since_date is None:
        since_date = datetime.now(target_tz)

    distance_in_time = since_date - from_date
    distance_in_seconds = int(round(abs(distance_in_time.days * 86400 + distance_in_time.seconds)))
    distance_in_minutes = int(round(distance_in_seconds/60))

    if distance_in_minutes <= 1:
        if include_seconds:
            for remainder in [5, 10, 20]:
                if distance_in_seconds < remainder:
                    return "less than %s seconds ago" % remainder
            if distance_in_seconds < 40:
                return "half a minute ago"
            elif distance_in_seconds < 60:
                return "less than a minute ago"
            else:
                return "1 minute ago"
        else:
            if distance_in_minutes == 0:
                return "less than a minute ago"
            else:
                return "1 minute ago"
    elif distance_in_minutes < 45:
        return "%s minutes ago" % distance_in_minutes
    elif distance_in_minutes < 90:
        return "about 1 hour ago"
    elif distance_in_minutes < 1440:
        return "about %d hours ago" % (round(distance_in_minutes / 60.0))
    elif distance_in_minutes < 2880:
        return "1 day ago"
    elif distance_in_minutes < 43220:
        return "%d days ago" % (round(distance_in_minutes / 1440))
    elif distance_in_minutes < 86400:
        return "about 1 month ago"
    elif distance_in_minutes < 525600:
        return "%d months ago" % (round(distance_in_minutes / 43200))
    elif distance_in_minutes < 1051200:
        return "about 1 year ago"
    else:
        return "over %d years ago" % (round(distance_in_minutes / 525600))




# URL decode
_ud = re.compile('%([0-9a-hA-H]{2})', re.MULTILINE)
urldecode = lambda x: _ud.sub(lambda m: chr(int(m.group(1), 16)), x)

def parse_url(url):
    o = url[8:].split('?')
    address = o[0]
    if len(o)>1:
        params = o[1].split('&')
    else:
        params = []

    amount = label = message = signature = identity = ''
    for p in params:
        k,v = p.split('=')
        uv = urldecode(v)
        if k == 'amount': amount = uv
        elif k == 'message': message = uv
        elif k == 'label': label = uv
        elif k == 'signature':
            identity, signature = uv.split(':')
            url = url.replace('&%s=%s'%(k,v),'')
        else: 
            print k,v

    return address, amount, label, message, signature, identity, url




########NEW FILE########
__FILENAME__ = zmqbase
import sys
import random
import struct
import logging

# Broken for ZMQ 4
#try:
#    from zmqproto import ZmqSocket
#except ImportError:
#    from zmq_fallback import ZmqSocket
from zmq_fallback import ZmqSocket

from obelisk.serialize import checksum

SNDMORE = 1

MAX_UINT32 = 4294967295

class ClientBase(object):

    valid_messages = []

    def __init__(self, address, block_address=None, tx_address=None, version=3):
        self._messages = []
        self._tx_messages = []
        self._block_messages = []
        self.zmq_version = version
        self.running = 1
        self._socket = self.setup(address)
        if block_address:
            self._socket_block = self.setup_block_sub(
                block_address, self.on_raw_block)
        if tx_address:
            self._socket_tx = self.setup_transaction_sub(
                tx_address, self.on_raw_transaction)
        self._subscriptions = {'address': {}}

    # Message arrived
    def on_raw_message(self, id, cmd, data):
        res = None
        short_cmd = cmd.split('.')[-1]
        if short_cmd in self.valid_messages:
            res = getattr(self, '_on_'+short_cmd)(data)
        else:
            logging.warning("Unknown Message " + cmd)
        if res:
            self.trigger_callbacks(id, *res)

    def on_raw_block(self, height, hash, header, tx_num, tx_hashes):
        print "block", height, len(tx_hashes)

    def on_raw_transaction(self, hash, transaction):
        print "tx", hash.encode('hex')

    # Base Api
    def send_command(self, command, data='', cb=None):
        tx_id = random.randint(0, MAX_UINT32)

        self.send(command, SNDMORE) # command
        self.send(struct.pack('I', tx_id), SNDMORE) # id (random)
        self.send(data, 0)    # data

        if cb:
            self._subscriptions[tx_id] = cb
        return tx_id

    def unsubscribe(self, cb):
        for sub_id in self._subscriptions.keys():
            if self._subscriptions[sub_id] == cb:
                self._subscriptions.pop(sub_id)

    def trigger_callbacks(self, tx_id, *args):
        if tx_id in self._subscriptions:
            self._subscriptions[tx_id](*args)
            del self._subscriptions[tx_id]

    # Low level zmq abstraction into obelisk frames
    def send(self, *args, **kwargs):
        self._socket.send(*args, **kwargs)

    def frame_received(self, frame, more):
        self._messages.append(frame)
        if not more:
            if not len(self._messages) == 3:
                print "Sequence with wrong messages", len(self._messages)
                print [m.encode("hex") for m in self._messages]
                self._messages = []
                return
            command, id, data = self._messages
            self._messages = []
            id = struct.unpack('I', id)[0]
            self.on_raw_message(id, command, data)

    def block_received(self, frame, more):
        self._block_messages.append(frame)
        if not more:
            nblocks = struct.unpack('Q', self._block_messages[3])[0]
            if not len(self._block_messages) == 4+nblocks:
                print "Sequence with wrong messages", len(self._block_messages), 4+nblocks
                self._block_messages = []
                return
            height, hash, header, tx_num = self._block_messages[:4]
            tx_hashes = self._block_messages[5:]
            if len(tx_num) >= 4:
                tx_num = struct.unpack_from('I', tx_num, 0 )[0]
            else:
                print "wrong tx_num length", len(tx_num), tx_num
                tx_num = struct.unpack('I', tx_num.zfill(4))[0]
            self._block_messages = []
            height = struct.unpack('I', height)[0]
            self._block_cb(height, hash, header, tx_num, tx_hashes)

    def transaction_received(self, frame, more):
        self._tx_messages.append(frame)
        if not more:
            if not len(self._tx_messages) == 2:
                print "Sequence with wrong messages", len(self._tx_messages)
                self._tx_messages = []
                return
            hash, transaction = self._tx_messages
            self._tx_messages = []
            self._tx_cb(hash, transaction)

    def setup(self, address):
        s = ZmqSocket(self.frame_received, self.zmq_version)
        s.connect(address)
        return s

    def setup_block_sub(self, address, cb):
        s = ZmqSocket(self.block_received, self.zmq_version, type='SUB')
        s.connect(address)
        self._block_cb = cb
        return s

    def setup_transaction_sub(self, address, cb):
        s = ZmqSocket(self.transaction_received, self.zmq_version, type='SUB')
        s.connect(address)
        self._tx_cb = cb
        return s

    # Low level packing
    def get_error(data):
        return struct.unpack_from('<I', data, 0)[0]

    def unpack_table(self, row_fmt, data, start=0):
        # get the number of rows
        row_size = struct.calcsize(row_fmt)
        nrows = (len(data)-start)/row_size

        # unpack
        rows = []
        for idx in xrange(nrows):
            offset = start+(idx*row_size)
            row = struct.unpack_from(row_fmt, data, offset)
            rows.append(row)
        return rows


########NEW FILE########
__FILENAME__ = zmq_fallback
import zmq
from twisted.internet import task
from twisted.internet import reactor

# Some versions of ZMQ have the error in a different module.
try:
    zmq.error
except AttributeError:
    zmq.error = zmq.core.error

class ZmqSocket:

    context = zmq.Context(1)

    def __init__(self, cb, version, type=zmq.DEALER):
        self._cb = cb
        self._type = type
        if self._type=='SUB':
            self._type = zmq.SUB

    def connect(self, address):
        self._socket = ZmqSocket.context.socket(self._type)
        self._socket.connect(address)
        if self._type==zmq.SUB:
            self._socket.setsockopt(zmq.SUBSCRIBE, '')
        l = task.LoopingCall(self.poll)
        l.start(0.1)

    def poll(self):
        try:
            data = self._socket.recv(flags=zmq.NOBLOCK)
        except zmq.error.ZMQError:
            return
        more = self._socket.getsockopt(zmq.RCVMORE)
        self._cb(data, more)

    def send(self, data, more=0):
        if more:
            more = zmq.SNDMORE
        self._socket.send(data, more)


########NEW FILE########
__FILENAME__ = cipher
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  Copyright (C) 2011 Yann GUIBET <yannguibet@gmail.com>
#  See LICENSE for details.

from pyelliptic.openssl import OpenSSL


class Cipher:
    """
    Symmetric encryption

        import pyelliptic
        iv = pyelliptic.Cipher.gen_IV('aes-256-cfb')
        ctx = pyelliptic.Cipher("secretkey", iv, 1, ciphername='aes-256-cfb')
        ciphertext = ctx.update('test1')
        ciphertext += ctx.update('test2')
        ciphertext += ctx.final()

        ctx2 = pyelliptic.Cipher("secretkey", iv, 0, ciphername='aes-256-cfb')
        print ctx2.ciphering(ciphertext)
    """
    def __init__(self, key, iv, do, ciphername='aes-256-cbc'):
        """
        do == 1 => Encrypt; do == 0 => Decrypt
        """
        self.cipher = OpenSSL.get_cipher(ciphername)
        self.ctx = OpenSSL.EVP_CIPHER_CTX_new()
        if do == 1 or do == 0:
            k = OpenSSL.malloc(key, len(key))
            IV = OpenSSL.malloc(iv, len(iv))
            OpenSSL.EVP_CipherInit_ex(
                self.ctx, self.cipher.get_pointer(), 0, k, IV, do)
        else:
            raise Exception("RTFM ...")

    @staticmethod
    def get_all_cipher():
        """
        static method, returns all ciphers available
        """
        return OpenSSL.cipher_algo.keys()

    @staticmethod
    def get_blocksize(ciphername):
        cipher = OpenSSL.get_cipher(ciphername)
        return cipher.get_blocksize()

    @staticmethod
    def gen_IV(ciphername):
        cipher = OpenSSL.get_cipher(ciphername)
        return OpenSSL.rand(cipher.get_blocksize())

    def update(self, input):
        i = OpenSSL.c_int(0)
        buffer = OpenSSL.malloc(b"", len(input) + self.cipher.get_blocksize())
        inp = OpenSSL.malloc(input, len(input))
        if OpenSSL.EVP_CipherUpdate(self.ctx, OpenSSL.byref(buffer),
                                    OpenSSL.byref(i), inp, len(input)) == 0:
            raise Exception("[OpenSSL] EVP_CipherUpdate FAIL ...")
        return buffer.raw[0:i.value]

    def final(self):
        i = OpenSSL.c_int(0)
        buffer = OpenSSL.malloc(b"", self.cipher.get_blocksize())
        if (OpenSSL.EVP_CipherFinal_ex(self.ctx, OpenSSL.byref(buffer),
                                       OpenSSL.byref(i))) == 0:
            raise Exception("[OpenSSL] EVP_CipherFinal_ex FAIL ...")
        return buffer.raw[0:i.value]

    def ciphering(self, input):
        """
        Do update and final in one method
        """
        buff = self.update(input)
        return buff + self.final()

    def __del__(self):
        OpenSSL.EVP_CIPHER_CTX_cleanup(self.ctx)
        OpenSSL.EVP_CIPHER_CTX_free(self.ctx)

########NEW FILE########
__FILENAME__ = ecc
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  Copyright (C) 2011 Yann GUIBET <yannguibet@gmail.com>
#  See LICENSE for details.

from hashlib import sha512
from pyelliptic.openssl import OpenSSL
from pyelliptic.cipher import Cipher
from pyelliptic.hash import hmac_sha256
from struct import pack, unpack


class ECC:
    """
    Asymmetric encryption with Elliptic Curve Cryptography (ECC)
    ECDH, ECDSA and ECIES

        import pyelliptic

        alice = pyelliptic.ECC() # default curve: sect283r1
        bob = pyelliptic.ECC(curve='sect571r1')

        ciphertext = alice.encrypt("Hello Bob", bob.get_pubkey())
        print bob.decrypt(ciphertext)

        signature = bob.sign("Hello Alice")
        # alice's job :
        print pyelliptic.ECC(
            pubkey=bob.get_pubkey()).verify(signature, "Hello Alice")

        # ERROR !!!
        try:
            key = alice.get_ecdh_key(bob.get_pubkey())
        except: print("For ECDH key agreement,\
                      the keys must be defined on the same curve !")

        alice = pyelliptic.ECC(curve='sect571r1')
        print alice.get_ecdh_key(bob.get_pubkey()).encode('hex')
        print bob.get_ecdh_key(alice.get_pubkey()).encode('hex')

    """
    def __init__(self, pubkey=None, privkey=None, pubkey_x=None,
                 pubkey_y=None, raw_privkey=None, curve='sect283r1'):
        """
        For a normal and High level use, specifie pubkey,
        privkey (if you need) and the curve
        """
        if type(curve) == str:
            self.curve = OpenSSL.get_curve(curve)
        else:
            self.curve = curve

        if pubkey_x is not None and pubkey_y is not None:
            self._set_keys(pubkey_x, pubkey_y, raw_privkey)
        elif pubkey is not None:
            curve, pubkey_x, pubkey_y, i = ECC._decode_pubkey(pubkey)
            if privkey is not None:
                curve2, raw_privkey, i = ECC._decode_privkey(privkey)
                if curve != curve2:
                    raise Exception("Bad ECC keys ...")
            self.curve = curve
            self._set_keys(pubkey_x, pubkey_y, raw_privkey)
        else:
            self.privkey, self.pubkey_x, self.pubkey_y = self._generate()

    def _set_keys(self, pubkey_x, pubkey_y, privkey):
        if self.raw_check_key(privkey, pubkey_x, pubkey_y) < 0:
            self.pubkey_x = None
            self.pubkey_y = None
            self.privkey = None
            raise Exception("Bad ECC keys ...")
        else:
            self.pubkey_x = pubkey_x
            self.pubkey_y = pubkey_y
            self.privkey = privkey

    @staticmethod
    def get_curves():
        """
        static method, returns the list of all the curves available
        """
        return OpenSSL.curves.keys()

    def get_curve(self):
        return OpenSSL.get_curve_by_id(self.curve)

    def get_curve_id(self):
        return self.curve

    def get_pubkey(self):
        """
        High level function which returns :
        curve(2) + len_of_pubkeyX(2) + pubkeyX + len_of_pubkeyY + pubkeyY
        """
        return b''.join((pack('!H', self.curve),
                         pack('!H', len(self.pubkey_x)),
                         self.pubkey_x,
                         pack('!H', len(self.pubkey_y)),
                         self.pubkey_y
                         ))

    def get_privkey(self):
        """
        High level function which returns
        curve(2) + len_of_privkey(2) + privkey
        """
        return b''.join((pack('!H', self.curve),
                         pack('!H', len(self.privkey)),
                         self.privkey
                         ))

    @staticmethod
    def _decode_pubkey(pubkey):
        i = 0
        curve = unpack('!H', pubkey[i:i + 2])[0]
        i += 2
        tmplen = unpack('!H', pubkey[i:i + 2])[0]
        i += 2
        pubkey_x = pubkey[i:i + tmplen]
        i += tmplen
        tmplen = unpack('!H', pubkey[i:i + 2])[0]
        i += 2
        pubkey_y = pubkey[i:i + tmplen]
        i += tmplen
        return curve, pubkey_x, pubkey_y, i

    @staticmethod
    def _decode_privkey(privkey):
        i = 0
        curve = unpack('!H', privkey[i:i + 2])[0]
        i += 2
        tmplen = unpack('!H', privkey[i:i + 2])[0]
        i += 2
        privkey = privkey[i:i + tmplen]
        i += tmplen
        return curve, privkey, i

    def _generate(self):
        try:
            pub_key_x = OpenSSL.BN_new()
            pub_key_y = OpenSSL.BN_new()

            key = OpenSSL.EC_KEY_new_by_curve_name(self.curve)
            if key == 0:
                raise Exception("[OpenSSL] EC_KEY_new_by_curve_name FAIL ...")
            if (OpenSSL.EC_KEY_generate_key(key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_generate_key FAIL ...")
            if (OpenSSL.EC_KEY_check_key(key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_check_key FAIL ...")
            priv_key = OpenSSL.EC_KEY_get0_private_key(key)

            group = OpenSSL.EC_KEY_get0_group(key)
            pub_key = OpenSSL.EC_KEY_get0_public_key(key)

            if (OpenSSL.EC_POINT_get_affine_coordinates_GFp(group, pub_key,
                                                            pub_key_x,
                                                            pub_key_y, 0
                                                            )) == 0:
                raise Exception(
                    "[OpenSSL] EC_POINT_get_affine_coordinates_GFp FAIL ...")

            privkey = OpenSSL.malloc(0, OpenSSL.BN_num_bytes(priv_key))
            pubkeyx = OpenSSL.malloc(0, OpenSSL.BN_num_bytes(pub_key_x))
            pubkeyy = OpenSSL.malloc(0, OpenSSL.BN_num_bytes(pub_key_y))
            OpenSSL.BN_bn2bin(priv_key, privkey)
            privkey = privkey.raw
            OpenSSL.BN_bn2bin(pub_key_x, pubkeyx)
            pubkeyx = pubkeyx.raw
            OpenSSL.BN_bn2bin(pub_key_y, pubkeyy)
            pubkeyy = pubkeyy.raw
            self.raw_check_key(privkey, pubkeyx, pubkeyy)

            return privkey, pubkeyx, pubkeyy

        finally:
            OpenSSL.EC_KEY_free(key)
            OpenSSL.BN_free(pub_key_x)
            OpenSSL.BN_free(pub_key_y)

    def get_ecdh_key(self, pubkey):
        """
        High level function. Compute public key with the local private key
        and returns a 512bits shared key
        """
        curve, pubkey_x, pubkey_y, i = ECC._decode_pubkey(pubkey)
        if curve != self.curve:
            raise Exception("ECC keys must be from the same curve !")
        return sha512(self.raw_get_ecdh_key(pubkey_x, pubkey_y)).digest()

    def raw_get_ecdh_key(self, pubkey_x, pubkey_y):
        try:
            ecdh_keybuffer = OpenSSL.malloc(0, 32)

            other_key = OpenSSL.EC_KEY_new_by_curve_name(self.curve)
            if other_key == 0:
                raise Exception("[OpenSSL] EC_KEY_new_by_curve_name FAIL ...")

            other_pub_key_x = OpenSSL.BN_bin2bn(pubkey_x, len(pubkey_x), 0)
            other_pub_key_y = OpenSSL.BN_bin2bn(pubkey_y, len(pubkey_y), 0)

            other_group = OpenSSL.EC_KEY_get0_group(other_key)
            other_pub_key = OpenSSL.EC_POINT_new(other_group)

            if (OpenSSL.EC_POINT_set_affine_coordinates_GFp(other_group,
                                                            other_pub_key,
                                                            other_pub_key_x,
                                                            other_pub_key_y,
                                                            0)) == 0:
                raise Exception(
                    "[OpenSSL] EC_POINT_set_affine_coordinates_GFp FAIL ...")
            if (OpenSSL.EC_KEY_set_public_key(other_key, other_pub_key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_set_public_key FAIL ...")
            if (OpenSSL.EC_KEY_check_key(other_key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_check_key FAIL ...")

            own_key = OpenSSL.EC_KEY_new_by_curve_name(self.curve)
            if own_key == 0:
                raise Exception("[OpenSSL] EC_KEY_new_by_curve_name FAIL ...")
            own_priv_key = OpenSSL.BN_bin2bn(
                self.privkey, len(self.privkey), 0)

            if (OpenSSL.EC_KEY_set_private_key(own_key, own_priv_key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_set_private_key FAIL ...")

            OpenSSL.ECDH_set_method(own_key, OpenSSL.ECDH_OpenSSL())
            ecdh_keylen = OpenSSL.ECDH_compute_key(
                ecdh_keybuffer, 32, other_pub_key, own_key, 0)

            if ecdh_keylen != 32:
                raise Exception("[OpenSSL] ECDH keylen FAIL ...")

            return ecdh_keybuffer.raw

        finally:
            OpenSSL.EC_KEY_free(other_key)
            OpenSSL.BN_free(other_pub_key_x)
            OpenSSL.BN_free(other_pub_key_y)
            OpenSSL.EC_POINT_free(other_pub_key)
            OpenSSL.EC_KEY_free(own_key)
            OpenSSL.BN_free(own_priv_key)

    def check_key(self, privkey, pubkey):
        """
        Check the public key and the private key.
        The private key is optional (replace by None)
        """
        curve, pubkey_x, pubkey_y, i = ECC._decode_pubkey(pubkey)
        if privkey is None:
            raw_privkey = None
            curve2 = curve
        else:
            curve2, raw_privkey, i = ECC._decode_privkey(privkey)
        if curve != curve2:
            raise Exception("Bad public and private key")
        return self.raw_check_key(raw_privkey, pubkey_x, pubkey_y, curve)

    def raw_check_key(self, privkey, pubkey_x, pubkey_y, curve=None):
        if curve is None:
            curve = self.curve
        elif type(curve) == str:
            curve = OpenSSL.get_curve(curve)
        else:
            curve = curve
        try:
            key = OpenSSL.EC_KEY_new_by_curve_name(curve)
            if key == 0:
                raise Exception("[OpenSSL] EC_KEY_new_by_curve_name FAIL ...")
            if privkey is not None:
                priv_key = OpenSSL.BN_bin2bn(privkey, len(privkey), 0)
            pub_key_x = OpenSSL.BN_bin2bn(pubkey_x, len(pubkey_x), 0)
            pub_key_y = OpenSSL.BN_bin2bn(pubkey_y, len(pubkey_y), 0)

            if privkey is not None:
                if (OpenSSL.EC_KEY_set_private_key(key, priv_key)) == 0:
                    raise Exception(
                        "[OpenSSL] EC_KEY_set_private_key FAIL ...")

            group = OpenSSL.EC_KEY_get0_group(key)
            pub_key = OpenSSL.EC_POINT_new(group)

            if (OpenSSL.EC_POINT_set_affine_coordinates_GFp(group, pub_key,
                                                            pub_key_x,
                                                            pub_key_y,
                                                            0)) == 0:
                raise Exception(
                    "[OpenSSL] EC_POINT_set_affine_coordinates_GFp FAIL ...")
            if (OpenSSL.EC_KEY_set_public_key(key, pub_key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_set_public_key FAIL ...")
            if (OpenSSL.EC_KEY_check_key(key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_check_key FAIL ...")
            return 0

        finally:
            OpenSSL.EC_KEY_free(key)
            OpenSSL.BN_free(pub_key_x)
            OpenSSL.BN_free(pub_key_y)
            OpenSSL.EC_POINT_free(pub_key)
            if privkey is not None:
                OpenSSL.BN_free(priv_key)

    def sign(self, inputb):
        """
        Sign the input with ECDSA method and returns the signature
        """
        try:
            size = len(inputb)
            buff = OpenSSL.malloc(inputb, size)
            digest = OpenSSL.malloc(0, 64)
            md_ctx = OpenSSL.EVP_MD_CTX_create()
            dgst_len = OpenSSL.pointer(OpenSSL.c_int(0))
            siglen = OpenSSL.pointer(OpenSSL.c_int(0))
            sig = OpenSSL.malloc(0, 151)

            key = OpenSSL.EC_KEY_new_by_curve_name(self.curve)
            if key == 0:
                raise Exception("[OpenSSL] EC_KEY_new_by_curve_name FAIL ...")

            priv_key = OpenSSL.BN_bin2bn(self.privkey, len(self.privkey), 0)
            pub_key_x = OpenSSL.BN_bin2bn(self.pubkey_x, len(self.pubkey_x), 0)
            pub_key_y = OpenSSL.BN_bin2bn(self.pubkey_y, len(self.pubkey_y), 0)

            if (OpenSSL.EC_KEY_set_private_key(key, priv_key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_set_private_key FAIL ...")

            group = OpenSSL.EC_KEY_get0_group(key)
            pub_key = OpenSSL.EC_POINT_new(group)

            if (OpenSSL.EC_POINT_set_affine_coordinates_GFp(group, pub_key,
                                                            pub_key_x,
                                                            pub_key_y,
                                                            0)) == 0:
                raise Exception(
                    "[OpenSSL] EC_POINT_set_affine_coordinates_GFp FAIL ...")
            if (OpenSSL.EC_KEY_set_public_key(key, pub_key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_set_public_key FAIL ...")
            if (OpenSSL.EC_KEY_check_key(key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_check_key FAIL ...")

            OpenSSL.EVP_MD_CTX_init(md_ctx)
            OpenSSL.EVP_DigestInit(md_ctx, OpenSSL.EVP_ecdsa())

            if (OpenSSL.EVP_DigestUpdate(md_ctx, buff, size)) == 0:
                raise Exception("[OpenSSL] EVP_DigestUpdate FAIL ...")
            OpenSSL.EVP_DigestFinal(md_ctx, digest, dgst_len)
            OpenSSL.ECDSA_sign(0, digest, dgst_len.contents, sig, siglen, key)
            if (OpenSSL.ECDSA_verify(0, digest, dgst_len.contents, sig,
                                     siglen.contents, key)) != 1:
                raise Exception("[OpenSSL] ECDSA_verify FAIL ...")

            return sig.raw[0:siglen.contents.value]

        finally:
            OpenSSL.EC_KEY_free(key)
            OpenSSL.BN_free(pub_key_x)
            OpenSSL.BN_free(pub_key_y)
            OpenSSL.BN_free(priv_key)
            OpenSSL.EC_POINT_free(pub_key)
            OpenSSL.EVP_MD_CTX_destroy(md_ctx)

    def verify(self, sig, inputb):
        """
        Verify the signature with the input and the local public key.
        Returns a boolean
        """
        try:
            bsig = OpenSSL.malloc(sig, len(sig))
            binputb = OpenSSL.malloc(inputb, len(inputb))
            digest = OpenSSL.malloc(0, 64)
            dgst_len = OpenSSL.pointer(OpenSSL.c_int(0))
            md_ctx = OpenSSL.EVP_MD_CTX_create()

            key = OpenSSL.EC_KEY_new_by_curve_name(self.curve)

            if key == 0:
                raise Exception("[OpenSSL] EC_KEY_new_by_curve_name FAIL ...")

            pub_key_x = OpenSSL.BN_bin2bn(self.pubkey_x, len(self.pubkey_x), 0)
            pub_key_y = OpenSSL.BN_bin2bn(self.pubkey_y, len(self.pubkey_y), 0)
            group = OpenSSL.EC_KEY_get0_group(key)
            pub_key = OpenSSL.EC_POINT_new(group)

            if (OpenSSL.EC_POINT_set_affine_coordinates_GFp(group, pub_key,
                                                            pub_key_x,
                                                            pub_key_y,
                                                            0)) == 0:
                raise Exception(
                    "[OpenSSL] EC_POINT_set_affine_coordinates_GFp FAIL ...")
            if (OpenSSL.EC_KEY_set_public_key(key, pub_key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_set_public_key FAIL ...")
            if (OpenSSL.EC_KEY_check_key(key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_check_key FAIL ...")

            OpenSSL.EVP_MD_CTX_init(md_ctx)
            OpenSSL.EVP_DigestInit(md_ctx, OpenSSL.EVP_ecdsa())
            if (OpenSSL.EVP_DigestUpdate(md_ctx, binputb, len(inputb))) == 0:
                raise Exception("[OpenSSL] EVP_DigestUpdate FAIL ...")

            OpenSSL.EVP_DigestFinal(md_ctx, digest, dgst_len)
            ret = OpenSSL.ECDSA_verify(
                0, digest, dgst_len.contents, bsig, len(sig), key)

            if ret == -1:
                return False  # Fail to Check
            else:
                if ret == 0:
                    return False  # Bad signature !
                else:
                    return True  # Good
            return False

        finally:
            OpenSSL.EC_KEY_free(key)
            OpenSSL.BN_free(pub_key_x)
            OpenSSL.BN_free(pub_key_y)
            OpenSSL.EC_POINT_free(pub_key)
            OpenSSL.EVP_MD_CTX_destroy(md_ctx)

    @staticmethod
    def encrypt(data, pubkey, ephemcurve=None, ciphername='aes-256-cbc'):
        """
        Encrypt data with ECIES method using the public key of the recipient.
        """
        curve, pubkey_x, pubkey_y, i = ECC._decode_pubkey(pubkey)
        return ECC.raw_encrypt(data, pubkey_x, pubkey_y, curve=curve,
                               ephemcurve=ephemcurve, ciphername=ciphername)

    @staticmethod
    def raw_encrypt(data, pubkey_x, pubkey_y, curve='sect283r1',
                    ephemcurve=None, ciphername='aes-256-cbc'):
        if ephemcurve is None:
            ephemcurve = curve
        ephem = ECC(curve=ephemcurve)
        key = sha512(ephem.raw_get_ecdh_key(pubkey_x, pubkey_y)).digest()
        key_e, key_m = key[:32], key[32:]
        pubkey = ephem.get_pubkey()
        iv = OpenSSL.rand(OpenSSL.get_cipher(ciphername).get_blocksize())
        ctx = Cipher(key_e, iv, 1, ciphername)
        ciphertext = ctx.ciphering(data)
        mac = hmac_sha256(key_m, ciphertext)
        return iv + pubkey + ciphertext + mac

    def decrypt(self, data, ciphername='aes-256-cbc'):
        """
        Decrypt data with ECIES method using the local private key
        """
        blocksize = OpenSSL.get_cipher(ciphername).get_blocksize()
        iv = data[:blocksize]
        i = blocksize
        curve, pubkey_x, pubkey_y, i2 = ECC._decode_pubkey(data[i:])
        i += i2
        ciphertext = data[i:len(data)-32]
        i += len(ciphertext)
        mac = data[i:]
        key = sha512(self.raw_get_ecdh_key(pubkey_x, pubkey_y)).digest()
        key_e, key_m = key[:32], key[32:]
        if hmac_sha256(key_m, ciphertext) != mac:
            raise RuntimeError("Fail to verify data")
        ctx = Cipher(key_e, iv, 0, ciphername)
        return ctx.ciphering(ciphertext)

########NEW FILE########
__FILENAME__ = hash
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  Copyright (C) 2011 Yann GUIBET <yannguibet@gmail.com>
#  See LICENSE for details.

from pyelliptic.openssl import OpenSSL


def hmac_sha256(k, m):
    """
    Compute the key and the message with HMAC SHA5256
    """
    key = OpenSSL.malloc(k, len(k))
    d = OpenSSL.malloc(m, len(m))
    md = OpenSSL.malloc(0, 32)
    i = OpenSSL.pointer(OpenSSL.c_int(0))
    OpenSSL.HMAC(OpenSSL.EVP_sha256(), key, len(k), d, len(m), md, i)
    return md.raw


def hmac_sha512(k, m):
    """
    Compute the key and the message with HMAC SHA512
    """
    key = OpenSSL.malloc(k, len(k))
    d = OpenSSL.malloc(m, len(m))
    md = OpenSSL.malloc(0, 64)
    i = OpenSSL.pointer(OpenSSL.c_int(0))
    OpenSSL.HMAC(OpenSSL.EVP_sha512(), key, len(k), d, len(m), md, i)
    return md.raw


def pbkdf2(password, salt=None, i=10000, keylen=64):
    if salt is None:
        salt = OpenSSL.rand(8)
    p_password = OpenSSL.malloc(password, len(password))
    p_salt = OpenSSL.malloc(salt, len(salt))
    output = OpenSSL.malloc(0, keylen)
    OpenSSL.PKCS5_PBKDF2_HMAC(p_password, len(password), p_salt,
                              len(p_salt), i, OpenSSL.EVP_sha256(),
                              keylen, output)
    return salt, output.raw

########NEW FILE########
__FILENAME__ = openssl
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  Copyright (C) 2011 Yann GUIBET <yannguibet@gmail.com>
#  See LICENSE for details.

import sys
import ctypes
import ctypes.util

OpenSSL = None


class CipherName:
    def __init__(self, name, pointer, blocksize):
        self._name = name
        self._pointer = pointer
        self._blocksize = blocksize

    def __str__(self):
        return "Cipher : " + self._name + " | Blocksize : " + str(self._blocksize) + " | Fonction pointer : " + str(self._pointer)

    def get_pointer(self):
        return self._pointer()

    def get_name(self):
        return self._name

    def get_blocksize(self):
        return self._blocksize


class _OpenSSL:
    """
    Wrapper for OpenSSL using ctypes
    """
    def __init__(self, library):
        """
        Build the wrapper
        """
        self._lib = ctypes.CDLL(library)

        self.pointer = ctypes.pointer
        self.c_int = ctypes.c_int
        self.byref = ctypes.byref
        self.create_string_buffer = ctypes.create_string_buffer

        self.BN_new = self._lib.BN_new
        self.BN_new.restype = ctypes.c_void_p
        self.BN_new.argtypes = []

        self.BN_free = self._lib.BN_free
        self.BN_free.restype = None
        self.BN_free.argtypes = [ctypes.c_void_p]

        self.BN_num_bits = self._lib.BN_num_bits
        self.BN_num_bits.restype = ctypes.c_int
        self.BN_num_bits.argtypes = [ctypes.c_void_p]

        self.BN_bn2bin = self._lib.BN_bn2bin
        self.BN_bn2bin.restype = ctypes.c_int
        self.BN_bn2bin.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

        self.BN_bin2bn = self._lib.BN_bin2bn
        self.BN_bin2bn.restype = ctypes.c_void_p
        self.BN_bin2bn.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                   ctypes.c_void_p]

        self.EC_KEY_free = self._lib.EC_KEY_free
        self.EC_KEY_free.restype = None
        self.EC_KEY_free.argtypes = [ctypes.c_void_p]

        self.EC_KEY_new_by_curve_name = self._lib.EC_KEY_new_by_curve_name
        self.EC_KEY_new_by_curve_name.restype = ctypes.c_void_p
        self.EC_KEY_new_by_curve_name.argtypes = [ctypes.c_int]

        self.EC_KEY_generate_key = self._lib.EC_KEY_generate_key
        self.EC_KEY_generate_key.restype = ctypes.c_int
        self.EC_KEY_generate_key.argtypes = [ctypes.c_void_p]

        self.EC_KEY_check_key = self._lib.EC_KEY_check_key
        self.EC_KEY_check_key.restype = ctypes.c_int
        self.EC_KEY_check_key.argtypes = [ctypes.c_void_p]

        self.EC_KEY_get0_private_key = self._lib.EC_KEY_get0_private_key
        self.EC_KEY_get0_private_key.restype = ctypes.c_void_p
        self.EC_KEY_get0_private_key.argtypes = [ctypes.c_void_p]

        self.EC_KEY_get0_public_key = self._lib.EC_KEY_get0_public_key
        self.EC_KEY_get0_public_key.restype = ctypes.c_void_p
        self.EC_KEY_get0_public_key.argtypes = [ctypes.c_void_p]

        self.EC_KEY_get0_group = self._lib.EC_KEY_get0_group
        self.EC_KEY_get0_group.restype = ctypes.c_void_p
        self.EC_KEY_get0_group.argtypes = [ctypes.c_void_p]

        self.EC_POINT_get_affine_coordinates_GFp = self._lib.EC_POINT_get_affine_coordinates_GFp
        self.EC_POINT_get_affine_coordinates_GFp.restype = ctypes.c_int
        self.EC_POINT_get_affine_coordinates_GFp.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]

        self.EC_KEY_set_private_key = self._lib.EC_KEY_set_private_key
        self.EC_KEY_set_private_key.restype = ctypes.c_int
        self.EC_KEY_set_private_key.argtypes = [ctypes.c_void_p,
                                                ctypes.c_void_p]

        self.EC_KEY_set_public_key = self._lib.EC_KEY_set_public_key
        self.EC_KEY_set_public_key.restype = ctypes.c_int
        self.EC_KEY_set_public_key.argtypes = [ctypes.c_void_p,
                                               ctypes.c_void_p]

        self.EC_KEY_set_group = self._lib.EC_KEY_set_group
        self.EC_KEY_set_group.restype = ctypes.c_int
        self.EC_KEY_set_group.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

        self.EC_POINT_set_affine_coordinates_GFp = self._lib.EC_POINT_set_affine_coordinates_GFp
        self.EC_POINT_set_affine_coordinates_GFp.restype = ctypes.c_int
        self.EC_POINT_set_affine_coordinates_GFp.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]

        self.EC_POINT_new = self._lib.EC_POINT_new
        self.EC_POINT_new.restype = ctypes.c_void_p
        self.EC_POINT_new.argtypes = [ctypes.c_void_p]

        self.EC_POINT_free = self._lib.EC_POINT_free
        self.EC_POINT_free.restype = None
        self.EC_POINT_free.argtypes = [ctypes.c_void_p]

        self.EC_KEY_set_private_key = self._lib.EC_KEY_set_private_key
        self.EC_KEY_set_private_key.restype = ctypes.c_int
        self.EC_KEY_set_private_key.argtypes = [ctypes.c_void_p,
                                                ctypes.c_void_p]

        self.ECDH_OpenSSL = self._lib.ECDH_OpenSSL
        self._lib.ECDH_OpenSSL.restype = ctypes.c_void_p
        self._lib.ECDH_OpenSSL.argtypes = []

        self.ECDH_set_method = self._lib.ECDH_set_method
        self._lib.ECDH_set_method.restype = ctypes.c_int
        self._lib.ECDH_set_method.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

        self.ECDH_compute_key = self._lib.ECDH_compute_key
        self.ECDH_compute_key.restype = ctypes.c_int
        self.ECDH_compute_key.argtypes = [ctypes.c_void_p,
                                          ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]

        self.EVP_CipherInit_ex = self._lib.EVP_CipherInit_ex
        self.EVP_CipherInit_ex.restype = ctypes.c_int
        self.EVP_CipherInit_ex.argtypes = [ctypes.c_void_p,
                                           ctypes.c_void_p, ctypes.c_void_p]

        self.EVP_CIPHER_CTX_new = self._lib.EVP_CIPHER_CTX_new
        self.EVP_CIPHER_CTX_new.restype = ctypes.c_void_p
        self.EVP_CIPHER_CTX_new.argtypes = []

        # Cipher
        self.EVP_aes_128_cfb128 = self._lib.EVP_aes_128_cfb128
        self.EVP_aes_128_cfb128.restype = ctypes.c_void_p
        self.EVP_aes_128_cfb128.argtypes = []

        self.EVP_aes_256_cfb128 = self._lib.EVP_aes_256_cfb128
        self.EVP_aes_256_cfb128.restype = ctypes.c_void_p
        self.EVP_aes_256_cfb128.argtypes = []

        self.EVP_aes_128_cbc = self._lib.EVP_aes_128_cbc
        self.EVP_aes_128_cbc.restype = ctypes.c_void_p
        self.EVP_aes_128_cbc.argtypes = []

        self.EVP_aes_256_cbc = self._lib.EVP_aes_256_cbc
        self.EVP_aes_256_cbc.restype = ctypes.c_void_p
        self.EVP_aes_256_cbc.argtypes = []

        self.EVP_aes_128_ctr = self._lib.EVP_aes_128_ctr
        self.EVP_aes_128_ctr.restype = ctypes.c_void_p
        self.EVP_aes_128_ctr.argtypes = []

        self.EVP_aes_256_ctr = self._lib.EVP_aes_256_ctr
        self.EVP_aes_256_ctr.restype = ctypes.c_void_p
        self.EVP_aes_256_ctr.argtypes = []

        self.EVP_aes_128_ofb = self._lib.EVP_aes_128_ofb
        self.EVP_aes_128_ofb.restype = ctypes.c_void_p
        self.EVP_aes_128_ofb.argtypes = []

        self.EVP_aes_256_ofb = self._lib.EVP_aes_256_ofb
        self.EVP_aes_256_ofb.restype = ctypes.c_void_p
        self.EVP_aes_256_ofb.argtypes = []

        self.EVP_bf_cbc = self._lib.EVP_bf_cbc
        self.EVP_bf_cbc.restype = ctypes.c_void_p
        self.EVP_bf_cbc.argtypes = []

        self.EVP_bf_cfb64 = self._lib.EVP_bf_cfb64
        self.EVP_bf_cfb64.restype = ctypes.c_void_p
        self.EVP_bf_cfb64.argtypes = []

        self.EVP_rc4 = self._lib.EVP_rc4
        self.EVP_rc4.restype = ctypes.c_void_p
        self.EVP_rc4.argtypes = []

        self.EVP_CIPHER_CTX_cleanup = self._lib.EVP_CIPHER_CTX_cleanup
        self.EVP_CIPHER_CTX_cleanup.restype = ctypes.c_int
        self.EVP_CIPHER_CTX_cleanup.argtypes = [ctypes.c_void_p]

        self.EVP_CIPHER_CTX_free = self._lib.EVP_CIPHER_CTX_free
        self.EVP_CIPHER_CTX_free.restype = None
        self.EVP_CIPHER_CTX_free.argtypes = [ctypes.c_void_p]

        self.EVP_CipherUpdate = self._lib.EVP_CipherUpdate
        self.EVP_CipherUpdate.restype = ctypes.c_int
        self.EVP_CipherUpdate.argtypes = [ctypes.c_void_p,
                                          ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]

        self.EVP_CipherFinal_ex = self._lib.EVP_CipherFinal_ex
        self.EVP_CipherFinal_ex.restype = ctypes.c_int
        self.EVP_CipherFinal_ex.argtypes = [ctypes.c_void_p,
                                            ctypes.c_void_p, ctypes.c_void_p]

        self.EVP_DigestInit = self._lib.EVP_DigestInit
        self.EVP_DigestInit.restype = ctypes.c_int
        self._lib.EVP_DigestInit.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

        self.EVP_DigestUpdate = self._lib.EVP_DigestUpdate
        self.EVP_DigestUpdate.restype = ctypes.c_int
        self.EVP_DigestUpdate.argtypes = [ctypes.c_void_p,
                                          ctypes.c_void_p, ctypes.c_int]

        self.EVP_DigestFinal = self._lib.EVP_DigestFinal
        self.EVP_DigestFinal.restype = ctypes.c_int
        self.EVP_DigestFinal.argtypes = [ctypes.c_void_p,
                                         ctypes.c_void_p, ctypes.c_void_p]

        self.EVP_ecdsa = self._lib.EVP_ecdsa
        self._lib.EVP_ecdsa.restype = ctypes.c_void_p
        self._lib.EVP_ecdsa.argtypes = []

        self.ECDSA_sign = self._lib.ECDSA_sign
        self.ECDSA_sign.restype = ctypes.c_int
        self.ECDSA_sign.argtypes = [ctypes.c_int, ctypes.c_void_p,
                                    ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]

        self.ECDSA_verify = self._lib.ECDSA_verify
        self.ECDSA_verify.restype = ctypes.c_int
        self.ECDSA_verify.argtypes = [ctypes.c_int, ctypes.c_void_p,
                                      ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]

        self.EVP_MD_CTX_create = self._lib.EVP_MD_CTX_create
        self.EVP_MD_CTX_create.restype = ctypes.c_void_p
        self.EVP_MD_CTX_create.argtypes = []

        self.EVP_MD_CTX_init = self._lib.EVP_MD_CTX_init
        self.EVP_MD_CTX_init.restype = None
        self.EVP_MD_CTX_init.argtypes = [ctypes.c_void_p]

        self.EVP_MD_CTX_destroy = self._lib.EVP_MD_CTX_destroy
        self.EVP_MD_CTX_destroy.restype = None
        self.EVP_MD_CTX_destroy.argtypes = [ctypes.c_void_p]

        self.RAND_bytes = self._lib.RAND_bytes
        self.RAND_bytes.restype = None
        self.RAND_bytes.argtypes = [ctypes.c_void_p, ctypes.c_int]


        self.EVP_sha256 = self._lib.EVP_sha256
        self.EVP_sha256.restype = ctypes.c_void_p
        self.EVP_sha256.argtypes = []

        self.EVP_sha512 = self._lib.EVP_sha512
        self.EVP_sha512.restype = ctypes.c_void_p
        self.EVP_sha512.argtypes = []

        self.HMAC = self._lib.HMAC
        self.HMAC.restype = ctypes.c_void_p
        self.HMAC.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
                              ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]

        self.PKCS5_PBKDF2_HMAC = self._lib.PKCS5_PBKDF2_HMAC
        self.PKCS5_PBKDF2_HMAC.restype = ctypes.c_int
        self.PKCS5_PBKDF2_HMAC.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                           ctypes.c_void_p, ctypes.c_int,
                                           ctypes.c_int, ctypes.c_void_p,
                                           ctypes.c_int, ctypes.c_void_p]

        self._set_ciphers()
        self._set_curves()

    def _set_ciphers(self):
        self.cipher_algo = {
            'aes-128-cbc': CipherName('aes-128-cbc', self.EVP_aes_128_cbc, 16),
            'aes-256-cbc': CipherName('aes-256-cbc', self.EVP_aes_256_cbc, 16),
            'aes-128-cfb': CipherName('aes-128-cfb', self.EVP_aes_128_cfb128, 16),
            'aes-256-cfb': CipherName('aes-256-cfb', self.EVP_aes_256_cfb128, 16),
            'aes-128-ofb': CipherName('aes-128-ofb', self._lib.EVP_aes_128_ofb, 16),
            'aes-256-ofb': CipherName('aes-256-ofb', self._lib.EVP_aes_256_ofb, 16),
            'aes-128-ctr': CipherName('aes-128-ctr', self._lib.EVP_aes_128_ctr, 16),
            'aes-256-ctr': CipherName('aes-256-ctr', self._lib.EVP_aes_256_ctr, 16),
            'bf-cfb': CipherName('bf-cfb', self.EVP_bf_cfb64, 8),
            'bf-cbc': CipherName('bf-cbc', self.EVP_bf_cbc, 8),
            'rc4': CipherName('rc4', self.EVP_rc4, 128), # 128 is the initialisation size not block size
        }

    def _set_curves(self):
        self.curves = {
            'secp112r1': 704,
            'secp112r2': 705,
            'secp128r1': 706,
            'secp128r2': 707,
            'secp160k1': 708,
            'secp160r1': 709,
            'secp160r2': 710,
            'secp192k1': 711,
            'secp224k1': 712,
            'secp224r1': 713,
            'secp256k1': 714,
            'secp384r1': 715,
            'secp521r1': 716,
            'sect113r1': 717,
            'sect113r2': 718,
            'sect131r1': 719,
            'sect131r2': 720,
            'sect163k1': 721,
            'sect163r1': 722,
            'sect163r2': 723,
            'sect193r1': 724,
            'sect193r2': 725,
            'sect233k1': 726,
            'sect233r1': 727,
            'sect239k1': 728,
            'sect283k1': 729,
            'sect283r1': 730,
            'sect409k1': 731,
            'sect409r1': 732,
            'sect571k1': 733,
            'sect571r1': 734,
            'prime256v1': 415,
        }

    def BN_num_bytes(self, x):
        """
        returns the length of a BN (OpenSSl API)
        """
        return int((self.BN_num_bits(x) + 7) / 8)

    def get_cipher(self, name):
        """
        returns the OpenSSL cipher instance
        """
        if name not in self.cipher_algo:
            raise Exception("Unknown cipher")
        return self.cipher_algo[name]

    def get_curve(self, name):
        """
        returns the id of a elliptic curve
        """
        if name not in self.curves:
            raise Exception("Unknown curve")
        return self.curves[name]

    def get_curve_by_id(self, id):
        """
        returns the name of a elliptic curve with his id
        """
        res = None
        for i in self.curves:
            if self.curves[i] == id:
                res = i
                break
        if res is None:
            raise Exception("Unknown curve")
        return res

    def rand(self, size):
        """
        OpenSSL random function
        """
        buffer = self.malloc(0, size)
        self.RAND_bytes(buffer, size)
        return buffer.raw

    def malloc(self, data, size):
        """
        returns a create_string_buffer (ctypes)
        """
        buffer = None
        if data != 0:
            if sys.version_info.major == 3 and isinstance(data, type('')):
                data = data.encode()
            buffer = self.create_string_buffer(data, size)
        else:
            buffer = self.create_string_buffer(size)
        return buffer

libname = ctypes.util.find_library('crypto')
if libname is None:
    # For Windows ...
    libname = ctypes.util.find_library('libeay32.dll')
if libname is None:
    raise Exception("Couldn't load OpenSSL lib ...")
OpenSSL = _OpenSSL(libname)

########NEW FILE########
__FILENAME__ = btc_ectest
import pyelliptic
from obelisk import bitcoin
 
# Symmetric encryption
iv = pyelliptic.Cipher.gen_IV('aes-256-cfb')
ctx = pyelliptic.Cipher("secretkey", iv, 1, ciphername='aes-256-cfb')
 
ciphertext = ctx.update('test1')
ciphertext += ctx.update('test2')
ciphertext += ctx.final()
 
ctx2 = pyelliptic.Cipher("secretkey", iv, 0, ciphername='aes-256-cfb')
print ctx2.ciphering(ciphertext)
 
# Asymmetric encryption
alice = pyelliptic.ECC(curve='secp256k1')
bob = pyelliptic.ECC(curve='secp256k1')

ciphertext = alice.encrypt("Hello bbBob", bob.get_pubkey())
print bob.decrypt(ciphertext)
 
signature = bob.sign("Hello Alice")
# alice's job :
print pyelliptic.ECC(pubkey=bob.get_pubkey()).verify(signature, "Hello Alice")
 
# ERROR !!!
try:
    key = alice.get_ecdh_key(bob.get_pubkey())
except: print("For ECDH key agreement, the keys must be defined on the same curve !")
 
alice = pyelliptic.ECC(curve='secp256k1')
print alice.get_ecdh_key(bob.get_pubkey()).encode('hex')
print bob.get_ecdh_key(alice.get_pubkey()).encode('hex')

print bob.get_pubkey().encode('hex')


########NEW FILE########
__FILENAME__ = ectest
import pyelliptic
 
# Symmetric encryption
iv = pyelliptic.Cipher.gen_IV('aes-256-cfb')
ctx = pyelliptic.Cipher("secretkey", iv, 1, ciphername='aes-256-cfb')
 
ciphertext = ctx.update('test1')
ciphertext += ctx.update('test2')
ciphertext += ctx.final()
 
ctx2 = pyelliptic.Cipher("secretkey", iv, 0, ciphername='aes-256-cfb')
print ctx2.ciphering(ciphertext)
 
# Asymmetric encryption
alice = pyelliptic.ECC(curve='secp256k1')
bob = pyelliptic.ECC(curve='secp256k1')

ciphertext = alice.encrypt("Hello bbBob", bob.get_pubkey())
print bob.decrypt(ciphertext)
 
signature = bob.sign("Hello Alice")
# alice's job :
print pyelliptic.ECC(pubkey=bob.get_pubkey()).verify(signature, "Hello Alice")
 
# ERROR !!!
try:
    key = alice.get_ecdh_key(bob.get_pubkey())
except: print("For ECDH key agreement, the keys must be defined on the same curve !")
 
alice = pyelliptic.ECC(curve='secp256k1')
print alice.get_ecdh_key(bob.get_pubkey()).encode('hex')
print bob.get_ecdh_key(alice.get_pubkey()).encode('hex')

print bob.get_pubkey().encode('hex')

########NEW FILE########
