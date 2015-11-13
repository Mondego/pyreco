__FILENAME__ = hammock
import requests
import copy


class Hammock(object):
    """Chainable, magical class helps you make requests to RESTful services"""

    HTTP_METHODS = ['get', 'options', 'head', 'post', 'put', 'patch', 'delete']

    def __init__(self, name=None, parent=None, append_slash=False, **kwargs):
        """Constructor

        Arguments:
            name -- name of node
            parent -- parent node for chaining
            append_slash -- flag if you want a trailing slash in urls
            **kwargs -- `requests` session be initiated with if any available
        """
        self._name = name
        self._parent = parent
        self._append_slash = append_slash
        self._session = requests.session()
        for k, v in kwargs.items():
            orig = getattr(self._session, k)  # Let it throw exception
            if isinstance(orig, dict):
                orig.update(v)
            else:
                setattr(self._session, k, v)

    def _spawn(self, name):
        """Returns a shallow copy of current `Hammock` instance as nested child

        Arguments:
            name -- name of child
        """
        child = copy.copy(self)
        child._name = name
        child._parent = self
        return child

    def __getattr__(self, name):
        """Here comes some magic. Any absent attribute typed within class
        falls here and return a new child `Hammock` instance in the chain.
        """
        # Ignore specials (Otherwise shallow copying causes infinite loops)
        if name.startswith('__'):
            raise AttributeError(name)
        return self._spawn(name)

    def __iter__(self):
        """Iterator implementation which iterates over `Hammock` chain."""
        current = self
        while current:
            if current._name:
                yield current
            current = current._parent

    def _chain(self, *args):
        """This method converts args into chained Hammock instances

        Arguments:
            *args -- array of string representable objects
        """
        chain = self
        for arg in args:
            chain = chain._spawn(str(arg))
        return chain

    def _close_session(self):
        """Closes session if exists"""
        if self._session:
            self._session.close()

    def __call__(self, *args):
        """Here comes second magic. If any `Hammock` instance called it
        returns a new child `Hammock` instance in the chain
        """
        return self._chain(*args)

    def _url(self, *args):
        """Converts current `Hammock` chain into a url string

        Arguments:
            *args -- extra url path components to tail
        """
        path_comps = [mock._name for mock in self._chain(*args)]
        url = "/".join(reversed(path_comps))
        if self._append_slash:
            url = url + "/"
        return url

    def __repr__(self):
        """ String representaion of current `Hammock` chain"""
        return self._url()

    def _request(self, method, *args, **kwargs):
        """
        Makes the HTTP request using requests module
        """
        return self._session.request(method, self._url(*args), **kwargs)


def bind_method(method):
    """Bind `requests` module HTTP verbs to `Hammock` class as
    static methods."""
    def aux(hammock, *args, **kwargs):
        return hammock._request(method, *args, **kwargs)
    return aux

for method in Hammock.HTTP_METHODS:
    setattr(Hammock, method.upper(), bind_method(method))

########NEW FILE########
__FILENAME__ = test_hammock
import unittest

from httpretty import HTTPretty
from httpretty import httprettified

from hammock import Hammock


class TestCaseWrest(unittest.TestCase):

    HOST = 'localhost'
    PORT = 8000
    BASE_URL = 'http://%s:%s' % (HOST, PORT)
    PATH = '/sample/path/to/resource'
    URL = BASE_URL + PATH

    @httprettified
    def test_methods(self):
        client = Hammock(self.BASE_URL)
        for method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
            HTTPretty.register_uri(getattr(HTTPretty, method), self.URL)
            request = getattr(client, method)
            resp = request('sample', 'path', 'to', 'resource')
            self.assertEqual(HTTPretty.last_request.method, method)

    @httprettified
    def test_urls(self):
        HTTPretty.register_uri(HTTPretty.GET, self.URL)
        client = Hammock(self.BASE_URL)
        combs = [
            client.sample.path.to.resource,
            client('sample').path('to').resource,
            client('sample', 'path', 'to', 'resource'),
            client('sample')('path')('to')('resource'),
            client.sample('path')('to', 'resource'),
            client('sample', 'path',).to.resource
        ]

        for comb in combs:
            self.assertEqual(str(comb), self.URL)
            resp = comb.GET()
            self.assertEqual(HTTPretty.last_request.path, self.PATH)

    @httprettified
    def test_append_slash_option(self):
        HTTPretty.register_uri(HTTPretty.GET, self.URL + '/')
        client = Hammock(self.BASE_URL, append_slash=True)
        resp = client.sample.path.to.resource.GET()
        self.assertEqual(HTTPretty.last_request.path, self.PATH + '/')

    @httprettified
    def test_inheritance(self):
        """https://github.com/kadirpekel/hammock/pull/5/files#L1R99"""
        class CustomHammock(Hammock):
            def __init__(self, name=None, parent=None, **kwargs):
                if 'testing' in kwargs:
                    self.testing = kwargs.pop('testing')
                super(CustomHammock, self).__init__(name, parent, **kwargs)

            def _url(self, *args):
                assert isinstance(self.testing, bool)
                global called
                called = True
                return super(CustomHammock, self)._url(*args)

        global called
        called = False
        HTTPretty.register_uri(HTTPretty.GET, self.URL)
        client = CustomHammock(self.BASE_URL, testing=True)
        resp = client.sample.path.to.resource.GET()
        self.assertTrue(called)
        self.assertEqual(HTTPretty.last_request.path, self.PATH)

    @httprettified
    def test_session(self):
        ACCEPT_HEADER = 'application/json'
        kwargs = {
            'headers': {'Accept': ACCEPT_HEADER},
            'auth': ('foo', 'bar'),
        }
        client = Hammock(self.BASE_URL, **kwargs)
        HTTPretty.register_uri(HTTPretty.GET, self.URL)
        client.sample.path.to.resource.GET()
        request = HTTPretty.last_request
        self.assertIn('User-Agent', request.headers)
        self.assertIn('Authorization', request.headers)
        self.assertIn('Accept', request.headers)
        self.assertEqual(request.headers.get('Accept'), ACCEPT_HEADER)
        client.sample.path.to.resource.GET()
        request = HTTPretty.last_request
        self.assertIn('User-Agent', request.headers)
        self.assertIn('Authorization', request.headers)
        self.assertIn('Accept', request.headers)
        self.assertEqual(request.headers.get('Accept'), ACCEPT_HEADER)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
