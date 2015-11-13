__FILENAME__ = common
#    Copyright 2012 Kjell Braden <afflux@pentabarf.de>
#
#    This file is part of the python-potr library.
#
#    python-potr is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    any later version.
#
#    python-potr is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this library.  If not, see <http://www.gnu.org/licenses/>.

# some python3 compatibilty
from __future__ import unicode_literals

import logging
import struct

from potr.utils import human_hash, bytes_to_long, unpack, pack_mpi

DEFAULT_KEYTYPE = 0x0000
pkTypes = {}
def registerkeytype(cls):
    if cls.keyType is None:
        raise TypeError('registered key class needs a type value')
    pkTypes[cls.keyType] = cls
    return cls

def generateDefaultKey():
    return pkTypes[DEFAULT_KEYTYPE].generate()

class PK(object):
    keyType = None

    @classmethod
    def generate(cls):
        raise NotImplementedError

    @classmethod
    def parsePayload(cls, data, private=False):
        raise NotImplementedError

    def sign(self, data):
        raise NotImplementedError
    def verify(self, data):
        raise NotImplementedError
    def fingerprint(self):
        raise NotImplementedError

    def serializePublicKey(self):
        return struct.pack(b'!H', self.keyType) \
                + self.getSerializedPublicPayload()

    def getSerializedPublicPayload(self):
        buf = b''
        for x in self.getPublicPayload():
            buf += pack_mpi(x)
        return buf

    def getPublicPayload(self):
        raise NotImplementedError

    def serializePrivateKey(self):
        return struct.pack(b'!H', self.keyType) \
                + self.getSerializedPrivatePayload()

    def getSerializedPrivatePayload(self):
        buf = b''
        for x in self.getPrivatePayload():
            buf += pack_mpi(x)
        return buf

    def getPrivatePayload(self):
        raise NotImplementedError

    def cfingerprint(self):
        return '{0:040x}'.format(bytes_to_long(self.fingerprint()))

    @classmethod
    def parsePrivateKey(cls, data):
        implCls, data = cls.getImplementation(data)
        logging.debug('Got privkey of type %r', implCls)
        return implCls.parsePayload(data, private=True)

    @classmethod
    def parsePublicKey(cls, data):
        implCls, data = cls.getImplementation(data)
        logging.debug('Got pubkey of type %r', implCls)
        return implCls.parsePayload(data)

    def __str__(self):
        return human_hash(self.cfingerprint())
    def __repr__(self):
        return '<{cls}(fpr=\'{fpr}\')>'.format(
                cls=self.__class__.__name__, fpr=str(self))

    @staticmethod
    def getImplementation(data):
        typeid, data = unpack(b'!H', data)
        cls = pkTypes.get(typeid, None)
        if cls is None:
            raise NotImplementedError('unknown typeid %r' % typeid)
        return cls, data

########NEW FILE########
__FILENAME__ = pycrypto
#    Copyright 2012 Kjell Braden <afflux@pentabarf.de>
#
#    This file is part of the python-potr library.
#
#    python-potr is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    any later version.
#
#    python-potr is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this library.  If not, see <http://www.gnu.org/licenses/>.

from Crypto import Cipher
from Crypto.Hash import SHA256 as _SHA256
from Crypto.Hash import SHA as _SHA1
from Crypto.Hash import HMAC as _HMAC
from Crypto.PublicKey import DSA
from Crypto.Random import random
from numbers import Number

from potr.compatcrypto import common
from potr.utils import read_mpi, bytes_to_long, long_to_bytes

def SHA256(data):
    return _SHA256.new(data).digest()

def SHA1(data):
    return _SHA1.new(data).digest()

def HMAC(key, data, mod):
    return _HMAC.new(key, msg=data, digestmod=mod).digest()

def SHA1HMAC(key, data):
    return HMAC(key, data, _SHA1)

def SHA256HMAC(key, data):
    return HMAC(key, data, _SHA256)

def SHA256HMAC160(key, data):
    return SHA256HMAC(key, data)[:20]

def AESCTR(key, counter=0):
    if isinstance(counter, Number):
        counter = Counter(counter)
    if not isinstance(counter, Counter):
        raise TypeError
    return Cipher.AES.new(key, Cipher.AES.MODE_CTR, counter=counter)

class Counter(object):
    def __init__(self, prefix):
        self.prefix = prefix
        self.val = 0

    def inc(self):
        self.prefix += 1
        self.val = 0

    def __setattr__(self, attr, val):
        if attr == 'prefix':
            self.val = 0
        super(Counter, self).__setattr__(attr, val)

    def __repr__(self):
        return '<Counter(p={p!r},v={v!r})>'.format(p=self.prefix, v=self.val)

    def byteprefix(self):
        return long_to_bytes(self.prefix, 8)

    def __call__(self):
        bytesuffix = long_to_bytes(self.val, 8)
        self.val += 1
        return self.byteprefix() + bytesuffix

@common.registerkeytype
class DSAKey(common.PK):
    keyType = 0x0000

    def __init__(self, key=None, private=False):
        self.priv = self.pub = None

        if not isinstance(key, tuple):
            raise TypeError('4/5-tuple required for key')

        if len(key) == 5 and private:
            self.priv = DSA.construct(key)
            self.pub = self.priv.publickey()
        elif len(key) == 4 and not private:
            self.pub = DSA.construct(key)
        else:
            raise TypeError('wrong number of arguments for ' \
                    'private={0!r}: got {1} '
                    .format(private, len(key)))

    def getPublicPayload(self):
        return (self.pub.p, self.pub.q, self.pub.g, self.pub.y)

    def getPrivatePayload(self):
        return (self.priv.p, self.priv.q, self.priv.g, self.priv.y, self.priv.x)

    def fingerprint(self):
        return SHA1(self.getSerializedPublicPayload())

    def sign(self, data):
        # 2 <= K <= q
        K = random.randrange(2, self.priv.q)
        r, s = self.priv.sign(data, K)
        return long_to_bytes(r, 20) + long_to_bytes(s, 20)

    def verify(self, data, sig):
        r, s = bytes_to_long(sig[:20]), bytes_to_long(sig[20:])
        return self.pub.verify(data, (r, s))

    def __hash__(self):
        return bytes_to_long(self.fingerprint())

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return self.fingerprint() == other.fingerprint()

    def __ne__(self, other):
        return not (self == other)

    @classmethod
    def generate(cls):
        privkey = DSA.generate(1024)
        return cls((privkey.key.y, privkey.key.g, privkey.key.p, privkey.key.q,
                privkey.key.x), private=True)

    @classmethod
    def parsePayload(cls, data, private=False):
        p, data = read_mpi(data)
        q, data = read_mpi(data)
        g, data = read_mpi(data)
        y, data = read_mpi(data)
        if private:
            x, data = read_mpi(data)
            return cls((y, g, p, q, x), private=True), data
        return cls((y, g, p, q), private=False), data

########NEW FILE########
__FILENAME__ = context
#    Copyright 2011-2012 Kjell Braden <afflux@pentabarf.de>
#
#    This file is part of the python-potr library.
#
#    python-potr is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    any later version.
#
#    python-potr is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this library.  If not, see <http://www.gnu.org/licenses/>.

# some python3 compatibilty
from __future__ import unicode_literals

try:
    type(basestring)
except NameError:
    # all strings are unicode in python3k
    basestring = str
    unicode = str

# callable is not available in python 3.0 and 3.1
try:
    type(callable)
except NameError:
    from collections import Callable
    def callable(x):
        return isinstance(x, Callable)


import base64
import logging
import struct

logger = logging.getLogger(__name__)

from potr import crypt
from potr import proto
from potr import compatcrypto

from time import time

EXC_UNREADABLE_MESSAGE = 1
EXC_FINISHED = 2

HEARTBEAT_INTERVAL = 60
STATE_PLAINTEXT = 0
STATE_ENCRYPTED = 1
STATE_FINISHED = 2
FRAGMENT_SEND_ALL = 0
FRAGMENT_SEND_ALL_BUT_FIRST = 1
FRAGMENT_SEND_ALL_BUT_LAST = 2

OFFER_NOTSENT = 0
OFFER_SENT = 1
OFFER_REJECTED = 2
OFFER_ACCEPTED = 3

