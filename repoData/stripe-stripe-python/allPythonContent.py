__FILENAME__ = example
import stripe

stripe.api_key = 'tGN0bIwXnHdwOa85VABjPdSn8nWY7G7I'

print "Attempting charge..."

resp = stripe.Charge.create(
    amount=200,
    currency='usd',
    card={
        'number': '4242424242424242',
        'exp_month': 10,
        'exp_year': 2014
    },
    description='customer@gmail.com'
)

print 'Success: %r' % (resp, )

########NEW FILE########
__FILENAME__ = api_requestor
import calendar
import datetime
import platform
import time
import os
import ssl
import socket
import urllib
import urlparse
import warnings

import stripe
from stripe import error, http_client, version, util, certificate_blacklist


def _encode_datetime(dttime):
    if dttime.tzinfo and dttime.tzinfo.utcoffset(dttime) is not None:
        utc_timestamp = calendar.timegm(dttime.utctimetuple())
    else:
        utc_timestamp = time.mktime(dttime.timetuple())

    return int(utc_timestamp)


def _api_encode(data):
    for key, value in data.iteritems():
        key = util.utf8(key)
        if value is None:
            continue
        elif hasattr(value, 'stripe_id'):
            yield (key, value.stripe_id)
        elif isinstance(value, list) or isinstance(value, tuple):
            for subvalue in value:
                yield ("%s[]" % (key,), util.utf8(subvalue))
        elif isinstance(value, dict):
            subdict = dict(('%s[%s]' % (key, subkey), subvalue) for
                           subkey, subvalue in value.iteritems())
            for subkey, subvalue in _api_encode(subdict):
                yield (subkey, subvalue)
        elif isinstance(value, datetime.datetime):
            yield (key, _encode_datetime(value))
        else:
            yield (key, util.utf8(value))


def _build_api_url(url, query):
    scheme, netloc, path, base_query, fragment = urlparse.urlsplit(url)

    if base_query:
        query = '%s&%s' % (base_query, query)

    return urlparse.urlunsplit((scheme, netloc, path, query, fragment))


class APIRequestor(object):

    _CERTIFICATE_VERIFIED = False

    def __init__(self, key=None, client=None):
        self.api_key = key

        from stripe import verify_ssl_certs

        self._client = client or http_client.new_default_http_client(
            verify_ssl_certs=verify_ssl_certs)

    @classmethod
    def api_url(cls, url=''):
        warnings.warn(
            'The `api_url` class method of APIRequestor is '
            'deprecated and will be removed in version 2.0.'
            'If you need public access to this function, please email us '
            'at support@stripe.com.',
            DeprecationWarning)
        return '%s%s' % (stripe.api_base, url)

    @classmethod
    def _deprecated_encode(cls, stk, key, value):
        warnings.warn(
            'The encode_* class methods of APIRequestor are deprecated and '
            'will be removed in version 2.0. '
            'If you need public access to this function, please email us '
            'at support@stripe.com.',
            DeprecationWarning, stacklevel=2)
        stk.extend(_api_encode({key: value}))

    @classmethod
    def encode_dict(cls, stk, key, value):
        cls._deprecated_encode(stk, key, value)

    @classmethod
    def encode_list(cls, stk, key, value):
        cls._deprecated_encode(stk, key, value)

    @classmethod
    def encode_datetime(cls, stk, key, value):
        cls._deprecated_encode(stk, key, value)

    @classmethod
    def encode_none(cls, stk, key, value):
        cls._deprecated_encode(stk, key, value)

    @classmethod
    def encode(cls, d):
        """
        Internal: encode a string for url representation
        """
        warnings.warn(
            'The `encode` class method of APIRequestor is deprecated and '
            'will be removed in version 2.0.'
            'If you need public access to this function, please email us '
            'at support@stripe.com.',
            DeprecationWarning)
        return urllib.urlencode(list(_api_encode(d)))

    @classmethod
    def build_url(cls, url, params):
        warnings.warn(
            'The `build_url` class method of APIRequestor is deprecated and '
            'will be removed in version 2.0.'
            'If you need public access to this function, please email us '
            'at support@stripe.com.',
            DeprecationWarning)
        return _build_api_url(url, cls.encode(params))

    def request(self, method, url, params=None):
        self._check_ssl_cert()
        rbody, rcode, my_api_key = self.request_raw(
            method.lower(), url, params)
        resp = self.interpret_response(rbody, rcode)
        return resp, my_api_key

    def handle_api_error(self, rbody, rcode, resp):
        try:
            err = resp['error']
        except (KeyError, TypeError):
            raise error.APIError(
                "Invalid response object from API: %r (HTTP response code "
                "was %d)" % (rbody, rcode),
                rbody, rcode, resp)

        if rcode in [400, 404]:
            raise error.InvalidRequestError(
                err.get('message'), err.get('param'), rbody, rcode, resp)
        elif rcode == 401:
            raise error.AuthenticationError(
                err.get('message'), rbody, rcode, resp)
        elif rcode == 402:
            raise error.CardError(err.get('message'), err.get('param'),
                                  err.get('code'), rbody, rcode, resp)
        else:
            raise error.APIError(err.get('message'), rbody, rcode, resp)

    def request_raw(self, method, url, params=None):
        """
        Mechanism for issuing an API call
        """
        from stripe import api_version

        if self.api_key:
            my_api_key = self.api_key
        else:
            from stripe import api_key
            my_api_key = api_key

        if my_api_key is None:
            raise error.AuthenticationError(
                'No API key provided. (HINT: set your API key using '
                '"stripe.api_key = <API-KEY>"). You can generate API keys '
                'from the Stripe web interface.  See https://stripe.com/api '
                'for details, or email support@stripe.com if you have any '
                'questions.')

        abs_url = '%s%s' % (stripe.api_base, url)

        encoded_params = urllib.urlencode(list(_api_encode(params or {})))

        if method == 'get' or method == 'delete':
            if params:
                abs_url = _build_api_url(abs_url, encoded_params)
            post_data = None
        elif method == 'post':
            post_data = encoded_params
        else:
            raise error.APIConnectionError(
                'Unrecognized HTTP method %r.  This may indicate a bug in the '
                'Stripe bindings.  Please contact support@stripe.com for '
                'assistance.' % (method,))

        ua = {
            'bindings_version': version.VERSION,
            'lang': 'python',
            'publisher': 'stripe',
            'httplib': self._client.name,
        }
        for attr, func in [['lang_version', platform.python_version],
                           ['platform', platform.platform],
                           ['uname', lambda: ' '.join(platform.uname())]]:
            try:
                val = func()
            except Exception, e:
                val = "!! %s" % (e,)
            ua[attr] = val

        headers = {
            'X-Stripe-Client-User-Agent': util.json.dumps(ua),
            'User-Agent': 'Stripe/v1 PythonBindings/%s' % (version.VERSION,),
            'Authorization': 'Bearer %s' % (my_api_key,)
        }

        if api_version is not None:
            headers['Stripe-Version'] = api_version

        rbody, rcode = self._client.request(
            method, abs_url, headers, post_data)

        util.logger.info(
            'API request to %s returned (response code, response body) of '
            '(%d, %r)',
            abs_url, rcode, rbody)
        return rbody, rcode, my_api_key

    def interpret_response(self, rbody, rcode):
        try:
            if hasattr(rbody, 'decode'):
                rbody = rbody.decode('utf-8')
            resp = util.json.loads(rbody)
        except Exception:
            raise error.APIError(
                "Invalid response body from API: %s "
                "(HTTP response code was %d)" % (rbody, rcode),
                rbody, rcode)
        if not (200 <= rcode < 300):
            self.handle_api_error(rbody, rcode, resp)
        return resp

    def _check_ssl_cert(self):
        """Preflight the SSL certificate presented by the backend.

        This isn't 100% bulletproof, in that we're not actually validating the
        transport used to communicate with Stripe, merely that the first
        attempt to does not use a revoked certificate.

        Unfortunately the interface to OpenSSL doesn't make it easy to check
        the certificate before sending potentially sensitive data on the wire.
        This approach raises the bar for an attacker significantly."""

        from stripe import verify_ssl_certs

        if verify_ssl_certs and not self._CERTIFICATE_VERIFIED:
            uri = urlparse.urlparse(stripe.api_base)
            try:
                certificate = ssl.get_server_certificate(
                    (uri.hostname, uri.port or 443))
                der_cert = ssl.PEM_cert_to_DER_cert(certificate)
            except socket.error, e:
                raise error.APIConnectionError(e)
            except TypeError:
                # The Google App Engine development server blocks the C socket
                # module which causes a type error when using the SSL library
                if ('APPENGINE_RUNTIME' in os.environ and
                        'Dev' in os.environ.get('SERVER_SOFTWARE', '')):
                    self._CERTIFICATE_VERIFIED = True
                    warnings.warn(
                        'We were unable to verify Stripe\'s SSL certificate '
                        'due to a bug in the Google App Engine development '
                        'server. Please alert us immediately at '
                        'support@stripe.com if this message appears in your '
                        'production logs.')
                    return
                else:
                    raise

            self._CERTIFICATE_VERIFIED = certificate_blacklist.verify(
                uri.hostname, der_cert)

    # Deprecated request handling.  Will all be removed in 2.0
    def _deprecated_request(self, impl, method, url, headers, params):
        warnings.warn(
            'The *_request functions of APIRequestor are deprecated and '
            'will be removed in version 2.0. Please use the client classes '
            ' in `stripe.http_client` instead',
            DeprecationWarning, stacklevel=2)

        method = method.lower()

        if method == 'get' or method == 'delete':
            if params:
                url = self.build_url(url, params)
            post_data = None
        elif method == 'post':
            post_data = self.encode(params)
        else:
            raise error.APIConnectionError(
                'Unrecognized HTTP method %r.  This may indicate a bug in the '
                'Stripe bindings.  Please contact support@stripe.com for '
                'assistance.' % (method,))

        client = impl(verify_ssl_certs=self._client._verify_ssl_certs)
        return client.request(method, url, headers, post_data)

    def _deprecated_handle_error(self, impl, *args):
        warnings.warn(
            'The handle_*_error functions of APIRequestor are deprecated and '
            'will be removed in version 2.0. Please use the client classes '
            ' in `stripe.http_client` instead',
            DeprecationWarning, stacklevel=2)

        client = impl(verify_ssl_certs=self._client._verify_ssl_certs)
        return client._handle_request_error(*args)

    def requests_request(self, meth, abs_url, headers, params):
        from stripe.http_client import RequestsClient
        return self._deprecated_request(RequestsClient, meth, abs_url,
                                        headers, params)

    def handle_requests_error(self, err):
        from stripe.http_client import RequestsClient
        return self._deprecated_handle_error(RequestsClient, err)

    def pycurl_request(self, meth, abs_url, headers, params):
        from stripe.http_client import PycurlClient
        return self._deprecated_request(PycurlClient, meth, abs_url,
                                        headers, params)

    def handle_pycurl_error(self, err):
        from stripe.http_client import PycurlClient
        return self._deprecated_handle_error(PycurlClient, err)

    def urlfetch_request(self, meth, abs_url, headers, params):
        from stripe.http_client import UrlFetchClient
        return self._deprecated_request(UrlFetchClient, meth, abs_url,
                                        headers, params)

    def handle_urlfetch_error(self, err, abs_url):
        from stripe.http_client import UrlFetchClient
        return self._deprecated_handle_error(UrlFetchClient, err, abs_url)

    def urllib2_request(self, meth, abs_url, headers, params):
        from stripe.http_client import Urllib2Client
        return self._deprecated_request(Urllib2Client, meth, abs_url,
                                        headers, params)

    def handle_urllib2_error(self, err, abs_url):
        from stripe.http_client import Urllib2Client
        return self._deprecated_handle_error(Urllib2Client, err)

########NEW FILE########
__FILENAME__ = certificate_blacklist
import hashlib
from stripe.error import APIError


BLACKLISTED_DIGESTS = {
    'api.stripe.com': (
        '05c0b3643694470a888c6e7feb5c9e24e823dc53',
    ),
    'revoked.stripe.com': (
        '5b7dc7fbc98d78bf76d4d4fa6f597a0c901fad5c',
    ),
}


