__FILENAME__ = adapters
from lxml import etree, objectify
import decimal

from refreshbooks import elements, client

# To make life nicer for clients, allow built-in numeric-alike types
# in API parameters.
_stringable_types = frozenset([float, int, decimal.Decimal])

def encode_as_simple_from_element(name, value):
    """Creates an etree element following the simple field convention. To 
    ease reuse of returned data in future calls, we smash anything that looks 
    like an ObjectifiedDataElement to unicode:
    
        >>> value = objectify.DataElement(5)
        >>> element = encode_as_simple('foo', value)
        >>> element.tag == 'foo'
        True
        >>> element.text == '5'
        True
    """
    return encode_as_simple(name, value.text)

def encode_as_simple(name, value):
    """Creates an etree element following the simple field convention. Values
    are assumed to be strs, unicodes, ints, floats, or Decimals:
    
        >>> element = encode_as_simple('foo', '5')
        >>> element.tag == 'foo'
        True
        >>> element.text == '5'
        True
        >>> element = encode_as_simple('bar', 8)
        >>> element.tag == 'bar'
        True
        >>> element.text == '8'
        True
    """
    if isinstance(value, objectify.ObjectifiedDataElement):
        return encode_as_simple(name, unicode(value))
    if type(value) in _stringable_types:
        value = str(value)
    return elements.field(name, value)

def encode_as_dict(_name, **kwargs):
    # To make collisions between the first positional parameter and the 
    # keyword parameters unlikely, that's why.
    return elements.type(_name, [
        encode_parameter(name, value) for (name, value) in kwargs.items()
    ])

def encode_as_list_of_dicts(name, *args):
    return elements.type(name, [
        encode_parameter(name, value) for (name, value) in args
    ])

def encode_parameter(name, value):
    # This type-checking order is delicate. Don't touch it until you 
    # understand the interactions between:
    #
    # - foo(*a_dict) causes foo to receive the keys of a_dict as positional
    #   parameters.
    # - foo(*a_string) causes foo to receive each character of a_string as a
    #   positional parameter.
    # - encode_as_simple will barf with a TypeError if the value is not
    #   representable as XML.
    # - encode_as_simple_from_element will barf with an AttributeError if the 
    #   value is not an Element-shaped thing.
    #
    # We do this so that we don't need to maintain a list of mappings for
    # every Freshbooks API document type. You're welcome.
    try:
        return encode_as_simple_from_element(name, value)
    except AttributeError:
        try:
            return encode_as_dict(name, **value)
        except TypeError:
            try:
                return encode_as_simple(name, value)
            except TypeError:
                return encode_as_list_of_dicts(name, *value)

def xml_request(method, **params):
    request_document = elements.request(
        method,
        [
            encode_parameter(name, value)
            for (name, value) in params.items()
        ]
    )
    
    return etree.tostring(request_document)

def fail_to_exception_response(response):
    if response.attrib['status'] == 'fail':
        raise client.FailedRequest(response.error)
    
    return response
########NEW FILE########
__FILENAME__ = api
from __future__ import print_function

import decimal
import sys
import functools

from lxml import objectify

from refreshbooks import client, adapters, transport

try:
    from refreshbooks.optional import oauth as os
    _create_oauth_client = os.OAuthClient
except ImportError:
    def _create_oauth_client(*args, **kwargs):
        raise NotImplementedError('oauth support requires the "oauth" module.')

def api_url(domain):
    """Returns the Freshbooks API URL for a given domain.
    
        >>> api_url('billing.freshbooks.com')
        'https://billing.freshbooks.com/api/2.1/xml-in'
    """
    return "https://%s/api/2.1/xml-in" % (domain, )


class DecimalElement(objectify.ObjectifiedDataElement):
    @property
    def pyval(self):
        return decimal.Decimal(self.text)

def check_decimal_element(decimal_string):
    """Catch decimal's exception and raise the one objectify expects"""
    try:
        decimal.Decimal(decimal_string)
    except decimal.InvalidOperation:
        raise ValueError

# register the decimal type with objectify
decimal_type = objectify.PyType('decimal', check_decimal_element, 
                                DecimalElement)
decimal_type.register(before='float')

default_request_encoder = adapters.xml_request

def default_response_decoder(*args, **kwargs):
    return adapters.fail_to_exception_response(
        objectify.fromstring(*args, **kwargs)
    )

