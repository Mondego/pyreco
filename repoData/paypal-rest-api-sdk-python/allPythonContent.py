__FILENAME__ = api
from __future__ import division

import base64
import datetime
import requests
import json
import logging
import os
import platform

import paypalrestsdk.util as util
from paypalrestsdk import exceptions
from paypalrestsdk.version import __version__


class Api(object):

    # User-Agent for HTTP request
    library_details = "requests %s; python %s" % (requests.__version__, platform.python_version())
    user_agent = "PayPalSDK/rest-sdk-python %s (%s)" % (__version__, library_details)

    def __init__(self, options=None, **kwargs):
        """Create API object

        Usage::

            >>> import paypalrestsdk
            >>> api = paypalrestsdk.Api(mode="sandbox", client_id='CLIENT_ID', client_secret='CLIENT_SECRET', ssl_options={"cert": "/path/to/server.pem"})
        """
        kwargs = util.merge_dict(options or {}, kwargs)

        self.mode = kwargs.get("mode", "sandbox")
        self.endpoint = kwargs.get("endpoint", self.default_endpoint())
        self.token_endpoint = kwargs.get("token_endpoint", self.endpoint)
        self.client_id = kwargs["client_id"]              # Mandatory parameter, so not using `dict.get`
        self.client_secret = kwargs["client_secret"]      # Mandatory parameter, so not using `dict.get`
        self.proxies = kwargs.get("proxies", None)
        self.token_hash = None
        self.token_request_at = None
        # setup SSL certificate verification if private certificate provided
        ssl_options = kwargs.get("ssl_options", {})
        if "cert" in ssl_options:
            os.environ["REQUESTS_CA_BUNDLE"] = ssl_options["cert"]

        if kwargs.get("token"):
            self.token_hash = {"access_token": kwargs["token"], "token_type": "Bearer"}

        self.options = kwargs

    def default_endpoint(self):
        if self.mode == "live":
            return "https://api.paypal.com"
        else:
            return "https://api.sandbox.paypal.com"

    def basic_auth(self):
        """Find basic auth, and returns base64 encoded
        """
        credentials = "%s:%s" % (self.client_id, self.client_secret)
        return base64.b64encode(credentials.encode('utf-8')).decode('utf-8').replace("\n", "")

    def get_token_hash(self, authorization_code=None, refresh_token=None):
        """Generate new token by making a POST request

            1. By using client credentials if validate_token_hash finds
            token to be invalid. This is useful during web flow so that an already
            authenticated user is not reprompted for login
            2. Exchange authorization_code from mobile device for a long living
            refresh token that can be used to charge user who has consented to future
            payments
            3. Exchange refresh_token for the user for a access_token of type Bearer
            which can be passed in to charge user

        """
        path = "/v1/oauth2/token"
        payload = "grant_type=client_credentials"

        if authorization_code is not None:
            payload = "grant_type=authorization_code&response_type=token&redirect_uri=urn:ietf:wg:oauth:2.0:oob&code=" + authorization_code

        elif refresh_token is not None:
            payload = "grant_type=refresh_token&refresh_token=" + refresh_token

        else:
            self.validate_token_hash()
            if self.token_hash is not None:
                return self.token_hash
            else:
                self.token_request_at = datetime.datetime.now()

        self.token_hash = self.http_call(
            util.join_url(self.token_endpoint, path), "POST",
            data=payload,
            headers={
                "Authorization": ("Basic %s" % self.basic_auth()),
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json", "User-Agent": self.user_agent
            })

        return self.token_hash

    def validate_token_hash(self):
        """Checks if token duration has expired and if so resets token
        """
        if self.token_request_at and self.token_hash and self.token_hash.get("expires_in") is not None:
            delta = datetime.datetime.now() - self.token_request_at
            duration = (delta.microseconds + (delta.seconds + delta.days * 24 * 3600) * 10**6) / 10**6
            if duration > self.token_hash.get("expires_in"):
                self.token_hash = None

    def get_refresh_token(self, authorization_code=None):
        if authorization_code is None:
            raise exceptions.MissingConfig("Authorization code needed to get new refresh token. Refer to https://developer.paypal.com/docs/integration/mobile/make-future-payment/#get-an-auth-code")
        return self.get_token_hash(authorization_code)["refresh_token"]

    def request(self, url, method, body=None, headers=None, refresh_token=None):
        """Make HTTP call, formats response and does error handling. Uses http_call method in API class.

        Usage::

            >>> api.request("https://api.sandbox.paypal.com/v1/payments/payment?count=10", "GET", {})
            >>> api.request("https://api.sandbox.paypal.com/v1/payments/payment", "POST", "{}", {} )

        """

        http_headers = util.merge_dict(self.headers(refresh_token=refresh_token), headers or {})

        if http_headers.get('PayPal-Request-Id'):
            logging.info('PayPal-Request-Id: %s' % (http_headers['PayPal-Request-Id']))

        try:
            return self.http_call(url, method, data=json.dumps(body), headers=http_headers)

        # Format Error message for bad request
        except exceptions.BadRequest as error:
            return {"error": json.loads(error.content)}

        # Handle Expired token
        except exceptions.UnauthorizedAccess as error:
            if(self.token_hash and self.client_id):
                self.token_hash = None
                return self.request(url, method, body, headers)
            else:
                raise error

    def http_call(self, url, method, **kwargs):
        """
        Makes a http call. Logs response information.
        """
        logging.info('Request[%s]: %s' % (method, url))
        start_time = datetime.datetime.now()

        response = requests.request(method, url, proxies=self.proxies, **kwargs)

        duration = datetime.datetime.now() - start_time
        logging.info('Response[%d]: %s, Duration: %s.%ss.' % (response.status_code, response.reason, duration.seconds, duration.microseconds))
        debug_id = response.headers.get('PayPal-Debug-Id')
        if debug_id:
            logging.debug('debug_id: %s' % debug_id)

        return self.handle_response(response, response.content.decode('utf-8'))

    def handle_response(self, response, content):
        """Validate HTTP response
        """
        status = response.status_code
        if status in (301, 302, 303, 307):
            raise exceptions.Redirection(response, content)
        elif 200 <= status <= 299:
            return json.loads(content) if content else {}
        elif status == 400:
            raise exceptions.BadRequest(response, content)
        elif status == 401:
            raise exceptions.UnauthorizedAccess(response, content)
        elif status == 403:
            raise exceptions.ForbiddenAccess(response, content)
        elif status == 404:
            raise exceptions.ResourceNotFound(response, content)
        elif status == 405:
            raise exceptions.MethodNotAllowed(response, content)
        elif status == 409:
            raise exceptions.ResourceConflict(response, content)
        elif status == 410:
            raise exceptions.ResourceGone(response, content)
        elif status == 422:
            raise exceptions.ResourceInvalid(response, content)
        elif 401 <= status <= 499:
            raise exceptions.ClientError(response, content)
        elif 500 <= status <= 599:
            raise exceptions.ServerError(response, content)
        else:
            raise exceptions.ConnectionError(response, content, "Unknown response code: #{response.code}")

    def headers(self, refresh_token=None):
        """Default HTTP headers
        """
        token_hash = self.get_token_hash(refresh_token=refresh_token)

        return {
            "Authorization": ("%s %s" % (token_hash['token_type'], token_hash['access_token'])),
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": self.user_agent
        }

    def get(self, action, headers=None):
        """Make GET request

        Usage::

            >>> api.get("v1/payments/payment?count=1")
            >>> api.get("v1/payments/payment/PAY-1234")
        """
        return self.request(util.join_url(self.endpoint, action), 'GET', headers=headers or {})

    def post(self, action, params=None, headers=None, refresh_token=None):
        """Make POST request

        Usage::

            >>> api.post("v1/payments/payment", { 'indent': 'sale' })
            >>> api.post("v1/payments/payment/PAY-1234/execute", { 'payer_id': '1234' })

        """
        return self.request(util.join_url(self.endpoint, action), 'POST', body=params or {}, headers=headers or {}, refresh_token=refresh_token)

    def put(self, action, params=None, headers=None, refresh_token=None):
        """Make PUT request
        """
        return self.request(util.join_url(self.endpoint, action), 'PUT', body=params or {}, headers=headers or {}, refresh_token=refresh_token)

    def delete(self, action, headers=None):
        """Make DELETE request
        """
        return self.request(util.join_url(self.endpoint, action), 'DELETE', headers=headers or {})

__api__ = None


def default():
    """Returns default api object and if not present creates a new one
    By default points to developer sandbox
    """
    global __api__
    if __api__ is None:
        try:
            client_id = os.environ["PAYPAL_CLIENT_ID"]
            client_secret = os.environ["PAYPAL_CLIENT_SECRET"]
        except KeyError:
            raise exceptions.MissingConfig("Required PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET. Refer https://github.com/paypal/rest-api-sdk-python#configuration")

        __api__ = Api(mode=os.environ.get("PAYPAL_MODE", "sandbox"), client_id=client_id, client_secret=client_secret)
    return __api__


def set_config(options=None, **config):
    """Create new default api object with given configuration
    """
    global __api__
    __api__ = Api(options or {}, **config)
    return __api__

configure = set_config

########NEW FILE########
__FILENAME__ = exceptions

class ConnectionError(Exception):
    def __init__(self, response, content=None, message=None):
        self.response = response
        self.content = content
        self.message = message

    def __str__(self):
        message = "Failed."
        if hasattr(self.response, 'status_code'):
            message += " Response status: %s." % (self.response.status_code)
        if hasattr(self.response, 'reason'):
            message += " Response message: %s." % (self.response.reason)
        if self.content is not None:
            message += " Error message: " + str(self.content)
        return message


class Redirection(ConnectionError):
    """3xx Redirection
    """
    def __str__(self):
        message = super(Redirection, self).__str__()
        if self.response.get('Location'):
            message = "%s => %s" % (message, self.response.get('Location'))
        return message


class MissingParam(TypeError):
    pass


class MissingConfig(Exception):
    pass


class ClientError(ConnectionError):
    """4xx Client Error
    """
    pass


class BadRequest(ClientError):
    """400 Bad Request
    """
    pass


class UnauthorizedAccess(ClientError):
    """401 Unauthorized
    """
    pass


class ForbiddenAccess(ClientError):
    """403 Forbidden
    """
    pass


class ResourceNotFound(ClientError):
    """404 Not Found
    """
    pass


class ResourceConflict(ClientError):
    """409 Conflict
    """
    pass


class ResourceGone(ClientError):
    """410 Gone
    """
    pass


class ResourceInvalid(ClientError):
    """422 Invalid
    """
    pass


class ServerError(ConnectionError):
    """5xx Server Error
    """
    pass


class MethodNotAllowed(ClientError):
    """405 Method Not Allowed
    """

    def allowed_methods(self):
        return self.response['Allow']

########NEW FILE########
__FILENAME__ = invoices
import paypalrestsdk.util as util
from paypalrestsdk.resource import List, Find, Delete, Create, Update, Post, Resource
from paypalrestsdk.api import default as default_api

class Invoice(List, Find, Create, Delete, Update, Post):
    """Invoice class wrapping the REST v1/invoices/invoice endpoint

    Usage::

        >>> invoice_histroy = Invoice.all({"count": 5})

        >>> invoice = Invoice.new({})
        >>> invoice.create()     # return True or False
    """
    path = "v1/invoicing/invoices"

    def send(self):
        return self.post('send', {}, self)

    def remind(self, attributes):
        return self.post('remind', attributes, self)

    def cancel(self, attributes):
        return self.post('cancel', attributes, self)

    @classmethod
    def search(cls, params=None, api=None):
        api = api or default_api()
        params = params or {}

        url = util.join_url(cls.path, 'search')

        return Resource(api.post(url, params), api=api)

Invoice.convert_resources['invoices'] = Invoice
Invoice.convert_resources['invoice'] = Invoice

########NEW FILE########
__FILENAME__ = openid_connect
from paypalrestsdk.resource import Resource
import paypalrestsdk.util as util
import paypalrestsdk.api as api
from paypalrestsdk.version import __version__
from six import string_types


class Base(Resource):

    user_agent = "PayPalSDK/openid-connect-python %s (%s)" % (__version__, api.Api.library_details)

    @classmethod
    def post(cls, action, options=None, headers=None):
        url = util.join_url(endpoint(), action)
        body = util.urlencode(options or {})
        headers = util.merge_dict({
            'User-Agent': cls.user_agent,
            'Content-Type': 'application/x-www-form-urlencoded'}, headers or {})
        data = api.default().http_call(url, 'POST', data=body, headers=headers)
        return cls(data)


