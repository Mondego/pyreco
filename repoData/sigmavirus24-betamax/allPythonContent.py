__FILENAME__ = adapter
import os

from .cassette import Cassette
from .exceptions import BetamaxError
from datetime import datetime, timedelta
from requests.adapters import BaseAdapter, HTTPAdapter


class BetamaxAdapter(BaseAdapter):

    """This object is an implementation detail of the library.

    It is not meant to be a public API and is not exported as such.

    """

    def __init__(self, **kwargs):
        super(BetamaxAdapter, self).__init__()
        self.cassette = None
        self.cassette_name = None
        self.old_adapters = kwargs.pop('old_adapters', {})
        self.http_adapter = HTTPAdapter(**kwargs)
        self.serialize = None
        self.options = {}

    def cassette_exists(self):
        if self.cassette_name and os.path.exists(self.cassette_name):
            return True
        return False

    def close(self):
        self.http_adapter.close()

    def eject_cassette(self):
        if self.cassette:
            self.cassette.eject()
        self.cassette = None  # Allow self.cassette to be garbage-collected

    def load_cassette(self, cassette_name, serialize, options):
        self.cassette_name = cassette_name
        self.serialize = serialize
        self.options.update(options.items())
        placeholders = self.options.get('placeholders', [])

        default_options = Cassette.default_cassette_options

        match_requests_on = self.options.get(
            'match_requests_on', default_options['match_requests_on']
            )

        preserve_exact_body_bytes = self.options.get(
            'preserve_exact_body_bytes',
            )

        self.cassette = Cassette(
            cassette_name, serialize, placeholders=placeholders,
            record_mode=self.options.get('record'),
            preserve_exact_body_bytes=preserve_exact_body_bytes,
            cassette_library_dir=self.options.get('cassette_library_dir')
            )

        if 'record' in self.options:
            self.cassette.record_mode = self.options['record']
        self.cassette.match_options = match_requests_on

        re_record_interval = timedelta.max
        if self.options.get('re_record_interval'):
            re_record_interval = timedelta(self.options['re_record_interval'])

        now = datetime.utcnow()
        if re_record_interval < (now - self.cassette.earliest_recorded_date):
            self.cassette.clear()

    def send(self, request, stream=False, timeout=None, verify=True,
             cert=None, proxies=None):
        interaction = None

        if not self.cassette:
            raise BetamaxError('No cassette was specified or found.')

        if self.cassette.interactions:
            interaction = self.cassette.find_match(request)

        if not interaction and self.cassette.is_recording():
            interaction = self.send_and_record(
                request, stream, timeout, verify, cert, proxies
                )

        if not interaction:
            raise BetamaxError(unhandled_request_message(request,
                                                         self.cassette))

        resp = interaction.as_response()
        resp.connection = self
        return resp

    def send_and_record(self, request, stream=False, timeout=None,
                        verify=True, cert=None, proxies=None):
        adapter = self.find_adapter(request.url)
        response = adapter.send(
            request, stream=True, timeout=timeout, verify=verify,
            cert=cert, proxies=proxies
            )
        self.cassette.save_interaction(response, request)
        return self.cassette.interactions[-1]

    def find_adapter(self, url):
        for (prefix, adapter) in self.old_adapters.items():

            if url.lower().startswith(prefix):
                return adapter

        # Unlike in requests, we cannot possibly get this far.


UNHANDLED_REQUEST_EXCEPTION = """A request was made that could not be handled.

A request was made to {url} that could not be found in {cassette_file_path}.

The settings on the cassette are:

    - record_mode: {cassette_record_mode}
    - match_options {cassette_match_options}.
"""


def unhandled_request_message(request, cassette):
    return UNHANDLED_REQUEST_EXCEPTION.format(
        url=request.url, cassette_file_path=cassette.cassette_name,
        cassette_record_mode=cassette.record_mode,
        cassette_match_options=cassette.match_options
        )

########NEW FILE########
__FILENAME__ = cassette
# -*- coding: utf-8 -*-
from .interaction import Interaction
from .util import (_option_from, serialize_prepared_request,
                   serialize_response, timestamp)
from betamax.matchers import matcher_registry
from betamax.serializers import serializer_registry, SerializerProxy
from datetime import datetime
from functools import partial

import os.path


class Cassette(object):

    default_cassette_options = {
        'record_mode': 'once',
        'match_requests_on': ['method', 'uri'],
        're_record_interval': None,
        'placeholders': [],
        'preserve_exact_body_bytes': False
    }

    def __init__(self, cassette_name, serialization_format, **kwargs):
        #: Short name of the cassette
        self.cassette_name = cassette_name

        self.serialized = None

        defaults = Cassette.default_cassette_options

        # Determine the record mode
        self.record_mode = _option_from('record_mode', kwargs, defaults)

        # Retrieve the serializer for this cassette
        self.serializer = SerializerProxy.find(
            serialization_format, kwargs.get('cassette_library_dir'),
            cassette_name
            )
        self.cassette_path = self.serializer.cassette_path

        # Determine which placeholders to use
        self.placeholders = kwargs.get('placeholders')
        if not self.placeholders:
            self.placeholders = defaults['placeholders']

        # Determine whether to preserve exact body bytes
        self.preserve_exact_body_bytes = _option_from(
            'preserve_exact_body_bytes', kwargs, defaults
            )

        # Initialize the interactions
        self.interactions = []

        # Initialize the match options
        self.match_options = set()

        self.load_interactions()
        self.serializer.allow_serialization = self.is_recording()

    @staticmethod
    def can_be_loaded(cassette_library_dir, cassette_name, serialize_with,
                      record_mode):
        # If we want to record a cassette we don't care if the file exists
        # yet
        recording = False
        if record_mode in ['once', 'all', 'new_episodes']:
            recording = True

        serializer = serializer_registry.get(serialize_with)
        if not serializer:
            raise ValueError(
                'Serializer {0} is not registered with Betamax'.format(
                    serialize_with
                    ))

        cassette_path = serializer.generate_cassette_name(
            cassette_library_dir, cassette_name
            )
        # Otherwise if we're only replaying responses, we should probably
        # have the cassette the user expects us to load and raise.
        return os.path.exists(cassette_path) or recording

    def clear(self):
        # Clear out the interactions
        self.interactions = []
        # Serialize to the cassette file
        self._save_cassette()

    @property
    def earliest_recorded_date(self):
        """The earliest date of all of the interactions this cassette."""
        if self.interactions:
            i = sorted(self.interactions, key=lambda i: i.recorded_at)[0]
            return i.recorded_at
        return datetime.now()

    def eject(self):
        self._save_cassette()

    def find_match(self, request):
        """Find a matching interaction based on the matchers and request.

        This uses all of the matchers selected via configuration or
        ``use_cassette`` and passes in the request currently in progress.

        :param request: ``requests.PreparedRequest``
        :returns: :class:`Interaction <Interaction>`
        """
        opts = self.match_options
        # Curry those matchers
        matchers = [partial(matcher_registry[o].match, request) for o in opts]

        for i in self.interactions:
            if i.match(matchers):  # If the interaction matches everything
                if self.record_mode == 'all':
                    # If we're recording everything and there's a matching
                    # interaction we want to overwrite it, so we remove it.
                    self.interactions.remove(i)
                    break
                return i

        # No matches. So sad.
        return None

    def is_empty(self):
        """Determines if the cassette when loaded was empty."""
        return not self.serialized

    def is_recording(self):
        """Returns if the cassette is recording."""
        values = {
            'none': False,
            'once': self.is_empty(),
        }
        return values.get(self.record_mode, True)

    def load_interactions(self):
        if self.serialized is None:
            self.serialized = self.serializer.deserialize()

        interactions = self.serialized.get('http_interactions', [])
        self.interactions = [Interaction(i) for i in interactions]

        for i in self.interactions:
            i.replace_all(self.placeholders, ('placeholder', 'replace'))

    def sanitize_interactions(self):
        for i in self.interactions:
            i.replace_all(self.placeholders)

    def save_interaction(self, response, request):
        interaction = self.serialize_interaction(response, request)
        self.interactions.append(Interaction(interaction, response))

    def serialize_interaction(self, response, request):
        return {
            'request': serialize_prepared_request(
                request,
                self.preserve_exact_body_bytes
                ),
            'response': serialize_response(
                response,
                self.preserve_exact_body_bytes
                ),
            'recorded_at': timestamp(),
        }

    # Private methods
    def _save_cassette(self):
        self.sanitize_interactions()

        cassette_data = {
            'http_interactions': [i.json for i in self.interactions],
            'recorded_with': 'betamax/{version}'
        }
        self.serializer.serialize(cassette_data)

########NEW FILE########
__FILENAME__ = interaction
from .util import (deserialize_response, deserialize_prepared_request,
                   from_list)
from datetime import datetime


