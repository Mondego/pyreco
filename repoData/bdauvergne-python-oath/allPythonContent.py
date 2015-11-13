__FILENAME__ = google_authenticator
'''
Google Authenticator API
------------------------

Google Authenticator is based on HOTP and TOTP. It provides a simple way of
provisionning an OTP generator through a new URL scheme.

This module provides parsing and high-level API over the classic HOTP and TOTP
APIs provided by the oath.hotp and oath.totp modules.
'''

import re
import urlparse
import base64
import hashlib
import urllib

from . import _hotp as hotp
from . import _totp as totp

__all__ = ('GoogleAuthenticator', 'from_b32key')

otpauth_re = re.compile(r'^otpauth://(?P<type>\w+)'
                        r'/(?P<labe>[^?]+)'
                        r'\?(?P<query>.*)$')

LABEL   =   'label'
TYPE    =    'type'
ALGORITHM = 'algorithm'
DIGITS  =  'digits'
SECRET  =  'secret'
COUNTER = 'counter'
PERIOD  =  'period'
TOTP    =    'totp'
HOTP    =    'hotp'
DRIFT    =   'drift'

def parse_otpauth(otpauth_uri):
    m = re.match(otpauth_re, otpauth_uri)
    if not m:
        raise ValueError('Invalid otpauth URI', otpauth_uri)
    d = m.groupdict()
    query_parse = urlparse.parse_qs(d['query'])
    if SECRET not in query_parse:
        raise ValueError('Missing secret field in otpauth URI', otpauth_uri)
    try:
        d[SECRET] = base64.b32decode(query_parse[SECRET][0]).encode('hex')
    except TypeError:
        raise ValueError('Invalid base32 encoding of the secret field in '
                'otpauth URI', otpauth_uri)
    if ALGORITHM in query_parse:
        d[ALGORITHM] = query_parse[ALGORITHM].lower()
        if d[ALGORITHM] not in ('sha1', 'sha256', 'sha512', 'md5'):
            raise ValueError('Invalid value for algorithm field in otpauth '
                    'URI', otpauth_uri)
    else:
        d[ALGORITHM] = 'sha1'
    try:
        d[ALGORITHM] = getattr(hashlib, d[ALGORITHM])
    except AttributeError:
        raise ValueError('Unsupported algorithm %s in othauth URI' %
                d[ALGORITHM], otpauth_uri)
    for key in (DIGITS, PERIOD, COUNTER):
        try:
            if key in query_parse:
                d[key] = int(query_parse[key])
        except ValueError:
            raise ValueError('Invalid value for field %s in otpauth URI, must '
                    'be a number' % key, otpauth_uri)
    if COUNTER not in d:
        d[COUNTER] = 0 # what else ?
    if DIGITS in d:
        if d[DIGITS] not in (6,8):
            raise ValueError('Invalid value for field digits in othauth URI, it '
                    'must 6 or 8', otpauth_uri)
    else:
        d[DIGITS] = 6
    if d[TYPE] == HOTP and COUNTER not in d:
        raise ValueError('Missing field counter in otpauth URI, it is '
                'mandatory with the hotp type', otpauth_uri)
    if d[TYPE] == TOTP and PERIOD not in d:
        d[PERIOD] = 30
    return d


def from_b32key(b32_key, state=None):
    '''Some phone app directly accept a partial b32 encoding, we try to emulate that'''
    if len(b32_key) % 8 not in (0, 2, 4, 5, 7):
        raise ValueError('invalid base32 value')
    b32_key += '=' * (8 - len(b32_key) % 8)
    b32_key = b32_key.upper()
    try:
        base64.b32decode(b32_key)
    except TypeError:
        raise ValueError('invalid base32 value')
    return GoogleAuthenticator('otpauth://totp/xxx?%s' %
            urllib.urlencode({'secret': b32_key}), state=state)


class GoogleAuthenticator(object):
    def __init__(self, otpauth_uri, state=None):
        self.otpauth_uri = otpauth_uri
        self.parsed_otpauth_uri = parse_otpauth(otpauth_uri)
        self.generator_state = state or {}
        self.acceptor_state = state or {}

    def generate(self, t=None):
        format = 'dec%s' % self.parsed_otpauth_uri[DIGITS]
        hash = self.parsed_otpauth_uri[ALGORITHM]
        secret = self.parsed_otpauth_uri[SECRET]
        state = self.generator_state
        if self.parsed_otpauth_uri[TYPE] == HOTP:
            if COUNTER not in state:
                state[COUNTER] = self.parsed_otpauth_uri[COUNTER]
            otp = hotp.hotp(secret, state[COUNTER], format=format, hash=hash)
            state[COUNTER] += 1
            return otp
        elif self.parsed_otpauth_uri[TYPE] == TOTP:
            period = self.parsed_otpauth_uri[PERIOD]
            return totp.totp(secret, format=format, period=period, hash=hash, t=t)
        else:
            raise NotImplementedError(self.parsed_otpauth_uri[TYPE])

    def accept(self, otp, hotp_drift=3, hotp_backward_drift=0,
            totp_forward_drift=1, totp_backward_drift=1, t=None):
        format = 'dec%s' % self.parsed_otpauth_uri[DIGITS]
        hash = self.parsed_otpauth_uri[ALGORITHM]
        secret = self.parsed_otpauth_uri[SECRET]
        state = self.acceptor_state
        if self.parsed_otpauth_uri[TYPE] == HOTP:
            if COUNTER not in state:
                state[COUNTER] = self.parsed_otpauth_uri[COUNTER]
            ok, state[COUNTER] = hotp.accept_hotp(otp, secret, state[COUNTER],
                    format=format, hash=hash, drift=hotp_drift,
                    backward_drift=hotp_backward_drift)
            return ok
        elif self.parsed_otpauth_uri[TYPE] == TOTP:
            period = 'dec%s' % self.parsed_otpauth_uri[PERIOD]
            if DRIFT not in state:
                state[DRIFT] = 0
            ok, state[DRIFT] = totp.accept_totp(secret, otp, format=format,
                    period=period, forward_drift=totp_forward_drift,
                    backward_drift=totp_backward_drift, drift=state[DRIFT],
                    t=t)
            return ok
        else:
            raise NotImplementedError(self.parsed_otpauth_uri[TYPE])