def verify(hostname, certificate):
    """Verifies a PEM encoded certficate against a blacklist of known revoked
    fingerprints.

    returns True on success, raises RuntimeError on failure.
    """

    if hostname not in BLACKLISTED_DIGESTS:
        return True

    sha = hashlib.sha1()
    sha.update(certificate)
    fingerprint = sha.hexdigest()

    if fingerprint in BLACKLISTED_DIGESTS[hostname]:
        raise APIError("Invalid server certificate. You tried to "
                       "connect to a server that has a revoked "
                       "SSL certificate, which means we cannot "
                       "securely send data to that server. "
                       "Please email support@stripe.com if you "
                       "need help connecting to the correct API "
                       "server.")
    return True

########NEW FILE########
__FILENAME__ = error
# Exceptions
class StripeError(Exception):

    def __init__(self, message=None, http_body=None, http_status=None,
                 json_body=None):
        super(StripeError, self).__init__(message)

        if http_body and hasattr(http_body, 'decode'):
            try:
                http_body = http_body.decode('utf-8')
            except:
                http_body = ('<Could not decode body as utf-8. '
                             'Please report to support@stripe.com>')

        self.http_body = http_body

        self.http_status = http_status
        self.json_body = json_body


class APIError(StripeError):
    pass


class APIConnectionError(StripeError):
    pass


class CardError(StripeError):

    def __init__(self, message, param, code, http_body=None,
                 http_status=None, json_body=None):
        super(CardError, self).__init__(message,
                                        http_body, http_status, json_body)
        self.param = param
        self.code = code


class InvalidRequestError(StripeError):

    def __init__(self, message, param, http_body=None,
                 http_status=None, json_body=None):
        super(InvalidRequestError, self).__init__(
            message, http_body, http_status, json_body)
        self.param = param


class AuthenticationError(StripeError):
    pass

########NEW FILE########
__FILENAME__ = http_client
import os
import sys
import textwrap
import warnings

from stripe import error, util


# - Requests is the preferred HTTP library
# - Google App Engine has urlfetch
# - Use Pycurl if it's there (at least it verifies SSL certs)
# - Fall back to urllib2 with a warning if needed
try:
    import urllib2
except ImportError:
    pass

try:
    import pycurl
except ImportError:
    pycurl = None

try:
    import requests
except ImportError:
    requests = None
else:
    try:
        # Require version 0.8.8, but don't want to depend on distutils
        version = requests.__version__
        major, minor, patch = [int(i) for i in version.split('.')]
    except Exception:
        # Probably some new-fangled version, so it should support verify
        pass
    else:
        if (major, minor, patch) < (0, 8, 8):
            sys.stderr.write(
                'Warning: the Stripe library requires that your Python '
                '"requests" library be newer than version 0.8.8, but your '
                '"requests" library is version %s. Stripe will fall back to '
                'an alternate HTTP library so everything should work. We '
                'recommend upgrading your "requests" library. If you have any '
                'questions, please contact support@stripe.com. (HINT: running '
                '"pip install -U requests" should upgrade your requests '
                'library to the latest version.)' % (version,))
            requests = None

try:
    from google.appengine.api import urlfetch
except ImportError:
    urlfetch = None


def new_default_http_client(*args, **kwargs):
    if urlfetch:
        impl = UrlFetchClient
    elif requests:
        impl = RequestsClient
    elif pycurl:
        impl = PycurlClient
    else:
        impl = Urllib2Client
        warnings.warn(
            "Warning: the Stripe library is falling back to urllib2/urllib "
            "because neither requests nor pycurl are installed. "
            "urllib2's SSL implementation doesn't verify server "
            "certificates. For improved security, we suggest installing "
            "requests.")

    return impl(*args, **kwargs)


class HTTPClient(object):

    def __init__(self, verify_ssl_certs=True):
        self._verify_ssl_certs = verify_ssl_certs

    def request(self, method, url, headers, post_data=None):
        raise NotImplementedError(
            'HTTPClient subclasses must implement `request`')


class RequestsClient(HTTPClient):
    name = 'requests'

    def request(self, method, url, headers, post_data=None):
        kwargs = {}

        if self._verify_ssl_certs:
            kwargs['verify'] = os.path.join(
                os.path.dirname(__file__), 'data/ca-certificates.crt')
        else:
            kwargs['verify'] = False

        try:
            try:
                result = requests.request(method,
                                          url,
                                          headers=headers,
                                          data=post_data,
                                          timeout=80,
                                          **kwargs)
            except TypeError, e:
                raise TypeError(
                    'Warning: It looks like your installed version of the '
                    '"requests" library is not compatible with Stripe\'s '
                    'usage thereof. (HINT: The most likely cause is that '
                    'your "requests" library is out of date. You can fix '
                    'that by running "pip install -U requests".) The '
                    'underlying error was: %s' % (e,))

            # This causes the content to actually be read, which could cause
            # e.g. a socket timeout. TODO: The other fetch methods probably
            # are succeptible to the same and should be updated.
            content = result.content
            status_code = result.status_code
        except Exception, e:
            # Would catch just requests.exceptions.RequestException, but can
            # also raise ValueError, RuntimeError, etc.
            self._handle_request_error(e)
        return content, status_code

    def _handle_request_error(self, e):
        if isinstance(e, requests.exceptions.RequestException):
            msg = ("Unexpected error communicating with Stripe.  "
                   "If this problem persists, let us know at "
                   "support@stripe.com.")
            err = "%s: %s" % (type(e).__name__, str(e))
        else:
            msg = ("Unexpected error communicating with Stripe. "
                   "It looks like there's probably a configuration "
                   "issue locally.  If this problem persists, let us "
                   "know at support@stripe.com.")
            err = "A %s was raised" % (type(e).__name__,)
            if str(e):
                err += " with error message %s" % (str(e),)
            else:
                err += " with no error message"
        msg = textwrap.fill(msg) + "\n\n(Network error: %s)" % (err,)
        raise error.APIConnectionError(msg)


class UrlFetchClient(HTTPClient):
    name = 'urlfetch'

    def request(self, method, url, headers, post_data=None):
        try:
            result = urlfetch.fetch(
                url=url,
                method=method,
                headers=headers,
                # Google App Engine doesn't let us specify our own cert bundle.
                # However, that's ok because the CA bundle they use recognizes
                # api.stripe.com.
                validate_certificate=self._verify_ssl_certs,
                # GAE requests time out after 60 seconds, so make sure we leave
                # some time for the application to handle a slow Stripe
                deadline=55,
                payload=post_data
            )
        except urlfetch.Error, e:
            self._handle_request_error(e, url)

        return result.content, result.status_code

    def _handle_request_error(self, e, url):
        if isinstance(e, urlfetch.InvalidURLError):
            msg = ("The Stripe library attempted to fetch an "
                   "invalid URL (%r). This is likely due to a bug "
                   "in the Stripe Python bindings. Please let us know "
                   "at support@stripe.com." % (url,))
        elif isinstance(e, urlfetch.DownloadError):
            msg = "There was a problem retrieving data from Stripe."
        elif isinstance(e, urlfetch.ResponseTooLargeError):
            msg = ("There was a problem receiving all of your data from "
                   "Stripe.  This is likely due to a bug in Stripe. "
                   "Please let us know at support@stripe.com.")
        else:
            msg = ("Unexpected error communicating with Stripe. If this "
                   "problem persists, let us know at support@stripe.com.")

        msg = textwrap.fill(msg) + "\n\n(Network error: " + str(e) + ")"
        raise error.APIConnectionError(msg)


class PycurlClient(HTTPClient):
    name = 'pycurl'

    def request(self, method, url, headers, post_data=None):
        s = util.StringIO.StringIO()
        curl = pycurl.Curl()

        if method == 'get':
            curl.setopt(pycurl.HTTPGET, 1)
        elif method == 'post':
            curl.setopt(pycurl.POST, 1)
            curl.setopt(pycurl.POSTFIELDS, post_data)
        else:
            curl.setopt(pycurl.CUSTOMREQUEST, method.upper())

        # pycurl doesn't like unicode URLs
        curl.setopt(pycurl.URL, util.utf8(url))

        curl.setopt(pycurl.WRITEFUNCTION, s.write)
        curl.setopt(pycurl.NOSIGNAL, 1)
        curl.setopt(pycurl.CONNECTTIMEOUT, 30)
        curl.setopt(pycurl.TIMEOUT, 80)
        curl.setopt(pycurl.HTTPHEADER, ['%s: %s' % (k, v)
                    for k, v in headers.iteritems()])
        if self._verify_ssl_certs:
            curl.setopt(pycurl.CAINFO, os.path.join(
                os.path.dirname(__file__), 'data/ca-certificates.crt'))
        else:
            curl.setopt(pycurl.SSL_VERIFYHOST, False)

        try:
            curl.perform()
        except pycurl.error, e:
            self._handle_request_error(e)
        rbody = s.getvalue()
        rcode = curl.getinfo(pycurl.RESPONSE_CODE)
        return rbody, rcode

    def _handle_request_error(self, e):
        if e[0] in [pycurl.E_COULDNT_CONNECT,
                    pycurl.E_COULDNT_RESOLVE_HOST,
                    pycurl.E_OPERATION_TIMEOUTED]:
            msg = ("Could not connect to Stripe.  Please check your "
                   "internet connection and try again.  If this problem "
                   "persists, you should check Stripe's service status at "
                   "https://twitter.com/stripestatus, or let us know at "
                   "support@stripe.com.")
        elif (e[0] in [pycurl.E_SSL_CACERT,
                       pycurl.E_SSL_PEER_CERTIFICATE]):
            msg = ("Could not verify Stripe's SSL certificate.  Please make "
                   "sure that your network is not intercepting certificates.  "
                   "If this problem persists, let us know at "
                   "support@stripe.com.")
        else:
            msg = ("Unexpected error communicating with Stripe. If this "
                   "problem persists, let us know at support@stripe.com.")

        msg = textwrap.fill(msg) + "\n\n(Network error: " + e[1] + ")"
        raise error.APIConnectionError(msg)


class Urllib2Client(HTTPClient):
    if sys.version_info >= (3, 0):
        name = 'urllib.request'
    else:
        name = 'urllib2'

    def request(self, method, url, headers, post_data=None):
        if sys.version_info >= (3, 0) and isinstance(post_data, basestring):
            post_data = post_data.encode('utf-8')

        req = urllib2.Request(url, post_data, headers)

        if method not in ('get', 'post'):
            req.get_method = lambda: method.upper()

        try:
            response = urllib2.urlopen(req)
            rbody = response.read()
            rcode = response.code
        except urllib2.HTTPError, e:
            rcode = e.code
            rbody = e.read()
        except (urllib2.URLError, ValueError), e:
            self._handle_request_error(e)
        return rbody, rcode

    def _handle_request_error(self, e):
        msg = ("Unexpected error communicating with Stripe. "
               "If this problem persists, let us know at support@stripe.com.")
        msg = textwrap.fill(msg) + "\n\n(Network error: " + str(e) + ")"
        raise error.APIConnectionError(msg)

########NEW FILE########
__FILENAME__ = importer
import warnings

warnings.warn("The importers module is deprecated and will be removed in "
              "version 2.0. Check the `util` module for json imports",
              DeprecationWarning)


def import_json():
    warnings.warn(
        "'import_json function is deprecated and will be removed in version "
        "2.0 of the Stripe python bindings.  Please use"
        "`from importer import json` instead'",
        DeprecationWarning)

    from stripe.util import json
    return json

########NEW FILE########
__FILENAME__ = resource
import urllib
import warnings
import sys

from stripe import api_requestor, error, util


def convert_to_stripe_object(resp, api_key):
    types = {'charge': Charge, 'customer': Customer,
             'invoice': Invoice, 'invoiceitem': InvoiceItem,
             'plan': Plan, 'coupon': Coupon, 'token': Token, 'event': Event,
             'transfer': Transfer, 'list': ListObject, 'recipient': Recipient,
             'card': Card, 'application_fee': ApplicationFee,
             'subscription': Subscription}

    if isinstance(resp, list):
        return [convert_to_stripe_object(i, api_key) for i in resp]
    elif isinstance(resp, dict) and not isinstance(resp, StripeObject):
        resp = resp.copy()
        klass_name = resp.get('object')
        if isinstance(klass_name, basestring):
            klass = types.get(klass_name, StripeObject)
        else:
            klass = StripeObject
        return klass.construct_from(resp, api_key)
    else:
        return resp


