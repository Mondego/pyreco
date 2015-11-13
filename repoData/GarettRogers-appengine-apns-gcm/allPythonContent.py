__FILENAME__ = admin
#!/usr/bin/env python
# appengine-apns-gcm was developed by Garett Rogers <garett.rogers@gmail.com>
# Source available at https://github.com/GarettRogers/appengine-apns-gcm
#
# appengine-apns-gcm is distributed under the terms of the MIT license.
#
# Copyright (c) 2013 AimX Labs
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

import webapp2
import os
from google.appengine.ext.webapp import template
from google.appengine.ext import ndb
from gcmdata import *
from gcm import *
from apns import *
from apnsdata import *
from appdata import *

appconfig = None

class ConfigureApp(webapp2.RequestHandler):
    def get(self):
        appconfig = AppConfig.get_or_insert("config")
        
        if not appconfig.gcm_api_key:
            appconfig.gcm_api_key = "<gcm key here>"
        if not appconfig.gcm_multicast_limit:
            appconfig.gcm_multicast_limit = 1000
        if not appconfig.apns_multicast_limit:
            appconfig.apns_multicast_limit = 1000
        if appconfig.apns_test_mode == None:
            appconfig.apns_test_mode = True
        if not appconfig.apns_sandbox_cert:
            appconfig.apns_sandbox_cert = "<sandbox pem certificate string>"
        if not appconfig.apns_sandbox_key:
            appconfig.apns_sandbox_key = "<sandbox pem private key string>"
        if not appconfig.apns_cert:
            appconfig.apns_cert = "<pem certificate string>"
        if not appconfig.apns_key:
            appconfig.apns_key = "<pem private key string>"
        
        appconfig.put()
        
        template_values = {
            'appconfig': appconfig,
        }
        path = os.path.join(os.path.dirname(__file__), 'config.html')
        self.response.out.write(template.render(path, template_values))
    
    def post(self):
        appconfig = AppConfig.get_or_insert("config")
        appconfig.gcm_api_key = self.request.get("gcm_api_key")
        appconfig.gcm_multicast_limit = int(self.request.get("gcm_multicast_limit"))
        appconfig.apns_multicast_limit = int(self.request.get("apns_multicast_limit"))
        appconfig.apns_sandbox_cert = self.request.get("apns_sandbox_cert")
        appconfig.apns_sandbox_key = self.request.get("apns_sandbox_key")
        appconfig.apns_cert = self.request.get("apns_cert")
        appconfig.apns_key = self.request.get("apns_key")
        
        if self.request.get("apns_test_mode") == "True":
            appconfig.apns_test_mode = True
        else:
            appconfig.apns_test_mode = False
        
        appconfig.put()
        
        template_values = {
            'appconfig': appconfig,
        }
        path = os.path.join(os.path.dirname(__file__), 'config.html')
        self.response.out.write(template.render(path, template_values))



app = webapp2.WSGIApplication([
    ('/admin/config', ConfigureApp)
], debug=True)

########NEW FILE########
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
from datetime import datetime
from socket import socket, AF_INET, SOCK_STREAM
from struct import pack, unpack
import StringIO

try:
    from ssl import wrap_socket
except ImportError:
    from socket import ssl as wrap_socket

try:
    import json
except ImportError:
    import simplejson as json