########NEW FILE########
__FILENAME__ = _hotp
import hashlib
import hmac
import binascii

'''
HOTP implementation

To compute an HOTP one-time-password:

    >>> hotp(key, counter)

where is the hotp is a key given as an hexadecimal string and counter is an
integer. The counter value must be kept synchronized on the server and the
client side. 

See also http://tools.ietf.org/html/rfc4226
'''

__all__ = ( 'hotp', 'accept_hotp' )

def truncated_value(h):
    bytes = map(ord, h)
    offset = bytes[-1] & 0xf
    v = (bytes[offset] & 0x7f) << 24 | (bytes[offset+1] & 0xff) << 16 | \
            (bytes[offset+2] & 0xff) << 8 | (bytes[offset+3] & 0xff)
    return v

def dec(h,p):
    v = truncated_value(h)
    v = v % (10**p)
    return '%0*d' % (p, v)


def int2beint64(i):
    hex_counter = hex(long(i))[2:-1]
    hex_counter = '0' * (16 - len(hex_counter)) + hex_counter
    bin_counter = binascii.unhexlify(hex_counter)
    return bin_counter

def __hotp(key, counter, hash=hashlib.sha1):
    bin_counter = int2beint64(counter)
    bin_key = binascii.unhexlify(key)

    return hmac.new(bin_key, bin_counter, hash).digest()

def hotp(key,counter,format='dec6',hash=hashlib.sha1):
    '''
       Compute a HOTP value as prescribed by RFC4226

       :param key: 
           the HOTP secret key given as an hexadecimal string
       :param counter:
           the OTP generation counter
       :param format:
           the output format, can be:
              - hex, for a variable length hexadecimal format,
              - hex-notrunc, for a 40 characters hexadecimal non-truncated format,
              - dec4, for a 4 characters decimal format,
              - dec6,
              - dec7, or
              - dec8
           it defaults to dec6.
       :param hash:
           the hash module (usually from the hashlib package) to use,
           it defaults to hashlib.sha1.

       :returns:
           a string representation of the OTP value (as instructed by the format parameter).

       Examples:

        >>> hotp('343434', 2, format='dec6')
            '791903'
    '''
    bin_hotp = __hotp(key, counter, hash)

    if format == 'dec4':
        return dec(bin_hotp, 4)
    elif format == 'dec6':
        return dec(bin_hotp, 6)
    elif format == 'dec7':
        return dec(bin_hotp, 7)
    elif format == 'dec8':
        return dec(bin_hotp, 8)
    elif format == 'hex':
        return hex(truncated_value(bin_hotp))[2:]
    elif format == 'hex-notrunc':
        return binascii.hexlify(bin_hotp)
    elif format == 'bin':
        return bin_hotp
    elif format == 'dec':
        return str(truncated_value(bin_hotp))
    else:
        raise ValueError('unknown format')

def accept_hotp(key, response, counter, format='dec6', hash=hashlib.sha1,
        drift=3, backward_drift=0):
    '''
       Validate a HOTP value inside a window of
       [counter-backward_drift:counter+forward_drift]

       :param key:
           the shared secret
       :type key:
           hexadecimal string of even length
       :param response:
           the OTP to check
       :type response:
           ASCII string
       :param counter:
           value of the counter running inside an HOTP token, usually it is
           just the count of HOTP value accepted so far for a given shared
           secret; see the specifications of HOTP for more details;
       :param format:
           the output format, can be:
             - hex40, for a 40 characters hexadecimal format,
             - dec4, for a 4 characters decimal format,
             - dec6,
             - dec7, or
             - dec8
           it defaults to dec6.
       :param hash:
           the hash module (usually from the hashlib package) to use,
           it defaults to hashlib.sha1.
       :param drift:
           how far we can look forward from the current value of the counter
       :param backward_drift:
           how far we can look backward from the current counter value to
           match the response, default to zero as it is usually a bad idea to
           look backward as the counter is only advanced when a valid value is
           checked (and so the counter on the token side should have been
           incremented too)

       :returns:
           a pair of a boolean and an integer:
            - first is True if the response is validated and False otherwise,
            - second is the new value for the counter; it can be more than
              counter + 1 if the drift window was used; you must store it if
              the response was validated.

       >>> accept_hotp('343434', '122323', 2, format='dec6')
           (False, 2)

       >>> hotp('343434', 2, format='dec6')
           '791903'

       >>> accept_hotp('343434', '791903', 2, format='dec6')
           (True, 3)

       >>> hotp('343434', 3, format='dec6')
           '907279'

       >>> accept_hotp('343434', '907279', 2, format='dec6')
           (True, 4)
    '''

    for i in range(-backward_drift, drift+1):
        if hotp(key, counter+i, format=format, hash=hash) == str(response):
            return True, counter+i+1
    return False,counter

########NEW FILE########
__FILENAME__ = _ocra
import hmac
import hashlib
import re
import random
import string

from . import _hotp as hotp

'''
    Implementation of OCRA


    See also http://tools.ietf.org/html/draft-mraihi-mutual-oath-hotp-variants-14
'''