class Interaction(object):

    """The Interaction object represents the entirety of a single interaction.

    The interaction includes the date it was recorded, its JSON
    representation, and the ``requests.Response`` object complete with its
    ``request`` attribute.

    This object also handles the filtering of sensitive data.

    No methods or attributes on this object are considered public or part of
    the public API. As such they are entirely considered implementation
    details and subject to change. Using or relying on them is not wise or
    advised.

    """

    def __init__(self, interaction, response=None):
        self.recorded_at = None
        self.json = interaction
        self.orig_response = response
        self.deserialize()

    def as_response(self):
        """Returns the Interaction as a Response object."""
        return self.recorded_response

    def deserialize(self):
        """Turns a serialized interaction into a Response."""
        r = deserialize_response(self.json['response'])
        r.request = deserialize_prepared_request(self.json['request'])
        self.recorded_at = datetime.strptime(
            self.json['recorded_at'], '%Y-%m-%dT%H:%M:%S'
        )
        self.recorded_response = r

    def match(self, matchers):
        """Return whether this interaction is a match."""
        request = self.json['request']
        return all(m(request) for m in matchers)

    def replace(self, text_to_replace, placeholder):
        """Replace sensitive data in this interaction."""
        self.replace_in_headers(text_to_replace, placeholder)
        self.replace_in_body(text_to_replace, placeholder)
        self.replace_in_uri(text_to_replace, placeholder)

    def replace_all(self, replacements, key_order=('replace', 'placeholder')):
        """Easy way to accept all placeholders registered."""
        (replace_key, placeholder_key) = key_order
        for r in replacements:
            self.replace(r[replace_key], r[placeholder_key])

    def replace_in_headers(self, text_to_replace, placeholder):
        for obj in ('request', 'response'):
            headers = self.json[obj]['headers']
            for k, v in list(headers.items()):
                v = from_list(v)
                headers[k] = v.replace(text_to_replace, placeholder)

    def replace_in_body(self, text_to_replace, placeholder):
        body = self.json['request']['body']
        # If body is not a string
        if hasattr(body, 'replace'):
            if text_to_replace in body:
                self.json['request']['body'] = body.replace(
                    text_to_replace, placeholder
                )
        # If body is a dictionary
        else:
            body = self.json['request']['body'].get('string', '')
            if text_to_replace in body:
                self.json['request']['body']['string'] = body.replace(
                    text_to_replace, placeholder
                )

        body = self.json['response']['body'].get('string', '')
        if text_to_replace in body:
            self.json['response']['body']['string'] = body.replace(
                text_to_replace, placeholder
            )

    def replace_in_uri(self, text_to_replace, placeholder):
        for (obj, key) in (('request', 'uri'), ('response', 'url')):
            uri = self.json[obj][key]
            if text_to_replace in uri:
                self.json[obj][key] = uri.replace(
                    text_to_replace, placeholder
                )

########NEW FILE########
__FILENAME__ = mock_response
from email import parser, message


class MockHTTPResponse(object):
    def __init__(self, headers):
        from .util import coerce_content

        h = ["%s: %s" % (k, v) for (k, v) in headers.items()]
        h = map(coerce_content, h)
        h = '\r\n'.join(h)
        p = parser.Parser(EmailMessage)
        # Thanks to Python 3, we have to use the slightly more awful API below
        # mimetools was deprecated so we have to use email.message.Message
        # which takes no arguments in its initializer.
        self.msg = p.parsestr(h)
        self.msg.set_payload(h)

    def isclosed(self):
        return False


class EmailMessage(message.Message):
    def getheaders(self, value, *args):
        return [self.get(value, b'', *args)]

########NEW FILE########
__FILENAME__ = util
from .mock_response import MockHTTPResponse
from datetime import datetime
from requests.models import PreparedRequest, Response
from requests.packages.urllib3 import HTTPResponse
from requests.structures import CaseInsensitiveDict
from requests.status_codes import _codes
from requests.cookies import RequestsCookieJar

import base64
import io


def coerce_content(content, encoding=None):
    if hasattr(content, 'decode'):
        content = content.decode(encoding or 'utf-8', 'replace')
    return content


def body_io(string, encoding=None):
    if hasattr(string, 'encode'):
        string = string.encode(encoding or 'utf-8')
    return io.BytesIO(string)


def from_list(value):
    if isinstance(value, list):
        return value[0]
    return value


def add_body(r, preserve_exact_body_bytes, body_dict):
    """Simple function which takes a response or request and coerces the body.

    This function adds either ``'string'`` or ``'base64_string'`` to
    ``body_dict``. If ``preserve_exact_body_bytes`` is ``True`` then it
    encodes the body as a base64 string and saves it like that. Otherwise,
    it saves the plain string.

    :param r: This is either a PreparedRequest instance or a Response
        instance.
    :param preserve_exact_body_bytes bool: Either True or False.
    :param body_dict dict: A dictionary already containing the encoding to be
        used.
    """
    body = getattr(r, 'raw', getattr(r, 'body', None))
    if hasattr(body, 'read'):
        body = body.read()

    if not body:
        body = ''

    if (preserve_exact_body_bytes or
            'gzip' in r.headers.get('Content-Encoding', '')):
        body_dict['base64_string'] = base64.b64encode(body).decode()
    else:
        body_dict['string'] = coerce_content(body, body_dict['encoding'])


def serialize_prepared_request(request, preserve_exact_body_bytes):
    headers = request.headers
    body = {'encoding': 'utf-8'}
    add_body(request, preserve_exact_body_bytes, body)
    return {
        'body': body,
        'headers': dict(
            (coerce_content(k, 'utf-8'), [v]) for (k, v) in headers.items()
        ),
        'method': request.method,
        'uri': request.url,
    }


def deserialize_prepared_request(serialized):
    p = PreparedRequest()
    p._cookies = RequestsCookieJar()
    body = serialized['body']
    if isinstance(body, dict):
        original_body = body.get('string')
        p.body = original_body or base64.b64decode(
            body.get('base64_string', '').encode())
    else:
        p.body = body
    h = [(k, from_list(v)) for k, v in serialized['headers'].items()]
    p.headers = CaseInsensitiveDict(h)
    p.method = serialized['method']
    p.url = serialized['uri']
    return p


def serialize_response(response, preserve_exact_body_bytes):
    body = {'encoding': response.encoding}
    add_body(response, preserve_exact_body_bytes, body)

    return {
        'body': body,
        'headers': dict((k, [v]) for k, v in response.headers.items()),
        'status': {'code': response.status_code, 'message': response.reason},
        'url': response.url,
    }


def deserialize_response(serialized):
    r = Response()
    r.encoding = serialized['body']['encoding']
    h = [(k, from_list(v)) for k, v in serialized['headers'].items()]
    r.headers = CaseInsensitiveDict(h)
    r.url = serialized.get('url', '')
    if 'status' in serialized:
        r.status_code = serialized['status']['code']
        r.reason = serialized['status']['message']
    else:
        r.status_code = serialized['status_code']
        r.reason = _codes[r.status_code][0].upper()
    add_urllib3_response(serialized, r)
    return r


def add_urllib3_response(serialized, response):
    if 'base64_string' in serialized['body']:
        body = io.BytesIO(
            base64.b64decode(serialized['body']['base64_string'].encode())
        )
    else:
        body = body_io(**serialized['body'])

    h = HTTPResponse(
        body,
        status=response.status_code,
        headers=response.headers,
        preload_content=False,
        original_response=MockHTTPResponse(response.headers)
    )
    response.raw = h


def timestamp():
    stamp = datetime.utcnow().isoformat()
    try:
        i = stamp.rindex('.')
    except ValueError:
        return stamp
    else:
        return stamp[:i]


def _option_from(option, kwargs, defaults):
    value = kwargs.get(option)
    if value is None:
        value = defaults.get(option)
    return value

########NEW FILE########
__FILENAME__ = configure
from .cassette import Cassette


class Configuration(object):

    """This object acts as a proxy to configure different parts of Betamax.

    You should only ever encounter this object when configuring the library as
    a whole. For example:

    .. code::

        with Betamax.configure() as config:
            config.cassette_library_dir = 'tests/cassettes/'
            config.default_cassette_options['record_mode'] = 'once'
            config.default_cassette_options['match_requests_on'] = ['uri']
            config.define_cassette_placeholder('<URI>', 'http://httpbin.org')
            config.preserve_exact_body_bytes = True

    """

    CASSETTE_LIBRARY_DIR = 'vcr/cassettes'

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def __setattr__(self, prop, value):
        if prop == 'preserve_exact_body_bytes':
            self.default_cassette_options[prop] = True
        else:
            super(Configuration, self).__setattr__(prop, value)

    @property
    def cassette_library_dir(self):
        """Retrieve and set the directory to store the cassettes in."""
        return Configuration.CASSETTE_LIBRARY_DIR

    @cassette_library_dir.setter
    def cassette_library_dir(self, value):
        Configuration.CASSETTE_LIBRARY_DIR = value

    @property
    def default_cassette_options(self):
        """Retrieve and set the default cassette options.

        The options include:

        - ``match_requests_on``
        - ``placeholders``
        - ``re_record_interval``
        - ``record_mode``

        Other options will be ignored.
        """
        return Cassette.default_cassette_options

    @default_cassette_options.setter
    def default_cassette_options(self, value):
        Cassette.default_cassette_options = value

    def define_cassette_placeholder(self, placeholder, replace):
        """Define a placeholder value for some text.

        This also will replace the placeholder text with the text you wish it
        to use when replaying interactions from cassettes.

        :param str placeholder: (required), text to be used as a placeholder
        :param str replace: (required), text to be replaced or replacing the
            placeholder
        """
        self.default_cassette_options['placeholders'].append({
            'placeholder': placeholder,
            'replace': replace
        })

########NEW FILE########
__FILENAME__ = exceptions
class BetamaxError(Exception):
    def __init__(self, message):
        super(BetamaxError, self).__init__(message)

    def __repr__(self):
        return 'BetamaxError("%s")' % self.message

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-


class BaseMatcher(object):

    """
    Base class that ensures sub-classes that implement custom matchers can be
    registered and have the only method that is required.

    Usage::

        from betamax import Betamax, BaseMatcher

        class MyMatcher(BaseMatcher):
            name = 'my'

            def match(self, request, recorded_request):
                # My fancy matching algorithm

        Betamax.register_request_matcher(MyMatcher)

    The last line is absolutely necessary.

    The `match` method will be given a `requests.PreparedRequest` object and a
    dictionary. The dictionary always has the following keys:

    - url
    - method
    - body
    - headers

    """

    name = None

    def __init__(self):
        if not self.name:
            raise ValueError('Matchers require names')
        self.on_init()

    def on_init(self):
        """Method to implement if you wish something to happen in ``__init__``.

        The return value is not checked and this is called at the end of
        ``__init__``. It is meant to provide the matcher author a way to
        perform things during initialization of the instance that would
        otherwise require them to override ``BaseMatcher.__init__``.
        """
        return None

    def match(self, request, recorded_request):
        """This is a method that must be implemented by the user.

        :param PreparedRequest request: A requests PreparedRequest object
        :param dict recorded_request: A dictionary containing the serialized
            request in the cassette
        :returns bool: True if they match else False
        """
        raise NotImplementedError('The match method must be implemented on'
                                  ' %s' % self.__class__.__name__)

