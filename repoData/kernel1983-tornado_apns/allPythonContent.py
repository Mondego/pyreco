__FILENAME__ = apns
# PyAPNs was developed by Simon Whitaker <simon@goosoftware.co.uk>
# Source available at https://github.com/simonwhitaker/PyAPNs
#
# PyAPNs is distributed under the terms of the MIT license.
#
# Copyright (c) 2011 Goo Software Ltd
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from binascii import a2b_hex, b2a_hex
import time
from socket import socket, AF_INET, SOCK_STREAM
from struct import pack, unpack
import functools

try:
    from ssl import wrap_socket
except ImportError:
    from socket import ssl as wrap_socket

try:
    import json
except ImportError:
    import simplejson as json

from tornado import iostream
from tornado import ioloop

MAX_PAYLOAD_LENGTH = 256
TIME_OUT = 20

class APNs(object):
    """A class representing an Apple Push Notification service connection"""

    def __init__(self, use_sandbox=False, cert_file=None, key_file=None):
        """
        Set use_sandbox to True to use the sandbox (test) APNs servers.
        Default is False.
        """
        super(APNs, self).__init__()
        self.use_sandbox = use_sandbox
        self.cert_file = cert_file
        self.key_file = key_file
        self._feedback_connection = None
        self._gateway_connection = None

    @staticmethod
    def packed_uchar(num):
        """
        Returns an unsigned char in packed form
        """
        return pack('>B', num)

    @staticmethod
    def unpacked_uchar(bytes):
        """
        Returns an unsigned char from a packed (network) byte
        """
        return unpack('>B', bytes)[0]

    @staticmethod
    def packed_ushort_big_endian(num):
        """
        Returns an unsigned short in packed big-endian (network) form
        """
        return pack('>H', num)

    @staticmethod
    def unpacked_ushort_big_endian(bytes):
        """
        Returns an unsigned short from a packed big-endian (network) byte
        array
        """
        return unpack('>H', bytes)[0]

    @staticmethod
    def packed_uint_big_endian(num):
        """
        Returns an unsigned int in packed big-endian (network) form
        """
        return pack('>I', num)

    @staticmethod
    def unpacked_uint_big_endian(bytes):
        """
        Returns an unsigned int from a packed big-endian (network) byte array
        """
        return unpack('>I', bytes)[0]

    @property
    def feedback_server(self):
        if not self._feedback_connection:
            self._feedback_connection = FeedbackConnection(
                use_sandbox = self.use_sandbox,
                cert_file = self.cert_file,
                key_file = self.key_file
            )
        return self._feedback_connection

    @property
    def gateway_server(self):
        if not self._gateway_connection:
            self._gateway_connection = GatewayConnection(
                use_sandbox = self.use_sandbox,
                cert_file = self.cert_file,
                key_file = self.key_file
            )
        return self._gateway_connection


class APNsConnection(object):
    """
    A generic connection class for communicating with the APNs
    """
    def __init__(self, cert_file=None, key_file=None):
        super(APNsConnection, self).__init__()
        self.cert_file = cert_file
        self.key_file = key_file
        self._socket = None
        self._ssl = None
        self._stream = None
        self._alive = False
        self._connecting = False
        self._connect_timeout = None

    def __del__(self):
        if self._stream:
            self._stream.close()
    
    def is_alive(self):
        return self._alive

    def is_connecting(self):
        return self._connecting

    def connect(self, callback):
        # Establish an SSL connection
        if not self._connecting:
            self._connecting = True
            _ioloop = ioloop.IOLoop.instance()
            self._connect_timeout = _ioloop.add_timeout(time.time()+TIME_OUT,
                    self._connecting_timeout_callback)
            self._socket = socket(AF_INET, SOCK_STREAM)
            self._stream = iostream.SSLIOStream(socket=self._socket, ssl_options={"keyfile": self.key_file, "certfile": self.cert_file})
            self._stream.connect((self.server, self.port),
                    functools.partial(self._on_connected, callback))

    def _connecting_timeout_callback(self):
        if not self.is_alive():
            self._connecting = False
            self.disconnect()
            raise ConnectionError('connect timeout')

    def _on_connected(self, callback):
        ioloop.IOLoop.instance().remove_timeout(self._connect_timeout)
        self._alive = True
        self._connecting = False
        callback()

    def disconnect(self):
        self._alive = False
        self._stream.close()

    def set_close_callback(self, callback):
        self._stream.set_close_callback(callback)

    def read(self, n, callback):
        try:
            self._stream.read_bytes(n, callback)
        except (AttributeError, IOError) as e:
            self.disconnect()
            raise ConnectionError('%s' % e)

    def read_till_close(self, callback):
        try:
            self._stream.read_until_close(callback=callback, streaming_callback=callback)
        except (AttributeError, IOError) as e:
            self.disconnect()
            raise ConnectionError('%s' % e)

    def write(self, string, callback):
        try:
            self._stream.write(string, callback)
        except (AttributeError, IOError) as e:
            self.disconnect()
            raise ConnectionError('%s' % e)