__all__ = ('str2ocrasuite', 'StateException', 'OCRAChallengeResponseServer',
    'OCRAChallengeResponseClient', 'OCRAMutualChallengeResponseServer',
    'OCRAMutualChallengeResponseClient')

def is_int(v):
    try:
        int(v)
        return True
    except ValueError:
        return False

# Constants
PERIODS = { 'H': 3600, 'M': 60, 'S': 1 }
HOTP = 'HOTP'
OCRA_1 = 'OCRA-1'

class CryptoFunction(object):
    '''Represents an OCRA CryptoFunction specification.

       :attribute hash_algo:
           an object implementing the digest interface as given by PEP 247 and
           the hashlib package
       :attribute truncation_length:
           the length to truncate the decimal representation, can be None, in
           this case no truncation is done.
    '''
    def __init__(self, hash_algo, truncation_length):
        assert hash_algo
        assert is_int(truncation_length) or truncation_length is None
        self.hash_algo = hash_algo
        self.truncation_length = truncation_length

    def __call__(self, key, data_input):
        '''Compute an HOTP digest using the given key and data input and
           following the current crypto function description.

           :param key:
               a byte string containing the HMAC key

           :param data_input:
               the data input assembled as a byte-string as described by the
               OCRA specification
           :returns:
               the computed digest
           :rtype: str
        '''
        h = hmac.new(key, data_input, self.hash_algo).digest()
        if self.truncation_length:
            return hotp.dec(h, self.truncation_length)
        else:
            return str(hotp.truncated_value(h))

    def __str__(self):
        '''Return the standard representation for the given crypto function.
        '''
        return 'HOTP-%s-%s' % (self.hash_algo.__name__, self.truncation_length)

def str2hashalgo(description):
    '''Convert the name of a hash algorithm as described in the OATH
       specifications, to a python object handling the digest algorithm
       interface, PEP-xxx.

       :param description
           the name of the hash algorithm, example
       :rtype: a hash algorithm class constructor
    '''
    algo = getattr(hashlib, description.lower(), None)
    if not callable(algo):
        raise ValueError, ('Unknown hash algorithm', description)
    return algo

def str2cryptofunction(crypto_function_description):
    '''
       Convert an OCRA crypto function description into a CryptoFunction
       instance

       :param crypto_function_description:
       :returns:
           the CryptoFunction object
       :rtype: CryptoFunction
    '''
    s = crypto_function_description.split('-')
    if len(s) != 3:
        raise ValueError, 'CryptoFunction description must be triplet separated by -'
    if s[0] != HOTP:
        raise ValueError, ('Unknown CryptoFunction kind', s[0])
    algo = str2hashalgo(s[1])
    try:
        truncation_length = int(s[2])
        if truncation_length < 0 or truncation_length > 10:
            raise ValueError
    except ValueError:
        raise ValueError, ('Invalid truncation length', s[2])
    return CryptoFunction(algo, truncation_length)

class DataInput(object):
    '''
       OCRA data input description

       By calling this instance of this class and giving the needed parameter
       corrresponding to the data input description, it compute a binary string
       to give to the HMAC algorithme implemented by a CryptoFunction object
    '''

    __slots__ = [ 'C', 'Q', 'P', 'S', 'T' ]

    def __init__(self, C=None, Q=None, P=None, S=None, T=None):
        self.C = C
        self.Q = Q
        self.P = P
        self.S = S
        self.T = T

    def __call__(self, C=None, Q=None, P=None, P_digest=None, S=None, T=None,
            T_precomputed=None, Qsc=None):
        datainput = ''
        if self.C:
            try:
                C = int(C)
                if C < 0 or C > 2**64:
                    raise Exception()
            except:
                raise ValueError, ('Invalid counter value', C)
            datainput += hotp.int2beint64(int(C))
        if self.Q:
            max_length = self.Q[1]
            if Qsc is not None:
                # Mutual Challenge-Response
                Q = Qsc
                max_length *= 2
            if Q is None or not isinstance(Q, str) or len(Q) > max_length:
                raise ValueError, 'challenge'
            if self.Q[0] == 'N' and not Q.isdigit():
                raise ValueError, 'challenge'
            if self.Q[0] == 'A' and not Q.isalnum():
                raise ValueError, 'challenge'
            if self.Q[0] == 'H':
                try:
                    int(Q, 16)
                except ValueError:
                    raise ValueError, 'challenge'
            if self.Q[0] == 'N':
                Q = hex(int(Q))[2:]
                Q += '0' * (len(Q) % 2)
                Q = Q.decode('hex')
            if self.Q[0] == 'A':
                pass
            if self.Q[0] == 'H':
                Q = Q.decode('hex')
            datainput += Q
            datainput += '\0' * (128-len(Q))
        if self.P:
            if P_digest:
                if len(P) == self.P.digest_size:
                    datainput += P_digest
                elif len(P) == 2*self.P.digest_size:
                    datainput += P_digest.decode('hex')
                else:
                    raise ValueError, ('Pin/Password digest invalid', P_digest)
            elif P is None:
                raise ValueError, 'Pin/Password missing'
            else:
                datainput += self.P(P).digest()
        if self.S:
            if S is None or len(S) != self.S:
                raise ValueError, 'session'
            datainput += S
        if self.T:
            if is_int(T_precomputed):
                datainput += hotp.int2beint64(int(T_precomputed))
            elif is_int(T):
                datainput += hotp.int2beint64(int(T / self.T))
            else:
                raise ValueError, 'timestamp'
        return datainput

    def __str__(self):
        values = []
        for slot in DataInput.__slots__:
            value = getattr(self, slot, None)
            if value is not None:
                values.append('{0}={1}'.format(slot, value))
        return '<{0} {1}>'.format(DataInput.__class__.__name__, ', '.join(values))



