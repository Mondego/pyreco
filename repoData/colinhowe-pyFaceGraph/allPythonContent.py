__FILENAME__ = api
import socket
import ujson as json
from urllib import urlencode, unquote

FB_READ_TIMEOUT = 180

class Api:
    
    def __init__(self, access_token=None, request=None, cookie=None, app_id=None, stack=None,
                       err_handler=None, timeout=FB_READ_TIMEOUT, urllib2=None, httplib=None,
                       retries=5):
        
        self.uid = None
        self.access_token = access_token
        self.stack = stack if stack else []
        self.cookie = cookie
        self.err_handler = err_handler
        self.retries = retries
        
        if urllib2 is None:
            import urllib2
        self.urllib2 = urllib2
        if httplib is None:
            import httplib
        self.httplib = httplib
        self.timeout = timeout

        socket.setdefaulttimeout(self.timeout)
        
        if self.cookie:
            self.load_cookie()
        elif request:
            self.check_cookie(request, app_id)

    def __sentry__(self):
        return u'FB(method: %s, access_token: %s)' % (self.__method(), self.access_token)

    def __repr__(self):
        return '<FB(%r) at 0x%x>' % (self.__method(), id(self))
    
    def __method(self):
        return u".".join(self.stack)
    
    def __getitem__(self, name):
        """
        This method returns a new FB and allows us to chain attributes, e.g. fb.stream.publish
        A stack of attributes is maintained so that we can call the correct method later
        """
        s = []
        s.extend(self.stack)
        s.append(name)
        return self.__class__(stack=s, access_token=self.access_token, cookie=self.cookie, err_handler=self.err_handler,
                              timeout=self.timeout, retries=self.retries, urllib2=self.urllib2, httplib=self.httplib)
    
    def __getattr__(self, name):
        """
        We trigger __getitem__ here so that both self.method.name and self['method']['name'] work
        """
        return self[name]
    
    def __call__(self, _retries=None, *args, **kwargs):
        """
        Executes an old REST api method using the stored method stack
        """
        _retries = _retries or self.retries
        
        if len(self.stack)>0:
            kwargs.update({"format": "JSON"})
            method = self.__method()
            # Custom overrides
            if method == "photos.upload":
                return self.__photo_upload(**kwargs)            
            
            # UTF8
            utf8_kwargs = {}
            for (k,v) in kwargs.iteritems():
                try:
                    v = v.encode('UTF-8')
                except AttributeError: pass
                utf8_kwargs[k] = v
            
            url = "https://api.facebook.com/method/%s?" % method
            if self.access_token:
                url += 'access_token=%s&' % self.access_token        
            url += urlencode(utf8_kwargs)
            
            attempt = 0
            while True:
                try:
                    response = self.urllib2.urlopen(url, timeout=self.timeout).read()
                    break
                except self.urllib2.HTTPError, e:
                    response = e.fp.read()
                    break
                except (self.httplib.BadStatusLine, IOError):
                    if attempt < _retries:
                        attempt += 1
                    else:
                        raise

            return self.__process_response(response, params=kwargs)

    def __process_response(self, response, params=None):
        try:
            data = json.loads(response)
        except ValueError:
            data = response
        try:
            if 'error_code' in data:
                e = ApiException(code=int(data.get('error_code')),
                                 message=data.get('error_msg'),
                                 method=self.__method(), 
                                 params=params,
                                 api=self)
                if self.err_handler:
                    return self.err_handler(e=e)
                else:
                    raise e
                                                
        except TypeError:
            pass
        return data

    def __photo_upload(self, _retries=None, **kwargs):
        _retries = _retries or self.retries
        
        body = []
        crlf = '\r\n'
        boundary = "conversocialBoundary"
        
        # UTF8
        utf8_kwargs = {}
        for (k,v) in kwargs.iteritems():
            try:
                v = v.encode('UTF-8')
            except AttributeError: pass
            utf8_kwargs[k] = v
        
        # Add args
        utf8_kwargs.update({'access_token': self.access_token})
        for (k,v) in utf8_kwargs.iteritems():
            if k=='photo': continue
            body.append("--"+boundary)
            body.append('Content-Disposition: form-data; name="%s"' % k) 
            body.append('')
            body.append(str(v))
        
        # Add raw image data
        photo = utf8_kwargs.get('photo')
        photo.open()
        data = photo.read()
        photo.close()
        
        body.append("--"+boundary)
        body.append('Content-Disposition: form-data; filename="myfilewhichisgood.png"')
        body.append('Content-Type: image/png')
        body.append('')
        body.append(data)
        
        body.append("--"+boundary+"--")
        body.append('')
        
        body = crlf.join(body)
                
        # Post to server
        r = self.httplib.HTTPSConnection('api.facebook.com', timeout=self.timeout)
        headers = {'Content-Type': 'multipart/form-data; boundary=%s' % boundary,
                   'Content-Length': str(len(body)),
                   'MIME-Version': '1.0'}
        
        r.request('POST', '/method/photos.upload', body, headers)
        
        attempt = 0
        while True:
            try:
                response = r.getresponse().read()
                return self.__process_response(response, params=kwargs)
            except (self.httplib.BadStatusLine, IOError):
                if attempt < _retries:
                    attempt += 1
                else:
                    raise
            finally:
                r.close()            
        
    def check_cookie(self, request, app_id):
        """"
        Parses the fb cookie if present
        """
        cookie = request.COOKIES.get("fbs_%s" % app_id)
        if cookie:
            self.cookie = dict([(v.split("=")[0], unquote(v.split("=")[1])) for v in cookie.split('&')])
            self.load_cookie()

    def load_cookie(self):
        """
        Checks for user FB cookie and sets as instance attributes.
        Contains:
            access_token    OAuth 2.0 access token used by FB for authentication
            uid             Users's Facebook UID
            expires         Expiry date of cookie, will be 0 for constant auth
            secret          Application secret
            sig             Sig parameter
            session_key     Old-style session key, replaced by access_token, deprecated
        """
        if self.cookie:
            for k in self.cookie:
                setattr(self, k, self.cookie.get(k))

    def __fetch(self, url):
        try:
            response = self.urllib2.urlopen(url, timeout=self.timeout)
        except self.urllib2.HTTPError, e:
            response = e.fp
        return json.load(response)
    
    def verify_token(self, tries=1):
        url = "https://graph.facebook.com/me?access_token=%s" % self.access_token
        for n in range(tries):
            data = self.__fetch(url)
            if 'error' in data:
                pass
            else:
                return True
        
    def exists(self, object_id):
        url = "https://graph.facebook.com/%s?access_token=%s" % (object_id, self.access_token)
        data = self.__fetch(url)
        if data:
            return True
        else:
            return False

