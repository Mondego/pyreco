__FILENAME__ = config
import glob
import os
from flask import Flask
from werkzeug.contrib.fixers import ProxyFix
from flask_sslify import SSLify

from foauth.providers import OAuthMeta

app = Flask(__name__)
app.secret_key = os.environ['SECRET_KEY']
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['DEBUG'] = 'DEBUG' in os.environ
app.wsgi_app = ProxyFix(app.wsgi_app)
if 'SSLIFY' in os.environ:
    SSLify(app)


def get_service_modules():
    for filename in glob.glob(os.path.join('services', '*.py')):
        module_name = os.path.splitext(os.path.split(filename)[1])[0]
        if not module_name.startswith('__'):
            yield module_name


def get_oauth_providers(module_name):
    module = getattr(__import__('services.%s' % module_name), module_name)
    for name, obj in module.__dict__.items():
        if isinstance(obj, OAuthMeta):
            yield obj


services = []
for module_name in get_service_modules():
    for service in get_oauth_providers(module_name):
        alias = service.alias.upper()
        key = os.environ.get('%s_KEY' % alias, '').decode('utf8')
        secret = os.environ.get('%s_SECRET' % alias, '').decode('utf8')

        if key and secret:  # Only initialize if all the pieces are in place
            services.append(service(key, secret))


alias_map = {}
for service in services:
    alias_map[service.alias] = service

domain_map = {}
for service in services:
    for domain in service.api_domains:
        domain_map[domain] = service

########NEW FILE########
__FILENAME__ = providers
import json
from os import urandom
import urllib
import urlparse

import flask
import requests
from requests_oauthlib import OAuth1 as OAuth1Manager
from oauthlib.oauth1.rfc5849 import SIGNATURE_HMAC, SIGNATURE_TYPE_AUTH_HEADER
from oauthlib.oauth2.draft25 import tokens
from werkzeug.urls import url_decode

from foauth import OAuthError

BEARER = 'BEARER'
BEARER_HEADER = 'HEADER'
BEARER_BODY = 'BODY'
BEARER_URI = 'URI'
BEARER_TYPES = (BEARER_HEADER, BEARER_BODY, BEARER_URI)


class Bearer(object):
    def __init__(self, token, bearer_type=BEARER_HEADER):
        self.token = token

        if bearer_type in BEARER_TYPES or callable(bearer_type):
            self.bearer_type = bearer_type
        else:
            raise ValueError('Unknown bearer type %s' % bearer_type)

    def __call__(self, r):
        if self.bearer_type == BEARER_HEADER:
            r.headers = tokens.prepare_bearer_headers(self.token, r.headers)
        elif self.bearer_type == BEARER_BODY:
            r.data = tokens.prepare_bearer_body(self.token, r.data)
        elif self.bearer_type == BEARER_URI:
            r.url = tokens.prepare_bearer_uri(self.token, r.url)
        elif callable(self.bearer_type):
            r = self.bearer_type(self.token, r)

        return r


class OAuthMeta(type):
    def __init__(cls, name, bases, attrs):
        if 'alias' not in attrs:
            cls.alias = cls.__name__.lower()
        if 'api_domain' in attrs and 'api_domains' not in attrs:
            cls.api_domains = [cls.api_domain]
        if 'provider_url' in attrs and 'favicon_url' not in attrs:
            # Use a favicon service when no favicon is supplied
            primary = 'https://getfavicon.appspot.com/%s' % cls.provider_url
            domain = urlparse.urlparse(cls.provider_url).netloc
            backup = 'https://www.google.com/s2/favicons?domain=%s' % domain
            cls.favicon_url = '%s?defaulticon=%s' % (primary, urllib.quote(backup))

        if 'name' not in attrs:
            cls.name = cls.__name__


class OAuth(object):
    __metaclass__ = OAuthMeta

    https = True
    verify = True
    signature_method = SIGNATURE_HMAC
    signature_type = SIGNATURE_TYPE_AUTH_HEADER
    permissions_widget = 'checkbox'
    description = ''
    disclaimer = ''

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret

    def get_request_token_url(self):
        return self.request_token_url

    def get_access_token_url(self):
        return self.access_token_url

    def get_scope_string(self, scopes):
        return ''

    def get_authorize_url(self, redirect_uri, scopes):
        params = self.get_authorize_params(redirect_uri=redirect_uri,
                                           scopes=scopes)
        req = requests.Request(url=self.authorize_url, params=params)
        return req.prepare().url

    def get_login_uri(self, redirect_uri):
        params = self.get_authorize_params(redirect_uri=redirect_uri,
                                           scopes=[])
        req = requests.Request(url=self.authorize_url, params=params)
        return req.prepare().url

    # The remainder of the API must be implemented for each flavor of OAuth

    def callback(self, data, redirect_uri):
        """
        Receives the full callback from the service and returns a 2-tuple
        containing the user token and user secret (if applicable).
        """
        raise NotImplementedError("callback() must be defined in a subclass")

    def api(self, key, domain, path, method='GET', params=None, data=None):
        """
        Passes along an API request to the service and returns the response.
        """
        raise NotImplementedError("api() must be defined in a subclass")


class OAuth1(OAuth):
    returns_token = True

    def parse_token(self, content):
        content = url_decode(content)
        return {
            'access_token': content['oauth_token'],
            'secret': content['oauth_token_secret'],
        }

    def get_request_token_params(self, redirect_uri, scopes):
        return {}

    def get_request_token_response(self, redirect_uri, scopes):
        auth = OAuth1Manager(client_key=self.client_id,
                             client_secret=self.client_secret,
                             callback_uri=redirect_uri,
                             signature_method=self.signature_method,
                             signature_type=self.signature_type)
        return requests.post(self.get_request_token_url(), auth=auth,
                             params=self.get_request_token_params(redirect_uri, scopes),
                             verify=self.verify)

    def get_authorize_params(self, redirect_uri, scopes):
        resp = self.get_request_token_response(redirect_uri, scopes)
        try:
            data = self.parse_token(resp.content)
        except Exception:
            raise OAuthError('Unable to parse access token')
        flask.session['%s_temp_secret' % self.alias] = data['secret']
        if not self.returns_token:
            redirect_uri += ('?oauth_token=%s' % data['access_token'])
        return {
            'oauth_token': data['access_token'],
            'oauth_callback': redirect_uri,
        }

    def get_access_token_response(self, token, secret, verifier=None):
        auth = OAuth1Manager(client_key=self.client_id,
                             client_secret=self.client_secret,
                             resource_owner_key=token,
                             resource_owner_secret=secret,
                             verifier=verifier,
                             signature_method=self.signature_method,
                             signature_type=self.signature_type)
        return requests.post(self.get_access_token_url(), auth=auth,
                             verify=self.verify)

    def callback(self, data, redirect_uri):
        token = data['oauth_token']
        verifier = data.get('oauth_verifier', None)
        secret = flask.session['%s_temp_secret' % self.alias]
        del flask.session['%s_temp_secret' % self.alias]
        resp = self.get_access_token_response(token, secret, verifier)
        try:
            return self.parse_token(resp.content)
        except Exception:
            raise OAuthError('Unable to parse access token')

    def api(self, key, domain, path, method='GET', params=None, data=None,
            headers=None):
        protocol = self.https and 'https' or 'http'
        url = '%s://%s%s' % (protocol, domain, path)
        auth = OAuth1Manager(client_key=self.client_id,
                             client_secret=self.client_secret,
                             resource_owner_key=key.access_token,
                             resource_owner_secret=key.secret,
                             signature_method=self.signature_method,
                             signature_type=self.signature_type)
        return requests.request(method, url, auth=auth, params=params or {},
                                data=data or {}, headers=headers or {},
                                verify=self.verify, stream=True)


class OAuth2(OAuth):
    token_type = BEARER
    bearer_type = BEARER_HEADER
    supports_state = True
    auth = None

    def parse_token(self, content):
        return json.loads(content)

    def get_scope_string(self, scopes):
        return ' '.join(scopes)

    def get_authorize_params(self, redirect_uri, scopes):
        state = ''.join('%02x' % ord(x) for x in urandom(16))
        flask.session['%s_state' % self.alias] = state
        if not self.supports_state:
            redirect_uri += ('?state=%s' % state)
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'state': state,
        }
        if any(scopes):
            params['scope'] = self.get_scope_string(scopes)
        return params

    def get_access_token_response(self, redirect_uri, data):
        return requests.post(self.get_access_token_url(), {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': data['code'],
            'redirect_uri': redirect_uri
        }, verify=self.verify, auth=self.auth)

    def callback(self, data, redirect_uri):
        state = flask.session['%s_state' % self.alias]
        if 'state' in data and state != data['state']:
            flask.abort(403)
        del flask.session['%s_state' % self.alias]
        if not self.supports_state:
            redirect_uri += ('?state=%s' % state)
        resp = self.get_access_token_response(redirect_uri, data)

        return self.parse_token(resp.content)

    def refresh_token(self, token):
        resp = requests.post(self.get_access_token_url(), {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': token
        }, verify=self.verify, auth=self.auth)

        return self.parse_token(resp.content)

    def api(self, key, domain, path, method='GET', params=None, data=None,
            headers=None):
        protocol = self.https and 'https' or 'http'
        url = '%s://%s%s' % (protocol, domain, path)
        if self.token_type == BEARER:
            auth = Bearer(key.access_token, bearer_type=self.bearer_type)
        return requests.request(method, url, auth=auth, params=params or {},
                                data=data or {}, headers=headers or {},
                                verify=self.verify, stream=True)

########NEW FILE########
__FILENAME__ = forms
from flask.ext.wtf import Form, TextField, PasswordField, BooleanField, validators

import models


class Signup(Form):
    email = TextField('Email address', [
        validators.Required('It&rsquo;s okay, we won&rsquo;t email you unless you want us to.'),
        validators.Email('Um, that doesn&rsquo;t look like an email address.'),
    ])
    password = PasswordField('Password', [
        validators.Required('How else will we know it&rsquo;s really you?'),
        validators.EqualTo('retype', message='If you can&rsquo;t type it twice now, you&rsquo;ll never be able to log in with it.')
    ])
    retype = PasswordField('Password (again)')
    consent = BooleanField('Accept the Terms', [
        validators.Required('Is there something you don&rsquo;t agree with?')
    ])

    def validate_email(form, field):
        if models.User.query.filter_by(email=field.data).count():
            raise validators.ValidationError('Looks like you&rsquo;ve already registered. Try logging in instead.')


class Login(Form):
    email = TextField('Email address', validators=[
        validators.Email('Please supply an email address.')
    ])
    password = PasswordField('Password', validators=[
        validators.Required('Please supply a password.')
    ])


class Password(Form):
    password = PasswordField('Password', [
        validators.Required('How else will we know it&rsquo;s really you?'),
    ])
    retype = PasswordField('Password (again)', [
        validators.EqualTo('password', message='If you can&rsquo;t type it twice now, you&rsquo;ll never be able to log in with it.')
    ])

########NEW FILE########
__FILENAME__ = models
import datetime

from werkzeug.security import generate_password_hash, check_password_hash
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext import login

import config
db = SQLAlchemy(config.app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True)
    password = db.Column(db.String)

    def __init__(self, email, password):
        self.email = email
        self.set_password(password)

    def hash_password(self, password):
        return generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def set_password(self, password):
        self.password = self.hash_password(password)

    def is_authenticated(self):
        return self.id is not None

    def is_anonymous(self):
        return False

    def is_active(self):
        return self.is_authenticated()

    def get_id(self):
        return unicode(self.id)

    def __repr__(self):
        return '<User: %s>' % self.email

    def key_for_service(self, alias):
        return self.keys.filter_by(service_alias=alias).first()


