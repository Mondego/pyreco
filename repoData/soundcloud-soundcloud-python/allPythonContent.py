__FILENAME__ = client
from functools import partial
from urllib import urlencode

from soundcloud.resource import wrapped_resource
from soundcloud.request import make_request


class Client(object):
    """A client for interacting with Soundcloud resources."""

    use_ssl = True
    host = 'api.soundcloud.com'

    def __init__(self, **kwargs):
        """Create a client instance with the provided options. Options should
        be passed in as kwargs.
        """
        self.use_ssl = kwargs.get('use_ssl', self.use_ssl)
        self.host = kwargs.get('host', self.host)
        self.scheme = self.use_ssl and 'https://' or 'http://'
        self.options = kwargs
        self._authorize_url = None

        self.client_id = kwargs.get('client_id')

        if 'access_token' in kwargs:
            self.access_token = kwargs.get('access_token')
            return

        if 'client_id' not in kwargs:
            raise TypeError("At least a client_id must be provided.")

        if 'scope' in kwargs:
            self.scope = kwargs.get('scope')

        # decide which protocol flow to follow based on the arguments
        # provided by the caller.
        if self._options_for_authorization_code_flow_present():
            self._authorization_code_flow()
        elif self._options_for_credentials_flow_present():
            self._credentials_flow()
        elif self._options_for_token_refresh_present():
            self._refresh_token_flow()

    def exchange_token(self, code):
        """Given the value of the code parameter, request an access token."""
        url = '%s%s/oauth2/token' % (self.scheme, self.host)
        options = {
            'grant_type': 'authorization_code',
            'redirect_uri': self._redirect_uri(),
            'client_id': self.options.get('client_id'),
            'client_secret': self.options.get('client_secret'),
            'code': code,
        }
        options.update({
            'verify_ssl': self.options.get('verify_ssl', True),
            'proxies': self.options.get('proxies', None)
        })
        self.token = wrapped_resource(
            make_request('post', url, options))
        self.access_token = self.token.access_token
        return self.token

    def authorize_url(self):
        """Return the authorization URL for OAuth2 authorization code flow."""
        return self._authorize_url

    def _authorization_code_flow(self):
        """Build the the auth URL so the user can authorize the app."""
        options = {
            'scope': getattr(self, 'scope', 'non-expiring'),
            'client_id': self.options.get('client_id'),
            'response_type': 'code',
            'redirect_uri': self._redirect_uri()
        }
        url = '%s%s/connect' % (self.scheme, self.host)
        self._authorize_url = '%s?%s' % (url, urlencode(options))

    def _refresh_token_flow(self):
        """Given a refresh token, obtain a new access token."""
        url = '%s%s/oauth2/token' % (self.scheme, self.host)
        options = {
            'grant_type': 'refresh_token',
            'client_id': self.options.get('client_id'),
            'client_secret': self.options.get('client_secret'),
            'refresh_token': self.options.get('refresh_token')
        }
        options.update({
            'verify_ssl': self.options.get('verify_ssl', True),
            'proxies': self.options.get('proxies', None)
        })
        self.token = wrapped_resource(
            make_request('post', url, options))
        self.access_token = self.token.access_token

    def _credentials_flow(self):
        """Given a username and password, obtain an access token."""
        url = '%s%s/oauth2/token' % (self.scheme, self.host)
        options = {
            'client_id': self.options.get('client_id'),
            'client_secret': self.options.get('client_secret'),
            'username': self.options.get('username'),
            'password': self.options.get('password'),
            'scope': getattr(self, 'scope', ''),
            'grant_type': 'password'
        }
        options.update({
            'verify_ssl': self.options.get('verify_ssl', True),
            'proxies': self.options.get('proxies', None)
        })
        self.token = wrapped_resource(
            make_request('post', url, options))
        self.access_token = self.token.access_token

    def _request(self, method, resource, **kwargs):
        """Given an HTTP method, a resource name and kwargs, construct a
        request and return the response.
        """
        url = self._resolve_resource_name(resource)

        if hasattr(self, 'access_token'):
            kwargs.update(dict(oauth_token=self.access_token))
        if hasattr(self, 'client_id'):
            kwargs.update(dict(client_id=self.client_id))

        kwargs.update({
            'verify_ssl': self.options.get('verify_ssl', True),
            'proxies': self.options.get('proxies', None)
        })
        return wrapped_resource(make_request(method, url, kwargs))

    def __getattr__(self, name, **kwargs):
        """Translate an HTTP verb into a request method."""
        if name not in ('get', 'post', 'put', 'head', 'delete'):
            raise AttributeError
        return partial(self._request, name, **kwargs)

    def _resolve_resource_name(self, name):
        """Convert a resource name (e.g. tracks) into a URI."""
        if name[:4] == 'http':  # already a url
            if name[:4] != 'json' and name[-8:] not in ('download', 'stream'):
                return '%s.json' % (name,)
            return name
        name = name.rstrip('/').lstrip('/')
        if name[-13:] == 'contributions':
            return '%s%s/%s' % (self.scheme, self.host, name)
        return '%s%s/%s.json' % (self.scheme, self.host, name)

    def _redirect_uri(self):
        """
        Return the redirect uri. Checks for ``redirect_uri`` or common typo,
        ``redirect_url``
        """
        return self.options.get(
            'redirect_uri',
            self.options.get('redirect_url', None))

    # Helper functions for testing arguments provided to the constructor.
    def _options_present(self, options, kwargs):
        return all(map(lambda k: k in kwargs, options))

    def _options_for_credentials_flow_present(self):
        required = ('client_id', 'client_secret', 'username', 'password')
        return self._options_present(required, self.options)

    def _options_for_authorization_code_flow_present(self):
        required = ('client_id', 'redirect_uri')
        or_required = ('client_id', 'redirect_url')
        return (self._options_present(required, self.options) or
                self._options_present(or_required, self.options))

    def _options_for_token_refresh_present(self):
        required = ('client_id', 'client_secret', 'refresh_token')
        return self._options_present(required, self.options)