class ApiException(Exception):
    def __init__(self, code, message, args=None, params=None, api=None, method=None):
        Exception.__init__(self)
        if args is not None:
            self.args = args
        self.message = message
        self.code = code
        self.params = params
        self.api = api
        self.method = method
        
    def __repr__(self):
        return str(self)
    
    def __str__(self):
        str = "%s, Method: %s" % (self.message, self.method)
        if self.params:
            str = "%s, Params: %s" % (str, self.params)
        if self.code:
            str =  "(#%s) %s" % (self.code, str)
        return str

########NEW FILE########
__FILENAME__ = fql
# -*- coding: utf-8 -*-

import urllib2

import bunch
import ujson as json
from graph import GraphException
from url_operations import add_path, update_query_params

class FQL(object):
    
    """
    A maker of single and multiple FQL queries.
    
    Usage
    =====
    
    Single queries:
    
        >>> q = FQL('access_token')
        >>> result = q("SELECT post_id FROM stream WHERE source_id = ...")
        >>> result
        [Bunch(post_id='XXXYYYZZZ'), ...]
        
        >>> result[0]
        Bunch(post_id='XXXYYYZZZ')
        
        >>> result[0].post_id
        'XXXYYYZZZ'
    
    Multiple queries:
    
        >>> q = FQL('access_token')
        >>> result = q.multi(dict(query1="SELECT...", query2="SELECT..."))
        
        >>> result[0].name
        'query1'
        >>> result[0].fql_result_set
        [...]
        
        >>> result[1].name
        'query2'
        >>> result[1].fql_result_set
        [...]
    
    """
    
    ENDPOINT = 'https://api.facebook.com/method/'
    
    def __init__(self, access_token=None, err_handler=None):
        self.access_token = access_token
        self.err_handler = err_handler
    
    def __call__(self, query, **params):
        
        """
        Execute a single FQL query (using `fql.query`).
        
        Example:
        
            >>> q = FQL('access_token')
            >>> result = q("SELECT post_id FROM stream WHERE source_id = ...")
            >>> result
            [Bunch(post_id='XXXYYYZZZ'), ...]
            
            >>> result[0]
            Bunch(post_id='XXXYYYZZZ')
            
            >>> result[0].post_id
            'XXXYYYZZZ'
        
        """
        
        url = add_path(self.ENDPOINT, 'fql.query')
        params.update(query=query, access_token=self.access_token,
                      format='json')
        url = update_query_params(url, params)
        
        return self.fetch_json(url)
    
    def multi(self, queries, **params):
        
        """
        Execute multiple FQL queries (using `fql.multiquery`).
        
        Example:
        
            >>> q = FQL('access_token')
            >>> result = q.multi(dict(query1="SELECT...", query2="SELECT..."))
            
            >>> result[0].name
            'query1'
            >>> result[0].fql_result_set
            [...]
            
            >>> result[1].name
            'query2'
            >>> result[1].fql_result_set
            [...]
        
        """
        
        url = add_path(self.ENDPOINT, 'fql.multiquery')
        params.update(queries=json.dumps(queries),
                      access_token=self.access_token, format='json')
        url = update_query_params(url, params)
        
        return self.fetch_json(url)
    
    @classmethod
    def fetch_json(cls, url, data=None):
        response = json.loads(cls.fetch(url, data=data))
        if isinstance(response, dict):
            if response.get("error_msg"):
                code = response.get("error_code")
                msg = response.get("error_msg")
                args = response.get("request_args")
                raise GraphException(code, msg, args=args)
        return bunch.bunchify(response)
    
    @staticmethod
    def fetch(url, data=None):
        conn = urllib2.urlopen(url, data=data)
        try:
            return conn.read()
        finally:
            conn.close()

