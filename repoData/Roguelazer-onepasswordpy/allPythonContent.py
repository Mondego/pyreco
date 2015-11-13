__FILENAME__ = crypt_util
from __future__ import print_function

import base64
import binascii
import math
import struct

import Crypto.Cipher.AES
import Crypto.Hash.HMAC

from . import padding
from . import pbkdf1
from . import pbkdf2
from .hashes import MD5, SHA256, SHA512
from .util import make_utf8


# 8 bytes for "opdata1"
# 8 bytes for plaintext length
# 16 bytes for IV
# 16 bytes for mimum cryptext size
# 32 bytes for HMAC-SHA256
OPDATA1_MINIMUM_SIZE = 80


DEFAULT_PBKDF_ITERATIONS = 1000
MINIMUM_PBKDF_ITERATIONS = 1000

A_AES_SIZE = 128
C_AES_SIZE = 256
KEY_SIZE = {
    128: 16,
    192: 24,
    256: 32,
}

SALT_SIZE = 8
SALT_MARKER = b'Salted__'


class BadKeyError(Exception):
    pass


def a_decrypt_key(key_obj, password, aes_size=A_AES_SIZE):
    if not isinstance(password, bytes):
        password = password.encode('utf-8')
    key_size = KEY_SIZE[aes_size]
    data = base64.b64decode(key_obj['data'])
    salt = b'\x00'*SALT_SIZE
    if data[:len(SALT_MARKER)] == SALT_MARKER:
        salt = data[len(SALT_MARKER):len(SALT_MARKER) + SALT_SIZE]
        data = data[len(SALT_MARKER) + SALT_SIZE:]
    iterations = max(int(key_obj.get('iterations', DEFAULT_PBKDF_ITERATIONS)), MINIMUM_PBKDF_ITERATIONS)
    keys = pbkdf2.pbkdf2_sha1(password=password, salt=salt, length=2*key_size, iterations=iterations)
    key = keys[:key_size]
    iv = keys[key_size:]
    aes_er = Crypto.Cipher.AES.new(key, Crypto.Cipher.AES.MODE_CBC, iv)
    potential_key = padding.pkcs5_unpad(aes_er.decrypt(data))
    validation = base64.b64decode(key_obj['validation'])
    decrypted_validation = a_decrypt_item(validation, potential_key)
    if decrypted_validation != potential_key:
        raise BadKeyError("Validation did not match")
    return potential_key


def hexize(byte_string):
    return binascii.hexlify(byte_string).upper()


def unhexize(hex_string):
    return binascii.unhexlify(hex_string)
    res = []
    if isinstance(hex_string, bytes):
        hex_string = hex_string.decode('ascii')
    for i in range(int(math.ceil(len(hex_string)/2.0))):
        conv = hex_string[2*i] + hex_string[2*i+1]
        res.append(int(conv, 16))
    return ''.join(chr(i) for i in res)


def a_decrypt_item(data, key, aes_size=A_AES_SIZE):
    key_size = KEY_SIZE[aes_size]
    if data[:len(SALT_MARKER)] == SALT_MARKER:
        salt = data[len(SALT_MARKER):len(SALT_MARKER) + SALT_SIZE]
        data = data[len(SALT_MARKER) + SALT_SIZE:]
        pb_gen = pbkdf1.PBKDF1(key, salt)
        nkey = pb_gen.read(key_size)
        iv = pb_gen.read(key_size)
    else:
        nkey = MD5.new(key).digest()
        iv = '\x00'*key_size
    aes_er = Crypto.Cipher.AES.new(nkey, Crypto.Cipher.AES.MODE_CBC, iv)
    return padding.pkcs5_unpad(aes_er.decrypt(data))


def opdata1_unpack(data):
    HEADER_LENGTH = 8
    TOTAL_HEADER_LENGTH = 32
    HMAC_LENGTH = 32
    if data[:HEADER_LENGTH] != b"opdata01":
        try:
            data = base64.b64decode(data)
        except binascii.Error:
            raise TypeError("expected opdata1 format message")
    if data[:HEADER_LENGTH] != b"opdata01":
        raise TypeError("expected opdata1 format message")
    plaintext_length, iv = struct.unpack("<Q16s", data[HEADER_LENGTH:TOTAL_HEADER_LENGTH])
    cryptext = data[TOTAL_HEADER_LENGTH:-HMAC_LENGTH]
    expected_hmac = data[-HMAC_LENGTH:]
    hmac_d_data = data[:-HMAC_LENGTH]
    return plaintext_length, iv, cryptext, expected_hmac, hmac_d_data


def opdata1_decrypt_key(data, key, hmac_key, aes_size=C_AES_SIZE, ignore_hmac=False):
    """Decrypt encrypted item keys"""
    hmac_key = make_utf8(hmac_key)
    key_size = KEY_SIZE[aes_size]
    iv, cryptext, expected_hmac = struct.unpack("=16s64s32s", data)
    if not ignore_hmac:
        verifier = Crypto.Hash.HMAC.new(key=hmac_key, msg=(iv + cryptext), digestmod=SHA256)
        if verifier.digest() != expected_hmac:
            raise ValueError("HMAC did not match for opdata1 key")
    decryptor = Crypto.Cipher.AES.new(key, Crypto.Cipher.AES.MODE_CBC, iv)
    decrypted = decryptor.decrypt(cryptext)
    crypto_key, mac_key = decrypted[:key_size], decrypted[key_size:]
    return crypto_key, mac_key


def opdata1_decrypt_master_key(data, key, hmac_key, aes_size=C_AES_SIZE, ignore_hmac=False):
    key_size = KEY_SIZE[aes_size]
    bare_key = opdata1_decrypt_item(data, key, hmac_key, aes_size=aes_size, ignore_hmac=ignore_hmac)
    # XXX: got the following step from jeff@agilebits (as opposed to the
    # docs anywhere)
    hashed_key = SHA512.new(bare_key).digest()
    return hashed_key[:key_size], hashed_key[key_size:]


