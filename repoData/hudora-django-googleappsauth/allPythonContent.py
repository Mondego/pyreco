__FILENAME__ = backends
#!/usr/bin/env python
# encoding: utf-8
"""
googleauth/backends.py - Django authentication backend connecting to Google Apps

Created by Axel Schlüter on 2009-12
Copyright (c) 2009 HUDORA GmbH. All rights reserved.
"""

from datetime import datetime
from django.conf import settings
from django.contrib.admin.models import LogEntry, ADDITION
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User, SiteProfileNotAvailable
from django.contrib.contenttypes.models import ContentType
from django.db import models
import re


class GoogleAuthBackend(ModelBackend):
    def authenticate(self, identifier=None, attributes=None):
        # da wir von Google keinen Benutzernamen bekommen versuchen wir zuerst, 
        # den ersten Teil der Emailadresse zu nehmen. Wenn wir keine Email haben 
        # dann bleibt nur der OpenID-Identifier als Benutzername
        email = attributes.get('email', '')
        username = attributes.get('email', identifier).split('@')[0].replace('.', '')
        users = User.objects.filter(username=username)
        if len(users) > 1:
            raise RuntimeError("duplicate user %s" % email)
        elif len(users) < 1:
            # for some reason it seems this code branch is never executed ?!?
            user = User.objects.create(email=email, username=username)
            # fuer einen neuen Benutzer erzeugen wir hier ein Zufallspasswort,
            # sodass er sich nicht mehr anders als ueber Google Apps einloggen kann
            user.set_unusable_password()
            # note creation in log
            LogEntry.objects.log_action(1, ContentType.objects.get_for_model(User).id,
                                    user.id, unicode(User),
                                    ADDITION, "durch googleauth automatisch erzeugt")
        else:
            user = users[0]
        # jetzt aktualisieren wir die Attribute des Benutzers mit den neuesten 
        # Werten von Google, falls sich da was geaendert haben sollte
        user.first_name = attributes.get('firstname')
        user.last_name = attributes.get('lastname')
        user.username = username
        user.is_staff = True
        if not user.password:
            user.set_unusable_password()
            
        user.save()
        
        # schliesslich speichern wir das Access Token des Benutzers in seinem
        # User Profile.
        try:
            profile = self._get_or_create_user_profile(user)
            profile.language = attributes.get('language')
            profile.access_token = attributes.get('access_token', '')
            profile.save()
        except SiteProfileNotAvailable:
            pass
        
        # das war's, Benutzer zurueckliefern, damit ist Login geglueckt
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def _get_or_create_user_profile(self, user):
        profile_module = getattr(settings, 'AUTH_PROFILE_MODULE', False)
        if not profile_module:
            raise SiteProfileNotAvailable
        app_label, model_name = profile_module.split('.')
        model = models.get_model(app_label, model_name)
        try: 
            return user.get_profile()
        except model.DoesNotExist:
            profile = model()
            profile.user = user
            return profile

########NEW FILE########
__FILENAME__ = middleware
#!/usr/bin/env python
# encoding: utf-8
"""
googleauth/middleware.py - force Google Apps Authentication for the whole site.

Created by Axel Schlüter on 2009-12
Copyright (c) 2009, 2010 HUDORA GmbH. All rights reserved.
"""

from django.conf import settings
from django.contrib.auth.models import User, SiteProfileNotAvailable
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
import django.contrib.auth as djauth
import googleappsauth.views


class GoogleAuthMiddleware(object):
    """Force Google Apps Authentication for the whole site.
    
    Using settings.AUTH_PROTECTED_AREAS you can restrict authentication 
    o only parts of a site.
    """
    
    def process_request(self, request):
        # zuerst ueberpruefen wir, ob wir fuer die aktuelle URL 
        # ueberhaupt einen gueltigen User einloggen muessen
        path = request.get_full_path()
        areas = getattr(settings, 'AUTH_PROTECTED_AREAS', [])
        # LEGACY: AUTH_PROTECTED_AREAS = "foo+bar" - to removed in Version 2.9
        if hasattr(areas, 'split'):
            areas = areas.split('+')
        matches = [area for area in areas if path.startswith(area)]
        if len(matches) == 0:
            return
        
        # Don't force authentication for excluded areas - allow sub-folders without auth
        excludes = getattr(settings, 'AUTH_EXCLUDED_AREAS', [])
        if hasattr(excludes, 'split'):
            excludes = excludes.split('+')
        exclude_matches = [exclude for exclude in excludes if path.startswith(exclude)]
        if len(exclude_matches) != 0:
            return

        # Dont force authentication for the callback URL since it would
        # result in a loop
        callback_url = request.build_absolute_uri(reverse(googleappsauth.views.callback))
        callback_path = reverse(googleappsauth.views.callback)
        if path.startswith(callback_path):
            return

        # ok, die Seite muss auth'd werden. Haben wir vielleicht
        # schon einen geauth'd User in der aktuellen Session? 
        if request.user.is_authenticated():
            return
        
        # nein, wir haben noch keinen User. Also den Login ueber
        # Google Apps OpenID/OAuth starten und Parameter in Session speichern
        return googleappsauth.views.login(request,
            redirect_url="%s?%s" % (path, request.META.get('QUERY_STRING', '')))

