__FILENAME__ = errors
from six.moves import http_client as httplib
from xml.etree import ElementTree
import six


class ResponseError(Exception):

    """An error received from the Recurly API in response to an HTTP
    request."""

    def __init__(self, response_xml):
        self.response_xml = response_xml

    @property
    def response_doc(self):
        """The XML document received from the service."""
        try:
            return self.__dict__['response_doc']
        except KeyError:
            self.__dict__['response_doc'] = ElementTree.fromstring(self.response_xml)
            return self.__dict__['response_doc']

    @property
    def symbol(self):
        """The machine-readable identifier for the error."""
        el = self.response_doc.find('symbol')
        if el is not None:
            return el.text

    @property
    def message(self):
        """The human-readable description of the error."""
        el = self.response_doc.find('description')
        if el is not None:
            return el.text

    @property
    def details(self):
        """A further human-readable elaboration on the error."""
        el = self.response_doc.find('details')
        if el is not None:
            return el.text

    @property
    def error(self):
        """A fall-back error message in the event no more specific
        error is given."""
        el = self.response_doc.find('error')
        if el is not None:
            return el.text

    def __str__(self):
        return six.text_type(self).encode('utf8')

    def __unicode__(self):
        symbol = self.symbol
        if symbol is None:
            return self.error
        details = self.details
        if details is not None:
            return six.u('%s: %s %s') % (symbol, self.message, details)
        return six.u('%s: %s') % (symbol, self.message)


class ClientError(ResponseError):
    """An error resulting from a problem in the client's request (that
    is, an error with an HTTP ``4xx`` status code)."""
    pass


class BadRequestError(ClientError):
    """An error showing the request was invalid or could not be
    understood by the server.

    The error was returned as a ``400 Bad Request`` response.
    Resubmitting the request will likely result in the same error.

    """
    pass


class UnauthorizedError(ClientError):

    """An error for a missing or invalid API key (HTTP ``401 Unauthorized``)."""

    def __init__(self, response_xml):
        self.response_text = response_xml

    def __str__(self):
        return six.text_type(self).encode('utf-8')

    def __unicode__(self):
        return six.text_type(self.response_text)


class PaymentRequiredError(ClientError):
    """An error indicating your Recurly account is in production mode
    but is not in good standing (HTTP ``402 Payment Required``)."""
    pass


class ForbiddenError(ClientError):
    """An error showing the request represented an action the client
    does not have privileges to access.

    This error was returned as a ``403 Forbidden`` response. Verify
    your login credentials are for the appropriate account.

    """
    pass


class NotFoundError(ClientError):
    """An error for when the resource was not found with the given
    identifier (HTTP ``404 Not Found``)."""
    pass


class NotAcceptableError(ClientError):
    """An error for when the client's request could not be accepted by
    the remote service (HTTP ``406 Not Acceptable``)."""
    pass


class PreconditionFailedError(ClientError):
    """An error for a request that was unsuccessful because a condition
    was not met.

    For example, this error may arise if you attempt to cancel a
    subscription for an account that has no subscription. This error
    corresponds to the HTTP ``412 Precondition Failed`` status code.

    """
    pass


class UnsupportedMediaTypeError(ClientError):
    """An error resulting from the submission as an unsupported media
    type (HTTP ``415 Unsupported Media Type``)."""
    pass


class ValidationError(ClientError):

    """An error indicating some values in the submitted request body
    were not valid."""

    class Suberror(object):

        """An error describing the invalidity of a single invalid
        field."""

        def __init__(self, field, symbol, message):
            self.field = field
            self.symbol = symbol
            self.message = message

        def __str__(self):
            return self.message.encode('utf8')

        def __unicode__(self):
            return six.u('%s: %s %s') % (self.symbol, self.field, self.message)

    @property
    def errors(self):
        """A dictionary of error objects, keyed on the name of the
        request field that was invalid.

        Each error value has `field`, `symbol`, and `message`
        attributes describing the particular invalidity of that field.

        """
        try:
            return self.__dict__['errors']
        except KeyError:
            pass

        suberrors = dict()
        for err in self.response_doc.findall('error'):
            field = err.attrib['field']
            symbol = err.attrib['symbol']
            message = err.text

            suberrors[field] = self.Suberror(field, symbol, message)

        self.__dict__['errors'] = suberrors
        return suberrors

    def __unicode__(self):
        return six.u('; ').join(six.text_type(error) for error in self.errors.itervalues())


class ServerError(ResponseError):
    """An error resulting from a problem creating the server's response
    to the request (that is, an error with an HTTP ``5xx`` status code)."""
    pass


class InternalServerError(ServerError):
    """An unexpected general server error (HTTP ``500 Internal Server
    Error``)."""
    pass


class BadGatewayError(ServerError):
    """An error resulting when the load balancer or web server has
    trouble connecting to the Recurly app.

    This error is returned as an HTTP ``502 Bad Gateway`` response.
    Try the request again.

    """
    pass


class ServiceUnavailableError(ServerError):
    """An error indicating the service is temporarily unavailable.

    This error results from an HTTP ``503 Service Unavailable``
    response. Try the request again.

    """
    pass


class UnexpectedStatusError(ResponseError):

    """An error resulting from an unexpected status code returned by
    the remote service."""

    def __init__(self, status, response_xml):
        super(UnexpectedStatusError, self).__init__(response_xml)
        self.status = status

    def __unicode__(self):
        return six.text_type(self.status)


error_classes = {
    400: BadRequestError,
    401: UnauthorizedError,
    402: PaymentRequiredError,
    403: ForbiddenError,
    404: NotFoundError,
    406: NotAcceptableError,
    412: PreconditionFailedError,
    415: UnsupportedMediaTypeError,
    422: ValidationError,
    500: InternalServerError,
    502: BadGatewayError,
    503: ServiceUnavailableError,
}


def error_class_for_http_status(status):
    """Return the appropriate `ResponseError` subclass for the given
    HTTP status code."""
    try:
        return error_classes[status]
    except KeyError:
        def new_status_error(xml_response):
            return UnexpectedStatusError(status, xml_response)
        return new_status_error


__all__ = [x.__name__ for x in error_classes.values()]

########NEW FILE########
__FILENAME__ = js
import base64
import hashlib
import hmac
import os
import re
import time
import six
from six.moves.urllib.parse import urljoin, quote_plus

import recurly


PRIVATE_KEY = None


class RequestForgeryError(Exception):
    """An error raised when verification of a Recurly.js response fails."""
    pass


def sign(*records):
    """ Signs objects or data dictionary with your Recurly.js private key."""
    if PRIVATE_KEY is None:
        raise ValueError("Recurly.js private key is not set.")
    records = list(records)
    try:
        data = records.pop() if type(records[-1]) is dict else {}
    except IndexError:
        data = {}
    for record in records:
        data[record.__class__.nodename] = record.__dict__
    if 'timestamp' not in data:
        data['timestamp'] = int(time.time())
    if 'nonce' not in data:
        data['nonce'] = re.sub(six.b('\W+'), six.b(''), base64.b64encode(os.urandom(32)))
    unsigned = to_query(data)
    signed = hmac.new(six.b(PRIVATE_KEY), six.b(unsigned), hashlib.sha1).hexdigest()
    return '|'.join([signed, unsigned])


def fetch(token):
    url = urljoin(recurly.base_uri(), 'recurly_js/result/%s' % token)
    resp, elem = recurly.Resource.element_for_url(url)
    cls = recurly.Resource.value_for_element(elem)
    return cls.from_element(elem)


def to_query(object, key=None):
    """ Dumps a dictionary into a nested query string."""
    object_type = type(object)
    if object_type is dict:
        return '&'.join([to_query(object[k], '%s[%s]' % (key, k) if key else k) for k in sorted(object)])
    elif object_type in (list, tuple):
        return '&'.join([to_query(o, '%s[]' % key) for o in object])
    else:
        return '%s=%s' % (quote_plus(str(key)), quote_plus(str(object)))

########NEW FILE########
__FILENAME__ = link_header
#!/usr/bin/env python
# source: https://gist.github.com/1103172
from __future__ import print_function

"""
HTTP Link Header Parsing

Simple routines to parse and manipulate Link headers.
"""