class PayloadAlert(object):
    def __init__(self, body, action_loc_key=None, loc_key=None,
                 loc_args=None, launch_image=None):
        super(PayloadAlert, self).__init__()
        self.body = body
        self.action_loc_key = action_loc_key
        self.loc_key = loc_key
        self.loc_args = loc_args
        self.launch_image = launch_image

    def dict(self):
        d = { 'body': self.body }
        if self.action_loc_key:
            d['action-loc-key'] = self.action_loc_key
        if self.loc_key:
            d['loc-key'] = self.loc_key
        if self.loc_args:
            d['loc-args'] = self.loc_args
        if self.launch_image:
            d['launch-image'] = self.launch_image
        return d

class PayloadTooLargeError(Exception):
    def __init__(self):
        super(PayloadTooLargeError, self).__init__()

class TokenLengthOddError(Exception):
    pass

class ConnectionError(Exception):
    pass

class Payload(object):
    """A class representing an APNs message payload"""
    def __init__(self, alert=None, badge=None, sound=None, custom={}):
        super(Payload, self).__init__()
        self.alert = alert
        self.badge = badge
        self.sound = sound
        self.custom = custom
        self._check_size()

    def dict(self):
        """Returns the payload as a regular Python dictionary"""
        d = {}
        if self.alert:
            # Alert can be either a string or a PayloadAlert
            # object
            if isinstance(self.alert, PayloadAlert):
                d['alert'] = self.alert.dict()
            else:
                d['alert'] = self.alert
        if self.sound:
            d['sound'] = self.sound
        if self.badge is not None:
            d['badge'] = int(self.badge)

        d = { 'aps': d }
        d.update(self.custom)
        return d

    def json(self):
        return json.dumps(self.dict(), separators=(',',':'), ensure_ascii=False).encode('utf-8')

    def _check_size(self):
        if len(self.json()) > MAX_PAYLOAD_LENGTH:
            raise PayloadTooLargeError()

    def __repr__(self):
        attrs = ("alert", "badge", "sound", "custom")
        args = ", ".join(["%s=%r" % (n, getattr(self, n)) for n in attrs])
        return "%s(%s)" % (self.__class__.__name__, args)


class FeedbackConnection(APNsConnection):
    """
    A class representing a connection to the APNs Feedback server
    """
    def __init__(self, use_sandbox=False, **kwargs):
        super(FeedbackConnection, self).__init__(**kwargs)
        self.server = (
            'feedback.push.apple.com',
            'feedback.sandbox.push.apple.com')[use_sandbox]
        self.port = 2196
        self.buff =''

    def __del__(self):
        super(FeedbackConnection, self).__del__()

    def receive_feedback(self, callback):
        self.read_till_close(functools.partial(self._feedback_callback, callback))

    def _feedback_callback(self, callback, data):

        self.buff += data

        if len(self.buff) < 6:
            return

        while len(self.buff) > 6:
            token_length = APNs.unpacked_ushort_big_endian(self.buff[4:6])
            bytes_to_read = 6 + token_length
            if len(self.buff) >= bytes_to_read:
                fail_time_unix = APNs.unpacked_uint_big_endian(self.buff[0:4])
                token = b2a_hex(self.buff[6:bytes_to_read])

                callback(token, fail_time_unix)

                # Remove data for current token from buffer
                self.buff = self.buff[bytes_to_read:]
            else:
                return
 