class Context(object):
    def __init__(self, account, peername):
        self.user = account
        self.peer = peername
        self.policy = {}
        self.crypto = crypt.CryptEngine(self)
        self.tagOffer = OFFER_NOTSENT
        self.mayRetransmit = 0
        self.lastSend = 0
        self.lastMessage = None
        self.state = STATE_PLAINTEXT
        self.trustName = self.peer

        self.fragmentInfo = None
        self.fragment = None
        self.discardFragment()

    def getPolicy(self, key):
        raise NotImplementedError

    def inject(self, msg, appdata=None):
        raise NotImplementedError

    def policyOtrEnabled(self):
        return self.getPolicy('ALLOW_V2') or self.getPolicy('ALLOW_V1')

    def discardFragment(self):
        self.fragmentInfo = (0, 0)
        self.fragment = []

    def fragmentAccumulate(self, message):
        '''Accumulate a fragmented message. Returns None if the fragment is
        to be ignored, returns a string if the message is ready for further
        processing'''

        params = message.split(b',')
        if len(params) < 5 or not params[1].isdigit() or not params[2].isdigit():
            logger.warning('invalid formed fragmented message: %r', params)
            self.discardFragment()
            return message


        K, N = self.fragmentInfo
        try:
            k = int(params[1])
            n = int(params[2])
        except ValueError:
            logger.warning('invalid formed fragmented message: %r', params)
            self.discardFragment()
            return message

        fragData = params[3]

        logger.debug(params)

        if n >= k == 1:
            # first fragment
            self.discardFragment()
            self.fragmentInfo = (k, n)
            self.fragment.append(fragData)
        elif N == n >= k > 1 and k == K+1:
            # accumulate
            self.fragmentInfo = (k, n)
            self.fragment.append(fragData)
        else:
            # bad, discard
            self.discardFragment()
            logger.warning('invalid fragmented message: %r', params)
            return message

        if n == k > 0:
            assembled = b''.join(self.fragment)
            self.discardFragment()
            return assembled

        return None

    def removeFingerprint(self, fingerprint):
        self.user.removeFingerprint(self.trustName, fingerprint)

    def setTrust(self, fingerprint, trustLevel):
        ''' sets the trust level for the given fingerprint.
        trust is usually:
            - the empty string for known but untrusted keys
            - 'verified' for manually verified keys
            - 'smp' for smp-style verified keys '''
        self.user.setTrust(self.trustName, fingerprint, trustLevel)

    def getTrust(self, fingerprint, default=None):
        return self.user.getTrust(self.trustName, fingerprint, default)

    def setCurrentTrust(self, trustLevel):
        self.setTrust(self.crypto.theirPubkey.cfingerprint(), trustLevel)

    def getCurrentKey(self):
        return self.crypto.theirPubkey

    def getCurrentTrust(self):
        ''' returns a 2-tuple: first element is the current fingerprint,
            second is:
            - None if the key is unknown yet
            - a non-empty string if the key is trusted
            - an empty string if the key is untrusted '''
        if self.crypto.theirPubkey is None:
            return None
        return self.getTrust(self.crypto.theirPubkey.cfingerprint(), None)

    def receiveMessage(self, messageData, appdata=None):
        IGN = None, []

        if not self.policyOtrEnabled():
            raise NotOTRMessage(messageData)

        message = self.parse(messageData)

        if message is None:
            # nothing to see. move along.
            return IGN

        logger.debug(repr(message))

        if self.getPolicy('SEND_TAG'):
            if isinstance(message, basestring):
                # received a plaintext message without tag
                # we should not tag anymore
                self.tagOffer = OFFER_REJECTED
            else:
                # got something OTR-ish, cool!
                self.tagOffer = OFFER_ACCEPTED

        if isinstance(message, proto.Query):
            self.handleQuery(message, appdata=appdata)

            if isinstance(message, proto.TaggedPlaintext):
                # it's actually a plaintext message
                if self.state != STATE_PLAINTEXT or \
                        self.getPolicy('REQUIRE_ENCRYPTION'):
                    # but we don't want plaintexts
                    raise UnencryptedMessage(message.msg)

                raise NotOTRMessage(message.msg)

            return IGN

        if isinstance(message, proto.AKEMessage):
            self.crypto.handleAKE(message, appdata=appdata)
            return IGN

        if isinstance(message, proto.DataMessage):
            ignore = message.flags & proto.MSGFLAGS_IGNORE_UNREADABLE

            if self.state != STATE_ENCRYPTED:
                self.sendInternal(proto.Error(
                        'You sent encrypted data, but I wasn\'t expecting it.'
                        ), appdata=appdata)
                if ignore:
                    return IGN
                raise NotEncryptedError(EXC_UNREADABLE_MESSAGE)

            try:
                plaintext, tlvs = self.crypto.handleDataMessage(message)
                self.processTLVs(tlvs, appdata=appdata)
                if plaintext and self.lastSend < time() - HEARTBEAT_INTERVAL:
                    self.sendInternal(b'', appdata=appdata)
                return plaintext or None, tlvs
            except crypt.InvalidParameterError:
                if ignore:
                    return IGN
                logger.exception('decryption failed')
                raise
        if isinstance(message, basestring):
            if self.state != STATE_PLAINTEXT or \
                    self.getPolicy('REQUIRE_ENCRYPTION'):
                raise UnencryptedMessage(message)

        if isinstance(message, proto.Error):
            raise ErrorReceived(message)

        raise NotOTRMessage(messageData)

    def sendInternal(self, msg, tlvs=[], appdata=None):
        self.sendMessage(FRAGMENT_SEND_ALL, msg, tlvs=tlvs, appdata=appdata,
                flags=proto.MSGFLAGS_IGNORE_UNREADABLE)

    def sendMessage(self, sendPolicy, msg, flags=0, tlvs=[], appdata=None):
        if self.policyOtrEnabled():
            self.lastSend = time()

            if isinstance(msg, proto.OTRMessage):
                # we want to send a protocol message (probably internal)
                # so we don't need further protocol encryption
                # also we can't add TLVs to arbitrary protocol messages
                if tlvs:
                    raise TypeError('can\'t add tlvs to protocol message')
            else:
                # we got plaintext to send. encrypt it
                msg = self.processOutgoingMessage(msg, flags, tlvs)

            if isinstance(msg, proto.OTRMessage) \
                    and not isinstance(msg, proto.Query):
                # if it's a query message, it must not get fragmented
                return self.sendFragmented(bytes(msg), policy=sendPolicy, appdata=appdata)
            else:
                msg = bytes(msg)
        return msg

    def processOutgoingMessage(self, msg, flags, tlvs=[]):
        isQuery = self.parseExplicitQuery(msg) is not None
        if isQuery:
            return self.user.getDefaultQueryMessage(self.getPolicy)

        if self.state == STATE_PLAINTEXT:
            if self.getPolicy('REQUIRE_ENCRYPTION'):
                if not isQuery:
                    self.lastMessage = msg
                    self.lastSend = time()
                    self.mayRetransmit = 2
                    # TODO notify
                    msg = self.user.getDefaultQueryMessage(self.getPolicy)
                return msg
            if self.getPolicy('SEND_TAG') and self.tagOffer != OFFER_REJECTED:
                self.tagOffer = OFFER_SENT
                versions = set()
                if self.getPolicy('ALLOW_V1'):
                    versions.add(1)
                if self.getPolicy('ALLOW_V2'):
                    versions.add(2)
                return proto.TaggedPlaintext(msg, versions)
            return msg
        if self.state == STATE_ENCRYPTED:
            msg = self.crypto.createDataMessage(msg, flags, tlvs)
            self.lastSend = time()
            return msg
        if self.state == STATE_FINISHED:
            raise NotEncryptedError(EXC_FINISHED)

    def disconnect(self, appdata=None):
        if self.state != STATE_FINISHED:
            self.sendInternal(b'', tlvs=[proto.DisconnectTLV()], appdata=appdata)
            self.setState(STATE_PLAINTEXT)
            self.crypto.finished()
        else:
            self.setState(STATE_PLAINTEXT)

    def setState(self, newstate):
        self.state = newstate

    def _wentEncrypted(self):
        self.setState(STATE_ENCRYPTED)

    def sendFragmented(self, msg, policy=FRAGMENT_SEND_ALL, appdata=None):
        mms = self.maxMessageSize(appdata)
        msgLen = len(msg)
        if mms != 0 and msgLen > mms:
            fms = mms - 19
            fragments = [ msg[i:i+fms] for i in range(0, msgLen, fms) ]

            fc = len(fragments)

            if fc > 65535:
                raise OverflowError('too many fragments')

            for fi in range(len(fragments)):
                ctr = unicode(fi+1) + ',' + unicode(fc) + ','
                fragments[fi] = b'?OTR,' + ctr.encode('ascii') \
                        + fragments[fi] + b','

            if policy == FRAGMENT_SEND_ALL:
                for f in fragments:
                    self.inject(f, appdata=appdata)
                return None
            elif policy == FRAGMENT_SEND_ALL_BUT_FIRST:
                for f in fragments[1:]:
                    self.inject(f, appdata=appdata)
                return fragments[0]
            elif policy == FRAGMENT_SEND_ALL_BUT_LAST:
                for f in fragments[:-1]:
                    self.inject(f, appdata=appdata)
                return fragments[-1]

        else:
            if policy == FRAGMENT_SEND_ALL:
                self.inject(msg, appdata=appdata)
                return None
            else:
                return msg

    def processTLVs(self, tlvs, appdata=None):
        for tlv in tlvs:
            if isinstance(tlv, proto.DisconnectTLV):
                logger.info('got disconnect tlv, forcing finished state')
                self.setState(STATE_FINISHED)
                self.crypto.finished()
                # TODO cleanup
                continue
            if isinstance(tlv, proto.SMPTLV):
                self.crypto.smpHandle(tlv, appdata=appdata)
                continue
            logger.info('got unhandled tlv: {0!r}'.format(tlv))

    def smpAbort(self, appdata=None):
        if self.state != STATE_ENCRYPTED:
            raise NotEncryptedError
        self.crypto.smpAbort(appdata=appdata)

    def smpIsValid(self):
        return self.crypto.smp and self.crypto.smp.prog != crypt.SMPPROG_CHEATED

    def smpIsSuccess(self):
        return self.crypto.smp.prog == crypt.SMPPROG_SUCCEEDED \
                if self.crypto.smp else None

    def smpGotSecret(self, secret, question=None, appdata=None):
        if self.state != STATE_ENCRYPTED:
            raise NotEncryptedError
        self.crypto.smpSecret(secret, question=question, appdata=appdata)

    def smpInit(self, secret, question=None, appdata=None):
        if self.state != STATE_ENCRYPTED:
            raise NotEncryptedError
        self.crypto.smp = None
        self.crypto.smpSecret(secret, question=question, appdata=appdata)

    def handleQuery(self, message, appdata=None):
        if 2 in message.versions and self.getPolicy('ALLOW_V2'):
            self.authStartV2(appdata=appdata)
        elif 1 in message.versions and self.getPolicy('ALLOW_V1'):
            self.authStartV1(appdata=appdata)

    def authStartV1(self, appdata=None):
        raise NotImplementedError()

    def authStartV2(self, appdata=None):
        self.crypto.startAKE(appdata=appdata)

    def parseExplicitQuery(self, message):
        otrTagPos = message.find(proto.OTRTAG)

        if otrTagPos == -1:
            return None

        indexBase = otrTagPos + len(proto.OTRTAG)

        if len(message) <= indexBase:
            return None

        compare = message[indexBase]

        hasq = compare == b'?'[0]
        hasv = compare == b'v'[0]

        if not hasq and not hasv:
            return None

        hasv |= len(message) > indexBase+1 and message[indexBase+1] == b'v'[0]
        if hasv:
            end = message.find(b'?', indexBase+1)
        else:
            end = indexBase+1
        return message[indexBase:end]

    def parse(self, message, nofragment=False):
        otrTagPos = message.find(proto.OTRTAG)
        if otrTagPos == -1:
            if proto.MESSAGE_TAG_BASE in message:
                return proto.TaggedPlaintext.parse(message)
            else:
                return message

        indexBase = otrTagPos + len(proto.OTRTAG)

        if len(message) <= indexBase:
            return message

        compare = message[indexBase]

        if nofragment is False and compare == b','[0]:
            message = self.fragmentAccumulate(message[indexBase:])
            if message is None:
                return None
            else:
                return self.parse(message, nofragment=True)
        else:
            self.discardFragment()

        queryPayload = self.parseExplicitQuery(message)
        if queryPayload is not None:
            return proto.Query.parse(queryPayload)

        if compare == b':'[0] and len(message) > indexBase + 4:
            try:
                infoTag = base64.b64decode(message[indexBase+1:indexBase+5])
                classInfo = struct.unpack(b'!HB', infoTag)

                cls = proto.messageClasses.get(classInfo, None)
                if cls is None:
                    return message

                logger.debug('{user} got msg {typ!r}' \
                        .format(user=self.user.name, typ=cls))
                return cls.parsePayload(message[indexBase+5:])
            except (TypeError, struct.error):
                logger.exception('could not parse OTR message %s', message)
                return message

        if message[indexBase:indexBase+7] == b' Error:':
            return proto.Error(message[indexBase+7:])

        return message

    def maxMessageSize(self, appdata=None):
        """Return the max message size for this context."""
        return self.user.maxMessageSize

    def getExtraKey(self, extraKeyAppId=None, extraKeyAppData=None, appdata=None):
        """ retrieves the generated extra symmetric key.

        if extraKeyAppId is set, notifies the chat partner about intended
        usage (additional application specific information can be supplied in
        extraKeyAppData).

        returns the 256 bit symmetric key """

        if self.state != STATE_ENCRYPTED:
            raise NotEncryptedError
        if extraKeyAppId is not None:
            tlvs = [proto.ExtraKeyTLV(extraKeyAppId, extraKeyAppData)]
            self.sendInternal(b'', tlvs=tlvs, appdata=appdata)
        return self.crypto.extraKey