MAX_PAYLOAD_LENGTH = 256

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
    
    def __del__(self):
        self._disconnect();
    
    def _connect(self):
        # Establish an SSL connection
        self._socket = socket(AF_INET, SOCK_STREAM)
        self._socket.connect((self.server, self.port))
        self._ssl = wrap_socket(self._socket, server_side=False, keyfile=StringIO.StringIO(self.key_file), certfile=StringIO.StringIO(self.cert_file))
    
    def _disconnect(self):
        if self._socket:
            self._socket.close()
    
    def _connection(self):
        if not self._ssl:
            self._connect()
        return self._ssl
    
    def read(self, n=None):
        return self._connection().read(n)
    
    def write(self, string):
        return self._connection().write(string)


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
    
    def _chunks(self):
        BUF_SIZE = 4096
        while 1:
            data = self.read(BUF_SIZE)
            yield data
            if not data:
                break
    
    def items(self):
        """
            A generator that yields (token_hex, fail_time) pairs retrieved from
            the APNs feedback server
            """
        buff = ''
        for chunk in self._chunks():
            buff += chunk
            
            # Quit if there's no more data to read
            if not buff:
                break
            
            # Sanity check: after a socket read we should always have at least
            # 6 bytes in the buffer
            if len(buff) < 6:
                break
            
            while len(buff) > 6:
                token_length = APNs.unpacked_ushort_big_endian(buff[4:6])
                bytes_to_read = 6 + token_length
                if len(buff) >= bytes_to_read:
                    fail_time_unix = APNs.unpacked_uint_big_endian(buff[0:4])
                    fail_time = datetime.utcfromtimestamp(fail_time_unix)
                    token = b2a_hex(buff[6:bytes_to_read])
                    
                    yield (token, fail_time)
                    
                    # Remove data for current token from buffer
                    buff = buff[bytes_to_read:]
                else:
                    # break out of inner while loop - i.e. go and fetch
                    # some more data and append to buffer
                    break

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
    
    def _get_notification(self, token_hex, payload):
        """
            Takes a token as a hex string and a payload as a Python dict and sends
            the notification
            """
        token_bin = a2b_hex(token_hex)
        token_length_bin = APNs.packed_ushort_big_endian(len(token_bin))
        payload_json = payload.json()
        payload_length_bin = APNs.packed_ushort_big_endian(len(payload_json))
        
        notification = ('\0' + token_length_bin + token_bin
                        + payload_length_bin + payload_json)
        
        return notification
    
    def send_notification(self, token_hex, payload):
        self.write(self._get_notification(token_hex, payload))

    def send_notifications(self, tokens, payload):
        for token in tokens:
            self.write(self._get_notification(token, payload))
########NEW FILE########
__FILENAME__ = apnsdata
import json
import logging
import time
import uuid
from google.appengine.api import memcache
from google.appengine.ext import ndb

class ApnsToken(ndb.Model):
    apns_token = ndb.StringProperty(indexed=True)
    enabled = ndb.BooleanProperty(indexed=True, default=True)
    registration_date = ndb.DateTimeProperty(indexed=False, auto_now_add=True)

class ApnsSandboxToken(ndb.Model):
    apns_token = ndb.StringProperty(indexed=True)
    enabled = ndb.BooleanProperty(indexed=True, default=True)
    registration_date = ndb.DateTimeProperty(indexed=False, auto_now_add=True)

class ApnsTag(ndb.Model):
    token = ndb.KeyProperty(kind=ApnsToken)
    tag = ndb.StringProperty(indexed=True, required=True)

class ApnsSandboxTag(ndb.Model):
    token = ndb.KeyProperty(kind=ApnsSandboxToken)
    tag = ndb.StringProperty(indexed=True, required=True)


########NEW FILE########
__FILENAME__ = apnsmodule
#!/usr/bin/env python
# appengine-apns-gcm was developed by Garett Rogers <garett.rogers@gmail.com>
# Source available at https://github.com/GarettRogers/appengine-apns-gcm
#
# appengine-apns-gcm is distributed under the terms of the MIT license.
#
# Copyright (c) 2013 AimX Labs
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

import webapp2
import os
from google.appengine.ext.webapp import template
from google.appengine.ext import ndb
from gcmdata import *
from gcm import *
from apns import *
from apnsdata import *
from appdata import *

appconfig = None

def GetApnsToken(regid):
    appconfig = AppConfig.get_or_insert("config")
    if appconfig.apns_test_mode:
        return ApnsSandboxToken.get_or_insert(regid)
    else:
        return ApnsToken.get_or_insert(regid)

