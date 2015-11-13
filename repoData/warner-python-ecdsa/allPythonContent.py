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

# This file helps to compute a version number in source trees obtained from
# git-archive tarball (such as those provided by githubs download-from-tag
# feature). Distribution tarballs (build by setup.py sdist) and build
# directories (produced by setup.py build) will contain a much shorter file
# that just contains the computed version number.

# This file is released into the public domain. Generated by
# versioneer-0.9 (https://github.com/warner/python-versioneer)

# these strings will be replaced by git during git-archive
git_refnames = "$Format:%d$"
git_full = "$Format:%H$"


import subprocess
import sys
import errno


def run_command(commands, args, cwd=None, verbose=False, hide_stderr=False):
    assert isinstance(commands, list)
    p = None
    for c in commands:
        try:
            # remember shell=False, so use git.cmd on windows, not just git
            p = subprocess.Popen([c] + args, cwd=cwd, stdout=subprocess.PIPE,
                                 stderr=(subprocess.PIPE if hide_stderr
                                         else None))
            break
        except EnvironmentError:
            e = sys.exc_info()[1]
            if e.errno == errno.ENOENT:
                continue
            if verbose:
                print("unable to run %s" % args[0])
                print(e)
            return None
    else:
        if verbose:
            print("unable to find command, tried %s" % (commands,))
        return None
    stdout = p.communicate()[0].strip()
    if sys.version >= '3':
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            print("unable to run %s (error)" % args[0])
        return None
    return stdout


import sys
import re
import os.path

