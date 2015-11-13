__FILENAME__ = client
import requests
from . import utils


class Client(object):

    def __init__(self, client_id, client_secret, redirect_uri, \
                 authorization_uri, token_uri):
        """Constructor for OAuth 2.0 Client.

        :param client_id: Client ID.
        :type client_id: str
        :param client_secret: Client secret.
        :type client_secret: str
        :param redirect_uri: Client redirect URI: handle provider response.
        :type redirect_uri: str
        :param authorization_uri: Provider authorization URI.
        :type authorization_uri: str
        :param token_uri: Provider token URI.
        :type token_uri: str
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.authorization_uri = authorization_uri
        self.token_uri = token_uri

    @property
    def default_response_type(self):
        return 'code'

    @property
    def default_grant_type(self):
        return 'authorization_code'

    def http_post(self, url, data=None):
        """POST to URL and get result as a response object.

        :param url: URL to POST.
        :type url: str
        :param data: Data to send in the form body.
        :type data: str
        :rtype: requests.Response
        """
        if not url.startswith('https://'):
            raise ValueError('Protocol must be HTTPS, invalid URL: %s' % url)
        return requests.post(url, data, verify=True)

    def get_authorization_code_uri(self, **params):
        """Construct a full URL that can be used to obtain an authorization
        code from the provider authorization_uri. Use this URI in a client
        frame to cause the provider to generate an authorization code.

        :rtype: str
        """
        if 'response_type' not in params:
            params['response_type'] = self.default_response_type
        params.update({'client_id': self.client_id,
                       'redirect_uri': self.redirect_uri})
        return utils.build_url(self.authorization_uri, params)

    def get_token(self, code, **params):
        """Get an access token from the provider token URI.

        :param code: Authorization code.
        :type code: str
        :return: Dict containing access token, refresh token, etc.
        :rtype: dict
        """
        params['code'] = code
        if 'grant_type' not in params:
            params['grant_type'] = self.default_grant_type
        params.update({'client_id': self.client_id,
                       'client_secret': self.client_secret,
                       'redirect_uri': self.redirect_uri})
        response = self.http_post(self.token_uri, params)
        try:
            return response.json()
        except TypeError:
            return response.json

########NEW FILE########
__FILENAME__ = provider
import json
import logging
from requests import Response
from cStringIO import StringIO
try:
    from werkzeug.exceptions import Unauthorized
except ImportError:
    Unauthorized = Exception
from . import utils


class Provider(object):
    """Base provider class for different types of OAuth 2.0 providers."""

    def _handle_exception(self, exc):
        """Handle an internal exception that was caught and suppressed.

        :param exc: Exception to process.
        :type exc: Exception
        """
        logger = logging.getLogger(__name__)
        logger.exception(exc)

    def _make_response(self, body='', headers=None, status_code=200):
        """Return a response object from the given parameters.

        :param body: Buffer/string containing the response body.
        :type body: str
        :param headers: Dict of headers to include in the requests.
        :type headers: dict
        :param status_code: HTTP status code.
        :type status_code: int
        :rtype: requests.Response
        """
        res = Response()
        res.status_code = status_code
        if headers is not None:
            res.headers.update(headers)
        res.raw = StringIO(body)
        return res

    def _make_redirect_error_response(self, redirect_uri, err):
        """Return a HTTP 302 redirect response object containing the error.

        :param redirect_uri: Client redirect URI.
        :type redirect_uri: str
        :param err: OAuth error message.
        :type err: str
        :rtype: requests.Response
        """
        params = {
            'error': err,
            'response_type': None,
            'client_id': None,
            'redirect_uri': None
        }
        redirect = utils.build_url(redirect_uri, params)
        return self._make_response(headers={'Location': redirect},
                                   status_code=302)

    def _make_json_response(self, data, headers=None, status_code=200):
        """Return a response object from the given JSON data.

        :param data: Data to JSON-encode.
        :type data: mixed
        :param headers: Dict of headers to include in the requests.
        :type headers: dict
        :param status_code: HTTP status code.
        :type status_code: int
        :rtype: requests.Response
        """
        response_headers = {}
        if headers is not None:
            response_headers.update(headers)
        response_headers['Content-Type'] = 'application/json;charset=UTF-8'
        response_headers['Cache-Control'] = 'no-store'
        response_headers['Pragma'] = 'no-cache'
        return self._make_response(json.dumps(data),
                                   response_headers,
                                   status_code)

    def _make_json_error_response(self, err):
        """Return a JSON-encoded response object representing the error.

        :param err: OAuth error message.
        :type err: str
        :rtype: requests.Response
        """
        return self._make_json_response({'error': err}, status_code=400)

    def _invalid_redirect_uri_response(self):
        """What to return when the redirect_uri parameter is missing.

        :rtype: requests.Response
        """
        return self._make_json_error_response('invalid_request')


class AuthorizationProvider(Provider):
    """OAuth 2.0 authorization provider. This class manages authorization
    codes and access tokens. Certain methods MUST be overridden in a
    subclass, thus this class cannot be directly used as a provider.

    These are the methods that must be implemented in a subclass:

        validate_client_id(self, client_id)
            # Return True or False

        validate_client_secret(self, client_id, client_secret)
            # Return True or False

        validate_scope(self, client_id, scope)
            # Return True or False

        validate_redirect_uri(self, client_id, redirect_uri)
            # Return True or False

        validate_access(self)  # Use this to validate your app session user
            # Return True or False

        from_authorization_code(self, client_id, code, scope)
            # Return mixed data or None on invalid

        from_refresh_token(self, client_id, refresh_token, scope)
            # Return mixed data or None on invalid

        persist_authorization_code(self, client_id, code, scope)
            # Return value ignored

        persist_token_information(self, client_id, scope, access_token,
                                  token_type, expires_in, refresh_token,
                                  data)
            # Return value ignored

        discard_authorization_code(self, client_id, code)
            # Return value ignored

        discard_refresh_token(self, client_id, refresh_token)
            # Return value ignored

    Optionally, the following may be overridden to acheive desired behavior:

        @property
        token_length(self)

        @property
        token_type(self)

        @property
        token_expires_in(self)

        generate_authorization_code(self)

        generate_access_token(self)

        generate_refresh_token(self)

    """

    @property
    def token_length(self):
        """Property method to get the length used to generate tokens.

        :rtype: int
        """
        return 40

    @property
    def token_type(self):
        """Property method to get the access token type.

        :rtype: str
        """
        return 'Bearer'

    @property
    def token_expires_in(self):
        """Property method to get the token expiration time in seconds.

        :rtype: int
        """
        return 3600

    def generate_authorization_code(self):
        """Generate a random authorization code.

        :rtype: str
        """
        return utils.random_ascii_string(self.token_length)

    def generate_access_token(self):
        """Generate a random access token.

        :rtype: str
        """
        return utils.random_ascii_string(self.token_length)

    def generate_refresh_token(self):
        """Generate a random refresh token.

        :rtype: str
        """
        return utils.random_ascii_string(self.token_length)

    def get_authorization_code(self,
                               response_type,
                               client_id,
                               redirect_uri,
                               **params):
        """Generate authorization code HTTP response.

        :param response_type: Desired response type. Must be exactly "code".
        :type response_type: str
        :param client_id: Client ID.
        :type client_id: str
        :param redirect_uri: Client redirect URI.
        :type redirect_uri: str
        :rtype: requests.Response
        """

        # Ensure proper response_type
        if response_type != 'code':
            err = 'unsupported_response_type'
            return self._make_redirect_error_response(redirect_uri, err)

        # Check redirect URI
        is_valid_redirect_uri = self.validate_redirect_uri(client_id,
                                                           redirect_uri)
        if not is_valid_redirect_uri:
            return self._invalid_redirect_uri_response()

        # Check conditions
        is_valid_client_id = self.validate_client_id(client_id)
        is_valid_access = self.validate_access()
        scope = params.get('scope', '')
        is_valid_scope = self.validate_scope(client_id, scope)

        # Return proper error responses on invalid conditions
        if not is_valid_client_id:
            err = 'unauthorized_client'
            return self._make_redirect_error_response(redirect_uri, err)

        if not is_valid_access:
            err = 'access_denied'
            return self._make_redirect_error_response(redirect_uri, err)

        if not is_valid_scope:
            err = 'invalid_scope'
            return self._make_redirect_error_response(redirect_uri, err)

        # Generate authorization code
        code = self.generate_authorization_code()

        # Save information to be used to validate later requests
        self.persist_authorization_code(client_id=client_id,
                                        code=code,
                                        scope=scope)

        # Return redirection response
        params.update({
            'code': code,
            'response_type': None,
            'client_id': None,
            'redirect_uri': None
        })
        redirect = utils.build_url(redirect_uri, params)
        return self._make_response(headers={'Location': redirect},
                                   status_code=302)

    def refresh_token(self,
                      grant_type,
                      client_id,
                      client_secret,
                      refresh_token,
                      **params):
        """Generate access token HTTP response from a refresh token.

        :param grant_type: Desired grant type. Must be "refresh_token".
        :type grant_type: str
        :param client_id: Client ID.
        :type client_id: str
        :param client_secret: Client secret.
        :type client_secret: str
        :param refresh_token: Refresh token.
        :type refresh_token: str
        :rtype: requests.Response
        """

        # Ensure proper grant_type
        if grant_type != 'refresh_token':
            return self._make_json_error_response('unsupported_grant_type')

        # Check conditions
        is_valid_client_id = self.validate_client_id(client_id)
        is_valid_client_secret = self.validate_client_secret(client_id,
                                                             client_secret)
        scope = params.get('scope', '')
        is_valid_scope = self.validate_scope(client_id, scope)
        data = self.from_refresh_token(client_id, refresh_token, scope)
        is_valid_refresh_token = data is not None

        # Return proper error responses on invalid conditions
        if not (is_valid_client_id and is_valid_client_secret):
            return self._make_json_error_response('invalid_client')

        if not is_valid_scope:
            return self._make_json_error_response('invalid_scope')

        if not is_valid_refresh_token:
            return self._make_json_error_response('invalid_grant')

        # Discard original refresh token
        self.discard_refresh_token(client_id, refresh_token)

        # Generate access tokens once all conditions have been met
        access_token = self.generate_access_token()
        token_type = self.token_type
        expires_in = self.token_expires_in
        refresh_token = self.generate_refresh_token()

        # Save information to be used to validate later requests
        self.persist_token_information(client_id=client_id,
                                       scope=scope,
                                       access_token=access_token,
                                       token_type=token_type,
                                       expires_in=expires_in,
                                       refresh_token=refresh_token,
                                       data=data)

        # Return json response
        return self._make_json_response({
            'access_token': access_token,
            'token_type': token_type,
            'expires_in': expires_in,
            'refresh_token': refresh_token
        })

    def get_token(self,
                  grant_type,
                  client_id,
                  client_secret,
                  redirect_uri,
                  code,
                  **params):
        """Generate access token HTTP response.

        :param grant_type: Desired grant type. Must be "authorization_code".
        :type grant_type: str
        :param client_id: Client ID.
        :type client_id: str
        :param client_secret: Client secret.
        :type client_secret: str
        :param redirect_uri: Client redirect URI.
        :type redirect_uri: str
        :param code: Authorization code.
        :type code: str
        :rtype: requests.Response
        """

        # Ensure proper grant_type
        if grant_type != 'authorization_code':
            return self._make_json_error_response('unsupported_grant_type')

        # Check conditions
        is_valid_client_id = self.validate_client_id(client_id)
        is_valid_client_secret = self.validate_client_secret(client_id,
                                                             client_secret)
        is_valid_redirect_uri = self.validate_redirect_uri(client_id,
                                                           redirect_uri)

        scope = params.get('scope', '')
        is_valid_scope = self.validate_scope(client_id, scope)
        data = self.from_authorization_code(client_id, code, scope)
        is_valid_grant = data is not None

        # Return proper error responses on invalid conditions
        if not (is_valid_client_id and is_valid_client_secret):
            return self._make_json_error_response('invalid_client')

        if not is_valid_grant or not is_valid_redirect_uri:
            return self._make_json_error_response('invalid_grant')

        if not is_valid_scope:
            return self._make_json_error_response('invalid_scope')

        # Discard original authorization code
        self.discard_authorization_code(client_id, code)

        # Generate access tokens once all conditions have been met
        access_token = self.generate_access_token()
        token_type = self.token_type
        expires_in = self.token_expires_in
        refresh_token = self.generate_refresh_token()

        # Save information to be used to validate later requests
        self.persist_token_information(client_id=client_id,
                                       scope=scope,
                                       access_token=access_token,
                                       token_type=token_type,
                                       expires_in=expires_in,
                                       refresh_token=refresh_token,
                                       data=data)

        # Return json response
        return self._make_json_response({
            'access_token': access_token,
            'token_type': token_type,
            'expires_in': expires_in,
            'refresh_token': refresh_token
        })

    def get_authorization_code_from_uri(self, uri):
        """Get authorization code response from a URI. This method will
        ignore the domain and path of the request, instead
        automatically parsing the query string parameters.

        :param uri: URI to parse for authorization information.
        :type uri: str
        :rtype: requests.Response
        """
        params = utils.url_query_params(uri)
        try:
            if 'response_type' not in params:
                raise TypeError('Missing parameter response_type in URL query')

            if 'client_id' not in params:
                raise TypeError('Missing parameter client_id in URL query')

            if 'redirect_uri' not in params:
                raise TypeError('Missing parameter redirect_uri in URL query')

            return self.get_authorization_code(**params)
        except TypeError as exc:
            self._handle_exception(exc)

            # Catch missing parameters in request
            err = 'invalid_request'
            if 'redirect_uri' in params:
                u = params['redirect_uri']
                return self._make_redirect_error_response(u, err)
            else:
                return self._invalid_redirect_uri_response()
        except StandardError as exc:
            self._handle_exception(exc)

            # Catch all other server errors
            err = 'server_error'
            u = params['redirect_uri']
            return self._make_redirect_error_response(u, err)

    def get_token_from_post_data(self, data):
        """Get a token response from POST data.

        :param data: POST data containing authorization information.
        :type data: dict
        :rtype: requests.Response
        """
        try:
            # Verify OAuth 2.0 Parameters
            for x in ['grant_type', 'client_id', 'client_secret']:
                if not data.get(x):
                    raise TypeError("Missing required OAuth 2.0 POST param: {0}".format(x))
            
            # Handle get token from refresh_token
            if 'refresh_token' in data:
                return self.refresh_token(**data)

            # Handle get token from authorization code
            for x in ['redirect_uri', 'code']:
                if not data.get(x):
                    raise TypeError("Missing required OAuth 2.0 POST param: {0}".format(x))            
            return self.get_token(**data)
        except TypeError as exc:
            self._handle_exception(exc)

            # Catch missing parameters in request
            return self._make_json_error_response('invalid_request')
        except StandardError as exc:
            self._handle_exception(exc)

            # Catch all other server errors
            return self._make_json_error_response('server_error')

    def validate_client_id(self, client_id):
        raise NotImplementedError('Subclasses must implement ' \
                                  'validate_client_id.')

    def validate_client_secret(self, client_id, client_secret):
        raise NotImplementedError('Subclasses must implement ' \
                                  'validate_client_secret.')

    def validate_redirect_uri(self, client_id, redirect_uri):
        raise NotImplementedError('Subclasses must implement ' \
                                  'validate_redirect_uri.')

    def validate_scope(self, client_id, scope):
        raise NotImplementedError('Subclasses must implement ' \
                                  'validate_scope.')

    def validate_access(self):
        raise NotImplementedError('Subclasses must implement ' \
                                  'validate_access.')

    def from_authorization_code(self, client_id, code, scope):
        raise NotImplementedError('Subclasses must implement ' \
                                  'from_authorization_code.')

    def from_refresh_token(self, client_id, refresh_token, scope):
        raise NotImplementedError('Subclasses must implement ' \
                                  'from_refresh_token.')

    def persist_authorization_code(self, client_id, code, scope):
        raise NotImplementedError('Subclasses must implement ' \
                                  'persist_authorization_code.')

    def persist_token_information(self, client_id, scope, access_token,
                                  token_type, expires_in, refresh_token,
                                  data):
        raise NotImplementedError('Subclasses must implement ' \
                                  'persist_token_information.')

    def discard_authorization_code(self, client_id, code):
        raise NotImplementedError('Subclasses must implement ' \
                                  'discard_authorization_code.')

    def discard_refresh_token(self, client_id, refresh_token):
        raise NotImplementedError('Subclasses must implement ' \
                                  'discard_refresh_token.')


class OAuthError(Unauthorized):
    """OAuth error, including the OAuth error reason."""
    def __init__(self, reason, *args, **kwargs):
        self.reason = reason
        super(OAuthError, self).__init__(*args, **kwargs)


class ResourceAuthorization(object):
    """A class containing an OAuth 2.0 authorization."""
    is_oauth = False
    is_valid = None
    token = None
    client_id = None
    expires_in = None
    error = None

    def raise_error_if_invalid(self):
        if not self.is_valid:
            raise OAuthError(self.error, 'OAuth authorization error')


class ResourceProvider(Provider):
    """OAuth 2.0 resource provider. This class provides an interface
    to validate an incoming request and authenticate resource access.
    Certain methods MUST be overridden in a subclass, thus this
    class cannot be directly used as a resource provider.

    These are the methods that must be implemented in a subclass:

        get_authorization_header(self)
            # Return header string for key "Authorization" or None

        validate_access_token(self, access_token, authorization)
            # Set is_valid=True, client_id, and expires_in attributes
            #   on authorization if authorization was successful.
            # Return value is ignored
    """

    @property
    def authorization_class(self):
        return ResourceAuthorization

    def get_authorization(self):
        """Get authorization object representing status of authentication."""
        auth = self.authorization_class()
        header = self.get_authorization_header()
        if not header or not header.split:
            return auth
        header = header.split()
        if len(header) > 1 and header[0] == 'Bearer':
            auth.is_oauth = True
            access_token = header[1]
            self.validate_access_token(access_token, auth)
            if not auth.is_valid:
                auth.error = 'access_denied'
        return auth

    def get_authorization_header(self):
        raise NotImplementedError('Subclasses must implement ' \
                                  'get_authorization_header.')

    def validate_access_token(self, access_token, authorization):
        raise NotImplementedError('Subclasses must implement ' \
                                  'validate_token.')

########NEW FILE########
__FILENAME__ = test_client
from __future__ import absolute_import
import unittest
from pyoauth2.client import Client
from pyoauth2 import utils


class ClientTest(unittest.TestCase):

    def setUp(self):

        self.client = Client(client_id='some.client',
                             client_secret='ASDFGHJKL',
                             redirect_uri='https://example.com/pyoauth2redirect',
                             authorization_uri='https://grapheffect.com/pyoauth2/auth',
                             token_uri='https://grapheffect.com/pyoauth2/token')

    def test_get_authorization_code_uri(self):
        """Test client generation of authorization code uri."""
        uri = self.client.get_authorization_code_uri(state="app.state")

        # Check URI
        self.assertTrue(uri.startswith('https://grapheffect.com/pyoauth2/auth?'))

        # Check params
        params = utils.url_query_params(uri)
        self.assertEquals('code', params['response_type'])
        self.assertEquals('some.client', params['client_id'])
        self.assertEquals('https://example.com/pyoauth2redirect', params['redirect_uri'])
        self.assertEquals('app.state', params['state'])

########NEW FILE########
__FILENAME__ = test_integration
from __future__ import absolute_import
import unittest
from pyoauth2.provider import AuthorizationProvider
from pyoauth2.client import Client
from pyoauth2 import utils

MOCK_CLIENT_ID = 'abc123456789'
MOCK_CLIENT_SECRET = 'MNBVCXZLKJHGFDSAPOIUYTREWQ'
MOCK_REDIRECT_URI = 'https://grapheffect.com/oauth_endpoint'
MOCK_AUTHORIZATION_CODE = 'poiuytrewqlkjhgfdsamnbvcxz0987654321'
MOCK_REFRESH_TOKEN = 'uhbygvtfcrdxeszokmijn'


class MockClient(Client):

    def http_post(self, url, data=None):
        if url.startswith('https://example.com/token'):
            return self.mock_provider_get_token_from_post_data(data)

        raise Exception('Test fail')


class MockAuthorizationProvider(AuthorizationProvider):
    """Implement an authorization pyoauth2 provider for testing purposes."""

    def validate_client_id(self, client_id):
        return client_id == MOCK_CLIENT_ID

    def validate_client_secret(self, client_id, client_secret):
        return client_id == MOCK_CLIENT_ID and client_secret == MOCK_CLIENT_SECRET

    def validate_scope(self, client_id, scope):
        requested_scopes = scope.split()
        if client_id == MOCK_CLIENT_ID and requested_scopes == ['example']:
            return True
        return False

    def validate_redirect_uri(self, client_id, redirect_uri):
        return redirect_uri.startswith(MOCK_REDIRECT_URI)

    def from_authorization_code(self, client_id, code, scope):
        if code == MOCK_AUTHORIZATION_CODE:
            return {'session': '12345'}
        return None

    def from_refresh_token(self, client_id, refresh_token, scope):
        if refresh_token == MOCK_REFRESH_TOKEN:
            return {'session': '56789'}
        return None

    def validate_access(self):
        return True

    def persist_authorization_code(self, client_id, code, scope):
        pass

    def persist_token_information(self, client_id, scope, access_token,
                                  token_type, expires_in, refresh_token,
                                  data):
        pass

    def discard_authorization_code(self, client_id, code):
        pass

    def discard_refresh_token(self, client_id, refresh_token):
        pass


class IntegrationTest(unittest.TestCase):

    def setUp(self):
        self.provider = MockAuthorizationProvider()
        self.client = MockClient(client_id=MOCK_CLIENT_ID,
                                 client_secret=MOCK_CLIENT_SECRET,
                                 authorization_uri='https://example.com/auth',
                                 token_uri='https://example.com/token',
                                 redirect_uri=MOCK_REDIRECT_URI + '?param=123')

        self.client.mock_provider_get_token_from_post_data = \
            self.provider.get_token_from_post_data

    def test_get_authorization_code(self):
        """Test client's auth code URI generation and provider's response."""
        uri = self.client.get_authorization_code_uri(scope='example')
        response = self.provider.get_authorization_code_from_uri(uri)

        # Check status code
        self.assertEquals(302, response.status_code)

        # Check the non-query portion of the redirect URL
        redirect = response.headers['Location']
        self.assertEquals(utils.url_dequery(redirect), MOCK_REDIRECT_URI)

        # Check params in the redirect URL
        params = utils.url_query_params(redirect)
        self.assertEquals(3, len(params))
        self.assertEquals(40, len(params['code']))
        self.assertEquals('123', params['param'])
        self.assertEquals('example', params['scope'])

    def test_get_token_with_valid_authorization_code(self):
        """Test client's ability to get an access token from the provider."""
        data = self.client.get_token(code=MOCK_AUTHORIZATION_CODE,
                                     scope='example')

        self.assertEquals(40, len(data['access_token']))
        self.assertEquals(40, len(data['refresh_token']))
        self.assertEquals('Bearer', data['token_type'])
        self.assertEquals(3600, data['expires_in'])