########NEW FILE########
__FILENAME__ = body
# -*- coding: utf-8 -*-
from .base import BaseMatcher


class BodyMatcher(BaseMatcher):
    # Matches based on the body of the request
    name = 'body'

    def match(self, request, recorded_request):
        return request.body == recorded_request['body']

########NEW FILE########
__FILENAME__ = digest_auth
# -*- coding: utf-8 -*-
from .base import BaseMatcher
from betamax.cassette.util import from_list


class DigestAuthMatcher(BaseMatcher):

    """This matcher is provided to help those who need to use Digest Auth.

    .. note::

        The code requests 2.0.1 uses to generate this header is different from
        the code that every requests version after it uses. Specifically, in
        2.0.1 one of the parameters is ``qop=auth`` and every other version is
        ``qop="auth"``. Given that there's also an unsupported type of ``qop``
        in requests, I've chosen not to ignore ore sanitize this. All
        cassettes recorded on 2.0.1 will need to be re-recorded for any
        requests version after it.

        This matcher also ignores the ``cnonce`` and ``response`` parameters.
        These parameters require the system time to be monkey-patched and
        that is out of the scope of betamax

    """

    name = 'digest-auth'

    def match(self, request, recorded_request):
        request_digest = self.digest_parts(request.headers)
        recorded_digest = self.digest_parts(recorded_request['headers'])
        return request_digest == recorded_digest

    def digest_parts(self, headers):
        auth = headers.get('Authorization') or headers.get('authorization')
        if not auth:
            return None
        auth = from_list(auth).strip('Digest ')
        # cnonce and response will be based on the system time, which I will
        # not monkey-patch.
        excludes = ('cnonce', 'response')
        return [p for p in auth.split(', ') if not p.startswith(excludes)]

########NEW FILE########
__FILENAME__ = headers
# -*- coding: utf-8 -*-
from .base import BaseMatcher


class HeadersMatcher(BaseMatcher):
    # Matches based on the headers of the request
    name = 'headers'

    def match(self, request, recorded_request):
        return dict(request.headers) == self.flatten_headers(recorded_request)

    def flatten_headers(self, request):
        from betamax.cassette.util import from_list
        headers = request['headers'].items()
        return dict((k, from_list(v)) for (k, v) in headers)

########NEW FILE########
__FILENAME__ = host
# -*- coding: utf-8 -*-
from .base import BaseMatcher
from requests.compat import urlparse


class HostMatcher(BaseMatcher):
    # Matches based on the host of the request
    name = 'host'

    def match(self, request, recorded_request):
        request_host = urlparse(request.url).netloc
        recorded_host = urlparse(recorded_request['uri']).netloc
        return request_host == recorded_host

########NEW FILE########
__FILENAME__ = method
# -*- coding: utf-8 -*-
from .base import BaseMatcher


class MethodMatcher(BaseMatcher):
    # Matches based on the method of the request
    name = 'method'

    def match(self, request, recorded_request):
        return request.method == recorded_request['method']

########NEW FILE########
__FILENAME__ = path
# -*- coding: utf-8 -*-
from .base import BaseMatcher
from requests.compat import urlparse


class PathMatcher(BaseMatcher):
    # Matches based on the path of the request
    name = 'path'

    def match(self, request, recorded_request):
        request_path = urlparse(request.url).path
        recorded_path = urlparse(recorded_request['uri']).path
        return request_path == recorded_path

########NEW FILE########
__FILENAME__ = query
# -*- coding: utf-8 -*-
from .base import BaseMatcher
from requests.compat import urlparse

try:
    from urlparse import parse_qs
except ImportError:
    from urllib.parse import parse_qs


class QueryMatcher(BaseMatcher):
    # Matches based on the query of the request
    name = 'query'

    def to_dict(self, query):
        """Turn the query string into a dictionary"""
        return parse_qs(query or '')  # Protect against None

    def match(self, request, recorded_request):
        request_query = self.to_dict(urlparse(request.url).query)
        recorded_query = self.to_dict(
            urlparse(recorded_request['uri']).query
        )
        return request_query == recorded_query

########NEW FILE########
__FILENAME__ = uri
# -*- coding: utf-8 -*-
from .base import BaseMatcher
from .query import QueryMatcher
from requests.compat import urlparse


class URIMatcher(BaseMatcher):
    # Matches based on the uri of the request
    name = 'uri'

    def on_init(self):
        # Get something we can use to match query strings with
        self.query_matcher = QueryMatcher().match

    def match(self, request, recorded_request):
        queries_match = self.query_matcher(request, recorded_request)
        request_url, recorded_url = request.url, recorded_request['uri']
        return self.all_equal(request_url, recorded_url) and queries_match

    def parse(self, uri):
        parsed = urlparse(uri)
        return {
            'scheme': parsed.scheme,
            'netloc': parsed.netloc,
            'path': parsed.path,
            'fragment': parsed.fragment
            }

    def all_equal(self, new_uri, recorded_uri):
        new_parsed = self.parse(new_uri)
        recorded_parsed = self.parse(recorded_uri)
        return (new_parsed == recorded_parsed)

########NEW FILE########
__FILENAME__ = options
from .cassette import Cassette


def validate_record(record):
    return record in ['all', 'new_episodes', 'none', 'once']


def validate_matchers(matchers):
    from betamax.matchers import matcher_registry
    available_matchers = list(matcher_registry.keys())
    return all(m in available_matchers for m in matchers)


def validate_serializer(serializer):
    from betamax.serializers import serializer_registry
    return serializer in list(serializer_registry.keys())


def translate_cassette_options():
    for (k, v) in Cassette.default_cassette_options.items():
        yield (k, v) if k != 'record_mode' else ('record', v)


class Options(object):
    valid_options = {
        'match_requests_on': validate_matchers,
        're_record_interval': lambda x: x is None or x > 0,
        'record': validate_record,
        'serialize': validate_serializer,  # TODO: Remove this
        'serialize_with': validate_serializer,
        'preserve_exact_body_bytes': lambda x: x in [True, False],
    }

    defaults = {
        'match_requests_on': ['method', 'uri'],
        're_record_interval': None,
        'record': 'once',
        'serialize': None,  # TODO: Remove this
        'serialize_with': 'json',
        'preserve_exact_body_bytes': False,
    }

    def __init__(self, data=None):
        self.data = data or {}
        self.validate()
        self.defaults = Options.defaults.copy()
        self.defaults.update(translate_cassette_options())

    def __repr__(self):
        return 'Options(%s)' % self.data

    def __getitem__(self, key):
        return self.data.get(key, self.defaults.get(key))

    def __setitem__(self, key, value):
        self.data[key] = value
        return value

    def __delitem__(self, key):
        del self.data[key]

    def __contains__(self, key):
        return key in self.data

    def items(self):
        return self.data.items()

    def validate(self):
        for key, value in list(self.data.items()):
            if key not in Options.valid_options:
                del self[key]
            else:
                is_valid = Options.valid_options[key]
                if not is_valid(value):
                    del self[key]

########NEW FILE########
__FILENAME__ = recorder
# -*- coding: utf-8 -*-
from . import matchers, serializers
from .adapter import BetamaxAdapter
from .cassette import Cassette
from .configure import Configuration
from .options import Options