def str2datainput(datainput_description):
    elements = datainput_description.split('-')
    datainputs = {}
    for element in elements:
        letter = element[0]
        if letter in datainputs:
            raise ValueError, ('DataInput alreadu present %s', element, datainput_description)
        if letter == 'C':
            datainputs['C'] = 1
        elif letter == 'Q':
            if len(element) == 1:
                datainputs['Q'] = ('N',8)
            else:
                second_letter = element[1]
                try:
                    if second_letter not in 'ANH':
                        raise ValueError
                    length = int(element[2:])
                    if length < 4 or length > 64:
                        raise ValueError
                except ValueError:
                    raise ValueError, ('Invalid challenge descriptor', element)
                datainputs['Q'] = (second_letter, length)
        elif letter == 'P':
            algo = str2hashalgo(element[1:] or 'SHA1')
            datainputs['P'] = algo
        elif letter == 'S':
            length = 64
            if element[1:]:
                try:
                    length = int(element[1:])
                except ValueError:
                    raise ValueError, ('Invalid session data descriptor', element)
            datainputs['S'] = length
        elif letter == 'T':
            complement = element[1:] or '1M'
            try:
                length = 0
                if not re.match('^(\d+[HMS])+$', complement):
                    raise ValueError
                parts = re.findall('\d+[HMS]', complement)
                for part in parts:
                    period = part[-1]
                    quantity = int(part[:-1])
                    length += quantity * PERIODS[period]
                datainputs['T'] = length
            except ValueError:
                raise ValueError, ('Invalid timestamp descriptor', element)
        else:
            raise ValueError, ('Invalid datainput descriptor', element)
    return DataInput(**datainputs)


class OcraSuite(object):
    def __init__(self, ocrasuite_description, crypto_function, data_input):
        self.ocrasuite_description = ocrasuite_description
        self.crypto_function = crypto_function
        self.data_input = data_input

    def __call__(self, key, **kwargs):
        data_input = self.ocrasuite_description + '\0' \
                + self.data_input(**kwargs)
        return self.crypto_function(key, data_input)

    def accept(self, response, key, **kwargs):
        return str(response) == self(key, **kwargs)

    def __str__(self):
        return '<OcraSuite crypto_function:%s data_input:%s>' % (self.crypto_function,
                self.data_input)

def str2ocrasuite(ocrasuite_description):
    elements = ocrasuite_description.split(':')
    if len(elements) != 3:
        raise ValueError, ('Bad OcraSuite description', ocrasuite_description)
    if elements[0] != OCRA_1:
        raise ValueError, ('Unsupported OCRA identifier', elements[0])
    crypto_function = str2cryptofunction(elements[1])
    data_input = str2datainput(elements[2])
    return OcraSuite(ocrasuite_description, crypto_function, data_input)

class StateException(Exception):
    pass

DEFAULT_LENGTH = 20

class OCRAChallengeResponse(object):
    state = 1

    def __init__(self, key, ocrasuite_description, remote_ocrasuite_description=None):
        self.key = key
        self.ocrasuite = str2ocrasuite(ocrasuite_description)
        self.remote_ocrasuite = remote_ocrasuite_description is not None \
                and str2ocrasuite(remote_ocrasuite_description)
        if not self.ocrasuite.data_input.Q:
            raise ValueError, ('Ocrasuite must have a Q descriptor',)

def compute_challenge(Q):
    kind, length = Q
    r = xrange(0, length)
    if kind == 'N':
        c = ''.join([random.choice(string.digits) for i in r])
    elif kind == 'A':
        alphabet = string.digits + string.letters
        c = ''.join([random.choice(alphabet) for i in r])
    elif kind == 'H':
        c = ''.join([random.choice(string.hexdigits) for i in r])
    else:
        raise ValueError, ('Q kind is unknown:', kind)
    return c

class OCRAChallengeResponseServer(OCRAChallengeResponse):
    SERVER_STATE_COMPUTE_CHALLENGE = 1
    SERVER_STATE_VERIFY_RESPONSE = 2
    SERVER_STATE_FINISHED = 3

    def compute_challenge(self):
        if self.state != self.SERVER_STATE_COMPUTE_CHALLENGE:
            raise StateException()
        ocrasuite = self.remote_ocrasuite or self.ocrasuite
        self.challenge = compute_challenge(ocrasuite.data_input.Q)
        self.state = self.SERVER_STATE_VERIFY_RESPONSE
        return self.challenge

    def verify_response(self, response, **kwargs):
        if self.state != self.SERVER_STATE_VERIFY_RESPONSE:
            return StateException()
        ocrasuite = self.remote_ocrasuite or self.ocrasuite
        c = ocrasuite(self.key, Q=self.challenge, **kwargs) == response
        if c:
            self.state = self.SERVER_STATE_FINISHED
        return c


class OCRAChallengeResponseClient(OCRAChallengeResponse):
    def compute_response(self, challenge, **kwargs):
        return self.ocrasuite(self.key, Q=challenge, **kwargs)