########NEW FILE########
__FILENAME__ = hashconversions
import re
import collections
from urllib import quote_plus


def to_params(hash):
    normalized = map(lambda (k, v): normalize_param(k, v), hash.iteritems())
    return dict((k, v) for d in normalized for (k, v) in d.items())


def normalize_param(key, value):
    """Convert a set of key, value parameters into a dictionary suitable for
    passing into requests. This will convert lists into the syntax required
    by SoundCloud. Heavily lifted from HTTParty.

    >>> normalize_param('playlist', {
    ...  'title': 'foo',
    ...  'sharing': 'private',
    ...  'tracks': [
    ...    {id: 1234}, {id: 4567}
    ...  ]})  # doctest:+ELLIPSIS
    {u'playlist[tracks][][<built-in function id>]': [1234, 4567], u'playlist[sharing]': 'private', u'playlist[title]': 'foo'}

    >>> normalize_param('oauth_token', 'foo')
    {'oauth_token': 'foo'}

    >>> normalize_param('playlist[tracks]', [1234, 4567])
    {u'playlist[tracks][]': [1234, 4567]}
    """
    params = {}
    stack = []
    if isinstance(value, list):
        normalized = map(lambda e: normalize_param(u"{0[key]}[]".format(dict(key=key)), e), value)
        keys = [item for sublist in tuple(h.keys() for h in normalized) for item in sublist]

        lists = {}
        if len(keys) != len(set(keys)):
            duplicates = [x for x, y in collections.Counter(keys).items() if y > 1]
            for dup in duplicates:
                lists[dup] = [h[dup] for h in normalized]
                for h in normalized:
                    del h[dup]

        params.update(dict((k, v) for d in normalized for (k, v) in d.items()))
        params.update(lists)
    elif isinstance(value, dict):
        stack.append([key, value])
    else:
        params.update({key: value})

    for (parent, hash) in stack:
        for (key, value) in hash.iteritems():
            if isinstance(value, dict):
                stack.append([u"{0[parent]}[{0[key]}]".format(dict(parent=parent, key=key)), value])
            else:
                params.update(normalize_param(u"{0[parent]}[{0[key]}]".format(dict(parent=parent, key=key)), value))

    return params

########NEW FILE########
__FILENAME__ = request
import urllib

import requests

import soundcloud
import hashconversions


def is_file_like(f):
    """Check to see if ```f``` has a ```read()``` method."""
    return hasattr(f, 'read') and callable(f.read)