def opdata1_decrypt_item(data, key, hmac_key, aes_size=C_AES_SIZE, ignore_hmac=False):
    key_size = KEY_SIZE[aes_size]
    assert len(key) == key_size
    assert len(data) >= OPDATA1_MINIMUM_SIZE
    plaintext_length, iv, cryptext, expected_hmac, hmac_d_data = opdata1_unpack(data)
    if not ignore_hmac:
        verifier = Crypto.Hash.HMAC.new(key=hmac_key, msg=hmac_d_data, digestmod=SHA256)
        got_hmac = verifier.digest()
        if len(got_hmac) != len(expected_hmac):
            raise ValueError("Got unexpected HMAC length (expected %d bytes, got %d bytes)" % (
                len(expected_hmac),
                len(got_hmac)
            ))
        if got_hmac != expected_hmac:
            raise ValueError("HMAC did not match for opdata1 record")
    decryptor = Crypto.Cipher.AES.new(key, Crypto.Cipher.AES.MODE_CBC, iv)
    decrypted = decryptor.decrypt(cryptext)
    unpadded = padding.ab_unpad(decrypted, plaintext_length)
    return unpadded


def opdata1_derive_keys(password, salt, iterations=1000, aes_size=C_AES_SIZE):
    """Key derivation function for .cloudkeychain files"""
    key_size = KEY_SIZE[aes_size]
    password = password.encode('utf-8')
    # TODO: is this necessary? does the hmac on ios actually include the
    # trailing nul byte?
    password += b'\x00'
    keys = pbkdf2.pbkdf2_sha512(password=password, salt=salt, length=2*key_size, iterations=iterations)
    key1 = keys[:key_size]
    key2 = keys[key_size:]
    return key1, key2


def opdata1_verify_overall_hmac(hmac_key, item):
    verifier = Crypto.Hash.HMAC.new(key=hmac_key, digestmod=SHA256)
    for key, value in sorted(item.items()):
        if key == 'hmac':
            continue
        if isinstance(value, bool):
            value = str(int(value)).encode('utf-8')
        else:
            value = str(value).encode('utf-8')
        verifier.update(key.encode('utf-8'))
        verifier.update(value)
    expected = base64.b64decode(item['hmac'])
    got = verifier.digest()
    if got != expected:
        raise ValueError("HMAC did not match for data dictionary")

########NEW FILE########
__FILENAME__ = hashes
try:
    from Crypto.Hash import MD5
    from Crypto.Hash import SHA as SHA1
    from Crypto.Hash import SHA256
    from Crypto.Hash import SHA512
except ImportError:
    import hashlib
    MD5 = hashlib.md5
    SHA256 = hashlib.sha256
    SHA512 = hashlib.sha512

########NEW FILE########
__FILENAME__ = item
import simplejson
import datetime

C_CATEGORIES = {
    '001': 'Login',
    '002': 'Credit Card',
    '003': 'Secure Note',
    '004': 'Identity',
    '005': 'Password',
    '099': 'Tombstone',
    '100': 'Software License',
    '101': 'Bank Account',
    '102': 'Database',
    '103': 'Driver License',
    '104': 'Outdoor License',
    '105': 'Membership',
    '106': 'Passport',
    '107': 'Rewards',
    '108': 'SSN',
    '109': 'Router',
    '110': 'Server',
    '111': 'Email',
}


class AItem(object):
    def __init__(self, keychain):
        self.keychain = keychain

    @classmethod
    def new_from_file(cls, path, keychain):
        o = cls(keychain)
        o.load_from(path)
        return o

    def load_from(self, path):
        with open(path, "r") as f:
            data = simplejson.load(f)
        self.uuid = data['uuid']
        self.data = data
        self.title = self.data['title']
        if 'keyID' in data:
            identifier = data['keyID']
        elif 'securityLevel' in data:
            identifier = self.keychain.levels[data['securityLevel']]
        else:
            raise KeyError("Neither keyID or securityLevel present in %s" % self.uuid)
        self.key_identifier = identifier

    def decrypt(self):
        return simplejson.loads(self.keychain.decrypt(self.key_identifier, self.data['encrypted']))

    def __repr__(self):
        return '%s<uuid=%s, keyid=%s>' % (self.__class__.__name__, self.uuid, self.key_identifier)


class CItem(object):
    def __init__(self, keychain, d):
        self.keychain = keychain
        self.uuid = d['uuid']
        self.category = C_CATEGORIES[d['category']]
        self.updated_at = datetime.datetime.fromtimestamp(d['updated'])
        self.overview = simplejson.loads(self.keychain.decrypt_overview(d['o']))
        self.title = self.overview['title']
        self.encrypted_data = d['k'], d['d']

    def __repr__(self):
        return '%s<uuid=%s, cat=%s>' % (
            self.__class__.__name__,
            self.uuid,
            self.category,
        )

    def decrypt(self):
        return simplejson.loads(self.keychain.decrypt_data(*self.encrypted_data))

########NEW FILE########
__FILENAME__ = keychain
import base64
import glob
import os.path

import simplejson

from . import crypt_util
from . import padding
from .item import AItem, CItem

EXPECTED_VERSION_MIN = 30000
EXPECTED_VERSION_MAX = 40000


class _AbstractKeychain(object):
    """Implementation of common keychain logic (MP design, etc)."""

    def __init__(self, path):
        self._open(path)

    def _open(self, path):
        self.base_path = path
        self.check_paths()
        self.check_version()

    def check_paths(self):
        if not(os.path.exists(self.base_path)):
            raise ValueError("Proported 1Password keychain %s does not exist" % self.base_path)

    def check_version(self):
        pass

    def get_by_uuid(self, uuid):
        try:
            return [i for i in self.items if i.uuid == uuid][0]
        except Exception:
            raise KeyError(uuid)