__license__ = """
Copyright (c) 2009 Mark Nottingham
 
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
 
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
 
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import re

TOKEN = r'(?:[^\(\)<>@,;:\\"/\[\]\?={} \t]+?)'
QUOTED_STRING = r'(?:"(?:\\"|[^"])*")'
PARAMETER = r'(?:%(TOKEN)s(?:=(?:%(TOKEN)s|%(QUOTED_STRING)s))?)' % locals()
LINK = r'<[^>]*>\s*(?:;\s*%(PARAMETER)s?\s*)*' % locals()
COMMA = r'(?:\s*(?:,\s*)+)'
LINK_SPLIT = r'%s(?=%s|\s*$)' % (LINK, COMMA)


def _unquotestring(instr):
    if instr[0] == instr[-1] == '"':
        instr = instr[1:-1]
        instr = re.sub(r'\\(.)', r'\1', instr)
    return instr


def _splitstring(instr, item, split):
    if not instr:
        return []
    return [h.strip() for h in re.findall(r'%s(?=%s|\s*$)' % (item, split), instr)]

link_splitter = re.compile(LINK_SPLIT)


def parse_link_value(instr):
    """
    Given a link-value (i.e., after separating the header-value on commas), 
    return a dictionary whose keys are link URLs and values are dictionaries
    of the parameters for their associated links.
    
    Note that internationalised parameters (e.g., title*) are 
    NOT percent-decoded.
    
    Also, only the last instance of a given parameter will be included.
    
    For example, 
    
    >>> parse_link_value('</foo>; rel="self"; title*=utf-8\'de\'letztes%20Kapitel')
    {'/foo': {'title*': "utf-8'de'letztes%20Kapitel", 'rel': 'self'}}
    
    """
    out = {}
    if not instr:
        return out
    for link in [h.strip() for h in link_splitter.findall(instr)]:
        url, params = link.split(">", 1)
        url = url[1:]
        param_dict = {}
        for param in _splitstring(params, PARAMETER, "\s*;\s*"):
            try:
                a, v = param.split("=", 1)
                param_dict[a.lower()] = _unquotestring(v)
            except ValueError:
                param_dict[param.lower()] = None
        out[url] = param_dict
    return out


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        print(parse_link_value(sys.argv[1]))
########NEW FILE########
__FILENAME__ = resource
import base64
from datetime import datetime
import logging
import socket
import ssl
import sys
from xml.etree import ElementTree

import iso8601
import six

import recurly
import recurly.errors
from recurly.link_header import parse_link_value
from six.moves import http_client
from six.moves.urllib.parse import urlencode, urljoin, urlsplit


if six.PY3:
    from ssl import match_hostname
else:
    from backports.ssl_match_hostname import match_hostname


class Money(object):

    """An amount of money in one or more currencies."""

    def __init__(self, *args, **kwargs):
        if args and kwargs:
            raise ValueError("Money may be single currency or multi-currency but not both")
        elif kwargs:
            self.currencies = dict(kwargs)
        elif args and len(args) > 1:
            raise ValueError("Multi-currency Money must be instantiated with codes")
        elif args:
            self.currencies = { recurly.DEFAULT_CURRENCY: args[0] }
        else:
            self.currencies = dict()

    @classmethod
    def from_element(cls, elem):
        currency = dict()
        for child_el in elem:
            if not child_el.tag:
                continue
            currency[child_el.tag] = int(child_el.text)
        return cls(**currency)

    def add_to_element(self, elem):
        for currency, amount in self.currencies.items():
            currency_el = ElementTree.Element(currency)
            currency_el.attrib['type'] = 'integer'
            currency_el.text = six.text_type(amount)
            elem.append(currency_el)

    def __getitem__(self, name):
        return self.currencies[name]

    def __setitem__(self, name, value):
        self.currencies[name] = value

    def __delitem__(self, name, value):
        del self.currencies[name]

    def __contains__(self, name):
        return name in self.currencies


class PageError(ValueError):
    """An error raised when requesting to continue to a stream page that
    doesn't exist.

    This error can be raised when requesting the next page for the last page in
    a series, or the first page for the first page in a series.

    """
    pass


class Page(list):

    """A set of related `Resource` instances retrieved together from
    the API.

    Use `Page` instances as `list` instances to access their contents.

    """
    def __iter__(self):
        if not self:
            raise StopIteration
        page = self
        while page:
            for x in list.__iter__(page):
                yield x
            try:
                page = page.next_page()
            except PageError:
                try:
                    del self.next_url
                except AttributeError:
                    pass
                raise StopIteration

    def __len__(self):
        try:
            if not self.record_size:
                return 0
            else:
                return int(self.record_size)
        except AttributeError:
            return 0


    def next_page(self):
        """Return the next `Page` after this one in the result sequence
        it's from.

        If the current page is the last page in the sequence, calling
        this method raises a `ValueError`.

        """
        try:
            next_url = self.next_url
        except AttributeError:
            raise PageError("Page %r has no next page" % self)
        return self.page_for_url(next_url)

    def first_page(self):
        """Return the first `Page` in the result sequence this `Page`
        instance is from.

        If the current page is already the first page in the sequence,
        calling this method raises a `ValueError`.

        """
        try:
            start_url = self.start_url
        except AttributeError:
            raise PageError("Page %r is already the first page" % self)
        return self.page_for_url(start_url)

    @classmethod
    def page_for_url(cls, url):
        """Return a new `Page` containing the items at the given
        endpoint URL."""
        resp, elem = Resource.element_for_url(url)

        value = Resource.value_for_element(elem)

        return cls.page_for_value(resp, value)

    @classmethod
    def page_for_value(cls, resp, value):
        """Return a new `Page` representing the given resource `value`
        retrieved using the HTTP response `resp`.

        This method records pagination ``Link`` headers present in `resp`, so
        that the returned `Page` can return their resources from its
        `next_page()` and `first_page()` methods.

        """
        page = cls(value)
        page.record_size = resp.getheader('X-Records')
        links = parse_link_value(resp.getheader('Link'))
        for url, data in six.iteritems(links):
            if data.get('rel') == 'start':
                page.start_url = url
            if data.get('rel') == 'next':
                page.next_url = url

        return page


class _ValidatedHTTPSConnection(http_client.HTTPSConnection):

    """An `http_client.HTTPSConnection` that validates the SSL connection by
    requiring certificate validation and checking the connection's intended
    hostname again the validated certificate's possible hosts."""

    def connect(self):
        socket_timeout = recurly.SOCKET_TIMEOUT_SECONDS or self.timeout
        if sys.version_info < (2, 7):
            sock = socket.create_connection((self.host, self.port),
                                            socket_timeout)
        else:
            sock = socket.create_connection((self.host, self.port),
                                            socket_timeout, self.source_address)

        if self._tunnel_host:
            self.sock = sock
            self._tunnel()

        ssl_sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
            ssl_version=ssl.PROTOCOL_SSLv3, cert_reqs=ssl.CERT_REQUIRED,
            ca_certs=recurly.CA_CERTS_FILE)

        # Let the CertificateError for failure be raised to the caller.
        match_hostname(ssl_sock.getpeercert(), self.host)

        self.sock = ssl_sock