class GatewayConnection(APNsConnection):
    """
    A class that represents a connection to the APNs gateway server
    """
    def __init__(self, use_sandbox=False, **kwargs):
        super(GatewayConnection, self).__init__(**kwargs)
        self.server = (
            'gateway.push.apple.com',
            'gateway.sandbox.push.apple.com')[use_sandbox]
        self.port = 2195

    def __del__(self):
        super(GatewayConnection, self).__del__()

    def _get_notification(self, identifier, expiry, token_hex, payload):
        """
        Takes a token as a hex string and a payload as a Python dict and sends
        the notification
        """
        try:
            token_bin = a2b_hex(token_hex)
        except TypeError as e:
            raise TokenLengthOddError("Token Length is Odd")
        token_length_bin = APNs.packed_ushort_big_endian(len(token_bin))
        identifier_bin = APNs.packed_uint_big_endian(identifier)
        expiry = APNs.packed_uint_big_endian(expiry)
        if isinstance(payload, Payload):
            payload_json = payload.json()
        else:
            payload_json = payload
        payload_length_bin = APNs.packed_ushort_big_endian(len(payload_json))

        notification = ('\1' + identifier_bin + expiry + token_length_bin + token_bin
            + payload_length_bin + payload_json)

        return notification
    
    def send_notification(self, identifier, expiry, token_hex, payload, callback):
        self.write(self._get_notification(identifier, expiry, token_hex, payload), callback)

    def receive_response(self, callback):
        '''
        receive the error response, return the error status and seq id
        '''
        def _read_response_call(callback, data):
            command = APNs.unpacked_uchar(data[0])
            status = APNs.unpacked_uchar(data[1])
            seq = APNs.unpacked_uint_big_endian(data[2:6])
            callback(status, seq)

        self.read(6, functools.partial(_read_response_call,callback))

########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/env python
# coding: utf-8
from apns import *
from binascii import a2b_hex
from random import random

import hashlib
import os
import time
import unittest

TEST_CERTIFICATE = "certificate.pem" # replace with path to test certificate