class APNSRegister(webapp2.RequestHandler):
    def post(self):
        regid = self.request.get('regId')
        if not regid:
            self.response.out.write('Must specify regid')
        else:
            #Store registration_id and an unique key_name with email value
            token = GetApnsToken(regid)
            token.apns_token = regid
            token.enabled = True
            token.put()

class APNSUnregister(webapp2.RequestHandler):
    def post(self):
        regid = self.request.get('regId')
        if not regId:
            self.response.out.write('Must specify regid')
        else:
            token = GetApnsToken(regid)
            token.enabled = False
            token.put()

class APNSTagHandler(webapp2.RequestHandler):
    def post(self):
        tagid = self.request.get("tagid")
        regid = self.request.get("regid")
            
        appconfig = AppConfig.get_or_insert("config")
            
        if appconfig.apns_test_mode:
            token = GetApnsToken(regid)
            sandboxtag = ApnsSandboxTag.get_or_insert(tagid + regid, tag=tagid, token=token.key)

        else:
            token = GetApnsToken(regid)
            prodtag = ApnsTag.get_or_insert(tagid + regid, tag=tagid, token=token.key)
            
                
    def delete(self):
        tagid = self.request.get("tagid")
        regid = self.request.get("regid")

        appconfig = AppConfig.get_or_insert("config")
        
        if appconfig.apns_test_mode:
            sandboxtag = ApnsSandboxTag.get_or_insert(tagid + regid)
            sandboxtag.key.delete()
        
        else:
            prodtag = ApnsTag.get_or_insert(tagid + regid)
            prodtag.key.delete()

app = webapp2.WSGIApplication([
    ('/apns/tag', APNSTagHandler),
    ('/apns/register', APNSRegister),
    ('/apns/unregister', APNSUnregister)
], debug=True)

########NEW FILE########
__FILENAME__ = appdata
import json
import logging
import time
import uuid
from google.appengine.api import memcache
from google.appengine.ext import ndb

class AppConfig(ndb.Model):
    gcm_api_key = ndb.StringProperty()
    gcm_multicast_limit = ndb.IntegerProperty()
    apns_multicast_limit = ndb.IntegerProperty()
    apns_test_mode = ndb.BooleanProperty()
    apns_sandbox_cert = ndb.TextProperty()
    apns_sandbox_key = ndb.TextProperty()
    apns_cert = ndb.TextProperty()
    apns_key = ndb.TextProperty()
    
########NEW FILE########
__FILENAME__ = gcm
#Source available at https://github.com/geeknam/python-gcm
#
# PyAPNs is distributed under the terms of the MIT license.
#
# Copyright (c) 2012 Minh Nam Ngo.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import urllib
import urllib2
import json
from collections import defaultdict
import time
import random

GCM_URL = 'https://android.googleapis.com/gcm/send'


class GCMException(Exception): pass
class GCMMalformedJsonException(GCMException): pass
class GCMConnectionException(GCMException): pass
class GCMAuthenticationException(GCMException): pass
class GCMTooManyRegIdsException(GCMException): pass
class GCMNoCollapseKeyException(GCMException): pass
class GCMInvalidTtlException(GCMException): pass

# Exceptions from Google responses
class GCMMissingRegistrationException(GCMException): pass
class GCMMismatchSenderIdException(GCMException): pass
class GCMNotRegisteredException(GCMException): pass
class GCMMessageTooBigException(GCMException): pass
class GCMInvalidRegistrationException(GCMException): pass
class GCMUnavailableException(GCMException): pass


# TODO: Refactor this to be more human-readable
def group_response(response, registration_ids, key):
    # Pair up results and reg_ids
    mapping = zip(registration_ids, response['results'])
    # Filter by key
    filtered = filter(lambda x: key in x[1], mapping)
    # Only consider the value in the dict
    tupled = [(s[0], s[1][key]) for s in filtered]
    # Grouping of errors and mapping of ids
    if key is 'registration_id':
        grouping = {}
        for k, v in tupled:
            grouping[k] = v
    else:
        grouping = defaultdict(list)
        for k, v in tupled:
            grouping[v].append(k)
    
    if len(grouping) == 0:
        return
    return grouping