class Account(object):
    contextclass = Context
    def __init__(self, name, protocol, maxMessageSize, privkey=None):
        self.name = name
        self.privkey = privkey
        self.policy = {}
        self.protocol = protocol
        self.ctxs = {}
        self.trusts = {}
        self.maxMessageSize = maxMessageSize
        self.defaultQuery = '?OTRv{versions}?\nI would like to start ' \
                'an Off-the-Record private conversation. However, you ' \
                'do not have a plugin to support that.\nSee '\
                'https://otr.cypherpunks.ca/ for more information.'

    def __repr__(self):
        return '<{cls}(name={name!r})>'.format(cls=self.__class__.__name__,
                name=self.name)

    def getPrivkey(self, autogen=True):
        if self.privkey is None:
            self.privkey = self.loadPrivkey()
        if self.privkey is None:
            if autogen is True:
                self.privkey = compatcrypto.generateDefaultKey()
                self.savePrivkey()
            else:
                raise LookupError
        return self.privkey

    def loadPrivkey(self):
        raise NotImplementedError

    def savePrivkey(self):
        raise NotImplementedError

    def saveTrusts(self):
        raise NotImplementedError

    def getContext(self, uid, newCtxCb=None):
        if uid not in self.ctxs:
            self.ctxs[uid] = self.contextclass(self, uid)
            if callable(newCtxCb):
                newCtxCb(self.ctxs[uid])
        return self.ctxs[uid]

    def getDefaultQueryMessage(self, policy):
        v  = '2' if policy('ALLOW_V2') else ''
        msg = self.defaultQuery.format(versions=v)
        return msg.encode('ascii')

    def setTrust(self, key, fingerprint, trustLevel):
        if key not in self.trusts:
            self.trusts[key] = {}
        self.trusts[key][fingerprint] = trustLevel
        self.saveTrusts()

    def getTrust(self, key, fingerprint, default=None):
        if key not in self.trusts:
            return default
        return self.trusts[key].get(fingerprint, default)

    def removeFingerprint(self, key, fingerprint):
        if key in self.trusts and fingerprint in self.trusts[key]:
            del self.trusts[key][fingerprint]

class NotEncryptedError(RuntimeError):
    pass
class UnencryptedMessage(RuntimeError):
    pass
class ErrorReceived(RuntimeError):
    pass
class NotOTRMessage(RuntimeError):
    pass

########NEW FILE########
__FILENAME__ = crypt
#    Copyright 2011-2012 Kjell Braden <afflux@pentabarf.de>
#
#    This file is part of the python-potr library.
#
#    python-potr is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    any later version.
#
#    python-potr is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this library.  If not, see <http://www.gnu.org/licenses/>.

# some python3 compatibilty
from __future__ import unicode_literals

import logging
import struct


from potr.compatcrypto import SHA256, SHA1, SHA1HMAC, SHA256HMAC, \
        SHA256HMAC160, Counter, AESCTR, PK, random
from potr.utils import bytes_to_long, long_to_bytes, pack_mpi, read_mpi
from potr import proto

logger = logging.getLogger(__name__)

STATE_NONE = 0
STATE_AWAITING_DHKEY = 1
STATE_AWAITING_REVEALSIG = 2
STATE_AWAITING_SIG = 4
STATE_V1_SETUP = 5


DH_MODULUS = 2410312426921032588552076022197566074856950548502459942654116941958108831682612228890093858261341614673227141477904012196503648957050582631942730706805009223062734745341073406696246014589361659774041027169249453200378729434170325843778659198143763193776859869524088940195577346119843545301547043747207749969763750084308926339295559968882457872412993810129130294592999947926365264059284647209730384947211681434464714438488520940127459844288859336526896320919633919
DH_MODULUS_2 = DH_MODULUS-2
DH_GENERATOR = 2
DH_BITS = 1536
DH_MAX = 2**DH_BITS
SM_ORDER = (DH_MODULUS - 1) // 2

def check_group(n):
    return 2 <= n <= DH_MODULUS_2
def check_exp(n):
    return 1 <= n < SM_ORDER

class DH(object):
    @classmethod
    def set_params(cls, prime, gen):
        cls.prime = prime
        cls.gen = gen

    def __init__(self):
        self.priv = random.randrange(2, 2**320)
        self.pub = pow(self.gen, self.priv, self.prime)

DH.set_params(DH_MODULUS, DH_GENERATOR)

class DHSession(object):
    def __init__(self, sendenc, sendmac, rcvenc, rcvmac):
        self.sendenc = sendenc
        self.sendmac = sendmac
        self.rcvenc = rcvenc
        self.rcvmac = rcvmac
        self.sendctr = Counter(0)
        self.rcvctr = Counter(0)
        self.sendmacused = False
        self.rcvmacused = False

    def __repr__(self):
        return '<{cls}(send={s!r},rcv={r!r})>' \
                .format(cls=self.__class__.__name__,
                        s=self.sendmac, r=self.rcvmac)

    @classmethod
    def create(cls, dh, y):
        s = pow(y, dh.priv, DH_MODULUS)
        sb = pack_mpi(s)

        if dh.pub > y:
            sendbyte = b'\1'
            rcvbyte = b'\2'
        else:
            sendbyte = b'\2'
            rcvbyte = b'\1'

        sendenc = SHA1(sendbyte + sb)[:16]
        sendmac = SHA1(sendenc)
        rcvenc = SHA1(rcvbyte + sb)[:16]
        rcvmac = SHA1(rcvenc)
        return cls(sendenc, sendmac, rcvenc, rcvmac)

class CryptEngine(object):
    def __init__(self, ctx):
        self.ctx = ctx
        self.ake = None

        self.sessionId = None
        self.sessionIdHalf = False
        self.theirKeyid = 0
        self.theirY = None
        self.theirOldY = None

        self.ourOldDHKey = None
        self.ourDHKey = None
        self.ourKeyid = 0

        self.sessionkeys = {0:{0:None, 1:None}, 1:{0:None, 1:None}}
        self.theirPubkey = None
        self.savedMacKeys = []

        self.smp = None
        self.extraKey = None

    def revealMacs(self, ours=True):
        if ours:
            dhs = self.sessionkeys[1].values()
        else:
            dhs = ( v[1] for v in self.sessionkeys.values() )
        for v in dhs:
            if v is not None:
                if v.rcvmacused:
                    self.savedMacKeys.append(v.rcvmac)
                if v.sendmacused:
                    self.savedMacKeys.append(v.sendmac)

    def rotateDHKeys(self):
        self.revealMacs(ours=True)
        self.ourOldDHKey = self.ourDHKey
        self.sessionkeys[1] = self.sessionkeys[0].copy()
        self.ourDHKey = DH()
        self.ourKeyid += 1

        self.sessionkeys[0][0] = None if self.theirY is None else \
                DHSession.create(self.ourDHKey, self.theirY)
        self.sessionkeys[0][1] = None if self.theirOldY is None else \
                DHSession.create(self.ourDHKey, self.theirOldY)

        logger.debug('{0}: Refreshing ourkey to {1} {2}'.format(
                self.ctx.user.name, self.ourKeyid, self.sessionkeys))

    def rotateYKeys(self, new_y):
        self.theirOldY = self.theirY
        self.revealMacs(ours=False)
        self.sessionkeys[0][1] = self.sessionkeys[0][0]
        self.sessionkeys[1][1] = self.sessionkeys[1][0]
        self.theirY = new_y
        self.theirKeyid += 1

        self.sessionkeys[0][0] = DHSession.create(self.ourDHKey, self.theirY)
        self.sessionkeys[1][0] = DHSession.create(self.ourOldDHKey, self.theirY)

        logger.debug('{0}: Refreshing theirkey to {1} {2}'.format(
                self.ctx.user.name, self.theirKeyid, self.sessionkeys))

    def handleDataMessage(self, msg):
        if self.saneKeyIds(msg) is False:
            raise InvalidParameterError

        sesskey = self.sessionkeys[self.ourKeyid - msg.rkeyid] \
                [self.theirKeyid - msg.skeyid]

        logger.debug('sesskeys: {0!r}, our={1}, r={2}, their={3}, s={4}' \
                .format(self.sessionkeys, self.ourKeyid, msg.rkeyid,
                        self.theirKeyid, msg.skeyid))

        if msg.mac != SHA1HMAC(sesskey.rcvmac, msg.getMacedData()):
            logger.error('HMACs don\'t match')
            raise InvalidParameterError
        sesskey.rcvmacused = True

        newCtrPrefix = bytes_to_long(msg.ctr)
        if newCtrPrefix <= sesskey.rcvctr.prefix:
            logger.error('CTR must increase (old %r, new %r)',
                    sesskey.rcvctr.prefix, newCtrPrefix)
            raise InvalidParameterError

        sesskey.rcvctr.prefix = newCtrPrefix

        logger.debug('handle: enc={0!r} mac={1!r} ctr={2!r}' \
                .format(sesskey.rcvenc, sesskey.rcvmac, sesskey.rcvctr))

        plaintextData = AESCTR(sesskey.rcvenc, sesskey.rcvctr) \
                .decrypt(msg.encmsg)

        if b'\0' in plaintextData:
            plaintext, tlvData = plaintextData.split(b'\0', 1)
            tlvs = proto.TLV.parse(tlvData)
        else:
            plaintext = plaintextData
            tlvs = []

        if msg.rkeyid == self.ourKeyid:
            self.rotateDHKeys()
        if msg.skeyid == self.theirKeyid:
            self.rotateYKeys(bytes_to_long(msg.dhy))

        return plaintext, tlvs

    def smpSecret(self, secret, question=None, appdata=None):
        if self.smp is None:
            logger.debug('Creating SMPHandler')
            self.smp = SMPHandler(self)

        self.smp.gotSecret(secret, question=question, appdata=appdata)

    def smpHandle(self, tlv, appdata=None):
        if self.smp is None:
            logger.debug('Creating SMPHandler')
            self.smp = SMPHandler(self)
        self.smp.handle(tlv, appdata=appdata)

    def smpAbort(self, appdata=None):
        if self.smp is None:
            logger.debug('Creating SMPHandler')
            self.smp = SMPHandler(self)
        self.smp.abort(appdata=appdata)

    def createDataMessage(self, message, flags=0, tlvs=None):
        # check MSGSTATE
        if self.theirKeyid == 0:
            raise InvalidParameterError

        if tlvs is None:
            tlvs = []

        sess = self.sessionkeys[1][0]
        sess.sendctr.inc()

        logger.debug('create: enc={0!r} mac={1!r} ctr={2!r}' \
                .format(sess.sendenc, sess.sendmac, sess.sendctr))

        # plaintext + TLVS
        plainBuf = message + b'\0' + b''.join([ bytes(t) for t in tlvs])
        encmsg = AESCTR(sess.sendenc, sess.sendctr).encrypt(plainBuf)

        msg = proto.DataMessage(flags, self.ourKeyid-1, self.theirKeyid,
                long_to_bytes(self.ourDHKey.pub), sess.sendctr.byteprefix(),
                encmsg, b'', b''.join(self.savedMacKeys))

        self.savedMacKeys = []

        msg.mac = SHA1HMAC(sess.sendmac, msg.getMacedData())
        return msg

    def saneKeyIds(self, msg):
        anyzero = self.theirKeyid == 0 or msg.skeyid == 0 or msg.rkeyid == 0
        if anyzero or (msg.skeyid != self.theirKeyid and \
                msg.skeyid != self.theirKeyid - 1) or \
                (msg.rkeyid != self.ourKeyid and msg.rkeyid != self.ourKeyid - 1):
            return False
        if self.theirOldY is None and msg.skeyid == self.theirKeyid - 1:
            return False
        return True

    def startAKE(self, appdata=None):
        self.ake = AuthKeyExchange(self.ctx.user.getPrivkey(), self.goEncrypted)
        outMsg = self.ake.startAKE()
        self.ctx.sendInternal(outMsg, appdata=appdata)

    def handleAKE(self, inMsg, appdata=None):
        outMsg = None

        if not self.ctx.getPolicy('ALLOW_V2'):
            return

        if isinstance(inMsg, proto.DHCommit):
            if self.ake is None or self.ake.state != STATE_AWAITING_REVEALSIG:
                self.ake = AuthKeyExchange(self.ctx.user.getPrivkey(),
                        self.goEncrypted)
            outMsg = self.ake.handleDHCommit(inMsg)

        elif isinstance(inMsg, proto.DHKey):
            if self.ake is None:
                return # ignore
            outMsg = self.ake.handleDHKey(inMsg)

        elif isinstance(inMsg, proto.RevealSig):
            if self.ake is None:
                return # ignore
            outMsg = self.ake.handleRevealSig(inMsg)

        elif isinstance(inMsg, proto.Signature):
            if self.ake is None:
                return # ignore
            self.ake.handleSignature(inMsg)

        if outMsg is not None:
            self.ctx.sendInternal(outMsg, appdata=appdata)

    def goEncrypted(self, ake):
        if ake.dh.pub == ake.gy:
            logger.warning('We are receiving our own messages')
            raise InvalidParameterError

        # TODO handle new fingerprint
        self.theirPubkey = ake.theirPubkey

        self.sessionId = ake.sessionId
        self.sessionIdHalf = ake.sessionIdHalf
        self.theirKeyid = ake.theirKeyid
        self.ourKeyid = ake.ourKeyid
        self.theirY = ake.gy
        self.theirOldY = None
        self.extraKey = ake.extraKey

        if self.ourKeyid != ake.ourKeyid + 1 or self.ourOldDHKey != ake.dh.pub:
            self.ourDHKey = ake.dh
            self.sessionkeys[0][0] = DHSession.create(self.ourDHKey, self.theirY)
            self.rotateDHKeys()

        # we don't need the AKE anymore, free the reference
        self.ake = None

        self.ctx._wentEncrypted()
        logger.info('went encrypted with {0}'.format(self.theirPubkey))

    def finished(self):
        self.smp = None