########NEW FILE########
__FILENAME__ = graph
# -*- coding: utf-8 -*-
import logging
import re
import urllib
import urllib2 as default_urllib2
import httplib as default_httplib
import traceback

from facegraph.url_operations import (add_path, get_host,
        add_query_params, update_query_params, get_path)

import bunch
import ujson as json
from functools import partial

p = "^\(#(\d+)\)"
code_re = re.compile(p)

__all__ = ['Graph']

log = logging.getLogger('pyfacegraph')

class Graph(object):
    
    """
    Proxy for accessing the Facebook Graph API.
    
    This class uses dynamic attribute handling to provide a flexible and
    future-proof interface to the Graph API.
    
    Tutorial
    ========
    
    To get started using the API, create a new `Graph` instance with an access
    token:
    
        >>> g = Graph(access_token)  # Access token is optional.
        >>> g
        <Graph('https://graph.facebook.com/') at 0x...>
    
    Addressing Nodes
    ----------------
    
    Each `Graph` contains an access token and a URL. The graph you just created
    will have its URL set to 'https://graph.facebook.com/' by default (this is
    defined as the class attribute `Graph.API_ROOT`).

        >>> print g.url
        https://graph.facebook.com/
    
    To address child nodes within the Graph API, `Graph` supports dynamic
    attribute and item lookups:
    
        >>> g.me
        <Graph('https://graph.facebook.com/me') at 0x...>
        >>> g.me.home
        <Graph('https://graph.facebook.com/me/home') at 0x...>
        >>> g['me']['home']
        <Graph('https://graph.facebook.com/me/home') at 0x...>
        >>> g[123456789]
        <Graph('https://graph.facebook.com/123456789') at 0x...>
    
    Note that a `Graph` instance is rarely modified; these methods return copies
    of the original object. In addition, the API is lazy: HTTP requests will
    never be made unless you explicitly make them.
    
    Retrieving Nodes
    ----------------
    
    You can fetch data by calling a `Graph` instance:
    
        >>> about_me = g.me()
        >>> about_me
        Node({'about': '...', 'id': '1503223370'})
    
    This returns a `Node` object, which contains the retrieved data. `Node` is
    a subclass of `bunch.Bunch`, so you can access keys using attribute syntax:
    
        >>> about_me.id
        '1503223370'
        >>> about_me.first_name
        'Zachary'
        >>> about_me.hometown.name
        'London, United Kingdom'
    
    Accessing non-existent attributes or items will return a `Graph` instance
    corresponding to a child node. This `Graph` can then be called normally, to
    retrieve the child node it represents:
    
        >>> about_me.home
        <Graph('https://graph.facebook.com/me/home') at 0x...>
        >>> about_me.home()
        Node({'data': [...]})
    
    See `Node`’s documentation for further examples.
    
    Creating, Updating and Deleting Nodes
    -------------------------------------
    
    With the Graph API, node manipulation is done via HTTP POST requests. The
    `post()` method on `Graph` instances will POST to the current URL, with
    varying semantics for each endpoint:
    
        >>> post = g.me.feed.post(message="Test.")  # Status update
        >>> post
        Node({'id': '...'})
        >>> g[post.id].comments.post(message="A comment.") # Comment on the post
        Node({'id': '...'})
        >>> g[post.id].likes.post()  # Like the post
        True
        
        >>> event = g[121481007877204]()
        >>> event.name
        'Facebook Developer Garage London May 2010'
        >>> event.rsvp_status is None
        True
        >>> event.attending.post()  # Attend the given event
        True
    
    Deletes are just POST requests with `?method=delete`; the `delete()` method
    is a helpful shortcut:
    
        >>> g[post.id].delete()
        True
    
    """
    
    API_ROOT = 'https://graph.facebook.com/'
    DEFAULT_TIMEOUT = 0 # No timeout as default
    
    def __init__(self, access_token=None, err_handler=None, timeout=DEFAULT_TIMEOUT, retries=5, urllib2=None, httplib=None, **state):
        self.access_token = access_token
        self.err_handler = err_handler
        self.url = self.API_ROOT
        self.timeout = timeout
        self.retries = retries
        self.__dict__.update(state)
        if urllib2 is None:
            import urllib2
        self.urllib2 = urllib2
        if httplib is None:
            import httplib
        self.httplib = httplib
    
    def __repr__(self):
        return '<Graph(%r) at 0x%x>' % (self.url, id(self))
    
    def copy(self, **update):
        """Copy this Graph, optionally overriding some attributes."""
        return type(self)(access_token=self.access_token, 
                          err_handler=self.err_handler,
                          timeout=self.timeout,
                          retries=self.retries,
                          urllib2=self.urllib2,
                          httplib=self.httplib,
                          **update)
    
    def __getitem__(self, item):
        if isinstance(item, slice):
            log.debug('Deprecated magic slice!')
            log.debug( traceback.format_stack())
            return self._range(item.start, item.stop)
        return self.copy(url=add_path(self.url, unicode(item)))
    
    def __getattr__(self, attr):
        return self[attr]

    def _range(self, start, stop):
        params = {'offset': start,
                  'limit': stop - start}
        return self.copy(url=add_query_params(self.url, params))

    def with_url_params(self, param, val):
        """
            this used to overload the bitwise OR op
        """
        return self.copy(url=update_query_params(self.url, (param, val)))

    def __call__(self, **params):
        log.debug('Deprecated magic call!')
        log.debug( traceback.format_stack())
        return self.call_fb(**params)
    
    def call_fb(self, **params):
        """Read the current URL, and JSON-decode the results."""

        if self.access_token:
            params['access_token'] = self.access_token
        url = update_query_params(self.url, params)
        data = json.loads(self.fetch(url,
                                     timeout=self.timeout,
                                     retries=self.retries,
                                     urllib2=self.urllib2,
                                     httplib=self.httplib))
        return self.process_response(data, params)

    def __iter__(self):
        raise TypeError('%r object is not iterable' % self.__class__.__name__)

    def __sentry__(self):
        return 'Graph(url: %s, params: %s)' % (self.url, repr(self.__dict__))
    
    def fields(self, *fields):
        """Shortcut for `?fields=x,y,z`."""
        return self | ('fields', ','.join(fields))
    
    def ids(self, *ids):
        """Shortcut for `?ids=1,2,3`."""
        
        return self | ('ids', ','.join(map(str, ids)))
    
    def process_response(self, data, params, method=None):
        if isinstance(data, dict):
            if data.get("error"):
                code = data["error"].get("code")
                if code is None:
                    code = data["error"].get("error_code")
                msg = data["error"].get("message")
                if msg is None:
                    msg = data["error"].get("error_msg")
                if code is None:
                    code_match = code_re.match(msg)
                    if code_match is not None:
                        code = int(code_match.group(1))
                e = GraphException(code, msg, graph=self, params=params, method=method)
                if self.err_handler:
                    return self.err_handler(e=e)
                else:
                    raise e
            return bunch.bunchify(data)
        return data
    
    def post(self, **params):
        """
        POST to this URL (with parameters); return the JSON-decoded result.
        
        Example:
        
            >>> Graph('ACCESS TOKEN').me.feed.post(message="Test.")
            Node({'id': '...'})
        
        Some methods allow file attachments so uses MIME request to send those through.
        Must pass in a file object as 'file'
        """
        
        if self.access_token:
            params['access_token'] = self.access_token
        
        if get_path(self.url).split('/')[-1] in ['photos']:
            params['timeout'] = self.timeout
            params['httplib'] = self.httplib
            fetch = partial(self.post_mime, 
                            self.url,
                            httplib=self.httplib,
                            retries=self.retries, 
                            **params)
        else:
            params = dict([(k, v.encode('UTF-8')) for (k,v) in params.iteritems() if v is not None])
            fetch = partial(self.fetch, 
                            self.url, 
                            urllib2=self.urllib2,
                            httplib=self.httplib,
                            timeout=self.timeout,
                            retries=self.retries, 
                            data=urllib.urlencode(params))
        
        data = json.loads(fetch())
        return self.process_response(data, params, "post")
    
    def post_file(self, file, **params):
        if self.access_token:
            params['access_token'] = self.access_token
        params['file'] = file
        params['timeout'] = self.timeout
        params['httplib'] = self.httplib
        data = json.loads(self.post_mime(self.url, **params))
        
        return self.process_response(data, params, "post_file")
    
    @staticmethod
    def post_mime(url, httplib=default_httplib, timeout=DEFAULT_TIMEOUT, retries=5, **kwargs):
        body = []
        crlf = '\r\n'
        boundary = "graphBoundary"
        
        # UTF8 params
        utf8_kwargs = dict([(k, v.encode('UTF-8')) for (k,v) in kwargs.iteritems() if k != 'file' and v is not None])
        
        # Add args
        for (k,v) in utf8_kwargs.iteritems():
            body.append("--"+boundary)
            body.append('Content-Disposition: form-data; name="%s"' % k) 
            body.append('')
            body.append(str(v))
        
        # Add raw data
        file = kwargs.get('file')
        if file:
            file.open()
            data = file.read()
            file.close()
            
            body.append("--"+boundary)
            body.append('Content-Disposition: form-data; filename="facegraphfile.png"')
            body.append('')
            body.append(data)
            
            body.append("--"+boundary+"--")
            body.append('')
        
        body = crlf.join(body)
        
        # Post to server
        kwargs = {}
        if timeout:
            kwargs = {'timeout': timeout}
        r = httplib.HTTPSConnection(get_host(url), **kwargs)
        headers = {'Content-Type': 'multipart/form-data; boundary=%s' % boundary,
                   'Content-Length': str(len(body)),
                   'MIME-Version': '1.0'}
        
        r.request('POST', get_path(url).encode(), body, headers)
        attempt = 0
        while True:
            try:
                return r.getresponse().read()
            except (httplib.BadStatusLine, IOError):
                if attempt < retries:
                    attempt += 1
                else:
                    raise
            finally:
                r.close()
    
    def delete(self):
        """
        Delete this resource. Sends a POST with `?method=delete`
        """
        return self.post(method='delete')
    
    @staticmethod
    def fetch(url, data=None, urllib2=default_urllib2, httplib=default_httplib, timeout=DEFAULT_TIMEOUT, retries=None):
        """
        Fetch the specified URL, with optional form data; return a string.
        
        This method exists mainly for dependency injection purposes. By default
        it uses urllib2; you may override it and use an alternative library.
        """
        conn = None
        attempt = 0
        while True:
            try:
                kwargs = {}
                if timeout:
                    kwargs = {'timeout': timeout}
                conn = urllib2.urlopen(url, data=data, **kwargs)
                return conn.read()
            except urllib2.HTTPError, e:
                return e.fp.read()        
            except (httplib.BadStatusLine, IOError):
                if attempt < retries:
                    attempt += 1
                else:
                    raise
            finally:
                conn and conn.close()

    def __sentry__(self):
        """
        Transform the graph object into something that sentry can
        understand
        """
        return "Graph(%s, %s)" % (self.url, str(self.__dict__))


