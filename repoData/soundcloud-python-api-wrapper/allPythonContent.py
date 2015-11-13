__FILENAME__ = bootstrap
import webbrowser
import scapi

# the host to connect to. Normally, this
# would be api.soundcloud.com
API_HOST = "api.sandbox-soundcloud.com"

# This needs to be the consumer ID you got from
# http://soundcloud.com/settings/applications/new
CONSUMER = "gLnhFeUBnBCZF8a6Ngqq7w"
# This needs to be the consumer secret password you got from
# http://soundcloud.com/settings/applications/new
CONSUMER_SECRET = "nbWRdG5X9xUb63l4nIeFYm3nmeVJ2v4s1ROpvRSBvU8"

# first, we create an OAuthAuthenticator that only knows about consumer
# credentials. This is done so that we can get an request-token as
# first step.
oauth_authenticator = scapi.authentication.OAuthAuthenticator(CONSUMER, 
                                                              CONSUMER_SECRET,
                                                              None, 
                                                              None)

# The connector works with the authenticator to create and sign the requests. It
# has some helper-methods that allow us to do the OAuth-dance.
connector = scapi.ApiConnector(host=API_HOST, authenticator=oauth_authenticator)

# First step is to get a request-token, and to let the user authorize that
# via the browser.
token, secret = connector.fetch_request_token()
authorization_url = connector.get_request_token_authorization_url(token)
webbrowser.open(authorization_url)
oauth_verifier = raw_input("please enter verifier code as seen in the browser:")

# Now we create a new authenticator with the temporary token & secret we got from
# the request-token. This will give us the access-token
oauth_authenticator = scapi.authentication.OAuthAuthenticator(CONSUMER, 
                                                              CONSUMER_SECRET,
                                                              token, 
                                                              secret)

# we need a new connector with the new authenticator!
connector = scapi.ApiConnector(API_HOST, authenticator=oauth_authenticator)
token, secret = connector.fetch_access_token(oauth_verifier)

# now we are finally ready to go - with all four parameters OAuth requires,
# we can setup an authenticator that allows for actual API-calls.
oauth_authenticator = scapi.authentication.OAuthAuthenticator(CONSUMER, 
                                                              CONSUMER_SECRET,
                                                              token, 
                                                              secret)

# we pass the connector to a Scope - a Scope is essentiall a path in the REST-url-space.
# Without any path-component, it's the root from which we can then query into the
# resources.
root = scapi.Scope(scapi.ApiConnector(host=API_HOST, authenticator=oauth_authenticator))

# Hey, nice meeting you!
print "Hello, %s" % root.me().username

########NEW FILE########
__FILENAME__ = client
'''
Example consumer.
'''
import httplib
import time
import oauth.oauth as oauth
import webbrowser
from scapi import util

SERVER = 'sandbox-soundcloud.com' # Change to soundcloud.com to reach the live site
PORT = 80

REQUEST_TOKEN_URL = 'http://api.' + SERVER + '/oauth/request_token'
ACCESS_TOKEN_URL  = 'http://api.' + SERVER + '/oauth/access_token'
AUTHORIZATION_URL = 'http://'     + SERVER + '/oauth/authorize'

CALLBACK_URL = ''
RESOURCE_URL = "http://api." + SERVER + "/me"

# key and secret granted by the service provider for this consumer application - same as the MockOAuthDataStore
CONSUMER_KEY    = 'JysXkO8ErA4EluFnF5nWg'
CONSUMER_SECRET = 'fauVjm61niGckeufkmMvgUo77oWzRHdMmeylJblHk'

# example client using httplib with headers
class SimpleOAuthClient(oauth.OAuthClient):

    def __init__(self, server, port=httplib.HTTP_PORT, request_token_url='', access_token_url='', authorization_url=''):
        self.server            = server
        self.port              = port
        self.request_token_url = request_token_url
        self.access_token_url  = access_token_url
        self.authorization_url = authorization_url
        self.connection        = httplib.HTTPConnection("%s:%d" % (self.server, self.port))

    def fetch_request_token(self, oauth_request):
        # via headers
        # -> OAuthToken
        print oauth_request.to_url()
        #self.connection.request(oauth_request.http_method, self.request_token_url, headers=oauth_request.to_header()) 
        self.connection.request(oauth_request.http_method, oauth_request.to_url()) 
        response = self.connection.getresponse()
        print "response status", response.status
        return oauth.OAuthToken.from_string(response.read())

    def fetch_access_token(self, oauth_request):
        # via headers
        # -> OAuthToken
        
        # This should proably be elsewhere but stays here for now
        oauth_request.set_parameter("oauth_signature", util.escape(oauth_request.get_parameter("oauth_signature")))
        self.connection.request(oauth_request.http_method, self.access_token_url, headers=oauth_request.to_header()) 
        response = self.connection.getresponse()
        resp = response.read()
        print "*" * 90
        print "response:", resp
        print "*" * 90

        return oauth.OAuthToken.from_string(resp)

    def authorize_token(self, oauth_request):
        webbrowser.open(oauth_request.to_url())
        raw_input("press return when authorizing is finished")

        return

        # via url
        # -> typically just some okay response
        self.connection.request(oauth_request.http_method, oauth_request.to_url()) 
        response = self.connection.getresponse()
        return response.read()

    def access_resource(self, oauth_request):
        print "resource url:", oauth_request.to_url()
        webbrowser.open(oauth_request.to_url())

        return

        # via post body
        # -> some protected resources
        self.connection.request('GET', oauth_request.to_url())
        response = self.connection.getresponse()
        return response.read()

def run_example():

    # setup
    print '** OAuth Python Library Example **'
    client = SimpleOAuthClient(SERVER, PORT, REQUEST_TOKEN_URL, ACCESS_TOKEN_URL, AUTHORIZATION_URL)
    consumer = oauth.OAuthConsumer(CONSUMER_KEY, CONSUMER_SECRET)
    signature_method_plaintext = oauth.OAuthSignatureMethod_PLAINTEXT()
    signature_method_hmac_sha1 = oauth.OAuthSignatureMethod_HMAC_SHA1()
    pause()
    # get request token
    print '* Obtain a request token ...'
    pause()
    oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, http_url=client.request_token_url)
    #oauth_request.sign_request(signature_method_plaintext, consumer, None)
    oauth_request.sign_request(signature_method_hmac_sha1, consumer, None)

    print 'REQUEST (via headers)'
    print 'parameters: %s' % str(oauth_request.parameters)
    pause()
    #import pdb; pdb.set_trace()

    token = client.fetch_request_token(oauth_request)
    print 'GOT'
    print 'key: %s' % str(token.key)
    print 'secret: %s' % str(token.secret)
    pause()

    print '* Authorize the request token ...'
    pause()
    oauth_request = oauth.OAuthRequest.from_token_and_callback(token=token, callback=CALLBACK_URL, http_url=client.authorization_url)
    print 'REQUEST (via url query string)'
    print 'parameters: %s' % str(oauth_request.parameters)
    pause()
    # this will actually occur only on some callback
    response = client.authorize_token(oauth_request)
    print 'GOT'
    print response
    pause()

    # get access token
    print '* Obtain an access token ...'
    pause()
    oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, token=token, http_url=client.access_token_url)
    oauth_request.sign_request(signature_method_hmac_sha1, consumer, token)
    print 'REQUEST (via headers)'
    print 'parameters: %s' % str(oauth_request.parameters)
    pause()
    token = client.fetch_access_token(oauth_request)
    print 'GOT'
    print 'key: %s' % str(token.key)
    print 'secret: %s' % str(token.secret)
    pause()

    # access some protected resources
    print '* Access protected resources ...'
    pause()
    parameters = {}
    oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, token=token, http_method='GET', http_url=RESOURCE_URL, parameters=parameters)
    oauth_request.sign_request(signature_method_hmac_sha1, consumer, token)
    print 'REQUEST (via get body)'
    print 'parameters: %s' % str(oauth_request.parameters)
    pause()
    params = client.access_resource(oauth_request)
    print 'GOT'
    print 'non-oauth parameters: %s' % params
    pause()

def pause():
    print ''
    time.sleep(1)

if __name__ == '__main__':
    run_example()
    print 'Done.'

########NEW FILE########
__FILENAME__ = server
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import urllib

import oauth.oauth as oauth

REQUEST_TOKEN_URL = 'https://photos.example.net/request_token'
ACCESS_TOKEN_URL = 'https://photos.example.net/access_token'
AUTHORIZATION_URL = 'https://photos.example.net/authorize'
RESOURCE_URL = 'http://photos.example.net/photos'
REALM = 'http://photos.example.net/'