class GCM(object):
    
    # Timeunit is milliseconds.
    BACKOFF_INITIAL_DELAY = 1000;
    MAX_BACKOFF_DELAY = 1024000;
    
    def __init__(self, api_key, url=GCM_URL, proxy=None):
        """ api_key : google api key
            url: url of gcm service.
            proxy: can be string "http://host:port" or dict {'https':'host:port'}
            """
        self.api_key = api_key
        self.url = url
        if proxy:
            if isinstance(proxy,basestring):
                protocol = url.split(':')[0]
                proxy={protocol:proxy}
            
            auth = urllib2.HTTPBasicAuthHandler()
            opener = urllib2.build_opener(urllib2.ProxyHandler(proxy), auth, urllib2.HTTPHandler)
            urllib2.install_opener(opener)
    
    
    def construct_payload(self, registration_ids, data=None, collapse_key=None,
                          delay_while_idle=False, time_to_live=None, is_json=True):
        """
            Construct the dictionary mapping of parameters.
            Encodes the dictionary into JSON if for json requests.
            Helps appending 'data.' prefix to the plaintext data: 'hello' => 'data.hello'
            
            :return constructed dict or JSON payload
            :raises GCMInvalidTtlException: if time_to_live is invalid
            :raises GCMNoCollapseKeyException: if collapse_key is missing when time_to_live is used
            """
        
        if time_to_live:
            if time_to_live > 2419200 or time_to_live < 0:
                raise GCMInvalidTtlException("Invalid time to live value")
        
        if is_json:
            payload = {'registration_ids': registration_ids}
            if data:
                payload['data'] = data
        else:
            payload = {'registration_id': registration_ids}
            if data:
                for k in data.keys():
                    data['data.%s' % k] = data.pop(k)
                payload.update(data)
        
        if delay_while_idle:
            payload['delay_while_idle'] = delay_while_idle
        
        if time_to_live:
            payload['time_to_live'] = time_to_live
            if collapse_key is None:
                raise GCMNoCollapseKeyException("collapse_key is required when time_to_live is provided")
        
        if collapse_key:
            payload['collapse_key'] = collapse_key
        
        if is_json:
            payload = json.dumps(payload)
        
        return payload
    
    def make_request(self, data, is_json=True):
        """
            Makes a HTTP request to GCM servers with the constructed payload
            
            :param data: return value from construct_payload method
            :raises GCMMalformedJsonException: if malformed JSON request found
            :raises GCMAuthenticationException: if there was a problem with authentication, invalid api key
            :raises GCMConnectionException: if GCM is screwed
            """
        
        headers = {
            'Authorization': 'key=%s' % self.api_key,
        }
        # Default Content-Type is defaulted to application/x-www-form-urlencoded;charset=UTF-8
        if is_json:
            headers['Content-Type'] = 'application/json'
        
        if not is_json:
            data = urllib.urlencode(data)
        req = urllib2.Request(self.url, data, headers)
        
        try:
            response = urllib2.urlopen(req).read()
        except urllib2.HTTPError as e:
            if e.code == 400:
                raise GCMMalformedJsonException("The request could not be parsed as JSON")
            elif e.code == 401:
                raise GCMAuthenticationException("There was an error authenticating the sender account")
            elif e.code == 503:
                raise GCMUnavailableException("GCM service is unavailable")
            else:
                error = "GCM service error: %d" % e.code
                raise GCMUnavailableException(error)
        except urllib2.URLError as e:
            raise GCMConnectionException("There was an internal error in the GCM server while trying to process the request")
        
        if is_json:
            response = json.loads(response)
        return response
    
    def raise_error(self, error):
        if error == 'InvalidRegistration':
            raise GCMInvalidRegistrationException("Registration ID is invalid")
        elif error == 'Unavailable':
            # Plain-text requests will never return Unavailable as the error code.
            # http://developer.android.com/guide/google/gcm/gcm.html#error_codes
            raise GCMUnavailableException("Server unavailable. Resent the message")
        elif error == 'NotRegistered':
            raise GCMNotRegisteredException("Registration id is not valid anymore")
        elif error == 'MismatchSenderId':
            raise GCMMismatchSenderIdException("A Registration ID is tied to a certain group of senders")
        elif error == 'MessageTooBig':
            raise GCMMessageTooBigException("Message can't exceed 4096 bytes")
    
    def handle_plaintext_response(self, response):
        
        # Split response by line
        response_lines = response.strip().split('\n')
        # Split the first line by =
        key, value = response_lines[0].split('=')
        if key == 'Error':
            self.raise_error(value)
        else:
            if len(response_lines) == 2:
                return response_lines[1].split('=')[1]
            else:
                return
    
    def handle_json_response(self, response, registration_ids):
        errors = group_response(response, registration_ids, 'error')
        canonical = group_response(response, registration_ids, 'registration_id')
        
        info = {}
        if errors:
            info.update({'errors': errors})
        if canonical:
            info.update({'canonical': canonical})
        
        return info
    
    def extract_unsent_reg_ids(self, info):
        if 'errors' in info and 'Unavailable' in info['errors']:
            return info['errors']['Unavailable']
        else:
            return []
    
    def plaintext_request(self, registration_id, data=None, collapse_key=None,
                          delay_while_idle=False, time_to_live=None, retries=5):
        """
            Makes a plaintext request to GCM servers
            
            :param registration_id: string of the registration id
            :param data: dict mapping of key-value pairs of messages
            :return dict of response body from Google including multicast_id, success, failure, canonical_ids, etc
            :raises GCMMissingRegistrationException: if registration_id is not provided
            """
        
        if not registration_id:
            raise GCMMissingRegistrationException("Missing registration_id")
        
        payload = self.construct_payload(
                                         registration_id, data, collapse_key,
                                         delay_while_idle, time_to_live, False
                                         )
        
        attempt = 0
        backoff = self.BACKOFF_INITIAL_DELAY
        for attempt in range(retries):
            try:
                response = self.make_request(payload, is_json=False)
                return self.handle_plaintext_response(response)
            except GCMUnavailableException:
                sleep_time = backoff / 2 + random.randrange(backoff)
                time.sleep(float(sleep_time) / 1000)
                if 2 * backoff < self.MAX_BACKOFF_DELAY:
                    backoff *= 2
        
        raise IOError("Could not make request after %d attempts" % attempt)
    
    def json_request(self, registration_ids, data=None, collapse_key=None,
                     delay_while_idle=False, time_to_live=None, retries=5):
        """
            Makes a JSON request to GCM servers
            
            :param registration_ids: list of the registration ids
            :param data: dict mapping of key-value pairs of messages
            :return dict of response body from Google including multicast_id, success, failure, canonical_ids, etc
            :raises GCMMissingRegistrationException: if the list of registration_ids exceeds 1000 items
            """
        
        if not registration_ids:
            raise GCMMissingRegistrationException("Missing registration_ids")
        if len(registration_ids) > 1000:
            raise GCMTooManyRegIdsException("Exceded number of registration_ids")
        
        attempt = 0
        backoff = self.BACKOFF_INITIAL_DELAY
        for attempt in range(retries):
            payload = self.construct_payload(
                                             registration_ids, data, collapse_key,
                                             delay_while_idle, time_to_live
                                             )
            response = self.make_request(payload, is_json=True)
            info = self.handle_json_response(response, registration_ids)
            
            unsent_reg_ids = self.extract_unsent_reg_ids(info)
            if unsent_reg_ids:
                registration_ids = unsent_reg_ids
                sleep_time = backoff / 2 + random.randrange(backoff)
                time.sleep(float(sleep_time) / 1000)
                if 2 * backoff < self.MAX_BACKOFF_DELAY:
                    backoff *= 2
            else:
                break
        
        return info