class AKeychain(_AbstractKeychain):
    """Implementation of the classic .agilekeychain storage format"""

    def check_paths(self):
        super(AKeychain, self).check_paths()
        files_to_check = {
            'keys': os.path.join(self.base_path, 'data', 'default', 'encryptionKeys.js')
        }
        for descriptor, expected_path in files_to_check.items():
            if not os.path.exists(expected_path):
                raise Exception("Missing %s, expected at %s" % (descriptor, expected_path))

    def check_version(self):
        super(AKeychain, self).check_version()
        version_file = os.path.join(self.base_path, 'config', 'buildnum')
        if not os.path.exists(version_file):
            return  # AgileBits stopped writing this file in newer versions
        with open(version_file, 'r') as f:
            version_num = int(f.read().strip())
        if version_num < EXPECTED_VERSION_MIN or version_num > EXPECTED_VERSION_MAX:
            raise ValueError("I only understand 1Password builds in [%s,%s]" % (
                EXPECTED_VERSION_MIN,
                EXPECTED_VERSION_MAX
            ))

    def unlock(self, password):
        keys = self._load_keys(password)
        self._load_items(keys)

    def _load_keys(self, password):
        self.keys = {}
        keys_file = os.path.join(self.base_path, 'data', 'default', 'encryptionKeys.js')
        with open(keys_file, 'r') as f:
            data = simplejson.load(f)
        levels = dict((l, v) for (l, v) in data.items() if l != 'list')
        for level, identifier in levels.items():
            keys = [k for k in data['list'] if k.get('identifier') == identifier]
            assert len(keys) == 1, "There should be exactly one key for level %s, got %d" % (level, len(keys))
            key = keys[0]
            self.keys[identifier] = crypt_util.a_decrypt_key(key, password)
        self.levels = levels

    def _load_items(self, keys):
        items = []
        for f in glob.glob(os.path.join(self.base_path, 'data', 'default', '*.1password')):
            items.append(AItem.new_from_file(f, self))
        self.items = items

    def decrypt(self, keyid, string):
        if keyid not in self.keys:
            raise ValueError("Item encrypted with unknown key %s" % keyid)
        string = base64.b64decode(string)
        return crypt_util.a_decrypt_item(string, self.keys[keyid])


class CKeychain(_AbstractKeychain):
    """Implementation of the modern .cloudkeychain format

    Documentation at http://learn.agilebits.com/1Password4/Security/keychain-design.html
    """

    INITIAL_KEY_OFFSET = 12
    KEY_SIZE = 32

    def check_paths(self):
        super(CKeychain, self).check_paths()
        files_to_check = {
            'profile': os.path.join(self.base_path, 'default', 'profile.js'),
        }
        for descriptor, expected_path in files_to_check.items():
            if not os.path.exists(expected_path):
                raise Exception("Missing %s, expected at %s" % (descriptor, expected_path))

    def unlock(self, password):
        self._load_keys(password)
        self._load_items()

    def _load_keys(self, password):
        with open(os.path.join(self.base_path, 'default', 'profile.js'), 'r') as f:
            ds = f.read()[self.INITIAL_KEY_OFFSET:-1]
            data = simplejson.loads(ds)
        super_master_key, super_hmac_key = crypt_util.opdata1_derive_keys(
            password,
            base64.b64decode(data['salt']),
            iterations=int(data['iterations'])
        )
        self.master_key, self.master_hmac = crypt_util.opdata1_decrypt_master_key(
            base64.b64decode(data['masterKey']),
            super_master_key,
            super_hmac_key
        )
        self.overview_key, self.overview_hmac = crypt_util.opdata1_decrypt_master_key(
            base64.b64decode(data['overviewKey']),
            super_master_key,
            super_hmac_key
        )

    def _load_items(self):
        items = []
        items_by_category = {}
        for band in range(0, 15):
            band = hex(band)[-1:].upper()
            path = os.path.join(self.base_path, 'default', 'band_%s.js' % band)
            if not os.path.exists(path):
                continue
            with open(path) as f:
                items.extend(self._load_band_file(f))
        for item in items:
            items_by_category.setdefault(item.category, [])
            items_by_category[item.category].append(item)
        self.items = items
        self.items_by_category = items_by_category

    def _load_band_file(self, f):
        items = []
        band_data = simplejson.loads(f.read()[3:-2])
        for uuid, blob in band_data.items():
            crypt_util.opdata1_verify_overall_hmac(self.overview_hmac, blob)
            items.append(CItem(self, blob))
        return items

    def decrypt_overview(self, blob):
        return crypt_util.opdata1_decrypt_item(
            base64.b64decode(blob),
            self.overview_key,
            self.overview_hmac
        )

    def decrypt_data(self, key_blob, data_blob):
        key, hmac = crypt_util.opdata1_decrypt_key(
            base64.b64decode(key_blob),
            self.master_key,
            self.master_hmac
        )
        return crypt_util.opdata1_decrypt_item(
            base64.b64decode(data_blob),
            key,
            hmac
        )

########NEW FILE########
__FILENAME__ = padding
from . import random_util

import six


def pkcs5_pad(string, block_size=16):
    """PKCS#5 pad the given string to the given block size

    Aguments:
        string - the string to pad. should be bytes()
        block_size - the amount to pad to in bytes
    """
    if block_size <= 0:
        raise ValueError("block_size must be a positive integer")
    return string + (block_size - len(string) % block_size) * six.int2byte(block_size - len(string) % block_size)


def pkcs5_unpad(string):
    """PKCS#5 unpad the given string"""
    # preserve empty strings
    if not string:
        return string
    amount_of_padding = six.indexbytes(string, -1)
    return string[:-amount_of_padding]


def ab_pad(string, block_size=16, random_generator=random_util.sort_of_random_bytes):
    """AgileBits custom pad a string to the given block size

    Arguments:
        string - The string to pad
        block_size - Block size in bytes
        random_generator - A function that returns random bytes
    """
    bytes_to_pad = block_size - (len(string) % block_size)
    padding = random_generator(bytes_to_pad)
    return padding + string