class AuthKeyExchange(object):
    def __init__(self, privkey, onSuccess):
        self.privkey = privkey
        self.state = STATE_NONE
        self.r = None
        self.encgx = None
        self.hashgx = None
        self.ourKeyid = 1
        self.theirPubkey = None
        self.theirKeyid = 1
        self.enc_c = None
        self.enc_cp = None
        self.mac_m1 = None
        self.mac_m1p = None
        self.mac_m2 = None
        self.mac_m2p = None
        self.sessionId = None
        self.sessionIdHalf = False
        self.dh = DH()
        self.onSuccess = onSuccess
        self.gy = None
        self.extraKey = None
        self.lastmsg = None

    def startAKE(self):
        self.r = long_to_bytes(random.getrandbits(128), 16)

        gxmpi = pack_mpi(self.dh.pub)

        self.hashgx = SHA256(gxmpi)
        self.encgx = AESCTR(self.r).encrypt(gxmpi)

        self.state = STATE_AWAITING_DHKEY

        return proto.DHCommit(self.encgx, self.hashgx)

    def handleDHCommit(self, msg):
        self.encgx = msg.encgx
        self.hashgx = msg.hashgx

        self.state = STATE_AWAITING_REVEALSIG
        return proto.DHKey(long_to_bytes(self.dh.pub))

    def handleDHKey(self, msg):
        if self.state == STATE_AWAITING_DHKEY:
            self.gy = bytes_to_long(msg.gy)

            # check 2 <= g**y <= p-2
            if not check_group(self.gy):
                logger.error('Invalid g**y received: %r', self.gy)
                return

            self.createAuthKeys()

            aesxb = self.calculatePubkeyAuth(self.enc_c, self.mac_m1)

            self.state = STATE_AWAITING_SIG

            self.lastmsg = proto.RevealSig(self.r, aesxb, b'')
            self.lastmsg.mac = SHA256HMAC160(self.mac_m2,
                    self.lastmsg.getMacedData())
            return self.lastmsg

        elif self.state == STATE_AWAITING_SIG:
            logger.info('received DHKey while not awaiting DHKEY')
            if msg.gy == self.gy:
                logger.info('resending revealsig')
                return self.lastmsg
        else:
            logger.info('bad state for DHKey')

    def handleRevealSig(self, msg):
        if self.state != STATE_AWAITING_REVEALSIG:
            logger.error('bad state for RevealSig')
            raise InvalidParameterError

        self.r = msg.rkey
        gxmpi = AESCTR(self.r).decrypt(self.encgx)
        if SHA256(gxmpi) != self.hashgx:
            logger.error('Hashes don\'t match')
            logger.info('r=%r, hashgx=%r, computed hash=%r, gxmpi=%r',
                    self.r, self.hashgx, SHA256(gxmpi), gxmpi)
            raise InvalidParameterError

        self.gy = read_mpi(gxmpi)[0]
        self.createAuthKeys()

        if msg.mac != SHA256HMAC160(self.mac_m2, msg.getMacedData()):
            logger.error('HMACs don\'t match')
            logger.info('mac=%r, mac_m2=%r, data=%r', msg.mac, self.mac_m2,
                    msg.getMacedData())
            raise InvalidParameterError

        self.checkPubkeyAuth(self.enc_c, self.mac_m1, msg.encsig)

        aesxb = self.calculatePubkeyAuth(self.enc_cp, self.mac_m1p)
        self.sessionIdHalf = True

        self.onSuccess(self)

        self.ourKeyid = 0
        self.state = STATE_NONE

        cmpmac = struct.pack(b'!I', len(aesxb)) + aesxb

        return proto.Signature(aesxb, SHA256HMAC160(self.mac_m2p, cmpmac))

    def handleSignature(self, msg):
        if self.state != STATE_AWAITING_SIG:
            logger.error('bad state (%d) for Signature', self.state)
            raise InvalidParameterError

        if msg.mac != SHA256HMAC160(self.mac_m2p, msg.getMacedData()):
            logger.error('HMACs don\'t match')
            raise InvalidParameterError

        self.checkPubkeyAuth(self.enc_cp, self.mac_m1p, msg.encsig)

        self.sessionIdHalf = False

        self.onSuccess(self)

        self.ourKeyid = 0
        self.state = STATE_NONE

    def createAuthKeys(self):
        s = pow(self.gy, self.dh.priv, DH_MODULUS)
        sbyte = pack_mpi(s)
        self.sessionId = SHA256(b'\x00' + sbyte)[:8]
        enc = SHA256(b'\x01' + sbyte)
        self.enc_c = enc[:16]
        self.enc_cp = enc[16:]
        self.mac_m1 = SHA256(b'\x02' + sbyte)
        self.mac_m2 = SHA256(b'\x03' + sbyte)
        self.mac_m1p = SHA256(b'\x04' + sbyte)
        self.mac_m2p = SHA256(b'\x05' + sbyte)
        self.extraKey = SHA256(b'\xff' + sbyte)

    def calculatePubkeyAuth(self, key, mackey):
        pubkey = self.privkey.serializePublicKey()
        buf = pack_mpi(self.dh.pub)
        buf += pack_mpi(self.gy)
        buf += pubkey
        buf += struct.pack(b'!I', self.ourKeyid)
        MB = self.privkey.sign(SHA256HMAC(mackey, buf))

        buf = pubkey
        buf += struct.pack(b'!I', self.ourKeyid)
        buf += MB
        return AESCTR(key).encrypt(buf)

    def checkPubkeyAuth(self, key, mackey, encsig):
        auth = AESCTR(key).decrypt(encsig)
        self.theirPubkey, auth = PK.parsePublicKey(auth)

        receivedKeyid, auth = proto.unpack(b'!I', auth)
        if receivedKeyid == 0:
            raise InvalidParameterError

        authbuf = pack_mpi(self.gy)
        authbuf += pack_mpi(self.dh.pub)
        authbuf += self.theirPubkey.serializePublicKey()
        authbuf += struct.pack(b'!I', receivedKeyid)

        if self.theirPubkey.verify(SHA256HMAC(mackey, authbuf), auth) is False:
            raise InvalidParameterError
        self.theirKeyid = receivedKeyid

SMPPROG_OK = 0
SMPPROG_CHEATED = -2
SMPPROG_FAILED = -1
SMPPROG_SUCCEEDED = 1

