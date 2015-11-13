__FILENAME__ = box
from pyoauth2 import Client

KEY = ''
SECRET = ''
CALLBACK = ''

client = Client(KEY, SECRET, 
                site='https://api.box.com/2.0', 
                authorize_url='https://api.box.com/oauth2/authorize',
                token_url='https://api.box.com/oauth2/token')

print '-' * 80
authorize_url = client.auth_code.authorize_url(redirect_uri=CALLBACK)
print 'Go to the following link in your browser:'
print authorize_url
print '-' * 80

code = raw_input('Enter the verification code and hit ENTER when you\'re done:')
code = code.strip()
access_token = client.auth_code.get_token(code, redirect_uri=CALLBACK)
print 'token', access_token.headers

print '-' * 80
ret = access_token.get('/folders/0')
print ret.parsed

########NEW FILE########
__FILENAME__ = douban
from pyoauth2 import Client

KEY = ''
SECRET = ''
CALLBACK = ''

client = Client(KEY, SECRET, 
                site='https://api.douban.com', 
                authorize_url='https://www.douban.com/service/auth2/auth',
                token_url='https://www.douban.com/service/auth2/token')

print '-' * 80
authorize_url = client.auth_code.authorize_url(redirect_uri=CALLBACK, scope='shuo_basic_w,douban_basic_common')
print 'Go to the following link in your browser:'
print authorize_url
print '-' * 80

code = raw_input('Enter the verification code and hit ENTER when you\'re done:')
code = code.strip()
access_token = client.auth_code.get_token(code, redirect_uri=CALLBACK)
print 'token', access_token.headers

print '-' * 80
print 'get @me info' 
ret = access_token.get('/v2/user/~me')
print ret.parsed

print '-' * 80
print 'post miniblog...'
ret = access_token.post('/shuo/v2/statuses/', text='hello oauth2, from py-oauth2')
print ret.parsed

########NEW FILE########
__FILENAME__ = douban_auth_password
from pyoauth2 import Client
from pyoauth2 import AccessToken

KEY = ''
SECRET = ''
CALLBACK = ''

user_email = ''
user_password = ''

client = Client(KEY, SECRET, 
                site='https://api.douban.com', 
                authorize_url='https://www.douban.com/service/auth2/auth',
                token_url='https://www.douban.com/service/auth2/token')

access_token = client.password.get_token(user_email, user_password)

print '-' * 80
ret = access_token.get('/v2/user/~me')
print ret.parsed

########NEW FILE########
__FILENAME__ = douban_auth_token
from pyoauth2 import Client
from pyoauth2 import AccessToken

KEY = ''
SECRET = ''
CALLBACK = ''

token = ''

client = Client(KEY, SECRET, 
                site='https://api.douban.com', 
                authorize_url='https://www.douban.com/service/auth2/auth',
                token_url='https://www.douban.com/service/auth2/token')

access_token = AccessToken(client, token)

print '-' * 80
ret = access_token.get('/people/%40me', alt='json')
print ret.parsed

########NEW FILE########
__FILENAME__ = github
from pyoauth2 import Client

KEY = ''
SECRET = ''
CALLBACK = ''

client = Client(KEY, SECRET,
                site='https://api.github.com',
                authorize_url='https://github.com/login/oauth/authorize',
                token_url='https://github.com/login/oauth/access_token')

print '-' * 80
authorize_url = client.auth_code.authorize_url(redirect_uri=CALLBACK, scope='user,public_repo')
print 'Go to the following link in your browser:'
print authorize_url
print '-' * 80

code = raw_input('Enter the verification code and hit ENTER when you\'re done:')
code = code.strip()
access_token = client.auth_code.get_token(code, redirect_uri=CALLBACK, parse='query')
print 'token', access_token.headers

print '-' * 80
print 'get user info'
ret = access_token.get('/user')
print ret.parsed

print '-' * 80
print 'create a repos'
ret = access_token.post('/user/repos', name='test_repo', headers={'content-type': 'application/json'})
print ret.parsed

########NEW FILE########
__FILENAME__ = google
from pyoauth2 import Client