def logging_request_encoder(method, **params):
    encoded = default_request_encoder(method, **params)
    
    print("--- Request (%r, %r) ---" % (method, params), file=sys.stderr)
    print(encoded, file=sys.stderr)
    
    return encoded

def logging_response_decoder(response):
    print("--- Response ---", file=sys.stderr)
    print(response, file=sys.stderr)
    
    return default_response_decoder(response)

def build_headers(authorization_headers, user_agent):
    headers = transport.KeepAliveHeaders(authorization_headers)
    if user_agent is not None:
        headers = transport.UserAgentHeaders(headers, user_agent)
    
    return headers

def AuthorizingClient(
    domain,
    auth,
    request_encoder,
    response_decoder,
    user_agent=None
):
    """Creates a Freshbooks client for a freshbooks domain, using
    an auth object.
    """
    
    http_transport = transport.HttpTransport(
        api_url(domain),
        build_headers(auth, user_agent)
    )
    
    return client.Client(
        request_encoder,
        http_transport,
        response_decoder
    )

def TokenClient(
    domain,
    token,
    user_agent=None,
    request_encoder=default_request_encoder,
    response_decoder=default_response_decoder,
):
    """Creates a Freshbooks client for a freshbooks domain, using
    token-based auth.
    
    The optional request_encoder and response_decoder parameters can be
    passed the logging_request_encoder and logging_response_decoder objects
    from this module, or custom encoders, to aid debugging or change the
    behaviour of refreshbooks' request-to-XML-to-response mapping.
    
    The optional user_agent keyword parameter can be used to specify the
    user agent string passed to FreshBooks. If unset, a default user agent
    string is used.
    """
    
    return AuthorizingClient(
        domain,
        transport.TokenAuthorization(token),
        request_encoder,
        response_decoder,
        user_agent=user_agent
    )

def OAuthClient(
    domain,
    consumer_key,
    consumer_secret,
    token,
    token_secret,
    user_agent=None,
    request_encoder=default_request_encoder,
    response_decoder=default_response_decoder
):
    """Creates a Freshbooks client for a freshbooks domain, using
    OAuth. Token management is assumed to have been handled out of band.
    
    The optional request_encoder and response_decoder parameters can be
    passed the logging_request_encoder and logging_response_decoder objects
    from this module, or custom encoders, to aid debugging or change the
    behaviour of refreshbooks' request-to-XML-to-response mapping.
    
    The optional user_agent keyword parameter can be used to specify the
    user agent string passed to FreshBooks. If unset, a default user agent
    string is used.
    """
    return _create_oauth_client(
        AuthorizingClient,
        domain,
        consumer_key,
        consumer_secret,
        token,
        token_secret,
        user_agent=user_agent,
        request_encoder=request_encoder,
        response_decoder=response_decoder
    )

def list_element_type(_name, **kwargs):
    """Convenience function for creating tuples that satisfy
    adapters.encode_as_list_of_dicts().
    
        >>> list_element_type('foo', a='5')
        ('foo', {'a': '5'})
    """
    return _name, kwargs

class Types(object):
    """Convenience factory for list elements in API requests.
    
        >>> types = Types()
        >>> types.line(id="5")
        ('line', {'id': '5'})
    
    A module-scoped instance is available as refreshbooks.api.types.
    """
    
    def __getattr__(self, name):
        return functools.partial(list_element_type, name)

types = Types()
########NEW FILE########
__FILENAME__ = client
class RemoteMethod(object):
    """Ties python method calls into FreshBooks API calls.
    
    See Client.
    """
    
    def __init__(self, names, request_encoder, transport, response_decoder):
        self.names = names
        self.request_encoder = request_encoder
        self.transport = transport
        self.response_decoder = response_decoder
    
    def __call__(self, *args, **kwargs):
        method = '.'.join(self.names)
        
        request = self.request_encoder(method, *args, **kwargs)
        raw_response = self.transport(request)
        return self.response_decoder(raw_response)
    
    def __getattr__(self, name):
        return RemoteMethod(
            self.names + [name],
            self.request_encoder,
            self.transport,
            self.response_decoder
        )

class FailedRequest(Exception):
    def __init__(self, error):
        self.error = error
    
    def __str__(self):
        return repr(self.error)

class Client(object):
    """The Freshbooks API client. Callers should use one of the factory
    methods (BasicAuthClient, OAuthClient) to create instances.
    """
    
    def __init__(self, request_encoder, transport, response_decoder):
        self.request_encoder = request_encoder
        self.transport = transport
        self.response_decoder = response_decoder
    
    def __getattr__(self, name):
        return RemoteMethod(
            [name],
            self.request_encoder,
            self.transport,
            self.response_decoder
        )