class GraphException(Exception):
    def __init__(self, code, message, args=None, params=None, graph=None, method=None):
        Exception.__init__(self)
        if args is not None:
            self.args = args
        self.message = message
        self.code = code
        self.params = params
        self.graph = graph
        self.method = method

    def __repr__(self):
        return str(self)

    def __str__(self):
        s = self.message
        if self.graph:
            s += "Node: %s" % self.graph.url
        if self.params:
            s += ", Params: %s" % self.params
        if self.code:
            s +=  ", (%s)" % self.code
        return s

########NEW FILE########
__FILENAME__ = url_operations
import urllib
import urlparse

def get_path(url):
    scheme, host, path, query, fragment = urlparse.urlsplit(url)
    return path

def get_host(url):
    scheme, host, path, query, fragment = urlparse.urlsplit(url)
    return host

def add_path(url, new_path):
    """Given a url and path, return a new url that combines
    the two.
    """
    scheme, host, path, query, fragment = urlparse.urlsplit(url)
    new_path = new_path.lstrip('/')
    if path.endswith('/'):
        path += new_path
    else:
        path += '/' + new_path
    return urlparse.urlunsplit([scheme, host, path, query, fragment])

def _query_param(key, value):
    """ensure that a query parameter's value is a string
    of bytes in UTF-8 encoding.
    """
    if isinstance(value, unicode):
        pass
    elif isinstance(value, str):
        value = value.decode('utf-8')
    else:
        value = unicode(value)
    return key, value.encode('utf-8')

