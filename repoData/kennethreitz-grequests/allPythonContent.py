__FILENAME__ = grequests
# -*- coding: utf-8 -*-

"""
grequests
~~~~~~~~~

This module contains an asynchronous replica of ``requests.api``, powered
by gevent. All API methods return a ``Request`` instance (as opposed to
``Response``). A list of requests can be sent with ``map()``.
"""
from functools import partial

try:
    import gevent
    from gevent import monkey as curious_george
    from gevent.pool import Pool
except ImportError:
    raise RuntimeError('Gevent is required for grequests.')

# Monkey-patch.
curious_george.patch_all(thread=False, select=False)

from requests import Session


__all__ = (
    'map', 'imap',
    'get', 'options', 'head', 'post', 'put', 'patch', 'delete', 'request'
)


class AsyncRequest(object):
    """ Asynchronous request.

    Accept same parameters as ``Session.request`` and some additional:

    :param session: Session which will do request
    :param callback: Callback called on response.
                     Same as passing ``hooks={'response': callback}``
    """
    def __init__(self, method, url, **kwargs):
        #: Request method
        self.method = method
        #: URL to request
        self.url = url
        #: Associated ``Session``
        self.session = kwargs.pop('session', None)
        if self.session is None:
            self.session = Session()

        callback = kwargs.pop('callback', None)
        if callback:
            kwargs['hooks'] = {'response': callback}

        #: The rest arguments for ``Session.request``
        self.kwargs = kwargs
        #: Resulting ``Response``
        self.response = None

    def send(self, **kwargs):
        """
        Prepares request based on parameter passed to constructor and optional ``kwargs```.
        Then sends request and saves response to :attr:`response`

        :returns: ``Response``
        """
        merged_kwargs = {}
        merged_kwargs.update(self.kwargs)
        merged_kwargs.update(kwargs)
        self.response =  self.session.request(self.method,
                                              self.url, **merged_kwargs)
        return self.response


def send(r, pool=None, stream=False):
    """Sends the request object using the specified pool. If a pool isn't
    specified this method blocks. Pools are useful because you can specify size
    and can hence limit concurrency."""
    if pool != None:
        return pool.spawn(r.send, stream=stream)

    return gevent.spawn(r.send, stream=stream)


# Shortcuts for creating AsyncRequest with appropriate HTTP method
get = partial(AsyncRequest, 'GET')
options = partial(AsyncRequest, 'OPTIONS')
head = partial(AsyncRequest, 'HEAD')
post = partial(AsyncRequest, 'POST')
put = partial(AsyncRequest, 'PUT')
patch = partial(AsyncRequest, 'PATCH')
delete = partial(AsyncRequest, 'DELETE')

# synonym
def request(method, url, **kwargs):
    return AsyncRequest(method, url, **kwargs)


def map(requests, stream=False, size=None):
    """Concurrently converts a list of Requests to Responses.

    :param requests: a collection of Request objects.
    :param stream: If True, the content will not be downloaded immediately.
    :param size: Specifies the number of requests to make at a time. If None, no throttling occurs.
    """

    requests = list(requests)

    pool = Pool(size) if size else None
    jobs = [send(r, pool, stream=stream) for r in requests]
    gevent.joinall(jobs)

    return [r.response for r in requests]


def imap(requests, stream=False, size=2):
    """Concurrently converts a generator object of Requests to
    a generator of Responses.

    :param requests: a generator of Request objects.
    :param stream: If True, the content will not be downloaded immediately.
    :param size: Specifies the number of requests to make at a time. default is 2
    """

    pool = Pool(size)

    def send(r):
        return r.send(stream=stream)

    for r in pool.imap_unordered(send, requests):
        yield r

    pool.join()

########NEW FILE########
__FILENAME__ = requirements
requests
gevent
nose

########NEW FILE########
__FILENAME__ = test_grequests
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Path hack
import os, sys
sys.path.insert(0, os.path.abspath('..'))