class StripeObject(dict):
    def __init__(self, id=None, api_key=None, **params):
        super(StripeObject, self).__init__()

        self._unsaved_values = set()
        self._transient_values = set()

        self._retrieve_params = params
        self._previous_metadata = None

        object.__setattr__(self, 'api_key', api_key)

        if id:
            self['id'] = id

    def __setattr__(self, k, v):
        if k[0] == '_' or k in self.__dict__:
            return super(StripeObject, self).__setattr__(k, v)
        else:
            self[k] = v

    def __getattr__(self, k):
        if k[0] == '_':
            raise AttributeError(k)

        try:
            return self[k]
        except KeyError, err:
            raise AttributeError(*err.args)

    def __setitem__(self, k, v):
        if v == "":
            raise ValueError(
                "You cannot set %s to an empty string. "
                "We interpret empty strings as None in requests."
                "You may set %s.%s = None to delete the property" % (
                    k, str(self), k))

        super(StripeObject, self).__setitem__(k, v)

        # Allows for unpickling in Python 3.x
        if not hasattr(self, '_unsaved_values'):
            self._unsaved_values = set()

        self._unsaved_values.add(k)

    def __getitem__(self, k):
        try:
            return super(StripeObject, self).__getitem__(k)
        except KeyError, err:
            if k in self._transient_values:
                raise KeyError(
                    "%r.  HINT: The %r attribute was set in the past."
                    "It was then wiped when refreshing the object with "
                    "the result returned by Stripe's API, probably as a "
                    "result of a save().  The attributes currently "
                    "available on this object are: %s" %
                    (k, k, ', '.join(self.keys())))
            else:
                raise err

    def __delitem__(self, k):
        raise TypeError(
            "You cannot delete attributes on a StripeObject. "
            "To unset a property, set it to None.")

    @classmethod
    def construct_from(cls, values, api_key):
        instance = cls(values.get('id'), api_key)
        instance.refresh_from(values, api_key)
        return instance

    def refresh_from(self, values, api_key=None, partial=False):
        self.api_key = api_key or getattr(values, 'api_key', None)

        # Wipe old state before setting new.  This is useful for e.g.
        # updating a customer, where there is no persistent card
        # parameter.  Mark those values which don't persist as transient
        if partial:
            self._unsaved_values = (self._unsaved_values - set(values))
        else:
            removed = set(self.keys()) - set(values)
            self._transient_values = self._transient_values | removed
            self._unsaved_values = set()

            self.clear()

        self._transient_values = self._transient_values - set(values)

        for k, v in values.iteritems():
            super(StripeObject, self).__setitem__(
                k, convert_to_stripe_object(v, api_key))

        self._previous_metadata = values.get('metadata')

    def request(self, method, url, params=None):
        if params is None:
            params = self._retrieve_params

        requestor = api_requestor.APIRequestor(self.api_key)
        response, api_key = requestor.request(method, url, params)

        return convert_to_stripe_object(response, api_key)

    def __repr__(self):
        ident_parts = [type(self).__name__]

        if isinstance(self.get('object'), basestring):
            ident_parts.append(self.get('object'))

        if isinstance(self.get('id'), basestring):
            ident_parts.append('id=%s' % (self.get('id'),))

        unicode_repr = '<%s at %s> JSON: %s' % (
            ' '.join(ident_parts), hex(id(self)), str(self))

        if sys.version_info[0] < 3:
            return unicode_repr.encode('utf-8')
        else:
            return unicode_repr

    def __str__(self):
        return util.json.dumps(self, sort_keys=True, indent=2)

    def to_dict(self):
        warnings.warn(
            'The `to_dict` method is deprecated and will be removed in '
            'version 2.0 of the Stripe bindings. The StripeObject is '
            'itself now a subclass of `dict`.',
            DeprecationWarning)

        return dict(self)

    @property
    def stripe_id(self):
        return self.id


class StripeObjectEncoder(util.json.JSONEncoder):

    def __init__(self, *args, **kwargs):
        warnings.warn(
            '`StripeObjectEncoder` is deprecated and will be removed in '
            'version 2.0 of the Stripe bindings.  StripeObject is now a '
            'subclass of `dict` and is handled natively by the built-in '
            'json library.',
            DeprecationWarning)
        super(StripeObjectEncoder, self).__init__(*args, **kwargs)


class APIResource(StripeObject):

    @classmethod
    def retrieve(cls, id, api_key=None, **params):
        instance = cls(id, api_key, **params)
        instance.refresh()
        return instance

    def refresh(self):
        self.refresh_from(self.request('get', self.instance_url()))
        return self

    @classmethod
    def class_name(cls):
        if cls == APIResource:
            raise NotImplementedError(
                'APIResource is an abstract class.  You should perform '
                'actions on its subclasses (e.g. Charge, Customer)')
        return str(urllib.quote_plus(cls.__name__.lower()))

    @classmethod
    def class_url(cls):
        cls_name = cls.class_name()
        return "/v1/%ss" % (cls_name,)

    def instance_url(self):
        id = self.get('id')
        if not id:
            raise error.InvalidRequestError(
                'Could not determine which URL to request: %s instance '
                'has invalid ID: %r' % (type(self).__name__, id), 'id')
        id = util.utf8(id)
        base = self.class_url()
        extn = urllib.quote_plus(id)
        return "%s/%s" % (base, extn)


class ListObject(StripeObject):

    def all(self, **params):
        return self.request('get', self['url'], params)

    def create(self, **params):
        return self.request('post', self['url'], params)

    def retrieve(self, id, **params):
        base = self.get('url')
        id = util.utf8(id)
        extn = urllib.quote_plus(id)
        url = "%s/%s" % (base, extn)

        return self.request('get', url, params)


class SingletonAPIResource(APIResource):

    @classmethod
    def retrieve(cls, api_key=None):
        return super(SingletonAPIResource, cls).retrieve(None,
                                                         api_key=api_key)

    @classmethod
    def class_url(cls):
        cls_name = cls.class_name()
        return "/v1/%s" % (cls_name,)

    def instance_url(self):
        return self.class_url()


# Classes of API operations


class ListableAPIResource(APIResource):

    @classmethod
    def all(cls, api_key=None, **params):
        requestor = api_requestor.APIRequestor(api_key)
        url = cls.class_url()
        response, api_key = requestor.request('get', url, params)
        return convert_to_stripe_object(response, api_key)


class CreateableAPIResource(APIResource):

    @classmethod
    def create(cls, api_key=None, **params):
        requestor = api_requestor.APIRequestor(api_key)
        url = cls.class_url()
        response, api_key = requestor.request('post', url, params)
        return convert_to_stripe_object(response, api_key)


class UpdateableAPIResource(APIResource):

    def save(self):
        updated_params = self.serialize(self)

        if getattr(self, 'metadata', None):
            updated_params['metadata'] = self.serialize_metadata()

        if updated_params:
            self.refresh_from(self.request('post', self.instance_url(),
                                           updated_params))
        else:
            util.logger.debug("Trying to save already saved object %r", self)
        return self

    def serialize_metadata(self):
        if 'metadata' in self._unsaved_values:
            # the metadata object has been reassigned
            # i.e. as object.metadata = {key: val}
            metadata_update = self.metadata
            keys_to_unset = set(self._previous_metadata.keys()) - \
                set(self.metadata.keys())
            for key in keys_to_unset:
                metadata_update[key] = ""

            return metadata_update
        else:
            return self.serialize(self.metadata)

    def serialize(self, obj):
        params = {}
        if obj._unsaved_values:
            for k in obj._unsaved_values:
                if k == 'id' or k == '_previous_metadata':
                    continue
                v = getattr(obj, k)
                params[k] = v if v is not None else ""
        return params


class DeletableAPIResource(APIResource):

    def delete(self, **params):
        self.refresh_from(self.request('delete', self.instance_url(), params))
        return self

# API objects


class Account(SingletonAPIResource):
    pass


class Balance(SingletonAPIResource):
    pass


class BalanceTransaction(ListableAPIResource):

    @classmethod
    def class_url(cls):
        return '/v1/balance/history'


class Card(UpdateableAPIResource, DeletableAPIResource):

    def instance_url(self):
        self.id = util.utf8(self.id)
        extn = urllib.quote_plus(self.id)
        if (hasattr(self, 'customer')):
            self.customer = util.utf8(self.customer)

            base = Customer.class_url()
            owner_extn = urllib.quote_plus(self.customer)

        elif (hasattr(self, 'recipient')):
            self.recipient = util.utf8(self.recipient)

            base = Recipient.class_url()
            owner_extn = urllib.quote_plus(self.recipient)

        else:
            raise error.InvalidRequestError(
                "Could not determine whether card_id %s is "
                "attached to a customer "
                "or a recipient." % self.id)

        return "%s/%s/cards/%s" % (base, owner_extn, extn)

    @classmethod
    def retrieve(cls, id, api_key=None, **params):
        raise NotImplementedError(
            "Can't retrieve a card without a customer or recipient"
            "ID. Use customer.cards.retrieve('card_id') or "
            "recipient.cards.retrieve('card_id') instead.")


class Charge(CreateableAPIResource, ListableAPIResource,
             UpdateableAPIResource):

    def refund(self, **params):
        url = self.instance_url() + '/refund'
        self.refresh_from(self.request('post', url, params))
        return self

    def capture(self, **params):
        url = self.instance_url() + '/capture'
        self.refresh_from(self.request('post', url, params))
        return self

    def update_dispute(self, **params):
        requestor = api_requestor.APIRequestor(self.api_key)
        url = self.instance_url() + '/dispute'
        response, api_key = requestor.request('post', url, params)
        self.refresh_from({'dispute': response}, api_key, True)
        return self.dispute

    def close_dispute(self):
        requestor = api_requestor.APIRequestor(self.api_key)
        url = self.instance_url() + '/dispute/close'
        response, api_key = requestor.request('post', url, {})
        self.refresh_from({'dispute': response}, api_key, True)
        return self.dispute


class Customer(CreateableAPIResource, UpdateableAPIResource,
               ListableAPIResource, DeletableAPIResource):

    def add_invoice_item(self, **params):
        params['customer'] = self.id
        ii = InvoiceItem.create(self.api_key, **params)
        return ii

    def invoices(self, **params):
        params['customer'] = self.id
        invoices = Invoice.all(self.api_key, **params)
        return invoices

    def invoice_items(self, **params):
        params['customer'] = self.id
        iis = InvoiceItem.all(self.api_key, **params)
        return iis

    def charges(self, **params):
        params['customer'] = self.id
        charges = Charge.all(self.api_key, **params)
        return charges

    def update_subscription(self, **params):
        requestor = api_requestor.APIRequestor(self.api_key)
        url = self.instance_url() + '/subscription'
        response, api_key = requestor.request('post', url, params)
        self.refresh_from({'subscription': response}, api_key, True)
        return self.subscription

    def cancel_subscription(self, **params):
        requestor = api_requestor.APIRequestor(self.api_key)
        url = self.instance_url() + '/subscription'
        response, api_key = requestor.request('delete', url, params)
        self.refresh_from({'subscription': response}, api_key, True)
        return self.subscription

    def delete_discount(self, **params):
        requestor = api_requestor.APIRequestor(self.api_key)
        url = self.instance_url() + '/discount'
        _, api_key = requestor.request('delete', url)
        self.refresh_from({'discount': None}, api_key, True)


class Invoice(CreateableAPIResource, ListableAPIResource,
              UpdateableAPIResource):

    def pay(self):
        return self.request('post', self.instance_url() + '/pay', {})

    @classmethod
    def upcoming(cls, api_key=None, **params):
        requestor = api_requestor.APIRequestor(api_key)
        url = cls.class_url() + '/upcoming'
        response, api_key = requestor.request('get', url, params)
        return convert_to_stripe_object(response, api_key)


class InvoiceItem(CreateableAPIResource, UpdateableAPIResource,
                  ListableAPIResource, DeletableAPIResource):
    pass


class Plan(CreateableAPIResource, DeletableAPIResource,
           UpdateableAPIResource, ListableAPIResource):
    pass


class Subscription(UpdateableAPIResource, DeletableAPIResource):

    def instance_url(self):
        self.id = util.utf8(self.id)
        self.customer = util.utf8(self.customer)

        base = Customer.class_url()
        cust_extn = urllib.quote_plus(self.customer)
        extn = urllib.quote_plus(self.id)

        return "%s/%s/subscriptions/%s" % (base, cust_extn, extn)

    @classmethod
    def retrieve(cls, id, api_key=None, **params):
        raise NotImplementedError(
            "Can't retrieve a subscription without a customer ID. "
            "Use customer.subscriptions.retrieve('subscription_id') instead.")

    def delete_discount(self, **params):
        requestor = api_requestor.APIRequestor(self.api_key)
        url = self.instance_url() + '/discount'
        _, api_key = requestor.request('delete', url)
        self.refresh_from({'discount': None}, api_key, True)