class Resource(object):

    """A Recurly API resource.

    This superclass implements the general behavior for all the
    specific Recurly API resources.

    All method parameters and return values that are XML elements are
    `xml.etree.ElementTree.Element` instances.

    """

    _classes_for_nodename = dict()

    sensitive_attributes = ()
    """Attributes that are not logged with the rest of a `Resource`
    of this class when submitted in a ``POST`` or ``PUT`` request."""
    xml_attribute_attributes = ()
    """Attributes of a `Resource` of this class that are not serialized
    as subelements, but rather attributes of the top level element."""
    inherits_currency = False
    """Whether a `Resource` of this class inherits a currency from a
    parent `Resource`, and therefore should not use `Money` instances
    even though this `Resource` class has no ``currency`` attribute of
    its own."""

    def __init__(self, **kwargs):
        try:
            self.attributes.index('currency') # Test for currency attribute,
            self.currency                     # and test if it's set.
        except ValueError:
            pass
        except AttributeError:
            self.currency = recurly.DEFAULT_CURRENCY

        for key, value in six.iteritems(kwargs):
            setattr(self, key, value)

    @classmethod
    def http_request(cls, url, method='GET', body=None, headers=None):
        """Make an HTTP request with the given method to the given URL,
        returning the resulting `http_client.HTTPResponse` instance.

        If the `body` argument is a `Resource` instance, it is serialized
        to XML by calling its `to_element()` method before submitting it.
        Requests are authenticated per the Recurly API specification
        using the ``recurly.API_KEY`` value for the API key.

        Requests and responses are logged at the ``DEBUG`` level to the
        ``recurly.http.request`` and ``recurly.http.response`` loggers
        respectively.

        """
        urlparts = urlsplit(url)
        if urlparts.scheme != 'https':
            connection = http_client.HTTPConnection(urlparts.netloc)
        elif recurly.CA_CERTS_FILE is None:
            connection = http_client.HTTPSConnection(urlparts.netloc)
        else:
            connection = _ValidatedHTTPSConnection(urlparts.netloc)

        headers = {} if headers is None else dict(headers)
        headers.setdefault('Accept', 'application/xml')
        headers.update({
            'User-Agent': 'recurly-python/%s' % recurly.__version__,
        })
        if recurly.API_KEY is None:
            raise recurly.UnauthorizedError('recurly.API_KEY not set')
        headers['Authorization'] = 'Basic %s' % base64.b64encode(six.b('%s:' % recurly.API_KEY)).decode()

        log = logging.getLogger('recurly.http.request')
        if log.isEnabledFor(logging.DEBUG):
            log.debug("%s %s HTTP/1.1", method, url)
            for header, value in six.iteritems(headers):
                if header == 'Authorization':
                    value = '<redacted>'
                log.debug("%s: %s", header, value)
            log.debug('')
            if method in ('POST', 'PUT') and body is not None:
                if isinstance(body, Resource):
                    log.debug(body.as_log_output())
                else:
                    log.debug(body)

        if isinstance(body, Resource):
            body = ElementTree.tostring(body.to_element(), encoding='UTF-8')
            headers['Content-Type'] = 'application/xml; charset=utf-8'
        if method in ('POST', 'PUT') and body is None:
            headers['Content-Length'] = '0'
        connection.request(method, url, body, headers)
        if recurly.SOCKET_TIMEOUT_SECONDS:
            connection.sock.settimeout(recurly.SOCKET_TIMEOUT_SECONDS)
        resp = connection.getresponse()

        log = logging.getLogger('recurly.http.response')
        if log.isEnabledFor(logging.DEBUG):
            log.debug("HTTP/1.1 %d %s", resp.status, resp.reason)
            if six.PY2:
                for header in resp.msg.headers:
                    log.debug(header.rstrip('\n'))
            else:
                log.debug(resp.msg._headers)
            log.debug('')

        return resp

    def as_log_output(self):
        """Returns an XML string containing a serialization of this
        instance suitable for logging.

        Attributes named in the instance's `sensitive_attributes` are
        redacted.

        """
        elem = self.to_element()
        for attrname in self.sensitive_attributes:
            for sensitive_el in elem.iter(attrname):
                sensitive_el.text = 'XXXXXXXXXXXXXXXX'
        return ElementTree.tostring(elem, encoding='UTF-8')

    @classmethod
    def _learn_nodenames(cls, classes):
        for resource_class in classes:
            try:
                rc_is_subclass = issubclass(resource_class, cls)
            except TypeError:
                continue
            if not rc_is_subclass:
                continue
            nodename = getattr(resource_class, 'nodename', None)
            if nodename is None:
                continue

            cls._classes_for_nodename[nodename] = resource_class

    @classmethod
    def get(cls, uuid):
        """Return a `Resource` instance of this class identified by
        the given code or UUID.

        Only `Resource` classes with specified `member_path` attributes
        can be directly requested with this method.

        """
        url = urljoin(recurly.base_uri(), cls.member_path % (uuid,))
        resp, elem = cls.element_for_url(url)
        return cls.from_element(elem)

    @classmethod
    def element_for_url(cls, url):
        """Return the resource at the given URL, as a
        (`http_client.HTTPResponse`, `xml.etree.ElementTree.Element`) tuple
        resulting from a ``GET`` request to that URL."""
        response = cls.http_request(url)
        if response.status != 200:
            cls.raise_http_error(response)

        assert response.getheader('Content-Type').startswith('application/xml')

        response_xml = response.read()
        logging.getLogger('recurly.http.response').debug(response_xml)
        response_doc = ElementTree.fromstring(response_xml)

        return response, response_doc

    @classmethod
    def _subclass_for_nodename(cls, nodename):
        try:
            return cls._classes_for_nodename[nodename]
        except KeyError:
            raise ValueError("Could not determine resource class for array member with tag %r"
                % nodename)

    @classmethod
    def value_for_element(cls, elem):
        """Deserialize the given XML `Element` into its representative
        value.

        Depending on the content of the element, the returned value may be:
        * a string, integer, or boolean value
        * a `datetime.datetime` instance
        * a list of `Resource` instances
        * a single `Resource` instance
        * a `Money` instance
        * ``None``

        """
        log = logging.getLogger('recurly.resource')
        if elem is None:
            log.debug("Converting %r element into None value", elem)
            return

        if elem.attrib.get('nil') is not None:
            log.debug("Converting %r element with nil attribute into None value", elem.tag)
            return

        if elem.tag.endswith('_in_cents') and 'currency' not in cls.attributes and not cls.inherits_currency:
            log.debug("Converting %r element in class with no matching 'currency' into a Money value", elem.tag)
            return Money.from_element(elem)

        attr_type = elem.attrib.get('type')
        log.debug("Converting %r element with type %r", elem.tag, attr_type)
        if attr_type == 'integer':
            return int(elem.text.strip())
        if attr_type == 'float':
            return float(elem.text.strip())
        if attr_type == 'boolean':
            return elem.text.strip() == 'true'
        if attr_type == 'datetime':
            return iso8601.parse_date(elem.text.strip())
        if attr_type == 'array':
            return [cls._subclass_for_nodename(sub_elem.tag).from_element(sub_elem) for sub_elem in elem]

        # Unknown types may be the names of resource classes.
        if attr_type is not None:
            try:
                value_class = cls._subclass_for_nodename(attr_type)
            except ValueError:
                log.debug("Not converting %r element with type %r to a resource as that matches no known nodename",
                    elem.tag, attr_type)
            else:
                return value_class.from_element(elem)

        # Untyped complex elements should still be resource instances. Guess from the nodename.
        if len(elem):  # has children
            value_class = cls._subclass_for_nodename(elem.tag)
            log.debug("Converting %r tag into a %s", elem.tag, value_class.__name__)
            return value_class.from_element(elem)

        value = elem.text or ''
        return value.strip()

    @classmethod
    def element_for_value(cls, attrname, value):
        """Serialize the given value into an XML `Element` with the
        given tag name, returning it.

        The value argument may be:
        * a `Resource` instance
        * a list or tuple of `Resource` instances
        * a `Money` instance
        * a `datetime.datetime` instance
        * a string, integer, or boolean value
        * ``None``

        """
        if isinstance(value, Resource):
            return value.to_element()

        el = ElementTree.Element(attrname)

        if value is None:
            el.attrib['nil'] = 'nil'
        elif isinstance(value, bool):
            el.attrib['type'] = 'boolean'
            el.text = 'true' if value else 'false'
        elif isinstance(value, int):
            el.attrib['type'] = 'integer'
            el.text = str(value)
        elif isinstance(value, datetime):
            el.attrib['type'] = 'datetime'
            el.text = value.strftime('%Y-%m-%dT%H:%M:%SZ')
        elif isinstance(value, list) or isinstance(value, tuple):
            el.attrib['type'] = 'array'
            for sub_resource in value:
                try:
                    elementize = sub_resource.to_element
                except AttributeError:
                    raise ValueError("Could not serialize member %r of list %r as a Resource instance"
                        % (sub_resource, attrname))
                el.append(elementize())
        elif isinstance(value, Money):
            value.add_to_element(el)
        else:
            el.text = six.text_type(value)

        return el

    @classmethod
    def paginated(self, url):
        """ Exposes Page.page_for_url in Resource """
        return Page.page_for_url(url)

    @classmethod
    def from_element(cls, elem):
        """Return a new instance of this `Resource` class representing
        the given XML element."""
        return cls().update_from_element(elem)

    def update_from_element(self, elem):
        """Reset this `Resource` instance to represent the values in
        the given XML element."""
        self._elem = elem

        for attrname in self.attributes:
            try:
                delattr(self, attrname)
            except AttributeError:
                pass

        document_url = elem.attrib.get('href')
        if document_url is not None:
            self._url = document_url

        return self

    def _make_actionator(self, url, method, extra_handler=None):
        def actionator(*args, **kwargs):
            if kwargs:
                full_url = '%s?%s' % (url, urlencode(kwargs))
            else:
                full_url = url

            body = args[0] if args else None
            response = self.http_request(full_url, method, body)

            if response.status == 200:
                response_xml = response.read()
                logging.getLogger('recurly.http.response').debug(response_xml)
                return self.update_from_element(ElementTree.fromstring(response_xml))
            elif response.status == 201:
                response_xml = response.read()
                logging.getLogger('recurly.http.response').debug(response_xml)
                elem = ElementTree.fromstring(response_xml)
                return self.value_for_element(elem)
            elif response.status == 204:
                pass
            elif extra_handler is not None:
                return extra_handler(response)
            else:
                self.raise_http_error(response)
        return actionator

    #usually the path is the same as the element name
    def __getpath__(self, name):
        return name

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)

        try:
            selfnode = self._elem
        except AttributeError:
            raise AttributeError(name)

        if name in self.xml_attribute_attributes:
            try:
                return selfnode.attrib[name]
            except KeyError:
                raise AttributeError(name)

        elem = selfnode.find(self.__getpath__(name))

        if elem is None:
            # It might be an <a name> link.
            for anchor_elem in selfnode.findall('a'):
                if anchor_elem.attrib.get('name') == name:
                    url = anchor_elem.attrib['href']
                    method = anchor_elem.attrib['method'].upper()
                    return self._make_actionator(url, method)

            raise AttributeError(name)

        # Follow links.
        if 'href' in elem.attrib:
            def make_relatitator(url):
                def relatitator(**kwargs):
                    if kwargs:
                        full_url = '%s?%s' % (url, urlencode(kwargs))
                    else:
                        full_url = url

                    resp, elem = Resource.element_for_url(full_url)
                    value = Resource.value_for_element(elem)

                    if isinstance(value, list):
                        return Page.page_for_value(resp, value)
                    return value
                return relatitator
            return make_relatitator(elem.attrib['href'])

        return self.value_for_element(elem)

    @classmethod
    def all(cls, **kwargs):
        """Return a `Page` of instances of this `Resource` class from
        its general collection endpoint.

        Only `Resource` classes with specified `collection_path`
        endpoints can be requested with this method. Any provided
        keyword arguments are passed to the API endpoint as query
        parameters.

        """
        url = urljoin(recurly.base_uri(), cls.collection_path)
        if kwargs:
            url = '%s?%s' % (url, urlencode(kwargs))
        return Page.page_for_url(url)

    def save(self):
        """Save this `Resource` instance to the service.

        If this is a new instance, it is created through a ``POST``
        request to its collection endpoint. If this instance already
        exists in the service, it is updated through a ``PUT`` request
        to its own URL.

        """
        if hasattr(self, '_url'):
            return self._update()
        return self._create()

    def _update(self):
        url = self._url
        response = self.http_request(url, 'PUT', self, {'Content-Type': 'application/xml; charset=utf-8'})
        if response.status != 200:
            self.raise_http_error(response)

        response_xml = response.read()
        logging.getLogger('recurly.http.response').debug(response_xml)
        self.update_from_element(ElementTree.fromstring(response_xml))

    def _create(self):
        url = urljoin(recurly.base_uri(), self.collection_path)
        return self.post(url)

    def post(self, url):
        """Sends this `Resource` instance to the service with a
        ``POST`` request to the given URL."""
        response = self.http_request(url, 'POST', self, {'Content-Type': 'application/xml; charset=utf-8'})
        if response.status not in (201, 204):
            self.raise_http_error(response)

        self._url = response.getheader('Location')

        if response.status == 201:
            response_xml = response.read()
            logging.getLogger('recurly.http.response').debug(response_xml)
            self.update_from_element(ElementTree.fromstring(response_xml))

    def delete(self):
        """Submits a deletion request for this `Resource` instance as
        a ``DELETE`` request to its URL."""
        url = self._url

        response = self.http_request(url, 'DELETE')
        if response.status != 204:
            self.raise_http_error(response)

    @classmethod
    def raise_http_error(cls, response):
        """Raise a `ResponseError` of the appropriate subclass in
        reaction to the given `http_client.HTTPResponse`."""
        response_xml = response.read()
        logging.getLogger('recurly.http.response').debug(response_xml)
        exc_class = recurly.errors.error_class_for_http_status(response.status)
        raise exc_class(response_xml)

    def to_element(self):
        """Serialize this `Resource` instance to an XML element."""
        elem = ElementTree.Element(self.nodename)
        for attrname in self.attributes:
            # Only use values that have been loaded into the internal
            # __dict__. For retrieved objects we look into the XML response at
            # access time, so the internal __dict__ contains only the elements
            # that have been set on the client side.
            try:
                value = self.__dict__[attrname]
            except KeyError:
                continue

            if attrname in self.xml_attribute_attributes:
                elem.attrib[attrname] = six.text_type(value)
            else:
                sub_elem = self.element_for_value(attrname, value)
                elem.append(sub_elem)
        return elem