def extract_files_from_dict(d):
    """Return any file objects from the provided dict.

    >>> extract_files_from_dict({
    ... 'oauth_token': 'foo',
    ... 'track': {
    ...   'title': 'bar',
    ...   'asset_data': file('setup.py', 'rb')
    ...  }})  # doctest:+ELLIPSIS
    {'track': {'asset_data': <open file 'setup.py', mode 'rb' at 0x...}}
    """
    files = {}
    for key, value in d.iteritems():
        if isinstance(value, dict):
            files[key] = extract_files_from_dict(value)
        elif is_file_like(value):
            files[key] = value
    return files


def remove_files_from_dict(d):
    """Return the provided dict with any file objects removed.

    >>> remove_files_from_dict({
    ...   'oauth_token': 'foo',
    ...   'track': {
    ...       'title': 'bar',
    ...       'asset_data': file('setup.py', 'rb')
    ...   }
    ... })  # doctest:+ELLIPSIS
    {'track': {'title': 'bar'}, 'oauth_token': 'foo'}
    """
    file_free = {}
    for key, value in d.iteritems():
        if isinstance(value, dict):
            file_free[key] = remove_files_from_dict(value)
        elif not is_file_like(value):
            if hasattr(value, '__iter__'):
                file_free[key] = value
            else:
                if hasattr(value, 'encode'):
                    file_free[key] = value.encode('utf-8')
                else:
                    file_free[key] = str(value)
    return file_free


def namespaced_query_string(d, prefix=""):
    """Transform a nested dict into a string with namespaced query params.

    >>> namespaced_query_string({
    ...  'oauth_token': 'foo',
    ...  'track': {'title': 'bar', 'sharing': 'private'}})  # doctest:+ELLIPSIS
    {'track[sharing]': 'private', 'oauth_token': 'foo', 'track[title]': 'bar'}
    """
    qs = {}
    prefixed = lambda k: prefix and "%s[%s]" % (prefix, k) or k
    for key, value in d.iteritems():
        if isinstance(value, dict):
            qs.update(namespaced_query_string(value, prefix=key))
        else:
            qs[prefixed(key)] = value
    return qs


def make_request(method, url, params):
    """Make an HTTP request, formatting params as required."""
    empty = []

    # TODO
    # del params[key]
    # without list
    for key, value in params.iteritems():
        if value is None:
            empty.append(key)
    for key in empty:
        del params[key]

    # allow caller to disable automatic following of redirects
    allow_redirects = params.get('allow_redirects', True)

    kwargs = {
        'allow_redirects': allow_redirects,
        'headers': {
            'User-Agent': soundcloud.USER_AGENT
        }
    }
    # options, not params
    if 'verify_ssl' in params:
        if params['verify_ssl'] is False:
            kwargs['verify'] = params['verify_ssl']
        del params['verify_ssl']
    if 'proxies' in params:
        kwargs['proxies'] = params['proxies']
        del params['proxies']
    if 'allow_redirects' in params:
        del params['allow_redirects']

    params = hashconversions.to_params(params)
    files = namespaced_query_string(extract_files_from_dict(params))
    data = namespaced_query_string(remove_files_from_dict(params))

    request_func = getattr(requests, method, None)
    if request_func is None:
        raise TypeError('Unknown method: %s' % (method,))

    if method == 'get':
        qs = urllib.urlencode(data)
        result = request_func('%s?%s' % (url, qs), **kwargs)
    else:
        kwargs['data'] = data
        if files:
            kwargs['files'] = files
        result = request_func(url, **kwargs)

    # if redirects are disabled, don't raise for 301 / 302
    if result.status_code in (301, 302):
        if allow_redirects:
            result.raise_for_status()
    else:
        result.raise_for_status()
    return result

########NEW FILE########
__FILENAME__ = resource
try:
    import json
except ImportError:
    import simplejson as json

from UserList import UserList


class Resource(object):
    """Object wrapper for resources.

    Provides an object interface to resources returned by the Soundcloud API.
    """
    def __init__(self, obj):
        self.obj = obj

    def __getstate__(self):
        return self.obj.items()

    def __setstate__(self, items):
        if not hasattr(self, 'obj'):
            self.obj = {}
        for key, val in items:
            self.obj[key] = val

    def __getattr__(self, name):
        if name in self.obj:
            return self.obj.get(name)
        raise AttributeError

    def fields(self):
        return self.obj

    def keys(self):
        return self.obj.keys()