########NEW FILE########
__FILENAME__ = test_provider
from __future__ import absolute_import
import unittest
from pyoauth2.provider import AuthorizationProvider


class MockAuthorizationProvider(AuthorizationProvider):
    pass


class AuthorizationProviderTest(unittest.TestCase):

    def setUp(self):
        self.provider = MockAuthorizationProvider()

    def test_make_redirect_error_response(self):

        response = self.provider._make_redirect_error_response(
            'https://test.example.com/oauthredirect?param=1234',
            'some_error')
        self.assertEquals(302, response.status_code)
        self.assertEquals('https://test.example.com/oauthredirect?'
                          'param=1234&error=some_error',
                          response.headers['Location'])

    def test_make_json_error_response(self):

        response = self.provider._make_json_error_response('some_error')
        self.assertEquals(400, response.status_code)
        try:
            response_json = response.json()
        except TypeError:
            response_json = response.json
        self.assertEquals({'error': 'some_error'}, response_json)

    def test_get_authorization_code_invalid_response_type(self):

        response = self.provider.get_authorization_code('foo', 'client12345',
                                               'https://example.com/oauth')

        self.assertEquals(302, response.status_code)
        self.assertEquals('https://example.com/oauth?'
                          'error=unsupported_response_type',
                          response.headers['Location'])