########NEW FILE########
__FILENAME__ = recurlytests
from contextlib import contextmanager
from datetime import datetime
import email
import logging
import os
from os.path import join, dirname
import time
import unittest
from xml.etree import ElementTree

import mock
import six

from six.moves import http_client


def xml(text):
    doc = ElementTree.fromstring(text)
    for el in doc.iter():
        if el.text and el.text.isspace():
            el.text = ''
        if el.tail and el.tail.isspace():
            el.tail = ''
    return ElementTree.tostring(doc, encoding='UTF-8')


class MockRequestManager(object):

    def __init__(self, fixture):
        self.fixture = fixture

    def __enter__(self):
        self.request_context = mock.patch.object(http_client.HTTPConnection, 'request')
        self.request_context.return_value = None
        self.request_mock = self.request_context.__enter__()

        self.fixture_file = open(join(dirname(__file__), 'fixtures', self.fixture), 'rb')

        # Read through the request.
        preamble_line = self.fixture_file.readline().strip()
        try:
            self.method, self.uri, http_version = preamble_line.split(None, 2)
            self.method = self.method.decode()
            self.uri = self.uri.decode()
        except ValueError:
            raise ValueError("Couldn't parse preamble line from fixture file %r; does it have a fixture in it?"
                % self.fixture)

        # Read request headers
        def read_headers(fp):
            while True:
                try:
                    line = fp.readline()
                except EOFError:
                    return
                if not line or line == six.b('\n'):
                    return
                yield line

        if six.PY2:
            msg = http_client.HTTPMessage(self.fixture_file, 0)
            self.headers = dict((k, v.strip()) for k, v in (header.split(':', 1) for header in msg.headers))
        else:
            # http.client.HTTPMessage doesn't have importing headers from file
            msg = http_client.HTTPMessage()
            headers = email.message_from_bytes(six.b('').join(read_headers(self.fixture_file)))
            self.headers = dict((k, v.strip()) for k, v in headers._headers)
            # self.headers = {k: v for k, v in headers._headers}
        msg.fp = None

        # Read through to the vertical space.
        def nextline(fp):
            while True:
                try:
                    line = fp.readline()
                except EOFError:
                    return
                if not line or line.startswith(six.b('\x16')):
                    return
                yield line

        body = six.b('').join(nextline(self.fixture_file))  # exhaust the request either way
        self.body = None
        if self.method in ('PUT', 'POST'):
            if 'Content-Type' in self.headers:
                if 'application/xml' in self.headers['Content-Type']:
                    self.body = xml(body)
                else:
                    self.body = body

        # Set up the response returner.
        sock = mock.Mock()
        sock.makefile = mock.Mock(return_value=self.fixture_file)
        response = http_client.HTTPResponse(sock, method=self.method)
        response.begin()

        self.response_context = mock.patch.object(http_client.HTTPConnection, 'getresponse', lambda self: response)
        self.response_mock = self.response_context.__enter__()

        return self

    def assert_request(self):
        headers = dict(self.headers)
        if 'User-Agent' in headers:
            import recurly
            headers['User-Agent'] = headers['User-Agent'].replace('{version}', recurly.__version__)
        self.request_mock.assert_called_once_with(self.method, self.uri, self.body, headers)

    def __exit__(self, exc_type, exc_value, traceback):
        self.fixture_file.close()
        try:
            if exc_type is None:
                self.assert_request()
        finally:
            self.request_context.__exit__(exc_type, exc_value, traceback)
            self.response_context.__exit__(exc_type, exc_value, traceback)


@contextmanager
def noop_request_manager():
    yield


class RecurlyTest(unittest.TestCase):

    def mock_request(self, *args, **kwargs):
        return MockRequestManager(*args, **kwargs)

    def noop_mock_request(self, *args, **kwargs):
        return noop_request_manager()

    def mock_sleep(self, secs):
        pass

    def noop_mock_sleep(self, secs):
        time.sleep(secs)

    def setUp(self):
        import recurly

        # Mock everything out unless we have an API key.
        try:
            api_key = os.environ['RECURLY_API_KEY']
        except KeyError:
            # Mock everything out.
            recurly.API_KEY = 'apikey'
            self.test_id = 'mock'
        else:
            recurly.API_KEY = api_key
            recurly.CA_CERTS_FILE = os.environ.get('RECURLY_CA_CERTS_FILE')
            self.mock_request = self.noop_mock_request
            self.mock_sleep = self.noop_mock_sleep
            self.test_id = datetime.now().strftime('%Y%m%d%H%M%S')

        # Update our endpoint if we have a different test host.
        try:
            recurly_host = os.environ['RECURLY_HOST']
        except KeyError:
            pass
        else:
            recurly.BASE_URI = 'https://%s/v2/' % recurly_host

        logging.basicConfig(level=logging.INFO)
        logging.getLogger('recurly').setLevel(logging.DEBUG)

########NEW FILE########
__FILENAME__ = test_js
import re
import time
import unittest

import mock

from recurlytests import RecurlyTest
import recurly.js


class TestJs(RecurlyTest):

    def setUp(self):
        super(TestJs, self).setUp()
        recurly.js.PRIVATE_KEY = '0cc86846024a4c95a5dfd3111a532d13'

    def test_serialize(self):
        message = {
            'a': {
                'a1': 123,
                'a2': 'abcdef',
            },
            'b': [1,2,3],
            'c': {
                '1':4,
                '2':5,
                '3':6,
            },
            'd': ':',
        }
        self.assertEqual(recurly.js.to_query(message), 'a%5Ba1%5D=123&a%5Ba2%5D=abcdef&b%5B%5D=1&b%5B%5D=2&b%5B%5D=3&c%5B1%5D=4&c%5B2%5D=5&c%5B3%5D=6&d=%3A')

    def test_sign(self):
        self.assertTrue(re.search('nonce=', recurly.js.sign()))
        self.assertTrue(re.search('timestamp=', recurly.js.sign()))
        self.assertEqual(
            recurly.js.sign({'timestamp': 1312701386, 'nonce': 1}),
            '015662c92688f387159bcac9bc1fb250a1327886|nonce=1&timestamp=1312701386'
        )
        self.assertEqual(
            recurly.js.sign(recurly.Account(account_code='1'), {'timestamp': 1312701386, 'nonce': 1}),
            '82bcbbd4deb8b1b663b7407d9085dc67e2922df7|account%5Baccount_code%5D=1&nonce=1&timestamp=1312701386'
        )


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_recurly
import unittest
from xml.etree import ElementTree

from recurlytests import xml