class Key(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    service_alias = db.Column(db.String)
    access_token = db.Column(db.String)
    secret = db.Column(db.String)
    expires = db.Column(db.DateTime)
    refresh_token = db.Column(db.String)
    service_user_id = db.Column(db.String)

    user = db.relationship('User', backref=db.backref('keys', lazy='dynamic'))

    @property
    def service(self):
        if not self.service_alias:
            raise AttributeError('No service specified.')
        try:
            return config.alias_map[self.service_alias]
        except KeyError:
            raise AttributeError('%r is not a valid service.' % self.service_alias)

    def update(self, data):
        self.access_token = data['access_token']
        self.secret = data.get('secret', None)
        if data.get('expires_in'):
            # Convert to a real datetime
            expires_in = datetime.timedelta(seconds=int(data['expires_in']))
            self.expires = datetime.datetime.now() + expires_in
        else:
            self.expires = None
        self.refresh_token = data.get('refresh_token', None)
        self.service_user_id = data.get('service_user_id', None)

    def is_expired(self):
        return self.will_expire(days=0)

    def will_expire(self, days=7):
        soon = datetime.datetime.now() + datetime.timedelta(days=days)
        return self.expires and self.expires < soon

    def fill_user_id(self):
        try:
            self.service_user_id = self.service.get_user_id(self)
        except Exception:
            # Normally `except Exception` would be a tremendously terrible
            # idea, but in this case a lot of things can go wrong, and the
            # end result is simply that the key couldn't be retrieved. In
            # that case, we can still handle it gracefully and return None.
            self.service_user_id = None


login_manager = login.LoginManager()
login_manager.setup_app(config.app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

########NEW FILE########
__FILENAME__ = pelican.conf
SITENAME = 'foauth.org'
AUTHOR = 'Marty Alchin'
SITEURL = 'https://foauth.org/blog'
TIMEZONE = 'America/Los_Angeles'

DEFAULT_PAGINATION = 10

ARTICLE_URL = '{slug}/'
ARTICLE_SAVE_AS = '{slug}/index.html'
FEED_ALL_ATOM = 'feed.rss'

PATH = 'blog/content'
OUTPUT_PATH = 'blog/output'
USE_FOLDER_AS_CATEGORY = False
DELETE_OUTPUT_DIRECTORY = True

MARKUP = ['md']
TYPOGRIFY = True

########NEW FILE########
__FILENAME__ = angellist
import foauth.providers


class AngelList(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'https://angel.co/'
    docs_url = 'https://angel.co/api'
    category = 'Money'

    # URLs to interact with the API
    authorize_url = 'https://angel.co/api/oauth/authorize'
    access_token_url = 'https://angel.co/api/oauth/token'
    api_domain = 'api.angel.co'

    available_permissions = [
        (None, 'follow items and update your status'),
        ('email', 'access your email address'),
        ('message', 'read and send private messages'),
    ]

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/1/me')
        return unicode(r.json()[u'id'])

########NEW FILE########
__FILENAME__ = assembla
import foauth.providers


class Assembla(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'https://www.assembla.com/'
    docs_url = 'http://api-doc.assembla.com/content/api_reference.html'
    category = 'Code'

    # URLs to interact with the API
    authorize_url = 'https://api.assembla.com/authorization'
    access_token_url = 'https://api.assembla.com/token'
    api_domain = 'api.assembla.com'

    available_permissions = [
        (None, 'read, write and manage your projects'),
    ]

    def __init__(self, *args, **kwargs):
        super(Assembla, self).__init__(*args, **kwargs)
        self.auth = (self.client_id, self.client_secret)

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/v1/user')
        return unicode(r.json()[u'id'])

########NEW FILE########
__FILENAME__ = behance
from oauthlib.common import add_params_to_uri
import foauth.providers


class Behance(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'http://www.behance.net/'
    docs_url = 'http://www.behance.net/dev/api/endpoints/'
    category = 'Career'

    # URLs to interact with the API
    authorize_url = 'https://www.behance.net/v2/oauth/authenticate'
    access_token_url = 'https://www.behance.net/v2/oauth/token'
    api_domain = 'www.behance.net'

    available_permissions = [
        (None, 'read your activity feed'),
        ('project_read', 'read your public and private projects'),
        ('post_as', 'post to your activity feed'),
        ('collection_read', 'read your private collections'),
        ('collection_write', 'write to your private collections'),
        ('invitations_read', 'read your invitations'),
        ('invitations_write', 'respond to your invitations'),
        ('wip_read', 'read your works in progress'),
        ('wip_write', 'write to your works in progress'),
    ]

    bearer_type = foauth.providers.BEARER_URI

    def get_scope_string(self, scopes):
        return '|'.join(scopes)

    def get_authorize_params(self, redirect_uri, scopes):
        # We always need to at least request something
        scopes.append('activity_read')
        return super(Behance, self).get_authorize_params(redirect_uri, scopes)

    def parse_token(self, content):
        data = super(Behance, self).parse_token(content)
        data['service_user_id'] = data['user']['id']
        return data

########NEW FILE########
__FILENAME__ = bitbucket
import foauth.providers


class Bitbucket(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'https://bitbucket.org/'
    docs_url = 'http://confluence.atlassian.com/display/BITBUCKET/Using+the+Bitbucket+REST+APIs'
    category = 'Code'

    # URLs to interact with the API
    request_token_url = 'https://bitbucket.org/api/1.0/oauth/request_token/'
    authorize_url = 'https://bitbucket.org/api/1.0/oauth/authenticate/'
    access_token_url = 'https://bitbucket.org/api/1.0/oauth/access_token/'
    api_domain = 'api.bitbucket.org'

    available_permissions = [
        (None, 'read and write your code and issues'),
    ]

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/1.0/user/')
        return r.json()[u'user'][u'username']

########NEW FILE########
__FILENAME__ = bitly
from werkzeug.urls import url_decode
import foauth.providers


class Bitly(foauth.providers.OAuth2):
    # General info about the provider
    name = 'bitly'
    provider_url = 'https://bitly.com/'
    docs_url = 'https://dev.bitly.com/'
    category = 'Social'

    # URLs to interact with the API
    authorize_url = 'https://bitly.com/oauth/authorize'
    access_token_url = 'https://api-ssl.bitly.com/oauth/access_token'
    api_domain = 'api-ssl.bitly.com'

    available_permissions = [
        (None, 'read and write to your shortened URLs'),
    ]

    bearer_type = foauth.providers.BEARER_URI

    def parse_token(self, content):
        return url_decode(content)

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/v3/user/info')
        return unicode(r.json()[u'data'][u'login'])

########NEW FILE########
__FILENAME__ = box
import flask
import requests
import urllib
from xml.dom import minidom

import foauth.providers


class Box(foauth.providers.OAuth1):
    # General info about the provider
    name = 'Box'
    provider_url = 'https://www.box.com/'
    docs_url = 'http://developers.box.com/docs/'
    category = 'Files'

    # URLs to interact with the API
    request_token_url = 'https://api.box.com/1.0/rest'
    authorize_url = 'https://api.box.com/1.0/auth/%s'
    access_token_url = 'https://api.box.com/1.0/rest'
    api_domains = ['api.box.com', 'www.box.com']

    available_permissions = [
        (None, 'read and write to your files'),
    ]

    def get_ticket(self):
        params = {
            'action': 'get_ticket',
            'api_key': self.client_id,
        }
        resp = requests.post(self.get_request_token_url(), params=params)
        dom = minidom.parseString(resp.content)
        return dom.getElementsByTagName('ticket')[0].firstChild.nodeValue

    def authorize(self, scopes):
        return flask.redirect(self.authorize_url % self.get_ticket())

    def parse_token(self, content):
        dom = minidom.parseString(content)
        token = dom.getElementsByTagName('auth_token')[0].firstChild.nodeValue
        return {'access_token': token}

    def callback(self, data, *args, **kwargs):
        params = {
            'action': 'get_auth_token',
            'api_key': self.client_id,
            'ticket': data['ticket'],
            'token': data['auth_token'],
        }
        resp = requests.get(self.get_access_token_url(), params=params)

        return self.parse_token(resp.content)

    def api(self, key, domain, path, method='GET', params=None, data=None,
            headers=None):
        url = 'https://%s%s' % (domain, path)
        auth = Auth(self.client_id, key.access_token)
        return requests.request(method, url, auth=auth, params=params or {},
                                data=data or {}, headers=dict(headers or {}))

    def get_user_id(self, key):
        r = self.api(key, self.api_domains[0], u'/2.0/folders/0')
        return r.json()[u'owned_by'][u'id']


class Auth(object):
    def __init__(self, client_id, auth_token):
        self.client_id = client_id
        self.auth_token = auth_token

    def __call__(self, r):
        params = [('api_key', self.client_id), ('auth_token', self.auth_token)]
        r.headers['Authorization'] = 'BoxAuth %s' % urllib.urlencode(params)
        return r

########NEW FILE########
__FILENAME__ = cheddar
import foauth.providers


class Cheddar(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'https://cheddarapp.com/'
    docs_url = 'https://cheddarapp.com/developer/'
    category = 'Tasks'

    # URLs to interact with the API
    authorize_url = 'https://api.cheddarapp.com/oauth/authorize'
    access_token_url = 'https://api.cheddarapp.com/oauth/token'
    api_domain = 'api.cheddarapp.com'

    available_permissions = [
        (None, 'read and write to your tasks'),
    ]

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/v1/me')
        return unicode(r.json()[u'id'])

########NEW FILE########
__FILENAME__ = coinbase
from oauthlib.common import add_params_to_uri
import foauth.providers


class Coinbase(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'https://coinbase.com/'
    docs_url = 'https://coinbase.com/api/doc'
    category = 'Money'

    # URLs to interact with the API
    authorize_url = 'https://coinbase.com/oauth/authorize'
    access_token_url = 'https://coinbase.com/oauth/token'
    api_domain = 'coinbase.com'

    available_permissions = [
        (None, 'View your basic account information'),
        ('merchant', 'Create payment buttons and forms, view your basic user information, edit your merchant settings, and generate new receive addresses'),
        ('balance', 'View your balance'),
        ('addresses', 'View receive addresses and create new ones'),
        ('buttons', 'Create payment buttons'),
        ('buy', 'Buy bitcoin'),
        ('contacts', 'List emails and bitcoin addresses in your contact list'),
        ('orders', 'List merchant orders received'),
        ('sell', 'Sell bitcoin'),
        ('transactions', 'View your transaction history'),
        ('send', 'Debit an unlimited amount of money from your account'),
        ('request', 'Request money from your account'),
        ('transfers', 'List bitcoin buy and sell history'),
        ('recurring_payments', 'List your recurring payments'),
        ('oauth_apps', "List the other apps you've authorized"),
        ('all', 'All of the above'),
    ]

    def get_authorize_params(self, redirect_uri, scopes):
        # Always request at least user information
        scopes.append('user')
        return super(Coinbase, self).get_authorize_params(redirect_uri, scopes)

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/api/v1/users')
        return r.json()[u'users'][0][u'user'][u'id']

########NEW FILE########
__FILENAME__ = dailymile
from oauthlib.oauth2.draft25 import utils
import foauth.providers


class Dailymile(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'http://dailymile.com'
    docs_url = 'http://www.dailymile.com/api/documentation'
    category = 'Fitness'

    # URLs to interact with the API
    authorize_url = 'https://api.dailymile.com/oauth/authorize'
    access_token_url = 'https://api.dailymile.com/oauth/token'
    api_domain = 'api.dailymile.com'

    available_permissions = [
        (None, 'read and write to your workout data'),
    ]

    def bearer_type(self, token, r):
        r.url = utils.add_params_to_uri(r.url, [((u'oauth_token', token))])
        return r

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/people/me.json')
        return r.json()[u'username']

########NEW FILE########
__FILENAME__ = dailymotion
import foauth.providers


class Dailymotion(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'http://www.dailymotion.com/'
    docs_url = 'http://www.dailymotion.com/doc/api/graph-api.html'
    category = 'Videos'

    # URLs to interact with the API
    authorize_url = 'https://api.dailymotion.com/oauth/authorize'
    access_token_url = 'https://api.dailymotion.com/oauth/token'
    api_domain = 'api.dailymotion.com'

    available_permissions = [
        (None, 'access your public profile information'),
        ('email', 'access your email address'),
        ('userinfo', 'read and write to your private profile information'),
        ('manage_videos', 'publish, modify and delete your videos'),
        ('manage_comments', 'publish comments on videos'),
        ('manage_playlists', 'create, edit and delete your playlists'),
        ('manage_tiles', 'read and write to your saved tiles'),
        ('manage_subscriptions', 'manage your subscriptions'),
        ('manage_friends', 'manage your list of friends'),
        ('manage_favorites', 'manage your list of favorite videos'),
        ('manage_groups', 'manage your groups'),
    ]

    available_permissions = [
        (None, 'access your personal assets'),
        ('email', 'access your email'),
        ('userinfo', 'access ane edit your personal information'),
        ('manage_videos', 'access and edit your videos'),
        ('manage_comments', 'access and edit your comments'),
        ('manage_playlists', 'access and edit your playlists'),
        ('manage_tiles', 'access and edit your dashboard'),
        ('manage_subscriptions', 'access and edit your following tab'),
        ('manage_friends', 'access and edit your friends'),
        ('manage_favorites', 'access and edit your favorites'),
        ('manage_groups', 'access and edit your groups'),
    ]

    def bearer_type(self, token, r):
        r.headers['Authorization'] = 'OAuth %s' % token
        return r

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/me')
        return unicode(r.json()[u'id'])

########NEW FILE########
__FILENAME__ = deviantart
import foauth.providers


def draft10(service, token, r):
    headers = r.headers or {}
    headers[u'Authorization'] = u'OAuth %s' % token
    r.headers = headers
    return r


class DeviantArt(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'http://deviantart.com/'
    docs_url = 'http://www.deviantart.com/developers/'
    category = 'Pictures'

    # URLs to interact with the API
    authorize_url = 'https://www.deviantart.com/oauth2/draft15/authorize'
    access_token_url = 'https://www.deviantart.com/oauth2/draft15/token'
    api_domain = 'www.deviantart.com'

    available_permissions = [
        (None, 'read and write to your artwork'),
    ]

    bearer_type = draft10

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/api/draft15/user/whoami')
        return r.json()[u'username']

########NEW FILE########
__FILENAME__ = disqus
from oauthlib.common import add_params_to_uri
import foauth.providers


class Disqus(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'http://disqus.com/'
    docs_url = 'http://disqus.com/api/docs/'
    category = 'Social'

    # URLs to interact with the API
    authorize_url = 'https://disqus.com/api/oauth/2.0/authorize/'
    access_token_url = 'https://disqus.com/api/oauth/2.0/access_token/'
    api_domain = 'disqus.com'

    available_permissions = [
        (None, 'access your contact info'),
        ('write', 'access your contact info and add comments'),
        ('admin', 'access your contact info, add comments and moderate your forums'),
    ]
    permissions_widget = 'radio'

    def bearer_type(service, token, r):
        params = [((u'access_token', token)), ((u'api_key', service.client_id))]
        r.url = add_params_to_uri(r.url, params)
        return r

    def get_scope_string(self, scopes):
        return ','.join(scopes)

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/api/3.0/users/details.json')
        return r.json()[u'response'][u'id']

########NEW FILE########
__FILENAME__ = dropbox
import foauth.providers
from oauthlib.oauth1.rfc5849 import SIGNATURE_PLAINTEXT


class Dropbox(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'https://www.dropbox.com/'
    docs_url = 'https://www.dropbox.com/developers/reference/api'
    category = 'Files'

    # URLs to interact with the API
    request_token_url = 'https://api.dropbox.com/1/oauth/request_token'
    authorize_url = 'https://www.dropbox.com/1/oauth/authorize'
    access_token_url = 'https://api.dropbox.com/1/oauth/access_token'
    api_domains = ['api.dropbox.com', 'api-content.dropbox.com']

    signature_method = SIGNATURE_PLAINTEXT

    available_permissions = [
        (None, 'read and write to your entire Dropbox'),
    ]

    def get_user_id(self, key):
        r = self.api(key, self.api_domains[0], u'/1/account/info')
        return unicode(r.json()[u'uid'])

########NEW FILE########
__FILENAME__ = dwolla
from oauthlib.common import add_params_to_uri
import foauth.providers


class Dwolla(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'https://dwolla.com/'
    docs_url = 'http://developers.dwolla.com/dev/docs'
    category = 'Money'

    # Required by Dwolla's ToS
    disclaimer = "This application is not directly supported by Dwolla Corp. Dwolla Corp. makes no claims about this application.  This application is not endorsed or certified by Dwolla Corp."

    # URLs to interact with the API
    authorize_url = 'https://www.dwolla.com/oauth/v2/authenticate'
    access_token_url = 'https://www.dwolla.com/oauth/v2/token'
    api_domain = 'www.dwolla.com'

    available_permissions = [
        (None, 'access your account details'),
        ('Contacts', 'read your contacts'),
        ('Transactions', 'read your transaction history'),
        ('Balance', 'read your current balance'),
        ('Send', 'send money to others'),
        ('Request', 'request money from others'),
        ('Funding', 'view your bank accounts and other funding sources'),
    ]

    def bearer_type(self, token, r):
        r.url = add_params_to_uri(r.url, [((u'oauth_token', token))])
        return r

    def get_authorize_params(self, redirect_uri, scopes):
        # Always request account info, in order to get the user ID
        scopes.append('AccountInfoFull')
        return super(Dwolla, self).get_authorize_params(redirect_uri, scopes)

    def get_scope_string(self, scopes):
        return '|'.join(scopes)

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/oauth/rest/users/')
        return unicode(r.json()[u'Response'][u'Id'])

########NEW FILE########
__FILENAME__ = elance
import foauth.providers
from foauth import OAuthDenied


class Elance(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'https://www.elance.com/'
    docs_url = 'https://www.elance.com/q/api2'
    category = 'Career'

    # URLs to interact with the API
    authorize_url = 'https://api.elance.com/api2/oauth/authorize'
    access_token_url = 'https://api.elance.com/api2/oauth/token'
    api_domain = 'api.elance.com'

    available_permissions = [
        (None, 'access and manage your Elance account'),
    ]

    bearer_type = foauth.providers.BEARER_URI

    def parse_token(self, content):
        return super(Elance, self).parse_token(content)[u'data']

    def callback(self, data, *args, **kwargs):
        if data.get('error') == 'access_denied':
            raise OAuthDenied('Denied access to Elance')

        return super(Elance, self).callback(data, *args, **kwargs)

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/api2/profiles/my')
        return unicode(r.json()[u'data'][u'providerProfile'][u'userId'])

########NEW FILE########
__FILENAME__ = eventbrite
import foauth.providers


class Eventbrite(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'https://www.eventbrite.com/'
    docs_url = 'http://developer.eventbrite.com/doc/'
    category = 'Events'

    # URLs to interact with the API
    authorize_url = 'https://www.eventbrite.com/oauth/authorize'
    access_token_url = 'https://www.eventbrite.com/oauth/token'
    api_domain = 'www.eventbrite.com'

    available_permissions = [
        (None, 'read and write to your check-ins'),
    ]

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/json/user_get')
        return unicode(r.json()[u'user'][u'user_id'])

########NEW FILE########
__FILENAME__ = facebook
from oauthlib.common import add_params_to_uri
from werkzeug.urls import url_decode
import foauth.providers


class Facebook(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'https://facebook.com/'
    docs_url = 'https://developers.facebook.com/docs/'
    category = 'Social'

    # URLs to interact with the API
    authorize_url = 'https://www.facebook.com/dialog/oauth'
    access_token_url = 'https://graph.facebook.com/oauth/access_token'
    api_domain = 'graph.facebook.com'

    available_permissions = [
        (None, 'read your basic, public information'),
        ('email', 'access your email address'),
        ('user_about_me', 'access your profile information'),
        ('user_activities', 'access your favorite activities'),
        ('user_birthday', 'access your birthday'),
        ('user_checkins', 'access your checkins'),
        ('user_education_history', 'access your education history'),
        ('user_events', 'access your events'),
        ('user_groups', 'access your groups'),
        ('user_hometown', 'access your hometown'),
        ('user_interests', 'access your interests'),
        ('user_likes', 'access the things you like'),
        ('user_location', 'access your location'),
        ('user_notes', 'access your notes'),
        ('user_online_presence', 'access your online presence'),
        ('user_photos', 'access your photos'),
        ('user_questions', 'access your questions'),
        ('user_relationships', 'access your relationships'),
        ('user_relationship_details', 'access your relationship details'),
        ('user_religion_politics', 'access your religious and policial affiliations'),
        ('user_status', 'access your most recent status'),
        ('user_videos', 'access your videos'),
        ('user_website', 'access your website address'),
        ('user_work_history', 'access your work history'),
        ('friends_about_me', "access your friends' profile information"),
        ('friends_activities', "access your friends' favoriate activities"), ('friends_birthday', "access your friends' birthdays"),
        ('friends_checkins', "access your friends' checkins"),
        ('friends_education_history', "access your friends' education history"),
        ('friends_events', "access your friends' events"),
        ('friends_groups', "access your friends' groups"),
        ('friends_hometown', "access your friends' hometowns"),
        ('friends_interests', "access your friends' interests"),
        ('friends_likes', "access the things your friends like"),
        ('friends_location', "access your friends' locations"),
        ('friends_notes', "access your friends' notes"),
        ('friends_online_presence', "access your friends' online presence"),
        ('friends_photos', "access your friends' photos"),
        ('friends_questions', "access your friends' questions"),
        ('friends_relationships', "access your friends' relationships"),
        ('friends_relationship_details', "access your friends' relationship details"),
        ('friends_religion_politics', "access your friends' religious and political affiliations"),
        ('friends_status', "access your friends' most recent statuses"),
        ('friends_videos', "access your friends' videos"),
        ('friends_website', "access your friends' website addresses"),
        ('friends_work_history', "access your friends' work history"),
    ]

    def parse_token(self, content):
        data = url_decode(content)
        data['expires_in'] = data.get('expires', None)
        return data

    def bearer_type(self, token, r):
        r.url = add_params_to_uri(r.url, [((u'access_token', token))])
        return r

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/me')
        return r.json()[u'id']

########NEW FILE########
__FILENAME__ = familysearch
import requests

import foauth.providers


class FamilySearch(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'http://www.familysearch.com/'
    docs_url = 'https://familysearch.org/developers/docs/api/resources'
    category = 'Genealogy'
    favicon_url = 'https://familysearch.org/favicon.ico'

    # URLs to interact with the API
    authorize_url = 'https://sandbox.familysearch.org/cis-web/oauth2/v3/authorization'
    access_token_url = 'https://sandbox.familysearch.org/cis-web/oauth2/v3/token'
    api_domain = 'sandbox.familysearch.org'

    available_permissions = [
        (None, 'read and write to your family tree'),
    ]

    def get_access_token_response(self, redirect_uri, data):
        # Sending the (basically empty) client secret will fail,
        # so this must send its own custom request.
        return requests.post(self.get_access_token_url(), {
            'client_id': self.client_id,
            'grant_type': 'authorization_code',
            'code': data['code'],
            'redirect_uri': redirect_uri,
        }, verify=self.verify, auth=self.auth)

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/platform/users/current',
                     headers={'Accept': 'application/json'})
        return unicode(r.json()[u'users'][0][u'id'])

########NEW FILE########
__FILENAME__ = fitbit
import foauth.providers


class FitBit(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'http://www.fitbit.com/'
    docs_url = 'https://wiki.fitbit.com/display/API/Fitbit+API'
    category = 'Fitness'

    # URLs to interact with the API
    request_token_url = 'http://api.fitbit.com/oauth/request_token'
    authorize_url = 'http://www.fitbit.com/oauth/authorize'
    access_token_url = 'http://api.fitbit.com/oauth/access_token'
    api_domain = 'api.fitbit.com'

    available_permissions = [
        (None, 'read and write your fitness data'),
    ]

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/1/user/-/profile.json')
        return r.json()[u'user'][u'encodedId']

########NEW FILE########
__FILENAME__ = fivehundredpx
import foauth.providers


class FiveHundredPX(foauth.providers.OAuth1):
    # General info about the provider
    alias = '500px'
    name = '500px'
    provider_url = 'http://500px.com/'
    docs_url = 'https://github.com/500px/api-documentation'
    category = 'Pictures'

    # URLs to interact with the API
    request_token_url = 'https://api.500px.com/v1/oauth/request_token'
    authorize_url = 'https://api.500px.com/v1/oauth/authorize'
    access_token_url = 'https://api.500px.com/v1/oauth/access_token'
    api_domain = 'api.500px.com'

    available_permissions = [
        (None, 'access and manage your photos'),
    ]

    def get_user_id(self, key):
        r = self.api(key, self.api_domains[0], u'/v1/users')
        return unicode(r.json()[u'user'][u'id'])

########NEW FILE########
__FILENAME__ = flickr
import foauth.providers


class Flickr(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'http://www.flickr.com/'
    docs_url = 'http://www.flickr.com/services/api/'
    category = 'Pictures'

    # URLs to interact with the API
    request_token_url = 'http://www.flickr.com/services/oauth/request_token'
    authorize_url = 'http://www.flickr.com/services/oauth/authorize'
    access_token_url = 'http://www.flickr.com/services/oauth/access_token'
    api_domain = 'api.flickr.com'

    available_permissions = [
        (None, 'access your public and private photos'),
        ('write', 'upload, edit and replace your photos'),
        ('delete', 'upload, edit, replace and delete your photos'),
    ]
    permissions_widget = 'radio'

    def get_authorize_params(self, redirect_uri, scopes):
        params = super(Flickr, self).get_authorize_params(redirect_uri, scopes)
        params['perms'] = scopes[0] or 'read'
        return params

    def get_user_id(self, key):
        url = u'/services/rest/?method=flickr.people.getLimits'
        url += u'&format=json&nojsoncallback=1'
        r = self.api(key, self.api_domain, url)
        return r.json()[u'person'][u'nsid']

########NEW FILE########
__FILENAME__ = foursquare
from oauthlib.common import add_params_to_uri
import foauth.providers


class Foursquare(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'http://www.foursquare.com/'
    docs_url = 'https://developer.foursquare.com/overview/'
    category = 'Travel'

    # URLs to interact with the API
    authorize_url = 'https://foursquare.com/oauth2/authorize'
    access_token_url = 'https://foursquare.com/oauth2/access_token'
    api_domain = 'api.foursquare.com'

    available_permissions = [
        (None, 'read and write to your check-ins'),
    ]

    def bearer_type(self, token, r):
        r.url = add_params_to_uri(r.url, [((u'oauth_token', token))])
        return r

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/v2/users/self')
        return r.json()[u'response'][u'user'][u'id']

########NEW FILE########
__FILENAME__ = friendfeed
import foauth.providers


class Friendfeed(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'http://friendfeed.com/'
    docs_url = 'http://friendfeed.com/api/documentation'
    category = 'Social'

    # URLs to interact with the API
    request_token_url = 'https://friendfeed.com/account/oauth/request_token'
    authorize_url = 'https://friendfeed.com/account/oauth/authorize'
    access_token_url = 'https://friendfeed.com/account/oauth/access_token'
    api_domain = 'friendfeed-api.com'


########NEW FILE########
__FILENAME__ = geni
import foauth.providers


class Geni(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'http://www.geni.com/'
    docs_url = 'http://www.geni.com/platform/developer/help/reference'
    category = 'Genealogy'

    # URLs to interact with the API
    authorize_url = 'https://www.geni.com/platform/oauth/authorize'
    access_token_url = 'https://www.geni.com/platform/oauth/request_token'
    api_domain = 'www.geni.com'

    available_permissions = [
        (None, 'read and write to your family tree'),
    ]

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/api/profile')
        return unicode(r.json()[u'guid'])

########NEW FILE########
__FILENAME__ = getglue
import flask
import foauth.providers


class GetGlue(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'https://getglue.com/'
    docs_url = 'http://getglue.com/api'
    category = 'Movies/TV'

    # URLs to interact with the API
    request_token_url = 'https://api.getglue.com/oauth/request_token'
    authorize_url = 'http://getglue.com/oauth/authorize'
    access_token_url = 'https://api.getglue.com/oauth/access_token'
    api_domain = 'api.getglue.com'

    available_permissions = [
        (None, 'read and write your social checkins'),
    ]

    returns_token = False

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/v2/user/profile?format=json')
        return r.json()[u'profile'][u'username']

########NEW FILE########
__FILENAME__ = getsatisfaction
import foauth.providers


class GetSatisfaction(foauth.providers.OAuth1):
    # General info about the provider
    name = 'Get Satisfaction'
    provider_url = 'http://getsatisfaction.com/'
    docs_url = 'http://getsatisfaction.com/developers/api-resources'
    category = 'Support'

    # URLs to interact with the API
    request_token_url = 'http://getsatisfaction.com/api/request_token'
    authorize_url = 'http://getsatisfaction.com/api/authorize'
    access_token_url = 'http://getsatisfaction.com/api/access_token'
    api_domain = 'api.getsatisfaction.com'

    available_permissions = [
        (None, 'access your support requests'),
    ]

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/me.json')
        return unicode(r.json()[u'id'])

########NEW FILE########
__FILENAME__ = github
from werkzeug.urls import url_decode
import foauth.providers


class GitHub(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'https://github.com/'
    docs_url = 'http://developer.github.com/v3/'
    category = 'Code'

    # URLs to interact with the API
    authorize_url = 'https://github.com/login/oauth/authorize'
    access_token_url = 'https://github.com/login/oauth/access_token'
    api_domain = 'api.github.com'

    available_permissions = [
        (None, 'read your public profile, public repo info and gists'),
        ('user:email', 'read your email address'),
        ('user:follow', 'follow and unfollow users'),
        ('user', 'read and write to your entire profile'),
        ('public_repo', 'write to your public repo info'),
        ('repo', 'write to your public and private repo info'),
        ('gist', 'write to your gists'),
    ]

    supports_state = False

    def get_scope_string(self, scopes):
        return ','.join(scopes)

    def parse_token(self, content):
        return url_decode(content)

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/user')
        return unicode(r.json()[u'id'])

########NEW FILE########
__FILENAME__ = goodreads
import foauth.providers
from xml.dom import minidom


class Goodreads(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'http://www.goodreads.com/'
    docs_url = 'http://www.goodreads.com/api'
    category = 'Books'

    # URLs to interact with the API
    request_token_url = 'http://www.goodreads.com/oauth/request_token'
    authorize_url = 'http://www.goodreads.com/oauth/authorize'
    access_token_url = 'http://www.goodreads.com/oauth/access_token'
    api_domain = 'www.goodreads.com'

    https = False

    available_permissions = [
        (None, 'read and write to your reading history'),
    ]

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/api/auth_user')
        dom = minidom.parseString(r.content)
        return dom.getElementsByTagName('user')[0].getAttribute('id')

########NEW FILE########
__FILENAME__ = google
import foauth.providers


class Google(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'http://google.com/'
    docs_url = 'http://code.google.com/more/'
    category = 'Productivity'

    # URLs to interact with the API
    authorize_url = 'https://accounts.google.com/o/oauth2/auth'
    access_token_url = 'https://accounts.google.com/o/oauth2/token'
    api_domains = [
        'www.googleapis.com',
        'www.blogger.com',
        'docs.google.com',
        'www.google.com',
        # TODO: Find more and add them here
    ]

    bearer_type = foauth.providers.BEARER_URI

    # Scopes: https://code.google.com/oauthplayground/
    # Also, search for "site:code.google.com https://www.googleapis.com/auth/"
    available_permissions = [
        (None, 'read your email address'),
        ('https://www.googleapis.com/auth/userinfo.profile', 'read your basic profile information'),
        ('https://www.googleapis.com/auth/analytics', 'access your analytics'),
        ('https://www.googleapis.com/auth/blogger', 'access your blogs'),
        ('https://www.googleapis.com/auth/books', 'access your books'),
        ('https://www.googleapis.com/auth/calendar', 'access your calendars'),
        ('https://www.googleapis.com/auth/contacts', 'access your contacts'),
        ('https://www.googleapis.com/auth/structuredcontent', 'access shopping data'),
        ('https://www.googleapis.com/auth/docs', 'access your documents'),
        ('https://www.googleapis.com/auth/picasa', 'access your photos'),
        ('https://www.googleapis.com/auth/spreadsheets', 'access your spreadsheets'),
        ('https://www.googleapis.com/auth/tasks', 'read and write to your tasks'),
        ('https://www.googleapis.com/auth/plus.me', 'access your Google+ data'),
        ('https://www.googleapis.com/auth/urlshortener', 'access your shortened URLs'),
        ('https://www.googleapis.com/auth/youtube', 'access your videos'),
        ('https://www.googleapis.com/auth/adsense', 'manage your adsense data'),
        ('https://www.googleapis.com/auth/gan', 'manage your affiliate options'),
        ('https://www.googleapis.com/auth/devstorage.read_write', 'read and write to your cloud storage'),
        ('https://www.googleapis.com/auth/structuredcontent', 'access shopping content'),
        ('https://www.googleapis.com/auth/chromewebstore', 'access your Chrome store settings'),
        ('https://www.googleapis.com/auth/drive.file', 'access your Google Drive'),
        ('https://www.googleapis.com/auth/latitude.all.best', 'access your location information'),
        ('https://www.googleapis.com/auth/moderator', 'access moderator content'),
        ('https://www.googleapis.com/auth/orkut', 'access your Orkut data'),
        ('https://www.googleapis.com/auth/youtube', 'access your videos'),
        ('https://www.googleapis.com/auth/fusiontables.readonly', 'read your fusion tables'),
        ('https://www.googleapis.com/auth/fusiontables', 'read and write to your fusion tables'),

        ('http://www.google.com/reader/api', 'access your news feeds'),
        ('http://www.google.com/webmasters/tools/feeds/', 'access your webmaster tools'),
        ('http://finance.google.com/finance/feeds/', 'access financial information'),
        ('https://mail.google.com/', 'access your email'),
        ('http://maps.google.com/maps/feeds/', 'access your custom maps'),
        ('https://sites.google.com/feeds/', 'access your sites'),

        # TODO: Find more and add them here
    ]

    def get_authorize_params(self, redirect_uri, scopes):
        scopes.append('https://www.googleapis.com/auth/userinfo.email')
        params = super(Google, self).get_authorize_params(redirect_uri, scopes)
        params['access_type'] = 'offline'
        params['approval_prompt'] = 'force'
        return params

    def get_user_id(self, key):
        r = self.api(key, self.api_domains[0], u'/oauth2/v2/userinfo')
        return r.json()[u'id']

    def refresh_token(self, token):
        # Retain the original refresh token, just to be sure we have one
        details = super(Google, self).refresh_token(token)
        details['refresh_token'] = token
        return details

########NEW FILE########
__FILENAME__ = groupme
import flask
import foauth.providers


class GroupMe(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'https://groupme.com/'
    docs_url = 'http://dev.groupme.com/docs/v3'
    category = 'Social'

    # URLs to interact with the API
    authorize_url = 'https://api.groupme.com/oauth/authorize'
    api_domain = 'api.groupme.com'

    available_permissions = [
        (None, 'access and manage your profile and messages'),
    ]

    def get_authorize_params(self, redirect_uri, scopes):
        return {'client_id': self.client_id}

    def callback(self, data, url_name):
        # The access token comes back directly in the callback
        return data

    def bearer_type(self, token, r):
        r.headers['X-Access-Token'] = token
        return r

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/v3/users/me')
        return unicode(r.json()[u'response'][u'id'])

########NEW FILE########
__FILENAME__ = heroku
import foauth.providers


class Heroku(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'https://heroku.com/'
    docs_url = 'https://devcenter.heroku.com/articles/platform-api-reference'
    category = 'Code'

    # URLs to interact with the API
    authorize_url = 'https://id.heroku.com/oauth/authorize'
    access_token_url = 'https://id.heroku.com/oauth/token'
    api_domain = 'api.heroku.com'

    available_permissions = [
        (None, 'read your account information'),
        ('read', 'read all of your apps and resources, excluding configuration values'),
        ('write', 'write to all of your apps and resources, excluding configuration values'),
        ('read-protected', 'read all of your apps and resources, including configuration values'),
        ('write-protected', 'write to all of your apps and resources, including configuration values'),
        ('global', 'read and write to all of your account, apps and resources'),
    ]
    permissions_widget = 'radio'

    def get_authorize_params(self, redirect_uri, scopes):
        params = super(Heroku, self).get_authorize_params(redirect_uri, scopes)
        params['scope'] = scopes[0] or 'identity'
        return params

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/account')
        return unicode(r.json()[u'id'])

########NEW FILE########
__FILENAME__ = imgur
import foauth.providers


class Imgur(foauth.providers.OAuth2):
    # General info about the provider
    name = 'imgur'
    provider_url = 'http://imgur.com/'
    docs_url = 'http://api.imgur.com/'
    category = 'Pictures'

    # URLs to interact with the API
    authorize_url = 'https://api.imgur.com/oauth2/authorize'
    access_token_url = 'https://api.imgur.com/oauth2/token'
    api_domain = 'api.imgur.com'

    available_permissions = [
        (None, 'read and write to your images'),
    ]

    # This is hopefully a short-term fix to a hostname mismatch on their end
    verify = False

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/3/account/me.json')
        return unicode(r.json()[u'data'][u'id'])

########NEW FILE########
__FILENAME__ = instagram
import foauth.providers


class Instagram(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'http://instagram.com'
    docs_url = 'http://instagram.com/developer/'
    category = 'Pictures'

    # URLs to interact with the API
    authorize_url = 'https://api.instagram.com/oauth/authorize/'
    access_token_url = 'https://api.instagram.com/oauth/access_token'
    api_domain = 'api.instagram.com'

    available_permissions = [
        (None, 'read all data related to you'),
        ('comments', 'create or delete comments'),
        ('relationships', 'follow and unfollow users'),
        ('likes', 'like and unlike items'),
    ]

    bearer_type = foauth.providers.BEARER_URI
    supports_state = False

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/v1/users/self')
        return r.json()[u'data'][u'id']

########NEW FILE########
__FILENAME__ = lastfm
import flask
import hashlib
import itertools
import requests
from urlparse import urlparse, parse_qsl
from xml.dom import minidom

import foauth.providers


class LastFM(foauth.providers.OAuth2):
    # General info about the provider
    name = 'last.fm'
    provider_url = 'http://last.fm/'
    docs_url = 'http://www.last.fm/api/intro'
    category = 'Music'

    # URLs to interact with the API
    authorize_url = 'http://www.last.fm/api/auth/'
    access_token_url = 'http://ws.audioscrobbler.com/2.0/'
    api_domain = 'ws.audioscrobbler.com'

    available_permissions = [
        (None, 'read and manage your music history'),
    ]

    def parse_token(self, content):
        dom = minidom.parseString(content)
        access_token = dom.getElementsByTagName('key')[0].firstChild.nodeValue
        return {'access_token': access_token}

    def get_authorize_params(self, *args, **kwargs):
        return {
            'api_key': self.client_id,
        }

    def callback(self, data, *args, **kwargs):
        auth = Session(self.client_id, self.client_secret, data['token'])
        params = {
            'method': 'auth.getSession',
            'api_key': self.client_id,
            'token': data['token'],
        }
        params['api_sig'] = auth.get_signature(params.items())
        resp = requests.get(self.get_access_token_url(), params=params)

        return self.parse_token(resp.content)

    def api(self, key, domain, path, method='GET', params=None, data=None,
            headers=None):
        url = 'http://%s%s' % (domain, path)
        auth = Session(self.client_id, self.client_secret, key.access_token)
        return requests.request(method, url, auth=auth, params=params or {},
                                data=data or {}, headers=headers or {})

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/2.0/?method=user.getInfo')
        dom = minidom.parseString(r.content)
        return dom.getElementsByTagName('id')[0].firstChild.nodeValue


class Session(object):
    def __init__(self, client_id, client_secret, token):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = token

    def __call__(self, r):
        if r.body:
            params = parse_sql(r.body)
        else:
            params = parse_qsl(urlparse(r.url).query)
        signature = self.get_signature(params)
        r.prepare_url(r.url, {'sk': self.token, 'api_key': self.client_id,
                              'api_sig': self.get_signature(params)})
        return r

    def get_signature(self, param_list):
        data = ''.join(i.encode('utf8') for i in itertools.chain(*sorted(param_list)))
        return hashlib.md5(data + self.client_secret).hexdigest()

########NEW FILE########
__FILENAME__ = launchpad
from oauthlib.oauth1.rfc5849 import SIGNATURE_PLAINTEXT, SIGNATURE_TYPE_BODY, SIGNATURE_TYPE_AUTH_HEADER
import requests

import foauth.providers

class Launchpad(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'https://launchpad.net/'
    docs_url = 'https://launchpad.net/+apidoc/1.0.html'
    category = 'Code'

    # URLs to interact with the API
    request_token_url = 'https://launchpad.net/+request-token'
    authorize_url = 'https://launchpad.net/+authorize-token'
    access_token_url = 'https://launchpad.net/+access-token'
    api_domains = ['api.launchpad.net', 'api.staging.launchpad.net']

    signature_method = SIGNATURE_PLAINTEXT
    returns_token = False
    signature_type = SIGNATURE_TYPE_AUTH_HEADER

    available_permissions = [
        (None, 'read non-privade data'),
        ('WRITE_PUBLIC', 'change non-private data'),
        ('READ_PRIVATE', 'read anything, including private data'),
        ('WRITE_PRIVATE', 'change anything, including private data'),
    ]
    permissions_widget = 'radio'

    def __init__(self, *args, **kwargs):
        super(Launchpad, self).__init__(*args, **kwargs)
        self.client_secret = ''  # Must be empty to satisfy Launchpad

    def get_authorize_params(self, redirect_uri, scopes):
        params = super(Launchpad, self).get_authorize_params(redirect_uri, scopes)
        params['allow_permission'] = scopes[0] or 'READ_PUBLIC'
        return params

    def get_request_token_response(self, redirect_uri, scopes):
        # Launchpad expects the signature in the body, but we don't have
        # additional parameters, so oauthlib doesn't help us here.
        return requests.post(self.get_request_token_url(),
                             data={'oauth_consumer_key': self.client_id,
                                   'oauth_signature_method': 'PLAINTEXT',
                                   'oauth_signature': '&'})

    def get_access_token_response(self, token, secret, verifier=None):
        # Launchpad expects the signature in the body, but we don't have
        # additional parameters, so oauthlib doesn't help us here.
        req = requests.Request(url=self.authorize_url,
                               data={'oauth_consumer_key': self.client_id,
                                     'oauth_token': token,
                                     'oauth_signature_method': 'PLAINTEXT',
                                     'oauth_signature': '&%s' % secret})
        req = req.prepare()
        return requests.post(self.get_access_token_url(),
                             data={'oauth_consumer_key': self.client_id,
                                   'oauth_token': token,
                                   'oauth_signature_method': 'PLAINTEXT',
                                   'oauth_signature': '&%s' % secret})

    def get_user_id(self, key):
        r = super(Launchpad, self).api(key, self.api_domains[0], '/1.0/people/+me')
        return r.json()[u'name']

########NEW FILE########
__FILENAME__ = linkedin
import foauth.providers
from foauth import OAuthDenied


class LinkedIn(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'http://www.linkedin.com/'
    docs_url = 'https://developer.linkedin.com/documents/linkedin-api-resource-map'
    category = 'Career'

    # URLs to interact with the API
    request_token_url = 'https://api.linkedin.com/uas/oauth/requestToken'
    authorize_url = 'https://www.linkedin.com/uas/oauth/authorize'
    access_token_url = 'https://api.linkedin.com/uas/oauth/accessToken'
    api_domain = 'api.linkedin.com'

    available_permissions = [
        (None, 'read and write to your employment information'),
    ]

    def callback(self, data, *args, **kwargs):
        if data.get('oauth_problem', '') == 'user_refused':
            raise OAuthDenied('Denied access to LinkedIn')

        return super(LinkedIn, self).callback(data, *args, **kwargs)

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/v1/people/~:(id)?format=json')
        return r.json()[u'id']

########NEW FILE########
__FILENAME__ = liveconnect
import foauth.providers


class LiveConnect(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'https://www.live.com/'
    docs_url = 'http://msdn.microsoft.com/en-us/library/hh243648.aspx'
    category = 'Productivity'

    # URLs to interact with the API
    authorize_url = 'https://oauth.live.com/authorize'
    access_token_url = 'https://oauth.live.com/token'
    api_domain = 'apis.live.net'

    available_permissions = [
        ('wl.basic', 'read your basic info and contacts'),
        ('wl.offline_access', "access your information while you're not logged in"),
        ('wl.birthday', 'access your complete birthday'),
        ('wl.calendars', 'read your calendars and events'),
        ('wl.calendars_update', 'write to your calendars and events'),
        ('wl.contacts_birthday', "access your contacts' birthdays"),
        ('wl.contacts_create', 'add new contacts to your address book'),
        ('wl.contacts_calendars', "read your contacts' calendars"),
        ('wl.contacts_photos', "read your contacts' photos and other media"),
        ('wl.contacts_skydrive', 'read files your contacts have shared with you'),
        ('wl.emails', 'read your email addresses'),
        ('wl.events_create', 'create events on your default calendar'),
        ('wl.messenger', 'chat with your contacts using Live Messenger'),
        ('wl.phone_numbers', 'read your phone numbers'),
        ('wl.photos', 'read your photos and other media'),
        ('wl.postal_addresses', 'read your postal addresses'),
        ('wl.share', 'update your status message'),
        ('wl.skydrive', "read files you've stored in SkyDrive"),
        ('wl.skydrive_update', "write to files you've stored in SkyDrive"),
        ('wl.work_profile', 'read your employer and work position information'),
        ('wl.applications', 'access the client IDs you use to interact with Live services'),
        ('wl.applications_create', 'create new client IDs to interact with Live services'),
    ]

    bearer_type = foauth.providers.BEARER_URI

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/v5.0/me')
        return r.json()[u'id']

########NEW FILE########
__FILENAME__ = meetup
import foauth.providers


class Meetup(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'http://www.meetup.com/'
    docs_url = 'http://www.meetup.com/meetup_api/'
    category = 'Events'

    # URLs to interact with the API
    authorize_url = 'https://secure.meetup.com/oauth2/authorize'
    access_token_url = 'https://secure.meetup.com/oauth2/access'
    api_domain = 'api.meetup.com'

    bearer_type = foauth.providers.BEARER_URI

    available_permissions = [
        (None, 'access your groups, create and edit events, and post photos'),
        ('messaging', 'send and receive messages'),
        ('ageless', 'keep the authorization active for two weeks'),
    ]

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/2/profiles?member_id=self')
        return unicode(r.json()[u'results'][0][u'member_id'])

########NEW FILE########
__FILENAME__ = miso
import foauth.providers


class Miso(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'http://gomiso.com/'
    docs_url = 'http://gomiso.com/developers/endpoints'
    category = 'Movies/TV'

    # URLs to interact with the API
    request_token_url = 'http://gomiso.com/oauth/request_token'
    authorize_url = 'http://gomiso.com/oauth/authorize'
    access_token_url = 'http://gomiso.com/oauth/access_token'
    api_domain = 'gomiso.com'

    available_permissions = [
        (None, 'read and write to your TV history'),
    ]

    https = False

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/api/oauth/v1/users/show.json')
        return unicode(r.json()[u'user'][u'id'])

########NEW FILE########
__FILENAME__ = netflix
import urlparse

import foauth.providers
from oauthlib.oauth1.rfc5849 import SIGNATURE_TYPE_QUERY


class Netflix(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'https://www.netflix.com/'
    favicon_url = 'https://netflix.hs.llnwd.net/e1/en_US/icons/nficon.ico'
    docs_url = 'http://developer.netflix.com/docs'
    category = 'Movies/TV'

    # URLs to interact with the API
    request_token_url = 'http://api-public.netflix.com/oauth/request_token'
    authorize_url = 'https://api-user.netflix.com/oauth/login'
    access_token_url = 'http://api-public.netflix.com/oauth/access_token'
    api_domain = 'api-public.netflix.com'

    available_permissions = [
        (None, 'read and manage your queue'),
    ]

    https = False
    signature_type = SIGNATURE_TYPE_QUERY

    def get_authorize_params(self, *args, **kwargs):
        params = super(Netflix, self).get_authorize_params(*args, **kwargs)
        params['oauth_consumer_key'] = self.client_id
        return params

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/users/current',
                     params={'output': 'json'})
        redirect = r.json()[u'resource'][u'link'][u'href']
        parts = urlparse.urlparse(redirect)
        r = self.api(key, parts.netloc, parts.path,
                     params={'output': 'json'})
        return r.json()[u'user'][u'user_id']

########NEW FILE########
__FILENAME__ = odesk
import foauth.providers


class ODesk(foauth.providers.OAuth1):
    # General info about the provider
    name = 'oDesk'
    provider_url = 'https://www.odesk.com/'
    docs_url = 'http://developers.odesk.com/w/page/12363985/API Documentation'
    category = 'Career'

    # URLs to interact with the API
    request_token_url = 'https://www.odesk.com/api/auth/v1/oauth/token/request'
    authorize_url = 'https://www.odesk.com/services/api/auth'
    access_token_url = 'https://www.odesk.com/api/auth/v1/oauth/token/access'
    api_domain = 'www.odesk.com'

    available_permissions = [
        (None, 'access your basic info'),
        (None, 'close your contracts'),
        (None, 'create, modify and remove job posts'),
        (None, 'make a job offer'),
        (None, 'make one-time payments to your contractors'),
        (None, 'view your contracts'),
        (None, 'access your payment history'),
        (None, 'view your job posts'),
        (None, 'view your job offers'),
        (None, 'send and organize your messages'),
        (None, 'access your messages'),
        (None, 'view the structure of your companies/teams'),
        (None, 'view task codes'),
        (None, 'modify task codes'),
        (None, 'generate time and financial reports for your companies and teams'),
        (None, 'view your workdiary'),
        (None, 'modify your workdiary'),
    ]

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/api/auth/v1/info.json')
        return unicode(r.json()[u'auth_user'][u'uid'])

########NEW FILE########
__FILENAME__ = ohloh
import foauth.providers


class Ohloh(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'https://www.ohloh.net/'
    docs_url = 'http://meta.ohloh.net/reference/'
    category = 'Code'

    # URLs to interact with the API
    request_token_url = 'http://www.ohloh.net/oauth/request_token'
    authorize_url = 'http://www.ohloh.net/oauth/authorize'
    access_token_url = 'http://www.ohloh.net/oauth/access_token'
    api_domain = 'www.ohloh.net'

    available_permissions = [
        (None, 'read and write to your software usage'),
    ]

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/accounts/me.json')
        return r.json()[u'account'][u'id']

########NEW FILE########
__FILENAME__ = openstreetmap
from xml.dom import minidom
from werkzeug.urls import url_decode

import foauth.providers


class OpenStreetMap(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'http://www.openstreetmap.org/'
    docs_url = 'http://wiki.openstreetmap.org/wiki/API'
    category = 'Mapping'

    # URLs to interact with the API
    request_token_url = 'http://www.openstreetmap.org/oauth/request_token'
    authorize_url = 'http://www.openstreetmap.org/oauth/authorize'
    access_token_url = 'http://www.openstreetmap.org/oauth/access_token'
    api_domain = 'api.openstreetmap.org'

    available_permissions = [
        (None, 'read your user preferences'),
        (None, 'modify your user preferences'),
        (None, 'created diary entries, comments and make friends'),
        (None, 'modify the map'),
        (None, 'read your private GPS traces'),
        (None, 'upload GPS traces'),
        (None, 'modify notes'),
    ]
    disclaimer = "You can select which permissions you want to authorize on the next screen, within OpenStreetMap."

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, '/api/0.6/user/details')
        dom = minidom.parseString(r.content)
        return dom.getElementsByTagName('user')[0].getAttribute('id')

########NEW FILE########
__FILENAME__ = paypal
import foauth.providers


class PayPal(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'https://www.paypal.com/'
    docs_url = 'https://developer.paypal.com/webapps/developer/docs/api/'
    category = 'Money'

    # URLs to interact with the API
    authorize_url = 'https://www.paypal.com/webapps/auth/protocol/openidconnect/v1/authorize'
    access_token_url = 'https://api.paypal.com/v1/identity/openidconnect/tokenservice'
    api_domain = 'api.paypal.com'

    available_permissions = [
        (None, 'access your user ID'),
        ('profile', 'access your name, gender, date of birth and geographic region'),
        ('email', 'access your email address'),
        ('address', 'access your physical address information'),
        ('phone', 'access your phone number'),
        ('https://uri.paypal.com/services/paypalattributes', 'access your account information'),
        ('https://api.paypal.com/v1/payments/.*', 'Access your payments'),
        ('https://api.paypal.com/v1/vault/credit-card', 'Access your credit cards'),
        ('https://api.paypal.com/v1/vault/credit-card/.*', 'Access your credit card history'),
    ]

    def get_authorize_params(self, redirect_uri, scopes):
        # We always need to at least request something
        scopes.append('openid')
        params = super(PayPal, self).get_authorize_params(redirect_uri, scopes)
        return params

    def parse_token(self, content):
        params = super(PayPal, self).parse_token(content)
        return params

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/v1/identity/openidconnect/userinfo/',
                     params={'schema': 'openid'})
        return unicode(r.json()[u'user_id'])

########NEW FILE########
__FILENAME__ = photobucket
import foauth.providers
from oauthlib.oauth1.rfc5849 import SIGNATURE_TYPE_QUERY


class Photobucket(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'http://www.photobucket.com/'
    docs_url = 'http://pic.pbsrc.com/dev_help/WebHelpPublic/PhotobucketPublicHelp.htm'
    category = 'Pictures'

    # URLs to interact with the API
    request_token_url = 'http://api.photobucket.com/login/request'
    authorize_url = 'http://photobucket.com/apilogin/login'
    access_token_url = 'http://api.photobucket.com/login/access'
    api_domain = 'api.photobucket.com'

    available_permissions = [
        (None, 'read and manage your pictures'),
    ]

    https = False
    signature_type = SIGNATURE_TYPE_QUERY

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/user', params={'format': 'json'})
        return r.json()[u'content'][u'username']

########NEW FILE########
__FILENAME__ = plurk
import foauth.providers


class Plurk(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'http://www.plurk.com/'
    docs_url = 'http://www.plurk.com/API#toc'
    category = 'Social'

    # URLs to interact with the API
    request_token_url = 'https://www.plurk.com/OAuth/request_token'
    authorize_url = 'http://www.plurk.com/OAuth/authorize'
    access_token_url = 'https://www.plurk.com/OAuth/access_token'
    api_domain = 'www.plurk.com'

    available_permissions = [
        (None, 'access and update your profile and plurks'),
    ]

    https = False

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/APP/Users/currUser')
        return unicode(r.json()[u'id'])

########NEW FILE########
__FILENAME__ = pocket
from werkzeug.urls import url_decode
import requests
import foauth.providers


class Pocket(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'http://getpocket.com/'
    docs_url = 'http://getpocket.com/developer/docs/overview'
    category = 'News'

    # URLs to interact with the API
    request_token_url = 'https://getpocket.com/v3/oauth/request'
    authorize_url = 'https://getpocket.com/auth/authorize'
    access_token_url = 'https://getpocket.com/v3/oauth/authorize'
    api_domain = 'getpocket.com'

    available_permissions = [
        (None, 'access your saved articles'),
    ]
    supports_state = False

    def get_authorize_params(self, redirect_uri, scopes):
        params = super(Pocket, self).get_authorize_params(redirect_uri, scopes)
        r = requests.post(self.request_token_url, data={
                'consumer_key': params['client_id'],
                'redirect_uri': redirect_uri,
            })
        data = url_decode(r.content)
        redirect_uri = '%s&code=%s' % (params['redirect_uri'], data['code'])
        return {
            'request_token': data['code'],
            'redirect_uri': redirect_uri,
        }

    def get_access_token_response(self, redirect_uri, data):
        return requests.post(self.get_access_token_url(), {
            'consumer_key': self.client_id,
            'code': data['code'],
            'redirect_uri': redirect_uri
        })

    def parse_token(self, content):
        data = url_decode(content)
        data['service_user_id'] = data['username']
        return data

    def bearer_type(self, token, r):
        r.prepare_url(r.url, {'consumer_key': self.client_id, 'access_token': token})
        return r

########NEW FILE########
__FILENAME__ = ravelry
import foauth.providers


class Ravelry(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'http://www.ravelry.com/'
    docs_url = 'http://www.ravelry.com/groups/ravelry-api/pages/API-Documentation'
    category = 'Crafts'

    # URLs to interact with the API
    request_token_url = 'https://www.ravelry.com/oauth/request_token'
    authorize_url = 'https://www.ravelry.com/oauth/authorize'
    access_token_url = 'https://www.ravelry.com/oauth/access_token'
    api_domain = 'api.ravelry.com'

    available_permissions = [
        (None, 'read and write to your knitting data'),
    ]

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/current_user.json')
        return unicode(r.json()[u'user'][u'id'])

########NEW FILE########
__FILENAME__ = rdio
from werkzeug.urls import url_decode

import foauth.providers


class Rdio(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'http://www.rdio.com/'
    favicon_url = 'http://www.rdio.com/media/favicon_rdio_2012_11_15.ico'
    docs_url = 'http://developer.rdio.com/docs/REST/'
    category = 'Music'

    # URLs to interact with the API
    request_token_url = 'http://api.rdio.com/oauth/request_token'
    authorize_url = 'https://www.rdio.com/account/oauth1/authorize/'
    access_token_url = 'http://api.rdio.com/oauth/access_token'
    api_domain = 'api.rdio.com'

    available_permissions = [
        (None, 'access and manage your music'),
    ]

    https = False

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/1/', method='POST', data={
            'method': 'currentUser',
        })
        return unicode(r.json()[u'result'][u'key'])

########NEW FILE########
__FILENAME__ = readmill
import foauth.providers


class Readmill(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'http://readmill.com/'
    docs_url = 'https://github.com/Readmill/api/wiki'
    category = 'Books'

    # URLs to interact with the API
    authorize_url = 'http://readmill.com/oauth/authorize'
    access_token_url = 'http://readmill.com/oauth/token'
    api_domain = 'api.readmill.com'

    available_permissions = [
        (None, 'read and write to your reading history'),
        ('non-expiring', 'access your data indefinitely'),
    ]

    bearer_type = foauth.providers.BEARER_URI

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/me')
        return unicode(r.json()[u'id'])

########NEW FILE########
__FILENAME__ = reddit
from oauthlib.oauth2.draft25 import utils
import foauth.providers


class Reddit(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'http://www.reddit.com/'
    docs_url = 'http://www.reddit.com/dev/api'
    category = 'News'

    # URLs to interact with the API
    authorize_url = 'https://ssl.reddit.com/api/v1/authorize'
    access_token_url = 'https://ssl.reddit.com/api/v1/access_token'
    api_domain = 'oauth.reddit.com'

    available_permissions = [
        (None, 'access your identity information'),
        ('read', 'read information about articles'),
        ('vote', 'vote on articles'),
        ('submit', 'submit new articles and comments'),
        ('edit', 'edit your posts and comments'),
        ('mysubreddits', 'manage your subreddits'),
        ('subscribe', 'manage your subscriptions'),
        ('modlog', 'view your moderation logs'),
        ('modposts', 'moderate posts in your subreddits'),
        ('modflair', 'manage and assign flair in your subreddits'),
        ('modconfig', 'manage the configuration of your subreddits'),
        ('privatemessages', 'read and write to your private messages'),
    ]

    def __init__(self, *args, **kwargs):
        super(Reddit, self).__init__(*args, **kwargs)
        self.auth = (self.client_id, self.client_secret)

    def get_authorize_params(self, redirect_uri, scopes):
        # Always request account info, in order to get the user ID
        scopes.append('identity')
        params = super(Reddit, self).get_authorize_params(redirect_uri, scopes)
        # Make sure we get refresh tokens
        params['duration'] = 'permanent'
        return params

    def get_scope_string(self, scopes):
        return ','.join(scopes)

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/api/v1/me')
        return unicode(r.json()[u'id'])

########NEW FILE########
__FILENAME__ = rememberthemilk
import flask
import hashlib
import itertools
import requests
from urlparse import urlparse, parse_qsl
from xml.dom import minidom

import foauth.providers


class RememberTheMilk(foauth.providers.OAuth2):
    # General info about the provider
    name = 'Remember the Milk'
    provider_url = 'http://rememberthemilk.com/'
    docs_url = 'https://www.rememberthemilk.com/services/api/'
    category = 'Tasks'

    # URLs to interact with the API
    authorize_url = 'http://www.rememberthemilk.com/services/auth/'
    access_token_url = 'http://api.rememberthemilk.com/services/rest/'
    api_domain = 'api.rememberthemilk.com'

    available_permissions = [
        (None, 'access your tasks, notes and contacts'),
        ('write', 'access, add and edit your tasks, notes and contacts'),
        ('delete', 'access, add, edit and delete your tasks, notes and contacts'),
    ]
    permissions_widget = 'radio'

    def parse_token(self, content):
        dom = minidom.parseString(content)
        access_token = dom.getElementsByTagName('token')[0].firstChild.nodeValue
        return {'access_token': access_token}

    def get_authorize_params(self, redirect_uri, scopes):
        params = {'api_key': self.client_id}

        if any(scopes):
            params['perms'] = scopes[0]
        else:
            params['perms'] = 'read'

        auth = Auth(self.client_id, self.client_secret, '')
        params['api_sig'] = auth.get_signature(params.items())
        return params

    def callback(self, data, *args, **kwargs):
        auth = Auth(self.client_id, self.client_secret, '')
        params = {
            'method': 'rtm.auth.getToken',
            'api_key': self.client_id,
            'frob': data['frob'],
        }
        params['api_sig'] = auth.get_signature(params.items())
        resp = requests.get(self.get_access_token_url(), params=params)

        return self.parse_token(resp.content)

    def api(self, key, domain, path, method='GET', params=None, data=None,
            headers=None):
        url = 'http://%s%s' % (domain, path)
        auth = Auth(self.client_id, self.client_secret, key.access_token)
        return requests.request(method, url, auth=auth, params=params or {},
                                data=data or {}, headers=headers or {})

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/services/rest/?method=rtm.auth.checkToken')
        dom = minidom.parseString(r.content)
        return dom.getElementsByTagName('user')[0].getAttribute('id')


class Auth(object):
    def __init__(self, client_id, client_secret, auth_token):
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_token = auth_token

    def __call__(self, r):
        r.prepare_url(r.url, {'api_key': self.client_id, 'auth_token': self.auth_token})
        if r.body:
            params = parse_sql(r.body)
        else:
            params = parse_qsl(urlparse(r.url).query)
        r.prepare_url(r.url, {'api_sig': self.get_signature(params)})
        return r

    def get_signature(self, param_list):
        data = ''.join(i.encode('utf8') for i in itertools.chain(*sorted(param_list)))
        return hashlib.md5(self.client_secret + data).hexdigest()

########NEW FILE########
__FILENAME__ = runkeeper
import foauth.providers


class Runkeeper(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'http://runkeeper.com/'
    docs_url = 'http://developer.runkeeper.com/healthgraph/overview'
    category = 'Fitness'

    # URLs to interact with the API
    authorize_url = 'https://runkeeper.com/apps/authorize'
    access_token_url = 'https://runkeeper.com/apps/token'
    api_domain = 'api.runkeeper.com'

    available_permissions = [
        (None, 'access your health and fitness data'),
    ]

    def get_user_id(self, key):
        r = self.api(key, self.api_domains[0], u'/user')
        return unicode(r.json()[u'userID'])

########NEW FILE########
__FILENAME__ = shutterfly
import datetime
import flask
import hashlib
import itertools
import requests
from urlparse import urlparse, parse_qsl
from xml.dom import minidom

import foauth.providers


class Shutterfly(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'http://www.shutterfly.com/'
    docs_url = 'http://www.shutterfly.com/documentation/start.sfly'
    category = 'Pictures'

    # URLs to interact with the API
    authorize_url = 'http://www.shutterfly.com/oflyuser/grantApp.sfly'
    api_domain = 'ws.shutterfly.com'

    available_permissions = [
        (None, 'read and manage your photos and products'),
    ]

    def get_authorize_params(self, redirect_uri, scopes):
        auth = Session(self.client_id, self.client_secret)
        req = requests.Request(url=self.authorize_url, auth=auth, params={
            'oflyCallbackUrl': redirect_uri,
        })
        params = parse_qsl(urlparse(req.prepare().url).query)

        return params

    def callback(self, data, *args, **kwargs):
        return {
            'access_token': data['oflyUserid'],
        }

    def api(self, key, domain, path, method='GET', params=None, data=None,
            headers=None):
        url = 'https://%s%s' % (domain, path)
        auth = Session(self.client_id, self.client_secret, key.access_token)
        return requests.request(method, url, auth=auth, params=params or {},
                                data=data or {}, headers=headers or {})

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/user')
        dom = minidom.parseString(r.content)
        nodes = dom.getElementsByTagNameNS('http://openfly.shutterfly.com/v1.0', 'userid')
        return nodes[0].firstChild.nodeValue


class Session(object):
    def __init__(self, client_id, client_secret, token=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = token

    def __call__(self, r):
        if self.token:
            r.prepare_url(r.url, params={'oflyUserid': self.token})

        parsed_url = urlparse(r.url)
        path = parsed_url.path.rstrip('/')
        params = parse_qsl(parsed_url.query)

        timestamp = self.get_timestamp()
        call_params = [
            ('oflyAppId', self.client_id),
            ('oflyHashMeth', 'SHA1'),
            ('oflyTimestamp', timestamp),
        ]
        signature = self.get_signature(path, params, call_params)

        r.prepare_url(r.url, params=dict(call_params, oflyApiSig=signature))
        return r

    def get_timestamp(self):
        now = datetime.datetime.utcnow()
        return now.isoformat()[:23] + 'Z'

    def iterparams(self, params):
        # Pull the parameter values out of their lists,
        # yielding multiple values for a key if necessary.
        for key in params:
            for val in params[key]:
                yield (key, val)

    def encode_pair(self, key, value):
        return key.encode('utf8'), value.encode('utf8')

    def encode_params(self, params):
        return '&'.join('%s=%s' % self.encode_pair(*pair) for pair in params)

    def get_signature(self, path, params, call_params):
        data = self.encode_params(sorted(params))
        call_data = self.encode_params(call_params)
        data = '%s%s?%s&%s' % (self.client_secret, path, data, call_data)
        return hashlib.sha1(data).hexdigest()

########NEW FILE########
__FILENAME__ = smugmug
import flask
import foauth.providers


class SmugMug(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'http://smugmug.com/'
    docs_url = 'http://wiki.smugmug.net/display/API/API+1.3.0'
    category = 'Pictures'

    # URLs to interact with the API
    request_token_url = 'http://api.smugmug.com/services/oauth/getRequestToken.mg'
    authorize_url = 'http://api.smugmug.com/services/oauth/authorize.mg?Access=Full&Permissions=Modify'
    access_token_url = 'http://api.smugmug.com/services/oauth/getAccessToken.mg'
    api_domain = 'api.smugmug.com'

    available_permissions = [
        (None, 'read and write your photos'),
    ]

    def get_user_id(self, key):
        url = u'/services/api/json/1.3.0/?method=smugmug.auth.checkAccessToken'
        r = self.api(key, self.api_domain, url)
        return unicode(r.json()[u'Auth'][u'User'][u'id'])

########NEW FILE########
__FILENAME__ = soundcloud
from oauthlib.common import add_params_to_uri
import foauth.providers


class SoundCloud(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'http://soundcloud.com'
    docs_url = 'http://developers.soundcloud.com/docs/api/reference'
    category = 'Music'

    # URLs to interact with the API
    authorize_url = 'https://soundcloud.com/connect'
    access_token_url = 'https://api.soundcloud.com/oauth2/token'
    api_domain = 'api.soundcloud.com'

    available_permissions = [
        (None, 'read and post sounds to the cloud'),
    ]

    def bearer_type(self, token, r):
        r.url = add_params_to_uri(r.url, [((u'oauth_token', token))])
        return r

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/me.json')
        return unicode(r.json()[u'id'])

########NEW FILE########
__FILENAME__ = stackexchange
import os
from oauthlib.common import add_params_to_uri
from werkzeug.urls import url_decode
import foauth.providers


class StackExchange(foauth.providers.OAuth2):
    # General info about the provider
    name = 'Stack Exchange'
    provider_url = 'https://stackexchange.com/'
    docs_url = 'https://api.stackexchange.com/docs'
    category = 'Support'

    # URLs to interact with the API
    authorize_url = 'https://stackexchange.com/oauth'
    access_token_url = 'https://stackexchange.com/oauth/access_token'
    api_domain = 'api.stackexchange.com'

    available_permissions = [
        (None, 'read your user information'),
        ('read_inbox', 'read your global inbox'),
    ]

    def bearer_type(service, token, r):
        params = [((u'access_token', token)), ((u'key', service.app_key))]
        r.url = add_params_to_uri(r.url, params)
        return r

    def __init__(self, *args, **kwargs):
        super(StackExchange, self).__init__(*args, **kwargs)

        # StackExchange also uses an application key
        self.app_key = os.environ.get('STACKEXCHANGE_APP_KEY', '').decode('utf8')

    def get_authorize_params(self, redirect_uri, scopes):
        # Always request a long-lasting token
        scopes.append('no_expiry')
        return super(StackExchange, self).get_authorize_params(redirect_uri, scopes)

    def parse_token(self, content):
        data = url_decode(content)
        data['expires_in'] = data.get('expires', None)
        return data

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/2.0/me/associated')
        return unicode(r.json()[u'items'][0][u'account_id'])

########NEW FILE########
__FILENAME__ = stripe
import foauth.providers
from foauth import OAuthDenied, OAuthError


class Stripe(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'https://stripe.com/'
    docs_url = 'https://stripe.com/docs/api'
    category = 'Money'

    # URLs to interact with the API
    authorize_url = 'https://connect.stripe.com/oauth/authorize'
    access_token_url = 'https://connect.stripe.com/oauth/token'
    api_domain = 'api.stripe.com'

    available_permissions = [
        (None, 'read your account and payment history'),
        ('read_write', 'read and write to your account and payments'),
    ]
    permissions_widget = 'radio'

    def get_authorize_params(self, redirect_uri, scopes):
        params = super(Stripe, self).get_authorize_params(redirect_uri, scopes)
        params['stripe_landing'] = 'login'
        return params

    def callback(self, data, *args, **kwargs):
        if data.get('error', '') == 'access_denied':
            raise OAuthDenied('Denied access to Stripe')

        return super(Stripe, self).callback(data, *args, **kwargs)

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/v1/account')
        return unicode(r.json()[u'id'])

########NEW FILE########
__FILENAME__ = taskrabbit
from oauthlib.oauth2.draft25 import utils
import foauth.providers


class Taskrabbit(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'https://www.taskrabbit.com/'
    docs_url = 'http://taskrabbit.github.com/'
    category = 'Tasks'

    # URLs to interact with the API
    # These are temporary until Taskrabbit approves foauth for production use
    authorize_url = 'https://taskrabbitdev.com/api/authorize'
    access_token_url = 'https://taskrabbitdev.com/api/oauth/token'
    api_domain = 'taskrabbitdev.com'

    available_permissions = [
        (None, 'read and write to your tasks'),
    ]

    def get_authorize_params(self, *args, **kwargs):
        params = super(Taskrabbit, self).get_authorize_params(*args, **kwargs)

        # Prevent the request for credit card information
        params['card'] = 'false'

        return params

    def bearer_type(self, token, r):
        r.headers['Authorization'] = 'OAuth %s' % token
        return r

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/api/v1/account')
        return r.json()[u'id']

########NEW FILE########
__FILENAME__ = thirtysevensignals
import foauth.providers


class ThirtySevenSignals(foauth.providers.OAuth2):
    # General info about the provider
    alias = '37signals'
    name = '37signals'
    provider_url = 'https://37signals.com/'
    docs_url = 'https://github.com/37signals/api'
    category = 'Productivity'

    # URLs to interact with the API
    authorize_url = 'https://launchpad.37signals.com/authorization/new?type=web_server'
    access_token_url = 'https://launchpad.37signals.com/authorization/token?type=web_server'
    api_domains = [
        'launchpad.37signals.com',
        'basecamp.com',
        'campfire.com',
        'highrisehq.com',
    ]

    available_permissions = [
        (None, 'access your information'),
    ]

    def get_user_id(self, key):
        r = self.api(key, self.api_domains[0], u'/authorization.json')
        return unicode(r.json()[u'identity'][u'id'])

########NEW FILE########
__FILENAME__ = trello
import foauth.providers


class Trello(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'https://trello.com/'
    docs_url = 'https://trello.com/docs/api/'
    category = 'Tasks'

    # URLs to interact with the API
    request_token_url = 'https://trello.com/1/OAuthGetRequestToken'
    authorize_url = 'https://trello.com/1/OAuthAuthorizeToken'
    access_token_url = 'https://trello.com/1/OAuthGetAccessToken'
    api_domain = 'api.trello.com'

    available_permissions = [
        (None, 'read your projects'),
        ('write', 'read and write to your projects'),
        ('account', 'manage your account'),
    ]

    def get_authorize_params(self, redirect_uri, scopes):
        params = super(Trello, self).get_authorize_params(redirect_uri, scopes)
        params.update({
            'name': 'foauth.org', 'expiration': 'never',
            'scope': self.get_scope_string(['read'] + scopes),
        })
        return params

    def get_scope_string(self, scopes):
        return ','.join(scopes)

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/1/members/me')
        return unicode(r.json()[u'id'])

########NEW FILE########
__FILENAME__ = tripit
from xml.dom import minidom

import foauth.providers


class TripIt(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'http://www.tripit.com/'
    docs_url = 'http://tripit.github.com/api/doc/v1/'
    category = 'Travel'

    # URLs to interact with the API
    request_token_url = 'https://api.tripit.com/oauth/request_token'
    authorize_url = 'https://www.tripit.com/oauth/authorize'
    access_token_url = 'https://api.tripit.com/oauth/access_token'
    api_domain = 'api.tripit.com'

    available_permissions = [
        (None, 'read, create and modify your trips'),
    ]

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/v1/get/profile')
        dom = minidom.parseString(r.content)
        return dom.getElementsByTagName('Profile')[0].getAttribute('ref')

########NEW FILE########
__FILENAME__ = tumblr
import foauth.providers


class Tumblr(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'http://www.tumblr.com/'
    docs_url = 'http://www.tumblr.com/docs/en/api/v2'
    category = 'Blogs'

    # URLs to interact with the API
    request_token_url = 'http://www.tumblr.com/oauth/request_token'
    authorize_url = 'http://www.tumblr.com/oauth/authorize'
    access_token_url = 'http://www.tumblr.com/oauth/access_token'
    api_domain = 'api.tumblr.com'

    https = False

    available_permissions = [
        (None, 'read, write and manage your blog'),
    ]

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/v2/user/info')
        return r.json()[u'response'][u'user'][u'name']

########NEW FILE########
__FILENAME__ = twentythreeandme
import foauth.providers

class TwentyThreeAndMe(foauth.providers.OAuth2):
    # General info about the provider
    alias = '23andme'
    name = '23andMe'
    provider_url = 'https://23andme.com/'
    docs_url = 'https://api.23andme.com/docs/'
    category = 'Genealogy'

    # URLs to interact with the API
    authorize_url = 'https://api.23andme.com/authorize/'
    access_token_url = 'https://api.23andme.com/token/'
    api_domain = 'api.23andme.com'

    available_permissions = [
        (None, 'anonymously tell whether each profile in your account is genotyped'),
        ('profile:read', 'read your profile information, including your picture'),
        ('profile:write', 'write to your profile information, including your picture'),
        ('names', 'read the full name of every profile in your account'),
        ('haplogroups', 'read your maternal and paternal haplogroups'),
        ('ancestry', 'access the full ancestral breakdown for all your profiles'),
        ('relatives', 'access your relatives who have also been genotyped'),
        ('relatives:write', 'add notes about and update relationships with relatives'),
        ('publish', 'publish shareable results so that anyone can read them'),
        ('analyses', 'access your analyzed genomes, including traits and health information'),
        ('genomes', 'read your entire genetic profile, raw and unanalyzed')
    ]

    def get_authorize_params(self, redirect_uri, scopes):
        scopes.append('basic')
        return super(TwentyThreeAndMe, self).get_authorize_params(redirect_uri, scopes)

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/1/user')
        return unicode(r.json()[u'id'])

########NEW FILE########
__FILENAME__ = twitch
from werkzeug.urls import url_decode
import foauth.providers


class Twitch(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'http://twitch.tv/'
    docs_url = 'https://github.com/justintv/twitch-api'
    category = 'Videos'

    # URLs to interact with the API
    authorize_url = 'https://api.twitch.tv/kraken/oauth2/authorize'
    access_token_url = 'https://api.twitch.tv/kraken/oauth2/token'
    api_domain = 'api.twitch.tv'

    available_permissions = [
        (None, 'access your user information, including email address'),
        ('user_blocks_read', 'access your list of blocked users'),
        ('user_blocks_edit', 'block and unblock users'),
        ('user_follows_edit', 'manage your followed channels'),
        ('channel_read', "read your channel's metadata"),
        ('channel_editor', "write to your channel's metadata"),
        ('channel_commercial', 'trigger commercials on a channel'),
        ('channel_stream', "reset your channel's stream key"),
        ('channel_subscriptions', 'access all subscribers to your channel'),
        ('channel_check_subscription', 'check if specific users are subscribed to your channel'),
        ('chat_login', 'send and receive chat messages'),
    ]

    def get_authorize_params(self, redirect_uri, scopes):
        scopes.append('user_read')
        return super(Twitch, self).get_authorize_params(redirect_uri, scopes)

    def bearer_type(self, token, r):
        r.headers['Authorization'] = 'OAuth %s' % token
        return r

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/kraken/user')
        return unicode(r.json()[u'_id'])

########NEW FILE########
__FILENAME__ = twitter
import foauth.providers
from foauth import OAuthDenied


class Twitter(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'https://www.twitter.com/'
    docs_url = 'https://dev.twitter.com/docs'
    category = 'Social'

    # URLs to interact with the API
    request_token_url = 'https://api.twitter.com/oauth/request_token'
    authorize_url = 'https://api.twitter.com/oauth/authorize'
    access_token_url = 'https://api.twitter.com/oauth/access_token'
    api_domains = ['api.twitter.com', 'stream.twitter.com',
                   'sitestream.twitter.com', 'userstream.twitter.com']

    available_permissions = [
        (None, 'read your tweets'),
        ('write', 'read and send tweets'),
        ('dm', 'read and send tweets, including DMs'),
    ]
    permissions_widget = 'radio'

    # Twitter's permissions model is subtractive, rather than additive. foauth
    # is registered with maximum permissions, which then have to be limited on
    # each authorization call. This mapping converts between the additive model
    # used within foauth and the subtractive model used by Twitter.
    scope_map = {
        None: 'read',
        'write': 'write',
        'dm': None
    }

    def get_request_token_params(self, redirect_uri, scopes):
        params = super(Twitter, self).get_request_token_params(redirect_uri, scopes)

        # Convert to Twitter's permissions model
        scopes = map(lambda x: self.scope_map.get(x or None), scopes)
        if any(scopes):
            params['x_auth_access_type'] = scopes[0]

        return params

    def callback(self, data, *args, **kwargs):
        if 'denied' in data:
            raise OAuthDenied('Denied access to Twitter')

        return super(Twitter, self).callback(data, *args, **kwargs)

    def get_user_id(self, key):
        r = self.api(key, self.api_domains[0], u'/1.1/account/verify_credentials.json')
        return unicode(r.json()[u'id'])

########NEW FILE########
__FILENAME__ = untappd
import json
import requests

import foauth.providers


class Untappd(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'https://untappd.com/'
    docs_url = 'https://untappd.com/api/docs'
    category = 'Food/Drink'

    # URLs to interact with the API
    authorize_url = 'https://untappd.com/oauth/authenticate/'
    access_token_url = 'https://untappd.com/oauth/authorize/'
    api_domain = 'api.untappd.com'

    available_permissions = [
        (None, 'read and write to your social drinking'),
    ]

    bearer_type = foauth.providers.BEARER_URI

    def get_authorize_params(self, redirect_uri, scopes):
        params = super(Untappd, self).get_authorize_params(redirect_uri, scopes)
        params['redirect_url'] = params.pop('redirect_uri')
        return params

    def get_access_token_response(self, redirect_uri, data):
        return requests.get(self.get_access_token_url(), params={
                                'client_id': self.client_id,
                                'client_secret': self.client_secret,
                                'response_type': 'code',
                                'code': data['code'],
                                'redirect_url': redirect_uri,
                            }, verify=self.verify, auth=self.auth)

    def parse_token(self, content):
        return json.loads(content)[u'response']

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/v4/user/info')
        return unicode(r.json()[u'response'][u'user'][u'id'])

########NEW FILE########
__FILENAME__ = uservoice
import foauth.providers


class UserVoice(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'http://uservoice.com/'
    docs_url = 'http://developer.uservoice.com/docs/api/reference/'
    category = 'Support'

    # URLs to interact with the API
    request_token_url = 'http://uservoice.com/api/v1/oauth/access_token'
    authorize_url = 'http://uservoice.com/api/v1/oauth/authorize'
    access_token_url = 'http://uservoice.com/api/v1/oauth/request_token'
    api_domain = 'uservoice.com'


########NEW FILE########
__FILENAME__ = venmo
import foauth.providers
from foauth import OAuthDenied, OAuthError


class Venmo(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'https://venmo.com/'
    docs_url = 'https://developer.venmo.com/docs/oauth'
    category = 'Money'

    # URLs to interact with the API
    authorize_url = 'https://api.venmo.com/v1/oauth/authorize'
    access_token_url = 'https://api.venmo.com/v1/oauth/access_token'
    api_domain = 'api.venmo.com'

    bearer_type = foauth.providers.BEARER_URI

    available_permissions = [
        (None, 'read your account details and current balance'),
        ('access_email', 'read your email address'),
        ('access_phone', 'read your phone number'),
        ('access_balance', 'read your current balance'),
        ('access_friends', 'access your list of friends'),
        ('access_feed', 'read your payment history and activity feed'),
    ]

    def get_authorize_params(self, redirect_uri, scopes):
        scopes = ['access_profile'] + scopes
        return super(Venmo, self).get_authorize_params(redirect_uri, scopes)

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/v1/me')
        return unicode(r.json()[u'data'][u'user'][u'id'])

########NEW FILE########
__FILENAME__ = vimeo
import foauth.providers


class Vimeo(foauth.providers.OAuth1):
    # General info about the provider
    provider_url = 'http://vimeo.com/'
    docs_url = 'http://developer.vimeo.com/apis/advanced'
    category = 'Videos'

    # URLs to interact with the API
    request_token_url = 'https://vimeo.com/oauth/request_token'
    authorize_url = 'https://vimeo.com/oauth/authorize'
    access_token_url = 'https://vimeo.com/oauth/access_token'
    api_domain = 'vimeo.com'

    available_permissions = [
        (None, 'access your videos'),
        ('write', 'access, update and like videos'),
        ('delete', 'access, update, like and delete videos'),
    ]
    permissions_widget = 'radio'

    def get_authorize_params(self, redirect_uri, scopes):
        params = super(Vimeo, self).get_authorize_params(redirect_uri, scopes)

        if any(scopes):
            params['permission'] = scopes[0]

        return params

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/api/rest/v2?method=vimeo.people.getInfo&format=json')
        return r.json()[u'person'][u'id']

########NEW FILE########
__FILENAME__ = wordpress
import foauth.providers


class Wordpress(foauth.providers.OAuth2):
    # General info about the provider
    name = 'WordPress.com'
    provider_url = 'https://www.wordpress.com/'
    docs_url = 'http://developer.wordpress.com/docs/api/'
    category = 'Blogs'

    # URLs to interact with the API
    authorize_url = 'https://public-api.wordpress.com/oauth2/authorize'
    access_token_url = 'https://public-api.wordpress.com/oauth2/token'
    api_domain = 'public-api.wordpress.com'

    available_permissions = [
        (None, 'read and post to your blog'),
    ]

    def get_user_id(self, key):
        r = self.api(key, self.api_domain, u'/rest/v1/me')
        return unicode(r.json()[u'ID'])

########NEW FILE########
__FILENAME__ = yahoo
from xml.dom import minidom

import foauth.providers


class Yahoo(foauth.providers.OAuth1):
    # General info about the provider
    name = 'Yahoo!'
    provider_url = 'http://www.yahoo.com/'
    docs_url = 'http://developer.yahoo.com/everything.html'
    category = 'Productivity'

    # URLs to interact with the API
    request_token_url = 'https://api.login.yahoo.com/oauth/v2/get_request_token'
    authorize_url = 'https://api.login.yahoo.com/oauth/v2/request_auth'
    access_token_url = 'https://api.login.yahoo.com/oauth/v2/get_token'
    api_domains = [
        'social.yahooapis.com',
        'answers.yahooapis.com',
        'messenger.yahooapis.com',
        'query.yahooapis.com',
        'mail.yahooapis.com',
    ]

    available_permissions = [
        (None, 'access your Yahoo! Answers private data and post content'),
        (None, 'read, write, and delete all aspects of your mail information'),
        (None, 'manage IM contacts, fetch user presence and send/receive instant messages'),
        (None, 'read and write to your contacts'),
        (None, 'read and write your profile information that is marked as public, shared with connections or private'),
        (None, 'read and write your information about social relationships to people and things'),
        (None, 'read and write your status message'),
        (None, 'read, write and delete updates information from your updates stream'),
    ]

    https = False

    def get_user_id(self, key):
        r = self.api(key, self.api_domains[0], u'/v1/me/guid')
        dom = minidom.parseString(r.content)
        return dom.getElementsByTagName('value')[0].firstChild.nodeValue

########NEW FILE########
__FILENAME__ = yammer
import foauth.providers


class Yammer(foauth.providers.OAuth2):
    # General info about the provider
    provider_url = 'https://www.yammer.com/'
    docs_url = 'https://developer.yammer.com/api/'
    category = 'Social'

    # URLs to interact with the API
    authorize_url = 'https://www.yammer.com/dialog/oauth'
    access_token_url = 'https://www.yammer.com/oauth2/access_token.json'
    api_domain = 'www.yammer.com'

    available_permissions = [
        (None, 'read and post to your stream'),
    ]

    def parse_token(self, content):
        data = super(Yammer, self).parse_token(content)
        data['access_token'] = data['access_token']['token']
        return data

########NEW FILE########
__FILENAME__ = providers
import unittest
import foauth.providers
import urllib


class ProviderTests(unittest.TestCase):
    def setUp(self):
        class Example(foauth.providers.OAuth):
            provider_url = 'http://example.com'
            api_domain = 'api.example.com'

        self.provider = Example

    def test_auto_name(self):
        self.assertEqual(self.provider.name, 'Example')

    def test_auto_alias(self):
        self.assertEqual(self.provider.alias, 'example')

    def test_auto_favicon_url(self):
        primary = 'https://getfavicon.appspot.com/http://example.com'
        backup = 'https://www.google.com/s2/favicons?domain=example.com'
        url = '%s?defaulticon=%s' % (primary, urllib.quote(backup))
        self.assertEqual(self.provider.favicon_url, url)

    def test_auto_api_domains(self):
        self.assertEqual(self.provider.api_domains, ['api.example.com'])

########NEW FILE########
__FILENAME__ = web
import datetime
from functools import wraps
import os
import sys

from flask import request, flash, redirect, render_template, abort, url_for, make_response
from flask.ext.login import current_user, login_user, logout_user, login_required
import static
from werkzeug.wsgi import DispatcherMiddleware

from foauth import OAuthDenied, OAuthError
import config
import forms
import models

HOST_HEADERS = [
    'Authorization',
    'Host',
    'X-Forwarded-For',
    'X-Forwarded-Port',
    'X-Forwarded-Proto',
    'X-Forwarded-Protocol',
    'X-Heroku-Dynos-In-Use',
    'X-Heroku-Queue-Depth',
    'X-Heroku-Queue-Wait-Time',
    'X-Real-Ip',
    'X-Request-Start',
    'X-Varnish',
]


@config.app.errorhandler(403)
def forbidden(e):
    return make_response(render_template('403.html'), 403)


@config.app.route('/', methods=['GET'])
def index():
    return render_template('index.html', form=forms.Signup(),
                           services=sorted(config.services,
                                           key=lambda x: x.name.lower()))


@config.app.route('/about/', methods=['GET'])
def about():
    return render_template('about.html')


@config.app.route('/security/', methods=['GET'])
def security():
    requirements = open(os.path.join(os.path.dirname(__file__), 'requirements.txt'))
    return render_template('security.html', py_version=sys.version_info,
                           requirements=sorted((r.split('==') for r in requirements),
                                               key=lambda x: x[0].lower()))


@config.app.route('/privacy/', methods=['GET'])
def privacy():
    return render_template('privacy.html')


@config.app.route('/about/faq/', methods=['GET'])
def faq():
    return render_template('faq.html')


@config.app.route('/about/terms/', methods=['GET'])
def terms():
    return render_template('terms.html')


@config.app.route('/login/', methods=['GET'])
def login():
    if current_user.is_authenticated():
        return redirect(url_for('services'))

    return render_template('login.html', form=forms.Login())


@config.app.route('/login/', methods=['POST'])
def login_post():
    form = forms.Login(request.form)
    if form.validate():
        user = models.User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for('services'))
        else:
            flash('Incorrect login', 'error')
            return redirect(url_for('login'))
    else:
        return render_template('login.html', form=form)


@config.app.route('/logout/', methods=['GET'])
def logout():
    logout_user()
    return redirect(url_for('index'))


@config.app.route('/signup/', methods=['POST'])
def signup():
    form = forms.Signup(request.form)
    if form.validate():
        user = models.User(email=form.email.data, password=form.password.data)
        models.db.session.add(user)
        models.db.session.commit()
        login_user(user)
        return redirect(url_for('services'))
    else:
        return render_template('index.html', form=form)


@config.app.route('/password/', methods=['GET'])
def password():
    return render_template('password.html', form=forms.Password())


@config.app.route('/password/', methods=['POST'])
@login_required
def password_post():
    form = forms.Password(request.form)
    if form.validate():
        current_user.set_password(form.data['password'])

        # Expire all stored keys, so this can't be used as an attack vector
        for key in current_user.keys:
            key.access_token = ''
            key.refresh_token = ''
            key.secret = ''
            key.service_user_id = ''
            key.expires = datetime.datetime.now()

        models.db.session.add(current_user)
        models.db.session.commit()
        return redirect(url_for('services'))
    else:
        return render_template('password.html', form=form)


@config.app.route('/services/', methods=['GET'])
def services():
    services = sorted((s.alias, s) for s in config.services)
    return render_template('services.html', services=config.services)


def auth_endpoint(func):
    @wraps(func)
    def wrapper(alias, *args, **kwargs):
        try:
            service = config.alias_map[alias]
        except KeyError:
            abort(404)
        return func(service, *args, **kwargs)
    return wrapper


@config.app.route('/oauth_login/', methods=['GET'])
def oauth_login():
    services = sorted((s.alias, s) for s in config.services)
    return render_template('service_login.html', services=services)


@config.app.route('/services/<alias>/login', methods=['GET'])
@auth_endpoint
def service_login(service):
    try:
        redirect_uri = url_for('login_callback', alias=service.alias, _external=True)
        url = service.get_authorize_url(redirect_uri.decode('utf8'), scopes=[])
        return redirect(url)
    except OAuthError:
        flash('Error occured while authorizing %s' % service.name, 'error')
        return redirect(url_for('oauth_login'))


@config.app.route('/services/<alias>/authorize', methods=['POST'])
@login_required
@auth_endpoint
def authorize(service):
    scopes = request.form.getlist('scope')
    try:
        redirect_uri = url_for('callback', alias=service.alias, _external=True)
        url = service.get_authorize_url(redirect_uri.decode('utf8'), scopes)
        return redirect(url)
    except OAuthError:
        flash('Error occured while authorizing %s' % service.name, 'error')
        return redirect(url_for('services'))


@config.app.route('/services/<alias>/callback', methods=['GET'])
@login_required
@auth_endpoint
def callback(service):
    user_key = models.Key.query.filter_by(user_id=current_user.id,
                                          service_alias=service.alias).first()
    try:
        redirect_uri = url_for('callback', alias=service.alias, _external=True)
        data = service.callback(request.args, redirect_uri.decode('utf8'))
        if not user_key:
            user_key = models.Key(user_id=current_user.id,
                                  service_alias=service.alias)
        user_key.update(data)
        if 'service_user_id' not in data:
            user_key.service_user_id = service.get_user_id(user_key)
        models.db.session.add(user_key)
        flash('Granted access to %s' % service.name, 'success')

    except OAuthError:
        flash('Error occurred while authorizing %s' % service.name, 'error')

    except OAuthDenied, e:
        # User denied the authorization request
        if user_key:
            models.db.session.delete(user_key)
        flash(e.args[0], 'error')

    models.db.session.commit()
    return redirect(url_for('services'))


@config.app.route('/services/<alias>/callback/login', methods=['GET'])
@auth_endpoint
def login_callback(service):
    try:
        redirect_uri = url_for('login_callback', alias=service.alias, _external=True)
        data = service.callback(request.args, redirect_uri.decode('utf8'))
    except OAuthError:
        flash('Error occurred while authorizing %s' % service.name, 'error')
        return redirect(url_for('oauth_login'))

    except OAuthDenied, e:
        # User denied the authorization request
        flash(e.args[0], 'error')
        return redirect(url_for('oauth_login'))

    key = models.Key()
    key.update(data)
    user_id = service.get_user_id(key)
    user_key = models.Key.query.filter_by(service_alias=service.alias,
                                          service_user_id=user_id).first()
    if user_key:
        login_user(user_key.user)
        return redirect(url_for('password'))
    else:
        flash('Unable to log in using %s' % service.name, 'error')
        return redirect(url_for('oauth_login'))


@config.app.route('/<domain>/<path:path>', methods=['OPTIONS', 'GET', 'PUT', 'POST', 'PATCH', 'DELETE'])
@config.app.route('/<domain>/', defaults={'path': u''}, methods=['OPTIONS', 'GET', 'PUT', 'POST', 'PATCH', 'DELETE'])
def api(domain, path):
    # Allow clients to override the method being provided, in case the client
    # or network doesn't natively support PATCH. For example, Amazon discards
    # PATCH requests before they ever reach Heroku, much less foauth.org.
    if request.method == 'POST':
        override = request.headers.get('X-Http-Method-Override')
        if override == 'PATCH':
            request.environ['REQUEST_METHOD'] = override

    auth = request.authorization
    if auth:
        user = models.User.query.filter_by(email=auth.username).first()
        if user and user.check_password(auth.password):
            try:
                service = config.domain_map[domain]
            except KeyError:
                abort(404)

            key = get_user_key(service, user)
            resp = service.api(key, domain, '/%s' % path, request.method,
                               request.args, request.form or request.data,
                               prepare_headers(request.headers))
            content = resp.raw.read() or resp.content

            if 'Transfer-Encoding' in resp.headers and \
               resp.headers['Transfer-Encoding'].lower() == 'chunked':
                # WSGI doesn't handle chunked encodings
                del resp.headers['Transfer-Encoding']
            if 'Connection' in resp.headers and \
               resp.headers['Connection'].lower() == 'keep-alive':
                # WSGI doesn't handle keep-alive
                del resp.headers['Connection']

            return config.app.make_response((content,
                                             resp.status_code,
                                             resp.headers))
    abort(403)


def prepare_headers(headers):
    # Make sure we have a mutable dictionary
    headers = dict(headers)

    # These are specific to the host environment and shouldn't be forwarded
    for header in HOST_HEADERS:
        if header in headers:
            del headers[header]

    # These are invalid if using the empty defaults
    if 'Content-Length' in headers and headers['Content-Length'] == '':
        del headers['Content-Length']
    if 'Content-Type' in headers and headers['Content-Type'] == '':
        del headers['Content-Type']

    return headers


def get_user_key(service, user):
    key = user.keys.filter_by(service_alias=service.alias).first()
    if not key:
        abort(403)
    if key.is_expired():
        # Key has expired
        if key.refresh_token:
            data = service.refresh_token(key.refresh_token)
            key.update(data)
            models.db.session.add(key)
            models.db.session.commit()
        else:
            # Unable to refresh the token
            abort(403)
    return key


blog = static.Cling('blog/output')
app = DispatcherMiddleware(config.app, {
    '/blog': blog,
})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

########NEW FILE########