class OCRAMutualChallengeResponseClient(OCRAChallengeResponse):
    CLIENT_STATE_COMPUTE_CLIENT_CHALLENGE = 1
    CLIENT_STATE_VERIFY_SERVER_RESPONSE = 2
    CLIENT_STATE_COMPUTE_CLIENT_RESPONSE = 3
    CLIENT_STATE_FINISHED = 4

    def compute_client_challenge(self, Qc=None):
        if self.state != self.CLIENT_STATE_COMPUTE_CLIENT_CHALLENGE:
            raise StateException()

        ocrasuite = self.remote_ocrasuite or self.ocrasuite
        self.client_challenge = Qc or compute_challenge(ocrasuite.data_input.Q)
        self.state = self.CLIENT_STATE_VERIFY_SERVER_RESPONSE
        return self.client_challenge

    def verify_server_response(self, response, challenge, **kwargs):
        if self.state != self.CLIENT_STATE_VERIFY_SERVER_RESPONSE:
            return StateException()
        self.server_challenge = challenge
        q = self.client_challenge+self.server_challenge
        ocrasuite = self.remote_ocrasuite or self.ocrasuite
        c = ocrasuite(self.key, Qsc=q, **kwargs) == response
        if c:
            self.state = self.CLIENT_STATE_COMPUTE_CLIENT_RESPONSE
        return c

    def compute_client_response(self, **kwargs):
        if self.state != self.CLIENT_STATE_COMPUTE_CLIENT_RESPONSE:
            return StateException()
        q = self.server_challenge+self.client_challenge
        rc = self.ocrasuite(self.key, Qsc=q, **kwargs)
        self.state = self.CLIENT_STATE_FINISHED
        return rc

class OCRAMutualChallengeResponseServer(OCRAChallengeResponse):
    SERVER_STATE_COMPUTE_SERVER_RESPONSE = 1
    SERVER_STATE_VERIFY_CLIENT_RESPONSE = 2
    SERVER_STATE_FINISHED = 3

    def compute_server_response(self, challenge, Qs=None, **kwargs):
        if self.state != self.SERVER_STATE_COMPUTE_SERVER_RESPONSE:
            raise StateException()
        self.client_challenge = challenge
        self.server_challenge = Qs or compute_challenge(self.ocrasuite.data_input.Q)
        q = self.client_challenge+self.server_challenge
        # no need for pin with server mode
        kwargs.pop('P', None)
        kwargs.pop('P_digest', None)
        rs = self.ocrasuite(self.key, Qsc=q, **kwargs)
        self.state = self.SERVER_STATE_VERIFY_CLIENT_RESPONSE
        return rs, self.server_challenge

    def verify_client_response(self, response, **kwargs):
        if self.state != self.SERVER_STATE_VERIFY_CLIENT_RESPONSE:
            raise StateException()
        q = self.server_challenge+self.client_challenge
        ocrasuite = self.remote_ocrasuite or self.ocrasuite
        c = ocrasuite(self.key, Qsc=q, **kwargs) == response
        if c:
            self.state = self.SERVER_STATE_FINISHED
        return c

########NEW FILE########
__FILENAME__ = _totp
import time
import hashlib
import datetime
import calendar

'''
:mod:`totp` -- RFC6238 - OATH TOTP implementation
=================================================

.. module:: parrot
  :platform: any
  :synosis: implement a time indexed one-time password algorithm based on a HMAC crypto function as specified in RFC6238
.. moduleauthor:: Benjamin Dauvergne <benjamin.dauvergne@gmail.com>

'''


from ._hotp import hotp

__all__ = ('totp', 'accept_totp')

def totp(key, format='dec6', period=30, t=None, hash=hashlib.sha1):
    '''
       Compute a TOTP value as prescribed by OATH specifications.

       :param key:
           the TOTP key given as an hexadecimal string
       :param format:
           the output format, can be:
              - hex40, for a 40 characters hexadecimal format,
              - dec4, for a 4 characters decimal format,
              - dec6,
              - dec7, or
              - dec8
           it default to dec6.
       :param period:
           a positive integer giving the period between changes of the OTP
           value, as seconds, it defaults to 30.
       :param t:
           a positive integer giving the current time as seconds since EPOCH
           (1st January 1970 at 00:00 GMT), if None we use time.time(); it
           defaults to None;
       :param hash:
           the hash module (usually from the hashlib package) to use,
           it defaults to hashlib.sha1.

       :returns:
           a string representation of the OTP value (as instructed by the format parameter).
       :type: str
    '''
    if t is None:
        t = int(time.time())
    else:
        if isinstance(t, datetime.datetime):
            t = calendar.timegm(t.utctimetuple())
        else:
            t = int(t)
    T = int(t/period)
    return hotp(key, T, format=format, hash=hash)

def accept_totp(key, response, format='dec6', period=30, t=None,
        hash=hashlib.sha1, forward_drift=1, backward_drift=1, drift=0):
    '''
       Validate a TOTP value inside a window of 
       [drift-bacward_drift:drift+forward_drift] of time steps.
       Where drift is the drift obtained during the last call to accept_totp.

       :param response:
           a string representing the OTP to check, its format should correspond
           to the format parameter (it's not mandatory, it is part of the
           checks),
       :param key:
           the TOTP key given as an hexadecimal string
       :param format:
           the output format, can be:
              - hex40, for a 40 characters hexadecimal format,
              - dec4, for a 4 characters decimal format,
              - dec6,
              - dec7, or
              - dec8
           it default to dec6.
       :param period:
           a positive integer giving the period between changes of the OTP
           value, as seconds, it defaults to 30.
       :param t:
           a positive integer giving the current time as seconds since EPOCH
           (1st January 1970 at 00:00 GMT), if None we use time.time(); it
           defaults to None;
       :param hash:
           the hash module (usually from the hashlib package) to use,
           it defaults to hashlib.sha1.
       :param forward_drift:
           how much we accept the client clock to advance, as a number of
           periods,  i.e. if the period is 30 seconds, a forward_drift of 2,
           allows at most a clock a drift of 90 seconds;

                   Schema:
                          .___ Current time
                          |
                   0      v       + 30s         +60s              +90s
                   [ current_period |   period+1  |   period+2     [

           it defaults to 1.

       :param backward_drift:
           how much we accept the client clock to backstep; it defaults to 1.
       :param drift:
           an absolute drift of the local clock to the client clock; use it to
           keep track of an augmenting drift with a client without augmenting
           the size of the window given by forward_drift and backward_dript; it
           defaults to 0, you should usually give as value the last value
           returned by accept_totp for this client (read further).

       :returns:
           a pair (v,d) where v is a boolean giving the result, and d the
           needed drift to validate the value. The drift value should be saved
           relative to the current client. This saved value SHOULD be used in
           later calls to accept_totp in order to accept a slowly accumulating
           drift in the client token clock; on the server side you should use
           reliable source of time like an NTP server.
       :rtype: a two element tuple
    '''
    if t is None:
        t = int(time.time())
    for i in range(max(-divmod(t, period)[0],-backward_drift),forward_drift+1):
        d = (drift+i) * period
        if totp(key, format=format, period=period, hash=hash, t=t+d) == str(response):
            return True, drift+i
    return False, 0

