__FILENAME__ = exceptions
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function


class _Reasons(object):
    BACKEND_MISSING_INTERFACE = object()
    UNSUPPORTED_HASH = object()
    UNSUPPORTED_CIPHER = object()
    UNSUPPORTED_PADDING = object()
    UNSUPPORTED_MGF = object()
    UNSUPPORTED_PUBLIC_KEY_ALGORITHM = object()


class UnsupportedAlgorithm(Exception):
    def __init__(self, message, reason=None):
        super(UnsupportedAlgorithm, self).__init__(message)
        self._reason = reason


class AlreadyFinalized(Exception):
    pass


class AlreadyUpdated(Exception):
    pass


class NotYetFinalized(Exception):
    pass


class InvalidTag(Exception):
    pass


class InvalidSignature(Exception):
    pass


class InternalError(Exception):
    pass


class InvalidKey(Exception):
    pass


class InvalidToken(Exception):
    pass

########NEW FILE########
__FILENAME__ = fernet
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import base64
import binascii
import os
import struct
import time

import six

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.hmac import HMAC


class InvalidToken(Exception):
    pass


_MAX_CLOCK_SKEW = 60


class Fernet(object):
    def __init__(self, key, backend=None):
        if backend is None:
            backend = default_backend()

        key = base64.urlsafe_b64decode(key)
        if len(key) != 32:
            raise ValueError(
                "Fernet key must be 32 url-safe base64-encoded bytes."
            )

        self._signing_key = key[:16]
        self._encryption_key = key[16:]
        self._backend = backend

    @classmethod
    def generate_key(cls):
        return base64.urlsafe_b64encode(os.urandom(32))

    def encrypt(self, data):
        current_time = int(time.time())
        iv = os.urandom(16)
        return self._encrypt_from_parts(data, current_time, iv)

    def _encrypt_from_parts(self, data, current_time, iv):
        if not isinstance(data, bytes):
            raise TypeError("data must be bytes.")

        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(data) + padder.finalize()
        encryptor = Cipher(
            algorithms.AES(self._encryption_key), modes.CBC(iv), self._backend
        ).encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        basic_parts = (
            b"\x80" + struct.pack(">Q", current_time) + iv + ciphertext
        )

        h = HMAC(self._signing_key, hashes.SHA256(), backend=self._backend)
        h.update(basic_parts)
        hmac = h.finalize()
        return base64.urlsafe_b64encode(basic_parts + hmac)

    def decrypt(self, token, ttl=None):
        if not isinstance(token, bytes):
            raise TypeError("token must be bytes.")

        current_time = int(time.time())

        try:
            data = base64.urlsafe_b64decode(token)
        except (TypeError, binascii.Error):
            raise InvalidToken

        if six.indexbytes(data, 0) != 0x80:
            raise InvalidToken

        try:
            timestamp, = struct.unpack(">Q", data[1:9])
        except struct.error:
            raise InvalidToken
        if ttl is not None:
            if timestamp + ttl < current_time:
                raise InvalidToken
        if current_time + _MAX_CLOCK_SKEW < timestamp:
            raise InvalidToken
        h = HMAC(self._signing_key, hashes.SHA256(), backend=self._backend)
        h.update(data[:-32])
        try:
            h.verify(data[-32:])
        except InvalidSignature:
            raise InvalidToken

        iv = data[9:25]
        ciphertext = data[25:-32]
        decryptor = Cipher(
            algorithms.AES(self._encryption_key), modes.CBC(iv), self._backend
        ).decryptor()
        plaintext_padded = decryptor.update(ciphertext)
        try:
            plaintext_padded += decryptor.finalize()
        except ValueError:
            raise InvalidToken
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()

        unpadded = unpadder.update(plaintext_padded)
        try:
            unpadded += unpadder.finalize()
        except ValueError:
            raise InvalidToken
        return unpadded

########NEW FILE########
__FILENAME__ = backend
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

from collections import namedtuple

from cryptography import utils
from cryptography.exceptions import (
    InternalError, InvalidTag, UnsupportedAlgorithm, _Reasons
)
from cryptography.hazmat.backends.interfaces import (
    CipherBackend, HMACBackend, HashBackend, PBKDF2HMACBackend
)
from cryptography.hazmat.bindings.commoncrypto.binding import Binding
from cryptography.hazmat.primitives import constant_time, interfaces
from cryptography.hazmat.primitives.ciphers.algorithms import (
    AES, ARC4, Blowfish, CAST5, TripleDES
)
from cryptography.hazmat.primitives.ciphers.modes import (
    CBC, CFB, CFB8, CTR, ECB, GCM, OFB
)


HashMethods = namedtuple(
    "HashMethods", ["ctx", "hash_init", "hash_update", "hash_final"]
)


@utils.register_interface(CipherBackend)
@utils.register_interface(HashBackend)
@utils.register_interface(HMACBackend)
@utils.register_interface(PBKDF2HMACBackend)
class Backend(object):
    """
    CommonCrypto API wrapper.
    """
    name = "commoncrypto"

    def __init__(self):
        self._binding = Binding()
        self._ffi = self._binding.ffi
        self._lib = self._binding.lib

        self._cipher_registry = {}
        self._register_default_ciphers()
        self._hash_mapping = {
            "md5": HashMethods(
                "CC_MD5_CTX *", self._lib.CC_MD5_Init,
                self._lib.CC_MD5_Update, self._lib.CC_MD5_Final
            ),
            "sha1": HashMethods(
                "CC_SHA1_CTX *", self._lib.CC_SHA1_Init,
                self._lib.CC_SHA1_Update, self._lib.CC_SHA1_Final
            ),
            "sha224": HashMethods(
                "CC_SHA256_CTX *", self._lib.CC_SHA224_Init,
                self._lib.CC_SHA224_Update, self._lib.CC_SHA224_Final
            ),
            "sha256": HashMethods(
                "CC_SHA256_CTX *", self._lib.CC_SHA256_Init,
                self._lib.CC_SHA256_Update, self._lib.CC_SHA256_Final
            ),
            "sha384": HashMethods(
                "CC_SHA512_CTX *", self._lib.CC_SHA384_Init,
                self._lib.CC_SHA384_Update, self._lib.CC_SHA384_Final
            ),
            "sha512": HashMethods(
                "CC_SHA512_CTX *", self._lib.CC_SHA512_Init,
                self._lib.CC_SHA512_Update, self._lib.CC_SHA512_Final
            ),
        }

        self._supported_hmac_algorithms = {
            "md5": self._lib.kCCHmacAlgMD5,
            "sha1": self._lib.kCCHmacAlgSHA1,
            "sha224": self._lib.kCCHmacAlgSHA224,
            "sha256": self._lib.kCCHmacAlgSHA256,
            "sha384": self._lib.kCCHmacAlgSHA384,
            "sha512": self._lib.kCCHmacAlgSHA512,
        }

        self._supported_pbkdf2_hmac_algorithms = {
            "sha1": self._lib.kCCPRFHmacAlgSHA1,
            "sha224": self._lib.kCCPRFHmacAlgSHA224,
            "sha256": self._lib.kCCPRFHmacAlgSHA256,
            "sha384": self._lib.kCCPRFHmacAlgSHA384,
            "sha512": self._lib.kCCPRFHmacAlgSHA512,
        }

    def hash_supported(self, algorithm):
        return algorithm.name in self._hash_mapping

    def hmac_supported(self, algorithm):
        return algorithm.name in self._supported_hmac_algorithms

    def create_hash_ctx(self, algorithm):
        return _HashContext(self, algorithm)

    def create_hmac_ctx(self, key, algorithm):
        return _HMACContext(self, key, algorithm)

    def cipher_supported(self, cipher, mode):
        return (type(cipher), type(mode)) in self._cipher_registry

    def create_symmetric_encryption_ctx(self, cipher, mode):
        if isinstance(mode, GCM):
            return _GCMCipherContext(
                self, cipher, mode, self._lib.kCCEncrypt
            )
        else:
            return _CipherContext(self, cipher, mode, self._lib.kCCEncrypt)

    def create_symmetric_decryption_ctx(self, cipher, mode):
        if isinstance(mode, GCM):
            return _GCMCipherContext(
                self, cipher, mode, self._lib.kCCDecrypt
            )
        else:
            return _CipherContext(self, cipher, mode, self._lib.kCCDecrypt)

    def pbkdf2_hmac_supported(self, algorithm):
        return algorithm.name in self._supported_pbkdf2_hmac_algorithms

    def derive_pbkdf2_hmac(self, algorithm, length, salt, iterations,
                           key_material):
        alg_enum = self._supported_pbkdf2_hmac_algorithms[algorithm.name]
        buf = self._ffi.new("char[]", length)
        res = self._lib.CCKeyDerivationPBKDF(
            self._lib.kCCPBKDF2,
            key_material,
            len(key_material),
            salt,
            len(salt),
            alg_enum,
            iterations,
            buf,
            length
        )
        self._check_response(res)

        return self._ffi.buffer(buf)[:]

    def _register_cipher_adapter(self, cipher_cls, cipher_const, mode_cls,
                                 mode_const):
        if (cipher_cls, mode_cls) in self._cipher_registry:
            raise ValueError("Duplicate registration for: {0} {1}.".format(
                cipher_cls, mode_cls)
            )
        self._cipher_registry[cipher_cls, mode_cls] = (cipher_const,
                                                       mode_const)

    def _register_default_ciphers(self):
        for mode_cls, mode_const in [
            (CBC, self._lib.kCCModeCBC),
            (ECB, self._lib.kCCModeECB),
            (CFB, self._lib.kCCModeCFB),
            (CFB8, self._lib.kCCModeCFB8),
            (OFB, self._lib.kCCModeOFB),
            (CTR, self._lib.kCCModeCTR),
            (GCM, self._lib.kCCModeGCM),
        ]:
            self._register_cipher_adapter(
                AES,
                self._lib.kCCAlgorithmAES128,
                mode_cls,
                mode_const
            )
        for mode_cls, mode_const in [
            (CBC, self._lib.kCCModeCBC),
            (CFB, self._lib.kCCModeCFB),
            (CFB8, self._lib.kCCModeCFB8),
            (OFB, self._lib.kCCModeOFB),
        ]:
            self._register_cipher_adapter(
                TripleDES,
                self._lib.kCCAlgorithm3DES,
                mode_cls,
                mode_const
            )
        for mode_cls, mode_const in [
            (CBC, self._lib.kCCModeCBC),
            (ECB, self._lib.kCCModeECB),
            (CFB, self._lib.kCCModeCFB),
            (OFB, self._lib.kCCModeOFB)
        ]:
            self._register_cipher_adapter(
                Blowfish,
                self._lib.kCCAlgorithmBlowfish,
                mode_cls,
                mode_const
            )
        for mode_cls, mode_const in [
            (CBC, self._lib.kCCModeCBC),
            (ECB, self._lib.kCCModeECB),
            (CFB, self._lib.kCCModeCFB),
            (OFB, self._lib.kCCModeOFB),
            (CTR, self._lib.kCCModeCTR)
        ]:
            self._register_cipher_adapter(
                CAST5,
                self._lib.kCCAlgorithmCAST,
                mode_cls,
                mode_const
            )
        self._register_cipher_adapter(
            ARC4,
            self._lib.kCCAlgorithmRC4,
            type(None),
            self._lib.kCCModeRC4
        )

    def _check_response(self, response):
        if response == self._lib.kCCSuccess:
            return
        elif response == self._lib.kCCAlignmentError:
            # This error is not currently triggered due to a bug filed as
            # rdar://15589470
            raise ValueError(
                "The length of the provided data is not a multiple of "
                "the block length."
            )
        else:
            raise InternalError(
                "The backend returned an unknown error, consider filing a bug."
                " Code: {0}.".format(response)
            )


def _release_cipher_ctx(ctx):
    """
    Called by the garbage collector and used to safely dereference and
    release the context.
    """
    if ctx[0] != backend._ffi.NULL:
        res = backend._lib.CCCryptorRelease(ctx[0])
        backend._check_response(res)
        ctx[0] = backend._ffi.NULL


@utils.register_interface(interfaces.CipherContext)
class _CipherContext(object):
    def __init__(self, backend, cipher, mode, operation):
        self._backend = backend
        self._cipher = cipher
        self._mode = mode
        self._operation = operation
        # There is a bug in CommonCrypto where block ciphers do not raise
        # kCCAlignmentError when finalizing if you supply non-block aligned
        # data. To work around this we need to keep track of the block
        # alignment ourselves, but only for alg+mode combos that require
        # block alignment. OFB, CFB, and CTR make a block cipher algorithm
        # into a stream cipher so we don't need to track them (and thus their
        # block size is effectively 1 byte just like OpenSSL/CommonCrypto
        # treat RC4 and other stream cipher block sizes).
        # This bug has been filed as rdar://15589470
        self._bytes_processed = 0
        if (isinstance(cipher, interfaces.BlockCipherAlgorithm) and not
                isinstance(mode, (OFB, CFB, CFB8, CTR))):
            self._byte_block_size = cipher.block_size // 8
        else:
            self._byte_block_size = 1

        registry = self._backend._cipher_registry
        try:
            cipher_enum, mode_enum = registry[type(cipher), type(mode)]
        except KeyError:
            raise UnsupportedAlgorithm(
                "cipher {0} in {1} mode is not supported "
                "by this backend.".format(
                    cipher.name, mode.name if mode else mode),
                _Reasons.UNSUPPORTED_CIPHER
            )

        ctx = self._backend._ffi.new("CCCryptorRef *")
        ctx = self._backend._ffi.gc(ctx, _release_cipher_ctx)

        if isinstance(mode, interfaces.ModeWithInitializationVector):
            iv_nonce = mode.initialization_vector
        elif isinstance(mode, interfaces.ModeWithNonce):
            iv_nonce = mode.nonce
        else:
            iv_nonce = self._backend._ffi.NULL

        if isinstance(mode, CTR):
            mode_option = self._backend._lib.kCCModeOptionCTR_BE
        else:
            mode_option = 0

        res = self._backend._lib.CCCryptorCreateWithMode(
            operation,
            mode_enum, cipher_enum,
            self._backend._lib.ccNoPadding, iv_nonce,
            cipher.key, len(cipher.key),
            self._backend._ffi.NULL, 0, 0, mode_option, ctx)
        self._backend._check_response(res)

        self._ctx = ctx

    def update(self, data):
        # Count bytes processed to handle block alignment.
        self._bytes_processed += len(data)
        buf = self._backend._ffi.new(
            "unsigned char[]", len(data) + self._byte_block_size - 1)
        outlen = self._backend._ffi.new("size_t *")
        res = self._backend._lib.CCCryptorUpdate(
            self._ctx[0], data, len(data), buf,
            len(data) + self._byte_block_size - 1, outlen)
        self._backend._check_response(res)
        return self._backend._ffi.buffer(buf)[:outlen[0]]

    def finalize(self):
        # Raise error if block alignment is wrong.
        if self._bytes_processed % self._byte_block_size:
            raise ValueError(
                "The length of the provided data is not a multiple of "
                "the block length."
            )
        buf = self._backend._ffi.new("unsigned char[]", self._byte_block_size)
        outlen = self._backend._ffi.new("size_t *")
        res = self._backend._lib.CCCryptorFinal(
            self._ctx[0], buf, len(buf), outlen)
        self._backend._check_response(res)
        _release_cipher_ctx(self._ctx)
        return self._backend._ffi.buffer(buf)[:outlen[0]]


@utils.register_interface(interfaces.AEADCipherContext)
@utils.register_interface(interfaces.AEADEncryptionContext)
class _GCMCipherContext(object):
    def __init__(self, backend, cipher, mode, operation):
        self._backend = backend
        self._cipher = cipher
        self._mode = mode
        self._operation = operation
        self._tag = None

        registry = self._backend._cipher_registry
        try:
            cipher_enum, mode_enum = registry[type(cipher), type(mode)]
        except KeyError:
            raise UnsupportedAlgorithm(
                "cipher {0} in {1} mode is not supported "
                "by this backend.".format(
                    cipher.name, mode.name if mode else mode),
                _Reasons.UNSUPPORTED_CIPHER
            )

        ctx = self._backend._ffi.new("CCCryptorRef *")
        ctx = self._backend._ffi.gc(ctx, _release_cipher_ctx)

        self._ctx = ctx

        res = self._backend._lib.CCCryptorCreateWithMode(
            operation,
            mode_enum, cipher_enum,
            self._backend._lib.ccNoPadding,
            self._backend._ffi.NULL,
            cipher.key, len(cipher.key),
            self._backend._ffi.NULL, 0, 0, 0, self._ctx)
        self._backend._check_response(res)

        res = self._backend._lib.CCCryptorGCMAddIV(
            self._ctx[0],
            mode.initialization_vector,
            len(mode.initialization_vector)
        )
        self._backend._check_response(res)

    def update(self, data):
        buf = self._backend._ffi.new("unsigned char[]", len(data))
        args = (self._ctx[0], data, len(data), buf)
        if self._operation == self._backend._lib.kCCEncrypt:
            res = self._backend._lib.CCCryptorGCMEncrypt(*args)
        else:
            res = self._backend._lib.CCCryptorGCMDecrypt(*args)

        self._backend._check_response(res)
        return self._backend._ffi.buffer(buf)[:]

    def finalize(self):
        tag_size = self._cipher.block_size // 8
        tag_buf = self._backend._ffi.new("unsigned char[]", tag_size)
        tag_len = self._backend._ffi.new("size_t *", tag_size)
        res = backend._lib.CCCryptorGCMFinal(self._ctx[0], tag_buf, tag_len)
        self._backend._check_response(res)
        _release_cipher_ctx(self._ctx)
        self._tag = self._backend._ffi.buffer(tag_buf)[:]
        if (self._operation == self._backend._lib.kCCDecrypt and
                not constant_time.bytes_eq(
                    self._tag[:len(self._mode.tag)], self._mode.tag
                )):
            raise InvalidTag
        return b""

    def authenticate_additional_data(self, data):
        res = self._backend._lib.CCCryptorGCMAddAAD(
            self._ctx[0], data, len(data)
        )
        self._backend._check_response(res)

    @property
    def tag(self):
        return self._tag


@utils.register_interface(interfaces.HashContext)
class _HashContext(object):
    def __init__(self, backend, algorithm, ctx=None):
        self.algorithm = algorithm
        self._backend = backend

        if ctx is None:
            try:
                methods = self._backend._hash_mapping[self.algorithm.name]
            except KeyError:
                raise UnsupportedAlgorithm(
                    "{0} is not a supported hash on this backend.".format(
                        algorithm.name),
                    _Reasons.UNSUPPORTED_HASH
                )
            ctx = self._backend._ffi.new(methods.ctx)
            res = methods.hash_init(ctx)
            assert res == 1

        self._ctx = ctx

    def copy(self):
        methods = self._backend._hash_mapping[self.algorithm.name]
        new_ctx = self._backend._ffi.new(methods.ctx)
        # CommonCrypto has no APIs for copying hashes, so we have to copy the
        # underlying struct.
        new_ctx[0] = self._ctx[0]

        return _HashContext(self._backend, self.algorithm, ctx=new_ctx)

    def update(self, data):
        methods = self._backend._hash_mapping[self.algorithm.name]
        res = methods.hash_update(self._ctx, data, len(data))
        assert res == 1

    def finalize(self):
        methods = self._backend._hash_mapping[self.algorithm.name]
        buf = self._backend._ffi.new("unsigned char[]",
                                     self.algorithm.digest_size)
        res = methods.hash_final(buf, self._ctx)
        assert res == 1
        return self._backend._ffi.buffer(buf)[:]


@utils.register_interface(interfaces.HashContext)
class _HMACContext(object):
    def __init__(self, backend, key, algorithm, ctx=None):
        self.algorithm = algorithm
        self._backend = backend
        if ctx is None:
            ctx = self._backend._ffi.new("CCHmacContext *")
            try:
                alg = self._backend._supported_hmac_algorithms[algorithm.name]
            except KeyError:
                raise UnsupportedAlgorithm(
                    "{0} is not a supported HMAC hash on this backend.".format(
                        algorithm.name),
                    _Reasons.UNSUPPORTED_HASH
                )

            self._backend._lib.CCHmacInit(ctx, alg, key, len(key))

        self._ctx = ctx
        self._key = key

    def copy(self):
        copied_ctx = self._backend._ffi.new("CCHmacContext *")
        # CommonCrypto has no APIs for copying HMACs, so we have to copy the
        # underlying struct.
        copied_ctx[0] = self._ctx[0]
        return _HMACContext(
            self._backend, self._key, self.algorithm, ctx=copied_ctx
        )

    def update(self, data):
        self._backend._lib.CCHmacUpdate(self._ctx, data, len(data))

    def finalize(self):
        buf = self._backend._ffi.new("unsigned char[]",
                                     self.algorithm.digest_size)
        self._backend._lib.CCHmacFinal(self._ctx, buf)
        return self._backend._ffi.buffer(buf)[:]


backend = Backend()

########NEW FILE########
__FILENAME__ = interfaces
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import abc

import six


@six.add_metaclass(abc.ABCMeta)
class CipherBackend(object):
    @abc.abstractmethod
    def cipher_supported(self, cipher, mode):
        """
        Return True if the given cipher and mode are supported.
        """

    @abc.abstractmethod
    def create_symmetric_encryption_ctx(self, cipher, mode):
        """
        Get a CipherContext that can be used for encryption.
        """

    @abc.abstractmethod
    def create_symmetric_decryption_ctx(self, cipher, mode):
        """
        Get a CipherContext that can be used for decryption.
        """


@six.add_metaclass(abc.ABCMeta)
class HashBackend(object):
    @abc.abstractmethod
    def hash_supported(self, algorithm):
        """
        Return True if the hash algorithm is supported by this backend.
        """

    @abc.abstractmethod
    def create_hash_ctx(self, algorithm):
        """
        Create a HashContext for calculating a message digest.
        """


@six.add_metaclass(abc.ABCMeta)
class HMACBackend(object):
    @abc.abstractmethod
    def hmac_supported(self, algorithm):
        """
        Return True if the hash algorithm is supported for HMAC by this
        backend.
        """

    @abc.abstractmethod
    def create_hmac_ctx(self, key, algorithm):
        """
        Create a HashContext for calculating a message authentication code.
        """


@six.add_metaclass(abc.ABCMeta)
class PBKDF2HMACBackend(object):
    @abc.abstractmethod
    def pbkdf2_hmac_supported(self, algorithm):
        """
        Return True if the hash algorithm is supported for PBKDF2 by this
        backend.
        """

    @abc.abstractmethod
    def derive_pbkdf2_hmac(self, algorithm, length, salt, iterations,
                           key_material):
        """
        Return length bytes derived from provided PBKDF2 parameters.
        """


@six.add_metaclass(abc.ABCMeta)
class RSABackend(object):
    @abc.abstractmethod
    def generate_rsa_private_key(self, public_exponent, key_size):
        """
        Generate an RSAPrivateKey instance with public_exponent and a modulus
        of key_size bits.
        """

    @abc.abstractmethod
    def create_rsa_signature_ctx(self, private_key, padding, algorithm):
        """
        Returns an object conforming to the AsymmetricSignatureContext
        interface.
        """

    @abc.abstractmethod
    def create_rsa_verification_ctx(self, public_key, signature, padding,
                                    algorithm):
        """
        Returns an object conforming to the AsymmetricVerificationContext
        interface.
        """

    @abc.abstractmethod
    def mgf1_hash_supported(self, algorithm):
        """
        Return True if the hash algorithm is supported for MGF1 in PSS.
        """

    @abc.abstractmethod
    def decrypt_rsa(self, private_key, ciphertext, padding):
        """
        Returns decrypted bytes.
        """

    @abc.abstractmethod
    def encrypt_rsa(self, public_key, plaintext, padding):
        """
        Returns encrypted bytes.
        """

    @abc.abstractmethod
    def rsa_padding_supported(self, padding):
        """
        Returns True if the backend supports the given padding options.
        """

    @abc.abstractmethod
    def generate_rsa_parameters_supported(self, public_exponent, key_size):
        """
        Returns True if the backend supports the given parameters for key
        generation.
        """


@six.add_metaclass(abc.ABCMeta)
class DSABackend(object):
    @abc.abstractmethod
    def generate_dsa_parameters(self, key_size):
        """
        Generate a DSAParameters instance with a modulus of key_size bits.
        """

    @abc.abstractmethod
    def generate_dsa_private_key(self, parameters):
        """
        Generate an DSAPrivateKey instance with parameters as
        a DSAParameters object.
        """

    @abc.abstractmethod
    def create_dsa_signature_ctx(self, private_key, algorithm):
        """
        Returns an object conforming to the AsymmetricSignatureContext
        interface.
        """

    @abc.abstractmethod
    def create_dsa_verification_ctx(self, public_key, signature, algorithm):
        """
        Returns an object conforming to the AsymmetricVerificationContext
        interface.
        """

    @abc.abstractmethod
    def dsa_hash_supported(self, algorithm):
        """
        Return True if the hash algorithm is supported by the backend for DSA.
        """

    @abc.abstractmethod
    def dsa_parameters_supported(self, p, q, g):
        """
        Return True if the parameters are supported by the backend for DSA.
        """


@six.add_metaclass(abc.ABCMeta)
class TraditionalOpenSSLSerializationBackend(object):
    @abc.abstractmethod
    def load_traditional_openssl_pem_private_key(self, data, password):
        """
        Load a private key from PEM encoded data, using password if the data
        is encrypted.
        """


@six.add_metaclass(abc.ABCMeta)
class PKCS8SerializationBackend(object):
    @abc.abstractmethod
    def load_pkcs8_pem_private_key(self, data, password):
        """
        Load a private key from PEM encoded data, using password if the data
        is encrypted.
        """


@six.add_metaclass(abc.ABCMeta)
class CMACBackend(object):
    @abc.abstractmethod
    def cmac_algorithm_supported(self, algorithm):
        """
        Returns True if the block cipher is supported for CMAC by this backend
        """

    @abc.abstractmethod
    def create_cmac_ctx(self, algorithm):
        """
        Create a CMACContext for calculating a message authentication code.
        """

########NEW FILE########
__FILENAME__ = multibackend
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

from cryptography import utils
from cryptography.exceptions import UnsupportedAlgorithm, _Reasons
from cryptography.hazmat.backends.interfaces import (
    CMACBackend, CipherBackend, DSABackend, HMACBackend, HashBackend,
    PBKDF2HMACBackend, RSABackend
)


@utils.register_interface(CMACBackend)
@utils.register_interface(CipherBackend)
@utils.register_interface(HashBackend)
@utils.register_interface(HMACBackend)
@utils.register_interface(PBKDF2HMACBackend)
@utils.register_interface(RSABackend)
@utils.register_interface(DSABackend)
class MultiBackend(object):
    name = "multibackend"

    def __init__(self, backends):
        self._backends = backends

    def _filtered_backends(self, interface):
        for b in self._backends:
            if isinstance(b, interface):
                yield b

    def cipher_supported(self, algorithm, mode):
        return any(
            b.cipher_supported(algorithm, mode)
            for b in self._filtered_backends(CipherBackend)
        )

    def create_symmetric_encryption_ctx(self, algorithm, mode):
        for b in self._filtered_backends(CipherBackend):
            try:
                return b.create_symmetric_encryption_ctx(algorithm, mode)
            except UnsupportedAlgorithm:
                pass
        raise UnsupportedAlgorithm(
            "cipher {0} in {1} mode is not supported by this backend.".format(
                algorithm.name, mode.name if mode else mode),
            _Reasons.UNSUPPORTED_CIPHER
        )

    def create_symmetric_decryption_ctx(self, algorithm, mode):
        for b in self._filtered_backends(CipherBackend):
            try:
                return b.create_symmetric_decryption_ctx(algorithm, mode)
            except UnsupportedAlgorithm:
                pass
        raise UnsupportedAlgorithm(
            "cipher {0} in {1} mode is not supported by this backend.".format(
                algorithm.name, mode.name if mode else mode),
            _Reasons.UNSUPPORTED_CIPHER
        )

    def hash_supported(self, algorithm):
        return any(
            b.hash_supported(algorithm)
            for b in self._filtered_backends(HashBackend)
        )

    def create_hash_ctx(self, algorithm):
        for b in self._filtered_backends(HashBackend):
            try:
                return b.create_hash_ctx(algorithm)
            except UnsupportedAlgorithm:
                pass
        raise UnsupportedAlgorithm(
            "{0} is not a supported hash on this backend.".format(
                algorithm.name),
            _Reasons.UNSUPPORTED_HASH
        )

    def hmac_supported(self, algorithm):
        return any(
            b.hmac_supported(algorithm)
            for b in self._filtered_backends(HMACBackend)
        )

    def create_hmac_ctx(self, key, algorithm):
        for b in self._filtered_backends(HMACBackend):
            try:
                return b.create_hmac_ctx(key, algorithm)
            except UnsupportedAlgorithm:
                pass
        raise UnsupportedAlgorithm(
            "{0} is not a supported hash on this backend.".format(
                algorithm.name),
            _Reasons.UNSUPPORTED_HASH
        )

    def pbkdf2_hmac_supported(self, algorithm):
        return any(
            b.pbkdf2_hmac_supported(algorithm)
            for b in self._filtered_backends(PBKDF2HMACBackend)
        )

    def derive_pbkdf2_hmac(self, algorithm, length, salt, iterations,
                           key_material):
        for b in self._filtered_backends(PBKDF2HMACBackend):
            try:
                return b.derive_pbkdf2_hmac(
                    algorithm, length, salt, iterations, key_material
                )
            except UnsupportedAlgorithm:
                pass
        raise UnsupportedAlgorithm(
            "{0} is not a supported hash on this backend.".format(
                algorithm.name),
            _Reasons.UNSUPPORTED_HASH
        )

    def generate_rsa_private_key(self, public_exponent, key_size):
        for b in self._filtered_backends(RSABackend):
            return b.generate_rsa_private_key(public_exponent, key_size)
        raise UnsupportedAlgorithm("RSA is not supported by the backend.",
                                   _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM)

    def generate_rsa_parameters_supported(self, public_exponent, key_size):
        for b in self._filtered_backends(RSABackend):
            return b.generate_rsa_parameters_supported(
                public_exponent, key_size
            )
        raise UnsupportedAlgorithm("RSA is not supported by the backend.",
                                   _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM)

    def create_rsa_signature_ctx(self, private_key, padding, algorithm):
        for b in self._filtered_backends(RSABackend):
            return b.create_rsa_signature_ctx(private_key, padding, algorithm)
        raise UnsupportedAlgorithm("RSA is not supported by the backend.",
                                   _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM)

    def create_rsa_verification_ctx(self, public_key, signature, padding,
                                    algorithm):
        for b in self._filtered_backends(RSABackend):
            return b.create_rsa_verification_ctx(public_key, signature,
                                                 padding, algorithm)
        raise UnsupportedAlgorithm("RSA is not supported by the backend.",
                                   _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM)

    def mgf1_hash_supported(self, algorithm):
        for b in self._filtered_backends(RSABackend):
            return b.mgf1_hash_supported(algorithm)
        raise UnsupportedAlgorithm("RSA is not supported by the backend.",
                                   _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM)

    def decrypt_rsa(self, private_key, ciphertext, padding):
        for b in self._filtered_backends(RSABackend):
            return b.decrypt_rsa(private_key, ciphertext, padding)
        raise UnsupportedAlgorithm("RSA is not supported by the backend.",
                                   _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM)

    def encrypt_rsa(self, public_key, plaintext, padding):
        for b in self._filtered_backends(RSABackend):
            return b.encrypt_rsa(public_key, plaintext, padding)
        raise UnsupportedAlgorithm("RSA is not supported by the backend.",
                                   _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM)

    def rsa_padding_supported(self, padding):
        for b in self._filtered_backends(RSABackend):
            return b.rsa_padding_supported(padding)
        raise UnsupportedAlgorithm("RSA is not supported by the backend.",
                                   _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM)

    def generate_dsa_parameters(self, key_size):
        for b in self._filtered_backends(DSABackend):
            return b.generate_dsa_parameters(key_size)
        raise UnsupportedAlgorithm("DSA is not supported by the backend.",
                                   _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM)

    def generate_dsa_private_key(self, parameters):
        for b in self._filtered_backends(DSABackend):
            return b.generate_dsa_private_key(parameters)
        raise UnsupportedAlgorithm("DSA is not supported by the backend.",
                                   _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM)

    def create_dsa_verification_ctx(self, public_key, signature, algorithm):
        for b in self._filtered_backends(DSABackend):
            return b.create_dsa_verification_ctx(public_key, signature,
                                                 algorithm)
        raise UnsupportedAlgorithm("DSA is not supported by the backend.",
                                   _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM)

    def create_dsa_signature_ctx(self, private_key, algorithm):
        for b in self._filtered_backends(DSABackend):
            return b.create_dsa_signature_ctx(private_key, algorithm)
        raise UnsupportedAlgorithm("DSA is not supported by the backend.",
                                   _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM)

    def dsa_hash_supported(self, algorithm):
        for b in self._filtered_backends(DSABackend):
            return b.dsa_hash_supported(algorithm)
        raise UnsupportedAlgorithm("DSA is not supported by the backend.",
                                   _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM)

    def dsa_parameters_supported(self, p, q, g):
        for b in self._filtered_backends(DSABackend):
            return b.dsa_parameters_supported(p, q, g)
        raise UnsupportedAlgorithm("DSA is not supported by the backend.",
                                   _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM)

    def cmac_algorithm_supported(self, algorithm):
        return any(
            b.cmac_algorithm_supported(algorithm)
            for b in self._filtered_backends(CMACBackend)
        )

    def create_cmac_ctx(self, algorithm):
        for b in self._filtered_backends(CMACBackend):
            try:
                return b.create_cmac_ctx(algorithm)
            except UnsupportedAlgorithm:
                pass
        raise UnsupportedAlgorithm("This backend does not support CMAC.",
                                   _Reasons.UNSUPPORTED_CIPHER)

########NEW FILE########
__FILENAME__ = backend
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import collections
import itertools
import math

import six

from cryptography import utils
from cryptography.exceptions import (
    AlreadyFinalized, InternalError, InvalidSignature, InvalidTag,
    UnsupportedAlgorithm, _Reasons
)
from cryptography.hazmat.backends.interfaces import (
    CMACBackend, CipherBackend, DSABackend, HMACBackend, HashBackend,
    PBKDF2HMACBackend, PKCS8SerializationBackend, RSABackend,
    TraditionalOpenSSLSerializationBackend
)
from cryptography.hazmat.bindings.openssl.binding import Binding
from cryptography.hazmat.primitives import hashes, interfaces
from cryptography.hazmat.primitives.asymmetric import dsa, rsa
from cryptography.hazmat.primitives.asymmetric.padding import (
    MGF1, OAEP, PKCS1v15, PSS
)
from cryptography.hazmat.primitives.ciphers.algorithms import (
    AES, ARC4, Blowfish, CAST5, Camellia, IDEA, SEED, TripleDES
)
from cryptography.hazmat.primitives.ciphers.modes import (
    CBC, CFB, CFB8, CTR, ECB, GCM, OFB
)


_MemoryBIO = collections.namedtuple("_MemoryBIO", ["bio", "char_ptr"])
_OpenSSLError = collections.namedtuple("_OpenSSLError",
                                       ["code", "lib", "func", "reason"])


@utils.register_interface(CipherBackend)
@utils.register_interface(CMACBackend)
@utils.register_interface(DSABackend)
@utils.register_interface(HashBackend)
@utils.register_interface(HMACBackend)
@utils.register_interface(PBKDF2HMACBackend)
@utils.register_interface(RSABackend)
@utils.register_interface(TraditionalOpenSSLSerializationBackend)
@utils.register_interface(PKCS8SerializationBackend)
class Backend(object):
    """
    OpenSSL API binding interfaces.
    """
    name = "openssl"

    def __init__(self):
        self._binding = Binding()
        self._ffi = self._binding.ffi
        self._lib = self._binding.lib

        self._binding.init_static_locks()

        # adds all ciphers/digests for EVP
        self._lib.OpenSSL_add_all_algorithms()
        # registers available SSL/TLS ciphers and digests
        self._lib.SSL_library_init()
        # loads error strings for libcrypto and libssl functions
        self._lib.SSL_load_error_strings()

        self._cipher_registry = {}
        self._register_default_ciphers()
        self.activate_osrandom_engine()

    def activate_builtin_random(self):
        # Obtain a new structural reference.
        e = self._lib.ENGINE_get_default_RAND()
        if e != self._ffi.NULL:
            self._lib.ENGINE_unregister_RAND(e)
            # Reset the RNG to use the new engine.
            self._lib.RAND_cleanup()
            # decrement the structural reference from get_default_RAND
            res = self._lib.ENGINE_finish(e)
            assert res == 1

    def activate_osrandom_engine(self):
        # Unregister and free the current engine.
        self.activate_builtin_random()
        # Fetches an engine by id and returns it. This creates a structural
        # reference.
        e = self._lib.ENGINE_by_id(self._lib.Cryptography_osrandom_engine_id)
        assert e != self._ffi.NULL
        # Initialize the engine for use. This adds a functional reference.
        res = self._lib.ENGINE_init(e)
        assert res == 1
        # Set the engine as the default RAND provider.
        res = self._lib.ENGINE_set_default_RAND(e)
        assert res == 1
        # Decrement the structural ref incremented by ENGINE_by_id.
        res = self._lib.ENGINE_free(e)
        assert res == 1
        # Decrement the functional ref incremented by ENGINE_init.
        res = self._lib.ENGINE_finish(e)
        assert res == 1
        # Reset the RNG to use the new engine.
        self._lib.RAND_cleanup()

    def openssl_version_text(self):
        """
        Friendly string name of the loaded OpenSSL library. This is not
        necessarily the same version as it was compiled against.

        Example: OpenSSL 1.0.1e 11 Feb 2013
        """
        return self._ffi.string(
            self._lib.SSLeay_version(self._lib.SSLEAY_VERSION)
        ).decode("ascii")

    def create_hmac_ctx(self, key, algorithm):
        return _HMACContext(self, key, algorithm)

    def hash_supported(self, algorithm):
        digest = self._lib.EVP_get_digestbyname(algorithm.name.encode("ascii"))
        return digest != self._ffi.NULL

    def hmac_supported(self, algorithm):
        return self.hash_supported(algorithm)

    def create_hash_ctx(self, algorithm):
        return _HashContext(self, algorithm)

    def cipher_supported(self, cipher, mode):
        if self._evp_cipher_supported(cipher, mode):
            return True
        elif isinstance(mode, CTR) and isinstance(cipher, AES):
            return True
        else:
            return False

    def _evp_cipher_supported(self, cipher, mode):
        try:
            adapter = self._cipher_registry[type(cipher), type(mode)]
        except KeyError:
            return False
        evp_cipher = adapter(self, cipher, mode)
        return self._ffi.NULL != evp_cipher

    def register_cipher_adapter(self, cipher_cls, mode_cls, adapter):
        if (cipher_cls, mode_cls) in self._cipher_registry:
            raise ValueError("Duplicate registration for: {0} {1}.".format(
                cipher_cls, mode_cls)
            )
        self._cipher_registry[cipher_cls, mode_cls] = adapter

    def _register_default_ciphers(self):
        for mode_cls in [CBC, CTR, ECB, OFB, CFB, CFB8]:
            self.register_cipher_adapter(
                AES,
                mode_cls,
                GetCipherByName("{cipher.name}-{cipher.key_size}-{mode.name}")
            )
        for mode_cls in [CBC, CTR, ECB, OFB, CFB]:
            self.register_cipher_adapter(
                Camellia,
                mode_cls,
                GetCipherByName("{cipher.name}-{cipher.key_size}-{mode.name}")
            )
        for mode_cls in [CBC, CFB, CFB8, OFB]:
            self.register_cipher_adapter(
                TripleDES,
                mode_cls,
                GetCipherByName("des-ede3-{mode.name}")
            )
        for mode_cls in [CBC, CFB, OFB, ECB]:
            self.register_cipher_adapter(
                Blowfish,
                mode_cls,
                GetCipherByName("bf-{mode.name}")
            )
        for mode_cls in [CBC, CFB, OFB, ECB]:
            self.register_cipher_adapter(
                SEED,
                mode_cls,
                GetCipherByName("seed-{mode.name}")
            )
        for cipher_cls, mode_cls in itertools.product(
            [CAST5, IDEA],
            [CBC, OFB, CFB, ECB],
        ):
            self.register_cipher_adapter(
                cipher_cls,
                mode_cls,
                GetCipherByName("{cipher.name}-{mode.name}")
            )
        self.register_cipher_adapter(
            ARC4,
            type(None),
            GetCipherByName("rc4")
        )
        self.register_cipher_adapter(
            AES,
            GCM,
            GetCipherByName("{cipher.name}-{cipher.key_size}-{mode.name}")
        )

    def create_symmetric_encryption_ctx(self, cipher, mode):
        if (isinstance(mode, CTR) and isinstance(cipher, AES)
                and not self._evp_cipher_supported(cipher, mode)):
            # This is needed to provide support for AES CTR mode in OpenSSL
            # 0.9.8. It can be removed when we drop 0.9.8 support (RHEL 5
            # extended life ends 2020).
            return _AESCTRCipherContext(self, cipher, mode)
        else:
            return _CipherContext(self, cipher, mode, _CipherContext._ENCRYPT)

    def create_symmetric_decryption_ctx(self, cipher, mode):
        if (isinstance(mode, CTR) and isinstance(cipher, AES)
                and not self._evp_cipher_supported(cipher, mode)):
            # This is needed to provide support for AES CTR mode in OpenSSL
            # 0.9.8. It can be removed when we drop 0.9.8 support (RHEL 5
            # extended life ends 2020).
            return _AESCTRCipherContext(self, cipher, mode)
        else:
            return _CipherContext(self, cipher, mode, _CipherContext._DECRYPT)

    def pbkdf2_hmac_supported(self, algorithm):
        if self._lib.Cryptography_HAS_PBKDF2_HMAC:
            return self.hmac_supported(algorithm)
        else:
            # OpenSSL < 1.0.0 has an explicit PBKDF2-HMAC-SHA1 function,
            # so if the PBKDF2_HMAC function is missing we only support
            # SHA1 via PBKDF2_HMAC_SHA1.
            return isinstance(algorithm, hashes.SHA1)

    def derive_pbkdf2_hmac(self, algorithm, length, salt, iterations,
                           key_material):
        buf = self._ffi.new("char[]", length)
        if self._lib.Cryptography_HAS_PBKDF2_HMAC:
            evp_md = self._lib.EVP_get_digestbyname(
                algorithm.name.encode("ascii"))
            assert evp_md != self._ffi.NULL
            res = self._lib.PKCS5_PBKDF2_HMAC(
                key_material,
                len(key_material),
                salt,
                len(salt),
                iterations,
                evp_md,
                length,
                buf
            )
            assert res == 1
        else:
            if not isinstance(algorithm, hashes.SHA1):
                raise UnsupportedAlgorithm(
                    "This version of OpenSSL only supports PBKDF2HMAC with "
                    "SHA1.",
                    _Reasons.UNSUPPORTED_HASH
                )
            res = self._lib.PKCS5_PBKDF2_HMAC_SHA1(
                key_material,
                len(key_material),
                salt,
                len(salt),
                iterations,
                length,
                buf
            )
            assert res == 1

        return self._ffi.buffer(buf)[:]

    def _err_string(self, code):
        err_buf = self._ffi.new("char[]", 256)
        self._lib.ERR_error_string_n(code, err_buf, 256)
        return self._ffi.string(err_buf, 256)[:]

    def _consume_errors(self):
        errors = []
        while True:
            code = self._lib.ERR_get_error()
            if code == 0:
                break

            lib = self._lib.ERR_GET_LIB(code)
            func = self._lib.ERR_GET_FUNC(code)
            reason = self._lib.ERR_GET_REASON(code)

            errors.append(_OpenSSLError(code, lib, func, reason))
        return errors

    def _unknown_error(self, error):
        return InternalError(
            "Unknown error code {0} from OpenSSL, "
            "you should probably file a bug. {1}.".format(
                error.code, self._err_string(error.code)
            )
        )

    def _bn_to_int(self, bn):
        if six.PY3:
            # Python 3 has constant time from_bytes, so use that.

            bn_num_bytes = (self._lib.BN_num_bits(bn) + 7) // 8
            bin_ptr = self._ffi.new("unsigned char[]", bn_num_bytes)
            bin_len = self._lib.BN_bn2bin(bn, bin_ptr)
            assert bin_len > 0
            assert bin_ptr != self._ffi.NULL
            return int.from_bytes(self._ffi.buffer(bin_ptr)[:bin_len], "big")

        else:
            # Under Python 2 the best we can do is hex()

            hex_cdata = self._lib.BN_bn2hex(bn)
            assert hex_cdata != self._ffi.NULL
            hex_str = self._ffi.string(hex_cdata)
            self._lib.OPENSSL_free(hex_cdata)
            return int(hex_str, 16)

    def _int_to_bn(self, num, bn=None):
        """
        Converts a python integer to a BIGNUM. The returned BIGNUM will not
        be garbage collected (to support adding them to structs that take
        ownership of the object). Be sure to register it for GC if it will
        be discarded after use.
        """

        if bn is None:
            bn = self._ffi.NULL

        if six.PY3:
            # Python 3 has constant time to_bytes, so use that.

            binary = num.to_bytes(int(num.bit_length() / 8.0 + 1), "big")
            bn_ptr = self._lib.BN_bin2bn(binary, len(binary), bn)
            assert bn_ptr != self._ffi.NULL
            return bn_ptr

        else:
            # Under Python 2 the best we can do is hex()

            hex_num = hex(num).rstrip("L").lstrip("0x").encode("ascii") or b"0"
            bn_ptr = self._ffi.new("BIGNUM **")
            bn_ptr[0] = bn
            res = self._lib.BN_hex2bn(bn_ptr, hex_num)
            assert res != 0
            assert bn_ptr[0] != self._ffi.NULL
            return bn_ptr[0]

    def generate_rsa_private_key(self, public_exponent, key_size):
        if public_exponent < 3:
            raise ValueError("public_exponent must be >= 3.")

        if public_exponent & 1 == 0:
            raise ValueError("public_exponent must be odd.")

        if key_size < 512:
            raise ValueError("key_size must be at least 512-bits.")

        ctx = self._lib.RSA_new()
        assert ctx != self._ffi.NULL
        ctx = self._ffi.gc(ctx, self._lib.RSA_free)

        bn = self._int_to_bn(public_exponent)
        bn = self._ffi.gc(bn, self._lib.BN_free)

        res = self._lib.RSA_generate_key_ex(
            ctx, key_size, bn, self._ffi.NULL
        )
        assert res == 1

        return self._rsa_cdata_to_private_key(ctx)

    def generate_rsa_parameters_supported(self, public_exponent, key_size):
        return (public_exponent >= 3 and public_exponent & 1 != 0 and
                key_size >= 512)

    def _new_evp_pkey(self):
        evp_pkey = self._lib.EVP_PKEY_new()
        assert evp_pkey != self._ffi.NULL
        return self._ffi.gc(evp_pkey, self._lib.EVP_PKEY_free)

    def _rsa_private_key_to_evp_pkey(self, private_key):
        evp_pkey = self._new_evp_pkey()
        rsa_cdata = self._rsa_cdata_from_private_key(private_key)

        res = self._lib.EVP_PKEY_assign_RSA(evp_pkey, rsa_cdata)
        assert res == 1

        return evp_pkey

    def _rsa_public_key_to_evp_pkey(self, public_key):
        evp_pkey = self._new_evp_pkey()
        rsa_cdata = self._rsa_cdata_from_public_key(public_key)

        res = self._lib.EVP_PKEY_assign_RSA(evp_pkey, rsa_cdata)
        assert res == 1

        return evp_pkey

    def _bytes_to_bio(self, data):
        """
        Return a _MemoryBIO namedtuple of (BIO, char*).

        The char* is the storage for the BIO and it must stay alive until the
        BIO is finished with.
        """
        data_char_p = backend._ffi.new("char[]", data)
        bio = backend._lib.BIO_new_mem_buf(
            data_char_p, len(data)
        )
        assert bio != self._ffi.NULL

        return _MemoryBIO(self._ffi.gc(bio, self._lib.BIO_free), data_char_p)

    def _evp_pkey_to_private_key(self, evp_pkey):
        """
        Return the appropriate type of PrivateKey given an evp_pkey cdata
        pointer.
        """

        type = evp_pkey.type

        if type == self._lib.EVP_PKEY_RSA:
            rsa_cdata = self._lib.EVP_PKEY_get1_RSA(evp_pkey)
            assert rsa_cdata != self._ffi.NULL
            rsa_cdata = self._ffi.gc(rsa_cdata, self._lib.RSA_free)
            return self._rsa_cdata_to_private_key(rsa_cdata)
        elif type == self._lib.EVP_PKEY_DSA:
            dsa_cdata = self._lib.EVP_PKEY_get1_DSA(evp_pkey)
            assert dsa_cdata != self._ffi.NULL
            dsa_cdata = self._ffi.gc(dsa_cdata, self._lib.DSA_free)
            return self._dsa_cdata_to_private_key(dsa_cdata)
        else:
            raise UnsupportedAlgorithm("Unsupported key type.")

    def _dsa_cdata_to_private_key(self, cdata):
        return dsa.DSAPrivateKey(
            modulus=self._bn_to_int(cdata.p),
            subgroup_order=self._bn_to_int(cdata.q),
            generator=self._bn_to_int(cdata.g),
            x=self._bn_to_int(cdata.priv_key),
            y=self._bn_to_int(cdata.pub_key)
        )

    def _rsa_cdata_to_private_key(self, cdata):
        return rsa.RSAPrivateKey(
            p=self._bn_to_int(cdata.p),
            q=self._bn_to_int(cdata.q),
            dmp1=self._bn_to_int(cdata.dmp1),
            dmq1=self._bn_to_int(cdata.dmq1),
            iqmp=self._bn_to_int(cdata.iqmp),
            private_exponent=self._bn_to_int(cdata.d),
            public_exponent=self._bn_to_int(cdata.e),
            modulus=self._bn_to_int(cdata.n),
        )

    def _pem_password_cb(self, password):
        """
        Generate a pem_password_cb function pointer that copied the password to
        OpenSSL as required and returns the number of bytes copied.

        typedef int pem_password_cb(char *buf, int size,
                                    int rwflag, void *userdata);

        Useful for decrypting PKCS8 files and so on.

        Returns a tuple of (cdata function pointer, callback function).
        """

        def pem_password_cb(buf, size, writing, userdata):
            pem_password_cb.called += 1

            if not password or len(password) >= size:
                return 0
            else:
                pw_buf = self._ffi.buffer(buf, size)
                pw_buf[:len(password)] = password
                return len(password)

        pem_password_cb.called = 0

        return (
            self._ffi.callback("int (char *, int, int, void *)",
                               pem_password_cb),
            pem_password_cb
        )

    def _rsa_cdata_from_private_key(self, private_key):
        # Does not GC the RSA cdata. You *must* make sure it's freed
        # correctly yourself!
        ctx = self._lib.RSA_new()
        assert ctx != self._ffi.NULL
        ctx.p = self._int_to_bn(private_key.p)
        ctx.q = self._int_to_bn(private_key.q)
        ctx.d = self._int_to_bn(private_key.d)
        ctx.e = self._int_to_bn(private_key.e)
        ctx.n = self._int_to_bn(private_key.n)
        ctx.dmp1 = self._int_to_bn(private_key.dmp1)
        ctx.dmq1 = self._int_to_bn(private_key.dmq1)
        ctx.iqmp = self._int_to_bn(private_key.iqmp)
        res = self._lib.RSA_blinding_on(ctx, self._ffi.NULL)
        assert res == 1

        return ctx

    def _rsa_cdata_from_public_key(self, public_key):
        # Does not GC the RSA cdata. You *must* make sure it's freed
        # correctly yourself!

        ctx = self._lib.RSA_new()
        assert ctx != self._ffi.NULL
        ctx.e = self._int_to_bn(public_key.e)
        ctx.n = self._int_to_bn(public_key.n)
        res = self._lib.RSA_blinding_on(ctx, self._ffi.NULL)
        assert res == 1

        return ctx

    def create_rsa_signature_ctx(self, private_key, padding, algorithm):
        return _RSASignatureContext(self, private_key, padding, algorithm)

    def create_rsa_verification_ctx(self, public_key, signature, padding,
                                    algorithm):
        return _RSAVerificationContext(self, public_key, signature, padding,
                                       algorithm)

    def mgf1_hash_supported(self, algorithm):
        if self._lib.Cryptography_HAS_MGF1_MD:
            return self.hash_supported(algorithm)
        else:
            return isinstance(algorithm, hashes.SHA1)

    def rsa_padding_supported(self, padding):
        if isinstance(padding, PKCS1v15):
            return True
        elif isinstance(padding, PSS) and isinstance(padding._mgf, MGF1):
            return self.mgf1_hash_supported(padding._mgf._algorithm)
        elif isinstance(padding, OAEP) and isinstance(padding._mgf, MGF1):
            return isinstance(padding._mgf._algorithm, hashes.SHA1)
        else:
            return False

    def generate_dsa_parameters(self, key_size):
        if key_size not in (1024, 2048, 3072):
            raise ValueError(
                "Key size must be 1024 or 2048 or 3072 bits.")

        if (self._lib.OPENSSL_VERSION_NUMBER < 0x1000000f and
                key_size > 1024):
            raise ValueError(
                "Key size must be 1024 because OpenSSL < 1.0.0 doesn't "
                "support larger key sizes.")

        ctx = self._lib.DSA_new()
        assert ctx != self._ffi.NULL
        ctx = self._ffi.gc(ctx, self._lib.DSA_free)

        res = self._lib.DSA_generate_parameters_ex(
            ctx, key_size, self._ffi.NULL, 0,
            self._ffi.NULL, self._ffi.NULL, self._ffi.NULL
        )

        assert res == 1

        return dsa.DSAParameters(
            modulus=self._bn_to_int(ctx.p),
            subgroup_order=self._bn_to_int(ctx.q),
            generator=self._bn_to_int(ctx.g)
        )

    def generate_dsa_private_key(self, parameters):
        ctx = self._lib.DSA_new()
        assert ctx != self._ffi.NULL
        ctx = self._ffi.gc(ctx, self._lib.DSA_free)
        ctx.p = self._int_to_bn(parameters.p)
        ctx.q = self._int_to_bn(parameters.q)
        ctx.g = self._int_to_bn(parameters.g)

        self._lib.DSA_generate_key(ctx)

        return dsa.DSAPrivateKey(
            modulus=self._bn_to_int(ctx.p),
            subgroup_order=self._bn_to_int(ctx.q),
            generator=self._bn_to_int(ctx.g),
            x=self._bn_to_int(ctx.priv_key),
            y=self._bn_to_int(ctx.pub_key)
        )

    def create_dsa_signature_ctx(self, private_key, algorithm):
        return _DSASignatureContext(self, private_key, algorithm)

    def create_dsa_verification_ctx(self, public_key, signature,
                                    algorithm):
        return _DSAVerificationContext(self, public_key, signature,
                                       algorithm)

    def _dsa_cdata_from_public_key(self, public_key):
        # Does not GC the DSA cdata. You *must* make sure it's freed
        # correctly yourself!
        ctx = self._lib.DSA_new()
        assert ctx != self._ffi.NULL
        parameters = public_key.parameters()
        ctx.p = self._int_to_bn(parameters.p)
        ctx.q = self._int_to_bn(parameters.q)
        ctx.g = self._int_to_bn(parameters.g)
        ctx.pub_key = self._int_to_bn(public_key.y)
        return ctx

    def _dsa_cdata_from_private_key(self, private_key):
        # Does not GC the DSA cdata. You *must* make sure it's freed
        # correctly yourself!
        ctx = self._lib.DSA_new()
        assert ctx != self._ffi.NULL
        parameters = private_key.parameters()
        ctx.p = self._int_to_bn(parameters.p)
        ctx.q = self._int_to_bn(parameters.q)
        ctx.g = self._int_to_bn(parameters.g)
        ctx.priv_key = self._int_to_bn(private_key.x)
        ctx.pub_key = self._int_to_bn(private_key.y)
        return ctx

    def dsa_hash_supported(self, algorithm):
        if self._lib.OPENSSL_VERSION_NUMBER < 0x1000000f:
            return isinstance(algorithm, hashes.SHA1)
        else:
            return self.hash_supported(algorithm)

    def dsa_parameters_supported(self, p, q, g):
        if self._lib.OPENSSL_VERSION_NUMBER < 0x1000000f:
            return (utils.bit_length(p) <= 1024 and utils.bit_length(q) <= 160)
        else:
            return True

    def decrypt_rsa(self, private_key, ciphertext, padding):
        key_size_bytes = int(math.ceil(private_key.key_size / 8.0))
        if key_size_bytes != len(ciphertext):
            raise ValueError("Ciphertext length must be equal to key size.")

        return self._enc_dec_rsa(private_key, ciphertext, padding)

    def encrypt_rsa(self, public_key, plaintext, padding):
        return self._enc_dec_rsa(public_key, plaintext, padding)

    def _enc_dec_rsa(self, key, data, padding):
        if isinstance(padding, PKCS1v15):
            padding_enum = self._lib.RSA_PKCS1_PADDING
        elif isinstance(padding, OAEP):
            padding_enum = self._lib.RSA_PKCS1_OAEP_PADDING
            if not isinstance(padding._mgf, MGF1):
                raise UnsupportedAlgorithm(
                    "Only MGF1 is supported by this backend.",
                    _Reasons.UNSUPPORTED_MGF
                )

            if not isinstance(padding._mgf._algorithm, hashes.SHA1):
                raise UnsupportedAlgorithm(
                    "This backend supports only SHA1 inside MGF1 when "
                    "using OAEP.",
                    _Reasons.UNSUPPORTED_HASH
                )

            if padding._label is not None and padding._label != b"":
                raise ValueError("This backend does not support OAEP labels.")

            if not isinstance(padding._algorithm, hashes.SHA1):
                raise UnsupportedAlgorithm(
                    "This backend only supports SHA1 when using OAEP.",
                    _Reasons.UNSUPPORTED_HASH
                )
        else:
            raise UnsupportedAlgorithm(
                "{0} is not supported by this backend.".format(
                    padding.name
                ),
                _Reasons.UNSUPPORTED_PADDING
            )

        if self._lib.Cryptography_HAS_PKEY_CTX:
            return self._enc_dec_rsa_pkey_ctx(key, data, padding_enum)
        else:
            return self._enc_dec_rsa_098(key, data, padding_enum)

    def _enc_dec_rsa_pkey_ctx(self, key, data, padding_enum):
        if isinstance(key, rsa.RSAPublicKey):
            init = self._lib.EVP_PKEY_encrypt_init
            crypt = self._lib.Cryptography_EVP_PKEY_encrypt
            evp_pkey = self._rsa_public_key_to_evp_pkey(key)
        else:
            init = self._lib.EVP_PKEY_decrypt_init
            crypt = self._lib.Cryptography_EVP_PKEY_decrypt
            evp_pkey = self._rsa_private_key_to_evp_pkey(key)

        pkey_ctx = self._lib.EVP_PKEY_CTX_new(
            evp_pkey, self._ffi.NULL
        )
        assert pkey_ctx != self._ffi.NULL
        pkey_ctx = self._ffi.gc(pkey_ctx, self._lib.EVP_PKEY_CTX_free)
        res = init(pkey_ctx)
        assert res == 1
        res = self._lib.EVP_PKEY_CTX_set_rsa_padding(
            pkey_ctx, padding_enum)
        assert res > 0
        buf_size = self._lib.EVP_PKEY_size(evp_pkey)
        assert buf_size > 0
        outlen = self._ffi.new("size_t *", buf_size)
        buf = self._ffi.new("char[]", buf_size)
        res = crypt(
            pkey_ctx,
            buf,
            outlen,
            data,
            len(data)
        )
        if res <= 0:
            self._handle_rsa_enc_dec_error(key)

        return self._ffi.buffer(buf)[:outlen[0]]

    def _enc_dec_rsa_098(self, key, data, padding_enum):
        if isinstance(key, rsa.RSAPublicKey):
            crypt = self._lib.RSA_public_encrypt
            rsa_cdata = self._rsa_cdata_from_public_key(key)
        else:
            crypt = self._lib.RSA_private_decrypt
            rsa_cdata = self._rsa_cdata_from_private_key(key)

        rsa_cdata = self._ffi.gc(rsa_cdata, self._lib.RSA_free)
        key_size = self._lib.RSA_size(rsa_cdata)
        assert key_size > 0
        buf = self._ffi.new("unsigned char[]", key_size)
        res = crypt(
            len(data),
            data,
            buf,
            rsa_cdata,
            padding_enum
        )
        if res < 0:
            self._handle_rsa_enc_dec_error(key)

        return self._ffi.buffer(buf)[:res]

    def _handle_rsa_enc_dec_error(self, key):
        errors = self._consume_errors()
        assert errors
        assert errors[0].lib == self._lib.ERR_LIB_RSA
        if isinstance(key, rsa.RSAPublicKey):
            assert (errors[0].reason ==
                    self._lib.RSA_R_DATA_TOO_LARGE_FOR_KEY_SIZE)
            raise ValueError(
                "Data too long for key size. Encrypt less data or use a "
                "larger key size."
            )
        else:
            assert (
                errors[0].reason == self._lib.RSA_R_BLOCK_TYPE_IS_NOT_01 or
                errors[0].reason == self._lib.RSA_R_BLOCK_TYPE_IS_NOT_02
            )
            raise ValueError("Decryption failed.")

    def cmac_algorithm_supported(self, algorithm):
        return (
            self._lib.Cryptography_HAS_CMAC == 1
            and self.cipher_supported(algorithm, CBC(
                b"\x00" * algorithm.block_size))
        )

    def create_cmac_ctx(self, algorithm):
        return _CMACContext(self, algorithm)

    def load_traditional_openssl_pem_private_key(self, data, password):
        # OpenSSLs API for loading PKCS#8 certs can also load the traditional
        # format so we just use that for both of them.

        return self.load_pkcs8_pem_private_key(data, password)

    def load_pkcs8_pem_private_key(self, data, password):
        mem_bio = self._bytes_to_bio(data)

        password_callback, password_func = self._pem_password_cb(password)

        evp_pkey = self._lib.PEM_read_bio_PrivateKey(
            mem_bio.bio,
            self._ffi.NULL,
            password_callback,
            self._ffi.NULL
        )

        if evp_pkey == self._ffi.NULL:
            errors = self._consume_errors()
            if not errors:
                raise ValueError("Could not unserialize key data.")

            if (
                errors[0][1:] == (
                    self._lib.ERR_LIB_PEM,
                    self._lib.PEM_F_PEM_DO_HEADER,
                    self._lib.PEM_R_BAD_PASSWORD_READ
                )
            ) or (
                errors[0][1:] == (
                    self._lib.ERR_LIB_PEM,
                    self._lib.PEM_F_PEM_READ_BIO_PRIVATEKEY,
                    self._lib.PEM_R_BAD_PASSWORD_READ
                )
            ):
                assert not password
                raise TypeError(
                    "Password was not given but private key is encrypted.")

            elif errors[0][1:] == (
                self._lib.ERR_LIB_EVP,
                self._lib.EVP_F_EVP_DECRYPTFINAL_EX,
                self._lib.EVP_R_BAD_DECRYPT
            ):
                raise ValueError(
                    "Bad decrypt. Incorrect password?"
                )

            elif errors[0][1:] in (
                (
                    self._lib.ERR_LIB_PEM,
                    self._lib.PEM_F_PEM_GET_EVP_CIPHER_INFO,
                    self._lib.PEM_R_UNSUPPORTED_ENCRYPTION
                ),

                (
                    self._lib.ERR_LIB_EVP,
                    self._lib.EVP_F_EVP_PBE_CIPHERINIT,
                    self._lib.EVP_R_UNKNOWN_PBE_ALGORITHM
                )
            ):
                raise UnsupportedAlgorithm(
                    "PEM data is encrypted with an unsupported cipher",
                    _Reasons.UNSUPPORTED_CIPHER
                )

            elif any(
                error[1:] == (
                    self._lib.ERR_LIB_EVP,
                    self._lib.EVP_F_EVP_PKCS82PKEY,
                    self._lib.EVP_R_UNSUPPORTED_PRIVATE_KEY_ALGORITHM
                )
                for error in errors
            ):
                raise UnsupportedAlgorithm(
                    "Unsupported public key algorithm.",
                    _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM
                )

            else:
                assert errors[0][1] in (
                    self._lib.ERR_LIB_EVP,
                    self._lib.ERR_LIB_PEM,
                    self._lib.ERR_LIB_ASN1,
                )
                raise ValueError("Could not unserialize key data.")

        evp_pkey = self._ffi.gc(evp_pkey, self._lib.EVP_PKEY_free)

        if password is not None and password_func.called == 0:
            raise TypeError(
                "Password was given but private key is not encrypted.")

        assert (
            (password is not None and password_func.called == 1) or
            password is None
        )

        return self._evp_pkey_to_private_key(evp_pkey)


class GetCipherByName(object):
    def __init__(self, fmt):
        self._fmt = fmt

    def __call__(self, backend, cipher, mode):
        cipher_name = self._fmt.format(cipher=cipher, mode=mode).lower()
        return backend._lib.EVP_get_cipherbyname(cipher_name.encode("ascii"))


@utils.register_interface(interfaces.CipherContext)
@utils.register_interface(interfaces.AEADCipherContext)
@utils.register_interface(interfaces.AEADEncryptionContext)
class _CipherContext(object):
    _ENCRYPT = 1
    _DECRYPT = 0

    def __init__(self, backend, cipher, mode, operation):
        self._backend = backend
        self._cipher = cipher
        self._mode = mode
        self._operation = operation
        self._tag = None

        if isinstance(self._cipher, interfaces.BlockCipherAlgorithm):
            self._block_size = self._cipher.block_size
        else:
            self._block_size = 1

        ctx = self._backend._lib.EVP_CIPHER_CTX_new()
        ctx = self._backend._ffi.gc(
            ctx, self._backend._lib.EVP_CIPHER_CTX_free
        )

        registry = self._backend._cipher_registry
        try:
            adapter = registry[type(cipher), type(mode)]
        except KeyError:
            raise UnsupportedAlgorithm(
                "cipher {0} in {1} mode is not supported "
                "by this backend.".format(
                    cipher.name, mode.name if mode else mode),
                _Reasons.UNSUPPORTED_CIPHER
            )

        evp_cipher = adapter(self._backend, cipher, mode)
        if evp_cipher == self._backend._ffi.NULL:
            raise UnsupportedAlgorithm(
                "cipher {0} in {1} mode is not supported "
                "by this backend.".format(
                    cipher.name, mode.name if mode else mode),
                _Reasons.UNSUPPORTED_CIPHER
            )

        if isinstance(mode, interfaces.ModeWithInitializationVector):
            iv_nonce = mode.initialization_vector
        elif isinstance(mode, interfaces.ModeWithNonce):
            iv_nonce = mode.nonce
        else:
            iv_nonce = self._backend._ffi.NULL
        # begin init with cipher and operation type
        res = self._backend._lib.EVP_CipherInit_ex(ctx, evp_cipher,
                                                   self._backend._ffi.NULL,
                                                   self._backend._ffi.NULL,
                                                   self._backend._ffi.NULL,
                                                   operation)
        assert res != 0
        # set the key length to handle variable key ciphers
        res = self._backend._lib.EVP_CIPHER_CTX_set_key_length(
            ctx, len(cipher.key)
        )
        assert res != 0
        if isinstance(mode, GCM):
            res = self._backend._lib.EVP_CIPHER_CTX_ctrl(
                ctx, self._backend._lib.EVP_CTRL_GCM_SET_IVLEN,
                len(iv_nonce), self._backend._ffi.NULL
            )
            assert res != 0
            if operation == self._DECRYPT:
                res = self._backend._lib.EVP_CIPHER_CTX_ctrl(
                    ctx, self._backend._lib.EVP_CTRL_GCM_SET_TAG,
                    len(mode.tag), mode.tag
                )
                assert res != 0

        # pass key/iv
        res = self._backend._lib.EVP_CipherInit_ex(
            ctx,
            self._backend._ffi.NULL,
            self._backend._ffi.NULL,
            cipher.key,
            iv_nonce,
            operation
        )
        assert res != 0
        # We purposely disable padding here as it's handled higher up in the
        # API.
        self._backend._lib.EVP_CIPHER_CTX_set_padding(ctx, 0)
        self._ctx = ctx

    def update(self, data):
        # OpenSSL 0.9.8e has an assertion in its EVP code that causes it
        # to SIGABRT if you call update with an empty byte string. This can be
        # removed when we drop support for 0.9.8e (CentOS/RHEL 5). This branch
        # should be taken only when length is zero and mode is not GCM because
        # AES GCM can return improper tag values if you don't call update
        # with empty plaintext when authenticating AAD for ...reasons.
        if len(data) == 0 and not isinstance(self._mode, GCM):
            return b""

        buf = self._backend._ffi.new("unsigned char[]",
                                     len(data) + self._block_size - 1)
        outlen = self._backend._ffi.new("int *")
        res = self._backend._lib.EVP_CipherUpdate(self._ctx, buf, outlen, data,
                                                  len(data))
        assert res != 0
        return self._backend._ffi.buffer(buf)[:outlen[0]]

    def finalize(self):
        buf = self._backend._ffi.new("unsigned char[]", self._block_size)
        outlen = self._backend._ffi.new("int *")
        res = self._backend._lib.EVP_CipherFinal_ex(self._ctx, buf, outlen)
        if res == 0:
            errors = self._backend._consume_errors()

            if not errors and isinstance(self._mode, GCM):
                raise InvalidTag

            assert errors

            if errors[0][1:] == (
                self._backend._lib.ERR_LIB_EVP,
                self._backend._lib.EVP_F_EVP_ENCRYPTFINAL_EX,
                self._backend._lib.EVP_R_DATA_NOT_MULTIPLE_OF_BLOCK_LENGTH
            ) or errors[0][1:] == (
                self._backend._lib.ERR_LIB_EVP,
                self._backend._lib.EVP_F_EVP_DECRYPTFINAL_EX,
                self._backend._lib.EVP_R_DATA_NOT_MULTIPLE_OF_BLOCK_LENGTH
            ):
                raise ValueError(
                    "The length of the provided data is not a multiple of "
                    "the block length."
                )
            else:
                raise self._backend._unknown_error(errors[0])

        if (isinstance(self._mode, GCM) and
           self._operation == self._ENCRYPT):
            block_byte_size = self._block_size // 8
            tag_buf = self._backend._ffi.new(
                "unsigned char[]", block_byte_size
            )
            res = self._backend._lib.EVP_CIPHER_CTX_ctrl(
                self._ctx, self._backend._lib.EVP_CTRL_GCM_GET_TAG,
                block_byte_size, tag_buf
            )
            assert res != 0
            self._tag = self._backend._ffi.buffer(tag_buf)[:]

        res = self._backend._lib.EVP_CIPHER_CTX_cleanup(self._ctx)
        assert res == 1
        return self._backend._ffi.buffer(buf)[:outlen[0]]

    def authenticate_additional_data(self, data):
        outlen = self._backend._ffi.new("int *")
        res = self._backend._lib.EVP_CipherUpdate(
            self._ctx, self._backend._ffi.NULL, outlen, data, len(data)
        )
        assert res != 0

    @property
    def tag(self):
        return self._tag


@utils.register_interface(interfaces.CipherContext)
class _AESCTRCipherContext(object):
    """
    This is needed to provide support for AES CTR mode in OpenSSL 0.9.8. It can
    be removed when we drop 0.9.8 support (RHEL5 extended life ends 2020).
    """
    def __init__(self, backend, cipher, mode):
        self._backend = backend

        self._key = self._backend._ffi.new("AES_KEY *")
        assert self._key != self._backend._ffi.NULL
        res = self._backend._lib.AES_set_encrypt_key(
            cipher.key, len(cipher.key) * 8, self._key
        )
        assert res == 0
        self._ecount = self._backend._ffi.new("char[]", 16)
        self._nonce = self._backend._ffi.new("char[16]", mode.nonce)
        self._num = self._backend._ffi.new("unsigned int *", 0)

    def update(self, data):
        buf = self._backend._ffi.new("unsigned char[]", len(data))
        self._backend._lib.AES_ctr128_encrypt(
            data, buf, len(data), self._key, self._nonce,
            self._ecount, self._num
        )
        return self._backend._ffi.buffer(buf)[:]

    def finalize(self):
        self._key = None
        self._ecount = None
        self._nonce = None
        self._num = None
        return b""


@utils.register_interface(interfaces.HashContext)
class _HashContext(object):
    def __init__(self, backend, algorithm, ctx=None):
        self.algorithm = algorithm

        self._backend = backend

        if ctx is None:
            ctx = self._backend._lib.EVP_MD_CTX_create()
            ctx = self._backend._ffi.gc(ctx,
                                        self._backend._lib.EVP_MD_CTX_destroy)
            evp_md = self._backend._lib.EVP_get_digestbyname(
                algorithm.name.encode("ascii"))
            if evp_md == self._backend._ffi.NULL:
                raise UnsupportedAlgorithm(
                    "{0} is not a supported hash on this backend.".format(
                        algorithm.name),
                    _Reasons.UNSUPPORTED_HASH
                )
            res = self._backend._lib.EVP_DigestInit_ex(ctx, evp_md,
                                                       self._backend._ffi.NULL)
            assert res != 0

        self._ctx = ctx

    def copy(self):
        copied_ctx = self._backend._lib.EVP_MD_CTX_create()
        copied_ctx = self._backend._ffi.gc(
            copied_ctx, self._backend._lib.EVP_MD_CTX_destroy
        )
        res = self._backend._lib.EVP_MD_CTX_copy_ex(copied_ctx, self._ctx)
        assert res != 0
        return _HashContext(self._backend, self.algorithm, ctx=copied_ctx)

    def update(self, data):
        res = self._backend._lib.EVP_DigestUpdate(self._ctx, data, len(data))
        assert res != 0

    def finalize(self):
        buf = self._backend._ffi.new("unsigned char[]",
                                     self._backend._lib.EVP_MAX_MD_SIZE)
        outlen = self._backend._ffi.new("unsigned int *")
        res = self._backend._lib.EVP_DigestFinal_ex(self._ctx, buf, outlen)
        assert res != 0
        assert outlen[0] == self.algorithm.digest_size
        res = self._backend._lib.EVP_MD_CTX_cleanup(self._ctx)
        assert res == 1
        return self._backend._ffi.buffer(buf)[:outlen[0]]


@utils.register_interface(interfaces.HashContext)
class _HMACContext(object):
    def __init__(self, backend, key, algorithm, ctx=None):
        self.algorithm = algorithm
        self._backend = backend

        if ctx is None:
            ctx = self._backend._ffi.new("HMAC_CTX *")
            self._backend._lib.HMAC_CTX_init(ctx)
            ctx = self._backend._ffi.gc(
                ctx, self._backend._lib.HMAC_CTX_cleanup
            )
            evp_md = self._backend._lib.EVP_get_digestbyname(
                algorithm.name.encode('ascii'))
            if evp_md == self._backend._ffi.NULL:
                raise UnsupportedAlgorithm(
                    "{0} is not a supported hash on this backend.".format(
                        algorithm.name),
                    _Reasons.UNSUPPORTED_HASH
                )
            res = self._backend._lib.Cryptography_HMAC_Init_ex(
                ctx, key, len(key), evp_md, self._backend._ffi.NULL
            )
            assert res != 0

        self._ctx = ctx
        self._key = key

    def copy(self):
        copied_ctx = self._backend._ffi.new("HMAC_CTX *")
        self._backend._lib.HMAC_CTX_init(copied_ctx)
        copied_ctx = self._backend._ffi.gc(
            copied_ctx, self._backend._lib.HMAC_CTX_cleanup
        )
        res = self._backend._lib.Cryptography_HMAC_CTX_copy(
            copied_ctx, self._ctx
        )
        assert res != 0
        return _HMACContext(
            self._backend, self._key, self.algorithm, ctx=copied_ctx
        )

    def update(self, data):
        res = self._backend._lib.Cryptography_HMAC_Update(
            self._ctx, data, len(data)
        )
        assert res != 0

    def finalize(self):
        buf = self._backend._ffi.new("unsigned char[]",
                                     self._backend._lib.EVP_MAX_MD_SIZE)
        outlen = self._backend._ffi.new("unsigned int *")
        res = self._backend._lib.Cryptography_HMAC_Final(
            self._ctx, buf, outlen
        )
        assert res != 0
        assert outlen[0] == self.algorithm.digest_size
        self._backend._lib.HMAC_CTX_cleanup(self._ctx)
        return self._backend._ffi.buffer(buf)[:outlen[0]]


def _get_rsa_pss_salt_length(pss, key_size, digest_size):
    if pss._mgf._salt_length is not None:
        salt = pss._mgf._salt_length
    else:
        salt = pss._salt_length

    if salt is MGF1.MAX_LENGTH or salt is PSS.MAX_LENGTH:
        # bit length - 1 per RFC 3447
        emlen = int(math.ceil((key_size - 1) / 8.0))
        salt_length = emlen - digest_size - 2
        assert salt_length >= 0
        return salt_length
    else:
        return salt


@utils.register_interface(interfaces.AsymmetricSignatureContext)
class _RSASignatureContext(object):
    def __init__(self, backend, private_key, padding, algorithm):
        self._backend = backend
        self._private_key = private_key

        if not isinstance(padding, interfaces.AsymmetricPadding):
            raise TypeError(
                "Expected provider of interfaces.AsymmetricPadding.")

        if isinstance(padding, PKCS1v15):
            if self._backend._lib.Cryptography_HAS_PKEY_CTX:
                self._finalize_method = self._finalize_pkey_ctx
                self._padding_enum = self._backend._lib.RSA_PKCS1_PADDING
            else:
                self._finalize_method = self._finalize_pkcs1
        elif isinstance(padding, PSS):
            if not isinstance(padding._mgf, MGF1):
                raise UnsupportedAlgorithm(
                    "Only MGF1 is supported by this backend.",
                    _Reasons.UNSUPPORTED_MGF
                )

            # Size of key in bytes - 2 is the maximum
            # PSS signature length (salt length is checked later)
            key_size_bytes = int(math.ceil(private_key.key_size / 8.0))
            if key_size_bytes - algorithm.digest_size - 2 < 0:
                raise ValueError("Digest too large for key size. Use a larger "
                                 "key.")

            if not self._backend.mgf1_hash_supported(padding._mgf._algorithm):
                raise UnsupportedAlgorithm(
                    "When OpenSSL is older than 1.0.1 then only SHA1 is "
                    "supported with MGF1.",
                    _Reasons.UNSUPPORTED_HASH
                )

            if self._backend._lib.Cryptography_HAS_PKEY_CTX:
                self._finalize_method = self._finalize_pkey_ctx
                self._padding_enum = self._backend._lib.RSA_PKCS1_PSS_PADDING
            else:
                self._finalize_method = self._finalize_pss
        else:
            raise UnsupportedAlgorithm(
                "{0} is not supported by this backend.".format(padding.name),
                _Reasons.UNSUPPORTED_PADDING
            )

        self._padding = padding
        self._algorithm = algorithm
        self._hash_ctx = _HashContext(backend, self._algorithm)

    def update(self, data):
        if self._hash_ctx is None:
            raise AlreadyFinalized("Context has already been finalized.")

        self._hash_ctx.update(data)

    def finalize(self):
        if self._hash_ctx is None:
            raise AlreadyFinalized("Context has already been finalized.")

        evp_pkey = self._backend._rsa_private_key_to_evp_pkey(
            self._private_key)

        evp_md = self._backend._lib.EVP_get_digestbyname(
            self._algorithm.name.encode("ascii"))
        assert evp_md != self._backend._ffi.NULL
        pkey_size = self._backend._lib.EVP_PKEY_size(evp_pkey)
        assert pkey_size > 0

        return self._finalize_method(evp_pkey, pkey_size, evp_md)

    def _finalize_pkey_ctx(self, evp_pkey, pkey_size, evp_md):
        pkey_ctx = self._backend._lib.EVP_PKEY_CTX_new(
            evp_pkey, self._backend._ffi.NULL
        )
        assert pkey_ctx != self._backend._ffi.NULL
        pkey_ctx = self._backend._ffi.gc(pkey_ctx,
                                         self._backend._lib.EVP_PKEY_CTX_free)
        res = self._backend._lib.EVP_PKEY_sign_init(pkey_ctx)
        assert res == 1
        res = self._backend._lib.EVP_PKEY_CTX_set_signature_md(
            pkey_ctx, evp_md)
        assert res > 0

        res = self._backend._lib.EVP_PKEY_CTX_set_rsa_padding(
            pkey_ctx, self._padding_enum)
        assert res > 0
        if isinstance(self._padding, PSS):
            res = self._backend._lib.EVP_PKEY_CTX_set_rsa_pss_saltlen(
                pkey_ctx,
                _get_rsa_pss_salt_length(
                    self._padding,
                    self._private_key.key_size,
                    self._hash_ctx.algorithm.digest_size
                )
            )
            assert res > 0

            if self._backend._lib.Cryptography_HAS_MGF1_MD:
                # MGF1 MD is configurable in OpenSSL 1.0.1+
                mgf1_md = self._backend._lib.EVP_get_digestbyname(
                    self._padding._mgf._algorithm.name.encode("ascii"))
                assert mgf1_md != self._backend._ffi.NULL
                res = self._backend._lib.EVP_PKEY_CTX_set_rsa_mgf1_md(
                    pkey_ctx, mgf1_md
                )
                assert res > 0
        data_to_sign = self._hash_ctx.finalize()
        self._hash_ctx = None
        buflen = self._backend._ffi.new("size_t *")
        res = self._backend._lib.EVP_PKEY_sign(
            pkey_ctx,
            self._backend._ffi.NULL,
            buflen,
            data_to_sign,
            len(data_to_sign)
        )
        assert res == 1
        buf = self._backend._ffi.new("unsigned char[]", buflen[0])
        res = self._backend._lib.EVP_PKEY_sign(
            pkey_ctx, buf, buflen, data_to_sign, len(data_to_sign))
        if res != 1:
            errors = self._backend._consume_errors()
            assert errors[0].lib == self._backend._lib.ERR_LIB_RSA
            reason = None
            if (errors[0].reason ==
                    self._backend._lib.RSA_R_DATA_TOO_LARGE_FOR_KEY_SIZE):
                reason = ("Salt length too long for key size. Try using "
                          "MAX_LENGTH instead.")
            elif (errors[0].reason ==
                    self._backend._lib.RSA_R_DIGEST_TOO_BIG_FOR_RSA_KEY):
                reason = "Digest too large for key size. Use a larger key."
            assert reason is not None
            raise ValueError(reason)

        return self._backend._ffi.buffer(buf)[:]

    def _finalize_pkcs1(self, evp_pkey, pkey_size, evp_md):
        sig_buf = self._backend._ffi.new("char[]", pkey_size)
        sig_len = self._backend._ffi.new("unsigned int *")
        res = self._backend._lib.EVP_SignFinal(
            self._hash_ctx._ctx,
            sig_buf,
            sig_len,
            evp_pkey
        )
        self._hash_ctx.finalize()
        self._hash_ctx = None
        if res == 0:
            errors = self._backend._consume_errors()
            assert errors[0].lib == self._backend._lib.ERR_LIB_RSA
            assert (errors[0].reason ==
                    self._backend._lib.RSA_R_DIGEST_TOO_BIG_FOR_RSA_KEY)
            raise ValueError("Digest too large for key size. Use a larger "
                             "key.")

        return self._backend._ffi.buffer(sig_buf)[:sig_len[0]]

    def _finalize_pss(self, evp_pkey, pkey_size, evp_md):
        data_to_sign = self._hash_ctx.finalize()
        self._hash_ctx = None
        padded = self._backend._ffi.new("unsigned char[]", pkey_size)
        rsa_cdata = self._backend._lib.EVP_PKEY_get1_RSA(evp_pkey)
        assert rsa_cdata != self._backend._ffi.NULL
        rsa_cdata = self._backend._ffi.gc(rsa_cdata,
                                          self._backend._lib.RSA_free)
        res = self._backend._lib.RSA_padding_add_PKCS1_PSS(
            rsa_cdata,
            padded,
            data_to_sign,
            evp_md,
            _get_rsa_pss_salt_length(
                self._padding,
                self._private_key.key_size,
                len(data_to_sign)
            )
        )
        if res != 1:
            errors = self._backend._consume_errors()
            assert errors[0].lib == self._backend._lib.ERR_LIB_RSA
            assert (errors[0].reason ==
                    self._backend._lib.RSA_R_DATA_TOO_LARGE_FOR_KEY_SIZE)
            raise ValueError("Salt length too long for key size. Try using "
                             "MAX_LENGTH instead.")

        sig_buf = self._backend._ffi.new("char[]", pkey_size)
        sig_len = self._backend._lib.RSA_private_encrypt(
            pkey_size,
            padded,
            sig_buf,
            rsa_cdata,
            self._backend._lib.RSA_NO_PADDING
        )
        assert sig_len != -1
        return self._backend._ffi.buffer(sig_buf)[:sig_len]


@utils.register_interface(interfaces.AsymmetricVerificationContext)
class _RSAVerificationContext(object):
    def __init__(self, backend, public_key, signature, padding, algorithm):
        self._backend = backend
        self._public_key = public_key
        self._signature = signature

        if not isinstance(padding, interfaces.AsymmetricPadding):
            raise TypeError(
                "Expected provider of interfaces.AsymmetricPadding.")

        if isinstance(padding, PKCS1v15):
            if self._backend._lib.Cryptography_HAS_PKEY_CTX:
                self._verify_method = self._verify_pkey_ctx
                self._padding_enum = self._backend._lib.RSA_PKCS1_PADDING
            else:
                self._verify_method = self._verify_pkcs1
        elif isinstance(padding, PSS):
            if not isinstance(padding._mgf, MGF1):
                raise UnsupportedAlgorithm(
                    "Only MGF1 is supported by this backend.",
                    _Reasons.UNSUPPORTED_MGF
                )

            # Size of key in bytes - 2 is the maximum
            # PSS signature length (salt length is checked later)
            key_size_bytes = int(math.ceil(public_key.key_size / 8.0))
            if key_size_bytes - algorithm.digest_size - 2 < 0:
                raise ValueError(
                    "Digest too large for key size. Check that you have the "
                    "correct key and digest algorithm."
                )

            if not self._backend.mgf1_hash_supported(padding._mgf._algorithm):
                raise UnsupportedAlgorithm(
                    "When OpenSSL is older than 1.0.1 then only SHA1 is "
                    "supported with MGF1.",
                    _Reasons.UNSUPPORTED_HASH
                )

            if self._backend._lib.Cryptography_HAS_PKEY_CTX:
                self._verify_method = self._verify_pkey_ctx
                self._padding_enum = self._backend._lib.RSA_PKCS1_PSS_PADDING
            else:
                self._verify_method = self._verify_pss
        else:
            raise UnsupportedAlgorithm(
                "{0} is not supported by this backend.".format(padding.name),
                _Reasons.UNSUPPORTED_PADDING
            )

        self._padding = padding
        self._algorithm = algorithm
        self._hash_ctx = _HashContext(backend, self._algorithm)

    def update(self, data):
        if self._hash_ctx is None:
            raise AlreadyFinalized("Context has already been finalized.")

        self._hash_ctx.update(data)

    def verify(self):
        if self._hash_ctx is None:
            raise AlreadyFinalized("Context has already been finalized.")

        evp_pkey = self._backend._rsa_public_key_to_evp_pkey(
            self._public_key)

        evp_md = self._backend._lib.EVP_get_digestbyname(
            self._algorithm.name.encode("ascii"))
        assert evp_md != self._backend._ffi.NULL

        self._verify_method(evp_pkey, evp_md)

    def _verify_pkey_ctx(self, evp_pkey, evp_md):
        pkey_ctx = self._backend._lib.EVP_PKEY_CTX_new(
            evp_pkey, self._backend._ffi.NULL
        )
        assert pkey_ctx != self._backend._ffi.NULL
        pkey_ctx = self._backend._ffi.gc(pkey_ctx,
                                         self._backend._lib.EVP_PKEY_CTX_free)
        res = self._backend._lib.EVP_PKEY_verify_init(pkey_ctx)
        assert res == 1
        res = self._backend._lib.EVP_PKEY_CTX_set_signature_md(
            pkey_ctx, evp_md)
        assert res > 0

        res = self._backend._lib.EVP_PKEY_CTX_set_rsa_padding(
            pkey_ctx, self._padding_enum)
        assert res > 0
        if isinstance(self._padding, PSS):
            res = self._backend._lib.EVP_PKEY_CTX_set_rsa_pss_saltlen(
                pkey_ctx,
                _get_rsa_pss_salt_length(
                    self._padding,
                    self._public_key.key_size,
                    self._hash_ctx.algorithm.digest_size
                )
            )
            assert res > 0
            if self._backend._lib.Cryptography_HAS_MGF1_MD:
                # MGF1 MD is configurable in OpenSSL 1.0.1+
                mgf1_md = self._backend._lib.EVP_get_digestbyname(
                    self._padding._mgf._algorithm.name.encode("ascii"))
                assert mgf1_md != self._backend._ffi.NULL
                res = self._backend._lib.EVP_PKEY_CTX_set_rsa_mgf1_md(
                    pkey_ctx, mgf1_md
                )
                assert res > 0

        data_to_verify = self._hash_ctx.finalize()
        self._hash_ctx = None
        res = self._backend._lib.EVP_PKEY_verify(
            pkey_ctx,
            self._signature,
            len(self._signature),
            data_to_verify,
            len(data_to_verify)
        )
        # The previous call can return negative numbers in the event of an
        # error. This is not a signature failure but we need to fail if it
        # occurs.
        assert res >= 0
        if res == 0:
            errors = self._backend._consume_errors()
            assert errors
            raise InvalidSignature

    def _verify_pkcs1(self, evp_pkey, evp_md):
        res = self._backend._lib.EVP_VerifyFinal(
            self._hash_ctx._ctx,
            self._signature,
            len(self._signature),
            evp_pkey
        )
        self._hash_ctx.finalize()
        self._hash_ctx = None
        # The previous call can return negative numbers in the event of an
        # error. This is not a signature failure but we need to fail if it
        # occurs.
        assert res >= 0
        if res == 0:
            errors = self._backend._consume_errors()
            assert errors
            raise InvalidSignature

    def _verify_pss(self, evp_pkey, evp_md):
        pkey_size = self._backend._lib.EVP_PKEY_size(evp_pkey)
        assert pkey_size > 0
        rsa_cdata = self._backend._lib.EVP_PKEY_get1_RSA(evp_pkey)
        assert rsa_cdata != self._backend._ffi.NULL
        rsa_cdata = self._backend._ffi.gc(rsa_cdata,
                                          self._backend._lib.RSA_free)
        buf = self._backend._ffi.new("unsigned char[]", pkey_size)
        res = self._backend._lib.RSA_public_decrypt(
            len(self._signature),
            self._signature,
            buf,
            rsa_cdata,
            self._backend._lib.RSA_NO_PADDING
        )
        if res != pkey_size:
            errors = self._backend._consume_errors()
            assert errors
            raise InvalidSignature

        data_to_verify = self._hash_ctx.finalize()
        self._hash_ctx = None
        res = self._backend._lib.RSA_verify_PKCS1_PSS(
            rsa_cdata,
            data_to_verify,
            evp_md,
            buf,
            _get_rsa_pss_salt_length(
                self._padding,
                self._public_key.key_size,
                len(data_to_verify)
            )
        )
        if res != 1:
            errors = self._backend._consume_errors()
            assert errors
            raise InvalidSignature


@utils.register_interface(interfaces.AsymmetricVerificationContext)
class _DSAVerificationContext(object):
    def __init__(self, backend, public_key, signature, algorithm):
        self._backend = backend
        self._public_key = public_key
        self._signature = signature
        self._algorithm = algorithm

        self._hash_ctx = _HashContext(backend, self._algorithm)

    def update(self, data):
        if self._hash_ctx is None:
            raise AlreadyFinalized("Context has already been finalized.")

        self._hash_ctx.update(data)

    def verify(self):
        if self._hash_ctx is None:
            raise AlreadyFinalized("Context has already been finalized.")

        self._dsa_cdata = self._backend._dsa_cdata_from_public_key(
            self._public_key)
        self._dsa_cdata = self._backend._ffi.gc(self._dsa_cdata,
                                                self._backend._lib.DSA_free)

        data_to_verify = self._hash_ctx.finalize()
        self._hash_ctx = None

        # The first parameter passed to DSA_verify is unused by OpenSSL but
        # must be an integer.
        res = self._backend._lib.DSA_verify(
            0, data_to_verify, len(data_to_verify), self._signature,
            len(self._signature), self._dsa_cdata)

        if res != 1:
            errors = self._backend._consume_errors()
            assert errors
            if res == -1:
                assert errors[0].lib == self._backend._lib.ERR_LIB_ASN1

            raise InvalidSignature


@utils.register_interface(interfaces.AsymmetricSignatureContext)
class _DSASignatureContext(object):
    def __init__(self, backend, private_key, algorithm):
        self._backend = backend
        self._private_key = private_key
        self._algorithm = algorithm
        self._hash_ctx = _HashContext(backend, self._algorithm)
        self._dsa_cdata = self._backend._dsa_cdata_from_private_key(
            self._private_key)
        self._dsa_cdata = self._backend._ffi.gc(self._dsa_cdata,
                                                self._backend._lib.DSA_free)

    def update(self, data):
        if self._hash_ctx is None:
            raise AlreadyFinalized("Context has already been finalized.")

        self._hash_ctx.update(data)

    def finalize(self):
        if self._hash_ctx is None:
            raise AlreadyFinalized("Context has already been finalized.")

        data_to_sign = self._hash_ctx.finalize()
        self._hash_ctx = None
        sig_buf_len = self._backend._lib.DSA_size(self._dsa_cdata)
        sig_buf = self._backend._ffi.new("unsigned char[]", sig_buf_len)
        buflen = self._backend._ffi.new("unsigned int *")

        # The first parameter passed to DSA_sign is unused by OpenSSL but
        # must be an integer.
        res = self._backend._lib.DSA_sign(
            0, data_to_sign, len(data_to_sign), sig_buf,
            buflen, self._dsa_cdata)
        assert res == 1
        assert buflen[0]

        return self._backend._ffi.buffer(sig_buf)[:buflen[0]]


@utils.register_interface(interfaces.CMACContext)
class _CMACContext(object):
    def __init__(self, backend, algorithm, ctx=None):
        if not backend.cmac_algorithm_supported(algorithm):
            raise UnsupportedAlgorithm("This backend does not support CMAC.",
                                       _Reasons.UNSUPPORTED_CIPHER)

        self._backend = backend
        self._key = algorithm.key
        self._algorithm = algorithm
        self._output_length = algorithm.block_size // 8

        if ctx is None:
            registry = self._backend._cipher_registry
            adapter = registry[type(algorithm), CBC]

            evp_cipher = adapter(self._backend, algorithm, CBC)

            ctx = self._backend._lib.CMAC_CTX_new()

            assert ctx != self._backend._ffi.NULL
            ctx = self._backend._ffi.gc(ctx, self._backend._lib.CMAC_CTX_free)

            self._backend._lib.CMAC_Init(
                ctx, self._key, len(self._key),
                evp_cipher, self._backend._ffi.NULL
            )

        self._ctx = ctx

    def update(self, data):
        res = self._backend._lib.CMAC_Update(self._ctx, data, len(data))
        assert res == 1

    def finalize(self):
        buf = self._backend._ffi.new("unsigned char[]", self._output_length)
        length = self._backend._ffi.new("size_t *", self._output_length)
        res = self._backend._lib.CMAC_Final(
            self._ctx, buf, length
        )
        assert res == 1

        self._ctx = None

        return self._backend._ffi.buffer(buf)[:]

    def copy(self):
        copied_ctx = self._backend._lib.CMAC_CTX_new()
        copied_ctx = self._backend._ffi.gc(
            copied_ctx, self._backend._lib.CMAC_CTX_free
        )
        res = self._backend._lib.CMAC_CTX_copy(
            copied_ctx, self._ctx
        )
        assert res == 1
        return _CMACContext(
            self._backend, self._algorithm, ctx=copied_ctx
        )


backend = Backend()

########NEW FILE########
__FILENAME__ = binding
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import platform
import sys

from cryptography.hazmat.bindings.utils import build_ffi


class Binding(object):
    """
    CommonCrypto API wrapper.
    """
    _module_prefix = "cryptography.hazmat.bindings.commoncrypto."
    _modules = [
        "common_digest",
        "common_hmac",
        "common_key_derivation",
        "common_cryptor",
    ]

    ffi = None
    lib = None

    def __init__(self):
        self._ensure_ffi_initialized()

    @classmethod
    def _ensure_ffi_initialized(cls):
        if cls.ffi is not None and cls.lib is not None:
            return

        cls.ffi, cls.lib = build_ffi(
            module_prefix=cls._module_prefix,
            modules=cls._modules,
        )

    @classmethod
    def is_available(cls):
        return sys.platform == "darwin" and list(map(
            int, platform.mac_ver()[0].split("."))) >= [10, 8, 0]

########NEW FILE########
__FILENAME__ = common_cryptor
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <CommonCrypto/CommonCryptor.h>
"""

TYPES = """
enum {
    kCCAlgorithmAES128 = 0,
    kCCAlgorithmDES,
    kCCAlgorithm3DES,
    kCCAlgorithmCAST,
    kCCAlgorithmRC4,
    kCCAlgorithmRC2,
    kCCAlgorithmBlowfish
};
typedef uint32_t CCAlgorithm;
enum {
    kCCSuccess = 0,
    kCCParamError = -4300,
    kCCBufferTooSmall = -4301,
    kCCMemoryFailure = -4302,
    kCCAlignmentError = -4303,
    kCCDecodeError = -4304,
    kCCUnimplemented = -4305
};
typedef int32_t CCCryptorStatus;
typedef uint32_t CCOptions;
enum {
    kCCEncrypt = 0,
    kCCDecrypt,
};
typedef uint32_t CCOperation;
typedef ... *CCCryptorRef;

enum {
    kCCModeOptionCTR_LE = 0x0001,
    kCCModeOptionCTR_BE = 0x0002
};

typedef uint32_t CCModeOptions;

enum {
    kCCModeECB = 1,
    kCCModeCBC = 2,
    kCCModeCFB = 3,
    kCCModeCTR = 4,
    kCCModeF8 = 5,
    kCCModeLRW = 6,
    kCCModeOFB = 7,
    kCCModeXTS = 8,
    kCCModeRC4 = 9,
    kCCModeCFB8 = 10,
    kCCModeGCM = 11
};
typedef uint32_t CCMode;
enum {
    ccNoPadding = 0,
    ccPKCS7Padding = 1,
};
typedef uint32_t CCPadding;
"""

FUNCTIONS = """
CCCryptorStatus CCCryptorCreateWithMode(CCOperation, CCMode, CCAlgorithm,
                                        CCPadding, const void *, const void *,
                                        size_t, const void *, size_t, int,
                                        CCModeOptions, CCCryptorRef *);
CCCryptorStatus CCCryptorCreate(CCOperation, CCAlgorithm, CCOptions,
                                const void *, size_t, const void *,
                                CCCryptorRef *);
CCCryptorStatus CCCryptorUpdate(CCCryptorRef, const void *, size_t, void *,
                                size_t, size_t *);
CCCryptorStatus CCCryptorFinal(CCCryptorRef, void *, size_t, size_t *);
CCCryptorStatus CCCryptorRelease(CCCryptorRef);

CCCryptorStatus CCCryptorGCMAddIV(CCCryptorRef, const void *, size_t);
CCCryptorStatus CCCryptorGCMAddAAD(CCCryptorRef, const void *, size_t);
CCCryptorStatus CCCryptorGCMEncrypt(CCCryptorRef, const void *, size_t,
                                    void *);
CCCryptorStatus CCCryptorGCMDecrypt(CCCryptorRef, const void *, size_t,
                                    void *);
CCCryptorStatus CCCryptorGCMFinal(CCCryptorRef, const void *, size_t *);
CCCryptorStatus CCCryptorGCMReset(CCCryptorRef);
"""

MACROS = """
"""

CUSTOMIZATIONS = """
// Not defined in the public header
enum {
    kCCModeGCM = 11
};
"""

CONDITIONAL_NAMES = {}

########NEW FILE########
__FILENAME__ = common_digest
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <CommonCrypto/CommonDigest.h>
"""

TYPES = """
typedef uint32_t CC_LONG;
typedef uint64_t CC_LONG64;
typedef struct CC_MD5state_st {
    ...;
} CC_MD5_CTX;
typedef struct CC_SHA1state_st {
    ...;
} CC_SHA1_CTX;
typedef struct CC_SHA256state_st {
    ...;
} CC_SHA256_CTX;
typedef struct CC_SHA512state_st {
    ...;
} CC_SHA512_CTX;
"""

FUNCTIONS = """
int CC_MD5_Init(CC_MD5_CTX *);
int CC_MD5_Update(CC_MD5_CTX *, const void *, CC_LONG);
int CC_MD5_Final(unsigned char *, CC_MD5_CTX *);

int CC_SHA1_Init(CC_SHA1_CTX *);
int CC_SHA1_Update(CC_SHA1_CTX *, const void *, CC_LONG);
int CC_SHA1_Final(unsigned char *, CC_SHA1_CTX *);

int CC_SHA224_Init(CC_SHA256_CTX *);
int CC_SHA224_Update(CC_SHA256_CTX *, const void *, CC_LONG);
int CC_SHA224_Final(unsigned char *, CC_SHA256_CTX *);

int CC_SHA256_Init(CC_SHA256_CTX *);
int CC_SHA256_Update(CC_SHA256_CTX *, const void *, CC_LONG);
int CC_SHA256_Final(unsigned char *, CC_SHA256_CTX *);

int CC_SHA384_Init(CC_SHA512_CTX *);
int CC_SHA384_Update(CC_SHA512_CTX *, const void *, CC_LONG);
int CC_SHA384_Final(unsigned char *, CC_SHA512_CTX *);

int CC_SHA512_Init(CC_SHA512_CTX *);
int CC_SHA512_Update(CC_SHA512_CTX *, const void *, CC_LONG);
int CC_SHA512_Final(unsigned char *, CC_SHA512_CTX *);
"""

MACROS = """
"""

CUSTOMIZATIONS = """
"""

CONDITIONAL_NAMES = {}

########NEW FILE########
__FILENAME__ = common_hmac
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <CommonCrypto/CommonHMAC.h>
"""

TYPES = """
typedef struct {
    ...;
} CCHmacContext;
enum {
    kCCHmacAlgSHA1,
    kCCHmacAlgMD5,
    kCCHmacAlgSHA256,
    kCCHmacAlgSHA384,
    kCCHmacAlgSHA512,
    kCCHmacAlgSHA224
};
typedef uint32_t CCHmacAlgorithm;
"""

FUNCTIONS = """
void CCHmacInit(CCHmacContext *, CCHmacAlgorithm, const void *, size_t);
void CCHmacUpdate(CCHmacContext *, const void *, size_t);
void CCHmacFinal(CCHmacContext *, void *);

"""

MACROS = """
"""

CUSTOMIZATIONS = """
"""

CONDITIONAL_NAMES = {}

########NEW FILE########
__FILENAME__ = common_key_derivation
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <CommonCrypto/CommonKeyDerivation.h>
"""

TYPES = """
enum {
    kCCPBKDF2 = 2,
};
typedef uint32_t CCPBKDFAlgorithm;
enum {
    kCCPRFHmacAlgSHA1 = 1,
    kCCPRFHmacAlgSHA224 = 2,
    kCCPRFHmacAlgSHA256 = 3,
    kCCPRFHmacAlgSHA384 = 4,
    kCCPRFHmacAlgSHA512 = 5,
};
typedef uint32_t CCPseudoRandomAlgorithm;
typedef unsigned int uint;
"""

FUNCTIONS = """
int CCKeyDerivationPBKDF(CCPBKDFAlgorithm, const char *, size_t,
                         const uint8_t *, size_t, CCPseudoRandomAlgorithm,
                         uint, uint8_t *, size_t);
uint CCCalibratePBKDF(CCPBKDFAlgorithm, size_t, size_t,
                      CCPseudoRandomAlgorithm, size_t, uint32_t);
"""

MACROS = """
"""

CUSTOMIZATIONS = """
"""

CONDITIONAL_NAMES = {}

########NEW FILE########
__FILENAME__ = aes
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/aes.h>
"""

TYPES = """
static const int Cryptography_HAS_AES_WRAP;

struct aes_key_st {
    ...;
};
typedef struct aes_key_st AES_KEY;
"""

FUNCTIONS = """
int AES_set_encrypt_key(const unsigned char *, const int, AES_KEY *);
int AES_set_decrypt_key(const unsigned char *, const int, AES_KEY *);
/* The ctr128_encrypt function is only useful in 0.9.8. You should use EVP for
   this in 1.0.0+. */
void AES_ctr128_encrypt(const unsigned char *, unsigned char *,
                        const unsigned long, const AES_KEY *,
                        unsigned char[], unsigned char[], unsigned int *);

"""

MACROS = """
/* these can be moved back to FUNCTIONS once we drop support for 0.9.8h.
   This should be when we drop RHEL/CentOS 5, which is on 0.9.8e. */
int AES_wrap_key(AES_KEY *, const unsigned char *, unsigned char *,
                 const unsigned char *, unsigned int);
int AES_unwrap_key(AES_KEY *, const unsigned char *, unsigned char *,
                   const unsigned char *, unsigned int);
"""

CUSTOMIZATIONS = """
// OpenSSL 0.9.8h+
#if OPENSSL_VERSION_NUMBER >= 0x0090808fL
static const long Cryptography_HAS_AES_WRAP = 1;
#else
static const long Cryptography_HAS_AES_WRAP = 0;
int (*AES_wrap_key)(AES_KEY *, const unsigned char *, unsigned char *,
                    const unsigned char *, unsigned int) = NULL;
int (*AES_unwrap_key)(AES_KEY *, const unsigned char *, unsigned char *,
                      const unsigned char *, unsigned int) = NULL;
#endif

"""

CONDITIONAL_NAMES = {
    "Cryptography_HAS_AES_WRAP": [
        "AES_wrap_key",
        "AES_unwrap_key",
    ],
}

########NEW FILE########
__FILENAME__ = asn1
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/asn1.h>
"""

TYPES = """
/*
 * TODO: This typedef is wrong.
 *
 * This is due to limitations of cffi.
 * See https://bitbucket.org/cffi/cffi/issue/69
 *
 * For another possible work-around (not used here because it involves more
 * complicated use of the cffi API which falls outside the general pattern used
 * by this package), see
 * http://paste.pound-python.org/show/iJcTUMkKeBeS6yXpZWUU/
 *
 * The work-around used here is to just be sure to declare a type that is at
 * least as large as the real type.  Maciej explains:
 *
 * <fijal> I think you want to declare your value too large (e.g. long)
 * <fijal> that way you'll never pass garbage
 */
typedef intptr_t time_t;

typedef int ASN1_BOOLEAN;
typedef ... ASN1_INTEGER;

struct asn1_string_st {
    int length;
    int type;
    unsigned char *data;
    long flags;
};

typedef struct asn1_string_st ASN1_OCTET_STRING;
typedef struct asn1_string_st ASN1_IA5STRING;
typedef ... ASN1_OBJECT;
typedef ... ASN1_STRING;
typedef ... ASN1_TYPE;
typedef ... ASN1_GENERALIZEDTIME;
typedef ... ASN1_ENUMERATED;
typedef ... ASN1_ITEM;
typedef ... ASN1_VALUE;

typedef struct {
    ...;
} ASN1_TIME;
typedef ... ASN1_ITEM_EXP;

typedef ... ASN1_UTCTIME;

static const int V_ASN1_GENERALIZEDTIME;

static const int MBSTRING_UTF8;
"""

FUNCTIONS = """
ASN1_OBJECT *ASN1_OBJECT_new(void);
void ASN1_OBJECT_free(ASN1_OBJECT *);

/*  ASN1 OBJECT IDENTIFIER */
ASN1_OBJECT *d2i_ASN1_OBJECT(ASN1_OBJECT **, const unsigned char **, long);
int i2d_ASN1_OBJECT(ASN1_OBJECT *, unsigned char **);

/*  ASN1 STRING */
ASN1_STRING *ASN1_STRING_new(void);
ASN1_STRING *ASN1_STRING_type_new(int);
void ASN1_STRING_free(ASN1_STRING *);
unsigned char *ASN1_STRING_data(ASN1_STRING *);
int ASN1_STRING_set(ASN1_STRING *, const void *, int);
int ASN1_STRING_type(ASN1_STRING *);
int ASN1_STRING_to_UTF8(unsigned char **, ASN1_STRING *);

/*  ASN1 OCTET STRING */
ASN1_OCTET_STRING *ASN1_OCTET_STRING_new(void);
void ASN1_OCTET_STRING_free(ASN1_OCTET_STRING *);
int ASN1_OCTET_STRING_set(ASN1_OCTET_STRING *, const unsigned char *, int);

/*  ASN1 INTEGER */
ASN1_INTEGER *ASN1_INTEGER_new(void);
void ASN1_INTEGER_free(ASN1_INTEGER *);
int ASN1_INTEGER_set(ASN1_INTEGER *, long);
int i2a_ASN1_INTEGER(BIO *, ASN1_INTEGER *);

/*  ASN1 TIME */
ASN1_TIME *ASN1_TIME_new(void);
void ASN1_TIME_free(ASN1_TIME *);
ASN1_GENERALIZEDTIME *ASN1_TIME_to_generalizedtime(ASN1_TIME *,
                                                   ASN1_GENERALIZEDTIME **);

/*  ASN1 UTCTIME */
int ASN1_UTCTIME_cmp_time_t(const ASN1_UTCTIME *, time_t);

/*  ASN1 GENERALIZEDTIME */
int ASN1_GENERALIZEDTIME_set_string(ASN1_GENERALIZEDTIME *, const char *);
void ASN1_GENERALIZEDTIME_free(ASN1_GENERALIZEDTIME *);

/*  ASN1 ENUMERATED */
ASN1_ENUMERATED *ASN1_ENUMERATED_new(void);
void ASN1_ENUMERATED_free(ASN1_ENUMERATED *);
int ASN1_ENUMERATED_set(ASN1_ENUMERATED *, long);

ASN1_VALUE *ASN1_item_d2i(ASN1_VALUE **, const unsigned char **, long,
                          const ASN1_ITEM *);
"""

MACROS = """
ASN1_TIME *M_ASN1_TIME_dup(void *);
const ASN1_ITEM *ASN1_ITEM_ptr(ASN1_ITEM_EXP *);

/* These aren't macros these arguments are all const X on openssl > 1.0.x */

int ASN1_STRING_length(ASN1_STRING *);
ASN1_STRING *ASN1_STRING_dup(ASN1_STRING *);
int ASN1_STRING_cmp(ASN1_STRING *, ASN1_STRING *);

ASN1_OCTET_STRING *ASN1_OCTET_STRING_dup(ASN1_OCTET_STRING *);
int ASN1_OCTET_STRING_cmp(ASN1_OCTET_STRING *, ASN1_OCTET_STRING *);

ASN1_INTEGER *ASN1_INTEGER_dup(ASN1_INTEGER *);
int ASN1_INTEGER_cmp(ASN1_INTEGER *, ASN1_INTEGER *);
long ASN1_INTEGER_get(ASN1_INTEGER *);

BIGNUM *ASN1_INTEGER_to_BN(ASN1_INTEGER *, BIGNUM *);
ASN1_INTEGER *BN_to_ASN1_INTEGER(BIGNUM *, ASN1_INTEGER *);

/* These isn't a macro the arg is const on openssl 1.0.2+ */
int ASN1_GENERALIZEDTIME_check(ASN1_GENERALIZEDTIME *);
"""

CUSTOMIZATIONS = """
"""

CONDITIONAL_NAMES = {}

########NEW FILE########
__FILENAME__ = bignum
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/bn.h>
"""

TYPES = """
typedef ... BN_CTX;
typedef ... BIGNUM;
/*
 * TODO: This typedef is wrong.
 *
 * This is due to limitations of cffi.
 * See https://bitbucket.org/cffi/cffi/issue/69
 *
 * For another possible work-around (not used here because it involves more
 * complicated use of the cffi API which falls outside the general pattern used
 * by this package), see
 * http://paste.pound-python.org/show/iJcTUMkKeBeS6yXpZWUU/
 *
 * The work-around used here is to just be sure to declare a type that is at
 * least as large as the real type.  Maciej explains:
 *
 * <fijal> I think you want to declare your value too large (e.g. long)
 * <fijal> that way you'll never pass garbage
 */
typedef uintptr_t BN_ULONG;
"""

FUNCTIONS = """
BIGNUM *BN_new(void);
void BN_free(BIGNUM *);

BN_CTX *BN_CTX_new(void);
void BN_CTX_free(BN_CTX *);

void BN_CTX_start(BN_CTX *);
BIGNUM *BN_CTX_get(BN_CTX *);
void BN_CTX_end(BN_CTX *);

BIGNUM *BN_copy(BIGNUM *, const BIGNUM *);
BIGNUM *BN_dup(const BIGNUM *);

int BN_set_word(BIGNUM *, BN_ULONG);
BN_ULONG BN_get_word(const BIGNUM *);

const BIGNUM *BN_value_one(void);

char *BN_bn2hex(const BIGNUM *);
int BN_hex2bn(BIGNUM **, const char *);
int BN_dec2bn(BIGNUM **, const char *);

int BN_bn2bin(const BIGNUM *, unsigned char *);
BIGNUM *BN_bin2bn(const unsigned char *, int, BIGNUM *);

int BN_num_bits(const BIGNUM *);

int BN_cmp(const BIGNUM *, const BIGNUM *);
int BN_add(BIGNUM *, const BIGNUM *, const BIGNUM *);
int BN_sub(BIGNUM *, const BIGNUM *, const BIGNUM *);
int BN_mul(BIGNUM *, const BIGNUM *, const BIGNUM *, BN_CTX *);
int BN_sqr(BIGNUM *, const BIGNUM *, BN_CTX *);
int BN_div(BIGNUM *, BIGNUM *, const BIGNUM *, const BIGNUM *, BN_CTX *);
int BN_nnmod(BIGNUM *, const BIGNUM *, const BIGNUM *, BN_CTX *);
int BN_mod_add(BIGNUM *, const BIGNUM *, const BIGNUM *, const BIGNUM *,
               BN_CTX *);
int BN_mod_sub(BIGNUM *, const BIGNUM *, const BIGNUM *, const BIGNUM *,
               BN_CTX *);
int BN_mod_mul(BIGNUM *, const BIGNUM *, const BIGNUM *, const BIGNUM *,
               BN_CTX *);
int BN_mod_sqr(BIGNUM *, const BIGNUM *, const BIGNUM *, BN_CTX *);
int BN_exp(BIGNUM *, const BIGNUM *, const BIGNUM *, BN_CTX *);
int BN_mod_exp(BIGNUM *, const BIGNUM *, const BIGNUM *, const BIGNUM *,
               BN_CTX *);
int BN_gcd(BIGNUM *, const BIGNUM *, const BIGNUM *, BN_CTX *);
BIGNUM *BN_mod_inverse(BIGNUM *, const BIGNUM *, const BIGNUM *, BN_CTX *);

int BN_set_bit(BIGNUM *, int);
int BN_clear_bit(BIGNUM *, int);

int BN_is_bit_set(const BIGNUM *, int);

int BN_mask_bits(BIGNUM *, int);
"""

MACROS = """
int BN_zero(BIGNUM *);
int BN_one(BIGNUM *);
int BN_mod(BIGNUM *, const BIGNUM *, const BIGNUM *, BN_CTX *);

int BN_lshift(BIGNUM *, const BIGNUM *, int);
int BN_lshift1(BIGNUM *, BIGNUM *);

int BN_rshift(BIGNUM *, BIGNUM *, int);
int BN_rshift1(BIGNUM *, BIGNUM *);
"""

CUSTOMIZATIONS = """
"""

CONDITIONAL_NAMES = {}

########NEW FILE########
__FILENAME__ = binding
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import sys
import threading

from cryptography.hazmat.bindings.utils import build_ffi


_OSX_PRE_INCLUDE = """
#ifdef __APPLE__
#include <AvailabilityMacros.h>
#define __ORIG_DEPRECATED_IN_MAC_OS_X_VERSION_10_7_AND_LATER \
    DEPRECATED_IN_MAC_OS_X_VERSION_10_7_AND_LATER
#undef DEPRECATED_IN_MAC_OS_X_VERSION_10_7_AND_LATER
#define DEPRECATED_IN_MAC_OS_X_VERSION_10_7_AND_LATER
#endif
"""

_OSX_POST_INCLUDE = """
#ifdef __APPLE__
#undef DEPRECATED_IN_MAC_OS_X_VERSION_10_7_AND_LATER
#define DEPRECATED_IN_MAC_OS_X_VERSION_10_7_AND_LATER \
    __ORIG_DEPRECATED_IN_MAC_OS_X_VERSION_10_7_AND_LATER
#endif
"""


class Binding(object):
    """
    OpenSSL API wrapper.
    """
    _module_prefix = "cryptography.hazmat.bindings.openssl."
    _modules = [
        "aes",
        "asn1",
        "bignum",
        "bio",
        "cmac",
        "cms",
        "conf",
        "crypto",
        "dh",
        "dsa",
        "ec",
        "ecdh",
        "ecdsa",
        "engine",
        "err",
        "evp",
        "hmac",
        "nid",
        "objects",
        "opensslv",
        "osrandom_engine",
        "pem",
        "pkcs7",
        "pkcs12",
        "rand",
        "rsa",
        "ssl",
        "x509",
        "x509name",
        "x509v3",
    ]

    _locks = None
    _lock_cb_handle = None
    _lock_init_lock = threading.Lock()

    ffi = None
    lib = None

    def __init__(self):
        self._ensure_ffi_initialized()

    @classmethod
    def _ensure_ffi_initialized(cls):
        if cls.ffi is not None and cls.lib is not None:
            return

        # OpenSSL goes by a different library name on different operating
        # systems.
        if sys.platform != "win32":
            libraries = ["crypto", "ssl"]
        else:  # pragma: no cover
            libraries = ["libeay32", "ssleay32", "advapi32"]

        cls.ffi, cls.lib = build_ffi(
            module_prefix=cls._module_prefix,
            modules=cls._modules,
            pre_include=_OSX_PRE_INCLUDE,
            post_include=_OSX_POST_INCLUDE,
            libraries=libraries,
        )
        res = cls.lib.Cryptography_add_osrandom_engine()
        assert res != 0

    @classmethod
    def is_available(cls):
        # For now, OpenSSL is considered our "default" binding, so we treat it
        # as always available.
        return True

    @classmethod
    def init_static_locks(cls):
        with cls._lock_init_lock:
            cls._ensure_ffi_initialized()

            if not cls._lock_cb_handle:
                cls._lock_cb_handle = cls.ffi.callback(
                    "void(int, int, const char *, int)",
                    cls._lock_cb
                )

            # Use Python's implementation if available, importing _ssl triggers
            # the setup for this.
            __import__("_ssl")

            if cls.lib.CRYPTO_get_locking_callback() != cls.ffi.NULL:
                return

            # If nothing else has setup a locking callback already, we set up
            # our own
            num_locks = cls.lib.CRYPTO_num_locks()
            cls._locks = [threading.Lock() for n in range(num_locks)]

            cls.lib.CRYPTO_set_locking_callback(cls._lock_cb_handle)

    @classmethod
    def _lock_cb(cls, mode, n, file, line):
        lock = cls._locks[n]

        if mode & cls.lib.CRYPTO_LOCK:
            lock.acquire()
        elif mode & cls.lib.CRYPTO_UNLOCK:
            lock.release()
        else:
            raise RuntimeError(
                "Unknown lock mode {0}: lock={1}, file={2}, line={3}.".format(
                    mode, n, file, line
                )
            )

########NEW FILE########
__FILENAME__ = bio
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/bio.h>
"""

TYPES = """
typedef struct bio_st BIO;
typedef void bio_info_cb(BIO *, int, const char *, int, long, long);
struct bio_method_st {
    int type;
    const char *name;
    int (*bwrite)(BIO *, const char *, int);
    int (*bread)(BIO *, char *, int);
    int (*bputs)(BIO *, const char *);
    int (*bgets)(BIO *, char*, int);
    long (*ctrl)(BIO *, int, long, void *);
    int (*create)(BIO *);
    int (*destroy)(BIO *);
    long (*callback_ctrl)(BIO *, int, bio_info_cb *);
    ...;
};
typedef struct bio_method_st BIO_METHOD;
struct bio_st {
    BIO_METHOD *method;
    long (*callback)(struct bio_st*, int, const char*, int, long, long);
    char *cb_arg;
    int init;
    int shutdown;
    int flags;
    int retry_reason;
    int num;
    void *ptr;
    struct bio_st *next_bio;
    struct bio_st *prev_bio;
    int references;
    unsigned long num_read;
    unsigned long num_write;
    ...;
};
typedef ... BUF_MEM;

static const int BIO_TYPE_MEM;
static const int BIO_TYPE_FILE;
static const int BIO_TYPE_FD;
static const int BIO_TYPE_SOCKET;
static const int BIO_TYPE_CONNECT;
static const int BIO_TYPE_ACCEPT;
static const int BIO_TYPE_NULL;
static const int BIO_CLOSE;
static const int BIO_NOCLOSE;
static const int BIO_TYPE_SOURCE_SINK;
static const int BIO_CTRL_RESET;
static const int BIO_CTRL_EOF;
static const int BIO_CTRL_SET;
static const int BIO_CTRL_SET_CLOSE;
static const int BIO_CTRL_FLUSH;
static const int BIO_CTRL_DUP;
static const int BIO_CTRL_GET_CLOSE;
static const int BIO_CTRL_INFO;
static const int BIO_CTRL_GET;
static const int BIO_CTRL_PENDING;
static const int BIO_CTRL_WPENDING;
static const int BIO_C_FILE_SEEK;
static const int BIO_C_FILE_TELL;
static const int BIO_TYPE_NONE;
static const int BIO_TYPE_PROXY_CLIENT;
static const int BIO_TYPE_PROXY_SERVER;
static const int BIO_TYPE_NBIO_TEST;
static const int BIO_TYPE_BER;
static const int BIO_TYPE_BIO;
static const int BIO_TYPE_DESCRIPTOR;
static const int BIO_FLAGS_READ;
static const int BIO_FLAGS_WRITE;
static const int BIO_FLAGS_IO_SPECIAL;
static const int BIO_FLAGS_RWS;
static const int BIO_FLAGS_SHOULD_RETRY;
static const int BIO_TYPE_NULL_FILTER;
static const int BIO_TYPE_SSL;
static const int BIO_TYPE_MD;
static const int BIO_TYPE_BUFFER;
static const int BIO_TYPE_CIPHER;
static const int BIO_TYPE_BASE64;
static const int BIO_TYPE_FILTER;
"""

FUNCTIONS = """
BIO* BIO_new(BIO_METHOD *);
int BIO_set(BIO *, BIO_METHOD *);
int BIO_free(BIO *);
void BIO_vfree(BIO *);
void BIO_free_all(BIO *);
BIO *BIO_push(BIO *, BIO *);
BIO *BIO_pop(BIO *);
BIO *BIO_next(BIO *);
BIO *BIO_find_type(BIO *, int);
BIO_METHOD *BIO_s_mem(void);
BIO *BIO_new_mem_buf(void *, int);
BIO_METHOD *BIO_s_file(void);
BIO *BIO_new_file(const char *, const char *);
BIO *BIO_new_fp(FILE *, int);
BIO_METHOD *BIO_s_fd(void);
BIO *BIO_new_fd(int, int);
BIO_METHOD *BIO_s_socket(void);
BIO *BIO_new_socket(int, int);
BIO_METHOD *BIO_s_null(void);
long BIO_ctrl(BIO *, int, long, void *);
long BIO_callback_ctrl(
    BIO *,
    int,
    void (*)(struct bio_st *, int, const char *, int, long, long)
);
char *BIO_ptr_ctrl(BIO *, int, long);
long BIO_int_ctrl(BIO *, int, long, int);
size_t BIO_ctrl_pending(BIO *);
size_t BIO_ctrl_wpending(BIO *);
int BIO_read(BIO *, void *, int);
int BIO_gets(BIO *, char *, int);
int BIO_write(BIO *, const void *, int);
int BIO_puts(BIO *, const char *);
BIO_METHOD *BIO_f_null(void);
BIO_METHOD *BIO_f_buffer(void);
"""

MACROS = """
long BIO_set_fd(BIO *, long, int);
long BIO_get_fd(BIO *, char *);
long BIO_set_mem_eof_return(BIO *, int);
long BIO_get_mem_data(BIO *, char **);
long BIO_set_mem_buf(BIO *, BUF_MEM *, int);
long BIO_get_mem_ptr(BIO *, BUF_MEM **);
long BIO_set_fp(BIO *, FILE *, int);
long BIO_get_fp(BIO *, FILE **);
long BIO_read_filename(BIO *, char *);
long BIO_write_filename(BIO *, char *);
long BIO_append_filename(BIO *, char *);
long BIO_rw_filename(BIO *, char *);
int BIO_should_read(BIO *);
int BIO_should_write(BIO *);
int BIO_should_io_special(BIO *);
int BIO_retry_type(BIO *);
int BIO_should_retry(BIO *);
int BIO_reset(BIO *);
int BIO_seek(BIO *, int);
int BIO_tell(BIO *);
int BIO_flush(BIO *);
int BIO_eof(BIO *);
int BIO_set_close(BIO *,long);
int BIO_get_close(BIO *);
int BIO_pending(BIO *);
int BIO_wpending(BIO *);
int BIO_get_info_callback(BIO *, bio_info_cb **);
int BIO_set_info_callback(BIO *, bio_info_cb *);
long BIO_get_buffer_num_lines(BIO *);
long BIO_set_read_buffer_size(BIO *, long);
long BIO_set_write_buffer_size(BIO *, long);
long BIO_set_buffer_size(BIO *, long);
long BIO_set_buffer_read_data(BIO *, void *, long);

/* The following was a macro in 0.9.8e. Once we drop support for RHEL/CentOS 5
   we should move this back to FUNCTIONS. */
int BIO_method_type(const BIO *);
"""

CUSTOMIZATIONS = """
"""

CONDITIONAL_NAMES = {}

########NEW FILE########
__FILENAME__ = cmac
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#if OPENSSL_VERSION_NUMBER >= 0x10001000L
#include <openssl/cmac.h>
#endif
"""

TYPES = """
static const int Cryptography_HAS_CMAC;
typedef ... CMAC_CTX;
"""

FUNCTIONS = """
"""

MACROS = """
CMAC_CTX *CMAC_CTX_new(void);
int CMAC_Init(CMAC_CTX *, const void *, size_t, const EVP_CIPHER *, ENGINE *);
int CMAC_Update(CMAC_CTX *, const void *, size_t);
int CMAC_Final(CMAC_CTX *, unsigned char *, size_t *);
int CMAC_CTX_copy(CMAC_CTX *, const CMAC_CTX *);
void CMAC_CTX_free(CMAC_CTX *);
"""

CUSTOMIZATIONS = """
#if OPENSSL_VERSION_NUMBER < 0x10001000L

static const long Cryptography_HAS_CMAC = 0;
typedef void CMAC_CTX;
CMAC_CTX *(*CMAC_CTX_new)(void) = NULL;
int (*CMAC_Init)(CMAC_CTX *, const void *, size_t, const EVP_CIPHER *,
    ENGINE *) = NULL;
int (*CMAC_Update)(CMAC_CTX *, const void *, size_t) = NULL;
int (*CMAC_Final)(CMAC_CTX *, unsigned char *, size_t *) = NULL;
int (*CMAC_CTX_copy)(CMAC_CTX *, const CMAC_CTX *) = NULL;
void (*CMAC_CTX_free)(CMAC_CTX *) = NULL;
#else
static const long Cryptography_HAS_CMAC = 1;
#endif
"""

CONDITIONAL_NAMES = {
    "Cryptography_HAS_CMAC": [
        "CMAC_CTX_new",
        "CMAC_Init",
        "CMAC_Update",
        "CMAC_Final",
        "CMAC_CTX_copy",
        "CMAC_CTX_free",
    ],
}

########NEW FILE########
__FILENAME__ = cms
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#if !defined(OPENSSL_NO_CMS) && OPENSSL_VERSION_NUMBER >= 0x0090808fL
// The next define should really be in the OpenSSL header, but it is missing.
// Failing to include this on Windows causes compilation failures.
#if defined(OPENSSL_SYS_WINDOWS)
#include <windows.h>
#endif
#include <openssl/cms.h>
#endif
"""

TYPES = """
static const long Cryptography_HAS_CMS;

typedef ... CMS_ContentInfo;
typedef ... CMS_SignerInfo;
typedef ... CMS_CertificateChoices;
typedef ... CMS_RevocationInfoChoice;
typedef ... CMS_RecipientInfo;
typedef ... CMS_ReceiptRequest;
typedef ... CMS_Receipt;
"""

FUNCTIONS = """
"""

MACROS = """
BIO *BIO_new_CMS(BIO *, CMS_ContentInfo *);
int i2d_CMS_bio_stream(BIO *, CMS_ContentInfo *, BIO *, int);
int PEM_write_bio_CMS_stream(BIO *, CMS_ContentInfo *, BIO *, int);
int CMS_final(CMS_ContentInfo *, BIO *, BIO *, unsigned int);
CMS_ContentInfo *CMS_sign(X509 *, EVP_PKEY *, Cryptography_STACK_OF_X509 *,
                          BIO *, unsigned int);
int CMS_verify(CMS_ContentInfo *, Cryptography_STACK_OF_X509 *, X509_STORE *,
               BIO *, BIO *, unsigned int);
CMS_ContentInfo *CMS_encrypt(Cryptography_STACK_OF_X509 *, BIO *,
                             const EVP_CIPHER *, unsigned int);
int CMS_decrypt(CMS_ContentInfo *, EVP_PKEY *, X509 *, BIO *, BIO *,
                unsigned int);
CMS_SignerInfo *CMS_add1_signer(CMS_ContentInfo *, X509 *, EVP_PKEY *,
                                const EVP_MD *, unsigned int);
"""

CUSTOMIZATIONS = """
#if !defined(OPENSSL_NO_CMS) && OPENSSL_VERSION_NUMBER >= 0x0090808fL
static const long Cryptography_HAS_CMS = 1;
#else
static const long Cryptography_HAS_CMS = 0;
typedef void CMS_ContentInfo;
typedef void CMS_SignerInfo;
typedef void CMS_CertificateChoices;
typedef void CMS_RevocationInfoChoice;
typedef void CMS_RecipientInfo;
typedef void CMS_ReceiptRequest;
typedef void CMS_Receipt;
BIO *(*BIO_new_CMS)(BIO *, CMS_ContentInfo *) = NULL;
int (*i2d_CMS_bio_stream)(BIO *, CMS_ContentInfo *, BIO *, int) = NULL;
int (*PEM_write_bio_CMS_stream)(BIO *, CMS_ContentInfo *, BIO *, int) = NULL;
int (*CMS_final)(CMS_ContentInfo *, BIO *, BIO *, unsigned int) = NULL;
CMS_ContentInfo *(*CMS_sign)(X509 *, EVP_PKEY *, Cryptography_STACK_OF_X509 *,
                             BIO *, unsigned int) = NULL;
int (*CMS_verify)(CMS_ContentInfo *, Cryptography_STACK_OF_X509 *,
                  X509_STORE *, BIO *, BIO *, unsigned int) = NULL;
CMS_ContentInfo *(*CMS_encrypt)(Cryptography_STACK_OF_X509 *, BIO *,
                                const EVP_CIPHER *, unsigned int) = NULL;
int (*CMS_decrypt)(CMS_ContentInfo *, EVP_PKEY *, X509 *, BIO *, BIO *,
                   unsigned int) = NULL;
CMS_SignerInfo *(*CMS_add1_signer)(CMS_ContentInfo *, X509 *, EVP_PKEY *,
                                   const EVP_MD *, unsigned int) = NULL;
#endif
"""

CONDITIONAL_NAMES = {
    "Cryptography_HAS_CMS": [
        "BIO_new_CMS",
        "i2d_CMS_bio_stream",
        "PEM_write_bio_CMS_stream",
        "CMS_final",
        "CMS_sign",
        "CMS_verify",
        "CMS_encrypt",
        "CMS_decrypt",
        "CMS_add1_signer",
    ]
}

########NEW FILE########
__FILENAME__ = conf
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/conf.h>
"""

TYPES = """
typedef ... CONF;
"""

FUNCTIONS = """
"""

MACROS = """
"""

CUSTOMIZATIONS = """
"""

CONDITIONAL_NAMES = {}

########NEW FILE########
__FILENAME__ = crypto
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/crypto.h>
"""

TYPES = """
typedef ... CRYPTO_THREADID;

static const int SSLEAY_VERSION;
static const int SSLEAY_CFLAGS;
static const int SSLEAY_PLATFORM;
static const int SSLEAY_DIR;
static const int SSLEAY_BUILT_ON;
static const int CRYPTO_MEM_CHECK_ON;
static const int CRYPTO_MEM_CHECK_OFF;
static const int CRYPTO_MEM_CHECK_ENABLE;
static const int CRYPTO_MEM_CHECK_DISABLE;
static const int CRYPTO_LOCK;
static const int CRYPTO_UNLOCK;
static const int CRYPTO_READ;
static const int CRYPTO_WRITE;
static const int CRYPTO_LOCK_SSL;
"""

FUNCTIONS = """
unsigned long SSLeay(void);
const char *SSLeay_version(int);

void CRYPTO_free(void *);
int CRYPTO_mem_ctrl(int);
int CRYPTO_is_mem_check_on(void);
void CRYPTO_mem_leaks(struct bio_st *);
void CRYPTO_cleanup_all_ex_data(void);
int CRYPTO_num_locks(void);
void CRYPTO_set_locking_callback(void(*)(int, int, const char *, int));
void CRYPTO_set_id_callback(unsigned long (*)(void));
unsigned long (*CRYPTO_get_id_callback(void))(void);
void (*CRYPTO_get_locking_callback(void))(int, int, const char *, int);
void CRYPTO_lock(int, int, const char *, int);

void OPENSSL_free(void *);
"""

MACROS = """
void CRYPTO_add(int *, int, int);
void CRYPTO_malloc_init(void);
void CRYPTO_malloc_debug_init(void);
"""

CUSTOMIZATIONS = """
"""

CONDITIONAL_NAMES = {}

########NEW FILE########
__FILENAME__ = dh
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/dh.h>
"""

TYPES = """
typedef struct dh_st {
    // prime number (shared)
    BIGNUM *p;
    // generator of Z_p (shared)
    BIGNUM *g;
    // private DH value x
    BIGNUM *priv_key;
    // public DH value g^x
    BIGNUM *pub_key;
    ...;
} DH;
"""

FUNCTIONS = """
DH *DH_new(void);
void DH_free(DH *);
int DH_size(const DH *);
DH *DH_generate_parameters(int, int, void (*)(int, int, void *), void *);
int DH_check(const DH *, int *);
int DH_generate_key(DH *);
int DH_compute_key(unsigned char *, const BIGNUM *, DH *);
int DH_set_ex_data(DH *, int, void *);
void *DH_get_ex_data(DH *, int);
DH *d2i_DHparams(DH **, const unsigned char **, long);
int i2d_DHparams(const DH *, unsigned char **);
int DHparams_print_fp(FILE *, const DH *);
int DHparams_print(BIO *, const DH *);
"""

MACROS = """
int DH_generate_parameters_ex(DH *, int, int, BN_GENCB *);
"""

CUSTOMIZATIONS = """
"""

CONDITIONAL_NAMES = {}

########NEW FILE########
__FILENAME__ = dsa
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/dsa.h>
"""

TYPES = """
typedef struct dsa_st {
    // prime number (public)
    BIGNUM *p;
    // 160-bit subprime, q | p-1 (public)
    BIGNUM *q;
    // generator of subgroup (public)
    BIGNUM *g;
    // private key x
    BIGNUM *priv_key;
    // public key y = g^x
    BIGNUM *pub_key;
    ...;
} DSA;
typedef struct {
    BIGNUM *r;
    BIGNUM *s;
} DSA_SIG;
"""

FUNCTIONS = """
DSA *DSA_generate_parameters(int, unsigned char *, int, int *, unsigned long *,
                             void (*)(int, int, void *), void *);
int DSA_generate_key(DSA *);
DSA *DSA_new(void);
void DSA_free(DSA *);
DSA_SIG *DSA_SIG_new(void);
void DSA_SIG_free(DSA_SIG *);
int i2d_DSA_SIG(const DSA_SIG *, unsigned char **);
DSA_SIG *d2i_DSA_SIG(DSA_SIG **, const unsigned char **, long);
int DSA_size(const DSA *);
int DSA_sign(int, const unsigned char *, int, unsigned char *, unsigned int *,
             DSA *);
int DSA_verify(int, const unsigned char *, int, const unsigned char *, int,
               DSA *);
"""

MACROS = """
int DSA_generate_parameters_ex(DSA *, int, unsigned char *, int,
                               int *, unsigned long *, BN_GENCB *);
"""

CUSTOMIZATIONS = """
"""

CONDITIONAL_NAMES = {}

########NEW FILE########
__FILENAME__ = ec
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#ifndef OPENSSL_NO_EC
#include <openssl/ec.h>
#endif

#include <openssl/obj_mac.h>
"""

TYPES = """
static const int Cryptography_HAS_EC;
static const int Cryptography_HAS_EC_1_0_1;
static const int Cryptography_HAS_EC_NISTP_64_GCC_128;
static const int Cryptography_HAS_EC2M;

static const int OPENSSL_EC_NAMED_CURVE;

typedef ... EC_KEY;
typedef ... EC_GROUP;
typedef ... EC_POINT;
typedef ... EC_METHOD;
typedef struct {
    int nid;
    const char *comment;
} EC_builtin_curve;
typedef enum { ... } point_conversion_form_t;
"""

FUNCTIONS = """
"""

MACROS = """
EC_GROUP *EC_GROUP_new(const EC_METHOD *);
void EC_GROUP_free(EC_GROUP *);
void EC_GROUP_clear_free(EC_GROUP *);

EC_GROUP *EC_GROUP_new_curve_GFp(
    const BIGNUM *, const BIGNUM *, const BIGNUM *, BN_CTX *);
EC_GROUP *EC_GROUP_new_curve_GF2m(
    const BIGNUM *, const BIGNUM *, const BIGNUM *, BN_CTX *);
EC_GROUP *EC_GROUP_new_by_curve_name(int);

int EC_GROUP_set_curve_GFp(
    EC_GROUP *, const BIGNUM *, const BIGNUM *, const BIGNUM *, BN_CTX *);
int EC_GROUP_get_curve_GFp(
    const EC_GROUP *, BIGNUM *, BIGNUM *, BIGNUM *, BN_CTX *);
int EC_GROUP_set_curve_GF2m(
    EC_GROUP *, const BIGNUM *, const BIGNUM *, const BIGNUM *, BN_CTX *);
int EC_GROUP_get_curve_GF2m(
    const EC_GROUP *, BIGNUM *, BIGNUM *, BIGNUM *, BN_CTX *);

int EC_GROUP_get_degree(const EC_GROUP *);

const EC_METHOD *EC_GROUP_method_of(const EC_GROUP *);
const EC_POINT *EC_GROUP_get0_generator(const EC_GROUP *);
int EC_GROUP_get_curve_name(const EC_GROUP *);

size_t EC_get_builtin_curves(EC_builtin_curve *, size_t);

void EC_KEY_free(EC_KEY *);

int EC_KEY_get_flags(const EC_KEY *);
void EC_KEY_set_flags(EC_KEY *, int);
void EC_KEY_clear_flags(EC_KEY *, int);
EC_KEY *EC_KEY_new_by_curve_name(int);
EC_KEY *EC_KEY_copy(EC_KEY *, const EC_KEY *);
EC_KEY *EC_KEY_dup(const EC_KEY *);
int EC_KEY_up_ref(EC_KEY *);
const EC_GROUP *EC_KEY_get0_group(const EC_KEY *);
int EC_GROUP_get_order(const EC_GROUP *, BIGNUM *, BN_CTX *);
int EC_KEY_set_group(EC_KEY *, const EC_GROUP *);
const BIGNUM *EC_KEY_get0_private_key(const EC_KEY *);
int EC_KEY_set_private_key(EC_KEY *, const BIGNUM *);
const EC_POINT *EC_KEY_get0_public_key(const EC_KEY *);
int EC_KEY_set_public_key(EC_KEY *, const EC_POINT *);
unsigned int EC_KEY_get_enc_flags(const EC_KEY *);
void EC_KEY_set_enc_flags(EC_KEY *eckey, unsigned int);
point_conversion_form_t EC_KEY_get_conv_form(const EC_KEY *);
void EC_KEY_set_conv_form(EC_KEY *, point_conversion_form_t);
void *EC_KEY_get_key_method_data(
    EC_KEY *,
    void *(*)(void *),
    void (*)(void *),
    void (*)(void *)
);
void EC_KEY_insert_key_method_data(
    EC_KEY *,
    void *,
    void *(*)(void *),
    void (*)(void *),
    void (*)(void *)
);
void EC_KEY_set_asn1_flag(EC_KEY *, int);
int EC_KEY_precompute_mult(EC_KEY *, BN_CTX *);
int EC_KEY_generate_key(EC_KEY *);
int EC_KEY_check_key(const EC_KEY *);
int EC_KEY_set_public_key_affine_coordinates(EC_KEY *, BIGNUM *, BIGNUM *);

EC_POINT *EC_POINT_new(const EC_GROUP *);
void EC_POINT_free(EC_POINT *);
void EC_POINT_clear_free(EC_POINT *);
int EC_POINT_copy(EC_POINT *, const EC_POINT *);
EC_POINT *EC_POINT_dup(const EC_POINT *, const EC_GROUP *);
const EC_METHOD *EC_POINT_method_of(const EC_POINT *);

int EC_POINT_set_to_infinity(const EC_GROUP *, EC_POINT *);

int EC_POINT_set_Jprojective_coordinates_GFp(const EC_GROUP *, EC_POINT *,
    const BIGNUM *, const BIGNUM *, const BIGNUM *, BN_CTX *);

int EC_POINT_get_Jprojective_coordinates_GFp(const EC_GROUP *,
    const EC_POINT *, BIGNUM *, BIGNUM *, BIGNUM *, BN_CTX *);

int EC_POINT_set_affine_coordinates_GFp(const EC_GROUP *, EC_POINT *,
    const BIGNUM *, const BIGNUM *, BN_CTX *);

int EC_POINT_get_affine_coordinates_GFp(const EC_GROUP *,
    const EC_POINT *, BIGNUM *, BIGNUM *, BN_CTX *);

int EC_POINT_set_compressed_coordinates_GFp(const EC_GROUP *, EC_POINT *,
    const BIGNUM *, int, BN_CTX *);

int EC_POINT_set_affine_coordinates_GF2m(const EC_GROUP *, EC_POINT *,
    const BIGNUM *, const BIGNUM *, BN_CTX *);

int EC_POINT_get_affine_coordinates_GF2m(const EC_GROUP *,
    const EC_POINT *, BIGNUM *, BIGNUM *, BN_CTX *);

int EC_POINT_set_compressed_coordinates_GF2m(const EC_GROUP *, EC_POINT *,
    const BIGNUM *, int, BN_CTX *);

size_t EC_POINT_point2oct(const EC_GROUP *, const EC_POINT *,
    point_conversion_form_t,
    unsigned char *, size_t, BN_CTX *);

int EC_POINT_oct2point(const EC_GROUP *, EC_POINT *,
    const unsigned char *, size_t, BN_CTX *);

BIGNUM *EC_POINT_point2bn(const EC_GROUP *, const EC_POINT *,
    point_conversion_form_t form, BIGNUM *, BN_CTX *);

EC_POINT *EC_POINT_bn2point(const EC_GROUP *, const BIGNUM *,
    EC_POINT *, BN_CTX *);

char *EC_POINT_point2hex(const EC_GROUP *, const EC_POINT *,
    point_conversion_form_t form, BN_CTX *);

EC_POINT *EC_POINT_hex2point(const EC_GROUP *, const char *,
    EC_POINT *, BN_CTX *);

int EC_POINT_add(const EC_GROUP *, EC_POINT *, const EC_POINT *,
    const EC_POINT *, BN_CTX *);

int EC_POINT_dbl(const EC_GROUP *, EC_POINT *, const EC_POINT *, BN_CTX *);
int EC_POINT_invert(const EC_GROUP *, EC_POINT *, BN_CTX *);
int EC_POINT_is_at_infinity(const EC_GROUP *, const EC_POINT *);
int EC_POINT_is_on_curve(const EC_GROUP *, const EC_POINT *, BN_CTX *);

int EC_POINT_cmp(
    const EC_GROUP *, const EC_POINT *, const EC_POINT *, BN_CTX *);

int EC_POINT_make_affine(const EC_GROUP *, EC_POINT *, BN_CTX *);
int EC_POINTs_make_affine(const EC_GROUP *, size_t, EC_POINT *[], BN_CTX *);

int EC_POINTs_mul(
    const EC_GROUP *, EC_POINT *, const BIGNUM *,
    size_t, const EC_POINT *[], const BIGNUM *[], BN_CTX *);

int EC_POINT_mul(const EC_GROUP *, EC_POINT *, const BIGNUM *,
    const EC_POINT *, const BIGNUM *, BN_CTX *);

int EC_GROUP_precompute_mult(EC_GROUP *, BN_CTX *);
int EC_GROUP_have_precompute_mult(const EC_GROUP *);

const EC_METHOD *EC_GFp_simple_method();
const EC_METHOD *EC_GFp_mont_method();
const EC_METHOD *EC_GFp_nist_method();

const EC_METHOD *EC_GFp_nistp224_method();
const EC_METHOD *EC_GFp_nistp256_method();
const EC_METHOD *EC_GFp_nistp521_method();

const EC_METHOD *EC_GF2m_simple_method();

int EC_METHOD_get_field_type(const EC_METHOD *);
"""

CUSTOMIZATIONS = """
#ifdef OPENSSL_NO_EC
static const long Cryptography_HAS_EC = 0;

typedef void EC_KEY;
typedef void EC_GROUP;
typedef void EC_POINT;
typedef void EC_METHOD;
typedef struct {
    int nid;
    const char *comment;
} EC_builtin_curve;
typedef long point_conversion_form_t;

static const int OPENSSL_EC_NAMED_CURVE = 0;

void (*EC_KEY_free)(EC_KEY *) = NULL;
size_t (*EC_get_builtin_curves)(EC_builtin_curve *, size_t) = NULL;
EC_KEY *(*EC_KEY_new_by_curve_name)(int) = NULL;
EC_KEY *(*EC_KEY_copy)(EC_KEY *, const EC_KEY *) = NULL;
EC_KEY *(*EC_KEY_dup)(const EC_KEY *) = NULL;
int (*EC_KEY_up_ref)(EC_KEY *) = NULL;
const EC_GROUP *(*EC_KEY_get0_group)(const EC_KEY *) = NULL;
int (*EC_GROUP_get_order)(const EC_GROUP *, BIGNUM *, BN_CTX *) = NULL;
int (*EC_KEY_set_group)(EC_KEY *, const EC_GROUP *) = NULL;
const BIGNUM *(*EC_KEY_get0_private_key)(const EC_KEY *) = NULL;
int (*EC_KEY_set_private_key)(EC_KEY *, const BIGNUM *) = NULL;
const EC_POINT *(*EC_KEY_get0_public_key)(const EC_KEY *) = NULL;
int (*EC_KEY_set_public_key)(EC_KEY *, const EC_POINT *) = NULL;
unsigned int (*EC_KEY_get_enc_flags)(const EC_KEY *) = NULL;
void (*EC_KEY_set_enc_flags)(EC_KEY *eckey, unsigned int) = NULL;
point_conversion_form_t (*EC_KEY_get_conv_form)(const EC_KEY *) = NULL;
void (*EC_KEY_set_conv_form)(EC_KEY *, point_conversion_form_t) = NULL;
void *(*EC_KEY_get_key_method_data)(
    EC_KEY *, void *(*)(void *), void (*)(void *), void (*)(void *)) = NULL;
void (*EC_KEY_insert_key_method_data)(
    EC_KEY *, void *,
    void *(*)(void *), void (*)(void *), void (*)(void *)) = NULL;
void (*EC_KEY_set_asn1_flag)(EC_KEY *, int) = NULL;
int (*EC_KEY_precompute_mult)(EC_KEY *, BN_CTX *) = NULL;
int (*EC_KEY_generate_key)(EC_KEY *) = NULL;
int (*EC_KEY_check_key)(const EC_KEY *) = NULL;

EC_GROUP *(*EC_GROUP_new)(const EC_METHOD *);
void (*EC_GROUP_free)(EC_GROUP *);
void (*EC_GROUP_clear_free)(EC_GROUP *);

EC_GROUP *(*EC_GROUP_new_curve_GFp)(
    const BIGNUM *, const BIGNUM *, const BIGNUM *, BN_CTX *);

EC_GROUP *(*EC_GROUP_new_by_curve_name)(int);

int (*EC_GROUP_set_curve_GFp)(
    EC_GROUP *, const BIGNUM *, const BIGNUM *, const BIGNUM *, BN_CTX *);

int (*EC_GROUP_get_curve_GFp)(
    const EC_GROUP *, BIGNUM *, BIGNUM *, BIGNUM *, BN_CTX *);

int (*EC_GROUP_get_degree)(const EC_GROUP *) = NULL;

const EC_METHOD *(*EC_GROUP_method_of)(const EC_GROUP *) = NULL;
const EC_POINT *(*EC_GROUP_get0_generator)(const EC_GROUP *) = NULL;
int (*EC_GROUP_get_curve_name)(const EC_GROUP *) = NULL;

EC_POINT *(*EC_POINT_new)(const EC_GROUP *) = NULL;
void (*EC_POINT_free)(EC_POINT *) = NULL;
void (*EC_POINT_clear_free)(EC_POINT *) = NULL;
int (*EC_POINT_copy)(EC_POINT *, const EC_POINT *) = NULL;
EC_POINT *(*EC_POINT_dup)(const EC_POINT *, const EC_GROUP *) = NULL;
const EC_METHOD *(*EC_POINT_method_of)(const EC_POINT *) = NULL;
int (*EC_POINT_set_to_infinity)(const EC_GROUP *, EC_POINT *) = NULL;
int (*EC_POINT_set_Jprojective_coordinates_GFp)(const EC_GROUP *, EC_POINT *,
    const BIGNUM *, const BIGNUM *, const BIGNUM *, BN_CTX *) = NULL;

int (*EC_POINT_get_Jprojective_coordinates_GFp)(const EC_GROUP *,
    const EC_POINT *, BIGNUM *, BIGNUM *, BIGNUM *, BN_CTX *) = NULL;

int (*EC_POINT_set_affine_coordinates_GFp)(const EC_GROUP *, EC_POINT *,
    const BIGNUM *, const BIGNUM *, BN_CTX *) = NULL;

int (*EC_POINT_get_affine_coordinates_GFp)(const EC_GROUP *,
    const EC_POINT *, BIGNUM *, BIGNUM *, BN_CTX *) = NULL;

int (*EC_POINT_set_compressed_coordinates_GFp)(const EC_GROUP *, EC_POINT *,
    const BIGNUM *, int, BN_CTX *) = NULL;

size_t (*EC_POINT_point2oct)(const EC_GROUP *, const EC_POINT *,
    point_conversion_form_t,
    unsigned char *, size_t, BN_CTX *) = NULL;

int (*EC_POINT_oct2point)(const EC_GROUP *, EC_POINT *,
    const unsigned char *, size_t, BN_CTX *) = NULL;

BIGNUM *(*EC_POINT_point2bn)(const EC_GROUP *, const EC_POINT *,
    point_conversion_form_t form, BIGNUM *, BN_CTX *) = NULL;

EC_POINT *(*EC_POINT_bn2point)(const EC_GROUP *, const BIGNUM *,
    EC_POINT *, BN_CTX *) = NULL;

char *(*EC_POINT_point2hex)(const EC_GROUP *, const EC_POINT *,
    point_conversion_form_t form, BN_CTX *) = NULL;

EC_POINT *(*EC_POINT_hex2point)(const EC_GROUP *, const char *,
    EC_POINT *, BN_CTX *) = NULL;

int (*EC_POINT_add)(const EC_GROUP *, EC_POINT *, const EC_POINT *,
    const EC_POINT *, BN_CTX *) = NULL;

int (*EC_POINT_dbl)(const EC_GROUP *, EC_POINT *, const EC_POINT *,
    BN_CTX *) = NULL;

int (*EC_POINT_invert)(const EC_GROUP *, EC_POINT *, BN_CTX *) = NULL;
int (*EC_POINT_is_at_infinity)(const EC_GROUP *, const EC_POINT *) = NULL;

int (*EC_POINT_is_on_curve)(const EC_GROUP *, const EC_POINT *,
    BN_CTX *) = NULL;

int (*EC_POINT_cmp)(
    const EC_GROUP *, const EC_POINT *, const EC_POINT *, BN_CTX *) = NULL;

int (*EC_POINT_make_affine)(const EC_GROUP *, EC_POINT *, BN_CTX *) = NULL;

int (*EC_POINTs_make_affine)(const EC_GROUP *, size_t, EC_POINT *[],
    BN_CTX *) = NULL;

int (*EC_POINTs_mul)(
    const EC_GROUP *, EC_POINT *, const BIGNUM *,
    size_t, const EC_POINT *[], const BIGNUM *[], BN_CTX *) = NULL;

int (*EC_POINT_mul)(const EC_GROUP *, EC_POINT *, const BIGNUM *,
    const EC_POINT *, const BIGNUM *, BN_CTX *) = NULL;

int (*EC_GROUP_precompute_mult)(EC_GROUP *, BN_CTX *) = NULL;
int (*EC_GROUP_have_precompute_mult)(const EC_GROUP *) = NULL;

const EC_METHOD *(*EC_GFp_simple_method)() = NULL;
const EC_METHOD *(*EC_GFp_mont_method)() = NULL;
const EC_METHOD *(*EC_GFp_nist_method)() = NULL;

int (*EC_METHOD_get_field_type)(const EC_METHOD *) = NULL;

#else
static const long Cryptography_HAS_EC = 1;
#endif

#if defined(OPENSSL_NO_EC) || OPENSSL_VERSION_NUMBER < 0x1000100f
static const long Cryptography_HAS_EC_1_0_1 = 0;

int (*EC_KEY_get_flags)(const EC_KEY *) = NULL;
void (*EC_KEY_set_flags)(EC_KEY *, int) = NULL;
void (*EC_KEY_clear_flags)(EC_KEY *, int) = NULL;

int (*EC_KEY_set_public_key_affine_coordinates)(
    EC_KEY *, BIGNUM *, BIGNUM *) = NULL;
#else
static const long Cryptography_HAS_EC_1_0_1 = 1;
#endif


#if defined(OPENSSL_NO_EC) || OPENSSL_VERSION_NUMBER < 0x1000100f || \
    defined(OPENSSL_NO_EC_NISTP_64_GCC_128)
static const long Cryptography_HAS_EC_NISTP_64_GCC_128 = 0;

const EC_METHOD *(*EC_GFp_nistp224_method)(void) = NULL;
const EC_METHOD *(*EC_GFp_nistp256_method)(void) = NULL;
const EC_METHOD *(*EC_GFp_nistp521_method)(void) = NULL;
#else
static const long Cryptography_HAS_EC_NISTP_64_GCC_128 = 1;
#endif

#if defined(OPENSSL_NO_EC) || defined(OPENSSL_NO_EC2M)
static const long Cryptography_HAS_EC2M = 0;

const EC_METHOD *(*EC_GF2m_simple_method)() = NULL;

int (*EC_POINT_set_affine_coordinates_GF2m)(const EC_GROUP *, EC_POINT *,
    const BIGNUM *, const BIGNUM *, BN_CTX *) = NULL;

int (*EC_POINT_get_affine_coordinates_GF2m)(const EC_GROUP *,
    const EC_POINT *, BIGNUM *, BIGNUM *, BN_CTX *) = NULL;

int (*EC_POINT_set_compressed_coordinates_GF2m)(const EC_GROUP *, EC_POINT *,
    const BIGNUM *, int, BN_CTX *) = NULL;

int (*EC_GROUP_set_curve_GF2m)(
    EC_GROUP *, const BIGNUM *, const BIGNUM *, const BIGNUM *, BN_CTX *);

int (*EC_GROUP_get_curve_GF2m)(
    const EC_GROUP *, BIGNUM *, BIGNUM *, BIGNUM *, BN_CTX *);

EC_GROUP *(*EC_GROUP_new_curve_GF2m)(
    const BIGNUM *, const BIGNUM *, const BIGNUM *, BN_CTX *);
#else
static const long Cryptography_HAS_EC2M = 1;
#endif
"""

CONDITIONAL_NAMES = {
    "Cryptography_HAS_EC": [
        "OPENSSL_EC_NAMED_CURVE",
        "EC_GROUP_new",
        "EC_GROUP_free",
        "EC_GROUP_clear_free",
        "EC_GROUP_new_curve_GFp",
        "EC_GROUP_new_by_curve_name",
        "EC_GROUP_set_curve_GFp",
        "EC_GROUP_get_curve_GFp",
        "EC_GROUP_method_of",
        "EC_GROUP_get0_generator",
        "EC_GROUP_get_curve_name",
        "EC_GROUP_get_degree",
        "EC_KEY_free",
        "EC_get_builtin_curves",
        "EC_KEY_new_by_curve_name",
        "EC_KEY_copy",
        "EC_KEY_dup",
        "EC_KEY_up_ref",
        "EC_KEY_set_group",
        "EC_KEY_get0_private_key",
        "EC_KEY_set_private_key",
        "EC_KEY_set_public_key",
        "EC_KEY_get_enc_flags",
        "EC_KEY_set_enc_flags",
        "EC_KEY_set_conv_form",
        "EC_KEY_get_key_method_data",
        "EC_KEY_insert_key_method_data",
        "EC_KEY_set_asn1_flag",
        "EC_KEY_precompute_mult",
        "EC_KEY_generate_key",
        "EC_KEY_check_key",
        "EC_POINT_new",
        "EC_POINT_free",
        "EC_POINT_clear_free",
        "EC_POINT_copy",
        "EC_POINT_dup",
        "EC_POINT_method_of",
        "EC_POINT_set_to_infinity",
        "EC_POINT_set_Jprojective_coordinates_GFp",
        "EC_POINT_get_Jprojective_coordinates_GFp",
        "EC_POINT_set_affine_coordinates_GFp",
        "EC_POINT_get_affine_coordinates_GFp",
        "EC_POINT_set_compressed_coordinates_GFp",
        "EC_POINT_point2oct",
        "EC_POINT_oct2point",
        "EC_POINT_point2bn",
        "EC_POINT_bn2point",
        "EC_POINT_point2hex",
        "EC_POINT_hex2point",
        "EC_POINT_add",
        "EC_POINT_dbl",
        "EC_POINT_invert",
        "EC_POINT_is_at_infinity",
        "EC_POINT_is_on_curve",
        "EC_POINT_cmp",
        "EC_POINT_make_affine",
        "EC_POINTs_make_affine",
        "EC_POINTs_mul",
        "EC_POINT_mul",
        "EC_GROUP_precompute_mult",
        "EC_GROUP_have_precompute_mult",
        "EC_GFp_simple_method",
        "EC_GFp_mont_method",
        "EC_GFp_nist_method",
        "EC_METHOD_get_field_type",
    ],

    "Cryptography_HAS_EC_1_0_1": [
        "EC_KEY_get_flags",
        "EC_KEY_set_flags",
        "EC_KEY_clear_flags",
        "EC_KEY_set_public_key_affine_coordinates",
    ],

    "Cryptography_HAS_EC_NISTP_64_GCC_128": [
        "EC_GFp_nistp224_method",
        "EC_GFp_nistp256_method",
        "EC_GFp_nistp521_method",
    ],

    "Cryptography_HAS_EC2M": [
        "EC_GF2m_simple_method",
        "EC_POINT_set_affine_coordinates_GF2m",
        "EC_POINT_get_affine_coordinates_GF2m",
        "EC_POINT_set_compressed_coordinates_GF2m",
        "EC_GROUP_set_curve_GF2m",
        "EC_GROUP_get_curve_GF2m",
        "EC_GROUP_new_curve_GF2m",
    ],
}

########NEW FILE########
__FILENAME__ = ecdh
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#ifndef OPENSSL_NO_ECDH
#include <openssl/ecdh.h>
#endif
"""

TYPES = """
static const int Cryptography_HAS_ECDH;
"""

FUNCTIONS = """
"""

MACROS = """
int ECDH_compute_key(void *, size_t, const EC_POINT *, EC_KEY *,
                     void *(*)(const void *, size_t, void *, size_t *));

int ECDH_get_ex_new_index(long, void *, CRYPTO_EX_new *, CRYPTO_EX_dup *,
                          CRYPTO_EX_free *);

int ECDH_set_ex_data(EC_KEY *, int, void *);

void *ECDH_get_ex_data(EC_KEY *, int);
"""

CUSTOMIZATIONS = """
#ifdef OPENSSL_NO_ECDH
static const long Cryptography_HAS_ECDH = 0;

int (*ECDH_compute_key)(void *, size_t, const EC_POINT *, EC_KEY *,
                        void *(*)(const void *, size_t, void *,
                        size_t *)) = NULL;

int (*ECDH_get_ex_new_index)(long, void *, CRYPTO_EX_new *, CRYPTO_EX_dup *,
                             CRYPTO_EX_free *) = NULL;

int (*ECDH_set_ex_data)(EC_KEY *, int, void *) = NULL;

void *(*ECDH_get_ex_data)(EC_KEY *, int) = NULL;

#else
static const long Cryptography_HAS_ECDH = 1;
#endif
"""

CONDITIONAL_NAMES = {
    "Cryptography_HAS_ECDH": [
        "ECDH_compute_key",
        "ECDH_get_ex_new_index",
        "ECDH_set_ex_data",
        "ECDH_get_ex_data",
    ],
}

########NEW FILE########
__FILENAME__ = ecdsa
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#ifndef OPENSSL_NO_ECDSA
#include <openssl/ecdsa.h>
#endif
"""

TYPES = """
static const int Cryptography_HAS_ECDSA;

typedef struct {
    BIGNUM *r;
    BIGNUM *s;
} ECDSA_SIG;

typedef ... CRYPTO_EX_new;
typedef ... CRYPTO_EX_dup;
typedef ... CRYPTO_EX_free;
"""

FUNCTIONS = """
"""

MACROS = """
ECDSA_SIG *ECDSA_SIG_new();
void ECDSA_SIG_free(ECDSA_SIG *);
int i2d_ECDSA_SIG(const ECDSA_SIG *, unsigned char **);
ECDSA_SIG *d2i_ECDSA_SIG(ECDSA_SIG **s, const unsigned char **, long);
ECDSA_SIG *ECDSA_do_sign(const unsigned char *, int, EC_KEY *);
ECDSA_SIG *ECDSA_do_sign_ex(const unsigned char *, int, const BIGNUM *,
                            const BIGNUM *, EC_KEY *);
int ECDSA_do_verify(const unsigned char *, int, const ECDSA_SIG *, EC_KEY*);
int ECDSA_sign_setup(EC_KEY *, BN_CTX *, BIGNUM **, BIGNUM **);
int ECDSA_sign(int, const unsigned char *, int, unsigned char *,
               unsigned int *, EC_KEY *);
int ECDSA_sign_ex(int, const unsigned char *, int dgstlen, unsigned char *,
                  unsigned int *, const BIGNUM *, const BIGNUM *, EC_KEY *);
int ECDSA_verify(int, const unsigned char *, int, const unsigned char *, int,
                 EC_KEY *);
int ECDSA_size(const EC_KEY *);

const ECDSA_METHOD* ECDSA_OpenSSL();
void ECDSA_set_default_method(const ECDSA_METHOD *);
const ECDSA_METHOD* ECDSA_get_default_method();
int ECDSA_get_ex_new_index(long, void *, CRYPTO_EX_new *,
                           CRYPTO_EX_dup *, CRYPTO_EX_free *);
int ECDSA_set_method(EC_KEY *, const ECDSA_METHOD *);
int ECDSA_set_ex_data(EC_KEY *, int, void *);
void *ECDSA_get_ex_data(EC_KEY *, int);
"""

CUSTOMIZATIONS = """
#ifdef OPENSSL_NO_ECDSA
static const long Cryptography_HAS_ECDSA = 0;

typedef struct {
    BIGNUM *r;
    BIGNUM *s;
} ECDSA_SIG;

ECDSA_SIG* (*ECDSA_SIG_new)() = NULL;
void (*ECDSA_SIG_free)(ECDSA_SIG *) = NULL;
int (*i2d_ECDSA_SIG)(const ECDSA_SIG *, unsigned char **) = NULL;
ECDSA_SIG* (*d2i_ECDSA_SIG)(ECDSA_SIG **s, const unsigned char **,
                            long) = NULL;
ECDSA_SIG* (*ECDSA_do_sign)(const unsigned char *, int, EC_KEY *eckey) = NULL;
ECDSA_SIG* (*ECDSA_do_sign_ex)(const unsigned char *, int, const BIGNUM *,
                               const BIGNUM *, EC_KEY *) = NULL;
int (*ECDSA_do_verify)(const unsigned char *, int, const ECDSA_SIG *,
                       EC_KEY*) = NULL;
int (*ECDSA_sign_setup)(EC_KEY *, BN_CTX *, BIGNUM **, BIGNUM **) = NULL;
int (*ECDSA_sign)(int, const unsigned char *, int, unsigned char *,
                  unsigned int *, EC_KEY *) = NULL;
int (*ECDSA_sign_ex)(int, const unsigned char *, int dgstlen, unsigned char *,
                     unsigned int *, const BIGNUM *, const BIGNUM *,
                     EC_KEY *) = NULL;
int (*ECDSA_verify)(int, const unsigned char *, int, const unsigned char *,
                    int, EC_KEY *) = NULL;
int (*ECDSA_size)(const EC_KEY *) = NULL;

const ECDSA_METHOD* (*ECDSA_OpenSSL)() = NULL;
void (*ECDSA_set_default_method)(const ECDSA_METHOD *) = NULL;
const ECDSA_METHOD* (*ECDSA_get_default_method)() = NULL;
int (*ECDSA_set_method)(EC_KEY *, const ECDSA_METHOD *) = NULL;
int (*ECDSA_get_ex_new_index)(long, void *, CRYPTO_EX_new *,
                              CRYPTO_EX_dup *, CRYPTO_EX_free *) = NULL;
int (*ECDSA_set_ex_data)(EC_KEY *, int, void *) = NULL;
void* (*ECDSA_get_ex_data)(EC_KEY *, int) = NULL;
#else
static const long Cryptography_HAS_ECDSA = 1;
#endif
"""

CONDITIONAL_NAMES = {
    "Cryptography_HAS_ECDSA": [
        "ECDSA_SIG_new",
        "ECDSA_SIG_free",
        "i2d_ECDSA_SIG",
        "d2i_ECDSA_SIG",
        "ECDSA_do_sign",
        "ECDSA_do_sign_ex",
        "ECDSA_do_verify",
        "ECDSA_sign_setup",
        "ECDSA_sign",
        "ECDSA_sign_ex",
        "ECDSA_verify",
        "ECDSA_size",
        "ECDSA_OpenSSL",
        "ECDSA_set_default_method",
        "ECDSA_get_default_method",
        "ECDSA_set_method",
        "ECDSA_get_ex_new_index",
        "ECDSA_set_ex_data",
        "ECDSA_get_ex_data",
    ],
}

########NEW FILE########
__FILENAME__ = engine
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/engine.h>
"""

TYPES = """
typedef ... ENGINE;
typedef ... RSA_METHOD;
typedef ... DSA_METHOD;
typedef ... ECDH_METHOD;
typedef ... ECDSA_METHOD;
typedef ... DH_METHOD;
typedef ... RAND_METHOD;
typedef ... STORE_METHOD;
typedef ... *ENGINE_GEN_INT_FUNC_PTR;
typedef ... *ENGINE_CTRL_FUNC_PTR;
typedef ... *ENGINE_LOAD_KEY_PTR;
typedef ... *ENGINE_CIPHERS_PTR;
typedef ... *ENGINE_DIGESTS_PTR;
typedef ... ENGINE_CMD_DEFN;
typedef ... UI_METHOD;

static const unsigned int ENGINE_METHOD_RSA;
static const unsigned int ENGINE_METHOD_DSA;
static const unsigned int ENGINE_METHOD_RAND;
static const unsigned int ENGINE_METHOD_ECDH;
static const unsigned int ENGINE_METHOD_ECDSA;
static const unsigned int ENGINE_METHOD_CIPHERS;
static const unsigned int ENGINE_METHOD_DIGESTS;
static const unsigned int ENGINE_METHOD_STORE;
static const unsigned int ENGINE_METHOD_ALL;
static const unsigned int ENGINE_METHOD_NONE;
"""

FUNCTIONS = """
ENGINE *ENGINE_get_first(void);
ENGINE *ENGINE_get_last(void);
ENGINE *ENGINE_get_next(ENGINE *);
ENGINE *ENGINE_get_prev(ENGINE *);
int ENGINE_add(ENGINE *);
int ENGINE_remove(ENGINE *);
ENGINE *ENGINE_by_id(const char *);
int ENGINE_init(ENGINE *);
int ENGINE_finish(ENGINE *);
void ENGINE_load_openssl(void);
void ENGINE_load_dynamic(void);
void ENGINE_load_cryptodev(void);
void ENGINE_load_builtin_engines(void);
void ENGINE_cleanup(void);
ENGINE *ENGINE_get_default_RSA(void);
ENGINE *ENGINE_get_default_DSA(void);
ENGINE *ENGINE_get_default_ECDH(void);
ENGINE *ENGINE_get_default_ECDSA(void);
ENGINE *ENGINE_get_default_DH(void);
ENGINE *ENGINE_get_default_RAND(void);
ENGINE *ENGINE_get_cipher_engine(int);
ENGINE *ENGINE_get_digest_engine(int);
int ENGINE_set_default_RSA(ENGINE *);
int ENGINE_set_default_DSA(ENGINE *);
int ENGINE_set_default_ECDH(ENGINE *);
int ENGINE_set_default_ECDSA(ENGINE *);
int ENGINE_set_default_DH(ENGINE *);
int ENGINE_set_default_RAND(ENGINE *);
int ENGINE_set_default_ciphers(ENGINE *);
int ENGINE_set_default_digests(ENGINE *);
int ENGINE_set_default_string(ENGINE *, const char *);
int ENGINE_set_default(ENGINE *, unsigned int);
unsigned int ENGINE_get_table_flags(void);
void ENGINE_set_table_flags(unsigned int);
int ENGINE_register_RSA(ENGINE *);
void ENGINE_unregister_RSA(ENGINE *);
void ENGINE_register_all_RSA(void);
int ENGINE_register_DSA(ENGINE *);
void ENGINE_unregister_DSA(ENGINE *);
void ENGINE_register_all_DSA(void);
int ENGINE_register_ECDH(ENGINE *);
void ENGINE_unregister_ECDH(ENGINE *);
void ENGINE_register_all_ECDH(void);
int ENGINE_register_ECDSA(ENGINE *);
void ENGINE_unregister_ECDSA(ENGINE *);
void ENGINE_register_all_ECDSA(void);
int ENGINE_register_DH(ENGINE *);
void ENGINE_unregister_DH(ENGINE *);
void ENGINE_register_all_DH(void);
int ENGINE_register_RAND(ENGINE *);
void ENGINE_unregister_RAND(ENGINE *);
void ENGINE_register_all_RAND(void);
int ENGINE_register_STORE(ENGINE *);
void ENGINE_unregister_STORE(ENGINE *);
void ENGINE_register_all_STORE(void);
int ENGINE_register_ciphers(ENGINE *);
void ENGINE_unregister_ciphers(ENGINE *);
void ENGINE_register_all_ciphers(void);
int ENGINE_register_digests(ENGINE *);
void ENGINE_unregister_digests(ENGINE *);
void ENGINE_register_all_digests(void);
int ENGINE_register_complete(ENGINE *);
int ENGINE_register_all_complete(void);
int ENGINE_ctrl(ENGINE *, int, long, void *, void (*)(void));
int ENGINE_cmd_is_executable(ENGINE *, int);
int ENGINE_ctrl_cmd(ENGINE *, const char *, long, void *, void (*)(void), int);
int ENGINE_ctrl_cmd_string(ENGINE *, const char *, const char *, int);

ENGINE *ENGINE_new(void);
int ENGINE_free(ENGINE *);
int ENGINE_up_ref(ENGINE *);
int ENGINE_set_id(ENGINE *, const char *);
int ENGINE_set_name(ENGINE *, const char *);
int ENGINE_set_RSA(ENGINE *, const RSA_METHOD *);
int ENGINE_set_DSA(ENGINE *, const DSA_METHOD *);
int ENGINE_set_ECDH(ENGINE *, const ECDH_METHOD *);
int ENGINE_set_ECDSA(ENGINE *, const ECDSA_METHOD *);
int ENGINE_set_DH(ENGINE *, const DH_METHOD *);
int ENGINE_set_RAND(ENGINE *, const RAND_METHOD *);
int ENGINE_set_STORE(ENGINE *, const STORE_METHOD *);
int ENGINE_set_destroy_function(ENGINE *, ENGINE_GEN_INT_FUNC_PTR);
int ENGINE_set_init_function(ENGINE *, ENGINE_GEN_INT_FUNC_PTR);
int ENGINE_set_finish_function(ENGINE *, ENGINE_GEN_INT_FUNC_PTR);
int ENGINE_set_ctrl_function(ENGINE *, ENGINE_CTRL_FUNC_PTR);
int ENGINE_set_load_privkey_function(ENGINE *, ENGINE_LOAD_KEY_PTR);
int ENGINE_set_load_pubkey_function(ENGINE *, ENGINE_LOAD_KEY_PTR);
int ENGINE_set_ciphers(ENGINE *, ENGINE_CIPHERS_PTR);
int ENGINE_set_digests(ENGINE *, ENGINE_DIGESTS_PTR);
int ENGINE_set_flags(ENGINE *, int);
int ENGINE_set_cmd_defns(ENGINE *, const ENGINE_CMD_DEFN *);
const char *ENGINE_get_id(const ENGINE *);
const char *ENGINE_get_name(const ENGINE *);
const RSA_METHOD *ENGINE_get_RSA(const ENGINE *);
const DSA_METHOD *ENGINE_get_DSA(const ENGINE *);
const ECDH_METHOD *ENGINE_get_ECDH(const ENGINE *);
const ECDSA_METHOD *ENGINE_get_ECDSA(const ENGINE *);
const DH_METHOD *ENGINE_get_DH(const ENGINE *);
const RAND_METHOD *ENGINE_get_RAND(const ENGINE *);
const STORE_METHOD *ENGINE_get_STORE(const ENGINE *);

const EVP_CIPHER *ENGINE_get_cipher(ENGINE *, int);
const EVP_MD *ENGINE_get_digest(ENGINE *, int);
int ENGINE_get_flags(const ENGINE *);
const ENGINE_CMD_DEFN *ENGINE_get_cmd_defns(const ENGINE *);
EVP_PKEY *ENGINE_load_private_key(ENGINE *, const char *, UI_METHOD *, void *);
EVP_PKEY *ENGINE_load_public_key(ENGINE *, const char *, UI_METHOD *, void *);
void ENGINE_add_conf_module(void);
"""

MACROS = """
"""

CUSTOMIZATIONS = """
"""

CONDITIONAL_NAMES = {}

########NEW FILE########
__FILENAME__ = err
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/err.h>
"""

TYPES = """
static const int Cryptography_HAS_REMOVE_THREAD_STATE;
static const int Cryptography_HAS_098H_ERROR_CODES;
static const int Cryptography_HAS_098C_CAMELLIA_CODES;

struct ERR_string_data_st {
    unsigned long error;
    const char *string;
};
typedef struct ERR_string_data_st ERR_STRING_DATA;


static const int ERR_LIB_EVP;
static const int ERR_LIB_PEM;
static const int ERR_LIB_ASN1;
static const int ERR_LIB_RSA;

static const int ASN1_F_ASN1_ENUMERATED_TO_BN;
static const int ASN1_F_ASN1_EX_C2I;
static const int ASN1_F_ASN1_FIND_END;
static const int ASN1_F_ASN1_GENERALIZEDTIME_SET;
static const int ASN1_F_ASN1_GENERATE_V3;
static const int ASN1_F_ASN1_GET_OBJECT;
static const int ASN1_F_ASN1_ITEM_I2D_FP;
static const int ASN1_F_ASN1_ITEM_PACK;
static const int ASN1_F_ASN1_ITEM_SIGN;
static const int ASN1_F_ASN1_ITEM_UNPACK;
static const int ASN1_F_ASN1_ITEM_VERIFY;
static const int ASN1_F_ASN1_MBSTRING_NCOPY;
static const int ASN1_F_ASN1_TEMPLATE_EX_D2I;
static const int ASN1_F_ASN1_TEMPLATE_NEW;
static const int ASN1_F_ASN1_TEMPLATE_NOEXP_D2I;
static const int ASN1_F_ASN1_TIME_SET;
static const int ASN1_F_ASN1_TYPE_GET_INT_OCTETSTRING;
static const int ASN1_F_ASN1_TYPE_GET_OCTETSTRING;
static const int ASN1_F_ASN1_UNPACK_STRING;
static const int ASN1_F_ASN1_UTCTIME_SET;
static const int ASN1_F_ASN1_VERIFY;
static const int ASN1_F_BITSTR_CB;
static const int ASN1_F_BN_TO_ASN1_ENUMERATED;
static const int ASN1_F_BN_TO_ASN1_INTEGER;
static const int ASN1_F_D2I_ASN1_TYPE_BYTES;
static const int ASN1_F_D2I_ASN1_UINTEGER;
static const int ASN1_F_D2I_ASN1_UTCTIME;
static const int ASN1_F_D2I_NETSCAPE_RSA;
static const int ASN1_F_D2I_NETSCAPE_RSA_2;
static const int ASN1_F_D2I_PRIVATEKEY;
static const int ASN1_F_D2I_X509;
static const int ASN1_F_D2I_X509_CINF;
static const int ASN1_F_D2I_X509_PKEY;
static const int ASN1_F_I2D_ASN1_SET;
static const int ASN1_F_I2D_ASN1_TIME;
static const int ASN1_F_I2D_DSA_PUBKEY;
static const int ASN1_F_LONG_C2I;
static const int ASN1_F_OID_MODULE_INIT;
static const int ASN1_F_PARSE_TAGGING;
static const int ASN1_F_PKCS5_PBE_SET;
static const int ASN1_F_X509_CINF_NEW;
static const int ASN1_R_BOOLEAN_IS_WRONG_LENGTH;
static const int ASN1_R_BUFFER_TOO_SMALL;
static const int ASN1_R_CIPHER_HAS_NO_OBJECT_IDENTIFIER;
static const int ASN1_R_DATA_IS_WRONG;
static const int ASN1_R_DECODE_ERROR;
static const int ASN1_R_DECODING_ERROR;
static const int ASN1_R_DEPTH_EXCEEDED;
static const int ASN1_R_ENCODE_ERROR;
static const int ASN1_R_ERROR_GETTING_TIME;
static const int ASN1_R_ERROR_LOADING_SECTION;
static const int ASN1_R_MSTRING_WRONG_TAG;
static const int ASN1_R_NESTED_ASN1_STRING;
static const int ASN1_R_NO_MATCHING_CHOICE_TYPE;
static const int ASN1_R_UNKNOWN_MESSAGE_DIGEST_ALGORITHM;
static const int ASN1_R_UNKNOWN_OBJECT_TYPE;
static const int ASN1_R_UNKNOWN_PUBLIC_KEY_TYPE;
static const int ASN1_R_UNKNOWN_TAG;
static const int ASN1_R_UNKOWN_FORMAT;
static const int ASN1_R_UNSUPPORTED_ANY_DEFINED_BY_TYPE;
static const int ASN1_R_UNSUPPORTED_ENCRYPTION_ALGORITHM;
static const int ASN1_R_UNSUPPORTED_PUBLIC_KEY_TYPE;
static const int ASN1_R_UNSUPPORTED_TYPE;
static const int ASN1_R_WRONG_TAG;
static const int ASN1_R_WRONG_TYPE;

static const int EVP_F_AES_INIT_KEY;
static const int EVP_F_D2I_PKEY;
static const int EVP_F_DSA_PKEY2PKCS8;
static const int EVP_F_DSAPKEY2PKCS8;
static const int EVP_F_ECDSA_PKEY2PKCS8;
static const int EVP_F_ECKEY_PKEY2PKCS8;
static const int EVP_F_EVP_CIPHER_CTX_CTRL;
static const int EVP_F_EVP_CIPHER_CTX_SET_KEY_LENGTH;
static const int EVP_F_EVP_CIPHERINIT_EX;
static const int EVP_F_EVP_DECRYPTFINAL_EX;
static const int EVP_F_EVP_DIGESTINIT_EX;
static const int EVP_F_EVP_ENCRYPTFINAL_EX;
static const int EVP_F_EVP_MD_CTX_COPY_EX;
static const int EVP_F_EVP_OPENINIT;
static const int EVP_F_EVP_PBE_ALG_ADD;
static const int EVP_F_EVP_PBE_CIPHERINIT;
static const int EVP_F_EVP_PKCS82PKEY;
static const int EVP_F_EVP_PKEY2PKCS8_BROKEN;
static const int EVP_F_EVP_PKEY_COPY_PARAMETERS;
static const int EVP_F_EVP_PKEY_DECRYPT;
static const int EVP_F_EVP_PKEY_ENCRYPT;
static const int EVP_F_EVP_PKEY_GET1_DH;
static const int EVP_F_EVP_PKEY_GET1_DSA;
static const int EVP_F_EVP_PKEY_GET1_ECDSA;
static const int EVP_F_EVP_PKEY_GET1_EC_KEY;
static const int EVP_F_EVP_PKEY_GET1_RSA;
static const int EVP_F_EVP_PKEY_NEW;
static const int EVP_F_EVP_RIJNDAEL;
static const int EVP_F_EVP_SIGNFINAL;
static const int EVP_F_EVP_VERIFYFINAL;
static const int EVP_F_PKCS5_PBE_KEYIVGEN;
static const int EVP_F_PKCS5_V2_PBE_KEYIVGEN;
static const int EVP_F_PKCS8_SET_BROKEN;
static const int EVP_F_RC2_MAGIC_TO_METH;
static const int EVP_F_RC5_CTRL;

static const int EVP_R_AES_KEY_SETUP_FAILED;
static const int EVP_R_ASN1_LIB;
static const int EVP_R_BAD_BLOCK_LENGTH;
static const int EVP_R_BAD_DECRYPT;
static const int EVP_R_BAD_KEY_LENGTH;
static const int EVP_R_BN_DECODE_ERROR;
static const int EVP_R_BN_PUBKEY_ERROR;
static const int EVP_R_CIPHER_PARAMETER_ERROR;
static const int EVP_R_CTRL_NOT_IMPLEMENTED;
static const int EVP_R_CTRL_OPERATION_NOT_IMPLEMENTED;
static const int EVP_R_DATA_NOT_MULTIPLE_OF_BLOCK_LENGTH;
static const int EVP_R_DECODE_ERROR;
static const int EVP_R_DIFFERENT_KEY_TYPES;
static const int EVP_R_ENCODE_ERROR;
static const int EVP_R_INITIALIZATION_ERROR;
static const int EVP_R_INPUT_NOT_INITIALIZED;
static const int EVP_R_INVALID_KEY_LENGTH;
static const int EVP_R_IV_TOO_LARGE;
static const int EVP_R_KEYGEN_FAILURE;
static const int EVP_R_MISSING_PARAMETERS;
static const int EVP_R_NO_CIPHER_SET;
static const int EVP_R_NO_DIGEST_SET;
static const int EVP_R_NO_DSA_PARAMETERS;
static const int EVP_R_NO_SIGN_FUNCTION_CONFIGURED;
static const int EVP_R_NO_VERIFY_FUNCTION_CONFIGURED;
static const int EVP_R_PKCS8_UNKNOWN_BROKEN_TYPE;
static const int EVP_R_PUBLIC_KEY_NOT_RSA;
static const int EVP_R_UNKNOWN_PBE_ALGORITHM;
static const int EVP_R_UNSUPORTED_NUMBER_OF_ROUNDS;
static const int EVP_R_UNSUPPORTED_CIPHER;
static const int EVP_R_UNSUPPORTED_KEY_DERIVATION_FUNCTION;
static const int EVP_R_UNSUPPORTED_KEYLENGTH;
static const int EVP_R_UNSUPPORTED_SALT_TYPE;
static const int EVP_R_UNSUPPORTED_PRIVATE_KEY_ALGORITHM;
static const int EVP_R_WRONG_FINAL_BLOCK_LENGTH;
static const int EVP_R_WRONG_PUBLIC_KEY_TYPE;

static const int PEM_F_D2I_PKCS8PRIVATEKEY_BIO;
static const int PEM_F_D2I_PKCS8PRIVATEKEY_FP;
static const int PEM_F_DO_PK8PKEY;
static const int PEM_F_DO_PK8PKEY_FP;
static const int PEM_F_LOAD_IV;
static const int PEM_F_PEM_ASN1_READ;
static const int PEM_F_PEM_ASN1_READ_BIO;
static const int PEM_F_PEM_ASN1_WRITE;
static const int PEM_F_PEM_ASN1_WRITE_BIO;
static const int PEM_F_PEM_DEF_CALLBACK;
static const int PEM_F_PEM_DO_HEADER;
static const int PEM_F_PEM_F_PEM_WRITE_PKCS8PRIVATEKEY;
static const int PEM_F_PEM_GET_EVP_CIPHER_INFO;
static const int PEM_F_PEM_PK8PKEY;
static const int PEM_F_PEM_READ;
static const int PEM_F_PEM_READ_BIO;
static const int PEM_F_PEM_READ_BIO_PRIVATEKEY;
static const int PEM_F_PEM_READ_PRIVATEKEY;
static const int PEM_F_PEM_SEALFINAL;
static const int PEM_F_PEM_SEALINIT;
static const int PEM_F_PEM_SIGNFINAL;
static const int PEM_F_PEM_WRITE;
static const int PEM_F_PEM_WRITE_BIO;
static const int PEM_F_PEM_X509_INFO_READ;
static const int PEM_F_PEM_X509_INFO_READ_BIO;
static const int PEM_F_PEM_X509_INFO_WRITE_BIO;

static const int PEM_R_BAD_BASE64_DECODE;
static const int PEM_R_BAD_DECRYPT;
static const int PEM_R_BAD_END_LINE;
static const int PEM_R_BAD_IV_CHARS;
static const int PEM_R_BAD_PASSWORD_READ;
static const int PEM_R_ERROR_CONVERTING_PRIVATE_KEY;
static const int PEM_R_NO_START_LINE;
static const int PEM_R_NOT_DEK_INFO;
static const int PEM_R_NOT_ENCRYPTED;
static const int PEM_R_NOT_PROC_TYPE;
static const int PEM_R_PROBLEMS_GETTING_PASSWORD;
static const int PEM_R_PUBLIC_KEY_NO_RSA;
static const int PEM_R_READ_KEY;
static const int PEM_R_SHORT_HEADER;
static const int PEM_R_UNSUPPORTED_CIPHER;
static const int PEM_R_UNSUPPORTED_ENCRYPTION;

static const int RSA_R_DATA_TOO_LARGE_FOR_KEY_SIZE;
static const int RSA_R_DIGEST_TOO_BIG_FOR_RSA_KEY;
static const int RSA_R_BLOCK_TYPE_IS_NOT_01;
static const int RSA_R_BLOCK_TYPE_IS_NOT_02;
"""

FUNCTIONS = """
void ERR_load_crypto_strings(void);
void ERR_load_SSL_strings(void);
void ERR_free_strings(void);
char* ERR_error_string(unsigned long, char *);
void ERR_error_string_n(unsigned long, char *, size_t);
const char* ERR_lib_error_string(unsigned long);
const char* ERR_func_error_string(unsigned long);
const char* ERR_reason_error_string(unsigned long);
void ERR_print_errors(BIO *);
void ERR_print_errors_fp(FILE *);
unsigned long ERR_get_error(void);
unsigned long ERR_peek_error(void);
unsigned long ERR_peek_last_error(void);
unsigned long ERR_get_error_line(const char **, int *);
unsigned long ERR_peek_error_line(const char **, int *);
unsigned long ERR_peek_last_error_line(const char **, int *);
unsigned long ERR_get_error_line_data(const char **, int *,
                                      const char **, int *);
unsigned long ERR_peek_error_line_data(const char **,
                                       int *, const char **, int *);
unsigned long ERR_peek_last_error_line_data(const char **,
                                            int *, const char **, int *);
void ERR_put_error(int, int, int, const char *, int);
void ERR_add_error_data(int, ...);
int ERR_get_next_error_library(void);
"""

MACROS = """
unsigned long ERR_PACK(int, int, int);
int ERR_GET_LIB(unsigned long);
int ERR_GET_FUNC(unsigned long);
int ERR_GET_REASON(unsigned long);
int ERR_FATAL_ERROR(unsigned long);
/* introduced in 1.0.0 so we have to handle this specially to continue
 * supporting 0.9.8
 */
void ERR_remove_thread_state(const CRYPTO_THREADID *);

/* These were added in OpenSSL 0.9.8h. When we drop support for RHEL/CentOS 5
   we should be able to move these back to TYPES. */
static const int ASN1_F_B64_READ_ASN1;
static const int ASN1_F_B64_WRITE_ASN1;
static const int ASN1_F_SMIME_READ_ASN1;
static const int ASN1_F_SMIME_TEXT;
static const int ASN1_R_NO_CONTENT_TYPE;
static const int ASN1_R_NO_MULTIPART_BODY_FAILURE;
static const int ASN1_R_NO_MULTIPART_BOUNDARY;
/* These were added in OpenSSL 0.9.8c. */
static const int EVP_F_CAMELLIA_INIT_KEY;
static const int EVP_R_CAMELLIA_KEY_SETUP_FAILED;
"""

CUSTOMIZATIONS = """
#if OPENSSL_VERSION_NUMBER >= 0x10000000L
static const long Cryptography_HAS_REMOVE_THREAD_STATE = 1;
#else
static const long Cryptography_HAS_REMOVE_THREAD_STATE = 0;
typedef uint32_t CRYPTO_THREADID;
void (*ERR_remove_thread_state)(const CRYPTO_THREADID *) = NULL;
#endif

// OpenSSL 0.9.8h+
#if OPENSSL_VERSION_NUMBER >= 0x0090808fL
static const long Cryptography_HAS_098H_ERROR_CODES = 1;
#else
static const long Cryptography_HAS_098H_ERROR_CODES = 0;
static const int ASN1_F_B64_READ_ASN1 = 0;
static const int ASN1_F_B64_WRITE_ASN1 = 0;
static const int ASN1_F_SMIME_READ_ASN1 = 0;
static const int ASN1_F_SMIME_TEXT = 0;
static const int ASN1_R_NO_CONTENT_TYPE = 0;
static const int ASN1_R_NO_MULTIPART_BODY_FAILURE = 0;
static const int ASN1_R_NO_MULTIPART_BOUNDARY = 0;
#endif

// OpenSSL 0.9.8c+
#ifdef EVP_F_CAMELLIA_INIT_KEY
static const long Cryptography_HAS_098C_CAMELLIA_CODES = 1;
#else
static const long Cryptography_HAS_098C_CAMELLIA_CODES = 0;
static const int EVP_F_CAMELLIA_INIT_KEY = 0;
static const int EVP_R_CAMELLIA_KEY_SETUP_FAILED = 0;
#endif

"""

CONDITIONAL_NAMES = {
    "Cryptography_HAS_REMOVE_THREAD_STATE": [
        "ERR_remove_thread_state"
    ],
    "Cryptography_HAS_098H_ERROR_CODES": [
        "ASN1_F_B64_READ_ASN1",
        "ASN1_F_B64_WRITE_ASN1",
        "ASN1_F_SMIME_READ_ASN1",
        "ASN1_F_SMIME_TEXT",
        "ASN1_R_NO_CONTENT_TYPE",
        "ASN1_R_NO_MULTIPART_BODY_FAILURE",
        "ASN1_R_NO_MULTIPART_BOUNDARY",
    ],
    "Cryptography_HAS_098C_CAMELLIA_CODES": [
        "EVP_F_CAMELLIA_INIT_KEY",
        "EVP_R_CAMELLIA_KEY_SETUP_FAILED"
    ]
}

########NEW FILE########
__FILENAME__ = evp
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/evp.h>
"""

TYPES = """
typedef ... EVP_CIPHER;
typedef struct {
    const EVP_CIPHER *cipher;
    ENGINE *engine;
    int encrypt;
    ...;
} EVP_CIPHER_CTX;
typedef ... EVP_MD;
typedef struct env_md_ctx_st {
    ...;
} EVP_MD_CTX;

typedef struct evp_pkey_st {
    int type;
    ...;
} EVP_PKEY;
typedef ... EVP_PKEY_CTX;
static const int EVP_PKEY_RSA;
static const int EVP_PKEY_DSA;
static const int EVP_PKEY_EC;
static const int EVP_MAX_MD_SIZE;
static const int EVP_CTRL_GCM_SET_IVLEN;
static const int EVP_CTRL_GCM_GET_TAG;
static const int EVP_CTRL_GCM_SET_TAG;

static const int Cryptography_HAS_GCM;
static const int Cryptography_HAS_PBKDF2_HMAC;
static const int Cryptography_HAS_PKEY_CTX;
"""

FUNCTIONS = """
const EVP_CIPHER *EVP_get_cipherbyname(const char *);
int EVP_EncryptInit_ex(EVP_CIPHER_CTX *, const EVP_CIPHER *, ENGINE *,
                       const unsigned char *, const unsigned char *);
int EVP_CIPHER_CTX_set_padding(EVP_CIPHER_CTX *, int);
int EVP_EncryptUpdate(EVP_CIPHER_CTX *, unsigned char *, int *,
                      const unsigned char *, int);
int EVP_EncryptFinal_ex(EVP_CIPHER_CTX *, unsigned char *, int *);
int EVP_DecryptInit_ex(EVP_CIPHER_CTX *, const EVP_CIPHER *, ENGINE *,
                       const unsigned char *, const unsigned char *);
int EVP_DecryptUpdate(EVP_CIPHER_CTX *, unsigned char *, int *,
                      const unsigned char *, int);
int EVP_DecryptFinal_ex(EVP_CIPHER_CTX *, unsigned char *, int *);
int EVP_CipherInit_ex(EVP_CIPHER_CTX *, const EVP_CIPHER *, ENGINE *,
                      const unsigned char *, const unsigned char *, int);
int EVP_CipherUpdate(EVP_CIPHER_CTX *, unsigned char *, int *,
                     const unsigned char *, int);
int EVP_CipherFinal_ex(EVP_CIPHER_CTX *, unsigned char *, int *);
int EVP_CIPHER_CTX_cleanup(EVP_CIPHER_CTX *);
void EVP_CIPHER_CTX_init(EVP_CIPHER_CTX *);
EVP_CIPHER_CTX *EVP_CIPHER_CTX_new(void);
void EVP_CIPHER_CTX_free(EVP_CIPHER_CTX *);
int EVP_CIPHER_CTX_set_key_length(EVP_CIPHER_CTX *, int);

EVP_MD_CTX *EVP_MD_CTX_create(void);
int EVP_MD_CTX_copy_ex(EVP_MD_CTX *, const EVP_MD_CTX *);
int EVP_DigestInit_ex(EVP_MD_CTX *, const EVP_MD *, ENGINE *);
int EVP_DigestUpdate(EVP_MD_CTX *, const void *, size_t);
int EVP_DigestFinal_ex(EVP_MD_CTX *, unsigned char *, unsigned int *);
int EVP_MD_CTX_cleanup(EVP_MD_CTX *);
void EVP_MD_CTX_destroy(EVP_MD_CTX *);
const EVP_MD *EVP_get_digestbyname(const char *);

EVP_PKEY *EVP_PKEY_new(void);
void EVP_PKEY_free(EVP_PKEY *);
int EVP_PKEY_type(int);
int EVP_PKEY_bits(EVP_PKEY *);
int EVP_PKEY_size(EVP_PKEY *);
RSA *EVP_PKEY_get1_RSA(EVP_PKEY *);
DSA *EVP_PKEY_get1_DSA(EVP_PKEY *);
DH *EVP_PKEY_get1_DH(EVP_PKEY *);

int EVP_SignInit(EVP_MD_CTX *, const EVP_MD *);
int EVP_SignUpdate(EVP_MD_CTX *, const void *, size_t);
int EVP_SignFinal(EVP_MD_CTX *, unsigned char *, unsigned int *, EVP_PKEY *);

int EVP_VerifyInit(EVP_MD_CTX *, const EVP_MD *);
int EVP_VerifyUpdate(EVP_MD_CTX *, const void *, size_t);
int EVP_VerifyFinal(EVP_MD_CTX *, const unsigned char *, unsigned int,
                    EVP_PKEY *);

const EVP_MD *EVP_md5(void);

int PKCS5_PBKDF2_HMAC_SHA1(const char *, int, const unsigned char *, int, int,
                           int, unsigned char *);

int EVP_PKEY_set1_RSA(EVP_PKEY *, struct rsa_st *);
int EVP_PKEY_set1_DSA(EVP_PKEY *, struct dsa_st *);
int EVP_PKEY_set1_DH(EVP_PKEY *, DH *);

int EVP_PKEY_get_attr_count(const EVP_PKEY *);
int EVP_PKEY_get_attr_by_NID(const EVP_PKEY *, int, int);
int EVP_PKEY_get_attr_by_OBJ(const EVP_PKEY *, ASN1_OBJECT *, int);
X509_ATTRIBUTE *EVP_PKEY_get_attr(const EVP_PKEY *, int);
X509_ATTRIBUTE *EVP_PKEY_delete_attr(EVP_PKEY *, int);
int EVP_PKEY_add1_attr(EVP_PKEY *, X509_ATTRIBUTE *);
int EVP_PKEY_add1_attr_by_OBJ(EVP_PKEY *, const ASN1_OBJECT *, int,
                              const unsigned char *, int);
int EVP_PKEY_add1_attr_by_NID(EVP_PKEY *, int, int,
                              const unsigned char *, int);
int EVP_PKEY_add1_attr_by_txt(EVP_PKEY *, const char *, int,
                              const unsigned char *, int);
"""

MACROS = """
void OpenSSL_add_all_algorithms(void);
int EVP_PKEY_assign_RSA(EVP_PKEY *, RSA *);
int EVP_PKEY_assign_DSA(EVP_PKEY *, DSA *);

int EVP_PKEY_assign_EC_KEY(EVP_PKEY *, EC_KEY *);
EC_KEY *EVP_PKEY_get1_EC_KEY(EVP_PKEY *);
int EVP_PKEY_set1_EC_KEY(EVP_PKEY *, EC_KEY *);

int EVP_CIPHER_CTX_block_size(const EVP_CIPHER_CTX *);
int EVP_CIPHER_CTX_ctrl(EVP_CIPHER_CTX *, int, int, void *);

int PKCS5_PBKDF2_HMAC(const char *, int, const unsigned char *, int, int,
                      const EVP_MD *, int, unsigned char *);

int EVP_PKEY_CTX_set_signature_md(EVP_PKEY_CTX *, const EVP_MD *);

// not macros but must be in this section since they're not available in 0.9.8
EVP_PKEY_CTX *EVP_PKEY_CTX_new(EVP_PKEY *, ENGINE *);
EVP_PKEY_CTX *EVP_PKEY_CTX_new_id(int, ENGINE *);
EVP_PKEY_CTX *EVP_PKEY_CTX_dup(EVP_PKEY_CTX *);
void EVP_PKEY_CTX_free(EVP_PKEY_CTX *);
int EVP_PKEY_sign_init(EVP_PKEY_CTX *);
int EVP_PKEY_sign(EVP_PKEY_CTX *, unsigned char *, size_t *,
                  const unsigned char *, size_t);
int EVP_PKEY_verify_init(EVP_PKEY_CTX *);
int EVP_PKEY_verify(EVP_PKEY_CTX *, const unsigned char *, size_t,
                    const unsigned char *, size_t);
int EVP_PKEY_encrypt_init(EVP_PKEY_CTX *);
int EVP_PKEY_decrypt_init(EVP_PKEY_CTX *);

/* The following were macros in 0.9.8e. Once we drop support for RHEL/CentOS 5
   we should move these back to FUNCTIONS. */
const EVP_CIPHER *EVP_CIPHER_CTX_cipher(const EVP_CIPHER_CTX *);
int EVP_CIPHER_block_size(const EVP_CIPHER *);
const EVP_MD *EVP_MD_CTX_md(const EVP_MD_CTX *);
int EVP_MD_size(const EVP_MD *);

/* Must be in macros because EVP_PKEY_CTX is undefined in 0.9.8 */
int Cryptography_EVP_PKEY_encrypt(EVP_PKEY_CTX *ctx, unsigned char *out,
                                  size_t *outlen, const unsigned char *in,
                                  size_t inlen);
int Cryptography_EVP_PKEY_decrypt(EVP_PKEY_CTX *ctx, unsigned char *out,
                                  size_t *outlen, const unsigned char *in,
                                  size_t inlen);
"""

CUSTOMIZATIONS = """
#ifdef EVP_CTRL_GCM_SET_TAG
const long Cryptography_HAS_GCM = 1;
#else
const long Cryptography_HAS_GCM = 0;
const long EVP_CTRL_GCM_GET_TAG = -1;
const long EVP_CTRL_GCM_SET_TAG = -1;
const long EVP_CTRL_GCM_SET_IVLEN = -1;
#endif
#if OPENSSL_VERSION_NUMBER >= 0x10000000L
const long Cryptography_HAS_PBKDF2_HMAC = 1;
const long Cryptography_HAS_PKEY_CTX = 1;

/* OpenSSL 0.9.8 defines EVP_PKEY_encrypt and EVP_PKEY_decrypt functions,
   but they are a completely different signature from the ones in 1.0.0+.
   These wrapper functions allows us to safely declare them on any version and
   conditionally remove them on 0.9.8. */
int Cryptography_EVP_PKEY_encrypt(EVP_PKEY_CTX *ctx, unsigned char *out,
                                  size_t *outlen, const unsigned char *in,
                                  size_t inlen) {
    return EVP_PKEY_encrypt(ctx, out, outlen, in, inlen);
}
int Cryptography_EVP_PKEY_decrypt(EVP_PKEY_CTX *ctx, unsigned char *out,
                                  size_t *outlen, const unsigned char *in,
                                  size_t inlen) {
    return EVP_PKEY_decrypt(ctx, out, outlen, in, inlen);
}
#else
const long Cryptography_HAS_PBKDF2_HMAC = 0;
int (*PKCS5_PBKDF2_HMAC)(const char *, int, const unsigned char *, int, int,
                         const EVP_MD *, int, unsigned char *) = NULL;
const long Cryptography_HAS_PKEY_CTX = 0;
typedef void EVP_PKEY_CTX;
int (*EVP_PKEY_CTX_set_signature_md)(EVP_PKEY_CTX *, const EVP_MD *) = NULL;
int (*EVP_PKEY_sign_init)(EVP_PKEY_CTX *) = NULL;
int (*EVP_PKEY_sign)(EVP_PKEY_CTX *, unsigned char *, size_t *,
                     const unsigned char *, size_t) = NULL;
int (*EVP_PKEY_verify_init)(EVP_PKEY_CTX *) = NULL;
int (*EVP_PKEY_verify)(EVP_PKEY_CTX *, const unsigned char *, size_t,
                       const unsigned char *, size_t) = NULL;
EVP_PKEY_CTX *(*EVP_PKEY_CTX_new)(EVP_PKEY *, ENGINE *) = NULL;
EVP_PKEY_CTX *(*EVP_PKEY_CTX_new_id)(int, ENGINE *) = NULL;
EVP_PKEY_CTX *(*EVP_PKEY_CTX_dup)(EVP_PKEY_CTX *) = NULL;
void (*EVP_PKEY_CTX_free)(EVP_PKEY_CTX *) = NULL;
int (*EVP_PKEY_encrypt_init)(EVP_PKEY_CTX *) = NULL;
int (*EVP_PKEY_decrypt_init)(EVP_PKEY_CTX *) = NULL;
int (*Cryptography_EVP_PKEY_encrypt)(EVP_PKEY_CTX *, unsigned char *, size_t *,
                                     const unsigned char *, size_t) = NULL;
int (*Cryptography_EVP_PKEY_decrypt)(EVP_PKEY_CTX *, unsigned char *, size_t *,
                                     const unsigned char *, size_t) = NULL;
#endif
#ifdef OPENSSL_NO_EC
int (*EVP_PKEY_assign_EC_KEY)(EVP_PKEY *, EC_KEY *) = NULL;
EC_KEY *(*EVP_PKEY_get1_EC_KEY)(EVP_PKEY *) = NULL;
int (*EVP_PKEY_set1_EC_KEY)(EVP_PKEY *, EC_KEY *) = NULL;
#endif

"""

CONDITIONAL_NAMES = {
    "Cryptography_HAS_GCM": [
        "EVP_CTRL_GCM_GET_TAG",
        "EVP_CTRL_GCM_SET_TAG",
        "EVP_CTRL_GCM_SET_IVLEN",
    ],
    "Cryptography_HAS_PBKDF2_HMAC": [
        "PKCS5_PBKDF2_HMAC"
    ],
    "Cryptography_HAS_PKEY_CTX": [
        "EVP_PKEY_CTX_new",
        "EVP_PKEY_CTX_new_id",
        "EVP_PKEY_CTX_dup",
        "EVP_PKEY_CTX_free",
        "EVP_PKEY_sign",
        "EVP_PKEY_sign_init",
        "EVP_PKEY_verify",
        "EVP_PKEY_verify_init",
        "Cryptography_EVP_PKEY_encrypt",
        "EVP_PKEY_encrypt_init",
        "Cryptography_EVP_PKEY_decrypt",
        "EVP_PKEY_decrypt_init",
        "EVP_PKEY_CTX_set_signature_md",
    ],
    "Cryptography_HAS_EC": [
        "EVP_PKEY_assign_EC_KEY",
        "EVP_PKEY_get1_EC_KEY",
        "EVP_PKEY_set1_EC_KEY",
    ]
}

########NEW FILE########
__FILENAME__ = hmac
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/hmac.h>
"""

TYPES = """
typedef struct { ...; } HMAC_CTX;
"""

FUNCTIONS = """
void HMAC_CTX_init(HMAC_CTX *);
void HMAC_CTX_cleanup(HMAC_CTX *);

int Cryptography_HMAC_Init_ex(HMAC_CTX *, const void *, int, const EVP_MD *,
                              ENGINE *);
int Cryptography_HMAC_Update(HMAC_CTX *, const unsigned char *, size_t);
int Cryptography_HMAC_Final(HMAC_CTX *, unsigned char *, unsigned int *);
int Cryptography_HMAC_CTX_copy(HMAC_CTX *, HMAC_CTX *);
"""

MACROS = """
"""

CUSTOMIZATIONS = """
int Cryptography_HMAC_Init_ex(HMAC_CTX *ctx, const void *key, int key_len,
                              const EVP_MD *md, ENGINE *impl) {
#if OPENSSL_VERSION_NUMBER >= 0x010000000
    return HMAC_Init_ex(ctx, key, key_len, md, impl);
#else
    HMAC_Init_ex(ctx, key, key_len, md, impl);
    return 1;
#endif
}

int Cryptography_HMAC_Update(HMAC_CTX *ctx, const unsigned char *data,
                             size_t data_len) {
#if OPENSSL_VERSION_NUMBER >= 0x010000000
    return HMAC_Update(ctx, data, data_len);
#else
    HMAC_Update(ctx, data, data_len);
    return 1;
#endif
}

int Cryptography_HMAC_Final(HMAC_CTX *ctx, unsigned char *digest,
    unsigned int *outlen) {
#if OPENSSL_VERSION_NUMBER >= 0x010000000
    return HMAC_Final(ctx, digest, outlen);
#else
    HMAC_Final(ctx, digest, outlen);
    return 1;
#endif
}

int Cryptography_HMAC_CTX_copy(HMAC_CTX *dst_ctx, HMAC_CTX *src_ctx) {
#if OPENSSL_VERSION_NUMBER >= 0x010000000
    return HMAC_CTX_copy(dst_ctx, src_ctx);
#else
    HMAC_CTX_init(dst_ctx);
    if (!EVP_MD_CTX_copy_ex(&dst_ctx->i_ctx, &src_ctx->i_ctx)) {
        goto err;
    }
    if (!EVP_MD_CTX_copy_ex(&dst_ctx->o_ctx, &src_ctx->o_ctx)) {
        goto err;
    }
    if (!EVP_MD_CTX_copy_ex(&dst_ctx->md_ctx, &src_ctx->md_ctx)) {
        goto err;
    }
    memcpy(dst_ctx->key, src_ctx->key, HMAC_MAX_MD_CBLOCK);
    dst_ctx->key_length = src_ctx->key_length;
    dst_ctx->md = src_ctx->md;
    return 1;

    err:
        return 0;
#endif
}
"""

CONDITIONAL_NAMES = {}

########NEW FILE########
__FILENAME__ = nid
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = ""

TYPES = """
static const int Cryptography_HAS_ECDSA_SHA2_NIDS;

static const int NID_undef;
static const int NID_dsa;
static const int NID_dsaWithSHA;
static const int NID_dsaWithSHA1;
static const int NID_md2;
static const int NID_md4;
static const int NID_md5;
static const int NID_mdc2;
static const int NID_ripemd160;
static const int NID_sha;
static const int NID_sha1;
static const int NID_sha256;
static const int NID_sha384;
static const int NID_sha512;
static const int NID_sha224;
static const int NID_sha;
static const int NID_ecdsa_with_SHA1;
static const int NID_ecdsa_with_SHA224;
static const int NID_ecdsa_with_SHA256;
static const int NID_ecdsa_with_SHA384;
static const int NID_ecdsa_with_SHA512;
static const int NID_crl_reason;
static const int NID_pbe_WithSHA1And3_Key_TripleDES_CBC;
static const int NID_subject_alt_name;
static const int NID_X9_62_c2pnb163v1;
static const int NID_X9_62_c2pnb163v2;
static const int NID_X9_62_c2pnb163v3;
static const int NID_X9_62_c2pnb176v1;
static const int NID_X9_62_c2tnb191v1;
static const int NID_X9_62_c2tnb191v2;
static const int NID_X9_62_c2tnb191v3;
static const int NID_X9_62_c2onb191v4;
static const int NID_X9_62_c2onb191v5;
static const int NID_X9_62_c2pnb208w1;
static const int NID_X9_62_c2tnb239v1;
static const int NID_X9_62_c2tnb239v2;
static const int NID_X9_62_c2tnb239v3;
static const int NID_X9_62_c2onb239v4;
static const int NID_X9_62_c2onb239v5;
static const int NID_X9_62_c2pnb272w1;
static const int NID_X9_62_c2pnb304w1;
static const int NID_X9_62_c2tnb359v1;
static const int NID_X9_62_c2pnb368w1;
static const int NID_X9_62_c2tnb431r1;
static const int NID_X9_62_prime192v1;
static const int NID_X9_62_prime192v2;
static const int NID_X9_62_prime192v3;
static const int NID_X9_62_prime239v1;
static const int NID_X9_62_prime239v2;
static const int NID_X9_62_prime239v3;
static const int NID_X9_62_prime256v1;
static const int NID_secp112r1;
static const int NID_secp112r2;
static const int NID_secp128r1;
static const int NID_secp128r2;
static const int NID_secp160k1;
static const int NID_secp160r1;
static const int NID_secp160r2;
static const int NID_sect163k1;
static const int NID_sect163r1;
static const int NID_sect163r2;
static const int NID_secp192k1;
static const int NID_secp224k1;
static const int NID_secp224r1;
static const int NID_secp256k1;
static const int NID_secp384r1;
static const int NID_secp521r1;
static const int NID_sect113r1;
static const int NID_sect113r2;
static const int NID_sect131r1;
static const int NID_sect131r2;
static const int NID_sect193r1;
static const int NID_sect193r2;
static const int NID_sect233k1;
static const int NID_sect233r1;
static const int NID_sect239k1;
static const int NID_sect283k1;
static const int NID_sect283r1;
static const int NID_sect409k1;
static const int NID_sect409r1;
static const int NID_sect571k1;
static const int NID_sect571r1;
static const int NID_wap_wsg_idm_ecid_wtls1;
static const int NID_wap_wsg_idm_ecid_wtls3;
static const int NID_wap_wsg_idm_ecid_wtls4;
static const int NID_wap_wsg_idm_ecid_wtls5;
static const int NID_wap_wsg_idm_ecid_wtls6;
static const int NID_wap_wsg_idm_ecid_wtls7;
static const int NID_wap_wsg_idm_ecid_wtls8;
static const int NID_wap_wsg_idm_ecid_wtls9;
static const int NID_wap_wsg_idm_ecid_wtls10;
static const int NID_wap_wsg_idm_ecid_wtls11;
static const int NID_wap_wsg_idm_ecid_wtls12;
static const int NID_ipsec3;
static const int NID_ipsec4;
static const char *const SN_X9_62_c2pnb163v1;
static const char *const SN_X9_62_c2pnb163v2;
static const char *const SN_X9_62_c2pnb163v3;
static const char *const SN_X9_62_c2pnb176v1;
static const char *const SN_X9_62_c2tnb191v1;
static const char *const SN_X9_62_c2tnb191v2;
static const char *const SN_X9_62_c2tnb191v3;
static const char *const SN_X9_62_c2onb191v4;
static const char *const SN_X9_62_c2onb191v5;
static const char *const SN_X9_62_c2pnb208w1;
static const char *const SN_X9_62_c2tnb239v1;
static const char *const SN_X9_62_c2tnb239v2;
static const char *const SN_X9_62_c2tnb239v3;
static const char *const SN_X9_62_c2onb239v4;
static const char *const SN_X9_62_c2onb239v5;
static const char *const SN_X9_62_c2pnb272w1;
static const char *const SN_X9_62_c2pnb304w1;
static const char *const SN_X9_62_c2tnb359v1;
static const char *const SN_X9_62_c2pnb368w1;
static const char *const SN_X9_62_c2tnb431r1;
static const char *const SN_X9_62_prime192v1;
static const char *const SN_X9_62_prime192v2;
static const char *const SN_X9_62_prime192v3;
static const char *const SN_X9_62_prime239v1;
static const char *const SN_X9_62_prime239v2;
static const char *const SN_X9_62_prime239v3;
static const char *const SN_X9_62_prime256v1;
static const char *const SN_secp112r1;
static const char *const SN_secp112r2;
static const char *const SN_secp128r1;
static const char *const SN_secp128r2;
static const char *const SN_secp160k1;
static const char *const SN_secp160r1;
static const char *const SN_secp160r2;
static const char *const SN_sect163k1;
static const char *const SN_sect163r1;
static const char *const SN_sect163r2;
static const char *const SN_secp192k1;
static const char *const SN_secp224k1;
static const char *const SN_secp224r1;
static const char *const SN_secp256k1;
static const char *const SN_secp384r1;
static const char *const SN_secp521r1;
static const char *const SN_sect113r1;
static const char *const SN_sect113r2;
static const char *const SN_sect131r1;
static const char *const SN_sect131r2;
static const char *const SN_sect193r1;
static const char *const SN_sect193r2;
static const char *const SN_sect233k1;
static const char *const SN_sect233r1;
static const char *const SN_sect239k1;
static const char *const SN_sect283k1;
static const char *const SN_sect283r1;
static const char *const SN_sect409k1;
static const char *const SN_sect409r1;
static const char *const SN_sect571k1;
static const char *const SN_sect571r1;
static const char *const SN_wap_wsg_idm_ecid_wtls1;
static const char *const SN_wap_wsg_idm_ecid_wtls3;
static const char *const SN_wap_wsg_idm_ecid_wtls4;
static const char *const SN_wap_wsg_idm_ecid_wtls5;
static const char *const SN_wap_wsg_idm_ecid_wtls6;
static const char *const SN_wap_wsg_idm_ecid_wtls7;
static const char *const SN_wap_wsg_idm_ecid_wtls8;
static const char *const SN_wap_wsg_idm_ecid_wtls9;
static const char *const SN_wap_wsg_idm_ecid_wtls10;
static const char *const SN_wap_wsg_idm_ecid_wtls11;
static const char *const SN_wap_wsg_idm_ecid_wtls12;
static const char *const SN_ipsec3;
static const char *const SN_ipsec4;
"""

FUNCTIONS = """
"""

MACROS = """
"""

CUSTOMIZATIONS = """
// OpenSSL 0.9.8g+
#if OPENSSL_VERSION_NUMBER >= 0x0090807fL
static const long Cryptography_HAS_ECDSA_SHA2_NIDS = 1;
#else
static const long Cryptography_HAS_ECDSA_SHA2_NIDS = 0;
static const int NID_ecdsa_with_SHA224 = 0;
static const int NID_ecdsa_with_SHA256 = 0;
static const int NID_ecdsa_with_SHA384 = 0;
static const int NID_ecdsa_with_SHA512 = 0;
#endif
"""

CONDITIONAL_NAMES = {
    "Cryptography_HAS_ECDSA_SHA2_NIDS": [
        "NID_ecdsa_with_SHA224",
        "NID_ecdsa_with_SHA256",
        "NID_ecdsa_with_SHA384",
        "NID_ecdsa_with_SHA512",
    ],
}

########NEW FILE########
__FILENAME__ = objects
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/objects.h>
"""

TYPES = """
"""

FUNCTIONS = """
ASN1_OBJECT *OBJ_nid2obj(int);
const char *OBJ_nid2ln(int);
const char *OBJ_nid2sn(int);
int OBJ_obj2nid(const ASN1_OBJECT *);
int OBJ_ln2nid(const char *);
int OBJ_sn2nid(const char *);
int OBJ_txt2nid(const char *);
ASN1_OBJECT *OBJ_txt2obj(const char *, int);
int OBJ_obj2txt(char *, int, const ASN1_OBJECT *, int);
int OBJ_cmp(const ASN1_OBJECT *, const ASN1_OBJECT *);
ASN1_OBJECT *OBJ_dup(const ASN1_OBJECT *);
int OBJ_create(const char *, const char *, const char *);
void OBJ_cleanup(void);
"""

MACROS = """
"""

CUSTOMIZATIONS = """
"""

CONDITIONAL_NAMES = {}

########NEW FILE########
__FILENAME__ = opensslv
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/opensslv.h>
"""

TYPES = """
/* Note that these will be resolved when cryptography is compiled and are NOT
   guaranteed to be the version that it actually loads. */
static const int OPENSSL_VERSION_NUMBER;
static const char *const OPENSSL_VERSION_TEXT;
"""

FUNCTIONS = """
"""

MACROS = """
"""

CUSTOMIZATIONS = """
"""

CONDITIONAL_NAMES = {}

########NEW FILE########
__FILENAME__ = osrandom_engine
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#ifdef _WIN32
#include <Wincrypt.h>
#else
#include <fcntl.h>
#include <unistd.h>
#endif
"""

TYPES = """
static const char *const Cryptography_osrandom_engine_name;
static const char *const Cryptography_osrandom_engine_id;
"""

FUNCTIONS = """
int Cryptography_add_osrandom_engine(void);
"""

MACROS = """
"""

WIN32_CUSTOMIZATIONS = """
static HCRYPTPROV hCryptProv = 0;

static int osrandom_init(ENGINE *e) {
    if (hCryptProv > 0) {
        return 1;
    }
    if (CryptAcquireContext(&hCryptProv, NULL, NULL,
                            PROV_RSA_FULL, CRYPT_VERIFYCONTEXT)) {
        return 1;
    } else {
        return 0;
    }
}

static int osrandom_rand_bytes(unsigned char *buffer, int size) {
    if (hCryptProv == 0) {
        return 0;
    }

    if (!CryptGenRandom(hCryptProv, (DWORD)size, buffer)) {
        ERR_put_error(
            ERR_LIB_RAND, 0, ERR_R_RAND_LIB, "osrandom_engine.py", 0
        );
        return 0;
    }
    return 1;
}

static int osrandom_finish(ENGINE *e) {
    if (CryptReleaseContext(hCryptProv, 0)) {
        hCryptProv = 0;
        return 1;
    } else {
        return 0;
    }
}

static int osrandom_rand_status(void) {
    if (hCryptProv == 0) {
        return 0;
    } else {
        return 1;
    }
}
"""

POSIX_CUSTOMIZATIONS = """
static int urandom_fd = -1;

static int osrandom_finish(ENGINE *e);

static int osrandom_init(ENGINE *e) {
    if (urandom_fd > -1) {
        return 1;
    }
    urandom_fd = open("/dev/urandom", O_RDONLY);
    if (urandom_fd > -1) {
        int flags = fcntl(urandom_fd, F_GETFD);
        if (flags == -1) {
            osrandom_finish(e);
            return 0;
        } else if (fcntl(urandom_fd, F_SETFD, flags | FD_CLOEXEC) == -1) {
            osrandom_finish(e);
            return 0;
        }
        return 1;
    } else {
        return 0;
    }
}

static int osrandom_rand_bytes(unsigned char *buffer, int size) {
    ssize_t n;
    while (size > 0) {
        do {
            n = read(urandom_fd, buffer, (size_t)size);
        } while (n < 0 && errno == EINTR);
        if (n <= 0) {
            ERR_put_error(
                ERR_LIB_RAND, 0, ERR_R_RAND_LIB, "osrandom_engine.py", 0
            );
            return 0;
        }
        buffer += n;
        size -= n;
    }
    return 1;
}

static int osrandom_finish(ENGINE *e) {
    int n;
    do {
        n = close(urandom_fd);
    } while (n < 0 && errno == EINTR);
    urandom_fd = -1;
    if (n < 0) {
        return 0;
    } else {
        return 1;
    }
}

static int osrandom_rand_status(void) {
    if (urandom_fd == -1) {
        return 0;
    } else {
        return 1;
    }
}
"""

CUSTOMIZATIONS = """
static const char *Cryptography_osrandom_engine_id = "osrandom";
static const char *Cryptography_osrandom_engine_name = "osrandom_engine";

#if defined(_WIN32)
%(WIN32_CUSTOMIZATIONS)s
#else
%(POSIX_CUSTOMIZATIONS)s
#endif

/* This replicates the behavior of the OpenSSL FIPS RNG, which returns a
   -1 in the event that there is an error when calling RAND_pseudo_bytes. */
static int osrandom_pseudo_rand_bytes(unsigned char *buffer, int size) {
    int res = osrandom_rand_bytes(buffer, size);
    if (res == 0) {
        return -1;
    } else {
        return res;
    }
}

static RAND_METHOD osrandom_rand = {
    NULL,
    osrandom_rand_bytes,
    NULL,
    NULL,
    osrandom_pseudo_rand_bytes,
    osrandom_rand_status,
};

/* Returns 1 if successfully added, 2 if engine has previously been added,
   and 0 for error. */
int Cryptography_add_osrandom_engine(void) {
    ENGINE *e;
    e = ENGINE_by_id(Cryptography_osrandom_engine_id);
    if (e != NULL) {
        ENGINE_free(e);
        return 2;
    } else {
        ERR_clear_error();
    }

    e = ENGINE_new();
    if (e == NULL) {
        return 0;
    }
    if(!ENGINE_set_id(e, Cryptography_osrandom_engine_id) ||
            !ENGINE_set_name(e, Cryptography_osrandom_engine_name) ||
            !ENGINE_set_RAND(e, &osrandom_rand) ||
            !ENGINE_set_init_function(e, osrandom_init) ||
            !ENGINE_set_finish_function(e, osrandom_finish)) {
        ENGINE_free(e);
        return 0;
    }
    if (!ENGINE_add(e)) {
        ENGINE_free(e);
        return 0;
    }
    if (!ENGINE_free(e)) {
        return 0;
    }

    return 1;
}
""" % {
    "WIN32_CUSTOMIZATIONS": WIN32_CUSTOMIZATIONS,
    "POSIX_CUSTOMIZATIONS": POSIX_CUSTOMIZATIONS,
}

CONDITIONAL_NAMES = {}

########NEW FILE########
__FILENAME__ = pem
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/pem.h>
"""

TYPES = """
typedef int pem_password_cb(char *buf, int size, int rwflag, void *userdata);
"""

FUNCTIONS = """
X509 *PEM_read_bio_X509(BIO *, X509 **, pem_password_cb *, void *);
int PEM_write_bio_X509(BIO *, X509 *);

int PEM_write_bio_PrivateKey(BIO *, EVP_PKEY *, const EVP_CIPHER *,
                             unsigned char *, int, pem_password_cb *, void *);

EVP_PKEY *PEM_read_bio_PrivateKey(BIO *, EVP_PKEY **, pem_password_cb *,
                                 void *);

int PEM_write_bio_PKCS8PrivateKey(BIO *, EVP_PKEY *, const EVP_CIPHER *,
                                  char *, int, pem_password_cb *, void *);
int PEM_write_bio_PKCS8PrivateKey_nid(BIO *, EVP_PKEY *, int, char *, int,
                                      pem_password_cb *, void *);

int i2d_PKCS8PrivateKey_bio(BIO *, EVP_PKEY *, const EVP_CIPHER *,
                            char *, int, pem_password_cb *, void *);
int i2d_PKCS8PrivateKey_nid_bio(BIO *, EVP_PKEY *, int,
                                char *, int, pem_password_cb *, void *);

EVP_PKEY *d2i_PKCS8PrivateKey_bio(BIO *, EVP_PKEY **, pem_password_cb *,
                                  void *);

int PEM_write_bio_X509_REQ(BIO *, X509_REQ *);

X509_REQ *PEM_read_bio_X509_REQ(BIO *, X509_REQ **, pem_password_cb *, void *);

X509_CRL *PEM_read_bio_X509_CRL(BIO *, X509_CRL **, pem_password_cb *, void *);

int PEM_write_bio_X509_CRL(BIO *, X509_CRL *);

PKCS7 *PEM_read_bio_PKCS7(BIO *, PKCS7 **, pem_password_cb *, void *);
DH *PEM_read_bio_DHparams(BIO *, DH **, pem_password_cb *, void *);

DSA *PEM_read_bio_DSAPrivateKey(BIO *, DSA **, pem_password_cb *, void *);

RSA *PEM_read_bio_RSAPrivateKey(BIO *, RSA **, pem_password_cb *, void *);

int PEM_write_bio_DSAPrivateKey(BIO *, DSA *, const EVP_CIPHER *,
                                unsigned char *, int,
                                pem_password_cb *, void *);

int PEM_write_bio_RSAPrivateKey(BIO *, RSA *, const EVP_CIPHER *,
                                unsigned char *, int,
                                pem_password_cb *, void *);

DSA *PEM_read_bio_DSA_PUBKEY(BIO *, DSA **, pem_password_cb *, void *);

RSA *PEM_read_bio_RSAPublicKey(BIO *, RSA **, pem_password_cb *, void *);

int PEM_write_bio_DSA_PUBKEY(BIO *, DSA *);

int PEM_write_bio_RSAPublicKey(BIO *, const RSA *);

EVP_PKEY *PEM_read_bio_PUBKEY(BIO *, EVP_PKEY **, pem_password_cb *, void *);
int PEM_write_bio_PUBKEY(BIO *, EVP_PKEY *);
"""

MACROS = """
"""

CUSTOMIZATIONS = """
"""

CONDITIONAL_NAMES = {}

########NEW FILE########
__FILENAME__ = pkcs12
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/pkcs12.h>
"""

TYPES = """
typedef ... PKCS12;
"""

FUNCTIONS = """
void PKCS12_free(PKCS12 *);

PKCS12 *d2i_PKCS12_bio(BIO *, PKCS12 **);
int i2d_PKCS12_bio(BIO *, PKCS12 *);
"""

MACROS = """
int PKCS12_parse(PKCS12 *, const char *, EVP_PKEY **, X509 **,
                 Cryptography_STACK_OF_X509 **);
PKCS12 *PKCS12_create(char *, char *, EVP_PKEY *, X509 *,
                      Cryptography_STACK_OF_X509 *, int, int, int, int, int);
"""

CUSTOMIZATIONS = """
"""

CONDITIONAL_NAMES = {}

########NEW FILE########
__FILENAME__ = pkcs7
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/pkcs7.h>
"""

TYPES = """
typedef struct {
    ASN1_OBJECT *type;
    ...;
} PKCS7;
"""

FUNCTIONS = """
void PKCS7_free(PKCS7 *);
"""

MACROS = """
int PKCS7_type_is_signed(PKCS7 *);
int PKCS7_type_is_enveloped(PKCS7 *);
int PKCS7_type_is_signedAndEnveloped(PKCS7 *);
int PKCS7_type_is_data(PKCS7 *);
"""

CUSTOMIZATIONS = """
"""

CONDITIONAL_NAMES = {}

########NEW FILE########
__FILENAME__ = rand
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/rand.h>
"""

TYPES = """
"""

FUNCTIONS = """
void ERR_load_RAND_strings(void);
void RAND_seed(const void *, int);
void RAND_add(const void *, int, double);
int RAND_status(void);
int RAND_egd(const char *);
int RAND_egd_bytes(const char *, int);
int RAND_query_egd_bytes(const char *, unsigned char *, int);
const char *RAND_file_name(char *, size_t);
int RAND_load_file(const char *, long);
int RAND_write_file(const char *);
void RAND_cleanup(void);
int RAND_bytes(unsigned char *, int);
int RAND_pseudo_bytes(unsigned char *, int);
"""

MACROS = """
"""

CUSTOMIZATIONS = """
"""

CONDITIONAL_NAMES = {}

########NEW FILE########
__FILENAME__ = rsa
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/rsa.h>
"""

TYPES = """
typedef struct rsa_st {
    BIGNUM *n;
    BIGNUM *e;
    BIGNUM *d;
    BIGNUM *p;
    BIGNUM *q;
    BIGNUM *dmp1;
    BIGNUM *dmq1;
    BIGNUM *iqmp;
    ...;
} RSA;
typedef ... BN_GENCB;
static const int RSA_PKCS1_PADDING;
static const int RSA_SSLV23_PADDING;
static const int RSA_NO_PADDING;
static const int RSA_PKCS1_OAEP_PADDING;
static const int RSA_X931_PADDING;
static const int RSA_PKCS1_PSS_PADDING;
static const int RSA_F4;

static const int Cryptography_HAS_PSS_PADDING;
static const int Cryptography_HAS_MGF1_MD;
"""

FUNCTIONS = """
RSA *RSA_new(void);
void RSA_free(RSA *);
int RSA_size(const RSA *);
int RSA_generate_key_ex(RSA *, int, BIGNUM *, BN_GENCB *);
int RSA_check_key(const RSA *);
RSA *RSAPublicKey_dup(RSA *);
int RSA_blinding_on(RSA *, BN_CTX *);
void RSA_blinding_off(RSA *);
int RSA_public_encrypt(int, const unsigned char *, unsigned char *,
                       RSA *, int);
int RSA_private_encrypt(int, const unsigned char *, unsigned char *,
                        RSA *, int);
int RSA_public_decrypt(int, const unsigned char *, unsigned char *,
                       RSA *, int);
int RSA_private_decrypt(int, const unsigned char *, unsigned char *,
                        RSA *, int);
int RSA_print(BIO *, const RSA *, int);
int RSA_verify_PKCS1_PSS(RSA *, const unsigned char *, const EVP_MD *,
                         const unsigned char *, int);
int RSA_padding_add_PKCS1_PSS(RSA *, unsigned char *, const unsigned char *,
                              const EVP_MD *, int);
int RSA_padding_add_PKCS1_OAEP(unsigned char *, int, const unsigned char *,
                               int, const unsigned char *, int);
int RSA_padding_check_PKCS1_OAEP(unsigned char *, int, const unsigned char *,
                                 int, int, const unsigned char *, int);
"""

MACROS = """
int EVP_PKEY_CTX_set_rsa_padding(EVP_PKEY_CTX *, int);
int EVP_PKEY_CTX_set_rsa_pss_saltlen(EVP_PKEY_CTX *, int);
int EVP_PKEY_CTX_set_rsa_mgf1_md(EVP_PKEY_CTX *, EVP_MD *);
"""

CUSTOMIZATIONS = """
#if OPENSSL_VERSION_NUMBER >= 0x10000000
static const long Cryptography_HAS_PSS_PADDING = 1;
#else
// see evp.py for the definition of Cryptography_HAS_PKEY_CTX
static const long Cryptography_HAS_PSS_PADDING = 0;
int (*EVP_PKEY_CTX_set_rsa_padding)(EVP_PKEY_CTX *, int) = NULL;
int (*EVP_PKEY_CTX_set_rsa_pss_saltlen)(EVP_PKEY_CTX *, int) = NULL;
static const long RSA_PKCS1_PSS_PADDING = 0;
#endif
#if OPENSSL_VERSION_NUMBER >= 0x1000100f
static const long Cryptography_HAS_MGF1_MD = 1;
#else
static const long Cryptography_HAS_MGF1_MD = 0;
int (*EVP_PKEY_CTX_set_rsa_mgf1_md)(EVP_PKEY_CTX *, EVP_MD *) = NULL;
#endif
"""

CONDITIONAL_NAMES = {
    "Cryptography_HAS_PKEY_CTX": [
        "EVP_PKEY_CTX_set_rsa_padding",
        "EVP_PKEY_CTX_set_rsa_pss_saltlen",
    ],
    "Cryptography_HAS_PSS_PADDING": [
        "RSA_PKCS1_PSS_PADDING",
    ],
    "Cryptography_HAS_MGF1_MD": [
        "EVP_PKEY_CTX_set_rsa_mgf1_md",
    ],
}

########NEW FILE########
__FILENAME__ = ssl
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/ssl.h>

typedef STACK_OF(SSL_CIPHER) Cryptography_STACK_OF_SSL_CIPHER;
"""

TYPES = """
/*
 * Internally invented symbols to tell which versions of SSL/TLS are supported.
*/
static const long Cryptography_HAS_SSL2;
static const long Cryptography_HAS_TLSv1_1;
static const long Cryptography_HAS_TLSv1_2;
static const long Cryptography_HAS_SECURE_RENEGOTIATION;

/* Internally invented symbol to tell us if SNI is supported */
static const long Cryptography_HAS_TLSEXT_HOSTNAME;

/* Internally invented symbol to tell us if SSL_MODE_RELEASE_BUFFERS is
 * supported
 */
static const long Cryptography_HAS_RELEASE_BUFFERS;

/* Internally invented symbol to tell us if SSL_OP_NO_COMPRESSION is
 * supported
 */
static const long Cryptography_HAS_OP_NO_COMPRESSION;

static const long Cryptography_HAS_SSL_OP_MSIE_SSLV2_RSA_PADDING;
static const long Cryptography_HAS_SSL_SET_SSL_CTX;
static const long Cryptography_HAS_SSL_OP_NO_TICKET;
static const long Cryptography_HAS_NETBSD_D1_METH;
static const long Cryptography_HAS_NEXTPROTONEG;

static const long SSL_FILETYPE_PEM;
static const long SSL_FILETYPE_ASN1;
static const long SSL_ERROR_NONE;
static const long SSL_ERROR_ZERO_RETURN;
static const long SSL_ERROR_WANT_READ;
static const long SSL_ERROR_WANT_WRITE;
static const long SSL_ERROR_WANT_X509_LOOKUP;
static const long SSL_ERROR_SYSCALL;
static const long SSL_ERROR_SSL;
static const long SSL_SENT_SHUTDOWN;
static const long SSL_RECEIVED_SHUTDOWN;
static const long SSL_OP_NO_SSLv2;
static const long SSL_OP_NO_SSLv3;
static const long SSL_OP_NO_TLSv1;
static const long SSL_OP_NO_TLSv1_1;
static const long SSL_OP_NO_TLSv1_2;
static const long SSL_OP_NO_COMPRESSION;
static const long SSL_OP_SINGLE_DH_USE;
static const long SSL_OP_EPHEMERAL_RSA;
static const long SSL_OP_MICROSOFT_SESS_ID_BUG;
static const long SSL_OP_NETSCAPE_CHALLENGE_BUG;
static const long SSL_OP_NETSCAPE_REUSE_CIPHER_CHANGE_BUG;
static const long SSL_OP_SSLREF2_REUSE_CERT_TYPE_BUG;
static const long SSL_OP_MICROSOFT_BIG_SSLV3_BUFFER;
static const long SSL_OP_MSIE_SSLV2_RSA_PADDING;
static const long SSL_OP_SSLEAY_080_CLIENT_DH_BUG;
static const long SSL_OP_TLS_D5_BUG;
static const long SSL_OP_TLS_BLOCK_PADDING_BUG;
static const long SSL_OP_DONT_INSERT_EMPTY_FRAGMENTS;
static const long SSL_OP_CIPHER_SERVER_PREFERENCE;
static const long SSL_OP_TLS_ROLLBACK_BUG;
static const long SSL_OP_PKCS1_CHECK_1;
static const long SSL_OP_PKCS1_CHECK_2;
static const long SSL_OP_NETSCAPE_CA_DN_BUG;
static const long SSL_OP_NETSCAPE_DEMO_CIPHER_CHANGE_BUG;
static const long SSL_OP_NO_QUERY_MTU;
static const long SSL_OP_COOKIE_EXCHANGE;
static const long SSL_OP_NO_TICKET;
static const long SSL_OP_ALL;
static const long SSL_OP_SINGLE_ECDH_USE;
static const long SSL_OP_ALLOW_UNSAFE_LEGACY_RENEGOTIATION;
static const long SSL_OP_LEGACY_SERVER_CONNECT;
static const long SSL_VERIFY_PEER;
static const long SSL_VERIFY_FAIL_IF_NO_PEER_CERT;
static const long SSL_VERIFY_CLIENT_ONCE;
static const long SSL_VERIFY_NONE;
static const long SSL_SESS_CACHE_OFF;
static const long SSL_SESS_CACHE_CLIENT;
static const long SSL_SESS_CACHE_SERVER;
static const long SSL_SESS_CACHE_BOTH;
static const long SSL_SESS_CACHE_NO_AUTO_CLEAR;
static const long SSL_SESS_CACHE_NO_INTERNAL_LOOKUP;
static const long SSL_SESS_CACHE_NO_INTERNAL_STORE;
static const long SSL_SESS_CACHE_NO_INTERNAL;
static const long SSL_ST_CONNECT;
static const long SSL_ST_ACCEPT;
static const long SSL_ST_MASK;
static const long SSL_ST_INIT;
static const long SSL_ST_BEFORE;
static const long SSL_ST_OK;
static const long SSL_ST_RENEGOTIATE;
static const long SSL_CB_LOOP;
static const long SSL_CB_EXIT;
static const long SSL_CB_READ;
static const long SSL_CB_WRITE;
static const long SSL_CB_ALERT;
static const long SSL_CB_READ_ALERT;
static const long SSL_CB_WRITE_ALERT;
static const long SSL_CB_ACCEPT_LOOP;
static const long SSL_CB_ACCEPT_EXIT;
static const long SSL_CB_CONNECT_LOOP;
static const long SSL_CB_CONNECT_EXIT;
static const long SSL_CB_HANDSHAKE_START;
static const long SSL_CB_HANDSHAKE_DONE;
static const long SSL_MODE_RELEASE_BUFFERS;
static const long SSL_MODE_ENABLE_PARTIAL_WRITE;
static const long SSL_MODE_ACCEPT_MOVING_WRITE_BUFFER;
static const long SSL_MODE_AUTO_RETRY;
static const long SSL3_RANDOM_SIZE;
typedef ... X509_STORE_CTX;
static const long X509_V_OK;
static const long X509_V_ERR_APPLICATION_VERIFICATION;
typedef ... SSL_METHOD;
typedef struct ssl_st {
    int version;
    int type;
    ...;
} SSL_CTX;

typedef struct {
    int master_key_length;
    unsigned char master_key[...];
    ...;
} SSL_SESSION;

typedef struct {
    unsigned char server_random[...];
    unsigned char client_random[...];
    ...;
} SSL3_STATE;

typedef struct {
    SSL3_STATE *s3;
    SSL_SESSION *session;
    int type;
    ...;
} SSL;

static const long TLSEXT_NAMETYPE_host_name;

typedef ... SSL_CIPHER;
typedef ... Cryptography_STACK_OF_SSL_CIPHER;
typedef ... COMP_METHOD;
"""

FUNCTIONS = """
void SSL_load_error_strings(void);
int SSL_library_init(void);

/*  SSL */
const char *SSL_state_string_long(const SSL *);
SSL_SESSION *SSL_get1_session(SSL *);
int SSL_set_session(SSL *, SSL_SESSION *);
int SSL_get_verify_mode(const SSL *);
void SSL_set_verify_depth(SSL *, int);
int SSL_get_verify_depth(const SSL *);
int (*SSL_get_verify_callback(const SSL *))(int, X509_STORE_CTX *);
void SSL_set_info_callback(SSL *ssl, void (*)(const SSL *, int, int));
void (*SSL_get_info_callback(const SSL *))(const SSL *, int, int);
SSL *SSL_new(SSL_CTX *);
void SSL_free(SSL *);
int SSL_set_fd(SSL *, int);
void SSL_set_bio(SSL *, BIO *, BIO *);
void SSL_set_connect_state(SSL *);
void SSL_set_accept_state(SSL *);
void SSL_set_shutdown(SSL *, int);
int SSL_get_shutdown(const SSL *);
int SSL_pending(const SSL *);
int SSL_write(SSL *, const void *, int);
int SSL_read(SSL *, void *, int);
X509 *SSL_get_peer_certificate(const SSL *);
int SSL_get_ex_data_X509_STORE_CTX_idx(void);

Cryptography_STACK_OF_X509 *SSL_get_peer_cert_chain(const SSL *);
Cryptography_STACK_OF_X509_NAME *SSL_get_client_CA_list(const SSL *);

int SSL_get_error(const SSL *, int);
int SSL_do_handshake(SSL *);
int SSL_shutdown(SSL *);
const char *SSL_get_cipher_list(const SSL *, int);
Cryptography_STACK_OF_SSL_CIPHER *SSL_get_ciphers(const SSL *);

const COMP_METHOD *SSL_get_current_compression(SSL *);
const COMP_METHOD *SSL_get_current_expansion(SSL *);
const char *SSL_COMP_get_name(const COMP_METHOD *);

/*  context */
void SSL_CTX_free(SSL_CTX *);
long SSL_CTX_set_timeout(SSL_CTX *, long);
int SSL_CTX_set_default_verify_paths(SSL_CTX *);
void SSL_CTX_set_verify(SSL_CTX *, int, int (*)(int, X509_STORE_CTX *));
void SSL_CTX_set_verify_depth(SSL_CTX *, int);
int (*SSL_CTX_get_verify_callback(const SSL_CTX *))(int, X509_STORE_CTX *);
int SSL_CTX_get_verify_mode(const SSL_CTX *);
int SSL_CTX_get_verify_depth(const SSL_CTX *);
int SSL_CTX_set_cipher_list(SSL_CTX *, const char *);
int SSL_CTX_load_verify_locations(SSL_CTX *, const char *, const char *);
void SSL_CTX_set_default_passwd_cb(SSL_CTX *, pem_password_cb *);
void SSL_CTX_set_default_passwd_cb_userdata(SSL_CTX *, void *);
int SSL_CTX_use_certificate(SSL_CTX *, X509 *);
int SSL_CTX_use_certificate_file(SSL_CTX *, const char *, int);
int SSL_CTX_use_certificate_chain_file(SSL_CTX *, const char *);
int SSL_CTX_use_PrivateKey(SSL_CTX *, EVP_PKEY *);
int SSL_CTX_use_PrivateKey_file(SSL_CTX *, const char *, int);
void SSL_CTX_set_cert_store(SSL_CTX *, X509_STORE *);
X509_STORE *SSL_CTX_get_cert_store(const SSL_CTX *);
int SSL_CTX_add_client_CA(SSL_CTX *, X509 *);

void SSL_CTX_set_client_CA_list(SSL_CTX *, Cryptography_STACK_OF_X509_NAME *);


/*  X509_STORE_CTX */
int X509_STORE_CTX_get_error(X509_STORE_CTX *);
void X509_STORE_CTX_set_error(X509_STORE_CTX *, int);
int X509_STORE_CTX_get_error_depth(X509_STORE_CTX *);
X509 *X509_STORE_CTX_get_current_cert(X509_STORE_CTX *);
int X509_STORE_CTX_set_ex_data(X509_STORE_CTX *, int, void *);
void *X509_STORE_CTX_get_ex_data(X509_STORE_CTX *, int);


/*  SSL_SESSION */
void SSL_SESSION_free(SSL_SESSION *);

/* Information about actually used cipher */
const char *SSL_CIPHER_get_name(const SSL_CIPHER *);
int SSL_CIPHER_get_bits(const SSL_CIPHER *, int *);
char *SSL_CIPHER_get_version(const SSL_CIPHER *);

size_t SSL_get_finished(const SSL *, void *, size_t);
size_t SSL_get_peer_finished(const SSL *, void *, size_t);
"""

MACROS = """
unsigned long SSL_set_mode(SSL *, unsigned long);
unsigned long SSL_get_mode(SSL *);

unsigned long SSL_set_options(SSL *, unsigned long);
unsigned long SSL_get_options(SSL *);

int SSL_want_read(const SSL *);
int SSL_want_write(const SSL *);

long SSL_total_renegotiations(SSL *);
long SSL_get_secure_renegotiation_support(SSL *);

/* Defined as unsigned long because SSL_OP_ALL is greater than signed 32-bit
   and Windows defines long as 32-bit. */
unsigned long SSL_CTX_set_options(SSL_CTX *, unsigned long);
unsigned long SSL_CTX_get_options(SSL_CTX *);
unsigned long SSL_CTX_set_mode(SSL_CTX *, unsigned long);
unsigned long SSL_CTX_get_mode(SSL_CTX *);
unsigned long SSL_CTX_set_session_cache_mode(SSL_CTX *, unsigned long);
unsigned long SSL_CTX_get_session_cache_mode(SSL_CTX *);
unsigned long SSL_CTX_set_tmp_dh(SSL_CTX *, DH *);
unsigned long SSL_CTX_set_tmp_ecdh(SSL_CTX *, EC_KEY *);
unsigned long SSL_CTX_add_extra_chain_cert(SSL_CTX *, X509 *);

/*- These aren't macros these functions are all const X on openssl > 1.0.x -*/

/*  methods */

/* SSLv2 support is compiled out of some versions of OpenSSL.  These will
 * get special support when we generate the bindings so that if they are
 * available they will be wrapped, but if they are not they won't cause
 * problems (like link errors).
 */
const SSL_METHOD *SSLv2_method(void);
const SSL_METHOD *SSLv2_server_method(void);
const SSL_METHOD *SSLv2_client_method(void);

/*
 * TLSv1_1 and TLSv1_2 are recent additions.  Only sufficiently new versions of
 * OpenSSL support them.
 */
const SSL_METHOD *TLSv1_1_method(void);
const SSL_METHOD *TLSv1_1_server_method(void);
const SSL_METHOD *TLSv1_1_client_method(void);

const SSL_METHOD *TLSv1_2_method(void);
const SSL_METHOD *TLSv1_2_server_method(void);
const SSL_METHOD *TLSv1_2_client_method(void);

const SSL_METHOD *SSLv3_method(void);
const SSL_METHOD *SSLv3_server_method(void);
const SSL_METHOD *SSLv3_client_method(void);

const SSL_METHOD *TLSv1_method(void);
const SSL_METHOD *TLSv1_server_method(void);
const SSL_METHOD *TLSv1_client_method(void);

const SSL_METHOD *DTLSv1_method(void);
const SSL_METHOD *DTLSv1_server_method(void);
const SSL_METHOD *DTLSv1_client_method(void);

const SSL_METHOD *SSLv23_method(void);
const SSL_METHOD *SSLv23_server_method(void);
const SSL_METHOD *SSLv23_client_method(void);

/*- These aren't macros these arguments are all const X on openssl > 1.0.x -*/
SSL_CTX *SSL_CTX_new(SSL_METHOD *);
long SSL_CTX_get_timeout(const SSL_CTX *);

const SSL_CIPHER *SSL_get_current_cipher(const SSL *);

/* SNI APIs were introduced in OpenSSL 1.0.0.  To continue to support
 * earlier versions some special handling of these is necessary.
 */
const char *SSL_get_servername(const SSL *, const int);
void SSL_set_tlsext_host_name(SSL *, char *);
void SSL_CTX_set_tlsext_servername_callback(
    SSL_CTX *,
    int (*)(const SSL *, int *, void *));

long SSL_session_reused(SSL *);

/* The following were macros in 0.9.8e. Once we drop support for RHEL/CentOS 5
   we should move these back to FUNCTIONS. */
void SSL_CTX_set_info_callback(SSL_CTX *, void (*)(const SSL *, int, int));
void (*SSL_CTX_get_info_callback(SSL_CTX *))(const SSL *, int, int);
/* This function does not exist in 0.9.8e. Once we drop support for
   RHEL/CentOS 5 this can be moved back to FUNCTIONS. */
SSL_CTX *SSL_set_SSL_CTX(SSL *, SSL_CTX *);

const SSL_METHOD* Cryptography_SSL_CTX_get_method(const SSL_CTX*);

/* NPN APIs were introduced in OpenSSL 1.0.1.  To continue to support earlier
 * versions some special handling of these is necessary.
 */
void SSL_CTX_set_next_protos_advertised_cb(SSL_CTX *,
                                           int (*)(SSL *,
                                                   const unsigned char **,
                                                   unsigned int *,
                                                   void *),
                                           void *);
void SSL_CTX_set_next_proto_select_cb(SSL_CTX *,
                                      int (*)(SSL *,
                                              unsigned char **,
                                              unsigned char *,
                                              const unsigned char *,
                                              unsigned int,
                                              void *),
                                      void *);
int SSL_select_next_proto(unsigned char **, unsigned char *,
                          const unsigned char *, unsigned int,
                          const unsigned char *, unsigned int);
void SSL_get0_next_proto_negotiated(const SSL *,
                                    const unsigned char **, unsigned *);

int sk_SSL_CIPHER_num(Cryptography_STACK_OF_SSL_CIPHER *);
SSL_CIPHER *sk_SSL_CIPHER_value(Cryptography_STACK_OF_SSL_CIPHER *, int);
"""

CUSTOMIZATIONS = """
/** Secure renegotiation is supported in OpenSSL >= 0.9.8m
 *  But some Linux distributions have back ported some features.
 */
#ifndef SSL_OP_ALLOW_UNSAFE_LEGACY_RENEGOTIATION
static const long Cryptography_HAS_SECURE_RENEGOTIATION = 0;
long (*SSL_get_secure_renegotiation_support)(SSL *) = NULL;
const long SSL_OP_ALLOW_UNSAFE_LEGACY_RENEGOTIATION = 0;
const long SSL_OP_LEGACY_SERVER_CONNECT = 0;
#else
static const long Cryptography_HAS_SECURE_RENEGOTIATION = 1;
#endif
#ifdef OPENSSL_NO_SSL2
static const long Cryptography_HAS_SSL2 = 0;
SSL_METHOD* (*SSLv2_method)(void) = NULL;
SSL_METHOD* (*SSLv2_client_method)(void) = NULL;
SSL_METHOD* (*SSLv2_server_method)(void) = NULL;
#else
static const long Cryptography_HAS_SSL2 = 1;
#endif

#ifdef SSL_CTRL_SET_TLSEXT_HOSTNAME
static const long Cryptography_HAS_TLSEXT_HOSTNAME = 1;
#else
static const long Cryptography_HAS_TLSEXT_HOSTNAME = 0;
void (*SSL_set_tlsext_host_name)(SSL *, char *) = NULL;
const char* (*SSL_get_servername)(const SSL *, const int) = NULL;
void (*SSL_CTX_set_tlsext_servername_callback)(
    SSL_CTX *,
    int (*)(const SSL *, int *, void *)) = NULL;
#endif

#ifdef SSL_MODE_RELEASE_BUFFERS
static const long Cryptography_HAS_RELEASE_BUFFERS = 1;
#else
static const long Cryptography_HAS_RELEASE_BUFFERS = 0;
const long SSL_MODE_RELEASE_BUFFERS = 0;
#endif

#ifdef SSL_OP_NO_COMPRESSION
static const long Cryptography_HAS_OP_NO_COMPRESSION = 1;
#else
static const long Cryptography_HAS_OP_NO_COMPRESSION = 0;
const long SSL_OP_NO_COMPRESSION = 0;
#endif

#ifdef SSL_OP_NO_TLSv1_1
static const long Cryptography_HAS_TLSv1_1 = 1;
#else
static const long Cryptography_HAS_TLSv1_1 = 0;
static const long SSL_OP_NO_TLSv1_1 = 0;
SSL_METHOD* (*TLSv1_1_method)(void) = NULL;
SSL_METHOD* (*TLSv1_1_client_method)(void) = NULL;
SSL_METHOD* (*TLSv1_1_server_method)(void) = NULL;
#endif

#ifdef SSL_OP_NO_TLSv1_2
static const long Cryptography_HAS_TLSv1_2 = 1;
#else
static const long Cryptography_HAS_TLSv1_2 = 0;
static const long SSL_OP_NO_TLSv1_2 = 0;
SSL_METHOD* (*TLSv1_2_method)(void) = NULL;
SSL_METHOD* (*TLSv1_2_client_method)(void) = NULL;
SSL_METHOD* (*TLSv1_2_server_method)(void) = NULL;
#endif

#ifdef SSL_OP_MSIE_SSLV2_RSA_PADDING
static const long Cryptography_HAS_SSL_OP_MSIE_SSLV2_RSA_PADDING = 1;
#else
static const long Cryptography_HAS_SSL_OP_MSIE_SSLV2_RSA_PADDING = 0;
const long SSL_OP_MSIE_SSLV2_RSA_PADDING = 0;
#endif

#ifdef OPENSSL_NO_EC
long (*SSL_CTX_set_tmp_ecdh)(SSL_CTX *, EC_KEY *) = NULL;
#endif

#ifdef SSL_OP_NO_TICKET
static const long Cryptography_HAS_SSL_OP_NO_TICKET = 1;
#else
static const long Cryptography_HAS_SSL_OP_NO_TICKET = 0;
const long SSL_OP_NO_TICKET = 0;
#endif

// OpenSSL 0.9.8f+
#if OPENSSL_VERSION_NUMBER >= 0x00908070L
static const long Cryptography_HAS_SSL_SET_SSL_CTX = 1;
#else
static const long Cryptography_HAS_SSL_SET_SSL_CTX = 0;
static const long TLSEXT_NAMETYPE_host_name = 0;
SSL_CTX *(*SSL_set_SSL_CTX)(SSL *, SSL_CTX *) = NULL;
#endif

/* NetBSD shipped without including d1_meth.c. This workaround checks to see
   if the version of NetBSD we're currently running on is old enough to
   have the bug and provides an empty implementation so we can link and
   then remove the function from the ffi object. */
#ifdef __NetBSD__
#  include <sys/param.h>
#  if (__NetBSD_Version__ < 699003800)
static const long Cryptography_HAS_NETBSD_D1_METH = 0;
const SSL_METHOD *DTLSv1_method(void) {
    return NULL;
}
#  else
static const long Cryptography_HAS_NETBSD_D1_METH = 1;
#  endif
#else
static const long Cryptography_HAS_NETBSD_D1_METH = 1;
#endif

// Workaround for #794 caused by cffi const** bug.
const SSL_METHOD* Cryptography_SSL_CTX_get_method(const SSL_CTX* ctx) {
    return ctx->method;
}

/* Because OPENSSL defines macros that claim lack of support for things, rather
 * than macros that claim support for things, we need to do a version check in
 * addition to a definition check. NPN was added in 1.0.1: for any version
 * before that, there is no compatibility.
 */
#if defined(OPENSSL_NO_NEXTPROTONEG) || OPENSSL_VERSION_NUMBER < 0x1000100fL
static const long Cryptography_HAS_NEXTPROTONEG = 0;
void (*SSL_CTX_set_next_protos_advertised_cb)(SSL_CTX *,
                                              int (*)(SSL *,
                                                      const unsigned char **,
                                                      unsigned int *,
                                                      void *),
                                              void *) = NULL;
void (*SSL_CTX_set_next_proto_select_cb)(SSL_CTX *,
                                         int (*)(SSL *,
                                                 unsigned char **,
                                                 unsigned char *,
                                                 const unsigned char *,
                                                 unsigned int,
                                                 void *),
                                         void *) = NULL;
int (*SSL_select_next_proto)(unsigned char **, unsigned char *,
                             const unsigned char *, unsigned int,
                             const unsigned char *, unsigned int) = NULL;
void (*SSL_get0_next_proto_negotiated)(const SSL *,
                                       const unsigned char **,
                                       unsigned *) = NULL;
#else
static const long Cryptography_HAS_NEXTPROTONEG = 1;
#endif
"""

CONDITIONAL_NAMES = {
    "Cryptography_HAS_TLSv1_1": [
        "SSL_OP_NO_TLSv1_1",
        "TLSv1_1_method",
        "TLSv1_1_server_method",
        "TLSv1_1_client_method",
    ],

    "Cryptography_HAS_TLSv1_2": [
        "SSL_OP_NO_TLSv1_2",
        "TLSv1_2_method",
        "TLSv1_2_server_method",
        "TLSv1_2_client_method",
    ],

    "Cryptography_HAS_SSL2": [
        "SSLv2_method",
        "SSLv2_client_method",
        "SSLv2_server_method",
    ],

    "Cryptography_HAS_TLSEXT_HOSTNAME": [
        "SSL_set_tlsext_host_name",
        "SSL_get_servername",
        "SSL_CTX_set_tlsext_servername_callback",
    ],

    "Cryptography_HAS_RELEASE_BUFFERS": [
        "SSL_MODE_RELEASE_BUFFERS",
    ],

    "Cryptography_HAS_OP_NO_COMPRESSION": [
        "SSL_OP_NO_COMPRESSION",
    ],

    "Cryptography_HAS_SSL_OP_MSIE_SSLV2_RSA_PADDING": [
        "SSL_OP_MSIE_SSLV2_RSA_PADDING",
    ],

    "Cryptography_HAS_EC": [
        "SSL_CTX_set_tmp_ecdh",
    ],

    "Cryptography_HAS_SSL_OP_NO_TICKET": [
        "SSL_OP_NO_TICKET",
    ],

    "Cryptography_HAS_SSL_SET_SSL_CTX": [
        "SSL_set_SSL_CTX",
        "TLSEXT_NAMETYPE_host_name",
    ],

    "Cryptography_HAS_NETBSD_D1_METH": [
        "DTLSv1_method",
    ],

    "Cryptography_HAS_NEXTPROTONEG": [
        "SSL_CTX_set_next_protos_advertised_cb",
        "SSL_CTX_set_next_proto_select_cb",
        "SSL_select_next_proto",
        "SSL_get0_next_proto_negotiated",
    ],

    "Cryptography_HAS_SECURE_RENEGOTIATION": [
        "SSL_OP_ALLOW_UNSAFE_LEGACY_RENEGOTIATION",
        "SSL_OP_LEGACY_SERVER_CONNECT",
        "SSL_get_secure_renegotiation_support",
    ],
}

########NEW FILE########
__FILENAME__ = x509
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/ssl.h>

/*
 * This is part of a work-around for the difficulty cffi has in dealing with
 * `STACK_OF(foo)` as the name of a type.  We invent a new, simpler name that
 * will be an alias for this type and use the alias throughout.  This works
 * together with another opaque typedef for the same name in the TYPES section.
 * Note that the result is an opaque type.
 */
typedef STACK_OF(X509) Cryptography_STACK_OF_X509;
typedef STACK_OF(X509_REVOKED) Cryptography_STACK_OF_X509_REVOKED;
"""

TYPES = """
typedef ... Cryptography_STACK_OF_X509;
typedef ... Cryptography_STACK_OF_X509_REVOKED;

typedef struct {
    ASN1_OBJECT *algorithm;
    ...;
} X509_ALGOR;

typedef ... X509_ATTRIBUTE;

typedef struct {
    X509_ALGOR *signature;
    ...;
} X509_CINF;

typedef struct {
    ASN1_OBJECT *object;
    ASN1_BOOLEAN critical;
    ASN1_OCTET_STRING *value;
} X509_EXTENSION;

typedef ... X509_EXTENSIONS;

typedef ... X509_REQ;

typedef struct {
    ASN1_INTEGER *serialNumber;
    ASN1_TIME *revocationDate;
    X509_EXTENSIONS *extensions;
    int sequence;
    ...;
} X509_REVOKED;

typedef struct {
    Cryptography_STACK_OF_X509_REVOKED *revoked;
    ...;
} X509_CRL_INFO;

typedef struct {
    X509_CRL_INFO *crl;
    ...;
} X509_CRL;

typedef struct {
    X509_CINF *cert_info;
    ...;
} X509;

typedef ... X509_STORE;
typedef ... NETSCAPE_SPKI;
"""

FUNCTIONS = """
X509 *X509_new(void);
void X509_free(X509 *);
X509 *X509_dup(X509 *);

int X509_print_ex(BIO *, X509 *, unsigned long, unsigned long);

int X509_set_version(X509 *, long);

EVP_PKEY *X509_get_pubkey(X509 *);
int X509_set_pubkey(X509 *, EVP_PKEY *);

unsigned char *X509_alias_get0(X509 *, int *);
int X509_sign(X509 *, EVP_PKEY *, const EVP_MD *);

int X509_digest(const X509 *, const EVP_MD *, unsigned char *, unsigned int *);

ASN1_TIME *X509_gmtime_adj(ASN1_TIME *, long);

unsigned long X509_subject_name_hash(X509 *);

X509_NAME *X509_get_subject_name(X509 *);
int X509_set_subject_name(X509 *, X509_NAME *);

X509_NAME *X509_get_issuer_name(X509 *);
int X509_set_issuer_name(X509 *, X509_NAME *);

int X509_get_ext_count(X509 *);
int X509_add_ext(X509 *, X509_EXTENSION *, int);
X509_EXTENSION *X509_EXTENSION_dup(X509_EXTENSION *);
X509_EXTENSION *X509_get_ext(X509 *, int);
int X509_EXTENSION_get_critical(X509_EXTENSION *);
ASN1_OBJECT *X509_EXTENSION_get_object(X509_EXTENSION *);
void X509_EXTENSION_free(X509_EXTENSION *);

int X509_REQ_set_version(X509_REQ *, long);
X509_REQ *X509_REQ_new(void);
void X509_REQ_free(X509_REQ *);
int X509_REQ_set_pubkey(X509_REQ *, EVP_PKEY *);
int X509_REQ_sign(X509_REQ *, EVP_PKEY *, const EVP_MD *);
int X509_REQ_verify(X509_REQ *, EVP_PKEY *);
EVP_PKEY *X509_REQ_get_pubkey(X509_REQ *);
int X509_REQ_print_ex(BIO *, X509_REQ *, unsigned long, unsigned long);

int X509V3_EXT_print(BIO *, X509_EXTENSION *, unsigned long, int);
ASN1_OCTET_STRING *X509_EXTENSION_get_data(X509_EXTENSION *);

X509_REVOKED *X509_REVOKED_new(void);
void X509_REVOKED_free(X509_REVOKED *);

int X509_REVOKED_set_serialNumber(X509_REVOKED *, ASN1_INTEGER *);

int X509_REVOKED_add1_ext_i2d(X509_REVOKED *, int, void *, int, unsigned long);

X509_CRL *d2i_X509_CRL_bio(BIO *, X509_CRL **);
X509_CRL *X509_CRL_new(void);
void X509_CRL_free(X509_CRL *);
int X509_CRL_add0_revoked(X509_CRL *, X509_REVOKED *);
int i2d_X509_CRL_bio(BIO *, X509_CRL *);
int X509_CRL_print(BIO *, X509_CRL *);
int X509_CRL_set_issuer_name(X509_CRL *, X509_NAME *);
int X509_CRL_sign(X509_CRL *, EVP_PKEY *, const EVP_MD *);

int NETSCAPE_SPKI_verify(NETSCAPE_SPKI *, EVP_PKEY *);
int NETSCAPE_SPKI_sign(NETSCAPE_SPKI *, EVP_PKEY *, const EVP_MD *);
char *NETSCAPE_SPKI_b64_encode(NETSCAPE_SPKI *);
EVP_PKEY *NETSCAPE_SPKI_get_pubkey(NETSCAPE_SPKI *);
int NETSCAPE_SPKI_set_pubkey(NETSCAPE_SPKI *, EVP_PKEY *);
NETSCAPE_SPKI *NETSCAPE_SPKI_new(void);
void NETSCAPE_SPKI_free(NETSCAPE_SPKI *);

/*  ASN1 serialization */
int i2d_X509_bio(BIO *, X509 *);
X509 *d2i_X509_bio(BIO *, X509 **);

int i2d_X509_REQ_bio(BIO *, X509_REQ *);
X509_REQ *d2i_X509_REQ_bio(BIO *, X509_REQ **);

int i2d_PrivateKey_bio(BIO *, EVP_PKEY *);
EVP_PKEY *d2i_PrivateKey_bio(BIO *, EVP_PKEY **);
int i2d_PUBKEY_bio(BIO *, EVP_PKEY *);
EVP_PKEY *d2i_PUBKEY_bio(BIO *, EVP_PKEY **);

ASN1_INTEGER *X509_get_serialNumber(X509 *);
int X509_set_serialNumber(X509 *, ASN1_INTEGER *);

/*  X509_STORE */
X509_STORE *X509_STORE_new(void);
void X509_STORE_free(X509_STORE *);
int X509_STORE_add_cert(X509_STORE *, X509 *);
int X509_verify_cert(X509_STORE_CTX *);

const char *X509_verify_cert_error_string(long);

const char *X509_get_default_cert_area(void);
const char *X509_get_default_cert_dir(void);
const char *X509_get_default_cert_file(void);
const char *X509_get_default_cert_dir_env(void);
const char *X509_get_default_cert_file_env(void);
const char *X509_get_default_private_dir(void);

int i2d_RSA_PUBKEY(RSA *, unsigned char **);
RSA *d2i_RSA_PUBKEY(RSA **, const unsigned char **, long);
RSA *d2i_RSAPublicKey(RSA **, const unsigned char **, long);
RSA *d2i_RSAPrivateKey(RSA **, const unsigned char **, long);
int i2d_DSA_PUBKEY(DSA *, unsigned char **);
DSA *d2i_DSA_PUBKEY(DSA **, const unsigned char **, long);
DSA *d2i_DSAPublicKey(DSA **, const unsigned char **, long);
DSA *d2i_DSAPrivateKey(DSA **, const unsigned char **, long);


RSA *d2i_RSAPrivateKey_bio(BIO *, RSA **);
int i2d_RSAPrivateKey_bio(BIO *, RSA *);
RSA *d2i_RSAPublicKey_bio(BIO *, RSA **);
int i2d_RSAPublicKey_bio(BIO *, RSA *);
RSA *d2i_RSA_PUBKEY_bio(BIO *, RSA **);
int i2d_RSA_PUBKEY_bio(BIO *, RSA *);
DSA *d2i_DSA_PUBKEY_bio(BIO *, DSA **);
int i2d_DSA_PUBKEY_bio(BIO *, DSA *);
DSA *d2i_DSAPrivateKey_bio(BIO *, DSA **);
int i2d_DSAPrivateKey_bio(BIO *, DSA *);
"""

MACROS = """
long X509_get_version(X509 *);

ASN1_TIME *X509_get_notBefore(X509 *);
ASN1_TIME *X509_get_notAfter(X509 *);

long X509_REQ_get_version(X509_REQ *);
X509_NAME *X509_REQ_get_subject_name(X509_REQ *);

Cryptography_STACK_OF_X509 *sk_X509_new_null(void);
void sk_X509_free(Cryptography_STACK_OF_X509 *);
int sk_X509_num(Cryptography_STACK_OF_X509 *);
int sk_X509_push(Cryptography_STACK_OF_X509 *, X509 *);
X509 *sk_X509_value(Cryptography_STACK_OF_X509 *, int);

X509_EXTENSIONS *sk_X509_EXTENSION_new_null(void);
int sk_X509_EXTENSION_num(X509_EXTENSIONS *);
X509_EXTENSION *sk_X509_EXTENSION_value(X509_EXTENSIONS *, int);
int sk_X509_EXTENSION_push(X509_EXTENSIONS *, X509_EXTENSION *);
X509_EXTENSION *sk_X509_EXTENSION_delete(X509_EXTENSIONS *, int);
void sk_X509_EXTENSION_free(X509_EXTENSIONS *);

int sk_X509_REVOKED_num(Cryptography_STACK_OF_X509_REVOKED *);
X509_REVOKED *sk_X509_REVOKED_value(Cryptography_STACK_OF_X509_REVOKED *, int);

int i2d_RSAPublicKey(RSA *, unsigned char **);
int i2d_RSAPrivateKey(RSA *, unsigned char **);
int i2d_DSAPublicKey(DSA *, unsigned char **);
int i2d_DSAPrivateKey(DSA *, unsigned char **);

/* These aren't macros these arguments are all const X on openssl > 1.0.x */
int X509_CRL_set_lastUpdate(X509_CRL *, ASN1_TIME *);
int X509_CRL_set_nextUpdate(X509_CRL *, ASN1_TIME *);

/* these use STACK_OF(X509_EXTENSION) in 0.9.8e. Once we drop support for
   RHEL/CentOS 5 we should move these back to FUNCTIONS. */
int X509_REQ_add_extensions(X509_REQ *, X509_EXTENSIONS *);
X509_EXTENSIONS *X509_REQ_get_extensions(X509_REQ *);

int i2d_EC_PUBKEY(EC_KEY *, unsigned char **);
EC_KEY *d2i_EC_PUBKEY(EC_KEY **, const unsigned char **, long);
EC_KEY *d2i_EC_PUBKEY_bio(BIO *, EC_KEY **);
int i2d_EC_PUBKEY_bio(BIO *, EC_KEY *);
EC_KEY *d2i_ECPrivateKey_bio(BIO *, EC_KEY **);
int i2d_ECPrivateKey_bio(BIO *, EC_KEY *);
"""

CUSTOMIZATIONS = """
// OpenSSL 0.9.8e does not have this definition
#if OPENSSL_VERSION_NUMBER <= 0x0090805fL
typedef STACK_OF(X509_EXTENSION) X509_EXTENSIONS;
#endif
#ifdef OPENSSL_NO_EC
int (*i2d_EC_PUBKEY)(EC_KEY *, unsigned char **) = NULL;
EC_KEY *(*d2i_EC_PUBKEY)(EC_KEY **, const unsigned char **, long) = NULL;
EC_KEY *(*d2i_EC_PUBKEY_bio)(BIO *, EC_KEY **) = NULL;
int (*i2d_EC_PUBKEY_bio)(BIO *, EC_KEY *) = NULL;
EC_KEY *(*d2i_ECPrivateKey_bio)(BIO *, EC_KEY **) = NULL;
int (*i2d_ECPrivateKey_bio)(BIO *, EC_KEY *) = NULL;
#endif
"""

CONDITIONAL_NAMES = {
    "Cryptography_HAS_EC": [
        "i2d_EC_PUBKEY",
        "d2i_EC_PUBKEY",
        "d2i_EC_PUBKEY_bio",
        "i2d_EC_PUBKEY_bio",
        "d2i_ECPrivateKey_bio",
        "i2d_ECPrivateKey_bio",
    ]
}

########NEW FILE########
__FILENAME__ = x509name
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/x509.h>

/*
 * See the comment above Cryptography_STACK_OF_X509 in x509.py
 */
typedef STACK_OF(X509_NAME) Cryptography_STACK_OF_X509_NAME;
"""

TYPES = """
typedef ... X509_NAME;
typedef ... X509_NAME_ENTRY;
typedef ... Cryptography_STACK_OF_X509_NAME;
"""

FUNCTIONS = """
int X509_NAME_entry_count(X509_NAME *);
X509_NAME_ENTRY *X509_NAME_get_entry(X509_NAME *, int);
ASN1_OBJECT *X509_NAME_ENTRY_get_object(X509_NAME_ENTRY *);
ASN1_STRING *X509_NAME_ENTRY_get_data(X509_NAME_ENTRY *);
unsigned long X509_NAME_hash(X509_NAME *);

int i2d_X509_NAME(X509_NAME *, unsigned char **);
int X509_NAME_add_entry_by_NID(X509_NAME *, int, int, unsigned char *,
                               int, int, int);
X509_NAME_ENTRY *X509_NAME_delete_entry(X509_NAME *, int);
void X509_NAME_ENTRY_free(X509_NAME_ENTRY *);
int X509_NAME_get_index_by_NID(X509_NAME *, int, int);
int X509_NAME_cmp(const X509_NAME *, const X509_NAME *);
char *X509_NAME_oneline(X509_NAME *, char *, int);
X509_NAME *X509_NAME_dup(X509_NAME *);
void X509_NAME_free(X509_NAME *);
"""

MACROS = """
Cryptography_STACK_OF_X509_NAME *sk_X509_NAME_new_null(void);
int sk_X509_NAME_num(Cryptography_STACK_OF_X509_NAME *);
int sk_X509_NAME_push(Cryptography_STACK_OF_X509_NAME *, X509_NAME *);
X509_NAME *sk_X509_NAME_value(Cryptography_STACK_OF_X509_NAME *, int);
void sk_X509_NAME_free(Cryptography_STACK_OF_X509_NAME *);
"""

CUSTOMIZATIONS = """
"""

CONDITIONAL_NAMES = {}

########NEW FILE########
__FILENAME__ = x509v3
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

INCLUDES = """
#include <openssl/x509v3.h>
"""

TYPES = """
typedef struct {
    X509 *issuer_cert;
    X509 *subject_cert;
    ...;
} X509V3_CTX;

typedef void * (*X509V3_EXT_D2I)(void *, const unsigned char **, long);

typedef struct {
    ASN1_ITEM_EXP *it;
    X509V3_EXT_D2I d2i;
    ...;
} X509V3_EXT_METHOD;

static const int GEN_OTHERNAME;
static const int GEN_EMAIL;
static const int GEN_X400;
static const int GEN_DNS;
static const int GEN_URI;
static const int GEN_DIRNAME;
static const int GEN_EDIPARTY;
static const int GEN_IPADD;
static const int GEN_RID;

typedef struct {
    ...;
} OTHERNAME;

typedef struct {
    ...;
} EDIPARTYNAME;

typedef struct {
    int type;
    union {
        char *ptr;
        OTHERNAME *otherName;  /* otherName */
        ASN1_IA5STRING *rfc822Name;
        ASN1_IA5STRING *dNSName;
        ASN1_TYPE *x400Address;
        X509_NAME *directoryName;
        EDIPARTYNAME *ediPartyName;
        ASN1_IA5STRING *uniformResourceIdentifier;
        ASN1_OCTET_STRING *iPAddress;
        ASN1_OBJECT *registeredID;

        /* Old names */
        ASN1_OCTET_STRING *ip; /* iPAddress */
        X509_NAME *dirn;       /* dirn */
        ASN1_IA5STRING *ia5;   /* rfc822Name, dNSName, */
                               /*   uniformResourceIdentifier */
        ASN1_OBJECT *rid;      /* registeredID */
        ASN1_TYPE *other;      /* x400Address */
    } d;
    ...;
} GENERAL_NAME;

typedef struct stack_st_GENERAL_NAME GENERAL_NAMES;
"""

FUNCTIONS = """
void X509V3_set_ctx(X509V3_CTX *, X509 *, X509 *, X509_REQ *, X509_CRL *, int);
X509_EXTENSION *X509V3_EXT_nconf(CONF *, X509V3_CTX *, char *, char *);
int GENERAL_NAME_print(BIO *, GENERAL_NAME *);
"""

MACROS = """
void *X509V3_set_ctx_nodb(X509V3_CTX *);
int sk_GENERAL_NAME_num(struct stack_st_GENERAL_NAME *);
int sk_GENERAL_NAME_push(struct stack_st_GENERAL_NAME *, GENERAL_NAME *);
GENERAL_NAME *sk_GENERAL_NAME_value(struct stack_st_GENERAL_NAME *, int);

/* These aren't macros these functions are all const X on openssl > 1.0.x */
const X509V3_EXT_METHOD *X509V3_EXT_get(X509_EXTENSION *);
const X509V3_EXT_METHOD *X509V3_EXT_get_nid(int);
"""

CUSTOMIZATIONS = """
"""

CONDITIONAL_NAMES = {}

########NEW FILE########
__FILENAME__ = utils
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import binascii

import sys

import cffi


def build_ffi(module_prefix, modules, pre_include="", post_include="",
              libraries=[], extra_compile_args=[], extra_link_args=[]):
    """
    Modules listed in ``modules`` should have the following attributes:

    * ``INCLUDES``: A string containing C includes.
    * ``TYPES``: A string containing C declarations for types.
    * ``FUNCTIONS``: A string containing C declarations for functions.
    * ``MACROS``: A string containing C declarations for any macros.
    * ``CUSTOMIZATIONS``: A string containing arbitrary top-level C code, this
        can be used to do things like test for a define and provide an
        alternate implementation based on that.
    * ``CONDITIONAL_NAMES``: A dict mapping strings of condition names from the
        library to a list of names which will not be present without the
        condition.
    """
    ffi = cffi.FFI()
    types = []
    includes = []
    functions = []
    macros = []
    customizations = []
    for name in modules:
        module_name = module_prefix + name
        __import__(module_name)
        module = sys.modules[module_name]

        types.append(module.TYPES)
        macros.append(module.MACROS)
        functions.append(module.FUNCTIONS)
        includes.append(module.INCLUDES)
        customizations.append(module.CUSTOMIZATIONS)

    cdef_sources = types + functions + macros
    ffi.cdef("\n".join(cdef_sources))

    # We include functions here so that if we got any of their definitions
    # wrong, the underlying C compiler will explode. In C you are allowed
    # to re-declare a function if it has the same signature. That is:
    #   int foo(int);
    #   int foo(int);
    # is legal, but the following will fail to compile:
    #   int foo(int);
    #   int foo(short);
    source = "\n".join(
        [pre_include] +
        includes +
        [post_include] +
        functions +
        customizations
    )
    lib = ffi.verify(
        source=source,
        modulename=_create_modulename(cdef_sources, source, sys.version),
        libraries=libraries,
        ext_package="cryptography",
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
    )

    for name in modules:
        module_name = module_prefix + name
        module = sys.modules[module_name]
        for condition, names in module.CONDITIONAL_NAMES.items():
            if not getattr(lib, condition):
                for name in names:
                    delattr(lib, name)

    return ffi, lib


def _create_modulename(cdef_sources, source, sys_version):
    """
    cffi creates a modulename internally that incorporates the cffi version.
    This will cause cryptography's wheels to break when the version of cffi
    the user has does not match what was used when building the wheel. To
    resolve this we build our own modulename that uses most of the same code
    from cffi but elides the version key.
    """
    key = '\x00'.join([sys_version[:3], source] + cdef_sources)
    key = key.encode('utf-8')
    k1 = hex(binascii.crc32(key[0::2]) & 0xffffffff)
    k1 = k1.lstrip('0x').rstrip('L')
    k2 = hex(binascii.crc32(key[1::2]) & 0xffffffff)
    k2 = k2.lstrip('0').rstrip('L')
    return '_Cryptography_cffi_{0}{1}'.format(k1, k2)

########NEW FILE########
__FILENAME__ = dsa
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import six

from cryptography import utils
from cryptography.exceptions import UnsupportedAlgorithm, _Reasons
from cryptography.hazmat.backends.interfaces import DSABackend
from cryptography.hazmat.primitives import interfaces


def _check_dsa_parameters(modulus, subgroup_order, generator):
    if (
        not isinstance(modulus, six.integer_types) or
        not isinstance(subgroup_order, six.integer_types) or
        not isinstance(generator, six.integer_types)
    ):
        raise TypeError("DSA parameters must be integers.")

    if (utils.bit_length(modulus),
        utils.bit_length(subgroup_order)) not in (
            (1024, 160),
            (2048, 256),
            (3072, 256)):
        raise ValueError("modulus and subgroup_order lengths must be "
                         "one of these pairs (1024, 160) or (2048, 256) "
                         "or (3072, 256).")

    if generator <= 1 or generator >= modulus:
        raise ValueError("generator must be > 1 and < modulus.")


@utils.register_interface(interfaces.DSAParameters)
class DSAParameters(object):
    def __init__(self, modulus, subgroup_order, generator):
        _check_dsa_parameters(modulus, subgroup_order, generator)

        self._modulus = modulus
        self._subgroup_order = subgroup_order
        self._generator = generator

    @classmethod
    def generate(cls, key_size, backend):
        if not isinstance(backend, DSABackend):
            raise UnsupportedAlgorithm(
                "Backend object does not implement DSABackend.",
                _Reasons.BACKEND_MISSING_INTERFACE
            )

        return backend.generate_dsa_parameters(key_size)

    @property
    def modulus(self):
        return self._modulus

    @property
    def subgroup_order(self):
        return self._subgroup_order

    @property
    def generator(self):
        return self._generator

    @property
    def p(self):
        return self.modulus

    @property
    def q(self):
        return self.subgroup_order

    @property
    def g(self):
        return self.generator


@utils.register_interface(interfaces.DSAPrivateKey)
class DSAPrivateKey(object):
    def __init__(self, modulus, subgroup_order, generator, x, y):
        _check_dsa_parameters(modulus, subgroup_order, generator)
        if (
            not isinstance(x, six.integer_types) or
            not isinstance(y, six.integer_types)
        ):
            raise TypeError("DSAPrivateKey arguments must be integers.")

        if x <= 0 or x >= subgroup_order:
            raise ValueError("x must be > 0 and < subgroup_order.")

        if y != pow(generator, x, modulus):
            raise ValueError("y must be equal to (generator ** x % modulus).")

        self._modulus = modulus
        self._subgroup_order = subgroup_order
        self._generator = generator
        self._x = x
        self._y = y

    @classmethod
    def generate(cls, parameters, backend):
        if not isinstance(backend, DSABackend):
            raise UnsupportedAlgorithm(
                "Backend object does not implement DSABackend.",
                _Reasons.BACKEND_MISSING_INTERFACE
            )

        return backend.generate_dsa_private_key(parameters)

    def signer(self, algorithm, backend):
        if not isinstance(backend, DSABackend):
            raise UnsupportedAlgorithm(
                "Backend object does not implement DSABackend.",
                _Reasons.BACKEND_MISSING_INTERFACE
            )

        return backend.create_dsa_signature_ctx(self, algorithm)

    @property
    def key_size(self):
        return utils.bit_length(self._modulus)

    def public_key(self):
        return DSAPublicKey(self._modulus, self._subgroup_order,
                            self._generator, self.y)

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    def parameters(self):
        return DSAParameters(self._modulus, self._subgroup_order,
                             self._generator)


@utils.register_interface(interfaces.DSAPublicKey)
class DSAPublicKey(object):
    def __init__(self, modulus, subgroup_order, generator, y):
        _check_dsa_parameters(modulus, subgroup_order, generator)
        if not isinstance(y, six.integer_types):
            raise TypeError("y must be an integer.")

        self._modulus = modulus
        self._subgroup_order = subgroup_order
        self._generator = generator
        self._y = y

    def verifier(self, signature, algorithm, backend):
        if not isinstance(backend, DSABackend):
            raise UnsupportedAlgorithm(
                "Backend object does not implement DSABackend.",
                _Reasons.BACKEND_MISSING_INTERFACE
            )

        return backend.create_dsa_verification_ctx(self, signature,
                                                   algorithm)

    @property
    def key_size(self):
        return utils.bit_length(self._modulus)

    @property
    def y(self):
        return self._y

    def parameters(self):
        return DSAParameters(self._modulus, self._subgroup_order,
                             self._generator)

########NEW FILE########
__FILENAME__ = padding
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import warnings

import six

from cryptography import utils
from cryptography.hazmat.primitives import interfaces


@utils.register_interface(interfaces.AsymmetricPadding)
class PKCS1v15(object):
    name = "EMSA-PKCS1-v1_5"


@utils.register_interface(interfaces.AsymmetricPadding)
class PSS(object):
    MAX_LENGTH = object()
    name = "EMSA-PSS"

    def __init__(self, mgf, salt_length=None):
        self._mgf = mgf

        if salt_length is None:
            warnings.warn(
                "salt_length is deprecated on MGF1 and should be added via the"
                " PSS constructor.",
                utils.DeprecatedIn04,
                stacklevel=2
            )
        else:
            if (not isinstance(salt_length, six.integer_types) and
                    salt_length is not self.MAX_LENGTH):
                raise TypeError("salt_length must be an integer.")

            if salt_length is not self.MAX_LENGTH and salt_length < 0:
                raise ValueError("salt_length must be zero or greater.")

        if salt_length is None and self._mgf._salt_length is None:
            raise ValueError("You must supply salt_length.")

        self._salt_length = salt_length


@utils.register_interface(interfaces.AsymmetricPadding)
class OAEP(object):
    name = "EME-OAEP"

    def __init__(self, mgf, algorithm, label):
        if not isinstance(algorithm, interfaces.HashAlgorithm):
            raise TypeError("Expected instance of interfaces.HashAlgorithm.")

        self._mgf = mgf
        self._algorithm = algorithm
        self._label = label


class MGF1(object):
    MAX_LENGTH = object()

    def __init__(self, algorithm, salt_length=None):
        if not isinstance(algorithm, interfaces.HashAlgorithm):
            raise TypeError("Expected instance of interfaces.HashAlgorithm.")

        self._algorithm = algorithm

        if salt_length is not None:
            warnings.warn(
                "salt_length is deprecated on MGF1 and should be passed to "
                "the PSS constructor instead.",
                utils.DeprecatedIn04,
                stacklevel=2
            )
            if (not isinstance(salt_length, six.integer_types) and
                    salt_length is not self.MAX_LENGTH):
                raise TypeError("salt_length must be an integer.")

            if salt_length is not self.MAX_LENGTH and salt_length < 0:
                raise ValueError("salt_length must be zero or greater.")

        self._salt_length = salt_length

########NEW FILE########
__FILENAME__ = rsa
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import six

from cryptography import utils
from cryptography.exceptions import UnsupportedAlgorithm, _Reasons
from cryptography.hazmat.backends.interfaces import RSABackend
from cryptography.hazmat.primitives import interfaces


@utils.register_interface(interfaces.RSAPublicKey)
class RSAPublicKey(object):
    def __init__(self, public_exponent, modulus):
        if (
            not isinstance(public_exponent, six.integer_types) or
            not isinstance(modulus, six.integer_types)
        ):
            raise TypeError("RSAPublicKey arguments must be integers.")

        if modulus < 3:
            raise ValueError("modulus must be >= 3.")

        if public_exponent < 3 or public_exponent >= modulus:
            raise ValueError("public_exponent must be >= 3 and < modulus.")

        if public_exponent & 1 == 0:
            raise ValueError("public_exponent must be odd.")

        self._public_exponent = public_exponent
        self._modulus = modulus

    def verifier(self, signature, padding, algorithm, backend):
        if not isinstance(backend, RSABackend):
            raise UnsupportedAlgorithm(
                "Backend object does not implement RSABackend.",
                _Reasons.BACKEND_MISSING_INTERFACE
            )

        return backend.create_rsa_verification_ctx(self, signature, padding,
                                                   algorithm)

    def encrypt(self, plaintext, padding, backend):
        if not isinstance(backend, RSABackend):
            raise UnsupportedAlgorithm(
                "Backend object does not implement RSABackend.",
                _Reasons.BACKEND_MISSING_INTERFACE
            )

        return backend.encrypt_rsa(self, plaintext, padding)

    @property
    def key_size(self):
        return utils.bit_length(self.modulus)

    @property
    def public_exponent(self):
        return self._public_exponent

    @property
    def modulus(self):
        return self._modulus

    @property
    def e(self):
        return self.public_exponent

    @property
    def n(self):
        return self.modulus


def _modinv(e, m):
    """
    Modular Multiplicative Inverse. Returns x such that: (x*e) mod m == 1
    """
    x1, y1, x2, y2 = 1, 0, 0, 1
    a, b = e, m
    while b > 0:
        q, r = divmod(a, b)
        xn, yn = x1 - q * x2, y1 - q * y2
        a, b, x1, y1, x2, y2 = b, r, x2, y2, xn, yn
    return x1 % m


def rsa_crt_iqmp(p, q):
    """
    Compute the CRT (q ** -1) % p value from RSA primes p and q.
    """
    return _modinv(q, p)


def rsa_crt_dmp1(private_exponent, p):
    """
    Compute the CRT private_exponent % (p - 1) value from the RSA
    private_exponent and p.
    """
    return private_exponent % (p - 1)


def rsa_crt_dmq1(private_exponent, q):
    """
    Compute the CRT private_exponent % (q - 1) value from the RSA
    private_exponent and q.
    """
    return private_exponent % (q - 1)


@utils.register_interface(interfaces.RSAPrivateKey)
class RSAPrivateKey(object):
    def __init__(self, p, q, private_exponent, dmp1, dmq1, iqmp,
                 public_exponent, modulus):
        if (
            not isinstance(p, six.integer_types) or
            not isinstance(q, six.integer_types) or
            not isinstance(dmp1, six.integer_types) or
            not isinstance(dmq1, six.integer_types) or
            not isinstance(iqmp, six.integer_types) or
            not isinstance(private_exponent, six.integer_types) or
            not isinstance(public_exponent, six.integer_types) or
            not isinstance(modulus, six.integer_types)
        ):
            raise TypeError("RSAPrivateKey arguments must be integers.")

        if modulus < 3:
            raise ValueError("modulus must be >= 3.")

        if p >= modulus:
            raise ValueError("p must be < modulus.")

        if q >= modulus:
            raise ValueError("q must be < modulus.")

        if dmp1 >= modulus:
            raise ValueError("dmp1 must be < modulus.")

        if dmq1 >= modulus:
            raise ValueError("dmq1 must be < modulus.")

        if iqmp >= modulus:
            raise ValueError("iqmp must be < modulus.")

        if private_exponent >= modulus:
            raise ValueError("private_exponent must be < modulus.")

        if public_exponent < 3 or public_exponent >= modulus:
            raise ValueError("public_exponent must be >= 3 and < modulus.")

        if public_exponent & 1 == 0:
            raise ValueError("public_exponent must be odd.")

        if dmp1 & 1 == 0:
            raise ValueError("dmp1 must be odd.")

        if dmq1 & 1 == 0:
            raise ValueError("dmq1 must be odd.")

        if p * q != modulus:
            raise ValueError("p*q must equal modulus.")

        self._p = p
        self._q = q
        self._dmp1 = dmp1
        self._dmq1 = dmq1
        self._iqmp = iqmp
        self._private_exponent = private_exponent
        self._public_exponent = public_exponent
        self._modulus = modulus

    @classmethod
    def generate(cls, public_exponent, key_size, backend):
        if not isinstance(backend, RSABackend):
            raise UnsupportedAlgorithm(
                "Backend object does not implement RSABackend.",
                _Reasons.BACKEND_MISSING_INTERFACE
            )

        return backend.generate_rsa_private_key(public_exponent, key_size)

    def signer(self, padding, algorithm, backend):
        if not isinstance(backend, RSABackend):
            raise UnsupportedAlgorithm(
                "Backend object does not implement RSABackend.",
                _Reasons.BACKEND_MISSING_INTERFACE
            )

        return backend.create_rsa_signature_ctx(self, padding, algorithm)

    def decrypt(self, ciphertext, padding, backend):
        if not isinstance(backend, RSABackend):
            raise UnsupportedAlgorithm(
                "Backend object does not implement RSABackend.",
                _Reasons.BACKEND_MISSING_INTERFACE
            )

        return backend.decrypt_rsa(self, ciphertext, padding)

    @property
    def key_size(self):
        return utils.bit_length(self.modulus)

    def public_key(self):
        return RSAPublicKey(self.public_exponent, self.modulus)

    @property
    def p(self):
        return self._p

    @property
    def q(self):
        return self._q

    @property
    def private_exponent(self):
        return self._private_exponent

    @property
    def public_exponent(self):
        return self._public_exponent

    @property
    def modulus(self):
        return self._modulus

    @property
    def d(self):
        return self.private_exponent

    @property
    def dmp1(self):
        return self._dmp1

    @property
    def dmq1(self):
        return self._dmq1

    @property
    def iqmp(self):
        return self._iqmp

    @property
    def e(self):
        return self.public_exponent

    @property
    def n(self):
        return self.modulus

########NEW FILE########
__FILENAME__ = algorithms
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

from cryptography import utils
from cryptography.hazmat.primitives import interfaces


def _verify_key_size(algorithm, key):
    # Verify that the key size matches the expected key size
    if len(key) * 8 not in algorithm.key_sizes:
        raise ValueError("Invalid key size ({0}) for {1}.".format(
            len(key) * 8, algorithm.name
        ))
    return key


@utils.register_interface(interfaces.BlockCipherAlgorithm)
@utils.register_interface(interfaces.CipherAlgorithm)
class AES(object):
    name = "AES"
    block_size = 128
    key_sizes = frozenset([128, 192, 256])

    def __init__(self, key):
        self.key = _verify_key_size(self, key)

    @property
    def key_size(self):
        return len(self.key) * 8


@utils.register_interface(interfaces.BlockCipherAlgorithm)
@utils.register_interface(interfaces.CipherAlgorithm)
class Camellia(object):
    name = "camellia"
    block_size = 128
    key_sizes = frozenset([128, 192, 256])

    def __init__(self, key):
        self.key = _verify_key_size(self, key)

    @property
    def key_size(self):
        return len(self.key) * 8


@utils.register_interface(interfaces.BlockCipherAlgorithm)
@utils.register_interface(interfaces.CipherAlgorithm)
class TripleDES(object):
    name = "3DES"
    block_size = 64
    key_sizes = frozenset([64, 128, 192])

    def __init__(self, key):
        if len(key) == 8:
            key += key + key
        elif len(key) == 16:
            key += key[:8]
        self.key = _verify_key_size(self, key)

    @property
    def key_size(self):
        return len(self.key) * 8


@utils.register_interface(interfaces.BlockCipherAlgorithm)
@utils.register_interface(interfaces.CipherAlgorithm)
class Blowfish(object):
    name = "Blowfish"
    block_size = 64
    key_sizes = frozenset(range(32, 449, 8))

    def __init__(self, key):
        self.key = _verify_key_size(self, key)

    @property
    def key_size(self):
        return len(self.key) * 8


@utils.register_interface(interfaces.BlockCipherAlgorithm)
@utils.register_interface(interfaces.CipherAlgorithm)
class CAST5(object):
    name = "CAST5"
    block_size = 64
    key_sizes = frozenset(range(40, 129, 8))

    def __init__(self, key):
        self.key = _verify_key_size(self, key)

    @property
    def key_size(self):
        return len(self.key) * 8


@utils.register_interface(interfaces.CipherAlgorithm)
class ARC4(object):
    name = "RC4"
    key_sizes = frozenset([40, 56, 64, 80, 128, 192, 256])

    def __init__(self, key):
        self.key = _verify_key_size(self, key)

    @property
    def key_size(self):
        return len(self.key) * 8


@utils.register_interface(interfaces.CipherAlgorithm)
class IDEA(object):
    name = "IDEA"
    block_size = 64
    key_sizes = frozenset([128])

    def __init__(self, key):
        self.key = _verify_key_size(self, key)

    @property
    def key_size(self):
        return len(self.key) * 8


@utils.register_interface(interfaces.BlockCipherAlgorithm)
@utils.register_interface(interfaces.CipherAlgorithm)
class SEED(object):
    name = "SEED"
    block_size = 128
    key_sizes = frozenset([128])

    def __init__(self, key):
        self.key = _verify_key_size(self, key)

    @property
    def key_size(self):
        return len(self.key) * 8

########NEW FILE########
__FILENAME__ = base
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

from cryptography import utils
from cryptography.exceptions import (
    AlreadyFinalized, AlreadyUpdated, NotYetFinalized, UnsupportedAlgorithm,
    _Reasons
)
from cryptography.hazmat.backends.interfaces import CipherBackend
from cryptography.hazmat.primitives import interfaces


class Cipher(object):
    def __init__(self, algorithm, mode, backend):
        if not isinstance(backend, CipherBackend):
            raise UnsupportedAlgorithm(
                "Backend object does not implement CipherBackend.",
                _Reasons.BACKEND_MISSING_INTERFACE
            )

        if not isinstance(algorithm, interfaces.CipherAlgorithm):
            raise TypeError(
                "Expected interface of interfaces.CipherAlgorithm."
            )

        if mode is not None:
            mode.validate_for_algorithm(algorithm)

        self.algorithm = algorithm
        self.mode = mode
        self._backend = backend

    def encryptor(self):
        if isinstance(self.mode, interfaces.ModeWithAuthenticationTag):
            if self.mode.tag is not None:
                raise ValueError(
                    "Authentication tag must be None when encrypting."
                )
        ctx = self._backend.create_symmetric_encryption_ctx(
            self.algorithm, self.mode
        )
        return self._wrap_ctx(ctx, encrypt=True)

    def decryptor(self):
        if isinstance(self.mode, interfaces.ModeWithAuthenticationTag):
            if self.mode.tag is None:
                raise ValueError(
                    "Authentication tag must be provided when decrypting."
                )
        ctx = self._backend.create_symmetric_decryption_ctx(
            self.algorithm, self.mode
        )
        return self._wrap_ctx(ctx, encrypt=False)

    def _wrap_ctx(self, ctx, encrypt):
        if isinstance(self.mode, interfaces.ModeWithAuthenticationTag):
            if encrypt:
                return _AEADEncryptionContext(ctx)
            else:
                return _AEADCipherContext(ctx)
        else:
            return _CipherContext(ctx)


@utils.register_interface(interfaces.CipherContext)
class _CipherContext(object):
    def __init__(self, ctx):
        self._ctx = ctx

    def update(self, data):
        if self._ctx is None:
            raise AlreadyFinalized("Context was already finalized.")
        return self._ctx.update(data)

    def finalize(self):
        if self._ctx is None:
            raise AlreadyFinalized("Context was already finalized.")
        data = self._ctx.finalize()
        self._ctx = None
        return data


@utils.register_interface(interfaces.AEADCipherContext)
@utils.register_interface(interfaces.CipherContext)
class _AEADCipherContext(object):
    def __init__(self, ctx):
        self._ctx = ctx
        self._tag = None
        self._updated = False

    def update(self, data):
        if self._ctx is None:
            raise AlreadyFinalized("Context was already finalized.")
        self._updated = True
        return self._ctx.update(data)

    def finalize(self):
        if self._ctx is None:
            raise AlreadyFinalized("Context was already finalized.")
        data = self._ctx.finalize()
        self._tag = self._ctx.tag
        self._ctx = None
        return data

    def authenticate_additional_data(self, data):
        if self._ctx is None:
            raise AlreadyFinalized("Context was already finalized.")
        if self._updated:
            raise AlreadyUpdated("Update has been called on this context.")
        self._ctx.authenticate_additional_data(data)


@utils.register_interface(interfaces.AEADEncryptionContext)
class _AEADEncryptionContext(_AEADCipherContext):
    @property
    def tag(self):
        if self._ctx is not None:
            raise NotYetFinalized("You must finalize encryption before "
                                  "getting the tag.")
        return self._tag

########NEW FILE########
__FILENAME__ = modes
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

from cryptography import utils
from cryptography.hazmat.primitives import interfaces


def _check_iv_length(mode, algorithm):
    if len(mode.initialization_vector) * 8 != algorithm.block_size:
        raise ValueError("Invalid IV size ({0}) for {1}.".format(
            len(mode.initialization_vector), mode.name
        ))


@utils.register_interface(interfaces.Mode)
@utils.register_interface(interfaces.ModeWithInitializationVector)
class CBC(object):
    name = "CBC"

    def __init__(self, initialization_vector):
        self.initialization_vector = initialization_vector

    validate_for_algorithm = _check_iv_length


@utils.register_interface(interfaces.Mode)
class ECB(object):
    name = "ECB"

    def validate_for_algorithm(self, algorithm):
        pass


@utils.register_interface(interfaces.Mode)
@utils.register_interface(interfaces.ModeWithInitializationVector)
class OFB(object):
    name = "OFB"

    def __init__(self, initialization_vector):
        self.initialization_vector = initialization_vector

    validate_for_algorithm = _check_iv_length


@utils.register_interface(interfaces.Mode)
@utils.register_interface(interfaces.ModeWithInitializationVector)
class CFB(object):
    name = "CFB"

    def __init__(self, initialization_vector):
        self.initialization_vector = initialization_vector

    validate_for_algorithm = _check_iv_length


@utils.register_interface(interfaces.Mode)
@utils.register_interface(interfaces.ModeWithInitializationVector)
class CFB8(object):
    name = "CFB8"

    def __init__(self, initialization_vector):
        self.initialization_vector = initialization_vector

    validate_for_algorithm = _check_iv_length


@utils.register_interface(interfaces.Mode)
@utils.register_interface(interfaces.ModeWithNonce)
class CTR(object):
    name = "CTR"

    def __init__(self, nonce):
        self.nonce = nonce

    def validate_for_algorithm(self, algorithm):
        if len(self.nonce) * 8 != algorithm.block_size:
            raise ValueError("Invalid nonce size ({0}) for {1}.".format(
                len(self.nonce), self.name
            ))


@utils.register_interface(interfaces.Mode)
@utils.register_interface(interfaces.ModeWithInitializationVector)
@utils.register_interface(interfaces.ModeWithAuthenticationTag)
class GCM(object):
    name = "GCM"

    def __init__(self, initialization_vector, tag=None):
        # len(initialization_vector) must in [1, 2 ** 64), but it's impossible
        # to actually construct a bytes object that large, so we don't check
        # for it
        if tag is not None and len(tag) < 4:
            raise ValueError(
                "Authentication tag must be 4 bytes or longer."
            )

        self.initialization_vector = initialization_vector
        self.tag = tag

    def validate_for_algorithm(self, algorithm):
        pass

########NEW FILE########
__FILENAME__ = cmac
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

from cryptography import utils
from cryptography.exceptions import (
    AlreadyFinalized, InvalidSignature, UnsupportedAlgorithm, _Reasons
)
from cryptography.hazmat.backends.interfaces import CMACBackend
from cryptography.hazmat.primitives import constant_time, interfaces


@utils.register_interface(interfaces.CMACContext)
class CMAC(object):
    def __init__(self, algorithm, backend, ctx=None):
        if not isinstance(backend, CMACBackend):
            raise UnsupportedAlgorithm(
                "Backend object does not implement CMACBackend.",
                _Reasons.BACKEND_MISSING_INTERFACE
            )

        if not isinstance(algorithm, interfaces.BlockCipherAlgorithm):
            raise TypeError(
                "Expected instance of interfaces.BlockCipherAlgorithm."
            )
        self._algorithm = algorithm

        self._backend = backend
        if ctx is None:
            self._ctx = self._backend.create_cmac_ctx(self._algorithm)
        else:
            self._ctx = ctx

    def update(self, data):
        if self._ctx is None:
            raise AlreadyFinalized("Context was already finalized.")
        if not isinstance(data, bytes):
            raise TypeError("data must be bytes.")
        self._ctx.update(data)

    def finalize(self):
        if self._ctx is None:
            raise AlreadyFinalized("Context was already finalized.")
        digest = self._ctx.finalize()
        self._ctx = None
        return digest

    def verify(self, signature):
        if not isinstance(signature, bytes):
            raise TypeError("signature must be bytes.")
        digest = self.finalize()
        if not constant_time.bytes_eq(digest, signature):
            raise InvalidSignature("Signature did not match digest.")

    def copy(self):
        if self._ctx is None:
            raise AlreadyFinalized("Context was already finalized.")
        return CMAC(
            self._algorithm,
            backend=self._backend,
            ctx=self._ctx.copy()
        )

########NEW FILE########
__FILENAME__ = constant_time
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import sys

import cffi

from cryptography.hazmat.bindings.utils import _create_modulename

TYPES = """
uint8_t Cryptography_constant_time_bytes_eq(uint8_t *, size_t, uint8_t *,
                                            size_t);
"""

FUNCTIONS = """
uint8_t Cryptography_constant_time_bytes_eq(uint8_t *a, size_t len_a,
                                            uint8_t *b, size_t len_b) {
    size_t i = 0;
    uint8_t mismatch = 0;
    if (len_a != len_b) {
        return 0;
    }
    for (i = 0; i < len_a; i++) {
        mismatch |= a[i] ^ b[i];
    }

    /* Make sure any bits set are copied to the lowest bit */
    mismatch |= mismatch >> 4;
    mismatch |= mismatch >> 2;
    mismatch |= mismatch >> 1;
    /* Now check the low bit to see if it's set */
    return (mismatch & 1) == 0;
}
"""

_ffi = cffi.FFI()
_ffi.cdef(TYPES)
_lib = _ffi.verify(
    source=FUNCTIONS,
    modulename=_create_modulename([TYPES], FUNCTIONS, sys.version),
    ext_package="cryptography",
)


def bytes_eq(a, b):
    if not isinstance(a, bytes) or not isinstance(b, bytes):
            raise TypeError("a and b must be bytes.")

    return _lib.Cryptography_constant_time_bytes_eq(a, len(a), b, len(b)) == 1

########NEW FILE########
__FILENAME__ = hashes
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

from cryptography import utils
from cryptography.exceptions import (
    AlreadyFinalized, UnsupportedAlgorithm, _Reasons
)
from cryptography.hazmat.backends.interfaces import HashBackend
from cryptography.hazmat.primitives import interfaces


@utils.register_interface(interfaces.HashContext)
class Hash(object):
    def __init__(self, algorithm, backend, ctx=None):
        if not isinstance(backend, HashBackend):
            raise UnsupportedAlgorithm(
                "Backend object does not implement HashBackend.",
                _Reasons.BACKEND_MISSING_INTERFACE
            )

        if not isinstance(algorithm, interfaces.HashAlgorithm):
            raise TypeError("Expected instance of interfaces.HashAlgorithm.")
        self.algorithm = algorithm

        self._backend = backend

        if ctx is None:
            self._ctx = self._backend.create_hash_ctx(self.algorithm)
        else:
            self._ctx = ctx

    def update(self, data):
        if self._ctx is None:
            raise AlreadyFinalized("Context was already finalized.")
        if not isinstance(data, bytes):
            raise TypeError("data must be bytes.")
        self._ctx.update(data)

    def copy(self):
        if self._ctx is None:
            raise AlreadyFinalized("Context was already finalized.")
        return Hash(
            self.algorithm, backend=self._backend, ctx=self._ctx.copy()
        )

    def finalize(self):
        if self._ctx is None:
            raise AlreadyFinalized("Context was already finalized.")
        digest = self._ctx.finalize()
        self._ctx = None
        return digest


@utils.register_interface(interfaces.HashAlgorithm)
class SHA1(object):
    name = "sha1"
    digest_size = 20
    block_size = 64


@utils.register_interface(interfaces.HashAlgorithm)
class SHA224(object):
    name = "sha224"
    digest_size = 28
    block_size = 64


@utils.register_interface(interfaces.HashAlgorithm)
class SHA256(object):
    name = "sha256"
    digest_size = 32
    block_size = 64


@utils.register_interface(interfaces.HashAlgorithm)
class SHA384(object):
    name = "sha384"
    digest_size = 48
    block_size = 128


@utils.register_interface(interfaces.HashAlgorithm)
class SHA512(object):
    name = "sha512"
    digest_size = 64
    block_size = 128


@utils.register_interface(interfaces.HashAlgorithm)
class RIPEMD160(object):
    name = "ripemd160"
    digest_size = 20
    block_size = 64


@utils.register_interface(interfaces.HashAlgorithm)
class Whirlpool(object):
    name = "whirlpool"
    digest_size = 64
    block_size = 64


@utils.register_interface(interfaces.HashAlgorithm)
class MD5(object):
    name = "md5"
    digest_size = 16
    block_size = 64

########NEW FILE########
__FILENAME__ = hmac
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

from cryptography import utils
from cryptography.exceptions import (
    AlreadyFinalized, InvalidSignature, UnsupportedAlgorithm, _Reasons
)
from cryptography.hazmat.backends.interfaces import HMACBackend
from cryptography.hazmat.primitives import constant_time, interfaces


@utils.register_interface(interfaces.HashContext)
class HMAC(object):
    def __init__(self, key, algorithm, backend, ctx=None):
        if not isinstance(backend, HMACBackend):
            raise UnsupportedAlgorithm(
                "Backend object does not implement HMACBackend.",
                _Reasons.BACKEND_MISSING_INTERFACE
            )

        if not isinstance(algorithm, interfaces.HashAlgorithm):
            raise TypeError("Expected instance of interfaces.HashAlgorithm.")
        self.algorithm = algorithm

        self._backend = backend
        self._key = key
        if ctx is None:
            self._ctx = self._backend.create_hmac_ctx(key, self.algorithm)
        else:
            self._ctx = ctx

    def update(self, msg):
        if self._ctx is None:
            raise AlreadyFinalized("Context was already finalized.")
        if not isinstance(msg, bytes):
            raise TypeError("msg must be bytes.")
        self._ctx.update(msg)

    def copy(self):
        if self._ctx is None:
            raise AlreadyFinalized("Context was already finalized.")
        return HMAC(
            self._key,
            self.algorithm,
            backend=self._backend,
            ctx=self._ctx.copy()
        )

    def finalize(self):
        if self._ctx is None:
            raise AlreadyFinalized("Context was already finalized.")
        digest = self._ctx.finalize()
        self._ctx = None
        return digest

    def verify(self, signature):
        if not isinstance(signature, bytes):
            raise TypeError("signature must be bytes.")
        digest = self.finalize()
        if not constant_time.bytes_eq(digest, signature):
            raise InvalidSignature("Signature did not match digest.")

########NEW FILE########
__FILENAME__ = interfaces
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import abc

import six


@six.add_metaclass(abc.ABCMeta)
class CipherAlgorithm(object):
    @abc.abstractproperty
    def name(self):
        """
        A string naming this mode (e.g. "AES", "Camellia").
        """

    @abc.abstractproperty
    def key_size(self):
        """
        The size of the key being used as an integer in bits (e.g. 128, 256).
        """


@six.add_metaclass(abc.ABCMeta)
class BlockCipherAlgorithm(object):
    @abc.abstractproperty
    def block_size(self):
        """
        The size of a block as an integer in bits (e.g. 64, 128).
        """


@six.add_metaclass(abc.ABCMeta)
class Mode(object):
    @abc.abstractproperty
    def name(self):
        """
        A string naming this mode (e.g. "ECB", "CBC").
        """

    @abc.abstractmethod
    def validate_for_algorithm(self, algorithm):
        """
        Checks that all the necessary invariants of this (mode, algorithm)
        combination are met.
        """


@six.add_metaclass(abc.ABCMeta)
class ModeWithInitializationVector(object):
    @abc.abstractproperty
    def initialization_vector(self):
        """
        The value of the initialization vector for this mode as bytes.
        """


@six.add_metaclass(abc.ABCMeta)
class ModeWithNonce(object):
    @abc.abstractproperty
    def nonce(self):
        """
        The value of the nonce for this mode as bytes.
        """


@six.add_metaclass(abc.ABCMeta)
class ModeWithAuthenticationTag(object):
    @abc.abstractproperty
    def tag(self):
        """
        The value of the tag supplied to the constructor of this mode.
        """


@six.add_metaclass(abc.ABCMeta)
class CipherContext(object):
    @abc.abstractmethod
    def update(self, data):
        """
        Processes the provided bytes through the cipher and returns the results
        as bytes.
        """

    @abc.abstractmethod
    def finalize(self):
        """
        Returns the results of processing the final block as bytes.
        """


@six.add_metaclass(abc.ABCMeta)
class AEADCipherContext(object):
    @abc.abstractmethod
    def authenticate_additional_data(self, data):
        """
        Authenticates the provided bytes.
        """


@six.add_metaclass(abc.ABCMeta)
class AEADEncryptionContext(object):
    @abc.abstractproperty
    def tag(self):
        """
        Returns tag bytes. This is only available after encryption is
        finalized.
        """


@six.add_metaclass(abc.ABCMeta)
class PaddingContext(object):
    @abc.abstractmethod
    def update(self, data):
        """
        Pads the provided bytes and returns any available data as bytes.
        """

    @abc.abstractmethod
    def finalize(self):
        """
        Finalize the padding, returns bytes.
        """


@six.add_metaclass(abc.ABCMeta)
class HashAlgorithm(object):
    @abc.abstractproperty
    def name(self):
        """
        A string naming this algorithm (e.g. "sha256", "md5").
        """

    @abc.abstractproperty
    def digest_size(self):
        """
        The size of the resulting digest in bytes.
        """

    @abc.abstractproperty
    def block_size(self):
        """
        The internal block size of the hash algorithm in bytes.
        """


@six.add_metaclass(abc.ABCMeta)
class HashContext(object):
    @abc.abstractproperty
    def algorithm(self):
        """
        A HashAlgorithm that will be used by this context.
        """

    @abc.abstractmethod
    def update(self, data):
        """
        Processes the provided bytes through the hash.
        """

    @abc.abstractmethod
    def finalize(self):
        """
        Finalizes the hash context and returns the hash digest as bytes.
        """

    @abc.abstractmethod
    def copy(self):
        """
        Return a HashContext that is a copy of the current context.
        """


@six.add_metaclass(abc.ABCMeta)
class RSAPrivateKey(object):
    @abc.abstractmethod
    def signer(self, padding, algorithm, backend):
        """
        Returns an AsymmetricSignatureContext used for signing data.
        """

    @abc.abstractproperty
    def modulus(self):
        """
        The public modulus of the RSA key.
        """

    @abc.abstractproperty
    def public_exponent(self):
        """
        The public exponent of the RSA key.
        """

    @abc.abstractproperty
    def private_exponent(self):
        """
        The private exponent of the RSA key.
        """

    @abc.abstractproperty
    def key_size(self):
        """
        The bit length of the public modulus.
        """

    @abc.abstractmethod
    def public_key(self):
        """
        The RSAPublicKey associated with this private key.
        """

    @abc.abstractproperty
    def n(self):
        """
        The public modulus of the RSA key. Alias for modulus.
        """

    @abc.abstractproperty
    def p(self):
        """
        One of the two primes used to generate d.
        """

    @abc.abstractproperty
    def q(self):
        """
        One of the two primes used to generate d.
        """

    @abc.abstractproperty
    def d(self):
        """
        The private exponent. This can be calculated using p and q. Alias for
        private_exponent.
        """

    @abc.abstractproperty
    def dmp1(self):
        """
        A Chinese remainder theorem coefficient used to speed up RSA
        calculations.  Calculated as: d mod (p-1)
        """

    @abc.abstractproperty
    def dmq1(self):
        """
        A Chinese remainder theorem coefficient used to speed up RSA
        calculations.  Calculated as: d mod (q-1)
        """

    @abc.abstractproperty
    def iqmp(self):
        """
        A Chinese remainder theorem coefficient used to speed up RSA
        calculations. The modular inverse of q modulo p
        """

    @abc.abstractproperty
    def e(self):
        """
        The public exponent of the RSA key. Alias for public_exponent.
        """


@six.add_metaclass(abc.ABCMeta)
class RSAPublicKey(object):
    @abc.abstractmethod
    def verifier(self, signature, padding, algorithm, backend):
        """
        Returns an AsymmetricVerificationContext used for verifying signatures.
        """

    @abc.abstractproperty
    def modulus(self):
        """
        The public modulus of the RSA key.
        """

    @abc.abstractproperty
    def public_exponent(self):
        """
        The public exponent of the RSA key.
        """

    @abc.abstractproperty
    def key_size(self):
        """
        The bit length of the public modulus.
        """

    @abc.abstractproperty
    def n(self):
        """
        The public modulus of the RSA key. Alias for modulus.
        """

    @abc.abstractproperty
    def e(self):
        """
        The public exponent of the RSA key. Alias for public_exponent.
        """


@six.add_metaclass(abc.ABCMeta)
class DSAParameters(object):
    @abc.abstractproperty
    def modulus(self):
        """
        The prime modulus that's used in generating the DSA keypair and used
        in the DSA signing and verification processes.
        """

    @abc.abstractproperty
    def subgroup_order(self):
        """
        The subgroup order that's used in generating the DSA keypair
        by the generator and used in the DSA signing and verification
        processes.
        """

    @abc.abstractproperty
    def generator(self):
        """
        The generator that is used in generating the DSA keypair and used
        in the DSA signing and verification processes.
        """

    @abc.abstractproperty
    def p(self):
        """
        The prime modulus that's used in generating the DSA keypair and used
        in the DSA signing and verification processes. Alias for modulus.
        """

    @abc.abstractproperty
    def q(self):
        """
        The subgroup order that's used in generating the DSA keypair
        by the generator and used in the DSA signing and verification
        processes. Alias for subgroup_order.
        """

    @abc.abstractproperty
    def g(self):
        """
        The generator that is used in generating the DSA keypair and used
        in the DSA signing and verification processes. Alias for generator.
        """


@six.add_metaclass(abc.ABCMeta)
class DSAPrivateKey(object):
    @abc.abstractproperty
    def key_size(self):
        """
        The bit length of the prime modulus.
        """

    @abc.abstractmethod
    def public_key(self):
        """
        The DSAPublicKey associated with this private key.
        """

    @abc.abstractproperty
    def x(self):
        """
        The private key "x" in the DSA structure.
        """

    @abc.abstractproperty
    def y(self):
        """
        The public key.
        """

    @abc.abstractmethod
    def parameters(self):
        """
        The DSAParameters object associated with this private key.
        """


@six.add_metaclass(abc.ABCMeta)
class DSAPublicKey(object):
    @abc.abstractproperty
    def key_size(self):
        """
        The bit length of the prime modulus.
        """

    @abc.abstractproperty
    def y(self):
        """
        The public key.
        """

    @abc.abstractmethod
    def parameters(self):
        """
        The DSAParameters object associated with this public key.
        """


@six.add_metaclass(abc.ABCMeta)
class AsymmetricSignatureContext(object):
    @abc.abstractmethod
    def update(self, data):
        """
        Processes the provided bytes and returns nothing.
        """

    @abc.abstractmethod
    def finalize(self):
        """
        Returns the signature as bytes.
        """


@six.add_metaclass(abc.ABCMeta)
class AsymmetricVerificationContext(object):
    @abc.abstractmethod
    def update(self, data):
        """
        Processes the provided bytes and returns nothing.
        """

    @abc.abstractmethod
    def verify(self):
        """
        Raises an exception if the bytes provided to update do not match the
        signature or the signature does not match the public key.
        """


@six.add_metaclass(abc.ABCMeta)
class AsymmetricPadding(object):
    @abc.abstractproperty
    def name(self):
        """
        A string naming this padding (e.g. "PSS", "PKCS1").
        """


@six.add_metaclass(abc.ABCMeta)
class KeyDerivationFunction(object):
    @abc.abstractmethod
    def derive(self, key_material):
        """
        Deterministically generates and returns a new key based on the existing
        key material.
        """

    @abc.abstractmethod
    def verify(self, key_material, expected_key):
        """
        Checks whether the key generated by the key material matches the
        expected derived key. Raises an exception if they do not match.
        """


@six.add_metaclass(abc.ABCMeta)
class CMACContext(object):
    @abc.abstractmethod
    def update(self, data):
        """
        Processes the provided bytes.
        """

    def finalize(self):
        """
        Returns the message authentication code as bytes.
        """

    @abc.abstractmethod
    def copy(self):
        """
        Return a CMACContext that is a copy of the current context.
        """

########NEW FILE########
__FILENAME__ = hkdf
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import six

from cryptography import utils
from cryptography.exceptions import (
    AlreadyFinalized, InvalidKey, UnsupportedAlgorithm, _Reasons
)
from cryptography.hazmat.backends.interfaces import HMACBackend
from cryptography.hazmat.primitives import constant_time, hmac, interfaces


@utils.register_interface(interfaces.KeyDerivationFunction)
class HKDF(object):
    def __init__(self, algorithm, length, salt, info, backend):
        if not isinstance(backend, HMACBackend):
            raise UnsupportedAlgorithm(
                "Backend object does not implement HMACBackend.",
                _Reasons.BACKEND_MISSING_INTERFACE
            )

        self._algorithm = algorithm

        if not isinstance(salt, bytes) and salt is not None:
            raise TypeError("salt must be bytes.")

        if salt is None:
            salt = b"\x00" * (self._algorithm.digest_size // 8)

        self._salt = salt

        self._backend = backend

        self._hkdf_expand = HKDFExpand(self._algorithm, length, info, backend)

    def _extract(self, key_material):
        h = hmac.HMAC(self._salt, self._algorithm, backend=self._backend)
        h.update(key_material)
        return h.finalize()

    def derive(self, key_material):
        if not isinstance(key_material, bytes):
            raise TypeError("key_material must be bytes.")

        return self._hkdf_expand.derive(self._extract(key_material))

    def verify(self, key_material, expected_key):
        if not constant_time.bytes_eq(self.derive(key_material), expected_key):
            raise InvalidKey


@utils.register_interface(interfaces.KeyDerivationFunction)
class HKDFExpand(object):
    def __init__(self, algorithm, length, info, backend):
        if not isinstance(backend, HMACBackend):
            raise UnsupportedAlgorithm(
                "Backend object does not implement HMACBackend.",
                _Reasons.BACKEND_MISSING_INTERFACE
            )

        self._algorithm = algorithm

        self._backend = backend

        max_length = 255 * (algorithm.digest_size // 8)

        if length > max_length:
            raise ValueError(
                "Can not derive keys larger than {0} octets.".format(
                    max_length
                ))

        self._length = length

        if not isinstance(info, bytes) and info is not None:
            raise TypeError("info must be bytes.")

        if info is None:
            info = b""

        self._info = info

        self._used = False

    def _expand(self, key_material):
        output = [b""]
        counter = 1

        while (self._algorithm.digest_size // 8) * len(output) < self._length:
            h = hmac.HMAC(key_material, self._algorithm, backend=self._backend)
            h.update(output[-1])
            h.update(self._info)
            h.update(six.int2byte(counter))
            output.append(h.finalize())
            counter += 1

        return b"".join(output)[:self._length]

    def derive(self, key_material):
        if not isinstance(key_material, bytes):
            raise TypeError("key_material must be bytes.")

        if self._used:
            raise AlreadyFinalized

        self._used = True
        return self._expand(key_material)

    def verify(self, key_material, expected_key):
        if not constant_time.bytes_eq(self.derive(key_material), expected_key):
            raise InvalidKey

########NEW FILE########
__FILENAME__ = pbkdf2
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

from cryptography import utils
from cryptography.exceptions import (
    AlreadyFinalized, InvalidKey, UnsupportedAlgorithm, _Reasons
)
from cryptography.hazmat.backends.interfaces import PBKDF2HMACBackend
from cryptography.hazmat.primitives import constant_time, interfaces


@utils.register_interface(interfaces.KeyDerivationFunction)
class PBKDF2HMAC(object):
    def __init__(self, algorithm, length, salt, iterations, backend):
        if not isinstance(backend, PBKDF2HMACBackend):
            raise UnsupportedAlgorithm(
                "Backend object does not implement PBKDF2HMACBackend.",
                _Reasons.BACKEND_MISSING_INTERFACE
            )

        if not backend.pbkdf2_hmac_supported(algorithm):
            raise UnsupportedAlgorithm(
                "{0} is not supported for PBKDF2 by this backend.".format(
                    algorithm.name),
                _Reasons.UNSUPPORTED_HASH
            )
        self._used = False
        self._algorithm = algorithm
        self._length = length
        if not isinstance(salt, bytes):
            raise TypeError("salt must be bytes.")
        self._salt = salt
        self._iterations = iterations
        self._backend = backend

    def derive(self, key_material):
        if self._used:
            raise AlreadyFinalized("PBKDF2 instances can only be used once.")
        self._used = True

        if not isinstance(key_material, bytes):
            raise TypeError("key_material must be bytes.")
        return self._backend.derive_pbkdf2_hmac(
            self._algorithm,
            self._length,
            self._salt,
            self._iterations,
            key_material
        )

    def verify(self, key_material, expected_key):
        derived_key = self.derive(key_material)
        if not constant_time.bytes_eq(derived_key, expected_key):
            raise InvalidKey("Keys do not match.")

########NEW FILE########
__FILENAME__ = padding
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import sys

import cffi

import six

from cryptography import utils
from cryptography.exceptions import AlreadyFinalized
from cryptography.hazmat.bindings.utils import _create_modulename
from cryptography.hazmat.primitives import interfaces


TYPES = """
uint8_t Cryptography_check_pkcs7_padding(const uint8_t *, uint8_t);
"""

FUNCTIONS = """
/* Returns the value of the input with the most-significant-bit copied to all
   of the bits. */
static uint8_t Cryptography_DUPLICATE_MSB_TO_ALL(uint8_t a) {
    return (1 - (a >> (sizeof(uint8_t) * 8 - 1))) - 1;
}

/* This returns 0xFF if a < b else 0x00, but does so in a constant time
   fashion */
static uint8_t Cryptography_constant_time_lt(uint8_t a, uint8_t b) {
    a -= b;
    return Cryptography_DUPLICATE_MSB_TO_ALL(a);
}

uint8_t Cryptography_check_pkcs7_padding(const uint8_t *data,
                                         uint8_t block_len) {
    uint8_t i;
    uint8_t pad_size = data[block_len - 1];
    uint8_t mismatch = 0;
    for (i = 0; i < block_len; i++) {
        unsigned int mask = Cryptography_constant_time_lt(i, pad_size);
        uint8_t b = data[block_len - 1 - i];
        mismatch |= (mask & (pad_size ^ b));
    }

    /* Check to make sure the pad_size was within the valid range. */
    mismatch |= ~Cryptography_constant_time_lt(0, pad_size);
    mismatch |= Cryptography_constant_time_lt(block_len, pad_size);

    /* Make sure any bits set are copied to the lowest bit */
    mismatch |= mismatch >> 4;
    mismatch |= mismatch >> 2;
    mismatch |= mismatch >> 1;
    /* Now check the low bit to see if it's set */
    return (mismatch & 1) == 0;
}
"""

_ffi = cffi.FFI()
_ffi.cdef(TYPES)
_lib = _ffi.verify(
    source=FUNCTIONS,
    modulename=_create_modulename([TYPES], FUNCTIONS, sys.version),
    ext_package="cryptography",
)


class PKCS7(object):
    def __init__(self, block_size):
        if not (0 <= block_size < 256):
            raise ValueError("block_size must be in range(0, 256).")

        if block_size % 8 != 0:
            raise ValueError("block_size must be a multiple of 8.")

        self.block_size = block_size

    def padder(self):
        return _PKCS7PaddingContext(self.block_size)

    def unpadder(self):
        return _PKCS7UnpaddingContext(self.block_size)


@utils.register_interface(interfaces.PaddingContext)
class _PKCS7PaddingContext(object):
    def __init__(self, block_size):
        self.block_size = block_size
        # TODO: more copies than necessary, we should use zero-buffer (#193)
        self._buffer = b""

    def update(self, data):
        if self._buffer is None:
            raise AlreadyFinalized("Context was already finalized.")

        if not isinstance(data, bytes):
            raise TypeError("data must be bytes.")

        self._buffer += data

        finished_blocks = len(self._buffer) // (self.block_size // 8)

        result = self._buffer[:finished_blocks * (self.block_size // 8)]
        self._buffer = self._buffer[finished_blocks * (self.block_size // 8):]

        return result

    def finalize(self):
        if self._buffer is None:
            raise AlreadyFinalized("Context was already finalized.")

        pad_size = self.block_size // 8 - len(self._buffer)
        result = self._buffer + six.int2byte(pad_size) * pad_size
        self._buffer = None
        return result


@utils.register_interface(interfaces.PaddingContext)
class _PKCS7UnpaddingContext(object):
    def __init__(self, block_size):
        self.block_size = block_size
        # TODO: more copies than necessary, we should use zero-buffer (#193)
        self._buffer = b""

    def update(self, data):
        if self._buffer is None:
            raise AlreadyFinalized("Context was already finalized.")

        if not isinstance(data, bytes):
            raise TypeError("data must be bytes.")

        self._buffer += data

        finished_blocks = max(
            len(self._buffer) // (self.block_size // 8) - 1,
            0
        )

        result = self._buffer[:finished_blocks * (self.block_size // 8)]
        self._buffer = self._buffer[finished_blocks * (self.block_size // 8):]

        return result

    def finalize(self):
        if self._buffer is None:
            raise AlreadyFinalized("Context was already finalized.")

        if len(self._buffer) != self.block_size // 8:
            raise ValueError("Invalid padding bytes.")

        valid = _lib.Cryptography_check_pkcs7_padding(
            self._buffer, self.block_size // 8
        )

        if not valid:
            raise ValueError("Invalid padding bytes.")

        pad_size = six.indexbytes(self._buffer, -1)
        res = self._buffer[:-pad_size]
        self._buffer = None
        return res

########NEW FILE########
__FILENAME__ = serialization
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function


def load_pem_traditional_openssl_private_key(data, password, backend):
    return backend.load_traditional_openssl_pem_private_key(
        data, password
    )


def load_pem_pkcs8_private_key(data, password, backend):
    return backend.load_pkcs8_pem_private_key(
        data, password
    )

########NEW FILE########
__FILENAME__ = hotp
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import struct

import six

from cryptography.exceptions import (
    InvalidToken, UnsupportedAlgorithm, _Reasons
)
from cryptography.hazmat.backends.interfaces import HMACBackend
from cryptography.hazmat.primitives import constant_time, hmac
from cryptography.hazmat.primitives.hashes import SHA1, SHA256, SHA512


class HOTP(object):
    def __init__(self, key, length, algorithm, backend):
        if not isinstance(backend, HMACBackend):
            raise UnsupportedAlgorithm(
                "Backend object does not implement HMACBackend.",
                _Reasons.BACKEND_MISSING_INTERFACE
            )

        if len(key) < 16:
            raise ValueError("Key length has to be at least 128 bits.")

        if not isinstance(length, six.integer_types):
            raise TypeError("Length parameter must be an integer type.")

        if length < 6 or length > 8:
            raise ValueError("Length of HOTP has to be between 6 to 8.")

        if not isinstance(algorithm, (SHA1, SHA256, SHA512)):
            raise TypeError("Algorithm must be SHA1, SHA256 or SHA512.")

        self._key = key
        self._length = length
        self._algorithm = algorithm
        self._backend = backend

    def generate(self, counter):
        truncated_value = self._dynamic_truncate(counter)
        hotp = truncated_value % (10 ** self._length)
        return "{0:0{1}}".format(hotp, self._length).encode()

    def verify(self, hotp, counter):
        if not constant_time.bytes_eq(self.generate(counter), hotp):
            raise InvalidToken("Supplied HOTP value does not match.")

    def _dynamic_truncate(self, counter):
        ctx = hmac.HMAC(self._key, self._algorithm, self._backend)
        ctx.update(struct.pack(">Q", counter))
        hmac_value = ctx.finalize()

        offset = six.indexbytes(hmac_value, len(hmac_value) - 1) & 0b1111
        p = hmac_value[offset:offset + 4]
        return struct.unpack(">I", p)[0] & 0x7fffffff

########NEW FILE########
__FILENAME__ = totp
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

from cryptography.exceptions import (
    InvalidToken, UnsupportedAlgorithm, _Reasons
)
from cryptography.hazmat.backends.interfaces import HMACBackend
from cryptography.hazmat.primitives import constant_time
from cryptography.hazmat.primitives.twofactor.hotp import HOTP


class TOTP(object):
    def __init__(self, key, length, algorithm, time_step, backend):
        if not isinstance(backend, HMACBackend):
            raise UnsupportedAlgorithm(
                "Backend object does not implement HMACBackend.",
                _Reasons.BACKEND_MISSING_INTERFACE
            )

        self._time_step = time_step
        self._hotp = HOTP(key, length, algorithm, backend)

    def generate(self, time):
        counter = int(time / self._time_step)
        return self._hotp.generate(counter)

    def verify(self, totp, time):
        if not constant_time.bytes_eq(self.generate(time), totp):
            raise InvalidToken("Supplied TOTP value does not match.")

########NEW FILE########
__FILENAME__ = utils
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import sys


DeprecatedIn04 = DeprecationWarning


def register_interface(iface):
    def register_decorator(klass):
        iface.register(klass)
        return klass
    return register_decorator


def bit_length(x):
    if sys.version_info >= (2, 7):
        return x.bit_length()
    else:
        return len(bin(x)) - (2 + (x <= 0))

########NEW FILE########
__FILENAME__ = __about__
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import absolute_import, division, print_function

__all__ = [
    "__title__", "__summary__", "__uri__", "__version__", "__author__",
    "__email__", "__license__", "__copyright__",
]

__title__ = "cryptography"
__summary__ = ("cryptography is a package which provides cryptographic recipes"
               " and primitives to Python developers.")
__uri__ = "https://github.com/pyca/cryptography"

__version__ = "0.5.dev1"

__author__ = "The cryptography developers"
__email__ = "cryptography-dev@python.org"

__license__ = "Apache License, Version 2.0"
__copyright__ = "Copyright 2013-2014 %s" % __author__

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# Cryptography documentation build configuration file, created by
# sphinx-quickstart on Tue Aug  6 19:19:14 2013.
#
# This file is execfile()d with the current directory set to its containing dir
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

from __future__ import absolute_import, division, print_function

import os
import sys

try:
    import sphinx_rtd_theme
except ImportError:
    sphinx_rtd_theme = None

try:
    from sphinxcontrib import spelling
except ImportError:
    spelling = None


# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions  coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'cryptography-docs',
]

if spelling is not None:
    extensions.append('sphinxcontrib.spelling')

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
# source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'Cryptography'
copyright = '2013-2014, Individual Contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#

base_dir = os.path.join(os.path.dirname(__file__), os.pardir)
about = {}
with open(os.path.join(base_dir, "cryptography", "__about__.py")) as f:
    exec(f.read(), about)

version = release = about["__version__"]

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
# language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
# today = ''
# Else, today_fmt is used as the format for a strftime call.
# today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents
# default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
# add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
# add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
# show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
# modindex_common_prefix = []


# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.

if sphinx_rtd_theme:
    html_theme = "sphinx_rtd_theme"
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
else:
    html_theme = "default"

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
# html_theme_options = {}

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
# html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
# html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
# html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
# html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
# html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
# html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
# html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
# html_additional_pages = {}

# If false, no module index is generated.
# html_domain_indices = True

# If false, no index is generated.
# html_use_index = True

# If true, the index is split into individual pages for each letter.
# html_split_index = False

# If true, links to the reST sources are added to the pages.
# html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
# html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
# html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
# html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
# html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Cryptographydoc'


# -- Options for LaTeX output -------------------------------------------------

latex_elements = {
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual])
latex_documents = [
    ('index', 'Cryptography.tex', 'Cryptography Documentation',
        'Individual Contributors', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
# latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
# latex_use_parts = False

# If true, show page references after internal links.
# latex_show_pagerefs = False

# If true, show URL addresses after external links.
# latex_show_urls = False

# Documents to append as an appendix to all manuals.
# latex_appendices = []

# If false, no module index is generated.
# latex_domain_indices = True


# -- Options for manual page output -------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'cryptography', 'Cryptography Documentation',
        ['Individual Contributors'], 1)
]

# If true, show URL addresses after external links.
# man_show_urls = False


# -- Options for Texinfo output -----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'Cryptography', 'Cryptography Documentation',
        'Individual Contributors', 'Cryptography',
        'One line description of project.',
        'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
# texinfo_appendices = []

# If false, no module index is generated.
# texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
# texinfo_show_urls = 'footnote'

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

epub_theme = 'epub'

########NEW FILE########
__FILENAME__ = cryptography-docs
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

from docutils import nodes

from sphinx.util.compat import Directive, make_admonition


DANGER_MESSAGE = """
This is a "Hazardous Materials" module. You should **ONLY** use it if you're
100% absolutely sure that you know what you're doing because this module is
full of land mines, dragons, and dinosaurs with laser guns.
"""

DANGER_ALTERNATE = """

You may instead be interested in :doc:`{alternate}`.
"""


class HazmatDirective(Directive):
    has_content = True

    def run(self):
        message = DANGER_MESSAGE
        if self.content:
            message += DANGER_ALTERNATE.format(alternate=self.content[0])

        ad = make_admonition(
            Hazmat,
            self.name,
            [],
            self.options,
            nodes.paragraph("", message),
            self.lineno,
            self.content_offset,
            self.block_text,
            self.state,
            self.state_machine
        )
        ad[0].line = self.lineno
        return ad


class Hazmat(nodes.Admonition, nodes.Element):
    pass


def html_visit_hazmat_node(self, node):
    return self.visit_admonition(node, "danger")


def latex_visit_hazmat_node(self, node):
    return self.visit_admonition(node)


def depart_hazmat_node(self, node):
    return self.depart_admonition(node)


def setup(app):
    app.add_node(
        Hazmat,
        html=(html_visit_hazmat_node, depart_hazmat_node),
        latex=(latex_visit_hazmat_node, depart_hazmat_node),
    )
    app.add_directive("hazmat", HazmatDirective)

########NEW FILE########
__FILENAME__ = generate_cast5
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import binascii

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import algorithms, base, modes


def encrypt(mode, key, iv, plaintext):
    cipher = base.Cipher(
        algorithms.CAST5(binascii.unhexlify(key)),
        mode(binascii.unhexlify(iv)),
        default_backend()
    )
    encryptor = cipher.encryptor()
    ct = encryptor.update(binascii.unhexlify(plaintext))
    ct += encryptor.finalize()
    return binascii.hexlify(ct)


def build_vectors(mode, filename):
    vector_file = open(filename, "r")

    count = 0
    output = []
    key = None
    iv = None
    plaintext = None
    for line in vector_file:
        line = line.strip()
        if line.startswith("KEY"):
            if count != 0:
                output.append("CIPHERTEXT = {}".format(
                    encrypt(mode, key, iv, plaintext))
                )
            output.append("\nCOUNT = {}".format(count))
            count += 1
            name, key = line.split(" = ")
            output.append("KEY = {}".format(key))
        elif line.startswith("IV"):
            name, iv = line.split(" = ")
            iv = iv[0:16]
            output.append("IV = {}".format(iv))
        elif line.startswith("PLAINTEXT"):
            name, plaintext = line.split(" = ")
            output.append("PLAINTEXT = {}".format(plaintext))

    output.append("CIPHERTEXT = {}".format(encrypt(mode, key, iv, plaintext)))
    return "\n".join(output)


def write_file(data, filename):
    with open(filename, "w") as f:
        f.write(data)

cbc_path = "tests/hazmat/primitives/vectors/ciphers/AES/CBC/CBCMMT128.rsp"
write_file(build_vectors(modes.CBC, cbc_path), "cast5-cbc.txt")
ofb_path = "tests/hazmat/primitives/vectors/ciphers/AES/OFB/OFBMMT128.rsp"
write_file(build_vectors(modes.OFB, ofb_path), "cast5-ofb.txt")
cfb_path = "tests/hazmat/primitives/vectors/ciphers/AES/CFB/CFB128MMT128.rsp"
write_file(build_vectors(modes.CFB, cfb_path), "cast5-cfb.txt")
ctr_path = "tests/hazmat/primitives/vectors/ciphers/AES/CTR/aes-128-ctr.txt"
write_file(build_vectors(modes.CTR, ctr_path), "cast5-ctr.txt")

########NEW FILE########
__FILENAME__ = generate_idea
import binascii

from cryptography.hazmat.backends.openssl.backend import backend
from cryptography.hazmat.primitives.ciphers import algorithms, base, modes


def encrypt(mode, key, iv, plaintext):
    cipher = base.Cipher(
        algorithms.IDEA(binascii.unhexlify(key)),
        mode(binascii.unhexlify(iv)),
        backend
    )
    encryptor = cipher.encryptor()
    ct = encryptor.update(binascii.unhexlify(plaintext))
    ct += encryptor.finalize()
    return binascii.hexlify(ct)


def build_vectors(mode, filename):
    with open(filename, "r") as f:
        vector_file = f.read().splitlines()

    count = 0
    output = []
    key = None
    iv = None
    plaintext = None
    for line in vector_file:
        line = line.strip()
        if line.startswith("KEY"):
            if count != 0:
                output.append("CIPHERTEXT = {0}".format(
                    encrypt(mode, key, iv, plaintext))
                )
            output.append("\nCOUNT = {0}".format(count))
            count += 1
            name, key = line.split(" = ")
            output.append("KEY = {0}".format(key))
        elif line.startswith("IV"):
            name, iv = line.split(" = ")
            iv = iv[0:16]
            output.append("IV = {0}".format(iv))
        elif line.startswith("PLAINTEXT"):
            name, plaintext = line.split(" = ")
            output.append("PLAINTEXT = {0}".format(plaintext))

    output.append("CIPHERTEXT = {0}".format(encrypt(mode, key, iv, plaintext)))
    return "\n".join(output)


def write_file(data, filename):
    with open(filename, "w") as f:
        f.write(data)

CBC_PATH = "tests/hazmat/primitives/vectors/ciphers/AES/CBC/CBCMMT128.rsp"
write_file(build_vectors(modes.CBC, CBC_PATH), "idea-cbc.txt")
OFB_PATH = "tests/hazmat/primitives/vectors/ciphers/AES/OFB/OFBMMT128.rsp"
write_file(build_vectors(modes.OFB, OFB_PATH), "idea-ofb.txt")
CFB_PATH = "tests/hazmat/primitives/vectors/ciphers/AES/CFB/CFB128MMT128.rsp"
write_file(build_vectors(modes.CFB, CFB_PATH), "idea-cfb.txt")

########NEW FILE########
__FILENAME__ = verify_idea
import binascii

import botan

from tests.utils import load_nist_vectors

BLOCK_SIZE = 64


def encrypt(mode, key, iv, plaintext):
    encryptor = botan.Cipher("IDEA/{0}/NoPadding".format(mode), "encrypt",
                             binascii.unhexlify(key))

    cipher_text = encryptor.cipher(binascii.unhexlify(plaintext),
                                   binascii.unhexlify(iv))
    return binascii.hexlify(cipher_text)


def verify_vectors(mode, filename):
    with open(filename, "r") as f:
        vector_file = f.read().splitlines()

    vectors = load_nist_vectors(vector_file)
    for vector in vectors:
        ct = encrypt(
            mode,
            vector["key"],
            vector["iv"],
            vector["plaintext"]
        )
        assert ct == vector["ciphertext"]


cbc_path = "tests/hazmat/primitives/vectors/ciphers/IDEA/idea-cbc.txt"
verify_vectors("CBC", cbc_path)
ofb_path = "tests/hazmat/primitives/vectors/ciphers/IDEA/idea-ofb.txt"
verify_vectors("OFB", ofb_path)
cfb_path = "tests/hazmat/primitives/vectors/ciphers/IDEA/idea-cfb.txt"
verify_vectors("CFB", cfb_path)

########NEW FILE########
__FILENAME__ = generate_seed
import binascii

from cryptography.hazmat.backends.openssl.backend import backend
from cryptography.hazmat.primitives.ciphers import algorithms, base, modes


def encrypt(mode, key, iv, plaintext):
    cipher = base.Cipher(
        algorithms.SEED(binascii.unhexlify(key)),
        mode(binascii.unhexlify(iv)),
        backend
    )
    encryptor = cipher.encryptor()
    ct = encryptor.update(binascii.unhexlify(plaintext))
    ct += encryptor.finalize()
    return binascii.hexlify(ct)


def build_vectors(mode, filename):
    with open(filename, "r") as f:
        vector_file = f.read().splitlines()

    count = 0
    output = []
    key = None
    iv = None
    plaintext = None
    for line in vector_file:
        line = line.strip()
        if line.startswith("KEY"):
            if count != 0:
                output.append("CIPHERTEXT = {0}".format(
                    encrypt(mode, key, iv, plaintext))
                )
            output.append("\nCOUNT = {0}".format(count))
            count += 1
            name, key = line.split(" = ")
            output.append("KEY = {0}".format(key))
        elif line.startswith("IV"):
            name, iv = line.split(" = ")
            output.append("IV = {0}".format(iv))
        elif line.startswith("PLAINTEXT"):
            name, plaintext = line.split(" = ")
            output.append("PLAINTEXT = {0}".format(plaintext))

    output.append("CIPHERTEXT = {0}".format(encrypt(mode, key, iv, plaintext)))
    return "\n".join(output)


def write_file(data, filename):
    with open(filename, "w") as f:
        f.write(data)

OFB_PATH = "vectors/cryptography_vectors/ciphers/AES/OFB/OFBMMT128.rsp"
write_file(build_vectors(modes.OFB, OFB_PATH), "seed-ofb.txt")
CFB_PATH = "vectors/cryptography_vectors/ciphers/AES/CFB/CFB128MMT128.rsp"
write_file(build_vectors(modes.CFB, CFB_PATH), "seed-cfb.txt")

########NEW FILE########
__FILENAME__ = verify_seed
import binascii

import botan

from tests.utils import load_nist_vectors


def encrypt(mode, key, iv, plaintext):
    encryptor = botan.Cipher("SEED/{0}/NoPadding".format(mode), "encrypt",
                             binascii.unhexlify(key))

    cipher_text = encryptor.cipher(binascii.unhexlify(plaintext),
                                   binascii.unhexlify(iv))
    return binascii.hexlify(cipher_text)


def verify_vectors(mode, filename):
    with open(filename, "r") as f:
        vector_file = f.read().splitlines()

    vectors = load_nist_vectors(vector_file)
    for vector in vectors:
        ct = encrypt(
            mode,
            vector["key"],
            vector["iv"],
            vector["plaintext"]
        )
        assert ct == vector["ciphertext"]


ofb_path = "vectors/cryptography_vectors/ciphers/SEED/seed-ofb.txt"
verify_vectors("OFB", ofb_path)
cfb_path = "vectors/cryptography_vectors/ciphers/SEED/seed-cfb.txt"
verify_vectors("CFB", cfb_path)

########NEW FILE########
__FILENAME__ = tasks
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import absolute_import, division, print_function

import getpass
import os
import time

import invoke

import requests


JENKINS_URL = "https://jenkins.cryptography.io/job/cryptography-wheel-builder"


def wait_for_build_completed():
    while True:
        response = requests.get(
            "{0}/lastBuild/api/json/".format(JENKINS_URL),
            headers={
                "Accept": "application/json",
            }
        )
        response.raise_for_status()
        if not response.json()["building"]:
            assert response.json()["result"] == "SUCCESS"
            break
        time.sleep(0.1)


def download_artifacts():
    response = requests.get(
        "{0}/lastBuild/api/json/".format(JENKINS_URL),
        headers={
            "Accept": "application/json"
        }
    )
    response.raise_for_status()
    assert not response.json()["building"]
    assert response.json()["result"] == "SUCCESS"

    paths = []

    for run in response.json()["runs"]:
        response = requests.get(
            run["url"] + "api/json/",
            headers={
                "Accept": "application/json",
            }
        )
        response.raise_for_status()
        for artifact in response.json()["artifacts"]:
            response = requests.get(
                "{0}artifact/{1}".format(run["url"], artifact["relativePath"])
            )
            out_path = os.path.join(
                os.path.dirname(__file__),
                "dist",
                artifact["fileName"],
            )
            with open(out_path, "wb") as f:
                f.write(response.content)
            paths.append(out_path)
    return paths


@invoke.task
def release(version):
    """
    ``version`` should be a string like '0.4' or '1.0'.
    """
    invoke.run("git tag -s {0}".format(version))
    invoke.run("git push --tags")

    invoke.run("python setup.py sdist")
    invoke.run("cd vectors/ && python setup.py sdist bdist_wheel")

    invoke.run(
        "twine upload -s dist/cryptography-{0}* "
        "vectors/dist/cryptography_vectors-{0}*".format(version)
    )

    token = getpass.getpass("Input the Jenkins token: ")
    response = requests.post(
        "{0}/build".format(JENKINS_URL),
        params={
            "token": token,
            "cause": "Building wheels for {0}".format(version)
        }
    )
    response.raise_for_status()
    wait_for_build_completed()
    paths = download_artifacts()
    invoke.run("twine upload {0}".format(" ".join(paths)))

########NEW FILE########
__FILENAME__ = conftest
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import pytest

from cryptography.hazmat.backends import _available_backends
from cryptography.hazmat.backends.interfaces import (
    CMACBackend, CipherBackend, DSABackend, HMACBackend, HashBackend,
    PBKDF2HMACBackend, PKCS8SerializationBackend, RSABackend,
    TraditionalOpenSSLSerializationBackend
)
from .utils import check_backend_support, check_for_iface, select_backends


def pytest_generate_tests(metafunc):
    names = metafunc.config.getoption("--backend")
    selected_backends = select_backends(names, _available_backends())

    if "backend" in metafunc.fixturenames:
        metafunc.parametrize("backend", selected_backends)


@pytest.mark.trylast
def pytest_runtest_setup(item):
    check_for_iface("hmac", HMACBackend, item)
    check_for_iface("cipher", CipherBackend, item)
    check_for_iface("cmac", CMACBackend, item)
    check_for_iface("hash", HashBackend, item)
    check_for_iface("pbkdf2hmac", PBKDF2HMACBackend, item)
    check_for_iface("dsa", DSABackend, item)
    check_for_iface("rsa", RSABackend, item)
    check_for_iface(
        "traditional_openssl_serialization",
        TraditionalOpenSSLSerializationBackend,
        item
    )
    check_for_iface(
        "pkcs8_serialization",
        PKCS8SerializationBackend,
        item
    )
    check_backend_support(item)


def pytest_addoption(parser):
    parser.addoption(
        "--backend", action="store", metavar="NAME",
        help="Only run tests matching the backend NAME."
    )

########NEW FILE########
__FILENAME__ = test_commoncrypto
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import pytest

from cryptography import utils
from cryptography.exceptions import InternalError, _Reasons
from cryptography.hazmat.bindings.commoncrypto.binding import Binding
from cryptography.hazmat.primitives import interfaces
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.base import Cipher
from cryptography.hazmat.primitives.ciphers.modes import CBC, GCM

from ...utils import raises_unsupported_algorithm


@utils.register_interface(interfaces.CipherAlgorithm)
class DummyCipher(object):
    name = "dummy-cipher"
    block_size = 128


@pytest.mark.skipif(not Binding.is_available(),
                    reason="CommonCrypto not available")
class TestCommonCrypto(object):
    def test_supports_cipher(self):
        from cryptography.hazmat.backends.commoncrypto.backend import backend
        assert backend.cipher_supported(None, None) is False

    def test_register_duplicate_cipher_adapter(self):
        from cryptography.hazmat.backends.commoncrypto.backend import backend
        with pytest.raises(ValueError):
            backend._register_cipher_adapter(
                AES, backend._lib.kCCAlgorithmAES128,
                CBC, backend._lib.kCCModeCBC
            )

    def test_handle_response(self):
        from cryptography.hazmat.backends.commoncrypto.backend import backend

        with pytest.raises(ValueError):
            backend._check_response(backend._lib.kCCAlignmentError)

        with pytest.raises(InternalError):
            backend._check_response(backend._lib.kCCMemoryFailure)

        with pytest.raises(InternalError):
            backend._check_response(backend._lib.kCCDecodeError)

    def test_nonexistent_aead_cipher(self):
        from cryptography.hazmat.backends.commoncrypto.backend import Backend
        b = Backend()
        cipher = Cipher(
            DummyCipher(), GCM(b"fake_iv_here"), backend=b,
        )
        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_CIPHER):
            cipher.encryptor()

########NEW FILE########
__FILENAME__ = test_multibackend
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

from cryptography import utils
from cryptography.exceptions import (
    UnsupportedAlgorithm, _Reasons
)
from cryptography.hazmat.backends.interfaces import (
    CMACBackend, CipherBackend, DSABackend, HMACBackend, HashBackend,
    PBKDF2HMACBackend, RSABackend
)
from cryptography.hazmat.backends.multibackend import MultiBackend
from cryptography.hazmat.primitives import cmac, hashes, hmac
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from ...utils import raises_unsupported_algorithm


@utils.register_interface(CipherBackend)
class DummyCipherBackend(object):
    def __init__(self, supported_ciphers):
        self._ciphers = supported_ciphers

    def cipher_supported(self, algorithm, mode):
        return (type(algorithm), type(mode)) in self._ciphers

    def create_symmetric_encryption_ctx(self, algorithm, mode):
        if not self.cipher_supported(algorithm, mode):
            raise UnsupportedAlgorithm("", _Reasons.UNSUPPORTED_CIPHER)

    def create_symmetric_decryption_ctx(self, algorithm, mode):
        if not self.cipher_supported(algorithm, mode):
            raise UnsupportedAlgorithm("", _Reasons.UNSUPPORTED_CIPHER)


@utils.register_interface(HashBackend)
class DummyHashBackend(object):
    def __init__(self, supported_algorithms):
        self._algorithms = supported_algorithms

    def hash_supported(self, algorithm):
        return type(algorithm) in self._algorithms

    def create_hash_ctx(self, algorithm):
        if not self.hash_supported(algorithm):
            raise UnsupportedAlgorithm("", _Reasons.UNSUPPORTED_HASH)


@utils.register_interface(HMACBackend)
class DummyHMACBackend(object):
    def __init__(self, supported_algorithms):
        self._algorithms = supported_algorithms

    def hmac_supported(self, algorithm):
        return type(algorithm) in self._algorithms

    def create_hmac_ctx(self, key, algorithm):
        if not self.hmac_supported(algorithm):
            raise UnsupportedAlgorithm("", _Reasons.UNSUPPORTED_HASH)


@utils.register_interface(PBKDF2HMACBackend)
class DummyPBKDF2HMACBackend(object):
    def __init__(self, supported_algorithms):
        self._algorithms = supported_algorithms

    def pbkdf2_hmac_supported(self, algorithm):
        return type(algorithm) in self._algorithms

    def derive_pbkdf2_hmac(self, algorithm, length, salt, iterations,
                           key_material):
        if not self.pbkdf2_hmac_supported(algorithm):
            raise UnsupportedAlgorithm("", _Reasons.UNSUPPORTED_HASH)


@utils.register_interface(RSABackend)
class DummyRSABackend(object):
    def generate_rsa_private_key(self, public_exponent, private_key):
        pass

    def create_rsa_signature_ctx(self, private_key, padding, algorithm):
        pass

    def create_rsa_verification_ctx(self, public_key, signature, padding,
                                    algorithm):
        pass

    def mgf1_hash_supported(self, algorithm):
        pass

    def rsa_padding_supported(self, padding):
        pass

    def generate_rsa_parameters_supported(self, public_exponent, key_size):
        pass

    def decrypt_rsa(self, private_key, ciphertext, padding):
        pass

    def encrypt_rsa(self, public_key, plaintext, padding):
        pass


@utils.register_interface(DSABackend)
class DummyDSABackend(object):
    def generate_dsa_parameters(self, key_size):
        pass

    def generate_dsa_private_key(self, parameters):
        pass

    def create_dsa_signature_ctx(self, private_key, algorithm):
        pass

    def create_dsa_verification_ctx(self, public_key, signature, algorithm):
        pass

    def dsa_hash_supported(self, algorithm):
        pass

    def dsa_parameters_supported(self, p, q, g):
        pass


@utils.register_interface(CMACBackend)
class DummyCMACBackend(object):
    def __init__(self, supported_algorithms):
        self._algorithms = supported_algorithms

    def cmac_algorithm_supported(self, algorithm):
        return type(algorithm) in self._algorithms

    def create_cmac_ctx(self, algorithm):
        if not self.cmac_algorithm_supported(algorithm):
            raise UnsupportedAlgorithm("", _Reasons.UNSUPPORTED_CIPHER)


class TestMultiBackend(object):
    def test_ciphers(self):
        backend = MultiBackend([
            DummyHashBackend([]),
            DummyCipherBackend([
                (algorithms.AES, modes.CBC),
            ])
        ])
        assert backend.cipher_supported(
            algorithms.AES(b"\x00" * 16), modes.CBC(b"\x00" * 16)
        )

        cipher = Cipher(
            algorithms.AES(b"\x00" * 16),
            modes.CBC(b"\x00" * 16),
            backend=backend
        )
        cipher.encryptor()
        cipher.decryptor()

        cipher = Cipher(
            algorithms.Camellia(b"\x00" * 16),
            modes.CBC(b"\x00" * 16),
            backend=backend
        )
        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_CIPHER):
            cipher.encryptor()
        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_CIPHER):
            cipher.decryptor()

    def test_hashes(self):
        backend = MultiBackend([
            DummyHashBackend([hashes.MD5])
        ])
        assert backend.hash_supported(hashes.MD5())

        hashes.Hash(hashes.MD5(), backend=backend)

        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_HASH):
            hashes.Hash(hashes.SHA1(), backend=backend)

    def test_hmac(self):
        backend = MultiBackend([
            DummyHMACBackend([hashes.MD5])
        ])
        assert backend.hmac_supported(hashes.MD5())

        hmac.HMAC(b"", hashes.MD5(), backend=backend)

        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_HASH):
            hmac.HMAC(b"", hashes.SHA1(), backend=backend)

    def test_pbkdf2(self):
        backend = MultiBackend([
            DummyPBKDF2HMACBackend([hashes.MD5])
        ])
        assert backend.pbkdf2_hmac_supported(hashes.MD5())

        backend.derive_pbkdf2_hmac(hashes.MD5(), 10, b"", 10, b"")

        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_HASH):
            backend.derive_pbkdf2_hmac(hashes.SHA1(), 10, b"", 10, b"")

    def test_rsa(self):
        backend = MultiBackend([
            DummyRSABackend()
        ])

        backend.generate_rsa_private_key(
            key_size=1024, public_exponent=65537
        )

        backend.create_rsa_signature_ctx("private_key", padding.PKCS1v15(),
                                         hashes.MD5())

        backend.create_rsa_verification_ctx("public_key", "sig",
                                            padding.PKCS1v15(), hashes.MD5())

        backend.mgf1_hash_supported(hashes.MD5())

        backend.rsa_padding_supported(padding.PKCS1v15())

        backend.generate_rsa_parameters_supported(65537, 1024)

        backend.encrypt_rsa("public_key", "encryptme", padding.PKCS1v15())

        backend.decrypt_rsa("private_key", "encrypted", padding.PKCS1v15())

        backend = MultiBackend([])
        with raises_unsupported_algorithm(
            _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM
        ):
            backend.generate_rsa_private_key(key_size=1024, public_exponent=3)

        with raises_unsupported_algorithm(
            _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM
        ):
            backend.create_rsa_signature_ctx("private_key", padding.PKCS1v15(),
                                             hashes.MD5())

        with raises_unsupported_algorithm(
            _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM
        ):
            backend.create_rsa_verification_ctx(
                "public_key", "sig", padding.PKCS1v15(), hashes.MD5())

        with raises_unsupported_algorithm(
            _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM
        ):
            backend.mgf1_hash_supported(hashes.MD5())

        with raises_unsupported_algorithm(
            _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM
        ):
            backend.rsa_padding_supported(padding.PKCS1v15())

        with raises_unsupported_algorithm(
            _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM
        ):
            backend.generate_rsa_parameters_supported(65537, 1024)

        with raises_unsupported_algorithm(
            _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM
        ):
            backend.encrypt_rsa("public_key", "encryptme", padding.PKCS1v15())

        with raises_unsupported_algorithm(
            _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM
        ):
            backend.decrypt_rsa("private_key", "encrypted", padding.PKCS1v15())

    def test_dsa(self):
        backend = MultiBackend([
            DummyDSABackend()
        ])

        backend.generate_dsa_parameters(key_size=1024)

        parameters = object()
        backend.generate_dsa_private_key(parameters)

        backend.create_dsa_verification_ctx("public_key", "sig", hashes.SHA1())
        backend.create_dsa_signature_ctx("private_key", hashes.SHA1())
        backend.dsa_hash_supported(hashes.SHA1())
        backend.dsa_parameters_supported(1, 2, 3)

        backend = MultiBackend([])
        with raises_unsupported_algorithm(
            _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM
        ):
            backend.generate_dsa_parameters(key_size=1024)

        with raises_unsupported_algorithm(
            _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM
        ):
            backend.generate_dsa_private_key(parameters)

        with raises_unsupported_algorithm(
            _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM
        ):
            backend.create_dsa_signature_ctx("private_key", hashes.SHA1())

        with raises_unsupported_algorithm(
            _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM
        ):
            backend.create_dsa_verification_ctx(
                "public_key", b"sig", hashes.SHA1()
            )

        with raises_unsupported_algorithm(
            _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM
        ):
            backend.dsa_hash_supported(hashes.SHA1())

        with raises_unsupported_algorithm(
            _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM
        ):
            backend.dsa_parameters_supported('p', 'q', 'g')

    def test_cmac(self):
        backend = MultiBackend([
            DummyCMACBackend([algorithms.AES])
        ])

        fake_key = b"\x00" * 16

        assert backend.cmac_algorithm_supported(
            algorithms.AES(fake_key)) is True

        cmac.CMAC(algorithms.AES(fake_key), backend)

        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_CIPHER):
            cmac.CMAC(algorithms.TripleDES(fake_key), backend)

########NEW FILE########
__FILENAME__ = test_openssl
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import pretend

import pytest

from cryptography import utils
from cryptography.exceptions import InternalError, _Reasons
from cryptography.hazmat.backends.openssl.backend import Backend, backend
from cryptography.hazmat.primitives import hashes, interfaces
from cryptography.hazmat.primitives.asymmetric import dsa, padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.modes import CBC, CTR
from cryptography.hazmat.primitives.interfaces import BlockCipherAlgorithm

from ...utils import raises_unsupported_algorithm


@utils.register_interface(interfaces.Mode)
class DummyMode(object):
    name = "dummy-mode"

    def validate_for_algorithm(self, algorithm):
        pass


@utils.register_interface(interfaces.CipherAlgorithm)
class DummyCipher(object):
    name = "dummy-cipher"


@utils.register_interface(interfaces.AsymmetricPadding)
class DummyPadding(object):
    name = "dummy-cipher"


@utils.register_interface(interfaces.HashAlgorithm)
class DummyHash(object):
    name = "dummy-hash"


class DummyMGF(object):
    _salt_length = 0


class TestOpenSSL(object):
    def test_backend_exists(self):
        assert backend

    def test_openssl_version_text(self):
        """
        This test checks the value of OPENSSL_VERSION_TEXT.

        Unfortunately, this define does not appear to have a
        formal content definition, so for now we'll test to see
        if it starts with OpenSSL as that appears to be true
        for every OpenSSL.
        """
        assert backend.openssl_version_text().startswith("OpenSSL")

    def test_supports_cipher(self):
        assert backend.cipher_supported(None, None) is False

    def test_aes_ctr_always_available(self):
        # AES CTR should always be available in both 0.9.8 and 1.0.0+
        assert backend.cipher_supported(AES(b"\x00" * 16),
                                        CTR(b"\x00" * 16)) is True

    def test_register_duplicate_cipher_adapter(self):
        with pytest.raises(ValueError):
            backend.register_cipher_adapter(AES, CBC, None)

    @pytest.mark.parametrize("mode", [DummyMode(), None])
    def test_nonexistent_cipher(self, mode):
        b = Backend()
        b.register_cipher_adapter(
            DummyCipher,
            type(mode),
            lambda backend, cipher, mode: backend._ffi.NULL
        )
        cipher = Cipher(
            DummyCipher(), mode, backend=b,
        )
        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_CIPHER):
            cipher.encryptor()

    def test_consume_errors(self):
        for i in range(10):
            backend._lib.ERR_put_error(backend._lib.ERR_LIB_EVP, 0, 0,
                                       b"test_openssl.py", -1)

        assert backend._lib.ERR_peek_error() != 0

        errors = backend._consume_errors()

        assert backend._lib.ERR_peek_error() == 0
        assert len(errors) == 10

    def test_openssl_error_string(self):
        backend._lib.ERR_put_error(
            backend._lib.ERR_LIB_EVP,
            backend._lib.EVP_F_EVP_DECRYPTFINAL_EX,
            0,
            b"test_openssl.py",
            -1
        )

        errors = backend._consume_errors()
        exc = backend._unknown_error(errors[0])

        assert (
            "digital envelope routines:"
            "EVP_DecryptFinal_ex:digital envelope routines" in str(exc)
        )

    def test_ssl_ciphers_registered(self):
        meth = backend._lib.TLSv1_method()
        ctx = backend._lib.SSL_CTX_new(meth)
        assert ctx != backend._ffi.NULL
        backend._lib.SSL_CTX_free(ctx)

    def test_evp_ciphers_registered(self):
        cipher = backend._lib.EVP_get_cipherbyname(b"aes-256-cbc")
        assert cipher != backend._ffi.NULL

    def test_error_strings_loaded(self):
        # returns a value in a static buffer
        err = backend._lib.ERR_error_string(101183626, backend._ffi.NULL)
        assert backend._ffi.string(err) == (
            b"error:0607F08A:digital envelope routines:EVP_EncryptFinal_ex:"
            b"data not multiple of block length"
        )

    def test_unknown_error_in_cipher_finalize(self):
        cipher = Cipher(AES(b"\0" * 16), CBC(b"\0" * 16), backend=backend)
        enc = cipher.encryptor()
        enc.update(b"\0")
        backend._lib.ERR_put_error(0, 0, 1,
                                   b"test_openssl.py", -1)
        with pytest.raises(InternalError):
            enc.finalize()

    def test_derive_pbkdf2_raises_unsupported_on_old_openssl(self):
        if backend.pbkdf2_hmac_supported(hashes.SHA256()):
            pytest.skip("Requires an older OpenSSL")
        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_HASH):
            backend.derive_pbkdf2_hmac(hashes.SHA256(), 10, b"", 1000, b"")

    @pytest.mark.skipif(
        backend._lib.OPENSSL_VERSION_NUMBER >= 0x1000000f,
        reason="Requires an older OpenSSL. Must be < 1.0.0"
    )
    def test_large_key_size_on_old_openssl(self):
        with pytest.raises(ValueError):
            dsa.DSAParameters.generate(2048, backend=backend)

        with pytest.raises(ValueError):
            dsa.DSAParameters.generate(3072, backend=backend)

    @pytest.mark.skipif(
        backend._lib.OPENSSL_VERSION_NUMBER < 0x1000000f,
        reason="Requires a newer OpenSSL. Must be >= 1.0.0"
    )
    def test_large_key_size_on_new_openssl(self):
        parameters = dsa.DSAParameters.generate(2048, backend)
        assert utils.bit_length(parameters.p) == 2048
        parameters = dsa.DSAParameters.generate(3072, backend)
        assert utils.bit_length(parameters.p) == 3072

    def test_int_to_bn(self):
        value = (2 ** 4242) - 4242
        bn = backend._int_to_bn(value)
        assert bn != backend._ffi.NULL
        bn = backend._ffi.gc(bn, backend._lib.BN_free)

        assert bn
        assert backend._bn_to_int(bn) == value

    def test_int_to_bn_inplace(self):
        value = (2 ** 4242) - 4242
        bn_ptr = backend._lib.BN_new()
        assert bn_ptr != backend._ffi.NULL
        bn_ptr = backend._ffi.gc(bn_ptr, backend._lib.BN_free)
        bn = backend._int_to_bn(value, bn_ptr)

        assert bn == bn_ptr
        assert backend._bn_to_int(bn_ptr) == value


class TestOpenSSLRandomEngine(object):
    def teardown_method(self, method):
        # we need to reset state to being default. backend is a shared global
        # for all these tests.
        backend.activate_osrandom_engine()
        current_default = backend._lib.ENGINE_get_default_RAND()
        name = backend._lib.ENGINE_get_name(current_default)
        assert name == backend._lib.Cryptography_osrandom_engine_name

    # This must be the first test in the class so that the teardown method
    # has not (potentially) altered the default engine.
    def test_osrandom_engine_is_default(self):
        e = backend._lib.ENGINE_get_default_RAND()
        name = backend._lib.ENGINE_get_name(e)
        assert name == backend._lib.Cryptography_osrandom_engine_name
        res = backend._lib.ENGINE_free(e)
        assert res == 1

    def test_osrandom_sanity_check(self):
        # This test serves as a check against catastrophic failure.
        buf = backend._ffi.new("char[]", 500)
        res = backend._lib.RAND_bytes(buf, 500)
        assert res == 1
        assert backend._ffi.buffer(buf)[:] != "\x00" * 500

    def test_activate_osrandom_already_default(self):
        e = backend._lib.ENGINE_get_default_RAND()
        name = backend._lib.ENGINE_get_name(e)
        assert name == backend._lib.Cryptography_osrandom_engine_name
        res = backend._lib.ENGINE_free(e)
        assert res == 1
        backend.activate_osrandom_engine()
        e = backend._lib.ENGINE_get_default_RAND()
        name = backend._lib.ENGINE_get_name(e)
        assert name == backend._lib.Cryptography_osrandom_engine_name
        res = backend._lib.ENGINE_free(e)
        assert res == 1

    def test_activate_osrandom_no_default(self):
        backend.activate_builtin_random()
        e = backend._lib.ENGINE_get_default_RAND()
        assert e == backend._ffi.NULL
        backend.activate_osrandom_engine()
        e = backend._lib.ENGINE_get_default_RAND()
        name = backend._lib.ENGINE_get_name(e)
        assert name == backend._lib.Cryptography_osrandom_engine_name
        res = backend._lib.ENGINE_free(e)
        assert res == 1

    def test_activate_builtin_random(self):
        e = backend._lib.ENGINE_get_default_RAND()
        assert e != backend._ffi.NULL
        name = backend._lib.ENGINE_get_name(e)
        assert name == backend._lib.Cryptography_osrandom_engine_name
        res = backend._lib.ENGINE_free(e)
        assert res == 1
        backend.activate_builtin_random()
        e = backend._lib.ENGINE_get_default_RAND()
        assert e == backend._ffi.NULL

    def test_activate_builtin_random_already_active(self):
        backend.activate_builtin_random()
        e = backend._lib.ENGINE_get_default_RAND()
        assert e == backend._ffi.NULL
        backend.activate_builtin_random()
        e = backend._lib.ENGINE_get_default_RAND()
        assert e == backend._ffi.NULL


class TestOpenSSLRSA(object):
    def test_generate_rsa_parameters_supported(self):
        assert backend.generate_rsa_parameters_supported(1, 1024) is False
        assert backend.generate_rsa_parameters_supported(4, 1024) is False
        assert backend.generate_rsa_parameters_supported(3, 1024) is True
        assert backend.generate_rsa_parameters_supported(3, 511) is False

    @pytest.mark.skipif(
        backend._lib.OPENSSL_VERSION_NUMBER >= 0x1000100f,
        reason="Requires an older OpenSSL. Must be < 1.0.1"
    )
    def test_non_sha1_pss_mgf1_hash_algorithm_on_old_openssl(self):
        private_key = rsa.RSAPrivateKey.generate(
            public_exponent=65537,
            key_size=512,
            backend=backend
        )
        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_HASH):
            private_key.signer(
                padding.PSS(
                    mgf=padding.MGF1(
                        algorithm=hashes.SHA256(),
                    ),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA1(),
                backend
            )
        public_key = private_key.public_key()
        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_HASH):
            public_key.verifier(
                b"sig",
                padding.PSS(
                    mgf=padding.MGF1(
                        algorithm=hashes.SHA256(),
                    ),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA1(),
                backend
            )

    def test_unsupported_mgf1_hash_algorithm(self):
        assert backend.mgf1_hash_supported(DummyHash()) is False

    def test_rsa_padding_unsupported_pss_mgf1_hash(self):
        assert backend.rsa_padding_supported(
            padding.PSS(mgf=padding.MGF1(DummyHash()), salt_length=0)
        ) is False

    def test_rsa_padding_unsupported(self):
        assert backend.rsa_padding_supported(DummyPadding()) is False

    def test_rsa_padding_supported_pkcs1v15(self):
        assert backend.rsa_padding_supported(padding.PKCS1v15()) is True

    def test_rsa_padding_supported_pss(self):
        assert backend.rsa_padding_supported(
            padding.PSS(mgf=padding.MGF1(hashes.SHA1()), salt_length=0)
        ) is True

    def test_rsa_padding_supported_oaep(self):
        assert backend.rsa_padding_supported(
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                algorithm=hashes.SHA1(),
                label=None
            ),
        ) is True

    def test_rsa_padding_unsupported_mgf(self):
        assert backend.rsa_padding_supported(
            padding.OAEP(
                mgf=DummyMGF(),
                algorithm=hashes.SHA1(),
                label=None
            ),
        ) is False

        assert backend.rsa_padding_supported(
            padding.PSS(mgf=DummyMGF(), salt_length=0)
        ) is False

    def test_unsupported_mgf1_hash_algorithm_decrypt(self):
        private_key = rsa.RSAPrivateKey.generate(
            public_exponent=65537,
            key_size=512,
            backend=backend
        )
        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_HASH):
            private_key.decrypt(
                b"0" * 64,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA1(),
                    label=None
                ),
                backend
            )

    def test_unsupported_oaep_hash_algorithm_decrypt(self):
        private_key = rsa.RSAPrivateKey.generate(
            public_exponent=65537,
            key_size=512,
            backend=backend
        )
        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_HASH):
            private_key.decrypt(
                b"0" * 64,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA1()),
                    algorithm=hashes.SHA256(),
                    label=None
                ),
                backend
            )

    def test_unsupported_oaep_label_decrypt(self):
        private_key = rsa.RSAPrivateKey.generate(
            public_exponent=65537,
            key_size=512,
            backend=backend
        )
        with pytest.raises(ValueError):
            private_key.decrypt(
                b"0" * 64,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA1()),
                    algorithm=hashes.SHA1(),
                    label=b"label"
                ),
                backend
            )


@pytest.mark.skipif(
    backend._lib.OPENSSL_VERSION_NUMBER <= 0x10001000,
    reason="Requires an OpenSSL version >= 1.0.1"
)
class TestOpenSSLCMAC(object):
    def test_unsupported_cipher(self):
        @utils.register_interface(BlockCipherAlgorithm)
        class FakeAlgorithm(object):
            def __init__(self):
                self.block_size = 64

        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_CIPHER):
            backend.create_cmac_ctx(FakeAlgorithm())


class TestOpenSSLSerialisationWithOpenSSL(object):
    def test_password_too_long(self):
        ffi_cb, cb = backend._pem_password_cb(b"aa")
        assert cb(None, 1, False, None) == 0

    def test_unsupported_evp_pkey_type(self):
        key = pretend.stub(type="unsupported")
        with raises_unsupported_algorithm(None):
            backend._evp_pkey_to_private_key(key)

########NEW FILE########
__FILENAME__ = test_commoncrypto
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import pytest

from cryptography.hazmat.bindings.commoncrypto.binding import Binding


@pytest.mark.skipif(not Binding.is_available(),
                    reason="CommonCrypto not available")
class TestCommonCrypto(object):
    def test_binding_loads(self):
        binding = Binding()
        assert binding
        assert binding.lib
        assert binding.ffi

    def test_binding_returns_same_lib(self):
        binding = Binding()
        binding2 = Binding()
        assert binding.lib == binding2.lib
        assert binding.ffi == binding2.ffi

########NEW FILE########
__FILENAME__ = test_openssl
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import pytest

from cryptography.hazmat.bindings.openssl.binding import Binding


class TestOpenSSL(object):
    def test_binding_loads(self):
        binding = Binding()
        assert binding
        assert binding.lib
        assert binding.ffi

    def test_is_available(self):
        assert Binding.is_available() is True

    def test_crypto_lock_init(self):
        b = Binding()
        b.init_static_locks()
        lock_cb = b.lib.CRYPTO_get_locking_callback()
        assert lock_cb != b.ffi.NULL

    def _skip_if_not_fallback_lock(self, b):
        # only run this test if we are using our locking cb
        original_cb = b.lib.CRYPTO_get_locking_callback()
        if original_cb != b._lock_cb_handle:
            pytest.skip(
                "Not using the fallback Python locking callback "
                "implementation. Probably because import _ssl set one"
            )

    def test_fallback_crypto_lock_via_openssl_api(self):
        b = Binding()
        b.init_static_locks()

        self._skip_if_not_fallback_lock(b)

        # check that the lock state changes appropriately
        lock = b._locks[b.lib.CRYPTO_LOCK_SSL]

        # starts out unlocked
        assert lock.acquire(False)
        lock.release()

        b.lib.CRYPTO_lock(
            b.lib.CRYPTO_LOCK | b.lib.CRYPTO_READ,
            b.lib.CRYPTO_LOCK_SSL, b.ffi.NULL, 0
        )

        # becomes locked
        assert not lock.acquire(False)

        b.lib.CRYPTO_lock(
            b.lib.CRYPTO_UNLOCK | b.lib.CRYPTO_READ,
            b.lib.CRYPTO_LOCK_SSL, b.ffi.NULL, 0
        )

        # then unlocked
        assert lock.acquire(False)
        lock.release()

    def test_fallback_crypto_lock_via_binding_api(self):
        b = Binding()
        b.init_static_locks()

        self._skip_if_not_fallback_lock(b)

        lock = b._locks[b.lib.CRYPTO_LOCK_SSL]

        with pytest.raises(RuntimeError):
            b._lock_cb(0, b.lib.CRYPTO_LOCK_SSL, "<test>", 1)

        # errors shouldn't cause locking
        assert lock.acquire(False)
        lock.release()

        b._lock_cb(b.lib.CRYPTO_LOCK | b.lib.CRYPTO_READ,
                   b.lib.CRYPTO_LOCK_SSL, "<test>", 1)
        # locked
        assert not lock.acquire(False)

        b._lock_cb(b.lib.CRYPTO_UNLOCK | b.lib.CRYPTO_READ,
                   b.lib.CRYPTO_LOCK_SSL, "<test>", 1)
        # unlocked
        assert lock.acquire(False)
        lock.release()

    def test_add_engine_more_than_once(self):
        b = Binding()
        res = b.lib.Cryptography_add_osrandom_engine()
        assert res == 2

    def test_ssl_ctx_options(self):
        # Test that we're properly handling 32-bit unsigned on all platforms.
        b = Binding()
        assert b.lib.SSL_OP_ALL > 0
        ctx = b.lib.SSL_CTX_new(b.lib.TLSv1_method())
        ctx = b.ffi.gc(ctx, b.lib.SSL_CTX_free)
        resp = b.lib.SSL_CTX_set_options(ctx, b.lib.SSL_OP_ALL)
        assert resp == b.lib.SSL_OP_ALL
        assert b.lib.SSL_OP_ALL == b.lib.SSL_CTX_get_options(ctx)

    def test_ssl_options(self):
        # Test that we're properly handling 32-bit unsigned on all platforms.
        b = Binding()
        assert b.lib.SSL_OP_ALL > 0
        ctx = b.lib.SSL_CTX_new(b.lib.TLSv1_method())
        ctx = b.ffi.gc(ctx, b.lib.SSL_CTX_free)
        ssl = b.lib.SSL_new(ctx)
        ssl = b.ffi.gc(ssl, b.lib.SSL_free)
        resp = b.lib.SSL_set_options(ssl, b.lib.SSL_OP_ALL)
        assert resp == b.lib.SSL_OP_ALL
        assert b.lib.SSL_OP_ALL == b.lib.SSL_get_options(ssl)

    def test_ssl_mode(self):
        # Test that we're properly handling 32-bit unsigned on all platforms.
        b = Binding()
        assert b.lib.SSL_OP_ALL > 0
        ctx = b.lib.SSL_CTX_new(b.lib.TLSv1_method())
        ctx = b.ffi.gc(ctx, b.lib.SSL_CTX_free)
        ssl = b.lib.SSL_new(ctx)
        ssl = b.ffi.gc(ssl, b.lib.SSL_free)
        resp = b.lib.SSL_set_mode(ssl, b.lib.SSL_OP_ALL)
        assert resp == b.lib.SSL_OP_ALL
        assert b.lib.SSL_OP_ALL == b.lib.SSL_get_mode(ssl)

########NEW FILE########
__FILENAME__ = test_utils
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

from cryptography.hazmat.bindings import utils


def test_create_modulename():
    cdef_sources = ["cdef sources go here"]
    source = "source code"
    name = utils._create_modulename(cdef_sources, source, "2.7")
    assert name == "_Cryptography_cffi_bcba7f4bx4a14b588"
    name = utils._create_modulename(cdef_sources, source, "3.2")
    assert name == "_Cryptography_cffi_a7462526x4a14b588"

########NEW FILE########
__FILENAME__ = fixtures_rsa
# icensed under the Apache icense, Version 2.0 (the "icense");
# you may not use this file except in compliance with the icense.
# You may obtain a copy of the icense at
#
#    http://www.apache.org/licenses/ICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the icense is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the icense for the specific language governing permissions and
# limitations under the icense.


from __future__ import absolute_import, division, print_function


RSA_KEY_512 = {
    "p": int(
        "d57846898d5c0de249c08467586cb458fa9bc417cdf297f73cfc52281b787cd9", 16
    ),
    "q": int(
        "d10f71229e87e010eb363db6a85fd07df72d985b73c42786191f2ce9134afb2d", 16
    ),
    "private_exponent": int(
        "272869352cacf9c866c4e107acc95d4c608ca91460a93d28588d51cfccc07f449"
        "18bbe7660f9f16adc2b4ed36ca310ef3d63b79bd447456e3505736a45a6ed21", 16
    ),
    "dmp1": int(
        "addff2ec7564c6b64bc670d250b6f24b0b8db6b2810099813b7e7658cecf5c39", 16
    ),
    "dmq1": int(
        "463ae9c6b77aedcac1397781e50e4afc060d4b216dc2778494ebe42a6850c81", 16
    ),
    "iqmp": int(
        "54deef8548f65cad1d411527a32dcb8e712d3e128e4e0ff118663fae82a758f4", 16
    ),
    "public_exponent": 65537,
    "modulus": int(
        "ae5411f963c50e3267fafcf76381c8b1e5f7b741fdb2a544bcf48bd607b10c991"
        "90caeb8011dc22cf83d921da55ec32bd05cac3ee02ca5e1dbef93952850b525", 16
    ),
}

RSA_KEY_512_ALT = {
    "p": int(
        "febe19c29a0b50fefa4f7b1832f84df1caf9be8242da25c9d689e18226e67ce5",
        16),
    "q": int(
        "eb616c639dd999feda26517e1c77b6878f363fe828c4e6670ec1787f28b1e731",
        16),
    "private_exponent": int(
        "80edecfde704a806445a4cc782b85d3f36f17558f385654ea767f006470fdfcbda5e2"
        "206839289d3f419b4e4fb8e1acee1b4fb9c591f69b64ec83937f5829241", 16),
    "dmp1": int(
        "7f4fa06e2a3077a54691cc5216bf13ad40a4b9fa3dd0ea4bca259487484baea5",
        16),
    "dmq1": int(
        "35eaa70d5a8711c352ed1c15ab27b0e3f46614d575214535ae279b166597fac1",
        16),
    "iqmp": int(
        "cc1f272de6846851ec80cb89a02dbac78f44b47bc08f53b67b4651a3acde8b19",
        16),
    "public_exponent": 65537,
    "modulus": int(
        "ea397388b999ef0f7e7416fa000367efd9a0ba0deddd3f8160d1c36d62267f210fbd9"
        "c97abeb6654450ff03e7601b8caa6c6f4cba18f0b52c179d17e8f258ad5", 16),
}

RSA_KEY_522 = {
    "p": int(
        "1a8aab9a069f92b52fdf05824f2846223dc27adfc806716a247a77d4c36885e4bf",
        16),
    "q": int(
        "19e8d620d177ec54cdb733bb1915e72ef644b1202b889ceb524613efa49c07eb4f",
        16),
    "private_exponent": int(
        "10b8a7c0a92c1ae2d678097d69db3bfa966b541fb857468291d48d1b52397ea2bac0d"
        "4370c159015c7219e3806a01bbafaffdd46f86e3da1e2d1fe80a0369ccd745", 16),
    "dmp1": int(
        "3eb6277f66e6e2dcf89f1b8529431f730839dbd9a3e49555159bc8470eee886e5",
        16),
    "dmq1": int(
        "184b4d74aa54c361e51eb23fee4eae5e4786b37b11b6e0447af9c0b9c4e4953c5b",
        16),
    "iqmp": int(
        "f80e9ab4fa7b35d0d232ef51c4736d1f2dcf2c7b1dd8716211b1bf1337e74f8ae",
        16),
    "public_exponent": 65537,
    "modulus": int(
        "2afaea0e0bb6fca037da7d190b5270a6c665bc18e7a456f7e69beaac4433db748ba99"
        "acdd14697e453bca596eb35b47f2d48f1f85ef08ce5109dad557a9cf85ebf1", 16),
}

RSA_KEY_599 = {
    "p": int(
        "cf95d20be0c7af69f4b3d909f65d858c26d1a7ef34da8e3977f4fa230580e58814b54"
        "24be99", 16),
    "q": int(
        "6052be4b28debd4265fe12ace5aa4a0c4eb8d63ff8853c66824b35622161eb48a3bc8"
        "c3ada5", 16),
    "private_exponent": int(
        "69d9adc465e61585d3142d7cc8dd30605e8d1cbbf31009bc2cd5538dc40528d5d68ee"
        "fe6a42d23674b6ec76e192351bf368c8968f0392110bf1c2825dbcff071270b80adcc"
        "fa1d19d00a1", 16),
    "dmp1": int(
        "a86d10edde456687fba968b1f298d2e07226adb1221b2a466a93f3d83280f0bb46c20"
        "2b6811", 16),
    "dmq1": int(
        "40d570e08611e6b1da94b95d46f8e7fe80be48f7a5ff8838375b08039514a399b11c2"
        "80735", 16),
    "iqmp": int(
        "cd051cb0ea68b88765c041262ace2ec4db11dab14afd192742e34d5da3328637fabdf"
        "bae26e", 16),
    "public_exponent": 65537,
    "modulus": int(
        "4e1b470fe00642426f3808e74c959632dd67855a4c503c5b7876ccf4dc7f6a1a49107"
        "b90d26daf0a7879a6858218345fbc6e59f01cd095ca5647c27c25265e6c474fea8953"
        "7191c7073d9d", 16),
}

RSA_KEY_745 = {
    "p": int(
        "1c5a0cfe9a86debd19eca33ba961f15bc598aa7983a545ce775b933afc89eb51bcf90"
        "836257fdd060d4b383240241d", 16
    ),
    "q": int(
        "fb2634f657f82ee6b70553382c4e2ed26b947c97ce2f0016f1b282cf2998184ad0527"
        "a9eead826dd95fe06b57a025", 16
    ),
    "private_exponent": int(
        "402f30f976bc07d15ff0779abff127b20a8b6b1d0024cc2ad8b6762d38f174f81e792"
        "3b49d80bdbdd80d9675cbc7b2793ec199a0430eb5c84604dacfdb29259ae6a1a44676"
        "22f0b23d4cb0f5cb1db4b8173c8d9d3e57a74dbd200d2141", 16),
    "dmp1": int(
        "e5e95b7751a6649f199be21bef7a51c9e49821d945b6fc5f538b4a670d8762c375b00"
        "8e70f31d52b3ea2bd14c3101", 16),
    "dmq1": int(
        "12b85d5843645f72990fcf8d2f58408b34b3a3b9d9078dd527fceb5d2fb7839008092"
        "dd4aca2a1fb00542801dcef5", 16),
    "iqmp": int(
        "5672740d947f621fc7969e3a44ec26736f3f819863d330e63e9409e139d20753551ac"
        "c16544dd2bdadb9dee917440", 16),
    "public_exponent": 65537,
    "modulus": int(
        "1bd085f92237774d34013b477ceebbb2f2feca71118db9b7429341477947e7b1d04e8"
        "c43ede3c52bb25781af58d4ff81289f301eac62dc3bcd7dafd7a4d5304e9f308e7669"
        "52fbf2b62373e66611fa53189987dbef9f7243dcbbeb25831", 16),
}

RSA_KEY_768 = {
    "p": int(
        "f80c0061b607f93206b68e208906498d68c6e396faf457150cf975c8f849848465869"
        "7ecd402313397088044c4c2071b", 16),
    "q": int(
        "e5b5dbecc93c6d306fc14e6aa9737f9be2728bc1a326a8713d2849b34c1cb54c63468"
        "3a68abb1d345dbf15a3c492cf55", 16),
    "private_exponent": int(
        "d44601442255ffa331212c60385b5e898555c75c0272632ff42d57c4b16ca97dbca9f"
        "d6d99cd2c9fd298df155ed5141b4be06c651934076133331d4564d73faed7ce98e283"
        "2f7ce3949bc183be7e7ca34f6dd04a9098b6c73649394b0a76c541", 16),
    "dmp1": int(
        "a5763406fa0b65929661ce7b2b8c73220e43a5ebbfe99ff15ddf464fd238105ad4f2a"
        "c83818518d70627d8908703bb03", 16),
    "dmq1": int(
        "cb467a9ef899a39a685aecd4d0ad27b0bfdc53b68075363c373d8eb2bed8eccaf3533"
        "42f4db735a9e087b7539c21ba9d", 16),
    "iqmp": int(
        "5fe86bd3aee0c4d09ef11e0530a78a4534c9b833422813b5c934a450c8e564d8097a0"
        "6fd74f1ebe2d5573782093f587a", 16),
    "public_exponent": 65537,
    "modulus": int(
        "de92f1eb5f4abf426b6cac9dd1e9bf57132a4988b4ed3f8aecc15e251028bd6df46eb"
        "97c711624af7db15e6430894d1b640c13929329241ee094f5a4fe1a20bc9b75232320"
        "a72bc567207ec54d6b48dccb19737cf63acc1021abb337f19130f7", 16),
}

RSA_KEY_1024 = {
    "p": int(
        "ea4d9d9a1a068be44b9a5f8f6de0512b2c5ba1fb804a4655babba688e6e890b347c1a"
        "7426685a929337f513ae4256f0b7e5022d642237f960c5b24b96bee8e51", 16),
    "q": int(
        "cffb33e400d6f08b410d69deb18a85cf0ed88fcca9f32d6f2f66c62143d49aff92c11"
        "4de937d4f1f62d4635ee89af99ce86d38a2b05310f3857c7b5d586ac8f9", 16),
    "private_exponent": int(
        "3d12d46d04ce942fb99be7bf30587b8cd3e21d75a2720e7bda1b867f1d418d91d8b9f"
        "e1c00181fdde94f2faf33b4e6f800a1b3ae3b972ccb6d5079dcb6c794070ac8306d59"
        "c00b58b7a9a81122a6b055832de7c72334a07494d8e7c9fbeed2cc37e011d9e6bfc6e"
        "9bcddbef7f0f5771d9cf82cd4b268c97ec684575c24b6c881", 16),
    "dmp1": int(
        "470f2b11257b7ec9ca34136f487f939e6861920ad8a9ae132a02e74af5dceaa5b4c98"
        "2949ccb44b67e2bcad2f58674db237fe250e0d62b47b28fa1dfaa603b41", 16),
    "dmq1": int(
        "c616e8317d6b3ae8272973709b80e8397256697ff14ea03389de454f619f99915a617"
        "45319fefbe154ec1d49441a772c2f63f7d15c478199afc60469bfd0d561", 16),
    "iqmp": int(
        "d15e7c9ad357dfcd5dbdc8427680daf1006761bcfba93a7f86589ad88832a8d564b1c"
        "d4291a658c96fbaea7ca588795820902d85caebd49c2d731e3fe0243130", 16),
    "public_exponent": 65537,
    "modulus": int(
        "be5aac07456d990133ebce69c06b48845b972ab1ad9f134bc5683c6b5489b5119ede0"
        "7be3bed0e355d48e0dfab1e4fb5187adf42d7d3fb0401c082acb8481bf17f0e871f88"
        "77be04c3a1197d40aa260e2e0c48ed3fd2b93dc3fc0867591f67f3cd60a77adee1d68"
        "a8c3730a5702485f6ac9ede7f0fd2918e037ee4cc1fc1b4c9", 16),
}

RSA_KEY_1025 = {
    "p": int(
        "18e9bfb7071725da04d31c103fa3563648c69def43a204989214eb57b0c8b299f9ef3"
        "5dda79a62d8d67fd2a9b69fbd8d0490aa2edc1e111a2b8eb7c737bb691a5", 16),
    "q": int(
        "d8eccaeeb95815f3079d13685f3f72ca2bf2550b349518049421375df88ca9bbb4ba8"
        "cb0e3502203c9eeae174112509153445d251313e4711a102818c66fcbb7", 16),
    "private_exponent": int(
        "fe9ac54910b8b1bc948a03511c54cab206a1d36d50d591124109a48abb7480977ccb0"
        "47b4d4f1ce7b0805df2d4fa3fe425f49b78535a11f4b87a4eba0638b3340c23d4e6b2"
        "1ecebe9d5364ea6ead2d47b27836019e6ecb407000a50dc95a8614c9d0031a6e3a524"
        "d2345cfb76e15c1f69d5ba35bdfb6ec63bcb115a757ef79d9", 16),
    "dmp1": int(
        "18537e81006a68ea76d590cc88e73bd26bc38d09c977959748e5265c0ce21c0b5fd26"
        "53d975f97ef759b809f791487a8fff1264bf561627fb4527a3f0bbb72c85", 16),
    "dmq1": int(
        "c807eac5a1f1e1239f04b04dd16eff9a00565127a91046fa89e1eb5d6301cace85447"
        "4d1f47b0332bd35b4214b66e9166953241538f761f30d969272ee214f17", 16),
    "iqmp": int(
        "133aa74dd41fe70fa244f07d0c4091a22f8c8f0134fe6aea9ec8b55383b758fefe358"
        "2beec36eca91715eee7d21931f24fa9e97e8e3a50f9cd0f731574a5eafcc", 16),
    "public_exponent": 65537,
    "modulus": int(
        "151c44fed756370fb2d4a0e6ec7dcac84068ca459b6aaf22daf902dca72c77563bf27"
        "6fe3523f38f5ddaf3ea9aa88486a9d8760ff732489075862bee0e599de5c5f509b451"
        "9f4f446521bad15cd279a498fe1e89107ce0d237e3103d7c5eb80166642e2924b152a"
        "ebff97b71fdd2d68ebb45034cc784e2e822ff6d1edf98af3f3", 16),
}

RSA_KEY_1026 = {
    "p": int(
        "1fcbfb8719c5bdb5fe3eb0937c76bb096e750b9442dfe31d6a877a13aed2a6a4e9f79"
        "40f815f1c307dd6bc2b4b207bb6fe5be3a15bd2875a957492ce197cdedb1", 16),
    "q": int(
        "1f704a0f6b8966dd52582fdc08227dd3dbaeaa781918b41144b692711091b4ca4eb62"
        "985c3513853828ce8739001dfba9a9a7f1a23cbcaf74280be925e2e7b50d", 16),
    "private_exponent": int(
        "c67975e35a1d0d0b3ebfca736262cf91990cb31cf4ac473c0c816f3bc2720bcba2475"
        "e8d0de8535d257816c0fc53afc1b597eada8b229069d6ef2792fc23f59ffb4dc6c3d9"
        "0a3c462082025a4cba7561296dd3d8870c4440d779406f00879afe2c681e7f5ee055e"
        "ff829e6e55883ec20830c72300762e6e3a333d94b4dbe4501", 16),
    "dmp1": int(
        "314730ca7066c55d086a9fbdf3670ef7cef816b9efea8b514b882ae9d647217cf41d7"
        "e9989269dc9893d02e315cb81f058c49043c2cac47adea58bdf5e20e841", 16),
    "dmq1": int(
        "1da28a9d687ff7cfeebc2439240de7505a8796376968c8ec723a2b669af8ce53d9c88"
        "af18540bd78b2da429014923fa435f22697ac60812d7ca9c17a557f394cd", 16),
    "iqmp": int(
        "727947b57b8a36acd85180522f1b381bce5fdbd962743b3b14af98a36771a80f58ddd"
        "62675d72a5935190da9ddc6fd6d6d5e9e9f805a2e92ab8d56b820493cdf", 16),
    "public_exponent": 65537,
    "modulus": int(
        "3e7a5e6483e55eb8b723f9c46732d21b0af9e06a4a1099962d67a35ee3f62e3129cfa"
        "e6ab0446da18e26f33e1d753bc1cc03585c100cf0ab5ef056695706fc8b0c9c710cd7"
        "3fe6e5beda70f515a96fabd3cc5ac49efcb2594b220ff3b603fcd927f6a0838ef04bf"
        "52f3ed9eab801f09e5aed1613ddeb946ed0fbb02060b3a36fd", 16),
}

RSA_KEY_1027 = {
    "p": int(
        "30135e54cfb072c3d3eaf2000f3ed92ceafc85efc867b9d4bf5612f2978c432040093"
        "4829f741c0f002b54af2a4433ff872b6321ef00ff1e72cba4e0ced937c7d", 16),
    "q": int(
        "1d01a8aead6f86b78c875f18edd74214e06535d65da054aeb8e1851d6f3319b4fb6d8"
        "6b01e07d19f8261a1ded7dc08116345509ab9790e3f13e65c037e5bb7e27", 16),
    "private_exponent": int(
        "21cf4477df79561c7818731da9b9c88cd793f1b4b8e175bd0bfb9c0941a4dc648ecf1"
        "6d96b35166c9ea116f4c2eb33ce1c231e641a37c25e54c17027bdec08ddafcb83642e"
        "795a0dd133155ccc5eed03b6e745930d9ac7cfe91f9045149f33295af03a2198c660f"
        "08d8150d13ce0e2eb02f21ac75d63b55822f77bd5be8d07619", 16),
    "dmp1": int(
        "173fb695931e845179511c18b546b265cb79b517c135902377281bdf9f34205e1f399"
        "4603ad63e9f6e7885ea73a929f03fa0d6bed943051ce76cddde2d89d434d", 16),
    "dmq1": int(
        "10956b387b2621327da0c3c8ffea2af8be967ee25163222746c28115a406e632a7f12"
        "5a9397224f1fa5c116cd3a313e5c508d31db2deb83b6e082d213e33f7fcf", 16),
    "iqmp": int(
        "234f833949f2c0d797bc6a0e906331e17394fa8fbc8449395766d3a8d222cf6167c48"
        "8e7fe1fe9721d3e3b699a595c8e6f063d92bd840dbc84d763b2b37002109", 16),
    "public_exponent": 65537,
    "modulus": int(
        "57281707d7f9b1369c117911758980e32c05b133ac52c225bcf68b79157ff47ea0a5a"
        "e9f579ef1fd7e42937f921eb3123c4a045cc47a2159fbbf904783e654954c42294c30"
        "a95c15db7c7b91f136244e548f62474b137087346c5522e54f226f49d6c93bc58cb39"
        "972e41bde452bb3ae9d60eb93e5e1ce91d222138d9890c7d0b", 16),
}

RSA_KEY_1028 = {
    "p": int(
        "359d17378fae8e9160097daee78a206bd52efe1b757c12a6da8026cc4fc4bb2620f12"
        "b8254f4db6aed8228be8ee3e5a27ec7d31048602f01edb00befd209e8c75", 16),
    "q": int(
        "33a2e70b93d397c46e63b273dcd3dcfa64291342a6ce896e1ec8f1c0edc44106550f3"
        "c06e7d3ca6ea29eccf3f6ab5ac6235c265313d6ea8e8767e6a343f616581", 16),
    "private_exponent": int(
        "880640088d331aa5c0f4cf2887809a420a2bc086e671e6ffe4e47a8c80792c038a314"
        "9a8e45ef9a72816ab45b36e3af6800351067a6b2751843d4232413146bb575491463a"
        "8addd06ce3d1bcf7028ec6c5d938c545a20f0a40214b5c574ca7e840062b2b5f8ed49"
        "4b144bb2113677c4b10519177fee1d4f5fb8a1c159b0b47c01", 16),
    "dmp1": int(
        "75f8c52dad2c1cea26b8bba63236ee4059489e3d2db766136098bcc6b67fde8f77cd3"
        "640035107bfb1ffc6480983cfb84fe0c3be008424ebc968a7db7e01f005", 16),
    "dmq1": int(
        "3893c59469e4ede5cd0e6ff9837ca023ba9b46ff40c60ccf1bec10f7d38db5b1ba817"
        "6c41a3f750ec4203b711455aca06d1e0adffc5cffa42bb92c7cb77a6c01", 16),
    "iqmp": int(
        "ad32aafae3c962ac25459856dc8ef1f733c3df697eced29773677f435d186cf759d1a"
        "5563dd421ec47b4d7e7f12f29647c615166d9c43fc49001b29089344f65", 16),
    "public_exponent": 65537,
    "modulus": int(
        "ad0696bef71597eb3a88e135d83c596930cac73868fbd7e6b2d64f34eea5c28cce351"
        "0c68073954d3ba4deb38643e7a820a4cf06e75f7f82eca545d412bd63781945c28d40"
        "6e95a6cced5ae924a8bfa4f3def3e0250d91246c269ec40c89c93a85acd3770ba4d2e"
        "774732f43abe94394de43fb57f93ca25f7a59d75d400a3eff5", 16),
}

RSA_KEY_1029 = {
    "p": int(
        "66f33e513c0b6b6adbf041d037d9b1f0ebf8de52812a3ac397a963d3f71ba64b3ad04"
        "e4d4b5e377e6fa22febcac292c907dc8dcfe64c807fd9a7e3a698850d983", 16),
    "q": int(
        "3b47a89a19022461dcc2d3c05b501ee76955e8ce3cf821beb4afa85a21a26fd7203db"
        "deb8941f1c60ada39fd6799f6c07eb8554113f1020460ec40e93cd5f6b21", 16),
    "private_exponent": int(
        "280c42af8b1c719821f2f6e2bf5f3dd53c81b1f3e1e7cc4fce6e2f830132da0665bde"
        "bc1e307106b112b52ad5754867dddd028116cf4471bc14a58696b99524b1ad8f05b31"
        "cf47256e54ab4399b6a073b2c0452441438dfddf47f3334c13c5ec86ece4d33409056"
        "139328fafa992fb5f5156f25f9b21d3e1c37f156d963d97e41", 16),
    "dmp1": int(
        "198c7402a4ec10944c50ab8488d7b5991c767e75eb2817bd427dff10335ae141fa2e8"
        "7c016dc22d975cac229b9ffdf7d943ddfd3a04b8bf82e83c3b32c5698b11", 16),
    "dmq1": int(
        "15fd30c7687b68ef7c2a30cdeb913ec56c4757c218cf9a04d995470797ee5f3a17558"
        "fbb6d00af245d2631d893b382da48a72bc8a613024289895952ab245b0c1", 16),
    "iqmp": int(
        "4f8fde17e84557a3f4e242d889e898545ab55a1a8e075c9bb0220173ccffe84659abe"
        "a235104f82e32750309389d4a52af57dbb6e48d831917b6efeb190176570", 16),
    "public_exponent": 65537,
    "modulus": int(
        "17d6e0a09aa5b2d003e51f43b9c37ffde74688f5e3b709fd02ef375cb6b8d15e299a9"
        "f74981c3eeaaf947d5c2d64a1a80f5c5108a49a715c3f7be95a016b8d3300965ead4a"
        "4df76e642d761526803e9434d4ec61b10cb50526d4dcaef02593085ded8c331c1b27b"
        "200a45628403065efcb2c0a0ca1f75d648d40a007fbfbf2cae3", 16),
}

RSA_KEY_1030 = {
    "p": int(
        "6f4ac8a8172ef1154cf7f80b5e91de723c35a4c512860bfdbafcc3b994a2384bf7796"
        "3a2dd0480c7e04d5d418629651a0de8979add6f47b23da14c27a682b69c9", 16),
    "q": int(
        "65a9f83e07dea5b633e036a9dccfb32c46bf53c81040a19c574c3680838fc6d28bde9"
        "55c0ff18b30481d4ab52a9f5e9f835459b1348bbb563ad90b15a682fadb3", 16),
    "private_exponent": int(
        "290db707b3e1a96445ae8ea93af55a9f211a54ebe52995c2eb28085d1e3f09c986e73"
        "a00010c8e4785786eaaa5c85b98444bd93b585d0c24363ccc22c482e150a3fd900176"
        "86968e4fa20423ae72823b0049defceccb39bb34aa4ef64e6b14463b76d6a871c859e"
        "37285455b94b8e1527d1525b1682ac6f7c8fd79d576c55318c1", 16),
    "dmp1": int(
        "23f7fa84010225dea98297032dac5d45745a2e07976605681acfe87e0920a8ab3caf5"
        "9d9602f3d63dc0584f75161fd8fff20c626c21c5e02a85282276a74628a9", 16),
    "dmq1": int(
        "18ebb657765464a8aa44bf019a882b72a2110a77934c54915f70e6375088b10331982"
        "962bce1c7edd8ef9d3d95aa2566d2a99da6ebab890b95375919408d00f33", 16),
    "iqmp": int(
        "3d59d208743c74054151002d77dcdfc55af3d41357e89af88d7eef2767be54c290255"
        "9258d85cf2a1083c035a33e65a1ca46dc8b706847c1c6434cef7b71a9dae", 16),
    "public_exponent": 65537,
    "modulus": int(
        "2c326574320818a6a8cb6b3328e2d6c1ba2a3f09b6eb2bc543c03ab18eb5efdaa8fcd"
        "bb6b4e12168304f587999f9d96a421fc80cb933a490df85d25883e6a88750d6bd8b3d"
        "4117251eee8f45e70e6daac7dbbd92a9103c623a09355cf00e3f16168e38b9c4cb5b3"
        "68deabbed8df466bc6835eaba959bc1c2f4ec32a09840becc8b", 16),
}

RSA_KEY_1031 = {
    "p": int(
        "c0958c08e50137db989fb7cc93abf1984543e2f955d4f43fb2967f40105e79274c852"
        "293fa06ce63ca8436155e475ed6d1f73fea4c8e2516cc79153e3dc83e897", 16),
    "q": int(
        "78cae354ea5d6862e5d71d20273b7cddb8cdfab25478fe865180676b04250685c4d03"
        "30c216574f7876a7b12dfe69f1661d3b0cea6c2c0dcfb84050f817afc28d", 16),
    "private_exponent": int(
        "1d55cc02b17a5d25bfb39f2bc58389004d0d7255051507f75ef347cdf5519d1a00f4b"
        "d235ce4171bfab7bdb7a6dcfae1cf41433fb7da5923cc84f15a675c0b83492c95dd99"
        "a9fc157aea352ffdcbb5d59dbc3662171d5838d69f130678ee27841a79ef64f679ce9"
        "3821fa69c03f502244c04b737edad8967def8022a144feaab29", 16),
    "dmp1": int(
        "5b1c2504ec3a984f86b4414342b5bcf59a0754f13adf25b2a0edbc43f5ba8c3cc061d"
        "80b03e5866d059968f0d10a98deaeb4f7830436d76b22cf41f2914e13eff", 16),
    "dmq1": int(
        "6c361e1819691ab5d67fb2a8f65c958d301cdf24d90617c68ec7005edfb4a7b638cde"
        "79d4b61cfba5c86e8c0ccf296bc7f611cb8d4ae0e072a0f68552ec2d5995", 16),
    "iqmp": int(
        "b7d61945fdc8b92e075b15554bab507fa8a18edd0a18da373ec6c766c71eece61136a"
        "84b90b6d01741d40458bfad17a9bee9d4a8ed2f6e270782dc3bf5d58b56e", 16),
    "public_exponent": 65537,
    "modulus": int(
        "5adebaa926ea11fb635879487fdd53dcfbb391a11ac7279bb3b4877c9b811370a9f73"
        "da0690581691626d8a7cf5d972cced9c2091ccf999024b23b4e6dc6d99f80a454737d"
        "ec0caffaebe4a3fac250ed02079267c8f39620b5ae3e125ca35338522dc9353ecac19"
        "cb2fe3b9e3a9291619dbb1ea3a7c388e9ee6469fbf5fb22892b", 16),
}

RSA_KEY_1536 = {
    "p": int(
        "f1a65fa4e2aa6e7e2b560251e8a4cd65b625ad9f04f6571785782d1c213d91c961637"
        "0c572f2783caf2899f7fb690cf99a0184257fbd4b071b212c88fb348279a5387e61f1"
        "17e9c62980c45ea863fa9292087c0f66ecdcde6443d5a37268bf71", 16),
    "q": int(
        "e54c2cbc3839b1da6ae6fea45038d986d6f523a3ae76051ba20583aab711ea5965cf5"
        "3cf54128cc9573f7460bba0fd6758a57aaf240c391790fb38ab473d83ef735510c53d"
        "1d10c31782e8fd7da42615e33565745c30a5e6ceb2a3ae0666cc35", 16),
    "private_exponent": int(
        "7bcad87e23da2cb2a8c328883fabce06e1f8e9b776c8bf253ad9884e6200e3bd9bd3b"
        "a2cbe87d3854527bf005ba5d878c5b0fa20cfb0a2a42884ae95ca12bf7304285e9214"
        "5e992f7006c7c0ae839ad550da495b143bec0f4806c7f44caed45f3ccc6dc44cfaf30"
        "7abdb757e3d28e41c2d21366835c0a41e50a95af490ac03af061d2feb36ac0afb87be"
        "a13fb0f0c5a410727ebedb286c77f9469473fae27ef2c836da6071ef7efc1647f1233"
        "4009a89eecb09a8287abc8c2afd1ddd9a1b0641", 16),
    "dmp1": int(
        "a845366cd6f9df1f34861bef7594ed025aa83a12759e245f58adaa9bdff9c3befb760"
        "75d3701e90038e888eec9bf092df63400152cb25fc07effc6c74c45f0654ccbde15cd"
        "90dd5504298a946fa5cf22a956072da27a6602e6c6e5c97f2db9c1", 16),
    "dmq1": int(
        "28b0c1e78cdac03310717992d321a3888830ec6829978c048156152d805b4f8919c61"
        "70b5dd204e5ddf3c6c53bc6aff15d0bd09faff7f351b94abb9db980b31f150a6d7573"
        "08eb66938f89a5225cb4dd817a824c89e7a0293b58fc2eefb7e259", 16),
    "iqmp": int(
        "6c1536c0e16e42a094b6caaf50231ba81916871497d73dcbbbd4bdeb9e60cae0413b3"
        "8143b5d680275b29ed7769fe5577e4f9b3647ddb064941120914526d64d80016d2eb7"
        "dc362da7c569623157f3d7cff8347f11494bf5c048d77e28d3f515", 16),
    "public_exponent": 65537,
    "modulus": int(
        "d871bb2d27672e54fc62c4680148cbdf848438da804e2c48b5a9c9f9daf6cc6e8ea7d"
        "2296f25064537a9a542aef3dd449ea75774238d4da02c353d1bee70013dccc248ceef"
        "4050160705c188043c8559bf6dbfb6c4bb382eda4e9547575a8227d5b3c0a70883913"
        "64cf9f018d8bea053b226ec65e8cdbeaf48a071d0074860a734b1cb7d2146d43014b2"
        "0776dea42f7853a54690e6cbbf3331a9f43763cfe2a51c3293bea3b2eebec0d8e43eb"
        "317a443afe541107d886e5243c096091543ae65", 16),
}

RSA_KEY_2048 = {
    "p": int(
        "e14202e58c5f7446648d75e5dc465781f661f6b73000c080368afcfb21377f4ef19da"
        "845d4ef9bc6b151f6d9f34629103f2e57615f9ba0a3a2fbb035069e1d63b4bb0e78ad"
        "dad1ec3c6f87e25c877a1c4c1972098e09158ef7b9bc163852a18d44a70b7b31a03dc"
        "2614fd9ab7bf002cba79054544af3bfbdb6aed06c7b24e6ab", 16),
    "q": int(
        "dbe2bea1ff92599bd19f9d045d6ce62250c05cfeac5117f3cf3e626cb696e3d886379"
        "557d5a57b7476f9cf886accfd40508a805fe3b45a78e1a8a125e516cda91640ee6398"
        "ec5a39d3e6b177ef12ab00d07907a17640e4ca454fd8487da3c4ffa0d5c2a5edb1221"
        "1c8e33c7ee9fa6753771fd111ec04b8317f86693eb2928c89", 16),
    "private_exponent": int(
        "aef17f80f2653bc30539f26dd4c82ed6abc1d1b53bc0abcdbee47e9a8ab433abde865"
        "9fcfae1244d22de6ad333c95aee7d47f30b6815065ac3322744d3ea75058002cd1b29"
        "3141ee2a6dc682342432707080071bd2131d6262cab07871c28aa5238b87173fb78c3"
        "7f9c7bcd18c12e8971bb77fd9fa3e0792fec18d8d9bed0b03ba02b263606f24dbace1"
        "c8263ce2802a769a090e993fd49abc50c3d3c78c29bee2de0c98055d2f102f1c5684b"
        "8dddee611d5205392d8e8dd61a15bf44680972a87f040a611a149271eeb2573f8bf6f"
        "627dfa70e77def2ee6584914fa0290e041349ea0999cdff3e493365885b906cbcf195"
        "843345809a85098cca90fea014a21", 16),
    "dmp1": int(
        "9ba56522ffcfa5244eae805c87cc0303461f82be29691b9a7c15a5a050df6c143c575"
        "7c288d3d7ab7f32c782e9d9fcddc10a604e6425c0e5d0e46069035d95a923646d276d"
        "d9d95b8696fa29ab0de18e53f6f119310f8dd9efca62f0679291166fed8cbd5f18fe1"
        "3a5f1ead1d71d8c90f40382818c18c8d069be793dbc094f69", 16),
    "dmq1": int(
        "a8d4a0aaa2212ccc875796a81353da1fdf00d46676c88d2b96a4bfcdd924622d8e607"
        "f3ac1c01dda7ebfb0a97dd7875c2a7b2db6728fb827b89c519f5716fb3228f4121647"
        "04b30253c17de2289e9cce3343baa82eb404f789e094a094577a9b0c5314f1725fdf5"
        "8e87611ad20da331bd30b8aebc7dc97d0e9a9ba8579772c9", 16),
    "iqmp": int(
        "17bd5ef638c49440d1853acb3fa63a5aca28cb7f94ed350db7001c8445da8943866a7"
        "0936e1ee2716c98b484e357cc054d82fbbd98d42f880695d38a1dd4eb096f629b9417"
        "aca47e6de5da9f34e60e8a0ffd7e35be74deeef67298d94b3e0db73fc4b7a4cb360c8"
        "9d2117a0bfd9434d37dc7c027d6b01e5295c875015510917d", 16),
    "public_exponent": 65537,
    "modulus": int(
        "c17afc7e77474caa5aa83036158a3ffbf7b5216851ba2230e5d6abfcc1c6cfef59e92"
        "3ea1330bc593b73802ab608a6e4a3306523a3116ba5aa3966145174e13b6c49e9b780"
        "62e449d72efb10fd49e91fa08b96d051e782e9f5abc5b5a6f7984827adb8e73da00f2"
        "2b2efdcdb76eab46edad98ed65662743fdc6c0e336a5d0cdbaa7dc29e53635e24c87a"
        "5b2c4215968063cdeb68a972babbc1e3cff00fb9a80e372a4d0c2c920d1e8cee333ce"
        "470dc2e8145adb05bf29aee1d24f141e8cc784989c587fc6fbacd979f3f2163c1d729"
        "9b365bc72ffe2848e967aed1e48dcc515b3a50ed4de04fd053846ca10a223b10cc841"
        "cc80fdebee44f3114c13e886af583", 16),
}

########NEW FILE########
__FILENAME__ = test_3des
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Test using the NIST Test Vectors
"""

from __future__ import absolute_import, division, print_function

import binascii
import os

import pytest

from cryptography.hazmat.primitives.ciphers import algorithms, modes

from .utils import generate_encrypt_test
from ...utils import load_nist_vectors


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.TripleDES("\x00" * 8), modes.CBC("\x00" * 8)
    ),
    skip_message="Does not support TripleDES CBC",
)
@pytest.mark.cipher
class TestTripleDESModeCBC(object):
    test_KAT = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "3DES", "CBC"),
        [
            "TCBCinvperm.rsp",
            "TCBCpermop.rsp",
            "TCBCsubtab.rsp",
            "TCBCvarkey.rsp",
            "TCBCvartext.rsp",
        ],
        lambda keys, **kwargs: algorithms.TripleDES(binascii.unhexlify(keys)),
        lambda iv, **kwargs: modes.CBC(binascii.unhexlify(iv)),
    )

    test_MMT = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "3DES", "CBC"),
        [
            "TCBCMMT1.rsp",
            "TCBCMMT2.rsp",
            "TCBCMMT3.rsp",
        ],
        lambda key1, key2, key3, **kwargs: algorithms.TripleDES(
            binascii.unhexlify(key1 + key2 + key3)
        ),
        lambda iv, **kwargs: modes.CBC(binascii.unhexlify(iv)),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.TripleDES("\x00" * 8), modes.OFB("\x00" * 8)
    ),
    skip_message="Does not support TripleDES OFB",
)
@pytest.mark.cipher
class TestTripleDESModeOFB(object):
    test_KAT = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "3DES", "OFB"),
        [
            "TOFBpermop.rsp",
            "TOFBsubtab.rsp",
            "TOFBvarkey.rsp",
            "TOFBvartext.rsp",
            "TOFBinvperm.rsp",
        ],
        lambda keys, **kwargs: algorithms.TripleDES(binascii.unhexlify(keys)),
        lambda iv, **kwargs: modes.OFB(binascii.unhexlify(iv)),
    )

    test_MMT = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "3DES", "OFB"),
        [
            "TOFBMMT1.rsp",
            "TOFBMMT2.rsp",
            "TOFBMMT3.rsp",
        ],
        lambda key1, key2, key3, **kwargs: algorithms.TripleDES(
            binascii.unhexlify(key1 + key2 + key3)
        ),
        lambda iv, **kwargs: modes.OFB(binascii.unhexlify(iv)),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.TripleDES("\x00" * 8), modes.CFB("\x00" * 8)
    ),
    skip_message="Does not support TripleDES CFB",
)
@pytest.mark.cipher
class TestTripleDESModeCFB(object):
    test_KAT = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "3DES", "CFB"),
        [
            "TCFB64invperm.rsp",
            "TCFB64permop.rsp",
            "TCFB64subtab.rsp",
            "TCFB64varkey.rsp",
            "TCFB64vartext.rsp",
        ],
        lambda keys, **kwargs: algorithms.TripleDES(binascii.unhexlify(keys)),
        lambda iv, **kwargs: modes.CFB(binascii.unhexlify(iv)),
    )

    test_MMT = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "3DES", "CFB"),
        [
            "TCFB64MMT1.rsp",
            "TCFB64MMT2.rsp",
            "TCFB64MMT3.rsp",
        ],
        lambda key1, key2, key3, **kwargs: algorithms.TripleDES(
            binascii.unhexlify(key1 + key2 + key3)
        ),
        lambda iv, **kwargs: modes.CFB(binascii.unhexlify(iv)),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.TripleDES("\x00" * 8), modes.CFB8("\x00" * 8)
    ),
    skip_message="Does not support TripleDES CFB8",
)
@pytest.mark.cipher
class TestTripleDESModeCFB8(object):
    test_KAT = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "3DES", "CFB"),
        [
            "TCFB8invperm.rsp",
            "TCFB8permop.rsp",
            "TCFB8subtab.rsp",
            "TCFB8varkey.rsp",
            "TCFB8vartext.rsp",
        ],
        lambda keys, **kwargs: algorithms.TripleDES(binascii.unhexlify(keys)),
        lambda iv, **kwargs: modes.CFB8(binascii.unhexlify(iv)),
    )

    test_MMT = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "3DES", "CFB"),
        [
            "TCFB8MMT1.rsp",
            "TCFB8MMT2.rsp",
            "TCFB8MMT3.rsp",
        ],
        lambda key1, key2, key3, **kwargs: algorithms.TripleDES(
            binascii.unhexlify(key1 + key2 + key3)
        ),
        lambda iv, **kwargs: modes.CFB8(binascii.unhexlify(iv)),
    )

########NEW FILE########
__FILENAME__ = test_aes
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import binascii
import os

import pytest

from cryptography.hazmat.primitives.ciphers import algorithms, modes

from .utils import generate_aead_test, generate_encrypt_test
from ...utils import load_nist_vectors


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.AES("\x00" * 16), modes.CBC("\x00" * 16)
    ),
    skip_message="Does not support AES CBC",
)
@pytest.mark.cipher
class TestAESModeCBC(object):
    test_CBC = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "AES", "CBC"),
        [
            "CBCGFSbox128.rsp",
            "CBCGFSbox192.rsp",
            "CBCGFSbox256.rsp",
            "CBCKeySbox128.rsp",
            "CBCKeySbox192.rsp",
            "CBCKeySbox256.rsp",
            "CBCVarKey128.rsp",
            "CBCVarKey192.rsp",
            "CBCVarKey256.rsp",
            "CBCVarTxt128.rsp",
            "CBCVarTxt192.rsp",
            "CBCVarTxt256.rsp",
            "CBCMMT128.rsp",
            "CBCMMT192.rsp",
            "CBCMMT256.rsp",
        ],
        lambda key, **kwargs: algorithms.AES(binascii.unhexlify(key)),
        lambda iv, **kwargs: modes.CBC(binascii.unhexlify(iv)),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.AES("\x00" * 16), modes.ECB()
    ),
    skip_message="Does not support AES ECB",
)
@pytest.mark.cipher
class TestAESModeECB(object):
    test_ECB = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "AES", "ECB"),
        [
            "ECBGFSbox128.rsp",
            "ECBGFSbox192.rsp",
            "ECBGFSbox256.rsp",
            "ECBKeySbox128.rsp",
            "ECBKeySbox192.rsp",
            "ECBKeySbox256.rsp",
            "ECBVarKey128.rsp",
            "ECBVarKey192.rsp",
            "ECBVarKey256.rsp",
            "ECBVarTxt128.rsp",
            "ECBVarTxt192.rsp",
            "ECBVarTxt256.rsp",
            "ECBMMT128.rsp",
            "ECBMMT192.rsp",
            "ECBMMT256.rsp",
        ],
        lambda key, **kwargs: algorithms.AES(binascii.unhexlify(key)),
        lambda **kwargs: modes.ECB(),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.AES("\x00" * 16), modes.OFB("\x00" * 16)
    ),
    skip_message="Does not support AES OFB",
)
@pytest.mark.cipher
class TestAESModeOFB(object):
    test_OFB = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "AES", "OFB"),
        [
            "OFBGFSbox128.rsp",
            "OFBGFSbox192.rsp",
            "OFBGFSbox256.rsp",
            "OFBKeySbox128.rsp",
            "OFBKeySbox192.rsp",
            "OFBKeySbox256.rsp",
            "OFBVarKey128.rsp",
            "OFBVarKey192.rsp",
            "OFBVarKey256.rsp",
            "OFBVarTxt128.rsp",
            "OFBVarTxt192.rsp",
            "OFBVarTxt256.rsp",
            "OFBMMT128.rsp",
            "OFBMMT192.rsp",
            "OFBMMT256.rsp",
        ],
        lambda key, **kwargs: algorithms.AES(binascii.unhexlify(key)),
        lambda iv, **kwargs: modes.OFB(binascii.unhexlify(iv)),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.AES("\x00" * 16), modes.CFB("\x00" * 16)
    ),
    skip_message="Does not support AES CFB",
)
@pytest.mark.cipher
class TestAESModeCFB(object):
    test_CFB = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "AES", "CFB"),
        [
            "CFB128GFSbox128.rsp",
            "CFB128GFSbox192.rsp",
            "CFB128GFSbox256.rsp",
            "CFB128KeySbox128.rsp",
            "CFB128KeySbox192.rsp",
            "CFB128KeySbox256.rsp",
            "CFB128VarKey128.rsp",
            "CFB128VarKey192.rsp",
            "CFB128VarKey256.rsp",
            "CFB128VarTxt128.rsp",
            "CFB128VarTxt192.rsp",
            "CFB128VarTxt256.rsp",
            "CFB128MMT128.rsp",
            "CFB128MMT192.rsp",
            "CFB128MMT256.rsp",
        ],
        lambda key, **kwargs: algorithms.AES(binascii.unhexlify(key)),
        lambda iv, **kwargs: modes.CFB(binascii.unhexlify(iv)),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.AES("\x00" * 16), modes.CFB8("\x00" * 16)
    ),
    skip_message="Does not support AES CFB8",
)
@pytest.mark.cipher
class TestAESModeCFB8(object):
    test_CFB8 = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "AES", "CFB"),
        [
            "CFB8GFSbox128.rsp",
            "CFB8GFSbox192.rsp",
            "CFB8GFSbox256.rsp",
            "CFB8KeySbox128.rsp",
            "CFB8KeySbox192.rsp",
            "CFB8KeySbox256.rsp",
            "CFB8VarKey128.rsp",
            "CFB8VarKey192.rsp",
            "CFB8VarKey256.rsp",
            "CFB8VarTxt128.rsp",
            "CFB8VarTxt192.rsp",
            "CFB8VarTxt256.rsp",
            "CFB8MMT128.rsp",
            "CFB8MMT192.rsp",
            "CFB8MMT256.rsp",
        ],
        lambda key, **kwargs: algorithms.AES(binascii.unhexlify(key)),
        lambda iv, **kwargs: modes.CFB8(binascii.unhexlify(iv)),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.AES("\x00" * 16), modes.CTR("\x00" * 16)
    ),
    skip_message="Does not support AES CTR",
)
@pytest.mark.cipher
class TestAESModeCTR(object):
    test_CTR = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "AES", "CTR"),
        ["aes-128-ctr.txt", "aes-192-ctr.txt", "aes-256-ctr.txt"],
        lambda key, **kwargs: algorithms.AES(binascii.unhexlify(key)),
        lambda iv, **kwargs: modes.CTR(binascii.unhexlify(iv)),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.AES("\x00" * 16), modes.GCM("\x00" * 12)
    ),
    skip_message="Does not support AES GCM",
)
@pytest.mark.cipher
class TestAESModeGCM(object):
    test_GCM = generate_aead_test(
        load_nist_vectors,
        os.path.join("ciphers", "AES", "GCM"),
        [
            "gcmDecrypt128.rsp",
            "gcmDecrypt192.rsp",
            "gcmDecrypt256.rsp",
            "gcmEncryptExtIV128.rsp",
            "gcmEncryptExtIV192.rsp",
            "gcmEncryptExtIV256.rsp",
        ],
        lambda key: algorithms.AES(key),
        lambda iv, tag: modes.GCM(iv, tag),
    )

########NEW FILE########
__FILENAME__ = test_arc4
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import binascii
import os

import pytest

from cryptography.hazmat.primitives.ciphers import algorithms

from .utils import generate_stream_encryption_test
from ...utils import load_nist_vectors


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.ARC4("\x00" * 16), None
    ),
    skip_message="Does not support ARC4",
)
@pytest.mark.cipher
class TestARC4(object):
    test_rfc = generate_stream_encryption_test(
        load_nist_vectors,
        os.path.join("ciphers", "ARC4"),
        [
            "rfc-6229-40.txt",
            "rfc-6229-56.txt",
            "rfc-6229-64.txt",
            "rfc-6229-80.txt",
            "rfc-6229-128.txt",
            "rfc-6229-192.txt",
            "rfc-6229-256.txt",
        ],
        lambda key, **kwargs: algorithms.ARC4(binascii.unhexlify(key)),
    )

########NEW FILE########
__FILENAME__ = test_block
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import binascii

import pytest

from cryptography import utils
from cryptography.exceptions import (
    AlreadyFinalized, _Reasons
)
from cryptography.hazmat.primitives import interfaces
from cryptography.hazmat.primitives.ciphers import (
    Cipher, algorithms, modes
)

from .utils import (
    generate_aead_exception_test, generate_aead_tag_exception_test
)
from ...utils import raises_unsupported_algorithm


@utils.register_interface(interfaces.Mode)
class DummyMode(object):
    name = "dummy-mode"

    def validate_for_algorithm(self, algorithm):
        pass


@utils.register_interface(interfaces.CipherAlgorithm)
class DummyCipher(object):
    name = "dummy-cipher"


@pytest.mark.cipher
class TestCipher(object):
    def test_creates_encryptor(self, backend):
        cipher = Cipher(
            algorithms.AES(binascii.unhexlify(b"0" * 32)),
            modes.CBC(binascii.unhexlify(b"0" * 32)),
            backend
        )
        assert isinstance(cipher.encryptor(), interfaces.CipherContext)

    def test_creates_decryptor(self, backend):
        cipher = Cipher(
            algorithms.AES(binascii.unhexlify(b"0" * 32)),
            modes.CBC(binascii.unhexlify(b"0" * 32)),
            backend
        )
        assert isinstance(cipher.decryptor(), interfaces.CipherContext)

    def test_instantiate_with_non_algorithm(self, backend):
        algorithm = object()
        with pytest.raises(TypeError):
            Cipher(algorithm, mode=None, backend=backend)


@pytest.mark.cipher
class TestCipherContext(object):
    def test_use_after_finalize(self, backend):
        cipher = Cipher(
            algorithms.AES(binascii.unhexlify(b"0" * 32)),
            modes.CBC(binascii.unhexlify(b"0" * 32)),
            backend
        )
        encryptor = cipher.encryptor()
        encryptor.update(b"a" * 16)
        encryptor.finalize()
        with pytest.raises(AlreadyFinalized):
            encryptor.update(b"b" * 16)
        with pytest.raises(AlreadyFinalized):
            encryptor.finalize()
        decryptor = cipher.decryptor()
        decryptor.update(b"a" * 16)
        decryptor.finalize()
        with pytest.raises(AlreadyFinalized):
            decryptor.update(b"b" * 16)
        with pytest.raises(AlreadyFinalized):
            decryptor.finalize()

    def test_unaligned_block_encryption(self, backend):
        cipher = Cipher(
            algorithms.AES(binascii.unhexlify(b"0" * 32)),
            modes.ECB(),
            backend
        )
        encryptor = cipher.encryptor()
        ct = encryptor.update(b"a" * 15)
        assert ct == b""
        ct += encryptor.update(b"a" * 65)
        assert len(ct) == 80
        ct += encryptor.finalize()
        decryptor = cipher.decryptor()
        pt = decryptor.update(ct[:3])
        assert pt == b""
        pt += decryptor.update(ct[3:])
        assert len(pt) == 80
        assert pt == b"a" * 80
        decryptor.finalize()

    @pytest.mark.parametrize("mode", [DummyMode(), None])
    def test_nonexistent_cipher(self, backend, mode):
        cipher = Cipher(
            DummyCipher(), mode, backend
        )
        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_CIPHER):
            cipher.encryptor()

        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_CIPHER):
            cipher.decryptor()

    def test_incorrectly_padded(self, backend):
        cipher = Cipher(
            algorithms.AES(b"\x00" * 16),
            modes.CBC(b"\x00" * 16),
            backend
        )
        encryptor = cipher.encryptor()
        encryptor.update(b"1")
        with pytest.raises(ValueError):
            encryptor.finalize()

        decryptor = cipher.decryptor()
        decryptor.update(b"1")
        with pytest.raises(ValueError):
            decryptor.finalize()


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.AES("\x00" * 16), modes.GCM("\x00" * 12)
    ),
    skip_message="Does not support AES GCM",
)
@pytest.mark.cipher
class TestAEADCipherContext(object):
    test_aead_exceptions = generate_aead_exception_test(
        algorithms.AES,
        modes.GCM,
    )
    test_aead_tag_exceptions = generate_aead_tag_exception_test(
        algorithms.AES,
        modes.GCM,
    )


@pytest.mark.cipher
class TestModeValidation(object):
    def test_cbc(self, backend):
        with pytest.raises(ValueError):
            Cipher(
                algorithms.AES(b"\x00" * 16),
                modes.CBC(b"abc"),
                backend,
            )

    def test_ofb(self, backend):
        with pytest.raises(ValueError):
            Cipher(
                algorithms.AES(b"\x00" * 16),
                modes.OFB(b"abc"),
                backend,
            )

    def test_cfb(self, backend):
        with pytest.raises(ValueError):
            Cipher(
                algorithms.AES(b"\x00" * 16),
                modes.CFB(b"abc"),
                backend,
            )

    def test_cfb8(self, backend):
        with pytest.raises(ValueError):
            Cipher(
                algorithms.AES(b"\x00" * 16),
                modes.CFB8(b"abc"),
                backend,
            )

    def test_ctr(self, backend):
        with pytest.raises(ValueError):
            Cipher(
                algorithms.AES(b"\x00" * 16),
                modes.CTR(b"abc"),
                backend,
            )

########NEW FILE########
__FILENAME__ = test_blowfish
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import binascii
import os

import pytest

from cryptography.hazmat.primitives.ciphers import algorithms, modes

from .utils import generate_encrypt_test
from ...utils import load_nist_vectors


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.Blowfish("\x00" * 56), modes.ECB()
    ),
    skip_message="Does not support Blowfish ECB",
)
@pytest.mark.cipher
class TestBlowfishModeECB(object):
    test_ECB = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "Blowfish"),
        ["bf-ecb.txt"],
        lambda key, **kwargs: algorithms.Blowfish(binascii.unhexlify(key)),
        lambda **kwargs: modes.ECB(),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.Blowfish("\x00" * 56), modes.CBC("\x00" * 8)
    ),
    skip_message="Does not support Blowfish CBC",
)
@pytest.mark.cipher
class TestBlowfishModeCBC(object):
    test_CBC = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "Blowfish"),
        ["bf-cbc.txt"],
        lambda key, **kwargs: algorithms.Blowfish(binascii.unhexlify(key)),
        lambda iv, **kwargs: modes.CBC(binascii.unhexlify(iv)),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.Blowfish("\x00" * 56), modes.OFB("\x00" * 8)
    ),
    skip_message="Does not support Blowfish OFB",
)
@pytest.mark.cipher
class TestBlowfishModeOFB(object):
    test_OFB = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "Blowfish"),
        ["bf-ofb.txt"],
        lambda key, **kwargs: algorithms.Blowfish(binascii.unhexlify(key)),
        lambda iv, **kwargs: modes.OFB(binascii.unhexlify(iv)),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.Blowfish("\x00" * 56), modes.CFB("\x00" * 8)
    ),
    skip_message="Does not support Blowfish CFB",
)
@pytest.mark.cipher
class TestBlowfishModeCFB(object):
    test_CFB = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "Blowfish"),
        ["bf-cfb.txt"],
        lambda key, **kwargs: algorithms.Blowfish(binascii.unhexlify(key)),
        lambda iv, **kwargs: modes.CFB(binascii.unhexlify(iv)),
    )

########NEW FILE########
__FILENAME__ = test_camellia
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import binascii
import os

import pytest

from cryptography.hazmat.primitives.ciphers import algorithms, modes

from .utils import generate_encrypt_test
from ...utils import (
    load_cryptrec_vectors, load_nist_vectors
)


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.Camellia("\x00" * 16), modes.ECB()
    ),
    skip_message="Does not support Camellia ECB",
)
@pytest.mark.cipher
class TestCamelliaModeECB(object):
    test_ECB = generate_encrypt_test(
        load_cryptrec_vectors,
        os.path.join("ciphers", "Camellia"),
        [
            "camellia-128-ecb.txt",
            "camellia-192-ecb.txt",
            "camellia-256-ecb.txt"
        ],
        lambda key, **kwargs: algorithms.Camellia(binascii.unhexlify(key)),
        lambda **kwargs: modes.ECB(),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.Camellia("\x00" * 16), modes.CBC("\x00" * 16)
    ),
    skip_message="Does not support Camellia CBC",
)
@pytest.mark.cipher
class TestCamelliaModeCBC(object):
    test_CBC = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "Camellia"),
        ["camellia-cbc.txt"],
        lambda key, **kwargs: algorithms.Camellia(binascii.unhexlify(key)),
        lambda iv, **kwargs: modes.CBC(binascii.unhexlify(iv)),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.Camellia("\x00" * 16), modes.OFB("\x00" * 16)
    ),
    skip_message="Does not support Camellia OFB",
)
@pytest.mark.cipher
class TestCamelliaModeOFB(object):
    test_OFB = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "Camellia"),
        ["camellia-ofb.txt"],
        lambda key, **kwargs: algorithms.Camellia(binascii.unhexlify(key)),
        lambda iv, **kwargs: modes.OFB(binascii.unhexlify(iv)),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.Camellia("\x00" * 16), modes.CFB("\x00" * 16)
    ),
    skip_message="Does not support Camellia CFB",
)
@pytest.mark.cipher
class TestCamelliaModeCFB(object):
    test_CFB = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "Camellia"),
        ["camellia-cfb.txt"],
        lambda key, **kwargs: algorithms.Camellia(binascii.unhexlify(key)),
        lambda iv, **kwargs: modes.CFB(binascii.unhexlify(iv)),
    )

########NEW FILE########
__FILENAME__ = test_cast5
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import binascii
import os

import pytest

from cryptography.hazmat.primitives.ciphers import algorithms, modes

from .utils import generate_encrypt_test
from ...utils import load_nist_vectors


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.CAST5("\x00" * 16), modes.ECB()
    ),
    skip_message="Does not support CAST5 ECB",
)
@pytest.mark.cipher
class TestCAST5ModeECB(object):
    test_ECB = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "CAST5"),
        ["cast5-ecb.txt"],
        lambda key, **kwargs: algorithms.CAST5(binascii.unhexlify((key))),
        lambda **kwargs: modes.ECB(),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.CAST5("\x00" * 16), modes.CBC("\x00" * 8)
    ),
    skip_message="Does not support CAST5 CBC",
)
@pytest.mark.cipher
class TestCAST5ModeCBC(object):
    test_CBC = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "CAST5"),
        ["cast5-cbc.txt"],
        lambda key, **kwargs: algorithms.CAST5(binascii.unhexlify((key))),
        lambda iv, **kwargs: modes.CBC(binascii.unhexlify(iv))
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.CAST5("\x00" * 16), modes.OFB("\x00" * 8)
    ),
    skip_message="Does not support CAST5 OFB",
)
@pytest.mark.cipher
class TestCAST5ModeOFB(object):
    test_OFB = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "CAST5"),
        ["cast5-ofb.txt"],
        lambda key, **kwargs: algorithms.CAST5(binascii.unhexlify((key))),
        lambda iv, **kwargs: modes.OFB(binascii.unhexlify(iv))
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.CAST5("\x00" * 16), modes.CFB("\x00" * 8)
    ),
    skip_message="Does not support CAST5 CFB",
)
@pytest.mark.cipher
class TestCAST5ModeCFB(object):
    test_CFB = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "CAST5"),
        ["cast5-cfb.txt"],
        lambda key, **kwargs: algorithms.CAST5(binascii.unhexlify((key))),
        lambda iv, **kwargs: modes.CFB(binascii.unhexlify(iv))
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.CAST5("\x00" * 16), modes.CTR("\x00" * 8)
    ),
    skip_message="Does not support CAST5 CTR",
)
@pytest.mark.cipher
class TestCAST5ModeCTR(object):
    test_CTR = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "CAST5"),
        ["cast5-ctr.txt"],
        lambda key, **kwargs: algorithms.CAST5(binascii.unhexlify((key))),
        lambda iv, **kwargs: modes.CTR(binascii.unhexlify(iv))
    )

########NEW FILE########
__FILENAME__ = test_ciphers
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import binascii

import pytest

from cryptography.exceptions import _Reasons
from cryptography.hazmat.primitives import ciphers
from cryptography.hazmat.primitives.ciphers.algorithms import (
    AES, ARC4, Blowfish, CAST5, Camellia, IDEA, SEED, TripleDES
)
from cryptography.hazmat.primitives.ciphers.modes import ECB

from ...utils import raises_unsupported_algorithm


class TestAES(object):
    @pytest.mark.parametrize(("key", "keysize"), [
        (b"0" * 32, 128),
        (b"0" * 48, 192),
        (b"0" * 64, 256),
    ])
    def test_key_size(self, key, keysize):
        cipher = AES(binascii.unhexlify(key))
        assert cipher.key_size == keysize

    def test_invalid_key_size(self):
        with pytest.raises(ValueError):
            AES(binascii.unhexlify(b"0" * 12))


class TestCamellia(object):
    @pytest.mark.parametrize(("key", "keysize"), [
        (b"0" * 32, 128),
        (b"0" * 48, 192),
        (b"0" * 64, 256),
    ])
    def test_key_size(self, key, keysize):
        cipher = Camellia(binascii.unhexlify(key))
        assert cipher.key_size == keysize

    def test_invalid_key_size(self):
        with pytest.raises(ValueError):
            Camellia(binascii.unhexlify(b"0" * 12))


class TestTripleDES(object):
    @pytest.mark.parametrize("key", [
        b"0" * 16,
        b"0" * 32,
        b"0" * 48,
    ])
    def test_key_size(self, key):
        cipher = TripleDES(binascii.unhexlify(key))
        assert cipher.key_size == 192

    def test_invalid_key_size(self):
        with pytest.raises(ValueError):
            TripleDES(binascii.unhexlify(b"0" * 12))


class TestBlowfish(object):
    @pytest.mark.parametrize(("key", "keysize"), [
        (b"0" * (keysize // 4), keysize) for keysize in range(32, 449, 8)
    ])
    def test_key_size(self, key, keysize):
        cipher = Blowfish(binascii.unhexlify(key))
        assert cipher.key_size == keysize

    def test_invalid_key_size(self):
        with pytest.raises(ValueError):
            Blowfish(binascii.unhexlify(b"0" * 6))


class TestCAST5(object):
    @pytest.mark.parametrize(("key", "keysize"), [
        (b"0" * (keysize // 4), keysize) for keysize in range(40, 129, 8)
    ])
    def test_key_size(self, key, keysize):
        cipher = CAST5(binascii.unhexlify(key))
        assert cipher.key_size == keysize

    def test_invalid_key_size(self):
        with pytest.raises(ValueError):
            CAST5(binascii.unhexlify(b"0" * 34))


class TestARC4(object):
    @pytest.mark.parametrize(("key", "keysize"), [
        (b"0" * 10, 40),
        (b"0" * 14, 56),
        (b"0" * 16, 64),
        (b"0" * 20, 80),
        (b"0" * 32, 128),
        (b"0" * 48, 192),
        (b"0" * 64, 256),
    ])
    def test_key_size(self, key, keysize):
        cipher = ARC4(binascii.unhexlify(key))
        assert cipher.key_size == keysize

    def test_invalid_key_size(self):
        with pytest.raises(ValueError):
            ARC4(binascii.unhexlify(b"0" * 34))


class TestIDEA(object):
    def test_key_size(self):
        cipher = IDEA(b"\x00" * 16)
        assert cipher.key_size == 128

    def test_invalid_key_size(self):
        with pytest.raises(ValueError):
            IDEA(b"\x00" * 17)


class TestSEED(object):
    def test_key_size(self):
        cipher = SEED(b"\x00" * 16)
        assert cipher.key_size == 128

    def test_invalid_key_size(self):
        with pytest.raises(ValueError):
            SEED(b"\x00" * 17)


def test_invalid_backend():
    pretend_backend = object()

    with raises_unsupported_algorithm(_Reasons.BACKEND_MISSING_INTERFACE):
        ciphers.Cipher(AES(b"AAAAAAAAAAAAAAAA"), ECB, pretend_backend)

########NEW FILE########
__FILENAME__ = test_cmac
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import binascii

import pretend

import pytest

import six

from cryptography import utils
from cryptography.exceptions import (
    AlreadyFinalized, InvalidSignature, _Reasons
)
from cryptography.hazmat.backends.interfaces import CMACBackend
from cryptography.hazmat.primitives.ciphers.algorithms import (
    AES, ARC4, TripleDES
)
from cryptography.hazmat.primitives.cmac import CMAC

from tests.utils import (
    load_nist_vectors, load_vectors_from_file, raises_unsupported_algorithm
)

vectors_aes128 = load_vectors_from_file(
    "CMAC/nist-800-38b-aes128.txt", load_nist_vectors)

vectors_aes192 = load_vectors_from_file(
    "CMAC/nist-800-38b-aes192.txt", load_nist_vectors)

vectors_aes256 = load_vectors_from_file(
    "CMAC/nist-800-38b-aes256.txt", load_nist_vectors)

vectors_aes = vectors_aes128 + vectors_aes192 + vectors_aes256

vectors_3des = load_vectors_from_file(
    "CMAC/nist-800-38b-3des.txt", load_nist_vectors)

fake_key = b"\x00" * 16


@pytest.mark.cmac
class TestCMAC(object):
    @pytest.mark.supported(
        only_if=lambda backend: backend.cmac_algorithm_supported(
            AES(fake_key)),
        skip_message="Does not support CMAC."
    )
    @pytest.mark.parametrize("params", vectors_aes)
    def test_aes_generate(self, backend, params):
        key = params["key"]
        message = params["message"]
        output = params["output"]

        cmac = CMAC(AES(binascii.unhexlify(key)), backend)
        cmac.update(binascii.unhexlify(message))
        assert binascii.hexlify(cmac.finalize()) == output

    @pytest.mark.supported(
        only_if=lambda backend: backend.cmac_algorithm_supported(
            AES(fake_key)),
        skip_message="Does not support CMAC."
    )
    @pytest.mark.parametrize("params", vectors_aes)
    def test_aes_verify(self, backend, params):
        key = params["key"]
        message = params["message"]
        output = params["output"]

        cmac = CMAC(AES(binascii.unhexlify(key)), backend)
        cmac.update(binascii.unhexlify(message))
        assert cmac.verify(binascii.unhexlify(output)) is None

    @pytest.mark.supported(
        only_if=lambda backend: backend.cmac_algorithm_supported(
            TripleDES(fake_key)),
        skip_message="Does not support CMAC."
    )
    @pytest.mark.parametrize("params", vectors_3des)
    def test_3des_generate(self, backend, params):
        key1 = params["key1"]
        key2 = params["key2"]
        key3 = params["key3"]

        key = key1 + key2 + key3

        message = params["message"]
        output = params["output"]

        cmac = CMAC(TripleDES(binascii.unhexlify(key)), backend)
        cmac.update(binascii.unhexlify(message))
        assert binascii.hexlify(cmac.finalize()) == output

    @pytest.mark.supported(
        only_if=lambda backend: backend.cmac_algorithm_supported(
            TripleDES(fake_key)),
        skip_message="Does not support CMAC."
    )
    @pytest.mark.parametrize("params", vectors_3des)
    def test_3des_verify(self, backend, params):
        key1 = params["key1"]
        key2 = params["key2"]
        key3 = params["key3"]

        key = key1 + key2 + key3

        message = params["message"]
        output = params["output"]

        cmac = CMAC(TripleDES(binascii.unhexlify(key)), backend)
        cmac.update(binascii.unhexlify(message))
        assert cmac.verify(binascii.unhexlify(output)) is None

    @pytest.mark.supported(
        only_if=lambda backend: backend.cmac_algorithm_supported(
            AES(fake_key)),
        skip_message="Does not support CMAC."
    )
    def test_invalid_verify(self, backend):
        key = b"2b7e151628aed2a6abf7158809cf4f3c"
        cmac = CMAC(AES(key), backend)
        cmac.update(b"6bc1bee22e409f96e93d7e117393172a")

        with pytest.raises(InvalidSignature):
            cmac.verify(b"foobar")

    @pytest.mark.supported(
        only_if=lambda backend: backend.cipher_supported(
            ARC4(fake_key), None),
        skip_message="Does not support CMAC."
    )
    def test_invalid_algorithm(self, backend):
        key = b"0102030405"
        with pytest.raises(TypeError):
            CMAC(ARC4(key), backend)

    @pytest.mark.supported(
        only_if=lambda backend: backend.cmac_algorithm_supported(
            AES(fake_key)),
        skip_message="Does not support CMAC."
    )
    def test_raises_after_finalize(self, backend):
        key = b"2b7e151628aed2a6abf7158809cf4f3c"
        cmac = CMAC(AES(key), backend)
        cmac.finalize()

        with pytest.raises(AlreadyFinalized):
            cmac.update(b"foo")

        with pytest.raises(AlreadyFinalized):
            cmac.copy()

        with pytest.raises(AlreadyFinalized):
            cmac.finalize()

    @pytest.mark.supported(
        only_if=lambda backend: backend.cmac_algorithm_supported(
            AES(fake_key)),
        skip_message="Does not support CMAC."
    )
    def test_verify_reject_unicode(self, backend):
        key = b"2b7e151628aed2a6abf7158809cf4f3c"
        cmac = CMAC(AES(key), backend)

        with pytest.raises(TypeError):
            cmac.update(six.u(''))

        with pytest.raises(TypeError):
            cmac.verify(six.u(''))

    @pytest.mark.supported(
        only_if=lambda backend: backend.cmac_algorithm_supported(
            AES(fake_key)),
        skip_message="Does not support CMAC."
    )
    def test_copy_with_backend(self, backend):
        key = b"2b7e151628aed2a6abf7158809cf4f3c"
        cmac = CMAC(AES(key), backend)
        cmac.update(b"6bc1bee22e409f96e93d7e117393172a")
        copy_cmac = cmac.copy()
        assert cmac.finalize() == copy_cmac.finalize()


def test_copy():
    @utils.register_interface(CMACBackend)
    class PretendBackend(object):
        pass

    pretend_backend = PretendBackend()
    copied_ctx = pretend.stub()
    pretend_ctx = pretend.stub(copy=lambda: copied_ctx)
    key = b"2b7e151628aed2a6abf7158809cf4f3c"
    cmac = CMAC(AES(key), backend=pretend_backend, ctx=pretend_ctx)

    assert cmac._backend is pretend_backend
    assert cmac.copy()._backend is pretend_backend


def test_invalid_backend():
    key = b"2b7e151628aed2a6abf7158809cf4f3c"
    pretend_backend = object()

    with raises_unsupported_algorithm(_Reasons.BACKEND_MISSING_INTERFACE):
        CMAC(AES(key), pretend_backend)

########NEW FILE########
__FILENAME__ = test_constant_time
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import pytest

import six

from cryptography.hazmat.primitives import constant_time


class TestConstantTimeBytesEq(object):
    def test_reject_unicode(self):
        with pytest.raises(TypeError):
            constant_time.bytes_eq(b"foo", six.u("foo"))

        with pytest.raises(TypeError):
            constant_time.bytes_eq(six.u("foo"), b"foo")

        with pytest.raises(TypeError):
            constant_time.bytes_eq(six.u("foo"), six.u("foo"))

    def test_compares(self):
        assert constant_time.bytes_eq(b"foo", b"foo") is True

        assert constant_time.bytes_eq(b"foo", b"bar") is False

        assert constant_time.bytes_eq(b"foobar", b"foo") is False

        assert constant_time.bytes_eq(b"foo", b"foobar") is False

########NEW FILE########
__FILENAME__ = test_dsa
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from __future__ import absolute_import, division, print_function

import os

import pytest

from cryptography.exceptions import (
    AlreadyFinalized, InvalidSignature, _Reasons)
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import dsa
from cryptography.utils import bit_length

from ...utils import (
    der_encode_dsa_signature, load_fips_dsa_key_pair_vectors,
    load_fips_dsa_sig_vectors, load_vectors_from_file,
    raises_unsupported_algorithm
)


def _check_dsa_private_key(skey):
    assert skey
    assert skey.x
    assert skey.y
    assert skey.key_size

    skey_parameters = skey.parameters()
    assert skey_parameters
    assert skey_parameters.modulus
    assert skey_parameters.subgroup_order
    assert skey_parameters.generator
    assert skey_parameters.modulus == skey_parameters.p
    assert skey_parameters.subgroup_order == skey_parameters.q
    assert skey_parameters.generator == skey_parameters.g

    pkey = skey.public_key()
    assert pkey
    assert skey.y == pkey.y
    assert skey.key_size == pkey.key_size

    pkey_parameters = pkey.parameters()
    assert pkey_parameters
    assert pkey_parameters.modulus
    assert pkey_parameters.subgroup_order
    assert pkey_parameters.generator
    assert pkey_parameters.modulus == pkey_parameters.p
    assert pkey_parameters.subgroup_order == pkey_parameters.q
    assert pkey_parameters.generator == pkey_parameters.g

    assert skey_parameters.modulus == pkey_parameters.modulus
    assert skey_parameters.subgroup_order == pkey_parameters.subgroup_order
    assert skey_parameters.generator == pkey_parameters.generator


@pytest.mark.dsa
class TestDSA(object):
    _parameters_1024 = {
        'p': 'd38311e2cd388c3ed698e82fdf88eb92b5a9a483dc88005d4b725ef341eabb47'
        'cf8a7a8a41e792a156b7ce97206c4f9c5ce6fc5ae7912102b6b502e59050b5b21ce26'
        '3dddb2044b652236f4d42ab4b5d6aa73189cef1ace778d7845a5c1c1c7147123188f8'
        'dc551054ee162b634d60f097f719076640e20980a0093113a8bd73',

        'q': '96c5390a8b612c0e422bb2b0ea194a3ec935a281',

        'g': '06b7861abbd35cc89e79c52f68d20875389b127361ca66822138ce4991d2b862'
        '259d6b4548a6495b195aa0e0b6137ca37eb23b94074d3c3d300042bdf15762812b633'
        '3ef7b07ceba78607610fcc9ee68491dbc1e34cd12615474e52b18bc934fb00c61d39e'
        '7da8902291c4434a4e2224c3f4fd9f93cd6f4f17fc076341a7e7d9',

        'x': '8185fee9cc7c0e91fd85503274f1cd5a3fd15a49',

        'y': '6f26d98d41de7d871b6381851c9d91fa03942092ab6097e76422070edb71db44'
        'ff568280fdb1709f8fc3feab39f1f824adaeb2a298088156ac31af1aa04bf54f475bd'
        'cfdcf2f8a2dd973e922d83e76f016558617603129b21c70bf7d0e5dc9e68fe332e295'
        'b65876eb9a12fe6fca9f1a1ce80204646bf99b5771d249a6fea627'
    }

    _parameters_2048 = {
        'p': 'ea1fb1af22881558ef93be8a5f8653c5a559434c49c8c2c12ace5e9c41434c9c'
        'f0a8e9498acb0f4663c08b4484eace845f6fb17dac62c98e706af0fc74e4da1c6c2b3'
        'fbf5a1d58ff82fc1a66f3e8b12252c40278fff9dd7f102eed2cb5b7323ebf1908c234'
        'd935414dded7f8d244e54561b0dca39b301de8c49da9fb23df33c6182e3f983208c56'
        '0fb5119fbf78ebe3e6564ee235c6a15cbb9ac247baba5a423bc6582a1a9d8a2b4f0e9'
        'e3d9dbac122f750dd754325135257488b1f6ecabf21bff2947fe0d3b2cb7ffe67f4e7'
        'fcdf1214f6053e72a5bb0dd20a0e9fe6db2df0a908c36e95e60bf49ca4368b8b892b9'
        'c79f61ef91c47567c40e1f80ac5aa66ef7',

        'q': '8ec73f3761caf5fdfe6e4e82098bf10f898740dcb808204bf6b18f'
        '507192c19d',

        'g': 'e4c4eca88415b23ecf811c96e48cd24200fe916631a68a684e6ccb6b1913413d'
        '344d1d8d84a333839d88eee431521f6e357c16e6a93be111a98076739cd401bab3b9d'
        '565bf4fb99e9d185b1e14d61c93700133f908bae03e28764d107dcd2ea76742176220'
        '74bb19efff482f5f5c1a86d5551b2fc68d1c6e9d8011958ef4b9c2a3a55d0d3c882e6'
        'ad7f9f0f3c61568f78d0706b10a26f23b4f197c322b825002284a0aca91807bba98ec'
        'e912b80e10cdf180cf99a35f210c1655fbfdd74f13b1b5046591f8403873d12239834'
        'dd6c4eceb42bf7482e1794a1601357b629ddfa971f2ed273b146ec1ca06d0adf55dd9'
        '1d65c37297bda78c6d210c0bc26e558302',

        'x': '405772da6e90d809e77d5de796562a2dd4dfd10ef00a83a3aba6bd'
        '818a0348a1',

        'y': '6b32e31ab9031dc4dd0b5039a78d07826687ab087ae6de4736f5b0434e125309'
        '2e8a0b231f9c87f3fc8a4cb5634eb194bf1b638b7a7889620ce6711567e36aa36cda4'
        '604cfaa601a45918371d4ccf68d8b10a50a0460eb1dc0fff62ef5e6ee4d473e18ea4a'
        '66c196fb7e677a49b48241a0b4a97128eff30fa437050501a584f8771e7280d26d5af'
        '30784039159c11ebfea10b692fd0a58215eeb18bff117e13f08db792ed4151a218e4b'
        'ed8dddfb0793225bd1e9773505166f4bd8cedbb286ea28232972da7bae836ba97329b'
        'a6b0a36508e50a52a7675e476d4d4137eae13f22a9d2fefde708ba8f34bf336c6e763'
        '31761e4b0617633fe7ec3f23672fb19d27'
    }

    _parameters_3072 = {
        'p': 'f335666dd1339165af8b9a5e3835adfe15c158e4c3c7bd53132e7d5828c352f5'
        '93a9a787760ce34b789879941f2f01f02319f6ae0b756f1a842ba54c85612ed632ee2'
        'd79ef17f06b77c641b7b080aff52a03fc2462e80abc64d223723c236deeb7d201078e'
        'c01ca1fbc1763139e25099a84ec389159c409792080736bd7caa816b92edf23f2c351'
        'f90074aa5ea2651b372f8b58a0a65554db2561d706a63685000ac576b7e4562e262a1'
        '4285a9c6370b290e4eb7757527d80b6c0fd5df831d36f3d1d35f12ab060548de1605f'
        'd15f7c7aafed688b146a02c945156e284f5b71282045aba9844d48b5df2e9e7a58871'
        '21eae7d7b01db7cdf6ff917cd8eb50c6bf1d54f90cce1a491a9c74fea88f7e7230b04'
        '7d16b5a6027881d6f154818f06e513faf40c8814630e4e254f17a47bfe9cb519b9828'
        '9935bf17673ae4c8033504a20a898d0032ee402b72d5986322f3bdfb27400561f7476'
        'cd715eaabb7338b854e51fc2fa026a5a579b6dcea1b1c0559c13d3c1136f303f4b4d2'
        '5ad5b692229957',

        'q': 'd3eba6521240694015ef94412e08bf3cf8d635a455a398d6f210f'
        '6169041653b',

        'g': 'ce84b30ddf290a9f787a7c2f1ce92c1cbf4ef400e3cd7ce4978db2104d7394b4'
        '93c18332c64cec906a71c3778bd93341165dee8e6cd4ca6f13afff531191194ada55e'
        'cf01ff94d6cf7c4768b82dd29cd131aaf202aefd40e564375285c01f3220af4d70b96'
        'f1395420d778228f1461f5d0b8e47357e87b1fe3286223b553e3fc9928f16ae3067de'
        'd6721bedf1d1a01bfd22b9ae85fce77820d88cdf50a6bde20668ad77a707d1c60fcc5'
        'd51c9de488610d0285eb8ff721ff141f93a9fb23c1d1f7654c07c46e58836d1652828'
        'f71057b8aff0b0778ef2ca934ea9d0f37daddade2d823a4d8e362721082e279d003b5'
        '75ee59fd050d105dfd71cd63154efe431a0869178d9811f4f231dc5dcf3b0ec0f2b0f'
        '9896c32ec6c7ee7d60aa97109e09224907328d4e6acd10117e45774406c4c947da802'
        '0649c3168f690e0bd6e91ac67074d1d436b58ae374523deaf6c93c1e6920db4a080b7'
        '44804bb073cecfe83fa9398cf150afa286dc7eb7949750cf5001ce104e9187f7e1685'
        '9afa8fd0d775ae',

        'x': 'b2764c46113983777d3e7e97589f1303806d14ad9f2f1ef033097'
        'de954b17706',

        'y': '814824e435e1e6f38daa239aad6dad21033afce6a3ebd35c1359348a0f241887'
        '1968c2babfc2baf47742148828f8612183178f126504da73566b6bab33ba1f124c15a'
        'a461555c2451d86c94ee21c3e3fc24c55527e01b1f03adcdd8ec5cb08082803a7b6a8'
        '29c3e99eeb332a2cf5c035b0ce0078d3d414d31fa47e9726be2989b8d06da2e6cd363'
        'f5a7d1515e3f4925e0b32adeae3025cc5a996f6fd27494ea408763de48f3bb39f6a06'
        '514b019899b312ec570851637b8865cff3a52bf5d54ad5a19e6e400a2d33251055d0a'
        '440b50d53f4791391dc754ad02b9eab74c46b4903f9d76f824339914db108057af7cd'
        'e657d41766a99991ac8787694f4185d6f91d7627048f827b405ec67bf2fe56141c4c5'
        '81d8c317333624e073e5879a82437cb0c7b435c0ce434e15965db1315d64895991e6b'
        'be7dac040c42052408bbc53423fd31098248a58f8a67da3a39895cd0cc927515d044c'
        '1e3cb6a3259c3d0da354cce89ea3552c59609db10ee989986527436af21d9485ddf25'
        'f90f7dff6d2bae'
    }

    def test_generate_dsa_parameters(self, backend):
        parameters = dsa.DSAParameters.generate(1024, backend)
        assert bit_length(parameters.p) == 1024

    def test_generate_invalid_dsa_parameters(self, backend):
        with pytest.raises(ValueError):
            dsa.DSAParameters.generate(1, backend)

    @pytest.mark.parametrize(
        "vector",
        load_vectors_from_file(
            os.path.join(
                "asymmetric", "DSA", "FIPS_186-3", "KeyPair.rsp"),
            load_fips_dsa_key_pair_vectors
        )
    )
    def test_generate_dsa_keys(self, vector, backend):
        parameters = dsa.DSAParameters(modulus=vector['p'],
                                       subgroup_order=vector['q'],
                                       generator=vector['g'])
        skey = dsa.DSAPrivateKey.generate(parameters, backend)

        skey_parameters = skey.parameters()
        assert skey_parameters.p == vector['p']
        assert skey_parameters.q == vector['q']
        assert skey_parameters.g == vector['g']
        assert skey.key_size == bit_length(vector['p'])
        assert skey.y == pow(skey_parameters.g, skey.x, skey_parameters.p)

    def test_invalid_parameters_argument_types(self):
        with pytest.raises(TypeError):
            dsa.DSAParameters(None, None, None)

    def test_invalid_private_key_argument_types(self):
        with pytest.raises(TypeError):
            dsa.DSAPrivateKey(None, None, None, None, None)

    def test_invalid_public_key_argument_types(self):
        with pytest.raises(TypeError):
            dsa.DSAPublicKey(None, None, None, None)

    def test_load_dsa_example_keys(self):
        parameters = dsa.DSAParameters(
            modulus=int(self._parameters_1024['p'], 16),
            subgroup_order=int(self._parameters_1024['q'], 16),
            generator=int(self._parameters_1024['g'], 16))

        assert parameters
        assert parameters.modulus
        assert parameters.subgroup_order
        assert parameters.generator
        assert parameters.modulus == parameters.p
        assert parameters.subgroup_order == parameters.q
        assert parameters.generator == parameters.g

        pub_key = dsa.DSAPublicKey(
            modulus=int(self._parameters_1024["p"], 16),
            subgroup_order=int(self._parameters_1024["q"], 16),
            generator=int(self._parameters_1024["g"], 16),
            y=int(self._parameters_1024["y"], 16)
        )
        assert pub_key
        assert pub_key.key_size
        assert pub_key.y
        pub_key_parameters = pub_key.parameters()
        assert pub_key_parameters
        assert pub_key_parameters.modulus
        assert pub_key_parameters.subgroup_order
        assert pub_key_parameters.generator

        skey = dsa.DSAPrivateKey(
            modulus=int(self._parameters_1024["p"], 16),
            subgroup_order=int(self._parameters_1024["q"], 16),
            generator=int(self._parameters_1024["g"], 16),
            x=int(self._parameters_1024["x"], 16),
            y=int(self._parameters_1024["y"], 16)
        )
        assert skey
        _check_dsa_private_key(skey)
        skey_parameters = skey.parameters()
        assert skey_parameters
        assert skey_parameters.modulus
        assert skey_parameters.subgroup_order
        assert skey_parameters.generator

        pkey = dsa.DSAPublicKey(
            modulus=int(self._parameters_1024["p"], 16),
            subgroup_order=int(self._parameters_1024["q"], 16),
            generator=int(self._parameters_1024["g"], 16),
            y=int(self._parameters_1024["y"], 16)
        )
        assert pkey
        pkey_parameters = pkey.parameters()
        assert pkey_parameters
        assert pkey_parameters.modulus
        assert pkey_parameters.subgroup_order
        assert pkey_parameters.generator

        pkey2 = skey.public_key()
        assert pkey2
        pkey2_parameters = pkey.parameters()
        assert pkey2_parameters
        assert pkey2_parameters.modulus
        assert pkey2_parameters.subgroup_order
        assert pkey2_parameters.generator

        assert skey_parameters.modulus == pkey_parameters.modulus
        assert skey_parameters.subgroup_order == pkey_parameters.subgroup_order
        assert skey_parameters.generator == pkey_parameters.generator
        assert skey.y == pkey.y
        assert skey.key_size == pkey.key_size

        assert pkey_parameters.modulus == pkey2_parameters.modulus
        assert pkey_parameters.subgroup_order == \
            pkey2_parameters.subgroup_order
        assert pkey_parameters.generator == pkey2_parameters.generator
        assert pkey.y == pkey2.y
        assert pkey.key_size == pkey2.key_size

    def test_invalid_parameters_values(self):
        # Test a modulus < 1024 bits in length
        with pytest.raises(ValueError):
            dsa.DSAParameters(
                modulus=2 ** 1000,
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=int(self._parameters_1024['g'], 16)
            )

        # Test a modulus < 2048 bits in length
        with pytest.raises(ValueError):
            dsa.DSAParameters(
                modulus=2 ** 2000,
                subgroup_order=int(self._parameters_2048['q'], 16),
                generator=int(self._parameters_2048['g'], 16)
            )

        # Test a modulus < 3072 bits in length
        with pytest.raises(ValueError):
            dsa.DSAParameters(
                modulus=2 ** 3000,
                subgroup_order=int(self._parameters_3072['q'], 16),
                generator=int(self._parameters_3072['g'], 16)
            )

        # Test a modulus > 3072 bits in length
        with pytest.raises(ValueError):
            dsa.DSAParameters(
                modulus=2 ** 3100,
                subgroup_order=int(self._parameters_3072['q'], 16),
                generator=int(self._parameters_3072['g'], 16)
            )

        # Test a subgroup_order < 160 bits in length
        with pytest.raises(ValueError):
            dsa.DSAParameters(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=2 ** 150,
                generator=int(self._parameters_1024['g'], 16)
            )

        # Test a subgroup_order < 256 bits in length
        with pytest.raises(ValueError):
            dsa.DSAParameters(
                modulus=int(self._parameters_2048['p'], 16),
                subgroup_order=2 ** 250,
                generator=int(self._parameters_2048['g'], 16)
            )

        # Test a subgroup_order > 256 bits in length
        with pytest.raises(ValueError):
            dsa.DSAParameters(
                modulus=int(self._parameters_3072['p'], 16),
                subgroup_order=2 ** 260,
                generator=int(self._parameters_3072['g'], 16)
            )

        # Test a modulus, subgroup_order pair of (1024, 256) bit lengths
        with pytest.raises(ValueError):
            dsa.DSAParameters(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=int(self._parameters_2048['q'], 16),
                generator=int(self._parameters_1024['g'], 16)
            )

        # Test a modulus, subgroup_order pair of (2048, 160) bit lengths
        with pytest.raises(ValueError):
            dsa.DSAParameters(
                modulus=int(self._parameters_2048['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=int(self._parameters_2048['g'], 16)
            )

        # Test a modulus, subgroup_order pair of (3072, 160) bit lengths
        with pytest.raises(ValueError):
            dsa.DSAParameters(
                modulus=int(self._parameters_3072['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=int(self._parameters_3072['g'], 16)
            )

        # Test a generator < 1
        with pytest.raises(ValueError):
            dsa.DSAParameters(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=0
            )

        # Test a generator = 1
        with pytest.raises(ValueError):
            dsa.DSAParameters(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=1
            )

        # Test a generator > modulus
        with pytest.raises(ValueError):
            dsa.DSAParameters(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=2 ** 1200
            )

    def test_invalid_dsa_private_key_arguments(self):
        # Test a modulus < 1024 bits in length
        with pytest.raises(ValueError):
            dsa.DSAPrivateKey(
                modulus=2 ** 1000,
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=int(self._parameters_1024['g'], 16),
                x=int(self._parameters_1024['x'], 16),
                y=int(self._parameters_1024['y'], 16)
            )

        # Test a modulus < 2048 bits in length
        with pytest.raises(ValueError):
            dsa.DSAPrivateKey(
                modulus=2 ** 2000,
                subgroup_order=int(self._parameters_2048['q'], 16),
                generator=int(self._parameters_2048['g'], 16),
                x=int(self._parameters_2048['x'], 16),
                y=int(self._parameters_2048['y'], 16)
            )

        # Test a modulus < 3072 bits in length
        with pytest.raises(ValueError):
            dsa.DSAPrivateKey(
                modulus=2 ** 3000,
                subgroup_order=int(self._parameters_3072['q'], 16),
                generator=int(self._parameters_3072['g'], 16),
                x=int(self._parameters_3072['x'], 16),
                y=int(self._parameters_3072['y'], 16)
            )

        # Test a modulus > 3072 bits in length
        with pytest.raises(ValueError):
            dsa.DSAPrivateKey(
                modulus=2 ** 3100,
                subgroup_order=int(self._parameters_3072['q'], 16),
                generator=int(self._parameters_3072['g'], 16),
                x=int(self._parameters_3072['x'], 16),
                y=int(self._parameters_3072['y'], 16)
            )

        # Test a subgroup_order < 160 bits in length
        with pytest.raises(ValueError):
            dsa.DSAPrivateKey(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=2 ** 150,
                generator=int(self._parameters_1024['g'], 16),
                x=int(self._parameters_1024['x'], 16),
                y=int(self._parameters_1024['y'], 16)
            )

        # Test a subgroup_order < 256 bits in length
        with pytest.raises(ValueError):
            dsa.DSAPrivateKey(
                modulus=int(self._parameters_2048['p'], 16),
                subgroup_order=2 ** 250,
                generator=int(self._parameters_2048['g'], 16),
                x=int(self._parameters_2048['x'], 16),
                y=int(self._parameters_2048['y'], 16)
            )

        # Test a subgroup_order > 256 bits in length
        with pytest.raises(ValueError):
            dsa.DSAPrivateKey(
                modulus=int(self._parameters_3072['p'], 16),
                subgroup_order=2 ** 260,
                generator=int(self._parameters_3072['g'], 16),
                x=int(self._parameters_3072['x'], 16),
                y=int(self._parameters_3072['y'], 16)
            )

        # Test a modulus, subgroup_order pair of (1024, 256) bit lengths
        with pytest.raises(ValueError):
            dsa.DSAPrivateKey(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=int(self._parameters_2048['q'], 16),
                generator=int(self._parameters_1024['g'], 16),
                x=int(self._parameters_1024['x'], 16),
                y=int(self._parameters_1024['y'], 16)
            )

        # Test a modulus, subgroup_order pair of (2048, 160) bit lengths
        with pytest.raises(ValueError):
            dsa.DSAPrivateKey(
                modulus=int(self._parameters_2048['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=int(self._parameters_2048['g'], 16),
                x=int(self._parameters_2048['x'], 16),
                y=int(self._parameters_2048['y'], 16)
            )

        # Test a modulus, subgroup_order pair of (3072, 160) bit lengths
        with pytest.raises(ValueError):
            dsa.DSAPrivateKey(
                modulus=int(self._parameters_3072['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=int(self._parameters_3072['g'], 16),
                x=int(self._parameters_3072['x'], 16),
                y=int(self._parameters_3072['y'], 16)
            )

        # Test a generator < 1
        with pytest.raises(ValueError):
            dsa.DSAPrivateKey(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=0,
                x=int(self._parameters_1024['x'], 16),
                y=int(self._parameters_1024['y'], 16)
            )

        # Test a generator = 1
        with pytest.raises(ValueError):
            dsa.DSAPrivateKey(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=1,
                x=int(self._parameters_1024['x'], 16),
                y=int(self._parameters_1024['y'], 16)
            )

        # Test a generator > modulus
        with pytest.raises(ValueError):
            dsa.DSAPrivateKey(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=2 ** 1200,
                x=int(self._parameters_1024['x'], 16),
                y=int(self._parameters_1024['y'], 16)
            )

        # Test x = 0
        with pytest.raises(ValueError):
            dsa.DSAPrivateKey(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=int(self._parameters_1024['g'], 16),
                x=0,
                y=int(self._parameters_1024['y'], 16)
            )

        # Test x < 0
        with pytest.raises(ValueError):
            dsa.DSAPrivateKey(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=int(self._parameters_1024['g'], 16),
                x=-2,
                y=int(self._parameters_1024['y'], 16)
            )

        # Test x = subgroup_order
        with pytest.raises(ValueError):
            dsa.DSAPrivateKey(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=int(self._parameters_1024['g'], 16),
                x=2 ** 159,
                y=int(self._parameters_1024['y'], 16)
            )

        # Test x > subgroup_order
        with pytest.raises(ValueError):
            dsa.DSAPrivateKey(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=int(self._parameters_1024['g'], 16),
                x=2 ** 200,
                y=int(self._parameters_1024['y'], 16)
            )

        # Test y != (generator ** x) % modulus
        with pytest.raises(ValueError):
            dsa.DSAPrivateKey(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=int(self._parameters_1024['g'], 16),
                x=int(self._parameters_1024['x'], 16),
                y=2 ** 100
            )

        # Test a non-integer y value
        with pytest.raises(TypeError):
            dsa.DSAPrivateKey(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=int(self._parameters_1024['g'], 16),
                x=int(self._parameters_1024['x'], 16),
                y=None
            )

        # Test a non-integer x value
        with pytest.raises(TypeError):
            dsa.DSAPrivateKey(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=int(self._parameters_1024['g'], 16),
                x=None,
                y=int(self._parameters_1024['x'], 16)
            )

    def test_invalid_dsa_public_key_arguments(self):
        # Test a modulus < 1024 bits in length
        with pytest.raises(ValueError):
            dsa.DSAPublicKey(
                modulus=2 ** 1000,
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=int(self._parameters_1024['g'], 16),
                y=int(self._parameters_1024['y'], 16)
            )

        # Test a modulus < 2048 bits in length
        with pytest.raises(ValueError):
            dsa.DSAPublicKey(
                modulus=2 ** 2000,
                subgroup_order=int(self._parameters_2048['q'], 16),
                generator=int(self._parameters_2048['g'], 16),
                y=int(self._parameters_2048['y'], 16)
            )

        # Test a modulus < 3072 bits in length
        with pytest.raises(ValueError):
            dsa.DSAPublicKey(
                modulus=2 ** 3000,
                subgroup_order=int(self._parameters_3072['q'], 16),
                generator=int(self._parameters_3072['g'], 16),
                y=int(self._parameters_3072['y'], 16)
            )

        # Test a modulus > 3072 bits in length
        with pytest.raises(ValueError):
            dsa.DSAPublicKey(
                modulus=2 ** 3100,
                subgroup_order=int(self._parameters_3072['q'], 16),
                generator=int(self._parameters_3072['g'], 16),
                y=int(self._parameters_3072['y'], 16)
            )

        # Test a subgroup_order < 160 bits in length
        with pytest.raises(ValueError):
            dsa.DSAPublicKey(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=2 ** 150,
                generator=int(self._parameters_1024['g'], 16),
                y=int(self._parameters_1024['y'], 16)
            )

        # Test a subgroup_order < 256 bits in length
        with pytest.raises(ValueError):
            dsa.DSAPublicKey(
                modulus=int(self._parameters_2048['p'], 16),
                subgroup_order=2 ** 250,
                generator=int(self._parameters_2048['g'], 16),
                y=int(self._parameters_2048['y'], 16)
            )

        # Test a subgroup_order > 256 bits in length
        with pytest.raises(ValueError):
            dsa.DSAPublicKey(
                modulus=int(self._parameters_3072['p'], 16),
                subgroup_order=2 ** 260,
                generator=int(self._parameters_3072['g'], 16),
                y=int(self._parameters_3072['y'], 16)
            )

        # Test a modulus, subgroup_order pair of (1024, 256) bit lengths
        with pytest.raises(ValueError):
            dsa.DSAPublicKey(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=int(self._parameters_2048['q'], 16),
                generator=int(self._parameters_1024['g'], 16),
                y=int(self._parameters_1024['y'], 16)
            )

        # Test a modulus, subgroup_order pair of (2048, 160) bit lengths
        with pytest.raises(ValueError):
            dsa.DSAPublicKey(
                modulus=int(self._parameters_2048['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=int(self._parameters_2048['g'], 16),
                y=int(self._parameters_2048['y'], 16)
            )

        # Test a modulus, subgroup_order pair of (3072, 160) bit lengths
        with pytest.raises(ValueError):
            dsa.DSAPublicKey(
                modulus=int(self._parameters_3072['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=int(self._parameters_3072['g'], 16),
                y=int(self._parameters_3072['y'], 16)
            )

        # Test a generator < 1
        with pytest.raises(ValueError):
            dsa.DSAPublicKey(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=0,
                y=int(self._parameters_1024['y'], 16)
            )

        # Test a generator = 1
        with pytest.raises(ValueError):
            dsa.DSAPublicKey(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=1,
                y=int(self._parameters_1024['y'], 16)
            )

        # Test a generator > modulus
        with pytest.raises(ValueError):
            dsa.DSAPublicKey(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=2 ** 1200,
                y=int(self._parameters_1024['y'], 16)
            )

        # Test a non-integer y value
        with pytest.raises(TypeError):
            dsa.DSAPublicKey(
                modulus=int(self._parameters_1024['p'], 16),
                subgroup_order=int(self._parameters_1024['q'], 16),
                generator=int(self._parameters_1024['g'], 16),
                y=None
            )


@pytest.mark.dsa
class TestDSAVerification(object):
    _algorithms_dict = {
        'SHA1': hashes.SHA1,
        'SHA224': hashes.SHA224,
        'SHA256': hashes.SHA256,
        'SHA384': hashes.SHA384,
        'SHA512': hashes.SHA512
    }

    @pytest.mark.parametrize(
        "vector",
        load_vectors_from_file(
            os.path.join(
                "asymmetric", "DSA", "FIPS_186-3", "SigVer.rsp"),
            load_fips_dsa_sig_vectors
        )
    )
    def test_dsa_verification(self, vector, backend):
        digest_algorithm = vector['digest_algorithm'].replace("-", "")
        algorithm = self._algorithms_dict[digest_algorithm]
        if (
            not backend.dsa_parameters_supported(
                vector['p'], vector['q'], vector['g']
            ) or not backend.dsa_hash_supported(algorithm)
        ):
            pytest.skip(
                "{0} does not support the provided parameters".format(backend)
            )

        public_key = dsa.DSAPublicKey(
            vector['p'], vector['q'], vector['g'], vector['y']
        )
        sig = der_encode_dsa_signature(vector['r'], vector['s'])
        verifier = public_key.verifier(sig, algorithm(), backend)
        verifier.update(vector['msg'])
        if vector['result'] == "F":
            with pytest.raises(InvalidSignature):
                verifier.verify()
        else:
            verifier.verify()

    def test_dsa_verify_invalid_asn1(self, backend):
        parameters = dsa.DSAParameters.generate(1024, backend)
        private_key = dsa.DSAPrivateKey.generate(parameters, backend)
        public_key = private_key.public_key()
        verifier = public_key.verifier(b'fakesig', hashes.SHA1(), backend)
        verifier.update(b'fakesig')
        with pytest.raises(InvalidSignature):
            verifier.verify()

    def test_use_after_finalize(self, backend):
        parameters = dsa.DSAParameters.generate(1024, backend)
        private_key = dsa.DSAPrivateKey.generate(parameters, backend)
        public_key = private_key.public_key()
        verifier = public_key.verifier(b'fakesig', hashes.SHA1(), backend)
        verifier.update(b'irrelevant')
        with pytest.raises(InvalidSignature):
            verifier.verify()
        with pytest.raises(AlreadyFinalized):
            verifier.verify()
        with pytest.raises(AlreadyFinalized):
            verifier.update(b"more data")

    def test_dsa_verifier_invalid_backend(self, backend):
        pretend_backend = object()
        params = dsa.DSAParameters.generate(1024, backend)
        private_key = dsa.DSAPrivateKey.generate(params, backend)
        public_key = private_key.public_key()

        with raises_unsupported_algorithm(
                _Reasons.BACKEND_MISSING_INTERFACE):
            public_key.verifier(b"sig", hashes.SHA1(), pretend_backend)


@pytest.mark.dsa
class TestDSASignature(object):
    _algorithms_dict = {
        'SHA1': hashes.SHA1,
        'SHA224': hashes.SHA224,
        'SHA256': hashes.SHA256,
        'SHA384': hashes.SHA384,
        'SHA512': hashes.SHA512}

    @pytest.mark.parametrize(
        "vector",
        load_vectors_from_file(
            os.path.join(
                "asymmetric", "DSA", "FIPS_186-3", "SigGen.txt"),
            load_fips_dsa_sig_vectors
        )
    )
    def test_dsa_signing(self, vector, backend):
        digest_algorithm = vector['digest_algorithm'].replace("-", "")
        algorithm = self._algorithms_dict[digest_algorithm]
        if (
            not backend.dsa_parameters_supported(
                vector['p'], vector['q'], vector['g']
            ) or not backend.dsa_hash_supported(algorithm)
        ):
            pytest.skip(
                "{0} does not support the provided parameters".format(backend)
            )

        private_key = dsa.DSAPrivateKey(
            vector['p'], vector['q'], vector['g'], vector['x'], vector['y']
        )
        signer = private_key.signer(algorithm(), backend)
        signer.update(vector['msg'])
        signature = signer.finalize()
        assert signature

        public_key = private_key.public_key()
        verifier = public_key.verifier(signature, algorithm(), backend)
        verifier.update(vector['msg'])
        verifier.verify()

    def test_use_after_finalize(self, backend):
        parameters = dsa.DSAParameters.generate(1024, backend)
        private_key = dsa.DSAPrivateKey.generate(parameters, backend)
        signer = private_key.signer(hashes.SHA1(), backend)
        signer.update(b"data")
        signer.finalize()
        with pytest.raises(AlreadyFinalized):
            signer.finalize()
        with pytest.raises(AlreadyFinalized):
            signer.update(b"more data")

    def test_dsa_signer_invalid_backend(self, backend):
        pretend_backend = object()
        params = dsa.DSAParameters.generate(1024, backend)
        private_key = dsa.DSAPrivateKey.generate(params, backend)

        with raises_unsupported_algorithm(
                _Reasons.BACKEND_MISSING_INTERFACE):
            private_key.signer(hashes.SHA1(), pretend_backend)


def test_dsa_generate_invalid_backend():
    pretend_backend = object()

    with raises_unsupported_algorithm(
            _Reasons.BACKEND_MISSING_INTERFACE):
        dsa.DSAParameters.generate(1024, pretend_backend)

    pretend_parameters = object()
    with raises_unsupported_algorithm(
            _Reasons.BACKEND_MISSING_INTERFACE):
        dsa.DSAPrivateKey.generate(pretend_parameters, pretend_backend)

########NEW FILE########
__FILENAME__ = test_hashes
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import pretend

import pytest

import six

from cryptography import utils
from cryptography.exceptions import (
    AlreadyFinalized, _Reasons
)
from cryptography.hazmat.backends.interfaces import HashBackend
from cryptography.hazmat.primitives import hashes, interfaces

from .utils import generate_base_hash_test
from ...utils import raises_unsupported_algorithm


@utils.register_interface(interfaces.HashAlgorithm)
class UnsupportedDummyHash(object):
    name = "unsupported-dummy-hash"


@pytest.mark.hash
class TestHashContext(object):
    def test_hash_reject_unicode(self, backend):
        m = hashes.Hash(hashes.SHA1(), backend=backend)
        with pytest.raises(TypeError):
            m.update(six.u("\u00FC"))

    def test_copy_backend_object(self):
        @utils.register_interface(HashBackend)
        class PretendBackend(object):
            pass

        pretend_backend = PretendBackend()
        copied_ctx = pretend.stub()
        pretend_ctx = pretend.stub(copy=lambda: copied_ctx)
        h = hashes.Hash(hashes.SHA1(), backend=pretend_backend,
                        ctx=pretend_ctx)
        assert h._backend is pretend_backend
        assert h.copy()._backend is h._backend

    def test_hash_algorithm_instance(self, backend):
        with pytest.raises(TypeError):
            hashes.Hash(hashes.SHA1, backend=backend)

    def test_raises_after_finalize(self, backend):
        h = hashes.Hash(hashes.SHA1(), backend=backend)
        h.finalize()

        with pytest.raises(AlreadyFinalized):
            h.update(b"foo")

        with pytest.raises(AlreadyFinalized):
            h.copy()

        with pytest.raises(AlreadyFinalized):
            h.finalize()

    def test_unsupported_hash(self, backend):
        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_HASH):
            hashes.Hash(UnsupportedDummyHash(), backend)


@pytest.mark.supported(
    only_if=lambda backend: backend.hash_supported(hashes.SHA1()),
    skip_message="Does not support SHA1",
)
@pytest.mark.hash
class TestSHA1(object):
    test_SHA1 = generate_base_hash_test(
        hashes.SHA1(),
        digest_size=20,
        block_size=64,
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.hash_supported(hashes.SHA224()),
    skip_message="Does not support SHA224",
)
@pytest.mark.hash
class TestSHA224(object):
    test_SHA224 = generate_base_hash_test(
        hashes.SHA224(),
        digest_size=28,
        block_size=64,
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.hash_supported(hashes.SHA256()),
    skip_message="Does not support SHA256",
)
@pytest.mark.hash
class TestSHA256(object):
    test_SHA256 = generate_base_hash_test(
        hashes.SHA256(),
        digest_size=32,
        block_size=64,
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.hash_supported(hashes.SHA384()),
    skip_message="Does not support SHA384",
)
@pytest.mark.hash
class TestSHA384(object):
    test_SHA384 = generate_base_hash_test(
        hashes.SHA384(),
        digest_size=48,
        block_size=128,
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.hash_supported(hashes.SHA512()),
    skip_message="Does not support SHA512",
)
@pytest.mark.hash
class TestSHA512(object):
    test_SHA512 = generate_base_hash_test(
        hashes.SHA512(),
        digest_size=64,
        block_size=128,
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.hash_supported(hashes.RIPEMD160()),
    skip_message="Does not support RIPEMD160",
)
@pytest.mark.hash
class TestRIPEMD160(object):
    test_RIPEMD160 = generate_base_hash_test(
        hashes.RIPEMD160(),
        digest_size=20,
        block_size=64,
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.hash_supported(hashes.Whirlpool()),
    skip_message="Does not support Whirlpool",
)
@pytest.mark.hash
class TestWhirlpool(object):
    test_Whirlpool = generate_base_hash_test(
        hashes.Whirlpool(),
        digest_size=64,
        block_size=64,
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.hash_supported(hashes.MD5()),
    skip_message="Does not support MD5",
)
@pytest.mark.hash
class TestMD5(object):
    test_MD5 = generate_base_hash_test(
        hashes.MD5(),
        digest_size=16,
        block_size=64,
    )


def test_invalid_backend():
    pretend_backend = object()

    with raises_unsupported_algorithm(_Reasons.BACKEND_MISSING_INTERFACE):
        hashes.Hash(hashes.SHA1(), pretend_backend)

########NEW FILE########
__FILENAME__ = test_hash_vectors
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import os

import pytest

from cryptography.hazmat.primitives import hashes

from .utils import generate_hash_test, generate_long_string_hash_test
from ...utils import load_hash_vectors


@pytest.mark.supported(
    only_if=lambda backend: backend.hash_supported(hashes.SHA1()),
    skip_message="Does not support SHA1",
)
@pytest.mark.hash
class TestSHA1(object):
    test_SHA1 = generate_hash_test(
        load_hash_vectors,
        os.path.join("hashes", "SHA1"),
        [
            "SHA1LongMsg.rsp",
            "SHA1ShortMsg.rsp",
        ],
        hashes.SHA1(),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.hash_supported(hashes.SHA224()),
    skip_message="Does not support SHA224",
)
@pytest.mark.hash
class TestSHA224(object):
    test_SHA224 = generate_hash_test(
        load_hash_vectors,
        os.path.join("hashes", "SHA2"),
        [
            "SHA224LongMsg.rsp",
            "SHA224ShortMsg.rsp",
        ],
        hashes.SHA224(),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.hash_supported(hashes.SHA256()),
    skip_message="Does not support SHA256",
)
@pytest.mark.hash
class TestSHA256(object):
    test_SHA256 = generate_hash_test(
        load_hash_vectors,
        os.path.join("hashes", "SHA2"),
        [
            "SHA256LongMsg.rsp",
            "SHA256ShortMsg.rsp",
        ],
        hashes.SHA256(),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.hash_supported(hashes.SHA384()),
    skip_message="Does not support SHA384",
)
@pytest.mark.hash
class TestSHA384(object):
    test_SHA384 = generate_hash_test(
        load_hash_vectors,
        os.path.join("hashes", "SHA2"),
        [
            "SHA384LongMsg.rsp",
            "SHA384ShortMsg.rsp",
        ],
        hashes.SHA384(),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.hash_supported(hashes.SHA512()),
    skip_message="Does not support SHA512",
)
@pytest.mark.hash
class TestSHA512(object):
    test_SHA512 = generate_hash_test(
        load_hash_vectors,
        os.path.join("hashes", "SHA2"),
        [
            "SHA512LongMsg.rsp",
            "SHA512ShortMsg.rsp",
        ],
        hashes.SHA512(),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.hash_supported(hashes.RIPEMD160()),
    skip_message="Does not support RIPEMD160",
)
@pytest.mark.hash
class TestRIPEMD160(object):
    test_RIPEMD160 = generate_hash_test(
        load_hash_vectors,
        os.path.join("hashes", "ripemd160"),
        [
            "ripevectors.txt",
        ],
        hashes.RIPEMD160(),
    )

    test_RIPEMD160_long_string = generate_long_string_hash_test(
        hashes.RIPEMD160(),
        "52783243c1697bdbe16d37f97f68f08325dc1528",
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.hash_supported(hashes.Whirlpool()),
    skip_message="Does not support Whirlpool",
)
@pytest.mark.hash
class TestWhirlpool(object):
    test_whirlpool = generate_hash_test(
        load_hash_vectors,
        os.path.join("hashes", "whirlpool"),
        [
            "iso-test-vectors.txt",
        ],
        hashes.Whirlpool(),
    )

    test_whirlpool_long_string = generate_long_string_hash_test(
        hashes.Whirlpool(),
        ("0c99005beb57eff50a7cf005560ddf5d29057fd86b2"
         "0bfd62deca0f1ccea4af51fc15490eddc47af32bb2b"
         "66c34ff9ad8c6008ad677f77126953b226e4ed8b01"),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.hash_supported(hashes.MD5()),
    skip_message="Does not support MD5",
)
@pytest.mark.hash
class TestMD5(object):
    test_md5 = generate_hash_test(
        load_hash_vectors,
        os.path.join("hashes", "MD5"),
        [
            "rfc-1321.txt",
        ],
        hashes.MD5(),
    )

########NEW FILE########
__FILENAME__ = test_hkdf
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import binascii

import pytest

import six

from cryptography.exceptions import (
    AlreadyFinalized, InvalidKey, _Reasons
)
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF, HKDFExpand

from ...utils import raises_unsupported_algorithm


@pytest.mark.hmac
class TestHKDF(object):
    def test_length_limit(self, backend):
        big_length = 255 * (hashes.SHA256().digest_size // 8) + 1

        with pytest.raises(ValueError):
            HKDF(
                hashes.SHA256(),
                big_length,
                salt=None,
                info=None,
                backend=backend
            )

    def test_already_finalized(self, backend):
        hkdf = HKDF(
            hashes.SHA256(),
            16,
            salt=None,
            info=None,
            backend=backend
        )

        hkdf.derive(b"\x01" * 16)

        with pytest.raises(AlreadyFinalized):
            hkdf.derive(b"\x02" * 16)

        hkdf = HKDF(
            hashes.SHA256(),
            16,
            salt=None,
            info=None,
            backend=backend
        )

        hkdf.verify(b"\x01" * 16, b"gJ\xfb{\xb1Oi\xc5sMC\xb7\xe4@\xf7u")

        with pytest.raises(AlreadyFinalized):
            hkdf.verify(b"\x02" * 16, b"gJ\xfb{\xb1Oi\xc5sMC\xb7\xe4@\xf7u")

        hkdf = HKDF(
            hashes.SHA256(),
            16,
            salt=None,
            info=None,
            backend=backend
        )

    def test_verify(self, backend):
        hkdf = HKDF(
            hashes.SHA256(),
            16,
            salt=None,
            info=None,
            backend=backend
        )

        hkdf.verify(b"\x01" * 16, b"gJ\xfb{\xb1Oi\xc5sMC\xb7\xe4@\xf7u")

    def test_verify_invalid(self, backend):
        hkdf = HKDF(
            hashes.SHA256(),
            16,
            salt=None,
            info=None,
            backend=backend
        )

        with pytest.raises(InvalidKey):
            hkdf.verify(b"\x02" * 16, b"gJ\xfb{\xb1Oi\xc5sMC\xb7\xe4@\xf7u")

    def test_unicode_typeerror(self, backend):
        with pytest.raises(TypeError):
            HKDF(
                hashes.SHA256(),
                16,
                salt=six.u("foo"),
                info=None,
                backend=backend
            )

        with pytest.raises(TypeError):
            HKDF(
                hashes.SHA256(),
                16,
                salt=None,
                info=six.u("foo"),
                backend=backend
            )

        with pytest.raises(TypeError):
            hkdf = HKDF(
                hashes.SHA256(),
                16,
                salt=None,
                info=None,
                backend=backend
            )

            hkdf.derive(six.u("foo"))

        with pytest.raises(TypeError):
            hkdf = HKDF(
                hashes.SHA256(),
                16,
                salt=None,
                info=None,
                backend=backend
            )

            hkdf.verify(six.u("foo"), b"bar")

        with pytest.raises(TypeError):
            hkdf = HKDF(
                hashes.SHA256(),
                16,
                salt=None,
                info=None,
                backend=backend
            )

            hkdf.verify(b"foo", six.u("bar"))


@pytest.mark.hmac
class TestHKDFExpand(object):
    def test_derive(self, backend):
        prk = binascii.unhexlify(
            b"077709362c2e32df0ddc3f0dc47bba6390b6c73bb50f9c3122ec844ad7c2b3e5"
        )

        okm = (b"3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c"
               b"5bf34007208d5b887185865")

        info = binascii.unhexlify(b"f0f1f2f3f4f5f6f7f8f9")
        hkdf = HKDFExpand(hashes.SHA256(), 42, info, backend)

        assert binascii.hexlify(hkdf.derive(prk)) == okm

    def test_verify(self, backend):
        prk = binascii.unhexlify(
            b"077709362c2e32df0ddc3f0dc47bba6390b6c73bb50f9c3122ec844ad7c2b3e5"
        )

        okm = (b"3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c"
               b"5bf34007208d5b887185865")

        info = binascii.unhexlify(b"f0f1f2f3f4f5f6f7f8f9")
        hkdf = HKDFExpand(hashes.SHA256(), 42, info, backend)

        assert hkdf.verify(prk, binascii.unhexlify(okm)) is None

    def test_invalid_verify(self, backend):
        prk = binascii.unhexlify(
            b"077709362c2e32df0ddc3f0dc47bba6390b6c73bb50f9c3122ec844ad7c2b3e5"
        )

        info = binascii.unhexlify(b"f0f1f2f3f4f5f6f7f8f9")
        hkdf = HKDFExpand(hashes.SHA256(), 42, info, backend)

        with pytest.raises(InvalidKey):
            hkdf.verify(prk, b"wrong key")

    def test_already_finalized(self, backend):
        info = binascii.unhexlify(b"f0f1f2f3f4f5f6f7f8f9")
        hkdf = HKDFExpand(hashes.SHA256(), 42, info, backend)

        hkdf.derive(b"first")

        with pytest.raises(AlreadyFinalized):
            hkdf.derive(b"second")

    def test_unicode_error(self, backend):
        info = binascii.unhexlify(b"f0f1f2f3f4f5f6f7f8f9")
        hkdf = HKDFExpand(hashes.SHA256(), 42, info, backend)

        with pytest.raises(TypeError):
            hkdf.derive(six.u("first"))


def test_invalid_backend():
    pretend_backend = object()

    with raises_unsupported_algorithm(_Reasons.BACKEND_MISSING_INTERFACE):
        HKDF(hashes.SHA256(), 16, None, None, pretend_backend)

    with raises_unsupported_algorithm(_Reasons.BACKEND_MISSING_INTERFACE):
        HKDFExpand(hashes.SHA256(), 16, None, pretend_backend)

########NEW FILE########
__FILENAME__ = test_hkdf_vectors
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import os

import pytest

from cryptography.hazmat.primitives import hashes

from .utils import generate_hkdf_test
from ...utils import load_nist_vectors


@pytest.mark.supported(
    only_if=lambda backend: backend.hmac_supported(hashes.SHA1()),
    skip_message="Does not support SHA1."
)
@pytest.mark.hmac
class TestHKDFSHA1(object):
    test_HKDFSHA1 = generate_hkdf_test(
        load_nist_vectors,
        os.path.join("KDF"),
        ["rfc-5869-HKDF-SHA1.txt"],
        hashes.SHA1()
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.hmac_supported(hashes.SHA256()),
    skip_message="Does not support SHA256."
)
@pytest.mark.hmac
class TestHKDFSHA256(object):
    test_HKDFSHA1 = generate_hkdf_test(
        load_nist_vectors,
        os.path.join("KDF"),
        ["rfc-5869-HKDF-SHA256.txt"],
        hashes.SHA256()
    )

########NEW FILE########
__FILENAME__ = test_hmac
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import pretend

import pytest

import six

from cryptography import utils
from cryptography.exceptions import (
    AlreadyFinalized, InvalidSignature, _Reasons
)
from cryptography.hazmat.backends.interfaces import HMACBackend
from cryptography.hazmat.primitives import hashes, hmac, interfaces

from .utils import generate_base_hmac_test
from ...utils import raises_unsupported_algorithm


@utils.register_interface(interfaces.HashAlgorithm)
class UnsupportedDummyHash(object):
        name = "unsupported-dummy-hash"


@pytest.mark.supported(
    only_if=lambda backend: backend.hmac_supported(hashes.MD5()),
    skip_message="Does not support MD5",
)
@pytest.mark.hmac
class TestHMACCopy(object):
    test_copy = generate_base_hmac_test(
        hashes.MD5(),
    )


@pytest.mark.hmac
class TestHMAC(object):
    def test_hmac_reject_unicode(self, backend):
        h = hmac.HMAC(b"mykey", hashes.SHA1(), backend=backend)
        with pytest.raises(TypeError):
            h.update(six.u("\u00FC"))

    def test_copy_backend_object(self):
        @utils.register_interface(HMACBackend)
        class PretendBackend(object):
            pass

        pretend_backend = PretendBackend()
        copied_ctx = pretend.stub()
        pretend_ctx = pretend.stub(copy=lambda: copied_ctx)
        h = hmac.HMAC(b"key", hashes.SHA1(), backend=pretend_backend,
                      ctx=pretend_ctx)
        assert h._backend is pretend_backend
        assert h.copy()._backend is pretend_backend

    def test_hmac_algorithm_instance(self, backend):
        with pytest.raises(TypeError):
            hmac.HMAC(b"key", hashes.SHA1, backend=backend)

    def test_raises_after_finalize(self, backend):
        h = hmac.HMAC(b"key", hashes.SHA1(), backend=backend)
        h.finalize()

        with pytest.raises(AlreadyFinalized):
            h.update(b"foo")

        with pytest.raises(AlreadyFinalized):
            h.copy()

        with pytest.raises(AlreadyFinalized):
            h.finalize()

    def test_verify(self, backend):
        h = hmac.HMAC(b'', hashes.SHA1(), backend=backend)
        digest = h.finalize()

        h = hmac.HMAC(b'', hashes.SHA1(), backend=backend)
        h.verify(digest)

        with pytest.raises(AlreadyFinalized):
            h.verify(b'')

    def test_invalid_verify(self, backend):
        h = hmac.HMAC(b'', hashes.SHA1(), backend=backend)
        with pytest.raises(InvalidSignature):
            h.verify(b'')

        with pytest.raises(AlreadyFinalized):
            h.verify(b'')

    def test_verify_reject_unicode(self, backend):
        h = hmac.HMAC(b'', hashes.SHA1(), backend=backend)
        with pytest.raises(TypeError):
            h.verify(six.u(''))

    def test_unsupported_hash(self, backend):
        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_HASH):
            hmac.HMAC(b"key", UnsupportedDummyHash(), backend)


def test_invalid_backend():
    pretend_backend = object()

    with raises_unsupported_algorithm(_Reasons.BACKEND_MISSING_INTERFACE):
        hmac.HMAC(b"key", hashes.SHA1(), pretend_backend)

########NEW FILE########
__FILENAME__ = test_hmac_vectors
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import pytest

from cryptography.hazmat.primitives import hashes

from .utils import generate_hmac_test
from ...utils import load_hash_vectors


@pytest.mark.supported(
    only_if=lambda backend: backend.hmac_supported(hashes.MD5()),
    skip_message="Does not support MD5",
)
@pytest.mark.hmac
class TestHMACMD5(object):
    test_hmac_md5 = generate_hmac_test(
        load_hash_vectors,
        "HMAC",
        [
            "rfc-2202-md5.txt",
        ],
        hashes.MD5(),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.hmac_supported(hashes.SHA1()),
    skip_message="Does not support SHA1",
)
@pytest.mark.hmac
class TestHMACSHA1(object):
    test_hmac_sha1 = generate_hmac_test(
        load_hash_vectors,
        "HMAC",
        [
            "rfc-2202-sha1.txt",
        ],
        hashes.SHA1(),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.hmac_supported(hashes.SHA224()),
    skip_message="Does not support SHA224",
)
@pytest.mark.hmac
class TestHMACSHA224(object):
    test_hmac_sha224 = generate_hmac_test(
        load_hash_vectors,
        "HMAC",
        [
            "rfc-4231-sha224.txt",
        ],
        hashes.SHA224(),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.hmac_supported(hashes.SHA256()),
    skip_message="Does not support SHA256",
)
@pytest.mark.hmac
class TestHMACSHA256(object):
    test_hmac_sha256 = generate_hmac_test(
        load_hash_vectors,
        "HMAC",
        [
            "rfc-4231-sha256.txt",
        ],
        hashes.SHA256(),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.hmac_supported(hashes.SHA384()),
    skip_message="Does not support SHA384",
)
@pytest.mark.hmac
class TestHMACSHA384(object):
    test_hmac_sha384 = generate_hmac_test(
        load_hash_vectors,
        "HMAC",
        [
            "rfc-4231-sha384.txt",
        ],
        hashes.SHA384(),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.hmac_supported(hashes.SHA512()),
    skip_message="Does not support SHA512",
)
@pytest.mark.hmac
class TestHMACSHA512(object):
    test_hmac_sha512 = generate_hmac_test(
        load_hash_vectors,
        "HMAC",
        [
            "rfc-4231-sha512.txt",
        ],
        hashes.SHA512(),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.hmac_supported(hashes.RIPEMD160()),
    skip_message="Does not support RIPEMD160",
)
@pytest.mark.hmac
class TestHMACRIPEMD160(object):
    test_hmac_ripemd160 = generate_hmac_test(
        load_hash_vectors,
        "HMAC",
        [
            "rfc-2286-ripemd160.txt",
        ],
        hashes.RIPEMD160(),
    )

########NEW FILE########
__FILENAME__ = test_idea
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import binascii
import os

import pytest

from cryptography.hazmat.primitives.ciphers import algorithms, modes

from .utils import generate_encrypt_test
from ...utils import load_nist_vectors


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.IDEA("\x00" * 16), modes.ECB()
    ),
    skip_message="Does not support IDEA ECB",
)
@pytest.mark.cipher
class TestIDEAModeECB(object):
    test_ECB = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "IDEA"),
        ["idea-ecb.txt"],
        lambda key, **kwargs: algorithms.IDEA(binascii.unhexlify((key))),
        lambda **kwargs: modes.ECB(),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.IDEA("\x00" * 16), modes.CBC("\x00" * 8)
    ),
    skip_message="Does not support IDEA CBC",
)
@pytest.mark.cipher
class TestIDEAModeCBC(object):
    test_CBC = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "IDEA"),
        ["idea-cbc.txt"],
        lambda key, **kwargs: algorithms.IDEA(binascii.unhexlify((key))),
        lambda iv, **kwargs: modes.CBC(binascii.unhexlify(iv))
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.IDEA("\x00" * 16), modes.OFB("\x00" * 8)
    ),
    skip_message="Does not support IDEA OFB",
)
@pytest.mark.cipher
class TestIDEAModeOFB(object):
    test_OFB = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "IDEA"),
        ["idea-ofb.txt"],
        lambda key, **kwargs: algorithms.IDEA(binascii.unhexlify((key))),
        lambda iv, **kwargs: modes.OFB(binascii.unhexlify(iv))
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.IDEA("\x00" * 16), modes.CFB("\x00" * 8)
    ),
    skip_message="Does not support IDEA CFB",
)
@pytest.mark.cipher
class TestIDEAModeCFB(object):
    test_CFB = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "IDEA"),
        ["idea-cfb.txt"],
        lambda key, **kwargs: algorithms.IDEA(binascii.unhexlify((key))),
        lambda iv, **kwargs: modes.CFB(binascii.unhexlify(iv))
    )

########NEW FILE########
__FILENAME__ = test_padding
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import pytest

import six

from cryptography.exceptions import AlreadyFinalized
from cryptography.hazmat.primitives import padding


class TestPKCS7(object):
    @pytest.mark.parametrize("size", [127, 4096, -2])
    def test_invalid_block_size(self, size):
        with pytest.raises(ValueError):
            padding.PKCS7(size)

    @pytest.mark.parametrize(("size", "padded"), [
        (128, b"1111"),
        (128, b"1111111111111111"),
        (128, b"111111111111111\x06"),
        (128, b""),
        (128, b"\x06" * 6),
        (128, b"\x00" * 16),
    ])
    def test_invalid_padding(self, size, padded):
        unpadder = padding.PKCS7(size).unpadder()
        with pytest.raises(ValueError):
            unpadder.update(padded)
            unpadder.finalize()

    def test_non_bytes(self):
        padder = padding.PKCS7(128).padder()
        with pytest.raises(TypeError):
            padder.update(six.u("abc"))
        unpadder = padding.PKCS7(128).unpadder()
        with pytest.raises(TypeError):
            unpadder.update(six.u("abc"))

    @pytest.mark.parametrize(("size", "unpadded", "padded"), [
        (
            128,
            b"1111111111",
            b"1111111111\x06\x06\x06\x06\x06\x06",
        ),
        (
            128,
            b"111111111111111122222222222222",
            b"111111111111111122222222222222\x02\x02",
        ),
        (
            128,
            b"1" * 16,
            b"1" * 16 + b"\x10" * 16,
        ),
        (
            128,
            b"1" * 17,
            b"1" * 17 + b"\x0F" * 15,
        )
    ])
    def test_pad(self, size, unpadded, padded):
        padder = padding.PKCS7(size).padder()
        result = padder.update(unpadded)
        result += padder.finalize()
        assert result == padded

    @pytest.mark.parametrize(("size", "unpadded", "padded"), [
        (
            128,
            b"1111111111",
            b"1111111111\x06\x06\x06\x06\x06\x06",
        ),
        (
            128,
            b"111111111111111122222222222222",
            b"111111111111111122222222222222\x02\x02",
        ),
    ])
    def test_unpad(self, size, unpadded, padded):
        unpadder = padding.PKCS7(size).unpadder()
        result = unpadder.update(padded)
        result += unpadder.finalize()
        assert result == unpadded

    def test_use_after_finalize(self):
        padder = padding.PKCS7(128).padder()
        b = padder.finalize()
        with pytest.raises(AlreadyFinalized):
            padder.update(b"")
        with pytest.raises(AlreadyFinalized):
            padder.finalize()

        unpadder = padding.PKCS7(128).unpadder()
        unpadder.update(b)
        unpadder.finalize()
        with pytest.raises(AlreadyFinalized):
            unpadder.update(b"")
        with pytest.raises(AlreadyFinalized):
            unpadder.finalize()

########NEW FILE########
__FILENAME__ = test_pbkdf2hmac
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import pytest

import six

from cryptography import utils
from cryptography.exceptions import (
    AlreadyFinalized, InvalidKey, _Reasons
)
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, interfaces
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ...utils import raises_unsupported_algorithm


@utils.register_interface(interfaces.HashAlgorithm)
class DummyHash(object):
    name = "dummy-hash"


class TestPBKDF2HMAC(object):
    def test_already_finalized(self):
        kdf = PBKDF2HMAC(hashes.SHA1(), 20, b"salt", 10, default_backend())
        kdf.derive(b"password")
        with pytest.raises(AlreadyFinalized):
            kdf.derive(b"password2")

        kdf = PBKDF2HMAC(hashes.SHA1(), 20, b"salt", 10, default_backend())
        key = kdf.derive(b"password")
        with pytest.raises(AlreadyFinalized):
            kdf.verify(b"password", key)

        kdf = PBKDF2HMAC(hashes.SHA1(), 20, b"salt", 10, default_backend())
        kdf.verify(b"password", key)
        with pytest.raises(AlreadyFinalized):
            kdf.verify(b"password", key)

    def test_unsupported_algorithm(self):
        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_HASH):
            PBKDF2HMAC(DummyHash(), 20, b"salt", 10, default_backend())

    def test_invalid_key(self):
        kdf = PBKDF2HMAC(hashes.SHA1(), 20, b"salt", 10, default_backend())
        key = kdf.derive(b"password")

        kdf = PBKDF2HMAC(hashes.SHA1(), 20, b"salt", 10, default_backend())
        with pytest.raises(InvalidKey):
            kdf.verify(b"password2", key)

    def test_unicode_error_with_salt(self):
        with pytest.raises(TypeError):
            PBKDF2HMAC(hashes.SHA1(), 20, six.u("salt"), 10, default_backend())

    def test_unicode_error_with_key_material(self):
        kdf = PBKDF2HMAC(hashes.SHA1(), 20, b"salt", 10, default_backend())
        with pytest.raises(TypeError):
            kdf.derive(six.u("unicode here"))


def test_invalid_backend():
    pretend_backend = object()

    with raises_unsupported_algorithm(_Reasons.BACKEND_MISSING_INTERFACE):
        PBKDF2HMAC(hashes.SHA1(), 20, b"salt", 10, pretend_backend)

########NEW FILE########
__FILENAME__ = test_pbkdf2hmac_vectors
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import pytest

from cryptography.hazmat.primitives import hashes

from .utils import generate_pbkdf2_test
from ...utils import load_nist_vectors


@pytest.mark.supported(
    only_if=lambda backend: backend.pbkdf2_hmac_supported(hashes.SHA1()),
    skip_message="Does not support SHA1 for PBKDF2HMAC",
)
@pytest.mark.pbkdf2hmac
class TestPBKDF2HMACSHA1(object):
    test_pbkdf2_sha1 = generate_pbkdf2_test(
        load_nist_vectors,
        "KDF",
        [
            "rfc-6070-PBKDF2-SHA1.txt",
        ],
        hashes.SHA1(),
    )

########NEW FILE########
__FILENAME__ = test_rsa
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from __future__ import absolute_import, division, print_function

import binascii
import itertools
import math
import os

import pytest

from cryptography import utils
from cryptography.exceptions import (
    AlreadyFinalized, InvalidSignature, _Reasons
)
from cryptography.hazmat.primitives import hashes, interfaces
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from .fixtures_rsa import (
    RSA_KEY_1024, RSA_KEY_1025, RSA_KEY_1026, RSA_KEY_1027, RSA_KEY_1028,
    RSA_KEY_1029, RSA_KEY_1030, RSA_KEY_1031, RSA_KEY_1536, RSA_KEY_2048,
    RSA_KEY_512, RSA_KEY_512_ALT, RSA_KEY_522, RSA_KEY_599, RSA_KEY_745,
    RSA_KEY_768,
)
from .utils import (
    _check_rsa_private_key, generate_rsa_verification_test
)
from ...utils import (
    load_pkcs1_vectors, load_rsa_nist_vectors, load_vectors_from_file,
    raises_unsupported_algorithm
)


@utils.register_interface(interfaces.AsymmetricPadding)
class DummyPadding(object):
    name = "UNSUPPORTED-PADDING"


class DummyMGF(object):
    _salt_length = 0


def _flatten_pkcs1_examples(vectors):
    flattened_vectors = []
    for vector in vectors:
        examples = vector[0].pop("examples")
        for example in examples:
            merged_vector = (vector[0], vector[1], example)
            flattened_vectors.append(merged_vector)

    return flattened_vectors


def test_modular_inverse():
    p = int(
        "d1f9f6c09fd3d38987f7970247b85a6da84907753d42ec52bc23b745093f4fff5cff3"
        "617ce43d00121a9accc0051f519c76e08cf02fc18acfe4c9e6aea18da470a2b611d2e"
        "56a7b35caa2c0239bc041a53cc5875ca0b668ae6377d4b23e932d8c995fd1e58ecfd8"
        "c4b73259c0d8a54d691cca3f6fb85c8a5c1baf588e898d481", 16
    )
    q = int(
        "d1519255eb8f678c86cfd06802d1fbef8b664441ac46b73d33d13a8404580a33a8e74"
        "cb2ea2e2963125b3d454d7a922cef24dd13e55f989cbabf64255a736671f4629a47b5"
        "b2347cfcd669133088d1c159518531025297c2d67c9da856a12e80222cd03b4c6ec0f"
        "86c957cb7bb8de7a127b645ec9e820aa94581e4762e209f01", 16
    )
    assert rsa._modinv(q, p) == int(
        "0275e06afa722999315f8f322275483e15e2fb46d827b17800f99110b269a6732748f"
        "624a382fa2ed1ec68c99f7fc56fb60e76eea51614881f497ba7034c17dde955f92f15"
        "772f8b2b41f3e56d88b1e096cdd293eba4eae1e82db815e0fadea0c4ec971bc6fd875"
        "c20e67e48c31a611e98d32c6213ae4c4d7b53023b2f80c538", 16
    )


@pytest.mark.rsa
class TestRSA(object):
    @pytest.mark.parametrize(
        ("public_exponent", "key_size"),
        itertools.product(
            (3, 5, 65537),
            (1024, 1025, 1026, 1027, 1028, 1029, 1030, 1031, 1536, 2048)
        )
    )
    def test_generate_rsa_keys(self, backend, public_exponent, key_size):
        skey = rsa.RSAPrivateKey.generate(public_exponent, key_size, backend)
        _check_rsa_private_key(skey)
        assert skey.key_size == key_size
        assert skey.public_exponent == public_exponent

    def test_generate_bad_public_exponent(self, backend):
        with pytest.raises(ValueError):
            rsa.RSAPrivateKey.generate(public_exponent=1,
                                       key_size=2048,
                                       backend=backend)

        with pytest.raises(ValueError):
            rsa.RSAPrivateKey.generate(public_exponent=4,
                                       key_size=2048,
                                       backend=backend)

    def test_cant_generate_insecure_tiny_key(self, backend):
        with pytest.raises(ValueError):
            rsa.RSAPrivateKey.generate(public_exponent=65537,
                                       key_size=511,
                                       backend=backend)

        with pytest.raises(ValueError):
            rsa.RSAPrivateKey.generate(public_exponent=65537,
                                       key_size=256,
                                       backend=backend)

    @pytest.mark.parametrize(
        "pkcs1_example",
        load_vectors_from_file(
            os.path.join(
                "asymmetric", "RSA", "pkcs-1v2-1d2-vec", "pss-vect.txt"),
            load_pkcs1_vectors
        )
    )
    def test_load_pss_vect_example_keys(self, pkcs1_example):
        secret, public = pkcs1_example

        skey = rsa.RSAPrivateKey(
            p=secret["p"],
            q=secret["q"],
            private_exponent=secret["private_exponent"],
            dmp1=secret["dmp1"],
            dmq1=secret["dmq1"],
            iqmp=secret["iqmp"],
            public_exponent=secret["public_exponent"],
            modulus=secret["modulus"]
        )
        assert skey
        _check_rsa_private_key(skey)

        pkey = rsa.RSAPublicKey(
            public_exponent=public["public_exponent"],
            modulus=public["modulus"]
        )
        assert pkey

        pkey2 = skey.public_key()
        assert pkey2

        assert skey.modulus == pkey.modulus
        assert skey.modulus == skey.n
        assert skey.public_exponent == pkey.public_exponent
        assert skey.public_exponent == skey.e
        assert skey.private_exponent == skey.d

        assert pkey.modulus
        assert pkey.modulus == pkey2.modulus
        assert pkey.modulus == pkey.n
        assert pkey.public_exponent == pkey2.public_exponent
        assert pkey.public_exponent == pkey.e

        assert skey.key_size
        assert skey.key_size == pkey.key_size
        assert skey.key_size == pkey2.key_size

    def test_invalid_private_key_argument_types(self):
        with pytest.raises(TypeError):
            rsa.RSAPrivateKey(None, None, None, None, None, None, None, None)

    def test_invalid_public_key_argument_types(self):
        with pytest.raises(TypeError):
            rsa.RSAPublicKey(None, None)

    def test_invalid_private_key_argument_values(self):
        # Start with p=3, q=11, private_exponent=3, public_exponent=7,
        # modulus=33, dmp1=1, dmq1=3, iqmp=2. Then change one value at
        # a time to test the bounds.

        # Test a modulus < 3.
        with pytest.raises(ValueError):
            rsa.RSAPrivateKey(
                p=3,
                q=11,
                private_exponent=3,
                dmp1=1,
                dmq1=3,
                iqmp=2,
                public_exponent=7,
                modulus=2
            )

        # Test a modulus != p * q.
        with pytest.raises(ValueError):
            rsa.RSAPrivateKey(
                p=3,
                q=11,
                private_exponent=3,
                dmp1=1,
                dmq1=3,
                iqmp=2,
                public_exponent=7,
                modulus=35
            )

        # Test a p > modulus.
        with pytest.raises(ValueError):
            rsa.RSAPrivateKey(
                p=37,
                q=11,
                private_exponent=3,
                dmp1=1,
                dmq1=3,
                iqmp=2,
                public_exponent=7,
                modulus=33
            )

        # Test a q > modulus.
        with pytest.raises(ValueError):
            rsa.RSAPrivateKey(
                p=3,
                q=37,
                private_exponent=3,
                dmp1=1,
                dmq1=3,
                iqmp=2,
                public_exponent=7,
                modulus=33
            )

        # Test a dmp1 > modulus.
        with pytest.raises(ValueError):
            rsa.RSAPrivateKey(
                p=3,
                q=11,
                private_exponent=3,
                dmp1=35,
                dmq1=3,
                iqmp=2,
                public_exponent=7,
                modulus=33
            )

        # Test a dmq1 > modulus.
        with pytest.raises(ValueError):
            rsa.RSAPrivateKey(
                p=3,
                q=11,
                private_exponent=3,
                dmp1=1,
                dmq1=35,
                iqmp=2,
                public_exponent=7,
                modulus=33
            )

        # Test an iqmp > modulus.
        with pytest.raises(ValueError):
            rsa.RSAPrivateKey(
                p=3,
                q=11,
                private_exponent=3,
                dmp1=1,
                dmq1=3,
                iqmp=35,
                public_exponent=7,
                modulus=33
            )

        # Test a private_exponent > modulus
        with pytest.raises(ValueError):
            rsa.RSAPrivateKey(
                p=3,
                q=11,
                private_exponent=37,
                dmp1=1,
                dmq1=3,
                iqmp=2,
                public_exponent=7,
                modulus=33
            )

        # Test a public_exponent < 3
        with pytest.raises(ValueError):
            rsa.RSAPrivateKey(
                p=3,
                q=11,
                private_exponent=3,
                dmp1=1,
                dmq1=3,
                iqmp=2,
                public_exponent=1,
                modulus=33
            )

        # Test a public_exponent > modulus
        with pytest.raises(ValueError):
            rsa.RSAPrivateKey(
                p=3,
                q=11,
                private_exponent=3,
                dmp1=1,
                dmq1=3,
                iqmp=2,
                public_exponent=65537,
                modulus=33
            )

        # Test a public_exponent that is not odd.
        with pytest.raises(ValueError):
            rsa.RSAPrivateKey(
                p=3,
                q=11,
                private_exponent=3,
                dmp1=1,
                dmq1=3,
                iqmp=2,
                public_exponent=6,
                modulus=33
            )

        # Test a dmp1 that is not odd.
        with pytest.raises(ValueError):
            rsa.RSAPrivateKey(
                p=3,
                q=11,
                private_exponent=3,
                dmp1=2,
                dmq1=3,
                iqmp=2,
                public_exponent=7,
                modulus=33
            )

        # Test a dmq1 that is not odd.
        with pytest.raises(ValueError):
            rsa.RSAPrivateKey(
                p=3,
                q=11,
                private_exponent=3,
                dmp1=1,
                dmq1=4,
                iqmp=2,
                public_exponent=7,
                modulus=33
            )

    def test_invalid_public_key_argument_values(self):
        # Start with public_exponent=7, modulus=15. Then change one value at a
        # time to test the bounds.

        # Test a modulus < 3.
        with pytest.raises(ValueError):
            rsa.RSAPublicKey(public_exponent=7, modulus=2)

        # Test a public_exponent < 3
        with pytest.raises(ValueError):
            rsa.RSAPublicKey(public_exponent=1, modulus=15)

        # Test a public_exponent > modulus
        with pytest.raises(ValueError):
            rsa.RSAPublicKey(public_exponent=17, modulus=15)

        # Test a public_exponent that is not odd.
        with pytest.raises(ValueError):
            rsa.RSAPublicKey(public_exponent=6, modulus=15)


def test_rsa_generate_invalid_backend():
    pretend_backend = object()

    with raises_unsupported_algorithm(_Reasons.BACKEND_MISSING_INTERFACE):
        rsa.RSAPrivateKey.generate(65537, 2048, pretend_backend)


@pytest.mark.rsa
class TestRSASignature(object):
    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PKCS1v15()
        ),
        skip_message="Does not support PKCS1v1.5."
    )
    @pytest.mark.parametrize(
        "pkcs1_example",
        _flatten_pkcs1_examples(load_vectors_from_file(
            os.path.join(
                "asymmetric", "RSA", "pkcs1v15sign-vectors.txt"),
            load_pkcs1_vectors
        ))
    )
    def test_pkcs1v15_signing(self, pkcs1_example, backend):
        private, public, example = pkcs1_example
        private_key = rsa.RSAPrivateKey(
            p=private["p"],
            q=private["q"],
            private_exponent=private["private_exponent"],
            dmp1=private["dmp1"],
            dmq1=private["dmq1"],
            iqmp=private["iqmp"],
            public_exponent=private["public_exponent"],
            modulus=private["modulus"]
        )
        signer = private_key.signer(padding.PKCS1v15(), hashes.SHA1(), backend)
        signer.update(binascii.unhexlify(example["message"]))
        signature = signer.finalize()
        assert binascii.hexlify(signature) == example["signature"]

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA1()),
                salt_length=padding.PSS.MAX_LENGTH
            )
        ),
        skip_message="Does not support PSS."
    )
    @pytest.mark.parametrize(
        "pkcs1_example",
        _flatten_pkcs1_examples(load_vectors_from_file(
            os.path.join(
                "asymmetric", "RSA", "pkcs-1v2-1d2-vec", "pss-vect.txt"),
            load_pkcs1_vectors
        ))
    )
    def test_pss_signing(self, pkcs1_example, backend):
        private, public, example = pkcs1_example
        private_key = rsa.RSAPrivateKey(
            p=private["p"],
            q=private["q"],
            private_exponent=private["private_exponent"],
            dmp1=private["dmp1"],
            dmq1=private["dmq1"],
            iqmp=private["iqmp"],
            public_exponent=private["public_exponent"],
            modulus=private["modulus"]
        )
        public_key = rsa.RSAPublicKey(
            public_exponent=public["public_exponent"],
            modulus=public["modulus"]
        )
        signer = private_key.signer(
            padding.PSS(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA1(),
            backend
        )
        signer.update(binascii.unhexlify(example["message"]))
        signature = signer.finalize()
        assert len(signature) == math.ceil(private_key.key_size / 8.0)
        # PSS signatures contain randomness so we can't do an exact
        # signature check. Instead we'll verify that the signature created
        # successfully verifies.
        verifier = public_key.verifier(
            signature,
            padding.PSS(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA1(),
            backend
        )
        verifier.update(binascii.unhexlify(example["message"]))
        verifier.verify()

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA1()),
                salt_length=padding.PSS.MAX_LENGTH
            )
        ),
        skip_message="Does not support PSS."
    )
    def test_deprecated_pss_mgf1_salt_length(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_512)
        signer = private_key.signer(
            pytest.deprecated_call(
                padding.PSS,
                mgf=pytest.deprecated_call(
                    padding.MGF1,
                    algorithm=hashes.SHA1(),
                    salt_length=padding.MGF1.MAX_LENGTH
                )
            ),
            hashes.SHA1(),
            backend
        )
        signer.update(b"so deprecated")
        signature = signer.finalize()
        assert len(signature) == math.ceil(private_key.key_size / 8.0)
        verifier = private_key.public_key().verifier(
            signature,
            pytest.deprecated_call(
                padding.PSS,
                mgf=pytest.deprecated_call(
                    padding.MGF1,
                    algorithm=hashes.SHA1(),
                    salt_length=padding.MGF1.MAX_LENGTH
                )
            ),
            hashes.SHA1(),
            backend
        )
        verifier.update(b"so deprecated")
        verifier.verify()

    @pytest.mark.parametrize(
        "hash_alg",
        [hashes.SHA224(), hashes.SHA256(), hashes.SHA384(), hashes.SHA512()]
    )
    def test_pss_signing_sha2(self, hash_alg, backend):
        if not backend.rsa_padding_supported(
            padding.PSS(
                mgf=padding.MGF1(hash_alg),
                salt_length=padding.PSS.MAX_LENGTH
            )
        ):
            pytest.skip(
                "Does not support {0} in MGF1 using PSS.".format(hash_alg.name)
            )
        private_key = rsa.RSAPrivateKey(**RSA_KEY_768)
        public_key = private_key.public_key()
        pss = padding.PSS(
            mgf=padding.MGF1(hash_alg),
            salt_length=padding.PSS.MAX_LENGTH
        )
        signer = private_key.signer(
            pss,
            hash_alg,
            backend
        )
        signer.update(b"testing signature")
        signature = signer.finalize()
        verifier = public_key.verifier(
            signature,
            pss,
            hash_alg,
            backend
        )
        verifier.update(b"testing signature")
        verifier.verify()

    @pytest.mark.supported(
        only_if=lambda backend: (
            backend.hash_supported(hashes.SHA512()) and
            backend.rsa_padding_supported(
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA1()),
                    salt_length=padding.PSS.MAX_LENGTH
                )
            )
        ),
        skip_message="Does not support SHA512."
    )
    def test_pss_minimum_key_size_for_digest(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_522)
        signer = private_key.signer(
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA1()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA512(),
            backend
        )
        signer.update(b"no failure")
        signer.finalize()

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA1()),
                salt_length=padding.PSS.MAX_LENGTH
            )
        ),
        skip_message="Does not support PSS."
    )
    @pytest.mark.supported(
        only_if=lambda backend: backend.hash_supported(hashes.SHA512()),
        skip_message="Does not support SHA512."
    )
    def test_pss_signing_digest_too_large_for_key_size(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_512)
        with pytest.raises(ValueError):
            private_key.signer(
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA1()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA512(),
                backend
            )

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA1()),
                salt_length=padding.PSS.MAX_LENGTH
            )
        ),
        skip_message="Does not support PSS."
    )
    def test_pss_signing_salt_length_too_long(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_512)
        signer = private_key.signer(
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA1()),
                salt_length=1000000
            ),
            hashes.SHA1(),
            backend
        )
        signer.update(b"failure coming")
        with pytest.raises(ValueError):
            signer.finalize()

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PKCS1v15()
        ),
        skip_message="Does not support PKCS1v1.5."
    )
    def test_use_after_finalize(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_512)
        signer = private_key.signer(padding.PKCS1v15(), hashes.SHA1(), backend)
        signer.update(b"sign me")
        signer.finalize()
        with pytest.raises(AlreadyFinalized):
            signer.finalize()
        with pytest.raises(AlreadyFinalized):
            signer.update(b"more data")

    def test_unsupported_padding(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_512)
        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_PADDING):
            private_key.signer(DummyPadding(), hashes.SHA1(), backend)

    def test_padding_incorrect_type(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_512)
        with pytest.raises(TypeError):
            private_key.signer("notpadding", hashes.SHA1(), backend)

    def test_rsa_signer_invalid_backend(self, backend):
        pretend_backend = object()
        private_key = rsa.RSAPrivateKey(**RSA_KEY_2048)

        with raises_unsupported_algorithm(_Reasons.BACKEND_MISSING_INTERFACE):
            private_key.signer(
                padding.PKCS1v15(), hashes.SHA256, pretend_backend)

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PSS(mgf=padding.MGF1(hashes.SHA1()), salt_length=0)
        ),
        skip_message="Does not support PSS."
    )
    def test_unsupported_pss_mgf(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_512)
        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_MGF):
            private_key.signer(padding.PSS(mgf=DummyMGF()), hashes.SHA1(),
                               backend)

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PKCS1v15()
        ),
        skip_message="Does not support PKCS1v1.5."
    )
    def test_pkcs1_digest_too_large_for_key_size(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_599)
        signer = private_key.signer(
            padding.PKCS1v15(),
            hashes.SHA512(),
            backend
        )
        signer.update(b"failure coming")
        with pytest.raises(ValueError):
            signer.finalize()

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PKCS1v15()
        ),
        skip_message="Does not support PKCS1v1.5."
    )
    def test_pkcs1_minimum_key_size(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_745)
        signer = private_key.signer(
            padding.PKCS1v15(),
            hashes.SHA512(),
            backend
        )
        signer.update(b"no failure")
        signer.finalize()


@pytest.mark.rsa
class TestRSAVerification(object):
    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PKCS1v15()
        ),
        skip_message="Does not support PKCS1v1.5."
    )
    @pytest.mark.parametrize(
        "pkcs1_example",
        _flatten_pkcs1_examples(load_vectors_from_file(
            os.path.join(
                "asymmetric", "RSA", "pkcs1v15sign-vectors.txt"),
            load_pkcs1_vectors
        ))
    )
    def test_pkcs1v15_verification(self, pkcs1_example, backend):
        private, public, example = pkcs1_example
        public_key = rsa.RSAPublicKey(
            public_exponent=public["public_exponent"],
            modulus=public["modulus"]
        )
        verifier = public_key.verifier(
            binascii.unhexlify(example["signature"]),
            padding.PKCS1v15(),
            hashes.SHA1(),
            backend
        )
        verifier.update(binascii.unhexlify(example["message"]))
        verifier.verify()

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PKCS1v15()
        ),
        skip_message="Does not support PKCS1v1.5."
    )
    def test_invalid_pkcs1v15_signature_wrong_data(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_512)
        public_key = private_key.public_key()
        signer = private_key.signer(padding.PKCS1v15(), hashes.SHA1(), backend)
        signer.update(b"sign me")
        signature = signer.finalize()
        verifier = public_key.verifier(
            signature,
            padding.PKCS1v15(),
            hashes.SHA1(),
            backend
        )
        verifier.update(b"incorrect data")
        with pytest.raises(InvalidSignature):
            verifier.verify()

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PKCS1v15()
        ),
        skip_message="Does not support PKCS1v1.5."
    )
    def test_invalid_pkcs1v15_signature_wrong_key(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_512)
        private_key2 = rsa.RSAPrivateKey(**RSA_KEY_512_ALT)
        public_key = private_key2.public_key()
        signer = private_key.signer(padding.PKCS1v15(), hashes.SHA1(), backend)
        signer.update(b"sign me")
        signature = signer.finalize()
        verifier = public_key.verifier(
            signature,
            padding.PKCS1v15(),
            hashes.SHA1(),
            backend
        )
        verifier.update(b"sign me")
        with pytest.raises(InvalidSignature):
            verifier.verify()

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA1()),
                salt_length=20
            )
        ),
        skip_message="Does not support PSS."
    )
    @pytest.mark.parametrize(
        "pkcs1_example",
        _flatten_pkcs1_examples(load_vectors_from_file(
            os.path.join(
                "asymmetric", "RSA", "pkcs-1v2-1d2-vec", "pss-vect.txt"),
            load_pkcs1_vectors
        ))
    )
    def test_pss_verification(self, pkcs1_example, backend):
        private, public, example = pkcs1_example
        public_key = rsa.RSAPublicKey(
            public_exponent=public["public_exponent"],
            modulus=public["modulus"]
        )
        verifier = public_key.verifier(
            binascii.unhexlify(example["signature"]),
            padding.PSS(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                salt_length=20
            ),
            hashes.SHA1(),
            backend
        )
        verifier.update(binascii.unhexlify(example["message"]))
        verifier.verify()

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA1()),
                salt_length=padding.PSS.MAX_LENGTH
            )
        ),
        skip_message="Does not support PSS."
    )
    def test_invalid_pss_signature_wrong_data(self, backend):
        public_key = rsa.RSAPublicKey(
            modulus=int(
                b"dffc2137d5e810cde9e4b4612f5796447218bab913b3fa98bdf7982e4fa6"
                b"ec4d6653ef2b29fb1642b095befcbea6decc178fb4bed243d3c3592c6854"
                b"6af2d3f3", 16
            ),
            public_exponent=65537
        )
        signature = binascii.unhexlify(
            b"0e68c3649df91c5bc3665f96e157efa75b71934aaa514d91e94ca8418d100f45"
            b"6f05288e58525f99666bab052adcffdf7186eb40f583bd38d98c97d3d524808b"
        )
        verifier = public_key.verifier(
            signature,
            padding.PSS(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA1(),
            backend
        )
        verifier.update(b"incorrect data")
        with pytest.raises(InvalidSignature):
            verifier.verify()

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA1()),
                salt_length=padding.PSS.MAX_LENGTH
            )
        ),
        skip_message="Does not support PSS."
    )
    def test_invalid_pss_signature_wrong_key(self, backend):
        signature = binascii.unhexlify(
            b"3a1880165014ba6eb53cc1449d13e5132ebcc0cfd9ade6d7a2494a0503bd0826"
            b"f8a46c431e0d7be0ca3e453f8b2b009e2733764da7927cc6dbe7a021437a242e"
        )
        public_key = rsa.RSAPublicKey(
            modulus=int(
                b"381201f4905d67dfeb3dec131a0fbea773489227ec7a1448c3109189ac68"
                b"5a95441be90866a14c4d2e139cd16db540ec6c7abab13ffff91443fd46a8"
                b"960cbb7658ded26a5c95c86f6e40384e1c1239c63e541ba221191c4dd303"
                b"231b42e33c6dbddf5ec9a746f09bf0c25d0f8d27f93ee0ae5c0d723348f4"
                b"030d3581e13522e1", 16
            ),
            public_exponent=65537
        )
        verifier = public_key.verifier(
            signature,
            padding.PSS(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA1(),
            backend
        )
        verifier.update(b"sign me")
        with pytest.raises(InvalidSignature):
            verifier.verify()

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA1()),
                salt_length=padding.PSS.MAX_LENGTH
            )
        ),
        skip_message="Does not support PSS."
    )
    def test_invalid_pss_signature_data_too_large_for_modulus(self, backend):
        signature = binascii.unhexlify(
            b"cb43bde4f7ab89eb4a79c6e8dd67e0d1af60715da64429d90c716a490b799c29"
            b"194cf8046509c6ed851052367a74e2e92d9b38947ed74332acb115a03fcc0222"
        )
        public_key = rsa.RSAPublicKey(
            modulus=int(
                b"381201f4905d67dfeb3dec131a0fbea773489227ec7a1448c3109189ac68"
                b"5a95441be90866a14c4d2e139cd16db540ec6c7abab13ffff91443fd46a8"
                b"960cbb7658ded26a5c95c86f6e40384e1c1239c63e541ba221191c4dd303"
                b"231b42e33c6dbddf5ec9a746f09bf0c25d0f8d27f93ee0ae5c0d723348f4"
                b"030d3581e13522", 16
            ),
            public_exponent=65537
        )
        verifier = public_key.verifier(
            signature,
            padding.PSS(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA1(),
            backend
        )
        verifier.update(b"sign me")
        with pytest.raises(InvalidSignature):
            verifier.verify()

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PKCS1v15()
        ),
        skip_message="Does not support PKCS1v1.5."
    )
    def test_use_after_finalize(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_512)
        public_key = private_key.public_key()
        signer = private_key.signer(padding.PKCS1v15(), hashes.SHA1(), backend)
        signer.update(b"sign me")
        signature = signer.finalize()

        verifier = public_key.verifier(
            signature,
            padding.PKCS1v15(),
            hashes.SHA1(),
            backend
        )
        verifier.update(b"sign me")
        verifier.verify()
        with pytest.raises(AlreadyFinalized):
            verifier.verify()
        with pytest.raises(AlreadyFinalized):
            verifier.update(b"more data")

    def test_unsupported_padding(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_512)
        public_key = private_key.public_key()
        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_PADDING):
            public_key.verifier(b"sig", DummyPadding(), hashes.SHA1(), backend)

    def test_padding_incorrect_type(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_512)
        public_key = private_key.public_key()
        with pytest.raises(TypeError):
            public_key.verifier(b"sig", "notpadding", hashes.SHA1(), backend)

    def test_rsa_verifier_invalid_backend(self, backend):
        pretend_backend = object()
        private_key = rsa.RSAPrivateKey.generate(65537, 2048, backend)
        public_key = private_key.public_key()

        with raises_unsupported_algorithm(_Reasons.BACKEND_MISSING_INTERFACE):
            public_key.verifier(
                b"foo", padding.PKCS1v15(), hashes.SHA256(), pretend_backend)

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PSS(mgf=padding.MGF1(hashes.SHA1()), salt_length=0)
        ),
        skip_message="Does not support PSS."
    )
    def test_unsupported_pss_mgf(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_512)
        public_key = private_key.public_key()
        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_MGF):
            public_key.verifier(b"sig", padding.PSS(mgf=DummyMGF()),
                                hashes.SHA1(), backend)

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA1()),
                salt_length=padding.PSS.MAX_LENGTH
            )
        ),
        skip_message="Does not support PSS."
    )
    @pytest.mark.supported(
        only_if=lambda backend: backend.hash_supported(hashes.SHA512()),
        skip_message="Does not support SHA512."
    )
    def test_pss_verify_digest_too_large_for_key_size(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_512)
        signature = binascii.unhexlify(
            b"8b9a3ae9fb3b64158f3476dd8d8a1f1425444e98940e0926378baa9944d219d8"
            b"534c050ef6b19b1bdc6eb4da422e89161106a6f5b5cc16135b11eb6439b646bd"
        )
        public_key = private_key.public_key()
        with pytest.raises(ValueError):
            public_key.verifier(
                signature,
                padding.PSS(
                    mgf=padding.MGF1(algorithm=hashes.SHA1()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA512(),
                backend
            )

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA1()),
                salt_length=padding.PSS.MAX_LENGTH
            )
        ),
        skip_message="Does not support PSS."
    )
    def test_pss_verify_salt_length_too_long(self, backend):
        signature = binascii.unhexlify(
            b"8b9a3ae9fb3b64158f3476dd8d8a1f1425444e98940e0926378baa9944d219d8"
            b"534c050ef6b19b1bdc6eb4da422e89161106a6f5b5cc16135b11eb6439b646bd"
        )
        public_key = rsa.RSAPublicKey(
            modulus=int(
                b"d309e4612809437548b747d7f9eb9cd3340f54fe42bb3f84a36933b0839c"
                b"11b0c8b7f67e11f7252370161e31159c49c784d4bc41c42a78ce0f0b40a3"
                b"ca8ffb91", 16
            ),
            public_exponent=65537
        )
        verifier = public_key.verifier(
            signature,
            padding.PSS(
                mgf=padding.MGF1(
                    algorithm=hashes.SHA1(),
                ),
                salt_length=1000000
            ),
            hashes.SHA1(),
            backend
        )
        verifier.update(b"sign me")
        with pytest.raises(InvalidSignature):
            verifier.verify()


@pytest.mark.rsa
class TestRSAPSSMGF1Verification(object):
    test_rsa_pss_mgf1_sha1 = pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA1()),
                salt_length=padding.PSS.MAX_LENGTH
            )
        ),
        skip_message="Does not support PSS using MGF1 with SHA1."
    )(generate_rsa_verification_test(
        load_rsa_nist_vectors,
        os.path.join("asymmetric", "RSA", "FIPS_186-2"),
        [
            "SigGenPSS_186-2.rsp",
            "SigGenPSS_186-3.rsp",
            "SigVerPSS_186-3.rsp",
        ],
        hashes.SHA1(),
        lambda params, hash_alg: padding.PSS(
            mgf=padding.MGF1(
                algorithm=hash_alg,
            ),
            salt_length=params["salt_length"]
        )
    ))

    test_rsa_pss_mgf1_sha224 = pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA224()),
                salt_length=padding.PSS.MAX_LENGTH
            )
        ),
        skip_message="Does not support PSS using MGF1 with SHA224."
    )(generate_rsa_verification_test(
        load_rsa_nist_vectors,
        os.path.join("asymmetric", "RSA", "FIPS_186-2"),
        [
            "SigGenPSS_186-2.rsp",
            "SigGenPSS_186-3.rsp",
            "SigVerPSS_186-3.rsp",
        ],
        hashes.SHA224(),
        lambda params, hash_alg: padding.PSS(
            mgf=padding.MGF1(
                algorithm=hash_alg,
            ),
            salt_length=params["salt_length"]
        )
    ))

    test_rsa_pss_mgf1_sha256 = pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            )
        ),
        skip_message="Does not support PSS using MGF1 with SHA256."
    )(generate_rsa_verification_test(
        load_rsa_nist_vectors,
        os.path.join("asymmetric", "RSA", "FIPS_186-2"),
        [
            "SigGenPSS_186-2.rsp",
            "SigGenPSS_186-3.rsp",
            "SigVerPSS_186-3.rsp",
        ],
        hashes.SHA256(),
        lambda params, hash_alg: padding.PSS(
            mgf=padding.MGF1(
                algorithm=hash_alg,
            ),
            salt_length=params["salt_length"]
        )
    ))

    test_rsa_pss_mgf1_sha384 = pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA384()),
                salt_length=padding.PSS.MAX_LENGTH
            )
        ),
        skip_message="Does not support PSS using MGF1 with SHA384."
    )(generate_rsa_verification_test(
        load_rsa_nist_vectors,
        os.path.join("asymmetric", "RSA", "FIPS_186-2"),
        [
            "SigGenPSS_186-2.rsp",
            "SigGenPSS_186-3.rsp",
            "SigVerPSS_186-3.rsp",
        ],
        hashes.SHA384(),
        lambda params, hash_alg: padding.PSS(
            mgf=padding.MGF1(
                algorithm=hash_alg,
            ),
            salt_length=params["salt_length"]
        )
    ))

    test_rsa_pss_mgf1_sha512 = pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA512()),
                salt_length=padding.PSS.MAX_LENGTH
            )
        ),
        skip_message="Does not support PSS using MGF1 with SHA512."
    )(generate_rsa_verification_test(
        load_rsa_nist_vectors,
        os.path.join("asymmetric", "RSA", "FIPS_186-2"),
        [
            "SigGenPSS_186-2.rsp",
            "SigGenPSS_186-3.rsp",
            "SigVerPSS_186-3.rsp",
        ],
        hashes.SHA512(),
        lambda params, hash_alg: padding.PSS(
            mgf=padding.MGF1(
                algorithm=hash_alg,
            ),
            salt_length=params["salt_length"]
        )
    ))


@pytest.mark.rsa
class TestRSAPKCS1Verification(object):
    test_rsa_pkcs1v15_verify_sha1 = pytest.mark.supported(
        only_if=lambda backend: (
            backend.hash_supported(hashes.SHA1()) and
            backend.rsa_padding_supported(padding.PKCS1v15())
        ),
        skip_message="Does not support SHA1 and PKCS1v1.5."
    )(generate_rsa_verification_test(
        load_rsa_nist_vectors,
        os.path.join("asymmetric", "RSA", "FIPS_186-2"),
        [
            "SigGen15_186-2.rsp",
            "SigGen15_186-3.rsp",
            "SigVer15_186-3.rsp",
        ],
        hashes.SHA1(),
        lambda params, hash_alg: padding.PKCS1v15()
    ))

    test_rsa_pkcs1v15_verify_sha224 = pytest.mark.supported(
        only_if=lambda backend: (
            backend.hash_supported(hashes.SHA224()) and
            backend.rsa_padding_supported(padding.PKCS1v15())
        ),
        skip_message="Does not support SHA224 and PKCS1v1.5."
    )(generate_rsa_verification_test(
        load_rsa_nist_vectors,
        os.path.join("asymmetric", "RSA", "FIPS_186-2"),
        [
            "SigGen15_186-2.rsp",
            "SigGen15_186-3.rsp",
            "SigVer15_186-3.rsp",
        ],
        hashes.SHA224(),
        lambda params, hash_alg: padding.PKCS1v15()
    ))

    test_rsa_pkcs1v15_verify_sha256 = pytest.mark.supported(
        only_if=lambda backend: (
            backend.hash_supported(hashes.SHA256()) and
            backend.rsa_padding_supported(padding.PKCS1v15())
        ),
        skip_message="Does not support SHA256 and PKCS1v1.5."
    )(generate_rsa_verification_test(
        load_rsa_nist_vectors,
        os.path.join("asymmetric", "RSA", "FIPS_186-2"),
        [
            "SigGen15_186-2.rsp",
            "SigGen15_186-3.rsp",
            "SigVer15_186-3.rsp",
        ],
        hashes.SHA256(),
        lambda params, hash_alg: padding.PKCS1v15()
    ))

    test_rsa_pkcs1v15_verify_sha384 = pytest.mark.supported(
        only_if=lambda backend: (
            backend.hash_supported(hashes.SHA384()) and
            backend.rsa_padding_supported(padding.PKCS1v15())
        ),
        skip_message="Does not support SHA384 and PKCS1v1.5."
    )(generate_rsa_verification_test(
        load_rsa_nist_vectors,
        os.path.join("asymmetric", "RSA", "FIPS_186-2"),
        [
            "SigGen15_186-2.rsp",
            "SigGen15_186-3.rsp",
            "SigVer15_186-3.rsp",
        ],
        hashes.SHA384(),
        lambda params, hash_alg: padding.PKCS1v15()
    ))

    test_rsa_pkcs1v15_verify_sha512 = pytest.mark.supported(
        only_if=lambda backend: (
            backend.hash_supported(hashes.SHA512()) and
            backend.rsa_padding_supported(padding.PKCS1v15())
        ),
        skip_message="Does not support SHA512 and PKCS1v1.5."
    )(generate_rsa_verification_test(
        load_rsa_nist_vectors,
        os.path.join("asymmetric", "RSA", "FIPS_186-2"),
        [
            "SigGen15_186-2.rsp",
            "SigGen15_186-3.rsp",
            "SigVer15_186-3.rsp",
        ],
        hashes.SHA512(),
        lambda params, hash_alg: padding.PKCS1v15()
    ))


class TestPSS(object):
    def test_deprecation_warning(self):
        pytest.deprecated_call(
            padding.PSS,
            mgf=padding.MGF1(hashes.SHA1(), 20)
        )

    def test_invalid_salt_length_not_integer(self):
        with pytest.raises(TypeError):
            padding.PSS(
                mgf=padding.MGF1(
                    hashes.SHA1()
                ),
                salt_length=b"not_a_length"
            )

    def test_invalid_salt_length_negative_integer(self):
        with pytest.raises(ValueError):
            padding.PSS(
                mgf=padding.MGF1(
                    hashes.SHA1()
                ),
                salt_length=-1
            )

    def test_no_salt_length_supplied_pss_or_mgf1(self):
        with pytest.raises(ValueError):
            padding.PSS(mgf=padding.MGF1(hashes.SHA1()))

    def test_valid_pss_parameters(self):
        algorithm = hashes.SHA1()
        salt_length = algorithm.digest_size
        mgf = padding.MGF1(algorithm)
        pss = padding.PSS(mgf=mgf, salt_length=salt_length)
        assert pss._mgf == mgf
        assert pss._salt_length == salt_length

    def test_valid_pss_parameters_maximum(self):
        algorithm = hashes.SHA1()
        mgf = padding.MGF1(algorithm)
        pss = padding.PSS(mgf=mgf, salt_length=padding.PSS.MAX_LENGTH)
        assert pss._mgf == mgf
        assert pss._salt_length == padding.PSS.MAX_LENGTH


class TestMGF1(object):
    def test_deprecation_warning(self):
        pytest.deprecated_call(
            padding.MGF1, algorithm=hashes.SHA1(), salt_length=20
        )

    def test_invalid_hash_algorithm(self):
        with pytest.raises(TypeError):
            padding.MGF1(b"not_a_hash", 0)

    def test_invalid_salt_length_not_integer(self):
        with pytest.raises(TypeError):
            padding.MGF1(hashes.SHA1(), b"not_a_length")

    def test_invalid_salt_length_negative_integer(self):
        with pytest.raises(ValueError):
            padding.MGF1(hashes.SHA1(), -1)

    def test_valid_mgf1_parameters(self):
        algorithm = hashes.SHA1()
        salt_length = algorithm.digest_size
        mgf = padding.MGF1(algorithm, salt_length)
        assert mgf._algorithm == algorithm
        assert mgf._salt_length == salt_length

    def test_valid_mgf1_parameters_maximum(self):
        algorithm = hashes.SHA1()
        mgf = padding.MGF1(algorithm, padding.MGF1.MAX_LENGTH)
        assert mgf._algorithm == algorithm
        assert mgf._salt_length == padding.MGF1.MAX_LENGTH


class TestOAEP(object):
    def test_invalid_algorithm(self):
        mgf = padding.MGF1(hashes.SHA1())
        with pytest.raises(TypeError):
            padding.OAEP(
                mgf=mgf,
                algorithm=b"",
                label=None
            )


@pytest.mark.rsa
class TestRSADecryption(object):
    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PKCS1v15()
        ),
        skip_message="Does not support PKCS1v1.5."
    )
    @pytest.mark.parametrize(
        "vector",
        _flatten_pkcs1_examples(load_vectors_from_file(
            os.path.join(
                "asymmetric", "RSA", "pkcs1v15crypt-vectors.txt"),
            load_pkcs1_vectors
        ))
    )
    def test_decrypt_pkcs1v15_vectors(self, vector, backend):
        private, public, example = vector
        skey = rsa.RSAPrivateKey(
            p=private["p"],
            q=private["q"],
            private_exponent=private["private_exponent"],
            dmp1=private["dmp1"],
            dmq1=private["dmq1"],
            iqmp=private["iqmp"],
            public_exponent=private["public_exponent"],
            modulus=private["modulus"]
        )
        ciphertext = binascii.unhexlify(example["encryption"])
        assert len(ciphertext) == math.ceil(skey.key_size / 8.0)
        message = skey.decrypt(
            ciphertext,
            padding.PKCS1v15(),
            backend
        )
        assert message == binascii.unhexlify(example["message"])

    def test_unsupported_padding(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_512)
        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_PADDING):
            private_key.decrypt(b"0" * 64, DummyPadding(), backend)

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PKCS1v15()
        ),
        skip_message="Does not support PKCS1v1.5."
    )
    def test_decrypt_invalid_decrypt(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_512)
        with pytest.raises(ValueError):
            private_key.decrypt(
                b"\x00" * 64,
                padding.PKCS1v15(),
                backend
            )

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PKCS1v15()
        ),
        skip_message="Does not support PKCS1v1.5."
    )
    def test_decrypt_ciphertext_too_large(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_512)
        with pytest.raises(ValueError):
            private_key.decrypt(
                b"\x00" * 65,
                padding.PKCS1v15(),
                backend
            )

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PKCS1v15()
        ),
        skip_message="Does not support PKCS1v1.5."
    )
    def test_decrypt_ciphertext_too_small(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_512)
        ct = binascii.unhexlify(
            b"50b4c14136bd198c2f3c3ed243fce036e168d56517984a263cd66492b80804f1"
            b"69d210f2b9bdfb48b12f9ea05009c77da257cc600ccefe3a6283789d8ea0"
        )
        with pytest.raises(ValueError):
            private_key.decrypt(
                ct,
                padding.PKCS1v15(),
                backend
            )

    def test_rsa_decrypt_invalid_backend(self, backend):
        pretend_backend = object()
        private_key = rsa.RSAPrivateKey.generate(65537, 2048, backend)

        with raises_unsupported_algorithm(_Reasons.BACKEND_MISSING_INTERFACE):
            private_key.decrypt(
                b"irrelevant",
                padding.PKCS1v15(),
                pretend_backend
            )

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                algorithm=hashes.SHA1(),
                label=None
            )
        ),
        skip_message="Does not support OAEP."
    )
    @pytest.mark.parametrize(
        "vector",
        _flatten_pkcs1_examples(load_vectors_from_file(
            os.path.join(
                "asymmetric", "RSA", "pkcs-1v2-1d2-vec", "oaep-vect.txt"),
            load_pkcs1_vectors
        ))
    )
    def test_decrypt_oaep_vectors(self, vector, backend):
        private, public, example = vector
        skey = rsa.RSAPrivateKey(
            p=private["p"],
            q=private["q"],
            private_exponent=private["private_exponent"],
            dmp1=private["dmp1"],
            dmq1=private["dmq1"],
            iqmp=private["iqmp"],
            public_exponent=private["public_exponent"],
            modulus=private["modulus"]
        )
        message = skey.decrypt(
            binascii.unhexlify(example["encryption"]),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                algorithm=hashes.SHA1(),
                label=None
            ),
            backend
        )
        assert message == binascii.unhexlify(example["message"])

    def test_unsupported_oaep_mgf(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_512)
        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_MGF):
            private_key.decrypt(
                b"0" * 64,
                padding.OAEP(
                    mgf=DummyMGF(),
                    algorithm=hashes.SHA1(),
                    label=None
                ),
                backend
            )


@pytest.mark.rsa
class TestRSAEncryption(object):
    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                algorithm=hashes.SHA1(),
                label=None
            )
        ),
        skip_message="Does not support OAEP."
    )
    @pytest.mark.parametrize(
        ("key_data", "pad"),
        itertools.product(
            (RSA_KEY_1024, RSA_KEY_1025, RSA_KEY_1026, RSA_KEY_1027,
             RSA_KEY_1028, RSA_KEY_1029, RSA_KEY_1030, RSA_KEY_1031,
             RSA_KEY_1536, RSA_KEY_2048),
            [
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA1()),
                    algorithm=hashes.SHA1(),
                    label=None
                )
            ]
        )
    )
    def test_rsa_encrypt_oaep(self, key_data, pad, backend):
        private_key = rsa.RSAPrivateKey(**key_data)
        pt = b"encrypt me!"
        public_key = private_key.public_key()
        ct = public_key.encrypt(
            pt,
            pad,
            backend
        )
        assert ct != pt
        assert len(ct) == math.ceil(public_key.key_size / 8.0)
        recovered_pt = private_key.decrypt(
            ct,
            pad,
            backend
        )
        assert recovered_pt == pt

    @pytest.mark.supported(
        only_if=lambda backend: backend.rsa_padding_supported(
            padding.PKCS1v15()
        ),
        skip_message="Does not support PKCS1v1.5."
    )
    @pytest.mark.parametrize(
        ("key_data", "pad"),
        itertools.product(
            (RSA_KEY_1024, RSA_KEY_1025, RSA_KEY_1026, RSA_KEY_1027,
             RSA_KEY_1028, RSA_KEY_1029, RSA_KEY_1030, RSA_KEY_1031,
             RSA_KEY_1536, RSA_KEY_2048),
            [padding.PKCS1v15()]
        )
    )
    def test_rsa_encrypt_pkcs1v15(self, key_data, pad, backend):
        private_key = rsa.RSAPrivateKey(**key_data)
        pt = b"encrypt me!"
        public_key = private_key.public_key()
        ct = public_key.encrypt(
            pt,
            pad,
            backend
        )
        assert ct != pt
        assert len(ct) == math.ceil(public_key.key_size / 8.0)
        recovered_pt = private_key.decrypt(
            ct,
            pad,
            backend
        )
        assert recovered_pt == pt

    @pytest.mark.parametrize(
        ("key_data", "pad"),
        itertools.product(
            (RSA_KEY_1024, RSA_KEY_1025, RSA_KEY_1026, RSA_KEY_1027,
             RSA_KEY_1028, RSA_KEY_1029, RSA_KEY_1030, RSA_KEY_1031,
             RSA_KEY_1536, RSA_KEY_2048),
            (
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA1()),
                    algorithm=hashes.SHA1(),
                    label=None
                ),
                padding.PKCS1v15()
            )
        )
    )
    def test_rsa_encrypt_key_too_small(self, key_data, pad, backend):
        private_key = rsa.RSAPrivateKey(**key_data)
        public_key = private_key.public_key()
        # Slightly smaller than the key size but not enough for padding.
        with pytest.raises(ValueError):
            public_key.encrypt(
                b"\x00" * (private_key.key_size // 8 - 1),
                pad,
                backend
            )

        # Larger than the key size.
        with pytest.raises(ValueError):
            public_key.encrypt(
                b"\x00" * (private_key.key_size // 8 + 5),
                pad,
                backend
            )

    def test_rsa_encrypt_invalid_backend(self, backend):
        pretend_backend = object()
        private_key = rsa.RSAPrivateKey.generate(65537, 512, backend)
        public_key = private_key.public_key()

        with raises_unsupported_algorithm(_Reasons.BACKEND_MISSING_INTERFACE):
            public_key.encrypt(
                b"irrelevant",
                padding.PKCS1v15(),
                pretend_backend
            )

    def test_unsupported_padding(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_512)
        public_key = private_key.public_key()

        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_PADDING):
            public_key.encrypt(b"somedata", DummyPadding(), backend)

    def test_unsupported_oaep_mgf(self, backend):
        private_key = rsa.RSAPrivateKey(**RSA_KEY_512)
        public_key = private_key.public_key()

        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_MGF):
            public_key.encrypt(
                b"ciphertext",
                padding.OAEP(
                    mgf=DummyMGF(),
                    algorithm=hashes.SHA1(),
                    label=None
                ),
                backend
            )

########NEW FILE########
__FILENAME__ = test_seed
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import binascii
import os

import pytest

from cryptography.hazmat.primitives.ciphers import algorithms, modes

from .utils import generate_encrypt_test
from ...utils import load_nist_vectors


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.SEED("\x00" * 16), modes.ECB()
    ),
    skip_message="Does not support SEED ECB",
)
@pytest.mark.cipher
class TestSEEDModeECB(object):
    test_ECB = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "SEED"),
        ["rfc-4269.txt"],
        lambda key, **kwargs: algorithms.SEED(binascii.unhexlify((key))),
        lambda **kwargs: modes.ECB(),
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.SEED("\x00" * 16), modes.CBC("\x00" * 16)
    ),
    skip_message="Does not support SEED CBC",
)
@pytest.mark.cipher
class TestSEEDModeCBC(object):
    test_CBC = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "SEED"),
        ["rfc-4196.txt"],
        lambda key, **kwargs: algorithms.SEED(binascii.unhexlify((key))),
        lambda iv, **kwargs: modes.CBC(binascii.unhexlify(iv))
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.SEED("\x00" * 16), modes.OFB("\x00" * 16)
    ),
    skip_message="Does not support SEED OFB",
)
@pytest.mark.cipher
class TestSEEDModeOFB(object):
    test_OFB = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "SEED"),
        ["seed-ofb.txt"],
        lambda key, **kwargs: algorithms.SEED(binascii.unhexlify((key))),
        lambda iv, **kwargs: modes.OFB(binascii.unhexlify(iv))
    )


@pytest.mark.supported(
    only_if=lambda backend: backend.cipher_supported(
        algorithms.SEED("\x00" * 16), modes.CFB("\x00" * 16)
    ),
    skip_message="Does not support SEED CFB",
)
@pytest.mark.cipher
class TestSEEDModeCFB(object):
    test_CFB = generate_encrypt_test(
        load_nist_vectors,
        os.path.join("ciphers", "SEED"),
        ["seed-cfb.txt"],
        lambda key, **kwargs: algorithms.SEED(binascii.unhexlify((key))),
        lambda iv, **kwargs: modes.CFB(binascii.unhexlify(iv))
    )

########NEW FILE########
__FILENAME__ = test_serialization
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from __future__ import absolute_import, division, print_function

import os
import textwrap

import pytest

from cryptography.exceptions import _Reasons
from cryptography.hazmat.primitives.asymmetric import dsa, rsa
from cryptography.hazmat.primitives.serialization import (
    load_pem_pkcs8_private_key,
    load_pem_traditional_openssl_private_key
)

from .utils import _check_rsa_private_key, load_vectors_from_file
from ...utils import raises_unsupported_algorithm


@pytest.mark.traditional_openssl_serialization
class TestTraditionalOpenSSLSerialisation(object):
    @pytest.mark.parametrize(
        ("key_file", "password"),
        [
            ("key1.pem", b"123456"),
            ("key2.pem", b"a123456"),
            ("testrsa.pem", None),
            ("testrsa-encrypted.pem", b"password"),
        ]
    )
    def test_load_pem_rsa_private_key(self, key_file, password, backend):
        key = load_vectors_from_file(
            os.path.join(
                "asymmetric", "Traditional_OpenSSL_Serialization", key_file),
            lambda pemfile: load_pem_traditional_openssl_private_key(
                pemfile.read().encode(), password, backend
            )
        )

        assert key
        assert isinstance(key, rsa.RSAPrivateKey)
        _check_rsa_private_key(key)

    @pytest.mark.parametrize(
        ("key_file", "password"),
        [
            ("dsa.1024.pem", None),
            ("dsa.2048.pem", None),
            ("dsa.3072.pem", None),
        ]
    )
    def test_load_pem_dsa_private_key(self, key_file, password, backend):
        key = load_vectors_from_file(
            os.path.join(
                "asymmetric", "Traditional_OpenSSL_Serialization", key_file),
            lambda pemfile: load_pem_traditional_openssl_private_key(
                pemfile.read().encode(), password, backend
            )
        )

        assert key
        assert isinstance(key, dsa.DSAPrivateKey)

    def test_key1_pem_encrypted_values(self, backend):
        pkey = load_vectors_from_file(
            os.path.join(
                "asymmetric", "Traditional_OpenSSL_Serialization", "key1.pem"),
            lambda pemfile: load_pem_traditional_openssl_private_key(
                pemfile.read().encode(), b"123456", backend
            )
        )
        assert pkey

        assert pkey.p == int(
            "fb7d316fc51531b36d93adaefaf52db6ad5beb793d37c4cf9dfc1ddd17cfbafb",
            16
        )
        assert pkey.q == int(
            "df98264e646de9a0fbeab094e31caad5bc7adceaaae3c800ca0275dd4bb307f5",
            16
        )
        assert pkey.private_exponent == int(
            "db4848c36f478dd5d38f35ae519643b6b810d404bcb76c00e44015e56ca1cab0"
            "7bb7ae91f6b4b43fcfc82a47d7ed55b8c575152116994c2ce5325ec24313b911",
            16
        )
        assert pkey.dmp1 == int(
            "ce997f967192c2bcc3853186f1559fd355c190c58ddc15cbf5de9b6df954c727",
            16
        )
        assert pkey.dmq1 == int(
            "b018a57ab20ffaa3862435445d863369b852cf70a67c55058213e3fe10e3848d",
            16
        )
        assert pkey.iqmp == int(
            "6a8d830616924f5cf2d1bc1973f97fde6b63e052222ac7be06aa2532d10bac76",
            16
        )
        assert pkey.public_exponent == 65537
        assert pkey.modulus == int(
            "dba786074f2f0350ce1d99f5aed5b520cfe0deb5429ec8f2a88563763f566e77"
            "9814b7c310e5326edae31198eed439b845dd2db99eaa60f5c16a43f4be6bcf37",
            16
        )

    def test_unused_password(self, backend):
        key_file = os.path.join(
            "asymmetric", "Traditional_OpenSSL_Serialization", "testrsa.pem")
        password = b"this password will not be used"

        with pytest.raises(TypeError):
            load_vectors_from_file(
                key_file,
                lambda pemfile: load_pem_traditional_openssl_private_key(
                    pemfile.read().encode(), password, backend
                )
            )

    def test_wrong_password(self, backend):
        key_file = os.path.join(
            "asymmetric",
            "Traditional_OpenSSL_Serialization",
            "testrsa-encrypted.pem"
        )
        password = b"this password is wrong"

        with pytest.raises(ValueError):
            load_vectors_from_file(
                key_file,
                lambda pemfile: load_pem_traditional_openssl_private_key(
                    pemfile.read().encode(), password, backend
                )
            )

    @pytest.mark.parametrize("password", [None, b""])
    def test_missing_password(self, backend, password):
        key_file = os.path.join(
            "asymmetric",
            "Traditional_OpenSSL_Serialization",
            "testrsa-encrypted.pem"
        )

        with pytest.raises(TypeError):
            load_vectors_from_file(
                key_file,
                lambda pemfile: load_pem_traditional_openssl_private_key(
                    pemfile.read().encode(), password, backend
                )
            )

    def test_wrong_format(self, backend):
        key_data = b"---- NOT A KEY ----\n"

        with pytest.raises(ValueError):
            load_pem_traditional_openssl_private_key(
                key_data, None, backend
            )

        with pytest.raises(ValueError):
            load_pem_traditional_openssl_private_key(
                key_data, b"this password will not be used", backend
            )

    def test_corrupt_format(self, backend):
        # privkey.pem with a bunch of data missing.
        key_data = textwrap.dedent("""\
        -----BEGIN RSA PRIVATE KEY-----
        MIIBPAIBAAJBAKrbeqkuRk8VcRmWFmtP+LviMB3+6dizWW3DwaffznyHGAFwUJ/I
        Tv0XtbsCyl3QoyKGhrOAy3RvPK5M38iuXT0CAwEAAQJAZ3cnzaHXM/bxGaR5CR1R
        rD1qFBAVfoQFiOH9uPJgMaoAuoQEisPHVcZDKcOv4wEg6/TInAIXBnEigtqvRzuy
        mvcpHZwQJdmdHHkGKAs37Dfxi67HbkUCIQCeZGliHXFa071Fp06ZeWlR2ADonTZz
        rJBhdTe0v5pCeQIhAIZfkiGgGBX4cIuuckzEm43g9WMUjxP/0GlK39vIyihxAiEA
        mymehFRT0MvqW5xAKAx7Pgkt8HVKwVhc2LwGKHE0DZM=
        -----END RSA PRIVATE KEY-----
        """).encode()

        with pytest.raises(ValueError):
            load_pem_traditional_openssl_private_key(
                key_data, None, backend
            )

        with pytest.raises(ValueError):
            load_pem_traditional_openssl_private_key(
                key_data, b"this password will not be used", backend
            )

    def test_encrypted_corrupt_format(self, backend):
        # privkey.pem with a single bit flipped
        key_data = textwrap.dedent("""\
        -----BEGIN RSA PRIVATE KEY-----
        Proc-Type: <,ENCRYPTED
        DEK-Info: AES-128-CBC,5E22A2BD85A653FB7A3ED20DE84F54CD

        hAqtb5ZkTMGcs4BBDQ1SKZzdQThWRDzEDxM3qBfjvYa35KxZ54aic013mW/lwj2I
        v5bbpOjrHYHNAiZYZ7RNb+ztbF6F/g5PA5g7mFwEq+LFBY0InIplYBSv9QtE+lot
        Dy4AlZa/+NzJwgdKDb+JVfk5SddyD4ywnyeORnMPy4xXKvjXwmW+iLibZVKsjIgw
        H8hSxcD+FhWyJm9h9uLtmpuqhQo0jTUYpnTezZx2xeVPB53Ev7YCxR9Nsgj5GsVf
        9Z/hqLB7IFgM3pa0z3PQeUIZF/cEf72fISWIOBwwkzVrPUkXWfbuWeJXQXSs3amE
        5A295jD9BQp9CY0nNFSsy+qiXWToq2xT3y5zVNEStmN0SCGNaIlUnJzL9IHW+oMI
        kPmXZMnAYBWeeCF1gf3J3aE5lZInegHNfEI0+J0LazC2aNU5Dg/BNqrmRqKWEIo/
        -----END RSA PRIVATE KEY-----
        """).encode()

        password = b"this password is wrong"

        with pytest.raises(ValueError):
            load_pem_traditional_openssl_private_key(
                key_data, None, backend
            )

        with pytest.raises(ValueError):
            load_pem_traditional_openssl_private_key(
                key_data, password, backend
            )

    def test_unsupported_key_encryption(self, backend):
        key_data = textwrap.dedent("""\
        -----BEGIN RSA PRIVATE KEY-----
        Proc-Type: 4,ENCRYPTED
        DEK-Info: FAKE-123,5E22A2BD85A653FB7A3ED20DE84F54CD

        hAqtb5ZkTMGcs4BBDQ1SKZzdQThWRDzEDxM3qBfjvYa35KxZ54aic013mW/lwj2I
        v5bbpOjrHYHNAiZYZ7RNb+ztbF6F/g5PA5g7mFwEq+LFBY0InIplYBSv9QtE+lot
        Dy4AlZa/+NzJwgdKDb+JVfk5SddyD4ywnyeORnMPy4xXKvjXwmW+iLibZVKsjIgw
        H8hSxcD+FhWyJm9h9uLtmpuqhQo0jTUYpnTezZx2xeVPB53Ev7YCxR9Nsgj5GsVf
        9Z/hqLB7IFgM3pa0z3PQeUIZF/cEf72fISWIOBwwkzVrPUkXWfbuWeJXQXSs3amE
        5A295jD9BQp9CY0nNFSsy+qiXWToq2xT3y5zVNEStmN0SCGNaIlUnJzL9IHW+oMI
        kPmXZMnAYBWeeCF1gf3J3aE5lZInegHNfEI0+J0LazC2aNU5Dg/BNqrmRqKWEIo/
        -----END RSA PRIVATE KEY-----
        """).encode()

        password = b"password"

        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_CIPHER):
            load_pem_traditional_openssl_private_key(
                key_data, password, backend
            )


@pytest.mark.pkcs8_serialization
class TestPKCS8Serialisation(object):
    @pytest.mark.parametrize(
        ("key_file", "password"),
        [
            ("unencpkcs8.pem", None),
            ("encpkcs8.pem", b"foobar"),
            ("enc2pkcs8.pem", b"baz"),
            ("pkcs12_s2k_pem-X_9607.pem", b"123456"),
            ("pkcs12_s2k_pem-X_9671.pem", b"123456"),
            ("pkcs12_s2k_pem-X_9925.pem", b"123456"),
            ("pkcs12_s2k_pem-X_9926.pem", b"123456"),
            ("pkcs12_s2k_pem-X_9927.pem", b"123456"),
            ("pkcs12_s2k_pem-X_9928.pem", b"123456"),
            ("pkcs12_s2k_pem-X_9929.pem", b"123456"),
            ("pkcs12_s2k_pem-X_9930.pem", b"123456"),
            ("pkcs12_s2k_pem-X_9931.pem", b"123456"),
            ("pkcs12_s2k_pem-X_9932.pem", b"123456"),
        ]
    )
    def test_load_pem_rsa_private_key(self, key_file, password, backend):
        key = load_vectors_from_file(
            os.path.join(
                "asymmetric", "PKCS8", key_file),
            lambda pemfile: load_pem_pkcs8_private_key(
                pemfile.read().encode(), password, backend
            )
        )

        assert key
        assert isinstance(key, rsa.RSAPrivateKey)
        _check_rsa_private_key(key)

    def test_unused_password(self, backend):
        key_file = os.path.join(
            "asymmetric", "PKCS8", "unencpkcs8.pem")
        password = b"this password will not be used"

        with pytest.raises(TypeError):
            load_vectors_from_file(
                key_file,
                lambda pemfile: load_pem_pkcs8_private_key(
                    pemfile.read().encode(), password, backend
                )
            )

    def test_wrong_password(self, backend):
        key_file = os.path.join(
            "asymmetric", "PKCS8", "encpkcs8.pem")
        password = b"this password is wrong"

        with pytest.raises(ValueError):
            load_vectors_from_file(
                key_file,
                lambda pemfile: load_pem_pkcs8_private_key(
                    pemfile.read().encode(), password, backend
                )
            )

    @pytest.mark.parametrize("password", [None, b""])
    def test_missing_password(self, backend, password):
        key_file = os.path.join(
            "asymmetric",
            "PKCS8",
            "encpkcs8.pem"
        )

        with pytest.raises(TypeError):
            load_vectors_from_file(
                key_file,
                lambda pemfile: load_pem_pkcs8_private_key(
                    pemfile.read().encode(), password, backend
                )
            )

    def test_wrong_format(self, backend):
        key_data = b"---- NOT A KEY ----\n"

        with pytest.raises(ValueError):
            load_pem_pkcs8_private_key(
                key_data, None, backend
            )

        with pytest.raises(ValueError):
            load_pem_pkcs8_private_key(
                key_data, b"this password will not be used", backend
            )

    def test_corrupt_format(self, backend):
        # unencpkcs8.pem with a bunch of data missing.
        key_data = textwrap.dedent("""\
        -----BEGIN PRIVATE KEY-----
        MIICdQIBADALBgkqhkiG9w0BAQEEggJhMIICXQIBAAKBgQC7JHoJfg6yNzLMOWet
        8Z49a4KD0dCspMAYvo2YAMB7/wdEycocujbhJ2n/seONi+5XqTqqFkM5VBl8rmkk
        FPZk/7x0xmdsTPECSWnHK+HhoaNDFPR3j8jQhVo1laxiqcEhAHegi5cwtFosuJAv
        FiRC0Cgz+frQPFQEBsAV9RuasyQxqzxrR0Ow0qncBeGBWbYE6WZhqtcLAI895b+i
        +F4lbB4iD7T9QeIDMU/aIMXA81UO4cns1z4qDAHKeyLLrPQrJ/B4X7XC+egUWm5+
        hr1qmyAMusyXIBECQQDJWZ8piluf4yrYfsJAn6hF5T4RjTztbqvO0GVG2McHY7Uj
        NPSffhzHx/ll0fQEQji+OgydCCX8o3HZrgw5YfSJAkEA7e+rqdU5nO5ZG//PSEQb
        tjLnRiTzBH/elQhtdZ5nF7pcpNTi4k13zutmKcWW4GK75azcRGJUhu1kDM7QYAOd
        SQJAVNkYcifkvna7GmooL5VYEsQsqLbM4v0NF2TIGNfG3z1MGp75KrC5LhL97MNR
        we2p/bd2k0HYyCKUGnf2nMPDiQJBAI75pwittSoE240EobUGIDTSz8CJsXIxuDmL
        z+KOpdpPRR5TQmbEMEspjsFpFymMiuYPgmihQbO2cJl1qScY5OkCQQCJ6m5tcN8l
        Xxg/SNpjEIv+qAyUD96XVlOJlOIeLHQ8kYE0C6ZA+MsqYIzgAreJk88Yn0lU/X0/
        mu/UpE/BRZmR
        -----END PRIVATE KEY-----
        """).encode()

        with pytest.raises(ValueError):
            load_pem_pkcs8_private_key(
                key_data, None, backend
            )

        with pytest.raises(ValueError):
            load_pem_pkcs8_private_key(
                key_data, b"this password will not be used", backend
            )

    def test_encrypted_corrupt_format(self, backend):
        # encpkcs8.pem with some bits flipped.
        key_data = textwrap.dedent("""\
        -----BEGIN ENCRYPTED PRIVATE KEY-----
        MIICojAcBgoqhkiG9w0BDAEDMA4ECHK0M0+QuEL9AgIBIcSCAoDRq+KRY+0XP0tO
        lwBTzViiXSXoyNnKAZKt5r5K/fGNntv22g/1s/ZNCetrqsJDC5eMUPPacz06jFq/
        Ipsep4/OgjQ9UAOzXNrWEoNyrHnWDo7usgD3CW0mKyqER4+wG0adVMbt3N+CJHGB
        85jzRmQTfkdx1rSWeSx+XyswHn8ER4+hQ+omKWMVm7AFkjjmP/KnhUnLT98J8rhU
        ArQoFPHz/6HVkypFccNaPPNg6IA4aS2A+TU9vJYOaXSVfFB2yf99hfYYzC+ukmuU
        5Lun0cysK5s/5uSwDueUmDQKspnaNyiaMGDxvw8hilJc7vg0fGObfnbIpizhxJwq
        gKBfR7Zt0Hv8OYi1He4MehfMGdbHskztF+yQ40LplBGXQrvAqpU4zShga1BoQ98T
        0ekbBmqj7hg47VFsppXR7DKhx7G7rpMmdKbFhAZVCjae7rRGpUtD52cpFdPhMyAX
        huhMkoczwUW8B/rM4272lkHo6Br0yk/TQfTEGkvryflNVu6lniPTV151WV5U1M3o
        3G3a44eDyt7Ln+WSOpWtbPQMTrpKhur6WXgJvrpa/m02oOGdvOlDsoOCgavgQMWg
        7xKKL7620pHl7p7f/8tlE8q6vLXVvyNtAOgt/JAr2rgvrHaZSzDE0DwgCjBXEm+7
        cVMVNkHod7bLQefVanVtWqPzbmr8f7gKeuGwWSG9oew/lN2hxcLEPJHAQlnLgx3P
        0GdGjK9NvwA0EP2gYIeE4+UtSder7xQ7bVh25VB20R4TTIIs4aXXCVOoQPagnzaT
        6JLgl8FrvdfjHwIvmSOO1YMNmILBq000Q8WDqyErBDs4hsvtO6VQ4LeqJj6gClX3
        qeJNaJFu
        -----END ENCRYPTED PRIVATE KEY-----
        """).encode()

        password = b"this password is wrong"

        with pytest.raises(ValueError):
            load_pem_pkcs8_private_key(
                key_data, None, backend
            )

        with pytest.raises(ValueError):
            load_pem_pkcs8_private_key(
                key_data, password, backend
            )

    def test_key1_pem_encrypted_values(self, backend):
        pkey = load_vectors_from_file(
            os.path.join(
                "asymmetric", "PKCS8", "encpkcs8.pem"),
            lambda pemfile: load_pem_pkcs8_private_key(
                pemfile.read().encode(), b"foobar", backend
            )
        )
        assert pkey

        assert pkey.modulus == int(
            "00beec64d6db5760ac2fd4c971145641b9bd7f5c56558ece608795c79807"
            "376a7fe5b19f95b35ca358ea5c8abd7ae051d49cd2f1e45969a1ae945460"
            "3c14b278664a0e414ebc8913acb6203626985525e17a600611b028542dd0"
            "562aad787fb4f1650aa318cdcff751e1b187cbf6785fbe164e9809491b95"
            "dd68480567c99b1a57", 16
        )

        assert pkey.public_exponent == 65537

        assert pkey.private_exponent == int(
            "0cfe316e9dc6b8817f4fcfd5ae38a0886f68f773b8a6db4c9e6d8703c599"
            "f3d9785c3a2c09e4c8090909fb3721e19a3009ec21221523a729265707a5"
            "8f13063671c42a4096cad378ef2510cb59e23071489d8893ac4934dd149f"
            "34f2d094bea57f1c8027c3a77248ac9b91218737d0c3c3dfa7d7829e6977"
            "cf7d995688c86c81", 16
        )

        assert pkey.p == int(
            "00db122ac857b2c0437d7616daa98e597bb75ca9ad3a47a70bec10c10036"
            "03328794b225c8e3eee6ffd3fd6d2253d28e071fe27d629ab072faa14377"
            "ce6118cb67", 16
        )

        assert pkey.q == int(
            "00df1b8aa8506fcbbbb9d00257f2975e38b33d2698fd0f37e82d7ef38c56"
            "f21b6ced63c825383782a7115cfcc093300987dbd2853b518d1c8f26382a"
            "2d2586d391", 16
        )

        assert pkey.dmp1 == int(
            "00be18aca13e60712fdf5daa85421eb10d86d654b269e1255656194fb0c4"
            "2dd01a1070ea12c19f5c39e09587af02f7b1a1030d016a9ffabf3b36d699"
            "ceaf38d9bf", 16
        )

        assert pkey.dmq1 == int(
            "71aa8978f90a0c050744b77cf1263725b203ac9f730606d8ae1d289dce4a"
            "28b8d534e9ea347aeb808c73107e583eb80c546d2bddadcdb3c82693a4c1"
            "3d863451", 16
        )

        assert pkey.iqmp == int(
            "136b7b1afac6e6279f71b24217b7083485a5e827d156024609dae39d48a6"
            "bdb55af2f062cc4a3b077434e6fffad5faa29a2b5dba2bed3e4621e478c0"
            "97ccfe7f", 16
        )

    @pytest.mark.parametrize(
        ("key_file", "password"),
        [
            ("unenc-dsa-pkcs8.pem", None),
        ]
    )
    def test_load_pem_dsa_private_key(self, key_file, password, backend):
        key = load_vectors_from_file(
            os.path.join(
                "asymmetric", "PKCS8", key_file),
            lambda pemfile: load_pem_traditional_openssl_private_key(
                pemfile.read().encode(), password, backend
            )
        )
        assert key
        assert isinstance(key, dsa.DSAPrivateKey)

        params = key.parameters()
        assert isinstance(params, dsa.DSAParameters)

        assert key.x == int("00a535a8e1d0d91beafc8bee1d9b2a3a8de3311203", 16)
        assert key.y == int(
            "2b260ea97dc6a12ae932c640e7df3d8ff04a8a05a0324f8d5f1b23f15fa1"
            "70ff3f42061124eff2586cb11b49a82dcdc1b90fc6a84fb10109cb67db5d"
            "2da971aeaf17be5e37284563e4c64d9e5fc8480258b319f0de29d54d8350"
            "70d9e287914d77df81491f4423b62da984eb3f45eb2a29fcea5dae525ac6"
            "ab6bcce04bfdf5b6",
            16
        )

        assert params.p == int(
            "00aa0930cc145825221caffa28ac2894196a27833de5ec21270791689420"
            "7774a2e7b238b0d36f1b2499a2c2585083eb01432924418d867faa212dd1"
            "071d4dceb2782794ad393cc08a4d4ada7f68d6e839a5fcd34b4e402d82cb"
            "8a8cb40fec31911bf9bd360b034caacb4c5e947992573c9e90099c1b0f05"
            "940cabe5d2de49a167",
            16
        )

        assert params.q == int("00adc0e869b36f0ac013a681fdf4d4899d69820451",
                               16)

        assert params.g == int(
            "008c6b4589afa53a4d1048bfc346d1f386ca75521ccf72ddaa251286880e"
            "e13201ff48890bbfc33d79bacaec71e7a778507bd5f1a66422e39415be03"
            "e71141ba324f5b93131929182c88a9fa4062836066cebe74b5c6690c7d10"
            "1106c240ab7ebd54e4e3301fd086ce6adac922fb2713a2b0887cba13b9bc"
            "68ce5cfff241cd3246",
            16
        )

    @pytest.mark.parametrize(
        ("key_file", "password"),
        [
            ("bad-oid-dsa-key.pem", None),
        ]
    )
    def test_load_bad_oid_key(self, key_file, password, backend):
        with raises_unsupported_algorithm(
            _Reasons.UNSUPPORTED_PUBLIC_KEY_ALGORITHM
        ):
            load_vectors_from_file(
                os.path.join(
                    "asymmetric", "PKCS8", key_file),
                lambda pemfile: load_pem_traditional_openssl_private_key(
                    pemfile.read().encode(), password, backend
                )
            )

    @pytest.mark.parametrize(
        ("key_file", "password"),
        [
            ("bad-encryption-oid.pem", b"password"),
        ]
    )
    def test_load_bad_encryption_oid_key(self, key_file, password, backend):
        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_CIPHER):
            load_vectors_from_file(
                os.path.join(
                    "asymmetric", "PKCS8", key_file),
                lambda pemfile: load_pem_traditional_openssl_private_key(
                    pemfile.read().encode(), password, backend
                )
            )

########NEW FILE########
__FILENAME__ = test_hotp
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import os

import pytest

from cryptography.exceptions import InvalidToken, _Reasons
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.hashes import MD5, SHA1
from cryptography.hazmat.primitives.twofactor.hotp import HOTP

from ....utils import (
    load_nist_vectors, load_vectors_from_file, raises_unsupported_algorithm
)

vectors = load_vectors_from_file(
    "twofactor/rfc-4226.txt", load_nist_vectors)


@pytest.mark.supported(
    only_if=lambda backend: backend.hmac_supported(hashes.SHA1()),
    skip_message="Does not support HMAC-SHA1."
)
@pytest.mark.hmac
class TestHOTP(object):
    def test_invalid_key_length(self, backend):
        secret = os.urandom(10)

        with pytest.raises(ValueError):
            HOTP(secret, 6, SHA1(), backend)

    def test_invalid_hotp_length(self, backend):
        secret = os.urandom(16)

        with pytest.raises(ValueError):
            HOTP(secret, 4, SHA1(), backend)

    def test_invalid_algorithm(self, backend):
        secret = os.urandom(16)

        with pytest.raises(TypeError):
            HOTP(secret, 6, MD5(), backend)

    @pytest.mark.parametrize("params", vectors)
    def test_truncate(self, backend, params):
        secret = params["secret"]
        counter = int(params["counter"])
        truncated = params["truncated"]

        hotp = HOTP(secret, 6, SHA1(), backend)

        assert hotp._dynamic_truncate(counter) == int(truncated.decode(), 16)

    @pytest.mark.parametrize("params", vectors)
    def test_generate(self, backend, params):
        secret = params["secret"]
        counter = int(params["counter"])
        hotp_value = params["hotp"]

        hotp = HOTP(secret, 6, SHA1(), backend)

        assert hotp.generate(counter) == hotp_value

    @pytest.mark.parametrize("params", vectors)
    def test_verify(self, backend, params):
        secret = params["secret"]
        counter = int(params["counter"])
        hotp_value = params["hotp"]

        hotp = HOTP(secret, 6, SHA1(), backend)

        assert hotp.verify(hotp_value, counter) is None

    def test_invalid_verify(self, backend):
        secret = b"12345678901234567890"
        counter = 0

        hotp = HOTP(secret, 6, SHA1(), backend)

        with pytest.raises(InvalidToken):
            hotp.verify(b"123456", counter)

    def test_length_not_int(self, backend):
        secret = b"12345678901234567890"

        with pytest.raises(TypeError):
            HOTP(secret, b"foo", SHA1(), backend)


def test_invalid_backend():
    secret = b"12345678901234567890"

    pretend_backend = object()

    with raises_unsupported_algorithm(_Reasons.BACKEND_MISSING_INTERFACE):
        HOTP(secret, 8, hashes.SHA1(), pretend_backend)

########NEW FILE########
__FILENAME__ = test_totp
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import pytest

from cryptography.exceptions import InvalidToken, _Reasons
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.twofactor.totp import TOTP

from ....utils import (
    load_nist_vectors, load_vectors_from_file, raises_unsupported_algorithm
)

vectors = load_vectors_from_file(
    "twofactor/rfc-6238.txt", load_nist_vectors)


@pytest.mark.hmac
class TestTOTP(object):
    @pytest.mark.supported(
        only_if=lambda backend: backend.hmac_supported(hashes.SHA1()),
        skip_message="Does not support HMAC-SHA1."
    )
    @pytest.mark.parametrize(
        "params", [i for i in vectors if i["mode"] == b"SHA1"])
    def test_generate_sha1(self, backend, params):
        secret = params["secret"]
        time = int(params["time"])
        totp_value = params["totp"]

        totp = TOTP(secret, 8, hashes.SHA1(), 30, backend)
        assert totp.generate(time) == totp_value

    @pytest.mark.supported(
        only_if=lambda backend: backend.hmac_supported(hashes.SHA256()),
        skip_message="Does not support HMAC-SHA256."
    )
    @pytest.mark.parametrize(
        "params", [i for i in vectors if i["mode"] == b"SHA256"])
    def test_generate_sha256(self, backend, params):
        secret = params["secret"]
        time = int(params["time"])
        totp_value = params["totp"]

        totp = TOTP(secret, 8, hashes.SHA256(), 30, backend)
        assert totp.generate(time) == totp_value

    @pytest.mark.supported(
        only_if=lambda backend: backend.hmac_supported(hashes.SHA512()),
        skip_message="Does not support HMAC-SHA512."
    )
    @pytest.mark.parametrize(
        "params", [i for i in vectors if i["mode"] == b"SHA512"])
    def test_generate_sha512(self, backend, params):
        secret = params["secret"]
        time = int(params["time"])
        totp_value = params["totp"]

        totp = TOTP(secret, 8, hashes.SHA512(), 30, backend)
        assert totp.generate(time) == totp_value

    @pytest.mark.supported(
        only_if=lambda backend: backend.hmac_supported(hashes.SHA1()),
        skip_message="Does not support HMAC-SHA1."
    )
    @pytest.mark.parametrize(
        "params", [i for i in vectors if i["mode"] == b"SHA1"])
    def test_verify_sha1(self, backend, params):
        secret = params["secret"]
        time = int(params["time"])
        totp_value = params["totp"]

        totp = TOTP(secret, 8, hashes.SHA1(), 30, backend)

        assert totp.verify(totp_value, time) is None

    @pytest.mark.supported(
        only_if=lambda backend: backend.hmac_supported(hashes.SHA256()),
        skip_message="Does not support HMAC-SHA256."
    )
    @pytest.mark.parametrize(
        "params", [i for i in vectors if i["mode"] == b"SHA256"])
    def test_verify_sha256(self, backend, params):
        secret = params["secret"]
        time = int(params["time"])
        totp_value = params["totp"]

        totp = TOTP(secret, 8, hashes.SHA256(), 30, backend)

        assert totp.verify(totp_value, time) is None

    @pytest.mark.supported(
        only_if=lambda backend: backend.hmac_supported(hashes.SHA512()),
        skip_message="Does not support HMAC-SHA512."
    )
    @pytest.mark.parametrize(
        "params", [i for i in vectors if i["mode"] == b"SHA512"])
    def test_verify_sha512(self, backend, params):
        secret = params["secret"]
        time = int(params["time"])
        totp_value = params["totp"]

        totp = TOTP(secret, 8, hashes.SHA512(), 30, backend)

        assert totp.verify(totp_value, time) is None

    def test_invalid_verify(self, backend):
        secret = b"12345678901234567890"
        time = 59

        totp = TOTP(secret, 8, hashes.SHA1(), 30, backend)

        with pytest.raises(InvalidToken):
            totp.verify(b"12345678", time)

    def test_floating_point_time_generate(self, backend):
        secret = b"12345678901234567890"
        time = 59.1

        totp = TOTP(secret, 8, hashes.SHA1(), 30, backend)

        assert totp.generate(time) == b"94287082"


def test_invalid_backend():
    secret = b"12345678901234567890"

    pretend_backend = object()

    with raises_unsupported_algorithm(_Reasons.BACKEND_MISSING_INTERFACE):
        TOTP(secret, 8, hashes.SHA1(), 30, pretend_backend)

########NEW FILE########
__FILENAME__ = utils
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import binascii
import itertools
import os

import pytest

from cryptography.exceptions import (
    AlreadyFinalized, AlreadyUpdated, InvalidSignature, InvalidTag,
    NotYetFinalized
)
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.kdf.hkdf import HKDF, HKDFExpand
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ...utils import load_vectors_from_file


def _load_all_params(path, file_names, param_loader):
    all_params = []
    for file_name in file_names:
        all_params.extend(
            load_vectors_from_file(os.path.join(path, file_name), param_loader)
        )
    return all_params


def generate_encrypt_test(param_loader, path, file_names, cipher_factory,
                          mode_factory):
    all_params = _load_all_params(path, file_names, param_loader)

    @pytest.mark.parametrize("params", all_params)
    def test_encryption(self, backend, params):
        encrypt_test(backend, cipher_factory, mode_factory, params)

    return test_encryption


def encrypt_test(backend, cipher_factory, mode_factory, params):
    plaintext = params["plaintext"]
    ciphertext = params["ciphertext"]
    cipher = Cipher(
        cipher_factory(**params),
        mode_factory(**params),
        backend=backend
    )
    encryptor = cipher.encryptor()
    actual_ciphertext = encryptor.update(binascii.unhexlify(plaintext))
    actual_ciphertext += encryptor.finalize()
    assert actual_ciphertext == binascii.unhexlify(ciphertext)
    decryptor = cipher.decryptor()
    actual_plaintext = decryptor.update(binascii.unhexlify(ciphertext))
    actual_plaintext += decryptor.finalize()
    assert actual_plaintext == binascii.unhexlify(plaintext)


def generate_aead_test(param_loader, path, file_names, cipher_factory,
                       mode_factory):
    all_params = _load_all_params(path, file_names, param_loader)

    @pytest.mark.parametrize("params", all_params)
    def test_aead(self, backend, params):
        aead_test(backend, cipher_factory, mode_factory, params)

    return test_aead


def aead_test(backend, cipher_factory, mode_factory, params):
    if params.get("pt") is not None:
        plaintext = params["pt"]
    ciphertext = params["ct"]
    aad = params["aad"]
    if params.get("fail") is True:
        cipher = Cipher(
            cipher_factory(binascii.unhexlify(params["key"])),
            mode_factory(binascii.unhexlify(params["iv"]),
                         binascii.unhexlify(params["tag"])),
            backend
        )
        decryptor = cipher.decryptor()
        decryptor.authenticate_additional_data(binascii.unhexlify(aad))
        actual_plaintext = decryptor.update(binascii.unhexlify(ciphertext))
        with pytest.raises(InvalidTag):
            decryptor.finalize()
    else:
        cipher = Cipher(
            cipher_factory(binascii.unhexlify(params["key"])),
            mode_factory(binascii.unhexlify(params["iv"]), None),
            backend
        )
        encryptor = cipher.encryptor()
        encryptor.authenticate_additional_data(binascii.unhexlify(aad))
        actual_ciphertext = encryptor.update(binascii.unhexlify(plaintext))
        actual_ciphertext += encryptor.finalize()
        tag_len = len(params["tag"])
        assert binascii.hexlify(encryptor.tag)[:tag_len] == params["tag"]
        cipher = Cipher(
            cipher_factory(binascii.unhexlify(params["key"])),
            mode_factory(binascii.unhexlify(params["iv"]),
                         binascii.unhexlify(params["tag"])),
            backend
        )
        decryptor = cipher.decryptor()
        decryptor.authenticate_additional_data(binascii.unhexlify(aad))
        actual_plaintext = decryptor.update(binascii.unhexlify(ciphertext))
        actual_plaintext += decryptor.finalize()
        assert actual_plaintext == binascii.unhexlify(plaintext)


def generate_stream_encryption_test(param_loader, path, file_names,
                                    cipher_factory):
    all_params = _load_all_params(path, file_names, param_loader)

    @pytest.mark.parametrize("params", all_params)
    def test_stream_encryption(self, backend, params):
        stream_encryption_test(backend, cipher_factory, params)
    return test_stream_encryption


def stream_encryption_test(backend, cipher_factory, params):
    plaintext = params["plaintext"]
    ciphertext = params["ciphertext"]
    offset = params["offset"]
    cipher = Cipher(cipher_factory(**params), None, backend=backend)
    encryptor = cipher.encryptor()
    # throw away offset bytes
    encryptor.update(b"\x00" * int(offset))
    actual_ciphertext = encryptor.update(binascii.unhexlify(plaintext))
    actual_ciphertext += encryptor.finalize()
    assert actual_ciphertext == binascii.unhexlify(ciphertext)
    decryptor = cipher.decryptor()
    decryptor.update(b"\x00" * int(offset))
    actual_plaintext = decryptor.update(binascii.unhexlify(ciphertext))
    actual_plaintext += decryptor.finalize()
    assert actual_plaintext == binascii.unhexlify(plaintext)


def generate_hash_test(param_loader, path, file_names, hash_cls):
    all_params = _load_all_params(path, file_names, param_loader)

    @pytest.mark.parametrize("params", all_params)
    def test_hash(self, backend, params):
        hash_test(backend, hash_cls, params)
    return test_hash


def hash_test(backend, algorithm, params):
    msg, md = params
    m = hashes.Hash(algorithm, backend=backend)
    m.update(binascii.unhexlify(msg))
    expected_md = md.replace(" ", "").lower().encode("ascii")
    assert m.finalize() == binascii.unhexlify(expected_md)


def generate_base_hash_test(algorithm, digest_size, block_size):
    def test_base_hash(self, backend):
        base_hash_test(backend, algorithm, digest_size, block_size)
    return test_base_hash


def base_hash_test(backend, algorithm, digest_size, block_size):
    m = hashes.Hash(algorithm, backend=backend)
    assert m.algorithm.digest_size == digest_size
    assert m.algorithm.block_size == block_size
    m_copy = m.copy()
    assert m != m_copy
    assert m._ctx != m_copy._ctx

    m.update(b"abc")
    copy = m.copy()
    copy.update(b"123")
    m.update(b"123")
    assert copy.finalize() == m.finalize()


def generate_long_string_hash_test(hash_factory, md):
    def test_long_string_hash(self, backend):
        long_string_hash_test(backend, hash_factory, md)
    return test_long_string_hash


def long_string_hash_test(backend, algorithm, md):
    m = hashes.Hash(algorithm, backend=backend)
    m.update(b"a" * 1000000)
    assert m.finalize() == binascii.unhexlify(md.lower().encode("ascii"))


def generate_base_hmac_test(hash_cls):
    def test_base_hmac(self, backend):
        base_hmac_test(backend, hash_cls)
    return test_base_hmac


def base_hmac_test(backend, algorithm):
    key = b"ab"
    h = hmac.HMAC(binascii.unhexlify(key), algorithm, backend=backend)
    h_copy = h.copy()
    assert h != h_copy
    assert h._ctx != h_copy._ctx


def generate_hmac_test(param_loader, path, file_names, algorithm):
    all_params = _load_all_params(path, file_names, param_loader)

    @pytest.mark.parametrize("params", all_params)
    def test_hmac(self, backend, params):
        hmac_test(backend, algorithm, params)
    return test_hmac


def hmac_test(backend, algorithm, params):
    msg, md, key = params
    h = hmac.HMAC(binascii.unhexlify(key), algorithm, backend=backend)
    h.update(binascii.unhexlify(msg))
    assert h.finalize() == binascii.unhexlify(md.encode("ascii"))


def generate_pbkdf2_test(param_loader, path, file_names, algorithm):
    all_params = _load_all_params(path, file_names, param_loader)

    @pytest.mark.parametrize("params", all_params)
    def test_pbkdf2(self, backend, params):
        pbkdf2_test(backend, algorithm, params)
    return test_pbkdf2


def pbkdf2_test(backend, algorithm, params):
    # Password and salt can contain \0, which should be loaded as a null char.
    # The NIST loader loads them as literal strings so we replace with the
    # proper value.
    kdf = PBKDF2HMAC(
        algorithm,
        int(params["length"]),
        params["salt"],
        int(params["iterations"]),
        backend
    )
    derived_key = kdf.derive(params["password"])
    assert binascii.hexlify(derived_key) == params["derived_key"]


def generate_aead_exception_test(cipher_factory, mode_factory):
    def test_aead_exception(self, backend):
        aead_exception_test(backend, cipher_factory, mode_factory)
    return test_aead_exception


def aead_exception_test(backend, cipher_factory, mode_factory):
    cipher = Cipher(
        cipher_factory(binascii.unhexlify(b"0" * 32)),
        mode_factory(binascii.unhexlify(b"0" * 24)),
        backend
    )
    encryptor = cipher.encryptor()
    encryptor.update(b"a" * 16)
    with pytest.raises(NotYetFinalized):
        encryptor.tag
    with pytest.raises(AlreadyUpdated):
        encryptor.authenticate_additional_data(b"b" * 16)
    encryptor.finalize()
    with pytest.raises(AlreadyFinalized):
        encryptor.authenticate_additional_data(b"b" * 16)
    with pytest.raises(AlreadyFinalized):
        encryptor.update(b"b" * 16)
    with pytest.raises(AlreadyFinalized):
        encryptor.finalize()
    cipher = Cipher(
        cipher_factory(binascii.unhexlify(b"0" * 32)),
        mode_factory(binascii.unhexlify(b"0" * 24), b"0" * 16),
        backend
    )
    decryptor = cipher.decryptor()
    decryptor.update(b"a" * 16)
    with pytest.raises(AttributeError):
        decryptor.tag


def generate_aead_tag_exception_test(cipher_factory, mode_factory):
    def test_aead_tag_exception(self, backend):
        aead_tag_exception_test(backend, cipher_factory, mode_factory)
    return test_aead_tag_exception


def aead_tag_exception_test(backend, cipher_factory, mode_factory):
    cipher = Cipher(
        cipher_factory(binascii.unhexlify(b"0" * 32)),
        mode_factory(binascii.unhexlify(b"0" * 24)),
        backend
    )
    with pytest.raises(ValueError):
        cipher.decryptor()

    with pytest.raises(ValueError):
        mode_factory(binascii.unhexlify(b"0" * 24), b"000")

    cipher = Cipher(
        cipher_factory(binascii.unhexlify(b"0" * 32)),
        mode_factory(binascii.unhexlify(b"0" * 24), b"0" * 16),
        backend
    )
    with pytest.raises(ValueError):
        cipher.encryptor()


def hkdf_derive_test(backend, algorithm, params):
    hkdf = HKDF(
        algorithm,
        int(params["l"]),
        salt=binascii.unhexlify(params["salt"]) or None,
        info=binascii.unhexlify(params["info"]) or None,
        backend=backend
    )

    okm = hkdf.derive(binascii.unhexlify(params["ikm"]))

    assert okm == binascii.unhexlify(params["okm"])


def hkdf_extract_test(backend, algorithm, params):
    hkdf = HKDF(
        algorithm,
        int(params["l"]),
        salt=binascii.unhexlify(params["salt"]) or None,
        info=binascii.unhexlify(params["info"]) or None,
        backend=backend
    )

    prk = hkdf._extract(binascii.unhexlify(params["ikm"]))

    assert prk == binascii.unhexlify(params["prk"])


def hkdf_expand_test(backend, algorithm, params):
    hkdf = HKDFExpand(
        algorithm,
        int(params["l"]),
        info=binascii.unhexlify(params["info"]) or None,
        backend=backend
    )

    okm = hkdf.derive(binascii.unhexlify(params["prk"]))

    assert okm == binascii.unhexlify(params["okm"])


def generate_hkdf_test(param_loader, path, file_names, algorithm):
    all_params = _load_all_params(path, file_names, param_loader)

    all_tests = [hkdf_extract_test, hkdf_expand_test, hkdf_derive_test]

    @pytest.mark.parametrize(
        ("params", "hkdf_test"),
        itertools.product(all_params, all_tests)
    )
    def test_hkdf(self, backend, params, hkdf_test):
        hkdf_test(backend, algorithm, params)

    return test_hkdf


def generate_rsa_verification_test(param_loader, path, file_names, hash_alg,
                                   pad_factory):
    all_params = _load_all_params(path, file_names, param_loader)
    all_params = [i for i in all_params
                  if i["algorithm"] == hash_alg.name.upper()]

    @pytest.mark.parametrize("params", all_params)
    def test_rsa_verification(self, backend, params):
        rsa_verification_test(backend, params, hash_alg, pad_factory)

    return test_rsa_verification


def rsa_verification_test(backend, params, hash_alg, pad_factory):
    public_key = rsa.RSAPublicKey(
        public_exponent=params["public_exponent"],
        modulus=params["modulus"]
    )
    pad = pad_factory(params, hash_alg)
    verifier = public_key.verifier(
        binascii.unhexlify(params["s"]),
        pad,
        hash_alg,
        backend
    )
    verifier.update(binascii.unhexlify(params["msg"]))
    if params["fail"]:
        with pytest.raises(InvalidSignature):
            verifier.verify()
    else:
        verifier.verify()


def _check_rsa_private_key(skey):
    assert skey
    assert skey.modulus
    assert skey.public_exponent
    assert skey.private_exponent
    assert skey.p * skey.q == skey.modulus
    assert skey.key_size
    assert skey.dmp1 == rsa.rsa_crt_dmp1(skey.d, skey.p)
    assert skey.dmq1 == rsa.rsa_crt_dmq1(skey.d, skey.q)
    assert skey.iqmp == rsa.rsa_crt_iqmp(skey.p, skey.q)

    pkey = skey.public_key()
    assert pkey
    assert skey.modulus == pkey.modulus
    assert skey.public_exponent == pkey.public_exponent
    assert skey.key_size == pkey.key_size

########NEW FILE########
__FILENAME__ = test_fernet
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import base64
import calendar
import json
import time

import iso8601

import pytest

import six

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import algorithms, modes

import cryptography_vectors


def json_parametrize(keys, filename):
    vector_file = cryptography_vectors.open_vector_file('fernet', filename)
    with vector_file:
        data = json.load(vector_file)
        return pytest.mark.parametrize(keys, [
            tuple([entry[k] for k in keys])
            for entry in data
        ])


@pytest.mark.cipher
class TestFernet(object):
    @pytest.mark.supported(
        only_if=lambda backend: backend.cipher_supported(
            algorithms.AES("\x00" * 32), modes.CBC("\x00" * 16)
        ),
        skip_message="Does not support AES CBC",
    )
    @json_parametrize(
        ("secret", "now", "iv", "src", "token"), "generate.json",
    )
    def test_generate(self, secret, now, iv, src, token, backend):
        f = Fernet(secret.encode("ascii"), backend=backend)
        actual_token = f._encrypt_from_parts(
            src.encode("ascii"),
            calendar.timegm(iso8601.parse_date(now).utctimetuple()),
            b"".join(map(six.int2byte, iv))
        )
        assert actual_token == token.encode("ascii")

    @pytest.mark.supported(
        only_if=lambda backend: backend.cipher_supported(
            algorithms.AES("\x00" * 32), modes.CBC("\x00" * 16)
        ),
        skip_message="Does not support AES CBC",
    )
    @json_parametrize(
        ("secret", "now", "src", "ttl_sec", "token"), "verify.json",
    )
    def test_verify(self, secret, now, src, ttl_sec, token, backend,
                    monkeypatch):
        f = Fernet(secret.encode("ascii"), backend=backend)
        current_time = calendar.timegm(iso8601.parse_date(now).utctimetuple())
        monkeypatch.setattr(time, "time", lambda: current_time)
        payload = f.decrypt(token.encode("ascii"), ttl=ttl_sec)
        assert payload == src.encode("ascii")

    @pytest.mark.supported(
        only_if=lambda backend: backend.cipher_supported(
            algorithms.AES("\x00" * 32), modes.CBC("\x00" * 16)
        ),
        skip_message="Does not support AES CBC",
    )
    @json_parametrize(("secret", "token", "now", "ttl_sec"), "invalid.json")
    def test_invalid(self, secret, token, now, ttl_sec, backend, monkeypatch):
        f = Fernet(secret.encode("ascii"), backend=backend)
        current_time = calendar.timegm(iso8601.parse_date(now).utctimetuple())
        monkeypatch.setattr(time, "time", lambda: current_time)
        with pytest.raises(InvalidToken):
            f.decrypt(token.encode("ascii"), ttl=ttl_sec)

    @pytest.mark.supported(
        only_if=lambda backend: backend.cipher_supported(
            algorithms.AES("\x00" * 32), modes.CBC("\x00" * 16)
        ),
        skip_message="Does not support AES CBC",
    )
    def test_invalid_start_byte(self, backend):
        f = Fernet(Fernet.generate_key(), backend=backend)
        with pytest.raises(InvalidToken):
            f.decrypt(base64.urlsafe_b64encode(b"\x81"))

    @pytest.mark.supported(
        only_if=lambda backend: backend.cipher_supported(
            algorithms.AES("\x00" * 32), modes.CBC("\x00" * 16)
        ),
        skip_message="Does not support AES CBC",
    )
    def test_timestamp_too_short(self, backend):
        f = Fernet(Fernet.generate_key(), backend=backend)
        with pytest.raises(InvalidToken):
            f.decrypt(base64.urlsafe_b64encode(b"\x80abc"))

    @pytest.mark.supported(
        only_if=lambda backend: backend.cipher_supported(
            algorithms.AES("\x00" * 32), modes.CBC("\x00" * 16)
        ),
        skip_message="Does not support AES CBC",
    )
    def test_unicode(self, backend):
        f = Fernet(base64.urlsafe_b64encode(b"\x00" * 32), backend=backend)
        with pytest.raises(TypeError):
            f.encrypt(six.u(""))
        with pytest.raises(TypeError):
            f.decrypt(six.u(""))

    @pytest.mark.supported(
        only_if=lambda backend: backend.cipher_supported(
            algorithms.AES("\x00" * 32), modes.CBC("\x00" * 16)
        ),
        skip_message="Does not support AES CBC",
    )
    @pytest.mark.parametrize("message", [b"", b"Abc!", b"\x00\xFF\x00\x80"])
    def test_roundtrips(self, message, backend):
        f = Fernet(Fernet.generate_key(), backend=backend)
        assert f.decrypt(f.encrypt(message)) == message

    def test_default_backend(self):
        f = Fernet(Fernet.generate_key())
        assert f._backend is default_backend()

    @pytest.mark.supported(
        only_if=lambda backend: backend.cipher_supported(
            algorithms.AES("\x00" * 32), modes.CBC("\x00" * 16)
        ),
        skip_message="Does not support AES CBC",
    )
    def test_bad_key(self, backend):
        with pytest.raises(ValueError):
            Fernet(base64.urlsafe_b64encode(b"abc"), backend=backend)

########NEW FILE########
__FILENAME__ = test_utils
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import binascii
import os
import textwrap

import pretend

import pytest

import cryptography
from cryptography.exceptions import UnsupportedAlgorithm, _Reasons

import cryptography_vectors

from .utils import (
    check_backend_support, check_for_iface, der_encode_dsa_signature,
    load_cryptrec_vectors, load_fips_dsa_key_pair_vectors,
    load_fips_dsa_sig_vectors, load_fips_ecdsa_key_pair_vectors,
    load_fips_ecdsa_signing_vectors, load_hash_vectors, load_nist_vectors,
    load_pkcs1_vectors, load_rsa_nist_vectors, load_vectors_from_file,
    raises_unsupported_algorithm, select_backends
)


class FakeInterface(object):
    pass


def test_select_one_backend():
    b1 = pretend.stub(name="b1")
    b2 = pretend.stub(name="b2")
    b3 = pretend.stub(name="b3")
    backends = [b1, b2, b3]
    name = "b2"
    selected_backends = select_backends(name, backends)
    assert len(selected_backends) == 1
    assert selected_backends[0] == b2


def test_select_no_backend():
    b1 = pretend.stub(name="b1")
    b2 = pretend.stub(name="b2")
    b3 = pretend.stub(name="b3")
    backends = [b1, b2, b3]
    name = "back!"
    with pytest.raises(ValueError):
        select_backends(name, backends)


def test_select_backends_none():
    b1 = pretend.stub(name="b1")
    b2 = pretend.stub(name="b2")
    b3 = pretend.stub(name="b3")
    backends = [b1, b2, b3]
    name = None
    selected_backends = select_backends(name, backends)
    assert len(selected_backends) == 3


def test_select_two_backends():
    b1 = pretend.stub(name="b1")
    b2 = pretend.stub(name="b2")
    b3 = pretend.stub(name="b3")
    backends = [b1, b2, b3]
    name = "b2 ,b1 "
    selected_backends = select_backends(name, backends)
    assert len(selected_backends) == 2
    assert selected_backends == [b1, b2]


def test_check_for_iface():
    item = pretend.stub(keywords=["fake_name"], funcargs={"backend": True})
    with pytest.raises(pytest.skip.Exception) as exc_info:
        check_for_iface("fake_name", FakeInterface, item)
    assert exc_info.value.args[0] == "True backend does not support fake_name"

    item = pretend.stub(
        keywords=["fake_name"],
        funcargs={"backend": FakeInterface()}
    )
    check_for_iface("fake_name", FakeInterface, item)


def test_check_backend_support_skip():
    supported = pretend.stub(
        kwargs={"only_if": lambda backend: False, "skip_message": "Nope"}
    )
    item = pretend.stub(keywords={"supported": supported},
                        funcargs={"backend": True})
    with pytest.raises(pytest.skip.Exception) as exc_info:
        check_backend_support(item)
    assert exc_info.value.args[0] == "Nope (True)"


def test_check_backend_support_no_skip():
    supported = pretend.stub(
        kwargs={"only_if": lambda backend: True, "skip_message": "Nope"}
    )
    item = pretend.stub(keywords={"supported": supported},
                        funcargs={"backend": True})
    assert check_backend_support(item) is None


def test_check_backend_support_no_backend():
    supported = pretend.stub(
        kwargs={"only_if": "notalambda", "skip_message": "Nope"}
    )
    item = pretend.stub(keywords={"supported": supported},
                        funcargs={})
    with pytest.raises(ValueError):
        check_backend_support(item)


def test_der_encode_dsa_signature_values():
    sig = der_encode_dsa_signature(1, 1)
    assert sig == b"0\x06\x02\x01\x01\x02\x01\x01"

    sig2 = der_encode_dsa_signature(
        1037234182290683143945502320610861668562885151617,
        559776156650501990899426031439030258256861634312
    )
    assert sig2 == (
        b'0-\x02\x15\x00\xb5\xaf0xg\xfb\x8bT9\x00\x13\xccg\x02\r\xdf\x1f,\x0b'
        b'\x81\x02\x14b\r;"\xabP1D\x0c>5\xea\xb6\xf4\x81)\x8f\x9e\x9f\x08'
    )

    sig3 = der_encode_dsa_signature(0, 0)
    assert sig3 == b"0\x06\x02\x01\x00\x02\x01\x00"

    sig4 = der_encode_dsa_signature(-1, 0)
    assert sig4 == b"0\x06\x02\x01\xFF\x02\x01\x00"


def test_load_nist_vectors():
    vector_data = textwrap.dedent("""
    # CAVS 11.1
    # Config info for aes_values
    # AESVS GFSbox test data for CBC
    # State : Encrypt and Decrypt
    # Key Length : 128
    # Generated on Fri Apr 22 15:11:33 2011

    [ENCRYPT]

    COUNT = 0
    KEY = 00000000000000000000000000000000
    IV = 00000000000000000000000000000000
    PLAINTEXT = f34481ec3cc627bacd5dc3fb08f273e6
    CIPHERTEXT = 0336763e966d92595a567cc9ce537f5e

    COUNT = 1
    KEY = 00000000000000000000000000000000
    IV = 00000000000000000000000000000000
    PLAINTEXT = 9798c4640bad75c7c3227db910174e72
    CIPHERTEXT = a9a1631bf4996954ebc093957b234589

    [DECRYPT]

    COUNT = 0
    KEY = 00000000000000000000000000000000
    IV = 00000000000000000000000000000000
    CIPHERTEXT = 0336763e966d92595a567cc9ce537f5e
    PLAINTEXT = f34481ec3cc627bacd5dc3fb08f273e6

    COUNT = 1
    KEY = 00000000000000000000000000000000
    IV = 00000000000000000000000000000000
    CIPHERTEXT = a9a1631bf4996954ebc093957b234589
    PLAINTEXT = 9798c4640bad75c7c3227db910174e72
    """).splitlines()

    assert load_nist_vectors(vector_data) == [
        {
            "key": b"00000000000000000000000000000000",
            "iv": b"00000000000000000000000000000000",
            "plaintext": b"f34481ec3cc627bacd5dc3fb08f273e6",
            "ciphertext": b"0336763e966d92595a567cc9ce537f5e",
        },
        {
            "key": b"00000000000000000000000000000000",
            "iv": b"00000000000000000000000000000000",
            "plaintext": b"9798c4640bad75c7c3227db910174e72",
            "ciphertext": b"a9a1631bf4996954ebc093957b234589",
        },
        {
            "key": b"00000000000000000000000000000000",
            "iv": b"00000000000000000000000000000000",
            "plaintext": b"f34481ec3cc627bacd5dc3fb08f273e6",
            "ciphertext": b"0336763e966d92595a567cc9ce537f5e",
        },
        {
            "key": b"00000000000000000000000000000000",
            "iv": b"00000000000000000000000000000000",
            "plaintext": b"9798c4640bad75c7c3227db910174e72",
            "ciphertext": b"a9a1631bf4996954ebc093957b234589",
        },
    ]


def test_load_nist_vectors_with_null_chars():
    vector_data = textwrap.dedent("""
    COUNT = 0
    KEY = thing\\0withnulls

    COUNT = 1
    KEY = 00000000000000000000000000000000
    """).splitlines()

    assert load_nist_vectors(vector_data) == [
        {
            "key": b"thing\x00withnulls",
        },
        {
            "key": b"00000000000000000000000000000000",
        },
    ]


def test_load_cryptrec_vectors():
    vector_data = textwrap.dedent("""
    # Vectors taken from http://info.isl.ntt.co.jp/crypt/eng/camellia/
    # Download is t_camelia.txt

    # Camellia with 128-bit key

    K No.001 : 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00

    P No.001 : 80 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    C No.001 : 07 92 3A 39 EB 0A 81 7D 1C 4D 87 BD B8 2D 1F 1C

    P No.002 : 40 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    C No.002 : 48 CD 64 19 80 96 72 D2 34 92 60 D8 9A 08 D3 D3

    K No.002 : 10 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00

    P No.001 : 80 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    C No.001 : 07 92 3A 39 EB 0A 81 7D 1C 4D 87 BD B8 2D 1F 1C
    """).splitlines()

    assert load_cryptrec_vectors(vector_data) == [
        {
            "key": b"00000000000000000000000000000000",
            "plaintext": b"80000000000000000000000000000000",
            "ciphertext": b"07923A39EB0A817D1C4D87BDB82D1F1C",
        },
        {
            "key": b"00000000000000000000000000000000",
            "plaintext": b"40000000000000000000000000000000",
            "ciphertext": b"48CD6419809672D2349260D89A08D3D3",
        },
        {
            "key": b"10000000000000000000000000000000",
            "plaintext": b"80000000000000000000000000000000",
            "ciphertext": b"07923A39EB0A817D1C4D87BDB82D1F1C",
        },
    ]


def test_load_cryptrec_vectors_invalid():
    vector_data = textwrap.dedent("""
    # Vectors taken from http://info.isl.ntt.co.jp/crypt/eng/camellia/
    # Download is t_camelia.txt

    # Camellia with 128-bit key

    E No.001 : 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    """).splitlines()

    with pytest.raises(ValueError):
        load_cryptrec_vectors(vector_data)


def test_load_hash_vectors():
    vector_data = textwrap.dedent("""

        # http://tools.ietf.org/html/rfc1321
        [irrelevant]

        Len = 0
        Msg = 00
        MD = d41d8cd98f00b204e9800998ecf8427e

        Len = 8
        Msg = 61
        MD = 0cc175b9c0f1b6a831c399e269772661

        Len = 24
        Msg = 616263
        MD = 900150983cd24fb0d6963f7d28e17f72

        Len = 112
        Msg = 6d65737361676520646967657374
        MD = f96b697d7cb7938d525a2f31aaf161d0
    """).splitlines()
    assert load_hash_vectors(vector_data) == [
        (b"", "d41d8cd98f00b204e9800998ecf8427e"),
        (b"61", "0cc175b9c0f1b6a831c399e269772661"),
        (b"616263", "900150983cd24fb0d6963f7d28e17f72"),
        (b"6d65737361676520646967657374", "f96b697d7cb7938d525a2f31aaf161d0"),
    ]


def test_load_hmac_vectors():
    vector_data = textwrap.dedent("""
Len = 224
# "Jefe"
Key = 4a656665
# "what do ya want for nothing?"
Msg = 7768617420646f2079612077616e7420666f72206e6f7468696e673f
MD = 750c783e6ab0b503eaa86e310a5db738
    """).splitlines()
    assert load_hash_vectors(vector_data) == [
        (b"7768617420646f2079612077616e7420666f72206e6f7468696e673f",
         "750c783e6ab0b503eaa86e310a5db738",
         b"4a656665"),
    ]


def test_load_hash_vectors_bad_data():
    vector_data = textwrap.dedent("""
        # http://tools.ietf.org/html/rfc1321

        Len = 0
        Msg = 00
        UNKNOWN=Hello World
    """).splitlines()
    with pytest.raises(ValueError):
        load_hash_vectors(vector_data)


def test_load_vectors_from_file():
    vectors = load_vectors_from_file(
        os.path.join("ciphers", "Blowfish", "bf-cfb.txt"),
        load_nist_vectors,
    )
    assert vectors == [
        {
            "key": b"0123456789ABCDEFF0E1D2C3B4A59687",
            "iv": b"FEDCBA9876543210",
            "plaintext": (
                b"37363534333231204E6F77206973207468652074696D6520666F722000"
            ),
            "ciphertext": (
                b"E73214A2822139CAF26ECF6D2EB9E76E3DA3DE04D1517200519D57A6C3"
            ),
        }
    ]


def test_load_nist_gcm_vectors():
    vector_data = textwrap.dedent("""
        [Keylen = 128]
        [IVlen = 96]
        [PTlen = 0]
        [AADlen = 0]
        [Taglen = 128]

        Count = 0
        Key = 11754cd72aec309bf52f7687212e8957
        IV = 3c819d9a9bed087615030b65
        PT =
        AAD =
        CT =
        Tag = 250327c674aaf477aef2675748cf6971

        Count = 1
        Key = 272f16edb81a7abbea887357a58c1917
        IV = 794ec588176c703d3d2a7a07
        PT =
        AAD =
        CT =
        Tag = b6e6f197168f5049aeda32dafbdaeb

        Count = 2
        Key = a49a5e26a2f8cb63d05546c2a62f5343
        IV = 907763b19b9b4ab6bd4f0281
        CT =
        AAD =
        Tag = a2be08210d8c470a8df6e8fbd79ec5cf
        FAIL

        Count = 3
        Key = 5c1155084cc0ede76b3bc22e9f7574ef
        IV = 9549e4ba69a61cad7856efc1
        PT = d1448fa852b84408e2dad8381f363de7
        AAD = e98e9d9c618e46fef32660976f854ee3
        CT = f78b60ca125218493bea1c50a2e12ef4
        Tag = d72da7f5c6cf0bca7242c71835809449

        [Keylen = 128]
        [IVlen = 96]
        [PTlen = 0]
        [AADlen = 0]
        [Taglen = 120]

        Count = 0
        Key = eac258e99c55e6ae8ef1da26640613d7
        IV = 4e8df20faaf2c8eebe922902
        CT =
        AAD =
        Tag = e39aeaebe86aa309a4d062d6274339
        PT =

        Count = 1
        Key = 3726cf02fcc6b8639a5497652c94350d
        IV = 55fef82cde693ce76efcc193
        CT =
        AAD =
        Tag = 3d68111a81ed22d2ef5bccac4fc27f
        FAIL

        Count = 2
        Key = f202299d5fd74f03b12d2119a6c4c038
        IV = eec51e7958c3f20a1bb71815
        CT =
        AAD =
        Tag = a81886b3fb26e51fca87b267e1e157
        FAIL

        Count = 3
        Key = fd52925f39546b4c55ffb6b20c59898c
        IV = f5cf3227444afd905a5f6dba
        CT =
        AAD =
        Tag = 1665b0f1a0b456e1664cfd3de08ccd
        PT =

        [Keylen = 128]
        [IVlen = 8]
        [PTlen = 104]
        [AADlen = 0]
        [Taglen = 128]

        Count = 0
        Key = 58fab7632bcf10d2bcee58520bf37414
        IV = 3c
        CT = 15c4db4cbb451211179d57017f
        AAD =
        Tag = eae841d4355feeb3f786bc86625f1e5b
        FAIL
    """).splitlines()
    assert load_nist_vectors(vector_data) == [
        {'aad': b'',
         'pt': b'',
         'iv': b'3c819d9a9bed087615030b65',
         'tag': b'250327c674aaf477aef2675748cf6971',
         'key': b'11754cd72aec309bf52f7687212e8957',
         'ct': b''},
        {'aad': b'',
         'pt': b'',
         'iv': b'794ec588176c703d3d2a7a07',
         'tag': b'b6e6f197168f5049aeda32dafbdaeb',
         'key': b'272f16edb81a7abbea887357a58c1917',
         'ct': b''},
        {'aad': b'',
         'iv': b'907763b19b9b4ab6bd4f0281',
         'tag': b'a2be08210d8c470a8df6e8fbd79ec5cf',
         'key': b'a49a5e26a2f8cb63d05546c2a62f5343',
         'ct': b'',
         'fail': True},
        {'aad': b'e98e9d9c618e46fef32660976f854ee3',
         'pt': b'd1448fa852b84408e2dad8381f363de7',
         'iv': b'9549e4ba69a61cad7856efc1',
         'tag': b'd72da7f5c6cf0bca7242c71835809449',
         'key': b'5c1155084cc0ede76b3bc22e9f7574ef',
         'ct': b'f78b60ca125218493bea1c50a2e12ef4'},
        {'aad': b'',
         'pt': b'',
         'iv': b'4e8df20faaf2c8eebe922902',
         'tag': b'e39aeaebe86aa309a4d062d6274339',
         'key': b'eac258e99c55e6ae8ef1da26640613d7',
         'ct': b''},
        {'aad': b'',
         'iv': b'55fef82cde693ce76efcc193',
         'tag': b'3d68111a81ed22d2ef5bccac4fc27f',
         'key': b'3726cf02fcc6b8639a5497652c94350d',
         'ct': b'',
         'fail': True},
        {'aad': b'',
         'iv': b'eec51e7958c3f20a1bb71815',
         'tag': b'a81886b3fb26e51fca87b267e1e157',
         'key': b'f202299d5fd74f03b12d2119a6c4c038',
         'ct': b'',
         'fail': True},
        {'aad': b'',
         'pt': b'',
         'iv': b'f5cf3227444afd905a5f6dba',
         'tag': b'1665b0f1a0b456e1664cfd3de08ccd',
         'key': b'fd52925f39546b4c55ffb6b20c59898c',
         'ct': b''},
        {'aad': b'',
         'iv': b'3c',
         'tag': b'eae841d4355feeb3f786bc86625f1e5b',
         'key': b'58fab7632bcf10d2bcee58520bf37414',
         'ct': b'15c4db4cbb451211179d57017f',
         'fail': True},
    ]


def test_load_pkcs1_vectors():
    vector_data = textwrap.dedent("""
    Test vectors for RSA-PSS
    ========================

    This file contains an extract of the original pss-vect.txt

    Key lengths:

    Key  8: 1031 bits
    Key  9: 1536 bits
    ===========================================================================

    <snip>

    # Example 8: A 1031-bit RSA key pair
    # -----------------------------------


    # Public key
    # ----------

    # Modulus:
    49 53 70 a1 fb 18 54 3c 16 d3 63 1e 31 63 25 5d
    f6 2b e6 ee e8 90 d5 f2 55 09 e4 f7 78 a8 ea 6f
    bb bc df 85 df f6 4e 0d 97 20 03 ab 36 81 fb ba
    6d d4 1f d5 41 82 9b 2e 58 2d e9 f2 a4 a4 e0 a2
    d0 90 0b ef 47 53 db 3c ee 0e e0 6c 7d fa e8 b1
    d5 3b 59 53 21 8f 9c ce ea 69 5b 08 66 8e de aa
    dc ed 94 63 b1 d7 90 d5 eb f2 7e 91 15 b4 6c ad
    4d 9a 2b 8e fa b0 56 1b 08 10 34 47 39 ad a0 73
    3f

    # Exponent:
    01 00 01

    # Private key
    # -----------

    # Modulus:
    49 53 70 a1 fb 18 54 3c 16 d3 63 1e 31 63 25 5d
    f6 2b e6 ee e8 90 d5 f2 55 09 e4 f7 78 a8 ea 6f
    bb bc df 85 df f6 4e 0d 97 20 03 ab 36 81 fb ba
    6d d4 1f d5 41 82 9b 2e 58 2d e9 f2 a4 a4 e0 a2
    d0 90 0b ef 47 53 db 3c ee 0e e0 6c 7d fa e8 b1
    d5 3b 59 53 21 8f 9c ce ea 69 5b 08 66 8e de aa
    dc ed 94 63 b1 d7 90 d5 eb f2 7e 91 15 b4 6c ad
    4d 9a 2b 8e fa b0 56 1b 08 10 34 47 39 ad a0 73
    3f

    # Public exponent:
    01 00 01

    # Exponent:
    6c 66 ff e9 89 80 c3 8f cd ea b5 15 98 98 83 61
    65 f4 b4 b8 17 c4 f6 a8 d4 86 ee 4e a9 13 0f e9
    b9 09 2b d1 36 d1 84 f9 5f 50 4a 60 7e ac 56 58
    46 d2 fd d6 59 7a 89 67 c7 39 6e f9 5a 6e ee bb
    45 78 a6 43 96 6d ca 4d 8e e3 de 84 2d e6 32 79
    c6 18 15 9c 1a b5 4a 89 43 7b 6a 61 20 e4 93 0a
    fb 52 a4 ba 6c ed 8a 49 47 ac 64 b3 0a 34 97 cb
    e7 01 c2 d6 26 6d 51 72 19 ad 0e c6 d3 47 db e9

    # Prime 1:
    08 da d7 f1 13 63 fa a6 23 d5 d6 d5 e8 a3 19 32
    8d 82 19 0d 71 27 d2 84 6c 43 9b 0a b7 26 19 b0
    a4 3a 95 32 0e 4e c3 4f c3 a9 ce a8 76 42 23 05
    bd 76 c5 ba 7b e9 e2 f4 10 c8 06 06 45 a1 d2 9e
    db

    # Prime 2:
    08 47 e7 32 37 6f c7 90 0f 89 8e a8 2e b2 b0 fc
    41 85 65 fd ae 62 f7 d9 ec 4c e2 21 7b 97 99 0d
    d2 72 db 15 7f 99 f6 3c 0d cb b9 fb ac db d4 c4
    da db 6d f6 77 56 35 8c a4 17 48 25 b4 8f 49 70
    6d

    # Prime exponent 1:
    05 c2 a8 3c 12 4b 36 21 a2 aa 57 ea 2c 3e fe 03
    5e ff 45 60 f3 3d de bb 7a da b8 1f ce 69 a0 c8
    c2 ed c1 65 20 dd a8 3d 59 a2 3b e8 67 96 3a c6
    5f 2c c7 10 bb cf b9 6e e1 03 de b7 71 d1 05 fd
    85

    # Prime exponent 2:
    04 ca e8 aa 0d 9f aa 16 5c 87 b6 82 ec 14 0b 8e
    d3 b5 0b 24 59 4b 7a 3b 2c 22 0b 36 69 bb 81 9f
    98 4f 55 31 0a 1a e7 82 36 51 d4 a0 2e 99 44 79
    72 59 51 39 36 34 34 e5 e3 0a 7e 7d 24 15 51 e1
    b9

    # Coefficient:
    07 d3 e4 7b f6 86 60 0b 11 ac 28 3c e8 8d bb 3f
    60 51 e8 ef d0 46 80 e4 4c 17 1e f5 31 b8 0b 2b
    7c 39 fc 76 63 20 e2 cf 15 d8 d9 98 20 e9 6f f3
    0d c6 96 91 83 9c 4b 40 d7 b0 6e 45 30 7d c9 1f
    3f

    # RSA-PSS signing of 6 random messages with random salts
    # -------------------------------------------------------
    # PSS Example 8.1

    # -----------------

    # Message to be signed:
    81 33 2f 4b e6 29 48 41 5e a1 d8 99 79 2e ea cf
    6c 6e 1d b1 da 8b e1 3b 5c ea 41 db 2f ed 46 70
    92 e1 ff 39 89 14 c7 14 25 97 75 f5 95 f8 54 7f
    73 56 92 a5 75 e6 92 3a f7 8f 22 c6 99 7d db 90
    fb 6f 72 d7 bb 0d d5 74 4a 31 de cd 3d c3 68 58
    49 83 6e d3 4a ec 59 63 04 ad 11 84 3c 4f 88 48
    9f 20 97 35 f5 fb 7f da f7 ce c8 ad dc 58 18 16
    8f 88 0a cb f4 90 d5 10 05 b7 a8 e8 4e 43 e5 42
    87 97 75 71 dd 99 ee a4 b1 61 eb 2d f1 f5 10 8f
    12 a4 14 2a 83 32 2e db 05 a7 54 87 a3 43 5c 9a
    78 ce 53 ed 93 bc 55 08 57 d7 a9 fb

    # Salt:
    1d 65 49 1d 79 c8 64 b3 73 00 9b e6 f6 f2 46 7b
    ac 4c 78 fa

    # Signature:
    02 62 ac 25 4b fa 77 f3 c1 ac a2 2c 51 79 f8 f0
    40 42 2b 3c 5b af d4 0a 8f 21 cf 0f a5 a6 67 cc
    d5 99 3d 42 db af b4 09 c5 20 e2 5f ce 2b 1e e1
    e7 16 57 7f 1e fa 17 f3 da 28 05 2f 40 f0 41 9b
    23 10 6d 78 45 aa f0 11 25 b6 98 e7 a4 df e9 2d
    39 67 bb 00 c4 d0 d3 5b a3 55 2a b9 a8 b3 ee f0
    7c 7f ec db c5 42 4a c4 db 1e 20 cb 37 d0 b2 74
    47 69 94 0e a9 07 e1 7f bb ca 67 3b 20 52 23 80
    c5

    # PSS Example 8.2

    # -----------------

    # Message to be signed:
    e2 f9 6e af 0e 05 e7 ba 32 6e cc a0 ba 7f d2 f7
    c0 23 56 f3 ce de 9d 0f aa bf 4f cc 8e 60 a9 73
    e5 59 5f d9 ea 08

    # Salt:
    43 5c 09 8a a9 90 9e b2 37 7f 12 48 b0 91 b6 89
    87 ff 18 38

    # Signature:
    27 07 b9 ad 51 15 c5 8c 94 e9 32 e8 ec 0a 28 0f
    56 33 9e 44 a1 b5 8d 4d dc ff 2f 31 2e 5f 34 dc
    fe 39 e8 9c 6a 94 dc ee 86 db bd ae 5b 79 ba 4e
    08 19 a9 e7 bf d9 d9 82 e7 ee 6c 86 ee 68 39 6e
    8b 3a 14 c9 c8 f3 4b 17 8e b7 41 f9 d3 f1 21 10
    9b f5 c8 17 2f ad a2 e7 68 f9 ea 14 33 03 2c 00
    4a 8a a0 7e b9 90 00 0a 48 dc 94 c8 ba c8 aa be
    2b 09 b1 aa 46 c0 a2 aa 0e 12 f6 3f bb a7 75 ba
    7e

    # <snip>

    # =============================================

    # Example 9: A 1536-bit RSA key pair
    # -----------------------------------


    # Public key
    # ----------

    # Modulus:
    e6 bd 69 2a c9 66 45 79 04 03 fd d0 f5 be b8 b9
    bf 92 ed 10 00 7f c3 65 04 64 19 dd 06 c0 5c 5b
    5b 2f 48 ec f9 89 e4 ce 26 91 09 97 9c bb 40 b4
    a0 ad 24 d2 24 83 d1 ee 31 5a d4 cc b1 53 42 68
    35 26 91 c5 24 f6 dd 8e 6c 29 d2 24 cf 24 69 73
    ae c8 6c 5b f6 b1 40 1a 85 0d 1b 9a d1 bb 8c bc
    ec 47 b0 6f 0f 8c 7f 45 d3 fc 8f 31 92 99 c5 43
    3d db c2 b3 05 3b 47 de d2 ec d4 a4 ca ef d6 14
    83 3d c8 bb 62 2f 31 7e d0 76 b8 05 7f e8 de 3f
    84 48 0a d5 e8 3e 4a 61 90 4a 4f 24 8f b3 97 02
    73 57 e1 d3 0e 46 31 39 81 5c 6f d4 fd 5a c5 b8
    17 2a 45 23 0e cb 63 18 a0 4f 14 55 d8 4e 5a 8b

    # Exponent:
    01 00 01

    # Private key
    # -----------

    # Modulus:
    e6 bd 69 2a c9 66 45 79 04 03 fd d0 f5 be b8 b9
    bf 92 ed 10 00 7f c3 65 04 64 19 dd 06 c0 5c 5b
    5b 2f 48 ec f9 89 e4 ce 26 91 09 97 9c bb 40 b4
    a0 ad 24 d2 24 83 d1 ee 31 5a d4 cc b1 53 42 68
    35 26 91 c5 24 f6 dd 8e 6c 29 d2 24 cf 24 69 73
    ae c8 6c 5b f6 b1 40 1a 85 0d 1b 9a d1 bb 8c bc
    ec 47 b0 6f 0f 8c 7f 45 d3 fc 8f 31 92 99 c5 43
    3d db c2 b3 05 3b 47 de d2 ec d4 a4 ca ef d6 14
    83 3d c8 bb 62 2f 31 7e d0 76 b8 05 7f e8 de 3f
    84 48 0a d5 e8 3e 4a 61 90 4a 4f 24 8f b3 97 02
    73 57 e1 d3 0e 46 31 39 81 5c 6f d4 fd 5a c5 b8
    17 2a 45 23 0e cb 63 18 a0 4f 14 55 d8 4e 5a 8b

    # Public exponent:
    01 00 01

    # Exponent:
    6a 7f d8 4f b8 5f ad 07 3b 34 40 6d b7 4f 8d 61
    a6 ab c1 21 96 a9 61 dd 79 56 5e 9d a6 e5 18 7b
    ce 2d 98 02 50 f7 35 95 75 35 92 70 d9 15 90 bb
    0e 42 7c 71 46 0b 55 d5 14 10 b1 91 bc f3 09 fe
    a1 31 a9 2c 8e 70 27 38 fa 71 9f 1e 00 41 f5 2e
    40 e9 1f 22 9f 4d 96 a1 e6 f1 72 e1 55 96 b4 51
    0a 6d ae c2 61 05 f2 be bc 53 31 6b 87 bd f2 13
    11 66 60 70 e8 df ee 69 d5 2c 71 a9 76 ca ae 79
    c7 2b 68 d2 85 80 dc 68 6d 9f 51 29 d2 25 f8 2b
    3d 61 55 13 a8 82 b3 db 91 41 6b 48 ce 08 88 82
    13 e3 7e eb 9a f8 00 d8 1c ab 32 8c e4 20 68 99
    03 c0 0c 7b 5f d3 1b 75 50 3a 6d 41 96 84 d6 29

    # Prime 1:
    f8 eb 97 e9 8d f1 26 64 ee fd b7 61 59 6a 69 dd
    cd 0e 76 da ec e6 ed 4b f5 a1 b5 0a c0 86 f7 92
    8a 4d 2f 87 26 a7 7e 51 5b 74 da 41 98 8f 22 0b
    1c c8 7a a1 fc 81 0c e9 9a 82 f2 d1 ce 82 1e dc
    ed 79 4c 69 41 f4 2c 7a 1a 0b 8c 4d 28 c7 5e c6
    0b 65 22 79 f6 15 4a 76 2a ed 16 5d 47 de e3 67

    # Prime 2:
    ed 4d 71 d0 a6 e2 4b 93 c2 e5 f6 b4 bb e0 5f 5f
    b0 af a0 42 d2 04 fe 33 78 d3 65 c2 f2 88 b6 a8
    da d7 ef e4 5d 15 3e ef 40 ca cc 7b 81 ff 93 40
    02 d1 08 99 4b 94 a5 e4 72 8c d9 c9 63 37 5a e4
    99 65 bd a5 5c bf 0e fe d8 d6 55 3b 40 27 f2 d8
    62 08 a6 e6 b4 89 c1 76 12 80 92 d6 29 e4 9d 3d

    # Prime exponent 1:
    2b b6 8b dd fb 0c 4f 56 c8 55 8b ff af 89 2d 80
    43 03 78 41 e7 fa 81 cf a6 1a 38 c5 e3 9b 90 1c
    8e e7 11 22 a5 da 22 27 bd 6c de eb 48 14 52 c1
    2a d3 d6 1d 5e 4f 77 6a 0a b5 56 59 1b ef e3 e5
    9e 5a 7f dd b8 34 5e 1f 2f 35 b9 f4 ce e5 7c 32
    41 4c 08 6a ec 99 3e 93 53 e4 80 d9 ee c6 28 9f

    # Prime exponent 2:
    4f f8 97 70 9f ad 07 97 46 49 45 78 e7 0f d8 54
    61 30 ee ab 56 27 c4 9b 08 0f 05 ee 4a d9 f3 e4
    b7 cb a9 d6 a5 df f1 13 a4 1c 34 09 33 68 33 f1
    90 81 6d 8a 6b c4 2e 9b ec 56 b7 56 7d 0f 3c 9c
    69 6d b6 19 b2 45 d9 01 dd 85 6d b7 c8 09 2e 77
    e9 a1 cc cd 56 ee 4d ba 42 c5 fd b6 1a ec 26 69

    # Coefficient:
    77 b9 d1 13 7b 50 40 4a 98 27 29 31 6e fa fc 7d
    fe 66 d3 4e 5a 18 26 00 d5 f3 0a 0a 85 12 05 1c
    56 0d 08 1d 4d 0a 18 35 ec 3d 25 a6 0f 4e 4d 6a
    a9 48 b2 bf 3d bb 5b 12 4c bb c3 48 92 55 a3 a9
    48 37 2f 69 78 49 67 45 f9 43 e1 db 4f 18 38 2c
    ea a5 05 df c6 57 57 bb 3f 85 7a 58 dc e5 21 56

    # PKCS#1 v1.5 Signature Example 2.17

    # -----------------

    # Message to be signed:
    06 ad d7 5a b6 89 de 06 77 44 e6 9a 2e bd 4b 90
    fa 93 83 00 3c d0 5f f5 36 cb f2 94 cd 21 5f 09
    23 b7 fc 90 04 f0 aa 18 52 71 a1 d0 06 1f d0 e9
    77 7a d1 ec 0c 71 59 1f 57 8b f7 b8 e5 a1

    # Signature:
    45 14 21 0e 54 1d 5b ad 7d d6 0a e5 49 b9 43 ac
    c4 4f 21 39 0d f5 b6 13 18 45 5a 17 61 0d f5 b7
    4d 84 ae d2 32 f1 7e 59 d9 1d d2 65 99 22 f8 12
    db d4 96 81 69 03 84 b9 54 e9 ad fb 9b 1a 96 8c
    0c bf f7 63 ec ee d6 27 50 c5 91 64 b5 e0 80 a8
    fe f3 d5 5b fe 2a cf ad 27 52 a6 a8 45 9f a1 fa
    b4 9a d3 78 c6 96 4b 23 ee 97 fd 10 34 61 0c 5c
    c1 4c 61 e0 eb fb 17 11 f8 ad e9 6f e6 55 7b 38

    # <snip>

    # =============================================

    # <snip>
    """).splitlines()

    vectors = tuple(load_pkcs1_vectors(vector_data))
    expected = (
        (
            {
                'modulus': int(
                    '495370a1fb18543c16d3631e3163255df62be6eee890d5f25509e4f77'
                    '8a8ea6fbbbcdf85dff64e0d972003ab3681fbba6dd41fd541829b2e58'
                    '2de9f2a4a4e0a2d0900bef4753db3cee0ee06c7dfae8b1d53b5953218'
                    'f9cceea695b08668edeaadced9463b1d790d5ebf27e9115b46cad4d9a'
                    '2b8efab0561b0810344739ada0733f', 16),
                'public_exponent': int('10001', 16),
                'private_exponent': int(
                    '6c66ffe98980c38fcdeab5159898836165f4b4b817c4f6a8d486ee4ea'
                    '9130fe9b9092bd136d184f95f504a607eac565846d2fdd6597a8967c7'
                    '396ef95a6eeebb4578a643966dca4d8ee3de842de63279c618159c1ab'
                    '54a89437b6a6120e4930afb52a4ba6ced8a4947ac64b30a3497cbe701'
                    'c2d6266d517219ad0ec6d347dbe9', 16),
                'p': int(
                    '8dad7f11363faa623d5d6d5e8a319328d82190d7127d2846c439b0ab7'
                    '2619b0a43a95320e4ec34fc3a9cea876422305bd76c5ba7be9e2f410c'
                    '8060645a1d29edb', 16),
                'q': int(
                    '847e732376fc7900f898ea82eb2b0fc418565fdae62f7d9ec4ce2217b'
                    '97990dd272db157f99f63c0dcbb9fbacdbd4c4dadb6df67756358ca41'
                    '74825b48f49706d', 16),
                'dmp1': int(
                    '05c2a83c124b3621a2aa57ea2c3efe035eff4560f33ddebb7adab81fc'
                    'e69a0c8c2edc16520dda83d59a23be867963ac65f2cc710bbcfb96ee1'
                    '03deb771d105fd85', 16),
                'dmq1': int(
                    '04cae8aa0d9faa165c87b682ec140b8ed3b50b24594b7a3b2c220b366'
                    '9bb819f984f55310a1ae7823651d4a02e99447972595139363434e5e3'
                    '0a7e7d241551e1b9', 16),
                'iqmp': int(
                    '07d3e47bf686600b11ac283ce88dbb3f6051e8efd04680e44c171ef53'
                    '1b80b2b7c39fc766320e2cf15d8d99820e96ff30dc69691839c4b40d7'
                    'b06e45307dc91f3f', 16),
                'examples': [
                    {
                        'message': b'81332f4be62948415ea1d899792eeacf6c6e1db1d'
                                   b'a8be13b5cea41db2fed467092e1ff398914c71425'
                                   b'9775f595f8547f735692a575e6923af78f22c6997'
                                   b'ddb90fb6f72d7bb0dd5744a31decd3dc368584983'
                                   b'6ed34aec596304ad11843c4f88489f209735f5fb7'
                                   b'fdaf7cec8addc5818168f880acbf490d51005b7a8'
                                   b'e84e43e54287977571dd99eea4b161eb2df1f5108'
                                   b'f12a4142a83322edb05a75487a3435c9a78ce53ed'
                                   b'93bc550857d7a9fb',
                        'salt': b'1d65491d79c864b373009be6f6f2467bac4c78fa',
                        'signature': b'0262ac254bfa77f3c1aca22c5179f8f040422b3'
                                     b'c5bafd40a8f21cf0fa5a667ccd5993d42dbafb4'
                                     b'09c520e25fce2b1ee1e716577f1efa17f3da280'
                                     b'52f40f0419b23106d7845aaf01125b698e7a4df'
                                     b'e92d3967bb00c4d0d35ba3552ab9a8b3eef07c7'
                                     b'fecdbc5424ac4db1e20cb37d0b2744769940ea9'
                                     b'07e17fbbca673b20522380c5'
                    }, {
                        'message': b'e2f96eaf0e05e7ba326ecca0ba7fd2f7c02356f3c'
                                   b'ede9d0faabf4fcc8e60a973e5595fd9ea08',
                        'salt': b'435c098aa9909eb2377f1248b091b68987ff1838',
                        'signature': b'2707b9ad5115c58c94e932e8ec0a280f56339e4'
                                     b'4a1b58d4ddcff2f312e5f34dcfe39e89c6a94dc'
                                     b'ee86dbbdae5b79ba4e0819a9e7bfd9d982e7ee6'
                                     b'c86ee68396e8b3a14c9c8f34b178eb741f9d3f1'
                                     b'21109bf5c8172fada2e768f9ea1433032c004a8'
                                     b'aa07eb990000a48dc94c8bac8aabe2b09b1aa46'
                                     b'c0a2aa0e12f63fbba775ba7e'
                    }
                ]
            },

            {
                'modulus': int(
                    '495370a1fb18543c16d3631e3163255df62be6eee890d5f25509e4f77'
                    '8a8ea6fbbbcdf85dff64e0d972003ab3681fbba6dd41fd541829b2e58'
                    '2de9f2a4a4e0a2d0900bef4753db3cee0ee06c7dfae8b1d53b5953218'
                    'f9cceea695b08668edeaadced9463b1d790d5ebf27e9115b46cad4d9a'
                    '2b8efab0561b0810344739ada0733f', 16),
                'public_exponent': int('10001', 16)
            }
        ),
        (
            {
                'modulus': int(
                    'e6bd692ac96645790403fdd0f5beb8b9bf92ed10007fc365046419dd0'
                    '6c05c5b5b2f48ecf989e4ce269109979cbb40b4a0ad24d22483d1ee31'
                    '5ad4ccb1534268352691c524f6dd8e6c29d224cf246973aec86c5bf6b'
                    '1401a850d1b9ad1bb8cbcec47b06f0f8c7f45d3fc8f319299c5433ddb'
                    'c2b3053b47ded2ecd4a4caefd614833dc8bb622f317ed076b8057fe8d'
                    'e3f84480ad5e83e4a61904a4f248fb397027357e1d30e463139815c6f'
                    'd4fd5ac5b8172a45230ecb6318a04f1455d84e5a8b', 16),
                'public_exponent': int('10001', 16),
                'private_exponent': int(
                    '6a7fd84fb85fad073b34406db74f8d61a6abc12196a961dd79565e9da'
                    '6e5187bce2d980250f7359575359270d91590bb0e427c71460b55d514'
                    '10b191bcf309fea131a92c8e702738fa719f1e0041f52e40e91f229f4'
                    'd96a1e6f172e15596b4510a6daec26105f2bebc53316b87bdf2131166'
                    '6070e8dfee69d52c71a976caae79c72b68d28580dc686d9f5129d225f'
                    '82b3d615513a882b3db91416b48ce08888213e37eeb9af800d81cab32'
                    '8ce420689903c00c7b5fd31b75503a6d419684d629', 16),
                'p': int(
                    'f8eb97e98df12664eefdb761596a69ddcd0e76daece6ed4bf5a1b50ac'
                    '086f7928a4d2f8726a77e515b74da41988f220b1cc87aa1fc810ce99a'
                    '82f2d1ce821edced794c6941f42c7a1a0b8c4d28c75ec60b652279f61'
                    '54a762aed165d47dee367', 16),
                'q': int(
                    'ed4d71d0a6e24b93c2e5f6b4bbe05f5fb0afa042d204fe3378d365c2f'
                    '288b6a8dad7efe45d153eef40cacc7b81ff934002d108994b94a5e472'
                    '8cd9c963375ae49965bda55cbf0efed8d6553b4027f2d86208a6e6b48'
                    '9c176128092d629e49d3d', 16),
                'dmp1': int(
                    '2bb68bddfb0c4f56c8558bffaf892d8043037841e7fa81cfa61a38c5e'
                    '39b901c8ee71122a5da2227bd6cdeeb481452c12ad3d61d5e4f776a0a'
                    'b556591befe3e59e5a7fddb8345e1f2f35b9f4cee57c32414c086aec9'
                    '93e9353e480d9eec6289f', 16),
                'dmq1': int(
                    '4ff897709fad079746494578e70fd8546130eeab5627c49b080f05ee4'
                    'ad9f3e4b7cba9d6a5dff113a41c3409336833f190816d8a6bc42e9bec'
                    '56b7567d0f3c9c696db619b245d901dd856db7c8092e77e9a1cccd56e'
                    'e4dba42c5fdb61aec2669', 16),
                'iqmp': int(
                    '77b9d1137b50404a982729316efafc7dfe66d34e5a182600d5f30a0a8'
                    '512051c560d081d4d0a1835ec3d25a60f4e4d6aa948b2bf3dbb5b124c'
                    'bbc3489255a3a948372f6978496745f943e1db4f18382ceaa505dfc65'
                    '757bb3f857a58dce52156', 16),
                'examples': [
                    {
                        'message': b'06add75ab689de067744e69a2ebd4b90fa9383003'
                                   b'cd05ff536cbf294cd215f0923b7fc9004f0aa1852'
                                   b'71a1d0061fd0e9777ad1ec0c71591f578bf7b8e5a'
                                   b'1',
                        'signature': b'4514210e541d5bad7dd60ae549b943acc44f213'
                                     b'90df5b61318455a17610df5b74d84aed232f17e'
                                     b'59d91dd2659922f812dbd49681690384b954e9a'
                                     b'dfb9b1a968c0cbff763eceed62750c59164b5e0'
                                     b'80a8fef3d55bfe2acfad2752a6a8459fa1fab49'
                                     b'ad378c6964b23ee97fd1034610c5cc14c61e0eb'
                                     b'fb1711f8ade96fe6557b38'
                    }
                ]
            },

            {
                'modulus': int(
                    'e6bd692ac96645790403fdd0f5beb8b9bf92ed10007fc365046419dd0'
                    '6c05c5b5b2f48ecf989e4ce269109979cbb40b4a0ad24d22483d1ee31'
                    '5ad4ccb1534268352691c524f6dd8e6c29d224cf246973aec86c5bf6b'
                    '1401a850d1b9ad1bb8cbcec47b06f0f8c7f45d3fc8f319299c5433ddb'
                    'c2b3053b47ded2ecd4a4caefd614833dc8bb622f317ed076b8057fe8d'
                    'e3f84480ad5e83e4a61904a4f248fb397027357e1d30e463139815c6f'
                    'd4fd5ac5b8172a45230ecb6318a04f1455d84e5a8b', 16),
                'public_exponent': int('10001', 16)
            }
        )
    )
    assert vectors == expected


def test_load_pkcs1_oaep_vectors():
    vector_data = textwrap.dedent("""
    Test vectors for RSA-OAEP
    =========================

    This file contains test vectors for the RSA-OAEP encryption

    Key lengths:

    Key  1: 1024 bits
    # <snip>
    ===========================================================================
    # Example 1: A 1024-bit RSA key pair
    # -----------------------------------


    # Public key
    # ----------

    # Modulus:
    a8 b3 b2 84 af 8e b5 0b 38 70 34 a8 60 f1 46 c4
    91 9f 31 87 63 cd 6c 55 98 c8 ae 48 11 a1 e0 ab
    c4 c7 e0 b0 82 d6 93 a5 e7 fc ed 67 5c f4 66 85
    12 77 2c 0c bc 64 a7 42 c6 c6 30 f5 33 c8 cc 72
    f6 2a e8 33 c4 0b f2 58 42 e9 84 bb 78 bd bf 97
    c0 10 7d 55 bd b6 62 f5 c4 e0 fa b9 84 5c b5 14
    8e f7 39 2d d3 aa ff 93 ae 1e 6b 66 7b b3 d4 24
    76 16 d4 f5 ba 10 d4 cf d2 26 de 88 d3 9f 16 fb

    # Exponent:
    01 00 01

    # Private key
    # -----------

    # Modulus:
    a8 b3 b2 84 af 8e b5 0b 38 70 34 a8 60 f1 46 c4
    91 9f 31 87 63 cd 6c 55 98 c8 ae 48 11 a1 e0 ab
    c4 c7 e0 b0 82 d6 93 a5 e7 fc ed 67 5c f4 66 85
    12 77 2c 0c bc 64 a7 42 c6 c6 30 f5 33 c8 cc 72
    f6 2a e8 33 c4 0b f2 58 42 e9 84 bb 78 bd bf 97
    c0 10 7d 55 bd b6 62 f5 c4 e0 fa b9 84 5c b5 14
    8e f7 39 2d d3 aa ff 93 ae 1e 6b 66 7b b3 d4 24
    76 16 d4 f5 ba 10 d4 cf d2 26 de 88 d3 9f 16 fb

    # Public exponent:
    01 00 01

    # Exponent:
    53 33 9c fd b7 9f c8 46 6a 65 5c 73 16 ac a8 5c
    55 fd 8f 6d d8 98 fd af 11 95 17 ef 4f 52 e8 fd
    8e 25 8d f9 3f ee 18 0f a0 e4 ab 29 69 3c d8 3b
    15 2a 55 3d 4a c4 d1 81 2b 8b 9f a5 af 0e 7f 55
    fe 73 04 df 41 57 09 26 f3 31 1f 15 c4 d6 5a 73
    2c 48 31 16 ee 3d 3d 2d 0a f3 54 9a d9 bf 7c bf
    b7 8a d8 84 f8 4d 5b eb 04 72 4d c7 36 9b 31 de
    f3 7d 0c f5 39 e9 cf cd d3 de 65 37 29 ea d5 d1

    # Prime 1:
    d3 27 37 e7 26 7f fe 13 41 b2 d5 c0 d1 50 a8 1b
    58 6f b3 13 2b ed 2f 8d 52 62 86 4a 9c b9 f3 0a
    f3 8b e4 48 59 8d 41 3a 17 2e fb 80 2c 21 ac f1
    c1 1c 52 0c 2f 26 a4 71 dc ad 21 2e ac 7c a3 9d

    # Prime 2:
    cc 88 53 d1 d5 4d a6 30 fa c0 04 f4 71 f2 81 c7
    b8 98 2d 82 24 a4 90 ed be b3 3d 3e 3d 5c c9 3c
    47 65 70 3d 1d d7 91 64 2f 1f 11 6a 0d d8 52 be
    24 19 b2 af 72 bf e9 a0 30 e8 60 b0 28 8b 5d 77

    # Prime exponent 1:
    0e 12 bf 17 18 e9 ce f5 59 9b a1 c3 88 2f e8 04
    6a 90 87 4e ef ce 8f 2c cc 20 e4 f2 74 1f b0 a3
    3a 38 48 ae c9 c9 30 5f be cb d2 d7 68 19 96 7d
    46 71 ac c6 43 1e 40 37 96 8d b3 78 78 e6 95 c1

    # Prime exponent 2:
    95 29 7b 0f 95 a2 fa 67 d0 07 07 d6 09 df d4 fc
    05 c8 9d af c2 ef 6d 6e a5 5b ec 77 1e a3 33 73
    4d 92 51 e7 90 82 ec da 86 6e fe f1 3c 45 9e 1a
    63 13 86 b7 e3 54 c8 99 f5 f1 12 ca 85 d7 15 83

    # Coefficient:
    4f 45 6c 50 24 93 bd c0 ed 2a b7 56 a3 a6 ed 4d
    67 35 2a 69 7d 42 16 e9 32 12 b1 27 a6 3d 54 11
    ce 6f a9 8d 5d be fd 73 26 3e 37 28 14 27 43 81
    81 66 ed 7d d6 36 87 dd 2a 8c a1 d2 f4 fb d8 e1

    # RSA-OAEP encryption of 6 random messages with random seeds
    # -----------------------------------------------------------

    # OAEP Example 1.1
    # ------------------

    # Message:
    66 28 19 4e 12 07 3d b0 3b a9 4c da 9e f9 53 23
    97 d5 0d ba 79 b9 87 00 4a fe fe 34

    # Seed:
    18 b7 76 ea 21 06 9d 69 77 6a 33 e9 6b ad 48 e1
    dd a0 a5 ef

    # Encryption:
    35 4f e6 7b 4a 12 6d 5d 35 fe 36 c7 77 79 1a 3f
    7b a1 3d ef 48 4e 2d 39 08 af f7 22 fa d4 68 fb
    21 69 6d e9 5d 0b e9 11 c2 d3 17 4f 8a fc c2 01
    03 5f 7b 6d 8e 69 40 2d e5 45 16 18 c2 1a 53 5f
    a9 d7 bf c5 b8 dd 9f c2 43 f8 cf 92 7d b3 13 22
    d6 e8 81 ea a9 1a 99 61 70 e6 57 a0 5a 26 64 26
    d9 8c 88 00 3f 84 77 c1 22 70 94 a0 d9 fa 1e 8c
    40 24 30 9c e1 ec cc b5 21 00 35 d4 7a c7 2e 8a

    # OAEP Example 1.2
    # ------------------

    # Message:
    75 0c 40 47 f5 47 e8 e4 14 11 85 65 23 29 8a c9
    ba e2 45 ef af 13 97 fb e5 6f 9d d5

    # Seed:
    0c c7 42 ce 4a 9b 7f 32 f9 51 bc b2 51 ef d9 25
    fe 4f e3 5f

    # Encryption:
    64 0d b1 ac c5 8e 05 68 fe 54 07 e5 f9 b7 01 df
    f8 c3 c9 1e 71 6c 53 6f c7 fc ec 6c b5 b7 1c 11
    65 98 8d 4a 27 9e 15 77 d7 30 fc 7a 29 93 2e 3f
    00 c8 15 15 23 6d 8d 8e 31 01 7a 7a 09 df 43 52
    d9 04 cd eb 79 aa 58 3a dc c3 1e a6 98 a4 c0 52
    83 da ba 90 89 be 54 91 f6 7c 1a 4e e4 8d c7 4b
    bb e6 64 3a ef 84 66 79 b4 cb 39 5a 35 2d 5e d1
    15 91 2d f6 96 ff e0 70 29 32 94 6d 71 49 2b 44

    # =============================================
    """).splitlines()

    vectors = load_pkcs1_vectors(vector_data)
    expected = [
        (
            {
                'modulus': int(
                    'a8b3b284af8eb50b387034a860f146c4919f318763cd6c5598c8ae481'
                    '1a1e0abc4c7e0b082d693a5e7fced675cf4668512772c0cbc64a742c6'
                    'c630f533c8cc72f62ae833c40bf25842e984bb78bdbf97c0107d55bdb'
                    '662f5c4e0fab9845cb5148ef7392dd3aaff93ae1e6b667bb3d4247616'
                    'd4f5ba10d4cfd226de88d39f16fb', 16),
                'public_exponent': int('10001', 16),
                'private_exponent': int(
                    '53339cfdb79fc8466a655c7316aca85c55fd8f6dd898fdaf119517ef4'
                    'f52e8fd8e258df93fee180fa0e4ab29693cd83b152a553d4ac4d1812b'
                    '8b9fa5af0e7f55fe7304df41570926f3311f15c4d65a732c483116ee3'
                    'd3d2d0af3549ad9bf7cbfb78ad884f84d5beb04724dc7369b31def37d'
                    '0cf539e9cfcdd3de653729ead5d1', 16),
                'p': int(
                    'd32737e7267ffe1341b2d5c0d150a81b586fb3132bed2f8d5262864a9'
                    'cb9f30af38be448598d413a172efb802c21acf1c11c520c2f26a471dc'
                    'ad212eac7ca39d', 16),
                'q': int(
                    'cc8853d1d54da630fac004f471f281c7b8982d8224a490edbeb33d3e3'
                    'd5cc93c4765703d1dd791642f1f116a0dd852be2419b2af72bfe9a030'
                    'e860b0288b5d77', 16),
                'dmp1': int(
                    '0e12bf1718e9cef5599ba1c3882fe8046a90874eefce8f2ccc20e4f27'
                    '41fb0a33a3848aec9c9305fbecbd2d76819967d4671acc6431e403796'
                    '8db37878e695c1', 16),
                'dmq1': int(
                    '95297b0f95a2fa67d00707d609dfd4fc05c89dafc2ef6d6ea55bec771'
                    'ea333734d9251e79082ecda866efef13c459e1a631386b7e354c899f5'
                    'f112ca85d71583', 16),
                'iqmp': int(
                    '4f456c502493bdc0ed2ab756a3a6ed4d67352a697d4216e93212b127a'
                    '63d5411ce6fa98d5dbefd73263e3728142743818166ed7dd63687dd2a'
                    '8ca1d2f4fbd8e1', 16),
                'examples': [
                    {
                        'message': b'6628194e12073db03ba94cda9ef9532397d50dba7'
                                   b'9b987004afefe34',
                        'seed': b'18b776ea21069d69776a33e96bad48e1dda0a5ef',
                        'encryption': b'354fe67b4a126d5d35fe36c777791a3f7ba13d'
                                      b'ef484e2d3908aff722fad468fb21696de95d0b'
                                      b'e911c2d3174f8afcc201035f7b6d8e69402de5'
                                      b'451618c21a535fa9d7bfc5b8dd9fc243f8cf92'
                                      b'7db31322d6e881eaa91a996170e657a05a2664'
                                      b'26d98c88003f8477c1227094a0d9fa1e8c4024'
                                      b'309ce1ecccb5210035d47ac72e8a'
                    }, {
                        'message': b'750c4047f547e8e41411856523298ac9bae245efa'
                                   b'f1397fbe56f9dd5',
                        'seed': b'0cc742ce4a9b7f32f951bcb251efd925fe4fe35f',
                        'encryption': b'640db1acc58e0568fe5407e5f9b701dff8c3c9'
                                      b'1e716c536fc7fcec6cb5b71c1165988d4a279e'
                                      b'1577d730fc7a29932e3f00c81515236d8d8e31'
                                      b'017a7a09df4352d904cdeb79aa583adcc31ea6'
                                      b'98a4c05283daba9089be5491f67c1a4ee48dc7'
                                      b'4bbbe6643aef846679b4cb395a352d5ed11591'
                                      b'2df696ffe0702932946d71492b44'
                    }
                ]
            },

            {
                'modulus': int(
                    'a8b3b284af8eb50b387034a860f146c4919f318763cd6c5598c8ae481'
                    '1a1e0abc4c7e0b082d693a5e7fced675cf4668512772c0cbc64a742c6'
                    'c630f533c8cc72f62ae833c40bf25842e984bb78bdbf97c0107d55bdb'
                    '662f5c4e0fab9845cb5148ef7392dd3aaff93ae1e6b667bb3d4247616'
                    'd4f5ba10d4cfd226de88d39f16fb', 16),
                'public_exponent': int('10001', 16),
            }
        )
    ]
    assert vectors == expected


def test_load_hotp_vectors():
    vector_data = textwrap.dedent("""
    # HOTP Test Vectors
    # RFC 4226 Appendix D

    COUNT = 0
    COUNTER = 0
    INTERMEDIATE = cc93cf18508d94934c64b65d8ba7667fb7cde4b0
    TRUNCATED = 4c93cf18
    HOTP = 755224
    SECRET = 12345678901234567890

    COUNT = 1
    COUNTER = 1
    INTERMEDIATE = 75a48a19d4cbe100644e8ac1397eea747a2d33ab
    TRUNCATED = 41397eea
    HOTP = 287082
    SECRET = 12345678901234567890


    COUNT = 2
    COUNTER = 2
    INTERMEDIATE = 0bacb7fa082fef30782211938bc1c5e70416ff44
    TRUNCATED = 82fef30
    HOTP = 359152
    SECRET = 12345678901234567890


    COUNT = 3
    COUNTER = 3
    INTERMEDIATE = 66c28227d03a2d5529262ff016a1e6ef76557ece
    TRUNCATED = 66ef7655
    HOTP = 969429
    SECRET = 12345678901234567890
    """).splitlines()

    assert load_nist_vectors(vector_data) == [
        {
            "counter": b"0",
            "intermediate": b"cc93cf18508d94934c64b65d8ba7667fb7cde4b0",
            "truncated": b"4c93cf18",
            "hotp": b"755224",
            "secret": b"12345678901234567890",
        },
        {
            "counter": b"1",
            "intermediate": b"75a48a19d4cbe100644e8ac1397eea747a2d33ab",
            "truncated": b"41397eea",
            "hotp": b"287082",
            "secret": b"12345678901234567890",
        },
        {
            "counter": b"2",
            "intermediate": b"0bacb7fa082fef30782211938bc1c5e70416ff44",
            "truncated": b"82fef30",
            "hotp": b"359152",
            "secret": b"12345678901234567890",
        },
        {
            "counter": b"3",
            "intermediate": b"66c28227d03a2d5529262ff016a1e6ef76557ece",
            "truncated": b"66ef7655",
            "hotp": b"969429",
            "secret": b"12345678901234567890",
        },
    ]


def test_load_totp_vectors():
    vector_data = textwrap.dedent("""
    # TOTP Test Vectors
    # RFC 6238 Appendix B

    COUNT = 0
    TIME = 59
    TOTP = 94287082
    MODE = SHA1
    SECRET = 12345678901234567890

    COUNT = 1
    TIME = 59
    TOTP = 46119246
    MODE = SHA256
    SECRET = 12345678901234567890

    COUNT = 2
    TIME = 59
    TOTP = 90693936
    MODE = SHA512
    SECRET = 12345678901234567890
    """).splitlines()

    assert load_nist_vectors(vector_data) == [
        {
            "time": b"59",
            "totp": b"94287082",
            "mode": b"SHA1",
            "secret": b"12345678901234567890",
        },
        {
            "time": b"59",
            "totp": b"46119246",
            "mode": b"SHA256",
            "secret": b"12345678901234567890",
        },
        {
            "time": b"59",
            "totp": b"90693936",
            "mode": b"SHA512",
            "secret": b"12345678901234567890",
        },
    ]


def test_load_rsa_nist_vectors():
    vector_data = textwrap.dedent("""
    # CAVS 11.4
    # "SigGen PKCS#1 RSASSA-PSS" information
    # Mod sizes selected: 1024 1536 2048 3072 4096
    # SHA Algorithm selected:SHA1 SHA224 SHA256 SHA384 SHA512
    # Salt len: 20

    [mod = 1024]

    n = bcb47b2e0dafcba81ff2a2b5cb115ca7e757184c9d72bcdcda707a146b3b4e29989d

    e = 00000000000000000000000000000000000000000000000000000000000000000010001
    SHAAlg = SHA1
    Msg = 1248f62a4389f42f7b4bb131053d6c88a994db2075b912ccbe3ea7dc611714f14e
    S = 682cf53c1145d22a50caa9eb1a9ba70670c5915e0fdfde6457a765de2a8fe12de97

    SHAAlg = SHA384
    Msg = e511903c2f1bfba245467295ac95413ac4746c984c3750a728c388aa628b0ebf
    S = 9c748702bbcc1f9468864cd360c8c39d007b2d8aaee833606c70f7593cf0d1519

    [mod = 1024]

    n = 1234567890

    e = 0010001

    SHAAlg = SHA512
    Msg = 3456781293fab829
    S = deadbeef0000
    """).splitlines()

    vectors = load_rsa_nist_vectors(vector_data)
    assert vectors == [
        {
            "modulus": int("bcb47b2e0dafcba81ff2a2b5cb115ca7e757184c9d72bcdcda"
                           "707a146b3b4e29989d", 16),
            "public_exponent": 65537,
            "algorithm": "SHA1",
            "salt_length": 20,
            "msg": b"1248f62a4389f42f7b4bb131053d6c88a994db2075b912ccbe3ea7dc6"
                   b"11714f14e",
            "s": b"682cf53c1145d22a50caa9eb1a9ba70670c5915e0fdfde6457a765de2a8"
                 b"fe12de97",
            "fail": False
        },
        {
            "modulus": int("bcb47b2e0dafcba81ff2a2b5cb115ca7e757184c9d72bcdcda"
                           "707a146b3b4e29989d", 16),
            "public_exponent": 65537,
            "algorithm": "SHA384",
            "salt_length": 20,
            "msg": b"e511903c2f1bfba245467295ac95413ac4746c984c3750a728c388aa6"
                   b"28b0ebf",
            "s": b"9c748702bbcc1f9468864cd360c8c39d007b2d8aaee833606c70f7593cf"
                 b"0d1519",
            "fail": False
        },
        {
            "modulus": 78187493520,
            "public_exponent": 65537,
            "algorithm": "SHA512",
            "salt_length": 20,
            "msg": b"3456781293fab829",
            "s": b"deadbeef0000",
            "fail": False
        },
    ]


def test_load_rsa_nist_pkcs1v15_verification_vectors():
    vector_data = textwrap.dedent("""
    # CAVS 11.0
    # "SigVer PKCS#1 Ver 1.5" information
    # Mod sizes selected: 1024 1536 2048 3072 4096
    # SHA Algorithm selected:SHA1 SHA224 SHA256 SHA384 SHA512
    # Generated on Wed Mar 02 00:13:02 2011

    [mod = 1024]

    n = be499b5e7f06c83fa0293e31465c8eb6b58af920bae52a7b5b9bfeb7aa72db126411

    p = e7a80c5d211c06acb900939495f26d365fc2b4825b75e356f89003eaa5931e6be5c3
    q = d248aa248000f720258742da67b711940c8f76e1ecd52b67a6ffe1e49354d66ff84f

    SHAAlg = SHA1
    e = 00000000000000000000000000000000000000000000000000000000000000000011
    d = 0d0f17362bdad181db4e1fe03e8de1a3208989914e14bf269558826bfa20faf4b68d
    Msg = 6b9cfac0ba1c7890b13e381ce752195cc1375237db2afcf6a9dcd1f95ec733a80c
    S = 562d87b5781c01d166fef3972669a0495c145b898a17df4743fbefb0a1582bd6ba9d
    SaltVal = 11223344555432167890
    Result = F (3 - Signature changed )

    SHAAlg = SHA1
    e = 0000000000003
    d = bfa20faf4b68d
    Msg = 2a67c70ff14f9b34ddb42e6f89d5971057a0da980fc9ae70c81a84da0c0ac42737
    S = 2b91c6ae2b3c46ff18d5b7abe239634cb752d0acb53eea0ccd8ea8483036a50e8faf
    SaltVal = 11223344555432167890
    Result = P
    """).splitlines()

    vectors = load_rsa_nist_vectors(vector_data)
    assert vectors == [
        {
            "modulus": int("be499b5e7f06c83fa0293e31465c8eb6b58af920bae52a7b5b"
                           "9bfeb7aa72db126411", 16),
            "p": int("e7a80c5d211c06acb900939495f26d365fc2b4825b75e356f89003ea"
                     "a5931e6be5c3", 16),
            "q": int("d248aa248000f720258742da67b711940c8f76e1ecd52b67a6ffe1e4"
                     "9354d66ff84f", 16),
            "public_exponent": 17,
            "algorithm": "SHA1",
            "private_exponent": int("0d0f17362bdad181db4e1fe03e8de1a3208989914"
                                    "e14bf269558826bfa20faf4b68d", 16),
            "msg": b"6b9cfac0ba1c7890b13e381ce752195cc1375237db2afcf6a9dcd1f95"
                   b"ec733a80c",
            "s": b"562d87b5781c01d166fef3972669a0495c145b898a17df4743fbefb0a15"
                 b"82bd6ba9d",
            "saltval": b"11223344555432167890",
            "fail": True
        },
        {
            "modulus": int("be499b5e7f06c83fa0293e31465c8eb6b58af920bae52a7b5b"
                           "9bfeb7aa72db126411", 16),
            "p": int("e7a80c5d211c06acb900939495f26d365fc2b4825b75e356f89003ea"
                     "a5931e6be5c3", 16),
            "q": int("d248aa248000f720258742da67b711940c8f76e1ecd52b67a6ffe1e4"
                     "9354d66ff84f", 16),
            "public_exponent": 3,
            "algorithm": "SHA1",
            "private_exponent": int("bfa20faf4b68d", 16),
            "msg": b"2a67c70ff14f9b34ddb42e6f89d5971057a0da980fc9ae70c81a84da0"
                   b"c0ac42737",
            "s": b"2b91c6ae2b3c46ff18d5b7abe239634cb752d0acb53eea0ccd8ea848303"
                 b"6a50e8faf",
            "saltval": b"11223344555432167890",
            "fail": False
        },
    ]


def test_load_rsa_nist_pss_verification_vectors():
    vector_data = textwrap.dedent("""
    # CAVS 11.0
    # "SigVer PKCS#1 RSASSA-PSS" information
    # Mod sizes selected: 1024 1536 2048 3072 4096
    # SHA Algorithm selected:SHA1 SHA224 SHA256 SHA384 SHA512
    # Salt len: 10
    # Generated on Wed Mar 02 00:25:22 2011

    [mod = 1024]

    n = be499b5e7f06c83fa0293e31465c8eb6b5

    p = e7a80c5d211c06acb900939495f26d365f
    q = d248aa248000f720258742da67b711940c

    SHAAlg = SHA1
    e = 00000000000000011
    d = c8e26a88239672cf49b3422a07c4d834ba
    Msg = 6b9cfac0ba1c7890b13e381ce752195c
    S = 562d87b5781c01d166fef3972669a0495c
    SaltVal = 11223344555432167890
    Result = F (3 - Signature changed )

    SHAAlg = SHA384
    e = 000003
    d = 0d0f17362bdad181db4e1fe03e8de1a320
    Msg = 2a67c70ff14f9b34ddb42e6f89d59710
    S = 2b91c6ae2b3c46ff18d5b7abe239634cb7
    SaltVal = 11223344555432167890
    Result = P
    """).splitlines()

    vectors = load_rsa_nist_vectors(vector_data)
    assert vectors == [
        {
            "modulus": int("be499b5e7f06c83fa0293e31465c8eb6b5", 16),
            "p": int("e7a80c5d211c06acb900939495f26d365f", 16),
            "q": int("d248aa248000f720258742da67b711940c", 16),
            "public_exponent": 17,
            "algorithm": "SHA1",
            "private_exponent": int("c8e26a88239672cf49b3422a07c4d834ba", 16),
            "msg": b"6b9cfac0ba1c7890b13e381ce752195c",
            "s": b"562d87b5781c01d166fef3972669a0495c",
            "saltval": b"11223344555432167890",
            "salt_length": 10,
            "fail": True
        },
        {
            "modulus": int("be499b5e7f06c83fa0293e31465c8eb6b5", 16),
            "p": int("e7a80c5d211c06acb900939495f26d365f", 16),
            "q": int("d248aa248000f720258742da67b711940c", 16),
            "public_exponent": 3,
            "algorithm": "SHA384",
            "private_exponent": int("0d0f17362bdad181db4e1fe03e8de1a320", 16),
            "msg": b"2a67c70ff14f9b34ddb42e6f89d59710",
            "s": b"2b91c6ae2b3c46ff18d5b7abe239634cb7",
            "saltval": b"11223344555432167890",
            "salt_length": 10,
            "fail": False
        },
    ]


def test_load_fips_dsa_key_pair_vectors():
    vector_data = textwrap.dedent("""
    #  CAVS 11.1
    #  "KeyPair" information
    #  Mod sizes selected: L=1024, N=160:: L=2048, N=224 :: L=2048, N=256 :: L
=3072, N=256
    # Generated on Wed May 04 08:50:52 2011


    [mod = L=1024, N=160]

    P = d38311e2cd388c3ed698e82fdf88eb92b5a9a483dc88005d4b725ef341eabb47cf8a7a\
8a41e792a156b7ce97206c4f9c5ce6fc5ae7912102b6b502e59050b5b21ce263dddb2044b65223\
6f4d42ab4b5d6aa73189cef1ace778d7845a5c1c1c7147123188f8dc551054ee162b634d60f097\
f719076640e20980a0093113a8bd73
    Q = 96c5390a8b612c0e422bb2b0ea194a3ec935a281
    G = 06b7861abbd35cc89e79c52f68d20875389b127361ca66822138ce4991d2b862259d6b\
4548a6495b195aa0e0b6137ca37eb23b94074d3c3d300042bdf15762812b6333ef7b07ceba7860\
7610fcc9ee68491dbc1e34cd12615474e52b18bc934fb00c61d39e7da8902291c4434a4e2224c3\
f4fd9f93cd6f4f17fc076341a7e7d9

    X = 8185fee9cc7c0e91fd85503274f1cd5a3fd15a49
    Y = 6f26d98d41de7d871b6381851c9d91fa03942092ab6097e76422070edb71db44ff5682\
80fdb1709f8fc3feab39f1f824adaeb2a298088156ac31af1aa04bf54f475bdcfdcf2f8a2dd973\
e922d83e76f016558617603129b21c70bf7d0e5dc9e68fe332e295b65876eb9a12fe6fca9f1a1c\
e80204646bf99b5771d249a6fea627

    X = 85322d6ea73083064376099ca2f65f56e8522d9b
    Y = 21f8690f717c9f4dcb8f4b6971de2f15b9231fcf41b7eeb997d781f240bfdddfd2090d\
22083c26cca39bf37c9caf1ec89518ea64845a50d747b49131ffff6a2fd11ea7bacbb93c7d0513\
7383a06365af82225dd3713ca5a45006316f53bd12b0e260d5f79795e5a4c9f353f12867a1d320\
2394673ada8563b71555e53f415254

    [mod = L=2048, N=224]

    P = 904ef8e31e14721910fa0969e77c99b79f190071a86026e37a887a6053960dbfb74390\
a6641319fe0af32c4e982934b0f1f4c5bc57534e8e56d77c36f0a99080c0d5bc9022fa34f58922\
81d7b1009571cb5b35699303f912b276d86b1b0722fc0b1500f0ffb2e4d90867a3bdca181a9734\
617a8a9f991aa7c14dec1cf45ceba00600f8425440ed0c3b52c82e3aa831932a98b477da220867\
eb2d5e0ca34580b33b1b65e558411ed09c369f4717bf03b551787e13d9e47c267c91c697225265\
da157945cd8b32e84fc45b80533265239aa00a2dd3d05f5cb231b7daf724b7ecdce170360a8397\
2e5be94626273d449f441be300a7345db387bebadad67d8060a7
    Q = d7d0a83e84d13032b830ed74a6a88592ec9a4cf42bf37080c6600aad
    G = 2050b18d3c9f39fac396c009310d6616f9309b67b59aef9aee813d6b4f12ee29ba8a6b\
350b11d4336d44b4641230002d870f1e6b1d8728bdd40262df0d2440999185ae077f7034c61679\
f4360fbb5d181569e7cb8acb04371c11ba55f1bbd777b74304b99b66d4405303e7120dc8bc4785\
f56e9533e65b63a0c77cce7bba0d5d6069df5edffa927c5a255a09405a008258ed93506a843366\
2154f6f67e922d7c9788f04d4ec09581063950d9cde8e373ea59a58b2a6df6ba8663345574fabb\
a9ca981696d83aeac1f34f14f1a813ba900b3f0341dea23f7d3297f919a97e1ae00ac0728c93fe\
0a88b66591baf4eb0bc6900f39ba5feb41cbbeea7eb7919aa4d3

    X = 3f19424da3b4f0cafca3fc5019fcd225dd7e496ffdf6b77e364f45be
    Y = 7681ed0ac257ab7ff17c52de4638c0614749792707a0c0d23883697e34963df15c806f\
a6206f7fafb3269018e7703bd1e6f518d13544331a017713dbbe0cee8da6c095271fbf24edb74a\
44e18b1d3b835622f68d31921c67c83e8479d1972ed0cb106c68188fe22c044254251ebf880b90\
49dc3b7958ef61e1e67d2f677d2a7d2ab6b7c42b70cc5dedc3e5de7459a2dbc70c69008553d7ff\
b6bf81c012c8bd67bdddeaab9a4a4373027912a7c7d9cd9cfc6c81dffe0cc7a6d40c3b2065aee7\
be80e3c35497d64c8045bc511edaf7314c84c56bd9f0fecf62262ea5b45b49a0cffb223713bdbd\
3ad03a25a0bb2211eba41ffcd08ab0e1ad485c29a3fc25ee8359

    X = 241396352dd26efe0e2e184da52fe2b61d9d51b91b5009674c447854
    Y = 2f07a3aa9884c65288e5fef56c7b7f4445632273290bae6fcaab87c90058b2bef81ad3\
34958657cf649ffb976d618b34ce69ef6d68c0d8bfe275cf097a301e8dd5595958e0c668c15f67\
b5c0b0d01983057ce61593635aab5e0564ed720b0336f055a86755c76be22df3b8487f16e2ba0b\
5136fd30d7e3b1d30c3bd298d3acc0a1988a11756c94e9a53184d0d3edfbb649caf03eace3083d\
e9933921e627f4b2e011d1c79e45d8ea1eb7e4e59a1cbd8382b3238474eb949749c985200fbb25\
41e2dce080aa881945d4d935076e48a0846dc5513bb4da8563b946af54f546455931e79c065ce7\
ca223a98f8fde40091d38eb2c3eb8e3b81d88374f3146b0afc42

    [mod = L=2048, N=256]

    P = ea1fb1af22881558ef93be8a5f8653c5a559434c49c8c2c12ace5e9c41434c9cf0a8e9\
498acb0f4663c08b4484eace845f6fb17dac62c98e706af0fc74e4da1c6c2b3fbf5a1d58ff82fc\
1a66f3e8b12252c40278fff9dd7f102eed2cb5b7323ebf1908c234d935414dded7f8d244e54561\
b0dca39b301de8c49da9fb23df33c6182e3f983208c560fb5119fbf78ebe3e6564ee235c6a15cb\
b9ac247baba5a423bc6582a1a9d8a2b4f0e9e3d9dbac122f750dd754325135257488b1f6ecabf2\
1bff2947fe0d3b2cb7ffe67f4e7fcdf1214f6053e72a5bb0dd20a0e9fe6db2df0a908c36e95e60\
bf49ca4368b8b892b9c79f61ef91c47567c40e1f80ac5aa66ef7
    Q = 8ec73f3761caf5fdfe6e4e82098bf10f898740dcb808204bf6b18f507192c19d
    G = e4c4eca88415b23ecf811c96e48cd24200fe916631a68a684e6ccb6b1913413d344d1d\
8d84a333839d88eee431521f6e357c16e6a93be111a98076739cd401bab3b9d565bf4fb99e9d18\
5b1e14d61c93700133f908bae03e28764d107dcd2ea7674217622074bb19efff482f5f5c1a86d5\
551b2fc68d1c6e9d8011958ef4b9c2a3a55d0d3c882e6ad7f9f0f3c61568f78d0706b10a26f23b\
4f197c322b825002284a0aca91807bba98ece912b80e10cdf180cf99a35f210c1655fbfdd74f13\
b1b5046591f8403873d12239834dd6c4eceb42bf7482e1794a1601357b629ddfa971f2ed273b14\
6ec1ca06d0adf55dd91d65c37297bda78c6d210c0bc26e558302

    X = 405772da6e90d809e77d5de796562a2dd4dfd10ef00a83a3aba6bd818a0348a1
    Y = 6b32e31ab9031dc4dd0b5039a78d07826687ab087ae6de4736f5b0434e1253092e8a0b\
231f9c87f3fc8a4cb5634eb194bf1b638b7a7889620ce6711567e36aa36cda4604cfaa601a4591\
8371d4ccf68d8b10a50a0460eb1dc0fff62ef5e6ee4d473e18ea4a66c196fb7e677a49b48241a0\
b4a97128eff30fa437050501a584f8771e7280d26d5af30784039159c11ebfea10b692fd0a5821\
5eeb18bff117e13f08db792ed4151a218e4bed8dddfb0793225bd1e9773505166f4bd8cedbb286\
ea28232972da7bae836ba97329ba6b0a36508e50a52a7675e476d4d4137eae13f22a9d2fefde70\
8ba8f34bf336c6e76331761e4b0617633fe7ec3f23672fb19d27

    X = 0e0b95e31fda3f888059c46c3002ef8f2d6be112d0209aeb9e9545da67aeea80
    Y = 778082b77ddba6f56597cc74c3a612abf2ddbd85cc81430c99ab843c1f630b9db01399\
65f563978164f9bf3a8397256be714625cd41cd7fa0067d94ea66d7e073f7125af692ad01371d4\
a17f4550590378f2b074030c20e36911598a1018772f61be3b24de4be5a388ccc09e15a92819c3\
1dec50de9fde105b49eaa097b9d13d9219eeb33b628facfd1c78a7159c8430d0647c506e7e3de7\
4763cb351eada72c00bef3c9641881e6254870c1e6599f8ca2f1bbb74f39a905e3a34e4544168e\
6e50c9e3305fd09cab6ed4aff6fda6e0d5bf375c81ac9054406d9193b003c89272f1bd83d48250\
134b65c77c2b6332d38d34d9016f0e8975536ad6c348a1faedb0

    [mod = L=3072, N=256]

    P = f335666dd1339165af8b9a5e3835adfe15c158e4c3c7bd53132e7d5828c352f593a9a7\
87760ce34b789879941f2f01f02319f6ae0b756f1a842ba54c85612ed632ee2d79ef17f06b77c6\
41b7b080aff52a03fc2462e80abc64d223723c236deeb7d201078ec01ca1fbc1763139e25099a8\
4ec389159c409792080736bd7caa816b92edf23f2c351f90074aa5ea2651b372f8b58a0a65554d\
b2561d706a63685000ac576b7e4562e262a14285a9c6370b290e4eb7757527d80b6c0fd5df831d\
36f3d1d35f12ab060548de1605fd15f7c7aafed688b146a02c945156e284f5b71282045aba9844\
d48b5df2e9e7a5887121eae7d7b01db7cdf6ff917cd8eb50c6bf1d54f90cce1a491a9c74fea88f\
7e7230b047d16b5a6027881d6f154818f06e513faf40c8814630e4e254f17a47bfe9cb519b9828\
9935bf17673ae4c8033504a20a898d0032ee402b72d5986322f3bdfb27400561f7476cd715eaab\
b7338b854e51fc2fa026a5a579b6dcea1b1c0559c13d3c1136f303f4b4d25ad5b692229957
    Q = d3eba6521240694015ef94412e08bf3cf8d635a455a398d6f210f6169041653b
    G = ce84b30ddf290a9f787a7c2f1ce92c1cbf4ef400e3cd7ce4978db2104d7394b493c183\
32c64cec906a71c3778bd93341165dee8e6cd4ca6f13afff531191194ada55ecf01ff94d6cf7c4\
768b82dd29cd131aaf202aefd40e564375285c01f3220af4d70b96f1395420d778228f1461f5d0\
b8e47357e87b1fe3286223b553e3fc9928f16ae3067ded6721bedf1d1a01bfd22b9ae85fce7782\
0d88cdf50a6bde20668ad77a707d1c60fcc5d51c9de488610d0285eb8ff721ff141f93a9fb23c1\
d1f7654c07c46e58836d1652828f71057b8aff0b0778ef2ca934ea9d0f37daddade2d823a4d8e3\
62721082e279d003b575ee59fd050d105dfd71cd63154efe431a0869178d9811f4f231dc5dcf3b\
0ec0f2b0f9896c32ec6c7ee7d60aa97109e09224907328d4e6acd10117e45774406c4c947da802\
0649c3168f690e0bd6e91ac67074d1d436b58ae374523deaf6c93c1e6920db4a080b744804bb07\
3cecfe83fa9398cf150afa286dc7eb7949750cf5001ce104e9187f7e16859afa8fd0d775ae

    X = b2764c46113983777d3e7e97589f1303806d14ad9f2f1ef033097de954b17706
    Y = 814824e435e1e6f38daa239aad6dad21033afce6a3ebd35c1359348a0f2418871968c2\
babfc2baf47742148828f8612183178f126504da73566b6bab33ba1f124c15aa461555c2451d86\
c94ee21c3e3fc24c55527e01b1f03adcdd8ec5cb08082803a7b6a829c3e99eeb332a2cf5c035b0\
ce0078d3d414d31fa47e9726be2989b8d06da2e6cd363f5a7d1515e3f4925e0b32adeae3025cc5\
a996f6fd27494ea408763de48f3bb39f6a06514b019899b312ec570851637b8865cff3a52bf5d5\
4ad5a19e6e400a2d33251055d0a440b50d53f4791391dc754ad02b9eab74c46b4903f9d76f8243\
39914db108057af7cde657d41766a99991ac8787694f4185d6f91d7627048f827b405ec67bf2fe\
56141c4c581d8c317333624e073e5879a82437cb0c7b435c0ce434e15965db1315d64895991e6b\
be7dac040c42052408bbc53423fd31098248a58f8a67da3a39895cd0cc927515d044c1e3cb6a32\
59c3d0da354cce89ea3552c59609db10ee989986527436af21d9485ddf25f90f7dff6d2bae

    X = 52e3e040efb30e1befd909a0bdbcfd140d005b1bff094af97186080262f1904d
    Y = a5ae6e8f9b7a68ab0516dad4d7b7d002126f811d5a52e3d35c6d387fcb43fd19bf7792\
362f9c98f8348aa058bb62376685f3d0c366c520d697fcd8416947151d4bbb6f32b53528a01647\
9e99d2cd48d1fc679027c15f0042f207984efe05c1796bca8eba678dfdd00b80418e3ea840557e\
73b09e003882f9a68edba3431d351d1ca07a8150b018fdbdf6c2f1ab475792a3ccaa6594472a45\
f8dc777b60bf67de3e0f65c20d11b7d59faedf83fbce52617f500d9e514947c455274c6e900464\
767fb56599b81344cf6d12c25cb2b7d038d7b166b6cf30534811c15d0e8ab880a2ac06786ae2dd\
de61329a78d526f65245380ce877e979c5b50de66c9c30d66382c8f254653d25a1eb1d3a4897d7\
623399b473ce712a2184cf2da1861706c41466806aefe41b497db82aca6c31c8f4aa68c17d1d9e\
380b57998917655783ec96e5234a131f7299398d36f1f5f84297a55ff292f1f060958c358fed34\
6db2de45127ca728a9417b2c54203e33e53b9a061d924395b09afab8daf3e8dd7eedcec3ac
    """).splitlines()

    expected = [
        {'g': int('06b7861abbd35cc89e79c52f68d20875389b127361ca66822138ce499'
                  '1d2b862259d6b4548a6495b195aa0e0b6137ca37eb23b94074d3c3d3000'
                  '42bdf15762812b6333ef7b07ceba78607610fcc9ee68491dbc1e34cd12'
                  '615474e52b18bc934fb00c61d39e7da8902291c4434a4e2224c3f'
                  '4fd9f93cd6f4f17fc076341a7e7d9', 16),
         'p': int('d38311e2cd388c3ed698e82fdf88eb92b5a9a483dc88005d4b725e'
                  'f341eabb47cf8a7a8a41e792a156b7ce97206c4f9c5ce6fc5ae791210'
                  '2b6b502e59050b5b21ce263dddb2044b652236f4d42ab4b5d6aa73189c'
                  'ef1ace778d7845a5c1c1c7147123188f8dc551054ee162b634d60f097f7'
                  '19076640e20980a0093113a8bd73', 16),
         'q': int('96c5390a8b612c0e422bb2b0ea194a3ec935a281', 16),
         'x': int('8185fee9cc7c0e91fd85503274f1cd5a3fd15a49', 16),
         'y': int('6f26d98d41de7d871b6381851c9d91fa03942092ab6097e76422'
                  '070edb71db44ff568280fdb1709f8fc3feab39f1f824adaeb2a29808815'
                  '6ac31af1aa04bf54f475bdcfdcf2f8a2dd973e922d83e76f01655861760'
                  '3129b21c70bf7d0e5dc9e68fe332e295b65876eb9a12fe6fca9f1a1ce80'
                  '204646bf99b5771d249a6fea627', 16)},
        {'g': int('06b7861abbd35cc89e79c52f68d20875389b127361ca66822138ce4991d'
                  '2b862259d6b4548a6495b195aa0e0b6137ca37eb23b94074d3c3d30004'
                  '2bdf15762812b6333ef7b07ceba78607610fcc9ee68491dbc1e34cd126'
                  '15474e52b18bc934fb00c61d39e7da8902291c4434a4e2224c3f4fd9'
                  'f93cd6f4f17fc076341a7e7d9', 16),
         'p': int('d38311e2cd388c3ed698e82fdf88eb92b5a9a483dc88005d4b725ef341e'
                  'abb47cf8a7a8a41e792a156b7ce97206c4f9c5ce6fc5ae7912102b6b50'
                  '2e59050b5b21ce263dddb2044b652236f4d42ab4b5d6aa73189cef1a'
                  'ce778d7845a5c1c1c7147123188f8dc551054ee162b634d6'
                  '0f097f719076640e20980a0093113a8bd73', 16),
         'q': int('96c5390a8b612c0e422bb2b0ea194a3ec935a281', 16),
         'x': int('85322d6ea73083064376099ca2f65f56e8522d9b', 16),
         'y': int('21f8690f717c9f4dcb8f4b6971de2f15b9231fcf41b7eeb997d781f240'
                  'bfdddfd2090d22083c26cca39bf37c9caf1ec89518ea64845a50d747b49'
                  '131ffff6a2fd11ea7bacbb93c7d05137383a06365af82225dd3713c'
                  'a5a45006316f53bd12b0e260d5f79795e5a4c9f353f12867a1d3'
                  '202394673ada8563b71555e53f415254', 16)},

        {'g': int('e4c4eca88415b23ecf811c96e48cd24200fe916631a68a684e6ccb6b191'
                  '3413d344d1d8d84a333839d88eee431521f6e357c16e6a93be111a9807'
                  '6739cd401bab3b9d565bf4fb99e9d185b1e14d61c93700133f908bae0'
                  '3e28764d107dcd2ea7674217622074bb19efff482f5f5c1a86d5551b2'
                  'fc68d1c6e9d8011958ef4b9c2a3a55d0d3c882e6ad7f9f0f3c61568f78'
                  'd0706b10a26f23b4f197c322b825002284a0aca91807bba98ece912'
                  'b80e10cdf180cf99a35f210c1655fbfdd74f13b1b5046591f8403873d'
                  '12239834dd6c4eceb42bf7482e1794a1601357b629ddfa971f2ed273b1'
                  '46ec1ca06d0adf55dd91d65c37297bda78c6d210c0bc26e558302', 16),
         'p': int('ea1fb1af22881558ef93be8a5f8653c5a559434c49c8c2c12ace'
                  '5e9c41434c9cf0a8e9498acb0f4663c08b4484eace845f6fb17d'
                  'ac62c98e706af0fc74e4da1c6c2b3fbf5a1d58ff82fc1a66f3e8b122'
                  '52c40278fff9dd7f102eed2cb5b7323ebf1908c234d935414dded7f8d2'
                  '44e54561b0dca39b301de8c49da9fb23df33c6182e3f983208c560fb5'
                  '119fbf78ebe3e6564ee235c6a15cbb9ac247baba5a423bc6582a1a9d8a'
                  '2b4f0e9e3d9dbac122f750dd754325135257488b1f6ecabf21bff2947'
                  'fe0d3b2cb7ffe67f4e7fcdf1214f6053e72a5bb0dd20a0e9fe6db2df0a'
                  '908c36e95e60bf49ca4368b8b892b9c79f61ef91c47567c40e1f80ac'
                  '5aa66ef7', 16),
         'q': int('8ec73f3761caf5fdfe6e4e82098bf10f898740dcb808204bf6b1'
                  '8f507192c19d', 16),
         'x': int('405772da6e90d809e77d5de796562a2dd4dfd10ef00a83a3aba6'
                  'bd818a0348a1', 16),
         'y': int('6b32e31ab9031dc4dd0b5039a78d07826687ab087ae6de4736f5'
                  'b0434e1253092e8a0b231f9c87f3fc8a4cb5634eb194bf1b638'
                  'b7a7889620ce6711567e36aa36cda4604cfaa601a45918371d'
                  '4ccf68d8b10a50a0460eb1dc0fff62ef5e6ee4d473e18ea4a6'
                  '6c196fb7e677a49b48241a0b4a97128eff30fa437050501a584'
                  'f8771e7280d26d5af30784039159c11ebfea10b692fd0a58215ee'
                  'b18bff117e13f08db792ed4151a218e4bed8dddfb0793225bd1e97'
                  '73505166f4bd8cedbb286ea28232972da7bae836ba97329ba6b0a36508'
                  'e50a52a7675e476d4d4137eae13f22a9d2fefde708ba8f34bf336c6e7'
                  '6331761e4b0617633fe7ec3f23672fb19d27', 16)},
        {'g': int('e4c4eca88415b23ecf811c96e48cd24200fe916631a68a684e6ccb6b191'
                  '3413d344d1d8d84a333839d88eee431521f6e357c16e6a93be111a9807'
                  '6739cd401bab3b9d565bf4fb99e9d185b1e14d61c93700133f908bae0'
                  '3e28764d107dcd2ea7674217622074bb19efff482f5f5c1a86d5551b2'
                  'fc68d1c6e9d8011958ef4b9c2a3a55d0d3c882e6ad7f9f0f3c61568f78'
                  'd0706b10a26f23b4f197c322b825002284a0aca91807bba98ece912'
                  'b80e10cdf180cf99a35f210c1655fbfdd74f13b1b5046591f8403873d'
                  '12239834dd6c4eceb42bf7482e1794a1601357b629ddfa971f2ed273b1'
                  '46ec1ca06d0adf55dd91d65c37297bda78c6d210c0bc26e558302', 16),
         'p': int('ea1fb1af22881558ef93be8a5f8653c5a559434c49c8c2c12ace'
                  '5e9c41434c9cf0a8e9498acb0f4663c08b4484eace845f6fb17d'
                  'ac62c98e706af0fc74e4da1c6c2b3fbf5a1d58ff82fc1a66f3e8b122'
                  '52c40278fff9dd7f102eed2cb5b7323ebf1908c234d935414dded7f8d2'
                  '44e54561b0dca39b301de8c49da9fb23df33c6182e3f983208c560fb5'
                  '119fbf78ebe3e6564ee235c6a15cbb9ac247baba5a423bc6582a1a9d8a'
                  '2b4f0e9e3d9dbac122f750dd754325135257488b1f6ecabf21bff2947'
                  'fe0d3b2cb7ffe67f4e7fcdf1214f6053e72a5bb0dd20a0e9fe6db2df0a'
                  '908c36e95e60bf49ca4368b8b892b9c79f61ef91c47567c40e1f80ac'
                  '5aa66ef7', 16),
         'q': int('8ec73f3761caf5fdfe6e4e82098bf10f898740dcb808204bf6b1'
                  '8f507192c19d', 16),
         'x': int('0e0b95e31fda3f888059c46c3002ef8f2d6be112d0209aeb9e95'
                  '45da67aeea80', 16),
         'y': int('778082b77ddba6f56597cc74c3a612abf2ddbd85cc81430c99ab'
                  '843c1f630b9db0139965f563978164f9bf3a8397256be714625'
                  'cd41cd7fa0067d94ea66d7e073f7125af692ad01371d4a17f45'
                  '50590378f2b074030c20e36911598a1018772f61be3b24de4be'
                  '5a388ccc09e15a92819c31dec50de9fde105b49eaa097b9d13d'
                  '9219eeb33b628facfd1c78a7159c8430d0647c506e7e3de74763c'
                  'b351eada72c00bef3c9641881e6254870c1e6599f8ca2f1bbb74f'
                  '39a905e3a34e4544168e6e50c9e3305fd09cab6ed4aff6fda6e0d'
                  '5bf375c81ac9054406d9193b003c89272f1bd83d48250134b65c77'
                  'c2b6332d38d34d9016f0e8975536ad6c348a1faedb0', 16)},

        {'g': int('ce84b30ddf290a9f787a7c2f1ce92c1cbf4ef400e3cd7ce4978d'
                  'b2104d7394b493c18332c64cec906a71c3778bd93341165dee8'
                  'e6cd4ca6f13afff531191194ada55ecf01ff94d6cf7c4768b82'
                  'dd29cd131aaf202aefd40e564375285c01f3220af4d70b96f1'
                  '395420d778228f1461f5d0b8e47357e87b1fe3286223b553e3'
                  'fc9928f16ae3067ded6721bedf1d1a01bfd22b9ae85fce77820d88cdf'
                  '50a6bde20668ad77a707d1c60fcc5d51c9de488610d0285eb8ff721f'
                  'f141f93a9fb23c1d1f7654c07c46e58836d1652828f71057b8aff0b077'
                  '8ef2ca934ea9d0f37daddade2d823a4d8e362721082e279d003b575ee'
                  '59fd050d105dfd71cd63154efe431a0869178d9811f4f231dc5dcf3b'
                  '0ec0f2b0f9896c32ec6c7ee7d60aa97109e09224907328d4e6acd1011'
                  '7e45774406c4c947da8020649c3168f690e0bd6e91ac67074d1d436b'
                  '58ae374523deaf6c93c1e6920db4a080b744804bb073cecfe83fa939'
                  '8cf150afa286dc7eb7949750cf5001ce104e9187f7e16859afa8fd0d'
                  '775ae', 16),
         'p': int('f335666dd1339165af8b9a5e3835adfe15c158e4c3c7bd53132e7d5828'
                  'c352f593a9a787760ce34b789879941f2f01f02319f6ae0b756f1a842'
                  'ba54c85612ed632ee2d79ef17f06b77c641b7b080aff52a03fc2462e8'
                  '0abc64d223723c236deeb7d201078ec01ca1fbc1763139e25099a84ec'
                  '389159c409792080736bd7caa816b92edf23f2c351f90074aa5ea2651'
                  'b372f8b58a0a65554db2561d706a63685000ac576b7e4562e262a1428'
                  '5a9c6370b290e4eb7757527d80b6c0fd5df831d36f3d1d35f12ab0605'
                  '48de1605fd15f7c7aafed688b146a02c945156e284f5b71282045aba9'
                  '844d48b5df2e9e7a5887121eae7d7b01db7cdf6ff917cd8eb50c6bf1d'
                  '54f90cce1a491a9c74fea88f7e7230b047d16b5a6027881d6f154818f'
                  '06e513faf40c8814630e4e254f17a47bfe9cb519b98289935bf17673a'
                  'e4c8033504a20a898d0032ee402b72d5986322f3bdfb27400561f7476'
                  'cd715eaabb7338b854e51fc2fa026a5a579b6dcea1b1c0559c13d3c11'
                  '36f303f4b4d25ad5b692229957', 16),
         'q': int('d3eba6521240694015ef94412e08bf3cf8d635a455a398d6f210'
                  'f6169041653b', 16),
         'x': int('b2764c46113983777d3e7e97589f1303806d14ad9f2f1ef03309'
                  '7de954b17706', 16),
         'y': int('814824e435e1e6f38daa239aad6dad21033afce6a3ebd35c1359348a0f2'
                  '418871968c2babfc2baf47742148828f8612183178f126504da73566b6'
                  'bab33ba1f124c15aa461555c2451d86c94ee21c3e3fc24c55527e'
                  '01b1f03adcdd8ec5cb08082803a7b6a829c3e99eeb332a2cf5c035b0c'
                  'e0078d3d414d31fa47e9726be2989b8d06da2e6cd363f5a7d1515e3f4'
                  '925e0b32adeae3025cc5a996f6fd27494ea408763de48f3bb39f6a06'
                  '514b019899b312ec570851637b8865cff3a52bf5d54ad5a19e6e400'
                  'a2d33251055d0a440b50d53f4791391dc754ad02b9eab74c46b4903'
                  'f9d76f824339914db108057af7cde657d41766a99991ac8787694f'
                  '4185d6f91d7627048f827b405ec67bf2fe56141c4c581d8c317333'
                  '624e073e5879a82437cb0c7b435c0ce434e15965db1315d648959'
                  '91e6bbe7dac040c42052408bbc53423fd31098248a58f8a67da3a'
                  '39895cd0cc927515d044c1e3cb6a3259c3d0da354cce89ea3552c'
                  '59609db10ee989986527436af21d9485ddf25f90f7dff6d2bae', 16)},
        {'g': int('ce84b30ddf290a9f787a7c2f1ce92c1cbf4ef400e3cd7ce4978d'
                  'b2104d7394b493c18332c64cec906a71c3778bd93341165dee8'
                  'e6cd4ca6f13afff531191194ada55ecf01ff94d6cf7c4768b82'
                  'dd29cd131aaf202aefd40e564375285c01f3220af4d70b96f1'
                  '395420d778228f1461f5d0b8e47357e87b1fe3286223b553e3'
                  'fc9928f16ae3067ded6721bedf1d1a01bfd22b9ae85fce77820d88cdf'
                  '50a6bde20668ad77a707d1c60fcc5d51c9de488610d0285eb8ff721f'
                  'f141f93a9fb23c1d1f7654c07c46e58836d1652828f71057b8aff0b077'
                  '8ef2ca934ea9d0f37daddade2d823a4d8e362721082e279d003b575ee'
                  '59fd050d105dfd71cd63154efe431a0869178d9811f4f231dc5dcf3b'
                  '0ec0f2b0f9896c32ec6c7ee7d60aa97109e09224907328d4e6acd1011'
                  '7e45774406c4c947da8020649c3168f690e0bd6e91ac67074d1d436b'
                  '58ae374523deaf6c93c1e6920db4a080b744804bb073cecfe83fa939'
                  '8cf150afa286dc7eb7949750cf5001ce104e9187f7e16859afa8fd0d'
                  '775ae', 16),
         'p': int('f335666dd1339165af8b9a5e3835adfe15c158e4c3c7bd53132e7d5828'
                  'c352f593a9a787760ce34b789879941f2f01f02319f6ae0b756f1a842'
                  'ba54c85612ed632ee2d79ef17f06b77c641b7b080aff52a03fc2462e8'
                  '0abc64d223723c236deeb7d201078ec01ca1fbc1763139e25099a84ec'
                  '389159c409792080736bd7caa816b92edf23f2c351f90074aa5ea2651'
                  'b372f8b58a0a65554db2561d706a63685000ac576b7e4562e262a1428'
                  '5a9c6370b290e4eb7757527d80b6c0fd5df831d36f3d1d35f12ab0605'
                  '48de1605fd15f7c7aafed688b146a02c945156e284f5b71282045aba9'
                  '844d48b5df2e9e7a5887121eae7d7b01db7cdf6ff917cd8eb50c6bf1d'
                  '54f90cce1a491a9c74fea88f7e7230b047d16b5a6027881d6f154818f'
                  '06e513faf40c8814630e4e254f17a47bfe9cb519b98289935bf17673a'
                  'e4c8033504a20a898d0032ee402b72d5986322f3bdfb27400561f7476'
                  'cd715eaabb7338b854e51fc2fa026a5a579b6dcea1b1c0559c13d3c11'
                  '36f303f4b4d25ad5b692229957', 16),
         'q': int('d3eba6521240694015ef94412e08bf3cf8d635a455a398d6f210'
                  'f6169041653b', 16),
         'x': int('52e3e040efb30e1befd909a0bdbcfd140d005b1bff094af97186'
                  '080262f1904d', 16),
         'y': int('a5ae6e8f9b7a68ab0516dad4d7b7d002126f811d5a52e3d35c6d'
                  '387fcb43fd19bf7792362f9c98f8348aa058bb62376685f3d0c3'
                  '66c520d697fcd8416947151d4bbb6f32b53528a016479e99d2cd'
                  '48d1fc679027c15f0042f207984efe05c1796bca8eba678dfdd0'
                  '0b80418e3ea840557e73b09e003882f9a68edba3431d351d1ca0'
                  '7a8150b018fdbdf6c2f1ab475792a3ccaa6594472a45f8dc777b'
                  '60bf67de3e0f65c20d11b7d59faedf83fbce52617f500d9e5149'
                  '47c455274c6e900464767fb56599b81344cf6d12c25cb2b7d038'
                  'd7b166b6cf30534811c15d0e8ab880a2ac06786ae2ddde61329a'
                  '78d526f65245380ce877e979c5b50de66c9c30d66382c8f25465'
                  '3d25a1eb1d3a4897d7623399b473ce712a2184cf2da1861706c4'
                  '1466806aefe41b497db82aca6c31c8f4aa68c17d1d9e380b5799'
                  '8917655783ec96e5234a131f7299398d36f1f5f84297a55ff292'
                  'f1f060958c358fed346db2de45127ca728a9417b2c54203e33e5'
                  '3b9a061d924395b09afab8daf3e8dd7eedcec3ac', 16)}
    ]

    assert expected == load_fips_dsa_key_pair_vectors(vector_data)


def test_load_fips_dsa_sig_ver_vectors():
    vector_data = textwrap.dedent("""
    # CAVS 11.0
    # "SigVer" information
    # Mod sizes selected: SHA-1 L=1024, N=160,SHA-384 L=2048, N=256
    # Generated on Fri Apr 01 08:37:15 2011

    [mod = L=1024, N=160, SHA-1]

    P = dc5bf3a88b2d99e4c95cdd7a0501cc38630d425cf5c390af3429cff1f35147b795cae\
a923f0d3577158f8a0c89dabd1962c2c453306b5d70cacfb01430aceb54e5a5fa6f93\
40d3bd2da612fceeb76b0ec1ebfae635a56ab141b108e00dc76eefe2edd0c514c21c4\
57457c39065dba9d0ecb7569c247172d8438ad2827b60435b
    Q = e956602b83d195dbe945b3ac702fc61f81571f1d
    G = d7eb9ca20a3c7a079606bafc4c9261ccaba303a5dc9fe9953f197dfe548c234895baa\
77f441ee6a2d97b909cbbd26ff7b869d24cae51b5c6edb127a4b5d75cd8b46608bfa1\
48249dffdb59807c5d7dde3fe3080ca3a2d28312142becb1fa8e24003e21c72871081\
74b95d5bc711e1c8d9b1076784f5dc37a964a5e51390da713

    Msg = 0fe1bfee500bdb76026099b1d37553f6bdfe48c82094ef98cb309dd777330bedfaa\
2f94c823ef74ef4074b50d8706041ac0e371c7c22dcf70263b8d60e17a86c7c379c\
fda8f22469e0df9d49d59439fc99891873628fff25dda5fac5ac794e948babdde96\
8143ba05f1128f34fdad5875edc4cd71c6c24ba2060ffbd439ce2b3
    X = 1d93010c29ecfc432188942f46f19f44f0e1bb5d
    Y = 6240ea0647117c38fe705106d56db578f3e10130928452d4f3587881b8a2bc6873a8b\
efc3237f20914e2a91c7f07a928ee22adeed23d74ab7f82ea11f70497e578f7a9b4cb\
d6f10226222b0b4da2ea1e49813d6bb9882fbf675c0846bb80cc891857b89b0ef1beb\
6cce3378a9aab5d66ad4cb9277cf447dfe1e64434749432fb
    R = b5af307867fb8b54390013cc67020ddf1f2c0b81
    S = 620d3b22ab5031440c3e35eab6f481298f9e9f08
    Result = P

    Msg = 97d50898025d2f9ba633866e968ca75e969d394edba6517204cb3dd537c2ba38778\
a2dc9dbc685a915e5676fcd43bc3726bc59ce3d7a9fae35565082a069c139fa37c9\
0d922b126933db3fa6c5ef6b1edf00d174a51887bb76909c6a94fe994ecc7b7fc8f\
26113b17f30f9d01693df99a125b4f17e184331c6b6e8ca00f54f3a
    X = 350e13534692a7e0c4b7d58836046c436fbb2322
    Y = 69974de550fe6bd3099150faea1623ad3fb6d9bf23a07215093f319725ad0877accff\
d291b6da18eb0cbe51676ceb0977504eb97c27c0b191883f72fb2710a9fbd8bcf13be\
0bf854410b32f42b33ec89d3cc1cf892bcd536c4195ca9ada302ad600c3408739935d\
77dc247529ca47f844cc86f5016a2fe962c6e20ca7c4d4e8f
    R = b5d05faa7005764e8dae0327c5bf1972ff7681b9
    S = 18ea15bd9f00475b25204cbc23f8c23e01588015
    Result = F (3 - R changed )

    [mod = L=2048, N=224, SHA-1]

    # unsupported so we ignore this

    Msg = f9d01693df99a125b4f17e184331c6b6e8ca00f54f3a
    X = e0c4b7d58836046c436fbb2322
    Y = fb6d9bf23a07215093f319725ad0877accff
    R = 5764e8dae0327c5bf1972ff7681b9
    S = 475b25204cbc23f8c23e01588015
    Result = F (3 - R changed )

    [mod = L=2048, N=256, SHA-384]

    P = e7c1c86125db9ef417da1ced7ea0861bdad629216a3f3c745df42a46b989e59f4d984\
25ee3c932fa3c2b6f637bdb6545bec526faa037e11f5578a4363b9fca5eba60d6a9cb\
aa2befd04141d989c7356285132c2eaf74f2d868521cdc0a17ae9a2546ef863027d3f\
8cc7949631fd0e2971417a912c8b8c5c989730db6ea6e8baee0e667850429038093c8\
51ccb6fb173bb081e0efe0bd7450e0946888f89f75e443ab93ef2da293a01622cf43c\
6dd79625d41ba8f9ef7e3086ab39134283d8e96c89249488120fd061e4a87d34af410\
69c0b4fd3934c31b589cbe85b68b912718d5dab859fda7082511fad1d152044905005\
546e19b14aa96585a55269bf2b831
    Q = 8e056ec9d4b7acb580087a6ed9ba3478711bb025d5b8d9c731ef9b38bd43db2f
    G = dc2bfb9776786ad310c8b0cdcbba3062402613c67e6959a8d8d1b05aab636528b7b1f\
e9cd33765f853d6dbe13d09f2681f8c7b1ed7886aaed70c7bd76dbe858ffb8bd86235\
ddf759244678f428c6519af593dc94eeadbd9852ba2b3d61664e8d58c29d2039af3c3\
d6d16f90988f6a8c824569f3d48050e30896a9e17cd0232ef01ab8790008f6973b84c\
763a72f4ae8b485abfb7e8efeb86808fa2b281d3e5d65d28f5992a34c077c5aa8026c\
b2fbc34a45f7e9bd216b10e6f12ecb172e9a6eb8f2e91316905b6add1fd22e83bc2f0\
89f1d5e6a6e6707c18ff55ddcb7954e8bceaf0efc4e8314910c03b0e51175f344faaf\
ee476a373ac95743cec712b72cf2e

    Msg = 6cd6ccfd66bcd832189c5f0c77994210e3bf2c43416f0fe77c4e92f31c5369538dc\
2c003f146c5ac79df43194ccf3c44d470d9f1083bd15b99b5bcf88c32d8a9021f09\
ea2288d7b3bf345a12aef3949c1e121b9fb371a67c2d1377364206ac839dd784835\
61426bda0303f285aa12e9c45d3cdfc6beae3549703b187deeb3296
    X = 56c897b5938ad5b3d437d7e4826da586a6b3be15e893fa1aaa946f20a028b6b3
    Y = 38ad44489e1a5778b9689f4dcf40e2acf23840fb954e987d6e8cb629106328ac64e1f\
3c3eba48b21176ad4afe3b733bead382ee1597e1b83e4b43424f2daaba04e5bd79e14\
36693ac2bddb79a298f026e57e200a252efd1e848a4a2e90be6e78f5242b468b9c0c6\
d2615047a5a40b9ae7e57a519114db55bf3bed65e580f894b094630ca9c217f6accd0\
91e72d2f22da620044ff372d7273f9445017fad492959e59600b7494dbe766a03e401\
25d4e6747c76f68a5b0cdc0e7d7cee12d08c6fb7d0fb049e420a33405075ed4463296\
345ca695fb7feab7c1b5333ae519fcd4bb6a043f4555378969114743d4face96cad31\
c0e0089da4e3f61b6d7dabc088ab7
    R = 3b85b17be240ed658beb3652c9d93e8e9eea160d35ee2459614305802963374e
    S = 726800a5174a53b56dce86064109c0273cd11fcfa3c92c5cd6aa910260c0e3c7
    Result = F (1 - Message changed)

    Msg = 3ad6b0884f358dea09c31a9abc40c45a6000611fc2b907b30eac00413fd2819de70\
15488a411609d46c499b8f7afa1b78b352ac7f8535bd805b8ff2a5eae557098c668\
f7ccd73af886d6823a6d456c29931ee864ed46d767382785728c2a83fcff5271007\
d2a67d06fa205fd7b9d1a42ea5d6dc76e5e18a9eb148cd1e8b262ae
    X = 2faf566a9f057960f1b50c69508f483d9966d6e35743591f3a677a9dc40e1555
    Y = 926425d617babe87c442b03903e32ba5bbf0cd9d602b59c4df791a4d64a6d4333ca0c\
0d370552539197d327dcd1bbf8c454f24b03fc7805f862db34c7b066ddfddbb11dbd0\
10b27123062d028fe041cb56a2e77488348ae0ab6705d87aac4d4e9e6600e9e706326\
d9979982cffa839beb9eacc3963bcca455a507e80c1c37ad4e765b2c9c0477a075e9b\
c584feacdf3a35a9391d4711f14e197c54022282bfed9a191213d64127f17a9c5affe\
c26e0c71f15d3a5b16098fec118c45bf8bb2f3b1560df0949254c1c0aeb0a16d5a95a\
40fab8521fbe8ea77c51169b587cc3360e5733e6a23b9fded8c40724ea1f9e93614b3\
a6c9b4f8dbbe915b794497227ba62
    R = 343ea0a9e66277380f604d5880fca686bffab69ca97bfba015a102a7e23dce0e
    S = 6258488c770e0f5ad7b9da8bade5023fc0d17c6ec517bd08d53e6dc01ac5c2b3
    Result = P
    """).splitlines()

    expected = [
        {
            'p': int('dc5bf3a88b2d99e4c95cdd7a0501cc38630d425cf5c390af3429cff1'
                     'f35147b795caea923f0d3577158f8a0c89dabd1962c2c453306b5d70'
                     'cacfb01430aceb54e5a5fa6f9340d3bd2da612fceeb76b0ec1ebfae6'
                     '35a56ab141b108e00dc76eefe2edd0c514c21c457457c39065dba9d0'
                     'ecb7569c247172d8438ad2827b60435b', 16),
            'q': int('e956602b83d195dbe945b3ac702fc61f81571f1d', 16),
            'g': int('d7eb9ca20a3c7a079606bafc4c9261ccaba303a5dc9fe9953f197dfe'
                     '548c234895baa77f441ee6a2d97b909cbbd26ff7b869d24cae51b5c6'
                     'edb127a4b5d75cd8b46608bfa148249dffdb59807c5d7dde3fe3080c'
                     'a3a2d28312142becb1fa8e24003e21c7287108174b95d5bc711e1c8d'
                     '9b1076784f5dc37a964a5e51390da713', 16),
            'digest_algorithm': 'SHA-1',
            'msg': binascii.unhexlify(
                b'0fe1bfee500bdb76026099b1d37553f6bdfe48c82094ef98cb309dd77733'
                b'0bedfaa2f94c823ef74ef4074b50d8706041ac0e371c7c22dcf70263b8d6'
                b'0e17a86c7c379cfda8f22469e0df9d49d59439fc99891873628fff25dda5'
                b'fac5ac794e948babdde968143ba05f1128f34fdad5875edc4cd71c6c24ba'
                b'2060ffbd439ce2b3'),
            'x': int('1d93010c29ecfc432188942f46f19f44f0e1bb5d', 16),
            'y': int('6240ea0647117c38fe705106d56db578f3e10130928452d4f3587881'
                     'b8a2bc6873a8befc3237f20914e2a91c7f07a928ee22adeed23d74ab'
                     '7f82ea11f70497e578f7a9b4cbd6f10226222b0b4da2ea1e49813d6b'
                     'b9882fbf675c0846bb80cc891857b89b0ef1beb6cce3378a9aab5d66'
                     'ad4cb9277cf447dfe1e64434749432fb', 16),
            'r': int('b5af307867fb8b54390013cc67020ddf1f2c0b81', 16),
            's': int('620d3b22ab5031440c3e35eab6f481298f9e9f08', 16),
            'result': 'P'},
        {
            'p': int('dc5bf3a88b2d99e4c95cdd7a0501cc38630d425cf5c390af3429cff1'
                     'f35147b795caea923f0d3577158f8a0c89dabd1962c2c453306b5d70'
                     'cacfb01430aceb54e5a5fa6f9340d3bd2da612fceeb76b0ec1ebfae6'
                     '35a56ab141b108e00dc76eefe2edd0c514c21c457457c39065dba9d0'
                     'ecb7569c247172d8438ad2827b60435b', 16),
            'q': int('e956602b83d195dbe945b3ac702fc61f81571f1d', 16),
            'g': int('d7eb9ca20a3c7a079606bafc4c9261ccaba303a5dc9fe9953f197dfe'
                     '548c234895baa77f441ee6a2d97b909cbbd26ff7b869d24cae51b5c6'
                     'edb127a4b5d75cd8b46608bfa148249dffdb59807c5d7dde3fe3080c'
                     'a3a2d28312142becb1fa8e24003e21c7287108174b95d5bc711e1c8d'
                     '9b1076784f5dc37a964a5e51390da713', 16),
            'digest_algorithm': 'SHA-1',
            'msg': binascii.unhexlify(
                b'97d50898025d2f9ba633866e968ca75e969d394edba6517204cb3dd537c2'
                b'ba38778a2dc9dbc685a915e5676fcd43bc3726bc59ce3d7a9fae35565082'
                b'a069c139fa37c90d922b126933db3fa6c5ef6b1edf00d174a51887bb7690'
                b'9c6a94fe994ecc7b7fc8f26113b17f30f9d01693df99a125b4f17e184331'
                b'c6b6e8ca00f54f3a'),
            'x': int('350e13534692a7e0c4b7d58836046c436fbb2322', 16),
            'y': int('69974de550fe6bd3099150faea1623ad3fb6d9bf23a07215093f3197'
                     '25ad0877accffd291b6da18eb0cbe51676ceb0977504eb97c27c0b19'
                     '1883f72fb2710a9fbd8bcf13be0bf854410b32f42b33ec89d3cc1cf8'
                     '92bcd536c4195ca9ada302ad600c3408739935d77dc247529ca47f84'
                     '4cc86f5016a2fe962c6e20ca7c4d4e8f', 16),
            'r': int('b5d05faa7005764e8dae0327c5bf1972ff7681b9', 16),
            's': int('18ea15bd9f00475b25204cbc23f8c23e01588015', 16),
            'result': 'F'},
        {
            'p': int('e7c1c86125db9ef417da1ced7ea0861bdad629216a3f3c745df42a4'
                     '6b989e59f4d98425ee3c932fa3c2b6f637bdb6545bec526faa037e1'
                     '1f5578a4363b9fca5eba60d6a9cbaa2befd04141d989c7356285132'
                     'c2eaf74f2d868521cdc0a17ae9a2546ef863027d3f8cc7949631fd0'
                     'e2971417a912c8b8c5c989730db6ea6e8baee0e667850429038093c'
                     '851ccb6fb173bb081e0efe0bd7450e0946888f89f75e443ab93ef2d'
                     'a293a01622cf43c6dd79625d41ba8f9ef7e3086ab39134283d8e96c'
                     '89249488120fd061e4a87d34af41069c0b4fd3934c31b589cbe85b6'
                     '8b912718d5dab859fda7082511fad1d152044905005546e19b14aa9'
                     '6585a55269bf2b831', 16),
            'q': int('8e056ec9d4b7acb580087a6ed9ba3478711bb025d5b8d9c731ef9b3'
                     '8bd43db2f', 16),
            'g': int('dc2bfb9776786ad310c8b0cdcbba3062402613c67e6959a8d8d1b05'
                     'aab636528b7b1fe9cd33765f853d6dbe13d09f2681f8c7b1ed7886a'
                     'aed70c7bd76dbe858ffb8bd86235ddf759244678f428c6519af593d'
                     'c94eeadbd9852ba2b3d61664e8d58c29d2039af3c3d6d16f90988f6'
                     'a8c824569f3d48050e30896a9e17cd0232ef01ab8790008f6973b84'
                     'c763a72f4ae8b485abfb7e8efeb86808fa2b281d3e5d65d28f5992a'
                     '34c077c5aa8026cb2fbc34a45f7e9bd216b10e6f12ecb172e9a6eb8'
                     'f2e91316905b6add1fd22e83bc2f089f1d5e6a6e6707c18ff55ddcb'
                     '7954e8bceaf0efc4e8314910c03b0e51175f344faafee476a373ac9'
                     '5743cec712b72cf2e', 16),
            'digest_algorithm': 'SHA-384',
            'msg': binascii.unhexlify(
                b'6cd6ccfd66bcd832189c5f0c77994210e3bf2c43416f0fe77c4e92f31c5'
                b'369538dc2c003f146c5ac79df43194ccf3c44d470d9f1083bd15b99b5bc'
                b'f88c32d8a9021f09ea2288d7b3bf345a12aef3949c1e121b9fb371a67c2'
                b'd1377364206ac839dd78483561426bda0303f285aa12e9c45d3cdfc6bea'
                b'e3549703b187deeb3296'),
            'x': int('56c897b5938ad5b3d437d7e4826da586a6b3be15e893fa1aaa946f2'
                     '0a028b6b3', 16),
            'y': int('38ad44489e1a5778b9689f4dcf40e2acf23840fb954e987d6e8cb62'
                     '9106328ac64e1f3c3eba48b21176ad4afe3b733bead382ee1597e1b'
                     '83e4b43424f2daaba04e5bd79e1436693ac2bddb79a298f026e57e2'
                     '00a252efd1e848a4a2e90be6e78f5242b468b9c0c6d2615047a5a40'
                     'b9ae7e57a519114db55bf3bed65e580f894b094630ca9c217f6accd'
                     '091e72d2f22da620044ff372d7273f9445017fad492959e59600b74'
                     '94dbe766a03e40125d4e6747c76f68a5b0cdc0e7d7cee12d08c6fb7'
                     'd0fb049e420a33405075ed4463296345ca695fb7feab7c1b5333ae5'
                     '19fcd4bb6a043f4555378969114743d4face96cad31c0e0089da4e3'
                     'f61b6d7dabc088ab7', 16),
            'r': int('3b85b17be240ed658beb3652c9d93e8e9eea160d35ee24596143058'
                     '02963374e', 16),
            's': int('726800a5174a53b56dce86064109c0273cd11fcfa3c92c5cd6aa910'
                     '260c0e3c7', 16),
            'result': 'F'},
        {
            'p': int('e7c1c86125db9ef417da1ced7ea0861bdad629216a3f3c745df42a4'
                     '6b989e59f4d98425ee3c932fa3c2b6f637bdb6545bec526faa037e1'
                     '1f5578a4363b9fca5eba60d6a9cbaa2befd04141d989c7356285132'
                     'c2eaf74f2d868521cdc0a17ae9a2546ef863027d3f8cc7949631fd0'
                     'e2971417a912c8b8c5c989730db6ea6e8baee0e667850429038093c'
                     '851ccb6fb173bb081e0efe0bd7450e0946888f89f75e443ab93ef2d'
                     'a293a01622cf43c6dd79625d41ba8f9ef7e3086ab39134283d8e96c'
                     '89249488120fd061e4a87d34af41069c0b4fd3934c31b589cbe85b6'
                     '8b912718d5dab859fda7082511fad1d152044905005546e19b14aa9'
                     '6585a55269bf2b831', 16),
            'q': int('8e056ec9d4b7acb580087a6ed9ba3478711bb025d5b8d9c731ef9b3'
                     '8bd43db2f', 16),
            'g': int('dc2bfb9776786ad310c8b0cdcbba3062402613c67e6959a8d8d1b05'
                     'aab636528b7b1fe9cd33765f853d6dbe13d09f2681f8c7b1ed7886a'
                     'aed70c7bd76dbe858ffb8bd86235ddf759244678f428c6519af593d'
                     'c94eeadbd9852ba2b3d61664e8d58c29d2039af3c3d6d16f90988f6'
                     'a8c824569f3d48050e30896a9e17cd0232ef01ab8790008f6973b84'
                     'c763a72f4ae8b485abfb7e8efeb86808fa2b281d3e5d65d28f5992a'
                     '34c077c5aa8026cb2fbc34a45f7e9bd216b10e6f12ecb172e9a6eb8'
                     'f2e91316905b6add1fd22e83bc2f089f1d5e6a6e6707c18ff55ddcb'
                     '7954e8bceaf0efc4e8314910c03b0e51175f344faafee476a373ac9'
                     '5743cec712b72cf2e', 16),
            'digest_algorithm': 'SHA-384',
            'msg': binascii.unhexlify(
                b'3ad6b0884f358dea09c31a9abc40c45a6000611fc2b907b30eac00413fd'
                b'2819de7015488a411609d46c499b8f7afa1b78b352ac7f8535bd805b8ff'
                b'2a5eae557098c668f7ccd73af886d6823a6d456c29931ee864ed46d7673'
                b'82785728c2a83fcff5271007d2a67d06fa205fd7b9d1a42ea5d6dc76e5e'
                b'18a9eb148cd1e8b262ae'),
            'x': int('2faf566a9f057960f1b50c69508f483d9966d6e35743591f3a677a9'
                     'dc40e1555', 16),
            'y': int('926425d617babe87c442b03903e32ba5bbf0cd9d602b59c4df791a4d'
                     '64a6d4333ca0c0d370552539197d327dcd1bbf8c454f24b03fc7805f'
                     '862db34c7b066ddfddbb11dbd010b27123062d028fe041cb56a2e774'
                     '88348ae0ab6705d87aac4d4e9e6600e9e706326d9979982cffa839be'
                     'b9eacc3963bcca455a507e80c1c37ad4e765b2c9c0477a075e9bc584'
                     'feacdf3a35a9391d4711f14e197c54022282bfed9a191213d64127f1'
                     '7a9c5affec26e0c71f15d3a5b16098fec118c45bf8bb2f3b1560df09'
                     '49254c1c0aeb0a16d5a95a40fab8521fbe8ea77c51169b587cc3360e'
                     '5733e6a23b9fded8c40724ea1f9e93614b3a6c9b4f8dbbe915b79449'
                     '7227ba62', 16),
            'r': int('343ea0a9e66277380f604d5880fca686bffab69ca97bfba015a102a'
                     '7e23dce0e', 16),
            's': int('6258488c770e0f5ad7b9da8bade5023fc0d17c6ec517bd08d53e6dc'
                     '01ac5c2b3', 16),
            'result': 'P'}
    ]

    assert expected == load_fips_dsa_sig_vectors(vector_data)


def test_load_fips_dsa_sig_gen_vectors():
    vector_data = textwrap.dedent("""
    # CAVS 11.2
    # "SigGen" information for "dsa2_values"
    # Mod sizes selected: SHA-1 L=1024, N=160, SHA-256 L=2048, N=256

    [mod = L=1024, N=160, SHA-1]

    P = a8f9cd201e5e35d892f85f80e4db2599a5676a3b1d4f190330ed3256b26d0e80a0e49\
a8fffaaad2a24f472d2573241d4d6d6c7480c80b4c67bb4479c15ada7ea8424d2502fa01472e7\
60241713dab025ae1b02e1703a1435f62ddf4ee4c1b664066eb22f2e3bf28bb70a2a76e4fd5eb\
e2d1229681b5b06439ac9c7e9d8bde283
    Q = f85f0f83ac4df7ea0cdf8f469bfeeaea14156495
    G = 2b3152ff6c62f14622b8f48e59f8af46883b38e79b8c74deeae9df131f8b856e3ad6c\
8455dab87cc0da8ac973417ce4f7878557d6cdf40b35b4a0ca3eb310c6a95d68ce284ad4e25ea\
28591611ee08b8444bd64b25f3f7c572410ddfb39cc728b9c936f85f419129869929cdb909a6a\
3a99bbe089216368171bd0ba81de4fe33

    Msg = 3b46736d559bd4e0c2c1b2553a33ad3c6cf23cac998d3d0c0e8fa4b19bca06f2f38\
6db2dcff9dca4f40ad8f561ffc308b46c5f31a7735b5fa7e0f9e6cb512e63d7eea05538d66a75\
cd0d4234b5ccf6c1715ccaaf9cdc0a2228135f716ee9bdee7fc13ec27a03a6d11c5c5b3685f51\
900b1337153bc6c4e8f52920c33fa37f4e7
    Y = 313fd9ebca91574e1c2eebe1517c57e0c21b0209872140c5328761bbb2450b33f1b18\
b409ce9ab7c4cd8fda3391e8e34868357c199e16a6b2eba06d6749def791d79e95d3a4d09b24c\
392ad89dbf100995ae19c01062056bb14bce005e8731efde175f95b975089bdcdaea562b32786\
d96f5a31aedf75364008ad4fffebb970b
    R = 50ed0e810e3f1c7cb6ac62332058448bd8b284c0
    S = c6aded17216b46b7e4b6f2a97c1ad7cc3da83fde

    Msg = d2bcb53b044b3e2e4b61ba2f91c0995fb83a6a97525e66441a3b489d9594238bc74\
0bdeea0f718a769c977e2de003877b5d7dc25b182ae533db33e78f2c3ff0645f2137abc137d4e\
7d93ccf24f60b18a820bc07c7b4b5fe08b4f9e7d21b256c18f3b9d49acc4f93e2ce6f3754c780\
7757d2e1176042612cb32fc3f4f70700e25
    Y = 29bdd759aaa62d4bf16b4861c81cf42eac2e1637b9ecba512bdbc13ac12a80ae8de25\
26b899ae5e4a231aef884197c944c732693a634d7659abc6975a773f8d3cd5a361fe2492386a3\
c09aaef12e4a7e73ad7dfc3637f7b093f2c40d6223a195c136adf2ea3fbf8704a675aa7817aa7\
ec7f9adfb2854d4e05c3ce7f76560313b
    R = a26c00b5750a2d27fe7435b93476b35438b4d8ab
    S = 61c9bfcb2938755afa7dad1d1e07c6288617bf70

    [mod = L=2048, N=256, SHA-256]

    P = a8adb6c0b4cf9588012e5deff1a871d383e0e2a85b5e8e03d814fe13a059705e66323\
0a377bf7323a8fa117100200bfd5adf857393b0bbd67906c081e585410e38480ead51684dac3a\
38f7b64c9eb109f19739a4517cd7d5d6291e8af20a3fbf17336c7bf80ee718ee087e322ee4104\
7dabefbcc34d10b66b644ddb3160a28c0639563d71993a26543eadb7718f317bf5d9577a61565\
61b082a10029cd44012b18de6844509fe058ba87980792285f2750969fe89c2cd6498db354563\
8d5379d125dccf64e06c1af33a6190841d223da1513333a7c9d78462abaab31b9f96d5f34445c\
eb6309f2f6d2c8dde06441e87980d303ef9a1ff007e8be2f0be06cc15f
    Q = e71f8567447f42e75f5ef85ca20fe557ab0343d37ed09edc3f6e68604d6b9dfb
    G = 5ba24de9607b8998e66ce6c4f812a314c6935842f7ab54cd82b19fa104abfb5d84579\
a623b2574b37d22ccae9b3e415e48f5c0f9bcbdff8071d63b9bb956e547af3a8df99e5d306197\
9652ff96b765cb3ee493643544c75dbe5bb39834531952a0fb4b0378b3fcbb4c8b5800a533039\
2a2a04e700bb6ed7e0b85795ea38b1b962741b3f33b9dde2f4ec1354f09e2eb78e95f037a5804\
b6171659f88715ce1a9b0cc90c27f35ef2f10ff0c7c7a2bb0154d9b8ebe76a3d764aa879af372\
f4240de8347937e5a90cec9f41ff2f26b8da9a94a225d1a913717d73f10397d2183f1ba3b7b45\
a68f1ff1893caf69a827802f7b6a48d51da6fbefb64fd9a6c5b75c4561

    Msg = 4e3a28bcf90d1d2e75f075d9fbe55b36c5529b17bc3a9ccaba6935c9e20548255b3\
dfae0f91db030c12f2c344b3a29c4151c5b209f5e319fdf1c23b190f64f1fe5b330cb7c8fa952\
f9d90f13aff1cb11d63181da9efc6f7e15bfed4862d1a62c7dcf3ba8bf1ff304b102b1ec3f149\
7dddf09712cf323f5610a9d10c3d9132659
    Y = 5a55dceddd1134ee5f11ed85deb4d634a3643f5f36dc3a70689256469a0b651ad2288\
0f14ab85719434f9c0e407e60ea420e2a0cd29422c4899c416359dbb1e592456f2b3cce233259\
c117542fd05f31ea25b015d9121c890b90e0bad033be1368d229985aac7226d1c8c2eab325ef3\
b2cd59d3b9f7de7dbc94af1a9339eb430ca36c26c46ecfa6c5481711496f624e188ad7540ef5d\
f26f8efacb820bd17a1f618acb50c9bc197d4cb7ccac45d824a3bf795c234b556b06aeb929173\
453252084003f69fe98045fe74002ba658f93475622f76791d9b2623d1b5fff2cc16844746efd\
2d30a6a8134bfc4c8cc80a46107901fb973c28fc553130f3286c1489da
    R = 633055e055f237c38999d81c397848c38cce80a55b649d9e7905c298e2a51447
    S = 2bbf68317660ec1e4b154915027b0bc00ee19cfc0bf75d01930504f2ce10a8b0

    Msg = a733b3f588d5ac9b9d4fe2f804df8c256403a9f8eef6f191fc48e1267fb5b4d546b\
a11e77b667844e489bf0d5f72990aeb061d01ccd7949a23def74a803b7d92d51abfadeb4885ff\
d8ffd58ab87548a15c087a39b8993b2fa64c9d31a594eeb7512da16955834336a234435c5a9d0\
dd9b15a94e116154dea63fdc8dd7a512181
    Y = 356ed47537fbf02cb30a8cee0537f300dff1d0c467399ce70b87a8758d5ec9dd25624\
6fccaeb9dfe109f2a984f2ddaa87aad54ce0d31f907e504521baf4207d7073b0a4a9fc67d8ddd\
a99f87aed6e0367cec27f9c608af743bf1ee6e11d55a182d43b024ace534029b866f6422828bb\
81a39aae9601ee81c7f81dd358e69f4e2edfa4654d8a65bc64311dc86aac4abc1fc7a3f651596\
61a0d8e288eb8d665cb0adf5ac3d6ba8e9453facf7542393ae24fd50451d3828086558f7ec528\
e284935a53f67a1aa8e25d8ad5c4ad55d83aef883a4d9eeb6297e6a53f65049ba9e2c6b7953a7\
60bc1dc46f78ceaaa2c02f5375dd82e708744aa40b15799eb81d7e5b1a
    R = bcd490568c0a89ba311bef88ea4f4b03d273e793722722327095a378dd6f3522
    S = 74498fc43091fcdd2d1ef0775f8286945a01cd72b805256b0451f9cbd943cf82
    """).splitlines()

    expected = [
        {
            'p': int('a8f9cd201e5e35d892f85f80e4db2599a5676a3b1d4f190330ed325'
                     '6b26d0e80a0e49a8fffaaad2a24f472d2573241d4d6d6c7480c80b4'
                     'c67bb4479c15ada7ea8424d2502fa01472e760241713dab025ae1b0'
                     '2e1703a1435f62ddf4ee4c1b664066eb22f2e3bf28bb70a2a76e4fd'
                     '5ebe2d1229681b5b06439ac9c7e9d8bde283', 16),
            'q': int('f85f0f83ac4df7ea0cdf8f469bfeeaea14156495', 16),
            'g': int('2b3152ff6c62f14622b8f48e59f8af46883b38e79b8c74deeae9df1'
                     '31f8b856e3ad6c8455dab87cc0da8ac973417ce4f7878557d6cdf40'
                     'b35b4a0ca3eb310c6a95d68ce284ad4e25ea28591611ee08b8444bd'
                     '64b25f3f7c572410ddfb39cc728b9c936f85f419129869929cdb909'
                     'a6a3a99bbe089216368171bd0ba81de4fe33', 16),
            'digest_algorithm': 'SHA-1',
            'msg': binascii.unhexlify(
                b'3b46736d559bd4e0c2c1b2553a33ad3c6cf23cac998d3d0c0e8fa4b19bc'
                b'a06f2f386db2dcff9dca4f40ad8f561ffc308b46c5f31a7735b5fa7e0f9'
                b'e6cb512e63d7eea05538d66a75cd0d4234b5ccf6c1715ccaaf9cdc0a222'
                b'8135f716ee9bdee7fc13ec27a03a6d11c5c5b3685f51900b1337153bc6c'
                b'4e8f52920c33fa37f4e7'),
            'y': int('313fd9ebca91574e1c2eebe1517c57e0c21b0209872140c5328761b'
                     'bb2450b33f1b18b409ce9ab7c4cd8fda3391e8e34868357c199e16a'
                     '6b2eba06d6749def791d79e95d3a4d09b24c392ad89dbf100995ae1'
                     '9c01062056bb14bce005e8731efde175f95b975089bdcdaea562b32'
                     '786d96f5a31aedf75364008ad4fffebb970b', 16),
            'r': int('50ed0e810e3f1c7cb6ac62332058448bd8b284c0', 16),
            's': int('c6aded17216b46b7e4b6f2a97c1ad7cc3da83fde', 16)},
        {
            'p': int('a8f9cd201e5e35d892f85f80e4db2599a5676a3b1d4f190330ed325'
                     '6b26d0e80a0e49a8fffaaad2a24f472d2573241d4d6d6c7480c80b4'
                     'c67bb4479c15ada7ea8424d2502fa01472e760241713dab025ae1b0'
                     '2e1703a1435f62ddf4ee4c1b664066eb22f2e3bf28bb70a2a76e4fd'
                     '5ebe2d1229681b5b06439ac9c7e9d8bde283', 16),
            'q': int('f85f0f83ac4df7ea0cdf8f469bfeeaea14156495', 16),
            'g': int('2b3152ff6c62f14622b8f48e59f8af46883b38e79b8c74deeae9df1'
                     '31f8b856e3ad6c8455dab87cc0da8ac973417ce4f7878557d6cdf40'
                     'b35b4a0ca3eb310c6a95d68ce284ad4e25ea28591611ee08b8444bd'
                     '64b25f3f7c572410ddfb39cc728b9c936f85f419129869929cdb909'
                     'a6a3a99bbe089216368171bd0ba81de4fe33', 16),
            'digest_algorithm': 'SHA-1',
            'msg': binascii.unhexlify(
                b'd2bcb53b044b3e2e4b61ba2f91c0995fb83a6a97525e66441a3b489d959'
                b'4238bc740bdeea0f718a769c977e2de003877b5d7dc25b182ae533db33e'
                b'78f2c3ff0645f2137abc137d4e7d93ccf24f60b18a820bc07c7b4b5fe08'
                b'b4f9e7d21b256c18f3b9d49acc4f93e2ce6f3754c7807757d2e11760426'
                b'12cb32fc3f4f70700e25'),
            'y': int('29bdd759aaa62d4bf16b4861c81cf42eac2e1637b9ecba512bdbc13'
                     'ac12a80ae8de2526b899ae5e4a231aef884197c944c732693a634d7'
                     '659abc6975a773f8d3cd5a361fe2492386a3c09aaef12e4a7e73ad7'
                     'dfc3637f7b093f2c40d6223a195c136adf2ea3fbf8704a675aa7817'
                     'aa7ec7f9adfb2854d4e05c3ce7f76560313b', 16),
            'r': int('a26c00b5750a2d27fe7435b93476b35438b4d8ab', 16),
            's': int('61c9bfcb2938755afa7dad1d1e07c6288617bf70', 16)},
        {
            'p': int('a8adb6c0b4cf9588012e5deff1a871d383e0e2a85b5e8e03d814fe1'
                     '3a059705e663230a377bf7323a8fa117100200bfd5adf857393b0bb'
                     'd67906c081e585410e38480ead51684dac3a38f7b64c9eb109f1973'
                     '9a4517cd7d5d6291e8af20a3fbf17336c7bf80ee718ee087e322ee4'
                     '1047dabefbcc34d10b66b644ddb3160a28c0639563d71993a26543e'
                     'adb7718f317bf5d9577a6156561b082a10029cd44012b18de684450'
                     '9fe058ba87980792285f2750969fe89c2cd6498db3545638d5379d1'
                     '25dccf64e06c1af33a6190841d223da1513333a7c9d78462abaab31'
                     'b9f96d5f34445ceb6309f2f6d2c8dde06441e87980d303ef9a1ff00'
                     '7e8be2f0be06cc15f', 16),
            'q': int('e71f8567447f42e75f5ef85ca20fe557ab0343d37ed09edc3f6e686'
                     '04d6b9dfb', 16),
            'g': int('5ba24de9607b8998e66ce6c4f812a314c6935842f7ab54cd82b19fa'
                     '104abfb5d84579a623b2574b37d22ccae9b3e415e48f5c0f9bcbdff'
                     '8071d63b9bb956e547af3a8df99e5d3061979652ff96b765cb3ee49'
                     '3643544c75dbe5bb39834531952a0fb4b0378b3fcbb4c8b5800a533'
                     '0392a2a04e700bb6ed7e0b85795ea38b1b962741b3f33b9dde2f4ec'
                     '1354f09e2eb78e95f037a5804b6171659f88715ce1a9b0cc90c27f3'
                     '5ef2f10ff0c7c7a2bb0154d9b8ebe76a3d764aa879af372f4240de8'
                     '347937e5a90cec9f41ff2f26b8da9a94a225d1a913717d73f10397d'
                     '2183f1ba3b7b45a68f1ff1893caf69a827802f7b6a48d51da6fbefb'
                     '64fd9a6c5b75c4561', 16),
            'digest_algorithm': 'SHA-256',
            'msg': binascii.unhexlify(
                b'4e3a28bcf90d1d2e75f075d9fbe55b36c5529b17bc3a9ccaba6935c9e20'
                b'548255b3dfae0f91db030c12f2c344b3a29c4151c5b209f5e319fdf1c23'
                b'b190f64f1fe5b330cb7c8fa952f9d90f13aff1cb11d63181da9efc6f7e1'
                b'5bfed4862d1a62c7dcf3ba8bf1ff304b102b1ec3f1497dddf09712cf323'
                b'f5610a9d10c3d9132659'),
            'y': int('5a55dceddd1134ee5f11ed85deb4d634a3643f5f36dc3a706892564'
                     '69a0b651ad22880f14ab85719434f9c0e407e60ea420e2a0cd29422'
                     'c4899c416359dbb1e592456f2b3cce233259c117542fd05f31ea25b'
                     '015d9121c890b90e0bad033be1368d229985aac7226d1c8c2eab325'
                     'ef3b2cd59d3b9f7de7dbc94af1a9339eb430ca36c26c46ecfa6c548'
                     '1711496f624e188ad7540ef5df26f8efacb820bd17a1f618acb50c9'
                     'bc197d4cb7ccac45d824a3bf795c234b556b06aeb92917345325208'
                     '4003f69fe98045fe74002ba658f93475622f76791d9b2623d1b5fff'
                     '2cc16844746efd2d30a6a8134bfc4c8cc80a46107901fb973c28fc5'
                     '53130f3286c1489da', 16),
            'r': int('633055e055f237c38999d81c397848c38cce80a55b649d9e7905c29'
                     '8e2a51447', 16),
            's': int('2bbf68317660ec1e4b154915027b0bc00ee19cfc0bf75d01930504f'
                     '2ce10a8b0', 16)},
        {
            'p': int('a8adb6c0b4cf9588012e5deff1a871d383e0e2a85b5e8e03d814fe1'
                     '3a059705e663230a377bf7323a8fa117100200bfd5adf857393b0bb'
                     'd67906c081e585410e38480ead51684dac3a38f7b64c9eb109f1973'
                     '9a4517cd7d5d6291e8af20a3fbf17336c7bf80ee718ee087e322ee4'
                     '1047dabefbcc34d10b66b644ddb3160a28c0639563d71993a26543e'
                     'adb7718f317bf5d9577a6156561b082a10029cd44012b18de684450'
                     '9fe058ba87980792285f2750969fe89c2cd6498db3545638d5379d1'
                     '25dccf64e06c1af33a6190841d223da1513333a7c9d78462abaab31'
                     'b9f96d5f34445ceb6309f2f6d2c8dde06441e87980d303ef9a1ff00'
                     '7e8be2f0be06cc15f', 16),
            'q': int('e71f8567447f42e75f5ef85ca20fe557ab0343d37ed09edc3f6e686'
                     '04d6b9dfb', 16),
            'g': int('5ba24de9607b8998e66ce6c4f812a314c6935842f7ab54cd82b19fa'
                     '104abfb5d84579a623b2574b37d22ccae9b3e415e48f5c0f9bcbdff'
                     '8071d63b9bb956e547af3a8df99e5d3061979652ff96b765cb3ee49'
                     '3643544c75dbe5bb39834531952a0fb4b0378b3fcbb4c8b5800a533'
                     '0392a2a04e700bb6ed7e0b85795ea38b1b962741b3f33b9dde2f4ec'
                     '1354f09e2eb78e95f037a5804b6171659f88715ce1a9b0cc90c27f3'
                     '5ef2f10ff0c7c7a2bb0154d9b8ebe76a3d764aa879af372f4240de8'
                     '347937e5a90cec9f41ff2f26b8da9a94a225d1a913717d73f10397d'
                     '2183f1ba3b7b45a68f1ff1893caf69a827802f7b6a48d51da6fbefb'
                     '64fd9a6c5b75c4561', 16),
            'digest_algorithm': 'SHA-256',
            'msg': binascii.unhexlify(
                b'a733b3f588d5ac9b9d4fe2f804df8c256403a9f8eef6f191fc48e1267fb'
                b'5b4d546ba11e77b667844e489bf0d5f72990aeb061d01ccd7949a23def7'
                b'4a803b7d92d51abfadeb4885ffd8ffd58ab87548a15c087a39b8993b2fa'
                b'64c9d31a594eeb7512da16955834336a234435c5a9d0dd9b15a94e11615'
                b'4dea63fdc8dd7a512181'),
            'y': int('356ed47537fbf02cb30a8cee0537f300dff1d0c467399ce70b87a87'
                     '58d5ec9dd256246fccaeb9dfe109f2a984f2ddaa87aad54ce0d31f9'
                     '07e504521baf4207d7073b0a4a9fc67d8ddda99f87aed6e0367cec2'
                     '7f9c608af743bf1ee6e11d55a182d43b024ace534029b866f642282'
                     '8bb81a39aae9601ee81c7f81dd358e69f4e2edfa4654d8a65bc6431'
                     '1dc86aac4abc1fc7a3f65159661a0d8e288eb8d665cb0adf5ac3d6b'
                     'a8e9453facf7542393ae24fd50451d3828086558f7ec528e284935a'
                     '53f67a1aa8e25d8ad5c4ad55d83aef883a4d9eeb6297e6a53f65049'
                     'ba9e2c6b7953a760bc1dc46f78ceaaa2c02f5375dd82e708744aa40'
                     'b15799eb81d7e5b1a', 16),
            'r': int('bcd490568c0a89ba311bef88ea4f4b03d273e793722722327095a37'
                     '8dd6f3522', 16),
            's': int('74498fc43091fcdd2d1ef0775f8286945a01cd72b805256b0451f9c'
                     'bd943cf82', 16)}
    ]
    assert expected == load_fips_dsa_sig_vectors(vector_data)


def test_load_fips_ecdsa_key_pair_vectors():
    vector_data = textwrap.dedent("""
    #  CAVS 11.0
    #  "Key Pair" information
    #  Curves selected: P-192 K-233 B-571
    #  Generated on Wed Mar 16 16:16:42 2011


    [P-192]

    [B.4.2 Key Pair Generation by Testing Candidates]
    N = 2

    d = e5ce89a34adddf25ff3bf1ffe6803f57d0220de3118798ea
    Qx = 8abf7b3ceb2b02438af19543d3e5b1d573fa9ac60085840f
    Qy = a87f80182dcd56a6a061f81f7da393e7cffd5e0738c6b245

    d = 7d14435714ad13ff23341cb567cc91198ff8617cc39751b2
    Qx = 39dc723b19527daa1e80425209c56463481b9b47c51f8cbd
    Qy = 432a3e84f2a16418834fabaf6b7d2341669512951f1672ad


    [K-233]

    [B.4.2 Key Pair Generation by Testing Candidates]
    N = 2

    d = 01da7422b50e3ff051f2aaaed10acea6cbf6110c517da2f4eaca8b5b87
    Qx = 01c7475da9a161e4b3f7d6b086494063543a979e34b8d7ac44204d47bf9f
    Qy = 0131cbd433f112871cc175943991b6a1350bf0cdd57ed8c831a2a7710c92

    d = 530951158f7b1586978c196603c12d25607d2cb0557efadb23cd0ce8
    Qx = d37500a0391d98d3070d493e2b392a2c79dc736c097ed24b7dd5ddec44
    Qy = 01d996cc79f37d8dba143d4a8ad9a8a60ed7ea760aae1ddba34d883f65d9


    [B-571]

    [B.4.2 Key Pair Generation by Testing Candidates]
    N = 2

    d = 01443e93c7ef6802655f641ecbe95e75f1f15b02d2e172f49a32e22047d5c00ebe1b3f\
f0456374461360667dbf07bc67f7d6135ee0d1d46a226a530fefe8ebf3b926e9fbad8d57a6
    Qx = 053e3710d8e7d4138db0a369c97e5332c1be38a20a4a84c36f5e55ea9fd6f34545b86\
4ea64f319e74b5ee9e4e1fa1b7c5b2db0e52467518f8c45b658824871d5d4025a6320ca06f8
    Qy = 03a22cfd370c4a449b936ae97ab97aab11c57686cca99d14ef184f9417fad8bedae4d\
f8357e3710bcda1833b30e297d4bf637938b995d231e557d13f062e81e830af5ab052208ead

    d = 03d2bd44ca9eeee8c860a4873ed55a54bdfdf5dab4060df7292877960b85d1fd496aa3\
3c587347213d7f6bf208a6ab4b430546e7b6ffbc3135bd12f44a28517867ca3c83a821d6f8
    Qx = 07a7af10f6617090bade18b2e092d0dfdc87cd616db7f2db133477a82bfe3ea421ebb\
7d6289980819292a719eb247195529ea60ad62862de0a26c72bfc49ecc81c2f9ed704e3168f
    Qy = 0721496cf16f988b1aabef3368450441df8439a0ca794170f270ead56203d675b57f5\
a4090a3a2f602a77ff3bac1417f7e25a683f667b3b91f105016a47afad46a0367b18e2bdf0c
    """).splitlines()

    expected = [
        {
            "curve": "secp192r1",
            "d": int("e5ce89a34adddf25ff3bf1ffe6803f57d0220de3118798ea", 16),
            "x": int("8abf7b3ceb2b02438af19543d3e5b1d573fa9ac60085840f", 16),
            "y": int("a87f80182dcd56a6a061f81f7da393e7cffd5e0738c6b245", 16)
        },

        {
            "curve": "secp192r1",
            "d": int("7d14435714ad13ff23341cb567cc91198ff8617cc39751b2", 16),
            "x": int("39dc723b19527daa1e80425209c56463481b9b47c51f8cbd", 16),
            "y": int("432a3e84f2a16418834fabaf6b7d2341669512951f1672ad", 16),
        },

        {
            "curve": "sect233k1",
            "d": int("1da7422b50e3ff051f2aaaed10acea6cbf6110c517da2f4e"
                     "aca8b5b87", 16),
            "x": int("1c7475da9a161e4b3f7d6b086494063543a979e34b8d7ac4"
                     "4204d47bf9f", 16),
            "y": int("131cbd433f112871cc175943991b6a1350bf0cdd57ed8c83"
                     "1a2a7710c92", 16),
        },

        {
            "curve": "sect233k1",
            "d": int("530951158f7b1586978c196603c12d25607d2cb0557efadb"
                     "23cd0ce8", 16),
            "x": int("d37500a0391d98d3070d493e2b392a2c79dc736c097ed24b"
                     "7dd5ddec44", 16),
            "y": int("1d996cc79f37d8dba143d4a8ad9a8a60ed7ea760aae1ddba"
                     "34d883f65d9", 16),
        },

        {
            "curve": "sect571r1",
            "d": int("1443e93c7ef6802655f641ecbe95e75f1f15b02d2e172f49"
                     "a32e22047d5c00ebe1b3ff0456374461360667dbf07bc67f"
                     "7d6135ee0d1d46a226a530fefe8ebf3b926e9fbad8d57a6", 16),
            "x": int("53e3710d8e7d4138db0a369c97e5332c1be38a20a4a84c36"
                     "f5e55ea9fd6f34545b864ea64f319e74b5ee9e4e1fa1b7c5"
                     "b2db0e52467518f8c45b658824871d5d4025a6320ca06f8", 16),
            "y": int("3a22cfd370c4a449b936ae97ab97aab11c57686cca99d14e"
                     "f184f9417fad8bedae4df8357e3710bcda1833b30e297d4b"
                     "f637938b995d231e557d13f062e81e830af5ab052208ead", 16),
        },

        {
            "curve": "sect571r1",
            "d": int("3d2bd44ca9eeee8c860a4873ed55a54bdfdf5dab4060df72"
                     "92877960b85d1fd496aa33c587347213d7f6bf208a6ab4b4"
                     "30546e7b6ffbc3135bd12f44a28517867ca3c83a821d6f8", 16),
            "x": int("7a7af10f6617090bade18b2e092d0dfdc87cd616db7f2db1"
                     "33477a82bfe3ea421ebb7d6289980819292a719eb2471955"
                     "29ea60ad62862de0a26c72bfc49ecc81c2f9ed704e3168f", 16),
            "y": int("721496cf16f988b1aabef3368450441df8439a0ca794170f"
                     "270ead56203d675b57f5a4090a3a2f602a77ff3bac1417f7"
                     "e25a683f667b3b91f105016a47afad46a0367b18e2bdf0c", 16),
        },
    ]

    assert expected == load_fips_ecdsa_key_pair_vectors(vector_data)


def test_load_fips_ecdsa_signing_vectors():
    vector_data = textwrap.dedent("""
    #  CAVS 11.2
    #  "SigVer" information for "ecdsa_values"
    #  Curves/SHAs selected: P-192, B-571,SHA-512
    #  Generated on Tue Aug 16 15:27:42 2011

    [P-192,SHA-1]

    Msg = ebf748d748ebbca7d29fb473698a6e6b4fb10c865d4af024cc39ae3df3464ba4f1d6\
d40f32bf9618a91bb5986fa1a2af048a0e14dc51e5267eb05e127d689d0ac6f1a7f156ce066316\
b971cc7a11d0fd7a2093e27cf2d08727a4e6748cc32fd59c7810c5b9019df21cdcc0bca432c0a3\
eed0785387508877114359cee4a071cf
    d = e14f37b3d1374ff8b03f41b9b3fdd2f0ebccf275d660d7f3
    Qx = 07008ea40b08dbe76432096e80a2494c94982d2d5bcf98e6
    Qy = 76fab681d00b414ea636ba215de26d98c41bd7f2e4d65477
    k = cb0abc7043a10783684556fb12c4154d57bc31a289685f25
    R = 6994d962bdd0d793ffddf855ec5bf2f91a9698b46258a63e
    S = 02ba6465a234903744ab02bc8521405b73cf5fc00e1a9f41
    Result = F (3 - S changed)

    Msg = 0dcb3e96d77ee64e9d0a350d31563d525755fc675f0c833504e83fc69c030181b42f\
e80c378e86274a93922c570d54a7a358c05755ec3ae91928e02236e81b43e596e4ccbf6a910488\
9c388072bec4e1faeae11fe4eb24fa4f9573560dcf2e3abc703c526d46d502c7a7222583431cc8\
178354ae7dbb84e3479917707bce0968
    d = 7a0235bea3d70445f14d56f9b7fb80ec8ff4eb2f76865244
    Qx = 0ea3c1fa1f124f26530cbfddeb831eecc67df31e08889d1d
    Qy = 7215a0cce0501b47903bd8fe1179c2dfe07bd076f89f5225
    k = 3c646b0f03f5575e5fd463d4319817ce8bd3022eaf551cef
    R = a3ba51c39c43991d87dff0f34d0bec7c883299e04f60f95e
    S = 8a7f9c59c6d65ad390e4c19636ba92b53be5d0f848b4e1f7

    [B-571,SHA-512]

    Msg = 10d2e00ae57176c79cdfc746c0c887abe799ee445b151b008e3d9f81eb69be40298d\
df37b5c45a9b6e5ff83785d8c140cf11e6a4c3879a2845796872363da24b10f1f8d9cc48f8af20\
681dceb60dd62095d6d3b1779a4a805de3d74e38983b24c0748618e2f92ef7cac257ff4bd1f411\
13f2891eb13c47930e69ddbe91f270fb
    d = 03e1b03ffca4399d5b439fac8f87a5cb06930f00d304193d7daf83d5947d0c1e293f74\
aef8e56849f16147133c37a6b3d1b1883e5d61d6b871ea036c5291d9a74541f28878cb986
    Qx = 3b236fc135d849d50140fdaae1045e6ae35ef61091e98f5059b30eb16acdd0deb2bc0\
d3544bc3a666e0014e50030134fe5466a9e4d3911ed580e28851f3747c0010888e819d3d1f
    Qy = 3a8b6627a587d289032bd76374d16771188d7ff281c39542c8977f6872fa932e5daa1\
4e13792dea9ffe8e9f68d6b525ec99b81a5a60cfb0590cc6f297cfff8d7ba1a8bb81fe2e16
    k = 2e56a94cfbbcd293e242f0c2a2e9df289a9480e6ba52e0f00fa19bcf2a7769bd155e6b\
79ddbd6a8646b0e69c8baea27f8034a18796e8eb4fe6e0e2358c383521d9375d2b6b437f9
    R = 2eb1c5c1fc93cf3c8babed12c031cf1504e094174fd335104cbe4a2abd210b5a14b1c3\
a455579f1ed0517c31822340e4dd3c1f967e1b4b9d071a1072afc1a199f8c548cd449a634
    S = 22f97bb48641235826cf4e597fa8de849402d6bd6114ad2d7fbcf53a08247e5ee921f1\
bd5994dffee36eedff5592bb93b8bb148214da3b7baebffbd96b4f86c55b3f6bbac142442
    Result = P (0 )

    Msg = b61a0849a28672cb536fcf61ea2eb389d02ff7a09aa391744cae6597bd56703c40c5\
0ca2dee5f7ee796acfd47322f03d8dbe4d99dc8eec588b4e5467f123075b2d74b2a0b0bbfd3ac5\
487a905fad6d6ac1421c2e564c0cf15e1f0f10bc31c249b7b46edd2462a55f85560d99bde9d5b0\
6b97817d1dbe0a67c701d6e6e7878272
    d = 2e09ffd8b434bb7f67d1d3ccf482164f1653c6e4ec64dec2517aa21b7a93b2b21ea1ee\
bb54734882f29303e489f02e3b741a87287e2dcdf3858eb6d2ec668f8b5b26f442ce513a2
    Qx = 36f1be8738dd7dae4486b86a08fe90424f3673e76b10e739442e15f3bfafaf841842a\
c98e490521b7e7bb94c127529f6ec6a42cc6f06fc80606f1210fe020ff508148f93301c9d3
    Qy = 4d39666ebe99fe214336ad440d776c88eb916f2f4a3433548b87d2aebed840b424d15\
c8341b4a0a657bf6a234d4fe78631c8e07ac1f4dc7474cd6b4545d536b7b17c160db4562d9
    k = 378e7801566d7b77db7a474717ab2195b02957cc264a9449d4126a7cc574728ed5a476\
9abd5dde987ca66cfe3d45b5fc52ffd266acb8a8bb3fcb4b60f7febbf48aebe33bd3efbdd
    R = 3d8105f87fe3166046c08e80a28acc98a80b8b7a729623053c2a9e80afd06756edfe09\
bdcf3035f6829ede041b745955d219dc5d30ddd8b37f6ba0f6d2857504cdc68a1ed812a10
    S = 34db9998dc53527114518a7ce3783d674ca8cced823fa05e2942e7a0a20b3cc583dcd9\
30c43f9b93079c5ee18a1f5a66e7c3527c18610f9b47a4da7e245ef803e0662e4d2ad721c
    """).splitlines()

    expected = [
        {
            "curve": "secp192r1",
            "digest_algorithm": "SHA-1",
            "message": binascii.unhexlify(
                b"ebf748d748ebbca7d29fb473698a6e6b4fb10c865d4af024cc39ae3df346"
                b"4ba4f1d6d40f32bf9618a91bb5986fa1a2af048a0e14dc51e5267eb05e12"
                b"7d689d0ac6f1a7f156ce066316b971cc7a11d0fd7a2093e27cf2d08727a4"
                b"e6748cc32fd59c7810c5b9019df21cdcc0bca432c0a3eed0785387508877"
                b"114359cee4a071cf"
            ),
            "d": int("e14f37b3d1374ff8b03f41b9b3fdd2f0ebccf275d660d7f3", 16),
            "x": int("7008ea40b08dbe76432096e80a2494c94982d2d5bcf98e6", 16),
            "y": int("76fab681d00b414ea636ba215de26d98c41bd7f2e4d65477", 16),
            "r": int("6994d962bdd0d793ffddf855ec5bf2f91a9698b46258a63e", 16),
            "s": int("02ba6465a234903744ab02bc8521405b73cf5fc00e1a9f41", 16),
            "fail": True
        },
        {
            "curve": "secp192r1",
            "digest_algorithm": "SHA-1",
            "message": binascii.unhexlify(
                b"0dcb3e96d77ee64e9d0a350d31563d525755fc675f0c833504e83fc69c03"
                b"0181b42fe80c378e86274a93922c570d54a7a358c05755ec3ae91928e022"
                b"36e81b43e596e4ccbf6a9104889c388072bec4e1faeae11fe4eb24fa4f95"
                b"73560dcf2e3abc703c526d46d502c7a7222583431cc8178354ae7dbb84e3"
                b"479917707bce0968"
            ),
            "d": int("7a0235bea3d70445f14d56f9b7fb80ec8ff4eb2f76865244", 16),
            "x": int("ea3c1fa1f124f26530cbfddeb831eecc67df31e08889d1d", 16),
            "y": int("7215a0cce0501b47903bd8fe1179c2dfe07bd076f89f5225", 16),
            "r": int("a3ba51c39c43991d87dff0f34d0bec7c883299e04f60f95e", 16),
            "s": int("8a7f9c59c6d65ad390e4c19636ba92b53be5d0f848b4e1f7", 16),
        },
        {
            "curve": "sect571r1",
            "digest_algorithm": "SHA-512",
            "message": binascii.unhexlify(
                b"10d2e00ae57176c79cdfc746c0c887abe799ee445b151b008e3d9f81eb69"
                b"be40298ddf37b5c45a9b6e5ff83785d8c140cf11e6a4c3879a2845796872"
                b"363da24b10f1f8d9cc48f8af20681dceb60dd62095d6d3b1779a4a805de3"
                b"d74e38983b24c0748618e2f92ef7cac257ff4bd1f41113f2891eb13c4793"
                b"0e69ddbe91f270fb"
            ),
            "d": int("3e1b03ffca4399d5b439fac8f87a5cb06930f00d304193d7daf83d59"
                     "47d0c1e293f74aef8e56849f16147133c37a6b3d1b1883e5d61d6b87"
                     "1ea036c5291d9a74541f28878cb986", 16),
            "x": int("3b236fc135d849d50140fdaae1045e6ae35ef61091e98f5059b30eb1"
                     "6acdd0deb2bc0d3544bc3a666e0014e50030134fe5466a9e4d3911ed"
                     "580e28851f3747c0010888e819d3d1f", 16),
            "y": int("3a8b6627a587d289032bd76374d16771188d7ff281c39542c8977f68"
                     "72fa932e5daa14e13792dea9ffe8e9f68d6b525ec99b81a5a60cfb05"
                     "90cc6f297cfff8d7ba1a8bb81fe2e16", 16),
            "r": int("2eb1c5c1fc93cf3c8babed12c031cf1504e094174fd335104cbe4a2a"
                     "bd210b5a14b1c3a455579f1ed0517c31822340e4dd3c1f967e1b4b9d"
                     "071a1072afc1a199f8c548cd449a634", 16),
            "s": int("22f97bb48641235826cf4e597fa8de849402d6bd6114ad2d7fbcf53a"
                     "08247e5ee921f1bd5994dffee36eedff5592bb93b8bb148214da3b7b"
                     "aebffbd96b4f86c55b3f6bbac142442", 16),
            "fail": False
        },
        {
            "curve": "sect571r1",
            "digest_algorithm": "SHA-512",
            "message": binascii.unhexlify(
                b"b61a0849a28672cb536fcf61ea2eb389d02ff7a09aa391744cae6597bd56"
                b"703c40c50ca2dee5f7ee796acfd47322f03d8dbe4d99dc8eec588b4e5467"
                b"f123075b2d74b2a0b0bbfd3ac5487a905fad6d6ac1421c2e564c0cf15e1f"
                b"0f10bc31c249b7b46edd2462a55f85560d99bde9d5b06b97817d1dbe0a67"
                b"c701d6e6e7878272"
            ),
            "d": int("2e09ffd8b434bb7f67d1d3ccf482164f1653c6e4ec64dec2517aa21b"
                     "7a93b2b21ea1eebb54734882f29303e489f02e3b741a87287e2dcdf3"
                     "858eb6d2ec668f8b5b26f442ce513a2", 16),
            "x": int("36f1be8738dd7dae4486b86a08fe90424f3673e76b10e739442e15f3"
                     "bfafaf841842ac98e490521b7e7bb94c127529f6ec6a42cc6f06fc80"
                     "606f1210fe020ff508148f93301c9d3", 16),
            "y": int("4d39666ebe99fe214336ad440d776c88eb916f2f4a3433548b87d2ae"
                     "bed840b424d15c8341b4a0a657bf6a234d4fe78631c8e07ac1f4dc74"
                     "74cd6b4545d536b7b17c160db4562d9", 16),
            "r": int("3d8105f87fe3166046c08e80a28acc98a80b8b7a729623053c2a9e80"
                     "afd06756edfe09bdcf3035f6829ede041b745955d219dc5d30ddd8b3"
                     "7f6ba0f6d2857504cdc68a1ed812a10", 16),
            "s": int("34db9998dc53527114518a7ce3783d674ca8cced823fa05e2942e7a0"
                     "a20b3cc583dcd930c43f9b93079c5ee18a1f5a66e7c3527c18610f9b"
                     "47a4da7e245ef803e0662e4d2ad721c", 16)
        }
    ]
    assert expected == load_fips_ecdsa_signing_vectors(vector_data)


def test_vector_version():
    assert cryptography.__version__ == cryptography_vectors.__version__


def test_raises_unsupported_algorithm_wrong_type():
    # Check that it raises if the wrong type of exception is raised.
    class TestException(Exception):
        pass

    with pytest.raises(TestException):
        with raises_unsupported_algorithm(None):
            raise TestException


def test_raises_unsupported_algorithm_wrong_reason():
    # Check that it fails if the wrong reason code is raised.
    with pytest.raises(AssertionError):
        with raises_unsupported_algorithm(None):
            raise UnsupportedAlgorithm("An error.",
                                       _Reasons.BACKEND_MISSING_INTERFACE)


def test_raises_unsupported_no_exc():
    # Check that it fails if no exception is raised.
    with pytest.raises(pytest.fail.Exception):
        with raises_unsupported_algorithm(
            _Reasons.BACKEND_MISSING_INTERFACE
        ):
            pass


def test_raises_unsupported_algorithm():
    # Check that it doesn't assert if the right things are raised.
    with raises_unsupported_algorithm(
        _Reasons.BACKEND_MISSING_INTERFACE
    ) as exc_info:
        raise UnsupportedAlgorithm("An error.",
                                   _Reasons.BACKEND_MISSING_INTERFACE)
    assert exc_info.type is UnsupportedAlgorithm

########NEW FILE########
__FILENAME__ = utils
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import binascii
import collections
import re
from contextlib import contextmanager

from pyasn1.codec.der import encoder
from pyasn1.type import namedtype, univ

import pytest

import six

from cryptography.exceptions import UnsupportedAlgorithm

import cryptography_vectors


HashVector = collections.namedtuple("HashVector", ["message", "digest"])
KeyedHashVector = collections.namedtuple(
    "KeyedHashVector", ["message", "digest", "key"]
)


def select_backends(names, backend_list):
    if names is None:
        return backend_list
    split_names = [x.strip() for x in names.split(',')]
    # this must be duplicated and then removed to preserve the metadata
    # pytest associates. Appending backends to a new list doesn't seem to work
    selected_backends = []
    for backend in backend_list:
        if backend.name in split_names:
            selected_backends.append(backend)

    if len(selected_backends) > 0:
        return selected_backends
    else:
        raise ValueError(
            "No backend selected. Tried to select: {0}".format(split_names)
        )


def check_for_iface(name, iface, item):
    if name in item.keywords and "backend" in item.funcargs:
        if not isinstance(item.funcargs["backend"], iface):
            pytest.skip("{0} backend does not support {1}".format(
                item.funcargs["backend"], name
            ))


def check_backend_support(item):
    supported = item.keywords.get("supported")
    if supported and "backend" in item.funcargs:
        if not supported.kwargs["only_if"](item.funcargs["backend"]):
            pytest.skip("{0} ({1})".format(
                supported.kwargs["skip_message"], item.funcargs["backend"]
            ))
    elif supported:
        raise ValueError("This mark is only available on methods that take a "
                         "backend")


@contextmanager
def raises_unsupported_algorithm(reason):
    with pytest.raises(UnsupportedAlgorithm) as exc_info:
        yield exc_info

    assert exc_info.value._reason is reason


class _DSSSigValue(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('r', univ.Integer()),
        namedtype.NamedType('s', univ.Integer())
    )


def der_encode_dsa_signature(r, s):
    sig = _DSSSigValue()
    sig.setComponentByName('r', r)
    sig.setComponentByName('s', s)
    return encoder.encode(sig)


def load_vectors_from_file(filename, loader):
    with cryptography_vectors.open_vector_file(filename) as vector_file:
        return loader(vector_file)


def load_nist_vectors(vector_data):
    test_data = None
    data = []

    for line in vector_data:
        line = line.strip()

        # Blank lines, comments, and section headers are ignored
        if not line or line.startswith("#") or (line.startswith("[")
                                                and line.endswith("]")):
            continue

        if line.strip() == "FAIL":
            test_data["fail"] = True
            continue

        # Build our data using a simple Key = Value format
        name, value = [c.strip() for c in line.split("=")]

        # Some tests (PBKDF2) contain \0, which should be interpreted as a
        # null character rather than literal.
        value = value.replace("\\0", "\0")

        # COUNT is a special token that indicates a new block of data
        if name.upper() == "COUNT":
            test_data = {}
            data.append(test_data)
            continue
        # For all other tokens we simply want the name, value stored in
        # the dictionary
        else:
            test_data[name.lower()] = value.encode("ascii")

    return data


def load_cryptrec_vectors(vector_data):
    cryptrec_list = []

    for line in vector_data:
        line = line.strip()

        # Blank lines and comments are ignored
        if not line or line.startswith("#"):
            continue

        if line.startswith("K"):
            key = line.split(" : ")[1].replace(" ", "").encode("ascii")
        elif line.startswith("P"):
            pt = line.split(" : ")[1].replace(" ", "").encode("ascii")
        elif line.startswith("C"):
            ct = line.split(" : ")[1].replace(" ", "").encode("ascii")
            # after a C is found the K+P+C tuple is complete
            # there are many P+C pairs for each K
            cryptrec_list.append({
                "key": key,
                "plaintext": pt,
                "ciphertext": ct
            })
        else:
            raise ValueError("Invalid line in file '{}'".format(line))
    return cryptrec_list


def load_hash_vectors(vector_data):
    vectors = []
    key = None
    msg = None
    md = None

    for line in vector_data:
        line = line.strip()

        if not line or line.startswith("#") or line.startswith("["):
            continue

        if line.startswith("Len"):
            length = int(line.split(" = ")[1])
        elif line.startswith("Key"):
            # HMAC vectors contain a key attribute. Hash vectors do not.
            key = line.split(" = ")[1].encode("ascii")
        elif line.startswith("Msg"):
            # In the NIST vectors they have chosen to represent an empty
            # string as hex 00, which is of course not actually an empty
            # string. So we parse the provided length and catch this edge case.
            msg = line.split(" = ")[1].encode("ascii") if length > 0 else b""
        elif line.startswith("MD"):
            md = line.split(" = ")[1]
            # after MD is found the Msg+MD (+ potential key) tuple is complete
            if key is not None:
                vectors.append(KeyedHashVector(msg, md, key))
                key = None
                msg = None
                md = None
            else:
                vectors.append(HashVector(msg, md))
                msg = None
                md = None
        else:
            raise ValueError("Unknown line in hash vector")
    return vectors


def load_pkcs1_vectors(vector_data):
    """
    Loads data out of RSA PKCS #1 vector files.
    """
    private_key_vector = None
    public_key_vector = None
    attr = None
    key = None
    example_vector = None
    examples = []
    vectors = []
    for line in vector_data:
        if (
            line.startswith("# PSS Example") or
            line.startswith("# OAEP Example") or
            line.startswith("# PKCS#1 v1.5")
        ):
            if example_vector:
                for key, value in six.iteritems(example_vector):
                    hex_str = "".join(value).replace(" ", "").encode("ascii")
                    example_vector[key] = hex_str
                examples.append(example_vector)

            attr = None
            example_vector = collections.defaultdict(list)

        if line.startswith("# Message"):
            attr = "message"
            continue
        elif line.startswith("# Salt"):
            attr = "salt"
            continue
        elif line.startswith("# Seed"):
            attr = "seed"
            continue
        elif line.startswith("# Signature"):
            attr = "signature"
            continue
        elif line.startswith("# Encryption"):
            attr = "encryption"
            continue
        elif (
            example_vector and
            line.startswith("# =============================================")
        ):
            for key, value in six.iteritems(example_vector):
                hex_str = "".join(value).replace(" ", "").encode("ascii")
                example_vector[key] = hex_str
            examples.append(example_vector)
            example_vector = None
            attr = None
        elif example_vector and line.startswith("#"):
            continue
        else:
            if attr is not None and example_vector is not None:
                example_vector[attr].append(line.strip())
                continue

        if (
            line.startswith("# Example") or
            line.startswith("# =============================================")
        ):
            if key:
                assert private_key_vector
                assert public_key_vector

                for key, value in six.iteritems(public_key_vector):
                    hex_str = "".join(value).replace(" ", "")
                    public_key_vector[key] = int(hex_str, 16)

                for key, value in six.iteritems(private_key_vector):
                    hex_str = "".join(value).replace(" ", "")
                    private_key_vector[key] = int(hex_str, 16)

                private_key_vector["examples"] = examples
                examples = []

                assert (
                    private_key_vector['public_exponent'] ==
                    public_key_vector['public_exponent']
                )

                assert (
                    private_key_vector['modulus'] ==
                    public_key_vector['modulus']
                )

                vectors.append(
                    (private_key_vector, public_key_vector)
                )

            public_key_vector = collections.defaultdict(list)
            private_key_vector = collections.defaultdict(list)
            key = None
            attr = None

        if private_key_vector is None or public_key_vector is None:
            continue

        if line.startswith("# Private key"):
            key = private_key_vector
        elif line.startswith("# Public key"):
            key = public_key_vector
        elif line.startswith("# Modulus:"):
            attr = "modulus"
        elif line.startswith("# Public exponent:"):
            attr = "public_exponent"
        elif line.startswith("# Exponent:"):
            if key is public_key_vector:
                attr = "public_exponent"
            else:
                assert key is private_key_vector
                attr = "private_exponent"
        elif line.startswith("# Prime 1:"):
            attr = "p"
        elif line.startswith("# Prime 2:"):
            attr = "q"
        elif line.startswith("# Prime exponent 1:"):
            attr = "dmp1"
        elif line.startswith("# Prime exponent 2:"):
            attr = "dmq1"
        elif line.startswith("# Coefficient:"):
            attr = "iqmp"
        elif line.startswith("#"):
            attr = None
        else:
            if key is not None and attr is not None:
                key[attr].append(line.strip())
    return vectors


def load_rsa_nist_vectors(vector_data):
    test_data = None
    p = None
    salt_length = None
    data = []

    for line in vector_data:
        line = line.strip()

        # Blank lines and section headers are ignored
        if not line or line.startswith("["):
            continue

        if line.startswith("# Salt len:"):
            salt_length = int(line.split(":")[1].strip())
            continue
        elif line.startswith("#"):
            continue

        # Build our data using a simple Key = Value format
        name, value = [c.strip() for c in line.split("=")]

        if name == "n":
            n = int(value, 16)
        elif name == "e" and p is None:
            e = int(value, 16)
        elif name == "p":
            p = int(value, 16)
        elif name == "q":
            q = int(value, 16)
        elif name == "SHAAlg":
            if p is None:
                test_data = {
                    "modulus": n,
                    "public_exponent": e,
                    "salt_length": salt_length,
                    "algorithm": value,
                    "fail": False
                }
            else:
                test_data = {
                    "modulus": n,
                    "p": p,
                    "q": q,
                    "algorithm": value
                }
                if salt_length is not None:
                    test_data["salt_length"] = salt_length
            data.append(test_data)
        elif name == "e" and p is not None:
            test_data["public_exponent"] = int(value, 16)
        elif name == "d":
            test_data["private_exponent"] = int(value, 16)
        elif name == "Result":
            test_data["fail"] = value.startswith("F")
        # For all other tokens we simply want the name, value stored in
        # the dictionary
        else:
            test_data[name.lower()] = value.encode("ascii")

    return data


def load_fips_dsa_key_pair_vectors(vector_data):
    """
    Loads data out of the FIPS DSA KeyPair vector files.
    """
    vectors = []
    # When reading_key_data is set to True it tells the loader to continue
    # constructing dictionaries. We set reading_key_data to False during the
    # blocks of the vectors of N=224 because we don't support it.
    reading_key_data = True
    for line in vector_data:
        line = line.strip()

        if not line or line.startswith("#"):
            continue
        elif line.startswith("[mod = L=1024"):
            continue
        elif line.startswith("[mod = L=2048, N=224"):
            reading_key_data = False
            continue
        elif line.startswith("[mod = L=2048, N=256"):
            reading_key_data = True
            continue
        elif line.startswith("[mod = L=3072"):
            continue

        if not reading_key_data:
            continue

        elif reading_key_data:
            if line.startswith("P"):
                vectors.append({'p': int(line.split("=")[1], 16)})
            elif line.startswith("Q"):
                vectors[-1]['q'] = int(line.split("=")[1], 16)
            elif line.startswith("G"):
                vectors[-1]['g'] = int(line.split("=")[1], 16)
            elif line.startswith("X") and 'x' not in vectors[-1]:
                vectors[-1]['x'] = int(line.split("=")[1], 16)
            elif line.startswith("X") and 'x' in vectors[-1]:
                vectors.append({'p': vectors[-1]['p'],
                                'q': vectors[-1]['q'],
                                'g': vectors[-1]['g'],
                                'x': int(line.split("=")[1], 16)
                                })
            elif line.startswith("Y"):
                vectors[-1]['y'] = int(line.split("=")[1], 16)

    return vectors


def load_fips_dsa_sig_vectors(vector_data):
    """
    Loads data out of the FIPS DSA SigVer vector files.
    """
    vectors = []
    sha_regex = re.compile(
        r"\[mod = L=...., N=..., SHA-(?P<sha>1|224|256|384|512)\]"
    )
    # When reading_key_data is set to True it tells the loader to continue
    # constructing dictionaries. We set reading_key_data to False during the
    # blocks of the vectors of N=224 because we don't support it.
    reading_key_data = True

    for line in vector_data:
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        sha_match = sha_regex.match(line)
        if sha_match:
            digest_algorithm = "SHA-{0}".format(sha_match.group("sha"))

        if line.startswith("[mod = L=2048, N=224"):
            reading_key_data = False
            continue
        elif line.startswith("[mod = L=2048, N=256"):
            reading_key_data = True
            continue

        if not reading_key_data or line.startswith("[mod"):
            continue

        name, value = [c.strip() for c in line.split("=")]

        if name == "P":
            vectors.append({'p': int(value, 16),
                            'digest_algorithm': digest_algorithm})
        elif name == "Q":
            vectors[-1]['q'] = int(value, 16)
        elif name == "G":
            vectors[-1]['g'] = int(value, 16)
        elif name == "Msg" and 'msg' not in vectors[-1]:
            hexmsg = value.strip().encode("ascii")
            vectors[-1]['msg'] = binascii.unhexlify(hexmsg)
        elif name == "Msg" and 'msg' in vectors[-1]:
            hexmsg = value.strip().encode("ascii")
            vectors.append({'p': vectors[-1]['p'],
                            'q': vectors[-1]['q'],
                            'g': vectors[-1]['g'],
                            'digest_algorithm':
                            vectors[-1]['digest_algorithm'],
                            'msg': binascii.unhexlify(hexmsg)})
        elif name == "X":
            vectors[-1]['x'] = int(value, 16)
        elif name == "Y":
            vectors[-1]['y'] = int(value, 16)
        elif name == "R":
            vectors[-1]['r'] = int(value, 16)
        elif name == "S":
            vectors[-1]['s'] = int(value, 16)
        elif name == "Result":
            vectors[-1]['result'] = value.split("(")[0].strip()

    return vectors


# http://tools.ietf.org/html/rfc4492#appendix-A
_ECDSA_CURVE_NAMES = {
    "P-192": "secp192r1",
    "P-224": "secp224r1",
    "P-256": "secp256r1",
    "P-384": "secp384r1",
    "P-521": "secp521r1",

    "K-163": "sect163k1",
    "K-233": "sect233k1",
    "K-283": "sect283k1",
    "K-409": "sect409k1",
    "K-571": "sect571k1",

    "B-163": "sect163r2",
    "B-233": "sect233r1",
    "B-283": "sect283r1",
    "B-409": "sect409r1",
    "B-571": "sect571r1",
}


def load_fips_ecdsa_key_pair_vectors(vector_data):
    """
    Loads data out of the FIPS ECDSA KeyPair vector files.
    """
    vectors = []
    key_data = None
    for line in vector_data:
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if line[1:-1] in _ECDSA_CURVE_NAMES:
            curve_name = _ECDSA_CURVE_NAMES[line[1:-1]]

        elif line.startswith("d = "):
            if key_data is not None:
                vectors.append(key_data)

            key_data = {
                "curve": curve_name,
                "d": int(line.split("=")[1], 16)
            }

        elif key_data is not None:
            if line.startswith("Qx = "):
                key_data["x"] = int(line.split("=")[1], 16)
            elif line.startswith("Qy = "):
                key_data["y"] = int(line.split("=")[1], 16)

    if key_data is not None:
        vectors.append(key_data)

    return vectors


def load_fips_ecdsa_signing_vectors(vector_data):
    """
    Loads data out of the FIPS ECDSA SigGen vector files.
    """
    vectors = []

    curve_rx = re.compile(
        r"\[(?P<curve>[PKB]-[0-9]{3}),SHA-(?P<sha>1|224|256|384|512)\]"
    )

    data = None
    for line in vector_data:
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        curve_match = curve_rx.match(line)
        if curve_match:
            curve_name = _ECDSA_CURVE_NAMES[curve_match.group("curve")]
            digest_name = "SHA-{0}".format(curve_match.group("sha"))

        elif line.startswith("Msg = "):
            if data is not None:
                vectors.append(data)

            hexmsg = line.split("=")[1].strip().encode("ascii")

            data = {
                "curve": curve_name,
                "digest_algorithm": digest_name,
                "message": binascii.unhexlify(hexmsg)
            }

        elif data is not None:
            if line.startswith("Qx = "):
                data["x"] = int(line.split("=")[1], 16)
            elif line.startswith("Qy = "):
                data["y"] = int(line.split("=")[1], 16)
            elif line.startswith("R = "):
                data["r"] = int(line.split("=")[1], 16)
            elif line.startswith("S = "):
                data["s"] = int(line.split("=")[1], 16)
            elif line.startswith("d = "):
                data["d"] = int(line.split("=")[1], 16)
            elif line.startswith("Result = "):
                data["fail"] = line.split("=")[1].strip()[0] == "F"

    if data is not None:
        vectors.append(data)
    return vectors

########NEW FILE########
__FILENAME__ = __about__
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import absolute_import, division, print_function

__all__ = [
    "__title__", "__summary__", "__uri__", "__version__", "__author__",
    "__email__", "__license__", "__copyright__",
]

__title__ = "cryptography_vectors"
__summary__ = "Test vectors for the cryptography package."

__uri__ = "https://github.com/pyca/cryptography"

__version__ = "0.5.dev1"

__author__ = "The cryptography developers"
__email__ = "cryptography-dev@python.org"

__license__ = "Apache License, Version 2.0"
__copyright__ = "Copyright 2013-2014 %s" % __author__

########NEW FILE########