class Betamax(object):

    """This object contains the main API of the request-vcr library.

    This object is entirely a context manager so all you have to do is:

    .. code::

        s = requests.Session()
        with Betamax(s) as vcr:
            vcr.use_cassette('example')
            r = s.get('https://httpbin.org/get')

    Or more concisely, you can do:

    .. code::

        s = requests.Session()
        with Betamax(s).use_cassette('example') as vcr:
            r = s.get('https://httpbin.org/get')

    This object allows for the user to specify the cassette library directory
    and default cassette options.

    .. code::

        s = requests.Session()
        with Betamax(s, cassette_library_dir='tests/cassettes') as vcr:
            vcr.use_cassette('example')
            r = s.get('https://httpbin.org/get')

        with Betamax(s, default_cassette_options={
                're_record_interval': 1000
                }) as vcr:
            vcr.use_cassette('example')
            r = s.get('https://httpbin.org/get')

    """

    def __init__(self, session, cassette_library_dir=None,
                 default_cassette_options={}):
        #: Store the requests.Session object being wrapped.
        self.session = session
        #: Store the session's original adapters.
        self.http_adapters = session.adapters.copy()
        #: Create a new adapter to replace the existing ones
        self.betamax_adapter = BetamaxAdapter(old_adapters=self.http_adapters)
        # We need a configuration instance to make life easier
        self.config = Configuration()
        # Merge the new cassette options with the default ones
        self.config.default_cassette_options.update(
            default_cassette_options or {}
        )

        # If it was passed in, use that instead.
        if cassette_library_dir:
            self.config.cassette_library_dir = cassette_library_dir

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *ex_args):
        self.stop()
        # ex_args comes through as the exception type, exception value and
        # exception traceback. If any of them are not None, we should probably
        # try to raise the exception and not muffle anything.
        if any(ex_args):
            # If you return False, Python will re-raise the exception for you
            return False

    @staticmethod
    def configure():
        """Helps configure the library as a whole.

        .. code::

            with Betamax.configure() as config:
                config.cassette_library_dir = 'tests/cassettes/'
                config.default_cassette_options['match_options'] = [
                    'method', 'uri', 'headers'
                    ]
        """
        return Configuration()

    @property
    def current_cassette(self):
        """Returns the cassette that is currently in use.

        :returns: :class:`Cassette <betamax.cassette.Cassette>`
        """
        return self.betamax_adapter.cassette

    @staticmethod
    def register_request_matcher(matcher_class):
        """Register a new request matcher.

        :param matcher_class: (required), this must sub-class
            :class:`BaseMatcher <betamax.matchers.BaseMatcher>`
        """
        matchers.matcher_registry[matcher_class.name] = matcher_class()

    @staticmethod
    def register_serializer(serializer_class):
        """Register a new serializer.

        :param matcher_class: (required), this must sub-class
            :class:`BaseSerializer <betamax.serializers.BaseSerializer>`
        """
        name = serializer_class.name
        serializers.serializer_registry[name] = serializer_class()

    # ❙▸
    def start(self):
        """Start recording or replaying interactions."""
        for k in self.http_adapters:
            self.session.mount(k, self.betamax_adapter)

    # ■
    def stop(self):
        """Stop recording or replaying interactions."""
        # No need to keep the cassette in memory any longer.
        self.betamax_adapter.eject_cassette()
        # On exit, we no longer wish to use our adapter and we want the
        # session to behave normally! Woooo!
        self.betamax_adapter.close()
        for (k, v) in self.http_adapters.items():
            self.session.mount(k, v)

    def use_cassette(self, cassette_name, **kwargs):
        """Tell Betamax which cassette you wish to use for the context.

        :param str cassette_name: relative name, without the serialization
            format, of the cassette you wish Betamax would use
        :param str serialize_with: the format you want Betamax to serialize
            the cassette with
        :param str serialize: DEPRECATED the format you want Betamax to
            serialize the request and response data to and from
        """
        kwargs = Options(kwargs)
        serialize = kwargs['serialize'] or kwargs['serialize_with']
        kwargs['cassette_library_dir'] = self.config.cassette_library_dir

        can_load = Cassette.can_be_loaded(
            self.config.cassette_library_dir,
            cassette_name,
            serialize,
            kwargs['record']
            )

        if can_load:
            self.betamax_adapter.load_cassette(cassette_name, serialize,
                                               kwargs)
        else:
            # If we're not recording or replaying an existing cassette, we
            # should tell the user/developer that there is no cassette, only
            # Zuul
            raise ValueError('Cassette must have a valid name and may not be'
                             ' None.')
        return self

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-
NOT_IMPLEMENTED_ERROR_MSG = ('This method must be implemented by classes'
                             ' inheriting from BaseSerializer.')


class BaseSerializer(object):

    """
    Base Serializer class that provides an interface for other serializers.

    Usage::

        from betamax import Betamax, BaseSerializer


        class MySerializer(BaseSerializer):
            name = 'my'

            @staticmethod
            def generate_cassette_name(cassette_library_dir, cassette_name):
                # Generate a string that will give the relative path of a
                # cassette

            def serialize(self, cassette_data):
                # Take a dictionary and convert it to whatever

            def deserialize(self):
                # Uses a cassette file to return a dictionary with the
                # cassette information

        Betamax.register_serializer(MySerializer)

    The last line is absolutely necessary.

    """

    name = None

    @staticmethod
    def generate_cassette_name(cassette_library_dir, cassette_name):
        raise NotImplementedError(NOT_IMPLEMENTED_ERROR_MSG)

    def __init__(self):
        if not self.name:
            raise ValueError("Serializer's name attribute must be a string"
                             " value, not None.")

        self.on_init()

    def on_init(self):
        """Method to implement if you wish something to happen in ``__init__``.

        The return value is not checked and this is called at the end of
        ``__init__``. It is meant to provide the matcher author a way to
        perform things during initialization of the instance that would
        otherwise require them to override ``BaseSerializer.__init__``.
        """
        return None

    def serialize(self, cassette_data):
        """This is a method that must be implemented by the Serializer author.

        :param dict cassette_data: A dictionary with two keys:
            ``http_interactions``, ``recorded_with``.
        :returns: Serialized data as a string.
        """
        raise NotImplementedError(NOT_IMPLEMENTED_ERROR_MSG)

    def deserialize(self, cassette_data):
        """This is a method that must be implemented by the Serializer author.

        The return value is extremely important. If it is not empty, the
        dictionary returned must have the following structure::

            {
                'http_interactions': [{
                    # Interaction
                },
                {
                    # Interaction
                }],
                'recorded_with': 'name of recorder'
            }

        :params str cassette_data: The data serialized as a string which needs
            to be deserialized.
        :returns: dictionary
        """
        raise NotImplementedError(NOT_IMPLEMENTED_ERROR_MSG)

########NEW FILE########
__FILENAME__ = json_serializer
from .base import BaseSerializer

import json
import os


class JSONSerializer(BaseSerializer):
    # Serializes and deserializes a cassette to JSON
    name = 'json'

    @staticmethod
    def generate_cassette_name(cassette_library_dir, cassette_name):
        return os.path.join(cassette_library_dir,
                            '{0}.{1}'.format(cassette_name, 'json'))

    def serialize(self, cassette_data):
        return json.dumps(cassette_data)

    def deserialize(self, cassette_data):
        try:
            deserialized_data = json.loads(cassette_data)
        except ValueError:
            deserialized_data = {}

        return deserialized_data

########NEW FILE########
__FILENAME__ = proxy
# -*- coding: utf-8 -*-
from .base import BaseSerializer

import os


class SerializerProxy(BaseSerializer):

    """
    This is an internal implementation detail of the betamax library.

    No users implementing a serializer should be using this. Developers
    working on betamax need only understand that this handles the logic
    surrounding whether a cassette should be updated, overwritten, or created.

    It provides one consistent way for betamax to be confident in how it
    serializes the data it receives. It allows authors of Serializer classes
    to not have to duplicate how files are handled. It delegates the
    responsibility of actually serializing the data to those classes and
    handles the rest.

    """

    def __init__(self, serializer, cassette_path, allow_serialization=False):
        self.proxied_serializer = serializer
        self.allow_serialization = allow_serialization
        self.cassette_path = cassette_path

    def _ensure_path_exists(self):
        if not os.path.exists(self.cassette_path):
            open(self.cassette_path, 'w+').close()

    @classmethod
    def find(cls, serialize_with, cassette_library_dir, cassette_name):
        from . import serializer_registry
        serializer = serializer_registry.get(serialize_with)
        if serializer is None:
            raise ValueError(
                'No serializer registered for {0}'.format(serialize_with)
                )

        cassette_path = cls.generate_cassette_name(
            serializer, cassette_library_dir, cassette_name
            )
        return cls(serializer, cassette_path)

    @staticmethod
    def generate_cassette_name(serializer, cassette_library_dir,
                               cassette_name):
        return serializer.generate_cassette_name(
            cassette_library_dir, cassette_name
            )

    def serialize(self, cassette_data):
        if not self.allow_serialization:
            return

        self._ensure_path_exists()

        with open(self.cassette_path, 'w') as fd:
            fd.write(self.proxied_serializer.serialize(cassette_data))

    def deserialize(self):
        self._ensure_path_exists()

        data = {}
        with open(self.cassette_path) as fd:
            data = self.proxied_serializer.deserialize(fd.read())

        return data

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Requests documentation build configuration file, created by
# sphinx-quickstart on Sun Feb 13 23:54:25 2011.
#
# This file is execfile()d with the current directory set to its containing
# dir
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import os
import sys

# This environment variable makes decorators not decorate functions, so their
# signatures in the generated documentation are still correct
os.environ['GENERATING_DOCUMENTATION'] = "betamax"

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))
import betamax

# -- General configuration ---------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Betamax'
copyright = u'2013 - Ian Cordasco'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = betamax.__version__
# The full version, including alpha/beta/rc tags.
release = version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all
# documents #default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
# pygments_style = 'flask_theme_support.FlaskyStyle'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output -----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'nature'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None


# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
#html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = False

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = False

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'betamax.doc'