import time
import unittest

import requests
import grequests

HTTPBIN_URL = os.environ.get('HTTPBIN_URL', 'http://httpbin.org/')

def httpbin(*suffix):
    """Returns url for HTTPBIN resource."""
    return HTTPBIN_URL + '/'.join(suffix)


N = 5
URLS = [httpbin('get?p=%s' % i) for i in range(N)]


class GrequestsCase(unittest.TestCase):

    def test_map(self):
        reqs = [grequests.get(url) for url in URLS]
        resp = grequests.map(reqs, size=N)
        self.assertEqual([r.url for r in resp], URLS)

    def test_imap(self):
        reqs = (grequests.get(url) for url in URLS)
        i = 0
        for i, r in enumerate(grequests.imap(reqs, size=N)):
            self.assertTrue(r.url in URLS)
        self.assertEqual(i, N - 1)

    def test_hooks(self):
        result = {}

        def hook(r, **kwargs):
            result[r.url] = True
            return r

        reqs = [grequests.get(url, hooks={'response': [hook]}) for url in URLS]
        resp = grequests.map(reqs, size=N)
        self.assertEqual(sorted(result.keys()), sorted(URLS))

    def test_callback_kwarg(self):
        result = {'ok': False}

        def callback(r, **kwargs):
            result['ok'] = True
            return r

        self.get(URLS[0], callback=callback)
        self.assertTrue(result['ok'])

    def test_session_and_cookies(self):
        c1 = {'k1': 'v1'}
        r = self.get(httpbin('cookies/set'), params=c1).json()
        self.assertEqual(r['cookies'], c1)
        s = requests.Session()
        r = self.get(httpbin('cookies/set'), session=s, params=c1).json()
        self.assertEqual(dict(s.cookies), c1)

        # ensure all cookies saved
        c2 = {'k2': 'v2'}
        c1.update(c2)
        r = self.get(httpbin('cookies/set'), session=s, params=c2).json()
        self.assertEqual(dict(s.cookies), c1)

        # ensure new session is created
        r = self.get(httpbin('cookies')).json()
        self.assertEqual(r['cookies'], {})

        # cookies as param
        c3 = {'p1': '42'}
        r = self.get(httpbin('cookies'), cookies=c3).json()
        self.assertEqual(r['cookies'], c3)

    def test_calling_request(self):
        reqs = [grequests.request('POST', httpbin('post'), data={'p': i})
                for i in range(N)]
        resp = grequests.map(reqs, size=N)
        self.assertEqual([int(r.json()['form']['p']) for r in resp], list(range(N)))

    def test_stream_enabled(self):
        r = grequests.map([grequests.get(httpbin('stream/10'))],
                          size=2, stream=True)[0]
        self.assertFalse(r._content_consumed)

    def test_concurrency_with_delayed_url(self):
        t = time.time()
        n = 10
        reqs = [grequests.get(httpbin('delay/1')) for _ in range(n)]
        resp = grequests.map(reqs, size=n)
        self.assertLess((time.time() - t), n)

    def get(self, url, **kwargs):
        return grequests.map([grequests.get(url, **kwargs)])[0]


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = tests
#! /usr/bin/env python
# -*- coding: utf-8 -*-

from grequests import get, map, imap
from nose.tools import ok_

########### Constants ############
urls = [
        'http://github.com',
        'http://www.google.com', 
        'http://www.psf.org'
        ]
############# tests ##############
def test_get():
    global urls
    to_fetch = (get(url) for url in urls)
    map(to_fetch)
    for fetched in to_fetch:
        ok_(fetched.ok, True)

def test_imap_with_size():
    global urls
    to_fetch = (get(url) for url in urls)
    imap(to_fetch, size = len(urls) - 1)
    for fetching in to_fetch:
        ok_(fetching.send(), True)

########NEW FILE########