def ab_unpad(string, plaintext_size):
    """AgileBits custom unpad a string with the given known plaintext size

    Arguments:
        string - The string to unpad
        plaintext_size - The target length in bytes
    """
    return string[len(string)-plaintext_size:]

########NEW FILE########
__FILENAME__ = pbkdf1
from __future__ import absolute_import
from __future__ import print_function

from .util import make_utf8

import hashlib
import math

import six


class PBKDF1(object):
    """Reimplement the simple PKCS#5 v1.5 key derivation function from
    OpenSSL. Tries to look like PBKDF2 as much as possible.

    (as in `openssl enc`). Technically, this is only PBKDF1 if the key size
    is 20 bytes or less. But whatever.
    """

    # TODO: Call openssl's EVP_BytesToKey instead of reimplementing by hand
    # (through m2crypto?). Alternatively, figure out how to make PyCrypto's
    # built-in PBKDF1 work without yelling at me that MD5 is an unacceptable
    # hash algorithm
    def __init__(self, key, salt, hash_algo=hashlib.md5, iterations=1):
        if salt is None:
            salt = b'\x00'*(int(math.ceil(len(key)/2)))
        key, salt = make_utf8(key, salt)
        self.key = key
        self.salt = salt
        self._ks = key + salt
        self._d = [b'']
        self._i = 1
        self.result = bytes()
        self._read = 0
        self.iterations = iterations
        self.hash_algo = hash_algo

    def read(self, nbytes):
        while len(self.result) - self._read < nbytes:
            tohash = self._d[self._i - 1] + self._ks
            for hash_application in six.moves.range(self.iterations):
                tohash = self.hash_algo(tohash).digest()
            self._d.append(tohash)
            self.result += tohash
            self._i += 1
        to_return = self.result[self._read:self._read + nbytes]
        self._read += nbytes
        return to_return

########NEW FILE########
__FILENAME__ = pbkdf2
from __future__ import absolute_import

try:
    from ._pbkdf2_nettle import pbkdf2_sha1, pbkdf2_sha512
    # make pyflakes happy
    pbkdf2_sha1 = pbkdf2_sha1
    pbkdf2_sha512 = pbkdf2_sha512
except ImportError:
    try:
        from ._pbkdf2_m2crypto import pbkdf2_sha1, pbkdf2_sha512
        # make pyflakes happy
        pbkdf2_sha1 = pbkdf2_sha1
        pbkdf2_sha512 = pbkdf2_sha512
    except ImportError:
        from ._pbkdf2_pycrypto import pbkdf2_sha1, pbkdf2_sha512
        # make pyflakes happy
        pbkdf2_sha1 = pbkdf2_sha1
        pbkdf2_sha512 = pbkdf2_sha512

########NEW FILE########
__FILENAME__ = random_util
"""Random sources"""

import os
import random

import six


# If someone's truly paranoid and wants to contribute
# code that knows how to talk to an EGD for really really
# strong randomness, I would not say no to that. but it's
# almost always safer/smarter to just use /dev/random and
# trust that your sysadmin knows how to use the EGD


def really_random_bytes(l):
    """Return bytes that should be cryptographically strong (generally, a
    PRNG regularly seeded with real-world entropy"""
    with open("/dev/random", "rb") as f:
        return f.read(l)


def sort_of_random_bytes(l):
    """Return bytes that may be cryptographically strong or may be
    PRNG-based depending on the operating system status"""
    return os.urandom(l)


def barely_random_bytes(l):
    """Return bytes that appear random but are not cryptographically
    strong"""
    return b''.join(six.int2byte(random.randrange(0, 255)) for b in six.moves.range(l))


def not_random_bytes(l):
    """Return bytes that are not at all random, but suitable for use as
    testing filler"""
    return b''.join(six.int2byte(x % 255) for x in six.moves.range(l))

########NEW FILE########
__FILENAME__ = util
def make_utf8(*args):
    rv = []
    for arg in args:
        if isinstance(arg, bytes):
            rv.append(arg)
        else:
            rv.append(arg.encode('utf-8'))
    if len(rv) == 1:
        return rv[0]
    else:
        return rv

########NEW FILE########
__FILENAME__ = _pbkdf2_m2crypto
import struct

from Crypto.Util.strxor import strxor
import M2Crypto.EVP


def pbkdf2_sha1(password, salt, length, iterations):
    return M2Crypto.EVP.pbkdf2(password=password, salt=salt, iter=iterations, keylen=length)


def pbkdf2_sha512(password, salt, length, iterations):
    hmac = M2Crypto.EVP.HMAC(key=password, algo='sha512')
    generated_data = 0
    generated_chunks = []
    # cache the thing we're iterating over
    iterator = range(iterations - 1)
    i = 1
    while generated_data < length:
        hmac.reset(key=password)
        hmac.update(salt)
        hmac.update(struct.pack(">I", i))
        U = U_1 = hmac.final()
        for j in iterator:
            hmac.reset(key=password)
            hmac.update(U_1)
            U_1 = hmac.final()
            U = strxor(U, U_1)
        generated_chunks.append(U)
        generated_data += len(U)
        i += 1
    return "".join(generated_chunks)[:length]

########NEW FILE########
__FILENAME__ = _pbkdf2_nettle
import ctypes
import ctypes.util

"""Simple ctypes wrapper around nettle. Idea came from https://github.com/fredrikt/python-ndnkdf"""


_nettle = ctypes.cdll.LoadLibrary(ctypes.util.find_library('nettle'))
for function in ('nettle_hmac_sha1_update', 'nettle_hmac_sha512_update', 'nettle_hmac_sha1_digest', 'nettle_hmac_sha512_digest', 'nettle_pbkdf2'):
    if not hasattr(_nettle, function):
        raise ImportError(function)