# -- Options for LaTeX output ----------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass
# [howto/manual]).
latex_documents = [
    ('index', 'betamax.tex', u'Betamax Documentation',
     u'Ian Cordasco', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output ----------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'github3.py', u'github3.py Documentation',
     [u'Ian Cordasco'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False

# -- Options for Texinfo output --------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'betamax', u'Betamax Documentation', u'Ian Cordasco',
     'Betamax', "Python imitation of Ruby's VCR", 'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
texinfo_appendices = []

########NEW FILE########
__FILENAME__ = conftest
import os
import sys
import betamax

sys.path.insert(0, os.path.abspath('.'))

with betamax.Betamax.configure() as config:
    config.cassette_library_dir = 'tests/cassettes/'

########NEW FILE########
__FILENAME__ = helper
import os
import unittest

from requests import Session


class IntegrationHelper(unittest.TestCase):
    cassette_created = True

    def setUp(self):
        self.cassette_path = None
        self.session = Session()

    def tearDown(self):
        if self.cassette_created:
            assert self.cassette_path is not None
            os.unlink(self.cassette_path)

########NEW FILE########
__FILENAME__ = test_backwards_compat
import betamax
import copy
from .helper import IntegrationHelper


class TestBackwardsCompatibleSerialization(IntegrationHelper):
    def setUp(self):
        super(TestBackwardsCompatibleSerialization, self).setUp()
        self.cassette_created = False
        opts = betamax.cassette.Cassette.default_cassette_options
        self.original_defaults = copy.deepcopy(opts)

        with betamax.Betamax.configure() as config:
            config.define_cassette_placeholder('<FOO>', 'nothing to replace')

    def tearDown(self):
        super(TestBackwardsCompatibleSerialization, self).setUp()
        Cassette = betamax.cassette.Cassette
        Cassette.default_cassette_options = self.original_defaults

    def test_can_deserialize_an_old_cassette(self):
        with betamax.Betamax(self.session).use_cassette('GitHub_emojis') as b:
            assert b.current_cassette is not None
            cassette = b.current_cassette
            assert len(cassette.interactions) > -1

    def test_matches_old_request_data(self):
        with betamax.Betamax(self.session).use_cassette('GitHub_emojis'):
            r = self.session.get('https://api.github.com/emojis')
            assert r is not None

    def tests_populates_correct_fields_with_missing_data(self):
        with betamax.Betamax(self.session).use_cassette('GitHub_emojis'):
            r = self.session.get('https://api.github.com/emojis')
            assert r.reason == 'OK'
            assert r.status_code == 200

    def tests_deserializes_old_cassette_headers(self):
        with betamax.Betamax(self.session).use_cassette('GitHub_emojis') as b:
            self.session.get('https://api.github.com/emojis')
            interaction = b.current_cassette.interactions[0].json
            header = interaction['request']['headers']['Accept']
            assert not isinstance(header, list)

########NEW FILE########
__FILENAME__ = test_placeholders
from betamax import Betamax
from betamax.cassette import Cassette

from copy import deepcopy
from tests.integration.helper import IntegrationHelper

original_cassette_options = deepcopy(Cassette.default_cassette_options)
b64_foobar = 'Zm9vOmJhcg=='  # base64.b64encode('foo:bar')


class TestPlaceholders(IntegrationHelper):
    def setUp(self):
        super(TestPlaceholders, self).setUp()
        config = Betamax.configure()
        config.define_cassette_placeholder('<AUTHORIZATION>', b64_foobar)

    def tearDown(self):
        super(TestPlaceholders, self).tearDown()
        Cassette.default_cassette_options = original_cassette_options

    def test_placeholders_work(self):
        placeholders = Cassette.default_cassette_options['placeholders']
        placeholder = {
            'placeholder': '<AUTHORIZATION>',
            'replace': b64_foobar
        }
        assert placeholders != []
        assert placeholder in placeholders

        s = self.session
        cassette = None
        with Betamax(s).use_cassette('test_placeholders') as recorder:
            r = s.get('http://httpbin.org/get', auth=('foo', 'bar'))
            cassette = recorder.current_cassette
            assert r.status_code == 200
            auth = r.json()['headers']['Authorization']
            assert b64_foobar in auth

        #cassette.sanitize_interactions()
        self.cassette_path = cassette.cassette_path
        i = cassette.interactions[0]
        auth = i.json['request']['headers']['Authorization']
        assert '<AUTHORIZATION>' in auth

########NEW FILE########
__FILENAME__ = test_preserve_exact_body_bytes
from .helper import IntegrationHelper
from betamax import Betamax
from betamax.cassette import Cassette

import copy


class TestPreserveExactBodyBytes(IntegrationHelper):
    def test_preserve_exact_body_bytes_does_not_munge_response_content(self):
        # Do not delete this cassette after the test
        self.cassette_created = False

        with Betamax(self.session) as b:
            b.use_cassette('preserve_exact_bytes',
                           preserve_exact_body_bytes=True)
            r = self.session.get('https://httpbin.org/get')
            assert 'headers' in r.json()

            interaction = b.current_cassette.interactions[0].json
            assert 'base64_string' in interaction['response']['body']


class TestPreserveExactBodyBytesForAllCassettes(IntegrationHelper):
    def setUp(self):
        super(TestPreserveExactBodyBytesForAllCassettes, self).setUp()
        self.orig = copy.deepcopy(Cassette.default_cassette_options)
        self.cassette_created = False

    def tearDown(self):
        super(TestPreserveExactBodyBytesForAllCassettes, self).tearDown()
        Cassette.default_cassette_options = self.orig

    def test_preserve_exact_body_bytes(self):
        with Betamax.configure() as config:
            config.preserve_exact_body_bytes = True

        with Betamax(self.session) as b:
            b.use_cassette('global_preserve_exact_body_bytes')
            r = self.session.get('https://httpbin.org/get')
            assert 'headers' in r.json()

            interaction = b.current_cassette.interactions[0].json
            assert 'base64_string' in interaction['response']['body']

########NEW FILE########
__FILENAME__ = test_record_modes
from betamax import Betamax, BetamaxError

from tests.integration.helper import IntegrationHelper


class TestRecordOnce(IntegrationHelper):
    def test_records_new_interaction(self):
        s = self.session
        with Betamax(s).use_cassette('test_record_once') as betamax:
            self.cassette_path = betamax.current_cassette.cassette_path
            assert betamax.current_cassette.is_empty() is True
            r = s.get('http://httpbin.org/get')
            assert r.status_code == 200
            assert betamax.current_cassette.is_empty() is True
            assert betamax.current_cassette.interactions != []

    def test_replays_response_from_cassette(self):
        s = self.session
        with Betamax(s).use_cassette('test_replays_response') as betamax:
            self.cassette_path = betamax.current_cassette.cassette_path
            assert betamax.current_cassette.is_empty() is True
            r0 = s.get('http://httpbin.org/get')
            assert r0.status_code == 200
            assert betamax.current_cassette.interactions != []
            assert len(betamax.current_cassette.interactions) == 1
            r1 = s.get('http://httpbin.org/get')
            assert len(betamax.current_cassette.interactions) == 1
            assert r1.status_code == 200
            assert r0.headers == r1.headers
            assert r0.content == r1.content


class TestRecordNone(IntegrationHelper):
    def test_raises_exception_when_no_interactions_present(self):
        s = self.session
        with Betamax(s) as betamax:
            betamax.use_cassette('test', record='none')
            self.cassette_created = False
            assert betamax.current_cassette is not None
            self.assertRaises(BetamaxError, s.get, 'http://httpbin.org/get')

    def test_record_none_does_not_create_cassettes(self):
        s = self.session
        with Betamax(s) as betamax:
            self.assertRaises(ValueError, betamax.use_cassette,
                              'test_record_none', record='none')
        self.cassette_created = False


class TestRecordNewEpisodes(IntegrationHelper):
    def setUp(self):
        super(TestRecordNewEpisodes, self).setUp()
        with Betamax(self.session).use_cassette('test_record_new'):
            self.session.get('http://httpbin.org/get')
            self.session.get('http://httpbin.org/redirect/2')

    def test_records_new_events_with_existing_cassette(self):
        s = self.session
        opts = {'record': 'new_episodes'}
        with Betamax(s).use_cassette('test_record_new', **opts) as betamax:
            cassette = betamax.current_cassette
            self.cassette_path = cassette.cassette_path
            assert cassette.interactions != []
            assert len(cassette.interactions) == 3
            assert cassette.is_empty() is False
            s.get('https://httpbin.org/get')
            assert len(cassette.interactions) == 4

        with Betamax(s).use_cassette('test_record_new') as betamax:
            cassette = betamax.current_cassette
            assert len(cassette.interactions) == 4
            r = s.get('https://httpbin.org/get')
            assert r.status_code == 200


class TestRecordNewEpisodesCreatesCassettes(IntegrationHelper):
    def test_creates_new_cassettes(self):
        recorder = Betamax(self.session)
        opts = {'record': 'new_episodes'}
        cassette_name = 'test_record_new_makes_new_cassettes'
        with recorder.use_cassette(cassette_name, **opts) as betamax:
            self.cassette_path = betamax.current_cassette.cassette_path
            self.session.get('https://httpbin.org/get')


class TestRecordAll(IntegrationHelper):
    def setUp(self):
        super(TestRecordAll, self).setUp()
        with Betamax(self.session).use_cassette('test_record_all'):
            self.session.get('http://httpbin.org/get')
            self.session.get('http://httpbin.org/redirect/2')

    def test_records_new_interactions(self):
        s = self.session
        opts = {'record': 'all'}
        with Betamax(s).use_cassette('test_record_all', **opts) as betamax:
            cassette = betamax.current_cassette
            self.cassette_path = cassette.cassette_path
            assert cassette.interactions != []
            assert len(cassette.interactions) == 3
            assert cassette.is_empty() is False
            s.post('http://httpbin.org/post', data={'foo': 'bar'})
            assert len(cassette.interactions) == 4

        with Betamax(s).use_cassette('test_record_all') as betamax:
            assert len(betamax.current_cassette.interactions) == 4

    def test_replaces_old_interactions(self):
        s = self.session
        opts = {'record': 'all'}
        with Betamax(s).use_cassette('test_record_all', **opts) as betamax:
            cassette = betamax.current_cassette
            self.cassette_path = cassette.cassette_path
            assert cassette.interactions != []
            assert len(cassette.interactions) == 3
            assert cassette.is_empty() is False
            s.get('http://httpbin.org/get')
            assert len(cassette.interactions) == 3

########NEW FILE########
__FILENAME__ = test_unicode
from betamax import Betamax
from tests.integration.helper import IntegrationHelper


class TestUnicode(IntegrationHelper):
    def test_unicode_is_saved_properly(self):
        s = self.session
        # https://github.com/kanzure/python-requestions/issues/4
        url = 'http://www.amazon.com/review/RAYTXRF3122TO'

        with Betamax(s).use_cassette('test_unicode') as beta:
            self.cassette_path = beta.current_cassette.cassette_path
            s.get(url)

########NEW FILE########
__FILENAME__ = test_cassettes_retain_global_configuration
import pytest
import unittest

from betamax import Betamax, cassette
from requests import Session


class TestCassetteRecordMode(unittest.TestCase):
    def setUp(self):
        with Betamax.configure() as config:
            config.default_cassette_options['record_mode'] = 'never'

    def tearDown(self):
        with Betamax.configure() as config:
            config.default_cassette_options['record_mode'] = 'once'

    def test_record_mode_is_never(self):
        s = Session()
        with pytest.raises(ValueError):
            with Betamax(s) as recorder:
                recorder.use_cassette('regression_record_mode')
                assert recorder.current_cassette is None

    def test_class_variables_retain_their_value(self):
        opts = cassette.Cassette.default_cassette_options
        assert opts['record_mode'] == 'never'

########NEW FILE########
__FILENAME__ = test_gzip_compression
import os
import unittest

from betamax import Betamax
from requests import Session


class TestGZIPRegression(unittest.TestCase):
    def tearDown(self):
        os.unlink('tests/cassettes/gzip_regression.json')

    def test_saves_content_as_gzip(self):
        s = Session()
        with Betamax(s).use_cassette('gzip_regression'):
            r = s.get(
                'https://api.github.com/repos/github3py/fork_this/issues/1',
                headers={'Accept-Encoding': 'gzip, deflate, compress'}
                )
            assert r.headers.get('Content-Encoding') == 'gzip'
            assert r.json() is not None

            r2 = s.get(
                'https://api.github.com/repos/github3py/fork_this/issues/1',
                headers={'Accept-Encoding': 'gzip, deflate, compress'}
                )
            assert r2.headers.get('Content-Encoding') == 'gzip'
            assert r2.json() is not None
            assert r2.json() == r.json()

        s = Session()
        with Betamax(s).use_cassette('gzip_regression'):
            r = s.get(
                'https://api.github.com/repos/github3py/fork_this/issues/1'
                )
            assert r.json() is not None

########NEW FILE########
__FILENAME__ = test_once_prevents_new_interactions
import pytest
import unittest

from betamax import Betamax, BetamaxError
from requests import Session


class TestOncePreventsNewInteractions(unittest.TestCase):

    """Test that using a cassette with once record mode prevents new requests.

    """

    def test_once_prevents_new_requests(self):
        s = Session()
        with Betamax(s).use_cassette('once_record_mode'):
            with pytest.raises(BetamaxError):
                s.get('http://example.com')

########NEW FILE########
__FILENAME__ = test_works_with_digest_auth
import unittest

from betamax import Betamax
from requests import Session
from requests.auth import HTTPDigestAuth


class TestDigestAuth(unittest.TestCase):
    def test_saves_content_as_gzip(self):
        s = Session()
        cassette_name = 'handles_digest_auth'
        match = ['method', 'uri', 'digest-auth']
        with Betamax(s).use_cassette(cassette_name, match_requests_on=match):
            r = s.get('https://httpbin.org/digest-auth/auth/user/passwd',
                      auth=HTTPDigestAuth('user', 'passwd'))
            assert r.ok
            assert r.history[0].status_code == 401

        s = Session()
        with Betamax(s).use_cassette(cassette_name, match_requests_on=match):
            r = s.get('https://httpbin.org/digest-auth/auth/user/passwd',
                      auth=HTTPDigestAuth('user', 'passwd'))
            assert r.json() is not None

########NEW FILE########
__FILENAME__ = test_adapter
import os
import sys
import unittest

# sys.path.insert(0, os.path.abspath('.'))
# sys.stderr.write('%s' % str(sys.path))

from betamax.adapter import BetamaxAdapter
from requests.adapters import HTTPAdapter


class TestBetamaxAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = BetamaxAdapter()

    def tearDown(self):
        self.adapter.eject_cassette()

    def test_has_http_adatper(self):
        assert self.adapter.http_adapter is not None
        assert isinstance(self.adapter.http_adapter, HTTPAdapter)

    def test_empty_initial_state(self):
        assert self.adapter.cassette is None
        assert self.adapter.cassette_name is None
        assert self.adapter.serialize is None

    def test_load_cassette(self):
        filename = 'test'
        self.adapter.load_cassette(filename, 'json', {
            'record': 'none',
            'cassette_library_dir': 'tests/cassettes/'
        })
        assert self.adapter.cassette is not None
        assert self.adapter.cassette_name == filename


if __name__ == '__main__':
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()

########NEW FILE########
__FILENAME__ = test_betamax
import unittest

from betamax import Betamax, matchers
from betamax.adapter import BetamaxAdapter
from betamax.cassette import Cassette
from requests import Session
from requests.adapters import HTTPAdapter


class TestBetamax(unittest.TestCase):
    def setUp(self):
        self.session = Session()
        self.vcr = Betamax(self.session)

    def test_initialization_does_alter_the_session(self):
        for v in self.session.adapters.values():
            assert not isinstance(v, BetamaxAdapter)
            assert isinstance(v, HTTPAdapter)

    def test_entering_context_alters_adapters(self):
        with self.vcr:
            for v in self.session.adapters.values():
                assert isinstance(v, BetamaxAdapter)

    def test_exiting_resets_the_adapters(self):
        with self.vcr:
            pass
        for v in self.session.adapters.values():
            assert not isinstance(v, BetamaxAdapter)

    def test_current_cassette(self):
        assert self.vcr.current_cassette is None
        self.vcr.use_cassette('test')
        assert isinstance(self.vcr.current_cassette, Cassette)

    def test_use_cassette_returns_cassette_object(self):
        assert self.vcr.use_cassette('test') is self.vcr

    def test_register_request_matcher(self):
        class FakeMatcher(object):
            name = 'fake'

        Betamax.register_request_matcher(FakeMatcher)
        assert 'fake' in matchers.matcher_registry
        assert isinstance(matchers.matcher_registry['fake'], FakeMatcher)

    def test_stores_the_session_instance(self):
        assert self.session is self.vcr.session

    def test_replaces_all_adapters(self):
        mount_point = 'fake_protocol://'
        s = Session()
        s.mount(mount_point, HTTPAdapter())
        with Betamax(s):
            adapter = s.adapters.get(mount_point)
            assert adapter is not None
            assert isinstance(adapter, BetamaxAdapter)

########NEW FILE########
__FILENAME__ = test_cassette
import email
import os
import unittest
from datetime import datetime

from betamax import cassette
from betamax import serializers
from betamax.cassette import util
from requests.models import Response, Request
from requests.packages import urllib3
from requests.structures import CaseInsensitiveDict


def decode(s):
    if hasattr(s, 'decode'):
        return s.decode()
    return s


class TestSerializer(serializers.BaseSerializer):
    name = 'test'

    @staticmethod
    def generate_cassette_name(cassette_library_dir, cassette_name):
        return 'test_cassette.test'

    def on_init(self):
        self.serialize_calls = []
        self.deserialize_calls = []

    def serialize(self, data):
        self.serialize_calls.append(data)
        return ''

    def deserialize(self, data):
        self.deserialize_calls.append(data)
        return {}


class TestSerialization(unittest.TestCase):

    """Unittests for the serialization and deserialization functions.

    This tests:

        - deserialize_prepared_request
        - deserialize_response
        - serialize_prepared_request
        - serialize_response

    """

    def test_serialize_response(self):
        r = Response()
        r.status_code = 200
        r.reason = 'OK'
        r.encoding = 'utf-8'
        r.headers = CaseInsensitiveDict()
        r.url = 'http://example.com'
        util.add_urllib3_response({
            'body': {
                'string': decode('foo'),
                'encoding': 'utf-8'
            }
        }, r)
        serialized = util.serialize_response(r, False)
        assert serialized is not None
        assert serialized != {}
        assert serialized['body']['encoding'] == 'utf-8'
        assert serialized['body']['string'] == 'foo'
        assert serialized['headers'] == {}
        assert serialized['url'] == 'http://example.com'
        assert serialized['status'] == {'code': 200, 'message': 'OK'}

    def test_deserialize_response_old(self):
        """For the previous version of Betamax and backwards compatibility."""
        s = {
            'body': {
                'string': decode('foo'),
                'encoding': 'utf-8'
            },
            'headers': {
                'Content-Type': decode('application/json')
            },
            'url': 'http://example.com/',
            'status_code': 200,
            'recorded_at': '2013-08-31T00:00:01'
        }
        r = util.deserialize_response(s)
        assert r.content == b'foo'
        assert r.encoding == 'utf-8'
        assert r.headers == {'Content-Type': 'application/json'}
        assert r.url == 'http://example.com/'
        assert r.status_code == 200

    def test_deserialize_response_new(self):
        """This adheres to the correct cassette specification."""
        s = {
            'body': {
                'string': decode('foo'),
                'encoding': 'utf-8'
            },
            'headers': {
                'Content-Type': [decode('application/json')]
            },
            'url': 'http://example.com/',
            'status': {'code': 200, 'message': 'OK'},
            'recorded_at': '2013-08-31T00:00:01'
        }
        r = util.deserialize_response(s)
        assert r.content == b'foo'
        assert r.encoding == 'utf-8'
        assert r.headers == {'Content-Type': 'application/json'}
        assert r.url == 'http://example.com/'
        assert r.status_code == 200
        assert r.reason == 'OK'

    def test_serialize_prepared_request(self):
        r = Request()
        r.method = 'GET'
        r.url = 'http://example.com'
        r.headers = {'User-Agent': 'betamax/test header'}
        r.data = {'key': 'value'}
        p = r.prepare()
        serialized = util.serialize_prepared_request(p, False)
        assert serialized is not None
        assert serialized != {}
        assert serialized['method'] == 'GET'
        assert serialized['uri'] == 'http://example.com/'
        assert serialized['headers'] == {
            'Content-Length': ['9'],
            'Content-Type': ['application/x-www-form-urlencoded'],
            'User-Agent': ['betamax/test header'],
        }
        assert serialized['body']['string'] == 'key=value'

    def test_deserialize_prepared_request(self):
        s = {
            'body': 'key=value',
            'headers': {
                'User-Agent': 'betamax/test header',
            },
            'method': 'GET',
            'uri': 'http://example.com/',
        }
        p = util.deserialize_prepared_request(s)
        assert p.body == 'key=value'
        assert p.headers == CaseInsensitiveDict(
            {'User-Agent': 'betamax/test header'}
        )
        assert p.method == 'GET'
        assert p.url == 'http://example.com/'

    def test_from_list_returns_an_element(self):
        a = ['value']
        assert util.from_list(a) == 'value'

    def test_from_list_handles_non_lists(self):
        a = 'value'
        assert util.from_list(a) == 'value'

    def test_add_urllib3_response(self):
        r = Response()
        r.status_code = 200
        r.headers = {}
        util.add_urllib3_response({
            'body': {
                'string': decode('foo'),
                'encoding': 'utf-8'
            }
        }, r)
        assert isinstance(r.raw, urllib3.response.HTTPResponse)
        assert r.content == b'foo'
        assert isinstance(r.raw._original_response, cassette.MockHTTPResponse)


class TestCassette(unittest.TestCase):
    cassette_name = 'test_cassette'

    def setUp(self):
        # Make a new serializer to test with
        self.test_serializer = TestSerializer()
        serializers.serializer_registry['test'] = self.test_serializer

        # Instantiate the cassette to test with
        self.cassette = cassette.Cassette(
            TestCassette.cassette_name,
            'test',
            record_mode='once'
        )

        # Create a new object to serialize
        r = Response()
        r.status_code = 200
        r.reason = 'OK'
        r.encoding = 'utf-8'
        r.headers = CaseInsensitiveDict({'Content-Type': decode('foo')})
        r.url = 'http://example.com'
        util.add_urllib3_response({
            'body': {
                'string': decode('foo'),
                'encoding': 'utf-8'
            }
        }, r)
        self.response = r

        # Create an associated request
        r = Request()
        r.method = 'GET'
        r.url = 'http://example.com'
        r.headers = {}
        r.data = {'key': 'value'}
        self.response.request = r.prepare()
        self.response.request.headers.update(
            {'User-Agent': 'betamax/test header'}
        )

        # Expected serialized cassette data.
        self.json = {
            'request': {
                'body': {
                    'encoding': 'utf-8',
                    'string': 'key=value',
                },
                'headers': {
                    'User-Agent': ['betamax/test header'],
                    'Content-Length': ['9'],
                    'Content-Type': ['application/x-www-form-urlencoded'],
                },
                'method': 'GET',
                'uri': 'http://example.com/',
            },
            'response': {
                'body': {
                    'string': decode('foo'),
                    'encoding': 'utf-8',
                },
                'headers': {'Content-Type': [decode('foo')]},
                'status': {'code': 200, 'message': 'OK'},
                'url': 'http://example.com',
            },
            'recorded_at': '2013-08-31T00:00:00',
        }
        self.date = datetime(2013, 8, 31)
        self.cassette.save_interaction(self.response, self.response.request)
        self.interaction = self.cassette.interactions[0]
        self.interaction.recorded_at = self.date

    def tearDown(self):
        try:
            self.cassette.eject()
        except:
            pass
        if os.path.exists(TestCassette.cassette_name):
            os.unlink(TestCassette.cassette_name)

    def test_serialize_interaction(self):
        serialized = self.interaction.json
        assert serialized['request'] == self.json['request']
        assert serialized['response'] == self.json['response']
        assert serialized.get('recorded_at') is not None

    def test_holds_interactions(self):
        assert isinstance(self.cassette.interactions, list)
        assert self.cassette.interactions != []
        assert self.interaction in self.cassette.interactions

    def test_find_match(self):
        self.cassette.match_options = set(['uri', 'method'])
        i = self.cassette.find_match(self.response.request)
        assert i is not None
        assert self.interaction is i

    def test_eject(self):
        serializer = self.test_serializer
        self.cassette.eject()
        assert serializer.serialize_calls == [
            {'http_interactions': [self.cassette.interactions[0].json],
             'recorded_with': 'betamax/{version}'}
            ]

    def test_earliest_recorded_date(self):
        assert self.interaction.recorded_at is not None
        assert self.cassette.earliest_recorded_date is not None


class TestInteraction(unittest.TestCase):
    def setUp(self):
        self.request = {
            'body': {
                'string': 'key=value&key2=secret_value',
                'encoding': 'utf-8'
            },
            'headers': {
                'User-Agent': ['betamax/test header'],
                'Content-Length': ['9'],
                'Content-Type': ['application/x-www-form-urlencoded'],
                'Authorization': ['123456789abcdef'],
                },
            'method': 'GET',
            'uri': 'http://example.com/',
        }
        self.response = {
            'body': {
                'string': decode('foo'),
                'encoding': 'utf-8'
            },
            'headers': {
                'Content-Type': [decode('foo')],
                'Set-Cookie': ['cookie_name=cookie_value']
            },
            'status_code': 200,
            'url': 'http://example.com',
        }
        self.json = {
            'request': self.request,
            'response': self.response,
            'recorded_at': '2013-08-31T00:00:00',
        }
        self.interaction = cassette.Interaction(self.json)
        self.date = datetime(2013, 8, 31)

    def test_as_response(self):
        r = self.interaction.as_response()
        assert isinstance(r, Response)

    def test_deserialized_response(self):
        def check_uri(attr):
            # Necessary since PreparedRequests do not have a uri attr
            if attr == 'uri':
                return 'url'
            return attr
        r = self.interaction.as_response()
        for attr in ['status_code', 'url']:
            assert self.response[attr] == decode(getattr(r, attr))

        headers = dict((k, v[0]) for k, v in self.response['headers'].items())
        assert headers == r.headers

        assert self.response['body']['string'] == decode(r.content)
        actual_req = r.request
        expected_req = self.request
        for attr in ['method', 'uri']:
            assert expected_req[attr] == getattr(actual_req, check_uri(attr))

        assert self.request['body']['string'] == decode(actual_req.body)
        headers = dict((k, v[0]) for k, v in expected_req['headers'].items())
        assert headers == actual_req.headers
        assert self.date == self.interaction.recorded_at

    def test_match(self):
        matchers = [lambda x: True, lambda x: False, lambda x: True]
        assert self.interaction.match(matchers) is False
        matchers[1] = lambda x: True
        assert self.interaction.match(matchers) is True

    def test_replace(self):
        self.interaction.replace('123456789abcdef', '<AUTH_TOKEN>')
        self.interaction.replace('cookie_value', '<COOKIE_VALUE>')
        self.interaction.replace('secret_value', '<SECRET_VALUE>')
        self.interaction.replace('foo', '<FOO>')
        self.interaction.replace('http://example.com', '<EXAMPLE_URI>')

        header = self.interaction.json['request']['headers']['Authorization']
        assert header == '<AUTH_TOKEN>'
        header = self.interaction.json['response']['headers']['Set-Cookie']
        assert header == 'cookie_name=<COOKIE_VALUE>'
        body = self.interaction.json['request']['body']['string']
        assert body == 'key=value&key2=<SECRET_VALUE>'
        body = self.interaction.json['response']['body']
        assert body == {'encoding': 'utf-8', 'string': '<FOO>'}
        uri = self.interaction.json['request']['uri']
        assert uri == '<EXAMPLE_URI>/'
        uri = self.interaction.json['response']['url']
        assert uri == '<EXAMPLE_URI>'

    def test_replace_in_headers(self):
        self.interaction.replace_in_headers('123456789abcdef', '<AUTH_TOKEN>')
        self.interaction.replace_in_headers('cookie_value', '<COOKIE_VALUE>')
        header = self.interaction.json['request']['headers']['Authorization']
        assert header == '<AUTH_TOKEN>'
        header = self.interaction.json['response']['headers']['Set-Cookie']
        assert header == 'cookie_name=<COOKIE_VALUE>'

    def test_replace_in_body(self):
        self.interaction.replace_in_body('secret_value', '<SECRET_VALUE>')
        self.interaction.replace_in_body('foo', '<FOO>')
        body = self.interaction.json['request']['body']['string']
        assert body == 'key=value&key2=<SECRET_VALUE>'
        body = self.interaction.json['response']['body']
        assert body == {'encoding': 'utf-8', 'string': '<FOO>'}

    def test_replace_in_uri(self):
        self.interaction.replace_in_uri('http://example.com', '<EXAMPLE_URI>')
        uri = self.interaction.json['request']['uri']
        assert uri == '<EXAMPLE_URI>/'
        uri = self.interaction.json['response']['url']
        assert uri == '<EXAMPLE_URI>'


class TestMockHTTPResponse(unittest.TestCase):
    def setUp(self):
        self.resp = cassette.MockHTTPResponse({
            decode('Header'): decode('value')
        })

    def test_isclosed(self):
        assert self.resp.isclosed() is False

    def test_is_Message(self):
        assert isinstance(self.resp.msg, email.message.Message)

########NEW FILE########
__FILENAME__ = test_configure
import copy
import unittest

from betamax.configure import Configuration
from betamax.cassette import Cassette


class TestConfiguration(unittest.TestCase):
    def setUp(self):
        self.cassette_options = copy.deepcopy(
            Cassette.default_cassette_options
            )
        self.cassette_dir = Configuration.CASSETTE_LIBRARY_DIR

    def tearDown(self):
        Cassette.default_cassette_options = self.cassette_options
        Configuration.CASSETTE_LIBRARY_DIR = self.cassette_dir

    def test_acts_as_pass_through(self):
        c = Configuration()
        c.default_cassette_options['foo'] = 'bar'
        assert 'foo' in Cassette.default_cassette_options
        assert Cassette.default_cassette_options.get('foo') == 'bar'

    def test_sets_cassette_library(self):
        c = Configuration()
        c.cassette_library_dir = 'foo'
        assert Configuration.CASSETTE_LIBRARY_DIR == 'foo'

    def test_is_a_context_manager(self):
        with Configuration() as c:
            assert isinstance(c, Configuration)

    def test_allows_registration_of_placeholders(self):
        opts = copy.deepcopy(Cassette.default_cassette_options)
        c = Configuration()

        c.define_cassette_placeholder('<TEST>', 'test')
        assert opts != Cassette.default_cassette_options
        placeholders = Cassette.default_cassette_options['placeholders']
        assert placeholders[0]['placeholder'] == '<TEST>'
        assert placeholders[0]['replace'] == 'test'

########NEW FILE########
__FILENAME__ = test_matchers
import unittest

from requests import PreparedRequest
from betamax import matchers


class TestMatchers(unittest.TestCase):
    def setUp(self):
        self.alt_url = ('http://example.com/path/to/end/point?query=string'
                        '&foo=bar')
        self.p = PreparedRequest()
        self.p.body = 'Foo bar'
        self.p.headers = {'User-Agent': 'betamax/test'}
        self.p.url = 'http://example.com/path/to/end/point?query=string'
        self.p.method = 'GET'

    def test_matcher_registry_has_body_matcher(self):
        assert 'body' in matchers.matcher_registry

    def test_matcher_registry_has_digest_auth_matcher(self):
        assert 'digest-auth' in matchers.matcher_registry

    def test_matcher_registry_has_headers_matcher(self):
        assert 'headers' in matchers.matcher_registry

    def test_matcher_registry_has_host_matcher(self):
        assert 'host' in matchers.matcher_registry

    def test_matcher_registry_has_method_matcher(self):
        assert 'method' in matchers.matcher_registry

    def test_matcher_registry_has_path_matcher(self):
        assert 'path' in matchers.matcher_registry

    def test_matcher_registry_has_query_matcher(self):
        assert 'query' in matchers.matcher_registry

    def test_matcher_registry_has_uri_matcher(self):
        assert 'uri' in matchers.matcher_registry

    def test_body_matcher(self):
        match = matchers.matcher_registry['body'].match
        assert match(self.p, {'body': 'Foo bar'})
        assert match(self.p, {'body': ''}) is False

    def test_digest_matcher(self):
        match = matchers.matcher_registry['digest-auth'].match
        assert match(self.p, {'headers': {}})
        saved_auth = (
            'Digest username="user", realm="realm", nonce="nonce", uri="/", '
            'response="r", opaque="o", qop="auth", nc=00000001, cnonce="c"'
            )
        self.p.headers['Authorization'] = saved_auth
        assert match(self.p, {'headers': {}}) is False
        assert match(self.p, {'headers': {'Authorization': saved_auth}})
        new_auth = (
            'Digest username="user", realm="realm", nonce="nonce", uri="/", '
            'response="e", opaque="o", qop="auth", nc=00000001, cnonce="n"'
            )
        assert match(self.p, {'headers': {'Authorization': new_auth}})
        new_auth = (
            'Digest username="u", realm="realm", nonce="nonce", uri="/", '
            'response="e", opaque="o", qop="auth", nc=00000001, cnonce="n"'
            )
        assert match(self.p, {'headers': {'Authorization': new_auth}}) is False

    def test_headers_matcher(self):
        match = matchers.matcher_registry['headers'].match
        assert match(self.p, {'headers': {'User-Agent': 'betamax/test'}})
        assert match(self.p, {'headers': {'X-Sha': '6bbde0af'}}) is False

    def test_host_matcher(self):
        match = matchers.matcher_registry['host'].match
        assert match(self.p, {'uri': 'http://example.com'})
        assert match(self.p, {'uri': 'https://example.com'})
        assert match(self.p, {'uri': 'https://example.com/path'})
        assert match(self.p, {'uri': 'https://example2.com'}) is False

    def test_method_matcher(self):
        match = matchers.matcher_registry['method'].match
        assert match(self.p, {'method': 'GET'})
        assert match(self.p, {'method': 'POST'}) is False

    def test_path_matcher(self):
        match = matchers.matcher_registry['path'].match
        assert match(self.p, {'uri': 'http://example.com/path/to/end/point'})
        assert match(self.p,
                     {'uri': 'http://example.com:8000/path/to/end/point'})
        assert match(self.p,
                     {'uri': 'http://example.com:8000/path/to/end/'}) is False

    def test_query_matcher(self):
        match = matchers.matcher_registry['query'].match
        assert match(
            self.p,
            {'uri': 'http://example.com/path/to/end/point?query=string'}
        )
        assert match(
            self.p,
            {'uri': 'http://example.com/?query=string'}
        )
        self.p.url = self.alt_url
        assert match(
            self.p,
            {'uri': self.alt_url}
        )
        # Regression test (order independence)
        assert match(
            self.p,
            {'uri': 'http://example.com/?foo=bar&query=string'}
        )
        # Regression test (no query issue)
        assert match(self.p, {'uri': 'http://example.com'}) is False

    def test_uri_matcher(self):
        match = matchers.matcher_registry['uri'].match
        assert match(
            self.p,
            {'uri': 'http://example.com/path/to/end/point?query=string'}
        )
        assert match(self.p, {'uri': 'http://example.com'}) is False

    def test_uri_matcher_handles_query_strings(self):
        match = matchers.matcher_registry['uri'].match
        self.p.url = 'http://example.com/path/to?query=string&form=value'
        other_uri = 'http://example.com/path/to?form=value&query=string'
        assert match(self.p, {'uri': other_uri}) is True


class TestBaseMatcher(unittest.TestCase):
    def setUp(self):
        class Matcher(matchers.BaseMatcher):
            pass
        self.Matcher = Matcher

    def test_requires_name(self):
        self.assertRaises(ValueError, self.Matcher)

    def test_requires_you_overload_match(self):
        self.Matcher.name = 'test'
        m = self.Matcher()
        self.assertRaises(NotImplementedError, m.match, None, None)

########NEW FILE########
__FILENAME__ = test_options
import unittest
from itertools import permutations
from betamax.options import Options, validate_record, validate_matchers


class TestValidators(unittest.TestCase):
    def test_validate_record(self):
        for mode in ['once', 'none', 'all', 'new_episodes']:
            assert validate_record(mode) is True

    def test_validate_matchers(self):
        matchers = ['method', 'uri', 'query', 'host', 'body']
        for i in range(1, len(matchers)):
            for l in permutations(matchers, i):
                assert validate_matchers(l) is True

        matchers.append('foobar')
        assert validate_matchers(matchers) is False


class TestOptions(unittest.TestCase):
    def setUp(self):
        self.data = {
            're_record_interval': 10000,
            'match_requests_on': ['method'],
            'serialize': 'json'
        }
        self.options = Options(self.data)

    def test_data_is_valid(self):
        for key in self.data:
            assert key in self.options

    def test_invalid_data_is_removed(self):
        data = self.data.copy()
        data['fake'] = 'value'
        options = Options(data)

        for key in self.data:
            assert key in options

        assert 'fake' not in options

    def test_values_are_validated(self):
        assert self.options['re_record_interval'] == 10000
        assert self.options['match_requests_on'] == ['method']

        data = self.data.copy()
        data['match_requests_on'] = ['foo', 'bar', 'bogus']
        options = Options(data)
        assert options['match_requests_on'] == ['method', 'uri']

########NEW FILE########
__FILENAME__ = test_recorder
import unittest

from betamax import matchers, serializers
from betamax.adapter import BetamaxAdapter
from betamax.cassette import Cassette
from betamax.recorder import Betamax
from requests import Session
from requests.adapters import HTTPAdapter


class TestBetamax(unittest.TestCase):
    def setUp(self):
        self.session = Session()
        self.vcr = Betamax(self.session)

    def test_initialization_does_not_alter_the_session(self):
        for v in self.session.adapters.values():
            assert not isinstance(v, BetamaxAdapter)
            assert isinstance(v, HTTPAdapter)

    def test_entering_context_alters_adapters(self):
        with self.vcr:
            for v in self.session.adapters.values():
                assert isinstance(v, BetamaxAdapter)

    def test_exiting_resets_the_adapters(self):
        with self.vcr:
            pass
        for v in self.session.adapters.values():
            assert not isinstance(v, BetamaxAdapter)

    def test_current_cassette(self):
        assert self.vcr.current_cassette is None
        self.vcr.use_cassette('test')
        assert isinstance(self.vcr.current_cassette, Cassette)

    def test_use_cassette_returns_cassette_object(self):
        assert self.vcr.use_cassette('test') is self.vcr

    def test_register_request_matcher(self):
        class FakeMatcher(object):
            name = 'fake_matcher'

        Betamax.register_request_matcher(FakeMatcher)
        assert 'fake_matcher' in matchers.matcher_registry
        assert isinstance(matchers.matcher_registry['fake_matcher'],
                          FakeMatcher)

    def test_register_serializer(self):
        class FakeSerializer(object):
            name = 'fake_serializer'

        Betamax.register_serializer(FakeSerializer)
        assert 'fake_serializer' in serializers.serializer_registry
        assert isinstance(serializers.serializer_registry['fake_serializer'],
                          FakeSerializer)

    def test_stores_the_session_instance(self):
        assert self.session is self.vcr.session

########NEW FILE########
__FILENAME__ = test_serializers
import pytest
import unittest

from betamax.serializers import BaseSerializer, JSONSerializer


class TestJSONSerializer(unittest.TestCase):
    def setUp(self):
        self.cassette_dir = 'fake_dir'
        self.cassette_name = 'cassette_name'

    def test_generate_cassette_name(self):
        assert ('fake_dir/cassette_name.json' ==
                JSONSerializer.generate_cassette_name(self.cassette_dir,
                                                      self.cassette_name))

    def test_generate_cassette_name_with_instance(self):
        serializer = JSONSerializer()
        assert ('fake_dir/cassette_name.json' ==
                serializer.generate_cassette_name(self.cassette_dir,
                                                  self.cassette_name))


class TestSerializer(BaseSerializer):
    name = 'test'


class TestBaseSerializer(unittest.TestCase):
    def test_serialize_is_an_interface(self):
        serializer = TestSerializer()
        with pytest.raises(NotImplementedError):
            serializer.serialize({})

    def test_deserialize_is_an_interface(self):
        serializer = TestSerializer()
        with pytest.raises(NotImplementedError):
            serializer.deserialize('path')

    def test_requires_a_name(self):
        with pytest.raises(ValueError):
            BaseSerializer()

########NEW FILE########