class Token(CreateableAPIResource):
    pass


class Coupon(CreateableAPIResource, DeletableAPIResource,
             ListableAPIResource):
    pass


class Event(ListableAPIResource):
    pass


class Transfer(CreateableAPIResource, UpdateableAPIResource,
               ListableAPIResource):

    def cancel(self):
        self.refresh_from(self.request('post',
                          self.instance_url() + '/cancel'))


class Recipient(CreateableAPIResource, UpdateableAPIResource,
                ListableAPIResource, DeletableAPIResource):

    def transfers(self, **params):
        params['recipient'] = self.id
        transfers = Transfer.all(self.api_key, **params)
        return transfers


class ApplicationFee(ListableAPIResource):
    @classmethod
    def class_name(cls):
        return 'application_fee'

    def refund(self, **params):
        url = self.instance_url() + '/refund'
        self.refresh_from(self.request('post', url, params))
        return self

########NEW FILE########
__FILENAME__ = helper
import datetime
import os
import random
import re
import string
import sys
import unittest

from mock import patch, Mock

import stripe

NOW = datetime.datetime.now()

DUMMY_CARD = {
    'number': '4242424242424242',
    'exp_month': NOW.month,
    'exp_year': NOW.year + 4
}
DUMMY_DEBIT_CARD = {
    'number': '4000056655665556',
    'exp_month': NOW.month,
    'exp_year': NOW.year + 4
}
DUMMY_CHARGE = {
    'amount': 100,
    'currency': 'usd',
    'card': DUMMY_CARD
}

DUMMY_PLAN = {
    'amount': 2000,
    'interval': 'month',
    'name': 'Amazing Gold Plan',
    'currency': 'usd',
    'id': ('stripe-test-gold-' +
           ''.join(random.choice(string.ascii_lowercase) for x in range(10)))
}

DUMMY_COUPON = {
    'percent_off': 25,
    'duration': 'repeating',
    'duration_in_months': 5
}

DUMMY_RECIPIENT = {
    'name': 'John Doe',
    'type': 'individual'
}

DUMMY_TRANSFER = {
    'amount': 400,
    'currency': 'usd',
    'recipient': 'self'
}

DUMMY_INVOICE_ITEM = {
    'amount': 456,
    'currency': 'usd',
}

SAMPLE_INVOICE = stripe.util.json.loads("""
{
  "amount_due": 1305,
  "attempt_count": 0,
  "attempted": true,
  "charge": "ch_wajkQ5aDTzFs5v",
  "closed": true,
  "customer": "cus_osllUe2f1BzrRT",
  "date": 1338238728,
  "discount": null,
  "ending_balance": 0,
  "id": "in_t9mHb2hpK7mml1",
  "livemode": false,
  "next_payment_attempt": null,
  "object": "invoice",
  "paid": true,
  "period_end": 1338238728,
  "period_start": 1338238716,
  "starting_balance": -8695,
  "subtotal": 10000,
  "total": 10000,
  "lines": {
    "invoiceitems": [],
    "prorations": [],
    "subscriptions": [
      {
        "plan": {
          "interval": "month",
          "object": "plan",
          "identifier": "expensive",
          "currency": "usd",
          "livemode": false,
          "amount": 10000,
          "name": "Expensive Plan",
          "trial_period_days": null,
          "id": "expensive"
        },
        "period": {
          "end": 1340917128,
          "start": 1338238728
        },
        "amount": 10000
      }
    ]
  }
}
""")


class StripeTestCase(unittest.TestCase):
    RESTORE_ATTRIBUTES = ('api_version', 'api_key')

    def setUp(self):
        super(StripeTestCase, self).setUp()

        self._stripe_original_attributes = {}

        for attr in self.RESTORE_ATTRIBUTES:
            self._stripe_original_attributes[attr] = getattr(stripe, attr)

        api_base = os.environ.get('STRIPE_API_BASE')
        if api_base:
            stripe.api_base = api_base
        stripe.api_key = os.environ.get(
            'STRIPE_API_KEY', 'tGN0bIwXnHdwOa85VABjPdSn8nWY7G7I')

    def tearDown(self):
        super(StripeTestCase, self).tearDown()

        for attr in self.RESTORE_ATTRIBUTES:
            setattr(stripe, attr, self._stripe_original_attributes[attr])

    # Python < 2.7 compatibility
    def assertRaisesRegexp(self, exception, regexp, callable, *args, **kwargs):
        try:
            callable(*args, **kwargs)
        except exception, err:
            if regexp is None:
                return True

            if isinstance(regexp, basestring):
                regexp = re.compile(regexp)
            if not regexp.search(str(err)):
                raise self.failureException('"%s" does not match "%s"' %
                                            (regexp.pattern, str(err)))
        else:
            raise self.failureException(
                '%s was not raised' % (exception.__name__,))


class StripeUnitTestCase(StripeTestCase):
    REQUEST_LIBRARIES = ['urlfetch', 'requests', 'pycurl']

    if sys.version_info >= (3, 0):
        REQUEST_LIBRARIES.append('urllib.request')
    else:
        REQUEST_LIBRARIES.append('urllib2')

    def setUp(self):
        super(StripeUnitTestCase, self).setUp()

        self.request_patchers = {}
        self.request_mocks = {}
        for lib in self.REQUEST_LIBRARIES:
            patcher = patch("stripe.http_client.%s" % (lib,))

            self.request_mocks[lib] = patcher.start()
            self.request_patchers[lib] = patcher

    def tearDown(self):
        super(StripeUnitTestCase, self).tearDown()

        for patcher in self.request_patchers.itervalues():
            patcher.stop()


class StripeApiTestCase(StripeTestCase):

    def setUp(self):
        super(StripeApiTestCase, self).setUp()

        self.requestor_patcher = patch('stripe.api_requestor.APIRequestor')
        requestor_class_mock = self.requestor_patcher.start()
        self.requestor_mock = requestor_class_mock.return_value

    def tearDown(self):
        super(StripeApiTestCase, self).tearDown()

        self.requestor_patcher.stop()

    def mock_response(self, res):
        self.requestor_mock.request = Mock(return_value=(res, 'reskey'))


class MyResource(stripe.resource.APIResource):
    pass


class MySingleton(stripe.resource.SingletonAPIResource):
    pass


class MyListable(stripe.resource.ListableAPIResource):
    pass


class MyCreatable(stripe.resource.CreateableAPIResource):
    pass


class MyUpdateable(stripe.resource.UpdateableAPIResource):
    pass


class MyDeletable(stripe.resource.DeletableAPIResource):
    pass


class MyComposite(stripe.resource.ListableAPIResource,
                  stripe.resource.CreateableAPIResource,
                  stripe.resource.UpdateableAPIResource,
                  stripe.resource.DeletableAPIResource):
    pass

########NEW FILE########
__FILENAME__ = test_blacklist
import ssl

import stripe
from stripe import certificate_blacklist
from stripe.api_requestor import APIRequestor
from stripe.error import APIError
from stripe.test.helper import StripeTestCase


class RequestorBlacklistTest(StripeTestCase):

    def test_revoked_cert_is_revoked(self):
        stripe.api_base = "https://revoked.stripe.com:444"
        requestor = APIRequestor()
        self.assertRaises(APIError, requestor._check_ssl_cert)

    def test_live_cert_is_not_revoked(self):
        stripe.api_base = "https://api.stripe.com"
        requestor = APIRequestor()
        requestor._check_ssl_cert()
        self.assertTrue(requestor._CERTIFICATE_VERIFIED)

    def tearDown(self):
        stripe.api_base = "https://api.stripe.com"


class BlacklistTest(StripeTestCase):

    def test_revoked_cert_is_revoked(self):
        hostname = "revoked.stripe.com"
        cert = ssl.get_server_certificate((hostname, 444))
        der_cert = ssl.PEM_cert_to_DER_cert(cert)
        self.assertRaises(APIError,
                          lambda: certificate_blacklist.verify(
                              hostname, der_cert))

    def test_live_cert_is_not_revoked(self):
        hostname = "api.stripe.com"
        cert = ssl.get_server_certificate((hostname, 443))
        der_cert = ssl.PEM_cert_to_DER_cert(cert)
        self.assertTrue(certificate_blacklist.verify(hostname, der_cert))

########NEW FILE########
__FILENAME__ = test_http_client
import sys
import unittest

from mock import Mock, patch

import stripe

from stripe.test.helper import StripeUnitTestCase

VALID_API_METHODS = ('get', 'post', 'delete')


class HttpClientTests(StripeUnitTestCase):

    def setUp(self):
        super(HttpClientTests, self).setUp()

        self.original_filters = stripe.http_client.warnings.filters[:]
        stripe.http_client.warnings.simplefilter('ignore')

    def tearDown(self):
        stripe.http_client.warnings.filters = self.original_filters

        super(HttpClientTests, self).tearDown()

    def check_default(self, none_libs, expected):
        for lib in none_libs:
            setattr(stripe.http_client, lib, None)

        inst = stripe.http_client.new_default_http_client()

        self.assertTrue(isinstance(inst, expected))

    def test_new_default_http_client_urlfetch(self):
        self.check_default((),
                           stripe.http_client.UrlFetchClient)

    def test_new_default_http_client_requests(self):
        self.check_default(('urlfetch',),
                           stripe.http_client.RequestsClient)

    def test_new_default_http_client_pycurl(self):
        self.check_default(('urlfetch', 'requests',),
                           stripe.http_client.PycurlClient)

    def test_new_default_http_client_urllib2(self):
        self.check_default(('urlfetch', 'requests', 'pycurl'),
                           stripe.http_client.Urllib2Client)


class ClientTestBase():

    @property
    def request_mock(self):
        return self.request_mocks[self.request_client.name]

    @property
    def valid_url(self, path='/foo'):
        return 'https://api.stripe.com%s' % (path,)

    def make_request(self, method, url, headers, post_data):
        client = self.request_client(verify_ssl_certs=True)
        return client.request(method, url, headers, post_data)

    def mock_response(self, body, code):
        raise NotImplementedError(
            'You must implement this in your test subclass')

    def mock_error(self, error):
        raise NotImplementedError(
            'You must implement this in your test subclass')

    def check_call(self, meth, abs_url, headers, params):
        raise NotImplementedError(
            'You must implement this in your test subclass')

    def test_request(self):
        self.mock_response(self.request_mock, '{"foo": "baz"}', 200)

        for meth in VALID_API_METHODS:
            abs_url = self.valid_url
            data = ''

            if meth != 'post':
                abs_url = '%s?%s' % (abs_url, data)
                data = None

            headers = {'my-header': 'header val'}

            body, code = self.make_request(
                meth, abs_url, headers, data)

            self.assertEqual(200, code)
            self.assertEqual('{"foo": "baz"}', body)

            self.check_call(self.request_mock, meth, abs_url,
                            data, headers)

    def test_exception(self):
        self.mock_error(self.request_mock)
        self.assertRaises(stripe.error.APIConnectionError,
                          self.make_request,
                          'get', self.valid_url, {}, None)


class RequestsVerify(object):

    def __eq__(self, other):
        return other and other.endswith('stripe/data/ca-certificates.crt')


class RequestsClientTests(StripeUnitTestCase, ClientTestBase):
    request_client = stripe.http_client.RequestsClient

    def mock_response(self, mock, body, code):
        result = Mock()
        result.content = body
        result.status_code = code

        mock.request = Mock(return_value=result)

    def mock_error(self, mock):
        mock.exceptions.RequestException = Exception
        mock.request.side_effect = mock.exceptions.RequestException()

    def check_call(self, mock, meth, url, post_data, headers):
        mock.request.assert_called_with(meth, url,
                                        headers=headers,
                                        data=post_data,
                                        verify=RequestsVerify(),
                                        timeout=80)