class SMPHandler:
    def __init__(self, crypto):
        self.crypto = crypto
        self.state = 1
        self.g1 = DH_GENERATOR
        self.g2 = None
        self.g3 = None
        self.g3o = None
        self.x2 = None
        self.x3 = None
        self.prog = SMPPROG_OK
        self.pab = None
        self.qab = None
        self.questionReceived = False
        self.secret = None
        self.p = None
        self.q = None

    def abort(self, appdata=None):
        self.state = 1
        self.sendTLV(proto.SMPABORTTLV(), appdata=appdata)

    def sendTLV(self, tlv, appdata=None):
        self.crypto.ctx.sendInternal(b'', tlvs=[tlv], appdata=appdata)

    def handle(self, tlv, appdata=None):
        logger.debug('handling TLV {0.__class__.__name__}'.format(tlv))
        self.prog = SMPPROG_CHEATED
        if isinstance(tlv, proto.SMPABORTTLV):
            self.state = 1
            return
        is1qTlv = isinstance(tlv, proto.SMP1QTLV)
        if isinstance(tlv, proto.SMP1TLV) or is1qTlv:
            if self.state != 1:
                self.abort(appdata=appdata)
                return

            msg = tlv.mpis

            if not check_group(msg[0]) or not check_group(msg[3]) \
                    or not check_exp(msg[2]) or not check_exp(msg[5]) \
                    or not check_known_log(msg[1], msg[2], self.g1, msg[0], 1) \
                    or not check_known_log(msg[4], msg[5], self.g1, msg[3], 2):
                logger.error('invalid SMP1TLV received')
                self.abort(appdata=appdata)
                return

            self.questionReceived = is1qTlv

            self.g3o = msg[3]

            self.x2 = random.randrange(2, DH_MAX)
            self.x3 = random.randrange(2, DH_MAX)

            self.g2 = pow(msg[0], self.x2, DH_MODULUS)
            self.g3 = pow(msg[3], self.x3, DH_MODULUS)

            self.prog = SMPPROG_OK
            self.state = 0
            return
        if isinstance(tlv, proto.SMP2TLV):
            if self.state != 2:
                self.abort(appdata=appdata)
                return

            msg = tlv.mpis
            mp = msg[6]
            mq = msg[7]

            if not check_group(msg[0]) or not check_group(msg[3]) \
                    or not check_group(msg[6]) or not check_group(msg[7]) \
                    or not check_exp(msg[2]) or not check_exp(msg[5]) \
                    or not check_exp(msg[9]) or not check_exp(msg[10]) \
                    or not check_known_log(msg[1], msg[2], self.g1, msg[0], 3) \
                    or not check_known_log(msg[4], msg[5], self.g1, msg[3], 4):
                logger.error('invalid SMP2TLV received')
                self.abort(appdata=appdata)
                return

            self.g3o = msg[3]
            self.g2 = pow(msg[0], self.x2, DH_MODULUS)
            self.g3 = pow(msg[3], self.x3, DH_MODULUS)

            if not self.check_equal_coords(msg[6:11], 5):
                logger.error('invalid SMP2TLV received')
                self.abort(appdata=appdata)
                return

            r = random.randrange(2, DH_MAX)
            self.p = pow(self.g3, r, DH_MODULUS)
            msg = [self.p]
            qa1 = pow(self.g1, r, DH_MODULUS)
            qa2 = pow(self.g2, self.secret, DH_MODULUS)
            self.q = qa1*qa2 % DH_MODULUS
            msg.append(self.q)
            msg += self.proof_equal_coords(r, 6)

            inv = invMod(mp)
            self.pab = self.p * inv % DH_MODULUS
            inv = invMod(mq)
            self.qab = self.q * inv % DH_MODULUS

            msg.append(pow(self.qab, self.x3, DH_MODULUS))
            msg += self.proof_equal_logs(7)

            self.state = 4
            self.prog = SMPPROG_OK
            self.sendTLV(proto.SMP3TLV(msg), appdata=appdata)
            return
        if isinstance(tlv, proto.SMP3TLV):
            if self.state != 3:
                self.abort(appdata=appdata)
                return

            msg = tlv.mpis

            if not check_group(msg[0]) or not check_group(msg[1]) \
                    or not check_group(msg[5]) or not check_exp(msg[3]) \
                    or not check_exp(msg[4]) or not check_exp(msg[7]) \
                    or not self.check_equal_coords(msg[:5], 6):
                logger.error('invalid SMP3TLV received')
                self.abort(appdata=appdata)
                return

            inv = invMod(self.p)
            self.pab = msg[0] * inv % DH_MODULUS
            inv = invMod(self.q)
            self.qab = msg[1] * inv % DH_MODULUS

            if not self.check_equal_logs(msg[5:8], 7):
                logger.error('invalid SMP3TLV received')
                self.abort(appdata=appdata)
                return

            md = msg[5]
            msg = [pow(self.qab, self.x3, DH_MODULUS)]
            msg += self.proof_equal_logs(8)

            rab = pow(md, self.x3, DH_MODULUS)
            self.prog = SMPPROG_SUCCEEDED if self.pab == rab else SMPPROG_FAILED

            if self.prog != SMPPROG_SUCCEEDED:
                logger.error('secrets don\'t match')
                self.abort(appdata=appdata)
                self.crypto.ctx.setCurrentTrust('')
                return

            logger.info('secrets matched')
            if not self.questionReceived:
                self.crypto.ctx.setCurrentTrust('smp')
            self.state = 1
            self.sendTLV(proto.SMP4TLV(msg), appdata=appdata)
            return
        if isinstance(tlv, proto.SMP4TLV):
            if self.state != 4:
                self.abort(appdata=appdata)
                return

            msg = tlv.mpis

            if not check_group(msg[0]) or not check_exp(msg[2]) \
                    or not self.check_equal_logs(msg[:3], 8):
                logger.error('invalid SMP4TLV received')
                self.abort(appdata=appdata)
                return

            rab = pow(msg[0], self.x3, DH_MODULUS)

            self.prog = SMPPROG_SUCCEEDED if self.pab == rab else SMPPROG_FAILED

            if self.prog != SMPPROG_SUCCEEDED:
                logger.error('secrets don\'t match')
                self.abort(appdata=appdata)
                self.crypto.ctx.setCurrentTrust('')
                return

            logger.info('secrets matched')
            self.crypto.ctx.setCurrentTrust('smp')
            self.state = 1
            return

    def gotSecret(self, secret, question=None, appdata=None):
        ourFP = self.crypto.ctx.user.getPrivkey().fingerprint()
        if self.state == 1:
            # first secret -> SMP1TLV
            combSecret = SHA256(b'\1' + ourFP +
                    self.crypto.theirPubkey.fingerprint() +
                    self.crypto.sessionId + secret)

            self.secret = bytes_to_long(combSecret)

            self.x2 = random.randrange(2, DH_MAX)
            self.x3 = random.randrange(2, DH_MAX)

            msg = [pow(self.g1, self.x2, DH_MODULUS)]
            msg += proof_known_log(self.g1, self.x2, 1)
            msg.append(pow(self.g1, self.x3, DH_MODULUS))
            msg += proof_known_log(self.g1, self.x3, 2)

            self.prog = SMPPROG_OK
            self.state = 2
            if question is None:
                self.sendTLV(proto.SMP1TLV(msg), appdata=appdata)
            else:
                self.sendTLV(proto.SMP1QTLV(question, msg), appdata=appdata)
        if self.state == 0:
            # response secret -> SMP2TLV
            combSecret = SHA256(b'\1' + self.crypto.theirPubkey.fingerprint() +
                    ourFP + self.crypto.sessionId + secret)

            self.secret = bytes_to_long(combSecret)

            msg = [pow(self.g1, self.x2, DH_MODULUS)]
            msg += proof_known_log(self.g1, self.x2, 3)
            msg.append(pow(self.g1, self.x3, DH_MODULUS))
            msg += proof_known_log(self.g1, self.x3, 4)

            r = random.randrange(2, DH_MAX)

            self.p = pow(self.g3, r, DH_MODULUS)
            msg.append(self.p)

            qb1 = pow(self.g1, r, DH_MODULUS)
            qb2 = pow(self.g2, self.secret, DH_MODULUS)
            self.q = qb1 * qb2 % DH_MODULUS
            msg.append(self.q)

            msg += self.proof_equal_coords(r, 5)

            self.state = 3
            self.sendTLV(proto.SMP2TLV(msg), appdata=appdata)

    def proof_equal_coords(self, r, v):
        r1 = random.randrange(2, DH_MAX)
        r2 = random.randrange(2, DH_MAX)
        temp2 = pow(self.g1, r1, DH_MODULUS) \
                * pow(self.g2, r2, DH_MODULUS) % DH_MODULUS
        temp1 = pow(self.g3, r1, DH_MODULUS)

        cb = SHA256(struct.pack(b'B', v) + pack_mpi(temp1) + pack_mpi(temp2))
        c = bytes_to_long(cb)

        temp1 = r * c % SM_ORDER
        d1 = (r1-temp1) % SM_ORDER

        temp1 = self.secret * c % SM_ORDER
        d2 = (r2 - temp1) % SM_ORDER
        return c, d1, d2

    def check_equal_coords(self, coords, v):
        (p, q, c, d1, d2) = coords
        temp1 = pow(self.g3, d1, DH_MODULUS) * pow(p, c, DH_MODULUS) \
                % DH_MODULUS

        temp2 = pow(self.g1, d1, DH_MODULUS) \
                * pow(self.g2, d2, DH_MODULUS) \
                * pow(q, c, DH_MODULUS) % DH_MODULUS

        cprime = SHA256(struct.pack(b'B', v) + pack_mpi(temp1) + pack_mpi(temp2))

        return long_to_bytes(c, 32) == cprime

    def proof_equal_logs(self, v):
        r = random.randrange(2, DH_MAX)
        temp1 = pow(self.g1, r, DH_MODULUS)
        temp2 = pow(self.qab, r, DH_MODULUS)

        cb = SHA256(struct.pack(b'B', v) + pack_mpi(temp1) + pack_mpi(temp2))
        c = bytes_to_long(cb)
        temp1 = self.x3 * c % SM_ORDER
        d = (r - temp1) % SM_ORDER
        return c, d

    def check_equal_logs(self, logs, v):
        (r, c, d) = logs
        temp1 = pow(self.g1, d, DH_MODULUS) \
                * pow(self.g3o, c, DH_MODULUS) % DH_MODULUS

        temp2 = pow(self.qab, d, DH_MODULUS) \
                * pow(r, c, DH_MODULUS) % DH_MODULUS

        cprime = SHA256(struct.pack(b'B', v) + pack_mpi(temp1) + pack_mpi(temp2))
        return long_to_bytes(c, 32) == cprime

def proof_known_log(g, x, v):
    r = random.randrange(2, DH_MAX)
    c = bytes_to_long(SHA256(struct.pack(b'B', v) + pack_mpi(pow(g, r, DH_MODULUS))))
    temp = x * c % SM_ORDER
    return c, (r-temp) % SM_ORDER

def check_known_log(c, d, g, x, v):
    gd = pow(g, d, DH_MODULUS)
    xc = pow(x, c, DH_MODULUS)
    gdxc = gd * xc % DH_MODULUS
    return SHA256(struct.pack(b'B', v) + pack_mpi(gdxc)) == long_to_bytes(c, 32)

def invMod(n):
    return pow(n, DH_MODULUS_2, DH_MODULUS)

class InvalidParameterError(RuntimeError):
    pass

########NEW FILE########
__FILENAME__ = proto
#    Copyright 2011-2012 Kjell Braden <afflux@pentabarf.de>
#
#    This file is part of the python-potr library.
#
#    python-potr is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    any later version.
#
#    python-potr is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this library.  If not, see <http://www.gnu.org/licenses/>.