class Tokeninfo(Base):
    """Token service for Log In with PayPal, API docs at
    https://developer.paypal.com/docs/api/#identity
    """

    path = "v1/identity/openidconnect/tokenservice"

    @classmethod
    def create(cls, options=None):
        options = options or {}
        if isinstance(options, string_types):
            options = {'code': options}

        options = util.merge_dict({
            'grant_type': 'authorization_code',
            'client_id': client_id(),
            'client_secret': client_secret()
        }, options)

        return cls.post(cls.path, options)

    @classmethod
    def create_with_refresh_token(cls, options=None):
        options = options or {}
        if isinstance(options, string_types):
            options = {'refresh_token': options}

        options = util.merge_dict({
            'grant_type': 'refresh_token',
            'client_id': client_id(),
            'client_secret': client_secret()
        }, options)

        return cls.post(cls.path, options)

    @classmethod
    def authorize_url(cls, options=None):
        return authorize_url(options or {})

    def logout_url(self, options=None):
        return logout_url(util.merge_dict({'id_token': self.id_token}, options or {}))

    def refresh(self, options=None):
        options = util.merge_dict({'refresh_token': self.refresh_token}, options or {})
        tokeninfo = self.__class__.create_with_refresh_token(options)
        self.merge(tokeninfo.to_dict())
        return self

    def userinfo(self, options=None):
        return Userinfo.get(util.merge_dict({'access_token': self.access_token}, options or {}))


class Userinfo(Base):
    """Retrive user profile attributes for Log In with PayPal
    """

    path = "v1/identity/openidconnect/userinfo"

    @classmethod
    def get(cls, options=None):
        options = options or {}
        if isinstance(options, string_types):
            options = {'access_token': options}
        options = util.merge_dict({'schema': 'openid'}, options)

        return cls.post(cls.path, options)


def endpoint():
    return api.default().options.get("openid_endpoint", api.default().endpoint)


def client_id():
    return api.default().options.get("openid_client_id", api.default().client_id)


def client_secret():
    return api.default().options.get("openid_client_secret", api.default().client_secret)


def redirect_uri():
    return api.default().options.get("openid_redirect_uri")


start_session_path = "/webapps/auth/protocol/openidconnect/v1/authorize"
end_session_path = "/webapps/auth/protocol/openidconnect/v1/endsession"


def session_url(path, options=None):
    if api.default().mode == "live":
        path = util.join_url("https://www.paypal.com", path)
    else:
        path = util.join_url("https://www.sandbox.paypal.com", path)
    return util.join_url_params(path, options or {})


def authorize_url(options=None):
    options = util.merge_dict({
        'response_type': 'code',
        'scope': 'openid',
        'client_id': client_id(),
        'redirect_uri': redirect_uri()
    }, options or {})
    return session_url(start_session_path, options)


def logout_url(options=None):
    options = util.merge_dict({
        'logout': 'true',
        'redirect_uri': redirect_uri()
    }, options or {})
    return session_url(end_session_path, options)

########NEW FILE########
__FILENAME__ = payments
from paypalrestsdk.resource import List, Find, Create, Post


class Payment(List, Find, Create, Post):
    """Payment class wrapping the REST v1/payments/payment endpoint

    Usage::

        >>> payment_histroy = Payment.all({"count": 5})
        >>> payment = Payment.find("PAY-1234")
        >>> payment = Payment.new({"intent": "sale"})
        >>> payment.create()     # return True or False
        >>> payment.execute({"payer_id": 1234})  # return True or False
    """
    path = "v1/payments/payment"

    def execute(self, attributes):
        return self.post('execute', attributes, self)

Payment.convert_resources['payments'] = Payment
Payment.convert_resources['payment'] = Payment


class Sale(Find, Post):
    """Sale class wrapping the REST v1/payments/sale endpoint

    Usage::

        >>> sale = Sale.find("98765432")
        >>> refund = sale.refund({"amount": {"total": "1.00", "currency": "USD"}})
        >>> refund.success()   # return True or False
    """
    path = "v1/payments/sale"

    def refund(self, attributes):
        return self.post('refund', attributes, Refund)

Sale.convert_resources['sales'] = Sale
Sale.convert_resources['sale'] = Sale


class Refund(Find):
    """Get details for a refund on direct or captured payment

    Usage::

        >>> refund = Refund.find("12345678")
    """
    path = "v1/payments/refund"

Refund.convert_resources['refund'] = Refund


class Authorization(Find, Post):
    """Enables looking up, voiding and capturing authorization and reauthorize payments

    Helpful links::
    https://developer.paypal.com/docs/api/#authorizations
    https://developer.paypal.com/docs/integration/direct/capture-payment/#authorize-the-payment

    Usage::

        >>> authorization = Authorization.find("")
        >>> capture = authorization.capture({ "amount": { "currency": "USD", "total": "1.00" } })
        >>> authorization.void() # return True or False
    """
    path = "v1/payments/authorization"

    def capture(self, attributes):
        return self.post('capture', attributes, Capture)

    def void(self):
        return self.post('void', {}, self)

    def reauthorize(self):
        return self.post('reauthorize', self, self)

Authorization.convert_resources['authorization'] = Authorization


class Capture(Find, Post):
    """Look up and refund captured payments, wraps v1/payments/capture

    Usage::

        >>> capture = Capture.find("")
        >>> refund = capture.refund({ "amount": { "currency": "USD", "total": "1.00" }})
    """
    path = "v1/payments/capture"

    def refund(self, attributes):
        return self.post('refund', attributes, Refund)

Capture.convert_resources['capture'] = Capture

########NEW FILE########
__FILENAME__ = resource
import uuid

import paypalrestsdk.util as util
from paypalrestsdk.api import default as default_api


class Resource(object):
    """Base class for all REST services
    """
    convert_resources = {}

    def __init__(self, attributes=None, api=None):
        attributes = attributes or {}
        self.__dict__['api'] = api or default_api()

        super(Resource, self).__setattr__('__data__', {})
        super(Resource, self).__setattr__('error', None)
        super(Resource, self).__setattr__('headers', {})
        super(Resource, self).__setattr__('header', {})
        super(Resource, self).__setattr__('request_id', None)
        self.merge(attributes)

    def generate_request_id(self):
        """Generate uniq request id
        """
        if self.request_id is None:
            self.request_id = str(uuid.uuid4())
        return self.request_id

    def http_headers(self):
        """Generate HTTP header
        """
        return util.merge_dict(self.header, self.headers,
                               {'PayPal-Request-Id': self.generate_request_id()})

    def __str__(self):
        return self.__data__.__str__()

    def __repr__(self):
        return self.__data__.__str__()

    def __getattr__(self, name):
        return self.__data__.get(name)

    def __setattr__(self, name, value):
        try:
            # Handle attributes(error, header, request_id)
            super(Resource, self).__getattribute__(name)
            super(Resource, self).__setattr__(name, value)
        except AttributeError:
            self.__data__[name] = self.convert(name, value)

    def success(self):
        return self.error is None

    def merge(self, new_attributes):
        """Merge new attributes e.g. response from a post to Resource
        """
        for k, v in new_attributes.items():
            setattr(self, k, v)

    def convert(self, name, value):
        """Convert the attribute values to configured class
        """
        if isinstance(value, dict):
            cls = self.convert_resources.get(name, Resource)
            return cls(value, api=self.api)
        elif isinstance(value, list):
            new_list = []
            for obj in value:
                new_list.append(self.convert(name, obj))
            return new_list
        else:
            return value

    def __getitem__(self, key):
        return self.__data__[key]

    def __setitem__(self, key, value):
        self.__data__[key] = self.convert(key, value)

    def to_dict(self):

        def parse_object(value):
            if isinstance(value, Resource):
                return value.to_dict()
            elif isinstance(value, list):
                new_list = []
                for obj in value:
                    new_list.append(parse_object(obj))
                return new_list
            else:
                return value

        data = {}
        for key in self.__data__:
            data[key] = parse_object(self.__data__[key])
        return data


class Find(Resource):

    @classmethod
    def find(cls, resource_id, api=None):
        """Locate resource e.g. payment with given id

        Usage::
            >>> payment = Payment.find("PAY-1234")
        """
        api = api or default_api()

        url = util.join_url(cls.path, str(resource_id))
        return cls(api.get(url), api=api)


class List(Resource):

    list_class = Resource

    @classmethod
    def all(cls, params=None, api=None):
        """Get list of payments as on
        https://developer.paypal.com/docs/api/#list-payment-resources

        Usage::

            >>> payment_histroy = Payment.all({'count': 2})
        """
        api = api or default_api()

        if params is None:
            url = cls.path
        else:
            url = util.join_url_params(cls.path, params)
        return cls.list_class(api.get(url), api=api)


class Create(Resource):

    def create(self, refresh_token=None, correlation_id=None):
        """Creates a resource e.g. payment

        Usage::

            >>> payment = Payment({})
            >>> payment.create() # return True or False
        """

        headers = {}
        if correlation_id is not None:
            headers = util.merge_dict(
                self.http_headers(),
                {'Paypal-Application-Correlation-Id': correlation_id}
            )
        else:
            headers = self.http_headers()

        new_attributes = self.api.post(self.path, self.to_dict(), headers, refresh_token)
        self.error = None
        self.merge(new_attributes)
        return self.success()

class Update(Resource):
    """ Update a resource

    Usage::

        >>> invoice.update()
    """

    def update(self, attributes=None, refresh_token=None):
        attributes = attributes or self.to_dict()
        url = util.join_url(self.path, str(self['id']))
        new_attributes = self.api.put(url, attributes, self.http_headers(), refresh_token)
        self.error = None
        self.merge(new_attributes)
        return self.success()

class Delete(Resource):

    def delete(self):
        """Deletes a resource e.g. credit_card

        Usage::

            >>> credit_card.delete()
        """
        url = util.join_url(self.path, str(self['id']))
        new_attributes = self.api.delete(url)
        self.error = None
        self.merge(new_attributes)
        return self.success()


class Post(Resource):

    def post(self, name, attributes=None, cls=Resource):
        """Constructs url with passed in headers and makes post request via
        post method in api class

        Usage::

            >>> payment.post("execute", {'payer_id': '1234'}, payment)  # return True or False
            >>> sale.post("refund", {'payer_id': '1234'})  # return Refund object
        """
        attributes = attributes or {}
        url = util.join_url(self.path, str(self['id']), name)
        if not isinstance(attributes, Resource):
            attributes = Resource(attributes, api=self.api)
        new_attributes = self.api.post(url, attributes.to_dict(), attributes.http_headers())
        if isinstance(cls, Resource):
            cls.error = None
            cls.merge(new_attributes)
            return self.success()
        else:
            return cls(new_attributes, api=self.api)

########NEW FILE########
__FILENAME__ = util
import re

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode


def join_url(url, *paths):
    """
    Joins individual URL strings together, and returns a single string.

    >>> util.join_url("example.com", "index.html")
    'example.com/index.html'
    """
    for path in paths:
        url = re.sub(r'/?$', re.sub(r'^/?', '/', path), url)
    return url


def join_url_params(url, params):
    return url + "?" + urlencode(params)


def merge_dict(data, *override):
    """
    Merges any number of dictionaries together, and returns a single dictionary

    >>> util.merge_dict ({"foo": "bar"}, {1: 2}, {"Pay": "Pal"})
    {1: 2, 'foo': 'bar', 'Pay': 'Pal'}
    >>>
    """
    result = {}
    for current_dict in (data,) + override:
        result.update(current_dict)
    return result

########NEW FILE########
__FILENAME__ = vault
from paypalrestsdk.resource import Find, Create, Delete


class CreditCard(Find, Create, Delete):
    """Use vault api to avoid having to store sensitive information
    such as credit card related details on your server. API docs at
    https://developer.paypal.com/docs/api/#vault

    Usage::

        >>> credit_card = CreditCard.find("CARD-5BT058015C739554AKE2GCEI")
        >>> credit_card = CreditCard.new({'type': 'visa'})

        >>> credit_card.create()  # return True or False
    """
    path = "v1/vault/credit-card"

CreditCard.convert_resources['credit_card'] = CreditCard

########NEW FILE########
__FILENAME__ = version
__version__ = "1.1.0"

########NEW FILE########
__FILENAME__ = capture
from paypalrestsdk import Authorization
import logging
logging.basicConfig(level=logging.INFO)

authorization = Authorization.find("5RA45624N3531924N")
capture = authorization.capture({
  "amount": {
    "currency": "USD",
    "total": "4.54" },
  "is_final_capture": True })

if capture.success():
  print("Capture[%s] successfully"%(capture.id))
else:
  print(capture.error)

########NEW FILE########
__FILENAME__ = find
from paypalrestsdk import Authorization, ResourceNotFound
import logging
logging.basicConfig(level=logging.INFO)

try:
  authorization = Authorization.find("99M58264FG144833V")
  print("Got Authorization details for Authorization[%s]"%(authorization.id))

except ResourceNotFound as error:
  print("Authorization Not Found")

########NEW FILE########
__FILENAME__ = reauthorize
from paypalrestsdk import Authorization

import logging
logging.basicConfig(level=logging.INFO)

authorization = Authorization.find("7GH53639GA425732B")

authorization.amount = {
  "currency": "USD",
  "total": "7.00" }

if authorization.reauthorize():
  print("Reauthorized[%s] successfully"%(authorization.id))
else:
  print(authorization.error)

########NEW FILE########
__FILENAME__ = void
from paypalrestsdk import Authorization
import logging
logging.basicConfig(level=logging.INFO)