class UrlFetchClientTests(StripeUnitTestCase, ClientTestBase):
    request_client = stripe.http_client.UrlFetchClient

    def mock_response(self, mock, body, code):
        result = Mock()
        result.content = body
        result.status_code = code

        mock.fetch = Mock(return_value=result)

    def mock_error(self, mock):
        mock.Error = mock.InvalidURLError = Exception
        mock.fetch.side_effect = mock.InvalidURLError()

    def check_call(self, mock, meth, url, post_data, headers):
        mock.fetch.assert_called_with(
            url=url,
            method=meth,
            headers=headers,
            validate_certificate=True,
            deadline=55,
            payload=post_data
        )


class Urllib2ClientTests(StripeUnitTestCase, ClientTestBase):
    request_client = stripe.http_client.Urllib2Client

    def mock_response(self, mock, body, code):
        response = Mock
        response.read = Mock(return_value=body)
        response.code = code

        self.request_object = Mock()
        mock.Request = Mock(return_value=self.request_object)

        mock.urlopen = Mock(return_value=response)

    def mock_error(self, mock):
        mock.urlopen.side_effect = ValueError

    def check_call(self, mock, meth, url, post_data, headers):
        if sys.version_info >= (3, 0) and isinstance(post_data, basestring):
            post_data = post_data.encode('utf-8')

        mock.Request.assert_called_with(url, post_data, headers)
        mock.urlopen.assert_called_with(self.request_object)


class PycurlClientTests(StripeUnitTestCase, ClientTestBase):
    request_client = stripe.http_client.PycurlClient

    @property
    def request_mock(self):
        if not hasattr(self, 'curl_mock'):
            lib_mock = self.request_mocks[self.request_client.name]

            self.curl_mock = Mock()

            lib_mock.Curl = Mock(return_value=self.curl_mock)

        return self.curl_mock

    def setUp(self):
        super(PycurlClientTests, self).setUp()

        self.sio_patcher = patch('stripe.util.StringIO.StringIO')

        sio_mock = Mock()
        self.sio_patcher.start().return_value = sio_mock
        self.sio_getvalue = sio_mock.getvalue

    def tearDown(self):
        super(PycurlClientTests, self).tearDown()

        self.sio_patcher.stop()

    def mock_response(self, mock, body, code):
        self.sio_getvalue.return_value = body

        mock.getinfo.return_value = code

    def mock_error(self, mock):
        class FakeException(BaseException):

            def __getitem__(self, i):
                return 'foo'

        stripe.http_client.pycurl.error = FakeException
        mock.perform.side_effect = stripe.http_client.pycurl.error

    def check_call(self, mock, meth, url, post_data, headers):
        # TODO: Check the setopt calls
        pass

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_integration
# -*- coding: utf-8 -*-
import datetime
import os
import sys
import time
import unittest

from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import stripe

from stripe.test.helper import (
    StripeTestCase,
    NOW, DUMMY_CARD, DUMMY_DEBIT_CARD, DUMMY_CHARGE, DUMMY_PLAN, DUMMY_COUPON,
    DUMMY_RECIPIENT, DUMMY_TRANSFER, DUMMY_INVOICE_ITEM)


class FunctionalTests(StripeTestCase):
    request_client = stripe.http_client.Urllib2Client

    def setUp(self):
        super(FunctionalTests, self).setUp()

        def get_http_client(*args, **kwargs):
            return self.request_client(*args, **kwargs)

        self.client_patcher = patch(
            'stripe.http_client.new_default_http_client')

        client_mock = self.client_patcher.start()
        client_mock.side_effect = get_http_client

    def tearDown(self):
        super(FunctionalTests, self).tearDown()

        self.client_patcher.stop()

    def test_dns_failure(self):
        api_base = stripe.api_base
        try:
            stripe.api_base = 'https://my-invalid-domain.ireallywontresolve/v1'
            self.assertRaises(stripe.error.APIConnectionError,
                              stripe.Customer.create)
        finally:
            stripe.api_base = api_base

    def test_run(self):
        charge = stripe.Charge.create(**DUMMY_CHARGE)
        self.assertFalse(charge.refunded)
        charge.refund()
        self.assertTrue(charge.refunded)

    def test_refresh(self):
        charge = stripe.Charge.create(**DUMMY_CHARGE)
        charge2 = stripe.Charge.retrieve(charge.id)
        self.assertEqual(charge2.created, charge.created)

        charge2.junk = 'junk'
        charge2.refresh()
        self.assertRaises(AttributeError, lambda: charge2.junk)

    def test_list_accessors(self):
        customer = stripe.Customer.create(card=DUMMY_CARD)
        self.assertEqual(customer['created'], customer.created)
        customer['foo'] = 'bar'
        self.assertEqual(customer.foo, 'bar')

    def test_raise(self):
        EXPIRED_CARD = DUMMY_CARD.copy()
        EXPIRED_CARD['exp_month'] = NOW.month - 2
        EXPIRED_CARD['exp_year'] = NOW.year - 2
        self.assertRaises(stripe.error.CardError, stripe.Charge.create,
                          amount=100, currency='usd', card=EXPIRED_CARD)

    def test_unicode(self):
        # Make sure unicode requests can be sent
        self.assertRaises(stripe.error.InvalidRequestError,
                          stripe.Charge.retrieve,
                          id=u'☃')

    def test_none_values(self):
        customer = stripe.Customer.create(plan=None)
        self.assertTrue(customer.id)

    def test_missing_id(self):
        customer = stripe.Customer()
        self.assertRaises(stripe.error.InvalidRequestError, customer.refresh)


class RequestsFunctionalTests(FunctionalTests):
    request_client = stripe.http_client.RequestsClient

# Avoid skipTest errors in < 2.7
if sys.version_info >= (2, 7):
    class UrlfetchFunctionalTests(FunctionalTests):
        request_client = 'urlfetch'

        def setUp(self):
            if stripe.http_client.urlfetch is None:
                self.skipTest(
                    '`urlfetch` from Google App Engine is unavailable.')
            else:
                super(UrlfetchFunctionalTests, self).setUp()

if not os.environ.get('SKIP_PYCURL_TESTS'):
    class PycurlFunctionalTests(FunctionalTests):
        def setUp(self):
            if sys.version_info >= (3, 0):
                self.skipTest('Pycurl is not supported in Python 3')
            else:
                super(PycurlFunctionalTests, self).setUp()

        request_client = stripe.http_client.PycurlClient


class AuthenticationErrorTest(StripeTestCase):

    def test_invalid_credentials(self):
        key = stripe.api_key
        try:
            stripe.api_key = 'invalid'
            stripe.Customer.create()
        except stripe.error.AuthenticationError, e:
            self.assertEqual(401, e.http_status)
            self.assertTrue(isinstance(e.http_body, basestring))
            self.assertTrue(isinstance(e.json_body, dict))
        finally:
            stripe.api_key = key


class CardErrorTest(StripeTestCase):

    def test_declined_card_props(self):
        EXPIRED_CARD = DUMMY_CARD.copy()
        EXPIRED_CARD['exp_month'] = NOW.month - 2
        EXPIRED_CARD['exp_year'] = NOW.year - 2
        try:
            stripe.Charge.create(amount=100, currency='usd', card=EXPIRED_CARD)
        except stripe.error.CardError, e:
            self.assertEqual(402, e.http_status)
            self.assertTrue(isinstance(e.http_body, basestring))
            self.assertTrue(isinstance(e.json_body, dict))

# Note that these are in addition to the core functional charge tests


class ChargeTest(StripeTestCase):

    def setUp(self):
        super(ChargeTest, self).setUp()

    def test_charge_list_all(self):
        charge_list = stripe.Charge.all(created={'lt': NOW})
        list_result = charge_list.all(created={'lt': NOW})

        self.assertEqual(len(charge_list.data),
                         len(list_result.data))

        for expected, actual in zip(charge_list.data,
                                    list_result.data):
            self.assertEqual(expected.id, actual.id)

    def test_charge_list_create(self):
        charge_list = stripe.Charge.all()

        charge = charge_list.create(**DUMMY_CHARGE)

        self.assertTrue(isinstance(charge, stripe.Charge))
        self.assertEqual(DUMMY_CHARGE['amount'], charge.amount)

    def test_charge_list_retrieve(self):
        charge_list = stripe.Charge.all()

        charge = charge_list.retrieve(charge_list.data[0].id)

        self.assertTrue(isinstance(charge, stripe.Charge))

    def test_charge_capture(self):
        params = DUMMY_CHARGE.copy()
        params['capture'] = False

        charge = stripe.Charge.create(**params)

        self.assertFalse(charge.captured)

        self.assertTrue(charge is charge.capture())
        self.assertTrue(stripe.Charge.retrieve(charge.id).captured)

    def test_charge_dispute(self):
        # We don't have a good way of simulating disputes
        # This is a pretty lame test but it at least checks that the
        # dispute code fails in the way we predict, not from e.g.
        # a syntax error

        charge = stripe.Charge.create(**DUMMY_CHARGE)

        self.assertRaisesRegexp(stripe.error.InvalidRequestError,
                                'No dispute for charge',
                                charge.update_dispute)

        self.assertRaisesRegexp(stripe.error.InvalidRequestError,
                                'No dispute for charge',
                                charge.close_dispute)


class AccountTest(StripeTestCase):

    def test_retrieve_account(self):
        account = stripe.Account.retrieve()
        self.assertEqual('test+bindings@stripe.com', account.email)
        self.assertFalse(account.charge_enabled)
        self.assertFalse(account.details_submitted)


class BalanceTest(StripeTestCase):

    def test_retrieve_balance(self):
        balance = stripe.Balance.retrieve()
        self.assertTrue(hasattr(balance, 'available'))
        self.assertTrue(isinstance(balance['available'], list))
        if len(balance['available']):
            self.assertTrue(hasattr(balance['available'][0], 'amount'))
            self.assertTrue(hasattr(balance['available'][0], 'currency'))

        self.assertTrue(hasattr(balance, 'pending'))
        self.assertTrue(isinstance(balance['pending'], list))
        if len(balance['pending']):
            self.assertTrue(hasattr(balance['pending'][0], 'amount'))
            self.assertTrue(hasattr(balance['pending'][0], 'currency'))

        self.assertEqual(False, balance['livemode'])
        self.assertEqual('balance', balance['object'])


class BalanceTransactionTest(StripeTestCase):

    def test_list_balance_transactions(self):
        balance_transactions = stripe.BalanceTransaction.all()
        self.assertTrue(hasattr(balance_transactions, 'has_more'))
        self.assertTrue(isinstance(balance_transactions.data, list))


class ApplicationFeeTest(StripeTestCase):
    def test_list_application_fees(self):
        application_fees = stripe.ApplicationFee.all()
        self.assertTrue(hasattr(application_fees, 'has_more'))
        self.assertTrue(isinstance(application_fees.data, list))


class CustomerTest(StripeTestCase):

    def test_list_customers(self):
        customers = stripe.Customer.all()
        self.assertTrue(isinstance(customers.data, list))

    def test_list_charges(self):
        customer = stripe.Customer.create(description="foo bar",
                                          card=DUMMY_CARD)

        stripe.Charge.create(customer=customer.id, amount=100, currency='usd')

        self.assertEqual(1,
                         len(customer.charges().data))

    def test_unset_description(self):
        customer = stripe.Customer.create(description="foo bar")

        customer.description = None
        customer.save()

        self.assertEqual(None, customer.retrieve(customer.id).description)

    def test_cannot_set_empty_string(self):
        customer = stripe.Customer()
        self.assertRaises(ValueError, setattr, customer, "description", "")

    def test_customer_add_card(self):
        customer = stripe.Customer.create(description="add_customer_card")
        card = customer.cards.create(card=DUMMY_CARD)
        card.save()

        updated_customer = stripe.Customer.retrieve(customer.id)
        retrieved_card = updated_customer.cards.retrieve(card.id)
        self.assertEqual(len(updated_customer.cards.data), 1)
        self.assertEqual(retrieved_card.id, card.id)

    def test_customer_update_card(self):
        customer = stripe.Customer.create(description="update_customer_card")
        card = customer.cards.create(card=DUMMY_CARD)
        card.save()

        updated_customer = stripe.Customer.retrieve(customer.id)
        retrieved_card = updated_customer.cards.retrieve(card.id)
        self.assertEqual(len(updated_customer.cards.data), 1)
        self.assertEqual(retrieved_card.id, card.id)

        retrieved_card.name = 'The Best'
        retrieved_card.save()

        post_update_customer = stripe.Customer.retrieve(customer.id)
        post_update_card = post_update_customer.cards.retrieve(card.id)

        self.assertEqual('The Best', post_update_card.name)

    def test_customer_delete_card(self):
        customer = stripe.Customer.create(description="update_customer_card")
        card = customer.cards.create(card=DUMMY_CARD)
        card.save()

        updated_customer = stripe.Customer.retrieve(customer.id)
        retrieved_card = updated_customer.cards.retrieve(card.id)
        self.assertEqual(len(updated_customer.cards.data), 1)

        retrieved_card.delete()

        post_delete_customer = stripe.Customer.retrieve(customer.id)
        self.assertEquals(len(post_delete_customer.cards.data), 0)