class ResourceList(UserList):
    """Object wrapper for lists of resources."""
    def __init__(self, resources=[]):
        data = [Resource(resource) for resource in resources]
        super(ResourceList, self).__init__(data)


def wrapped_resource(response):
    """Return a response wrapped in the appropriate wrapper type.

    Lists will be returned as a ```ResourceList``` instance,
    dicts will be returned as a ```Resource``` instance.
    """
    # decode response text
    response_content = response.content.decode(response.encoding)

    try:
        content = json.loads(response_content)
    except ValueError:
        # not JSON
        content = response_content
    if isinstance(content, list):
        result = ResourceList(content)
    else:
        result = Resource(content)
    result.raw_data = response_content

    for attr in ('encoding', 'url', 'status_code', 'reason'):
        setattr(result, attr, getattr(response, attr))

    return result

########NEW FILE########
__FILENAME__ = test_client
import soundcloud

from soundcloud.tests.utils import MockResponse

from urllib import urlencode

from nose.tools import eq_, raises
from fudge import patch


def test_kwargs_parsing_valid():
    """Test that valid kwargs are stored as properties on the client."""
    client = soundcloud.Client(client_id='foo', client_secret='foo')
    assert isinstance(client, soundcloud.Client)
    eq_('foo', client.client_id)
    client = soundcloud.Client(client_id='foo', client_secret='bar',
                               access_token='baz', username='you',
                               password='secret', redirect_uri='foooo')
    eq_('foo', client.client_id)
    eq_('baz', client.access_token)


@raises(AttributeError)
def test_kwargs_parsing_invalid():
    """Test that unknown kwargs are ignored."""
    client = soundcloud.Client(foo='bar', client_id='bar')
    client.foo


def test_url_creation():
    """Test that resources are turned into urls properly."""
    client = soundcloud.Client(client_id='foo')
    url = client._resolve_resource_name('tracks')
    eq_('https://api.soundcloud.com/tracks.json', url)
    url = client._resolve_resource_name('/tracks/')
    eq_('https://api.soundcloud.com/tracks.json', url)


def test_url_creation_options():
    """Test that resource resolving works with different options."""
    client = soundcloud.Client(client_id='foo', use_ssl=False)
    client.host = 'soundcloud.dev'
    url = client._resolve_resource_name('apps/132445')
    eq_('http://soundcloud.dev/apps/132445.json', url)


def test_method_dispatching():
    """Test that getattr is doing right by us."""
    client = soundcloud.Client(client_id='foo')
    for method in ('get', 'post', 'put', 'delete', 'head'):
        p = getattr(client, method)
        eq_((method,), p.args)
        eq_('_request', p.func.__name__)


def test_host_config():
    """We should be able to set the host on the client."""
    client = soundcloud.Client(client_id='foo', host='api.soundcloud.dev')
    eq_('api.soundcloud.dev', client.host)
    client = soundcloud.Client(client_id='foo')
    eq_('api.soundcloud.com', client.host)


@patch('requests.get')
def test_disabling_ssl_verification(fake_get):
    """We should be able to disable ssl verification when we are in dev mode"""
    client = soundcloud.Client(client_id='foo', host='api.soundcloud.dev',
                               verify_ssl=False)
    expected_url = '%s?%s' % (
        client._resolve_resource_name('tracks'),
        urlencode({
            'limit': 5,
            'client_id': 'foo'
        }))
    headers = {
        'User-Agent': soundcloud.USER_AGENT
    }
    (fake_get.expects_call()
             .with_args(expected_url,
                        headers=headers,
                        verify=False,
                        allow_redirects=True)
             .returns(MockResponse("{}")))
    client.get('tracks', limit=5)


@raises(AttributeError)
def test_method_dispatching_invalid_method():
    """Test that getattr raises an attributeerror if we give it garbage."""
    client = soundcloud.Client(client_id='foo')
    client.foo()