authorization = Authorization.find("6CR34526N64144512")

if authorization.void():
  print("Void authorization successfully")
else:
  print(authorization.error)

########NEW FILE########
__FILENAME__ = find
from paypalrestsdk import Capture, ResourceNotFound
import logging
logging.basicConfig(level=logging.INFO)

try:
  capture = Capture.find("8F148933LY9388354")
  print("Got Capture details for Capture[%s]"%(capture.id))

except ResourceNotFound as error:
  print("Capture Not Found")

########NEW FILE########
__FILENAME__ = refund
from paypalrestsdk import Capture
import logging
logging.basicConfig(level=logging.INFO)

capture = Capture.find("8F148933LY9388354")
refund  = capture.refund({
  "amount": {
    "currency": "USD",
    "total": "110.54" } })

if refund.success():
  print("Refund[%s] Success"%(refund.id))
else:
  print("Unable to Refund")
  print(refund.error)

########NEW FILE########
__FILENAME__ = create
# #CreateCreditCard Sample
# Using the 'vault' API, you can store a
# Credit Card securely on PayPal. You can
# use a saved Credit Card to process
# a payment in the future.
# The following code demonstrates how
# can save a Credit Card on PayPal using
# the Vault API.
# API used: POST /v1/vault/credit-card
from paypalrestsdk import CreditCard
import logging
logging.basicConfig(level=logging.INFO)

credit_card = CreditCard({
   # ###CreditCard
   # A resource representing a credit card that can be
   # used to fund a payment.
   "type": "visa",
   "number": "4417119669820331",
   "expire_month": "11",
   "expire_year": "2018",
   "cvv2": "874",
   "first_name": "Joe",
   "last_name": "Shopper",

    # ###Address
    # Base Address object used as shipping or billing
    # address in a payment. [Optional]
   "billing_address": {
     "line1": "52 N Main ST",
     "city": "Johnstown",
     "state": "OH",
     "postal_code": "43210",
     "country_code": "US" }})

# Make API call & get response status
# ###Save
# Creates the credit card as a resource
# in the PayPal vault.
if credit_card.create():
  print("CreditCard[%s] created successfully"%(credit_card.id))
else:
  print("Error while creating CreditCard:")
  print(credit_card.error)

########NEW FILE########
__FILENAME__ = delete
from paypalrestsdk import CreditCard
import logging
logging.basicConfig(level=logging.INFO)

credit_card = CreditCard.find("CARD-7LT50814996943336KESEVWA")

if credit_card.delete():
  print("CreditCard deleted")
else:
  print(credit_card.error)

########NEW FILE########
__FILENAME__ = find
# #GetCreditCard Sample
# This sample code demonstrates how you
# retrieve a previously saved
# Credit Card using the 'vault' API.
# API used: GET /v1/vault/credit-card/{id}
from paypalrestsdk import CreditCard, ResourceNotFound
import logging
logging.basicConfig(level=logging.INFO)

try:
  # Retrieve the CreditCard  by calling the
  # static `find` method on the CreditCard class,
  # and pass CreditCard ID
  credit_card = CreditCard.find("CARD-5BT058015C739554AKE2GCEI")
  print("Got CreditCard[%s]"%(credit_card.id))

except ResourceNotFound as error:
  print("CreditCard Not Found")

########NEW FILE########
__FILENAME__ = cancel
from paypalrestsdk import Invoice
import logging
logging.basicConfig(level=logging.INFO)

invoice = Invoice.find("INV2-CJL7-PF4G-BLQF-5FWG")
options = {
  "subject": "Past due",
  "note": "Canceling invoice",
  "send_to_merchant": True,
  "send_to_payer": True
}

if invoice.cancel(options):  # return True or False
  print("Invoice[%s] cancel successfully"%(invoice.id))
else:
  print(invoice.error)


########NEW FILE########
__FILENAME__ = create
from paypalrestsdk import Invoice
import logging

logging.basicConfig(level=logging.INFO)

invoice = Invoice({
  "merchant_info": {
    "email": "PPX.DevNet-facilitator@gmail.com",
    "first_name": "Dennis",
    "last_name": "Doctor",
    "business_name": "Medical Professionals, LLC",
    "phone": {
      "country_code": "001",
      "national_number": "5032141716"
    },
      "address": {
      "line1": "1234 Main St.",
      "city": "Portland",
      "state": "OR",
      "postal_code": "97217",
      "country_code": "US"
    }
  },
  "billing_info": [ { "email": "example@example.com" } ],
  "items": [
    {
      "name": "Sutures",
      "quantity": 100,
      "unit_price": {
        "currency": "USD",
        "value": 5
      }
    }
  ],
  "note": "Medical Invoice 16 Jul, 2013 PST",
  "payment_term": {
    "term_type": "NET_45"
  },
  "shipping_info": {
    "first_name": "Sally",
    "last_name": "Patient",
    "business_name": "Not applicable",
    "phone": {
      "country_code": "001",
      "national_number": "5039871234"
    },
    "address": {
      "line1": "1234 Broad St.",
      "city": "Portland",
      "state": "OR",
      "postal_code": "97216",
      "country_code": "US"
    }
  }
})

if invoice.create():
  print("Invoice[%s] created successfully"%(invoice.id))
else:
  print(invoice.error)

########NEW FILE########
__FILENAME__ = get
from paypalrestsdk import Invoice, ResourceNotFound
import logging
logging.basicConfig(level=logging.INFO)

try:
  invoice = Invoice.find("INV2-9DRB-YTHU-2V9Q-7Q24")
  print("Got Invoice Details for Invoice[%s]"%(invoice.id))

except ResourceNotFound as error:
  print("Invoice Not Found")


########NEW FILE########
__FILENAME__ = get_all
from paypalrestsdk import Invoice
import logging
logging.basicConfig(level=logging.INFO)

history = Invoice.all({"page_size": 2})

print("List Invoice:")
for invoice in history.invoices:
  print("  -> Invoice[%s]"%(invoice.id))

########NEW FILE########
__FILENAME__ = remind
from paypalrestsdk import Invoice
import logging
logging.basicConfig(level=logging.INFO)

invoice = Invoice.find("INV2-9CAH-K5G7-2JPL-G4B4")
options = {
  "subject": "Past due",
  "note": "Please pay soon",
  "send_to_merchant": True
}

if invoice.remind(options):  # return True or False
  print("Invoice[%s] remind successfully"%(invoice.id))
else:
  print(invoice.error)


########NEW FILE########
__FILENAME__ = send
from paypalrestsdk import Invoice
import logging
logging.basicConfig(level=logging.INFO)

invoice = Invoice.find("INV2-9DRB-YTHU-2V9Q-7Q24")

if invoice.send():  # return True or False
  print("Invoice[%s] send successfully"%(invoice.id))
else:
  print(invoice.error)


########NEW FILE########
__FILENAME__ = merchant_server
# Flask application for a developer/merchant verifying payments and executing
# payments on behalf of customer who has consented to future payments

from flask import Flask, request, jsonify
from paypal_client import verify_payment, add_consent, charge_wallet

app = Flask(__name__)


@app.route('/client_responses', methods=['POST'])
def parse_response():
    """Check validity of a mobile payment made via credit card or PayPal,
    or save customer consented to future payments
    """
    if not request.json or not 'response' or not 'response_type' in request.json:
        raise InvalidUsage('Invalid mobile client response ')

    if request.json['response_type'] == 'payment':
        result, message = verify_payment(request.json)
        if result:
            return jsonify({"status": "verified"}), 200
        else:
            raise InvalidUsage(message, status_code=404)

    elif request.json['response_type'] == 'authorization_code':
        add_consent(request.json['customer_id'],
                    request.json['response']['code'])
        return jsonify({"status": "Received consent"}), 200

    else:
        raise InvalidUsage('Invalid response type')


@app.route('/correlations', methods=['POST'])
def correlations():
    """Send correlation id, customer id (e.g email) and transactions details for
    purchase made by customer who formerly consented to future payments.
    Can be used for immediate payments or authorize a payment for later execution

    https://developer.paypal.com/docs/integration/direct/capture-payment/
    """
    result, message = charge_wallet(
        transaction=request.json['transactions'][0], customer_id=request.json['customer_id'],
        correlation_id=request.json['correlation_id'], intent=request.json['intent']
    )
    if result:
        return jsonify({"status": message}), 200
    else:
        raise InvalidUsage(message)


class InvalidUsage(Exception):
    """Errorhandler class to enable custom error message propagation
    """
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

if __name__ == '__main__':
    app.run('0.0.0.0', port=8000, debug=True)

########NEW FILE########
__FILENAME__ = merchant_server_tests
from merchant_server import app
import paypal_client
import unittest
import json
from mock import patch, Mock

class TestMerchantServer(unittest.TestCase):

    def setUp(self):
        """Before each test, set up a test client"""
    	app.config['TESTING'] = True
    	self.app = app.test_client()
        self.response_dict = dict(
            create_time='2014-02-12T22:29:49Z',
            id='PAY-564191241M8701234KL57LXI',
            intent='sale',
            state='approved'
        )
        self.client_json = json.dumps(dict(
            response_type='payment', 
            response=self.response_dict            
        ))

    def test_empty_request(self):
        """Check that request without body raises 400"""
    	rv = self.app.post('/client_responses')
    	self.assertEqual(rv.status_code, 400)
    	self.assertIn('Invalid mobile client response', rv.data)

    def test_invalid_response_type(self):
        """Check invalid response type is handled properly"""
        json_data = json.dumps(dict(response_type='test', response='test'))
        rv = self.app.post('/client_responses', data=json_data, content_type='application/json')
        self.assertEqual(rv.status_code, 400)
        self.assertIn('Invalid response type', rv.data)

    @patch('merchant_server.verify_payment')
    def test_verify_payment(self, mock):
        """verify correct response on successful paypal payment verification"""
        mock.return_value = True, None
        rv = self.app.post('/client_responses', data=self.client_json, content_type='application/json')
        self.assertEqual(rv.status_code, 200)
        self.assertIn('verified', rv.data)

    @patch('merchant_server.verify_payment')
    def test_verify_payment_twice_fails(self, mock):
        """Trying to verify an already verified payment is a bad request"""
        mock.return_value = True, None
        rv = self.app.post('/client_responses', data=self.client_json, content_type='application/json')
        self.assertEqual(rv.status_code, 200)
        self.assertIn('verified', rv.data)  
        mock.return_value = False, 'Payment already been verified.'
        rv = self.app.post('/client_responses', data=self.client_json, content_type='application/json')
        self.assertEqual(rv.status_code, 404)
        self.assertIn('Payment already been verified', rv.data)

    @patch('merchant_server.add_consent')
    def test_send_future_payment_consent(self, mock):
        """Test consent is received properly on merchant_server"""
        mock.return_value = None
        response_dict = dict(
            code='EBYhRW3ncivudQn8UopLp4A28xIlqPDpAoqd7bi'
        )
        client_dict = dict(
            environment='live',
            paypal_sdk_version='2.0.1',
            platform='iOS',
            product_name='PayPal iOS SDK'
        )
        json_data= json.dumps(dict(
            response_type='authorization_code', 
            response=response_dict,
            customer_id='customer@gmail.com',
            client=client_dict
        ))
        rv = self.app.post('/client_responses', data=json_data, content_type='application/json')
        self.assertEqual(rv.status_code, 200)
        self.assertIn('Received consent', rv.data)

class TestPaypalClient(unittest.TestCase):

    def setUp(self):
        self.transaction = {
            "amount": {
                "total": "1.00",
                "currency": "USD" 
            },
            "description": "This is the payment transaction description." 
        }

    def test_get_stored_refresh_token(self):
        """Test that the correct refresh token is getting fetched for the customer"""
        paypal_client.save_refresh_token('customer1@gmail.com', 'ref_token_sample')
        refresh_token = paypal_client.get_stored_refresh_token('customer1@gmail.com')
        self.assertEqual(refresh_token, 'ref_token_sample')
       
    def test_remove_consent(self):
        """Test removing consent deletes stored refresh token"""
        paypal_client.save_refresh_token('customer1@gmail.com', 'ref_token_sample')
        refresh_token = paypal_client.get_stored_refresh_token('customer1@gmail.com')
        self.assertEqual(refresh_token, 'ref_token_sample')
        paypal_client.remove_consent('customer1@gmail.com')
        refresh_token = paypal_client.get_stored_refresh_token('customer1@gmail.com')
        self.assertEqual(refresh_token, None)

    def test_charge_wallet_missing_consent(self):
        """Charging a new customer without consent will not work"""
        return_status, message = paypal_client.charge_wallet(self.transaction, 'new_customer@gmail.com', None, 'sale')
        self.assertEqual(return_status, False)
        self.assertIn("Customer has not granted consent", message)

    @patch('paypal_client.paypalrestsdk.Payment.create')
    @patch('paypal_client.get_stored_refresh_token')
    def test_charge_wallet_failure(self, mock_create, mock_token):
        """Test charge wallet fails with correct message"""
        mock_token.return_value = False
        mock_create.return_value = 'refresh_token'
        return_status, message = paypal_client.charge_wallet(self.transaction, 'customer1@gmail.com', 'correlation_id', 'sale')
        self.assertEqual(return_status, False)
        self.assertIn("Error while creating payment", message)
    
    @patch('paypal_client.paypalrestsdk.Payment.create')
    def test_charge_wallet_success(self, mock):
        mock.return_value = True
        paypal_client.save_refresh_token('customer1@gmail.com', 'ref_token_sample')
        return_status, message = paypal_client.charge_wallet(self.transaction, 'customer1@gmail.com', 'correlation_id', 'sale')
        self.assertEqual(return_status, True)
        self.assertIn("Charged customer customer1@gmail.com " + self.transaction["amount"]["total"], message)