CLIENT_ID = ''
CLIENT_SECRET = ''
REDIRECT_URL = ''
SCOPE = 'https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email'

client = Client(CLIENT_ID, CLIENT_SECRET,
                site='https://www.googleapis.com/oauth2/v1',
                authorize_url='https://accounts.google.com/o/oauth2/auth',
                token_url='https://accounts.google.com/o/oauth2/token')

print '-' * 80
authorize_url = client.auth_code.authorize_url(redirect_uri=REDIRECT_URL, scope=SCOPE)
print 'Go to the following link in your browser:'
print authorize_url

code = raw_input('Enter the verification code and hit ENTER when you\'re done:')
code = code.strip()
access_token = client.auth_code.get_token(code, redirect_uri=REDIRECT_URL)
print 'token', access_token.headers

print '-' * 80
print 'get user info' 
ret = access_token.get('/userinfo')
print ret.parsed

########NEW FILE########
__FILENAME__ = instagram
from pyoauth2 import Client

CLIENT_ID = ''
CLIENT_SECRET = ''
REDIRECT_URL = ''

client = Client(CLIENT_ID, CLIENT_SECRET, 
                site='https://api.instagram.com',
                authorize_url='/oauth/authorize',
                token_url='/oauth/access_token')

authorize_url = client.auth_code.authorize_url(redirect_uri=REDIRECT_URL)

print 'Go to the following link in your browser:'
print authorize_url
print '-' * 80

code = raw_input('Enter the verification code and hit ENTER when you\'re done:')
code = code.strip()
access_token = client.auth_code.get_token(code, redirect_uri=REDIRECT_URL)

print 'token', access_token.headers
print 'params', access_token.params

########NEW FILE########
__FILENAME__ = qq
from pyoauth2 import Client

KEY = ''
SECRET = ''
CALLBACK = ''

client = Client(KEY, SECRET, 
                site='https://graph.qq.com', 
                authorize_url='https://graph.qq.com/oauth2.0/authorize',
                token_url='https://graph.qq.com/oauth2.0/token')

print '-' * 80
authorize_url = client.auth_code.authorize_url(redirect_uri=CALLBACK, 
                    scope='get_user_info,list_album,upload_pic,do_like')
print 'Go to the following link in your browser:'
print authorize_url
print '-' * 80

code = raw_input('Enter the verification code and hit ENTER when you\'re done:')
code = code.strip()
access_token = client.auth_code.get_token(code, redirect_uri=CALLBACK, parse='query')

print 'token', access_token.headers
print access_token.expires_at

########NEW FILE########
__FILENAME__ = weibo
from pyoauth2 import Client

KEY = ''
SECRET = ''
CALLBACK = ''

client = Client(KEY, SECRET, 
                site='https://api.weibo.com', 
                authorize_url='/oauth2/authorize',
                token_url='/oauth2/access_token')

print '-' * 80
authorize_url = client.auth_code.authorize_url(redirect_uri=CALLBACK)
print 'Go to the following link in your browser:'
print authorize_url

code = raw_input('Enter the verification code and hit ENTER when you\'re done:')
code = code.strip()
access_token = client.auth_code.get_token(code, redirect_uri=CALLBACK, header_format='OAuth2 %s')
print 'token', access_token.headers

ret = access_token.get('/2/statuses/public_timeline.json')
print '-' * 80
print 'get public timeline' 
print ret.body

print '-' * 80
print 'post miniblog...'
ret = access_token.post('/2/statuses/update.json', status='now')
print ret.body

########NEW FILE########
__FILENAME__ = weibo_token
from pyoauth2 import Client
from pyoauth2 import AccessToken

KEY = ''
SECRET = ''
CALLBACK = ''

client = Client(KEY, SECRET, site='https://api.weibo.com', 
                authorize_url='/oauth2/authorize',
                token_url='/oauth2/access_token')

code = raw_input('Enter the verification code and hit ENTER when you\'re done:')
client.auth_code.get_token(code, redirect_uri=CALLBACK)
access_token = AccessToken(client, code)

print access_token.get('/2/statuses/public_timeline.json', access_token=access_token.token).parsed