########NEW FILE########
__FILENAME__ = elements
from lxml import etree

def field(name, value):
    field_element = etree.Element(name)
    field_element.text = value
    return field_element

def type(name, fields):
    type_element = etree.Element(name)
    
    for field in fields:
        type_element.append(field)
    
    return type_element

def request(name, parameters, _element_name='request'):
    request_element = type(_element_name, parameters)
    request_element.attrib.update(dict(method=name))
    return request_element

########NEW FILE########
__FILENAME__ = exceptions
class TransportException(Exception):
    def __init__(self, status, content):
        self.status = status
        self.content = content
    
    def __str__(self):
        return repr(self)
    
    def __repr__(self):
        return "TransportException(%r, %r)" % (self.status, self.content)

########NEW FILE########
__FILENAME__ = oauth
from __future__ import absolute_import

import oauth.oauth as oauth

class OAuthAuthorization(object):
    """Generates headers for an OAuth Core 1.0 Revision A (say that three 
    times fast) request, given an oauth.Consumer and an oauth.Token.
    
        >>> import oauth.oauth as oauth
        >>> consumer = oauth.OAuthConsumer("EXAMPLE", "CONSUMER")
        >>> token = oauth.OAuthToken("EXAMPLE", "TOKEN")
        >>> auth = OAuthAuthorization(consumer, token)
        >>> auth() # doctest:+ELLIPSIS
        {'Authorization': 'OAuth realm="", oauth_nonce="...", oauth_timestamp="...", oauth_consumer_key="EXAMPLE", oauth_signature_method="PLAINTEXT", oauth_version="1.0", oauth_token="EXAMPLE", oauth_signature="CONSUMER%26TOKEN"'}
    
    """
    def __init__(self, consumer, token, sig_method=oauth.OAuthSignatureMethod_PLAINTEXT()):
        self.consumer = consumer
        self.token = token
        self.sig_method = sig_method

    def __call__(self):
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(
            self.consumer,
            token=self.token
        )
        oauth_request.sign_request(self.sig_method, self.consumer, self.token)
        return oauth_request.to_header()

def OAuthClient(
    AuthorizingClient,
    domain,
    consumer_key,
    consumer_secret,
    token,
    token_secret,
    user_agent,
    request_encoder,
    response_decoder
):
    consumer = oauth.OAuthConsumer(consumer_key, consumer_secret)
    token = oauth.OAuthToken(token, token_secret)

    return AuthorizingClient(
        domain,
        OAuthAuthorization(
            consumer,
            token
        ),
        request_encoder,
        response_decoder,
        user_agent=user_agent
    )

########NEW FILE########
__FILENAME__ = test_adapters
from lxml import etree

from refreshbooks import adapters

def test_request_xml_simple():
    xml = adapters.xml_request('client.list')
    
    # test that xml looks roughly like <request method="client.list"/>
    request_document = etree.fromstring(xml)
    assert 'request' == request_document.tag
    assert {'method': 'client.list'} == request_document.attrib
    assert 0 == len(request_document)

def test_request_xml_simple_params():
    xml = adapters.xml_request('client.get', id="5", monkey="butter")
    
    # test that xml looks roughly like either
    # <request method="client.get"><id>5</id><monkey>butter</monkey></request>
    # or
    # <request method="client.get"><monkey>butter</monkey><id>5</id></request>
    #
    # (We don't actually care which.)
    request_document = etree.fromstring(xml)
    assert 'request' == request_document.tag
    assert {'method': 'client.get'} == request_document.attrib
    assert 2 == len(request_document)
    assert any(
        parameter.tag == 'id' and parameter.text == '5'
        for parameter in request_document
    )
    assert any(
        parameter.tag == 'monkey' and parameter.text == 'butter'
        for parameter in request_document
    )

def test_request_xml_dict_params():
    xml = adapters.xml_request(
        'client.get',
        id="5",
        monkey=dict(name="butter")
    )
    
    # test that xml looks roughly like either
    # <request method="client.get">
    #     <id>5</id>
    #     <monkey><name>butter</name></monkey>
    # </request>
    # or
    # <request method="client.get">
    #     <id>5</id>
    #     <monkey><name>butter</name></monkey>
    # </request>
    #
    # (We don't actually care which.)
    request_document = etree.fromstring(xml)
    assert 'request' == request_document.tag
    assert {'method': 'client.get'} == request_document.attrib
    assert 2 == len(request_document)
    assert any(
        parameter.tag == 'id' and parameter.text == '5'
        for parameter in request_document
    )
    assert any(
        parameter.tag == 'monkey' 
        and len(parameter) == 1
        and parameter[0].tag == 'name'
        and parameter[0].text == 'butter'
        for parameter in request_document
    )