########NEW FILE########
__FILENAME__ = paypal_client
import paypalrestsdk
import paypal_config
import logging

logging.basicConfig(level=logging.DEBUG)

api = paypalrestsdk.configure({
    "mode": paypal_config.MODE,
    "client_id": paypal_config.CLIENT_ID,
    "client_secret": paypal_config.CLIENT_SECRET
})

# map from user email to refresh_token
CUSTOMER_TOKEN_MAP = "customer_token_map.txt"

# store ids of verified payments
# use a database instead of files in production
VERIFIED_PAYMENTS = "paypal_verified_payments.txt"


def verify_payment(payment_client):
    """Verify credit card of paypal payment made using rest apis
    https://developer.paypal.com/docs/integration/mobile/verify-mobile-payment/
    """
    payment_id = payment_client['response']['id']

    try:
        payment_server = paypalrestsdk.Payment.find(payment_id)

        if payment_server.state != 'approved':
            return False, 'Payment has not been approved yet. Status is ' + payment_server.state + '.'

        amount_client = payment_client['payment']['amount']
        currency_client = payment_client['payment']['currency_code']

        # Get most recent transaction
        transaction = payment_server.transactions[0]
        amount_server = transaction.amount.total
        currency_server = transaction.amount.currency
        sale_state = transaction.related_resources[0].sale.state

        if (amount_server != amount_client):
            return False, 'Payment amount does not match order.'
        elif (currency_client != currency_server):
            return False, 'Payment currency does not match order.'
        elif sale_state != 'completed':
            return False, 'Sale not completed.'
        elif used_payment(payment_id):
            return False, 'Payment already been verified.'
        else:
            return True, None

    except paypalrestsdk.ResourceNotFound:
        return False, 'Payment Not Found'


def used_payment(payment_id):
    """Make sure same payment does not get reused
    """
    pp_verified_payments = set([line.strip() for line in open(VERIFIED_PAYMENTS, "rw")])
    if payment_id in pp_verified_payments:
        return True
    else:
        with open(VERIFIED_PAYMENTS, "a") as f:
            f.write(payment_id + "\n")
            return False


def add_consent(customer_id=None, auth_code=None):
    """Send authorization code after obtaining customer
    consent. Exchange for long living refresh token for
    creating payments in future
    """
    refresh_token = api.get_refresh_token(auth_code)
    save_refresh_token(customer_id, refresh_token)


def remove_consent(customer_id):
    """Remove previously granted consent by customer
    """
    customer_token_map = dict([line.strip().split(",") for line in open(CUSTOMER_TOKEN_MAP)])
    customer_token_map.pop(customer_id, None)
    with open(CUSTOMER_TOKEN_MAP, "w") as f:
        for customer, token in customer_token_map:
            f.write(customer + "," + token + "\n")


def save_refresh_token(customer_id=None, refresh_token=None):
    """Store refresh token, likely in a database for app in production
    """
    with open(CUSTOMER_TOKEN_MAP, "a") as f:
        f.write(customer_id + "," + refresh_token + "\n")


def get_stored_refresh_token(customer_id=None):
    """If customer has already consented, return cached refresh token
    """
    try:
        customer_token_map = dict([line.strip().split(",") for line in open(CUSTOMER_TOKEN_MAP)])
        return customer_token_map.get(customer_id)
    except (OSError, IOError):
        return None


def charge_wallet(transaction, customer_id=None, correlation_id=None, intent="authorize"):
    """Charge a customer who formerly consented to future payments
    from paypal wallet.
    """
    payment = paypalrestsdk.Payment({
        "intent":  intent,
        "payer": {
            "payment_method": "paypal"
        },
        "transactions": [{
            "amount": {
                "total":  transaction["amount"]["total"],
                "currency":  transaction["amount"]["currency"]
                },
            "description":  transaction["description"]
        }]})
    
    refresh_token = get_stored_refresh_token(customer_id)

    if not refresh_token:
        return False, "Customer has not granted consent as no refresh token has been found for customer. Authorization code needed to get new refresh token."

    if payment.create(refresh_token, correlation_id):
        print("Payment %s created successfully" % (payment.id))
        if payment['intent'] == "authorize":
            authorization_id = payment['transactions'][0]['related_resources'][0]['authorization']['id']
            print(
                "Payment %s authorized. Authorization id is %s" % (
                    payment.id, authorization_id
                )
            )
        return True, "Charged customer " + customer_id + " " + transaction["amount"]["total"]
    else:
        return False, "Error while creating payment:" + str(payment.error)

########NEW FILE########
__FILENAME__ = openid_connect
import paypalrestsdk
from paypalrestsdk.openid_connect import Tokeninfo

paypalrestsdk.configure({ 'openid_client_id': 'CLIENT_ID',
  'openid_client_secret': 'CLIENT_SECRET',
  'openid_redirect_uri': 'http://example.com' })

login_url = Tokeninfo.authorize_url({ 'scope': 'openid profile'})

print(login_url)

code = raw_input('Authorize code: ')

tokeninfo = Tokeninfo.create(code)

print(tokeninfo)

userinfo  = tokeninfo.userinfo()

print(userinfo)

tokeninfo = tokeninfo.refresh()

print(tokeninfo)

logout_url = tokeninfo.logout_url()

print(logout_url)

########NEW FILE########
__FILENAME__ = all
# #GetPaymentList Sample
# This sample code demonstrate how you can
# retrieve a list of all Payment resources
# you've created using the Payments API.
# Note various query parameters that you can
# use to filter, and paginate through the
# payments list.
# API used: GET /v1/payments/payments
from paypalrestsdk import Payment
import logging
logging.basicConfig(level=logging.INFO)

# ###Retrieve
# Retrieve the PaymentHistory  by calling the
# `all` method
# on the Payment class
# Refer the API documentation
# for valid values for keys
# Supported paramters are :count, :next_id
payment_history = Payment.all({"count": 2})

# List Payments
print("List Payment:")
for payment in payment_history.payments:
  print("  -> Payment[%s]"%(payment.id))

########NEW FILE########
__FILENAME__ = create_future_payment
# Create Future Payment Using PayPal Wallet
# https://developer.paypal.com/docs/integration/mobile/make-future-payment/
import paypalrestsdk

api = paypalrestsdk.configure({
    "mode": "sandbox",
    "client_id": "CLIENT_ID",
    "client_secret": "CLIENT_SECRET"
})

#authorization code from mobile sdk
authorization_code = ''

#Exchange authorization_code for long living refresh token. You should store
#it in a database for later use
refresh_token = api.get_refresh_token(authorization_code)

#correlation id from mobile sdk
correlation_id=''

#Initialize the payment object
payment = paypalrestsdk.Payment({
  "intent":  "authorize",
  "payer": {
    "payment_method":  "paypal" },
  "transactions": [{
    "amount":{
      "total":  "0.17",
      "currency":  "USD"},
    "description":  "This is the payment transaction description."}]})

# Create the payment. Set intent to sale to charge immediately,
# else if authorize use the authorization id to capture
# payment later using samples/authorization/capture.py
if payment.create(refresh_token, correlation_id):
  print("Payment %s created successfully"%(payment.id))
  if payment['intent'] == "authorize":
    print(
      "Payment %s authorized. Authorization id is %s"
      %(payment.id, payment['transactions'][0]['related_resources'][0]['authorization']['id'])
      )
else:
  print("Error while creating payment:")
  print(payment.error)

########NEW FILE########
__FILENAME__ = create_with_credit_card
# #CreatePayment using credit card Sample
# This sample code demonstrate how you can process
# a payment with a credit card.
# API used: /v1/payments/payment
from paypalrestsdk import Payment
import logging

logging.basicConfig(level=logging.INFO)

# ###Payment
# A Payment Resource; create one using
# the above types and intent as 'sale'
payment = Payment({
  "intent": "sale",

  # ###Payer
  # A resource representing a Payer that funds a payment
  # Use the List of `FundingInstrument` and the Payment Method
  # as 'credit_card'
  "payer": {
    "payment_method": "credit_card",

    # ###FundingInstrument
    # A resource representing a Payeer's funding instrument.
    # Use a Payer ID (A unique identifier of the payer generated
    # and provided by the facilitator. This is required when
    # creating or using a tokenized funding instrument)
    # and the `CreditCardDetails`
    "funding_instruments": [{

      # ###CreditCard
      # A resource representing a credit card that can be
      # used to fund a payment.
      "credit_card": {
        "type": "visa",
        "number": "4417119669820331",
        "expire_month": "11",
        "expire_year": "2018",
        "cvv2": "874",
        "first_name": "Joe",
        "last_name": "Shopper",

        # ###Address
        # Base Address used as shipping or billing
        # address in a payment. [Optional]
        "billing_address": {
          "line1": "52 N Main ST",
          "city": "Johnstown",
          "state": "OH",
          "postal_code": "43210",
          "country_code": "US" }}}]},
  # ###Transaction
  # A transaction defines the contract of a
  # payment - what is the payment for and who
  # is fulfilling it.
  "transactions": [{

    # ### ItemList
    "item_list": {
      "items": [{
        "name": "item",
        "sku": "item",
        "price": "1.00",
        "currency": "USD",
        "quantity": 1 }]},

    # ###Amount
    # Let's you specify a payment amount.
    "amount": {
      "total": "1.00",
      "currency": "USD" },
    "description": "This is the payment transaction description." }]})

# Create Payment and return status( True or False )
if payment.create():
  print("Payment[%s] created successfully"%(payment.id))
else:
  # Display Error message
  print("Error while creating payment:")
  print(payment.error)

########NEW FILE########
__FILENAME__ = create_with_credit_card_token
# #CreatePayment Using Saved Card Sample
# This sample code demonstrates how you can process a
# Payment using a previously saved credit card.
# API used: /v1/payments/payment
from paypalrestsdk import Payment
import logging

logging.basicConfig(level=logging.INFO)

# ###Payment
# A Payment Resource; create one using
# the above types and intent as 'sale'
payment = Payment({
  "intent": "sale",
  # ###Payer
  # A resource representing a Payer that funds a payment
  # Use the List of `FundingInstrument` and the Payment Method
  # as 'credit_card'
  "payer": {
    "payment_method": "credit_card",

    # ###FundingInstrument
    # A resource representing a Payeer's funding instrument.
    # In this case, a Saved Credit Card can be passed to
    # charge the payment.
    "funding_instruments": [{
      # ###CreditCardToken
      # A resource representing a credit card that can be
      # used to fund a payment.
      "credit_card_token": {
        "credit_card_id": "CARD-5BT058015C739554AKE2GCEI" }}]},

  # ###Transaction
  # A transaction defines the contract of a
  # payment - what is the payment for and who
  # is fulfilling it
  "transactions": [{

    # ### ItemList
    "item_list": {
      "items": [{
        "name": "item",
        "sku": "item",
        "price": "1.00",
        "currency": "USD",
        "quantity": 1 }]},

    # ###Amount
    # Let's you specify a payment amount.
    "amount": {
      "total": "1.00",
      "currency": "USD" },
    "description": "This is the payment transaction description." }]})

# Create Payment and return status
if payment.create():
  print("Payment[%s] created successfully"%(payment.id))
else:
  print("Error while creating payment:")
  print(payment.error)

########NEW FILE########
__FILENAME__ = create_with_paypal
# #Create Payment Using PayPal Sample
# This sample code demonstrates how you can process a
# PayPal Account based Payment.
# API used: /v1/payments/payment
from paypalrestsdk import Payment
import logging

logging.basicConfig(level=logging.INFO)

# ###Payment
# A Payment Resource; create one using
# the above types and intent as 'sale'
payment = Payment({
  "intent":  "sale",

  # ###Payer
  # A resource representing a Payer that funds a payment
  # Payment Method as 'paypal'
  "payer":  {
    "payment_method":  "paypal" },

  # ###Redirect URLs
  "redirect_urls": {
    "return_url": "http://localhost:3000/payment/execute",
    "cancel_url": "http://localhost:3000/" },

  # ###Transaction
  # A transaction defines the contract of a
  # payment - what is the payment for and who
  # is fulfilling it.
  "transactions":  [ {

    # ### ItemList
    "item_list": {
      "items": [{
        "name": "item",
        "sku": "item",
        "price": "5.00",
        "currency": "USD",
        "quantity": 1 }]},

    # ###Amount
    # Let's you specify a payment amount.
    "amount":  {
      "total":  "5.00",
      "currency":  "USD" },
    "description":  "This is the payment transaction description." } ] } )