########NEW FILE########
__FILENAME__ = client
# -*- coding: utf-8 -*-

from .libs.auth_code import AuthCode
from .libs.password import Password
from .libs.access_token import AccessToken
from .libs.request import Request
from .libs.connection import Connection


class Client(object):

    def __init__(self, client_id, client_secret, **opts):
        self.id = client_id
        self.secret = client_secret
        self.site = opts.pop('site', '')
        self.opts = {'authorize_url': '/oauth/authorize',
                     'token_url': '/oauth/token',
                     'token_method': 'POST',
                     'connection_opts': {},
                     'raise_errors': True, }
        self.opts.update(opts)

    def __repr__(self):
        return '<OAuth2 Client>'

    def authorize_url(self, params={}):
        return Connection.build_url(self.site, path=self.opts['authorize_url'], params=params)

    def token_url(self, params={}):
        return Connection.build_url(self.site, path=self.opts['token_url'], params=params)

    def request(self, method, uri, **opts):
        uri = Connection.build_url(self.site, path=uri)
        response = Request(method, uri, **opts).request()
        return response

    def get_token(self, **opts):
        self.response = self.request(self.opts['token_method'], self.token_url(), **opts)
        opts.update(self.response.parsed)
        return AccessToken.from_hash(self, **opts)

    @property
    def password(self):
        return Password(self)

    @property
    def auth_code(self):
        return AuthCode(self)

########NEW FILE########
__FILENAME__ = access_token
# -*- coding: utf-8 -*-
import time
from .utils import urlparse


class AccessToken(object):

    def __init__(self, client, token, **opts):
        self.client = client
        self.token = token

        for attr in ['refresh_token', 'expires_in', 'expires_at']:
            if attr in opts.keys():
                setattr(self, attr, opts.pop(attr))

        if hasattr(self, 'expires_in') and str(self.expires_in).isdigit():
            self.expires_at = int(time.time()) + int(self.expires_in)

        self.opts = {'mode': opts.pop('mode', 'header'),
                     'header_format': opts.pop('header_format', 'Bearer %s'),
                     'param_name': opts.pop('param_name', 'bearer_token'),
                     }
        self.params = opts

    def __repr__(self):
        return '<OAuth2 AccessToken>'

    @classmethod
    def from_hash(cls, client, **opts):
        return cls(client, opts.pop('access_token', ''), **opts)

    @classmethod
    def from_kvform(cls, client, kvform):
        opts = dict(urlparse.parse_qsl(kvform))
        return cls(client, opts.pop('access_token', ''), **opts)

    def refresh(self, **opts):
        if not getattr(self, 'refresh_token', None):
            raise 'A refresh_token is not available'

        opts = {'client_id': self.client.id,
                'client_secret': self.client.secret,
                'refresh_token': self.refresh_token,
                'grant_type': 'refresh_token',
                }
        new_token = self.client.get_token(**opts)
        return new_token

    def request(self, method, uri, **opts):
        opts = self.__set_token(**opts)
        return self.client.request(method, uri, **opts)

    def get(self, uri, **opts):
        return self.request('GET', uri, **opts)

    def post(self, uri, **opts):
        return self.request('POST', uri, **opts)

    def put(self, uri, **opts):
        return self.request('PUT', uri, **opts)

    def patch(self, uri, **opts):
        return self.request('PATCH', uri, **opts)

    def delete(self, uri, **opts):
        return self.request('DELETE', uri, **opts)

    @property
    def headers(self):
        return {'Authorization': self.opts['header_format'] % self.token}

    def __set_token(self, **opts):
        mode = self.opts['mode']
        if mode == 'header':
            headers = opts.get('headers', {})
            headers.update(self.headers)
            opts['headers'] = headers
        elif mode == 'query':
            params = opts.get('params', {})
            params[self.opts['param_name']] = self.token
            opts['params'] = params
        elif mode == 'body':
            body = opts.get('body', {})
            if isinstance(body, dict):
                opts['body'][self.opts['param_name']] = self.token
            else:
                opts['body'] += "&%s=%s" % (self.opts['param_name'], self.token)
        else:
            raise "invalid :mode option of %s" % (self.opts['param_name'])

        return opts