class TransferTest(StripeTestCase):

    def test_list_transfers(self):
        transfers = stripe.Transfer.all()
        self.assertTrue(isinstance(transfers.data, list))
        self.assertTrue(isinstance(transfers.data[0], stripe.Transfer))

    def test_cancel_transfer(self):
        transfer = stripe.Transfer.all().data[0]
        self.assertRaisesRegexp(stripe.error.InvalidRequestError,
                                'Transfer cannot be canceled',
                                transfer.cancel)


class RecipientTest(StripeTestCase):

    def test_list_recipients(self):
        recipients = stripe.Recipient.all()
        self.assertTrue(isinstance(recipients.data, list))
        self.assertTrue(isinstance(recipients.data[0], stripe.Recipient))

    def test_recipient_transfers(self):
        recipient = stripe.Recipient.all(count=1).data[0]

        # Weak assertion since the list could be empty
        for transfer in recipient.transfers().data:
            self.assertTrue(isinstance(transfer, stripe.Transfer))

    def test_recipient_add_card(self):
        recipient = stripe.Recipient.create(
            name="Best Debitholder",
            description="add_recipient_card",
            type="individual"
        )
        card = recipient.cards.create(card=DUMMY_DEBIT_CARD)
        card.save()

        updated_recipient = stripe.Recipient.retrieve(recipient.id)
        retrieved_card = updated_recipient.cards.retrieve(card.id)
        self.assertEqual(len(updated_recipient.cards.data), 1)
        self.assertEqual(retrieved_card.id, card.id)

    def test_recipient_update_card(self):
        recipient = stripe.Recipient.create(
            name="Best Debitholder",
            description="update_recipient_card",
            type="individual"
        )
        card = recipient.cards.create(card=DUMMY_DEBIT_CARD)
        card.save()

        updated_recipient = stripe.Recipient.retrieve(recipient.id)
        retrieved_card = updated_recipient.cards.retrieve(card.id)
        self.assertEqual(len(updated_recipient.cards.data), 1)
        self.assertEqual(retrieved_card.id, card.id)

        retrieved_card.name = 'The Best'
        retrieved_card.save()

        post_update_recipient = stripe.Recipient.retrieve(recipient.id)
        post_update_card = post_update_recipient.cards.retrieve(card.id)

        self.assertEqual('The Best', post_update_card.name)

    def test_recipient_delete_card(self):
        recipient = stripe.Recipient.create(
            name="Best Debitholder",
            description="update_recipient_card",
            type="individual"
        )
        card = recipient.cards.create(card=DUMMY_DEBIT_CARD)
        card.save()

        updated_recipient = stripe.Recipient.retrieve(recipient.id)
        retrieved_card = updated_recipient.cards.retrieve(card.id)
        self.assertEqual(len(updated_recipient.cards.data), 1)

        retrieved_card.delete()

        post_delete_recipient = stripe.Recipient.retrieve(recipient.id)
        self.assertEquals(len(post_delete_recipient.cards.data), 0)


class CustomerPlanTest(StripeTestCase):

    def setUp(self):
        super(CustomerPlanTest, self).setUp()
        try:
            self.plan_obj = stripe.Plan.create(**DUMMY_PLAN)
        except stripe.error.InvalidRequestError:
            self.plan_obj = None

    def tearDown(self):
        if self.plan_obj:
            try:
                self.plan_obj.delete()
            except stripe.error.InvalidRequestError:
                pass
        super(CustomerPlanTest, self).tearDown()

    def test_create_customer(self):
        self.assertRaises(stripe.error.InvalidRequestError,
                          stripe.Customer.create,
                          plan=DUMMY_PLAN['id'])
        customer = stripe.Customer.create(
            plan=DUMMY_PLAN['id'], card=DUMMY_CARD)
        self.assertTrue(hasattr(customer, 'subscriptions'))
        self.assertFalse(hasattr(customer, 'plan'))
        customer.delete()
        self.assertFalse(hasattr(customer, 'plan'))
        self.assertTrue(customer.deleted)

    def test_legacy_update_and_cancel_subscription(self):
        customer = stripe.Customer.create(card=DUMMY_CARD)

        sub = customer.update_subscription(plan=DUMMY_PLAN['id'])
        self.assertEqual(customer.subscription.id, sub.id)
        self.assertEqual(DUMMY_PLAN['id'], sub.plan.id)

        customer.cancel_subscription(at_period_end=True)
        self.assertEqual(customer.subscription.status, 'active')
        self.assertTrue(customer.subscription.cancel_at_period_end)
        customer.cancel_subscription()
        self.assertEqual(customer.subscription.status, 'canceled')

    def test_create_and_cancel_customer_subscription(self):
        customer = stripe.Customer.create(card=DUMMY_CARD)

        subscription = customer.subscriptions.create(plan=DUMMY_PLAN['id'])
        self.assertEqual(DUMMY_PLAN['id'], subscription.plan.id)

        subscription = customer.subscriptions.retrieve(subscription.id)
        subscription.delete(at_period_end=True)
        subscription = customer.subscriptions.retrieve(subscription.id)
        self.assertEqual(subscription.status, 'active')
        self.assertTrue(subscription.cancel_at_period_end)

        subscription = customer.subscriptions.retrieve(subscription.id)
        subscription = subscription.delete()
        self.assertEqual(subscription.status, 'canceled')

    def test_create_and_update_customer_subscription(self):
        customer = stripe.Customer.create(card=DUMMY_CARD)
        subscription = customer.subscriptions.create(plan=DUMMY_PLAN['id'])
        self.assertEqual(DUMMY_PLAN['id'], subscription.plan.id)

        subscription = customer.subscriptions.retrieve(subscription.id)
        trial_end_dttm = datetime.datetime.now() + datetime.timedelta(days=15)
        trial_end_int = int(time.mktime(trial_end_dttm.timetuple()))
        subscription.trial_end = trial_end_int
        subscription.plan = subscription.plan.id
        subscription.save()

        self.assertEqual(
            trial_end_int,
            customer.subscriptions.retrieve(subscription.id).trial_end)

    def test_datetime_trial_end(self):
        customer = stripe.Customer.create(
            plan=DUMMY_PLAN['id'], card=DUMMY_CARD,
            trial_end=datetime.datetime.now() + datetime.timedelta(days=15))
        self.assertTrue(customer.id)

    def test_integer_trial_end(self):
        trial_end_dttm = datetime.datetime.now() + datetime.timedelta(days=15)
        trial_end_int = int(time.mktime(trial_end_dttm.timetuple()))
        customer = stripe.Customer.create(plan=DUMMY_PLAN['id'],
                                          card=DUMMY_CARD,
                                          trial_end=trial_end_int)
        self.assertTrue(customer.id)


class InvoiceTest(StripeTestCase):

    def test_invoice(self):
        customer = stripe.Customer.create(card=DUMMY_CARD)

        customer.add_invoice_item(**DUMMY_INVOICE_ITEM)

        items = customer.invoice_items()
        self.assertEqual(1, len(items.data))

        invoice = stripe.Invoice.create(customer=customer)

        invoices = customer.invoices()
        self.assertEqual(1, len(invoices.data))
        self.assertEqual(1, len(invoices.data[0].lines.data))
        self.assertEqual(invoice.id, invoices.data[0].id)

        self.assertTrue(invoice.pay().paid)

        # It would be better to test for an actually existing
        # upcoming invoice but that isn't working so we'll just
        # check that the appropriate error comes back for now
        self.assertRaisesRegexp(
            stripe.error.InvalidRequestError,
            'No upcoming invoices',
            stripe.Invoice.upcoming,
            customer=customer)


class CouponTest(StripeTestCase):

    def test_create_coupon(self):
        self.assertRaises(stripe.error.InvalidRequestError,
                          stripe.Coupon.create, percent_off=25)
        c = stripe.Coupon.create(**DUMMY_COUPON)
        self.assertTrue(isinstance(c, stripe.Coupon))
        self.assertTrue(hasattr(c, 'percent_off'))
        self.assertTrue(hasattr(c, 'id'))

    def test_delete_coupon(self):
        c = stripe.Coupon.create(**DUMMY_COUPON)
        self.assertFalse(hasattr(c, 'deleted'))
        c.delete()
        self.assertFalse(hasattr(c, 'percent_off'))
        self.assertTrue(hasattr(c, 'id'))
        self.assertTrue(c.deleted)


class CustomerCouponTest(StripeTestCase):

    def setUp(self):
        super(CustomerCouponTest, self).setUp()
        self.coupon_obj = stripe.Coupon.create(**DUMMY_COUPON)

    def tearDown(self):
        self.coupon_obj.delete()

    def test_attach_coupon(self):
        customer = stripe.Customer.create(coupon=self.coupon_obj.id)
        self.assertTrue(hasattr(customer, 'discount'))
        self.assertNotEqual(None, customer.discount)

        customer.delete_discount()
        self.assertEqual(None, customer.discount)


class SubscriptionCouponTest(StripeTestCase):

    def setUp(self):
        super(SubscriptionCouponTest, self).setUp()
        self.plan_obj = stripe.Plan.create(**DUMMY_PLAN)
        self.coupon_obj = stripe.Coupon.create(**DUMMY_COUPON)

    def tearDown(self):
        self.coupon_obj.delete()

    def test_attach_coupon_to_subscription(self):
        customer = stripe.Customer.create(card=DUMMY_CARD)

        subscription = customer.subscriptions.create(
            plan=DUMMY_PLAN['id'], coupon=self.coupon_obj.id)

        self.assertTrue(hasattr(subscription, 'discount'))
        self.assertNotEqual(None, subscription.discount)

        subscription.delete_discount()
        self.assertEqual(None, subscription.discount)


class InvalidRequestErrorTest(StripeTestCase):

    def test_nonexistent_object(self):
        try:
            stripe.Charge.retrieve('invalid')
        except stripe.error.InvalidRequestError, e:
            self.assertEqual(404, e.http_status)
            self.assertTrue(isinstance(e.http_body, basestring))
            self.assertTrue(isinstance(e.json_body, dict))

    def test_invalid_data(self):
        try:
            stripe.Charge.create()
        except stripe.error.InvalidRequestError, e:
            self.assertEqual(400, e.http_status)
            self.assertTrue(isinstance(e.http_body, basestring))
            self.assertTrue(isinstance(e.json_body, dict))


class PlanTest(StripeTestCase):

    def setUp(self):
        super(PlanTest, self).setUp()
        try:
            stripe.Plan(DUMMY_PLAN['id']).delete()
        except stripe.error.InvalidRequestError:
            pass

    def test_create_plan(self):
        self.assertRaises(stripe.error.InvalidRequestError,
                          stripe.Plan.create, amount=2500)
        p = stripe.Plan.create(**DUMMY_PLAN)
        self.assertTrue(hasattr(p, 'amount'))
        self.assertTrue(hasattr(p, 'id'))
        self.assertEqual(DUMMY_PLAN['amount'], p.amount)
        p.delete()
        self.assertTrue(hasattr(p, 'deleted'))
        self.assertTrue(p.deleted)

    def test_update_plan(self):
        p = stripe.Plan.create(**DUMMY_PLAN)
        name = "New plan name"
        p.name = name
        p.save()
        self.assertEqual(name, p.name)
        p.delete()

    def test_update_plan_without_retrieving(self):
        p = stripe.Plan.create(**DUMMY_PLAN)

        name = 'updated plan name!'
        plan = stripe.Plan(p.id)
        plan.name = name

        # should only have name and id
        self.assertEqual(sorted(['id', 'name']), sorted(plan.keys()))
        plan.save()

        self.assertEqual(name, plan.name)
        # should load all the properties
        self.assertEqual(p.amount, plan.amount)
        p.delete()