########NEW FILE########
__FILENAME__ = oauth
#!/usr/bin/env python
# encoding: utf-8
"""
googleauth/oauth.py - 

Created by Axel Schlüter on 2009-12

code is part of django-twitter-oauth and was taken from http://github.com/henriklied/django-twitter-oauth#.
It  was by Henrik Lied and is based on a snippet based on  Simon Willison's Fire Eagle views found at 
http://www.djangosnippets.org/snippets/655/
"""


import cgi
import urllib
import time
import random
import urlparse
import hmac
import binascii

VERSION = '1.0'
HTTP_METHOD = 'GET'
SIGNATURE_METHOD = 'PLAINTEXT'


class OAuthError(RuntimeError):
    """Generic exception class."""

    def __init__(self, message='OAuth error occured.'):
        self.message = message


def build_authenticate_header(realm=''):
    """optional WWW-Authenticate header (401 error)."""
    return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}


def escape(s):
    """url escape."""
    # escape '/' too
    return urllib.quote(s, safe='~')


def generate_timestamp():
    """util function: current timestamp

    seconds since epoch (UTC)"""
    return int(time.time())


def generate_nonce(length=8):
    """util function: nonce
    pseudorandom number"""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


class OAuthConsumer(object):
    """ OAuthConsumer is a data type that represents the identity of the Consumer
    via its shared secret with the Service Provider."""
    key = None
    secret = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret


class OAuthToken(object):
    """ OAuthToken is a data type that represents an End User via either an access
    or request token."""
    # access tokens and request tokens
    key = None
    secret = None

    '''
    key = the token
    secret = the token secret
    '''

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

    def to_string(self):
        return urllib.urlencode({'oauth_token': self.key, 'oauth_token_secret': self.secret})

    # return a token from something like:
    # oauth_token_secret=digg&oauth_token=digg
    def from_string(s):
        params = cgi.parse_qs(s, keep_blank_values=False)
        key = params['oauth_token'][0]
        secret = params['oauth_token_secret'][0]
        return OAuthToken(key, secret)
    from_string = staticmethod(from_string)

    def __str__(self):
        return self.to_string()