########NEW FILE########
__FILENAME__ = gcmdata
import json
import logging
import time
import uuid
from google.appengine.api import memcache
from google.appengine.ext import ndb

class GcmToken(ndb.Model):
    gcm_token = ndb.StringProperty(indexed=True)
    enabled = ndb.BooleanProperty(indexed=True, default=True)
    registration_date = ndb.DateTimeProperty(indexed=False, auto_now_add=True)

class GcmTag(ndb.Model):
    token = ndb.KeyProperty(kind=GcmToken)
    tag = ndb.StringProperty(indexed=True, required=True)


########NEW FILE########
__FILENAME__ = gcmmodule
#!/usr/bin/env python
# appengine-apns-gcm was developed by Garett Rogers <garett.rogers@gmail.com>
# Source available at https://github.com/GarettRogers/appengine-apns-gcm
#
# appengine-apns-gcm is distributed under the terms of the MIT license.
#
# Copyright (c) 2013 AimX Labs
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

import webapp2
import os
from google.appengine.ext.webapp import template
from google.appengine.ext import ndb
from gcmdata import *
from gcm import *
from apns import *
from apnsdata import *
from appdata import *

appconfig = None

class GCMRegister(webapp2.RequestHandler):
    def post(self):
        regid = self.request.get("regId")
        if not regid:
            self.response.out.write('Must specify regid')
        else:
            token = GcmToken.get_or_insert(regid)
            token.gcm_token = regid
            token.enabled = True
            token.put()