class MetadataTest(StripeTestCase):

    def setUp(self):
        super(MetadataTest, self).setUp()
        self.initial_metadata = {
            'address': '77 Massachusetts Ave, Cambridge',
            'uuid': 'id'
        }

        charge = stripe.Charge.create(
            metadata=self.initial_metadata, **DUMMY_CHARGE)
        customer = stripe.Customer.create(
            metadata=self.initial_metadata, card=DUMMY_CARD)
        recipient = stripe.Recipient.create(
            metadata=self.initial_metadata, **DUMMY_RECIPIENT)
        transfer = stripe.Transfer.create(
            metadata=self.initial_metadata, **DUMMY_TRANSFER)

        self.support_metadata = [charge, customer, recipient, transfer]

    def test_noop_metadata(self):
        for obj in self.support_metadata:
            obj.description = 'test'
            obj.save()
            metadata = obj.retrieve(obj.id).metadata
            self.assertEqual(self.initial_metadata, metadata)

    def test_unset_metadata(self):
        for obj in self.support_metadata:
            obj.metadata = None
            expected_metadata = {}
            obj.save()
            metadata = obj.retrieve(obj.id).metadata
            self.assertEqual(expected_metadata, metadata)

    def test_whole_update(self):
        for obj in self.support_metadata:
            expected_metadata = {'txn_id': '3287423s34'}
            obj.metadata = expected_metadata.copy()
            obj.save()
            metadata = obj.retrieve(obj.id).metadata
            self.assertEqual(expected_metadata, metadata)

    def test_individual_delete(self):
        for obj in self.support_metadata:
            obj.metadata['uuid'] = None
            expected_metadata = {'address': self.initial_metadata['address']}
            obj.save()
            metadata = obj.retrieve(obj.id).metadata
            self.assertEqual(expected_metadata, metadata)

    def test_individual_update(self):
        for obj in self.support_metadata:
            obj.metadata['txn_id'] = 'abc'
            expected_metadata = {'txn_id': 'abc'}
            expected_metadata.update(self.initial_metadata)
            obj.save()
            metadata = obj.retrieve(obj.id).metadata
            self.assertEqual(expected_metadata, metadata)

    def test_combo_update(self):
        for obj in self.support_metadata:
            obj.metadata['txn_id'] = 'bar'
            obj.metadata = {'uid': '6735'}
            obj.save()
            metadata = obj.retrieve(obj.id).metadata
            self.assertEqual({'uid': '6735'}, metadata)

        for obj in self.support_metadata:
            obj.metadata = {'uid': '6735'}
            obj.metadata['foo'] = 'bar'
            obj.save()
            metadata = obj.retrieve(obj.id).metadata
            self.assertEqual({'uid': '6735', 'foo': 'bar'}, metadata)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_requestor
import datetime
import unittest
import urlparse

from mock import Mock

import stripe

from stripe.test.helper import StripeUnitTestCase

VALID_API_METHODS = ('get', 'post', 'delete')