########NEW FILE########
__FILENAME__ = test_utils
from __future__ import absolute_import
import unittest
from pyoauth2 import utils


class UtilsTest(unittest.TestCase):

    def setUp(self):
        self.base_url = 'https://www.grapheffect.com/some/path;hello?c=30&b=2&a=10'

    def test_random_ascii_string(self):
        """Test that random_ascii_string generates string of correct length."""
        code = utils.random_ascii_string(25)

        self.assertEquals(25, len(code))

    def test_url_query_params(self):
        """Test get query parameters dict."""
        result = utils.url_query_params(self.base_url)

        self.assertEquals(result, {'c': '30', 'b': '2', 'a': '10'})

    def test_url_dequery(self):
        """Test url dequery removes query portion of URL."""
        result = utils.url_dequery(self.base_url)

        self.assertEquals(result, 'https://www.grapheffect.com/some/path;hello')

    def test_build_url(self):
        """Test that build_url properly adds query parameters."""
        result = utils.build_url(self.base_url, {'b': 20})

        # Note param ordering and correct new value for b
        self.assertEquals(result, 'https://www.grapheffect.com/some/path;hello?a=10&c=30&b=20')

########NEW FILE########
__FILENAME__ = utils
import string
import urllib
import urlparse
from Crypto.Random import random