# some python3 compatibilty
from __future__ import unicode_literals

import base64
import struct
from potr.utils import pack_mpi, read_mpi, pack_data, read_data, unpack

OTRTAG = b'?OTR'
MESSAGE_TAG_BASE = b' \t  \t\t\t\t \t \t \t  '
MESSAGE_TAGS = {
        1:b' \t \t  \t ',
        2:b'  \t\t  \t ',
        3:b'  \t\t  \t\t',
    }

MSGTYPE_NOTOTR = 0
MSGTYPE_TAGGEDPLAINTEXT = 1
MSGTYPE_QUERY = 2
MSGTYPE_DH_COMMIT = 3
MSGTYPE_DH_KEY = 4
MSGTYPE_REVEALSIG = 5
MSGTYPE_SIGNATURE = 6
MSGTYPE_V1_KEYEXCH = 7
MSGTYPE_DATA = 8
MSGTYPE_ERROR = 9
MSGTYPE_UNKNOWN = -1

MSGFLAGS_IGNORE_UNREADABLE = 1

tlvClasses = {}
messageClasses = {}

hasByteStr = bytes == str
def bytesAndStrings(cls):
    if hasByteStr:
        cls.__str__ = lambda self: self.__bytes__()
    else:
        cls.__str__ = lambda self: str(self.__bytes__(), encoding='ascii')
    return cls

def registermessage(cls):
    if not hasattr(cls, 'parsePayload'):
        raise TypeError('registered message types need parsePayload()')
    messageClasses[cls.version, cls.msgtype] = cls
    return cls

def registertlv(cls):
    if not hasattr(cls, 'parsePayload'):
        raise TypeError('registered tlv types need parsePayload()')
    if cls.typ is None:
        raise TypeError('registered tlv type needs type ID')
    tlvClasses[cls.typ] = cls
    return cls


def getslots(cls, base):
    ''' helper to collect all the message slots from ancestors '''
    clss = [cls]
    
    for cls in clss:
        if cls == base:
            continue

        clss.extend(cls.__bases__)

        for slot in cls.__slots__:
            yield slot

@bytesAndStrings
class OTRMessage(object):
    __slots__ = ['payload']
    version = 0x0002
    msgtype = 0

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        for slot in getslots(self.__class__, OTRMessage):
            if getattr(self, slot) != getattr(other, slot):
                return False
        return True

    def __neq__(self, other):
        return not self.__eq__(other)

class Error(OTRMessage):
    __slots__ = ['error']
    def __init__(self, error):
        super(Error, self).__init__()
        self.error = error

    def __repr__(self):
        return '<proto.Error(%r)>' % self.error

    def __bytes__(self):
        return b'?OTR Error:' + self.error

class Query(OTRMessage):
    __slots__ = ['versions']
    def __init__(self, versions=set()):
        super(Query, self).__init__()
        self.versions = versions

    @classmethod
    def parse(cls, data):
        if not isinstance(data, bytes):
            raise TypeError('can only parse bytes')
        udata = data.decode('ascii', errors='replace')

        versions = set()
        if len(udata) > 0 and udata[0] == '?':
            udata = udata[1:]
            versions.add(1)

        if len(udata) > 0 and udata[0] == 'v':
            versions.update(( int(c) for c in udata if c.isdigit() ))
        return cls(versions)

    def __repr__(self):
        return '<proto.Query(versions=%r)>' % (self.versions)

    def __bytes__(self):
        d = b'?OTR'
        if 1 in self.versions:
            d += b'?'
        d += b'v'

        # in python3 there is only int->unicode conversion
        # so I convert to unicode and encode it to a byte string
        versions = [ '%d' % v for v in self.versions if v != 1 ]
        d += ''.join(versions).encode('ascii')

        d += b'?'
        return d

class TaggedPlaintext(Query):
    __slots__ = ['msg']
    def __init__(self, msg, versions):
        super(TaggedPlaintext, self).__init__(versions)
        self.msg = msg

    def __bytes__(self):
        data = self.msg + MESSAGE_TAG_BASE
        for v in self.versions:
            data += MESSAGE_TAGS[v]
        return data

    def __repr__(self):
        return '<proto.TaggedPlaintext(versions={versions!r},msg={msg!r})>' \
                .format(versions=self.versions, msg=self.msg)

    @classmethod
    def parse(cls, data):
        tagPos = data.find(MESSAGE_TAG_BASE)
        if tagPos < 0:
            raise TypeError(
                    'this is not a tagged plaintext ({0!r:.20})'.format(data))

        tags = [ data[i:i+8] for i in range(tagPos, len(data), 8) ]
        versions = set([ version for version, tag in MESSAGE_TAGS.items() if tag
            in tags ])

        return TaggedPlaintext(data[:tagPos], versions)

class GenericOTRMessage(OTRMessage):
    __slots__ = ['data']
    fields  = []

    def __init__(self, *args):
        super(GenericOTRMessage, self).__init__()
        if len(args) != len(self.fields):
            raise TypeError('%s needs %d arguments, got %d' %
                    (self.__class__.__name__, len(self.fields), len(args)))

        super(GenericOTRMessage, self).__setattr__('data',
                dict(zip((f[0] for f in self.fields), args)))

    def __getattr__(self, attr):
        if attr in self.data:
            return self.data[attr]
        raise AttributeError(
                "'{t!r}' object has no attribute '{attr!r}'".format(attr=attr,
                t=self.__class__.__name__))

    def __setattr__(self, attr, val):
        if attr in self.__slots__:
            super(GenericOTRMessage, self).__setattr__(attr, val)
        else:
            self.__getattr__(attr) # existence check
            self.data[attr] = val

    def __bytes__(self):
        data = struct.pack(b'!HB', self.version, self.msgtype) \
                + self.getPayload()
        return b'?OTR:' + base64.b64encode(data) + b'.'

    def __repr__(self):
        name = self.__class__.__name__
        data = ''
        for k, _ in self.fields:
            data += '%s=%r,' % (k, self.data[k])
        return '<proto.%s(%s)>' % (name, data)

    @classmethod
    def parsePayload(cls, data):
        data = base64.b64decode(data)
        args = []
        for _, ftype in cls.fields:
            if ftype == 'data':
                value, data = read_data(data)
            elif isinstance(ftype, bytes):
                value, data = unpack(ftype, data)
            elif isinstance(ftype, int):
                value, data = data[:ftype], data[ftype:]
            args.append(value)
        return cls(*args)

    def getPayload(self, *ffilter):
        payload = b''
        for k, ftype in self.fields:
            if k in ffilter:
                continue

            if ftype == 'data':
                payload += pack_data(self.data[k])
            elif isinstance(ftype, bytes):
                payload += struct.pack(ftype, self.data[k])
            else:
                payload += self.data[k]
        return payload

class AKEMessage(GenericOTRMessage):
    __slots__ = []

@registermessage
class DHCommit(AKEMessage):
    __slots__ = []
    msgtype = 0x02
    fields = [('encgx', 'data'), ('hashgx', 'data'), ]

@registermessage
class DHKey(AKEMessage):
    __slots__ = []
    msgtype = 0x0a
    fields = [('gy', 'data'), ]

@registermessage
class RevealSig(AKEMessage):
    __slots__ = []
    msgtype = 0x11
    fields = [('rkey', 'data'), ('encsig', 'data'), ('mac', 20),]

    def getMacedData(self):
        p = self.encsig
        return struct.pack(b'!I', len(p)) + p

@registermessage
class Signature(AKEMessage):
    __slots__ = []
    msgtype = 0x12
    fields = [('encsig', 'data'), ('mac', 20)]

    def getMacedData(self):
        p = self.encsig
        return struct.pack(b'!I', len(p)) + p

@registermessage
class DataMessage(GenericOTRMessage):
    __slots__ = []
    msgtype = 0x03
    fields = [('flags', b'!B'), ('skeyid', b'!I'), ('rkeyid', b'!I'),
            ('dhy', 'data'), ('ctr', 8), ('encmsg', 'data'), ('mac', 20),
            ('oldmacs', 'data'), ]

    def getMacedData(self):
        return struct.pack(b'!HB', self.version, self.msgtype) + \
                self.getPayload('mac', 'oldmacs')

@bytesAndStrings
class TLV(object):
    __slots__ = []
    typ = None

    def getPayload(self):
        raise NotImplementedError

    def __repr__(self):
        val = self.getPayload()
        return '<{cls}(typ={t},len={l},val={v!r})>'.format(t=self.typ,
                l=len(val), v=val, cls=self.__class__.__name__)

    def __bytes__(self):
        val = self.getPayload()
        return struct.pack(b'!HH', self.typ, len(val)) + val

    @classmethod
    def parse(cls, data):
        if not data:
            return []
        typ, length, data = unpack(b'!HH', data)
        return [tlvClasses[typ].parsePayload(data[:length])] \
                + cls.parse(data[length:])

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        for slot in getslots(self.__class__, TLV):
            if getattr(self, slot) != getattr(other, slot):
                return False
        return True

    def __neq__(self, other):
        return not self.__eq__(other)

@registertlv
class PaddingTLV(TLV):
    typ = 0

    __slots__ = ['padding']

    def __init__(self, padding):
        super(PaddingTLV, self).__init__()
        self.padding = padding

    def getPayload(self):
        return self.padding

    @classmethod
    def parsePayload(cls, data):
        return cls(data)

@registertlv
class DisconnectTLV(TLV):
    typ = 1
    def __init__(self):
        super(DisconnectTLV, self).__init__()

    def getPayload(self):
        return b''

    @classmethod
    def parsePayload(cls, data):
        if len(data) >  0:
            raise TypeError('DisconnectTLV must not contain data. got {0!r}'
                    .format(data))
        return cls()

class SMPTLV(TLV):
    __slots__ = ['mpis']
    dlen = None

    def __init__(self, mpis=None):
        super(SMPTLV, self).__init__()
        if mpis is None:
            mpis = []
        if self.dlen is None:
            raise TypeError('no amount of mpis specified in dlen')
        if len(mpis) != self.dlen:
            raise TypeError('expected {0} mpis, got {1}'
                    .format(self.dlen, len(mpis)))
        self.mpis = mpis

    def getPayload(self):
        d = struct.pack(b'!I', len(self.mpis))
        for n in self.mpis:
            d += pack_mpi(n)
        return d

    @classmethod
    def parsePayload(cls, data):
        mpis = []
        if cls.dlen > 0:
            count, data = unpack(b'!I', data)
            for _ in range(count):
                n, data = read_mpi(data)
                mpis.append(n)
        if len(data) > 0:
            raise TypeError('too much data for {0} mpis'.format(cls.dlen))
        return cls(mpis)

@registertlv
class SMP1TLV(SMPTLV):
    typ = 2
    dlen = 6