########NEW FILE########
__FILENAME__ = google_authenticator
import unittest

class GoogleAuthenticator(unittest.TestCase):
    def test_simple(self):
        from oath.google_authenticator import from_b32key
        l = (
                # generated from http://gauth.apps.gbraad.nl/
                (1391203240, 'GG', '762819'),
                (1391203342, 'FF', '737839'),
            )
        for t, b32_key, result in l:
            self.assertEquals(from_b32key(b32_key).generate(t=t), result)

########NEW FILE########
__FILENAME__ = hotp
import unittest

from oath import hotp, accept_hotp

class Hotp(unittest.TestCase):
    secret = '3132333435363738393031323334353637383930'

    def test_hotp(self):
        tvector = [
            (0, 'cc93cf18508d94934c64b65d8ba7667fb7cde4b0'),
            (1, '75a48a19d4cbe100644e8ac1397eea747a2d33ab'),
            (2, '0bacb7fa082fef30782211938bc1c5e70416ff44'),
            (3, '66c28227d03a2d5529262ff016a1e6ef76557ece'),
            (4, 'a904c900a64b35909874b33e61c5938a8e15ed1c'),
            (5, 'a37e783d7b7233c083d4f62926c7a25f238d0316'),
            (6, 'bc9cd28561042c83f219324d3c607256c03272ae'),
            (7, 'a4fb960c0bc06e1eabb804e5b397cdc4b45596fa'),
            (8, '1b3c89f65e6c9e883012052823443f048b4332db'),
            (9, '1637409809a679dc698207310c8c7fc07290d9e5'), ]

        for counter, value in tvector:
            h = hotp(self.secret, counter, format='hex-notrunc')
            self.assertEqual(h, value)

    def test_accept_hotp(self):
        tvector2 = [
            (0, '4c93cf18', '1284755224', '755224',),
            (1, '41397eea', '1094287082', '287082',),
            (2, '82fef30',  '137359152',  '359152',),
            (3, '66ef7655', '1726969429', '969429',),
            (4, '61c5938a', '1640338314', '338314',),
            (5, '33c083d4', '868254676',  '254676',),
            (6, '7256c032', '1918287922', '287922',),
            (7, '4e5b397',  '82162583',   '162583',),
            (8, '2823443f', '673399871',  '399871',),
            (9, '2679dc69',  '645520489', '520489',),]

        for counter, hexa, deci, trunc in tvector2:
            h = hotp(self.secret, counter, format='hex')
            d = hotp(self.secret, counter, format='dec')
            d6 = hotp(self.secret, counter, format='dec6')
            self.assertEqual(d, deci)
            self.assertEqual(h,  hexa)
            self.assertEqual(d6, trunc)
            self.assertTrue(accept_hotp(self.secret, trunc, counter))

    def test_dec8_regression_20130716(self):
        h = hotp("fb9cda921c82d893d9cdc6d6559997b1","132974666","dec8")
        assert len(h) == 8, 'wrong length %s' % h
        assert h == '03562487'

########NEW FILE########
__FILENAME__ = ocra
import unittest
from oath import (str2ocrasuite, OCRAMutualChallengeResponseClient,
        OCRAMutualChallengeResponseServer)


