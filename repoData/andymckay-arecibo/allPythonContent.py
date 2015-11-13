__FILENAME__ = wrapper
# this requires Django to get at the settings
# not sure what other apps do for thi
from django.conf import settings
from django.http import HttpResponse
from django.utils import simplejson
from django.middleware.common import _is_ignorable_404

from google.appengine.api import urlfetch
from google.appengine.api import mail

from urllib import urlencode
from urlparse import urljoin, urlparse, urlunparse

import logging
import traceback
import sys
import time

def get_host(request):
    """Returns the HTTP host using the environment or request headers."""
    # We try three options, in order of decreasing preference.
    if 'HTTP_X_FORWARDED_HOST' in request.META:
        host = request.META['HTTP_X_FORWARDED_HOST']
    elif 'HTTP_HOST' in request.META:
        host = request.META['HTTP_HOST']
    else:
        # Reconstruct the host using the algorithm from PEP 333.
        host = request.META['SERVER_NAME']
        server_port = request.META['SERVER_PORT']
        if server_port != (request.is_secure() and 443 or 80):
            host = '%s:%s' % (host, server_port)
    return host

def getpath(request):
    location = request.get_full_path()
    if not ':' in location:
        current_uri = '%s://%s%s' % (request.is_secure() and 'https' or 'http',
                    get_host(request), request.path)
        location = urljoin(current_uri, location)
    return location

def post(request, status, **kw):
    exc_info = sys.exc_info()

    path = request.get_full_path()
    if _is_ignorable_404(path):
        return

    if request.META.get('REMOTE_ADDR') in settings.INTERNAL_IPS:
        return

    data = {
        "account": settings.ARECIBO_PUBLIC_ACCOUNT_NUMBER,
        "url": getpath(request),
        "ip": request.META.get('REMOTE_ADDR'),
        "traceback": "\n".join(traceback.format_tb(exc_info[2])),
        "type": str(exc_info[0].__name__),
        "msg": str(exc_info[1]),
        "status": status,
        "uid": time.time(),
        "user_agent": request.META.get('HTTP_USER_AGENT'),
        "server": "Google App Engine"
    }

    # it could be the site does not have the standard django auth
    # setup and hence no reques.user
    try:
        data["username"] = request.user.username,
        # this will be "" for Anonymous
    except AttributeError:
        pass

    data.update(kw)

    # a 404 has some specific formatting of the error that
    # can be useful
    if status == 404:
        msg = ""
        for m in exc_info[1]:
            tried = "\n".join(m["tried"])
            msg = "Failed to find %s, tried: \n\t%s" % (m["path"], tried)
        data["msg"] = msg

    # if we don't get a priority, make create one
    if not data.get("priority"):
        if status == 500:
            data["priority"] = 1
        else:
            data["priority"] = 5

    try:
        if getattr(settings, "ARECIBO_TRANSPORT", None):
            try:
                sender = settings.ARECIBO_EMAIL_SENDER_ADDRESS
            except AttributeError:
                raise ValueError, "We must have a valid ARECIBO_EMAIL_SENDER_ADDRESS in the settings."

            mail.send_mail(
                sender=sender,
                to=settings.ARECIBO_SERVER_EMAIL,
                subject="Error",
                body=simplejson.dumps(data))
        else:
            udata = urlencode(data)
            headers = {'Content-Type': 'application/x-www-form-urlencoded', "Accept": "text/plain"}
            url = list(urlparse(settings.ARECIBO_SERVER_URL))
            if url[2] != "/v/1/": url[2] = "/v/1/"
            result = urlfetch.fetch(
                url=urlunparse(url),
                payload=udata,
                method=urlfetch.POST,
                headers=headers)

    except:
        raise
        # write to the standard google app engine log
        # http://code.google.com/appengine/docs/python/logging.html
        exctype, value = sys.exc_info()[:2]
        msg = "There was an error posting that error to Arecibo via smtp %s, %s" % (exctype, value)
        logging.error("Arecibo: %s", msg)

    return data["uid"]

########NEW FILE########
__FILENAME__ = arecibo_growl
# License: GPL
# Author: Andy McKay, Clearwind
#
# you will need growl for this, the binary and the source
# http://growl.info/source.php
# and then in Growl-1.2-src/Bindings/python run setup.py
# then this should work...
import Growl
import urllib

# requires 2.6
import json
import time
import os
from datetime import datetime

# the URL to your arecibo instance... remember you can use the query string to filter
url = "http://test-areciboapp.appspot.com/feed/sw3tqw35ywq45ws4kqa4ia6yw5q45serws23w351245lk6y/json/"
delay = 30

filename = os.path.expanduser("~/.arecibo-last")

class notifier(object):
    def __init__(self):
        self.gn = Growl.GrowlNotifier("arecibo", ["status",])
        self.gn.register()
        image_path = os.path.join(os.path.dirname(__file__), "apple-touch-icon.png")
        self.image = Growl.Image.imageFromPath(image_path)

    def load(self):
        if os.path.exists(filename):
            try:
                return self.convert(open(filename).read())
            except ValueError:
                pass
        return datetime.min

    def convert(self, string):
        return datetime.strptime(string, "%Y-%m-%d %H:%M:%S")

    def save(self, last_date):
        filehandle = open(filename, "w")
        filehandle.write(last_date.strftime("%Y-%m-%d %H:%M:%S"))
        filehandle.close()

    def get(self):
        unparsed = urllib.urlopen(url).read()
        parsed = json.loads(unparsed)
        highest = last_date = self.load()
        for error in parsed:
            dt = self.convert(error["fields"]["error_timestamp"][:19])
            if dt > last_date:
                self.gn.notify("status", "Arecibo error (priority %s)" % error["fields"]["priority"], "%s at %s\n%s" % (
                    error["fields"]["status"],
                    error["fields"]["domain"],
                    dt.strftime("%d %B, %H:%M")),
                    icon=self.image,
                    sticky=error["fields"]["priority"]==1)
            highest = max(highest, dt)
        self.save(highest)

if __name__=="__main__":
    anotifier = notifier()
    while True:
        anotifier.get()
        time.sleep(delay)

########NEW FILE########
__FILENAME__ = config
from zope.formlib import form
from Products.Five.formlib import formbase
from plone.app.controlpanel.form import ControlPanelForm
from clearwind.arecibo.interfaces import IAreciboConfiguration

from zope.i18nmessageid import MessageFactory
_ = MessageFactory('clearwind.arecibo')

class AreciboConfigurationForm(ControlPanelForm):
    form_fields = form.Fields(IAreciboConfiguration)

    description = _(u"Configure Plone to work with your Arecibo account here.")
    form_name = _(u"Arecibo settings")
    label = _(u"Arecibo settings")
########NEW FILE########
__FILENAME__ = config
from zope.interface import implements
from zope.schema.fieldproperty import FieldProperty
from zope.component import getUtility

from interfaces import IAreciboConfiguration

from OFS.SimpleItem import SimpleItem

class AreciboConfiguration(SimpleItem):
    implements(IAreciboConfiguration)
    account_number = FieldProperty(IAreciboConfiguration['account_number'])
    transport = FieldProperty(IAreciboConfiguration['transport'])

def form_adapter(context):
    return getUtility(IAreciboConfiguration, name='Arecibo_config', context=context)
########NEW FILE########
__FILENAME__ = Install
import transaction
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.DirectoryView import createDirectoryView
from clearwind.arecibo.interfaces import IAreciboConfiguration
from clearwind.arecibo.config import AreciboConfiguration

EXTENSION_PROFILES = ('clearwind.arecibo:default',)

def uninstall(self):
    """ Uninstall """
    cp = getToolByName(self, 'portal_controlpanel')
    if "arecibo" in [ c.id for c in cp._actions ]:
        cp.unregisterConfiglet("arecibo")


def install(self, reinstall=False):
    """ We still have to do this? """

    portal_quickinstaller = getToolByName(self, 'portal_quickinstaller')
    portal_setup = getToolByName(self, 'portal_setup')

    sm = self.getSiteManager()

    if not sm.queryUtility(IAreciboConfiguration,
        name='Arecibo_config'):
        sm.registerUtility(AreciboConfiguration(),
                           IAreciboConfiguration,
                           'Arecibo_config')

    for extension_id in EXTENSION_PROFILES:
        portal_setup.runAllImportStepsFromProfile('profile-%s' % extension_id, purge_old=False)
        product_name = extension_id.split(':')[0]
        portal_quickinstaller.notifyInstalled(product_name)
        transaction.savepoint()
########NEW FILE########
__FILENAME__ = interfaces
from zope.interface import Interface
from zope.schema import Choice
from zope.schema import TextLine
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

from zope.i18nmessageid import MessageFactory
_ = MessageFactory('clearwind.arecibo')

arecibo_choices = {
    _(u"Send via http"): "http",
    _(u"Send via email"): "smtp"
}
arecibo_choices_vocab = SimpleVocabulary(
    [SimpleTerm(v, v, k) for k, v in arecibo_choices.items()]
    )

class IAreciboConfiguration(Interface):
  """ This interface defines the configlet."""
  account_number = TextLine(title=_(u"Arecibo public account number"),
                                  required=True)
  transport = Choice(title=_(u'Transport'),
                description=_(u"""How errors will be sent to Arecibo, for mail
                to work, your mail host must be correctly configured."""),
                default='http',
                vocabulary=arecibo_choices_vocab,
                required=False)
########NEW FILE########
__FILENAME__ = arecibo
# -*- coding: utf-8 -*-
# Copyright ClearWind Consulting Ltd., 2008
# Under the BSD License, see LICENSE.TXT
from httplib import HTTPConnection
has_https = False
try:
    from httplib import HTTPSConnection
    has_https = True
except ImportError:
    pass

from urllib import urlencode
from urlparse import urlparse
from socket import gethostname, getdefaulttimeout, setdefaulttimeout
from email.Utils import formatdate

import smtplib
import simplejson

posturl = "http://www.areciboapp.com/v/1/"
postaddress = "arecibo@clearwind.ca"
url = urlparse(posturl)

keys = ["account", "ip", "priority", "uid",
    "type", "msg", "traceback", "user_agent",
    "url", "status", "server", "timestamp",
    "request", "username"]

required = [ "account", ]

class post:
    def __init__(self):
        self._data = {}
        self.transport = "http"
        self.smtp_server = "localhost"
        self.smtp_from = "noreply@clearwind.ca"
        self.set("server", gethostname())
        self.set("timestamp", formatdate())

    # public
    def set(self, key, value):
        """ Sets the variable named key, with the value """
        if key not in keys:
            raise ValueError, "Unknown value: %s" % key
        self._data[key] = value

    def send(self):
        """ Sends the data to the arecibo server """
        for x in required:
            assert self._data.get(x), "The key %s is required" % x

        self._send()

    # private
    def _data_encoded(self):
        data = {}
        for k in keys:
            if self._data.get(k):
                data[k] = self._data.get(k)
        return urlencode(data)

    def _send(self):
        key = self.transport.lower()
        assert key in ["http", "smtp", "https"]
        if key in ["http", "https"]:
            self._send_http()
        elif key == "smtp":
            self._send_smtp()

    def _msg_body(self):
        body = simplejson.dumps(self._data)
        msg = "From: %s\r\nTo: %s\r\n\r\n%s" % (self.smtp_from, postaddress, body)
        return msg

    def _send_smtp(self):
        msg = self._msg_body()
        s = smtplib.SMTP(self.smtp_server)
        s.sendmail(self.smtp_from, postaddress, msg)
        s.quit()

    def _send_http(self):
        if self.transport == "https" and has_https:
            h = HTTPSConnection(url[1])
        else:
            h = HTTPConnection(url[1])
        headers = {
            "Content-type": 'application/x-www-form-urlencoded; charset="utf-8"',
            "Accept": "text/plain"}
        data = self._data_encoded()
        oldtimeout = getdefaulttimeout()
        try:
            setdefaulttimeout(10)
            h.request("POST", url[2], data, headers)

            reply = h.getresponse()
            if reply.status != 200:
                raise ValueError, "%s (%s)" % (reply.read(), reply.status)
        finally:
            setdefaulttimeout(oldtimeout)

if __name__=='__main__':
    new = post()
    #new.transport = "https"
    new.set("account", "YOUR KEY HERE")
    new.set("priority", 4)
    new.set("user_agent", "Mozilla/5.0 (Macintosh; U; Intel Mac OS X...")
    new.set("url", "http://badapp.org/-\ufffdwe-cant-lose")
    new.set("uid", "123124123123")
    new.set("ip", "127.0.0.1")
    new.set("type", "Test from python")
    new.set("status", "403")
    new.set("server", "Test Script")
    new.set("request", """This is the bit that goes in the request""")
    new.set("username", "Jimbob")
    new.set("msg", """
Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut
labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris
nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit
esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in
culpa qui officia deserunt mollit anim id est laborum
""")
    new.set("traceback", """Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
ZeroDivisionError: integer division or modulo by zero  df
""")
    new.send()

########NEW FILE########
__FILENAME__ = decoder
"""
Implementation of JSONDecoder
"""
import re
import sys

try:
    from simplejson.scanner import Scanner, pattern
except ImportError:
    from scanner import Scanner, pattern
try:
    from simplejson._speedups import scanstring as c_scanstring
except ImportError:
    c_scanstring = None

FLAGS = re.VERBOSE | re.MULTILINE | re.DOTALL

def _floatconstants():
    import struct
    import sys
    _BYTES = '7FF80000000000007FF0000000000000'.decode('hex')
    if sys.byteorder != 'big':
        _BYTES = _BYTES[:8][::-1] + _BYTES[8:][::-1]
    nan, inf = struct.unpack('dd', _BYTES)
    return nan, inf, -inf

NaN, PosInf, NegInf = _floatconstants()


def linecol(doc, pos):
    lineno = doc.count('\n', 0, pos) + 1
    if lineno == 1:
        colno = pos
    else:
        colno = pos - doc.rindex('\n', 0, pos)
    return lineno, colno


def errmsg(msg, doc, pos, end=None):
    lineno, colno = linecol(doc, pos)
    if end is None:
        return '%s: line %d column %d (char %d)' % (msg, lineno, colno, pos)
    endlineno, endcolno = linecol(doc, end)
    return '%s: line %d column %d - line %d column %d (char %d - %d)' % (
        msg, lineno, colno, endlineno, endcolno, pos, end)


_CONSTANTS = {
    '-Infinity': NegInf,
    'Infinity': PosInf,
    'NaN': NaN,
    'true': True,
    'false': False,
    'null': None,
}

def JSONConstant(match, context, c=_CONSTANTS):
    s = match.group(0)
    fn = getattr(context, 'parse_constant', None)
    if fn is None:
        rval = c[s]
    else:
        rval = fn(s)
    return rval, None
pattern('(-?Infinity|NaN|true|false|null)')(JSONConstant)


def JSONNumber(match, context):
    match = JSONNumber.regex.match(match.string, *match.span())
    integer, frac, exp = match.groups()
    if frac or exp:
        fn = getattr(context, 'parse_float', None) or float
        res = fn(integer + (frac or '') + (exp or ''))
    else:
        fn = getattr(context, 'parse_int', None) or int
        res = fn(integer)
    return res, None
pattern(r'(-?(?:0|[1-9]\d*))(\.\d+)?([eE][-+]?\d+)?')(JSONNumber)


STRINGCHUNK = re.compile(r'(.*?)(["\\\x00-\x1f])', FLAGS)
BACKSLASH = {
    '"': u'"', '\\': u'\\', '/': u'/',
    'b': u'\b', 'f': u'\f', 'n': u'\n', 'r': u'\r', 't': u'\t',
}

DEFAULT_ENCODING = "utf-8"

def py_scanstring(s, end, encoding=None, strict=True, _b=BACKSLASH, _m=STRINGCHUNK.match):
    if encoding is None:
        encoding = DEFAULT_ENCODING
    chunks = []
    _append = chunks.append
    begin = end - 1
    while 1:
        chunk = _m(s, end)
        if chunk is None:
            raise ValueError(
                errmsg("Unterminated string starting at", s, begin))
        end = chunk.end()
        content, terminator = chunk.groups()
        if content:
            if not isinstance(content, unicode):
                content = unicode(content, encoding)
            _append(content)
        if terminator == '"':
            break
        elif terminator != '\\':
            if strict:
                raise ValueError(errmsg("Invalid control character %r at", s, end))
            else:
                _append(terminator)
                continue
        try:
            esc = s[end]
        except IndexError:
            raise ValueError(
                errmsg("Unterminated string starting at", s, begin))
        if esc != 'u':
            try:
                m = _b[esc]
            except KeyError:
                raise ValueError(
                    errmsg("Invalid \\escape: %r" % (esc,), s, end))
            end += 1
        else:
            esc = s[end + 1:end + 5]
            next_end = end + 5
            msg = "Invalid \\uXXXX escape"
            try:
                if len(esc) != 4:
                    raise ValueError
                uni = int(esc, 16)
                if 0xd800 <= uni <= 0xdbff and sys.maxunicode > 65535:
                    msg = "Invalid \\uXXXX\\uXXXX surrogate pair"
                    if not s[end + 5:end + 7] == '\\u':
                        raise ValueError
                    esc2 = s[end + 7:end + 11]
                    if len(esc2) != 4:
                        raise ValueError
                    uni2 = int(esc2, 16)
                    uni = 0x10000 + (((uni - 0xd800) << 10) | (uni2 - 0xdc00))
                    next_end += 6
                m = unichr(uni)
            except ValueError:
                raise ValueError(errmsg(msg, s, end))
            end = next_end
        _append(m)
    return u''.join(chunks), end


# Use speedup if available
scanstring = c_scanstring or py_scanstring

def JSONString(match, context):
    encoding = getattr(context, 'encoding', None)
    strict = getattr(context, 'strict', True)
    return scanstring(match.string, match.end(), encoding, strict)
pattern(r'"')(JSONString)


WHITESPACE = re.compile(r'\s*', FLAGS)

def JSONObject(match, context, _w=WHITESPACE.match):
    pairs = {}
    s = match.string
    end = _w(s, match.end()).end()
    nextchar = s[end:end + 1]
    # Trivial empty object
    if nextchar == '}':
        return pairs, end + 1
    if nextchar != '"':
        raise ValueError(errmsg("Expecting property name", s, end))
    end += 1
    encoding = getattr(context, 'encoding', None)
    strict = getattr(context, 'strict', True)
    iterscan = JSONScanner.iterscan
    while True:
        key, end = scanstring(s, end, encoding, strict)
        end = _w(s, end).end()
        if s[end:end + 1] != ':':
            raise ValueError(errmsg("Expecting : delimiter", s, end))
        end = _w(s, end + 1).end()
        try:
            value, end = iterscan(s, idx=end, context=context).next()
        except StopIteration:
            raise ValueError(errmsg("Expecting object", s, end))
        pairs[key] = value
        end = _w(s, end).end()
        nextchar = s[end:end + 1]
        end += 1
        if nextchar == '}':
            break
        if nextchar != ',':
            raise ValueError(errmsg("Expecting , delimiter", s, end - 1))
        end = _w(s, end).end()
        nextchar = s[end:end + 1]
        end += 1
        if nextchar != '"':
            raise ValueError(errmsg("Expecting property name", s, end - 1))
    object_hook = getattr(context, 'object_hook', None)
    if object_hook is not None:
        pairs = object_hook(pairs)
    return pairs, end
pattern(r'{')(JSONObject)


def JSONArray(match, context, _w=WHITESPACE.match):
    values = []
    s = match.string
    end = _w(s, match.end()).end()
    # Look-ahead for trivial empty array
    nextchar = s[end:end + 1]
    if nextchar == ']':
        return values, end + 1
    iterscan = JSONScanner.iterscan
    while True:
        try:
            value, end = iterscan(s, idx=end, context=context).next()
        except StopIteration:
            raise ValueError(errmsg("Expecting object", s, end))
        values.append(value)
        end = _w(s, end).end()
        nextchar = s[end:end + 1]
        end += 1
        if nextchar == ']':
            break
        if nextchar != ',':
            raise ValueError(errmsg("Expecting , delimiter", s, end))
        end = _w(s, end).end()
    return values, end
pattern(r'\[')(JSONArray)


ANYTHING = [
    JSONObject,
    JSONArray,
    JSONString,
    JSONConstant,
    JSONNumber,
]

JSONScanner = Scanner(ANYTHING)


class JSONDecoder(object):
    """
    Simple JSON <http://json.org> decoder

    Performs the following translations in decoding by default:

    +---------------+-------------------+
    | JSON          | Python            |
    +===============+===================+
    | object        | dict              |
    +---------------+-------------------+
    | array         | list              |
    +---------------+-------------------+
    | string        | unicode           |
    +---------------+-------------------+
    | number (int)  | int, long         |
    +---------------+-------------------+
    | number (real) | float             |
    +---------------+-------------------+
    | true          | True              |
    +---------------+-------------------+
    | false         | False             |
    +---------------+-------------------+
    | null          | None              |
    +---------------+-------------------+

    It also understands ``NaN``, ``Infinity``, and ``-Infinity`` as
    their corresponding ``float`` values, which is outside the JSON spec.
    """

    _scanner = Scanner(ANYTHING)
    __all__ = ['__init__', 'decode', 'raw_decode']

    def __init__(self, encoding=None, object_hook=None, parse_float=None,
            parse_int=None, parse_constant=None, strict=True):
        """
        ``encoding`` determines the encoding used to interpret any ``str``
        objects decoded by this instance (utf-8 by default).  It has no
        effect when decoding ``unicode`` objects.

        Note that currently only encodings that are a superset of ASCII work,
        strings of other encodings should be passed in as ``unicode``.

        ``object_hook``, if specified, will be called with the result
        of every JSON object decoded and its return value will be used in
        place of the given ``dict``.  This can be used to provide custom
        deserializations (e.g. to support JSON-RPC class hinting).

        ``parse_float``, if specified, will be called with the string
        of every JSON float to be decoded. By default this is equivalent to
        float(num_str). This can be used to use another datatype or parser
        for JSON floats (e.g. decimal.Decimal).

        ``parse_int``, if specified, will be called with the string
        of every JSON int to be decoded. By default this is equivalent to
        int(num_str). This can be used to use another datatype or parser
        for JSON integers (e.g. float).

        ``parse_constant``, if specified, will be called with one of the
        following strings: -Infinity, Infinity, NaN, null, true, false.
        This can be used to raise an exception if invalid JSON numbers
        are encountered.
        """
        self.encoding = encoding
        self.object_hook = object_hook
        self.parse_float = parse_float
        self.parse_int = parse_int
        self.parse_constant = parse_constant
        self.strict = strict

    def decode(self, s, _w=WHITESPACE.match):
        """
        Return the Python representation of ``s`` (a ``str`` or ``unicode``
        instance containing a JSON document)
        """
        obj, end = self.raw_decode(s, idx=_w(s, 0).end())
        end = _w(s, end).end()
        if end != len(s):
            raise ValueError(errmsg("Extra data", s, end, len(s)))
        return obj

    def raw_decode(self, s, **kw):
        """
        Decode a JSON document from ``s`` (a ``str`` or ``unicode`` beginning
        with a JSON document) and return a 2-tuple of the Python
        representation and the index in ``s`` where the document ended.

        This can be used to decode a JSON document from a string that may
        have extraneous data at the end.
        """
        kw.setdefault('context', self)
        try:
            obj, end = self._scanner.iterscan(s, **kw).next()
        except StopIteration:
            raise ValueError("No JSON object could be decoded")
        return obj, end

__all__ = ['JSONDecoder']

########NEW FILE########
__FILENAME__ = encoder
"""
Implementation of JSONEncoder
"""
import re

try:
    from simplejson._speedups import encode_basestring_ascii as c_encode_basestring_ascii
except ImportError:
    c_encode_basestring_ascii = None

ESCAPE = re.compile(r'[\x00-\x1f\\"\b\f\n\r\t]')
ESCAPE_ASCII = re.compile(r'([\\"]|[^\ -~])')
HAS_UTF8 = re.compile(r'[\x80-\xff]')
ESCAPE_DCT = {
    '\\': '\\\\',
    '"': '\\"',
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\\n',
    '\r': '\\r',
    '\t': '\\t',
}
for i in range(0x20):
    ESCAPE_DCT.setdefault(chr(i), '\\u%04x' % (i,))

# Assume this produces an infinity on all machines (probably not guaranteed)
INFINITY = float('1e66666')
FLOAT_REPR = repr

def floatstr(o, allow_nan=True):
    # Check for specials.  Note that this type of test is processor- and/or
    # platform-specific, so do tests which don't depend on the internals.

    if o != o:
        text = 'NaN'
    elif o == INFINITY:
        text = 'Infinity'
    elif o == -INFINITY:
        text = '-Infinity'
    else:
        return FLOAT_REPR(o)

    if not allow_nan:
        raise ValueError("Out of range float values are not JSON compliant: %r"
            % (o,))

    return text


def encode_basestring(s):
    """
    Return a JSON representation of a Python string
    """
    def replace(match):
        return ESCAPE_DCT[match.group(0)]
    return '"' + ESCAPE.sub(replace, s) + '"'


def py_encode_basestring_ascii(s):
    if isinstance(s, str) and HAS_UTF8.search(s) is not None:
        s = s.decode('utf-8')
    def replace(match):
        s = match.group(0)
        try:
            return ESCAPE_DCT[s]
        except KeyError:
            n = ord(s)
            if n < 0x10000:
                return '\\u%04x' % (n,)
            else:
                # surrogate pair
                n -= 0x10000
                s1 = 0xd800 | ((n >> 10) & 0x3ff)
                s2 = 0xdc00 | (n & 0x3ff)
                return '\\u%04x\\u%04x' % (s1, s2)
    return '"' + str(ESCAPE_ASCII.sub(replace, s)) + '"'


encode_basestring_ascii = c_encode_basestring_ascii or py_encode_basestring_ascii


class JSONEncoder(object):
    """
    Extensible JSON <http://json.org> encoder for Python data structures.

    Supports the following objects and types by default:

    +-------------------+---------------+
    | Python            | JSON          |
    +===================+===============+
    | dict              | object        |
    +-------------------+---------------+
    | list, tuple       | array         |
    +-------------------+---------------+
    | str, unicode      | string        |
    +-------------------+---------------+
    | int, long, float  | number        |
    +-------------------+---------------+
    | True              | true          |
    +-------------------+---------------+
    | False             | false         |
    +-------------------+---------------+
    | None              | null          |
    +-------------------+---------------+

    To extend this to recognize other objects, subclass and implement a
    ``.default()`` method with another method that returns a serializable
    object for ``o`` if possible, otherwise it should call the superclass
    implementation (to raise ``TypeError``).
    """
    __all__ = ['__init__', 'default', 'encode', 'iterencode']
    item_separator = ', '
    key_separator = ': '
    def __init__(self, skipkeys=False, ensure_ascii=True,
            check_circular=True, allow_nan=True, sort_keys=False,
            indent=None, separators=None, encoding='utf-8', default=None):
        """
        Constructor for JSONEncoder, with sensible defaults.

        If skipkeys is False, then it is a TypeError to attempt
        encoding of keys that are not str, int, long, float or None.  If
        skipkeys is True, such items are simply skipped.

        If ensure_ascii is True, the output is guaranteed to be str
        objects with all incoming unicode characters escaped.  If
        ensure_ascii is false, the output will be unicode object.

        If check_circular is True, then lists, dicts, and custom encoded
        objects will be checked for circular references during encoding to
        prevent an infinite recursion (which would cause an OverflowError).
        Otherwise, no such check takes place.

        If allow_nan is True, then NaN, Infinity, and -Infinity will be
        encoded as such.  This behavior is not JSON specification compliant,
        but is consistent with most JavaScript based encoders and decoders.
        Otherwise, it will be a ValueError to encode such floats.

        If sort_keys is True, then the output of dictionaries will be
        sorted by key; this is useful for regression tests to ensure
        that JSON serializations can be compared on a day-to-day basis.

        If indent is a non-negative integer, then JSON array
        elements and object members will be pretty-printed with that
        indent level.  An indent level of 0 will only insert newlines.
        None is the most compact representation.

        If specified, separators should be a (item_separator, key_separator)
        tuple.  The default is (', ', ': ').  To get the most compact JSON
        representation you should specify (',', ':') to eliminate whitespace.

        If specified, default is a function that gets called for objects
        that can't otherwise be serialized.  It should return a JSON encodable
        version of the object or raise a ``TypeError``.

        If encoding is not None, then all input strings will be
        transformed into unicode using that encoding prior to JSON-encoding.
        The default is UTF-8.
        """

        self.skipkeys = skipkeys
        self.ensure_ascii = ensure_ascii
        self.check_circular = check_circular
        self.allow_nan = allow_nan
        self.sort_keys = sort_keys
        self.indent = indent
        self.current_indent_level = 0
        if separators is not None:
            self.item_separator, self.key_separator = separators
        if default is not None:
            self.default = default
        self.encoding = encoding

    def _newline_indent(self):
        return '\n' + (' ' * (self.indent * self.current_indent_level))

    def _iterencode_list(self, lst, markers=None):
        if not lst:
            yield '[]'
            return
        if markers is not None:
            markerid = id(lst)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = lst
        yield '['
        if self.indent is not None:
            self.current_indent_level += 1
            newline_indent = self._newline_indent()
            separator = self.item_separator + newline_indent
            yield newline_indent
        else:
            newline_indent = None
            separator = self.item_separator
        first = True
        for value in lst:
            if first:
                first = False
            else:
                yield separator
            for chunk in self._iterencode(value, markers):
                yield chunk
        if newline_indent is not None:
            self.current_indent_level -= 1
            yield self._newline_indent()
        yield ']'
        if markers is not None:
            del markers[markerid]

    def _iterencode_dict(self, dct, markers=None):
        if not dct:
            yield '{}'
            return
        if markers is not None:
            markerid = id(dct)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = dct
        yield '{'
        key_separator = self.key_separator
        if self.indent is not None:
            self.current_indent_level += 1
            newline_indent = self._newline_indent()
            item_separator = self.item_separator + newline_indent
            yield newline_indent
        else:
            newline_indent = None
            item_separator = self.item_separator
        first = True
        if self.ensure_ascii:
            encoder = encode_basestring_ascii
        else:
            encoder = encode_basestring
        allow_nan = self.allow_nan
        if self.sort_keys:
            keys = dct.keys()
            keys.sort()
            items = [(k, dct[k]) for k in keys]
        else:
            items = dct.iteritems()
        _encoding = self.encoding
        _do_decode = (_encoding is not None
            and not (_encoding == 'utf-8'))
        for key, value in items:
            if isinstance(key, str):
                if _do_decode:
                    key = key.decode(_encoding)
            elif isinstance(key, basestring):
                pass
            # JavaScript is weakly typed for these, so it makes sense to
            # also allow them.  Many encoders seem to do something like this.
            elif isinstance(key, float):
                key = floatstr(key, allow_nan)
            elif isinstance(key, (int, long)):
                key = str(key)
            elif key is True:
                key = 'true'
            elif key is False:
                key = 'false'
            elif key is None:
                key = 'null'
            elif self.skipkeys:
                continue
            else:
                raise TypeError("key %r is not a string" % (key,))
            if first:
                first = False
            else:
                yield item_separator
            yield encoder(key)
            yield key_separator
            for chunk in self._iterencode(value, markers):
                yield chunk
        if newline_indent is not None:
            self.current_indent_level -= 1
            yield self._newline_indent()
        yield '}'
        if markers is not None:
            del markers[markerid]

    def _iterencode(self, o, markers=None):
        if isinstance(o, basestring):
            if self.ensure_ascii:
                encoder = encode_basestring_ascii
            else:
                encoder = encode_basestring
            _encoding = self.encoding
            if (_encoding is not None and isinstance(o, str)
                    and not (_encoding == 'utf-8')):
                o = o.decode(_encoding)
            yield encoder(o)
        elif o is None:
            yield 'null'
        elif o is True:
            yield 'true'
        elif o is False:
            yield 'false'
        elif isinstance(o, (int, long)):
            yield str(o)
        elif isinstance(o, float):
            yield floatstr(o, self.allow_nan)
        elif isinstance(o, (list, tuple)):
            for chunk in self._iterencode_list(o, markers):
                yield chunk
        elif isinstance(o, dict):
            for chunk in self._iterencode_dict(o, markers):
                yield chunk
        else:
            if markers is not None:
                markerid = id(o)
                if markerid in markers:
                    raise ValueError("Circular reference detected")
                markers[markerid] = o
            for chunk in self._iterencode_default(o, markers):
                yield chunk
            if markers is not None:
                del markers[markerid]

    def _iterencode_default(self, o, markers=None):
        newobj = self.default(o)
        return self._iterencode(newobj, markers)

    def default(self, o):
        """
        Implement this method in a subclass such that it returns
        a serializable object for ``o``, or calls the base implementation
        (to raise a ``TypeError``).

        For example, to support arbitrary iterators, you could
        implement default like this::

            def default(self, o):
                try:
                    iterable = iter(o)
                except TypeError:
                    pass
                else:
                    return list(iterable)
                return JSONEncoder.default(self, o)
        """
        raise TypeError("%r is not JSON serializable" % (o,))

    def encode(self, o):
        """
        Return a JSON string representation of a Python data structure.

        >>> JSONEncoder().encode({"foo": ["bar", "baz"]})
        '{"foo": ["bar", "baz"]}'
        """
        # This is for extremely simple cases and benchmarks.
        if isinstance(o, basestring):
            if isinstance(o, str):
                _encoding = self.encoding
                if (_encoding is not None
                        and not (_encoding == 'utf-8')):
                    o = o.decode(_encoding)
            if self.ensure_ascii:
                return encode_basestring_ascii(o)
            else:
                return encode_basestring(o)
        # This doesn't pass the iterator directly to ''.join() because the
        # exceptions aren't as detailed.  The list call should be roughly
        # equivalent to the PySequence_Fast that ''.join() would do.
        chunks = list(self.iterencode(o))
        return ''.join(chunks)

    def iterencode(self, o):
        """
        Encode the given object and yield each string
        representation as available.

        For example::

            for chunk in JSONEncoder().iterencode(bigobject):
                mysocket.write(chunk)
        """
        if self.check_circular:
            markers = {}
        else:
            markers = None
        return self._iterencode(o, markers)

__all__ = ['JSONEncoder']

########NEW FILE########
__FILENAME__ = scanner
"""
Iterator based sre token scanner
"""
import re
from re import VERBOSE, MULTILINE, DOTALL
import sre_parse
import sre_compile
import sre_constants
from sre_constants import BRANCH, SUBPATTERN

__all__ = ['Scanner', 'pattern']

FLAGS = (VERBOSE | MULTILINE | DOTALL)

class Scanner(object):
    def __init__(self, lexicon, flags=FLAGS):
        self.actions = [None]
        # Combine phrases into a compound pattern
        s = sre_parse.Pattern()
        s.flags = flags
        p = []
        for idx, token in enumerate(lexicon):
            phrase = token.pattern
            try:
                subpattern = sre_parse.SubPattern(s,
                    [(SUBPATTERN, (idx + 1, sre_parse.parse(phrase, flags)))])
            except sre_constants.error:
                raise
            p.append(subpattern)
            self.actions.append(token)

        s.groups = len(p) + 1 # NOTE(guido): Added to make SRE validation work
        p = sre_parse.SubPattern(s, [(BRANCH, (None, p))])
        self.scanner = sre_compile.compile(p)

    def iterscan(self, string, idx=0, context=None):
        """
        Yield match, end_idx for each match
        """
        match = self.scanner.scanner(string, idx).match
        actions = self.actions
        lastend = idx
        end = len(string)
        while True:
            m = match()
            if m is None:
                break
            matchbegin, matchend = m.span()
            if lastend == matchend:
                break
            action = actions[m.lastindex]
            if action is not None:
                rval, next_pos = action(m, context)
                if next_pos is not None and next_pos != matchend:
                    # "fast forward" the scanner
                    matchend = next_pos
                    match = self.scanner.scanner(string, matchend).match
                yield rval, matchend
            lastend = matchend


def pattern(pattern, flags=FLAGS):
    def decorator(fn):
        fn.pattern = pattern
        fn.regex = re.compile(pattern, flags)
        return fn
    return decorator
########NEW FILE########
__FILENAME__ = tool
r"""
Using simplejson from the shell to validate and
pretty-print::

    $ echo '{"json":"obj"}' | python -msimplejson
    {
        "json": "obj"
    }
    $ echo '{ 1.2:3.4}' | python -msimplejson
    Expecting property name: line 1 column 2 (char 2)

Note that the JSON produced by this module's default settings
is a subset of YAML, so it may be used as a serializer for that as well.
"""
import simplejson

#
# Pretty printer:
#     curl http://mochikit.com/examples/ajax_tables/domains.json | python -msimplejson.tool
#

def main():
    import sys
    if len(sys.argv) == 1:
        infile = sys.stdin
        outfile = sys.stdout
    elif len(sys.argv) == 2:
        infile = open(sys.argv[1], 'rb')
        outfile = sys.stdout
    elif len(sys.argv) == 3:
        infile = open(sys.argv[1], 'rb')
        outfile = open(sys.argv[2], 'wb')
    else:
        raise SystemExit("%s [infile [outfile]]" % (sys.argv[0],))
    try:
        obj = simplejson.load(infile)
    except ValueError, e:
        raise SystemExit(e)
    simplejson.dump(obj, outfile, sort_keys=True, indent=4)
    outfile.write('\n')


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = patch
from Products.SiteErrorLog import SiteErrorLog
from wrapper import arecibo
import traceback

old_raising = SiteErrorLog.SiteErrorLog.raising
def raising(self, *args, **kw):
    if self.aq_parent.meta_type == "Plone Site":
        err = str(getattr(args[0][0], '__name__', args[0][0]))
        tb = "\n".join(traceback.format_tb(args[0][2]))
        msg = args[0][1]
        arecibo(self, error_type=err, error_tb=tb, error_msg=msg)
    return old_raising(self, *args, **kw)

SiteErrorLog.SiteErrorLog.raising = raising

########NEW FILE########
__FILENAME__ = tests
import unittest

from zope.testing import doctestunit
from zope.component import testing
from Testing import ZopeTestCase as ztc

from Products.Five import zcml
from Products.Five import fiveconfigure
from Products.PloneTestCase import PloneTestCase as ptc
from Products.PloneTestCase.layer import PloneSite
ptc.setupPloneSite()

import clearwind.arecibo

class TestCase(ptc.PloneTestCase):
    class layer(PloneSite):
        @classmethod
        def setUp(cls):
            fiveconfigure.debug_mode = True
            zcml.load_config('configure.zcml',
                             clearwind.arecibo)
            fiveconfigure.debug_mode = False

        @classmethod
        def tearDown(cls):
            pass


def test_suite():
    return unittest.TestSuite([

        # Unit tests
        #doctestunit.DocFileSuite(
        #    'README.txt', package='clearwind.arecibo',
        #    setUp=testing.setUp, tearDown=testing.tearDown),

        #doctestunit.DocTestSuite(
        #    module='clearwind.arecibo.mymodule',
        #    setUp=testing.setUp, tearDown=testing.tearDown),


        # Integration tests that use PloneTestCase
        #ztc.ZopeDocFileSuite(
        #    'README.txt', package='clearwind.arecibo',
        #    test_class=TestCase),

        #ztc.FunctionalDocFileSuite(
        #    'browser.txt', package='clearwind.arecibo',
        #    test_class=TestCase),

        ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

########NEW FILE########
__FILENAME__ = wrapper
import sys
import os
from lib.arecibo import post, postaddress
from App.config import getConfiguration
from AccessControl import getSecurityManager
from ZODB.POSException import ConflictError
from clearwind.arecibo.interfaces import IAreciboConfiguration

from logging import getLogger
log = getLogger('Plone')

headers = ['HOME', 'HTTP_ACCEPT', 'HTTP_ACCEPT_ENCODING', \
         'HTTP_ACCEPT_LANGUAGE', 'HTTP_CONNECTION', 'HTTP_HOST', 'LANG', \
         'PATH_INFO', 'QUERY_STRING', 'REQUEST_METHOD', 'SCRIPT_NAME', \
         'SERVER_NAME', 'SERVER_PORT', 'SERVER_PROTOCOL', 'SERVER_SOFTWARE']

try:
    import site_configuration
    from site_configuration import config
    log.info("Arecibo configuration read from: %s" % os.path.abspath(site_configuration.__file__))
except:
    # please don't override this here, look in site_configuration.py for a chance to
    # overload this, details are there too
    config = {
        "account": "",
        "transport": "http",
        "priorities": {
            404: 5,
            403: 3,
            500: 1,
        },
        "default-priority": 3,
        "ignores": ["Redirect",]
    }

def get(context):
    # pull first from our default settings above
    # the from site_configuration
    # and finally from the Plone Control Panel
    cfg = config.copy()
    qu = context.getSiteManager().queryUtility(IAreciboConfiguration, name='Arecibo_config')
    if not qu:
        return cfg
    if qu.account_number:
        cfg["account"] = qu.account_number
    if qu.transport == "smtp":
        cfg["transport"] = "smtp"
    return cfg

def arecibo(context, **kw):
    cfg = get(context)
    if kw.get("error_type") in cfg["ignores"]:
        return

    if not cfg["account"]:
        msg = "There is no account number configured so that the error can be sent to Arecibo"
        log.error('Arecibo: %s', msg)
        return

    req = context.REQUEST
    error = post()

    mail_possible = not not context.MailHost.smtp_host
    if mail_possible and cfg["transport"] == "smtp":
        error.transport = "smtp"

    if kw.get("error_type") == 'NotFound':
        status = 404
    elif kw.get("error_type") == 'Unauthorized':
        status = 403
    else:
        status = 500

    priority = cfg["priorities"].get(status, cfg["default-priority"])

    error.set("account", cfg["account"])
    error.set("priority", priority)
    error.set("user_agent", req.get('HTTP_USER_AGENT', ""))

    if req.get("QUERY_STRING"):
        error.set("url", "%s?%s" % (req['ACTUAL_URL'], req['QUERY_STRING']))
    else:
        error.set("url", req['ACTUAL_URL'])

    if kw.get("error_log_id"):
        error.set("uid", kw.get("error_log_id"))

    error.set("ip", req.get("X_FORWARDED_FOR", req.get('REMOTE_ADDR', '')))
    error.set("type", kw.get("error_type"))
    error.set("status", status)
    error.set("request", "\n".join([ "%s: %s" % (k, req[k]) for k in headers if req.get(k)]))

    if status != 404:
        # lets face it the 404 tb is not useful
        error.set("traceback", kw.get("error_tb"))

    usr = getSecurityManager().getUser()
    error.set("username", "%s (%s)" % (usr.getId(), usr.getUserName()))
    error.set("msg", kw.get("error_msg"))

    if error.transport == "http":
        try:
            error.send()
        except ConflictError:
            raise
        except:
            exctype, value = sys.exc_info()[:2]
            msg = "There was an error posting that error to Arecibo via http %s, %s" % (exctype, value)
            log.error('Arecibo: %s', msg)
    elif error.transport == "smtp":
        # use the MailHost to send out which is configured by the site
        # administrator, and has more functionality than straight smtplib
        try:
            context.MailHost.send(error._msg_body())
        except ConflictError:
            raise
        except:
            exctype, value = sys.exc_info()[:2]
            msg = "There was an error posting that error to Arecibo via smtp %s, %s" % (exctype, value)
            log.error('Arecibo: %s', msg)

########NEW FILE########
__FILENAME__ = arecibo
# -*- coding: utf-8 -*-
# Copyright ClearWind Consulting Ltd., 2008
# Under the BSD License, see LICENSE.TXT
from httplib import HTTPConnection
has_https = False
try:
    from httplib import HTTPSConnection
    has_https = True
except ImportError:
    pass

from urllib import urlencode
from urlparse import urlparse
try:
    from socket import gethostname, getdefaulttimeout, setdefaulttimeout
except ImportError:
    # App Engine doesn't have these
    # so here are a some replacements
    def gethostname(): return "unknown"
    def getdefaulttimeout(): return 60
    def setdefaulttimeout(num): pass

from email.Utils import formatdate

import smtplib
import simplejson

keys = ["account", "count", "ip", "priority", "uid",
    "type", "msg", "traceback", "user_agent",
    "url", "status", "server", "timestamp",
    "request", "username"]

default_route = "/v/1/"

class post:
    def __init__(self):
        self._data = {}
        self.transport = "http"
        self.smtp_server = "localhost"
        self.smtp_from = "noreply@clearwind.ca"
        self.url = None
        self.smtp_to = None
        self.set("server", gethostname())
        self.set("timestamp", formatdate())

    # public
    def set(self, key, value):
        """ Sets the variable named key, with the value """
        if key not in keys:
            raise ValueError, "Unknown value: %s" % key
        self._data[key] = value

    def server(self, url=None, email=None):
        """ Sets the URL or address so we know where to post the error """
        if url: self.url = urlparse(url)
        if email: self.smtp_to = email

    def send(self):
        """ Sends the data to the arecibo server """
        self._send()

    def as_json(self):
        return simplejson.dumps(self._data)

    # private
    def _data_encoded(self):
        data = {}
        for k in keys:
            if self._data.get(k):
                data[k] = self._data.get(k)
        return urlencode(data)

    def _send(self):
        key = self.transport.lower()
        assert key in ["http", "smtp", "https"]
        if key in ["http", "https"]:
            assert self.url, "No URL is set to post the error to."
            self._send_http()
        elif key == "smtp":
            assert self.smtp_to, "No destination email is set to post the error to."
            self._send_smtp()

    def _msg_body(self):
        msg = "From: %s\r\nTo: %s\r\n\r\n%s" % (self.smtp_from, self.smtp_to, self.as_json())
        return msg

    def _send_smtp(self):
        msg = self._msg_body()
        s = smtplib.SMTP(self.smtp_server)
        s.sendmail(self.smtp_from, self.smtp_to, msg)
        s.quit()

    def _send_http(self):
        if self.transport == "https" and has_https:
            h = HTTPSConnection(self.url[1])
        else:
            h = HTTPConnection(self.url[1])
        headers = {
            "Content-type": 'application/x-www-form-urlencoded; charset="utf-8"',
            "Accept": "text/plain"}
        data = self._data_encoded()
        oldtimeout = getdefaulttimeout()
        try:
            setdefaulttimeout(10)
            h.request("POST", default_route, data, headers)

            reply = h.getresponse()
            if reply.status != 200:
                raise ValueError, "%s (%s)" % (reply.read(), reply.status)
        finally:
            setdefaulttimeout(oldtimeout)

if __name__=='__main__':
    new = post()
    #new.server(url="http://amckay-arecibo.khan.mozilla.org")
    new.server(url="http://arecibo1.dmz.sjc1.mozilla.com")
    #new.transport = "smtp"
    #new.smtp_server = "smtp.telus.net"
    #new.server(email="your server")
    new.set("account", "sldkfslefhsjefartuatrjahrglw4a3tw3uthka")#your_public_account_number_here")
    new.set("priority", 4)
    new.set("user_agent", "Mozilla/5.0 (Macintosh; U; Intel Mac OS X...")
    new.set("url", "http://badapp.org/-\ufffdwe-cant-lose")
    new.set("uid", "123124123123")
    new.set("ip", "127.0.0.1")
    new.set("type", "Test from python")
    new.set("status", "403")
    new.set("server", "Test Script")
    new.set("request", """This is the bit that goes in the request""")
    new.set("username", "Jimbob")
    new.set("msg", """
Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut
labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris
nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit
esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in
culpa qui officia deserunt mollit anim id est laborum
""")
    new.set("traceback", """Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
ZeroDivisionError: integer division or modulo by zero  df
""")
    new.send()

########NEW FILE########
__FILENAME__ = decoder
"""
Implementation of JSONDecoder
"""
import re
import sys

try:
    from simplejson.scanner import Scanner, pattern
except ImportError:
    from scanner import Scanner, pattern
try:
    from simplejson._speedups import scanstring as c_scanstring
except ImportError:
    c_scanstring = None

FLAGS = re.VERBOSE | re.MULTILINE | re.DOTALL

def _floatconstants():
    import struct
    import sys
    _BYTES = '7FF80000000000007FF0000000000000'.decode('hex')
    if sys.byteorder != 'big':
        _BYTES = _BYTES[:8][::-1] + _BYTES[8:][::-1]
    nan, inf = struct.unpack('dd', _BYTES)
    return nan, inf, -inf

NaN, PosInf, NegInf = _floatconstants()


def linecol(doc, pos):
    lineno = doc.count('\n', 0, pos) + 1
    if lineno == 1:
        colno = pos
    else:
        colno = pos - doc.rindex('\n', 0, pos)
    return lineno, colno


def errmsg(msg, doc, pos, end=None):
    lineno, colno = linecol(doc, pos)
    if end is None:
        return '%s: line %d column %d (char %d)' % (msg, lineno, colno, pos)
    endlineno, endcolno = linecol(doc, end)
    return '%s: line %d column %d - line %d column %d (char %d - %d)' % (
        msg, lineno, colno, endlineno, endcolno, pos, end)


_CONSTANTS = {
    '-Infinity': NegInf,
    'Infinity': PosInf,
    'NaN': NaN,
    'true': True,
    'false': False,
    'null': None,
}

def JSONConstant(match, context, c=_CONSTANTS):
    s = match.group(0)
    fn = getattr(context, 'parse_constant', None)
    if fn is None:
        rval = c[s]
    else:
        rval = fn(s)
    return rval, None
pattern('(-?Infinity|NaN|true|false|null)')(JSONConstant)


def JSONNumber(match, context):
    match = JSONNumber.regex.match(match.string, *match.span())
    integer, frac, exp = match.groups()
    if frac or exp:
        fn = getattr(context, 'parse_float', None) or float
        res = fn(integer + (frac or '') + (exp or ''))
    else:
        fn = getattr(context, 'parse_int', None) or int
        res = fn(integer)
    return res, None
pattern(r'(-?(?:0|[1-9]\d*))(\.\d+)?([eE][-+]?\d+)?')(JSONNumber)


STRINGCHUNK = re.compile(r'(.*?)(["\\\x00-\x1f])', FLAGS)
BACKSLASH = {
    '"': u'"', '\\': u'\\', '/': u'/',
    'b': u'\b', 'f': u'\f', 'n': u'\n', 'r': u'\r', 't': u'\t',
}

DEFAULT_ENCODING = "utf-8"

def py_scanstring(s, end, encoding=None, strict=True, _b=BACKSLASH, _m=STRINGCHUNK.match):
    if encoding is None:
        encoding = DEFAULT_ENCODING
    chunks = []
    _append = chunks.append
    begin = end - 1
    while 1:
        chunk = _m(s, end)
        if chunk is None:
            raise ValueError(
                errmsg("Unterminated string starting at", s, begin))
        end = chunk.end()
        content, terminator = chunk.groups()
        if content:
            if not isinstance(content, unicode):
                content = unicode(content, encoding)
            _append(content)
        if terminator == '"':
            break
        elif terminator != '\\':
            if strict:
                raise ValueError(errmsg("Invalid control character %r at", s, end))
            else:
                _append(terminator)
                continue
        try:
            esc = s[end]
        except IndexError:
            raise ValueError(
                errmsg("Unterminated string starting at", s, begin))
        if esc != 'u':
            try:
                m = _b[esc]
            except KeyError:
                raise ValueError(
                    errmsg("Invalid \\escape: %r" % (esc,), s, end))
            end += 1
        else:
            esc = s[end + 1:end + 5]
            next_end = end + 5
            msg = "Invalid \\uXXXX escape"
            try:
                if len(esc) != 4:
                    raise ValueError
                uni = int(esc, 16)
                if 0xd800 <= uni <= 0xdbff and sys.maxunicode > 65535:
                    msg = "Invalid \\uXXXX\\uXXXX surrogate pair"
                    if not s[end + 5:end + 7] == '\\u':
                        raise ValueError
                    esc2 = s[end + 7:end + 11]
                    if len(esc2) != 4:
                        raise ValueError
                    uni2 = int(esc2, 16)
                    uni = 0x10000 + (((uni - 0xd800) << 10) | (uni2 - 0xdc00))
                    next_end += 6
                m = unichr(uni)
            except ValueError:
                raise ValueError(errmsg(msg, s, end))
            end = next_end
        _append(m)
    return u''.join(chunks), end


# Use speedup if available
scanstring = c_scanstring or py_scanstring

def JSONString(match, context):
    encoding = getattr(context, 'encoding', None)
    strict = getattr(context, 'strict', True)
    return scanstring(match.string, match.end(), encoding, strict)
pattern(r'"')(JSONString)


WHITESPACE = re.compile(r'\s*', FLAGS)

def JSONObject(match, context, _w=WHITESPACE.match):
    pairs = {}
    s = match.string
    end = _w(s, match.end()).end()
    nextchar = s[end:end + 1]
    # Trivial empty object
    if nextchar == '}':
        return pairs, end + 1
    if nextchar != '"':
        raise ValueError(errmsg("Expecting property name", s, end))
    end += 1
    encoding = getattr(context, 'encoding', None)
    strict = getattr(context, 'strict', True)
    iterscan = JSONScanner.iterscan
    while True:
        key, end = scanstring(s, end, encoding, strict)
        end = _w(s, end).end()
        if s[end:end + 1] != ':':
            raise ValueError(errmsg("Expecting : delimiter", s, end))
        end = _w(s, end + 1).end()
        try:
            value, end = iterscan(s, idx=end, context=context).next()
        except StopIteration:
            raise ValueError(errmsg("Expecting object", s, end))
        pairs[key] = value
        end = _w(s, end).end()
        nextchar = s[end:end + 1]
        end += 1
        if nextchar == '}':
            break
        if nextchar != ',':
            raise ValueError(errmsg("Expecting , delimiter", s, end - 1))
        end = _w(s, end).end()
        nextchar = s[end:end + 1]
        end += 1
        if nextchar != '"':
            raise ValueError(errmsg("Expecting property name", s, end - 1))
    object_hook = getattr(context, 'object_hook', None)
    if object_hook is not None:
        pairs = object_hook(pairs)
    return pairs, end
pattern(r'{')(JSONObject)


def JSONArray(match, context, _w=WHITESPACE.match):
    values = []
    s = match.string
    end = _w(s, match.end()).end()
    # Look-ahead for trivial empty array
    nextchar = s[end:end + 1]
    if nextchar == ']':
        return values, end + 1
    iterscan = JSONScanner.iterscan
    while True:
        try:
            value, end = iterscan(s, idx=end, context=context).next()
        except StopIteration:
            raise ValueError(errmsg("Expecting object", s, end))
        values.append(value)
        end = _w(s, end).end()
        nextchar = s[end:end + 1]
        end += 1
        if nextchar == ']':
            break
        if nextchar != ',':
            raise ValueError(errmsg("Expecting , delimiter", s, end))
        end = _w(s, end).end()
    return values, end
pattern(r'\[')(JSONArray)


ANYTHING = [
    JSONObject,
    JSONArray,
    JSONString,
    JSONConstant,
    JSONNumber,
]

JSONScanner = Scanner(ANYTHING)


class JSONDecoder(object):
    """
    Simple JSON <http://json.org> decoder

    Performs the following translations in decoding by default:

    +---------------+-------------------+
    | JSON          | Python            |
    +===============+===================+
    | object        | dict              |
    +---------------+-------------------+
    | array         | list              |
    +---------------+-------------------+
    | string        | unicode           |
    +---------------+-------------------+
    | number (int)  | int, long         |
    +---------------+-------------------+
    | number (real) | float             |
    +---------------+-------------------+
    | true          | True              |
    +---------------+-------------------+
    | false         | False             |
    +---------------+-------------------+
    | null          | None              |
    +---------------+-------------------+

    It also understands ``NaN``, ``Infinity``, and ``-Infinity`` as
    their corresponding ``float`` values, which is outside the JSON spec.
    """

    _scanner = Scanner(ANYTHING)
    __all__ = ['__init__', 'decode', 'raw_decode']

    def __init__(self, encoding=None, object_hook=None, parse_float=None,
            parse_int=None, parse_constant=None, strict=True):
        """
        ``encoding`` determines the encoding used to interpret any ``str``
        objects decoded by this instance (utf-8 by default).  It has no
        effect when decoding ``unicode`` objects.

        Note that currently only encodings that are a superset of ASCII work,
        strings of other encodings should be passed in as ``unicode``.

        ``object_hook``, if specified, will be called with the result
        of every JSON object decoded and its return value will be used in
        place of the given ``dict``.  This can be used to provide custom
        deserializations (e.g. to support JSON-RPC class hinting).

        ``parse_float``, if specified, will be called with the string
        of every JSON float to be decoded. By default this is equivalent to
        float(num_str). This can be used to use another datatype or parser
        for JSON floats (e.g. decimal.Decimal).

        ``parse_int``, if specified, will be called with the string
        of every JSON int to be decoded. By default this is equivalent to
        int(num_str). This can be used to use another datatype or parser
        for JSON integers (e.g. float).

        ``parse_constant``, if specified, will be called with one of the
        following strings: -Infinity, Infinity, NaN, null, true, false.
        This can be used to raise an exception if invalid JSON numbers
        are encountered.
        """
        self.encoding = encoding
        self.object_hook = object_hook
        self.parse_float = parse_float
        self.parse_int = parse_int
        self.parse_constant = parse_constant
        self.strict = strict

    def decode(self, s, _w=WHITESPACE.match):
        """
        Return the Python representation of ``s`` (a ``str`` or ``unicode``
        instance containing a JSON document)
        """
        obj, end = self.raw_decode(s, idx=_w(s, 0).end())
        end = _w(s, end).end()
        if end != len(s):
            raise ValueError(errmsg("Extra data", s, end, len(s)))
        return obj

    def raw_decode(self, s, **kw):
        """
        Decode a JSON document from ``s`` (a ``str`` or ``unicode`` beginning
        with a JSON document) and return a 2-tuple of the Python
        representation and the index in ``s`` where the document ended.

        This can be used to decode a JSON document from a string that may
        have extraneous data at the end.
        """
        kw.setdefault('context', self)
        try:
            obj, end = self._scanner.iterscan(s, **kw).next()
        except StopIteration:
            raise ValueError("No JSON object could be decoded")
        return obj, end

__all__ = ['JSONDecoder']

########NEW FILE########
__FILENAME__ = encoder
"""
Implementation of JSONEncoder
"""
import re

try:
    from simplejson._speedups import encode_basestring_ascii as c_encode_basestring_ascii
except ImportError:
    c_encode_basestring_ascii = None

ESCAPE = re.compile(r'[\x00-\x1f\\"\b\f\n\r\t]')
ESCAPE_ASCII = re.compile(r'([\\"]|[^\ -~])')
HAS_UTF8 = re.compile(r'[\x80-\xff]')
ESCAPE_DCT = {
    '\\': '\\\\',
    '"': '\\"',
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\\n',
    '\r': '\\r',
    '\t': '\\t',
}
for i in range(0x20):
    ESCAPE_DCT.setdefault(chr(i), '\\u%04x' % (i,))

# Assume this produces an infinity on all machines (probably not guaranteed)
INFINITY = float('1e66666')
FLOAT_REPR = repr

def floatstr(o, allow_nan=True):
    # Check for specials.  Note that this type of test is processor- and/or
    # platform-specific, so do tests which don't depend on the internals.

    if o != o:
        text = 'NaN'
    elif o == INFINITY:
        text = 'Infinity'
    elif o == -INFINITY:
        text = '-Infinity'
    else:
        return FLOAT_REPR(o)

    if not allow_nan:
        raise ValueError("Out of range float values are not JSON compliant: %r"
            % (o,))

    return text


def encode_basestring(s):
    """
    Return a JSON representation of a Python string
    """
    def replace(match):
        return ESCAPE_DCT[match.group(0)]
    return '"' + ESCAPE.sub(replace, s) + '"'


def py_encode_basestring_ascii(s):
    if isinstance(s, str) and HAS_UTF8.search(s) is not None:
        s = s.decode('utf-8')
    def replace(match):
        s = match.group(0)
        try:
            return ESCAPE_DCT[s]
        except KeyError:
            n = ord(s)
            if n < 0x10000:
                return '\\u%04x' % (n,)
            else:
                # surrogate pair
                n -= 0x10000
                s1 = 0xd800 | ((n >> 10) & 0x3ff)
                s2 = 0xdc00 | (n & 0x3ff)
                return '\\u%04x\\u%04x' % (s1, s2)
    return '"' + str(ESCAPE_ASCII.sub(replace, s)) + '"'


encode_basestring_ascii = c_encode_basestring_ascii or py_encode_basestring_ascii


class JSONEncoder(object):
    """
    Extensible JSON <http://json.org> encoder for Python data structures.

    Supports the following objects and types by default:

    +-------------------+---------------+
    | Python            | JSON          |
    +===================+===============+
    | dict              | object        |
    +-------------------+---------------+
    | list, tuple       | array         |
    +-------------------+---------------+
    | str, unicode      | string        |
    +-------------------+---------------+
    | int, long, float  | number        |
    +-------------------+---------------+
    | True              | true          |
    +-------------------+---------------+
    | False             | false         |
    +-------------------+---------------+
    | None              | null          |
    +-------------------+---------------+

    To extend this to recognize other objects, subclass and implement a
    ``.default()`` method with another method that returns a serializable
    object for ``o`` if possible, otherwise it should call the superclass
    implementation (to raise ``TypeError``).
    """
    __all__ = ['__init__', 'default', 'encode', 'iterencode']
    item_separator = ', '
    key_separator = ': '
    def __init__(self, skipkeys=False, ensure_ascii=True,
            check_circular=True, allow_nan=True, sort_keys=False,
            indent=None, separators=None, encoding='utf-8', default=None):
        """
        Constructor for JSONEncoder, with sensible defaults.

        If skipkeys is False, then it is a TypeError to attempt
        encoding of keys that are not str, int, long, float or None.  If
        skipkeys is True, such items are simply skipped.

        If ensure_ascii is True, the output is guaranteed to be str
        objects with all incoming unicode characters escaped.  If
        ensure_ascii is false, the output will be unicode object.

        If check_circular is True, then lists, dicts, and custom encoded
        objects will be checked for circular references during encoding to
        prevent an infinite recursion (which would cause an OverflowError).
        Otherwise, no such check takes place.

        If allow_nan is True, then NaN, Infinity, and -Infinity will be
        encoded as such.  This behavior is not JSON specification compliant,
        but is consistent with most JavaScript based encoders and decoders.
        Otherwise, it will be a ValueError to encode such floats.

        If sort_keys is True, then the output of dictionaries will be
        sorted by key; this is useful for regression tests to ensure
        that JSON serializations can be compared on a day-to-day basis.

        If indent is a non-negative integer, then JSON array
        elements and object members will be pretty-printed with that
        indent level.  An indent level of 0 will only insert newlines.
        None is the most compact representation.

        If specified, separators should be a (item_separator, key_separator)
        tuple.  The default is (', ', ': ').  To get the most compact JSON
        representation you should specify (',', ':') to eliminate whitespace.

        If specified, default is a function that gets called for objects
        that can't otherwise be serialized.  It should return a JSON encodable
        version of the object or raise a ``TypeError``.

        If encoding is not None, then all input strings will be
        transformed into unicode using that encoding prior to JSON-encoding.
        The default is UTF-8.
        """

        self.skipkeys = skipkeys
        self.ensure_ascii = ensure_ascii
        self.check_circular = check_circular
        self.allow_nan = allow_nan
        self.sort_keys = sort_keys
        self.indent = indent
        self.current_indent_level = 0
        if separators is not None:
            self.item_separator, self.key_separator = separators
        if default is not None:
            self.default = default
        self.encoding = encoding

    def _newline_indent(self):
        return '\n' + (' ' * (self.indent * self.current_indent_level))

    def _iterencode_list(self, lst, markers=None):
        if not lst:
            yield '[]'
            return
        if markers is not None:
            markerid = id(lst)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = lst
        yield '['
        if self.indent is not None:
            self.current_indent_level += 1
            newline_indent = self._newline_indent()
            separator = self.item_separator + newline_indent
            yield newline_indent
        else:
            newline_indent = None
            separator = self.item_separator
        first = True
        for value in lst:
            if first:
                first = False
            else:
                yield separator
            for chunk in self._iterencode(value, markers):
                yield chunk
        if newline_indent is not None:
            self.current_indent_level -= 1
            yield self._newline_indent()
        yield ']'
        if markers is not None:
            del markers[markerid]

    def _iterencode_dict(self, dct, markers=None):
        if not dct:
            yield '{}'
            return
        if markers is not None:
            markerid = id(dct)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = dct
        yield '{'
        key_separator = self.key_separator
        if self.indent is not None:
            self.current_indent_level += 1
            newline_indent = self._newline_indent()
            item_separator = self.item_separator + newline_indent
            yield newline_indent
        else:
            newline_indent = None
            item_separator = self.item_separator
        first = True
        if self.ensure_ascii:
            encoder = encode_basestring_ascii
        else:
            encoder = encode_basestring
        allow_nan = self.allow_nan
        if self.sort_keys:
            keys = dct.keys()
            keys.sort()
            items = [(k, dct[k]) for k in keys]
        else:
            items = dct.iteritems()
        _encoding = self.encoding
        _do_decode = (_encoding is not None
            and not (_encoding == 'utf-8'))
        for key, value in items:
            if isinstance(key, str):
                if _do_decode:
                    key = key.decode(_encoding)
            elif isinstance(key, basestring):
                pass
            # JavaScript is weakly typed for these, so it makes sense to
            # also allow them.  Many encoders seem to do something like this.
            elif isinstance(key, float):
                key = floatstr(key, allow_nan)
            elif isinstance(key, (int, long)):
                key = str(key)
            elif key is True:
                key = 'true'
            elif key is False:
                key = 'false'
            elif key is None:
                key = 'null'
            elif self.skipkeys:
                continue
            else:
                raise TypeError("key %r is not a string" % (key,))
            if first:
                first = False
            else:
                yield item_separator
            yield encoder(key)
            yield key_separator
            for chunk in self._iterencode(value, markers):
                yield chunk
        if newline_indent is not None:
            self.current_indent_level -= 1
            yield self._newline_indent()
        yield '}'
        if markers is not None:
            del markers[markerid]

    def _iterencode(self, o, markers=None):
        if isinstance(o, basestring):
            if self.ensure_ascii:
                encoder = encode_basestring_ascii
            else:
                encoder = encode_basestring
            _encoding = self.encoding
            if (_encoding is not None and isinstance(o, str)
                    and not (_encoding == 'utf-8')):
                o = o.decode(_encoding)
            yield encoder(o)
        elif o is None:
            yield 'null'
        elif o is True:
            yield 'true'
        elif o is False:
            yield 'false'
        elif isinstance(o, (int, long)):
            yield str(o)
        elif isinstance(o, float):
            yield floatstr(o, self.allow_nan)
        elif isinstance(o, (list, tuple)):
            for chunk in self._iterencode_list(o, markers):
                yield chunk
        elif isinstance(o, dict):
            for chunk in self._iterencode_dict(o, markers):
                yield chunk
        else:
            if markers is not None:
                markerid = id(o)
                if markerid in markers:
                    raise ValueError("Circular reference detected")
                markers[markerid] = o
            for chunk in self._iterencode_default(o, markers):
                yield chunk
            if markers is not None:
                del markers[markerid]

    def _iterencode_default(self, o, markers=None):
        newobj = self.default(o)
        return self._iterencode(newobj, markers)

    def default(self, o):
        """
        Implement this method in a subclass such that it returns
        a serializable object for ``o``, or calls the base implementation
        (to raise a ``TypeError``).

        For example, to support arbitrary iterators, you could
        implement default like this::

            def default(self, o):
                try:
                    iterable = iter(o)
                except TypeError:
                    pass
                else:
                    return list(iterable)
                return JSONEncoder.default(self, o)
        """
        raise TypeError("%r is not JSON serializable" % (o,))

    def encode(self, o):
        """
        Return a JSON string representation of a Python data structure.

        >>> JSONEncoder().encode({"foo": ["bar", "baz"]})
        '{"foo": ["bar", "baz"]}'
        """
        # This is for extremely simple cases and benchmarks.
        if isinstance(o, basestring):
            if isinstance(o, str):
                _encoding = self.encoding
                if (_encoding is not None
                        and not (_encoding == 'utf-8')):
                    o = o.decode(_encoding)
            if self.ensure_ascii:
                return encode_basestring_ascii(o)
            else:
                return encode_basestring(o)
        # This doesn't pass the iterator directly to ''.join() because the
        # exceptions aren't as detailed.  The list call should be roughly
        # equivalent to the PySequence_Fast that ''.join() would do.
        chunks = list(self.iterencode(o))
        return ''.join(chunks)

    def iterencode(self, o):
        """
        Encode the given object and yield each string
        representation as available.

        For example::

            for chunk in JSONEncoder().iterencode(bigobject):
                mysocket.write(chunk)
        """
        if self.check_circular:
            markers = {}
        else:
            markers = None
        return self._iterencode(o, markers)

__all__ = ['JSONEncoder']

########NEW FILE########
__FILENAME__ = scanner
"""
Iterator based sre token scanner
"""
import re
from re import VERBOSE, MULTILINE, DOTALL
import sre_parse
import sre_compile
import sre_constants
from sre_constants import BRANCH, SUBPATTERN

__all__ = ['Scanner', 'pattern']

FLAGS = (VERBOSE | MULTILINE | DOTALL)

class Scanner(object):
    def __init__(self, lexicon, flags=FLAGS):
        self.actions = [None]
        # Combine phrases into a compound pattern
        s = sre_parse.Pattern()
        s.flags = flags
        p = []
        for idx, token in enumerate(lexicon):
            phrase = token.pattern
            try:
                subpattern = sre_parse.SubPattern(s,
                    [(SUBPATTERN, (idx + 1, sre_parse.parse(phrase, flags)))])
            except sre_constants.error:
                raise
            p.append(subpattern)
            self.actions.append(token)

        s.groups = len(p) + 1 # NOTE(guido): Added to make SRE validation work
        p = sre_parse.SubPattern(s, [(BRANCH, (None, p))])
        self.scanner = sre_compile.compile(p)

    def iterscan(self, string, idx=0, context=None):
        """
        Yield match, end_idx for each match
        """
        match = self.scanner.scanner(string, idx).match
        actions = self.actions
        lastend = idx
        end = len(string)
        while True:
            m = match()
            if m is None:
                break
            matchbegin, matchend = m.span()
            if lastend == matchend:
                break
            action = actions[m.lastindex]
            if action is not None:
                rval, next_pos = action(m, context)
                if next_pos is not None and next_pos != matchend:
                    # "fast forward" the scanner
                    matchend = next_pos
                    match = self.scanner.scanner(string, matchend).match
                yield rval, matchend
            lastend = matchend


def pattern(pattern, flags=FLAGS):
    def decorator(fn):
        fn.pattern = pattern
        fn.regex = re.compile(pattern, flags)
        return fn
    return decorator
########NEW FILE########
__FILENAME__ = tool
r"""
Using simplejson from the shell to validate and
pretty-print::

    $ echo '{"json":"obj"}' | python -msimplejson
    {
        "json": "obj"
    }
    $ echo '{ 1.2:3.4}' | python -msimplejson
    Expecting property name: line 1 column 2 (char 2)

Note that the JSON produced by this module's default settings
is a subset of YAML, so it may be used as a serializer for that as well.
"""
import simplejson

#
# Pretty printer:
#     curl http://mochikit.com/examples/ajax_tables/domains.json | python -msimplejson.tool
#

def main():
    import sys
    if len(sys.argv) == 1:
        infile = sys.stdin
        outfile = sys.stdout
    elif len(sys.argv) == 2:
        infile = open(sys.argv[1], 'rb')
        outfile = sys.stdout
    elif len(sys.argv) == 3:
        infile = open(sys.argv[1], 'rb')
        outfile = open(sys.argv[2], 'wb')
    else:
        raise SystemExit("%s [infile [outfile]]" % (sys.argv[0],))
    try:
        obj = simplejson.load(infile)
    except ValueError, e:
        raise SystemExit(e)
    simplejson.dump(obj, outfile, sort_keys=True, indent=4)
    outfile.write('\n')


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = configure
import re
import sys
import os
import random
import hashlib
import time
import string
import shutil
import urllib
import tarfile

def key(phrase, type):
    m = hashlib.md5()
    m.update(str(time.time()))
    m.update(phrase)
    m.update(type)
    m.update("".join(random.sample(string.lowercase, 3)))
    return m.hexdigest()

def create():
    print "Configure Arecibo instance."
    directory = os.path.join(os.path.realpath(os.curdir), "listener", "app_engine") 
    
    print "Name of remote app engine instance: "
    name = sys.stdin.readline().strip()
    if not name:
        print "Error: app engine instance name required"
        sys.exit(1)
        
    print "Gmail account used to manage app engine instance: "
    email = sys.stdin.readline().strip()

    print "Key passphrase (type in a few chars): "
    phrase = sys.stdin.readline().strip()
    private = key(phrase, "private")
    public = key(phrase, "public")
    
    print "Creating app.yaml... "
    src = os.path.join(directory, "app.yaml.example")
    dest = src[:-8]
    shutil.copy(src, dest)
    data = open(dest, "rb").read()
    data = data.replace("application: your_application_error", "application: %s" % name)
    outfile = open(dest, "wb")
    outfile.write(data)
    outfile.close()
    print "... set application id."
    
    print "Creating local_settings.py... "
    src = os.path.join(directory, "local_settings.py.example")
    dest = src[:-8]
    shutil.copy(src, dest)
    data = open(dest, "rb").read()
    data = data.replace('your_public_account_number_here', public)
    data = data.replace('your_private_account_number_here', private)
    data = data.replace('theurl.to.your.arecibo.instance.com', '%s.appspot.com' % name)
    data = data.replace('you.account@gmail.com.that.is.authorized.for.app_engine', email)
    print "... set public, private keys."
    print "... set url and email."
    outfile = open(dest, "wb")
    outfile.write(data)
    outfile.close()

    django = "http://www.djangoproject.com/download/1.2.3/tarball/"
    print "Attempting to download django from:"
    print "... %s" % django
    try:
        filename, response = urllib.urlretrieve(django)
    except IOError:
        print "... download failed."
        print "Please download django and continue install as per:"
        print "http://areciboapp.com/docs/server/installation.html"
        return    
    
    print "Extracting django..."
    tar = tarfile.open(filename)
    tar.extractall(directory)
    tar.close()

    print "Copying over to Arecibo"
    shutil.copytree(os.path.join(directory, "Django-1.2.3", "django"), 
                    os.path.join(directory, "django"))
    shutil.rmtree(os.path.join(directory, "Django-1.2.3"))
    print "...complete."
    print "Arecibo local installation at: %s" % directory

if __name__=='__main__':
    create()

########NEW FILE########
__FILENAME__ = base
from appengine_django.models import BaseModel
from google.appengine.ext import db

class Base(BaseModel):
    @property
    def id(self):
        try:
            return str(self.key())
        except db.NotSavedError:
            pass
        
    pk = id

########NEW FILE########
__FILENAME__ = context
from urllib import urlencode
from django.conf import settings

def context(request):
    data = {}
    data["user"] = request.user
    data["public_key"] = settings.ARECIBO_PUBLIC_ACCOUNT_NUMBER
    data["private_key"] = settings.ARECIBO_PRIVATE_ACCOUNT_NUMBER
    data["site_url"] = settings.SITE_URL

    qs = request.GET.copy()
    if "page" in qs:
        del qs["page"]

    data["qs"] = ""
    if qs:
        data["qs"] = "%s" % urlencode(qs)

    return data

########NEW FILE########
__FILENAME__ = errors
from exceptions import Exception

class StatusDoesNotExist(Exception): pass

from django.template import RequestContext, loader
from django.http import HttpResponse

def not_found_error(request):
    t = loader.get_template('404.html')
    c = RequestContext(request)
    return HttpResponse(t.render(c), status=404)

def application_error(request):
    t = loader.get_template('500.html')
    c = RequestContext(request)
    return HttpResponse(t.render(c), status=500)
########NEW FILE########
__FILENAME__ = fields
from django import forms
from django.core.validators import EMPTY_VALUES

class OurModelChoiceIterator(forms.models.ModelChoiceIterator):
    def __iter__(self):
        if self.field.empty_label is not None:
            yield (u"", self.field.empty_label)
        if self.field.cache_choices:
            if self.field.choice_cache is None:
                self.field.choice_cache = [
                    self.choice(obj) for obj in self.queryset
                ]
            for choice in self.field.choice_cache:
                yield choice
        else:
            for obj in self.queryset:
                yield self.choice(obj)

class OurModelChoiceField(forms.ModelChoiceField):
    """ This required a few modifications to get working on app engine it seems """

    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop("model")
        super(OurModelChoiceField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if value in EMPTY_VALUES:
            return None
        value = self.model.get(value)
        return value

    def _get_choices(self):
        if hasattr(self, '_choices'):
            return self._choices
        return OurModelChoiceIterator(self)

    choices = property(_get_choices, forms.ModelChoiceField._set_choices)
########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.html import conditional_escape
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe

def as_blue_print(self):
    return self._html_output(u"""
    <div class="span-8 clear">
        <div %(html_class_attr)s>
            %(label)s<br />
            %(errors)s
            <span class="help">%(help_text)s</span>
            %(field)s
        </div>
    </div>
    """, u'%s', '', u'%s', False)

class Form(forms.Form):
    required_css_class = 'required'

    def as_custom(self):
        return as_blue_print(self)

class ModelForm(forms.ModelForm):
    required_css_class = 'required'

    def as_custom(self):
        return as_blue_print(self)

def as_div(self):
    if not self:
        return u''
    template = "%s"
    errors = ''.join([u'<p class="field-error">%s</p>' % conditional_escape(force_unicode(e)) for e in self])
    template = template % errors
    return mark_safe(template)

forms.util.ErrorList.__unicode__ = as_div

########NEW FILE########
__FILENAME__ = remote
from django.core.management.base import BaseCommand, CommandError

import code
import getpass
import sys
import os

from google.appengine.ext.remote_api import remote_api_stub
from google.appengine.ext import db

def auth_func():
    return raw_input('Username:'), getpass.getpass('Password:')

class Command(BaseCommand):
    help = 'Command shell for the remote App Engine instance'

    def handle(self, *args, **options):
        app_id = os.environ.get("APPLICATION_ID")
        host = "%s.appspot.com" % app_id
        remote_api_stub.ConfigureRemoteDatastore(app_id, '/remote_api', auth_func, host)
        code.interact('App Engine interactive console for %s' % (app_id,), None, locals())
########NEW FILE########
__FILENAME__ = paginator
from django.core.paginator import Paginator as BasePaginator
from django.core.paginator import Page, InvalidPage, EmptyPage

class GAEPaginator(BasePaginator):
    def page(self, number):
        "Returns a Page object for the given 1-based page number."
        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page
        queryset = self.object_list.fetch((number * self.per_page)+1)
        results = queryset[bottom:top]
        try:
            queryset[top]
            self._num_pages = number + 1
        except IndexError:
            self._num_pages = number

        return Page(results, number, self)

Paginator = GAEPaginator

def get_page(request, paginator):
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    try:
        page = paginator.page(page)
    except (EmptyPage, InvalidPage):
        page = paginator.page(paginator.num_pages)

    return page
########NEW FILE########
__FILENAME__ = tags
from google.appengine.ext import webapp
register = webapp.template.create_template_register()

from app.utils import trunc_string

from django.contrib.markup.templatetags.markup import markdown as real_markdown

@register.filter
def trunc(value, arg):
    "Removes all values of arg from the given string"
    return trunc_string(value, arg)

@register.filter
def markdown(value, arg=""):
    return real_markdown(value, arg)

########NEW FILE########
__FILENAME__ = tests
# test data
from django.conf import settings

try:
    account = settings.ARECIBO_PUBLIC_ACCOUNT_NUMBER
except ImportError:
    account = "1231241243"
        
test_data = {
    "account": account,
    "priority": 4,
    "user_agent": "Mozilla/5.0 (Macintosh; U; Intel Mac OS X...",
    "url": "http://badapp.org/-\ufffdwe-cant-lose",
    "uid": "123124123123",
    "ip": "127.0.0.1",
    "type": "Test from python",
    "status": "403",
    "server": "Test Script",
    "request": """This is the bit that goes in the request""",
    "username": "Jimbob",
    "msg": """
Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut
labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris
nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit
esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in
culpa qui officia deserunt mollit anim id est laborum
""",
    "traceback": """Traceback (most recent call last",:
File "<stdin>", line 1, in <module>
ZeroDivisionError: integer division or modulo by zero  df
""",}
########NEW FILE########
__FILENAME__ = test_runner
import os

from django.conf import settings
from django.test.simple import DjangoTestSuiteRunner

from django.core import mail
from django.core.mail.backends import locmem

from google.appengine.api import mail
from django.core.mail.message import EmailMessage

os.environ['SERVER_SOFTWARE'] = "Development"
settings.DATABASES['default']['SUPPORTS_TRANSACTIONS'] = True

# amongst other things this will suppress those annoying logs
settings.DEBUG = False

def send_email_dummy(sender=None, to=None, subject=None, body=None):
    # app engine doesn't use the backend, so that if you try to write
    # unit tests that check the mail api, they fail, this patches it
    # back in, for the purpose of unit_tests
    return EmailMessage(subject, body, sender, [to,], connection=None).send()

class AreciboRunner(DjangoTestSuiteRunner):
    def setup_test_environment(self, **kwargs):
        super(AreciboRunner, self).setup_test_environment(**kwargs)
        mail.send_mail = send_email_dummy
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^$', 'app.views.index', name="index"),
    url(r'^lib/error.js', 'app.views.javascript_client', name="error-javascript"),
    url(r'^lib/error-compress.js', 'app.views.javascript_client', name="error-javascript-compressed"),
    url(r'^accounts/login/$', 'app.views.login', name="login"),
    url(r'^accounts/logout/$', 'app.views.logout', name="logout"),
    url(r'^accounts/not-allowed/$', 'app.views.not_allowed', name="not-allowed"),
    url(r'^setup$', 'app.views.setup', name="setup")
)

########NEW FILE########
__FILENAME__ = utils
# general utils
import logging
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import simplejson
from django.utils.encoding import smart_unicode
from django.core.urlresolvers import reverse

from urlparse import urlparse, urlunparse

try:
    from functools import update_wrapper, wraps
except ImportError:
    from django.utils.functional import update_wrapper, wraps  # Python 2.3, 2.4 fallback.

def log(msg):
    if settings.DEBUG:
        logging.info(" Arecibo: %s" % msg)

def safe_int(key, result=None):
    try:
        return int(key)
    except (ValueError, AttributeError):
        return result

def render_plain(msg):
    return HttpResponse(msg, mimetype="text/plain")

def render_json(view_func):
    def wrapper(*args, **kwargs):
        data = view_func(*args, **kwargs)
        return HttpResponse(simplejson.dumps(data), mimetype='application/json')
    return wrapper

def not_allowed(request):
    return HttpResponseRedirect(reverse("not-allowed"))

def safe_string(text, result=""):
    try:
        return str(text)
    except (ValueError, AttributeError):
        return result

def trunc_string(text, length, ellipsis="..."):
    try:
        if len(text) < length:
            return text
        else:
            return "%s%s" % (text[:length-len(ellipsis)], ellipsis)
    except TypeError:
        return ""

def has_private_key(view_func):
    """ Will check that the person accessing the page is doing so with the private URL """
    def wrapper(*args, **kwargs):
        request = args[0]
        if settings.ARECIBO_PRIVATE_ACCOUNT_NUMBER not in request.get_full_path().split("/"):
            return HttpResponseRedirect(settings.LOGIN_URL)
        return view_func(*args, **kwargs)
    return wraps(view_func)(wrapper)

def break_url(url):
    result = {"raw": url}
    parsed = list(urlparse(url))
    result["protocol"] = parsed[0]
    result["domain"] = parsed[1]
    result["query"] = urlunparse(["",""] + parsed[2:])
    return result

def _pdb():
    import pdb, sys
    sys.__stdout__.write('\a')
    sys.__stdout__.flush()
    debugger = pdb.Pdb(stdin=sys.__stdin__, stdout=sys.__stdout__)
    debugger.set_trace()

########NEW FILE########
__FILENAME__ = views
import os
from urlparse import urlparse

from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseRedirect
from django.views.generic.simple import direct_to_template
from django.core.urlresolvers import reverse
from django.conf import settings
from django.views.decorators.vary import vary_on_headers
from django.views.decorators.cache import cache_control

from google.appengine.api import users

#: static_resource cache decorator will be used for things which can safely
# be cached to improve client HTTP performance
static_resource = cache_control(public=True, max_age=86400)

def index(request):
    if request.user.is_authenticated and request.user.is_staff:
        return HttpResponseRedirect(reverse("error-list"))
    return direct_to_template(request, "index.html")

def not_allowed(request):
    return direct_to_template(request, "403.html")

@user_passes_test(lambda u: u.is_staff)
def setup(request):
    return direct_to_template(request, "setup.html", extra_context={
        "nav": {"selected": "setup"},
        "app_id": os.environ.get("APPLICATION_ID"),
        })

@static_resource
@vary_on_headers("Accept-Encoding")
def javascript_client(request):
    return direct_to_template(request, "error.js",
        extra_context = {
            "domain": urlparse(settings.SITE_URL)[1]
        },
        mimetype = "text/javascript",
    )

def logout(request):
    return HttpResponseRedirect(users.create_logout_url("/"))

def login(request):
    return HttpResponseRedirect(users.create_login_url("/"))

########NEW FILE########
__FILENAME__ = decorators
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Decorators for the authentication framework."""

from django.http import HttpResponseRedirect

from google.appengine.api import users


def login_required(function):
  """Implementation of Django's login_required decorator.

  The login redirect URL is always set to request.path
  """
  def login_required_wrapper(request, *args, **kw):
    if request.user.is_authenticated():
      return function(request, *args, **kw)
    return HttpResponseRedirect(users.create_login_url(request.path))
  return login_required_wrapper

########NEW FILE########
__FILENAME__ = middleware
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.contrib.auth.models import AnonymousUser

from google.appengine.api import users

from appengine_django.auth.models import User


class LazyUser(object):
  def __get__(self, request, obj_type=None):
    if not hasattr(request, '_cached_user'):
      user = users.get_current_user()
      if user:
        request._cached_user = User.get_djangouser_for_user(user)
      else:
        request._cached_user = AnonymousUser()
    return request._cached_user


class AuthenticationMiddleware(object):
  def process_request(self, request):
    request.__class__.user = LazyUser()
    return None

########NEW FILE########
__FILENAME__ = models
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
App Engine compatible models for the Django authentication framework.
"""

from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.utils.encoding import smart_str
import urllib

from django.db.models.manager import EmptyManager

from google.appengine.api import users
from google.appengine.ext import db

from appengine_django.models import BaseModel
from appengine_django.auth.signals import user_created

class User(BaseModel):
  """A model with the same attributes and methods as a Django user model.

  The model has two additions. The first addition is a 'user' attribute which
  references a App Engine user. The second is the 'get_djangouser_for_user'
  classmethod that should be used to retrieve a DjangoUser instance from a App
  Engine user object.
  """
  user = db.UserProperty(required=True)
  username = db.StringProperty(required=True)
  first_name = db.StringProperty()
  last_name = db.StringProperty()
  email = db.EmailProperty()
  password = db.StringProperty()
  is_staff = db.BooleanProperty(default=False, required=True)
  is_active = db.BooleanProperty(default=True, required=True)
  is_superuser = db.BooleanProperty(default=False, required=True)
  last_login = db.DateTimeProperty(auto_now_add=True, required=True)
  date_joined = db.DateTimeProperty(auto_now_add=True, required=True)
  groups = EmptyManager()
  user_permissions = EmptyManager()

  def __unicode__(self):
    return self.username

  def __str__(self):
    return unicode(self).encode('utf-8')

  @classmethod
  def get_djangouser_for_user(cls, user):
    query = cls.all().filter("user =", user)
    if query.count() == 0:
      django_user = cls(user=user, email=user.email(), username=user.nickname())
      django_user.save()
    else:
      django_user = query.get()
    return django_user

  def set_password(self, raw_password):
    raise NotImplementedError

  def check_password(self, raw_password):
    raise NotImplementedError

  def set_unusable_password(self):
    raise NotImplementedError

  def has_usable_password(self):
    raise NotImplementedError

  def get_group_permissions(self):
    return self.user_permissions

  def get_all_permissions(self):
    return self.user_permissions

  def has_perm(self, perm):
    return False

  def has_perms(self, perm_list):
    return False

  def has_module_perms(self, module):
    return False

  def get_and_delete_messages(self):
    """Gets and deletes messages for this user"""
    msgs = []
    for msg in self.message_set:
      msgs.append(msg)
      msg.delete()
    return msgs

  def is_anonymous(self):
    """Always return False"""
    return False

  def is_authenticated(self):
    """Always return True"""
    return True

  def get_absolute_url(self):
    return "/users/%s/" % urllib.quote(smart_str(self.username))

  def get_full_name(self):
    full_name = u'%s %s' % (self.first_name, self.last_name)
    return full_name.strip()

  def email_user(self, subject, message, from_email):
    """Sends an email to this user.

    According to the App Engine email API the from_email must be the
    email address of a registered administrator for the application.
    """
    mail.send_mail(subject,
                   message,
                   from_email,
                   [self.email])


  @property
  def pk(self):
    try:
      return str(self.key())
    except db.NotSavedError:
      pass

  def get_profile(self):
    """
    Returns site-specific profile for this user. Raises
    SiteProfileNotAvailable if this site does not allow profiles.

    When using the App Engine authentication framework, users are created
    automatically.
    """
    from django.contrib.auth.models import SiteProfileNotAvailable
    if not hasattr(self, '_profile_cache'):
      from django.conf import settings
      if not hasattr(settings, "AUTH_PROFILE_MODULE"):
        raise SiteProfileNotAvailable
      try:
        app_label, model_name = settings.AUTH_PROFILE_MODULE.split('.')
        model = models.get_model(app_label, model_name)
        self._profile_cache = model.all().filter("user =", self).get()
        if not self._profile_cache:
          raise model.DoesNotExist
      except (ImportError, ImproperlyConfigured):
        raise SiteProfileNotAvailable
    return self._profile_cache

  def save(self):
      created = False
      if not hasattr(self, "id"):
        created = True
      super(User, self).save()
      if created:
        user_created.send(sender=self.__class__, instance=self)

class Group(BaseModel):
  """Group model not fully implemented yet."""
  # TODO: Implement this model, requires contenttypes
  name = db.StringProperty()
  permissions = EmptyManager()


class Message(BaseModel):
  """User message model"""
  user = db.ReferenceProperty(User)
  message = db.TextProperty()


class Permission(BaseModel):
  """Permission model not fully implemented yet."""
  # TODO: Implement this model, requires contenttypes
  name = db.StringProperty()

########NEW FILE########
__FILENAME__ = signals
# add in a user created signal
import django.dispatch

user_created = django.dispatch.Signal(providing_args=["instance",])
########NEW FILE########
__FILENAME__ = templatetags
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Template tags for the auth module. These are inserted into Django as "built-in"
tags so you do not need to use the load statement in your template to get
access to them.
"""

from django.template import Library
from django.template import Node

from google.appengine.api import users


class AuthLoginUrlsNode(Node):
  """Template node that creates an App Engine login or logout URL.

  If create_login_url is True the App Engine's login URL is rendered into
  the template, otherwise the logout URL.
  """
  def __init__(self, create_login_url, redirect):
    self.redirect = redirect
    self.create_login_url = create_login_url

  def render(self, context):
    if self.create_login_url:
      return users.create_login_url(self.redirect)
    else:
      return users.create_logout_url(self.redirect)


def auth_login_urls(parser, token):
  """Template tag registered as 'auth_login_url' and 'auth_logout_url'
  when the module is imported.

  Both tags take an optional argument that specifies the redirect URL and
  defaults to '/'.
  """
  bits = list(token.split_contents())
  if len(bits) == 2:
    redirect = bits[1]
  else:
    redirect = "/"
  login = bits[0] == "auth_login_url"
  return AuthLoginUrlsNode(login, redirect)


register = Library()
register.tag("auth_login_url", auth_login_urls)
register.tag("auth_logout_url", auth_login_urls)

########NEW FILE########
__FILENAME__ = models
from appengine_django.models import BaseModel
from google.appengine.ext import db

# Create your models here.

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = base
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This module looks after initialising the appengine api stubs."""

import logging
import os

from appengine_django import appid
from appengine_django import have_appserver
from appengine_django.db.creation import DatabaseCreation


from django.db.backends import BaseDatabaseWrapper
from django.db.backends import BaseDatabaseFeatures
from django.db.backends import BaseDatabaseOperations


def get_datastore_paths():
  """Returns a tuple with the path to the datastore and history file.

  The datastore is stored in the same location as dev_appserver uses by
  default, but the name is altered to be unique to this project so multiple
  Django projects can be developed on the same machine in parallel.

  Returns:
    (datastore_path, history_path)
  """
  from google.appengine.tools import dev_appserver_main
  datastore_path = dev_appserver_main.DEFAULT_ARGS['datastore_path']
  history_path = dev_appserver_main.DEFAULT_ARGS['history_path']
  datastore_path = datastore_path.replace("dev_appserver", "django_%s" % appid)
  history_path = history_path.replace("dev_appserver", "django_%s" % appid)
  return datastore_path, history_path


def get_test_datastore_paths(inmemory=True):
  """Returns a tuple with the path to the test datastore and history file.

  If inmemory is true, (None, None) is returned to request an in-memory
  datastore. If inmemory is false the path returned will be similar to the path
  returned by get_datastore_paths but with a different name.

  Returns:
    (datastore_path, history_path)
  """
  if inmemory:
    return None, None
  datastore_path, history_path = get_datastore_paths()
  datastore_path = datastore_path.replace("datastore", "testdatastore")
  history_path = history_path.replace("datastore", "testdatastore")
  return datastore_path, history_path


def destroy_datastore(datastore_path, history_path):
  """Destroys the appengine datastore at the specified paths."""
  for path in [datastore_path, history_path]:
    if not path: continue
    try:
      os.remove(path)
    except OSError, e:
      if e.errno != 2:
        logging.error("Failed to clear datastore: %s" % e)


class DatabaseError(Exception):
  """Stub class for database errors. Required by Django"""
  pass


class IntegrityError(Exception):
  """Stub class for database integrity errors. Required by Django"""
  pass


class DatabaseFeatures(BaseDatabaseFeatures):
  """Stub class to provide the feaures member expected by Django"""
  pass


class DatabaseOperations(BaseDatabaseOperations):
  """Stub class to provide the options member expected by Django"""
  pass


class DatabaseWrapper(BaseDatabaseWrapper):
  """App Engine database definition for Django.

  This "database" backend does not support any of the standard backend
  operations. The only task that it performs is to setup the api stubs required
  by the appengine libraries if they have not already been initialised by an
  appserver.
  """

  def __init__(self, *args, **kwargs):
    super(DatabaseWrapper, self).__init__(*args, **kwargs)
    self.features = DatabaseFeatures()
    self.ops = DatabaseOperations()
    self.creation = DatabaseCreation(self)
    self.use_test_datastore = kwargs.get("use_test_datastore", False)
    self.test_datastore_inmemory = kwargs.get("test_datastore_inmemory", True)
    if have_appserver:
      return
    self._setup_stubs()

  def _get_paths(self):
    if self.use_test_datastore:
      return get_test_datastore_paths(self.test_datastore_inmemory)
    else:
      return get_datastore_paths()

  def _setup_stubs(self):
    # If this code is being run without an appserver (eg. via a django
    # commandline flag) then setup a default stub environment.
    from google.appengine.tools import dev_appserver_main
    args = dev_appserver_main.DEFAULT_ARGS.copy()
    args['datastore_path'], args['history_path'] = self._get_paths()
    from google.appengine.tools import dev_appserver
    dev_appserver.SetupStubs(appid, **args)
    if self.use_test_datastore:
      logging.debug("Configured API stubs for the test datastore")
    else:
      logging.debug("Configured API stubs for the development datastore")

  def flush(self):
    """Helper function to remove the current datastore and re-open the stubs"""
    destroy_datastore(*self._get_paths())
    self._setup_stubs()

  def close(self):
    pass

  def _commit(self):
    pass

  def cursor(self, *args):
    pass

########NEW FILE########
__FILENAME__ = creation
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import logging

from django.conf import settings
from django.db.backends.creation import BaseDatabaseCreation


class DatabaseCreation(BaseDatabaseCreation):

  def create_test_db(self, *args, **kw):
    """Destroys the test datastore. A new store will be recreated on demand"""
    settings.DATABASE_SUPPORTS_TRANSACTIONS = False
    self.destroy_test_db()
    self.connection.use_test_datastore = True
    self.connection.flush()


  def destroy_test_db(self, *args, **kw):
    """Destroys the test datastore files."""
    from appengine_django.db.base import destroy_datastore
    from appengine_django.db.base import get_test_datastore_paths
    destroy_datastore(*get_test_datastore_paths())
    logging.debug("Destroyed test datastore")

########NEW FILE########
__FILENAME__ = mail
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module replaces the Django mail implementation with a version that sends
email via the mail API provided by Google App Engine.

Multipart / HTML email is not yet supported.
"""

import logging

from django.core import mail
from django.core.mail import SMTPConnection
from django.conf import settings

from google.appengine.api import mail as gmail


class GoogleSMTPConnection(SMTPConnection):
  def __init__(self, host=None, port=None, username=None, password=None,
               use_tls=None, fail_silently=False):
    self.use_tls = (use_tls is not None) and use_tls or settings.EMAIL_USE_TLS
    self.fail_silently = fail_silently
    self.connection = None

  def open(self):
    self.connection = True

  def close(self):
    pass

  def _send(self, email_message):
    """A helper method that does the actual sending."""
    if not email_message.to:
      return False
    try:
      if (isinstance(email_message,gmail.EmailMessage)):
        e = message
      elif (isinstance(email_message,mail.EmailMessage)):
        e = gmail.EmailMessage(sender=email_message.from_email,
                               to=email_message.to,
                               subject=email_message.subject,
                               body=email_message.body)
        if email_message.extra_headers.get('Reply-To', None):
            e.reply_to = email_message.extra_headers['Reply-To']
        if email_message.bcc:
            e.bcc = list(email_message.bcc)
        #TODO - add support for html messages and attachments...
      e.send()
    except:
      if not self.fail_silently:
          raise
      return False
    return True


def mail_admins(subject, message, fail_silently=False):
    """Sends a message to the admins, as defined by the ADMINS setting."""
    _mail_group(settings.ADMINS, subject, message, fail_silently)


def mail_managers(subject, message, fail_silently=False):
    """Sends a message to the managers, as defined by the MANAGERS setting."""
    _mail_group(settings.MANAGERS, subject, message, fail_silently)


def _mail_group(group, subject, message, fail_silently=False):
    """Sends a message to an administrative group."""
    if group:
      mail.send_mail(settings.EMAIL_SUBJECT_PREFIX + subject, message,
                     settings.SERVER_EMAIL, [a[1] for a in group],
                     fail_silently)
      return
    # If the group had no recipients defined, default to the App Engine admins.
    try:
      gmail.send_mail_to_admins(settings.SERVER_EMAIL,
                                settings.EMAIL_SUBJECT_PREFIX + subject,
                                message)
    except:
      if not fail_silently:
        raise

########NEW FILE########
__FILENAME__ = console
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import code
import getpass
import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand

from google.appengine.ext.remote_api import remote_api_stub


def auth_func():
  return raw_input('Username:'), getpass.getpass('Password:')

class Command(BaseCommand):
  """ Start up an interactive console backed by your app using remote_api """

  help = 'Start up an interactive console backed by your app using remote_api.'

  def run_from_argv(self, argv):
    app_id = argv[2]
    if len(argv) > 3:
      host = argv[3]
    else:
      host = '%s.appspot.com' % app_id

    remote_api_stub.ConfigureRemoteDatastore(app_id,
                                             '/remote_api',
                                             auth_func,
                                             host)

    code.interact('App Engine interactive console for %s' % (app_id,),
                  None,
                  locals())

########NEW FILE########
__FILENAME__ = flush
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
import sys

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Overrides the default Django flush command.
    """
    help = 'Clears the current datastore and loads the initial fixture data.'

    def run_from_argv(self, argv):
      from django.db import connection
      connection.flush()
      from django.core.management import call_command
      call_command('loaddata', 'initial_data')

    def handle(self, *args, **kwargs):
      self.run_from_argv(None)

########NEW FILE########
__FILENAME__ = reset
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import logging
import os
import sys

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Overrides the default Django reset command.
    """
    help = 'Clears the current datastore.'

    def run_from_argv(self, argv):
      from django.db import connection
      connection.flush()

########NEW FILE########
__FILENAME__ = rollback
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import sys
import logging

from django.core.management.base import BaseCommand


def run_appcfg():
  # import this so that we run through the checks at the beginning
  # and report the appropriate errors
  import appcfg

  # We don't really want to use that one though, it just executes this one
  from google.appengine.tools import appcfg

  # Reset the logging level to WARN as appcfg will spew tons of logs on INFO
  logging.getLogger().setLevel(logging.WARN)

  # Note: if we decide to change the name of this command to something other
  #       than 'rollback' we will have to munge the args to replace whatever
  #       we called it with 'rollback'
  new_args = sys.argv[:]
  new_args.append('.')
  appcfg.main(new_args)


class Command(BaseCommand):
  """Calls the appcfg.py's rollback command for the current project.

  Any additional arguments are passed directly to appcfg.py.
  """
  help = 'Calls appcfg.py rollback for the current project.'
  args = '[any appcfg.py options]'

  def run_from_argv(self, argv):
    run_appcfg()

########NEW FILE########
__FILENAME__ = runserver
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import sys

from appengine_django.db.base import get_datastore_paths

from django.core.management.base import BaseCommand


def start_dev_appserver():
  """Starts the appengine dev_appserver program for the Django project.

  The appserver is run with default parameters. If you need to pass any special
  parameters to the dev_appserver you will have to invoke it manually.
  """
  from google.appengine.tools import dev_appserver_main
  progname = sys.argv[0]
  args = []
  # hack __main__ so --help in dev_appserver_main works OK.
  sys.modules['__main__'] = dev_appserver_main
  # Set bind ip/port if specified.
  if len(sys.argv) > 2:
    addrport = sys.argv[2]
    try:
      addr, port = addrport.split(":")
    except ValueError:
      addr, port = None, addrport
    if not port.isdigit():
      print "Error: '%s' is not a valid port number." % port
      sys.exit(1)
  else:
    addr, port = None, "8000"
  if addr:
    args.extend(["--address", addr])
  if port:
    args.extend(["--port", port])
  # Add email settings
  from django.conf import settings
  args.extend(['--smtp_host', settings.EMAIL_HOST,
               '--smtp_port', str(settings.EMAIL_PORT),
               '--smtp_user', settings.EMAIL_HOST_USER,
               '--smtp_password', settings.EMAIL_HOST_PASSWORD])

  # Allow skipped files so we don't die
  args.extend(['--allow_skipped_files'])

  # Pass the application specific datastore location to the server.
  p = get_datastore_paths()
  args.extend(["--datastore_path", p[0], "--history_path", p[1]])

  # Append the current working directory to the arguments.
  dev_appserver_main.main([progname] + args + [os.getcwdu()])


class Command(BaseCommand):
    """Overrides the default Django runserver command.

    Instead of starting the default Django development server this command
    fires up a copy of the full fledged appengine dev_appserver that emulates
    the live environment your application will be deployed to.
    """
    help = 'Runs a copy of the appengine development server.'
    args = '[optional port number, or ipaddr:port]'

    def run_from_argv(self, argv):
      start_dev_appserver()

########NEW FILE########
__FILENAME__ = startapp
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os

import django
from django.core.management.commands import startapp

import appengine_django


class Command(startapp.Command):
  def handle_label(self, *args, **kwds):
    """Temporary adjust django.__path__ to load app templates from the
    helpers directory.
    """
    old_path = django.__path__
    django.__path__ = appengine_django.__path__
    startapp.Command.handle_label(self, *args, **kwds)
    django.__path__ = old_path


class ProjectCommand(Command):
  def __init__(self, project_directory):
    super(ProjectCommand, self).__init__()
    self.project_directory = project_directory

  def handle_label(self, app_name, **options):
    super(ProjectCommand, self).handle_label(app_name, self.project_directory,
                                             **options)


########NEW FILE########
__FILENAME__ = testserver
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import sys

from appengine_django.db.base import destroy_datastore
from appengine_django.db.base import get_test_datastore_paths

from django.core.management.base import BaseCommand


class Command(BaseCommand):
  """Overrides the default Django testserver command.

  Instead of starting the default Django development server this command fires
  up a copy of the full fledged appengine dev_appserver.

  The appserver is always initialised with a blank datastore with the specified
  fixtures loaded into it.
  """
  help = 'Runs the development server with data from the given fixtures.'

  def run_from_argv(self, argv):
    fixtures = argv[2:]

    # Ensure an on-disk test datastore is used.
    from django.db import connection
    connection.use_test_datastore = True
    connection.test_datastore_inmemory = False

    # Flush any existing test datastore.
    connection.flush()

    # Load the fixtures.
    from django.core.management import call_command
    call_command('loaddata', 'initial_data')
    if fixtures:
      call_command('loaddata', *fixtures)

    # Build new arguments for dev_appserver.
    datastore_path, history_path = get_test_datastore_paths(False)
    new_args = argv[0:1]
    new_args.extend(['--datastore_path', datastore_path])
    new_args.extend(['--history_path', history_path])
    new_args.extend([os.getcwdu()])

    # Add email settings
    from django.conf import settings
    new_args.extend(['--smtp_host', settings.EMAIL_HOST,
                     '--smtp_port', str(settings.EMAIL_PORT),
                     '--smtp_user', settings.EMAIL_HOST_USER,
                     '--smtp_password', settings.EMAIL_HOST_PASSWORD])

    # Allow skipped files so we don't die
    new_args.extend(['--allow_skipped_files'])

    # Start the test dev_appserver.
    from google.appengine.tools import dev_appserver_main
    dev_appserver_main.main(new_args)

########NEW FILE########
__FILENAME__ = update
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import sys
import logging

from django.core.management.base import BaseCommand


def run_appcfg():
  # import this so that we run through the checks at the beginning
  # and report the appropriate errors
  import appcfg

  # We don't really want to use that one though, it just executes this one
  from google.appengine.tools import appcfg

  # Reset the logging level to WARN as appcfg will spew tons of logs on INFO
  logging.getLogger().setLevel(logging.WARN)

  # Note: if we decide to change the name of this command to something other
  #       than 'update' we will have to munge the args to replace whatever
  #       we called it with 'update'
  new_args = sys.argv[:]
  new_args.append('.')
  appcfg.main(new_args)

class Command(BaseCommand):
  """Calls the appcfg.py's update command for the current project.

  Any additional arguments are passed directly to appcfg.py.
  """
  help = 'Calls appcfg.py update for the current project.'
  args = '[any appcfg.py options]'

  def run_from_argv(self, argv):
    run_appcfg()

########NEW FILE########
__FILENAME__ = vacuum_indexes
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import sys
import logging

from django.core.management.base import BaseCommand


def run_appcfg():
  # import this so that we run through the checks at the beginning
  # and report the appropriate errors
  import appcfg

  # We don't really want to use that one though, it just executes this one
  from google.appengine.tools import appcfg

  # Reset the logging level to WARN as appcfg will spew tons of logs on INFO
  logging.getLogger().setLevel(logging.WARN)

  # Note: if we decide to change the name of this command to something other
  #       than 'vacuum_indexes' we will have to munge the args to replace whatever
  #       we called it with 'vacuum_indexes'
  new_args = sys.argv[:]
  new_args.append('.')
  appcfg.main(new_args)


class Command(BaseCommand):
  """Calls the appcfg.py's vacuum_indexes command for the current project.

  Any additional arguments are passed directly to appcfg.py.
  """
  help = 'Calls appcfg.py vacuum_indexes for the current project.'
  args = '[any appcfg.py options]'

  def run_from_argv(self, argv):
    run_appcfg()

########NEW FILE########
__FILENAME__ = models
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import types

from google.appengine.ext import db

from django import VERSION
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.fields import Field
from django.db.models.options import Options
from django.db.models.loading import register_models, get_model


class ModelManager(object):
  """Replacement for the default Django model manager."""

  def __init__(self, owner):
    self.owner = owner

  def __getattr__(self, name):
    """Pass all attribute requests through to the real model"""
    return getattr(self.owner, name)


class ModelOptions(object):
  """Replacement for the default Django options class.

  This class sits at ._meta of each model. The primary information supplied by
  this class that needs to be stubbed out is the list of fields on the model.
  """

  # Django 1.1 compat
  proxy = None
  # http://code.google.com/p/google-app-engine-django/issues/detail?id=171
  auto_created = False

  def __init__(self, cls):
    self.object_name = cls.__name__
    self.module_name = self.object_name.lower()
    model_module = sys.modules[cls.__module__]
    self.app_label = model_module.__name__.split('.')[-2]
    self.abstract = False

  class pk:
    """Stub the primary key to always be 'key_name'"""
    name = "key_name"

  def __str__(self):
    return "%s.%s" % (self.app_label, self.module_name)

  @property
  def many_to_many(self):
    """The datastore does not support many to many relationships."""
    return []


class Relation(object):
  def __init__(self, to):
    self.field_name = "key_name"


def PropertyWrapper(prop):
  """Wrapper for db.Property to make it look like a Django model Property"""
  if isinstance(prop, db.Reference):
    prop.rel = Relation(prop.reference_class)
  else:
    prop.rel = None
  prop.serialize = True

  # NOTE(termie): These are rather useless hacks to get around Django changing
  #               their approach to "fields" and breaking encapsulation a bit,
  def _get_val_from_obj(obj):
    if obj:
      return getattr(obj, prop.name)
    else:
      return prop.default_value()

  def value_to_string(obj):
    if obj:
      return str(getattr(obj, prop.name))
    else:
      return str(prop.default_value())

  prop._get_val_from_obj = _get_val_from_obj
  prop.value_to_string = value_to_string

  return prop




class PropertiedClassWithDjango(db.PropertiedClass):
  """Metaclass for the combined Django + App Engine model class.

  This metaclass inherits from db.PropertiedClass in the appengine library.
  This metaclass has two additional purposes:
  1) Register each model class created with Django (the parent class will take
     care of registering it with the appengine libraries).
  2) Add the (minimum number) of attributes and methods to make Django believe
     the class is a normal Django model.

  The resulting classes are still not generally useful as Django classes and
  are intended to be used by Django only in limited situations such as loading
  and dumping fixtures.
  """

  def __new__(cls, name, bases, attrs):
    """Creates a combined appengine and Django model.

    The resulting model will be known to both the appengine libraries and
    Django.
    """
    if name == 'BaseModel':
      # This metaclass only acts on subclasses of BaseModel.
      return super(PropertiedClassWithDjango, cls).__new__(cls, name,
                                                           bases, attrs)

    new_class = super(PropertiedClassWithDjango, cls).__new__(cls, name,
                                                              bases, attrs)

    new_class._meta = ModelOptions(new_class)
    new_class.objects = ModelManager(new_class)
    new_class._default_manager = new_class.objects
    new_class.DoesNotExist = types.ClassType('DoesNotExist',
                                             (ObjectDoesNotExist,), {})

    m = get_model(new_class._meta.app_label, name, False)
    if m:
      return m

    register_models(new_class._meta.app_label, new_class)
    return get_model(new_class._meta.app_label, name, False)

  def __init__(cls, name, bases, attrs):
    """Initialises the list of Django properties.

    This method takes care of wrapping the properties created by the superclass
    so that they look like Django properties and installing them into the
    ._meta object of the class so that Django can find them at the appropriate
    time.
    """
    super(PropertiedClassWithDjango, cls).__init__(name, bases, attrs)
    if name == 'BaseModel':
      # This metaclass only acts on subclasses of BaseModel.
      return

    fields = [PropertyWrapper(p) for p in cls._properties.values()]
    cls._meta.local_fields = fields


class BaseModel(db.Model):
  """Combined appengine and Django model.

  All models used in the application should derive from this class.
  """
  __metaclass__ = PropertiedClassWithDjango
  _deferred = False
  # Added for Django 1.1.2 and 1.2.1
  # http://code.google.com/p/google-app-engine-django/issues/detail?id=171

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return False
    return self._get_pk_val() == other._get_pk_val()

  def __ne__(self, other):
    return not self.__eq__(other)

  def _get_pk_val(self):
    """Return the string representation of the model's key"""
    return unicode(self.key())

  def __repr__(self):
    """Create a string that can be used to construct an equivalent object.

    e.g. eval(repr(obj)) == obj
    """
    # First, creates a dictionary of property names and values. Note that
    # property values, not property objects, has to be passed in to constructor.
    def _MakeReprTuple(prop_name):
      prop = getattr(self.__class__, prop_name)
      return (prop_name, prop.get_value_for_datastore(self))

    d = dict([_MakeReprTuple(prop_name) for prop_name in self.properties()])
    return "%s(**%s)" % (self.__class__.__name__, repr(d))



class RegistrationTestModel(BaseModel):
  """Used to check registration with Django is working correctly.

  Django 0.96 only recognises models defined within an applications models
  module when get_models() is called so this definition must be here rather
  than within the associated test (tests/model_test.py).
  """
  pass

########NEW FILE########
__FILENAME__ = replacement_imp
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This file acts as a very minimal replacement for the 'imp' module.

It contains only what Django expects to use and does not actually implement the
same functionality as the real 'imp' module.
"""


def find_module(name, path=None):
  """Django needs imp.find_module, but it works fine if nothing is found."""
  raise ImportError

########NEW FILE########
__FILENAME__ = json
#!/usr/bin/python2.4
#
# Copyright 2009 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Replacement for the Django JSON encoder that handles microseconds.
"""
import datetime

from django.utils import datetime_safe
from django.utils import simplejson


class DjangoJSONEncoder(simplejson.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time with microseconds.
    """

    DATE_FORMAT = "%Y-%m-%d"
    TIME_FORMAT = "%H:%M:%S"

    def default(self, o):
        if isinstance(o, datetime.datetime):
            d = datetime_safe.new_datetime(o)
            output = d.strftime("%s %s" % (self.DATE_FORMAT, self.TIME_FORMAT))
            return "%s.%s" % (output, d.microsecond)
        elif isinstance(o, datetime.date):
            d = datetime_safe.new_date(o)
            return d.strftime(self.DATE_FORMAT)
        elif isinstance(o, datetime.time):
            output = o.strftime(self.TIME_FORMAT)
            return "%s.%s" % (output, o.microsecond)
        elif isinstance(o, decimal.Decimal):
            return str(o)
        else:
            return super(DjangoJSONEncoder, self).default(o)

########NEW FILE########
__FILENAME__ = python
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
A Python "serializer", based on the default Django python serializer.

The only customisation is in the deserialization process which needs to take
special care to resolve the name and parent attributes of the key for each
entity and also recreate the keys for any references appropriately.
"""
import datetime
import re

from django.conf import settings
from django.core.serializers import base
from django.core.serializers import python
from django.db import models

from google.appengine.api import datastore_types
from google.appengine.ext import db

from django.utils.encoding import smart_unicode

Serializer = python.Serializer


class FakeParent(object):
  """Fake parent 'model' like object.

  This class exists to allow a parent object to be provided to a new model
  without having to load the parent instance itself.
  """

  def __init__(self, parent_key):
    self._entity = parent_key


def Deserializer(object_list, **options):
  """Deserialize simple Python objects back into Model instances.

  It's expected that you pass the Python objects themselves (instead of a
  stream or a string) to the constructor
  """
  models.get_apps()
  for d in object_list:
    # Look up the model and starting build a dict of data for it.
    Model = python._get_model(d["model"])
    data = {}
    key = resolve_key(Model._meta.module_name, d["pk"])
    if key.name():
      data["key_name"] = key.name()
    parent = None
    if key.parent():
      parent = FakeParent(key.parent())
    m2m_data = {}

    # Handle each field
    for (field_name, field_value) in d["fields"].iteritems():
      if isinstance(field_value, str):
        field_value = smart_unicode(
            field_value, options.get("encoding",
                                     settings.DEFAULT_CHARSET),
            strings_only=True)
      field = Model.properties()[field_name]

      if isinstance(field, db.Reference):
        # Resolve foreign key references.
        data[field.name] = resolve_key(Model._meta.module_name, field_value)
      else:
        # Handle converting strings to more specific formats.
        if isinstance(field_value, basestring):
          if isinstance(field, db.DateProperty):
            field_value = datetime.datetime.strptime(
                field_value, '%Y-%m-%d').date()
          elif isinstance(field, db.TimeProperty):
            field_value = parse_datetime_with_microseconds(field_value,
                                                           '%H:%M:%S').time()
          elif isinstance(field, db.DateTimeProperty):
            field_value = parse_datetime_with_microseconds(field_value,
                                                           '%Y-%m-%d %H:%M:%S')
        # Handle pyyaml datetime.time deserialization - it returns a datetime
        # instead of a time.
        if (isinstance(field_value, datetime.datetime) and
            isinstance(field, db.TimeProperty)):
          field_value = field_value.time()
        data[field.name] = field.validate(field_value)
    # Create the new model instance with all it's data, but no parent.
    object = Model(**data)
    # Now add the parent into the hidden attribute, bypassing the type checks
    # in the Model's __init__ routine.
    object._parent = parent
    # When the deserialized object is saved our replacement DeserializedObject
    # class will set object._parent to force the real parent model to be loaded
    # the first time it is referenced.
    yield base.DeserializedObject(object, m2m_data)


def parse_datetime_with_microseconds(field_value, format):
  """Parses a string to a datetime object including microseconds.

  Args:
    field_value: The string to parse.
    format: The format string to parse to datetime.strptime. Not including a
      format specifier for the expected microseconds component.

  Returns:
    A datetime instance.
  """
  try:
    # This will only return if no microseconds were availanle.
    return datetime.datetime.strptime(field_value, format)
  except ValueError, e:
    # Hack to deal with microseconds.
    match = re.match(r'unconverted data remains: \.([0-9]+)$',
                     str(e))
    if not match:
      raise
    ms_str = match.group(1)
    without_ms = field_value[:-(len(ms_str)+1)]
    new_value = datetime.datetime.strptime(without_ms, format)
    return new_value.replace(microsecond=int(ms_str))


def resolve_key(model, key_data):
  """Creates a Key instance from a some data.

  Args:
    model: The name of the model this key is being resolved for. Only used in
      the fourth case below (a plain key_name string).
    key_data: The data to create a key instance from. May be in four formats:
      * The str() output of a key instance. Eg. A base64 encoded string.
      * The repr() output of a key instance. Eg. A string for eval().
      * A list of arguments to pass to db.Key.from_path.
      * A single string value, being the key_name of the instance. When this
        format is used the resulting key has no parent, and is for the model
        named in the model parameter.

  Returns:
    An instance of db.Key. If the data cannot be used to create a Key instance
    an error will be raised.
  """
  if isinstance(key_data, list):
    # The key_data is a from_path sequence.
    return db.Key.from_path(*key_data)
  elif isinstance(key_data, basestring):
    if key_data.find("from_path") != -1:
      # key_data is encoded in repr(key) format
      return eval(key_data)
    else:
      try:
        # key_data encoded a str(key) format
        return db.Key(key_data)
      except datastore_types.datastore_errors.BadKeyError, e:
        # Final try, assume it's a plain key name for the model.
        return db.Key.from_path(model, key_data)
  else:
    raise base.DeserializationError(u"Invalid key data: '%s'" % key_data)

########NEW FILE########
__FILENAME__ = pyyaml
#!/usr/bin/python2.4
#
# Copyright 2009 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Replacement YAML dumper that can handle datetime.time objects.
"""

import datetime
import yaml

try:
    import decimal
except ImportError:
    from django.utils import _decimal as decimal # Python 2.3 fallback


class DjangoSafeDumper(yaml.SafeDumper):
  """Replacement DjangoSafeDumper that handles datetime.time objects.

  Serializes datetime.time objects to a YAML timestamp tag, there is a
  corresponding hack in python.py to convert the datetime.datetime that the
  YAML decoder returns back to the expected datetime.time object.
  """

  def represent_decimal(self, data):
    return self.represent_scalar('tag:yaml.org,2002:str', str(data))

  def represent_time(self, data):
    value = '1970-01-01 %s' % unicode(data.isoformat())
    return self.represent_scalar('tag:yaml.org,2002:timestamp', value)

DjangoSafeDumper.add_representer(decimal.Decimal, DjangoSafeDumper.represent_decimal)
DjangoSafeDumper.add_representer(datetime.time, DjangoSafeDumper.represent_time)

########NEW FILE########
__FILENAME__ = xml
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""
Replaces the default Django XML serializer with one that uses the built in
ToXml method for each entity.
"""

from datetime import datetime
import re

from django.conf import settings
from django.core.serializers import base
from django.core.serializers import xml_serializer
from django.db import models

from google.appengine.api import datastore_types
from google.appengine.ext import db

from python import FakeParent
from python import parse_datetime_with_microseconds

getInnerText = xml_serializer.getInnerText


class Serializer(xml_serializer.Serializer):
  """A Django Serializer class to convert datastore models to XML.

  This class relies on the ToXml method of the entity behind each model to do
  the hard work.
  """

  def __init__(self, *args, **kwargs):
    super(Serializer, self).__init__(*args, **kwargs)
    self._objects = []

  def handle_field(self, obj, field):
    """Fields are not handled individually."""
    pass

  def handle_fk_field(self, obj, field):
    """Fields are not handled individually."""
    pass

  def start_object(self, obj):
    """Nothing needs to be done to start an object."""
    pass

  def end_object(self, obj):
    """Serialize the object to XML and add to the list of objects to output.

    The output of ToXml is manipulated to replace the datastore model name in
    the "kind" tag with the Django model name (which includes the Django
    application name) to make importing easier.
    """
    xml = obj._entity.ToXml()
    xml = xml.replace(u"""kind="%s" """ % obj._entity.kind(),
                      u"""kind="%s" """ % unicode(obj._meta))
    self._objects.append(xml)

  def getvalue(self):
    """Wrap the serialized objects with XML headers and return."""
    str = u"""<?xml version="1.0" encoding="utf-8"?>\n"""
    str += u"""<django-objects version="1.0">\n"""
    str += u"".join(self._objects)
    str += u"""</django-objects>"""
    return str


class Deserializer(xml_serializer.Deserializer):
  """A Django Deserializer class to convert XML to Django objects.

  This is a fairly manualy and simplistic XML parser, it supports just enough
  functionality to read the keys and fields for an entity from the XML file and
  construct a model object.
  """

  def next(self):
    """Replacement next method to look for 'entity'.

    The default next implementation exepects 'object' nodes which is not
    what the entity's ToXml output provides.
    """
    for event, node in self.event_stream:
      if event == "START_ELEMENT" and node.nodeName == "entity":
        self.event_stream.expandNode(node)
        return self._handle_object(node)
    raise StopIteration

  def _handle_object(self, node):
    """Convert an <entity> node to a DeserializedObject"""
    Model = self._get_model_from_node(node, "kind")
    data = {}
    key = db.Key(node.getAttribute("key"))
    if key.name():
      data["key_name"] = key.name()
    parent = None
    if key.parent():
      parent = FakeParent(key.parent())
    m2m_data = {}

    # Deseralize each field.
    for field_node in node.getElementsByTagName("property"):
      # If the field is missing the name attribute, bail (are you
      # sensing a pattern here?)
      field_name = field_node.getAttribute("name")
      if not field_name:
          raise base.DeserializationError("<field> node is missing the 'name' "
                                          "attribute")
      field = Model.properties()[field_name]
      field_value = getInnerText(field_node).strip()

      if isinstance(field, db.Reference):
        m = re.match("tag:.*\[(.*)\]", field_value)
        if not m:
          raise base.DeserializationError(u"Invalid reference value: '%s'" %
                                          field_value)
        key = m.group(1)
        key_obj = db.Key(key)
        if not key_obj.name():
          raise base.DeserializationError(u"Cannot load Reference with "
                                          "unnamed key: '%s'" % field_value)
        data[field.name] = key_obj
      else:
        format = '%Y-%m-%d %H:%M:%S'
        if isinstance(field, db.DateProperty):
          field_value = datetime.strptime(field_value, format).date()
        elif isinstance(field, db.TimeProperty):
          field_value = parse_datetime_with_microseconds(field_value,
                                                         format).time()
        elif isinstance(field, db.DateTimeProperty):
          field_value = parse_datetime_with_microseconds(field_value, format)
        data[field.name] = field.validate(field_value)

    # Create the new model instance with all it's data, but no parent.
    object = Model(**data)
    # Now add the parent into the hidden attribute, bypassing the type checks
    # in the Model's __init__ routine.
    object._parent = parent
    # When the deserialized object is saved our replacement DeserializedObject
    # class will set object._parent to force the real parent model to be loaded
    # the first time it is referenced.
    return base.DeserializedObject(object, m2m_data)

########NEW FILE########
__FILENAME__ = db
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime

from django.contrib.sessions.backends import base
from django.core.exceptions import SuspiciousOperation

from appengine_django.sessions.models import Session


class SessionStore(base.SessionBase):
  """A key-based session store for Google App Engine."""

  def load(self):
    session = self._get_session(self.session_key)
    if session:
      try:
        return self.decode(session.session_data)
      except SuspiciousOperation:
        # Create a new session_key for extra security.
        pass
    self.session_key = self._get_new_session_key()
    self._session_cache = {}
    self.save()
    # Ensure the user is notified via a new cookie.
    self.modified = True
    return {}

  def save(self, must_create=False):
    if must_create and self.exists(self.session_key):
      raise base.CreateError
    session = Session(
        key_name='k:' + self.session_key,
        session_data = self.encode(self._session),
        expire_date = self.get_expiry_date())
    session.put()

  def exists(self, session_key):
    return Session.get_by_key_name('k:' + session_key) is not None

  def delete(self, session_key=None):
    if session_key is None:
      session_key = self._session_key
    session = self._get_session(session_key=session_key)
    if session:
      session.delete()

  def _get_session(self, session_key):
    session = Session.get_by_key_name('k:' + session_key)
    if session:
      if session.expire_date > datetime.now():
        return session
      session.delete()
    return None

  def create(self):
    while True:
      self.session_key = self._get_new_session_key()
      try:
        # Save immediately to ensure we have a unique entry in the
        # database.
        self.save(must_create=True)
      except base.CreateError:
        # Key wasn't unique. Try again.
        continue
      self.modified = True
      self._session_cache = {}
      return

########NEW FILE########
__FILENAME__ = models
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.appengine.ext import db

class Session(db.Model):
  """Django compatible App Engine Datastore session model."""
  session_data = db.BlobProperty()
  expire_date = db.DateTimeProperty()

########NEW FILE########
__FILENAME__ = commands_test
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Tests that the manage.py commands execute correctly.

These tests only verify that the commands execute and exit with a success code.
They are intended to catch import exceptions and similar problems, it is left
up to tests in other modules to verify that the functionality of each command
works correctly.
"""


import os
import re
import signal
import subprocess
import tempfile
import time
import unittest

from django.db.models import get_models

from google.appengine.ext import db
from appengine_django.models import BaseModel
from appengine_django.models import ModelManager
from appengine_django.models import ModelOptions
from appengine_django.models import RegistrationTestModel


class CommandsTest(unittest.TestCase):
  """Unit tests for the manage.py commands."""

  # How many seconds to wait for a command to exit.
  COMMAND_TIMEOUT = 10

  def runCommand(self, command, args=None, int_after=None, input=None):
    """Helper to run the specified command in a child process.

    Args:
      command: The name of the command to run.
      args: List of command arguments to run the command with.
      int_after: If set to a positive integer, SIGINT will be sent to the
        running child process after this many seconds to cause an exit. This
        should be less than the COMMAND_TIMEOUT value (10 seconds).
      input: A string to write to stdin when the command starts. stdin is
        closed after the string is written.

    Returns:
      rc: The integer return code of the process.
      output: A string containing the childs output.
    """
    if not args:
      args = []
    start = time.time()
    int_sent = False
    fd = subprocess.PIPE

    child = subprocess.Popen(["./manage.py", command] + args, stdin=fd,
                             stdout=fd, stderr=fd, cwd=os.getcwdu())
    if input:
      child.stdin.write(input)
      child.stdin.close()

    while 1:
      rc = child.poll()
      if rc is not None:
        # Child has exited.
        break
      elapsed = time.time() - start
      if int_after and int_after > 0 and elapsed > int_after and not int_sent:
        # Sent SIGINT as requested, give child time to exit cleanly.
        os.kill(child.pid, signal.SIGINT)
        start = time.time()
        int_sent = True
        continue
      if elapsed < self.COMMAND_TIMEOUT:
        continue
      # Command is over time, kill and exit loop.
      os.kill(child.pid, signal.SIGKILL)
      time.sleep(2)  # Give time for the signal to be received.
      break

    # Return status and output.
    return rc, child.stdout.read(), child.stderr.read()

  def assertCommandSucceeds(self, command, *args, **kwargs):
    """Asserts that the specified command successfully completes.

    Args:
      command: The name of the command to run.
      All other arguments are passed directly through to the runCommand
      routine.

    Raises:
      This function does not return anything but will raise assertion errors if
      the command does not exit successfully.
    """
    rc, stdout, stderr = self.runCommand(command, *args, **kwargs)
    fd, tempname = tempfile.mkstemp()
    os.write(fd, stdout)
    os.close(fd)
    self.assertEquals(0, rc,
                      "%s did not return successfully (rc: %d): Output in %s" %
                      (command, rc, tempname))
    os.unlink(tempname)

  def getCommands(self):
    """Returns a list of valid commands for manage.py.

    Args:
      None

    Returns:
      A list of valid commands for manage.py as read from manage.py's help
      output.
    """
    rc, stdout, stderr = self.runCommand("help")
    parts = re.split("Available subcommands:", stderr)
    if len(parts) < 2:
      return []

    return [t.strip() for t in parts[-1].split("\n") if t.strip()]

  def testDiffSettings(self):
    """Tests the diffsettings command."""
    self.assertCommandSucceeds("diffsettings")

  def testDumpData(self):
    """Tests the dumpdata command."""
    self.assertCommandSucceeds("dumpdata")

  def testFlush(self):
    """Tests the flush command."""
    self.assertCommandSucceeds("flush")

  def testLoadData(self):
    """Tests the loaddata command."""
    self.assertCommandSucceeds("loaddata")

  def testLoadData(self):
    """Tests the loaddata command."""
    self.assertCommandSucceeds("loaddata")

  def testReset(self):
    """Tests the reste command."""
    self.assertCommandSucceeds("reset", ["appengine_django"])

  # Disabled due to flakiness - re-enable when it can be guaranteed to succeed
  # reliably.
  #def testRunserver(self):
  #  """Tests the runserver command."""
  #  self.assertCommandSucceeds("runserver", int_after=2.0)

  def testShell(self):
    """Tests the shell command."""
    self.assertCommandSucceeds("shell", input="exit")

  def testUpdate(self):
    """Tests that the update command exists.

    Cannot test that it works without mocking out parts of dev_appserver so for
    now we just assume that if it is present it will work.
    """
    cmd_list = self.getCommands()
    self.assert_("update" in cmd_list)

  def testZipCommandListFiltersCorrectly(self):
    """When running under a zipfile test that only valid commands are found."""
    cmd_list = self.getCommands()
    self.assert_("__init__" not in cmd_list)
    self.assert_("base" not in cmd_list)

########NEW FILE########
__FILENAME__ = core_test
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests that the core module functionality is present and functioning."""


import unittest

from django.test import TestCase as DjangoTestCase

from appengine_django import appid
from appengine_django import have_appserver


class AppengineDjangoTest(unittest.TestCase):
  """Tests that the helper module has been correctly installed."""

  def testAppidProvided(self):
    """Tests that application ID and configuration has been loaded."""
    self.assert_(appid is not None)

  def testAppserverDetection(self):
    """Tests that the appserver detection flag is present and correct."""
    # It seems highly unlikely that these tests would ever be run from within
    # an appserver.
    self.assertEqual(have_appserver, False)


class DjangoTestCaseTest(DjangoTestCase):
  """Tests that the tests can be subclassed from Django's TestCase class."""

  def testPassing(self):
    """Tests that tests with Django's TestCase class work."""
    self.assert_(True)

########NEW FILE########
__FILENAME__ = db_test
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests that the db module correctly initialises the API stubs."""


import unittest

from django.db import connection
from django.db.backends.appengine.base import DatabaseWrapper

from appengine_django import appid
from appengine_django.db import base


class DatastoreTest(unittest.TestCase):
  """Tests that the datastore stubs have been correctly setup."""

  def testDjangoDBConnection(self):
    """Tests that the Django DB connection is using our replacement."""
    self.assert_(isinstance(connection, DatabaseWrapper))

  def testDjangoDBConnectionStubs(self):
    """Tests that members required by Django are stubbed."""
    self.assert_(hasattr(connection, "features"))
    self.assert_(hasattr(connection, "ops"))

  def testDjangoDBErrorClasses(self):
    """Tests that the error classes required by Django are stubbed."""
    self.assert_(hasattr(base, "DatabaseError"))
    self.assert_(hasattr(base, "IntegrityError"))

  def testDatastorePath(self):
    """Tests that the datastore path contains the app name."""
    d_path, h_path = base.get_datastore_paths()
    self.assertNotEqual(-1, d_path.find("django_%s" % appid))
    self.assertNotEqual(-1, h_path.find("django_%s" % appid))

  def testTestInMemoryDatastorePath(self):
    """Tests that the test datastore is using the in-memory datastore."""
    td_path, th_path = base.get_test_datastore_paths()
    self.assert_(td_path is None)
    self.assert_(th_path is None)

  def testTestFilesystemDatastorePath(self):
    """Tests that the test datastore is on the filesystem when requested."""
    td_path, th_path = base.get_test_datastore_paths(False)
    self.assertNotEqual(-1, td_path.find("testdatastore"))
    self.assertNotEqual(-1, th_path.find("testdatastore"))

########NEW FILE########
__FILENAME__ = integration_test
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests that the core module functionality is present and functioning."""

import httplib
import logging
import os
import unittest
import sys
import threading

from django import http
from django import test
from django.test import client
from django.conf import settings

from google.appengine.tools import dev_appserver
from google.appengine.tools import dev_appserver_login

PORT = 8000
ROOT_PATH = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
APP_ID = 'google-app-engine-django'
LOGIN_URL = '/_ah/login'

# ########
# NOTE: All this stuff is expected to break with SDK updates
# TODO: get an interface for this into the SDK proper
# ########

def start_server(root_path=ROOT_PATH, port=PORT, app_id=APP_ID):
  dev_appserver.ApplicationLoggingHandler.InitializeTemplates(
      'HEADER', 'SCRIPT', 'MIDDLE', 'FOOTER')
  dev_appserver.SetupStubs(app_id,
                           login_url=LOGIN_URL,
                           datastore_path='/dev/null',
                           history_path='/dev/null',
                           blobstore_path='/dev/null',
                           clear_datastore=False)
  server = dev_appserver.CreateServer(ROOT_PATH,
                                      LOGIN_URL,
                                      port,
                                      '/unused/templates/path')

  server_thread = threading.Thread(target=server.serve_forever)
  server_thread.setDaemon(True)
  server_thread.start()
  return port

def RetrieveURL(method,
                host_port,
                relative_url,
                user_info=None,
                body=None,
                extra_headers=[]):
  """Access a URL over HTTP and returns the results.

  Args:
    method: HTTP method to use, e.g., GET, POST
    host_port: Tuple (hostname, port) of the host to contact.
    relative_url: Relative URL to access on the remote host.
    user_info: If not None, send this user_info tuple in an HTTP Cookie header
      along with the request; otherwise, no header is included. The user_info
      tuple should be in the form (email, admin) where:
        email: The user's email address.
        admin: True if the user should be an admin; False otherwise.
      If email is empty, it will be as if the user is not logged in.
    body: Request body to write to the remote server. Should only be used with
      the POST method any other methods that expect a message body.
    extra_headers: List of (key, value) tuples for headers to send on the
      request.

  Returns:
    Tuple (status, content, headers) where:
      status: HTTP status code returned by the remote host, e.g. 404, 200, 500
      content: Data returned by the remote host.
      headers: Dictionary mapping header names to header values (both strings).

    If an exception is raised while accessing the remote host, both status and
    content will be set to None.
  """
  url_host = '%s:%d' % host_port

  try:
    connection = httplib.HTTPConnection(url_host)

    try:
      connection.putrequest(method, relative_url)

      if user_info is not None:
        email, admin = user_info
        auth_string = '%s=%s' % (dev_appserver_login.COOKIE_NAME,
            dev_appserver_login.CreateCookieData(email, admin))
        connection.putheader('Cookie', auth_string)

      if body is not None:
        connection.putheader('Content-length', len(body))

      for key, value in extra_headers:
        connection.putheader(str(key), str(value))

      connection.endheaders()

      if body is not None:
        connection.send(body)

      response = connection.getresponse()
      status = response.status
      content = response.read()
      headers = dict(response.getheaders())

      return status, content, headers
    finally:
      connection.close()
  except (IOError, httplib.HTTPException, socket.error), e:
    logging.error('Encountered exception accessing HTTP server: %s', e)
    raise e

class AppEngineClientHandler(client.ClientHandler):
  def __init__(self, port):
    super(AppEngineClientHandler, self).__init__()
    self._port = port
    self._host = 'localhost'

  def __call__(self, environ):
    method = environ['REQUEST_METHOD']
    host_port = (self._host, self._port)
    relative_url = environ['PATH_INFO']
    if environ['QUERY_STRING']:
      relative_url += '?%s' % environ['QUERY_STRING']
    body = environ['wsgi.input'].read(environ.get('CONTENT_LENGTH', 0))
    headers = [] # Not yet supported
    status, content, headers = RetrieveURL(method,
                                           host_port,
                                           relative_url,
                                           body = body,
                                           extra_headers = headers)
    response = http.HttpResponse(content = content,
                                 status = status)
    for header, value in headers.iteritems():
      response[header] = value

    return response


class AppEngineClient(client.Client):
  def __init__(self, port, *args, **kw):
    super(AppEngineClient, self).__init__(*args, **kw)
    self.handler = AppEngineClientHandler(port=port)


class IntegrationTest(test.TestCase):
  """Tests that we can make a request."""

  def setUp(self):
    port = start_server()
    self.gae_client = AppEngineClient(port=port)


  def testBasic(self):
    """a request to the default page works in the dev_appserver"""
    rv = self.gae_client.get('/')
    self.assertEquals(rv.status_code, 200)

########NEW FILE########
__FILENAME__ = memcache_test
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Ensures the App Engine memcache API works as Django's memcache backend."""

import unittest

from django.core.cache import get_cache
from appengine_django import appid
from appengine_django import have_appserver


class AppengineMemcacheTest(unittest.TestCase):
  """Tests that the memcache backend works."""

  def setUp(self):
    """Get the memcache cache module so it is available to tests."""
    self._cache = get_cache("memcached://")

  def testSimpleSetGet(self):
    """Tests that a simple set/get operation through the cache works."""
    self._cache.set("test_key", "test_value")
    self.assertEqual(self._cache.get("test_key"), "test_value")

  def testDelete(self):
    """Tests that delete removes values from the cache."""
    self._cache.set("test_key", "test_value")
    self.assertEqual(self._cache.has_key("test_key"), True)
    self._cache.delete("test_key")
    self.assertEqual(self._cache.has_key("test_key"), False)

########NEW FILE########
__FILENAME__ = model_test
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests that the combined appengine and Django models function correctly."""


import unittest

from django import VERSION
from django.db.models import get_models
from django import forms

from google.appengine.ext.db import djangoforms
from google.appengine.ext import db

from appengine_django.models import BaseModel
from appengine_django.models import ModelManager
from appengine_django.models import ModelOptions
from appengine_django.models import RegistrationTestModel


class TestModelWithProperties(BaseModel):
  """Test model class for checking property -> Django field setup."""
  property1 = db.StringProperty()
  property2 = db.IntegerProperty()
  property3 = db.Reference()


class ModelTest(unittest.TestCase):
  """Unit tests for the combined model class."""

  def testModelRegisteredWithDjango(self):
    """Tests that a combined model class has been registered with Django."""
    self.assert_(RegistrationTestModel in get_models())

  def testDatastoreModelProperties(self):
    """Tests that a combined model class still has datastore properties."""
    self.assertEqual(3, len(TestModelWithProperties.properties()))

  def testDjangoModelClass(self):
    """Tests the parts of a model required by Django are correctly stubbed."""
    # Django requires model options to be found at ._meta.
    self.assert_(isinstance(RegistrationTestModel._meta, ModelOptions))
    # Django requires a manager at .objects
    self.assert_(isinstance(RegistrationTestModel.objects, ModelManager))
    # Django requires ._default_manager.
    self.assert_(hasattr(RegistrationTestModel, "_default_manager"))

  def testDjangoModelFields(self):
    """Tests that a combined model class has (faked) Django fields."""
    fields = TestModelWithProperties._meta.local_fields
    self.assertEqual(3, len(fields))
    # Check each fake field has the minimal properties that Django needs.
    for field in fields:
      # The Django serialization code looks for rel to determine if the field
      # is a relationship/reference to another model.
      self.assert_(hasattr(field, "rel"))
      # serialize is required to tell Django to serialize the field.
      self.assertEqual(True, field.serialize)
      if field.name == "property3":
        # Extra checks for the Reference field.
        # rel.field_name is used during serialization to find the field in the
        # other model that this field is related to. This should always be
        # 'key_name' for appengine models.
        self.assertEqual("key_name", field.rel.field_name)

  def testDjangoModelOptionsStub(self):
    """Tests that the options stub has the required properties by Django."""
    # Django requires object_name and app_label for serialization output.
    self.assertEqual("RegistrationTestModel",
                     RegistrationTestModel._meta.object_name)
    self.assertEqual("appengine_django", RegistrationTestModel._meta.app_label)
    # The pk.name member is required during serialization for dealing with
    # related fields.
    self.assertEqual("key_name", RegistrationTestModel._meta.pk.name)
    # The many_to_many method is called by Django in the serialization code to
    # find m2m relationships. m2m is not supported by the datastore.
    self.assertEqual([], RegistrationTestModel._meta.many_to_many)

  def testDjangoModelManagerStub(self):
    """Tests that the manager stub acts as Django would expect."""
    # The serialization code calls model.objects.all() to retrieve all objects
    # to serialize.
    self.assertEqual([], list(RegistrationTestModel.objects.all()))

  def testDjangoModelPK(self):
    """Tests that each model instance has a 'primary key' generated."""
    obj = RegistrationTestModel(key_name="test")
    obj.put()
    pk = obj._get_pk_val()
    self.assert_(pk)
    new_obj = RegistrationTestModel.get(pk)
    self.assertEqual(obj.key(), new_obj.key())

  def testModelFormPatched(self):
    """Tests that the Django ModelForm is being successfully patched."""
    self.assertEqual(djangoforms.ModelForm, forms.ModelForm)

########NEW FILE########
__FILENAME__ = serialization_test
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests that the serialization modules are functioning correctly.

In particular, these tests verify that the modifications made to the standard
Django serialization modules function correctly and that the combined datastore
and Django models can be dumped and loaded to all of the provided formats.
"""


import os
import re
import unittest
from StringIO import StringIO

from django.core import serializers

from google.appengine.ext import db
from appengine_django.models import BaseModel


class ModelA(BaseModel):
  description = db.StringProperty()


class ModelB(BaseModel):
  description = db.StringProperty()
  friend = db.Reference(ModelA)

class ModelC(BaseModel):
  dt_value = db.DateTimeProperty(auto_now_add=True)
  d_value = db.DateProperty(auto_now_add=True)
  t_value = db.TimeProperty(auto_now_add=True)


class TestAllFormats(type):

  def __new__(cls, name, bases, attrs):
    """Extends base test functions to be called for every serialisation format.

    Looks for functions matching 'run.*Test', where the wildcard in the middle
    matches the desired test name and ensures that a test case is setup to call
    that function once for every defined serialisation format. The test case
    that is created will be called 'test<format><name>'. Eg, for the function
    'runKeyedObjectTest' functions like 'testJsonKeyedObject' will be created.
    """
    test_formats = serializers.get_serializer_formats()
    test_formats.remove("python")  # Python serializer is only used indirectly.

    for func_name in attrs.keys():
      m = re.match("^run(.*)Test$", func_name)
      if not m:
        continue
      for format in test_formats:
        test_name = "test%s%s" % (format.title(), m.group(1))
        test_func = eval("lambda self: getattr(self, \"%s\")(\"%s\")" %
                         (func_name, format))
        attrs[test_name] = test_func

    return super(TestAllFormats, cls).__new__(cls, name, bases, attrs)


class SerializationTest(unittest.TestCase):
  """Unit tests for the serialization/deserialization functionality.

  Tests that every loaded serialization format can successfully dump and then
  reload objects without the objects changing.
  """
  __metaclass__ = TestAllFormats

  def compareObjects(self, orig, new, format="unknown"):
    """Compares two objects to ensure they are identical.

    Args:
      orig: The original object, must be an instance of db.Model.
      new: The new object, must be an instance of db.Model.
      format: The serialization format being tested, used to make error output
        more helpful.

    Raises:
      The function has no return value, but will raise assertion errors if the
      objects do not match correctly.
    """
    if orig.key().name():
      # Only compare object keys when the key is named. Key IDs are not static
      # and will change between dump/load. If you want stable Keys they need to
      # be named!
      self.assertEqual(orig.key(), new.key(),
                       "keys not equal after %s serialization: %s != %s" %
                       (format, repr(orig.key()), repr(new.key())))

    for key in orig.properties().keys():
      oval = getattr(orig, key)
      nval = getattr(new, key)
      if isinstance(orig.properties()[key], db.Reference):
        # Need to compare object keys not the objects themselves.
        oval = oval.key()
        nval = nval.key()
      self.assertEqual(oval, nval, "%s attribute differs after %s "
                       "serialization: %s != %s" % (key, format, oval, nval))

  def doSerialisationTest(self, format, obj, rel_attr=None, obj_ref=None):
    """Runs a serialization test on an object for the specified format.

    Args:
      format: The name of the Django serialization class to use.
      obj: The object to {,de}serialize, must be an instance of db.Model.
      rel_attr: Name of the attribute of obj references another model.
      obj_ref: The expected object reference, must be an instance of db.Model.

    Raises:
      The function has no return value but raises assertion errors if the
      object cannot be successfully serialized and then deserialized back to an
      identical object. If rel_attr and obj_ref are specified the deserialized
      object must also retain the references from the original object.
    """
    serialised = serializers.serialize(format, [obj])
    # Try and get the object back from the serialized string.
    result = list(serializers.deserialize(format, StringIO(serialised)))
    self.assertEqual(1, len(result),
                     "%s serialization should create 1 object" % format)
    result[0].save()  # Must save back into the database to get a Key.
    self.compareObjects(obj, result[0].object, format)
    if rel_attr and obj_ref:
      rel = getattr(result[0].object, rel_attr)
      if callable(rel):
        rel = rel()
      self.compareObjects(rel, obj_ref, format)

  def doLookupDeserialisationReferenceTest(self, lookup_dict, format):
    """Tests the Key reference is loaded OK for a format.

    Args:
      lookup_dict: A dictionary indexed by format containing serialized strings
        of the objects to load.
      format: The format to extract from the dict and deserialize.

    Raises:
      This function has no return value but raises assertion errors if the
      string cannot be deserialized correctly or the resulting object does not
      reference the object correctly.
    """
    if format not in lookup_dict:
      # Check not valid for this format.
      return
    obj = ModelA(description="test object", key_name="test")
    obj.put()
    s = lookup_dict[format]
    result = list(serializers.deserialize(format, StringIO(s)))
    self.assertEqual(1, len(result), "expected 1 object from %s" % format)
    result[0].save()
    self.compareObjects(obj, result[0].object.friend, format)

  def doModelKeyDeserialisationReferenceTest(self, lookup_dict, format):
    """Tests a model with a key can be loaded OK for a format.

    Args:
      lookup_dict: A dictionary indexed by format containing serialized strings
        of the objects to load.
      format: The format to extract from the dict and deserialize.

    Returns:
      This function has no return value but raises assertion errors if the
      string cannot be deserialized correctly or the resulting object is not an
      instance of ModelA with a key named 'test'.
    """
    if format not in lookup_dict:
      # Check not valid for this format.
      return
    s = lookup_dict[format]
    result = list(serializers.deserialize(format, StringIO(s)))
    self.assertEqual(1, len(result), "expected 1 object from %s" % format)
    result[0].save()
    self.assert_(isinstance(result[0].object, ModelA))
    self.assertEqual("test", result[0].object.key().name())

  # Lookup dicts for the above (doLookupDeserialisationReferenceTest) function.
  SERIALIZED_WITH_KEY_AS_LIST = {
      "json": """[{"pk": "agR0ZXN0chMLEgZNb2RlbEIiB21vZGVsYmkM", """
              """"model": "tests.modelb", "fields": {"description": "test", """
              """"friend": ["ModelA", "test"] }}]""",
      "yaml": """- fields: {description: !!python/unicode 'test', friend: """
              """ [ModelA, test]}\n  model: tests.modelb\n  pk: """
              """ agR0ZXN0chMLEgZNb2RlbEEiB21vZGVsYWkM\n"""
  }
  SERIALIZED_WITH_KEY_REPR = {
      "json": """[{"pk": "agR0ZXN0chMLEgZNb2RlbEIiB21vZGVsYmkM", """
              """"model": "tests.modelb", "fields": {"description": "test", """
              """"friend": "datastore_types.Key.from_path("""
              """'ModelA', 'test')" }}]""",
      "yaml": """- fields: {description: !!python/unicode 'test', friend: """
              """\'datastore_types.Key.from_path("ModelA", "test")\'}\n  """
              """model: tests.modelb\n  pk: """
              """ agR0ZXN0chMLEgZNb2RlbEEiB21vZGVsYWkM\n"""
  }

  # Lookup dict for the doModelKeyDeserialisationReferenceTest function.
  MK_SERIALIZED_WITH_LIST = {
      "json": """[{"pk": ["ModelA", "test"], "model": "tests.modela", """
              """"fields": {}}]""",
      "yaml": """-\n fields: {description: null}\n model: tests.modela\n """
              """pk: [ModelA, test]\n"""
  }
  MK_SERIALIZED_WITH_KEY_REPR = {
      "json": """[{"pk": "datastore_types.Key.from_path('ModelA', 'test')", """
              """"model": "tests.modela", "fields": {}}]""",
      "yaml": """-\n fields: {description: null}\n model: tests.modela\n """
              """pk: \'datastore_types.Key.from_path("ModelA", "test")\'\n"""
  }
  MK_SERIALIZED_WITH_KEY_AS_TEXT = {
      "json": """[{"pk": "test", "model": "tests.modela", "fields": {}}]""",
      "yaml": """-\n fields: {description: null}\n model: tests.modela\n """
              """pk: test\n"""
  }

  # Lookup dict for the function.
  SERIALIZED_WITH_NON_EXISTANT_PARENT = {
      "json": """[{"pk": "ahhnb29nbGUtYXBwLWVuZ2luZS1kamFuZ29yIgsSBk1vZG"""
              """VsQiIGcGFyZW50DAsSBk1vZGVsQSIEdGVzdAw", """
              """"model": "tests.modela", "fields": """
              """{"description": null}}]""",
      "yaml": """- fields: {description: null}\n  """
              """model: tests.modela\n  """
              """pk: ahhnb29nbGUtYXBwLWVuZ2luZS1kamFuZ29yIgsSBk1"""
              """vZGVsQiIGcGFyZW50DAsSBk1vZGVsQSIEdGVzdAw\n""",
      "xml":  """<?xml version="1.0" encoding="utf-8"?>\n"""
              """<django-objects version="1.0">\n"""
              """<entity kind="tests.modela" key="ahhnb29nbGUtYXBwL"""
              """WVuZ2luZS1kamFuZ29yIgsSBk1vZGVsQiIGcGFyZW50DA"""
              """sSBk1vZGVsQSIEdGVzdAw">\n  """
              """<key>tag:google-app-engine-django.gmail.com,"""
              """2008-05-13:ModelA[ahhnb29nbGUtYXBwLWVuZ2luZS1kam"""
              """FuZ29yIgsSBk1vZGVsQiIGcGFyZW50DAsSBk1vZGVsQSIEdGVzdAw"""
              """]</key>\n  <property name="description" """
              """type="null"></property>\n</entity>\n</django-objects>"""
  }

  # The following functions are all expanded by the metaclass to be run once
  # for every registered Django serialization module.

  def runKeyedObjectTest(self, format):
    """Test serialization of a basic object with a named key."""
    obj = ModelA(description="test object", key_name="test")
    obj.put()
    self.doSerialisationTest(format, obj)

  def runObjectWithIdTest(self, format):
    """Test serialization of a basic object with a numeric ID key."""
    obj = ModelA(description="test object")
    obj.put()
    self.doSerialisationTest(format, obj)

  def runObjectWithReferenceTest(self, format):
    """Test serialization of an object that references another object."""
    obj = ModelA(description="test object", key_name="test")
    obj.put()
    obj2 = ModelB(description="friend object", friend=obj)
    obj2.put()
    self.doSerialisationTest(format, obj2, "friend", obj)

  def runObjectWithParentTest(self, format):
    """Test serialization of an object that has a parent object reference."""
    obj = ModelA(description="parent object", key_name="parent")
    obj.put()
    obj2 = ModelA(description="child object", key_name="child", parent=obj)
    obj2.put()
    self.doSerialisationTest(format, obj2, "parent", obj)

  def runObjectWithNonExistantParentTest(self, format):
    """Test deserialization of an object referencing a non-existant parent."""
    self.doModelKeyDeserialisationReferenceTest(
        self.SERIALIZED_WITH_NON_EXISTANT_PARENT, format)

  def runCreateKeyReferenceFromListTest(self, format):
    """Tests that a reference specified as a list in json/yaml can be loaded OK."""
    self.doLookupDeserialisationReferenceTest(self.SERIALIZED_WITH_KEY_AS_LIST,
                                              format)

  def runCreateKeyReferenceFromReprTest(self, format):
    """Tests that a reference specified as repr(Key) in can loaded OK."""
    self.doLookupDeserialisationReferenceTest(self.SERIALIZED_WITH_KEY_REPR,
                                              format)

  def runCreateModelKeyFromListTest(self, format):
    """Tests that a model key specified as a list can be loaded OK."""
    self.doModelKeyDeserialisationReferenceTest(self.MK_SERIALIZED_WITH_LIST,
                                                format)

  def runCreateModelKeyFromReprTest(self, format):
    """Tests that a model key specified as a repr(Key) can be loaded OK."""
    self.doModelKeyDeserialisationReferenceTest(
        self.MK_SERIALIZED_WITH_KEY_REPR, format)

  def runCreateModelKeyFromTextTest(self, format):
    """Tests that a reference specified as a plain key_name loads OK."""
    self.doModelKeyDeserialisationReferenceTest(
        self.MK_SERIALIZED_WITH_KEY_AS_TEXT, format)

  def runDateTimeTest(self, format):
    """Tests that db.DateTimeProperty and related can be correctly handled."""
    obj = ModelC()
    obj.put()
    self.doSerialisationTest(format, obj)


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = default_public
from error.models import Error

from error import signals

def default_public(instance, **kw):
    instance.public = True
    instance.save()

signals.error_created.connect(default_public, dispatch_uid="default_public")

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse

from app.tests import test_data as data
from error.models import Error, Group
from error import signals

from custom.examples import default_public

class ErrorTests(TestCase):
    # test the view for writing errors
    def setUp(self):
        for error in Error.all(): error.delete()

    def testNotDefaultAsPublic(self):
        signals.error_created.disconnect(default_public.default_public, dispatch_uid="default_public")
        
        c = Client()
        assert not Error.objects.all().count()
        c.post(reverse("error-post"), data)
        assert Error.objects.all().count() == 1
        assert Error.objects.all()[0].public == False
        
    def testDefaultAsPublic(self):
        signals.error_created.connect(default_public.default_public, dispatch_uid="default_public")
        
        c = Client()
        assert not Error.objects.all().count()
        c.post(reverse("error-post"), data)
        assert Error.objects.all().count() == 1
        assert Error.objects.all()[0].public == True
        
        signals.error_created.disconnect(default_public.default_public, dispatch_uid="default_public")
########NEW FILE########
__FILENAME__ = agent
import re

from ConfigParser import SafeConfigParser as ConfigParser
from StringIO import StringIO

from google.appengine.api.urlfetch import fetch, DownloadError
from google.appengine.api import memcache
from app.utils import log

class Browser(object):
    def __init__(self, capabilities):
        self.lazy_flag = True
        self.cap = capabilities

    def parse(self):
        for name, value in self.cap.items():
            if name in ["tables", "aol", "javaapplets",
                       "activexcontrols", "backgroundsounds",
                       "vbscript", "win16", "javascript", "cdf",
                       "wap", "crawler", "netclr", "beta",
                        "iframes", "frames", "stripper", "wap"]:
                self.cap[name] = (value.strip().lower() == "true")
            elif name in ["ecmascriptversion", "w3cdomversion"]:
                self.cap[name] = float(value)
            elif name in ["css"]:
                self.cap[name] = int(value)
            else:
                self.cap[name] = value
        self.lazy_flag = False

    def __repr__(self):
        if self.lazy_flag: self.parse()
        return repr(self.cap)

    def get(self, name, default=None):
        if self.lazy_flag: self.parse()
        try:
            return self[name]
        except KeyError:
            return default

    def __getitem__(self, name):
        if self.lazy_flag: self.parse()
        return self.cap[name.lower()]

    def keys(self):
        return self.cap.keys()

    def items(self):
        if self.lazy_flag: self.parse()
        return self.cap.items()

    def values(self):
        if self.lazy_flag: self.parse()
        return self.cap.values()

    def __len__(self):
        return len(self.cap)

    def supports(self, feature):
        value = self.cap.get(feature)
        if value == None:
            return False
        return value

    def features(self):
        l = []
        for f in ["tables", "frames", "iframes", "javascript",
                  "cookies", "w3cdomversion", "wap"]:
            if self.supports(f):
                l.append(f)
        if self.supports_java():
            l.append("java")
        if self.supports_activex():
            l.append("activex")
        css = self.css_version()
        if css > 0:
            l.append("css1")
        if css > 1:
            l.append("css2")
        return l

    def supports_tables(self):
        return self.supports("frames")

    def supports_iframes(self):
        return self.supports("iframes")

    def supports_frames(self):
        return self.supports("frames")

    def supports_java(self):
        return self.supports("javaapplets")

    def supports_javascript(self):
        return self.supports("javascript")

    def supports_vbscript(self):
        return self.supports("vbscript")

    def supports_activex(self):
        return self.supports("activexcontrols")

    def supports_cookies(self):
        return self.supports("cookies")

    def supports_wap(self):
        return self.supports("wap")

    def css_version(self):
        return self.get("css", 0)

    def version(self):
        major = self.get("majorver")
        minor = self.get("minorver")
        if major and minor:
            return (major, minor)
        elif major:
            return (major, None)
        elif minor:
            return (None, minor)
        else:
            ver = self.get("version")
            if ver and "." in ver:
                return tuple(ver.split(".", 1))
            elif ver:
                return (ver, None)
            else:
                return (None, None)

    def dom_version(self):
        return self.get("w3cdomversion", 0)


    def is_bot(self):
        return self.get("crawler") == True

    def is_mobile(self):
        return self.get("ismobiledevice") == True

    def name(self):
        return self.get("browser")

    def platform(self):
        return self.get("platform")

class BrowserCapabilities(object):

    def __new__(cls, *args, **kwargs):
        # Only create one instance of this clas
        if "instance" not in cls.__dict__:
            cls.instance = object.__new__(cls, *args, **kwargs)
        return cls.instance

    def __init__(self):
        self.cache = {}
        self.parse()

    def parse(self):
        key = "browser-capabilities-raw"
        raw = memcache.get(key)
        # if the data isn't there, download it
        if raw is None:
            log("Fetching from browser capabilities")
            try:
                data = fetch("http://www.areciboapp.com/static/browscap.ini")
            except DownloadError:
                data = None
            if data and data.status_code == 200:
                # that should be one week (1 min > 1 hour > 1 day > 1 week)
                log("...succeeded")
                raw = data.content
                memcache.set(key, raw, 60 * 60 * 24 * 7)
            else:
                log("...failed")
                # try again in 1 hour if there was a problem
                memcache.set(key, "", 60 * 60)
                raw = ""
        else:
            log("Using cached browser capabilities")

        string = StringIO(raw)
        cfg = ConfigParser()
        cfg.readfp(string)

        self.sections = []
        self.items = {}
        self.browsers = {}
        parents = set()
        for name in cfg.sections():
            qname = name
            for unsafe in list("^$()[].-"):
                qname = qname.replace(unsafe, "\%s" % unsafe)
            qname = qname.replace("?", ".").replace("*", ".*?")
            qname = "^%s$" % qname
            sec_re = re.compile(qname)
            sec = dict(regex=qname)
            sec.update(cfg.items(name))
            p = sec.get("parent")
            if p: parents.add(p)
            self.browsers[name] = sec
            if name not in parents:
                self.sections.append(sec_re)
            self.items[sec_re] = sec


    def query(self, useragent):
        useragent = useragent.replace(' \r\n', '')
        b = self.cache.get(useragent)
        if b: return b

        if not hasattr(self, "sections"):
            return None

        for sec_pat in self.sections:
            if sec_pat.match(useragent):
                browser = dict(agent=useragent)
                browser.update(self.items[sec_pat])
                parent = browser.get("parent")
                while parent:
                    items = self.browsers[parent]
                    for key, value in items.items():
                        if key not in browser.keys():
                            browser[key] = value
                        elif key == "browser" and value != "DefaultProperties":
                            browser["category"] = value # Wget, Godzilla -> Download Managers
                    parent = items.get("parent")
                if browser.get("browser") != "Default Browser":
                    b = Browser(browser)
                    self.cache[useragent] = b
                    return b
        self.cache[useragent] = None

    __call__ = query

def get():
    key = "browser-capabilities-parsed"
    parsed = memcache.get(key)
    if parsed is None:
        parsed = BrowserCapabilities()
        # that should be one week (1 min > 1 hour > 1 day > 1 week)
        memcache.set(key, parsed, 60 * 60 * 24 * 7)
    return parsed

def test():
    bc = get()
    for agent in [
        "Mozilla/5.0 (compatible; Konqueror/3.5; Linux; X11; de) KHTML/3.5.2 (like Gecko) Kubuntu 6.06 Dapper",
        "Mozilla/5.0 (X11; U; Linux i686; de; rv:1.8.0.5) Gecko/20060731 Ubuntu/dapper-security Firefox/1.5.0.5",
        "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.7.12) Gecko/20060216 Debian/1.7.12-1.1ubuntu2",
        "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.0.5) Gecko/20060731 Ubuntu/dapper-security Epiphany/2.14 Firefox/1.5.0.5",
        "Opera/9.00 (X11; Linux i686; U; en)",
        "Wget/1.10.2",
        "Mozilla/5.0 (X11; Linux i686; U;) Gecko/20051128 Kazehakase/0.3.3 Debian/0.3.3-1",
        "Mozilla/5.0 (X11; U; Linux i386) Gecko/20063102 Galeon/1.3test",
        "Mozilla/5.0 (Macintosh; U; PPC Mac OS X 10_5_4; en-us) AppleWebKit/525.18 (KHTML, like Gecko) Version/3.1.2 Safari/525.20.1",
        "Mozilla/4.0 (compatible; MSIE 6.0; Windows 98)" # Tested under Wine
        """Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.5; en-US;  \r
rv:1.9.0.5) Gecko/2008120121 Firefox/3.0.5,gzip(gfe)""",
        "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.5; en-US; rv:1.9.0.5) Gecko/2008120121 Firefox/3.0.5,gzip(gfe)",
        "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_5_6; en-us) AppleWebKit/525.27.1 (KHTML, like Gecko) Version/3.2.1 Safari/525.27.1,gzip(gfe)"
      ]:
        b = bc(agent)
        if not b:
            print "! Not found", agent
        else:
            print b.name(), b.version(), b.get("category", ""), b.features()
########NEW FILE########
__FILENAME__ = feeds
from django.contrib.syndication.views import Feed
from django.core import serializers
from django.http import HttpResponse

from app.utils import has_private_key
from error.views import get_filtered, get_group_filtered

class base(Feed):
    title = "Arecibo Errors"
    link = "/list/"
    description = "Arecibo Errors"
    subtitle = "Arecibo Errors"

    def __init__(self, *args, **kw):
        Feed.__init__(self, *args, **kw)
        self.request = None

    def items(self):
        form, queryset = get_filtered(self.request)
        return queryset[:20]

    def item_title(self, item): return item.title
    def item_description(self, item): return item.description
    def item_pubdate(self, item): return item.timestamp

@has_private_key
def atom(request):
    feedgen = base()
    feedgen.request = request
    return feedgen(request)

@has_private_key
def json(request):
    form, queryset = get_filtered(request)
    response = HttpResponse(mimetype="text/javascript")
    json_serializer = serializers.get_serializer("json")()
    json_serializer.serialize(queryset[:20], ensure_ascii=False, stream=response)
    return response

class gropu(Feed):
    title = "Arecibo Errors by Groups"
    link = "/groups/"
    description = "Arecibo Errors by Groups"
    subtitle = "Arecibo Errors by Groups"

    def __init__(self, *args, **kw):
        Feed.__init__(self, *args, **kw)
        self.request = None

    def items(self):
        form, queryset = get_filtered(self.request)
        return queryset[:20]

    def item_title(self, item): return item.title
    def item_description(self, item): return item.description
    def item_pubdate(self, item): return item.timestamp

@has_private_key
def group_atom(request):
    feedgen = base()
    feedgen.request = request
    return feedgen(request)

@has_private_key
def group_json(request):
    form, queryset = get_group_filtered(request)
    response = HttpResponse(mimetype="text/javascript")
    json_serializer = serializers.get_serializer("json")()
    json_serializer.serialize(queryset[:20], ensure_ascii=False, stream=response)
    return response
########NEW FILE########
__FILENAME__ = forms
from django import forms

from app.fields import OurModelChoiceField
from app.forms import Form
from app.utils import safe_int

from google.appengine.ext import db

from projects.models import ProjectURL
from error.models import Group

read_choices = (("", "All"), ("True", 'Read only'), ("False", 'Unread only'))
priority_choices = [ (r, r) for r in range(1, 11)]
priority_choices.insert(0, ("", "All"))

status_choices = ['500', '404', '100', '101', '102', '200', '201', '202', '203',
'204', '205', '206', '207', '226', '300', '301', '302', '303', '304',
'305', '307', '400', '401', '402', '403', '405', '406', '407',
'408', '409', '410', '411', '412', '413', '414', '415', '416', '417',
'422', '423', '424', '426', '501', '502', '503', '504', '505',
'507', '510']
status_choices = [ (r, r) for r in status_choices ]
status_choices.insert(0, ("", "All"))

err = "You can cannot query on path and start or end dates, this is an App Engine limitation."

class Filter(Form):
    """ Base for the filters """
    inequality = ""

    def as_query(self, table):
        """ This is getting a bit complicated """
        args, gql = [], []
        counter = 1

        for k, v in self.cleaned_data.items():
            # if there's a value handler, use it
            lookup = getattr(self, "handle_%s" % k, None)
            if lookup:  v = lookup(v)
            # if there's a filter handler user it
            lfilter = getattr(self, "filter_%s" % k, None)
            if lfilter:
                # will return a filter and args..
                newfilter, newargs = lfilter(v, args)
                gql.append(newfilter)
                args.extend(newargs)
                counter += len(newargs)
            else:
                gql.append(" %s = :%s " % (k, counter))
                args.append(v)
                counter += 1

        conditions = " AND ".join(gql)
        if conditions: conditions = "WHERE %s" % conditions
        conditions = "SELECT * FROM %s %s ORDER BY %s timestamp DESC" % (table, conditions, self.inequality)
        query = db.GqlQuery(conditions, *args)
        return query

    def clean(self):
        data = {}
        for k, v in self.cleaned_data.items():
            if not v: continue
            data[k] = v

        return data

class GroupForm(Filter):
    project_url = OurModelChoiceField(required=False,
                                      model=ProjectURL,
                                      queryset=ProjectURL.objects.all())

    def as_query(self):
        return super(GroupForm, self).as_query("Group")

    def handle_project_url(self, value):
        return value.key()
    
class ErrorForm(Filter):
    priority = forms.ChoiceField(choices=priority_choices, widget=forms.Select, required=False)
    status = forms.ChoiceField(choices=status_choices, widget=forms.Select, required=False)
    read = forms.ChoiceField(choices=read_choices, widget=forms.Select, required=False)
    start = forms.DateField(required=False, label="Start date",
        widget=forms.DateInput(attrs={"class":"date",}))
    end = forms.DateField(required=False, label="End date",
        widget=forms.DateInput(attrs={"class":"date",}))
    query = forms.CharField(required=False, label="Path")
    domain = forms.CharField(required=False)
    uid = forms.CharField(required=False)
    group = forms.CharField(required=False)

    def clean(self):
        data = {}
        for k, v in self.cleaned_data.items():
            if not v: continue
            data[k] = v

        if "query" in data:
            if "start" in data or "end" in data:
                raise forms.ValidationError(err)

        return data

    def handle_read(self, value):
        return {"False":False, "True":True}.get(value, None)

    def filter_start(self, value, args):
        return "timestamp >= :%d" % (len(args)+1), [value,]

    def filter_end(self, value, args):
        return "timestamp <= :%d" % (len(args)+1), [value,]

    def handle_priority(self, value):
        return safe_int(value)

    def filter_query(self, value, args):
        self.inequality = "query,"
        x = len(args)
        return "query >= :%d AND query < :%d" % (x+1, x+2), [value, value + u"\ufffd"]

    def handle_group(self, value):
        try:
            return Group.get(value)
        except IndexError:
            pass

    def as_query(self):
        return super(ErrorForm, self).as_query("Error")

########NEW FILE########
__FILENAME__ = listeners
import md5

from app.utils import safe_string, log
from error.models import Group, Error

from error.agent import get
from error import signals

def generate_key(instance):
    keys = ["type", "server", "msg", "status", "domain"]
    hsh = None

    for key in keys:
        value = safe_string(getattr(instance, key))
        if value:
            if not hsh:
                hsh = md5.new()
            hsh.update(value.encode("ascii", "ignore"))

    return hsh

def default_grouping(instance, **kw):
    """ Given an error, see if we can fingerprint it and find similar ones """
    log("Firing signal: default_grouping")

    hsh = generate_key(instance)
    if hsh:
        digest = hsh.hexdigest()
        try:
            created = False
            group = Group.all().filter("uid = ", digest)[0]
            group.count = Error.all().filter("group = ", group).count() + 1
            group.save()
        except IndexError:
            created = True
            group = Group()
            group.uid = digest
            group.count = 1
            group.save()

        instance.group = group
        instance.save()

        if created:
            signals.group_assigned.send(sender=group.__class__, instance=group)

signals.error_created.connect(default_grouping, dispatch_uid="default_grouping")

def default_browser_parsing(instance, **kw):
    # prevent an infinite loop
    log("Firing signal: default_browser_parsing")
    
    if instance.user_agent:
        bc = get()
        b = bc(instance.user_agent)
        if b:
            instance.user_agent_short = b.name()
            instance.operating_system = b.platform()

    instance.user_agent_parsed = True
    instance.save()

signals.error_created.connect(default_browser_parsing, dispatch_uid="default_browser_parsing")

########NEW FILE########
__FILENAME__ = models
from django.core.urlresolvers import reverse

from datetime import datetime

from google.appengine.ext import db
from google.appengine.api.labs import taskqueue

from error.signals import group_created
from projects.models import ProjectURL

from app.utils import trunc_string
from app.base import Base
import os

class Group(Base):
    """ A grouping of errors """
    uid = db.StringProperty()
    timestamp = db.DateTimeProperty()
    project_url = db.ReferenceProperty(ProjectURL, required=False)
    count = db.IntegerProperty(default=0)

    def sample(self):
        try:
            return Error.all().filter("group = ", self).order("-timestamp")[0]
        except IndexError:
            return None

    def save(self, *args, **kw):
        created = not getattr(self, "id", None)
        if created:
            self.timestamp = datetime.now()
        self.put()
        if created:
            group_created.send(sender=self.__class__, instance=self)

class Error(Base):
    # time error was received by this server
    timestamp = db.DateTimeProperty()
    timestamp_date = db.DateProperty()

    ip = db.StringProperty()
    user_agent = db.StringProperty()
    user_agent_short = db.StringProperty()
    user_agent_parsed = db.BooleanProperty(default=False)
    operating_system = db.StringProperty()

    priority = db.IntegerProperty()
    status = db.StringProperty()

    raw = db.StringProperty()
    domain = db.StringProperty()
    server = db.StringProperty()
    query = db.StringProperty()
    protocol = db.StringProperty()

    uid = db.StringProperty()
    type = db.StringProperty()
    msg = db.TextProperty()
    traceback = db.TextProperty()

    errors = db.TextProperty(default="")

    # time error was recorded on the client server
    error_timestamp = db.DateTimeProperty()
    request = db.TextProperty()
    username = db.StringProperty()

    group = db.ReferenceProperty(Group)

    read = db.BooleanProperty(default=False)

    create_signal_sent = db.BooleanProperty(default=False)

    public = db.BooleanProperty(default=False)

    def get_absolute_url(self):
        return reverse("error-view", args=[self.id,])

    def has_group(self):
        try:
            return self.group
        except db.Error:
            return []

    def get_similar(self, limit=5):
        try:
            return Error.all().filter("group = ", self.group).filter("__key__ !=", self.key())[:limit]
        except db.Error:
            return []

    def delete(self):
        try:
            if self.group:
                self.group.count = self.group.count - 1
                if self.group.count < 1:
                    self.group.delete()
        except db.Error:
            pass
        super(Error, self).delete()

    @property
    def title(self):
        """ Try to give a nice title to describe the error """
        strng = ""
        if self.type:
            strng = self.type
            if self.server:
                if self.status:
                    strng = "%s" % (strng)
                if not strng:
                    strng = "Error"
                strng = "%s on %s" % (strng, self.server)
        elif self.status:
            strng = self.status
            if self.server:
                strng = "%s on server %s" % (strng, self.server)
        elif self.raw:
            strng = self.raw
        else:
            strng = self.error_timestamp.isoformat()
        if self.uid:
            strng = "%s" % (strng)
        return strng

    @property
    def description(self):
        return self.msg or ""

    def save(self, *args, **kw):
        created = not getattr(self, "id", None)
        self.put()
        if created and not "dont_send_signals" in kw:
            if os.environ.get('SERVER_SOFTWARE', '').startswith('Dev'):
                # send the signal, otherwise we have to clicking buttons
                # to process the queue
                from error.views import send_signal
                send_signal(None, self.id)
            else:
                # enqueue the send notification
                # if development
                taskqueue.add(url=reverse("error-created", args=[self.id,]))

from notifications import registry
registry.register(Error, "Error")
########NEW FILE########
__FILENAME__ = signals
import django.dispatch

error_created = django.dispatch.Signal(providing_args=["instance",])
group_created = django.dispatch.Signal(providing_args=["instance",])
group_assigned = django.dispatch.Signal(providing_args=["instance",])
########NEW FILE########
__FILENAME__ = tests
# -*- coding: UTF8 -*-
from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse

from app.tests import test_data as data
from app.utils import trunc_string
from error.models import Error, Group

class ErrorTests(TestCase):
    # test the view for writing errors
    def setUp(self):
        for error in Error.all(): error.delete()

    def testBasic(self):
        c = Client()
        assert not Error.all().count()
        c.post(reverse("error-post"), data)
        assert Error.all().count() == 1

    def testOverPriority(self):
        c = Client()
        assert not Error.all().count()
        ldata = data.copy()
        ldata["priority"] = 123
        c.post(reverse("error-post"), ldata)
        assert Error.all().count() == 1

    def testStringPriority(self):
        c = Client()
        assert not Error.all().count()
        ldata = data.copy()
        ldata["priority"] = "test"
        c.post(reverse("error-post"), ldata)
        assert Error.all().count() == 1

    def testNoPriority(self):
        c = Client()
        assert not Error.all().count()
        ldata = data.copy()
        del ldata["priority"]
        c.post(reverse("error-post"), ldata)
        assert Error.all().count() == 1

    def testGroup(self):
        c = Client()
        c.post(reverse("error-post"), data)
        assert Group.all().count() == 1, "Got %s groups, not 1" % Group.all().count()
        c.post(reverse("error-post"), data)
        assert Group.all().count() == 1
        new_data = data.copy()
        new_data["status"] = 402
        c.post(reverse("error-post"), new_data)
        assert Group.all().count() == 2

        # and test similar
        assert not Error.all()[2].get_similar()
        assert len(Error.all()[1].get_similar()) == 1
        assert len(Error.all()[1].get_similar()) == 1

    def testGroupDelete(self):
        c = Client()
        c.post(reverse("error-post"), data)
        assert Group.all().count() == 1, "Got %s groups, not 1" % Group.all().count()
        assert Error.all().count() == 1
        Error.all()[0].delete()
        assert Group.all().count() == 0

    def testBrowser(self):
        c = Client()
        assert not Error.all().count()
        ldata = data.copy()
        ldata["user_agent"] = "Mozilla/5.0 (compatible; Konqueror/3.5; Linux; X11; de) KHTML/3.5.2 (like Gecko) Kubuntu 6.06 Dapper"
        c.post(reverse("error-post"), ldata)
        assert Error.all().count() == 1
        assert Error.all()[0].user_agent_short == "Konqueror"
        assert Error.all()[0].user_agent_parsed == True
        assert Error.all()[0].operating_system == "Linux"

    # http://github.com/andymckay/arecibo/issues#issue/14
    def testUnicodeTraceback(self):
        c = Client()
        assert not Error.all().count()
        ldata = data.copy()
        ldata["traceback"] = "ɷo̚حٍ"
        c.post(reverse("error-post"), ldata)
        assert Error.all().count() == 1
    
class TagsTests(TestCase):
    def testTrunc(self):
        assert trunc_string("Test123", 5) == "Te..."
        assert trunc_string(None, 5) == ""
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# if you put the key in here it will get exposed in errors
# so probably
urlpatterns = patterns('',
    url(r'^feed/.*?/json/$', 'error.feeds.json', name="json"),
    url(r'^feed/.*?/$', 'error.feeds.atom', name="rss"),
    url(r'^group/feed/.*?/json/$', 'error.feeds.group_json', name="json"),
    url(r'^group/feed/.*?/$', 'error.feeds.group_atom', name="rss"),
    url(r'^list/$', 'error.views.errors_list', name="error-list"),
    url(r'^list/snippet/$', 'error.views.errors_snippet', name="error-snippet"),
    url(r'^groups/$', 'error.views.groups_list', name="group-list"),
    url(r'^view/(?P<pk>[\w-]+)/$', 'error.views.error_view', name="error-view"),
    url(r'^view/toggle/(?P<pk>[\w-]+)/$','error.views.error_public_toggle', name="error-toggle"),
    url(r'^send/created/(?P<pk>[\w-]+)/$', 'error.views.send_signal', name="error-created"),
)

########NEW FILE########
__FILENAME__ = validations
from app.errors import StatusDoesNotExist

codes = ['100', '101', '102', '200', '201', '202', '203', '204', '205', '206',
    '207', '226', '300', '301', '302', '303', '304', '305', '307', '400', '401',
    '402', '403', '404', '405', '406', '407', '408', '409', '410', '411', '412',
    '413', '414', '415', '416', '417', '422', '423', '424', '426', '500', '501',
    '502', '503', '504', '505', '507', '510']

def valid_status(code):
    if isinstance(code, str):
        code = str(code)
    if code not in codes:
        raise StatusDoesNotExist, 'The status "%s" does not exist.' % code

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.views.generic.simple import direct_to_template
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.template import RequestContext, loader

from google.appengine.ext import db

from error.models import Error, Group
from error.forms import ErrorForm, GroupForm
from error.signals import error_created

from app.utils import render_plain, render_json, not_allowed
from app.paginator import Paginator, get_page

# these aren't used directly, but if we don't import them here they
# won't get imported
from notifications import listeners as notifications_listeners
from projects import listeners as projects_listeners
from error import listeners as error_listeners
from issues import listeners as error_listeners

try:
    from custom import listeners as custom_listeners
except ImportError:
    pass

def send_signal(request, pk):
    error = Error.get(pk)
    if not error.create_signal_sent:
        error.create_signal_sent = True
        error.save()
        error_created.send(sender=error.__class__, instance=error)
        return render_plain("Signal sent")
    return render_plain("Signal not sent")

def get_group_filtered(request):
    form = GroupForm(request.GET or None)
    if form.is_valid():
        queryset = form.as_query()
    else:
        queryset = db.Query(Group)
        queryset.order("-timestamp")

    return form, queryset

def get_filtered(request):
    form = ErrorForm(request.GET or None)
    if form.is_valid():
        queryset = form.as_query()
    else:
        queryset = db.Query(Error)
        queryset.order("-timestamp")

    return form, queryset

@user_passes_test(lambda u: u.is_staff)
def errors_list(request):
    form, queryset = get_filtered(request)
    paginated = Paginator(queryset, 50)
    page = get_page(request, paginated)
    if request.GET.get("lucky") and len(page.object_list):
        return HttpResponseRedirect(reverse("error-view", args=[page.object_list[0].id,]))
    return direct_to_template(request, "list.html", extra_context={
        "page": page,
        "nav": {"selected": "list", "subnav": "list"},
        "form": form,
        "refresh": True
        })

@user_passes_test(lambda u: u.is_staff)
@render_json
def errors_snippet(request, pk=None):
    form, queryset = get_filtered(request)
    paginated = Paginator(queryset, 50)
    page = get_page(request, paginated)
    template = loader.get_template('list-snippet.html')
    html = template.render(RequestContext(request, {"object_list": page.object_list, }))
    return {"html":html, "count": len(page.object_list) }

@user_passes_test(lambda u: u.is_staff)
def groups_list(request):
    form, queryset = get_group_filtered(request)
    paginated = Paginator(queryset, 10)
    page = get_page(request, paginated)
    return direct_to_template(request, "group.html", extra_context={
        "page": page,
        "form": form,
        "nav": {"selected": "list", "subnav": "group"},
        })

@user_passes_test(lambda u: u.is_staff)
def error_public_toggle(request, pk):
    error = Error.get(pk)
    if request.method.lower() == "post":
        if error.public:
            error.public = False
        else:
            error.public = True
        error.save()
    return HttpResponseRedirect(reverse("error-view", args=[error.id,]))

def error_view(request, pk):
    error = Error.get(pk)
    if not error.public:
        if not request.user.is_staff:
            return not_allowed(request)

    if not error.read:
        error.read = True
        error.save()

    return direct_to_template(request, "view.html", extra_context={
        "error":error,
        "nav": {"selected": "list"},
        })

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext as _
from django.core.validators import EMPTY_VALUES

from app.forms import ModelForm, Form
from app.fields import OurModelChoiceField, OurModelChoiceIterator
from issues.models import Issue, Comment, IssueProjectURL
from appengine_django.auth.models import User
from error.forms import Filter

priorities = ([1,_("High")], [3, _("Medium")], [5, _("Low")])
states = (
    ["open", _("Open")],
    ["accepted", _("Accepted")],
    ["work_progress", _("Work in progress")],
    ["testing", _("Testing")],
    ["approved", _("Approved")],
    ["deploy_progress", _("Deploy in process")],
    ["deployed", _("Deployed")],
    ["rejected", _("Rejected")],
    )
states_first_empty = list(states)
states_first_empty.insert(0, ["", "-------"])

issue_project_url_statuses = (
    ["fixed", _("Fixed")],
    ["not_fixed", _("Not Fixed")],
    ["not_relevant", _("Not relevant")],
)

class IssueProjectURLForm(ModelForm):
    status = forms.ChoiceField(choices=issue_project_url_statuses,
        widget=forms.Select, required=False)

    class Meta:
        model = IssueProjectURL
        fields = ("status")

class IssueListForm(Filter):
    status = forms.ChoiceField(choices=states_first_empty, widget=forms.Select, required=False)
    assigned = OurModelChoiceField(required=False,
        queryset=User.all().filter("is_staff = ", True),
        model=User)

    def as_query(self):
        return super(IssueListForm, self).as_query("Issue")

class IssueForm(ModelForm):
    title = forms.CharField(required=False, label=_("Title"),
        widget=forms.TextInput(attrs={"size":100}))
    raw = forms.CharField(required=False, label=_("URL"),
        widget=forms.TextInput(attrs={"size":100}))
    description = forms.CharField(required=True,
        help_text=_("A description, markdown syntax possible."),
        widget=forms.Textarea(attrs={"cols": 100, "rows": 10}))
    priority = forms.IntegerField(required=False,
        widget=forms.Select(choices=priorities))
    status = forms.CharField(required=False,
        widget=forms.Select(choices=states))
    assigned = OurModelChoiceField(required=False,
        queryset=User.all().filter("is_staff = ", True),
        model=User)
    
    class Meta:
        model = Issue
        fields = ("raw", "description", "title", "priority", "assigned",
                    "project", "status")

class GroupForm(Form):
    group = forms.CharField(required=False, widget=forms.HiddenInput())

class UpdateForm(Form):
    status = forms.CharField(required=False, widget=forms.Select(choices=states))
    assigned = OurModelChoiceField(required=False,
        queryset=User.all().filter("is_staff = ", True),
        model=User)
    text = forms.CharField(required=False, label=_("Comments"),
        widget = forms.Textarea(
            attrs={"cols": 100, "rows": 10}
            ),
        help_text=_("A description, markdown syntax possible.")
        )

########NEW FILE########
__FILENAME__ = listeners
import md5

from django.utils.translation import ugettext as _

from app.utils import safe_string, log
from issues import signals
from issues.models import IssueProjectURL

def default_add_issue(instance, **kw):
    log("Firing signal: default_add_issue")
    instance.add_log(_("Issue created."))

signals.issue_created.connect(default_add_issue, dispatch_uid="default_add_issue")

def default_add_comment(instance, **kw):
    log("Firing signal: default_add_comment")
    instance.issue.add_log(_("Comment created."))

signals.comment_created.connect(default_add_comment, dispatch_uid="default_add_comment")

def default_add_project_urls(instance, **kw):
    log("Firing signal: default_add_project_urls")
    if instance.project:
        for project_url in instance.project.projecturl_set:
            issue_project_url = IssueProjectURL(
                issue=instance,
                project_url=project_url,
                status="not_fixed")
            issue_project_url.save()

signals.issue_created.connect(default_add_project_urls, dispatch_uid="default_add_project_urls")

########NEW FILE########
__FILENAME__ = models
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from datetime import datetime

from google.appengine.api.labs import taskqueue
from google.appengine.ext import db

from appengine_django.auth.models import User

from userstorage.utils import get_user

from app.base import Base
from app.utils import break_url, trunc_string
from projects.models import Project, ProjectURL
from error.models import Group
from issues import signals

class Issue(Base):
    # time error was received by this server
    timestamp = db.DateTimeProperty()

    title = db.StringProperty(required=False)
    description = db.TextProperty(required=False)

    priority = db.IntegerProperty()

    raw = db.StringProperty()
    domain = db.StringProperty()
    query = db.StringProperty()
    protocol = db.StringProperty()

    project = db.ReferenceProperty(Project, required=False)
    creator = db.ReferenceProperty(User, required=False, collection_name="creator")
    assigned = db.ReferenceProperty(User, required=False, collection_name="assignee")

    status = db.StringProperty()

    number = db.IntegerProperty()

    def get_absolute_url(self):
        return reverse("issues-view", args=[self.number,])

    def get_log_set(self):
        """ We need to provide a way to order the logs """
        return self.log_set.order("-timestamp")

    def get_comment_set(self):
        """ We need to provide a way to order the comments """
        return self.comment_set.order("-timestamp")

    def add_log(self, text):
        """ Adds in a log on the issue for the current user """
        log = Log(creator=get_user(), timestamp=datetime.now(), text=text, issue=self)
        log.save()
        return log

    def add_group(self, group):
        """ Adds in an issue group """
        issue_group = IssueGroup(issue=self, group=group)
        issue_group.save()
        return issue_group

    def __str__(self):
        return self.title

    def save(self, *args, **kw):
        if self.raw:
            for k, v in break_url(self.raw).items():
                setattr(self, k, v)

        if not self.title:
            self.title = trunc_string(self.description, 50)

        created = not getattr(self, "id", None)
        old = None
        if created:
            # there's a possible race condition here
            try:
                self.number = Issue.all().order("-number")[0].number + 1
            except IndexError:
                self.number = 1
            self.timestamp = datetime.now()
        else:
            old = Issue.get(self.id)

        self.put()
        if created:
            signals.issue_created.send(sender=self.__class__, instance=self)
        else:
            for key in ["status", "assigned", "priority"]:
                new_value = getattr(self, key)
                old_value = getattr(old, key)
                if new_value !=old_value:
                    signal = getattr(signals, "issue_%s_changed" % key)
                    signal.send(sender=self.__class__, instance=self, old=old_value, new=new_value)

            signals.issue_changed.send(sender=self.__class__, instance=self, old=old)

class Comment(Base):
    timestamp = db.DateTimeProperty()
    issue = db.ReferenceProperty(Issue)
    text = db.TextProperty()

    creator = db.ReferenceProperty(User)

    def save(self, *args, **kw):
        created = not getattr(self, "id", None)
        if created:
            self.timestamp = datetime.now()

        self.put()
        if created:
            signals.comment_created.send(sender=self.__class__, instance=self)

class IssueGroup(Base):
    issue = db.ReferenceProperty(Issue)
    group = db.ReferenceProperty(Group)

class IssueProjectURL(Base):
    issue = db.ReferenceProperty(Issue)
    project_url = db.ReferenceProperty(ProjectURL)
    status = db.StringProperty(required=False)

    def get_status_image(self):
        return {
            "not_fixed": "not-fixed",
            "fixed": "fixed"
        }.get(self.status, "")

    def get_status_display(self):
        from issues.forms import issue_project_url_statuses
        return dict(issue_project_url_statuses).get(self.status)

    def __str__(self):
        return str(self.project_url)

class Log(Base):
    timestamp = db.DateTimeProperty()

    issue = db.ReferenceProperty(Issue)
    text = db.TextProperty()

    creator = db.ReferenceProperty(User)

from notifications import registry
registry.register(Issue, "Issue")
########NEW FILE########
__FILENAME__ = signals
import django.dispatch

issue_created = django.dispatch.Signal(providing_args=["instance",])
comment_created = django.dispatch.Signal(providing_args=["instance",])

issue_status_changed = django.dispatch.Signal(providing_args=["instance", "old", "new"])
issue_assigned_changed = django.dispatch.Signal(providing_args=["instance", "old", "new"])
issue_priority_changed = django.dispatch.Signal(providing_args=["instance", "old", "new"])

issue_changed = django.dispatch.Signal(providing_args=["instance", "old"])

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse

from issues.models import Issue, Log, Comment, IssueGroup
from error.models import Group, Error
from projects.models import Project, ProjectURL
from google.appengine.ext import db

from issues import listeners
from issues import signals
from issues.views import issue_by_number
from error import listeners

from app.utils import break_url, safe_int
from app.utils import _pdb

class ErrorTests(TestCase):
    # test the view for writing errors
    def setUp(self):
        for issue in Issue.all(): issue.delete()
        for log in Log.all(): log.delete()
        for comment in Comment.all(): comment.delete()
        for group in Group.all(): group.delete()
        for error in Error.all(): error.delete()
        for project in Project.all(): project.delete()

    def testLogAdded(self):
        issue = Issue()
        issue.description = "This is a test"
        issue.save()

        assert issue.log_set[0]
    
    def testIssueNumber(self):
        issue = Issue()
        issue.description = "This is a test"
        issue.save()
        assert issue.number == 1
        
        issue = Issue()
        issue.description = "This is a test"
        issue.save()
        assert issue.number == 2

        old_issue = issue

        issue = Issue()
        issue.description = "This is a test"
        issue.save()
        assert issue.number == 3, issue.number

        old_issue.delete()
        
        issue = Issue()
        issue.description = "This is a test"
        issue.save()
        assert issue.number == 4
        
    def _setup(self):
        self.project = Project(name="testing")
        self.project.save()

        self.url = ProjectURL(url="http://test.areciboapp.com")
        self.url.project = self.project
        self.url.save()

        self.url = ProjectURL(url="http://www.areciboapp.com")
        self.url.project = self.project
        self.url.save()

        self.error = Error()
        for k, v in break_url("http://test.areciboapp.com/an/other").items():
            setattr(self.error, k, v)
        self.error.save()

    def _issue(self):
        self.issue = Issue()
        self.issue.description = "This is a test"
        self.issue.save()

    def testIssueGroup(self):
        self._setup()

        self._issue()

        group = Group.all()[0]
        self.issue.add_group(group)

        assert group == self.issue.issuegroup_set[0].group
        assert self.issue.issuegroup_set.count() == 1

        assert self.issue == IssueGroup.all().filter("issue = ", self.issue)[0].issue

    def testIssueURL(self):
        self._setup()

        self.issue = Issue()
        self.issue.description = "This is a test"
        self.issue.project = self.project
        self.issue.save()

        assert self.issue.issueprojecturl_set.count() == 2
        assert self.issue.issueprojecturl_set[0].status == "not_fixed"

    def testIssueURLFlexibility(self):
        self._setup()

        self._issue()
        assert self.issue == issue_by_number(self.issue.number)
        assert self.issue == issue_by_number(self.issue.number)

    def testIssueChanged(self):
        self.signal_fired = False
        def signal_fired(instance, old, **kw):
            self.signal_fired = True
        signals.issue_changed.connect(signal_fired, dispatch_uid="issue_changed")
        self._issue()
        self.issue.status = "rejected"
        self.issue.save()
        assert self.signal_fired

    def testIssuePriorityChanged(self):
        self.signal_fired = False
        def signal_fired(instance, old, new, **kw):
            self.signal_fired = True
            assert old in (None, 1)
            assert new in (1, 2)

        signals.issue_priority_changed.connect(signal_fired, dispatch_uid="issue_priority_changed")

        self._issue()
        self.issue.priority = 1
        self.issue.save()
        assert self.signal_fired

        self.signal_fired = False
        self.issue.priority = 2
        self.issue.save()
        assert self.signal_fired

    def testIssueStatusChanged(self):
        self.signal_fired = False
        def signal_fired(instance, old, new, **kw):
            self.signal_fired = True
            assert not old
            assert new == "rejected"

        signals.issue_status_changed.connect(signal_fired, dispatch_uid="issue_status_changed")

        self._issue()
        self.issue.status = "rejected"
        self.issue.save()
        assert self.signal_fired

        self.signal_fired = False
        self.issue.priority = 1
        self.issue.save()
        assert not self.signal_fired

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^$', 'issues.views.issue_list', name="issues-list"),
    url(r'^add/$', 'issues.views.issue_add', name="issues-add"),

    url(r'^edit/project-url/(?P<pk>[\w-]+)/$', 'issues.views.edit_project_url', name="issues-project-url"),
    url(r'^edit/(?P<pk>[\w-]+)/$', 'issues.views.issue_edit', name="issues-edit"),

    url(r'^view/(?P<pk>[\w-]+)/$', 'issues.views.issue_view', name="issues-view"),
    url(r'^view/logs/(?P<pk>[\w-]+)/$', 'issues.views.issue_log_view', name="issues-log-view"),

    url(r'^add/comment/(?P<pk>[\w-]+)/$', 'issues.views.comment_add', name="issues-add-comment"),
)

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.decorators import user_passes_test
from django.views.generic.simple import direct_to_template
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.template import RequestContext, loader
from django.forms.formsets import formset_factory

from google.appengine.ext import db
from app.paginator import Paginator, get_page
from app.utils import safe_int

from error.models import Group

from issues.models import Issue, Comment, Log, IssueProjectURL, IssueGroup
from issues.forms import IssueForm, UpdateForm, IssueListForm, IssueProjectURLForm, GroupForm
from issues.forms import issue_project_url_statuses

from userstorage.utils import get_user

def get_issues_filtered(request):
    form = IssueListForm(request.GET or None)
    if form.is_valid():
        queryset = form.as_query()
    else:
        queryset = db.Query(Issue)
        queryset.order("-timestamp")

    return form, queryset

def issue_by_number(pk):
    """ Get's the issue by a primary key or a number, i like hacking the url so
        you can just put in a number in the URL """
    number = safe_int(pk)
    if number:
        issues = Issue.all().filter("number = ", number)
        return issues[0]
    else:
        return Issue.get(pk)

@user_passes_test(lambda u: u.is_staff)
def issue_list(request):
    form, queryset = get_issues_filtered(request)
    paginated = Paginator(queryset, 50)
    page = get_page(request, paginated)
    return direct_to_template(request, "issue_list.html", extra_context={
        "page": page,
        "form": form,
        "nav": {"selected": "issues", "subnav": "list"},
    })

@user_passes_test(lambda u: u.is_staff)
def issue_log_view(request, pk):
    issue = issue_by_number(pk)
    logs = Log.all().filter("issue = ", issue)
    paginated = Paginator(logs, 50)
    page = get_page(request, paginated)
    return direct_to_template(request, "issue_log_list.html", extra_context={
        "page": page,
        "issue": issue,
        "nav": {"selected": "issues", "subnav": "list"},
    })

@user_passes_test(lambda u: u.is_staff)
def issue_view(request, pk):
    issue = issue_by_number(pk)
    return direct_to_template(request, "issue_view.html", extra_context={
        "issue": issue,
        "get_user": get_user(),
        "nav": {"selected": "issues"}
    })

@user_passes_test(lambda u: u.is_staff)
def issue_add(request):
    issue_form = IssueForm(request.POST or request.GET or None)
    group_form = GroupForm(request.POST or request.GET or None)
    if issue_form.is_valid() and group_form.is_valid():
        obj = issue_form.save(commit=False)
        obj.creator = request.user
        obj.save()

        if group_form.cleaned_data.get("group"):
            group = Group.get(group_form.cleaned_data["group"])
            IssueGroup(group=group, issue=obj).save()

        return HttpResponseRedirect(reverse("issues-list"))
    return direct_to_template(request, "issue_add.html", extra_context={
        "issue_form": issue_form,
        "group_form": group_form,
        "nav": {"selected": "issues", "subnav": "add"},
    })

@user_passes_test(lambda u: u.is_staff)
def issue_edit(request, pk):
    issue = issue_by_number(pk)
    form = IssueForm(request.POST or None, instance=issue)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.save()
        return HttpResponseRedirect(reverse("issues-view", args=[pk,]))
    return direct_to_template(request, "issue_edit.html", extra_context={
        "form": form,
        "issue": issue,
        "nav": {"selected": "issues",},
    })

@user_passes_test(lambda u: u.is_staff)
def edit_project_url(request, pk):
    issue = Issue.get(pk)
    urls = IssueProjectURL.all().filter("issue = ", issue)
    url_ids = dict([ (url.id, url) for url in urls ])
    if request.POST:
        for key, value in request.POST.items():
            if key in url_ids:
                assert value in [ i[0] for i in issue_project_url_statuses ], \
                    "%s not in %s" % (value, issue_project_url_statuses)
                url_ids[key].status = value
                url_ids[key].save()
        return HttpResponseRedirect(reverse("issues-view", args=[pk,]))
    return direct_to_template(request, "issue_project_url.html", extra_context={
        "issue": issue,
        "urls": urls,
        "issue_project_url_statuses": issue_project_url_statuses,
        "nav": {"selected": "issues",},
    })

@user_passes_test(lambda u: u.is_staff)
def comment_add(request, pk):
    issue = issue_by_number(pk)
    initial={"status":issue.status,}
    if issue.assigned:
        initial["assigned"] = issue.assigned.pk
    form = UpdateForm(request.POST or None, initial=initial)
    if form.is_valid():
        if "text" in form.cleaned_data:
            comment = Comment()
            comment.text = form.cleaned_data["text"]
            comment.issue = issue
            comment.creator = request.user
            comment.save()

        if "status" in form.cleaned_data and issue.status != form.cleaned_data["status"]:
            issue.add_log("Status changed from %s to %s" % (issue.status, form.cleaned_data["status"]))
            issue.status = form.cleaned_data["status"]
            issue.save()

        if "assigned" in form.cleaned_data and issue.assigned != form.cleaned_data["assigned"]:
            issue.add_log("Reassigned from %s to %s" % (issue.assigned, form.cleaned_data["assigned"]))
            issue.assigned = form.cleaned_data["assigned"]
            issue.save()

        return HttpResponseRedirect(reverse("issues-view", args=[pk,]))
    return direct_to_template(request, "comment_add.html", extra_context={
        "form": form,
        "issue": issue,
        "nav": {"selected": "issues"},
    })

########NEW FILE########
__FILENAME__ = main
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Bootstrap for running a Django app under Google App Engine.

The site-specific code is all in other files: settings.py, urls.py,
models.py, views.py.  And in fact, only 'settings' is referenced here
directly -- everything else is controlled from there.

"""

# Standard Python imports.
import sys

from appengine_django import InstallAppengineHelperForDjango
InstallAppengineHelperForDjango()

from appengine_django import have_django_zip
from appengine_django import django_zip_path

# Google App Engine imports.
from google.appengine.ext.webapp import util

# Import the part of Django that we use here.
import django.core.handlers.wsgi

from google.appengine.ext.webapp import template
template.register_template_library('app.tags')

def main():
  # Ensure the Django zipfile is in the path if required.
  if have_django_zip and django_zip_path not in sys.path:
    sys.path.insert(1, django_zip_path)

  # Create a Django application for WSGI.
  application = django.core.handlers.wsgi.WSGIHandler()

  # Run the WSGI CGI handler with that application.
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from appengine_django import InstallAppengineHelperForDjango
InstallAppengineHelperForDjango()

from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)


if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = email
error_msg = """Arecibo is notifying you of the following errors:
--------------------

%s
--------------------
You are receiving this because it's the email address set for your account at %s.

Please remember I'm just a bot and don't really exist, so replying to this email will
not do you any good I'm afraid.
"""

issue_msg = """Arecibo is notifying you of the following issue_changes:
--------------------

%s
--------------------
You are receiving this because it's the email address set for your account at %s.

Please remember I'm just a bot and don't really exist, so replying to this email will
not do you any good I'm afraid.
"""

from google.appengine.api import mail
from django.conf import settings
from app.utils import log

def as_text(issue):
    pass

def as_text(error):
    details = ["    Error: %s%s" % (settings.SITE_URL, error.get_absolute_url()), ]
    if error.raw:
        details.append("    URL: %s" % error.raw)
    for key in ("timestamp", "status", "priority", "type", "server"):
        value = getattr(error, key)
        if value:
            details.append("    %s: %s" % (key.capitalize(), value))
    details.append("")
    details = "\n".join(details)
    return details

def send_error_email(holder):
    alot = 10
    data = "\n".join([ as_text(obj) for obj in holder.objs[:alot]])
    count = len(holder.objs)
    if count > 1:
        subject = "Reporting %s errors" % count
    else:
        subject = "Reporting an error"
    if count > alot:
        data += "\n...truncated. For more see the website.\n"
    log("Sending email to: %s of %s error(s)" % (holder.user.email, count))
    mail.send_mail(sender=settings.DEFAULT_FROM_EMAIL,
        to=holder.user.email,
        subject=subject,
        body=error_msg % (data, settings.SITE_URL))
    
def send_issue_email(holder):
    # unlike errors, we are assuming that there isn't going to be a huge number each time
    data = "\n".join([ as_text(obj) for obj in holder.objs])
    count = len(holder.objs)
    if count > 1:
        subject = "Reporting %s issue changes" % count
    else:
        subject = "Reporting an issue change"
    log("Sending email to: %s of %s issues(s)" % (holder.user.email, count))
    mail.send_mail(sender=settings.DEFAULT_FROM_EMAIL,
        to=holder.user.email,
        subject=subject,
        body=error_msg % (data, settings.SITE_URL))
########NEW FILE########
__FILENAME__ = listeners
from app.utils import log
from notifications.models import Notification
from profiles.utils import get_profile
from users.utils import approved_users

from error.signals import error_created
from issues.signals import issue_created, issue_changed

def default_notification(instance, **kw):
    """ Given an error see if we need to send a notification """
    log("Firing signal: default_notification")

    users = approved_users()
    filtered = []
    for user in users:
        profile = get_profile(user)
        if profile.notification and instance.priority <= profile.notification:
            filtered.append(user)
    
    if not filtered:
        return
    
    notification = Notification()
    notification.type = "Error"
    notification.type_key = str(instance.key())
    notification.user = [ str(u.key()) for u in filtered ]
    notification.save()

error_created.connect(default_notification, dispatch_uid="default_notification")

def default_issue_notification(instance, **kw):
    """ Given an issue see default_issue_notification we need to send a notification """
    log("Firing signal: default_notification")

    users = approved_users()

    if not users.count():
        return
    
    notification = Notification()
    notification.type = "Issue"
    notification.type_key = str(instance.key())
    notification.user = [ str(u.key()) for u in users ]
    notification.save()

# turn this on when its all working
#issue_created.connect(default_issue_notification, dispatch_uid="default_issue_notification")
#issue_changed.connect(default_issue_notification, dispatch_uid="default_issue_notification")
########NEW FILE########
__FILENAME__ = models
from datetime import datetime

from google.appengine.api import memcache
from appengine_django.models import BaseModel
from appengine_django.auth.models import User

from google.appengine.ext import db

from notifications.signals import notification_created
from registry import get

class Notification(BaseModel):
    user = db.ListProperty(str)

    tried = db.BooleanProperty(default=False)
    completed = db.BooleanProperty(default=False)
    error_msg = db.TextProperty()
    timestamp = db.DateTimeProperty()

    type = db.StringProperty()
    type_key = db.StringProperty()

    def notifier(self):
        """ Returns the object that you'd like to be notified about """
        if self.type and self.type_key:
            return get()[self.type].get(self.type_key)        

    def save(self):
        created = not hasattr(self, "id")
        if created:
            self.timestamp = datetime.now()
        self.put()
        if created:
            notification_created.send(sender=self.__class__, instance=self)

    def user_list(self):
        users = []
        for key in self.user:
            data = memcache.get(key)
            if data:
                users.append(data)
            else:
                user = User.get(key)
                users.append(user)
                memcache.set(key, user, 60)
        return users


########NEW FILE########
__FILENAME__ = registry
_registry = {}

def register(klass, name):
    global _registry
    _registry[name] = klass
    
def get():
    return _registry
########NEW FILE########
__FILENAME__ = signals
import django.dispatch

notification_created = django.dispatch.Signal(providing_args=["instance",])
########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.test.client import Client

from django.core.urlresolvers import reverse

from error.models import Error
from issues.models import Issue
from notifications.models import Notification
from appengine_django.auth.models import User as AppUser
from google.appengine.api.users import User
from profiles.utils import get_profile

from app.tests import test_data
from django.core import mail

def create_user():
    return AppUser(user=User(email="test@foo.com"),
                    username="test",
                    email="test@foo.com",
                    is_staff=True).save()


class ErrorTests(TestCase):
    # test the view for writing errors
    def setUp(self):
        for error in Error.all(): error.delete()
        for notification in Notification.all(): notification.delete()
        for user in AppUser.all(): user.delete()
        for issue in Issue.all(): issue.delete()

    def testBasic(self):
        c = Client()
        assert not Error.all().count()
        c.post(reverse("error-post"), test_data)
        assert test_data["priority"] < 5, test_data["priority"]
        assert Error.all().count() == 1

        c.post(reverse("error-post"), test_data)
        assert test_data["priority"] < 5, test_data["priority"]
        assert Error.all().count() == 2

    def testNoNotification(self):
        c = Client()
        assert not Error.all().count()
        data = test_data.copy()
        data["priority"] = 6
        c.post(reverse("error-post"), data)
        assert data["priority"] > 5, data["priority"]
        assert Error.all().count() == 1
        assert Notification.all().count() == 0

    def testProfile(self):
        user = create_user()        
        
        c = Client()
        data = test_data.copy()
        data["priority"] = 6
        c.post(reverse("error-post"), data)
        
        assert Notification.all().count() == 0, Notification.all().count()
    
        data["priority"] = 5
        c.post(reverse("error-post"), data)
        
        assert Notification.all().count() == 1
        
        profile = get_profile(user)
        profile.notification = 8

        data["priority"] = 5
        c.post(reverse("error-post"), data)
        
        assert Notification.all().count() == 2
        
        data["priority"] = 8
        c.post(reverse("error-post"), data)
        
        assert Notification.all().count() == 2

        data["priority"] = 9
        c.post(reverse("error-post"), data)
        
        assert Notification.all().count() == 2

    def testNotificationNoUsers(self):
        c = Client()
        c.post(reverse("error-post"), test_data)
        assert Notification.all().count() == 0
    
    def testIssueAndErrorNotification(self):
        user = create_user()
        
        issue = Issue()
        issue.description = "This is a test"
        issue.save()
        
        assert Issue.all().count() == 1

        c = Client()
        c.post(reverse("error-post"), test_data)

        #assert Notification.all().count() == 2
        # this would be 2 when issues are turned on
        assert Notification.all().count() == 1
        
        c = Client()
        res = c.get(reverse("notification-send"))        
        self.assertEquals(len(mail.outbox), 1)
        
        # this is to check that at the moment issue notifications don't get sent
    
    def testIssueNotification(self):
        user = create_user()
    
        issue = Issue()
        issue.description = "This is a test"
        issue.save()
        
        assert Issue.all().count() == 1
        #assert Notification.all().count() == 1
        #assert Notification.all()[0].type == "Issue"
    
    def testCron(self):
        user = create_user()
        
        self.testBasic()
        # now test our sending actually works
        c = Client()
        res = c.get(reverse("notification-send"))        
        self.assertEquals(len(mail.outbox), 1)
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^list/$', 'notifications.views.notifications_list', name="notification-list"),
    url(r'^send/$', 'notifications.views.notifications_send', name="notification-send"),
    url(r'^cleanup/$', 'notifications.views.notifications_cleanup', name="notification-clean"),
)

########NEW FILE########
__FILENAME__ = views
import sys
from datetime import datetime, timedelta

from django.contrib.auth.decorators import user_passes_test
from django.views.generic.simple import direct_to_template

from notifications.models import Notification
from notifications.email import send_error_email

from app.paginator import Paginator, get_page
from app.utils import log, render_plain

@user_passes_test(lambda u: u.is_staff)
def notifications_list(request):
    queryset = Notification.all().order("-timestamp")
    # this number doesn't need to be high and its quite an expensive
    # page to generate
    paginated = Paginator(queryset, 10)
    page = get_page(request, paginated)
    return direct_to_template(request, "notification_list.html", extra_context={
        "page": page,
        "nav": {"selected": "notifications"}
        })


def notifications_cleanup(request):
    log("Firing cron: notifications_cleanup")
    expired = datetime.today() - timedelta(days=7)
    queryset = Notification.all().filter("tried = ", True).filter("timestamp < ", expired)
    for notification in queryset:
        notification.delete()

    return render_plain("Cron job completed")

class Holder:
    def __init__(self):
        self.user = None
        self.objs = []
        self.notifs = []

def notifications_send(request):
    log("Firing cron: notifications_send")
    notifications = Notification.all().filter("type = ", "Error").filter("tried = ", False)

    # batch up the notifications for the user
    holders = {}
    for notif in notifications:
        for user in notif.user_list():
            key = str(user.key())
            if key not in holders:
                holder = Holder()
                holder.user = user
                holders[key] = holder

            holders[key].objs.append(notif.notifier())
            holders[key].notifs.append(notif)

    for user_id, holder in holders.items():
        try:
            send_error_email(holder)
            for notification in holder.notifs:
                notification.tried = True
                notification.completed = True
                notification.save()
        except:
            info = sys.exc_info()
            data = "%s, %s" % (info[0], info[1])
            for notification in holder.notifs:
                notification.tried = True
                notification.completed = True
                notification.error_msg = data
                notification.save()
            
    return render_plain("Cron job completed")
########NEW FILE########
__FILENAME__ = models
from datetime import datetime

from app.base import Base
from google.appengine.ext import db
from appengine_django.auth.models import User

class Profile(Base):
    user = db.ReferenceProperty(User)
    notification = db.IntegerProperty()

    def __str__(self):
        return str(self.user)

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase

from appengine_django.auth.models import User as AppUser
from google.appengine.api.users import User

from profiles.models import Profile
from profiles.utils import get_profile

class TestProfile(TestCase):
    
    def setUp(self):
        for user in AppUser.all(): user.delete()
        for profile in Profile.all(): profile.delete()

    def test_add_user(self):
        user = AppUser(user=User(email="test@foo.com"),
                       username="test",
                       email="test@foo.com",
                       is_staff=True).save()
        assert not Profile.all().count()
        profile = get_profile(user)
        assert profile.notification == 5
        assert Profile.all().count()

########NEW FILE########
__FILENAME__ = utils
from profiles.models import Profile

def get_profile(user):
    try:
        return Profile.all().filter("user = ", user)[0]
    except IndexError:
        profile = Profile(user=user, notification=5)
        profile.save()
        return profile
########NEW FILE########
__FILENAME__ = forms
from django import forms
from app.forms import ModelForm

from projects.models import Project, ProjectURL, stage_choices

class ProjectForm(ModelForm):
    name = forms.CharField(required=True, label="Name")
    description = forms.CharField(required=False, label="Description", widget=forms.Textarea)

    class Meta:
        model = Project

class ProjectURLForm(ModelForm):
    url = forms.CharField(required=True, label="Domain")
    stage = forms.CharField(
        required=True, label="Project stage",
        widget=forms.Select(choices=stage_choices)
        )

    class Meta:
        model = ProjectURL
        fields = ("url", "stage")
########NEW FILE########
__FILENAME__ = listeners
from app.utils import log

from projects.models import Project
from error import signals

def lookup_domain(domain):
    # given a domain, find the project
    projects = Project.all()
    for project in projects:
        for url in project.projecturl_set:
            if domain == url.url:
                return url

def default_project(instance, **kw):
    log("Firing signal: default_project")
    if instance.project_url:
        return

    error = instance.sample()
    if error:
        domain = lookup_domain(error.domain)
        if domain:
            instance.project_url = domain
            instance.save()

signals.group_assigned.connect(default_project, dispatch_uid="default_browser_parsing")
########NEW FILE########
__FILENAME__ = models
from datetime import datetime

from app.base import Base
from appengine_django.models import BaseModel
from google.appengine.ext import db

from django.utils.translation import ugettext as _

stage_choices = (
    ["dev", _("Development")],
    ["testing", _("Testing")],
    ["staging", _("Staging")],
    ["backup", _("Backups")],
    ["production", _("Production")],
    ["other", _("Other")]
)

class Project(Base):
    name = db.StringProperty(required=True)
    description = db.TextProperty(required=False)

    def __str__(self):
        return self.name

class ProjectURL(Base):
    project = db.ReferenceProperty(Project)
    url = db.StringProperty(required=False)
    stage = db.StringProperty(required=False)

    def get_stage_display(self):
        return dict(stage_choices).get(self.stage)

    def __str__(self):
        return self.url

########NEW FILE########
__FILENAME__ = signals

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.test.client import Client

from django.core.urlresolvers import reverse

from error.models import Error, Group
from projects.models import Project, ProjectURL

from app.tests import test_data
from app.utils import _pdb

class ProjectTests(TestCase):
    # test the signals for project
    def setUp(self):
        for error in Error.all(): error.delete()
        for group in Group.all(): group.delete()
        for project in Project.all(): project.delete()

    def _addError(self):
        c = Client()
        assert not Error.all().count()
        c.post(reverse("error-post"), test_data)
        assert test_data["priority"] < 5, test_data["priority"]
        assert Error.all().count() == 1

    def testAddProject(self):
        project = Project(name="test")
        project.save()

        project_url = ProjectURL()
        project_url.url = "badapp.org"
        project_url.stage = "dev"
        project_url.project = project
        project_url.save()

        self._addError()

        assert Group.all().count() == 1
        assert Group.all()[0].project_url == project_url
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^$', 'projects.views.project_list', name="projects-list"),

    url(r'^add/url/(?P<pk>[\w-]+)/$', 'projects.views.project_url_add', name="projects-url-add"),
    url(r'^edit/url/(?P<pk>[\w-]+)/(?P<url>[\w-]+)/$', 'projects.views.project_url_edit', name="projects-url-edit"),

    url(r'^add/$', 'projects.views.project_add', name="projects-add"),
    url(r'^edit/(?P<pk>[\w-]+)/$', 'projects.views.project_edit', name="projects-edit"),

)

########NEW FILE########
__FILENAME__ = utils

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.decorators import user_passes_test
from django.views.generic.simple import direct_to_template
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.template import RequestContext, loader

from google.appengine.ext import db

from projects.models import Project, ProjectURL
from projects.forms import ProjectForm, ProjectURLForm

@user_passes_test(lambda u: u.is_staff)
def project_list(request):
    projects = Project.all().order("-name")
    return direct_to_template(request, "project_list.html", extra_context={
        "page": projects,
        "nav": {"selected": "projects", "subnav": "list"},
    })

@user_passes_test(lambda u: u.is_staff)
def project_add(request):
    form = ProjectForm(request.POST or None)
    if form.is_valid():
        form.save()
        return HttpResponseRedirect(reverse("projects-list"))
    return direct_to_template(request, "project_add.html", extra_context={
        "form": form,
        "nav": {"selected": "projects",},
    })

@user_passes_test(lambda u: u.is_staff)
def project_edit(request, pk):
    form = ProjectForm(request.POST or None, instance=Project.get(pk))
    if form.is_valid():
        form.save()
        return HttpResponseRedirect(reverse("projects-list"))
    return direct_to_template(request, "project_edit.html", extra_context={
        "form": form,
        "nav": {"selected": "projects",},
    })

@user_passes_test(lambda u: u.is_staff)
def project_url_add(request, pk):
    project = Project.get(pk)
    form = ProjectURLForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.project = project
        obj.save()
        return HttpResponseRedirect(reverse("projects-list"))
    return direct_to_template(request, "project_url_add.html", extra_context={
        "form": form,
        "project": project,
        "nav": {"selected": "projects",},
    })

@user_passes_test(lambda u: u.is_staff)
def project_url_edit(request, pk, url):
    url = ProjectURL.get(url)
    project = Project.get(pk)
    form = ProjectURLForm(request.POST or None, instance=url)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.project = project
        obj.save()
        return HttpResponseRedirect(reverse("projects-list"))
    return direct_to_template(request, "project_url_edit.html", extra_context={
        "form": form,
        "project": project,
        "nav": {"selected": "projects",},
    })

########NEW FILE########
__FILENAME__ = http
from django.http import HttpResponse
from error.models import Error

from app.utils import render_plain
from receiving.post import populate

def post(request):
    """ Add in a post """
    err = Error()
    err.ip = request.META.get("REMOTE_ADDR", "")
    err.user_agent = request.META.get("HTTP_USER_AGENT", "")

    populate(err, request.POST)
    return render_plain("Error recorded")

########NEW FILE########
__FILENAME__ = mail
from django.utils.simplejson import loads
from django.http import HttpResponse

from error.models import Error

from app.utils import log, render_plain
from google.appengine.api import mail
from receiving.post import populate

def parse(content_type, body):
    data = body.decode()
    if data.rfind("}") > 0:
        # strip out any crap on the end
        end = data.rfind("}")
        # not sure why i was doing this, i'm sure there
        # was a good reason at one point
        text = data[:end] + "}"
        err = Error()
        json = loads(text, strict=False)
        populate(err, json)
        return True

def post(request):
    """ Add in a post """
    log("Processing email message")
    mailobj = mail.InboundEmailMessage(request.raw_post_data)
    found = False

    for content_type, body in mailobj.bodies("text/plain"):
        found = parse(content_type, body)
    for content_type, body in mailobj.bodies("text/html"):
        found = parse(content_type, body)

    if not found:
        log("No contents found in the message.")

    return render_plain("message parsed")
########NEW FILE########
__FILENAME__ = mail_django
# # this is a specific handler for django
import re
from urlparse import urlunparse

from django.conf import settings

from app.utils import log, render_plain
from google.appengine.api import mail
from receiving.post import populate
from error.models import Error

mapping_404_key = {
    "Referrer":"request",
    "Requested URL":"url",
    "User agent":"user_agent",
    "IP address":"ip"
}

mapping_404_value = {
    "request": "HTTP_REFERER: %s"
}

mapping_500_key = {
    "server": re.compile("'SERVER_NAME.*'(?P<value>.*?)'"),
    "user_agent": re.compile("'HTTP_USER_AGENT.*'(?P<value>.*?)'"),
    "ip": re.compile("'REMOTE_ADDR.*'(?P<value>.*?)'"),
    "path": re.compile("'PATH_INFO.*'(?P<value>.*?)'"),
    "host": re.compile("'HTTP_HOST.*'(?P<value>.*?)'"),
    "query_string": re.compile("'QUERY_STRING.*'(?P<value>.*?)'"),
    "server_port": re.compile("'SERVER_PORT.*'(?P<value>.*?)'"),
    "server_protocol": re.compile("'SERVER_PROTOCOL.*'(?P<value>.*?)'"),
}

def parse_http(value):
    return "%s" % value.split('/')[0].lower()

mapping_500_value = {
    "server_protocol": parse_http
}

def parse_404(body, subject):
    domain = subject.split(" on ")[-1]
    body = body.decode().replace("=\n", "")
    lines = body.split("\n")
    data = {"status": 404, "priority": 5}
    for line in lines:
        if not line: continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value == "None": value = None
        key = mapping_404_key.get(key)
        if key in mapping_404_value:
            value = mapping_404_value[key] % value
        data[key] = value
    try:
        data["url"] = "http://%s%s" % (domain, data["url"])
        # note we have to assume this
    except KeyError:
        pass
    return data

def parse_500(body, subject):
    # subject is not needed
    data = {"traceback":[], "request":[], "status": 500, "priority": 1}
    data["traceback"], data["request"] = body.decode().split("\n\n<")
    for key, regex in mapping_500_key.items():
        match = regex.search(data["request"])
        if match:
            value = match.groups()[0]
            if key in mapping_500_value:
                value = mapping_500_value[key](value)
            data[key] = value
    try:
        data["url"] = urlunparse((
            data["server_protocol"], data["host"],
            data["path"], data["query_string"],
            "", "")
            )
    except KeyError:
        pass
    try:
        data["type"], data["message"] = data["traceback"].strip().split("\n")[-1].split(": ", 1)
    except ValueError:
        pass
    return data

def post(request):
    """ Add in a post """
    log("Processing email message")
    mailobj = mail.InboundEmailMessage(request.raw_post_data)
    to = mailobj.to

    if to in settings.ALLOWED_RECEIVING_ADDRESSES:
        key = settings.ARECIBO_PUBLIC_ACCOUNT_NUMBER
    else:
        key = to.split("-", 1)[1].split("@")[0]
        if key != settings.ARECIBO_PUBLIC_ACCOUNT_NUMBER:
            log("To address (%s, to %s) does not match account number (%s)" % (key, to, settings.ARECIBO_PUBLIC_ACCOUNT_NUMBER))
            return        

    for content_type, body in mailobj.bodies("text/plain"):
        if mailobj.subject.find(" Broken ") > -1:
            log("Trying to parse body using 404 parser")
            result = parse_404(body, mailobj.subject)
        else:
            log("Trying to parse body using 500 parser")
            result = parse_500(body, mailobj.subject)
        err = Error()
        result["account"] = key
        populate(err, result)

    return render_plain("message parsed")

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = post
from datetime import datetime
from urlparse import urlparse, urlunparse

from django.conf import settings

from app.utils import break_url
from app.errors import StatusDoesNotExist
from error.validations import valid_status
from email.Utils import parsedate

def populate(err, incoming):
    """ Populate the error table with the incoming error """
    # special lookup the account
    uid = incoming.get("account", "")
    if not uid:
        raise ValueError, "Missing the required account number."
    if str(uid) != settings.ARECIBO_PUBLIC_ACCOUNT_NUMBER:
        raise ValueError, "Account number does not match"

    # special
    if incoming.has_key("url"):
        for k, v in break_url(incoming["url"]).items():
            setattr(err, k, v)

    # check the status codes
    if incoming.has_key("status"):
        status = str(incoming["status"])
        try:
            valid_status(status)
            err.status = status
        except StatusDoesNotExist:
            err.errors += "Status does not exist, ignored.\n"

    # not utf-8 encoded
    for src, dest in [
        ("ip", "ip"),
        ("user_agent", "user_agent"),
        ("uid", "uid"),
        ]:
        actual = incoming.get(src, None)
        if actual is not None:
            setattr(err, dest, str(actual))

    try:
        priority = int(incoming.get("priority", 0))
    except ValueError:
        priority = 0
    err.priority = min(priority, 10)

    # possibly utf-8 encoding
    for src, dest in [
        ("type", "type"),
        ("msg", "msg"),
        ("server", "server"),
        ("traceback", "traceback"),
        ("request", "request"),
        ("username", "username")
        ]:
        actual = incoming.get(src, None)
        if actual is not None:
            try:
                setattr(err, dest, actual.encode("utf-8"))
            except UnicodeDecodeError:
                err.errors += "Encoding error on the %s field, ignored.\n" % src

    # timestamp handling
    if incoming.has_key("timestamp"):
        tmstmp = incoming["timestamp"].strip()
        if tmstmp.endswith("GMT"):
            tmstmp = tmstmp[:-3] + "-0000"
        tme = parsedate(tmstmp)
        if tme:
            try:
                final = datetime(*tme[:7])
                err.error_timestamp = final
            except ValueError, msg:
                err.errors += 'Date error on the field "%s", ignored.\n' % msg

    err.timestamp = datetime.now()
    err.timestamp_date = datetime.now().date()
    err.save()
########NEW FILE########
__FILENAME__ = tests
sample_500_body = """Traceback (most recent call last):

File "/data/amo_python/www/prod/zamboni/vendor/src/django/django/core/handlers/base.py", line 100, in get_response
  response = callback(request, *callback_args, **callback_kwargs)

File "/data/amo_python/www/prod/zamboni/apps/users/views.py", line 78, in confirm_resend
  user.email_confirmation_code()

File "/data/amo_python/www/prod/zamboni/apps/users/models.py", line 254, in email_confirmation_code
  t.render(Context(c)), None, [self.email])

File "/data/amo_python/www/prod/zamboni/vendor/src/django/django/core/mail/__init__.py", line 61, in send_mail
  connection=connection).send()

File "/data/amo_python/www/prod/zamboni/vendor/src/django/django/core/mail/message.py", line 175, in send
  return self.get_connection(fail_silently).send_messages([self])

File "/data/amo_python/www/prod/zamboni/vendor/src/django/django/core/mail/backends/smtp.py", line 85, in send_messages
  sent = self._send(message)

File "/data/amo_python/www/prod/zamboni/vendor/src/django/django/core/mail/backends/smtp.py", line 101, in _send
  email_message.message().as_string())

File "/usr/lib/python2.6/smtplib.py", line 709, in sendmail
  raise SMTPRecipientsRefused(senderrs)

SMTPRecipientsRefused: {u'runnoex@hotmail.com': (553, 'Requested mail action aborted: Mailbox name has been suppressed.')}


<WSGIRequest
GET:<QueryDict: {}>,
POST:<QueryDict: {}>,
COOKIES:{'WT_FPC': 'id=25780a0ac63c363510a1290112372929:lv=1290112451748:ss=1290112372929',
'amo_home_promo_seen': '1',
'csrftoken': '35224bac87f70725a34afc8a97aa50d1',
'wtspl': '967280'},
META:{'CSRF_COOKIE': '35224bac87f70725a34afc8a97aa50d1',
'DOCUMENT_ROOT': '/data/www/addons.mozilla.org-remora/site/app/webroot',
'GATEWAY_INTERFACE': 'CGI/1.1',
'HTTPS': 'on',
'HTTP_ACCEPT': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
'HTTP_ACCEPT_CHARSET': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
'HTTP_ACCEPT_ENCODING': 'gzip,deflate',
'HTTP_ACCEPT_LANGUAGE': 'pt-br,pt;q=0.8,en-us;q=0.5,en;q=0.3',
'HTTP_CONNECTION': 'Keep-Alive',
'HTTP_COOKIE': 'csrftoken=35224bac87f70725a34afc8a97aa50d1; WT_FPC=id=25780a0ac63c363510a1290112372929:lv=1290112451748:ss=1290112372929; wtspl=967280; amo_home_promo_seen=1',
'HTTP_HOST': 'addons.mozilla.org',
'HTTP_KEEP_ALIVE': '115',
'HTTP_REFERER': 'https://addons.mozilla.org/pt-BR/firefox/users/login',
'HTTP_SSLCLIENTCERTSTATUS': 'NoClientCert',
'HTTP_SSLCLIENTCIPHER': 'SSL_RSA_WITH_RC4_128_SHA, version=SSLv3, bits=128',
'HTTP_SSLSESSIONID': 'D76B89BB968FE44847A97FA889B9EA6F169D2A7B6A7B85EB11858851DA23DB47',
'HTTP_USER_AGENT': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; pt-BR; rv:1.9.2.12) Gecko/20101026 Firefox/3.6.12',
'HTTP_X_CLUSTER_CLIENT_IP': '63.245.213.6',
'HTTP_X_FORWARDED_FOR': '201.73.138.6, 63.245.213.6',
'HTTP_X_ZEUS_DL_PT': '552612',
'PATH_INFO': u'/pt-BR/firefox/user/5550302/confirm/resend',
'PATH_TRANSLATED': '/data/amo_python/www/prod/zamboni/wsgi/zamboni.wsgi/pt-BR/firefox/user/5550302/confirm/resend',
'QUERY_STRING': '',
'REMOTE_ADDR': '201.73.138.6',
'REMOTE_PORT': '62955',
'REQUEST_METHOD': 'GET',
'REQUEST_URI': '/pt-BR/firefox/user/5550302/confirm/resend',
'SCRIPT_FILENAME': '/data/amo_python/www/prod/zamboni/wsgi/zamboni.wsgi',
'SCRIPT_NAME': u'',
'SCRIPT_URI': 'http://addons.mozilla.org/pt-BR/firefox/user/5550302/confirm/resend',
'SCRIPT_URL': '',
'SERVER_ADDR': '10.2.83.17',
'SERVER_ADMIN': 'webmaster@mozilla.com',
'SERVER_NAME': 'addons.mozilla.org',
'SERVER_PORT': '80',
'SERVER_PROTOCOL': 'HTTP/1.1',
'SERVER_SIGNATURE': '',
'SERVER_SOFTWARE': 'Apache',
'datetime': '2010-11-18 19:34:48.900860',
'hostname': 'pm-app-amo05',
'is-forwarded': '1',
'mod_wsgi.application_group': 'addons.mozilla.org|/z',
'mod_wsgi.callable_object': 'application',
'mod_wsgi.handler_script': '',
'mod_wsgi.input_chunked': '0',
'mod_wsgi.listener_host': '',
'mod_wsgi.listener_port': '81',
'mod_wsgi.process_group': 'zamboni_prod',
'mod_wsgi.request_handler': 'wsgi-script',
'mod_wsgi.script_reloading': '1',
'mod_wsgi.version': (3, 3),
'wsgi.errors': <mod_wsgi.Log object at 0xc6d09d0>,
'wsgi.file_wrapper': <built-in method file_wrapper of mod_wsgi.Adapter object at 0xc961890>,
'wsgi.input': <mod_wsgi.Input object at 0xc6d0b60>,
'wsgi.loaded': datetime.datetime(2010, 11, 18, 19, 31, 15, 188526),
'wsgi.multiprocess': True,
'wsgi.multithread': False,
'wsgi.run_once': False,
'wsgi.url_scheme': 'https',
'wsgi.version': (1, 1)}>
_______________________________________________
Amo-tracebacks mailing list
Amo-tracebacks@mozilla.org
https://mail.mozilla.org/listinfo/amo-tracebacks
"""

sample_404_body = """Referrer: None
Requested URL: /error/awkdjhga?asd
User agent: Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_3; en-us) AppleW=
ebKit/531.22.7 (KHTML, like Gecko) Version/4.0.5 Safari/531.22.7
IP address: 127.0.0.1
"""

sample_404_body_parsed = {'url': '/error/awkdjhga?asd',
    'ip': '127.0.0.1',
    'request': 'HTTP_REFERER: None',
    'user_agent': 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_3; en-us) AppleWebKit/531.22.7 (KHTML, like Gecko) Version/4.0.5 Safari/531.22.7'
}


from mail_django import parse_404, parse_500

from django.test import TestCase

class ErrorTests(TestCase):
    # test the view for writing errors
    def testBasic(self):
        result = parse_404(sample_404_body, "")
        result = parse_500(sample_500_body, "")

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^v/1/$', 'receiving.http.post', name="error-post"),
    url(r'^_ah/mail/django-.*', 'receiving.mail_django.post', name="mail-django-post"),
    url(r'^_ah/mail/.*', 'receiving.mail.post', name="mail-post"),
)

########NEW FILE########
__FILENAME__ = settings
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Django settings for google-app-engine-django project.

import os

DEBUG = False #True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'appengine'  # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = ''             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.
TIME_ZONE = 'UTC'

LANGUAGE_CODE = 'en-us'

SITE_ID = 1

USE_I18N = False
MEDIA_ROOT = ''
MEDIA_URL = ''


# Make this unique, and don't share it with anybody.
SECRET_KEY = 'hvhdrfgd4tg54lwi435qa4tg.isz6taz^%sg_nx'

# Ensure that email is not sent via SMTP by default to match the standard App
# Engine SDK behaviour. If you want to sent email via SMTP then add the name of
# your mailserver here.
EMAIL_HOST = ''

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'appengine_django.auth.middleware.AuthenticationMiddleware',
    'userstorage.middleware.UserStorage'
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'app.context.context',
)

ROOT_URLCONF = 'urls'

ROOT_PATH = os.path.dirname(__file__)
TEMPLATE_DIRS = (
    os.path.join(ROOT_PATH, 'templates'),
    os.path.join(ROOT_PATH, 'custom', 'templates')
)

INSTALLED_APPS = (
     'django.contrib.auth',
     'appengine_django',
     'appengine_django.auth',
     'error',
     'app',
     'notifications',
     'receiving',
     'users',
     'stats',
     'projects',
     'issues',
     'profiles',
     'custom'
)

TEST_RUNNER = "app.test_runner.AreciboRunner"

ALLOWED_RECEIVING_ADDRESSES = ()
AUTH_PROFILE_MODULE = 'profiles.Profile'

try:
    from local_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = models
from django.utils import simplejson

from datetime import datetime

from google.appengine.ext import db

from appengine_django.models import BaseModel
from stats.signals import stats_completed

class Stats(BaseModel):
    """ A series of stats for a date """
    date = db.DateProperty()
    timestamp = db.DateTimeProperty()
    stats = db.TextProperty()
    completed = db.BooleanProperty(default=False)

    @property
    def id(self):
        return str(self.key())

    def save(self, *args, **kw):
        created = not hasattr(self, "id")
        if created:
            self.timestamp = datetime.now()

        if not self.completed and self.complete():
            self.completed = True
            self.put()
            stats_completed.send(sender=self.__class__, instance=self)
        else:
            self.put()

    def get_stats(self):
        if self.stats:
            return simplejson.loads(self.stats)
        return simplejson.loads("{}")

    def set_stats(self, data):
        self.stats = simplejson.dumps(data)

    def complete(self):
        values = self.get_stats().values()
        if not values:
            return False
        return not None in values

########NEW FILE########
__FILENAME__ = signals
import django.dispatch

stats_completed = django.dispatch.Signal(providing_args=["instance",])

########NEW FILE########
__FILENAME__ = tests
import os
from datetime import datetime, timedelta

from django.test import TestCase
from django.test.client import Client

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import connection

from app import tests
from error.models import Error, Group
from stats.utils import count

class StatsTests(TestCase):
    # test the view for writing errors
    def setUp(self):
        for error in Error.all(): error.delete()

    def testCount(self):
        for x in range(0, 1110):
            Error().save(dont_send_signals=True)
        assert count() == 1110
        for x in range(0, 5):
            err = Error(dont_send_signals=True)
            err.priority = 4
            err.save()
        assert count(["priority = ", 4]) == 5
        assert count(["priority = ", None]) == 1110
        assert count() == 1115
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# if you put the key in here it will get exposed in errors
# so probably
urlpatterns = patterns('',
    url(r'^$', 'stats.views.view', name="stats-view"),
    url(r'^generate/$', 'stats.views.start', name="stats-start"),
    url(r'^generate/action/(?P<action>[\w-]+)/(?P<pk>[\w-]+)/$', 'stats.views.get_action', name="stats-action"),

)

########NEW FILE########
__FILENAME__ = utils
from error.models import Error

# get around the 1000 count limit, based on
# http://notes.mhawthorne.net/post/172608709/appengine-counting-more-than-1000-entities
max_fetch = 1000

def count(*filters):
    count = 0

    query = Error.all(keys_only=True)
    for k, v in filters:
        query = query.filter(k, v)

    query = query.order('__key__')

    while count % max_fetch == 0:
        current_count = query.count()
        if current_count == 0:
            break
        count += current_count

        if current_count == max_fetch:
            last_key = query.fetch(1, max_fetch - 1)[0]
            query = query.filter('__key__ > ', last_key)

    return count
########NEW FILE########
__FILENAME__ = views
from datetime import datetime, timedelta

from django.contrib.auth.decorators import user_passes_test
from django.views.generic.simple import direct_to_template
from django.core.urlresolvers import reverse
from django.http import HttpResponse

from google.appengine.api.labs import taskqueue

from app.utils import render_plain, safe_int

from stats.utils import count
from stats.models import Stats

registered = {}

def start(request):
    days = safe_int(request.GET.get("days", 1))
    if not days:
        days = 1
    date = (datetime.today() - timedelta(days=days)).date()
    create(date)
    return HttpResponse("total started")

def create(date):
    existing = Stats.all().filter("date = ", date)
    try:
        stats = existing[0]
    except IndexError:
        stats = Stats()
    stats.date = date
    data = dict([(key, None) for key in registered.keys()])
    stats.set_stats(data)
    stats.save()

    for key in registered.keys():
        taskqueue.add(url=reverse("stats-action", kwargs={"action":key, "pk":stats.id}))

def get_action(request, action, pk):
    stats = Stats.get(pk)
    current = stats.get_stats()
    if action not in registered:
        raise ValueError, "Action: %s not registered" % action
    current[action] = registered[action](stats)
    stats.set_stats(current)
    stats.save()
    return render_plain("total done: %s" % current)

def get_total(stats):
    return count(["timestamp_date = ", stats.date],)

def get_status(stats):
    return {
        "500":count(["status = ", "500"], ["timestamp_date = ", stats.date]),
        "404":count(["status = ", "404"], ["timestamp_date = ", stats.date]),
        "403":count(["status = ", "403"], ["timestamp_date = ", stats.date]),
    }

registered["total"] = get_total
registered["status"] = get_status

@user_passes_test(lambda u: u.is_staff)
def view(request):
    stats = Stats.all().filter("completed = ", True).order("date")[:30]
    stats = [ {"object":s, "stats":s.get_stats()} for s in stats ]
    return direct_to_template(request, "stats.html", {
        "stats": stats,
        "nav": {"selected": "stats",}
        })
########NEW FILE########
__FILENAME__ = urls
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'', include('error.urls')),
    (r'', include('receiving.urls')),
    (r'', include('app.urls')),
    (r'', include('users.urls')),
    (r'^issues/', include('issues.urls')),
    (r'^stats/', include('stats.urls')),
    (r'^projects/', include('projects.urls')),
    (r'^notification/', include('notifications.urls')),
)

handler404 = 'app.errors.not_found_error'
handler500 = 'app.errors.application_error'
########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext as _

from app.forms import ModelForm

from appengine_django.auth.models import User
from profiles.models import Profile

class UserForm(ModelForm):
    is_staff = forms.BooleanField(required=False, label=_("Access to Arecibo"))
        
    class Meta:
        model = User
        fields = ("is_staff", "first_name", "last_name", "email")
        
choices = [ [x,x] for x in range(0, 10) ]
choices[0][1] = "No notifications"

class ProfileForm(ModelForm):
    notification = forms.IntegerField(
                         required=False,
                         label=_("Send notification at this priority level and above"),
                         widget=forms.Select(choices=choices))
    
    class Meta:
        model = Profile
        fields = ("notification",)
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^users/$', 'users.views.user_list', name="user-list"),
    url(r'^users/edit/(?P<pk>[\w-]+)/$', 'users.views.user_edit', name="user-edit"),
)

########NEW FILE########
__FILENAME__ = utils
from appengine_django.auth.models import User

def approved_users():
    return User.all().filter("is_staff = ", True)

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.decorators import user_passes_test
from django.views.generic.simple import direct_to_template
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

from appengine_django.auth.models import User
from app.paginator import Paginator, get_page

from users.forms import UserForm, ProfileForm
from profiles.utils import get_profile

@user_passes_test(lambda u: u.is_staff)
def user_list(request):
    queryset = User.all()
    # this number doesn't need to be high and its quite an expensive
    # page to generate
    paginated = Paginator(queryset, 10)
    page = get_page(request, paginated)
    return direct_to_template(request, "user_list.html", extra_context={
        "page": page,
        "nav": {"selected": "setup"}
        })

@user_passes_test(lambda u: u.is_staff)
def user_edit(request, pk):
    user = User.get(pk)
    form = UserForm(request.POST or None, instance=user)
    profile = ProfileForm(request.POST or None, instance=get_profile(user))
    if form.is_valid() and profile.is_valid():
        form.save()
        profile.save()
        return HttpResponseRedirect(reverse("user-list"))
    return direct_to_template(request, "user_edit.html", extra_context={
        "form": form,
        "profile": profile,
        "nav": {"selected": "users",},
    })


########NEW FILE########
__FILENAME__ = middleware
from userstorage.utils import activate, deactivate

class UserStorage:
    def process_request(self, request):
        activate(request)

    def process_exception(self, request, exception):
        deactivate(request)

    def process_response(self, request, response):
        deactivate(request)
        return response

########NEW FILE########
__FILENAME__ = utils
from threading import currentThread

_active = {}

def activate(request):
    if request and request.user:
        _active[currentThread()] = request.user

def deactivate(request):
    global _active
    if currentThread() in _active:
        del _active[currentThread()]

def get_user():
    if currentThread() not in _active:
        return None
    return _active[currentThread()]

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Arecibo documentation build configuration file, created by
# sphinx-quickstart on Tue Jun  1 18:29:27 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Arecibo'
copyright = u'2010, Andy McKay and Contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '2'
# The full version, including alpha/beta/rc tags.
release = '2'

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
exclude_patterns = []

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'trac'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "default"


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
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

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
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Arecibodoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Arecibo.tex', u'Arecibo Documentation',
   u'Andy McKay and Contributors', 'manual'),
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


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'arecibo', u'Arecibo Documentation',
     [u'Andy McKay and Contributors'], 1)
]

########NEW FILE########
__FILENAME__ = blockparser

import markdown

class State(list):
    """ Track the current and nested state of the parser. 
    
    This utility class is used to track the state of the BlockParser and 
    support multiple levels if nesting. It's just a simple API wrapped around
    a list. Each time a state is set, that state is appended to the end of the
    list. Each time a state is reset, that state is removed from the end of
    the list.

    Therefore, each time a state is set for a nested block, that state must be 
    reset when we back out of that level of nesting or the state could be
    corrupted.

    While all the methods of a list object are available, only the three
    defined below need be used.

    """

    def set(self, state):
        """ Set a new state. """
        self.append(state)

    def reset(self):
        """ Step back one step in nested state. """
        self.pop()

    def isstate(self, state):
        """ Test that top (current) level is of given state. """
        if len(self):
            return self[-1] == state
        else:
            return False

class BlockParser:
    """ Parse Markdown blocks into an ElementTree object. 
    
    A wrapper class that stitches the various BlockProcessors together,
    looping through them and creating an ElementTree object.
    """

    def __init__(self):
        self.blockprocessors = markdown.odict.OrderedDict()
        self.state = State()

    def parseDocument(self, lines):
        """ Parse a markdown document into an ElementTree. 
        
        Given a list of lines, an ElementTree object (not just a parent Element)
        is created and the root element is passed to the parser as the parent.
        The ElementTree object is returned.
        
        This should only be called on an entire document, not pieces.

        """
        # Create a ElementTree from the lines
        self.root = markdown.etree.Element(markdown.DOC_TAG)
        self.parseChunk(self.root, '\n'.join(lines))
        return markdown.etree.ElementTree(self.root)

    def parseChunk(self, parent, text):
        """ Parse a chunk of markdown text and attach to given etree node. 
        
        While the ``text`` argument is generally assumed to contain multiple
        blocks which will be split on blank lines, it could contain only one
        block. Generally, this method would be called by extensions when
        block parsing is required. 
        
        The ``parent`` etree Element passed in is altered in place. 
        Nothing is returned.

        """
        self.parseBlocks(parent, text.split('\n\n'))

    def parseBlocks(self, parent, blocks):
        """ Process blocks of markdown text and attach to given etree node. 
        
        Given a list of ``blocks``, each blockprocessor is stepped through
        until there are no blocks left. While an extension could potentially
        call this method directly, it's generally expected to be used internally.

        This is a public method as an extension may need to add/alter additional
        BlockProcessors which call this method to recursively parse a nested
        block.

        """
        while blocks:
           for processor in self.blockprocessors.values():
               if processor.test(parent, blocks[0]):
                   processor.run(parent, blocks)
                   break



########NEW FILE########
__FILENAME__ = blockprocessors
"""
CORE MARKDOWN BLOCKPARSER
=============================================================================

This parser handles basic parsing of Markdown blocks.  It doesn't concern itself
with inline elements such as **bold** or *italics*, but rather just catches 
blocks, lists, quotes, etc.

The BlockParser is made up of a bunch of BlockProssors, each handling a 
different type of block. Extensions may add/replace/remove BlockProcessors
as they need to alter how markdown blocks are parsed.

"""

import re
import markdown

class BlockProcessor:
    """ Base class for block processors. 
    
    Each subclass will provide the methods below to work with the source and
    tree. Each processor will need to define it's own ``test`` and ``run``
    methods. The ``test`` method should return True or False, to indicate
    whether the current block should be processed by this processor. If the
    test passes, the parser will call the processors ``run`` method.

    """

    def __init__(self, parser=None):
        self.parser = parser

    def lastChild(self, parent):
        """ Return the last child of an etree element. """
        if len(parent):
            return parent[-1]
        else:
            return None

    def detab(self, text):
        """ Remove a tab from the front of each line of the given text. """
        newtext = []
        lines = text.split('\n')
        for line in lines:
            if line.startswith(' '*markdown.TAB_LENGTH):
                newtext.append(line[markdown.TAB_LENGTH:])
            elif not line.strip():
                newtext.append('')
            else:
                break
        return '\n'.join(newtext), '\n'.join(lines[len(newtext):])

    def looseDetab(self, text, level=1):
        """ Remove a tab from front of lines but allowing dedented lines. """
        lines = text.split('\n')
        for i in range(len(lines)):
            if lines[i].startswith(' '*markdown.TAB_LENGTH*level):
                lines[i] = lines[i][markdown.TAB_LENGTH*level:]
        return '\n'.join(lines)

    def test(self, parent, block):
        """ Test for block type. Must be overridden by subclasses. 
        
        As the parser loops through processors, it will call the ``test`` method
        on each to determine if the given block of text is of that type. This
        method must return a boolean ``True`` or ``False``. The actual method of
        testing is left to the needs of that particular block type. It could 
        be as simple as ``block.startswith(some_string)`` or a complex regular
        expression. As the block type may be different depending on the parent
        of the block (i.e. inside a list), the parent etree element is also 
        provided and may be used as part of the test.

        Keywords:
        
        * ``parent``: A etree element which will be the parent of the block.
        * ``block``: A block of text from the source which has been split at 
            blank lines.
        """
        pass

    def run(self, parent, blocks):
        """ Run processor. Must be overridden by subclasses. 
        
        When the parser determines the appropriate type of a block, the parser
        will call the corresponding processor's ``run`` method. This method
        should parse the individual lines of the block and append them to
        the etree. 

        Note that both the ``parent`` and ``etree`` keywords are pointers
        to instances of the objects which should be edited in place. Each
        processor must make changes to the existing objects as there is no
        mechanism to return new/different objects to replace them.

        This means that this method should be adding SubElements or adding text
        to the parent, and should remove (``pop``) or add (``insert``) items to
        the list of blocks.

        Keywords:

        * ``parent``: A etree element which is the parent of the current block.
        * ``blocks``: A list of all remaining blocks of the document.
        """
        pass


class ListIndentProcessor(BlockProcessor):
    """ Process children of list items. 
    
    Example:
        * a list item
            process this part

            or this part

    """

    INDENT_RE = re.compile(r'^(([ ]{%s})+)'% markdown.TAB_LENGTH)
    ITEM_TYPES = ['li']
    LIST_TYPES = ['ul', 'ol']

    def test(self, parent, block):
        return block.startswith(' '*markdown.TAB_LENGTH) and \
                not self.parser.state.isstate('detabbed') and  \
                (parent.tag in self.ITEM_TYPES or \
                    (len(parent) and parent[-1] and \
                        (parent[-1].tag in self.LIST_TYPES)
                    )
                )

    def run(self, parent, blocks):
        block = blocks.pop(0)
        level, sibling = self.get_level(parent, block)
        block = self.looseDetab(block, level)

        self.parser.state.set('detabbed')
        if parent.tag in self.ITEM_TYPES:
            # The parent is already a li. Just parse the child block.
            self.parser.parseBlocks(parent, [block])
        elif sibling.tag in self.ITEM_TYPES:
            # The sibling is a li. Use it as parent.
            self.parser.parseBlocks(sibling, [block])
        elif len(sibling) and sibling[-1].tag in self.ITEM_TYPES:
            # The parent is a list (``ol`` or ``ul``) which has children.
            # Assume the last child li is the parent of this block.
            if sibling[-1].text:
                # If the parent li has text, that text needs to be moved to a p
                block = '%s\n\n%s' % (sibling[-1].text, block)
                sibling[-1].text = ''
            self.parser.parseChunk(sibling[-1], block)
        else:
            self.create_item(sibling, block)
        self.parser.state.reset()

    def create_item(self, parent, block):
        """ Create a new li and parse the block with it as the parent. """
        li = markdown.etree.SubElement(parent, 'li')
        self.parser.parseBlocks(li, [block])
 
    def get_level(self, parent, block):
        """ Get level of indent based on list level. """
        # Get indent level
        m = self.INDENT_RE.match(block)
        if m:
            indent_level = len(m.group(1))/markdown.TAB_LENGTH
        else:
            indent_level = 0
        if self.parser.state.isstate('list'):
            # We're in a tightlist - so we already are at correct parent.
            level = 1
        else:
            # We're in a looselist - so we need to find parent.
            level = 0
        # Step through children of tree to find matching indent level.
        while indent_level > level:
            child = self.lastChild(parent)
            if child and (child.tag in self.LIST_TYPES or child.tag in self.ITEM_TYPES):
                if child.tag in self.LIST_TYPES:
                    level += 1
                parent = child
            else:
                # No more child levels. If we're short of indent_level,
                # we have a code block. So we stop here.
                break
        return level, parent


class CodeBlockProcessor(BlockProcessor):
    """ Process code blocks. """

    def test(self, parent, block):
        return block.startswith(' '*markdown.TAB_LENGTH)
    
    def run(self, parent, blocks):
        sibling = self.lastChild(parent)
        block = blocks.pop(0)
        theRest = ''
        if sibling and sibling.tag == "pre" and len(sibling) \
                    and sibling[0].tag == "code":
            # The previous block was a code block. As blank lines do not start
            # new code blocks, append this block to the previous, adding back
            # linebreaks removed from the split into a list.
            code = sibling[0]
            block, theRest = self.detab(block)
            code.text = markdown.AtomicString('%s\n%s\n' % (code.text, block.rstrip()))
        else:
            # This is a new codeblock. Create the elements and insert text.
            pre = markdown.etree.SubElement(parent, 'pre')
            code = markdown.etree.SubElement(pre, 'code')
            block, theRest = self.detab(block)
            code.text = markdown.AtomicString('%s\n' % block.rstrip())
        if theRest:
            # This block contained unindented line(s) after the first indented 
            # line. Insert these lines as the first block of the master blocks
            # list for future processing.
            blocks.insert(0, theRest)


class BlockQuoteProcessor(BlockProcessor):

    RE = re.compile(r'(^|\n)[ ]{0,3}>[ ]?(.*)')

    def test(self, parent, block):
        return bool(self.RE.search(block))

    def run(self, parent, blocks):
        block = blocks.pop(0)
        m = self.RE.search(block)
        if m:
            before = block[:m.start()] # Lines before blockquote
            # Pass lines before blockquote in recursively for parsing forst.
            self.parser.parseBlocks(parent, [before])
            # Remove ``> `` from begining of each line.
            block = '\n'.join([self.clean(line) for line in 
                            block[m.start():].split('\n')])
        sibling = self.lastChild(parent)
        if sibling and sibling.tag == "blockquote":
            # Previous block was a blockquote so set that as this blocks parent
            quote = sibling
        else:
            # This is a new blockquote. Create a new parent element.
            quote = markdown.etree.SubElement(parent, 'blockquote')
        # Recursively parse block with blockquote as parent.
        self.parser.parseChunk(quote, block)

    def clean(self, line):
        """ Remove ``>`` from beginning of a line. """
        m = self.RE.match(line)
        if line.strip() == ">":
            return ""
        elif m:
            return m.group(2)
        else:
            return line

class OListProcessor(BlockProcessor):
    """ Process ordered list blocks. """

    TAG = 'ol'
    # Detect an item (``1. item``). ``group(1)`` contains contents of item.
    RE = re.compile(r'^[ ]{0,3}\d+\.[ ]+(.*)')
    # Detect items on secondary lines. they can be of either list type.
    CHILD_RE = re.compile(r'^[ ]{0,3}((\d+\.)|[*+-])[ ]+(.*)')
    # Detect indented (nested) items of either type
    INDENT_RE = re.compile(r'^[ ]{4,7}((\d+\.)|[*+-])[ ]+.*')

    def test(self, parent, block):
        return bool(self.RE.match(block))

    def run(self, parent, blocks):
        # Check fr multiple items in one block.
        items = self.get_items(blocks.pop(0))
        sibling = self.lastChild(parent)
        if sibling and sibling.tag in ['ol', 'ul']:
            # Previous block was a list item, so set that as parent
            lst = sibling
            # make sure previous item is in a p.
            if len(lst) and lst[-1].text and not len(lst[-1]):
                p = markdown.etree.SubElement(lst[-1], 'p')
                p.text = lst[-1].text
                lst[-1].text = ''
            # parse first block differently as it gets wrapped in a p.
            li = markdown.etree.SubElement(lst, 'li')
            self.parser.state.set('looselist')
            firstitem = items.pop(0)
            self.parser.parseBlocks(li, [firstitem])
            self.parser.state.reset()
        else:
            # This is a new list so create parent with appropriate tag.
            lst = markdown.etree.SubElement(parent, self.TAG)
        self.parser.state.set('list')
        # Loop through items in block, recursively parsing each with the
        # appropriate parent.
        for item in items:
            if item.startswith(' '*markdown.TAB_LENGTH):
                # Item is indented. Parse with last item as parent
                self.parser.parseBlocks(lst[-1], [item])
            else:
                # New item. Create li and parse with it as parent
                li = markdown.etree.SubElement(lst, 'li')
                self.parser.parseBlocks(li, [item])
        self.parser.state.reset()

    def get_items(self, block):
        """ Break a block into list items. """
        items = []
        for line in block.split('\n'):
            m = self.CHILD_RE.match(line)
            if m:
                # This is a new item. Append
                items.append(m.group(3))
            elif self.INDENT_RE.match(line):
                # This is an indented (possibly nested) item.
                if items[-1].startswith(' '*markdown.TAB_LENGTH):
                    # Previous item was indented. Append to that item.
                    items[-1] = '%s\n%s' % (items[-1], line)
                else:
                    items.append(line)
            else:
                # This is another line of previous item. Append to that item.
                items[-1] = '%s\n%s' % (items[-1], line)
        return items


class UListProcessor(OListProcessor):
    """ Process unordered list blocks. """

    TAG = 'ul'
    RE = re.compile(r'^[ ]{0,3}[*+-][ ]+(.*)')


class HashHeaderProcessor(BlockProcessor):
    """ Process Hash Headers. """

    # Detect a header at start of any line in block
    RE = re.compile(r'(^|\n)(?P<level>#{1,6})(?P<header>.*?)#*(\n|$)')

    def test(self, parent, block):
        return bool(self.RE.search(block))

    def run(self, parent, blocks):
        block = blocks.pop(0)
        m = self.RE.search(block)
        if m:
            before = block[:m.start()] # All lines before header
            after = block[m.end():]    # All lines after header
            if before:
                # As the header was not the first line of the block and the
                # lines before the header must be parsed first,
                # recursively parse this lines as a block.
                self.parser.parseBlocks(parent, [before])
            # Create header using named groups from RE
            h = markdown.etree.SubElement(parent, 'h%d' % len(m.group('level')))
            h.text = m.group('header').strip()
            if after:
                # Insert remaining lines as first block for future parsing.
                blocks.insert(0, after)
        else:
            # This should never happen, but just in case...
            message(CRITICAL, "We've got a problem header!")


class SetextHeaderProcessor(BlockProcessor):
    """ Process Setext-style Headers. """

    # Detect Setext-style header. Must be first 2 lines of block.
    RE = re.compile(r'^.*?\n[=-]{3,}', re.MULTILINE)

    def test(self, parent, block):
        return bool(self.RE.match(block))

    def run(self, parent, blocks):
        lines = blocks.pop(0).split('\n')
        # Determine level. ``=`` is 1 and ``-`` is 2.
        if lines[1].startswith('='):
            level = 1
        else:
            level = 2
        h = markdown.etree.SubElement(parent, 'h%d' % level)
        h.text = lines[0].strip()
        if len(lines) > 2:
            # Block contains additional lines. Add to  master blocks for later.
            blocks.insert(0, '\n'.join(lines[2:]))


class HRProcessor(BlockProcessor):
    """ Process Horizontal Rules. """

    RE = r'[ ]{0,3}(?P<ch>[*_-])[ ]?((?P=ch)[ ]?){2,}[ ]*'
    # Detect hr on any line of a block.
    SEARCH_RE = re.compile(r'(^|\n)%s(\n|$)' % RE)
    # Match a hr on a single line of text.
    MATCH_RE = re.compile(r'^%s$' % RE)

    def test(self, parent, block):
        return bool(self.SEARCH_RE.search(block))

    def run(self, parent, blocks):
        lines = blocks.pop(0).split('\n')
        prelines = []
        # Check for lines in block before hr.
        for line in lines:
            m = self.MATCH_RE.match(line)
            if m:
                break
            else:
                prelines.append(line)
        if len(prelines):
            # Recursively parse lines before hr so they get parsed first.
            self.parser.parseBlocks(parent, ['\n'.join(prelines)])
        # create hr
        hr = markdown.etree.SubElement(parent, 'hr')
        # check for lines in block after hr.
        lines = lines[len(prelines)+1:]
        if len(lines):
            # Add lines after hr to master blocks for later parsing.
            blocks.insert(0, '\n'.join(lines))


class EmptyBlockProcessor(BlockProcessor):
    """ Process blocks and start with an empty line. """

    # Detect a block that only contains whitespace 
    # or only whitespace on the first line.
    RE = re.compile(r'^\s*\n')

    def test(self, parent, block):
        return bool(self.RE.match(block))

    def run(self, parent, blocks):
        block = blocks.pop(0)
        m = self.RE.match(block)
        if m:
            # Add remaining line to master blocks for later.
            blocks.insert(0, block[m.end():])
            sibling = self.lastChild(parent)
            if sibling and sibling.tag == 'pre' and sibling[0] and \
                    sibling[0].tag == 'code':
                # Last block is a codeblock. Append to preserve whitespace.
                sibling[0].text = markdown.AtomicString('%s/n/n/n' % sibling[0].text )


class ParagraphProcessor(BlockProcessor):
    """ Process Paragraph blocks. """

    def test(self, parent, block):
        return True

    def run(self, parent, blocks):
        block = blocks.pop(0)
        if block.strip():
            # Not a blank block. Add to parent, otherwise throw it away.
            if self.parser.state.isstate('list'):
                # The parent is a tight-list. Append to parent.text
                if parent.text:
                    parent.text = '%s\n%s' % (parent.text, block)
                else:
                    parent.text = block.lstrip()
            else:
                # Create a regular paragraph
                p = markdown.etree.SubElement(parent, 'p')
                p.text = block.lstrip()

########NEW FILE########
__FILENAME__ = commandline
"""
COMMAND-LINE SPECIFIC STUFF
=============================================================================

The rest of the code is specifically for handling the case where Python
Markdown is called from the command line.
"""

import markdown
import sys
import logging
from logging import DEBUG, INFO, WARN, ERROR, CRITICAL

EXECUTABLE_NAME_FOR_USAGE = "python markdown.py"
""" The name used in the usage statement displayed for python versions < 2.3.
(With python 2.3 and higher the usage statement is generated by optparse
and uses the actual name of the executable called.) """

OPTPARSE_WARNING = """
Python 2.3 or higher required for advanced command line options.
For lower versions of Python use:

      %s INPUT_FILE > OUTPUT_FILE

""" % EXECUTABLE_NAME_FOR_USAGE

def parse_options():
    """
    Define and parse `optparse` options for command-line usage.
    """

    try:
        optparse = __import__("optparse")
    except:
        if len(sys.argv) == 2:
            return {'input': sys.argv[1],
                    'output': None,
                    'safe': False,
                    'extensions': [],
                    'encoding': None }, CRITICAL
        else:
            print OPTPARSE_WARNING
            return None, None

    parser = optparse.OptionParser(usage="%prog INPUTFILE [options]")
    parser.add_option("-f", "--file", dest="filename", default=sys.stdout,
                      help="write output to OUTPUT_FILE",
                      metavar="OUTPUT_FILE")
    parser.add_option("-e", "--encoding", dest="encoding",
                      help="encoding for input and output files",)
    parser.add_option("-q", "--quiet", default = CRITICAL,
                      action="store_const", const=CRITICAL+10, dest="verbose",
                      help="suppress all messages")
    parser.add_option("-v", "--verbose",
                      action="store_const", const=INFO, dest="verbose",
                      help="print info messages")
    parser.add_option("-s", "--safe", dest="safe", default=False,
                      metavar="SAFE_MODE",
                      help="safe mode ('replace', 'remove' or 'escape'  user's HTML tag)")
    parser.add_option("-o", "--output_format", dest="output_format", 
                      default='xhtml1', metavar="OUTPUT_FORMAT",
                      help="Format of output. One of 'xhtml1' (default) or 'html4'.")
    parser.add_option("--noisy",
                      action="store_const", const=DEBUG, dest="verbose",
                      help="print debug messages")
    parser.add_option("-x", "--extension", action="append", dest="extensions",
                      help = "load extension EXTENSION", metavar="EXTENSION")

    (options, args) = parser.parse_args()

    if not len(args) == 1:
        parser.print_help()
        return None, None
    else:
        input_file = args[0]

    if not options.extensions:
        options.extensions = []

    return {'input': input_file,
            'output': options.filename,
            'safe_mode': options.safe,
            'extensions': options.extensions,
            'encoding': options.encoding,
            'output_format': options.output_format}, options.verbose

def run():
    """Run Markdown from the command line."""

    # Parse options and adjust logging level if necessary
    options, logging_level = parse_options()
    if not options: sys.exit(0)
    if logging_level: logging.getLogger('MARKDOWN').setLevel(logging_level)

    # Run
    markdown.markdownFromFile(**options)

########NEW FILE########
__FILENAME__ = etree_loader

from markdown import message, CRITICAL
import sys

## Import
def importETree():
    """Import the best implementation of ElementTree, return a module object."""
    etree_in_c = None
    try: # Is it Python 2.5+ with C implemenation of ElementTree installed?
        import xml.etree.cElementTree as etree_in_c
    except ImportError:
        try: # Is it Python 2.5+ with Python implementation of ElementTree?
            import xml.etree.ElementTree as etree
        except ImportError:
            try: # An earlier version of Python with cElementTree installed?
                import cElementTree as etree_in_c
            except ImportError:
                try: # An earlier version of Python with Python ElementTree?
                    import elementtree.ElementTree as etree
                except ImportError:
                    message(CRITICAL, "Failed to import ElementTree")
                    sys.exit(1)
    if etree_in_c and etree_in_c.VERSION < "1.0":
        message(CRITICAL, "For cElementTree version 1.0 or higher is required.")
        sys.exit(1)
    elif etree_in_c :
        return etree_in_c
    elif etree.VERSION < "1.1":
        message(CRITICAL, "For ElementTree version 1.1 or higher is required")
        sys.exit(1)
    else :
        return etree


########NEW FILE########
__FILENAME__ = abbr
'''
Abbreviation Extension for Python-Markdown
==========================================

This extension adds abbreviation handling to Python-Markdown.

Simple Usage:

    >>> import markdown
    >>> text = """
    ... Some text with an ABBR and a REF. Ignore REFERENCE and ref.
    ...
    ... *[ABBR]: Abbreviation
    ... *[REF]: Abbreviation Reference
    ... """
    >>> markdown.markdown(text, ['abbr'])
    u'<p>Some text with an <abbr title="Abbreviation">ABBR</abbr> and a <abbr title="Abbreviation Reference">REF</abbr>. Ignore REFERENCE and ref.</p>'

Copyright 2007-2008
* [Waylan Limberg](http://achinghead.com/)
* [Seemant Kulleen](http://www.kulleen.org/)
	

'''

import markdown, re
from markdown import etree

# Global Vars
ABBR_REF_RE = re.compile(r'[*]\[(?P<abbr>[^\]]*)\][ ]?:\s*(?P<title>.*)')

class AbbrExtension(markdown.Extension):
    """ Abbreviation Extension for Python-Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Insert AbbrPreprocessor before ReferencePreprocessor. """
        md.preprocessors.add('abbr', AbbrPreprocessor(md), '<reference')
        
           
class AbbrPreprocessor(markdown.preprocessors.Preprocessor):
    """ Abbreviation Preprocessor - parse text for abbr references. """

    def run(self, lines):
        '''
        Find and remove all Abbreviation references from the text.
        Each reference is set as a new AbbrPattern in the markdown instance.
        
        '''
        new_text = []
        for line in lines:
            m = ABBR_REF_RE.match(line)
            if m:
                abbr = m.group('abbr').strip()
                title = m.group('title').strip()
                self.markdown.inlinePatterns['abbr-%s'%abbr] = \
                    AbbrPattern(self._generate_pattern(abbr), title)
            else:
                new_text.append(line)
        return new_text
    
    def _generate_pattern(self, text):
        '''
        Given a string, returns an regex pattern to match that string. 
        
        'HTML' -> r'(?P<abbr>[H][T][M][L])' 
        
        Note: we force each char as a literal match (in brackets) as we don't 
        know what they will be beforehand.

        '''
        chars = list(text)
        for i in range(len(chars)):
            chars[i] = r'[%s]' % chars[i]
        return r'(?P<abbr>\b%s\b)' % (r''.join(chars))


class AbbrPattern(markdown.inlinepatterns.Pattern):
    """ Abbreviation inline pattern. """

    def __init__(self, pattern, title):
        markdown.inlinepatterns.Pattern.__init__(self, pattern)
        self.title = title

    def handleMatch(self, m):
        abbr = etree.Element('abbr')
        abbr.text = m.group('abbr')
        abbr.set('title', self.title)
        return abbr

def makeExtension(configs=None):
    return AbbrExtension(configs=configs)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = codehilite
#!/usr/bin/python

"""
CodeHilite Extension for Python-Markdown
========================================

Adds code/syntax highlighting to standard Python-Markdown code blocks.

Copyright 2006-2008 [Waylan Limberg](http://achinghead.com/).

Project website: <http://www.freewisdom.org/project/python-markdown/CodeHilite>
Contact: markdown@freewisdom.org
 
License: BSD (see ../docs/LICENSE for details)
  
Dependencies:
* [Python 2.3+](http://python.org/)
* [Markdown 2.0+](http://www.freewisdom.org/projects/python-markdown/)
* [Pygments](http://pygments.org/)

"""

import markdown

# --------------- CONSTANTS YOU MIGHT WANT TO MODIFY -----------------

try:
    TAB_LENGTH = markdown.TAB_LENGTH
except AttributeError:
    TAB_LENGTH = 4


# ------------------ The Main CodeHilite Class ----------------------
class CodeHilite:
    """
    Determine language of source code, and pass it into the pygments hilighter.

    Basic Usage:
        >>> code = CodeHilite(src = 'some text')
        >>> html = code.hilite()
    
    * src: Source string or any object with a .readline attribute.
      
    * linenos: (Boolen) Turn line numbering 'on' or 'off' (off by default).

    * css_class: Set class name of wrapper div ('codehilite' by default).
      
    Low Level Usage:
        >>> code = CodeHilite()
        >>> code.src = 'some text' # String or anything with a .readline attr.
        >>> code.linenos = True  # True or False; Turns line numbering on or of.
        >>> html = code.hilite()
    
    """

    def __init__(self, src=None, linenos=False, css_class="codehilite"):
        self.src = src
        self.lang = None
        self.linenos = linenos
        self.css_class = css_class

    def hilite(self):
        """
        Pass code to the [Pygments](http://pygments.pocoo.org/) highliter with 
        optional line numbers. The output should then be styled with css to 
        your liking. No styles are applied by default - only styling hooks 
        (i.e.: <span class="k">). 

        returns : A string of html.
    
        """

        self.src = self.src.strip('\n')
        
        self._getLang()

        try:
            from pygments import highlight
            from pygments.lexers import get_lexer_by_name, guess_lexer, \
                                        TextLexer
            from pygments.formatters import HtmlFormatter
        except ImportError:
            # just escape and pass through
            txt = self._escape(self.src)
            if self.linenos:
                txt = self._number(txt)
            else :
                txt = '<div class="%s"><pre>%s</pre></div>\n'% \
                        (self.css_class, txt)
            return txt
        else:
            try:
                lexer = get_lexer_by_name(self.lang)
            except ValueError:
                try:
                    lexer = guess_lexer(self.src)
                except ValueError:
                    lexer = TextLexer()
            formatter = HtmlFormatter(linenos=self.linenos, 
                                      cssclass=self.css_class)
            return highlight(self.src, lexer, formatter)

    def _escape(self, txt):
        """ basic html escaping """
        txt = txt.replace('&', '&amp;')
        txt = txt.replace('<', '&lt;')
        txt = txt.replace('>', '&gt;')
        txt = txt.replace('"', '&quot;')
        return txt

    def _number(self, txt):
        """ Use <ol> for line numbering """
        # Fix Whitespace
        txt = txt.replace('\t', ' '*TAB_LENGTH)
        txt = txt.replace(" "*4, "&nbsp; &nbsp; ")
        txt = txt.replace(" "*3, "&nbsp; &nbsp;")
        txt = txt.replace(" "*2, "&nbsp; ")        
        
        # Add line numbers
        lines = txt.splitlines()
        txt = '<div class="codehilite"><pre><ol>\n'
        for line in lines:
            txt += '\t<li>%s</li>\n'% line
        txt += '</ol></pre></div>\n'
        return txt


    def _getLang(self):
        """ 
        Determines language of a code block from shebang lines and whether said
        line should be removed or left in place. If the sheband line contains a
        path (even a single /) then it is assumed to be a real shebang lines and
        left alone. However, if no path is given (e.i.: #!python or :::python) 
        then it is assumed to be a mock shebang for language identifitation of a
        code fragment and removed from the code block prior to processing for 
        code highlighting. When a mock shebang (e.i: #!python) is found, line 
        numbering is turned on. When colons are found in place of a shebang 
        (e.i.: :::python), line numbering is left in the current state - off 
        by default.
        
        """

        import re
    
        #split text into lines
        lines = self.src.split("\n")
        #pull first line to examine
        fl = lines.pop(0)
    
        c = re.compile(r'''
            (?:(?:::+)|(?P<shebang>[#]!))	# Shebang or 2 or more colons.
            (?P<path>(?:/\w+)*[/ ])?        # Zero or 1 path 
            (?P<lang>[\w+-]*)               # The language 
            ''',  re.VERBOSE)
        # search first line for shebang
        m = c.search(fl)
        if m:
            # we have a match
            try:
                self.lang = m.group('lang').lower()
            except IndexError:
                self.lang = None
            if m.group('path'):
                # path exists - restore first line
                lines.insert(0, fl)
            if m.group('shebang'):
                # shebang exists - use line numbers
                self.linenos = True
        else:
            # No match
            lines.insert(0, fl)
        
        self.src = "\n".join(lines).strip("\n")



# ------------------ The Markdown Extension -------------------------------
class HiliteTreeprocessor(markdown.treeprocessors.Treeprocessor):
    """ Hilight source code in code blocks. """

    def run(self, root):
        """ Find code blocks and store in htmlStash. """
        blocks = root.getiterator('pre')
        for block in blocks:
            children = block.getchildren()
            if len(children) == 1 and children[0].tag == 'code':
                code = CodeHilite(children[0].text, 
                            linenos=self.config['force_linenos'][0],
                            css_class=self.config['css_class'][0])
                placeholder = self.markdown.htmlStash.store(code.hilite(), 
                                                            safe=True)
                # Clear codeblock in etree instance
                block.clear()
                # Change to p element which will later 
                # be removed when inserting raw html
                block.tag = 'p'
                block.text = placeholder


class CodeHiliteExtension(markdown.Extension):
    """ Add source code hilighting to markdown codeblocks. """

    def __init__(self, configs):
        # define default configs
        self.config = {
            'force_linenos' : [False, "Force line numbers - Default: False"],
            'css_class' : ["codehilite", 
                           "Set class name for wrapper <div> - Default: codehilite"],
            }
        
        # Override defaults with user settings
        for key, value in configs:
            self.setConfig(key, value) 

    def extendMarkdown(self, md, md_globals):
        """ Add HilitePostprocessor to Markdown instance. """
        hiliter = HiliteTreeprocessor(md)
        hiliter.config = self.config
        md.treeprocessors.add("hilite", hiliter, "_begin") 


def makeExtension(configs={}):
  return CodeHiliteExtension(configs=configs)


########NEW FILE########
__FILENAME__ = def_list
#!/usr/bin/env Python
"""
Definition List Extension for Python-Markdown
=============================================

Added parsing of Definition Lists to Python-Markdown.

A simple example:

    Apple
    :   Pomaceous fruit of plants of the genus Malus in 
        the family Rosaceae.
    :   An american computer company.

    Orange
    :   The fruit of an evergreen tree of the genus Citrus.

Copyright 2008 - [Waylan Limberg](http://achinghead.com)

"""

import markdown, re
from markdown import etree


class DefListProcessor(markdown.blockprocessors.BlockProcessor):
    """ Process Definition Lists. """

    RE = re.compile(r'(^|\n)[ ]{0,3}:[ ]{1,3}(.*?)(\n|$)')

    def test(self, parent, block):
        return bool(self.RE.search(block))

    def run(self, parent, blocks):
        block = blocks.pop(0)
        m = self.RE.search(block)
        terms = [l.strip() for l in block[:m.start()].split('\n') if l.strip()]
        d, theRest = self.detab(block[m.end():])
        if d:
            d = '%s\n%s' % (m.group(2), d)
        else:
            d = m.group(2)
        #import ipdb; ipdb.set_trace()
        sibling = self.lastChild(parent)
        if not terms and sibling.tag == 'p':
            # The previous paragraph contains the terms
            state = 'looselist'
            terms = sibling.text.split('\n')
            parent.remove(sibling)
            # Aquire new sibling
            sibling = self.lastChild(parent)
        else:
            state = 'list'

        if sibling and sibling.tag == 'dl':
            # This is another item on an existing list
            dl = sibling
            if len(dl) and dl[-1].tag == 'dd' and len(dl[-1]):
                state = 'looselist'
        else:
            # This is a new list
            dl = etree.SubElement(parent, 'dl')
        # Add terms
        for term in terms:
            dt = etree.SubElement(dl, 'dt')
            dt.text = term
        # Add definition
        self.parser.state.set(state)
        dd = etree.SubElement(dl, 'dd')
        self.parser.parseBlocks(dd, [d])
        self.parser.state.reset()

        if theRest:
            blocks.insert(0, theRest)

class DefListIndentProcessor(markdown.blockprocessors.ListIndentProcessor):
    """ Process indented children of definition list items. """

    ITEM_TYPES = ['dd']
    LIST_TYPES = ['dl']

    def create_item(parent, block):
        """ Create a new dd and parse the block with it as the parent. """
        dd = markdown.etree.SubElement(parent, 'dd')
        self.parser.parseBlocks(dd, [block])
 


class DefListExtension(markdown.Extension):
    """ Add definition lists to Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Add an instance of DefListProcessor to BlockParser. """
        md.parser.blockprocessors.add('defindent',
                                      DefListIndentProcessor(md.parser),
                                      '>indent')
        md.parser.blockprocessors.add('deflist', 
                                      DefListProcessor(md.parser),
                                      '>ulist')


def makeExtension(configs={}):
    return DefListExtension(configs=configs)


########NEW FILE########
__FILENAME__ = extra
#!/usr/bin/env python
"""
Python-Markdown Extra Extension
===============================

A compilation of various Python-Markdown extensions that imitates
[PHP Markdown Extra](http://michelf.com/projects/php-markdown/extra/).

Note that each of the individual extensions still need to be available
on your PYTHONPATH. This extension simply wraps them all up as a 
convenience so that only one extension needs to be listed when
initiating Markdown. See the documentation for each individual
extension for specifics about that extension.

In the event that one or more of the supported extensions are not 
available for import, Markdown will issue a warning and simply continue 
without that extension. 

There may be additional extensions that are distributed with 
Python-Markdown that are not included here in Extra. Those extensions
are not part of PHP Markdown Extra, and therefore, not part of
Python-Markdown Extra. If you really would like Extra to include
additional extensions, we suggest creating your own clone of Extra
under a differant name. You could also edit the `extensions` global 
variable defined below, but be aware that such changes may be lost 
when you upgrade to any future version of Python-Markdown.

"""

import markdown

extensions = ['fenced_code',
              'footnotes',
              'headerid',
              'def_list',
              'tables',
              'abbr',
              ]
              

class ExtraExtension(markdown.Extension):
    """ Add various extensions to Markdown class."""

    def extendMarkdown(self, md, md_globals):
        """ Register extension instances. """
        md.registerExtensions(extensions, self.config)

def makeExtension(configs={}):
    return ExtraExtension(configs=dict(configs))

########NEW FILE########
__FILENAME__ = fenced_code
#!/usr/bin/env python

"""
Fenced Code Extension for Python Markdown
=========================================

This extension adds Fenced Code Blocks to Python-Markdown.

    >>> import markdown
    >>> text = '''
    ... A paragraph before a fenced code block:
    ... 
    ... ~~~
    ... Fenced code block
    ... ~~~
    ... '''
    >>> html = markdown.markdown(text, extensions=['fenced_code'])
    >>> html
    u'<p>A paragraph before a fenced code block:</p>\\n<pre><code>Fenced code block\\n</code></pre>'

Works with safe_mode also (we check this because we are using the HtmlStash):

    >>> markdown.markdown(text, extensions=['fenced_code'], safe_mode='replace')
    u'<p>A paragraph before a fenced code block:</p>\\n<pre><code>Fenced code block\\n</code></pre>'
    
Include tilde's in a code block and wrap with blank lines:

    >>> text = '''
    ... ~~~~~~~~
    ... 
    ... ~~~~
    ... 
    ... ~~~~~~~~'''
    >>> markdown.markdown(text, extensions=['fenced_code'])
    u'<pre><code>\\n~~~~\\n\\n</code></pre>'

Multiple blocks and language tags:

    >>> text = '''
    ... ~~~~{.python}
    ... block one
    ... ~~~~
    ... 
    ... ~~~~.html
    ... <p>block two</p>
    ... ~~~~'''
    >>> markdown.markdown(text, extensions=['fenced_code'])
    u'<pre><code class="python">block one\\n</code></pre>\\n\\n<pre><code class="html">&lt;p&gt;block two&lt;/p&gt;\\n</code></pre>'

Copyright 2007-2008 [Waylan Limberg](http://achinghead.com/).

Project website: <http://www.freewisdom.org/project/python-markdown/Fenced__Code__Blocks>
Contact: markdown@freewisdom.org

License: BSD (see ../docs/LICENSE for details) 

Dependencies:
* [Python 2.3+](http://python.org)
* [Markdown 2.0+](http://www.freewisdom.org/projects/python-markdown/)

"""

import markdown, re

# Global vars
FENCED_BLOCK_RE = re.compile( \
    r'(?P<fence>^~{3,})[ ]*(\{?\.(?P<lang>[a-zA-Z0-9_-]*)\}?)?[ ]*\n(?P<code>.*?)(?P=fence)[ ]*$', 
    re.MULTILINE|re.DOTALL
    )
CODE_WRAP = '<pre><code%s>%s</code></pre>'
LANG_TAG = ' class="%s"'


class FencedCodeExtension(markdown.Extension):

    def extendMarkdown(self, md, md_globals):
        """ Add FencedBlockPreprocessor to the Markdown instance. """

        md.preprocessors.add('fenced_code_block', 
                                 FencedBlockPreprocessor(md), 
                                 "_begin")


class FencedBlockPreprocessor(markdown.preprocessors.Preprocessor):
    
    def run(self, lines):
        """ Match and store Fenced Code Blocks in the HtmlStash. """
        text = "\n".join(lines)
        while 1:
            m = FENCED_BLOCK_RE.search(text)
            if m:
                lang = ''
                if m.group('lang'):
                    lang = LANG_TAG % m.group('lang')
                code = CODE_WRAP % (lang, self._escape(m.group('code')))
                placeholder = self.markdown.htmlStash.store(code, safe=True)
                text = '%s\n%s\n%s'% (text[:m.start()], placeholder, text[m.end():])
            else:
                break
        return text.split("\n")

    def _escape(self, txt):
        """ basic html escaping """
        txt = txt.replace('&', '&amp;')
        txt = txt.replace('<', '&lt;')
        txt = txt.replace('>', '&gt;')
        txt = txt.replace('"', '&quot;')
        return txt


def makeExtension(configs=None):
    return FencedCodeExtension()


if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = footnotes
"""
========================= FOOTNOTES =================================

This section adds footnote handling to markdown.  It can be used as
an example for extending python-markdown with relatively complex
functionality.  While in this case the extension is included inside
the module itself, it could just as easily be added from outside the
module.  Not that all markdown classes above are ignorant about
footnotes.  All footnote functionality is provided separately and
then added to the markdown instance at the run time.

Footnote functionality is attached by calling extendMarkdown()
method of FootnoteExtension.  The method also registers the
extension to allow it's state to be reset by a call to reset()
method.

Example:
    Footnotes[^1] have a label[^label] and a definition[^!DEF].

    [^1]: This is a footnote
    [^label]: A footnote on "label"
    [^!DEF]: The footnote for definition

"""

import re, markdown
from markdown import etree

FN_BACKLINK_TEXT = "zz1337820767766393qq"
NBSP_PLACEHOLDER =  "qq3936677670287331zz"
DEF_RE = re.compile(r'(\ ?\ ?\ ?)\[\^([^\]]*)\]:\s*(.*)')
TABBED_RE = re.compile(r'((\t)|(    ))(.*)')

class FootnoteExtension(markdown.Extension):
    """ Footnote Extension. """

    def __init__ (self, configs):
        """ Setup configs. """
        self.config = {'PLACE_MARKER':
                       ["///Footnotes Go Here///",
                        "The text string that marks where the footnotes go"],
                       'UNIQUE_IDS':
                       [False,
                        "Avoid name collisions across "
                        "multiple calls to reset()."]}

        for key, value in configs:
            self.config[key][0] = value

        # In multiple invocations, emit links that don't get tangled.
        self.unique_prefix = 0

        self.reset()

    def extendMarkdown(self, md, md_globals):
        """ Add pieces to Markdown. """
        md.registerExtension(self)
        self.parser = md.parser
        # Insert a preprocessor before ReferencePreprocessor
        md.preprocessors.add("footnote", FootnotePreprocessor(self),
                             "<reference")
        # Insert an inline pattern before ImageReferencePattern
        FOOTNOTE_RE = r'\[\^([^\]]*)\]' # blah blah [^1] blah
        md.inlinePatterns.add("footnote", FootnotePattern(FOOTNOTE_RE, self),
                              "<reference")
        # Insert a tree-processor that would actually add the footnote div
        # This must be before the inline treeprocessor so inline patterns
        # run on the contents of the div.
        md.treeprocessors.add("footnote", FootnoteTreeprocessor(self),
                                 "<inline")
        # Insert a postprocessor after amp_substitute oricessor
        md.postprocessors.add("footnote", FootnotePostprocessor(self),
                                  ">amp_substitute")

    def reset(self):
        """ Clear the footnotes on reset, and prepare for a distinct document. """
        self.footnotes = markdown.odict.OrderedDict()
        self.unique_prefix += 1

    def findFootnotesPlaceholder(self, root):
        """ Return ElementTree Element that contains Footnote placeholder. """
        def finder(element):
            for child in element:
                if child.text:
                    if child.text.find(self.getConfig("PLACE_MARKER")) > -1:
                        return child, True
                if child.tail:
                    if child.tail.find(self.getConfig("PLACE_MARKER")) > -1:
                        return (child, element), False
                finder(child)
            return None
                
        res = finder(root)
        return res

    def setFootnote(self, id, text):
        """ Store a footnote for later retrieval. """
        self.footnotes[id] = text

    def makeFootnoteId(self, id):
        """ Return footnote link id. """
        if self.getConfig("UNIQUE_IDS"):
            return 'fn:%d-%s' % (self.unique_prefix, id)
        else:
            return 'fn:%s' % id

    def makeFootnoteRefId(self, id):
        """ Return footnote back-link id. """
        if self.getConfig("UNIQUE_IDS"):
            return 'fnref:%d-%s' % (self.unique_prefix, id)
        else:
            return 'fnref:%s' % id

    def makeFootnotesDiv(self, root):
        """ Return div of footnotes as et Element. """

        if not self.footnotes.keys():
            return None

        div = etree.Element("div")
        div.set('class', 'footnote')
        hr = etree.SubElement(div, "hr")
        ol = etree.SubElement(div, "ol")

        for id in self.footnotes.keys():
            li = etree.SubElement(ol, "li")
            li.set("id", self.makeFootnoteId(id))
            self.parser.parseChunk(li, self.footnotes[id])
            backlink = etree.Element("a")
            backlink.set("href", "#" + self.makeFootnoteRefId(id))
            backlink.set("rev", "footnote")
            backlink.set("title", "Jump back to footnote %d in the text" % \
                            (self.footnotes.index(id)+1))
            backlink.text = FN_BACKLINK_TEXT

            if li.getchildren():
                node = li[-1]
                if node.tag == "p":
                    node.text = node.text + NBSP_PLACEHOLDER
                    node.append(backlink)
                else:
                    p = etree.SubElement(li, "p")
                    p.append(backlink)
        return div


class FootnotePreprocessor(markdown.preprocessors.Preprocessor):
    """ Find all footnote references and store for later use. """

    def __init__ (self, footnotes):
        self.footnotes = footnotes

    def run(self, lines):
        lines = self._handleFootnoteDefinitions(lines)
        text = "\n".join(lines)
        return text.split("\n")

    def _handleFootnoteDefinitions(self, lines):
        """
        Recursively find all footnote definitions in lines.

        Keywords:

        * lines: A list of lines of text
        
        Return: A list of lines with footnote definitions removed.
        
        """
        i, id, footnote = self._findFootnoteDefinition(lines)

        if id :
            plain = lines[:i]
            detabbed, theRest = self.detectTabbed(lines[i+1:])
            self.footnotes.setFootnote(id,
                                       footnote + "\n"
                                       + "\n".join(detabbed))
            more_plain = self._handleFootnoteDefinitions(theRest)
            return plain + [""] + more_plain
        else :
            return lines

    def _findFootnoteDefinition(self, lines):
        """
        Find the parts of a footnote definition.

        Keywords:

        * lines: A list of lines of text.

        Return: A three item tuple containing the index of the first line of a
        footnote definition, the id of the definition and the body of the 
        definition.
        
        """
        counter = 0
        for line in lines:
            m = DEF_RE.match(line)
            if m:
                return counter, m.group(2), m.group(3)
            counter += 1
        return counter, None, None

    def detectTabbed(self, lines):
        """ Find indented text and remove indent before further proccesing.

        Keyword arguments:

        * lines: an array of strings

        Returns: a list of post processed items and the unused
        remainder of the original list

        """
        items = []
        item = -1
        i = 0 # to keep track of where we are

        def detab(line):
            match = TABBED_RE.match(line)
            if match:
               return match.group(4)

        for line in lines:
            if line.strip(): # Non-blank line
                line = detab(line)
                if line:
                    items.append(line)
                    i += 1
                    continue
                else:
                    return items, lines[i:]

            else: # Blank line: _maybe_ we are done.
                i += 1 # advance

                # Find the next non-blank line
                for j in range(i, len(lines)):
                    if lines[j].strip():
                        next_line = lines[j]; break
                else:
                    break # There is no more text; we are done.

                # Check if the next non-blank line is tabbed
                if detab(next_line): # Yes, more work to do.
                    items.append("")
                    continue
                else:
                    break # No, we are done.
        else:
            i += 1

        return items, lines[i:]


class FootnotePattern(markdown.inlinepatterns.Pattern):
    """ InlinePattern for footnote markers in a document's body text. """

    def __init__(self, pattern, footnotes):
        markdown.inlinepatterns.Pattern.__init__(self, pattern)
        self.footnotes = footnotes

    def handleMatch(self, m):
        sup = etree.Element("sup")
        a = etree.SubElement(sup, "a")
        id = m.group(2)
        sup.set('id', self.footnotes.makeFootnoteRefId(id))
        a.set('href', '#' + self.footnotes.makeFootnoteId(id))
        a.set('rel', 'footnote')
        a.text = str(self.footnotes.footnotes.index(id) + 1)
        return sup


class FootnoteTreeprocessor(markdown.treeprocessors.Treeprocessor):
    """ Build and append footnote div to end of document. """

    def __init__ (self, footnotes):
        self.footnotes = footnotes

    def run(self, root):
        footnotesDiv = self.footnotes.makeFootnotesDiv(root)
        if footnotesDiv:
            result = self.footnotes.findFootnotesPlaceholder(root)
            if result:
                node, isText = result
                if isText:
                    node.text = None
                    node.getchildren().insert(0, footnotesDiv)
                else:
                    child, element = node
                    ind = element.getchildren().find(child)
                    element.getchildren().insert(ind + 1, footnotesDiv)
                    child.tail = None
                fnPlaceholder.parent.replaceChild(fnPlaceholder, footnotesDiv)
            else:
                root.append(footnotesDiv)

class FootnotePostprocessor(markdown.postprocessors.Postprocessor):
    """ Replace placeholders with html entities. """

    def run(self, text):
        text = text.replace(FN_BACKLINK_TEXT, "&#8617;")
        return text.replace(NBSP_PLACEHOLDER, "&#160;")

def makeExtension(configs=[]):
    """ Return an instance of the FootnoteExtension """
    return FootnoteExtension(configs=configs)


########NEW FILE########
__FILENAME__ = headerid
#!/usr/bin/python

"""
HeaderID Extension for Python-Markdown
======================================

Adds ability to set HTML IDs for headers.

Basic usage:

    >>> import markdown
    >>> text = "# Some Header # {#some_id}"
    >>> md = markdown.markdown(text, ['headerid'])
    >>> md
    u'<h1 id="some_id">Some Header</h1>'

All header IDs are unique:

    >>> text = '''
    ... #Header
    ... #Another Header {#header}
    ... #Third Header {#header}'''
    >>> md = markdown.markdown(text, ['headerid'])
    >>> md
    u'<h1 id="header">Header</h1>\\n<h1 id="header_1">Another Header</h1>\\n<h1 id="header_2">Third Header</h1>'

To fit within a html template's hierarchy, set the header base level:

    >>> text = '''
    ... #Some Header
    ... ## Next Level'''
    >>> md = markdown.markdown(text, ['headerid(level=3)'])
    >>> md
    u'<h3 id="some_header">Some Header</h3>\\n<h4 id="next_level">Next Level</h4>'

Turn off auto generated IDs:

    >>> text = '''
    ... # Some Header
    ... # Header with ID # { #foo }'''
    >>> md = markdown.markdown(text, ['headerid(forceid=False)'])
    >>> md
    u'<h1>Some Header</h1>\\n<h1 id="foo">Header with ID</h1>'

Use with MetaData extension:

    >>> text = '''header_level: 2
    ... header_forceid: Off
    ...
    ... # A Header'''
    >>> md = markdown.markdown(text, ['headerid', 'meta'])
    >>> md
    u'<h2>A Header</h2>'

Copyright 2007-2008 [Waylan Limberg](http://achinghead.com/).

Project website: <http://www.freewisdom.org/project/python-markdown/HeaderId>
Contact: markdown@freewisdom.org

License: BSD (see ../docs/LICENSE for details) 

Dependencies:
* [Python 2.3+](http://python.org)
* [Markdown 2.0+](http://www.freewisdom.org/projects/python-markdown/)

"""

import markdown
from markdown import etree
import re
from string import ascii_lowercase, digits, punctuation

ID_CHARS = ascii_lowercase + digits + '-_'
IDCOUNT_RE = re.compile(r'^(.*)_([0-9]+)$')


class HeaderIdProcessor(markdown.blockprocessors.BlockProcessor):
    """ Replacement BlockProcessor for Header IDs. """

    # Detect a header at start of any line in block
    RE = re.compile(r"""(^|\n)
                        (?P<level>\#{1,6})  # group('level') = string of hashes
                        (?P<header>.*?)     # group('header') = Header text
                        \#*                 # optional closing hashes
                        (?:[ \t]*\{[ \t]*\#(?P<id>[-_:a-zA-Z0-9]+)[ \t]*\})?
                        (\n|$)              #  ^^ group('id') = id attribute
                     """,
                     re.VERBOSE)

    IDs = []

    def test(self, parent, block):
        return bool(self.RE.search(block))

    def run(self, parent, blocks):
        block = blocks.pop(0)
        m = self.RE.search(block)
        if m:
            before = block[:m.start()] # All lines before header
            after = block[m.end():]    # All lines after header
            if before:
                # As the header was not the first line of the block and the
                # lines before the header must be parsed first,
                # recursively parse this lines as a block.
                self.parser.parseBlocks(parent, [before])
            # Create header using named groups from RE
            start_level, force_id = self._get_meta()
            level = len(m.group('level')) + start_level
            if level > 6: 
                level = 6
            h = markdown.etree.SubElement(parent, 'h%d' % level)
            h.text = m.group('header').strip()
            if m.group('id'):
                h.set('id', self._unique_id(m.group('id')))
            elif force_id:
                h.set('id', self._create_id(m.group('header').strip()))
            if after:
                # Insert remaining lines as first block for future parsing.
                blocks.insert(0, after)
        else:
            # This should never happen, but just in case...
            message(CRITICAL, "We've got a problem header!")

    def _get_meta(self):
        """ Return meta data suported by this ext as a tuple """
        level = int(self.config['level'][0]) - 1
        force = self._str2bool(self.config['forceid'][0])
        if hasattr(self.md, 'Meta'):
            if self.md.Meta.has_key('header_level'):
                level = int(self.md.Meta['header_level'][0]) - 1
            if self.md.Meta.has_key('header_forceid'): 
                force = self._str2bool(self.md.Meta['header_forceid'][0])
        return level, force

    def _str2bool(self, s, default=False):
        """ Convert a string to a booleen value. """
        s = str(s)
        if s.lower() in ['0', 'f', 'false', 'off', 'no', 'n']:
            return False
        elif s.lower() in ['1', 't', 'true', 'on', 'yes', 'y']:
            return True
        return default

    def _unique_id(self, id):
        """ Ensure ID is unique. Append '_1', '_2'... if not """
        while id in self.IDs:
            m = IDCOUNT_RE.match(id)
            if m:
                id = '%s_%d'% (m.group(1), int(m.group(2))+1)
            else:
                id = '%s_%d'% (id, 1)
        self.IDs.append(id)
        return id

    def _create_id(self, header):
        """ Return ID from Header text. """
        h = ''
        for c in header.lower().replace(' ', '_'):
            if c in ID_CHARS:
                h += c
            elif c not in punctuation:
                h += '+'
        return self._unique_id(h)


class HeaderIdExtension (markdown.Extension):
    def __init__(self, configs):
        # set defaults
        self.config = {
                'level' : ['1', 'Base level for headers.'],
                'forceid' : ['True', 'Force all headers to have an id.']
            }

        for key, value in configs:
            self.setConfig(key, value)

    def extendMarkdown(self, md, md_globals):
        md.registerExtension(self)
        self.processor = HeaderIdProcessor(md.parser)
        self.processor.md = md
        self.processor.config = self.config
        # Replace existing hasheader in place.
        md.parser.blockprocessors['hashheader'] = self.processor

    def reset(self):
        self.processor.IDs = []


def makeExtension(configs=None):
    return HeaderIdExtension(configs=configs)

if __name__ == "__main__":
    import doctest
    doctest.testmod()


########NEW FILE########
__FILENAME__ = html_tidy
#!/usr/bin/env python

"""
HTML Tidy Extension for Python-Markdown
=======================================

Runs [HTML Tidy][] on the output of Python-Markdown using the [uTidylib][] 
Python wrapper. Both libtidy and uTidylib must be installed on your system.

Note than any Tidy [options][] can be passed in as extension configs. So, 
for example, to output HTML rather than XHTML, set ``output_xhtml=0``. To
indent the output, set ``indent=auto`` and to have Tidy wrap the output in 
``<html>`` and ``<body>`` tags, set ``show_body_only=0``.

[HTML Tidy]: http://tidy.sourceforge.net/
[uTidylib]: http://utidylib.berlios.de/
[options]: http://tidy.sourceforge.net/docs/quickref.html

Copyright (c)2008 [Waylan Limberg](http://achinghead.com)

License: [BSD](http://www.opensource.org/licenses/bsd-license.php) 

Dependencies:
* [Python2.3+](http://python.org)
* [Markdown 2.0+](http://www.freewisdom.org/projects/python-markdown/)
* [HTML Tidy](http://utidylib.berlios.de/)
* [uTidylib](http://utidylib.berlios.de/)

"""

import markdown
import tidy

class TidyExtension(markdown.Extension):

    def __init__(self, configs):
        # Set defaults to match typical markdown behavior.
        self.config = dict(output_xhtml=1,
                           show_body_only=1,
                          )
        # Merge in user defined configs overriding any present if nessecary.
        for c in configs:
            self.config[c[0]] = c[1]

    def extendMarkdown(self, md, md_globals):
        # Save options to markdown instance
        md.tidy_options = self.config
        # Add TidyProcessor to postprocessors
        md.postprocessors['tidy'] = TidyProcessor(md)


class TidyProcessor(markdown.postprocessors.Postprocessor):

    def run(self, text):
        # Pass text to Tidy. As Tidy does not accept unicode we need to encode
        # it and decode its return value.
        return unicode(tidy.parseString(text.encode('utf-8'), 
                                        **self.markdown.tidy_options)) 


def makeExtension(configs=None):
    return TidyExtension(configs=configs)

########NEW FILE########
__FILENAME__ = imagelinks
"""
========================= IMAGE LINKS =================================


Turns paragraphs like

<~~~~~~~~~~~~~~~~~~~~~~~~
dir/subdir
dir/subdir
dir/subdir
~~~~~~~~~~~~~~
dir/subdir
dir/subdir
dir/subdir
~~~~~~~~~~~~~~~~~~~>

Into mini-photo galleries.

"""

import re, markdown
import url_manager


IMAGE_LINK = """<a href="%s"><img src="%s" title="%s"/></a>"""
SLIDESHOW_LINK = """<a href="%s" target="_blank">[slideshow]</a>"""
ALBUM_LINK = """&nbsp;<a href="%s">[%s]</a>"""


class ImageLinksExtension(markdown.Extension):

    def extendMarkdown(self, md, md_globals):

        md.preprocessors.add("imagelink", ImageLinkPreprocessor(md), "_begin")


class ImageLinkPreprocessor(markdown.preprocessors.Preprocessor):

    def run(self, lines):

        url = url_manager.BlogEntryUrl(url_manager.BlogUrl("all"),
                                       "2006/08/29/the_rest_of_our")


        all_images = []
        blocks = []
        in_image_block = False

        new_lines = []
        
        for line in lines:

            if line.startswith("<~~~~~~~"):
                albums = []
                rows = []
                in_image_block = True

            if not in_image_block:

                new_lines.append(line)

            else:

                line = line.strip()
                
                if line.endswith("~~~~~~>") or not line:
                    in_image_block = False
                    new_block = "<div><br/><center><span class='image-links'>\n"

                    album_url_hash = {}

                    for row in rows:
                        for photo_url, title in row:
                            new_block += "&nbsp;"
                            new_block += IMAGE_LINK % (photo_url,
                                                       photo_url.get_thumbnail(),
                                                       title)
                            
                            album_url_hash[str(photo_url.get_album())] = 1
                        
                    new_block += "<br/>"
                            
                    new_block += "</span>"
                    new_block += SLIDESHOW_LINK % url.get_slideshow()

                    album_urls = album_url_hash.keys()
                    album_urls.sort()

                    if len(album_urls) == 1:
                        new_block += ALBUM_LINK % (album_urls[0], "complete album")
                    else :
                        for i in range(len(album_urls)) :
                            new_block += ALBUM_LINK % (album_urls[i],
                                                       "album %d" % (i + 1) )
                    
                    new_lines.append(new_block + "</center><br/></div>")

                elif line[1:6] == "~~~~~" :
                    rows.append([])  # start a new row
                else :
                    parts = line.split()
                    line = parts[0]
                    title = " ".join(parts[1:])

                    album, photo = line.split("/")
                    photo_url = url.get_photo(album, photo,
                                              len(all_images)+1)
                    all_images.append(photo_url)                        
                    rows[-1].append((photo_url, title))

                    if not album in albums :
                        albums.append(album)

        return new_lines


def makeExtension(configs):
    return ImageLinksExtension(configs)


########NEW FILE########
__FILENAME__ = meta
#!usr/bin/python

"""
Meta Data Extension for Python-Markdown
=======================================

This extension adds Meta Data handling to markdown.

Basic Usage:

    >>> import markdown
    >>> text = '''Title: A Test Doc.
    ... Author: Waylan Limberg
    ...         John Doe
    ... Blank_Data:
    ...
    ... The body. This is paragraph one.
    ... '''
    >>> md = markdown.Markdown(['meta'])
    >>> md.convert(text)
    u'<p>The body. This is paragraph one.</p>'
    >>> md.Meta
    {u'blank_data': [u''], u'author': [u'Waylan Limberg', u'John Doe'], u'title': [u'A Test Doc.']}

Make sure text without Meta Data still works (markdown < 1.6b returns a <p>).

    >>> text = '    Some Code - not extra lines of meta data.'
    >>> md = markdown.Markdown(['meta'])
    >>> md.convert(text)
    u'<pre><code>Some Code - not extra lines of meta data.\\n</code></pre>'
    >>> md.Meta
    {}

Copyright 2007-2008 [Waylan Limberg](http://achinghead.com).

Project website: <http://www.freewisdom.org/project/python-markdown/Meta-Data>
Contact: markdown@freewisdom.org

License: BSD (see ../docs/LICENSE for details)

"""

import markdown, re

# Global Vars
META_RE = re.compile(r'^[ ]{0,3}(?P<key>[A-Za-z0-9_-]+):\s*(?P<value>.*)')
META_MORE_RE = re.compile(r'^[ ]{4,}(?P<value>.*)')

class MetaExtension (markdown.Extension):
    """ Meta-Data extension for Python-Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Add MetaPreprocessor to Markdown instance. """

        md.preprocessors.add("meta", MetaPreprocessor(md), "_begin")


class MetaPreprocessor(markdown.preprocessors.Preprocessor):
    """ Get Meta-Data. """

    def run(self, lines):
        """ Parse Meta-Data and store in Markdown.Meta. """
        meta = {}
        key = None
        while 1:
            line = lines.pop(0)
            if line.strip() == '':
                break # blank line - done
            m1 = META_RE.match(line)
            if m1:
                key = m1.group('key').lower().strip()
                meta[key] = [m1.group('value').strip()]
            else:
                m2 = META_MORE_RE.match(line)
                if m2 and key:
                    # Add another line to existing key
                    meta[key].append(m2.group('value').strip())
                else:
                    lines.insert(0, line)
                    break # no meta data - done
        self.markdown.Meta = meta
        return lines
        

def makeExtension(configs={}):
    return MetaExtension(configs=configs)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = rss
import markdown
from markdown import etree

DEFAULT_URL = "http://www.freewisdom.org/projects/python-markdown/"
DEFAULT_CREATOR = "Yuri Takhteyev"
DEFAULT_TITLE = "Markdown in Python"
GENERATOR = "http://www.freewisdom.org/projects/python-markdown/markdown2rss"

month_map = { "Jan" : "01",
              "Feb" : "02",
              "March" : "03",
              "April" : "04",
              "May" : "05",
              "June" : "06",
              "July" : "07",
              "August" : "08",
              "September" : "09",
              "October" : "10",
              "November" : "11",
              "December" : "12" }

def get_time(heading):

    heading = heading.split("-")[0]
    heading = heading.strip().replace(",", " ").replace(".", " ")

    month, date, year = heading.split()
    month = month_map[month]

    return rdftime(" ".join((month, date, year, "12:00:00 AM")))

def rdftime(time):

    time = time.replace(":", " ")
    time = time.replace("/", " ")
    time = time.split()
    return "%s-%s-%sT%s:%s:%s-08:00" % (time[0], time[1], time[2],
                                        time[3], time[4], time[5])


def get_date(text):
    return "date"

class RssExtension (markdown.Extension):

    def extendMarkdown(self, md, md_globals):

        self.config = { 'URL' : [DEFAULT_URL, "Main URL"],
                        'CREATOR' : [DEFAULT_CREATOR, "Feed creator's name"],
                        'TITLE' : [DEFAULT_TITLE, "Feed title"] }

        md.xml_mode = True
        
        # Insert a tree-processor that would actually add the title tag
        treeprocessor = RssTreeProcessor(md)
        treeprocessor.ext = self
        md.treeprocessors['rss'] = treeprocessor
        md.stripTopLevelTags = 0
        md.docType = '<?xml version="1.0" encoding="utf-8"?>\n'

class RssTreeProcessor(markdown.treeprocessors.Treeprocessor):

    def run (self, root):

        rss = etree.Element("rss")
        rss.set("version", "2.0")

        channel = etree.SubElement(rss, "channel")

        for tag, text in (("title", self.ext.getConfig("TITLE")),
                          ("link", self.ext.getConfig("URL")),
                          ("description", None)):
            
            element = etree.SubElement(channel, tag)
            element.text = text

        for child in root:

            if child.tag in ["h1", "h2", "h3", "h4", "h5"]:
      
                heading = child.text.strip()
                item = etree.SubElement(channel, "item")
                link = etree.SubElement(item, "link")
                link.text = self.ext.getConfig("URL")
                title = etree.SubElement(item, "title")
                title.text = heading

                guid = ''.join([x for x in heading if x.isalnum()])
                guidElem = etree.SubElement(item, "guid")
                guidElem.text = guid
                guidElem.set("isPermaLink", "false")

            elif child.tag in ["p"]:
                try:
                    description = etree.SubElement(item, "description")
                except UnboundLocalError:
                    # Item not defined - moving on
                    pass
                else:
                    if len(child):
                        content = "\n".join([etree.tostring(node)
                                             for node in child])
                    else:
                        content = child.text
                    pholder = self.markdown.htmlStash.store(
                                                "<![CDATA[ %s]]>" % content)
                    description.text = pholder
    
        return rss


def makeExtension(configs):

    return RssExtension(configs)

########NEW FILE########
__FILENAME__ = tables
#!/usr/bin/env Python
"""
Tables Extension for Python-Markdown
====================================

Added parsing of tables to Python-Markdown.

A simple example:

    First Header  | Second Header
    ------------- | -------------
    Content Cell  | Content Cell
    Content Cell  | Content Cell

Copyright 2009 - [Waylan Limberg](http://achinghead.com)
"""
import markdown
from markdown import etree


class TableProcessor(markdown.blockprocessors.BlockProcessor):
    """ Process Tables. """

    def test(self, parent, block):
        rows = block.split('\n')
        return (len(rows) > 2 and '|' in rows[0] and 
                '|' in rows[1] and '-' in rows[1] and 
                rows[1][0] in ['|', ':', '-'])

    def run(self, parent, blocks):
        """ Parse a table block and build table. """
        block = blocks.pop(0).split('\n')
        header = block[:2]
        rows = block[2:]
        # Get format type (bordered by pipes or not)
        border = False
        if header[0].startswith('|'):
            border = True
        # Get alignment of columns
        align = []
        for c in self._split_row(header[1], border):
            if c.startswith(':') and c.endswith(':'):
                align.append('center')
            elif c.startswith(':'):
                align.append('left')
            elif c.endswith(':'):
                align.append('right')
            else:
                align.append(None)
        # Build table
        table = etree.SubElement(parent, 'table')
        thead = etree.SubElement(table, 'thead')
        self._build_row(header[0], thead, align, border)
        tbody = etree.SubElement(table, 'tbody')
        for row in rows:
            self._build_row(row, tbody, align, border)

    def _build_row(self, row, parent, align, border):
        """ Given a row of text, build table cells. """
        tr = etree.SubElement(parent, 'tr')
        tag = 'td'
        if parent.tag == 'thead':
            tag = 'th'
        cells = self._split_row(row, border)
        # We use align here rather than cells to ensure every row 
        # contains the same number of columns.
        for i, a in enumerate(align):
            c = etree.SubElement(tr, tag)
            try:
                c.text = cells[i].strip()
            except IndexError:
                c.text = ""
            if a:
                c.set('align', a)

    def _split_row(self, row, border):
        """ split a row of text into list of cells. """
        if border:
            if row.startswith('|'):
                row = row[1:]
            if row.endswith('|'):
                row = row[:-1]
        return row.split('|')


class TableExtension(markdown.Extension):
    """ Add tables to Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Add an instance of TableProcessor to BlockParser. """
        md.parser.blockprocessors.add('table', 
                                      TableProcessor(md.parser),
                                      '<hashheader')


def makeExtension(configs={}):
    return TableExtension(configs=configs)

########NEW FILE########
__FILENAME__ = toc
"""
Table of Contents Extension for Python-Markdown
* * *

(c) 2008 [Jack Miller](http://codezen.org)

Dependencies:
* [Markdown 2.0+](http://www.freewisdom.org/projects/python-markdown/)

"""
import markdown
from markdown import etree
import re

class TocTreeprocessor(markdown.treeprocessors.Treeprocessor):
    # Iterator wrapper to get parent and child all at once
    def iterparent(self, root):
        for parent in root.getiterator():
            for child in parent:
                yield parent, child

    def run(self, doc):
        div = etree.Element("div")
        div.attrib["class"] = "toc"
        last_li = None

        # Add title to the div
        if self.config["title"][0]:
            header = etree.SubElement(div, "span")
            header.attrib["class"] = "toctitle"
            header.text = self.config["title"][0]

        level = 0
        list_stack=[div]
        header_rgx = re.compile("[Hh][123456]")

        # Get a list of id attributes
        used_ids = []
        for c in doc.getiterator():
            if "id" in c.attrib:
                used_ids.append(c.attrib["id"])

        for (p, c) in self.iterparent(doc):
            if not c.text:
                continue

            # To keep the output from screwing up the
            # validation by putting a <div> inside of a <p>
            # we actually replace the <p> in its entirety.
            # We do not allow the marker inside a header as that
            # would causes an enless loop of placing a new TOC 
            # inside previously generated TOC.

            if c.text.find(self.config["marker"][0]) > -1 and not header_rgx.match(c.tag):
                for i in range(len(p)):
                    if p[i] == c:
                        p[i] = div
                        break
                    
            if header_rgx.match(c.tag):
                tag_level = int(c.tag[-1])
                
                while tag_level < level:
                    list_stack.pop()
                    level -= 1

                if tag_level > level:
                    newlist = etree.Element("ul")
                    if last_li:
                        last_li.append(newlist)
                    else:
                        list_stack[-1].append(newlist)
                    list_stack.append(newlist)
                    level += 1

                # Do not override pre-existing ids 
                if not "id" in c.attrib:
                    id = self.config["slugify"][0](c.text)
                    if id in used_ids:
                        ctr = 1
                        while "%s_%d" % (id, ctr) in used_ids:
                            ctr += 1
                        id = "%s_%d" % (id, ctr)
                    used_ids.append(id)
                    c.attrib["id"] = id
                else:
                    id = c.attrib["id"]

                # List item link, to be inserted into the toc div
                last_li = etree.Element("li")
                link = etree.SubElement(last_li, "a")
                link.text = c.text
                link.attrib["href"] = '#' + id

                if int(self.config["anchorlink"][0]):
                    anchor = etree.SubElement(c, "a")
                    anchor.text = c.text
                    anchor.attrib["href"] = "#" + id
                    anchor.attrib["class"] = "toclink"
                    c.text = ""

                list_stack[-1].append(last_li)

class TocExtension(markdown.Extension):
    def __init__(self, configs):
        self.config = { "marker" : ["[TOC]", 
                            "Text to find and replace with Table of Contents -"
                            "Defaults to \"[TOC]\""],
                        "slugify" : [self.slugify,
                            "Function to generate anchors based on header text-"
                            "Defaults to a built in slugify function."],
                        "title" : [None,
                            "Title to insert into TOC <div> - "
                            "Defaults to None"],
                        "anchorlink" : [0,
                            "1 if header should be a self link"
                            "Defaults to 0"]}

        for key, value in configs:
            self.setConfig(key, value)

    # This is exactly the same as Django's slugify
    def slugify(self, value):
        """ Slugify a string, to make it URL friendly. """
        import unicodedata
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
        value = unicode(re.sub('[^\w\s-]', '', value).strip().lower())
        return re.sub('[-\s]+','-',value)

    def extendMarkdown(self, md, md_globals):
        tocext = TocTreeprocessor(md)
        tocext.config = self.config
        md.treeprocessors.add("toc", tocext, "_begin")
	
def makeExtension(configs={}):
    return TocExtension(configs=configs)

########NEW FILE########
__FILENAME__ = wikilinks
#!/usr/bin/env python

'''
WikiLinks Extension for Python-Markdown
======================================

Converts [[WikiLinks]] to relative links.  Requires Python-Markdown 2.0+

Basic usage:

    >>> import markdown
    >>> text = "Some text with a [[WikiLink]]."
    >>> html = markdown.markdown(text, ['wikilinks'])
    >>> html
    u'<p>Some text with a <a class="wikilink" href="/WikiLink/">WikiLink</a>.</p>'

Whitespace behavior:

    >>> markdown.markdown('[[ foo bar_baz ]]', ['wikilinks'])
    u'<p><a class="wikilink" href="/foo_bar_baz/">foo bar_baz</a></p>'
    >>> markdown.markdown('foo [[ ]] bar', ['wikilinks'])
    u'<p>foo  bar</p>'

To define custom settings the simple way:

    >>> markdown.markdown(text, 
    ...     ['wikilinks(base_url=/wiki/,end_url=.html,html_class=foo)']
    ... )
    u'<p>Some text with a <a class="foo" href="/wiki/WikiLink.html">WikiLink</a>.</p>'
    
Custom settings the complex way:

    >>> md = markdown.Markdown(
    ...     extensions = ['wikilinks'], 
    ...     extension_configs = {'wikilinks': [
    ...                                 ('base_url', 'http://example.com/'), 
    ...                                 ('end_url', '.html'),
    ...                                 ('html_class', '') ]},
    ...     safe_mode = True)
    >>> md.convert(text)
    u'<p>Some text with a <a href="http://example.com/WikiLink.html">WikiLink</a>.</p>'

Use MetaData with mdx_meta.py (Note the blank html_class in MetaData):

    >>> text = """wiki_base_url: http://example.com/
    ... wiki_end_url:   .html
    ... wiki_html_class:
    ...
    ... Some text with a [[WikiLink]]."""
    >>> md = markdown.Markdown(extensions=['meta', 'wikilinks'])
    >>> md.convert(text)
    u'<p>Some text with a <a href="http://example.com/WikiLink.html">WikiLink</a>.</p>'

MetaData should not carry over to next document:

    >>> md.convert("No [[MetaData]] here.")
    u'<p>No <a class="wikilink" href="/MetaData/">MetaData</a> here.</p>'

Define a custom URL builder:

    >>> def my_url_builder(label, base, end):
    ...     return '/bar/'
    >>> md = markdown.Markdown(extensions=['wikilinks'], 
    ...         extension_configs={'wikilinks' : [('build_url', my_url_builder)]})
    >>> md.convert('[[foo]]')
    u'<p><a class="wikilink" href="/bar/">foo</a></p>'

From the command line:

    python markdown.py -x wikilinks(base_url=http://example.com/,end_url=.html,html_class=foo) src.txt

By [Waylan Limberg](http://achinghead.com/).

License: [BSD](http://www.opensource.org/licenses/bsd-license.php) 

Dependencies:
* [Python 2.3+](http://python.org)
* [Markdown 2.0+](http://www.freewisdom.org/projects/python-markdown/)
'''

import markdown
import re

def build_url(label, base, end):
    """ Build a url from the label, a base, and an end. """
    clean_label = re.sub(r'([ ]+_)|(_[ ]+)|([ ]+)', '_', label)
    return '%s%s%s'% (base, clean_label, end)


class WikiLinkExtension(markdown.Extension):
    def __init__(self, configs):
        # set extension defaults
        self.config = {
                        'base_url' : ['/', 'String to append to beginning or URL.'],
                        'end_url' : ['/', 'String to append to end of URL.'],
                        'html_class' : ['wikilink', 'CSS hook. Leave blank for none.'],
                        'build_url' : [build_url, 'Callable formats URL from label.'],
        }
        
        # Override defaults with user settings
        for key, value in configs :
            self.setConfig(key, value)
        
    def extendMarkdown(self, md, md_globals):
        self.md = md
    
        # append to end of inline patterns
        WIKILINK_RE = r'\[\[([A-Za-z0-9_ -]+)\]\]'
        wikilinkPattern = WikiLinks(WIKILINK_RE, self.config)
        wikilinkPattern.md = md
        md.inlinePatterns.add('wikilink', wikilinkPattern, "<not_strong")


class WikiLinks(markdown.inlinepatterns.Pattern):
    def __init__(self, pattern, config):
        markdown.inlinepatterns.Pattern.__init__(self, pattern)
        self.config = config
  
    def handleMatch(self, m):
        if m.group(2).strip():
            base_url, end_url, html_class = self._getMeta()
            label = m.group(2).strip()
            url = self.config['build_url'][0](label, base_url, end_url)
            a = markdown.etree.Element('a')
            a.text = label 
            a.set('href', url)
            if html_class:
                a.set('class', html_class)
        else:
            a = ''
        return a

    def _getMeta(self):
        """ Return meta data or config data. """
        base_url = self.config['base_url'][0]
        end_url = self.config['end_url'][0]
        html_class = self.config['html_class'][0]
        if hasattr(self.md, 'Meta'):
            if self.md.Meta.has_key('wiki_base_url'):
                base_url = self.md.Meta['wiki_base_url'][0]
            if self.md.Meta.has_key('wiki_end_url'):
                end_url = self.md.Meta['wiki_end_url'][0]
            if self.md.Meta.has_key('wiki_html_class'):
                html_class = self.md.Meta['wiki_html_class'][0]
        return base_url, end_url, html_class
    

def makeExtension(configs=None) :
    return WikiLinkExtension(configs=configs)


if __name__ == "__main__":
    import doctest
    doctest.testmod()


########NEW FILE########
__FILENAME__ = html4
# markdown/html4.py
#
# Add html4 serialization to older versions of Elementree
# Taken from ElementTree 1.3 preview with slight modifications
#
# Copyright (c) 1999-2007 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2007 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------


import markdown
ElementTree = markdown.etree.ElementTree
QName = markdown.etree.QName
Comment = markdown.etree.Comment
PI = markdown.etree.PI
ProcessingInstruction = markdown.etree.ProcessingInstruction

HTML_EMPTY = ("area", "base", "basefont", "br", "col", "frame", "hr",
              "img", "input", "isindex", "link", "meta" "param")

try:
    HTML_EMPTY = set(HTML_EMPTY)
except NameError:
    pass

_namespace_map = {
    # "well-known" namespace prefixes
    "http://www.w3.org/XML/1998/namespace": "xml",
    "http://www.w3.org/1999/xhtml": "html",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
    "http://schemas.xmlsoap.org/wsdl/": "wsdl",
    # xml schema
    "http://www.w3.org/2001/XMLSchema": "xs",
    "http://www.w3.org/2001/XMLSchema-instance": "xsi",
    # dublic core
    "http://purl.org/dc/elements/1.1/": "dc",
}


def _raise_serialization_error(text):
    raise TypeError(
        "cannot serialize %r (type %s)" % (text, type(text).__name__)
        )

def _encode(text, encoding):
    try:
        return text.encode(encoding, "xmlcharrefreplace")
    except (TypeError, AttributeError):
        _raise_serialization_error(text)

def _escape_cdata(text, encoding):
    # escape character data
    try:
        # it's worth avoiding do-nothing calls for strings that are
        # shorter than 500 character, or so.  assume that's, by far,
        # the most common case in most applications.
        if "&" in text:
            text = text.replace("&", "&amp;")
        if "<" in text:
            text = text.replace("<", "&lt;")
        if ">" in text:
            text = text.replace(">", "&gt;")
        return text.encode(encoding, "xmlcharrefreplace")
    except (TypeError, AttributeError):
        _raise_serialization_error(text)


def _escape_attrib(text, encoding):
    # escape attribute value
    try:
        if "&" in text:
            text = text.replace("&", "&amp;")
        if "<" in text:
            text = text.replace("<", "&lt;")
        if ">" in text:
            text = text.replace(">", "&gt;")
        if "\"" in text:
            text = text.replace("\"", "&quot;")
        if "\n" in text:
            text = text.replace("\n", "&#10;")
        return text.encode(encoding, "xmlcharrefreplace")
    except (TypeError, AttributeError):
        _raise_serialization_error(text)

def _escape_attrib_html(text, encoding):
    # escape attribute value
    try:
        if "&" in text:
            text = text.replace("&", "&amp;")
        if ">" in text:
            text = text.replace(">", "&gt;")
        if "\"" in text:
            text = text.replace("\"", "&quot;")
        return text.encode(encoding, "xmlcharrefreplace")
    except (TypeError, AttributeError):
        _raise_serialization_error(text)


def _serialize_html(write, elem, encoding, qnames, namespaces):
    tag = elem.tag
    text = elem.text
    if tag is Comment:
        write("<!--%s-->" % _escape_cdata(text, encoding))
    elif tag is ProcessingInstruction:
        write("<?%s?>" % _escape_cdata(text, encoding))
    else:
        tag = qnames[tag]
        if tag is None:
            if text:
                write(_escape_cdata(text, encoding))
            for e in elem:
                _serialize_html(write, e, encoding, qnames, None)
        else:
            write("<" + tag)
            items = elem.items()
            if items or namespaces:
                items.sort() # lexical order
                for k, v in items:
                    if isinstance(k, QName):
                        k = k.text
                    if isinstance(v, QName):
                        v = qnames[v.text]
                    else:
                        v = _escape_attrib_html(v, encoding)
                    # FIXME: handle boolean attributes
                    write(" %s=\"%s\"" % (qnames[k], v))
                if namespaces:
                    items = namespaces.items()
                    items.sort(key=lambda x: x[1]) # sort on prefix
                    for v, k in items:
                        if k:
                            k = ":" + k
                        write(" xmlns%s=\"%s\"" % (
                            k.encode(encoding),
                            _escape_attrib(v, encoding)
                            ))
            write(">")
            tag = tag.lower()
            if text:
                if tag == "script" or tag == "style":
                    write(_encode(text, encoding))
                else:
                    write(_escape_cdata(text, encoding))
            for e in elem:
                _serialize_html(write, e, encoding, qnames, None)
            if tag not in HTML_EMPTY:
                write("</" + tag + ">")
    if elem.tail:
        write(_escape_cdata(elem.tail, encoding))

def write_html(root, f,
          # keyword arguments
          encoding="us-ascii",
          default_namespace=None):
    assert root is not None
    if not hasattr(f, "write"):
        f = open(f, "wb")
    write = f.write
    if not encoding:
        encoding = "us-ascii"
    qnames, namespaces = _namespaces(
            root, encoding, default_namespace
            )
    _serialize_html(
                write, root, encoding, qnames, namespaces
                )

# --------------------------------------------------------------------
# serialization support

def _namespaces(elem, encoding, default_namespace=None):
    # identify namespaces used in this tree

    # maps qnames to *encoded* prefix:local names
    qnames = {None: None}

    # maps uri:s to prefixes
    namespaces = {}
    if default_namespace:
        namespaces[default_namespace] = ""

    def encode(text):
        return text.encode(encoding)

    def add_qname(qname):
        # calculate serialized qname representation
        try:
            if qname[:1] == "{":
                uri, tag = qname[1:].split("}", 1)
                prefix = namespaces.get(uri)
                if prefix is None:
                    prefix = _namespace_map.get(uri)
                    if prefix is None:
                        prefix = "ns%d" % len(namespaces)
                    if prefix != "xml":
                        namespaces[uri] = prefix
                if prefix:
                    qnames[qname] = encode("%s:%s" % (prefix, tag))
                else:
                    qnames[qname] = encode(tag) # default element
            else:
                if default_namespace:
                    # FIXME: can this be handled in XML 1.0?
                    raise ValueError(
                        "cannot use non-qualified names with "
                        "default_namespace option"
                        )
                qnames[qname] = encode(qname)
        except TypeError:
            _raise_serialization_error(qname)

    # populate qname and namespaces table
    try:
        iterate = elem.iter
    except AttributeError:
        iterate = elem.getiterator # cET compatibility
    for elem in iterate():
        tag = elem.tag
        if isinstance(tag, QName) and tag.text not in qnames:
            add_qname(tag.text)
        elif isinstance(tag, basestring):
            if tag not in qnames:
                add_qname(tag)
        elif tag is not None and tag is not Comment and tag is not PI:
            _raise_serialization_error(tag)
        for key, value in elem.items():
            if isinstance(key, QName):
                key = key.text
            if key not in qnames:
                add_qname(key)
            if isinstance(value, QName) and value.text not in qnames:
                add_qname(value.text)
        text = elem.text
        if isinstance(text, QName) and text.text not in qnames:
            add_qname(text.text)
    return qnames, namespaces

def to_html_string(element, encoding=None):
    class dummy:
        pass
    data = []
    file = dummy()
    file.write = data.append
    write_html(ElementTree(element).getroot(),file,encoding)
    return "".join(data)

########NEW FILE########
__FILENAME__ = inlinepatterns
"""
INLINE PATTERNS
=============================================================================

Inline patterns such as *emphasis* are handled by means of auxiliary
objects, one per pattern.  Pattern objects must be instances of classes
that extend markdown.Pattern.  Each pattern object uses a single regular
expression and needs support the following methods:

    pattern.getCompiledRegExp() # returns a regular expression

    pattern.handleMatch(m) # takes a match object and returns
                           # an ElementTree element or just plain text

All of python markdown's built-in patterns subclass from Pattern,
but you can add additional patterns that don't.

Also note that all the regular expressions used by inline must
capture the whole block.  For this reason, they all start with
'^(.*)' and end with '(.*)!'.  In case with built-in expression
Pattern takes care of adding the "^(.*)" and "(.*)!".

Finally, the order in which regular expressions are applied is very
important - e.g. if we first replace http://.../ links with <a> tags
and _then_ try to replace inline html, we would end up with a mess.
So, we apply the expressions in the following order:

* escape and backticks have to go before everything else, so
  that we can preempt any markdown patterns by escaping them.

* then we handle auto-links (must be done before inline html)

* then we handle inline HTML.  At this point we will simply
  replace all inline HTML strings with a placeholder and add
  the actual HTML to a hash.

* then inline images (must be done before links)

* then bracketed links, first regular then reference-style

* finally we apply strong and emphasis
"""

import markdown
import re
from urlparse import urlparse, urlunparse
import sys
if sys.version >= "3.0":
    from html import entities as htmlentitydefs
else:
    import htmlentitydefs

"""
The actual regular expressions for patterns
-----------------------------------------------------------------------------
"""

NOBRACKET = r'[^\]\[]*'
BRK = ( r'\[('
        + (NOBRACKET + r'(\[')*6
        + (NOBRACKET+ r'\])*')*6
        + NOBRACKET + r')\]' )
NOIMG = r'(?<!\!)'

BACKTICK_RE = r'(?<!\\)(`+)(.+?)(?<!`)\2(?!`)' # `e=f()` or ``e=f("`")``
ESCAPE_RE = r'\\(.)'                             # \<
EMPHASIS_RE = r'(\*)([^\*]+)\2'                    # *emphasis*
STRONG_RE = r'(\*{2}|_{2})(.+?)\2'                      # **strong**
STRONG_EM_RE = r'(\*{3}|_{3})(.+?)\2'            # ***strong***

if markdown.SMART_EMPHASIS:
    EMPHASIS_2_RE = r'(?<!\w)(_)(\S.+?)\2(?!\w)'        # _emphasis_
else:
    EMPHASIS_2_RE = r'(_)(.+?)\2'                 # _emphasis_

LINK_RE = NOIMG + BRK + \
r'''\(\s*(<.*?>|((?:(?:\(.*?\))|[^\(\)]))*?)\s*((['"])(.*?)\12)?\)'''
# [text](url) or [text](<url>)

IMAGE_LINK_RE = r'\!' + BRK + r'\s*\((<.*?>|([^\)]*))\)'
# ![alttxt](http://x.com/) or ![alttxt](<http://x.com/>)
REFERENCE_RE = NOIMG + BRK+ r'\s*\[([^\]]*)\]'           # [Google][3]
IMAGE_REFERENCE_RE = r'\!' + BRK + '\s*\[([^\]]*)\]' # ![alt text][2]
NOT_STRONG_RE = r'((^| )(\*|_)( |$))'                        # stand-alone * or _
AUTOLINK_RE = r'<((?:f|ht)tps?://[^>]*)>'        # <http://www.123.com>
AUTOMAIL_RE = r'<([^> \!]*@[^> ]*)>'               # <me@example.com>

HTML_RE = r'(\<([a-zA-Z/][^\>]*?|\!--.*?--)\>)'               # <...>
ENTITY_RE = r'(&[\#a-zA-Z0-9]*;)'               # &amp;
LINE_BREAK_RE = r'  \n'                     # two spaces at end of line
LINE_BREAK_2_RE = r'  $'                    # two spaces at end of text


def dequote(string):
    """Remove quotes from around a string."""
    if ( ( string.startswith('"') and string.endswith('"'))
         or (string.startswith("'") and string.endswith("'")) ):
        return string[1:-1]
    else:
        return string

ATTR_RE = re.compile("\{@([^\}]*)=([^\}]*)}") # {@id=123}

def handleAttributes(text, parent):
    """Set values of an element based on attribute definitions ({@id=123})."""
    def attributeCallback(match):
        parent.set(match.group(1), match.group(2).replace('\n', ' '))
    return ATTR_RE.sub(attributeCallback, text)


"""
The pattern classes
-----------------------------------------------------------------------------
"""

class Pattern:
    """Base class that inline patterns subclass. """

    def __init__ (self, pattern, markdown_instance=None):
        """
        Create an instant of an inline pattern.

        Keyword arguments:

        * pattern: A regular expression that matches a pattern

        """
        self.pattern = pattern
        self.compiled_re = re.compile("^(.*?)%s(.*?)$" % pattern, re.DOTALL)

        # Api for Markdown to pass safe_mode into instance
        self.safe_mode = False
        if markdown_instance:
            self.markdown = markdown_instance

    def getCompiledRegExp (self):
        """ Return a compiled regular expression. """
        return self.compiled_re

    def handleMatch(self, m):
        """Return a ElementTree element from the given match.

        Subclasses should override this method.

        Keyword arguments:

        * m: A re match object containing a match of the pattern.

        """
        pass

    def type(self):
        """ Return class name, to define pattern type """
        return self.__class__.__name__

BasePattern = Pattern # for backward compatibility

class SimpleTextPattern (Pattern):
    """ Return a simple text of group(2) of a Pattern. """
    def handleMatch(self, m):
        text = m.group(2)
        if text == markdown.INLINE_PLACEHOLDER_PREFIX:
            return None
        return text

class SimpleTagPattern (Pattern):
    """
    Return element of type `tag` with a text attribute of group(3)
    of a Pattern.

    """
    def __init__ (self, pattern, tag):
        Pattern.__init__(self, pattern)
        self.tag = tag

    def handleMatch(self, m):
        el = markdown.etree.Element(self.tag)
        el.text = m.group(3)
        return el


class SubstituteTagPattern (SimpleTagPattern):
    """ Return a eLement of type `tag` with no children. """
    def handleMatch (self, m):
        return markdown.etree.Element(self.tag)


class BacktickPattern (Pattern):
    """ Return a `<code>` element containing the matching text. """
    def __init__ (self, pattern):
        Pattern.__init__(self, pattern)
        self.tag = "code"

    def handleMatch(self, m):
        el = markdown.etree.Element(self.tag)
        el.text = markdown.AtomicString(m.group(3).strip())
        return el


class DoubleTagPattern (SimpleTagPattern):
    """Return a ElementTree element nested in tag2 nested in tag1.

    Useful for strong emphasis etc.

    """
    def handleMatch(self, m):
        tag1, tag2 = self.tag.split(",")
        el1 = markdown.etree.Element(tag1)
        el2 = markdown.etree.SubElement(el1, tag2)
        el2.text = m.group(3)
        return el1


class HtmlPattern (Pattern):
    """ Store raw inline html and return a placeholder. """
    def handleMatch (self, m):
        rawhtml = m.group(2)
        inline = True
        place_holder = self.markdown.htmlStash.store(rawhtml)
        return place_holder


class LinkPattern (Pattern):
    """ Return a link element from the given match. """
    def handleMatch(self, m):
        el = markdown.etree.Element("a")
        el.text = m.group(2)
        title = m.group(11)
        href = m.group(9)

        if href:
            if href[0] == "<":
                href = href[1:-1]
            el.set("href", self.sanitize_url(href.strip()))
        else:
            el.set("href", "")

        if title:
            title = dequote(title) #.replace('"', "&quot;")
            el.set("title", title)
        return el

    def sanitize_url(self, url):
        """
        Sanitize a url against xss attacks in "safe_mode".

        Rather than specifically blacklisting `javascript:alert("XSS")` and all
        its aliases (see <http://ha.ckers.org/xss.html>), we whitelist known
        safe url formats. Most urls contain a network location, however some
        are known not to (i.e.: mailto links). Script urls do not contain a
        location. Additionally, for `javascript:...`, the scheme would be
        "javascript" but some aliases will appear to `urlparse()` to have no
        scheme. On top of that relative links (i.e.: "foo/bar.html") have no
        scheme. Therefore we must check "path", "parameters", "query" and
        "fragment" for any literal colons. We don't check "scheme" for colons
        because it *should* never have any and "netloc" must allow the form:
        `username:password@host:port`.

        """
        locless_schemes = ['', 'mailto', 'news']
        scheme, netloc, path, params, query, fragment = url = urlparse(url)
        safe_url = False
        if netloc != '' or scheme in locless_schemes:
            safe_url = True

        for part in url[2:]:
            if ":" in part:
                safe_url = False

        if self.markdown.safeMode and not safe_url:
            return ''
        else:
            return urlunparse(url)

class ImagePattern(LinkPattern):
    """ Return a img element from the given match. """
    def handleMatch(self, m):
        el = markdown.etree.Element("img")
        src_parts = m.group(9).split()
        if src_parts:
            src = src_parts[0]
            if src[0] == "<" and src[-1] == ">":
                src = src[1:-1]
            el.set('src', self.sanitize_url(src))
        else:
            el.set('src', "")
        if len(src_parts) > 1:
            el.set('title', dequote(" ".join(src_parts[1:])))

        if markdown.ENABLE_ATTRIBUTES:
            truealt = handleAttributes(m.group(2), el)
        else:
            truealt = m.group(2)

        el.set('alt', truealt)
        return el

class ReferencePattern(LinkPattern):
    """ Match to a stored reference and return link element. """
    def handleMatch(self, m):
        if m.group(9):
            id = m.group(9).lower()
        else:
            # if we got something like "[Google][]"
            # we'll use "google" as the id
            id = m.group(2).lower()

        if not id in self.markdown.references: # ignore undefined refs
            return None
        href, title = self.markdown.references[id]

        text = m.group(2)
        return self.makeTag(href, title, text)

    def makeTag(self, href, title, text):
        el = markdown.etree.Element('a')

        el.set('href', self.sanitize_url(href))
        if title:
            el.set('title', title)

        el.text = text
        return el


class ImageReferencePattern (ReferencePattern):
    """ Match to a stored reference and return img element. """
    def makeTag(self, href, title, text):
        el = markdown.etree.Element("img")
        el.set("src", self.sanitize_url(href))
        if title:
            el.set("title", title)
        el.set("alt", text)
        return el


class AutolinkPattern (Pattern):
    """ Return a link Element given an autolink (`<http://example/com>`). """
    def handleMatch(self, m):
        el = markdown.etree.Element("a")
        el.set('href', m.group(2))
        el.text = markdown.AtomicString(m.group(2))
        return el

class AutomailPattern (Pattern):
    """
    Return a mailto link Element given an automail link (`<foo@example.com>`).
    """
    def handleMatch(self, m):
        el = markdown.etree.Element('a')
        email = m.group(2)
        if email.startswith("mailto:"):
            email = email[len("mailto:"):]

        def codepoint2name(code):
            """Return entity definition by code, or the code if not defined."""
            entity = htmlentitydefs.codepoint2name.get(code)
            if entity:
                return "%s%s;" % (markdown.AMP_SUBSTITUTE, entity)
            else:
                return "%s#%d;" % (markdown.AMP_SUBSTITUTE, code)

        letters = [codepoint2name(ord(letter)) for letter in email]
        el.text = markdown.AtomicString(''.join(letters))

        mailto = "mailto:" + email
        mailto = "".join([markdown.AMP_SUBSTITUTE + '#%d;' %
                          ord(letter) for letter in mailto])
        el.set('href', mailto)
        return el


########NEW FILE########
__FILENAME__ = odict
class OrderedDict(dict):
    """
    A dictionary that keeps its keys in the order in which they're inserted.
    
    Copied from Django's SortedDict with some modifications.

    """
    def __new__(cls, *args, **kwargs):
        instance = super(OrderedDict, cls).__new__(cls, *args, **kwargs)
        instance.keyOrder = []
        return instance

    def __init__(self, data=None):
        if data is None:
            data = {}
        super(OrderedDict, self).__init__(data)
        if isinstance(data, dict):
            self.keyOrder = data.keys()
        else:
            self.keyOrder = []
            for key, value in data:
                if key not in self.keyOrder:
                    self.keyOrder.append(key)

    def __deepcopy__(self, memo):
        from copy import deepcopy
        return self.__class__([(key, deepcopy(value, memo))
                               for key, value in self.iteritems()])

    def __setitem__(self, key, value):
        super(OrderedDict, self).__setitem__(key, value)
        if key not in self.keyOrder:
            self.keyOrder.append(key)

    def __delitem__(self, key):
        super(OrderedDict, self).__delitem__(key)
        self.keyOrder.remove(key)

    def __iter__(self):
        for k in self.keyOrder:
            yield k

    def pop(self, k, *args):
        result = super(OrderedDict, self).pop(k, *args)
        try:
            self.keyOrder.remove(k)
        except ValueError:
            # Key wasn't in the dictionary in the first place. No problem.
            pass
        return result

    def popitem(self):
        result = super(OrderedDict, self).popitem()
        self.keyOrder.remove(result[0])
        return result

    def items(self):
        return zip(self.keyOrder, self.values())

    def iteritems(self):
        for key in self.keyOrder:
            yield key, super(OrderedDict, self).__getitem__(key)

    def keys(self):
        return self.keyOrder[:]

    def iterkeys(self):
        return iter(self.keyOrder)

    def values(self):
        return [super(OrderedDict, self).__getitem__(k) for k in self.keyOrder]

    def itervalues(self):
        for key in self.keyOrder:
            yield super(OrderedDict, self).__getitem__(key)

    def update(self, dict_):
        for k, v in dict_.items():
            self.__setitem__(k, v)

    def setdefault(self, key, default):
        if key not in self.keyOrder:
            self.keyOrder.append(key)
        return super(OrderedDict, self).setdefault(key, default)

    def value_for_index(self, index):
        """Return the value of the item at the given zero-based index."""
        return self[self.keyOrder[index]]

    def insert(self, index, key, value):
        """Insert the key, value pair before the item with the given index."""
        if key in self.keyOrder:
            n = self.keyOrder.index(key)
            del self.keyOrder[n]
            if n < index:
                index -= 1
        self.keyOrder.insert(index, key)
        super(OrderedDict, self).__setitem__(key, value)

    def copy(self):
        """Return a copy of this object."""
        # This way of initializing the copy means it works for subclasses, too.
        obj = self.__class__(self)
        obj.keyOrder = self.keyOrder[:]
        return obj

    def __repr__(self):
        """
        Replace the normal dict.__repr__ with a version that returns the keys
        in their sorted order.
        """
        return '{%s}' % ', '.join(['%r: %r' % (k, v) for k, v in self.items()])

    def clear(self):
        super(OrderedDict, self).clear()
        self.keyOrder = []

    def index(self, key):
        """ Return the index of a given key. """
        return self.keyOrder.index(key)

    def index_for_location(self, location):
        """ Return index or None for a given location. """
        if location == '_begin':
            i = 0
        elif location == '_end':
            i = None
        elif location.startswith('<') or location.startswith('>'):
            i = self.index(location[1:])
            if location.startswith('>'):
                if i >= len(self):
                    # last item
                    i = None
                else:
                    i += 1
        else:
            raise ValueError('Not a valid location: "%s". Location key '
                             'must start with a ">" or "<".' % location)
        return i

    def add(self, key, value, location):
        """ Insert by key location. """
        i = self.index_for_location(location)
        if i is not None:
            self.insert(i, key, value)
        else:
            self.__setitem__(key, value)

    def link(self, key, location):
        """ Change location of an existing item. """
        n = self.keyOrder.index(key)
        del self.keyOrder[n]
        i = self.index_for_location(location)
        try:
            if i is not None:
                self.keyOrder.insert(i, key)
            else:
                self.keyOrder.append(key)
        except Error:
            # restore to prevent data loss and reraise
            self.keyOrder.insert(n, key)
            raise Error

########NEW FILE########
__FILENAME__ = postprocessors
"""
POST-PROCESSORS
=============================================================================

Markdown also allows post-processors, which are similar to preprocessors in
that they need to implement a "run" method. However, they are run after core
processing.

"""


import markdown

class Processor:
    def __init__(self, markdown_instance=None):
        if markdown_instance:
            self.markdown = markdown_instance

class Postprocessor(Processor):
    """
    Postprocessors are run after the ElementTree it converted back into text.

    Each Postprocessor implements a "run" method that takes a pointer to a
    text string, modifies it as necessary and returns a text string.

    Postprocessors must extend markdown.Postprocessor.

    """

    def run(self, text):
        """
        Subclasses of Postprocessor should implement a `run` method, which
        takes the html document as a single text string and returns a
        (possibly modified) string.

        """
        pass


class RawHtmlPostprocessor(Postprocessor):
    """ Restore raw html to the document. """

    def run(self, text):
        """ Iterate over html stash and restore "safe" html. """
        for i in range(self.markdown.htmlStash.html_counter):
            html, safe  = self.markdown.htmlStash.rawHtmlBlocks[i]
            if self.markdown.safeMode and not safe:
                if str(self.markdown.safeMode).lower() == 'escape':
                    html = self.escape(html)
                elif str(self.markdown.safeMode).lower() == 'remove':
                    html = ''
                else:
                    html = markdown.HTML_REMOVED_TEXT
            if safe or not self.markdown.safeMode:
                text = text.replace("<p>%s</p>" % 
                            (markdown.preprocessors.HTML_PLACEHOLDER % i),
                            html + "\n")
            text =  text.replace(markdown.preprocessors.HTML_PLACEHOLDER % i, 
                                 html)
        return text

    def escape(self, html):
        """ Basic html escaping """
        html = html.replace('&', '&amp;')
        html = html.replace('<', '&lt;')
        html = html.replace('>', '&gt;')
        return html.replace('"', '&quot;')


class AndSubstitutePostprocessor(Postprocessor):
    """ Restore valid entities """
    def __init__(self):
        pass

    def run(self, text):
        text =  text.replace(markdown.AMP_SUBSTITUTE, "&")
        return text

########NEW FILE########
__FILENAME__ = preprocessors

"""
PRE-PROCESSORS
=============================================================================

Preprocessors work on source text before we start doing anything too
complicated. 
"""

import re
import markdown

HTML_PLACEHOLDER_PREFIX = markdown.STX+"wzxhzdk:"
HTML_PLACEHOLDER = HTML_PLACEHOLDER_PREFIX + "%d" + markdown.ETX

class Processor:
    def __init__(self, markdown_instance=None):
        if markdown_instance:
            self.markdown = markdown_instance

class Preprocessor (Processor):
    """
    Preprocessors are run after the text is broken into lines.

    Each preprocessor implements a "run" method that takes a pointer to a
    list of lines of the document, modifies it as necessary and returns
    either the same pointer or a pointer to a new list.

    Preprocessors must extend markdown.Preprocessor.

    """
    def run(self, lines):
        """
        Each subclass of Preprocessor should override the `run` method, which
        takes the document as a list of strings split by newlines and returns
        the (possibly modified) list of lines.

        """
        pass

class HtmlStash:
    """
    This class is used for stashing HTML objects that we extract
    in the beginning and replace with place-holders.
    """

    def __init__ (self):
        """ Create a HtmlStash. """
        self.html_counter = 0 # for counting inline html segments
        self.rawHtmlBlocks=[]

    def store(self, html, safe=False):
        """
        Saves an HTML segment for later reinsertion.  Returns a
        placeholder string that needs to be inserted into the
        document.

        Keyword arguments:

        * html: an html segment
        * safe: label an html segment as safe for safemode

        Returns : a placeholder string

        """
        self.rawHtmlBlocks.append((html, safe))
        placeholder = HTML_PLACEHOLDER % self.html_counter
        self.html_counter += 1
        return placeholder

    def reset(self):
        self.html_counter = 0
        self.rawHtmlBlocks = []


class HtmlBlockPreprocessor(Preprocessor):
    """Remove html blocks from the text and store them for later retrieval."""

    right_tag_patterns = ["</%s>", "%s>"]

    def _get_left_tag(self, block):
        return block[1:].replace(">", " ", 1).split()[0].lower()

    def _get_right_tag(self, left_tag, block):
        for p in self.right_tag_patterns:
            tag = p % left_tag
            i = block.rfind(tag)
            if i > 2:
                return tag.lstrip("<").rstrip(">"), i + len(p)-2 + len(left_tag)
        return block.rstrip()[-len(left_tag)-2:-1].lower(), len(block)

    def _equal_tags(self, left_tag, right_tag):
        if left_tag == 'div' or left_tag[0] in ['?', '@', '%']: # handle PHP, etc.
            return True
        if ("/" + left_tag) == right_tag:
            return True
        if (right_tag == "--" and left_tag == "--"):
            return True
        elif left_tag == right_tag[1:] \
            and right_tag[0] != "<":
            return True
        else:
            return False

    def _is_oneliner(self, tag):
        return (tag in ['hr', 'hr/'])

    def run(self, lines):
        text = "\n".join(lines)
        new_blocks = []
        text = text.split("\n\n")
        items = []
        left_tag = ''
        right_tag = ''
        in_tag = False # flag

        while text:
            block = text[0]
            if block.startswith("\n"):
                block = block[1:]
            text = text[1:]

            if block.startswith("\n"):
                block = block[1:]

            if not in_tag:
                if block.startswith("<"):
                    left_tag = self._get_left_tag(block)
                    right_tag, data_index = self._get_right_tag(left_tag, block)

                    if block[1] == "!":
                        # is a comment block
                        left_tag = "--"
                        right_tag, data_index = self._get_right_tag(left_tag, block)
                        # keep checking conditions below and maybe just append
                    
                    if data_index < len(block) \
                        and markdown.isBlockLevel(left_tag): 
                        text.insert(0, block[data_index:])
                        block = block[:data_index]

                    if not (markdown.isBlockLevel(left_tag) \
                        or block[1] in ["!", "?", "@", "%"]):
                        new_blocks.append(block)
                        continue

                    if self._is_oneliner(left_tag):
                        new_blocks.append(block.strip())
                        continue

                    if block.rstrip().endswith(">") \
                        and self._equal_tags(left_tag, right_tag):
                        new_blocks.append(
                            self.markdown.htmlStash.store(block.strip()))
                        continue
                    else: #if not block[1] == "!":
                        # if is block level tag and is not complete

                        if markdown.isBlockLevel(left_tag) or left_tag == "--" \
                            and not block.rstrip().endswith(">"):
                            items.append(block.strip())
                            in_tag = True
                        else:
                            new_blocks.append(
                            self.markdown.htmlStash.store(block.strip()))

                        continue

                new_blocks.append(block)

            else:
                items.append(block.strip())

                right_tag, data_index = self._get_right_tag(left_tag, block)

                if self._equal_tags(left_tag, right_tag):
                    # if find closing tag
                    in_tag = False
                    new_blocks.append(
                        self.markdown.htmlStash.store('\n\n'.join(items)))
                    items = []

        if items:
            new_blocks.append(self.markdown.htmlStash.store('\n\n'.join(items)))
            new_blocks.append('\n')

        new_text = "\n\n".join(new_blocks)
        return new_text.split("\n")


class ReferencePreprocessor(Preprocessor):
    """ Remove reference definitions from text and store for later use. """

    RE = re.compile(r'^(\ ?\ ?\ ?)\[([^\]]*)\]:\s*([^ ]*)(.*)$', re.DOTALL)

    def run (self, lines):
        new_text = [];
        for line in lines:
            m = self.RE.match(line)
            if m:
                id = m.group(2).strip().lower()
                t = m.group(4).strip()  # potential title
                if not t:
                    self.markdown.references[id] = (m.group(3), t)
                elif (len(t) >= 2
                      and (t[0] == t[-1] == "\""
                           or t[0] == t[-1] == "\'"
                           or (t[0] == "(" and t[-1] == ")") ) ):
                    self.markdown.references[id] = (m.group(3), t[1:-1])
                else:
                    new_text.append(line)
            else:
                new_text.append(line)

        return new_text #+ "\n"

########NEW FILE########
__FILENAME__ = treeprocessors
import markdown
import re

def isString(s):
    """ Check if it's string """
    return isinstance(s, unicode) or isinstance(s, str)

class Processor:
    def __init__(self, markdown_instance=None):
        if markdown_instance:
            self.markdown = markdown_instance

class Treeprocessor(Processor):
    """
    Treeprocessors are run on the ElementTree object before serialization.

    Each Treeprocessor implements a "run" method that takes a pointer to an
    ElementTree, modifies it as necessary and returns an ElementTree
    object.

    Treeprocessors must extend markdown.Treeprocessor.

    """
    def run(self, root):
        """
        Subclasses of Treeprocessor should implement a `run` method, which
        takes a root ElementTree. This method can return another ElementTree 
        object, and the existing root ElementTree will be replaced, or it can 
        modify the current tree and return None.
        """
        pass


class InlineProcessor(Treeprocessor):
    """
    A Treeprocessor that traverses a tree, applying inline patterns.
    """

    def __init__ (self, md):
        self.__placeholder_prefix = markdown.INLINE_PLACEHOLDER_PREFIX
        self.__placeholder_suffix = markdown.ETX
        self.__placeholder_length = 4 + len(self.__placeholder_prefix) \
                                      + len(self.__placeholder_suffix)
        self.__placeholder_re = re.compile(markdown.INLINE_PLACEHOLDER % r'([0-9]{4})')
        self.markdown = md

    def __makePlaceholder(self, type):
        """ Generate a placeholder """
        id = "%04d" % len(self.stashed_nodes)
        hash = markdown.INLINE_PLACEHOLDER % id
        return hash, id

    def __findPlaceholder(self, data, index):
        """
        Extract id from data string, start from index

        Keyword arguments:

        * data: string
        * index: index, from which we start search

        Returns: placeholder id and string index, after the found placeholder.
        """

        m = self.__placeholder_re.search(data, index)
        if m:
            return m.group(1), m.end()
        else:
            return None, index + 1

    def __stashNode(self, node, type):
        """ Add node to stash """
        placeholder, id = self.__makePlaceholder(type)
        self.stashed_nodes[id] = node
        return placeholder

    def __handleInline(self, data, patternIndex=0):
        """
        Process string with inline patterns and replace it
        with placeholders

        Keyword arguments:

        * data: A line of Markdown text
        * patternIndex: The index of the inlinePattern to start with

        Returns: String with placeholders.

        """
        if not isinstance(data, markdown.AtomicString):
            startIndex = 0
            while patternIndex < len(self.markdown.inlinePatterns):
                data, matched, startIndex = self.__applyPattern(
                    self.markdown.inlinePatterns.value_for_index(patternIndex),
                    data, patternIndex, startIndex)
                if not matched:
                    patternIndex += 1
        return data

    def __processElementText(self, node, subnode, isText=True):
        """
        Process placeholders in Element.text or Element.tail
        of Elements popped from self.stashed_nodes.

        Keywords arguments:

        * node: parent node
        * subnode: processing node
        * isText: bool variable, True - it's text, False - it's tail

        Returns: None

        """
        if isText:
            text = subnode.text
            subnode.text = None
        else:
            text = subnode.tail
            subnode.tail = None

        childResult = self.__processPlaceholders(text, subnode)

        if not isText and node is not subnode:
            pos = node.getchildren().index(subnode)
            node.remove(subnode)
        else:
            pos = 0

        childResult.reverse()
        for newChild in childResult:
            node.insert(pos, newChild)

    def __processPlaceholders(self, data, parent):
        """
        Process string with placeholders and generate ElementTree tree.

        Keyword arguments:

        * data: string with placeholders instead of ElementTree elements.
        * parent: Element, which contains processing inline data

        Returns: list with ElementTree elements with applied inline patterns.
        """
        def linkText(text):
            if text:
                if result:
                    if result[-1].tail:
                        result[-1].tail += text
                    else:
                        result[-1].tail = text
                else:
                    if parent.text:
                        parent.text += text
                    else:
                        parent.text = text

        result = []
        strartIndex = 0
        while data:
            index = data.find(self.__placeholder_prefix, strartIndex)
            if index != -1:
                id, phEndIndex = self.__findPlaceholder(data, index)

                if id in self.stashed_nodes:
                    node = self.stashed_nodes.get(id)

                    if index > 0:
                        text = data[strartIndex:index]
                        linkText(text)

                    if not isString(node): # it's Element
                        for child in [node] + node.getchildren():
                            if child.tail:
                                if child.tail.strip():
                                    self.__processElementText(node, child, False)
                            if child.text:
                                if child.text.strip():
                                    self.__processElementText(child, child)
                    else: # it's just a string
                        linkText(node)
                        strartIndex = phEndIndex
                        continue

                    strartIndex = phEndIndex
                    result.append(node)

                else: # wrong placeholder
                    end = index + len(prefix)
                    linkText(data[strartIndex:end])
                    strartIndex = end
            else:
                text = data[strartIndex:]
                linkText(text)
                data = ""

        return result

    def __applyPattern(self, pattern, data, patternIndex, startIndex=0):
        """
        Check if the line fits the pattern, create the necessary
        elements, add it to stashed_nodes.

        Keyword arguments:

        * data: the text to be processed
        * pattern: the pattern to be checked
        * patternIndex: index of current pattern
        * startIndex: string index, from which we starting search

        Returns: String with placeholders instead of ElementTree elements.

        """
        match = pattern.getCompiledRegExp().match(data[startIndex:])
        leftData = data[:startIndex]

        if not match:
            return data, False, 0

        node = pattern.handleMatch(match)

        if node is None:
            return data, True, len(leftData) + match.span(len(match.groups()))[0]

        if not isString(node):
            if not isinstance(node.text, markdown.AtomicString):
                # We need to process current node too
                for child in [node] + node.getchildren():
                    if not isString(node):
                        if child.text:
                            child.text = self.__handleInline(child.text,
                                                            patternIndex + 1)
                        if child.tail:
                            child.tail = self.__handleInline(child.tail,
                                                            patternIndex)

        placeholder = self.__stashNode(node, pattern.type())

        return "%s%s%s%s" % (leftData,
                             match.group(1),
                             placeholder, match.groups()[-1]), True, 0

    def run(self, tree):
        """Apply inline patterns to a parsed Markdown tree.

        Iterate over ElementTree, find elements with inline tag, apply inline
        patterns and append newly created Elements to tree.  If you don't
        want process your data with inline paterns, instead of normal string,
        use subclass AtomicString:

            node.text = markdown.AtomicString("data won't be processed with inline patterns")

        Arguments:

        * markdownTree: ElementTree object, representing Markdown tree.

        Returns: ElementTree object with applied inline patterns.

        """
        self.stashed_nodes = {}

        stack = [tree]

        while stack:
            currElement = stack.pop()
            insertQueue = []
            for child in currElement.getchildren():
                if child.text and not isinstance(child.text, markdown.AtomicString):
                    text = child.text
                    child.text = None
                    lst = self.__processPlaceholders(self.__handleInline(
                                                    text), child)
                    stack += lst
                    insertQueue.append((child, lst))

                if child.getchildren():
                    stack.append(child)

            for element, lst in insertQueue:
                if element.text:
                    element.text = \
                        markdown.inlinepatterns.handleAttributes(element.text, 
                                                                 element)
                i = 0
                for newChild in lst:
                    # Processing attributes
                    if newChild.tail:
                        newChild.tail = \
                            markdown.inlinepatterns.handleAttributes(newChild.tail,
                                                                     element)
                    if newChild.text:
                        newChild.text = \
                            markdown.inlinepatterns.handleAttributes(newChild.text,
                                                                     newChild)
                    element.insert(i, newChild)
                    i += 1
        return tree


class PrettifyTreeprocessor(Treeprocessor):
    """ Add linebreaks to the html document. """

    def _prettifyETree(self, elem):
        """ Recursively add linebreaks to ElementTree children. """

        i = "\n"
        if markdown.isBlockLevel(elem.tag) and elem.tag not in ['code', 'pre']:
            if (not elem.text or not elem.text.strip()) \
                    and len(elem) and markdown.isBlockLevel(elem[0].tag):
                elem.text = i
            for e in elem:
                if markdown.isBlockLevel(e.tag):
                    self._prettifyETree(e)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        if not elem.tail or not elem.tail.strip():
            elem.tail = i

    def run(self, root):
        """ Add linebreaks to ElementTree root object. """

        self._prettifyETree(root)
        # Do <br />'s seperately as they are often in the middle of
        # inline content and missed by _prettifyETree.
        brs = root.getiterator('br')
        for br in brs:
            if not br.tail or not br.tail.strip():
                br.tail = '\n'
            else:
                br.tail = '\n%s' % br.tail

########NEW FILE########
__FILENAME__ = middleware
from userstorage.utils import activate, deactivate

class UserStorage:
    def process_request(self, request):
        activate(request)

    def process_exception(self, request, exception):
        deactivate(request)

    def process_response(self, request, response):
        deactivate(request)
        return response

########NEW FILE########
__FILENAME__ = utils
from threading import currentThread

_active = {}

def activate(request):
    if request and request.user:
        _active[currentThread()] = request.user

def deactivate(request):
    global _active
    if currentThread() in _active:
        del _active[currentThread()]

def get_user():
    if currentThread() not in _active:
        return None
    return _active[currentThread()]

########NEW FILE########
__FILENAME__ = base

########NEW FILE########
__FILENAME__ = context
from urllib import urlencode
from django.conf import settings


def context(request):
    data = {}
    data["request"] = request
    data["user"] = request.user
    data["public_key"] = settings.ARECIBO_PUBLIC_ACCOUNT_NUMBER
    data["private_key"] = settings.ARECIBO_PRIVATE_ACCOUNT_NUMBER
    data["site_url"] = settings.SITE_URL.strip()
    data["anonymous_access"] = settings.ANONYMOUS_ACCESS

    qs = request.GET.copy()
    if "page" in qs:
        del qs["page"]

    data["qs"] = ""
    if qs:
        data["qs"] = "%s" % urlencode(qs)

    return data

########NEW FILE########
__FILENAME__ = decorators
from django.contrib.auth.decorators import user_passes_test
from django.conf import settings


def arecibo_login_required(func):
    return user_passes_test(lambda u: settings.ANONYMOUS_ACCESS or u.is_staff)(func)
########NEW FILE########
__FILENAME__ = errors
from exceptions import Exception

from django.template import RequestContext, loader
from django.http import HttpResponse


class StatusDoesNotExist(Exception): pass


def not_found_error(request):
    t = loader.get_template('404.html')
    c = RequestContext(request)
    return HttpResponse(t.render(c), status=404)


def application_error(request):
    t = loader.get_template('500.html')
    c = RequestContext(request)
    return HttpResponse(t.render(c), status=500)
########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.html import conditional_escape
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe


def as_blue_print(self):
    return self._html_output(u"""
    <div class="span-8 clear">
        <div %(html_class_attr)s>
            %(label)s<br />
            %(errors)s
            <span class="help">%(help_text)s</span>
            %(field)s
        </div>
    </div>
    """, u'%s', '', u'%s', False)


class Form(forms.Form):
    required_css_class = 'required'

    def as_custom(self):
        return as_blue_print(self)


class ModelForm(forms.ModelForm):
    required_css_class = 'required'

    def as_custom(self):
        return as_blue_print(self)


def as_div(self):
    if not self:
        return u''
    template = "%s"
    errors = ''.join([u'<p class="field-error">%s</p>' % conditional_escape(force_unicode(e)) for e in self])
    template = template % errors
    return mark_safe(template)


forms.util.ErrorList.__unicode__ = as_div

########NEW FILE########
__FILENAME__ = groups
from django.core.management.base import BaseCommand

from error.models import Error
from error.models import Group
from error.signals import error_created

class Command(BaseCommand):
    help = 'Drops groups and then refires signals on addons, recreating the groups'

    def handle(self, *args, **options):
        groups = Group.objects.all()
        print 'Deleting %s group(s)' % groups.count()
   	groups.delete()

        for error in Error.objects.all():
            error_created.send(sender=Error, instance=error)        

########NEW FILE########
__FILENAME__ = middleware
from django.conf import settings

class Middleware:
    def process_request(self, request):
        request.view_access = (settings.ANONYMOUS_ACCESS or
                               request.user.is_authenticated())
        request.write_access = request.user.is_authenticated()
########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = paginator
from django.core.paginator import Paginator as BasePaginator
from django.core.paginator import Page, InvalidPage, EmptyPage

class Paginator(BasePaginator):
    def page(self, number):
        "Returns a Page object for the given 1-based page number."
        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page
        queryset = self.object_list[:(number * self.per_page)+1]
        results = queryset[bottom:top]
        try:
            queryset[top]
            self._num_pages = number + 1
        except IndexError:
            self._num_pages = number

        return Page(results, number, self)
    

def get_page(request, paginator):
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    try:
        page = paginator.page(page)
    except (EmptyPage, InvalidPage):
        page = paginator.page(paginator.num_pages)

    return page
########NEW FILE########
__FILENAME__ = tags

########NEW FILE########
__FILENAME__ = arecibo
from app.utils import trunc_string
from django.template.defaultfilters import stringfilter
from django import template

register = template.Library()


@register.filter
@stringfilter
def trunc(value, arg):
    return trunc_string(value, arg)

########NEW FILE########
__FILENAME__ = tests
# test data
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase

try:
    account = settings.ARECIBO_PUBLIC_ACCOUNT_NUMBER
except ImportError:
    account = "1231241243"
        
test_data = {
    "account": account,
    "priority": 4,
    "user_agent": "Mozilla/5.0 (Macintosh; U; Intel Mac OS X...",
    "url": "http://badapp.org/-\ufffdwe-cant-lose",
    "uid": "123124123123",
    "ip": "127.0.0.1",
    "type": "Test from python",
    "status": "403",
    "server": "Test Script",
    "request": """This is the bit that goes in the request""",
    "username": "Jimbob",
    "msg": """
Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut
labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris
nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit
esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in
culpa qui officia deserunt mollit anim id est laborum
""",
    "traceback": """Traceback (most recent call last",:
File "<stdin>", line 1, in <module>
ZeroDivisionError: integer division or modulo by zero  df
""",}

class TestAppNotAnon(TestCase):
    fixtures = ['users.json']
    
    def setUp(self):
        settings.ANONYMOUS_ACCESS = False
        self.url = reverse('setup')

    def test_auth(self):
        assert self.client.login(username='admin', password='password')
        
    def test_decorator(self):
        res = self.client.get(self.url)
        assert res.status_code == 302

    def test_decorator_logged_in(self):
        assert self.client.login(username='admin', password='password')
        res = self.client.get(self.url)
        assert res.status_code == 200

class TestAppAnon(TestCase):
    fixtures = ['users.json']
    
    def setUp(self):
        settings.ANONYMOUS_ACCESS = True
        self.url = reverse('setup')

    def test_decorator_anon(self):
        res = self.client.get(self.url)
        assert res.status_code == 200

    def test_decorator_anon_logged_in(self):
        assert self.client.login(username='admin', password='password')
        res = self.client.get(self.url)
        assert res.status_code == 200

########NEW FILE########
__FILENAME__ = test_runner
import os

from django.conf import settings
from django.test.simple import DjangoTestSuiteRunner

from django.core import mail
from django.core.mail.backends import locmem

from django.core.mail.message import EmailMessage


# amongst other things this will suppress those annoying logs
settings.DEBUG = False


class AreciboRunner(DjangoTestSuiteRunner):
    def setup_test_environment(self, **kwargs):
        msgs = 'django.contrib.messages.context_processors.messages'
        if msgs not in settings.TEMPLATE_CONTEXT_PROCESSORS:
            tcp = list(settings.TEMPLATE_CONTEXT_PROCESSORS)
            tcp.append(msgs)
            settings.TEMPLATE_CONTEXT_PROCESSORS = tuple(tcp)
        settings.DEBUG_PROPAGATE_EXCEPTIONS = True
        settings.CELERY_ALWAYS_EAGER = True
        super(AreciboRunner, self).setup_test_environment(**kwargs)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^$', 'app.views.index', name="index"),
    url(r'^lib/error.js', 'app.views.javascript_client', name="error-javascript"),
    url(r'^lib/error-compress.js', 'app.views.javascript_client', name="error-javascript-compressed"),
    url(r'^setup$', 'app.views.setup', name="setup")
)

########NEW FILE########
__FILENAME__ = utils
# general utils
try:
    import hashlib
except ImportError:
    import md5 as hashlib
import itertools
import logging
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import simplejson
from django.utils.encoding import smart_unicode
from django.core.cache import cache
from django.core.urlresolvers import reverse

from urlparse import urlparse, urlunparse

try:
    from functools import update_wrapper, wraps
except ImportError:
    from django.utils.functional import update_wrapper, wraps  # Python 2.3, 2.4 fallback.


def log(msg):
    if settings.DEBUG:
        logging.info(" Arecibo: %s" % msg)


def safe_int(key, result=None):
    try:
        return int(key)
    except (ValueError, AttributeError):
        return result


def render_plain(msg):
    return HttpResponse(msg, mimetype="text/plain")


def render_json(view_func):
    def wrapper(*args, **kwargs):
        data = view_func(*args, **kwargs)
        return HttpResponse(simplejson.dumps(data), mimetype='application/json')
    return wrapper


def not_allowed(request):
    return HttpResponseRedirect(reverse("not-allowed"))


def safe_string(text, result=""):
    try:
        return str(text)
    except (ValueError, AttributeError):
        return result


def trunc_string(text, length, ellipsis="..."):
    try:
        if len(text) < length:
            return text
        else:
            return "%s%s" % (text[:length-len(ellipsis)], ellipsis)
    except TypeError:
        return ""


def has_private_key(view_func):
    """Will check that the person accessing the page is doing
    so with the private URL """
    def wrapper(*args, **kwargs):
        request = args[0]
        if settings.ARECIBO_PRIVATE_ACCOUNT_NUMBER not in request.get_full_path().split("/"):
            return HttpResponseRedirect(settings.LOGIN_URL)
        return view_func(*args, **kwargs)
    return wraps(view_func)(wrapper)


def break_url(url):
    result = {"raw": url}
    parsed = list(urlparse(url))
    result["protocol"] = parsed[0]
    result["domain"] = parsed[1]
    result["query"] = urlunparse(["",""] + parsed[2:])
    return result


def redirect(name):
    return HttpResponseRedirect(reverse(name))


def memoize(prefix, time=60):
    """
    A simple memoize that caches into memcache, using a simple
    key based on stringing args and kwargs. Keep args simple.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            key = hashlib.md5()
            for arg in itertools.chain(args, kwargs):
                key.update(str(arg))
            key = 'memoize:%s:%s' % (prefix, key.hexdigest())
            data = cache.get(key)
            if data is not None:
                return data
            data = func(*args, **kwargs)
            cache.set(key, data, time)
            return data
        return wrapper
    return decorator

########NEW FILE########
__FILENAME__ = views
import os
from urlparse import urlparse

from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseRedirect
from django.views.generic.simple import direct_to_template
from django.core.urlresolvers import reverse
from django.conf import settings
from django.views.decorators.vary import vary_on_headers
from django.views.decorators.cache import cache_control
from django.contrib.messages.api import info

from app.decorators import arecibo_login_required

# Static_resource cache decorator will be used for things which can safely
# be cached to improve client HTTP performance
static_resource = cache_control(public=True, max_age=86400)


def index(request):
    if ((request.user.is_authenticated and request.user.is_staff) or
        settings.ANONYMOUS_ACCESS):
        return HttpResponseRedirect(reverse("error-list"))
    return direct_to_template(request, "index.html")


def not_allowed(request):
    return direct_to_template(request, "403.html")


@arecibo_login_required
def setup(request):
    return direct_to_template(request, "setup.html", extra_context={
        "nav": {"selected": "setup"},
        "app_id": os.environ.get("APPLICATION_ID"),
        })


@static_resource
@vary_on_headers("Accept-Encoding")
def javascript_client(request):
    return direct_to_template(request, "error.js",
        extra_context = {
            "domain": urlparse(settings.SITE_URL)[1]
        },
        mimetype = "text/javascript",
    )


def login(request):
    return HttpResponseRedirect(users.create_login_url("/"))

########NEW FILE########
__FILENAME__ = default_public
from error.models import Error

from error import signals

def default_public(instance, **kw):
    instance.public = True
    instance.save()

signals.error_created.connect(default_public, dispatch_uid="default_public")

########NEW FILE########
__FILENAME__ = no_notifications
from notifications.listeners import default_notification
from error.signals import error_created

error_created.disconnect(default_notification, dispatch_uid="default_notification")


########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from error.models import Error, Group


class ErrorAdmin(admin.ModelAdmin):
    pass


class GroupAdmin(admin.ModelAdmin):
    pass


admin.site.register(Error, ErrorAdmin)
admin.site.register(Group, GroupAdmin)

########NEW FILE########
__FILENAME__ = agent
import urllib
import re

from ConfigParser import SafeConfigParser as ConfigParser
from StringIO import StringIO

from django.core.cache import cache

from app.utils import log


class Browser(object):
    def __init__(self, capabilities):
        self.lazy_flag = True
        self.cap = capabilities

    def parse(self):
        for name, value in self.cap.items():
            if name in ["tables", "aol", "javaapplets",
                       "activexcontrols", "backgroundsounds",
                       "vbscript", "win16", "javascript", "cdf",
                       "wap", "crawler", "netclr", "beta",
                        "iframes", "frames", "stripper", "wap"]:
                self.cap[name] = (value.strip().lower() == "true")
            elif name in ["ecmascriptversion", "w3cdomversion"]:
                self.cap[name] = float(value)
            elif name in ["css"]:
                self.cap[name] = int(value)
            else:
                self.cap[name] = value
        self.lazy_flag = False

    def __repr__(self):
        if self.lazy_flag: self.parse()
        return repr(self.cap)

    def get(self, name, default=None):
        if self.lazy_flag: self.parse()
        try:
            return self[name]
        except KeyError:
            return default

    def __getitem__(self, name):
        if self.lazy_flag: self.parse()
        return self.cap[name.lower()]

    def keys(self):
        return self.cap.keys()

    def items(self):
        if self.lazy_flag: self.parse()
        return self.cap.items()

    def values(self):
        if self.lazy_flag: self.parse()
        return self.cap.values()

    def __len__(self):
        return len(self.cap)

    def supports(self, feature):
        value = self.cap.get(feature)
        if value == None:
            return False
        return value

    def features(self):
        l = []
        for f in ["tables", "frames", "iframes", "javascript",
                  "cookies", "w3cdomversion", "wap"]:
            if self.supports(f):
                l.append(f)
        if self.supports_java():
            l.append("java")
        if self.supports_activex():
            l.append("activex")
        css = self.css_version()
        if css > 0:
            l.append("css1")
        if css > 1:
            l.append("css2")
        return l

    def supports_tables(self):
        return self.supports("frames")

    def supports_iframes(self):
        return self.supports("iframes")

    def supports_frames(self):
        return self.supports("frames")

    def supports_java(self):
        return self.supports("javaapplets")

    def supports_javascript(self):
        return self.supports("javascript")

    def supports_vbscript(self):
        return self.supports("vbscript")

    def supports_activex(self):
        return self.supports("activexcontrols")

    def supports_cookies(self):
        return self.supports("cookies")

    def supports_wap(self):
        return self.supports("wap")

    def css_version(self):
        return self.get("css", 0)

    def version(self):
        major = self.get("majorver")
        minor = self.get("minorver")
        if major and minor:
            return (major, minor)
        elif major:
            return (major, None)
        elif minor:
            return (None, minor)
        else:
            ver = self.get("version")
            if ver and "." in ver:
                return tuple(ver.split(".", 1))
            elif ver:
                return (ver, None)
            else:
                return (None, None)

    def dom_version(self):
        return self.get("w3cdomversion", 0)


    def is_bot(self):
        return self.get("crawler") == True

    def is_mobile(self):
        return self.get("ismobiledevice") == True

    def name(self):
        return self.get("browser")

    def platform(self):
        return self.get("platform")

class BrowserCapabilities(object):

    def __new__(cls, *args, **kwargs):
        # Only create one instance of this clas
        if "instance" not in cls.__dict__:
            cls.instance = object.__new__(cls, *args, **kwargs)
        return cls.instance

    def __init__(self):
        self.cache = {}
        self.parse()

    def parse(self):
        key = "browser-capabilities-raw"
        raw = cache.get(key)
        # if the data isn't there, download it
        if raw is None:
            data = None
            log("Fetching from browser capabilities")
            try:
                data = urllib.urlopen("http://www.areciboapp.com/static/browscap.ini")
            except (IOError):
                pass
            if data: # and data.code == 200:
                # that should be one week (1 min > 1 hour > 1 day > 1 week)
                log("...succeeded")
                raw = data.read()
                cache.set(key, raw, 60 * 60 * 24 * 7)
            else:
                log("...failed")
                # try again in 1 hour if there was a problem
                cache.set(key, "", 60 * 60)
                raw = ""
        else:
            log("Using cached browser capabilities")

        string = StringIO(raw)
        cfg = ConfigParser()
        cfg.readfp(string)

        self.sections = []
        self.items = {}
        self.browsers = {}
        parents = set()
        for name in cfg.sections():
            qname = name
            for unsafe in list("^$()[].-"):
                qname = qname.replace(unsafe, "\%s" % unsafe)
            qname = qname.replace("?", ".").replace("*", ".*?")
            qname = "^%s$" % qname
            sec_re = re.compile(qname)
            sec = dict(regex=qname)
            sec.update(cfg.items(name))
            p = sec.get("parent")
            if p: parents.add(p)
            self.browsers[name] = sec
            if name not in parents:
                self.sections.append(sec_re)
            self.items[sec_re] = sec


    def query(self, useragent):
        useragent = useragent.replace(' \r\n', '')
        b = self.cache.get(useragent)
        if b: return b

        if not hasattr(self, "sections"):
            return None

        for sec_pat in self.sections:
            if sec_pat.match(useragent):
                browser = dict(agent=useragent)
                browser.update(self.items[sec_pat])
                parent = browser.get("parent")
                while parent:
                    items = self.browsers[parent]
                    for key, value in items.items():
                        if key not in browser.keys():
                            browser[key] = value
                        elif key == "browser" and value != "DefaultProperties":
                            browser["category"] = value # Wget, Godzilla -> Download Managers
                    parent = items.get("parent")
                if browser.get("browser") != "Default Browser":
                    b = Browser(browser)
                    self.cache[useragent] = b
                    return b
        self.cache[useragent] = None

    __call__ = query


def get():
    key = "browser-capabilities-parsed"
    parsed = cache.get(key)
    if parsed is None:
        parsed = BrowserCapabilities()
        # that should be one week (1 min > 1 hour > 1 day > 1 week)
        cache.set(key, parsed, 60 * 60 * 24 * 7)
    return parsed
########NEW FILE########
__FILENAME__ = feeds
from django.contrib.syndication.views import Feed
from django.core import serializers
from django.http import HttpResponse

from app.utils import has_private_key
from error.views import get_filtered, get_group_filtered

class base(Feed):
    title = "Arecibo Errors"
    link = "/list/"
    description = "Arecibo Errors"
    subtitle = "Arecibo Errors"

    def __init__(self, *args, **kw):
        Feed.__init__(self, *args, **kw)
        self.request = None

    def items(self):
        form, queryset = get_filtered(self.request)
        return queryset[:20]

    def item_title(self, item): return item.title
    def item_description(self, item): return item.description
    def item_pubdate(self, item): return item.timestamp

@has_private_key
def atom(request):
    feedgen = base()
    feedgen.request = request
    return feedgen(request)

@has_private_key
def json(request):
    form, queryset = get_filtered(request)
    response = HttpResponse(mimetype="text/javascript")
    json_serializer = serializers.get_serializer("json")()
    json_serializer.serialize(queryset[:20], ensure_ascii=False, stream=response)
    return response

class group(Feed):
    title = "Arecibo Errors by Groups"
    link = "/groups/"
    description = "Arecibo Errors by Groups"
    subtitle = "Arecibo Errors by Groups"

    def __init__(self, *args, **kw):
        Feed.__init__(self, *args, **kw)
        self.request = None

    def items(self):
        form, queryset = get_filtered(self.request)
        return queryset[:20]

    def item_title(self, item): return item.title
    def item_description(self, item): return item.description
    def item_pubdate(self, item): return item.timestamp

@has_private_key
def group_atom(request):
    feedgen = base()
    feedgen.request = request
    return feedgen(request)

@has_private_key
def group_json(request):
    form, queryset = get_group_filtered(request)
    response = HttpResponse(mimetype="text/javascript")
    json_serializer = serializers.get_serializer("json")()
    json_serializer.serialize(queryset[:20], ensure_ascii=False, stream=response)
    return response

########NEW FILE########
__FILENAME__ = forms
from datetime import datetime, timedelta
import operator

from django import forms
from django.db.models import Q

from app.forms import Form, ModelForm
from app.utils import memoize, safe_int

from projects.models import ProjectURL
from error.models import Error, Group

read_choices = (("", "All"), ("True", 'Read only'), ("False", 'Unread only'))
priority_choices = [ (r, r) for r in range(1, 11)]
priority_choices.insert(0, ("", "All"))

status_choices = ['500', '404', '100', '101', '102', '200', '201', '202', '203',
'204', '205', '206', '207', '226', '300', '301', '302', '303', '304',
'305', '307', '400', '401', '402', '403', '405', '406', '407',
'408', '409', '410', '411', '412', '413', '414', '415', '416', '417',
'422', '423', '424', '426', '501', '502', '503', '504', '505',
'507', '510']
status_choices = [ (r, r) for r in status_choices ]
status_choices.insert(0, ("", "All"))


class Filter(Form):
    """ Base for the filters """
    inequality = ""

    def as_query(self, object):
        args = []
        for k, v in self.cleaned_data.items():
            if not v:
                continue

            lookup = getattr(self, "handle_%s" % k, None)
            if lookup:
                args.append(lookup(v))
            else:
                args.append(Q(**{k:v}))

        if args:
            return object.objects.filter(reduce(operator.and_, args))
        return object.objects.all()

    def clean(self):
        data = {}
        for k, v in self.cleaned_data.items():
            if not v: continue
            data[k] = v

        return data


@memoize(prefix='get-project-urls', time=120)
def get_project_urls():
    urls = [('', '')]
    urls.extend([k.pk, k.url] for k in ProjectURL.objects.all())
    return urls


class GroupForm(Filter):
    project_url = forms.ChoiceField(choices=[],
                                    widget=forms.Select, required=False)

    def __init__(self, *args, **kw):
        super(GroupForm, self).__init__(*args, **kw)
        self.fields['project_url'].choices = get_project_urls()

    def as_query(self):
        return super(GroupForm, self).as_query(Group)

    def handle_project_url(self, value):
        return Q(project_url=value)


@memoize(prefix='get-domains', time=120)
def get_domains():
    errs = ProjectURL.objects.order_by('url').values_list('url', flat=True).distinct()
    domains = sorted([(d, d) for d in errs])
    domains.insert(0, ('', ''))
    return domains

period_choices = (['', ''],
                  ['last_24', 'Last 24 hours'],
                  ['today', 'Today'],
                  ['yesterday', 'Yesterday'])


class GroupEditForm(ModelForm):
    class Meta:
        model = Group
        fields = ['name', 'count', 'timestamp']


class ErrorForm(Filter):
    priority = forms.ChoiceField(choices=priority_choices,
                                 widget=forms.Select, required=False)
    status = forms.ChoiceField(choices=status_choices,
                               widget=forms.Select, required=False)
    read = forms.ChoiceField(choices=read_choices,
                             widget=forms.Select, required=False)
    start = forms.DateField(required=False, label="Start date",
        widget=forms.DateInput(attrs={"class":"date",}))
    period = forms.ChoiceField(choices=period_choices,
                               widget=forms.Select, required=False)
    end = forms.DateField(required=False, label="End date",
        widget=forms.DateInput(attrs={"class":"date",}))
    query = forms.CharField(required=False, label="Path")
    ip = forms.CharField(required=False, label="IP")
    domain = forms.ChoiceField(choices=[],
                               widget=forms.Select, required=False)
    uid = forms.CharField(required=False)
    group = forms.ModelChoiceField(queryset=Group.objects.none(),
                                   widget=forms.Select, required=False)

    def __init__(self, *args, **kw):
        super(ErrorForm, self).__init__(*args, **kw)
        self.fields['group'].queryset = Group.objects.all()
        self.fields['domain'].choices = get_domains()

    def clean(self):
        data = {}
        for k, v in self.cleaned_data.items():
            if not v: continue
            data[k] = v

        return data

    def handle_period(self, period):
        if period == 'last_24':
           return Q(timestamp__gte=datetime.now() - timedelta(hours=24))
        elif period == 'today':
           return Q(timestamp__gte=datetime.today().date())
        elif period == 'yesterday':
           return Q(timestamp__gte=datetime.today().date() - timedelta(days=1),
                    timestamp__lt=datetime.today())
        else:
           raise NotImplementedError

    def handle_read(self, value):
        return Q(read={"False":False, "True":True}.get(value, None))

    def handle_start(self, value):
        return Q(timestamp__gte=value)

    def handle_end(self, value):
        return Q(timestamp__lte=value)

    def handle_priority(self, value):
        return Q(priority__lte=value)

    def as_query(self):
        return super(ErrorForm, self).as_query(Error)

########NEW FILE########
__FILENAME__ = listeners
try:
    from hashlib import md5
except ImportError:
    from md5 import md5 

from django.db.models import F

from app.utils import safe_string, log
from error.models import Group, Error

from error.agent import get
from error import signals

def generate_key(instance):
    keys = ["type", "server", "msg", "status", "domain"]
    hsh = None

    for key in keys:
        value = safe_string(getattr(instance, key))
        if value:
            if not hsh:
                hsh = md5()
            hsh.update(value.encode("ascii", "ignore"))

    return hsh

def default_grouping(instance, **kw):
    """ Given an error, see if we can fingerprint it and find similar ones """
    log("Firing signal: default_grouping")

    hsh = generate_key(instance)
    if hsh:
        digest = hsh.hexdigest()
        try:
            created = False
            group = Group.objects.get(uid=digest)
            group.count = F('count')+getattr(instance, 'count', 1)
            group.save()
        except Group.DoesNotExist:
            created = True
            group = Group.objects.create(uid=digest, count=getattr(instance, 'count', 1))

        instance.group = group
        instance.save()

        if created:
            signals.group_assigned.send(sender=group.__class__, instance=group)
        signals.error_assigned.send(sender=instance.__class__, instance=instance)

signals.error_created.connect(default_grouping,
                              dispatch_uid="default_grouping")

def default_browser_parsing(instance, **kw):
    log("Firing signal: default_browser_parsing")
    if instance.user_agent:
        bc = get()
        if bc:
            b = bc(instance.user_agent)
            if b:
                instance.user_agent_short = b.name()
                instance.operating_system = b.platform()

    instance.user_agent_parsed = True
    instance.save()

signals.error_created.connect(default_browser_parsing,
                              dispatch_uid="default_browser_parsing")

########NEW FILE########
__FILENAME__ = models
from django.core.urlresolvers import reverse
from django.db import models

from datetime import datetime

from error.signals import error_created, group_created
from projects.models import ProjectURL

from app.utils import trunc_string
import os

class Group(models.Model):
    """ A grouping of errors """
    uid = models.CharField(max_length=255, db_index=True)
    timestamp = models.DateTimeField(db_index=True)
    project_url = models.ForeignKey(ProjectURL, null=True, db_index=True)
    count = models.IntegerField(default=0, db_index=True)
    name = models.CharField(max_length=255)

    def __unicode__(self):
        if self.name:
            return self.name
        elif self.project_url:
            return "%s: %s..." % (self.project_url, self.uid[:10])
        else:
            return unicode(self.uid)

    def sample(self):
        try:
            return Error.objects.filter(group=self).order_by("-timestamp")[0]
        except IndexError:
            return None

    def save(self, *args, **kw):
        created = not getattr(self, "id", None)
        self.timestamp = datetime.now()
        if created:
            group_created.send(sender=self.__class__, instance=self)
        super(Group, self).save(*args, **kw)

class Error(models.Model):
    # time error was received by this server
    timestamp = models.DateTimeField(db_index=True)
    timestamp_date = models.DateField(db_index=True)

    ip = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=255)
    user_agent_short = models.CharField(max_length=255)
    user_agent_parsed = models.BooleanField(default=False)
    operating_system = models.CharField(max_length=255)

    priority = models.IntegerField(default=0, db_index=True)
    status = models.CharField(max_length=255, db_index=True)

    raw = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, db_index=True)
    server = models.CharField(max_length=255, db_index=True)
    query = models.CharField(max_length=255)
    protocol = models.CharField(max_length=255)

    uid = models.CharField(max_length=255, db_index=True)
    type = models.CharField(max_length=255, db_index=True)
    msg = models.TextField()
    traceback = models.TextField()

    errors = models.TextField()

    # time error was recorded on the client server
    error_timestamp = models.DateTimeField()
    error_timestamp_date = models.DateTimeField(db_index=True)

    request = models.TextField()
    username = models.CharField(max_length=255, db_index=True)

    group = models.ForeignKey(Group, blank=True, null=True,
                              on_delete=models.SET_NULL)

    read = models.BooleanField(default=False, db_index=True)

    create_signal_sent = models.BooleanField(default=False)

    public = models.BooleanField(default=False, db_index=True)
    #count = models.IntegerField(default=1, db_index=True)

    class Meta:
        ordering = ['-timestamp', '-id']

    def get_absolute_url(self):
        return reverse("error-view", args=[self.id,])

    def has_group(self):
        return self.group

    def get_similar(self, limit=5):
        return (Error.objects.filter(group=self.group)
                             .exclude(pk=self.pk)[:limit])

    def delete(self):
        # TODO: improve this
        if self.group:
            self.group.count = self.group.count - 1
            if self.group.count < 1:
                self.group.delete()
        super(Error, self).delete()

    @property
    def title(self):
        """ Try to give a nice title to describe the error """
        strng = ""
        if self.type:
            strng = self.type
            if self.server:
                if self.status:
                    strng = "%s" % (strng)
                if not strng:
                    strng = "Error"
                strng = "%s on %s" % (strng, self.server)
        elif self.status:
            strng = self.status
            if self.server:
                strng = "%s on server %s" % (strng, self.server)
        elif self.raw:
            strng = self.raw
        else:
            strng = self.error_timestamp.isoformat()
        if self.uid:
            strng = "%s" % (strng)
        return strng

    @property
    def description(self):
        return self.msg or ""

    def save(self, *args, **kw):
        created = not getattr(self, "id", None)
        if created:
            self.error_timestamp = datetime.now()
            self.error_timestamp_date = self.error_timestamp.date()
            self.create_signal_sent = True
            super(Error, self).save(*args, **kw)
            error_created.send(sender=self.__class__, instance=self)
        else:
            super(Error, self).save(*args, **kw)

########NEW FILE########
__FILENAME__ = signals
import django.dispatch

error_created = django.dispatch.Signal(providing_args=["instance",])
group_created = django.dispatch.Signal(providing_args=["instance",])
group_assigned = django.dispatch.Signal(providing_args=["instance",])
error_assigned = django.dispatch.Signal(providing_args=["instance",])

########NEW FILE########
__FILENAME__ = tests
# -*- coding: UTF8 -*-
import os
from django.test import TestCase
from django.test.client import Client
from django.core.cache import cache
from django.core.urlresolvers import reverse

from app.tests import test_data as data
from app.utils import trunc_string
from error.models import Error, Group
from error.agent import get

class ErrorTests(TestCase):
    # test the view for writing errors

    def testBasic(self):
        assert not Error.objects.count()
        self.client.post(reverse("error-post"), data)
        assert Error.objects.count() == 1

    def testOverPriority(self):
        assert not Error.objects.count()
        ldata = data.copy()
        ldata["priority"] = 123
        self.client.post(reverse("error-post"), ldata)
        assert Error.objects.count() == 1

    def testStringPriority(self):
        assert not Error.objects.count()
        ldata = data.copy()
        ldata["priority"] = "test"
        self.client.post(reverse("error-post"), ldata)
        assert Error.objects.count() == 1

    def testNoPriority(self):
        assert not Error.objects.count()
        ldata = data.copy()
        del ldata["priority"]
        self.client.post(reverse("error-post"), ldata)
        assert Error.objects.count() == 1

    def testGroup(self):
        self.client.post(reverse("error-post"), data)
        assert Group.objects.count() == 1, "Got %s groups, not 1" % Group.objects.count()
        self.client.post(reverse("error-post"), data)
        assert Group.objects.count() == 1
        new_data = data.copy()
        new_data["status"] = 402
        self.client.post(reverse("error-post"), new_data)
        assert Group.objects.count() == 2

        # and test similar
        assert not Error.objects.order_by('pk')[2].get_similar()
        assert len(Error.objects.order_by('pk')[1].get_similar()) == 1
        assert len(Error.objects.order_by('pk')[0].get_similar()) == 1

    def testGroupDelete(self):
        self.client.post(reverse("error-post"), data)
        assert Group.objects.count() == 1, "Got %s groups, not 1" % Group.objects.count()
        assert Error.objects.count() == 1
        Error.objects.all()[0].delete()
        assert Group.objects.count() == 0

    def testBrowser(self):
        assert not Error.objects.count()
        ldata = data.copy()
        ldata["user_agent"] = "Mozilla/5.0 (X11; U; Linux i686; de; rv:1.8.0.5) Gecko/20060731 Ubuntu/dapper-security Firefox/1.5.0.5"
        self.client.post(reverse("error-post"), ldata)
        assert Error.objects.count() == 1
        assert Error.objects.all()[0].user_agent_short == "Firefox"
        assert Error.objects.all()[0].user_agent_parsed == True
        assert Error.objects.all()[0].operating_system == "Linux"

    # http://github.com/andymckay/arecibo/issues#issue/14
    def testUnicodeTraceback(self):
        assert not Error.objects.count()
        ldata = data.copy()
        ldata["traceback"] = "ɷo̚حٍ"
        self.client.post(reverse("error-post"), ldata)
        assert Error.objects.count() == 1

    def testCount(self):
        ldata = data.copy()
        ldata["count"] = 5
        self.client.post(reverse("error-post"), ldata)
        assert Group.objects.count() == 1
        assert Group.objects.all()[0].count == 5

    def testCountUpdate(self):
        ldata = data.copy()
        self.client.post(reverse("error-post"), ldata)
        assert Group.objects.all()[0].count == 1

        ldata["count"] = 5
        self.client.post(reverse("error-post"), ldata)
        assert Group.objects.all()[0].count == 6

    def testGroupTimestampUpdates(self):
        self.client.post(reverse("error-post"), data)
        group = Group.objects.all()[0]
        old = group.timestamp
        self.client.post(reverse("error-post"), data)
        group = Group.objects.all()[0]
        assert group.timestamp != old


class TagsTests(TestCase):
    def testTrunc(self):
        assert trunc_string("Test123", 5) == "Te..."
        assert trunc_string(None, 5) == ""

class AgentTests(TestCase):
    def setUp(self):
        path = os.path.join(os.path.dirname(__file__), 'fixtures/browscap.ini')
        raw = open(path).read()
        key = "browser-capabilities-raw"
        cache.set(key, raw)

    def testAgent(self):
        bc = get()
        for agent in [
            "Mozilla/5.0 (compatible; Konqueror/3.5; Linux; X11; de) KHTML/3.5.2 (like Gecko) Kubuntu 6.06 Dapper",
            "Mozilla/5.0 (X11; U; Linux i686; de; rv:1.8.0.5) Gecko/20060731 Ubuntu/dapper-security Firefox/1.5.0.5",
            "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.7.12) Gecko/20060216 Debian/1.7.12-1.1ubuntu2",
            "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.0.5) Gecko/20060731 Ubuntu/dapper-security Epiphany/2.14 Firefox/1.5.0.5",
            "Opera/9.00 (X11; Linux i686; U; en)",
            "Wget/1.10.2",
            "Mozilla/5.0 (X11; U; Linux i386) Gecko/20063102 Galeon/1.3test",
            "Mozilla/5.0 (Macintosh; U; PPC Mac OS X 10_5_4; en-us) AppleWebKit/525.18 (KHTML, like Gecko) Version/3.1.2 Safari/525.20.1",
            "Mozilla/4.0 (compatible; MSIE 6.0; Windows 98)" # Tested under Wine
            """Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.5; en-US;  \r
    rv:1.9.0.5) Gecko/2008120121 Firefox/3.0.5,gzip(gfe)""",
            "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.5; en-US; rv:1.9.0.5) Gecko/2008120121 Firefox/3.0.5,gzip(gfe)",
            "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_5_6; en-us) AppleWebKit/525.27.1 (KHTML, like Gecko) Version/3.2.1 Safari/525.27.1,gzip(gfe)"
          ]:
            b = bc(agent)
            assert b.name()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# if you put the key in here it will get exposed in errors
# so probably
urlpatterns = patterns('',
    url(r'^feed/.*?/json/$', 'error.feeds.json', name="json"),
    url(r'^feed/.*?/$', 'error.feeds.atom', name="rss"),
    url(r'^group/feed/.*?/json/$', 'error.feeds.group_json', name="json"),
    url(r'^group/feed/.*?/$', 'error.feeds.group_atom', name="rss"),
    url(r'^list/$', 'error.views.errors_list', name="error-list"),
    url(r'^list/snippet/$', 'error.views.errors_snippet', name="error-snippet"),
    url(r'^groups/$', 'error.views.groups_list', name="group-list"),
    url(r'^group/(?P<pk>[\w-]+)$', 'error.views.group_edit', name="group-edit"),
    url(r'^view/(?P<pk>[\w-]+)/$', 'error.views.error_view', name="error-view"),
    url(r'^view/toggle/(?P<pk>[\w-]+)/$','error.views.error_public_toggle', name="error-toggle")
)

########NEW FILE########
__FILENAME__ = validations
from app.errors import StatusDoesNotExist

codes = ['100', '101', '102', '200', '201', '202', '203', '204', '205', '206',
    '207', '226', '300', '301', '302', '303', '304', '305', '307', '400', '401',
    '402', '403', '404', '405', '406', '407', '408', '409', '410', '411', '412',
    '413', '414', '415', '416', '417', '422', '423', '424', '426', '500', '501',
    '502', '503', '504', '505', '507', '510']

def valid_status(code):
    if isinstance(code, str):
        code = str(code)
    if code not in codes:
        raise StatusDoesNotExist, 'The status "%s" does not exist.' % code

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.views.generic.simple import direct_to_template
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.template import RequestContext, loader

from error.models import Error, Group
from error.forms import ErrorForm, GroupForm, GroupEditForm
from error.signals import error_created

from app.decorators import arecibo_login_required
from app.utils import render_plain, render_json, not_allowed
from app.paginator import Paginator, get_page


def get_group_filtered(request):
    form = GroupForm(request.GET or None)
    if form.is_valid():
        queryset = form.as_query()
    else:
        queryset = Group.objects.all()
        queryset.order_by("-timestamp")

    return form, queryset


def get_filtered(request):
    form = ErrorForm(request.GET or None)
    if form.is_valid():
        queryset = form.as_query()
    else:
        queryset = Error.objects.all()
        queryset.order_by("-timestamp")

    return form, queryset


@arecibo_login_required
def errors_list(request):
    form, queryset = get_filtered(request)
    paginated = Paginator(queryset, 50)
    page = get_page(request, paginated)
    if request.GET.get("lucky") and len(page.object_list):
        return HttpResponseRedirect(reverse("error-view", args=[page.object_list[0].id,]))
    return direct_to_template(request, "list.html", extra_context={
        "page": page,
        "nav": {"selected": "list", "subnav": "list"},
        "form": form,
        "refresh": True
        })


@arecibo_login_required
@render_json
def errors_snippet(request, pk=None):
    form, queryset = get_filtered(request)
    paginated = Paginator(queryset, 50)
    page = get_page(request, paginated)
    template = loader.get_template('list-snippet.html')
    html = template.render(RequestContext(request, {"object_list": page.object_list, }))
    return {"html":html, "count": len(page.object_list) }


@arecibo_login_required
def groups_list(request):
    form, queryset = get_group_filtered(request)
    paginated = Paginator(queryset, 50)
    page = get_page(request, paginated)
    return direct_to_template(request, "group.html", extra_context={
        "page": page,
        "form": form,
        "nav": {"selected": "list", "subnav": "group"},
        })


@arecibo_login_required
def error_public_toggle(request, pk):
#    error = Error.objects.get(pk=pk)
#    if request.method.lower() == "post":
#        if error.public:
#            error.public = False
#        else:
#            error.public = True
#        error.save()
    return HttpResponseRedirect(reverse("error-view", args=[error.id,]))


@arecibo_login_required
def error_view(request, pk):
    error = Error.objects.get(pk=pk)

    if not error.read:
        error.read = True
        error.save()

    return direct_to_template(request, "view.html", extra_context={
        "error":error,
        "nav": {"selected": "list"},
        })
    

@user_passes_test(lambda u: u.is_staff)
def group_edit(request, pk):
    group = Group.objects.get(pk=pk)
    form = GroupEditForm(request.POST or None, instance=group)
    if request.POST:
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse("group-list"))

    return direct_to_template(request, "group-edit.html", extra_context={
        "form": form,
        "nav": {"selected": "list"},
        })

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from notifications.models import Notification


class NotificationAdmin(admin.ModelAdmin):
    pass


admin.site.register(Notification, NotificationAdmin)

########NEW FILE########
__FILENAME__ = email
error_msg = """Arecibo is notifying you of the following errors:
--------------------

%s
--------------------
You are receiving this because it's the email address set for your account at %s.

Please remember I'm just a bot and don't really exist, so replying to this email will
not do you any good I'm afraid.
"""

from django.core.mail import send_mail
from django.conf import settings
from app.utils import log

def as_text(issue):
    pass

def as_text(error):
    details = ["    Error: %s%s" % (settings.SITE_URL, error.get_absolute_url()), ]
    if error.raw:
        details.append("    URL: %s" % error.raw)
    details.append("    Error: %s, %s" % (error.type, error.msg))
    for key in ("timestamp", "status", "server"):
        value = getattr(error, key)
        if value:
            details.append("    %s: %s" % (key.capitalize(), value))
    details.append("")
    details = "\n".join(details)
    return details

def send_error_email(holder):
    alot = 10
    data = "\n".join([ as_text(obj) for obj in holder.objs[:alot]])
    count = len(holder.objs)
    if count > 1:
        subject = "Reporting %s errors" % count
    else:
        subject = "Reporting an error"
    if count > alot:
        data += "\n...truncated. For more see the website.\n"
    log("Sending email to: %s of %s error(s)" % (holder.user.email, count))
    send_mail(subject,
              error_msg % (data, settings.SITE_URL),
              settings.DEFAULT_FROM_EMAIL,
              [holder.user.email],
              fail_silently=False)

########NEW FILE########
__FILENAME__ = listeners
from app.utils import log
from notifications.models import Notification
from users.utils import approved_users

from error.signals import error_created

def default_notification(instance, **kw):
    """ Given an error see if we need to send a notification """
    log("Firing signal: default_notification")

    if instance.priority >= 5:
        return

    users = approved_users()
    if not users.count():
        return
    
    notification = Notification()
    notification.notifier = instance
    notification.save()
    for user in users:
        notification.user.add(user)
    

error_created.connect(default_notification, dispatch_uid="default_notification")
########NEW FILE########
__FILENAME__ = cleanup_notifications
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand

from notifications.models import Notification
from app.utils import log, render_plain

class Command(BaseCommand):
    def handle(self, *args, **options):
        notifications_cleanup()

def notifications_cleanup(days=0):
    log("Firing cron: notifications_cleanup")
    expired = datetime.today() - timedelta(days=days)
    queryset = Notification.objects.filter(tried=True, timestamp__lt=expired)
    for notification in queryset:
        notification.delete()

    return render_plain("Cron job completed")


########NEW FILE########
__FILENAME__ = send_notifications
import sys

from django.core.management.base import BaseCommand

from notifications.email import send_error_email
from notifications.models import Notification
from app.utils import log, render_plain


class Holder:
    def __init__(self):
        self.user = None
        self.objs = []
        self.notifs = []


class Command(BaseCommand):
    def handle(self, *args, **options):
        notifications_send()


def notifications_send():
    log("Firing cron: notifications_send")
    notifications = Notification.objects.filter(tried=False)

    # batch up the notifications for the user
    holders = {}
    for notif in notifications:
        for user in notif.user.all():
            key = user.pk
            if key not in holders:
                holder = Holder()
                holder.user = user
                holders[key] = holder

            holders[key].objs.append(notif.notifier)
            holders[key].notifs.append(notif)

    for user_id, holder in holders.items():
        try:
            send_error_email(holder)
            for notification in holder.notifs:
                notification.tried = True
                notification.completed = True
                notification.save()
        except:
            info = sys.exc_info()
            data = "%s, %s" % (info[0], info[1])
            for notification in holder.notifs:
                notification.tried = True
                notification.completed = True
                notification.error_msg = data
                notification.save()

    return render_plain("Cron job completed")

########NEW FILE########
__FILENAME__ = models
from django.contrib.auth.models import User
from django.db import models
from django.utils.timesince import timesince

from error.models import Error
from notifications.signals import notification_created


class Notification(models.Model):
    user = models.ManyToManyField(User)

    tried = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    error_msg = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    notifier = models.ForeignKey(Error, blank=True, null=True)

    def save(self, *args, **kw):
        created = not getattr(self, "id", None)
        super(Notification, self).save(*args, **kw)
        if created:
            notification_created.send(sender=self.__class__, instance=self)

    def __unicode__(self):
        rest = ''
        if self.tried:
            rest += '[tried]'
        if self.completed:
            rest += '[completed]'
        since = timesince(self.timestamp)
        return u'[%s] %s %s' % (since, self.error_msg[50:], rest)

########NEW FILE########
__FILENAME__ = signals
import django.dispatch

notification_created = django.dispatch.Signal(providing_args=["instance",])
########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.test.client import Client

from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from error.models import Error
from notifications.models import Notification

from app.tests import test_data
from django.core import mail

class ErrorTests(TestCase):
    # test the view for writing errors
    def testBasic(self):
        c = Client()
        assert not Error.objects.all().count()
        c.post(reverse("error-post"), test_data)
        assert test_data["priority"] < 5, test_data["priority"]
        assert Error.objects.all().count() == 1, Error.objects.all().count()

        c.post(reverse("error-post"), test_data)
        assert test_data["priority"] < 5, test_data["priority"]
        assert Error.objects.all().count() == 2

    def testNoNotification(self):
        c = Client()
        assert not Error.objects.all().count()
        data = test_data.copy()
        data["priority"] = 6
        c.post(reverse("error-post"), data)
        assert data["priority"] > 5, data["priority"]
        assert Error.objects.all().count() == 1
        assert Notification.objects.all().count() == 0

    def testNotificationNoUsers(self):
        c = Client()
        c.post(reverse("error-post"), test_data)
        assert Notification.objects.all().count() == 0

    def testCron(self):
        User(email="test@foo.com",
             username="test",
             is_staff=True).save()
        self.testBasic()
        # now test our sending actually works
        c = Client()
        res = c.get(reverse("notification-send"))
        self.assertEquals(len(mail.outbox), 1)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^list/$', 'notifications.views.notifications_list', name="notification-list"),
)

########NEW FILE########
__FILENAME__ = views
import sys
from datetime import datetime, timedelta

from django.contrib.auth.decorators import user_passes_test
from django.views.generic.simple import direct_to_template

from notifications.models import Notification
from notifications.email import send_error_email

from app.decorators import arecibo_login_required
from app.paginator import Paginator, get_page
from app.utils import log, render_plain


@arecibo_login_required
def notifications_list(request):
    queryset = Notification.objects.all().order_by("-timestamp")
    paginated = Paginator(queryset, 10)
    page = get_page(request, paginated)
    return direct_to_template(request, "notification_list.html", extra_context={
        "page": page,
        "nav": {"selected": "notifications"}
        })

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from projects.models import Project, ProjectURL


class ProjectAdmin(admin.ModelAdmin):
    pass


class ProjectURLAdmin(admin.ModelAdmin):
    pass


admin.site.register(Project, ProjectAdmin)
admin.site.register(ProjectURL, ProjectURLAdmin)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from app.forms import ModelForm

from projects.models import Project, ProjectURL, stage_choices


class ProjectForm(ModelForm):
    name = forms.CharField(required=True, label="Name")
    description = forms.CharField(required=False, label="Description",
                                  widget=forms.Textarea)

    class Meta:
        model = Project


class ProjectURLForm(ModelForm):
    url = forms.CharField(required=True, label="Domain")
    stage = forms.CharField(required=True, label="Project stage",
                            widget=forms.Select(choices=stage_choices))

    class Meta:
        model = ProjectURL
        fields = ("url", "stage")
########NEW FILE########
__FILENAME__ = listeners
from app.utils import log

from projects.models import Project
from error import signals


def lookup_domain(domain):
    # given a domain, find the project
    projects = Project.objects.all()
    for project in projects:
        for url in project.projecturl_set.all():
            if domain == url.url:
                return url


def default_project(instance, **kw):
    log("Firing signal: default_project")
    if instance.project_url:
        return

    error = instance.sample()
    if error:
        domain = lookup_domain(error.domain)
        if domain:
            instance.project_url = domain
            instance.save()


signals.group_assigned.connect(default_project,
                               dispatch_uid="default_browser_parsing")
########NEW FILE########
__FILENAME__ = models
from datetime import datetime

from django.db import models

from django.utils.translation import ugettext as _

stage_choices = (
    ["dev", _("Development")],
    ["testing", _("Testing")],
    ["staging", _("Staging")],
    ["backup", _("Backups")],
    ["production", _("Production")],
    ["other", _("Other")]
)

class Project(models.Model):
    name = models.CharField(blank=False, max_length=255)
    description = models.CharField(blank=False, max_length=255)

    def __unicode__(self):
        return self.name

class ProjectURL(models.Model):
    project = models.ForeignKey(Project)
    url = models.CharField(blank=False, max_length=255)
    stage = models.CharField(choices=stage_choices, blank=False, max_length=255)

    def get_stage_display(self):
        return dict(stage_choices).get(self.stage)

    def __unicode__(self):
        return self.url

########NEW FILE########
__FILENAME__ = signals

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.test.client import Client

from django.core.urlresolvers import reverse

from error.models import Error, Group
from projects.models import Project, ProjectURL

from app.tests import test_data


class ProjectTests(TestCase):
    fixtures = ['users.json']

    def _addError(self):
        c = Client()
        assert not Error.objects.all().count()
        c.post(reverse("error-post"), test_data)
        assert test_data["priority"] < 5, test_data["priority"]
        assert Error.objects.all().count() == 1

    def testEditProject(self):
        project = Project(name="test")
        project.save()

        self.client.login(username='admin', password='password')
        r = self.client.get(reverse("projects-edit", args=[project.pk]))
        self.assertEquals(200, r.status_code)

    def testAddProject(self):
        project = Project(name="test")
        project.save()

        project_url = ProjectURL()
        project_url.url = "badapp.org"
        project_url.stage = "dev"
        project_url.project = project
        project_url.save()

        self._addError()

        assert Group.objects.count() == 1
        assert Group.objects.all()[0].project_url == project_url

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^$', 'projects.views.project_list', name="projects-list"),

    url(r'^add/url/(?P<pk>[\w-]+)/$', 'projects.views.project_url_add', name="projects-url-add"),
    url(r'^edit/url/(?P<pk>[\w-]+)/(?P<url>[\w-]+)/$', 'projects.views.project_url_edit', name="projects-url-edit"),

    url(r'^add/$', 'projects.views.project_add', name="projects-add"),
    url(r'^edit/(?P<pk>[\w-]+)/$', 'projects.views.project_edit', name="projects-edit"),

)

########NEW FILE########
__FILENAME__ = utils

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.decorators import user_passes_test
from django.views.generic.simple import direct_to_template
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.template import RequestContext, loader
from django.shortcuts import get_object_or_404

from app.decorators import arecibo_login_required

from projects.models import Project, ProjectURL
from projects.forms import ProjectForm, ProjectURLForm


@arecibo_login_required
def project_list(request):
    projects = Project.objects.all().order_by("-name")
    return direct_to_template(request, "project_list.html", extra_context={
        "page": projects,
        "nav": {"selected": "projects", "subnav": "list"},
    })


@user_passes_test(lambda u: u.is_staff)
def project_add(request):
    form = ProjectForm(request.POST or None)
    if form.is_valid():
        form.save()
        return HttpResponseRedirect(reverse("projects-list"))
    return direct_to_template(request, "project_add.html", extra_context={
        "form": form,
        "nav": {"selected": "projects",},
    })


@user_passes_test(lambda u: u.is_staff)
def project_edit(request, pk):
    form = ProjectForm(request.POST or None,
                       instance=Project.objects.get(pk=pk))
    if form.is_valid():
        form.save()
        return HttpResponseRedirect(reverse("projects-list"))
    return direct_to_template(request, "project_edit.html", extra_context={
        "form": form,
        "nav": {"selected": "projects",},
    })


@user_passes_test(lambda u: u.is_staff)
def project_url_add(request, pk):
    project = get_object_or_404(Project, pk=pk)
    form = ProjectURLForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.project = project
        obj.save()
        return HttpResponseRedirect(reverse("projects-list"))
    return direct_to_template(request, "project_url_add.html", extra_context={
        "form": form,
        "project": project,
        "nav": {"selected": "projects",},
    })


@user_passes_test(lambda u: u.is_staff)
def project_url_edit(request, pk, url):
    url = get_object_or_404(ProjectURL, pk=url)
    project = project = get_object_or_404(Project, pk=pk)
    form = ProjectURLForm(request.POST or None, instance=url)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.project = project
        obj.save()
        return HttpResponseRedirect(reverse("projects-list"))
    return direct_to_template(request, "project_url_edit.html", extra_context={
        "form": form,
        "project": project,
        "nav": {"selected": "projects",},
    })

########NEW FILE########
__FILENAME__ = http
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from app.utils import render_plain
from error.models import Error
from receiving.post import populate


@csrf_exempt
def post(request):
    """ Add in a post """
    data = request.POST.copy()
    if "ip" not in data:
        data["ip"] = request.META.get("REMOTE_ADDR", "")
    if "user_agent" not in data:
        data["user_agent"] = request.META.get("HTTP_USER_AGENT", "")
    populate.delay(data)
    return render_plain("Error recorded")

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = post
from datetime import datetime
from urlparse import urlparse, urlunparse

from django.conf import settings

from app.utils import break_url
from app.errors import StatusDoesNotExist
from error.models import Error
from error.validations import valid_status
from email.Utils import parsedate

from celery.task import task

@task(rate_limit='10/s')
def populate(incoming):
    """ Populate the error table with the incoming error """
    # special lookup the account
    err = Error()
    uid = incoming.get("account", "")
    if not settings.ANONYMOUS_POSTING:
        if not uid:
            raise ValueError, "Missing the required account number."

        if str(uid) != settings.ARECIBO_PUBLIC_ACCOUNT_NUMBER:
            raise ValueError, "Account number does not match"

    # special
    if incoming.has_key("url"):
        for k, v in break_url(incoming["url"]).items():
            setattr(err, k, v)

    # check the status codes
    if incoming.has_key("status"):
        status = str(incoming["status"])
        try:
            valid_status(status)
            err.status = status
        except StatusDoesNotExist:
            err.errors += "Status does not exist, ignored.\n"

    # not utf-8 encoded
    for src, dest in [
        ("ip", "ip"),
        ("user_agent", "user_agent"),
        ("uid", "uid"),
        ]:
        actual = incoming.get(src, None)
        if actual is not None:
            setattr(err, dest, str(actual))

    try:
        priority = int(incoming.get("priority", 0))
    except ValueError:
        priority = 0
    err.priority = min(priority, 10)

    # possibly utf-8 encoding
    for src, dest in [
        ("type", "type"),
        ("msg", "msg"),
        ("server", "server"),
        ("traceback", "traceback"),
        ("request", "request"),
        ("username", "username")
        ]:
        actual = incoming.get(src, None)
        if actual is not None:
            try:
                setattr(err, dest, actual.encode("utf-8"))
            except UnicodeDecodeError:
                err.errors += "Encoding error on the %s field, ignored.\n" % src

    # timestamp handling
    if "timestamp" in incoming:
        tmstmp = incoming["timestamp"].strip()
        if tmstmp.endswith("GMT"):
            tmstmp = tmstmp[:-3] + "-0000"
        tme = parsedate(tmstmp)
        if tme:
            try:
                final = datetime(*tme[:7])
                err.error_timestamp = final
                err.error_timestamp_date = final.date()
            except ValueError, msg:
                err.errors += 'Date error on the field "%s", ignored.\n' % msg

    err.timestamp = datetime.now()
    err.timestamp_date = datetime.now().date()
    if "count" in incoming:
        err.count = incoming["count"]
    err.save()

########NEW FILE########
__FILENAME__ = tests
from receiving import post
from django.conf import settings
from django.test import TestCase
from error.models import Error

class PostTest(TestCase):

    def test_post_key(self):
        settings.ANONYMOUS_POSTING = False
        acc = settings.ARECIBO_PUBLIC_ACCOUNT_NUMBER
        post.populate({'account': acc})
        assert(Error.objects.count() == 1)
        self.assertRaises(ValueError, post.populate, {'account': acc + "a"})

    def test_post_no_key(self):
        settings.ANONYMOUS_POSTING = True
        acc = settings.ARECIBO_PUBLIC_ACCOUNT_NUMBER
        post.populate({'account': acc})
        assert(Error.objects.count() == 1)
        post.populate({})
        assert(Error.objects.count() == 2)
        settings.ANONYMOUS_POSTING = False

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^v/1/$', 'receiving.http.post', name="error-post"),
)

########NEW FILE########
__FILENAME__ = settings
import os
import sys

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ROOT_PATH = os.path.abspath(os.path.dirname(__file__))

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '/Users/andy/tempy/db.sql',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

TIME_ZONE = 'UTC'

LANGUAGE_CODE = 'en-us'

SITE_ID = 1

USE_I18N = False
MEDIA_ROOT = ''
MEDIA_URL = ''


# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'userstorage.middleware.UserStorage',
    'app.middleware.Middleware'
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'app.context.context',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    os.path.join(ROOT_PATH, 'templates'),
    os.path.join(ROOT_PATH, 'custom', 'templates')
)

SETTINGS_MODULE = 'settings'
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.admin',
    'error',
    'app',
    'notifications',
    'receiving',
    'users',
    'projects',
    'djcelery',
    'stats',
    'custom'
)

LOGIN_URL = '/login/'
LOGOUT_URL = '/logout/'
LOGIN_REDIRECT_URL = '/list/'

TEST_RUNNER = "app.test_runner.AreciboRunner"
ARECIBO_PUBLIC_ACCOUNT_NUMBER = "your_public_account_number_here"
ARECIBO_PRIVATE_ACCOUNT_NUMBER = "your_private_account_number_here"

DEFAULT_FROM_EMAIL = "you.account@gmail.com.that.is.authorized.for.app_engine"
SITE_URL = "http://theurl.to.your.arecibo.instance.com"

ANONYMOUS_ACCESS = False
ANONYMOUS_POSTING = False

CELERY_RESULT_BACKEND = "amqp"

CELERY_IMPORTS = ("custom", "users", "notifications", "receiving.post", )

BROKER_HOST = "localhost"
BROKER_PORT = 5672
BROKER_USER = "guest"
BROKER_PASSWORD = "guest"
BROKER_VHOST = ""

try:
    from local_settings import *
except ImportError:
    pass

# Add in required lib.
lib = os.path.abspath(os.path.join(ROOT_PATH, '..', 'lib'))

assert os.path.exists(lib), 'Cannot find required lib directory at: %s' % lib
if lib not in sys.path:
    sys.path.append(lib)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = signals
import django.dispatch

stats_completed = django.dispatch.Signal(providing_args=["instance",])

########NEW FILE########
__FILENAME__ = tests
import os
from datetime import datetime, timedelta

from django.test import TestCase
from django.test.client import Client

from django.contrib.auth.models import User
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import connection

from app import tests
from error.models import Error

def create_error():
    return Error(timestamp=datetime.now(),
                 timestamp_date=datetime.today())


class StatsTests(TestCase):
    # test the view for writing errors
    def setUp(self):
        settings.ANONYMOUS_ACCESS = True
        Error.objects.all().delete()
    
    def testCount(self):
        for x in range(0, 10):
            create_error().save()
    
        for x in range(0, 5):
            err = create_error()
            err.priority = 4
            err.save()

        url = reverse('stats-view', args=['priority'])
        res = self.client.get(url)
        assert 'data.setValue(0, 1, 10);' in res.content
        assert 'data.setValue(0, 2, 5);' in res.content
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^$', 'stats.views.stats_view', name="stats-view"),
    url(r'^view/(?P<key>[\w-]+)/$', 'stats.views.stats_view', name="stats-view"),
)

########NEW FILE########
__FILENAME__ = views
from datetime import datetime, timedelta

from django.contrib.auth.decorators import user_passes_test
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.http import HttpResponse
from django.views.generic.simple import direct_to_template

from app.decorators import arecibo_login_required
from app.utils import render_plain, safe_int
from app.paginator import Paginator, get_page

from error.models import Error

stats = {
    "priority": {
        "title": "By Priority",
        "column": "priority",
        "count": "priority__count",
        "query": (Error.objects.values('priority', 'timestamp_date')
                       .order_by('timestamp_date')
                       .annotate(Count('priority'))),
    },
    "type": {
        "title": "By Type",
        "column": "type",
        "count": "type__count",
        "query": (Error.objects.values('type', 'timestamp_date')
                       .order_by('timestamp_date')
                       .annotate(Count('type'))),
    },
#    "group": {
#        "title": "By Group",
#        "column": "group__name",
#        "count": "group__count", 
#        "query": (Error.objects.values('group', 'group__name', 'timestamp_date')
#                  .order_by('timestamp_date').annotate(Count('group'))),
#    }
}


def format_results(stat, query):
    data = {"columns":[], "rows":{}}
    for line in query:
        column = line[stat['column']]
        if column == '':
            column = '(empty)'
        if column not in data['columns']:
            data['columns'].append(column)
        data['rows'].setdefault(line['timestamp_date'], [])
        data['rows'][line['timestamp_date']].append({
            'num': data['columns'].index(column) + 1,
            'count': line[stat['count']],
        })
    # sigh Python 2.4 compat.
    data['rows'] = [(k, data['rows'][k]) for k in sorted(data['rows'].iterkeys())]
    return data

@arecibo_login_required
def stats_view(request, key="type"):
    data = {
        "stats": zip(stats.keys(), stats.values()),
        "nav": {"selected": "stats"} 
    }
    if key:
        stat = stats[key]
        end = datetime.today()
        start = end - timedelta(days=30)
        query = stat["query"].filter(timestamp_date__gte=start,
                                 timestamp_date__lte=end)
        data.update({
            "stat": stat,
            "start": start,
            "end": end,
            "result": format_results(stat, query),
            "query": query,
        })
    return direct_to_template(request, "stats_view.html", data)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.contrib import admin
admin.autodiscover()

import os
from django.conf import settings

urlpatterns = patterns('',
    (r'', include('error.urls')),
    (r'', include('receiving.urls')),
    (r'', include('app.urls')),
    (r'', include('users.urls')),
    (r'^stats/', include('stats.urls')),
    (r'^projects/', include('projects.urls')),
    (r'^notification/', include('notifications.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^media/(?P<path>.*)', 'django.views.static.serve',
     {'document_root' : os.path.join(settings.ROOT_PATH, '..', 'media')})
)

#handler404 = 'app.errors.not_found_error'
#handler500 = 'app.errors.application_error'

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import (AuthenticationForm, UserCreationForm,
                                       SetPasswordForm)
from django.utils.translation import ugettext as _

from app.forms import Form, ModelForm


class LoginForm(Form, AuthenticationForm):
    pass


class CreateForm(ModelForm, UserCreationForm):
    username = forms.RegexField(max_length=30, regex=r'^[\w.@+-]+$',
                                error_messages={'invalid': _("This value may contain only letters, numbers and @/./+/-/_ characters.")})

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "password1",
                  "password2", "email")
        
        
class EditForm(ModelForm):
    username = forms.CharField(max_length=30)
    is_staff = forms.BooleanField(required=False, label=_("Access to Arecibo"))
    
    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "is_staff")
        

class PasswordForm(Form, SetPasswordForm):
    pass
########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^users/$', 'users.views.user_list', name="user-list"),
    url(r'^users/edit/(?P<pk>[\w-]+)/$', 'users.views.user_edit', name="user-edit"),
    url(r'^users/create/$', 'users.views.user_create', name="user-create"),
    url(r'^users/password/$', 'users.views.user_password', name="user-password"),
    
    url(r'^login/$', 'users.views.login', name="login"),
    url(r'^logout/$', 'users.views.logout', name="logout"),
)

########NEW FILE########
__FILENAME__ = utils
from django.contrib.auth.models import User

def approved_users():
    return User.objects.filter(is_staff=True)

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth import logout as logout_user
from django.contrib.auth.views import login as login_view
from django.contrib.messages.api import info
from django.views.generic.simple import direct_to_template
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from app.paginator import Paginator, get_page
from app.utils import redirect

from users.forms import CreateForm, EditForm, LoginForm, PasswordForm


@user_passes_test(lambda u: u.is_staff)
def user_list(request):
    queryset = User.objects.all()
    # this number doesn't need to be high and its quite an expensive
    # page to generate
    paginated = Paginator(queryset, 10)
    page = get_page(request, paginated)
    return direct_to_template(request, "user_list.html", extra_context={
        "page": page,
        "nav": {"selected": "setup"}
        })

@user_passes_test(lambda u: u.is_staff)
def user_edit(request, pk):
    form = EditForm(request.POST or None, instance=User.objects.get(pk=pk))
    if form.is_valid():
        form.save()
        info(request, 'User details changed.')
        return HttpResponseRedirect(reverse("user-list"))
    return direct_to_template(request, "user_edit.html", extra_context={
        "form": form,
        "nav": {"selected": "users",},
    })


def user_create(request):
    form = CreateForm(request.POST or None)
    if form.is_valid():
        form.save()
        info(request, _('Account added, please wait for an admin to verify.'))
        return HttpResponseRedirect(reverse("index"))
    return direct_to_template(request, "user_create.html", extra_context={
        "form": form,
    })
 

@user_passes_test(lambda u: u.is_staff)
def user_password(request):
    form = PasswordForm(request.user, request.POST or None)
    if form.is_valid():
        form.save()
        info(request, 'Password changed.')
        return HttpResponseRedirect(reverse("user-edit",
                                            args=[request.user.pk]))
    return direct_to_template(request, "user_password.html", extra_context={
        "form": form,
    })
    
    
def logout(request):
    logout_user(request)
    return redirect('index')


def login(request):
    return login_view(request, 'user_login.html', authentication_form=LoginForm)
########NEW FILE########