@registertlv
class SMP1QTLV(SMPTLV):
    typ = 7
    dlen = 6
    __slots__ = ['msg']

    def __init__(self, msg, mpis):
        self.msg = msg
        super(SMP1QTLV, self).__init__(mpis)

    def getPayload(self):
        return self.msg + b'\0' + super(SMP1QTLV, self).getPayload()

    @classmethod
    def parsePayload(cls, data):
        msg, data = data.split(b'\0', 1)
        mpis = SMP1TLV.parsePayload(data).mpis
        return cls(msg, mpis)

@registertlv
class SMP2TLV(SMPTLV):
    typ = 3
    dlen = 11

@registertlv
class SMP3TLV(SMPTLV):
    typ = 4
    dlen = 8

@registertlv
class SMP4TLV(SMPTLV):
    typ = 5
    dlen = 3

@registertlv
class SMPABORTTLV(SMPTLV):
    typ = 6
    dlen = 0

    def getPayload(self):
        return b''

@registertlv
class ExtraKeyTLV(TLV):
    typ = 8

    __slots__ = ['appid', 'appdata']

    def __init__(self, appid, appdata):
        super(ExtraKeyTLV, self).__init__()
        self.appid = appid
        self.appdata = appdata
        if appdata is None:
            self.appdata = b''

    def getPayload(self):
        return self.appid + self.appdata

    @classmethod
    def parsePayload(cls, data):
        return cls(data[:4], data[4:])

########NEW FILE########
__FILENAME__ = utils
#    Copyright 2012 Kjell Braden <afflux@pentabarf.de>
#
#    This file is part of the python-potr library.
#
#    python-potr is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    any later version.
#
#    python-potr is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this library.  If not, see <http://www.gnu.org/licenses/>.

# some python3 compatibilty
from __future__ import unicode_literals


import struct

def pack_mpi(n):
    return pack_data(long_to_bytes(n))
def read_mpi(data):
    n, data = read_data(data)
    return bytes_to_long(n), data
def pack_data(data):
    return struct.pack(b'!I', len(data)) + data
def read_data(data):
    datalen, data = unpack(b'!I', data)
    return data[:datalen], data[datalen:]
def unpack(fmt, buf):
    s = struct.Struct(fmt)
    return s.unpack(buf[:s.size]) + (buf[s.size:],)


def bytes_to_long(b):
    l = len(b)
    s = 0
    for i in range(l):
        s += byte_to_long(b[i:i+1]) << 8*(l-i-1)
    return s

def long_to_bytes(l, n=0):
    b = b''
    while l != 0 or n > 0:
        b = long_to_byte(l & 0xff) + b
        l >>= 8
        n -= 1
    return b

def byte_to_long(b):
    return struct.unpack(b'B', b)[0]
def long_to_byte(l):
    return struct.pack(b'B', l)

def human_hash(fp):
    fp = fp.upper()
    fplen = len(fp)
    wordsize = fplen//5
    buf = ''
    for w in range(0, fplen, wordsize):
        buf += '{0} '.format(fp[w:w+wordsize])
    return buf.rstrip()

########NEW FILE########
__FILENAME__ = convertkey
#!/usr/bin/python
#    Copyright 2011 Kjell Braden <afflux@pentabarf.de>
#
#    This file is part of the python-potr library.
#
#    python-potr is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    any later version.
#
#    python-potr is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this library.  If not, see <http://www.gnu.org/licenses/>.

from potr.compatcrypto.pycrypto import DSAKey

def parse(tokens):
    key = tokens.pop(0)[1:]

    parsed = {key:{}}

    while tokens:
        token = tokens.pop(0)
        if token.endswith(')'):
            if token[:-1]:
                val = token[:-1].strip('"')
                if val.startswith('#') and val.endswith('#'):
                    val = int(val[1:-1], 16)
                parsed[key] = val
            return parsed, tokens
        if token.startswith('('):
            pdata, tokens = parse([token]+tokens)
            parsed[key].update(pdata)

    return parsed, []

def convert(path):
    with open(path, 'r') as f:
        text = f.read().strip()
    tokens = text.split()
    oldkey = parse(tokens)[0]['privkeys']['account']

    k = oldkey['private-key']['dsa']
    newkey = DSAKey((k['y'],k['g'],k['p'],k['q'],k['x']), private=True)
    print('Writing converted key for %s/%s to %s' % (oldkey['name'],
            oldkey['protocol'], path+'2'))
    with open(path+'3', 'wb') as f:
        f.write(newkey.serializePrivateKey())

if __name__ == '__main__':
    import sys
    convert(sys.argv[1])

########NEW FILE########
__FILENAME__ = testBasic
# some python3 compatibilty
from __future__ import print_function
from __future__ import unicode_literals

import unittest
import base64
from potr import proto


class ProtoTest(unittest.TestCase):
    def testPackData(self):
        self.assertEqual(b'\0\0\0\0', proto.pack_data(b''))
        self.assertEqual(b'\0\0\0\x0afoobarbazx', proto.pack_data(b'foobarbazx'))
        self.assertEqual(b'\0\1\0\0' + b'\xff' * 0x10000,
                proto.pack_data(b'\xff' * 0x10000))

    def testEncodeMpi(self):
        # small values
        self.assertEqual(b'\0\0\0\2\xff\0', proto.pack_mpi(65280))
        # the OTR protocol describes MPIs as carrying no leading zeros
        # so 0 itself should be encoded as the empty string
        self.assertEqual(b'\0\0\0\0', proto.pack_mpi(0))

        # large values
        self.assertEqual(b'\0\0\1\1\1' + 256*b'\0', proto.pack_mpi(0x100**0x100))

    def testDecodeMpi(self):
        # small values
        self.assertEqual((0, b'foo'), proto.read_mpi(b'\0\0\0\0foo'))
        self.assertEqual((0, b''), proto.read_mpi(b'\0\0\0\1\0'))
        self.assertEqual((65280, b''), proto.read_mpi(b'\0\0\0\2\xff\0'))
        # large values
        self.assertEqual((0x100**0x100-1, b'\xff'),
                proto.read_mpi(b'\0\0\1\0'+257*b'\xff'))

    def testUnpackData(self):
        encMsg = b'\0\0\0\1q\0\0\0\x0afoobarbazx'
        (decMsg, encMsg) = proto.read_data(encMsg)
        self.assertEqual(b'q', decMsg)
        (decMsg, encMsg) = proto.read_data(encMsg)
        self.assertEqual(b'foobarbazx', decMsg)
        self.assertEqual(b'', encMsg)

    def queryBoth(self, suffix, vset):
        self.assertEqual(b'?OTR' + suffix, bytes(proto.Query(vset)))
        self.assertEqual(proto.Query(vset), proto.Query.parse(suffix))

    def taggedBoth(self, text, suffix, vset):
        self.assertEqual(text + suffix, bytes(proto.TaggedPlaintext(text, vset)))
        self.assertEqual(proto.TaggedPlaintext(text, vset),
                proto.TaggedPlaintext.parse(text + suffix))

    def testQuery(self):
        # these are "canonical" representations
        self.queryBoth(b'v?', set())
        self.queryBoth(b'v2?', set([2]))
        self.queryBoth(b'?v?', set([1]))
        self.queryBoth(b'?v2?', set([1, 2]))

        # these should be parsable but should not be produced
        self.assertEqual(proto.Query(set([1])), proto.Query.parse(b'?'))
        self.assertEqual(proto.Query(set([1])), proto.Query.parse(b'v1?'))
        self.assertEqual(proto.Query(set([1,2,3,8])), proto.Query.parse(b'v2831?'))
        self.assertEqual(proto.Query(set([0,1,2])), proto.Query.parse(b'?v20xy?'))


        # both version tags
        self.taggedBoth(b'',
                b'\x20\x09\x20\x20\x09\x09\x09\x09\x20\x09\x20\x09\x20\x09\x20\x20'
                + b'\x20\x09\x20\x09\x20\x20\x09\x20'
                + b'\x20\x20\x09\x09\x20\x20\x09\x20',
                set([1,2]))
        # text + only v1 version tag
        self.taggedBoth(b'Hello World!\n',
                b'\x20\x09\x20\x20\x09\x09\x09\x09\x20\x09\x20\x09\x20\x09\x20\x20'
                + b'\x20\x09\x20\x09\x20\x20\x09\x20',
                set([1]))
        # text + only v2 version tag
        self.taggedBoth(b'Foo.\n',
                b'\x20\x09\x20\x20\x09\x09\x09\x09\x20\x09\x20\x09\x20\x09\x20\x20'
                + b'\x20\x20\x09\x09\x20\x20\x09\x20',
                set([2]))
        # only base tag, no version supported
        self.taggedBoth(b'',
                b'\x20\x09\x20\x20\x09\x09\x09\x09\x20\x09\x20\x09\x20\x09\x20\x20',
                set([]))

        # untagged
        self.assertRaises(TypeError,
                lambda: proto.TaggedPlaintext.parse(b'Foobarbaz?'))

        # only the version tag without base
        self.assertRaises(TypeError,
                lambda: proto.TaggedPlaintext.parse(b'Foobarbaz!'
                    + b'\x20\x09\x20\x09\x20\x20\x09\x20'))

    def testGenericMsg(self):
        msg = base64.b64encode(proto.pack_data(b'foo'))
        self.assertEqual(b'foo', proto.DHKey.parsePayload(msg).gy)
        self.assertEqual(b'?OTR:AAIK' + msg + b'.', bytes(proto.DHKey(b'foo')))

        msg = base64.b64encode(b'\x42\1\3\3\1\x08\6\4\2'
                + proto.pack_data(b'foo') + b'\0\0\0\0\xde\xad\xbe\xef'
                + proto.pack_data(b'encoded_dummy')
                + b'this is a dummy mac\0' + b'\0\0\0\0')
        pMsg = proto.DataMessage.parsePayload(msg)
        self.assertEqual(0x42, pMsg.flags)
        self.assertEqual(0x01030301, pMsg.skeyid)
        self.assertEqual(0x08060402, pMsg.rkeyid)
        self.assertEqual(b'foo', pMsg.dhy)
        self.assertEqual(b'\0\0\0\0\xde\xad\xbe\xef', pMsg.ctr)
        self.assertEqual(b'encoded_dummy', pMsg.encmsg)
        self.assertEqual(b'this is a dummy mac\0', pMsg.mac)
        self.assertEqual(b'', pMsg.oldmacs)
        self.assertEqual(b'?OTR:AAID' + msg + b'.',
            bytes(proto.DataMessage(0x42, 0x01030301, 0x08060402, b'foo',
                b'\0\0\0\0\xde\xad\xbe\xef', b'encoded_dummy',
                b'this is a dummy mac\0', b'')))

    def testGenericTLV(self):
        testtlvs = [
                (proto.DisconnectTLV(), b'\0\1\0\0'),
                (proto.SMP1TLV([1, 2, 3, 4, 5, 6]),
                    b'\0\2\0\x22\0\0\0\6\0\0\0\1\1\0\0\0\1\2\0\0\0\1\3\0\0\0\1\4\0\0\0\1\5\0\0\0\1\6'),
                (proto.SMPABORTTLV(), b'\0\6\0\0')
                ]

        for tlv, data in testtlvs:
            self.assertEqual(tlv, proto.TLV.parse(data)[0])
            self.assertEqual(data, bytes(tlv))

        tlvs, datas = tuple(zip(*testtlvs))
        self.assertEqual(list(tlvs), proto.TLV.parse(b''.join(datas)))

        self.assertRaises(TypeError, lambda: proto.TLV.parse(b'\0\1\0\1x'))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = testCommunicate
