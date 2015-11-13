__FILENAME__ = helpers
import gevent
import subprocess


def subprocess_call_background(*args, **kwargs):
    p = subprocess.Popen(*args, **kwargs)
    gevent.sleep(0)
    return p.wait()


def subprocess_check_output_background(*args, **kwargs):
    p = subprocess.Popen(*args, stdout=subprocess.PIPE, **kwargs)
    gevent.sleep(0)
    return p.communicate()[0]

########NEW FILE########
__FILENAME__ = http
import re
import json
import types

from socketio.namespace import BaseNamespace
from socketio.mixins import RoomsMixin, BroadcastMixin

from ajenti.api import BasePlugin, interface


def url(pattern):
    """
    Exposes the decorated method of your :class:`HttpPlugin` via HTTP

    :param pattern: URL regex (no ``^`` and ``$`` required)
    :type  pattern: str
    :rtype: function

        Named capture groups will be fed to function as ``**kwargs``

    """

    def decorator(f):
        f._url_pattern = re.compile('^%s$' % pattern)
        return f
    return decorator


@interface
class HttpPlugin (object):
    """
    A base plugin class for HTTP request handling::

        @plugin
        class TerminalHttp (BasePlugin, HttpPlugin):
            @url('/ajenti:terminal/(?P<id>\d+)')
            def get_page(self, context, id):
                if context.session.identity is None:
                    context.respond_redirect('/')
                context.add_header('Content-Type', 'text/html')
                context.respond_ok()
                return self.open_content('static/index.html').read()

    """

    def handle(self, context):
        """
        Finds and executes the handler for given request context (handlers are methods decorated with :func:`url` )

        :param context: HTTP context
        :type  context: :class:`ajenti.http.HttpContext`
        """

        for name, method in self.__class__.__dict__.iteritems():
            if hasattr(method, '_url_pattern'):
                method = getattr(self, name)
                match = method._url_pattern.match(context.path)
                if match:
                    context.route_data = match.groupdict()
                    data = method(context, **context.route_data)
                    if type(data) is types.GeneratorType:
                        return data
                    else:
                        return [data]


@interface
class SocketPlugin (BasePlugin, BaseNamespace, RoomsMixin, BroadcastMixin):
    """
    A base class for a Socket.IO endpoint::

        @plugin
        class TerminalSocket (SocketPlugin):
            name = '/terminal'

            def on_message(self, message):
                if message['type'] == 'select':
                    self.id = int(message['tid'])
                    self.terminal = self.context.session.terminals[self.id]
                    self.send_data(self.terminal.protocol.history())
                    self.spawn(self.worker)
                if message['type'] == 'key':
                    ch = b64decode(message['key'])
                    self.terminal.write(ch)

            ...
    """

    name = None
    """ Endpoint ID """

    def __init__(self, *args, **kwargs):
        if self.name is None:
            raise Exception('Socket endpoint name is not set')
        BaseNamespace.__init__(self, *args, **kwargs)

    def recv_connect(self):
        """ Internal """
        if self.request.session.identity is None:
            self.emit('auth-error', '')
            return

        self.context = self.request.session.appcontext
        self.on_connect()

    def recv_disconnect(self):
        """ Internal """
        if self.request.session.identity is None:
            return

        self.on_disconnect()
        self.disconnect(silent=True)

    def recv_message(self, message):
        """ Internal """
        if self.request.session.identity is None:
            return

        self.request.session.touch()
        self.on_message(json.loads(message))

    def on_connect(self):
        """ Called when a socket is connected """

    def on_disconnect(self):
        """ Called when a socket disconnects """

    def on_message(self, message):
        """
        Called when a message from browser arrives

        :param message: a message object (parsed JSON)
        :type  message: str
        """

########NEW FILE########
__FILENAME__ = sensors
import time

from ajenti.api import *


@interface
@persistent
class Sensor (object):
    """
    Base class for a Sensor. Sensors measure system status parameters and can be queried from other plugins.
    """
    id = None
    timeout = 0

    def init(self):
        self.cache = {}
        self.last_measurement = {}

    @staticmethod
    def find(id):
        """
        Returns a Sensor by name

        :param id: sensor ID
        :type  id: str
        :rtype: :class:`Sensor`, None
        """
        for cls in Sensor.get_classes():
            if cls.id == id:
                return cls.get()
        else:
            return None

    def value(self, variant=None):
        """
        Returns sensor's measurement for a specific `variant`. Sensors can have multiple variants; for example, disk usage sensor accepts device name as a variant.

        :param variant: variant to measure
        :type  variant: str, None
        :rtype: int, float, tuple, list, dict, str
        """
        t = time.time()
        if (not variant in self.cache) or (t - self.last_measurement[variant]) > self.timeout:
            self.cache[variant] = self.measure(variant)
            self.last_measurement[variant] = t
        return self.cache[variant]

    def get_variants(self):
        """
        Override this and return a list of available variants.

        :rtype: list
        """
        return [None]

    def measure(self, variant=None):
        """
        Override this and perform the measurement.

        :param variant: variant to measure
        :type  variant: str, None
        :rtype: int, float, tuple, list, dict, str
        """

########NEW FILE########
__FILENAME__ = compat
import logging
import subprocess
import os


# add subprocess.check_output to Python < 2.6
if not hasattr(subprocess, 'check_output'):
    def c_o(*args, **kwargs):
        kwargs['stdout'] = subprocess.PIPE
        popen = subprocess.Popen(*args, **kwargs)
        stdout, stderr = popen.communicate()
        return stdout
    subprocess.check_output = c_o


old_Popen = subprocess.Popen.__init__


def Popen(*args, **kwargs):
    logging.debug('Popen: %s' % (args[1],))
    __null = open(os.devnull, 'w')
    return old_Popen(
        stdin=kwargs.pop('stdin', subprocess.PIPE),
        stdout=kwargs.pop('stdout', __null),
        stderr=kwargs.pop('stderr', __null),
        *args, **kwargs)

subprocess.Popen.__init__ = Popen


# fix AttributeError
# a super-rude fix - DummyThread doesn't have a __block so provide an acquired one
import threading


def tbget(self):
    if hasattr(self, '__compat_lock'):
        return self.__compat_lock
    c = threading.Condition()
    c.acquire()
    return c


def tbset(self, l):
    self.__compat_lock = l


def tbdel(self):
    del self.__compat_lock

threading.Thread._Thread__block = property(tbget, tbset, tbdel)


# fix AttributeError("'Event' object has no attribute '_reset_internal_locks'",)
import threading
if not hasattr(threading.Event, '_reset_internal_locks'):
    def r_i_l(self):
        pass
    threading.Event._reset_internal_locks = r_i_l


# suppress Requests logging
logging.getLogger("requests").setLevel(logging.WARNING)

# suppress simplejson
try:
    import simplejson
    _loads = simplejson.loads

    def wrap(fx):
        def f(*args, **kwargs):
            kwargs.pop('use_decimal', None)
            return fx(*args, **kwargs)
        return f

    simplejson.dumps = wrap(simplejson.dumps)
    simplejson.loads = wrap(simplejson.loads)
except:
    pass

########NEW FILE########
__FILENAME__ = cookies
"""Parse, manipulate and render cookies in a convenient way.

Copyright (c) 2011-2013, Sasha Hart.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
__version__ = "1.2.1"
import re
import datetime
import logging
import sys
from unicodedata import normalize
if sys.version_info >= (3, 0, 0):  # pragma: no cover
    from urllib.parse import (
        quote as _default_quote, unquote as _default_unquote)
    basestring = str
    long = int
else:  # pragma: no cover
    from urllib import (
        quote as _default_quote, unquote as _default_unquote)


def _total_seconds(td):
    """Wrapper to work around lack of .total_seconds() method in Python 3.1.
    """
    if hasattr(td, "total_seconds"):
        return td.total_seconds()
    return td.days * 3600 * 24 + td.seconds + td.microseconds / 100000.0

# see test_encoding_assumptions for how these magical safe= parms were figured
# out. the differences are because of what cookie-octet may contain
# vs the more liberal spec for extension-av
default_cookie_quote = lambda item: _default_quote(
    item, safe='!#$%&\'()*+/:<=>?@[]^`{|}~')

default_extension_quote = lambda item: _default_quote(
    item, safe=' !"#$%&\'()*+,/:<=>?@[\\]^`{|}~')

default_unquote = _default_unquote


def _report_invalid_cookie(data):
    "How this module logs a bad cookie when exception suppressed"
    logging.error("invalid Cookie: %r", data)


def _report_unknown_attribute(name):
    "How this module logs an unknown attribute when exception suppressed"
    logging.error("unknown Cookie attribute: %r", name)


def _report_invalid_attribute(name, value, reason):
    "How this module logs a bad attribute when exception suppressed"
    logging.error("invalid Cookie attribute (%s): %r=%r", reason, name, value)


class CookieError(Exception):
    """Base class for this module's exceptions, so you can catch them all if
    you want to.
    """
    def __init__(self):
        Exception.__init__(self)


class InvalidCookieError(CookieError):
    """Raised when attempting to parse or construct a cookie which is
    syntactically invalid (in any way that has possibly serious implications).
    """
    def __init__(self, data=None, message=""):
        CookieError.__init__(self)
        self.data = data
        self.message = message

    def __str__(self):
        return '%r %r' % (self.message, self.data)


class InvalidCookieAttributeError(CookieError):
    """Raised when setting an invalid attribute on a Cookie.
    """
    def __init__(self, name, value, reason=None):
        CookieError.__init__(self)
        self.name = name
        self.value = value
        self.reason = reason

    def __str__(self):
        prefix = ("%s: " % self.reason) if self.reason else ""
        if self.name is None:
            return '%s%r' % (prefix, self.value)
        return '%s%r = %r' % (prefix, self.name, self.value)


class Definitions(object):
    """Namespace to hold definitions used in cookie parsing (mostly pieces of
    regex).

    These are separated out for individual testing against examples and RFC
    grammar, and kept here to avoid cluttering other namespaces.
    """
    # Most of the following are set down or cited in RFC 6265 4.1.1

    # This is the grammar's 'cookie-name' defined as 'token' per RFC 2616 2.2.
    COOKIE_NAME = r"!#$%&'*+\-.0-9A-Z^_`a-z|~"

    # 'cookie-octet' - as used twice in definition of 'cookie-value'
    COOKIE_OCTET = r"\x21\x23-\x2B\--\x3A\x3C-\x5B\]-\x7E"

    # extension-av - also happens to be a superset of cookie-av and path-value
    EXTENSION_AV = """ !"#$%&\\\\'()*+,\-./0-9:<=>?@A-Z[\\]^_`a-z{|}~"""

    # This is for the first pass parse on a Set-Cookie: response header. It
    # includes cookie-value, cookie-pair, set-cookie-string, cookie-av.
    # extension-av is used to extract the chunk containing variable-length,
    # unordered attributes. The second pass then uses ATTR to break out each
    # attribute and extract it appropriately.
    # As compared with the RFC production grammar, it is must more liberal with
    # space characters, in order not to break on data made by barbarians.
    SET_COOKIE_HEADER = """(?x) # Verbose mode
        ^(?:Set-Cookie:[ ]*)?
        (?P<name>[{name}:]+)
        [ ]*=[ ]*

        # Accept anything in quotes - this is not RFC 6265, but might ease
        # working with older code that half-heartedly works with 2965. Accept
        # spaces inside tokens up front, so we can deal with that error one
        # cookie at a time, after this first pass.
        (?P<value>(?:"{value}*")|(?:[{cookie_octet} ]*))
        [ ]*

        # Extract everything up to the end in one chunk, which will be broken
        # down in the second pass. Don't match if there's any unexpected
        # garbage at the end (hence the \Z; $ matches before newline).
        (?P<attrs>(?:;[ ]*[{cookie_av}]+)*)
        """.format(name=COOKIE_NAME, cookie_av=EXTENSION_AV + ";",
                   cookie_octet=COOKIE_OCTET, value="[^;]")

    # Now we specify the individual patterns for the attribute extraction pass
    # of Set-Cookie parsing (mapping to *-av in the RFC grammar). Things which
    # don't match any of these but are in extension-av are simply ignored;
    # anything else should be rejected in the first pass (SET_COOKIE_HEADER).

    # Max-Age attribute. These are digits, they are expressed this way
    # because that is how they are expressed in the RFC.
    MAX_AGE_AV = "Max-Age=(?P<max_age>[\x31-\x39][\x30-\x39]*)"

    # Domain attribute; a label is one part of the domain
    LABEL = '{let_dig}(?:(?:{let_dig_hyp}+)?{let_dig})?'.format(
            let_dig="[A-Za-z0-9]", let_dig_hyp="[0-9A-Za-z\-]")
    DOMAIN = "(?:{label}\.)*(?:{label})".format(label=LABEL)
    # Parse initial period though it's wrong, as RFC 6265 4.1.2.3
    DOMAIN_AV = "Domain=(?P<domain>\.?{domain})".format(domain=DOMAIN)

    # Path attribute. We don't take special care with quotes because
    # they are hardly used, they don't allow invalid characters per RFC 6265,
    # and " is a valid character to occur in a path value anyway.
    PATH_AV = 'Path=(?P<path>[%s]+)' % EXTENSION_AV

    # Expires attribute. This gets big because of date parsing, which needs to
    # support a large range of formats, so it's broken down into pieces.

    # Generate a mapping of months to use in render/parse, to avoid
    # localizations which might be produced by strftime (e.g. %a -> Mayo)
    month_list = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November",
                  "December"]
    month_abbr_list = [item[:3] for item in month_list]
    month_numbers = {}
    for index, name in enumerate(month_list):
        name = name.lower()
        month_numbers[name[:3]] = index + 1
        month_numbers[name] = index + 1
    # Use the same list to create regexps for months.
    MONTH_SHORT = "(?:" + "|".join(item[:3] for item in month_list) + ")"
    MONTH_LONG = "(?:" + "|".join(item for item in month_list) + ")"

    # Same drill with weekdays, for the same reason.
    weekday_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
                    "Saturday", "Sunday"]
    weekday_abbr_list = [item[:3] for item in weekday_list]
    WEEKDAY_SHORT = "(?:" + "|".join(item[:3] for item in weekday_list) + ")"
    WEEKDAY_LONG = "(?:" + "|".join(item for item in weekday_list) + ")"

    # This regexp tries to exclude obvious nonsense in the first pass.
    DAY_OF_MONTH = "(?:[0 ]?[1-9]|[12][0-9]|[3][01])(?!\d)"

    # Here is the overall date format; ~99% of cases fold into one generalized
    # syntax like RFC 1123, and many of the rest use asctime-like formats.
    # (see test_date_formats for a full exegesis)
    DATE = """(?ix) # Case-insensitive mode, verbose mode
        (?:
            (?P<weekday>(?:{wdy}|{weekday}),[ ])?
            (?P<day>{day})
            [ \-]
            (?P<month>{mon}|{month})
            [ \-]
            # This does not support 3-digit years, which are rare and don't
            # seem to have one canonical interpretation.
            (?P<year>(?:\d{{2}}|\d{{4}}))
            [ ]
            # HH:MM[:SS] GMT
            (?P<hour>(?:[ 0][0-9]|[01][0-9]|2[0-3]))
            :(?P<minute>(?:0[0-9]|[1-5][0-9]))
            (?::(?P<second>\d{{2}}))?
            [ ]GMT
        |
            # Support asctime format, e.g. 'Sun Nov  6 08:49:37 1994'
            (?P<weekday2>{wdy})[ ]
            (?P<month2>{mon})[ ]
            (?P<day2>[ ]\d|\d\d)[ ]
            (?P<hour2>\d\d):
            (?P<minute2>\d\d)
            (?::(?P<second2>\d\d)?)[ ]
            (?P<year2>\d\d\d\d)
            (?:[ ]GMT)?  # GMT (Amazon)
        )
    """
    DATE = DATE.format(wdy=WEEKDAY_SHORT, weekday=WEEKDAY_LONG,
                       day=DAY_OF_MONTH, mon=MONTH_SHORT, month=MONTH_LONG)

    EXPIRES_AV = "Expires=(?P<expires>%s)" % DATE

    # Now we're ready to define a regexp which can match any number of attrs
    # in the variable portion of the Set-Cookie header (like the unnamed latter
    # part of set-cookie-string in the grammar). Each regexp of any complexity
    # is split out for testing by itself.
    ATTR = """(?ix)  # Case-insensitive mode, verbose mode
        # Always start with start or semicolon and any number of spaces
        (?:^|;)[ ]*(?:
            # Big disjunction of attribute patterns (*_AV), with named capture
            # groups to extract everything in one pass. Anything unrecognized
            # goes in the 'unrecognized' capture group for reporting.
            {expires}
            |{max_age}
            |{domain}
            |{path}
            |(?P<secure>Secure=?)
            |(?P<httponly>HttpOnly=?)
            |Version=(?P<version>[{stuff}]+)
            |Comment=(?P<comment>[{stuff}]+)
            |(?P<unrecognized>[{stuff}]+)
        )
        # End with any number of spaces not matched by the preceding (up to the
        # next semicolon) - but do not capture these.
        [ ]*
    """.format(expires=EXPIRES_AV, max_age=MAX_AGE_AV, domain=DOMAIN_AV,
               path=PATH_AV, stuff=EXTENSION_AV)

    # For request data ("Cookie: ") parsing, with finditer cf. RFC 6265 4.2.1
    COOKIE = """(?x) # Verbose mode
        (?: # Either something close to valid...

            # Match starts at start of string, or at separator.
            # Split on comma for the sake of legacy code (RFC 2109/2965),
            # and since it only breaks when invalid commas are put in values.
            # see http://bugs.python.org/issue1210326
            (?:^Cookie:|^|;|,)

            # 1 or more valid token characters making up the name (captured)
            # with colon added to accommodate users of some old Java apps, etc.
            [ ]*
            (?P<name>[{name}:]+)
            [ ]*
            =
            [ ]*

            # While 6265 provides only for cookie-octet, this allows just about
            # anything in quotes (like in RFC 2616); people stuck on RFC
            # 2109/2965 will expect it to work this way. The non-quoted token
            # allows interior spaces ('\x20'), which is not valid. In both
            # cases, the decision of whether to allow these is downstream.
            (?P<value>
                ["][^\00-\31"]*["]
                |
                [{value}]
                |
                [{value}][{value} ]*[{value}]+
                |
                )

        # ... Or something way off-spec - extract to report and move on
        |
            (?P<invalid>[^;]+)
        )
        # Trailing spaces after value
        [ ]*
        # Must end with ; or be at end of string (don't consume this though,
        # so use the lookahead assertion ?=
        (?=;|\Z)
    """.format(name=COOKIE_NAME, value=COOKIE_OCTET)

    # Precompile externally useful definitions into re objects.
    COOKIE_NAME_RE = re.compile("^([%s:]+)\Z" % COOKIE_NAME)
    COOKIE_RE = re.compile(COOKIE)
    SET_COOKIE_HEADER_RE = re.compile(SET_COOKIE_HEADER)
    ATTR_RE = re.compile(ATTR)
    DATE_RE = re.compile(DATE)
    DOMAIN_RE = re.compile(DOMAIN)
    PATH_RE = re.compile('^([%s]+)\Z' % EXTENSION_AV)
    EOL = re.compile("(?:\r\n|\n)")


def strip_spaces_and_quotes(value):
    """Remove invalid whitespace and/or single pair of dquotes and return None
    for empty strings.

    Used to prepare cookie values, path, and domain attributes in a way which
    tolerates simple formatting mistakes and standards variations.
    """
    value = value.strip() if value else ""
    if value and len(value) > 1 and (value[0] == value[-1] == '"'):
        value = value[1:-1]
    if not value:
        value = ""
    return value


def parse_string(data, unquote=default_unquote):
    """Decode URL-encoded strings to UTF-8 containing the escaped chars.
    """
    if data is None:
        return None

    # We'll soon need to unquote to recover our UTF-8 data.
    # In Python 2, unquote crashes on chars beyond ASCII. So encode functions
    # had better not include anything beyond ASCII in data.
    # In Python 3, unquote crashes on bytes objects, requiring conversion to
    # str objects (unicode) using decode().
    # But in Python 2, the same decode causes unquote to butcher the data.
    # So in that case, just leave the bytes.
    if isinstance(data, bytes):
        if sys.version_info > (3, 0, 0):  # pragma: no cover
            data = data.decode('ascii')
    # Recover URL encoded data
    unquoted = unquote(data)
    # Without this step, Python 2 may have good URL decoded *bytes*,
    # which will therefore not normalize as unicode and not compare to
    # the original.
    if isinstance(unquoted, bytes):
        try:
            unquoted = unquoted.decode('utf-8')
        except:
            unquoted = '--invalid--'
    return unquoted


def parse_date(value):
    """Parse an RFC 1123 or asctime-like format date string to produce
    a Python datetime object (without a timezone).
    """
    # Do the regex magic; also enforces 2 or 4 digit years
    match = Definitions.DATE_RE.match(value) if value else None
    if not match:
        return None
    # We're going to extract and prepare captured data in 'data'.
    data = {}
    captured = match.groupdict()
    fields = ['year', 'month', 'day', 'hour', 'minute', 'second']
    # If we matched on the RFC 1123 family format
    if captured['year']:
        for field in fields:
            data[field] = captured[field]
    # If we matched on the asctime format, use year2 etc.
    else:
        for field in fields:
            data[field] = captured[field + "2"]
    year = data['year']
    # Interpret lame 2-digit years - base the cutoff on UNIX epoch, in case
    # someone sets a '70' cookie meaning 'distant past'. This won't break for
    # 58 years and people who use 2-digit years are asking for it anyway.
    if len(year) == 2:
        if int(year) < 70:
            year = "20" + year
        else:
            year = "19" + year
    year = int(year)
    # Clamp to [1900, 9999]: strftime has min 1900, datetime has max 9999
    data['year'] = max(1900, min(year, 9999))
    # Other things which are numbers should convert to integer
    for field in ['day', 'hour', 'minute', 'second']:
        if data[field] is None:
            data[field] = 0
        data[field] = int(data[field])
    # Look up the number datetime needs for the named month
    data['month'] = Definitions.month_numbers[data['month'].lower()]
    return datetime.datetime(**data)


def parse_domain(value):
    """Parse and validate an incoming Domain attribute value.
    """
    value = strip_spaces_and_quotes(value)
    # Strip/ignore invalid leading period as in RFC 5.2.3
    if value and value[0] == '.':
        value = value[1:]
    if value:
        assert valid_domain(value)
    return value


def parse_path(value):
    """Parse and validate an incoming Path attribute value.
    """
    value = strip_spaces_and_quotes(value)
    assert valid_path(value)
    return value


def parse_value(value, allow_spaces=True, unquote=default_unquote):
    "Process a cookie value"
    if value is None:
        return None
    value = strip_spaces_and_quotes(value)
    value = parse_string(value, unquote=unquote)
    if not allow_spaces:
        assert ' ' not in value
    return value


def valid_name(name):
    "Validate a cookie name string"
    if isinstance(name, bytes):
        name = name.decode('ascii')
    if not Definitions.COOKIE_NAME_RE.match(name):
        return False
    # This module doesn't support $identifiers, which are part of an obsolete
    # and highly complex standard which is never used.
    if name[0] == "$":
        return False
    return True


def valid_value(value, quote=default_cookie_quote, unquote=default_unquote):
    """Validate a cookie value string.

    This is generic across quote/unquote functions because it directly verifies
    the encoding round-trip using the specified quote/unquote functions.
    So if you use different quote/unquote functions, use something like this
    as a replacement for valid_value::

        my_valid_value = lambda value: valid_value(value, quote=my_quote,
                                                          unquote=my_unquote)
    """
    if value is None:
        return False

    # Put the value through a round trip with the given quote and unquote
    # functions, so we will know whether data will get lost or not in the event
    # that we don't complain.
    encoded = encode_cookie_value(value, quote=quote)
    decoded = parse_string(encoded, unquote=unquote)

    # If the original string made the round trip, this is a valid value for the
    # given quote and unquote functions. Since the round trip can generate
    # different unicode forms, normalize before comparing, so we can ignore
    # trivial inequalities.
    decoded_normalized = (normalize("NFKD", decoded)
                          if not isinstance(decoded, bytes) else decoded)
    value_normalized = (normalize("NFKD", value)
                        if not isinstance(value, bytes) else value)
    if decoded_normalized == value_normalized:
        return True
    return False


def valid_date(date):
    "Validate an expires datetime object"
    # We want something that acts like a datetime. In particular,
    # strings indicate a failure to parse down to an object and ints are
    # nonstandard and ambiguous at best.
    if not hasattr(date, 'tzinfo'):
        return False
    # Relevant RFCs define UTC as 'close enough' to GMT, and the maximum
    # difference between UTC and GMT is often stated to be less than a second.
    if date.tzinfo is None or _total_seconds(date.utcoffset()) < 1.1:
        return True
    return False


def valid_domain(domain):
    "Validate a cookie domain ASCII string"
    # Using encoding on domain would confuse browsers into not sending cookies.
    # Generate UnicodeDecodeError up front if it can't store as ASCII.
    domain.encode('ascii')
    if domain and domain[0] in '."':
        return False
    # Domains starting with periods are not RFC-valid, but this is very common
    # in existing cookies, so they should still parse with DOMAIN_AV.
    if Definitions.DOMAIN_RE.match(domain):
        return True
    return False


def valid_path(value):
    "Validate a cookie path ASCII string"
    # Generate UnicodeDecodeError if path can't store as ASCII.
    value.encode("ascii")
    # Cookies without leading slash will likely be ignored, raise ASAP.
    if not (value and value[0] == "/"):
        return False
    if not Definitions.PATH_RE.match(value):
        return False
    return True


def valid_max_age(number):
    "Validate a cookie Max-Age"
    if isinstance(number, basestring):
        try:
            number = long(number)
        except (ValueError, TypeError):
            return False
    if number >= 0 and number % 1 == 0:
        return True
    return False


def encode_cookie_value(data, quote=default_cookie_quote):
    """URL-encode strings to make them safe for a cookie value.

    By default this uses urllib quoting, as used in many other cookie
    implementations and in other Python code, instead of an ad hoc escaping
    mechanism which includes backslashes (these also being illegal chars in RFC
    6265).
    """
    if data is None:
        return None

    # encode() to ASCII bytes so quote won't crash on non-ASCII.
    # but doing that to bytes objects is nonsense.
    # On Python 2 encode crashes if s is bytes containing non-ASCII.
    # On Python 3 encode crashes on all byte objects.
    if not isinstance(data, bytes):
        data = data.encode("utf-8")

    # URL encode data so it is safe for cookie value
    quoted = quote(data)

    # Don't force to bytes, so that downstream can use proper string API rather
    # than crippled bytes, and to encourage encoding to be done just once.
    return quoted


def encode_extension_av(data, quote=default_extension_quote):
    """URL-encode strings to make them safe for an extension-av
    (extension attribute value): <any CHAR except CTLs or ";">
    """
    if not data:
        return ''
    return quote(data)


def render_date(date):
    """Render a date (e.g. an Expires value) per RFCs 6265/2616/1123.

    Don't give this localized (timezone-aware) datetimes. If you use them,
    convert them to GMT before passing them to this. There are too many
    conversion corner cases to handle this universally.
    """
    if not date:
        return None
    assert valid_date(date)
    # Avoid %a and %b, which can change with locale, breaking compliance
    weekday = Definitions.weekday_abbr_list[date.weekday()]
    month = Definitions.month_abbr_list[date.month - 1]
    return date.strftime("{day}, %d {month} %Y %H:%M:%S GMT"
                         ).format(day=weekday, month=month)


def _parse_request(header_data, ignore_bad_cookies=False):
    """Turn one or more lines of 'Cookie:' header data into a dict mapping
    cookie names to cookie values (raw strings).
    """
    cookies_dict = {}
    for line in Definitions.EOL.split(header_data.strip()):
        matches = Definitions.COOKIE_RE.finditer(line)
        matches = [item for item in matches]
        for match in matches:
            invalid = match.group('invalid')
            if invalid:
                if not ignore_bad_cookies:
                    raise InvalidCookieError(data=invalid)
                _report_invalid_cookie(invalid)
                continue
            name = match.group('name')
            values = cookies_dict.get(name)
            value = match.group('value').strip('"')
            if values:
                values.append(value)
            else:
                cookies_dict[name] = [value]
        if not matches:
            if not ignore_bad_cookies:
                raise InvalidCookieError(data=line)
            _report_invalid_cookie(line)
    return cookies_dict


def parse_one_response(line, ignore_bad_cookies=False,
                       ignore_bad_attributes=True):
    """Turn one 'Set-Cookie:' line into a dict mapping attribute names to
    attribute values (raw strings).
    """
    cookie_dict = {}
    # Basic validation, extract name/value/attrs-chunk
    match = Definitions.SET_COOKIE_HEADER_RE.match(line)
    if not match:
        if not ignore_bad_cookies:
            raise InvalidCookieError(data=line)
        _report_invalid_cookie(line)
        return None
    cookie_dict.update({
        'name': match.group('name'),
        'value': match.group('value')})
    # Extract individual attrs from the attrs chunk
    for match in Definitions.ATTR_RE.finditer(match.group('attrs')):
        captured = dict((k, v) for (k, v) in match.groupdict().items() if v)
        unrecognized = captured.get('unrecognized', None)
        if unrecognized:
            if not ignore_bad_attributes:
                raise InvalidCookieAttributeError(None, unrecognized,
                                                  "unrecognized")
            _report_unknown_attribute(unrecognized)
            continue
        # for unary flags
        for key in ('secure', 'httponly'):
            if captured.get(key):
                captured[key] = True
        # ignore subcomponents of expires - they're still there to avoid doing
        # two passes
        timekeys = ('weekday', 'month', 'day', 'hour', 'minute', 'second',
                    'year')
        if 'year' in captured:
            for key in timekeys:
                del captured[key]
        elif 'year2' in captured:
            for key in timekeys:
                del captured[key + "2"]
        cookie_dict.update(captured)
    return cookie_dict


def _parse_response(header_data, ignore_bad_cookies=False,
                    ignore_bad_attributes=True):
    """Turn one or more lines of 'Set-Cookie:' header data into a list of dicts
    mapping attribute names to attribute values (as plain strings).
    """
    cookie_dicts = []
    for line in Definitions.EOL.split(header_data.strip()):
        if not line:
            break
        cookie_dict = parse_one_response(
            line, ignore_bad_cookies=ignore_bad_cookies,
            ignore_bad_attributes=ignore_bad_attributes)
        if not cookie_dict:
            continue
        cookie_dicts.append(cookie_dict)
    if not cookie_dicts:
        if not ignore_bad_cookies:
            raise InvalidCookieError(data=header_data)
        _report_invalid_cookie(header_data)
    return cookie_dicts


class Cookie(object):
    """Provide a simple interface for creating, modifying, and rendering
    individual HTTP cookies.

    Cookie attributes are represented as normal Python object attributes.
    Parsing, rendering and validation are reconfigurable per-attribute. The
    default behavior is intended to comply with RFC 6265, URL-encoding illegal
    characters where necessary. For example: the default behavior for the
    Expires attribute is to parse strings as datetimes using parse_date,
    validate that any set value is a datetime, and render the attribute per the
    preferred date format in RFC 1123.
    """
    def __init__(self, name, value, **kwargs):
        # If we don't have or can't set a name value, we don't want to return
        # junk, so we must break control flow. And we don't want to use
        # InvalidCookieAttributeError, because users may want to catch that to
        # suppress all complaining about funky attributes.
        try:
            self.name = name
        except InvalidCookieAttributeError:
            raise InvalidCookieError(message="invalid name for new Cookie")
        self.value = value or ''
        if kwargs:
            self._set_attributes(kwargs, ignore_bad_attributes=False)

    def _set_attributes(self, attrs, ignore_bad_attributes=False):
        for attr_name, attr_value in attrs.items():
            if not attr_name in self.attribute_names:
                if not ignore_bad_attributes:
                    raise InvalidCookieAttributeError(
                        attr_name, attr_value,
                        "unknown cookie attribute '%s'" % attr_name)
                _report_unknown_attribute(attr_name)

            try:
                setattr(self, attr_name, attr_value)
            except InvalidCookieAttributeError as error:
                if not ignore_bad_attributes:
                    raise
                _report_invalid_attribute(attr_name, attr_value, error.reason)
                continue

    @classmethod
    def from_dict(cls, cookie_dict, ignore_bad_attributes=True):
        """Construct a Cookie object from a dict of strings to parse.

        The main difference between this and Cookie(name, value, **kwargs) is
        that the values in the argument to this method are parsed.

        If ignore_bad_attributes=True (default), values which did not parse
        are set to '' in order to avoid passing bad data.
        """
        name = cookie_dict.get('name', None)
        if not name:
            raise InvalidCookieError("Cookie must have name")
        raw_value = cookie_dict.get('value', '')
        # Absence or failure of parser here is fatal; errors in present name
        # and value should be found by Cookie.__init__.
        value = cls.attribute_parsers['value'](raw_value)
        cookie = Cookie(name, value)

        # Parse values from serialized formats into objects
        parsed = {}
        for key, value in cookie_dict.items():
            # Don't want to pass name/value to _set_attributes
            if key in ('name', 'value'):
                continue
            parser = cls.attribute_parsers.get(key)
            if not parser:
                # Don't let totally unknown attributes pass silently
                if not ignore_bad_attributes:
                    raise InvalidCookieAttributeError(
                        key, value, "unknown cookie attribute '%s'" % key)
                _report_unknown_attribute(key)
                continue
            try:
                parsed_value = parser(value)
            except Exception as e:
                reason = "did not parse with %r: %r" % (parser, e)
                if not ignore_bad_attributes:
                    raise InvalidCookieAttributeError(
                        key, value, reason)
                _report_invalid_attribute(key, value, reason)
                parsed_value = ''
            parsed[key] = parsed_value

        # Set the parsed objects (does object validation automatically)
        cookie._set_attributes(parsed, ignore_bad_attributes)
        return cookie

    @classmethod
    def from_string(cls, line, ignore_bad_cookies=False,
                    ignore_bad_attributes=True):
        "Construct a Cookie object from a line of Set-Cookie header data."
        cookie_dict = parse_one_response(
            line, ignore_bad_cookies=ignore_bad_cookies,
            ignore_bad_attributes=ignore_bad_attributes)
        if not cookie_dict:
            return None
        return cls.from_dict(
            cookie_dict, ignore_bad_attributes=ignore_bad_attributes)

    def to_dict(self):
        this_dict = {'name': self.name, 'value': self.value}
        this_dict.update(self.attributes())
        return this_dict

    def validate(self, name, value):
        """Validate a cookie attribute with an appropriate validator.

        The value comes in already parsed (for example, an expires value
        should be a datetime). Called automatically when an attribute
        value is set.
        """
        validator = self.attribute_validators.get(name, None)
        if validator:
            return True if validator(value) else False
        return True

    def __setattr__(self, name, value):
        """Attributes mentioned in attribute_names get validated using
        functions in attribute_validators, raising an exception on failure.
        Others get left alone.
        """
        if name in self.attribute_names or name in ("name", "value"):
            if name == 'name' and not value:
                raise InvalidCookieError(message="Cookies must have names")
            # Ignore None values indicating unset attr. Other invalids should
            # raise error so users of __setattr__ can learn.
            if value is not None:
                if not self.validate(name, value):
                    pass # sorry, nope
                    #raise InvalidCookieAttributeError(
                    #    name, value, "did not validate with " +
                    #    repr(self.attribute_validators.get(name)))
        object.__setattr__(self, name, value)

    def __getattr__(self, name):
        """Provide for acting like everything in attribute_names is
        automatically set to None, rather than having to do so explicitly and
        only at import time.
        """
        if name in self.attribute_names:
            return None
        raise AttributeError(name)

    def attributes(self):
        """Export this cookie's attributes as a dict of encoded values.

        This is an important part of the code for rendering attributes, e.g.
        render_response().
        """
        dictionary = {}
        # Only look for attributes registered in attribute_names.
        for python_attr_name, cookie_attr_name in self.attribute_names.items():
            value = getattr(self, python_attr_name)
            renderer = self.attribute_renderers.get(python_attr_name, None)
            if renderer:
                value = renderer(value)
            # If renderer returns None, or it's just natively none, then the
            # value is suppressed entirely - does not appear in any rendering.
            if not value:
                continue
            dictionary[cookie_attr_name] = value
        return dictionary

    def render_request(self):
        """Render as a string formatted for HTTP request headers
        (simple 'Cookie: ' style).
        """
        # Use whatever renderers are defined for name and value.
        name, value = self.name, self.value
        renderer = self.attribute_renderers.get('name', None)
        if renderer:
            name = renderer(name)
        renderer = self.attribute_renderers.get('value', None)
        if renderer:
            value = renderer(value)
        return ''.join((name, "=", value))

    def render_response(self):
        """Render as a string formatted for HTTP response headers
        (detailed 'Set-Cookie: ' style).
        """
        # Use whatever renderers are defined for name and value.
        # (.attributes() is responsible for all other rendering.)
        name, value = self.name, self.value
        renderer = self.attribute_renderers.get('name', None)
        if renderer:
            name = renderer(name)
        renderer = self.attribute_renderers.get('value', None)
        if renderer:
            value = renderer(value)
        return '; '.join(
            ['{0}={1}'.format(name, value)] +
            [key if isinstance(value, bool) else '='.join((key, value))
             for key, value in self.attributes().items()]
        )

    def __eq__(self, other):
        attrs = ['name', 'value'] + list(self.attribute_names.keys())
        for attr in attrs:
            mine = getattr(self, attr, None)
            his = getattr(other, attr, None)
            if isinstance(mine, bytes):
                mine = mine.decode('utf-8')
            if isinstance(his, bytes):
                his = his.decode('utf-8')
            if mine != his:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    # Add a name and its proper rendering to this dict to register an attribute
    # as exportable. The key is the name of the Cookie object attribute in
    # Python, and it is mapped to the name you want in the output.
    # 'name' and 'value' should not be here.
    attribute_names = {
        'expires':  'Expires',
        'max_age':  'Max-Age',
        'domain':   'Domain',
        'path':     'Path',
        'comment':  'Comment',
        'version':  'Version',
        'secure':   'Secure',
        'httponly': 'HttpOnly',
    }

    # Register single-parameter functions in this dictionary to have them
    # used for encoding outgoing values (e.g. as RFC compliant strings,
    # as base64, encrypted stuff, etc.)
    # These are called by the property generated by cookie_attribute().
    # Usually it would be wise not to define a renderer for name, but it is
    # supported in case there is ever a real need.
    attribute_renderers = {
        'value':    encode_cookie_value,
        'expires':  render_date,
        'max_age':  lambda item: str(item) if item is not None else None,
        'secure':   lambda item: True if item else False,
        'httponly': lambda item: True if item else False,
        'comment':  encode_extension_av,
        'version':  lambda item: (str(item) if isinstance(item, int)
                                  else encode_extension_av(item)),
    }

    # Register single-parameter functions in this dictionary to have them used
    # for decoding incoming values for use in the Python API (e.g. into nice
    # objects, numbers, unicode strings, etc.)
    # These are called by the property generated by cookie_attribute().
    attribute_parsers = {
        'value':    parse_value,
        'expires':  parse_date,
        'domain':   parse_domain,
        'path':     parse_path,
        'max_age':  lambda item: long(strip_spaces_and_quotes(item)),
        'comment':  parse_string,
        'version':  lambda item: int(strip_spaces_and_quotes(item)),
        'secure':   lambda item: True if item else False,
        'httponly': lambda item: True if item else False,
    }

    # Register single-parameter functions which return a true value for
    # acceptable values, and a false value for unacceptable ones. An
    # attribute's validator is run after it is parsed or when it is directly
    # set, and InvalidCookieAttribute is raised if validation fails (and the
    # validator doesn't raise a different exception prior)
    attribute_validators = {
        'name':     valid_name,
        'value':    valid_value,
        'expires':  valid_date,
        'domain':   valid_domain,
        'path':     valid_path,
        'max_age':  valid_max_age,
        'comment':  valid_value,
        'version':  lambda number: re.match("^\d+\Z", str(number)),
        'secure':   lambda item: item is True or item is False,
        'httponly': lambda item: item is True or item is False,
    }


class Cookies(dict, object):
    """Represent a set of cookies indexed by name.

    This class bundles together a set of Cookie objects and provides
    a convenient interface to them. for parsing and producing cookie headers.
    In basic operation it acts just like a dict of Cookie objects, but it adds
    additional convenience methods for the usual cookie tasks: add cookie
    objects by their names, create new cookie objects under specified names,
    parse HTTP request or response data into new cookie objects automatically
    stored in the dict, and render the set in formats suitable for HTTP request
    or response headers.
    """
    def __init__(self, *args, **kwargs):
        dict.__init__(self)
        self.all_cookies = []
        self.add(*args, **kwargs)

    def add(self, *args, **kwargs):
        """Add Cookie objects by their names, or create new ones under
        specified names.

        Any unnamed arguments are interpreted as existing cookies, and
        are added under the value in their .name attribute. With keyword
        arguments, the key is interpreted as the cookie name and the
        value as the UNENCODED value stored in the cookie.
        """
        # Only the first one is accessible through the main interface,
        # others accessible through get_all (all_cookies).
        for cookie in args:
            self.all_cookies.append(cookie)
            if cookie.name in self:
                continue
            self[cookie.name] = cookie
        for key, value in kwargs.items():
            cookie = Cookie(key, value)
            self.all_cookies.append(cookie)
            if key in self:
                continue
            self[key] = cookie

    def get_all(self, key):
        return [cookie for cookie in self.all_cookies
                if cookie.name == key]

    def parse_request(self, header_data, ignore_bad_cookies=False):
        """Parse 'Cookie' header data into Cookie objects, and add them to
        this Cookies object.

        :arg header_data: string containing only 'Cookie:' request headers or
        header values (as in CGI/WSGI HTTP_COOKIE); if more than one, they must
        be separated by CRLF (\\r\\n).

        :arg ignore_bad_cookies: if set, will log each syntactically invalid
        cookie (at the granularity of semicolon-delimited blocks) rather than
        raising an exception at the first bad cookie.

        :returns: a Cookies instance containing Cookie objects parsed from
        header_data.

        .. note::
        If you want to parse 'Set-Cookie:' response headers, please use
        parse_response instead. parse_request will happily turn 'expires=frob'
        into a separate cookie without complaining, according to the grammar.
        """
        cookies_dict = _parse_request(
            header_data, ignore_bad_cookies=ignore_bad_cookies)
        cookie_objects = []
        for name, values in cookies_dict.items():
            for value in values:
                # Use from_dict to check name and parse value
                cookie_dict = {'name': name, 'value': value}
                try:
                    cookie = Cookie.from_dict(cookie_dict)
                except InvalidCookieError:
                    if not ignore_bad_cookies:
                        raise
                else:
                    cookie_objects.append(cookie)
        try:
            self.add(*cookie_objects)
        except (InvalidCookieError):
            if not ignore_bad_cookies:
                raise
            _report_invalid_cookie(header_data)
        return self

    def parse_response(self, header_data, ignore_bad_cookies=False,
                       ignore_bad_attributes=True):
        """Parse 'Set-Cookie' header data into Cookie objects, and add them to
        this Cookies object.

        :arg header_data: string containing only 'Set-Cookie:' request headers
        or their corresponding header values; if more than one, they must be
        separated by CRLF (\\r\\n).

        :arg ignore_bad_cookies: if set, will log each syntactically invalid
        cookie rather than raising an exception at the first bad cookie. (This
        includes cookies which have noncompliant characters in the attribute
        section).

        :arg ignore_bad_attributes: defaults to True, which means to log but
        not raise an error when a particular attribute is unrecognized. (This
        does not necessarily mean that the attribute is invalid, although that
        would often be the case.) if unset, then an error will be raised at the
        first semicolon-delimited block which has an unknown attribute.

        :returns: a Cookies instance containing Cookie objects parsed from
        header_data, each with recognized attributes populated.

        .. note::
        If you want to parse 'Cookie:' headers (i.e., data like what's sent
        with an HTTP request, which has only name=value pairs and no
        attributes), then please use parse_request instead. Such lines often
        contain multiple name=value pairs, and parse_response will throw away
        the pairs after the first one, which will probably generate errors or
        confusing behavior. (Since there's no perfect way to automatically
        determine which kind of parsing to do, you have to tell it manually by
        choosing correctly from parse_request between part_response.)
        """
        cookie_dicts = _parse_response(
            header_data,
            ignore_bad_cookies=ignore_bad_cookies,
            ignore_bad_attributes=ignore_bad_attributes)
        cookie_objects = []
        for cookie_dict in cookie_dicts:
            cookie = Cookie.from_dict(cookie_dict)
            cookie_objects.append(cookie)
        self.add(*cookie_objects)
        return self

    @classmethod
    def from_request(cls, header_data, ignore_bad_cookies=False):
        "Construct a Cookies object from request header data."
        cookies = Cookies()
        cookies.parse_request(
            header_data, ignore_bad_cookies=ignore_bad_cookies)
        return cookies

    @classmethod
    def from_response(cls, header_data, ignore_bad_cookies=False,
                      ignore_bad_attributes=True):
        "Construct a Cookies object from response header data."
        cookies = Cookies()
        cookies.parse_response(
            header_data,
            ignore_bad_cookies=ignore_bad_cookies,
            ignore_bad_attributes=ignore_bad_attributes)
        return cookies

    def render_request(self, sort=True):
        """Render the dict's Cookie objects into a string formatted for HTTP
        request headers (simple 'Cookie: ' style).
        """
        if not sort:
            return ("; ".join(
                cookie.render_request() for cookie in self.values()))
        return ("; ".join(sorted(
            cookie.render_request() for cookie in self.values())))

    def render_response(self, sort=True):
        """Render the dict's Cookie objects into list of strings formatted for
        HTTP response headers (detailed 'Set-Cookie: ' style).
        """
        rendered = [cookie.render_response() for cookie in self.values()]
        return rendered if not sort else sorted(rendered)

    def __repr__(self):
        return "Cookies(%s)" % ', '.join("%s=%r" % (name, cookie.value) for
                                         (name, cookie) in self.items())

    def __eq__(self, other):
        """Test if a Cookies object is globally 'equal' to another one by
        seeing if it looks like a dict such that d[k] == self[k]. This depends
        on each Cookie object reporting its equality correctly.
        """
        if not hasattr(other, "keys"):
            return False
        try:
            keys = sorted(set(self.keys()) | set(other.keys()))
            for key in keys:
                if not key in self:
                    return False
                if not key in other:
                    return False
                if not(self[key] == other[key]):
                    return False
        except (TypeError, KeyError):
            raise
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

########NEW FILE########
__FILENAME__ = core
from __future__ import unicode_literals

import exconsole
import locale
import logging
import os
import signal
import socket
import sys
import syslog
import traceback


import ajenti
import ajenti.locales  # importing locale before everything else!

import ajenti.feedback
import ajenti.licensing
import ajenti.plugins
from ajenti.http import HttpRoot
from ajenti.middleware import SessionMiddleware, AuthenticationMiddleware
from ajenti.plugins import manager
from ajenti.routing import CentralDispatcher
from ajenti.ui import Inflater
from ajenti.util import make_report

import gevent
import gevent.ssl
from gevent import monkey

import ajenti.ipc

# Gevent monkeypatch ---------------------
try:
    monkey.patch_all(select=True, thread=True, aggressive=False, subprocess=True)
except:
    monkey.patch_all(select=True, thread=True, aggressive=False)  # old gevent

from gevent.event import Event
import threading
threading.Event = Event
# ----------------------------------------

import ajenti.compat

from socketio.server import SocketIOServer


def run():
    ajenti.init()

    reload(sys)
    sys.setdefaultencoding('utf8')

    try:
        locale.setlocale(locale.LC_ALL, '')
    except:
        logging.warning('Couldn\'t set default locale')

    logging.info('Ajenti %s running on platform: %s' % (ajenti.version, ajenti.platform))
    if not ajenti.platform in ['debian', 'centos', 'freebsd']:
        logging.warn('%s is not officially supported!' % ajenti.platform)

    if ajenti.debug:
        def cmd_list_instances(ctx=None):
            import pprint
            if not ctx:
                from ajenti.plugins import manager
                ctx = manager.context
            pprint.pprint(ctx._get_all_instances())

        def cmd_sessions():
            import pprint
            sessions = SessionMiddleware.get().sessions
            return sessions

        def cmd_list_instances_session():
            cmd_list_instances(cmd_sessions().values()[0].appcontext)

        exconsole.register(commands=[
            ('_manager', 'PluginManager', ajenti.plugins.manager),
            ('_instances', 'return all @plugin instances', cmd_list_instances),
            ('_sessions', 'return all Sessions', cmd_sessions),
            ('_instances_session', 'return all @plugin instances in session #0', cmd_list_instances_session),
        ])

    # Load plugins
    ajenti.plugins.manager.load_all()
    Inflater.get().precache()

    bind_spec = (ajenti.config.tree.http_binding.host, ajenti.config.tree.http_binding.port)
    if ':' in bind_spec[0]:
        addrs = socket.getaddrinfo(bind_spec[0], bind_spec[1], socket.AF_INET6, 0, socket.SOL_TCP)
        bind_spec = addrs[0][-1]

    # Fix stupid socketio bug (it tries to do *args[0][0])
    socket.socket.__getitem__ = lambda x, y: None

    logging.info('Starting server on %s' % (bind_spec, ))
    if bind_spec[0].startswith('/'):
        if os.path.exists(bind_spec[0]):
            os.unlink(bind_spec[0])
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            listener.bind(bind_spec[0])
        except:
            logging.error('Could not bind to %s' % bind_spec[0])
            sys.exit(1)
        listener.listen(10)
    else:
        listener = socket.socket(socket.AF_INET6 if ':' in bind_spec[0] else socket.AF_INET, socket.SOCK_STREAM)
        try:
            listener.setsockopt(socket.IPPROTO_TCP, socket.TCP_CORK, 1)
        except:
            try:
                socket.TCP_NOPUSH = 4
                listener.setsockopt(socket.IPPROTO_TCP, socket.TCP_NOPUSH, 1)
            except:
                logging.warn('Could not set TCP_CORK/TCP_NOPUSH')
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind(bind_spec)
        except:
            logging.error('Could not bind to %s' % (bind_spec,))
            sys.exit(1)
        listener.listen(10)

    stack = [
        SessionMiddleware.get(),
        AuthenticationMiddleware.get(),
        CentralDispatcher.get()
    ]

    ssl_args = {}
    if ajenti.config.tree.ssl.enable:
        ssl_args['certfile'] = ajenti.config.tree.ssl.certificate_path
        logging.info('SSL enabled: %s' % ssl_args['certfile'])

    ajenti.server = SocketIOServer(
        listener,
        log=open(os.devnull, 'w'),
        application=HttpRoot(stack).dispatch,
        policy_server=False,
        resource='ajenti:socket',
        transports=[
            str('websocket'),
            str('flashsocket'),
            str('xhr-polling'),
            str('jsonp-polling'),
        ],
        **ssl_args
    )

    # auth.log
    try:
        syslog.openlog(
            ident=str(b'ajenti'),
            facility=syslog.LOG_AUTH,
        )
    except:
        syslog.openlog(b'ajenti')

    try:
        gevent.signal(signal.SIGINT, lambda: sys.exit(0))
        gevent.signal(signal.SIGTERM, lambda: sys.exit(0))
    except:
        pass

    ajenti.feedback.start()
    ajenti.ipc.IPCServer.get().start()
    ajenti.licensing.Licensing.get()

    ajenti.server.serve_forever()

    if hasattr(ajenti.server, 'restart_marker'):
        logging.warn('Restarting by request')

        fd = 20  # Close all descriptors. Creepy thing
        while fd > 2:
            try:
                os.close(fd)
                logging.debug('Closed descriptor #%i' % fd)
            except:
                pass
            fd -= 1

        os.execv(sys.argv[0], sys.argv)
    else:
        logging.info('Stopped by request')


def handle_crash(exc):
    logging.error('Fatal crash occured')
    traceback.print_exc()
    exc.traceback = traceback.format_exc(exc)
    report_path = '/root/ajenti-crash.txt'
    try:
        report = open(report_path, 'w')
    except:
        report_path = './ajenti-crash.txt'
        report = open(report_path, 'w')
    report.write(make_report(exc))
    report.close()
    logging.error('Crash report written to %s' % report_path)
    logging.error('Please submit it to https://github.com/Eugeny/ajenti/issues/new')

########NEW FILE########
__FILENAME__ = feedback
"""
Module for sending usage statistics to ajenti.org
"""

import ajenti
import requests
import json
import gevent
import logging

from ajenti.util import *


HOST = 'meta.ajenti.org'
URL = 'http://%s/api/v2/' % HOST


enabled = True


@public
def start():
    gevent.spawn(worker)


def send(url, data):
    id = ajenti.config.tree.installation_id
    if id:
        data['id'] = id
    logging.debug('Feedback >> %s (%s)' % (url, data))
    try:
        response = requests.post(URL + url, data=data)
    except:
        raise IOError()
    logging.debug('Feedback << %s' % response.content)
    return json.loads(response.content)


def worker():
    global enabled
    enabled = ajenti.config.tree.enable_feedback
    if enabled:
        data = {
            'version': ajenti.version,
            'os': ajenti.platform,
            'edition': ajenti.edition,
        }
        if not ajenti.config.tree.installation_id:
            logging.debug('Registering installation')
            enabled = False
            try:
                resp = send('register', data)
                if resp['status'] != 'ok':
                    return
            except IOError:
                pass
            ajenti.config.tree.installation_id = resp['id']
            ajenti.config.save()
            enabled = True

        while True:
            try:
                send('ping', data)
            except IOError:
                pass
            gevent.sleep(3600 * 12)

########NEW FILE########
__FILENAME__ = http
import os
import gzip
import cgi
import math
import gevent
from StringIO import StringIO
from datetime import datetime


class HttpRoot (object):
    """
    A root middleware object that creates the :class:`HttpContext` and dispatches it to other registered middleware
    """

    def __init__(self, stack=[]):
        self.stack = stack

    def add(self, middleware):
        """
        Pushes the middleware onto the stack
        """
        self.stack.append(middleware)

    def dispatch(self, env, start_response):
        """
        Dispatches the WSGI request
        """
        context = HttpContext(env, start_response)
        for middleware in self.stack:
            output = middleware.handle(context)
            if output is not None:
                return output


class HttpContext (object):
    """
    Instance of :class:`HttpContext` is passed to all HTTP handler methods

    .. attribute:: env

        WSGI environment dict

    .. attribute:: path

        Path segment of the URL

    .. attribute:: headers

        List of HTTP response headers

    .. attribute:: response_ready

        Indicates whether a HTTP response has already been submitted in this context

    .. attribute:: query

        HTTP query parameters
    """

    def __init__(self, env, start_response):
        self.start_response = start_response
        self.env = env
        self.path = env['PATH_INFO']
        self.headers = []
        self.response_ready = False

        self.env.setdefault('QUERY_STRING', '')
        if self.env['REQUEST_METHOD'].upper() == 'POST':
            ctype = self.env.get('CONTENT_TYPE', 'application/x-www-form-urlencoded')
            if ctype.startswith('application/x-www-form-urlencoded') \
               or ctype.startswith('multipart/form-data'):
                sio = StringIO(self.env['wsgi.input'].read())
                self.query = cgi.FieldStorage(fp=sio, environ=self.env, keep_blank_values=1)
            else:
                self.body = self.env['wsgi.input'].read()
        else:
            self.query = cgi.FieldStorage(environ=self.env, keep_blank_values=1)

    def add_header(self, key, value):
        """
        Adds a given HTTP header to the response

        :type key: str
        :type value: str
        """
        self.headers += [(key, value)]

    def remove_header(self, key):
        """
        Removed a given HTTP header from the response

        :type key: str
        """
        self.headers = filter(lambda h: h[0] != key, self.headers)

    def fallthrough(self, handler):
        """
        Executes a ``handler`` in this context

        :returns: handler-supplied output
        """
        return handler.handle(self)

    def respond(self, status):
        """
        Creates a response with given HTTP status line
        :type status: str
        """
        self.start_response(status, self.headers)
        self.response_ready = True

    def respond_ok(self):
        """
        Creates a ``HTTP 200 OK`` response
        """
        self.respond('200 OK')

    def respond_server_error(self):
        """
        Returns a HTTP ``500 Server Error`` response
        """
        self.respond('500 Server Error')
        return 'Server Error'

    def respond_forbidden(self):
        """
        Returns a HTTP ``403 Forbidden`` response
        """
        self.respond('403 Forbidden')
        return 'Forbidden'

    def respond_not_found(self):
        """
        Returns a ``HTTP 404 Not Found`` response
        """
        self.respond('404 Not Found')
        return 'Not Found'

    def redirect(self, url):
        """
        Returns a ``HTTP 302 Found`` redirect response with given ``url``
        :type url: str
        """
        self.add_header('Location', url)
        self.respond('302 Found')
        return ''

    def gzip(self, content, compression=9):
        """
        Returns a GZip compressed response with given ``content`` and correct headers
        :type content: str
        :type compression: int
        :rtype: str
        """
        io = StringIO()
        gz = gzip.GzipFile('', 'wb', compression, io)
        gz.write(content)
        gz.close()
        compressed = io.getvalue()

        self.add_header('Content-Length', str(len(compressed)))
        self.add_header('Content-Encoding', 'gzip')
        self.respond_ok()

        return compressed

    def file(self, path, stream=False):
        """
        Returns a GZip compressed response with content of file located in ``path`` and correct headers
        :type path: str
        :type stream: bool
        """

        # Block path traversal
        if '..' in path:
            self.respond_forbidden()
            return

        if not os.path.isfile(path):
            self.respond_not_found()
            return

        content_types = {
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.woff': 'application/x-font-woff',
        }

        ext = os.path.splitext(path)[1]
        if ext in content_types:
            self.add_header('Content-Type', content_types[ext])
        else:
            self.add_header('Content-Type', 'application/octet-stream')

        mtime = datetime.utcfromtimestamp(math.trunc(os.path.getmtime(path)))

        rtime = self.env.get('HTTP_IF_MODIFIED_SINCE', None)
        if rtime:
            try:
                rtime = datetime.strptime(rtime, '%a, %b %d %Y %H:%M:%S GMT')
                if mtime <= rtime:
                    self.respond('304 Not Modified')
                    return
            except:
                pass

        range = self.env.get('HTTP_RANGE', None)
        rfrom = rto = None
        if range and range.startswith('bytes'):
            rsize = os.stat(path).st_size
            rfrom, rto = range.split('=')[1].split('-')
            rfrom = int(rfrom) if rfrom else 0
            rto = int(rto) if rto else (rsize - 1)
        else:
            rfrom = 0
            rto = 999999999

        self.add_header('Last-Modified', mtime.strftime('%a, %b %d %Y %H:%M:%S GMT'))
        self.add_header('Accept-Ranges', 'bytes')

        if stream:
            if rfrom:
                self.add_header('Content-Length', str(rto - rfrom + 1))
                self.add_header('Content-Range', 'bytes %i-%i/%i' % (rfrom, rto, rsize))
                self.respond('206 Partial Content')
            else:
                self.respond_ok()
            fd = os.open(path, os.O_RDONLY)# | os.O_NONBLOCK)
            os.lseek(fd, rfrom or 0, os.SEEK_SET)
            bufsize = 100 * 1024
            read = rfrom
            buf = 1
            while buf:
                buf = os.read(fd, bufsize)
                gevent.sleep(0)
                if read + len(buf) > rto:
                    buf = buf[:rto + 1 - read]
                yield buf
                read += len(buf)
                if read >= rto:
                    break
            os.close(fd)
        else:
            yield self.gzip(open(path).read())


class HttpHandler (object):
    """
    Base class for everything that can process HTTP requests
    """

    def handle(self, context):
        """
        Should create a HTTP response in the given ``context`` and return the plain output

        :param context: HTTP context
        :type  context: :class:`ajenti.http.HttpContext`
        """

########NEW FILE########
__FILENAME__ = ipc
import gevent
from gevent.pywsgi import WSGIServer, WSGIHandler
import logging
import os
import socket
import threading
import traceback

from ajenti.api import *
from ajenti.plugins import manager
from ajenti.util import public


@public
@rootcontext
@interface
class IPCHandler (object):
    """
    Interface for custom IPC endpoints
    """

    def get_name(self):
        """
        Should return short identifier of IPC endpoint:

        $ ajenti-ipc <endpoint-name> <args>

        :rtype str:
        """

    def handle(self, args):
        """
        Override to handle IPC requests

        :param args: list of `str` parameters
        :type  args: list
        """


class IPCWSGIHandler (WSGIHandler):
    def __init__(self, *args, **kwargs):
        WSGIHandler.__init__(self, *args, **kwargs)
        self.client_address = ('ipc', 0)

    def log_request(self):
        pass


class IPCSocketServer (WSGIServer):
    pass


def ipc_application(environment, start_response):
    name, args = environment['PATH_INFO'].split('/')
    args = args.decode('base64').splitlines()
    logging.info('IPC: %s %s' % (name, args))

    for h in IPCHandler.get_all(manager.context):
        if h.get_name() == name:
            try:
                result = h.handle(args)
                if result is None:
                    start_response('404 Not found', [])
                    return ''
                else:
                    start_response('200 OK', [])
                    return result
            except Exception, e:
                traceback.print_exc()
                start_response('500 Error', [])
                return str(e)
            break
    else:
        start_response('404 Handler not found', [])


@public
@plugin
@persistent
@rootcontext
class IPCServer (BasePlugin):
    def start(self):
        gevent.spawn(self.run)

    def run(self):
        socket_path = '/var/run/ajenti-ipc.sock'
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        if os.path.exists(socket_path):
            os.unlink(socket_path)
        sock.bind(socket_path)
        sock.listen(5)
        os.chmod(socket_path, 0700)

        server = IPCSocketServer(sock, application=ipc_application, handler_class=IPCWSGIHandler)
        server.serve_forever()

########NEW FILE########
__FILENAME__ = licensing
import gevent
import json
import logging
import os
import requests

from ajenti.api import *
from ajenti.ipc import IPCHandler
from ajenti.plugins import manager
from ajenti.util import *


HOST = 'ajenti.org'
URL = 'http://%s/licensing-api/' % HOST
LICENSE_PATH = '/var/lib/ajenti/license'


@public
@plugin
@persistent
@rootcontext
class Licensing (BasePlugin):
    licensing_active = True

    def init(self):
        gevent.spawn(self.worker)
        self.__license_status = {}

    def get_license_status(self):
        return self.__license_status

    def read_license(self):
        if not os.path.exists(LICENSE_PATH):
            return None
        return open(LICENSE_PATH).read()

    def remove_license(self):
        if os.path.exists(LICENSE_PATH):
            os.unlink(LICENSE_PATH)
        self.__license_status = {}

    def write_license(self, key):
        open(LICENSE_PATH, 'w').write(key)
        os.chmod(LICENSE_PATH, 0600)

    def activate(self):
        response = requests.post(URL + 'activate?key=' + self.read_license())
        logging.debug('Licensing << %s' % response.content)
        response = json.loads(response.content)
        if response['status'] == 'ok' and self.__license_status == {}:
            logging.info('License activated')
        self.__license_status = response
        return self.__license_status

    def deactivate(self):
        response = requests.post(URL + 'deactivate?key=' + self.read_license())
        logging.debug('Licensing << %s' % response.content)

    def worker(self):
        while True:
            try:
                if self.read_license() is not None:
                    self.activate()
            except:
                pass
            gevent.sleep(3600 * 12)


@plugin
class LicensingIPC (IPCHandler):
    def init(self):
        self.manager = Licensing.get()

    def get_name(self):
        return 'license'

    def handle(self, args):
        command = args[0]
        if command == 'install':
            if len(args) != 2:
                return 'ajenti-ipc license install <key>'
            self.manager.write_license(args[1])
            return json.dumps(self.manager.activate())
        if command == 'remove':
            self.manager.deactivate()
            self.manager.remove_license()
            return 'OK'

########NEW FILE########
__FILENAME__ = log
import logging
import logging.handlers
import os
import sys
from datetime import datetime

from ajenti.api import extract_context


LOG_DIR = '/var/log/ajenti'
LOG_NAME = 'ajenti.log'
LOG_FILE = os.path.join(LOG_DIR, LOG_NAME)


class DebugHandler (logging.StreamHandler):
    """
    Captures log into a buffer for error reports
    """

    def __init__(self):
        self.capturing = False
        self.buffer = ''

    def start(self):
        self.capturing = True

    def stop(self):
        self.capturing = False

    def handle(self, record):
        if self.capturing:
            self.buffer += self.formatter.format(record) + '\n'


class ConsoleHandler (logging.StreamHandler):
    def __init__(self, stream, debug):
        self.debug = debug
        logging.StreamHandler.__init__(self, stream)

    def handle(self, record):
        if not self.stream.isatty():
            return logging.StreamHandler.handle(self, record)

        s = ''
        d = datetime.fromtimestamp(record.created)
        s += d.strftime("\033[37m%d.%m.%Y %H:%M \033[0m")
        if self.debug:
            s += ('%s:%s' % (record.filename, record.lineno)).ljust(30)
        l = ''
        if record.levelname == 'DEBUG':
            l = '\033[37mDEBUG\033[0m '
        if record.levelname == 'INFO':
            l = '\033[32mINFO\033[0m  '
        if record.levelname == 'WARNING':
            l = '\033[33mWARN\033[0m  '
        if record.levelname == 'ERROR':
            l = '\033[31mERROR\033[0m '
        s += l.ljust(9)

        context = extract_context()
        if hasattr(context, 'session') and hasattr(context.session, 'identity'):
            s += '[%s] ' % context.session.identity

        try:
            s += record.msg % record.args
        except:
            s += record.msg
        s += '\n'
        self.stream.write(s)


def make_log(debug=False, log_level=logging.INFO):
    log = logging.getLogger()
    log.setLevel(logging.DEBUG)

    stdout = ConsoleHandler(sys.stdout, debug)
    stdout.setLevel(log_level)

    logging.blackbox = DebugHandler()
    logging.blackbox.setLevel(logging.DEBUG)
    dformatter = logging.Formatter('%(asctime)s %(levelname)-8s %(module)s.%(funcName)s(): %(message)s')
    logging.blackbox.setFormatter(dformatter)
    stdout.setFormatter(dformatter)
    log.addHandler(logging.blackbox)

    log.addHandler(stdout)


def init_log_directory():
    if not os.path.exists(LOG_DIR):
        os.mkdir(LOG_DIR)


def init_log_rotation():
    log = logging.getLogger()
    try:
        handler = logging.handlers.TimedRotatingFileHandler(
            os.path.join(LOG_DIR, LOG_NAME),
            when='midnight',
            backupCount=7
        )
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s: %(message)s'))
        log.addHandler(handler)
    except IOError:
        pass

    return log


def init(level=logging.INFO):
    make_log(debug=level == logging.DEBUG, log_level=level)
    logging.blackbox.start()

########NEW FILE########
__FILENAME__ = middleware
import hashlib
import time
import random
import gevent

import ajenti
from ajenti.api import *
from ajenti.cookies import Cookie, Cookies
from ajenti.plugins import manager
from ajenti.http import HttpHandler
from ajenti.users import UserManager


class Session (object):
    """
    Holds the HTTP session data
    """

    def __init__(self, manager, id):
        self.touch()
        self.id = id
        self.data = {}
        self.active = True
        self.manager = manager
        self.greenlets = []

    def destroy(self):
        """
        Marks this session as dead
        """
        self.active = False
        for g in self.greenlets:
            g.kill()
        self.manager.vacuum()

    def touch(self):
        """
        Updates the "last used" timestamp
        """
        self.timestamp = time.time()

    def spawn(self, *args, **kwargs):
        """
        Spawns a ``greenlet`` that will be stopped and garbage-collected when the session is destroyed

        :params: Same as for :func:`gevent.spawn`
        """
        g = gevent.spawn(*args, **kwargs)
        self.greenlets += [g]

    def is_dead(self):
        return not self.active or (time.time() - self.timestamp) > 3600

    def set_cookie(self, context):
        """
        Adds headers to :class:`ajenti.http.HttpContext` that set the session cookie
        """
        context.add_header('Set-Cookie', Cookie('session', self.id, path='/', httponly=True).render_response())


@plugin
@persistent
@rootcontext
class SessionMiddleware (HttpHandler):
    def __init__(self):
        self.sessions = {}

    def generate_session_id(self, context):
        hash = str(random.random())
        hash += context.env.get('REMOTE_ADDR', '')
        hash += context.env.get('REMOTE_HOST', '')
        hash += context.env.get('HTTP_USER_AGENT', '')
        hash += context.env.get('HTTP_HOST', '')
        return hashlib.sha1(hash).hexdigest()

    def vacuum(self):
        """
        Eliminates dead sessions
        """
        for session in [x for x in self.sessions.values() if x.is_dead()]:
            del self.sessions[session.id]

    def open_session(self, context):
        """
        Creates a new session for the :class:`ajenti.http.HttpContext`
        """
        session_id = self.generate_session_id(context)
        session = Session(self, session_id)
        self.sessions[session_id] = session
        return session

    def handle(self, context):
        self.vacuum()
        cookie_str = context.env.get('HTTP_COOKIE', None)
        context.session = None
        if cookie_str:
            cookie = Cookies.from_request(
                cookie_str,
                ignore_bad_cookies=True,
            ).get('session', None)
            if cookie and cookie.value:
                if cookie.value in self.sessions:
                    # Session found
                    context.session = self.sessions[cookie.value]
                    if context.session.is_dead():
                        context.session = None
        if context.session is None:
            context.session = self.open_session(context)
        context.session.set_cookie(context)
        context.session.touch()


@plugin
@persistent
@rootcontext
class AuthenticationMiddleware (HttpHandler):
    def handle(self, context):
        if not hasattr(context.session, 'identity'):
            if ajenti.config.tree.authentication:
                context.session.identity = None
            else:
                context.session.identity = 'root'
                context.session.appcontext = AppContext(manager.context, context)

        if context.session.identity:
            context.add_header('X-Auth-Status', 'ok')
            context.add_header('X-Auth-Identity', str(context.session.identity))
        else:
            context.add_header('X-Auth-Status', 'none')

    def try_login(self, context, username, password, env=None):
        if UserManager.get().check_password(username, password, env=env):
            self.login(context, username)
            return True
        return False

    def login(self, context, username):
        context.session.identity = username
        context.session.appcontext = AppContext(manager.context, context)

    def logout(self, context):
        context.session.identity = None


__all__ = ['Session', 'SessionMiddleware', 'AuthenticationMiddleware']

########NEW FILE########
__FILENAME__ = main
import os
import gevent
import requests
import json
from datetime import datetime

from ajenti.api import *
from ajenti.api.sensors import Sensor
from ajenti.plugins import manager
from ajenti.plugins.configurator.api import ClassConfigEditor
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
import ajenti


ENDPOINT = 'http://ajenti.local.org:8080/docking-bay/receive/%i'
ENDPOINT = 'http://ajenti.org/docking-bay/receive/%i'


def _check():
    return os.path.exists('/var/lib/ajenti/.ajenti.org.enabled')


@plugin
class AjentiOrgReporterConfigEditor (ClassConfigEditor):
    title = 'ajenti.org reporter'
    icon = 'globe'

    def init(self):
        self.append(self.ui.inflate('ajenti_org:config'))


@plugin
class AjentiOrgReporter (BasePlugin):
    default_classconfig = {'key': None}
    classconfig_editor = AjentiOrgReporterConfigEditor
    classconfig_root = True

    @classmethod
    def verify(cls):
        return _check()

    def init(self):
        self.last_report = None
        self.last_error = None
        gevent.spawn(self.worker)

    @classmethod
    def classinit(cls):
        cls.get()

    def get_key(self):
        self.load_classconfig()
        if not 'key' in self.classconfig:
            return None
        return self.classconfig['key']

    def set_key(self, key):
        self.classconfig['key'] = key
        self.save_classconfig()

    def worker(self):
        if not ENDPOINT:
            return
        while True:
            datapack = {'sensors': {}}

            for sensor in Sensor.get_all():
                data = {}
                for variant in sensor.get_variants():
                    data[variant] = sensor.value(variant)
                datapack['sensors'][sensor.id] = data

            gevent.sleep(10)
            url = ENDPOINT % ajenti.config.tree.installation_id

            if not self.get_key():
                continue

            try:
                requests.post(url, data={
                    'data': json.dumps(datapack),
                    'key': self.get_key()
                })
                self.last_report = datetime.now()
                self.last_error = None
            except Exception, e:
                self.last_error = e


@plugin
class AjentiOrgSection (SectionPlugin):

    @classmethod
    def verify(cls):
        return _check()

    def init(self):
        self.title = 'Ajenti.org'
        self.icon = 'group'
        self.category = ''
        self.order = 25
        self.append(self.ui.inflate('ajenti_org:main'))
        self.reporter = AjentiOrgReporter.get(manager.context)

    def on_page_load(self):
        self.refresh()

    def refresh(self):
        key = self.reporter.get_key()
        self.find('pane-not-configured').visible = key is None
        self.find('pane-configured').visible = key is not None
        self.find('last-report').text = str(self.reporter.last_report)
        self.find('last-error').visible = self.reporter.last_error is not None
        self.find('last-error').text = str(self.reporter.last_error)

    @on('save-key', 'click')
    def on_save_key(self):
        AjentiOrgReporter.get().set_key(self.find('machine-key').value)
        self.refresh()

    @on('disconnect', 'click')
    def on_disconnect(self):
        AjentiOrgReporter.get().set_key(None)
        self.refresh()

########NEW FILE########
__FILENAME__ = main
import ajenti
from ajenti.api import *
from ajenti.plugins.webserver_common.api import WebserverPlugin
from ajenti.util import platform_select


@plugin
class Apache (WebserverPlugin):
    service_name = 'apache2'
    service_buttons = [
        {
            'command': 'force-reload',
            'text': _('Reload'),
            'icon': 'step-forward',
        }
    ]
    hosts_available_dir = platform_select(
        debian='/etc/apache2/sites-available',
        centos='/etc/httpd/conf.d',
        freebsd='/usr/local/etc/apache/sites-available',
    )
    hosts_enabled_dir = '/etc/apache2/sites-enabled'
    supports_host_activation = platform_select(
        debian=True,
        default=False,
    )

    template = """<VirtualHost *:80>
    ServerAdmin webmaster@localhost

    DocumentRoot /var/www

    <Directory />
            Options FollowSymLinks
            AllowOverride None
    </Directory>

    <Directory /var/www/>
            Options Indexes FollowSymLinks MultiViews
            AllowOverride None
            Order allow,deny
            allow from all
    </Directory>
</VirtualHost>
"""

    def init(self):
        self.title = 'Apache'
        self.category = _('Software')
        self.icon = 'globe'
        if ajenti.platform == 'centos':
            self.service_name = 'httpd'

########NEW FILE########
__FILENAME__ = widget
import subprocess

from ajenti.api import plugin
from ajenti.api.sensors import Sensor
from ajenti.plugins.dashboard.api import DashboardWidget


@plugin
class UPSChargeSensor (Sensor):
    id = 'ups'
    timeout = 2

    def measure(self, variant=None):
        data = {}
        for l in subprocess.check_output('apcaccess').splitlines():
            if l and ':' in l:
                k,v = l.split(':', 1)
                k = k.strip()
                v = v.strip()
                data[k] = v

        return (float(data.get('BCHARGE', '0 Percent').split()[0]) / 100.0, data.get('TIMELEFT', 'Unknown'))


@plugin
class UPSWidget (DashboardWidget):
    name = 'UPS'
    icon = 'bolt'

    def init(self):
        self.sensor = Sensor.find('ups')
        self.append(self.ui.inflate('apcups:widget'))
        value = self.sensor.value()
        self.find('charge').value = value[0]
        self.find('time').text = value[1]

########NEW FILE########
__FILENAME__ = main
import os

from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder
from ajenti.util import platform_select

from reconfigure.configs import BIND9Config
from reconfigure.items.bind9 import ZoneData


@plugin
class BIND9Plugin (SectionPlugin):
    config_root = platform_select(
        debian='/etc/bind/',
        centos='/etc/named/',
        arch='/var/named/',
    )

    config_path = platform_select(
        debian='/etc/bind/named.conf',
        default='/etc/named.conf',
    )

    def init(self):
        self.title = 'BIND9'
        self.icon = 'globe'
        self.category = _('Software')

        self.append(self.ui.inflate('bind9:main'))

        self.config = BIND9Config(path=self.config_path)
        self.binder = Binder(None, self)
        self.find('zones').new_item = lambda c: ZoneData()

        def post_zone_bind(o, c, i, u):
            path = i.file
            if path is not None:
                if not path.startswith('/'):
                    path = self.config_root + path
                exists = os.path.exists(path)
            else:
                exists = False
            u.find('no-file').visible = not exists
            u.find('file').visible = exists
            if exists:
                u.find('editor').value = open(path).read()

            def on_save_zone():
                open(path, 'w').write(u.find('editor').value)
                self.context.notify('info', _('Zone saved'))

            def on_create_zone():
                open(path, 'w').write("""$TTL    604800
@       IN      SOA     ns. root.ns. (
                              1         ; Serial
                         604800         ; Refresh
                          86400         ; Retry
                        2419200         ; Expire
                         604800 )       ; Negative Cache TTL
;
@                   IN      NS      ns.
example.com.        IN      A       127.0.0.1
example.com.        IN      AAAA    ::1
""")
                post_zone_bind(o, c, i, u)

            u.find('save-zone').on('click', on_save_zone)
            u.find('create-zone').on('click', on_create_zone)
        self.find('zones').post_item_bind = post_zone_bind

    def on_page_load(self):
        self.refresh()

    def refresh(self):
        self.config.load()
        self.binder.setup(self.config.tree).populate()

    @on('save', 'click')
    def save(self):
        self.binder.update()
        self.config.save()
        self.refresh()
        self.context.notify('info', _('Saved'))

########NEW FILE########
__FILENAME__ = api
from ajenti.api import *
from ajenti.ui import *


@p('title')
@interface
class ClassConfigEditor (BasePlugin, UIElement):
    typeid = 'configurator:classconfig-editor'

########NEW FILE########
__FILENAME__ = configurator
from copy import deepcopy
import logging
import subprocess

import ajenti
import ajenti.locales
from ajenti.api import *
from ajenti.licensing import Licensing
from ajenti.plugins import manager
from ajenti.plugins.main.api import SectionPlugin, intent
from ajenti.ui import on
from ajenti.ui.binder import Binder, DictAutoBinding
from ajenti.users import UserManager, PermissionProvider, restrict
from ajenti.usersync import UserSyncProvider

from reconfigure.items.ajenti import UserData

from licensing import LicensingUI


@plugin
class ClassConfigManager (BasePlugin):
    def init(self):
        self.classes = []

    def reload(self):
        if self.context.user.name == 'root':
            self.classes = BasePlugin.get_instances(self.context)
            self.classes += BasePlugin.get_instances(self.context.parent)
        else:
            self.classes = filter(
                lambda x: not x.classconfig_root,
                BasePlugin.get_instances()
            )
        self.classes = filter(lambda x: x.classconfig_editor, self.classes)
        self.classes = list(set(self.classes))
        self.classes = sorted(
            self.classes,
            key=lambda x: x.classconfig_editor.title
        )


@plugin
class Configurator (SectionPlugin):
    def init(self):
        self.title = _('Configure')
        self.icon = 'wrench'
        self.category = ''
        self.order = 50

        self.append(self.ui.inflate('configurator:main'))

        self.binder = Binder(ajenti.config.tree, self.find('ajenti-config'))

        self.ccmgr = ClassConfigManager.get()
        if Licensing.licensing_active:
            self.find('licensing').append(LicensingUI.new(self.ui))
        else:
            self.find('licensing').delete()
        self.classconfig_binding = Binder(
            self.ccmgr,
            self.find('classconfigs')
        )

        def post_classconfig_bind(object, collection, item, ui):
            def configure():
                self.configure_plugin(item, notify=False)

            ui.find('configure').on('click', configure)

        self.find('classconfigs').find('classes') \
            .post_item_bind = post_classconfig_bind

        self.find('users').new_item = lambda c: UserData()

        def post_user_bind(object, collection, item, ui):
            provider = UserManager.get().get_sync_provider()
            editable = item.name != 'root'
            renameable = editable and provider.allows_renaming
            deletable = renameable

            ui.find('name-edit').visible = renameable
            ui.find('name-label').visible = not renameable
            ui.find('delete').visible = deletable

            box = ui.find('permissions')
            box.empty()

            p = PermissionProvider.get_all()
            for prov in p:
                line = self.ui.create('tab', title=prov.get_name())
                box.append(line)
                for perm in prov.get_permissions():
                    line.append(
                        self.ui.create(
                            'checkbox', id=perm[0],
                            text=perm[1], value=(perm[0] in item.permissions)
                        )
                    )

            def copy():
                self.save()
                newuser = deepcopy(item)
                newuser.name += '_'
                collection[newuser.name] = newuser
                self.refresh()

            ui.find('copy').on('click', copy)

        self.find('users').post_item_bind = post_user_bind

        def post_user_update(object, collection, item, ui):
            box = ui.find('permissions')
            for prov in PermissionProvider.get_all():
                for perm in prov.get_permissions():
                    has = box.find(perm[0]).value
                    if has and not perm[0] in item.permissions:
                        item.permissions.append(perm[0])
                    if not has and perm[0] in item.permissions:
                        item.permissions.remove(perm[0])
            if ui.find('password').value:
                item.password = ui.find('password').value
        self.find('users').post_item_update = post_user_update

    def on_page_load(self):
        self.refresh()

    @on('sync-users-button', 'click')
    def on_sync_users(self):
        self.save()
        prov = UserManager.get().get_sync_provider()
        try:
            prov.test()
            prov.sync()
        except Exception as e:
            self.context.notify('error', str(e))
        self.refresh()

    @on('configure-sync-button', 'click')
    def on_configure_sync(self):
        self.save()
        if UserManager.get().get_sync_provider().classconfig_editor is not None:
            self.configure_plugin(
                UserManager.get().get_sync_provider(),
                notify=False
            )
        self.refresh()

    def refresh(self):
        self.binder.unpopulate()

        self.find('sync-providers').labels = [
            x.title for x in UserSyncProvider.get_classes()
        ]
        self.find('sync-providers').values = [
            x.id for x in UserSyncProvider.get_classes()
        ]

        provider = UserManager.get().get_sync_provider()
        self.find('sync-providers').value = provider.id
        self.find('users-dt').addrow = _('Add') if provider.id == '' else None
        self.find('sync-users-button').visible = provider.id != ''
        self.find('password').visible = provider.id == ''
        self.find('configure-sync-button').visible = \
            provider.classconfig_editor is not None

        try:
            provider.test()
            sync_ok = True
        except Exception as e:
            self.context.notify('error', str(e))
            sync_ok = False

        self.find('sync-status-ok').visible = sync_ok
        self.find('sync-status-fail').visible = not sync_ok

        languages = sorted(ajenti.locales.list_locales())
        self.find('language').labels = [_('Auto'), 'en_US'] + languages
        self.find('language').values = ['', 'en_US'] + languages

        self.binder.setup().populate()
        self.ccmgr.reload()
        self.classconfig_binding.setup().populate()

    @on('save-button', 'click')
    @restrict('configurator:configure')
    def save(self):
        self.binder.update()

        UserManager.get().set_sync_provider(
            self.find('sync-providers').value
        )

        UserManager.get().hash_passwords()
        
        self.refresh()
        ajenti.config.save()
        self.context.notify(
            'info',
            _('Saved. Please restart Ajenti for changes to take effect.')
        )

    @on('fake-ssl', 'click')
    def on_gen_ssl(self):
        host = self.find('fake-ssl-host').value
        if host == '':
            self.context.notify('error', _('Please supply hostname'))
        else:
            self.gen_ssl(host)

    @on('restart-button', 'click')
    def on_restart(self):
        ajenti.restart()

    @intent('configure-plugin')
    def configure_plugin(self, plugin=None, notify=True):
        self.find('tabs').active = 1
        self.refresh()

        if plugin and notify:
            self.context.notify(
                'info',
                _('Please configure %s plugin!') %
                plugin.classconfig_editor.title
            )

        self.activate()

        dialog = self.find('classconfigs').find('dialog')
        dialog.find('container').empty()
        dialog.visible = True

        editor = plugin.classconfig_editor.new(self.ui)
        dialog.find('container').append(editor)

        if editor.find('bind'):
            logging.warn('%s uses old dictbinding classconfig editor layout')
            binder = DictAutoBinding(plugin, 'classconfig', editor.find('bind'))
        else:
            binder = Binder(plugin, editor)
        binder.populate()

        def save(button=None):
            dialog.visible = False
            binder.update()
            plugin.save_classconfig()
            self.save()

        dialog.on('button', save)

    @intent('setup-fake-ssl')
    def gen_ssl(self, host):
        self.save()
        subprocess.call(['ajenti-ssl-gen', host, '-f'])
        ajenti.config.load()
        self.refresh()


@plugin
class ConfigurationPermissionsProvider (PermissionProvider):
    def get_name(self):
        return _('Configuration')

    def get_permissions(self):
        return [
            ('configurator:configure', _('Modify Ajenti configuration')),
            ('configurator:restart', _('Restart Ajenti')),
        ]

########NEW FILE########
__FILENAME__ = licensing
from ajenti.api import *
from ajenti.licensing import Licensing
from ajenti.plugins import manager
from ajenti.ui import UIElement, on


@plugin
class LicensingUI (UIElement):
    typeid = 'configurator:licensingui'

    def init(self):
        self.append(self.ui.inflate('configurator:licensing'))
        self.mgr = Licensing.get()

    def on_page_load(self):
        self.refresh()

    def on_tab_shown(self):
        self.refresh()

    def refresh(self):
        license_status = self.mgr.get_license_status()
        active = bool(self.mgr.get_license_status())
        self.find('license-active').visible = active
        self.find('license-inactive').visible = not active

        self.find('license-current-status').text = {
            'ok': 'OK',
            'invalid-key': _('Invalid key'),
            'invalid-ip': _('Invalid IP'),
            'expired': _('Expired'),
        }.get(license_status.get('status', None), _('Unknown'))

        license = license_status.get('license', {})
        self.find('license-current-expires').text = license.get('expires', '')
        self.find('license-current-type').text = license.get('type', '')
        self.find('license-current-company').text = license.get('company', '')

    @on('license-install', 'click')
    def on_install(self):
        try:
            self.mgr.write_license(self.find('license-key').value)
            self.mgr.activate()
        except Exception, e:
            self.context.notify('error', _('Error: "%s"') % str(e))
        self.refresh()

    @on('license-remove', 'click')
    def on_remove(self):
        try:
            self.mgr.deactivate()
            self.mgr.remove_license()
        except Exception, e:
            self.context.notify('error', _('Error: "%s"') % str(e))
        self.refresh()
########NEW FILE########
__FILENAME__ = api
import subprocess

from ajenti.api import plugin
from reconfigure.configs import CrontabConfig


@plugin
class CronManager (object):
    def load_tab(self, user):
        self.current_user = user
        try:
            data = subprocess.check_output(['crontab', '-l', '-u', user])
        except Exception:
            data = ''
        config = CrontabConfig(content=data)
        config.load()
        return config

    def save_tab(self, user, config):
        data = config.save()[None]
        p = subprocess.Popen(['crontab', '-', '-u', user])
        stdout, stderr = p.communicate(data + '\n')
        if stderr:
            raise Exception(stderr)
            

########NEW FILE########
__FILENAME__ = main
import logging

from ajenti.api import *
from ajenti.ui.binder import Binder
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on

from reconfigure.configs import PasswdConfig
from reconfigure.items.crontab import CrontabEnvSettingData, CrontabNormalTaskData, CrontabSpecialTaskData

from api import CronManager


@plugin
class Cron (SectionPlugin):
    def init(self):
        self.title = 'Cron'
        self.icon = 'time'
        self.category = _('System')
        self.append(self.ui.inflate('cron:main'))

        def create_task(cls):
            logging.info('[cron] created a %s' % cls.__name__)
            return cls()

        def remove_task(i, c):
            c.remove(i)
            logging.info('[cron] removed %s' % getattr(i, 'command', None))

        self.binder = Binder(None, self.find('config'))
        self.find('normal_tasks').new_item = lambda c: create_task(CrontabNormalTaskData)
        self.find('special_tasks').new_item = lambda c: create_task(CrontabSpecialTaskData)
        self.find('env_settings').new_item = lambda c: create_task(CrontabEnvSettingData)
        self.find('normal_tasks').delete_item = remove_task
        self.find('special_tasks').delete_item = remove_task
        self.find('env_settings').delete_item = remove_task

        self.current_user = 'root'

    def on_page_load(self):
        self.refresh()

    @on('user-select', 'click')
    def on_user_select(self):
        self.current_user = self.find('users').value
        logging.info('[cron] selected user %s' % self.current_user)
        self.refresh()

    def refresh(self):
        users_select = self.find('users')
        users_select.value = self.current_user
        users = [x.name for x in PasswdConfig(path='/etc/passwd').load().tree.users if int(x.uid) >= 500 or x.name == 'root']
        users_select.values = users_select.labels = users

        self.config = CronManager.get().load_tab(self.current_user)
        self.binder.setup(self.config.tree).populate()

    @on('save', 'click')
    def on_save(self):
        self.binder.update()
        logging.info('[cron] edited tasks')
        try:
            CronManager.get().save_tab(self.current_user, self.config)
            self.refresh()
        except Exception, e:
            self.context.notify('error', e.message)

########NEW FILE########
__FILENAME__ = main
import os
import subprocess

from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder

from reconfigure.configs import CSFConfig
from reconfigure.items.hosts import AliasData, HostData


@plugin
class CSFSection (SectionPlugin):
    def init(self):
        self.title = _('CSF Firewall')
        self.icon = 'fire'
        self.category = _('System')
        self.backend = CSFBackend.get()

        self.append(self.ui.inflate('csf:main'))

        self.config = CSFConfig(path='/etc/csf/csf.conf')
        self.list_allow = []
        self.list_deny = []
        self.list_tempallow = []
        self.list_tempban = []

        def delete_rule(csf_option, i):
            self.save()
            subprocess.call(['csf', csf_option, i.value.split('#')[0]])
            self.refresh()

        self.find('list_allow').on_delete = lambda i, c: delete('-ar', i)
        self.find('list_deny').on_delete = lambda i, c: delete('-dr', i)
        self.find('list_tempallow').on_delete = lambda i, c: delete('-tr', i)
        self.find('list_tempban').on_delete = lambda i, c: delete('-tr', i)

        def add_rule(csf_option, address):
            self.save()
            p = subprocess.Popen(['csf', csf_option, address], stdout=subprocess.PIPE)
            o, e = p.communicate()
            self.context.notify('info', o)
            self.refresh()

        self.find('list_allow-add').on('click', lambda: add_rule('-a', self.find('permanent-lists-add-address').value))
        self.find('list_deny-add').on('click', lambda: add_rule('-d', self.find('permanent-lists-add-address').value))
        self.find('list_tempallow-add').on('click', lambda: add_rule('-ta', self.find('temporary-lists-add-address').value))
        self.find('list_tempban-add').on('click', lambda: add_rule('-td', self.find('temporary-lists-add-address').value))

        self.binder = Binder(None, self)
        self.binder_lists = Binder(self, self.find('lists'))

    def on_page_load(self):
        self.refresh()

    def refresh(self):
        self.config.load()
        self.list_allow = self.backend.read_list('allow')
        self.list_deny = self.backend.read_list('deny')
        self.list_tempallow = self.backend.read_list('tempallow')
        self.list_tempban = self.backend.read_list('tempban')
        self.binder.setup(self.config.tree).populate()
        self.binder_lists.populate()

    @on('apply', 'click')
    def on_apply(self):
        self.backend.apply()
        self.context.notify('info', _('Applied'))

    @on('save', 'click')
    def save(self):
        self.binder.update()
        self.config.save()
        self.backend.write_list('allow', self.list_allow)
        self.backend.write_list('deny', self.list_deny)
        self.backend.write_list('tempallow', self.list_tempallow)
        self.backend.write_list('tempban', self.list_tempban)

        self.binder.setup(self.config.tree).populate()
        self.context.notify('info', _('Saved'))
        try:
            self.backend.test_config()
            self.context.notify('info', _('Self-test OK'))
        except Exception, e:
            self.context.notify('error', str(e))


class CSFListItem (object):
    def __init__(self, value):
        self.value = value


@plugin
@persistent
@rootcontext
class CSFBackend (object):
    csf_files = {
        'tempallow': '/var/lib/csf/csf.tempallow',
        'tempban': '/var/lib/csf/csf.tempban',
        'allow': '/etc/csf/csf.allow',
        'deny': '/etc/csf/csf.deny',
    }

    def apply(self):
        subprocess.call(['csf', '-r'])

    def test_config(self):
        p = subprocess.Popen(['/usr/local/csf/bin/csftest.pl'], stdout=subprocess.PIPE)
        o, e = p.communicate()
        if p.returncode != 0:
            raise Exception(e)

    def read_list(self, name):
        if not os.path.exists(self.csf_files[name]):
            return []
        return [
            CSFListItem(l.strip())
            for l in open(self.csf_files[name])
            if l.strip() and not l.startswith('#')
        ]

    def write_list(self, name, lst):
        open(self.csf_files[name], 'w').write(
            '\n'.join(
                x.value for x in lst
            ) + '\n'
        )

########NEW FILE########
__FILENAME__ = main
import os
import subprocess

import ajenti
from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder

from reconfigure.configs import CTDBConfig, CTDBNodesConfig, CTDBPublicAddressesConfig
from reconfigure.items.ctdb import NodeData, PublicAddressData


@plugin
class CTDB (SectionPlugin):
    nodes_file = '/etc/ctdb/nodes'
    addresses_file = '/etc/ctdb/public_addresses'

    def init(self):
        self.title = _('Samba Cluster')
        self.icon = 'folder-close'
        self.category = _('Software')

        self.append(self.ui.inflate('ctdb:main'))

        self.config_path = {
            'debian': '/etc/default/ctdb',
            'centos': '/etc/sysconfig/ctdb'
        }[ajenti.platform]

        self.config = CTDBConfig(path=self.config_path)
        self.config.load()

        self.binder = Binder(None, self.find('main-config'))
        self.n_binder = Binder(None, self.find('nodes-config'))
        self.a_binder = Binder(None, self.find('addresses-config'))
        self.find('nodes').new_item = lambda c: NodeData()
        self.find('addresses').new_item = lambda c: PublicAddressData()

    def on_page_load(self):
        n_path = self.config.tree.nodes_file
        self.nodes_config = CTDBNodesConfig(path=n_path)
        if not os.path.exists(n_path):
            open(n_path, 'w').close()
        self.nodes_config.load()

        a_path = self.config.tree.public_addresses_file
        self.addresses_config = CTDBPublicAddressesConfig(path=a_path)
        if not os.path.exists(a_path):
            open(a_path, 'w').close()
        self.addresses_config.load()

        self.config.load()
        self.binder.setup(self.config.tree).populate()
        self.n_binder.setup(self.nodes_config.tree).populate()
        self.a_binder.setup(self.addresses_config.tree).populate()
        self.refresh()

    @on('refresh', 'click')
    def refresh(self):
        try:
            self.find('status').value = subprocess.check_output(['ctdb', 'status'])
            self.find('status-ip').value = subprocess.check_output(['ctdb', 'ip'])
        except:
            self.find('status').value = _('Failed to obtain CTDB status')

    @on('save', 'click')
    def save(self):
        self.binder.update()
        self.n_binder.update()
        self.a_binder.update()
        self.config.save()
        self.nodes_config.save()
        self.addresses_config.save()
        self.context.notify('info', _('Saved'))

########NEW FILE########
__FILENAME__ = api
from ajenti.api import *
from ajenti.ui import UIElement, p


@p('config', public=False, doc="current configuration dict of this widget instance")
@p('container', type=int, default=0)
@p('index', type=int, default=0)
@interface
class DashboardWidget (BasePlugin, UIElement):
    """
    Base class for widgets (inherits :class:`ajenti.ui.UIElement`).
    """
    typeid = 'dashboard:widget'
    name = '---'
    """ Widget type name """
    icon = None
    """ Widget icon name """
    hidden = False
    """ If True, user will not be able to add this widget through dashboard """

    def save_config(self):
        self.event('save-config')


@interface
class ConfigurableWidget (DashboardWidget):
    """
    Base class for widgets with a configuration dialog
    """
    def init(self):
        self.on_prepare()
        self.dialog = self.find('config-dialog')
        if not self.config and self.dialog:
            self.config = self.create_config()
            self.begin_configuration()            
        else:
            self.on_start()

    def begin_configuration(self):
        self.on_config_start()
        self.dialog.on('button', self.on_config)
        self.dialog.visible = True

    def on_config(self, button):
        self.dialog.visible = False
        self.on_config_save()
        self.save_config()

    def on_prepare(self):
        """
        Widget should create its UI in this method. Called before **self.config** is created
        """

    def on_start(self):
        """
        Widget should populate its UI in this method. **self.config** is now available.
        """

    def create_config(self):
        """
        Should return a default config dict
        """
        return None

    def on_config_start(self):
        """
        Called when user begins to configure the widget. Should populate the config dialog.
        """

    def on_config_save(self):
        """
        Called when user is done configuring the widget.
        """

########NEW FILE########
__FILENAME__ = dash
import gevent
import logging
import random
import traceback

import ajenti
from ajenti.api import *
from ajenti.api.sensors import Sensor
from ajenti.ui.binder import CollectionAutoBinding
from ajenti.ui import on, UIElement, p
from ajenti.users import UserManager, PermissionProvider
from ajenti.plugins.main.api import SectionPlugin, intent

from api import DashboardWidget
from updater import AjentiUpdater


@plugin
class Dash (SectionPlugin):
    default_classconfig = {'widgets': []}

    def init(self):
        self.title = _('Dashboard')
        self.category = ''
        self.icon = 'dashboard'
        self.order = 0

        self.append(self.ui.inflate('dashboard:dash'))
        self.dash = self.find('dash')
        self.dash.on('reorder', self.on_reorder)

        self.autorefresh = False

        self.find('header').platform = ajenti.platform_unmapped
        self.find('header').distro = ajenti.platform_string

        def post_widget_bind(o, c, i, u):
            u.find('listitem').on('click', self.on_add_widget_click, i)

        self.find('add-widgets').post_item_bind = post_widget_bind

        classes = [
            x for x in DashboardWidget.get_classes()
            if not x.hidden and
            UserManager.get().has_permission(self.context, WidgetPermissions.name_for(x))
        ]

        CollectionAutoBinding(
            sorted(classes, key=lambda x: x.name),
            None, self.find('add-widgets')).populate()

        self.context.session.spawn(self.worker)
        AjentiUpdater.get().check_for_updates(self.update_check_callback)

    def worker(self):
        while True:
            if self.active and self.autorefresh:
                self.refresh()
            gevent.sleep(5)

    def update_check_callback(self, updates):
        logging.debug('Update availability: %s' % updates)
        self.find('update-panel').visible = (updates != []) and self.context.session.identity == 'root'

    def install_updates(self, updates):
        AjentiUpdater.get().run_update(updates)

    @on('update-ajenti', 'click')
    def install_update(self):
        AjentiUpdater.get().check_for_updates(self.install_updates)

    def on_page_load(self):
        self.refresh()

    @on('refresh-button', 'click')
    def on_refresh(self):
        self.refresh()

    @on('auto-refresh-button', 'click')
    def on_auto_refresh(self):
        self.autorefresh = not self.autorefresh
        self.find('auto-refresh-button').pressed = self.autorefresh
        self.refresh()

    @on('add-button', 'click')
    def on_dialog_open(self):
        self.find('add-dialog').visible = True

    @on('add-dialog', 'button')
    def on_dialog_close(self, button):
        self.find('add-dialog').visible = False

    def on_add_widget_click(self, cls, config=None):
        self.add_widget(cls, config)

    def add_widget(self, cls, config=None):
        self.find('add-dialog').visible = False
        self.classconfig['widgets'].append({
            'class': cls.classname,
            'container': random.randrange(0, 2),
            'index': 0,
            'config': config,
        })
        self.save_classconfig()
        self.refresh()

    @intent('dashboard-add-widget')
    def add_widget_intent(self, cls=None, config=None):
        self.add_widget(cls, config)
        self.activate()

    def refresh(self):
        self.find('header').hostname = Sensor.find('hostname').value()

        self.dash.empty()
        for widget in self.classconfig['widgets']:
            for cls in DashboardWidget.get_classes():
                if cls.classname == widget['class']:
                    if not UserManager.get().has_permission(self.context, WidgetPermissions.name_for(cls)):
                        continue
                    try:
                        instance = cls.new(
                            self.ui,
                            container=widget['container'],
                            index=widget['index'],
                            config=widget['config'],
                        )
                    except Exception, e:
                        traceback.print_exc()
                        instance = CrashedWidget.new(
                            self.ui,
                            container=widget['container'],
                            index=widget['index'],
                            config=widget['config'],
                        )
                        instance.classname = cls.classname
                        instance.set(e)
                    instance.on('save-config', self.on_widget_config, widget, instance)
                    self.dash.append(instance)

    def on_widget_config(self, config, instance):
        config['config'] = instance.config
        self.save_classconfig()
        self.refresh()

    def on_reorder(self, indexes):
        if len(indexes) == 0:
            return
        cfg = {'widgets': []}
        for container, items in indexes.iteritems():
            idx = 0
            for item in items:
                item = self.dash.find_uid(item)
                if item:
                    item.container = container
                    item.index = idx
                    idx += 1
                    cfg['widgets'].append({
                        'class': item.classname,
                        'container': item.container,
                        'index': item.index,
                        'config': item.config,
                    })
        self.classconfig = cfg
        self.save_classconfig()
        self.refresh()


@plugin
class DashboardDash (UIElement):
    typeid = 'dashboard:dash'


@p('platform')
@p('hostname')
@p('distro')
@plugin
class DashboardHeader (UIElement):
    typeid = 'dashboard:header'


@plugin
class CrashedWidget (DashboardWidget):
    hidden = True

    def init(self):
        self.append(self.ui.create('label', id='text'))

    def set(self, e):
        self.find('text').text = 'Widget crashed: ' + str(e)


@plugin
class WidgetPermissions (PermissionProvider):
    def get_name(self):
        return _('Widgets')

    @staticmethod
    def name_for(widget):
        return 'widget:%s' % widget.__name__

    def get_permissions(self):
        # Generate permission set on-the-fly
        return sorted([
            (WidgetPermissions.name_for(x), _(x.name))
            for x in DashboardWidget.get_classes()
            if not x.hidden
        ], key=lambda x: x[1])

########NEW FILE########
__FILENAME__ = text
from ajenti.api import plugin
from ajenti.plugins.dashboard.api import ConfigurableWidget


@plugin
class TextWidget (ConfigurableWidget):
    name = _('Text')
    icon = 'font'

    def on_prepare(self):
        self.append(self.ui.inflate('dashboard:text'))

    def on_start(self):
        self.find('text').text = self.config['text']

    def create_config(self):
        return {'text': ''}

    def on_config_start(self):
        pass

    def on_config_save(self):
        self.config['text'] = self.dialog.find('text').value

########NEW FILE########
__FILENAME__ = updater
import gevent

from ajenti.api import *
from ajenti.plugins.packages.api import PackageManager, PackageInfo


@plugin
class AjentiUpdater (BasePlugin):
    AJENTI_PACKAGE_NAME = 'ajenti'

    def run_update(self, packages):
        packages = packages or [self.AJENTI_PACKAGE_NAME]
        actions = []
        for name in packages:
            mgr = PackageManager.get()
            p = PackageInfo()
            p.name, p.action = name, 'i'
            actions.append(p)
        mgr.do(actions)

    def check_for_updates(self, callback):
        mgr = PackageManager.get()

        def worker():
            mgr.refresh()
            r = []
            for p in mgr.upgradeable:
                if p.name.startswith(self.AJENTI_PACKAGE_NAME):
                    r.append(p.name)
            callback(r)

        gevent.spawn(worker)

########NEW FILE########
__FILENAME__ = welcome
from ajenti.api import plugin
from ajenti.plugins.dashboard.api import DashboardWidget
from ajenti.ui import UIElement


@plugin
class DashboardWelcome (UIElement):
    typeid = 'dashboard:welcome'


@plugin
class WelcomeWidget (DashboardWidget):
    name = _('Welcome')
    icon = 'comment'

    def init(self):
        self.append(self.ui.inflate('dashboard:welcome'))

########NEW FILE########
__FILENAME__ = api
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder


class Database (object):
    def __init__(self):
        self.name = ''


class User (object):
    def __init__(self):
        self.name = ''
        self.host = ''


class DBPlugin (SectionPlugin):
    service_name = ''
    service_buttons = []

    def init(self):
        self.append(self.ui.inflate('db_common:main'))
        self.binder = Binder(None, self)
        self.find_type('servicebar').buttons = self.service_buttons

        def delete_db(db, c):
            self.query_drop(db)
            self.refresh()

        self.find('databases').delete_item = delete_db

        def delete_user(user, c):
            self.query_drop_user(user)
            self.refresh()

        self.find('users').delete_item = delete_user

    def on_page_load(self):
        self.refresh()

    @on('sql-run', 'click')
    def on_sql_run(self):
        try:
            result = self.query_sql(self.find('sql-db').value, self.find('sql-input').value)
            self.context.notify('info', _('Query finished'))
        except Exception, e:
            self.context.notify('error', str(e))
            return

        tbl = self.find('sql-output')
        tbl.empty()

        if len(result) > 200:
            self.context.notify('info', _('Output cut from %i rows to 200') % len(result))
            result = result[:200]

        for row in result:
            erow = self.ui.create('dtr')
            tbl.append(erow)
            for cell in row:
                ecell = self.ui.create('dtd')
                ecell.append(self.ui.create('label', text=str(cell)))
                erow.append(ecell)

    @on('add-db', 'click')
    def on_add_db(self):
        self.find('db-name-dialog').value = ''
        self.find('db-name-dialog').visible = True

    @on('add-user', 'click')
    def on_add_user(self):
        self.find('add-user-dialog').visible = True

    def refresh(self):
        self.databases = []
        self.users = []
        try:
            self.databases = self.query_databases()
            self.users = self.query_users()
        except Exception, e:
            import traceback; traceback.print_exc();
            self.context.notify('error', str(e))
            if hasattr(self, 'config_class'):
                self.context.launch('configure-plugin', plugin=self.config_class.get())
            return

        self.binder.unpopulate()
        self.find('sql-db').labels = self.find('sql-db').values = [x.name for x in self.databases]
        self.binder.setup(self).populate()
        self.find_type('servicebar').reload()

    @on('db-name-dialog', 'submit')
    def on_db_name_dialog_submit(self, value=None):
        try:
            self.query_create(value)
        except Exception, e:
            self.context.notify('error', str(e))
            return
        self.refresh()

    @on('add-user-dialog', 'button')
    def on_add_user_dialog(self, button=None):
        d = self.find('add-user-dialog')
        d.visible = False
        if button == 'ok':
            u = User()
            u.name = d.find('name').value
            u.host = d.find('host').value
            u.password = d.find('password').value
            try:
                self.query_create_user(u)
            except Exception, e:
                self.context.notify('error', str(e))
                return

        self.refresh()

    def query_sql(self, db, sql):
        return []

    def query_databases(self):
        return []

    def query_drop(self, db):
        pass

    def query_create(self, name):
        pass

    def query_users(self):
        return []

    def query_create_user(self, user):
        pass

    def query_drop_user(self, user):
        pass

########NEW FILE########
__FILENAME__ = main
from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder
from ajenti.util import platform_select

from reconfigure.configs import DHCPDConfig
from reconfigure.items.dhcpd import SubnetData, OptionData, RangeData


@plugin
class DHCPDPlugin (SectionPlugin):
    def init(self):
        self.title = _('DHCP Server')
        self.icon = 'sitemap'
        self.category = _('Software')

        self.append(self.ui.inflate('dhcpd:main'))

        self.config = DHCPDConfig(path=platform_select(
            default='/etc/dhcp/dhcpd.conf',
            arch='/etc/dhcpd.conf',
        ))

        self.binder = Binder(None, self)

        for x in self.nearest(lambda x: x.bind == 'ranges'):
            x.new_item = lambda c: RangeData()
        for x in self.nearest(lambda x: x.bind == 'options'):
            x.new_item = lambda c: OptionData()
        self.find('subnets').new_item = lambda c: SubnetData()

    def on_page_load(self):
        self.config.load()
        self.binder.setup(self.config.tree).populate()

    @on('save', 'click')
    def save(self):
        self.binder.update()
        self.config.save()

########NEW FILE########
__FILENAME__ = main
import os

from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder

from reconfigure.configs import ExportsConfig
from reconfigure.items.exports import ExportData, ClientData


@plugin
class Exports (SectionPlugin):
    config_path = '/etc/exports'

    def init(self):
        self.title = _('NFS Exports')
        self.icon = 'hdd'
        self.category = _('Software')
        self.append(self.ui.inflate('exports:main'))

        if not os.path.exists(self.config_path):
            open(self.config_path, 'w').close()

        self.config = ExportsConfig(path=self.config_path)
        self.binder = Binder(None, self)
        self.find('exports').new_item = lambda c: ExportData()
        self.find('clients').new_item = lambda c: ClientData()

    def on_page_load(self):
        self.config.load()
        self.binder.setup(self.config.tree).populate()

    @on('save', 'click')
    def save(self):
        self.binder.update()
        self.config.save()
        self.context.notify('info', _('Saved'))

########NEW FILE########
__FILENAME__ = backend
import grp
import logging
import os
import pwd
import re
import subprocess
import stat
import shutil

from ajenti.api import *
from ajenti.util import str_fsize
from ajenti.plugins import manager
from ajenti.plugins.tasks.manager import TaskManager
from ajenti.plugins.tasks.tasks import CopyFilesTask, MoveFilesTask


class Item (object):
    stat_bits = [
        stat.S_IRUSR,
        stat.S_IWUSR,
        stat.S_IXUSR,
        stat.S_IRGRP,
        stat.S_IWGRP,
        stat.S_IXGRP,
        stat.S_IROTH,
        stat.S_IWOTH,
        stat.S_IXOTH,
    ]

    def __init__(self, path):
        self.checked = False
        self.path, self.name = os.path.split(path)
        self.fullpath = path
        self.isdir = os.path.isdir(path)
        self.icon = 'folder-close' if self.isdir else 'file'
        try:
            self.size = 0 if self.isdir else os.path.getsize(path)
        except OSError:
            self.size = 0
        self.sizestr = '' if self.isdir else str_fsize(self.size)

    def read(self):
        stat = os.stat(self.fullpath)

        try:
            self.owner = pwd.getpwuid(stat.st_uid)[0]
        except KeyError:
            self.owner = str(stat.st_uid)

        try:
            self.group = grp.getgrgid(stat.st_gid)[0]
        except KeyError:
            self.group = str(stat.st_gid)

        self.mod_ur, self.mod_uw, self.mod_ux, \
            self.mod_gr, self.mod_gw, self.mod_gx, \
            self.mod_ar, self.mod_aw, self.mod_ax = [
                (stat.st_mode & Item.stat_bits[i] != 0)
                for i in range(0, 9)
            ]

    @property
    def mode(self):
        mods = [
            self.mod_ur, self.mod_uw, self.mod_ux,
            self.mod_gr, self.mod_gw, self.mod_gx,
            self.mod_ar, self.mod_aw, self.mod_ax
        ]
        return sum(
            Item.stat_bits[i] * (1 if mods[i] else 0)
            for i in range(0, 9)
        )

    def write(self):
        newpath = os.path.join(self.path, self.name)
        if self.fullpath != newpath:
            logging.info('[fm] renaming %s -> %s' % (self.fullpath, newpath))
            os.rename(self.fullpath, newpath)
        self.fullpath = os.path.join(self.path, self.name)
        os.chmod(self.fullpath, self.mode)

        err = None

        try:
            uid = int(self.owner or -1)
        except:
            try:
                uid = pwd.getpwnam(self.owner)[2]
            except KeyError:
                uid = -1
                err = Exception('Invalid owner')
        try:
            gid = int(self.group or -1)
        except:
            try:
                gid = grp.getgrnam(self.group)[2]
            except KeyError:
                gid = -1
                err = Exception('Invalid group')

        os.chown(self.fullpath, uid, gid)
        if err:
            raise err


@plugin
class FMBackend (BasePlugin):
    FG_OPERATION_LIMIT = 1024 * 1024 * 50

    def _escape(self, i):
        if hasattr(i, 'fullpath'):
            i = i.fullpath
        return '\'%s\' ' % i.replace("'", "\\'")

    def _total_size(self, items):
        return sum(_.size for _ in items)

    def _has_dirs(self, items):
        return any(_.isdir for _ in items)

    def init(self):
        self.task_manager = TaskManager.get()

    def remove(self, items, cb=lambda: None):
        logging.info('[fm] removing %s' % ', '.join(x.fullpath for x in items))
        if self._total_size(items) > self.FG_OPERATION_LIMIT or self._has_dirs(items):
            command = 'rm -vfr -- '
            for item in items:
                command += self._escape(item)
            self.context.launch('terminal', command=command, callback=cb)
        else:
            for i in items:
                if os.path.isdir(i.fullpath):
                    shutil.rmtree(i.fullpath)
                else:
                    os.unlink(i.fullpath)
            cb()

    def move(self, items, dest, cb=lambda t: None):
        logging.info('[fm] moving %s to %s' % (', '.join(x.fullpath for x in items), dest))
        if self._total_size(items) > self.FG_OPERATION_LIMIT or self._has_dirs(items):
            paths = [x.fullpath for x in items]
            task = MoveFilesTask.new(source=paths, destination=dest)
            task.callback = cb
            self.task_manager.run(task=task)
        else:
            for i in items:
                shutil.move(i.fullpath, dest)
            cb()

    def copy(self, items, dest, cb=lambda t: None):
        logging.info('[fm] copying %s to %s' % (', '.join(x.fullpath for x in items), dest))
        if self._total_size(items) > self.FG_OPERATION_LIMIT or self._has_dirs(items):
            paths = [x.fullpath for x in items]
            task = CopyFilesTask.new(source=paths, destination=dest)
            task.callback = cb
            self.task_manager.run(task=task)
        else:
            for i in items:
                if os.path.isdir(i.fullpath):
                    shutil.copytree(i.fullpath, os.path.join(dest, i.name))
                else:
                    shutil.copy(i.fullpath, os.path.join(dest, i.name))
            cb()


@interface
class Unpacker (BasePlugin):
    @staticmethod
    def find(fn):
        for u in Unpacker.get_all():
            if u.match(fn):
                return u

    def match(self, fn):
        pass

    def unpack(self, path, cb=lambda: None):
        pass


@plugin
class TarUnpacker (Unpacker):
    def match(self, fn):
        return any(re.match(x, fn) for x in [r'.+\.tar.gz', r'.+\.tgz', r'.+\.tar'])

    def unpack(self, fn, cb=lambda: None):
        self.context.launch('terminal', command='cd "%s"; tar xvf "%s"' % os.path.split(fn), callback=cb)


@plugin
class ZipUnpacker (Unpacker):
    def match(self, fn):
        return any(re.match(x, fn) for x in [r'.+\.zip'])

    def unpack(self, fn, cb=lambda: None):
        self.context.launch('terminal', command='cd "%s"; unzip "%s"' % os.path.split(fn), callback=cb)
########NEW FILE########
__FILENAME__ = fm
import gevent
import grp
import logging
import os
import pwd

from ajenti.api import *
from ajenti.api.http import *
from ajenti.plugins.configurator.api import ClassConfigEditor
from ajenti.plugins.main.api import SectionPlugin, intent
from ajenti.ui import on
from ajenti.ui.binder import Binder

from backend import FMBackend, Item, Unpacker


@plugin
class FileManagerConfigEditor (ClassConfigEditor):
    title = _('File Manager')
    icon = 'folder-open'

    def init(self):
        self.append(self.ui.inflate('fm:config'))


@plugin
class FileManager (SectionPlugin):
    default_classconfig = {'root': '/', 'start': '/'}
    classconfig_editor = FileManagerConfigEditor
    classconfig_root = True

    def init(self):
        self.title = _('File Manager')
        self.category = _('Tools')
        self.icon = 'folder-open'

        self.backend = FMBackend().get()

        self.append(self.ui.inflate('fm:main'))
        self.controller = Controller()

        def post_item_bind(object, collection, item, ui):
            ui.find('name').on('click', self.on_item_click, object, item)
            ui.find('edit').on('click', self.edit, item.fullpath)
        self.find('items').post_item_bind = post_item_bind

        def post_bc_bind(object, collection, item, ui):
            ui.find('name').on('click', self.on_bc_click, object, item)
        self.find('breadcrumbs').post_item_bind = post_bc_bind

        self.clipboard = []
        self.tabs = self.find('tabs')

    def on_first_page_load(self):
        self.new_tab()
        self.binder = Binder(self.controller, self.find('filemanager')).populate()
        self.binder_c = Binder(self, self.find('bind-clipboard')).populate()

    def on_page_load(self):
        self.refresh()

    def refresh_clipboard(self):
        self.binder_c.setup().populate()

    @on('tabs', 'switch')
    def on_tab_switch(self):
        if self.tabs.active == (len(self.controller.tabs) - 1):
            self.new_tab()
        self.refresh()

    @intent('fm:browse')
    def new_tab(self, path=None):
        dir = path or self.classconfig.get('start', None) or '/'
        if not dir.startswith(self.classconfig['root']):
            dir = self.classconfig['root']
        self.controller.new_tab(dir)
        if not self.active:
            self.activate()

    @on('close', 'click')
    def on_tab_close(self):
        if len(self.controller.tabs) > 2:
            self.controller.tabs.pop(self.tabs.active)
        self.tabs.active = 0
        self.refresh()

    @on('new-file', 'click')
    def on_new_file(self):
        destination = self.controller.tabs[self.tabs.active].path
        logging.info('[fm] new file in %s' % destination)
        path = os.path.join(destination, 'new file')
        try:
            open(path, 'w').close()
            self._chown_new(path)
        except OSError, e:
            self.context.notify('error', str(e))
        self.refresh()

    @on('new-dir', 'click')
    def on_new_directory(self):
        destination = self.controller.tabs[self.tabs.active].path
        logging.info('[fm] new directory in %s' % destination)
        path = os.path.join(destination, 'new directory')
        if not os.path.exists(path):
            try:
                os.mkdir(path)
                os.chmod(path, 0755)
                self._chown_new(path)
            except OSError, e:
                self.context.notify('error', str(e))
        self.refresh()

    def _chown_new(self, path):
        uid = self.classconfig.get('new_owner', 'root')
        gid = self.classconfig.get('new_group', 'root')
        try:
            uid = int(uid)
        except:
            uid = pwd.getpwnam(uid)[2]
        try:
            gid = int(gid)
        except:
            gid = grp.getgrnam(gid)[2]
        os.chown(path, uid, gid)

    def upload(self, name, file):
        destination = self.controller.tabs[self.tabs.active].path
        logging.info('[fm] uploading %s to %s' % (name, destination))
        try:
            output = open(os.path.join(destination, name), 'w')
            while True:
                data = file.read(1024 * 1024)
                if not data:
                    break
                gevent.sleep(0)
                output.write(data)
            output.close()
        except OSError, e:
            self.context.notify('error', str(e))
        self.refresh()

    @on('mass-cut', 'click')
    def on_cut(self):
        l = self._get_checked()
        for i in l:
            i.action = 'cut'
        self.clipboard += l
        self.refresh_clipboard()

    @on('mass-copy', 'click')
    def on_copy(self):
        l = self._get_checked()
        for i in l:
            i.action = 'copy'
        self.clipboard += l
        self.refresh_clipboard()

    @on('mass-delete', 'click')
    def on_delete(self):
        self.backend.remove(self._get_checked(), self.refresh)

    @on('paste', 'click')
    def on_paste(self):
        tab = self.controller.tabs[self.tabs.active]
        for_move = []
        for_copy = []
        for i in self.clipboard:
            if i.action == 'cut':
                for_move.append(i)
            else:
                for_copy.append(i)

        try:
            if for_move:
                def callback(task):
                    self.context.notify('info', _('Files moved'))
                    self.refresh()
                self.backend.move(for_move, tab.path, callback)
            if for_copy:
                def callback(task):
                    self.context.notify('info', _('Files copied'))
                    self.refresh()
                self.backend.copy(for_copy, tab.path, callback)
            self.clipboard = []
        except Exception as e:
            self.context.notify('error', str(e))
        self.refresh_clipboard()

    @on('select-all', 'click')
    def on_select_all(self):
        self.binder.update()
        tab = self.controller.tabs[self.tabs.active]
        for item in tab.items:
            item.checked = True
        self.binder.populate()
        self.context.notify('info', _('Selected %i items') % len(tab.items)) 

    def _get_checked(self):
        self.binder.update()
        tab = self.controller.tabs[self.tabs.active]
        r = []
        for item in tab.items:
            if item.checked:
                r.append(item)
                item.checked = False
        self.refresh()
        return r

    @on('clear-clipboard', 'click')
    def on_clear_clipboard(self):
        self.clipboard = []
        self.refresh_clipboard()

    def on_item_click(self, tab, item):
        path = os.path.join(tab.path, item.name)
        if not os.path.isdir(path):
            self.edit(path)
        if not path.startswith(self.classconfig['root']):
            return
        tab.navigate(path)
        self.refresh()

    def edit(self, path):
        self.find('dialog').visible = True
        self.item = Item(path)
        self.item.read()
        self.binder_d = Binder(self.item, self.find('dialog')).populate()

        # Unpack
        u = Unpacker.find(self.item.fullpath.lower())
        unpack_btn = self.find('dialog').find('unpack')
        unpack_btn.visible = u is not None

        def cb():
            self.context.notify('info', _('Unpacked'))
            self.refresh()

        def unpack():
            u.unpack(self.item.fullpath, cb=cb)
            logging.info('[fm] unpacking %s' % self.item.fullpath)

        unpack_btn.on('click', lambda: unpack())

        # Edit
        edit_btn = self.find('dialog').find('edit')
        if self.item.size > 1024 * 1024 * 5:
            edit_btn.visible = False

        def edit():
            self.context.launch('notepad', path=self.item.fullpath)

        edit_btn.on('click', lambda: edit())

    @on('dialog', 'button')
    def on_close_dialog(self, button):
        self.find('dialog').visible = False
        if button == 'save':
            self.binder_d.update()
            try:
                self.item.write()
            except Exception, e:
                self.context.notify('error', str(e))
            self.refresh()

            if self.find('chmod-recursive').value:
                cmd = 'chown -Rv "%s:%s" "%s"; chmod -Rv %o "%s"' % (
                    self.item.owner, self.item.group,
                    self.item.fullpath,
                    self.item.mode,
                    self.item.fullpath,
                )
                self.context.launch('terminal', command=cmd)

            logging.info('[fm] modifying %s: %o %s:%s' % (self.item.fullpath, self.item.mode, self.item.owner, self.item.group))

    def on_bc_click(self, tab, item):
        if not item.path.startswith(self.classconfig['root']):
            return
        tab.navigate(item.path)
        self.refresh()

    def refresh(self):
        for tab in self.controller.tabs:
            tab.refresh()
        self.binder.populate()


@plugin
class UploadReceiver (HttpPlugin):
    @url('/ajenti:fm-upload')
    def handle_upload(self, context):
        file = context.query['file']
        context.session.endpoint.get_section(FileManager).upload(file.filename, file.file)
        context.respond_ok()
        return 'OK'


class Controller (object):
    def __init__(self):
        self.tabs = []

    def new_tab(self, path='/'):
        if len(self.tabs) > 1:
            self.tabs.pop(-1)
        self.tabs.append(Tab(path))
        self.tabs.append(Tab(None))


class Tab (object):
    def __init__(self, path):
        if path:
            self.navigate(path)
        else:
            self.shortpath = '+'
            self.path = None

    def refresh(self):
        if self.path:
            self.navigate(self.path)

    def navigate(self, path):
        if not os.path.isdir(path):
            return
        self.path = path
        self.shortpath = os.path.split(path)[1] or '/'
        self.items = []
        for item in os.listdir(unicode(self.path)):
            itempath = os.path.join(self.path, item)
            if os.path.exists(itempath):
                self.items.append(Item(itempath))
        self.items = sorted(self.items, key=lambda x: (not x.isdir, x.name))

        self.breadcrumbs = []
        p = path
        while len(p) > 1:
            p = os.path.split(p)[0]
            self.breadcrumbs.insert(0, Breadcrumb(p))


class Breadcrumb (object):
    def __init__(self, path):
        self.name = os.path.split(path)[1]
        self.path = path
        if self.path == '/':
            self.name = '/'

########NEW FILE########
__FILENAME__ = disks
import os
import re
import psutil
import shutil
import statvfs

from ajenti.api import *
from ajenti.api.sensors import Sensor


def list_devices(by_name=True, by_uuid=False, by_id=False, by_label=False):
    result = []

    def add_dir(path, namefx=lambda s, r: s, valuefx=lambda s, r: r):
        if os.path.exists(path):
            for s in os.listdir(path):
                rp = os.path.realpath(os.path.join(path, s))
                result.append((namefx(s, rp), valuefx(s, rp)))

    for s in os.listdir('/dev'):
        if re.match('sd.$|hd.$|scd.$|fd.$|ad.+$', s):
            result.append((s, '/dev/' + s))

    if by_uuid:
        add_dir('/dev/disk/by-uuid', lambda s, r: '%s: UUID %s' % (r, s), lambda s, r: 'UUID=%s' % s)

    if by_label:
        add_dir('/dev/disk/by-label', lambda s, r: 'Label "%s"' % s, lambda s, r: 'LABEL=%s' % s)

    if by_id:
        add_dir('/dev/disk/by-id', lambda s, r: '%s: %s' % (r, s))

    return sorted(result, key=lambda x: x[0])


@plugin
class PSUtilDiskUsageSensor (Sensor):
    id = 'disk-usage'
    timeout = 5

    @classmethod
    def __list_partitions(cls):
        return filter(lambda p: p.device, psutil.disk_partitions(True))
    
    @classmethod
    def verify(cls):
        try:
            return len(cls.__list_partitions()) > 0
        except:
            return False

    def get_variants(self):
        return sorted([x.mountpoint for x in self.__list_partitions()])

    def measure(self, path):
        try:
            if path:
                v = psutil.disk_usage(path)
            else:
                return (0, 1)
        except OSError:
            return (0, 1)
        return (v.used, v.free, v.total)


@plugin
class MTabDiskUsageSensor (Sensor):
    """
    Useful for procfs-less virtualization containers
    """
    id = 'disk-usage'
    timeout = 5

    @classmethod
    def verify(cls):
        return os.path.exists('/etc/mtab')

    def get_variants(self):
        return filter(lambda x: x != 'none', sorted(l.split()[1] for l in open('/etc/mtab')))

    def measure(self, path):
        s = os.statvfs(path)
        total = s[statvfs.F_FRSIZE] * s[statvfs.F_BLOCKS]
        free = s[statvfs.F_BFREE] * s[statvfs.F_BSIZE]
        return (total - free, free, total)
        
########NEW FILE########
__FILENAME__ = iops
import os
import psutil

from ajenti.api import plugin
from ajenti.api.sensors import Sensor
from ajenti.plugins.dashboard.api import ConfigurableWidget
from ajenti.util import str_fsize


@plugin
class ImmediateWriteSensor (Sensor):
    id = 'immediate-write'
    timeout = 5

    @classmethod
    def verify(cls):
        return os.path.exists('/proc/diskstats')

    def init(self):
        self.last_write = {}

    def get_variants(self):
        return psutil.disk_io_counters(perdisk=True).keys()

    def measure(self, device):
        try:
            v = psutil.disk_io_counters(perdisk=True)[device]
        except KeyError:
            return 0
        if not self.last_write.get(device, None):
            self.last_write[device] = v.write_bytes
            return 0
        else:
            d = v.write_bytes - self.last_write[device]
            self.last_write[device] = v.write_bytes
            return d


@plugin
class ImmediateReadSensor (Sensor):
    id = 'immediate-read'
    timeout = 5

    @classmethod
    def verify(cls):
        return os.path.exists('/proc/diskstats')

    def init(self):
        self.last_read = {}

    def get_variants(self):
        return psutil.disk_io_counters(perdisk=True).keys()

    def measure(self, device):
        try:
            v = psutil.disk_io_counters(perdisk=True)[device]
        except KeyError:
            return 0
        if not self.last_read.get(device, None):
            self.last_read[device] = v.read_bytes
            return 0
        else:
            d = v.read_bytes - self.last_read[device]
            self.last_read[device] = v.read_bytes
            return d


@plugin
class ImmediateIOWidget (ConfigurableWidget):
    name = _('Immediate I/O')
    icon = 'hdd'

    @classmethod
    def verify(cls):
        return os.path.exists('/proc/diskstats')

    def on_prepare(self):
        self.sensor_write = Sensor.find('immediate-write')
        self.sensor_read = Sensor.find('immediate-read')
        self.append(self.ui.inflate('fstab:iio-widget'))

    def on_start(self):
        self.find('device').text = self.config['device']
        self.find('up').text = str_fsize(self.sensor_write.value(self.config['device'])) + '/s'
        self.find('down').text = str_fsize(self.sensor_read.value(self.config['device'])) + '/s'

    def create_config(self):
        return {'device': ''}

    def on_config_start(self):
        device_list = self.dialog.find('device')
        lst = self.sensor_write.get_variants()
        device_list.labels = lst
        device_list.values = lst
        device_list.value = self.config['device']

    def on_config_save(self):
        self.config['device'] = self.dialog.find('device').value

########NEW FILE########
__FILENAME__ = main
import subprocess

from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder

from reconfigure.configs import FSTabConfig
from reconfigure.items.fstab import FilesystemData

import disks


class Mount (object):
    def __init__(self):
        self.device = ''
        self.mountpoint = ''
        self.type = ''
        self.option = ''


@plugin
class MountsBackend (BasePlugin):
    def __init__(self):
        self.reload()

    def reload(self):
        self.filesystems = []
        for l in subprocess.check_output(['df', '-P']).splitlines()[1:]:
            f = Mount()
            l = l.split()
            f.device = l[0]
            f.mountpoint = l[5]
            f.used = int(l[2]) * 1024
            f.size = int(l[1]) * 1024
            f.usage = 1.0 * f.used / f.size
            self.filesystems.append(f)


@plugin
class Filesystems (SectionPlugin):
    def init(self):
        self.title = _('Filesystems')
        self.icon = 'hdd'
        self.category = _('System')
        self.append(self.ui.inflate('fstab:main'))

        self.find('type').labels = ['Auto', 'EXT2', 'EXT3', 'EXT4', 'NTFS', 'FAT', 'ZFS', 'ReiserFS', 'Samba', 'None', 'Loop']
        self.find('type').values = ['auto', 'ext2', 'ext3', 'ext4', 'ntfs', 'vfat', 'zfs', 'reiser',  'smb',   'none', 'loop']

        self.fstab_config = FSTabConfig(path='/etc/fstab')
        self.mounts = MountsBackend.get()

        self.binder = Binder(None, self)
        self.find('fstab').find('filesystems').new_item = lambda c: FilesystemData()

        def post_mount_bind(object, collection, item, ui):
            ui.find('umount').on('click', self.on_umount, item)

        self.find('mounts').find('filesystems').post_item_bind = post_mount_bind

    def on_page_load(self):
        self.refresh()

    def on_umount(self, mount):
        subprocess.call(['umount', mount.mountpoint])
        self.context.notify('info', _('Unmounted'))
        self.refresh()

    @on('mount-all', 'click')
    def on_mount_all(self):
        self.save()
        if subprocess.call(['mount', '-a']):
            self.context.notify('error', _('mount -a failed'))
        self.refresh()

    @on('refresh', 'click')
    def refresh(self):
        self.binder.unpopulate()
        self.reload_disks()
        self.fstab_config.load()
        self.fstab = self.fstab_config.tree
        self.mounts.reload()
        self.binder.setup(self).populate()

    def reload_disks(self):
        lst = disks.list_devices(by_uuid=True, by_id=True, by_label=True)
        self.find('device').labels = [x[0] for x in lst]
        self.find('device').values = [x[1] for x in lst]

    @on('save', 'click')
    def save(self):
        self.binder.update()
        self.fstab_config.save()
        self.context.notify('info', _('Saved'))

########NEW FILE########
__FILENAME__ = widget
from ajenti.api import plugin
from ajenti.api.sensors import Sensor
from ajenti.plugins.dashboard.api import ConfigurableWidget
from ajenti.util import str_fsize


@plugin
class DiskSpaceWidget (ConfigurableWidget):
    name = _('Disk space')
    icon = 'hdd'

    def on_prepare(self):
        self.sensor = Sensor.find('disk-usage')
        self.append(self.ui.inflate('fstab:widget'))

    def on_start(self):
        self.find('device').text = self.config['device']
        u, f, t = self.sensor.value(self.config['device'])
        self.find('percent').text = str_fsize(u)
        self.find('usage').value = float(1.0 * u / t)

    def create_config(self):
        return {'device': ''}

    def on_config_start(self):
        device_list = self.dialog.find('device')
        lst = self.sensor.get_variants()
        device_list.labels = lst
        device_list.values = lst
        device_list.value = self.config['device']

    def on_config_save(self):
        self.config['device'] = self.dialog.find('device').value


@plugin
class DiskFreeSpaceWidget (DiskSpaceWidget):
    name = _('Free disk space')
    icon = 'hdd'

    def on_prepare(self):
        self.sensor = Sensor.find('disk-usage')
        self.append(self.ui.inflate('fstab:free-widget'))

    def on_start(self):
        self.find('device').text = self.config['device']
        u, f, t = self.sensor.value(self.config['device'])
        self.find('value').text = _('%s free') % str_fsize(f)

########NEW FILE########
__FILENAME__ = sensor
import os
import re
import subprocess

from ajenti.api import *
from ajenti.api.sensors import Sensor


@plugin
class DiskTemperatureSensor (Sensor):
    id = 'hdd-temp'
    timeout = 5

    def get_variants(self):
        r = []
        for s in os.listdir('/dev'):
            if re.match('sd.$|hd.$|scd.$|fd.$|ad.+$', s):
                r.append(s)
        return sorted(r)

    def measure(self, device):
        try:
            v = float('0' + subprocess.check_output(
                ['hddtemp', '/dev/%s' % device, '-uC', '-qn'], stderr=None).strip())
            return v
        except:
            return 0

########NEW FILE########
__FILENAME__ = widget
#coding: utf-8
from ajenti.api import plugin
from ajenti.api.sensors import Sensor
from ajenti.plugins.dashboard.api import ConfigurableWidget


@plugin
class HDDTempWidget (ConfigurableWidget):
    name = _('HDD Temperature')
    icon = 'hdd'

    def on_prepare(self):
        self.sensor = Sensor.find('hdd-temp')
        self.append(self.ui.inflate('hddtemp:widget'))

    def on_start(self):
        self.find('device').text = self.config['device']
        v = self.sensor.value(self.config['device'])
        self.find('value').text = '%.2f °C' % v

    def create_config(self):
        return {'device': ''}

    def on_config_start(self):
        device_list = self.dialog.find('device')
        lst = self.sensor.get_variants()
        device_list.labels = lst
        device_list.values = lst
        device_list.value = self.config['device']

    def on_config_save(self):
        self.config['device'] = self.dialog.find('device').value

########NEW FILE########
__FILENAME__ = widget
import subprocess
import re
import os

from ajenti.api import plugin
from ajenti.api.sensors import Sensor
from ajenti.plugins.dashboard.api import ConfigurableWidget


@plugin
class HDPARMSensor (Sensor):
    id = 'hdparm_state'
    timeout = 5

    def get_variants(self):
        r = []
        for s in os.listdir('/dev'):
            if re.match('sd.$|hd.$|scd.$|fd.$|ad.+$', s):
                r.append(s)
        return sorted(r)

    def measure(self, path):
        """
        returns state string
        """
        if not path:
            return -1
        output = subprocess.check_output(['hdparm', '-C', '/dev/' + path]).splitlines()
        if len(output) < 3:
            return None
        r = output[-1].split(':')[-1].strip()
        return r


@plugin
class HDPARMWidget (ConfigurableWidget):
    name = _('HDD drive state')
    icon = 'hdd'

    def on_prepare(self):
        self.sensor = Sensor.find('hdparm_state')
        self.append(self.ui.inflate('hdparm:widget'))

    def on_start(self):
        self.find('device').text = self.config['device']
        v = self.sensor.value(self.config['device'])
        self.find('value').text = v or _('No data')

    def create_config(self):
        return {'device': ''}

    def on_config_start(self):
        device_list = self.dialog.find('device')
        lst = self.sensor.get_variants()
        device_list.labels = lst
        device_list.values = lst
        device_list.value = self.config['device']

    def on_config_save(self):
        self.config['device'] = self.dialog.find('device').value

########NEW FILE########
__FILENAME__ = main
from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder

from reconfigure.configs import HostsConfig
from reconfigure.items.hosts import AliasData, HostData


@plugin
class Hosts (SectionPlugin):
    def init(self):
        self.title = _('Hosts')
        self.icon = 'sitemap'
        self.category = _('System')

        self.append(self.ui.inflate('hosts:main'))

        self.config = HostsConfig(path='/etc/hosts')
        self.binder = Binder(None, self.find('hosts-config'))
        self.find('aliases').new_item = lambda c: AliasData()
        self.find('hosts').new_item = lambda c: HostData()

    def on_page_load(self):
        self.config.load()
        self.binder.setup(self.config.tree).populate()

    @on('save', 'click')
    def save(self):
        self.binder.update()
        self.config.save()

########NEW FILE########
__FILENAME__ = sensor
import subprocess

from ajenti.api import *
from ajenti.api.sensors import Sensor
from ajenti.util import cache_value


@plugin
class IPMISensor (Sensor):
    id = 'ipmi'
    timeout = 5

    @cache_value(2)
    def _get_data(self):
        r = {}
        for l in subprocess.check_output(['ipmitool', 'sensor']).splitlines():
            l = l.split('|')
            if len(l) > 2:
                r[l[0].strip()] = (l[1].strip(), l[2].strip())
        return r

    def get_variants(self):
        return sorted(self._get_data().keys())

    def measure(self, variant):
        try:
            return self._get_data()[variant]
        except:
            return (0, '')

########NEW FILE########
__FILENAME__ = widget
#coding: utf-8
from ajenti.api import plugin
from ajenti.api.sensors import Sensor
from ajenti.plugins.dashboard.api import ConfigurableWidget


@plugin
class IPMIWidget (ConfigurableWidget):
    name = _('IPMI Sensor')
    icon = 'dashboard'

    def on_prepare(self):
        self.sensor = Sensor.find('ipmi')
        self.append(self.ui.inflate('ipmi:widget'))

    def on_start(self):
        self.find('variant').text = self.config['variant']
        v = self.sensor.value(self.config['variant'])
        self.find('value').text = v[0]
        self.find('unit').text = v[1]

    def create_config(self):
        return {'variant': ''}

    def on_config_start(self):
        v_list = self.dialog.find('variant')
        lst = self.sensor.get_variants()
        v_list.labels = lst
        v_list.values = lst
        v_list.value = self.config['variant']

    def on_config_save(self):
        self.config['variant'] = self.dialog.find('variant').value

########NEW FILE########
__FILENAME__ = main
import os
import stat
import itertools
import subprocess

from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.inflater import TemplateNotFoundError
from ajenti.ui.binder import Binder, CollectionAutoBinding

from ajenti.plugins.network.api import NetworkManager

from reconfigure.configs import IPTablesConfig
from reconfigure.items.iptables import TableData, ChainData, RuleData, OptionData


@interface
class FirewallManager (object):
    def get_autostart_state(self):
        pass

    def set_autostart_state(self, state):
        pass


@plugin
class DebianFirewallManager (FirewallManager):
    platforms = ['debian']
    autostart_script_path = '/etc/network/if-up.d/iptables'
    config_path = '/etc/iptables.up.rules'
    config_path_ajenti = '/etc/iptables.up.rules.ajenti'

    def get_autostart_state(self):
        return os.path.exists(self.autostart_script_path)

    def set_autostart_state(self, state):
        if state and not self.get_autostart_state():
            open(self.autostart_script_path, 'w').write("""#!/bin/sh
            iptables-restore < %s
            """ % self.config_path)
            os.chmod(self.autostart_script_path, stat.S_IRWXU | stat.S_IRWXO)
        if not state and self.get_autostart_state():
            os.unlink(self.autostart_script_path)


@plugin
class CentOSFirewallManager (FirewallManager, BasePlugin):
    platforms = ['centos']
    config_path = '/etc/sysconfig/iptables'
    config_path_ajenti = '/etc/iptables.up.rules.ajenti'

    def get_autostart_state(self):
        return True

    def set_autostart_state(self, state):
        self.context.notify('info', _('You can\'t disable firewall autostart on this platform'))

@plugin
class ArchFirewallManager (FirewallManager, BasePlugin):
    platforms = ['arch']
    config_path = '/etc/iptables/iptables.rules'
    config_path_ajenti = '/etc/iptables/iptables-ajenti.rules'

@plugin
class Firewall (SectionPlugin):
    platforms = ['centos', 'debian', 'arch']

    def init(self):
        self.title = _('Firewall')
        self.icon = 'fire'
        self.category = _('System')

        self.append(self.ui.inflate('iptables:main'))

        self.fw_mgr = FirewallManager.get()
        self.config = IPTablesConfig(path=self.fw_mgr.config_path_ajenti)
        self.binder = Binder(None, self.find('config'))

        self.find('tables').new_item = lambda c: TableData()
        self.find('chains').new_item = lambda c: ChainData()
        self.find('rules').new_item = lambda c: RuleData()
        self.find('options').new_item = lambda c: OptionData()
        self.find('options').binding = OptionsBinding
        self.find('options').filter = lambda i: not i.name in ['j', 'jump']

        def post_rule_bind(o, c, i, u):
            u.find('add-option').on('change', self.on_add_option, c, i, u)
            action = ''
            j_option = i.get_option('j', 'jump')
            if j_option:
                action = j_option.arguments[0].value
            u.find('action').text = action
            u.find('action').style = 'iptables-action iptables-%s' % action
            u.find('action-select').value = action
            u.find('title').text = i.comment if i.comment else i.summary

        def post_rule_update(o, c, i, u):
            action = u.find('action-select').value
            j_option = i.get_option('j', 'jump')
            if j_option:
                j_option.arguments[0].value = action
            else:
                if action:
                    o = OptionData.create_destination()
                    o.arguments[0].value = action
                    i.options.append(o)

        self.find('rules').post_item_bind = post_rule_bind
        self.find('rules').post_item_update = post_rule_update

        self.find('add-option').values = self.find('add-option').labels = [_('Add option')] + sorted(OptionData.templates.keys())

    def on_page_load(self):
        if not os.path.exists(self.fw_mgr.config_path_ajenti):
            if not os.path.exists(self.fw_mgr.config_path):
                open(self.fw_mgr.config_path, 'w').write("""
*mangle
:PREROUTING ACCEPT [0:0]
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
:POSTROUTING ACCEPT [0:0]
COMMIT
*nat
:PREROUTING ACCEPT [0:0]
:INPUT ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
:POSTROUTING ACCEPT [0:0]
COMMIT
*filter
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
COMMIT

                """)
            open(self.fw_mgr.config_path_ajenti, 'w').write(open(self.fw_mgr.config_path).read())
        self.config.load()
        self.refresh()

    @on('load-current', 'click')
    def on_load_current(self):
        subprocess.call('iptables-save > %s' % self.fw_mgr.config_path, shell=True)
        self.config.load()
        self.refresh()

    def refresh(self):
        self.find('autostart').text = (_('Disable') if self.fw_mgr.get_autostart_state() else _('Enable')) + _(' autostart')

        actions = ['ACCEPT', 'DROP', 'REJECT', 'LOG', 'MASQUERADE', 'DNAT', 'SNAT'] + \
            list(set(itertools.chain.from_iterable([[c.name for c in t.chains] for t in self.config.tree.tables])))
        self.find('action-select').labels = actions
        self.find('action-select').values = actions
        self.find('chain-action-select').labels = actions
        self.find('chain-action-select').values = actions
        self.binder.setup(self.config.tree).populate()

    @on('autostart', 'click')
    def on_autostart_change(self):
        self.fw_mgr.set_autostart_state(not self.fw_mgr.get_autostart_state())
        self.refresh()

    def on_add_option(self, options, rule, ui):
        o = OptionData.create(ui.find('add-option').value)
        ui.find('add-option').value = ''
        rule.options.append(o)
        self.binder.populate()

    @on('save', 'click')
    def save(self):
        self.binder.update()

        for t in self.config.tree.tables:
            for c in t.chains:
                for r in c.rules:
                    r.verify()

        self.config.save()

        open(self.fw_mgr.config_path, 'w').write(
            ''.join(
                l.split('#')[0] + '\n'
                for l in
                open(self.fw_mgr.config_path_ajenti).read().splitlines()
            )
        )
        self.refresh()
        self.context.notify('info', _('Saved'))

    @on('edit', 'click')
    def raw_edit(self):
        self.context.launch('notepad', path=self.fw_mgr.config_path_ajenti)

    @on('apply', 'click')
    def apply(self):
        self.save()
        cmd = 'cat %s | iptables-restore' % self.fw_mgr.config_path
        if subprocess.call(cmd, shell=True) != 0:
            self.context.launch('terminal', command=cmd)
        else:
            self.context.notify('info', _('Applied successfully'))


class OptionsBinding (CollectionAutoBinding):
    option_map = {
        's': 'source',
        'src': 'source',
        'i': 'in-interface',
        'o': 'out-interface',
        'sport': 'source-port',
        'dport': 'destination-port',
        'sports': 'source-ports',
        'dports': 'destination-ports',
        'm': 'match',
        'p': 'protocol',
    }

    template_map = {
        'source': 'address',
        'destination': 'address',
        'mac-source': 'address',
        'in-interface': 'interface',
        'out-interface': 'interface',
        'source-port': 'port',
        'destination-port': 'port',
        'source-ports': 'ports',
        'destination-ports': 'ports',
    }

    def get_template(self, item, ui):
        root = ui.ui.inflate('iptables:option')

        option = item.name
        if option in OptionsBinding.option_map:
            option = OptionsBinding.option_map[option]
        item.name = option
        item.cmdline = '--%s' % option

        if option in OptionsBinding.template_map:
            template = OptionsBinding.template_map[option]
        else:
            template = option

        try:
            option_ui = ui.ui.inflate('iptables:option-%s' % template)
        except TemplateNotFoundError:
            option_ui = ui.ui.inflate('iptables:option-custom')

        if option_ui.find('device'):
            device = option_ui.find('device')
            device.values = device.labels = NetworkManager.get().get_devices()
        root.find('slot').append(option_ui)
        return root

########NEW FILE########
__FILENAME__ = main
#coding: utf-8
import subprocess
import re

from ajenti.api import BasePlugin, plugin
from ajenti.api.sensors import Sensor
from ajenti.plugins.dashboard.api import ConfigurableWidget
from ajenti.util import *


class LMSensors (BasePlugin):
    re_temp = re.compile(r'^(?P<name>.+?):\s+\+(?P<value>[\d.]+).+$')

    @cache_value(3)
    def get(self):
        try:
            lines = subprocess.check_output(['sensors']).splitlines()
        except subprocess.CalledProcessError, e:
            return {}  # sensors not configured
        r = {}
        for l in lines:
            m = self.re_temp.match(l)
            if m:
                r[m.groupdict()['name']] = float(m.groupdict()['value'])
        return r


@plugin
class Sensors (Sensor):
    id = 'lm-sensors'
    timeout = 3

    def init(self):
        self.lm = LMSensors()

    def measure(self, variant=None):
        try:
            return self.lm.get()[variant]
        except KeyError:
            return 0

    def get_variants(self):
        return self.lm.get().keys()


@plugin
class TempWidget (ConfigurableWidget):
    name = 'Temperature'
    icon = 'fire'

    def on_prepare(self):
        self.sensor = Sensor.find('lm-sensors')
        self.append(self.ui.inflate('lm_sensors:widget'))

    def on_start(self):
        value = self.sensor.value(self.config['sensor'])
        self.find('name').text = self.config['sensor']
        self.find('value').text = '+%.1f °C' % value

    def create_config(self):
        return {'sensor': ''}

    def on_config_start(self):
        service_list = self.dialog.find('sensor')
        service_list.labels = service_list.values = self.sensor.get_variants()
        service_list.value = self.config['sensor']

    def on_config_save(self):
        self.config['sensor'] = self.dialog.find('sensor').value

########NEW FILE########
__FILENAME__ = main
import gevent
import time

from ajenti.api import *
from ajenti.api.http import SocketPlugin
from ajenti.plugins.main.api import SectionPlugin, intent
from ajenti.ui import UIElement, p, on


@plugin
class Logs (SectionPlugin):
    def init(self):
        self.title = _('Logs')
        self.icon = 'list'
        self.category = _('System')

        self.append(self.ui.inflate('logs:main'))
        self.opendialog = self.find('opendialog')
        self.log = self.find('log')

    @on('open-button', 'click')
    def on_open(self):
        self.opendialog.show()

    @on('opendialog', 'button')
    def on_open_dialog(self, button):
        self.opendialog.visible = False

    @on('opendialog', 'select')
    def on_file_select(self, path=None):
        self.opendialog.visible = False
        self.select(path)

    @intent('view-log')
    def select(self, path):
        self.log.path = path
        self.activate()


@p('path', type=unicode)
@plugin
class LogView (UIElement):
    typeid = 'logs:log'


@plugin
class LogsSocket (SocketPlugin):
    name = '/log'

    def init(self):
        self.reader = None

    def on_message(self, message):
        if message['type'] == 'select':
            self.path = message['path']
            self.reader = Reader(self.path)
            self.spawn(self.worker)
            self.emit('add', self.reader.data)

    def on_disconnect(self):
        if self.reader:
            self.reader.kill()

    def worker(self):
        while True:
            data = self.reader.read()
            if data is not None:
                self.send_data(data)

    def send_data(self, data):
        self.emit('add', data)


class Reader():
    def __init__(self, path):
        self.data = ''
        self.file = open(path, 'r')

    def read(self):
        ctr = 0
        try:
            l = self.file.readline()
        except:
            return None
        d = ''
        while not l:
            gevent.sleep(0.33)
            l = self.file.readline()
        while l:
            gevent.sleep(0)
            d += l
            ctr += 1
            l = self.file.readline()
            if len(d) > 1024 * 128:
                break
        return d

    def kill(self):
        self.file.close()

########NEW FILE########
__FILENAME__ = api
from ajenti.api import *
from ajenti.ui import *


@p('title')
@p('icon', default=None)
@p('order', default=99, doc='Sorting weight, light plugins end up higher')
@p('category', default='Other', doc='Section category name')
@p('active', default=False)
@p('clsname', default='')
@p('hidden', default=False, type=bool, doc='Hide this section in sidebar')
@track
@interface
class SectionPlugin (BasePlugin, UIElement):
    """
    A base class for section plugins visible on the left in the UI. Inherits :class:`ajenti.ui.UIElement`
    """

    typeid = 'main:section'

    def init(self):
        self._first_page_load = True
        self._intents = {}
        for k, v in self.__class__.__dict__.iteritems():
            if hasattr(v, '_intent'):
                self._intents[v._intent] = getattr(self, k)

    def activate(self):
        """
        Activate this section
        """
        self.context.endpoint.switch_tab(self)

    def on_first_page_load(self):
        """
        Called before first ``on_page_load``
        """

    def on_page_load(self):
        """
        Called when this section becomes active, or the page is reloaded
        """


def intent(id):
    """
    Registers this method as an intent with given ID
    """
    def decorator(fx):
        fx._intent = id
        return fx
    return decorator

########NEW FILE########
__FILENAME__ = controls_binding
from ajenti.api import *
from ajenti.ui import p, UIElement


@plugin
class BindTemplate (UIElement):
    typeid = 'bind:template'

    def init(self):
        self.visible = False

########NEW FILE########
__FILENAME__ = controls_containers
from ajenti.api import *
from ajenti.ui import p, UIElement


@p('width', default=None)
@p('height', default=None)
@p('scroll', default=False, type=bool)
@plugin
class Box (UIElement):
    typeid = 'box'


@p('text', default='', bindtypes=[str, unicode])
@plugin
class FormLine (UIElement):
    typeid = 'formline'


@p('text', default='', bindtypes=[str, unicode])
@plugin
class FormGroup (UIElement):
    typeid = 'formgroup'


@p('expanded', default=False, type=bool, bindtypes=[bool])
@plugin
class Collapse (UIElement):
    typeid = 'collapse'


@p('expanded', default=False, type=bool, bindtypes=[bool])
@plugin
class CollapseRow (UIElement):
    typeid = 'collapserow'


@p('width', default='99%')
@p('emptytext', type=unicode, default=_('Empty'))
@p('filtering', type=bool, default=True)
@p('filterrow', type=unicode, default=_('Filter...'))
@p('filter', type=unicode, default='')
@p('addrow', type=unicode, default=None)
@plugin
class Table (UIElement):
    typeid = 'dt'


@p('sortable', default=True, type=bool)
@p('order', default='', type=str)
@plugin
class SortableTable (Table):
    typeid = 'sortabledt'


@p('header', default=False)
@plugin
class TableRow (UIElement):
    typeid = 'dtr'


@p('width', default=None)
@p('forcewidth', default=None)
@plugin
class TableCell (UIElement):
    typeid = 'dtd'


@p('text', default='', bindtypes=[str, unicode])
@p('width', default=None)
@plugin
class TableHeader (UIElement):
    typeid = 'dth'


@p('width', default='99%')
@plugin
class LayoutTable (UIElement):
    typeid = 'lt'


@p('width', default=None)
@plugin
class LayoutTableCell (UIElement):
    typeid = 'ltd'


@p('title', default='', bindtypes=[str, unicode])
@plugin
class Tab (UIElement):
    typeid = 'tab'


@p('active', type=int, default=0)
@plugin
class Tabs (UIElement):
    typeid = 'tabs'

    def init(self):
        self._active = 0
        self.refresh()

    #---

    def active_get(self):
        return getattr(self, '_active', 0)

    def active_set(self, active):
        self._active = active
        self.on_switch()

    active = property(active_get, active_set)

    #---

    def on_switch(self):
        self.children_changed = True  # force update
        self.refresh()

    def refresh(self):
        for i, child in enumerate(self.children):
            child.visible = int(self.active) == i
            if child.visible:
                child.broadcast('on_tab_shown')

########NEW FILE########
__FILENAME__ = controls_dialogs
import os

from ajenti.api import *
from ajenti.plugins import *
from ajenti.ui import *


@p('buttons', default=['ok'], type=eval)
@plugin
class Dialog (UIElement):
    typeid = 'dialog'

    def init(self):
        presets = {
            'ok': {'text': 'OK', 'id': 'ok'},
            'cancel': {'text': 'Cancel', 'id': 'cancel'},
        }
        new_buttons = []
        for button in self.buttons:
            if isinstance(button, basestring) and button in presets:
                new_buttons.append(presets[button])
            else:
                new_buttons.append(button)
        self.buttons = new_buttons


@p('text', default='Input value:', type=unicode)
@p('value', default='', bindtypes=[str, unicode], type=unicode)
@plugin
class InputDialog (UIElement):
    typeid = 'inputdialog'

    def init(self):
        self.append(self.ui.inflate('main:input-dialog'))
        self.find('text').text = self.text

    def on_button(self, button):
        self.value = self.find('input').value
        if button == 'ok':
            self.reverse_event('submit', {'value': self.value})
        else:
            self.reverse_event('cancel', {})
        self.visible = False


class BaseFileDialog (object):
    shows_files = True
    layout = 'main:file-dialog'

    def navigate(self, path):
        self.path = path
        self.verify_path()
        self.refresh()

    def verify_path(self):
        if not self.path.startswith(self.root) or not os.path.isdir(self.path):
            self.path = self.root

    def show(self):
        self.visible = True
        self.refresh()

    def refresh(self):
        self.empty()
        self.append(self.ui.inflate(self.layout))
        list = self.find('list')
        _dirs = []
        if len(self.path) > 1:
            _dirs.append('..')
        for item in _dirs + sorted(os.listdir(unicode(self.path))):
            isdir = os.path.isdir(os.path.join(self.path, item))
            if not self.shows_files and not isdir:
                continue
            itemui = self.ui.create('listitem', children=[
                self.ui.create('hc', children=[
                    self.ui.create('icon', icon='folder-open' if isdir else 'file'),
                    self.ui.create('label', text=item),
                ])
            ])
            itemui.on('click', self.on_item_click, item)
            list.append(itemui)


@p('path', default='/', type=unicode)
@p('root', default='/', type=unicode)
@plugin
class OpenFileDialog (UIElement, BaseFileDialog):
    typeid = 'openfiledialog'

    def init(self):
        self.verify_path()
        self.refresh()

    def on_item_click(self, item):
        path = os.path.abspath(os.path.join(self.path, item))
        if os.path.isdir(path):
            self.navigate(path)
        else:
            self.reverse_event('select', {'path': path})

    def on_button(self, button=None):
        self.reverse_event('select', {'path': None})


@p('path', default='/', type=unicode)
@p('root', default='/', type=unicode)
@plugin
class OpenDirDialog (UIElement, BaseFileDialog):
    typeid = 'opendirdialog'
    shows_files = False

    def init(self):
        self.verify_path()
        self.refresh()

    def on_item_click(self, item):
        path = os.path.abspath(os.path.join(self.path, item))
        if os.path.exists(path):
            self.navigate(path)

    def on_button(self, button=None):
        if button == 'select':
            self.reverse_event('select', {'path': self.path})
        else:
            self.reverse_event('select', {'path': None})


@p('path', default='/', type=unicode)
@p('root', default='/', type=unicode)
@plugin
class SaveFileDialog (UIElement, BaseFileDialog):
    typeid = 'savefiledialog'
    shows_files = False
    layout = 'main:file-dialog-save'

    def init(self):
        self.refresh()

    def on_item_click(self, item):
        path = os.path.abspath(os.path.join(self.path, item))
        if os.path.isdir(path):
            self.navigate(path)
        else:
            self.reverse_event('select', {'path': path})

    def navigate(self, path):
        self.path = path
        self.verify_path()
        self.refresh()

    def on_button(self, button=None):
        self.reverse_event('select', {'path': None})

########NEW FILE########
__FILENAME__ = controls_inputs
import calendar
import datetime
import os
import time

from ajenti.api import *
from ajenti.ui import p, UIElement, on


@p('value', default='', bindtypes=[str, unicode, int, long])
@p('readonly', type=bool, default=False)
@p('type', default='text')
@plugin
class TextBox (UIElement):
    typeid = 'textbox'


@p('value', default='', bindtypes=[str, unicode, int, long])
@plugin
class PasswordBox (UIElement):
    typeid = 'passwordbox'


@p('value', default='', type=int, bindtypes=[str, unicode, int, long])
@plugin
class DateTime (UIElement):
    typeid = 'datetime'

    @property
    def dateobject(self):
        if self.value:
            return datetime.fromtimestamp(self.value)

    @dateobject.setter
    def dateobject__set(self, value):
        if value:
            self.value = calendar.timegm(value.timetuple())
        else:
            self.value = None


@p('value', default='', bindtypes=[str, unicode])
@p('icon', default=None)
@p('placeholder', default=None)
@plugin
class Editable (UIElement):
    typeid = 'editable'


@p('text', default='')
@p('value', default=False, bindtypes=[bool])
@plugin
class CheckBox (UIElement):
    typeid = 'checkbox'


@p('labels', default=[], type=list)
@p('values', default=[], type=list, public=False)
@p('value', bindtypes=[object], public=False)
@p('index', default=0, type=int)
@p('server', default=False, type=bool)
@plugin
class Dropdown (UIElement):
    typeid = 'dropdown'

    def value_get(self):
        if self.index < len(self.values):
            try:
                return self.values[self.index]
            except TypeError:
                return None
        return None

    def value_set(self, value):
        if value in self.values:
            self.index = self.values.index(value)
        else:
            self.index = 0

    value = property(value_get, value_set)


@p('labels', default=[], type=list)
@p('values', default=[], type=list)
@p('separator', default=None, type=str)
@p('value', default='', bindtypes=[str, unicode])
@plugin
class Combobox (UIElement):
    typeid = 'combobox'


@p('target', type=str)
@plugin
class FileUpload (UIElement):
    typeid = 'fileupload'


@p('active', type=int)
@p('length', type=int)
@plugin
class Paging (UIElement):
    typeid = 'paging'


@p('value', default='', bindtypes=[str, unicode])
@p('directory', default=False, type=bool)
@p('type', default='text')
@plugin
class Pathbox (UIElement):
    typeid = 'pathbox'

    def init(self, *args, **kwargs):
        if self.directory:
            self.dialog = self.ui.create('opendirdialog')
        else:
            self.dialog = self.ui.create('openfiledialog')
        self.append(self.dialog)
        self.dialog.id = 'dialog'
        self.dialog.visible = False

    def on_start(self):
        self.find('dialog').navigate(os.path.split(self.value or '')[0] or '/')
        self.find('dialog').visible = True

    @on('dialog', 'select')
    def on_select(self, path=None):
        self.find('dialog').visible = False
        if path:
            self.value = path

########NEW FILE########
__FILENAME__ = controls_simple
from ajenti.api import *
from ajenti.ui import p, UIElement


@p('text', default='', bindtypes=[str, unicode, int, float])
@plugin
class Label (UIElement):
    typeid = 'label'


@p('text', default='', bindtypes=[str, unicode, int])
@plugin
class Tooltip (UIElement):
    typeid = 'tooltip'


@p('icon', default=None, bindtypes=[str, unicode])
@plugin
class Icon (UIElement):
    typeid = 'icon'


@p('text', default='', bindtypes=[str, unicode])
@p('icon', default=None)
@p('warning', default=None)
@plugin
class Button (UIElement):
    typeid = 'button'


@p('text', default='', bindtypes=[str, unicode])
@p('icon', default=None)
@p('pressed', default=False, type=bool)
@plugin
class ToggleButton (UIElement):
    typeid = 'togglebutton'


@p('width', default=None)
@p('value', default=0, type=float, bindtypes=[int, float])
@plugin
class ProgressBar (UIElement):
    typeid = 'progressbar'

########NEW FILE########
__FILENAME__ = main
from base64 import b64encode
import catcher
import gevent
import gevent.coros
import json
import logging
import requests
import traceback
import zlib

import ajenti
from ajenti.api import *
from ajenti.api.http import *
from ajenti.api.sensors import Sensor
from ajenti.licensing import Licensing
from ajenti.middleware import AuthenticationMiddleware
from ajenti.plugins import manager
from ajenti.profiler import *
from ajenti.users import PermissionProvider, UserManager, SecurityError
from ajenti.ui import *
from ajenti.util import make_report
import ajenti.feedback

from api import SectionPlugin


@plugin
class MainServer (BasePlugin, HttpPlugin):
    @url('/')
    def handle_index(self, context):
        context.add_header('Content-Type', 'text/html')
        if context.session.identity is None:
            context.respond_ok()
            html = self.open_content('static/auth.html').read()
            return html % {
                'license': json.dumps(Licensing.get().get_license_status()),
                'error': json.dumps(context.session.data.pop('login-error', None)),
            }
        context.respond_ok()
        return self.open_content('static/index.html').read()

    @url('/ajenti:auth')
    def handle_auth(self, context):
        username = context.query.getvalue('username', '')
        password = context.query.getvalue('password', '')
        if not AuthenticationMiddleware.get().try_login(
            context, username, password, env=context.env,
        ):
            context.session.data['login-error'] = _('Invalid login or password')
            gevent.sleep(3)
        return context.redirect('/')

    @url('/ajenti:auth-persona')
    def handle_persona_auth(self, context):
        assertion = context.query.getvalue('assertion', None)
        audience = context.query.getvalue('audience', None)
        if not assertion:
            return self.context.respond_forbidden()

        data = {
            'assertion': assertion,
            'audience': audience,
        }

        resp = requests.post('https://verifier.login.persona.org/verify', data=data, verify=True)

        if resp.ok:
            verification_data = json.loads(resp.content)
            if verification_data['status'] == 'okay':
                context.respond_ok()
                email = verification_data['email']
                for user in ajenti.config.tree.users.values():
                    if user.email == email:
                        AuthenticationMiddleware.get().login(context, user.name)
                        break
                else:
                    context.session.data['login-error'] = _('Email "%s" is not associated with any user') % email
                return ''
        context.session.data['login-error'] = _('Login failed')
        return context.respond_not_found()

    @url('/ajenti:logout')
    def handle_logout(self, context):
        AuthenticationMiddleware.get().logout(context)
        context.session.destroy()
        return context.redirect('/')


@plugin
class MainSocket (SocketPlugin):
    name = '/stream'
    ui = None

    def on_connect(self):
        self.compression = 'zlib'
        self.__updater_lock = gevent.coros.RLock()

        # Inject into session
        self.request.session.endpoint = self

        # Inject the context methods
        self.context.notify = self.send_notify
        self.context.launch = self.launch
        self.context.endpoint = self

        if not 'ui' in self.request.session.data:
            # This is a newly created session
            ui = UI.new()

            self.request.session.data['ui'] = ui
            ui.root = MainPage.new(ui)
            ui.root.username = self.request.session.identity
            sections_root = SectionsRoot.new(ui)

            for e in sections_root.startup_crashes:
                self.send_crash(e)

            ui.root.append(sections_root)
            ui._sections = sections_root.children
            ui._sections_root = sections_root

        self.ui = self.request.session.data['ui']
        self.send_init()
        self.send_ui()
        self.spawn(self.ui_watcher)

    def on_message(self, message):
        if not self.ui:
            return
        self.spawn(self.handle_message, message)

    def handle_message(self, message):
        try:
            with self.__updater_lock:
                if message['type'] == 'ui_update':
                    # UI updates arrived
                    profile_start('Total')
                    # handle content updates first, before events affect UI
                    for update in message['content']:
                        if update['type'] == 'update':
                            # Property change
                            profile_start('Handling updates')
                            els = self.ui.root.nearest(
                                lambda x: x.uid == update['uid'],
                                exclude=lambda x: x.parent and not x.parent.visible,
                                descend=False,
                            )
                            if len(els) == 0:
                                continue
                            el = els[0]
                            for k, v in update['properties'].iteritems():
                                setattr(el, k, v)
                            profile_end('Handling updates')
                    for update in message['content']:
                        if update['type'] == 'event':
                            # Element event emitted
                            profile_start('Handling event')
                            self.ui.dispatch_event(update['uid'], update['event'], update['params'])
                            profile_end('Handling event')
                    if self.ui.has_updates():
                        # If any updates happened due to event handlers, send these immediately
                        self.ui.clear_updates()
                        self.send_ui()
                    else:
                        # Otherwise just ACK
                        self.send_ack()
                    profile_end('Total')
                    if ajenti.debug:
                        self.send_debug()
        except SecurityError, e:
            self.send_security_error()
        except Exception, e:
            catcher.backup(e)
            traceback.print_exc()
            e.traceback = traceback.format_exc(e)
            self.send_crash(e)

    def send_init(self):
        data = {
            'version': ajenti.version,
            'platform': ajenti.platform,
            'hostname': Sensor.find('hostname').value(),
            'session': self.context.session.id,
            'feedback': ajenti.config.tree.enable_feedback,
            'edition': ajenti.edition,
            'compression': self.compression,
        }
        self.emit('init', json.dumps(data))

    def send_ui(self):
        profile_start('Rendering')
        data = json.dumps(self.ui.render())
        profile_end('Rendering')
        if self.compression == 'zlib':
            data = b64encode(zlib.compress(data, 4)[2:-4])
        if self.compression == 'lzw':
            data = b64encode(self.__compress_lzw(data))
        self.emit('ui', data)

    def __compress_lzw(self, data):
        dict = {}
        out = []
        phrase = data[0]
        code = 256
        for i in range(1, len(data)):
            currChar = data[i]
            if dict.get(phrase + currChar, None):
                phrase += currChar
            else:
                out.append(dict[phrase] if (len(phrase) > 1) else ord(phrase[0]))
                dict[phrase + currChar] = code
                code += 1
                phrase = currChar
        out.append(dict[phrase] if (len(phrase) > 1) else ord(phrase[0]))
        res = ''
        for code in out:
            if code >= 256:
                res += chr(0)
                res += chr(code / 256)
            res += chr(code % 256)
        return res

    def send_ack(self):
        self.emit('ack')

    def send_progress(self, msg=''):
        self.emit('progress-message', msg)
        gevent.sleep(0)

    def send_update_request(self):
        self.emit('update-request')

    def send_security_error(self):
        self.emit('security-error', '')

    def send_open_tab(self, url, title='new tab'):
        self.emit('openTab', json.dumps({'url': url, 'title': title}))

    def send_close_tab(self, url):
        self.emit('closeTab', json.dumps({'url': url}))

    def send_debug(self):
        profiles = get_profiles()
        logging.debug(repr(profiles))
        data = {
            'profiles': profiles
        }
        self.emit('debug', json.dumps(data))

    def send_crash(self, exc):
        if not hasattr(exc, 'traceback'):
            traceback.print_exc()
            exc.traceback = traceback.format_exc(exc)
        data = {
            'message': str(exc),
            'traceback': exc.traceback,
            'report': make_report(exc)
        }
        data = json.dumps(data)
        self.emit('crash', data)

    def send_notify(self, type, text):
        self.emit('notify', json.dumps({'type': type, 'text': text}))

    def switch_tab(self, tab):
        self.ui._sections_root.on_switch(tab.uid)

    def launch(self, intent, **data):
        for section in self.ui._sections:
            for handler in section._intents:
                if handler == intent:
                    section._intents[handler](**data)
                    return

    def get_section(self, cls):
        for section in self.ui._sections:
            if section.__class__ == cls:
                return section

    def ui_watcher(self):
        # Sends UI updates periodically
        while True:
            if self.__updater_lock:
                if self.ui.has_updates():
                    self.send_update_request()
                    gevent.sleep(0.5)
            gevent.sleep(0.2)


@plugin
class SectionPermissions (PermissionProvider):
    def get_name(self):
        return _('Section access')

    def get_permissions(self):
        # Generate permission set on-the-fly
        return sorted([
            ('section:%s' % x.__class__.__name__, (_(x.category) or 'Ajenti') + ' | ' + _(x.title))
            for x in SectionPlugin.get_instances()
        ], key=lambda x: x[1])


@p('username')
@plugin
class MainPage (UIElement, BasePlugin):
    typeid = 'main:page'


@p('name')
@plugin
class SectionsCategory (UIElement):
    typeid = 'main:sections_category'


@p('is_empty', type=bool)
@plugin
class SectionsRoot (UIElement):
    typeid = 'main:sections_root'
    category_order = {
        '': 0,
        'System': 50,
        'Web': 60,
        'Tools': 70,
        'Software': 80,
        'Other': 99
    }

    def init(self):
        self.categories = {}
        self.startup_crashes = []

        profile_start('Starting plugins')

        self.is_empty = True
        for cls in SectionPlugin.get_classes():
            try:
                UserManager.get().require_permission(self.context, 'section:%s' % cls.__name__)

                try:
                    profile_start('Starting %s' % cls.__name__)
                    cat = cls.new(self.ui)
                    cat.clsname = cls.classname
                    profile_end()
                    self.append(cat)
                    self.is_empty = False
                except SecurityError:
                    pass
                except Exception, e:
                    catcher.backup(e)
                    traceback.print_exc()
                    e.traceback = traceback.format_exc(e)
                    self.startup_crashes.append(e)
            except SecurityError:
                pass

        profile_end()

        def category_order(x):
            order = 98
            if x.category in self.category_order:
                order = self.category_order[x.category]
            return (order, x.order, x.title)

        self.children = sorted(self.children, key=category_order)
        if len(self.children) > 0:
            self.on_switch(self.children[0].uid)

    def on_switch(self, uid):
        for child in self.children:
            child.active = child.uid == uid
            child.visible = child.active
            if child.active:
                if child._first_page_load:
                    child.broadcast('on_first_page_load')
                    child._first_page_load = False
                child.broadcast('on_page_load')
        self.invalidate()

########NEW FILE########
__FILENAME__ = passwd
import ajenti
from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.users import UserManager


@plugin
class PasswordChangeSection (SectionPlugin):
    def init(self):
        self.title = _('Password')
        self.icon = 'lock'
        self.category = ''
        self.order = 51
        self.append(self.ui.inflate('main:passwd-main'))

    @on('save', 'click')
    def save(self):
        new_password = self.find('new-password').value
        if new_password != self.find('new-password-2').value:
            self.context.notify('error', _('Passwords don\'t match'))
            return
        old_password = self.find('old-password').value
        if not UserManager.get().check_password(self.context.session.identity, old_password) or not new_password or not old_password:
            self.context.notify('error', _('Incorrect password'))
            return
        UserManager.get().set_password(self.context.session.identity, new_password)
        ajenti.config.save()
        self.context.notify('info', _('Password changed'))

########NEW FILE########
__FILENAME__ = api
import subprocess
from ajenti.api import *


class RAIDDevice (object):
    def __init__(self):
        self.name = ''
        self.up = False
        self.failed = False
        self.index = 0


class RAIDArray (object):
    def __init__(self):
        self.id = ''
        self.name = ''
        self.level = ''
        self.size = 0
        self.state = ''
        self.disks = []


class RAIDAdapter (object):
    def __init__(self):
        self.id = ''
        self.name = ''
        self.arrays = []


@plugin
class RAIDManager (BasePlugin):
    cli_path = '/opt/MegaRAID/MegaCli/MegaCli'

    def __init__(self):
        self.refresh()

    def refresh(self):
        self.adapters = []

        ll = subprocess.check_output([self.cli_path, '-LDPDInfo', '-aall']).splitlines()
        #ll = open('mraid.txt').read().splitlines()
        current_adapter = None
        current_array = None
        current_disk = None
        while ll:
            l = ll.pop(0)
            if l.startswith('Adapter'):
                current_adapter = RAIDAdapter()
                self.adapters.append(current_adapter)
                current_array = None
                current_disk = None
                current_adapter.id = l.split('#')[1].strip()
                continue
            if l.startswith('Virtual Drive'):
                current_array = RAIDArray()
                current_adapter.arrays.append(current_array)
                current_disk = None
                current_array.id = l.split()[2]
                continue
            if l.startswith('PD:'):
                current_disk = RAIDDevice()
                current_array.disks.append(current_disk)
                current_disk.id = l.split()[1]
            if ':' in l:
                k, v = l.split(':', 1)
                k = k.strip().lower().replace(' ', '_')
                v = v.strip()
                o = current_disk or current_array or current_adapter
                setattr(o, k, v)

    def find_array(self, name):
        for a in self.adapters:
            for arr in a.arrays:
                if arr.name == name:
                    return arr

    def list_arrays(self):
        for a in self.adapters:
            for arr in a.arrays:
                yield arr.name

########NEW FILE########
__FILENAME__ = main
from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder

from reconfigure.configs import ResolvConfig
from reconfigure.items.resolv import ItemData

from api import RAIDManager


@plugin
class RAID (SectionPlugin):
    def init(self):
        self.title = 'LSI MegaRAID'
        self.icon = 'hdd'
        self.category = _('System')

        self.append(self.ui.inflate('megaraid:main'))

        self.mgr = RAIDManager.get()
        self.binder = Binder(None, self)

    def on_page_load(self):
        self.refresh()

    def refresh(self):
        self.mgr.refresh()
        self.binder.setup(self.mgr).populate()

########NEW FILE########
__FILENAME__ = widget
from ajenti.api import plugin
from ajenti.plugins.dashboard.api import ConfigurableWidget

from api import RAIDManager


@plugin
class LSIWidget (ConfigurableWidget):
    name = 'LSI MegaRAID'
    icon = 'hdd'

    def on_prepare(self):
        self.mgr = RAIDManager.get()
        self.append(self.ui.inflate('megaraid:widget'))

    def on_start(self):
        self.mgr.refresh()
        self.find('variant').text = self.config['variant']
        arr = self.mgr.find_array(self.config['variant'])
        if arr:
            self.find('value').text = arr.state

    def create_config(self):
        return {'variant': ''}

    def on_config_start(self):
        self.mgr.refresh()
        lst = list(self.mgr.list_arrays())
        v_list = self.dialog.find('variant')
        v_list.labels = lst
        v_list.values = lst
        v_list.value = self.config['variant']

    def on_config_save(self):
        self.config['variant'] = self.dialog.find('variant').value

########NEW FILE########
__FILENAME__ = widget
import os
import socket

from ajenti.api import plugin
from ajenti.api.sensors import Sensor
from ajenti.plugins.dashboard.api import DashboardWidget
from ajenti.util import str_fsize


@plugin
class MemcacheSensor (Sensor):
    id = 'memcache'
    timeout = 5

    def measure(self, variant=None):
        sock_path = '/var/run/memcached.sock'
        if os.path.exists(sock_path):
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(sock_path)
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('127.0.0.1', 11211))
        s.send('stats\r\n')
        data = s.recv(10240)
        s.close()
        d = dict([
            l.split()[1:]
            for l in data.splitlines() if len(l.split()) == 3
        ])
        return (int(d['bytes']), int(d['limit_maxbytes']))


@plugin
class MemcachedWidget (DashboardWidget):
    name = _('Memcache memory usage')
    icon = 'tasks'

    def init(self):
        self.sensor = Sensor.find('memcache')
        self.append(self.ui.inflate('memcache:widget'))
        value = self.sensor.value()
        self.find('value').text = str_fsize(value[0])
        self.find('progress').value = 1.0 * value[0] / value[1]

########NEW FILE########
__FILENAME__ = client
from ajenti.api import *

from BeautifulSoup import BeautifulSoup
import requests


@plugin
class MuninClient (BasePlugin):
    default_classconfig = {
        'username': 'username',
        'password': '123',
        'prefix': 'http://localhost:8080/munin'
    }

    classconfig_root = True

    def init(self):
        self.reset()

    def fetch_domains(self):
        self._domains = []
        s = self._fetch('/')
        ds = s.findAll('span', 'domain')
        for d in ds:
            domain = MuninDomain()
            domain.name = str(d.a.string)
            hs = d.parent.findAll('span', 'host')
            for h in hs:
                host = MuninHost(self)
                host.name = str(h.a.string)
                host.domain = domain
                domain.hosts.append(host)
            self._domains.append(domain)

    @property
    def domains(self):
        if self._domains is None:
            self.fetch_domains()
        return self._domains

    def reset(self):
        self._domains = None

    def _fetch(self, url):
        req = requests.get(
            self.classconfig['prefix'] + url,
            auth=(self.classconfig['username'], self.classconfig['password']),
            verify=False,
        )
        if req.status_code == 401:
            raise Exception('auth')
        return BeautifulSoup(req.text)


class MuninDomain:
    def __init__(self):
        self.name = ''
        self.hosts = []


class MuninHost:
    def __init__(self, client):
        self.name = ''
        self._client = client
        self._graphs = None

    @property
    def graphs(self):
        if self._graphs is None:
            s = self._client._fetch('/%s/%s/' % (self.domain.name, self.name))
            gs = [x.a for x in s.findAll('div', 'lighttext')]
            new_content = s.findAll('div', id='content')
            if new_content:
                gs += new_content[0].findAll('a')

            self._graphs = []
            have_graphs = []
            for g in gs:
                graph = MuninGraph()
                graph.name = g['href'].split('/')[0] if '/' in g['href'] else g['href'].split('.')[0]
                graph.full_name = str(g.string or g.img['alt'])
                graph.host = self
                graph.url = '/%s/%s/%s-' % (self.domain.name, self.name, graph.name)
                if not graph.name in have_graphs:
                    self._graphs.append(graph)
                have_graphs.append(graph.name)
        return self._graphs


class MuninGraph:
    def __init__(self):
        self.name = ''
        self.full_name = ''
        self.url = ''

########NEW FILE########
__FILENAME__ = main
from ajenti.api import *
from ajenti.api.http import HttpPlugin, url
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on, UIElement, p
from ajenti.ui.binder import Binder

import requests
import urllib2

from client import MuninClient
from widget import MuninWidget


@plugin
class Munin (SectionPlugin):
    def init(self):
        self.title = 'Munin'
        self.icon = 'stethoscope'
        self.category = _('Software')
        self.append(self.ui.inflate('munin:main'))

        def post_graph_bind(o, c, i, u):
            for plot in u.nearest(lambda x: x.typeid == 'munin:plot'):
                plot.on('widget', self.on_add_widget, i)

        self.find('graphs').post_item_bind = post_graph_bind

        self.munin_client = MuninClient.get()
        self.binder = Binder(None, self)

    def on_page_load(self):
        self.refresh()

    def on_add_widget(self, graph, url=None, period=None):
        self.context.launch('dashboard-add-widget', cls=MuninWidget, config={'url': url, 'period': period})

    def refresh(self):
        self.munin_client.reset()
        try:
            self.munin_client.fetch_domains()
        except requests.ConnectionError, e:
            self.find_type('tabs').active = 1
            self.context.notify('error', _('Couldn\'t connect to Munin: %s') % e.message)
        except Exception, e:
            self.find_type('tabs').active = 1
            if e.message == 'auth':
                self.context.notify('error', _('Munin HTTP authentication failed'))
            else:
                raise
        self.binder.setup(self.munin_client).populate()

    @on('save-button', 'click')
    def save(self):
        self.binder.update()
        self.munin_client.save_classconfig()
        self.refresh()
        self.find_type('tabs').active = 0


@plugin
class MuninProxy (HttpPlugin):
    def init(self):
        self.client = MuninClient.get()

    @url('/ajenti:munin-proxy/(?P<url>.+)')
    def get_page(self, context, url):
        if context.session.identity is None:
            context.respond_redirect('/')
        url = urllib2.unquote(url)
        data = requests.get(self.client.classconfig['prefix'] + url,
                auth=(self.client.classconfig['username'], self.client.classconfig['password'])
               ).content
        context.add_header('Content-Type', 'image/png')
        context.respond_ok()
        return data


@p('url', bindtypes=[str, unicode])
@p('period')
@p('widget', type=bool)
@plugin
class MuninPlot (UIElement):
    typeid = 'munin:plot'

########NEW FILE########
__FILENAME__ = widget
from ajenti.api import plugin
from ajenti.plugins.dashboard.api import ConfigurableWidget


@plugin
class MuninWidget (ConfigurableWidget):
    name = 'Munin'
    icon = 'stethoscope'
    hidden = True

    def on_prepare(self):
        self.append(self.ui.inflate('munin:widget'))

    def on_start(self):
        self.find('plot').url = self.config['url']
        if 'period' in self.config:
            self.find('plot').period = self.config['period']

    def create_config(self):
        return {'url': '', 'period': ''}

########NEW FILE########
__FILENAME__ = api
import logging
import subprocess

from ajenti.api import *
from ajenti.plugins.configurator.api import ClassConfigEditor
from ajenti.plugins.db_common.api import Database, User


@plugin
class MySQLClassConfigEditor (ClassConfigEditor):
    title = 'MySQL'
    icon = 'table'

    def init(self):
        self.append(self.ui.inflate('mysql:config'))


@plugin
class MySQLDB (BasePlugin):
    default_classconfig = {'user': 'root', 'password': '', 'hostname': 'localhost'}
    classconfig_editor = MySQLClassConfigEditor

    def query(self, sql, db=''):
        self.host = self.classconfig.get('hostname', None)
        self.username = self.classconfig['user']
        self.password = self.classconfig['password']
        p = subprocess.Popen(
            [
                'mysql',
                '-u' + self.username,
            ] + 
            ([
                '-p' + self.password,
            ] if self.password else []) + 
            [
                '-h', self.host or 'localhost',
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        sql = (('USE %s; ' % db) if db else '') + sql
        logging.debug(sql)
        o, e = p.communicate(sql)
        if p.returncode:
            raise Exception(e)
        return filter(None, o.splitlines()[1:])

    def query_sql(self, db, sql):
        r = []
        for l in self.query(sql + ';', db):
            r.append(l.split('\t'))
        return r

    def query_databases(self):
        r = []
        for l in self.query('SHOW DATABASES;'):
            db = Database()
            db.name = l
            r.append(db)
        return r

    def query_drop(self, db):
        self.query("DROP DATABASE `%s`;" % db.name)

    def query_create(self, name):
        self.query("CREATE DATABASE `%s` CHARACTER SET UTF8;" % name)

    def query_users(self):
        r = []
        for l in self.query('USE mysql; SELECT * FROM user;'):
            u = User()
            u.host, u.name = l.split('\t')[:2]
            r.append(u)
        return r

    def query_create_user(self, user):
        self.query("CREATE USER `%s`@`%s` IDENTIFIED BY '%s'" % (user.name, user.host, user.password))

    def query_drop_user(self, user):
        self.query("DROP USER `%s`@`%s`" % (user.name, user.host))

    def query_grant(self, user, db):
        self.query("GRANT ALL PRIVILEGES ON `%s`.* TO `%s`@`%s`" % (db.name, user.name, user.host))
        self.query("FLUSH PRIVILEGES")

########NEW FILE########
__FILENAME__ = main
from ajenti.api import *
from ajenti.plugins.db_common.api import DBPlugin
from ajenti.util import platform_select

from api import MySQLDB


@plugin
class MySQLPlugin (DBPlugin):
    config_class = MySQLDB

    service_name = platform_select(
        debian='mysql',
        default='mysqld'
    )

    service_buttons = [
        {
            'command': 'reload',
            'text': _('Reload'),
            'icon': 'step-forward',
        }
    ]

    def init(self):
        self.title = 'MySQL'
        self.category = _('Software')
        self.icon = 'table'
        self.db = MySQLDB.get()

    def query_sql(self, db, sql):
        return self.db.query_sql(db, sql)

    def query_databases(self):
        return self.db.query_databases()

    def query_drop(self, db):
        return self.db.query_drop(db)

    def query_create(self, name):
        return self.db.query_create(name)

    def query_users(self):
        return self.db.query_users()

    def query_create_user(self, user):
        return self.db.query_create_user(user)

    def query_drop_user(self, user):
        return self.db.query_drop_user(user)

    def query_grant(self, user, db):
        return self.db.query_grant(user, db)

########NEW FILE########
__FILENAME__ = main
import os

from ajenti.api import *
from ajenti.ui.binder import Binder
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on

from reconfigure.configs import NetatalkConfig
from reconfigure.items.netatalk import ShareData


@plugin
class Netatalk (SectionPlugin):
    config_path = '/etc/afp.conf'

    def init(self):
        self.title = 'Netatalk'
        self.icon = 'folder-close'
        self.category = _('Software')
        self.append(self.ui.inflate('netatalk:main'))

        if not os.path.exists(self.config_path):
            open(self.config_path, 'w').write("[Global]")

        self.binder = Binder(None, self.find('config'))
        self.find('shares').new_item = lambda c: ShareData()
        self.config = NetatalkConfig(path=self.config_path)

    def on_page_load(self):
        self.refresh()

    def refresh(self):
        self.config.load()
        self.binder.setup(self.config.tree).populate()

    @on('save', 'click')
    def on_save(self):
        self.binder.update()
        self.config.save()
        self.refresh()

########NEW FILE########
__FILENAME__ = api
import psutil

from ajenti.api import *
from ajenti.ui import *


@plugin
class NetworkManager (BasePlugin):
    def get_devices(self):
        return psutil.network_io_counters(pernic=True).keys()


@interface
class INetworkConfig (object):
    interfaces = {}

    @property
    def interface_list(self):
        return self.interfaces.values()

    def rescan(self):
        pass

    def save(self):
        pass


@interface
class INetworkConfigBit (object):
    def apply(self):
        pass


@plugin
class NetworkConfigBit (UIElement, INetworkConfigBit):
    cls = 'unknown'
    iface = None
    title = 'Unknown'
    typeid = 'box'


class NetworkInterface(object):
    def __init__(self):
        self.up = False
        self.auto = False
        self.name = ''
        self.devclass = ''
        self.addressing = 'static'
        self.bits = []
        self.params = {'address': '0.0.0.0'}
        self.type = ''
        self.editable = True

    def __getitem__(self, idx):
        if idx in self.params:
            return self.params[idx]
        else:
            return ''

    def __setitem__(self, idx, val):
        self.params[idx] = val

    def add_bits(self, ui):
        for cls in INetworkConfigBit.get_classes():
            if cls.cls in self.bit_classes:
                b = cls.new(ui)
                b.iface = self
                b.refresh()
                self.bits.append(b)

########NEW FILE########
__FILENAME__ = main
from ajenti.api import *
from ajenti.api.sensors import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import *
from ajenti.ui.binder import Binder

from api import *


@plugin
class NetworkPlugin (SectionPlugin):
    platforms = ['debian', 'centos']

    def init(self):
        self.title = _('Network')
        self.icon = 'globe'
        self.category = _('System')
        self.net_config = INetworkConfig.get()

        self.append(self.ui.inflate('network:main'))

        def post_interface_bind(o, c, i, u):
            i.add_bits(self.ui)
            for bit in i.bits:
                u.find('bits').append(self.ui.create(
                    'tab',
                    children=[bit],
                    title=bit.title,
                ))
            u.find('up').on('click', self.on_up, i)
            u.find('down').on('click', self.on_down, i)
            u.find('restart').on('click', self.on_restart, i)
            u.find('ip').text = self.net_config.get_ip(i)

        def post_interface_update(o, c, i, u):
            for bit in i.bits:
                bit.apply()

        self.find('interfaces').post_item_bind = post_interface_bind
        self.find('interfaces').post_item_update = post_interface_update

        self.binder = Binder(None, self)

    def on_page_load(self):
        self.refresh()

    def refresh(self):
        self.net_config.rescan()

        sensor = Sensor.find('traffic')
        for i in self.net_config.interface_list:
            i.tx, i.rx = sensor.value(i.name)

        self.binder.setup(self.net_config).populate()
        return

    def on_up(self, iface=None):
        self.save()
        self.net_config.up(iface)
        self.refresh()

    def on_down(self, iface=None):
        self.save()
        self.net_config.down(iface)
        self.refresh()

    def on_restart(self, iface=None):
        self.save()
        self.on_down(iface)
        self.on_up(iface)

    @on('save', 'click')
    def save(self):
        self.binder.update()
        self.net_config.save()
        self.refresh()
        self.context.notify('info', _('Saved'))

########NEW FILE########
__FILENAME__ = ncs_linux_basic
from ajenti.ui import *
from ajenti.ui.binder import Binder

from api import *


@plugin
class LinuxBasicNetworkConfigSet (NetworkConfigBit):
    cls = 'linux-basic'
    title = 'Basic'

    def init(self):
        self.append(self.ui.inflate('network:bit-linux-basic'))
        self.binder = Binder(None, self)

    def refresh(self):
        self.binder.setup(self.iface).populate()

    def apply(self):
        self.binder.update()

########NEW FILE########
__FILENAME__ = ncs_linux_dhcp
from ajenti.ui import *
from ajenti.ui.binder import Binder

from api import *


@plugin
class LinuxDHCPNetworkConfigSet (NetworkConfigBit):
    cls = 'linux-dhcp'
    title = 'DHCP'

    def init(self):
        self.append(self.ui.inflate('network:bit-linux-dhcp'))
        self.binder = Binder(None, self)

    def refresh(self):
        self.binder.setup(self.iface).populate()

    def apply(self):
        self.binder.update()

########NEW FILE########
__FILENAME__ = ncs_linux_ifupdown
from ajenti.ui import *
from ajenti.ui.binder import Binder

from api import *


@plugin
class LinuxIfUpDownNetworkConfigSet (NetworkConfigBit):
    cls = 'linux-ifupdown'
    title = 'Scripts'

    def init(self):
        self.append(self.ui.inflate('network:bit-linux-ifupdown'))
        self.binder = Binder(None, self)

    def refresh(self):
        self.binder.setup(self.iface).populate()

    def apply(self):
        self.binder.update()

########NEW FILE########
__FILENAME__ = ncs_linux_ipv4
from ajenti.ui import *
from ajenti.ui.binder import Binder

from api import *


@plugin
class LinuxIPv4NetworkConfigSet (NetworkConfigBit):
    cls = 'linux-ipv4'
    title = 'IPv4'

    def init(self):
        self.append(self.ui.inflate('network:bit-linux-ipv4'))
        self.binder = Binder(None, self)

    def refresh(self):
        self.binder.setup(self.iface).populate()

    def apply(self):
        self.binder.update()

########NEW FILE########
__FILENAME__ = nctp_linux
import fcntl
import gevent
import subprocess
import socket
import struct
import re

from ajenti.api import *
from ajenti.ui import *


class LinuxIfconfig (object):
    platforms = ['debian', 'centos']

    def detect_dev_class(self, iface):
        ifname = re.compile('[a-z]+').findall(iface.name)
        if ifname in ['ppp', 'wvdial']:
            return 'ppp'
        if ifname in ['wlan', 'ra', 'wifi', 'ath']:
            return 'wireless'
        if ifname == 'br':
            return 'bridge'
        if ifname == 'tun':
            return 'tunnel'
        if ifname == 'lo':
            return 'loopback'
        if ifname == 'eth':
            return 'ethernet'
        return 'ethernet'

    def detect_iface_bits(self, iface):
        r = ['linux-basic']
        cls = self.detect_dev_class(iface)
        if iface.type == 'inet' and iface.addressing == 'static':
            r.append('linux-ipv4')
        if iface.type == 'inet6' and iface.addressing == 'static':
            r.append('linux-ipv6')
        if iface.addressing == 'dhcp':
            r.append('linux-dhcp')
        if cls == 'ppp':
            r.append('linux-ppp')
        if cls == 'wireless':
            r.append('linux-wlan')
        if cls == 'bridge':
            r.append('linux-bridge')
        if cls == 'tunnel':
            r.append('linux-tunnel')

        r.append('linux-ifupdown')
        return r

    def up(self, iface):
        subprocess.call(['ifup', iface.name])
        gevent.sleep(1)

    def down(self, iface):
        subprocess.call(['ifdown', iface.name])
        gevent.sleep(1)

    def get_ip(self, iface):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', iface.name[:15]))[20:24])
        except IOError:
            return None

########NEW FILE########
__FILENAME__ = nc_centos
import os
import subprocess

from ajenti.api import *

from api import *
from nctp_linux import *


optionmap = {
    'IPADDR': 'address',
    'NETMASK': 'netmask',
    'GATEWAY': 'gateway',
    'BROADCAST': 'broadcast',
    'MACADDR': 'hwaddr',
}


@plugin
class CentosNetworkConfig (LinuxIfconfig, INetworkConfig):
    platforms = ['centos']

    interfaces = None

    classes = {
        'none': ('inet', 'static'),
        'dhcp': ('inet', 'dhcp'),
        'loopback': ('inet', 'loopback')
    }

    def __init__(self):
        self.rescan()

    def rescan(self):
        self.interfaces = {}

        for ifcf in os.listdir('/etc/sysconfig/network-scripts/'):
            if ifcf.startswith('ifcfg-'):
                ifcn = ifcf[6:]
                with open('/etc/sysconfig/network-scripts/' + ifcf, 'r') as f:
                    ss = f.read().splitlines()
                    d = {}
                    for s in ss:
                        try:
                            k = s.split('=', 1)[0].strip('\t "\'')
                            v = s.split('=', 1)[1].strip('\t "\'')
                            d[k] = v
                        except:
                            pass

                    m = 'loopback'
                    c = 'inet'
                    try:
                        if 'BOOTPROTO' in d:
                            m = d['BOOTPROTO']
                        c, m = self.classes[m]
                    except:
                        pass

                    e = NetworkInterface()
                    e.name = ifcn
                    self.interfaces[ifcn] = e
                    self.interfaces[ifcn].auto = 'yes' in d.get('ONBOOT', 'no')
                    e.type = c
                    e.addressing = m
                    for k in d:
                        if k == 'BOOTPROTO':
                            pass
                        elif k in optionmap:
                            e.params[optionmap[k]] = d[k]
                        else:
                            e.params[k] = d[k]

                    e.devclass = self.detect_dev_class(e)
                    try:
                        e.up = 'UP' in subprocess.check_output(['ifconfig', e.name])
                    except:
                        e.up = False
                    e.bit_classes = self.detect_iface_bits(e)

    def save(self):
        for i in self.interfaces:
            with open('/etc/sysconfig/network-scripts/ifcfg-' + i, 'w') as f:
                self.save_iface(self.interfaces[i], f)
        return

    def save_iface(self, iface, f):
        iface.params['ONBOOT'] = 'yes' if iface.auto else 'no'
        for x in self.classes:
            if self.classes[x] == (iface.type, iface.addressing):
                f.write('BOOTPROTO="' + x + '"\n')

        for x in iface.params:
            if not iface.params[x]:
                continue
            fnd = False
            for k in optionmap:
                if optionmap[k] == x:
                    f.write(k + '="' + iface.params[x] + '"\n')
                    fnd = True
            if not fnd:
                f.write(x + '="' + iface.params[x] + '"\n')

########NEW FILE########
__FILENAME__ = nc_debian
import subprocess

from ajenti.api import *

from api import *
from nctp_linux import *


@plugin
class DebianNetworkConfig (LinuxIfconfig, INetworkConfig):
    platforms = ['debian']

    interfaces = None

    def __init__(self):
        self.rescan()

    def rescan(self):
        self.interfaces = {}

        try:
            f = open('/etc/network/interfaces')
            ss = f.read().splitlines()
            f.close()
        except IOError, e:
            return

        auto = []

        while len(ss) > 0:
            line = ss[0].strip(' \t\n')
            if (len(line) > 0 and not line[0] == '#'):
                a = line.split(' ')
                for s in a:
                    if s == '':
                        a.remove(s)
                if (a[0] == 'auto'):
                    auto.append(a[1])
                elif (a[0] == 'allow-hotplug'):
                    pass
                elif (a[0] == 'iface'):
                    tmp = NetworkInterface()
                    tmp.addressing = a[3]
                    tmp.type = a[2]
                    e = self.get_iface(a[1], self.detect_iface_bits(tmp))
                    del tmp
                    e.type = a[2]
                    e.addressing = a[3]
                    e.devclass = self.detect_dev_class(e)
                    try:
                        e.up = 'UP' in subprocess.check_output(['ifconfig', e.name])
                    except:
                        e.up = False
                else:
                    e.params[a[0]] = ' '.join(a[1:])
            if len(ss) > 1:
                ss = ss[1:]
            else:
                ss = []

        for x in auto:
            if x in self.interfaces:
                self.interfaces[x].auto = True

    def get_iface(self, name, bits):
        if not name in self.interfaces:
            self.interfaces[name] = NetworkInterface()
            self.interfaces[name].bit_classes = bits
            self.interfaces[name].name = name
        return self.interfaces[name]

    def save(self):
        f = open('/etc/network/interfaces', 'w')
        for i in self.interfaces:
            self.save_iface(self.interfaces[i], f)
        f.close()
        return

    def save_iface(self, iface, f):
        if iface.auto:
            f.write('auto ' + iface.name + '\n')
        f.write('iface %s %s %s\n' % (iface.name, iface.type, iface.addressing))
        for x in iface.params:
            if iface.params[x]:
                f.write('\t%s %s\n' % (x, iface.params[x]))
        f.write('\n')

########NEW FILE########
__FILENAME__ = widget
import psutil
import time

from ajenti.api import plugin
from ajenti.api.sensors import Sensor
from ajenti.plugins.dashboard.api import ConfigurableWidget
from ajenti.util import str_fsize

from api import NetworkManager


@plugin
class TrafficSensor (Sensor):
    id = 'traffic'
    timeout = 5

    def get_variants(self):
        return NetworkManager.get().get_devices()

    def measure(self, device):
        try:
            v = psutil.network_io_counters(pernic=True)[device]
        except KeyError:
            return (0, 0)
        return (v.bytes_sent, v.bytes_recv)


@plugin
class ImmediateTXSensor (Sensor):
    id = 'immediate-tx'
    timeout = 5

    def init(self):
        self.last_tx = {}
        self.last_time = {}

    def get_variants(self):
        return psutil.network_io_counters(pernic=True).keys()

    def measure(self, device):
        try:
            v = psutil.network_io_counters(pernic=True)[device]
        except KeyError:
            return 0
        r = (v.bytes_sent, v.bytes_recv)
        if not self.last_tx.get(device, None):
            self.last_tx[device] = r[0]
            self.last_time[device] = time.time()
            return 0
        else:
            d = (r[0] - self.last_tx[device]) / (1.0 * time.time() - self.last_time[device])
            self.last_tx[device] = r[0]
            self.last_time[device] = time.time()
            return d


@plugin
class ImmediateRXSensor (Sensor):
    id = 'immediate-rx'
    timeout = 5

    def init(self):
        self.last_rx = {}
        self.last_time = {}

    def get_variants(self):
        return psutil.network_io_counters(pernic=True).keys()

    def measure(self, device):
        try:
            v = psutil.network_io_counters(pernic=True)[device]
        except KeyError:
            return 0
        r = (v.bytes_sent, v.bytes_recv)
        if not self.last_rx.get(device, None):
            self.last_rx[device] = r[1]
            self.last_time[device] = time.time()
            return 0
        else:
            d = (r[1] - self.last_rx[device]) / (1.0 * time.time() - self.last_time[device])
            self.last_rx[device] = r[1]
            self.last_time[device] = time.time()
            return d


@plugin
class ImmediateTrafficWidget (ConfigurableWidget):
    name = _('Immediate Traffic')
    icon = 'exchange'

    def on_prepare(self):
        self.sensor = Sensor.find('traffic')
        self.sensor_tx = Sensor.find('immediate-tx')
        self.sensor_rx = Sensor.find('immediate-rx')
        self.append(self.ui.inflate('network:widget'))

    def on_start(self):
        self.find('device').text = self.config['device']
        self.find('up').text = str_fsize(self.sensor_tx.value(self.config['device'])) + '/s'
        self.find('down').text = str_fsize(self.sensor_rx.value(self.config['device'])) + '/s'

    def create_config(self):
        return {'device': ''}

    def on_config_start(self):
        device_list = self.dialog.find('device')
        lst = self.sensor.get_variants()
        device_list.labels = lst
        device_list.values = lst
        device_list.value = self.config['device']

    def on_config_save(self):
        self.config['device'] = self.dialog.find('device').value


@plugin
class TrafficWidget (ConfigurableWidget):
    name = _('Traffic')
    icon = 'exchange'

    def on_prepare(self):
        self.sensor = Sensor.find('traffic')
        self.append(self.ui.inflate('network:widget'))

    def on_start(self):
        self.find('device').text = self.config['device']
        u, d = self.sensor.value(self.config['device'])
        self.find('up').text = str_fsize(u)
        self.find('down').text = str_fsize(d)

    def create_config(self):
        return {'device': ''}

    def on_config_start(self):
        device_list = self.dialog.find('device')
        lst = self.sensor.get_variants()
        device_list.labels = lst
        device_list.values = lst
        device_list.value = self.config['device']

    def on_config_save(self):
        self.config['device'] = self.dialog.find('device').value

########NEW FILE########
__FILENAME__ = main
from ajenti.api import *
from ajenti.plugins.webserver_common.api import WebserverPlugin
from ajenti.util import platform_select


@plugin
class Nginx (WebserverPlugin):
    service_name = 'nginx'
    service_buttons = [
        {
            'command': 'force-reload',
            'text': _('Reload'),
            'icon': 'step-forward',
        }
    ]
    hosts_available_dir = platform_select(
        debian='/etc/nginx/sites-available',
        centos='/etc/nginx/conf.d',
        freebsd='/usr/local/etc/nginx/conf.d',
        arch='/etc/nginx/sites-available',
    )
    hosts_enabled_dir = '/etc/nginx/sites-enabled'
    supports_host_activation = platform_select(
        debian=True,
        arch=True,
        default=False,
    )

    template = """server {
    server_name name;
    access_log /var/log/nginx/name.access.log;
    error_log  /var/log/nginx/name.error.log;

    listen 80;

    location / {
        root /var/www/name;
    }

    location ~ \.lang$ {
        include fastcgi_params;
        fastcgi_pass 127.0.0.1:port;
        fastcgi_split_path_info ^()(.*)$;
    }
}
"""

    def init(self):
        self.title = 'NGINX'
        self.category = _('Software')
        self.icon = 'globe'

########NEW FILE########
__FILENAME__ = notepad
import logging
import mimetypes
import os

from ajenti.api import *
from ajenti.plugins.configurator.api import ClassConfigEditor
from ajenti.plugins.main.api import SectionPlugin, intent
from ajenti.ui import on


@plugin
class NotepadConfigEditor (ClassConfigEditor):
    title = _('Notepad')
    icon = 'edit'

    def init(self):
        self.append(self.ui.inflate('notepad:config'))


@plugin
class Notepad (SectionPlugin):
    default_classconfig = {
        'bookmarks': [],
        'root': '/',
    }
    classconfig_editor = NotepadConfigEditor
    classconfig_root = True
    SIZE_LIMIT = 1024 * 1024 * 5

    def init(self):
        self.title = _('Notepad')
        self.icon = 'edit'
        self.category = _('Tools')

        self.append(self.ui.inflate('notepad:main'))

        self.editor = self.find('editor')
        self.list = self.find('list')
        self.opendialog = self.find('opendialog')
        self.savedialog = self.find('savedialog')

        self.opendialog.root = self.savedialog.root = \
            self.classconfig.get('root', None) or '/'
        self.opendialog.navigate(self.opendialog.root)
        self.savedialog.navigate(self.savedialog.root)

        self.controller = Controller.new()

        self.selected = None

    def on_first_page_load(self):
        id = None
        if self.classconfig['bookmarks']:
            for path in self.classconfig['bookmarks']:
                if path:
                    id = self.controller.open(path)
        if id:
            self.select(id)
        else:
            self.on_new()

    def select(self, id):
        if self.selected in self.controller.files:
            self.controller.files[self.selected]['content'] = self.editor.value
        self.selected = id
        self.editor.value = self.controller.files[id]['content']
        self.editor.mode = self.controller.files[id]['mime']
        self.list.empty()
        for id, file in self.controller.files.iteritems():
            item = self.ui.inflate('notepad:listitem')
            item.find('name').text = file['path'] or _('Untitled %i') % id

            item.find('close').on('click', self.on_close, id)
            item.find('close').visible = len(self.controller.files.keys()) > 1
            item.on('click', self.select, id)

            if file['path'] in self.classconfig['bookmarks']:
                item.find('icon').icon = 'tag'
            self.list.append(item)

    @on('new-button', 'click')
    def on_new(self):
        self.select(self.controller.new_item())

    @on('open-button', 'click')
    def on_open(self):
        self.opendialog.show()

    @on('save-button', 'click')
    def on_save(self):
        path = self.controller.files[self.selected]['path']
        if not path:
            self.on_save_as()
        else:
            self.on_save_dialog_select(path)

    @on('save-as-button', 'click')
    def on_save_as(self):
        self.savedialog.show()

    @intent('notepad')
    @on('opendialog', 'select')
    def on_open_dialog_select(self, path=None):
        self.opendialog.visible = False
        if path:
            self.activate()
            if os.stat(path).st_size > self.SIZE_LIMIT:
                self.context.notify('error', 'File is too big')
                return
            self.select(self.controller.open(path))

    @on('savedialog', 'select')
    def on_save_dialog_select(self, path):
        self.savedialog.visible = False
        if path:
            logging.info('[notepad] saving %s' % path)
            self.select(self.selected)
            self.controller.save(self.selected, path)
            self.select(self.selected)
            self.context.notify('info', _('Saved'))

    def on_close(self, id):
        if self.controller.files[id]['path'] in self.classconfig['bookmarks']:
            self.classconfig['bookmarks'].remove(
                self.controller.files[id]['path']
            )
            self.save_classconfig()
        self.controller.close(id)
        self.select(self.controller.files.keys()[0])

    @on('bookmark-button', 'click')
    def on_bookmark(self):
        if not self.controller.files[self.selected]['path'] \
                in self.classconfig['bookmarks']:
            self.classconfig['bookmarks'].append(
                self.controller.files[self.selected]['path']
            )
            self.save_classconfig()
        self.select(self.selected)


@plugin
class Controller (BasePlugin):
    def __init__(self):
        self.files = {}
        self._id = 0

    def new_item(self):
        id = self._id
        self._id += 1
        self.files[id] = {
            'id': id,
            'path': None,
            'content': '',
            'mime': None
        }
        return id

    def open(self, path):
        id = self.new_item()
        self.files[id]['path'] = path
        content = ''
        try:
            content = open(path).read().decode('utf-8')
        except Exception, e:
            self.context.notify('error', str(e))
        self.files[id]['content'] = content
        self.files[id]['mime'] = mimetypes.guess_type(path, strict=False)[0]
        return id

    def save(self, id, path=None):
        path = path or self.files[id]['path']
        self.files[id]['path'] = path
        open(path, 'w').write(self.files[id]['content'])

    def close(self, id):
        del self.files[id]

########NEW FILE########
__FILENAME__ = main
import os

from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder
from ajenti.util import platform_select

from reconfigure.configs import NSDConfig
from reconfigure.items.nsd import ZoneData


@plugin
class NSDPlugin (SectionPlugin):
    def init(self):
        self.title = 'NSD'
        self.icon = 'globe'
        self.category = _('Software')

        self.append(self.ui.inflate('nsd:main'))

        self.config = NSDConfig(path=platform_select(
            default='/etc/nsd3/nsd.conf',
            arch='/etc/nsd/nsd.conf',
        ))

        self.binder = Binder(None, self)
        self.find('zones').new_item = lambda c: ZoneData()

        def post_zone_bind(o, c, i, u):
            path = i.file
            if not path.startswith('/'):
                path = '/etc/nsd3/' + path
            exists = os.path.exists(path)
            u.find('no-file').visible = not exists
            u.find('file').visible = exists
            if exists:
                u.find('editor').value = open(path).read()

            def on_save_zone():
                open(path, 'w').write(u.find('editor').value)
                self.context.notify('info', _('Zone saved'))

            def on_create_zone():
                open(path, 'w').write("""$TTL    604800
@       IN      SOA     ns. root.ns. (
                              1         ; Serial
                         604800         ; Refresh
                          86400         ; Retry
                        2419200         ; Expire
                         604800 )       ; Negative Cache TTL
;
@                   IN      NS      ns.
example.com.        IN      A       127.0.0.1
example.com.        IN      AAAA    ::1
""")
                post_zone_bind(o, c, i, u)

            u.find('save-zone').on('click', on_save_zone)
            u.find('create-zone').on('click', on_create_zone)
        self.find('zones').post_item_bind = post_zone_bind

    def on_page_load(self):
        self.refresh()

    def refresh(self):
        if not os.path.exists(self.config.origin):
            self.context.notify(
                'error',
                _('%s does not exist') % self.config.origin
            )
            return
        self.config.load()
        self.binder.setup(self.config.tree).populate()

    @on('save', 'click')
    def save(self):
        self.binder.update()
        self.config.save()
        self.refresh()
        self.context.notify('info', _('Saved'))

########NEW FILE########
__FILENAME__ = backend
# coding=utf-8
from ajenti.api import plugin, BasePlugin
from ajenti.plugins.configurator.api import ClassConfigEditor

import manager


@plugin
class OpenVPNClassConfigEditor (ClassConfigEditor):
    title = 'OpenVPN'
    icon = 'globe'

    def init(self):
        self.append(self.ui.inflate('openvpn:config'))


@plugin
class OpenVPNBackend (BasePlugin):
    """
    OpenVPN plugin and widget backend
    @ivar _m: manager instance
    """
    default_classconfig = {'addr': '', 'password': ''}
    classconfig_editor = OpenVPNClassConfigEditor

    def setup(self):
        """
        Initializes instance variables, creates manager instance and tests connection
        @return: Nothing
        """
        # Retrieve configuration settings
        addr = self.classconfig['addr']
        password = self.classconfig['password']
        if not addr:
            raise Exception('No address specified')
        # Check if addr is a "host:port" string
        (host, colon, port) = addr.partition(":")
        try:
            if colon:
                # IPv4/IPv6
                self._m = manager.manager(host=host, port=int(port), password=password)
            else:
                # UNIX Socket
                self._m = manager.manager(path=addr, password=password)
            # Test connection
            self.getpid()
        except Exception, e:
            raise Exception(str(e))

    def _execute(self, func, *args):
        """
        OpenVPN management interface is unable to handle more than one connection.
        This method is used to connect and disconnect (if was not connected manually) every
        time plugin wants to execute a command.
        @param func: Function to call
        @param args: Argument List
        @return: Function result
        """
        if not self._m.connected:
            self._m.connect()
            result = self._execute(func, *args)
            self._m.disconnect()
        else:
            result = func(*args)
        return result

    def connect(self):
        self._m.connect()

    def disconnect(self):
        self._m.disconnect()

    def getstatus(self):
        return self._execute(self._m.status)

    def getstats(self):
        return self._execute(self._m.stats)

    def killbyaddr(self, addr):
        return self._execute(self._m.killbyaddr, addr)

    def restartcond(self):
        return self._execute(self._m.signal, "SIGUSR1")

    def restarthard(self):
        return self._execute(self._m.signal, "SIGHUP")

    def getmessages(self):
        return self._execute(self._m.messages)

    def getpid(self):
        return self._execute(self._m.pid)

########NEW FILE########
__FILENAME__ = main
import time

from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder

from backend import OpenVPNBackend


class State (object):
    pass


class Client (object):
    pass


class Message (object):
    pass


@plugin
class OpenVPN (SectionPlugin):
    def init(self):
        self.title = _('OpenVPN')
        self.icon = 'globe'
        self.category = _('Software')

        self.append(self.ui.inflate('openvpn:main'))

        def disconnect(u, c):
            try:
                self.backend.killbyaddr(u.raddress)
                time.sleep(1)
            except Exception, e:
                self.context.notify('error', e.message)
            self.refresh()

        self.find('clients').delete_item = disconnect

        self.binder = Binder(None, self)
        self.backend = OpenVPNBackend.get()

    def on_page_load(self):
        self.refresh()

    @on('hard-restart', 'click')
    def on_hard_restart(self):
        self.backend.restarthard()
        time.sleep(2)

    @on('soft-restart', 'click')
    def on_soft_restart(self):
        self.backend.restartcond()
        time.sleep(2)

    def refresh(self):
        try:
            self.backend.setup()
        except Exception, e:
            self.context.notify('error', e.message)
            self.context.launch('configure-plugin', plugin=self.backend)
            return

        self.state = State()

        try:
            self.backend.connect()
            self.state.stats = self.backend.getstats()
            self.state.status = self.backend.getstatus()
            self.state.messages = []
            self.state.clients = []
            for d in self.state.status['clients']:
                c = Client()
                c.__dict__.update(d)
                self.state.clients.append(c)
            for d in self.backend.getmessages():
                m = Message()
                m.timestamp, m.flags, m.text = d[:3]
                self.state.messages.append(m)

        except Exception, e:
            self.context.notify('error', e.message)

        self.binder.setup(self.state).populate()

########NEW FILE########
__FILENAME__ = manager
# coding=utf-8
"""
OpenVPN Management API for Python
(http://svn.openvpn.net/projects/openvpn/contrib/dazo/management/management-notes.txt)
"""
__author__ = "Ilya Voronin"
__version__ = "0.1"
__all__ = ['manager']

import socket

CRLF = "\r\n"
PASSWORD_PROMPT = "ENTER PASSWORD:"
STATUS_SUCCESS = "SUCCESS: "
STATUS_ERROR = "ERROR: "
END_MARKER = "END"
NOTIFICATION_PREFIX = ">"


class lsocket(socket.socket):
    """Socket subclass for buffered line-oriented i/o
    @version: 1.0
    @group Line functions: recvl, peekl, sendl, recvuntil
    @group Byte functions: recvb, peekb
    @sort: sendl,recvl,peekl,recvuntil,recvb,peekb
    @ivar _b: Internal read buffer"""
    def __init__(self, *args, **kwargs):
        """Calls superclass constructor and initializes instance variables."""
        super(lsocket, self).__init__(*args, **kwargs)
        self._b = ""

    def sendl(self, line):
        """Adds CRLF to the supplied line and sends it
        @type line: str
        @param line: Line to send"""
        #print "> {0}".format(line)
        self.send(line + CRLF)

    def recvl(self, peek=False):
        """Fills internal buffer with data from socket and returns first found line.
        @type peek: Bool
        @param peek: Keeps line in the buffer if true
        @rtype: str
        @return: First found line"""
        while True:
            i = self._b.find(CRLF)
            if i == -1:
                self._b += self.recv(1024)
            else:
                line = self._b[:i]
                if not peek:
                    self._b = self._b[i+2:]
                #print "{0} {1}".format("?" if peek else ">", line)
                return line

    def recvb(self, count, peek=False):
        """Fills internal buffer with data from socket and returns first B{count} received bytes.
        @type count: int
        @param count: Number of bytes to recieve
        @type peek: Bool
        @param peek: Keeps bytes in the buffer if true
        @rtype: str
        @return: First B{count} received bytes"""
        while True:
            if count > len(self._b):
                self._b += self.recv(count - len(self._b))
            else:
                bytez = self._b[:count]
                if not peek:
                    self._b = self._b[count:]
                #print "{0} {1}".format("?" if peek else ">", bytez)
                return bytez

    def peekb(self, count):
        """Same as peekb(count, peek = True)
        @type count: int
        @param count: Number of bytes to peek
        @rtype: str
        @return: First B{count} received bytes"""
        return self.recvb(count, peek=True)

    def peekl(self):
        """Same as recvl(peek = True)
        @rtype: str
        @return: First found line"""
        return self.recvl(peek=True)

    def recvuntil(self, marker):
        """Returns list of lines received until the line matching the B{marker} was found.
        @type marker: str
        @param marker: Marker
        @rtype: list
        @return: List of strings"""
        lines = []
        while True:
            line = self.recvl()
            if line == marker:
                return lines
            lines.append(line)


class manager(object):
    """OpenVPN Management Client.
    @group Connection: connect,disconnect
    @group Commands: status, stats, killbyaddr, killbycn, signal, messages, pid
    @ivar _host: Hostname or address to connect to
    @ivar _port: Port number to connect to
    @ivar _path: Path to UNIX socket to connect to
    @ivar _password: Password
    @ivar _timeout: Connection timeout
    @ivar _s: Socket object"""
    def __init__(self, host=None, port=None, path=None, password="", timeout=5):
        """Initializes instance variables.
        @type host: str
        @param host: Hostname or address to connect to
        @type port: int
        @param port: Port number to connect to
        @type path: str
        @param path: Path to UNIX socket to connect to
        @type password: str
        @param password: Password
        @type timeout: int
        @param timeout: Connection timeout
        @note: host/port and path should not be specified at the same time """
        assert bool(host and port) ^ bool(path)
        (self._host, self._port, self._path, self._password, self._timeout) = (host, port, path, password, timeout)
        self._s = None

    def connect(self):
        """Initializes and opens a socket. Performs authentication if needed."""
        # UNIX Socket
        if self._path:
            self._s = lsocket(socket.AF_UNIX)
            self._s.settimeout(self._timeout)
            self._s.connect(self._path)
        # IPv4 or IPv6 Socket
        else:
            ai = socket.getaddrinfo(self._host, self._port, 0, socket.SOCK_STREAM)[0]
            self._s = lsocket(ai[0], ai[1], ai[2])
            self._s.settimeout(self._timeout)
            self._s.connect((self._host, self._port))

        # Check if management is password protected
        # We cannot use self.execute(), because OpenVPN uses non-CRLF terminated lines during auth
        if self._s.peekb(len(PASSWORD_PROMPT)) == PASSWORD_PROMPT:
            self._s.recvb(len(PASSWORD_PROMPT))
            self._s.sendl(self._password)
            # Check if OpenVPN asks for password again
            if self._s.peekb(len(PASSWORD_PROMPT)) == PASSWORD_PROMPT:
                self._s.recvb(len(PASSWORD_PROMPT)) # Consume "ENTER PASSWORD:"
                raise Exception("Authentication error")
            else:
                self._s.recvl() # Consume "SUCCESS: " line

    def disconnect(self):
        """Closes a socket."""
        self._s.close()
        self._s = None

    @property
    def connected(self):
        """Returns socket status."""
        return bool(self._s)

    def execute(self, name, *args):
        """Executes command and returns response as a list of lines.
        @type name: str
        @param name: Command name
        @type args: list
        @param args: Argument List
        @rtype: list
        @return: List of strings"""
        cmd = name
        if args:
            cmd += " " + " ".join(args)
        self._s.sendl(cmd)

        # Handle notifications
        while self._s.peekl().startswith(NOTIFICATION_PREFIX):
            self._s.recvl()  # Consume

        # Handle one-line responses
        if self._s.peekl().startswith(STATUS_SUCCESS):
            return [self._s.recvl()[len(STATUS_SUCCESS):]]
        elif self._s.peekl().startswith(STATUS_ERROR):
            raise Exception(self._s.recvl()[len(STATUS_ERROR):])

        # Handle multi-line reponses
        return self._s.recvuntil(END_MARKER)

    def status(self):
        """Executes "status 2" command and returns response as a dictionary.
        @rtype: dict
        @return: Dictionary"""
        status = dict()
        status["clients"] = list()
        # V2 status
        for line in self.execute("status", "2"):
            fields = line.split(",")
            if fields[0] == "TITLE":
                status["title"] = fields[1]
            elif fields[0] == "TIME":
                status["time"] = fields[1]
                status["timeu"] = fields[2]
            elif fields[0] == "HEADER":
                continue
            elif fields[0] == "CLIENT_LIST":
                status["clients"].append(dict(
                    zip(("cn", "raddress", "vaddress", "brecv", "bsent", "connsince", "connsinceu"), fields[1:])
                ))

        return status

    def messages(self):
        """Executes "log all" and returns response as a list of messages.
        Each message is a list of 3 elements: time, flags and text.
        @rtype: list
        @return: List of messages"""
        return map(lambda x: x.split(","), self.execute("log", "all"))

    def killbyaddr(self, addr):
        """Executes "kill IP:port" command and returns response as a string
        @type addr: str
        @param addr: Real address of client to kill (in IP:port format)
        @rtype: str
        @return: Response string"""
        return self.execute("kill", addr)[0]

    def killbycn(self, cn):
        """
        Executes "kill cn" command and returns response as a string
        @type cn: str
        @param cn: Common name of client(s) to kill
        @rtype: str
        @return: Response string
        """
        return self.execute("kill", cn)[0]

    @staticmethod
    def _pgenresp(response):
        """
        Parses generically formatted response (param1=value1,param2=value2,param3=value3)
        @type response: str
        @param response: Response string
        @return: Dictionary
        """
        return dict(map(lambda x: x.split("="), response.split(",")))

    def stats(self):
        """Executes "load-stats" command and returns response as a dictionary:

        >>> print manager.stats()
        {'nclients': '2', 'bytesout': '21400734', 'bytesin': '10129283'}

        @rtype: dict
        @return: Dictionary"""
        return self._pgenresp(self.execute("load-stats")[0])

    def signal(self, signal):
        """Executes "signal" command and returns response as a string.
        @type signal: str
        @param signal: Signal name (SIGHUP, SIGTERM, SIGUSR1 or SIGUSR2)
        @rtype: str
        @return: Response string"""
        assert signal in ["SIGHUP", "SIGTERM", "SIGUSR1", "SIGUSR2"]
        return self.execute("signal", signal)[0]

    def pid(self):
        """Executes "pid" command and returns response as a dictionary.
        @return: Dictionary"""
        return self._pgenresp(self.execute("pid")[0])["pid"]

########NEW FILE########
__FILENAME__ = api
import subprocess

from ajenti.api import *


class PackageInfo (object):
    def __init__(self):
        self.name = ''
        self.state = 'r'
        self.action = None
        self.version = ''
        self.description = ''

    @property
    def _icon(self):
        if self.action == 'i':
            return 'ok-circle'
        if self.action == 'r':
            return 'remove-circle'
        return 'ok' if self.state == 'i' else None


@interface
class PackageManager (BasePlugin):
    def init(self):
        self.upgradeable = []

    def get_lists(self):
        pass

    def refresh(self):
        pass

    def search(self, query):
        return []

    def do(self, actions, callback=lambda: 0):
        pass

########NEW FILE########
__FILENAME__ = installer
import ajenti
from ajenti.api import *
from ajenti.ui import UIElement, p, on
from ajenti.ui.binder import Binder
from ajenti.plugins import BinaryDependency, ModuleDependency


@p('package', default='')
@plugin
class PackageInstaller (UIElement, BasePlugin):
    typeid = 'packages:installer'

    def init(self):
        self.visible = False
        self.append(self.ui.inflate('packages:installer'))
        self.recheck()

    def on_page_load(self):
        self.recheck()

    def recheck(self):
        if not self.package:
            return
        if ajenti.platform in db:
            apps = db[ajenti.platform]
            if self.package in apps:
                self.pkg = db[ajenti.platform][self.package]
                self.visible = True
                Binder(self, self).populate()
            if self.package.startswith('python-module-'):
                d = ModuleDependency(self.package[len('python-module-'):])
            else:
                d = BinaryDependency(self.package)
            if d.satisfied():
                self.visible = False

    @on('install', 'click')
    def on_install(self):
        self.event('activate')
        self.context.launch('install-package', package=self.pkg)


db = {
    'debian': {
        'python-module-BeautifulSoup': 'python-beautifulsoup',
        'supervisord': 'supervisor',
        'hddtemp': 'hddtemp',
        'sensors': 'lm-sensors',
        'munin-cron': 'munin',
        'smbd': 'samba',
        'smartctl': 'smartmontools',
        'squid3': 'squid3',
        'apache2': 'apache2',
        'ctdb': 'ctdb',
        'mysql': 'mysql-server',
        'mysqld_safe': 'mysql-server',
        'psql': 'postgresql',
        'nfsstat': 'nfs-kernel-server',
        'mdadm': 'mdadm',
        'nginx': 'nginx',
        'ipmitool': 'ipmitool',
    },
    'centos': {
        'python-module-BeautifulSoup': 'python-BeautifulSoup',
        'supervisord': 'supervisor',
        'hddtemp': 'hddtemp',
        'sensors': 'lm_sensors',
        'munin-cron': 'munin',
        'smbd': 'samba',
        'smartctl': 'smartmontools',
        'squid3': 'squid',
        'apache2': 'httpd',
        'ctdb': 'ctdb',
        'mysql': 'mysql',
        'mysqld_safe': 'mysql-server',
        'psql': 'postgresql',
        'mdadm': 'mdadm',
        'nginx': 'nginx',
        'ipmitool': 'ipmitool',
        'cron': 'cronie',
    },
    'arch': {
        'python-module-BeautifulSoup': 'python2-beautifulsoup3',
        'supervisord': 'supervisor',
        'hddtemp': 'hddtemp',
        'sensors': 'lm_sensors',
        'munin-cron': 'munin',
        'smbd': 'samba',
        'smartctl': 'smartmontools',
        'squid3': 'squid',
        'apache2': 'apache',
        'mysql': 'mariadb-clients',
        'mysqld_safe': 'mariadb',
        'psql': 'postgresql',
        'mdadm': 'mdadm',
        'nginx': 'nginx',
        'apcaccess': 'apcupsd',
        'openvpn': 'openvpn',
        'nsd': 'nsd',
        'memcached': 'memcached',
        'nfsstat': 'nfs-utils',
        'dhcpd': 'dhcp',
        'named': 'bind',
        'ipmitool': 'ipmitool',
    },
}

########NEW FILE########
__FILENAME__ = main
from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin, intent
from ajenti.ui import on
from ajenti.ui.binder import Binder, CollectionAutoBinding
from ajenti.users import PermissionProvider, restrict
from api import PackageManager, PackageInfo


@plugin
class Packages (SectionPlugin):
    def init(self):
        self.title = _('Packages')
        self.icon = 'gift'
        self.category = _('System')

        self.mgr = PackageManager.get()

        self.append(self.ui.inflate('packages:main'))

        def post_item_bind(object, collection, item, ui):
            ui.find('install').on('click', self.on_install, item)
            ui.find('remove').on('click', self.on_remove, item)
            ui.find('cancel').on('click', self.on_cancel, item)
            ui.find('install').visible = item.action is None
            ui.find('remove').visible = item.action is None and item.state == 'i'
            ui.find('cancel').visible = item.action is not None

        self.find('upgradeable').post_item_bind = post_item_bind
        self.find('search').post_item_bind = post_item_bind
        self.find('pending').post_item_bind = post_item_bind

        self.binder = Binder(None, self.find('bind-root'))
        self.binder_p = Binder(self, self.find('bind-pending'))
        self.binder_s = CollectionAutoBinding([], None, self.find('search')).populate()

        self.pending = {}
        self.installation_running = False
        self.action_queue = []

    def refresh(self):
        self.fill(self.mgr.upgradeable)
        self.binder.setup(self.mgr).populate()
        self.binder_s.unpopulate().populate()
        self._pending = self.pending.values()
        self.binder_p.setup(self).populate()

    def run(self, tasks):
        if self.installation_running:
            self.action_queue += tasks
            self.context.notify('info', _('Enqueueing package installation'))
            return

        self.installation_running = True

        def callback():
            self.installation_running = False
            if self.action_queue:
                self.run(self.action_queue)
                self.action_queue = []
                return
            self.context.notify('info', _('Installation complete!'))

        self.mgr.do(tasks, callback=callback)

    @intent('install-package')
    @restrict('packages:modify')
    def intent_install(self, package):
        p = PackageInfo()
        p.name, p.action = package, 'i'
        self.run([p])

    def on_page_load(self):
        self.context.endpoint.send_progress(_('Querying package manager'))
        self.mgr.refresh()
        self.refresh()

    @restrict('packages:modify')
    def on_install(self, package):
        package.action = 'i'
        self.pending[package.name] = package
        self.refresh()

    @restrict('packages:modify')
    def on_cancel(self, package):
        package.action = None
        if package.name in self.pending:
            del self.pending[package.name]
        self.refresh()

    @restrict('packages:modify')
    def on_remove(self, package):
        package.action = 'r'
        self.pending[package.name] = package
        self.refresh()

    @on('get-lists-button', 'click')
    @restrict('packages:refresh')
    def on_get_lists(self):
        self.mgr.get_lists()

    @on('apply-button', 'click')
    @restrict('packages:modify')
    def on_apply(self):
        self.run(self.pending.values())
        self.pending = {}
        self.refresh()

    @on('upgrade-all-button', 'click')
    @restrict('packages:modify')
    def on_upgrade_all(self):
        for p in self.mgr.upgradeable:
            p.action = 'i'
            self.pending[p.name] = p
        self.refresh()

    @on('cancel-all-button', 'click')
    @restrict('packages:modify')
    def on_cancel_all(self):
        self.pending = {}
        self.refresh()

    def fill(self, packages):
        for p in packages:
            if p.name in self.pending:
                p.action = self.pending[p.name].action

    @on('search-button', 'click')
    def on_search(self):
        query = self.find('search-box').value
        results = self.mgr.search(query)
        if self.binder_s:
            self.binder_s.unpopulate()
        if len(results) > 100:
            self.find('search-counter').text = _('%i found, 100 shown') % len(results)
            results = results[:100]
        else:
            self.find('search-counter').text = _('%i found') % len(results)

        self.fill(results)
        self.binder_s = CollectionAutoBinding(results, None, self.find('search')).populate()


@plugin
class PackagesPermissionsProvider (PermissionProvider):
    def get_name(self):
        return _('Packages')

    def get_permissions(self):
        return [
            ('packages:modify', _('Install / remove')),
            ('packages:refresh', _('Refresh lists')),
        ]

########NEW FILE########
__FILENAME__ = pm_apt
import subprocess

from ajenti.api import *
from api import PackageInfo, PackageManager


@plugin
@rootcontext
@persistent
class DebianPackageManager (PackageManager):
    platforms = ['debian']

    def refresh(self):
        out_u = subprocess.check_output(['apt-show-versions', '-u'])
        out_a = subprocess.check_output(['dpkg', '-l'])
        self.all = self._parse_dpkg(out_a)
        self.all_dict = dict((x.name, x) for x in self.all)
        self.upgradeable = self._parse_asv(out_u)

    def search(self, query):
        out_s = subprocess.check_output(['apt-show-versions', '-a', '-R', query])
        r = []
        found = {}
        for l in out_s.split('\n'):
            s = l.split()
            if len(s) < 4:
                continue

            p = PackageInfo()
            p.name = s[0]
            p.state = 'i' if p.name in self.all_dict else 'r'
            p.version = s[1]

            if not p.name in found or found[p.name] < p.version:
                r.append(p)
                found[p.name] = p.version
        return r

    def get_lists(self):
        self.context.launch('terminal', command='apt-get update')

    def do(self, actions, callback=lambda: 0):
        cmd = 'apt-get install '
        for a in actions:
            cmd += a.name + {'r': '-', 'i': '+'}[a.action] + ' '
        self.context.launch('terminal', command=cmd, callback=callback)

    def _parse_asv(self, d):
        r = []
        for l in d.split('\n'):
            s = l.split('/')
            if len(s) == 0 or not s[0]:
                continue

            p = PackageInfo()
            p.name = s[0]
            p.version = s[1].split(' ')[-1]
            r.append(p)
        return r

    def _parse_apt(self, d):
        r = []
        for l in d.split('\n'):
            s = filter(None, l.split(' '))
            if len(s) == 0:
                continue

            p = PackageInfo()
            if s[0] == 'Inst':
                p.action = 'i'
            elif s[0] in ['Remv', 'Purg']:
                p.action = 'r'
            else:
                continue
            p.name = s[1]
            p.version = s[2].strip('[]')
            r.append(p)
        return r

    def _parse_dpkg(self, d):
        r = []
        for l in d.split('\n'):
            s = filter(None, l.split(' '))
            if len(s) == 0:
                continue

            p = PackageInfo()
            if s[0][0] == 'i':
                p.state = 'i'
            else:
                continue

            p.name = s[1]
            p.version = s[2]
            p.description = ' '.join(s[3:])
            r.append(p)
        return r

########NEW FILE########
__FILENAME__ = pm_bsd
from ajenti.api import *
from api import PackageInfo, PackageManager


@plugin
@rootcontext
@persistent
class BSDPackageManager (PackageManager):
    platforms = ['freebsd']

    def init(self):
        self.upgradeable = []

    def get_lists(self):
        pass

    def refresh(self):
        pass

    def search(self, query):
        return []

    def do(self, actions):
        pass

########NEW FILE########
__FILENAME__ = pm_pacman
import subprocess
import logging

from ajenti.api import *
from api import PackageInfo, PackageManager


@plugin
@rootcontext
@persistent
class ArchPackageManager (PackageManager):
    platforms = ['arch']

    def init(self):
        self.upgradeable = []
        self.all = []

    def get_lists(self):
        self.context.launch('terminal', command='pacman -Sy')

    def refresh(self):
        try:
            out_u = subprocess.check_output(['pacman', '-Qu'])
        except subprocess.CalledProcessError as cpe:
            out_u = ''

        out_a = subprocess.check_output(['pacman', '-Qs'])

        self.upgradeable = self._parse_upgradeable(out_u)

        self.all = self._parse_all_installed(out_a)
        self.all_dict = dict((x.name, x) for x in self.all)

    def search(self, query):
        try:
            out_s = subprocess.check_output(['pacman', '-Ss', query])
        except subprocess.CalledProcessError as cpe:
            self.context.notify('info', _('No search results found'))
            logging.info('No search results found')
            out_s = ''

        r = []
        for l in out_s.split('\n'):
            s = l.split('/')
            if len(s) == 2 and not(s[0].startswith('  ')):
                sn = s[1].split(' ')

                p = PackageInfo()
                p.name = sn[0]
                p.state = 'i' if subprocess.call(['pacman', '-Q', p.name]) == 0 else 'r'
                p.version = sn[1]

                r.append(p)

        return r

    def do(self, actions, callback=lambda: 0):
        to_install = [a for a in actions if a.action == 'i']
        to_remove = [a for a in actions if a.action == 'r']
        cmd = ''
        if len(to_install) > 0:
            cmd += 'pacman -S --noconfirm ' + ' '.join(a.name for a in to_install)
            if len(to_remove) > 0:
                cmd += ' && '

        if len(to_remove) > 0:
            cmd += 'pacman -R --noconfirm ' + ' '.join(a.name for a in to_remove)

        logging.debug('launching terminal with command %s' % cmd)
        self.context.launch('terminal', command=cmd, callback=callback)


    def _parse_upgradeable(self, d):
        r = []
        for l in d.split('\n'):
            s = l.split(' ')
            if len(s) == 1:
                continue

            p = PackageInfo()
            p.action = 'i'

            p.name = s[0]
            p.version = s[1]
            r.append(p)
        return r

    def _parse_all_installed(self, d):
        r = []

        lines = d.splitlines()
        infos = ['\n'.join(lines[i:i+2]) for i in range(0, len(lines), 2)]

        for info in infos:
            s = info.split('\n')
            if len(s) == 0:
                continue

            package = s[0].split(' ')

            p = PackageInfo()
            p.state = 'i'

            p.name = package[0]
            p.version = package[1]

            s[1].lstrip().rstrip()
            p.description = ' '.join(s[1])

            r.append(p)
        return r


########NEW FILE########
__FILENAME__ = pm_yum
import subprocess

from ajenti.api import *
from api import PackageInfo, PackageManager


@plugin
@rootcontext
@persistent
class YumPackageManager (PackageManager):
    platforms = ['centos']

    def refresh(self):
        try:
            out_u = subprocess.check_output(['yum', '-C', '-q', '-d0', '-e0', 'check-update'])
        except subprocess.CalledProcessError as e:
            # yum check-update returns 100 if there are packages available for an update
            if e.returncode == 100:
                out_u = e.output
            else:
                raise e
        out_a = subprocess.check_output(['yum', '-C', '-d0', '-e0', 'list', 'installed', '-q'])
        self.all = self._parse_yum(out_a)
        self.all_dict = dict((x.name, x) for x in self.all)
        self.upgradeable = self._parse_yum(out_u)

    def search(self, query):
        out_s = subprocess.check_output(['yum', '-C', '-q', '-d0', '-e0', 'search', query])
        r = []
        for l in out_s.split('\n'):
            s = l.split()
            if len(s) < 2:
                continue
            if s[0].startswith('====') or s[0] == ':':
                continue
            else:
                p = PackageInfo()
                p.name = s[0]
                p.state = 'r'
                if p.name in self.all_dict and self.all_dict[p.name].state == 'i':
                    p.state = 'i'
                r.append(p)
        return r

    def get_lists(self):
        self.context.launch('terminal', command='yum check-update')

    def do(self, actions, callback=lambda: 0):
        to_install = [a for a in actions if a.action == 'i']
        to_remove = [a for a in actions if a.action == 'r']
        cmd = ''
        if len(to_install) > 0:
            cmd += 'yum install ' + ' '.join(a.name for a in to_install)
            if len(to_remove) > 0:
                cmd += ' && '
        if len(to_remove) > 0:
            cmd += 'yum remove ' + ' '.join(a.name for a in to_remove)
        self.context.launch('terminal', command=cmd, callback=callback)

    def _parse_yum(self, ss):
        r = []
        for s in ss.splitlines():
            s = s.split()
            try:
                if s[0] == '':
                    continue
                else:
                    p = PackageInfo()
                    p.name = s[0]
                    p.state = 'i'
                    r.append(p)
                if len(r.keys()) > 250:
                    break
            except:
                pass
        return r

########NEW FILE########
__FILENAME__ = plugins
from ajenti.api import *
from ajenti.plugins import manager, ModuleDependency, BinaryDependency
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui.binder import Binder


@plugin
class PluginsPlugin (SectionPlugin):
    def init(self):
        self.title = _('Plugins')
        self.icon = 'cogs'
        self.category = ''
        self.order = 60

        # In case you didn't notice it yet, this is the Plugins Plugin Plugin
        self.append(self.ui.inflate('plugins:main'))

        def post_plugin_bind(object, collection, item, ui):
            if not item.crash:
                ui.find('crash').visible = False

        def post_dep_bind(object, collection, item, ui):
            if not item.satisfied():
                installer = ui.find('fix')
                if item.__class__ == ModuleDependency:
                    installer.package = 'python-module-' + item.module_name
                if item.__class__ == BinaryDependency:
                    installer.package = item.binary_name
                installer.recheck()

        self.find('plugins').post_item_bind = post_plugin_bind
        self.find('dependencies').post_item_bind = post_dep_bind

        self.binder = Binder(None, self.find('bind-root'))

    def on_page_load(self):
        self.context.endpoint.send_progress(_('Gathering plugin list'))
        self.plugins = sorted(manager.get_all().values())
        self.binder.setup(self).populate()

########NEW FILE########
__FILENAME__ = api
import subprocess

from ajenti.api import plugin, interface
from ajenti.util import cache_value


@interface
class PowerController (object):
    def shutdown(self):
        pass

    def suspend(self):
        pass

    def hibernate(self):
        pass

    def reboot(self):
        pass

    @classmethod
    def capabilities(cls):
        pass


@plugin
class SystemdPowerController (PowerController):
    def shutdown(self):
        subprocess.call(['systemctl', 'poweroff'])

    def reboot(self):
        subprocess.call(['systemctl', 'reboot'])

    def suspend(self):
        subprocess.call(['systemctl', 'suspend'])

    def hibernate(self):
        subprocess.call(['systemctl', 'hibernate'])

    @classmethod
    @cache_value()
    def capabilities(cls):
        if subprocess.call(['which', 'systemctl']) == 0:
            return ['reboot', 'suspend', 'hibernate', 'shutdown']
        else:
            return []

    @classmethod
    def verify(cls):
        return subprocess.call(['which', 'systemctl']) == 0


@plugin
class PMUtilsPowerController (PowerController):
    def shutdown(self):
        subprocess.call(['poweroff'])

    def suspend(self):
        subprocess.call(['pm-suspend'])

    def hibernate(self):
        subprocess.call(['pm-hibernate'])

    def reboot(self):
        subprocess.call(['reboot'])

    @classmethod
    @cache_value()
    def capabilities(cls):
        return ['shutdown', 'reboot', 'suspend', 'hibernate']

    @classmethod
    def verify(cls):
        return subprocess.call(['which', 'pm-hibernate']) == 0


@plugin
class BasicLinuxPowerController (PowerController):
    def shutdown(self):
        subprocess.call(['poweroff'])

    def reboot(self):
        subprocess.call(['reboot'])

    @classmethod
    def capabilities(cls):
        return ['shutdown', 'reboot']

########NEW FILE########
__FILENAME__ = power
import logging
import subprocess
import os

from ajenti.api import plugin
from ajenti.api.sensors import Sensor
from ajenti.plugins.dashboard.api import DashboardWidget
from ajenti.ui import on
from ajenti.users import PermissionProvider, restrict

from api import PowerController


@plugin
class PowerSensor (Sensor):
    id = 'power'
    timeout = 2

    def measure(self, variant):
        adapters_path = '/proc/acpi/ac_adapter'
        if os.path.exists(adapters_path):
            for x in os.listdir(adapters_path):
                ss = open('/proc/acpi/ac_adapter/%s/state' % x).read().splitlines()
                for s in ss:
                    if s.startswith('state:') and s.endswith('on-line'):
                        return 'ac'
        else:
            return 'ac'
        return 'battery'


@plugin
class BatterySensor (Sensor):
    id = 'battery'
    timeout = 2

    def measure(self, variant):
        battery_path = '/proc/acpi/battery'

        if os.path.exists(battery_path):
            for x in os.listdir(battery_path):
                current = total = 100
                for s in open('/proc/acpi/battery/%s/state' % x).read().split('\n'):
                    if s.startswith('remaining capacity:'):
                        current = int(s.split()[2])

                for s in open('/proc/acpi/battery/%s/info' % x).read().split('\n'):
                    if s.startswith('last full capacity:'):
                        total = int(s.split()[3])

                return (current, total)

        return (1, 1)


@plugin
class PowerWidget (DashboardWidget):
    name = _('Power')
    icon = 'bolt'

    def init(self):
        self.sensor = Sensor.find('power')
        self.append(self.ui.inflate('power:widget'))
        self.find('ac').visible = self.sensor.value() == 'ac'
        self.find('battery').visible = self.sensor.value() == 'battery'
        charge = Sensor.find('battery').value()
        self.find('charge').value = charge[0] * 1.0 / charge[1]

        self.powerctl = PowerController.get()
        caps = self.powerctl.capabilities()
        for cap in ('shutdown', 'suspend', 'hibernate', 'reboot'):
            self.find(cap).visible = cap in caps

    @on('suspend', 'click')
    @restrict('power:suspend')
    def on_suspend(self):
        logging.info('[power] suspend')
        self.powerctl.suspend()

    @on('hibernate', 'click')
    @restrict('power:hibernate')
    def on_hibernate(self):
        logging.info('[power] hibernate')
        self.powerctl.hibernate()

    @on('reboot', 'click')
    @restrict('power:reboot')
    def on_reboot(self):
        logging.info('[power] reboot')
        self.powerctl.reboot()

    @on('shutdown', 'click')
    @restrict('power:shutdown')
    def on_shutdown(self):
        logging.info('[power] poweroff')
        self.powerctl.shutdown()


@plugin
class PowerPermissionsProvider (PermissionProvider):
    def get_name(self):
        return _('Power control')

    def get_permissions(self):
        return [
            ('power:suspend', _('Suspend')),
            ('power:hibernate', _('Hibernate')),
            ('power:reboot', _('Reboot')),
            ('power:shutdown', _('Shutdown')),
        ]

########NEW FILE########
__FILENAME__ = main
import subprocess

from ajenti.api import *
from ajenti.plugins.db_common.api import DBPlugin, Database, User


@plugin
class PSQLPlugin (DBPlugin):
    service_name = 'postgresql'
    service_buttons = [
        {
            'command': 'reload',
            'text': _('Reload'),
            'icon': 'step-forward',
        }
    ]

    def init(self):
        self.title = 'PostgreSQL'
        self.category = _('Software')
        self.icon = 'table'

    def query(self, sql, db=''):
        p = subprocess.Popen([
            'su',
            'postgres',
            '-c',
            'psql -R"~~~" -A -t -c "%s" %s' % (sql, db)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        o, e = p.communicate()
        if p.returncode:
            raise Exception(e)
        return filter(None, o.split('~~~'))

    def query_sql(self, db, sql):
        r = []
        for l in self.query(sql.replace('"', '\\"') + ';', db):
            r.append(l.split('|'))
        return r

    def query_databases(self):
        r = []
        for l in self.query('\\l'):
            db = Database()
            db.name = l.split('|')[0]
            r.append(db)
        return r

    def query_drop(self, db):
        self.query('DROP DATABASE %s;' % db.name)

    def query_create(self, name):
        self.query('CREATE DATABASE %s;' % name)

    def query_users(self):
        r = []
        for l in self.query('\\du'):
            u = User()
            u.host, u.name = '', l.split('|')[0]
            r.append(u)
        return r

    def query_create_user(self, user):
        self.query('CREATE USER %s WITH PASSWORD \'%s\';' % (user.name, user.password))

    def query_drop_user(self, user):
        self.query('DROP USER "%s";' % user.name)

########NEW FILE########
__FILENAME__ = api
from ajenti.api import *


class RAIDDevice (object):
    def __init__(self):
        self.name = ''
        self.up = False
        self.failed = False
        self.index = 0


class RAIDArray (object):
    def __init__(self):
        self.name = ''
        self.type = ''
        self.blocks = 0
        self.metadata = ''
        self.devices = []
        self.recovery = False
        self.recovery_progress = 0
        self.recovery_remaining = ''


@plugin
class RAIDManager (BasePlugin):
    def __init__(self):
        self.refresh()

    def refresh(self):
        self.arrays = []
        ll = open('/proc/mdstat').read().splitlines()
        while ll:
            l = ll.pop(0)
            if l.startswith('Personalities'):
                continue
            if l.startswith('unused'):
                continue
            if ':' in l:
                array = RAIDArray()
                array.name, tokens = l.split(':')
                array.name = array.name.strip()
                tokens = tokens.split()

                if tokens[1].startswith('('):
                    tokens[0] += ' ' + tokens[1]
                    tokens.pop(1)

                array.state = tokens[0]
                array.active = array.state == 'active'
                array.type = tokens[1]
                devices = tokens[2:]

                l = ll.pop(0)
                tokens = l.split()
                array.blocks = int(tokens[0])
                array.metadata = tokens[3]

                states = tokens[-1][1:-1]

                self.arrays.append(array)

                for i in range(len(devices)):
                    device = RAIDDevice()
                    device.name = devices[i].split('[')[0]
                    device.index = int(devices[i].split('[')[1].split(']')[0])
                    device.up = states[i] == 'U'
                    array.devices.append(device)

                l = ll.pop(0)
                if 'recovery' in l:
                    array.recovery = True
                    array.recovery_progress = float(l.split()[3].strip('%')) / 100
                    array.recovery_remaining = l.split()[5].split('=')[1]

########NEW FILE########
__FILENAME__ = main
from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder

from reconfigure.configs import ResolvConfig
from reconfigure.items.resolv import ItemData

from api import RAIDManager


@plugin
class RAID (SectionPlugin):
    def init(self):
        self.title = _('RAID')
        self.icon = 'hdd'
        self.category = _('System')

        self.append(self.ui.inflate('raid:main'))

        def post_array_bind(o, c, i, u):
            u.find('recovery').visible = i.recovery

        self.find('arrays').post_item_bind = post_array_bind

        self.mgr = RAIDManager.get()
        self.binder = Binder(None, self)

    def on_page_load(self):
        self.refresh()

    def refresh(self):
        self.mgr.refresh()
        self.binder.setup(self.mgr).populate()

########NEW FILE########
__FILENAME__ = main
from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder

from reconfigure.configs import ResolvConfig
from reconfigure.items.resolv import ItemData


@plugin
class Resolv (SectionPlugin):
    def init(self):
        self.title = _('Nameservers')
        self.icon = 'globe'
        self.category = _('System')

        self.append(self.ui.inflate('resolv:main'))
        self.find('name-box').labels = [_('DNS nameserver'), _('Local domain name'), _('Search list'), _('Sort list'), _('Options')]
        self.find('name-box').values = ['nameserver', 'domain', 'search', 'sortlist', 'options']

        self.config = ResolvConfig(path='/etc/resolv.conf')
        self.binder = Binder(None, self.find('resolv-config'))
        self.find('items').new_item = lambda c: ItemData()

    def on_page_load(self):
        self.config.load()
        self.binder.setup(self.config.tree).populate()

    @on('save', 'click')
    def save(self):
        self.binder.update()
        self.config.save()

########NEW FILE########
__FILENAME__ = server
import os
import re
import time
import subprocess

import ajenti
from ajenti.api import *
from ajenti.api.http import *
from ajenti.plugins import manager


@plugin
class ContentServer (HttpPlugin):
    last_query = 0

    @url('/ajenti:static/resources.(?P<type>.+)')
    def handle_resources(self, context, type):
        if ajenti.debug:
            if time.time() - self.last_query > 5:
                try:
                    print subprocess.check_output('./compile_resources.py nocompress', shell=True)
                except:
                    pass
                ContentCompressor.get().compress()
            self.last_query = time.time()
        content = ContentCompressor.get().compressed[type]
        types = {
            'css': 'text/css',
            'js': 'application/javascript',
        }
        context.respond_ok()
        context.add_header('Content-Type', types[type])
        return context.gzip(content)

    @url('/ajenti:static/(?P<plugin>\w+)/(?P<path>.+)')
    def handle_static(self, context, plugin, path):
        plugin_path = manager.resolve_path(plugin)
        if plugin_path is None:
            context.respond_not_found()
            return 'Not Found'
        path = os.path.join(plugin_path, 'content/static', path)
        context.respond_ok()
        return context.file(path)


@plugin
@persistent
@rootcontext
class ContentCompressor (object):
    def __init__(self):
        self.files = {}
        self.compressed = {}
        self.compressors = {
            'js': self.process_js,
            'css': self.process_css
        }
        self.patterns = {
            'js': r'.+\.[cm]\.js$',
            'css': r'.+\.[cm]\.css$'
        }
        self.scan('js')
        self.scan('css')
        self.compress()

    def scan(self, dir):
        for plugin in manager.get_order():
            pfiles = {}
            path = os.path.join(manager.resolve_path(plugin), 'content', dir)
            if not os.path.exists(path):
                continue
            for (dp, dn, fn) in os.walk(path):
                for name in fn:
                    for key in self.patterns:
                        if re.match(self.patterns[key], name):
                            pfiles.setdefault(key, []).append(os.path.join(dp, name))
            for key in self.patterns:
                self.files.setdefault(key, []).extend(sorted(pfiles.setdefault(key, [])))

    def compress(self):
        for key in self.patterns:
            self.compressed[key] = self.compressors[key](self.files.setdefault(key, []))

    def process_js(self, files):
        return '\n'.join([open(x).read() for x in files])

    def process_css(self, files):
        return '\n'.join([open(x).read() for x in files])

########NEW FILE########
__FILENAME__ = main
from ajenti.api import *
from ajenti.ui.binder import Binder
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.util import platform_select

from reconfigure.configs import SambaConfig, PasswdConfig
from reconfigure.items.samba import ShareData

from status import SambaMonitor
from smbusers import SambaUsers


@plugin
class Samba (SectionPlugin):
    def init(self):
        self.title = 'Samba'
        self.icon = 'folder-close'
        self.category = _('Software')
        self.append(self.ui.inflate('samba:main'))

        self.find('servicebar').name = platform_select(
            debian='samba',
            ubuntu='smbd',
            centos='smb',
            default='samba',
        )
        self.find('servicebar').reload()

        self.binder = Binder(None, self.find('config'))
        self.find('shares').new_item = lambda c: ShareData()
        self.config = SambaConfig(path='/etc/samba/smb.conf')

        def post_item_bind(object, collection, item, ui):
            ui.find('disconnect').on('click', self.on_disconnect, item)

        self.find('connections').post_item_bind = post_item_bind

        def post_user_bind(object, collection, item, ui):
            def delete_user():
                self.usermgr.delete(item.username)
                self.refresh()
            ui.find('delete').on('click', delete_user)

            def set_password():
                if self.usermgr.set_password(item.username, ui.find('password').value):
                    self.context.notify('info', _('Password updated'))
                    ui.find('password').value = ''
                else:
                    self.context.notify('error', _('Password update failed'))
            ui.find('password-set').on('click', set_password)

        self.find('user-list').post_item_bind = post_user_bind

        self.usermgr = SambaUsers()
        self.binder_u = Binder(self.usermgr, self.find('users'))

        self.monitor = SambaMonitor()
        self.binder_m = Binder(self.monitor, self.find('status'))

    def on_page_load(self):
        self.refresh()

    def on_disconnect(self, connection):
        connection.disconnect()
        self.refresh()

    def refresh(self):
        self.config.load()
        self.monitor.refresh()
        self.usermgr.load()
        self.binder.setup(self.config.tree).populate()
        self.binder_m.setup(self.monitor).populate()
        self.binder_u.setup(self.usermgr).populate()

        users_dropdown = self.find('add-user-list')
        users = [x.name for x in PasswdConfig(path='/etc/passwd').load().tree.users]
        for u in self.usermgr.users:
            if u.username in users:
                users.remove(u.username)
        users_dropdown.values = users_dropdown.labels = users

    @on('add-user', 'click')
    def on_add_user(self):
        self.usermgr.create(self.find('add-user-list').value)
        self.refresh()

    @on('save', 'click')
    def on_save(self):
        self.binder.update()
        self.config.save()
        self.refresh()

########NEW FILE########
__FILENAME__ = smbusers
import subprocess


class SambaUser (object):
    def __init__(self):
        self.username = None
        self.sid = None


class SambaUsers (object):
    def load(self):
        self.users = []
        for un in [s.split(':')[0] for s in subprocess.check_output(['pdbedit', '-L', '-d0']).split('\n')]:
            if un and not ' ' in un and not un.startswith('WARNING'):
                lines = subprocess.check_output(['pdbedit', '-Lv', '-d0', '-u', un]).split('\n')
                fields = {}
                for l in lines:
                    if l and ':' in l:
                        l = l.split(':', 1)
                        fields[l[0]] = l[1].strip()
                u = SambaUser()
                u.username = un
                u.sid = fields['User SID']
                self.users.append(u)

    def create(self, un):
        p = subprocess.Popen(['pdbedit', '-at', '-u', un])
        p.communicate('\n\n\n')

    def delete(self, un):
        subprocess.call(['pdbedit', '-x', '-u', un])

    def set_password(self, un, pw):
        p = subprocess.Popen(['pdbedit', '-at', '-u', un])
        p.communicate('%s\n%s\n' % (pw, pw))
        return p.returncode == 0

########NEW FILE########
__FILENAME__ = status
import os
import subprocess


class SambaMonitor (object):
    def __init__(self):
        self.refresh()

    def refresh(self):
        pids = {}

        ll = subprocess.check_output(['smbstatus', '-p']).splitlines()
        for l in ll[4:]:
            s = l.split()
            if len(s) > 0:
                pids[s[0]] = (s[1], ' '.join(s[3:]))

        self.connections = []
        ll = subprocess.check_output(['smbstatus', '-S']).splitlines()
        for l in ll[3:]:
            s = l.split()
            if len(s) > 0 and s[1] in pids:
                c = SambaConnection(s[0], s[1], *pids[s[1]])
                self.connections.append(c)


class SambaConnection (object):
    def __init__(self, share, pid, user, machine):
        self.share, self.pid, self.user, self.machine = share, pid, user, machine

    def disconnect(self):
        os.kill(int(self.pid), 15)

########NEW FILE########
__FILENAME__ = widget
import gevent
import subprocess

from ajenti.api import plugin
from ajenti.plugins.dashboard.api import ConfigurableWidget
from ajenti.users import PermissionProvider, restrict
from ajenti.ui import on


@plugin
class ScriptWidget (ConfigurableWidget):
    name = _('Script')
    icon = 'play'

    def on_prepare(self):
        self.append(self.ui.inflate('scripts:widget'))

    def on_start(self):
        self.command = self.config['command']
        if not self.command:
            return
        self.find('name').text = self.config['title']

    def create_config(self):
        return {'command': '', 'title': '', 'terminal': False}

    def on_config_start(self):
        self.dialog.find('command').value = self.config['command']
        self.dialog.find('title').value = self.config['title']
        self.dialog.find('terminal').value = self.config['terminal']

    @on('edit', 'click')
    def on_edit(self):
        self.begin_configuration()

    def on_config_save(self):
        self.config['command'] = self.dialog.find('command').value
        self.config['title'] = self.dialog.find('title').value
        self.config['terminal'] = self.dialog.find('terminal').value

    @on('start', 'click')
    @restrict('scripts:run')
    def on_s_start(self):
        if self.config['terminal']:
            self.context.launch('terminal', command=self.config['command'])
        else:
            p = subprocess.Popen(self.config['command'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.context.notify('info', _('Launched'))

            def worker():
                o, e = p.communicate()
                self.context.notify('info', o + e)

            gevent.spawn(worker)


@plugin
class ScriptPermissionsProvider (PermissionProvider):
    def get_name(self):
        return _('Scripts')

    def get_permissions(self):
        return [
            ('scripts:run', _('Run scripts')),
        ]

########NEW FILE########
__FILENAME__ = cpu
import psutil

from ajenti.api import plugin
from ajenti.api.sensors import Sensor
from ajenti.plugins.dashboard.api import DashboardWidget


@plugin
class CPUSensor (Sensor):
    id = 'cpu'
    timeout = 3

    def measure(self, variant=None):
        return [x / 100 for x in psutil.cpu_percent(interval=0, percpu=True)]


@plugin
class CPUWidget (DashboardWidget):
    name = _('CPU usage')
    icon = 'signal'

    def init(self):
        self.sensor = Sensor.find('cpu')
        self.append(self.ui.inflate('sensors:cpu-widget'))
        self.find('icon').icon = 'signal'
        self.find('name').text = _('CPU usage')
        for value in self.sensor.value():
            l = self.ui.inflate('sensors:cpu-line')
            l.find('progress').value = value
            l.find('value').text = '%i%%' % int(value * 100)
            self.find('lines').append(l)

########NEW FILE########
__FILENAME__ = hostname
import platform

from ajenti.api import *
from ajenti.api.sensors import Sensor


@plugin
class HostnameSensor (Sensor):
    id = 'hostname'
    timeout = 60

    def measure(self, variant=None):
        return platform.node()

########NEW FILE########
__FILENAME__ = load
import subprocess

from ajenti.api import plugin
from ajenti.api.sensors import Sensor
from ajenti.plugins.dashboard.api import DashboardWidget


class BaseLoadSensor (Sensor):
    id = 'load'
    timeout = 1

    def get_variants(self):
        return ['1 min', '5 min', '15 min']


@plugin
class LinuxLoadSensor (BaseLoadSensor):
    platforms = ['debian', 'centos', 'arch']

    def measure(self, variant):
        idx = self.get_variants().index(variant)
        return float(open('/proc/loadavg').read().split()[idx])


@plugin
class BSDLoadSensor (BaseLoadSensor):
    platforms = ['freebsd']

    def measure(self, variant):
        idx = self.get_variants().index(variant)
        tokens = subprocess.check_output(['uptime']).split()
        loads = [float(x.strip(',')) for x in tokens[-3:]]
        return loads[idx]


@plugin
class LoadWidget (DashboardWidget):
    name = _('Load average')
    icon = 'signal'

    def init(self):
        self.sensor = Sensor.find('load')
        self.append(self.ui.inflate('sensors:value-widget'))
        self.find('icon').icon = 'signal'
        self.find('name').text = _('Load average')
        self.find('value').text = ' / '.join(str(self.sensor.value(x)) for x in self.sensor.get_variants())

########NEW FILE########
__FILENAME__ = memory
import psutil

from ajenti.api import plugin
from ajenti.api.sensors import Sensor
from ajenti.plugins.dashboard.api import DashboardWidget
from ajenti.util import str_fsize


@plugin
class MemorySensor (Sensor):
    id = 'memory'
    timeout = 5

    def measure(self, variant):
        v = psutil.virtual_memory()
        return (v.total - v.available, v.total)


@plugin
class SwapSensor (Sensor):
    id = 'swap'
    timeout = 5

    def measure(self, variant):
        v = psutil.swap_memory()
        return (v.used, v.total)


@plugin
class MemoryWidget (DashboardWidget):
    name = _('Memory usage')
    icon = 'tasks'

    def init(self):
        self.sensor = Sensor.find('memory')
        self.append(self.ui.inflate('sensors:progressbar-widget'))
        self.find('icon').icon = 'tasks'
        self.find('name').text = _('Memory usage')
        value = self.sensor.value()
        self.find('value').text = str_fsize(value[0])
        self.find('progress').value = 1.0 * value[0] / value[1]


@plugin
class SwapWidget (DashboardWidget):
    name = _('Swap usage')
    icon = 'hdd'

    def init(self):
        self.sensor = Sensor.find('swap')
        self.append(self.ui.inflate('sensors:progressbar-widget'))
        self.find('icon').icon = 'hdd'
        self.find('name').text = _('Swap usage')
        value = self.sensor.value()
        self.find('value').text = str_fsize(value[0])
        if value[1] > 0:
            frac = 1.0 * value[0] / value[1]
        else:
            frac = 0
        self.find('progress').value = frac

########NEW FILE########
__FILENAME__ = uptime
import psutil
import time

from ajenti.api import plugin
from ajenti.api.sensors import Sensor
from ajenti.plugins.dashboard.api import DashboardWidget
from ajenti.util import str_timedelta


@plugin
class UnixUptimeSensor (Sensor):
    id = 'uptime'
    timeout = 1

    def measure(self, variant):
        return time.time() - psutil.BOOT_TIME


@plugin
class UptimeWidget (DashboardWidget):
    name = _('Uptime')
    icon = 'off'

    def init(self):
        self.sensor = Sensor.find('uptime')
        self.append(self.ui.inflate('sensors:value-widget'))

        self.find('icon').text = 'off'
        self.find('name').text = 'Uptime'
        self.find('value').text = str_timedelta(self.sensor.value())

########NEW FILE########
__FILENAME__ = api
from ajenti.api import *
from ajenti.util import cache_value


@plugin
@persistent
class ServiceMultiplexor (object):
    """
    Merges together output of all available ServiceManagers.
    """
    def init(self):
        self.managers = ServiceManager.get_all()

    @cache_value(1)
    def get_all(self):
        """
        Returns all :class:`Service` s.
        """
        r = []
        for mgr in self.managers:
            r += mgr.get_all()
        return r

    def get_one(self, name):
        """
        Returns a :class:`Service` by name.
        """
        for mgr in self.managers:
            s = mgr.get_one(name)
            if s:
                return s
        return None


@interface
@persistent
class ServiceManager (object):
    def get_all(self):
        return []

    def get_one(self, name):
        """
        Returns a :class:`Service` by name.
        """
        for s in self.get_all():
            if s.name == name:
                return s
        return None


class Service (object):
    source = 'unknown'
    """ Marks which ServiceManager owns this object """

    def __init__(self):
        self.name = None
        self.running = False

    @property
    def icon(self):
        return 'play' if self.running else None

    def start(self):
        pass

    def stop(self):
        pass

    def restart(self):
        pass

    def command(self, cmd):
        pass

########NEW FILE########
__FILENAME__ = main
import logging

from ajenti.api import *
from ajenti.ui.binder import Binder
from ajenti.ui import p, UIElement, on
from ajenti.plugins.main.api import SectionPlugin

from api import ServiceMultiplexor


@plugin
class Services (SectionPlugin):
    def init(self):
        self.title = _('Services')
        self.icon = 'play'
        self.category = _('Software')
        self.append(self.ui.inflate('services:main'))
        self.mgr = ServiceMultiplexor.get()
        self.binder = Binder(None, self.find('main'))

        def post_item_bind(object, collection, item, ui):
            ui.find('stop').on('click', self.on_stop, item)
            ui.find('restart').on('click', self.on_restart, item)
            ui.find('start').on('click', self.on_start, item)
            ui.find('stop').visible = item.running
            ui.find('restart').visible = item.running
            ui.find('start').visible = not item.running

        self.find('services').post_item_bind = post_item_bind

    def on_page_load(self):
        self.refresh()

    def refresh(self):
        self.services = sorted(self.mgr.get_all(), key=lambda x: x.name)
        self.binder.setup(self).populate()

    def on_start(self, item):
        item.start()
        self.refresh()
        self.context.notify('info', _('%s started') % item.name)

    def on_stop(self, item):
        item.stop()
        self.refresh()
        self.context.notify('info', _('%s stopped') % item.name)

    def on_restart(self, item):
        item.restart()
        self.refresh()
        self.context.notify('info', _('%s restarted') % item.name)


@p('name', bindtypes=[str, unicode])
@p('buttons', default=[], type=eval)
@plugin
class ServiceControlBar (UIElement):
    typeid = 'servicebar'

    def init(self):
        self.service = None
        self.reload()

    def reload(self):
        self.empty()
        self.append(self.ui.inflate('services:bar'))
        if self.name:
            self.service = ServiceMultiplexor.get().get_one(self.name)
            for btn in self.buttons:
                b = self.ui.create('button')
                b.text, b.icon = btn['text'], btn['icon']
                b.on('click', self.on_command_button, btn['command'])
                self.find('buttons').append(b)
            self.refresh()

    def on_page_load(self):
        self.reload()

    def refresh(self):
        if self.service:
            self.service.refresh()
            self.find('start').visible = not self.service.running
            self.find('stop').visible = self.service.running
            self.find('restart').visible = self.service.running

    @on('start', 'click')
    def on_start(self):
        self.service.start()
        self.on_page_load()
        self.reverse_event('command', {'command': 'start'})
        logging.info('[services] starting %s' % self.service.name)

    @on('restart', 'click')
    def on_restart(self):
        self.service.restart()
        self.on_page_load()
        self.reverse_event('command', {'command': 'restart'})
        logging.info('[services] restarting %s' % self.service.name)

    @on('stop', 'click')
    def on_stop(self):
        self.service.stop()
        self.on_page_load()
        self.reverse_event('command', {'command': 'stop'})
        logging.info('[services] stopping %s' % self.service.name)

    def on_command_button(self, cmd):
        self.service.command(cmd)
        self.on_page_load()
        self.reverse_event('command', {'command': cmd})
        logging.info('[services] %s %s' % (cmd, self.service.name))

########NEW FILE########
__FILENAME__ = sensor
from ajenti.api import plugin
from ajenti.api.sensors import Sensor
from api import ServiceMultiplexor


@plugin
class ServiceSensor (Sensor):
    id = 'service'
    timeout = 5

    def init(self):
        self.sm = ServiceMultiplexor.get()

    def get_variants(self):
        return [x.name for x in self.sm.get_all()]

    def measure(self, variant):
        s = self.sm.get_one(variant)
        if not s:
            return 0
        return int(s.running)

########NEW FILE########
__FILENAME__ = sm_centos
import os
import subprocess

from ajenti.api import *
from ajenti.api.helpers import subprocess_call_background, subprocess_check_output_background
from ajenti.util import cache_value

from api import ServiceManager
from sm_sysvinit import SysVInitService


@plugin
class CentOSServiceManager (ServiceManager):
    platforms = ['centos']

    @cache_value(1)
    def get_all(self):
        r = []
        pending = {}
        for line in subprocess_check_output_background(['chkconfig', '--list']).splitlines():
            tokens = line.split()
            if len(tokens) < 3:
                continue

            name = tokens[0]
            s = SysVInitService(name)
            pending[s] = s._begin_refresh()
            r.append(s)

        for s, v in pending.iteritems():
            s._end_refresh(v)
        return r

    def get_one(self, name):
        s = SysVInitService(name)
        if os.path.exists(s.script):
            s.refresh()
            return s
        return None

########NEW FILE########
__FILENAME__ = sm_freebsd
import os
import subprocess

from ajenti.api import *
from ajenti.util import cache_value

from api import Service, ServiceManager


@plugin
class FreeBSDServiceManager (ServiceManager):
    platforms = ['freebsd']

    @cache_value(1)
    def get_all(self):
        r = []
        dirs = ['/etc/rc.d', '/usr/local/etc/rc.d']
        for line in subprocess.check_output(['service', '-l']).splitlines():
            if line:
                for d in dirs:
                    if os.path.exists(os.path.join(d, line)):
                        s = FreeBSDService(line, d)
                        try:
                            s.refresh()
                            r.append(s)
                        except OSError:
                            pass
        return r


class FreeBSDService (Service):
    source = 'rc.d'

    def __init__(self, name, dir):
        self.name = name
        self.script = os.path.join(dir, self.name)

    def refresh(self):
        self.running = subprocess.call([self.script, 'status']) == 0

    def start(self):
        self.command('start')

    def stop(self):
        self.command('stop')

    def restart(self):
        self.command('restart')

    def command(self, cmd):
        subprocess.call([self.script, cmd])

########NEW FILE########
__FILENAME__ = sm_systemd
import dbus
import os

import subprocess
import logging

from ajenti.api import *
from ajenti.util import cache_value

from api import Service, ServiceManager


@plugin
class SystemdServiceManager (ServiceManager):
    platforms = ['arch']

    def init(self):
        self.bus = dbus.SystemBus()
        self.systemd = self.bus.get_object("org.freedesktop.systemd1", "/org/freedesktop/systemd1")
        self.interface = dbus.Interface(self.systemd, 'org.freedesktop.systemd1.Manager')

    @cache_value(1)
    def get_all(self):
        try:
            units = self.interface.ListUnits()
            r = []
            logging.debug('units size: %i' % len(units))
            for unit in units:
                if (unit[0].endswith('.service')):
                    #logging.debug('================== service ==================')
                    #logging.debug('unit: %s' % unit[0])
                    #logging.debug('desc: %s' % unit[1])
                    #logging.debug('status: %s' % unit[2])
                    #logging.debug('isactive: %s' % unit[3])
                    #logging.debug('plugged: %s' % unit[4])
                    #logging.debug('path: %s' % unit[6])

                    s = SystemdService(os.path.splitext(str(unit[0]))[0])
                    s.running = (str(unit[4]) == 'running')
                    r.append(s)

            return r
        except dbus.DBusException:
            return []


class SystemdService (Service):
    source = 'systemd'

    def __init__(self, name):
        self.name = name

    def refresh(self):
        self.running = 'running' in subprocess.check_output(['systemctl', 'status', self.name])

    def start(self):
        self.command('start')

    def stop(self):
        self.command('stop')

    def restart(self):
        self.command('restart')

    def command(self, cmd):
        subprocess.Popen(['systemctl', cmd,  self.name], close_fds=True).wait()

########NEW FILE########
__FILENAME__ = sm_sysvinit
import gevent
import logging
import os
import subprocess

from ajenti.api import *
from ajenti.api.helpers import subprocess_call_background, subprocess_check_output_background
from ajenti.util import cache_value

from api import Service, ServiceManager


@plugin
class SysVInitServiceManager (ServiceManager):
    platforms = ['debian']

    @cache_value(1)
    def get_all(self):
        r = []
        for line in subprocess_check_output_background(['service', '--status-all']).splitlines():
            tokens = line.split()
            if len(tokens) < 3:
                continue

            name = tokens[3]
            status = tokens[1]
            if status == '?':
                continue

            s = SysVInitService(name)
            s.running = status == '+'
            r.append(s)
        return r

    def get_one(self, name):
        s = SysVInitService(name)
        if os.path.exists(s.script):
            s.refresh()
            return s
        return None


class SysVInitService (Service):
    source = 'sysvinit'

    def __init__(self, name):
        self.name = name
        self.script = '/etc/init.d/%s' % self.name

    def refresh(self):
        self.running = subprocess.call([self.script, 'status']) == 0

    def _begin_refresh(self):
        return subprocess.Popen([self.script, 'status'])

    def _end_refresh(self, v):
        v.wait()
        self.running = v.returncode == 0

    def start(self):
        self.command('start')

    def stop(self):
        self.command('stop')

    def restart(self):
        self.command('restart')

    def command(self, cmd):
        try:
            p = subprocess.Popen([self.script, cmd], close_fds=True)
            gevent.sleep(0)
            p.wait()
        except OSError, e:
            logging.warn('service script failed: %s - %s' % (self.script, e))

########NEW FILE########
__FILENAME__ = sm_upstart
try:
    import dbus
except ImportError:
    pass

import gevent
import subprocess

from ajenti.api import *
from ajenti.api.helpers import subprocess_call_background, subprocess_check_output_background
from ajenti.util import cache_value

from api import Service, ServiceManager


@plugin
class UpstartServiceManager (ServiceManager):
    platforms = ['debian']

    def init(self):
        self.bus = dbus.SystemBus()
        self.upstart = self.bus.get_object("com.ubuntu.Upstart", "/com/ubuntu/Upstart")

    @classmethod
    def verify(cls):
        try:
            c = cls()
            c.init()
            return True
        except:
            return False

    @cache_value(1)
    def get_all(self):
        try:
            jobs = self.upstart.GetAllJobs(dbus_interface="com.ubuntu.Upstart0_6")
            r = []
            for job in jobs:
                obj = self.bus.get_object("com.ubuntu.Upstart", job)
                jprops = obj.GetAll("com.ubuntu.Upstart0_6.Job", dbus_interface=dbus.PROPERTIES_IFACE)

                s = UpstartService(str(jprops['name']))

                paths = obj.GetAllInstances(dbus_interface="com.ubuntu.Upstart0_6.Job")
                if len(paths) > 0:
                    instance = self.bus.get_object("com.ubuntu.Upstart", paths[0])
                    iprops = instance.GetAll("com.ubuntu.Upstart0_6.Instance", dbus_interface=dbus.PROPERTIES_IFACE)
                    s.running = str(iprops['state']) == 'running'
                else:
                    s.running = False

                r.append(s)
            return r
        except dbus.DBusException:
            return []


class UpstartService (Service):
    source = 'upstart'

    def __init__(self, name):
        self.name = name

    def refresh(self):
        self.running = 'running' in subprocess.check_output(['status', self.name])

    def start(self):
        p = subprocess.Popen(['start', self.name], close_fds=True)
        gevent.sleep(0)
        p.wait()

    def stop(self):
        p = subprocess.Popen(['stop', self.name], close_fds=True)
        gevent.sleep(0)
        p.wait()

    def restart(self):
        p = subprocess.Popen(['restart', self.name], close_fds=True)
        gevent.sleep(0)
        p.wait()

    def command(self, cmd):
        subprocess.Popen(['/etc/init.d/%s' % self.name, cmd], close_fds=True).wait()

########NEW FILE########
__FILENAME__ = widget
from ajenti.api import plugin
from ajenti.plugins.dashboard.api import ConfigurableWidget
from ajenti.ui import on

from api import ServiceMultiplexor


@plugin
class ServiceWidget (ConfigurableWidget):
    name = _('Service')
    icon = 'play'

    def on_prepare(self):
        self.mgr = ServiceMultiplexor.get()
        self.append(self.ui.inflate('services:widget'))

    def on_start(self):
        self.service = self.mgr.get_one(self.config['service'])
        if not self.service:
            return
        self.find('name').text = self.service.name
        self.find('icon').icon = self.service.icon
        self.find('start').visible = not self.service.running
        self.find('stop').visible = self.service.running
        self.find('restart').visible = self.service.running

    def create_config(self):
        return {'service': ''}

    def on_config_start(self):
        service_list = self.dialog.find('service')
        service_list.labels = service_list.values = [x.name for x in self.mgr.get_all()]
        service_list.value = self.config['service']

    def on_config_save(self):
        self.config['service'] = self.dialog.find('service').value

    @on('start', 'click')
    def on_s_start(self):
        self.service.start()
        self.on_start()

    @on('restart', 'click')
    def on_s_restart(self):
        self.service.restart()
        self.on_start()

    @on('stop', 'click')
    def on_s_stop(self):
        self.service.stop()
        self.on_start()

########NEW FILE########
__FILENAME__ = widget
import subprocess
import re
import os

from ajenti.api import plugin
from ajenti.api.sensors import Sensor
from ajenti.plugins.dashboard.api import ConfigurableWidget


@plugin
class SMARTSensor (Sensor):
    id = 'smart'
    timeout = 5

    def get_variants(self):
        r = []
        for s in os.listdir('/dev'):
            if re.match('sd.$|hd.$|scd.$|fd.$|ad.+$', s):
                r.append(s)
        return sorted(r)

    def measure(self, path):
        """
        -1 = No SMART
        0  = DISK FAILING
        1  = PRE-FAIL
        2  = Unknown error
        3  = Errors in log
        4  = DISK OK
        """
        if not path:
            return -1
        r = subprocess.call(['smartctl', '-H', '/dev/' + path])
        if r & 2:
            return -1
        if r & 8:
            return 0
        if r & 16:
            return 1
        if r & 64:
            return 3
        if r == 0:
            return 4
        return 2


@plugin
class SMARTWidget (ConfigurableWidget):
    name = 'S.M.A.R.T.'
    icon = 'hdd'

    def on_prepare(self):
        self.sensor = Sensor.find('smart')
        self.append(self.ui.inflate('smartctl:widget'))

    def on_start(self):
        self.find('device').text = self.config['device']
        v = self.sensor.value(self.config['device'])
        v = {
            -1: _('No data'),
            0: _('FAILING'),
            1: _('PRE-FAIL'),
            2: _('Unknown error'),
            3: _('Errors in log'),
            4: 'OK'
        }[v]
        self.find('value').text = v

    def create_config(self):
        return {'device': ''}

    def on_config_start(self):
        device_list = self.dialog.find('device')
        lst = self.sensor.get_variants()
        device_list.labels = lst
        device_list.values = lst
        device_list.value = self.config['device']

    def on_config_save(self):
        self.config['device'] = self.dialog.find('device').value

########NEW FILE########
__FILENAME__ = main
from ajenti.api import *
from ajenti.ui.binder import Binder
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.util import platform_select

from reconfigure.configs import SquidConfig
from reconfigure.items.squid import ACLData, HTTPAccessData, HTTPPortData, HTTPSPortData, ArgumentData


@plugin
class Squid (SectionPlugin):
    def init(self):
        self.title = 'Squid'
        self.icon = 'exchange'
        self.category = _('Software')
        self.append(self.ui.inflate('squid:main'))

        self.find('servicebar').name = platform_select(
            debian='squid3',
            centos='squid',
            default='squid',
        )
        self.find('servicebar').reload()

        self.binder = Binder(None, self.find('config'))
        self.find('acl').new_item = lambda c: ACLData(name='new')
        self.find('http_access').new_item = lambda c: HTTPAccessData()
        self.find('http_port').new_item = lambda c: HTTPPortData()
        self.find('https_port').new_item = lambda c: HTTPSPortData()
        for e in self.nearest(lambda x: x.id == 'options'):
            e.new_item = lambda c: ArgumentData()
        self.config = SquidConfig(path='/etc/squid3/squid.conf')

    def on_page_load(self):
        self.refresh()

    def refresh(self):
        self.config.load()
        self.binder.setup(self.config.tree).populate()

    @on('save', 'click')
    def on_save(self):
        self.binder.update()
        self.config.save()
        self.refresh()

########NEW FILE########
__FILENAME__ = client
import subprocess

from ajenti.api import *
from ajenti.api.helpers import subprocess_check_output_background
from ajenti.plugins.services.api import Service, ServiceManager


@plugin
@persistent
@rootcontext
class SupervisorServiceManager (ServiceManager):
    def test(self):
        return subprocess.call(['supervisorctl', 'status']) == 0

    def run(self, *cmds):
        return subprocess_check_output_background(['supervisorctl'] + list(cmds))

    def _parse_status_line(self, l):
        l = l.split(None, 2)
        s = SupervisorService()
        s.name = l[0]
        s.running = len(l) > 2 and l[1] == 'RUNNING'
        s.status = l[2] if len(l) > 2 else ''
        return s

    def get_all(self):
        r = []
        try:
            lines = self.run('status').splitlines()
        except:
            return []

        for l in lines:
            if l:
                r.append(self._parse_status_line(l))
        return r

    def get_one(self, name):
        try:
            lines = self.run('status', name).splitlines()
        except:
            return None

        for l in lines:
            if l:
                if l.strip().endswith(name):
                    return None
                return self._parse_status_line(l)

    def fill(self, programs):
        for p in programs:
            p.status = ''
            p.icon = ''
        for s in self.get_all():
            for p in programs:
                if p.name == s.name:
                    p.running = s.running
                    p.status = s.status
                    p.icon = 'play' if p.running else None


class SupervisorService (Service):
    source = 'supervisord'

    def __init__(self):
        self.name = None
        self.running = False

    def run(self, *cmds):
        return subprocess.check_output(['supervisorctl'] + list(cmds))

    @property
    def icon(self):
        return 'play' if self.running else None

    def start(self):
        self.run('start', self.name)

    def stop(self):
        self.run('stop', self.name)

    def restart(self):
        self.run('restart', self.name)

    def tail(self, id):
        return self.run('tail', self.name)

    def refresh(self):
        self.running = SupervisorServiceManager.get().get_one(self.name).running

########NEW FILE########
__FILENAME__ = main
from ajenti.api import *
from ajenti.ui.binder import Binder
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.util import platform_select

from reconfigure.configs import SupervisorConfig
from reconfigure.items.supervisor import ProgramData

from client import SupervisorServiceManager


@plugin
class Supervisor (SectionPlugin):
    def init(self):
        self.title = 'Supervisor'
        self.icon = 'play'
        self.category = _('Software')
        self.append(self.ui.inflate('supervisor:main'))
        self.mgr = SupervisorServiceManager.get()
        self.binder = Binder(None, self.find('main'))
        self.find('programs').new_item = lambda c: ProgramData()
        self.config = SupervisorConfig(path=platform_select(
            default='/etc/supervisor/supervisord.conf',
            centos='/etc/supervisord.conf',
        ))
        self.find('servicebar').name = platform_select(
            centos='supervisord',
            default='supervisor',
        )
        self.find('servicebar').reload()

    def on_page_load(self):
        self.refresh()

    def refresh(self):
        self.config.load()
        self.mgr.fill(self.config.tree.programs)
        self.binder.setup(self.config.tree).populate()

    @on('save', 'click')
    def on_save(self):
        self.binder.update()
        self.config.save()
        self.refresh()

########NEW FILE########
__FILENAME__ = main
import psutil
import os

from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui.binder import Binder

from ajenti.profiler import *

def get(value):
    '''
    psutil 2 compatibility layer
    '''
    return value() if callable(value) else value

@plugin
class TaskManager (SectionPlugin):
    def init(self):
        self.title = _('Processes')
        self.icon = 'th-list'
        self.category = _('System')
        self.append(self.ui.inflate('taskmgr:main'))

        def post_item_bind(object, collection, item, ui):
            ui.find('term').on('click', self.on_term, item)
            ui.find('kill').on('click', self.on_kill, item)

        self.find('processes').post_item_bind = post_item_bind

        self.binder = Binder(None, self)
        self.sorting = '_cpu'
        self.sorting_reverse = True

        for x in ['_cpu', 'pid', '_sort_ram', '_sort_name']:
            self.find('sort-by-' + x).on('click', self.sort, x)

    def on_page_load(self):
        self.refresh()

    def sort(self, by):
        if self.sorting == by:
            self.sorting_reverse = not self.sorting_reverse
        else:
            self.sorting_reverse = by in ['_cpu', '_ram']
        self.sorting = by
        self.refresh()

    def refresh(self):
        self.processes = list(psutil.process_iter())
        for p in self.processes:
            try:
                p._name = get(p.name)
                p._cmd = ' '.join(get(p.cmdline))
                p._cpu = p.get_cpu_percent(interval=0)
                p._ram = '%i K' % int(p.get_memory_info()[0] / 1024)
                p._ppid = get(p.ppid)
                p._sort_ram = p.get_memory_info()[0]
                p._sort_name = get(p.name).lower()
                try:
                    p._username = get(p.username)
                except:
                    p._username = '?'
            except psutil.NoSuchProcess:
                self.processes.remove(p)

        self.processes = sorted(self.processes, key=lambda x: getattr(x, self.sorting, None), reverse=self.sorting_reverse)
        self.binder.setup(self).populate()

    def on_term(self, p):
        os.kill(p.pid, 15)
        self.refresh()

    def on_kill(self, p):
        os.kill(p.pid, 9)
        self.refresh()

########NEW FILE########
__FILENAME__ = api
import gevent
import logging
import traceback
import uuid

from ajenti.api import *


class TaskResult (object):
    SUCCESS = 0
    ABORTED = 1
    ERROR = 2
    CRASH = 3

    def __init__(self):
        self.result = TaskResult.SUCCESS
        self.output = ''
        self.name = None


class TaskError (Exception):
    pass


@interface
class Task (object):
    """
    Base class for custom tasks

    :param name: display name
    :param ui: full layout name for parameter editor, will be bound to parameter dictionary (so begin it with <bind:dict bind="params">)
    :param hidden: if True, task won't be available for manual creation
    """

    name = '---'
    ui = None
    hidden = False

    def __init__(self, **kwargs):
        self.params = kwargs

    def init(self):
        self._progress = 0
        self._progress_max = 1
        self.running = False
        self.complete = False
        self.pending = False
        self.aborted = False
        self.parallel = False
        self.message = ''
        self.result = TaskResult()
        self.callback = lambda x: None

    def start(self):
        self.thread = gevent.spawn(self._run)

    def _run(self):
        logging.info('Starting task %s' % self.__class__.__name__)
        self.running = True
        self.result.name = self.name
        try:
            self.run(**self.params)
            self.result.result = TaskResult.SUCCESS
        except TaskError, e:
            self.result.result = TaskResult.ERROR
            self.result.output = e.message
        except Exception, e:
            traceback.print_exc()
            self.result.result = TaskResult.CRASH
            self.result.output = str(e)
            logging.exception(str(e))
        self.running = False
        self.complete = True
        logging.info('Task %s complete (%s)' % (self.__class__.__name__, 'aborted' if self.aborted else 'success'))
        self.callback(self)

    def run(**kwargs):
        """
        Override with your task actions here.
        Raise :class:`TaskError` in case of emergency.
        Check `aborted` often and return if it's True
        """

    def abort(self):
        if not self.running:
            return
        self.aborted = True
        self.result.result = TaskResult.ABORTED
        self.thread.join()

    def set_progress(self, current, max):
        self._progress, self._progress_max = current, max

    def get_progress(self):
        return self._progress, self._progress_max


class TaskDefinition (object):
    def __init__(self, j={}, task_class=None):
        self.name = j.get('name', 'unnamed')
        self.parallel = j.get('parallel', False)
        self.task_class = j.get('task_class', task_class)
        self.params = j.get('params', self.get_class().default_params.copy() if self.get_class() else {})
        self.id = j.get('id', str(uuid.uuid4()))

    def get_class(self):
        for task in Task.get_classes():
            if task.classname == self.task_class:
                return task

    def save(self):
        return {
            'name': self.name,
            'task_class': self.task_class,
            'params': self.params,
            'id': self.id,
        }


class JobDefinition (object):
    def __init__(self, j={}):
        self.name = j.get('name', 'unnamed')
        self.task_id = j.get('task_id', None)
        self.id = j.get('id', str(uuid.uuid4()))
        self.schedule_special = j.get('schedule_special', None)
        self.schedule_minute = j.get('schedule_minute', '0')
        for _ in ['hour', 'day_of_month', 'month', 'day_of_week']:
            setattr(self, 'schedule_' + _, j.get('schedule_' + _, '*'))

    def save(self):
        return {
            'name': self.name,
            'task_id': self.task_id,
            'id': self.id,
            'schedule_special': self.schedule_special,
            'schedule_minute': self.schedule_minute,
            'schedule_hour': self.schedule_hour,
            'schedule_day_of_month': self.schedule_day_of_month,
            'schedule_month': self.schedule_month,
            'schedule_day_of_week': self.schedule_day_of_week,
        }

########NEW FILE########
__FILENAME__ = main
from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.plugins import manager
from ajenti.ui import on
from ajenti.ui.binder import Binder, DictAutoBinding

from api import Task, TaskDefinition, JobDefinition
from manager import TaskManager


@plugin
class Tasks (SectionPlugin):
    def init(self):
        self.title = _('Tasks')
        self.icon = 'cog'
        self.category = _('Tools')

        self.append(self.ui.inflate('tasks:main'))

        self.manager = TaskManager.get()
        self.binder = Binder(None, self)

        def post_td_bind(object, collection, item, ui):
            if item.get_class():
                params_ui = self.ui.inflate(item.get_class().ui)
                item.binder = DictAutoBinding(item, 'params', params_ui.find('bind'))
                item.binder.populate()
                ui.find('slot').empty()
                ui.find('slot').append(params_ui)

        def post_td_update(object, collection, item, ui):
            if hasattr(item, 'binder'):
                item.binder.update()

        def post_rt_bind(object, collection, item, ui):
            def abort():
                item.abort()
                self.refresh()
            ui.find('abort').on('click', abort)

        self.find('task_definitions').post_item_bind = post_td_bind
        self.find('task_definitions').post_item_update = post_td_update
        self.find('running_tasks').post_item_bind = post_rt_bind

        self.find('job_definitions').new_item = lambda c: JobDefinition()

    def on_page_load(self):
        self.refresh()

    @on('refresh', 'click')
    def refresh(self):
        self.manager.refresh()

        self.binder.unpopulate()

        dd = self.find('task-classes')
        dd.labels = []
        dd.values = []
        for task in Task.get_classes():
            if not task.hidden:
                dd.labels.append(task.name)
                dd.values.append(task.classname)

        dd = self.find('task-selector')
        dd.labels = [_.name for _ in self.manager.task_definitions]
        dd.values = [_.id for _ in self.manager.task_definitions]
        self.find('run-task-selector').labels = dd.labels
        self.find('run-task-selector').values = dd.values

        self.binder.setup(self.manager).populate()

    @on('run-task', 'click')
    def on_run_task(self):
        self.manager.run(task_id=self.find('run-task-selector').value, context=self.context)
        self.refresh()

    @on('create-task', 'click')
    def on_create_task(self):
        cls = self.find('task-classes').value
        td = TaskDefinition(task_class=cls)
        td.name = td.get_class().name

        self.manager.task_definitions.append(td)
        self.refresh()

    @on('save', 'click')
    def on_save(self):
        self.binder.update()
        self.manager.save()
        self.refresh()

########NEW FILE########
__FILENAME__ = manager
from datetime import datetime

from ajenti.api import *
from ajenti.ipc import IPCHandler
from ajenti.plugins import manager

from api import TaskDefinition, JobDefinition
from ajenti.plugins.cron.api import CronManager
from reconfigure.items.crontab import CrontabNormalTaskData, CrontabSpecialTaskData


@plugin
@rootcontext
class TaskManager (BasePlugin):
    classconfig_root = True
    default_classconfig = {
        'task_definitions': []
    }

    def init(self):
        self.task_definitions = [TaskDefinition(_) for _ in self.classconfig['task_definitions']]
        self.job_definitions = [JobDefinition(_) for _ in self.classconfig.get('job_definitions', [])]
        self.running_tasks = []
        self.pending_tasks = []
        self.result_log = []

    @property
    def all_tasks(self):
        return self.running_tasks + self.pending_tasks

    def save(self):
        self.classconfig['task_definitions'] = [_.save() for _ in self.task_definitions]
        self.classconfig['job_definitions'] = [_.save() for _ in self.job_definitions]
        self.save_classconfig()

        prefix = 'ajenti-ipc tasks run '

        tab = CronManager.get().load_tab('root')
        for item in list(tab.tree.normal_tasks):
            if item.command.startswith(prefix):
                tab.tree.normal_tasks.remove(item)
        for item in list(tab.tree.special_tasks):
            if item.command.startswith(prefix):
                tab.tree.special_tasks.remove(item)

        for job in self.job_definitions:
            if job.schedule_special:
                e = CrontabSpecialTaskData()
                e.special = job.schedule_special
                e.command = prefix + job.task_id
                tab.tree.special_tasks.append(e)
            else:
                e = CrontabNormalTaskData()
                e.minute = job.schedule_minute
                e.hour = job.schedule_hour
                e.day_of_month = job.schedule_day_of_month
                e.month = job.schedule_month
                e.day_of_week = job.schedule_day_of_week
                e.command = prefix + job.task_id
                tab.tree.normal_tasks.append(e)

        CronManager.get().save_tab('root', tab)

    def task_done(self, task):
        task.time_completed = datetime.now()
        task.result.time_started = task.time_started
        task.result.duration = task.time_completed - task.time_started
        if task.execution_context:
            task.execution_context.notify('info', _('Task %s finished') % task.name)
        if task in self.running_tasks:
            self.result_log = [task.result] + self.result_log[:9]
            self.running_tasks.remove(task)
        if not self.running_tasks:
            if self.pending_tasks:
                t = self.pending_tasks.pop(0)
                self.run(task=t)

    def refresh(self):
        complete_tasks = [task for task in self.running_tasks if task.complete]
        for task in complete_tasks:
            self.running_tasks.remove(task)

    def run(self, task=None, task_definition=None, task_id=None, context=None):
        if task_id is not None:
            for td in self.task_definitions:
                if td.id == task_id:
                    task_definition = td
                    break
            else:
                raise IndexError('Task not found')

        if task_definition is not None:
            task = task_definition.get_class().new(**task_definition.params)
            task.definition = task_definition
            task.parallel = task_definition.parallel

        task.time_started = datetime.now()
        task.execution_context = context

        if not task.parallel and self.running_tasks:
            self.pending_tasks.append(task)
            task.pending = True
            if task.execution_context:
                task.execution_context.notify('info', _('Task %s queued') % task.name)
        else:
            self.running_tasks.append(task)
            task.pending = False

            old_callback = task.callback
            def new_callback(task):
                old_callback(task)
                self.task_done(task)
            task.callback = new_callback

            if task.execution_context:
                task.execution_context.notify('info', _('Task %s started') % task.name)
            task.start()


@plugin
class TasksIPC (IPCHandler):
    def init(self):
        self.manager = TaskManager.get()

    def get_name(self):
        return 'tasks'

    def handle(self, args):
        command, task_id = args
        if command == 'run':
            self.manager.run(task_id=task_id)

        return ''

########NEW FILE########
__FILENAME__ = tasks
import logging
import os
import gevent
import subprocess

from ajenti.api import *

from api import Task, TaskError



@plugin
class CommandTask (Task):
    name = 'Execute command'
    ui = 'tasks:params-execute'
    default_params = {
        'command': '',
    }

    def run(self, command=None):
        p = subprocess.Popen(command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        o,e = p.communicate()
        if p.returncode:
            raise TaskError(o + e)
        else:
            self.result.output = o


@plugin
class CopyFilesTask (Task):
    name = 'Copy files'
    ui = 'tasks:params-copydir'
    command = ['cp', '-rp']
    message_template = _('Copying %s')
    default_params = {
        'source': '',
        'destination': '',
    }

    def run(self, source=None, destination=None):
        index = 0
        if isinstance(source, basestring):
            source = [source]

        if not os.path.exists(destination):
            os.makedirs(destination)
        if not destination.endswith('/'):
            destination += '/'

        for file in source:
            self.message = self.message_template % file
            p = subprocess.Popen(self.command + [file, destination])
            while p.poll() is None:
                gevent.sleep(1)
                if self.aborted:
                    p.terminate()
                    return
            index += 1
            self.set_progress(index, len(source))


@plugin
class MoveFilesTask (CopyFilesTask):
    name = 'Move files'
    command = ['mv']
    message_template = _('Moving %s')


@plugin
class RSyncTask (Task):
    name = 'RSync'
    ui = 'tasks:params-rsync'
    default_params = {
        'source': '',
        'destination': '',
        'archive': True,
        'recursive': True,
        'times': True,
        'xattrs': True,
        'delete': False,
        'perms': True,
    }

    def run(self, source=None, destination=None, **kwargs):
        cmd = ['rsync']
        for opt in ['archive', 'recursive', 'times', 'xattrs', 'delete', 'perms']:
            if kwargs.get(opt, self.default_params[opt]):
                cmd += ['--' + opt]
        cmd += [source, destination]
        logging.info('RSync: ' + ' '.join(cmd))
        p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)  
        o, e = p.communicate()
        if p.returncode:
            raise TaskError(o + e)

########NEW FILE########
__FILENAME__ = main
from base64 import b64decode, b64encode
import gevent
import gevent.event
import json
from PIL import Image, ImageDraw
import StringIO
import zlib
import logging

from ajenti.api import *
from ajenti.api.http import HttpPlugin, url, SocketPlugin
from ajenti.plugins.configurator.api import ClassConfigEditor
from ajenti.plugins.main.api import SectionPlugin, intent
from ajenti.ui import UIElement, p, on
from ajenti.users import PermissionProvider, restrict

from terminal import Terminal


@plugin
class TerminalClassConfigEditor (ClassConfigEditor):
    title = _('Terminal')
    icon = 'list-alt'

    def init(self):
        self.append(self.ui.inflate('terminal:config'))


@plugin
class Terminals (SectionPlugin):
    default_classconfig = {'shell': 'sh -c $SHELL || bash'}
    classconfig_editor = TerminalClassConfigEditor

    def init(self):
        self.title = _('Terminal')
        self.icon = 'list-alt'
        self.category = _('Tools')

        self.append(self.ui.inflate('terminal:main'))

        self.terminals = {}
        self.context.session.terminals = self.terminals

    def on_page_load(self):
        self.refresh()

    @intent('terminals:refresh')
    def refresh(self):
        ulist = self.find('list')
        ulist.empty()
        self.find('empty').visible = len(self.terminals) == 0
        for k, v in list(self.terminals.iteritems()):
            if v.autoclose and v.dead():
                self.terminals.pop(k)
        for k in sorted(self.terminals.keys()):
            thumb = TerminalThumbnail(self.ui)
            thumb.tid = k
            thumb.on('close', self.on_close, k)
            ulist.append(thumb)

    @intent('terminal')
    def launch(self, command=None, callback=None):
        self.on_new(command, autoclose=True, autoopen=True, callback=callback)

    @on('new-button', 'click')
    @restrict('terminal:shell')
    def on_new(self, command=None, autoopen=False, autoclose=False, callback=None, **kwargs):
        if not command:
            command = self.classconfig['shell']
        if self.terminals:
            key = sorted(self.terminals.keys())[-1] + 1
        else:
            key = 0
        url = '/ajenti:terminal/%i' % key

        def _callback(exitcode=None):
            if callback:
                callback()
            if autoclose and exitcode == 0:
                self.context.endpoint.send_close_tab(url)

        self.terminals[key] = Terminal(command, autoclose=autoclose, callback=_callback, **kwargs)
        self.refresh()
        if autoopen:
            self.context.endpoint.send_open_tab(url, 'Terminal %i' % key)
        return key

    @on('run-button', 'click')
    @restrict('terminal:custom')
    def on_run(self):
        self.on_new(self.find('command').value, autoclose=True, autoopen=True)

    def on_close(self, k):
        self.terminals[k].kill()
        self.terminals.pop(k)
        self.refresh()


@plugin
class TerminalHttp (BasePlugin, HttpPlugin):
    colors = {
        'green': '#859900',
        'white': '#eee8d5',
        'yellow': '#b58900',
        'red': '#dc322f',
        'magenta': '#d33682',
        'violet': '#6c71c4',
        'blue': '#268bd2',
        'cyan': '#2aa198',
    }

    @url('/ajenti:terminal/(?P<id>\d+)')
    def get_page(self, context, id):
        if context.session.identity is None:
            context.respond_redirect('/')
        context.add_header('Content-Type', 'text/html')
        context.respond_ok()
        return self.open_content('static/index.html').read()

    @url('/ajenti:terminal/(?P<id>\d+)/thumbnail')
    def get_thumbnail(self, context, id):
        terminal = context.session.terminals[int(id)]

        img = Image.new("RGB", (terminal.width, terminal.height * 2 + 20))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, terminal.width, terminal.height], fill=(0, 0, 0))

        for y in range(0, terminal.height):
            for x in range(0, terminal.width):
                fc = terminal.screen.buffer[y][x][1]
                if fc == 'default':
                    fc = 'lightgray'
                if fc in self.colors:
                    fc = self.colors[fc]
                fc = ImageDraw.ImageColor.getcolor(fc, 'RGB')
                bc = terminal.screen.buffer[y][x][2]
                if bc == 'default':
                    bc = 'black'
                if bc in self.colors:
                    bc = self.colors[bc]
                bc = ImageDraw.ImageColor.getcolor(bc, 'RGB')
                ch = terminal.screen.buffer[y][x][0]
                draw.point((x, 10 + y * 2 + 1), fill=(fc if ord(ch) > 32 else bc))
                draw.point((x, 10 + y * 2), fill=bc)

        sio = StringIO.StringIO()
        img.save(sio, 'PNG')

        context.add_header('Content-type', 'image/png')
        context.respond_ok()
        return sio.getvalue()


@p('tid', default=0, type=int)
@plugin
class TerminalThumbnail (UIElement):
    typeid = 'terminal:thumbnail'


@plugin
class TerminalSocket (SocketPlugin):
    name = '/terminal'

    def on_connect(self):
        self.emit('re-select')
        self.terminal = None
        self.ready_to_send = gevent.event.Event()
        self.have_data = gevent.event.Event()

    def on_message(self, message):
        if message['type'] == 'select':
            self.id = int(message['tid'])
            try:
                self.terminal = self.context.session.terminals.get(self.id)
            except AttributeError:
                logging.error('Cannot assign terminal')
                self.terminal = None

            if self.terminal is None:
                url = '/ajenti:terminal/%i' % self.id
                self.context.endpoint.send_close_tab(url)
                return
            self.send_data(self.terminal.protocol.history())
            self.spawn(self.worker)
            self.spawn(self.sender)
        if message['type'] == 'key':
            if self.terminal:
                ch = b64decode(message['key'])
                self.terminal.write(ch)
                self.ready_to_send.set()
        if message['type'] == 'read':
            self.ready_to_send.set()

    def worker(self):
        while True:
            self.terminal.protocol.read(timeout=1)
            if self.terminal.protocol.has_updates():
                self.have_data.set()
            if self.terminal.dead():
                del self.context.session.terminals[self.id]
                self.context.launch('terminals:refresh')
                return

    def sender(self):
        while True:
            self.ready_to_send.wait()
            self.have_data.wait()
            data = self.terminal.protocol.format()
            self.have_data.clear()
            self.send_data(data)
            self.ready_to_send.clear()
            if self.terminal.dead():
                return
        
    def send_data(self, data):
        data = b64encode(zlib.compress(json.dumps(data))[2:-4])
        self.emit('set', data)


@plugin
class TerminalPermissionsProvider (PermissionProvider):
    def get_name(self):
        return _('Terminal')

    def get_permissions(self):
        return [
            ('terminal:shell', _('Run shell')),
            ('terminal:custom', _('Run custom commands')),
        ]

########NEW FILE########
__FILENAME__ = charsets
# -*- coding: utf-8 -*-
"""
    pyte.charsets
    ~~~~~~~~~~~~~

    This module defines ``G0`` and ``G1`` charset mappings the same way
    they are defined for linux terminal, see
    ``linux/drivers/tty/consolemap.c`` @ http://git.kernel.org

    .. note:: ``VT100_MAP`` and ``IBMPC_MAP`` were taken unchanged
              from linux kernel source and therefore are licensed
              under **GPL**.

    :copyright: (c) 2011-2013 by Selectel, see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import unicode_literals

import sys

if sys.version_info[0] == 2:
    chr = unichr


#: Latin1.
LAT1_MAP = list(map(chr, range(256)))

#: VT100 graphic character set.
VT100_MAP = "".join(chr(c) for c in [
    0x0000, 0x0001, 0x0002, 0x0003, 0x0004, 0x0005, 0x0006, 0x0007,
    0x0008, 0x0009, 0x000a, 0x000b, 0x000c, 0x000d, 0x000e, 0x000f,
    0x0010, 0x0011, 0x0012, 0x0013, 0x0014, 0x0015, 0x0016, 0x0017,
    0x0018, 0x0019, 0x001a, 0x001b, 0x001c, 0x001d, 0x001e, 0x001f,
    0x0020, 0x0021, 0x0022, 0x0023, 0x0024, 0x0025, 0x0026, 0x0027,
    0x0028, 0x0029, 0x002a, 0x2192, 0x2190, 0x2191, 0x2193, 0x002f,
    0x2588, 0x0031, 0x0032, 0x0033, 0x0034, 0x0035, 0x0036, 0x0037,
    0x0038, 0x0039, 0x003a, 0x003b, 0x003c, 0x003d, 0x003e, 0x003f,
    0x0040, 0x0041, 0x0042, 0x0043, 0x0044, 0x0045, 0x0046, 0x0047,
    0x0048, 0x0049, 0x004a, 0x004b, 0x004c, 0x004d, 0x004e, 0x004f,
    0x0050, 0x0051, 0x0052, 0x0053, 0x0054, 0x0055, 0x0056, 0x0057,
    0x0058, 0x0059, 0x005a, 0x005b, 0x005c, 0x005d, 0x005e, 0x00a0,
    0x25c6, 0x2592, 0x2409, 0x240c, 0x240d, 0x240a, 0x00b0, 0x00b1,
    0x2591, 0x240b, 0x2518, 0x2510, 0x250c, 0x2514, 0x253c, 0x23ba,
    0x23bb, 0x2500, 0x23bc, 0x23bd, 0x251c, 0x2524, 0x2534, 0x252c,
    0x2502, 0x2264, 0x2265, 0x03c0, 0x2260, 0x00a3, 0x00b7, 0x007f,
    0x0080, 0x0081, 0x0082, 0x0083, 0x0084, 0x0085, 0x0086, 0x0087,
    0x0088, 0x0089, 0x008a, 0x008b, 0x008c, 0x008d, 0x008e, 0x008f,
    0x0090, 0x0091, 0x0092, 0x0093, 0x0094, 0x0095, 0x0096, 0x0097,
    0x0098, 0x0099, 0x009a, 0x009b, 0x009c, 0x009d, 0x009e, 0x009f,
    0x00a0, 0x00a1, 0x00a2, 0x00a3, 0x00a4, 0x00a5, 0x00a6, 0x00a7,
    0x00a8, 0x00a9, 0x00aa, 0x00ab, 0x00ac, 0x00ad, 0x00ae, 0x00af,
    0x00b0, 0x00b1, 0x00b2, 0x00b3, 0x00b4, 0x00b5, 0x00b6, 0x00b7,
    0x00b8, 0x00b9, 0x00ba, 0x00bb, 0x00bc, 0x00bd, 0x00be, 0x00bf,
    0x00c0, 0x00c1, 0x00c2, 0x00c3, 0x00c4, 0x00c5, 0x00c6, 0x00c7,
    0x00c8, 0x00c9, 0x00ca, 0x00cb, 0x00cc, 0x00cd, 0x00ce, 0x00cf,
    0x00d0, 0x00d1, 0x00d2, 0x00d3, 0x00d4, 0x00d5, 0x00d6, 0x00d7,
    0x00d8, 0x00d9, 0x00da, 0x00db, 0x00dc, 0x00dd, 0x00de, 0x00df,
    0x00e0, 0x00e1, 0x00e2, 0x00e3, 0x00e4, 0x00e5, 0x00e6, 0x00e7,
    0x00e8, 0x00e9, 0x00ea, 0x00eb, 0x00ec, 0x00ed, 0x00ee, 0x00ef,
    0x00f0, 0x00f1, 0x00f2, 0x00f3, 0x00f4, 0x00f5, 0x00f6, 0x00f7,
    0x00f8, 0x00f9, 0x00fa, 0x00fb, 0x00fc, 0x00fd, 0x00fe, 0x00ff
])

#: IBM Codepage 437.
IBMPC_MAP = "".join(chr(c) for c in [
    0x0000, 0x263a, 0x263b, 0x2665, 0x2666, 0x2663, 0x2660, 0x2022,
    0x25d8, 0x25cb, 0x25d9, 0x2642, 0x2640, 0x266a, 0x266b, 0x263c,
    0x25b6, 0x25c0, 0x2195, 0x203c, 0x00b6, 0x00a7, 0x25ac, 0x21a8,
    0x2191, 0x2193, 0x2192, 0x2190, 0x221f, 0x2194, 0x25b2, 0x25bc,
    0x0020, 0x0021, 0x0022, 0x0023, 0x0024, 0x0025, 0x0026, 0x0027,
    0x0028, 0x0029, 0x002a, 0x002b, 0x002c, 0x002d, 0x002e, 0x002f,
    0x0030, 0x0031, 0x0032, 0x0033, 0x0034, 0x0035, 0x0036, 0x0037,
    0x0038, 0x0039, 0x003a, 0x003b, 0x003c, 0x003d, 0x003e, 0x003f,
    0x0040, 0x0041, 0x0042, 0x0043, 0x0044, 0x0045, 0x0046, 0x0047,
    0x0048, 0x0049, 0x004a, 0x004b, 0x004c, 0x004d, 0x004e, 0x004f,
    0x0050, 0x0051, 0x0052, 0x0053, 0x0054, 0x0055, 0x0056, 0x0057,
    0x0058, 0x0059, 0x005a, 0x005b, 0x005c, 0x005d, 0x005e, 0x005f,
    0x0060, 0x0061, 0x0062, 0x0063, 0x0064, 0x0065, 0x0066, 0x0067,
    0x0068, 0x0069, 0x006a, 0x006b, 0x006c, 0x006d, 0x006e, 0x006f,
    0x0070, 0x0071, 0x0072, 0x0073, 0x0074, 0x0075, 0x0076, 0x0077,
    0x0078, 0x0079, 0x007a, 0x007b, 0x007c, 0x007d, 0x007e, 0x2302,
    0x00c7, 0x00fc, 0x00e9, 0x00e2, 0x00e4, 0x00e0, 0x00e5, 0x00e7,
    0x00ea, 0x00eb, 0x00e8, 0x00ef, 0x00ee, 0x00ec, 0x00c4, 0x00c5,
    0x00c9, 0x00e6, 0x00c6, 0x00f4, 0x00f6, 0x00f2, 0x00fb, 0x00f9,
    0x00ff, 0x00d6, 0x00dc, 0x00a2, 0x00a3, 0x00a5, 0x20a7, 0x0192,
    0x00e1, 0x00ed, 0x00f3, 0x00fa, 0x00f1, 0x00d1, 0x00aa, 0x00ba,
    0x00bf, 0x2310, 0x00ac, 0x00bd, 0x00bc, 0x00a1, 0x00ab, 0x00bb,
    0x2591, 0x2592, 0x2593, 0x2502, 0x2524, 0x2561, 0x2562, 0x2556,
    0x2555, 0x2563, 0x2551, 0x2557, 0x255d, 0x255c, 0x255b, 0x2510,
    0x2514, 0x2534, 0x252c, 0x251c, 0x2500, 0x253c, 0x255e, 0x255f,
    0x255a, 0x2554, 0x2569, 0x2566, 0x2560, 0x2550, 0x256c, 0x2567,
    0x2568, 0x2564, 0x2565, 0x2559, 0x2558, 0x2552, 0x2553, 0x256b,
    0x256a, 0x2518, 0x250c, 0x2588, 0x2584, 0x258c, 0x2590, 0x2580,
    0x03b1, 0x00df, 0x0393, 0x03c0, 0x03a3, 0x03c3, 0x00b5, 0x03c4,
    0x03a6, 0x0398, 0x03a9, 0x03b4, 0x221e, 0x03c6, 0x03b5, 0x2229,
    0x2261, 0x00b1, 0x2265, 0x2264, 0x2320, 0x2321, 0x00f7, 0x2248,
    0x00b0, 0x2219, 0x00b7, 0x221a, 0x207f, 0x00b2, 0x25a0, 0x00a0
])


#: VAX42 character set.
VAX42_MAP = "".join(chr(c) for c in [
    0x0000, 0x263a, 0x263b, 0x2665, 0x2666, 0x2663, 0x2660, 0x2022,
    0x25d8, 0x25cb, 0x25d9, 0x2642, 0x2640, 0x266a, 0x266b, 0x263c,
    0x25b6, 0x25c0, 0x2195, 0x203c, 0x00b6, 0x00a7, 0x25ac, 0x21a8,
    0x2191, 0x2193, 0x2192, 0x2190, 0x221f, 0x2194, 0x25b2, 0x25bc,
    0x0020, 0x043b, 0x0022, 0x0023, 0x0024, 0x0025, 0x0026, 0x0027,
    0x0028, 0x0029, 0x002a, 0x002b, 0x002c, 0x002d, 0x002e, 0x002f,
    0x0030, 0x0031, 0x0032, 0x0033, 0x0034, 0x0035, 0x0036, 0x0037,
    0x0038, 0x0039, 0x003a, 0x003b, 0x003c, 0x003d, 0x003e, 0x0435,
    0x0040, 0x0041, 0x0042, 0x0043, 0x0044, 0x0045, 0x0046, 0x0047,
    0x0048, 0x0049, 0x004a, 0x004b, 0x004c, 0x004d, 0x004e, 0x004f,
    0x0050, 0x0051, 0x0052, 0x0053, 0x0054, 0x0055, 0x0056, 0x0057,
    0x0058, 0x0059, 0x005a, 0x005b, 0x005c, 0x005d, 0x005e, 0x005f,
    0x0060, 0x0441, 0x0062, 0x0063, 0x0064, 0x0065, 0x0066, 0x0067,
    0x0435, 0x0069, 0x006a, 0x006b, 0x006c, 0x006d, 0x006e, 0x043a,
    0x0070, 0x0071, 0x0442, 0x0073, 0x043b, 0x0435, 0x0076, 0x0077,
    0x0078, 0x0079, 0x007a, 0x007b, 0x007c, 0x007d, 0x007e, 0x2302,
    0x00c7, 0x00fc, 0x00e9, 0x00e2, 0x00e4, 0x00e0, 0x00e5, 0x00e7,
    0x00ea, 0x00eb, 0x00e8, 0x00ef, 0x00ee, 0x00ec, 0x00c4, 0x00c5,
    0x00c9, 0x00e6, 0x00c6, 0x00f4, 0x00f6, 0x00f2, 0x00fb, 0x00f9,
    0x00ff, 0x00d6, 0x00dc, 0x00a2, 0x00a3, 0x00a5, 0x20a7, 0x0192,
    0x00e1, 0x00ed, 0x00f3, 0x00fa, 0x00f1, 0x00d1, 0x00aa, 0x00ba,
    0x00bf, 0x2310, 0x00ac, 0x00bd, 0x00bc, 0x00a1, 0x00ab, 0x00bb,
    0x2591, 0x2592, 0x2593, 0x2502, 0x2524, 0x2561, 0x2562, 0x2556,
    0x2555, 0x2563, 0x2551, 0x2557, 0x255d, 0x255c, 0x255b, 0x2510,
    0x2514, 0x2534, 0x252c, 0x251c, 0x2500, 0x253c, 0x255e, 0x255f,
    0x255a, 0x2554, 0x2569, 0x2566, 0x2560, 0x2550, 0x256c, 0x2567,
    0x2568, 0x2564, 0x2565, 0x2559, 0x2558, 0x2552, 0x2553, 0x256b,
    0x256a, 0x2518, 0x250c, 0x2588, 0x2584, 0x258c, 0x2590, 0x2580,
    0x03b1, 0x00df, 0x0393, 0x03c0, 0x03a3, 0x03c3, 0x00b5, 0x03c4,
    0x03a6, 0x0398, 0x03a9, 0x03b4, 0x221e, 0x03c6, 0x03b5, 0x2229,
    0x2261, 0x00b1, 0x2265, 0x2264, 0x2320, 0x2321, 0x00f7, 0x2248,
    0x00b0, 0x2219, 0x00b7, 0x221a, 0x207f, 0x00b2, 0x25a0, 0x00a0
])


MAPS = {
    "B": LAT1_MAP,
    "0": VT100_MAP,
    "U": IBMPC_MAP,
    "V": VAX42_MAP
}

########NEW FILE########
__FILENAME__ = control
# -*- coding: utf-8 -*-
"""
    pyte.control
    ~~~~~~~~~~~~

    This module defines simple control sequences, recognized by
    :class:`~pyte.streams.Stream`, the set of codes here is for
    ``TERM=linux`` which is a superset of VT102.

    :copyright: (c) 2011-2013 by Selectel, see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import unicode_literals


#: *Space*: Not suprisingly -- ``" "``.
SP = " "

#: *Null*: Does nothing.
NUL = "\u0000"

#: *Bell*: Beeps.
BEL = "\u0007"

#: *Backspace*: Backspace one column, but not past the begining of the
#: line.
BS = "\u0008"

#: *Horizontal tab*: Move cursor to the next tab stop, or to the end
#: of the line if there is no earlier tab stop.
HT = "\u0009"

#: *Linefeed*: Give a line feed, and, if :data:`pyte.modes.LNM` (new
#: line mode) is set also a carriage return.
LF = "\n"
#: *Vertical tab*: Same as :data:`LF`.
VT = "\u000b"
#: *Form feed*: Same as :data:`LF`.
FF = "\u000c"

#: *Carriage return*: Move cursor to left margin on current line.
CR = "\r"

#: *Shift out*: Activate G1 character set.
SO = "\u000e"

#: *Shift in*: Activate G0 character set.
SI = "\u000f"

#: *Cancel*: Interrupt escape sequence. If received during an escape or
#: control sequence, cancels the sequence and displays substitution
#: character.
CAN = "\u0018"
#: *Substitute*: Same as :data:`CAN`.
SUB = "\u001a"

#: *Escape*: Starts an escape sequence.
ESC = "\u001b"

#: *Delete*: Is ingored.
DEL = "\u007f"

#: *Control sequence introducer*: An equavalent for ``ESC [``.
CSI = "\u009b"

########NEW FILE########
__FILENAME__ = escape
# -*- coding: utf-8 -*-
"""
    pyte.escape
    ~~~~~~~~~~~

    This module defines bot CSI and non-CSI escape sequences, recognized
    by :class:`~pyte.streams.Stream` and subclasses.

    :copyright: (c) 2011-2013 by Selectel, see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import unicode_literals


#: *Reset*.
RIS = "c"

#: *Index*: Move cursor down one line in same column. If the cursor is
#: at the bottom margin, the screen performs a scroll-up.
IND = "D"

#: *Next line*: Same as :data:`pyte.control.LF`.
NEL = "E"

#: Tabulation set: Set a horizontal tab stop at cursor position.
HTS = "H"

#: *Reverse index*: Move cursor up one line in same column. If the
#: cursor is at the top margin, the screen performs a scroll-down.
RI = "M"

#: Save cursor: Save cursor position, character attribute (graphic
#: rendition), character set, and origin mode selection (see
#: :data:`DECRC`).
DECSC = "7"

#: *Restore cursor*: Restore previously saved cursor position, character
#: attribute (graphic rendition), character set, and origin mode
#: selection. If none were saved, move cursor to home position.
DECRC = "8"


# "Sharp" escape sequences.
# -------------------------

#: *Alignment display*: Fill screen with uppercase E's for testing
#: screen focus and alignment.
DECALN = "8"


# ECMA-48 CSI sequences.
# ---------------------

#: *Insert character*: Insert the indicated # of blank characters.
ICH = "@"

#: *Cursor up*: Move cursor up the indicated # of lines in same column.
#: Cursor stops at top margin.
CUU = "A"

#: *Cursor down*: Move cursor down the indicated # of lines in same
#: column. Cursor stops at bottom margin.
CUD = "B"

#: *Cursor forward*: Move cursor right the indicated # of columns.
#: Cursor stops at right margin.
CUF = "C"

#: *Cursor back*: Move cursor left the indicated # of columns. Cursor
#: stops at left margin.
CUB = "D"

#: *Cursor next line*: Move cursor down the indicated # of lines to
#: column 1.
CNL = "E"

#: *Cursor previous line*: Move cursor up the indicated # of lines to
#: column 1.
CPL = "F"

#: *Cursor horizontal align*: Move cursor to the indicated column in
#: current line.
CHA = "G"

#: *Cursor position*: Move cursor to the indicated line, column (origin
#: at ``1, 1``).
CUP = "H"

#: *Erase data* (default: from cursor to end of line).
ED = "J"

#: *Erase in line* (default: from cursor to end of line).
EL = "K"

#: *Insert line*: Insert the indicated # of blank lines, starting from
#: the current line. Lines displayed below cursor move down. Lines moved
#: past the bottom margin are lost.
IL = "L"

#: *Delete line*: Delete the indicated # of lines, starting from the
#: current line. As lines are deleted, lines displayed below cursor
#: move up. Lines added to bottom of screen have spaces with same
#: character attributes as last line move up.
DL = "M"

#: *Delete character*: Delete the indicated # of characters on the
#: current line. When character is deleted, all characters to the right
#: of cursor move left.
DCH = "P"

#: *Erase character*: Erase the indicated # of characters on the
#: current line.
ECH = "X"

#: *Horizontal position relative*: Same as :data:`CUF`.
HPR = "a"

#: *Vertical position adjust*: Move cursor to the indicated line,
#: current column.
VPA = "d"

#: *Vertical position relative*: Same as :data:`CUD`.
VPR = "e"

#: *Horizontal / Vertical position*: Same as :data:`CUP`.
HVP = "f"

#: *Tabulation clear*: Clears a horizontal tab stop at cursor position.
TBC = "g"

#: *Set mode*.
SM = "h"

#: *Reset mode*.
RM = "l"

#: *Select graphics rendition*: The terminal can display the following
#: character attributes that change the character display without
#: changing the character (see :mod:`pyte.graphics`).
SGR = "m"

#: *Select top and bottom margins*: Selects margins, defining the
#: scrolling region; parameters are top and bottom line. If called
#: without any arguments, whole screen is used.
DECSTBM = "r"

#: *Horizontal position adjust*: Same as :data:`CHA`.
HPA = "'"

########NEW FILE########
__FILENAME__ = graphics
# -*- coding: utf-8 -*-
"""
    pyte.graphics
    ~~~~~~~~~~~~~

    This module defines graphic-related constants, mostly taken from
    :manpage:`console_codes(4)` and
    http://pueblo.sourceforge.net/doc/manual/ansi_color_codes.html.

    :copyright: (c) 2011-2013 by Selectel, see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

import itertools


#: A mapping of ANSI text style codes to style names, "+" means the:
#: attribute is set, "-" -- reset; example:
#:
#: >>> text[1]
#: '+bold'
#: >>> text[9]
#: '+strikethrough'
TEXT = {
    1: "+bold" ,
    3: "+italics",
    4: "+underscore",
    7: "+reverse",
    9: "+strikethrough",
    22: "-bold",
    23: "-italics",
    24: "-underscore",
    27: "-reverse",
    29: "-strikethrough"
}


#: A mapping of ANSI foreground color codes to color names, example:
#:
#: >>> FG[30]
#: 'black'
#: >>> FG[38]
#: 'default'
FG = {
    30: "black",
    31: "red",
    32: "green",
    33: "brown",
    34: "blue",
    35: "magenta",
    36: "cyan",
    37: "white",
    39: "default"  # white.
}

#: A mapping of ANSI background color codes to color names, example:
#:
#: >>> BG[40]
#: 'black'
#: >>> BG[48]
#: 'default'
BG = {
    40: "black",
    41: "red",
    42: "green",
    43: "brown",
    44: "blue",
    45: "magenta",
    46: "cyan",
    47: "white",
    49: "default"  # black.
}

# Reverse mapping of all available attributes -- keep this private!
_SGR = dict((v, k) for k, v in itertools.chain(BG.items(),
                                               FG.items(),
                                               TEXT.items()))

########NEW FILE########
__FILENAME__ = modes
# -*- coding: utf-8 -*-
"""
    pyte.modes
    ~~~~~~~~~~

    This module defines terminal mode switches, used by
    :class:`~pyte.screens.Screen`. There're two types of terminal modes:

    * `non-private` which should be set with ``ESC [ N h``, where ``N``
      is an integer, representing mode being set; and
    * `private` which should be set with ``ESC [ ? N h``.

    The latter are shifted 5 times to the right, to be easily
    distinguishable from the former ones; for example `Origin Mode`
    -- :data:`DECOM` is ``192`` not ``6``.

    >>> DECOM
    192

    :copyright: (c) 2011-2013 by Selectel, see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

#: *Line Feed/New Line Mode*: When enabled, causes a received
#: :data:`~pyte.control.LF`, :data:`pyte.control.FF`, or
#: :data:`~pyte.control.VT` to move the cursor to the first column of
#: the next line.
LNM = 20

#: *Insert/Replace Mode*: When enabled, new display characters move
#: old display characters to the right. Characters moved past the
#: right margin are lost. Otherwise, new display characters replace
#: old display characters at the cursor position.
IRM = 4


# Private modes.
# ..............

#: *Text Cursor Enable Mode*: determines if the text cursor is
#: visible.
DECTCEM = 25 << 5

#: *Screen Mode*: toggles screen-wide reverse-video mode.
DECSCNM = 5 << 5

#: *Origin Mode*: allows cursor addressing relative to a user-defined
#: origin. This mode resets when the terminal is powered up or reset.
#: It does not affect the erase in display (ED) function.
DECOM = 6 << 5

#: *Auto Wrap Mode*: selects where received graphic characters appear
#: when the cursor is at the right margin.
DECAWM = 7 << 5

#: *Column Mode*: selects the number of columns per line (80 or 132)
#: on the screen.
DECCOLM = 3 << 5

########NEW FILE########
__FILENAME__ = screens
# -*- coding: utf-8 -*-
"""
    pyte.screens
    ~~~~~~~~~~~~

    This module provides classes for terminal screens, currently
    it contains three screens with different features:

    * :class:`~pyte.screens.Screen` -- base screen implementation,
      which handles all the core escape sequences, recognized by
      :class:`~pyte.streams.Stream`.
    * If you need a screen to keep track of the changed lines
      (which you probably do need) -- use
      :class:`~pyte.screens.DiffScreen`.
    * If you also want a screen to collect history and allow
      pagination -- :class:`pyte.screen.HistoryScreen` is here
      for ya ;)

    .. note:: It would be nice to split those features into mixin
              classes, rather than subclasses, but it's not obvious
              how to do -- feel free to submit a pull request.

    :copyright: (c) 2011-2013 Selectel, see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import absolute_import, unicode_literals, division

import copy
import math
import operator
import sys
from collections import deque, namedtuple
from itertools import islice, repeat

from . import modes as mo, graphics as g, charsets as cs


if sys.version_info[0] == 2:
    from future_builtins import map

    range = xrange


def take(n, iterable):
    """Returns first n items of the iterable as a list."""
    return list(islice(iterable, n))


#: A container for screen's scroll margins.
Margins = namedtuple("Margins", "top bottom")

#: A container for savepoint, created on :data:`~pyte.escape.DECSC`.
Savepoint = namedtuple("Savepoint", [
    "cursor",
    "g0_charset",
    "g1_charset",
    "charset",
    "origin",
    "wrap"
])

#: A container for a single character, field names are *hopefully*
#: self-explanatory.
_Char = namedtuple("_Char", [
    "data",
    "fg",
    "bg",
    "bold",
    "italics",
    "underscore",
    "strikethrough",
    "reverse",
])


class Char(_Char):
    """A wrapper around :class:`_Char`, providing some useful defaults
    for most of the attributes.
    """
    __slots__ = ()

    def __new__(cls, data, fg="default", bg="default", bold=False,
                italics=False, underscore=False, reverse=False,
                strikethrough=False):
        return _Char.__new__(cls, data, fg, bg, bold, italics, underscore,
                             reverse, strikethrough)


class Cursor(object):
    """Screen cursor.

    :param int x: horizontal cursor position.
    :param int y: vertical cursor position.
    :param pyte.screens.Char attrs: cursor attributes (see
        :meth:`~pyte.screens.Screen.selectel_graphic_rendition`
        for details).
    """
    def __init__(self, x, y, attrs=Char(" ")):
        self.x, self.y, self.attrs, self.hidden = x, y, attrs, False


class Screen(object):
    """
    A screen is an in-memory matrix of characters that represents the
    screen display of the terminal. It can be instantiated on it's own
    and given explicit commands, or it can be attached to a stream and
    will respond to events.

    .. attribute:: buffer

       A ``lines x columns`` :class:`~pyte.screens.Char` matrix.

    .. attribute:: cursor

       Reference to the :class:`~pyte.screens.Cursor` object, holding
       cursor position and attributes.

    .. attribute:: margins

       Top and bottom screen margins, defining the scrolling region;
       the actual values are top and bottom line.

    .. attribute:: charset

       Current charset number; can be either ``0`` or ``1`` for `G0`
       and `G1` respectively, note that `G0` is activated by default.

    .. note::

       According to ``ECMA-48`` standard, **lines and columnns are
       1-indexed**, so, for instance ``ESC [ 10;10 f`` really means
       -- move cursor to position (9, 9) in the display matrix.

    .. versionchanged:: 0.4.7
    .. warning::

       :data:`~pyte.modes.LNM` is reset by default, to match VT220
       specification.

    .. versionchanged:: 0.4.8
    .. warning::

       If `DECAWM` mode is set than a cursor will be wrapped to the
       **beginning* of the next line, which is the behaviour described
       in ``man console_codes``.

    .. seealso::

       `Standard ECMA-48, Section 6.1.1 \
       <http://www.ecma-international.org/publications
       /standards/Ecma-048.htm>`_
         For a description of the presentational component, implemented
         by ``Screen``.
    """
    #: A plain empty character with default foreground and background
    #: colors.
    default_char = Char(data=" ", fg="default", bg="default")

    #: An inifinite sequence of default characters, used for populating
    #: new lines and columns.
    default_line = repeat(default_char)

    def __init__(self, columns, lines):
        self.savepoints = []
        self.lines, self.columns = lines, columns
        self.buffer = []
        self.reset()

    def __repr__(self):
        return ("{0}({1}, {2})".format(self.__class__.__name__,
                                       self.columns, self.lines))

    def __before__(self, command):
        """Hook, called **before** a command is dispatched to the
        :class:`Screen` instance.

        :param str command: command name, for example ``"LINEFEED"``.
        """

    def __after__(self, command):
        """Hook, called **after** a command is dispatched to the
        :class:`Screen` instance.

        :param str command: command name, for example ``"LINEFEED"``.
        """

    @property
    def size(self):
        """Returns screen size -- ``(lines, columns)``"""
        return self.lines, self.columns

    @property
    def display(self):
        """Returns a :func:`list` of screen lines as unicode strings."""
        return ["".join(map(operator.attrgetter("data"), line))
                for line in self.buffer]

    def reset(self):
        """Resets the terminal to its initial state.

        * Scroll margins are reset to screen boundaries.
        * Cursor is moved to home location -- ``(0, 0)`` and its
          attributes are set to defaults (see :attr:`default_char`).
        * Screen is cleared -- each character is reset to
          :attr:`default_char`.
        * Tabstops are reset to "every eight columns".

        .. note::

           Neither VT220 nor VT102 manuals mentioned that terminal modes
           and tabstops should be reset as well, thanks to
           :manpage:`xterm` -- we now know that.
        """
        self.buffer[:] = (take(self.columns, self.default_line)
                          for _ in range(self.lines))
        self.mode = set([mo.DECAWM, mo.DECTCEM])
        self.margins = Margins(0, self.lines - 1)

        # According to VT220 manual and ``linux/drivers/tty/vt.c``
        # the default G0 charset is latin-1, but for reasons unknown
        # latin-1 breaks ascii-graphics; so G0 defaults to cp437.
        self.charset = 0
        self.g0_charset = cs.IBMPC_MAP
        self.g1_charset = cs.VT100_MAP

        # From ``man terminfo`` -- "... hardware tabs are initially
        # set every `n` spaces when the terminal is powered up. Since
        # we aim to support VT102 / VT220 and linux -- we use n = 8.
        self.tabstops = set(range(7, self.columns, 8))

        self.cursor = Cursor(0, 0)
        self.cursor_position()

    def resize(self, lines=None, columns=None):
        """Resize the screen to the given dimensions.

        If the requested screen size has more lines than the existing
        screen, lines will be added at the bottom. If the requested
        size has less lines than the existing screen lines will be
        clipped at the top of the screen. Similarly, if the existing
        screen has less columns than the requested screen, columns will
        be added at the right, and if it has more -- columns will be
        clipped at the right.

        .. note:: According to `xterm`, we should also reset origin
                  mode and screen margins, see ``xterm/screen.c:1761``.

        :param int lines: number of lines in the new screen.
        :param int columns: number of columns in the new screen.
        """
        lines = lines or self.lines
        columns = columns or self.columns

        # First resize the lines:
        diff = self.lines - lines

        # a) if the current display size is less than the requested
        #    size, add lines to the bottom.
        if diff < 0:
            self.buffer.extend(take(self.columns, self.default_line)
                               for _ in range(diff, 0))
        # b) if the current display size is greater than requested
        #    size, take lines off the top.
        elif diff > 0:
            self.buffer[:diff] = ()

        # Then resize the columns:
        diff = self.columns - columns

        # a) if the current display size is less than the requested
        #    size, expand each line to the new size.
        if diff < 0:
            for y in range(lines):
                self.buffer[y].extend(take(abs(diff), self.default_line))
        # b) if the current display size is greater than requested
        #    size, trim each line from the right to the new size.
        elif diff > 0:
            for line in self.buffer:
                del line[columns:]

        self.lines, self.columns = lines, columns
        self.margins = Margins(0, self.lines - 1)
        self.reset_mode(mo.DECOM)

    def set_margins(self, top=None, bottom=None):
        """Selects top and bottom margins for the scrolling region.

        Margins determine which screen lines move during scrolling
        (see :meth:`index` and :meth:`reverse_index`). Characters added
        outside the scrolling region do not cause the screen to scroll.

        :param int top: the smallest line number that is scrolled.
        :param int bottom: the biggest line number that is scrolled.
        """
        if top is None or bottom is None:
            return

        # Arguments are 1-based, while :attr:`margins` are zero based --
        # so we have to decrement them by one. We also make sure that
        # both of them is bounded by [0, lines - 1].
        top = max(0, min(top - 1, self.lines - 1))
        bottom = max(0, min(bottom - 1, self.lines - 1))

        # Even though VT102 and VT220 require DECSTBM to ignore regions
        # of width less than 2, some programs (like aptitude for example)
        # rely on it. Practicality beats purity.
        if bottom - top >= 1:
            self.margins = Margins(top, bottom)

            # The cursor moves to the home position when the top and
            # bottom margins of the scrolling region (DECSTBM) changes.
            self.cursor_position()

    def set_charset(self, code, mode):
        """Set active ``G0`` or ``G1`` charset.

        :param str code: character set code, should be a character
                         from ``"B0UK"`` -- otherwise ignored.
        :param str mode: if ``"("`` ``G0`` charset is set, if
                         ``")"`` -- we operate on ``G1``.

        .. warning:: User-defined charsets are currently not supported.
        """
        if code in cs.MAPS:
            setattr(self, {"(": "g0_charset", ")": "g1_charset"}[mode],
                    cs.MAPS[code])

    def set_mode(self, *modes, **kwargs):
        """Sets (enables) a given list of modes.

        :param list modes: modes to set, where each mode is a constant
                           from :mod:`pyte.modes`.
        """
        # Private mode codes are shifted, to be distingiushed from non
        # private ones.
        if kwargs.get("private"):
            modes = [mode << 5 for mode in modes]

        self.mode.update(modes)

        # When DECOLM mode is set, the screen is erased and the cursor
        # moves to the home position.
        if mo.DECCOLM in modes:
            self.resize(columns=132)
            self.erase_in_display(2)
            self.cursor_position()

        # According to `vttest`, DECOM should also home the cursor, see
        # vttest/main.c:303.
        if mo.DECOM in modes:
            self.cursor_position()

        # Mark all displayed characters as reverse.
        if mo.DECSCNM in modes:
            self.buffer[:] = ([char._replace(reverse=True) for char in line]
                       for line in self.buffer)
            self.select_graphic_rendition(g._SGR["+reverse"])

        # Make the cursor visible.
        if mo.DECTCEM in modes:
            self.cursor.hidden = False

    def reset_mode(self, *modes, **kwargs):
        """Resets (disables) a given list of modes.

        :param list modes: modes to reset -- hopefully, each mode is a
                           constant from :mod:`pyte.modes`.
        """
        # Private mode codes are shifted, to be distingiushed from non
        # private ones.
        if kwargs.get("private"):
            modes = [mode << 5 for mode in modes]

        self.mode.difference_update(modes)

        # Lines below follow the logic in :meth:`set_mode`.
        if mo.DECCOLM in modes:
            self.resize(columns=80)
            self.erase_in_display(2)
            self.cursor_position()

        if mo.DECOM in modes:
            self.cursor_position()

        if mo.DECSCNM in modes:
            self.buffer[:] = ([char._replace(reverse=False) for char in line]
                       for line in self.buffer)
            self.select_graphic_rendition(g._SGR["-reverse"])

        # Hide the cursor.
        if mo.DECTCEM in modes:
            self.cursor.hidden = True

    def shift_in(self):
        """Activates ``G0`` character set."""
        self.charset = 0

    def shift_out(self):
        """Activates ``G1`` character set."""
        self.charset = 1

    def draw(self, char):
        """Display a character at the current cursor position and advance
        the cursor if :data:`~pyte.modes.DECAWM` is set.

        :param str char: a character to display.
        """
        # Translating a given character.
        char = char.translate([self.g0_charset,
                               self.g1_charset][self.charset])

        # If this was the last column in a line and auto wrap mode is
        # enabled, move the cursor to the beginning of the next line,
        # otherwise replace characters already displayed with newly
        # entered.
        if self.cursor.x == self.columns:
            if mo.DECAWM in self.mode:
                self.carriage_return()
                self.linefeed()
            else:
                self.cursor.x -= 1

        # If Insert mode is set, new characters move old characters to
        # the right, otherwise terminal is in Replace mode and new
        # characters replace old characters at cursor position.
        if mo.IRM in self.mode:
            self.insert_characters(1)

        self.buffer[self.cursor.y][self.cursor.x] = self.cursor.attrs \
            ._replace(data=char)

        # .. note:: We can't use :meth:`cursor_forward()`, because that
        #           way, we'll never know when to linefeed.
        self.cursor.x += 1

    def carriage_return(self):
        """Move the cursor to the beginning of the current line."""
        self.cursor.x = 0

    def index(self):
        """Move the cursor down one line in the same column. If the
        cursor is at the last line, create a new line at the bottom.
        """
        top, bottom = self.margins

        if self.cursor.y == bottom:
            self.buffer.pop(top)
            self.buffer.insert(bottom, take(self.columns, self.default_line))
        else:
            self.cursor_down()

    def reverse_index(self):
        """Move the cursor up one line in the same column. If the cursor
        is at the first line, create a new line at the top.
        """
        top, bottom = self.margins

        if self.cursor.y == top:
            self.buffer.pop(bottom)
            self.buffer.insert(top, take(self.columns, self.default_line))
        else:
            self.cursor_up()

    def linefeed(self):
        """Performs an index and, if :data:`~pyte.modes.LNM` is set, a
        carriage return.
        """
        self.index()

        if mo.LNM in self.mode:
            self.carriage_return()

        self.ensure_bounds()

    def tab(self):
        """Move to the next tab space, or the end of the screen if there
        aren't anymore left.
        """
        for stop in sorted(self.tabstops):
            if self.cursor.x < stop:
                column = stop
                break
        else:
            column = self.columns - 1

        self.cursor.x = column

    def backspace(self):
        """Move cursor to the left one or keep it in it's position if
        it's at the beginning of the line already.
        """
        self.cursor_back()

    def save_cursor(self):
        """Push the current cursor position onto the stack."""
        self.savepoints.append(Savepoint(copy.copy(self.cursor),
                                         self.g0_charset,
                                         self.g1_charset,
                                         self.charset,
                                         mo.DECOM in self.mode,
                                         mo.DECAWM in self.mode))

    def restore_cursor(self):
        """Set the current cursor position to whatever cursor is on top
        of the stack.
        """
        if self.savepoints:
            savepoint = self.savepoints.pop()

            self.g0_charset = savepoint.g0_charset
            self.g1_charset = savepoint.g1_charset
            self.charset = savepoint.charset

            if savepoint.origin:
                self.set_mode(mo.DECOM)
            if savepoint.wrap:
                self.set_mode(mo.DECAWM)

            self.cursor = savepoint.cursor
            self.ensure_bounds(use_margins=True)
        else:
            # If nothing was saved, the cursor moves to home position;
            # origin mode is reset. :todo: DECAWM?
            self.reset_mode(mo.DECOM)
            self.cursor_position()

    def insert_lines(self, count=None):
        """Inserts the indicated # of lines at line with cursor. Lines
        displayed **at** and below the cursor move down. Lines moved
        past the bottom margin are lost.

        :param count: number of lines to delete.
        """
        count = count or 1
        top, bottom = self.margins

        # If cursor is outside scrolling margins it -- do nothin'.
        if top <= self.cursor.y <= bottom:
            #                           v +1, because range() is exclusive.
            for line in range(self.cursor.y,
                              min(bottom + 1, self.cursor.y + count)):
                self.buffer.pop(bottom)
                self.buffer.insert(line, take(self.columns, self.default_line))

            self.carriage_return()

    def delete_lines(self, count=None):
        """Deletes the indicated # of lines, starting at line with
        cursor. As lines are deleted, lines displayed below cursor
        move up. Lines added to bottom of screen have spaces with same
        character attributes as last line moved up.

        :param int count: number of lines to delete.
        """
        count = count or 1
        top, bottom = self.margins

        # If cursor is outside scrolling margins it -- do nothin'.
        if top <= self.cursor.y <= bottom:
            #                v -- +1 to include the bottom margin.
            for _ in range(min(bottom - self.cursor.y + 1, count)):
                self.buffer.pop(self.cursor.y)
                self.buffer.insert(bottom, list(
                    repeat(self.cursor.attrs, self.columns)))

            self.carriage_return()

    def insert_characters(self, count=None):
        """Inserts the indicated # of blank characters at the cursor
        position. The cursor does not move and remains at the beginning
        of the inserted blank characters. Data on the line is shifted
        forward.

        :param int count: number of characters to insert.
        """
        count = count or 1

        for _ in range(min(self.columns - self.cursor.y, count)):
            self.buffer[self.cursor.y].insert(self.cursor.x, self.cursor.attrs)
            self.buffer[self.cursor.y].pop()

    def delete_characters(self, count=None):
        """Deletes the indicated # of characters, starting with the
        character at cursor position. When a character is deleted, all
        characters to the right of cursor move left. Character attributes
        move with the characters.

        :param int count: number of characters to delete.
        """
        count = count or 1

        for _ in range(min(self.columns - self.cursor.x, count)):
            self.buffer[self.cursor.y].pop(self.cursor.x)
            self.buffer[self.cursor.y].append(self.cursor.attrs)

    def erase_characters(self, count=None):
        """Erases the indicated # of characters, starting with the
        character at cursor position. Character attributes are set
        cursor attributes. The cursor remains in the same position.

        :param int count: number of characters to erase.

        .. warning::

           Even though *ALL* of the VTXXX manuals state that character
           attributes **should be reset to defaults**, ``libvte``,
           ``xterm`` and ``ROTE`` completely ignore this. Same applies
           too all ``erase_*()`` and ``delete_*()`` methods.
        """
        count = count or 1

        for column in range(self.cursor.x,
                            min(self.cursor.x + count, self.columns)):
            self.buffer[self.cursor.y][column] = self.cursor.attrs

    def erase_in_line(self, type_of=0, private=False):
        """Erases a line in a specific way.

        :param int type_of: defines the way the line should be erased in:

            * ``0`` -- Erases from cursor to end of line, including cursor
              position.
            * ``1`` -- Erases from beginning of line to cursor,
              including cursor position.
            * ``2`` -- Erases complete line.
        :param bool private: when ``True`` character attributes aren left
                             unchanged **not implemented**.
        """
        interval = (
            # a) erase from the cursor to the end of line, including
            # the cursor,
            range(self.cursor.x, self.columns),
            # b) erase from the beginning of the line to the cursor,
            # including it,
            range(0, self.cursor.x + 1),
            # c) erase the entire line.
            range(0, self.columns)
        )[type_of]

        for column in interval:
            self.buffer[self.cursor.y][column] = self.cursor.attrs

    def erase_in_display(self, type_of=0, private=False):
        """Erases display in a specific way.

        :param int type_of: defines the way the line should be erased in:

            * ``0`` -- Erases from cursor to end of screen, including
              cursor position.
            * ``1`` -- Erases from beginning of screen to cursor,
              including cursor position.
            * ``2`` -- Erases complete display. All lines are erased
              and changed to single-width. Cursor does not move.
        :param bool private: when ``True`` character attributes aren left
                             unchanged **not implemented**.
        """
        interval = (
            # a) erase from cursor to the end of the display, including
            # the cursor,
            range(self.cursor.y + 1, self.lines),
            # b) erase from the beginning of the display to the cursor,
            # including it,
            range(0, self.cursor.y),
            # c) erase the whole display.
            range(0, self.lines)
        )[type_of]

        for line in interval:
            self.buffer[line][:] = \
                (self.cursor.attrs for _ in range(self.columns))

        # In case of 0 or 1 we have to erase the line with the cursor.
        if type_of in [0, 1]:
            self.erase_in_line(type_of)

    def set_tab_stop(self):
        """Sest a horizontal tab stop at cursor position."""
        self.tabstops.add(self.cursor.x)

    def clear_tab_stop(self, type_of=None):
        """Clears a horizontal tab stop in a specific way, depending
        on the ``type_of`` value:

        * ``0`` or nothing -- Clears a horizontal tab stop at cursor
          position.
        * ``3`` -- Clears all horizontal tab stops.
        """
        if not type_of:
            # Clears a horizontal tab stop at cursor position, if it's
            # present, or silently fails if otherwise.
            self.tabstops.discard(self.cursor.x)
        elif type_of == 3:
            self.tabstops = set()  # Clears all horizontal tab stops.

    def ensure_bounds(self, use_margins=None):
        """Ensure that current cursor position is within screen bounds.

        :param bool use_margins: when ``True`` or when
                                 :data:`~pyte.modes.DECOM` is set,
                                 cursor is bounded by top and and bottom
                                 margins, instead of ``[0; lines - 1]``.
        """
        if use_margins or mo.DECOM in self.mode:
            top, bottom = self.margins
        else:
            top, bottom = 0, self.lines - 1

        self.cursor.x = min(max(0, self.cursor.x), self.columns - 1)
        self.cursor.y = min(max(top, self.cursor.y), bottom)

    def cursor_up(self, count=None):
        """Moves cursor up the indicated # of lines in same column.
        Cursor stops at top margin.

        :param int count: number of lines to skip.
        """
        self.cursor.y -= count or 1
        self.ensure_bounds(use_margins=True)

    def cursor_up1(self, count=None):
        """Moves cursor up the indicated # of lines to column 1. Cursor
        stops at bottom margin.

        :param int count: number of lines to skip.
        """
        self.cursor_up(count)
        self.carriage_return()

    def cursor_down(self, count=None):
        """Moves cursor down the indicated # of lines in same column.
        Cursor stops at bottom margin.

        :param int count: number of lines to skip.
        """
        self.cursor.y += count or 1
        self.ensure_bounds(use_margins=True)

    def cursor_down1(self, count=None):
        """Moves cursor down the indicated # of lines to column 1.
        Cursor stops at bottom margin.

        :param int count: number of lines to skip.
        """
        self.cursor_down(count)
        self.carriage_return()

    def cursor_back(self, count=None):
        """Moves cursor left the indicated # of columns. Cursor stops
        at left margin.

        :param int count: number of columns to skip.
        """
        self.cursor.x -= count or 1
        self.ensure_bounds()

    def cursor_forward(self, count=None):
        """Moves cursor right the indicated # of columns. Cursor stops
        at right margin.

        :param int count: number of columns to skip.
        """
        self.cursor.x += count or 1
        self.ensure_bounds()

    def cursor_position(self, line=None, column=None):
        """Set the cursor to a specific `line` and `column`.

        Cursor is allowed to move out of the scrolling region only when
        :data:`~pyte.modes.DECOM` is reset, otherwise -- the position
        doesn't change.

        :param int line: line number to move the cursor to.
        :param int column: column number to move the cursor to.
        """
        column = (column or 1) - 1
        line = (line or 1) - 1

        # If origin mode (DECOM) is set, line number are relative to
        # the top scrolling margin.
        if mo.DECOM in self.mode:
            line += self.margins.top

            # Cursor is not allowed to move out of the scrolling region.
            if not self.margins.top <= line <= self.margins.bottom:
                return

        self.cursor.x, self.cursor.y = column, line
        self.ensure_bounds()

    def cursor_to_column(self, column=None):
        """Moves cursor to a specific column in the current line.

        :param int column: column number to move the cursor to.
        """
        self.cursor.x = (column or 1) - 1
        self.ensure_bounds()

    def cursor_to_line(self, line=None):
        """Moves cursor to a specific line in the current column.

        :param int line: line number to move the cursor to.
        """
        self.cursor.y = (line or 1) - 1

        # If origin mode (DECOM) is set, line number are relative to
        # the top scrolling margin.
        if mo.DECOM in self.mode:
            self.cursor.y += self.margins.top

            # FIXME: should we also restrict the cursor to the scrolling
            # region?

        self.ensure_bounds()

    def bell(self, *args):
        """Bell stub -- the actual implementation should probably be
        provided by the end-user.
        """

    def alignment_display(self):
        """Fills screen with uppercase E's for screen focus and alignment."""
        for line in self.buffer:
            for column, char in enumerate(line):
                line[column] = char._replace(data="E")

    def select_graphic_rendition(self, *attrs):
        """Set display attributes.

        :param list attrs: a list of display attributes to set.
        """
        replace = {}

        for attr in attrs or [0]:
            if attr in g.FG:
                replace["fg"] = g.FG[attr]
            elif attr in g.BG:
                replace["bg"] = g.BG[attr]
            elif attr in g.TEXT:
                attr = g.TEXT[attr]
                replace[attr[1:]] = attr.startswith("+")
            elif not attr:
                replace = self.default_char._asdict()

        self.cursor.attrs = self.cursor.attrs._replace(**replace)


class DiffScreen(Screen):
    """A screen subclass, which maintains a set of dirty lines in its
    :attr:`dirty` attribute. The end user is responsible for emptying
    a set, when a diff is applied.

    .. attribute:: dirty

       A set of line numbers, which should be re-drawn.

       >>> screen = DiffScreen(80, 24)
       >>> screen.dirty.clear()
       >>> screen.draw(u"!")
       >>> screen.dirty
       set([0])
    """
    def __init__(self, *args):
        self.dirty = set()
        super(DiffScreen, self).__init__(*args)

    def set_mode(self, *modes, **kwargs):
        if mo.DECSCNM >> 5 in modes and kwargs.get("private"):
            self.dirty.update(range(self.lines))
        super(DiffScreen, self).set_mode(*modes, **kwargs)

    def reset_mode(self, *modes, **kwargs):
        if mo.DECSCNM >> 5 in modes and kwargs.get("private"):
            self.dirty.update(range(self.lines))
        super(DiffScreen, self).reset_mode(*modes, **kwargs)

    def reset(self):
        self.dirty.update(range(self.lines))
        super(DiffScreen, self).reset()

    def resize(self, *args, **kwargs):
        self.dirty.update(range(self.lines))
        super(DiffScreen, self).resize(*args, **kwargs)

    def draw(self, *args):
        self.dirty.add(self.cursor.y)
        super(DiffScreen, self).draw(*args)

    def index(self):
        if self.cursor.y == self.margins.bottom:
            self.dirty.update(range(self.lines))

        super(DiffScreen, self).index()

    def reverse_index(self):
        if self.cursor.y == self.margins.top:
            self.dirty.update(range(self.lines))

        super(DiffScreen, self).reverse_index()

    def insert_lines(self, *args):
        self.dirty.update(range(self.cursor.y, self.lines))
        super(DiffScreen, self).insert_lines(*args)

    def delete_lines(self, *args):
        self.dirty.update(range(self.cursor.y, self.lines))
        super(DiffScreen, self).delete_lines(*args)

    def insert_characters(self, *args):
        self.dirty.add(self.cursor.y)
        super(DiffScreen, self).insert_characters(*args)

    def delete_characters(self, *args):
        self.dirty.add(self.cursor.y)
        super(DiffScreen, self).delete_characters(*args)

    def erase_characters(self, *args):
        self.dirty.add(self.cursor.y)
        super(DiffScreen, self).erase_characters(*args)

    def erase_in_line(self, *args):
        self.dirty.add(self.cursor.y)
        super(DiffScreen, self).erase_in_line(*args)

    def erase_in_display(self, type_of=0):
        self.dirty.update((
            range(self.cursor.y + 1, self.lines),
            range(0, self.cursor.y),
            range(0, self.lines)
        )[type_of])
        super(DiffScreen, self).erase_in_display(type_of)

    def alignment_display(self):
        self.dirty.update(range(self.lines))
        super(DiffScreen, self).alignment_display()


History = namedtuple("History", "top bottom ratio size position")


class HistoryScreen(DiffScreen):
    """A screen subclass, which keeps track of screen history and allows
    pagination. This is not linux-specific, but still useful; see  page
    462 of VT520 User's Manual.

    :param int history: total number of history lines to keep; is split
                        between top and bottom queues.
    :param int ratio: defines how much lines to scroll on :meth:`next_page`
                      and :meth:`prev_page` calls.

    .. attribute:: history

       A pair of history queues for top and bottom margins accordingly;
       here's the overall screen structure::

            [ 1: .......]
            [ 2: .......]  <- top history
            [ 3: .......]
            ------------
            [ 4: .......]  s
            [ 5: .......]  c
            [ 6: .......]  r
            [ 7: .......]  e
            [ 8: .......]  e
            [ 9: .......]  n
            ------------
            [10: .......]
            [11: .......]  <- bottom history
            [12: .......]

    .. note::

       Don't forget to update :class:`~pyte.streams.Stream` class with
       appropriate escape sequences -- you can use any, since pagination
       protocol is not standardized, for example::

           Stream.escape["N"] = "next_page"
           Stream.escape["P"] = "prev_page"
    """

    def __init__(self, columns, lines, history=100, ratio=.5):
        self.history = History(deque(maxlen=history // 2),
                               deque(maxlen=history),
                               float(ratio),
                               history,
                               history)

        super(HistoryScreen, self).__init__(columns, lines)

    def __before__(self, command):
        """Ensures a screen is at the bottom of the history buffer."""
        if command not in ["prev_page", "next_page"]:
            while self.history.position < self.history.size:
                self.next_page()

        super(HistoryScreen, self).__before__(command)

    def __after__(self, command):
        """Ensures all lines on a screen have proper width (:attr:`columns`).

        Extra characters are truncated, missing characters are filled
        with whitespace.
        """
        if command in ["prev_page", "next_page"]:
            for idx, line in enumerate(self.buffer):
                if len(line) > self.columns:
                    self.buffer[idx] = line[:self.columns]
                elif len(line) < self.columns:
                    self.buffer[idx] = line + take(self.columns - len(line),
                                                   self.default_line)

        # If we're at the bottom of the history buffer and `DECTCEM`
        # mode is set -- show the cursor.
        self.cursor.hidden = not (
            abs(self.history.position - self.history.size) < self.lines and
            mo.DECTCEM in self.mode
        )

        super(HistoryScreen, self).__after__(command)

    def reset(self):
        """Overloaded to reset screen history state: history position
        is reset to bottom of both queues;  queues themselves are
        emptied.
        """
        super(HistoryScreen, self).reset()

        self.history.top.clear()
        self.history.bottom.clear()
        self.history = self.history._replace(position=self.history.size)

    def index(self):
        """Overloaded to update top history with the removed lines."""
        top, bottom = self.margins

        if self.cursor.y == bottom:
            self.history.top.append(self.buffer[top])

        super(HistoryScreen, self).index()

    def reverse_index(self):
        """Overloaded to update bottom history with the removed lines."""
        top, bottom = self.margins

        if self.cursor.y == top:
            self.history.bottom.append(self.buffer[bottom])

        super(HistoryScreen, self).reverse_index()

    def prev_page(self):
        """Moves the screen page up through the history buffer. Page
        size is defined by ``history.ratio``, so for instance
        ``ratio = .5`` means that half the screen is restored from
        history on page switch.
        """
        if self.history.position > self.lines and self.history.top:
            mid = min(len(self.history.top),
                      int(math.ceil(self.lines * self.history.ratio)))

            self.history.bottom.extendleft(reversed(self.buffer[-mid:]))
            self.history = self.history \
                ._replace(position=self.history.position - self.lines)

            self.buffer[:] = list(reversed([
                self.history.top.pop() for _ in range(mid)
            ])) + self.buffer[:-mid]

            self.dirty = set(range(self.lines))

    def next_page(self):
        """Moves the screen page down through the history buffer."""
        if self.history.position < self.history.size and self.history.bottom:
            mid = min(len(self.history.bottom),
                      int(math.ceil(self.lines * self.history.ratio)))

            self.history.top.extend(self.buffer[:mid])
            self.history = self.history \
                ._replace(position=self.history.position + self.lines)

            self.buffer[:] = self.buffer[mid:] + [
                self.history.bottom.popleft() for _ in range(mid)
            ]

            self.dirty = set(range(self.lines))

########NEW FILE########
__FILENAME__ = streams
# -*- coding: utf-8 -*-
"""
    pyte.streams
    ~~~~~~~~~~~~

    This module provides three stream implementations with different
    features; for starters, here's a quick example of how streams are
    typically used:

    >>> import pyte
    >>>
    >>> class Dummy(object):
    ...     def __init__(self):
    ...         self.y = 0
    ...
    ...     def cursor_up(self, count=None):
    ...         self.y += count or 1
    ...
    >>> dummy = Dummy()
    >>> stream = pyte.Stream()
    >>> stream.attach(dummy)
    >>> stream.feed(u"\u001B[5A")  # Move the cursor up 5 rows.
    >>> dummy.y
    5

    :copyright: (c) 2011-2013 by Selectel, see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import absolute_import, unicode_literals

import os
import codecs
import sys

from . import control as ctrl, escape as esc


if sys.version_info[0] == 2:
    str = unicode


class Stream(object):
    """A stream is a state machine that parses a stream of characters
    and dispatches events based on what it sees.

    .. note::

       Stream only accepts  strings as input, but if, for some reason,
       you need to feed it with bytes, consider using
       :class:`~pyte.streams.ByteStream` instead.

    .. seealso::

        `man console_codes <http://linux.die.net/man/4/console_codes>`_
            For details on console codes listed bellow in :attr:`basic`,
            :attr:`escape`, :attr:`csi` and :attr:`sharp`.
    """

    #: Control sequences, which don't require any arguments.
    basic = {
        ctrl.BEL: "bell",
        ctrl.BS: "backspace",
        ctrl.HT: "tab",
        ctrl.LF: "linefeed",
        ctrl.VT: "linefeed",
        ctrl.FF: "linefeed",
        ctrl.CR: "carriage_return",
        ctrl.SO: "shift_out",
        ctrl.SI: "shift_in",
    }

    #: non-CSI escape sequences.
    escape = {
        esc.RIS: "reset",
        esc.IND: "index",
        esc.NEL: "linefeed",
        esc.RI: "reverse_index",
        esc.HTS: "set_tab_stop",
        esc.DECSC: "save_cursor",
        esc.DECRC: "restore_cursor",
    }

    #: "sharp" escape sequences -- ``ESC # <N>``.
    sharp = {
        esc.DECALN: "alignment_display",
    }

    #: CSI escape sequences -- ``CSI P1;P2;...;Pn <fn>``.
    csi = {
        esc.ICH: "insert_characters",
        esc.CUU: "cursor_up",
        esc.CUD: "cursor_down",
        esc.CUF: "cursor_forward",
        esc.CUB: "cursor_back",
        esc.CNL: "cursor_down1",
        esc.CPL: "cursor_up1",
        esc.CHA: "cursor_to_column",
        esc.CUP: "cursor_position",
        esc.ED: "erase_in_display",
        esc.EL: "erase_in_line",
        esc.IL: "insert_lines",
        esc.DL: "delete_lines",
        esc.DCH: "delete_characters",
        esc.ECH: "erase_characters",
        esc.HPR: "cursor_forward",
        esc.VPA: "cursor_to_line",
        esc.VPR: "cursor_down",
        esc.HVP: "cursor_position",
        esc.TBC: "clear_tab_stop",
        esc.SM: "set_mode",
        esc.RM: "reset_mode",
        esc.SGR: "select_graphic_rendition",
        esc.DECSTBM: "set_margins",
        esc.HPA: "cursor_to_column",
    }

    def __init__(self):
        self.handlers = {
            "stream": self._stream,
            "escape": self._escape,
            "arguments": self._arguments,
            "sharp": self._sharp,
            "charset": self._charset
        }

        self.listeners = []
        self.reset()

    def reset(self):
        """Reset state to ``"stream"`` and empty parameter attributes."""
        self.state = "stream"
        self.flags = {}
        self.params = []
        self.current = ""

    def consume(self, char):
        """Consume a single string character and advance the state as
        necessary.

        :param str char: a character to consume.
        """
        if not isinstance(char, str):
            raise TypeError("%s requires str input" % self.__class__.__name__)

        try:
            self.handlers.get(self.state)(char)
        except TypeError:
            pass
        except KeyError:
            if __debug__:
                self.flags["state"] = self.state
                self.flags["unhandled"] = char
                self.dispatch("debug", *self.params)
                self.reset()
            else:
                raise

    def feed(self, chars):
        """Consume a string and advance the state as necessary.

        :param str chars: a string to feed from.
        """
        if not isinstance(chars, str):
            raise TypeError("%s requires str input" % self.__class__.__name__)

        for char in chars: self.consume(char)

    def attach(self, screen, only=()):
        """Adds a given screen to the listeners queue.

        :param pyte.screens.Screen screen: a screen to attach to.
        :param list only: a list of events you want to dispatch to a
                          given screen (empty by default, which means
                          -- dispatch all events).
        """
        self.listeners.append((screen, set(only)))

    def detach(self, screen):
        """Removes a given screen from the listeners queue and failes
        silently if it's not attached.

        :param pyte.screens.Screen screen: a screen to detach.
        """
        for idx, (listener, _) in enumerate(self.listeners):
            if screen is listener:
                self.listeners.pop(idx)

    def dispatch(self, event, *args, **kwargs):
        """Dispatch an event.

        Event handlers are looked up implicitly in the listeners'
        ``__dict__``, so, if a listener only wants to handle ``DRAW``
        events it should define a ``draw()`` method or pass
        ``only=["draw"]`` argument to :meth:`attach`.

        .. warning::

           If any of the attached listeners throws an exception, the
           subsequent callbacks are be aborted.

        :param str event: event to dispatch.
        :param list args: arguments to pass to event handlers.
        """
        for listener, only in self.listeners:
            if only and event not in only:
                continue

            try:
                handler = getattr(listener, event)
            except AttributeError:
                continue

            if hasattr(listener, "__before__"):
                listener.__before__(event)

            handler(*args, **self.flags)

            if hasattr(listener, "__after__"):
                listener.__after__(event)
        else:
            if kwargs.get("reset", True): self.reset()

    # State transformers.
    # ...................

    def _stream(self, char):
        """Process a character when in the default ``"stream"`` state."""
        if char in self.basic:
            self.dispatch(self.basic[char])
        elif char == ctrl.ESC:
            self.state = "escape"
        elif char == ctrl.CSI:
            self.state = "arguments"
        elif char not in [ctrl.NUL, ctrl.DEL]:
            self.dispatch("draw", char)

    def _escape(self, char):
        """Handle characters seen when in an escape sequence.

        Most non-VT52 commands start with a left-bracket after the
        escape and then a stream of parameters and a command; with
        a single notable exception -- :data:`escape.DECOM` sequence,
        which starts with a sharp.
        """
        if char == "#":
            self.state = "sharp"
        elif char == "[":
            self.state = "arguments"
        elif char in "()":
            self.state = "charset"
            self.flags["mode"] = char
        else:
            self.dispatch(self.escape[char])

    def _sharp(self, char):
        """Parse arguments of a `"#"` seqence."""
        self.dispatch(self.sharp[char])

    def _charset(self, char):
        """Parse ``G0`` or ``G1`` charset code."""
        self.dispatch("set_charset", char)

    def _arguments(self, char):
        """Parse arguments of an escape sequence.

        All parameters are unsigned, positive decimal integers, with
        the most significant digit sent first. Any parameter greater
        than 9999 is set to 9999. If you do not specify a value, a 0
        value is assumed.

        .. seealso::

           `VT102 User Guide <http://vt100.net/docs/vt102-ug/>`_
               For details on the formatting of escape arguments.

           `VT220 Programmer Reference <http://http://vt100.net/docs/vt220-rm/>`_
               For details on the characters valid for use as arguments.
        """
        if char == "?":
            self.flags["private"] = True
        elif char in [ctrl.BEL, ctrl.BS, ctrl.HT, ctrl.LF, ctrl.VT,
                      ctrl.FF, ctrl.CR]:
            # Not sure why, but those seem to be allowed between CSI
            # sequence arguments.
            self.dispatch(self.basic[char], reset=False)
        elif char == ctrl.SP:
            pass
        elif char in [ctrl.CAN, ctrl.SUB]:
            # If CAN or SUB is received during a sequence, the current
            # sequence is aborted; terminal displays the substitute
            # character, followed by characters in the sequence received
            # after CAN or SUB.
            self.dispatch("draw", char)
            self.state = "stream"
        elif char.isdigit():
            self.current += char
        else:
            self.params.append(min(int(self.current or 0), 9999))

            if char == ";":
                self.current = ""
            else:
                self.dispatch(self.csi[char], *self.params)


class ByteStream(Stream):
    """A stream, which takes bytes (instead of strings) as input
    and tries to decode them using a given list of possible encodings.
    It uses :class:`codecs.IncrementalDecoder` internally, so broken
    bytes is not an issue.

    By default, the following decoding strategy is used:

    * First, try strict ``"utf-8"``, proceed if recieved and
      :exc:`UnicodeDecodeError` ...
    * Try strict ``"cp437"``, failed? move on ...
    * Use ``"utf-8"`` with invalid bytes replaced -- this one will
      allways succeed.

    >>> stream = ByteStream()
    >>> stream.feed(b"foo".decode("utf-8"))
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "pyte/streams.py", line 323, in feed
        "%s requires input in bytes" % self.__class__.__name__)
    TypeError: ByteStream requires input in bytes
    >>> stream.feed(b"foo")

    :param list encodings: a list of ``(encoding, errors)`` pairs,
                           where the first element is encoding name,
                           ex: ``"utf-8"`` and second defines how
                           decoding errors should be handeld; see
                           :meth:`str.decode` for possible values.
    """

    def __init__(self, encodings=None):
        encodings = encodings or [
            ("utf-8", "strict"),
            ("cp437", "strict"),
            ("utf-8", "replace")
        ]

        self.buffer = b"", 0
        self.decoders = [codecs.getincrementaldecoder(encoding)(errors)
                         for encoding, errors in encodings]

        super(ByteStream, self).__init__()

    def feed(self, chars):
        if not isinstance(chars, bytes):
            raise TypeError(
                "%s requires input in bytes" % self.__class__.__name__)

        for decoder in self.decoders:
            decoder.setstate(self.buffer)

            try:
                chars = decoder.decode(chars)
            except UnicodeDecodeError:
                continue

            self.buffer = decoder.getstate()
            return super(ByteStream, self).feed(chars)
        else:
            raise


class DebugStream(ByteStream):
    """Stream, which dumps a subset of the dispatched events to a given
    file-like object (:data:`sys.stdout` by default).

    >>> stream = DebugStream()
    >>> stream.feed("\x1b[1;24r\x1b[4l\x1b[24;1H\x1b[0;10m")
    SET_MARGINS 1; 24
    RESET_MODE 4
    CURSOR_POSITION 24; 1
    SELECT_GRAPHIC_RENDITION 0; 10

    :param file to: a file-like object to write debug information to.
    :param list only: a list of events you want to debug (empty by
                      default, which means -- debug all events).
    """

    def __init__(self, to=sys.stdout, only=(), *args, **kwargs):
        super(DebugStream, self).__init__(*args, **kwargs)

        def safe_str(chunk):
            if isinstance(chunk, bytes):
                chunk = chunk.decode("utf-8")
            elif not isinstance(chunk, str):
                chunk = str(chunk)

            return chunk

        class Bugger(object):
            __before__ = __after__ = lambda *args: None

            def __getattr__(self, event):
                def inner(*args, **flags):
                    to.write(event.upper() + " ")
                    to.write("; ".join(map(safe_str, args)))
                    to.write(" ")
                    to.write(", ".join("{0}: {1}".format(name, safe_str(arg))
                                       for name, arg in flags.items()))
                    to.write(os.linesep)
                return inner

        self.attach(Bugger(), only=only)

########NEW FILE########
__FILENAME__ = terminal
from gevent.select import select
import fcntl
import gevent
import logging
import os
import pty
import subprocess

import pyte


class Terminal (object):
    def __init__(self, command=None, autoclose=False, **kwargs):
        self.protocol = None
        self.width = 160
        self.height = 35
        self.autoclose = autoclose

        env = {}
        env.update(os.environ)
        env['TERM'] = 'linux'
        env['COLUMNS'] = str(self.width)
        env['LINES'] = str(self.height)
        env['LC_ALL'] = 'en_US.UTF8'

        shell = os.environ.get('SHELL', None)
        if not shell:
            for sh in ['zsh', 'bash', 'sh']:
                try:
                    shell = subprocess.check_output(['which', sh])
                    break
                except:
                    pass
        command = ['sh', '-c', command or shell]

        logging.info('Terminal: %s' % command)

        pid, master = pty.fork()
        if pid == 0:
            os.execvpe('sh', command, env)

        self.screen = pyte.DiffScreen(self.width, self.height)
        self.protocol = PTYProtocol(pid, master, self.screen, **kwargs)

    def restart(self):
        if self.protocol is not None:
            self.protocol.kill()
        self.start()

    def dead(self):
        return self.protocol is None or self.protocol.dead

    def write(self, data):
        self.protocol.write(data)

    def kill(self):
        self.protocol.kill()


class PTYProtocol():
    def __init__(self, pid, master, term, callback=None):
        self.pid = pid
        self.master = master
        self.dead = False
        self.callback = callback

        fd = self.master
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        self.mstream = os.fdopen(self.master, 'r+')
        gevent.sleep(0.5)
        self.term = term
        self.stream = pyte.Stream()
        self.stream.attach(self.term)
        self.data = ''

        self.last_cursor_position = None

    def read(self, timeout=1):
        select([self.master], [], [], timeout=timeout)
        
        try:
            d = self.mstream.read()
        except IOError:
            d = ''

        try:
            self.data += d
            if len(self.data) > 0:
                u = unicode(str(self.data))
                self.stream.feed(u)
                self.data = ''
                return None
        except UnicodeDecodeError:
            return None

        self._check()

    def _check(self):
        try:
            pid, status = os.waitpid(self.pid, os.WNOHANG)
        except OSError:
            self.on_died(code=-1)
            return
        if pid:
            self.on_died(code=status)

    def on_died(self, code=0):
        if self.dead:
            return
        self.dead = True
        if code:
            self.stream.feed('\n\n * ' + unicode(_('Process has exited with status %i') % code))
        else:
            self.stream.feed('\n\n * ' + unicode(_('Process has exited successfully')))
        if self.callback:
            try:
                self.callback(exitcode=code)
            except TypeError:
                self.callback()

    def history(self):
        return self.format(full=True)

    def has_updates(self):
        if self.last_cursor_position != (self.term.cursor.x, self.term.cursor.y):
            return True
        return len(self.term.dirty) > 0

    def format(self, full=False):
        def compress(line):
            return [[tok or 0 for tok in ch] for ch in line]

        l = {}
        self.term.dirty.add(self.term.cursor.y)
        for k in self.term.dirty:
            l[k] = compress(self.term.buffer[k])
        self.term.dirty.clear()

        if full:
            l = [compress(x) for x in self.term.buffer]

        r = {
            'lines': l,
            'cx': self.term.cursor.x,
            'cy': self.term.cursor.y,
            'cursor': not self.term.cursor.hidden,
        }

        self.last_cursor_position = (self.term.cursor.x, self.term.cursor.y)
        return r

    def write(self, data):
        self.mstream.write(data)
        self.mstream.flush()

    def kill(self):
        os.kill(self.pid, 9)

########NEW FILE########
__FILENAME__ = main
from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder


class Person (object):
    def __init__(self, name, phone):
        self.name = name
        self.phone = phone

    def __repr__(self):
        return '{%s: %s}' % (self.name, self.phone)


@plugin
class SimpleDemo (SectionPlugin):
    def init(self):
        self.title = 'Binder'
        self.icon = 'question'
        self.category = 'Demo'

        self.append(self.ui.inflate('test:binder-main'))

        self.data = [
            Person('Alice', '123'),
            Person('Bob', '234'),
        ]

        self.dict = {
            'a': 1,
            'b': 2,
        }

        self.find('data').text = repr(self.data)

        self.binder = Binder(self, self.find('bindroot'))

    @on('populate', 'click')
    def on_populate(self):
        self.binder.populate()

    @on('unpopulate', 'click')
    def on_unpopulate(self):
        self.binder.unpopulate()

    @on('update', 'click')
    def on_update(self):
        self.binder.update()
        self.find('data').text = repr(self.data)
########NEW FILE########
__FILENAME__ = main
from ajenti.api import *
from ajenti.api.http import *
from ajenti.plugins.configurator.api import ClassConfigEditor
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on


@plugin
class SimpleConfigEditor (ClassConfigEditor):
    title = 'Simple demo config'
    icon = 'question'

    def init(self):
        self.append(self.ui.inflate('test:classconfig-simple-editor'))


@plugin
class SimpleClassconfigSection (SectionPlugin):
    default_classconfig = {'option1': 'qwerty', 'option2': 1}
    classconfig_editor = SimpleConfigEditor

    def init(self):
        self.title = 'Classconfig (simple)'
        self.icon = 'question'
        self.category = 'Demo'
        self.append(self.ui.inflate('test:classconfig-main'))

    def on_page_load(self):
        self.find('value').text = repr(self.classconfig)

    @on('config', 'click')
    def on_config_btn(self):
        self.context.launch('configure-plugin', plugin=self)

########NEW FILE########
__FILENAME__ = main
from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on


@plugin
class EventsDemo (SectionPlugin):
    def init(self):
        self.title = 'Event handlers'
        self.icon = 'question'
        self.category = 'Demo'

        self.append(self.ui.inflate('test:events-main'))

        def on_click(*args):
            self.context.notify('info', 'Directly attached event fired with arguments %s!' % repr(args))

        self.find('btn').on('click', on_click, 123, 456)
            

    @on('btn', 'click')
    def on_button_click(self):
        self.context.notify('info', 'Decorator-attached event fired!')

########NEW FILE########
__FILENAME__ = http
from ajenti.api import plugin, BasePlugin
from ajenti.api.http import HttpPlugin, url


@plugin
class HttpDemo (BasePlugin, HttpPlugin):
    @url('/ajenti:demo/notify')
    def get_page(self, context):
        if context.session.identity is None:
            context.respond_redirect('/')
        self.context.notify('info', context.query.getvalue('text', ''))
        context.respond_ok()
        return ''

    @url('/ajenti:demo/respond/(?P<what>.+)')
    def get_response(self, context, what=None):
        if what == 'ok':
            context.respond_ok()
            return 'Hello!'
        if what == 'redirect':
            return context.respond_redirect('/')
        if what == 'server_error':
            return context.respond_server_error()
        if what == 'forbidden':
            return context.respond_forbidden()
        if what == 'not_found':
            return context.respond_not_found()
        if what == 'file':
            return context.file('/etc/issue')
        if what == 'error':
            raise Exception('error!')
########NEW FILE########
__FILENAME__ = main
from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder


class Phone (object):
    def __init__(self, number):
        self.number = number


class Person (object):
    def __init__(self, name, phones):
        self.name = name
        self.phones = phones


class AddressBook (object):
    def __init__(self, persons):
        self.persons = persons


@plugin
class Test (SectionPlugin):
    def init(self):
        self.title = 'Test'
        self.icon = 'question'
        self.category = 'Demo'

        self.append(self.ui.inflate('test:main'))

        alice = Person('Alice', [Phone('123')])
        bob = Person('Bob', [Phone('234'), Phone('345')])
        book = AddressBook([alice, bob])

        self.find('persons-collection').new_item = lambda c: Person('New person', [])
        self.find('phones-collection').new_item = lambda c: Phone('123')

        self.binder = Binder(None, self.find('addressbook'))
        self.binder.setup(book).populate()

########NEW FILE########
__FILENAME__ = main
from ajenti.api import plugin
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on


@plugin
class NotificationsDemo (SectionPlugin):
    def init(self):
        self.title = 'Notifications'
        self.icon = 'question'
        self.category = 'Demo'

        self.append(self.ui.inflate('test:notifications-main'))

    @on('show', 'click')
    def on_show(self):
        self.context.notify(self.find('style').value, self.find('text').value)

########NEW FILE########
__FILENAME__ = main
from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin


@plugin
class SimpleDemo (SectionPlugin):
    def init(self):
        self.title = 'Simple'
        self.icon = 'question'
        self.category = 'Demo'

        self.append(self.ui.inflate('test:simple-main'))

########NEW FILE########
__FILENAME__ = main
import os
import subprocess

from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder

from reconfigure.configs import PasswdConfig, GroupConfig


@plugin
class Users (SectionPlugin):
    def init(self):
        self.title = _('Users')
        self.icon = 'group'
        self.category = _('System')
        self.append(self.ui.inflate('users:main'))

        def _filterOnlyUsers(x):
            u = int(x.uid)
            return u >= 500

        def _filterOnlySystemUsers(x):
            u = int(x.uid)
            return u < 500

        def _sorter(x):
            g = int(x.gid)
            if g >= 500:
                return g - 10000
            return g

        self.find('users').filter = _filterOnlyUsers
        self.find('system-users').filter = _filterOnlySystemUsers
        self.find('groups').sorting = _sorter

        self.config = PasswdConfig(path='/etc/passwd')
        self.config_g = GroupConfig(path='/etc/group')
        self.binder = Binder(None, self.find('passwd-config'))
        self.binder_system = Binder(None, self.find('passwd-config-system'))
        self.binder_g = Binder(None, self.find('group-config'))

        self.mgr = UsersBackend.get()

        def post_item_bind(object, collection, item, ui):
            ui.find('change-password').on('click', self.change_password, item, ui)
            ui.find('remove-password').on('click', self.remove_password, item)
            if not os.path.exists(item.home):
                ui.find('create-home-dir').on('click', self.create_home_dir, item, ui)
                ui.find('create-home-dir').visible = True

        self.find('users').post_item_bind = post_item_bind
        self.find('system-users').post_item_bind = post_item_bind

    def on_page_load(self):
        self.refresh()

    def refresh(self):
        self.config.load()
        self.config_g.load()

        self.binder.setup(self.config.tree).populate()
        self.binder_system.setup(self.config.tree).populate()

        self.binder_g.setup(self.config_g.tree)
        self.find('group-members').labels = self.find('group-members').values = [x.name for x in self.config.tree.users]
        self.binder_g.populate()

    @on('add-user', 'click')
    def on_add_user(self):
        self.find('input-username').visible = True

    @on('input-username', 'submit')
    def on_add_user_done(self, value):
        self.mgr.add_user(value)
        self.refresh()

    @on('add-group', 'click')
    def on_add_group(self):
        self.find('input-groupname').visible = True

    @on('input-groupname', 'submit')
    def on_add_group_done(self, value):
        self.mgr.add_group(value)
        self.refresh()

    @on('save-users', 'click')
    def save_users(self):
        self.binder.update()
        self.config.save()

    @on('save-system-users', 'click')
    def save_system_users(self):
        self.binder_system.update()
        self.config.save()

    @on('save-groups', 'click')
    def save_groups(self):
        self.binder_g.update()
        self.config_g.save()

    def create_home_dir(self, user, ui):
        self.mgr.make_home_dir(user)
        self.context.notify('info', _('Home dir for %s was created') % user.name)
        ui.find('create-home-dir').visible = False

    def change_password(self, user, ui):
        new_password = ui.find('new-password').value

        if new_password:
            try:
                self.mgr.change_password(user, new_password)
                self.context.notify('info', _('Password for %s was changed') % user.name)
                ui.find('new-password').value = ''
            except Exception, e:
                self.context.notify('error', _('Error: "%s"') % e.message)
        else:
            self.context.notify('error', _('Password shouldn\'t be empty'))

    def remove_password(self, user):
        self.mgr.remove_password(user)
        self.context.notify('info', _('Password for %s was removed') % user.name)


@interface
class UsersBackend (object):
    def add_user(self, name):
        pass

    def add_group(self, name):
        pass

    def set_home(self, user):
        pass

    def change_password(self, user, password):
        proc = subprocess.Popen(
            ['passwd', user.name],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = proc.communicate('%s\n%s\n' % (password, password))
        if proc.returncode:
            raise Exception(stderr)

    def remove_password(self, user):
        subprocess.call(['passwd', '-d', user.name])

    def make_home_dir(self, user):
        subprocess.call(['mkdir', '-p', user.home])
        subprocess.call(['chown', '%s:%s' % (user.uid, user.gid), user.home])
        subprocess.call(['chmod', '755', user.home])
        self.set_home(user)


@plugin
class LinuxUsersBackend (UsersBackend):
    platforms = ['debian', 'centos', 'arch']

    def add_user(self, name):
        subprocess.call(['useradd', '-s', '/bin/false', name])

    def add_group(self, name):
        subprocess.call(['groupadd', name])

    def set_home(self, user):
        subprocess.call(['usermod', '-d', user.home, '-m', user.name])


@plugin
class BSDUsersBackend (UsersBackend):
    platforms = ['freebsd']

    def add_user(self, name):
        subprocess.call(['pw', 'useradd', '-s', '/bin/false', name])

    def add_group(self, name):
        subprocess.call(['pw', 'groupadd', name])

    def set_home(self, user):
        subprocess.call(['pw', 'usermod', '-d', user.home, '-m', user.name])

########NEW FILE########
__FILENAME__ = api
import logging
import os

from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder


class AvailabilitySymlinks (object):
    """
    Manage directories of following style::

        --sites.available
         |-a.site
         --b.site
        --sites.enabled
         --a.site -> ../sites.available/a.site
    """

    def __init__(self, dir_a, dir_e, supports_activation):
        self.dir_a, self.dir_e = dir_a, dir_e
        self.supports_activation = supports_activation

    def list_available(self):
        return [x for x in sorted(os.listdir(self.dir_a)) if not os.path.isdir(os.path.join(self.dir_a, x))]

    def is_enabled(self, entry):
        if not self.supports_activation:
            return True
        return self.find_link(entry) is not None

    def get_path(self, entry):
        return os.path.abspath(os.path.join(self.dir_a, entry))

    def find_link(self, entry):
        path = self.get_path(entry)

        for e in os.listdir(self.dir_e):
            if os.path.abspath(os.path.realpath(os.path.join(self.dir_e, e))) == path:
                return e

    def enable(self, entry):
        if not self.supports_activation:
            return
        e = self.find_link(entry)
        if not e:
            link_path = os.path.join(self.dir_e, entry)
            if not os.path.exists(link_path):
                os.symlink(self.get_path(entry), link_path)

    def disable(self, entry):
        if not self.supports_activation:
            return
        e = self.find_link(entry)
        if e:
            os.unlink(os.path.join(self.dir_e, e))

    def rename(self, old, new):
        on = self.is_enabled(old)
        self.disable(old)
        os.rename(self.get_path(old), self.get_path(new))
        if on:
            self.enable(new)

    def delete(self, entry):
        self.disable(entry)
        os.unlink(self.get_path(entry))

    def open(self, entry, mode='r'):
        return open(os.path.join(self.dir_a, entry), mode)

    def exists(self):
        return os.path.exists(self.dir_a) and os.path.exists(self.dir_e)


class WebserverHost (object):
    def __init__(self, owner, dir, entry):
        self.owner = owner
        self.name = entry
        self.dir = dir
        self.active = dir.is_enabled(entry)
        self.config = dir.open(entry).read()

    def save(self):
        self.dir.open(self.name, 'w').write(self.config)
        if self.active:
            self.dir.enable(self.name)
        else:
            self.dir.disable(self.name)


class WebserverPlugin (SectionPlugin):
    service_name = ''
    service_buttons = []
    hosts_available_dir = ''
    hosts_enabled_dir = ''
    template = ''
    supports_host_activation = True

    def log(self, msg):
        logging.info('[%s] %s' % (self.service_name, msg))

    def init(self):
        self.append(self.ui.inflate('webserver_common:main'))
        self.binder = Binder(None, self)
        self.find_type('servicebar').buttons = self.service_buttons
        self.hosts_dir = AvailabilitySymlinks(
            self.hosts_available_dir, 
            self.hosts_enabled_dir,
            self.supports_host_activation
        )

        def delete_host(host, c):
            self.log('removed host %s' % host.name)
            c.remove(host)
            self.hosts_dir.delete(host.name)

        def on_host_bind(o, c, host, u):
            host.__old_name = host.name

        def on_host_update(o, c, host, u):
            if host.__old_name != host.name:
                self.log('renamed host %s to %s' % (host.__old_name, host.name))
                self.hosts_dir.rename(host.__old_name, host.name)
            host.save()

        def new_host(c):
            name = 'untitled'
            while os.path.exists(self.hosts_dir.get_path(name)):
                name += '_'
            self.log('created host %s' % name)
            self.hosts_dir.open(name, 'w').write(self.template)
            return WebserverHost(self, self.hosts_dir, name)

        self.find('hosts').delete_item = delete_host
        self.find('hosts').new_item = new_host
        self.find('hosts').post_item_bind = on_host_bind
        self.find('hosts').post_item_update = on_host_update
        self.find('header-active-checkbox').visible = \
            self.find('body-active-line').visible = \
                self.supports_host_activation

    def on_page_load(self):
        self.refresh()

    @on('save-button', 'click')
    def save(self):
        self.log('saving hosts')
        self.binder.update()
        self.refresh()
        self.context.notify('info', 'Saved')

    def refresh(self):
        self.hosts = [WebserverHost(self, self.hosts_dir, x) for x in self.hosts_dir.list_available()]
        self.binder.setup(self).populate()
        self.find_type('servicebar').reload()

########NEW FILE########
__FILENAME__ = profiler
import time

_profiles = {}
_profiles_running = {}
_profiles_stack = []


def profile_start(name):
    """
    Starts a profiling interval with specific ``name``
    Profiling data is sent to the client with next data batch.
    """
    _profiles_running[name] = time.time()
    _profiles_stack.append(name)


def profile_end(name=None):
    """
    Ends a profiling interval with specific ``name``
    """
    last_name = _profiles_stack.pop()
    name = name or last_name
    if not name in _profiles:
        _profiles[name] = 0.0
    _profiles[name] += time.time() - _profiles_running[name]


def get_profiles():
    """
    Returns all accumulated profiling values
    """
    global _profiles
    r = _profiles
    _profiles = {}
    return r


def profiled(namefx=None):
    def decorator(fx):
        def wrapper(*args, **kwargs):
            if namefx:
                profile_start(namefx(args, kwargs))
            else:
                profile_start('%s %s %s' % (fx.__name__, args, kwargs))
            r = fx(*args, **kwargs)
            profile_end()
            return r

        return wrapper
    return decorator

########NEW FILE########
__FILENAME__ = routing
import socketio
import traceback

from ajenti.http import HttpHandler
from ajenti.api import BasePlugin, plugin, persistent, rootcontext
from ajenti.api.http import HttpPlugin, SocketPlugin
from ajenti.plugins import manager
from ajenti.profiler import *


class SocketIORouteHandler (HttpHandler):
    def __init__(self):
        self.namespaces = {}
        for cls in SocketPlugin.get_classes():
            self.namespaces[cls.name] = cls

    def handle(self, context):
        return str(socketio.socketio_manage(context.env, self.namespaces, context))


class InvalidRouteHandler (HttpHandler):
    def handle(self, context):
        context.respond_not_found()
        return 'Invalid URL'


@plugin
@persistent
@rootcontext
class CentralDispatcher (BasePlugin, HttpHandler):
    def __init__(self):
        self.invalid = InvalidRouteHandler()
        self.io = SocketIORouteHandler()

    @profiled(lambda a, k: 'HTTP %s' % a[1].path)
    def handle(self, context):
        """
        Dispatch the request to every HttpPlugin
        """

        if hasattr(context.session, 'appcontext'):
            self.context = context.session.appcontext
        else:
            self.context = manager.context

        if context.path.startswith('/ajenti:socket'):
            return context.fallthrough(self.io)

        if not hasattr(self.context, 'http_handlers'):
            self.context.http_handlers = HttpPlugin.get_all()

        for instance in self.context.http_handlers:
            try:
                output = instance.handle(context)
            except Exception, e:
                return [self.respond_error(context, e)]
            if output is not None:
                return output
        return context.fallthrough(self.invalid)

    def respond_error(self, context, exception):
        context.respond_server_error()
        stack = traceback.format_exc()
        return """
        <html>
            <body>

                <style>
                    body {
                        font-family: sans-serif;
                        color: #888;
                        text-align: center;
                    }

                    body pre {
                        width: 600px;
                        text-align: left;
                        margin: auto;
                        font-family: monospace;
                    }
                </style>

                <img src="/ajenti:static/main/error.jpeg" />
                <br/>
                <p>
                    Server error
                </p>
                <pre>
%s
                </pre>
            </body>
        </html>
        """ % stack

########NEW FILE########
__FILENAME__ = binder
import copy
import warnings

from ajenti.api import *
from ajenti.ui.element import p, UIElement
from ajenti.util import *


def is_bound_context(el):
    """
    :type el: UIElement
    :rtype: bool
    """
    return ('{binder}context' in el.properties) and el.properties['{binder}context'] is not None


def is_bound(el):
    """
    :type el: UIElement
    :rtype: bool
    """
    if el.typeid.startswith('bind:'):
        return True
    for prop in el.properties.keys():
        if prop == 'bind' or prop.startswith('{bind}') or is_bound_context(el):
            if el.properties[prop]:
                return True
    return False


@public
class Binding (object):
    """
    A base class for bindings. Binding is a link between a Python object attribute and Ajenti UI element's property.

    :param object: a Python object
    :param attribute: attribute name
    :param ui: Ajenti :class:`ajenti.ui.UIElement`
    """

    def __init__(self, object, attribute, ui):
        """
        :type object: object
        :type attribute: str
        :type ui: UIElement
        """
        self.object = object
        self.attribute = attribute
        self.ui = ui
        self.dict_mode = False
        if attribute and attribute.startswith('[') and attribute.endswith(']'):
            self.dict_mode = True
            self.attribute = self.attribute[1:-1]

    @classmethod
    def applicable(cls, object, attribute):
        try:
            cls.extract(object, attribute)
            return True
        except:
            return False

    @classmethod
    def extract(cls, object, attribute, ignore_errors=True):
        if attribute.startswith('[') and attribute.endswith(']'):
            if ignore_errors:
                return object.get(attribute[1:-1], None)
            else:
                return object.get[attribute[1:-1]]
        else:
            return getattr(object, attribute)

    def get(self):
        """
        :returns: value of the bound attribute
        """
        if self.dict_mode:
            return self.object.get(self.attribute, None)
        else:
            return getattr(self.object, self.attribute)

    def set(self, value):
        """
        Sets value of the bound attribute
        """
        try:
            if self.dict_mode:
                self.object[self.attribute] = value
            else:
                setattr(self.object, self.attribute, value)
        except Exception:
            raise Exception('Binder set failed: %s.%s = %s' % (self.object, self.attribute, repr(value)))

    def populate(self):
        """
        Should update the UI with attribute's value
        """

    def unpopulate(self):
        """
        Should revert UI to normal state
        """

    def update(self):
        """
        Should update the attribute with data from the UI
        """


@public
class PropertyBinding (Binding):
    """
    A simple binding between UI element's property and Python object's attribute

    :param property: UI property name. If ``None``, property is deduced from ``bindtypes``
    """

    def __init__(self, obj, attribute, ui, property=None):
        """
        :type attribute: str
        :type ui: UIElement
        :type property: str, None
        """
        Binding.__init__(self, obj, attribute, ui)
        if property is None:
            # find a property with matching bindtypes
            v = self.__get_transformed()
            for prop in ui.property_definitions.values():
                if prop.bindtypes:
                    # nb: we can't guess the type for None
                    if type(v) in prop.bindtypes or (v is None) or (object in prop.bindtypes):
                        self.property = prop.name
                        break
            else:
                raise Exception('Cannot bind %s.%s (%s, = %s) to %s' % (repr(obj), attribute, repr(type(v)), repr(v), ui))
        else:
            self.property = property
        self.oneway = ui.bindtransform is not None

    def __repr__(self):
        return u'[%s.%s <-> %s.%s]' % (self.object, self.attribute, self.ui, self.property)

    def __get_transformed(self):
        return self.ui.bindtransform(self.get()) if self.ui.bindtransform else self.get()

    def populate(self):
        self.old_value = self.get()
        setattr(self.ui, self.property, self.__get_transformed())

    def update(self):
        if self.oneway:
            return
        new_value = getattr(self.ui, self.property)
        # avoid unnecessary sets
        if new_value != self.old_value:
            self.set(new_value)


class DictValueBinding (PropertyBinding):
    def get(self):
        return self.object.get(self.attribute, None)

    def set(self, value):
        self.object[self.attribute] = value

    def update(self):
        if self.oneway:
            return
        self.set(getattr(self.ui, self.property))


@public
class ListAutoBinding (Binding):
    """
    Binds values of a collection to UI element's children consecutively, using :class:`Binder`
    """

    def __init__(self, object, attribute, ui):
        Binding.__init__(self, object, attribute, ui)
        self.binders = {}
        self.values = []

    def unpopulate(self):
        for binder in self.binders.values():
            binder.unpopulate()

    def populate(self):
        if self.attribute:
            self.collection = getattr(self.object, self.attribute)
        else:
            self.collection = self.object
        self.values = self.ui.values(self.collection)

        self.unpopulate()

        self.binders = {}
        index = 0

        if len(self.values) > len(self.ui.children):
            raise Exception('Number of bind:list children is less than collection size')

        for value in self.values:
            template = self.ui.children[index]
            index += 1
            binder = Binder(value, template)
            binder.populate()
            self.binders[value] = binder
            self.ui.post_item_bind(self.object, self.collection, value, template)

        self.ui.post_bind(self.object, self.collection, self.ui)
        return self

    def update(self):
        for value in self.values:
            self.binders[value].update()
            self.ui.post_item_update(self.object, self.collection, value, self.binders[value].ui)


@public
class DictAutoBinding (Binding):
    """
    Binds values from a dict to UI element's children mapping 'bind' attribute to dict key, using :class:`Binder`
    """

    def __init__(self, object, attribute, ui):
        Binding.__init__(self, object, attribute, ui)
        self.binders = {}

    def unpopulate(self):
        for binder in self.binders.values():
            binder.unpopulate()

    def populate(self):
        if self.attribute:
            self.collection = getattr(self.object, self.attribute)
        else:
            self.collection = self.object
        self.values = self.ui.values(self.collection)

        self.unpopulate()

        self.binders = {}
        bindables = self.ui.nearest(
            lambda x: is_bound(x),
            exclude=lambda x: (
                x != self.ui and is_bound_context(x.parent) and x.parent != self.ui
            )
        )

        for bindable in bindables:
            if bindable == self.ui:
                continue

            for prop in bindable.properties:
                if not bindable.properties[prop]:
                    continue
                if prop.startswith('{bind}'):
                    binder = DictValueBinding(self.values, bindable.properties[prop], bindable, prop.split('}')[1])
                elif prop == 'bind':
                    binder = DictValueBinding(self.values, bindable.bind, bindable)
                else:
                    continue
                key = bindable.properties[prop]
                binder.populate()
                self.binders[key] = binder

        self.ui.post_bind(self.object, self.collection, self.ui)
        return self

    def update(self):
        for key in self.binders:
            self.binders[key].update()
            self.ui.post_item_update(self.object, self.collection, key, self.binders[key].ui)


def _element_in_child_binder(root, e):
    """
    detect if the element is trapped inside a nested bind: tag
    relative to e

    :type root: UIElement
    :type e: UIElement
    :rtype: bool
    """
    return any(x.typeid.startswith('bind:') for x in root.path_to(e))


def _element_in_child_template(root, e):
    """
    detect if the element is trapped inside a nested bind: tag
    relative to e

    :type root: UIElement
    :type e: UIElement
    :rtype: bool
    """
    return any(x.typeid.startswith('bind:template') for x in root.path_to(e))


@public
class CollectionAutoBinding (Binding):
    """
    Binds values of a collection to UI element's children using a template.
    The expected UI layout::

        <xml xmlns:bind="bind">
            <bind:collection id="<binding to this>">
                <container-element bind="__items">
                    <1-- instantiated templates will appear here -->
                </container-element>

                <bind:template>
                    <!-- a template for one collection item
                         it will be bound to item using ajenti.ui.binder.Binder -->
                    <label bind="some_property" />

                    <button id="__delete" /> <!-- a delete button may appear in the template -->
                </bind:template>

                <button id="__add" /> <!-- an add button may appear inside collection tag -->
            </bind:collection>
        </xml>
    """

    def __init__(self, object, attribute, ui):
        Binding.__init__(self, object, attribute, ui)
        self.template = ui.find_type('bind:template')
        if self.template:
            if self.template.children:
                self.template = self.template.children[0]
            self.template_parent = self.template.parent
            self.template.visible = False
        self.items_ui = self.ui.nearest(lambda x: x.bind == '__items')[0] or self.ui
        self.old_items = copy.copy(self.items_ui.children)

        self.item_ui = {}
        self.binders = {}
        self.values = []

        self.last_template_hash = None

    def unpopulate(self):
        if self.template:
            self.template_parent.append(self.template)
        self.items_ui.empty()
        # restore original container content
        self.items_ui.children = copy.copy(self.old_items)
        return self

    def get_template(self, item, ui):
        # override for custom item template creation
        return self.template.clone()

    def populate(self):
        if self.template:
            self.template_parent.remove(self.template)

        if self.attribute:
            self.collection = getattr(self.object, self.attribute)
        else:
            self.collection = self.object

        self.values = self.ui.values(self.collection)
        if self.ui.sorting:
            self.values = sorted(self.values, key=self.ui.sorting)

        self.unpopulate()

        # Do it before DOM becomes huge
        self.items_ui.on('add', self.on_add)

        try:
            add_button = self.ui.nearest(lambda x: x.bind == '__add')[0]
            if not _element_in_child_binder(self.ui, add_button):
                add_button.on('click', self.on_add)
        except IndexError:
            pass

        if self.ui.pagesize:
            try:
                self.paging = None
                paging = self.ui.nearest(lambda x: x.bind == '__paging')[0]
                if not _element_in_child_binder(self.ui, paging):
                    self.paging = paging
                    paging.on('switch', self.set_page)
                    paging.length = int((len(self.values) - 1) / self.ui.pagesize) + 1
            except IndexError:
                pass

        self.item_ui = {}
        self.binders = {}
        for value in self.values:
            # apply the filter property
            if not self.ui.filter(value):
                continue

            template = self.get_template(value, self.ui)
            template.visible = True
            self.items_ui.append(template)
            self.item_ui[value] = template

            binder = Binder(value, template)
            binder.populate()
            self.binders[value] = binder

            try:
                del_button = template.nearest(lambda x: x.bind == '__delete')[0]
                if not _element_in_child_binder(template, del_button):
                    del_button.on('click', self.on_delete, value)
            except IndexError:
                pass

            self.ui.post_item_bind(self.object, self.collection, value, template)

        self.set_page(0)
        self.ui.post_bind(self.object, self.collection, self.ui)
        return self

    def set_page(self, page=0):
        if self.ui.pagesize:
            i = 0
            for value in self.values:
                self.item_ui[value].visible = int(i / self.ui.pagesize) == page
                i += 1
            if self.paging:
                self.paging.active = page

    def on_add(self):
        self.update()
        self.ui.add_item(self.ui.new_item(self.collection), self.collection)
        self.populate()

    def on_delete(self, item):
        self.update()
        self.ui.delete_item(item, self.collection)
        self.populate()

    def update(self):
        if hasattr(self.items_ui, 'sortable') and self.items_ui.order:
            sortable_indexes = []
            for i, e in enumerate(self.items_ui.children):
                if e.visible:
                    sortable_indexes.append(i)

            absolute_order = [sortable_indexes[i - 1] for i in self.items_ui.order]
            new_indexes = []
            absolute_order_idx = 0
            for i in range(len(self.values)):
                if i in sortable_indexes:
                    new_indexes.append(absolute_order[absolute_order_idx])
                    absolute_order_idx += 1
                else:
                    new_indexes.append(i)

            new_values = []
            for i in new_indexes:
                if i < len(self.collection):
                    new_values.append(self.values[i])

            while len(self.collection) > 0:
                self.collection.pop(0)
            for e in new_values:
                self.collection.append(e)
            self.items_ui.order = []

        for value in self.values:
            if self.ui.filter(value) and value in self.binders:
                self.binders[value].update()
                self.ui.post_item_update(self.object, self.collection, value, self.binders[value].ui)


@public
class Binder (object):
    """
    An automatic object-to-ui-hierarchy binder. Uses ``bind`` UI property to find what and where to bind.
    If ``object`` is not None, the Binder is also initialized (see ``setup(object)``) with this data object.

    :param object: Python object
    :param ui: UI hierarchy root
    """

    def __init__(self, object=None, ui=None):
        self.bindings = []
        self.ui = ui
        if object is not None:
            self.setup(object)

    def __warn_new_binder(self, s):
        import traceback; traceback.print_stack();
        warnings.warn(s, DeprecationWarning)
        print 'Binding syntax has been changed: see http://docs.ajenti.org/en/latest/dev/binding.html'

    def setup(self, object=None):
        """
        Initializes the Binder with a data object.
        :type object: object
        """
        self.unpopulate()
        if object is not None:
            self.object = object
        self.__autodiscover()
        return self

    def reset(self, object=None, ui=None):
        """
        Cancels the binding and replaces Python object / UI root.

        :type object: object
        :type ui: UIElement, None
        """
        self.__warn_new_binder('Binder.reset(object, ui)')
        self.unpopulate()
        if object is not None:
            self.object = object
        if ui:
            self.ui = ui
        return self

    def autodiscover(self, object=None, ui=None):
        self.__warn_new_binder('Binder.autodiscover(object, ui)')
        self.__autodiscover(object, ui)
        return self

    def __autodiscover(self, object=None, ui=None):
        """
        Recursively scans UI tree for ``bind`` properties, and creates bindings.
        """

        # Initial call
        if not object and not ui:
            self.bindings = []

        ui = ui or self.ui
        object = object or self.object

        bindables = ui.nearest(
            lambda x: is_bound(x),
            exclude=lambda x: (
                x.parent != ui and x != ui and (
                    '{bind}context' in x.parent.properties  # skip nested contexts
                    or x.parent.typeid.startswith('bind:')  # and templates and nested collections
                )
            )
        )

        for bindable in bindables:
            # Custom/collection binding
            if bindable.typeid.startswith('bind:'):
                k = bindable.bind
                if k and hasattr(object, k):
                    self.add(bindable.binding(object, k, bindable))
                continue

            for prop in bindable.properties:
                if not prop.startswith('{bind') and prop != 'bind':
                    continue

                k = bindable.properties[prop]

                # Nested binder context
                if prop == '{binder}context':
                    if bindable is not ui and k:
                        if Binding.applicable(object, k):
                            self.__autodiscover(Binding.extract(object, k), bindable)

                # Property binding
                if prop.startswith('{bind}') or prop == 'bind':
                    propname = None if prop == 'bind' else prop.split('}')[1]
                    if k and Binding.applicable(object, k):
                        self.add(PropertyBinding(object, k, bindable, propname))

        return self

    def add(self, binding):
        self.bindings.append(binding)

    def populate(self):
        """
        Populates the bindings.
        """
        for binding in self.bindings:
            binding.populate()
        return self

    def unpopulate(self):
        """
        Unpopulates the bindings.
        """
        for binding in self.bindings:
            binding.unpopulate()
        return self

    def update(self):
        """
        Updates the bindings.
        """
        for binding in self.bindings:
            binding.update()
        return self


# Helper elements
@p('post_bind', default=lambda o, c, u: None, type=eval, public=False,
    doc='Called after binding is complete, ``lambda object, collection, ui: None``')
@p('post_item_bind', default=lambda o, c, i, u: None, type=eval, public=False,
    doc='Called after an item is bound, ``lambda object, collection, item, item-ui: None``')
@p('post_item_update', default=lambda o, c, i, u: None, type=eval, public=False,
    doc='Called after an item is updated, ``lambda object, collection, item, item-ui: None``')
@p('binding', default=ListAutoBinding, type=eval, public=False,
    doc='Collection binding class to use')
@p('filter', default=lambda i: True, type=eval, public=False,
    doc='Called to filter collection''s values, ``lambda value: bool``')
@p('values', default=lambda c: c, type=eval, public=False,
    doc='Called to extract values from the collection, ``lambda collection: []``')
@public
class BasicCollectionElement (UIElement):
    pass


@public
@plugin
class ListElement (BasicCollectionElement):
    typeid = 'bind:list'


@public
@p('add_item', default=lambda i, c: c.append(i), type=eval, public=False,
    doc='Called to append value to the collection, ``lambda item, collection: None``')
@p('new_item', default=lambda c: None, type=eval, public=False,
    doc='Called to create an empty new item, ``lambda collection: object()``')
@p('delete_item', default=lambda i, c: c.remove(i), type=eval, public=False,
    doc='Called to remove value from the collection, ``lambda item, collection: None``')
@p('sorting', default=None, type=eval, public=False,
    doc='If defined, used as key function to sort items')
@p('pagesize', default=0, type=int, public=False)
@p('binding', default=CollectionAutoBinding, type=eval, public=False)
@plugin
class CollectionElement (BasicCollectionElement):
    typeid = 'bind:collection'


@p('binding', default=DictAutoBinding, type=eval, public=False)
@plugin
class DictElement (BasicCollectionElement):
    typeid = 'bind:dict'

########NEW FILE########
__FILENAME__ = element
from ajenti.api import *
from ajenti.util import *


@public
def p(prop, default=None, bindtypes=[], type=unicode, public=True, doc=None):
    """
    Creates an UI property inside an :class:`UIElement`::

        @p('title')
        @p('category', default='Other', doc='Section category name')
        @p('active', default=False)
        class SectionPlugin (BasePlugin, UIElement):
            typeid = 'main:section'

    :param default: Default value
    :type  default: object
    :param bindtypes: List of Python types that can be bound to this property
    :type  bindtypes: list
    :param type: expected Python type for this value
    :type  type: object
    :param public: whether this property is rendered and sent to client
    :type  public: bool
    :param doc: docstring
    :type  doc: str, None
    :rtype: function
    """

    def decorator(cls):
        prop_obj = UIProperty(prop, default=default, bindtypes=bindtypes, type=type, public=public)
        if not hasattr(cls, '_properties'):
            cls._properties = {}
        cls._properties = cls._properties.copy()
        cls._properties[prop] = prop_obj

        def get(self):
            return self.properties[prop]

        def set(self, value):
            self.properties_dirty[prop] |= self.properties[prop] != value
            self.properties[prop] = value

        _property = property(get, set, None, doc)
        if not hasattr(cls, prop):
            setattr(cls, prop, _property)
        return cls
    return decorator


@public
def on(id, event):
    """
    Sets the decorated method to handle indicated event::

        @plugin
        class Hosts (SectionPlugin):
            def init(self):
                self.append(self.ui.inflate('hosts:main'))
                ...

            @on('save', 'click')
            def save(self):
                self.config.save()

    :param id: element ID
    :type  id: str
    :param event: event name
    :type  event: str
    :rtype: function
    """

    def decorator(fx):
        fx._event_id = id
        fx._event_name = event
        return fx
    return decorator


@public
class UIProperty (object):
    __slots__ = ['name', 'default', 'bindtypes', 'type', 'public']

    def __init__(self, name, default=None, bindtypes=[], type=unicode, public=True):
        self.name = name
        self.default = default
        self.bindtypes = bindtypes
        self.type = type
        self.public = public

    def clone(self):
        return UIProperty(
            self.name,
            self.default,
            self.bindtypes,
            self.type,
            self.public,
        )


@public
@p('visible', default=True, type=bool,
    doc='Visibility of the element')
@p('bind', default=None, type=str, public=False,
    doc='Bound property name')
@p('client', default=False, type=True,
    doc='Whether this element\'s events are only processed on client side')
@p('bindtransform', default=None, type=eval, public=False,
    doc='Value transformation function for one-direction bindings')
@p('id', default=None, type=str, public=False,
    doc='Element ID')
@p('style', default='normal',
    doc='Additional CSS class')
@interface
@notrack
class UIElement (object):
    """ Base UI element class """

    typeid = None
    """ Unique identifier or element type class, used for XML tag name """

    __last_id = 0

    @classmethod
    def __generate_id(cls):
        cls.__last_id += 1
        return cls.__last_id

    def _prepare(self):
        #: Generated unique identifier (UID)
        self.uid = UIElement.__generate_id()
        if not hasattr(self, '_properties'):
            self._properties = []
        self.parent = None
        self.children = []
        self.children_changed = False
        self.invalidated = False
        self.events = {}
        self.event_args = {}
        self.context = None

    def __init__(self, ui, typeid=None, children=[], **kwargs):
        """
        :param ui: UI
        :type  ui: :class:`ajenti.ui.UI`
        :param typeid: type ID
        :type  typeid: str
        :param children:
        :type  children: list
        """
        self.ui = ui
        self._prepare()

        if typeid is not None:
            self.typeid = typeid

        for c in children:
            self.append(c)

        # Copy properties from the class
        self.properties = {}
        self.properties_dirty = {}
        for prop in self._properties.values():
            self.properties[prop.name] = prop.default
            self.properties_dirty[prop.name] = False
        for key in kwargs:
            self.properties[key] = kwargs[key]

    def __str__(self):
        return '<%s # %s>' % (self.typeid, self.uid)

    @property
    def property_definitions(self):
        return self.__class__._properties

    def clone(self, set_ui=None, set_context=None):
        """
        :returns: a deep copy of the element and its children. Property values are shallow copies.
        :rtype: :class:`UIElement`
        """
        o = self.__class__.__new__(self.__class__)
        o._prepare()
        o.ui, o.typeid, o.context = (set_ui or self.ui), self.typeid, (set_context or self.context)

        o.events = self.events.copy()
        o.event_args = self.event_args.copy()
        o.properties = self.properties.copy()
        o.properties_dirty = self.properties_dirty.copy()

        o.children = []
        for c in self.children:
            o.append(c.clone(set_ui=set_ui, set_context=set_context))

        o.post_clone()
        return o

    def init(self):
        pass

    def post_clone(self):
        pass

    def nearest(self, predicate, exclude=None, descend=True):
        """
        Returns the nearest child which matches an arbitrary predicate lambda

        :param predicate: ``lambda element: bool``
        :type  predicate: function
        :param exclude: ``lambda element: bool`` - excludes matching branches from search
        :type  exclude: function, None
        :param descend: whether to descend inside matching elements
        :type  descend: bool
        """
        r = []
        q = [self]
        while len(q) > 0:
            e = q.pop(0)
            if exclude and exclude(e):
                continue
            if predicate(e):
                r.append(e)
                if not descend and e is not self:
                    continue
            q.extend(e.children)
        return r

    def find(self, id):
        """
        :param id: element ID
        :type  id: str
        :returns: the nearest child with given ID or ``None``
        :rtype: :class:`UIElement`, None
        """
        r = self.nearest(lambda x: x.id == id)
        return r[0] if len(r) > 0 else None

    def find_uid(self, uid):
        """
        :param uid: element UID
        :type  uid: int
        :returns: the nearest child with given UID or ``None``
        :rtype: :class:`UIElement`, None
        """
        r = self.nearest(lambda x: x.uid == uid)
        return r[0] if len(r) > 0 else None

    def find_type(self, typeid):
        """
        :returns: the nearest child with given type ID or ``None``
        :rtype: :class:`UIElement`, None
        """
        r = self.nearest(lambda x: x.typeid == typeid)
        return r[0] if len(r) > 0 else None

    def contains(self, element):
        """
        Checks if the ``element`` is in the subtree of ``self``

        :param element: element
        :type  element: :class:`UIElement`
        """
        return len(self.nearest(lambda x: x == element)) > 0

    def path_to(self, element):
        """
        :returns: a list of elements forming a path from ``self`` to ``element``
        :rtype: list
        """
        r = []
        while element != self:
            r.insert(0, element)
            element = element.parent
        return r

    def render(self):
        """
        Renders this element and its subtree to JSON

        :rtype: dict
        """
        attributes = {
            'uid': self.uid,
            'typeid': self.typeid,
            'children': [c.render() for c in self.children if self.visible],
        }

        attr_defaults = {
            'visible': True,
            'client': False,
        }
        attr_map = {
            'children': '_c',
            'typeid': '_t',
            'style': '_s',
        }

        result = {}
        for key, value in attributes.iteritems():
            if attr_defaults.get(key, None) != value:
                result[attr_map.get(key, key)] = value

        for prop in self.properties:
            if self.property_definitions[prop].public:
                value = getattr(self, prop)
                if attr_defaults.get(prop, None) != value:
                    result[attr_map.get(prop, prop)] = value
        return result

    def on(self, event, handler, *args):
        """
        Binds event with ID ``event`` to ``handler``. ``*args`` will be passed to the ``handler``.
        :param event: event
        :type  event: str
        :param handler: handler
        :type  handler: function
        """
        self.events[event] = handler
        self.event_args[event] = args

    def has_updates(self):
        """
        Checks for pending UI updates
        """
        if self.children_changed or self.invalidated:
            return True
        if any(self.properties_dirty.values()):
            return True
        if self.visible:
            for child in self.children:
                if child.has_updates():
                    return True
        return False

    def clear_updates(self):
        """
        Marks all pending updates as processed
        """
        self.children_changed = False
        self.invalidated = False
        for property in self.properties:
            self.properties_dirty[property] = False
        if self.visible:
            for child in self.children:
                child.clear_updates()

    def invalidate(self):
        self.invalidated = True

    def broadcast(self, method, *args, **kwargs):
        """
        Calls ``method`` on every member of the subtree

        :param method: method
        :type  method: str
        """
        if hasattr(self, method):
            getattr(self, method)(*args, **kwargs)

        if not self.visible:
            return

        for child in self.children:
            child.broadcast(method, *args, **kwargs)

    def dispatch_event(self, uid, event, params=None):
        """
        Dispatches an event to an element with given UID

        :param uid: element UID
        :type  uid: int
        :param event: event name
        :type  event: str
        :param params: event arguments
        :type  params: dict, None
        """
        if not self.visible:
            return False
        if self.uid == uid:
            self.event(event, params)
            return True
        else:
            for child in self.children:
                if child.dispatch_event(uid, event, params):
                    for k in dir(self):
                        v = getattr(self, k)
                        if hasattr(v, '_event_id'):
                            element = self.find(v._event_id)
                            if element and element.uid == uid and v._event_name == event:
                                getattr(self, k)(**(params or {}))
                    return True

    def event(self, event, params=None):
        """
        Invokes handler for ``event`` on this element with given ``**params``

        :param event: event name
        :type  event: str
        :param params: event arguments
        :type  params: dict, None
        """
        self_event = event.replace('-', '_')
        if hasattr(self, 'on_%s' % self_event):
            getattr(self, 'on_%s' % self_event)(**(params or {}))
        if event in self.events:
            self.events[event](*self.event_args[event], **(params or {}))

    def reverse_event(self, event, params=None):
        """
        Raises the event on this element by feeding it to the UI root (so that ``@on`` methods in ancestors will work).

        :param event: event name
        :type  event: str
        :param params: event arguments
        :type  params: dict
        """
        self.ui.dispatch_event(self.uid, event, params)

    def empty(self):
        """
        Detaches all child elements
        """
        self.children = []
        self.children_changed = True

    def append(self, child):
        """
        Appends a ``child``

        :param child: child
        :type  child: :class:`UIElement`
        """
        if child in self.children:
            return
        self.children.append(child)
        child.parent = self
        self.children_changed = True

    def delete(self):
        """
        Detaches this element from its parent
        """
        self.parent.remove(self)

    def remove(self, child):
        """
        Detaches the ``child``

        :param child: child
        :type  child: :class:`UIElement`
        """
        self.children.remove(child)
        child.parent = None
        self.children_changed = True


@public
@plugin
class NullElement (UIElement):
    pass


########NEW FILE########
__FILENAME__ = inflater
from lxml import etree
import os
import logging

import ajenti
from ajenti.api import plugin, BasePlugin, persistent, rootcontext
from ajenti.plugins import manager
from ajenti.ui.element import UIProperty, UIElement, NullElement
from ajenti.util import *
#from ajenti.profiler import *


@public
class TemplateNotFoundError (Exception):
    pass


@public
@persistent
@rootcontext
@plugin
class Inflater (BasePlugin):
    def init(self):
        self.parser = etree.XMLParser()
        self.cache = {}
        self._element_cache = {}

    def precache(self):
        from ajenti.ui import UI
        temp_ui = UI.new()
        for plugin in manager.get_order():
            layout_dir = os.path.join(manager.resolve_path(plugin), 'layout')
            if os.path.exists(layout_dir):
                for layout in os.listdir(layout_dir):
                    layout_name = os.path.splitext(layout)[0]
                    if layout_name:
                        layout = '%s:%s' % (plugin, layout_name)
                        logging.debug('Precaching layout %s' % layout)
                        self.inflate(temp_ui, layout)

    def create_element(self, ui, typeid, *args, **kwargs):
        """
        Creates an element by its type ID.
        """
        cls = self.get_class(typeid)
        inst = cls.new(ui, context=(ui or self).context, *args, **kwargs)
        inst.typeid = typeid
        return inst

    def get_class(self, typeid):
        """
        :returns: element class by element type ID
        """
        if typeid in self._element_cache:
            return self._element_cache[typeid]
        for cls in UIElement.get_classes():
            if cls.typeid == typeid:
                self._element_cache[typeid] = cls
                return cls
        else:
            self._element_cache[typeid] = NullElement
            return NullElement

    def inflate(self, ui, layout):
        if not layout in self.cache or ajenti.debug:
            plugin, path = layout.split(':')
            try:
                file = open(os.path.join(manager.resolve_path(plugin), 'layout', path + '.xml'), 'r')
            except IOError, e:
                raise TemplateNotFoundError(e)
            data = file.read()
            data = """<xml xmlns:bind="bind" xmlns:binder="binder">%s</xml>""" % data
            xml = etree.fromstring(data, parser=self.parser)[0]
            self.cache[layout] = self.inflate_rec(ui, xml)
        layout = self.cache[layout].clone(set_ui=ui, set_context=(ui or self).context)
        return layout

    def inflate_rec(self, ui, node):
        if callable(node.tag):
            # skip comments
            return None

        tag = node.tag.replace('{', '').replace('}', ':')

        if tag == 'include':
            return self.inflate(ui, node.attrib['layout'])

        cls = self.get_class(tag)
        props = {}
        extra_props = {}

        for key in node.attrib:
            value = node.attrib[key]
            if value.startswith('{') and value.endswith('}'):
                value = _(value[1:-1])
            value = value.replace('\\n', '\n')
            for prop in cls._properties.values():
                if prop.name == key:
                    if prop.type in [int, float, unicode, eval]:
                        value = prop.type(value)
                    elif prop.type in [list, dict]:
                        value = eval(value)
                    elif prop.type == bool:
                        value = value == 'True'
                    props[key] = value
                    break
            else:
                extra_props[key] = value

        children = filter(None, list(self.inflate_rec(ui, child) for child in node))
        element = self.create_element(ui, tag, children=children, **props)
        for k, v in extra_props.iteritems():
            element.property_definitions[k] = UIProperty(name=k, public=False)
            element.properties[k] = v
        return element

########NEW FILE########
__FILENAME__ = users
import logging
import syslog
from passlib.hash import sha512_crypt

import ajenti
import ajenti.usersync
from ajenti.api import *


def restrict(permission):
    """
    Marks a decorated function as requiring ``permission``.
    If the invoking user doesn't have one, :class:`SecurityError` is raised.
    """
    def decorator(fx):
        def wrapper(*args, **kwargs):
            UserManager.get().require_permission(extract_context(), permission)
            return fx(*args, **kwargs)
        return wrapper
    return decorator


class SecurityError (Exception):
    """
    Indicates that user didn't have a required permission.

    .. attribute:: permission

        permission ID
    """

    def __init__(self, permission):
        self.permission = permission

    def __str__(self):
        return 'Permission "%s" required' % self.permission


@plugin
@persistent
@rootcontext
class UserManager (BasePlugin):
    default_classconfig = {'sync-provider': ''}
    classconfig_root = True

    def check_password(self, username, password, env=None):
        """
        Verifies the given username/password combo

        :type username: str
        :type password: str
        :rtype: bool
        """
        provider = self.get_sync_provider(fallback=True)
        if username == 'root' and not provider.syncs_root:
            provider = ajenti.usersync.AjentiSyncProvider.get()

        if not username in ajenti.config.tree.users:
            return False

        try:
            provider.sync()
        except Exception as e:
            logging.error(str(e))

        result = provider.check_password(username, password)

        provider_name = type(provider).__name__

        ip_notion = ''
        ip = env.get('REMOTE_ADDR', None) if env else None
        if ip:
            ip_notion = ' from %s' % ip

        if not result:
            msg = 'failed login attempt for %s ("%s") through %s%s' % \
                (username, password, provider_name, ip_notion)
            syslog.syslog(syslog.LOG_WARNING, msg)
            logging.warn(msg)
        else:
            msg = 'user %s logged in through %s%s' % (username, provider_name, ip_notion)
            syslog.syslog(syslog.LOG_INFO, msg)
            logging.info(msg)
        return result

    def hash_password(self, password):
        """
        :type password: str
        :rtype: str
        """
        if not password.startswith('sha512|'):
            password = 'sha512|%s' % sha512_crypt.encrypt(password)
        return password

    def hash_passwords(self):
        for user in ajenti.config.tree.users.values():
            if not '|' in user.password:
                user.password = self.hash_password(user.password)

    def has_permission(self, context, permission):
        """
        Checks whether the current user has a permission

        :type permission: str
        :rtype: bool
        """
        if context.user.name == 'root':
            return True
        if not permission in context.user.permissions:
            return False
        return True

    def require_permission(self, context, permission):
        """
        Checks current user for given permission and
        raises :class:`SecurityError` if he doesn't have one
        :type permission: str
        :raises: SecurityError
        """
        if not self.has_permission(context, permission):
            raise SecurityError(permission)

    def get_sync_provider(self, fallback=False):
        """
        :type fallback: bool
        :rtype: ajenti.usersync.UserSyncProvider
        """
        for p in ajenti.usersync.UserSyncProvider.get_classes():
            p.get()
            if p.id == self.classconfig['sync-provider']:
                try:
                    p.get().test()
                except:
                    if fallback:
                        return ajenti.usersync.AjentiSyncProvider.get()
                return p.get()

    def set_sync_provider(self, provider_id):
        self.classconfig['sync-provider'] = provider_id
        self.save_classconfig()

    def set_password(self, username, password):
        ajenti.config.tree.users[username].password = self.hash_password(password)


@interface
class PermissionProvider (object):
    """
    Override to create your own set of permissions
    """

    def get_permissions(self):
        """
        Should return a list of permission names

        :rtype: list
        """
        return []

    def get_name(self):
        """
        Should return a human-friendly name for this set
        of permissions (displayed in Configurator)
        :rtype: str
        """
        return ''


__all__ = ['restrict', 'PermissionProvider', 'SecurityError', 'UserManager']

########NEW FILE########
__FILENAME__ = adsync
try:
    import ldap
except ImportError:
    ldap = None

import ajenti
from ajenti.api import *
from ajenti.plugins.configurator.api import ClassConfigEditor

from reconfigure.items.ajenti import UserData

from base import UserSyncProvider



@plugin
class ADSyncClassConfigEditor (ClassConfigEditor):
    title = _('Active Directory Syncronization')
    icon = 'refresh'

    def init(self):
        self.append(self.ui.inflate('configurator:ad-sync-config'))


@plugin
class ActiveDirectorySyncProvider (UserSyncProvider, BasePlugin):
    id = 'ad'
    title = 'Active Directory'
    default_classconfig = {
        'address': 'localhost',
        'domain': 'DOMAIN',
        'user': 'Administrator',
        'password': '',
        'base': 'cn=Users,dc=DOMAIN',
    }
    classconfig_root = True
    classconfig_editor = ADSyncClassConfigEditor

    @classmethod
    def verify(cls):
        return ldap is not None

    def __get_ldap(self):
        if not ldap:
            return None

        c = ldap.initialize('ldap://' + self.classconfig['address'])
        c.bind_s('%s\\%s' % (self.classconfig['domain'], self.classconfig.get('user', 'Administrator')), self.classconfig['password'])
        c.set_option(ldap.OPT_REFERRALS, 0)
        return c

    def test(self):
        self.__search()

    def check_password(self, username, password):
        l = self.__get_ldap()
        try:
            return bool(l.bind_s('%s\\%s' % (self.classconfig['domain'], username), password))
        except Exception, e:
            print e
            return False

    def __search(self):
        l = self.__get_ldap()
        return l.search_s(
            self.classconfig['base'],
            ldap.SCOPE_SUBTREE,
            '(|(objectClass=user)(objectClass=simpleSecurityObject))',
            ['sAMAccountName']
        )

    def sync(self):
        found_names = []
        users = self.__search()
        for u in users:
            username = u[1]['sAMAccountName'][0]
            found_names.append(username)
            if not username in ajenti.config.tree.users:
                u = UserData()
                u.name = username
                ajenti.config.tree.users[username] = u

        for user in list(ajenti.config.tree.users.values()):
            if not user.name in found_names and user.name != 'root':
                ajenti.config.tree.users.pop(user.name)

        ajenti.config.save()

########NEW FILE########
__FILENAME__ = base
from ajenti.api import *


@interface
class UserSyncProvider (BasePlugin):
    allows_renaming = False
    syncs_root = False
    
    def test(self):
        return False

    def check_password(self, username, password):
        return False

    def sync(self):
        pass
########NEW FILE########
__FILENAME__ = ldapsync
try:
    import ldap
except ImportError:
    ldap = None

import ajenti
from ajenti.api import *
from ajenti.plugins.configurator.api import ClassConfigEditor

from reconfigure.items.ajenti import UserData

from base import UserSyncProvider


@plugin
class LDAPSyncClassConfigEditor (ClassConfigEditor):
    title = _('LDAP User Syncronization')
    icon = 'refresh'

    def init(self):
        self.append(self.ui.inflate('configurator:ldap-sync-config'))


@plugin
class LDAPSyncProvider (UserSyncProvider):
    id = 'ldap'
    title = 'LDAP'
    default_classconfig = {
        'url': 'ldap://localhost',
        'admin_dn': 'cn=admin,dc=nodomain',
        'auth_dn': 'dc=nodomain',
        'secret': '',
    }
    classconfig_root = True
    classconfig_editor = LDAPSyncClassConfigEditor

    def __get_ldap(self):
        if not ldap:
            return None

        c = ldap.initialize(self.classconfig['url'])
        c.bind_s(self.classconfig['admin_dn'], self.classconfig['secret'])
        return c

    @classmethod
    def verify(cls):
        return ldap is not None

    def test(self):
        self.__get_ldap()

    def check_password(self, username, password):
        l = self.__get_ldap()
        try:
            return bool(l.bind_s('cn=%s,' % username + self.classconfig['auth_dn'], password))
        except Exception, e:
            print e
            return False

    def sync(self):
        found_names = []
        l = self.__get_ldap()
        users = l.search_s(
            self.classconfig['auth_dn'],
            ldap.SCOPE_SUBTREE,
            '(|(objectClass=user)(objectClass=simpleSecurityObject))',
            ['cn']
        )
        for u in users:
            username = u[1]['cn'][0]
            found_names.append(username)
            if not username in ajenti.config.tree.users:
                u = UserData()
                u.name = username
                ajenti.config.tree.users[username] = u

        for user in list(ajenti.config.tree.users.values()):
            if not user.name in found_names and user.name != 'root':
                ajenti.config.tree.users.pop(user.name)

        ajenti.config.save()

########NEW FILE########
__FILENAME__ = local
from passlib.hash import sha512_crypt

import ajenti
from ajenti.api import *

from base import UserSyncProvider


@plugin
class AjentiSyncProvider (UserSyncProvider):
    id = ''
    title = _('Off')
    allows_renaming = True
    syncs_root = True

    def test(self):
        pass

    def check_password(self, username, password):
        if not username in ajenti.config.tree.users:
            return False
        type = 'plain'
        saved = ajenti.config.tree.users[username].password
        if '|' in saved:
            type, saved = saved.split('|')

        if type == 'plain':
            hash = password
            return hash == saved
        elif sha512_crypt.identify(saved):
            return sha512_crypt.verify(password, saved)

    def sync(self):
        pass
########NEW FILE########
__FILENAME__ = pam
# (c) 2007 Chris AtLee <chris@atlee.ca>
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
PAM module for python

Provides an authenticate function that will allow the caller to authenticate
a user against the Pluggable Authentication Modules (PAM) on the system.

Implemented using ctypes, so no compilation is necessary.
"""
__all__ = ['authenticate']

from ctypes import CDLL, POINTER, Structure, CFUNCTYPE, cast, pointer, sizeof
from ctypes import c_void_p, c_uint, c_char_p, c_char, c_int
from ctypes.util import find_library

LIBPAM = CDLL(find_library("pam"))
LIBC = CDLL(find_library("c"))

CALLOC = LIBC.calloc
CALLOC.restype = c_void_p
CALLOC.argtypes = [c_uint, c_uint]

STRDUP = LIBC.strdup
STRDUP.argstypes = [c_char_p]
STRDUP.restype = POINTER(c_char) # NOT c_char_p !!!!

# Various constants
PAM_PROMPT_ECHO_OFF = 1
PAM_PROMPT_ECHO_ON = 2
PAM_ERROR_MSG = 3
PAM_TEXT_INFO = 4

class PamHandle(Structure):
    """wrapper class for pam_handle_t"""
    _fields_ = [
            ("handle", c_void_p)
            ]

    def __init__(self):
        Structure.__init__(self)
        self.handle = 0

class PamMessage(Structure):
    """wrapper class for pam_message structure"""
    _fields_ = [
            ("msg_style", c_int),
            ("msg", POINTER(c_char)),
            ]

    def __repr__(self):
        return "<PamMessage %i '%s'>" % (self.msg_style, self.msg)

class PamResponse(Structure):
    """wrapper class for pam_response structure"""
    _fields_ = [
            ("resp", POINTER(c_char)),
            ("resp_retcode", c_int),
            ]

    def __repr__(self):
        return "<PamResponse %i '%s'>" % (self.resp_retcode, self.resp)

CONV_FUNC = CFUNCTYPE(c_int,
        c_int, POINTER(POINTER(PamMessage)),
               POINTER(POINTER(PamResponse)), c_void_p)

class PamConv(Structure):
    """wrapper class for pam_conv structure"""
    _fields_ = [
            ("conv", CONV_FUNC),
            ("appdata_ptr", c_void_p)
            ]

PAM_START = LIBPAM.pam_start
PAM_START.restype = c_int
PAM_START.argtypes = [c_char_p, c_char_p, POINTER(PamConv),
        POINTER(PamHandle)]

PAM_END = LIBPAM.pam_end
PAM_END.restpe = c_int
PAM_END.argtypes = [PamHandle, c_int]

PAM_AUTHENTICATE = LIBPAM.pam_authenticate
PAM_AUTHENTICATE.restype = c_int
PAM_AUTHENTICATE.argtypes = [PamHandle, c_int]

def authenticate(username, password, service='login'):
    """Returns True if the given username and password authenticate for the
    given service.  Returns False otherwise
    
    ``username``: the username to authenticate
    
    ``password``: the password in plain text
    
    ``service``: the PAM service to authenticate against.
                 Defaults to 'login'"""
    @CONV_FUNC
    def my_conv(n_messages, messages, p_response, app_data):
        """Simple conversation function that responds to any
        prompt where the echo is off with the supplied password"""
        # Create an array of n_messages response objects
        addr = CALLOC(n_messages, sizeof(PamResponse))
        p_response[0] = cast(addr, POINTER(PamResponse))
        for i in range(n_messages):
            if messages[i].contents.msg_style == PAM_PROMPT_ECHO_OFF:
                pw_copy = STRDUP(str(password))
                p_response.contents[i].resp = pw_copy
                p_response.contents[i].resp_retcode = 0
        return 0

    handle = PamHandle()
    conv = PamConv(my_conv, 0)
    retval = PAM_START(service, username, pointer(conv), pointer(handle))

    if retval != 0:
        # TODO: This is not an authentication error, something
        # has gone wrong starting up PAM
        PAM_END(handle, retval)
        return False

    retval = PAM_AUTHENTICATE(handle, 0)
    e = PAM_END(handle, retval)
    return retval == 0 and e == 0

########NEW FILE########
__FILENAME__ = unix
import ajenti
from ajenti.api import *

from reconfigure.items.ajenti import UserData

from base import UserSyncProvider
from pam import authenticate



@plugin
class UNIXSyncProvider (UserSyncProvider):
    id = 'unix'
    title = _('OS users')
    syncs_root = True

    def test(self):
        pass

    def check_password(self, username, password):
        return authenticate(username, password, 'passwd')

    def sync(self):
        found_names = []
        for l in open('/etc/shadow').read().splitlines():
            l = l.split(':')
            if len(l) >= 2:
                username, pwd = l[:2]
                if len(pwd) > 2:
                    found_names.append(username)
                    if not username in ajenti.config.tree.users:
                        u = UserData()
                        u.name = username
                        ajenti.config.tree.users[username] = u

        for user in list(ajenti.config.tree.users.values()):
            if not user.name in found_names and user.name != 'root':
                ajenti.config.tree.users.pop(user.name)

        ajenti.config.save()

########NEW FILE########
__FILENAME__ = util
from datetime import timedelta
import catcher
import locale
import logging
import subprocess
import sys
import time
import traceback

import ajenti


def public(f):
    """"
    Use a decorator to avoid retyping function/class names.

    Based on an idea by Duncan Booth:
    http://groups.google.com/group/comp.lang.python/msg/11cbb03e09611b8a

    Improved via a suggestion by Dave Angel:
    http://groups.google.com/group/comp.lang.python/msg/3d400fb22d8a42e1

    """
    all = sys.modules[f.__module__].__dict__.setdefault('__all__', [])
    if f.__name__ not in all:  # Prevent duplicates if run from an IDE.
        all.append(f.__name__)
    return f
public(public)  # Emulate decorating ourself


@public
def str_fsize(sz):
    """
    Formats file size as string (i.e., 1.2 Mb)
    """
    if sz < 1024:
        return '%.1f bytes' % sz
    sz /= 1024.0
    if sz < 1024:
        return '%.1f KB' % sz
    sz /= 1024.0
    if sz < 1024:
        return '%.1f MB' % sz
    sz /= 1024.0
    if sz < 1024:
        return '%.1f GB' % sz
    sz /= 1024.0
    return '%.1f TB' % sz


@public
def str_timedelta(s):
    """
    Formats a time delta (i.e., "5 days, 5:06:07")
    """
    return str(timedelta(0, s)).split('.')[0]


@public
def cache_value(duration=None):
    """
    Makes a function lazy.

    :param duration: cache duration in seconds (default: infinite)
    :type  duration: int
    """
    def decorator(fx):
        fx.__cached = None
        fx.__cached_at = 0

        def wrapper(*args, **kwargs):
            dt = time.time() - fx.__cached_at
            if (dt > duration and duration is not None) or \
                    (fx.__cached_at == 0 and duration is None):
                val = fx(*args, **kwargs)
                fx.__cached = val
                fx.__cached_at = time.time()
            else:
                val = fx.__cached
            return val
        wrapper.__doc__ = fx.__doc__
        return wrapper
    return decorator


@public
def platform_select(**values):
    """
    Selects a value from **kwargs** depending on runtime platform

    ::

        service = platform_select(
            debian='samba',
            ubuntu='smbd',
            centos='smbd',
            default='samba',
        )

    """
    if ajenti.platform_unmapped in values:
        return values[ajenti.platform_unmapped]
    if ajenti.platform in values:
        return values[ajenti.platform]
    return values.get('default', None)


@public
def make_report(e):
    """
    Formats a bug report.
    """
    import platform as _platform
    from ajenti.plugins import manager
    from ajenti import platform, platform_unmapped, platform_string, installation_uid, version, debug

    # Finalize the reported log
    logging.blackbox.stop()

    tb = traceback.format_exc(e)
    tb = '\n'.join('    ' + x for x in tb.splitlines())
    log = logging.blackbox.buffer
    log = '\n'.join('    ' + x for x in log.splitlines())

    catcher_url = None
    try:
        report = catcher.collect(e)
        html = catcher.formatters.HTMLFormatter().format(report, maxdepth=3)
        catcher_url = catcher.uploaders.AjentiOrgUploader().upload(html)
    except:
        pass

    import gevent
    import greenlet
    import reconfigure
    import requests
    import psutil

    return """Ajenti bug report
--------------------


Info | Value
----- | -----
Ajenti | %s
Platform | %s / %s / %s
Architecture | %s
Python | %s
Installation | %s
Debug | %s
Catcher report | %s
Loaded plugins | %s

Library | Version
------- | -------
gevent | %s
greenlet | %s
reconfigure | %s
requests | %s
psutil | %s


%s

Log content:

%s
            """ % (
        version,
        platform, platform_unmapped, platform_string.strip(),
        subprocess.check_output(['uname', '-mp']).strip(),
        '.'.join([str(x) for x in _platform.python_version_tuple()]),
        installation_uid,
        debug,
        catcher_url or 'Failed to upload traceback',
        ', '.join(sorted(manager.get_order())),

        gevent.__version__,
        greenlet.__version__,
        reconfigure.__version__,
        requests.__version__,
        psutil.__version__,

        tb,
        log,
    )

########NEW FILE########
__FILENAME__ = compile_resources
#!/usr/bin/env python
import subprocess
import shutil
import glob
import os
import re
import sys
import gevent

try:
    from gevent import subprocess
except:
    import subprocess

import uuid
import threading

import logging
import ajenti.compat
import ajenti.log


def check_output(*args, **kwargs):
    try:
        return subprocess.check_output(*args, **kwargs)
    except Exception, e:
        logging.error('Call failed')
        logging.error(' '.join(args[0]))
        logging.error(str(e))
        sys.exit(0)


ajenti.log.init()


def dirname():
    return 'tmp/' + str(uuid.uuid4())

def compile_coffeescript(inpath):
    outpath = '%s.c.js' % inpath

    if os.path.exists(outpath) and os.stat(outpath).st_mtime > os.stat(inpath).st_mtime:
        logging.info('Skipping %s' % inpath)
        return

    logging.info('Compiling CoffeeScript: %s' % inpath)

    d = dirname()
    check_output('coffee -o %s -c "%s"' % (d, inpath), shell=True)
    shutil.move(glob.glob('./%s/*.js' % d)[0], outpath)
    shutil.rmtree(d)


def compile_less(inpath):
    outpath = '%s.c.css' % inpath

    if os.path.exists(outpath) and os.stat(outpath).st_mtime > os.stat(inpath).st_mtime:
        logging.info('Skipping %s' % inpath)
        #return

    logging.info('Compiling LESS %s' % inpath)
    out = check_output('lessc "%s" "%s"' % (inpath, outpath), shell=True)
    if out:
        logging.error(out)
    #print subprocess.check_output('recess --compile "%s" > "%s"' % (inpath, outpath), shell=True)

compilers = {
    r'.+\.coffee$': compile_coffeescript,
    r'.+[^i]\.less$': compile_less,
}



greenlets = []

def traverse(fx):
    plugins_path = './ajenti/plugins'
    for plugin in os.listdir(plugins_path):
        path = os.path.join(plugins_path, plugin, 'content')
        if os.path.exists(path):
            for (dp, dn, fn) in os.walk(path):
                for name in fn:
                    file_path = os.path.join(dp, name)
                    greenlets.append(gevent.spawn(fx, file_path))

    done = 0
    done_gls = []
    length = 40
    total = len(greenlets)
    print

    while True:
        for gl in greenlets:
            if gl.ready() and not gl in done_gls:
                done_gls.append(gl)
                done += 1
                dots = int(1.0 * length * done / total)
                sys.stdout.write('\r%3i/%3i [' % (done, total) + '.' * dots + ' ' * (length - dots) + ']')
                sys.stdout.flush()
        gevent.sleep(0.1)
        if done == total:
            print
            break



def compile(file_path):
    for pattern in compilers:
        if re.match(pattern, file_path):
            compilers[pattern](file_path)



if not os.path.exists('tmp'):
    os.mkdir('tmp')

greenlets = []
traverse(compile)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, os.path.abspath('../..'))

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.ifconfig', 'sphinx.ext.viewcode']  # 'sphinx.ext.intersphinx']

templates_path = ['_templates']

source_suffix = '.rst'

master_doc = 'index'

project = u'Ajenti'
copyright = u'2013, Eugene Pankov'

import ajenti
version = ajenti.__version__
release = ajenti.__version__

exclude_patterns = []
add_function_parentheses = True

pygments_style = 'sphinx'


# ReadTheDocs
import os
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if not on_rtd:  # only import and set the theme if we're building docs locally
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

html_static_path = ['_static']
htmlhelp_basename = 'Ajentidoc'


html_context = {
    "disqus_shortname": 'ajenti',
    "github_base_account": 'Eugeny',
    "github_project": 'ajenti',
}

# Gettext
import gettext
translation = gettext.NullTranslations()
translation.install(unicode=True)


intersphinx_mapping = {'http://docs.python.org/': None}


def skip(app, what, name, obj, skip, options):
    if hasattr(obj, '_plugin'):
        for x in ['get', 'new', 'classname']:
            if hasattr(obj, x):
                try:
                    delattr(obj, x)
                except:
                    pass
    if hasattr(obj, '_interface'):
        for x in ['get', 'get_all', 'get_instances', 'get_class', 'get_classes']:
            if hasattr(obj, x):
                try:
                    delattr(obj, x)
                except:
                    pass
    return skip


def setup(app):
    app.connect("autodoc-skip-member", skip)




USE_PIP_INSTALL = True

class Mock(object):
    __all__ = []

    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return Mock()

    @classmethod
    def __getattr__(cls, name):
        if name in ('__file__', '__path__'):
            return '/dev/null'
        elif name[0] == name[0].upper():
            mockType = type(name, (), {})
            mockType.__module__ = __name__
            return mockType
        else:
            return Mock()

MOCK_MODULES = ['python-ldap', 'gevent', 'gevent-socketio', 'lxml', 'lxml.etree', 'pyOpenSSL', 'Pillow', 'psutil']
for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = Mock()
########NEW FILE########
__FILENAME__ = make_messages
#!/usr/bin/env python
import os
import sys
import subprocess
from lxml import etree

import logging
import ajenti.log


def check_call(*args):
    try:
        subprocess.call(*args)
    except Exception, e:
        logging.error('Call failed')
        logging.error(' '.join(args[0]))
        logging.error(str(e))


ajenti.log.init()

LOCALEDIR = 'ajenti/locales'
LANGUAGES = [x for x in os.listdir(LOCALEDIR) if not '.' in x]

pot_path = os.path.join(LOCALEDIR, 'ajenti.po')

if len(sys.argv) != 2:
    logging.error('Usage: ./make_messages.py [extract|compile]')
    sys.exit(1)

if subprocess.call(['which', 'xgettext']) != 0:
    logging.error('xgettext app not found')
    sys.exit(0)

if sys.argv[1] == 'extract':
    os.unlink(pot_path)
    for (dirpath, dirnames, filenames) in os.walk('ajenti', followlinks=True):
        if '/custom_' in dirpath:
            continue
        if '/elements' in dirpath:
            continue
        for f in filenames:
            path = os.path.join(dirpath, f)
            if f.endswith('.py'):
                logging.info('Extracting from %s' % path)
                check_call([
                    'xgettext',
                    '-c',
                    '--from-code=utf-8',
                    '--omit-header',
                    '-o', pot_path,
                    '-j' if os.path.exists(pot_path) else '-dajenti',
                    path,
                ])
            if f.endswith('.xml'):
                logging.info('Extracting from %s' % path)
                content = open(path).read()
                xml = etree.fromstring('<xml xmlns:bind="bind" xmlns:binder="binder">' + content + '</xml>')
                try:
                    msgs = []

                    def traverse(n):
                        for k, v in n.items():
                            if v.startswith('{') and v.endswith('}'):
                                msgs.append(v[1:-1])
                            try:
                                if "_('" in v:
                                    eval(v, {'_': msgs.append})
                            except:
                                pass
                        for c in n:
                            traverse(c)
                    traverse(xml)

                    fake_content = ''.join('gettext("%s");\n' % msg for msg in msgs)
                    fake_content = 'void main() { ' + fake_content + ' }'

                    open(path, 'w').write(fake_content)
                    check_call([
                        'xgettext',
                        '-C',
                        '--from-code=utf-8',
                        '--omit-header',
                        '-o', pot_path,
                        '-j' if os.path.exists(pot_path) else '-dajenti',
                        path,
                    ])
                finally:
                    open(path, 'w').write(content)

if sys.argv[1] == 'compile':
    for lang in LANGUAGES:
        po_dir = os.path.join(LOCALEDIR, lang, 'LC_MESSAGES')
        po_path = os.path.join(po_dir, 'ajenti.po')
        mo_path = os.path.join(po_dir, 'ajenti.mo')

        if not os.path.exists(po_dir):
            os.makedirs(po_dir)

        logging.info('Compiling %s' % lang)
        check_call([
            'msgfmt',
            po_path,
            '-v',
            '-o', mo_path
        ])

########NEW FILE########