def get_expanded_variables(versionfile_abs):
    # the code embedded in _version.py can just fetch the value of these
    # variables. When used from setup.py, we don't want to import
    # _version.py, so we do it with a regexp instead. This function is not
    # used from _version.py.
    variables = {}
    try:
        f = open(versionfile_abs,"r")
        for line in f.readlines():
            if line.strip().startswith("git_refnames ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["refnames"] = mo.group(1)
            if line.strip().startswith("git_full ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["full"] = mo.group(1)
        f.close()
    except EnvironmentError:
        pass
    return variables

def versions_from_expanded_variables(variables, tag_prefix, verbose=False):
    refnames = variables["refnames"].strip()
    if refnames.startswith("$Format"):
        if verbose:
            print("variables are unexpanded, not using")
        return {} # unexpanded, so not in an unpacked git-archive tarball
    refs = set([r.strip() for r in refnames.strip("()").split(",")])
    # starting in git-1.8.3, tags are listed as "tag: foo-1.0" instead of
    # just "foo-1.0". If we see a "tag: " prefix, prefer those.
    TAG = "tag: "
    tags = set([r[len(TAG):] for r in refs if r.startswith(TAG)])
    if not tags:
        # Either we're using git < 1.8.3, or there really are no tags. We use
        # a heuristic: assume all version tags have a digit. The old git %d
        # expansion behaves like git log --decorate=short and strips out the
        # refs/heads/ and refs/tags/ prefixes that would let us distinguish
        # between branches and tags. By ignoring refnames without digits, we
        # filter out many common branch names like "release" and
        # "stabilization", as well as "HEAD" and "master".
        tags = set([r for r in refs if re.search(r'\d', r)])
        if verbose:
            print("discarding '%s', no digits" % ",".join(refs-tags))
    if verbose:
        print("likely tags: %s" % ",".join(sorted(tags)))
    for ref in sorted(tags):
        # sorting will prefer e.g. "2.0" over "2.0rc1"
        if ref.startswith(tag_prefix):
            r = ref[len(tag_prefix):]
            if verbose:
                print("picking %s" % r)
            return { "version": r,
                     "full": variables["full"].strip() }
    # no suitable tags, so we use the full revision id
    if verbose:
        print("no suitable tags, using full revision id")
    return { "version": variables["full"].strip(),
             "full": variables["full"].strip() }

def versions_from_vcs(tag_prefix, root, verbose=False):
    # this runs 'git' from the root of the source tree. This only gets called
    # if the git-archive 'subst' variables were *not* expanded, and
    # _version.py hasn't already been rewritten with a short version string,
    # meaning we're inside a checked out source tree.

    if not os.path.exists(os.path.join(root, ".git")):
        if verbose:
            print("no .git in %s" % root)
        return {}

    GITS = ["git"]
    if sys.platform == "win32":
        GITS = ["git.cmd", "git.exe"]
    stdout = run_command(GITS, ["describe", "--tags", "--dirty", "--always"],
                         cwd=root)
    if stdout is None:
        return {}
    if not stdout.startswith(tag_prefix):
        if verbose:
            print("tag '%s' doesn't start with prefix '%s'" % (stdout, tag_prefix))
        return {}
    tag = stdout[len(tag_prefix):]
    stdout = run_command(GITS, ["rev-parse", "HEAD"], cwd=root)
    if stdout is None:
        return {}
    full = stdout.strip()
    if tag.endswith("-dirty"):
        full += "-dirty"
    return {"version": tag, "full": full}


def versions_from_parentdir(parentdir_prefix, root, verbose=False):
    # Source tarballs conventionally unpack into a directory that includes
    # both the project name and a version string.
    dirname = os.path.basename(root)
    if not dirname.startswith(parentdir_prefix):
        if verbose:
            print("guessing rootdir is '%s', but '%s' doesn't start with prefix '%s'" %
                  (root, dirname, parentdir_prefix))
        return None
    return {"version": dirname[len(parentdir_prefix):], "full": ""}

tag_prefix = "python-ecdsa-"
parentdir_prefix = "ecdsa-"
versionfile_source = "ecdsa/_version.py"

def get_versions(default={"version": "unknown", "full": ""}, verbose=False):
    # I am in _version.py, which lives at ROOT/VERSIONFILE_SOURCE. If we have
    # __file__, we can work backwards from there to the root. Some
    # py2exe/bbfreeze/non-CPython implementations don't do __file__, in which
    # case we can only use expanded variables.

    variables = { "refnames": git_refnames, "full": git_full }
    ver = versions_from_expanded_variables(variables, tag_prefix, verbose)
    if ver:
        return ver

    try:
        root = os.path.abspath(__file__)
        # versionfile_source is the relative path from the top of the source
        # tree (where the .git directory might live) to this file. Invert
        # this to find the root from __file__.
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    except NameError:
        return default

    return (versions_from_vcs(tag_prefix, root, verbose)
            or versions_from_parentdir(parentdir_prefix, root, verbose)
            or default)


########NEW FILE########
__FILENAME__ = versioneer

# Version: 0.9

"""
The Versioneer
==============

* like a rocketeer, but for versions!
* https://github.com/warner/python-versioneer
* Brian Warner
* License: Public Domain
* Compatible With: python2.6, 2.7, and 3.2, 3.3

[![Build Status](https://travis-ci.org/warner/python-versioneer.png?branch=master)](https://travis-ci.org/warner/python-versioneer)

This is a tool for managing a recorded version number in distutils-based
python projects. The goal is to remove the tedious and error-prone "update
the embedded version string" step from your release process. Making a new
release should be as easy as recording a new tag in your version-control
system, and maybe making new tarballs.


## Quick Install

* `pip install versioneer` to somewhere to your $PATH
* run `versioneer-installer` in your source tree: this installs `versioneer.py`
* follow the instructions below (also in the `versioneer.py` docstring)

## Version Identifiers

Source trees come from a variety of places:

* a version-control system checkout (mostly used by developers)
* a nightly tarball, produced by build automation
* a snapshot tarball, produced by a web-based VCS browser, like github's
  "tarball from tag" feature
* a release tarball, produced by "setup.py sdist", distributed through PyPI

Within each source tree, the version identifier (either a string or a number,
this tool is format-agnostic) can come from a variety of places:

* ask the VCS tool itself, e.g. "git describe" (for checkouts), which knows
  about recent "tags" and an absolute revision-id
* the name of the directory into which the tarball was unpacked
* an expanded VCS variable ($Id$, etc)
* a `_version.py` created by some earlier build step

For released software, the version identifier is closely related to a VCS
tag. Some projects use tag names that include more than just the version
string (e.g. "myproject-1.2" instead of just "1.2"), in which case the tool
needs to strip the tag prefix to extract the version identifier. For
unreleased software (between tags), the version identifier should provide
enough information to help developers recreate the same tree, while also
giving them an idea of roughly how old the tree is (after version 1.2, before
version 1.3). Many VCS systems can report a description that captures this,
for example 'git describe --tags --dirty --always' reports things like
"0.7-1-g574ab98-dirty" to indicate that the checkout is one revision past the
0.7 tag, has a unique revision id of "574ab98", and is "dirty" (it has
uncommitted changes.

The version identifier is used for multiple purposes:

* to allow the module to self-identify its version: `myproject.__version__`
* to choose a name and prefix for a 'setup.py sdist' tarball

## Theory of Operation

Versioneer works by adding a special `_version.py` file into your source
tree, where your `__init__.py` can import it. This `_version.py` knows how to
dynamically ask the VCS tool for version information at import time. However,
when you use "setup.py build" or "setup.py sdist", `_version.py` in the new
copy is replaced by a small static file that contains just the generated
version data.

`_version.py` also contains `$Revision$` markers, and the installation
process marks `_version.py` to have this marker rewritten with a tag name
during the "git archive" command. As a result, generated tarballs will
contain enough information to get the proper version.


## Installation

First, decide on values for the following configuration variables:

* `versionfile_source`:

  A project-relative pathname into which the generated version strings should
  be written. This is usually a `_version.py` next to your project's main
  `__init__.py` file. If your project uses `src/myproject/__init__.py`, this
  should be `src/myproject/_version.py`. This file should be checked in to
  your VCS as usual: the copy created below by 'setup.py update_files' will
  include code that parses expanded VCS keywords in generated tarballs. The
  'build' and 'sdist' commands will replace it with a copy that has just the
  calculated version string.

*  `versionfile_build`:

  Like `versionfile_source`, but relative to the build directory instead of
  the source directory. These will differ when your setup.py uses
  'package_dir='. If you have `package_dir={'myproject': 'src/myproject'}`,
  then you will probably have `versionfile_build='myproject/_version.py'` and
  `versionfile_source='src/myproject/_version.py'`.

* `tag_prefix`:

  a string, like 'PROJECTNAME-', which appears at the start of all VCS tags.
  If your tags look like 'myproject-1.2.0', then you should use
  tag_prefix='myproject-'. If you use unprefixed tags like '1.2.0', this
  should be an empty string.

* `parentdir_prefix`:

  a string, frequently the same as tag_prefix, which appears at the start of
  all unpacked tarball filenames. If your tarball unpacks into
  'myproject-1.2.0', this should be 'myproject-'.

This tool provides one script, named `versioneer-installer`. That script does
one thing: write a copy of `versioneer.py` into the current directory.

To versioneer-enable your project:

* 1: Run `versioneer-installer` to copy `versioneer.py` into the top of your
  source tree.

* 2: add the following lines to the top of your `setup.py`, with the
  configuration values you decided earlier:

        import versioneer
        versioneer.versionfile_source = 'src/myproject/_version.py'
        versioneer.versionfile_build = 'myproject/_version.py'
        versioneer.tag_prefix = '' # tags are like 1.2.0
        versioneer.parentdir_prefix = 'myproject-' # dirname like 'myproject-1.2.0'

* 3: add the following arguments to the setup() call in your setup.py:

        version=versioneer.get_version(),
        cmdclass=versioneer.get_cmdclass(),

* 4: now run `setup.py update_files`, which will create `_version.py`, and
  will modify your `__init__.py` to define `__version__` (by calling a
  function from `_version.py`)

* 5: modify your MANIFEST.in to include `versioneer.py` in sdist tarballs

* 6: commit these changes to your VCS. `update_files` will mark both
  `versioneer.py` and the generated `_version.py` for addition.

## Post-Installation Usage

Once established, all uses of your tree from a VCS checkout should get the
current version string. All generated tarballs should include an embedded
version string (so users who unpack them will not need a VCS tool installed).

If you distribute your project through PyPI, then the release process should
boil down to two steps:

* 1: git tag 1.0
* 2: python setup.py register sdist upload

If you distribute it through github (i.e. users use github to generate
tarballs with `git archive`), the process is:

* 1: git tag 1.0
* 2: git push; git push --tags

Currently, all version strings must be based upon a tag. Versioneer will
report "unknown" until your tree has at least one tag in its history. This
restriction will be fixed eventually (see issue #12).

## Version-String Flavors

Code which uses Versioneer can learn about its version string at runtime by
importing `_version` from your main `__init__.py` file and running the
`get_versions()` function. From the "outside" (e.g. in `setup.py`), you can
import the top-level `versioneer.py` and run `get_versions()`.

Both functions return a dictionary with different keys for different flavors
of the version string:

* `['version']`: condensed tag+distance+shortid+dirty identifier. For git,
  this uses the output of `git describe --tags --dirty --always` but strips
  the tag_prefix. For example "0.11-2-g1076c97-dirty" indicates that the tree
  is like the "1076c97" commit but has uncommitted changes ("-dirty"), and
  that this commit is two revisions ("-2-") beyond the "0.11" tag. For
  released software (exactly equal to a known tag), the identifier will only
  contain the stripped tag, e.g. "0.11".

* `['full']`: detailed revision identifier. For Git, this is the full SHA1
  commit id, followed by "-dirty" if the tree contains uncommitted changes,
  e.g. "1076c978a8d3cfc70f408fe5974aa6c092c949ac-dirty".

Some variants are more useful than others. Including `full` in a bug report
should allow developers to reconstruct the exact code being tested (or
indicate the presence of local changes that should be shared with the
developers). `version` is suitable for display in an "about" box or a CLI
`--version` output: it can be easily compared against release notes and lists
of bugs fixed in various releases.

In the future, this will also include a
[PEP-0440](http://legacy.python.org/dev/peps/pep-0440/) -compatible flavor
(e.g. `1.2.post0.dev123`). This loses a lot of information (and has no room
for a hash-based revision id), but is safe to use in a `setup.py`
"`version=`" argument. It also enables tools like *pip* to compare version
strings and evaluate compatibility constraint declarations.

The `setup.py update_files` command adds the following text to your
`__init__.py` to place a basic version in `YOURPROJECT.__version__`:

    from ._version import get_versions
    __version = get_versions()['version']
    del get_versions

## Future Directions

This tool is designed to make it easily extended to other version-control
systems: all VCS-specific components are in separate directories like
src/git/ . The top-level `versioneer.py` script is assembled from these
components by running make-versioneer.py . In the future, make-versioneer.py
will take a VCS name as an argument, and will construct a version of
`versioneer.py` that is specific to the given VCS. It might also take the
configuration arguments that are currently provided manually during
installation by editing setup.py . Alternatively, it might go the other
direction and include code from all supported VCS systems, reducing the
number of intermediate scripts.


## License

To make Versioneer easier to embed, all its code is hereby released into the
public domain. The `_version.py` that it creates is also in the public
domain.

"""

import os, sys, re
from distutils.core import Command
from distutils.command.sdist import sdist as _sdist
from distutils.command.build import build as _build

versionfile_source = None
versionfile_build = None
tag_prefix = None
parentdir_prefix = None

VCS = "git"


LONG_VERSION_PY = '''
# This file helps to compute a version number in source trees obtained from
# git-archive tarball (such as those provided by githubs download-from-tag
# feature). Distribution tarballs (build by setup.py sdist) and build
# directories (produced by setup.py build) will contain a much shorter file
# that just contains the computed version number.

# This file is released into the public domain. Generated by
# versioneer-0.9 (https://github.com/warner/python-versioneer)

# these strings will be replaced by git during git-archive
git_refnames = "%(DOLLAR)sFormat:%%d%(DOLLAR)s"
git_full = "%(DOLLAR)sFormat:%%H%(DOLLAR)s"


import subprocess
import sys
import errno


def run_command(commands, args, cwd=None, verbose=False, hide_stderr=False):
    assert isinstance(commands, list)
    p = None
    for c in commands:
        try:
            # remember shell=False, so use git.cmd on windows, not just git
            p = subprocess.Popen([c] + args, cwd=cwd, stdout=subprocess.PIPE,
                                 stderr=(subprocess.PIPE if hide_stderr
                                         else None))
            break
        except EnvironmentError:
            e = sys.exc_info()[1]
            if e.errno == errno.ENOENT:
                continue
            if verbose:
                print("unable to run %%s" %% args[0])
                print(e)
            return None
    else:
        if verbose:
            print("unable to find command, tried %%s" %% (commands,))
        return None
    stdout = p.communicate()[0].strip()
    if sys.version >= '3':
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            print("unable to run %%s (error)" %% args[0])
        return None
    return stdout


import sys
import re
import os.path

def get_expanded_variables(versionfile_abs):
    # the code embedded in _version.py can just fetch the value of these
    # variables. When used from setup.py, we don't want to import
    # _version.py, so we do it with a regexp instead. This function is not
    # used from _version.py.
    variables = {}
    try:
        f = open(versionfile_abs,"r")
        for line in f.readlines():
            if line.strip().startswith("git_refnames ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["refnames"] = mo.group(1)
            if line.strip().startswith("git_full ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["full"] = mo.group(1)
        f.close()
    except EnvironmentError:
        pass
    return variables

def versions_from_expanded_variables(variables, tag_prefix, verbose=False):
    refnames = variables["refnames"].strip()
    if refnames.startswith("$Format"):
        if verbose:
            print("variables are unexpanded, not using")
        return {} # unexpanded, so not in an unpacked git-archive tarball
    refs = set([r.strip() for r in refnames.strip("()").split(",")])
    # starting in git-1.8.3, tags are listed as "tag: foo-1.0" instead of
    # just "foo-1.0". If we see a "tag: " prefix, prefer those.
    TAG = "tag: "
    tags = set([r[len(TAG):] for r in refs if r.startswith(TAG)])
    if not tags:
        # Either we're using git < 1.8.3, or there really are no tags. We use
        # a heuristic: assume all version tags have a digit. The old git %%d
        # expansion behaves like git log --decorate=short and strips out the
        # refs/heads/ and refs/tags/ prefixes that would let us distinguish
        # between branches and tags. By ignoring refnames without digits, we
        # filter out many common branch names like "release" and
        # "stabilization", as well as "HEAD" and "master".
        tags = set([r for r in refs if re.search(r'\d', r)])
        if verbose:
            print("discarding '%%s', no digits" %% ",".join(refs-tags))
    if verbose:
        print("likely tags: %%s" %% ",".join(sorted(tags)))
    for ref in sorted(tags):
        # sorting will prefer e.g. "2.0" over "2.0rc1"
        if ref.startswith(tag_prefix):
            r = ref[len(tag_prefix):]
            if verbose:
                print("picking %%s" %% r)
            return { "version": r,
                     "full": variables["full"].strip() }
    # no suitable tags, so we use the full revision id
    if verbose:
        print("no suitable tags, using full revision id")
    return { "version": variables["full"].strip(),
             "full": variables["full"].strip() }

def versions_from_vcs(tag_prefix, root, verbose=False):
    # this runs 'git' from the root of the source tree. This only gets called
    # if the git-archive 'subst' variables were *not* expanded, and
    # _version.py hasn't already been rewritten with a short version string,
    # meaning we're inside a checked out source tree.

    if not os.path.exists(os.path.join(root, ".git")):
        if verbose:
            print("no .git in %%s" %% root)
        return {}

    GITS = ["git"]
    if sys.platform == "win32":
        GITS = ["git.cmd", "git.exe"]
    stdout = run_command(GITS, ["describe", "--tags", "--dirty", "--always"],
                         cwd=root)
    if stdout is None:
        return {}
    if not stdout.startswith(tag_prefix):
        if verbose:
            print("tag '%%s' doesn't start with prefix '%%s'" %% (stdout, tag_prefix))
        return {}
    tag = stdout[len(tag_prefix):]
    stdout = run_command(GITS, ["rev-parse", "HEAD"], cwd=root)
    if stdout is None:
        return {}
    full = stdout.strip()
    if tag.endswith("-dirty"):
        full += "-dirty"
    return {"version": tag, "full": full}


def versions_from_parentdir(parentdir_prefix, root, verbose=False):
    # Source tarballs conventionally unpack into a directory that includes
    # both the project name and a version string.
    dirname = os.path.basename(root)
    if not dirname.startswith(parentdir_prefix):
        if verbose:
            print("guessing rootdir is '%%s', but '%%s' doesn't start with prefix '%%s'" %%
                  (root, dirname, parentdir_prefix))
        return None
    return {"version": dirname[len(parentdir_prefix):], "full": ""}

tag_prefix = "%(TAG_PREFIX)s"
parentdir_prefix = "%(PARENTDIR_PREFIX)s"
versionfile_source = "%(VERSIONFILE_SOURCE)s"

def get_versions(default={"version": "unknown", "full": ""}, verbose=False):
    # I am in _version.py, which lives at ROOT/VERSIONFILE_SOURCE. If we have
    # __file__, we can work backwards from there to the root. Some
    # py2exe/bbfreeze/non-CPython implementations don't do __file__, in which
    # case we can only use expanded variables.

    variables = { "refnames": git_refnames, "full": git_full }
    ver = versions_from_expanded_variables(variables, tag_prefix, verbose)
    if ver:
        return ver

    try:
        root = os.path.abspath(__file__)
        # versionfile_source is the relative path from the top of the source
        # tree (where the .git directory might live) to this file. Invert
        # this to find the root from __file__.
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    except NameError:
        return default

    return (versions_from_vcs(tag_prefix, root, verbose)
            or versions_from_parentdir(parentdir_prefix, root, verbose)
            or default)

'''


import subprocess
import sys
import errno


def run_command(commands, args, cwd=None, verbose=False, hide_stderr=False):
    assert isinstance(commands, list)
    p = None
    for c in commands:
        try:
            # remember shell=False, so use git.cmd on windows, not just git
            p = subprocess.Popen([c] + args, cwd=cwd, stdout=subprocess.PIPE,
                                 stderr=(subprocess.PIPE if hide_stderr
                                         else None))
            break
        except EnvironmentError:
            e = sys.exc_info()[1]
            if e.errno == errno.ENOENT:
                continue
            if verbose:
                print("unable to run %s" % args[0])
                print(e)
            return None
    else:
        if verbose:
            print("unable to find command, tried %s" % (commands,))
        return None
    stdout = p.communicate()[0].strip()
    if sys.version >= '3':
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            print("unable to run %s (error)" % args[0])
        return None
    return stdout


import sys
import re
import os.path

def get_expanded_variables(versionfile_abs):
    # the code embedded in _version.py can just fetch the value of these
    # variables. When used from setup.py, we don't want to import
    # _version.py, so we do it with a regexp instead. This function is not
    # used from _version.py.
    variables = {}
    try:
        f = open(versionfile_abs,"r")
        for line in f.readlines():
            if line.strip().startswith("git_refnames ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["refnames"] = mo.group(1)
            if line.strip().startswith("git_full ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["full"] = mo.group(1)
        f.close()
    except EnvironmentError:
        pass
    return variables

def versions_from_expanded_variables(variables, tag_prefix, verbose=False):
    refnames = variables["refnames"].strip()
    if refnames.startswith("$Format"):
        if verbose:
            print("variables are unexpanded, not using")
        return {} # unexpanded, so not in an unpacked git-archive tarball
    refs = set([r.strip() for r in refnames.strip("()").split(",")])
    # starting in git-1.8.3, tags are listed as "tag: foo-1.0" instead of
    # just "foo-1.0". If we see a "tag: " prefix, prefer those.
    TAG = "tag: "
    tags = set([r[len(TAG):] for r in refs if r.startswith(TAG)])
    if not tags:
        # Either we're using git < 1.8.3, or there really are no tags. We use
        # a heuristic: assume all version tags have a digit. The old git %d
        # expansion behaves like git log --decorate=short and strips out the
        # refs/heads/ and refs/tags/ prefixes that would let us distinguish
        # between branches and tags. By ignoring refnames without digits, we
        # filter out many common branch names like "release" and
        # "stabilization", as well as "HEAD" and "master".
        tags = set([r for r in refs if re.search(r'\d', r)])
        if verbose:
            print("discarding '%s', no digits" % ",".join(refs-tags))
    if verbose:
        print("likely tags: %s" % ",".join(sorted(tags)))
    for ref in sorted(tags):
        # sorting will prefer e.g. "2.0" over "2.0rc1"
        if ref.startswith(tag_prefix):
            r = ref[len(tag_prefix):]
            if verbose:
                print("picking %s" % r)
            return { "version": r,
                     "full": variables["full"].strip() }
    # no suitable tags, so we use the full revision id
    if verbose:
        print("no suitable tags, using full revision id")
    return { "version": variables["full"].strip(),
             "full": variables["full"].strip() }

def versions_from_vcs(tag_prefix, root, verbose=False):
    # this runs 'git' from the root of the source tree. This only gets called
    # if the git-archive 'subst' variables were *not* expanded, and
    # _version.py hasn't already been rewritten with a short version string,
    # meaning we're inside a checked out source tree.

    if not os.path.exists(os.path.join(root, ".git")):
        if verbose:
            print("no .git in %s" % root)
        return {}

    GITS = ["git"]
    if sys.platform == "win32":
        GITS = ["git.cmd", "git.exe"]
    stdout = run_command(GITS, ["describe", "--tags", "--dirty", "--always"],
                         cwd=root)
    if stdout is None:
        return {}
    if not stdout.startswith(tag_prefix):
        if verbose:
            print("tag '%s' doesn't start with prefix '%s'" % (stdout, tag_prefix))
        return {}
    tag = stdout[len(tag_prefix):]
    stdout = run_command(GITS, ["rev-parse", "HEAD"], cwd=root)
    if stdout is None:
        return {}
    full = stdout.strip()
    if tag.endswith("-dirty"):
        full += "-dirty"
    return {"version": tag, "full": full}


def versions_from_parentdir(parentdir_prefix, root, verbose=False):
    # Source tarballs conventionally unpack into a directory that includes
    # both the project name and a version string.
    dirname = os.path.basename(root)
    if not dirname.startswith(parentdir_prefix):
        if verbose:
            print("guessing rootdir is '%s', but '%s' doesn't start with prefix '%s'" %
                  (root, dirname, parentdir_prefix))
        return None
    return {"version": dirname[len(parentdir_prefix):], "full": ""}
import os.path
import sys

# os.path.relpath only appeared in Python-2.6 . Define it here for 2.5.
def os_path_relpath(path, start=os.path.curdir):
    """Return a relative version of a path"""

    if not path:
        raise ValueError("no path specified")

    start_list = [x for x in os.path.abspath(start).split(os.path.sep) if x]
    path_list = [x for x in os.path.abspath(path).split(os.path.sep) if x]

    # Work out how much of the filepath is shared by start and path.
    i = len(os.path.commonprefix([start_list, path_list]))

    rel_list = [os.path.pardir] * (len(start_list)-i) + path_list[i:]
    if not rel_list:
        return os.path.curdir
    return os.path.join(*rel_list)

def do_vcs_install(versionfile_source, ipy):
    GITS = ["git"]
    if sys.platform == "win32":
        GITS = ["git.cmd", "git.exe"]
    files = [versionfile_source, ipy]
    try:
        me = __file__
        if me.endswith(".pyc") or me.endswith(".pyo"):
            me = os.path.splitext(me)[0] + ".py"
        versioneer_file = os_path_relpath(me)
    except NameError:
        versioneer_file = "versioneer.py"
    files.append(versioneer_file)
    present = False
    try:
        f = open(".gitattributes", "r")
        for line in f.readlines():
            if line.strip().startswith(versionfile_source):
                if "export-subst" in line.strip().split()[1:]:
                    present = True
        f.close()
    except EnvironmentError:
        pass    
    if not present:
        f = open(".gitattributes", "a+")
        f.write("%s export-subst\n" % versionfile_source)
        f.close()
        files.append(".gitattributes")
    run_command(GITS, ["add", "--"] + files)

SHORT_VERSION_PY = """
# This file was generated by 'versioneer.py' (0.9) from
# revision-control system data, or from the parent directory name of an
# unpacked source archive. Distribution tarballs contain a pre-generated copy
# of this file.

version_version = '%(version)s'
version_full = '%(full)s'
def get_versions(default={}, verbose=False):
    return {'version': version_version, 'full': version_full}

"""

DEFAULT = {"version": "unknown", "full": "unknown"}

def versions_from_file(filename):
    versions = {}
    try:
        f = open(filename)
    except EnvironmentError:
        return versions
    for line in f.readlines():
        mo = re.match("version_version = '([^']+)'", line)
        if mo:
            versions["version"] = mo.group(1)
        mo = re.match("version_full = '([^']+)'", line)
        if mo:
            versions["full"] = mo.group(1)
    f.close()
    return versions

def write_to_version_file(filename, versions):
    f = open(filename, "w")
    f.write(SHORT_VERSION_PY % versions)
    f.close()
    print("set %s to '%s'" % (filename, versions["version"]))


def get_versions(default=DEFAULT, verbose=False):
    # returns dict with two keys: 'version' and 'full'
    assert versionfile_source is not None, "please set versioneer.versionfile_source"
    assert tag_prefix is not None, "please set versioneer.tag_prefix"
    assert parentdir_prefix is not None, "please set versioneer.parentdir_prefix"
    # I am in versioneer.py, which must live at the top of the source tree,
    # which we use to compute the root directory. py2exe/bbfreeze/non-CPython
    # don't have __file__, in which case we fall back to sys.argv[0] (which
    # ought to be the setup.py script). We prefer __file__ since that's more
    # robust in cases where setup.py was invoked in some weird way (e.g. pip)
    try:
        root = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        root = os.path.dirname(os.path.abspath(sys.argv[0]))
    versionfile_abs = os.path.join(root, versionfile_source)

    # extract version from first of _version.py, 'git describe', parentdir.
    # This is meant to work for developers using a source checkout, for users
    # of a tarball created by 'setup.py sdist', and for users of a
    # tarball/zipball created by 'git archive' or github's download-from-tag
    # feature.

    variables = get_expanded_variables(versionfile_abs)
    if variables:
        ver = versions_from_expanded_variables(variables, tag_prefix)
        if ver:
            if verbose: print("got version from expanded variable %s" % ver)
            return ver

    ver = versions_from_file(versionfile_abs)
    if ver:
        if verbose: print("got version from file %s %s" % (versionfile_abs,ver))
        return ver

    ver = versions_from_vcs(tag_prefix, root, verbose)
    if ver:
        if verbose: print("got version from git %s" % ver)
        return ver

    ver = versions_from_parentdir(parentdir_prefix, root, verbose)
    if ver:
        if verbose: print("got version from parentdir %s" % ver)
        return ver

    if verbose: print("got version from default %s" % ver)
    return default

def get_version(verbose=False):
    return get_versions(verbose=verbose)["version"]

class cmd_version(Command):
    description = "report generated version string"
    user_options = []
    boolean_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        ver = get_version(verbose=True)
        print("Version is currently: %s" % ver)


class cmd_build(_build):
    def run(self):
        versions = get_versions(verbose=True)
        _build.run(self)
        # now locate _version.py in the new build/ directory and replace it
        # with an updated value
        target_versionfile = os.path.join(self.build_lib, versionfile_build)
        print("UPDATING %s" % target_versionfile)
        os.unlink(target_versionfile)
        f = open(target_versionfile, "w")
        f.write(SHORT_VERSION_PY % versions)
        f.close()

class cmd_sdist(_sdist):
    def run(self):
        versions = get_versions(verbose=True)
        self._versioneer_generated_versions = versions
        # unless we update this, the command will keep using the old version
        self.distribution.metadata.version = versions["version"]
        return _sdist.run(self)

    def make_release_tree(self, base_dir, files):
        _sdist.make_release_tree(self, base_dir, files)
        # now locate _version.py in the new base_dir directory (remembering
        # that it may be a hardlink) and replace it with an updated value
        target_versionfile = os.path.join(base_dir, versionfile_source)
        print("UPDATING %s" % target_versionfile)
        os.unlink(target_versionfile)
        f = open(target_versionfile, "w")
        f.write(SHORT_VERSION_PY % self._versioneer_generated_versions)
        f.close()

INIT_PY_SNIPPET = """
from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
"""

class cmd_update_files(Command):
    description = "modify __init__.py and create _version.py"
    user_options = []
    boolean_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        ipy = os.path.join(os.path.dirname(versionfile_source), "__init__.py")
        print(" creating %s" % versionfile_source)
        f = open(versionfile_source, "w")
        f.write(LONG_VERSION_PY % {"DOLLAR": "$",
                                   "TAG_PREFIX": tag_prefix,
                                   "PARENTDIR_PREFIX": parentdir_prefix,
                                   "VERSIONFILE_SOURCE": versionfile_source,
                                   })
        f.close()
        try:
            old = open(ipy, "r").read()
        except EnvironmentError:
            old = ""
        if INIT_PY_SNIPPET not in old:
            print(" appending to %s" % ipy)
            f = open(ipy, "a")
            f.write(INIT_PY_SNIPPET)
            f.close()
        else:
            print(" %s unmodified" % ipy)
        do_vcs_install(versionfile_source, ipy)

def get_cmdclass():
    return {'version': cmd_version,
            'update_files': cmd_update_files,
            'build': cmd_build,
            'sdist': cmd_sdist,
            }

########NEW FILE########