def _pbkdf2(password, salt, length, iterations, hash_size, set_fn, update_fn, digest_fn):
    buf = ctypes.create_string_buffer(b'', size=max(length, hash_size))
    # TODO: 1024 bytes is almost definitely not the size of this structure
    shactx = ctypes.create_string_buffer(b'', size=1024)
    set_fn(ctypes.byref(shactx), len(password), password)
    _nettle.nettle_pbkdf2(
        ctypes.byref(shactx),
        update_fn,
        digest_fn,
        hash_size, int(iterations),
        len(salt), salt,
        max(length, hash_size), ctypes.byref(buf))
    return buf.raw[:length]


def pbkdf2_sha1(password, salt, length, iterations):
    return _pbkdf2(password, salt, length, iterations, 20, _nettle.nettle_hmac_sha1_set_key, _nettle.nettle_hmac_sha1_update, _nettle.nettle_hmac_sha1_digest)


def pbkdf2_sha512(password, salt, length, iterations):
    return _pbkdf2(password, salt, length, iterations, 64, _nettle.nettle_hmac_sha512_set_key, _nettle.nettle_hmac_sha512_update, _nettle.nettle_hmac_sha512_digest)

########NEW FILE########
__FILENAME__ = _pbkdf2_pycrypto
import Crypto.Hash.HMAC
import Crypto.Protocol.KDF

from .hashes import SHA1, SHA512
from .util import make_utf8


def pbkdf2_sha1(password, salt, length, iterations):
    password, salt = make_utf8(password, salt)
    prf = lambda p, s: Crypto.Hash.HMAC.new(p, s, digestmod=SHA1).digest()
    return Crypto.Protocol.KDF.PBKDF2(password=password, salt=salt, dkLen=length, count=iterations, prf=prf)


def pbkdf2_sha512(password, salt, length, iterations):
    password, salt = make_utf8(password, salt)
    prf = lambda p, s: Crypto.Hash.HMAC.new(p, s, digestmod=SHA512).digest()
    return Crypto.Protocol.KDF.PBKDF2(password=password, salt=salt, dkLen=length, count=iterations, prf=prf)

########NEW FILE########
__FILENAME__ = helpers
from contextlib import contextmanager


@contextmanager
def assert_raises(exc_klass):
    excepted = None
    try:
        yield
    except Exception as exc:
        excepted = exc
    assert type(excepted) == exc_klass

########NEW FILE########
__FILENAME__ = agilekeychain_tests
import os.path

from unittest2 import TestCase

import onepassword.keychain


class AgileKeychainIntegrationTestCase(TestCase):
    test_file_root = os.path.realpath(os.path.join(__file__, '..', '..', '..', 'data', 'sample.agilekeychain'))

    def test_open(self):
        c = onepassword.keychain.AKeychain(self.test_file_root)
        c.unlock("george")
        self.assertEqual(len(c.items), 2)

    def test_item_parsing(self):
        c = onepassword.keychain.AKeychain(self.test_file_root)
        c.unlock("george")
        google = c.get_by_uuid('00925AACC28B482ABFE650FCD42F82CD')
        self.assertEqual(google.title, 'Google')
        self.assertEqual(google.decrypt()['fields'][1]['value'], 'test_password')

########NEW FILE########
__FILENAME__ = cloudkeychain_tests
import os.path

from unittest2 import TestCase

import onepassword.keychain


class CloudKeychainIntegrationTestCase(TestCase):
    test_file_root = os.path.realpath(os.path.join(__file__, '..', '..', '..', 'data', 'sample.cloudkeychain'))

    def test_open(self):
        c = onepassword.keychain.CKeychain(self.test_file_root)
        c.unlock("fred")

    def test_item_parsing(self):
        c = onepassword.keychain.CKeychain(self.test_file_root)
        c.unlock("fred")
        skype_item = c.get_by_uuid('2A632FDD32F5445E91EB5636C7580447')
        self.assertEqual(skype_item.title, 'Skype')
        self.assertEqual(skype_item.decrypt()['fields'][1]['value'], 'dej3ur9unsh5ian1and5')

########NEW FILE########
__FILENAME__ = crypt_util_tests
import base64
import hashlib
import hmac
import struct
from unittest2 import TestCase

import simplejson

from onepassword import crypt_util
from ..helpers import assert_raises


class HexizeTestCase(TestCase):
    VECTORS = (
        (b'', b''),
        (b'\x00', b'00'),
        (b'abcd', b'61626364'),
        (b'\x00,123', b'002C313233'),
    )

    def test_hexize_simple(self):
        for unhexed, hexed in self.VECTORS:
            self.assertEqual(crypt_util.hexize(unhexed), hexed)

    def test_unhexize_simple(self):
        for unhexed, hexed in self.VECTORS:
            self.assertEqual(crypt_util.unhexize(hexed), unhexed)


class OPData1KeyDerivationTestCase(TestCase):
    VECTORS = (
        (('', b''), (b'\xcb\x93\tl:\x02\xbe\xeb\x1c_\xac6v\\\x90\x11\xfe\x99\xf8\xd8\xeab6`H\xfc\x98\xcb\x98\xdf\xea\x8f', b'O\x8d0U\xa5\xef\x9bz\xf2\x97s\xad\x82R\x95Ti9\x9d%\xd3\nS1(\x89(X\x1f\xb8n\xcb')),
        (('', b'', 10000), (b'I\xb4\xa7!=\xfc\xeeN\xad\xde\xc1\xe2\x1e\xa6\xfc\x8b\x9a,FZ\xe7\xcdPOA\x1e\xeek!\xd2\xe5\xef', b'v4\x8a\xe1\xa9\xea\xa8\x1bUUm\x13\xa2CM\t\x02,\xc4\x07\xd9\x13bF\xef5(\x05\xf4\xb4\xab\xb5')),
        # with iterations=1, is just hmac-sha512 of (key, salt + "\x00\x00\x00\x01)
        (('fred', b'', 1), (b'v\x08\xb1\xd6\x9a\x16\xbe\x11\x8b\x7fa\x86\x99\xdc\xc9\xbd\xb2\xe5a\xf2wld,\xfa\xd6V\x16\x8bV\x88`', b'\xad\x96\xd3\xe7S\x10\xa8L!\xf3\xa7\xb9w\xf0%2\x91\x94\xbb\xf0f\x00\x11\xcb\xa4\xaa\xf2\x8d\x81\x0fb\xa9')),
        (('fred', b''), (b'P\x9b\xe2\xb9\xc0C"\xaf\xf2>\xc0zF\xe8\xff\x06j\x88\x91\xe3\t\x82\x96VZ0\x8e\xd6\x11\xcc\xa7\xd4', b'b$\x81(\xd4\xf4\x0e8M\xf0\x0c\x18)!r\xcf\x02>\xf3hK_\x95\xa4\x8c\xa0\x91\x9c\xf97 W')),
    )

    def test_vectors(self):
        for args, expected in self.VECTORS:
            self.assertEqual(crypt_util.opdata1_derive_keys(*args), expected)