@patch('requests.get')
def test_method_dispatching_get_request_readonly(fake_get):
    """Test that calling client.get() results in a proper call
    to the get function in the requests module with the provided
    kwargs as the querystring.
    """
    client = soundcloud.Client(client_id='foo')
    expected_url = '%s?%s' % (
        client._resolve_resource_name('tracks'),
        urlencode({
            'limit': 5,
            'client_id': 'foo'
        }))
    headers = {
        'User-Agent': soundcloud.USER_AGENT
    }
    (fake_get.expects_call()
             .with_args(expected_url, headers=headers, allow_redirects=True)
             .returns(MockResponse("{}")))
    client.get('tracks', limit=5)


@patch('requests.post')
def test_method_dispatching_post_request(fake_post):
    """Test that calling client.post() results in a proper call
    to the post function in the requests module.

    TODO: Revise once read/write support has been added.
    """
    client = soundcloud.Client(client_id='foo')
    expected_url = client._resolve_resource_name('tracks')
    data = {
        'client_id': 'foo'
    }
    headers = {
        'User-Agent': soundcloud.USER_AGENT
    }
    (fake_post.expects_call()
              .with_args(expected_url,
                         data=data,
                         headers=headers,
                         allow_redirects=True)
              .returns(MockResponse("{}")))
    client.post('tracks')


@patch('requests.get')
def test_proxy_servers(fake_request):
    """Test that providing a dictionary of proxy servers works."""
    proxies = {
        'http': 'myproxyserver:1234'
    }
    client = soundcloud.Client(client_id='foo', proxies=proxies)
    expected_url = "%s?%s" % (
        client._resolve_resource_name('me'),
        urlencode({
            'client_id': 'foo'
        })
    )
    headers = {
        'User-Agent': soundcloud.USER_AGENT
    }
    (fake_request.expects_call()
                 .with_args(expected_url,
                            headers=headers,
                            proxies=proxies,
                            allow_redirects=True)
                 .returns(MockResponse("{}")))
    client.get('/me')

########NEW FILE########
__FILENAME__ = test_encoding
# -*- coding: utf-8
import soundcloud

from soundcloud.tests.utils import MockResponse

from fudge import patch


@patch('requests.put')
def test_non_ascii_data(fake_put):
    """Test that non-ascii characters are accepted."""
    client = soundcloud.Client(client_id='foo', client_secret='foo')
    title = u'Föo Baß'
    fake_put.expects_call().returns(MockResponse("{}"))
    client.put('/tracks', track={
        'title': title
    })

########NEW FILE########
__FILENAME__ = test_oauth
from contextlib import contextmanager
from urllib import urlencode

from nose.tools import eq_

import fudge
import soundcloud

from soundcloud.tests.utils import MockResponse


@contextmanager
def non_expiring_token_response(fake_http_request):
    response = MockResponse(
        '{"access_token":"access-1234","scope":"non-expiring"}')
    fake_http_request.expects_call().returns(response)
    yield


@contextmanager
def expiring_token_response(fake_http_request):
    response = MockResponse(
        '{"access_token":"access-1234","expires_in":12345,"scope":"*",' +
        '"refresh_token":"refresh-1234"}')
    fake_http_request.expects_call().returns(response)
    yield


@contextmanager
def positive_refresh_token_response(fake_http_request):
    response = MockResponse(
        '{"access_token":"access-2345","expires_in":21599,"scope":"*",' +
        '"refresh_token":"refresh-2345"}')
    fake_http_request.expects_call().returns(response)
    yield


def test_authorize_url_construction():
    """Test that authorize url is being generated properly."""
    client = soundcloud.Client(client_id='foo', client_secret='bar',
                               redirect_uri='http://example.com/callback')
    eq_('https://api.soundcloud.com/connect?%s' % (urlencode({
        'scope': 'non-expiring',
        'client_id': 'foo',
        'response_type': 'code',
        'redirect_uri': 'http://example.com/callback'
     }),), client.authorize_url())


@fudge.patch('requests.post')
def test_exchange_code_non_expiring(fake):
    """Test that exchanging a code for an access token works."""
    with non_expiring_token_response(fake):
        client = soundcloud.Client(client_id='foo', client_secret='bar',
                                   redirect_uri='http://example.com/callback')
        token = client.exchange_token('this-is-a-code')
        eq_('access-1234', token.access_token)
        eq_('non-expiring', token.scope)
        eq_('access-1234', client.access_token)


