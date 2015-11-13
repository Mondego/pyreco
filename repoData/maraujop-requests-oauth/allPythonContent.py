__FILENAME__ = auth
import binascii
import hmac
import random
import urllib
from urlparse import urlparse, urlunparse
try:
    from hashlib import sha1
    sha = sha1
except ImportError:
    # hashlib was added in Python 2.5
    import sha


escape = lambda url: urllib.quote(to_utf8(url), safe='~')

def to_utf8(x):
    """
    Tries to utf-8 encode x when possible 

    If x is a string returns it encoded, otherwise tries to iter x and 
    encode utf-8 all strings it contains, returning a list.
    """
    if isinstance(x, basestring): 
        return x.encode('utf-8') if isinstance(x, unicode) else x
    try:
        l = iter(x)
    except TypeError:
        return x
    return [to_utf8(i) for i in l]

generate_verifier = lambda length=8: ''.join([str(random.randint(0, 9)) for i in xrange(length)])


class OAuthObject(object):
    def __init__(self, key, secret):
        self.key, self.secret = key, secret


class Consumer(OAuthObject):
    pass


class Token(OAuthObject):
    pass


class SignatureMethod_HMAC_SHA1(object):
    """
    This is a barebones implementation of a signature method only suitable for use 
    for signing OAuth HTTP requests as a hook to requests library.
    """
    name = 'HMAC-SHA1'

    def check(self, request, consumer, token, signature):
        """Returns whether the given signature is the correct signature for
        the given consumer and token signing the given request."""
        built = self.sign(request, consumer, token)
        return built == signature

    def signing_base(self, request, consumer, token):
        pass

    def sign(self, request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.signing_base(request, consumer, token)
        hashed = hmac.new(key, raw, sha)
        # Calculate the digest base 64.
        return binascii.b2a_base64(hashed.digest())[:-1]

########NEW FILE########
__FILENAME__ = hook
# -*- coding: utf-8 -*-
import time
from datetime import datetime
import random
import urllib
from urlparse import urlparse, urlunparse, parse_qs, urlsplit, urlunsplit

from auth import Token, Consumer
from auth import to_utf8, escape
from auth import SignatureMethod_HMAC_SHA1


class CustomSignatureMethod_HMAC_SHA1(SignatureMethod_HMAC_SHA1):
    def signing_base(self, request, consumer, token):
        """
        This method generates the OAuth signature. It's defined here to avoid circular imports.
        """
        sig = (
            escape(request.method),
            escape(OAuthHook.get_normalized_url(request.url)),
            escape(OAuthHook.get_normalized_parameters(request)),
        )

        key = '%s&' % escape(consumer.secret)
        if token is not None:
            key += escape(token.secret)
        raw = '&'.join(sig)
        return key, raw


class OAuthHook(object):
    OAUTH_VERSION = '1.0'
    header_auth = False
    signature = CustomSignatureMethod_HMAC_SHA1()
    consumer_key = None
    consumer_secret = None

    def __init__(self, access_token=None, access_token_secret=None, consumer_key=None, consumer_secret=None, header_auth=None):
        """
        Consumer is compulsory, while the user's Token can be retrieved through the API
        """
        if access_token is not None:
            self.token = Token(access_token, access_token_secret)
        else:
            self.token = None

        if consumer_key is None and consumer_secret is None:
            consumer_key = self.consumer_key
            consumer_secret = self.consumer_secret

        if header_auth is not None:
            self.header_auth = header_auth

        self.consumer = Consumer(consumer_key, consumer_secret)

    @staticmethod
    def _split_url_string(query_string):
        """
        Turns a `query_string` into a Python dictionary with unquoted values
        """
        parameters = parse_qs(to_utf8(query_string), keep_blank_values=True)
        for k, v in parameters.iteritems():
            parameters[k] = urllib.unquote(v[0])
        return parameters

    @staticmethod
    def get_normalized_parameters(request):
        """
        Returns a string that contains the parameters that must be signed.
        This function is called by SignatureMethod subclass CustomSignatureMethod_HMAC_SHA1
        """
        # See issues #10 and #12
        if ('Content-Type' not in request.headers or \
            request.headers.get('Content-Type').startswith('application/x-www-form-urlencoded')) \
            and not isinstance(request.data, basestring):
            data_and_params = dict(request.data.items() + request.params.items())

            for key,value in data_and_params.items():
                request.data_and_params[to_utf8(key)] = to_utf8(value)

        if request.data_and_params.has_key('oauth_signature'):
            del request.data_and_params['oauth_signature']

        items = []
        for key, value in request.data_and_params.iteritems():
            # 1.0a/9.1.1 states that kvp must be sorted by key, then by value,
            # so we unpack sequence values into multiple items for sorting.
            if isinstance(value, basestring):
                items.append((key, value))
            else:
                try:
                    value = list(value)
                except TypeError, e:
                    assert 'is not iterable' in str(e)
                    items.append((key, value))
                else:
                    items.extend((key, item) for item in value)

        # Include any query string parameters included in the url
        query_string = urlparse(request.url)[4]
        items.extend([(to_utf8(k), to_utf8(v)) for k, v in OAuthHook._split_url_string(query_string).items()])
        items.sort()

        return urllib.urlencode(items).replace('+', '%20').replace('%7E', '~')

    @staticmethod
    def get_normalized_url(url):
        """
        Returns a normalized url, without params
        """
        scheme, netloc, path, params, query, fragment = urlparse(url)

        # Exclude default port numbers.
        if scheme == 'http' and netloc[-3:] == ':80':
            netloc = netloc[:-3]
        elif scheme == 'https' and netloc[-4:] == ':443':
            netloc = netloc[:-4]
        if scheme not in ('http', 'https'):
            raise ValueError("Unsupported URL %s (%s)." % (url, scheme))

        # Normalized URL excludes params, query, and fragment.
        return urlunparse((scheme, netloc, path, None, None, None))

    @staticmethod
    def to_url(request):
        """Serialize as a URL for a GET request."""
        scheme, netloc, path, query, fragment = urlsplit(to_utf8(request.url))
        query = parse_qs(query)

        for key, value in request.data_and_params.iteritems():
            query.setdefault(key, []).append(value)

        query = urllib.urlencode(query, True)
        return urlunsplit((scheme, netloc, path, query, fragment))

    @staticmethod
    def to_postdata(request):
        """Serialize as post data for a POST request. This serializes data and params"""
        # tell urlencode to convert each sequence element to a separate parameter
        return urllib.urlencode(request.data_and_params, True).replace('+', '%20')

    @staticmethod
    def authorization_header(oauth_params):
        """Return Authorization header"""
        authorization_headers = 'OAuth realm="",'
        authorization_headers += ','.join(['{0}="{1}"'.format(k, urllib.quote(str(v)))
            for k, v in oauth_params.items()])
        return authorization_headers

    def __call__(self, request):
        """
        Pre-request hook that signs a Python-requests Request for OAuth authentication
        """
        # These checkings are necessary because type inconsisntecy of requests library
        # See request Github issue #230 https://github.com/kennethreitz/requests/pull/230
        if not request.params:
            request.params = {}
        if not request.data:
            request.data = {}
        if isinstance(request.params, list):
            request.params = dict(request.params)
        if isinstance(request.data, list):
            request.data = dict(request.data)

        # Dictionary to OAuth1 signing params
        request.oauth_params = {}

        # Adding OAuth params
        request.oauth_params['oauth_consumer_key'] = self.consumer.key
        request.oauth_params['oauth_timestamp'] = str(int(time.time()))
        request.oauth_params['oauth_nonce'] = str(random.randint(0, 100000000))
        request.oauth_params['oauth_version'] = self.OAUTH_VERSION
        if self.token:
            request.oauth_params['oauth_token'] = self.token.key
        if 'oauth_verifier' in request.data:
            request.oauth_params['oauth_verifier'] = request.data.pop('oauth_verifier')
        request.oauth_params['oauth_signature_method'] = self.signature.name

        # oauth_callback is an special parameter, we remove it out of the body
        # If it needs to go in the body, it will be overwritten later, otherwise not
        if 'oauth_callback' in request.data:
            request.oauth_params['oauth_callback'] = request.data.pop('oauth_callback')
        if 'oauth_callback' in request.params:
            request.oauth_params['oauth_callback'] = request.params.pop('oauth_callback')

        request.data_and_params = request.oauth_params.copy()
        request.oauth_params['oauth_signature'] = self.signature.sign(request, self.consumer, self.token)
        request.data_and_params['oauth_signature'] = request.oauth_params['oauth_signature']

        if self.header_auth:
            request.headers['Authorization'] = self.authorization_header(request.oauth_params)
        elif request.method in ("GET", "DELETE"):
            request.url = self.to_url(request)
        elif ('Content-Type' not in request.headers or \
              request.headers['Content-Type'] != 'application/x-www-form-urlencoded') \
              and not isinstance(request.data, basestring):
            # You can pass a string as data. See issues #10 and #12
            request.url = self.to_url(request)
            request.data = {}
        else:
            request.data = request.data_and_params

        return request

########NEW FILE########
__FILENAME__ = tests
#! /usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import unittest
import random
import json
import requests
from urlparse import parse_qs

# Insert this package's path in the PYTHON PATH as first route
path = os.path.dirname(os.getcwd())
sys.path.insert(0, path)

from oauth_hook.hook import OAuthHook
from test_settings import TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
from test_settings import TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET
from test_settings import RDIO_API_KEY, RDIO_SHARED_SECRET
from test_settings import (
    IMGUR_CONSUMER_KEY, IMGUR_CONSUMER_SECRET,
    IMGUR_ACCESS_TOKEN, IMGUR_ACCESS_TOKEN_SECRET,
)

# Initializing the hook and Python-requests client
OAuthHook.consumer_key = TWITTER_CONSUMER_KEY
OAuthHook.consumer_secret = TWITTER_CONSUMER_SECRET
oauth_hook = OAuthHook(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
client = requests.session(hooks={'pre_request': oauth_hook})


class TwitterOAuthTestSuite(unittest.TestCase):
    def setUp(self):
        # twitter prefers that you use header_auth
        oauth_hook.header_auth = True

    def test_rate_limit_GET_urlencoded(self):
        oauth_hook.header_auth = False
        self.test_rate_limit_GET()

    def test_rate_limit_GET(self):
        response = client.get('http://api.twitter.com/1/account/rate_limit_status.json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['hourly_limit'], 350)

    def test_status_POST_urlencoded(self):
        oauth_hook.header_auth = False
        self.test_status_POST()

    def test_status_POST(self):
        message = "Kind of a random message %s" % random.random()
        response = client.post('http://api.twitter.com/1/statuses/update.json',
            {'status': message, 'wrap_links': True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['text'], message)

    def test_status_GET_with_data_urlencoded(self):
        oauth_hook.header_auth = False
        self.test_status_GET_with_data()

    def test_status_GET_with_data(self):
        response = client.get('http://api.twitter.com/1/statuses/friends.json', data={'user_id': 12345})
        self.assertEqual(response.status_code, 200)

    def test_status_GET_with_params_urlencoded(self):
        oauth_hook.header_auth = False
        self.test_status_GET_with_params()

    def test_status_GET_with_params(self):
        response = client.get('http://api.twitter.com/1/statuses/friends.json', params={'user_id': 12345})
        self.assertEqual(response.status_code, 200)

    def test_create_delete_list_urlencoded(self):
        oauth_hook.header_auth = False
        self.test_create_delete_list()

    def test_create_delete_list(self):
        screen_name = json.loads(client.get('http://api.twitter.com/1/account/verify_credentials.json').content)['screen_name']
        user_lists = json.loads(client.get('http://api.twitter.com/1/lists.json', data={'screen_name': screen_name}).content)['lists']
        for list in user_lists:
            if list['name'] == 'OAuth Request Hook':
                client.post('http://api.twitter.com/1/lists/destroy.json', data={'list_id': list['id']})

        created_list = json.loads(client.post('http://api.twitter.com/1/%s/lists.json' % screen_name, data={'name': "OAuth Request Hook"}).content)
        list_id = created_list['id']
        response = client.delete('http://api.twitter.com/1/%s/lists/%s.json' % (screen_name, list_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), created_list)

    def test_three_legged_auth(self):
        yes_or_no = raw_input("Do you want to skip Twitter three legged auth test? (y/n):")
        if yes_or_no.lower() in ['y', 'yes']:
            return

        twitter_oauth_hook = OAuthHook()
        for header_auth in (True, False):
            # See https://dev.twitter.com/docs/auth/implementing-sign-twitter
            # Step 1: Obtaining a request token
            twitter_oauth_hook.header_auth = header_auth

            client = requests.session(hooks={'pre_request': twitter_oauth_hook})
            response = client.post('http://api.twitter.com/oauth/request_token', data={'oauth_callback': 'oob'})
            self.assertEqual(response.status_code, 200)
            response = parse_qs(response.content)
            self.assertTrue(response['oauth_token'])
            self.assertTrue(response['oauth_token_secret'])

            oauth_token = response['oauth_token']
            oauth_secret = response['oauth_token_secret']

            # Step 2: Redirecting the user
            print "Go to https://api.twitter.com/oauth/authenticate?oauth_token=%s and sign in into the application, then enter your PIN" % oauth_token[0]
            oauth_verifier = raw_input('Please enter your PIN:')

            # Step 3: Authenticate
            response = client.post('http://api.twitter.com/oauth/access_token', {'oauth_verifier': oauth_verifier, 'oauth_token': oauth_token[0]})
            response = parse_qs(response.content)
            self.assertTrue(response['oauth_token'])
            self.assertTrue(response['oauth_token_secret'])

    def test_update_profile_image_urlencoded(self):
        oauth_hook.header_auth = False
        self.test_update_profile_image()

    def test_update_profile_image(self):
        files = {'image': ('hommer.gif', open('hommer.gif', 'rb'))}
        response = client.post('http://api.twitter.com/1/account/update_profile_image.json', files=files)
        self.assertEqual(response.status_code, 200)


class RdioOAuthTestSuite(unittest.TestCase):
    def setUp(self):
        rdio_oauth_hook = OAuthHook(consumer_key=RDIO_API_KEY, consumer_secret=RDIO_SHARED_SECRET, header_auth=False)
        self.client = requests.session(hooks={'pre_request': rdio_oauth_hook})

    def test_rdio_oauth_get_token_data(self):
        response = self.client.post('http://api.rdio.com/oauth/request_token', data={'oauth_callback': 'oob'})
        self.assertEqual(response.status_code, 200)
        response = parse_qs(response.content)
        self.assertTrue(response['oauth_token'])
        self.assertTrue(response['oauth_token_secret'])

    def test_rdio_oauth_get_token_params(self):
        self.client.params = {'oauth_callback': 'oob'}
        response = self.client.post('http://api.rdio.com/oauth/request_token')
        self.assertEqual(response.status_code, 200)
        response = parse_qs(response.content)
        self.assertTrue(response['oauth_token'])
        self.assertTrue(response['oauth_token_secret'])


class ImgurOAuthTestSuite(unittest.TestCase):
    def test_three_legged_auth(self):
        yes_or_no = raw_input("Do you want to skip Imgur three legged auth test? (y/n):")
        if yes_or_no.lower() in ['y', 'yes']:
            return

        for header_auth in (True, False):
            # Step 1: Obtaining a request token
            imgur_oauth_hook = OAuthHook(
                consumer_key=IMGUR_CONSUMER_KEY,
                consumer_secret=IMGUR_CONSUMER_SECRET,
                header_auth=header_auth
            )
            client = requests.session(hooks={'pre_request': imgur_oauth_hook})

            response = client.post('http://api.imgur.com/oauth/request_token')
            qs = parse_qs(response.text)
            oauth_token = qs['oauth_token'][0]
            oauth_secret = qs['oauth_token_secret'][0]

            # Step 2: Redirecting the user
            print "Go to http://api.imgur.com/oauth/authorize?oauth_token=%s and sign in into the application, then enter your PIN" % oauth_token
            oauth_verifier = raw_input('Please enter your PIN:')

            # Step 3: Authenticate
            new_imgur_oauth_hook = OAuthHook(oauth_token, oauth_secret, IMGUR_CONSUMER_KEY, IMGUR_CONSUMER_SECRET, header_auth)
            new_client = requests.session(
                hooks={'pre_request': new_imgur_oauth_hook}
            )
            response = new_client.post('http://api.imgur.com/oauth/access_token', {'oauth_verifier': oauth_verifier})
            response = parse_qs(response.content)
            token = response['oauth_token'][0]
            token_secret = response['oauth_token_secret'][0]
            self.assertTrue(token)
            self.assertTrue(token_secret)

    def test_stats(self):
        imgur_oauth_hook = OAuthHook(IMGUR_ACCESS_TOKEN, IMGUR_ACCESS_TOKEN_SECRET, IMGUR_CONSUMER_KEY, IMGUR_CONSUMER_SECRET, True)
        client = requests.session(hooks={'pre_request': imgur_oauth_hook})

        response = client.get("http://api.imgur.com/2/account/images.json")
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