class OPData1UnpackTestCase(TestCase):
    def build_opdata1(self):
        header = b"opdata01"
        plaintext = b""
        plaintext_len = struct.pack(b"<Q", len(plaintext))
        iv = b"".join(chr(x).encode('utf-8') for x in range(16))
        cryptext = plaintext
        msg = plaintext_len + iv + cryptext
        hmac_val = hmac.new(digestmod=hashlib.sha256, key=b"", msg=msg).digest()
        msg += hmac_val
        return header + msg

    def test_bad_header_fails(self):
        with assert_raises(TypeError):
            crypt_util.opdata1_unpack(b"")
        with assert_raises(TypeError):
            crypt_util.opdata1_unpack(b"opdata02abcdef")

    def test_basic(self):
        packed = self.build_opdata1()
        plaintext_length, iv, cryptext, expected_hmac, _ = crypt_util.opdata1_unpack(packed)
        self.assertEqual(plaintext_length, 0)
        self.assertEqual(cryptext, b"")

    def test_basic_auto_b64decode(self):
        packed = self.build_opdata1()
        packed = base64.b64encode(packed)
        plaintext_length, iv, cryptext, expected_hmac, _ = crypt_util.opdata1_unpack(packed)
        self.assertEqual(plaintext_length, 0)
        self.assertEqual(cryptext, b"")


class OPdata1DecryptTestCase(TestCase):
    """test specific data from the example keychain provided by AgileBits"""

    DERIVED_KEY = b'`\x8c\x9f\x19<p\xd5U\xec!Sx\xd6\xe8\x9b\xaf\xbc&:\x8f\x82T\xff\xfbZ\xae{LAf\xaaI'
    DERIVED_HMAC = b'\xb9\xeaO\xdc\xeb\x8e<\xee68\xa8\xc0\x9b\xe1\xbdV\xf94\xf5g\x165\xca\x1a\n\x98Hl\x8bT2"'
    OVERVIEW_KEY = b'\x12*D\x01\xaeL\x16\x80\x91(\xbd\xc5$\xbc\x04\xc6\xd6\xd2\xccrx\x84\xdb\x83`+\xb6\xcc\xbb=\xb9 '
    OVERVIEW_HMAC = b'\xee\xa8[K\xfe9\x1c`\xc4\x1e}\xb2\xd7\xd7\xa8\x91|\x9d\xdf~\x14c\tJC]h\xd5\x1a\xa3\xcf\x0b'
    MASTER_KEY = b'\x8c\r\x8d\xb6p\xb0\xb7\xd5l\xb1\x1aF5w\xe1A\x03W4@\x80\xb9\xae\xec!Q\x19\x1c\xf3\xde\xc5\x9d'
    MASTER_HMAC = b'\xc9S\x10w\xbf|g\xb3\x1aI\xa7\x13\x93\xcf\xd6v_,\x9a\xd8"\xc9\xa8\x8ctX\x1d>k\xe8\xf6V'

    def test_master_key_decryption(self):
        data = "b3BkYXRhMDEAAQAAAAAAAIgdZa9rhj9meNSE/1UbyEOpX68om5FOVwoZkzU3ibZqnGvUC0LFiJI+iGmGIznQbvPVwJHAupl6cEYZs//BIbSxJgcengoIEvci+Vote4DCK8kfwjfLPfq6G+4cnTy0yUMyM1qyA7sPB8p3TBlynOgYL5HNIorhj7grF1NeyuAS8UkEpqzpDZurHZNOuVfqmKaLSy2zyOAtJ/ev+SA829kcK3xqqm+cLKPB1fl2/J7Ya4AIKuPjnC8wo10mwsFNvWQ4a+m1rkCFGCTcWWO1RwO6F9ILQk3qqkUnk6HvhBjbLdpmmwZAdeRQQEpGQz9lM9/goTs0+h9VI4/+pQYqTyLoIbnpljnJ0OziffZcrwqqrXIAsBh+ezE0EH44WC73O2/eEARBA5JNgnW/m/rcmFQK5hxeWb4GxbypgUYDRb0p"
        master_key, master_hmac = crypt_util.opdata1_decrypt_master_key(data, self.DERIVED_KEY, self.DERIVED_HMAC)
        self.assertEqual(master_key, self.MASTER_KEY)
        self.assertEqual(master_hmac, self.MASTER_HMAC)

    def test_overview_key_decryption(self):
        data = "b3BkYXRhMDFAAAAAAAAAAMggp7KPfHsgxuBvQ1mn3YPVxJ7Sc+gvnTCZXQMop2osF7qQUohQHXRTftuCriAAUYgmK6bytJVdIz5JIXCUZEq6xWFekj5L3Br6MO55+bPz1qei50DwFs27eh0+tjpSGm3dMcCqhMAqMmqkENbur0f5t73xlvAEkPwpZzWcrPKe"
        key, hmac = crypt_util.opdata1_decrypt_master_key(data, self.DERIVED_KEY, self.DERIVED_HMAC)
        self.assertEqual(key, self.OVERVIEW_KEY)
        self.assertEqual(hmac, self.OVERVIEW_HMAC)

    def test_item_decryption(self):
        source_data = base64.b64decode("R+JJyjeDfDC49x0XwaW5eJkJhG9COpfzFPSo8P2ZDa6ZYeLRzyjeukgdtDj5Yg7F0l2fMCbHKmOtQUXRQxCfsaCcsTeDR10WGMlzQtJoygmdMreG9joX18JPFWtDo/P94sbn8Wd0Q+Sx18Whdo0lRA==")
        item_data = "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"
        item_key, item_hmac = crypt_util.opdata1_decrypt_key(source_data, self.MASTER_KEY, self.MASTER_HMAC)
        plaintext_item = crypt_util.opdata1_decrypt_item(item_data, item_key, item_hmac)
        item_dict = simplejson.loads(plaintext_item)
        self.assertIn('sections', item_dict)
        self.assertEqual(item_dict['sections'][0]['title'], 'set.name')

    def test_item_overview_decryption(self):
        source_data = "b3BkYXRhMDEuAAAAAAAAACCvfWbzwBJIcF501hFPJGgqwKPA+y333FXC2LG9W+M9GGIyd9wBW6DToRRV5964EkpEs4zlwz5FHNt25FfGuC2TPYnVl+zKLH0GFPXVvFYz3XP5COQ3fHhX2SmeHHsviw=="
        expected_data = {"title":"Personal","ainfo":"Wendy Appleseed"}
        data = simplejson.loads(crypt_util.opdata1_decrypt_item(source_data, self.OVERVIEW_KEY, self.OVERVIEW_HMAC))
        self.assertEqual(data, expected_data)

    def test_ignore_hmac(self):
        expected_data = {"title":"Personal","ainfo":"Wendy Appleseed"}
        source_data = base64.b64decode("b3BkYXRhMDEuAAAAAAAAACCvfWbzwBJIcF501hFPJGgqwKPA+y333FXC2LG9W+M9GGIyd9wBW6DToRRV5964EkpEs4zlwz5FHNt25FfGuC2TPYnVl+zKLH0GFPXVvFYz3XP5COQ3fHhX2SmeHHsviw==")
        source_data = source_data[:-2] + b".."
        with assert_raises(ValueError):
            decrypted = crypt_util.opdata1_decrypt_item(source_data, self.OVERVIEW_KEY, self.OVERVIEW_HMAC)
        decrypted = crypt_util.opdata1_decrypt_item(source_data, self.OVERVIEW_KEY, self.OVERVIEW_HMAC, ignore_hmac=True)
        data = simplejson.loads(decrypted)
        self.assertEqual(data, expected_data)