def _make_query_tuples(params):
    if hasattr(params, 'items'):
        return [_query_param(*param) for param in params.items()]
    else:
        return [_query_param(*params)]

def add_query_params(url, params):
    """use the _update_query_params function to set a new query
    string for the url based on params.
    """
    return update_query_params(url, params, update=False)

def update_query_params(url, params, update=True):
    """Given a url and a tuple or dict of parameters, return
    a url that includes the parameters as a properly formatted
    query string.

    If update is True, change any existing values to new values
    given in params.
    """
    scheme, host, path, query, fragment = urlparse.urlsplit(url)

    # urlparse.parse_qsl gives back url-decoded byte strings. Leave these as
    # they are: they will be re-urlencoded below
    query_bits = [(k, v) for k, v in urlparse.parse_qsl(query)]
    if update:
        query_bits = dict(query_bits)
        query_bits.update(_make_query_tuples(params))
    else:
        query_bits.extend(_make_query_tuples(params))

    query = urllib.urlencode(query_bits)
    return urlparse.urlunsplit([scheme, host, path, query, fragment])


########NEW FILE########
__FILENAME__ = test_url_operations
from unittest import TestCase
from facegraph import graph
from facegraph import url_operations as ops
from facegraph.fql import FQL
from mock import patch

class UrlOperationsTests(TestCase):
    def test_get_path(self):
        self.assertEquals('', ops.get_path(u'http://a.com'))
        self.assertEquals('/', ops.get_path(u'http://a.com/'))
        self.assertEquals('/a', ops.get_path(u'http://a.com/a'))
        self.assertEquals('/a/', ops.get_path(u'http://a.com/a/'))
        self.assertEquals('/a/b', ops.get_path(u'http://a.com/a/b'))

    def test_get_host(self):
        self.assertEquals('a.com', ops.get_host('http://a.com'))
        self.assertEquals('a.com', ops.get_host('http://a.com/a/b'))
        self.assertEquals('a.com', ops.get_host('http://a.com/a?a=b'))

    def test_add_path(self):
        url = u'http://a.com'
        self.assertEquals('http://a.com/', ops.add_path(url, ''))
        self.assertEquals('http://a.com/path', ops.add_path(url, 'path'))
        self.assertEquals('http://a.com/path', ops.add_path(url, '/path'))
        self.assertEquals('http://a.com/path/', ops.add_path(url, 'path/'))
        self.assertEquals('http://a.com/path/', ops.add_path(url, '/path/'))

    def test_add_path_trailing_slash(self):
        url = u'http://a.com/'
        self.assertEquals('http://a.com/path', ops.add_path(url, 'path'))
        self.assertEquals('http://a.com/path', ops.add_path(url, '/path'))
        self.assertEquals('http://a.com/path/', ops.add_path(url, 'path/'))
        self.assertEquals('http://a.com/path/', ops.add_path(url, '/path/'))

    def test_add_path_existing_path(self):
        url = u'http://a.com/path1'
        self.assertEquals('http://a.com/path1/path2', ops.add_path(url, 'path2'))
        self.assertEquals('http://a.com/path1/path2', ops.add_path(url, '/path2'))
        self.assertEquals('http://a.com/path1/path2/', ops.add_path(url, 'path2/'))
        self.assertEquals('http://a.com/path1/path2/', ops.add_path(url, '/path2/'))

    def test_add_path_trailing_slash_and_existing_path(self):
        url = u'http://a.com/path1/'
        self.assertEquals('http://a.com/path1/path2', ops.add_path(url, 'path2'))
        self.assertEquals('http://a.com/path1/path2', ops.add_path(url, '/path2'))
        self.assertEquals('http://a.com/path1/path2/', ops.add_path(url, 'path2/'))
        self.assertEquals('http://a.com/path1/path2/', ops.add_path(url, '/path2/'))

    def test_add_path_fragment(self):
        url = u'http://a.com/path1/#anchor'
        self.assertEquals('http://a.com/path1/path2#anchor', ops.add_path(url, 'path2'))
        self.assertEquals('http://a.com/path1/path2/#anchor', ops.add_path(url, 'path2/'))

    def test_add_path_query_string(self):
        url = u'http://a.com/path1/?a=b'
        self.assertEquals('http://a.com/path1/path2?a=b', ops.add_path(url, 'path2'))
        self.assertEquals('http://a.com/path1/path2/?a=b', ops.add_path(url, 'path2/'))

    def test_query_param(self):
        self.assertEquals(('a', 'b'), ops._query_param('a', 'b'))

    def test_query_param_unicode(self):
        # unicode objects should be encoded as utf-8 bytes
        self.assertEquals(('a', 'b'), ops._query_param('a', u'b'))
        self.assertEquals(('a', '\xc3\xa9'), ops._query_param('a', u'\xe9'))

        # bytes should be remain as bytes
        self.assertEquals(('a', '\xc3\xa9'), ops._query_param('a', '\xc3\xa9'))

    def test_add_query_params(self):
        url = u'http://a.com'
        self.assertEquals('http://a.com?a=b', ops.add_query_params(url, ('a', 'b')))
        self.assertEquals('http://a.com?a=b', ops.add_query_params(url, {'a': 'b'}))
        self.assertEquals('http://a.com?a=%C3%A9', ops.add_query_params(url, {'a': '\xc3\xa9'}))

        url = u'http://a.com/path'
        self.assertEquals('http://a.com/path?a=b', ops.add_query_params(url, {'a': 'b'}))

        url = u'http://a.com?a=b'
        self.assertEquals('http://a.com?a=b&a=c', ops.add_query_params(url, ('a', 'c')))
        self.assertEquals('http://a.com?a=b&c=d', ops.add_query_params(url, ('c', 'd')))

    def test_update_query_params(self):
        url = u'http://a.com?a=b'
        self.assertEquals('http://a.com?a=b', ops.update_query_params(url, {}))
        self.assertEquals('http://a.com?a=c', ops.update_query_params(url, ('a', 'c')))
        self.assertEquals('http://a.com?a=b&c=d', ops.update_query_params(url, {'c': 'd'}))
        self.assertEquals('http://a.com?a=%C4%A9', ops.update_query_params(url, {'a': '\xc4\xa9'}))

        url = u'http://a.com/path?a=b'
        self.assertEquals('http://a.com/path?a=c', ops.update_query_params(url, {'a': 'c'}))

    def test_escaping(self):
        url = u'http://a.com'
        self.assertEquals('http://a.com?my+key=c', ops.add_query_params(url, ('my key', 'c')))
        self.assertEquals('http://a.com?c=my+val', ops.add_query_params(url, ('c', 'my val')))

    def test_no_double_escaping_existing_params(self):
        url = 'http://a.com?a=%C4%A9'
        self.assertEquals('http://a.com?a=%C4%A9&c=d', ops.update_query_params(url, {'c': 'd'}))

        url = 'http://a.com?a=my+val'
        self.assertEquals('http://a.com?a=my+val&c=d', ops.update_query_params(url, {'c': 'd'}))