########NEW FILE########
__FILENAME__ = auth_code
# -*- coding: utf-8 -*-
from .base import Base


class AuthCode(Base):

    def __repr__(self):
        return '<OAuth2 AuthCode %s>' % self.client.id

    def authorize_params(self, **params):
        params.update({'response_type': 'code', 'client_id': self.client.id})
        return params

    def authorize_url(self, **params):
        params = self.authorize_params(**params)
        return self.client.authorize_url(params)

    def get_token(self, code, **opts):
        params = {'grant_type': 'authorization_code', 'code': code}
        params.update(self.client_params)
        opts.update(params)
        return self.client.get_token(**opts)

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*


class Base(object):

    def __init__(self, client):
        self.client = client

    @property
    def client_params(self):
        return {'client_id': self.client.id, 'client_secret': self.client.secret}

########NEW FILE########
__FILENAME__ = connection
# -*- coding: utf-8 -*-
from .utils import urlencode


class Connection(object):

    def __repr__(self):
        return '<OAuth2 Connection>'

    @classmethod
    def build_url(cls, url, path='', params={}):
        params = urlencode(params)
        params = '?%s' % params if params else ''
        url = path if path.startswith(('http://', 'https://')) else '%s%s' % (url, path)
        return '%s%s' % (url, params)

########NEW FILE########
__FILENAME__ = password
# -*- coding: utf-8 -*-

from .base import Base


class Password(Base):

    def authorize_url(self):
        return NotImplementedError('The authorization endpoint is not used in this strategy')

    def get_token(self, username, password, **opts):
        params = {'grant_type': 'password',
                  'username': username,
                  'password': password,
                  }
        params.update(self.client_params)
        opts.update(params)
        return self.client.get_token(**opts)

########NEW FILE########
__FILENAME__ = request
# -*- coding: utf-8 -*-
import json
import requests

from .response import Response


class Request(object):

    def __init__(self, method, uri, **opts):
        self.method = method
        self.uri = uri
        self.headers = opts.pop('headers', {})
        self.parse = opts.pop('parse', 'json')
        self.files = opts.pop('files', {})
        if self.headers.get('content-type') == 'application/json':
            self.opts = json.dumps(opts)
        else:
            self.opts = opts

    def __repr__(self):
        return '<OAuth2 Request>'

    def request(self):
        if self.method in ('POST', 'PUT'):
            response = requests.request(self.method, self.uri, data=self.opts, files=self.files, headers=self.headers)
        else:
            response = requests.request(self.method, self.uri, params=self.opts, headers=self.headers)

        response = Response(response, parse=self.parse)

        status = response.status_code
        #TODO raise error
        if status in (301, 302, 303, 307):
            return response
        elif 200 <= status < 400:
            return response
        elif 400 <= status < 500:
            return response
        elif 500 <= status < 600:
            return response
        return response

########NEW FILE########
__FILENAME__ = response
# -*- coding: utf-8 -*-
from .utils import urlparse


def to_query(txt):
    qs = urlparse.parse_qsl(txt)
    ret = dict(qs)
    return _check_expires_in(ret)


def to_text(txt):
    return txt


def _check_expires_in(ret):
    expires_in = ret.get('expires_in')
    if expires_in and expires_in.isdigit():
        ret['expires_in'] = int(expires_in)
    return ret


class Response(object):

    def __init__(self, response, **opts):
        self.resp = response
        self.status_code = self.status = response.status_code
        self.reason = response.reason
        self.content_type = response.headers.get('content-type')
        self.body = response.text

        options = {'parse': 'text'}
        options.update(opts)
        self.options = options

    def __repr__(self):
        return '<OAuth2 Response>'

    @property
    def parsed(self):
        fmt = self.options['parse']
        if fmt == 'json':
            return self.resp.json()
        elif fmt == 'query':
            return to_query(self.body)
        else:
            return self.body

########NEW FILE########
__FILENAME__ = utils
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

########NEW FILE########