########NEW FILE########
__FILENAME__ = padding_tests
from unittest2 import TestCase

from onepassword import padding
import six


class PKCS5PaddingTestCase(TestCase):
    """Test our PKCS#5 padding"""
    VECTORS = (
        (b"", 1, b"\x01"),
        (b"abcd", 8, b"abcd\x04\x04\x04\x04"),
        (b"abcdefg\x00", 16, b"abcdefg\x00\x08\x08\x08\x08\x08\x08\x08\x08"),
    )

    def test_pad(self):
        for unpadded, bs, padded in self.VECTORS:
            self.assertEqual(padding.pkcs5_pad(unpadded, bs), padded)

    def test_unpad(self):
        for unpadded, _, padded in self.VECTORS:
            self.assertEqual(padding.pkcs5_unpad(padded), unpadded)
        self.assertEqual(padding.pkcs5_unpad(""), "")


class ABPaddingTestCase(TestCase):
    """Test the custom AgileBits padding"""
    VECTORS = (
        (b"", 4, b"\x00\x00\x00\x00"),
        (b"ab", 4, b"\x00\x00ab"),
        (b"abcd", 4, b"\x00\x00\x00\x00abcd"),
        (b"\x01\x02", 10, b"\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02"),
    )

    def zeros(self, count):
        return b''.join([six.int2byte(0) for x in range(count)])

    def test_pad(self):
        for unpadded, bs, padded in self.VECTORS:
            self.assertEqual(padding.ab_pad(unpadded, bs, random_generator=self.zeros), padded)

    def test_unpad(self):
        for unpadded, _, padded in self.VECTORS:
            size = len(unpadded)
            self.assertEqual(padding.ab_unpad(padded, size), unpadded)

########NEW FILE########
__FILENAME__ = pbkdf1_tests
import mock
from unittest2 import TestCase

from onepassword import pbkdf1
from onepassword import crypt_util

class PBKDF1TestCase(TestCase):
    # test vectors generated with
    # openssl enc -aes-128-cbc -p -k <PASSWORD> -a -nosalt -p < /dev/null
    VECTORS = (
        (b'password', b'', b'5F4DCC3B5AA765D61D8327DEB882CF99', b'2B95990A9151374ABD8FF8C5A7A0FE08'),
        (b'', b'', b'D41D8CD98F00B204E9800998ECF8427E', b'59ADB24EF3CDBE0297F05B395827453F'),
        (b'', b'E3936A9A8ACFE9BE', b'E9FAB75961E5DE62D6982C3F569114A5', b'652D875150F652F75154666E1FD0E8AC'),
        (b'012345678910111231415161717', b'F7560045C70A96DB', b'2E14B2EC7E2F8CDC18F15BB773CCD6F2', b'5C8AADA268F9B86F960DF0464AE5E981'),
    )

    def test_vectors(self):
        for password, hex_salt, expected_key, expected_iv in self.VECTORS:
            salt = crypt_util.unhexize(hex_salt)
            pb_gen = pbkdf1.PBKDF1(password, salt)
            derived_key = pb_gen.read(16)
            derived_iv = pb_gen.read(16)
            hex_derived_key = crypt_util.hexize(derived_key)
            hex_derived_iv = crypt_util.hexize(derived_iv)
            self.assertEqual(hex_derived_key, expected_key)
            self.assertEqual(hex_derived_iv, expected_iv)

    def test_count(self):
        # can't use vectors as easily here because openssl never passes
        # count != 1
        sigil = b"SENTINTEL VALUE THAT IS A STRING"
        mock_hash = mock.Mock()
        mock_hash.digest = mock.Mock(return_value=sigil)
        mock_md5 = mock.Mock(return_value=mock_hash)
        # choose parameters so that key + salt is already desired length
        key = b'aaaaaaaa'
        salt = b'bbbbbbbb'
        pb_gen = pbkdf1.PBKDF1(key, salt, iterations=4, hash_algo=mock_md5)
        keyish = pb_gen.read(16)
        ivish = pb_gen.read(16)
        self.assertEqual((keyish, ivish), (sigil[:-16], sigil[-16:]))
        self.assertEqual(mock_md5.mock_calls, [
            mock.call(key+salt),
            mock.call(sigil),
            mock.call(sigil),
            mock.call(sigil),
        ])