class GraphUrlTests(TestCase):
    def setUp(self):
        self.graph = graph.Graph()

    def test_initial_state(self):
        self.assertEquals(graph.Graph.API_ROOT, self.graph.url)

    def test_getitem(self):
        expected = 'https://graph.facebook.com/path'
        self.assertEquals(expected, self.graph.path.url)

        expected = 'https://graph.facebook.com/path/path2'
        self.assertEquals(expected, self.graph.path.path2.url)

    def test_getitem_slice(self):
        url = self.graph[0:20].url
        self.assertTrue(url.startswith('https://graph.facebook.com/?'))
        self.assertTrue('offset=0' in url)
        self.assertTrue('limit=20' in url)

    def test_getattr(self):
        expected = 'https://graph.facebook.com/path'
        self.assertEquals(expected, self.graph['path'].url)

        expected = 'https://graph.facebook.com/path/path2'
        self.assertEquals(expected, self.graph['path']['path2'].url)

    def test_update_params(self):
        expected = 'https://graph.facebook.com/?a=b'
        self.graph = self.graph & {'a': 'b'}
        self.assertEquals(expected, self.graph.url)
        expected += '&c=d'
        self.assertEquals(expected, (self.graph & {'c': 'd'}).url)

    def test_set_params(self):
        expected = 'https://graph.facebook.com/?a=b'
        self.graph = self.graph | {'a': 'b'}
        self.assertEquals(expected, self.graph.url)

        expected = 'https://graph.facebook.com/?a=c'
        self.assertEquals(expected, (self.graph | {'a': 'c'}).url)

        expected = 'https://graph.facebook.com/?a=b&c=d'
        self.assertEquals(expected, (self.graph | {'c': 'd'}).url)

    def test_fields(self):
        expected = 'https://graph.facebook.com/?fields=a%2Cb'
        self.graph = self.graph.fields('a', 'b')
        self.assertEquals(expected, self.graph.url)

    def test_ids(self):
        expected = 'https://graph.facebook.com/?ids=a%2Cb'
        self.graph = self.graph.ids('a', 'b')
        self.assertEquals(expected, self.graph.url)