# some python3 compatibilty
from __future__ import print_function

import os
import pickle
import sys

import unittest

import otr
import potr
from potr import context

MMS = 30
PROTO = 'test'

PNAME = 'P-pureotr'
CNAME = 'C-libotr'

try:
    bytes('', encoding='ascii')
except TypeError:
    import __builtin__
    def str(s, encoding='ascii'):
        return __builtin__.str(s)
    def bytes(s, encoding='ascii'):
        return __builtin__.bytes(s)



#############################################################################
#
#   pure-otr infrastructure
#
#############################################################################

class TestContext(context.Context):
    def getPolicy(self, key):
        return self.user.policy[key]

    def inject(self, msg, appdata=None):
        appdata.csend(bytes(msg))

class TestAccount(context.Account):
    contextclass = TestContext
    def __init__(self, name, proto, mms, policy):
        super(TestAccount, self).__init__(name, proto, mms)
        self.policy = policy
    def loadPrivkey(self):
        try:
            with open(os.path.join(sys.path[0], 'pTest.key'), 'rb') as keyFile:
                return potr.crypt.PK.parsePrivateKey(keyFile.read())[0]
        except IOError:
            return None

    def savePrivkey(self):
        pass

#############################################################################
#
#   libotr infrastructure
#
#############################################################################

class COps:
    def __init__(self, test, policy):
        self.test = test
        self.dpolicy = policy
        self.cSecState = 0
        self.cSecTrust = False

    def policy(self, opdata=None, context=None):
        val = int(self.dpolicy['ALLOW_V1'])
        val |= int(self.dpolicy['ALLOW_V2']) << 1
        val |= int(self.dpolicy['REQUIRE_ENCRYPTION']) << 2
        val |= int(self.dpolicy['SEND_TAG']) << 3
        val |= int(self.dpolicy['WHITESPACE_START_AKE']) << 4
        val |= int(self.dpolicy['ERROR_START_AKE']) << 5
        return val

    def create_privkey(self, opdata=None, accountname=None, protocol=None):
        pass # ignore

    def is_logged_in(self, opdata=None, accountname=None, protocol=None,
            recipient=None):
        return True
    
    def inject_message(self, opdata=None, accountname=None, protocol=None,
            recipient=None, message=None):
        opdata.psend(bytes(message, encoding='ascii'))

    def notify(sef, opdata=None, level=None, accountname=None, protocol=None,
            username=None, title=None, primary=None, secondary=None):
        print('\nOTR notify: %r' % (title, primary, secondary))
        pass # ignore

    def display_otr_message(self, opdata=None, accountname=None,
            protocol=None, username=None, msg=None):
        return 1

    def update_context_list(self, opdata=None):
        pass

    def protocol_name(self, opdata=None, protocol=None):
        return PROTO

    def new_fingerprint(self, opdata=None, userstate=None, accountname=None,
            protocol=None, username=None, fingerprint=None):
        cFpReceived = fingerprint #otr.otrl_privkey_hash_to_human(fingerprint)

    def write_fingerprints(self, opdata=None):
        pass # ignore

    def gone_secure(self, opdata=None, context=None):
        trust = context.active_fingerprint.trust
        self.cSecState = 1
        if trust:
           self.cSecTrust = True
        else:
           self.cSecTrust = False

    def gone_insecure(self, opdata=None, context=None):
        self.cSecState = 2

    def still_secure(self, opdata=None, context=None, is_reply=0):
        pass # ignore

    def log_message(self, opdata=None, message=None):
        print('\nOTR LOG: %r' % message)
        pass # ignore

    def max_message_size(self, opdata=None, context=None):
        return MMS

    def account_name(self, opdata=None, account=None, context=None):
        return CNAME




class TestCommunicate(unittest.TestCase):
    def setUp(self):
        self.pQueue = []
        self.cQueue = []

        self.cUserState = otr.otrl_userstate_create()

    def createWithPolicies(self, ppol, cpol=None):
        if cpol is None:
            cpol = ppol
        self.pAccount = TestAccount(PNAME, PROTO, MMS, ppol)
        self.pCtx = self.pAccount.getContext(CNAME)
        self.cops = COps(self, cpol)
        otr.otrl_privkey_read(self.cUserState, "cTest.key")


#############################################################################
#
#   Actual tests
#
#############################################################################

    def testAutoFromP(self):
        self.createWithPolicies({
                    'ALLOW_V1':False,
                    'ALLOW_V2':True,
                    'REQUIRE_ENCRYPTION':False,
                    'SEND_TAG':True,
                    'WHITESPACE_START_AKE':True,
                    'ERROR_START_AKE':True,
                })

        self.psend(bytes(self.otrcsend(b'hello!'), encoding='ascii'))
        self.assertEqual((b'hello!', []),
                self.otrpparse(self.pCtx, self.prcv()))

        # no more messages to process:
        self.assertEqual((None, None, None), self.process(self.pCtx, self.cUserState))
        # went encrypted
        self.assertEqual(context.STATE_ENCRYPTED, self.cops.cSecState)
        self.assertEqual(context.STATE_ENCRYPTED, self.pCtx.state)

        # is untrusted
        self.assertFalse(self.cops.cSecTrust)
        self.assertFalse(self.pCtx.getCurrentTrust()) 

    def testAutoFromC(self):
        self.createWithPolicies({
                    'ALLOW_V1':False,
                    'ALLOW_V2':True,
                    'REQUIRE_ENCRYPTION':False,
                    'SEND_TAG':True,
                    'WHITESPACE_START_AKE':True,
                    'ERROR_START_AKE':True,
                })

        self.otrpsend(self.pCtx, b'hello!', context.FRAGMENT_SEND_ALL)
        #self.assertEqual((False, 'hello!', None), self.otrcparse(self.crcv()))
        self.assertEqual((True, b'hello!', None), self.process(self.pCtx,
                self.cUserState))

        # no more messages to process:
        self.assertEqual((None, None, None), self.process(self.pCtx, self.cUserState))
        # went encrypted
        self.assertEqual(context.STATE_ENCRYPTED, self.cops.cSecState)
        self.assertEqual(context.STATE_ENCRYPTED, self.pCtx.state)

        # is untrusted
        self.assertFalse(self.cops.cSecTrust)
        self.assertFalse(self.pCtx.getCurrentTrust()) 

    def testNothingFromP(self):
        self.createWithPolicies({
                    'ALLOW_V1':True,
                    'ALLOW_V2':True,
                    'REQUIRE_ENCRYPTION':False,
                    'SEND_TAG':False,
                    'WHITESPACE_START_AKE':False,
                    'ERROR_START_AKE':False,
                })

        origMsg = b'hello!'*100

        # no fragmentation, message unchanged
        msg = self.otrpsend(self.pCtx, origMsg)
        self.assertEqual(origMsg, msg)
        self.csend(msg)

        self.assertEqual((False, str(origMsg, encoding='ascii'), None), self.otrcparse(self.crcv()))

        # no more messages to process:
        self.assertEqual((None, None, None), self.process(self.pCtx, self.cUserState))
        # went encrypted
        self.assertEqual(context.STATE_PLAINTEXT, self.cops.cSecState)
        self.assertEqual(context.STATE_PLAINTEXT, self.pCtx.state)

        # is untrusted
        self.assertFalse(self.cops.cSecTrust)
        self.assertFalse(self.pCtx.getCurrentTrust()) 

    def testNothingFromC(self):
        self.createWithPolicies({
                    'ALLOW_V1':True,
                    'ALLOW_V2':True,
                    'REQUIRE_ENCRYPTION':False,
                    'SEND_TAG':False,
                    'WHITESPACE_START_AKE':False,
                    'ERROR_START_AKE':False,
                })

        origMsg = b'hello!'*100

        # no fragmentation, message unchanged
        msg = bytes(self.otrcsend(origMsg), encoding='ascii')
        self.assertEqual(origMsg, msg)
        self.psend(msg)

        self.assertEqual((origMsg, []), self.otrpparse(self.pCtx, self.prcv()))

        # no more messages to process:
        self.assertEqual((None, None, None), self.process(self.pCtx, self.cUserState))
        # went encrypted
        self.assertEqual(context.STATE_PLAINTEXT, self.cops.cSecState)
        self.assertEqual(context.STATE_PLAINTEXT, self.pCtx.state)

        # is untrusted
        self.assertFalse(self.cops.cSecTrust)
        self.assertFalse(self.pCtx.getCurrentTrust()) 

#############################################################################
#
#   Message helpers
#
#############################################################################

    def otrcparse(self, msg):
        return otr.otrl_message_receiving(self.cUserState, (self.cops, self),
            CNAME, PROTO, PNAME, str(msg, encoding='ascii'))

    def otrcsend(self, msg):
        return otr.otrl_message_sending(self.cUserState, (self.cops, self),
            CNAME, PROTO, PNAME, str(msg, encoding='ascii'), None)

    def otrpparse(self, ctx, msg):
        return ctx.receiveMessage(msg, appdata=self)

    def otrpsend(self, ctx, msg, fragment=context.FRAGMENT_SEND_ALL_BUT_FIRST):
        return ctx.sendMessage(fragment, msg, appdata=self)


#############################################################################
#
#   Message queues
#
#############################################################################



    def csend(self, msg):
        self.cQueue.append(msg)

    def crcv(self):
        return self.cQueue.pop(0)

    def psend(self, msg):
        self.pQueue.append(msg)

    def prcv(self):
        return self.pQueue.pop(0)

    def process(self, pCtx, cUserState):
        while len(self.cQueue) > 0 or len(self.pQueue) > 0:
            if self.pQueue:
                dat = self.prcv()
                txt, tlvs = self.otrpparse(self.pCtx, dat)
                #txt, tlvs = self.otrpparse(self.pCtx, self.prcv())
                if txt:
                    return (False, txt, tlvs)
            if self.cQueue:
                is_internal, txt, tlvs = self.otrcparse(self.crcv())
                if not is_internal and txt:
                    return (True, bytes(txt, encoding='ascii'), tlvs)
        return None, None, None

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