class TestRecurly(unittest.TestCase):

    def test_hello(self):
        import recurly

    def test_xml(self):
        import recurly
        account = recurly.Account()
        account.username = 'importantbreakfast'
        account_xml = ElementTree.tostring(account.to_element(), encoding='UTF-8')
        self.assertEqual(account_xml, xml('<account><username>importantbreakfast</username></account>'))

    def test_objects_for_push_notification(self):
        import recurly

        objs = recurly.objects_for_push_notification("""<?xml version="1.0" encoding="UTF-8"?>
        <new_subscription_notification>
          <account>
            <account_code>verena@test.com</account_code>
            <username>verena</username>
            <email>verena@test.com</email>
            <first_name>Verena</first_name>
            <last_name>Test</last_name>
            <company_name>Company, Inc.</company_name>
          </account>
          <subscription>
            <plan>
              <plan_code>bronze</plan_code>
              <name>Bronze Plan</name>
              <version type="integer">2</version>
            </plan>
            <state>active</state>
            <quantity type="integer">2</quantity>
            <unit_amount_in_cents type="integer">2000</unit_amount_in_cents>
            <activated_at type="datetime">2009-11-22T13:10:38-08:00</activated_at>
            <canceled_at type="datetime"></canceled_at>
            <expires_at type="datetime"></expires_at>
            <current_period_started_at type="datetime">2009-11-22T13:10:38-08:00</current_period_started_at>
            <current_period_ends_at type="datetime">2009-11-29T13:10:38-08:00</current_period_ends_at>
            <trial_started_at type="datetime">2009-11-22T13:10:38-08:00</trial_started_at>
            <trial_ends_at type="datetime">2009-11-29T13:10:38-08:00</trial_ends_at>
          </subscription>
        </new_subscription_notification>""")
        self.assertEqual(objs['type'], 'new_subscription_notification')
        self.assertTrue('account' in objs)
        self.assertTrue(isinstance(objs['account'], recurly.Account))
        self.assertEqual(objs['account'].username, 'verena')
        self.assertTrue('subscription' in objs)
        self.assertTrue(isinstance(objs['subscription'], recurly.Subscription))
        self.assertEqual(objs['subscription'].state, 'active')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_resources
import collections
import logging
import time
from xml.etree import ElementTree

import six
import recurly

from six import StringIO
from six.moves import urllib, http_client
from six.moves.urllib.parse import urljoin


from recurly import Account, AddOn, Adjustment, BillingInfo, Coupon, Plan, Redemption, Subscription, SubscriptionAddOn, Transaction
from recurly import Money, NotFoundError, ValidationError, BadRequestError, PageError
from recurlytests import RecurlyTest, xml

recurly.SUBDOMAIN = 'api'