def test_request_xml_list_params():
    xml = adapters.xml_request(
        'client.get',
        id="5",
        monkeys=[
            ('monkey', dict(name="butter"))
        ]
    )
    
    # test that xml looks roughly like either
    # <request method="client.get">
    #     <id>5</id>
    #     <monkeys>
    #         <monkey><name>butter</name></monkey>
    #     </monkeys>
    # </request>
    # or
    # <request method="client.get">
    #     <monkeys>
    #         <monkey><name>butter</name></monkey>
    #     </monkeys>
    #     <id>5</id>
    # </request>
    #
    # (We don't actually care which.)
    request_document = etree.fromstring(xml)
    assert 'request' == request_document.tag
    assert {'method': 'client.get'} == request_document.attrib
    assert 2 == len(request_document)
    assert any(
        parameter.tag == 'id' and parameter.text == '5'
        for parameter in request_document
    )
    assert any(
        parameter.tag == 'monkeys' 
        and len(parameter) == 1
        and parameter[0].tag == 'monkey'
        and len(parameter[0]) == 1
        and parameter[0][0].tag == 'name'
        and parameter[0][0].text == 'butter'
        for parameter in request_document
    )

########NEW FILE########
__FILENAME__ = test_client
import mock
from mock import sentinel

from refreshbooks import client

def test_arbitrary_method():
    request_encoder = mock.Mock()
    request_encoder.return_value = sentinel.request
    
    transport = mock.Mock()
    transport.return_value = sentinel.transport_response
    
    response_decoder = mock.Mock()
    response_decoder.return_value = sentinel.response
    
    test_client = client.Client(
        request_encoder,
        transport,
        response_decoder
    )
    
    response = test_client.arbitrary.method(id=5)
    
    assert (('arbitrary.method', ), dict(id=5)) == request_encoder.call_args
    assert ((sentinel.request, ), {}) == transport.call_args
    assert ((sentinel.transport_response, ), {}) == response_decoder.call_args
    assert sentinel.response == response

########NEW FILE########
__FILENAME__ = test_elements
from lxml import etree
from refreshbooks import elements

def test_field():
    field_element = elements.field("example", "A Test Value Here")
    
    assert "<example>A Test Value Here</example>" == etree.tostring(
        field_element
    )

def test_simple_type_strings():
    type_element = elements.type("example", [
        elements.field('name', 'Bob'),
        elements.field('age', '27')
    ])
    
    assert 'example' == type_element.tag
    assert 2 == len(type_element)
    assert 'name' == type_element[0].tag
    assert 'Bob' == type_element[0].text
    assert 'age' == type_element[1].tag
    assert '27' == type_element[1].text

def test_simple_request():
    body = elements.field("foo", "bar")
    
    request_element = elements.request("client.list", [body])
    
    assert 'request' == request_element.tag
    assert {'method': 'client.list'} == request_element.attrib
    assert 1 == len(request_element)
    assert body == request_element[0]

########NEW FILE########
__FILENAME__ = test_transports
from mock import patch, Mock, sentinel
from nose.tools import raises
from nose.plugins.attrib import attr
from nose.plugins.skip import SkipTest
from refreshbooks.exceptions import TransportException

@attr('integration')
@raises(TransportException)
def test_urllib2_transport_exception():
    from refreshbooks.transports.use_urllib2 import Transport
    Transport('http://httpstat.us/400', dict)("foo")

@attr('integration')
def test_urllib2():
    from refreshbooks.transports.use_urllib2 import Transport
    assert len(Transport('http://httpstat.us/200', dict)("foo")) > 0

@attr('integration')
@raises(TransportException)
def test_httplib2_transport_exception():
    try:
        import httplib2
    except ImportError:
        raise SkipTest("module 'httplib2' not installed")
    from refreshbooks.transports.use_httplib2 import Transport
    Transport('http://httpstat.us/400', dict)("foo")

@attr('integration')
def test_httplib2():
    try:
        import httplib2
    except ImportError:
        raise SkipTest("module 'httplib2' not installed")
    from refreshbooks.transports.use_httplib2 import Transport
    assert len(Transport('http://httpstat.us/200', dict)("foo")) > 0