# Create Payment and return status
if payment.create():
  print("Payment[%s] created successfully"%(payment.id))
  # Redirect the user to given approval url
  for link in payment.links:
    if link.method == "REDIRECT":
      redirect_url = link.href
      print("Redirect for approval: %s"%(redirect_url))
else:
  print("Error while creating payment:")
  print(payment.error)

########NEW FILE########
__FILENAME__ = execute
# # Execute an approved PayPal payment
# Use this call to execute (complete) a PayPal payment that has been approved by the payer.
# You can optionally update transaction information by passing in one or more transactions.
# API used: /v1/payments/payment
from paypalrestsdk import Payment
import logging
logging.basicConfig(level=logging.INFO)

# ID of the payment. This ID is provided when creating payment.
payment = Payment.find("PAY-28103131SP722473WKFD7VGQ")

# PayerID is required to approve the payment.
if payment.execute({"payer_id": "DUFRQ8GWYMJXC"}):  # return True or False
  print("Payment[%s] execute successfully"%(payment.id))
else:
  print(payment.error)


########NEW FILE########
__FILENAME__ = find
# #GetPayment Sample
# This sample code demonstrates how you can retrieve
# the details of a payment resource.
# API used: /v1/payments/payment/{payment-id}
from paypalrestsdk import Payment, ResourceNotFound
import logging
logging.basicConfig(level=logging.INFO)

try:
  # Retrieve the payment object by calling the
  # `find` method
  # on the Payment class by passing Payment ID
  payment = Payment.find("PAY-0XL713371A312273YKE2GCNI")
  print("Got Payment Details for Payment[%s]"%(payment.id))

except ResourceNotFound as error:
  # It will through ResourceNotFound exception if the payment not found
  print("Payment Not Found")


########NEW FILE########
__FILENAME__ = find
# # Get Details of a Sale Transaction Sample
# This sample code demonstrates how you can retrieve
# details of completed Sale Transaction.
# API used: /v1/payments/sale/{sale-id}
from paypalrestsdk import Sale, ResourceNotFound
import logging
logging.basicConfig(level=logging.INFO)

try:
  # Get Sale object by passing sale id
  sale = Sale.find("7DY409201T7922549")
  print("Got Sale details for Sale[%s]"%(sale.id))

except ResourceNotFound as error:
  print("Sale Not Found")

########NEW FILE########
__FILENAME__ = refund
# #SaleRefund Sample
# This sample code demonstrate how you can
# process a refund on a sale transaction created
# using the Payments API.
# API used: /v1/payments/sale/{sale-id}/refund
from paypalrestsdk import Sale
import logging
logging.basicConfig(level=logging.INFO)

sale = Sale.find("7DY409201T7922549")

# Make Refund API call
# Set amount only if the refund is partial
refund = sale.refund({
  "amount": {
    "total": "0.01",
    "currency": "USD" } })

# Check refund status
if refund.success():
  print("Refund[%s] Success"%(refund.id))
else:
  print("Unable to Refund")
  print(refund.error)

########NEW FILE########
__FILENAME__ = api_test
from test_helper import unittest, client_id, client_secret, paypal

class Api(unittest.TestCase):

  api = paypal.Api(
    client_id= client_id,
    client_secret= client_secret )

  def test_endpoint(self):
    
    new_api = paypal.Api(mode="live", client_id="dummy", client_secret="dummy")
    self.assertEqual(new_api.endpoint, "https://api.paypal.com")
    self.assertEqual(new_api.token_endpoint, "https://api.paypal.com")
    
    new_api = paypal.Api(mode="sandbox", client_id="dummy", client_secret="dummy")
    self.assertEqual(new_api.endpoint, "https://api.sandbox.paypal.com")
    self.assertEqual(new_api.token_endpoint, "https://api.sandbox.paypal.com")

    new_api = paypal.Api(endpoint="https://custom-endpoint.paypal.com", client_id="dummy", client_secret="dummy")
    self.assertEqual(new_api.endpoint, "https://custom-endpoint.paypal.com")
    self.assertEqual(new_api.token_endpoint, "https://custom-endpoint.paypal.com")
  
  def test_get(self):
    payment_history = self.api.get("/v1/payments/payment?count=1")
    self.assertEqual(payment_history['count'], 1)

  def test_post(self):
    credit_card = self.api.post("v1/vault/credit-card", {
      "type": "visa",
      "number": "4417119669820331",
      "expire_month": "11",
      "expire_year": "2018",
      "cvv2": "874",
      "first_name": "Joe",
      "last_name": "Shopper" })
    self.assertEqual(credit_card.get('error'), None)
    self.assertNotEqual(credit_card.get('id'), None)

  def test_bad_request(self):
    credit_card = self.api.post("v1/vault/credit-card", {})
    self.assertNotEqual(credit_card.get('error'), None)

  def test_expired_token(self):
    old_token = self.api.get_token_hash()['access_token']
    self.assertNotEqual(old_token, None)
    self.api.token_hash["access_token"] = "ExpiredToken"
    new_token = self.api.get_token_hash()['access_token']
    self.assertEqual(new_token, "ExpiredToken")
    payment_history = self.api.get("/v1/payments/payment?count=1")
    self.assertEqual(payment_history['count'], 1)

  def test_expired_time(self):
    old_token = self.api.get_token_hash()['access_token']
    self.api.token_hash["expires_in"] = 0
    new_token = self.api.get_token_hash()['access_token']
    self.assertNotEqual(new_token, old_token)

  def test_not_found(self):
    self.assertRaises(paypal.ResourceNotFound, self.api.get, ("/v1/payments/payment/PAY-1234"))
  

########NEW FILE########
__FILENAME__ = openid_connect_test
from test_helper import unittest, paypal, client_id, client_secret, assert_regex_matches
from paypalrestsdk.openid_connect import Tokeninfo, Userinfo, authorize_url, logout_url, endpoint


class TestTokeninfo(unittest.TestCase):

  def test_create(self):
    self.assertRaises(paypal.ResourceNotFound, Tokeninfo.create, "invalid-code")

  def test_userinfo(self):
    self.assertRaises(paypal.UnauthorizedAccess, Tokeninfo().userinfo, {})

  def test_refresh(self):
    self.assertRaises(paypal.ResourceNotFound, Tokeninfo().refresh, {})

  def test_create_with_refresh_token(self):
    self.assertRaises(paypal.ResourceNotFound, Tokeninfo.create_with_refresh_token, "invalid-token")

class TestUserinfo(unittest.TestCase):

  def test_get(self):
    self.assertRaises(paypal.UnauthorizedAccess, Userinfo.get, "invalid")

class TestUrls(unittest.TestCase):

  def test_authorize_url(self):
    url = authorize_url()
    assert_regex_matches(self, url, 'response_type=code')
    assert_regex_matches(self, url, 'scope=openid')
    assert_regex_matches(self, url, 'client_id=%s'%(client_id))
    assert_regex_matches(self, url, 'https://www.sandbox.paypal.com')

    self.assertEqual(endpoint(), 'https://api.sandbox.paypal.com')

  def test_live_mode_url(self):
    try:
      paypal.configure( mode='live',  client_id=client_id, client_secret=client_secret )
      url = authorize_url()
      assert_regex_matches(self, url, 'response_type=code')
      assert_regex_matches(self, url, 'scope=openid')
      assert_regex_matches(self, url, 'client_id=%s'%(client_id))
      assert_regex_matches(self, url, 'https://www.paypal.com')

      self.assertEqual(endpoint(), 'https://api.paypal.com')
    finally:
      paypal.configure( mode='sandbox', client_id=client_id, client_secret=client_secret )

  def test_authorize_url_options(self):
    url = authorize_url({ 'scope': 'openid profile' })
    assert_regex_matches(self, url, 'scope=openid\+profile')

  def test_authorize_url_using_tokeninfo(self):
    url = Tokeninfo.authorize_url({ 'scope': 'openid profile' })
    assert_regex_matches(self, url, 'scope=openid\+profile')

  def test_logout_url(self):
    url = logout_url()
    assert_regex_matches(self, url, 'logout=true')

  def test_logout_url_options(self):
    url = logout_url({'id_token': '1234'})
    assert_regex_matches(self, url, 'id_token=1234')

  def test_logout_url_using_tokeninfo(self):
    url = Tokeninfo({'id_token': '1234'}).logout_url()
    assert_regex_matches(self, url, 'id_token=1234')

########NEW FILE########
__FILENAME__ = payments_test
from test_helper import paypal, unittest

class TestPayment(unittest.TestCase):

  def test_create(self):
    payment = paypal.Payment({
      "intent": "sale",
      "payer": {
        "payment_method": "credit_card",
        "funding_instruments": [{
          "credit_card": {
            "type": "visa",
            "number": "4417119669820331",
            "expire_month": "11",
            "expire_year": "2018",
            "cvv2": "874",
            "first_name": "Joe",
            "last_name": "Shopper" }}]},
      "transactions": [{
        "item_list": {
          "items": [{
            "name": "item",
            "sku": "item",
            "price": "1.00",
            "currency": "USD",
            "quantity": 1 }]},
        "amount": {
          "total": "1.00",
          "currency": "USD" },
        "description": "This is the payment transaction description." }]})
    self.assertEqual(payment.create(), True)

  def test_validation(self):
    payment = paypal.Payment({})
    self.assertEqual(payment.create(), False)

  def test_all(self):
    payment_histroy = paypal.Payment.all({"count": 1 })
    self.assertEqual(payment_histroy.count, 1)
    self.assertEqual(payment_histroy.payments[0].__class__, paypal.Payment)
  
  def test_find(self):
    payment_history = paypal.Payment.all({"count": 1 })
    payment_id = payment_history.payments[0]['id']
    payment = paypal.Payment.find(payment_id)
    self.assertEqual(payment.id, payment_id)
  
  def test_not_found(self):
    self.assertRaises(paypal.ResourceNotFound, paypal.Payment.find, ("PAY-1234"))
  
  def test_execute(self):
    payment = paypal.Payment({
      "intent": "sale",
      "payer": {
        "payment_method": "paypal" },
      "redirect_urls": {
        "return_url": "http://localhost:3000/payment/execute",
        "cancel_url": "http://localhost:3000/" },
      "transactions": [{
        "item_list": {
          "items": [{
            "name": "item",
            "sku": "item",
            "price": "1.00",
            "currency": "USD",
            "quantity": 1 }]},
        "amount": {
          "total": "1.00",
          "currency": "USD" },
        "description": "This is the payment transaction description." }]})
    self.assertEqual(payment.create(), True)
    payment.execute({ 'payer_id': 'HZH2W8NPXUE5W' })


class TestSale(unittest.TestCase):

  def create_sale(self):
    payment = paypal.Payment({
      "intent": "sale",
      "payer": {
        "payment_method": "credit_card",
        "funding_instruments": [{
          "credit_card": {
            "type": "visa",
            "number": "4417119669820331",
            "expire_month": "11",
            "expire_year": "2018",
            "cvv2": "874",
            "first_name": "Joe",
            "last_name": "Shopper" }}]},
      "transactions": [{
        "amount": {
          "total": "1.00",
          "currency": "USD" },
        "description": "This is the payment transaction description." }]})
    self.assertEqual(payment.create(), True)
    return payment.transactions[0].related_resources[0].sale
    
  def test_find(self):
    sale = paypal.Sale.find(self.create_sale().id)
    self.assertEqual(sale.__class__, paypal.Sale)

  def test_refund(self):
    sale   = paypal.Sale.find(self.create_sale().id)
    refund = sale.refund({ "amount": { "total": "0.01", "currency": "USD" } })
    self.assertEqual(refund.success(), True)


class TestRefund(unittest.TestCase):

  def test_find(self):
    refund = paypal.Refund.find("5C377143F71265517")
    self.assertEqual(refund.__class__, paypal.Refund)


class TestAuthorization(unittest.TestCase):

  def create_authorization(self):
    payment = paypal.Payment({
      "intent": "authorize",
      "payer": {
        "payment_method": "credit_card",
        "funding_instruments": [{
          "credit_card": {
            "type": "visa",
            "number": "4417119669820331",
            "expire_month": "11",
            "expire_year": "2018",
            "cvv2": "874",
            "first_name": "Joe",
            "last_name": "Shopper" }}]},
      "transactions": [{
        "item_list": {
          "items": [{
            "name": "item",
            "sku": "item",
            "price": "1.00",
            "currency": "USD",
            "quantity": 1 }]},
        "amount": {
          "total": "1.00",
          "currency": "USD" },
        "description": "This is the payment transaction description." }]})
    self.assertEqual(payment.create(), True)
    return payment.transactions[0].related_resources[0].authorization

  def test_find(self):
    authorization = paypal.Authorization.find(self.create_authorization().id)
    self.assertEqual(authorization.__class__, paypal.Authorization)

  def test_capture(self):
    authorization = self.create_authorization()
    capture = authorization.capture({ "amount": { "currency": "USD", "total": "1.00" } })
    self.assertEqual(capture.success(), True)

  def test_void(self):
    authorization = self.create_authorization()
    self.assertEqual(authorization.void(), True)

  def test_capture_find(self):
    authorization = self.create_authorization()
    capture = authorization.capture({ "amount": { "currency": "USD", "total": "1.00" } })
    self.assertEqual(capture.success(), True)
    capture = paypal.Capture.find(capture.id)
    self.assertEqual(capture.__class__, paypal.Capture)

  def test_reauthorize(self):
    authorization = paypal.Authorization.find("7GH53639GA425732B")
    authorization.amount = {
      "currency": "USD",
      "total": "7.00" }
    self.assertEqual(authorization.reauthorize(), False)

  def test_capture_refund(self):
    authorization = self.create_authorization()
    capture = authorization.capture({ "amount": { "currency": "USD", "total": "1.00" } })
    self.assertEqual(capture.success(), True)

    refund = capture.refund({ "amount": { "currency": "USD", "total": "1.00" } })
    self.assertEqual(refund.success(), True)
    self.assertEqual(refund.__class__, paypal.Refund)