class OAuthRequest(object):
    '''
    OAuthRequest represents the request and can be serialized
    OAuth parameters:
        - oauth_consumer_key 
        - oauth_token
        - oauth_signature_method
        - oauth_signature 
        - oauth_timestamp 
        - oauth_nonce
        - oauth_version
        ... any additional parameters, as defined by the Service Provider.
    '''
    parameters = None # oauth parameters
    http_method = HTTP_METHOD
    http_url = None
    version = VERSION

    def __init__(self, http_method=HTTP_METHOD, http_url=None, parameters=None):
        self.http_method = http_method
        self.http_url = http_url
        self.parameters = parameters or {}

    def set_parameter(self, parameter, value):
        self.parameters[parameter] = value

    def get_parameter(self, parameter):
        try:
            return self.parameters[parameter]
        except:
            raise OAuthError('Parameter not found: %s' % parameter)

    def _get_timestamp_nonce(self):
        return self.get_parameter('oauth_timestamp'), self.get_parameter('oauth_nonce')

    # get any non-oauth parameters
    def get_nonoauth_parameters(self):
        parameters = {}
        for k, v in self.parameters.iteritems():
            # ignore oauth parameters
            if k.find('oauth_') < 0:
                parameters[k] = v
        return parameters

    # serialize as a header for an HTTPAuth request
    def to_header(self, realm=''):
        auth_header = 'OAuth realm="%s"' % realm
        # add the oauth parameters
        if self.parameters:
            for k, v in self.parameters.iteritems():
                if k[:6] == 'oauth_':
                    auth_header += ', %s="%s"' % (k, escape(str(v)))
        return {'Authorization': auth_header}

    # serialize as post data for a POST request
    def to_postdata(self):
        return '&'.join(['%s=%s' % (escape(str(k)), escape(str(v))) for k, v in self.parameters.iteritems()])

    # serialize as a url for a GET request
    def to_url(self):
        return '%s?%s' % (self.get_normalized_http_url(), self.to_postdata())

    # return a string that consists of all the parameters that need to be signed
    def get_normalized_parameters(self):
        params = self.parameters
        try:
            # exclude the signature if it exists
            del params['oauth_signature']
        except:
            pass
        key_values = sorted(params.items())
        # sort lexicographically, first after key, then after value
        return '&'.join(['%s=%s' % (escape(str(k)), escape(str(v))) for k, v in key_values])

    # just uppercases the http method
    def get_normalized_http_method(self):
        return self.http_method.upper()

    # parses the url and rebuilds it to be scheme://host/path
    def get_normalized_http_url(self):
        parts = urlparse.urlparse(self.http_url)
        url_string = '%s://%s%s' % (parts[0], parts[1], parts[2]) # scheme, netloc, path
        return url_string
        
    # set the signature parameter to the result of build_signature
    def sign_request(self, signature_method, consumer, token):
        # set the signature method
        self.set_parameter('oauth_signature_method', signature_method.get_name())
        # set the signature
        self.set_parameter('oauth_signature', self.build_signature(signature_method, consumer, token))

    def build_signature(self, signature_method, consumer, token):
        # call the build signature method within the signature method
        return signature_method.build_signature(self, consumer, token)

    def from_request(http_method, http_url, headers=None, parameters=None, query_string=None):
        # combine multiple parameter sources
        if parameters is None:
            parameters = {}

        # headers
        if headers and 'Authorization' in headers:
            auth_header = headers['Authorization']
            # check that the authorization header is OAuth
            if auth_header.index('OAuth') > -1:
                try:
                    # get the parameters from the header
                    header_params = OAuthRequest._split_header(auth_header)
                    parameters.update(header_params)
                except:
                    raise OAuthError('Unable to parse OAuth parameters from Authorization header.')

        # GET or POST query string
        if query_string:
            query_params = OAuthRequest._split_url_string(query_string)
            parameters.update(query_params)

        # URL parameters
        param_str = urlparse.urlparse(http_url)[4] # query
        url_params = OAuthRequest._split_url_string(param_str)
        parameters.update(url_params)

        if parameters:
            return OAuthRequest(http_method, http_url, parameters)

        return None
    from_request = staticmethod(from_request)

    def from_consumer_and_token(oauth_consumer, token=None, http_method=HTTP_METHOD, http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        defaults = {
            'oauth_consumer_key': oauth_consumer.key,
            'oauth_timestamp': generate_timestamp(),
            'oauth_nonce': generate_nonce(),
            'oauth_version': OAuthRequest.version,
        }

        defaults.update(parameters)
        parameters = defaults

        if token:
            parameters['oauth_token'] = token.key

        return OAuthRequest(http_method, http_url, parameters)
    from_consumer_and_token = staticmethod(from_consumer_and_token)

    def from_token_and_callback(token, callback=None, http_method=HTTP_METHOD, http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        parameters['oauth_token'] = token.key

        if callback:
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_token_and_callback = staticmethod(from_token_and_callback)

    # util function: turn Authorization: header into parameters, has to do some unescaping
    def _split_header(header):
        params = {}
        parts = header.split(',')
        for param in parts:
            # ignore realm parameter
            if param.find('OAuth realm') > -1:
                continue
            # remove whitespace
            param = param.strip()
            # split key-value
            param_parts = param.split('=', 1)
            # remove quotes and unescape the value
            params[param_parts[0]] = urllib.unquote(param_parts[1].strip('\"'))
        return params
    _split_header = staticmethod(_split_header)
    
    # util function: turn url string into parameters, has to do some unescaping
    def _split_url_string(param_str):
        parameters = cgi.parse_qs(param_str, keep_blank_values=False)
        for k, v in parameters.iteritems():
            parameters[k] = urllib.unquote(v[0])
        return parameters
    _split_url_string = staticmethod(_split_url_string)


class OAuthServer(object):
    """OAuthServer is a worker to check a requests validity against a data store"""
    timestamp_threshold = 300 # in seconds, five minutes
    version = VERSION
    signature_methods = None
    data_store = None

    def __init__(self, data_store=None, signature_methods=None):
        self.data_store = data_store
        self.signature_methods = signature_methods or {}

    def set_data_store(self, oauth_data_store):
        self.data_store = data_store

    def get_data_store(self):
        return self.data_store

    def add_signature_method(self, signature_method):
        self.signature_methods[signature_method.get_name()] = signature_method
        return self.signature_methods

    # process a request_token request
    # returns the request token on success
    def fetch_request_token(self, oauth_request):
        try:
            # get the request token for authorization
            token = self._get_token(oauth_request, 'request')
        except OAuthError:
            # no token required for the initial token request
            version = self._get_version(oauth_request)
            consumer = self._get_consumer(oauth_request)
            self._check_signature(oauth_request, consumer, None)
            # fetch a new token
            token = self.data_store.fetch_request_token(consumer)
        return token

    # process an access_token request
    # returns the access token on success
    def fetch_access_token(self, oauth_request):
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        # get the request token
        token = self._get_token(oauth_request, 'request')
        self._check_signature(oauth_request, consumer, token)
        new_token = self.data_store.fetch_access_token(consumer, token)
        return new_token

    # verify an api call, checks all the parameters
    def verify_request(self, oauth_request):
        # -> consumer and token
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        # get the access token
        token = self._get_token(oauth_request, 'access')
        self._check_signature(oauth_request, consumer, token)
        parameters = oauth_request.get_nonoauth_parameters()
        return consumer, token, parameters

    # authorize a request token
    def authorize_token(self, token, user):
        return self.data_store.authorize_request_token(token, user)
    
    # get the callback url
    def get_callback(self, oauth_request):
        return oauth_request.get_parameter('oauth_callback')

    # optional support for the authenticate header   
    def build_authenticate_header(self, realm=''):
        return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

    # verify the correct version request for this server
    def _get_version(self, oauth_request):
        try:
            version = oauth_request.get_parameter('oauth_version')
        except:
            version = VERSION
        if version and version != self.version:
            raise OAuthError('OAuth version %s not supported.' % str(version))
        return version

    # figure out the signature with some defaults
    def _get_signature_method(self, oauth_request):
        try:
            signature_method = oauth_request.get_parameter('oauth_signature_method')
        except:
            signature_method = SIGNATURE_METHOD
        try:
            # get the signature method object
            signature_method = self.signature_methods[signature_method]
        except:
            signature_method_names = ', '.join(self.signature_methods.keys())
            raise OAuthError('Signature method %s not supported try one of the following: %s' % (signature_method, signature_method_names))

        return signature_method

    def _get_consumer(self, oauth_request):
        consumer_key = oauth_request.get_parameter('oauth_consumer_key')
        if not consumer_key:
            raise OAuthError('Invalid consumer key.')
        consumer = self.data_store.lookup_consumer(consumer_key)
        if not consumer:
            raise OAuthError('Invalid consumer.')
        return consumer

    # try to find the token for the provided request token key
    def _get_token(self, oauth_request, token_type='access'):
        token_field = oauth_request.get_parameter('oauth_token')
        token = self.data_store.lookup_token(token_type, token_field)
        if not token:
            raise OAuthError('Invalid %s token: %s' % (token_type, token_field))
        return token

    def _check_signature(self, oauth_request, consumer, token):
        timestamp, nonce = oauth_request._get_timestamp_nonce()
        self._check_timestamp(timestamp)
        self._check_nonce(consumer, token, nonce)
        signature_method = self._get_signature_method(oauth_request)
        try:
            signature = oauth_request.get_parameter('oauth_signature')
        except:
            raise OAuthError('Missing signature.')
        # validate the signature
        valid_sig = signature_method.check_signature(oauth_request, consumer, token, signature)
        if not valid_sig:
            key, base = signature_method.build_signature_base_string(oauth_request, consumer, token)
            raise OAuthError('Invalid signature. Expected signature base string: %s' % base)
        built = signature_method.build_signature(oauth_request, consumer, token)

    def _check_timestamp(self, timestamp):
        # verify that timestamp is recentish
        timestamp = int(timestamp)
        now = int(time.time())
        lapsed = now - timestamp
        if lapsed > self.timestamp_threshold:
            raise OAuthError('Expired timestamp: given %d and now %s has a greater difference than threshold %d' % (timestamp, now, self.timestamp_threshold))

    def _check_nonce(self, consumer, token, nonce):
        # verify that the nonce is uniqueish
        nonce = self.data_store.lookup_nonce(consumer, token, nonce)
        if nonce:
            raise OAuthError('Nonce already used: %s' % str(nonce))


class OAuthClient(object):
    """OAuthClient is a worker to attempt to execute a request."""
    consumer = None
    token = None

    def __init__(self, oauth_consumer, oauth_token):
        self.consumer = oauth_consumer
        self.token = oauth_token

    def get_consumer(self):
        return self.consumer

    def get_token(self):
        return self.token

    def fetch_request_token(self, oauth_request):
        # -> OAuthToken
        raise NotImplementedError

    def fetch_access_token(self, oauth_request):
        # -> OAuthToken
        raise NotImplementedError

    def access_resource(self, oauth_request):
        # -> some protected resource
        raise NotImplementedError


class OAuthDataStore(object):
    """OAuthDataStore is a database abstraction used to lookup consumers and tokens"""

    def lookup_consumer(self, key):
        # -> OAuthConsumer
        raise NotImplementedError

    def lookup_token(self, oauth_consumer, token_type, token_token):
        # -> OAuthToken
        raise NotImplementedError

    def lookup_nonce(self, oauth_consumer, oauth_token, nonce, timestamp):
        # -> OAuthToken
        raise NotImplementedError

    def fetch_request_token(self, oauth_consumer):
        # -> OAuthToken
        raise NotImplementedError

    def fetch_access_token(self, oauth_consumer, oauth_token):
        # -> OAuthToken
        raise NotImplementedError

    def authorize_request_token(self, oauth_token, user):
        # -> OAuthToken
        raise NotImplementedError


class OAuthSignatureMethod(object):
    """OAuthSignatureMethod is a strategy class that implements a signature method"""

    def get_name(self):
        # -> str
        raise NotImplementedError

    def build_signature_base_string(self, oauth_request, oauth_consumer, oauth_token):
        # -> str key, str raw
        raise NotImplementedError

    def build_signature(self, oauth_request, oauth_consumer, oauth_token):
        # -> str
        raise NotImplementedError

    def check_signature(self, oauth_request, consumer, token, signature):
        built = self.build_signature(oauth_request, consumer, token)
        return built == signature


class OAuthSignatureMethod_HMAC_SHA1(OAuthSignatureMethod):

    def get_name(self):
        return 'HMAC-SHA1'
        
    def build_signature_base_string(self, oauth_request, consumer, token):
        sig = (
            escape(oauth_request.get_normalized_http_method()),
            escape(oauth_request.get_normalized_http_url()),
            escape(oauth_request.get_normalized_parameters()),
        )

        key = '%s&' % escape(consumer.secret)
        if token:
            key += escape(token.secret)
        raw = '&'.join(sig)
        return key, raw

    def build_signature(self, oauth_request, consumer, token):
        # build the base signature string
        key, raw = self.build_signature_base_string(oauth_request, consumer, token)

        # hmac object
        try:
            import hashlib # 2.5
            hashed = hmac.new(key, raw, hashlib.sha1)
        except:
            import sha # deprecated
            hashed = hmac.new(key, raw, sha)

        # calculate the digest base 64
        return binascii.b2a_base64(hashed.digest())[:-1]


class OAuthSignatureMethod_PLAINTEXT(OAuthSignatureMethod):

    def get_name(self):
        return 'PLAINTEXT'

    def build_signature_base_string(self, oauth_request, consumer, token):
        # concatenate the consumer key and secret
        sig = escape(consumer.secret) + '&'
        if token:
            sig = sig + escape(token.secret)
        return sig

    def build_signature(self, oauth_request, consumer, token):
        return self.build_signature_base_string(oauth_request, consumer, token)

########NEW FILE########
__FILENAME__ = openid
#!/usr/bin/env python
# encoding: utf-8
"""
googleauth/tools.py - 

Created by Axel Schlüter on 2009-12
Copyright (c) 2009 HUDORA GmbH. All rights reserved.
"""

import re
import urllib


class OpenIdError(Exception):

    def __init__(self, why=None):
        Exception.__init__(self, why)
        self.why = why


def build_login_url(endpoint_url, realm, callback_url, oauth_consumer=None, oauth_scope=None):
    # zuerst ueberpruefen wir, ob die Callback Url gueltig ist
    if not endpoint_url:
        raise OpenIdError('invalid GOOGLE_OPENID_ENDPOINT %r' % endpoint_url)
    if not realm:
        raise OpenIdError('invalid GOOGLE_OPENID_REALM %r' % realm)
    if not callback_url:
        raise OpenIdError('invalid callback url %r' % callback_url)

    # 'openid.mode': 'checkid_setup' oder 'checkid_immediate'
    params = {
        # zuerst die Keys fuer die eigentliche Authentifizierung
        'openid.ns': 'http://specs.openid.net/auth/2.0',
        'openid.mode': 'checkid_setup', 
        'openid.claimed_id': 'http://specs.openid.net/auth/2.0/identifier_select',
        'openid.identity': 'http://specs.openid.net/auth/2.0/identifier_select',
        'openid.realm': realm,
        'openid.return_to': callback_url,

        # jetzt noch die Keys fuer die 'extended attributes', damit wir den
        # Realnamen und die Emailadresse des eingeloggten Benutzers bekommen
        'openid.ns.ax': 'http://openid.net/srv/ax/1.0',
        'openid.ax.mode': 'fetch_request',
        'openid.ax.required': 'firstname,lastname,language,email',
        'openid.ax.type.email': 'http://axschema.org/contact/email',
        'openid.ax.type.firstname': 'http://axschema.org/namePerson/first',
        'openid.ax.type.language': 'http://axschema.org/pref/language',
        'openid.ax.type.lastname': 'http://axschema.org/namePerson/last',
    }

    # und schliesslich noch die Keys fuer OAuth, damit wir einen 
    # Request Key bekommen, den wir dann auf Wunsch zum Access Key
    # machen koennen (notwendig fuer einen API-Zugriff auf GApps)
    if oauth_consumer and oauth_scope:
        params['openid.ns.oauth']='http://specs.openid.net/extensions/oauth/1.0'
        params['openid.oauth.consumer']=oauth_consumer
        params['openid.oauth.scope']=oauth_scope

    # jetzt bauen wir die Parameter zusammen mit der URL des OpenID-
    # Endpoints noch zu einer kompletten URL zusammen und liefern
    # diese zurueck
    urlencoded_params = urllib.urlencode(params)
    redirect_url = endpoint_url
    if endpoint_url.find('?') == -1:
        redirect_url += '?%s' % urlencoded_params
    else:
        redirect_url += '&%s' % urlencoded_params
    return redirect_url


def parse_login_response(request, callback_url=None):
    # haben wir ueberhaupt eine positive Antwort?
    args = _get_request_args(request)
    is_valid_logon = args.get('openid.mode') == 'id_res'

    # basic checks: stimmen die URLs ueberein?
    if callback_url:
        if callback_url != _lookup_key(args, 'openid.return_to'):
            is_valid_logon = None

    # wir holen uns den OpenID identifier
    identifier = _lookup_key(args, 'openid.identity')
    if identifier == None:
        identifier = _lookup_key(args, 'openid.claimed_id')

    # wenn der Login gueltig war liefern wir jetzt den 
    # OpenID-Identifier zurueck, ansonsten None
    if is_valid_logon:
        return identifier
    else:
        return None


def get_email(request):
    return _lookup_key(_get_request_args(request), 'value.email')


def get_language(request):
    return _lookup_key(_get_request_args(request), 'value.language')


def get_firstname(request):
    return _lookup_key(_get_request_args(request), 'value.firstname')


def get_lastname(request):
    return _lookup_key(_get_request_args(request), 'value.lastname')


def get_oauth_request_token(request):
    return _lookup_key(_get_request_args(request), 'request_token')


def _get_request_args(request):
    args = request.GET
    if request.method == 'POST':
        args = request.POST
    return args


def _lookup_key(args, key_pattern):
    for key, value in args.items():
        if key == key_pattern or re.search(key_pattern, key):
            if isinstance(value, list):
                return value[0]
            else:
                return value
    return None

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
# encoding: utf-8
"""
googleauth/tools.py - 

Created by Axel Schlüter on 2009-12
Copyright (c) 2009 HUDORA GmbH. All rights reserved.
"""

import oauth
import httplib
import random
from django.conf import settings


""" Google OAuth Key und Secret, wird im Backend fuer hudora.de konfiguriert """
_apps_domain = getattr(settings, 'GOOGLE_APPS_DOMAIN', None)
_consumer_key = getattr(settings, 'GOOGLE_APPS_CONSUMER_KEY', None)
_consumer_secret = getattr(settings, 'GOOGLE_APPS_CONSUMER_SECRET', None)


""" Google OAuth URLs, auf die zugegriffen werden soll """
SERVER = 'www.google.com'
REQUEST_TOKEN_URL = 'https://%s/accounts/OAuthGetRequestToken' % SERVER
AUTHORIZATION_URL = 'https://%s/accounts/OAuthAuthorizeToken' % SERVER
ACCESS_TOKEN_URL = 'https://%s/accounts/OAuthGetAccessToken' % SERVER
PROFILES_URL = 'http://%s/m8/feeds/profiles/domain/%s/full/' % (SERVER, _apps_domain)


""" die globalen Objekte zum Zugriff auf Google OAuth """
_consumer = oauth.OAuthConsumer(_consumer_key, _consumer_secret)
_connection = httplib.HTTPSConnection(SERVER)
_signature_method = oauth.OAuthSignatureMethod_HMAC_SHA1()


def fetch_response(req, conn):
    """
    helper method, fuehrt einen HTTP-Request durch und liefert die 
    vom Server gelieferte Antwort als String zurueck.
    """
    conn.request(req.http_method, req.to_url())
    resp = conn.getresponse()
    return resp.read()


def token_from_session(request, attribute_name='access_token'):
    """
    helper method, liesst das serialisierte Access Token aus der 
    Session und erzeugt wieder ein Object daraus.
    """
    token_str = request.session.get(attribute_name, None)
    if not token_str:
        return None
    return token_from_string(token_str)


def token_from_string(serialized_token):
    """
    helper method, konvertiert ein als String serialisiertes 
    Token wieder zurueck in ein Python Object 
    """
    token = oauth.OAuthToken.from_string(serialized_token)
    return token


def get_request_token(callback_url, google_scope):
    """
    OAuth call, laedt ein neuen Request-Token vom Server 
    """
    req = oauth.OAuthRequest.from_consumer_and_token(_consumer,
        http_url=REQUEST_TOKEN_URL,
        parameters={'scope': google_scope,
                    'oauth_callback': callback_url})
    req.sign_request(_signature_method, _consumer, None)
    resp = fetch_response(req, _connection)
    req_token = oauth.OAuthToken.from_string(resp)
    return req_token


def get_access_token(req_token, verifier=None):
    """
    OAuth call, laedt nach erfolgtem Auth des Users und 
    der App das eigentliche Access-Token von Google. Mit diesem
    Token koennen dann die Calls durchgefuehrt werden, fuer die 
    bei Google ein vorheriges Auth notwendig ist.
    """
    parameters={}
    if verifier:
        parameters['oauth_verifier'] = verifier

    req = oauth.OAuthRequest.from_consumer_and_token(_consumer, token=req_token,
        http_url=ACCESS_TOKEN_URL, parameters=parameters)
    req.sign_request(_signature_method, _consumer, req_token)
    resp = fetch_response(req, _connection)
    access_token = oauth.OAuthToken.from_string(resp) 
    return access_token


def build_auth_url(req_token):
    """
    OAuth call, erzeugt aus dem vorher geladenen Request-Token 
    die URL, auf die der Benutzer zu Google umgeleitet werden muss. Dort
    authorisiert der Benutzer dann zuerst sich selbst und in der Folge unsere 
    App zum Zugriff auf das API. Nach erfolgtem Auth leitet Google den Benutzer
    auf die bei Google hinterlegte URL zurueck zur App, es muss als der 
    richtige Key genutzt werden, damit der Redirect wirklich auf unseren 
    Server geht.
    """

    req = oauth.OAuthRequest.from_consumer_and_token(_consumer, token=req_token,
        http_url=AUTHORIZATION_URL,
        parameters={'hd': _apps_domain})
    req.sign_request(_signature_method, _consumer, req_token)
    auth_url = req.to_url()
    return auth_url


def get_user_profile(access_token, username):
    req = oauth.OAuthRequest.from_consumer_and_token(_consumer, token=access_token,
        http_method='GET',
        http_url=PROFILES_URL + username,
        parameters={'v': '3.0'})
    req.sign_request(_signature_method, _consumer, access_token)
    resp = fetch_response(req, _connection)
    return 'schluete'



# OpenID
# https://www.google.com/accounts/o8/site-xrds?hd=hudora.de
# user's login identifier, as openid.claimed_id
# requested user attributes, as openid.ax.value.email (if requested)
# authorized OAuth request token, as openid.ext2.request_token (if requested)

########NEW FILE########
__FILENAME__ = views
#!/usr/bin/env python
# encoding: utf-8
"""
googleappsauth/views.py - 

Created by Axel Schlüter on 2009-12
Copyright (c) 2009, 2010 HUDORA GmbH. All rights reserved.
"""

import types

from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
import django.contrib.auth as djauth
import googleappsauth.openid


_google_apps_domain = getattr(settings, 'GOOGLE_APPS_DOMAIN', None)
_google_openid_endpoint = getattr(settings, 'GOOGLE_OPENID_ENDPOINT', None)
_google_openid_realm = getattr(settings, 'GOOGLE_OPENID_REALM', None)
_oauth_consumer_key = getattr(settings, 'GOOGLE_APPS_CONSUMER_KEY', None)
_oauth_consumer_secret = getattr(settings, 'GOOGLE_APPS_CONSUMER_SECRET', None)
_google_api_scope = getattr(settings, 'GOOGLE_API_SCOPE', None)

_login_url = getattr(settings, 'LOGIN_URL', None)


def login(request, redirect_field_name=REDIRECT_FIELD_NAME, redirect_url=None):
    # wenn wir ueber einen Post-Request in die Method gekommen sind gehen 
    # wir davon aus, das der Benutzer vorher eine Domain fuer den Login 
    # ausgewaehlt hat. Ansonsten ist's ein Fehler.
    if request.method == 'POST':
        callback_url = request.session['callback_url']
        login_domain = request.POST.get('domain')
        if not login_domain:
            raise Http404('invalid or missing login domain!')

    # ansonsten ist das ein Login-Versuch, also bestimmen wir zuerst, wohin 
    # nach erfolgtem Login in die App umgeleitet werden soll
    else:
        login_domain = None
        if not redirect_url:
            redirect_url = request.REQUEST.get(redirect_field_name)
            if not redirect_url:
                redirect_url =  getattr(settings, 'LOGIN_REDIRECT_URL', '/')
        request.session['redirect_url'] = redirect_url

        # jetzt bauen wir uns die URL fuer den Callback zusammen, unter
        # dem wir von Google aufgerufen werden moechten nach dem Login
        callback_url = request.build_absolute_uri(reverse(callback))
        request.session['callback_url'] = callback_url

    # wenn wir mehr als eine Apps-Domain konfiguriert haben und noch 
    # keine Login-Domain aus dem POST-Request ausgewaehlt wurde dann
    # dann zeigen wir jetzt zuerst noch eine Auswahlbox fuer die 
    # gewuenschte Login-Domain an.
    if not login_domain:
        if type(_google_apps_domain) == types.ListType:
            return render_to_response('googleappsauth/domains.html', 
                                      { 'login_url': _login_url, 'domains': _google_apps_domain })
        else:
            login_domain = _google_apps_domain 

    # jetzt haben wir ganz sicher eine Domain, ueber die wir uns einloggen
    # sollen. Um die Kompatibilitaet mit alten Versionen (in denen der Settings-
    # Parameter 'GOOGLE_OPENID_ENDPOINT' bereits die vollstaendige Endpoint-URL 
    # inkl. Login-Domain enthalten hat) nicht zu brechen fangen wir hier moegliche 
    # Typfehler (eben wenn der Parameter kein passendes '%s' enthaelt) ab.
    openid_endpoint = _google_openid_endpoint
    try:
        openid_endpoint = openid_endpoint % login_domain
    except TypeError:
        pass

    # und schliesslich konstruieren wir darauf die Google-OpenID-
    # Endpoint-URL, auf die wir dann den Benutzer umleiten
    url = googleappsauth.openid.build_login_url(
            openid_endpoint, _google_openid_realm,
            callback_url, _oauth_consumer_key, _google_api_scope)
    return HttpResponseRedirect(url)


def callback(request):
    # haben wir einen erfolgreichen Login? Wenn nicht gehen wir
    # sofort zurueck, ohne einen Benutzer einzuloggen
    callback_url = request.session.get('callback_url', '/')
    identifier = googleappsauth.openid.parse_login_response(request, callback_url)
    if not identifier:
        # TODO: was ist hier los?
        return HttpResponseRedirect('/')
    
    # jetzt holen wir uns die restlichen Daten aus dem Login
    attributes = {
        'email': googleappsauth.openid.get_email(request),
        'language': googleappsauth.openid.get_language(request),
        'firstname': googleappsauth.openid.get_firstname(request),
        'lastname': googleappsauth.openid.get_lastname(request)}
    
    # wenn wir ein OAuth request token bekommen haben machen wir
    # daraus jetzt noch flott ein access token
    request_token = googleappsauth.openid.get_oauth_request_token(request)
    #if request_token:
    #    attributes['access_token'] = None
    #    raise Exception('access token handling not yet implemented!')
    
    # Usernames are based on E-Mail Addresses which are unique.
    username = attributes.get('email', identifier).split('@')[0].replace('.', '')
    
    # schliesslich melden wir den Benutzer mit seinen Attributen am
    # Auth-System von Django an, dann zurueck zur eigentlichen App
    user = djauth.authenticate(identifier=username, attributes=attributes)
    if not user:
        # For some reason I do not fully understand we get back a "None"" coasionalty - retry.
        user = djauth.authenticate(identifier=username, attributes=attributes)
        if not user:
            # die Authentifizierung ist gescheitert
            raise RuntimeError("Authentifizierungsproblem: %s|%s|%s" % (username, identifier, attributes))
    djauth.login(request, user)
    redirect_url = request.session['redirect_url']
    # del request.session['redirect_url']
    return HttpResponseRedirect(redirect_url)


def logout(request):
    djauth.logout(request)
    return HttpResponseRedirect('https://www.google.com/a/%s/Logout' % _google_apps_domain)

########NEW FILE########