class TestAPNs(unittest.TestCase):
    """Unit tests for PyAPNs"""

    def setUp(self):
        """docstring for setUp"""
        pass

    def tearDown(self):
        """docstring for tearDown"""
        pass

    def testConfigs(self):
        apns_test = APNs(use_sandbox=True)
        apns_prod = APNs(use_sandbox=False)

        self.assertEqual(apns_test.gateway_server.port, 2195)
        self.assertEqual(apns_test.gateway_server.server,
            'gateway.sandbox.push.apple.com')
        self.assertEqual(apns_test.feedback_server.port, 2196)
        self.assertEqual(apns_test.feedback_server.server,
            'feedback.sandbox.push.apple.com')

        self.assertEqual(apns_prod.gateway_server.port, 2195)
        self.assertEqual(apns_prod.gateway_server.server,
            'gateway.push.apple.com')
        self.assertEqual(apns_prod.feedback_server.port, 2196)
        self.assertEqual(apns_prod.feedback_server.server,
            'feedback.push.apple.com')

    def testGatewayServer(self):
        pem_file = TEST_CERTIFICATE
        apns = APNs(use_sandbox=True, cert_file=pem_file, key_file=pem_file)
        gateway_server = apns.gateway_server

        self.assertEqual(gateway_server.cert_file, apns.cert_file)
        self.assertEqual(gateway_server.key_file, apns.key_file)

        identifier = 1
        expiry = 3600
        token_hex = 'b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c'
        payload   = Payload(
            alert = "Hello World!",
            sound = "default",
            badge = 4
        )
        notification = gateway_server._get_notification(identifier, expiry, token_hex, payload)

        expected_length = (
            1                       # leading null byte
            + 4                     # length of identifier as a packed ushort
            + 4                     # length of expiry time as a packed ushort
            + 2                     # length of token as a packed short
            + len(token_hex) / 2    # length of token as binary string
            + 2                     # length of payload as a packed short
            + len(payload.json())   # length of JSON-formatted payload
        )

        self.assertEqual(len(notification), expected_length)
        self.assertEqual(notification[0], '\1')

    def testFeedbackServer(self):
        pem_file = TEST_CERTIFICATE
        apns = APNs(use_sandbox=True, cert_file=pem_file, key_file=pem_file)
        feedback_server = apns.feedback_server

        self.assertEqual(feedback_server.cert_file, apns.cert_file)
        self.assertEqual(feedback_server.key_file, apns.key_file)
        
        token_hex = hashlib.sha256("%.12f" % random()).hexdigest()
        token_bin       = a2b_hex(token_hex)
        token_length    = len(token_bin)
        now_time = int(time.time())
        data = ''
        data += APNs.packed_uint_big_endian(now_time)
        data += APNs.packed_ushort_big_endian(token_length)
        data += token_bin

        def test_callback(token, fail_time):
            self.assertEqual(token, token_hex)
            self.assertEqual(fail_time, now_time)

        feedback_server._feedback_callback(test_callback, data)

    def testPayloadAlert(self):
        pa = PayloadAlert('foo')
        d = pa.dict()
        self.assertEqual(d['body'], 'foo')
        self.assertFalse('action-loc-key' in d)
        self.assertFalse('loc-key' in d)
        self.assertFalse('loc-args' in d)
        self.assertFalse('launch-image' in d)

        pa = PayloadAlert('foo', action_loc_key='bar', loc_key='wibble',
            loc_args=['king','kong'], launch_image='wobble')
        d = pa.dict()
        self.assertEqual(d['body'], 'foo')
        self.assertEqual(d['action-loc-key'], 'bar')
        self.assertEqual(d['loc-key'], 'wibble')
        self.assertEqual(d['loc-args'], ['king','kong'])
        self.assertEqual(d['launch-image'], 'wobble')

    def testPayload(self):
        # Payload with just alert
        p = Payload(alert=PayloadAlert('foo'))
        d = p.dict()
        self.assertTrue('alert' in d['aps'])
        self.assertTrue('sound' not in d['aps'])
        self.assertTrue('badge' not in d['aps'])

        # Payload with just sound
        p = Payload(sound="foo")
        d = p.dict()
        self.assertTrue('sound' in d['aps'])
        self.assertTrue('alert' not in d['aps'])
        self.assertTrue('badge' not in d['aps'])

        # Payload with just badge
        p = Payload(badge=1)
        d = p.dict()
        self.assertTrue('badge' in d['aps'])
        self.assertTrue('alert' not in d['aps'])
        self.assertTrue('sound' not in d['aps'])

        # Payload with just badge removal
        p = Payload(badge=0)
        d = p.dict()
        self.assertTrue('badge' in d['aps'])
        self.assertTrue('alert' not in d['aps'])
        self.assertTrue('sound' not in d['aps'])

        # Test plain string alerts
        alert_str = 'foobar'
        p = Payload(alert=alert_str)
        d = p.dict()
        self.assertEqual(d['aps']['alert'], alert_str)
        self.assertTrue('sound' not in d['aps'])
        self.assertTrue('badge' not in d['aps'])

        # Test custom payload
        alert_str = 'foobar'
        custom_dict = {'foo': 'bar'}
        p = Payload(alert=alert_str, custom=custom_dict)
        d = p.dict()
        self.assertEqual(d, {'foo': 'bar', 'aps': {'alert': 'foobar'}})


    def testPayloadTooLargeError(self):
        # The maximum size of the JSON payload is MAX_PAYLOAD_LENGTH 
        # bytes. First determine how many bytes this allows us in the
        # raw payload (i.e. before JSON serialisation)
        json_overhead_bytes = len(Payload('.').json()) - 1
        max_raw_payload_bytes = MAX_PAYLOAD_LENGTH - json_overhead_bytes

        # Test ascii characters payload
        Payload('.' * max_raw_payload_bytes)
        self.assertRaises(PayloadTooLargeError, Payload, 
            '.' * (max_raw_payload_bytes + 1))

        # Test unicode 2-byte characters payload
        Payload(u'\u0100' * int(max_raw_payload_bytes / 2))
        self.assertRaises(PayloadTooLargeError, Payload,
            u'\u0100' * (int(max_raw_payload_bytes / 2) + 1))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