class GCMUnregister(webapp2.RequestHandler):
    def post(self):
        regid = self.request.get("regId")
        token = GcmToken.get_or_insert(regid)
        token.enabled = False
        token.put()

class GCMTagHandler(webapp2.RequestHandler):
    def post(self):
        tagid = self.request.get("tagid")
        regid = self.request.get("regid")
        
        appconfig = AppConfig.get_or_insert("config")
        
        token = GcmToken.get_or_insert(regid)
        tag = GcmTag.get_or_insert(tagid + regid, tag=tagid, token=token.key)
    
    
    def delete(self):
        tagid = self.request.get("tagid")
        regid = self.request.get("regid")
        
        appconfig = AppConfig.get_or_insert("config")
        
        tag = GcmTag.get_or_insert(tagid + regid)
        tag.key.delete()

app = webapp2.WSGIApplication([
    ('/gcm/tag', GCMTagHandler),
    ('/gcm/register', GCMRegister),
    ('/gcm/unregister', GCMUnregister)
], debug=True)

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
# appengine-apns-gcm was developed by Garett Rogers <garett.rogers@gmail.com>
# Source available at https://github.com/GarettRogers/appengine-apns-gcm
#
# appengine-apns-gcm is distributed under the terms of the MIT license.
#
# Copyright (c) 2013 AimX Labs
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

import webapp2
import os
from google.appengine.ext.webapp import template
from google.appengine.ext import ndb
from gcmdata import *
from gcm import *
from apns import *
from apnsdata import *
from appdata import *

class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.response.write('Nothing to see here!')

app = webapp2.WSGIApplication([
    ('/', MainHandler)
], debug=True)

########NEW FILE########
__FILENAME__ = push
#!/usr/bin/env python
# appengine-apns-gcm was developed by Garett Rogers <garett.rogers@gmail.com>
# Source available at https://github.com/GarettRogers/appengine-apns-gcm
#
# appengine-apns-gcm is distributed under the terms of the MIT license.
#
# Copyright (c) 2013 AimX Labs
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

import webapp2
import os
from google.appengine.ext.webapp import template
from google.appengine.ext import ndb
from gcmdata import *
from gcm import *
from apns import *
from apnsdata import *
from appdata import *

appconfig = None