class OCRA(unittest.TestCase):
    key20 = '3132333435363738393031323334353637383930'.decode('hex')
    key32 = '3132333435363738393031323334353637383930313233343536373839303132'\
            .decode('hex')
    key64 = '31323334353637383930313233343536373839303132333435363738393031323\
334353637383930313233343536373839303132333435363738393031323334'.decode('hex')
    pin = '1234'
    pin_sha1 = '7110eda4d09e062aa5e4a390b0a572ac0d2c0220'.decode('hex')

    tests = [ { 'ocrasuite': 'OCRA-1:HOTP-SHA1-6:QN08',
                'key': key20,
                'vectors': [
                    {'params': { 'Q': '00000000' }, 'result': '237653' },
                    {'params': { 'Q': '11111111' }, 'result': '243178' },
                    {'params': { 'Q': '22222222' }, 'result': '653583' },
                    {'params': { 'Q': '33333333' }, 'result': '740991' },
                    {'params': { 'Q': '44444444' }, 'result': '608993' },
                    {'params': { 'Q': '55555555' }, 'result': '388898' },
                    {'params': { 'Q': '66666666' }, 'result': '816933' },
                    {'params': { 'Q': '77777777' }, 'result': '224598' },
                    {'params': { 'Q': '88888888' }, 'result': '750600' },
                    {'params': { 'Q': '99999999' }, 'result': '294470' }
                ]
              },
              { 'ocrasuite': 'OCRA-1:HOTP-SHA256-8:C-QN08-PSHA1',
                'key': key32,
                'vectors': [
                    {'params': { 'C': 0, 'Q': '12345678' }, 'result': '65347737' },
                    {'params': { 'C': 1, 'Q': '12345678' }, 'result': '86775851' },
                    {'params': { 'C': 2, 'Q': '12345678' }, 'result': '78192410' },
                    {'params': { 'C': 3, 'Q': '12345678' }, 'result': '71565254' },
                    {'params': { 'C': 4, 'Q': '12345678' }, 'result': '10104329' },
                    {'params': { 'C': 5, 'Q': '12345678' }, 'result': '65983500' },
                    {'params': { 'C': 6, 'Q': '12345678' }, 'result': '70069104' },
                    {'params': { 'C': 7, 'Q': '12345678' }, 'result': '91771096' },
                    {'params': { 'C': 8, 'Q': '12345678' }, 'result': '75011558' },
                    {'params': { 'C': 9, 'Q': '12345678' }, 'result': '08522129' }
                ]
              },
              { 'ocrasuite': 'OCRA-1:HOTP-SHA256-8:QN08-PSHA1',
                'key': key32,
                'vectors': [
                    {'params': { 'Q': '00000000' }, 'result': '83238735' },
                    {'params': { 'Q': '11111111' }, 'result': '01501458' },
                    {'params': { 'Q': '22222222' }, 'result': '17957585' },
                    {'params': { 'Q': '33333333' }, 'result': '86776967' },
                    {'params': { 'Q': '44444444' }, 'result': '86807031' }
                ]
              },
              { 'ocrasuite': 'OCRA-1:HOTP-SHA512-8:C-QN08',
                'key': key64,
                'vectors': [
                    {'params': { 'C': '00000', 'Q': '00000000' }, 'result': '07016083' },
                    {'params': { 'C': '00001', 'Q': '11111111' }, 'result': '63947962' },
                    {'params': { 'C': '00002', 'Q': '22222222' }, 'result': '70123924' },
                    {'params': { 'C': '00003', 'Q': '33333333' }, 'result': '25341727' },
                    {'params': { 'C': '00004', 'Q': '44444444' }, 'result': '33203315' },
                    {'params': { 'C': '00005', 'Q': '55555555' }, 'result': '34205738' },
                    {'params': { 'C': '00006', 'Q': '66666666' }, 'result': '44343969' },
                    {'params': { 'C': '00007', 'Q': '77777777' }, 'result': '51946085' },
                    {'params': { 'C': '00008', 'Q': '88888888' }, 'result': '20403879' },
                    {'params': { 'C': '00009', 'Q': '99999999' }, 'result': '31409299' }
                ]
              },
              { 'ocrasuite': 'OCRA-1:HOTP-SHA512-8:QN08-T1M',
                'key': key64,
                'vectors': [
                    {'params': { 'Q': '00000000', 'T_precomputed': int('132d0b6', 16) },
                        'result': '95209754' },
                    {'params': { 'Q': '11111111', 'T_precomputed': int('132d0b6', 16) },
                        'result': '55907591' },
                    {'params': { 'Q': '22222222', 'T_precomputed': int('132d0b6', 16) },
                        'result': '22048402' },
                    {'params': { 'Q': '33333333', 'T_precomputed': int('132d0b6', 16) },
                        'result': '24218844' },
                    {'params': { 'Q': '44444444', 'T_precomputed': int('132d0b6', 16) },
                        'result': '36209546' },
                ]
              },
            ]

    def test_str2ocrasuite(self):
        for test in self.tests:
            ocrasuite = str2ocrasuite(test['ocrasuite'])
            key = test['key']
            for vector in test['vectors']:
                params = vector['params']
                result = vector['result']
                if ocrasuite.data_input.P:
                    params['P'] = self.pin
                self.assertEqual(ocrasuite(key, **params), result)

    mut_suite = 'OCRA-1:HOTP-SHA256-8:QA08'

    mut_tests = [{'server_ocrasuite': 'OCRA-1:HOTP-SHA256-8:QA08',
                  'client_ocrasuite': 'OCRA-1:HOTP-SHA256-8:QA08',
                  'key': key32,
                  'challenges': [{ 'params': { 'Q': 'CLI22220SRV11110' },
                        'server_result': '28247970',
                        'client_result': '15510767' },
                      { 'params': { 'Q': 'CLI22221SRV11111' },
                        'server_result': '01984843',
                        'client_result': '90175646' },
                      { 'params': { 'Q': 'CLI22222SRV11112' },
                        'server_result': '65387857',
                        'client_result': '33777207' },
                      { 'params': { 'Q': 'CLI22223SRV11113' },
                        'server_result': '03351211',
                        'client_result': '95285278' },
                      { 'params': { 'Q': 'CLI22224SRV11114' },
                        'server_result': '83412541',
                        'client_result': '28934924' },]},
                 {'server_ocrasuite': 'OCRA-1:HOTP-SHA512-8:QA08',
                  'client_ocrasuite': 'OCRA-1:HOTP-SHA512-8:QA08-PSHA1',
                  'key': key64,
                  'challenges': [{ 'params': { 'Q': 'CLI22220SRV11110' },
                        'server_result': '79496648',
                        'client_result': '18806276' },
                                 { 'params': { 'Q': 'CLI22221SRV11111' },
                        'server_result': '76831980',
                        'client_result': '70020315' },
                                 { 'params': { 'Q': 'CLI22222SRV11112' },
                        'server_result': '12250499',
                        'client_result': '01600026' },
                                 { 'params': { 'Q': 'CLI22223SRV11113' },
                        'server_result': '90856481',
                        'client_result': '18951020' },
                                 { 'params': { 'Q': 'CLI22224SRV11114' },
                        'server_result': '12761449',
                        'client_result': '32528969' },
                      ]},
                ]


    def test_mutual_challenge_response_rfc(self):
        for test in self.mut_tests:
            for server_instance in test['challenges']:
                ocra_client = OCRAMutualChallengeResponseClient(test['key'],
                        test['client_ocrasuite'], test['server_ocrasuite'])
                ocra_server = OCRAMutualChallengeResponseServer(test['key'],
                        test['server_ocrasuite'], test['client_ocrasuite'])
                Q = server_instance['params']['Q']
                qc, qs = Q[:8], Q[8:]
                # ignore computed challenge
                ocra_client.compute_client_challenge(Qc=qc)
                rs, qs = ocra_server.compute_server_response(qc, Qs=qs)
                self.assertEqual(rs, server_instance['server_result'])
                self.assertTrue(ocra_client.verify_server_response(rs, qs))
                kwargs = {}
                if ocra_client.ocrasuite.data_input.P:
                    kwargs['P'] = self.pin
                rc = ocra_client.compute_client_response(**kwargs)
                self.assertEqual(rc, server_instance['client_result'])
                self.assertTrue(ocra_server.verify_client_response(rc, **kwargs))

    def test_mutual_challenge_response_simple(self):
        ocra_client = OCRAMutualChallengeResponseClient(self.key32,
                self.mut_suite)
        ocra_server = OCRAMutualChallengeResponseServer(self.key32,
                self.mut_suite)
        qc = ocra_client.compute_client_challenge()
        rs, qs = ocra_server.compute_server_response(qc)
        self.assertTrue(ocra_client.verify_server_response(rs, qs))
        rc = ocra_client.compute_client_response()
        self.assertTrue(ocra_server.verify_client_response(rc))