# example store for one of each thing
class MockOAuthDataStore(oauth.OAuthDataStore):

    def __init__(self):
        self.consumer = oauth.OAuthConsumer('key', 'secret')
        self.request_token = oauth.OAuthToken('requestkey', 'requestsecret')
        self.access_token = oauth.OAuthToken('accesskey', 'accesssecret')
        self.nonce = 'nonce'

    def lookup_consumer(self, key):
        if key == self.consumer.key:
            return self.consumer
        return None

    def lookup_token(self, token_type, token):
        token_attrib = getattr(self, '%s_token' % token_type)
        if token == token_attrib.key:
            return token_attrib
        return None

    def lookup_nonce(self, oauth_consumer, oauth_token, nonce):
        if oauth_token and oauth_consumer.key == self.consumer.key and (oauth_token.key == self.request_token.key or token.key == self.access_token.key) and nonce == self.nonce:
            return self.nonce
        else:
            raise oauth.OAuthError('Nonce not found: %s' % str(nonce))
        return None

    def fetch_request_token(self, oauth_consumer):
        if oauth_consumer.key == self.consumer.key:
            return self.request_token
        return None

    def fetch_access_token(self, oauth_consumer, oauth_token):
        if oauth_consumer.key == self.consumer.key and oauth_token.key == self.request_token.key:
            # want to check here if token is authorized
            # for mock store, we assume it is
            return self.access_token
        return None

    def authorize_request_token(self, oauth_token):
        if oauth_token.key == self.request_token.key:
            # authorize the request token in the store
            # for mock store, do nothing
            return self.request_token
        return None