class TestResources(RecurlyTest):

    def test_authentication(self):
        recurly.API_KEY = None

        account_code = 'test%s' % self.test_id
        try:
            Account.get(account_code)
        except recurly.UnauthorizedError as exc:
            pass
        else:
            self.fail("Updating account with invalid email address did not raise a ValidationError")

    def test_account(self):
        account_code = 'test%s' % self.test_id
        with self.mock_request('account/does-not-exist.xml'):
            self.assertRaises(NotFoundError, Account.get, account_code)

        account = Account(account_code=account_code)
        account.vat_number = '444444-UK'
        with self.mock_request('account/created.xml'):
            account.save()
        self.assertEqual(account._url, urljoin(recurly.base_uri(), 'accounts/%s' % account_code))
        self.assertEqual(account.vat_number, '444444-UK')

        with self.mock_request('account/list-active.xml'):
            active = Account.all_active()
        self.assertTrue(len(active) >= 1)
        self.assertEqual(active[0].account_code, account_code)

        with self.mock_request('account/exists.xml'):
            same_account = Account.get(account_code)
        self.assertTrue(isinstance(same_account, Account))
        self.assertTrue(same_account is not account)
        self.assertEqual(same_account.account_code, account_code)
        self.assertTrue(same_account.first_name is None)
        self.assertEqual(same_account._url, urljoin(recurly.base_uri(), 'accounts/%s' % account_code))

        account.username = 'shmohawk58'
        account.email = 'larry.david'
        account.first_name = six.u('L\xe4rry')
        account.last_name = 'David'
        account.company_name = 'Home Box Office'
        account.accept_language = 'en-US'
        with self.mock_request('account/update-bad-email.xml'):
            try:
                account.save()
            except ValidationError as exc:
                self.assertTrue(isinstance(exc.errors, collections.Mapping))
                self.assertTrue('account.email' in exc.errors)
                suberror = exc.errors['account.email']
                self.assertEqual(suberror.symbol, 'invalid_email')
                self.assertTrue(suberror.message)
                self.assertEqual(suberror.message, suberror.message)
            else:
                self.fail("Updating account with invalid email address did not raise a ValidationError")

        account.email = 'larry.david@example.com'
        with self.mock_request('account/updated.xml'):
            account.save()

        with self.mock_request('account/deleted.xml'):
            account.delete()

        with self.mock_request('account/list-closed.xml'):
            closed = Account.all_closed()
        self.assertTrue(len(closed) >= 1)
        self.assertEqual(closed[0].account_code, account_code)

        with self.mock_request('account/list-active-when-closed.xml'):
            active = Account.all_active()
        self.assertTrue(len(active) < 1 or active[0].account_code != account_code)

        # Make sure we can reopen a closed account.
        with self.mock_request('account/reopened.xml'):
            account.reopen()
        try:
            with self.mock_request('account/list-active.xml'):
                active = Account.all_active()
            self.assertTrue(len(active) >= 1)
            self.assertEqual(active[0].account_code, account_code)
        finally:
            with self.mock_request('account/deleted.xml'):
                account.delete()

        # Make sure numeric account codes work.
        if self.test_id == 'mock':
            numeric_test_id = 58
        else:
            numeric_test_id = int(self.test_id)

        account = Account(account_code=numeric_test_id)
        with self.mock_request('account/numeric-created.xml'):
            account.save()
        try:
            self.assertEqual(account._url, urljoin(recurly.base_uri(), 'accounts/%d' % numeric_test_id))
        finally:
            with self.mock_request('account/numeric-deleted.xml'):
                account.delete()

        """Create an account with an account level address"""
        account = Account(account_code=account_code)
        account.address.address1 = '123 Main St'
        account.address.city = 'San Francisco'
        account.address.zip = '94105'
        account.address.state = 'CA'
        account.address.country = 'US'
        account.address.phone = '8015559876'
        with self.mock_request('account/created-with-address.xml'):
            account.save()
        self.assertEqual(account.address.address1, '123 Main St')
        self.assertEqual(account.address.city, 'San Francisco')
        self.assertEqual(account.address.zip, '94105')
        self.assertEqual(account.address.state, 'CA')
        self.assertEqual(account.address.country, 'US')
        self.assertEqual(account.address.phone, '8015559876')

        """Get taxed account"""
        with self.mock_request('account/show-taxed.xml'):
            account = Account.get(account_code)
            self.assertTrue(account.tax_exempt)


    def test_add_on(self):
        plan_code = 'plan%s' % self.test_id
        add_on_code = 'addon%s' % self.test_id

        plan = Plan(
            plan_code=plan_code,
            name='Mock Plan',
            setup_fee_in_cents=Money(0),
            unit_amount_in_cents=Money(1000),
        )
        with self.mock_request('add-on/plan-created.xml'):
            plan.save()

        try:

            add_on = AddOn(add_on_code=add_on_code, name='Mock Add-On')
            exc = None
            with self.mock_request('add-on/need-amount.xml'):
                try:
                    plan.create_add_on(add_on)
                except ValidationError as _exc:
                    exc = _exc
                else:
                    self.fail("Creating a plan add-on without an amount did not raise a ValidationError")
            error = exc.errors['add_on.unit_amount_in_cents']
            self.assertEqual(error.symbol, 'blank')

            add_on = AddOn(add_on_code=add_on_code, name='Mock Add-On', unit_amount_in_cents=Money(40))
            with self.mock_request('add-on/created.xml'):
                plan.create_add_on(add_on)
            self.assertEqual(add_on.add_on_code, add_on_code)
            self.assertEqual(add_on.name, 'Mock Add-On')

            try:

                with self.mock_request('add-on/exists.xml'):
                    same_add_on = plan.get_add_on(add_on_code)
                self.assertEqual(same_add_on.add_on_code, add_on_code)
                self.assertEqual(same_add_on.name, 'Mock Add-On')
                self.assertEqual(same_add_on.unit_amount_in_cents['USD'], 40)

            finally:
                with self.mock_request('add-on/deleted.xml'):
                    add_on.delete()
        finally:
            with self.mock_request('add-on/plan-deleted.xml'):
                plan.delete()

    def test_billing_info(self):
        logging.basicConfig(level=logging.DEBUG)  # make sure it's init'ed
        logger = logging.getLogger('recurly.http.request')
        logger.setLevel(logging.DEBUG)

        log_content = StringIO()
        log_handler = logging.StreamHandler(log_content)
        logger.addHandler(log_handler)

        account = Account(account_code='binfo%s' % self.test_id)
        with self.mock_request('billing-info/account-created.xml'):
            account.save()

        logger.removeHandler(log_handler)
        self.assertTrue('<account' in log_content.getvalue())

        try:

            # Billing info link won't be present at all yet.
            self.assertRaises(AttributeError, getattr, account, 'billing_info')

            log_content = StringIO()
            log_handler = logging.StreamHandler(log_content)
            logger.addHandler(log_handler)

            binfo = BillingInfo(
                first_name='Verena',
                last_name='Example',
                address1='123 Main St',
                city=six.u('San Jos\xe9'),
                state='CA',
                zip='94105',
                country='US',
                type='credit_card',
                number='4111 1111 1111 1111',
                verification_value='7777',
                year='2015',
                month='12',
            )
            with self.mock_request('billing-info/created.xml'):
                account.update_billing_info(binfo)

            logger.removeHandler(log_handler)
            log_content = log_content.getvalue()
            self.assertTrue('<billing_info' in log_content)
            # See if we redacted our sensitive fields properly.
            self.assertTrue('4111' not in log_content)
            self.assertTrue('7777' not in log_content)

            with self.mock_request('billing-info/account-exists.xml'):
                same_account = Account.get('binfo%s' % self.test_id)
            with self.mock_request('billing-info/exists.xml'):
                same_binfo = same_account.billing_info
            self.assertEqual(same_binfo.first_name, 'Verena')
            self.assertEqual(same_binfo.city, six.u('San Jos\xe9'))

            with self.mock_request('billing-info/deleted.xml'):
                binfo.delete()
        finally:
            with self.mock_request('billing-info/account-deleted.xml'):
                account.delete()

        # Credit Card
        log_content = StringIO()
        log_handler = logging.StreamHandler(log_content)
        logger.addHandler(log_handler)

        account = Account(account_code='binfo-%s-2' % self.test_id)
        account.billing_info = BillingInfo(
            first_name='Verena',
            last_name='Example',
            address1='123 Main St',
            city=six.u('San Jos\xe9'),
            state='CA',
            zip='94105',
            country='US',
            type='credit_card',
            number='4111 1111 1111 1111',
            verification_value='7777',
            year='2015',
            month='12',
        )
        with self.mock_request('billing-info/account-embed-created.xml'):
            account.save()

        try:
            logger.removeHandler(log_handler)
            log_content = log_content.getvalue()
            self.assertTrue('<account' in log_content)
            self.assertTrue('<billing_info' in log_content)
            self.assertTrue('4111' not in log_content)
            self.assertTrue('7777' not in log_content)

            with self.mock_request('billing-info/account-embed-exists.xml'):
                same_account = Account.get('binfo-%s-2' % self.test_id)
            with self.mock_request('billing-info/embedded-exists.xml'):
                binfo = same_account.billing_info
            self.assertEqual(binfo.first_name, 'Verena')
        finally:
            with self.mock_request('billing-info/account-embed-deleted.xml'):
                account.delete()

        # Token
        log_content = StringIO()
        log_handler = logging.StreamHandler(log_content)
        logger.addHandler(log_handler)

        account = Account(account_code='binfo-%s-3' % self.test_id)
        account.billing_info = BillingInfo(token_id = 'abc123')
        with self.mock_request('billing-info/account-embed-token.xml'):
            account.save()

        logger.removeHandler(log_handler)
        log_content = log_content.getvalue()
        self.assertTrue('<billing_info' in log_content)
        self.assertTrue('<token_id' in log_content)

    def test_charge(self):
        account = Account(account_code='charge%s' % self.test_id)
        with self.mock_request('adjustment/account-created.xml'):
            account.save()

        try:
            with self.mock_request('adjustment/account-has-no-charges.xml'):
                charges = account.adjustments()
            self.assertEqual(charges, [])

            charge = Adjustment(unit_amount_in_cents=1000, currency='USD', description='test charge', type='charge')
            with self.mock_request('adjustment/charged.xml'):
                account.charge(charge)

            with self.mock_request('adjustment/account-has-adjustments.xml'):
                charges = account.adjustments()
            self.assertEqual(len(charges), 1)
            same_charge = charges[0]
            self.assertEqual(same_charge.unit_amount_in_cents, 1000)
            self.assertEqual(same_charge.tax_in_cents, 5000)
            self.assertEqual(same_charge.currency, 'USD')
            self.assertEqual(same_charge.description, 'test charge')
            self.assertEqual(same_charge.type, 'charge')

            tax_details = same_charge.tax_details
            state, county = tax_details

            self.assertEqual(len(tax_details), 2)
            self.assertEqual(state.name, 'california')
            self.assertEqual(state.type, 'state')
            self.assertEqual(state.tax_rate, 0.065)
            self.assertEqual(state.tax_in_cents, 3000)

            self.assertEqual(county.name, 'san francisco')
            self.assertEqual(county.type, 'county')
            self.assertEqual(county.tax_rate, 0.02)
            self.assertEqual(county.tax_in_cents, 2000)

            with self.mock_request('adjustment/account-has-charges.xml'):
                charges = account.adjustments(type='charge')
            self.assertEqual(len(charges), 1)

            with self.mock_request('adjustment/account-has-no-credits.xml'):
                credits = account.adjustments(type='credit')
            self.assertEqual(len(credits), 0)

        finally:
            with self.mock_request('adjustment/account-deleted.xml'):
                account.delete()

        """Test taxed adjustments"""
        with self.mock_request('adjustment/show-taxed.xml'):
            charge = account.adjustments()[0]
            self.assertFalse(charge.tax_exempt)

    def test_coupon(self):
        # Check that a coupon may not exist.
        coupon_code = 'coupon%s' % self.test_id
        with self.mock_request('coupon/does-not-exist.xml'):
            self.assertRaises(NotFoundError, Coupon.get, coupon_code)

        # Create a coupon?
        coupon = Coupon(
            coupon_code=coupon_code,
            name='Nice Coupon',
            discount_in_cents=Money(1000),
            hosted_description="Nice Description"
        )
        with self.mock_request('coupon/created.xml'):
            coupon.save()
        self.assertTrue(coupon._url)

        try:

            with self.mock_request('coupon/exists.xml'):
                same_coupon = Coupon.get(coupon_code)
            self.assertEqual(same_coupon.coupon_code, coupon_code)
            self.assertEqual(same_coupon.name, 'Nice Coupon')
            discount = same_coupon.discount_in_cents
            self.assertEqual(discount['USD'], 1000)
            self.assertTrue('USD' in discount)
            self.assertIsNotNone(same_coupon.hosted_description)

            account_code = 'coupon%s' % self.test_id
            account = Account(account_code=account_code)
            with self.mock_request('coupon/account-created.xml'):
                account.save()

            try:

                redemption = Redemption(
                    account_code=account_code,
                    currency='USD',
                )
                with self.mock_request('coupon/redeemed.xml'):
                    real_redemption = coupon.redeem(redemption)
                self.assertTrue(isinstance(real_redemption, Redemption))
                self.assertEqual(real_redemption.currency, 'USD')

                with self.mock_request('coupon/account-with-redemption.xml'):
                    account = Account.get(account_code)
                with self.mock_request('coupon/redemption-exists.xml'):
                    same_redemption = account.redemption()
                self.assertEqual(same_redemption._url, real_redemption._url)

                with self.mock_request('coupon/unredeemed.xml'):
                    real_redemption.delete()

            finally:
                with self.mock_request('coupon/account-deleted.xml'):
                    account.delete()

            plan = Plan(
                plan_code='basicplan',
                name='Basic Plan',
                setup_fee_in_cents=Money(0),
                unit_amount_in_cents=Money(1000),
            )
            with self.mock_request('coupon/plan-created.xml'):
                plan.save()

            try:

                account_code_2 = 'coupon-%s-2' % self.test_id
                sub = Subscription(
                    plan_code='basicplan',
                    coupon_code='coupon%s' % self.test_id,
                    currency='USD',
                    account=Account(
                        account_code=account_code_2,
                        billing_info=BillingInfo(
                            first_name='Verena',
                            last_name='Example',
                            number='4111 1111 1111 1111',
                            address1='123 Main St',
                            city='San Francisco',
                            state='CA',
                            zip='94105',
                            country='US',
                            verification_value='7777',
                            year='2015',
                            month='12',
                        ),
                    ),
                )
                with self.mock_request('coupon/subscribed.xml'):
                    sub.save()

                with self.mock_request('coupon/second-account-exists.xml'):
                    account_2 = Account.get(account_code_2)

                try:

                    with self.mock_request('coupon/second-account-redemption.xml'):
                        redemption_2 = account_2.redemption()
                    self.assertTrue(isinstance(redemption_2, Redemption))
                    self.assertEqual(redemption_2.currency, 'USD')
                    with self.mock_request('coupon/exists.xml'):
                        same_coupon = redemption_2.coupon()
                    self.assertEqual(same_coupon.coupon_code, coupon_code)

                finally:
                    with self.mock_request('coupon/second-account-deleted.xml'):
                        account_2.delete()

                plan_coupon = Coupon(
                    coupon_code='plancoupon%s' % self.test_id,
                    name='Plan Coupon',
                    discount_in_cents=Money(1000),
                    applies_to_all_plans=False,
                    plan_codes=('basicplan',),
                )
                with self.mock_request('coupon/plan-coupon-created.xml'):
                    plan_coupon.save()

                try:
                    self.assertTrue(plan_coupon._url)

                    coupon_plans = list(plan_coupon.plan_codes)
                    self.assertEqual(len(coupon_plans), 1)
                    self.assertEqual(coupon_plans[0], 'basicplan')
                finally:
                    with self.mock_request('coupon/plan-coupon-deleted.xml'):
                        plan_coupon.delete()

            finally:
                with self.mock_request('coupon/plan-deleted.xml'):
                    plan.delete()

        finally:
            with self.mock_request('coupon/deleted.xml'):
                coupon.delete()

    def test_invoice(self):
        account = Account(account_code='invoice%s' % self.test_id)
        with self.mock_request('invoice/account-created.xml'):
            account.save()

        try:
            with self.mock_request('invoice/account-has-no-invoices.xml'):
                invoices = account.invoices()
            self.assertEqual(invoices, [])

            with self.mock_request('invoice/error-no-charges.xml'):
                try:
                    account.invoice()
                except ValidationError as exc:
                    error = exc
                else:
                    self.fail("Invoicing an account with no charges did not raise a ValidationError")
            self.assertEqual(error.symbol, 'will_not_invoice')

            charge = Adjustment(unit_amount_in_cents=1000, currency='USD', description='test charge', type='charge')
            with self.mock_request('invoice/charged.xml'):
                account.charge(charge)

            with self.mock_request('invoice/invoiced.xml'):
                account.invoice()

            with self.mock_request('invoice/account-has-invoices.xml'):
                invoices = account.invoices()
            self.assertEqual(len(invoices), 1)
        finally:
            with self.mock_request('invoice/account-deleted.xml'):
                account.delete()

        """Test taxed invoice"""
        with self.mock_request('invoice/show-taxed.xml'):
            invoice = account.invoices()[0]
            self.assertEqual(invoice.tax_type, 'usst')

    def test_pages(self):
        account_code = 'pages-%s-%%d' % self.test_id
        all_test_accounts = list()

        try:
            for i in range(1, 8):
                account = Account(account_code=account_code % i)
                all_test_accounts.append(account)
                with self.mock_request('pages/account-%d-created.xml' % i):
                    account.save()
                    self.mock_sleep(1)

            with self.mock_request('pages/list.xml'):
                accounts = Account.all(per_page=4)
            self.assertTrue(isinstance(accounts[0], Account))
            self.assertRaises(IndexError, lambda: accounts[4])

            # Test errors, since the first page has no first page.
            self.assertRaises(PageError, lambda: accounts.first_page())
            # Make sure PageError is a ValueError.
            self.assertRaises(ValueError, lambda: accounts.first_page())

            with self.mock_request('pages/next-list.xml'):
                next_accounts = accounts.next_page()
            # We asked for all the accounts, which may include closed accounts
            # from previous tests or data, not just the three we created.
            self.assertTrue(isinstance(next_accounts[0], Account))
            self.assertRaises(IndexError, lambda: next_accounts[4])

            with self.mock_request('pages/list.xml'):  # should be just like the first
                first_accounts = next_accounts.first_page()
            self.assertTrue(isinstance(first_accounts[0], Account))

        finally:
            for i, account in enumerate(all_test_accounts, 1):
                with self.mock_request('pages/account-%d-deleted.xml' % i):
                    account.delete()

    def test_plan(self):
        plan_code = 'plan%s' % self.test_id
        with self.mock_request('plan/does-not-exist.xml'):
            self.assertRaises(NotFoundError, Plan.get, plan_code)

        plan = Plan(
            plan_code=plan_code,
            name='Mock Plan',
            setup_fee_in_cents=Money(0),
            unit_amount_in_cents=Money(1000),
        )
        with self.mock_request('plan/created.xml'):
            plan.save()

        try:
            self.assertEqual(plan.plan_code, plan_code)

            with self.mock_request('plan/exists.xml'):
                same_plan = Plan.get(plan_code)
            self.assertEqual(same_plan.plan_code, plan_code)
            self.assertEqual(same_plan.name, 'Mock Plan')

            plan.plan_interval_length = 2
            plan.plan_interval_unit = 'months'
            plan.unit_amount_in_cents = Money(USD=2000)
            plan.setup_fee_in_cents = Money(USD=0)
            with self.mock_request('plan/updated.xml'):
                plan.save()
        finally:
            with self.mock_request('plan/deleted.xml'):
                plan.delete()

        """Test taxed plan"""
        with self.mock_request('plan/show-taxed.xml'):
            plan = Plan.get(plan_code)
            self.assertTrue(plan.tax_exempt)

    def test_subscribe(self):
        logging.basicConfig(level=logging.DEBUG)  # make sure it's init'ed
        logger = logging.getLogger('recurly.http.request')
        logger.setLevel(logging.DEBUG)

        plan = Plan(
            plan_code='basicplan',
            name='Basic Plan',
            setup_fee_in_cents=Money(0),
            unit_amount_in_cents=Money(1000),
        )
        with self.mock_request('subscription/plan-created.xml'):
            plan.save()

        try:
            account = Account(account_code='subscribe%s' % self.test_id)
            with self.mock_request('subscription/account-created.xml'):
                account.save()

            try:

                sub = Subscription(
                    plan_code='basicplan',
                    currency='USD',
                    unit_amount_in_cents=1000,
                )

                with self.mock_request('subscription/error-no-billing-info.xml'):
                    try:
                        account.subscribe(sub)
                    except BadRequestError as exc:
                        error = exc
                    else:
                        self.fail("Subscribing with no billing info did not raise a BadRequestError")
                self.assertEqual(error.symbol, 'billing_info_required')

                binfo = BillingInfo(
                    first_name='Verena',
                    last_name='Example',
                    address1='123 Main St',
                    city=six.u('San Jos\xe9'),
                    state='CA',
                    zip='94105',
                    country='US',
                    type='credit_card',
                    number='4111 1111 1111 1111',
                    verification_value='7777',
                    year='2015',
                    month='12',
                )
                with self.mock_request('subscription/update-billing-info.xml'):
                    account.update_billing_info(binfo)

                with self.mock_request('subscription/subscribed.xml'):
                    account.subscribe(sub)
                self.assertTrue(sub._url)

                manualsub = Subscription(
                    plan_code='basicplan',
                    currency='USD',
                    net_terms=10,
                    po_number='1000',
                    collection_method='manual'
                )
                with self.mock_request('subscription/subscribed-manual.xml'):
                    account.subscribe(manualsub)
                self.assertTrue(manualsub._url)
                self.assertEqual(manualsub.net_terms, 10)
                self.assertEqual(manualsub.collection_method, 'manual')
                self.assertEqual(manualsub.po_number, '1000')

                with self.mock_request('subscription/account-subscriptions.xml'):
                    subs = account.subscriptions()
                self.assertTrue(len(subs) > 0)
                self.assertEqual(subs[0].uuid, sub.uuid)

                with self.mock_request('subscription/all-subscriptions.xml'):
                    subs = Subscription.all()
                self.assertTrue(len(subs) > 0)
                self.assertEqual(subs[0].uuid, sub.uuid)

                with self.mock_request('subscription/cancelled.xml'):
                    sub.cancel()
                with self.mock_request('subscription/reactivated.xml'):
                    sub.reactivate()

                # Try modifying the subscription.
                sub.timeframe = 'renewal'
                sub.unit_amount_in_cents = 800
                with self.mock_request('subscription/updated-at-renewal.xml'):
                    sub.save()
                pending_sub = sub.pending_subscription
                self.assertTrue(isinstance(pending_sub, Subscription))
                self.assertEqual(pending_sub.unit_amount_in_cents, 800)
                self.assertEqual(sub.unit_amount_in_cents, 1000)

                with self.mock_request('subscription/terminated.xml'):
                    sub.terminate(refund='none')

                log_content = StringIO()
                log_handler = logging.StreamHandler(log_content)
                logger.addHandler(log_handler)

                sub = Subscription(
                    plan_code='basicplan',
                    currency='USD',
                    account=Account(
                        account_code='subscribe%s' % self.test_id,
                        billing_info=BillingInfo(
                            first_name='Verena',
                            last_name='Example',
                            address1='123 Main St',
                            city=six.u('San Jos\xe9'),
                            state='CA',
                            zip='94105',
                            country='US',
                            type='credit_card',
                            number='4111 1111 1111 1111',
                            verification_value='7777',
                            year='2015',
                            month='12',
                        ),
                    ),
                )
                with self.mock_request('subscription/subscribed-billing-info.xml'):
                    account.subscribe(sub)

                logger.removeHandler(log_handler)
                log_content = log_content.getvalue()
                self.assertTrue('<subscription' in log_content)
                self.assertTrue('<billing_info' in log_content)
                # See if we redacted our sensitive fields properly.
                self.assertTrue('4111' not in log_content)
                self.assertTrue('7777' not in log_content)

            finally:
                with self.mock_request('subscription/account-deleted.xml'):
                    account.delete()

            account_code_2 = 'subscribe-%s-2' % self.test_id
            sub = Subscription(
                plan_code='basicplan',
                currency='USD',
                account=Account(
                    account_code=account_code_2,
                    billing_info=BillingInfo(
                        first_name='Verena',
                        last_name='Example',
                        address1='123 Main St',
                        city=six.u('San Jos\xe9'),
                        state='CA',
                        zip='94105',
                        country='US',
                        type='credit_card',
                        number='4111 1111 1111 1111',
                        verification_value='7777',
                        year='2015',
                        month='12',
                    ),
                ),
            )
            with self.mock_request('subscription/subscribe-embedded-account.xml'):
                sub.save()

            with self.mock_request('subscription/embedded-account-exists.xml'):
                acc = Account.get(account_code_2)
            self.assertEqual(acc.account_code, account_code_2)

            with self.mock_request('subscription/embedded-account-deleted.xml'):
                acc.delete()

        finally:
            with self.mock_request('subscription/plan-deleted.xml'):
                plan.delete()

        """Test taxed subscription"""
        with self.mock_request('subscription/show-taxed.xml'):
            sub = account.subscriptions()[0]
            self.assertEqual(sub.tax_in_cents, 0)
            self.assertEqual(sub.tax_type, 'usst')

    def test_subscribe_add_on(self):
        plan = Plan(
            plan_code='basicplan',
            name='Basic Plan',
            setup_fee_in_cents=Money(0),
            unit_amount_in_cents=Money(1000),
        )
        with self.mock_request('subscribe-add-on/plan-created.xml'):
            plan.save()

        try:

            add_on = AddOn(
                add_on_code='mock_add_on',
                name='Mock Add-On',
                unit_amount_in_cents=Money(100),
            )
            with self.mock_request('subscribe-add-on/add-on-created.xml'):
                plan.create_add_on(add_on)

            second_add_on = AddOn(
                add_on_code='second_add_on',
                name='Second Add-On',
                unit_amount_in_cents=Money(50),
            )
            with self.mock_request('subscribe-add-on/second-add-on-created.xml'):
                plan.create_add_on(second_add_on)

            account_code='sad-on-%s' % self.test_id
            sub = Subscription(
                plan_code='basicplan',
                subscription_add_ons=[
                    SubscriptionAddOn(
                        add_on_code='mock_add_on',
                    ),
                    SubscriptionAddOn(
                        add_on_code='second_add_on',
                    ),
                ],
                currency='USD',
                account=Account(
                    account_code=account_code,
                    billing_info=BillingInfo(
                        first_name='Verena',
                        last_name='Example',
                        number='4111 1111 1111 1111',
                        address1='123 Main St',
                        city='San Francisco',
                        state='CA',
                        zip='94105',
                        country='US',
                        verification_value='7777',
                        year='2015',
                        month='12',
                    ),
                ),
            )
            with self.mock_request('subscribe-add-on/subscribed.xml'):
                sub.save()

            # Subscription amounts are in one real currency, so they aren't Money instances.
            sub_amount = sub.unit_amount_in_cents
            self.assertTrue(not isinstance(sub_amount, Money))
            self.assertEqual(sub_amount, 1000)

            # Test that the add-ons' amounts aren't real Money instances either.
            add_on_1, add_on_2 = sub.subscription_add_ons
            self.assertIsInstance(add_on_1, SubscriptionAddOn)
            amount_1 = add_on_1.unit_amount_in_cents
            self.assertTrue(not isinstance(amount_1, Money))
            self.assertEqual(amount_1, 100)

            with self.mock_request('subscribe-add-on/account-exists.xml'):
                account = Account.get(account_code)
            with self.mock_request('subscribe-add-on/account-deleted.xml'):
                account.delete()

        finally:
            with self.mock_request('subscribe-add-on/plan-deleted.xml'):
                plan.delete()

    def test_account_notes(self):
        account1 = Account(account_code='note%s' % self.test_id)
        account2 = Account(account_code='note%s' % self.test_id)

        with self.mock_request('account-notes/account1-created.xml'):
            account1.save()
        with self.mock_request('account-notes/account2-created.xml'):
            account2.save()
        try:
            with self.mock_request('account-notes/account1-note-list.xml'):
                notes1 = account1.notes()
            with self.mock_request('account-notes/account2-note-list.xml'):
                notes2 = account2.notes()

            # assert accounts don't share notes
            self.assertNotEqual(notes1, notes2)

            # assert contains the proper notes
            self.assertEqual(notes1[0].message, "Python Madness")
            self.assertEqual(notes1[1].message, "Some message")
            self.assertEqual(notes2[0].message, "Foo Bar")
            self.assertEqual(notes2[1].message, "Baz Boo Bop")

        finally:
            with self.mock_request('account-notes/account1-deleted.xml'):
                account1.delete()
            with self.mock_request('account-notes/account2-deleted.xml'):
                account2.delete()

    def test_transaction(self):
        logging.basicConfig(level=logging.DEBUG)  # make sure it's init'ed
        logger = logging.getLogger('recurly.http.request')
        logger.setLevel(logging.DEBUG)

        account_code = 'transaction%s' % self.test_id

        log_content = StringIO()
        log_handler = logging.StreamHandler(log_content)
        logger.addHandler(log_handler)

        transaction = Transaction(
            amount_in_cents=1000,
            currency='USD',
            account=Account(
                account_code=account_code,
                billing_info=BillingInfo(
                    first_name='Verena',
                    last_name='Example',
                    number='4111-1111-1111-1111',
                    year='2014',
                    address1='123 Main St',
                    city='San Francisco',
                    state='CA',
                    zip='94105',
                    country='US',
                    month='7',
                    verification_value='7777',
                ),
            )
        )
        with self.mock_request('transaction/created.xml'):
            transaction.save()

        logger.removeHandler(log_handler)

        try:
            transaction.get_refund_transaction()
        except ValueError:
            pass
        else:
            self.fail("Transaction with no refund transaction did not raise a ValueError from get_refund_transaction()")

        with self.mock_request('transaction/account-exists.xml'):
            account = Account.get(account_code)

        try:
            log_content = log_content.getvalue()
            self.assertTrue('<transaction' in log_content)
            self.assertTrue('<billing_info' in log_content)
            # See if we redacted our sensitive fields properly.
            self.assertTrue('4111' not in log_content)
            self.assertTrue('7777' not in log_content)

            with self.mock_request('transaction/refunded.xml'):
                refunded_transaction = transaction.refund()

            transaction_2 = Transaction(
                amount_in_cents=1000,
                currency='USD',
                account=Account(account_code=account_code),
            )
            with self.mock_request('transaction/created-again.xml'):
                transaction_2.save()
            self.assertNotEqual(transaction_2.uuid, transaction.uuid)
            self.assertTrue(transaction_2.refundable)

            with self.mock_request('transaction/partial-refunded.xml'):
                refunded_transaction = transaction_2.refund(amount_in_cents=700)
            self.assertTrue(refunded_transaction is transaction_2)
            self.assertTrue(hasattr(transaction_2, 'get_refund_transaction'))
            with self.mock_request('transaction/partial-refunded-transaction.xml'):
                refund_transaction = transaction_2.get_refund_transaction()
            self.assertTrue(isinstance(refund_transaction, Transaction))
            self.assertTrue(not refund_transaction.refundable)
            self.assertNotEqual(refund_transaction.uuid, transaction_2.uuid)

        finally:
            with self.mock_request('transaction/account-deleted.xml'):
                account.delete()

    def test_transaction_with_balance(self):
        transaction = Transaction(
            amount_in_cents=1000,
            currency='USD',
            account=Account(),
        )
        error = None
        with self.mock_request('transaction-balance/transaction-no-account.xml'):
            try:
                transaction.save()
            except ValidationError as _error:
                error = _error
            else:
                self.fail("Posting a transaction without an account code did not raise a ValidationError")
        # Make sure there really were errors.
        self.assertTrue(len(error.errors) > 0)

        account_code = 'transbalance%s' % self.test_id
        account = Account(account_code=account_code)
        with self.mock_request('transaction-balance/account-created.xml'):
            account.save()

        try:
            # Try to charge without billing info, should break.
            transaction = Transaction(
                amount_in_cents=1000,
                currency='USD',
                account=account,
            )
            error = None
            with self.mock_request('transaction-balance/transaction-no-billing-fails.xml'):
                try:
                    transaction.save()
                except ValidationError as _error:
                    error = _error
                else:
                    self.fail("Posting a transaction without billing info did not raise a ValidationError")
            # Make sure there really were errors.
            self.assertTrue(len(error.errors) > 0)

            binfo = BillingInfo(
                first_name='Verena',
                last_name='Example',
                address1='123 Main St',
                city=six.u('San Jos\xe9'),
                state='CA',
                zip='94105',
                country='US',
                type='credit_card',
                number='4111 1111 1111 1111',
                verification_value='7777',
                year='2015',
                month='12',
            )
            with self.mock_request('transaction-balance/set-billing-info.xml'):
                account.update_billing_info(binfo)

            # Try to charge now, should be okay.
            transaction = Transaction(
                amount_in_cents=1000,
                currency='USD',
                account=account,
            )
            with self.mock_request('transaction-balance/transacted.xml'):
                transaction.save()

            # Give the account a credit.
            credit = Adjustment(unit_amount_in_cents=-2000, currency='USD', description='transaction test credit')
            with self.mock_request('transaction-balance/credited.xml'):
                # TODO: maybe this should be adjust()?
                account.charge(credit)

            # Try to charge less than the account balance, which should fail (not a CC transaction).
            transaction = Transaction(
                amount_in_cents=500,
                currency='USD',
                account=account,
            )
            with self.mock_request('transaction-balance/transacted-2.xml'):
                transaction.save()
            # The transaction doesn't actually save.
            self.assertTrue(transaction._url is None)

            # Try to charge more than the account balance, which should work.
            transaction = Transaction(
                amount_in_cents=3000,
                currency='USD',
                account=account,
            )
            with self.mock_request('transaction-balance/transacted-3.xml'):
                transaction.save()
            # This transaction should be recorded.
            self.assertTrue(transaction._url is not None)

        finally:
            with self.mock_request('transaction-balance/account-deleted.xml'):
                account.delete()


if __name__ == '__main__':
    import unittest
    unittest.main()

########NEW FILE########