########NEW FILE########
__FILENAME__ = vault_test
from test_helper import paypal, unittest

class TestCreditCard(unittest.TestCase):

  credit_card_attributes = {
      "type": "visa",
      "number": "4417119669820331",
      "expire_month": "11",
      "expire_year": "2018",
      "cvv2": "874",
      "first_name": "Joe",
      "last_name": "Shopper" }

  def test_create_and_find(self):
    credit_card = paypal.CreditCard(self.credit_card_attributes)
    self.assertEqual(credit_card.create(), True)

    credit_card = paypal.CreditCard.find(credit_card.id)
    self.assertEqual(credit_card.__class__, paypal.CreditCard)

  def test_delete(self):
    credit_card = paypal.CreditCard(self.credit_card_attributes)
    self.assertEqual(credit_card.create(), True)
    self.assertEqual(credit_card.delete(), True)

  def test_duplicate_request_id(self):
    credit_card = paypal.CreditCard(self.credit_card_attributes)
    self.assertEqual(credit_card.create(), True)

    new_credit_card = paypal.CreditCard(self.credit_card_attributes)
    new_credit_card.request_id = credit_card.request_id
    self.assertEqual(new_credit_card.create(), True)

    self.assertEqual(new_credit_card.id, credit_card.id)
    self.assertEqual(new_credit_card.request_id, credit_card.request_id)


########NEW FILE########
__FILENAME__ = test_helper
import logging
import re
import unittest

import paypalrestsdk as paypal

# Logging
logging.basicConfig(level=logging.INFO)

# Credential
client_id = "EBWKjlELKMYqRNQ6sYvFo64FtaRLRR5BdHEESmha49TM"
client_secret = "EO422dn3gQLgDbuwqTjzrFgFtaRLRR5BdHEESmha49TM"

# Set credential for default api
paypal.configure(client_id=client_id, client_secret=client_secret)


def assert_regex_matches(test, s, regex):
    test.assertTrue(re.compile(regex).search(s))

########NEW FILE########
__FILENAME__ = api_test
from test_helper import unittest, client_id, client_secret, paypal
from mock import Mock, patch

class Api(unittest.TestCase):

  def setUp(self):
    self.api = paypal.Api(
      client_id= client_id, 
      client_secret= client_secret
    )
    self.api.request = Mock()
    self.card_attributes = {
      "type": "visa",
      "number": "4417119669820331",
      "expire_month": "11",
      "expire_year": "2018",
      "cvv2": "874",
      "first_name": "Joe",
      "last_name": "Shopper" }
    self.authorization_code = 'auth_code_from_device'
    self.refresh_token = 'long_living_token'
    self.access_token = 'use_once_token'
    self.future_payments_scope = 'https://api.paypal.com/v1/payments/.* https://uri.paypal.com/services/payments/futurepayments'
  
  def test_endpoint(self):
    new_api = paypal.Api(mode="live", client_id="dummy", client_secret="dummy")
    self.assertEqual(new_api.endpoint, "https://api.paypal.com")
    self.assertEqual(new_api.token_endpoint, "https://api.paypal.com")

    new_api = paypal.Api(mode="sandbox", client_id="dummy", client_secret="dummy")
    self.assertEqual(new_api.endpoint, "https://api.sandbox.paypal.com")
    self.assertEqual(new_api.token_endpoint, "https://api.sandbox.paypal.com")

    new_api = paypal.Api(endpoint="https://custom-endpoint.paypal.com", client_id="dummy", client_secret="dummy")
    self.assertEqual(new_api.endpoint, "https://custom-endpoint.paypal.com")
    self.assertEqual(new_api.token_endpoint, "https://custom-endpoint.paypal.com")
  
  def test_get(self):
    payment_history = self.api.get("/v1/payments/payment?count=1")
    self.api.request.assert_called_once_with('https://api.sandbox.paypal.com/v1/payments/payment?count=1','GET',headers={})
  
  def test_post(self):
    self.api.request.return_value = {'id': 'test'}
    credit_card = self.api.post("v1/vault/credit-card", self.card_attributes)

    self.assertEqual(credit_card.get('error'), None)
    self.assertNotEqual(credit_card.get('id'), None)

  def test_bad_request(self):
    self.api.request.return_value = {'error': 'test'}
    credit_card = self.api.post("v1/vault/credit-card", {})
    
    self.api.request.assert_called_once_with('https://api.sandbox.paypal.com/v1/vault/credit-card',
                                        'POST', 
                                         body={},
                                         headers={}, 
                                         refresh_token=None)
    self.assertNotEqual(credit_card.get('error'), None)

  def test_expired_time(self):
    old_token = self.api.get_token_hash()['access_token']
    self.api.token_hash["expires_in"] = 0
    new_token = self.api.get_token_hash()['access_token']
    self.assertNotEqual(new_token, old_token)

  def test_not_found(self):
    self.api.request.side_effect = paypal.ResourceNotFound("error")
    self.assertRaises(paypal.ResourceNotFound, self.api.get, ("/v1/payments/payment/PAY-1234"))

  @patch('test_helper.paypal.Api.http_call', autospec=True)
  def test_get_refresh_token(self, mock_http):
    mock_http.return_value = {
      'access_token': self.access_token,
      'expires_in': 900,
      'refresh_token': self.refresh_token,
      'scope': self.future_payments_scope,
      'token_type': 'Bearer'
    }
    refresh_token = self.api.get_refresh_token(self.authorization_code)
    mock_http.assert_called_once_with(self.api,
      'https://api.sandbox.paypal.com/v1/oauth2/token', 'POST',
      data = 'grant_type=authorization_code&response_type=token&redirect_uri=urn:ietf:wg:oauth:2.0:oob&code=' + self.authorization_code,
      headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'Authorization': 'Basic ' + self.api.basic_auth(),
        'User-Agent': self.api.user_agent
      }
    )
    self.assertEqual(refresh_token, self.refresh_token)

  def test_fail_get_refresh_token(self):
    self.assertRaises(paypal.MissingConfig, self.api.get_refresh_token, None)

  @patch('test_helper.paypal.Api.http_call', autospec=True)
  def test_refresh_access_token(self, mock_http):
    mock_http.return_value = {
      'access_token': self.access_token,
      'app_id': 'APP-6XR95014BA15863X',
      'expires_in': 900,
      'scope': self.future_payments_scope,
      'token_type': 'Bearer'
    }
    access_token = self.api.get_token_hash(refresh_token=self.refresh_token)['access_token']
    mock_http.assert_called_once_with(self.api,
      'https://api.sandbox.paypal.com/v1/oauth2/token', 'POST',
      data = 'grant_type=refresh_token&refresh_token=' + self.refresh_token,
      headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'Authorization': 'Basic ' + self.api.basic_auth(),
        'User-Agent': self.api.user_agent        
      }
    )
    self.assertEqual(access_token, self.access_token)

########NEW FILE########
__FILENAME__ = exceptions_test
import unittest
from collections import namedtuple
import json
from paypalrestsdk.exceptions import *

class TestExceptions(unittest.TestCase):

  def setUp(self):
    self.Response = namedtuple('Response', 'status_code reason')

  def test_connection(self):
    error = ConnectionError({})
    self.assertEqual(str(error), "Failed.")

  def test_redirect(self):
    error = Redirection({ "Location": "http://example.com" })
    self.assertEqual(str(error), "Failed. => http://example.com")

  def test_not_found(self):
    response = self.Response(status_code="404", reason="Not Found" )
    error = ResourceNotFound(response)
    self.assertEqual(str(error), "Failed. Response status: %s. Response message: %s." % (response.status_code, response.reason))

  def test_unauthorized_access(self):
    response = self.Response(status_code="401", reason="Unauthorized" )
    error = UnauthorizedAccess(response)
    self.assertEqual(str(error), "Failed. Response status: %s. Response message: %s." % (response.status_code, response.reason))

  def test_missing_param(self):
    error = MissingParam("Missing Payment Id")
    self.assertEqual(str(error), "Missing Payment Id")

  def test_missing_config(self):
    error = MissingParam("Missing client_id")
    self.assertEqual(str(error), "Missing client_id")


########NEW FILE########
__FILENAME__ = invoices_test
from test_helper import paypal, unittest
from mock import patch, ANY

class TestInvoice(unittest.TestCase):

	def setUp(self):
		self.invoice_attributes = {
			'merchant_info': {
				'email': 'ppaas_default@paypal.com'
			},
			'billing_info': [
				{ 'email': 'example@example.com' }
			],
			'items': [
				{
					'name': 'Sutures',
					'quantity': 100,
					'unit_price': {
						'currency': 'USD',
						'value': 5
					}
				}
			]
		}
		self.invoice = paypal.Invoice(self.invoice_attributes)
		self.invoice.id = 'INV2-RUVR-ADWQ-H89Y-ABCD'

	@patch('test_helper.paypal.Api.post', autospec=True)
	def test_create(self, mock):
		invoice = paypal.Invoice(self.invoice_attributes)
		response = invoice.create()

		mock.assert_called_once_with(invoice.api,'v1/invoicing/invoices', self.invoice_attributes, {'PayPal-Request-Id' : invoice.request_id}, None)
		self.assertEqual(response, True)

	@patch('test_helper.paypal.Api.get', autospec=True)
	def test_find(self, mock):
		invoice = paypal.Invoice.find(self.invoice.id)

		mock.assert_called_once_with(self.invoice.api, 'v1/invoicing/invoices/'+self.invoice.id)
		self.assertTrue(isinstance(invoice, paypal.Invoice))

	@patch('test_helper.paypal.Api.get', autospec=True)
	def test_all(self, mock):
		mock.return_value = {'total_count': 1, 'invoices': [self.invoice_attributes]}
		history = paypal.Invoice.all({'count': 1})

		mock.assert_called_once_with(self.invoice.api, 'v1/invoicing/invoices?count=1')
		self.assertEqual(history.total_count, 1)
		self.assertTrue(isinstance(history.invoices[0], paypal.Invoice))


	@patch('test_helper.paypal.Api.delete', autospec=True)
	def test_delete(self, mock):
		response = self.invoice.delete()

		mock.assert_called_once_with(self.invoice.api,'v1/invoicing/invoices/'+self.invoice.id)
		self.assertEqual(response, True)

	@patch('test_helper.paypal.Api.put', autospec=True)
	def test_update(self, mock):
		response = self.invoice.update(self.invoice_attributes)

		mock.assert_called_once_with(self.invoice.api,'v1/invoicing/invoices/'+self.invoice.id, self.invoice_attributes, {'PayPal-Request-Id' : self.invoice.request_id}, None)
		self.assertEqual(response, True)

	@patch('test_helper.paypal.Api.post', autospec=True)
	def test_send(self, mock):
		response = self.invoice.send()

		mock.assert_called_once_with(self.invoice.api,'v1/invoicing/invoices/'+self.invoice.id+'/send', {}, {'PayPal-Request-Id' : ANY})
		self.assertEqual(response, True)

	@patch('test_helper.paypal.Api.post', autospec=True)
	def test_search(self, mock):
		search_attributes = {
			"start_invoice_date" : "2014-04-01 PST",
			"end_invoice_date" : "2013-04-03 PST",
			"page" : 1,
			"page_size" : 20,
			"total_count_required" : True
		}
		mock.return_value = {'total_count': 1, 'invoices': [self.invoice_attributes]}

		history = paypal.Invoice.search(search_attributes)

		mock.assert_called_once_with(self.invoice.api,'v1/invoicing/invoices/search', search_attributes)
		self.assertEqual(history.total_count, 1)
		self.assertTrue(isinstance(history.invoices[0], paypal.Invoice))

	@patch('test_helper.paypal.Api.post', autospec=True)
	def test_remind(self, mock):
		remind_attributes = {
			'subject': 'Past due',
			'note': 'Please pay soon',
			'send_to_merchant': True
		}

		response = self.invoice.remind(remind_attributes)

		mock.assert_called_once_with(self.invoice.api,'v1/invoicing/invoices/'+self.invoice.id+'/remind', remind_attributes, {'PayPal-Request-Id' : ANY})
		self.assertEqual(response, True)

	@patch('test_helper.paypal.Api.post', autospec=True)
	def test_cancel(self, mock):
		cancel_attributes = {
			'subject': 'Past due',
			'note': 'Canceling invoice',
			'send_to_merchant': True,
			'send_to_payer': True
		}

		response = self.invoice.cancel(cancel_attributes)

		mock.assert_called_once_with(self.invoice.api,'v1/invoicing/invoices/'+self.invoice.id+'/cancel', cancel_attributes, {'PayPal-Request-Id' : ANY})
		self.assertEqual(response, True)

