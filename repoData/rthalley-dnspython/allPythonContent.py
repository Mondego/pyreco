__FILENAME__ = dnssec
# Copyright (C) 2003-2007, 2009, 2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""Common DNSSEC-related functions and constants."""

import cStringIO
import struct
import time

import dns.exception
import dns.hash
import dns.name
import dns.node
import dns.rdataset
import dns.rdata
import dns.rdatatype
import dns.rdataclass

class UnsupportedAlgorithm(dns.exception.DNSException):
    """Raised if an algorithm is not supported."""
    pass

class ValidationFailure(dns.exception.DNSException):
    """The DNSSEC signature is invalid."""
    pass

RSAMD5 = 1
DH = 2
DSA = 3
ECC = 4
RSASHA1 = 5
DSANSEC3SHA1 = 6
RSASHA1NSEC3SHA1 = 7
RSASHA256 = 8
RSASHA512 = 10
ECDSAP256SHA256 = 13
ECDSAP384SHA384 = 14
INDIRECT = 252
PRIVATEDNS = 253
PRIVATEOID = 254

_algorithm_by_text = {
    'RSAMD5' : RSAMD5,
    'DH' : DH,
    'DSA' : DSA,
    'ECC' : ECC,
    'RSASHA1' : RSASHA1,
    'DSANSEC3SHA1' : DSANSEC3SHA1,
    'RSASHA1NSEC3SHA1' : RSASHA1NSEC3SHA1,
    'RSASHA256' : RSASHA256,
    'RSASHA512' : RSASHA512,
    'INDIRECT' : INDIRECT,
    'ECDSAP256SHA256' : ECDSAP256SHA256,
    'ECDSAP384SHA384' : ECDSAP384SHA384,
    'PRIVATEDNS' : PRIVATEDNS,
    'PRIVATEOID' : PRIVATEOID,
    }

# We construct the inverse mapping programmatically to ensure that we
# cannot make any mistakes (e.g. omissions, cut-and-paste errors) that
# would cause the mapping not to be true inverse.

_algorithm_by_value = dict([(y, x) for x, y in _algorithm_by_text.iteritems()])

def algorithm_from_text(text):
    """Convert text into a DNSSEC algorithm value
    @rtype: int"""

    value = _algorithm_by_text.get(text.upper())
    if value is None:
        value = int(text)
    return value

def algorithm_to_text(value):
    """Convert a DNSSEC algorithm value to text
    @rtype: string"""

    text = _algorithm_by_value.get(value)
    if text is None:
        text = str(value)
    return text

def _to_rdata(record, origin):
    s = cStringIO.StringIO()
    record.to_wire(s, origin=origin)
    return s.getvalue()

def key_id(key, origin=None):
    rdata = _to_rdata(key, origin)
    if key.algorithm == RSAMD5:
        return (ord(rdata[-3]) << 8) + ord(rdata[-2])
    else:
        total = 0
        for i in range(len(rdata) // 2):
            total += (ord(rdata[2 * i]) << 8) + ord(rdata[2 * i + 1])
        if len(rdata) % 2 != 0:
            total += ord(rdata[len(rdata) - 1]) << 8
        total += ((total >> 16) & 0xffff);
        return total & 0xffff

def make_ds(name, key, algorithm, origin=None):
    if algorithm.upper() == 'SHA1':
        dsalg = 1
        hash = dns.hash.get('SHA1')()
    elif algorithm.upper() == 'SHA256':
        dsalg = 2
        hash = dns.hash.get('SHA256')()
    else:
        raise UnsupportedAlgorithm, 'unsupported algorithm "%s"' % algorithm

    if isinstance(name, (str, unicode)):
        name = dns.name.from_text(name, origin)
    hash.update(name.canonicalize().to_wire())
    hash.update(_to_rdata(key, origin))
    digest = hash.digest()

    dsrdata = struct.pack("!HBB", key_id(key), key.algorithm, dsalg) + digest
    return dns.rdata.from_wire(dns.rdataclass.IN, dns.rdatatype.DS, dsrdata, 0,
                               len(dsrdata))

def _find_candidate_keys(keys, rrsig):
    candidate_keys=[]
    value = keys.get(rrsig.signer)
    if value is None:
        return None
    if isinstance(value, dns.node.Node):
        try:
            rdataset = value.find_rdataset(dns.rdataclass.IN,
                                           dns.rdatatype.DNSKEY)
        except KeyError:
            return None
    else:
        rdataset = value
    for rdata in rdataset:
        if rdata.algorithm == rrsig.algorithm and \
               key_id(rdata) == rrsig.key_tag:
            candidate_keys.append(rdata)
    return candidate_keys

def _is_rsa(algorithm):
    return algorithm in (RSAMD5, RSASHA1,
                         RSASHA1NSEC3SHA1, RSASHA256,
                         RSASHA512)

def _is_dsa(algorithm):
    return algorithm in (DSA, DSANSEC3SHA1)

def _is_ecdsa(algorithm):
    return _have_ecdsa and (algorithm in (ECDSAP256SHA256, ECDSAP384SHA384))

def _is_md5(algorithm):
    return algorithm == RSAMD5

def _is_sha1(algorithm):
    return algorithm in (DSA, RSASHA1,
                         DSANSEC3SHA1, RSASHA1NSEC3SHA1)

def _is_sha256(algorithm):
    return algorithm in (RSASHA256, ECDSAP256SHA256)

def _is_sha384(algorithm):
    return algorithm == ECDSAP384SHA384

def _is_sha512(algorithm):
    return algorithm == RSASHA512

def _make_hash(algorithm):
    if _is_md5(algorithm):
        return dns.hash.get('MD5')()
    if _is_sha1(algorithm):
        return dns.hash.get('SHA1')()
    if _is_sha256(algorithm):
        return dns.hash.get('SHA256')()
    if _is_sha384(algorithm):
        return dns.hash.get('SHA384')()
    if _is_sha512(algorithm):
        return dns.hash.get('SHA512')()
    raise ValidationFailure, 'unknown hash for algorithm %u' % algorithm

def _make_algorithm_id(algorithm):
    if _is_md5(algorithm):
        oid = [0x2a, 0x86, 0x48, 0x86, 0xf7, 0x0d, 0x02, 0x05]
    elif _is_sha1(algorithm):
        oid = [0x2b, 0x0e, 0x03, 0x02, 0x1a]
    elif _is_sha256(algorithm):
        oid = [0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x01]
    elif _is_sha512(algorithm):
        oid = [0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x03]
    else:
        raise ValidationFailure, 'unknown algorithm %u' % algorithm
    olen = len(oid)
    dlen = _make_hash(algorithm).digest_size
    idbytes = [0x30] + [8 + olen + dlen] + \
              [0x30, olen + 4] + [0x06, olen] + oid + \
              [0x05, 0x00] + [0x04, dlen]
    return ''.join(map(chr, idbytes))

def _validate_rrsig(rrset, rrsig, keys, origin=None, now=None):
    """Validate an RRset against a single signature rdata

    The owner name of the rrsig is assumed to be the same as the owner name
    of the rrset.

    @param rrset: The RRset to validate
    @type rrset: dns.rrset.RRset or (dns.name.Name, dns.rdataset.Rdataset)
    tuple
    @param rrsig: The signature rdata
    @type rrsig: dns.rrset.Rdata
    @param keys: The key dictionary.
    @type keys: a dictionary keyed by dns.name.Name with node or rdataset values
    @param origin: The origin to use for relative names
    @type origin: dns.name.Name or None
    @param now: The time to use when validating the signatures.  The default
    is the current time.
    @type now: int
    """

    if isinstance(origin, (str, unicode)):
        origin = dns.name.from_text(origin, dns.name.root)

    for candidate_key in _find_candidate_keys(keys, rrsig):
        if not candidate_key:
            raise ValidationFailure, 'unknown key'

        # For convenience, allow the rrset to be specified as a (name, rdataset)
        # tuple as well as a proper rrset
        if isinstance(rrset, tuple):
            rrname = rrset[0]
            rdataset = rrset[1]
        else:
            rrname = rrset.name
            rdataset = rrset

        if now is None:
            now = time.time()
        if rrsig.expiration < now:
            raise ValidationFailure, 'expired'
        if rrsig.inception > now:
            raise ValidationFailure, 'not yet valid'

        hash = _make_hash(rrsig.algorithm)

        if _is_rsa(rrsig.algorithm):
            keyptr = candidate_key.key
            (bytes,) = struct.unpack('!B', keyptr[0:1])
            keyptr = keyptr[1:]
            if bytes == 0:
                (bytes,) = struct.unpack('!H', keyptr[0:2])
                keyptr = keyptr[2:]
            rsa_e = keyptr[0:bytes]
            rsa_n = keyptr[bytes:]
            keylen = len(rsa_n) * 8
            pubkey = Crypto.PublicKey.RSA.construct(
                (Crypto.Util.number.bytes_to_long(rsa_n),
                 Crypto.Util.number.bytes_to_long(rsa_e)))
            sig = (Crypto.Util.number.bytes_to_long(rrsig.signature),)
        elif _is_dsa(rrsig.algorithm):
            keyptr = candidate_key.key
            (t,) = struct.unpack('!B', keyptr[0:1])
            keyptr = keyptr[1:]
            octets = 64 + t * 8
            dsa_q = keyptr[0:20]
            keyptr = keyptr[20:]
            dsa_p = keyptr[0:octets]
            keyptr = keyptr[octets:]
            dsa_g = keyptr[0:octets]
            keyptr = keyptr[octets:]
            dsa_y = keyptr[0:octets]
            pubkey = Crypto.PublicKey.DSA.construct(
                (Crypto.Util.number.bytes_to_long(dsa_y),
                 Crypto.Util.number.bytes_to_long(dsa_g),
                 Crypto.Util.number.bytes_to_long(dsa_p),
                 Crypto.Util.number.bytes_to_long(dsa_q)))
            (dsa_r, dsa_s) = struct.unpack('!20s20s', rrsig.signature[1:])
            sig = (Crypto.Util.number.bytes_to_long(dsa_r),
                   Crypto.Util.number.bytes_to_long(dsa_s))
        elif _is_ecdsa(rrsig.algorithm):
            if rrsig.algorithm == ECDSAP256SHA256:
                curve = ecdsa.curves.NIST256p
                key_len = 32
                digest_len = 32
            elif rrsig.algorithm == ECDSAP384SHA384:
                curve = ecdsa.curves.NIST384p
                key_len = 48
                digest_len = 48
            else:
                # shouldn't happen
                raise ValidationFailure, 'unknown ECDSA curve'
            keyptr = candidate_key.key
            x = Crypto.Util.number.bytes_to_long(keyptr[0:key_len])
            y = Crypto.Util.number.bytes_to_long(keyptr[key_len:key_len * 2])
            assert ecdsa.ecdsa.point_is_valid(curve.generator, x, y)
            point = ecdsa.ellipticcurve.Point(curve.curve, x, y, curve.order)
            verifying_key = ecdsa.keys.VerifyingKey.from_public_point(point,
                                                                      curve)
            pubkey = ECKeyWrapper(verifying_key, key_len)
            r = rrsig.signature[:key_len]
            s = rrsig.signature[key_len:]
            sig = ecdsa.ecdsa.Signature(Crypto.Util.number.bytes_to_long(r),
                                        Crypto.Util.number.bytes_to_long(s))
        else:
            raise ValidationFailure, 'unknown algorithm %u' % rrsig.algorithm

        hash.update(_to_rdata(rrsig, origin)[:18])
        hash.update(rrsig.signer.to_digestable(origin))

        if rrsig.labels < len(rrname) - 1:
            suffix = rrname.split(rrsig.labels + 1)[1]
            rrname = dns.name.from_text('*', suffix)
        rrnamebuf = rrname.to_digestable(origin)
        rrfixed = struct.pack('!HHI', rdataset.rdtype, rdataset.rdclass,
                              rrsig.original_ttl)
        rrlist = sorted(rdataset);
        for rr in rrlist:
            hash.update(rrnamebuf)
            hash.update(rrfixed)
            rrdata = rr.to_digestable(origin)
            rrlen = struct.pack('!H', len(rrdata))
            hash.update(rrlen)
            hash.update(rrdata)

        digest = hash.digest()

        if _is_rsa(rrsig.algorithm):
            # PKCS1 algorithm identifier goop
            digest = _make_algorithm_id(rrsig.algorithm) + digest
            padlen = keylen // 8 - len(digest) - 3
            digest = chr(0) + chr(1) + chr(0xFF) * padlen + chr(0) + digest
        elif _is_dsa(rrsig.algorithm) or _is_ecdsa(rrsig.algorithm):
            pass
        else:
            # Raise here for code clarity; this won't actually ever happen
            # since if the algorithm is really unknown we'd already have
            # raised an exception above
            raise ValidationFailure, 'unknown algorithm %u' % rrsig.algorithm

        if pubkey.verify(digest, sig):
            return
    raise ValidationFailure, 'verify failure'

def _validate(rrset, rrsigset, keys, origin=None, now=None):
    """Validate an RRset

    @param rrset: The RRset to validate
    @type rrset: dns.rrset.RRset or (dns.name.Name, dns.rdataset.Rdataset)
    tuple
    @param rrsigset: The signature RRset
    @type rrsigset: dns.rrset.RRset or (dns.name.Name, dns.rdataset.Rdataset)
    tuple
    @param keys: The key dictionary.
    @type keys: a dictionary keyed by dns.name.Name with node or rdataset values
    @param origin: The origin to use for relative names
    @type origin: dns.name.Name or None
    @param now: The time to use when validating the signatures.  The default
    is the current time.
    @type now: int
    """

    if isinstance(origin, (str, unicode)):
        origin = dns.name.from_text(origin, dns.name.root)

    if isinstance(rrset, tuple):
        rrname = rrset[0]
    else:
        rrname = rrset.name

    if isinstance(rrsigset, tuple):
        rrsigname = rrsigset[0]
        rrsigrdataset = rrsigset[1]
    else:
        rrsigname = rrsigset.name
        rrsigrdataset = rrsigset

    rrname = rrname.choose_relativity(origin)
    rrsigname = rrname.choose_relativity(origin)
    if rrname != rrsigname:
        raise ValidationFailure, "owner names do not match"

    for rrsig in rrsigrdataset:
        try:
            _validate_rrsig(rrset, rrsig, keys, origin, now)
            return
        except ValidationFailure, e:
            pass
    raise ValidationFailure, "no RRSIGs validated"

def _need_pycrypto(*args, **kwargs):
    raise NotImplementedError, "DNSSEC validation requires pycrypto"

try:
    import Crypto.PublicKey.RSA
    import Crypto.PublicKey.DSA
    import Crypto.Util.number
    validate = _validate
    validate_rrsig = _validate_rrsig
except ImportError:
    validate = _need_pycrypto
    validate_rrsig = _need_pycrypto

try:
    import ecdsa
    import ecdsa.ecdsa
    import ecdsa.ellipticcurve
    import ecdsa.keys
    _have_ecdsa = True

    class ECKeyWrapper(object):
        def __init__(self, key, key_len):
            self.key = key
            self.key_len = key_len
        def verify(self, digest, sig):
            diglong = Crypto.Util.number.bytes_to_long(digest)
            return self.key.pubkey.verifies(diglong, sig)

except ImportError:
    _have_ecdsa = False

########NEW FILE########
__FILENAME__ = e164
# Copyright (C) 2006, 2007, 2009, 2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS E.164 helpers

@var public_enum_domain: The DNS public ENUM domain, e164.arpa.
@type public_enum_domain: dns.name.Name object
"""

import dns.exception
import dns.name
import dns.resolver

public_enum_domain = dns.name.from_text('e164.arpa.')

def from_e164(text, origin=public_enum_domain):
    """Convert an E.164 number in textual form into a Name object whose
    value is the ENUM domain name for that number.
    @param text: an E.164 number in textual form.
    @type text: str
    @param origin: The domain in which the number should be constructed.
    The default is e164.arpa.
    @type origin: dns.name.Name object or None
    @rtype: dns.name.Name object
    """
    parts = [d for d in text if d.isdigit()]
    parts.reverse()
    return dns.name.from_text('.'.join(parts), origin=origin)

def to_e164(name, origin=public_enum_domain, want_plus_prefix=True):
    """Convert an ENUM domain name into an E.164 number.
    @param name: the ENUM domain name.
    @type name: dns.name.Name object.
    @param origin: A domain containing the ENUM domain name.  The
    name is relativized to this domain before being converted to text.
    @type origin: dns.name.Name object or None
    @param want_plus_prefix: if True, add a '+' to the beginning of the
    returned number.
    @rtype: str
    """
    if not origin is None:
        name = name.relativize(origin)
    dlabels = [d for d in name.labels if (d.isdigit() and len(d) == 1)]
    if len(dlabels) != len(name.labels):
        raise dns.exception.SyntaxError('non-digit labels in ENUM domain name')
    dlabels.reverse()
    text = ''.join(dlabels)
    if want_plus_prefix:
        text = '+' + text
    return text

def query(number, domains, resolver=None):
    """Look for NAPTR RRs for the specified number in the specified domains.

    e.g. lookup('16505551212', ['e164.dnspython.org.', 'e164.arpa.'])
    """
    if resolver is None:
        resolver = dns.resolver.get_default_resolver()
    for domain in domains:
        if isinstance(domain, (str, unicode)):
            domain = dns.name.from_text(domain)
        qname = dns.e164.from_e164(number, domain)
        try:
            return resolver.query(qname, 'NAPTR')
        except dns.resolver.NXDOMAIN:
            pass
    raise dns.resolver.NXDOMAIN

########NEW FILE########
__FILENAME__ = edns
# Copyright (C) 2009, 2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""EDNS Options"""

NSID = 3

class Option(object):
    """Base class for all EDNS option types.
    """

    def __init__(self, otype):
        """Initialize an option.
        @param otype: The rdata type
        @type otype: int
        """
        self.otype = otype

    def to_wire(self, file):
        """Convert an option to wire format.
        """
        raise NotImplementedError

    def from_wire(cls, otype, wire, current, olen):
        """Build an EDNS option object from wire format

        @param otype: The option type
        @type otype: int
        @param wire: The wire-format message
        @type wire: string
        @param current: The offet in wire of the beginning of the rdata.
        @type current: int
        @param olen: The length of the wire-format option data
        @type olen: int
        @rtype: dns.edns.Option instance"""
        raise NotImplementedError

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        """Compare an EDNS option with another option of the same type.
        Return < 0 if self < other, 0 if self == other, and > 0 if self > other.
        """
        raise NotImplementedError

    def __eq__(self, other):
        if not isinstance(other, Option):
            return False
        if self.otype != other.otype:
            return False
        return self._cmp(other) == 0

    def __ne__(self, other):
        if not isinstance(other, Option):
            return False
        if self.otype != other.otype:
            return False
        return self._cmp(other) != 0

    def __lt__(self, other):
        if not isinstance(other, Option) or \
               self.otype != other.otype:
            return NotImplemented
        return self._cmp(other) < 0

    def __le__(self, other):
        if not isinstance(other, Option) or \
               self.otype != other.otype:
            return NotImplemented
        return self._cmp(other) <= 0

    def __ge__(self, other):
        if not isinstance(other, Option) or \
               self.otype != other.otype:
            return NotImplemented
        return self._cmp(other) >= 0

    def __gt__(self, other):
        if not isinstance(other, Option) or \
               self.otype != other.otype:
            return NotImplemented
        return self._cmp(other) > 0


class GenericOption(Option):
    """Generate Rdata Class

    This class is used for EDNS option types for which we have no better
    implementation.
    """

    def __init__(self, otype, data):
        super(GenericOption, self).__init__(otype)
        self.data = data

    def to_wire(self, file):
        file.write(self.data)

    def from_wire(cls, otype, wire, current, olen):
        return cls(otype, wire[current : current + olen])

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
	return cmp(self.data, other.data)

_type_to_class = {
}

def get_option_class(otype):
    cls = _type_to_class.get(otype)
    if cls is None:
        cls = GenericOption
    return cls

def option_from_wire(otype, wire, current, olen):
    """Build an EDNS option object from wire format

    @param otype: The option type
    @type otype: int
    @param wire: The wire-format message
    @type wire: string
    @param current: The offet in wire of the beginning of the rdata.
    @type current: int
    @param olen: The length of the wire-format option data
    @type olen: int
    @rtype: dns.edns.Option instance"""

    cls = get_option_class(otype)
    return cls.from_wire(otype, wire, current, olen)

########NEW FILE########
__FILENAME__ = entropy
# Copyright (C) 2009, 2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import os
import time
try:
    import threading as _threading
except ImportError:
    import dummy_threading as _threading

class EntropyPool(object):
    def __init__(self, seed=None):
        self.pool_index = 0
        self.digest = None
        self.next_byte = 0
        self.lock = _threading.Lock()
        try:
            import hashlib
            self.hash = hashlib.sha1()
            self.hash_len = 20
        except:
            try:
                import sha
                self.hash = sha.new()
                self.hash_len = 20
            except:
                import md5
                self.hash = md5.new()
                self.hash_len = 16
        self.pool = '\0' * self.hash_len
        if not seed is None:
            self.stir(seed)
            self.seeded = True
        else:
            self.seeded = False

    def stir(self, entropy, already_locked=False):
        if not already_locked:
            self.lock.acquire()
        try:
            bytes = [ord(c) for c in self.pool]
            for c in entropy:
                if self.pool_index == self.hash_len:
                    self.pool_index = 0
                b = ord(c) & 0xff
                bytes[self.pool_index] ^= b
                self.pool_index += 1
            self.pool = ''.join([chr(c) for c in bytes])
        finally:
            if not already_locked:
                self.lock.release()

    def _maybe_seed(self):
        if not self.seeded:
            try:
                seed = os.urandom(16)
            except:
                try:
                    r = file('/dev/urandom', 'r', 0)
                    try:
                        seed = r.read(16)
                    finally:
                        r.close()
                except:
                    seed = str(time.time())
            self.seeded = True
            self.stir(seed, True)

    def random_8(self):
        self.lock.acquire()
        self._maybe_seed()
        try:
            if self.digest is None or self.next_byte == self.hash_len:
                self.hash.update(self.pool)
                self.digest = self.hash.digest()
                self.stir(self.digest, True)
                self.next_byte = 0
            value = ord(self.digest[self.next_byte])
            self.next_byte += 1
        finally:
            self.lock.release()
        return value

    def random_16(self):
        return self.random_8() * 256 + self.random_8()

    def random_32(self):
        return self.random_16() * 65536 + self.random_16()

    def random_between(self, first, last):
        size = last - first + 1
        if size > 4294967296L:
            raise ValueError('too big')
        if size > 65536:
            rand = self.random_32
            max = 4294967295L
        elif size > 256:
            rand = self.random_16
            max = 65535
        else:
            rand = self.random_8
            max = 255
	return (first + size * rand() // (max + 1))

pool = EntropyPool()

def random_16():
    return pool.random_16()

def between(first, last):
    return pool.random_between(first, last)

########NEW FILE########
__FILENAME__ = exception
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""Common DNS Exceptions."""

class DNSException(Exception):
    """Abstract base class shared by all dnspython exceptions."""
    pass

class FormError(DNSException):
    """DNS message is malformed."""
    pass

class SyntaxError(DNSException):
    """Text input is malformed."""
    pass

class UnexpectedEnd(SyntaxError):
    """Raised if text input ends unexpectedly."""
    pass

class TooBig(DNSException):
    """The message is too big."""
    pass

class Timeout(DNSException):
    """The operation timed out."""
    pass

########NEW FILE########
__FILENAME__ = flags
# Copyright (C) 2001-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS Message Flags."""

# Standard DNS flags

QR = 0x8000
AA = 0x0400
TC = 0x0200
RD = 0x0100
RA = 0x0080
AD = 0x0020
CD = 0x0010

# EDNS flags

DO = 0x8000

_by_text = {
    'QR' : QR,
    'AA' : AA,
    'TC' : TC,
    'RD' : RD,
    'RA' : RA,
    'AD' : AD,
    'CD' : CD
}

_edns_by_text = {
    'DO' : DO
}


# We construct the inverse mappings programmatically to ensure that we
# cannot make any mistakes (e.g. omissions, cut-and-paste errors) that
# would cause the mappings not to be true inverses.

_by_value = dict([(y, x) for x, y in _by_text.iteritems()])

_edns_by_value = dict([(y, x) for x, y in _edns_by_text.iteritems()])

def _order_flags(table):
    order = list(table.iteritems())
    order.sort()
    order.reverse()
    return order

_flags_order = _order_flags(_by_value)

_edns_flags_order = _order_flags(_edns_by_value)

def _from_text(text, table):
    flags = 0
    tokens = text.split()
    for t in tokens:
        flags = flags | table[t.upper()]
    return flags

def _to_text(flags, table, order):
    text_flags = []
    for k, v in order:
        if flags & k != 0:
            text_flags.append(v)
    return ' '.join(text_flags)

def from_text(text):
    """Convert a space-separated list of flag text values into a flags
    value.
    @rtype: int"""

    return _from_text(text, _by_text)

def to_text(flags):
    """Convert a flags value into a space-separated list of flag text
    values.
    @rtype: string"""

    return _to_text(flags, _by_value, _flags_order)
    

def edns_from_text(text):
    """Convert a space-separated list of EDNS flag text values into a EDNS
    flags value.
    @rtype: int"""

    return _from_text(text, _edns_by_text)

def edns_to_text(flags):
    """Convert an EDNS flags value into a space-separated list of EDNS flag
    text values.
    @rtype: string"""

    return _to_text(flags, _edns_by_value, _edns_flags_order)

########NEW FILE########
__FILENAME__ = grange
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS GENERATE range conversion."""

import dns

def from_text(text):
    """Convert the text form of a range in a GENERATE statement to an
    integer.

    @param text: the textual range
    @type text: string
    @return: The start, stop and step values.
    @rtype: tuple
    """
    # TODO, figure out the bounds on start, stop and step.

    import pdb
    step = 1
    cur = ''
    state = 0
    # state   0 1 2 3 4
    #         x - y / z
    for c in text:
        if c == '-' and state == 0:
            start = int(cur)
            cur = ''
            state = 2
        elif c == '/':
            stop = int(cur)
            cur = ''
            state = 4
        elif c.isdigit():
            cur += c
        else:
            raise dns.exception.SyntaxError("Could not parse %s" % (c))

    if state in (1, 3):
        raise dns.exception.SyntaxError

    if state == 2:
        stop = int(cur)

    if state == 4:
        step = int(cur)

    assert step >= 1
    assert start >= 0
    assert start <= stop
    # TODO, can start == stop?

    return (start, stop, step)

########NEW FILE########
__FILENAME__ = hash
# Copyright (C) 2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""Hashing backwards compatibility wrapper"""

import sys

_hashes = None

def _need_later_python(alg):
    def func(*args, **kwargs):
        raise NotImplementedError("TSIG algorithm " + alg +
                                  " requires Python 2.5.2 or later")
    return func

def _setup():
    global _hashes
    _hashes = {}
    try:
        import hashlib
        _hashes['MD5'] = hashlib.md5
        _hashes['SHA1'] = hashlib.sha1
        _hashes['SHA224'] = hashlib.sha224
        _hashes['SHA256'] = hashlib.sha256
        if sys.hexversion >= 0x02050200:
            _hashes['SHA384'] = hashlib.sha384
            _hashes['SHA512'] = hashlib.sha512
        else:
            _hashes['SHA384'] = _need_later_python('SHA384')
            _hashes['SHA512'] = _need_later_python('SHA512')

        if sys.hexversion < 0x02050000:
            # hashlib doesn't conform to PEP 247: API for
            # Cryptographic Hash Functions, which hmac before python
            # 2.5 requires, so add the necessary items.
            class HashlibWrapper:
                def __init__(self, basehash):
                    self.basehash = basehash
                    self.digest_size = self.basehash().digest_size

                def new(self, *args, **kwargs):
                    return self.basehash(*args, **kwargs)

            for name in _hashes:
                _hashes[name] = HashlibWrapper(_hashes[name])

    except ImportError:
        import md5, sha
        _hashes['MD5'] =  md5
        _hashes['SHA1'] = sha

def get(algorithm):
    if _hashes is None:
        _setup()
    return _hashes[algorithm.upper()]

########NEW FILE########
__FILENAME__ = inet
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""Generic Internet address helper functions."""

import socket

import dns.ipv4
import dns.ipv6


# We assume that AF_INET is always defined.

AF_INET = socket.AF_INET

# AF_INET6 might not be defined in the socket module, but we need it.
# We'll try to use the socket module's value, and if it doesn't work,
# we'll use our own value.

try:
    AF_INET6 = socket.AF_INET6
except AttributeError:
    AF_INET6 = 9999

def inet_pton(family, text):
    """Convert the textual form of a network address into its binary form.

    @param family: the address family
    @type family: int
    @param text: the textual address
    @type text: string
    @raises NotImplementedError: the address family specified is not
    implemented.
    @rtype: string
    """
    
    if family == AF_INET:
        return dns.ipv4.inet_aton(text)
    elif family == AF_INET6:
        return dns.ipv6.inet_aton(text)
    else:
        raise NotImplementedError

def inet_ntop(family, address):
    """Convert the binary form of a network address into its textual form.

    @param family: the address family
    @type family: int
    @param address: the binary address
    @type address: string
    @raises NotImplementedError: the address family specified is not
    implemented.
    @rtype: string
    """
    if family == AF_INET:
        return dns.ipv4.inet_ntoa(address)
    elif family == AF_INET6:
        return dns.ipv6.inet_ntoa(address)
    else:
        raise NotImplementedError

def af_for_address(text):
    """Determine the address family of a textual-form network address.

    @param text: the textual address
    @type text: string
    @raises ValueError: the address family cannot be determined from the input.
    @rtype: int
    """
    try:
        junk = dns.ipv4.inet_aton(text)
        return AF_INET
    except:
        try:
            junk = dns.ipv6.inet_aton(text)
            return AF_INET6
        except:
            raise ValueError

def is_multicast(text):
    """Is the textual-form network address a multicast address?

    @param text: the textual address
    @raises ValueError: the address family cannot be determined from the input.
    @rtype: bool
    """
    try:
        first = ord(dns.ipv4.inet_aton(text)[0])
        return (first >= 224 and first <= 239)
    except:
        try:
            first = ord(dns.ipv6.inet_aton(text)[0])
            return (first == 255)
        except:
            raise ValueError
    

########NEW FILE########
__FILENAME__ = ipv4
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""IPv4 helper functions."""

import struct

import dns.exception

def inet_ntoa(address):
    """Convert an IPv4 address in network form to text form.

    @param address: The IPv4 address
    @type address: string
    @returns: string
    """
    if len(address) != 4:
        raise dns.exception.SyntaxError
    return '%u.%u.%u.%u' % (ord(address[0]), ord(address[1]),
                            ord(address[2]), ord(address[3]))

def inet_aton(text):
    """Convert an IPv4 address in text form to network form.

    @param text: The IPv4 address
    @type text: string
    @returns: string
    """
    parts = text.split('.')
    if len(parts) != 4:
        raise dns.exception.SyntaxError
    for part in parts:
        if not part.isdigit():
            raise dns.exception.SyntaxError
        if len(part) > 1 and part[0] == '0':
            # No leading zeros
            raise dns.exception.SyntaxError
    try:
        bytes = [int(part) for part in parts]
        return struct.pack('BBBB', *bytes)
    except:
        raise dns.exception.SyntaxError

########NEW FILE########
__FILENAME__ = ipv6
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""IPv6 helper functions."""

import re

import dns.exception
import dns.ipv4

_leading_zero = re.compile(r'0+([0-9a-f]+)')

def inet_ntoa(address):
    """Convert a network format IPv6 address into text.

    @param address: the binary address
    @type address: string
    @rtype: string
    @raises ValueError: the address isn't 16 bytes long
    """

    if len(address) != 16:
        raise ValueError("IPv6 addresses are 16 bytes long")
    hex = address.encode('hex_codec')
    chunks = []
    i = 0
    l = len(hex)
    while i < l:
        chunk = hex[i : i + 4]
        # strip leading zeros.  we do this with an re instead of
        # with lstrip() because lstrip() didn't support chars until
        # python 2.2.2
        m = _leading_zero.match(chunk)
        if not m is None:
            chunk = m.group(1)
        chunks.append(chunk)
        i += 4
    #
    # Compress the longest subsequence of 0-value chunks to ::
    #
    best_start = 0
    best_len = 0
    start = -1
    last_was_zero = False
    for i in xrange(8):
        if chunks[i] != '0':
            if last_was_zero:
                end = i
                current_len = end - start
                if current_len > best_len:
                    best_start = start
                    best_len = current_len
                last_was_zero = False
        elif not last_was_zero:
            start = i
            last_was_zero = True
    if last_was_zero:
        end = 8
        current_len = end - start
        if current_len > best_len:
            best_start = start
            best_len = current_len
    if best_len > 1:
        if best_start == 0 and \
           (best_len == 6 or
            best_len == 5 and chunks[5] == 'ffff'):
            # We have an embedded IPv4 address
            if best_len == 6:
                prefix = '::'
            else:
                prefix = '::ffff:'
            hex = prefix + dns.ipv4.inet_ntoa(address[12:])
        else:
            hex = ':'.join(chunks[:best_start]) + '::' + \
                  ':'.join(chunks[best_start + best_len:])
    else:
        hex = ':'.join(chunks)
    return hex

_v4_ending = re.compile(r'(.*):(\d+\.\d+\.\d+\.\d+)$')
_colon_colon_start = re.compile(r'::.*')
_colon_colon_end = re.compile(r'.*::$')

def inet_aton(text):
    """Convert a text format IPv6 address into network format.

    @param text: the textual address
    @type text: string
    @rtype: string
    @raises dns.exception.SyntaxError: the text was not properly formatted
    """

    #
    # Our aim here is not something fast; we just want something that works.
    #

    if text == '::':
        text = '0::'
    #
    # Get rid of the icky dot-quad syntax if we have it.
    #
    m = _v4_ending.match(text)
    if not m is None:
        b = dns.ipv4.inet_aton(m.group(2))
        text = "%s:%02x%02x:%02x%02x" % (m.group(1), ord(b[0]), ord(b[1]),
                                         ord(b[2]), ord(b[3]))
    #
    # Try to turn '::<whatever>' into ':<whatever>'; if no match try to
    # turn '<whatever>::' into '<whatever>:'
    #
    m = _colon_colon_start.match(text)
    if not m is None:
        text = text[1:]
    else:
        m = _colon_colon_end.match(text)
        if not m is None:
            text = text[:-1]
    #
    # Now canonicalize into 8 chunks of 4 hex digits each
    #
    chunks = text.split(':')
    l = len(chunks)
    if l > 8:
        raise dns.exception.SyntaxError
    seen_empty = False
    canonical = []
    for c in chunks:
        if c == '':
            if seen_empty:
                raise dns.exception.SyntaxError
            seen_empty = True
            for i in xrange(0, 8 - l + 1):
                canonical.append('0000')
        else:
            lc = len(c)
            if lc > 4:
                raise dns.exception.SyntaxError
            if lc != 4:
                c = ('0' * (4 - lc)) + c
            canonical.append(c)
    if l < 8 and not seen_empty:
        raise dns.exception.SyntaxError
    text = ''.join(canonical)

    #
    # Finally we can go to binary.
    #
    try:
        return text.decode('hex_codec')
    except TypeError:
        raise dns.exception.SyntaxError

########NEW FILE########
__FILENAME__ = message
# Copyright (C) 2001-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS Messages"""

import cStringIO
import random
import struct
import sys
import time

import dns.edns
import dns.exception
import dns.flags
import dns.name
import dns.opcode
import dns.entropy
import dns.rcode
import dns.rdata
import dns.rdataclass
import dns.rdatatype
import dns.rrset
import dns.renderer
import dns.tsig
import dns.wiredata

class ShortHeader(dns.exception.FormError):
    """Raised if the DNS packet passed to from_wire() is too short."""
    pass

class TrailingJunk(dns.exception.FormError):
    """Raised if the DNS packet passed to from_wire() has extra junk
    at the end of it."""
    pass

class UnknownHeaderField(dns.exception.DNSException):
    """Raised if a header field name is not recognized when converting from
    text into a message."""
    pass

class BadEDNS(dns.exception.FormError):
    """Raised if an OPT record occurs somewhere other than the start of
    the additional data section."""
    pass

class BadTSIG(dns.exception.FormError):
    """Raised if a TSIG record occurs somewhere other than the end of
    the additional data section."""
    pass

class UnknownTSIGKey(dns.exception.DNSException):
    """Raised if we got a TSIG but don't know the key."""
    pass

class Message(object):
    """A DNS message.

    @ivar id: The query id; the default is a randomly chosen id.
    @type id: int
    @ivar flags: The DNS flags of the message.  @see: RFC 1035 for an
    explanation of these flags.
    @type flags: int
    @ivar question: The question section.
    @type question: list of dns.rrset.RRset objects
    @ivar answer: The answer section.
    @type answer: list of dns.rrset.RRset objects
    @ivar authority: The authority section.
    @type authority: list of dns.rrset.RRset objects
    @ivar additional: The additional data section.
    @type additional: list of dns.rrset.RRset objects
    @ivar edns: The EDNS level to use.  The default is -1, no Edns.
    @type edns: int
    @ivar ednsflags: The EDNS flags
    @type ednsflags: long
    @ivar payload: The EDNS payload size.  The default is 0.
    @type payload: int
    @ivar options: The EDNS options
    @type options: list of dns.edns.Option objects
    @ivar request_payload: The associated request's EDNS payload size.
    @type request_payload: int
    @ivar keyring: The TSIG keyring to use.  The default is None.
    @type keyring: dict
    @ivar keyname: The TSIG keyname to use.  The default is None.
    @type keyname: dns.name.Name object
    @ivar keyalgorithm: The TSIG algorithm to use; defaults to
    dns.tsig.default_algorithm.  Constants for TSIG algorithms are defined
    in dns.tsig, and the currently implemented algorithms are
    HMAC_MD5, HMAC_SHA1, HMAC_SHA224, HMAC_SHA256, HMAC_SHA384, and
    HMAC_SHA512.
    @type keyalgorithm: string
    @ivar request_mac: The TSIG MAC of the request message associated with
    this message; used when validating TSIG signatures.   @see: RFC 2845 for
    more information on TSIG fields.
    @type request_mac: string
    @ivar fudge: TSIG time fudge; default is 300 seconds.
    @type fudge: int
    @ivar original_id: TSIG original id; defaults to the message's id
    @type original_id: int
    @ivar tsig_error: TSIG error code; default is 0.
    @type tsig_error: int
    @ivar other_data: TSIG other data.
    @type other_data: string
    @ivar mac: The TSIG MAC for this message.
    @type mac: string
    @ivar xfr: Is the message being used to contain the results of a DNS
    zone transfer?  The default is False.
    @type xfr: bool
    @ivar origin: The origin of the zone in messages which are used for
    zone transfers or for DNS dynamic updates.  The default is None.
    @type origin: dns.name.Name object
    @ivar tsig_ctx: The TSIG signature context associated with this
    message.  The default is None.
    @type tsig_ctx: hmac.HMAC object
    @ivar had_tsig: Did the message decoded from wire format have a TSIG
    signature?
    @type had_tsig: bool
    @ivar multi: Is this message part of a multi-message sequence?  The
    default is false.  This variable is used when validating TSIG signatures
    on messages which are part of a zone transfer.
    @type multi: bool
    @ivar first: Is this message standalone, or the first of a multi
    message sequence?  This variable is used when validating TSIG signatures
    on messages which are part of a zone transfer.
    @type first: bool
    @ivar index: An index of rrsets in the message.  The index key is
    (section, name, rdclass, rdtype, covers, deleting).  Indexing can be
    disabled by setting the index to None.
    @type index: dict
    """

    def __init__(self, id=None):
        if id is None:
            self.id = dns.entropy.random_16()
        else:
            self.id = id
        self.flags = 0
        self.question = []
        self.answer = []
        self.authority = []
        self.additional = []
        self.edns = -1
        self.ednsflags = 0
        self.payload = 0
        self.options = []
        self.request_payload = 0
        self.keyring = None
        self.keyname = None
        self.keyalgorithm = dns.tsig.default_algorithm
        self.request_mac = ''
        self.other_data = ''
        self.tsig_error = 0
        self.fudge = 300
        self.original_id = self.id
        self.mac = ''
        self.xfr = False
        self.origin = None
        self.tsig_ctx = None
        self.had_tsig = False
        self.multi = False
        self.first = True
        self.index = {}

    def __repr__(self):
        return '<DNS message, ID ' + `self.id` + '>'

    def __str__(self):
        return self.to_text()

    def to_text(self,  origin=None, relativize=True, **kw):
        """Convert the message to text.

        The I{origin}, I{relativize}, and any other keyword
        arguments are passed to the rrset to_wire() method.

        @rtype: string
        """

        s = cStringIO.StringIO()
        print >> s, 'id %d' % self.id
        print >> s, 'opcode %s' % \
              dns.opcode.to_text(dns.opcode.from_flags(self.flags))
        rc = dns.rcode.from_flags(self.flags, self.ednsflags)
        print >> s, 'rcode %s' % dns.rcode.to_text(rc)
        print >> s, 'flags %s' % dns.flags.to_text(self.flags)
        if self.edns >= 0:
            print >> s, 'edns %s' % self.edns
            if self.ednsflags != 0:
                print >> s, 'eflags %s' % \
                      dns.flags.edns_to_text(self.ednsflags)
            print >> s, 'payload', self.payload
        is_update = dns.opcode.is_update(self.flags)
        if is_update:
            print >> s, ';ZONE'
        else:
            print >> s, ';QUESTION'
        for rrset in self.question:
            print >> s, rrset.to_text(origin, relativize, **kw)
        if is_update:
            print >> s, ';PREREQ'
        else:
            print >> s, ';ANSWER'
        for rrset in self.answer:
            print >> s, rrset.to_text(origin, relativize, **kw)
        if is_update:
            print >> s, ';UPDATE'
        else:
            print >> s, ';AUTHORITY'
        for rrset in self.authority:
            print >> s, rrset.to_text(origin, relativize, **kw)
        print >> s, ';ADDITIONAL'
        for rrset in self.additional:
            print >> s, rrset.to_text(origin, relativize, **kw)
        #
        # We strip off the final \n so the caller can print the result without
        # doing weird things to get around eccentricities in Python print
        # formatting
        #
        return s.getvalue()[:-1]

    def __eq__(self, other):
        """Two messages are equal if they have the same content in the
        header, question, answer, and authority sections.
        @rtype: bool"""
        if not isinstance(other, Message):
            return False
        if self.id != other.id:
            return False
        if self.flags != other.flags:
            return False
        for n in self.question:
            if n not in other.question:
                return False
        for n in other.question:
            if n not in self.question:
                return False
        for n in self.answer:
            if n not in other.answer:
                return False
        for n in other.answer:
            if n not in self.answer:
                return False
        for n in self.authority:
            if n not in other.authority:
                return False
        for n in other.authority:
            if n not in self.authority:
                return False
        return True

    def __ne__(self, other):
        """Are two messages not equal?
        @rtype: bool"""
        return not self.__eq__(other)

    def is_response(self, other):
        """Is other a response to self?
        @rtype: bool"""
        if other.flags & dns.flags.QR == 0 or \
           self.id != other.id or \
           dns.opcode.from_flags(self.flags) != \
           dns.opcode.from_flags(other.flags):
            return False
        if dns.rcode.from_flags(other.flags, other.ednsflags) != \
               dns.rcode.NOERROR:
            return True
        if dns.opcode.is_update(self.flags):
            return True
        for n in self.question:
            if n not in other.question:
                return False
        for n in other.question:
            if n not in self.question:
                return False
        return True

    def section_number(self, section):
        if section is self.question:
            return 0
        elif section is self.answer:
            return 1
        elif section is self.authority:
            return 2
        elif section is self.additional:
            return 3
        else:
            raise ValueError('unknown section')

    def find_rrset(self, section, name, rdclass, rdtype,
                   covers=dns.rdatatype.NONE, deleting=None, create=False,
                   force_unique=False):
        """Find the RRset with the given attributes in the specified section.

        @param section: the section of the message to look in, e.g.
        self.answer.
        @type section: list of dns.rrset.RRset objects
        @param name: the name of the RRset
        @type name: dns.name.Name object
        @param rdclass: the class of the RRset
        @type rdclass: int
        @param rdtype: the type of the RRset
        @type rdtype: int
        @param covers: the covers value of the RRset
        @type covers: int
        @param deleting: the deleting value of the RRset
        @type deleting: int
        @param create: If True, create the RRset if it is not found.
        The created RRset is appended to I{section}.
        @type create: bool
        @param force_unique: If True and create is also True, create a
        new RRset regardless of whether a matching RRset exists already.
        @type force_unique: bool
        @raises KeyError: the RRset was not found and create was False
        @rtype: dns.rrset.RRset object"""

        key = (self.section_number(section),
               name, rdclass, rdtype, covers, deleting)
        if not force_unique:
            if not self.index is None:
                rrset = self.index.get(key)
                if not rrset is None:
                    return rrset
            else:
                for rrset in section:
                    if rrset.match(name, rdclass, rdtype, covers, deleting):
                        return rrset
        if not create:
            raise KeyError
        rrset = dns.rrset.RRset(name, rdclass, rdtype, covers, deleting)
        section.append(rrset)
        if not self.index is None:
            self.index[key] = rrset
        return rrset

    def get_rrset(self, section, name, rdclass, rdtype,
                  covers=dns.rdatatype.NONE, deleting=None, create=False,
                  force_unique=False):
        """Get the RRset with the given attributes in the specified section.

        If the RRset is not found, None is returned.

        @param section: the section of the message to look in, e.g.
        self.answer.
        @type section: list of dns.rrset.RRset objects
        @param name: the name of the RRset
        @type name: dns.name.Name object
        @param rdclass: the class of the RRset
        @type rdclass: int
        @param rdtype: the type of the RRset
        @type rdtype: int
        @param covers: the covers value of the RRset
        @type covers: int
        @param deleting: the deleting value of the RRset
        @type deleting: int
        @param create: If True, create the RRset if it is not found.
        The created RRset is appended to I{section}.
        @type create: bool
        @param force_unique: If True and create is also True, create a
        new RRset regardless of whether a matching RRset exists already.
        @type force_unique: bool
        @rtype: dns.rrset.RRset object or None"""

        try:
            rrset = self.find_rrset(section, name, rdclass, rdtype, covers,
                                    deleting, create, force_unique)
        except KeyError:
            rrset = None
        return rrset

    def to_wire(self, origin=None, max_size=0, **kw):
        """Return a string containing the message in DNS compressed wire
        format.

        Additional keyword arguments are passed to the rrset to_wire()
        method.

        @param origin: The origin to be appended to any relative names.
        @type origin: dns.name.Name object
        @param max_size: The maximum size of the wire format output; default
        is 0, which means 'the message's request payload, if nonzero, or
        65536'.
        @type max_size: int
        @raises dns.exception.TooBig: max_size was exceeded
        @rtype: string
        """

        if max_size == 0:
            if self.request_payload != 0:
                max_size = self.request_payload
            else:
                max_size = 65535
        if max_size < 512:
            max_size = 512
        elif max_size > 65535:
            max_size = 65535
        r = dns.renderer.Renderer(self.id, self.flags, max_size, origin)
        for rrset in self.question:
            r.add_question(rrset.name, rrset.rdtype, rrset.rdclass)
        for rrset in self.answer:
            r.add_rrset(dns.renderer.ANSWER, rrset, **kw)
        for rrset in self.authority:
            r.add_rrset(dns.renderer.AUTHORITY, rrset, **kw)
        if self.edns >= 0:
            r.add_edns(self.edns, self.ednsflags, self.payload, self.options)
        for rrset in self.additional:
            r.add_rrset(dns.renderer.ADDITIONAL, rrset, **kw)
        r.write_header()
        if not self.keyname is None:
            r.add_tsig(self.keyname, self.keyring[self.keyname],
                       self.fudge, self.original_id, self.tsig_error,
                       self.other_data, self.request_mac,
                       self.keyalgorithm)
            self.mac = r.mac
        return r.get_wire()

    def use_tsig(self, keyring, keyname=None, fudge=300,
                 original_id=None, tsig_error=0, other_data='',
                 algorithm=dns.tsig.default_algorithm):
        """When sending, a TSIG signature using the specified keyring
        and keyname should be added.

        @param keyring: The TSIG keyring to use; defaults to None.
        @type keyring: dict
        @param keyname: The name of the TSIG key to use; defaults to None.
        The key must be defined in the keyring.  If a keyring is specified
        but a keyname is not, then the key used will be the first key in the
        keyring.  Note that the order of keys in a dictionary is not defined,
        so applications should supply a keyname when a keyring is used, unless
        they know the keyring contains only one key.
        @type keyname: dns.name.Name or string
        @param fudge: TSIG time fudge; default is 300 seconds.
        @type fudge: int
        @param original_id: TSIG original id; defaults to the message's id
        @type original_id: int
        @param tsig_error: TSIG error code; default is 0.
        @type tsig_error: int
        @param other_data: TSIG other data.
        @type other_data: string
        @param algorithm: The TSIG algorithm to use; defaults to
        dns.tsig.default_algorithm
        """

        self.keyring = keyring
        if keyname is None:
            self.keyname = self.keyring.keys()[0]
        else:
            if isinstance(keyname, (str, unicode)):
                keyname = dns.name.from_text(keyname)
            self.keyname = keyname
        self.keyalgorithm = algorithm
        self.fudge = fudge
        if original_id is None:
            self.original_id = self.id
        else:
            self.original_id = original_id
        self.tsig_error = tsig_error
        self.other_data = other_data

    def use_edns(self, edns=0, ednsflags=0, payload=1280, request_payload=None, options=None):
        """Configure EDNS behavior.
        @param edns: The EDNS level to use.  Specifying None, False, or -1
        means 'do not use EDNS', and in this case the other parameters are
        ignored.  Specifying True is equivalent to specifying 0, i.e. 'use
        EDNS0'.
        @type edns: int or bool or None
        @param ednsflags: EDNS flag values.
        @type ednsflags: int
        @param payload: The EDNS sender's payload field, which is the maximum
        size of UDP datagram the sender can handle.
        @type payload: int
        @param request_payload: The EDNS payload size to use when sending
        this message.  If not specified, defaults to the value of payload.
        @type request_payload: int or None
        @param options: The EDNS options
        @type options: None or list of dns.edns.Option objects
        @see: RFC 2671
        """
        if edns is None or edns is False:
            edns = -1
        if edns is True:
            edns = 0
        if request_payload is None:
            request_payload = payload
        if edns < 0:
            ednsflags = 0
            payload = 0
            request_payload = 0
            options = []
        else:
            # make sure the EDNS version in ednsflags agrees with edns
            ednsflags &= 0xFF00FFFFL
            ednsflags |= (edns << 16)
            if options is None:
                options = []
        self.edns = edns
        self.ednsflags = ednsflags
        self.payload = payload
        self.options = options
        self.request_payload = request_payload

    def want_dnssec(self, wanted=True):
        """Enable or disable 'DNSSEC desired' flag in requests.
        @param wanted: Is DNSSEC desired?  If True, EDNS is enabled if
        required, and then the DO bit is set.  If False, the DO bit is
        cleared if EDNS is enabled.
        @type wanted: bool
        """
        if wanted:
            if self.edns < 0:
                self.use_edns()
            self.ednsflags |= dns.flags.DO
        elif self.edns >= 0:
            self.ednsflags &= ~dns.flags.DO

    def rcode(self):
        """Return the rcode.
        @rtype: int
        """
        return dns.rcode.from_flags(self.flags, self.ednsflags)

    def set_rcode(self, rcode):
        """Set the rcode.
        @param rcode: the rcode
        @type rcode: int
        """
        (value, evalue) = dns.rcode.to_flags(rcode)
        self.flags &= 0xFFF0
        self.flags |= value
        self.ednsflags &= 0x00FFFFFFL
        self.ednsflags |= evalue
        if self.ednsflags != 0 and self.edns < 0:
            self.edns = 0

    def opcode(self):
        """Return the opcode.
        @rtype: int
        """
        return dns.opcode.from_flags(self.flags)

    def set_opcode(self, opcode):
        """Set the opcode.
        @param opcode: the opcode
        @type opcode: int
        """
        self.flags &= 0x87FF
        self.flags |= dns.opcode.to_flags(opcode)

class _WireReader(object):
    """Wire format reader.

    @ivar wire: the wire-format message.
    @type wire: string
    @ivar message: The message object being built
    @type message: dns.message.Message object
    @ivar current: When building a message object from wire format, this
    variable contains the offset from the beginning of wire of the next octet
    to be read.
    @type current: int
    @ivar updating: Is the message a dynamic update?
    @type updating: bool
    @ivar one_rr_per_rrset: Put each RR into its own RRset?
    @type one_rr_per_rrset: bool
    @ivar ignore_trailing: Ignore trailing junk at end of request?
    @type ignore_trailing: bool
    @ivar zone_rdclass: The class of the zone in messages which are
    DNS dynamic updates.
    @type zone_rdclass: int
    """

    def __init__(self, wire, message, question_only=False,
                 one_rr_per_rrset=False, ignore_trailing=False):
        self.wire = dns.wiredata.maybe_wrap(wire)
        self.message = message
        self.current = 0
        self.updating = False
        self.zone_rdclass = dns.rdataclass.IN
        self.question_only = question_only
        self.one_rr_per_rrset = one_rr_per_rrset
        self.ignore_trailing = ignore_trailing

    def _get_question(self, qcount):
        """Read the next I{qcount} records from the wire data and add them to
        the question section.
        @param qcount: the number of questions in the message
        @type qcount: int"""

        if self.updating and qcount > 1:
            raise dns.exception.FormError

        for i in xrange(0, qcount):
            (qname, used) = dns.name.from_wire(self.wire, self.current)
            if not self.message.origin is None:
                qname = qname.relativize(self.message.origin)
            self.current = self.current + used
            (rdtype, rdclass) = \
                     struct.unpack('!HH',
                                   self.wire[self.current:self.current + 4])
            self.current = self.current + 4
            self.message.find_rrset(self.message.question, qname,
                                    rdclass, rdtype, create=True,
                                    force_unique=True)
            if self.updating:
                self.zone_rdclass = rdclass

    def _get_section(self, section, count):
        """Read the next I{count} records from the wire data and add them to
        the specified section.
        @param section: the section of the message to which to add records
        @type section: list of dns.rrset.RRset objects
        @param count: the number of records to read
        @type count: int"""

        if self.updating or self.one_rr_per_rrset:
            force_unique = True
        else:
            force_unique = False
        seen_opt = False
        for i in xrange(0, count):
            rr_start = self.current
            (name, used) = dns.name.from_wire(self.wire, self.current)
            absolute_name = name
            if not self.message.origin is None:
                name = name.relativize(self.message.origin)
            self.current = self.current + used
            (rdtype, rdclass, ttl, rdlen) = \
                     struct.unpack('!HHIH',
                                   self.wire[self.current:self.current + 10])
            self.current = self.current + 10
            if rdtype == dns.rdatatype.OPT:
                if not section is self.message.additional or seen_opt:
                    raise BadEDNS
                self.message.payload = rdclass
                self.message.ednsflags = ttl
                self.message.edns = (ttl & 0xff0000) >> 16
                self.message.options = []
                current = self.current
                optslen = rdlen
                while optslen > 0:
                    (otype, olen) = \
                            struct.unpack('!HH',
                                          self.wire[current:current + 4])
                    current = current + 4
                    opt = dns.edns.option_from_wire(otype, self.wire, current, olen)
                    self.message.options.append(opt)
                    current = current + olen
                    optslen = optslen - 4 - olen
                seen_opt = True
            elif rdtype == dns.rdatatype.TSIG:
                if not (section is self.message.additional and
                        i == (count - 1)):
                    raise BadTSIG
                if self.message.keyring is None:
                    raise UnknownTSIGKey('got signed message without keyring')
                secret = self.message.keyring.get(absolute_name)
                if secret is None:
                    raise UnknownTSIGKey("key '%s' unknown" % name)
                self.message.keyname = absolute_name
                (self.message.keyalgorithm, self.message.mac) = \
                    dns.tsig.get_algorithm_and_mac(self.wire, self.current,
                                                   rdlen)
                self.message.tsig_ctx = \
                                      dns.tsig.validate(self.wire,
                                          absolute_name,
                                          secret,
                                          int(time.time()),
                                          self.message.request_mac,
                                          rr_start,
                                          self.current,
                                          rdlen,
                                          self.message.tsig_ctx,
                                          self.message.multi,
                                          self.message.first)
                self.message.had_tsig = True
            else:
                if ttl < 0:
                    ttl = 0
                if self.updating and \
                   (rdclass == dns.rdataclass.ANY or
                    rdclass == dns.rdataclass.NONE):
                    deleting = rdclass
                    rdclass = self.zone_rdclass
                else:
                    deleting = None
                if deleting == dns.rdataclass.ANY or \
                   (deleting == dns.rdataclass.NONE and \
                    section is self.message.answer):
                    covers = dns.rdatatype.NONE
                    rd = None
                else:
                    rd = dns.rdata.from_wire(rdclass, rdtype, self.wire,
                                             self.current, rdlen,
                                             self.message.origin)
                    covers = rd.covers()
                if self.message.xfr and rdtype == dns.rdatatype.SOA:
                    force_unique = True
                rrset = self.message.find_rrset(section, name,
                                                rdclass, rdtype, covers,
                                                deleting, True, force_unique)
                if not rd is None:
                    rrset.add(rd, ttl)
            self.current = self.current + rdlen

    def read(self):
        """Read a wire format DNS message and build a dns.message.Message
        object."""

        l = len(self.wire)
        if l < 12:
            raise ShortHeader
        (self.message.id, self.message.flags, qcount, ancount,
         aucount, adcount) = struct.unpack('!HHHHHH', self.wire[:12])
        self.current = 12
        if dns.opcode.is_update(self.message.flags):
            self.updating = True
        self._get_question(qcount)
        if self.question_only:
            return
        self._get_section(self.message.answer, ancount)
        self._get_section(self.message.authority, aucount)
        self._get_section(self.message.additional, adcount)
        if not self.ignore_trailing and self.current != l:
            raise TrailingJunk
        if self.message.multi and self.message.tsig_ctx and \
               not self.message.had_tsig:
            self.message.tsig_ctx.update(self.wire)


def from_wire(wire, keyring=None, request_mac='', xfr=False, origin=None,
              tsig_ctx = None, multi = False, first = True,
              question_only = False, one_rr_per_rrset = False,
              ignore_trailing = False):
    """Convert a DNS wire format message into a message
    object.

    @param keyring: The keyring to use if the message is signed.
    @type keyring: dict
    @param request_mac: If the message is a response to a TSIG-signed request,
    I{request_mac} should be set to the MAC of that request.
    @type request_mac: string
    @param xfr: Is this message part of a zone transfer?
    @type xfr: bool
    @param origin: If the message is part of a zone transfer, I{origin}
    should be the origin name of the zone.
    @type origin: dns.name.Name object
    @param tsig_ctx: The ongoing TSIG context, used when validating zone
    transfers.
    @type tsig_ctx: hmac.HMAC object
    @param multi: Is this message part of a multiple message sequence?
    @type multi: bool
    @param first: Is this message standalone, or the first of a multi
    message sequence?
    @type first: bool
    @param question_only: Read only up to the end of the question section?
    @type question_only: bool
    @param one_rr_per_rrset: Put each RR into its own RRset
    @type one_rr_per_rrset: bool
    @param ignore_trailing: Ignore trailing junk at end of request?
    @type ignore_trailing: bool
    @raises ShortHeader: The message is less than 12 octets long.
    @raises TrailingJunk: There were octets in the message past the end
    of the proper DNS message.
    @raises BadEDNS: An OPT record was in the wrong section, or occurred more
    than once.
    @raises BadTSIG: A TSIG record was not the last record of the additional
    data section.
    @rtype: dns.message.Message object"""

    m = Message(id=0)
    m.keyring = keyring
    m.request_mac = request_mac
    m.xfr = xfr
    m.origin = origin
    m.tsig_ctx = tsig_ctx
    m.multi = multi
    m.first = first

    reader = _WireReader(wire, m, question_only, one_rr_per_rrset,
                         ignore_trailing)
    reader.read()

    return m


class _TextReader(object):
    """Text format reader.

    @ivar tok: the tokenizer
    @type tok: dns.tokenizer.Tokenizer object
    @ivar message: The message object being built
    @type message: dns.message.Message object
    @ivar updating: Is the message a dynamic update?
    @type updating: bool
    @ivar zone_rdclass: The class of the zone in messages which are
    DNS dynamic updates.
    @type zone_rdclass: int
    @ivar last_name: The most recently read name when building a message object
    from text format.
    @type last_name: dns.name.Name object
    """

    def __init__(self, text, message):
        self.message = message
        self.tok = dns.tokenizer.Tokenizer(text)
        self.last_name = None
        self.zone_rdclass = dns.rdataclass.IN
        self.updating = False

    def _header_line(self, section):
        """Process one line from the text format header section."""

        token = self.tok.get()
        what = token.value
        if what == 'id':
            self.message.id = self.tok.get_int()
        elif what == 'flags':
            while True:
                token = self.tok.get()
                if not token.is_identifier():
                    self.tok.unget(token)
                    break
                self.message.flags = self.message.flags | \
                                     dns.flags.from_text(token.value)
            if dns.opcode.is_update(self.message.flags):
                self.updating = True
        elif what == 'edns':
            self.message.edns = self.tok.get_int()
            self.message.ednsflags = self.message.ednsflags | \
                                     (self.message.edns << 16)
        elif what == 'eflags':
            if self.message.edns < 0:
                self.message.edns = 0
            while True:
                token = self.tok.get()
                if not token.is_identifier():
                    self.tok.unget(token)
                    break
                self.message.ednsflags = self.message.ednsflags | \
                              dns.flags.edns_from_text(token.value)
        elif what == 'payload':
            self.message.payload = self.tok.get_int()
            if self.message.edns < 0:
                self.message.edns = 0
        elif what == 'opcode':
            text = self.tok.get_string()
            self.message.flags = self.message.flags | \
                      dns.opcode.to_flags(dns.opcode.from_text(text))
        elif what == 'rcode':
            text = self.tok.get_string()
            self.message.set_rcode(dns.rcode.from_text(text))
        else:
            raise UnknownHeaderField
        self.tok.get_eol()

    def _question_line(self, section):
        """Process one line from the text format question section."""

        token = self.tok.get(want_leading = True)
        if not token.is_whitespace():
            self.last_name = dns.name.from_text(token.value, None)
        name = self.last_name
        token = self.tok.get()
        if not token.is_identifier():
            raise dns.exception.SyntaxError
        # Class
        try:
            rdclass = dns.rdataclass.from_text(token.value)
            token = self.tok.get()
            if not token.is_identifier():
                raise dns.exception.SyntaxError
        except dns.exception.SyntaxError:
            raise dns.exception.SyntaxError
        except:
            rdclass = dns.rdataclass.IN
        # Type
        rdtype = dns.rdatatype.from_text(token.value)
        self.message.find_rrset(self.message.question, name,
                                rdclass, rdtype, create=True,
                                force_unique=True)
        if self.updating:
            self.zone_rdclass = rdclass
        self.tok.get_eol()

    def _rr_line(self, section):
        """Process one line from the text format answer, authority, or
        additional data sections.
        """

        deleting = None
        # Name
        token = self.tok.get(want_leading = True)
        if not token.is_whitespace():
            self.last_name = dns.name.from_text(token.value, None)
        name = self.last_name
        token = self.tok.get()
        if not token.is_identifier():
            raise dns.exception.SyntaxError
        # TTL
        try:
            ttl = int(token.value, 0)
            token = self.tok.get()
            if not token.is_identifier():
                raise dns.exception.SyntaxError
        except dns.exception.SyntaxError:
            raise dns.exception.SyntaxError
        except:
            ttl = 0
        # Class
        try:
            rdclass = dns.rdataclass.from_text(token.value)
            token = self.tok.get()
            if not token.is_identifier():
                raise dns.exception.SyntaxError
            if rdclass == dns.rdataclass.ANY or rdclass == dns.rdataclass.NONE:
                deleting = rdclass
                rdclass = self.zone_rdclass
        except dns.exception.SyntaxError:
            raise dns.exception.SyntaxError
        except:
            rdclass = dns.rdataclass.IN
        # Type
        rdtype = dns.rdatatype.from_text(token.value)
        token = self.tok.get()
        if not token.is_eol_or_eof():
            self.tok.unget(token)
            rd = dns.rdata.from_text(rdclass, rdtype, self.tok, None)
            covers = rd.covers()
        else:
            rd = None
            covers = dns.rdatatype.NONE
        rrset = self.message.find_rrset(section, name,
                                        rdclass, rdtype, covers,
                                        deleting, True, self.updating)
        if not rd is None:
            rrset.add(rd, ttl)

    def read(self):
        """Read a text format DNS message and build a dns.message.Message
        object."""

        line_method = self._header_line
        section = None
        while 1:
            token = self.tok.get(True, True)
            if token.is_eol_or_eof():
                break
            if token.is_comment():
                u = token.value.upper()
                if u == 'HEADER':
                    line_method = self._header_line
                elif u == 'QUESTION' or u == 'ZONE':
                    line_method = self._question_line
                    section = self.message.question
                elif u == 'ANSWER' or u == 'PREREQ':
                    line_method = self._rr_line
                    section = self.message.answer
                elif u == 'AUTHORITY' or u == 'UPDATE':
                    line_method = self._rr_line
                    section = self.message.authority
                elif u == 'ADDITIONAL':
                    line_method = self._rr_line
                    section = self.message.additional
                self.tok.get_eol()
                continue
            self.tok.unget(token)
            line_method(section)


def from_text(text):
    """Convert the text format message into a message object.

    @param text: The text format message.
    @type text: string
    @raises UnknownHeaderField:
    @raises dns.exception.SyntaxError:
    @rtype: dns.message.Message object"""

    # 'text' can also be a file, but we don't publish that fact
    # since it's an implementation detail.  The official file
    # interface is from_file().

    m = Message()

    reader = _TextReader(text, m)
    reader.read()

    return m

def from_file(f):
    """Read the next text format message from the specified file.

    @param f: file or string.  If I{f} is a string, it is treated
    as the name of a file to open.
    @raises UnknownHeaderField:
    @raises dns.exception.SyntaxError:
    @rtype: dns.message.Message object"""

    if sys.hexversion >= 0x02030000:
        # allow Unicode filenames; turn on universal newline support
        str_type = basestring
        opts = 'rU'
    else:
        str_type = str
        opts = 'r'
    if isinstance(f, str_type):
        f = file(f, opts)
        want_close = True
    else:
        want_close = False

    try:
        m = from_text(f)
    finally:
        if want_close:
            f.close()
    return m

def make_query(qname, rdtype, rdclass = dns.rdataclass.IN, use_edns=None,
               want_dnssec=False, ednsflags=0, payload=1280,
               request_payload=None, options=None):
    """Make a query message.

    The query name, type, and class may all be specified either
    as objects of the appropriate type, or as strings.

    The query will have a randomly choosen query id, and its DNS flags
    will be set to dns.flags.RD.

    @param qname: The query name.
    @type qname: dns.name.Name object or string
    @param rdtype: The desired rdata type.
    @type rdtype: int
    @param rdclass: The desired rdata class; the default is class IN.
    @type rdclass: int
    @param use_edns: The EDNS level to use; the default is None (no EDNS).
    See the description of dns.message.Message.use_edns() for the possible
    values for use_edns and their meanings.
    @type use_edns: int or bool or None
    @param want_dnssec: Should the query indicate that DNSSEC is desired?
    @type want_dnssec: bool
    @param ednsflags: EDNS flag values.
    @type ednsflags: int
    @param payload: The EDNS sender's payload field, which is the maximum
    size of UDP datagram the sender can handle.
    @type payload: int
    @param request_payload: The EDNS payload size to use when sending
    this message.  If not specified, defaults to the value of payload.
    @type request_payload: int or None
    @param options: The EDNS options
    @type options: None or list of dns.edns.Option objects
    @see: RFC 2671
    @rtype: dns.message.Message object"""

    if isinstance(qname, (str, unicode)):
        qname = dns.name.from_text(qname)
    if isinstance(rdtype, (str, unicode)):
        rdtype = dns.rdatatype.from_text(rdtype)
    if isinstance(rdclass, (str, unicode)):
        rdclass = dns.rdataclass.from_text(rdclass)
    m = Message()
    m.flags |= dns.flags.RD
    m.find_rrset(m.question, qname, rdclass, rdtype, create=True,
                 force_unique=True)
    m.use_edns(use_edns, ednsflags, payload, request_payload, options)
    m.want_dnssec(want_dnssec)
    return m

def make_response(query, recursion_available=False, our_payload=8192,
                  fudge=300):
    """Make a message which is a response for the specified query.
    The message returned is really a response skeleton; it has all
    of the infrastructure required of a response, but none of the
    content.

    The response's question section is a shallow copy of the query's
    question section, so the query's question RRsets should not be
    changed.

    @param query: the query to respond to
    @type query: dns.message.Message object
    @param recursion_available: should RA be set in the response?
    @type recursion_available: bool
    @param our_payload: payload size to advertise in EDNS responses; default
    is 8192.
    @type our_payload: int
    @param fudge: TSIG time fudge; default is 300 seconds.
    @type fudge: int
    @rtype: dns.message.Message object"""

    if query.flags & dns.flags.QR:
        raise dns.exception.FormError('specified query message is not a query')
    response = dns.message.Message(query.id)
    response.flags = dns.flags.QR | (query.flags & dns.flags.RD)
    if recursion_available:
        response.flags |= dns.flags.RA
    response.set_opcode(query.opcode())
    response.question = list(query.question)
    if query.edns >= 0:
        response.use_edns(0, 0, our_payload, query.payload)
    if query.had_tsig:
        response.use_tsig(query.keyring, query.keyname, fudge, None, 0, '',
                          query.keyalgorithm)
        response.request_mac = query.mac
    return response

########NEW FILE########
__FILENAME__ = name
# Copyright (C) 2001-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS Names.

@var root: The DNS root name.
@type root: dns.name.Name object
@var empty: The empty DNS name.
@type empty: dns.name.Name object
"""

import cStringIO
import struct
import sys
import copy

if sys.hexversion >= 0x02030000:
    import encodings.idna

import dns.exception
import dns.wiredata

NAMERELN_NONE = 0
NAMERELN_SUPERDOMAIN = 1
NAMERELN_SUBDOMAIN = 2
NAMERELN_EQUAL = 3
NAMERELN_COMMONANCESTOR = 4

class EmptyLabel(dns.exception.SyntaxError):
    """Raised if a label is empty."""
    pass

class BadEscape(dns.exception.SyntaxError):
    """Raised if an escaped code in a text format name is invalid."""
    pass

class BadPointer(dns.exception.FormError):
    """Raised if a compression pointer points forward instead of backward."""
    pass

class BadLabelType(dns.exception.FormError):
    """Raised if the label type of a wire format name is unknown."""
    pass

class NeedAbsoluteNameOrOrigin(dns.exception.DNSException):
    """Raised if an attempt is made to convert a non-absolute name to
    wire when there is also a non-absolute (or missing) origin."""
    pass

class NameTooLong(dns.exception.FormError):
    """Raised if a name is > 255 octets long."""
    pass

class LabelTooLong(dns.exception.SyntaxError):
    """Raised if a label is > 63 octets long."""
    pass

class AbsoluteConcatenation(dns.exception.DNSException):
    """Raised if an attempt is made to append anything other than the
    empty name to an absolute name."""
    pass

class NoParent(dns.exception.DNSException):
    """Raised if an attempt is made to get the parent of the root name
    or the empty name."""
    pass

_escaped = {
    '"' : True,
    '(' : True,
    ')' : True,
    '.' : True,
    ';' : True,
    '\\' : True,
    '@' : True,
    '$' : True
    }

def _escapify(label):
    """Escape the characters in label which need it.
    @returns: the escaped string
    @rtype: string"""
    text = ''
    for c in label:
        if c in _escaped:
            text += '\\' + c
        elif ord(c) > 0x20 and ord(c) < 0x7F:
            text += c
        else:
            text += '\\%03d' % ord(c)
    return text

def _validate_labels(labels):
    """Check for empty labels in the middle of a label sequence,
    labels that are too long, and for too many labels.
    @raises NameTooLong: the name as a whole is too long
    @raises LabelTooLong: an individual label is too long
    @raises EmptyLabel: a label is empty (i.e. the root label) and appears
    in a position other than the end of the label sequence"""

    l = len(labels)
    total = 0
    i = -1
    j = 0
    for label in labels:
        ll = len(label)
        total += ll + 1
        if ll > 63:
            raise LabelTooLong
        if i < 0 and label == '':
            i = j
        j += 1
    if total > 255:
        raise NameTooLong
    if i >= 0 and i != l - 1:
        raise EmptyLabel

class Name(object):
    """A DNS name.

    The dns.name.Name class represents a DNS name as a tuple of labels.
    Instances of the class are immutable.

    @ivar labels: The tuple of labels in the name. Each label is a string of
    up to 63 octets."""

    __slots__ = ['labels']

    def __init__(self, labels):
        """Initialize a domain name from a list of labels.
        @param labels: the labels
        @type labels: any iterable whose values are strings
        """

        super(Name, self).__setattr__('labels', tuple(labels))
        _validate_labels(self.labels)

    def __setattr__(self, name, value):
        raise TypeError("object doesn't support attribute assignment")

    def __copy__(self):
        return Name(self.labels)

    def __deepcopy__(self, memo):
        return Name(copy.deepcopy(self.labels, memo))

    def is_absolute(self):
        """Is the most significant label of this name the root label?
        @rtype: bool
        """

        return len(self.labels) > 0 and self.labels[-1] == ''

    def is_wild(self):
        """Is this name wild?  (I.e. Is the least significant label '*'?)
        @rtype: bool
        """

        return len(self.labels) > 0 and self.labels[0] == '*'

    def __hash__(self):
        """Return a case-insensitive hash of the name.
        @rtype: int
        """

        h = 0L
        for label in self.labels:
            for c in label:
                h += ( h << 3 ) + ord(c.lower())
        return int(h % sys.maxint)

    def fullcompare(self, other):
        """Compare two names, returning a 3-tuple (relation, order, nlabels).

        I{relation} describes the relation ship beween the names,
        and is one of: dns.name.NAMERELN_NONE,
        dns.name.NAMERELN_SUPERDOMAIN, dns.name.NAMERELN_SUBDOMAIN,
        dns.name.NAMERELN_EQUAL, or dns.name.NAMERELN_COMMONANCESTOR

        I{order} is < 0 if self < other, > 0 if self > other, and ==
        0 if self == other.  A relative name is always less than an
        absolute name.  If both names have the same relativity, then
        the DNSSEC order relation is used to order them.

        I{nlabels} is the number of significant labels that the two names
        have in common.
        """

        sabs = self.is_absolute()
        oabs = other.is_absolute()
        if sabs != oabs:
            if sabs:
                return (NAMERELN_NONE, 1, 0)
            else:
                return (NAMERELN_NONE, -1, 0)
        l1 = len(self.labels)
        l2 = len(other.labels)
        ldiff = l1 - l2
        if ldiff < 0:
            l = l1
        else:
            l = l2

        order = 0
        nlabels = 0
        namereln = NAMERELN_NONE
        while l > 0:
            l -= 1
            l1 -= 1
            l2 -= 1
            label1 = self.labels[l1].lower()
            label2 = other.labels[l2].lower()
            if label1 < label2:
                order = -1
                if nlabels > 0:
                    namereln = NAMERELN_COMMONANCESTOR
                return (namereln, order, nlabels)
            elif label1 > label2:
                order = 1
                if nlabels > 0:
                    namereln = NAMERELN_COMMONANCESTOR
                return (namereln, order, nlabels)
            nlabels += 1
        order = ldiff
        if ldiff < 0:
            namereln = NAMERELN_SUPERDOMAIN
        elif ldiff > 0:
            namereln = NAMERELN_SUBDOMAIN
        else:
            namereln = NAMERELN_EQUAL
        return (namereln, order, nlabels)

    def is_subdomain(self, other):
        """Is self a subdomain of other?

        The notion of subdomain includes equality.
        @rtype: bool
        """

        (nr, o, nl) = self.fullcompare(other)
        if nr == NAMERELN_SUBDOMAIN or nr == NAMERELN_EQUAL:
            return True
        return False

    def is_superdomain(self, other):
        """Is self a superdomain of other?

        The notion of subdomain includes equality.
        @rtype: bool
        """

        (nr, o, nl) = self.fullcompare(other)
        if nr == NAMERELN_SUPERDOMAIN or nr == NAMERELN_EQUAL:
            return True
        return False

    def canonicalize(self):
        """Return a name which is equal to the current name, but is in
        DNSSEC canonical form.
        @rtype: dns.name.Name object
        """

        return Name([x.lower() for x in self.labels])

    def __eq__(self, other):
        if isinstance(other, Name):
            return self.fullcompare(other)[1] == 0
        else:
            return False

    def __ne__(self, other):
        if isinstance(other, Name):
            return self.fullcompare(other)[1] != 0
        else:
            return True

    def __lt__(self, other):
        if isinstance(other, Name):
            return self.fullcompare(other)[1] < 0
        else:
            return NotImplemented

    def __le__(self, other):
        if isinstance(other, Name):
            return self.fullcompare(other)[1] <= 0
        else:
            return NotImplemented

    def __ge__(self, other):
        if isinstance(other, Name):
            return self.fullcompare(other)[1] >= 0
        else:
            return NotImplemented

    def __gt__(self, other):
        if isinstance(other, Name):
            return self.fullcompare(other)[1] > 0
        else:
            return NotImplemented

    def __repr__(self):
        return '<DNS name ' + self.__str__() + '>'

    def __str__(self):
        return self.to_text(False)

    def to_text(self, omit_final_dot = False):
        """Convert name to text format.
        @param omit_final_dot: If True, don't emit the final dot (denoting the
        root label) for absolute names.  The default is False.
        @rtype: string
        """

        if len(self.labels) == 0:
            return '@'
        if len(self.labels) == 1 and self.labels[0] == '':
            return '.'
        if omit_final_dot and self.is_absolute():
            l = self.labels[:-1]
        else:
            l = self.labels
        s = '.'.join(map(_escapify, l))
        return s

    def to_unicode(self, omit_final_dot = False):
        """Convert name to Unicode text format.

        IDN ACE lables are converted to Unicode.

        @param omit_final_dot: If True, don't emit the final dot (denoting the
        root label) for absolute names.  The default is False.
        @rtype: string
        """

        if len(self.labels) == 0:
            return u'@'
        if len(self.labels) == 1 and self.labels[0] == '':
            return u'.'
        if omit_final_dot and self.is_absolute():
            l = self.labels[:-1]
        else:
            l = self.labels
        s = u'.'.join([encodings.idna.ToUnicode(_escapify(x)) for x in l])
        return s

    def to_digestable(self, origin=None):
        """Convert name to a format suitable for digesting in hashes.

        The name is canonicalized and converted to uncompressed wire format.

        @param origin: If the name is relative and origin is not None, then
        origin will be appended to it.
        @type origin: dns.name.Name object
        @raises NeedAbsoluteNameOrOrigin: All names in wire format are
        absolute.  If self is a relative name, then an origin must be supplied;
        if it is missing, then this exception is raised
        @rtype: string
        """

        if not self.is_absolute():
            if origin is None or not origin.is_absolute():
                raise NeedAbsoluteNameOrOrigin
            labels = list(self.labels)
            labels.extend(list(origin.labels))
        else:
            labels = self.labels
        dlabels = ["%s%s" % (chr(len(x)), x.lower()) for x in labels]
        return ''.join(dlabels)

    def to_wire(self, file = None, compress = None, origin = None):
        """Convert name to wire format, possibly compressing it.

        @param file: the file where the name is emitted (typically
        a cStringIO file).  If None, a string containing the wire name
        will be returned.
        @type file: file or None
        @param compress: The compression table.  If None (the default) names
        will not be compressed.
        @type compress: dict
        @param origin: If the name is relative and origin is not None, then
        origin will be appended to it.
        @type origin: dns.name.Name object
        @raises NeedAbsoluteNameOrOrigin: All names in wire format are
        absolute.  If self is a relative name, then an origin must be supplied;
        if it is missing, then this exception is raised
        """

        if file is None:
            file = cStringIO.StringIO()
            want_return = True
        else:
            want_return = False

        if not self.is_absolute():
            if origin is None or not origin.is_absolute():
                raise NeedAbsoluteNameOrOrigin
            labels = list(self.labels)
            labels.extend(list(origin.labels))
        else:
            labels = self.labels
        i = 0
        for label in labels:
            n = Name(labels[i:])
            i += 1
            if not compress is None:
                pos = compress.get(n)
            else:
                pos = None
            if not pos is None:
                value = 0xc000 + pos
                s = struct.pack('!H', value)
                file.write(s)
                break
            else:
                if not compress is None and len(n) > 1:
                    pos = file.tell()
                    if pos <= 0x3fff:
                        compress[n] = pos
                l = len(label)
                file.write(chr(l))
                if l > 0:
                    file.write(label)
        if want_return:
            return file.getvalue()

    def __len__(self):
        """The length of the name (in labels).
        @rtype: int
        """

        return len(self.labels)

    def __getitem__(self, index):
        return self.labels[index]

    def __getslice__(self, start, stop):
        return self.labels[start:stop]

    def __add__(self, other):
        return self.concatenate(other)

    def __sub__(self, other):
        return self.relativize(other)

    def split(self, depth):
        """Split a name into a prefix and suffix at depth.

        @param depth: the number of labels in the suffix
        @type depth: int
        @raises ValueError: the depth was not >= 0 and <= the length of the
        name.
        @returns: the tuple (prefix, suffix)
        @rtype: tuple
        """

        l = len(self.labels)
        if depth == 0:
            return (self, dns.name.empty)
        elif depth == l:
            return (dns.name.empty, self)
        elif depth < 0 or depth > l:
            raise ValueError('depth must be >= 0 and <= the length of the name')
        return (Name(self[: -depth]), Name(self[-depth :]))

    def concatenate(self, other):
        """Return a new name which is the concatenation of self and other.
        @rtype: dns.name.Name object
        @raises AbsoluteConcatenation: self is absolute and other is
        not the empty name
        """

        if self.is_absolute() and len(other) > 0:
            raise AbsoluteConcatenation
        labels = list(self.labels)
        labels.extend(list(other.labels))
        return Name(labels)

    def relativize(self, origin):
        """If self is a subdomain of origin, return a new name which is self
        relative to origin.  Otherwise return self.
        @rtype: dns.name.Name object
        """

        if not origin is None and self.is_subdomain(origin):
            return Name(self[: -len(origin)])
        else:
            return self

    def derelativize(self, origin):
        """If self is a relative name, return a new name which is the
        concatenation of self and origin.  Otherwise return self.
        @rtype: dns.name.Name object
        """

        if not self.is_absolute():
            return self.concatenate(origin)
        else:
            return self

    def choose_relativity(self, origin=None, relativize=True):
        """Return a name with the relativity desired by the caller.  If
        origin is None, then self is returned.  Otherwise, if
        relativize is true the name is relativized, and if relativize is
        false the name is derelativized.
        @rtype: dns.name.Name object
        """

        if origin:
            if relativize:
                return self.relativize(origin)
            else:
                return self.derelativize(origin)
        else:
            return self

    def parent(self):
        """Return the parent of the name.
        @rtype: dns.name.Name object
        @raises NoParent: the name is either the root name or the empty name,
        and thus has no parent.
        """
        if self == root or self == empty:
            raise NoParent
        return Name(self.labels[1:])

root = Name([''])
empty = Name([])

def from_unicode(text, origin = root):
    """Convert unicode text into a Name object.

    Lables are encoded in IDN ACE form.

    @rtype: dns.name.Name object
    """

    if not isinstance(text, unicode):
        raise ValueError("input to from_unicode() must be a unicode string")
    if not (origin is None or isinstance(origin, Name)):
        raise ValueError("origin must be a Name or None")
    labels = []
    label = u''
    escaping = False
    edigits = 0
    total = 0
    if text == u'@':
        text = u''
    if text:
        if text == u'.':
            return Name([''])	# no Unicode "u" on this constant!
        for c in text:
            if escaping:
                if edigits == 0:
                    if c.isdigit():
                        total = int(c)
                        edigits += 1
                    else:
                        label += c
                        escaping = False
                else:
                    if not c.isdigit():
                        raise BadEscape
                    total *= 10
                    total += int(c)
                    edigits += 1
                    if edigits == 3:
                        escaping = False
                        label += chr(total)
            elif c == u'.' or c == u'\u3002' or \
                 c == u'\uff0e' or c == u'\uff61':
                if len(label) == 0:
                    raise EmptyLabel
                labels.append(encodings.idna.ToASCII(label))
                label = u''
            elif c == u'\\':
                escaping = True
                edigits = 0
                total = 0
            else:
                label += c
        if escaping:
            raise BadEscape
        if len(label) > 0:
            labels.append(encodings.idna.ToASCII(label))
        else:
            labels.append('')
    if (len(labels) == 0 or labels[-1] != '') and not origin is None:
        labels.extend(list(origin.labels))
    return Name(labels)

def from_text(text, origin = root):
    """Convert text into a Name object.
    @rtype: dns.name.Name object
    """

    if not isinstance(text, str):
        if isinstance(text, unicode) and sys.hexversion >= 0x02030000:
            return from_unicode(text, origin)
        else:
            raise ValueError("input to from_text() must be a string")
    if not (origin is None or isinstance(origin, Name)):
        raise ValueError("origin must be a Name or None")
    labels = []
    label = ''
    escaping = False
    edigits = 0
    total = 0
    if text == '@':
        text = ''
    if text:
        if text == '.':
            return Name([''])
        for c in text:
            if escaping:
                if edigits == 0:
                    if c.isdigit():
                        total = int(c)
                        edigits += 1
                    else:
                        label += c
                        escaping = False
                else:
                    if not c.isdigit():
                        raise BadEscape
                    total *= 10
                    total += int(c)
                    edigits += 1
                    if edigits == 3:
                        escaping = False
                        label += chr(total)
            elif c == '.':
                if len(label) == 0:
                    raise EmptyLabel
                labels.append(label)
                label = ''
            elif c == '\\':
                escaping = True
                edigits = 0
                total = 0
            else:
                label += c
        if escaping:
            raise BadEscape
        if len(label) > 0:
            labels.append(label)
        else:
            labels.append('')
    if (len(labels) == 0 or labels[-1] != '') and not origin is None:
        labels.extend(list(origin.labels))
    return Name(labels)

def from_wire(message, current):
    """Convert possibly compressed wire format into a Name.
    @param message: the entire DNS message
    @type message: string
    @param current: the offset of the beginning of the name from the start
    of the message
    @type current: int
    @raises dns.name.BadPointer: a compression pointer did not point backwards
    in the message
    @raises dns.name.BadLabelType: an invalid label type was encountered.
    @returns: a tuple consisting of the name that was read and the number
    of bytes of the wire format message which were consumed reading it
    @rtype: (dns.name.Name object, int) tuple
    """

    if not isinstance(message, str):
        raise ValueError("input to from_wire() must be a byte string")
    message = dns.wiredata.maybe_wrap(message)
    labels = []
    biggest_pointer = current
    hops = 0
    count = ord(message[current])
    current += 1
    cused = 1
    while count != 0:
        if count < 64:
            labels.append(message[current : current + count].unwrap())
            current += count
            if hops == 0:
                cused += count
        elif count >= 192:
            current = (count & 0x3f) * 256 + ord(message[current])
            if hops == 0:
                cused += 1
            if current >= biggest_pointer:
                raise BadPointer
            biggest_pointer = current
            hops += 1
        else:
            raise BadLabelType
        count = ord(message[current])
        current += 1
        if hops == 0:
            cused += 1
    labels.append('')
    return (Name(labels), cused)

########NEW FILE########
__FILENAME__ = namedict
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS name dictionary"""

import dns.name

class NameDict(dict):

    """A dictionary whose keys are dns.name.Name objects.
    @ivar max_depth: the maximum depth of the keys that have ever been
    added to the dictionary.
    @type max_depth: int
    """

    def __init__(self, *args, **kwargs):
        super(NameDict, self).__init__(*args, **kwargs)
        self.max_depth = 0

    def __setitem__(self, key, value):
        if not isinstance(key, dns.name.Name):
            raise ValueError('NameDict key must be a name')
        depth = len(key)
        if depth > self.max_depth:
            self.max_depth = depth
        super(NameDict, self).__setitem__(key, value)

    def get_deepest_match(self, name):
        """Find the deepest match to I{name} in the dictionary.

        The deepest match is the longest name in the dictionary which is
        a superdomain of I{name}.

        @param name: the name
        @type name: dns.name.Name object
        @rtype: (key, value) tuple
        """

        depth = len(name)
        if depth > self.max_depth:
            depth = self.max_depth
        for i in xrange(-depth, 0):
            n = dns.name.Name(name[i:])
            if self.has_key(n):
                return (n, self[n])
        v = self[dns.name.empty]
        return (dns.name.empty, v)

########NEW FILE########
__FILENAME__ = node
# Copyright (C) 2001-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS nodes.  A node is a set of rdatasets."""

import StringIO

import dns.rdataset
import dns.rdatatype
import dns.renderer

class Node(object):
    """A DNS node.

    A node is a set of rdatasets

    @ivar rdatasets: the node's rdatasets
    @type rdatasets: list of dns.rdataset.Rdataset objects"""

    __slots__ = ['rdatasets']

    def __init__(self):
        """Initialize a DNS node.
        """

        self.rdatasets = [];

    def to_text(self, name, **kw):
        """Convert a node to text format.

        Each rdataset at the node is printed.  Any keyword arguments
        to this method are passed on to the rdataset's to_text() method.
        @param name: the owner name of the rdatasets
        @type name: dns.name.Name object
        @rtype: string
        """

        s = StringIO.StringIO()
        for rds in self.rdatasets:
            if len(rds) > 0:
                print >> s, rds.to_text(name, **kw)
        return s.getvalue()[:-1]

    def __repr__(self):
        return '<DNS node ' + str(id(self)) + '>'

    def __eq__(self, other):
        """Two nodes are equal if they have the same rdatasets.

        @rtype: bool
        """
        #
        # This is inefficient.  Good thing we don't need to do it much.
        #
        for rd in self.rdatasets:
            if rd not in other.rdatasets:
                return False
        for rd in other.rdatasets:
            if rd not in self.rdatasets:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __len__(self):
        return len(self.rdatasets)

    def __iter__(self):
        return iter(self.rdatasets)

    def find_rdataset(self, rdclass, rdtype, covers=dns.rdatatype.NONE,
                      create=False):
        """Find an rdataset matching the specified properties in the
        current node.

        @param rdclass: The class of the rdataset
        @type rdclass: int
        @param rdtype: The type of the rdataset
        @type rdtype: int
        @param covers: The covered type.  Usually this value is
        dns.rdatatype.NONE, but if the rdtype is dns.rdatatype.SIG or
        dns.rdatatype.RRSIG, then the covers value will be the rdata
        type the SIG/RRSIG covers.  The library treats the SIG and RRSIG
        types as if they were a family of
        types, e.g. RRSIG(A), RRSIG(NS), RRSIG(SOA).  This makes RRSIGs much
        easier to work with than if RRSIGs covering different rdata
        types were aggregated into a single RRSIG rdataset.
        @type covers: int
        @param create: If True, create the rdataset if it is not found.
        @type create: bool
        @raises KeyError: An rdataset of the desired type and class does
        not exist and I{create} is not True.
        @rtype: dns.rdataset.Rdataset object
        """

        for rds in self.rdatasets:
            if rds.match(rdclass, rdtype, covers):
                return rds
        if not create:
            raise KeyError
        rds = dns.rdataset.Rdataset(rdclass, rdtype)
        self.rdatasets.append(rds)
        return rds

    def get_rdataset(self, rdclass, rdtype, covers=dns.rdatatype.NONE,
                     create=False):
        """Get an rdataset matching the specified properties in the
        current node.

        None is returned if an rdataset of the specified type and
        class does not exist and I{create} is not True.

        @param rdclass: The class of the rdataset
        @type rdclass: int
        @param rdtype: The type of the rdataset
        @type rdtype: int
        @param covers: The covered type.
        @type covers: int
        @param create: If True, create the rdataset if it is not found.
        @type create: bool
        @rtype: dns.rdataset.Rdataset object or None
        """

        try:
            rds = self.find_rdataset(rdclass, rdtype, covers, create)
        except KeyError:
            rds = None
        return rds

    def delete_rdataset(self, rdclass, rdtype, covers=dns.rdatatype.NONE):
        """Delete the rdataset matching the specified properties in the
        current node.

        If a matching rdataset does not exist, it is not an error.

        @param rdclass: The class of the rdataset
        @type rdclass: int
        @param rdtype: The type of the rdataset
        @type rdtype: int
        @param covers: The covered type.
        @type covers: int
        """

        rds = self.get_rdataset(rdclass, rdtype, covers)
        if not rds is None:
            self.rdatasets.remove(rds)

    def replace_rdataset(self, replacement):
        """Replace an rdataset.

        It is not an error if there is no rdataset matching I{replacement}.

        Ownership of the I{replacement} object is transferred to the node;
        in other words, this method does not store a copy of I{replacement}
        at the node, it stores I{replacement} itself.
        """

        if not isinstance(replacement, dns.rdataset.Rdataset):
            raise ValueError, 'replacement is not an rdataset'
        self.delete_rdataset(replacement.rdclass, replacement.rdtype,
                             replacement.covers)
        self.rdatasets.append(replacement)

########NEW FILE########
__FILENAME__ = opcode
# Copyright (C) 2001-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS Opcodes."""

import dns.exception

QUERY = 0
IQUERY = 1
STATUS = 2
NOTIFY = 4
UPDATE = 5

_by_text = {
    'QUERY' : QUERY,
    'IQUERY' : IQUERY,
    'STATUS' : STATUS,
    'NOTIFY' : NOTIFY,
    'UPDATE' : UPDATE
}

# We construct the inverse mapping programmatically to ensure that we
# cannot make any mistakes (e.g. omissions, cut-and-paste errors) that
# would cause the mapping not to be true inverse.

_by_value = dict([(y, x) for x, y in _by_text.iteritems()])


class UnknownOpcode(dns.exception.DNSException):
    """Raised if an opcode is unknown."""
    pass

def from_text(text):
    """Convert text into an opcode.

    @param text: the textual opcode
    @type text: string
    @raises UnknownOpcode: the opcode is unknown
    @rtype: int
    """

    if text.isdigit():
        value = int(text)
        if value >= 0 and value <= 15:
            return value
    value = _by_text.get(text.upper())
    if value is None:
        raise UnknownOpcode
    return value

def from_flags(flags):
    """Extract an opcode from DNS message flags.

    @param flags: int
    @rtype: int
    """
    
    return (flags & 0x7800) >> 11

def to_flags(value):
    """Convert an opcode to a value suitable for ORing into DNS message
    flags.
    @rtype: int
    """
    
    return (value << 11) & 0x7800
    
def to_text(value):
    """Convert an opcode to text.

    @param value: the opcdoe
    @type value: int
    @raises UnknownOpcode: the opcode is unknown
    @rtype: string
    """
    
    text = _by_value.get(value)
    if text is None:
        text = str(value)
    return text

def is_update(flags):
    """True if the opcode in flags is UPDATE.

    @param flags: DNS flags
    @type flags: int
    @rtype: bool
    """
    
    if (from_flags(flags) == UPDATE):
        return True
    return False

########NEW FILE########
__FILENAME__ = query
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""Talk to a DNS server."""

from __future__ import generators

import errno
import select
import socket
import struct
import sys
import time

import dns.exception
import dns.inet
import dns.name
import dns.message
import dns.rdataclass
import dns.rdatatype

class UnexpectedSource(dns.exception.DNSException):
    """Raised if a query response comes from an unexpected address or port."""
    pass

class BadResponse(dns.exception.FormError):
    """Raised if a query response does not respond to the question asked."""
    pass

def _compute_expiration(timeout):
    if timeout is None:
        return None
    else:
        return time.time() + timeout

def _poll_for(fd, readable, writable, error, timeout):
    """Poll polling backend.
    @param fd: File descriptor
    @type fd: int
    @param readable: Whether to wait for readability
    @type readable: bool
    @param writable: Whether to wait for writability
    @type writable: bool
    @param timeout: Deadline timeout (expiration time, in seconds)
    @type timeout: float
    @return True on success, False on timeout
    """
    event_mask = 0
    if readable:
        event_mask |= select.POLLIN
    if writable:
        event_mask |= select.POLLOUT
    if error:
        event_mask |= select.POLLERR

    pollable = select.poll()
    pollable.register(fd, event_mask)

    if timeout:
        event_list = pollable.poll(long(timeout * 1000))
    else:
        event_list = pollable.poll()

    return bool(event_list)

def _select_for(fd, readable, writable, error, timeout):
    """Select polling backend.
    @param fd: File descriptor
    @type fd: int
    @param readable: Whether to wait for readability
    @type readable: bool
    @param writable: Whether to wait for writability
    @type writable: bool
    @param timeout: Deadline timeout (expiration time, in seconds)
    @type timeout: float
    @return True on success, False on timeout
    """
    rset, wset, xset = [], [], []

    if readable:
        rset = [fd]
    if writable:
        wset = [fd]
    if error:
        xset = [fd]

    if timeout is None:
        (rcount, wcount, xcount) = select.select(rset, wset, xset)
    else:
        (rcount, wcount, xcount) = select.select(rset, wset, xset, timeout)

    return bool((rcount or wcount or xcount))

def _wait_for(fd, readable, writable, error, expiration):
    done = False
    while not done:
        if expiration is None:
            timeout = None
        else:
            timeout = expiration - time.time()
            if timeout <= 0.0:
                raise dns.exception.Timeout
        try:
            if not _polling_backend(fd, readable, writable, error, timeout):
                raise dns.exception.Timeout
        except select.error, e:
            if e.args[0] != errno.EINTR:
                raise e
        done = True

def _set_polling_backend(fn):
    """
    Internal API. Do not use.
    """
    global _polling_backend

    _polling_backend = fn

if hasattr(select, 'poll'):
    # Prefer poll() on platforms that support it because it has no
    # limits on the maximum value of a file descriptor (plus it will
    # be more efficient for high values).
    _polling_backend = _poll_for
else:
    _polling_backend = _select_for

def _wait_for_readable(s, expiration):
    _wait_for(s, True, False, True, expiration)

def _wait_for_writable(s, expiration):
    _wait_for(s, False, True, True, expiration)

def _addresses_equal(af, a1, a2):
    # Convert the first value of the tuple, which is a textual format
    # address into binary form, so that we are not confused by different
    # textual representations of the same address
    n1 = dns.inet.inet_pton(af, a1[0])
    n2 = dns.inet.inet_pton(af, a2[0])
    return n1 == n2 and a1[1:] == a2[1:]

def _destination_and_source(af, where, port, source, source_port):
    # Apply defaults and compute destination and source tuples
    # suitable for use in connect(), sendto(), or bind().
    if af is None:
        try:
            af = dns.inet.af_for_address(where)
        except:
            af = dns.inet.AF_INET
    if af == dns.inet.AF_INET:
        destination = (where, port)
        if source is not None or source_port != 0:
            if source is None:
                source = '0.0.0.0'
            source = (source, source_port)
    elif af == dns.inet.AF_INET6:
        destination = (where, port, 0, 0)
        if source is not None or source_port != 0:
            if source is None:
                source = '::'
            source = (source, source_port, 0, 0)
    return (af, destination, source)

def udp(q, where, timeout=None, port=53, af=None, source=None, source_port=0,
        ignore_unexpected=False, one_rr_per_rrset=False):
    """Return the response obtained after sending a query via UDP.

    @param q: the query
    @type q: dns.message.Message
    @param where: where to send the message
    @type where: string containing an IPv4 or IPv6 address
    @param timeout: The number of seconds to wait before the query times out.
    If None, the default, wait forever.
    @type timeout: float
    @param port: The port to which to send the message.  The default is 53.
    @type port: int
    @param af: the address family to use.  The default is None, which
    causes the address family to use to be inferred from the form of of where.
    If the inference attempt fails, AF_INET is used.
    @type af: int
    @rtype: dns.message.Message object
    @param source: source address.  The default is the wildcard address.
    @type source: string
    @param source_port: The port from which to send the message.
    The default is 0.
    @type source_port: int
    @param ignore_unexpected: If True, ignore responses from unexpected
    sources.  The default is False.
    @type ignore_unexpected: bool
    @param one_rr_per_rrset: Put each RR into its own RRset
    @type one_rr_per_rrset: bool
    """

    wire = q.to_wire()
    (af, destination, source) = _destination_and_source(af, where, port, source,
                                                        source_port)
    s = socket.socket(af, socket.SOCK_DGRAM, 0)
    try:
        expiration = _compute_expiration(timeout)
        s.setblocking(0)
        if source is not None:
            s.bind(source)
        _wait_for_writable(s, expiration)
        s.sendto(wire, destination)
        while 1:
            _wait_for_readable(s, expiration)
            (wire, from_address) = s.recvfrom(65535)
            if _addresses_equal(af, from_address, destination) or \
                    (dns.inet.is_multicast(where) and \
                         from_address[1:] == destination[1:]):
                break
            if not ignore_unexpected:
                raise UnexpectedSource('got a response from '
                                       '%s instead of %s' % (from_address,
                                                             destination))
    finally:
        s.close()
    r = dns.message.from_wire(wire, keyring=q.keyring, request_mac=q.mac,
                              one_rr_per_rrset=one_rr_per_rrset)
    if not q.is_response(r):
        raise BadResponse
    return r

def _net_read(sock, count, expiration):
    """Read the specified number of bytes from sock.  Keep trying until we
    either get the desired amount, or we hit EOF.
    A Timeout exception will be raised if the operation is not completed
    by the expiration time.
    """
    s = ''
    while count > 0:
        _wait_for_readable(sock, expiration)
        n = sock.recv(count)
        if n == '':
            raise EOFError
        count = count - len(n)
        s = s + n
    return s

def _net_write(sock, data, expiration):
    """Write the specified data to the socket.
    A Timeout exception will be raised if the operation is not completed
    by the expiration time.
    """
    current = 0
    l = len(data)
    while current < l:
        _wait_for_writable(sock, expiration)
        current += sock.send(data[current:])

def _connect(s, address):
    try:
        s.connect(address)
    except socket.error:
        (ty, v) = sys.exc_info()[:2]
        if v[0] != errno.EINPROGRESS and \
               v[0] != errno.EWOULDBLOCK and \
               v[0] != errno.EALREADY:
            raise v

def tcp(q, where, timeout=None, port=53, af=None, source=None, source_port=0,
        one_rr_per_rrset=False):
    """Return the response obtained after sending a query via TCP.

    @param q: the query
    @type q: dns.message.Message object
    @param where: where to send the message
    @type where: string containing an IPv4 or IPv6 address
    @param timeout: The number of seconds to wait before the query times out.
    If None, the default, wait forever.
    @type timeout: float
    @param port: The port to which to send the message.  The default is 53.
    @type port: int
    @param af: the address family to use.  The default is None, which
    causes the address family to use to be inferred from the form of of where.
    If the inference attempt fails, AF_INET is used.
    @type af: int
    @rtype: dns.message.Message object
    @param source: source address.  The default is the wildcard address.
    @type source: string
    @param source_port: The port from which to send the message.
    The default is 0.
    @type source_port: int
    @param one_rr_per_rrset: Put each RR into its own RRset
    @type one_rr_per_rrset: bool
    """

    wire = q.to_wire()
    (af, destination, source) = _destination_and_source(af, where, port, source,
                                                        source_port)
    s = socket.socket(af, socket.SOCK_STREAM, 0)
    try:
        expiration = _compute_expiration(timeout)
        s.setblocking(0)
        if source is not None:
            s.bind(source)
        _connect(s, destination)

        l = len(wire)

        # copying the wire into tcpmsg is inefficient, but lets us
        # avoid writev() or doing a short write that would get pushed
        # onto the net
        tcpmsg = struct.pack("!H", l) + wire
        _net_write(s, tcpmsg, expiration)
        ldata = _net_read(s, 2, expiration)
        (l,) = struct.unpack("!H", ldata)
        wire = _net_read(s, l, expiration)
    finally:
        s.close()
    r = dns.message.from_wire(wire, keyring=q.keyring, request_mac=q.mac,
                              one_rr_per_rrset=one_rr_per_rrset)
    if not q.is_response(r):
        raise BadResponse
    return r

def xfr(where, zone, rdtype=dns.rdatatype.AXFR, rdclass=dns.rdataclass.IN,
        timeout=None, port=53, keyring=None, keyname=None, relativize=True,
        af=None, lifetime=None, source=None, source_port=0, serial=0,
        use_udp=False, keyalgorithm=dns.tsig.default_algorithm):
    """Return a generator for the responses to a zone transfer.

    @param where: where to send the message
    @type where: string containing an IPv4 or IPv6 address
    @param zone: The name of the zone to transfer
    @type zone: dns.name.Name object or string
    @param rdtype: The type of zone transfer.  The default is
    dns.rdatatype.AXFR.
    @type rdtype: int or string
    @param rdclass: The class of the zone transfer.  The default is
    dns.rdataclass.IN.
    @type rdclass: int or string
    @param timeout: The number of seconds to wait for each response message.
    If None, the default, wait forever.
    @type timeout: float
    @param port: The port to which to send the message.  The default is 53.
    @type port: int
    @param keyring: The TSIG keyring to use
    @type keyring: dict
    @param keyname: The name of the TSIG key to use
    @type keyname: dns.name.Name object or string
    @param relativize: If True, all names in the zone will be relativized to
    the zone origin.  It is essential that the relativize setting matches
    the one specified to dns.zone.from_xfr().
    @type relativize: bool
    @param af: the address family to use.  The default is None, which
    causes the address family to use to be inferred from the form of of where.
    If the inference attempt fails, AF_INET is used.
    @type af: int
    @param lifetime: The total number of seconds to spend doing the transfer.
    If None, the default, then there is no limit on the time the transfer may
    take.
    @type lifetime: float
    @rtype: generator of dns.message.Message objects.
    @param source: source address.  The default is the wildcard address.
    @type source: string
    @param source_port: The port from which to send the message.
    The default is 0.
    @type source_port: int
    @param serial: The SOA serial number to use as the base for an IXFR diff
    sequence (only meaningful if rdtype == dns.rdatatype.IXFR).
    @type serial: int
    @param use_udp: Use UDP (only meaningful for IXFR)
    @type use_udp: bool
    @param keyalgorithm: The TSIG algorithm to use; defaults to
    dns.tsig.default_algorithm
    @type keyalgorithm: string
    """

    if isinstance(zone, (str, unicode)):
        zone = dns.name.from_text(zone)
    if isinstance(rdtype, (str, unicode)):
        rdtype = dns.rdatatype.from_text(rdtype)
    q = dns.message.make_query(zone, rdtype, rdclass)
    if rdtype == dns.rdatatype.IXFR:
        rrset = dns.rrset.from_text(zone, 0, 'IN', 'SOA',
                                    '. . %u 0 0 0 0' % serial)
        q.authority.append(rrset)
    if not keyring is None:
        q.use_tsig(keyring, keyname, algorithm=keyalgorithm)
    wire = q.to_wire()
    (af, destination, source) = _destination_and_source(af, where, port, source,
                                                        source_port)
    if use_udp:
        if rdtype != dns.rdatatype.IXFR:
            raise ValueError('cannot do a UDP AXFR')
        s = socket.socket(af, socket.SOCK_DGRAM, 0)
    else:
        s = socket.socket(af, socket.SOCK_STREAM, 0)
    s.setblocking(0)
    if source is not None:
        s.bind(source)
    expiration = _compute_expiration(lifetime)
    _connect(s, destination)
    l = len(wire)
    if use_udp:
        _wait_for_writable(s, expiration)
        s.send(wire)
    else:
        tcpmsg = struct.pack("!H", l) + wire
        _net_write(s, tcpmsg, expiration)
    done = False
    delete_mode = True
    expecting_SOA = False
    soa_rrset = None
    soa_count = 0
    if relativize:
        origin = zone
        oname = dns.name.empty
    else:
        origin = None
        oname = zone
    tsig_ctx = None
    first = True
    while not done:
        mexpiration = _compute_expiration(timeout)
        if mexpiration is None or mexpiration > expiration:
            mexpiration = expiration
        if use_udp:
            _wait_for_readable(s, expiration)
            (wire, from_address) = s.recvfrom(65535)
        else:
            ldata = _net_read(s, 2, mexpiration)
            (l,) = struct.unpack("!H", ldata)
            wire = _net_read(s, l, mexpiration)
        r = dns.message.from_wire(wire, keyring=q.keyring, request_mac=q.mac,
                                  xfr=True, origin=origin, tsig_ctx=tsig_ctx,
                                  multi=True, first=first,
                                  one_rr_per_rrset=(rdtype==dns.rdatatype.IXFR))
        tsig_ctx = r.tsig_ctx
        first = False
        answer_index = 0
        if soa_rrset is None:
            if not r.answer or r.answer[0].name != oname:
                raise dns.exception.FormError("No answer or RRset not for qname")
            rrset = r.answer[0]
            if rrset.rdtype != dns.rdatatype.SOA:
                raise dns.exception.FormError("first RRset is not an SOA")
            answer_index = 1
            soa_rrset = rrset.copy()
            if rdtype == dns.rdatatype.IXFR:
                if soa_rrset[0].serial <= serial:
                    #
                    # We're already up-to-date.
                    #
                    done = True
                else:
                    expecting_SOA = True
        #
        # Process SOAs in the answer section (other than the initial
        # SOA in the first message).
        #
        for rrset in r.answer[answer_index:]:
            if done:
                raise dns.exception.FormError("answers after final SOA")
            if rrset.rdtype == dns.rdatatype.SOA and rrset.name == oname:
                if expecting_SOA:
                    if rrset[0].serial != serial:
                        raise dns.exception.FormError("IXFR base serial mismatch")
                    expecting_SOA = False
                elif rdtype == dns.rdatatype.IXFR:
                    delete_mode = not delete_mode
                #
                # If this SOA RRset is equal to the first we saw then we're
                # finished. If this is an IXFR we also check that we're seeing
                # the record in the expected part of the response.
                #
                if rrset == soa_rrset and \
                        (rdtype == dns.rdatatype.AXFR or \
                        (rdtype == dns.rdatatype.IXFR and delete_mode)):
                    done = True
            elif expecting_SOA:
                #
                # We made an IXFR request and are expecting another
                # SOA RR, but saw something else, so this must be an
                # AXFR response.
                #
                rdtype = dns.rdatatype.AXFR
                expecting_SOA = False
        if done and q.keyring and not r.had_tsig:
            raise dns.exception.FormError("missing TSIG")
        yield r
    s.close()

########NEW FILE########
__FILENAME__ = rcode
# Copyright (C) 2001-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS Result Codes."""

import dns.exception

NOERROR = 0
FORMERR = 1
SERVFAIL = 2
NXDOMAIN = 3
NOTIMP = 4
REFUSED = 5
YXDOMAIN = 6
YXRRSET = 7
NXRRSET = 8
NOTAUTH = 9
NOTZONE = 10
BADVERS = 16

_by_text = {
    'NOERROR' : NOERROR,
    'FORMERR' : FORMERR,
    'SERVFAIL' : SERVFAIL,
    'NXDOMAIN' : NXDOMAIN,
    'NOTIMP' : NOTIMP,
    'REFUSED' : REFUSED,
    'YXDOMAIN' : YXDOMAIN,
    'YXRRSET' : YXRRSET,
    'NXRRSET' : NXRRSET,
    'NOTAUTH' : NOTAUTH,
    'NOTZONE' : NOTZONE,
    'BADVERS' : BADVERS
}

# We construct the inverse mapping programmatically to ensure that we
# cannot make any mistakes (e.g. omissions, cut-and-paste errors) that
# would cause the mapping not to be a true inverse.

_by_value = dict([(y, x) for x, y in _by_text.iteritems()])


class UnknownRcode(dns.exception.DNSException):
    """Raised if an rcode is unknown."""
    pass

def from_text(text):
    """Convert text into an rcode.

    @param text: the texual rcode
    @type text: string
    @raises UnknownRcode: the rcode is unknown
    @rtype: int
    """

    if text.isdigit():
        v = int(text)
        if v >= 0 and v <= 4095:
            return v
    v = _by_text.get(text.upper())
    if v is None:
        raise UnknownRcode
    return v

def from_flags(flags, ednsflags):
    """Return the rcode value encoded by flags and ednsflags.

    @param flags: the DNS flags
    @type flags: int
    @param ednsflags: the EDNS flags
    @type ednsflags: int
    @raises ValueError: rcode is < 0 or > 4095
    @rtype: int
    """

    value = (flags & 0x000f) | ((ednsflags >> 20) & 0xff0)
    if value < 0 or value > 4095:
        raise ValueError('rcode must be >= 0 and <= 4095')
    return value

def to_flags(value):
    """Return a (flags, ednsflags) tuple which encodes the rcode.

    @param value: the rcode
    @type value: int
    @raises ValueError: rcode is < 0 or > 4095
    @rtype: (int, int) tuple
    """

    if value < 0 or value > 4095:
        raise ValueError('rcode must be >= 0 and <= 4095')
    v = value & 0xf
    ev = long(value & 0xff0) << 20
    return (v, ev)

def to_text(value):
    """Convert rcode into text.

    @param value: the rcode
    @type value: int
    @rtype: string
    """

    text = _by_value.get(value)
    if text is None:
        text = str(value)
    return text

########NEW FILE########
__FILENAME__ = rdata
# Copyright (C) 2001-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS rdata.

@var _rdata_modules: A dictionary mapping a (rdclass, rdtype) tuple to
the module which implements that type.
@type _rdata_modules: dict
@var _module_prefix: The prefix to use when forming modules names.  The
default is 'dns.rdtypes'.  Changing this value will break the library.
@type _module_prefix: string
@var _hex_chunk: At most this many octets that will be represented in each
chunk of hexstring that _hexify() produces before whitespace occurs.
@type _hex_chunk: int"""

import cStringIO

import dns.exception
import dns.name
import dns.rdataclass
import dns.rdatatype
import dns.tokenizer
import dns.wiredata

_hex_chunksize = 32

def _hexify(data, chunksize=None):
    """Convert a binary string into its hex encoding, broken up into chunks
    of I{chunksize} characters separated by a space.

    @param data: the binary string
    @type data: string
    @param chunksize: the chunk size.  Default is L{dns.rdata._hex_chunksize}
    @rtype: string
    """

    if chunksize is None:
        chunksize = _hex_chunksize
    hex = data.encode('hex_codec')
    l = len(hex)
    if l > chunksize:
        chunks = []
        i = 0
        while i < l:
            chunks.append(hex[i : i + chunksize])
            i += chunksize
        hex = ' '.join(chunks)
    return hex

_base64_chunksize = 32

def _base64ify(data, chunksize=None):
    """Convert a binary string into its base64 encoding, broken up into chunks
    of I{chunksize} characters separated by a space.

    @param data: the binary string
    @type data: string
    @param chunksize: the chunk size.  Default is
    L{dns.rdata._base64_chunksize}
    @rtype: string
    """

    if chunksize is None:
        chunksize = _base64_chunksize
    b64 = data.encode('base64_codec')
    b64 = b64.replace('\n', '')
    l = len(b64)
    if l > chunksize:
        chunks = []
        i = 0
        while i < l:
            chunks.append(b64[i : i + chunksize])
            i += chunksize
        b64 = ' '.join(chunks)
    return b64

__escaped = {
    '"' : True,
    '\\' : True,
    }

def _escapify(qstring):
    """Escape the characters in a quoted string which need it.

    @param qstring: the string
    @type qstring: string
    @returns: the escaped string
    @rtype: string
    """

    text = ''
    for c in qstring:
        if c in __escaped:
            text += '\\' + c
        elif ord(c) >= 0x20 and ord(c) < 0x7F:
            text += c
        else:
            text += '\\%03d' % ord(c)
    return text

def _truncate_bitmap(what):
    """Determine the index of greatest byte that isn't all zeros, and
    return the bitmap that contains all the bytes less than that index.

    @param what: a string of octets representing a bitmap.
    @type what: string
    @rtype: string
    """

    for i in xrange(len(what) - 1, -1, -1):
        if what[i] != '\x00':
            break
    return ''.join(what[0 : i + 1])

class Rdata(object):
    """Base class for all DNS rdata types.
    """

    __slots__ = ['rdclass', 'rdtype']

    def __init__(self, rdclass, rdtype):
        """Initialize an rdata.
        @param rdclass: The rdata class
        @type rdclass: int
        @param rdtype: The rdata type
        @type rdtype: int
        """

        self.rdclass = rdclass
        self.rdtype = rdtype

    def covers(self):
        """DNS SIG/RRSIG rdatas apply to a specific type; this type is
        returned by the covers() function.  If the rdata type is not
        SIG or RRSIG, dns.rdatatype.NONE is returned.  This is useful when
        creating rdatasets, allowing the rdataset to contain only RRSIGs
        of a particular type, e.g. RRSIG(NS).
        @rtype: int
        """

        return dns.rdatatype.NONE

    def extended_rdatatype(self):
        """Return a 32-bit type value, the least significant 16 bits of
        which are the ordinary DNS type, and the upper 16 bits of which are
        the "covered" type, if any.
        @rtype: int
        """

        return self.covers() << 16 | self.rdtype

    def to_text(self, origin=None, relativize=True, **kw):
        """Convert an rdata to text format.
        @rtype: string
        """
        raise NotImplementedError

    def to_wire(self, file, compress = None, origin = None):
        """Convert an rdata to wire format.
        @rtype: string
        """

        raise NotImplementedError

    def to_digestable(self, origin = None):
        """Convert rdata to a format suitable for digesting in hashes.  This
        is also the DNSSEC canonical form."""
        f = cStringIO.StringIO()
        self.to_wire(f, None, origin)
        return f.getvalue()

    def validate(self):
        """Check that the current contents of the rdata's fields are
        valid.  If you change an rdata by assigning to its fields,
        it is a good idea to call validate() when you are done making
        changes.
        """
        dns.rdata.from_text(self.rdclass, self.rdtype, self.to_text())

    def __repr__(self):
        covers = self.covers()
        if covers == dns.rdatatype.NONE:
            ctext = ''
        else:
            ctext = '(' + dns.rdatatype.to_text(covers) + ')'
        return '<DNS ' + dns.rdataclass.to_text(self.rdclass) + ' ' + \
               dns.rdatatype.to_text(self.rdtype) + ctext + ' rdata: ' + \
               str(self) + '>'

    def __str__(self):
        return self.to_text()

    def _cmp(self, other):
        """Compare an rdata with another rdata of the same rdtype and
        rdclass.  Return < 0 if self < other in the DNSSEC ordering,
        0 if self == other, and > 0 if self > other.
        """

        raise NotImplementedError

    def __eq__(self, other):
        if not isinstance(other, Rdata):
            return False
        if self.rdclass != other.rdclass or \
           self.rdtype != other.rdtype:
            return False
        return self._cmp(other) == 0

    def __ne__(self, other):
        if not isinstance(other, Rdata):
            return True
        if self.rdclass != other.rdclass or \
           self.rdtype != other.rdtype:
            return True
        return self._cmp(other) != 0

    def __lt__(self, other):
        if not isinstance(other, Rdata) or \
               self.rdclass != other.rdclass or \
               self.rdtype != other.rdtype:
            return NotImplemented
        return self._cmp(other) < 0

    def __le__(self, other):
        if not isinstance(other, Rdata) or \
               self.rdclass != other.rdclass or \
               self.rdtype != other.rdtype:
            return NotImplemented
        return self._cmp(other) <= 0

    def __ge__(self, other):
        if not isinstance(other, Rdata) or \
               self.rdclass != other.rdclass or \
               self.rdtype != other.rdtype:
            return NotImplemented
        return self._cmp(other) >= 0

    def __gt__(self, other):
        if not isinstance(other, Rdata) or \
               self.rdclass != other.rdclass or \
               self.rdtype != other.rdtype:
            return NotImplemented
        return self._cmp(other) > 0

    def __hash__(self):
        return hash(self.to_digestable(dns.name.root))

    def _wire_cmp(self, other):
        # A number of types compare rdata in wire form, so we provide
        # the method here instead of duplicating it.
        #
        # We specifiy an arbitrary origin of '.' when doing the
        # comparison, since the rdata may have relative names and we
        # can't convert a relative name to wire without an origin.
        b1 = cStringIO.StringIO()
        self.to_wire(b1, None, dns.name.root)
        b2 = cStringIO.StringIO()
        other.to_wire(b2, None, dns.name.root)
        return cmp(b1.getvalue(), b2.getvalue())

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        """Build an rdata object from text format.

        @param rdclass: The rdata class
        @type rdclass: int
        @param rdtype: The rdata type
        @type rdtype: int
        @param tok: The tokenizer
        @type tok: dns.tokenizer.Tokenizer
        @param origin: The origin to use for relative names
        @type origin: dns.name.Name
        @param relativize: should names be relativized?
        @type relativize: bool
        @rtype: dns.rdata.Rdata instance
        """

        raise NotImplementedError

    from_text = classmethod(from_text)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        """Build an rdata object from wire format

        @param rdclass: The rdata class
        @type rdclass: int
        @param rdtype: The rdata type
        @type rdtype: int
        @param wire: The wire-format message
        @type wire: string
        @param current: The offet in wire of the beginning of the rdata.
        @type current: int
        @param rdlen: The length of the wire-format rdata
        @type rdlen: int
        @param origin: The origin to use for relative names
        @type origin: dns.name.Name
        @rtype: dns.rdata.Rdata instance
        """

        raise NotImplementedError

    from_wire = classmethod(from_wire)

    def choose_relativity(self, origin = None, relativize = True):
        """Convert any domain names in the rdata to the specified
        relativization.
        """

        pass


class GenericRdata(Rdata):
    """Generate Rdata Class

    This class is used for rdata types for which we have no better
    implementation.  It implements the DNS "unknown RRs" scheme.
    """

    __slots__ = ['data']

    def __init__(self, rdclass, rdtype, data):
        super(GenericRdata, self).__init__(rdclass, rdtype)
        self.data = data

    def to_text(self, origin=None, relativize=True, **kw):
        return r'\# %d ' % len(self.data) + _hexify(self.data)

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        token = tok.get()
        if not token.is_identifier() or token.value != '\#':
            raise dns.exception.SyntaxError(r'generic rdata does not start with \#')
        length = tok.get_int()
        chunks = []
        while 1:
            token = tok.get()
            if token.is_eol_or_eof():
                break
            chunks.append(token.value)
        hex = ''.join(chunks)
        data = hex.decode('hex_codec')
        if len(data) != length:
            raise dns.exception.SyntaxError('generic rdata hex data has wrong length')
        return cls(rdclass, rdtype, data)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        file.write(self.data)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        return cls(rdclass, rdtype, wire[current : current + rdlen])

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        return cmp(self.data, other.data)

_rdata_modules = {}
_module_prefix = 'dns.rdtypes'

def get_rdata_class(rdclass, rdtype):

    def import_module(name):
        mod = __import__(name)
        components = name.split('.')
        for comp in components[1:]:
            mod = getattr(mod, comp)
        return mod

    mod = _rdata_modules.get((rdclass, rdtype))
    rdclass_text = dns.rdataclass.to_text(rdclass)
    rdtype_text = dns.rdatatype.to_text(rdtype)
    rdtype_text = rdtype_text.replace('-', '_')
    if not mod:
        mod = _rdata_modules.get((dns.rdatatype.ANY, rdtype))
        if not mod:
            try:
                mod = import_module('.'.join([_module_prefix,
                                              rdclass_text, rdtype_text]))
                _rdata_modules[(rdclass, rdtype)] = mod
            except ImportError:
                try:
                    mod = import_module('.'.join([_module_prefix,
                                                  'ANY', rdtype_text]))
                    _rdata_modules[(dns.rdataclass.ANY, rdtype)] = mod
                except ImportError:
                    mod = None
    if mod:
        cls = getattr(mod, rdtype_text)
    else:
        cls = GenericRdata
    return cls

def from_text(rdclass, rdtype, tok, origin = None, relativize = True):
    """Build an rdata object from text format.

    This function attempts to dynamically load a class which
    implements the specified rdata class and type.  If there is no
    class-and-type-specific implementation, the GenericRdata class
    is used.

    Once a class is chosen, its from_text() class method is called
    with the parameters to this function.

    If I{tok} is a string, then a tokenizer is created and the string
    is used as its input.

    @param rdclass: The rdata class
    @type rdclass: int
    @param rdtype: The rdata type
    @type rdtype: int
    @param tok: The tokenizer or input text
    @type tok: dns.tokenizer.Tokenizer or string
    @param origin: The origin to use for relative names
    @type origin: dns.name.Name
    @param relativize: Should names be relativized?
    @type relativize: bool
    @rtype: dns.rdata.Rdata instance"""

    if isinstance(tok, str):
        tok = dns.tokenizer.Tokenizer(tok)
    cls = get_rdata_class(rdclass, rdtype)
    if cls != GenericRdata:
        # peek at first token
        token = tok.get()
        tok.unget(token)
        if token.is_identifier() and \
           token.value == r'\#':
            #
            # Known type using the generic syntax.  Extract the
            # wire form from the generic syntax, and then run
            # from_wire on it.
            #
            rdata = GenericRdata.from_text(rdclass, rdtype, tok, origin,
                                           relativize)
            return from_wire(rdclass, rdtype, rdata.data, 0, len(rdata.data),
                             origin)
    return cls.from_text(rdclass, rdtype, tok, origin, relativize)

def from_wire(rdclass, rdtype, wire, current, rdlen, origin = None):
    """Build an rdata object from wire format

    This function attempts to dynamically load a class which
    implements the specified rdata class and type.  If there is no
    class-and-type-specific implementation, the GenericRdata class
    is used.

    Once a class is chosen, its from_wire() class method is called
    with the parameters to this function.

    @param rdclass: The rdata class
    @type rdclass: int
    @param rdtype: The rdata type
    @type rdtype: int
    @param wire: The wire-format message
    @type wire: string
    @param current: The offet in wire of the beginning of the rdata.
    @type current: int
    @param rdlen: The length of the wire-format rdata
    @type rdlen: int
    @param origin: The origin to use for relative names
    @type origin: dns.name.Name
    @rtype: dns.rdata.Rdata instance"""

    wire = dns.wiredata.maybe_wrap(wire)
    cls = get_rdata_class(rdclass, rdtype)
    return cls.from_wire(rdclass, rdtype, wire, current, rdlen, origin)

########NEW FILE########
__FILENAME__ = rdataclass
# Copyright (C) 2001-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS Rdata Classes.

@var _by_text: The rdata class textual name to value mapping
@type _by_text: dict
@var _by_value: The rdata class value to textual name mapping
@type _by_value: dict
@var _metaclasses: If an rdataclass is a metaclass, there will be a mapping
whose key is the rdatatype value and whose value is True in this dictionary.
@type _metaclasses: dict"""

import re

import dns.exception

RESERVED0 = 0
IN = 1
CH = 3
HS = 4
NONE = 254
ANY = 255

_by_text = {
    'RESERVED0' : RESERVED0,
    'IN' : IN,
    'CH' : CH,
    'HS' : HS,
    'NONE' : NONE,
    'ANY' : ANY
    }

# We construct the inverse mapping programmatically to ensure that we
# cannot make any mistakes (e.g. omissions, cut-and-paste errors) that
# would cause the mapping not to be true inverse.

_by_value = dict([(y, x) for x, y in _by_text.iteritems()])

# Now that we've built the inverse map, we can add class aliases to
# the _by_text mapping.

_by_text.update({
    'INTERNET' : IN,
    'CHAOS' : CH,
    'HESIOD' : HS
    })

_metaclasses = {
    NONE : True,
    ANY : True
    }

_unknown_class_pattern = re.compile('CLASS([0-9]+)$', re.I);

class UnknownRdataclass(dns.exception.DNSException):
    """Raised when a class is unknown."""
    pass

def from_text(text):
    """Convert text into a DNS rdata class value.
    @param text: the text
    @type text: string
    @rtype: int
    @raises dns.rdataclass.UnknownRdataclass: the class is unknown
    @raises ValueError: the rdata class value is not >= 0 and <= 65535
    """

    value = _by_text.get(text.upper())
    if value is None:
        match = _unknown_class_pattern.match(text)
        if match == None:
            raise UnknownRdataclass
        value = int(match.group(1))
        if value < 0 or value > 65535:
            raise ValueError("class must be between >= 0 and <= 65535")
    return value

def to_text(value):
    """Convert a DNS rdata class to text.
    @param value: the rdata class value
    @type value: int
    @rtype: string
    @raises ValueError: the rdata class value is not >= 0 and <= 65535
    """

    if value < 0 or value > 65535:
        raise ValueError("class must be between >= 0 and <= 65535")
    text = _by_value.get(value)
    if text is None:
        text = 'CLASS' + `value`
    return text

def is_metaclass(rdclass):
    """True if the class is a metaclass.
    @param rdclass: the rdata class
    @type rdclass: int
    @rtype: bool"""

    if _metaclasses.has_key(rdclass):
        return True
    return False

########NEW FILE########
__FILENAME__ = rdataset
# Copyright (C) 2001-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS rdatasets (an rdataset is a set of rdatas of a given type and class)"""

import random
import StringIO
import struct

import dns.exception
import dns.rdatatype
import dns.rdataclass
import dns.rdata
import dns.set

# define SimpleSet here for backwards compatibility
SimpleSet = dns.set.Set

class DifferingCovers(dns.exception.DNSException):
    """Raised if an attempt is made to add a SIG/RRSIG whose covered type
    is not the same as that of the other rdatas in the rdataset."""
    pass

class IncompatibleTypes(dns.exception.DNSException):
    """Raised if an attempt is made to add rdata of an incompatible type."""
    pass

class Rdataset(dns.set.Set):
    """A DNS rdataset.

    @ivar rdclass: The class of the rdataset
    @type rdclass: int
    @ivar rdtype: The type of the rdataset
    @type rdtype: int
    @ivar covers: The covered type.  Usually this value is
    dns.rdatatype.NONE, but if the rdtype is dns.rdatatype.SIG or
    dns.rdatatype.RRSIG, then the covers value will be the rdata
    type the SIG/RRSIG covers.  The library treats the SIG and RRSIG
    types as if they were a family of
    types, e.g. RRSIG(A), RRSIG(NS), RRSIG(SOA).  This makes RRSIGs much
    easier to work with than if RRSIGs covering different rdata
    types were aggregated into a single RRSIG rdataset.
    @type covers: int
    @ivar ttl: The DNS TTL (Time To Live) value
    @type ttl: int
    """

    __slots__ = ['rdclass', 'rdtype', 'covers', 'ttl']

    def __init__(self, rdclass, rdtype, covers=dns.rdatatype.NONE):
        """Create a new rdataset of the specified class and type.

        @see: the description of the class instance variables for the
        meaning of I{rdclass} and I{rdtype}"""

        super(Rdataset, self).__init__()
        self.rdclass = rdclass
        self.rdtype = rdtype
        self.covers = covers
        self.ttl = 0

    def _clone(self):
        obj = super(Rdataset, self)._clone()
        obj.rdclass = self.rdclass
        obj.rdtype = self.rdtype
        obj.covers = self.covers
        obj.ttl = self.ttl
        return obj

    def update_ttl(self, ttl):
        """Set the TTL of the rdataset to be the lesser of the set's current
        TTL or the specified TTL.  If the set contains no rdatas, set the TTL
        to the specified TTL.
        @param ttl: The TTL
        @type ttl: int"""

        if len(self) == 0:
            self.ttl = ttl
        elif ttl < self.ttl:
            self.ttl = ttl

    def add(self, rd, ttl=None):
        """Add the specified rdata to the rdataset.

        If the optional I{ttl} parameter is supplied, then
        self.update_ttl(ttl) will be called prior to adding the rdata.

        @param rd: The rdata
        @type rd: dns.rdata.Rdata object
        @param ttl: The TTL
        @type ttl: int"""

        #
        # If we're adding a signature, do some special handling to
        # check that the signature covers the same type as the
        # other rdatas in this rdataset.  If this is the first rdata
        # in the set, initialize the covers field.
        #
        if self.rdclass != rd.rdclass or self.rdtype != rd.rdtype:
            raise IncompatibleTypes
        if not ttl is None:
            self.update_ttl(ttl)
        if self.rdtype == dns.rdatatype.RRSIG or \
           self.rdtype == dns.rdatatype.SIG:
            covers = rd.covers()
            if len(self) == 0 and self.covers == dns.rdatatype.NONE:
                self.covers = covers
            elif self.covers != covers:
                raise DifferingCovers
        if dns.rdatatype.is_singleton(rd.rdtype) and len(self) > 0:
            self.clear()
        super(Rdataset, self).add(rd)

    def union_update(self, other):
        self.update_ttl(other.ttl)
        super(Rdataset, self).union_update(other)

    def intersection_update(self, other):
        self.update_ttl(other.ttl)
        super(Rdataset, self).intersection_update(other)

    def update(self, other):
        """Add all rdatas in other to self.

        @param other: The rdataset from which to update
        @type other: dns.rdataset.Rdataset object"""

        self.update_ttl(other.ttl)
        super(Rdataset, self).update(other)

    def __repr__(self):
        if self.covers == 0:
            ctext = ''
        else:
            ctext = '(' + dns.rdatatype.to_text(self.covers) + ')'
        return '<DNS ' + dns.rdataclass.to_text(self.rdclass) + ' ' + \
               dns.rdatatype.to_text(self.rdtype) + ctext + ' rdataset>'

    def __str__(self):
        return self.to_text()

    def __eq__(self, other):
        """Two rdatasets are equal if they have the same class, type, and
        covers, and contain the same rdata.
        @rtype: bool"""

        if not isinstance(other, Rdataset):
            return False
        if self.rdclass != other.rdclass or \
           self.rdtype != other.rdtype or \
           self.covers != other.covers:
            return False
        return super(Rdataset, self).__eq__(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def to_text(self, name=None, origin=None, relativize=True,
                override_rdclass=None, **kw):
        """Convert the rdataset into DNS master file format.

        @see: L{dns.name.Name.choose_relativity} for more information
        on how I{origin} and I{relativize} determine the way names
        are emitted.

        Any additional keyword arguments are passed on to the rdata
        to_text() method.

        @param name: If name is not None, emit a RRs with I{name} as
        the owner name.
        @type name: dns.name.Name object
        @param origin: The origin for relative names, or None.
        @type origin: dns.name.Name object
        @param relativize: True if names should names be relativized
        @type relativize: bool"""
        if not name is None:
            name = name.choose_relativity(origin, relativize)
            ntext = str(name)
            pad = ' '
        else:
            ntext = ''
            pad = ''
        s = StringIO.StringIO()
        if not override_rdclass is None:
            rdclass = override_rdclass
        else:
            rdclass = self.rdclass
        if len(self) == 0:
            #
            # Empty rdatasets are used for the question section, and in
            # some dynamic updates, so we don't need to print out the TTL
            # (which is meaningless anyway).
            #
            print >> s, '%s%s%s %s' % (ntext, pad,
                                       dns.rdataclass.to_text(rdclass),
                                       dns.rdatatype.to_text(self.rdtype))
        else:
            for rd in self:
                print >> s, '%s%s%d %s %s %s' % \
                      (ntext, pad, self.ttl, dns.rdataclass.to_text(rdclass),
                       dns.rdatatype.to_text(self.rdtype),
                       rd.to_text(origin=origin, relativize=relativize, **kw))
        #
        # We strip off the final \n for the caller's convenience in printing
        #
        return s.getvalue()[:-1]

    def to_wire(self, name, file, compress=None, origin=None,
                override_rdclass=None, want_shuffle=True):
        """Convert the rdataset to wire format.

        @param name: The owner name of the RRset that will be emitted
        @type name: dns.name.Name object
        @param file: The file to which the wire format data will be appended
        @type file: file
        @param compress: The compression table to use; the default is None.
        @type compress: dict
        @param origin: The origin to be appended to any relative names when
        they are emitted.  The default is None.
        @returns: the number of records emitted
        @rtype: int
        """

        if not override_rdclass is None:
            rdclass =  override_rdclass
            want_shuffle = False
        else:
            rdclass = self.rdclass
        file.seek(0, 2)
        if len(self) == 0:
            name.to_wire(file, compress, origin)
            stuff = struct.pack("!HHIH", self.rdtype, rdclass, 0, 0)
            file.write(stuff)
            return 1
        else:
            if want_shuffle:
                l = list(self)
                random.shuffle(l)
            else:
                l = self
            for rd in l:
                name.to_wire(file, compress, origin)
                stuff = struct.pack("!HHIH", self.rdtype, rdclass,
                                    self.ttl, 0)
                file.write(stuff)
                start = file.tell()
                rd.to_wire(file, compress, origin)
                end = file.tell()
                assert end - start < 65536
                file.seek(start - 2)
                stuff = struct.pack("!H", end - start)
                file.write(stuff)
                file.seek(0, 2)
            return len(self)

    def match(self, rdclass, rdtype, covers):
        """Returns True if this rdataset matches the specified class, type,
        and covers"""
        if self.rdclass == rdclass and \
           self.rdtype == rdtype and \
           self.covers == covers:
            return True
        return False

def from_text_list(rdclass, rdtype, ttl, text_rdatas):
    """Create an rdataset with the specified class, type, and TTL, and with
    the specified list of rdatas in text format.

    @rtype: dns.rdataset.Rdataset object
    """

    if isinstance(rdclass, (str, unicode)):
        rdclass = dns.rdataclass.from_text(rdclass)
    if isinstance(rdtype, (str, unicode)):
        rdtype = dns.rdatatype.from_text(rdtype)
    r = Rdataset(rdclass, rdtype)
    r.update_ttl(ttl)
    for t in text_rdatas:
        rd = dns.rdata.from_text(r.rdclass, r.rdtype, t)
        r.add(rd)
    return r

def from_text(rdclass, rdtype, ttl, *text_rdatas):
    """Create an rdataset with the specified class, type, and TTL, and with
    the specified rdatas in text format.

    @rtype: dns.rdataset.Rdataset object
    """

    return from_text_list(rdclass, rdtype, ttl, text_rdatas)

def from_rdata_list(ttl, rdatas):
    """Create an rdataset with the specified TTL, and with
    the specified list of rdata objects.

    @rtype: dns.rdataset.Rdataset object
    """

    if len(rdatas) == 0:
        raise ValueError("rdata list must not be empty")
    r = None
    for rd in rdatas:
        if r is None:
            r = Rdataset(rd.rdclass, rd.rdtype)
            r.update_ttl(ttl)
            first_time = False
        r.add(rd)
    return r

def from_rdata(ttl, *rdatas):
    """Create an rdataset with the specified TTL, and with
    the specified rdata objects.

    @rtype: dns.rdataset.Rdataset object
    """

    return from_rdata_list(ttl, rdatas)

########NEW FILE########
__FILENAME__ = rdatatype
# Copyright (C) 2001-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS Rdata Types.

@var _by_text: The rdata type textual name to value mapping
@type _by_text: dict
@var _by_value: The rdata type value to textual name mapping
@type _by_value: dict
@var _metatypes: If an rdatatype is a metatype, there will be a mapping
whose key is the rdatatype value and whose value is True in this dictionary.
@type _metatypes: dict
@var _singletons: If an rdatatype is a singleton, there will be a mapping
whose key is the rdatatype value and whose value is True in this dictionary.
@type _singletons: dict"""

import re

import dns.exception

NONE = 0
A = 1
NS = 2
MD = 3
MF = 4
CNAME = 5
SOA = 6
MB = 7
MG = 8
MR = 9
NULL = 10
WKS = 11
PTR = 12
HINFO = 13
MINFO = 14
MX = 15
TXT = 16
RP = 17
AFSDB = 18
X25 = 19
ISDN = 20
RT = 21
NSAP = 22
NSAP_PTR = 23
SIG = 24
KEY = 25
PX = 26
GPOS = 27
AAAA = 28
LOC = 29
NXT = 30
SRV = 33
NAPTR = 35
KX = 36
CERT = 37
A6 = 38
DNAME = 39
OPT = 41
APL = 42
DS = 43
SSHFP = 44
IPSECKEY = 45
RRSIG = 46
NSEC = 47
DNSKEY = 48
DHCID = 49
NSEC3 = 50
NSEC3PARAM = 51
TLSA = 52
HIP = 55
SPF = 99
UNSPEC = 103
TKEY = 249
TSIG = 250
IXFR = 251
AXFR = 252
MAILB = 253
MAILA = 254
ANY = 255
TA = 32768
DLV = 32769

_by_text = {
    'NONE' : NONE,
    'A' : A,
    'NS' : NS,
    'MD' : MD,
    'MF' : MF,
    'CNAME' : CNAME,
    'SOA' : SOA,
    'MB' : MB,
    'MG' : MG,
    'MR' : MR,
    'NULL' : NULL,
    'WKS' : WKS,
    'PTR' : PTR,
    'HINFO' : HINFO,
    'MINFO' : MINFO,
    'MX' : MX,
    'TXT' : TXT,
    'RP' : RP,
    'AFSDB' : AFSDB,
    'X25' : X25,
    'ISDN' : ISDN,
    'RT' : RT,
    'NSAP' : NSAP,
    'NSAP-PTR' : NSAP_PTR,
    'SIG' : SIG,
    'KEY' : KEY,
    'PX' : PX,
    'GPOS' : GPOS,
    'AAAA' : AAAA,
    'LOC' : LOC,
    'NXT' : NXT,
    'SRV' : SRV,
    'NAPTR' : NAPTR,
    'KX' : KX,
    'CERT' : CERT,
    'A6' : A6,
    'DNAME' : DNAME,
    'OPT' : OPT,
    'APL' : APL,
    'DS' : DS,
    'SSHFP' : SSHFP,
    'IPSECKEY' : IPSECKEY,
    'RRSIG' : RRSIG,
    'NSEC' : NSEC,
    'DNSKEY' : DNSKEY,
    'DHCID' : DHCID,
    'NSEC3' : NSEC3,
    'NSEC3PARAM' : NSEC3PARAM,
    'TLSA' : TLSA,
    'HIP' : HIP,
    'SPF' : SPF,
    'UNSPEC' : UNSPEC,
    'TKEY' : TKEY,
    'TSIG' : TSIG,
    'IXFR' : IXFR,
    'AXFR' : AXFR,
    'MAILB' : MAILB,
    'MAILA' : MAILA,
    'ANY' : ANY,
    'TA' : TA,
    'DLV' : DLV,
    }

# We construct the inverse mapping programmatically to ensure that we
# cannot make any mistakes (e.g. omissions, cut-and-paste errors) that
# would cause the mapping not to be true inverse.

_by_value = dict([(y, x) for x, y in _by_text.iteritems()])


_metatypes = {
    OPT : True
    }

_singletons = {
    SOA : True,
    NXT : True,
    DNAME : True,
    NSEC : True,
    # CNAME is technically a singleton, but we allow multiple CNAMEs.
    }

_unknown_type_pattern = re.compile('TYPE([0-9]+)$', re.I);

class UnknownRdatatype(dns.exception.DNSException):
    """Raised if a type is unknown."""
    pass

def from_text(text):
    """Convert text into a DNS rdata type value.
    @param text: the text
    @type text: string
    @raises dns.rdatatype.UnknownRdatatype: the type is unknown
    @raises ValueError: the rdata type value is not >= 0 and <= 65535
    @rtype: int"""

    value = _by_text.get(text.upper())
    if value is None:
        match = _unknown_type_pattern.match(text)
        if match == None:
            raise UnknownRdatatype
        value = int(match.group(1))
        if value < 0 or value > 65535:
            raise ValueError("type must be between >= 0 and <= 65535")
    return value

def to_text(value):
    """Convert a DNS rdata type to text.
    @param value: the rdata type value
    @type value: int
    @raises ValueError: the rdata type value is not >= 0 and <= 65535
    @rtype: string"""

    if value < 0 or value > 65535:
        raise ValueError("type must be between >= 0 and <= 65535")
    text = _by_value.get(value)
    if text is None:
        text = 'TYPE' + `value`
    return text

def is_metatype(rdtype):
    """True if the type is a metatype.
    @param rdtype: the type
    @type rdtype: int
    @rtype: bool"""

    if rdtype >= TKEY and rdtype <= ANY or _metatypes.has_key(rdtype):
        return True
    return False

def is_singleton(rdtype):
    """True if the type is a singleton.
    @param rdtype: the type
    @type rdtype: int
    @rtype: bool"""

    if _singletons.has_key(rdtype):
        return True
    return False

########NEW FILE########
__FILENAME__ = AFSDB
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import dns.rdtypes.mxbase

class AFSDB(dns.rdtypes.mxbase.UncompressedDowncasingMX):
    """AFSDB record

    @ivar subtype: the subtype value
    @type subtype: int
    @ivar hostname: the hostname name
    @type hostname: dns.name.Name object"""

    # Use the property mechanism to make "subtype" an alias for the
    # "preference" attribute, and "hostname" an alias for the "exchange"
    # attribute.
    #
    # This lets us inherit the UncompressedMX implementation but lets
    # the caller use appropriate attribute names for the rdata type.
    #
    # We probably lose some performance vs. a cut-and-paste
    # implementation, but this way we don't copy code, and that's
    # good.

    def get_subtype(self):
        return self.preference

    def set_subtype(self, subtype):
        self.preference = subtype

    subtype = property(get_subtype, set_subtype)

    def get_hostname(self):
        return self.exchange

    def set_hostname(self, hostname):
        self.exchange = hostname

    hostname = property(get_hostname, set_hostname)

########NEW FILE########
__FILENAME__ = CERT
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import cStringIO
import struct

import dns.exception
import dns.dnssec
import dns.rdata
import dns.tokenizer

_ctype_by_value = {
    1 : 'PKIX',
    2 : 'SPKI',
    3 : 'PGP',
    253 : 'URI',
    254 : 'OID',
    }

_ctype_by_name = {
    'PKIX' : 1,
    'SPKI' : 2,
    'PGP' : 3,
    'URI' : 253,
    'OID' : 254,
    }

def _ctype_from_text(what):
    v = _ctype_by_name.get(what)
    if not v is None:
        return v
    return int(what)

def _ctype_to_text(what):
    v = _ctype_by_value.get(what)
    if not v is None:
        return v
    return str(what)

class CERT(dns.rdata.Rdata):
    """CERT record

    @ivar certificate_type: certificate type
    @type certificate_type: int
    @ivar key_tag: key tag
    @type key_tag: int
    @ivar algorithm: algorithm
    @type algorithm: int
    @ivar certificate: the certificate or CRL
    @type certificate: string
    @see: RFC 2538"""

    __slots__ = ['certificate_type', 'key_tag', 'algorithm', 'certificate']

    def __init__(self, rdclass, rdtype, certificate_type, key_tag, algorithm,
                 certificate):
        super(CERT, self).__init__(rdclass, rdtype)
        self.certificate_type = certificate_type
        self.key_tag = key_tag
        self.algorithm = algorithm
        self.certificate = certificate

    def to_text(self, origin=None, relativize=True, **kw):
        certificate_type = _ctype_to_text(self.certificate_type)
        return "%s %d %s %s" % (certificate_type, self.key_tag,
                                dns.dnssec.algorithm_to_text(self.algorithm),
                                dns.rdata._base64ify(self.certificate))

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        certificate_type = _ctype_from_text(tok.get_string())
        key_tag = tok.get_uint16()
        algorithm = dns.dnssec.algorithm_from_text(tok.get_string())
        if algorithm < 0 or algorithm > 255:
            raise dns.exception.SyntaxError("bad algorithm type")
        chunks = []
        while 1:
            t = tok.get().unescape()
            if t.is_eol_or_eof():
                break
            if not t.is_identifier():
                raise dns.exception.SyntaxError
            chunks.append(t.value)
        b64 = ''.join(chunks)
        certificate = b64.decode('base64_codec')
        return cls(rdclass, rdtype, certificate_type, key_tag,
                   algorithm, certificate)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        prefix = struct.pack("!HHB", self.certificate_type, self.key_tag,
                             self.algorithm)
        file.write(prefix)
        file.write(self.certificate)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        prefix = wire[current : current + 5].unwrap()
        current += 5
        rdlen -= 5
        if rdlen < 0:
            raise dns.exception.FormError
        (certificate_type, key_tag, algorithm) = struct.unpack("!HHB", prefix)
        certificate = wire[current : current + rdlen].unwrap()
        return cls(rdclass, rdtype, certificate_type, key_tag, algorithm,
                   certificate)

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        f = cStringIO.StringIO()
        self.to_wire(f)
        wire1 = f.getvalue()
        f.seek(0)
        f.truncate()
        other.to_wire(f)
        wire2 = f.getvalue()
        f.close()

        return cmp(wire1, wire2)

########NEW FILE########
__FILENAME__ = CNAME
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import dns.rdtypes.nsbase

class CNAME(dns.rdtypes.nsbase.NSBase):
    """CNAME record

    Note: although CNAME is officially a singleton type, dnspython allows
    non-singleton CNAME rdatasets because such sets have been commonly
    used by BIND and other nameservers for load balancing."""
    pass

########NEW FILE########
__FILENAME__ = DLV
# Copyright (C) 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import dns.rdtypes.dsbase

class DLV(dns.rdtypes.dsbase.DSBase):
    """DLV record"""
    pass

########NEW FILE########
__FILENAME__ = DNAME
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import dns.rdtypes.nsbase

class DNAME(dns.rdtypes.nsbase.UncompressedNS):
    """DNAME record"""
    def to_digestable(self, origin = None):
        return self.target.to_digestable(origin)

########NEW FILE########
__FILENAME__ = DNSKEY
# Copyright (C) 2004-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.


import struct

import dns.exception
import dns.dnssec
import dns.rdata

# flag constants
SEP = 0x0001
REVOKE = 0x0080
ZONE = 0x0100

class DNSKEY(dns.rdata.Rdata):
    """DNSKEY record

    @ivar flags: the key flags
    @type flags: int
    @ivar protocol: the protocol for which this key may be used
    @type protocol: int
    @ivar algorithm: the algorithm used for the key
    @type algorithm: int
    @ivar key: the public key
    @type key: string"""

    __slots__ = ['flags', 'protocol', 'algorithm', 'key']

    def __init__(self, rdclass, rdtype, flags, protocol, algorithm, key):
        super(DNSKEY, self).__init__(rdclass, rdtype)
        self.flags = flags
        self.protocol = protocol
        self.algorithm = algorithm
        self.key = key

    def to_text(self, origin=None, relativize=True, **kw):
        return '%d %d %d %s' % (self.flags, self.protocol, self.algorithm,
                                dns.rdata._base64ify(self.key))

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        flags = tok.get_uint16()
        protocol = tok.get_uint8()
        algorithm = dns.dnssec.algorithm_from_text(tok.get_string())
        chunks = []
        while 1:
            t = tok.get().unescape()
            if t.is_eol_or_eof():
                break
            if not t.is_identifier():
                raise dns.exception.SyntaxError
            chunks.append(t.value)
        b64 = ''.join(chunks)
        key = b64.decode('base64_codec')
        return cls(rdclass, rdtype, flags, protocol, algorithm, key)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        header = struct.pack("!HBB", self.flags, self.protocol, self.algorithm)
        file.write(header)
        file.write(self.key)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        if rdlen < 4:
            raise dns.exception.FormError
        header = struct.unpack('!HBB', wire[current : current + 4])
        current += 4
        rdlen -= 4
        key = wire[current : current + rdlen].unwrap()
        return cls(rdclass, rdtype, header[0], header[1], header[2],
                   key)

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        hs = struct.pack("!HBB", self.flags, self.protocol, self.algorithm)
        ho = struct.pack("!HBB", other.flags, other.protocol, other.algorithm)
        v = cmp(hs, ho)
        if v == 0:
            v = cmp(self.key, other.key)
        return v

########NEW FILE########
__FILENAME__ = DS
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import dns.rdtypes.dsbase

class DS(dns.rdtypes.dsbase.DSBase):
    """DS record"""
    pass

########NEW FILE########
__FILENAME__ = GPOS
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import dns.exception
import dns.rdata
import dns.tokenizer

def _validate_float_string(what):
    if what[0] == '-' or what[0] == '+':
        what = what[1:]
    if what.isdigit():
        return
    (left, right) = what.split('.')
    if left == '' and right == '':
        raise dns.exception.FormError
    if not left == '' and not left.isdigit():
        raise dns.exception.FormError
    if not right == '' and not right.isdigit():
        raise dns.exception.FormError

class GPOS(dns.rdata.Rdata):
    """GPOS record

    @ivar latitude: latitude
    @type latitude: string
    @ivar longitude: longitude
    @type longitude: string
    @ivar altitude: altitude
    @type altitude: string
    @see: RFC 1712"""

    __slots__ = ['latitude', 'longitude', 'altitude']

    def __init__(self, rdclass, rdtype, latitude, longitude, altitude):
        super(GPOS, self).__init__(rdclass, rdtype)
        if isinstance(latitude, float) or \
           isinstance(latitude, int) or \
           isinstance(latitude, long):
            latitude = str(latitude)
        if isinstance(longitude, float) or \
           isinstance(longitude, int) or \
           isinstance(longitude, long):
            longitude = str(longitude)
        if isinstance(altitude, float) or \
           isinstance(altitude, int) or \
           isinstance(altitude, long):
            altitude = str(altitude)
        _validate_float_string(latitude)
        _validate_float_string(longitude)
        _validate_float_string(altitude)
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude

    def to_text(self, origin=None, relativize=True, **kw):
        return '%s %s %s' % (self.latitude, self.longitude, self.altitude)

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        latitude = tok.get_string()
        longitude = tok.get_string()
        altitude = tok.get_string()
        tok.get_eol()
        return cls(rdclass, rdtype, latitude, longitude, altitude)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        l = len(self.latitude)
        assert l < 256
        byte = chr(l)
        file.write(byte)
        file.write(self.latitude)
        l = len(self.longitude)
        assert l < 256
        byte = chr(l)
        file.write(byte)
        file.write(self.longitude)
        l = len(self.altitude)
        assert l < 256
        byte = chr(l)
        file.write(byte)
        file.write(self.altitude)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        l = ord(wire[current])
        current += 1
        rdlen -= 1
        if l > rdlen:
            raise dns.exception.FormError
        latitude = wire[current : current + l].unwrap()
        current += l
        rdlen -= l
        l = ord(wire[current])
        current += 1
        rdlen -= 1
        if l > rdlen:
            raise dns.exception.FormError
        longitude = wire[current : current + l].unwrap()
        current += l
        rdlen -= l
        l = ord(wire[current])
        current += 1
        rdlen -= 1
        if l != rdlen:
            raise dns.exception.FormError
        altitude = wire[current : current + l].unwrap()
        return cls(rdclass, rdtype, latitude, longitude, altitude)

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        v = cmp(self.latitude, other.latitude)
        if v == 0:
            v = cmp(self.longitude, other.longitude)
            if v == 0:
                v = cmp(self.altitude, other.altitude)
        return v

    def _get_float_latitude(self):
        return float(self.latitude)

    def _set_float_latitude(self, value):
        self.latitude = str(value)

    float_latitude = property(_get_float_latitude, _set_float_latitude,
                              doc="latitude as a floating point value")

    def _get_float_longitude(self):
        return float(self.longitude)

    def _set_float_longitude(self, value):
        self.longitude = str(value)

    float_longitude = property(_get_float_longitude, _set_float_longitude,
                               doc="longitude as a floating point value")

    def _get_float_altitude(self):
        return float(self.altitude)

    def _set_float_altitude(self, value):
        self.altitude = str(value)

    float_altitude = property(_get_float_altitude, _set_float_altitude,
                              doc="altitude as a floating point value")

########NEW FILE########
__FILENAME__ = HINFO
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import dns.exception
import dns.rdata
import dns.tokenizer

class HINFO(dns.rdata.Rdata):
    """HINFO record

    @ivar cpu: the CPU type
    @type cpu: string
    @ivar os: the OS type
    @type os: string
    @see: RFC 1035"""

    __slots__ = ['cpu', 'os']

    def __init__(self, rdclass, rdtype, cpu, os):
        super(HINFO, self).__init__(rdclass, rdtype)
        self.cpu = cpu
        self.os = os

    def to_text(self, origin=None, relativize=True, **kw):
        return '"%s" "%s"' % (dns.rdata._escapify(self.cpu),
                              dns.rdata._escapify(self.os))

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        cpu = tok.get_string()
        os = tok.get_string()
        tok.get_eol()
        return cls(rdclass, rdtype, cpu, os)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        l = len(self.cpu)
        assert l < 256
        byte = chr(l)
        file.write(byte)
        file.write(self.cpu)
        l = len(self.os)
        assert l < 256
        byte = chr(l)
        file.write(byte)
        file.write(self.os)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        l = ord(wire[current])
        current += 1
        rdlen -= 1
        if l > rdlen:
            raise dns.exception.FormError
        cpu = wire[current : current + l].unwrap()
        current += l
        rdlen -= l
        l = ord(wire[current])
        current += 1
        rdlen -= 1
        if l != rdlen:
            raise dns.exception.FormError
        os = wire[current : current + l].unwrap()
        return cls(rdclass, rdtype, cpu, os)

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        v = cmp(self.cpu, other.cpu)
        if v == 0:
            v = cmp(self.os, other.os)
        return v

########NEW FILE########
__FILENAME__ = HIP
# Copyright (C) 2010, 2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import cStringIO
import string
import struct

import dns.exception
import dns.rdata
import dns.rdatatype

class HIP(dns.rdata.Rdata):
    """HIP record

    @ivar hit: the host identity tag
    @type hit: string
    @ivar algorithm: the public key cryptographic algorithm
    @type algorithm: int
    @ivar key: the public key
    @type key: string
    @ivar servers: the rendezvous servers
    @type servers: list of dns.name.Name objects
    @see: RFC 5205"""

    __slots__ = ['hit', 'algorithm', 'key', 'servers']

    def __init__(self, rdclass, rdtype, hit, algorithm, key, servers):
        super(HIP, self).__init__(rdclass, rdtype)
        self.hit = hit
        self.algorithm = algorithm
        self.key = key
        self.servers = servers

    def to_text(self, origin=None, relativize=True, **kw):
        hit = self.hit.encode('hex-codec')
        key = self.key.encode('base64-codec').replace('\n', '')
        text = ''
        servers = []
        for server in self.servers:
            servers.append(str(server.choose_relativity(origin, relativize)))
        if len(servers) > 0:
            text += (' ' + ' '.join(servers))
        return '%u %s %s%s' % (self.algorithm, hit, key, text)

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        algorithm = tok.get_uint8()
        hit = tok.get_string().decode('hex-codec')
        if len(hit) > 255:
            raise dns.exception.SyntaxError("HIT too long")
        key = tok.get_string().decode('base64-codec')
        servers = []
        while 1:
            token = tok.get()
            if token.is_eol_or_eof():
                break
            server = dns.name.from_text(token.value, origin)
            server.choose_relativity(origin, relativize)
            servers.append(server)
        return cls(rdclass, rdtype, hit, algorithm, key, servers)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        lh = len(self.hit)
        lk = len(self.key)
        file.write(struct.pack("!BBH", lh, self.algorithm, lk))
        file.write(self.hit)
        file.write(self.key)
        for server in self.servers:
            server.to_wire(file, None, origin)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        (lh, algorithm, lk) = struct.unpack('!BBH',
                                            wire[current : current + 4])
        current += 4
        rdlen -= 4
        hit = wire[current : current + lh].unwrap()
        current += lh
        rdlen -= lh
        key = wire[current : current + lk].unwrap()
        current += lk
        rdlen -= lk
        servers = []
        while rdlen > 0:
            (server, cused) = dns.name.from_wire(wire[: current + rdlen],
                                                 current)
            current += cused
            rdlen -= cused
            if not origin is None:
                server = server.relativize(origin)
            servers.append(server)
        return cls(rdclass, rdtype, hit, algorithm, key, servers)

    from_wire = classmethod(from_wire)

    def choose_relativity(self, origin = None, relativize = True):
        servers = []
        for server in self.servers:
            server = server.choose_relativity(origin, relativize)
            servers.append(server)
        self.servers = servers

    def _cmp(self, other):
        b1 = cStringIO.StringIO()
        lh = len(self.hit)
        lk = len(self.key)
        b1.write(struct.pack("!BBH", lh, self.algorithm, lk))
        b1.write(self.hit)
        b1.write(self.key)
        b2 = cStringIO.StringIO()
        lh = len(other.hit)
        lk = len(other.key)
        b2.write(struct.pack("!BBH", lh, other.algorithm, lk))
        b2.write(other.hit)
        b2.write(other.key)
        v = cmp(b1.getvalue(), b2.getvalue())
        if v != 0:
            return v
        ls = len(self.servers)
        lo = len(other.servers)
        count = min(ls, lo)
        i = 0
        while i < count:
            v = cmp(self.servers[i], other.servers[i])
            if v != 0:
                return v
            i += 1
        return ls - lo

########NEW FILE########
__FILENAME__ = ISDN
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import dns.exception
import dns.rdata
import dns.tokenizer

class ISDN(dns.rdata.Rdata):
    """ISDN record

    @ivar address: the ISDN address
    @type address: string
    @ivar subaddress: the ISDN subaddress (or '' if not present)
    @type subaddress: string
    @see: RFC 1183"""

    __slots__ = ['address', 'subaddress']

    def __init__(self, rdclass, rdtype, address, subaddress):
        super(ISDN, self).__init__(rdclass, rdtype)
        self.address = address
        self.subaddress = subaddress

    def to_text(self, origin=None, relativize=True, **kw):
        if self.subaddress:
            return '"%s" "%s"' % (dns.rdata._escapify(self.address),
                                  dns.rdata._escapify(self.subaddress))
        else:
            return '"%s"' % dns.rdata._escapify(self.address)

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        address = tok.get_string()
        t = tok.get()
        if not t.is_eol_or_eof():
            tok.unget(t)
            subaddress = tok.get_string()
        else:
            tok.unget(t)
            subaddress = ''
        tok.get_eol()
        return cls(rdclass, rdtype, address, subaddress)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        l = len(self.address)
        assert l < 256
        byte = chr(l)
        file.write(byte)
        file.write(self.address)
        l = len(self.subaddress)
        if l > 0:
            assert l < 256
            byte = chr(l)
            file.write(byte)
            file.write(self.subaddress)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        l = ord(wire[current])
        current += 1
        rdlen -= 1
        if l > rdlen:
            raise dns.exception.FormError
        address = wire[current : current + l].unwrap()
        current += l
        rdlen -= l
        if rdlen > 0:
            l = ord(wire[current])
            current += 1
            rdlen -= 1
            if l != rdlen:
                raise dns.exception.FormError
            subaddress = wire[current : current + l].unwrap()
        else:
            subaddress = ''
        return cls(rdclass, rdtype, address, subaddress)

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        v = cmp(self.address, other.address)
        if v == 0:
            v = cmp(self.subaddress, other.subaddress)
        return v

########NEW FILE########
__FILENAME__ = LOC
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import cStringIO
import struct

import dns.exception
import dns.rdata

_pows = (1L, 10L, 100L, 1000L, 10000L, 100000L, 1000000L, 10000000L,
         100000000L, 1000000000L, 10000000000L)

# default values are in centimeters
_default_size = 100.0
_default_hprec = 1000000.0
_default_vprec = 1000.0

def _exponent_of(what, desc):
    if what == 0:
        return 0
    exp = None
    for i in xrange(len(_pows)):
        if what // _pows[i] == 0L:
            exp = i - 1
            break
    if exp is None or exp < 0:
        raise dns.exception.SyntaxError("%s value out of bounds" % desc)
    return exp

def _float_to_tuple(what):
    if what < 0:
        sign = -1
        what *= -1
    else:
        sign = 1
    what = long(round(what * 3600000))
    degrees = int(what // 3600000)
    what -= degrees * 3600000
    minutes = int(what // 60000)
    what -= minutes * 60000
    seconds = int(what // 1000)
    what -= int(seconds * 1000)
    what = int(what)
    return (degrees * sign, minutes, seconds, what)

def _tuple_to_float(what):
    if what[0] < 0:
        sign = -1
        value = float(what[0]) * -1
    else:
        sign = 1
        value = float(what[0])
    value += float(what[1]) / 60.0
    value += float(what[2]) / 3600.0
    value += float(what[3]) / 3600000.0
    return sign * value

def _encode_size(what, desc):
    what = long(what);
    exponent = _exponent_of(what, desc) & 0xF
    base = what // pow(10, exponent) & 0xF
    return base * 16 + exponent

def _decode_size(what, desc):
    exponent = what & 0x0F
    if exponent > 9:
        raise dns.exception.SyntaxError("bad %s exponent" % desc)
    base = (what & 0xF0) >> 4
    if base > 9:
        raise dns.exception.SyntaxError("bad %s base" % desc)
    return long(base) * pow(10, exponent)

class LOC(dns.rdata.Rdata):
    """LOC record

    @ivar latitude: latitude
    @type latitude: (int, int, int, int) tuple specifying the degrees, minutes,
    seconds, and milliseconds of the coordinate.
    @ivar longitude: longitude
    @type longitude: (int, int, int, int) tuple specifying the degrees,
    minutes, seconds, and milliseconds of the coordinate.
    @ivar altitude: altitude
    @type altitude: float
    @ivar size: size of the sphere
    @type size: float
    @ivar horizontal_precision: horizontal precision
    @type horizontal_precision: float
    @ivar vertical_precision: vertical precision
    @type vertical_precision: float
    @see: RFC 1876"""

    __slots__ = ['latitude', 'longitude', 'altitude', 'size',
                 'horizontal_precision', 'vertical_precision']

    def __init__(self, rdclass, rdtype, latitude, longitude, altitude,
                 size=_default_size, hprec=_default_hprec, vprec=_default_vprec):
        """Initialize a LOC record instance.

        The parameters I{latitude} and I{longitude} may be either a 4-tuple
        of integers specifying (degrees, minutes, seconds, milliseconds),
        or they may be floating point values specifying the number of
        degrees. The other parameters are floats. Size, horizontal precision,
        and vertical precision are specified in centimeters."""

        super(LOC, self).__init__(rdclass, rdtype)
        if isinstance(latitude, int) or isinstance(latitude, long):
            latitude = float(latitude)
        if isinstance(latitude, float):
            latitude = _float_to_tuple(latitude)
        self.latitude = latitude
        if isinstance(longitude, int) or isinstance(longitude, long):
            longitude = float(longitude)
        if isinstance(longitude, float):
            longitude = _float_to_tuple(longitude)
        self.longitude = longitude
        self.altitude = float(altitude)
        self.size = float(size)
        self.horizontal_precision = float(hprec)
        self.vertical_precision = float(vprec)

    def to_text(self, origin=None, relativize=True, **kw):
        if self.latitude[0] > 0:
            lat_hemisphere = 'N'
            lat_degrees = self.latitude[0]
        else:
            lat_hemisphere = 'S'
            lat_degrees = -1 * self.latitude[0]
        if self.longitude[0] > 0:
            long_hemisphere = 'E'
            long_degrees = self.longitude[0]
        else:
            long_hemisphere = 'W'
            long_degrees = -1 * self.longitude[0]
        text = "%d %d %d.%03d %s %d %d %d.%03d %s %0.2fm" % (
            lat_degrees, self.latitude[1], self.latitude[2], self.latitude[3],
            lat_hemisphere, long_degrees, self.longitude[1], self.longitude[2],
            self.longitude[3], long_hemisphere, self.altitude / 100.0
            )

        # do not print default values
        if self.size != _default_size or \
            self.horizontal_precision != _default_hprec or \
            self.vertical_precision != _default_vprec:
            text += " %0.2fm %0.2fm %0.2fm" % (
                self.size / 100.0, self.horizontal_precision / 100.0,
                self.vertical_precision / 100.0
            )
        return text

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        latitude = [0, 0, 0, 0]
        longitude = [0, 0, 0, 0]
        size = _default_size
        hprec = _default_hprec
        vprec = _default_vprec

        latitude[0] = tok.get_int()
        t = tok.get_string()
        if t.isdigit():
            latitude[1] = int(t)
            t = tok.get_string()
            if '.' in t:
                (seconds, milliseconds) = t.split('.')
                if not seconds.isdigit():
                    raise dns.exception.SyntaxError('bad latitude seconds value')
                latitude[2] = int(seconds)
                if latitude[2] >= 60:
                    raise dns.exception.SyntaxError('latitude seconds >= 60')
                l = len(milliseconds)
                if l == 0 or l > 3 or not milliseconds.isdigit():
                    raise dns.exception.SyntaxError('bad latitude milliseconds value')
                if l == 1:
                    m = 100
                elif l == 2:
                    m = 10
                else:
                    m = 1
                latitude[3] = m * int(milliseconds)
                t = tok.get_string()
            elif t.isdigit():
                latitude[2] = int(t)
                t = tok.get_string()
        if t == 'S':
            latitude[0] *= -1
        elif t != 'N':
            raise dns.exception.SyntaxError('bad latitude hemisphere value')

        longitude[0] = tok.get_int()
        t = tok.get_string()
        if t.isdigit():
            longitude[1] = int(t)
            t = tok.get_string()
            if '.' in t:
                (seconds, milliseconds) = t.split('.')
                if not seconds.isdigit():
                    raise dns.exception.SyntaxError('bad longitude seconds value')
                longitude[2] = int(seconds)
                if longitude[2] >= 60:
                    raise dns.exception.SyntaxError('longitude seconds >= 60')
                l = len(milliseconds)
                if l == 0 or l > 3 or not milliseconds.isdigit():
                    raise dns.exception.SyntaxError('bad longitude milliseconds value')
                if l == 1:
                    m = 100
                elif l == 2:
                    m = 10
                else:
                    m = 1
                longitude[3] = m * int(milliseconds)
                t = tok.get_string()
            elif t.isdigit():
                longitude[2] = int(t)
                t = tok.get_string()
        if t == 'W':
            longitude[0] *= -1
        elif t != 'E':
            raise dns.exception.SyntaxError('bad longitude hemisphere value')

        t = tok.get_string()
        if t[-1] == 'm':
            t = t[0 : -1]
        altitude = float(t) * 100.0	# m -> cm

        token = tok.get().unescape()
        if not token.is_eol_or_eof():
            value = token.value
            if value[-1] == 'm':
                value = value[0 : -1]
            size = float(value) * 100.0	# m -> cm
            token = tok.get().unescape()
            if not token.is_eol_or_eof():
                value = token.value
                if value[-1] == 'm':
                    value = value[0 : -1]
                hprec = float(value) * 100.0	# m -> cm
                token = tok.get().unescape()
                if not token.is_eol_or_eof():
                    value = token.value
                    if value[-1] == 'm':
                        value = value[0 : -1]
                    vprec = float(value) * 100.0	# m -> cm
                    tok.get_eol()

        return cls(rdclass, rdtype, latitude, longitude, altitude,
                   size, hprec, vprec)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        if self.latitude[0] < 0:
            sign = -1
            degrees = long(-1 * self.latitude[0])
        else:
            sign = 1
            degrees = long(self.latitude[0])
        milliseconds = (degrees * 3600000 +
                        self.latitude[1] * 60000 +
                        self.latitude[2] * 1000 +
                        self.latitude[3]) * sign
        latitude = 0x80000000L + milliseconds
        if self.longitude[0] < 0:
            sign = -1
            degrees = long(-1 * self.longitude[0])
        else:
            sign = 1
            degrees = long(self.longitude[0])
        milliseconds = (degrees * 3600000 +
                        self.longitude[1] * 60000 +
                        self.longitude[2] * 1000 +
                        self.longitude[3]) * sign
        longitude = 0x80000000L + milliseconds
        altitude = long(self.altitude) + 10000000L
        size = _encode_size(self.size, "size")
        hprec = _encode_size(self.horizontal_precision, "horizontal precision")
        vprec = _encode_size(self.vertical_precision, "vertical precision")
        wire = struct.pack("!BBBBIII", 0, size, hprec, vprec, latitude,
                           longitude, altitude)
        file.write(wire)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        (version, size, hprec, vprec, latitude, longitude, altitude) = \
                  struct.unpack("!BBBBIII", wire[current : current + rdlen])
        if latitude > 0x80000000L:
            latitude = float(latitude - 0x80000000L) / 3600000
        else:
            latitude = -1 * float(0x80000000L - latitude) / 3600000
        if latitude < -90.0 or latitude > 90.0:
            raise dns.exception.FormError("bad latitude")
        if longitude > 0x80000000L:
            longitude = float(longitude - 0x80000000L) / 3600000
        else:
            longitude = -1 * float(0x80000000L - longitude) / 3600000
        if longitude < -180.0 or longitude > 180.0:
            raise dns.exception.FormError("bad longitude")
        altitude = float(altitude) - 10000000.0
        size = _decode_size(size, "size")
        hprec = _decode_size(hprec, "horizontal precision")
        vprec = _decode_size(vprec, "vertical precision")
        return cls(rdclass, rdtype, latitude, longitude, altitude,
                   size, hprec, vprec)

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        f = cStringIO.StringIO()
        self.to_wire(f)
        wire1 = f.getvalue()
        f.seek(0)
        f.truncate()
        other.to_wire(f)
        wire2 = f.getvalue()
        f.close()

        return cmp(wire1, wire2)

    def _get_float_latitude(self):
        return _tuple_to_float(self.latitude)

    def _set_float_latitude(self, value):
        self.latitude = _float_to_tuple(value)

    float_latitude = property(_get_float_latitude, _set_float_latitude,
                              doc="latitude as a floating point value")

    def _get_float_longitude(self):
        return _tuple_to_float(self.longitude)

    def _set_float_longitude(self, value):
        self.longitude = _float_to_tuple(value)

    float_longitude = property(_get_float_longitude, _set_float_longitude,
                               doc="longitude as a floating point value")

########NEW FILE########
__FILENAME__ = MX
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import dns.rdtypes.mxbase

class MX(dns.rdtypes.mxbase.MXBase):
    """MX record"""
    pass

########NEW FILE########
__FILENAME__ = NS
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import dns.rdtypes.nsbase

class NS(dns.rdtypes.nsbase.NSBase):
    """NS record"""
    pass

########NEW FILE########
__FILENAME__ = NSEC
# Copyright (C) 2004-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import cStringIO

import dns.exception
import dns.rdata
import dns.rdatatype
import dns.name

class NSEC(dns.rdata.Rdata):
    """NSEC record

    @ivar next: the next name
    @type next: dns.name.Name object
    @ivar windows: the windowed bitmap list
    @type windows: list of (window number, string) tuples"""

    __slots__ = ['next', 'windows']

    def __init__(self, rdclass, rdtype, next, windows):
        super(NSEC, self).__init__(rdclass, rdtype)
        self.next = next
        self.windows = windows

    def to_text(self, origin=None, relativize=True, **kw):
        next = self.next.choose_relativity(origin, relativize)
        text = ''
        for (window, bitmap) in self.windows:
            bits = []
            for i in xrange(0, len(bitmap)):
                byte = ord(bitmap[i])
                for j in xrange(0, 8):
                    if byte & (0x80 >> j):
                        bits.append(dns.rdatatype.to_text(window * 256 + \
                                                          i * 8 + j))
            text += (' ' + ' '.join(bits))
        return '%s%s' % (next, text)

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        next = tok.get_name()
        next = next.choose_relativity(origin, relativize)
        rdtypes = []
        while 1:
            token = tok.get().unescape()
            if token.is_eol_or_eof():
                break
            nrdtype = dns.rdatatype.from_text(token.value)
            if nrdtype == 0:
                raise dns.exception.SyntaxError("NSEC with bit 0")
            if nrdtype > 65535:
                raise dns.exception.SyntaxError("NSEC with bit > 65535")
            rdtypes.append(nrdtype)
        rdtypes.sort()
        window = 0
        octets = 0
        prior_rdtype = 0
        bitmap = ['\0'] * 32
        windows = []
        for nrdtype in rdtypes:
            if nrdtype == prior_rdtype:
                continue
            prior_rdtype = nrdtype
            new_window = nrdtype // 256
            if new_window != window:
                windows.append((window, ''.join(bitmap[0:octets])))
                bitmap = ['\0'] * 32
                window = new_window
            offset = nrdtype % 256
            byte = offset // 8
            bit = offset % 8
            octets = byte + 1
            bitmap[byte] = chr(ord(bitmap[byte]) | (0x80 >> bit))
        windows.append((window, ''.join(bitmap[0:octets])))
        return cls(rdclass, rdtype, next, windows)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        self.next.to_wire(file, None, origin)
        for (window, bitmap) in self.windows:
            file.write(chr(window))
            file.write(chr(len(bitmap)))
            file.write(bitmap)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        (next, cused) = dns.name.from_wire(wire[: current + rdlen], current)
        current += cused
        rdlen -= cused
        windows = []
        while rdlen > 0:
            if rdlen < 3:
                raise dns.exception.FormError("NSEC too short")
            window = ord(wire[current])
            octets = ord(wire[current + 1])
            if octets == 0 or octets > 32:
                raise dns.exception.FormError("bad NSEC octets")
            current += 2
            rdlen -= 2
            if rdlen < octets:
                raise dns.exception.FormError("bad NSEC bitmap length")
            bitmap = wire[current : current + octets].unwrap()
            current += octets
            rdlen -= octets
            windows.append((window, bitmap))
        if not origin is None:
            next = next.relativize(origin)
        return cls(rdclass, rdtype, next, windows)

    from_wire = classmethod(from_wire)

    def choose_relativity(self, origin = None, relativize = True):
        self.next = self.next.choose_relativity(origin, relativize)

    def _cmp(self, other):
        return self._wire_cmp(other)

########NEW FILE########
__FILENAME__ = NSEC3
# Copyright (C) 2004-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import base64
import cStringIO
import string
import struct

import dns.exception
import dns.rdata
import dns.rdatatype

b32_hex_to_normal = string.maketrans('0123456789ABCDEFGHIJKLMNOPQRSTUV',
                                     'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567')
b32_normal_to_hex = string.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ234567',
                                     '0123456789ABCDEFGHIJKLMNOPQRSTUV')

# hash algorithm constants
SHA1 = 1

# flag constants
OPTOUT = 1

class NSEC3(dns.rdata.Rdata):
    """NSEC3 record

    @ivar algorithm: the hash algorithm number
    @type algorithm: int
    @ivar flags: the flags
    @type flags: int
    @ivar iterations: the number of iterations
    @type iterations: int
    @ivar salt: the salt
    @type salt: string
    @ivar next: the next name hash
    @type next: string
    @ivar windows: the windowed bitmap list
    @type windows: list of (window number, string) tuples"""

    __slots__ = ['algorithm', 'flags', 'iterations', 'salt', 'next', 'windows']

    def __init__(self, rdclass, rdtype, algorithm, flags, iterations, salt,
                 next, windows):
        super(NSEC3, self).__init__(rdclass, rdtype)
        self.algorithm = algorithm
        self.flags = flags
        self.iterations = iterations
        self.salt = salt
        self.next = next
        self.windows = windows

    def to_text(self, origin=None, relativize=True, **kw):
        next = base64.b32encode(self.next).translate(b32_normal_to_hex).lower()
        if self.salt == '':
            salt = '-'
        else:
            salt = self.salt.encode('hex-codec')
        text = ''
        for (window, bitmap) in self.windows:
            bits = []
            for i in xrange(0, len(bitmap)):
                byte = ord(bitmap[i])
                for j in xrange(0, 8):
                    if byte & (0x80 >> j):
                        bits.append(dns.rdatatype.to_text(window * 256 + \
                                                          i * 8 + j))
            text += (' ' + ' '.join(bits))
        return '%u %u %u %s %s%s' % (self.algorithm, self.flags, self.iterations,
                                     salt, next, text)

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        algorithm = tok.get_uint8()
        flags = tok.get_uint8()
        iterations = tok.get_uint16()
        salt = tok.get_string()
        if salt == '-':
            salt = ''
        else:
            salt = salt.decode('hex-codec')
        next = tok.get_string().upper().translate(b32_hex_to_normal)
        next = base64.b32decode(next)
        rdtypes = []
        while 1:
            token = tok.get().unescape()
            if token.is_eol_or_eof():
                break
            nrdtype = dns.rdatatype.from_text(token.value)
            if nrdtype == 0:
                raise dns.exception.SyntaxError("NSEC3 with bit 0")
            if nrdtype > 65535:
                raise dns.exception.SyntaxError("NSEC3 with bit > 65535")
            rdtypes.append(nrdtype)
        rdtypes.sort()
        window = 0
        octets = 0
        prior_rdtype = 0
        bitmap = ['\0'] * 32
        windows = []
        for nrdtype in rdtypes:
            if nrdtype == prior_rdtype:
                continue
            prior_rdtype = nrdtype
            new_window = nrdtype // 256
            if new_window != window:
                if octets != 0:
                    windows.append((window, ''.join(bitmap[0:octets])))
                bitmap = ['\0'] * 32
                window = new_window
            offset = nrdtype % 256
            byte = offset // 8
            bit = offset % 8
            octets = byte + 1
            bitmap[byte] = chr(ord(bitmap[byte]) | (0x80 >> bit))
        if octets != 0:
            windows.append((window, ''.join(bitmap[0:octets])))
        return cls(rdclass, rdtype, algorithm, flags, iterations, salt, next, windows)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        l = len(self.salt)
        file.write(struct.pack("!BBHB", self.algorithm, self.flags,
                               self.iterations, l))
        file.write(self.salt)
        l = len(self.next)
        file.write(struct.pack("!B", l))
        file.write(self.next)
        for (window, bitmap) in self.windows:
            file.write(chr(window))
            file.write(chr(len(bitmap)))
            file.write(bitmap)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        (algorithm, flags, iterations, slen) = struct.unpack('!BBHB',
                                                             wire[current : current + 5])
        current += 5
        rdlen -= 5
        salt = wire[current : current + slen].unwrap()
        current += slen
        rdlen -= slen
        (nlen, ) = struct.unpack('!B', wire[current])
        current += 1
        rdlen -= 1
        next = wire[current : current + nlen].unwrap()
        current += nlen
        rdlen -= nlen
        windows = []
        while rdlen > 0:
            if rdlen < 3:
                raise dns.exception.FormError("NSEC3 too short")
            window = ord(wire[current])
            octets = ord(wire[current + 1])
            if octets == 0 or octets > 32:
                raise dns.exception.FormError("bad NSEC3 octets")
            current += 2
            rdlen -= 2
            if rdlen < octets:
                raise dns.exception.FormError("bad NSEC3 bitmap length")
            bitmap = wire[current : current + octets].unwrap()
            current += octets
            rdlen -= octets
            windows.append((window, bitmap))
        return cls(rdclass, rdtype, algorithm, flags, iterations, salt, next, windows)

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        b1 = cStringIO.StringIO()
        self.to_wire(b1)
        b2 = cStringIO.StringIO()
        other.to_wire(b2)
        return cmp(b1.getvalue(), b2.getvalue())

########NEW FILE########
__FILENAME__ = NSEC3PARAM
# Copyright (C) 2004-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import cStringIO
import struct

import dns.exception
import dns.rdata

class NSEC3PARAM(dns.rdata.Rdata):
    """NSEC3PARAM record

    @ivar algorithm: the hash algorithm number
    @type algorithm: int
    @ivar flags: the flags
    @type flags: int
    @ivar iterations: the number of iterations
    @type iterations: int
    @ivar salt: the salt
    @type salt: string"""

    __slots__ = ['algorithm', 'flags', 'iterations', 'salt']

    def __init__(self, rdclass, rdtype, algorithm, flags, iterations, salt):
        super(NSEC3PARAM, self).__init__(rdclass, rdtype)
        self.algorithm = algorithm
        self.flags = flags
        self.iterations = iterations
        self.salt = salt

    def to_text(self, origin=None, relativize=True, **kw):
        if self.salt == '':
            salt = '-'
        else:
            salt = self.salt.encode('hex-codec')
        return '%u %u %u %s' % (self.algorithm, self.flags, self.iterations, salt)

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        algorithm = tok.get_uint8()
        flags = tok.get_uint8()
        iterations = tok.get_uint16()
        salt = tok.get_string()
        if salt == '-':
            salt = ''
        else:
            salt = salt.decode('hex-codec')
        return cls(rdclass, rdtype, algorithm, flags, iterations, salt)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        l = len(self.salt)
        file.write(struct.pack("!BBHB", self.algorithm, self.flags,
                               self.iterations, l))
        file.write(self.salt)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        (algorithm, flags, iterations, slen) = struct.unpack('!BBHB',
                                                             wire[current : current + 5])
        current += 5
        rdlen -= 5
        salt = wire[current : current + slen].unwrap()
        current += slen
        rdlen -= slen
        if rdlen != 0:
            raise dns.exception.FormError
        return cls(rdclass, rdtype, algorithm, flags, iterations, salt)

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        b1 = cStringIO.StringIO()
        self.to_wire(b1)
        b2 = cStringIO.StringIO()
        other.to_wire(b2)
        return cmp(b1.getvalue(), b2.getvalue())

########NEW FILE########
__FILENAME__ = PTR
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import dns.rdtypes.nsbase

class PTR(dns.rdtypes.nsbase.NSBase):
    """PTR record"""
    pass

########NEW FILE########
__FILENAME__ = RP
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import dns.exception
import dns.rdata
import dns.name

class RP(dns.rdata.Rdata):
    """RP record

    @ivar mbox: The responsible person's mailbox
    @type mbox: dns.name.Name object
    @ivar txt: The owner name of a node with TXT records, or the root name
    if no TXT records are associated with this RP.
    @type txt: dns.name.Name object
    @see: RFC 1183"""

    __slots__ = ['mbox', 'txt']

    def __init__(self, rdclass, rdtype, mbox, txt):
        super(RP, self).__init__(rdclass, rdtype)
        self.mbox = mbox
        self.txt = txt

    def to_text(self, origin=None, relativize=True, **kw):
        mbox = self.mbox.choose_relativity(origin, relativize)
        txt = self.txt.choose_relativity(origin, relativize)
        return "%s %s" % (str(mbox), str(txt))

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        mbox = tok.get_name()
        txt = tok.get_name()
        mbox = mbox.choose_relativity(origin, relativize)
        txt = txt.choose_relativity(origin, relativize)
        tok.get_eol()
        return cls(rdclass, rdtype, mbox, txt)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        self.mbox.to_wire(file, None, origin)
        self.txt.to_wire(file, None, origin)

    def to_digestable(self, origin = None):
        return self.mbox.to_digestable(origin) + \
            self.txt.to_digestable(origin)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        (mbox, cused) = dns.name.from_wire(wire[: current + rdlen],
                                           current)
        current += cused
        rdlen -= cused
        if rdlen <= 0:
            raise dns.exception.FormError
        (txt, cused) = dns.name.from_wire(wire[: current + rdlen],
                                          current)
        if cused != rdlen:
            raise dns.exception.FormError
        if not origin is None:
            mbox = mbox.relativize(origin)
            txt = txt.relativize(origin)
        return cls(rdclass, rdtype, mbox, txt)

    from_wire = classmethod(from_wire)

    def choose_relativity(self, origin = None, relativize = True):
        self.mbox = self.mbox.choose_relativity(origin, relativize)
        self.txt = self.txt.choose_relativity(origin, relativize)

    def _cmp(self, other):
        v = cmp(self.mbox, other.mbox)
        if v == 0:
            v = cmp(self.txt, other.txt)
        return v

########NEW FILE########
__FILENAME__ = RRSIG
# Copyright (C) 2004-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import calendar
import struct
import time

import dns.dnssec
import dns.exception
import dns.rdata
import dns.rdatatype

class BadSigTime(dns.exception.DNSException):
    """Raised when a SIG or RRSIG RR's time cannot be parsed."""
    pass

def sigtime_to_posixtime(what):
    if len(what) != 14:
        raise BadSigTime
    year = int(what[0:4])
    month = int(what[4:6])
    day = int(what[6:8])
    hour = int(what[8:10])
    minute = int(what[10:12])
    second = int(what[12:14])
    return calendar.timegm((year, month, day, hour, minute, second,
                            0, 0, 0))

def posixtime_to_sigtime(what):
    return time.strftime('%Y%m%d%H%M%S', time.gmtime(what))

class RRSIG(dns.rdata.Rdata):
    """RRSIG record

    @ivar type_covered: the rdata type this signature covers
    @type type_covered: int
    @ivar algorithm: the algorithm used for the sig
    @type algorithm: int
    @ivar labels: number of labels
    @type labels: int
    @ivar original_ttl: the original TTL
    @type original_ttl: long
    @ivar expiration: signature expiration time
    @type expiration: long
    @ivar inception: signature inception time
    @type inception: long
    @ivar key_tag: the key tag
    @type key_tag: int
    @ivar signer: the signer
    @type signer: dns.name.Name object
    @ivar signature: the signature
    @type signature: string"""

    __slots__ = ['type_covered', 'algorithm', 'labels', 'original_ttl',
                 'expiration', 'inception', 'key_tag', 'signer',
                 'signature']

    def __init__(self, rdclass, rdtype, type_covered, algorithm, labels,
                 original_ttl, expiration, inception, key_tag, signer,
                 signature):
        super(RRSIG, self).__init__(rdclass, rdtype)
        self.type_covered = type_covered
        self.algorithm = algorithm
        self.labels = labels
        self.original_ttl = original_ttl
        self.expiration = expiration
        self.inception = inception
        self.key_tag = key_tag
        self.signer = signer
        self.signature = signature

    def covers(self):
        return self.type_covered

    def to_text(self, origin=None, relativize=True, **kw):
        return '%s %d %d %d %s %s %d %s %s' % (
            dns.rdatatype.to_text(self.type_covered),
            self.algorithm,
            self.labels,
            self.original_ttl,
            posixtime_to_sigtime(self.expiration),
            posixtime_to_sigtime(self.inception),
            self.key_tag,
            self.signer,
            dns.rdata._base64ify(self.signature)
            )

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        type_covered = dns.rdatatype.from_text(tok.get_string())
        algorithm = dns.dnssec.algorithm_from_text(tok.get_string())
        labels = tok.get_int()
        original_ttl = tok.get_ttl()
        expiration = sigtime_to_posixtime(tok.get_string())
        inception = sigtime_to_posixtime(tok.get_string())
        key_tag = tok.get_int()
        signer = tok.get_name()
        signer = signer.choose_relativity(origin, relativize)
        chunks = []
        while 1:
            t = tok.get().unescape()
            if t.is_eol_or_eof():
                break
            if not t.is_identifier():
                raise dns.exception.SyntaxError
            chunks.append(t.value)
        b64 = ''.join(chunks)
        signature = b64.decode('base64_codec')
        return cls(rdclass, rdtype, type_covered, algorithm, labels,
                   original_ttl, expiration, inception, key_tag, signer,
                   signature)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        header = struct.pack('!HBBIIIH', self.type_covered,
                             self.algorithm, self.labels,
                             self.original_ttl, self.expiration,
                             self.inception, self.key_tag)
        file.write(header)
        self.signer.to_wire(file, None, origin)
        file.write(self.signature)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        header = struct.unpack('!HBBIIIH', wire[current : current + 18])
        current += 18
        rdlen -= 18
        (signer, cused) = dns.name.from_wire(wire[: current + rdlen], current)
        current += cused
        rdlen -= cused
        if not origin is None:
            signer = signer.relativize(origin)
        signature = wire[current : current + rdlen].unwrap()
        return cls(rdclass, rdtype, header[0], header[1], header[2],
                   header[3], header[4], header[5], header[6], signer,
                   signature)

    from_wire = classmethod(from_wire)

    def choose_relativity(self, origin = None, relativize = True):
        self.signer = self.signer.choose_relativity(origin, relativize)

    def _cmp(self, other):
        return self._wire_cmp(other)

########NEW FILE########
__FILENAME__ = RT
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import dns.rdtypes.mxbase

class RT(dns.rdtypes.mxbase.UncompressedDowncasingMX):
    """RT record"""
    pass

########NEW FILE########
__FILENAME__ = SOA
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import struct

import dns.exception
import dns.rdata
import dns.name

class SOA(dns.rdata.Rdata):
    """SOA record

    @ivar mname: the SOA MNAME (master name) field
    @type mname: dns.name.Name object
    @ivar rname: the SOA RNAME (responsible name) field
    @type rname: dns.name.Name object
    @ivar serial: The zone's serial number
    @type serial: int
    @ivar refresh: The zone's refresh value (in seconds)
    @type refresh: int
    @ivar retry: The zone's retry value (in seconds)
    @type retry: int
    @ivar expire: The zone's expiration value (in seconds)
    @type expire: int
    @ivar minimum: The zone's negative caching time (in seconds, called
    "minimum" for historical reasons)
    @type minimum: int
    @see: RFC 1035"""

    __slots__ = ['mname', 'rname', 'serial', 'refresh', 'retry', 'expire',
                 'minimum']

    def __init__(self, rdclass, rdtype, mname, rname, serial, refresh, retry,
                 expire, minimum):
        super(SOA, self).__init__(rdclass, rdtype)
        self.mname = mname
        self.rname = rname
        self.serial = serial
        self.refresh = refresh
        self.retry = retry
        self.expire = expire
        self.minimum = minimum

    def to_text(self, origin=None, relativize=True, **kw):
        mname = self.mname.choose_relativity(origin, relativize)
        rname = self.rname.choose_relativity(origin, relativize)
        return '%s %s %d %d %d %d %d' % (
            mname, rname, self.serial, self.refresh, self.retry,
            self.expire, self.minimum )

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        mname = tok.get_name()
        rname = tok.get_name()
        mname = mname.choose_relativity(origin, relativize)
        rname = rname.choose_relativity(origin, relativize)
        serial = tok.get_uint32()
        refresh = tok.get_ttl()
        retry = tok.get_ttl()
        expire = tok.get_ttl()
        minimum = tok.get_ttl()
        tok.get_eol()
        return cls(rdclass, rdtype, mname, rname, serial, refresh, retry,
                   expire, minimum )

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        self.mname.to_wire(file, compress, origin)
        self.rname.to_wire(file, compress, origin)
        five_ints = struct.pack('!IIIII', self.serial, self.refresh,
                                self.retry, self.expire, self.minimum)
        file.write(five_ints)

    def to_digestable(self, origin = None):
        return self.mname.to_digestable(origin) + \
            self.rname.to_digestable(origin) + \
            struct.pack('!IIIII', self.serial, self.refresh,
                        self.retry, self.expire, self.minimum)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        (mname, cused) = dns.name.from_wire(wire[: current + rdlen], current)
        current += cused
        rdlen -= cused
        (rname, cused) = dns.name.from_wire(wire[: current + rdlen], current)
        current += cused
        rdlen -= cused
        if rdlen != 20:
            raise dns.exception.FormError
        five_ints = struct.unpack('!IIIII',
                                  wire[current : current + rdlen])
        if not origin is None:
            mname = mname.relativize(origin)
            rname = rname.relativize(origin)
        return cls(rdclass, rdtype, mname, rname,
                   five_ints[0], five_ints[1], five_ints[2], five_ints[3],
                   five_ints[4])

    from_wire = classmethod(from_wire)

    def choose_relativity(self, origin = None, relativize = True):
        self.mname = self.mname.choose_relativity(origin, relativize)
        self.rname = self.rname.choose_relativity(origin, relativize)

    def _cmp(self, other):
        v = cmp(self.mname, other.mname)
        if v == 0:
            v = cmp(self.rname, other.rname)
            if v == 0:
                self_ints = struct.pack('!IIIII', self.serial, self.refresh,
                                        self.retry, self.expire, self.minimum)
                other_ints = struct.pack('!IIIII', other.serial, other.refresh,
                                         other.retry, other.expire,
                                         other.minimum)
                v = cmp(self_ints, other_ints)
        return v

########NEW FILE########
__FILENAME__ = SPF
# Copyright (C) 2006, 2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import dns.rdtypes.txtbase

class SPF(dns.rdtypes.txtbase.TXTBase):
    """SPF record

    @see: RFC 4408"""
    pass

########NEW FILE########
__FILENAME__ = SSHFP
# Copyright (C) 2005-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import struct

import dns.rdata
import dns.rdatatype

class SSHFP(dns.rdata.Rdata):
    """SSHFP record

    @ivar algorithm: the algorithm
    @type algorithm: int
    @ivar fp_type: the digest type
    @type fp_type: int
    @ivar fingerprint: the fingerprint
    @type fingerprint: string
    @see: draft-ietf-secsh-dns-05.txt"""

    __slots__ = ['algorithm', 'fp_type', 'fingerprint']

    def __init__(self, rdclass, rdtype, algorithm, fp_type,
                 fingerprint):
        super(SSHFP, self).__init__(rdclass, rdtype)
        self.algorithm = algorithm
        self.fp_type = fp_type
        self.fingerprint = fingerprint

    def to_text(self, origin=None, relativize=True, **kw):
        return '%d %d %s' % (self.algorithm,
                             self.fp_type,
                             dns.rdata._hexify(self.fingerprint,
                                               chunksize=128))

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        algorithm = tok.get_uint8()
        fp_type = tok.get_uint8()
        chunks = []
        while 1:
            t = tok.get().unescape()
            if t.is_eol_or_eof():
                break
            if not t.is_identifier():
                raise dns.exception.SyntaxError
            chunks.append(t.value)
        fingerprint = ''.join(chunks)
        fingerprint = fingerprint.decode('hex_codec')
        return cls(rdclass, rdtype, algorithm, fp_type, fingerprint)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        header = struct.pack("!BB", self.algorithm, self.fp_type)
        file.write(header)
        file.write(self.fingerprint)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        header = struct.unpack("!BB", wire[current : current + 2])
        current += 2
        rdlen -= 2
        fingerprint = wire[current : current + rdlen].unwrap()
        return cls(rdclass, rdtype, header[0], header[1], fingerprint)

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        hs = struct.pack("!BB", self.algorithm, self.fp_type)
        ho = struct.pack("!BB", other.algorithm, other.fp_type)
        v = cmp(hs, ho)
        if v == 0:
            v = cmp(self.fingerprint, other.fingerprint)
        return v

########NEW FILE########
__FILENAME__ = TLSA
# Copyright (C) 2005-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import struct

import dns.rdata
import dns.rdatatype

class TLSA(dns.rdata.Rdata):
    """TLSA record

    @ivar usage: The certificate usage
    @type usage: int
    @ivar selector: The selector field
    @type selector: int
    @ivar mtype: The 'matching type' field
    @type mtype: int
    @ivar cert: The 'Certificate Association Data' field
    @type cert: string
    @see: RFC 6698"""

    __slots__ = ['usage', 'selector', 'mtype', 'cert']

    def __init__(self, rdclass, rdtype, usage, selector,
                 mtype, cert):
        super(TLSA, self).__init__(rdclass, rdtype)
        self.usage = usage
        self.selector = selector
        self.mtype = mtype
        self.cert = cert

    def to_text(self, origin=None, relativize=True, **kw):
        return '%d %d %d %s' % (self.usage,
                                self.selector,
                                self.mtype,
                                dns.rdata._hexify(self.cert,
                                               chunksize=128))

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        usage = tok.get_uint8()
        selector = tok.get_uint8()
        mtype = tok.get_uint8()
        cert_chunks = []
        while 1:
            t = tok.get().unescape()
            if t.is_eol_or_eof():
                break
            if not t.is_identifier():
                raise dns.exception.SyntaxError
            cert_chunks.append(t.value)
        cert = ''.join(cert_chunks)
        cert = cert.decode('hex_codec')
        return cls(rdclass, rdtype, usage, selector, mtype, cert)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        header = struct.pack("!BBB", self.usage, self.selector, self.mtype)
        file.write(header)
        file.write(self.cert)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        header = struct.unpack("!BBB", wire[current : current + 3])
        current += 3
        rdlen -= 3
        cert = wire[current : current + rdlen].unwrap()
        return cls(rdclass, rdtype, header[0], header[1], header[2], cert)

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        hs = struct.pack("!BBB", self.usage, self.selector, self.mtype)
        ho = struct.pack("!BBB", other.usage, other.selector, other.mtype)
        v = cmp(hs, ho)
        if v == 0:
            v = cmp(self.cert, other.cert)
        return v

########NEW FILE########
__FILENAME__ = TXT
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import dns.rdtypes.txtbase

class TXT(dns.rdtypes.txtbase.TXTBase):
    """TXT record"""
    pass

########NEW FILE########
__FILENAME__ = X25
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import dns.exception
import dns.rdata
import dns.tokenizer

class X25(dns.rdata.Rdata):
    """X25 record

    @ivar address: the PSDN address
    @type address: string
    @see: RFC 1183"""

    __slots__ = ['address']

    def __init__(self, rdclass, rdtype, address):
        super(X25, self).__init__(rdclass, rdtype)
        self.address = address

    def to_text(self, origin=None, relativize=True, **kw):
        return '"%s"' % dns.rdata._escapify(self.address)

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        address = tok.get_string()
        tok.get_eol()
        return cls(rdclass, rdtype, address)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        l = len(self.address)
        assert l < 256
        byte = chr(l)
        file.write(byte)
        file.write(self.address)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        l = ord(wire[current])
        current += 1
        rdlen -= 1
        if l != rdlen:
            raise dns.exception.FormError
        address = wire[current : current + l].unwrap()
        return cls(rdclass, rdtype, address)

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        return cmp(self.address, other.address)

########NEW FILE########
__FILENAME__ = dsbase
# Copyright (C) 2010, 2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import struct

import dns.rdata
import dns.rdatatype

class DSBase(dns.rdata.Rdata):
    """Base class for rdata that is like a DS record

    @ivar key_tag: the key tag
    @type key_tag: int
    @ivar algorithm: the algorithm
    @type algorithm: int
    @ivar digest_type: the digest type
    @type digest_type: int
    @ivar digest: the digest
    @type digest: int
    @see: draft-ietf-dnsext-delegation-signer-14.txt"""

    __slots__ = ['key_tag', 'algorithm', 'digest_type', 'digest']

    def __init__(self, rdclass, rdtype, key_tag, algorithm, digest_type,
                 digest):
        super(DSBase, self).__init__(rdclass, rdtype)
        self.key_tag = key_tag
        self.algorithm = algorithm
        self.digest_type = digest_type
        self.digest = digest

    def to_text(self, origin=None, relativize=True, **kw):
        return '%d %d %d %s' % (self.key_tag, self.algorithm,
                                self.digest_type,
                                dns.rdata._hexify(self.digest,
                                                  chunksize=128))

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        key_tag = tok.get_uint16()
        algorithm = tok.get_uint8()
        digest_type = tok.get_uint8()
        chunks = []
        while 1:
            t = tok.get().unescape()
            if t.is_eol_or_eof():
                break
            if not t.is_identifier():
                raise dns.exception.SyntaxError
            chunks.append(t.value)
        digest = ''.join(chunks)
        digest = digest.decode('hex_codec')
        return cls(rdclass, rdtype, key_tag, algorithm, digest_type,
                   digest)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        header = struct.pack("!HBB", self.key_tag, self.algorithm,
                             self.digest_type)
        file.write(header)
        file.write(self.digest)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        header = struct.unpack("!HBB", wire[current : current + 4])
        current += 4
        rdlen -= 4
        digest = wire[current : current + rdlen].unwrap()
        return cls(rdclass, rdtype, header[0], header[1], header[2], digest)

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        hs = struct.pack("!HBB", self.key_tag, self.algorithm,
                         self.digest_type)
        ho = struct.pack("!HBB", other.key_tag, other.algorithm,
                         other.digest_type)
        v = cmp(hs, ho)
        if v == 0:
            v = cmp(self.digest, other.digest)
        return v

########NEW FILE########
__FILENAME__ = A
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import dns.exception
import dns.ipv4
import dns.rdata
import dns.tokenizer

class A(dns.rdata.Rdata):
    """A record.

    @ivar address: an IPv4 address
    @type address: string (in the standard "dotted quad" format)"""

    __slots__ = ['address']

    def __init__(self, rdclass, rdtype, address):
        super(A, self).__init__(rdclass, rdtype)
        # check that it's OK
        junk = dns.ipv4.inet_aton(address)
        self.address = address

    def to_text(self, origin=None, relativize=True, **kw):
        return self.address

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        address = tok.get_identifier()
        tok.get_eol()
        return cls(rdclass, rdtype, address)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        file.write(dns.ipv4.inet_aton(self.address))

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        address = dns.ipv4.inet_ntoa(wire[current : current + rdlen])
        return cls(rdclass, rdtype, address)

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        sa = dns.ipv4.inet_aton(self.address)
        oa = dns.ipv4.inet_aton(other.address)
        return cmp(sa, oa)

########NEW FILE########
__FILENAME__ = AAAA
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import dns.exception
import dns.inet
import dns.rdata
import dns.tokenizer

class AAAA(dns.rdata.Rdata):
    """AAAA record.

    @ivar address: an IPv6 address
    @type address: string (in the standard IPv6 format)"""

    __slots__ = ['address']

    def __init__(self, rdclass, rdtype, address):
        super(AAAA, self).__init__(rdclass, rdtype)
        # check that it's OK
        junk = dns.inet.inet_pton(dns.inet.AF_INET6, address)
        self.address = address

    def to_text(self, origin=None, relativize=True, **kw):
        return self.address

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        address = tok.get_identifier()
        tok.get_eol()
        return cls(rdclass, rdtype, address)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        file.write(dns.inet.inet_pton(dns.inet.AF_INET6, self.address))

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        address = dns.inet.inet_ntop(dns.inet.AF_INET6,
                                     wire[current : current + rdlen])
        return cls(rdclass, rdtype, address)

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        sa = dns.inet.inet_pton(dns.inet.AF_INET6, self.address)
        oa = dns.inet.inet_pton(dns.inet.AF_INET6, other.address)
        return cmp(sa, oa)

########NEW FILE########
__FILENAME__ = APL
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import cStringIO
import struct

import dns.exception
import dns.inet
import dns.rdata
import dns.tokenizer

class APLItem(object):
    """An APL list item.

    @ivar family: the address family (IANA address family registry)
    @type family: int
    @ivar negation: is this item negated?
    @type negation: bool
    @ivar address: the address
    @type address: string
    @ivar prefix: the prefix length
    @type prefix: int
    """

    __slots__ = ['family', 'negation', 'address', 'prefix']

    def __init__(self, family, negation, address, prefix):
        self.family = family
        self.negation = negation
        self.address = address
        self.prefix = prefix

    def __str__(self):
        if self.negation:
            return "!%d:%s/%s" % (self.family, self.address, self.prefix)
        else:
            return "%d:%s/%s" % (self.family, self.address, self.prefix)

    def to_wire(self, file):
        if self.family == 1:
            address = dns.inet.inet_pton(dns.inet.AF_INET, self.address)
        elif self.family == 2:
            address = dns.inet.inet_pton(dns.inet.AF_INET6, self.address)
        else:
            address = self.address.decode('hex_codec')
        #
        # Truncate least significant zero bytes.
        #
        last = 0
        for i in xrange(len(address) - 1, -1, -1):
            if address[i] != chr(0):
                last = i + 1
                break
        address = address[0 : last]
        l = len(address)
        assert l < 128
        if self.negation:
            l |= 0x80
        header = struct.pack('!HBB', self.family, self.prefix, l)
        file.write(header)
        file.write(address)

class APL(dns.rdata.Rdata):
    """APL record.

    @ivar items: a list of APL items
    @type items: list of APL_Item
    @see: RFC 3123"""

    __slots__ = ['items']

    def __init__(self, rdclass, rdtype, items):
        super(APL, self).__init__(rdclass, rdtype)
        self.items = items

    def to_text(self, origin=None, relativize=True, **kw):
        return ' '.join(map(lambda x: str(x), self.items))

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        items = []
        while 1:
            token = tok.get().unescape()
            if token.is_eol_or_eof():
                break
            item = token.value
            if item[0] == '!':
                negation = True
                item = item[1:]
            else:
                negation = False
            (family, rest) = item.split(':', 1)
            family = int(family)
            (address, prefix) = rest.split('/', 1)
            prefix = int(prefix)
            item = APLItem(family, negation, address, prefix)
            items.append(item)

        return cls(rdclass, rdtype, items)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        for item in self.items:
            item.to_wire(file)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        items = []
        while 1:
            if rdlen < 4:
                raise dns.exception.FormError
            header = struct.unpack('!HBB', wire[current : current + 4])
            afdlen = header[2]
            if afdlen > 127:
                negation = True
                afdlen -= 128
            else:
                negation = False
            current += 4
            rdlen -= 4
            if rdlen < afdlen:
                raise dns.exception.FormError
            address = wire[current : current + afdlen].unwrap()
            l = len(address)
            if header[0] == 1:
                if l < 4:
                    address += '\x00' * (4 - l)
                address = dns.inet.inet_ntop(dns.inet.AF_INET, address)
            elif header[0] == 2:
                if l < 16:
                    address += '\x00' * (16 - l)
                address = dns.inet.inet_ntop(dns.inet.AF_INET6, address)
            else:
                #
                # This isn't really right according to the RFC, but it
                # seems better than throwing an exception
                #
                address = address.encode('hex_codec')
            current += afdlen
            rdlen -= afdlen
            item = APLItem(header[0], negation, address, header[1])
            items.append(item)
            if rdlen == 0:
                break
        return cls(rdclass, rdtype, items)

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        f = cStringIO.StringIO()
        self.to_wire(f)
        wire1 = f.getvalue()
        f.seek(0)
        f.truncate()
        other.to_wire(f)
        wire2 = f.getvalue()
        f.close()

        return cmp(wire1, wire2)

########NEW FILE########
__FILENAME__ = DHCID
# Copyright (C) 2006, 2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import dns.exception

class DHCID(dns.rdata.Rdata):
    """DHCID record

    @ivar data: the data (the content of the RR is opaque as far as the
    DNS is concerned)
    @type data: string
    @see: RFC 4701"""

    __slots__ = ['data']

    def __init__(self, rdclass, rdtype, data):
        super(DHCID, self).__init__(rdclass, rdtype)
        self.data = data

    def to_text(self, origin=None, relativize=True, **kw):
        return dns.rdata._base64ify(self.data)

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        chunks = []
        while 1:
            t = tok.get().unescape()
            if t.is_eol_or_eof():
                break
            if not t.is_identifier():
                raise dns.exception.SyntaxError
            chunks.append(t.value)
        b64 = ''.join(chunks)
        data = b64.decode('base64_codec')
        return cls(rdclass, rdtype, data)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        file.write(self.data)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        data = wire[current : current + rdlen].unwrap()
        return cls(rdclass, rdtype, data)

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        return cmp(self.data, other.data)

########NEW FILE########
__FILENAME__ = IPSECKEY
# Copyright (C) 2006, 2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import cStringIO
import struct

import dns.exception
import dns.inet
import dns.name

class IPSECKEY(dns.rdata.Rdata):
    """IPSECKEY record

    @ivar precedence: the precedence for this key data
    @type precedence: int
    @ivar gateway_type: the gateway type
    @type gateway_type: int
    @ivar algorithm: the algorithm to use
    @type algorithm: int
    @ivar gateway: the public key
    @type gateway: None, IPv4 address, IPV6 address, or domain name
    @ivar key: the public key
    @type key: string
    @see: RFC 4025"""

    __slots__ = ['precedence', 'gateway_type', 'algorithm', 'gateway', 'key']

    def __init__(self, rdclass, rdtype, precedence, gateway_type, algorithm,
                 gateway, key):
        super(IPSECKEY, self).__init__(rdclass, rdtype)
        if gateway_type == 0:
            if gateway != '.' and not gateway is None:
                raise SyntaxError('invalid gateway for gateway type 0')
            gateway = None
        elif gateway_type == 1:
            # check that it's OK
            junk = dns.inet.inet_pton(dns.inet.AF_INET, gateway)
        elif gateway_type == 2:
            # check that it's OK
            junk = dns.inet.inet_pton(dns.inet.AF_INET6, gateway)
        elif gateway_type == 3:
            pass
        else:
            raise SyntaxError('invalid IPSECKEY gateway type: %d' % gateway_type)
        self.precedence = precedence
        self.gateway_type = gateway_type
        self.algorithm = algorithm
        self.gateway = gateway
        self.key = key

    def to_text(self, origin=None, relativize=True, **kw):
        if self.gateway_type == 0:
            gateway = '.'
        elif self.gateway_type == 1:
            gateway = self.gateway
        elif self.gateway_type == 2:
            gateway = self.gateway
        elif self.gateway_type == 3:
            gateway = str(self.gateway.choose_relativity(origin, relativize))
        else:
            raise ValueError('invalid gateway type')
        return '%d %d %d %s %s' % (self.precedence, self.gateway_type,
                                   self.algorithm, gateway,
                                   dns.rdata._base64ify(self.key))

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        precedence = tok.get_uint8()
        gateway_type = tok.get_uint8()
        algorithm = tok.get_uint8()
        if gateway_type == 3:
            gateway = tok.get_name().choose_relativity(origin, relativize)
        else:
            gateway = tok.get_string()
        chunks = []
        while 1:
            t = tok.get().unescape()
            if t.is_eol_or_eof():
                break
            if not t.is_identifier():
                raise dns.exception.SyntaxError
            chunks.append(t.value)
        b64 = ''.join(chunks)
        key = b64.decode('base64_codec')
        return cls(rdclass, rdtype, precedence, gateway_type, algorithm,
                   gateway, key)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        header = struct.pack("!BBB", self.precedence, self.gateway_type,
                             self.algorithm)
        file.write(header)
        if self.gateway_type == 0:
            pass
        elif self.gateway_type == 1:
            file.write(dns.inet.inet_pton(dns.inet.AF_INET, self.gateway))
        elif self.gateway_type == 2:
            file.write(dns.inet.inet_pton(dns.inet.AF_INET6, self.gateway))
        elif self.gateway_type == 3:
            self.gateway.to_wire(file, None, origin)
        else:
            raise ValueError('invalid gateway type')
        file.write(self.key)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        if rdlen < 3:
            raise dns.exception.FormError
        header = struct.unpack('!BBB', wire[current : current + 3])
        gateway_type = header[1]
        current += 3
        rdlen -= 3
        if gateway_type == 0:
            gateway = None
        elif gateway_type == 1:
            gateway = dns.inet.inet_ntop(dns.inet.AF_INET,
                                         wire[current : current + 4])
            current += 4
            rdlen -= 4
        elif gateway_type == 2:
            gateway = dns.inet.inet_ntop(dns.inet.AF_INET6,
                                         wire[current : current + 16])
            current += 16
            rdlen -= 16
        elif gateway_type == 3:
            (gateway, cused) = dns.name.from_wire(wire[: current + rdlen],
                                                  current)
            current += cused
            rdlen -= cused
        else:
            raise dns.exception.FormError('invalid IPSECKEY gateway type')
        key = wire[current : current + rdlen].unwrap()
        return cls(rdclass, rdtype, header[0], gateway_type, header[2],
                   gateway, key)

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        f = cStringIO.StringIO()
        self.to_wire(f)
        wire1 = f.getvalue()
        f.seek(0)
        f.truncate()
        other.to_wire(f)
        wire2 = f.getvalue()
        f.close()

        return cmp(wire1, wire2)

########NEW FILE########
__FILENAME__ = KX
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import dns.rdtypes.mxbase

class KX(dns.rdtypes.mxbase.UncompressedMX):
    """KX record"""
    pass

########NEW FILE########
__FILENAME__ = NAPTR
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import struct

import dns.exception
import dns.name
import dns.rdata

def _write_string(file, s):
    l = len(s)
    assert l < 256
    byte = chr(l)
    file.write(byte)
    file.write(s)

class NAPTR(dns.rdata.Rdata):
    """NAPTR record

    @ivar order: order
    @type order: int
    @ivar preference: preference
    @type preference: int
    @ivar flags: flags
    @type flags: string
    @ivar service: service
    @type service: string
    @ivar regexp: regular expression
    @type regexp: string
    @ivar replacement: replacement name
    @type replacement: dns.name.Name object
    @see: RFC 3403"""

    __slots__ = ['order', 'preference', 'flags', 'service', 'regexp',
                 'replacement']

    def __init__(self, rdclass, rdtype, order, preference, flags, service,
                 regexp, replacement):
        super(NAPTR, self).__init__(rdclass, rdtype)
        self.order = order
        self.preference = preference
        self.flags = flags
        self.service = service
        self.regexp = regexp
        self.replacement = replacement

    def to_text(self, origin=None, relativize=True, **kw):
        replacement = self.replacement.choose_relativity(origin, relativize)
        return '%d %d "%s" "%s" "%s" %s' % \
               (self.order, self.preference,
                dns.rdata._escapify(self.flags),
                dns.rdata._escapify(self.service),
                dns.rdata._escapify(self.regexp),
                self.replacement)

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        order = tok.get_uint16()
        preference = tok.get_uint16()
        flags = tok.get_string()
        service = tok.get_string()
        regexp = tok.get_string()
        replacement = tok.get_name()
        replacement = replacement.choose_relativity(origin, relativize)
        tok.get_eol()
        return cls(rdclass, rdtype, order, preference, flags, service,
                   regexp, replacement)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        two_ints = struct.pack("!HH", self.order, self.preference)
        file.write(two_ints)
        _write_string(file, self.flags)
        _write_string(file, self.service)
        _write_string(file, self.regexp)
        self.replacement.to_wire(file, compress, origin)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        (order, preference) = struct.unpack('!HH', wire[current : current + 4])
        current += 4
        rdlen -= 4
        strings = []
        for i in xrange(3):
            l = ord(wire[current])
            current += 1
            rdlen -= 1
            if l > rdlen or rdlen < 0:
                raise dns.exception.FormError
            s = wire[current : current + l].unwrap()
            current += l
            rdlen -= l
            strings.append(s)
        (replacement, cused) = dns.name.from_wire(wire[: current + rdlen],
                                                  current)
        if cused != rdlen:
            raise dns.exception.FormError
        if not origin is None:
            replacement = replacement.relativize(origin)
        return cls(rdclass, rdtype, order, preference, strings[0], strings[1],
                   strings[2], replacement)

    from_wire = classmethod(from_wire)

    def choose_relativity(self, origin = None, relativize = True):
        self.replacement = self.replacement.choose_relativity(origin,
                                                              relativize)

    def _cmp(self, other):
        sp = struct.pack("!HH", self.order, self.preference)
        op = struct.pack("!HH", other.order, other.preference)
        v = cmp(sp, op)
        if v == 0:
            v = cmp(self.flags, other.flags)
            if v == 0:
                v = cmp(self.service, other.service)
                if v == 0:
                    v = cmp(self.regexp, other.regexp)
                    if v == 0:
                        v = cmp(self.replacement, other.replacement)
        return v

########NEW FILE########
__FILENAME__ = NSAP
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import dns.exception
import dns.rdata
import dns.tokenizer

class NSAP(dns.rdata.Rdata):
    """NSAP record.

    @ivar address: a NASP
    @type address: string
    @see: RFC 1706"""

    __slots__ = ['address']

    def __init__(self, rdclass, rdtype, address):
        super(NSAP, self).__init__(rdclass, rdtype)
        self.address = address

    def to_text(self, origin=None, relativize=True, **kw):
        return "0x%s" % self.address.encode('hex_codec')

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        address = tok.get_string()
        t = tok.get_eol()
        if address[0:2] != '0x':
            raise dns.exception.SyntaxError('string does not start with 0x')
        address = address[2:].replace('.', '')
        if len(address) % 2 != 0:
            raise dns.exception.SyntaxError('hexstring has odd length')
        address = address.decode('hex_codec')
        return cls(rdclass, rdtype, address)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        file.write(self.address)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        address = wire[current : current + rdlen].unwrap()
        return cls(rdclass, rdtype, address)

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        return cmp(self.address, other.address)

########NEW FILE########
__FILENAME__ = NSAP_PTR
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import dns.rdtypes.nsbase

class NSAP_PTR(dns.rdtypes.nsbase.UncompressedNS):
    """NSAP-PTR record"""
    pass

########NEW FILE########
__FILENAME__ = PX
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import struct

import dns.exception
import dns.rdata
import dns.name

class PX(dns.rdata.Rdata):
    """PX record.

    @ivar preference: the preference value
    @type preference: int
    @ivar map822: the map822 name
    @type map822: dns.name.Name object
    @ivar mapx400: the mapx400 name
    @type mapx400: dns.name.Name object
    @see: RFC 2163"""

    __slots__ = ['preference', 'map822', 'mapx400']

    def __init__(self, rdclass, rdtype, preference, map822, mapx400):
        super(PX, self).__init__(rdclass, rdtype)
        self.preference = preference
        self.map822 = map822
        self.mapx400 = mapx400

    def to_text(self, origin=None, relativize=True, **kw):
        map822 = self.map822.choose_relativity(origin, relativize)
        mapx400 = self.mapx400.choose_relativity(origin, relativize)
        return '%d %s %s' % (self.preference, map822, mapx400)

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        preference = tok.get_uint16()
        map822 = tok.get_name()
        map822 = map822.choose_relativity(origin, relativize)
        mapx400 = tok.get_name(None)
        mapx400 = mapx400.choose_relativity(origin, relativize)
        tok.get_eol()
        return cls(rdclass, rdtype, preference, map822, mapx400)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        pref = struct.pack("!H", self.preference)
        file.write(pref)
        self.map822.to_wire(file, None, origin)
        self.mapx400.to_wire(file, None, origin)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        (preference, ) = struct.unpack('!H', wire[current : current + 2])
        current += 2
        rdlen -= 2
        (map822, cused) = dns.name.from_wire(wire[: current + rdlen],
                                               current)
        if cused > rdlen:
            raise dns.exception.FormError
        current += cused
        rdlen -= cused
        if not origin is None:
            map822 = map822.relativize(origin)
        (mapx400, cused) = dns.name.from_wire(wire[: current + rdlen],
                                              current)
        if cused != rdlen:
            raise dns.exception.FormError
        if not origin is None:
            mapx400 = mapx400.relativize(origin)
        return cls(rdclass, rdtype, preference, map822, mapx400)

    from_wire = classmethod(from_wire)

    def choose_relativity(self, origin = None, relativize = True):
        self.map822 = self.map822.choose_relativity(origin, relativize)
        self.mapx400 = self.mapx400.choose_relativity(origin, relativize)

    def _cmp(self, other):
        sp = struct.pack("!H", self.preference)
        op = struct.pack("!H", other.preference)
        v = cmp(sp, op)
        if v == 0:
            v = cmp(self.map822, other.map822)
            if v == 0:
                v = cmp(self.mapx400, other.mapx400)
        return v

########NEW FILE########
__FILENAME__ = SRV
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import struct

import dns.exception
import dns.rdata
import dns.name

class SRV(dns.rdata.Rdata):
    """SRV record

    @ivar priority: the priority
    @type priority: int
    @ivar weight: the weight
    @type weight: int
    @ivar port: the port of the service
    @type port: int
    @ivar target: the target host
    @type target: dns.name.Name object
    @see: RFC 2782"""

    __slots__ = ['priority', 'weight', 'port', 'target']

    def __init__(self, rdclass, rdtype, priority, weight, port, target):
        super(SRV, self).__init__(rdclass, rdtype)
        self.priority = priority
        self.weight = weight
        self.port = port
        self.target = target

    def to_text(self, origin=None, relativize=True, **kw):
        target = self.target.choose_relativity(origin, relativize)
        return '%d %d %d %s' % (self.priority, self.weight, self.port,
                                target)

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        priority = tok.get_uint16()
        weight = tok.get_uint16()
        port = tok.get_uint16()
        target = tok.get_name(None)
        target = target.choose_relativity(origin, relativize)
        tok.get_eol()
        return cls(rdclass, rdtype, priority, weight, port, target)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        three_ints = struct.pack("!HHH", self.priority, self.weight, self.port)
        file.write(three_ints)
        self.target.to_wire(file, compress, origin)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        (priority, weight, port) = struct.unpack('!HHH',
                                                 wire[current : current + 6])
        current += 6
        rdlen -= 6
        (target, cused) = dns.name.from_wire(wire[: current + rdlen],
                                             current)
        if cused != rdlen:
            raise dns.exception.FormError
        if not origin is None:
            target = target.relativize(origin)
        return cls(rdclass, rdtype, priority, weight, port, target)

    from_wire = classmethod(from_wire)

    def choose_relativity(self, origin = None, relativize = True):
        self.target = self.target.choose_relativity(origin, relativize)

    def _cmp(self, other):
        sp = struct.pack("!HHH", self.priority, self.weight, self.port)
        op = struct.pack("!HHH", other.priority, other.weight, other.port)
        v = cmp(sp, op)
        if v == 0:
            v = cmp(self.target, other.target)
        return v

########NEW FILE########
__FILENAME__ = WKS
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import socket
import struct

import dns.ipv4
import dns.rdata

_proto_tcp = socket.getprotobyname('tcp')
_proto_udp = socket.getprotobyname('udp')

class WKS(dns.rdata.Rdata):
    """WKS record

    @ivar address: the address
    @type address: string
    @ivar protocol: the protocol
    @type protocol: int
    @ivar bitmap: the bitmap
    @type bitmap: string
    @see: RFC 1035"""

    __slots__ = ['address', 'protocol', 'bitmap']

    def __init__(self, rdclass, rdtype, address, protocol, bitmap):
        super(WKS, self).__init__(rdclass, rdtype)
        self.address = address
        self.protocol = protocol
        self.bitmap = bitmap

    def to_text(self, origin=None, relativize=True, **kw):
        bits = []
        for i in xrange(0, len(self.bitmap)):
            byte = ord(self.bitmap[i])
            for j in xrange(0, 8):
                if byte & (0x80 >> j):
                    bits.append(str(i * 8 + j))
        text = ' '.join(bits)
        return '%s %d %s' % (self.address, self.protocol, text)

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        address = tok.get_string()
        protocol = tok.get_string()
        if protocol.isdigit():
            protocol = int(protocol)
        else:
            protocol = socket.getprotobyname(protocol)
        bitmap = []
        while 1:
            token = tok.get().unescape()
            if token.is_eol_or_eof():
                break
            if token.value.isdigit():
                serv = int(token.value)
            else:
                if protocol != _proto_udp and protocol != _proto_tcp:
                    raise NotImplementedError("protocol must be TCP or UDP")
                if protocol == _proto_udp:
                    protocol_text = "udp"
                else:
                    protocol_text = "tcp"
                serv = socket.getservbyname(token.value, protocol_text)
            i = serv // 8
            l = len(bitmap)
            if l < i + 1:
                for j in xrange(l, i + 1):
                    bitmap.append('\x00')
            bitmap[i] = chr(ord(bitmap[i]) | (0x80 >> (serv % 8)))
        bitmap = dns.rdata._truncate_bitmap(bitmap)
        return cls(rdclass, rdtype, address, protocol, bitmap)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        file.write(dns.ipv4.inet_aton(self.address))
        protocol = struct.pack('!B', self.protocol)
        file.write(protocol)
        file.write(self.bitmap)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        address = dns.ipv4.inet_ntoa(wire[current : current + 4])
        protocol, = struct.unpack('!B', wire[current + 4 : current + 5])
        current += 5
        rdlen -= 5
        bitmap = wire[current : current + rdlen].unwrap()
        return cls(rdclass, rdtype, address, protocol, bitmap)

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        sa = dns.ipv4.inet_aton(self.address)
        oa = dns.ipv4.inet_aton(other.address)
        v = cmp(sa, oa)
        if v == 0:
            sp = struct.pack('!B', self.protocol)
            op = struct.pack('!B', other.protocol)
            v = cmp(sp, op)
            if v == 0:
                v = cmp(self.bitmap, other.bitmap)
        return v

########NEW FILE########
__FILENAME__ = mxbase
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""MX-like base classes."""

import cStringIO
import struct

import dns.exception
import dns.rdata
import dns.name

class MXBase(dns.rdata.Rdata):
    """Base class for rdata that is like an MX record.

    @ivar preference: the preference value
    @type preference: int
    @ivar exchange: the exchange name
    @type exchange: dns.name.Name object"""

    __slots__ = ['preference', 'exchange']

    def __init__(self, rdclass, rdtype, preference, exchange):
        super(MXBase, self).__init__(rdclass, rdtype)
        self.preference = preference
        self.exchange = exchange

    def to_text(self, origin=None, relativize=True, **kw):
        exchange = self.exchange.choose_relativity(origin, relativize)
        return '%d %s' % (self.preference, exchange)

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        preference = tok.get_uint16()
        exchange = tok.get_name()
        exchange = exchange.choose_relativity(origin, relativize)
        tok.get_eol()
        return cls(rdclass, rdtype, preference, exchange)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        pref = struct.pack("!H", self.preference)
        file.write(pref)
        self.exchange.to_wire(file, compress, origin)

    def to_digestable(self, origin = None):
        return struct.pack("!H", self.preference) + \
            self.exchange.to_digestable(origin)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        (preference, ) = struct.unpack('!H', wire[current : current + 2])
        current += 2
        rdlen -= 2
        (exchange, cused) = dns.name.from_wire(wire[: current + rdlen],
                                               current)
        if cused != rdlen:
            raise dns.exception.FormError
        if not origin is None:
            exchange = exchange.relativize(origin)
        return cls(rdclass, rdtype, preference, exchange)

    from_wire = classmethod(from_wire)

    def choose_relativity(self, origin = None, relativize = True):
        self.exchange = self.exchange.choose_relativity(origin, relativize)

    def _cmp(self, other):
        sp = struct.pack("!H", self.preference)
        op = struct.pack("!H", other.preference)
        v = cmp(sp, op)
        if v == 0:
            v = cmp(self.exchange, other.exchange)
        return v

class UncompressedMX(MXBase):
    """Base class for rdata that is like an MX record, but whose name
    is not compressed when converted to DNS wire format, and whose
    digestable form is not downcased."""

    def to_wire(self, file, compress = None, origin = None):
        super(UncompressedMX, self).to_wire(file, None, origin)

    def to_digestable(self, origin = None):
        f = cStringIO.StringIO()
        self.to_wire(f, None, origin)
        return f.getvalue()

class UncompressedDowncasingMX(MXBase):
    """Base class for rdata that is like an MX record, but whose name
    is not compressed when convert to DNS wire format."""

    def to_wire(self, file, compress = None, origin = None):
        super(UncompressedDowncasingMX, self).to_wire(file, None, origin)

########NEW FILE########
__FILENAME__ = nsbase
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""NS-like base classes."""

import cStringIO

import dns.exception
import dns.rdata
import dns.name

class NSBase(dns.rdata.Rdata):
    """Base class for rdata that is like an NS record.

    @ivar target: the target name of the rdata
    @type target: dns.name.Name object"""

    __slots__ = ['target']

    def __init__(self, rdclass, rdtype, target):
        super(NSBase, self).__init__(rdclass, rdtype)
        self.target = target

    def to_text(self, origin=None, relativize=True, **kw):
        target = self.target.choose_relativity(origin, relativize)
        return str(target)

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        target = tok.get_name()
        target = target.choose_relativity(origin, relativize)
        tok.get_eol()
        return cls(rdclass, rdtype, target)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        self.target.to_wire(file, compress, origin)

    def to_digestable(self, origin = None):
        return self.target.to_digestable(origin)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        (target, cused) = dns.name.from_wire(wire[: current + rdlen],
                                             current)
        if cused != rdlen:
            raise dns.exception.FormError
        if not origin is None:
            target = target.relativize(origin)
        return cls(rdclass, rdtype, target)

    from_wire = classmethod(from_wire)

    def choose_relativity(self, origin = None, relativize = True):
        self.target = self.target.choose_relativity(origin, relativize)

    def _cmp(self, other):
        return cmp(self.target, other.target)

class UncompressedNS(NSBase):
    """Base class for rdata that is like an NS record, but whose name
    is not compressed when convert to DNS wire format, and whose
    digestable form is not downcased."""

    def to_wire(self, file, compress = None, origin = None):
        super(UncompressedNS, self).to_wire(file, None, origin)

    def to_digestable(self, origin = None):
        f = cStringIO.StringIO()
        self.to_wire(f, None, origin)
        return f.getvalue()

########NEW FILE########
__FILENAME__ = txtbase
# Copyright (C) 2006, 2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""TXT-like base class."""

import dns.exception
import dns.rdata
import dns.tokenizer

class TXTBase(dns.rdata.Rdata):
    """Base class for rdata that is like a TXT record

    @ivar strings: the text strings
    @type strings: list of string
    @see: RFC 1035"""

    __slots__ = ['strings']

    def __init__(self, rdclass, rdtype, strings):
        super(TXTBase, self).__init__(rdclass, rdtype)
        if isinstance(strings, str):
            strings = [ strings ]
        self.strings = strings[:]

    def to_text(self, origin=None, relativize=True, **kw):
        txt = ''
        prefix = ''
        for s in self.strings:
            txt += '%s"%s"' % (prefix, dns.rdata._escapify(s))
            prefix = ' '
        return txt

    def from_text(cls, rdclass, rdtype, tok, origin = None, relativize = True):
        strings = []
        while 1:
            token = tok.get().unescape()
            if token.is_eol_or_eof():
                break
            if not (token.is_quoted_string() or token.is_identifier()):
                raise dns.exception.SyntaxError("expected a string")
            if len(token.value) > 255:
                raise dns.exception.SyntaxError("string too long")
            strings.append(token.value)
        if len(strings) == 0:
            raise dns.exception.UnexpectedEnd
        return cls(rdclass, rdtype, strings)

    from_text = classmethod(from_text)

    def to_wire(self, file, compress = None, origin = None):
        for s in self.strings:
            l = len(s)
            assert l < 256
            byte = chr(l)
            file.write(byte)
            file.write(s)

    def from_wire(cls, rdclass, rdtype, wire, current, rdlen, origin = None):
        strings = []
        while rdlen > 0:
            l = ord(wire[current])
            current += 1
            rdlen -= 1
            if l > rdlen:
                raise dns.exception.FormError
            s = wire[current : current + l].unwrap()
            current += l
            rdlen -= l
            strings.append(s)
        return cls(rdclass, rdtype, strings)

    from_wire = classmethod(from_wire)

    def _cmp(self, other):
        return cmp(self.strings, other.strings)

########NEW FILE########
__FILENAME__ = renderer
# Copyright (C) 2001-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""Help for building DNS wire format messages"""

import cStringIO
import struct
import random
import time

import dns.exception
import dns.tsig

QUESTION = 0
ANSWER = 1
AUTHORITY = 2
ADDITIONAL = 3

class Renderer(object):
    """Helper class for building DNS wire-format messages.

    Most applications can use the higher-level L{dns.message.Message}
    class and its to_wire() method to generate wire-format messages.
    This class is for those applications which need finer control
    over the generation of messages.

    Typical use::

        r = dns.renderer.Renderer(id=1, flags=0x80, max_size=512)
        r.add_question(qname, qtype, qclass)
        r.add_rrset(dns.renderer.ANSWER, rrset_1)
        r.add_rrset(dns.renderer.ANSWER, rrset_2)
        r.add_rrset(dns.renderer.AUTHORITY, ns_rrset)
        r.add_edns(0, 0, 4096)
        r.add_rrset(dns.renderer.ADDTIONAL, ad_rrset_1)
        r.add_rrset(dns.renderer.ADDTIONAL, ad_rrset_2)
        r.write_header()
        r.add_tsig(keyname, secret, 300, 1, 0, '', request_mac)
        wire = r.get_wire()

    @ivar output: where rendering is written
    @type output: cStringIO.StringIO object
    @ivar id: the message id
    @type id: int
    @ivar flags: the message flags
    @type flags: int
    @ivar max_size: the maximum size of the message
    @type max_size: int
    @ivar origin: the origin to use when rendering relative names
    @type origin: dns.name.Name object
    @ivar compress: the compression table
    @type compress: dict
    @ivar section: the section currently being rendered
    @type section: int (dns.renderer.QUESTION, dns.renderer.ANSWER,
    dns.renderer.AUTHORITY, or dns.renderer.ADDITIONAL)
    @ivar counts: list of the number of RRs in each section
    @type counts: int list of length 4
    @ivar mac: the MAC of the rendered message (if TSIG was used)
    @type mac: string
    """

    def __init__(self, id=None, flags=0, max_size=65535, origin=None):
        """Initialize a new renderer.

        @param id: the message id
        @type id: int
        @param flags: the DNS message flags
        @type flags: int
        @param max_size: the maximum message size; the default is 65535.
        If rendering results in a message greater than I{max_size},
        then L{dns.exception.TooBig} will be raised.
        @type max_size: int
        @param origin: the origin to use when rendering relative names
        @type origin: dns.name.Namem or None.
        """

        self.output = cStringIO.StringIO()
        if id is None:
            self.id = random.randint(0, 65535)
        else:
            self.id = id
        self.flags = flags
        self.max_size = max_size
        self.origin = origin
        self.compress = {}
        self.section = QUESTION
        self.counts = [0, 0, 0, 0]
        self.output.write('\x00' * 12)
        self.mac = ''

    def _rollback(self, where):
        """Truncate the output buffer at offset I{where}, and remove any
        compression table entries that pointed beyond the truncation
        point.

        @param where: the offset
        @type where: int
        """

        self.output.seek(where)
        self.output.truncate()
        keys_to_delete = []
        for k, v in self.compress.iteritems():
            if v >= where:
                keys_to_delete.append(k)
        for k in keys_to_delete:
            del self.compress[k]

    def _set_section(self, section):
        """Set the renderer's current section.

        Sections must be rendered order: QUESTION, ANSWER, AUTHORITY,
        ADDITIONAL.  Sections may be empty.

        @param section: the section
        @type section: int
        @raises dns.exception.FormError: an attempt was made to set
        a section value less than the current section.
        """

        if self.section != section:
            if self.section > section:
                raise dns.exception.FormError
            self.section = section

    def add_question(self, qname, rdtype, rdclass=dns.rdataclass.IN):
        """Add a question to the message.

        @param qname: the question name
        @type qname: dns.name.Name
        @param rdtype: the question rdata type
        @type rdtype: int
        @param rdclass: the question rdata class
        @type rdclass: int
        """

        self._set_section(QUESTION)
        before = self.output.tell()
        qname.to_wire(self.output, self.compress, self.origin)
        self.output.write(struct.pack("!HH", rdtype, rdclass))
        after = self.output.tell()
        if after >= self.max_size:
            self._rollback(before)
            raise dns.exception.TooBig
        self.counts[QUESTION] += 1

    def add_rrset(self, section, rrset, **kw):
        """Add the rrset to the specified section.

        Any keyword arguments are passed on to the rdataset's to_wire()
        routine.

        @param section: the section
        @type section: int
        @param rrset: the rrset
        @type rrset: dns.rrset.RRset object
        """

        self._set_section(section)
        before = self.output.tell()
        n = rrset.to_wire(self.output, self.compress, self.origin, **kw)
        after = self.output.tell()
        if after >= self.max_size:
            self._rollback(before)
            raise dns.exception.TooBig
        self.counts[section] += n

    def add_rdataset(self, section, name, rdataset, **kw):
        """Add the rdataset to the specified section, using the specified
        name as the owner name.

        Any keyword arguments are passed on to the rdataset's to_wire()
        routine.

        @param section: the section
        @type section: int
        @param name: the owner name
        @type name: dns.name.Name object
        @param rdataset: the rdataset
        @type rdataset: dns.rdataset.Rdataset object
        """

        self._set_section(section)
        before = self.output.tell()
        n = rdataset.to_wire(name, self.output, self.compress, self.origin,
                             **kw)
        after = self.output.tell()
        if after >= self.max_size:
            self._rollback(before)
            raise dns.exception.TooBig
        self.counts[section] += n

    def add_edns(self, edns, ednsflags, payload, options=None):
        """Add an EDNS OPT record to the message.

        @param edns: The EDNS level to use.
        @type edns: int
        @param ednsflags: EDNS flag values.
        @type ednsflags: int
        @param payload: The EDNS sender's payload field, which is the maximum
        size of UDP datagram the sender can handle.
        @type payload: int
        @param options: The EDNS options list
        @type options: list of dns.edns.Option instances
        @see: RFC 2671
        """

        # make sure the EDNS version in ednsflags agrees with edns
        ednsflags &= 0xFF00FFFFL
        ednsflags |= (edns << 16)
        self._set_section(ADDITIONAL)
        before = self.output.tell()
        self.output.write(struct.pack('!BHHIH', 0, dns.rdatatype.OPT, payload,
                                      ednsflags, 0))
        if not options is None:
            lstart = self.output.tell()
            for opt in options:
                stuff = struct.pack("!HH", opt.otype, 0)
                self.output.write(stuff)
                start = self.output.tell()
                opt.to_wire(self.output)
                end = self.output.tell()
                assert end - start < 65536
                self.output.seek(start - 2)
                stuff = struct.pack("!H", end - start)
                self.output.write(stuff)
                self.output.seek(0, 2)
            lend = self.output.tell()
            assert lend - lstart < 65536
            self.output.seek(lstart - 2)
            stuff = struct.pack("!H", lend - lstart)
            self.output.write(stuff)
            self.output.seek(0, 2)
        after = self.output.tell()
        if after >= self.max_size:
            self._rollback(before)
            raise dns.exception.TooBig
        self.counts[ADDITIONAL] += 1

    def add_tsig(self, keyname, secret, fudge, id, tsig_error, other_data,
                 request_mac, algorithm=dns.tsig.default_algorithm):
        """Add a TSIG signature to the message.

        @param keyname: the TSIG key name
        @type keyname: dns.name.Name object
        @param secret: the secret to use
        @type secret: string
        @param fudge: TSIG time fudge
        @type fudge: int
        @param id: the message id to encode in the tsig signature
        @type id: int
        @param tsig_error: TSIG error code; default is 0.
        @type tsig_error: int
        @param other_data: TSIG other data.
        @type other_data: string
        @param request_mac: This message is a response to the request which
        had the specified MAC.
        @type request_mac: string
        @param algorithm: the TSIG algorithm to use
        @type algorithm: dns.name.Name object
        """

        self._set_section(ADDITIONAL)
        before = self.output.tell()
        s = self.output.getvalue()
        (tsig_rdata, self.mac, ctx) = dns.tsig.sign(s,
                                                    keyname,
                                                    secret,
                                                    int(time.time()),
                                                    fudge,
                                                    id,
                                                    tsig_error,
                                                    other_data,
                                                    request_mac,
                                                    algorithm=algorithm)
        keyname.to_wire(self.output, self.compress, self.origin)
        self.output.write(struct.pack('!HHIH', dns.rdatatype.TSIG,
                                      dns.rdataclass.ANY, 0, 0))
        rdata_start = self.output.tell()
        self.output.write(tsig_rdata)
        after = self.output.tell()
        assert after - rdata_start < 65536
        if after >= self.max_size:
            self._rollback(before)
            raise dns.exception.TooBig
        self.output.seek(rdata_start - 2)
        self.output.write(struct.pack('!H', after - rdata_start))
        self.counts[ADDITIONAL] += 1
        self.output.seek(10)
        self.output.write(struct.pack('!H', self.counts[ADDITIONAL]))
        self.output.seek(0, 2)

    def write_header(self):
        """Write the DNS message header.

        Writing the DNS message header is done after all sections
        have been rendered, but before the optional TSIG signature
        is added.
        """

        self.output.seek(0)
        self.output.write(struct.pack('!HHHHHH', self.id, self.flags,
                                      self.counts[0], self.counts[1],
                                      self.counts[2], self.counts[3]))
        self.output.seek(0, 2)

    def get_wire(self):
        """Return the wire format message.

        @rtype: string
        """

        return self.output.getvalue()

########NEW FILE########
__FILENAME__ = resolver
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS stub resolver.

@var default_resolver: The default resolver object
@type default_resolver: dns.resolver.Resolver object"""

import socket
import sys
import time

try:
    import threading as _threading
except ImportError:
    import dummy_threading as _threading

import dns.exception
import dns.flags
import dns.ipv4
import dns.ipv6
import dns.message
import dns.name
import dns.query
import dns.rcode
import dns.rdataclass
import dns.rdatatype
import dns.reversename

if sys.platform == 'win32':
    import _winreg

class NXDOMAIN(dns.exception.DNSException):
    """The query name does not exist."""
    pass

class YXDOMAIN(dns.exception.DNSException):
    """The query name is too long after DNAME substitution."""
    pass

# The definition of the Timeout exception has moved from here to the
# dns.exception module.  We keep dns.resolver.Timeout defined for
# backwards compatibility.

Timeout = dns.exception.Timeout

class NoAnswer(dns.exception.DNSException):
    """The response did not contain an answer to the question."""
    pass

class NoNameservers(dns.exception.DNSException):
    """No non-broken nameservers are available to answer the query."""
    pass

class NotAbsolute(dns.exception.DNSException):
    """Raised if an absolute domain name is required but a relative name
    was provided."""
    pass

class NoRootSOA(dns.exception.DNSException):
    """Raised if for some reason there is no SOA at the root name.
    This should never happen!"""
    pass

class NoMetaqueries(dns.exception.DNSException):
    """Metaqueries are not allowed."""
    pass


class Answer(object):
    """DNS stub resolver answer

    Instances of this class bundle up the result of a successful DNS
    resolution.

    For convenience, the answer object implements much of the sequence
    protocol, forwarding to its rrset.  E.g. "for a in answer" is
    equivalent to "for a in answer.rrset", "answer[i]" is equivalent
    to "answer.rrset[i]", and "answer[i:j]" is equivalent to
    "answer.rrset[i:j]".

    Note that CNAMEs or DNAMEs in the response may mean that answer
    node's name might not be the query name.

    @ivar qname: The query name
    @type qname: dns.name.Name object
    @ivar rdtype: The query type
    @type rdtype: int
    @ivar rdclass: The query class
    @type rdclass: int
    @ivar response: The response message
    @type response: dns.message.Message object
    @ivar rrset: The answer
    @type rrset: dns.rrset.RRset object
    @ivar expiration: The time when the answer expires
    @type expiration: float (seconds since the epoch)
    @ivar canonical_name: The canonical name of the query name
    @type canonical_name: dns.name.Name object
    """
    def __init__(self, qname, rdtype, rdclass, response,
                 raise_on_no_answer=True):
        self.qname = qname
        self.rdtype = rdtype
        self.rdclass = rdclass
        self.response = response
        min_ttl = -1
        rrset = None
        for count in xrange(0, 15):
            try:
                rrset = response.find_rrset(response.answer, qname,
                                            rdclass, rdtype)
                if min_ttl == -1 or rrset.ttl < min_ttl:
                    min_ttl = rrset.ttl
                break
            except KeyError:
                if rdtype != dns.rdatatype.CNAME:
                    try:
                        crrset = response.find_rrset(response.answer,
                                                     qname,
                                                     rdclass,
                                                     dns.rdatatype.CNAME)
                        if min_ttl == -1 or crrset.ttl < min_ttl:
                            min_ttl = crrset.ttl
                        for rd in crrset:
                            qname = rd.target
                            break
                        continue
                    except KeyError:
                        if raise_on_no_answer:
                            raise NoAnswer
                if raise_on_no_answer:
                    raise NoAnswer
        if rrset is None and raise_on_no_answer:
            raise NoAnswer
        self.canonical_name = qname
        self.rrset = rrset
        if rrset is None:
            while 1:
                # Look for a SOA RR whose owner name is a superdomain
                # of qname.
                try:
                    srrset = response.find_rrset(response.authority, qname,
                                                rdclass, dns.rdatatype.SOA)
                    if min_ttl == -1 or srrset.ttl < min_ttl:
                        min_ttl = srrset.ttl
                    if srrset[0].minimum < min_ttl:
                        min_ttl = srrset[0].minimum
                    break
                except KeyError:
                    try:
                        qname = qname.parent()
                    except dns.name.NoParent:
                        break
        self.expiration = time.time() + min_ttl

    def __getattr__(self, attr):
        if attr == 'name':
            return self.rrset.name
        elif attr == 'ttl':
            return self.rrset.ttl
        elif attr == 'covers':
            return self.rrset.covers
        elif attr == 'rdclass':
            return self.rrset.rdclass
        elif attr == 'rdtype':
            return self.rrset.rdtype
        else:
            raise AttributeError(attr)

    def __len__(self):
        return len(self.rrset)

    def __iter__(self):
        return iter(self.rrset)

    def __getitem__(self, i):
        return self.rrset[i]

    def __delitem__(self, i):
        del self.rrset[i]

    def __getslice__(self, i, j):
        return self.rrset[i:j]

    def __delslice__(self, i, j):
        del self.rrset[i:j]

class Cache(object):
    """Simple DNS answer cache.

    @ivar data: A dictionary of cached data
    @type data: dict
    @ivar cleaning_interval: The number of seconds between cleanings.  The
    default is 300 (5 minutes).
    @type cleaning_interval: float
    @ivar next_cleaning: The time the cache should next be cleaned (in seconds
    since the epoch.)
    @type next_cleaning: float
    """

    def __init__(self, cleaning_interval=300.0):
        """Initialize a DNS cache.

        @param cleaning_interval: the number of seconds between periodic
        cleanings.  The default is 300.0
        @type cleaning_interval: float.
        """

        self.data = {}
        self.cleaning_interval = cleaning_interval
        self.next_cleaning = time.time() + self.cleaning_interval
        self.lock = _threading.Lock()

    def _maybe_clean(self):
        """Clean the cache if it's time to do so."""

        now = time.time()
        if self.next_cleaning <= now:
            keys_to_delete = []
            for (k, v) in self.data.iteritems():
                if v.expiration <= now:
                    keys_to_delete.append(k)
            for k in keys_to_delete:
                del self.data[k]
            now = time.time()
            self.next_cleaning = now + self.cleaning_interval

    def get(self, key):
        """Get the answer associated with I{key}.  Returns None if
        no answer is cached for the key.
        @param key: the key
        @type key: (dns.name.Name, int, int) tuple whose values are the
        query name, rdtype, and rdclass.
        @rtype: dns.resolver.Answer object or None
        """

        try:
            self.lock.acquire()
            self._maybe_clean()
            v = self.data.get(key)
            if v is None or v.expiration <= time.time():
                return None
            return v
        finally:
            self.lock.release()

    def put(self, key, value):
        """Associate key and value in the cache.
        @param key: the key
        @type key: (dns.name.Name, int, int) tuple whose values are the
        query name, rdtype, and rdclass.
        @param value: The answer being cached
        @type value: dns.resolver.Answer object
        """

        try:
            self.lock.acquire()
            self._maybe_clean()
            self.data[key] = value
        finally:
            self.lock.release()

    def flush(self, key=None):
        """Flush the cache.

        If I{key} is specified, only that item is flushed.  Otherwise
        the entire cache is flushed.

        @param key: the key to flush
        @type key: (dns.name.Name, int, int) tuple or None
        """

        try:
            self.lock.acquire()
            if not key is None:
                if self.data.has_key(key):
                    del self.data[key]
            else:
                self.data = {}
                self.next_cleaning = time.time() + self.cleaning_interval
        finally:
            self.lock.release()

class LRUCacheNode(object):
    """LRUCache node.
    """
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.prev = self
        self.next = self

    def link_before(self, node):
        self.prev = node.prev
        self.next = node
        node.prev.next = self
        node.prev = self

    def link_after(self, node):
        self.prev = node
        self.next = node.next
        node.next.prev = self
        node.next = self

    def unlink(self):
        self.next.prev = self.prev
        self.prev.next = self.next

class LRUCache(object):
    """Bounded least-recently-used DNS answer cache.

    This cache is better than the simple cache (above) if you're
    running a web crawler or other process that does a lot of
    resolutions.  The LRUCache has a maximum number of nodes, and when
    it is full, the least-recently used node is removed to make space
    for a new one.

    @ivar data: A dictionary of cached data
    @type data: dict
    @ivar sentinel: sentinel node for circular doubly linked list of nodes
    @type sentinel: LRUCacheNode object
    @ivar max_size: The maximum number of nodes
    @type max_size: int
    """

    def __init__(self, max_size=100000):
        """Initialize a DNS cache.

        @param max_size: The maximum number of nodes to cache; the default is 100000.  Must be > 1.
        @type max_size: int
        """
        self.data = {}
        self.set_max_size(max_size)
        self.sentinel = LRUCacheNode(None, None)
        self.lock = _threading.Lock()

    def set_max_size(self, max_size):
        if max_size < 1:
            max_size = 1
        self.max_size = max_size

    def get(self, key):
        """Get the answer associated with I{key}.  Returns None if
        no answer is cached for the key.
        @param key: the key
        @type key: (dns.name.Name, int, int) tuple whose values are the
        query name, rdtype, and rdclass.
        @rtype: dns.resolver.Answer object or None
        """
        try:
            self.lock.acquire()
            node = self.data.get(key)
            if node is None:
                return None
            # Unlink because we're either going to move the node to the front
            # of the LRU list or we're going to free it.
            node.unlink()
            if node.value.expiration <= time.time():
                del self.data[node.key]
                return None
            node.link_after(self.sentinel)
            return node.value
        finally:
            self.lock.release()

    def put(self, key, value):
        """Associate key and value in the cache.
        @param key: the key
        @type key: (dns.name.Name, int, int) tuple whose values are the
        query name, rdtype, and rdclass.
        @param value: The answer being cached
        @type value: dns.resolver.Answer object
        """
        try:
            self.lock.acquire()
            node = self.data.get(key)
            if not node is None:
                node.unlink()
                del self.data[node.key]
            while len(self.data) >= self.max_size:
                node = self.sentinel.prev
                node.unlink()
                del self.data[node.key]
            node = LRUCacheNode(key, value)
            node.link_after(self.sentinel)
            self.data[key] = node
        finally:
            self.lock.release()

    def flush(self, key=None):
        """Flush the cache.

        If I{key} is specified, only that item is flushed.  Otherwise
        the entire cache is flushed.

        @param key: the key to flush
        @type key: (dns.name.Name, int, int) tuple or None
        """
        try:
            self.lock.acquire()
            if not key is None:
                node = self.data.get(key)
                if not node is None:
                    node.unlink()
                    del self.data[node.key]
            else:
                node = self.sentinel.next
                while node != self.sentinel:
                    next = node.next
                    node.prev = None
                    node.next = None
                    node = next
                self.data = {}
        finally:
            self.lock.release()

class Resolver(object):
    """DNS stub resolver

    @ivar domain: The domain of this host
    @type domain: dns.name.Name object
    @ivar nameservers: A list of nameservers to query.  Each nameserver is
    a string which contains the IP address of a nameserver.
    @type nameservers: list of strings
    @ivar search: The search list.  If the query name is a relative name,
    the resolver will construct an absolute query name by appending the search
    names one by one to the query name.
    @type search: list of dns.name.Name objects
    @ivar port: The port to which to send queries.  The default is 53.
    @type port: int
    @ivar timeout: The number of seconds to wait for a response from a
    server, before timing out.
    @type timeout: float
    @ivar lifetime: The total number of seconds to spend trying to get an
    answer to the question.  If the lifetime expires, a Timeout exception
    will occur.
    @type lifetime: float
    @ivar keyring: The TSIG keyring to use.  The default is None.
    @type keyring: dict
    @ivar keyname: The TSIG keyname to use.  The default is None.
    @type keyname: dns.name.Name object
    @ivar keyalgorithm: The TSIG key algorithm to use.  The default is
    dns.tsig.default_algorithm.
    @type keyalgorithm: string
    @ivar edns: The EDNS level to use.  The default is -1, no Edns.
    @type edns: int
    @ivar ednsflags: The EDNS flags
    @type ednsflags: int
    @ivar payload: The EDNS payload size.  The default is 0.
    @type payload: int
    @ivar flags: The message flags to use.  The default is None (i.e. not overwritten)
    @type flags: int
    @ivar cache: The cache to use.  The default is None.
    @type cache: dns.resolver.Cache object
    @ivar retry_servfail: should we retry a nameserver if it says SERVFAIL?
    The default is 'false'.
    @type retry_servfail: bool
    """
    def __init__(self, filename='/etc/resolv.conf', configure=True):
        """Initialize a resolver instance.

        @param filename: The filename of a configuration file in
        standard /etc/resolv.conf format.  This parameter is meaningful
        only when I{configure} is true and the platform is POSIX.
        @type filename: string or file object
        @param configure: If True (the default), the resolver instance
        is configured in the normal fashion for the operating system
        the resolver is running on.  (I.e. a /etc/resolv.conf file on
        POSIX systems and from the registry on Windows systems.)
        @type configure: bool"""

        self.reset()
        if configure:
            if sys.platform == 'win32':
                self.read_registry()
            elif filename:
                self.read_resolv_conf(filename)

    def reset(self):
        """Reset all resolver configuration to the defaults."""
        self.domain = \
            dns.name.Name(dns.name.from_text(socket.gethostname())[1:])
        if len(self.domain) == 0:
            self.domain = dns.name.root
        self.nameservers = []
        self.search = []
        self.port = 53
        self.timeout = 2.0
        self.lifetime = 30.0
        self.keyring = None
        self.keyname = None
        self.keyalgorithm = dns.tsig.default_algorithm
        self.edns = -1
        self.ednsflags = 0
        self.payload = 0
        self.cache = None
        self.flags = None
        self.retry_servfail = False

    def read_resolv_conf(self, f):
        """Process f as a file in the /etc/resolv.conf format.  If f is
        a string, it is used as the name of the file to open; otherwise it
        is treated as the file itself."""
        if isinstance(f, str) or isinstance(f, unicode):
            try:
                f = open(f, 'r')
            except IOError:
                # /etc/resolv.conf doesn't exist, can't be read, etc.
                # We'll just use the default resolver configuration.
                self.nameservers = ['127.0.0.1']
                return
            want_close = True
        else:
            want_close = False
        try:
            for l in f:
                if len(l) == 0 or l[0] == '#' or l[0] == ';':
                    continue
                tokens = l.split()
                if len(tokens) == 0:
                    continue
                if tokens[0] == 'nameserver':
                    self.nameservers.append(tokens[1])
                elif tokens[0] == 'domain':
                    self.domain = dns.name.from_text(tokens[1])
                elif tokens[0] == 'search':
                    for suffix in tokens[1:]:
                        self.search.append(dns.name.from_text(suffix))
        finally:
            if want_close:
                f.close()
        if len(self.nameservers) == 0:
            self.nameservers.append('127.0.0.1')

    def _determine_split_char(self, entry):
        #
        # The windows registry irritatingly changes the list element
        # delimiter in between ' ' and ',' (and vice-versa) in various
        # versions of windows.
        #
        if entry.find(' ') >= 0:
            split_char = ' '
        elif entry.find(',') >= 0:
            split_char = ','
        else:
            # probably a singleton; treat as a space-separated list.
            split_char = ' '
        return split_char

    def _config_win32_nameservers(self, nameservers):
        """Configure a NameServer registry entry."""
        # we call str() on nameservers to convert it from unicode to ascii
        nameservers = str(nameservers)
        split_char = self._determine_split_char(nameservers)
        ns_list = nameservers.split(split_char)
        for ns in ns_list:
            if not ns in self.nameservers:
                self.nameservers.append(ns)

    def _config_win32_domain(self, domain):
        """Configure a Domain registry entry."""
        # we call str() on domain to convert it from unicode to ascii
        self.domain = dns.name.from_text(str(domain))

    def _config_win32_search(self, search):
        """Configure a Search registry entry."""
        # we call str() on search to convert it from unicode to ascii
        search = str(search)
        split_char = self._determine_split_char(search)
        search_list = search.split(split_char)
        for s in search_list:
            if not s in self.search:
                self.search.append(dns.name.from_text(s))

    def _config_win32_fromkey(self, key):
        """Extract DNS info from a registry key."""
        try:
            servers, rtype = _winreg.QueryValueEx(key, 'NameServer')
        except WindowsError:
            servers = None
        if servers:
            self._config_win32_nameservers(servers)
            try:
                dom, rtype = _winreg.QueryValueEx(key, 'Domain')
                if dom:
                    self._config_win32_domain(dom)
            except WindowsError:
                pass
        else:
            try:
                servers, rtype = _winreg.QueryValueEx(key, 'DhcpNameServer')
            except WindowsError:
                servers = None
            if servers:
                self._config_win32_nameservers(servers)
                try:
                    dom, rtype = _winreg.QueryValueEx(key, 'DhcpDomain')
                    if dom:
                        self._config_win32_domain(dom)
                except WindowsError:
                    pass
        try:
            search, rtype = _winreg.QueryValueEx(key, 'SearchList')
        except WindowsError:
            search = None
        if search:
            self._config_win32_search(search)

    def read_registry(self):
        """Extract resolver configuration from the Windows registry."""
        lm = _winreg.ConnectRegistry(None, _winreg.HKEY_LOCAL_MACHINE)
        want_scan = False
        try:
            try:
                # XP, 2000
                tcp_params = _winreg.OpenKey(lm,
                                             r'SYSTEM\CurrentControlSet'
                                             r'\Services\Tcpip\Parameters')
                want_scan = True
            except EnvironmentError:
                # ME
                tcp_params = _winreg.OpenKey(lm,
                                             r'SYSTEM\CurrentControlSet'
                                             r'\Services\VxD\MSTCP')
            try:
                self._config_win32_fromkey(tcp_params)
            finally:
                tcp_params.Close()
            if want_scan:
                interfaces = _winreg.OpenKey(lm,
                                             r'SYSTEM\CurrentControlSet'
                                             r'\Services\Tcpip\Parameters'
                                             r'\Interfaces')
                try:
                    i = 0
                    while True:
                        try:
                            guid = _winreg.EnumKey(interfaces, i)
                            i += 1
                            key = _winreg.OpenKey(interfaces, guid)
                            if not self._win32_is_nic_enabled(lm, guid, key):
                                continue
                            try:
                                self._config_win32_fromkey(key)
                            finally:
                                key.Close()
                        except EnvironmentError:
                            break
                finally:
                    interfaces.Close()
        finally:
            lm.Close()

    def _win32_is_nic_enabled(self, lm, guid, interface_key):
         # Look in the Windows Registry to determine whether the network
         # interface corresponding to the given guid is enabled.
         #
         # (Code contributed by Paul Marks, thanks!)
         #
         try:
             # This hard-coded location seems to be consistent, at least
             # from Windows 2000 through Vista.
             connection_key = _winreg.OpenKey(
                 lm,
                 r'SYSTEM\CurrentControlSet\Control\Network'
                 r'\{4D36E972-E325-11CE-BFC1-08002BE10318}'
                 r'\%s\Connection' % guid)

             try:
                 # The PnpInstanceID points to a key inside Enum
                 (pnp_id, ttype) = _winreg.QueryValueEx(
                     connection_key, 'PnpInstanceID')

                 if ttype != _winreg.REG_SZ:
                     raise ValueError

                 device_key = _winreg.OpenKey(
                     lm, r'SYSTEM\CurrentControlSet\Enum\%s' % pnp_id)

                 try:
                     # Get ConfigFlags for this device
                     (flags, ttype) = _winreg.QueryValueEx(
                         device_key, 'ConfigFlags')

                     if ttype != _winreg.REG_DWORD:
                         raise ValueError

                     # Based on experimentation, bit 0x1 indicates that the
                     # device is disabled.
                     return not (flags & 0x1)

                 finally:
                     device_key.Close()
             finally:
                 connection_key.Close()
         except (EnvironmentError, ValueError):
             # Pre-vista, enabled interfaces seem to have a non-empty
             # NTEContextList; this was how dnspython detected enabled
             # nics before the code above was contributed.  We've retained
             # the old method since we don't know if the code above works
             # on Windows 95/98/ME.
             try:
                 (nte, ttype) = _winreg.QueryValueEx(interface_key,
                                                     'NTEContextList')
                 return nte is not None
             except WindowsError:
                 return False

    def _compute_timeout(self, start):
        now = time.time()
        if now < start:
            if start - now > 1:
                # Time going backwards is bad.  Just give up.
                raise Timeout
            else:
                # Time went backwards, but only a little.  This can
                # happen, e.g. under vmware with older linux kernels.
                # Pretend it didn't happen.
                now = start
        duration = now - start
        if duration >= self.lifetime:
            raise Timeout
        return min(self.lifetime - duration, self.timeout)

    def query(self, qname, rdtype=dns.rdatatype.A, rdclass=dns.rdataclass.IN,
              tcp=False, source=None, raise_on_no_answer=True, source_port=0):
        """Query nameservers to find the answer to the question.

        The I{qname}, I{rdtype}, and I{rdclass} parameters may be objects
        of the appropriate type, or strings that can be converted into objects
        of the appropriate type.  E.g. For I{rdtype} the integer 2 and the
        the string 'NS' both mean to query for records with DNS rdata type NS.

        @param qname: the query name
        @type qname: dns.name.Name object or string
        @param rdtype: the query type
        @type rdtype: int or string
        @param rdclass: the query class
        @type rdclass: int or string
        @param tcp: use TCP to make the query (default is False).
        @type tcp: bool
        @param source: bind to this IP address (defaults to machine default IP).
        @type source: IP address in dotted quad notation
        @param raise_on_no_answer: raise NoAnswer if there's no answer
        (defaults is True).
        @type raise_on_no_answer: bool
        @param source_port: The port from which to send the message.
        The default is 0.
        @type source_port: int
        @rtype: dns.resolver.Answer instance
        @raises Timeout: no answers could be found in the specified lifetime
        @raises NXDOMAIN: the query name does not exist
        @raises YXDOMAIN: the query name is too long after DNAME substitution
        @raises NoAnswer: the response did not contain an answer and
        raise_on_no_answer is True.
        @raises NoNameservers: no non-broken nameservers are available to
        answer the question."""

        if isinstance(qname, (str, unicode)):
            qname = dns.name.from_text(qname, None)
        if isinstance(rdtype, (str, unicode)):
            rdtype = dns.rdatatype.from_text(rdtype)
        if dns.rdatatype.is_metatype(rdtype):
            raise NoMetaqueries
        if isinstance(rdclass, (str, unicode)):
            rdclass = dns.rdataclass.from_text(rdclass)
        if dns.rdataclass.is_metaclass(rdclass):
            raise NoMetaqueries
        qnames_to_try = []
        if qname.is_absolute():
            qnames_to_try.append(qname)
        else:
            if len(qname) > 1:
                qnames_to_try.append(qname.concatenate(dns.name.root))
            if self.search:
                for suffix in self.search:
                    qnames_to_try.append(qname.concatenate(suffix))
            else:
                qnames_to_try.append(qname.concatenate(self.domain))
        all_nxdomain = True
        start = time.time()
        for qname in qnames_to_try:
            if self.cache:
                answer = self.cache.get((qname, rdtype, rdclass))
                if not answer is None:
                    if answer.rrset is None and raise_on_no_answer:
                        raise NoAnswer
                    else:
                        return answer
            request = dns.message.make_query(qname, rdtype, rdclass)
            if not self.keyname is None:
                request.use_tsig(self.keyring, self.keyname,
                                 algorithm=self.keyalgorithm)
            request.use_edns(self.edns, self.ednsflags, self.payload)
            if self.flags is not None:
                request.flags = self.flags
            response = None
            #
            # make a copy of the servers list so we can alter it later.
            #
            nameservers = self.nameservers[:]
            backoff = 0.10
            while response is None:
                if len(nameservers) == 0:
                    raise NoNameservers
                for nameserver in nameservers[:]:
                    timeout = self._compute_timeout(start)
                    try:
                        if tcp:
                            response = dns.query.tcp(request, nameserver,
                                                     timeout, self.port,
                                                     source=source,
                                                     source_port=source_port)
                        else:
                            response = dns.query.udp(request, nameserver,
                                                     timeout, self.port,
                                                     source=source,
                                                     source_port=source_port)
                            if response.flags & dns.flags.TC:
                                # Response truncated; retry with TCP.
                                timeout = self._compute_timeout(start)
                                response = dns.query.tcp(request, nameserver,
                                                       timeout, self.port,
                                                       source=source,
                                                       source_port=source_port)
                    except (socket.error, dns.exception.Timeout):
                        #
                        # Communication failure or timeout.  Go to the
                        # next server
                        #
                        response = None
                        continue
                    except dns.query.UnexpectedSource:
                        #
                        # Who knows?  Keep going.
                        #
                        response = None
                        continue
                    except dns.exception.FormError:
                        #
                        # We don't understand what this server is
                        # saying.  Take it out of the mix and
                        # continue.
                        #
                        nameservers.remove(nameserver)
                        response = None
                        continue
                    except EOFError:
                        #
                        # We're using TCP and they hung up on us.
                        # Probably they don't support TCP (though
                        # they're supposed to!).  Take it out of the
                        # mix and continue.
                        #
                        nameservers.remove(nameserver)
                        response = None
                        continue
                    rcode = response.rcode()
                    if rcode == dns.rcode.YXDOMAIN:
                        raise YXDOMAIN
                    if rcode == dns.rcode.NOERROR or \
                           rcode == dns.rcode.NXDOMAIN:
                        break
                    #
                    # We got a response, but we're not happy with the
                    # rcode in it.  Remove the server from the mix if
                    # the rcode isn't SERVFAIL.
                    #
                    if rcode != dns.rcode.SERVFAIL or not self.retry_servfail:
                        nameservers.remove(nameserver)
                    response = None
                if not response is None:
                    break
                #
                # All nameservers failed!
                #
                if len(nameservers) > 0:
                    #
                    # But we still have servers to try.  Sleep a bit
                    # so we don't pound them!
                    #
                    timeout = self._compute_timeout(start)
                    sleep_time = min(timeout, backoff)
                    backoff *= 2
                    time.sleep(sleep_time)
            if response.rcode() == dns.rcode.NXDOMAIN:
                continue
            all_nxdomain = False
            break
        if all_nxdomain:
            raise NXDOMAIN
        answer = Answer(qname, rdtype, rdclass, response,
                        raise_on_no_answer)
        if self.cache:
            self.cache.put((qname, rdtype, rdclass), answer)
        return answer

    def use_tsig(self, keyring, keyname=None,
                 algorithm=dns.tsig.default_algorithm):
        """Add a TSIG signature to the query.

        @param keyring: The TSIG keyring to use; defaults to None.
        @type keyring: dict
        @param keyname: The name of the TSIG key to use; defaults to None.
        The key must be defined in the keyring.  If a keyring is specified
        but a keyname is not, then the key used will be the first key in the
        keyring.  Note that the order of keys in a dictionary is not defined,
        so applications should supply a keyname when a keyring is used, unless
        they know the keyring contains only one key.
        @param algorithm: The TSIG key algorithm to use.  The default
        is dns.tsig.default_algorithm.
        @type algorithm: string"""
        self.keyring = keyring
        if keyname is None:
            self.keyname = self.keyring.keys()[0]
        else:
            self.keyname = keyname
        self.keyalgorithm = algorithm

    def use_edns(self, edns, ednsflags, payload):
        """Configure Edns.

        @param edns: The EDNS level to use.  The default is -1, no Edns.
        @type edns: int
        @param ednsflags: The EDNS flags
        @type ednsflags: int
        @param payload: The EDNS payload size.  The default is 0.
        @type payload: int"""

        if edns is None:
            edns = -1
        self.edns = edns
        self.ednsflags = ednsflags
        self.payload = payload

    def set_flags(self, flags):
        """Overrides the default flags with your own

        @param flags: The flags to overwrite the default with
        @type flags: int"""
        self.flags = flags

default_resolver = None

def get_default_resolver():
    """Get the default resolver, initializing it if necessary."""
    global default_resolver
    if default_resolver is None:
        default_resolver = Resolver()
    return default_resolver

def query(qname, rdtype=dns.rdatatype.A, rdclass=dns.rdataclass.IN,
          tcp=False, source=None, raise_on_no_answer=True,
          source_port=0):
    """Query nameservers to find the answer to the question.

    This is a convenience function that uses the default resolver
    object to make the query.
    @see: L{dns.resolver.Resolver.query} for more information on the
    parameters."""
    return get_default_resolver().query(qname, rdtype, rdclass, tcp, source,
                                        raise_on_no_answer, source_port)

def zone_for_name(name, rdclass=dns.rdataclass.IN, tcp=False, resolver=None):
    """Find the name of the zone which contains the specified name.

    @param name: the query name
    @type name: absolute dns.name.Name object or string
    @param rdclass: The query class
    @type rdclass: int
    @param tcp: use TCP to make the query (default is False).
    @type tcp: bool
    @param resolver: the resolver to use
    @type resolver: dns.resolver.Resolver object or None
    @rtype: dns.name.Name"""

    if isinstance(name, (str, unicode)):
        name = dns.name.from_text(name, dns.name.root)
    if resolver is None:
        resolver = get_default_resolver()
    if not name.is_absolute():
        raise NotAbsolute(name)
    while 1:
        try:
            answer = resolver.query(name, dns.rdatatype.SOA, rdclass, tcp)
            if answer.rrset.name == name:
                return name
            # otherwise we were CNAMEd or DNAMEd and need to look higher
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            pass
        try:
            name = name.parent()
        except dns.name.NoParent:
            raise NoRootSOA

#
# Support for overriding the system resolver for all python code in the
# running process.
#

_protocols_for_socktype = {
    socket.SOCK_DGRAM : [socket.SOL_UDP],
    socket.SOCK_STREAM : [socket.SOL_TCP],
    }

_resolver = None
_original_getaddrinfo = socket.getaddrinfo
_original_getnameinfo = socket.getnameinfo
_original_getfqdn = socket.getfqdn
_original_gethostbyname = socket.gethostbyname
_original_gethostbyname_ex = socket.gethostbyname_ex
_original_gethostbyaddr = socket.gethostbyaddr

def _getaddrinfo(host=None, service=None, family=socket.AF_UNSPEC, socktype=0,
                 proto=0, flags=0):
    if flags & (socket.AI_ADDRCONFIG|socket.AI_V4MAPPED) != 0:
        raise NotImplementedError
    if host is None and service is None:
        raise socket.gaierror(socket.EAI_NONAME)
    v6addrs = []
    v4addrs = []
    canonical_name = None
    try:
        # Is host None or a V6 address literal?
        if host is None:
            canonical_name = 'localhost'
            if flags & socket.AI_PASSIVE != 0:
                v6addrs.append('::')
                v4addrs.append('0.0.0.0')
            else:
                v6addrs.append('::1')
                v4addrs.append('127.0.0.1')
        else:
            parts = host.split('%')
            if len(parts) == 2:
                ahost = parts[0]
            else:
                ahost = host
            addr = dns.ipv6.inet_aton(ahost)
            v6addrs.append(host)
            canonical_name = host
    except:
        try:
            # Is it a V4 address literal?
            addr = dns.ipv4.inet_aton(host)
            v4addrs.append(host)
            canonical_name = host
        except:
            if flags & socket.AI_NUMERICHOST == 0:
                try:
                    qname = None
                    if family == socket.AF_INET6 or family == socket.AF_UNSPEC:
                        v6 = _resolver.query(host, dns.rdatatype.AAAA,
                                             raise_on_no_answer=False)
                        # Note that setting host ensures we query the same name
                        # for A as we did for AAAA.
                        host = v6.qname
                        canonical_name = v6.canonical_name.to_text(True)
                        if v6.rrset is not None:
                            for rdata in v6.rrset:
                                v6addrs.append(rdata.address)
                    if family == socket.AF_INET or family == socket.AF_UNSPEC:
                        v4 = _resolver.query(host, dns.rdatatype.A,
                                             raise_on_no_answer=False)
                        host = v4.qname
                        canonical_name = v4.canonical_name.to_text(True)
                        if v4.rrset is not None:
                            for rdata in v4.rrset:
                                v4addrs.append(rdata.address)
                except dns.resolver.NXDOMAIN:
                    raise socket.gaierror(socket.EAI_NONAME)
                except:
                    raise socket.gaierror(socket.EAI_SYSTEM)
    port = None
    try:
        # Is it a port literal?
        if service is None:
            port = 0
        else:
            port = int(service)
    except:
        if flags & socket.AI_NUMERICSERV == 0:
            try:
                port = socket.getservbyname(service)
            except:
                pass
    if port is None:
        raise socket.gaierror(socket.EAI_NONAME)
    tuples = []
    if socktype == 0:
        socktypes = [socket.SOCK_DGRAM, socket.SOCK_STREAM]
    else:
        socktypes = [socktype]
    if flags & socket.AI_CANONNAME != 0:
        cname = canonical_name
    else:
        cname = ''
    if family == socket.AF_INET6 or family == socket.AF_UNSPEC:
        for addr in v6addrs:
            for socktype in socktypes:
                for proto in _protocols_for_socktype[socktype]:
                    tuples.append((socket.AF_INET6, socktype, proto,
                                   cname, (addr, port, 0, 0)))
    if family == socket.AF_INET or family == socket.AF_UNSPEC:
        for addr in v4addrs:
            for socktype in socktypes:
                for proto in _protocols_for_socktype[socktype]:
                    tuples.append((socket.AF_INET, socktype, proto,
                                   cname, (addr, port)))
    if len(tuples) == 0:
        raise socket.gaierror(socket.EAI_NONAME)
    return tuples

def _getnameinfo(sockaddr, flags=0):
    host = sockaddr[0]
    port = sockaddr[1]
    if len(sockaddr) == 4:
        scope = sockaddr[3]
        family = socket.AF_INET6
    else:
        scope = None
        family = socket.AF_INET
    tuples = _getaddrinfo(host, port, family, socket.SOCK_STREAM,
                          socket.SOL_TCP, 0)
    if len(tuples) > 1:
        raise socket.error('sockaddr resolved to multiple addresses')
    addr = tuples[0][4][0]
    if flags & socket.NI_DGRAM:
        pname = 'udp'
    else:
        pname = 'tcp'
    qname = dns.reversename.from_address(addr)
    if flags & socket.NI_NUMERICHOST == 0:
        try:
            answer = _resolver.query(qname, 'PTR')
            hostname = answer.rrset[0].target.to_text(True)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            if flags & socket.NI_NAMEREQD:
                raise socket.gaierror(socket.EAI_NONAME)
            hostname = addr
            if scope is not None:
                hostname += '%' + str(scope)
    else:
        hostname = addr
        if scope is not None:
            hostname += '%' + str(scope)
    if flags & socket.NI_NUMERICSERV:
        service = str(port)
    else:
        service = socket.getservbyport(port, pname)
    return (hostname, service)

def _getfqdn(name=None):
    if name is None:
        name = socket.gethostname()
    return _getnameinfo(_getaddrinfo(name, 80)[0][4])[0]

def _gethostbyname(name):
    return _gethostbyname_ex(name)[2][0]

def _gethostbyname_ex(name):
    aliases = []
    addresses = []
    tuples = _getaddrinfo(name, 0, socket.AF_INET, socket.SOCK_STREAM,
                         socket.SOL_TCP, socket.AI_CANONNAME)
    canonical = tuples[0][3]
    for item in tuples:
        addresses.append(item[4][0])
    # XXX we just ignore aliases
    return (canonical, aliases, addresses)

def _gethostbyaddr(ip):
    try:
        addr = dns.ipv6.inet_aton(ip)
        sockaddr = (ip, 80, 0, 0)
        family = socket.AF_INET6
    except:
        sockaddr = (ip, 80)
        family = socket.AF_INET
    (name, port) = _getnameinfo(sockaddr, socket.NI_NAMEREQD)
    aliases = []
    addresses = []
    tuples = _getaddrinfo(name, 0, family, socket.SOCK_STREAM, socket.SOL_TCP,
                          socket.AI_CANONNAME)
    canonical = tuples[0][3]
    for item in tuples:
        addresses.append(item[4][0])
    # XXX we just ignore aliases
    return (canonical, aliases, addresses)

def override_system_resolver(resolver=None):
    """Override the system resolver routines in the socket module with
    versions which use dnspython's resolver.

    This can be useful in testing situations where you want to control
    the resolution behavior of python code without having to change
    the system's resolver settings (e.g. /etc/resolv.conf).

    The resolver to use may be specified; if it's not, the default
    resolver will be used.

    @param resolver: the resolver to use
    @type resolver: dns.resolver.Resolver object or None
    """
    if resolver is None:
        resolver = get_default_resolver()
    global _resolver
    _resolver = resolver
    socket.getaddrinfo = _getaddrinfo
    socket.getnameinfo = _getnameinfo
    socket.getfqdn = _getfqdn
    socket.gethostbyname = _gethostbyname
    socket.gethostbyname_ex = _gethostbyname_ex
    socket.gethostbyaddr = _gethostbyaddr

def restore_system_resolver():
    """Undo the effects of override_system_resolver().
    """
    global _resolver
    _resolver = None
    socket.getaddrinfo = _original_getaddrinfo
    socket.getnameinfo = _original_getnameinfo
    socket.getfqdn = _original_getfqdn
    socket.gethostbyname = _original_gethostbyname
    socket.gethostbyname_ex = _original_gethostbyname_ex
    socket.gethostbyaddr = _original_gethostbyaddr

########NEW FILE########
__FILENAME__ = reversename
# Copyright (C) 2006, 2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS Reverse Map Names.

@var ipv4_reverse_domain: The DNS IPv4 reverse-map domain, in-addr.arpa.
@type ipv4_reverse_domain: dns.name.Name object
@var ipv6_reverse_domain: The DNS IPv6 reverse-map domain, ip6.arpa.
@type ipv6_reverse_domain: dns.name.Name object
"""

import dns.name
import dns.ipv6
import dns.ipv4

ipv4_reverse_domain = dns.name.from_text('in-addr.arpa.')
ipv6_reverse_domain = dns.name.from_text('ip6.arpa.')

def from_address(text):
    """Convert an IPv4 or IPv6 address in textual form into a Name object whose
    value is the reverse-map domain name of the address.
    @param text: an IPv4 or IPv6 address in textual form (e.g. '127.0.0.1',
    '::1')
    @type text: str
    @rtype: dns.name.Name object
    """
    try:
        parts = list(dns.ipv6.inet_aton(text).encode('hex_codec'))
        origin = ipv6_reverse_domain
    except:
        parts = ['%d' % ord(byte) for byte in dns.ipv4.inet_aton(text)]
        origin = ipv4_reverse_domain
    parts.reverse()
    return dns.name.from_text('.'.join(parts), origin=origin)

def to_address(name):
    """Convert a reverse map domain name into textual address form.
    @param name: an IPv4 or IPv6 address in reverse-map form.
    @type name: dns.name.Name object
    @rtype: str
    """
    if name.is_subdomain(ipv4_reverse_domain):
        name = name.relativize(ipv4_reverse_domain)
        labels = list(name.labels)
        labels.reverse()
        text = '.'.join(labels)
        # run through inet_aton() to check syntax and make pretty.
        return dns.ipv4.inet_ntoa(dns.ipv4.inet_aton(text))
    elif name.is_subdomain(ipv6_reverse_domain):
        name = name.relativize(ipv6_reverse_domain)
        labels = list(name.labels)
        labels.reverse()
        parts = []
        i = 0
        l = len(labels)
        while i < l:
            parts.append(''.join(labels[i:i+4]))
            i += 4
        text = ':'.join(parts)
        # run through inet_aton() to check syntax and make pretty.
        return dns.ipv6.inet_ntoa(dns.ipv6.inet_aton(text))
    else:
        raise dns.exception.SyntaxError('unknown reverse-map address family')

########NEW FILE########
__FILENAME__ = rrset
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS RRsets (an RRset is a named rdataset)"""

import dns.name
import dns.rdataset
import dns.rdataclass
import dns.renderer

class RRset(dns.rdataset.Rdataset):
    """A DNS RRset (named rdataset).

    RRset inherits from Rdataset, and RRsets can be treated as
    Rdatasets in most cases.  There are, however, a few notable
    exceptions.  RRsets have different to_wire() and to_text() method
    arguments, reflecting the fact that RRsets always have an owner
    name.
    """

    __slots__ = ['name', 'deleting']

    def __init__(self, name, rdclass, rdtype, covers=dns.rdatatype.NONE,
                 deleting=None):
        """Create a new RRset."""

        super(RRset, self).__init__(rdclass, rdtype, covers)
        self.name = name
        self.deleting = deleting

    def _clone(self):
        obj = super(RRset, self)._clone()
        obj.name = self.name
        obj.deleting = self.deleting
        return obj

    def __repr__(self):
        if self.covers == 0:
            ctext = ''
        else:
            ctext = '(' + dns.rdatatype.to_text(self.covers) + ')'
        if not self.deleting is None:
            dtext = ' delete=' + dns.rdataclass.to_text(self.deleting)
        else:
            dtext = ''
        return '<DNS ' + str(self.name) + ' ' + \
               dns.rdataclass.to_text(self.rdclass) + ' ' + \
               dns.rdatatype.to_text(self.rdtype) + ctext + dtext + ' RRset>'

    def __str__(self):
        return self.to_text()

    def __eq__(self, other):
        """Two RRsets are equal if they have the same name and the same
        rdataset

        @rtype: bool"""
        if not isinstance(other, RRset):
            return False
        if self.name != other.name:
            return False
        return super(RRset, self).__eq__(other)

    def match(self, name, rdclass, rdtype, covers, deleting=None):
        """Returns True if this rrset matches the specified class, type,
        covers, and deletion state."""

        if not super(RRset, self).match(rdclass, rdtype, covers):
            return False
        if self.name != name or self.deleting != deleting:
            return False
        return True

    def to_text(self, origin=None, relativize=True, **kw):
        """Convert the RRset into DNS master file format.

        @see: L{dns.name.Name.choose_relativity} for more information
        on how I{origin} and I{relativize} determine the way names
        are emitted.

        Any additional keyword arguments are passed on to the rdata
        to_text() method.

        @param origin: The origin for relative names, or None.
        @type origin: dns.name.Name object
        @param relativize: True if names should names be relativized
        @type relativize: bool"""

        return super(RRset, self).to_text(self.name, origin, relativize,
                                          self.deleting, **kw)

    def to_wire(self, file, compress=None, origin=None, **kw):
        """Convert the RRset to wire format."""

        return super(RRset, self).to_wire(self.name, file, compress, origin,
                                          self.deleting, **kw)

    def to_rdataset(self):
        """Convert an RRset into an Rdataset.

        @rtype: dns.rdataset.Rdataset object
        """
        return dns.rdataset.from_rdata_list(self.ttl, list(self))


def from_text_list(name, ttl, rdclass, rdtype, text_rdatas):
    """Create an RRset with the specified name, TTL, class, and type, and with
    the specified list of rdatas in text format.

    @rtype: dns.rrset.RRset object
    """

    if isinstance(name, (str, unicode)):
        name = dns.name.from_text(name, None)
    if isinstance(rdclass, (str, unicode)):
        rdclass = dns.rdataclass.from_text(rdclass)
    if isinstance(rdtype, (str, unicode)):
        rdtype = dns.rdatatype.from_text(rdtype)
    r = RRset(name, rdclass, rdtype)
    r.update_ttl(ttl)
    for t in text_rdatas:
        rd = dns.rdata.from_text(r.rdclass, r.rdtype, t)
        r.add(rd)
    return r

def from_text(name, ttl, rdclass, rdtype, *text_rdatas):
    """Create an RRset with the specified name, TTL, class, and type and with
    the specified rdatas in text format.

    @rtype: dns.rrset.RRset object
    """

    return from_text_list(name, ttl, rdclass, rdtype, text_rdatas)

def from_rdata_list(name, ttl, rdatas):
    """Create an RRset with the specified name and TTL, and with
    the specified list of rdata objects.

    @rtype: dns.rrset.RRset object
    """

    if isinstance(name, (str, unicode)):
        name = dns.name.from_text(name, None)

    if len(rdatas) == 0:
        raise ValueError("rdata list must not be empty")
    r = None
    for rd in rdatas:
        if r is None:
            r = RRset(name, rd.rdclass, rd.rdtype)
            r.update_ttl(ttl)
            first_time = False
        r.add(rd)
    return r

def from_rdata(name, ttl, *rdatas):
    """Create an RRset with the specified name and TTL, and with
    the specified rdata objects.

    @rtype: dns.rrset.RRset object
    """

    return from_rdata_list(name, ttl, rdatas)

########NEW FILE########
__FILENAME__ = set
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""A simple Set class."""

class Set(object):
    """A simple set class.

    Sets are not in Python until 2.3, and rdata are not immutable so
    we cannot use sets.Set anyway.  This class implements subset of
    the 2.3 Set interface using a list as the container.

    @ivar items: A list of the items which are in the set
    @type items: list"""

    __slots__ = ['items']

    def __init__(self, items=None):
        """Initialize the set.

        @param items: the initial set of items
        @type items: any iterable or None
        """

        self.items = []
        if not items is None:
            for item in items:
                self.add(item)

    def __repr__(self):
        return "dns.simpleset.Set(%s)" % repr(self.items)

    def add(self, item):
        """Add an item to the set."""
        if not item in self.items:
            self.items.append(item)

    def remove(self, item):
        """Remove an item from the set."""
        self.items.remove(item)

    def discard(self, item):
        """Remove an item from the set if present."""
        try:
            self.items.remove(item)
        except ValueError:
            pass

    def _clone(self):
        """Make a (shallow) copy of the set.

        There is a 'clone protocol' that subclasses of this class
        should use.  To make a copy, first call your super's _clone()
        method, and use the object returned as the new instance.  Then
        make shallow copies of the attributes defined in the subclass.

        This protocol allows us to write the set algorithms that
        return new instances (e.g. union) once, and keep using them in
        subclasses.
        """

        cls = self.__class__
        obj = cls.__new__(cls)
        obj.items = list(self.items)
        return obj

    def __copy__(self):
        """Make a (shallow) copy of the set."""
        return self._clone()

    def copy(self):
        """Make a (shallow) copy of the set."""
        return self._clone()

    def union_update(self, other):
        """Update the set, adding any elements from other which are not
        already in the set.
        @param other: the collection of items with which to update the set
        @type other: Set object
        """
        if not isinstance(other, Set):
            raise ValueError('other must be a Set instance')
        if self is other:
            return
        for item in other.items:
            self.add(item)

    def intersection_update(self, other):
        """Update the set, removing any elements from other which are not
        in both sets.
        @param other: the collection of items with which to update the set
        @type other: Set object
        """
        if not isinstance(other, Set):
            raise ValueError('other must be a Set instance')
        if self is other:
            return
        # we make a copy of the list so that we can remove items from
        # the list without breaking the iterator.
        for item in list(self.items):
            if item not in other.items:
                self.items.remove(item)

    def difference_update(self, other):
        """Update the set, removing any elements from other which are in
        the set.
        @param other: the collection of items with which to update the set
        @type other: Set object
        """
        if not isinstance(other, Set):
            raise ValueError('other must be a Set instance')
        if self is other:
            self.items = []
        else:
            for item in other.items:
                self.discard(item)

    def union(self, other):
        """Return a new set which is the union of I{self} and I{other}.

        @param other: the other set
        @type other: Set object
        @rtype: the same type as I{self}
        """

        obj = self._clone()
        obj.union_update(other)
        return obj

    def intersection(self, other):
        """Return a new set which is the intersection of I{self} and I{other}.

        @param other: the other set
        @type other: Set object
        @rtype: the same type as I{self}
        """

        obj = self._clone()
        obj.intersection_update(other)
        return obj

    def difference(self, other):
        """Return a new set which I{self} - I{other}, i.e. the items
        in I{self} which are not also in I{other}.

        @param other: the other set
        @type other: Set object
        @rtype: the same type as I{self}
        """

        obj = self._clone()
        obj.difference_update(other)
        return obj

    def __or__(self, other):
        return self.union(other)

    def __and__(self, other):
        return self.intersection(other)

    def __add__(self, other):
        return self.union(other)

    def __sub__(self, other):
        return self.difference(other)

    def __ior__(self, other):
        self.union_update(other)
        return self

    def __iand__(self, other):
        self.intersection_update(other)
        return self

    def __iadd__(self, other):
        self.union_update(other)
        return self

    def __isub__(self, other):
        self.difference_update(other)
        return self

    def update(self, other):
        """Update the set, adding any elements from other which are not
        already in the set.
        @param other: the collection of items with which to update the set
        @type other: any iterable type"""
        for item in other:
            self.add(item)

    def clear(self):
        """Make the set empty."""
        self.items = []

    def __eq__(self, other):
        # Yes, this is inefficient but the sets we're dealing with are
        # usually quite small, so it shouldn't hurt too much.
        for item in self.items:
            if not item in other.items:
                return False
        for item in other.items:
            if not item in self.items:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, i):
        return self.items[i]

    def __delitem__(self, i):
        del self.items[i]

    def __getslice__(self, i, j):
        return self.items[i:j]

    def __delslice__(self, i, j):
        del self.items[i:j]

    def issubset(self, other):
        """Is I{self} a subset of I{other}?

        @rtype: bool
        """

        if not isinstance(other, Set):
            raise ValueError('other must be a Set instance')
        for item in self.items:
            if not item in other.items:
                return False
        return True

    def issuperset(self, other):
        """Is I{self} a superset of I{other}?

        @rtype: bool
        """

        if not isinstance(other, Set):
            raise ValueError('other must be a Set instance')
        for item in other.items:
            if not item in self.items:
                return False
        return True

########NEW FILE########
__FILENAME__ = tokenizer
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""Tokenize DNS master file format"""

import cStringIO
import sys

import dns.exception
import dns.name
import dns.ttl

_DELIMITERS = {
    ' ' : True,
    '\t' : True,
    '\n' : True,
    ';' : True,
    '(' : True,
    ')' : True,
    '"' : True }

_QUOTING_DELIMITERS = { '"' : True }

EOF = 0
EOL = 1
WHITESPACE = 2
IDENTIFIER = 3
QUOTED_STRING = 4
COMMENT = 5
DELIMITER = 6

class UngetBufferFull(dns.exception.DNSException):
    """Raised when an attempt is made to unget a token when the unget
    buffer is full."""
    pass

class Token(object):
    """A DNS master file format token.

    @ivar ttype: The token type
    @type ttype: int
    @ivar value: The token value
    @type value: string
    @ivar has_escape: Does the token value contain escapes?
    @type has_escape: bool
    """

    def __init__(self, ttype, value='', has_escape=False):
        """Initialize a token instance.

        @param ttype: The token type
        @type ttype: int
        @param value: The token value
        @type value: string
        @param has_escape: Does the token value contain escapes?
        @type has_escape: bool
        """
        self.ttype = ttype
        self.value = value
        self.has_escape = has_escape

    def is_eof(self):
        return self.ttype == EOF

    def is_eol(self):
        return self.ttype == EOL

    def is_whitespace(self):
        return self.ttype == WHITESPACE

    def is_identifier(self):
        return self.ttype == IDENTIFIER

    def is_quoted_string(self):
        return self.ttype == QUOTED_STRING

    def is_comment(self):
        return self.ttype == COMMENT

    def is_delimiter(self):
        return self.ttype == DELIMITER

    def is_eol_or_eof(self):
        return (self.ttype == EOL or self.ttype == EOF)

    def __eq__(self, other):
        if not isinstance(other, Token):
            return False
        return (self.ttype == other.ttype and
                self.value == other.value)

    def __ne__(self, other):
        if not isinstance(other, Token):
            return True
        return (self.ttype != other.ttype or
                self.value != other.value)

    def __str__(self):
        return '%d "%s"' % (self.ttype, self.value)

    def unescape(self):
        if not self.has_escape:
            return self
        unescaped = ''
        l = len(self.value)
        i = 0
        while i < l:
            c = self.value[i]
            i += 1
            if c == '\\':
                if i >= l:
                    raise dns.exception.UnexpectedEnd
                c = self.value[i]
                i += 1
                if c.isdigit():
                    if i >= l:
                        raise dns.exception.UnexpectedEnd
                    c2 = self.value[i]
                    i += 1
                    if i >= l:
                        raise dns.exception.UnexpectedEnd
                    c3 = self.value[i]
                    i += 1
                    if not (c2.isdigit() and c3.isdigit()):
                        raise dns.exception.SyntaxError
                    c = chr(int(c) * 100 + int(c2) * 10 + int(c3))
            unescaped += c
        return Token(self.ttype, unescaped)

    # compatibility for old-style tuple tokens

    def __len__(self):
        return 2

    def __iter__(self):
        return iter((self.ttype, self.value))

    def __getitem__(self, i):
        if i == 0:
            return self.ttype
        elif i == 1:
            return self.value
        else:
            raise IndexError

class Tokenizer(object):
    """A DNS master file format tokenizer.

    A token is a (type, value) tuple, where I{type} is an int, and
    I{value} is a string.  The valid types are EOF, EOL, WHITESPACE,
    IDENTIFIER, QUOTED_STRING, COMMENT, and DELIMITER.

    @ivar file: The file to tokenize
    @type file: file
    @ivar ungotten_char: The most recently ungotten character, or None.
    @type ungotten_char: string
    @ivar ungotten_token: The most recently ungotten token, or None.
    @type ungotten_token: (int, string) token tuple
    @ivar multiline: The current multiline level.  This value is increased
    by one every time a '(' delimiter is read, and decreased by one every time
    a ')' delimiter is read.
    @type multiline: int
    @ivar quoting: This variable is true if the tokenizer is currently
    reading a quoted string.
    @type quoting: bool
    @ivar eof: This variable is true if the tokenizer has encountered EOF.
    @type eof: bool
    @ivar delimiters: The current delimiter dictionary.
    @type delimiters: dict
    @ivar line_number: The current line number
    @type line_number: int
    @ivar filename: A filename that will be returned by the L{where} method.
    @type filename: string
    """

    def __init__(self, f=sys.stdin, filename=None):
        """Initialize a tokenizer instance.

        @param f: The file to tokenize.  The default is sys.stdin.
        This parameter may also be a string, in which case the tokenizer
        will take its input from the contents of the string.
        @type f: file or string
        @param filename: the name of the filename that the L{where} method
        will return.
        @type filename: string
        """

        if isinstance(f, str):
            f = cStringIO.StringIO(f)
            if filename is None:
                filename = '<string>'
        else:
            if filename is None:
                if f is sys.stdin:
                    filename = '<stdin>'
                else:
                    filename = '<file>'
        self.file = f
        self.ungotten_char = None
        self.ungotten_token = None
        self.multiline = 0
        self.quoting = False
        self.eof = False
        self.delimiters = _DELIMITERS
        self.line_number = 1
        self.filename = filename

    def _get_char(self):
        """Read a character from input.
        @rtype: string
        """

        if self.ungotten_char is None:
            if self.eof:
                c = ''
            else:
                c = self.file.read(1)
                if c == '':
                    self.eof = True
                elif c == '\n':
                    self.line_number += 1
        else:
            c = self.ungotten_char
            self.ungotten_char = None
        return c

    def where(self):
        """Return the current location in the input.

        @rtype: (string, int) tuple.  The first item is the filename of
        the input, the second is the current line number.
        """

        return (self.filename, self.line_number)

    def _unget_char(self, c):
        """Unget a character.

        The unget buffer for characters is only one character large; it is
        an error to try to unget a character when the unget buffer is not
        empty.

        @param c: the character to unget
        @type c: string
        @raises UngetBufferFull: there is already an ungotten char
        """

        if not self.ungotten_char is None:
            raise UngetBufferFull
        self.ungotten_char = c

    def skip_whitespace(self):
        """Consume input until a non-whitespace character is encountered.

        The non-whitespace character is then ungotten, and the number of
        whitespace characters consumed is returned.

        If the tokenizer is in multiline mode, then newlines are whitespace.

        @rtype: int
        """

        skipped = 0
        while True:
            c = self._get_char()
            if c != ' ' and c != '\t':
                if (c != '\n') or not self.multiline:
                    self._unget_char(c)
                    return skipped
            skipped += 1

    def get(self, want_leading = False, want_comment = False):
        """Get the next token.

        @param want_leading: If True, return a WHITESPACE token if the
        first character read is whitespace.  The default is False.
        @type want_leading: bool
        @param want_comment: If True, return a COMMENT token if the
        first token read is a comment.  The default is False.
        @type want_comment: bool
        @rtype: Token object
        @raises dns.exception.UnexpectedEnd: input ended prematurely
        @raises dns.exception.SyntaxError: input was badly formed
        """

        if not self.ungotten_token is None:
            token = self.ungotten_token
            self.ungotten_token = None
            if token.is_whitespace():
                if want_leading:
                    return token
            elif token.is_comment():
                if want_comment:
                    return token
            else:
                return token
        skipped = self.skip_whitespace()
        if want_leading and skipped > 0:
            return Token(WHITESPACE, ' ')
        token = ''
        ttype = IDENTIFIER
        has_escape = False
        while True:
            c = self._get_char()
            if c == '' or c in self.delimiters:
                if c == '' and self.quoting:
                    raise dns.exception.UnexpectedEnd
                if token == '' and ttype != QUOTED_STRING:
                    if c == '(':
                        self.multiline += 1
                        self.skip_whitespace()
                        continue
                    elif c == ')':
                        if not self.multiline > 0:
                            raise dns.exception.SyntaxError
                        self.multiline -= 1
                        self.skip_whitespace()
                        continue
                    elif c == '"':
                        if not self.quoting:
                            self.quoting = True
                            self.delimiters = _QUOTING_DELIMITERS
                            ttype = QUOTED_STRING
                            continue
                        else:
                            self.quoting = False
                            self.delimiters = _DELIMITERS
                            self.skip_whitespace()
                            continue
                    elif c == '\n':
                        return Token(EOL, '\n')
                    elif c == ';':
                        while 1:
                            c = self._get_char()
                            if c == '\n' or c == '':
                                break
                            token += c
                        if want_comment:
                            self._unget_char(c)
                            return Token(COMMENT, token)
                        elif c == '':
                            if self.multiline:
                                raise dns.exception.SyntaxError('unbalanced parentheses')
                            return Token(EOF)
                        elif self.multiline:
                            self.skip_whitespace()
                            token = ''
                            continue
                        else:
                            return Token(EOL, '\n')
                    else:
                        # This code exists in case we ever want a
                        # delimiter to be returned.  It never produces
                        # a token currently.
                        token = c
                        ttype = DELIMITER
                else:
                    self._unget_char(c)
                break
            elif self.quoting:
                if c == '\\':
                    c = self._get_char()
                    if c == '':
                        raise dns.exception.UnexpectedEnd
                    if c.isdigit():
                        c2 = self._get_char()
                        if c2 == '':
                            raise dns.exception.UnexpectedEnd
                        c3 = self._get_char()
                        if c == '':
                            raise dns.exception.UnexpectedEnd
                        if not (c2.isdigit() and c3.isdigit()):
                            raise dns.exception.SyntaxError
                        c = chr(int(c) * 100 + int(c2) * 10 + int(c3))
                elif c == '\n':
                    raise dns.exception.SyntaxError('newline in quoted string')
            elif c == '\\':
                #
                # It's an escape.  Put it and the next character into
                # the token; it will be checked later for goodness.
                #
                token += c
                has_escape = True
                c = self._get_char()
                if c == '' or c == '\n':
                    raise dns.exception.UnexpectedEnd
            token += c
        if token == '' and ttype != QUOTED_STRING:
            if self.multiline:
                raise dns.exception.SyntaxError('unbalanced parentheses')
            ttype = EOF
        return Token(ttype, token, has_escape)

    def unget(self, token):
        """Unget a token.

        The unget buffer for tokens is only one token large; it is
        an error to try to unget a token when the unget buffer is not
        empty.

        @param token: the token to unget
        @type token: Token object
        @raises UngetBufferFull: there is already an ungotten token
        """

        if not self.ungotten_token is None:
            raise UngetBufferFull
        self.ungotten_token = token

    def next(self):
        """Return the next item in an iteration.
        @rtype: (int, string)
        """

        token = self.get()
        if token.is_eof():
            raise StopIteration
        return token

    def __iter__(self):
        return self

    # Helpers

    def get_int(self):
        """Read the next token and interpret it as an integer.

        @raises dns.exception.SyntaxError:
        @rtype: int
        """

        token = self.get().unescape()
        if not token.is_identifier():
            raise dns.exception.SyntaxError('expecting an identifier')
        if not token.value.isdigit():
            raise dns.exception.SyntaxError('expecting an integer')
        return int(token.value)

    def get_uint8(self):
        """Read the next token and interpret it as an 8-bit unsigned
        integer.

        @raises dns.exception.SyntaxError:
        @rtype: int
        """

        value = self.get_int()
        if value < 0 or value > 255:
            raise dns.exception.SyntaxError('%d is not an unsigned 8-bit integer' % value)
        return value

    def get_uint16(self):
        """Read the next token and interpret it as a 16-bit unsigned
        integer.

        @raises dns.exception.SyntaxError:
        @rtype: int
        """

        value = self.get_int()
        if value < 0 or value > 65535:
            raise dns.exception.SyntaxError('%d is not an unsigned 16-bit integer' % value)
        return value

    def get_uint32(self):
        """Read the next token and interpret it as a 32-bit unsigned
        integer.

        @raises dns.exception.SyntaxError:
        @rtype: int
        """

        token = self.get().unescape()
        if not token.is_identifier():
            raise dns.exception.SyntaxError('expecting an identifier')
        if not token.value.isdigit():
            raise dns.exception.SyntaxError('expecting an integer')
        value = long(token.value)
        if value < 0 or value > 4294967296L:
            raise dns.exception.SyntaxError('%d is not an unsigned 32-bit integer' % value)
        return value

    def get_string(self, origin=None):
        """Read the next token and interpret it as a string.

        @raises dns.exception.SyntaxError:
        @rtype: string
        """

        token = self.get().unescape()
        if not (token.is_identifier() or token.is_quoted_string()):
            raise dns.exception.SyntaxError('expecting a string')
        return token.value

    def get_identifier(self, origin=None):
        """Read the next token and raise an exception if it is not an identifier.

        @raises dns.exception.SyntaxError:
        @rtype: string
        """

        token = self.get().unescape()
        if not token.is_identifier():
            raise dns.exception.SyntaxError('expecting an identifier')
        return token.value

    def get_name(self, origin=None):
        """Read the next token and interpret it as a DNS name.

        @raises dns.exception.SyntaxError:
        @rtype: dns.name.Name object"""

        token = self.get()
        if not token.is_identifier():
            raise dns.exception.SyntaxError('expecting an identifier')
        return dns.name.from_text(token.value, origin)

    def get_eol(self):
        """Read the next token and raise an exception if it isn't EOL or
        EOF.

        @raises dns.exception.SyntaxError:
        @rtype: string
        """

        token = self.get()
        if not token.is_eol_or_eof():
            raise dns.exception.SyntaxError('expected EOL or EOF, got %d "%s"' % (token.ttype, token.value))
        return token.value

    def get_ttl(self):
        token = self.get().unescape()
        if not token.is_identifier():
            raise dns.exception.SyntaxError('expecting an identifier')
        return dns.ttl.from_text(token.value)

########NEW FILE########
__FILENAME__ = tsig
# Copyright (C) 2001-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS TSIG support."""

import hmac
import struct
import sys

import dns.exception
import dns.hash
import dns.rdataclass
import dns.name

class BadTime(dns.exception.DNSException):
    """Raised if the current time is not within the TSIG's validity time."""
    pass

class BadSignature(dns.exception.DNSException):
    """Raised if the TSIG signature fails to verify."""
    pass

class PeerError(dns.exception.DNSException):
    """Base class for all TSIG errors generated by the remote peer"""
    pass

class PeerBadKey(PeerError):
    """Raised if the peer didn't know the key we used"""
    pass

class PeerBadSignature(PeerError):
    """Raised if the peer didn't like the signature we sent"""
    pass

class PeerBadTime(PeerError):
    """Raised if the peer didn't like the time we sent"""
    pass

class PeerBadTruncation(PeerError):
    """Raised if the peer didn't like amount of truncation in the TSIG we sent"""
    pass

# TSIG Algorithms

HMAC_MD5 = dns.name.from_text("HMAC-MD5.SIG-ALG.REG.INT")
HMAC_SHA1 = dns.name.from_text("hmac-sha1")
HMAC_SHA224 = dns.name.from_text("hmac-sha224")
HMAC_SHA256 = dns.name.from_text("hmac-sha256")
HMAC_SHA384 = dns.name.from_text("hmac-sha384")
HMAC_SHA512 = dns.name.from_text("hmac-sha512")

default_algorithm = HMAC_MD5

BADSIG = 16
BADKEY = 17
BADTIME = 18
BADTRUNC = 22

def sign(wire, keyname, secret, time, fudge, original_id, error,
         other_data, request_mac, ctx=None, multi=False, first=True,
         algorithm=default_algorithm):
    """Return a (tsig_rdata, mac, ctx) tuple containing the HMAC TSIG rdata
    for the input parameters, the HMAC MAC calculated by applying the
    TSIG signature algorithm, and the TSIG digest context.
    @rtype: (string, string, hmac.HMAC object)
    @raises ValueError: I{other_data} is too long
    @raises NotImplementedError: I{algorithm} is not supported
    """

    (algorithm_name, digestmod) = get_algorithm(algorithm)
    if first:
        ctx = hmac.new(secret, digestmod=digestmod)
        ml = len(request_mac)
        if ml > 0:
            ctx.update(struct.pack('!H', ml))
            ctx.update(request_mac)
    id = struct.pack('!H', original_id)
    ctx.update(id)
    ctx.update(wire[2:])
    if first:
        ctx.update(keyname.to_digestable())
        ctx.update(struct.pack('!H', dns.rdataclass.ANY))
        ctx.update(struct.pack('!I', 0))
    long_time = time + 0L
    upper_time = (long_time >> 32) & 0xffffL
    lower_time = long_time & 0xffffffffL
    time_mac = struct.pack('!HIH', upper_time, lower_time, fudge)
    pre_mac = algorithm_name + time_mac
    ol = len(other_data)
    if ol > 65535:
        raise ValueError('TSIG Other Data is > 65535 bytes')
    post_mac = struct.pack('!HH', error, ol) + other_data
    if first:
        ctx.update(pre_mac)
        ctx.update(post_mac)
    else:
        ctx.update(time_mac)
    mac = ctx.digest()
    mpack = struct.pack('!H', len(mac))
    tsig_rdata = pre_mac + mpack + mac + id + post_mac
    if multi:
        ctx = hmac.new(secret, digestmod=digestmod)
        ml = len(mac)
        ctx.update(struct.pack('!H', ml))
        ctx.update(mac)
    else:
        ctx = None
    return (tsig_rdata, mac, ctx)

def hmac_md5(wire, keyname, secret, time, fudge, original_id, error,
             other_data, request_mac, ctx=None, multi=False, first=True,
             algorithm=default_algorithm):
    return sign(wire, keyname, secret, time, fudge, original_id, error,
                other_data, request_mac, ctx, multi, first, algorithm)

def validate(wire, keyname, secret, now, request_mac, tsig_start, tsig_rdata,
             tsig_rdlen, ctx=None, multi=False, first=True):
    """Validate the specified TSIG rdata against the other input parameters.

    @raises FormError: The TSIG is badly formed.
    @raises BadTime: There is too much time skew between the client and the
    server.
    @raises BadSignature: The TSIG signature did not validate
    @rtype: hmac.HMAC object"""

    (adcount,) = struct.unpack("!H", wire[10:12])
    if adcount == 0:
        raise dns.exception.FormError
    adcount -= 1
    new_wire = wire[0:10] + struct.pack("!H", adcount) + wire[12:tsig_start]
    current = tsig_rdata
    (aname, used) = dns.name.from_wire(wire, current)
    current = current + used
    (upper_time, lower_time, fudge, mac_size) = \
                 struct.unpack("!HIHH", wire[current:current + 10])
    time = ((upper_time + 0L) << 32) + (lower_time + 0L)
    current += 10
    mac = wire[current:current + mac_size]
    current += mac_size
    (original_id, error, other_size) = \
                  struct.unpack("!HHH", wire[current:current + 6])
    current += 6
    other_data = wire[current:current + other_size]
    current += other_size
    if current != tsig_rdata + tsig_rdlen:
        raise dns.exception.FormError
    if error != 0:
        if error == BADSIG:
            raise PeerBadSignature
        elif error == BADKEY:
            raise PeerBadKey
        elif error == BADTIME:
            raise PeerBadTime
        elif error == BADTRUNC:
            raise PeerBadTruncation
        else:
            raise PeerError('unknown TSIG error code %d' % error)
    time_low = time - fudge
    time_high = time + fudge
    if now < time_low or now > time_high:
        raise BadTime
    (junk, our_mac, ctx) = sign(new_wire, keyname, secret, time, fudge,
                                original_id, error, other_data,
                                request_mac, ctx, multi, first, aname)
    if (our_mac != mac):
        raise BadSignature
    return ctx

_hashes = None

def _maybe_add_hash(tsig_alg, hash_alg):
    try:
        _hashes[tsig_alg] = dns.hash.get(hash_alg)
    except KeyError:
        pass

def _setup_hashes():
    global _hashes
    _hashes = {}
    _maybe_add_hash(HMAC_SHA224, 'SHA224')
    _maybe_add_hash(HMAC_SHA256, 'SHA256')
    _maybe_add_hash(HMAC_SHA384, 'SHA384')
    _maybe_add_hash(HMAC_SHA512, 'SHA512')
    _maybe_add_hash(HMAC_SHA1, 'SHA1')
    _maybe_add_hash(HMAC_MD5, 'MD5')

def get_algorithm(algorithm):
    """Returns the wire format string and the hash module to use for the
    specified TSIG algorithm

    @rtype: (string, hash constructor)
    @raises NotImplementedError: I{algorithm} is not supported
    """

    global _hashes
    if _hashes is None:
        _setup_hashes()

    if isinstance(algorithm, (str, unicode)):
        algorithm = dns.name.from_text(algorithm)

    if sys.hexversion < 0x02050200 and \
       (algorithm == HMAC_SHA384 or algorithm == HMAC_SHA512):
        raise NotImplementedError("TSIG algorithm " + str(algorithm) +
                                  " requires Python 2.5.2 or later")

    try:
        return (algorithm.to_digestable(), _hashes[algorithm])
    except KeyError:
        raise NotImplementedError("TSIG algorithm " + str(algorithm) +
                                  " is not supported")

def get_algorithm_and_mac(wire, tsig_rdata, tsig_rdlen):
    """Return the tsig algorithm for the specified tsig_rdata
    @raises FormError: The TSIG is badly formed.
    """
    current = tsig_rdata
    (aname, used) = dns.name.from_wire(wire, current)
    current = current + used
    (upper_time, lower_time, fudge, mac_size) = \
                 struct.unpack("!HIHH", wire[current:current + 10])
    current += 10
    mac = wire[current:current + mac_size]
    current += mac_size
    if current > tsig_rdata + tsig_rdlen:
        raise dns.exception.FormError
    return (aname, mac)

########NEW FILE########
__FILENAME__ = tsigkeyring
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""A place to store TSIG keys."""

import base64

import dns.name

def from_text(textring):
    """Convert a dictionary containing (textual DNS name, base64 secret) pairs
    into a binary keyring which has (dns.name.Name, binary secret) pairs.
    @rtype: dict"""
    
    keyring = {}
    for keytext in textring:
        keyname = dns.name.from_text(keytext)
        secret = base64.decodestring(textring[keytext])
        keyring[keyname] = secret
    return keyring

def to_text(keyring):
    """Convert a dictionary containing (dns.name.Name, binary secret) pairs
    into a text keyring which has (textual DNS name, base64 secret) pairs.
    @rtype: dict"""
    
    textring = {}
    for keyname in keyring:
        keytext = keyname.to_text()
        secret = base64.encodestring(keyring[keyname])
        textring[keytext] = secret
    return textring

########NEW FILE########
__FILENAME__ = ttl
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS TTL conversion."""

import dns.exception

class BadTTL(dns.exception.SyntaxError):
    pass

def from_text(text):
    """Convert the text form of a TTL to an integer.

    The BIND 8 units syntax for TTLs (e.g. '1w6d4h3m10s') is supported.

    @param text: the textual TTL
    @type text: string
    @raises dns.ttl.BadTTL: the TTL is not well-formed
    @rtype: int
    """

    if text.isdigit():
        total = long(text)
    else:
        if not text[0].isdigit():
            raise BadTTL
        total = 0L
        current = 0L
        for c in text:
            if c.isdigit():
                current *= 10
                current += long(c)
            else:
                c = c.lower()
                if c == 'w':
                    total += current * 604800L
                elif c == 'd':
                    total += current * 86400L
                elif c == 'h':
                    total += current * 3600L
                elif c == 'm':
                    total += current * 60L
                elif c == 's':
                    total += current
                else:
                    raise BadTTL("unknown unit '%s'" % c)
                current = 0
        if not current == 0:
            raise BadTTL("trailing integer")
    if total < 0L or total > 2147483647L:
        raise BadTTL("TTL should be between 0 and 2^31 - 1 (inclusive)")
    return total

########NEW FILE########
__FILENAME__ = update
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS Dynamic Update Support"""

import dns.message
import dns.name
import dns.opcode
import dns.rdata
import dns.rdataclass
import dns.rdataset
import dns.tsig

class Update(dns.message.Message):
    def __init__(self, zone, rdclass=dns.rdataclass.IN, keyring=None,
                 keyname=None, keyalgorithm=dns.tsig.default_algorithm):
        """Initialize a new DNS Update object.

        @param zone: The zone which is being updated.
        @type zone: A dns.name.Name or string
        @param rdclass: The class of the zone; defaults to dns.rdataclass.IN.
        @type rdclass: An int designating the class, or a string whose value
        is the name of a class.
        @param keyring: The TSIG keyring to use; defaults to None.
        @type keyring: dict
        @param keyname: The name of the TSIG key to use; defaults to None.
        The key must be defined in the keyring.  If a keyring is specified
        but a keyname is not, then the key used will be the first key in the
        keyring.  Note that the order of keys in a dictionary is not defined,
        so applications should supply a keyname when a keyring is used, unless
        they know the keyring contains only one key.
        @type keyname: dns.name.Name or string
        @param keyalgorithm: The TSIG algorithm to use; defaults to
        dns.tsig.default_algorithm.  Constants for TSIG algorithms are defined
        in dns.tsig, and the currently implemented algorithms are
        HMAC_MD5, HMAC_SHA1, HMAC_SHA224, HMAC_SHA256, HMAC_SHA384, and
        HMAC_SHA512.
        @type keyalgorithm: string
        """
        super(Update, self).__init__()
        self.flags |= dns.opcode.to_flags(dns.opcode.UPDATE)
        if isinstance(zone, (str, unicode)):
            zone = dns.name.from_text(zone)
        self.origin = zone
        if isinstance(rdclass, str):
            rdclass = dns.rdataclass.from_text(rdclass)
        self.zone_rdclass = rdclass
        self.find_rrset(self.question, self.origin, rdclass, dns.rdatatype.SOA,
                        create=True, force_unique=True)
        if not keyring is None:
            self.use_tsig(keyring, keyname, algorithm=keyalgorithm)

    def _add_rr(self, name, ttl, rd, deleting=None, section=None):
        """Add a single RR to the update section."""

        if section is None:
            section = self.authority
        covers = rd.covers()
        rrset = self.find_rrset(section, name, self.zone_rdclass, rd.rdtype,
                                covers, deleting, True, True)
        rrset.add(rd, ttl)

    def _add(self, replace, section, name, *args):
        """Add records.  The first argument is the replace mode.  If
        false, RRs are added to an existing RRset; if true, the RRset
        is replaced with the specified contents.  The second
        argument is the section to add to.  The third argument
        is always a name.  The other arguments can be:

                - rdataset...

                - ttl, rdata...

                - ttl, rdtype, string..."""

        if isinstance(name, (str, unicode)):
            name = dns.name.from_text(name, None)
        if isinstance(args[0], dns.rdataset.Rdataset):
            for rds in args:
                if replace:
                    self.delete(name, rds.rdtype)
                for rd in rds:
                    self._add_rr(name, rds.ttl, rd, section=section)
        else:
            args = list(args)
            ttl = int(args.pop(0))
            if isinstance(args[0], dns.rdata.Rdata):
                if replace:
                    self.delete(name, args[0].rdtype)
                for rd in args:
                    self._add_rr(name, ttl, rd, section=section)
            else:
                rdtype = args.pop(0)
                if isinstance(rdtype, str):
                    rdtype = dns.rdatatype.from_text(rdtype)
                if replace:
                    self.delete(name, rdtype)
                for s in args:
                    rd = dns.rdata.from_text(self.zone_rdclass, rdtype, s,
                                             self.origin)
                    self._add_rr(name, ttl, rd, section=section)

    def add(self, name, *args):
        """Add records.  The first argument is always a name.  The other
        arguments can be:

                - rdataset...

                - ttl, rdata...

                - ttl, rdtype, string..."""
        self._add(False, self.authority, name, *args)

    def delete(self, name, *args):
        """Delete records.  The first argument is always a name.  The other
        arguments can be:

                - I{nothing}

                - rdataset...

                - rdata...

                - rdtype, [string...]"""

        if isinstance(name, (str, unicode)):
            name = dns.name.from_text(name, None)
        if len(args) == 0:
            rrset = self.find_rrset(self.authority, name, dns.rdataclass.ANY,
                                    dns.rdatatype.ANY, dns.rdatatype.NONE,
                                    dns.rdatatype.ANY, True, True)
        elif isinstance(args[0], dns.rdataset.Rdataset):
            for rds in args:
                for rd in rds:
                    self._add_rr(name, 0, rd, dns.rdataclass.NONE)
        else:
            args = list(args)
            if isinstance(args[0], dns.rdata.Rdata):
                for rd in args:
                    self._add_rr(name, 0, rd, dns.rdataclass.NONE)
            else:
                rdtype = args.pop(0)
                if isinstance(rdtype, (str, unicode)):
                    rdtype = dns.rdatatype.from_text(rdtype)
                if len(args) == 0:
                    rrset = self.find_rrset(self.authority, name,
                                            self.zone_rdclass, rdtype,
                                            dns.rdatatype.NONE,
                                            dns.rdataclass.ANY,
                                            True, True)
                else:
                    for s in args:
                        rd = dns.rdata.from_text(self.zone_rdclass, rdtype, s,
                                                 self.origin)
                        self._add_rr(name, 0, rd, dns.rdataclass.NONE)

    def replace(self, name, *args):
        """Replace records.  The first argument is always a name.  The other
        arguments can be:

                - rdataset...

                - ttl, rdata...

                - ttl, rdtype, string...

        Note that if you want to replace the entire node, you should do
        a delete of the name followed by one or more calls to add."""

        self._add(True, self.authority, name, *args)

    def present(self, name, *args):
        """Require that an owner name (and optionally an rdata type,
        or specific rdataset) exists as a prerequisite to the
        execution of the update.  The first argument is always a name.
        The other arguments can be:

                - rdataset...

                - rdata...

                - rdtype, string..."""

        if isinstance(name, (str, unicode)):
            name = dns.name.from_text(name, None)
        if len(args) == 0:
            rrset = self.find_rrset(self.answer, name,
                                    dns.rdataclass.ANY, dns.rdatatype.ANY,
                                    dns.rdatatype.NONE, None,
                                    True, True)
        elif isinstance(args[0], dns.rdataset.Rdataset) or \
             isinstance(args[0], dns.rdata.Rdata) or \
             len(args) > 1:
            if not isinstance(args[0], dns.rdataset.Rdataset):
                # Add a 0 TTL
                args = list(args)
                args.insert(0, 0)
            self._add(False, self.answer, name, *args)
        else:
            rdtype = args[0]
            if isinstance(rdtype, (str, unicode)):
                rdtype = dns.rdatatype.from_text(rdtype)
            rrset = self.find_rrset(self.answer, name,
                                    dns.rdataclass.ANY, rdtype,
                                    dns.rdatatype.NONE, None,
                                    True, True)

    def absent(self, name, rdtype=None):
        """Require that an owner name (and optionally an rdata type) does
        not exist as a prerequisite to the execution of the update."""

        if isinstance(name, (str, unicode)):
            name = dns.name.from_text(name, None)
        if rdtype is None:
            rrset = self.find_rrset(self.answer, name,
                                    dns.rdataclass.NONE, dns.rdatatype.ANY,
                                    dns.rdatatype.NONE, None,
                                    True, True)
        else:
            if isinstance(rdtype, (str, unicode)):
                rdtype = dns.rdatatype.from_text(rdtype)
            rrset = self.find_rrset(self.answer, name,
                                    dns.rdataclass.NONE, rdtype,
                                    dns.rdatatype.NONE, None,
                                    True, True)

    def to_wire(self, origin=None, max_size=65535):
        """Return a string containing the update in DNS compressed wire
        format.
        @rtype: string"""
        if origin is None:
            origin = self.origin
        return super(Update, self).to_wire(origin, max_size)

########NEW FILE########
__FILENAME__ = version
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""dnspython release version information."""

MAJOR = 1
MINOR = 11
MICRO = 1
RELEASELEVEL = 0x0f
SERIAL = 0

if RELEASELEVEL == 0x0f:
    version = '%d.%d.%d' % (MAJOR, MINOR, MICRO)
elif RELEASELEVEL == 0x00:
    version = '%d.%d.%dx%d' % \
              (MAJOR, MINOR, MICRO, SERIAL)
else:
    version = '%d.%d.%d%x%d' % \
              (MAJOR, MINOR, MICRO, RELEASELEVEL, SERIAL)

hexversion = MAJOR << 24 | MINOR << 16 | MICRO << 8 | RELEASELEVEL << 4 | \
             SERIAL

########NEW FILE########
__FILENAME__ = wiredata
# Copyright (C) 2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS Wire Data Helper"""

import sys

import dns.exception

class WireData(str):
    # WireData is a string with stricter slicing
    def __getitem__(self, key):
        try:
            return WireData(super(WireData, self).__getitem__(key))
        except IndexError:
            raise dns.exception.FormError
    def __getslice__(self, i, j):
        try:
            if j == sys.maxint:
                # handle the case where the right bound is unspecified
                j = len(self)
            if i < 0 or j < 0:
                raise dns.exception.FormError
            # If it's not an empty slice, access left and right bounds
            # to make sure they're valid
            if i != j:
                super(WireData, self).__getitem__(i)
                super(WireData, self).__getitem__(j - 1)
            return WireData(super(WireData, self).__getslice__(i, j))
        except IndexError:
            raise dns.exception.FormError
    def __iter__(self):
        i = 0
        while 1:
            try:
                yield self[i]
                i += 1
            except dns.exception.FormError:
                raise StopIteration
    def unwrap(self):
        return str(self)

def maybe_wrap(wire):
    if not isinstance(wire, WireData):
        return WireData(wire)
    else:
        return wire

########NEW FILE########
__FILENAME__ = zone
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS Zones."""

from __future__ import generators

import sys
import re

import dns.exception
import dns.name
import dns.node
import dns.rdataclass
import dns.rdatatype
import dns.rdata
import dns.rrset
import dns.tokenizer
import dns.ttl
import dns.grange


class BadZone(dns.exception.DNSException):
    """The zone is malformed."""
    pass

class NoSOA(BadZone):
    """The zone has no SOA RR at its origin."""
    pass

class NoNS(BadZone):
    """The zone has no NS RRset at its origin."""
    pass

class UnknownOrigin(BadZone):
    """The zone's origin is unknown."""
    pass

class Zone(object):
    """A DNS zone.

    A Zone is a mapping from names to nodes.  The zone object may be
    treated like a Python dictionary, e.g. zone[name] will retrieve
    the node associated with that name.  The I{name} may be a
    dns.name.Name object, or it may be a string.  In the either case,
    if the name is relative it is treated as relative to the origin of
    the zone.

    @ivar rdclass: The zone's rdata class; the default is class IN.
    @type rdclass: int
    @ivar origin: The origin of the zone.
    @type origin: dns.name.Name object
    @ivar nodes: A dictionary mapping the names of nodes in the zone to the
    nodes themselves.
    @type nodes: dict
    @ivar relativize: should names in the zone be relativized?
    @type relativize: bool
    @cvar node_factory: the factory used to create a new node
    @type node_factory: class or callable
    """

    node_factory = dns.node.Node

    __slots__ = ['rdclass', 'origin', 'nodes', 'relativize']

    def __init__(self, origin, rdclass=dns.rdataclass.IN, relativize=True):
        """Initialize a zone object.

        @param origin: The origin of the zone.
        @type origin: dns.name.Name object
        @param rdclass: The zone's rdata class; the default is class IN.
        @type rdclass: int"""

        self.rdclass = rdclass
        self.origin = origin
        self.nodes = {}
        self.relativize = relativize

    def __eq__(self, other):
        """Two zones are equal if they have the same origin, class, and
        nodes.
        @rtype: bool
        """

        if not isinstance(other, Zone):
            return False
        if self.rdclass != other.rdclass or \
           self.origin != other.origin or \
           self.nodes != other.nodes:
            return False
        return True

    def __ne__(self, other):
        """Are two zones not equal?
        @rtype: bool
        """

        return not self.__eq__(other)

    def _validate_name(self, name):
        if isinstance(name, (str, unicode)):
            name = dns.name.from_text(name, None)
        elif not isinstance(name, dns.name.Name):
            raise KeyError("name parameter must be convertable to a DNS name")
        if name.is_absolute():
            if not name.is_subdomain(self.origin):
                raise KeyError("name parameter must be a subdomain of the zone origin")
            if self.relativize:
                name = name.relativize(self.origin)
        return name

    def __getitem__(self, key):
        key = self._validate_name(key)
        return self.nodes[key]

    def __setitem__(self, key, value):
        key = self._validate_name(key)
        self.nodes[key] = value

    def __delitem__(self, key):
        key = self._validate_name(key)
        del self.nodes[key]

    def __iter__(self):
        return self.nodes.iterkeys()

    def iterkeys(self):
        return self.nodes.iterkeys()

    def keys(self):
        return self.nodes.keys()

    def itervalues(self):
        return self.nodes.itervalues()

    def values(self):
        return self.nodes.values()

    def iteritems(self):
        return self.nodes.iteritems()

    def items(self):
        return self.nodes.items()

    def get(self, key):
        key = self._validate_name(key)
        return self.nodes.get(key)

    def __contains__(self, other):
        return other in self.nodes

    def find_node(self, name, create=False):
        """Find a node in the zone, possibly creating it.

        @param name: the name of the node to find
        @type name: dns.name.Name object or string
        @param create: should the node be created if it doesn't exist?
        @type create: bool
        @raises KeyError: the name is not known and create was not specified.
        @rtype: dns.node.Node object
        """

        name = self._validate_name(name)
        node = self.nodes.get(name)
        if node is None:
            if not create:
                raise KeyError
            node = self.node_factory()
            self.nodes[name] = node
        return node

    def get_node(self, name, create=False):
        """Get a node in the zone, possibly creating it.

        This method is like L{find_node}, except it returns None instead
        of raising an exception if the node does not exist and creation
        has not been requested.

        @param name: the name of the node to find
        @type name: dns.name.Name object or string
        @param create: should the node be created if it doesn't exist?
        @type create: bool
        @rtype: dns.node.Node object or None
        """

        try:
            node = self.find_node(name, create)
        except KeyError:
            node = None
        return node

    def delete_node(self, name):
        """Delete the specified node if it exists.

        It is not an error if the node does not exist.
        """

        name = self._validate_name(name)
        if self.nodes.has_key(name):
            del self.nodes[name]

    def find_rdataset(self, name, rdtype, covers=dns.rdatatype.NONE,
                      create=False):
        """Look for rdata with the specified name and type in the zone,
        and return an rdataset encapsulating it.

        The I{name}, I{rdtype}, and I{covers} parameters may be
        strings, in which case they will be converted to their proper
        type.

        The rdataset returned is not a copy; changes to it will change
        the zone.

        KeyError is raised if the name or type are not found.
        Use L{get_rdataset} if you want to have None returned instead.

        @param name: the owner name to look for
        @type name: DNS.name.Name object or string
        @param rdtype: the rdata type desired
        @type rdtype: int or string
        @param covers: the covered type (defaults to None)
        @type covers: int or string
        @param create: should the node and rdataset be created if they do not
        exist?
        @type create: bool
        @raises KeyError: the node or rdata could not be found
        @rtype: dns.rrset.RRset object
        """

        name = self._validate_name(name)
        if isinstance(rdtype, (str, unicode)):
            rdtype = dns.rdatatype.from_text(rdtype)
        if isinstance(covers, (str, unicode)):
            covers = dns.rdatatype.from_text(covers)
        node = self.find_node(name, create)
        return node.find_rdataset(self.rdclass, rdtype, covers, create)

    def get_rdataset(self, name, rdtype, covers=dns.rdatatype.NONE,
                     create=False):
        """Look for rdata with the specified name and type in the zone,
        and return an rdataset encapsulating it.

        The I{name}, I{rdtype}, and I{covers} parameters may be
        strings, in which case they will be converted to their proper
        type.

        The rdataset returned is not a copy; changes to it will change
        the zone.

        None is returned if the name or type are not found.
        Use L{find_rdataset} if you want to have KeyError raised instead.

        @param name: the owner name to look for
        @type name: DNS.name.Name object or string
        @param rdtype: the rdata type desired
        @type rdtype: int or string
        @param covers: the covered type (defaults to None)
        @type covers: int or string
        @param create: should the node and rdataset be created if they do not
        exist?
        @type create: bool
        @rtype: dns.rrset.RRset object
        """

        try:
            rdataset = self.find_rdataset(name, rdtype, covers, create)
        except KeyError:
            rdataset = None
        return rdataset

    def delete_rdataset(self, name, rdtype, covers=dns.rdatatype.NONE):
        """Delete the rdataset matching I{rdtype} and I{covers}, if it
        exists at the node specified by I{name}.

        The I{name}, I{rdtype}, and I{covers} parameters may be
        strings, in which case they will be converted to their proper
        type.

        It is not an error if the node does not exist, or if there is no
        matching rdataset at the node.

        If the node has no rdatasets after the deletion, it will itself
        be deleted.

        @param name: the owner name to look for
        @type name: DNS.name.Name object or string
        @param rdtype: the rdata type desired
        @type rdtype: int or string
        @param covers: the covered type (defaults to None)
        @type covers: int or string
        """

        name = self._validate_name(name)
        if isinstance(rdtype, (str, unicode)):
            rdtype = dns.rdatatype.from_text(rdtype)
        if isinstance(covers, (str, unicode)):
            covers = dns.rdatatype.from_text(covers)
        node = self.get_node(name)
        if not node is None:
            node.delete_rdataset(self.rdclass, rdtype, covers)
            if len(node) == 0:
                self.delete_node(name)

    def replace_rdataset(self, name, replacement):
        """Replace an rdataset at name.

        It is not an error if there is no rdataset matching I{replacement}.

        Ownership of the I{replacement} object is transferred to the zone;
        in other words, this method does not store a copy of I{replacement}
        at the node, it stores I{replacement} itself.

        If the I{name} node does not exist, it is created.

        @param name: the owner name
        @type name: DNS.name.Name object or string
        @param replacement: the replacement rdataset
        @type replacement: dns.rdataset.Rdataset
        """

        if replacement.rdclass != self.rdclass:
            raise ValueError('replacement.rdclass != zone.rdclass')
        node = self.find_node(name, True)
        node.replace_rdataset(replacement)

    def find_rrset(self, name, rdtype, covers=dns.rdatatype.NONE):
        """Look for rdata with the specified name and type in the zone,
        and return an RRset encapsulating it.

        The I{name}, I{rdtype}, and I{covers} parameters may be
        strings, in which case they will be converted to their proper
        type.

        This method is less efficient than the similar
        L{find_rdataset} because it creates an RRset instead of
        returning the matching rdataset.  It may be more convenient
        for some uses since it returns an object which binds the owner
        name to the rdata.

        This method may not be used to create new nodes or rdatasets;
        use L{find_rdataset} instead.

        KeyError is raised if the name or type are not found.
        Use L{get_rrset} if you want to have None returned instead.

        @param name: the owner name to look for
        @type name: DNS.name.Name object or string
        @param rdtype: the rdata type desired
        @type rdtype: int or string
        @param covers: the covered type (defaults to None)
        @type covers: int or string
        @raises KeyError: the node or rdata could not be found
        @rtype: dns.rrset.RRset object
        """

        name = self._validate_name(name)
        if isinstance(rdtype, (str, unicode)):
            rdtype = dns.rdatatype.from_text(rdtype)
        if isinstance(covers, (str, unicode)):
            covers = dns.rdatatype.from_text(covers)
        rdataset = self.nodes[name].find_rdataset(self.rdclass, rdtype, covers)
        rrset = dns.rrset.RRset(name, self.rdclass, rdtype, covers)
        rrset.update(rdataset)
        return rrset

    def get_rrset(self, name, rdtype, covers=dns.rdatatype.NONE):
        """Look for rdata with the specified name and type in the zone,
        and return an RRset encapsulating it.

        The I{name}, I{rdtype}, and I{covers} parameters may be
        strings, in which case they will be converted to their proper
        type.

        This method is less efficient than the similar L{get_rdataset}
        because it creates an RRset instead of returning the matching
        rdataset.  It may be more convenient for some uses since it
        returns an object which binds the owner name to the rdata.

        This method may not be used to create new nodes or rdatasets;
        use L{find_rdataset} instead.

        None is returned if the name or type are not found.
        Use L{find_rrset} if you want to have KeyError raised instead.

        @param name: the owner name to look for
        @type name: DNS.name.Name object or string
        @param rdtype: the rdata type desired
        @type rdtype: int or string
        @param covers: the covered type (defaults to None)
        @type covers: int or string
        @rtype: dns.rrset.RRset object
        """

        try:
            rrset = self.find_rrset(name, rdtype, covers)
        except KeyError:
            rrset = None
        return rrset

    def iterate_rdatasets(self, rdtype=dns.rdatatype.ANY,
                          covers=dns.rdatatype.NONE):
        """Return a generator which yields (name, rdataset) tuples for
        all rdatasets in the zone which have the specified I{rdtype}
        and I{covers}.  If I{rdtype} is dns.rdatatype.ANY, the default,
        then all rdatasets will be matched.

        @param rdtype: int or string
        @type rdtype: int or string
        @param covers: the covered type (defaults to None)
        @type covers: int or string
        """

        if isinstance(rdtype, (str, unicode)):
            rdtype = dns.rdatatype.from_text(rdtype)
        if isinstance(covers, (str, unicode)):
            covers = dns.rdatatype.from_text(covers)
        for (name, node) in self.iteritems():
            for rds in node:
                if rdtype == dns.rdatatype.ANY or \
                   (rds.rdtype == rdtype and rds.covers == covers):
                    yield (name, rds)

    def iterate_rdatas(self, rdtype=dns.rdatatype.ANY,
                       covers=dns.rdatatype.NONE):
        """Return a generator which yields (name, ttl, rdata) tuples for
        all rdatas in the zone which have the specified I{rdtype}
        and I{covers}.  If I{rdtype} is dns.rdatatype.ANY, the default,
        then all rdatas will be matched.

        @param rdtype: int or string
        @type rdtype: int or string
        @param covers: the covered type (defaults to None)
        @type covers: int or string
        """

        if isinstance(rdtype, (str, unicode)):
            rdtype = dns.rdatatype.from_text(rdtype)
        if isinstance(covers, (str, unicode)):
            covers = dns.rdatatype.from_text(covers)
        for (name, node) in self.iteritems():
            for rds in node:
                if rdtype == dns.rdatatype.ANY or \
                   (rds.rdtype == rdtype and rds.covers == covers):
                    for rdata in rds:
                        yield (name, rds.ttl, rdata)

    def to_file(self, f, sorted=True, relativize=True, nl=None):
        """Write a zone to a file.

        @param f: file or string.  If I{f} is a string, it is treated
        as the name of a file to open.
        @param sorted: if True, the file will be written with the
        names sorted in DNSSEC order from least to greatest.  Otherwise
        the names will be written in whatever order they happen to have
        in the zone's dictionary.
        @param relativize: if True, domain names in the output will be
        relativized to the zone's origin (if possible).
        @type relativize: bool
        @param nl: The end of line string.  If not specified, the
        output will use the platform's native end-of-line marker (i.e.
        LF on POSIX, CRLF on Windows, CR on Macintosh).
        @type nl: string or None
        """

        if sys.hexversion >= 0x02030000:
            # allow Unicode filenames
            str_type = basestring
        else:
            str_type = str
        if nl is None:
            opts = 'w'
        else:
            opts = 'wb'
        if isinstance(f, str_type):
            f = file(f, opts)
            want_close = True
        else:
            want_close = False
        try:
            if sorted:
                names = self.keys()
                names.sort()
            else:
                names = self.iterkeys()
            for n in names:
                l = self[n].to_text(n, origin=self.origin,
                                    relativize=relativize)
                if nl is None:
                    print >> f, l
                else:
                    f.write(l)
                    f.write(nl)
        finally:
            if want_close:
                f.close()

    def check_origin(self):
        """Do some simple checking of the zone's origin.

        @raises dns.zone.NoSOA: there is no SOA RR
        @raises dns.zone.NoNS: there is no NS RRset
        @raises KeyError: there is no origin node
        """
        if self.relativize:
            name = dns.name.empty
        else:
            name = self.origin
        if self.get_rdataset(name, dns.rdatatype.SOA) is None:
            raise NoSOA
        if self.get_rdataset(name, dns.rdatatype.NS) is None:
            raise NoNS


class _MasterReader(object):
    """Read a DNS master file

    @ivar tok: The tokenizer
    @type tok: dns.tokenizer.Tokenizer object
    @ivar ttl: The default TTL
    @type ttl: int
    @ivar last_name: The last name read
    @type last_name: dns.name.Name object
    @ivar current_origin: The current origin
    @type current_origin: dns.name.Name object
    @ivar relativize: should names in the zone be relativized?
    @type relativize: bool
    @ivar zone: the zone
    @type zone: dns.zone.Zone object
    @ivar saved_state: saved reader state (used when processing $INCLUDE)
    @type saved_state: list of (tokenizer, current_origin, last_name, file)
    tuples.
    @ivar current_file: the file object of the $INCLUDed file being parsed
    (None if no $INCLUDE is active).
    @ivar allow_include: is $INCLUDE allowed?
    @type allow_include: bool
    @ivar check_origin: should sanity checks of the origin node be done?
    The default is True.
    @type check_origin: bool
    """

    def __init__(self, tok, origin, rdclass, relativize, zone_factory=Zone,
                 allow_include=False, check_origin=True):
        if isinstance(origin, (str, unicode)):
            origin = dns.name.from_text(origin)
        self.tok = tok
        self.current_origin = origin
        self.relativize = relativize
        self.ttl = 0
        self.last_name = None
        self.zone = zone_factory(origin, rdclass, relativize=relativize)
        self.saved_state = []
        self.current_file = None
        self.allow_include = allow_include
        self.check_origin = check_origin

    def _eat_line(self):
        while 1:
            token = self.tok.get()
            if token.is_eol_or_eof():
                break

    def _rr_line(self):
        """Process one line from a DNS master file."""
        # Name
        if self.current_origin is None:
            raise UnknownOrigin
        token = self.tok.get(want_leading = True)
        if not token.is_whitespace():
            self.last_name = dns.name.from_text(token.value, self.current_origin)
        else:
            token = self.tok.get()
            if token.is_eol_or_eof():
                # treat leading WS followed by EOL/EOF as if they were EOL/EOF.
                return
            self.tok.unget(token)
        name = self.last_name
        if not name.is_subdomain(self.zone.origin):
            self._eat_line()
            return
        if self.relativize:
            name = name.relativize(self.zone.origin)
        token = self.tok.get()
        if not token.is_identifier():
            raise dns.exception.SyntaxError
        # TTL
        try:
            ttl = dns.ttl.from_text(token.value)
            token = self.tok.get()
            if not token.is_identifier():
                raise dns.exception.SyntaxError
        except dns.ttl.BadTTL:
            ttl = self.ttl
        # Class
        try:
            rdclass = dns.rdataclass.from_text(token.value)
            token = self.tok.get()
            if not token.is_identifier():
                raise dns.exception.SyntaxError
        except dns.exception.SyntaxError:
            raise dns.exception.SyntaxError
        except:
            rdclass = self.zone.rdclass
        if rdclass != self.zone.rdclass:
            raise dns.exception.SyntaxError("RR class is not zone's class")
        # Type
        try:
            rdtype = dns.rdatatype.from_text(token.value)
        except:
            raise dns.exception.SyntaxError("unknown rdatatype '%s'" % token.value)
        n = self.zone.nodes.get(name)
        if n is None:
            n = self.zone.node_factory()
            self.zone.nodes[name] = n
        try:
            rd = dns.rdata.from_text(rdclass, rdtype, self.tok,
                                     self.current_origin, False)
        except dns.exception.SyntaxError:
            # Catch and reraise.
            (ty, va) = sys.exc_info()[:2]
            raise va
        except:
            # All exceptions that occur in the processing of rdata
            # are treated as syntax errors.  This is not strictly
            # correct, but it is correct almost all of the time.
            # We convert them to syntax errors so that we can emit
            # helpful filename:line info.
            (ty, va) = sys.exc_info()[:2]
            raise dns.exception.SyntaxError("caught exception %s: %s" % (str(ty), str(va)))

        rd.choose_relativity(self.zone.origin, self.relativize)
        covers = rd.covers()
        rds = n.find_rdataset(rdclass, rdtype, covers, True)
        rds.add(rd, ttl)

    def _parse_modify(self, side):
        # Here we catch everything in '{' '}' in a group so we can replace it
        # with ''.
        is_generate1 = re.compile("^.*\$({(\+|-?)(\d+),(\d+),(.)}).*$")
        is_generate2 = re.compile("^.*\$({(\+|-?)(\d+)}).*$")
        is_generate3 = re.compile("^.*\$({(\+|-?)(\d+),(\d+)}).*$")
        # Sometimes there are modifiers in the hostname. These come after
        # the dollar sign. They are in the form: ${offset[,width[,base]]}.
        # Make names
        g1 = is_generate1.match(side)
        if g1:
            mod, sign, offset, width, base = g1.groups()
            if sign == '':
                sign = '+'
        g2 = is_generate2.match(side)
        if g2:
            mod, sign, offset = g2.groups()
            if sign == '':
                sign = '+'
            width = 0
            base = 'd'
        g3 = is_generate3.match(side)
        if g3:
            mod, sign, offset, width = g1.groups()
            if sign == '':
                sign = '+'
            width = g1.groups()[2]
            base = 'd'

        if not (g1 or g2 or g3):
            mod = ''
            sign = '+'
            offset = 0
            width = 0
            base = 'd'

        if base != 'd':
            raise NotImplemented

        return mod, sign, offset, width, base

    def _generate_line(self):
        # range lhs [ttl] [class] type rhs [ comment ]
        """Process one line containing the GENERATE statement from a DNS
        master file."""
        if self.current_origin is None:
            raise UnknownOrigin

        token = self.tok.get()
        # Range (required)
        try:
            start, stop, step = dns.grange.from_text(token.value)
            token = self.tok.get()
            if not token.is_identifier():
                raise dns.exception.SyntaxError
        except:
            raise dns.exception.SyntaxError

        # lhs (required)
        try:
            lhs = token.value
            token = self.tok.get()
            if not token.is_identifier():
                raise dns.exception.SyntaxError
        except:
            raise dns.exception.SyntaxError

        # TTL
        try:
            ttl = dns.ttl.from_text(token.value)
            token = self.tok.get()
            if not token.is_identifier():
                raise dns.exception.SyntaxError
        except dns.ttl.BadTTL:
            ttl = self.ttl
        # Class
        try:
            rdclass = dns.rdataclass.from_text(token.value)
            token = self.tok.get()
            if not token.is_identifier():
                raise dns.exception.SyntaxError
        except dns.exception.SyntaxError:
            raise dns.exception.SyntaxError
        except:
            rdclass = self.zone.rdclass
        if rdclass != self.zone.rdclass:
            raise dns.exception.SyntaxError("RR class is not zone's class")
        # Type
        try:
            rdtype = dns.rdatatype.from_text(token.value)
            token = self.tok.get()
            if not token.is_identifier():
                raise dns.exception.SyntaxError
        except:
            raise dns.exception.SyntaxError("unknown rdatatype '%s'" %
                    token.value)

        # lhs (required)
        try:
            rhs = token.value
        except:
            raise dns.exception.SyntaxError


        lmod, lsign, loffset, lwidth, lbase = self._parse_modify(lhs)
        rmod, rsign, roffset, rwidth, rbase = self._parse_modify(rhs)
        for i in range(start, stop + 1, step):
            # +1 because bind is inclusive and python is exclusive

            if lsign == '+':
                lindex = i + int(loffset)
            elif lsign == '-':
                lindex = i - int(loffset)

            if rsign == '-':
                rindex = i - int(roffset)
            elif rsign == '+':
                rindex = i + int(roffset)

            lzfindex = str(lindex).zfill(int(lwidth))
            rzfindex = str(rindex).zfill(int(rwidth))


            name = lhs.replace('$%s' % (lmod), lzfindex)
            rdata = rhs.replace('$%s' % (rmod), rzfindex)

            self.last_name = dns.name.from_text(name, self.current_origin)
            name = self.last_name
            if not name.is_subdomain(self.zone.origin):
                self._eat_line()
                return
            if self.relativize:
                name = name.relativize(self.zone.origin)

            n = self.zone.nodes.get(name)
            if n is None:
                n = self.zone.node_factory()
                self.zone.nodes[name] = n
            try:
                rd = dns.rdata.from_text(rdclass, rdtype, rdata,
                                         self.current_origin, False)
            except dns.exception.SyntaxError:
                # Catch and reraise.
                (ty, va) = sys.exc_info()[:2]
                raise va
            except:
                # All exceptions that occur in the processing of rdata
                # are treated as syntax errors.  This is not strictly
                # correct, but it is correct almost all of the time.
                # We convert them to syntax errors so that we can emit
                # helpful filename:line info.
                (ty, va) = sys.exc_info()[:2]
                raise dns.exception.SyntaxError("caught exception %s: %s" %
                        (str(ty), str(va)))

            rd.choose_relativity(self.zone.origin, self.relativize)
            covers = rd.covers()
            rds = n.find_rdataset(rdclass, rdtype, covers, True)
            rds.add(rd, ttl)

    def read(self):
        """Read a DNS master file and build a zone object.

        @raises dns.zone.NoSOA: No SOA RR was found at the zone origin
        @raises dns.zone.NoNS: No NS RRset was found at the zone origin
        """

        try:
            while 1:
                token = self.tok.get(True, True)
                if token.is_eof():
                    if not self.current_file is None:
                        self.current_file.close()
                    if len(self.saved_state) > 0:
                        (self.tok,
                         self.current_origin,
                         self.last_name,
                         self.current_file,
                         self.ttl) = self.saved_state.pop(-1)
                        continue
                    break
                elif token.is_eol():
                    continue
                elif token.is_comment():
                    self.tok.get_eol()
                    continue
                elif token.value[0] == '$':
                    u = token.value.upper()
                    if u == '$TTL':
                        token = self.tok.get()
                        if not token.is_identifier():
                            raise dns.exception.SyntaxError("bad $TTL")
                        self.ttl = dns.ttl.from_text(token.value)
                        self.tok.get_eol()
                    elif u == '$ORIGIN':
                        self.current_origin = self.tok.get_name()
                        self.tok.get_eol()
                        if self.zone.origin is None:
                            self.zone.origin = self.current_origin
                    elif u == '$INCLUDE' and self.allow_include:
                        token = self.tok.get()
                        filename = token.value
                        token = self.tok.get()
                        if token.is_identifier():
                            new_origin = dns.name.from_text(token.value, \
                                                            self.current_origin)
                            self.tok.get_eol()
                        elif not token.is_eol_or_eof():
                            raise dns.exception.SyntaxError("bad origin in $INCLUDE")
                        else:
                            new_origin = self.current_origin
                        self.saved_state.append((self.tok,
                                                 self.current_origin,
                                                 self.last_name,
                                                 self.current_file,
                                                 self.ttl))
                        self.current_file = file(filename, 'r')
                        self.tok = dns.tokenizer.Tokenizer(self.current_file,
                                                           filename)
                        self.current_origin = new_origin
                    elif u == '$GENERATE':
                        self._generate_line()
                    else:
                        raise dns.exception.SyntaxError("Unknown master file directive '" + u + "'")
                    continue
                self.tok.unget(token)
                self._rr_line()
        except dns.exception.SyntaxError, detail:
            (filename, line_number) = self.tok.where()
            if detail is None:
                detail = "syntax error"
            raise dns.exception.SyntaxError("%s:%d: %s" % (filename, line_number, detail))

        # Now that we're done reading, do some basic checking of the zone.
        if self.check_origin:
            self.zone.check_origin()

def from_text(text, origin = None, rdclass = dns.rdataclass.IN,
              relativize = True, zone_factory=Zone, filename=None,
              allow_include=False, check_origin=True):
    """Build a zone object from a master file format string.

    @param text: the master file format input
    @type text: string.
    @param origin: The origin of the zone; if not specified, the first
    $ORIGIN statement in the master file will determine the origin of the
    zone.
    @type origin: dns.name.Name object or string
    @param rdclass: The zone's rdata class; the default is class IN.
    @type rdclass: int
    @param relativize: should names be relativized?  The default is True
    @type relativize: bool
    @param zone_factory: The zone factory to use
    @type zone_factory: function returning a Zone
    @param filename: The filename to emit when describing where an error
    occurred; the default is '<string>'.
    @type filename: string
    @param allow_include: is $INCLUDE allowed?
    @type allow_include: bool
    @param check_origin: should sanity checks of the origin node be done?
    The default is True.
    @type check_origin: bool
    @raises dns.zone.NoSOA: No SOA RR was found at the zone origin
    @raises dns.zone.NoNS: No NS RRset was found at the zone origin
    @rtype: dns.zone.Zone object
    """

    # 'text' can also be a file, but we don't publish that fact
    # since it's an implementation detail.  The official file
    # interface is from_file().

    if filename is None:
        filename = '<string>'
    tok = dns.tokenizer.Tokenizer(text, filename)
    reader = _MasterReader(tok, origin, rdclass, relativize, zone_factory,
                           allow_include=allow_include,
                           check_origin=check_origin)
    reader.read()
    return reader.zone

def from_file(f, origin = None, rdclass = dns.rdataclass.IN,
              relativize = True, zone_factory=Zone, filename=None,
              allow_include=True, check_origin=True):
    """Read a master file and build a zone object.

    @param f: file or string.  If I{f} is a string, it is treated
    as the name of a file to open.
    @param origin: The origin of the zone; if not specified, the first
    $ORIGIN statement in the master file will determine the origin of the
    zone.
    @type origin: dns.name.Name object or string
    @param rdclass: The zone's rdata class; the default is class IN.
    @type rdclass: int
    @param relativize: should names be relativized?  The default is True
    @type relativize: bool
    @param zone_factory: The zone factory to use
    @type zone_factory: function returning a Zone
    @param filename: The filename to emit when describing where an error
    occurred; the default is '<file>', or the value of I{f} if I{f} is a
    string.
    @type filename: string
    @param allow_include: is $INCLUDE allowed?
    @type allow_include: bool
    @param check_origin: should sanity checks of the origin node be done?
    The default is True.
    @type check_origin: bool
    @raises dns.zone.NoSOA: No SOA RR was found at the zone origin
    @raises dns.zone.NoNS: No NS RRset was found at the zone origin
    @rtype: dns.zone.Zone object
    """

    if sys.hexversion >= 0x02030000:
        # allow Unicode filenames; turn on universal newline support
        str_type = basestring
        opts = 'rU'
    else:
        str_type = str
        opts = 'r'
    if isinstance(f, str_type):
        if filename is None:
            filename = f
        f = file(f, opts)
        want_close = True
    else:
        if filename is None:
            filename = '<file>'
        want_close = False

    try:
        z = from_text(f, origin, rdclass, relativize, zone_factory,
                      filename, allow_include, check_origin)
    finally:
        if want_close:
            f.close()
    return z

def from_xfr(xfr, zone_factory=Zone, relativize=True, check_origin=True):
    """Convert the output of a zone transfer generator into a zone object.

    @param xfr: The xfr generator
    @type xfr: generator of dns.message.Message objects
    @param relativize: should names be relativized?  The default is True.
    It is essential that the relativize setting matches the one specified
    to dns.query.xfr().
    @type relativize: bool
    @param check_origin: should sanity checks of the origin node be done?
    The default is True.
    @type check_origin: bool
    @raises dns.zone.NoSOA: No SOA RR was found at the zone origin
    @raises dns.zone.NoNS: No NS RRset was found at the zone origin
    @rtype: dns.zone.Zone object
    """

    z = None
    for r in xfr:
        if z is None:
            if relativize:
                origin = r.origin
            else:
                origin = r.answer[0].name
            rdclass = r.answer[0].rdclass
            z = zone_factory(origin, rdclass, relativize=relativize)
        for rrset in r.answer:
            znode = z.nodes.get(rrset.name)
            if not znode:
                znode = z.node_factory()
                z.nodes[rrset.name] = znode
            zrds = znode.find_rdataset(rrset.rdclass, rrset.rdtype,
                                       rrset.covers, True)
            zrds.update_ttl(rrset.ttl)
            for rd in rrset:
                rd.choose_relativity(z.origin, relativize)
                zrds.add(rd)
    if check_origin:
        z.check_origin()
    return z

########NEW FILE########
__FILENAME__ = ddns
#!/usr/bin/env python

#
# Use a TSIG-signed DDNS update to update our hostname-to-address
# mapping.
#
# usage: ddns.py <ip-address>
#
# On linux systems, you can automatically update your DNS any time an
# interface comes up by adding an ifup-local script that invokes this
# python code.
#
# E.g. on my systems I have this
#
#	#!/bin/sh
#
#	DEVICE=$1
#
#	if [ "X${DEVICE}" == "Xeth0" ]; then
#        	IPADDR=`LANG= LC_ALL= ifconfig ${DEVICE} | grep 'inet addr' |
#                	awk -F: '{ print $2 } ' | awk '{ print $1 }'`
#		/usr/local/sbin/ddns.py $IPADDR
#	fi
#
# in /etc/ifup-local.
#

import sys

import dns.update
import dns.query
import dns.tsigkeyring

#
# Replace the keyname and secret with appropriate values for your
# configuration.
#
keyring = dns.tsigkeyring.from_text({
    'keyname.' : 'NjHwPsMKjdN++dOfE5iAiQ=='
    })

#
# Replace "example." with your domain, and "host" with your hostname.
#
update = dns.update.Update('example.', keyring=keyring)
update.replace('host', 300, 'A', sys.argv[1])

#
# Replace "10.0.0.1" with the IP address of your master server.
#
response = dns.query.tcp(update, '10.0.0.1', timeout=10)

########NEW FILE########
__FILENAME__ = e164
#!/usr/bin/env python

import dns.e164
n = dns.e164.from_e164("+1 555 1212")
print n
print dns.e164.to_e164(n)

########NEW FILE########
__FILENAME__ = mx
#!/usr/bin/env python

import dns.resolver

answers = dns.resolver.query('nominum.com', 'MX')
for rdata in answers:
    print 'Host', rdata.exchange, 'has preference', rdata.preference

########NEW FILE########
__FILENAME__ = name
#!/usr/bin/env python

import dns.name

n = dns.name.from_text('www.dnspython.org')
o = dns.name.from_text('dnspython.org')
print n.is_subdomain(o)         # True
print n.is_superdomain(o)       # False
print n > o                     # True
rel = n.relativize(o)           # rel is the relative name www
n2 = rel + o
print n2 == n                   # True
print n.labels                  # ['www', 'dnspython', 'org', '']

########NEW FILE########
__FILENAME__ = reverse
#!/usr/bin/env python

# Usage: reverse.py <zone_filename>...
#
# This demo script will load in all of the zones specified by the
# filenames on the command line, find all the A RRs in them, and
# construct a reverse mapping table that maps each IP address used to
# the list of names mapping to that address.  The table is then sorted
# nicely and printed.
#
# Note!  The zone name is taken from the basename of the filename, so
# you must use filenames like "/wherever/you/like/dnspython.org" and
# not something like "/wherever/you/like/foo.db" (unless you're
# working with the ".db" GTLD, of course :)).
#
# If this weren't a demo script, there'd be a way of specifying the
# origin for each zone instead of constructing it from the filename.

import dns.zone
import dns.ipv4
import os.path
import sys

reverse_map = {}

for filename in sys.argv[1:]:
    zone = dns.zone.from_file(filename, os.path.basename(filename),
                              relativize=False)
    for (name, ttl, rdata) in zone.iterate_rdatas('A'):
        try:
	    reverse_map[rdata.address].append(name.to_text())
	except KeyError:
	    reverse_map[rdata.address] = [name.to_text()]

keys = reverse_map.keys()
keys.sort(lambda a1, a2: cmp(dns.ipv4.inet_aton(a1), dns.ipv4.inet_aton(a2)))
for k in keys:
    v = reverse_map[k]
    v.sort()
    print k, v

########NEW FILE########
__FILENAME__ = reverse_name
#!/usr/bin/env python

import dns.reversename
n = dns.reversename.from_address("127.0.0.1")
print n
print dns.reversename.to_address(n)

########NEW FILE########
__FILENAME__ = xfr
#!/usr/bin/env python

import dns.query
import dns.resolver
import dns.zone

soa_answer = dns.resolver.query('dnspython.org', 'SOA')
master_answer = dns.resolver.query(soa_answer[0].mname, 'A')

z = dns.zone.from_xfr(dns.query.xfr(master_answer[0].address, 'dnspython.org'))
names = z.nodes.keys()
names.sort()
for n in names:
        print z[n].to_text(n)

########NEW FILE########
__FILENAME__ = zonediff
#!/usr/bin/env python
# 
# Small library and commandline tool to do logical diffs of zonefiles
# ./zonediff -h gives you help output
#
# Requires dnspython to do all the heavy lifting
#
# (c)2009 Dennis Kaarsemaker <dennis@kaarsemaker.net>
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
# 
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
"""See diff_zones.__doc__ for more information"""

__all__ = ['diff_zones', 'format_changes_plain', 'format_changes_html']

try:
    import dns.zone
except ImportError:
    import sys
    sys.stderr.write("Please install dnspython")
    sys.exit(1)

def diff_zones(zone1, zone2, ignore_ttl=False, ignore_soa=False):
    """diff_zones(zone1, zone2, ignore_ttl=False, ignore_soa=False) -> changes
    Compares two dns.zone.Zone objects and returns a list of all changes
    in the format (name, oldnode, newnode).

    If ignore_ttl is true, a node will not be added to this list if the
    only change is its TTL.
    
    If ignore_soa is true, a node will not be added to this list if the
    only changes is a change in a SOA Rdata set.

    The returned nodes do include all Rdata sets, including unchanged ones.
    """

    changes = []
    for name in zone1:
        name = str(name)
        n1 = zone1.get_node(name)
        n2 = zone2.get_node(name)
        if not n2:
            changes.append((str(name), n1, n2))
        elif _nodes_differ(n1, n2, ignore_ttl, ignore_soa):
            changes.append((str(name), n1, n2))

    for name in zone2:
        n1 = zone1.get_node(name)
        if not n1:
            n2 = zone2.get_node(name)
            changes.append((str(name), n1, n2))
    return changes

def _nodes_differ(n1, n2, ignore_ttl, ignore_soa):
    if ignore_soa or not ignore_ttl:
        # Compare datasets directly
        for r in n1.rdatasets:
            if ignore_soa and r.rdtype == dns.rdatatype.SOA:
                continue
            if r not in n2.rdatasets:
                return True
            if not ignore_ttl:
                return r.ttl != n2.find_rdataset(r.rdclass, r.rdtype).ttl

        for r in n2.rdatasets:
            if ignore_soa and r.rdtype == dns.rdatatype.SOA:
                continue
            if r not in n1.rdatasets:
                return True
    else:
        return n1 != n2

def format_changes_plain(oldf, newf, changes, ignore_ttl=False):
    """format_changes(oldfile, newfile, changes, ignore_ttl=False) -> str
    Given 2 filenames and a list of changes from diff_zones, produce diff-like
    output. If ignore_ttl is True, TTL-only changes are not displayed"""

    ret = "--- %s\n+++ %s\n" % (oldf, newf)
    for name, old, new in changes:
        ret +=  "@ %s\n" % name
        if not old:
            for r in new.rdatasets:
                ret += "+ %s\n" % str(r).replace('\n','\n+ ')
        elif not new:
            for r in old.rdatasets:
                ret += "- %s\n" % str(r).replace('\n','\n+ ')
        else:
            for r in old.rdatasets:
                if r not in new.rdatasets or (r.ttl != new.find_rdataset(r.rdclass, r.rdtype).ttl and not ignore_ttl):
                    ret += "- %s\n" % str(r).replace('\n','\n+ ')
            for r in new.rdatasets:
                if r not in old.rdatasets or (r.ttl != old.find_rdataset(r.rdclass, r.rdtype).ttl and not ignore_ttl):
                    ret += "+ %s\n" % str(r).replace('\n','\n+ ')
    return ret

def format_changes_html(oldf, newf, changes, ignore_ttl=False):
    """format_changes(oldfile, newfile, changes, ignore_ttl=False) -> str
    Given 2 filenames and a list of changes from diff_zones, produce nice html
    output. If ignore_ttl is True, TTL-only changes are not displayed"""

    ret = '''<table class="zonediff">
  <thead>
    <tr>
      <th>&nbsp;</th>
      <th class="old">%s</th>
      <th class="new">%s</th>
    </tr>
  </thead>
  <tbody>\n''' % (oldf, newf)

    for name, old, new in changes:
        ret +=  '    <tr class="rdata">\n      <td class="rdname">%s</td>\n' % name
        if not old:
            for r in new.rdatasets:
                ret += '      <td class="old">&nbsp;</td>\n      <td class="new">%s</td>\n' % str(r).replace('\n','<br />')
        elif not new:
            for r in old.rdatasets:
                ret += '      <td class="old">%s</td>\n      <td class="new">&nbsp;</td>\n' % str(r).replace('\n','<br />')
        else:
            ret += '      <td class="old">'
            for r in old.rdatasets:
                if r not in new.rdatasets or (r.ttl != new.find_rdataset(r.rdclass, r.rdtype).ttl and not ignore_ttl):
                    ret += str(r).replace('\n','<br />')
            ret += '</td>\n'
            ret += '      <td class="new">'
            for r in new.rdatasets:
                if r not in old.rdatasets or (r.ttl != old.find_rdataset(r.rdclass, r.rdtype).ttl and not ignore_ttl):
                    ret += str(r).replace('\n','<br />')
            ret += '</td>\n'
        ret += '    </tr>\n'
    return ret + '  </tbody>\n</table>'

# Make this module usable as a script too.
if __name__ == '__main__':
    import optparse
    import subprocess
    import sys
    import traceback

    usage = """%prog zonefile1 zonefile2 - Show differences between zones in a diff-like format
%prog [--git|--bzr|--rcs] zonefile rev1 [rev2] - Show differences between two revisions of a zonefile

The differences shown will be logical differences, not textual differences.
"""
    p = optparse.OptionParser(usage=usage)
    p.add_option('-s', '--ignore-soa', action="store_true", default=False, dest="ignore_soa",
                 help="Ignore SOA-only changes to records")
    p.add_option('-t', '--ignore-ttl', action="store_true", default=False, dest="ignore_ttl",
                 help="Ignore TTL-only changes to Rdata")
    p.add_option('-T', '--traceback', action="store_true", default=False, dest="tracebacks",
                 help="Show python tracebacks when errors occur")
    p.add_option('-H', '--html', action="store_true", default=False, dest="html",
                 help="Print HTML output")
    p.add_option('-g', '--git', action="store_true", default=False, dest="use_git",
                 help="Use git revisions instead of real files")
    p.add_option('-b', '--bzr', action="store_true", default=False, dest="use_bzr",
                 help="Use bzr revisions instead of real files")
    p.add_option('-r', '--rcs', action="store_true", default=False, dest="use_rcs",
                 help="Use rcs revisions instead of real files")
    opts, args = p.parse_args()
    opts.use_vc = opts.use_git or opts.use_bzr or opts.use_rcs

    def _open(what, err):
        if isinstance(what, basestring):
            # Open as normal file
            try:
                return open(what, 'rb')
            except:
                sys.stderr.write(err + "\n")
                if opts.tracebacks:
                    traceback.print_exc()
        else:
            # Must be a list, open subprocess
            try:
                proc = subprocess.Popen(what, stdout=subprocess.PIPE)
                proc.wait()
                if proc.returncode == 0:
                    return proc.stdout
                sys.stderr.write(err + "\n")
            except:
                sys.stderr.write(err + "\n")
                if opts.tracebacks:
                    traceback.print_exc()

    if not opts.use_vc and len(args) != 2:
        p.print_help()
        sys.exit(64)
    if opts.use_vc and len(args) not in (2,3):
        p.print_help()
        sys.exit(64)

    # Open file desriptors
    if not opts.use_vc:
        oldn, newn = args
    else:
        if len(args) == 3:
            filename, oldr, newr = args
            oldn = "%s:%s" % (oldr, filename)
            newn = "%s:%s" % (newr, filename)
        else:
            filename, oldr = args
            newr = None
            oldn = "%s:%s" % (oldr, filename)
            newn = filename

        
    old, new = None, None
    oldz, newz = None, None
    if opts.use_bzr:
        old = _open(["bzr", "cat", "-r" + oldr, filename],
                    "Unable to retrieve revision %s of %s" % (oldr, filename))
        if newr != None:
            new = _open(["bzr", "cat", "-r" + newr, filename],
                        "Unable to retrieve revision %s of %s" % (newr, filename))
    elif opts.use_git:
        old = _open(["git", "show", oldn],
                    "Unable to retrieve revision %s of %s" % (oldr, filename))
        if newr != None:
            new = _open(["git", "show", newn],
                        "Unable to retrieve revision %s of %s" % (newr, filename))
    elif opts.use_rcs:
        old = _open(["co", "-q", "-p", "-r" + oldr, filename],
                    "Unable to retrieve revision %s of %s" % (oldr, filename))
        if newr != None:
            new = _open(["co", "-q", "-p", "-r" + newr, filename],
                        "Unable to retrieve revision %s of %s" % (newr, filename))
    if not opts.use_vc:
        old = _open(oldn, "Unable to open %s" % oldn)
    if not opts.use_vc or newr == None:
        new = _open(newn, "Unable to open %s" % newn)

    if not old or not new:
        sys.exit(65)

    # Parse the zones
    try:
        oldz = dns.zone.from_file(old, origin = '.', check_origin=False)
    except dns.exception.DNSException:
        sys.stderr.write("Incorrect zonefile: %s\n", old)
        if opts.tracebacks:
            traceback.print_exc()
    try:
        newz = dns.zone.from_file(new, origin = '.', check_origin=False)
    except dns.exception.DNSException:
        sys.stderr.write("Incorrect zonefile: %s\n" % new)
        if opts.tracebacks:
            traceback.print_exc()
    if not oldz or not newz:
        sys.exit(65)

    changes = diff_zones(oldz, newz, opts.ignore_ttl, opts.ignore_soa)
    changes.sort()

    if not changes:
        sys.exit(0)
    if opts.html:
        print format_changes_html(oldn, newn, changes, opts.ignore_ttl)
    else:
        print format_changes_plain(oldn, newn, changes, opts.ignore_ttl)
    sys.exit(1)

########NEW FILE########
__FILENAME__ = bugs
# Copyright (C) 2006, 2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import unittest

import dns.rdata
import dns.rdataclass
import dns.rdatatype
import dns.ttl

class BugsTestCase(unittest.TestCase):

    def test_float_LOC(self):
        rdata = dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.LOC,
                                    "30 30 0.000 N 100 30 0.000 W 10.00m 20m 2000m 20m")
        self.failUnless(rdata.float_latitude == 30.5)
        self.failUnless(rdata.float_longitude == -100.5)

    def test_SOA_BIND8_TTL(self):
        rdata1 = dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.SOA,
                                     "a b 100 1s 1m 1h 1d")
        rdata2 = dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.SOA,
                                     "a b 100 1 60 3600 86400")
        self.failUnless(rdata1 == rdata2)

    def test_TTL_bounds_check(self):
        def bad():
            ttl = dns.ttl.from_text("2147483648")
        self.failUnlessRaises(dns.ttl.BadTTL, bad)

    def test_empty_NSEC3_window(self):
        rdata = dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.NSEC3,
                                    "1 0 100 ABCD SCBCQHKU35969L2A68P3AD59LHF30715")
        self.failUnless(rdata.windows == [])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = dnssec
# Copyright (C) 2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import unittest

import dns.dnssec
import dns.name
import dns.rdata
import dns.rdataclass
import dns.rdatatype
import dns.rrset

abs_dnspython_org = dns.name.from_text('dnspython.org')

abs_keys = { abs_dnspython_org :
             dns.rrset.from_text('dnspython.org.', 3600, 'IN', 'DNSKEY',
                                 '257 3 5 AwEAAenVTr9L1OMlL1/N2ta0Qj9LLLnnmFWIr1dJoAsWM9BQfsbV7kFZ XbAkER/FY9Ji2o7cELxBwAsVBuWn6IUUAJXLH74YbC1anY0lifjgt29z SwDzuB7zmC7yVYZzUunBulVW4zT0tg1aePbpVL2EtTL8VzREqbJbE25R KuQYHZtFwG8S4iBxJUmT2Bbd0921LLxSQgVoFXlQx/gFV2+UERXcJ5ce iX6A6wc02M/pdg/YbJd2rBa0MYL3/Fz/Xltre0tqsImZGxzi6YtYDs45 NC8gH+44egz82e2DATCVM1ICPmRDjXYTLldQiWA2ZXIWnK0iitl5ue24 7EsWJefrIhE=',
                                 '256 3 5 AwEAAdSSghOGjU33IQZgwZM2Hh771VGXX05olJK49FxpSyuEAjDBXY58 LGU9R2Zgeecnk/b9EAhFu/vCV9oECtiTCvwuVAkt9YEweqYDluQInmgP NGMJCKdSLlnX93DkjDw8rMYv5dqXCuSGPlKChfTJOLQxIAxGloS7lL+c 0CTZydAF')
         }

abs_keys_duplicate_keytag = { abs_dnspython_org :
             dns.rrset.from_text('dnspython.org.', 3600, 'IN', 'DNSKEY',
                                 '257 3 5 AwEAAenVTr9L1OMlL1/N2ta0Qj9LLLnnmFWIr1dJoAsWM9BQfsbV7kFZ XbAkER/FY9Ji2o7cELxBwAsVBuWn6IUUAJXLH74YbC1anY0lifjgt29z SwDzuB7zmC7yVYZzUunBulVW4zT0tg1aePbpVL2EtTL8VzREqbJbE25R KuQYHZtFwG8S4iBxJUmT2Bbd0921LLxSQgVoFXlQx/gFV2+UERXcJ5ce iX6A6wc02M/pdg/YbJd2rBa0MYL3/Fz/Xltre0tqsImZGxzi6YtYDs45 NC8gH+44egz82e2DATCVM1ICPmRDjXYTLldQiWA2ZXIWnK0iitl5ue24 7EsWJefrIhE=',
                                 '256 3 5 AwEAAdSSg++++THIS/IS/NOT/THE/CORRECT/KEY++++++++++++++++ ++++++++++++++++++++++++++++++++++++++++++++++++++++++++ ++++++++++++++++++++++++++++++++++++++++++++++++++++++++ AaOSydAF',
                                 '256 3 5 AwEAAdSSghOGjU33IQZgwZM2Hh771VGXX05olJK49FxpSyuEAjDBXY58 LGU9R2Zgeecnk/b9EAhFu/vCV9oECtiTCvwuVAkt9YEweqYDluQInmgP NGMJCKdSLlnX93DkjDw8rMYv5dqXCuSGPlKChfTJOLQxIAxGloS7lL+c 0CTZydAF')
         }

rel_keys = { dns.name.empty :
             dns.rrset.from_text('@', 3600, 'IN', 'DNSKEY',
                                 '257 3 5 AwEAAenVTr9L1OMlL1/N2ta0Qj9LLLnnmFWIr1dJoAsWM9BQfsbV7kFZ XbAkER/FY9Ji2o7cELxBwAsVBuWn6IUUAJXLH74YbC1anY0lifjgt29z SwDzuB7zmC7yVYZzUunBulVW4zT0tg1aePbpVL2EtTL8VzREqbJbE25R KuQYHZtFwG8S4iBxJUmT2Bbd0921LLxSQgVoFXlQx/gFV2+UERXcJ5ce iX6A6wc02M/pdg/YbJd2rBa0MYL3/Fz/Xltre0tqsImZGxzi6YtYDs45 NC8gH+44egz82e2DATCVM1ICPmRDjXYTLldQiWA2ZXIWnK0iitl5ue24 7EsWJefrIhE=',
                                 '256 3 5 AwEAAdSSghOGjU33IQZgwZM2Hh771VGXX05olJK49FxpSyuEAjDBXY58 LGU9R2Zgeecnk/b9EAhFu/vCV9oECtiTCvwuVAkt9YEweqYDluQInmgP NGMJCKdSLlnX93DkjDw8rMYv5dqXCuSGPlKChfTJOLQxIAxGloS7lL+c 0CTZydAF')
         }

when = 1290250287

abs_soa = dns.rrset.from_text('dnspython.org.', 3600, 'IN', 'SOA',
                              'howl.dnspython.org. hostmaster.dnspython.org. 2010020047 3600 1800 604800 3600')

abs_other_soa = dns.rrset.from_text('dnspython.org.', 3600, 'IN', 'SOA',
                                    'foo.dnspython.org. hostmaster.dnspython.org. 2010020047 3600 1800 604800 3600')

abs_soa_rrsig = dns.rrset.from_text('dnspython.org.', 3600, 'IN', 'RRSIG',
                                    'SOA 5 2 3600 20101127004331 20101119213831 61695 dnspython.org. sDUlltRlFTQw5ITFxOXW3TgmrHeMeNpdqcZ4EXxM9FHhIlte6V9YCnDw t6dvM9jAXdIEi03l9H/RAd9xNNW6gvGMHsBGzpvvqFQxIBR2PoiZA1mX /SWHZFdbt4xjYTtXqpyYvrMK0Dt7bUYPadyhPFCJ1B+I8Zi7B5WJEOd0 8vs=')

rel_soa = dns.rrset.from_text('@', 3600, 'IN', 'SOA',
                              'howl hostmaster 2010020047 3600 1800 604800 3600')

rel_other_soa = dns.rrset.from_text('@', 3600, 'IN', 'SOA',
                                    'foo hostmaster 2010020047 3600 1800 604800 3600')

rel_soa_rrsig = dns.rrset.from_text('@', 3600, 'IN', 'RRSIG',
                                    'SOA 5 2 3600 20101127004331 20101119213831 61695 @ sDUlltRlFTQw5ITFxOXW3TgmrHeMeNpdqcZ4EXxM9FHhIlte6V9YCnDw t6dvM9jAXdIEi03l9H/RAd9xNNW6gvGMHsBGzpvvqFQxIBR2PoiZA1mX /SWHZFdbt4xjYTtXqpyYvrMK0Dt7bUYPadyhPFCJ1B+I8Zi7B5WJEOd0 8vs=')

sep_key = dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.DNSKEY,
                              '257 3 5 AwEAAenVTr9L1OMlL1/N2ta0Qj9LLLnnmFWIr1dJoAsWM9BQfsbV7kFZ XbAkER/FY9Ji2o7cELxBwAsVBuWn6IUUAJXLH74YbC1anY0lifjgt29z SwDzuB7zmC7yVYZzUunBulVW4zT0tg1aePbpVL2EtTL8VzREqbJbE25R KuQYHZtFwG8S4iBxJUmT2Bbd0921LLxSQgVoFXlQx/gFV2+UERXcJ5ce iX6A6wc02M/pdg/YbJd2rBa0MYL3/Fz/Xltre0tqsImZGxzi6YtYDs45 NC8gH+44egz82e2DATCVM1ICPmRDjXYTLldQiWA2ZXIWnK0iitl5ue24 7EsWJefrIhE=')

good_ds = dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.DS,
                              '57349 5 2 53A79A3E7488AB44FFC56B2D1109F0699D1796DD977E72108B841F96 E47D7013')

when2 = 1290425644

abs_example = dns.name.from_text('example')

abs_dsa_keys = { abs_example :
                 dns.rrset.from_text('example.', 86400, 'IN', 'DNSKEY',
                                     '257 3 3 CI3nCqyJsiCJHTjrNsJOT4RaszetzcJPYuoH3F9ZTVt3KJXncCVR3bwn 1w0iavKljb9hDlAYSfHbFCp4ic/rvg4p1L8vh5s8ToMjqDNl40A0hUGQ Ybx5hsECyK+qHoajilUX1phYSAD8d9WAGO3fDWzUPBuzR7o85NiZCDxz yXuNVfni0uhj9n1KYhEO5yAbbruDGN89wIZcxMKuQsdUY2GYD93ssnBv a55W6XRABYWayKZ90WkRVODLVYLSn53Pj/wwxGH+XdhIAZJXimrZL4yl My7rtBsLMqq8Ihs4Tows7LqYwY7cp6y/50tw6pj8tFqMYcPUjKZV36l1 M/2t5BVg3i7IK61Aidt6aoC3TDJtzAxg3ZxfjZWJfhHjMJqzQIfbW5b9 q1mjFsW5EUv39RaNnX+3JWPRLyDqD4pIwDyqfutMsdk/Py3paHn82FGp CaOg+nicqZ9TiMZURN/XXy5JoXUNQ3RNvbHCUiPUe18KUkY6mTfnyHld 1l9YCWmzXQVClkx/hOYxjJ4j8Ife58+Obu5X',
                                     '256 3 3 CJE1yb9YRQiw5d2xZrMUMR+cGCTt1bp1KDCefmYKmS+Z1+q9f42ETVhx JRiQwXclYwmxborzIkSZegTNYIV6mrYwbNB27Q44c3UGcspb3PiOw5TC jNPRYEcdwGvDZ2wWy+vkSV/S9tHXY8O6ODiE6abZJDDg/RnITyi+eoDL R3KZ5n/V1f1T1b90rrV6EewhBGQJpQGDogaXb2oHww9Tm6NfXyo7SoMM pbwbzOckXv+GxRPJIQNSF4D4A9E8XCksuzVVdE/0lr37+uoiAiPia38U 5W2QWe/FJAEPLjIp2eTzf0TrADc1pKP1wrA2ASpdzpm/aX3IB5RPp8Ew S9U72eBFZJAUwg635HxJVxH1maG6atzorR566E+e0OZSaxXS9o1o6QqN 3oPlYLGPORDiExilKfez3C/x/yioOupW9K5eKF0gmtaqrHX0oq9s67f/ RIM2xVaKHgG9Vf2cgJIZkhv7sntujr+E4htnRmy9P9BxyFxsItYxPI6Z bzygHAZpGhlI/7ltEGlIwKxyTK3ZKBm67q7B')
                 }

abs_dsa_soa = dns.rrset.from_text('example.', 86400, 'IN', 'SOA',
                                  'ns1.example. hostmaster.example. 2 10800 3600 604800 86400')

abs_other_dsa_soa = dns.rrset.from_text('example.', 86400, 'IN', 'SOA',
                                        'ns1.example. hostmaster.example. 2 10800 3600 604800 86401')

abs_dsa_soa_rrsig = dns.rrset.from_text('example.', 86400, 'IN', 'RRSIG',
                                        'SOA 3 1 86400 20101129143231 20101122112731 42088 example. CGul9SuBofsktunV8cJs4eRs6u+3NCS3yaPKvBbD+pB2C76OUXDZq9U=')

example_sep_key = dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.DNSKEY,
                                      '257 3 3 CI3nCqyJsiCJHTjrNsJOT4RaszetzcJPYuoH3F9ZTVt3KJXncCVR3bwn 1w0iavKljb9hDlAYSfHbFCp4ic/rvg4p1L8vh5s8ToMjqDNl40A0hUGQ Ybx5hsECyK+qHoajilUX1phYSAD8d9WAGO3fDWzUPBuzR7o85NiZCDxz yXuNVfni0uhj9n1KYhEO5yAbbruDGN89wIZcxMKuQsdUY2GYD93ssnBv a55W6XRABYWayKZ90WkRVODLVYLSn53Pj/wwxGH+XdhIAZJXimrZL4yl My7rtBsLMqq8Ihs4Tows7LqYwY7cp6y/50tw6pj8tFqMYcPUjKZV36l1 M/2t5BVg3i7IK61Aidt6aoC3TDJtzAxg3ZxfjZWJfhHjMJqzQIfbW5b9 q1mjFsW5EUv39RaNnX+3JWPRLyDqD4pIwDyqfutMsdk/Py3paHn82FGp CaOg+nicqZ9TiMZURN/XXy5JoXUNQ3RNvbHCUiPUe18KUkY6mTfnyHld 1l9YCWmzXQVClkx/hOYxjJ4j8Ife58+Obu5X')

example_ds_sha1 = dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.DS,
                                      '18673 3 1 71b71d4f3e11bbd71b4eff12cde69f7f9215bbe7')

example_ds_sha256 = dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.DS,
                                        '18673 3 2 eb8344cbbf07c9d3d3d6c81d10c76653e28d8611a65e639ef8f716e4e4e5d913')

when3 = 1379801800

abs_ecdsa256_keys = { abs_example :
                      dns.rrset.from_text('example.', 86400, 'IN', 'DNSKEY',
                                          "256 3 13 +3ss1sCpdARVA61DJigEsL/8quo2a8MszKtn2gkkfxgzFs8S2UHtpb4N fY+XFmNW+JK6MsCkI3jHYN8eEQUgMw==",
                                          "257 3 13 eJCEVH7AS3wnoaQpaNlAXH0W8wxymtT9P6P3qjN2ZCV641ED8pF7wZ5V yWfOpgTs6oaZevbJgehl/GaRPUgVyQ==")
                 }

abs_ecdsa256_soa = dns.rrset.from_text('example.', 86400, 'IN', 'SOA',
                                       'ns1.example. hostmaster.example. 4 10800 3600 604800 86400')

abs_other_ecdsa256_soa = dns.rrset.from_text('example.', 86400, 'IN', 'SOA',
                                             'ns1.example. hostmaster.example. 2 10800 3600 604800 86401')

abs_ecdsa256_soa_rrsig = dns.rrset.from_text('example.', 86400, 'IN', 'RRSIG',
                                             "SOA 13 1 86400 20130921221753 20130921221638 7460 example. Sm09SOGz1ULB5D/duwdE2Zpn8bWbVBM77H6N1wPkc42LevvVO+kZEjpq 2nq4GOMJcih52667GIAbMrwmU5P2MQ==")

when4 = 1379804850

abs_ecdsa384_keys = { abs_example :
                      dns.rrset.from_text('example.', 86400, 'IN', 'DNSKEY',
                                          "256 3 14 1bG8qWviKNXQX3BIuG6/T5jrP1FISiLW/8qGF6BsM9DQtWYhhZUA3Owr OAEiyHAhQwjkN2kTvWiAYoPN80Ii+5ff9/atzY4F9W50P4l75Dj9PYrL HN/hLUgWMNVc9pvA",
                                          "257 3 14 mSub2n0KRt6u2FaD5XJ3oQu0R4XvB/9vUJcyW6+oo0y+KzfQeTdkf1ro ZMVKoyWXW9zUKBYGJpMUIdbAxzrYi7f5HyZ3yDpBFz1hw9+o3CX+gtgb +RyhHfJDwwFXBid9")
                 }

abs_ecdsa384_soa = dns.rrset.from_text('example.', 86400, 'IN', 'SOA',
                                       'ns1.example. hostmaster.example. 2 10800 3600 604800 86400')

abs_other_ecdsa384_soa = dns.rrset.from_text('example.', 86400, 'IN', 'SOA',
                                             'ns1.example. hostmaster.example. 2 10800 3600 604800 86401')

abs_ecdsa384_soa_rrsig = dns.rrset.from_text('example.', 86400, 'IN', 'RRSIG',
                                             "SOA 14 1 86400 20130929021229 20130921230729 63571 example. CrnCu34EeeRz0fEhL9PLlwjpBKGYW8QjBjFQTwd+ViVLRAS8tNkcDwQE NhSV89NEjj7ze1a/JcCfcJ+/mZgnvH4NHLNg3Tf6KuLZsgs2I4kKQXEk 37oIHravPEOlGYNI")

class DNSSECValidatorTestCase(unittest.TestCase):

    def testAbsoluteRSAGood(self):
        dns.dnssec.validate(abs_soa, abs_soa_rrsig, abs_keys, None, when)

    def testDuplicateKeytag(self):
        dns.dnssec.validate(abs_soa, abs_soa_rrsig, abs_keys_duplicate_keytag, None, when)

    def testAbsoluteRSABad(self):
        def bad():
            dns.dnssec.validate(abs_other_soa, abs_soa_rrsig, abs_keys, None,
                                when)
        self.failUnlessRaises(dns.dnssec.ValidationFailure, bad)

    def testRelativeRSAGood(self):
        dns.dnssec.validate(rel_soa, rel_soa_rrsig, rel_keys,
                            abs_dnspython_org, when)

    def testRelativeRSABad(self):
        def bad():
            dns.dnssec.validate(rel_other_soa, rel_soa_rrsig, rel_keys,
                                abs_dnspython_org, when)
        self.failUnlessRaises(dns.dnssec.ValidationFailure, bad)

    def testMakeSHA256DS(self):
        ds = dns.dnssec.make_ds(abs_dnspython_org, sep_key, 'SHA256')
        self.failUnless(ds == good_ds)

    def testAbsoluteDSAGood(self):
        dns.dnssec.validate(abs_dsa_soa, abs_dsa_soa_rrsig, abs_dsa_keys, None,
                            when2)

    def testAbsoluteDSABad(self):
        def bad():
            dns.dnssec.validate(abs_other_dsa_soa, abs_dsa_soa_rrsig,
                                abs_dsa_keys, None, when2)
        self.failUnlessRaises(dns.dnssec.ValidationFailure, bad)

    def testMakeExampleSHA1DS(self):
        ds = dns.dnssec.make_ds(abs_example, example_sep_key, 'SHA1')
        self.failUnless(ds == example_ds_sha1)

    def testMakeExampleSHA256DS(self):
        ds = dns.dnssec.make_ds(abs_example, example_sep_key, 'SHA256')
        self.failUnless(ds == example_ds_sha256)

    @unittest.skipIf(not dns.dnssec._have_ecdsa,
                     "python ECDSA can not be imported")
    def testAbsoluteECDSA256Good(self):
        dns.dnssec.validate(abs_ecdsa256_soa, abs_ecdsa256_soa_rrsig,
                            abs_ecdsa256_keys, None, when3)

    @unittest.skipIf(not dns.dnssec._have_ecdsa,
                     "python ECDSA can not be imported")
    def testAbsoluteECDSA256Bad(self):
        def bad():
            dns.dnssec.validate(abs_other_ecdsa256_soa, abs_ecdsa256_soa_rrsig,
                                abs_ecdsa256_keys, None, when3)
        self.failUnlessRaises(dns.dnssec.ValidationFailure, bad)

    @unittest.skipIf(not dns.dnssec._have_ecdsa,
                     "python ECDSA can not be imported")
    def testAbsoluteECDSA384Good(self):
        dns.dnssec.validate(abs_ecdsa384_soa, abs_ecdsa384_soa_rrsig,
                            abs_ecdsa384_keys, None, when4)

    @unittest.skipIf(not dns.dnssec._have_ecdsa,
                     "python ECDSA can not be imported")
    def testAbsoluteECDSA384Bad(self):
        def bad():
            dns.dnssec.validate(abs_other_ecdsa384_soa, abs_ecdsa384_soa_rrsig,
                                abs_ecdsa384_keys, None, when4)
        self.failUnlessRaises(dns.dnssec.ValidationFailure, bad)


if __name__ == '__main__':
    import_ok = False
    try:
        import Crypto.Util.number
        import_ok = True
    except:
        pass
    if import_ok:
        unittest.main()
    else:
        print 'skipping DNSSEC tests because pycrypto is not installed'

########NEW FILE########
__FILENAME__ = flags
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import unittest

import dns.flags
import dns.rcode
import dns.opcode

class FlagsTestCase(unittest.TestCase):

    def test_rcode1(self):
        self.failUnless(dns.rcode.from_text('FORMERR') ==  dns.rcode.FORMERR)

    def test_rcode2(self):
        self.failUnless(dns.rcode.to_text(dns.rcode.FORMERR) == "FORMERR")

    def test_rcode3(self):
        self.failUnless(dns.rcode.to_flags(dns.rcode.FORMERR) == (1, 0))

    def test_rcode4(self):
        self.failUnless(dns.rcode.to_flags(dns.rcode.BADVERS) == \
                        (0, 0x01000000))

    def test_rcode6(self):
        self.failUnless(dns.rcode.from_flags(0, 0x01000000) == \
                        dns.rcode.BADVERS)

    def test_rcode6(self):
        self.failUnless(dns.rcode.from_flags(5, 0) == dns.rcode.REFUSED)

    def test_rcode7(self):
        def bad():
            dns.rcode.to_flags(4096)
        self.failUnlessRaises(ValueError, bad)

    def test_flags1(self):
        self.failUnless(dns.flags.from_text("RA RD AA QR") == \
                        dns.flags.QR|dns.flags.AA|dns.flags.RD|dns.flags.RA)

    def test_flags2(self):
        flags = dns.flags.QR|dns.flags.AA|dns.flags.RD|dns.flags.RA
        self.failUnless(dns.flags.to_text(flags) == "QR AA RD RA")


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = generate
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import sys
sys.path.insert(0, '../')  # Force the local project to be *the* dns

import cStringIO
import filecmp
import os
import unittest

import dns.exception
import dns.rdata
import dns.rdataclass
import dns.rdatatype
import dns.rrset
import dns.zone

import pprint

pp = pprint.PrettyPrinter(indent=2)

import pdb
example_text = """$TTL 1h
$ORIGIN 0.0.192.IN-ADDR.ARPA.
$GENERATE 1-2 0 CNAME SERVER$.EXAMPLE.
"""

example_text1 = """$TTL 1h
$ORIGIN 0.0.192.IN-ADDR.ARPA.
$GENERATE 1-10 fooo$ CNAME $.0
"""

example_text2 = """$TTL 1h
@ 3600 IN SOA foo bar 1 2 3 4 5
@ 3600 IN NS ns1
@ 3600 IN NS ns2
bar.foo 300 IN MX 0 blaz.foo
ns1 3600 IN A 10.0.0.1
ns2 3600 IN A 10.0.0.2
$GENERATE 3-5 foo$ A 10.0.0.$
"""

example_text3 = """$TTL 1h
@ 3600 IN SOA foo bar 1 2 3 4 5
@ 3600 IN NS ns1
@ 3600 IN NS ns2
bar.foo 300 IN MX 0 blaz.foo
ns1 3600 IN A 10.0.0.1
ns2 3600 IN A 10.0.0.2
$GENERATE 4-8/2 foo$ A 10.0.0.$
"""

example_text4 = """$TTL 1h
@ 3600 IN SOA foo bar 1 2 3 4 5
@ 3600 IN NS ns1
@ 3600 IN NS ns2
bar.foo 300 IN MX 0 blaz.foo
ns1 3600 IN A 10.0.0.1
ns2 3600 IN A 10.0.0.2
$GENERATE 11-13 wp-db${-10,2,d}.services.mozilla.com 0 CNAME SERVER.FOOBAR.
"""

example_text5 = """$TTL 1h
@ 3600 IN SOA foo bar 1 2 3 4 5
@ 3600 IN NS ns1
@ 3600 IN NS ns2
bar.foo 300 IN MX 0 blaz.foo
ns1 3600 IN A 10.0.0.1
ns2 3600 IN A 10.0.0.2
$GENERATE 11-13 wp-db${10,2,d}.services.mozilla.com 0 CNAME SERVER.FOOBAR.
"""

example_text6 = """$TTL 1h
@ 3600 IN SOA foo bar 1 2 3 4 5
@ 3600 IN NS ns1
@ 3600 IN NS ns2
bar.foo 300 IN MX 0 blaz.foo
ns1 3600 IN A 10.0.0.1
ns2 3600 IN A 10.0.0.2
$GENERATE 11-13 wp-db${+10,2,d}.services.mozilla.com 0 CNAME SERVER.FOOBAR.
"""

example_text7 = """$TTL 1h
@ 3600 IN SOA foo bar 1 2 3 4 5
@ 3600 IN NS ns1
@ 3600 IN NS ns2
bar.foo 300 IN MX 0 blaz.foo
ns1 3600 IN A 10.0.0.1
ns2 3600 IN A 10.0.0.2
$GENERATE 11-13     sync${-10}.db   IN  A   10.10.16.0
"""

example_text8 = """$TTL 1h
@ 3600 IN SOA foo bar 1 2 3 4 5
@ 3600 IN NS ns1
@ 3600 IN NS ns2
bar.foo 300 IN MX 0 blaz.foo
ns1 3600 IN A 10.0.0.1
ns2 3600 IN A 10.0.0.2
$GENERATE 11-12 wp-db${-10,2,d} IN A 10.10.16.0
"""

example_text9 = """$TTL 1h
@ 3600 IN SOA foo bar 1 2 3 4 5
@ 3600 IN NS ns1
@ 3600 IN NS ns2
bar.foo 300 IN MX 0 blaz.foo
ns1 3600 IN A 10.0.0.1
ns2 3600 IN A 10.0.0.2
$GENERATE 11-12 wp-db${-10,2,d} IN A 10.10.16.0
$GENERATE 11-13     sync${-10}.db   IN  A   10.10.16.0
"""
example_text10 = """$TTL 1h
@ 3600 IN SOA foo bar 1 2 3 4 5
@ 3600 IN NS ns1
@ 3600 IN NS ns2
bar.foo 300 IN MX 0 blaz.foo
ns1 3600 IN A 10.0.0.1
ns2 3600 IN A 10.0.0.2
$GENERATE 27-28 $.2 PTR zlb${-26}.oob
"""


class GenerateTestCase(unittest.TestCase):

    def testFromText(self):
        def bad():
            z = dns.zone.from_text(example_text, 'example.', relativize=True)
        self.failUnlessRaises(dns.zone.NoSOA, bad)

    def testFromText1(self):
        def bad():
            z = dns.zone.from_text(example_text1, 'example.', relativize=True)
        self.failUnlessRaises(dns.zone.NoSOA, bad)

    def testIterateAllRdatas2(self):
        z = dns.zone.from_text(example_text2, 'example.', relativize=True)
        l = list(z.iterate_rdatas())
        l.sort()
        exl = [(dns.name.from_text('@', None),
                3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.NS,
                                    'ns1')),
               (dns.name.from_text('@', None),
                3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.NS,
                                    'ns2')),
               (dns.name.from_text('@', None),
                3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.SOA,
                                    'foo bar 1 2 3 4 5')),
               (dns.name.from_text('bar.foo', None),
                300,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.MX,
                                    '0 blaz.foo')),
                (dns.name.from_text('ns1', None),
                3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.1')),
                (dns.name.from_text('ns2', None),
                3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.2')),
                (dns.name.from_text('foo3', None),
                3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.3')),
                (dns.name.from_text('foo4', None),
                3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.4')),
                (dns.name.from_text('foo5', None),
                3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.5'))]

        exl.sort()
        self.failUnless(l == exl)

    def testIterateAllRdatas3(self):
        z = dns.zone.from_text(example_text3, 'example.', relativize=True)
        l = list(z.iterate_rdatas())
        l.sort()
        exl = [(dns.name.from_text('@', None),
                3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.NS,
                                    'ns1')),
               (dns.name.from_text('@', None),
                3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.NS,
                                    'ns2')),
               (dns.name.from_text('@', None),
                3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.SOA,
                                    'foo bar 1 2 3 4 5')),
               (dns.name.from_text('bar.foo', None),
                300,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.MX,
                                    '0 blaz.foo')),
               (dns.name.from_text('ns1', None),
                3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.1')),
               (dns.name.from_text('ns2', None),
                3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.2')),
                (dns.name.from_text('foo4', None), 3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.4')),
                (dns.name.from_text('foo6', None), 3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.6')),
                (dns.name.from_text('foo8', None), 3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.8'))]
        exl.sort()
        self.failUnless(l == exl)
    def testGenerate1(self):
        z = dns.zone.from_text(example_text4, 'example.', relativize=True)
        l = list(z.iterate_rdatas())
        l.sort()
        exl = [(dns.name.from_text('@', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.NS,
                                    'ns1')),
               (dns.name.from_text('@', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.NS,
                                    'ns2')),
               (dns.name.from_text('@', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.SOA,
                                    'foo bar 1 2 3 4 5')),
               (dns.name.from_text('bar.foo', None),
                300L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.MX,
                                    '0 blaz.foo')),
               (dns.name.from_text('ns1', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.1')),
               (dns.name.from_text('ns2', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.2')),

                (dns.name.from_text('wp-db01.services.mozilla.com', None),
                    0L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.CNAME,
                                    'SERVER.FOOBAR.')),

                (dns.name.from_text('wp-db02.services.mozilla.com', None),
                    0L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.CNAME,
                                    'SERVER.FOOBAR.')),

                (dns.name.from_text('wp-db03.services.mozilla.com', None),
                    0L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.CNAME,
                                    'SERVER.FOOBAR.'))]
        exl.sort()
        self.failUnless(l == exl)

    def testGenerate2(self):
        z = dns.zone.from_text(example_text5, 'example.', relativize=True)
        l = list(z.iterate_rdatas())
        l.sort()
        exl = [(dns.name.from_text('@', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.NS,
                                    'ns1')),
               (dns.name.from_text('@', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.NS,
                                    'ns2')),
               (dns.name.from_text('@', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.SOA,
                                    'foo bar 1 2 3 4 5')),
               (dns.name.from_text('bar.foo', None),
                300L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.MX,
                                    '0 blaz.foo')),
               (dns.name.from_text('ns1', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.1')),
               (dns.name.from_text('ns2', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.2')),

                (dns.name.from_text('wp-db21.services.mozilla.com', None), 0L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.CNAME,
                                    'SERVER.FOOBAR.')),

                (dns.name.from_text('wp-db22.services.mozilla.com', None), 0L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.CNAME,
                                    'SERVER.FOOBAR.')),

                (dns.name.from_text('wp-db23.services.mozilla.com', None), 0L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.CNAME,
                                    'SERVER.FOOBAR.'))]
        exl.sort()
        self.failUnless(l == exl)

    def testGenerate3(self):
        z = dns.zone.from_text(example_text6, 'example.', relativize=True)
        l = list(z.iterate_rdatas())
        l.sort()

        exl = [(dns.name.from_text('@', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.NS,
                                    'ns1')),
               (dns.name.from_text('@', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.NS,
                                    'ns2')),
               (dns.name.from_text('@', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.SOA,
                                    'foo bar 1 2 3 4 5')),
               (dns.name.from_text('bar.foo', None),
                300L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.MX,
                                    '0 blaz.foo')),
               (dns.name.from_text('ns1', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.1')),
               (dns.name.from_text('ns2', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.2')),
                (dns.name.from_text('wp-db21.services.mozilla.com', None), 0L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.CNAME,
                                    'SERVER.FOOBAR.')),

                (dns.name.from_text('wp-db22.services.mozilla.com', None), 0L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.CNAME,
                                    'SERVER.FOOBAR.')),

                (dns.name.from_text('wp-db23.services.mozilla.com', None), 0L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.CNAME,
                                    'SERVER.FOOBAR.'))]
        exl.sort()
        self.failUnless(l == exl)

    def testGenerate4(self):
        z = dns.zone.from_text(example_text7, 'example.', relativize=True)
        l = list(z.iterate_rdatas())
        l.sort()
        exl = [(dns.name.from_text('@', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.NS,
                                    'ns1')),
               (dns.name.from_text('@', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.NS,
                                    'ns2')),
               (dns.name.from_text('@', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.SOA,
                                    'foo bar 1 2 3 4 5')),
               (dns.name.from_text('bar.foo', None),
                300L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.MX,
                                    '0 blaz.foo')),
               (dns.name.from_text('ns1', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.1')),
               (dns.name.from_text('ns2', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.2')),

                (dns.name.from_text('sync1.db', None), 3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.10.16.0')),

                (dns.name.from_text('sync2.db', None), 3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.10.16.0')),

                (dns.name.from_text('sync3.db', None), 3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.10.16.0'))]
        exl.sort()
        self.failUnless(l == exl)

    def testGenerate6(self):
        z = dns.zone.from_text(example_text9, 'example.', relativize=True)
        l = list(z.iterate_rdatas())
        l.sort()
        exl = [(dns.name.from_text('@', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.NS,
                                    'ns1')),
               (dns.name.from_text('@', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.NS,
                                    'ns2')),
               (dns.name.from_text('@', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.SOA,
                                    'foo bar 1 2 3 4 5')),
               (dns.name.from_text('bar.foo', None),
                300L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.MX,
                                    '0 blaz.foo')),
               (dns.name.from_text('ns1', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.1')),
               (dns.name.from_text('ns2', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.2')),

                (dns.name.from_text('wp-db01', None), 3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.10.16.0')),
                (dns.name.from_text('wp-db02', None), 3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.10.16.0')),

                (dns.name.from_text('sync1.db', None), 3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.10.16.0')),

                (dns.name.from_text('sync2.db', None), 3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.10.16.0')),

                (dns.name.from_text('sync3.db', None), 3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.10.16.0'))]
        exl.sort()
        self.failUnless(l == exl)

    def testGenerate7(self):
        z = dns.zone.from_text(example_text10, 'example.', relativize=True)
        l = list(z.iterate_rdatas())
        l.sort()
        exl = [(dns.name.from_text('@', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.NS,
                                    'ns1')),
               (dns.name.from_text('@', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.NS,
                                    'ns2')),
               (dns.name.from_text('@', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.SOA,
                                    'foo bar 1 2 3 4 5')),
               (dns.name.from_text('bar.foo', None),
                300L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.MX,
                                    '0 blaz.foo')),
               (dns.name.from_text('ns1', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.1')),
               (dns.name.from_text('ns2', None),
                3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.2')),

                (dns.name.from_text('27.2', None), 3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.PTR,
                                    'zlb1.oob')),

                (dns.name.from_text('28.2', None), 3600L,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.PTR,
                                    'zlb2.oob'))]

        exl.sort()
        self.failUnless(l == exl)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = grange
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import sys
sys.path.insert(0, '../')

import cStringIO
import filecmp
import os
import unittest

import dns
import dns.exception
import dns.grange

import pdb



class GRangeTestCase(unittest.TestCase):

    def testFromText1(self):
        start, stop, step = dns.grange.from_text('1-1')
        self.assertEqual(start, 1)
        self.assertEqual(stop, 1)
        self.assertEqual(step, 1)

    def testFromText2(self):
        start, stop, step = dns.grange.from_text('1-4')
        self.assertEqual(start, 1)
        self.assertEqual(stop, 4)
        self.assertEqual(step, 1)

    def testFromText3(self):
        start, stop, step = dns.grange.from_text('4-255')
        self.assertEqual(start, 4)
        self.assertEqual(stop, 255)
        self.assertEqual(step, 1)

    def testFromText4(self):
        start, stop, step = dns.grange.from_text('1-1/1')
        self.assertEqual(start, 1)
        self.assertEqual(stop, 1)
        self.assertEqual(step, 1)

    def testFromText5(self):
        start, stop, step = dns.grange.from_text('1-4/2')
        self.assertEqual(start, 1)
        self.assertEqual(stop, 4)
        self.assertEqual(step, 2)

    def testFromText6(self):
        start, stop, step = dns.grange.from_text('4-255/77')
        self.assertEqual(start, 4)
        self.assertEqual(stop, 255)
        self.assertEqual(step, 77)

    def testFailFromText1(self):
        def bad():
            start = 2
            stop = 1
            step = 1
            dns.grange.from_text('%d-%d/%d' % (start, stop, step))
        self.assertRaises(AssertionError, bad)

    def testFailFromText2(self):
        def bad():
            start = '-1'
            stop = 3
            step = 1
            dns.grange.from_text('%s-%d/%d' % (start, stop, step))
        self.assertRaises(dns.exception.SyntaxError, bad)

    def testFailFromText2(self):
        def bad():
            start = 1
            stop = 4
            step = '-2'
            dns.grange.from_text('%d-%d/%s' % (start, stop, step))
        self.assertRaises(dns.exception.SyntaxError, bad)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = message
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import cStringIO
import os
import unittest

import dns.exception
import dns.message

query_text = """id 1234
opcode QUERY
rcode NOERROR
flags RD
edns 0
eflags DO
payload 4096
;QUESTION
wwww.dnspython.org. IN A
;ANSWER
;AUTHORITY
;ADDITIONAL"""

goodhex = '04d201000001000000000001047777777709646e73707974686f6e' \
          '036f726700000100010000291000000080000000'

goodwire = goodhex.decode('hex_codec')

answer_text = """id 1234
opcode QUERY
rcode NOERROR
flags QR AA RD
;QUESTION
dnspython.org. IN SOA
;ANSWER
dnspython.org. 3600 IN SOA woof.dnspython.org. hostmaster.dnspython.org. 2003052700 3600 1800 604800 3600
;AUTHORITY
dnspython.org. 3600 IN NS ns1.staff.nominum.org.
dnspython.org. 3600 IN NS ns2.staff.nominum.org.
dnspython.org. 3600 IN NS woof.play-bow.org.
;ADDITIONAL
woof.play-bow.org. 3600 IN A 204.152.186.150
"""

goodhex2 = '04d2 8500 0001 0001 0003 0001' \
           '09646e73707974686f6e036f726700 0006 0001' \
           'c00c 0006 0001 00000e10 0028 ' \
               '04776f6f66c00c 0a686f73746d6173746572c00c' \
               '7764289c 00000e10 00000708 00093a80 00000e10' \
           'c00c 0002 0001 00000e10 0014' \
               '036e7331057374616666076e6f6d696e756dc016' \
           'c00c 0002 0001 00000e10 0006 036e7332c063' \
           'c00c 0002 0001 00000e10 0010 04776f6f6608706c61792d626f77c016' \
           'c091 0001 0001 00000e10 0004 cc98ba96'


goodwire2 = goodhex2.replace(' ', '').decode('hex_codec')

query_text_2 = """id 1234
opcode QUERY
rcode 4095
flags RD
edns 0
eflags DO
payload 4096
;QUESTION
wwww.dnspython.org. IN A
;ANSWER
;AUTHORITY
;ADDITIONAL"""

goodhex3 = '04d2010f0001000000000001047777777709646e73707974686f6e' \
          '036f726700000100010000291000ff0080000000'

goodwire3 = goodhex3.decode('hex_codec')

class MessageTestCase(unittest.TestCase):

    def test_comparison_eq1(self):
        q1 = dns.message.from_text(query_text)
        q2 = dns.message.from_text(query_text)
        self.failUnless(q1 == q2)

    def test_comparison_ne1(self):
        q1 = dns.message.from_text(query_text)
        q2 = dns.message.from_text(query_text)
        q2.id = 10
        self.failUnless(q1 != q2)

    def test_comparison_ne2(self):
        q1 = dns.message.from_text(query_text)
        q2 = dns.message.from_text(query_text)
        q2.question = []
        self.failUnless(q1 != q2)

    def test_comparison_ne3(self):
        q1 = dns.message.from_text(query_text)
        self.failUnless(q1 != 1)

    def test_EDNS_to_wire1(self):
        q = dns.message.from_text(query_text)
        w = q.to_wire()
        self.failUnless(w == goodwire)

    def test_EDNS_from_wire1(self):
        m = dns.message.from_wire(goodwire)
        self.failUnless(str(m) == query_text)

    def test_EDNS_to_wire2(self):
        q = dns.message.from_text(query_text_2)
        w = q.to_wire()
        self.failUnless(w == goodwire3)

    def test_EDNS_from_wire2(self):
        m = dns.message.from_wire(goodwire3)
        self.failUnless(str(m) == query_text_2)

    def test_TooBig(self):
        def bad():
            q = dns.message.from_text(query_text)
            for i in xrange(0, 25):
                rrset = dns.rrset.from_text('foo%d.' % i, 3600,
                                            dns.rdataclass.IN,
                                            dns.rdatatype.A,
                                            '10.0.0.%d' % i)
                q.additional.append(rrset)
            w = q.to_wire(max_size=512)
        self.failUnlessRaises(dns.exception.TooBig, bad)

    def test_answer1(self):
        a = dns.message.from_text(answer_text)
        wire = a.to_wire(want_shuffle=False)
        self.failUnless(wire == goodwire2)

    def test_TrailingJunk(self):
        def bad():
            badwire = goodwire + '\x00'
            m = dns.message.from_wire(badwire)
        self.failUnlessRaises(dns.message.TrailingJunk, bad)

    def test_ShortHeader(self):
        def bad():
            badwire = '\x00' * 11
            m = dns.message.from_wire(badwire)
        self.failUnlessRaises(dns.message.ShortHeader, bad)

    def test_RespondingToResponse(self):
        def bad():
            q = dns.message.make_query('foo', 'A')
            r1 = dns.message.make_response(q)
            r2 = dns.message.make_response(r1)
        self.failUnlessRaises(dns.exception.FormError, bad)

    def test_ExtendedRcodeSetting(self):
        m = dns.message.make_query('foo', 'A')
        m.set_rcode(4095)
        self.failUnless(m.rcode() == 4095)
        m.set_rcode(2)
        self.failUnless(m.rcode() == 2)

    def test_EDNSVersionCoherence(self):
        m = dns.message.make_query('foo', 'A')
        m.use_edns(1)
        self.failUnless((m.ednsflags >> 16) & 0xFF == 1)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = name
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import unittest

import cStringIO
import socket

import dns.name
import dns.reversename
import dns.e164

class NameTestCase(unittest.TestCase):
    def setUp(self):
        self.origin = dns.name.from_text('example.')
        
    def testFromTextRel1(self):
        n = dns.name.from_text('foo.bar')
        self.failUnless(n.labels == ('foo', 'bar', ''))

    def testFromTextRel2(self):
        n = dns.name.from_text('foo.bar', origin=self.origin)
        self.failUnless(n.labels == ('foo', 'bar', 'example', ''))

    def testFromTextRel3(self):
        n = dns.name.from_text('foo.bar', origin=None)
        self.failUnless(n.labels == ('foo', 'bar'))

    def testFromTextRel4(self):
        n = dns.name.from_text('@', origin=None)
        self.failUnless(n == dns.name.empty)

    def testFromTextRel5(self):
        n = dns.name.from_text('@', origin=self.origin)
        self.failUnless(n == self.origin)

    def testFromTextAbs1(self):
        n = dns.name.from_text('foo.bar.')
        self.failUnless(n.labels == ('foo', 'bar', ''))

    def testTortureFromText(self):
        good = [
            r'.',
            r'a',
            r'a.',
            r'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            r'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            r'\000.\008.\010.\032.\046.\092.\099.\255',
            r'\\',
            r'\..\.',
            r'\\.\\',
            r'!"#%&/()=+-',
            r'\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255.\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255.\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255.\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255',
            ]
        bad = [
            r'..',
            r'.a',
            r'\\..',
            '\\',		# yes, we don't want the 'r' prefix!
            r'\0',
            r'\00',
            r'\00Z',
            r'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            r'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            r'\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255.\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255.\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255.\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255\255',
            ]
        for t in good:
            try:
                n = dns.name.from_text(t)
            except:
                self.fail("good test '%s' raised an exception" % t)
        for t in bad:
            caught = False
            try:
                n = dns.name.from_text(t)
            except:
                caught = True
            if not caught:
                self.fail("bad test '%s' did not raise an exception" % t)

    def testImmutable1(self):
        def bad():
            self.origin.labels = ()
        self.failUnlessRaises(TypeError, bad)

    def testImmutable2(self):
        def bad():
            self.origin.labels[0] = 'foo'
        self.failUnlessRaises(TypeError, bad)

    def testAbs1(self):
        self.failUnless(dns.name.root.is_absolute())

    def testAbs2(self):
        self.failUnless(not dns.name.empty.is_absolute())

    def testAbs3(self):
        self.failUnless(self.origin.is_absolute())

    def testAbs3(self):
        n = dns.name.from_text('foo', origin=None)
        self.failUnless(not n.is_absolute())

    def testWild1(self):
        n = dns.name.from_text('*.foo', origin=None)
        self.failUnless(n.is_wild())

    def testWild2(self):
        n = dns.name.from_text('*a.foo', origin=None)
        self.failUnless(not n.is_wild())

    def testWild3(self):
        n = dns.name.from_text('a.*.foo', origin=None)
        self.failUnless(not n.is_wild())

    def testWild4(self):
        self.failUnless(not dns.name.root.is_wild())

    def testWild5(self):
        self.failUnless(not dns.name.empty.is_wild())

    def testHash1(self):
        n1 = dns.name.from_text('fOo.COM')
        n2 = dns.name.from_text('foo.com')
        self.failUnless(hash(n1) == hash(n2))

    def testCompare1(self):
        n1 = dns.name.from_text('a')
        n2 = dns.name.from_text('b')
        self.failUnless(n1 < n2)
        self.failUnless(n2 > n1)

    def testCompare2(self):
        n1 = dns.name.from_text('')
        n2 = dns.name.from_text('b')
        self.failUnless(n1 < n2)
        self.failUnless(n2 > n1)

    def testCompare3(self):
        self.failUnless(dns.name.empty < dns.name.root)
        self.failUnless(dns.name.root > dns.name.empty)

    def testCompare4(self):
        self.failUnless(dns.name.root != 1)

    def testCompare5(self):
        self.failUnless(dns.name.root < 1 or dns.name.root > 1)

    def testSubdomain1(self):
        self.failUnless(not dns.name.empty.is_subdomain(dns.name.root))

    def testSubdomain2(self):
        self.failUnless(not dns.name.root.is_subdomain(dns.name.empty))

    def testSubdomain3(self):
        n = dns.name.from_text('foo', origin=self.origin)
        self.failUnless(n.is_subdomain(self.origin))

    def testSubdomain4(self):
        n = dns.name.from_text('foo', origin=self.origin)
        self.failUnless(n.is_subdomain(dns.name.root))

    def testSubdomain5(self):
        n = dns.name.from_text('foo', origin=self.origin)
        self.failUnless(n.is_subdomain(n))

    def testSuperdomain1(self):
        self.failUnless(not dns.name.empty.is_superdomain(dns.name.root))

    def testSuperdomain2(self):
        self.failUnless(not dns.name.root.is_superdomain(dns.name.empty))

    def testSuperdomain3(self):
        n = dns.name.from_text('foo', origin=self.origin)
        self.failUnless(self.origin.is_superdomain(n))

    def testSuperdomain4(self):
        n = dns.name.from_text('foo', origin=self.origin)
        self.failUnless(dns.name.root.is_superdomain(n))

    def testSuperdomain5(self):
        n = dns.name.from_text('foo', origin=self.origin)
        self.failUnless(n.is_superdomain(n))

    def testCanonicalize1(self):
        n = dns.name.from_text('FOO.bar', origin=self.origin)
        c = n.canonicalize()
        self.failUnless(c.labels == ('foo', 'bar', 'example', ''))

    def testToText1(self):
        n = dns.name.from_text('FOO.bar', origin=self.origin)
        t = n.to_text()
        self.failUnless(t == 'FOO.bar.example.')

    def testToText2(self):
        n = dns.name.from_text('FOO.bar', origin=self.origin)
        t = n.to_text(True)
        self.failUnless(t == 'FOO.bar.example')

    def testToText3(self):
        n = dns.name.from_text('FOO.bar', origin=None)
        t = n.to_text()
        self.failUnless(t == 'FOO.bar')

    def testToText4(self):
        t = dns.name.empty.to_text()
        self.failUnless(t == '@')

    def testToText5(self):
        t = dns.name.root.to_text()
        self.failUnless(t == '.')

    def testToText6(self):
        n = dns.name.from_text('FOO bar', origin=None)
        t = n.to_text()
        self.failUnless(t == r'FOO\032bar')

    def testToText7(self):
        n = dns.name.from_text(r'FOO\.bar', origin=None)
        t = n.to_text()
        self.failUnless(t == r'FOO\.bar')

    def testToText8(self):
        n = dns.name.from_text(r'\070OO\.bar', origin=None)
        t = n.to_text()
        self.failUnless(t == r'FOO\.bar')

    def testSlice1(self):
        n = dns.name.from_text(r'a.b.c.', origin=None)
        s = n[:]
        self.failUnless(s == ('a', 'b', 'c', ''))

    def testSlice2(self):
        n = dns.name.from_text(r'a.b.c.', origin=None)
        s = n[:2]
        self.failUnless(s == ('a', 'b'))

    def testSlice3(self):
        n = dns.name.from_text(r'a.b.c.', origin=None)
        s = n[2:]
        self.failUnless(s == ('c', ''))

    def testEmptyLabel1(self):
        def bad():
            n = dns.name.Name(['a', '', 'b'])
        self.failUnlessRaises(dns.name.EmptyLabel, bad)

    def testEmptyLabel2(self):
        def bad():
            n = dns.name.Name(['', 'b'])
        self.failUnlessRaises(dns.name.EmptyLabel, bad)

    def testEmptyLabel3(self):
        n = dns.name.Name(['b', ''])
        self.failUnless(n)

    def testLongLabel(self):
        n = dns.name.Name(['a' * 63])
        self.failUnless(n)

    def testLabelTooLong(self):
        def bad():
            n = dns.name.Name(['a' * 64, 'b'])
        self.failUnlessRaises(dns.name.LabelTooLong, bad)

    def testLongName(self):
        n = dns.name.Name(['a' * 63, 'a' * 63, 'a' * 63, 'a' * 62])
        self.failUnless(n)

    def testNameTooLong(self):
        def bad():
            n = dns.name.Name(['a' * 63, 'a' * 63, 'a' * 63, 'a' * 63])
        self.failUnlessRaises(dns.name.NameTooLong, bad)

    def testConcat1(self):
        n1 = dns.name.Name(['a', 'b'])
        n2 = dns.name.Name(['c', 'd'])
        e = dns.name.Name(['a', 'b', 'c', 'd'])
        r = n1 + n2
        self.failUnless(r == e)

    def testConcat2(self):
        n1 = dns.name.Name(['a', 'b'])
        n2 = dns.name.Name([])
        e = dns.name.Name(['a', 'b'])
        r = n1 + n2
        self.failUnless(r == e)

    def testConcat2(self):
        n1 = dns.name.Name([])
        n2 = dns.name.Name(['a', 'b'])
        e = dns.name.Name(['a', 'b'])
        r = n1 + n2
        self.failUnless(r == e)

    def testConcat3(self):
        n1 = dns.name.Name(['a', 'b', ''])
        n2 = dns.name.Name([])
        e = dns.name.Name(['a', 'b', ''])
        r = n1 + n2
        self.failUnless(r == e)

    def testConcat4(self):
        n1 = dns.name.Name(['a', 'b'])
        n2 = dns.name.Name(['c', ''])
        e = dns.name.Name(['a', 'b', 'c', ''])
        r = n1 + n2
        self.failUnless(r == e)

    def testConcat5(self):
        def bad():
            n1 = dns.name.Name(['a', 'b', ''])
            n2 = dns.name.Name(['c'])
            r = n1 + n2
        self.failUnlessRaises(dns.name.AbsoluteConcatenation, bad)

    def testBadEscape(self):
        def bad():
            n = dns.name.from_text(r'a.b\0q1.c.')
            print n
        self.failUnlessRaises(dns.name.BadEscape, bad)

    def testDigestable1(self):
        n = dns.name.from_text('FOO.bar')
        d = n.to_digestable()
        self.failUnless(d == '\x03foo\x03bar\x00')

    def testDigestable2(self):
        n1 = dns.name.from_text('FOO.bar')
        n2 = dns.name.from_text('foo.BAR.')
        d1 = n1.to_digestable()
        d2 = n2.to_digestable()
        self.failUnless(d1 == d2)

    def testDigestable3(self):
        d = dns.name.root.to_digestable()
        self.failUnless(d == '\x00')

    def testDigestable4(self):
        n = dns.name.from_text('FOO.bar', None)
        d = n.to_digestable(dns.name.root)
        self.failUnless(d == '\x03foo\x03bar\x00')
        
    def testBadDigestable(self):
        def bad():
            n = dns.name.from_text('FOO.bar', None)
            d = n.to_digestable()
        self.failUnlessRaises(dns.name.NeedAbsoluteNameOrOrigin, bad)

    def testToWire1(self):
        n = dns.name.from_text('FOO.bar')
        f = cStringIO.StringIO()
        compress = {}
        n.to_wire(f, compress)
        self.failUnless(f.getvalue() == '\x03FOO\x03bar\x00')

    def testToWire2(self):
        n = dns.name.from_text('FOO.bar')
        f = cStringIO.StringIO()
        compress = {}
        n.to_wire(f, compress)
        n.to_wire(f, compress)
        self.failUnless(f.getvalue() == '\x03FOO\x03bar\x00\xc0\x00')

    def testToWire3(self):
        n1 = dns.name.from_text('FOO.bar')
        n2 = dns.name.from_text('foo.bar')
        f = cStringIO.StringIO()
        compress = {}
        n1.to_wire(f, compress)
        n2.to_wire(f, compress)
        self.failUnless(f.getvalue() == '\x03FOO\x03bar\x00\xc0\x00')

    def testToWire4(self):
        n1 = dns.name.from_text('FOO.bar')
        n2 = dns.name.from_text('a.foo.bar')
        f = cStringIO.StringIO()
        compress = {}
        n1.to_wire(f, compress)
        n2.to_wire(f, compress)
        self.failUnless(f.getvalue() == '\x03FOO\x03bar\x00\x01\x61\xc0\x00')

    def testToWire5(self):
        n1 = dns.name.from_text('FOO.bar')
        n2 = dns.name.from_text('a.foo.bar')
        f = cStringIO.StringIO()
        compress = {}
        n1.to_wire(f, compress)
        n2.to_wire(f, None)
        self.failUnless(f.getvalue() == \
                        '\x03FOO\x03bar\x00\x01\x61\x03foo\x03bar\x00')

    def testToWire6(self):
        n = dns.name.from_text('FOO.bar')
        v = n.to_wire()
        self.failUnless(v == '\x03FOO\x03bar\x00')

    def testBadToWire(self):
        def bad():
            n = dns.name.from_text('FOO.bar', None)
            f = cStringIO.StringIO()
            compress = {}
            n.to_wire(f, compress)
        self.failUnlessRaises(dns.name.NeedAbsoluteNameOrOrigin, bad)

    def testSplit1(self):
        n = dns.name.from_text('foo.bar.')
        (prefix, suffix) = n.split(2)
        ep = dns.name.from_text('foo', None)
        es = dns.name.from_text('bar.', None)
        self.failUnless(prefix == ep and suffix == es)

    def testSplit2(self):
        n = dns.name.from_text('foo.bar.')
        (prefix, suffix) = n.split(1)
        ep = dns.name.from_text('foo.bar', None)
        es = dns.name.from_text('.', None)
        self.failUnless(prefix == ep and suffix == es)

    def testSplit3(self):
        n = dns.name.from_text('foo.bar.')
        (prefix, suffix) = n.split(0)
        ep = dns.name.from_text('foo.bar.', None)
        es = dns.name.from_text('', None)
        self.failUnless(prefix == ep and suffix == es)

    def testSplit4(self):
        n = dns.name.from_text('foo.bar.')
        (prefix, suffix) = n.split(3)
        ep = dns.name.from_text('', None)
        es = dns.name.from_text('foo.bar.', None)
        self.failUnless(prefix == ep and suffix == es)

    def testBadSplit1(self):
        def bad():
            n = dns.name.from_text('foo.bar.')
            (prefix, suffix) = n.split(-1)
        self.failUnlessRaises(ValueError, bad)

    def testBadSplit2(self):
        def bad():
            n = dns.name.from_text('foo.bar.')
            (prefix, suffix) = n.split(4)
        self.failUnlessRaises(ValueError, bad)

    def testRelativize1(self):
        n = dns.name.from_text('a.foo.bar.', None)
        o = dns.name.from_text('bar.', None)
        e = dns.name.from_text('a.foo', None)
        self.failUnless(n.relativize(o) == e)

    def testRelativize2(self):
        n = dns.name.from_text('a.foo.bar.', None)
        o = n
        e = dns.name.empty
        self.failUnless(n.relativize(o) == e)

    def testRelativize3(self):
        n = dns.name.from_text('a.foo.bar.', None)
        o = dns.name.from_text('blaz.', None)
        e = n
        self.failUnless(n.relativize(o) == e)

    def testRelativize4(self):
        n = dns.name.from_text('a.foo', None)
        o = dns.name.root
        e = n
        self.failUnless(n.relativize(o) == e)

    def testDerelativize1(self):
        n = dns.name.from_text('a.foo', None)
        o = dns.name.from_text('bar.', None)
        e = dns.name.from_text('a.foo.bar.', None)
        self.failUnless(n.derelativize(o) == e)

    def testDerelativize2(self):
        n = dns.name.empty
        o = dns.name.from_text('a.foo.bar.', None)
        e = o
        self.failUnless(n.derelativize(o) == e)

    def testDerelativize3(self):
        n = dns.name.from_text('a.foo.bar.', None)
        o = dns.name.from_text('blaz.', None)
        e = n
        self.failUnless(n.derelativize(o) == e)

    def testChooseRelativity1(self):
        n = dns.name.from_text('a.foo.bar.', None)
        o = dns.name.from_text('bar.', None)
        e = dns.name.from_text('a.foo', None)
        self.failUnless(n.choose_relativity(o, True) == e)

    def testChooseRelativity2(self):
        n = dns.name.from_text('a.foo.bar.', None)
        o = dns.name.from_text('bar.', None)
        e = n
        self.failUnless(n.choose_relativity(o, False) == e)

    def testChooseRelativity3(self):
        n = dns.name.from_text('a.foo', None)
        o = dns.name.from_text('bar.', None)
        e = dns.name.from_text('a.foo.bar.', None)
        self.failUnless(n.choose_relativity(o, False) == e)

    def testChooseRelativity4(self):
        n = dns.name.from_text('a.foo', None)
        o = None
        e = n
        self.failUnless(n.choose_relativity(o, True) == e)

    def testChooseRelativity5(self):
        n = dns.name.from_text('a.foo', None)
        o = None
        e = n
        self.failUnless(n.choose_relativity(o, False) == e)

    def testChooseRelativity6(self):
        n = dns.name.from_text('a.foo.', None)
        o = None
        e = n
        self.failUnless(n.choose_relativity(o, True) == e)

    def testChooseRelativity7(self):
        n = dns.name.from_text('a.foo.', None)
        o = None
        e = n
        self.failUnless(n.choose_relativity(o, False) == e)

    def testFromWire1(self):
        w = '\x03foo\x00\xc0\x00'
        (n1, cused1) = dns.name.from_wire(w, 0)
        (n2, cused2) = dns.name.from_wire(w, cused1)
        en1 = dns.name.from_text('foo.')
        en2 = en1
        ecused1 = 5
        ecused2 = 2
        self.failUnless(n1 == en1 and cused1 == ecused1 and \
                        n2 == en2 and cused2 == ecused2)

    def testFromWire1(self):
        w = '\x03foo\x00\x01a\xc0\x00\x01b\xc0\x05'
        current = 0
        (n1, cused1) = dns.name.from_wire(w, current)
        current += cused1
        (n2, cused2) = dns.name.from_wire(w, current)
        current += cused2
        (n3, cused3) = dns.name.from_wire(w, current)
        en1 = dns.name.from_text('foo.')
        en2 = dns.name.from_text('a.foo.')
        en3 = dns.name.from_text('b.a.foo.')
        ecused1 = 5
        ecused2 = 4
        ecused3 = 4
        self.failUnless(n1 == en1 and cused1 == ecused1 and \
                        n2 == en2 and cused2 == ecused2 and \
                        n3 == en3 and cused3 == ecused3)

    def testBadFromWire1(self):
        def bad():
            w = '\x03foo\xc0\x04'
            (n, cused) = dns.name.from_wire(w, 0)
        self.failUnlessRaises(dns.name.BadPointer, bad)

    def testBadFromWire2(self):
        def bad():
            w = '\x03foo\xc0\x05'
            (n, cused) = dns.name.from_wire(w, 0)
        self.failUnlessRaises(dns.name.BadPointer, bad)

    def testBadFromWire3(self):
        def bad():
            w = '\xbffoo'
            (n, cused) = dns.name.from_wire(w, 0)
        self.failUnlessRaises(dns.name.BadLabelType, bad)

    def testBadFromWire4(self):
        def bad():
            w = '\x41foo'
            (n, cused) = dns.name.from_wire(w, 0)
        self.failUnlessRaises(dns.name.BadLabelType, bad)

    def testParent1(self):
        n = dns.name.from_text('foo.bar.')
        self.failUnless(n.parent() == dns.name.from_text('bar.'))
        self.failUnless(n.parent().parent() == dns.name.root)

    def testParent2(self):
        n = dns.name.from_text('foo.bar', None)
        self.failUnless(n.parent() == dns.name.from_text('bar', None))
        self.failUnless(n.parent().parent() == dns.name.empty)

    def testParent3(self):
        def bad():
            n = dns.name.root
            n.parent()
        self.failUnlessRaises(dns.name.NoParent, bad)

    def testParent4(self):
        def bad():
            n = dns.name.empty
            n.parent()
        self.failUnlessRaises(dns.name.NoParent, bad)

    def testFromUnicode1(self):
        n = dns.name.from_text(u'foo.bar')
        self.failUnless(n.labels == ('foo', 'bar', ''))

    def testFromUnicode2(self):
        n = dns.name.from_text(u'foo\u1234bar.bar')
        self.failUnless(n.labels == ('xn--foobar-r5z', 'bar', ''))

    def testFromUnicodeAlternateDot1(self):
        n = dns.name.from_text(u'foo\u3002bar')
        self.failUnless(n.labels == ('foo', 'bar', ''))

    def testFromUnicodeAlternateDot2(self):
        n = dns.name.from_text(u'foo\uff0ebar')
        self.failUnless(n.labels == ('foo', 'bar', ''))

    def testFromUnicodeAlternateDot3(self):
        n = dns.name.from_text(u'foo\uff61bar')
        self.failUnless(n.labels == ('foo', 'bar', ''))

    def testToUnicode1(self):
        n = dns.name.from_text(u'foo.bar')
        s = n.to_unicode()
        self.failUnless(s == u'foo.bar.')

    def testToUnicode2(self):
        n = dns.name.from_text(u'foo\u1234bar.bar')
        s = n.to_unicode()
        self.failUnless(s == u'foo\u1234bar.bar.')

    def testToUnicode3(self):
        n = dns.name.from_text('foo.bar')
        s = n.to_unicode()
        self.failUnless(s == u'foo.bar.')

    def testReverseIPv4(self):
        e = dns.name.from_text('1.0.0.127.in-addr.arpa.')
        n = dns.reversename.from_address('127.0.0.1')
        self.failUnless(e == n)

    def testReverseIPv6(self):
        e = dns.name.from_text('1.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.ip6.arpa.')
        n = dns.reversename.from_address('::1')
        self.failUnless(e == n)

    def testBadReverseIPv4(self):
        def bad():
            n = dns.reversename.from_address('127.0.foo.1')
        self.failUnlessRaises(dns.exception.SyntaxError, bad)

    def testBadReverseIPv6(self):
        def bad():
            n = dns.reversename.from_address('::1::1')
        self.failUnlessRaises(dns.exception.SyntaxError, bad)

    def testForwardIPv4(self):
        n = dns.name.from_text('1.0.0.127.in-addr.arpa.')
        e = '127.0.0.1'
        text = dns.reversename.to_address(n)
        self.failUnless(text == e)

    def testForwardIPv6(self):
        n = dns.name.from_text('1.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.ip6.arpa.')
        e = '::1'
        text = dns.reversename.to_address(n)
        self.failUnless(text == e)

    def testE164ToEnum(self):
        text = '+1 650 555 1212'
        e = dns.name.from_text('2.1.2.1.5.5.5.0.5.6.1.e164.arpa.')
        n = dns.e164.from_e164(text)
        self.failUnless(n == e)

    def testEnumToE164(self):
        n = dns.name.from_text('2.1.2.1.5.5.5.0.5.6.1.e164.arpa.')
        e = '+16505551212'
        text = dns.e164.to_e164(n)
        self.failUnless(text == e)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = namedict
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import unittest

import dns.name
import dns.namedict

class NameTestCase(unittest.TestCase):

    def setUp(self):
        self.ndict = dns.namedict.NameDict()
        n1 = dns.name.from_text('foo.bar.')
        n2 = dns.name.from_text('bar.')
        self.ndict[n1] = 1
        self.ndict[n2] = 2
        self.rndict = dns.namedict.NameDict()
        n1 = dns.name.from_text('foo.bar', None)
        n2 = dns.name.from_text('bar', None)
        self.rndict[n1] = 1
        self.rndict[n2] = 2

    def testDepth(self):
        self.failUnless(self.ndict.max_depth == 3)

    def testLookup1(self):
        k = dns.name.from_text('foo.bar.')
        self.failUnless(self.ndict[k] == 1)

    def testLookup2(self):
        k = dns.name.from_text('foo.bar.')
        self.failUnless(self.ndict.get_deepest_match(k)[1] == 1)

    def testLookup3(self):
        k = dns.name.from_text('a.b.c.foo.bar.')
        self.failUnless(self.ndict.get_deepest_match(k)[1] == 1)

    def testLookup4(self):
        k = dns.name.from_text('a.b.c.bar.')
        self.failUnless(self.ndict.get_deepest_match(k)[1] == 2)

    def testLookup5(self):
        def bad():
            n = dns.name.from_text('a.b.c.')
            (k, v) = self.ndict.get_deepest_match(n)
        self.failUnlessRaises(KeyError, bad)

    def testLookup6(self):
        def bad():
            (k, v) = self.ndict.get_deepest_match(dns.name.empty)
        self.failUnlessRaises(KeyError, bad)

    def testLookup7(self):
        self.ndict[dns.name.empty] = 100
        n = dns.name.from_text('a.b.c.')
        (k, v) = self.ndict.get_deepest_match(n)
        self.failUnless(v == 100)

    def testLookup8(self):
        def bad():
            self.ndict['foo'] = 100
        self.failUnlessRaises(ValueError, bad)

    def testRelDepth(self):
        self.failUnless(self.rndict.max_depth == 2)

    def testRelLookup1(self):
        k = dns.name.from_text('foo.bar', None)
        self.failUnless(self.rndict[k] == 1)

    def testRelLookup2(self):
        k = dns.name.from_text('foo.bar', None)
        self.failUnless(self.rndict.get_deepest_match(k)[1] == 1)

    def testRelLookup3(self):
        k = dns.name.from_text('a.b.c.foo.bar', None)
        self.failUnless(self.rndict.get_deepest_match(k)[1] == 1)

    def testRelLookup4(self):
        k = dns.name.from_text('a.b.c.bar', None)
        self.failUnless(self.rndict.get_deepest_match(k)[1] == 2)

    def testRelLookup7(self):
        self.rndict[dns.name.empty] = 100
        n = dns.name.from_text('a.b.c', None)
        (k, v) = self.rndict.get_deepest_match(n)
        self.failUnless(v == 100)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ntoaaton
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import unittest

import dns.exception
import dns.ipv4
import dns.ipv6

# for convenience
aton4 = dns.ipv4.inet_aton
ntoa4 = dns.ipv4.inet_ntoa
aton6 = dns.ipv6.inet_aton
ntoa6 = dns.ipv6.inet_ntoa

v4_bad_addrs = ['256.1.1.1', '1.1.1', '1.1.1.1.1', '01.1.1.1',
                '+1.1.1.1', '1.1.1.1+', '1..2.3.4', '.1.2.3.4',
                '1.2.3.4.']

class NtoAAtoNTestCase(unittest.TestCase):

    def test_aton1(self):
        a = aton6('::')
        self.failUnless(a == '\x00' * 16)

    def test_aton2(self):
        a = aton6('::1')
        self.failUnless(a == '\x00' * 15 + '\x01')

    def test_aton3(self):
        a = aton6('::10.0.0.1')
        self.failUnless(a == '\x00' * 12 + '\x0a\x00\x00\x01')

    def test_aton4(self):
        a = aton6('abcd::dcba')
        self.failUnless(a == '\xab\xcd' + '\x00' * 12 + '\xdc\xba')

    def test_aton5(self):
        a = aton6('1:2:3:4:5:6:7:8')
        self.failUnless(a == \
                        '00010002000300040005000600070008'.decode('hex_codec'))

    def test_bad_aton1(self):
        def bad():
            a = aton6('abcd:dcba')
        self.failUnlessRaises(dns.exception.SyntaxError, bad)

    def test_bad_aton2(self):
        def bad():
            a = aton6('abcd::dcba::1')
        self.failUnlessRaises(dns.exception.SyntaxError, bad)

    def test_bad_aton3(self):
        def bad():
            a = aton6('1:2:3:4:5:6:7:8:9')
        self.failUnlessRaises(dns.exception.SyntaxError, bad)

    def test_aton1(self):
        a = aton6('::')
        self.failUnless(a == '\x00' * 16)

    def test_aton2(self):
        a = aton6('::1')
        self.failUnless(a == '\x00' * 15 + '\x01')

    def test_aton3(self):
        a = aton6('::10.0.0.1')
        self.failUnless(a == '\x00' * 12 + '\x0a\x00\x00\x01')

    def test_aton4(self):
        a = aton6('abcd::dcba')
        self.failUnless(a == '\xab\xcd' + '\x00' * 12 + '\xdc\xba')

    def test_ntoa1(self):
        b = '00010002000300040005000600070008'.decode('hex_codec')
        t = ntoa6(b)
        self.failUnless(t == '1:2:3:4:5:6:7:8')

    def test_ntoa2(self):
        b = '\x00' * 16
        t = ntoa6(b)
        self.failUnless(t == '::')

    def test_ntoa3(self):
        b = '\x00' * 15 + '\x01'
        t = ntoa6(b)
        self.failUnless(t == '::1')

    def test_ntoa4(self):
        b = '\x80' + '\x00' * 15
        t = ntoa6(b)
        self.failUnless(t == '8000::')

    def test_ntoa5(self):
        b = '\x01\xcd' + '\x00' * 12 + '\x03\xef'
        t = ntoa6(b)
        self.failUnless(t == '1cd::3ef')

    def test_ntoa6(self):
        b = 'ffff00000000ffff000000000000ffff'.decode('hex_codec')
        t = ntoa6(b)
        self.failUnless(t == 'ffff:0:0:ffff::ffff')

    def test_ntoa7(self):
        b = '00000000ffff000000000000ffffffff'.decode('hex_codec')
        t = ntoa6(b)
        self.failUnless(t == '0:0:ffff::ffff:ffff')

    def test_ntoa8(self):
        b = 'ffff0000ffff00000000ffff00000000'.decode('hex_codec')
        t = ntoa6(b)
        self.failUnless(t == 'ffff:0:ffff::ffff:0:0')

    def test_ntoa9(self):
        b = '0000000000000000000000000a000001'.decode('hex_codec')
        t = ntoa6(b)
        self.failUnless(t == '::10.0.0.1')

    def test_ntoa10(self):
        b = '0000000000000000000000010a000001'.decode('hex_codec')
        t = ntoa6(b)
        self.failUnless(t == '::1:a00:1')

    def test_ntoa11(self):
        b = '00000000000000000000ffff0a000001'.decode('hex_codec')
        t = ntoa6(b)
        self.failUnless(t == '::ffff:10.0.0.1')

    def test_ntoa12(self):
        b = '000000000000000000000000ffffffff'.decode('hex_codec')
        t = ntoa6(b)
        self.failUnless(t == '::255.255.255.255')

    def test_ntoa13(self):
        b = '00000000000000000000ffffffffffff'.decode('hex_codec')
        t = ntoa6(b)
        self.failUnless(t == '::ffff:255.255.255.255')

    def test_ntoa14(self):
        b = '0000000000000000000000000001ffff'.decode('hex_codec')
        t = ntoa6(b)
        self.failUnless(t == '::0.1.255.255')

    def test_bad_ntoa1(self):
        def bad():
            a = ntoa6('')
        self.failUnlessRaises(ValueError, bad)

    def test_bad_ntoa2(self):
        def bad():
            a = ntoa6('\x00' * 17)
        self.failUnlessRaises(ValueError, bad)

    def test_good_v4_aton(self):
        pairs = [('1.2.3.4', '\x01\x02\x03\x04'),
                 ('255.255.255.255', '\xff\xff\xff\xff'),
                 ('0.0.0.0', '\x00\x00\x00\x00')]
        for (t, b) in pairs:
            b1 = aton4(t)
            t1 = ntoa4(b1)
            self.failUnless(b1 == b)
            self.failUnless(t1 == t)

    def test_bad_v4_aton(self):
        def make_bad(a):
            def bad():
                return aton4(a)
            return bad
        for addr in v4_bad_addrs:
            self.failUnlessRaises(dns.exception.SyntaxError, make_bad(addr))

    def test_bad_v6_aton(self):
        addrs = ['+::0', '0::0::', '::0::', '1:2:3:4:5:6:7:8:9',
                 ':::::::']
        embedded = ['::' + x for x in v4_bad_addrs]
        addrs.extend(embedded)
        def make_bad(a):
            def bad():
                x = aton6(a)
            return bad
        for addr in addrs:
            self.failUnlessRaises(dns.exception.SyntaxError, make_bad(addr))

    def test_rfc5952_section_4_2_2(self):
        addr = '2001:db8:0:1:1:1:1:1'
        b1 = aton6(addr)
        t1 = ntoa6(b1)
        self.failUnless(t1 == addr)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = rdtypeandclass
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import unittest

import dns.rdataclass
import dns.rdatatype

class RdTypeAndClassTestCase(unittest.TestCase):

    # Classes
    
    def test_class_meta1(self):
        self.failUnless(dns.rdataclass.is_metaclass(dns.rdataclass.ANY))

    def test_class_meta2(self):
        self.failUnless(not dns.rdataclass.is_metaclass(dns.rdataclass.IN))

    def test_class_bytext1(self):
        self.failUnless(dns.rdataclass.from_text('IN') == dns.rdataclass.IN)

    def test_class_bytext2(self):
        self.failUnless(dns.rdataclass.from_text('CLASS1') ==
                        dns.rdataclass.IN)

    def test_class_bytext_bounds1(self):
        self.failUnless(dns.rdataclass.from_text('CLASS0') == 0)
        self.failUnless(dns.rdataclass.from_text('CLASS65535') == 65535)

    def test_class_bytext_bounds2(self):
        def bad():
            junk = dns.rdataclass.from_text('CLASS65536')
        self.failUnlessRaises(ValueError, bad)

    def test_class_bytext_unknown(self):
        def bad():
            junk = dns.rdataclass.from_text('XXX')
        self.failUnlessRaises(dns.rdataclass.UnknownRdataclass, bad)

    def test_class_totext1(self):
        self.failUnless(dns.rdataclass.to_text(dns.rdataclass.IN) == 'IN')

    def test_class_totext1(self):
        self.failUnless(dns.rdataclass.to_text(999) == 'CLASS999')

    def test_class_totext_bounds1(self):
        def bad():
            junk = dns.rdataclass.to_text(-1)
        self.failUnlessRaises(ValueError, bad)

    def test_class_totext_bounds2(self):
        def bad():
            junk = dns.rdataclass.to_text(65536)
        self.failUnlessRaises(ValueError, bad)

    # Types
    
    def test_type_meta1(self):
        self.failUnless(dns.rdatatype.is_metatype(dns.rdatatype.ANY))

    def test_type_meta2(self):
        self.failUnless(dns.rdatatype.is_metatype(dns.rdatatype.OPT))

    def test_type_meta3(self):
        self.failUnless(not dns.rdatatype.is_metatype(dns.rdatatype.A))

    def test_type_singleton1(self):
        self.failUnless(dns.rdatatype.is_singleton(dns.rdatatype.SOA))

    def test_type_singleton2(self):
        self.failUnless(not dns.rdatatype.is_singleton(dns.rdatatype.A))

    def test_type_bytext1(self):
        self.failUnless(dns.rdatatype.from_text('A') == dns.rdatatype.A)

    def test_type_bytext2(self):
        self.failUnless(dns.rdatatype.from_text('TYPE1') ==
                        dns.rdatatype.A)

    def test_type_bytext_bounds1(self):
        self.failUnless(dns.rdatatype.from_text('TYPE0') == 0)
        self.failUnless(dns.rdatatype.from_text('TYPE65535') == 65535)

    def test_type_bytext_bounds2(self):
        def bad():
            junk = dns.rdatatype.from_text('TYPE65536')
        self.failUnlessRaises(ValueError, bad)

    def test_type_bytext_unknown(self):
        def bad():
            junk = dns.rdatatype.from_text('XXX')
        self.failUnlessRaises(dns.rdatatype.UnknownRdatatype, bad)

    def test_type_totext1(self):
        self.failUnless(dns.rdatatype.to_text(dns.rdatatype.A) == 'A')

    def test_type_totext1(self):
        self.failUnless(dns.rdatatype.to_text(999) == 'TYPE999')

    def test_type_totext_bounds1(self):
        def bad():
            junk = dns.rdatatype.to_text(-1)
        self.failUnlessRaises(ValueError, bad)

    def test_type_totext_bounds2(self):
        def bad():
            junk = dns.rdatatype.to_text(65536)
        self.failUnlessRaises(ValueError, bad)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = rdtypeanyloc
# Copyright (C) 2014 Red Hat, Inc.
# Author: Petr Spacek <pspacek@redhat.com>
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED 'AS IS' AND RED HAT DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import unittest

import dns.rrset
import dns.rdtypes.ANY.LOC

class RdtypeAnyLocTestCase(unittest.TestCase):

    def testEqual1(self):
        '''Test default values for size, horizontal and vertical precision.'''
        r1 = dns.rrset.from_text('foo', 300, 'IN', 'LOC',
                                 '49 11 42.400 N 16 36 29.600 E 227.64m')
        r2 = dns.rrset.from_text('FOO', 600, 'in', 'loc',
                                 '49 11 42.400 N 16 36 29.600 E 227.64m '
                                 '1.00m 10000.00m 10.00m')
        self.failUnless(r1 == r2, '"%s" != "%s"' % (r1, r2))

    def testEqual2(self):
        '''Test default values for size, horizontal and vertical precision.'''
        r1 = dns.rdtypes.ANY.LOC.LOC(1, 29, (49, 11, 42, 400),
                                     (16, 36, 29, 600), 22764.0) # centimeters
        r2 = dns.rdtypes.ANY.LOC.LOC(1, 29, (49, 11, 42, 400),
                                     (16, 36, 29, 600), 22764.0, # centimeters
                                     100.0, 1000000.00, 1000.0)  # centimeters
        self.failUnless(r1 == r2, '"%s" != "%s"' % (r1, r2))

    def testEqual3(self):
        '''Test size, horizontal and vertical precision parsers: 100 cm == 1 m.

        Parsers in from_text() and __init__() have to produce equal results.'''
        r1 = dns.rdtypes.ANY.LOC.LOC(1, 29, (49, 11, 42, 400),
                                     (16, 36, 29, 600), 22764.0,
                                     200.0, 1000.00, 200.0)      # centimeters
        r2 = dns.rrset.from_text('FOO', 600, 'in', 'loc',
                                 '49 11 42.400 N 16 36 29.600 E 227.64m '
                                 '2.00m 10.00m 2.00m')[0]
        self.failUnless(r1 == r2, '"%s" != "%s"' % (r1, r2))

    def testEqual4(self):
        '''Test size, horizontal and vertical precision parsers without unit.

        Parsers in from_text() and __init__() have produce equal result
        for values with and without trailing "m".'''
        r1 = dns.rdtypes.ANY.LOC.LOC(1, 29, (49, 11, 42, 400),
                                     (16, 36, 29, 600), 22764.0,
                                     200.0, 1000.00, 200.0)      # centimeters
        r2 = dns.rrset.from_text('FOO', 600, 'in', 'loc',
                                 '49 11 42.400 N 16 36 29.600 E 227.64 '
                                 '2 10 2')[0] # meters without explicit unit
        self.failUnless(r1 == r2, '"%s" != "%s"' % (r1, r2))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = resolver
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import cStringIO
import select
import sys
import time
import unittest

import dns.name
import dns.message
import dns.name
import dns.rdataclass
import dns.rdatatype
import dns.resolver

resolv_conf = """
    /t/t
# comment 1
; comment 2
domain foo
nameserver 10.0.0.1
nameserver 10.0.0.2
"""

message_text = """id 1234
opcode QUERY
rcode NOERROR
flags QR AA RD
;QUESTION
example. IN A
;ANSWER
example. 1 IN A 10.0.0.1
;AUTHORITY
;ADDITIONAL
"""

class FakeAnswer(object):
    def __init__(self, expiration):
        self.expiration = expiration

class BaseResolverTests(object):

    if sys.platform != 'win32':
        def testRead(self):
            f = cStringIO.StringIO(resolv_conf)
            r = dns.resolver.Resolver(f)
            self.failUnless(r.nameservers == ['10.0.0.1', '10.0.0.2'] and
                            r.domain == dns.name.from_text('foo'))

    def testCacheExpiration(self):
        message = dns.message.from_text(message_text)
        name = dns.name.from_text('example.')
        answer = dns.resolver.Answer(name, dns.rdatatype.A, dns.rdataclass.IN,
                                     message)
        cache = dns.resolver.Cache()
        cache.put((name, dns.rdatatype.A, dns.rdataclass.IN), answer)
        time.sleep(2)
        self.failUnless(cache.get((name, dns.rdatatype.A, dns.rdataclass.IN))
                        is None)

    def testCacheCleaning(self):
        message = dns.message.from_text(message_text)
        name = dns.name.from_text('example.')
        answer = dns.resolver.Answer(name, dns.rdatatype.A, dns.rdataclass.IN,
                                     message)
        cache = dns.resolver.Cache(cleaning_interval=1.0)
        cache.put((name, dns.rdatatype.A, dns.rdataclass.IN), answer)
        time.sleep(2)
        self.failUnless(cache.get((name, dns.rdatatype.A, dns.rdataclass.IN))
                        is None)

    def testZoneForName1(self):
        name = dns.name.from_text('www.dnspython.org.')
        ezname = dns.name.from_text('dnspython.org.')
        zname = dns.resolver.zone_for_name(name)
        self.failUnless(zname == ezname)

    def testZoneForName2(self):
        name = dns.name.from_text('a.b.www.dnspython.org.')
        ezname = dns.name.from_text('dnspython.org.')
        zname = dns.resolver.zone_for_name(name)
        self.failUnless(zname == ezname)

    def testZoneForName3(self):
        name = dns.name.from_text('dnspython.org.')
        ezname = dns.name.from_text('dnspython.org.')
        zname = dns.resolver.zone_for_name(name)
        self.failUnless(zname == ezname)

    def testZoneForName4(self):
        def bad():
            name = dns.name.from_text('dnspython.org', None)
            zname = dns.resolver.zone_for_name(name)
        self.failUnlessRaises(dns.resolver.NotAbsolute, bad)

    def testLRUReplace(self):
        cache = dns.resolver.LRUCache(4)
        for i in xrange(0, 5):
            name = dns.name.from_text('example%d.' % i)
            answer = FakeAnswer(time.time() + 1)
            cache.put((name, dns.rdatatype.A, dns.rdataclass.IN), answer)
        for i in xrange(0, 5):
            name = dns.name.from_text('example%d.' % i)
            if i == 0:
                self.failUnless(cache.get((name, dns.rdatatype.A,
                                           dns.rdataclass.IN))
                                is None)
            else:
                self.failUnless(not cache.get((name, dns.rdatatype.A,
                                               dns.rdataclass.IN))
                                is None)

    def testLRUDoesLRU(self):
        cache = dns.resolver.LRUCache(4)
        for i in xrange(0, 4):
            name = dns.name.from_text('example%d.' % i)
            answer = FakeAnswer(time.time() + 1)
            cache.put((name, dns.rdatatype.A, dns.rdataclass.IN), answer)
        name = dns.name.from_text('example0.')
        cache.get((name, dns.rdatatype.A, dns.rdataclass.IN))
        # The LRU is now example1.
        name = dns.name.from_text('example4.')
        answer = FakeAnswer(time.time() + 1)
        cache.put((name, dns.rdatatype.A, dns.rdataclass.IN), answer)
        for i in xrange(0, 5):
            name = dns.name.from_text('example%d.' % i)
            if i == 1:
                self.failUnless(cache.get((name, dns.rdatatype.A,
                                           dns.rdataclass.IN))
                                is None)
            else:
                self.failUnless(not cache.get((name, dns.rdatatype.A,
                                               dns.rdataclass.IN))
                                is None)

    def testLRUExpiration(self):
        cache = dns.resolver.LRUCache(4)
        for i in xrange(0, 4):
            name = dns.name.from_text('example%d.' % i)
            answer = FakeAnswer(time.time() + 1)
            cache.put((name, dns.rdatatype.A, dns.rdataclass.IN), answer)
        time.sleep(2)
        for i in xrange(0, 4):
            name = dns.name.from_text('example%d.' % i)
            self.failUnless(cache.get((name, dns.rdatatype.A,
                                       dns.rdataclass.IN))
                            is None)

class PollingMonkeyPatchMixin(object):
    def setUp(self):
        self.__native_polling_backend = dns.query._polling_backend
        dns.query._set_polling_backend(self.polling_backend())

        unittest.TestCase.setUp(self)

    def tearDown(self):
        dns.query._set_polling_backend(self.__native_polling_backend)

        unittest.TestCase.tearDown(self)

class SelectResolverTestCase(PollingMonkeyPatchMixin, BaseResolverTests, unittest.TestCase):
    def polling_backend(self):
        return dns.query._select_for

if hasattr(select, 'poll'):
    class PollResolverTestCase(PollingMonkeyPatchMixin, BaseResolverTests, unittest.TestCase):
        def polling_backend(self):
            return dns.query._poll_for

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = rrset
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import unittest

import dns.rrset

class RRsetTestCase(unittest.TestCase):
        
    def testEqual1(self):
        r1 = dns.rrset.from_text('foo', 300, 'in', 'a', '10.0.0.1', '10.0.0.2')
        r2 = dns.rrset.from_text('FOO', 300, 'in', 'a', '10.0.0.2', '10.0.0.1')
        self.failUnless(r1 == r2)

    def testEqual2(self):
        r1 = dns.rrset.from_text('foo', 300, 'in', 'a', '10.0.0.1', '10.0.0.2')
        r2 = dns.rrset.from_text('FOO', 600, 'in', 'a', '10.0.0.2', '10.0.0.1')
        self.failUnless(r1 == r2)

    def testNotEqual1(self):
        r1 = dns.rrset.from_text('fooa', 30, 'in', 'a', '10.0.0.1', '10.0.0.2')
        r2 = dns.rrset.from_text('FOO', 30, 'in', 'a', '10.0.0.2', '10.0.0.1')
        self.failUnless(r1 != r2)

    def testNotEqual2(self):
        r1 = dns.rrset.from_text('foo', 30, 'in', 'a', '10.0.0.1', '10.0.0.3')
        r2 = dns.rrset.from_text('FOO', 30, 'in', 'a', '10.0.0.2', '10.0.0.1')
        self.failUnless(r1 != r2)

    def testNotEqual3(self):
        r1 = dns.rrset.from_text('foo', 30, 'in', 'a', '10.0.0.1', '10.0.0.2',
                                 '10.0.0.3')
        r2 = dns.rrset.from_text('FOO', 30, 'in', 'a', '10.0.0.2', '10.0.0.1')
        self.failUnless(r1 != r2)

    def testNotEqual4(self):
        r1 = dns.rrset.from_text('foo', 30, 'in', 'a', '10.0.0.1')
        r2 = dns.rrset.from_text('FOO', 30, 'in', 'a', '10.0.0.2', '10.0.0.1')
        self.failUnless(r1 != r2)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = set
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import unittest

import dns.set

# for convenience
S = dns.set.Set

class SimpleSetTestCase(unittest.TestCase):
        
    def testLen1(self):
        s1 = S()
        self.failUnless(len(s1) == 0)

    def testLen2(self):
        s1 = S([1, 2, 3])
        self.failUnless(len(s1) == 3)

    def testLen3(self):
        s1 = S([1, 2, 3, 3, 3])
        self.failUnless(len(s1) == 3)

    def testUnion1(self):
        s1 = S([1, 2, 3])
        s2 = S([1, 2, 3])
        e = S([1, 2, 3])
        self.failUnless(s1 | s2 == e)

    def testUnion2(self):
        s1 = S([1, 2, 3])
        s2 = S([])
        e = S([1, 2, 3])
        self.failUnless(s1 | s2 == e)

    def testUnion3(self):
        s1 = S([1, 2, 3])
        s2 = S([3, 4])
        e = S([1, 2, 3, 4])
        self.failUnless(s1 | s2 == e)

    def testIntersection1(self):
        s1 = S([1, 2, 3])
        s2 = S([1, 2, 3])
        e = S([1, 2, 3])
        self.failUnless(s1 & s2 == e)

    def testIntersection2(self):
        s1 = S([0, 1, 2, 3])
        s2 = S([1, 2, 3, 4])
        e = S([1, 2, 3])
        self.failUnless(s1 & s2 == e)

    def testIntersection3(self):
        s1 = S([1, 2, 3])
        s2 = S([])
        e = S([])
        self.failUnless(s1 & s2 == e)

    def testIntersection4(self):
        s1 = S([1, 2, 3])
        s2 = S([5, 4])
        e = S([])
        self.failUnless(s1 & s2 == e)

    def testDifference1(self):
        s1 = S([1, 2, 3])
        s2 = S([5, 4])
        e = S([1, 2, 3])
        self.failUnless(s1 - s2 == e)

    def testDifference2(self):
        s1 = S([1, 2, 3])
        s2 = S([])
        e = S([1, 2, 3])
        self.failUnless(s1 - s2 == e)

    def testDifference3(self):
        s1 = S([1, 2, 3])
        s2 = S([3, 2])
        e = S([1])
        self.failUnless(s1 - s2 == e)

    def testDifference4(self):
        s1 = S([1, 2, 3])
        s2 = S([3, 2, 1])
        e = S([])
        self.failUnless(s1 - s2 == e)

    def testSubset1(self):
        s1 = S([1, 2, 3])
        s2 = S([3, 2, 1])
        self.failUnless(s1.issubset(s2))

    def testSubset2(self):
        s1 = S([1, 2, 3])
        self.failUnless(s1.issubset(s1))

    def testSubset3(self):
        s1 = S([])
        s2 = S([1, 2, 3])
        self.failUnless(s1.issubset(s2))

    def testSubset4(self):
        s1 = S([1])
        s2 = S([1, 2, 3])
        self.failUnless(s1.issubset(s2))

    def testSubset5(self):
        s1 = S([])
        s2 = S([])
        self.failUnless(s1.issubset(s2))

    def testSubset6(self):
        s1 = S([1, 4])
        s2 = S([1, 2, 3])
        self.failUnless(not s1.issubset(s2))

    def testSuperset1(self):
        s1 = S([1, 2, 3])
        s2 = S([3, 2, 1])
        self.failUnless(s1.issuperset(s2))

    def testSuperset2(self):
        s1 = S([1, 2, 3])
        self.failUnless(s1.issuperset(s1))

    def testSuperset3(self):
        s1 = S([1, 2, 3])
        s2 = S([])
        self.failUnless(s1.issuperset(s2))

    def testSuperset4(self):
        s1 = S([1, 2, 3])
        s2 = S([1])
        self.failUnless(s1.issuperset(s2))

    def testSuperset5(self):
        s1 = S([])
        s2 = S([])
        self.failUnless(s1.issuperset(s2))

    def testSuperset6(self):
        s1 = S([1, 2, 3])
        s2 = S([1, 4])
        self.failUnless(not s1.issuperset(s2))

    def testUpdate1(self):
        s1 = S([1, 2, 3])
        u = (4, 5, 6)
        e = S([1, 2, 3, 4, 5, 6])
        s1.update(u)
        self.failUnless(s1 == e)

    def testUpdate2(self):
        s1 = S([1, 2, 3])
        u = []
        e = S([1, 2, 3])
        s1.update(u)
        self.failUnless(s1 == e)

    def testGetitem(self):
        s1 = S([1, 2, 3])
        i0 = s1[0]
        i1 = s1[1]
        i2 = s1[2]
        s2 = S([i0, i1, i2])
        self.failUnless(s1 == s2)

    def testGetslice(self):
        s1 = S([1, 2, 3])
        slice = s1[0:2]
        self.failUnless(len(slice) == 2)
        item = s1[2]
        slice.append(item)
        s2 = S(slice)
        self.failUnless(s1 == s2)

    def testDelitem(self):
        s1 = S([1, 2, 3])
        del s1[0]
        i1 = s1[0]
        i2 = s1[1]
        self.failUnless(i1 != i2)
        self.failUnless(i1 == 1 or i1 == 2 or i1 == 3)
        self.failUnless(i2 == 1 or i2 == 2 or i2 == 3)

    def testDelslice(self):
        s1 = S([1, 2, 3])
        del s1[0:2]
        i1 = s1[0]
        self.failUnless(i1 == 1 or i1 == 2 or i1 == 3)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = tokenizer
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import unittest

import dns.exception
import dns.tokenizer

Token = dns.tokenizer.Token

class TokenizerTestCase(unittest.TestCase):

    def testQuotedString1(self):
        tok = dns.tokenizer.Tokenizer(r'"foo"')
        token = tok.get()
        self.failUnless(token == Token(dns.tokenizer.QUOTED_STRING, 'foo'))

    def testQuotedString2(self):
        tok = dns.tokenizer.Tokenizer(r'""')
        token = tok.get()
        self.failUnless(token == Token(dns.tokenizer.QUOTED_STRING, ''))

    def testQuotedString3(self):
        tok = dns.tokenizer.Tokenizer(r'"\"foo\""')
        token = tok.get()
        self.failUnless(token == Token(dns.tokenizer.QUOTED_STRING, '"foo"'))

    def testQuotedString4(self):
        tok = dns.tokenizer.Tokenizer(r'"foo\010bar"')
        token = tok.get()
        self.failUnless(token == Token(dns.tokenizer.QUOTED_STRING, 'foo\x0abar'))

    def testQuotedString5(self):
        def bad():
            tok = dns.tokenizer.Tokenizer(r'"foo')
            token = tok.get()
        self.failUnlessRaises(dns.exception.UnexpectedEnd, bad)

    def testQuotedString6(self):
        def bad():
            tok = dns.tokenizer.Tokenizer(r'"foo\01')
            token = tok.get()
        self.failUnlessRaises(dns.exception.SyntaxError, bad)

    def testQuotedString7(self):
        def bad():
            tok = dns.tokenizer.Tokenizer('"foo\nbar"')
            token = tok.get()
        self.failUnlessRaises(dns.exception.SyntaxError, bad)

    def testEmpty1(self):
        tok = dns.tokenizer.Tokenizer('')
        token = tok.get()
        self.failUnless(token.is_eof())

    def testEmpty2(self):
        tok = dns.tokenizer.Tokenizer('')
        token1 = tok.get()
        token2 = tok.get()
        self.failUnless(token1.is_eof() and token2.is_eof())

    def testEOL(self):
        tok = dns.tokenizer.Tokenizer('\n')
        token1 = tok.get()
        token2 = tok.get()
        self.failUnless(token1.is_eol() and token2.is_eof())

    def testWS1(self):
        tok = dns.tokenizer.Tokenizer(' \n')
        token1 = tok.get()
        self.failUnless(token1.is_eol())

    def testWS2(self):
        tok = dns.tokenizer.Tokenizer(' \n')
        token1 = tok.get(want_leading=True)
        self.failUnless(token1.is_whitespace())

    def testComment1(self):
        tok = dns.tokenizer.Tokenizer(' ;foo\n')
        token1 = tok.get()
        self.failUnless(token1.is_eol())

    def testComment2(self):
        tok = dns.tokenizer.Tokenizer(' ;foo\n')
        token1 = tok.get(want_comment = True)
        token2 = tok.get()
        self.failUnless(token1 == Token(dns.tokenizer.COMMENT, 'foo') and
                        token2.is_eol())

    def testComment3(self):
        tok = dns.tokenizer.Tokenizer(' ;foo bar\n')
        token1 = tok.get(want_comment = True)
        token2 = tok.get()
        self.failUnless(token1 == Token(dns.tokenizer.COMMENT, 'foo bar') and
                        token2.is_eol())

    def testMultiline1(self):
        tok = dns.tokenizer.Tokenizer('( foo\n\n bar\n)')
        tokens = list(iter(tok))
        self.failUnless(tokens == [Token(dns.tokenizer.IDENTIFIER, 'foo'),
                                   Token(dns.tokenizer.IDENTIFIER, 'bar')])

    def testMultiline2(self):
        tok = dns.tokenizer.Tokenizer('( foo\n\n bar\n)\n')
        tokens = list(iter(tok))
        self.failUnless(tokens == [Token(dns.tokenizer.IDENTIFIER, 'foo'),
                                   Token(dns.tokenizer.IDENTIFIER, 'bar'),
                                   Token(dns.tokenizer.EOL, '\n')])
    def testMultiline3(self):
        def bad():
            tok = dns.tokenizer.Tokenizer('foo)')
            tokens = list(iter(tok))
        self.failUnlessRaises(dns.exception.SyntaxError, bad)

    def testMultiline4(self):
        def bad():
            tok = dns.tokenizer.Tokenizer('((foo)')
            tokens = list(iter(tok))
        self.failUnlessRaises(dns.exception.SyntaxError, bad)

    def testUnget1(self):
        tok = dns.tokenizer.Tokenizer('foo')
        t1 = tok.get()
        tok.unget(t1)
        t2 = tok.get()
        self.failUnless(t1 == t2 and t1.ttype == dns.tokenizer.IDENTIFIER and \
                        t1.value == 'foo')

    def testUnget2(self):
        def bad():
            tok = dns.tokenizer.Tokenizer('foo')
            t1 = tok.get()
            tok.unget(t1)
            tok.unget(t1)
        self.failUnlessRaises(dns.tokenizer.UngetBufferFull, bad)

    def testGetEOL1(self):
        tok = dns.tokenizer.Tokenizer('\n')
        t = tok.get_eol()
        self.failUnless(t == '\n')

    def testGetEOL2(self):
        tok = dns.tokenizer.Tokenizer('')
        t = tok.get_eol()
        self.failUnless(t == '')

    def testEscapedDelimiter1(self):
        tok = dns.tokenizer.Tokenizer(r'ch\ ld')
        t = tok.get()
        self.failUnless(t.ttype == dns.tokenizer.IDENTIFIER and t.value == r'ch\ ld')

    def testEscapedDelimiter2(self):
        tok = dns.tokenizer.Tokenizer(r'ch\032ld')
        t = tok.get()
        self.failUnless(t.ttype == dns.tokenizer.IDENTIFIER and t.value == r'ch\032ld')

    def testEscapedDelimiter3(self):
        tok = dns.tokenizer.Tokenizer(r'ch\ild')
        t = tok.get()
        self.failUnless(t.ttype == dns.tokenizer.IDENTIFIER and t.value == r'ch\ild')

    def testEscapedDelimiter1u(self):
        tok = dns.tokenizer.Tokenizer(r'ch\ ld')
        t = tok.get().unescape()
        self.failUnless(t.ttype == dns.tokenizer.IDENTIFIER and t.value == r'ch ld')

    def testEscapedDelimiter2u(self):
        tok = dns.tokenizer.Tokenizer(r'ch\032ld')
        t = tok.get().unescape()
        self.failUnless(t.ttype == dns.tokenizer.IDENTIFIER and t.value == 'ch ld')

    def testEscapedDelimiter3u(self):
        tok = dns.tokenizer.Tokenizer(r'ch\ild')
        t = tok.get().unescape()
        self.failUnless(t.ttype == dns.tokenizer.IDENTIFIER and t.value == r'child')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = update
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import unittest

import dns.update
import dns.rdata
import dns.rdataset

goodhex = '0001 2800 0001 0005 0007 0000' \
          '076578616d706c6500 0006 0001' \
          '03666f6fc00c 00ff 00ff 00000000 0000' \
          'c019 0001 00ff 00000000 0000' \
          '03626172c00c 0001 0001 00000000 0004 0a000005' \
          '05626c617a32c00c 00ff 00fe 00000000 0000' \
          'c049 0001 00fe 00000000 0000' \
          'c019 0001 00ff 00000000 0000' \
          'c019 0001 0001 0000012c 0004 0a000001' \
          'c019 0001 0001 0000012c 0004 0a000002' \
          'c035 0001 0001 0000012c 0004 0a000003' \
          'c035 0001 00fe 00000000 0004 0a000004' \
          '04626c617ac00c 0001 00ff 00000000 0000' \
          'c049 00ff 00ff 00000000 0000'

goodwire = goodhex.replace(' ', '').decode('hex_codec')

update_text="""id 1
opcode UPDATE
rcode NOERROR
;ZONE
example. IN SOA
;PREREQ
foo ANY ANY
foo ANY A
bar 0 IN A 10.0.0.5
blaz2 NONE ANY
blaz2 NONE A
;UPDATE
foo ANY A
foo 300 IN A 10.0.0.1
foo 300 IN A 10.0.0.2
bar 300 IN A 10.0.0.3
bar 0 NONE A 10.0.0.4
blaz ANY A
blaz2 ANY ANY
"""

class UpdateTestCase(unittest.TestCase):

    def test_to_wire1(self):
        update = dns.update.Update('example')
        update.id = 1
        update.present('foo')
        update.present('foo', 'a')
        update.present('bar', 'a', '10.0.0.5')
        update.absent('blaz2')
        update.absent('blaz2', 'a')
        update.replace('foo', 300, 'a', '10.0.0.1', '10.0.0.2')
        update.add('bar', 300, 'a', '10.0.0.3')
        update.delete('bar', 'a', '10.0.0.4')
        update.delete('blaz','a')
        update.delete('blaz2')
        self.failUnless(update.to_wire() == goodwire)

    def test_to_wire2(self):
        update = dns.update.Update('example')
        update.id = 1
        update.present('foo')
        update.present('foo', 'a')
        update.present('bar', 'a', '10.0.0.5')
        update.absent('blaz2')
        update.absent('blaz2', 'a')
        update.replace('foo', 300, 'a', '10.0.0.1', '10.0.0.2')
        update.add('bar', 300, dns.rdata.from_text(1, 1, '10.0.0.3'))
        update.delete('bar', 'a', '10.0.0.4')
        update.delete('blaz','a')
        update.delete('blaz2')
        self.failUnless(update.to_wire() == goodwire)

    def test_to_wire3(self):
        update = dns.update.Update('example')
        update.id = 1
        update.present('foo')
        update.present('foo', 'a')
        update.present('bar', 'a', '10.0.0.5')
        update.absent('blaz2')
        update.absent('blaz2', 'a')
        update.replace('foo', 300, 'a', '10.0.0.1', '10.0.0.2')
        update.add('bar', dns.rdataset.from_text(1, 1, 300, '10.0.0.3'))
        update.delete('bar', 'a', '10.0.0.4')
        update.delete('blaz','a')
        update.delete('blaz2')
        self.failUnless(update.to_wire() == goodwire)

    def test_from_text1(self):
        update = dns.message.from_text(update_text)
        w = update.to_wire(origin=dns.name.from_text('example'),
                           want_shuffle=False)
        self.failUnless(w == goodwire)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = zone
# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import cStringIO
import filecmp
import os
import unittest

import dns.exception
import dns.rdata
import dns.rdataclass
import dns.rdatatype
import dns.rrset
import dns.zone

example_text = """$TTL 3600
$ORIGIN example.
@ soa foo bar 1 2 3 4 5
@ ns ns1
@ ns ns2
ns1 a 10.0.0.1
ns2 a 10.0.0.2
$TTL 300
$ORIGIN foo.example.
bar mx 0 blaz
"""

example_text_output = """@ 3600 IN SOA foo bar 1 2 3 4 5
@ 3600 IN NS ns1
@ 3600 IN NS ns2
bar.foo 300 IN MX 0 blaz.foo
ns1 3600 IN A 10.0.0.1
ns2 3600 IN A 10.0.0.2
"""

something_quite_similar = """@ 3600 IN SOA foo bar 1 2 3 4 5
@ 3600 IN NS ns1
@ 3600 IN NS ns2
bar.foo 300 IN MX 0 blaz.foo
ns1 3600 IN A 10.0.0.1
ns2 3600 IN A 10.0.0.3
"""

something_different = """@ 3600 IN SOA fooa bar 1 2 3 4 5
@ 3600 IN NS ns11
@ 3600 IN NS ns21
bar.fooa 300 IN MX 0 blaz.fooa
ns11 3600 IN A 10.0.0.11
ns21 3600 IN A 10.0.0.21
"""

ttl_example_text = """$TTL 1h
$ORIGIN example.
@ soa foo bar 1 2 3 4 5
@ ns ns1
@ ns ns2
ns1 1d1s a 10.0.0.1
ns2 1w1D1h1m1S a 10.0.0.2
"""

no_soa_text = """$TTL 1h
$ORIGIN example.
@ ns ns1
@ ns ns2
ns1 1d1s a 10.0.0.1
ns2 1w1D1h1m1S a 10.0.0.2
"""

no_ns_text = """$TTL 1h
$ORIGIN example.
@ soa foo bar 1 2 3 4 5
"""

include_text = """$INCLUDE "example"
"""

bad_directive_text = """$FOO bar
$ORIGIN example.
@ soa foo bar 1 2 3 4 5
@ ns ns1
@ ns ns2
ns1 1d1s a 10.0.0.1
ns2 1w1D1h1m1S a 10.0.0.2
"""

_keep_output = False

class ZoneTestCase(unittest.TestCase):

    def testFromFile1(self):
        z = dns.zone.from_file('example', 'example')
        ok = False
        try:
            z.to_file('example1.out', nl='\x0a')
            ok = filecmp.cmp('example1.out', 'example1.good')
        finally:
            if not _keep_output:
                os.unlink('example1.out')
        self.failUnless(ok)

    def testFromFile2(self):
        z = dns.zone.from_file('example', 'example', relativize=False)
        ok = False
        try:
            z.to_file('example2.out', relativize=False, nl='\x0a')
            ok = filecmp.cmp('example2.out', 'example2.good')
        finally:
            if not _keep_output:
                os.unlink('example2.out')
        self.failUnless(ok)

    def testFromText(self):
        z = dns.zone.from_text(example_text, 'example.', relativize=True)
        f = cStringIO.StringIO()
        names = z.nodes.keys()
        names.sort()
        for n in names:
            print >> f, z[n].to_text(n)
        self.failUnless(f.getvalue() == example_text_output)
            
    def testTorture1(self):
        #
        # Read a zone containing all our supported RR types, and
        # for each RR in the zone, convert the rdata into wire format
        # and then back out, and see if we get equal rdatas.
        #
        f = cStringIO.StringIO()
        o = dns.name.from_text('example.')
        z = dns.zone.from_file('example', o)
        for (name, node) in z.iteritems():
            for rds in node:
                for rd in rds:
                    f.seek(0)
                    f.truncate()
                    rd.to_wire(f, origin=o)
                    wire = f.getvalue()
                    rd2 = dns.rdata.from_wire(rds.rdclass, rds.rdtype,
                                              wire, 0, len(wire),
                                              origin = o)
                    self.failUnless(rd == rd2)

    def testEqual(self):
        z1 = dns.zone.from_text(example_text, 'example.', relativize=True)
        z2 = dns.zone.from_text(example_text_output, 'example.',
                                relativize=True)
        self.failUnless(z1 == z2)

    def testNotEqual1(self):
        z1 = dns.zone.from_text(example_text, 'example.', relativize=True)
        z2 = dns.zone.from_text(something_quite_similar, 'example.',
                                relativize=True)
        self.failUnless(z1 != z2)

    def testNotEqual2(self):
        z1 = dns.zone.from_text(example_text, 'example.', relativize=True)
        z2 = dns.zone.from_text(something_different, 'example.',
                                relativize=True)
        self.failUnless(z1 != z2)

    def testNotEqual3(self):
        z1 = dns.zone.from_text(example_text, 'example.', relativize=True)
        z2 = dns.zone.from_text(something_different, 'example2.',
                                relativize=True)
        self.failUnless(z1 != z2)

    def testFindRdataset1(self):
        z = dns.zone.from_text(example_text, 'example.', relativize=True)
        rds = z.find_rdataset('@', 'soa')
        exrds = dns.rdataset.from_text('IN', 'SOA', 300, 'foo bar 1 2 3 4 5')
        self.failUnless(rds == exrds)

    def testFindRdataset2(self):
        def bad():
            z = dns.zone.from_text(example_text, 'example.', relativize=True)
            rds = z.find_rdataset('@', 'loc')
        self.failUnlessRaises(KeyError, bad)

    def testFindRRset1(self):
        z = dns.zone.from_text(example_text, 'example.', relativize=True)
        rrs = z.find_rrset('@', 'soa')
        exrrs = dns.rrset.from_text('@', 300, 'IN', 'SOA', 'foo bar 1 2 3 4 5')
        self.failUnless(rrs == exrrs)

    def testFindRRset2(self):
        def bad():
            z = dns.zone.from_text(example_text, 'example.', relativize=True)
            rrs = z.find_rrset('@', 'loc')
        self.failUnlessRaises(KeyError, bad)

    def testGetRdataset1(self):
        z = dns.zone.from_text(example_text, 'example.', relativize=True)
        rds = z.get_rdataset('@', 'soa')
        exrds = dns.rdataset.from_text('IN', 'SOA', 300, 'foo bar 1 2 3 4 5')
        self.failUnless(rds == exrds)

    def testGetRdataset2(self):
        z = dns.zone.from_text(example_text, 'example.', relativize=True)
        rds = z.get_rdataset('@', 'loc')
        self.failUnless(rds == None)

    def testGetRRset1(self):
        z = dns.zone.from_text(example_text, 'example.', relativize=True)
        rrs = z.get_rrset('@', 'soa')
        exrrs = dns.rrset.from_text('@', 300, 'IN', 'SOA', 'foo bar 1 2 3 4 5')
        self.failUnless(rrs == exrrs)

    def testGetRRset2(self):
        z = dns.zone.from_text(example_text, 'example.', relativize=True)
        rrs = z.get_rrset('@', 'loc')
        self.failUnless(rrs == None)

    def testReplaceRdataset1(self):
        z = dns.zone.from_text(example_text, 'example.', relativize=True)
        rdataset = dns.rdataset.from_text('in', 'ns', 300, 'ns3', 'ns4')
        z.replace_rdataset('@', rdataset)
        rds = z.get_rdataset('@', 'ns')
        self.failUnless(rds is rdataset)

    def testReplaceRdataset2(self):
        z = dns.zone.from_text(example_text, 'example.', relativize=True)
        rdataset = dns.rdataset.from_text('in', 'txt', 300, '"foo"')
        z.replace_rdataset('@', rdataset)
        rds = z.get_rdataset('@', 'txt')
        self.failUnless(rds is rdataset)

    def testDeleteRdataset1(self):
        z = dns.zone.from_text(example_text, 'example.', relativize=True)
        z.delete_rdataset('@', 'ns')
        rds = z.get_rdataset('@', 'ns')
        self.failUnless(rds is None)

    def testDeleteRdataset2(self):
        z = dns.zone.from_text(example_text, 'example.', relativize=True)
        z.delete_rdataset('ns1', 'a')
        node = z.get_node('ns1')
        self.failUnless(node is None)

    def testNodeFindRdataset1(self):
        z = dns.zone.from_text(example_text, 'example.', relativize=True)
        node = z['@']
        rds = node.find_rdataset(dns.rdataclass.IN, dns.rdatatype.SOA)
        exrds = dns.rdataset.from_text('IN', 'SOA', 300, 'foo bar 1 2 3 4 5')
        self.failUnless(rds == exrds)

    def testNodeFindRdataset2(self):
        def bad():
            z = dns.zone.from_text(example_text, 'example.', relativize=True)
            node = z['@']
            rds = node.find_rdataset(dns.rdataclass.IN, dns.rdatatype.LOC)
        self.failUnlessRaises(KeyError, bad)

    def testNodeGetRdataset1(self):
        z = dns.zone.from_text(example_text, 'example.', relativize=True)
        node = z['@']
        rds = node.get_rdataset(dns.rdataclass.IN, dns.rdatatype.SOA)
        exrds = dns.rdataset.from_text('IN', 'SOA', 300, 'foo bar 1 2 3 4 5')
        self.failUnless(rds == exrds)

    def testNodeGetRdataset2(self):
        z = dns.zone.from_text(example_text, 'example.', relativize=True)
        node = z['@']
        rds = node.get_rdataset(dns.rdataclass.IN, dns.rdatatype.LOC)
        self.failUnless(rds == None)

    def testNodeDeleteRdataset1(self):
        z = dns.zone.from_text(example_text, 'example.', relativize=True)
        node = z['@']
        rds = node.delete_rdataset(dns.rdataclass.IN, dns.rdatatype.SOA)
        rds = node.get_rdataset(dns.rdataclass.IN, dns.rdatatype.SOA)
        self.failUnless(rds == None)

    def testNodeDeleteRdataset2(self):
        z = dns.zone.from_text(example_text, 'example.', relativize=True)
        node = z['@']
        rds = node.delete_rdataset(dns.rdataclass.IN, dns.rdatatype.LOC)
        rds = node.get_rdataset(dns.rdataclass.IN, dns.rdatatype.LOC)
        self.failUnless(rds == None)

    def testIterateRdatasets(self):
        z = dns.zone.from_text(example_text, 'example.', relativize=True)
        ns = [n for n, r in z.iterate_rdatasets('A')]
        ns.sort()
        self.failUnless(ns == [dns.name.from_text('ns1', None),
                               dns.name.from_text('ns2', None)])

    def testIterateAllRdatasets(self):
        z = dns.zone.from_text(example_text, 'example.', relativize=True)
        ns = [n for n, r in z.iterate_rdatasets()]
        ns.sort()
        self.failUnless(ns == [dns.name.from_text('@', None),
                               dns.name.from_text('@', None),
                               dns.name.from_text('bar.foo', None),
                               dns.name.from_text('ns1', None),
                               dns.name.from_text('ns2', None)])

    def testIterateRdatas(self):
        z = dns.zone.from_text(example_text, 'example.', relativize=True)
        l = list(z.iterate_rdatas('A'))
        l.sort()
        exl = [(dns.name.from_text('ns1', None),
                3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.1')),
               (dns.name.from_text('ns2', None),
                3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.2'))]
        self.failUnless(l == exl)

    def testIterateAllRdatas(self):
        z = dns.zone.from_text(example_text, 'example.', relativize=True)
        l = list(z.iterate_rdatas())
        l.sort()
        exl = [(dns.name.from_text('@', None),
                3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.NS,
                                    'ns1')),
               (dns.name.from_text('@', None),
                3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.NS,
                                    'ns2')),
               (dns.name.from_text('@', None),
                3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.SOA,
                                    'foo bar 1 2 3 4 5')),
               (dns.name.from_text('bar.foo', None),
                300,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.MX,
                                    '0 blaz.foo')),
               (dns.name.from_text('ns1', None),
                3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.1')),
               (dns.name.from_text('ns2', None),
                3600,
                dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A,
                                    '10.0.0.2'))]
        self.failUnless(l == exl)

    def testTTLs(self):
        z = dns.zone.from_text(ttl_example_text, 'example.', relativize=True)
        n = z['@']
        rds = n.get_rdataset(dns.rdataclass.IN, dns.rdatatype.SOA)
        self.failUnless(rds.ttl == 3600)
        n = z['ns1']
        rds = n.get_rdataset(dns.rdataclass.IN, dns.rdatatype.A)
        self.failUnless(rds.ttl == 86401)
        n = z['ns2']
        rds = n.get_rdataset(dns.rdataclass.IN, dns.rdatatype.A)
        self.failUnless(rds.ttl == 694861)

    def testNoSOA(self):
        def bad():
            z = dns.zone.from_text(no_soa_text, 'example.',
                                   relativize=True)
        self.failUnlessRaises(dns.zone.NoSOA, bad)

    def testNoNS(self):
        def bad():
            z = dns.zone.from_text(no_ns_text, 'example.',
                                   relativize=True)
        self.failUnlessRaises(dns.zone.NoNS, bad)

    def testInclude(self):
        z1 = dns.zone.from_text(include_text, 'example.', relativize=True,
                                allow_include=True)
        z2 = dns.zone.from_file('example', 'example.', relativize=True)
        self.failUnless(z1 == z2)

    def testBadDirective(self):
        def bad():
            z = dns.zone.from_text(bad_directive_text, 'example.',
                                   relativize=True)
        self.failUnlessRaises(dns.exception.SyntaxError, bad)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