class RequestHandler(BaseHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        self.oauth_server = oauth.OAuthServer(MockOAuthDataStore())
        self.oauth_server.add_signature_method(oauth.OAuthSignatureMethod_PLAINTEXT())
        self.oauth_server.add_signature_method(oauth.OAuthSignatureMethod_HMAC_SHA1())
        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

    # example way to send an oauth error
    def send_oauth_error(self, err=None):
        # send a 401 error
        self.send_error(401, str(err.message))
        # return the authenticate header
        header = oauth.build_authenticate_header(realm=REALM)
        for k, v in header.iteritems():
            self.send_header(k, v) 

    def do_GET(self):

        # debug info
        #print self.command, self.path, self.headers
        
        # get the post data (if any)
        postdata = None
        if self.command == 'POST':
            try:
                length = int(self.headers.getheader('content-length'))
                postdata = self.rfile.read(length)
            except:
                pass

        # construct the oauth request from the request parameters
        oauth_request = oauth.OAuthRequest.from_request(self.command, self.path, headers=self.headers, postdata=postdata)

        # request token
        if self.path.startswith(REQUEST_TOKEN_URL):
            try:
                # create a request token
                token = self.oauth_server.fetch_request_token(oauth_request)
                # send okay response
                self.send_response(200, 'OK')
                self.end_headers()
                # return the token
                self.wfile.write(token.to_string())
            except oauth.OAuthError, err:
                self.send_oauth_error(err)
            return

        # user authorization
        if self.path.startswith(AUTHORIZATION_URL):
            try:
                # get the request token
                token = self.oauth_server.fetch_request_token(oauth_request)
                callback = self.oauth_server.get_callback(oauth_request)
                # send okay response
                self.send_response(200, 'OK')
                self.end_headers()
                # return the callback url (to show server has it)
                self.wfile.write('callback: %s' %callback)
                # authorize the token (kind of does nothing for now)
                token = self.oauth_server.authorize_token(token)
                self.wfile.write('\n')
                # return the token key
                token_key = urllib.urlencode({'oauth_token': token.key})
                self.wfile.write('token key: %s' % token_key)
            except oauth.OAuthError, err:
                self.send_oauth_error(err)
            return

        # access token
        if self.path.startswith(ACCESS_TOKEN_URL):
            try:
                # create an access token
                token = self.oauth_server.fetch_access_token(oauth_request)
                # send okay response
                self.send_response(200, 'OK')
                self.end_headers()
                # return the token
                self.wfile.write(token.to_string())
            except oauth.OAuthError, err:
                self.send_oauth_error(err)
            return

        # protected resources
        if self.path.startswith(RESOURCE_URL):
            try:
                # verify the request has been oauth authorized
                consumer, token, params = self.oauth_server.verify_request(oauth_request)
                # send okay response
                self.send_response(200, 'OK')
                self.end_headers()
                # return the extra parameters - just for something to return
                self.wfile.write(str(params))
            except oauth.OAuthError, err:
                self.send_oauth_error(err)
            return

    def do_POST(self):
        return self.do_GET()

def main():
    try:
        server = HTTPServer(('', 8080), RequestHandler)
        print 'Test server running...'
        server.serve_forever()
    except KeyboardInterrupt:
        server.socket.close()

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = oauth
import cgi
import urllib
import time
import random
import urlparse
import hmac
import hashlib
import base64

VERSION = '1.0' # Hi Blaine!
HTTP_METHOD = 'GET'
SIGNATURE_METHOD = 'PLAINTEXT'

# Generic exception class
class OAuthError(RuntimeError):
    def __init__(self, message='OAuth error occured'):
        self.message = message

# optional WWW-Authenticate header (401 error)
def build_authenticate_header(realm=''):
    return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

# url escape
def escape(s):
    # escape '/' too
    return urllib.quote(s, safe='')

# util function: current timestamp
# seconds since epoch (UTC)
def generate_timestamp():
    return int(time.time())

# util function: nonce
# pseudorandom number
def generate_nonce(length=8):
    return ''.join(str(random.randint(0, 9)) for i in range(length))

# OAuthConsumer is a data type that represents the identity of the Consumer
# via its shared secret with the Service Provider.
class OAuthConsumer(object):
    key = None
    secret = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

# OAuthToken is a data type that represents an End User via either an access
# or request token.     
class OAuthToken(object):
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
    @staticmethod   
    def from_string(s):
        params = cgi.parse_qs(s, keep_blank_values=False)
        key = params['oauth_token'][0]
        secret = params['oauth_token_secret'][0]
        return OAuthToken(key, secret)

    def __str__(self):
        return self.to_string()

# OAuthRequest represents the request and can be serialized
class OAuthRequest(object):
    '''
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
                auth_header += ',\n\t %s="%s"' % (k, v)
        return {'Authorization': auth_header}

    # serialize as post data for a POST request
    def to_postdata(self):
        return '&'.join('%s=%s' % (escape(str(k)), escape(str(v))) for k, v in self.parameters.iteritems())

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
        key_values = params.items()
        # sort lexicographically, first after key, then after value
        key_values.sort()
        # combine key value pairs in string and escape
        return '&'.join('%s=%s' % (str(k), str(p)) for k, p in key_values)

    # just uppercases the http method
    def get_normalized_http_method(self):
        return self.http_method.upper()

    # parses the url and rebuilds it to be scheme://host/path
    def get_normalized_http_url(self):
        parts = urlparse.urlparse(self.http_url)
        url_string = '%s://%s%s' % (parts.scheme, parts.netloc, parts.path)
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

    @staticmethod
    def from_request(http_method, http_url, headers=None, postdata=None, parameters=None):

        # let the library user override things however they'd like, if they know
        # which parameters to use then go for it, for example XMLRPC might want to
        # do this
        if parameters is not None:
            return OAuthRequest(http_method, http_url, parameters)

        # from the headers
        if headers is not None:
            try:
                auth_header = headers['Authorization']
                # check that the authorization header is OAuth
                auth_header.index('OAuth')
                # get the parameters from the header
                parameters = OAuthRequest._split_header(auth_header)
                return OAuthRequest(http_method, http_url, parameters)
            except:
                pass

        # from the parameter string (post body)
        if http_method == 'POST' and postdata is not None:
            parameters = OAuthRequest._split_url_string(postdata)

        # from the url string
        elif http_method == 'GET':
            param_str = urlparse.urlparse(http_url).query
            parameters = OAuthRequest._split_url_string(param_str)

        if parameters:
            return OAuthRequest(http_method, http_url, parameters)

        raise OAuthError('Missing all OAuth parameters. OAuth parameters must be in the headers, post body, or url.')

    @staticmethod
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

    @staticmethod
    def from_token_and_callback(token, callback=None, http_method=HTTP_METHOD, http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        parameters['oauth_token'] = token.key

        if callback:
            parameters['oauth_callback'] = escape(callback)

        return OAuthRequest(http_method, http_url, parameters)

    # util function: turn Authorization: header into parameters, has to do some unescaping
    @staticmethod
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
    
    # util function: turn url string into parameters, has to do some unescaping
    @staticmethod
    def _split_url_string(param_str):
        parameters = cgi.parse_qs(param_str, keep_blank_values=False)
        for k, v in parameters.iteritems():
            parameters[k] = urllib.unquote(v[0])
        return parameters

# OAuthServer is a worker to check a requests validity against a data store
class OAuthServer(object):
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
        except:
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
    def authorize_token(self, token):
        return self.data_store.authorize_request_token(token)
    
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
            raise OAuthError('OAuth version %s not supported' % str(version))
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
            raise OAuthError('Invalid consumer key')
        consumer = self.data_store.lookup_consumer(consumer_key)
        if not consumer:
            raise OAuthError('Invalid consumer')
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
            raise OAuthError('Missing signature')
        # attempt to construct the same signature
        built = signature_method.build_signature(oauth_request, consumer, token)
        if signature != built:
            raise OAuthError('Invalid signature')

    def _check_timestamp(self, timestamp):
        # verify that timestamp is recentish
        timestamp = int(timestamp)
        now = int(time.time())
        lapsed = now - timestamp
        if lapsed > self.timestamp_threshold:
            raise OAuthError('Expired timestamp: given %d and now %s has a greater difference than threshold %d' % (timestamp, now, self.timestamp_threshold))

    def _check_nonce(self, consumer, token, nonce):
        # verify that the nonce is uniqueish
        try:
            self.data_store.lookup_nonce(consumer, token, nonce)
            raise OAuthError('Nonce already used: %s' % str(nonce))
        except:
            pass

# OAuthClient is a worker to attempt to execute a request
class OAuthClient(object):
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

# OAuthDataStore is a database abstraction used to lookup consumers and tokens
class OAuthDataStore(object):

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

    def authorize_request_token(self, oauth_token):
        # -> OAuthToken
        raise NotImplementedError

# OAuthSignatureMethod is a strategy class that implements a signature method
class OAuthSignatureMethod(object):
    def get_name():
        # -> str
        raise NotImplementedError

    def build_signature(oauth_request, oauth_consumer, oauth_token):
        # -> str
        raise NotImplementedError

class OAuthSignatureMethod_HMAC_SHA1(OAuthSignatureMethod):

    def get_name(self):
        return 'HMAC-SHA1'

    def build_signature(self, oauth_request, consumer, token):
        sig = (
            escape(oauth_request.get_normalized_http_method()),
            escape(oauth_request.get_normalized_http_url()),
            escape(oauth_request.get_normalized_parameters()),
        )

        key = '%s&' % consumer.secret
        if token:
            key += token.secret
        raw = '&'.join(sig)

        # hmac object
        hashed = hmac.new(key, raw, hashlib.sha1)

        # calculate the digest base 64
        return base64.b64encode(hashed.digest())

class OAuthSignatureMethod_PLAINTEXT(OAuthSignatureMethod):

    def get_name(self):
        return 'PLAINTEXT'

    def build_signature(self, oauth_request, consumer, token):
        # concatenate the consumer key and secret
        sig = escape(consumer.secret)
        if token:
            sig = '&'.join((sig, escape(token.secret)))
        return sig

########NEW FILE########
__FILENAME__ = authentication
##    SouncCloudAPI implements a Python wrapper around the SoundCloud RESTful
##    API
##
##    Copyright (C) 2008  Diez B. Roggisch
##    Contact mailto:deets@soundcloud.com
##
##    This library is free software; you can redistribute it and/or
##    modify it under the terms of the GNU Lesser General Public
##    License as published by the Free Software Foundation; either
##    version 2.1 of the License, or (at your option) any later version.
##
##    This library is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
##    Lesser General Public License for more details.
##
##    You should have received a copy of the GNU Lesser General Public
##    License along with this library; if not, write to the Free Software
##    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import base64
import time, random
import urlparse
import hmac
import hashlib
from scapi.util import escape
import logging


USE_DOUBLE_ESCAPE_HACK = True
"""
There seems to be an uncertainty on the way
parameters are to be escaped. For now, this
variable switches between two escaping mechanisms.

If True, the passed parameters - GET or POST - are
escaped *twice*.
"""

logger = logging.getLogger(__name__)

class OAuthSignatureMethod_HMAC_SHA1(object):

    FORBIDDEN = ['realm', 'oauth_signature']

    def get_name(self):
        return 'HMAC-SHA1'

    def build_signature(self, request, parameters, consumer_secret, token_secret, oauth_parameters):
        if logger.level == logging.DEBUG:
            logger.debug("request: %r", request)
            logger.debug("parameters: %r", parameters)
            logger.debug("consumer_secret: %r", consumer_secret)
            logger.debug("token_secret: %r", token_secret)
            logger.debug("oauth_parameters: %r", oauth_parameters)

            
        temp = {}
        temp.update(oauth_parameters)
        for p in self.FORBIDDEN:
            if p in temp:
                del temp[p]
        if parameters is not None:
            temp.update(parameters)
        sig = (
            escape(self.get_normalized_http_method(request)),
            escape(self.get_normalized_http_url(request)),
            self.get_normalized_parameters(temp), # these are escaped in the method already
        )
        
        key = '%s&' % consumer_secret
        if token_secret is not None:
            key += token_secret
        raw = '&'.join(sig)
        logger.debug("raw basestring: %s", raw)
        logger.debug("key: %s", key)
        # hmac object
        hashed = hmac.new(key, raw, hashlib.sha1)
        # calculate the digest base 64
        signature = escape(base64.b64encode(hashed.digest()))
        return signature


    def get_normalized_http_method(self, request):
        return request.get_method().upper()


    # parses the url and rebuilds it to be scheme://host/path
    def get_normalized_http_url(self, request):
        url = request.get_full_url()
        parts = urlparse.urlparse(url)
        url_string = '%s://%s%s' % (parts.scheme, parts.netloc, parts.path)
        return url_string


    def get_normalized_parameters(self, params):
        if params is None:
            params = {}
        try:
            # exclude the signature if it exists
            del params['oauth_signature']
        except:
            pass
        key_values = []
        
        for key, values in params.iteritems():
            if isinstance(values, file):
                continue
            if isinstance(values, (int, long, float)):
                values = str(values)
            if isinstance(values, (list, tuple)):
                values = [str(v) for v in values]
            if isinstance(values, basestring):
                values = [values]
            if USE_DOUBLE_ESCAPE_HACK and not key.startswith("ouath"):
                key = escape(key)                
            for v in values:
                v = v.encode("utf-8")
                key = key.encode("utf-8")
                if USE_DOUBLE_ESCAPE_HACK and not key.startswith("oauth"):
                    # this is a dirty hack to make the
                    # thing work with the current server-side
                    # implementation. Or is it by spec? 
                    v = escape(v)
                key_values.append(escape("%s=%s" % (key, v)))
        # sort lexicographically, first after key, then after value
        key_values.sort()
        # combine key value pairs in string
        return escape('&').join(key_values)


class OAuthAuthenticator(object):
    OAUTH_API_VERSION = '1.0'
    AUTHORIZATION_HEADER = "Authorization"

    def __init__(self, consumer=None, consumer_secret=None, token=None, secret=None, signature_method=OAuthSignatureMethod_HMAC_SHA1()):
        if consumer == None:
          raise ValueError("The consumer key must be passed for all public requests; it may not be None")
        self._consumer, self._token, self._secret = consumer, token, secret
        self._consumer_secret = consumer_secret
        self._signature_method = signature_method
        random.seed()


    def augment_request(self, req, parameters, use_multipart=False, oauth_callback=None, oauth_verifier=None):
        oauth_parameters = {
            'oauth_consumer_key':     self._consumer,
            'oauth_timestamp':        self.generate_timestamp(),
            'oauth_nonce':            self.generate_nonce(),
            'oauth_version':          self.OAUTH_API_VERSION,
            'oauth_signature_method': self._signature_method.get_name(),
            #'realm' : "http://soundcloud.com",
            }
        if self._token is not None:
            oauth_parameters['oauth_token'] = self._token

        if oauth_callback is not None:
            oauth_parameters['oauth_callback'] = oauth_callback

        if oauth_verifier is not None:
            oauth_parameters['oauth_verifier'] = oauth_verifier
            
        # in case we upload large files, we don't
        # sign the request over the parameters
        # There's a bug in the OAuth 1.0 (and a) specs that says that PUT request should omit parameters from the base string.
        # This is fixed in the IETF draft, don't know when this will be released though. - HT
        if use_multipart or req.get_method() == 'PUT':
            parameters = None

        oauth_parameters['oauth_signature'] = self._signature_method.build_signature(req, 
                                                                                     parameters, 
                                                                                     self._consumer_secret, 
                                                                                     self._secret, 
                                                                                     oauth_parameters)
        def to_header(d):
            return ",".join('%s="%s"' % (key, value) for key, value in sorted(oauth_parameters.items()))

        req.add_header(self.AUTHORIZATION_HEADER, "OAuth  %s" % to_header(oauth_parameters))

    def generate_timestamp(self):
        return int(time.time())# * 1000.0)

    def generate_nonce(self, length=8):
        return ''.join(str(random.randint(0, 9)) for i in range(length))


class BasicAuthenticator(object):
    
    def __init__(self, user, password, consumer, consumer_secret):
        self._base64string = base64.encodestring("%s:%s" % (user, password))[:-1]
        self._x_auth_header = 'OAuth oauth_consumer_key="%s" oauth_consumer_secret="%s"' % (consumer, consumer_secret)

    def augment_request(self, req, parameters):
        req.add_header("Authorization", "Basic %s" % self._base64string)
        req.add_header("X-Authorization", self._x_auth_header)

########NEW FILE########
__FILENAME__ = config



########NEW FILE########
__FILENAME__ = json
import string
import types

##    json.py implements a JSON (http://json.org) reader and writer.
##    Copyright (C) 2005  Patrick D. Logan
##    Contact mailto:patrickdlogan@stardecisions.com
##
##    This library is free software; you can redistribute it and/or
##    modify it under the terms of the GNU Lesser General Public
##    License as published by the Free Software Foundation; either
##    version 2.1 of the License, or (at your option) any later version.
##
##    This library is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
##    Lesser General Public License for more details.
##
##    You should have received a copy of the GNU Lesser General Public
##    License along with this library; if not, write to the Free Software
##    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


class _StringGenerator(object):
	def __init__(self, string):
		self.string = string
		self.index = -1
	def peek(self):
		i = self.index + 1
		if i < len(self.string):
			return self.string[i]
		else:
			return None
	def next(self):
		self.index += 1
		if self.index < len(self.string):
			return self.string[self.index]
		else:
			raise StopIteration
	def all(self):
		return self.string

class WriteException(Exception):
    pass

class ReadException(Exception):
    pass

class JsonReader(object):
    hex_digits = {'A': 10,'B': 11,'C': 12,'D': 13,'E': 14,'F':15}
    escapes = {'t':'\t','n':'\n','f':'\f','r':'\r','b':'\b'}

    def read(self, s):
        self._generator = _StringGenerator(s)
        result = self._read()
        return result

    def _read(self):
        self._eatWhitespace()
        peek = self._peek()
        if peek is None:
            raise ReadException, "Nothing to read: '%s'" % self._generator.all()
        if peek == '{':
            return self._readObject()
        elif peek == '[':
            return self._readArray()            
        elif peek == '"':
            return self._readString()
        elif peek == '-' or peek.isdigit():
            return self._readNumber()
        elif peek == 't':
            return self._readTrue()
        elif peek == 'f':
            return self._readFalse()
        elif peek == 'n':
            return self._readNull()
        elif peek == '/':
            self._readComment()
            return self._read()
        else:
            raise ReadException, "Input is not valid JSON: '%s'" % self._generator.all()

    def _readTrue(self):
        self._assertNext('t', "true")
        self._assertNext('r', "true")
        self._assertNext('u', "true")
        self._assertNext('e', "true")
        return True

    def _readFalse(self):
        self._assertNext('f', "false")
        self._assertNext('a', "false")
        self._assertNext('l', "false")
        self._assertNext('s', "false")
        self._assertNext('e', "false")
        return False

    def _readNull(self):
        self._assertNext('n', "null")
        self._assertNext('u', "null")
        self._assertNext('l', "null")
        self._assertNext('l', "null")
        return None

    def _assertNext(self, ch, target):
        if self._next() != ch:
            raise ReadException, "Trying to read %s: '%s'" % (target, self._generator.all())

    def _readNumber(self):
        isfloat = False
        result = self._next()
        peek = self._peek()
        while peek is not None and (peek.isdigit() or peek == "."):
            isfloat = isfloat or peek == "."
            result = result + self._next()
            peek = self._peek()
        try:
            if isfloat:
                return float(result)
            else:
                return int(result)
        except ValueError:
            raise ReadException, "Not a valid JSON number: '%s'" % result

    def _readString(self):
        result = ""
        assert self._next() == '"'
        try:
            while self._peek() != '"':
                ch = self._next()
                if ch == "\\":
                    ch = self._next()
                    if ch in 'brnft':
                        ch = self.escapes[ch]
                    elif ch == "u":
		        ch4096 = self._next()
			ch256  = self._next()
			ch16   = self._next()
			ch1    = self._next()
			n = 4096 * self._hexDigitToInt(ch4096)
			n += 256 * self._hexDigitToInt(ch256)
			n += 16  * self._hexDigitToInt(ch16)
			n += self._hexDigitToInt(ch1)
			ch = unichr(n)
                    elif ch not in '"/\\':
                        raise ReadException, "Not a valid escaped JSON character: '%s' in %s" % (ch, self._generator.all())
                result = result + ch
        except StopIteration:
            raise ReadException, "Not a valid JSON string: '%s'" % self._generator.all()
        assert self._next() == '"'
        return result

    def _hexDigitToInt(self, ch):
        try:
            result = self.hex_digits[ch.upper()]
        except KeyError:
            try:
                result = int(ch)
	    except ValueError:
	         raise ReadException, "The character %s is not a hex digit." % ch
        return result

    def _readComment(self):
        assert self._next() == "/"
        second = self._next()
        if second == "/":
            self._readDoubleSolidusComment()
        elif second == '*':
            self._readCStyleComment()
        else:
            raise ReadException, "Not a valid JSON comment: %s" % self._generator.all()

    def _readCStyleComment(self):
        try:
            done = False
            while not done:
                ch = self._next()
                done = (ch == "*" and self._peek() == "/")
                if not done and ch == "/" and self._peek() == "*":
                    raise ReadException, "Not a valid JSON comment: %s, '/*' cannot be embedded in the comment." % self._generator.all()
            self._next()
        except StopIteration:
            raise ReadException, "Not a valid JSON comment: %s, expected */" % self._generator.all()

    def _readDoubleSolidusComment(self):
        try:
            ch = self._next()
            while ch != "\r" and ch != "\n":
                ch = self._next()
        except StopIteration:
            pass

    def _readArray(self):
        result = []
        assert self._next() == '['
        done = self._peek() == ']'
        while not done:
            item = self._read()
            result.append(item)
            self._eatWhitespace()
            done = self._peek() == ']'
            if not done:
                ch = self._next()
                if ch != ",":
                    raise ReadException, "Not a valid JSON array: '%s' due to: '%s'" % (self._generator.all(), ch)
        assert ']' == self._next()
        return result

    def _readObject(self):
        result = {}
        assert self._next() == '{'
        done = self._peek() == '}'
        while not done:
            key = self._read()
            if type(key) is not types.StringType:
                raise ReadException, "Not a valid JSON object key (should be a string): %s" % key
            self._eatWhitespace()
            ch = self._next()
            if ch != ":":
                raise ReadException, "Not a valid JSON object: '%s' due to: '%s'" % (self._generator.all(), ch)
            self._eatWhitespace()
            val = self._read()
            result[key] = val
            self._eatWhitespace()
            done = self._peek() == '}'
            if not done:
                ch = self._next()
                if ch != ",":
                    raise ReadException, "Not a valid JSON array: '%s' due to: '%s'" % (self._generator.all(), ch)
	assert self._next() == "}"
        return result

    def _eatWhitespace(self):
        p = self._peek()
        while p is not None and p in string.whitespace or p == '/':
            if p == '/':
                self._readComment()
            else:
                self._next()
            p = self._peek()

    def _peek(self):
        return self._generator.peek()

    def _next(self):
        return self._generator.next()

class JsonWriter(object):
        
    def _append(self, s):
        self._results.append(s)

    def write(self, obj, escaped_forward_slash=False):
        self._escaped_forward_slash = escaped_forward_slash
        self._results = []
        self._write(obj)
        return "".join(self._results)

    def _write(self, obj):
        ty = type(obj)
        if ty is types.DictType:
            n = len(obj)
            self._append("{")
            for k, v in obj.items():
                self._write(k)
                self._append(":")
                self._write(v)
                n = n - 1
                if n > 0:
                    self._append(",")
            self._append("}")
        elif ty is types.ListType or ty is types.TupleType:
            n = len(obj)
            self._append("[")
            for item in obj:
                self._write(item)
                n = n - 1
                if n > 0:
                    self._append(",")
            self._append("]")
        elif ty is types.StringType or ty is types.UnicodeType:
            self._append('"')
	    obj = obj.replace('\\', r'\\')
            if self._escaped_forward_slash:
                obj = obj.replace('/', r'\/')
	    obj = obj.replace('"', r'\"')
	    obj = obj.replace('\b', r'\b')
	    obj = obj.replace('\f', r'\f')
	    obj = obj.replace('\n', r'\n')
	    obj = obj.replace('\r', r'\r')
	    obj = obj.replace('\t', r'\t')
            self._append(obj)
            self._append('"')
        elif ty is types.IntType or ty is types.LongType:
            self._append(str(obj))
        elif ty is types.FloatType:
            self._append("%f" % obj)
        elif obj is True:
            self._append("true")
        elif obj is False:
            self._append("false")
        elif obj is None:
            self._append("null")
        else:
            raise WriteException, "Cannot write in JSON: %s" % repr(obj)

def write(obj, escaped_forward_slash=False):
    return JsonWriter().write(obj, escaped_forward_slash)

def read(s):
    return JsonReader().read(s)

########NEW FILE########
__FILENAME__ = MultipartPostHandler
#!/usr/bin/python

####
# 02/2006 Will Holcomb <wholcomb@gmail.com>
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
"""
Usage:
  Enables the use of multipart/form-data for posting forms

Inspirations:
  Upload files in python:
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/146306
  urllib2_file:
    Fabien Seisen: <fabien@seisen.org>

Example:
  import MultipartPostHandler, urllib2, cookielib

  cookies = cookielib.CookieJar()
  opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies),
                                MultipartPostHandler.MultipartPostHandler)
  params = { "username" : "bob", "password" : "riviera",
             "file" : open("filename", "rb") }
  opener.open("http://wwww.bobsite.com/upload/", params)

Further Example:
  The main function of this file is a sample which downloads a page and
  then uploads it to the W3C validator.
"""

import urllib
import urllib2
import mimetools, mimetypes
import os, stat

class Callable:
    def __init__(self, anycallable):
        self.__call__ = anycallable

# Controls how sequences are uncoded. If true, elements may be given multiple values by
#  assigning a sequence.
doseq = 1

class MultipartPostHandler(urllib2.BaseHandler):
    handler_order = urllib2.HTTPHandler.handler_order - 10 # needs to run first

    def http_request(self, request):
        data = request.get_data()
        if data is not None and type(data) != str:
            v_files = []
            v_vars = []
            try:
                 for(key, value) in data.items():
                     if type(value) == file:
                         v_files.append((key, value))
                     else:
                         v_vars.append((key, value))
            except TypeError:
                systype, value, traceback = sys.exc_info()
                raise TypeError, "not a valid non-string sequence or mapping object", traceback

            if len(v_files) == 0:
                data = urllib.urlencode(v_vars, doseq)
            else:
                boundary, data = self.multipart_encode(v_vars, v_files)
                contenttype = 'multipart/form-data; boundary=%s' % boundary
                if(request.has_header('Content-Type')
                   and request.get_header('Content-Type').find('multipart/form-data') != 0):
                    print "Replacing %s with %s" % (request.get_header('content-type'), 'multipart/form-data')
                request.add_unredirected_header('Content-Type', contenttype)

            request.add_data(data)
        return request

    def multipart_encode(vars, files, boundary = None, buffer = None):
        if boundary is None:
            boundary = mimetools.choose_boundary()
        if buffer is None:
            buffer = ''
        for(key, value) in vars:
            if isinstance(value, basestring):
                value = [value]
            for sub_value in value:
                buffer += '--%s\r\n' % boundary
                buffer += 'Content-Disposition: form-data; name="%s"' % key
                buffer += '\r\n\r\n' + sub_value + '\r\n'
        for(key, fd) in files:
            file_size = os.fstat(fd.fileno())[stat.ST_SIZE]
            filename = fd.name.split('/')[-1]
            contenttype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            buffer += '--%s\r\n' % boundary
            buffer += 'Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (key, filename)
            buffer += 'Content-Type: %s\r\n' % contenttype
            # buffer += 'Content-Length: %s\r\n' % file_size
            fd.seek(0)
            buffer += '\r\n' + fd.read() + '\r\n'
        buffer += '--%s--\r\n\r\n' % boundary
        return boundary, buffer
    multipart_encode = Callable(multipart_encode)

    https_request = http_request

def main():
    import tempfile, sys

    validatorURL = "http://validator.w3.org/check"
    opener = urllib2.build_opener(MultipartPostHandler)

    def validateFile(url):
        temp = tempfile.mkstemp(suffix=".html")
        os.write(temp[0], opener.open(url).read())
        params = { "ss" : "0",            # show source
                   "doctype" : "Inline",
                   "uploaded_file" : open(temp[1], "rb") }
        print opener.open(validatorURL, params).read()
        os.remove(temp[1])

    if len(sys.argv[1:]) > 0:
        for arg in sys.argv[1:]:
            validateFile(arg)
    else:
        validateFile("http://www.google.com")

if __name__=="__main__":
    main()

########NEW FILE########
__FILENAME__ = scapi_tests
from __future__ import with_statement

import os
import urllib2
import itertools
from textwrap import dedent
import pkg_resources
import logging
import webbrowser
from unittest import TestCase

from configobj import ConfigObj
from validate import Validator


import scapi
import scapi.authentication

logger = logging.getLogger("scapi.tests")

api_logger = logging.getLogger("scapi")


class SCAPITests(TestCase):

    CONFIG_NAME = "test.ini"
    TOKEN = None
    SECRET = None 
    CONSUMER = None 
    CONSUMER_SECRET = None 
    API_HOST = None 
    USER = None 
    PASSWORD = None 
    AUTHENTICATOR = None 
    RUN_INTERACTIVE_TESTS = False
    RUN_LONG_TESTS = False
    
    def setUp(self):
        self._load_config()
        assert pkg_resources.resource_exists("scapi.tests.test_connect", "knaster.mp3")
        self.data = pkg_resources.resource_stream("scapi.tests.test_connect", "knaster.mp3")
        self.artwork_data = pkg_resources.resource_stream("scapi.tests.test_connect", "spam.jpg")

    CONFIGSPEC=dedent("""
    [api]
    token=string
    secret=string
    consumer=string
    consumer_secret=string
    api_host=string
    user=string
    password=string
    authenticator=option('oauth', 'base', default='oauth')
    
    [proxy]
    use_proxy=boolean(default=false)
    proxy=string(default=http://127.0.0.1:10000/)

    [logging]
    test_logger=string(default=ERROR)
    api_logger=string(default=ERROR)

    [test]
    run_interactive_tests=boolean(default=false)
    """)


    def _load_config(self):
        """
        Loads the configuration by looking from

         - the environment variable SCAPI_CONFIG
         - the installation location upwards until it finds test.ini
         - the current working directory upwards until it finds test.ini

        Raises an error if there is no config found
        """
        config_name = self.CONFIG_NAME

        name = None

        if "SCAPI_CONFIG" in os.environ:
            if os.path.exists(os.environ["SCAPI_CONFIG"]):
                name = os.environ["SCAPI_CONFIG"]

        def search_for_config(current):
            while current:
                name = os.path.join(current, config_name)
                if os.path.exists(name):
                    return name
                new_current = os.path.dirname(current)
                if new_current == current:
                    return
                current = new_current

        if name is None:
            name = search_for_config(os.path.dirname(__file__))
        if name is None:
            name = search_for_config(os.getcwd())

        if not name:
            raise Exception("No test configuration file found!")

        parser = ConfigObj(name, configspec=self.CONFIGSPEC.split("\n"))
        val = Validator()
        if not parser.validate(val):
            raise Exception("Config file validation error")

        api = parser['api']
        self.TOKEN = api.get('token')
        self.SECRET = api.get('secret')
        self.CONSUMER = api.get('consumer')
        self.CONSUMER_SECRET = api.get('consumer_secret')
        self.API_HOST = api.get('api_host')
        self.USER = api.get('user', None)
        self.PASSWORD = api.get('password', None)
        self.AUTHENTICATOR = api.get("authenticator")

        # reset the hard-coded values in the api
        if self.API_HOST:
            scapi.AUTHORIZATION_URL = "http://%s/oauth/authorize" % self.API_HOST
            scapi.REQUEST_TOKEN_URL = 'http://%s/oauth/request_token' % self.API_HOST
            scapi.ACCESS_TOKEN_URL = 'http://%s/oauth/access_token' % self.API_HOST

        if "proxy" in parser and parser["proxy"]["use_proxy"]:
            scapi.USE_PROXY = True
            scapi.PROXY = parser["proxy"]["proxy"]

        if "logging" in parser:
            logger.setLevel(getattr(logging, parser["logging"]["test_logger"]))
            api_logger.setLevel(getattr(logging, parser["logging"]["api_logger"]))

        self.RUN_INTERACTIVE_TESTS = parser["test"]["run_interactive_tests"]
        

    @property
    def root(self):
        """
        Return the properly configured root-scope.
        """
        if self.AUTHENTICATOR == "oauth":
            authenticator = scapi.authentication.OAuthAuthenticator(self.CONSUMER, 
                                                                    self.CONSUMER_SECRET,
                                                                    self.TOKEN, 
                                                                    self.SECRET)
        elif self.AUTHENTICATOR == "base":
            authenticator = scapi.authentication.BasicAuthenticator(self.USER, self.PASSWORD, self.CONSUMER, self.CONSUMER_SECRET)
        else:
            raise Exception("Unknown authenticator setting: %s", self.AUTHENTICATOR)

        connector = scapi.ApiConnector(host=self.API_HOST, 
                                        authenticator=authenticator)

        logger.debug("RootScope: %s authenticator: %s", self.API_HOST, self.AUTHENTICATOR)
        return scapi.Scope(connector)


    def test_connect(self):
        """
        test_connect

        Tries to connect & performs some read-only operations.
        """
        sca = self.root
    #     quite_a_few_users = list(itertools.islice(sca.users(), 0, 127))

    #     logger.debug(quite_a_few_users)
    #     assert isinstance(quite_a_few_users, list) and isinstance(quite_a_few_users[0], scapi.User)
        user = sca.me()
        logger.debug(user)
        assert isinstance(user, scapi.User)
        contacts = list(user.contacts())
        assert isinstance(contacts, list)
        if contacts:
            assert isinstance(contacts[0], scapi.User)
            logger.debug(contacts)
        tracks = list(user.tracks())
        assert isinstance(tracks, list)
        if tracks:
            assert isinstance(tracks[0], scapi.Track)
            logger.debug(tracks)


    def test_access_token_acquisition(self):
        """
        This test is commented out because it needs user-interaction.
        """
        if not self.RUN_INTERACTIVE_TESTS:
            return
        oauth_authenticator = scapi.authentication.OAuthAuthenticator(self.CONSUMER, 
                                                                      self.CONSUMER_SECRET,
                                                                      None, 
                                                                      None)

        sca = scapi.ApiConnector(host=self.API_HOST, authenticator=oauth_authenticator)
        token, secret = sca.fetch_request_token()
        authorization_url = sca.get_request_token_authorization_url(token)
        webbrowser.open(authorization_url)
        oauth_verifier = raw_input("please enter verifier code as seen in the browser:")
        
        oauth_authenticator = scapi.authentication.OAuthAuthenticator(self.CONSUMER, 
                                                                      self.CONSUMER_SECRET,
                                                                      token, 
                                                                      secret)

        sca = scapi.ApiConnector(self.API_HOST, authenticator=oauth_authenticator)
        token, secret = sca.fetch_access_token(oauth_verifier)
        logger.info("Access token: '%s'", token)
        logger.info("Access token secret: '%s'", secret)
        # force oauth-authentication with the new parameters, and
        # then invoke some simple test
        self.AUTHENTICATOR = "oauth"
        self.TOKEN = token
        self.SECRET = secret
        self.test_connect()


    def test_track_creation(self):
        sca = self.root
        track = sca.Track.new(title='bar', asset_data=self.data)
        assert isinstance(track, scapi.Track)


    def test_track_update(self):
        sca = self.root
        track = sca.Track.new(title='bar', asset_data=self.data)
        assert isinstance(track, scapi.Track)
        track.title='baz'
        track = sca.Track.get(track.id)
        assert track.title == "baz"


    def test_scoped_track_creation(self):
        sca = self.root
        user = sca.me()
        track = user.tracks.new(title="bar", asset_data=self.data)
        assert isinstance(track, scapi.Track)


    def test_upload(self):
        sca = self.root
        sca = self.root
        track = sca.Track.new(title='bar', asset_data=self.data)
        assert isinstance(track, scapi.Track)


    def test_contact_list(self):
        sca = self.root
        user = sca.me()
        contacts = list(user.contacts())
        assert isinstance(contacts, list)
        if contacts:
            assert isinstance(contacts[0], scapi.User)


    def test_permissions(self):
        sca = self.root
        user = sca.me()
        tracks = itertools.islice(user.tracks(), 1)
        for track in tracks:
            permissions = list(track.permissions())
            logger.debug(permissions)
            assert isinstance(permissions, list)
            if permissions:
                assert isinstance(permissions[0], scapi.User)


    def test_setting_permissions(self):
        sca = self.root
        me = sca.me()
        track = sca.Track.new(title='bar', sharing="private", asset_data=self.data)
        assert track.sharing == "private"
        users = itertools.islice(sca.users(), 10)
        users_to_set = [user  for user in users if user != me]
        assert users_to_set, "Didn't find any suitable users"
        track.permissions = users_to_set
        assert set(track.permissions()) == set(users_to_set)


    def test_setting_comments(self):
        sca = self.root
        user = sca.me()
        track = sca.Track.new(title='bar', sharing="private", asset_data=self.data)
        comment = sca.Comment.create(body="This is the body of my comment", timestamp=10)
        track.comments = comment
        assert track.comments().next().body == comment.body


    def test_setting_comments_the_way_shawn_says_its_correct(self):
        sca = self.root
        track = sca.Track.new(title='bar', sharing="private", asset_data=self.data)
        cbody = "This is the body of my comment"
        track.comments.new(body=cbody, timestamp=10)
        assert list(track.comments())[0].body == cbody


    def test_contact_add_and_removal(self):
        sca = self.root
        me = sca.me()
        for user in sca.users():
            if user != me:            
                user_to_set = user
                break

        contacts = list(me.contacts())
        if user_to_set in contacts:
            me.contacts.remove(user_to_set)

        me.contacts.append(user_to_set)

        contacts = list(me.contacts() )
        assert user_to_set.id in [c.id for c in contacts]

        me.contacts.remove(user_to_set)

        contacts = list(me.contacts() )
        assert user_to_set not in contacts


    def test_favorites(self):
        sca = self.root
        me = sca.me()

        favorites = list(me.favorites())
        assert favorites == [] or isinstance(favorites[0], scapi.Track)

        track = None
        for user in sca.users():
            if user == me:
                continue
            for track in user.tracks():
                break
            if track is not None:
                break

        me.favorites.append(track)

        favorites = list(me.favorites())
        assert track in favorites

        me.favorites.remove(track)

        favorites = list(me.favorites())
        assert track not in favorites


    def test_large_list(self):
        if not self.RUN_LONG_TESTS:
            return
        
        sca = self.root
        
        tracks = list(sca.tracks())
        if len(tracks) < scapi.ApiConnector.LIST_LIMIT:
            for i in xrange(scapi.ApiConnector.LIST_LIMIT):
                sca.Track.new(title='test_track_%i' % i, asset_data=self.data)
        all_tracks = sca.tracks()
        assert not isinstance(all_tracks, list)
        all_tracks = list(all_tracks)
        assert len(all_tracks) > scapi.ApiConnector.LIST_LIMIT



    def test_filtered_list(self):
        if not self.RUN_LONG_TESTS:
            return
        
        sca = self.root
    
        tracks = list(sca.tracks(params={
            "bpm[from]" : "180",
            }))
        if len(tracks) < scapi.ApiConnector.LIST_LIMIT:
            for i in xrange(scapi.ApiConnector.LIST_LIMIT):
                sca.Track.new(title='test_track_%i' % i, asset_data=self.data)
        all_tracks = sca.tracks()
        assert not isinstance(all_tracks, list)
        all_tracks = list(all_tracks)
        assert len(all_tracks) > scapi.ApiConnector.LIST_LIMIT


    def test_events(self):
        events = list(self.root.events())
        assert isinstance(events, list)
        assert isinstance(events[0], scapi.Event)


    def test_me_having_stress(self):
        sca = self.root
        for _ in xrange(20):
            self.setUp()
            sca.me()


    def test_non_global_api(self):
        root = self.root
        me = root.me()
        assert isinstance(me, scapi.User)

        # now get something *from* that user
        list(me.favorites())


    def test_playlists(self):
        sca = self.root
        playlists = list(itertools.islice(sca.playlists(), 0, 127))
        for playlist in playlists:
            tracks = playlist.tracks
            if not isinstance(tracks, list):
                tracks = [tracks]
            for trackdata in tracks:
                print trackdata
                #user = trackdata.user
                #print user
                #print user.tracks()
            print playlist.user
            break




    def test_playlist_creation(self):
        sca = self.root
        sca.Playlist.new(title="I'm so happy, happy, happy, happy!")
        


    def test_groups(self):
        if not self.RUN_LONG_TESTS:
            return
        
        sca = self.root
        groups = list(itertools.islice(sca.groups(), 0, 127))
        for group in groups:
            users = group.users()
            for user in users:
                pass


    def test_track_creation_with_email_sharers(self):
        sca = self.root
        emails = [dict(address="deets@web.de"), dict(address="hannes@soundcloud.com")]
        track = sca.Track.new(title='bar', asset_data=self.data,
                              shared_to=dict(emails=emails)
                              )
        assert isinstance(track, scapi.Track)



    def test_track_creation_with_artwork(self):
        sca = self.root
        track = sca.Track.new(title='bar',
                              asset_data=self.data,
                              artwork_data=self.artwork_data,
                              )
        assert isinstance(track, scapi.Track)

        track.title = "foobarbaz"
        


    def test_oauth_get_signing(self):
        sca = self.root

        url = "http://api.soundcloud.dev/oauth/test_request"
        params = dict(foo="bar",
                      baz="padamm",
                      )
        url += sca._create_query_string(params)
        signed_url = sca.oauth_sign_get_request(url)

        
        res = urllib2.urlopen(signed_url).read()
        assert "oauth_nonce" in res


    def test_streaming(self):
        sca = self.root

        track = sca.tracks(params={
            "filter" : "streamable",
            }).next()

        
        assert isinstance(track, scapi.Track)

        stream_url = track.stream_url

        signed_url = track.oauth_sign_get_request(stream_url)

        
    def test_downloadable(self):
        sca = self.root

        track = sca.tracks(params={
            "filter" : "downloadable",
            }).next()

        
        assert isinstance(track, scapi.Track)

        download_url = track.download_url

        signed_url = track.oauth_sign_get_request(download_url)

        data = urllib2.urlopen(signed_url).read()
        assert data



    def test_modifying_playlists(self):
        sca = self.root

        me = sca.me()
        my_tracks = list(me.tracks())

        assert my_tracks

        playlist = me.playlists().next()
        # playlist = sca.Playlist.get(playlist.id)

        assert isinstance(playlist, scapi.Playlist)

        pl_tracks = playlist.tracks

        playlist.title = "foobarbaz"



    def test_track_deletion(self):
        sca = self.root
        track = sca.Track.new(title='bar', asset_data=self.data,
                              )

        sca.tracks.remove(track)

        

    def test_track_creation_with_updated_artwork(self):
        sca = self.root
        track = sca.Track.new(title='bar',
                              asset_data=self.data,
                              )
        assert isinstance(track, scapi.Track)

        track.artwork_data = self.artwork_data

    def test_update_own_description(self):
        sca = self.root
        me = sca.me()
        
        new_description = "This is my new description"
        old_description = "This is my old description"
        
        if me.description == new_description:
          change_to_description = old_description
        else:
          change_to_description = new_description
        
        me.description = change_to_description
        
        user = sca.User.get(me.id)
        assert user.description == change_to_description

########NEW FILE########
__FILENAME__ = test_connect
from __future__ import with_statement
import os
import tempfile
import itertools
from ConfigParser import SafeConfigParser
import pkg_resources
import scapi
import scapi.authentication
import logging
import webbrowser

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
_logger = logging.getLogger("scapi")
#_logger.setLevel(logging.DEBUG)

RUN_INTERACTIVE_TESTS = False
USE_OAUTH = True

TOKEN  = "FjNE9aRTg8kpxuOjzwsX8Q"
SECRET = "NP5PGoyKcQv64E0aZgV4CRNzHfPwR4QghrWoqEgEE"
CONSUMER = "EEi2URUfM97pAAxHTogDpQ"
CONSUMER_SECRET = "NFYd8T3i4jVKGZ9TMy9LHaBQB3Sh8V5sxBiMeMZBow"
API_HOST = "api.soundcloud.dev:3000"
USER = ""
PASSWORD = ""

CONFIG_NAME = "soundcloud.cfg"

CONNECTOR = None
ROOT = None
def setup():
    global CONNECTOR, ROOT
    # load_config()
    #scapi.ApiConnector(host='192.168.2.101:3000', user='tiga', password='test')
    #scapi.ApiConnector(host='sandbox-api.soundcloud.com:3030', user='tiga', password='test')
    scapi.USE_PROXY = False
    scapi.PROXY = 'http://127.0.0.1:10000/'

    if USE_OAUTH:
        authenticator = scapi.authentication.OAuthAuthenticator(CONSUMER, 
                                                                CONSUMER_SECRET,
                                                                TOKEN, 
                                                                SECRET)
    else:
        authenticator = scapi.authentication.BasicAuthenticator(USER, PASSWORD, CONSUMER, CONSUMER_SECRET)
    
    logger.debug("API_HOST: %s", API_HOST)
    CONNECTOR = scapi.ApiConnector(host=API_HOST, 
                                    authenticator=authenticator)
    ROOT = scapi.Scope(CONNECTOR)

def load_config(config_name=None):
    global TOKEN, SECRET, CONSUMER_SECRET, CONSUMER, API_HOST, USER, PASSWORD
    if config_name is None:
        config_name = CONFIG_NAME
    parser = SafeConfigParser()
    current = os.getcwd()
    while current:
        name = os.path.join(current, config_name)
        if os.path.exists(name):
            parser.read([name])
            TOKEN = parser.get('global', 'accesstoken')
            SECRET = parser.get('global', 'accesstoken_secret')
            CONSUMER = parser.get('global', 'consumer')
            CONSUMER_SECRET = parser.get('global', 'consumer_secret')
            API_HOST = parser.get('global', 'host')
            USER = parser.get('global', 'user')
            PASSWORD = parser.get('global', 'password')
            logger.debug("token: %s", TOKEN)
            logger.debug("secret: %s", SECRET)
            logger.debug("consumer: %s", CONSUMER)
            logger.debug("consumer_secret: %s", CONSUMER_SECRET)
            logger.debug("user: %s", USER)
            logger.debug("password: %s", PASSWORD)
            logger.debug("host: %s", API_HOST)
            break
        new_current = os.path.dirname(current)
        if new_current == current:
            break
        current = new_current
    

def test_load_config():
    base = tempfile.mkdtemp()
    oldcwd = os.getcwd()
    cdir = os.path.join(base, "foo")
    os.mkdir(cdir)
    os.chdir(cdir)
    test_config = """
[global]
host=host
consumer=consumer
consumer_secret=consumer_secret
accesstoken=accesstoken
accesstoken_secret=accesstoken_secret
user=user
password=password
"""
    with open(os.path.join(base, CONFIG_NAME), "w") as cf:
        cf.write(test_config)
    load_config()
    assert TOKEN == "accesstoken" and SECRET == "accesstoken_secret" and API_HOST == 'host'
    assert CONSUMER == "consumer" and CONSUMER_SECRET == "consumer_secret"
    assert USER == "user" and PASSWORD == "password"
    os.chdir(oldcwd)
    load_config()
    
    
def test_connect():
    sca = ROOT
    quite_a_few_users = list(itertools.islice(sca.users(), 0, 127))

    logger.debug(quite_a_few_users)
    assert isinstance(quite_a_few_users, list) and isinstance(quite_a_few_users[0], scapi.User)
    user = sca.me()
    logger.debug(user)
    assert isinstance(user, scapi.User)
    contacts = list(user.contacts())
    assert isinstance(contacts, list)
    assert isinstance(contacts[0], scapi.User)
    logger.debug(contacts)
    tracks = list(user.tracks())
    assert isinstance(tracks, list)
    assert isinstance(tracks[0], scapi.Track)
    logger.debug(tracks)


def test_access_token_acquisition():
    """
    This test is commented out because it needs user-interaction.
    """
    if not RUN_INTERACTIVE_TESTS:
        return
    oauth_authenticator = scapi.authentication.OAuthAuthenticator(CONSUMER, 
                                                                  CONSUMER_SECRET,
                                                                  None, 
                                                                  None)

    sca = scapi.ApiConnector(host=API_HOST, authenticator=oauth_authenticator)
    token, secret = sca.fetch_request_token()
    authorization_url = sca.get_request_token_authorization_url(token)
    webbrowser.open(authorization_url)
    raw_input("please press return")
    oauth_authenticator = scapi.authentication.OAuthAuthenticator(CONSUMER, 
                                                                  CONSUMER_SECRET,
                                                                  token, 
                                                                  secret)

    sca = scapi.ApiConnector(API_HOST, authenticator=oauth_authenticator)
    token, secret = sca.fetch_access_token()
    logger.info("Access token: '%s'", token)
    logger.info("Access token secret: '%s'", secret)
    oauth_authenticator = scapi.authentication.OAuthAuthenticator(CONSUMER, 
                                                                  CONSUMER_SECRET,
                                                                  token, 
                                                                  secret)

    sca = scapi.ApiConnector(API_HOST, authenticator=oauth_authenticator)
    test_track_creation()

def test_track_creation():
    sca = ROOT
    track = sca.Track.new(title='bar')
    assert isinstance(track, scapi.Track)

def test_track_update():
    sca = ROOT
    track = sca.Track.new(title='bar')
    assert isinstance(track, scapi.Track)
    track.title='baz'
    track = sca.Track.get(track.id)
    assert track.title == "baz"

def test_scoped_track_creation():
    sca = ROOT
    user = sca.me()
    track = user.tracks.new(title="bar")
    assert isinstance(track, scapi.Track)

def test_upload():
    assert pkg_resources.resource_exists("scapi.tests.test_connect", "knaster.mp3")
    data = pkg_resources.resource_stream("scapi.tests.test_connect", "knaster.mp3")
    sca = ROOT
    user = sca.me()
    logger.debug(user)
    asset = sca.assets.new(filedata=data)
    assert isinstance(asset, scapi.Asset)
    logger.debug(asset)
    tracks = list(user.tracks())
    track = tracks[0]
    track.assets.append(asset)

def test_contact_list():
    sca = ROOT
    user = sca.me()
    contacts = list(user.contacts())
    assert isinstance(contacts, list)
    assert isinstance(contacts[0], scapi.User)

def test_permissions():
    sca = ROOT
    user = sca.me()
    tracks = itertools.islice(user.tracks(), 1)
    for track in tracks:
        permissions = list(track.permissions())
        logger.debug(permissions)
        assert isinstance(permissions, list)
        if permissions:
            assert isinstance(permissions[0], scapi.User)

def test_setting_permissions():
    sca = ROOT
    me = sca.me()
    track = sca.Track.new(title='bar', sharing="private")
    assert track.sharing == "private"
    users = itertools.islice(sca.users(), 10)
    users_to_set = [user  for user in users if user != me]
    assert users_to_set, "Didn't find any suitable users"
    track.permissions = users_to_set
    assert set(track.permissions()) == set(users_to_set)

def test_setting_comments():
    sca = ROOT
    user = sca.me()
    track = sca.Track.new(title='bar', sharing="private")
    comment = sca.Comment.create(body="This is the body of my comment", timestamp=10)
    track.comments = comment
    assert track.comments().next().body == comment.body
    

def test_setting_comments_the_way_shawn_says_its_correct():
    sca = ROOT
    track = sca.Track.new(title='bar', sharing="private")
    cbody = "This is the body of my comment"
    track.comments.new(body=cbody, timestamp=10)
    assert list(track.comments())[0].body == cbody

def test_contact_add_and_removal():
    sca = ROOT
    me = sca.me()
    for user in sca.users():
        if user != me:            
            user_to_set = user
            break

    contacts = list(me.contacts())
    if user_to_set in contacts:
        me.contacts.remove(user_to_set)

    me.contacts.append(user_to_set)

    contacts = list(me.contacts() )
    assert user_to_set.id in [c.id for c in contacts]

    me.contacts.remove(user_to_set)

    contacts = list(me.contacts() )
    assert user_to_set not in contacts


def test_favorites():
    sca = ROOT
    me = sca.me()

    favorites = list(me.favorites())
    assert favorites == [] or isinstance(favorites[0], scapi.Track)

    track = None
    for user in sca.users():
        if user == me:
            continue
        for track in user.tracks():
            break
        if track is not None:
            break
    
    me.favorites.append(track)

    favorites = list(me.favorites())
    assert track in favorites

    me.favorites.remove(track)

    favorites = list(me.favorites())
    assert track not in favorites

def test_large_list():
    sca = ROOT
    tracks = list(sca.tracks())
    if len(tracks) < scapi.ApiConnector.LIST_LIMIT:
        for i in xrange(scapi.ApiConnector.LIST_LIMIT):            
            scapi.Track.new(title='test_track_%i' % i)
    all_tracks = sca.tracks()
    assert not isinstance(all_tracks, list)
    all_tracks = list(all_tracks)
    assert len(all_tracks) > scapi.ApiConnector.LIST_LIMIT


def test_events():
    events = list(ROOT.events())
    assert isinstance(events, list)
    assert isinstance(events[0], scapi.Event)

def test_me_having_stress():
    sca = ROOT
    for _ in xrange(20):
        setup()
        sca.me()

def test_non_global_api():
    root = scapi.Scope(CONNECTOR)
    me = root.me()
    assert isinstance(me, scapi.User)

    # now get something *from* that user
    favorites = list(me.favorites())
    assert favorites

def test_playlists():
    sca = ROOT
    playlists = list(itertools.islice(sca.playlists(), 0, 127))
    found = False
    for playlist in playlists:
        tracks = playlist.tracks
        if not isinstance(tracks, list):
            tracks = [tracks]
        for trackdata in tracks:
            print trackdata
            user = trackdata.user
            print user
            print user.tracks()
        print playlist.user
        break

########NEW FILE########
__FILENAME__ = test_oauth
import pkg_resources
import scapi
import scapi.authentication
import urllib
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
_logger = logging.getLogger("scapi")
_logger.setLevel(logging.DEBUG)

TOKEN  = "QcciYu1FSwDSGKAG2mNw"
SECRET = "gJ2ok6ULUsYQB3rsBmpHCRHoFCAPOgK8ZjoIyxzris"
CONSUMER = "Cy2eLPrIMp4vOxjz9icdQ"
CONSUMER_SECRET = "KsBa272x6M2to00Vo5FdvZXt9kakcX7CDIPJoGwTro"

def test_base64_connect():
    scapi.USE_PROXY = True
    scapi.PROXY = 'http://127.0.0.1:10000/'
    scapi.SoundCloudAPI(host='192.168.2.31:3000', authenticator=scapi.authentication.BasicAuthenticator('tiga', 'test'))
    sca = scapi.Scope()
    assert isinstance(sca.me(), scapi.User)


def test_oauth_connect():
    scapi.USE_PROXY = True
    scapi.PROXY = 'http://127.0.0.1:10000/'
    scapi.SoundCloudAPI(host='192.168.2.31:3000', 
                        authenticator=scapi.authentication.OAuthAuthenticator(CONSUMER, 
                                                                              CONSUMER_SECRET,
                                                                              TOKEN, SECRET))

    sca = scapi.Scope()
    assert isinstance(sca.me(), scapi.User)



########NEW FILE########
__FILENAME__ = util
##    SouncCloudAPI implements a Python wrapper around the SoundCloud RESTful
##    API
##
##    Copyright (C) 2008  Diez B. Roggisch
##    Contact mailto:deets@soundcloud.com
##
##    This library is free software; you can redistribute it and/or
##    modify it under the terms of the GNU Lesser General Public
##    License as published by the Free Software Foundation; either
##    version 2.1 of the License, or (at your option) any later version.
##
##    This library is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
##    Lesser General Public License for more details.
##
##    You should have received a copy of the GNU Lesser General Public
##    License along with this library; if not, write to the Free Software
##    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import urllib

def escape(s):
    # escape '/' too
    return urllib.quote(s, safe='')






class MultiDict(dict):


    def add(self, key, new_value):
        if key in self:
            value = self[key]
            if not isinstance(value, list):
                value = [value]
                self[key] = value
            value.append(new_value)
        else:
            self[key] = new_value


    def iteritemslist(self):
        for key, value in self.iteritems():
            if not isinstance(value, list):
                value = [value]
            yield key, value


    

########NEW FILE########