########NEW FILE########
__FILENAME__ = openid_connect_test
from test_helper import unittest, paypal, client_id, client_secret, assert_regex_matches
from paypalrestsdk.openid_connect import Tokeninfo, Userinfo, authorize_url, logout_url, endpoint, Base
from mock import Mock

class TestTokeninfo(unittest.TestCase):

  def setUp(self):
  	"""
  	Base is the base class of Tokeninfo and Userinfo. Replace post
  	method of base with a mock object to prevent http call
  	"""
  	Base.post = Mock()

  def test_create(self):
    Base.post.side_effect = paypal.ResourceNotFound('','')
    self.assertRaises(paypal.ResourceNotFound, Tokeninfo.create, "invalid-code")
    Base.post.assert_called_once_with('v1/identity/openidconnect/tokenservice',{'code': 'invalid-code', 'client_secret': client_secret, 'grant_type': 'authorization_code', 'client_id': client_id})
  
  def test_userinfo(self):
    Base.post.side_effect = paypal.UnauthorizedAccess('','')
    self.assertRaises(paypal.UnauthorizedAccess, Tokeninfo().userinfo, {})
    Base.post.assert_called_once_with('v1/identity/openidconnect/userinfo', {'access_token': None, 'schema': 'openid'})
  
  
  def test_refresh(self):
    Base.post.side_effect = paypal.ResourceNotFound('','')
    self.assertRaises(paypal.ResourceNotFound, Tokeninfo().refresh, {})
    Base.post.assert_called_once_with('v1/identity/openidconnect/tokenservice',{'client_secret': client_secret, 'grant_type': 'refresh_token', 'refresh_token': None, 'client_id': client_id})

  
  def test_create_with_refresh_token(self):
    Base.post.side_effect = paypal.ResourceNotFound('','')
    self.assertRaises(paypal.ResourceNotFound, Tokeninfo.create_with_refresh_token, "invalid-token")
    Base.post.assert_called_once_with('v1/identity/openidconnect/tokenservice',{'client_secret': client_secret, 'grant_type': 'refresh_token', 'refresh_token': 'invalid-token', 'client_id': client_id})
  
class TestUserinfo(unittest.TestCase):

  def setUp(self):
  	Base.post = Mock()

  def test_get(self):
    Base.post.side_effect = paypal.UnauthorizedAccess('','')
    self.assertRaises(paypal.UnauthorizedAccess, Userinfo.get, "invalid")
    Base.post.assert_called_once_with('v1/identity/openidconnect/userinfo', {'access_token': 'invalid', 'schema': 'openid'})

class TestUrls(unittest.TestCase):

  def test_authorize_url(self):
    url = authorize_url()
    assert_regex_matches(self, url, 'response_type=code')
    assert_regex_matches(self, url, 'scope=openid')
    assert_regex_matches(self, url, 'client_id=%s'%(client_id))
    assert_regex_matches(self, url, 'https://www.sandbox.paypal.com')

    self.assertEqual(endpoint(), 'https://api.sandbox.paypal.com')

  def test_live_mode_url(self):
    try:
      paypal.configure( mode='live',  client_id=client_id, client_secret=client_secret )
      url = authorize_url()
      assert_regex_matches(self, url, 'response_type=code')
      assert_regex_matches(self, url, 'scope=openid')
      assert_regex_matches(self, url, 'client_id=%s'%(client_id))
      assert_regex_matches(self, url, 'https://www.paypal.com')

      self.assertEqual(endpoint(), 'https://api.paypal.com')
    finally:
      paypal.configure( mode='sandbox', client_id=client_id, client_secret=client_secret )

  def test_authorize_url_options(self):
    url = authorize_url({ 'scope': 'openid profile' })
    assert_regex_matches(self, url, 'scope=openid\+profile')

  def test_authorize_url_using_tokeninfo(self):
    url = Tokeninfo.authorize_url({ 'scope': 'openid profile' })
    assert_regex_matches(self, url, 'scope=openid\+profile')

  def test_logout_url(self):
    url = logout_url()
    assert_regex_matches(self, url, 'logout=true')

  def test_logout_url_options(self):
    url = logout_url({'id_token': '1234'})
    assert_regex_matches(self, url, 'id_token=1234')

  def test_logout_url_using_tokeninfo(self):
    url = Tokeninfo({'id_token': '1234'}).logout_url()
    assert_regex_matches(self, url, 'id_token=1234')

########NEW FILE########
__FILENAME__ = payments_test
from test_helper import paypal, unittest
from mock import patch, ANY

class TestPayment(unittest.TestCase):

	def setUp(self):
		self.payment_attributes = {
		      "intent": "sale",
		      "payer": {
		        "payment_method": "credit_card",
		        "funding_instruments": [{
		          "credit_card": {
		            "type": "visa",
		            "number": "4417119669820331",
		            "expire_month": "11",
		            "expire_year": "2018",
		            "cvv2": "874",
		            "first_name": "Joe",
		            "last_name": "Shopper" }}]},
		      "transactions": [{
		        "item_list": {
		          "items": [{
		            "name": "item",
		            "sku": "item",
		            "price": "1.00",
		            "currency": "USD",
		            "quantity": 1 }]},
		        "amount": {
		          "total": "1.00",
		          "currency": "USD" },
		        "description": "This is the payment transaction description." }]}
		self.payment = paypal.Payment(self.payment_attributes)
		self.refresh_token = 'long_living_refresh_token'
		self.correlation_id = 'paypal_application_correlation_id'


	@patch('test_helper.paypal.Api.post', autospec=True)
	def test_create(self, mock):	
		response = self.payment.create()
		self.assertNotEqual(self.payment.request_id, None)
		mock.assert_called_once_with(self.payment.api,'v1/payments/payment',self.payment_attributes, {'PayPal-Request-Id' : self.payment.request_id}, None)		
		self.assertEqual(response, True)

	@patch('test_helper.paypal.Api.post', autospec=True)
	def test_create_future_payment(self, mock):
		response = self.payment.create(
			refresh_token=self.refresh_token, 
			correlation_id=self.correlation_id
		)
		self.assertNotEqual(self.payment.request_id, None)
		mock.assert_called_once_with(
			self.payment.api,'v1/payments/payment',
			self.payment_attributes, 
			{'PayPal-Request-Id' : self.payment.request_id, 'Paypal-Application-Correlation-Id' : self.correlation_id}, 
			self.refresh_token
		)
		self.assertEqual(response, True)

	@patch('test_helper.paypal.Api.post', autospec=True)
	def test_validation(self, mock):
		'''
		Check that validation fails on trying to create a payment
		with required fields missing
		'''

		payment = paypal.Payment({})
		mock.return_value = {'error' : 'validation', 'message' : 'Invalid request - see details',
		 	'debug_id': 'b8ef6b0aa6329',
		 	'information_link' : 'https://developer.paypal.com/webapps/developer/docs/api/#VALIDATION_ERROR'
		 	}
		response = payment.create()
		mock.assert_called_once_with(self.payment.api,'v1/payments/payment',{}, {'PayPal-Request-Id' : payment.request_id}, None)

		self.assertEqual(response, False)

	
	@patch('test_helper.paypal.Api.get', autospec=True)
	def test_all(self, mock):
		mock.return_value = {'count': 1,'next_id': 'PAY-5TU016908T094823BKLKU7MY', 'payments': [{'update_time': '2014-01-14T15:00:41Z', 'links' : [],
	     	'payer': {'payment_method': 'paypal', 'payer_info': {}}, 'transactions': [], 'state': 'created', 'intent': 'sale', 'id': 'PAY-0A963503EW637094HKLKVCGI'}]}

		payment_histroy = paypal.Payment.all({"count": 1 })

		mock.assert_called_once_with(self.payment.api,'v1/payments/payment?count=1')
		self.assertEqual(payment_histroy.count, 1)

		self.assertEqual(payment_histroy.payments[0].__class__, paypal.Payment)

	@patch('test_helper.paypal.Api.get', autospec=True)
	def test_find(self, mock):
		mock.return_value = {'count': 1,'next_id': 'PAY-5TU016908T094823BKLKU7MY', 'payments': [{'update_time': '2014-01-14T15:00:41Z', 'links' : [],
		'payer': {'payment_method': 'paypal', 'payer_info': {}}, 'transactions': [], 'state': 'created', 'intent': 'sale', 'id': 'PAY-0A963503EW637094HKLKVCGI'}]}

		payment_history = paypal.Payment.all({"count": 1 })
		mock.assert_called_once_with(self.payment.api,'v1/payments/payment?count=1')

		payment_id = payment_history.payments[0]['id']
		mock.return_value = {'id': 'PAY-3KM36407UD294123NKLKV34I', 'intent' : 'sale', 'state' : 'completed', 'description' : 'This is the payment transaction' }
		payment = paypal.Payment.find(payment_id)

		mock.assert_called_with(self.payment.api,'v1/payments/payment/PAY-0A963503EW637094HKLKVCGI')

		self.assertNotEqual(payment.id, payment_id)
    
	@patch('test_helper.paypal.Api.get', autospec=True)
	def test_not_found(self, mock):
		mock.side_effect = paypal.ResourceNotFound('','')
		self.assertRaises(paypal.ResourceNotFound, paypal.Payment.find, ("PAY-1234"))

	@patch('test_helper.paypal.Api.post', autospec=True)
	def test_execute(self, mock):
		paypal_payment_attrib = {
	      "intent": "sale",
	      "payer": {
	        "payment_method": "paypal" },
	      "redirect_urls": {
	        "return_url": "http://localhost:3000/payment/execute",
	        "cancel_url": "http://localhost:3000/" },
	      "transactions": [{
	        "item_list": {
	          "items": [{
	            "name": "item",
	            "sku": "item",
	            "price": "1.00",
	            "currency": "USD",
	            "quantity": 1 }]},
	        "amount": {
	          "total": "1.00",
	          "currency": "USD" },
	        "description": "This is the payment transaction description." }]}
		payment = paypal.Payment(paypal_payment_attrib)
		mock.return_value = {'id' : 'AY-7JD471929T152531RKLKWR6Q', 'intent' : 'sale', 'state' : 'completed', 'description' : 'This is the payment transaction' }

		response = payment.create()
		mock.assert_called_once_with(self.payment.api,'v1/payments/payment',paypal_payment_attrib, {'PayPal-Request-Id' : payment.request_id}, None)
		self.assertEqual(response, True)
		
		payment.execute({ 'payer_id': 'HZH2W8NPXUE5W' })
		mock.assert_called_with(self.payment.api,'v1/payments/payment/AY-7JD471929T152531RKLKWR6Q/execute',{'payer_id': 'HZH2W8NPXUE5W'}, {'PayPal-Request-Id' : ANY})

class TestSale(unittest.TestCase):

	def setUp(self):
		self.payment_attributes = {
		      "intent": "sale",
		      "payer": {
		        "payment_method": "credit_card",
		        "funding_instruments": [{
		          "credit_card": {
		            "type": "visa",
		            "number": "4417119669820331",
		            "expire_month": "11",
		            "expire_year": "2018",
		            "cvv2": "874",
		            "first_name": "Joe",
		            "last_name": "Shopper" }}]},
		      "transactions": [{
		        "item_list": {
		          "items": [{
		            "name": "item",
		            "sku": "item",
		            "price": "1.00",
		            "currency": "USD",
		            "quantity": 1 }]},
		        "amount": {
		          "total": "1.00",
		          "currency": "USD" },
		        "description": "This is the payment transaction description." }]}
		self.payment = paypal.Payment(self.payment_attributes)

	@patch('test_helper.paypal.Api.post', autospec=True)
	def create_sale(self, mock):
		mock.return_value = {'id': 'PAY-888868365Y436124EKLKW6JA', 'update_time': '2014-01-14T17:09:00Z', 'links': [], 'payer' : {}, 'transactions': [{'related_resources': [{'sale': {'update_time': '2014-01-14T17:09:00Z', 
							  	'links' : [], 'state': 'completed', 'id': '5VX40080GX603650', 
							  	'amount': {'currency': 'USD', 'total': '1.00'} }}],
							  	}]}
		response = self.payment.create()
		self.assertEqual(response, True)
		return self.payment.transactions[0].related_resources[0].sale
	    
	@patch('test_helper.paypal.Api.get', autospec=True)    
	def test_find(self, mock):
		sale = paypal.Sale.find(self.create_sale().id)
		mock.assert_called_once_with(sale.api,'v1/payments/sale/5VX40080GX603650')
		self.assertEqual(sale.__class__, paypal.Sale)