#TODO:
# - Make this more fail safe -- use Backends and a Task Queue or something so that we can guarantee delivery, and so it doesn't tie up the request when we are broadcasting to a very large number of devices
# - Properly handle feedback from the APNS Feedback service

def convertToGcmMessage(self, message):
    gcmmessage = {}
    gcmmessage["data"] = {}
    
    if 'android_collapse_key' in message["request"]:
        gcmmessage["collapse_key"] = message["request"]["android_collapse_key"]
    
    if 'data' in message["request"]:
        gcmmessage["data"] = message["request"]["data"]

    return gcmmessage

def convertToApnsMessage(self, message):
    apnsmessage = {}
    apnsmessage["data"] = {}
    apnsmessage["sound"] = "default"
    apnsmessage["badge"] = -1
    apnsmessage["alert"] = None
    apnsmessage["custom"] = None
    
    if 'ios_sound' in message["request"]:
        apnsmessage["sound"] = message["request"]["ios_sound"]
    
    if 'data' in message["request"]:
        apnsmessage["custom"] = message["request"]["data"]

    if 'ios_badge' in message["request"]:
        apnsmessage["badge"] = message["request"]["ios_badge"]

    if 'ios_message' in message["request"] and 'ios_button_text' in message["request"]:
        apnsmessage["alert"] = PayloadAlert(message["request"]["ios_message"], action_loc_key=message["request"]["ios_button_text"])
    else:
        if 'ios_message' in message["request"]:
            apnsmessage["alert"] = message["request"]["ios_message"]
    
    return apnsmessage

def getAPNs():
    appconfig = AppConfig.get_or_insert("config")
    
    if appconfig.apns_test_mode:
        return APNs(use_sandbox=True, cert_file=appconfig.apns_sandbox_cert, key_file=appconfig.apns_sandbox_key)
    else:
        return APNs(use_sandbox=False, cert_file=appconfig.apns_cert, key_file=appconfig.apns_key)

def GetApnsToken(regid):
    appconfig = AppConfig.get_or_insert("config")
    if appconfig.apns_test_mode:
        return ApnsSandboxToken.get_or_insert(regid)
    else:
        return ApnsToken.get_or_insert(regid)

def sendMulticastApnsMessage(self, apns_reg_ids, apnsmessage):
    apns = getAPNs()
    
    # Send a notification
    payload = Payload(alert=apnsmessage["alert"], sound=apnsmessage["sound"], custom=apnsmessage["custom"], badge=apnsmessage["badge"])
    apns.gateway_server.send_notifications(apns_reg_ids, payload)

    # Get feedback messages
    for (token_hex, fail_time) in apns.feedback_server.items():
        break

def sendSingleApnsMessage(self, message, token):
    apns_reg_ids=[token]
    sendMulticastApnsMessage(self, apns_reg_ids, message)


def sendMulticastGcmMessage(self, gcm_reg_ids, gcmmessage):
    appconfig = AppConfig.get_or_insert("config")
    gcm = GCM(appconfig.gcm_api_key)

    # JSON request
    response = gcm.json_request(registration_ids=gcm_reg_ids, data=gcmmessage)
    if 'errors' in response:
        for error, reg_ids in response['errors'].items():
            # Check for errors and act accordingly
            if error is 'NotRegistered':
                # Remove reg_ids from database
                for reg_id in reg_ids:
                    token = GcmToken.get_or_insert(reg_id)
                    token.key.delete()
    
    if 'canonical' in response:
        for reg_id, canonical_id in response['canonical'].items():
            # Repace reg_id with canonical_id in your database
            token = GcmToken.get_or_insert(reg_id)
            token.key.delete()
            
            token = GcmToken.get_or_insert(canonical_id)
            token.gcm_token = canonical_id
            token.enabled = True
            token.put()


def sendSingleGcmMessage(self, message, token):
    gcm_reg_ids=[token]
    sendMulticastGcmMessage(self, gcm_reg_ids, message)