@fudge.patch('requests.post')
def test_exchange_code_expiring(fake):
    """Excluding a scope=non-expiring arg should generate a refresh token."""
    with expiring_token_response(fake):
        client = soundcloud.Client(client_id='foo', client_secret='bar',
                                   redirect_uri='http://example.com/callback',
                                   scope='*')
        eq_('https://api.soundcloud.com/connect?%s' % (urlencode({
            'scope': '*',
            'client_id': 'foo',
            'response_type': 'code',
            'redirect_uri': 'http://example.com/callback'
        }),), client.authorize_url())
        token = client.exchange_token('this-is-a-code')
        eq_('access-1234', token.access_token)
        eq_('refresh-1234', token.refresh_token)


@fudge.patch('requests.post')
def test_refresh_token_flow(fake):
    """Providing a refresh token should generate a new access token."""
    with positive_refresh_token_response(fake):
        client = soundcloud.Client(client_id='foo', client_secret='bar',
                                   refresh_token='refresh-token')
        eq_('access-2345', client.token.access_token)

########NEW FILE########
__FILENAME__ = test_requests
from contextlib import contextmanager

import fudge
import soundcloud

from nose.tools import raises, assert_raises
from requests.exceptions import HTTPError

from soundcloud.tests.utils import MockResponse


class MockRaw(object):
    """Simple mock for the raw response in requests model."""
    def __init__(self):
        self.reason = "foo"


@contextmanager
def response_status(fake_http_request, status):
    response = MockResponse('{}', status_code=status)
    response.raw = MockRaw()
    fake_http_request.expects_call().returns(response)
    yield


@fudge.patch('requests.get')
def test_bad_responses(fake):
    """Anything in the 400 or 500 range should raise an exception."""
    client = soundcloud.Client(client_id='foo', client_secret='foo')

    for status in range(400, 423):
        with response_status(fake, status):
            assert_raises(HTTPError, lambda: client.get('/me'))
    for status in (500, 501, 502, 503, 504, 505):
        with response_status(fake, status):
            assert_raises(HTTPError, lambda: client.get('/me'))

@fudge.patch('requests.get')
def test_ok_response(fake):
    """A 200 range response should be fine."""
    client = soundcloud.Client(client_id='foo', client_secret='foo')
    for status in (200, 201, 202, 203, 204, 205, 206):
        with response_status(fake, status):
            user = client.get('/me')


########NEW FILE########
__FILENAME__ = test_resource
try:
    import json
except ImportError:
    import simplejson as json

from soundcloud.resource import wrapped_resource, ResourceList, Resource
from soundcloud.tests.utils import MockResponse

from nose.tools import eq_


def test_json_list():
    """Verify that a json list is wrapped in a ResourceList object."""
    resources = wrapped_resource(MockResponse(json.dumps([{'foo': 'bar'}]),
                                              encoding='utf-8'))
    assert isinstance(resources, ResourceList)
    eq_(1, len(resources))
    eq_('bar', resources[0].foo)


def test_json_object():
    """Verify that a json object is wrapped in a Resource object."""
    resource = wrapped_resource(MockResponse(json.dumps({'foo': 'bar'}),
                                             encoding='utf-8'))
    assert isinstance(resource, Resource)
    eq_('bar', resource.foo)


def test_properties_copied():
    """Certain properties should be copied to the wrapped resource."""
    response = MockResponse(json.dumps({'foo': 'bar'}),
                            encoding='utf-8',
                            status_code=200,
                            reason='OK',
                            url='http://example.com')
    resource = wrapped_resource(response)
    eq_(200, resource.status_code)
    eq_('OK', resource.reason)
    eq_('utf-8', resource.encoding)
    eq_('http://example.com', resource.url)

########NEW FILE########
__FILENAME__ = utils
from requests.models import Response


class MockResponse(Response):
    def __init__(self, content, encoding='utf-8',
                 status_code=200, url=None, reason='OK'):
        self._content = content.encode('utf-8')
        self.encoding = encoding
        self.status_code = status_code
        self.url = url
        self.reason = reason

########NEW FILE########
