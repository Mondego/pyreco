__FILENAME__ = paginator
class Paginator(object):
    """
    Paginate through all entries:

    >>> paginator = Paginator(api.trends.listThreads, forum='disqus')
    >>> for result in paginator:
    >>>     print result

    Paginate only up to a number of entries:

    >>> for result in paginator(limit=500):
    >>>     print result
    """

    def __init__(self, endpoint, **params):
        self.endpoint = endpoint
        self.params = params

    def __iter__(self):
        for result in self():
            yield result

    def __call__(self, limit=None):
        params = self.params.copy()
        num = 0
        more = True
        while more and (not limit or num < limit):
            results = self.endpoint(**params)
            for result in results:
                if limit and num >= limit:
                    break
                num += 1
                yield result

            if results.cursor:
                more = results.cursor['more']
                params['cursor'] = results.cursor['id']
            else:
                more = False
########NEW FILE########
__FILENAME__ = tests
import mock
import os
import unittest

import disqusapi

def requires(*env_vars):
    def wrapped(func):
        for k in env_vars:
            if not os.environ.get(k):
                return
        return func
    return wrapped

class MockResponse(object):
    def __init__(self, body, status=200):
        self.body = body
        self.status = status

    def read(self):
        return self.body

class DisqusAPITest(unittest.TestCase):
    API_SECRET = 'b'*64
    API_PUBLIC = 'c'*64
    HOST = os.environ.get('DISQUS_API_HOST', disqusapi.HOST)

    def setUp(self):
        disqusapi.HOST = self.HOST

    def test_setKey(self):
        api = disqusapi.DisqusAPI('a', 'c')
        self.assertEquals(api.secret_key, 'a')
        api.setKey('b')
        self.assertEquals(api.secret_key, 'b')

    def test_setSecretKey(self):
        api = disqusapi.DisqusAPI('a', 'c')
        self.assertEquals(api.secret_key, 'a')
        api.setSecretKey('b')
        self.assertEquals(api.secret_key, 'b')

    def test_setPublicKey(self):
        api = disqusapi.DisqusAPI('a', 'c')
        self.assertEquals(api.public_key, 'c')
        api.setPublicKey('b')
        self.assertEquals(api.public_key, 'b')

    def test_setFormat(self):
        api = disqusapi.DisqusAPI()
        self.assertEquals(api.format, 'json')
        api.setFormat('jsonp')
        self.assertEquals(api.format, 'jsonp')

    def test_setVersion(self):
        api = disqusapi.DisqusAPI()
        self.assertEquals(api.version, '3.0')
        api.setVersion('3.1')
        self.assertEquals(api.version, '3.1')

    def test_paginator(self):
        def iter_results():
            for n in xrange(11):
                yield disqusapi.Result(
                    response=[n]*10,
                    cursor={
                        'id': n,
                        'more': n < 10,
                    },
                )

        api = disqusapi.DisqusAPI(self.API_SECRET, self.API_PUBLIC)

        with mock.patch('disqusapi.Resource._request') as _request:
            iterator = iter_results()
            _request.return_value = iterator.next()
            paginator = disqusapi.Paginator(api.posts.list, forum='disqus')
            n = 0
            for n, result in enumerate(paginator(limit=100)):
                if n % 10 == 0:
                    iterator.next()
        self.assertEquals(n, 99)

if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = utils
import binascii
import hashlib
import hmac
import urllib
import urlparse

def get_normalized_params(params):
    """
    Given a list of (k, v) parameters, returns
    a sorted, encoded normalized param
    """
    return urllib.urlencode(sorted(params))

def get_normalized_request_string(method, url, nonce, params, ext='', body_hash=None):
    """
    Returns a normalized request string as described iN OAuth2 MAC spec.

    http://tools.ietf.org/html/draft-ietf-oauth-v2-http-mac-00#section-3.3.1
    """
    urlparts = urlparse.urlparse(url)
    if urlparts.query:
        norm_url = '%s?%s' % (urlparts.path, urlparts.query)
    elif params:
        norm_url = '%s?%s' % (urlparts.path, get_normalized_params(params))
    else:
        norm_url = urlparts.path

    if not body_hash:
        body_hash = get_body_hash(params)

    port = urlparts.port
    if not port:
        assert urlparts.scheme in ('http', 'https')

        if urlparts.scheme == 'http':
            port = 80
        elif urlparts.scheme == 'https':
            port = 443

    output = [nonce, method.upper(), norm_url, urlparts.hostname, port, body_hash, ext, '']

    return '\n'.join(map(str, output))

def get_body_hash(params):
    """
    Returns BASE64 ( HASH (text) ) as described in OAuth2 MAC spec.

    http://tools.ietf.org/html/draft-ietf-oauth-v2-http-mac-00#section-3.2
    """
    norm_params = get_normalized_params(params)

    return binascii.b2a_base64(hashlib.sha1(norm_params).digest())[:-1]

def get_mac_signature(api_secret, norm_request_string):
    """
    Returns HMAC-SHA1 (api secret, normalized request string)
    """
    hashed = hmac.new(str(api_secret), norm_request_string, hashlib.sha1)
    return binascii.b2a_base64(hashed.digest())[:-1]
########NEW FILE########