########NEW FILE########
__FILENAME__ = pbkdf2_tests
from __future__ import print_function

from functools import wraps
from unittest2 import TestCase


def ignore_import_error(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except ImportError as ex:
            print('ignoring ImportError: {0}'.format(ex))
    return wrapper


class PBKDF2SHA1TestCase(TestCase):
    VECTORS = (
        (b'password', b'', 1, b'\x87T\xc3,d\xb0\xf5$\xfcP\xc0\x0fx\x815\xde'),
        (b'password', b'', 16, b'\x0bP|}r\x13\xe9\x9e\x0f\x0cj\xd0\xbdH\xa7\xc9'),
        (b'password', b'salt', 1, b'\x0c`\xc8\x0f\x96\x1f\x0eq\xf3\xa9\xb5$\xaf`\x12\x06'),
        (b'password', b'salt', 16, b'\x1e\x84Lf\xb5|\x0e\xed\xf6\xfdx\x1b\xca\xfc\xe8"'),
        (b'password', b'salt', 163840, b'\xc2\x03/\xb4\xfe\xf4\xa8n\x15\\\x1a\x93kY\xa9\xda'),
    )

    def test_vectors_pycrypto(self):
        from onepassword import _pbkdf2_pycrypto
        for password, salt, iterations, expected_key in self.VECTORS:
            generated = _pbkdf2_pycrypto.pbkdf2_sha1(password, salt, length=16, iterations=iterations)
            self.assertEqual(generated, expected_key)

    @ignore_import_error
    def test_vectors_m2crypto(self):
        from onepassword import _pbkdf2_m2crypto
        for password, salt, iterations, expected_key in self.VECTORS:
            generated = _pbkdf2_m2crypto.pbkdf2_sha1(password, salt, length=16, iterations=iterations)
            self.assertEqual(generated, expected_key)

    @ignore_import_error
    def test_vectors_nettle(self):
        from onepassword import _pbkdf2_nettle
        for password, salt, iterations, expected_key in self.VECTORS:
            generated = _pbkdf2_nettle.pbkdf2_sha1(password, salt, length=16, iterations=iterations)
            self.assertEqual(generated, expected_key)


class PBKDF2SHA512TestCase(TestCase):
    VECTORS = (
        (b'password', b'', 1, b'\xae\x16\xcem\xfdJj\x0c B\x1f\xf8\x0e\xb3\xbaJ'),
        (b'password', b'', 16, b'T\xe1\xd5T\xa6{\x15\x1d\x19;\x82\nbXbI'),
        (b'password', b'salt', 1, b'\x86\x7fp\xcf\x1a\xde\x02\xcf\xf3u%\x99\xa3\xa5=\xc4'),
        (b'password', b'salt', 16, b'\x884\xdc\xaf\xec\xf51&\xcc\xfeMF\xc6v\x16M'),
        (b'password', b'salt', 163840, b'|\xc2\xa2i\xe7\xa2j\x9e\x8f\xfb\x93\xd7\xb7f\x88\x05'),
    )

    def test_vectors_pycrypto(self):
        from onepassword import _pbkdf2_pycrypto
        for password, salt, iterations, expected_key in self.VECTORS:
            generated = _pbkdf2_pycrypto.pbkdf2_sha512(password, salt, length=16, iterations=iterations)
            self.assertEqual(generated, expected_key)

    @ignore_import_error
    def test_vectors_m2crypto(self):
        from onepassword import _pbkdf2_m2crypto
        for password, salt, iterations, expected_key in self.VECTORS:
            generated = _pbkdf2_m2crypto.pbkdf2_sha512(password, salt, length=16, iterations=iterations)
            self.assertEqual(generated, expected_key)

    @ignore_import_error
    def test_vectors_nettle(self):
        from onepassword import _pbkdf2_nettle
        for password, salt, iterations, expected_key in self.VECTORS:
            generated = _pbkdf2_nettle.pbkdf2_sha512(password, salt, length=16, iterations=iterations)
            self.assertEqual(generated, expected_key)


########NEW FILE########
__FILENAME__ = random_tests
from unittest2 import TestCase
from onepassword import random_util


class RandomTestCase(TestCase):
    # just make sure that all of the functions return the right number
    # of bytes for now
    BYTES = 512

    def test_not_random(self):
        bytez = random_util.not_random_bytes(self.BYTES)
        self.assertEqual(len(bytez), self.BYTES)

    def test_barely_random(self):
        bytez = random_util.barely_random_bytes(self.BYTES)
        self.assertEqual(len(bytez), self.BYTES)

    def test_sort_of_random(self):
        bytez = random_util.sort_of_random_bytes(self.BYTES)
        self.assertEqual(len(bytez), self.BYTES)

    def test_really_random(self):
        bytez = random_util.really_random_bytes(self.BYTES)
        self.assertEqual(len(bytez), self.BYTES)

########NEW FILE########