class TestRefund(unittest.TestCase):

	@patch('test_helper.paypal.Api.get', autospec=True)  
	def test_find(self,mock):
		refund_id = '5C377143F71265517'
		mock.return_value = {'update_time': '2013-04-01T08:44:09Z',
			 'sale_id': '7DY409201T7922549', 'state': 'completed', 'id': refund_id,
			 'amount': {'currency': 'USD', 'total': '0.01'}}
		refund = paypal.Refund.find(refund_id)
		mock.assert_called_once_with(refund.api, 'v1/payments/refund/'+refund_id)
		self.assertEqual(refund.__class__, paypal.Refund)

class TestAuthorization(unittest.TestCase):

	def setUp(self):
		self.payment_attributes = {
		"intent": "authorize",
		"payer": {
		"payment_method": "credit_card",
		"funding_instruments": [{
		  "credit_card": {
		    "type": "visa",
		    "number": "4417119669820331",
		    "expire_month": "11",
		    "expire_year": "2018",
		    "cvv2": "874",
		    "first_name": "Joe",
		    "last_name": "Shopper" }}]},
		"transactions": [{
		"item_list": {
		  "items": [{
		    "name": "item",
		    "sku": "item",
		    "price": "1.00",
		    "currency": "USD",
		    "quantity": 1 }]},
		"amount": {
		  "total": "1.00",
		  "currency": "USD" },
		"description": "This is the payment transaction description." }]}
		self.payment = paypal.Payment(self.payment_attributes)
		self.auth_id = '3J872959AY1512221'
		self.authorization_attributes = {'valid_until': '2014-02-12T21:11:25Z',
			  'update_time': '2014-01-14T21:11:33Z', 'links': [{'href': 'https://api.sandbox.paypal.com/v1/payments/authorization/3J872959AY1512221', 'method': 'GET', 'rel': 'self'},
			   {'href': 'https://api.sandbox.paypal.com/v1/payments/authorization/3J872959AY1512221/capture', 'method': 'POST', 'rel': 'capture'},
			    {'href': 'https://api.sandbox.paypal.com/v1/payments/authorization/3J872959AY1512221/void', 'method': 'POST', 'rel': 'void'},
			     {'href': 'https://api.sandbox.paypal.com/v1/payments/payment/PAY-1EE254486E964802VKLK2P7I', 'method': 'GET', 'rel': 'parent_payment'}],
			      'state': 'authorized', 'parent_payment': 'PAY-1EE254486E964802VKLK2P7I', 'amount': {'currency': 'USD', 'total': '1.00', 'details': {'subtotal': '1.00'}},
			       'create_time': '2014-01-14T21:11:25Z', 'id': '3J872959AY1512221'}
		self.capture_attributes = { "amount": { "currency": "USD", "total": "1.00" } }

	@patch('test_helper.paypal.Api.post', autospec=True)
	def test_create(self, mock):
		mock.return_value = {'id': 'PAY-888868365Y436124EKLKW6JA', 'update_time': '2014-01-14T17:09:00Z', 'links': [], 'payer' : {},
		'transactions': [{'related_resources': [{'authorization': self.authorization_attributes}],
		    					  	}]}
		response = self.payment.create()
		mock.assert_called_once_with(self.payment.api,'v1/payments/payment',self.payment_attributes, {'PayPal-Request-Id' : self.payment.request_id}, None)		
		self.assertEqual(response, True)
		self.assertNotEqual(self.payment.transactions[0].related_resources[0].authorization.id, None)

	@patch('test_helper.paypal.Api.get', autospec=True) 
	def test_find(self, mock):
		authorization = paypal.Authorization.find(self.auth_id)
		self.assertEqual(authorization.__class__, paypal.Authorization)
		mock.assert_called_once_with(authorization.api, 'v1/payments/authorization/'+self.auth_id)

	@patch('test_helper.paypal.Api.post', autospec=True) 
	def test_capture(self, mock):
		authorization = paypal.Authorization.find(self.auth_id)
		capture = authorization.capture(self.capture_attributes)
		self.assertEqual(capture.success(), True)
		mock.assert_called_once_with(authorization.api, 'v1/payments/authorization/' + self.auth_id + '/capture', self.capture_attributes, 
			{'PayPal-Request-Id': ANY})

	@patch('test_helper.paypal.Api.post', autospec=True) 
	def test_void(self, mock):
		authorization = paypal.Authorization.find(self.auth_id)
		self.assertEqual(authorization.void(), True)
		mock.assert_called_once_with(authorization.api, 'v1/payments/authorization/' + self.auth_id + '/void', {}, 
			{'PayPal-Request-Id': ANY})
  
	@patch('test_helper.paypal.Api.get', autospec=True) 
	def test_capture_find(self, mock):
		capture_id = '7S373777UY2709045'
		capture = paypal.Capture.find(capture_id)
		self.assertEqual(capture.__class__, paypal.Capture)
		mock.assert_called_once_with(capture.api, 'v1/payments/capture/' + capture_id)


########NEW FILE########
__FILENAME__ = resource_test
from test_helper import unittest
from paypalrestsdk.resource import Resource, Find, List, Post

class TestResource(unittest.TestCase):
  def test_getter(self):
    data = {
      'name': 'testing',
      'amount': 10.0,
      'transaction': { 'description': 'testing' },
      'items': [ { 'name': 'testing' } ] }
    resource = Resource(data)
    self.assertEqual(resource.name, 'testing')
    self.assertEqual(resource['name'], 'testing')
    self.assertEqual(resource.amount, 10.0)
    self.assertEqual(resource.items[0].__class__, Resource)
    self.assertEqual(resource.items[0].name, 'testing')
    self.assertEqual(resource.items[0]['name'], 'testing')
    self.assertEqual(resource.unknown, None)
    self.assertRaises(KeyError, lambda: resource['unknown'])

  def test_setter(self):
    data = { 'name': 'testing' }
    resource = Resource(data)
    self.assertEqual(resource.name, 'testing' )
    resource.name = 'changed'
    self.assertEqual(resource.name, 'changed' )
    resource['name'] = 'again-changed'
    self.assertEqual(resource.name, 'again-changed' )
    resource.transaction = { 'description': 'testing' }
    self.assertEqual(resource.transaction.__class__, Resource)
    self.assertEqual(resource.transaction.description, 'testing')

  def test_to_dict(self):
    data = {
      "intent": "sale",
      "payer": {
        "payment_method": "credit_card",
        "funding_instruments": [{
          "credit_card": {
            "type": "visa",
            "number": "4417119669820331",
            "expire_month": "11",
            "expire_year": "2018",
            "cvv2": "874",
            "first_name": "Joe",
            "last_name": "Shopper" }}]},
      "transactions": [{
        "item_list": {
          "items": [{
            "name": "item",
            "sku": "item",
            "price": "1.00",
            "currency": "USD",
            "quantity": 1 }]},
        "amount": {
          "total": "1.00",
          "currency": "USD" },
        "description": "This is the payment transaction description." }]}
    resource = Resource(data)
    self.assertEqual(resource.to_dict(), data)

  def test_request_id(self):
    data = {
      'name': 'testing',
      'request_id': 1234 }
    resource = Resource(data)
    self.assertEqual(resource.to_dict(), {'name': 'testing'})
    self.assertEqual(resource.request_id, 1234)
    self.assertEqual(resource.http_headers(), {'PayPal-Request-Id': 1234})

  def test_http_headers(self):
    data = {
      'name': 'testing',
      'header': { 'My-Header': 'testing' } }
    resource = Resource(data)
    self.assertEqual(resource.header, {'My-Header': 'testing'})
    self.assertEqual(resource.http_headers(), {'PayPal-Request-Id': resource.request_id, 'My-Header': 'testing'})

  def test_passing_api(self):
    """
    Check that api objects are passed on to new resources when given
    """
    class DummyAPI(object):
      post = lambda s,*a,**k: {}
      get = lambda s,*a,**k: {}

    api = DummyAPI()

    # Conversion
    resource = Resource({
      'name': 'testing',
    }, api=api)
    self.assertEqual(resource.api, api)
    convert_ret = resource.convert('test', {})
    self.assertEqual(convert_ret.api, api)

    class TestResource(Find, List, Post):
      path = '/'

    # Find
    find = TestResource.find('resourceid', api=api)
    self.assertEqual(find.api, api)

    # List
    list_ = TestResource.all(api=api)
    self.assertEqual(list_.api, api)

    # Post
    post = TestResource({'id':'id'}, api=api)
    post_ret = post.post('test')
    self.assertEqual(post_ret.api, api)

  def test_default_resource(self):
    from paypalrestsdk import api
    original = api.__api__

    class DummyAPI(object):
      post = lambda s,*a,**k: {}
      get = lambda s,*a,**k: {}

    # Make default api object a dummy api object
    default = api.__api__ = DummyAPI()

    resource = Resource({})
    self.assertEqual(resource.api, default)

    class TestResource(Find, List, Post):
      path = '/'

    # Find
    find = TestResource.find('resourceid')
    self.assertEqual(find.api, default)

    # List
    list_ = TestResource.all()
    self.assertEqual(list_.api, default)

    api.__api__ = original # Restore original api object
    

########NEW FILE########
__FILENAME__ = util_test
import paypalrestsdk.util as util
import unittest

class TestUtil(unittest.TestCase):

  def test_join_url(self):
    url = util.join_url("payment", "1")
    self.assertEqual(url, "payment/1")
    url = util.join_url("payment/", "1")
    self.assertEqual(url, "payment/1")
    url = util.join_url("payment", "/1")
    self.assertEqual(url, "payment/1")
    url = util.join_url("payment/", "/1")
    self.assertEqual(url, "payment/1")

  def test_join_url_params(self):
    url = util.join_url_params("payment", { "count": 1 })
    self.assertEqual(url, "payment?count=1")
    url = util.join_url_params("payment", { "count": 1, "next_id": 4321 })
    self.assertTrue(url in ("payment?count=1&next_id=4321", "payment?next_id=4321&count=1"))


########NEW FILE########
__FILENAME__ = vault_test
from test_helper import paypal, unittest
from mock import patch

class TestCreditCard(unittest.TestCase):

	def setUp(self):
		self.credit_card_attributes = {
	      "type": "visa",
	      "number": "4417119669820331",
	      "expire_month": "11",
	      "expire_year": "2018",
	      "cvv2": "874",
	      "first_name": "Joe",
	      "last_name": "Shopper" }
		self.credit_card = paypal.CreditCard(self.credit_card_attributes)
		
	@patch('test_helper.paypal.Api.post', autospec=True)
	def test_create(self, mock):
		'''
		Check that a request id has been created and the mock post method
		has been called with the instance of api object, correct route and 
		api credentials
		'''

		response = self.credit_card.create()
		self.assertNotEqual(self.credit_card.request_id, None)
		mock.assert_called_once_with(self.credit_card.api,'v1/vault/credit-card',self.credit_card_attributes, {'PayPal-Request-Id' : self.credit_card.request_id}, None)		
		self.assertEqual(response, True)
	
	@patch('test_helper.paypal.Api.get', autospec=True)
	def test_find(self, mock):
		'''
		Check correct endpoint requested for finding a credit_card
		and the response of credit card type
		'''

		self.credit_card.id = 'CARD-6KP075290X361673LKLKB24A'
		card = paypal.CreditCard.find(self.credit_card.id)
		#python 2.6 compatible
		mock.assert_called_once_with(self.credit_card.api,'v1/vault/credit-card/'+self.credit_card.id)
		self.assertTrue(isinstance(card,paypal.CreditCard))
	
	@patch('test_helper.paypal.Api.delete', autospec=True)
	def test_delete(self, mock):
		'''
		Check correct endpoint requested for deleting a card 
		from vault
		''' 

		self.credit_card.id = 'CARD-6KP075290X361673LKLKB24A'
		response = self.credit_card.delete()
		mock.assert_called_once_with(self.credit_card.api,'v1/vault/credit-card/'+self.credit_card.id)
		self.assertEqual(response, True)

	@patch('test_helper.paypal.Api.post', autospec=True)
	def test_duplicate_request_id(self, mock):
		'''
		Test that credit card with identical attributes and request id
		returns the credit card already created. Request id must be the 
		same for idempotency
		'''

		response = self.credit_card.create()
		mock.assert_called_once_with(self.credit_card.api,'v1/vault/credit-card',self.credit_card_attributes, {'PayPal-Request-Id' : self.credit_card.request_id}, None)		
		self.assertEqual(response, True)

		duplicate_card = paypal.CreditCard(self.credit_card_attributes)
		duplicate_card.request_id = self.credit_card.request_id
		duplicate_card_response = duplicate_card.create()

		mock.assert_called_with(self.credit_card.api,'v1/vault/credit-card',self.credit_card_attributes, {'PayPal-Request-Id' : self.credit_card.request_id}, None)
		self.assertEqual(mock.call_count, 2)
		self.assertEqual(duplicate_card_response, True)
		self.assertEqual(duplicate_card.id, self.credit_card.id)

	
########NEW FILE########