@attr('integration')
@raises(TransportException)
def test_requests_transport_exception():
    try:
        import requests
    except ImportError:
        raise SkipTest("module 'requests' not installed")
    from refreshbooks.transports.use_requests import Transport
    Transport('http://httpstat.us/400', dict)("foo")

@attr('integration')
def test_requests():
    try:
        import requests
    except ImportError:
        raise SkipTest("module 'requests' not installed")
    from refreshbooks.transports.use_requests import Transport
    assert len(Transport('http://httpstat.us/200', dict)("foo")) > 0

########NEW FILE########
__FILENAME__ = transport
import base64

from refreshbooks import exceptions

try:
    from refreshbooks.optional import oauth as os
    
    OAuthAuthorization = os.OAuthAuthorization
except ImportError:
    def OAuthAuthorization(consumer, token, sig_method=None):
        raise NotImplementedError('oauth support requires the "oauth" module.')

try:
    from refreshbooks.transports import use_requests as transport
except ImportError:
    try:
        from refreshbooks.transports import use_httplib2 as transport
    except ImportError:
        import warnings
        warnings.warn(
            "Unable to load requests or httplib2 transports, falling back to urllib2. SSL cert verification disabled."
        )
        from refreshbooks.transports import use_urllib2 as transport

class TokenAuthorization(object):
    """Generates HTTP BASIC authentication headers obeying FreshBooks'
    token-based auth scheme (token as username, password irrelevant).
    
        >>> auth = TokenAuthorization("monkey")
        >>> auth()
        {'Authorization': 'Basic bW9ua2V5Og=='}
    
    Prefer OAuthAuthorization, from refreshbooks.optional.oauth, for new
    development.
    """
    def __init__(self, token):
        try:
            token = token.encode('US-ASCII')
        except NameError:
            # token already byte string.
            pass
        # See RFC 2617.
        base64_user_pass = base64.b64encode(token + b':').decode('US-ASCII')
        
        self.headers = {
            'Authorization': 'Basic %s' % (base64_user_pass, )
        }
    
    def __call__(self):
        return self.headers

class UserAgentHeaders(object):
    def __init__(self, base_headers_factory, user_agent):
        self.base_headers_factory = base_headers_factory
        self.user_agent = user_agent
    
    def __call__(self):
        headers = self.base_headers_factory()
        headers['User-Agent'] = self.user_agent
        return headers

class KeepAliveHeaders(object):
    def __init__(self, base_headers_factory):
        self.base_headers_factory = base_headers_factory
    
    def __call__(self):
        headers = self.base_headers_factory()
        headers['Connection'] = 'Keep-Alive'
        return headers

HttpTransport = transport.Transport
TransportException = exceptions.TransportException

########NEW FILE########
__FILENAME__ = use_httplib2
import httplib2

from refreshbooks import exceptions as exc

class Transport(object):
    def __init__(self, url, headers_factory):
        self.client = httplib2.Http()
        self.url = url
        self.headers_factory = headers_factory
    
    def __call__(self, entity):
        
        resp, content = self.client.request(
            self.url,
            'POST',
            headers=self.headers_factory(),
            body=entity
        )
        if resp.status >= 400:
            raise exc.TransportException(resp.status, content)
        
        return content

########NEW FILE########
__FILENAME__ = use_requests
import requests

from refreshbooks import exceptions as exc

class Transport(object):
    def __init__(self, url, headers_factory):
        self.session = requests.session()
        self.url = url
        self.headers_factory = headers_factory
    
    def __call__(self, entity):
        
        resp = self.session.post(
            self.url,
            headers=self.headers_factory(),
            data=entity
        )
        if resp.status_code >= 400:
            raise exc.TransportException(resp.status_code, resp.content)
        
        return resp.content

########NEW FILE########
__FILENAME__ = use_urllib2
import sys
if sys.version_info.major == 3:
    import urllib.request as u
else:
    import urllib2 as u

from refreshbooks import exceptions as exc

class Transport(object):
    def __init__(self, url, headers_factory):
        self.url = url
        self.headers_factory = headers_factory
    
    def __call__(self, entity):
        request = u.Request(
            url=self.url,
            data=entity,
            headers=self.headers_factory()
        )
        try:
            return u.urlopen(request).read()
        except u.HTTPError as e:
            raise exc.TransportException(e.code, e.read())

########NEW FILE########