class GMT1(datetime.tzinfo):

    def utcoffset(self, dt):
        return datetime.timedelta(hours=1)

    def dst(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return "Europe/Prague"


class APIHeaderMatcher(object):
    EXP_KEYS = ['X-Stripe-Client-User-Agent', 'User-Agent', 'Authorization']

    def __init__(self, api_key=None, extra={}):
        self.api_key = api_key or stripe.api_key
        self.extra = extra

    def __eq__(self, other):
        return (self._keys_match(other) and
                self._auth_match(other) and
                self._extra_match(other))

    def _keys_match(self, other):
        expected_keys = self.EXP_KEYS + self.extra.keys()
        return (sorted(other.keys()) == sorted(expected_keys))

    def _auth_match(self, other):
        return other['Authorization'] == "Bearer %s" % (self.api_key,)

    def _extra_match(self, other):
        for k, v in self.extra.iteritems():
            if other[k] != v:
                return False

        return True


class QueryMatcher(object):
    def __init__(self, expected):
        self.expected = sorted(expected)

    def __eq__(self, other):
        query = urlparse.urlsplit(other).query or other

        parsed = stripe.util.parse_qsl(query)
        return self.expected == sorted(parsed)


class UrlMatcher(object):
    def __init__(self, expected):
        self.exp_parts = urlparse.urlsplit(expected)

    def __eq__(self, other):
        other_parts = urlparse.urlsplit(other)

        for part in ('scheme', 'netloc', 'path', 'fragment'):
            expected = getattr(self.exp_parts, part)
            actual = getattr(other_parts, part)
            if expected != actual:
                print 'Expected %s "%s" but got "%s"' % (
                    part, expected, actual)
                return False

        q_matcher = QueryMatcher(stripe.util.parse_qsl(self.exp_parts.query))
        return q_matcher == other


class APIRequestorRequestTests(StripeUnitTestCase):
    ENCODE_INPUTS = {
        'dict': {
            'astring': 'bar',
            'anint': 5,
            'anull': None,
            'adatetime': datetime.datetime(2013, 1, 1, tzinfo=GMT1()),
            'atuple': (1, 2),
            'adict': {'foo': 'bar', 'boz': 5},
            'alist': ['foo', 'bar'],
        },
        'list': [1, 'foo', 'baz'],
        'string': 'boo',
        'unicode': u'\u1234',
        'datetime': datetime.datetime(2013, 1, 1, second=1, tzinfo=GMT1()),
        'none': None,
    }

    ENCODE_EXPECTATIONS = {
        'dict': [
            ('%s[astring]', 'bar'),
            ('%s[anint]', 5),
            ('%s[adatetime]', 1356994800),
            ('%s[adict][foo]', 'bar'),
            ('%s[adict][boz]', 5),
            ('%s[alist][]', 'foo'),
            ('%s[alist][]', 'bar'),
            ('%s[atuple][]', 1),
            ('%s[atuple][]', 2),
        ],
        'list': [
            ('%s[]', 1),
            ('%s[]', 'foo'),
            ('%s[]', 'baz'),
        ],
        'string': [('%s', 'boo')],
        'unicode': [('%s', stripe.util.utf8(u'\u1234'))],
        'datetime': [('%s', 1356994801)],
        'none': [],
    }

    def setUp(self):
        super(APIRequestorRequestTests, self).setUp()

        self.http_client = Mock(stripe.http_client.HTTPClient)
        self.http_client._verify_ssl_certs = True
        self.http_client.name = 'mockclient'

        self.requestor = stripe.api_requestor.APIRequestor(
            client=self.http_client)

    def mock_response(self, return_body, return_code, requestor=None):
        if not requestor:
            requestor = self.requestor

        self.http_client.request = Mock(
            return_value=(return_body, return_code))

    def check_call(self, meth, abs_url=None, headers=None,
                   post_data=None, requestor=None):
        if not abs_url:
            abs_url = 'https://api.stripe.com%s' % (self.valid_path,)
        if not requestor:
            requestor = self.requestor
        if not headers:
            headers = APIHeaderMatcher()

        self.http_client.request.assert_called_with(
            meth, abs_url, headers, post_data)

    @property
    def valid_path(self):
        return '/foo'

    def encoder_check(self, key):
        stk_key = "my%s" % (key,)

        value = self.ENCODE_INPUTS[key]
        expectation = [(k % (stk_key,), v) for k, v in
                       self.ENCODE_EXPECTATIONS[key]]

        stk = []
        fn = getattr(stripe.api_requestor.APIRequestor, "encode_%s" % (key,))
        fn(stk, stk_key, value)

        if isinstance(value, dict):
            expectation.sort()
            stk.sort()

        self.assertEqual(expectation, stk)

    def _test_encode_naive_datetime(self):
        stk = []

        stripe.api_requestor.APIRequestor.encode_datetime(
            stk, 'test', datetime.datetime(2013, 1, 1))

        # Naive datetimes will encode differently depending on your system
        # local time.  Since we don't know the local time of your system,
        # we just check that naive encodings are within 24 hours of correct.
        self.assertTrue(60 * 60 * 24 > abs(stk[0][1] - 1356994800))

    def test_param_encoding(self):
        self.mock_response('{}', 200)

        self.requestor.request('get', '', self.ENCODE_INPUTS)

        expectation = []
        for type_, values in self.ENCODE_EXPECTATIONS.iteritems():
            expectation.extend([(k % (type_,), str(v)) for k, v in values])

        self.check_call('get', QueryMatcher(expectation))

    def test_url_construction(self):
        CASES = (
            ('https://api.stripe.com?foo=bar', '', {'foo': 'bar'}),
            ('https://api.stripe.com?foo=bar', '?', {'foo': 'bar'}),
            ('https://api.stripe.com', '', {}),
            (
                'https://api.stripe.com/%20spaced?foo=bar%24&baz=5',
                '/%20spaced?foo=bar%24',
                {'baz': '5'}
            ),
            (
                'https://api.stripe.com?foo=bar&foo=bar',
                '?foo=bar',
                {'foo': 'bar'}
            ),
        )

        for expected, url, params in CASES:
            self.mock_response('{}', 200)

            self.requestor.request('get', url, params)

            self.check_call('get', expected)

    def test_empty_methods(self):
        for meth in VALID_API_METHODS:
            self.mock_response('{}', 200)

            body, key = self.requestor.request(meth, self.valid_path, {})

            if meth == 'post':
                post_data = ''
            else:
                post_data = None

            self.check_call(meth, post_data=post_data)
            self.assertEqual({}, body)

    def test_methods_with_params_and_response(self):
        for meth in VALID_API_METHODS:
            self.mock_response('{"foo": "bar", "baz": 6}', 200)

            params = {
                'alist': [1, 2, 3],
                'adict': {'frobble': 'bits'},
                'adatetime': datetime.datetime(2013, 1, 1, tzinfo=GMT1())
            }
            encoded = ('adict%5Bfrobble%5D=bits&adatetime=1356994800&'
                       'alist%5B%5D=1&alist%5B%5D=2&alist%5B%5D=3')

            body, key = self.requestor.request(meth, self.valid_path,
                                               params)
            self.assertEqual({'foo': 'bar', 'baz': 6}, body)

            if meth == 'post':
                self.check_call(
                    meth,
                    post_data=QueryMatcher(stripe.util.parse_qsl(encoded)))
            else:
                abs_url = "https://api.stripe.com%s?%s" % (
                    self.valid_path, encoded)
                self.check_call(meth, abs_url=UrlMatcher(abs_url))

    def test_uses_instance_key(self):
        key = 'fookey'
        requestor = stripe.api_requestor.APIRequestor(key,
                                                      client=self.http_client)

        self.mock_response('{}', 200, requestor=requestor)

        body, used_key = requestor.request('get', self.valid_path, {})

        self.check_call('get', headers=APIHeaderMatcher(key),
                        requestor=requestor)
        self.assertEqual(key, used_key)

    def test_passes_api_version(self):
        stripe.api_version = 'fooversion'

        self.mock_response('{}', 200)

        body, key = self.requestor.request('get', self.valid_path, {})

        self.check_call('get', headers=APIHeaderMatcher(
            extra={'Stripe-Version': 'fooversion'}))

    def test_fails_without_api_key(self):
        stripe.api_key = None

        self.assertRaises(stripe.error.AuthenticationError,
                          self.requestor.request,
                          'get', self.valid_path, {})

    def test_not_found(self):
        self.mock_response('{"error": {}}', 404)

        self.assertRaises(stripe.error.InvalidRequestError,
                          self.requestor.request,
                          'get', self.valid_path, {})

    def test_authentication_error(self):
        self.mock_response('{"error": {}}', 401)

        self.assertRaises(stripe.error.AuthenticationError,
                          self.requestor.request,
                          'get', self.valid_path, {})

    def test_card_error(self):
        self.mock_response('{"error": {}}', 402)

        self.assertRaises(stripe.error.CardError,
                          self.requestor.request,
                          'get', self.valid_path, {})

    def test_server_error(self):
        self.mock_response('{"error": {}}', 500)

        self.assertRaises(stripe.error.APIError,
                          self.requestor.request,
                          'get', self.valid_path, {})

    def test_invalid_json(self):
        self.mock_response('{', 200)

        self.assertRaises(stripe.error.APIError,
                          self.requestor.request,
                          'get', self.valid_path, {})

    def test_invalid_method(self):
        self.assertRaises(stripe.error.APIConnectionError,
                          self.requestor.request,
                          'foo', 'bar')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_resources
import pickle
import sys

import stripe

from stripe.test.helper import (
    StripeUnitTestCase, StripeApiTestCase,
    MySingleton, MyListable, MyCreatable, MyUpdateable, MyDeletable,
    MyResource, SAMPLE_INVOICE)

from stripe import util


class StripeObjectTests(StripeUnitTestCase):

    def test_initializes_with_parameters(self):
        obj = stripe.resource.StripeObject(
            'foo', 'bar', myparam=5, yourparam='boo')

        self.assertEqual('foo', obj.id)
        self.assertEqual('bar', obj.api_key)

    def test_access(self):
        obj = stripe.resource.StripeObject('myid', 'mykey', myparam=5)

        # Empty
        self.assertRaises(AttributeError, getattr, obj, 'myattr')
        self.assertRaises(KeyError, obj.__getitem__, 'myattr')
        self.assertEqual('def', obj.get('myattr', 'def'))
        self.assertEqual(None, obj.get('myattr'))

        # Setters
        obj.myattr = 'myval'
        obj['myitem'] = 'itval'
        self.assertEqual('sdef', obj.setdefault('mydef', 'sdef'))

        # Getters
        self.assertEqual('myval', obj.setdefault('myattr', 'sdef'))
        self.assertEqual('myval', obj.myattr)
        self.assertEqual('myval', obj['myattr'])
        self.assertEqual('myval', obj.get('myattr'))

        self.assertEqual(['id', 'myattr', 'mydef', 'myitem'],
                         sorted(obj.keys()))
        self.assertEqual(['itval', 'myid', 'myval', 'sdef'],
                         sorted(obj.values()))

        # Illegal operations
        self.assertRaises(ValueError, setattr, obj, 'foo', '')
        self.assertRaises(TypeError, obj.__delitem__, 'myattr')

    def test_refresh_from(self):
        obj = stripe.resource.StripeObject.construct_from({
            'foo': 'bar',
            'trans': 'me',
        }, 'mykey')

        self.assertEqual('mykey', obj.api_key)
        self.assertEqual('bar', obj.foo)
        self.assertEqual('me', obj['trans'])

        obj.refresh_from({
            'foo': 'baz',
            'johnny': 5,
        }, 'key2')

        self.assertEqual(5, obj.johnny)
        self.assertEqual('baz', obj.foo)
        self.assertRaises(AttributeError, getattr, obj, 'trans')
        self.assertEqual('key2', obj.api_key)

        obj.refresh_from({
            'trans': 4,
            'metadata': {'amount': 42}
        }, 'key2', True)

        self.assertEqual('baz', obj.foo)
        self.assertEqual(4, obj.trans)
        self.assertEqual({'amount': 42}, obj._previous_metadata)

    def test_refresh_from_nested_object(self):
        obj = stripe.resource.StripeObject.construct_from(
            SAMPLE_INVOICE, 'key')

        self.assertEqual(1, len(obj.lines.subscriptions))
        self.assertTrue(
            isinstance(obj.lines.subscriptions[0],
                       stripe.resource.StripeObject))
        self.assertEqual('month', obj.lines.subscriptions[0].plan.interval)

    def test_to_json(self):
        obj = stripe.resource.StripeObject.construct_from(
            SAMPLE_INVOICE, 'key')

        self.check_invoice_data(util.json.loads(str(obj)))

    def check_invoice_data(self, data):
        # Check rough structure
        self.assertEqual(20, len(data.keys()))
        self.assertEqual(3, len(data['lines'].keys()))
        self.assertEqual(0, len(data['lines']['invoiceitems']))
        self.assertEqual(1, len(data['lines']['subscriptions']))

        # Check various data types
        self.assertEqual(1338238728, data['date'])
        self.assertEqual(None, data['next_payment_attempt'])
        self.assertEqual(False, data['livemode'])
        self.assertEqual('month',
                         data['lines']['subscriptions'][0]['plan']['interval'])

    def test_repr(self):
        obj = stripe.resource.StripeObject(
            'foo', 'bar', myparam=5)

        obj['object'] = u'\u4e00boo\u1f00'

        res = repr(obj)

        if sys.version_info[0] < 3:
            res = unicode(repr(obj), 'utf-8')

        self.assertTrue(u'<StripeObject \u4e00boo\u1f00' in res)
        self.assertTrue(u'id=foo' in res)

    def test_pickling(self):
        obj = stripe.resource.StripeObject(
            'foo', 'bar', myparam=5)

        obj['object'] = 'boo'
        obj.refresh_from({'fala': 'lalala'}, api_key='bar', partial=True)

        self.assertEqual('lalala', obj.fala)

        pickled = pickle.dumps(obj)
        newobj = pickle.loads(pickled)

        self.assertEqual('foo', newobj.id)
        self.assertEqual('bar', newobj.api_key)
        self.assertEqual('boo', newobj['object'])
        self.assertEqual('lalala', newobj.fala)


class ListObjectTests(StripeApiTestCase):

    def setUp(self):
        super(ListObjectTests, self).setUp()

        self.lo = stripe.resource.ListObject.construct_from({
            'id': 'me',
            'url': '/my/path',
        }, 'mykey')

        self.mock_response([{
            'object': 'charge',
            'foo': 'bar',
        }])

    def assertResponse(self, res):
        self.assertTrue(isinstance(res[0], stripe.Charge))
        self.assertEqual('bar', res[0].foo)

    def test_all(self):
        res = self.lo.all(myparam='you')

        self.requestor_mock.request.assert_called_with(
            'get', '/my/path', {'myparam': 'you'})

        self.assertResponse(res)

    def test_create(self):
        res = self.lo.create(myparam='eter')

        self.requestor_mock.request.assert_called_with(
            'post', '/my/path', {'myparam': 'eter'})

        self.assertResponse(res)

    def test_retrieve(self):
        res = self.lo.retrieve('myid', myparam='cow')

        self.requestor_mock.request.assert_called_with(
            'get', '/my/path/myid', {'myparam': 'cow'})

        self.assertResponse(res)


class APIResourceTests(StripeApiTestCase):

    def test_retrieve_and_refresh(self):
        self.mock_response({
            'id': 'foo2',
            'bobble': 'scrobble',
        })

        res = MyResource.retrieve('foo*', myparam=5)

        url = '/v1/myresources/foo%2A'
        self.requestor_mock.request.assert_called_with(
            'get', url, {'myparam': 5}
        )

        self.assertEqual('scrobble', res.bobble)
        self.assertEqual('foo2', res.id)
        self.assertEqual('reskey', res.api_key)

        self.mock_response({
            'frobble': 5,
        })

        res = res.refresh()

        url = '/v1/myresources/foo2'
        self.requestor_mock.request.assert_called_with(
            'get', url, {'myparam': 5}
        )

        self.assertEqual(5, res.frobble)
        self.assertRaises(KeyError, res.__getitem__, 'bobble')

    def test_convert_to_stripe_object(self):
        sample = {
            'foo': 'bar',
            'adict': {
                'object': 'charge',
                'id': 42,
                'amount': 7,
            },
            'alist': [
                {
                    'object': 'customer',
                    'name': 'chilango'
                }
            ]
        }

        converted = stripe.resource.convert_to_stripe_object(sample, 'akey')

        # Types
        self.assertTrue(isinstance(converted, stripe.resource.StripeObject))
        self.assertTrue(isinstance(converted.adict, stripe.Charge))
        self.assertEqual(1, len(converted.alist))
        self.assertTrue(isinstance(converted.alist[0], stripe.Customer))

        # Values
        self.assertEqual('bar', converted.foo)
        self.assertEqual(42, converted.adict.id)
        self.assertEqual('chilango', converted.alist[0].name)

        # Stripping
        # TODO: We should probably be stripping out this property
        # self.assertRaises(AttributeError, getattr, converted.adict, 'object')


class SingletonAPIResourceTests(StripeApiTestCase):

    def test_retrieve(self):
        self.mock_response({
            'single': 'ton'
        })
        res = MySingleton.retrieve()

        self.requestor_mock.request.assert_called_with(
            'get', '/v1/mysingleton', {})

        self.assertEqual('ton', res.single)


class ListableAPIResourceTests(StripeApiTestCase):

    def test_all(self):
        self.mock_response([
            {
                'object': 'charge',
                'name': 'jose',
            },
            {
                'object': 'charge',
                'name': 'curly',
            }
        ])

        res = MyListable.all()

        self.requestor_mock.request.assert_called_with(
            'get', '/v1/mylistables', {})

        self.assertEqual(2, len(res))
        self.assertTrue(all(isinstance(obj, stripe.Charge) for obj in res))
        self.assertEqual('jose', res[0].name)
        self.assertEqual('curly', res[1].name)


class CreateableAPIResourceTests(StripeApiTestCase):

    def test_create(self):
        self.mock_response({
            'object': 'charge',
            'foo': 'bar',
        })

        res = MyCreatable.create()

        self.requestor_mock.request.assert_called_with(
            'post', '/v1/mycreatables', {})

        self.assertTrue(isinstance(res, stripe.Charge))
        self.assertEqual('bar', res.foo)


class UpdateableAPIResourceTests(StripeApiTestCase):

    def setUp(self):
        super(UpdateableAPIResourceTests, self).setUp()

        self.mock_response({
            'thats': 'it'
        })

        self.obj = MyUpdateable.construct_from({
            'id': 'myid',
            'foo': 'bar',
            'baz': 'boz',
            'metadata': {
                'size': 'l',
                'score': 4,
                'height': 10
            }
        }, 'mykey')

    def checkSave(self):
        self.assertTrue(self.obj is self.obj.save())

        self.assertEqual('it', self.obj.thats)
        # TODO: Should we force id to be retained?
        # self.assertEqual('myid', obj.id)
        self.assertRaises(AttributeError, getattr, self.obj, 'baz')

    def test_save(self):
        self.obj.baz = 'updated'
        self.obj.other = 'newval'
        self.obj.metadata.size = 'm'
        self.obj.metadata.info = 'a2'
        self.obj.metadata.height = None

        self.checkSave()

        self.requestor_mock.request.assert_called_with(
            'post',
            '/v1/myupdateables/myid',
            {
                'baz': 'updated',
                'other': 'newval',
                'metadata': {
                    'size': 'm',
                    'info': 'a2',
                    'height': '',
                }
            }
        )

    def test_save_replace_metadata(self):
        self.obj.baz = 'updated'
        self.obj.other = 'newval'
        self.obj.metadata = {
            'size': 'm',
            'info': 'a2',
            'score': 4,
        }

        self.checkSave()

        self.requestor_mock.request.assert_called_with(
            'post',
            '/v1/myupdateables/myid',
            {
                'baz': 'updated',
                'other': 'newval',
                'metadata': {
                    'size': 'm',
                    'info': 'a2',
                    'height': '',
                    'score': 4,
                }
            }
        )


class DeletableAPIResourceTests(StripeApiTestCase):

    def test_delete(self):
        self.mock_response({
            'id': 'mid',
            'deleted': True,
        })

        obj = MyDeletable.construct_from({
            'id': 'mid'
        }, 'mykey')

        self.assertTrue(obj is obj.delete())

        self.assertEqual(True, obj.deleted)
        self.assertEqual('mid', obj.id)

########NEW FILE########
__FILENAME__ = util
import logging
import sys

logger = logging.getLogger('stripe')

__all__ = ['StringIO', 'parse_qsl', 'json', 'utf8']

try:
    # When cStringIO is available
    import cStringIO as StringIO
except ImportError:
    import StringIO

try:
    from urlparse import parse_qsl
except ImportError:
    # Python < 2.6
    from cgi import parse_qsl

try:
    import json
except ImportError:
    json = None

if not (json and hasattr(json, 'loads')):
    try:
        import simplejson as json
    except ImportError:
        if not json:
            raise ImportError(
                "Stripe requires a JSON library, such as simplejson. "
                "HINT: Try installing the "
                "python simplejson library via 'pip install simplejson' or "
                "'easy_install simplejson', or contact support@stripe.com "
                "with questions.")
        else:
            raise ImportError(
                "Stripe requires a JSON library with the same interface as "
                "the Python 2.6 'json' library.  You appear to have a 'json' "
                "library with a different interface.  Please install "
                "the simplejson library.  HINT: Try installing the "
                "python simplejson library via 'pip install simplejson' "
                "or 'easy_install simplejson', or contact support@stripe.com"
                "with questions.")


def utf8(value):
    if isinstance(value, unicode) and sys.version_info < (3, 0):
        return value.encode('utf-8')
    else:
        return value

########NEW FILE########
__FILENAME__ = version
VERSION = '1.16.0'

########NEW FILE########