UNICODE_ASCII_CHARACTERS = (string.ascii_letters.decode('ascii') +
    string.digits.decode('ascii'))


def random_ascii_string(length):
    return ''.join([random.choice(UNICODE_ASCII_CHARACTERS) for x in xrange(length)])


def url_query_params(url):
    """Return query parameters as a dict from the specified URL.

    :param url: URL.
    :type url: str
    :rtype: dict
    """
    return dict(urlparse.parse_qsl(urlparse.urlparse(url).query, True))


def url_dequery(url):
    """Return a URL with the query component removed.

    :param url: URL to dequery.
    :type url: str
    :rtype: str
    """
    url = urlparse.urlparse(url)
    return urlparse.urlunparse((url.scheme,
                                url.netloc,
                                url.path,
                                url.params,
                                '',
                                url.fragment))


def build_url(base, additional_params=None):
    """Construct a URL based off of base containing all parameters in
    the query portion of base plus any additional parameters.

    :param base: Base URL
    :type base: str
    ::param additional_params: Additional query parameters to include.
    :type additional_params: dict
    :rtype: str
    """
    url = urlparse.urlparse(base)
    query_params = {}
    query_params.update(urlparse.parse_qsl(url.query, True))
    if additional_params is not None:
        query_params.update(additional_params)
        for k, v in additional_params.iteritems():
            if v is None:
                query_params.pop(k)

    return urlparse.urlunparse((url.scheme,
                                url.netloc,
                                url.path,
                                url.params,
                                urllib.urlencode(query_params),
                                url.fragment))

########NEW FILE########