def broadcastGcmMessage(self, message):
    appconfig = AppConfig.get_or_insert("config")
    gcmmessage = message
    
    gcm_reg_ids = []
    q = GcmToken.query(GcmToken.enabled == True)
    x=0
    
    for token in q.iter():
        if x == appconfig.gcm_multicast_limit:
            sendMulticastGcmMessage(self, gcm_reg_ids, gcmmessage)
            gcm_reg_ids.clear()
            x = 0
        
        gcm_reg_ids.append(token.gcm_token)
        x = x + 1
    
    if len(gcm_reg_ids) > 0:
        sendMulticastGcmMessage(self, gcm_reg_ids, gcmmessage)


def broadcastApnsMessage(self, message):
    appconfig = AppConfig.get_or_insert("config")
    apnsmessage = message
    
    apns_reg_ids = []
    if appconfig.apns_test_mode:
        q = ApnsSandboxToken.query(ApnsSandboxToken.enabled == True)
    else:
        q = ApnsToken.query(ApnsToken.enabled == True)

    x=0
    
    for token in q.iter():
        if x == appconfig.apns_multicast_limit:
            sendMulticastApnsMessage(self, apns_reg_ids, apnsmessage)
            apns_reg_ids.clear()
            x = 0
        
        apns_reg_ids.append(token.apns_token)
        x = x + 1
    
    if len(apns_reg_ids) > 0:
        sendMulticastApnsMessage(self, apns_reg_ids, apnsmessage)


#Sample POST Data -->  message={"request":{"data":{"custom": "json data"},"platforms": [1,2], "ios_message":"This is a test","ios_button_text":"yeah!","ios_badge": -1, "ios_sound": "soundfile", "android_collapse_key": "collapsekey"}}
class BroadcastMessage(webapp2.RequestHandler):
    def post(self):
        msg = json.loads(self.request.get("message"))
        if 1 in msg["request"]["platforms"]:
            #Send to Android devices using GCM
            broadcastGcmMessage(self, convertToGcmMessage(self, msg))
    
        if 2 in msg["request"]["platforms"]:
            #Send to iOS devices using APNS
            broadcastApnsMessage(self, convertToApnsMessage(self, msg))

        #Return result
        self.response.write("OK")

class BroadcastMessageToTag(webapp2.RequestHandler):
    def post(self):
        msg = json.loads(self.request.get("message"))
        if 1 in msg["request"]["platforms"]:
            tagid = self.request.get("tagid")
            
            q = GcmTag.query(GcmTag.tag == tagid)
            for tag in q.iter():
                sendSingleGcmMessage(self, convertToGcmMessage(self, msg), tag.token.get().gcm_token)
    
        if 2 in msg["request"]["platforms"]:
            #Send to iOS devices using APNS
            tagid = self.request.get("tagid")
            
            q = ApnsSandboxTag.query(ApnsSandboxTag.tag == tagid)
            for tag in q.iter():
                sendSingleApnsMessage(self, convertToApnsMessage(self, msg), tag.token.get().apns_token)
            
        #Return result
        self.response.write("OK")


#Sample POST Data -->  platform=1&token=<device token string>&message={"request":{"data":{"custom": "json data"}, "ios_message":"This is a test","ios_button_text":"yeah!","ios_badge": -1, "ios_sound": "soundfile", "android_collapse_key": "collapsekey"}}
class SendMessage(webapp2.RequestHandler):
   def post(self):
        platform = self.request.get("platform")
        message = self.request.get("message")
        token = self.request.get("token")
        
        #Send a single message to a device token
        if platform == "1": #Android
            sendSingleGcmMessage(convertToGcmMessage(self, json.loads(message)), token)
        elif platform == "2": #iOS
            sendSingleApnsMessage(convertToApnsMessage(self, json.loads(message)), token)
                
        self.response.write("OK")

app = webapp2.WSGIApplication([
    ('/push/tagbroadcast', BroadcastMessageToTag),
    ('/push/broadcast', BroadcastMessage),
    ('/push/send', SendMessage)
], debug=True)

########NEW FILE########