class FQLTests(TestCase):
    def setUp(self):
        self.fql = FQL(access_token='abc123')

    @patch('facegraph.fql.FQL.fetch_json')
    def test_call(self, mock_fetch):
        self.fql('my_query')
        url = mock_fetch.call_args[0][0]
        self.assertTrue(url.startswith('https://api.facebook.com/method/fql.query?'))
        self.assertTrue('query=my_query' in url)
        self.assertTrue('access_token=abc123' in url)

    @patch('facegraph.fql.FQL.fetch_json')
    def test_call_with_arbitrary_params(self, mock_fetch):
        self.fql('my_query', key='value')
        url = mock_fetch.call_args[0][0]
        self.assertTrue(url.startswith('https://api.facebook.com/method/fql.query?'))
        self.assertTrue('query=my_query' in url)
        self.assertTrue('access_token=abc123' in url)
        self.assertTrue('key=value' in url)

    @patch('facegraph.fql.FQL.fetch_json')
    def test_multi(self, mock_fetch):
        self.fql.multi(['my_query1', 'my_query2'])
        url = mock_fetch.call_args[0][0]
        self.assertTrue(url.startswith('https://api.facebook.com/method/fql.multiquery?'))
        self.assertTrue("&queries=%5B%22my_query1%22%2C+%22my_query2%22%5D" in url)

########NEW FILE########