########NEW FILE########
__FILENAME__ = totp
import unittest
import binascii
import hashlib

from oath import accept_totp

def parse_tv(tv):
    test_vectors  = [ [ cell.strip() for cell in line.strip(' |').split('|') ] for line in tv.splitlines()]
    test_vectors  = [ line for line in test_vectors if line[0] and len(line) > 3 ]
    return test_vectors

class Totp(unittest.TestCase):
    key_sha1 = binascii.hexlify('1234567890'*2)
    key_sha256 = binascii.hexlify('1234567890'*3+'12')
    key_sha512 = binascii.hexlify('1234567890'*6+'1234')

    tv = parse_tv('''|      59     |  1970-01-01  | 0000000000000001 | 94287082 |  SHA1  |
   |             |   00:00:59   |                  |          |        |
   |      59     |  1970-01-01  | 0000000000000001 | 46119246 | SHA256 |
   |             |   00:00:59   |                  |          |        |
   |      59     |  1970-01-01  | 0000000000000001 | 90693936 | SHA512 |
   |             |   00:00:59   |                  |          |        |
   |  1111111109 |  2005-03-18  | 00000000023523EC | 07081804 |  SHA1  |
   |             |   01:58:29   |                  |          |        |
   |  1111111109 |  2005-03-18  | 00000000023523EC | 68084774 | SHA256 |
   |             |   01:58:29   |                  |          |        |
   |  1111111109 |  2005-03-18  | 00000000023523EC | 25091201 | SHA512 |
   |             |   01:58:29   |                  |          |        |
   |  1111111111 |  2005-03-18  | 00000000023523ED | 14050471 |  SHA1  |
   |             |   01:58:31   |                  |          |        |
   |  1111111111 |  2005-03-18  | 00000000023523ED | 67062674 | SHA256 |
   |             |   01:58:31   |                  |          |        |
   |  1111111111 |  2005-03-18  | 00000000023523ED | 99943326 | SHA512 |
   |             |   01:58:31   |                  |          |        |
   |  1234567890 |  2009-02-13  | 000000000273EF07 | 89005924 |  SHA1  |
   |             |   23:31:30   |                  |          |        |
   |  1234567890 |  2009-02-13  | 000000000273EF07 | 91819424 | SHA256 |
   |             |   23:31:30   |                  |          |        |
   |  1234567890 |  2009-02-13  | 000000000273EF07 | 93441116 | SHA512 |
   |             |   23:31:30   |                  |          |        |
   |  2000000000 |  2033-05-18  | 0000000003F940AA | 69279037 |  SHA1  |
   |             |   03:33:20   |                  |          |        |
   |  2000000000 |  2033-05-18  | 0000000003F940AA | 90698825 | SHA256 |
   |             |   03:33:20   |                  |          |        |
   |  2000000000 |  2033-05-18  | 0000000003F940AA | 38618901 | SHA512 |
   |             |   03:33:20   |                  |          |        |
   | 20000000000 |  2603-10-11  | 0000000027BC86AA | 65353130 |  SHA1  |
   |             |   11:33:20   |                  |          |        |
   | 20000000000 |  2603-10-11  | 0000000027BC86AA | 77737706 | SHA256 |
   |             |   11:33:20   |                  |          |        |
   | 20000000000 |  2603-10-11  | 0000000027BC86AA | 47863826 | SHA512 |
   |             |   11:33:20   |                  |          |        |''')


    hash_algos = {
            'SHA1': {
                'key': key_sha1,
                'alg': hashlib.sha1, },
            'SHA256': {
                'key': key_sha256,
                'alg': hashlib.sha256, },
            'SHA512': {
                'key': key_sha512,
                'alg': hashlib.sha512, },
    }

    def test_totp(self):
        for t, _, _, response, algo_key in self.tv:
            algo = self.hash_algos[algo_key]
            self.assertTrue(accept_totp(algo['key'], response, t=int(t),
                hash=algo['alg'], format='dec8'))

########NEW FILE########
