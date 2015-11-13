__FILENAME__ = test
import contextlib

from tornado import ioloop

from tornadomail import send_mail
from tornadomail.backends.smtp import EmailBackend

from tornado import stack_context


def callback(*args, **kwargs):
    ioloop.IOLoop.instance().stop()
    print 'Successfully sended'


def error_handler(e, msg, traceback):
    print 'Error:'
    print msg
    ioloop.IOLoop.instance().stop()
    return True


with stack_context.ExceptionStackContext(error_handler):
    send_mail(
        'subject', 'message', 'robo@djangostars.com',
        ['anton.agafonov@gmail.com'], callback=callback,
        connection=EmailBackend(
            'smtp.gmail.com', 587, 'robo@djangostars.com', 'fakeuser2',
            True
         )
    )

ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = testproject
#!/usr/bin/env python
import logging

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado import gen

from tornado.options import define, options

from tornadomail.message import EmailMessage
from tornadomail.backends.smtp import EmailBackend

define("port", default=8888, help="run on the given port", type=int)


logging.basicConfig(level=logging.DEBUG) 

class Application(tornado.web.Application):
    @property
    def mail_connection(self):
        return EmailBackend(
            'smtp.gmail.com', 587, '<your google email>', '<your google password>',
            True
        )

class MainHandler(tornado.web.RequestHandler):

    @property
    def mail_connection(self):
        return self.application.mail_connection

    def get(self):
        self.render("index.html")

    def post(self):

        def _finish(num):
            print 'sended %d message(s)' % num
            self.render("index.html")

        message = EmailMessage(
            self.get_argument('subject'),
            self.get_argument('message'),
            '<your google email>',
            [self.get_argument('email')],
            connection=self.mail_connection
        )
        message.send()#callback=_finish)
        self.render("index.html")


def main():
    tornado.options.parse_command_line()
    application = Application([
        (r"/", MainHandler),
    ])
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = base
"""Base email backend class."""

class BaseEmailBackend(object):
    """
    Base class for email backend implementations.

    Subclasses must at least overwrite send_messages().
    """
    def __init__(self, fail_silently=False, **kwargs):
        self.fail_silently = fail_silently

    def open(self, callback=False):
        """Open a network connection.

        This method can be overwritten by backend implementations to
        open a network connection.

        It's up to the backend implementation to track the status of
        a network connection if it's needed by the backend.

        This method can be called by applications to force a single
        network connection to be used when sending mails. See the
        send_messages() method of the SMTP backend for a reference
        implementation.

        The default implementation does nothing.
        """
        pass

    def close(self):
        """Close a network connection."""
        pass

    def send_messages(self, email_messages, callback=False):
        """
        Sends one or more EmailMessage objects and returns the number of email
        messages sent.
        """
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = smtp
"""SMTP email backend class."""
from .. import smtplib
import socket

from .base import BaseEmailBackend
from ..utils import DNS_NAME
from ..message import sanitize_address

from tornado import gen


class EmailBackend(BaseEmailBackend):
    """
    A wrapper that manages the SMTP network connection.
    """
    def __init__(self, host=None, port=None, username=None, password=None,
                 use_tls=None, fail_silently=False, **kwargs):
        super(EmailBackend, self).__init__(fail_silently=fail_silently)
        self.host = host or '127.0.0.1'
        self.port = port or 25
        self.username = username or None
        self.password = password or None
        if use_tls is None:
            self.use_tls = None
        else:
            self.use_tls = use_tls
        self.connection = None
        self.template_loader = kwargs.get('template_loader', None)

    @gen.engine
    def open(self, callback):
        """
        Ensures we have a connection to the email server. Returns whether or
        not a new connection was required (True or False).
        """
        if self.connection:
            # Nothing to do if the connection is already open.
            callback(False)
        try:
            # If local_hostname is not specified, socket.getfqdn() gets used.
            # For performance, we use the cached FQDN for local_hostname.
            self.connection = smtplib.SMTP(self.host, self.port,
                                           local_hostname=DNS_NAME.get_fqdn())
            yield gen.Task(self.connection.connect, self.host, self.port)
            if self.use_tls:
                yield gen.Task(self.connection.ehlo)
                yield gen.Task(self.connection.starttls)
                yield gen.Task(self.connection.ehlo)
            if self.username and self.password:
                yield gen.Task(self.connection.login, self.username, self.password)
            callback(True)
        except:
            if not self.fail_silently:
                raise

    def close(self):
        """Closes the connection to the email server."""
        try:
            try:
                self.connection.quit()
            except socket.sslerror:
                # This happens when calling quit() on a TLS connection
                # sometimes.
                self.connection.close()
            except:
                if self.fail_silently:
                    return
                raise
        finally:
            self.connection = None

    @gen.engine
    def send_messages(self, email_messages, callback=None):
        """
        Sends one or more EmailMessage objects and returns the number of email
        messages sent.
        """
        if not email_messages:
            return

        new_conn_created = yield gen.Task(self.open)
        if not self.connection:
            # We failed silently on open().
            # Trying to send would be pointless.
            return
        num_sent = 0
        for message in email_messages:
            sent = yield gen.Task(self._send, message)
            if sent:
                num_sent += 1
        if new_conn_created:
            self.close()
        if callback:
            callback(num_sent)

    @gen.engine
    def _send(self, email_message, callback=None):
        """A helper method that does the actual sending."""
        if not email_message.recipients():
            if callback:
                callback(False)
        from_email = sanitize_address(email_message.from_email, email_message.encoding)
        recipients = [sanitize_address(addr, email_message.encoding)
                      for addr in email_message.recipients()]
        try:
            yield gen.Task(self.connection.sendmail, from_email, recipients,
                    email_message.message().as_string())
        except:
            if not self.fail_silently:
                raise
            if callback:
                callback(False)
        if callback:
            callback(True)

########NEW FILE########
__FILENAME__ = copycompat
"""
Fixes Python 2.4's failure to deepcopy unbound functions.
"""

import copy
import types

# Monkeypatch copy's deepcopy registry to handle functions correctly.
if (hasattr(copy, '_deepcopy_dispatch') and types.FunctionType not in copy._deepcopy_dispatch):
    copy._deepcopy_dispatch[types.FunctionType] = copy._deepcopy_atomic

# Pose as the copy module now.
del copy, types
from copy import *

########NEW FILE########
__FILENAME__ = encoding
import types
import urllib
import locale
import datetime
import codecs
from decimal import Decimal

from functional import Promise

class TornadomainUnicodeDecodeError(UnicodeDecodeError):
    def __init__(self, obj, *args):
        self.obj = obj
        UnicodeDecodeError.__init__(self, *args)

    def __str__(self):
        original = UnicodeDecodeError.__str__(self)
        return '%s. You passed in %r (%s)' % (original, self.obj,
                type(self.obj))

class StrAndUnicode(object):
    """
    A class whose __str__ returns its __unicode__ as a UTF-8 bytestring.

    Useful as a mix-in.
    """
    def __str__(self):
        return self.__unicode__().encode('utf-8')

def smart_unicode(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a unicode object representing 's'. Treats bytestrings using the
    'encoding' codec.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if isinstance(s, Promise):
        # The input is the result of a gettext_lazy() call.
        return s
    return force_unicode(s, encoding, strings_only, errors)

def is_protected_type(obj):
    """Determine if the object instance is of a protected type.

    Objects of protected types are preserved as-is when passed to
    force_unicode(strings_only=True).
    """
    return isinstance(obj, (
        types.NoneType,
        int, long,
        datetime.datetime, datetime.date, datetime.time,
        float, Decimal)
    )

def force_unicode(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Similar to smart_unicode, except that lazy instances are resolved to
    strings, rather than kept as lazy objects.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    # Handle the common case first, saves 30-40% in performance when s
    # is an instance of unicode. This function gets called often in that
    # setting.
    if isinstance(s, unicode):
        return s
    if strings_only and is_protected_type(s):
        return s
    try:
        if not isinstance(s, basestring,):
            if hasattr(s, '__unicode__'):
                s = unicode(s)
            else:
                try:
                    s = unicode(str(s), encoding, errors)
                except UnicodeEncodeError:
                    if not isinstance(s, Exception):
                        raise
                    # If we get to here, the caller has passed in an Exception
                    # subclass populated with non-ASCII data without special
                    # handling to display as a string. We need to handle this
                    # without raising a further exception. We do an
                    # approximation to what the Exception's standard str()
                    # output should be.
                    s = ' '.join([force_unicode(arg, encoding, strings_only,
                            errors) for arg in s])
        elif not isinstance(s, unicode):
            # Note: We use .decode() here, instead of unicode(s, encoding,
            # errors), so that if s is a SafeString, it ends up being a
            # SafeUnicode at the end.
            s = s.decode(encoding, errors)
    except UnicodeDecodeError, e:
        if not isinstance(s, Exception):
            raise TornadomainUnicodeDecodeError(s, *e.args)
        else:
            # If we get to here, the caller has passed in an Exception
            # subclass populated with non-ASCII bytestring data without a
            # working unicode method. Try to handle this without raising a
            # further exception by individually forcing the exception args
            # to unicode.
            s = ' '.join([force_unicode(arg, encoding, strings_only,
                    errors) for arg in s])
    return s

def smart_str(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if strings_only and isinstance(s, (types.NoneType, int)):
        return s
    if isinstance(s, Promise):
        return unicode(s).encode(encoding, errors)
    elif not isinstance(s, basestring):
        try:
            return str(s)
        except UnicodeEncodeError:
            if isinstance(s, Exception):
                # An Exception subclass containing non-ASCII data that doesn't
                # know how to print itself properly. We shouldn't raise a
                # further exception.
                return ' '.join([smart_str(arg, encoding, strings_only,
                        errors) for arg in s])
            return unicode(s).encode(encoding, errors)
    elif isinstance(s, unicode):
        return s.encode(encoding, errors)
    elif s and encoding != 'utf-8':
        return s.decode('utf-8', errors).encode(encoding, errors)
    else:
        return s

def iri_to_uri(iri):
    """
    Convert an Internationalized Resource Identifier (IRI) portion to a URI
    portion that is suitable for inclusion in a URL.

    This is the algorithm from section 3.1 of RFC 3987.  However, since we are
    assuming input is either UTF-8 or unicode already, we can simplify things a
    little from the full method.

    Returns an ASCII string containing the encoded result.
    """
    # The list of safe characters here is constructed from the "reserved" and
    # "unreserved" characters specified in sections 2.2 and 2.3 of RFC 3986:
    #     reserved    = gen-delims / sub-delims
    #     gen-delims  = ":" / "/" / "?" / "#" / "[" / "]" / "@"
    #     sub-delims  = "!" / "$" / "&" / "'" / "(" / ")"
    #                   / "*" / "+" / "," / ";" / "="
    #     unreserved  = ALPHA / DIGIT / "-" / "." / "_" / "~"
    # Of the unreserved characters, urllib.quote already considers all but
    # the ~ safe.
    # The % character is also added to the list of safe characters here, as the
    # end of section 3.1 of RFC 3987 specifically mentions that % must not be
    # converted.
    if iri is None:
        return iri
    return urllib.quote(smart_str(iri), safe="/#%[]=:;$&()+,!?*@'~")

def filepath_to_uri(path):
    """Convert an file system path to a URI portion that is suitable for
    inclusion in a URL.

    We are assuming input is either UTF-8 or unicode already.

    This method will encode certain chars that would normally be recognized as
    special chars for URIs.  Note that this method does not encode the '
    character, as it is a valid character within URIs.  See
    encodeURIComponent() JavaScript function for more details.

    Returns an ASCII string containing the encoded result.
    """
    if path is None:
        return path
    # I know about `os.sep` and `os.altsep` but I want to leave
    # some flexibility for hardcoding separators.
    return urllib.quote(smart_str(path).replace("\\", "/"), safe="/~!*()'")

# The encoding of the default system locale but falls back to the
# given fallback encoding if the encoding is unsupported by python or could
# not be determined.  See tickets #10335 and #5846
try:
    DEFAULT_LOCALE_ENCODING = locale.getdefaultlocale()[1] or 'ascii'
    codecs.lookup(DEFAULT_LOCALE_ENCODING)
except:
    DEFAULT_LOCALE_ENCODING = 'ascii'

########NEW FILE########
__FILENAME__ = functional
# License for code in this file that was taken from Python 2.5.

# PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2
# --------------------------------------------
#
# 1. This LICENSE AGREEMENT is between the Python Software Foundation
# ("PSF"), and the Individual or Organization ("Licensee") accessing and
# otherwise using this software ("Python") in source or binary form and
# its associated documentation.
#
# 2. Subject to the terms and conditions of this License Agreement, PSF
# hereby grants Licensee a nonexclusive, royalty-free, world-wide
# license to reproduce, analyze, test, perform and/or display publicly,
# prepare derivative works, distribute, and otherwise use Python
# alone or in any derivative version, provided, however, that PSF's
# License Agreement and PSF's notice of copyright, i.e., "Copyright (c)
# 2001, 2002, 2003, 2004, 2005, 2006, 2007 Python Software Foundation;
# All Rights Reserved" are retained in Python alone or in any derivative
# version prepared by Licensee.
#
# 3. In the event Licensee prepares a derivative work that is based on
# or incorporates Python or any part thereof, and wants to make
# the derivative work available to others as provided herein, then
# Licensee hereby agrees to include in any such work a brief summary of
# the changes made to Python.
#
# 4. PSF is making Python available to Licensee on an "AS IS"
# basis.  PSF MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR
# IMPLIED.  BY WAY OF EXAMPLE, BUT NOT LIMITATION, PSF MAKES NO AND
# DISCLAIMS ANY REPRESENTATION OR WARRANTY OF MERCHANTABILITY OR FITNESS
# FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF PYTHON WILL NOT
# INFRINGE ANY THIRD PARTY RIGHTS.
#
# 5. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON
# FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS
# A RESULT OF MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON,
# OR ANY DERIVATIVE THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.
#
# 6. This License Agreement will automatically terminate upon a material
# breach of its terms and conditions.
#
# 7. Nothing in this License Agreement shall be deemed to create any
# relationship of agency, partnership, or joint venture between PSF and
# Licensee.  This License Agreement does not grant permission to use PSF
# trademarks or trade name in a trademark sense to endorse or promote
# products or services of Licensee, or any third party.
#
# 8. By copying, installing or otherwise using Python, Licensee
# agrees to be bound by the terms and conditions of this License
# Agreement.


def curry(_curried_func, *args, **kwargs):
    def _curried(*moreargs, **morekwargs):
        return _curried_func(*(args+moreargs), **dict(kwargs, **morekwargs))
    return _curried

### Begin from Python 2.5 functools.py ########################################

# Summary of changes made to the Python 2.5 code below:
#   * swapped ``partial`` for ``curry`` to maintain backwards-compatibility
#     in Django.

# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007 Python Software Foundation.
# All Rights Reserved.

###############################################################################

# update_wrapper() and wraps() are tools to help write
# wrapper functions that can handle naive introspection

WRAPPER_ASSIGNMENTS = ('__module__', '__name__', '__doc__')
WRAPPER_UPDATES = ('__dict__',)
def update_wrapper(wrapper,
                   wrapped,
                   assigned = WRAPPER_ASSIGNMENTS,
                   updated = WRAPPER_UPDATES):
    """Update a wrapper function to look like the wrapped function

       wrapper is the function to be updated
       wrapped is the original function
       assigned is a tuple naming the attributes assigned directly
       from the wrapped function to the wrapper function (defaults to
       functools.WRAPPER_ASSIGNMENTS)
       updated is a tuple naming the attributes off the wrapper that
       are updated with the corresponding attribute from the wrapped
       function (defaults to functools.WRAPPER_UPDATES)
    """
    for attr in assigned:
        setattr(wrapper, attr, getattr(wrapped, attr))
    for attr in updated:
        getattr(wrapper, attr).update(getattr(wrapped, attr))
    # Return the wrapper so this can be used as a decorator via curry()
    return wrapper

def wraps(wrapped,
          assigned = WRAPPER_ASSIGNMENTS,
          updated = WRAPPER_UPDATES):
    """Decorator factory to apply update_wrapper() to a wrapper function

       Returns a decorator that invokes update_wrapper() with the decorated
       function as the wrapper argument and the arguments to wraps() as the
       remaining arguments. Default arguments are as for update_wrapper().
       This is a convenience function to simplify applying curry() to
       update_wrapper().
    """
    return curry(update_wrapper, wrapped=wrapped,
                 assigned=assigned, updated=updated)

### End from Python 2.5 functools.py ##########################################

def memoize(func, cache, num_args):
    """
    Wrap a function so that results for any argument tuple are stored in
    'cache'. Note that the args to the function must be usable as dictionary
    keys.

    Only the first num_args are considered when creating the key.
    """
    def wrapper(*args):
        mem_args = args[:num_args]
        if mem_args in cache:
            return cache[mem_args]
        result = func(*args)
        cache[mem_args] = result
        return result
    return wraps(func)(wrapper)

class Promise(object):
    """
    This is just a base class for the proxy class created in
    the closure of the lazy function. It can be used to recognize
    promises in code.
    """
    pass

def lazy(func, *resultclasses):
    """
    Turns any callable into a lazy evaluated callable. You need to give result
    classes or types -- at least one is needed so that the automatic forcing of
    the lazy evaluation code is triggered. Results are not memoized; the
    function is evaluated on every access.
    """

    class __proxy__(Promise):
        """
        Encapsulate a function call and act as a proxy for methods that are
        called on the result of that function. The function is not evaluated
        until one of the methods on the result is called.
        """
        __dispatch = None

        def __init__(self, args, kw):
            self.__func = func
            self.__args = args
            self.__kw = kw
            if self.__dispatch is None:
                self.__prepare_class__()

        def __reduce__(self):
            return (
                _lazy_proxy_unpickle,
                (self.__func, self.__args, self.__kw) + resultclasses
            )

        def __prepare_class__(cls):
            cls.__dispatch = {}
            for resultclass in resultclasses:
                cls.__dispatch[resultclass] = {}
                for (k, v) in resultclass.__dict__.items():
                    # All __promise__ return the same wrapper method, but they
                    # also do setup, inserting the method into the dispatch
                    # dict.
                    meth = cls.__promise__(resultclass, k, v)
                    if hasattr(cls, k):
                        continue
                    setattr(cls, k, meth)
            cls._delegate_str = str in resultclasses
            cls._delegate_unicode = unicode in resultclasses
            assert not (cls._delegate_str and cls._delegate_unicode), "Cannot call lazy() with both str and unicode return types."
            if cls._delegate_unicode:
                cls.__unicode__ = cls.__unicode_cast
            elif cls._delegate_str:
                cls.__str__ = cls.__str_cast
        __prepare_class__ = classmethod(__prepare_class__)

        def __promise__(cls, klass, funcname, func):
            # Builds a wrapper around some magic method and registers that magic
            # method for the given type and method name.
            def __wrapper__(self, *args, **kw):
                # Automatically triggers the evaluation of a lazy value and
                # applies the given magic method of the result type.
                res = self.__func(*self.__args, **self.__kw)
                for t in type(res).mro():
                    if t in self.__dispatch:
                        return self.__dispatch[t][funcname](res, *args, **kw)
                raise TypeError("Lazy object returned unexpected type.")

            if klass not in cls.__dispatch:
                cls.__dispatch[klass] = {}
            cls.__dispatch[klass][funcname] = func
            return __wrapper__
        __promise__ = classmethod(__promise__)

        def __unicode_cast(self):
            return self.__func(*self.__args, **self.__kw)

        def __str_cast(self):
            return str(self.__func(*self.__args, **self.__kw))

        def __cmp__(self, rhs):
            if self._delegate_str:
                s = str(self.__func(*self.__args, **self.__kw))
            elif self._delegate_unicode:
                s = unicode(self.__func(*self.__args, **self.__kw))
            else:
                s = self.__func(*self.__args, **self.__kw)
            if isinstance(rhs, Promise):
                return -cmp(rhs, s)
            else:
                return cmp(s, rhs)

        def __mod__(self, rhs):
            if self._delegate_str:
                return str(self) % rhs
            elif self._delegate_unicode:
                return unicode(self) % rhs
            else:
                raise AssertionError('__mod__ not supported for non-string types')

        def __deepcopy__(self, memo):
            # Instances of this class are effectively immutable. It's just a
            # collection of functions. So we don't need to do anything
            # complicated for copying.
            memo[id(self)] = self
            return self

    def __wrapper__(*args, **kw):
        # Creates the proxy object, instead of the actual value.
        return __proxy__(args, kw)

    return wraps(func)(__wrapper__)

def _lazy_proxy_unpickle(func, args, kwargs, *resultclasses):
    return lazy(func, *resultclasses)(*args, **kwargs)

def allow_lazy(func, *resultclasses):
    """
    A decorator that allows a function to be called with one or more lazy
    arguments. If none of the args are lazy, the function is evaluated
    immediately, otherwise a __proxy__ is returned that will evaluate the
    function when needed.
    """
    def wrapper(*args, **kwargs):
        for arg in list(args) + kwargs.values():
            if isinstance(arg, Promise):
                break
        else:
            return func(*args, **kwargs)
        return lazy(func, *resultclasses)(*args, **kwargs)
    return wraps(func)(wrapper)

class LazyObject(object):
    """
    A wrapper for another class that can be used to delay instantiation of the
    wrapped class.

    By subclassing, you have the opportunity to intercept and alter the
    instantiation. If you don't need to do that, use SimpleLazyObject.
    """
    def __init__(self):
        self._wrapped = None

    def __getattr__(self, name):
        if self._wrapped is None:
            self._setup()
        return getattr(self._wrapped, name)

    def __setattr__(self, name, value):
        if name == "_wrapped":
            # Assign to __dict__ to avoid infinite __setattr__ loops.
            self.__dict__["_wrapped"] = value
        else:
            if self._wrapped is None:
                self._setup()
            setattr(self._wrapped, name, value)

    def __delattr__(self, name):
        if name == "_wrapped":
            raise TypeError("can't delete _wrapped.")
        if self._wrapped is None:
            self._setup()
        delattr(self._wrapped, name)

    def _setup(self):
        """
        Must be implemented by subclasses to initialise the wrapped object.
        """
        raise NotImplementedError

    # introspection support:
    __members__ = property(lambda self: self.__dir__())

    def __dir__(self):
        if self._wrapped is None:
            self._setup()
        return  dir(self._wrapped)

class SimpleLazyObject(LazyObject):
    """
    A lazy object initialised from any function.

    Designed for compound objects of unknown type. For builtins or objects of
    known type, use django.utils.functional.lazy.
    """
    def __init__(self, func):
        """
        Pass in a callable that returns the object to be wrapped.

        If copies are made of the resulting SimpleLazyObject, which can happen
        in various circumstances within Django, then you must ensure that the
        callable can be safely run more than once and will return the same
        value.
        """
        self.__dict__['_setupfunc'] = func
        # For some reason, we have to inline LazyObject.__init__ here to avoid
        # recursion
        self._wrapped = None

    def __str__(self):
        if self._wrapped is None: self._setup()
        return str(self._wrapped)

    def __unicode__(self):
        if self._wrapped is None: self._setup()
        return unicode(self._wrapped)

    def __deepcopy__(self, memo):
        if self._wrapped is None:
            # We have to use SimpleLazyObject, not self.__class__, because the
            # latter is proxied.
            result = SimpleLazyObject(self._setupfunc)
            memo[id(self)] = result
            return result
        else:
            # Changed to use deepcopy from copycompat, instead of copy
            # For Python 2.4.
            from copycompat import deepcopy
            return deepcopy(self._wrapped, memo)

    # Need to pretend to be the wrapped class, for the sake of objects that care
    # about this (especially in equality tests)
    def __get_class(self):
        if self._wrapped is None: self._setup()
        return self._wrapped.__class__
    __class__ = property(__get_class)

    def __eq__(self, other):
        if self._wrapped is None: self._setup()
        return self._wrapped == other

    def __hash__(self):
        if self._wrapped is None: self._setup()
        return hash(self._wrapped)

    def _setup(self):
        self._wrapped = self._setupfunc()

########NEW FILE########
__FILENAME__ = importlib
# Taken from Python 2.7 with permission from/by the original author.
import sys

def _resolve_name(name, package, level):
    """Return the absolute name of the module to be imported."""
    if not hasattr(package, 'rindex'):
        raise ValueError("'package' not set to a string")
    dot = len(package)
    for x in xrange(level, 1, -1):
        try:
            dot = package.rindex('.', 0, dot)
        except ValueError:
            raise ValueError("attempted relative import beyond top-level "
                              "package")
    return "%s.%s" % (package[:dot], name)


def import_module(name, package=None):
    """Import a module.

    The 'package' argument is required when performing a relative import. It
    specifies the package to use as the anchor point from which to resolve the
    relative import to an absolute import.

    """
    if name.startswith('.'):
        if not package:
            raise TypeError("relative imports require the 'package' argument")
        level = 0
        for character in name:
            if character != '.':
                break
            level += 1
        name = _resolve_name(name[level:], package, level)
    __import__(name)
    return sys.modules[name]

########NEW FILE########
__FILENAME__ = message
import mimetypes
import os
import random
import time
from email import Charset, Encoders
try:
    from email.generator import Generator
except ImportError:
    from email.Generator import Generator # TODO: Remove when remove Python 2.4 support
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.Header import Header
from email.Utils import formatdate, getaddresses, formataddr, parseaddr

from utils import DNS_NAME
from encoding import smart_str, force_unicode

from tornado import gen

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

# Don't BASE64-encode UTF-8 messages so that we avoid unwanted attention from
# some spam filters.
Charset.add_charset('utf-8', Charset.SHORTEST, Charset.QP, 'utf-8')

# Default MIME type to use on attachments (if it is not explicitly given
# and cannot be guessed).
DEFAULT_ATTACHMENT_MIME_TYPE = 'application/octet-stream'
DEFAULT_CHARSET = 'utf8'
DEFAULT_FROM_MAIL = 'noreply@localhost'


class BadHeaderError(ValueError):
    pass


# Copied from Python standard library, with the following modifications:
# * Used cached hostname for performance.
# * Added try/except to support lack of getpid() in Jython (#5496).
def make_msgid(idstring=None):
    """Returns a string suitable for RFC 2822 compliant Message-ID, e.g:

    <20020201195627.33539.96671@nightshade.la.mastaler.com>

    Optional idstring if given is a string used to strengthen the
    uniqueness of the message id.
    """
    timeval = time.time()
    utcdate = time.strftime('%Y%m%d%H%M%S', time.gmtime(timeval))
    try:
        pid = os.getpid()
    except AttributeError:
        # No getpid() in Jython, for example.
        pid = 1
    randint = random.randrange(100000)
    if idstring is None:
        idstring = ''
    else:
        idstring = '.' + idstring
    idhost = DNS_NAME
    msgid = '<%s.%s.%s%s@%s>' % (utcdate, pid, randint, idstring, idhost)
    return msgid


# Header names that contain structured address data (RFC #5322)
ADDRESS_HEADERS = set([
    'from',
    'sender',
    'reply-to',
    'to',
    'cc',
    'bcc',
    'resent-from',
    'resent-sender',
    'resent-to',
    'resent-cc',
    'resent-bcc',
])


def forbid_multi_line_headers(name, val, encoding):
    """Forbids multi-line headers, to prevent header injection."""
    encoding = encoding or DEFAULT_CHARSET
    val = force_unicode(val)
    if '\n' in val or '\r' in val:
        raise BadHeaderError("Header values can't contain newlines (got %r for header %r)" % (val, name))
    try:
        val = val.encode('ascii')
    except UnicodeEncodeError:
        if name.lower() in ADDRESS_HEADERS:
            val = ', '.join(sanitize_address(addr, encoding)
                for addr in getaddresses((val,)))
        else:
            val = str(Header(val, encoding))
    else:
        if name.lower() == 'subject':
            val = Header(val)
    return name, val


def sanitize_address(addr, encoding):
    if isinstance(addr, basestring):
        addr = parseaddr(force_unicode(addr))
    nm, addr = addr
    nm = str(Header(nm, encoding))
    try:
        addr = addr.encode('ascii')
    except UnicodeEncodeError:  # IDN
        if u'@' in addr:
            localpart, domain = addr.split(u'@', 1)
            localpart = str(Header(localpart, encoding))
            domain = domain.encode('idna')
            addr = '@'.join([localpart, domain])
        else:
            addr = str(Header(addr, encoding))
    return formataddr((nm, addr))


class SafeMIMEText(MIMEText):

    def __init__(self, text, subtype, charset):
        self.encoding = charset
        MIMEText.__init__(self, text, subtype, charset)

    def __setitem__(self, name, val):
        name, val = forbid_multi_line_headers(name, val, self.encoding)
        MIMEText.__setitem__(self, name, val)

    def as_string(self, unixfrom=False):
        """Return the entire formatted message as a string.
        Optional `unixfrom' when True, means include the Unix From_ envelope
        header.

        This overrides the default as_string() implementation to not mangle
        lines that begin with 'From '. See bug #13433 for details.
        """
        fp = StringIO()
        g = Generator(fp, mangle_from_ = False)
        g.flatten(self, unixfrom=unixfrom)
        return fp.getvalue()


class SafeMIMEMultipart(MIMEMultipart):

    def __init__(self, _subtype='mixed', boundary=None, _subparts=None, encoding=None, **_params):
        self.encoding = encoding
        MIMEMultipart.__init__(self, _subtype, boundary, _subparts, **_params)

    def __setitem__(self, name, val):
        name, val = forbid_multi_line_headers(name, val, self.encoding)
        MIMEMultipart.__setitem__(self, name, val)

    def as_string(self, unixfrom=False):
        """Return the entire formatted message as a string.
        Optional `unixfrom' when True, means include the Unix From_ envelope
        header.

        This overrides the default as_string() implementation to not mangle
        lines that begin with 'From '. See bug #13433 for details.
        """
        fp = StringIO()
        g = Generator(fp, mangle_from_ = False)
        g.flatten(self, unixfrom=unixfrom)
        return fp.getvalue()


class EmailMessage(object):
    """
    A container for email information.
    """
    content_subtype = 'plain'
    mixed_subtype = 'mixed'
    encoding = None     # None => use settings default

    def __init__(self, subject='', body='', from_email=None, to=None, bcc=None,
                 connection=None, attachments=None, headers=None, cc=None, reply_to=None):
        """
        Initialize a single email message (which can be sent to multiple
        recipients).

        All strings used to create the message can be unicode strings
        (or UTF-8 bytestrings). The SafeMIMEText class will handle any
        necessary encoding conversions.
        """
        if to:
            assert not isinstance(to, basestring), '"to" argument must be a list or tuple'
            self.to = list(to)
        else:
            self.to = []
        if cc:
            assert not isinstance(cc, basestring), '"cc" argument must be a list or tuple'
            self.cc = list(cc)
        else:
            self.cc = []
        if bcc:
            assert not isinstance(bcc, basestring), '"bcc" argument must be a list or tuple'
            self.bcc = list(bcc)
        else:
            self.bcc = []
        self.from_email = from_email or DEFAULT_FROM_EMAIL
        self.reply_to = reply_to
        self.subject = subject
        self.body = body
        self.attachments = attachments or []
        self.extra_headers = headers or {}
        self.connection = connection

    def get_connection(self, fail_silently=False):
        from . import get_connection
        if not self.connection:
            self.connection = get_connection(fail_silently=fail_silently)
        return self.connection

    def message(self):
        encoding = self.encoding or DEFAULT_CHARSET
        msg = SafeMIMEText(smart_str(self.body, encoding),
                           self.content_subtype, encoding)
        msg = self._create_message(msg)
        msg['Subject'] = self.subject
        msg['From'] = self.extra_headers.get('From', self.from_email)
        if self.reply_to:
        	msg['Reply-To'] = self.reply_to
        msg['To'] = ', '.join(self.to)
        if self.cc:
            msg['Cc'] = ', '.join(self.cc)

        # Email header names are case-insensitive (RFC 2045), so we have to
        # accommodate that when doing comparisons.
        header_names = [key.lower() for key in self.extra_headers]
        if 'date' not in header_names:
            msg['Date'] = formatdate()
        if 'message-id' not in header_names:
            msg['Message-ID'] = make_msgid()
        for name, value in self.extra_headers.items():
            if name.lower() == 'from':  # From is already handled
                continue
            msg[name] = value
        return msg

    def recipients(self):
        """
        Returns a list of all recipients of the email (includes direct
        addressees as well as Cc and Bcc entries).
        """
        return self.to + self.cc + self.bcc

    @gen.engine
    def send(self, fail_silently=False, callback=None):
        """Sends the email message."""
        if not self.recipients():
            # Don't bother creating the network connection if there's nobody to
            # send to.
            if callback:
                callback(0)
                return
        result = yield gen.Task(self.get_connection(fail_silently).send_messages, [self])
        if callback:
            callback(result)

    def attach(self, filename=None, content=None, mimetype=None):
        """
        Attaches a file with the given filename and content. The filename can
        be omitted and the mimetype is guessed, if not provided.

        If the first parameter is a MIMEBase subclass it is inserted directly
        into the resulting message attachments.
        """
        if isinstance(filename, MIMEBase):
            assert content == mimetype == None
            self.attachments.append(filename)
        else:
            assert content is not None
            self.attachments.append((filename, content, mimetype))

    def attach_file(self, path, mimetype=None):
        """Attaches a file from the filesystem."""
        filename = os.path.basename(path)
        content = open(path, 'rb').read()
        self.attach(filename, content, mimetype)

    def _create_message(self, msg):
        return self._create_attachments(msg)

    def _create_attachments(self, msg):
        if self.attachments:
            encoding = self.encoding or DEFAULT_CHARSET
            body_msg = msg
            msg = SafeMIMEMultipart(_subtype=self.mixed_subtype, encoding=encoding)
            if self.body:
                msg.attach(body_msg)
            for attachment in self.attachments:
                if isinstance(attachment, MIMEBase):
                    msg.attach(attachment)
                else:
                    msg.attach(self._create_attachment(*attachment))
        return msg

    def _create_mime_attachment(self, content, mimetype):
        """
        Converts the content, mimetype pair into a MIME attachment object.
        """
        basetype, subtype = mimetype.split('/', 1)
        if basetype == 'text':
            encoding = self.encoding or DEFAULT_CHARSET
            attachment = SafeMIMEText(smart_str(content, encoding), subtype, encoding)
        else:
            # Encode non-text attachments with base64.
            attachment = MIMEBase(basetype, subtype)
            attachment.set_payload(content)
            Encoders.encode_base64(attachment)
        return attachment

    def _create_attachment(self, filename, content, mimetype=None):
        """
        Converts the filename, content, mimetype triple into a MIME attachment
        object.
        """
        if mimetype is None:
            mimetype, _ = mimetypes.guess_type(filename)
            if mimetype is None:
                mimetype = DEFAULT_ATTACHMENT_MIME_TYPE
        attachment = self._create_mime_attachment(content, mimetype)
        if filename:
            attachment.add_header('Content-Disposition', 'attachment',
                                  filename=filename)
        return attachment


class EmailMultiAlternatives(EmailMessage):
    """
    A version of EmailMessage that makes it easy to send multipart/alternative
    messages. For example, including text and HTML versions of the text is
    made easier.
    """
    alternative_subtype = 'alternative'

    def __init__(self, subject='', body='', from_email=None, to=None, bcc=None,
            connection=None, attachments=None, headers=None, alternatives=None,
            cc=None, reply_to=None):
        """
        Initialize a single email message (which can be sent to multiple
        recipients).

        All strings used to create the message can be unicode strings (or UTF-8
        bytestrings). The SafeMIMEText class will handle any necessary encoding
        conversions.
        """
        super(EmailMultiAlternatives, self).__init__(subject, body, from_email, to, bcc, connection, attachments, headers, cc, reply_to)
        self.alternatives = alternatives or []

    def attach_alternative(self, content, mimetype):
        """Attach an alternative content representation."""
        assert content is not None
        assert mimetype is not None
        self.alternatives.append((content, mimetype))

    def _create_message(self, msg):
        return self._create_attachments(self._create_alternatives(msg))

    def _create_alternatives(self, msg):
        encoding = self.encoding or DEFAULT_CHARSET
        if self.alternatives:
            body_msg = msg
            msg = SafeMIMEMultipart(_subtype=self.alternative_subtype, encoding=encoding)
            if self.body:
                msg.attach(body_msg)
            for alternative in self.alternatives:
                msg.attach(self._create_mime_attachment(*alternative))
        return msg


class EmailFromTemplate(EmailMultiAlternatives):
    """
    A version of EmailMultiAlternatives that builds body with the result from
    generate a template HTML and parameters.
    """
    content_subtype = "html"

    def __init__(self, subject, template, params={}, from_email=None, to=None,
            bcc=None, connection=None, attachments=None, headers=None,
            alternatives=None, cc=None, reply_to=None):
        if not connection.template_loader:
            raise Exception("Must to set a template_loader to connection")
        body = connection.template_loader.load(template).generate(**params)
        super(EmailFromTemplate, self).__init__(subject, body, from_email, to,
            bcc, connection, attachments, headers, alternatives, cc, reply_to)

########NEW FILE########
__FILENAME__ = smtplib
#! /usr/bin/env python

'''SMTP/ESMTP client class.

This should follow RFC 821 (SMTP), RFC 1869 (ESMTP), RFC 2554 (SMTP
Authentication) and RFC 2487 (Secure SMTP over TLS).

Notes:

Please remember, when doing ESMTP, that the names of the SMTP service
extensions are NOT the same thing as the option keywords for the RCPT
and MAIL commands!

Example:

  >>> import smtplib
  >>> s=smtplib.SMTP("localhost")
  >>> print s.help()
  This is Sendmail version 8.8.4
  Topics:
      HELO    EHLO    MAIL    RCPT    DATA
      RSET    NOOP    QUIT    HELP    VRFY
      EXPN    VERB    ETRN    DSN
  For more info use "HELP <topic>".
  To report bugs in the implementation send email to
      sendmail-bugs@sendmail.org.
  For local information send email to Postmaster at your site.
  End of HELP info
  >>> s.putcmd("vrfy","someone@here")
  >>> s.getreply()
  (250, "Somebody OverHere <somebody@here.my.org>")
  >>> s.quit()
'''

# Author: The Dragon De Monsyne <dragondm@integral.org>
# ESMTP support, test code and doc fixes added by
#     Eric S. Raymond <esr@thyrsus.com>
# Better RFC 821 compliance (MAIL and RCPT, and CRLF in data)
#     by Carey Evans <c.evans@clear.net.nz>, for picky mail servers.
# RFC 2554 (authentication) support by Gerhard Haering <gerhard@bigfoot.de>.
#
# This was modified from the Python 1.5 library HTTP lib.

import socket
import re
import email.utils
import base64
import hmac
from email.base64mime import encode as encode_base64
from sys import stderr
from functools import partial
import contextlib

from tornado import gen
from tornado import iostream
from tornado import ioloop
from tornado import stack_context

__all__ = ["SMTPException","SMTPServerDisconnected","SMTPResponseException",
           "SMTPSenderRefused","SMTPRecipientsRefused","SMTPDataError",
           "SMTPConnectError","SMTPHeloError","SMTPAuthenticationError",
           "quoteaddr","quotedata","SMTP"]

SMTP_PORT = 25
SMTP_SSL_PORT = 465
CRLF="\r\n"

OLDSTYLE_AUTH = re.compile(r"auth=(.*)", re.I)

# Exception classes used by this module.
class SMTPException(Exception):
    """Base class for all exceptions raised by this module."""

class SMTPServerDisconnected(SMTPException):
    """Not connected to any SMTP server.

    This exception is raised when the server unexpectedly disconnects,
    or when an attempt is made to use the SMTP instance before
    connecting it to a server.
    """

class SMTPResponseException(SMTPException):
    """Base class for all exceptions that include an SMTP error code.

    These exceptions are generated in some instances when the SMTP
    server returns an error code.  The error code is stored in the
    `smtp_code' attribute of the error, and the `smtp_error' attribute
    is set to the error message.
    """

    def __init__(self, code, msg):
        self.smtp_code = code
        self.smtp_error = msg
        self.args = (code, msg)

class SMTPSenderRefused(SMTPResponseException):
    """Sender address refused.

    In addition to the attributes set by on all SMTPResponseException
    exceptions, this sets `sender' to the string that the SMTP refused.
    """

    def __init__(self, code, msg, sender):
        self.smtp_code = code
        self.smtp_error = msg
        self.sender = sender
        self.args = (code, msg, sender)

class SMTPRecipientsRefused(SMTPException):
    """All recipient addresses refused.

    The errors for each recipient are accessible through the attribute
    'recipients', which is a dictionary of exactly the same sort as
    SMTP.sendmail() returns.
    """

    def __init__(self, recipients):
        self.recipients = recipients
        self.args = ( recipients,)


class SMTPDataError(SMTPResponseException):
    """The SMTP server didn't accept the data."""

class SMTPConnectError(SMTPResponseException):
    """Error during connection establishment."""

class SMTPHeloError(SMTPResponseException):
    """The server refused our HELO reply."""

class SMTPAuthenticationError(SMTPResponseException):
    """Authentication error.

    Most probably the server didn't accept the username/password
    combination provided.
    """

def quoteaddr(addr):
    """Quote a subset of the email addresses defined by RFC 821.

    Should be able to handle anything rfc822.parseaddr can handle.
    """
    m = (None, None)
    try:
        m = email.utils.parseaddr(addr)[1]
    except AttributeError:
        pass
    if m == (None, None): # Indicates parse failure or AttributeError
        # something weird here.. punt -ddm
        return "<%s>" % addr
    elif m is None:
        # the sender wants an empty return address
        return "<>"
    else:
        return "<%s>" % m

def quotedata(data):
    """Quote data for email.

    Double leading '.', and change Unix newline '\\n', or Mac '\\r' into
    Internet CRLF end-of-line.
    """
    return re.sub(r'(?m)^\.', '..',
        re.sub(r'(?:\r\n|\n|\r(?!\n))', CRLF, data))


try:
    import ssl
except ImportError:
    _have_ssl = False
else:
    class SSLFakeFile:
        """A fake file like object that really wraps a SSLObject.

        It only supports what is needed in smtplib.
        """
        def __init__(self, sslobj):
            self.sslobj = sslobj

        def readline(self):
            str = ""
            chr = None
            while chr != "\n":
                chr = self.sslobj.read(1)
                if not chr: break
                str += chr
            return str

        def close(self):
            pass

    _have_ssl = True

class SMTP:
    """This class manages a connection to an SMTP or ESMTP server.
    SMTP Objects:
        SMTP objects have the following attributes:
            helo_resp
                This is the message given by the server in response to the
                most recent HELO command.

            ehlo_resp
                This is the message given by the server in response to the
                most recent EHLO command. This is usually multiline.

            does_esmtp
                This is a True value _after you do an EHLO command_, if the
                server supports ESMTP.

            esmtp_features
                This is a dictionary, which, if the server supports ESMTP,
                will _after you do an EHLO command_, contain the names of the
                SMTP service extensions this server supports, and their
                parameters (if any).

                Note, all extension names are mapped to lower case in the
                dictionary.

        See each method's docstrings for details.  In general, there is a
        method of the same name to perform each SMTP command.  There is also a
        method called 'sendmail' that will do an entire mail transaction.
        """
    debuglevel = 0
    file = None
    helo_resp = None
    ehlo_msg = "ehlo"
    ehlo_resp = None
    does_esmtp = 0

    def __init__(self, host, port=0, local_hostname=None,
                 timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
        """Initialize a new instance.

        If specified, `host' is the name of the remote host to which to
        connect.  If specified, `port' specifies the port to which to connect.
        By default, smtplib.SMTP_PORT is used.  An SMTPConnectError is raised
        if the specified `host' doesn't respond correctly.  If specified,
        `local_hostname` is used as the FQDN of the local host.  By default,
        the local hostname is found using socket.getfqdn().

        """
        self.timeout = timeout
        self.esmtp_features = {}
        self.default_port = SMTP_PORT
        self.local_hostname = local_hostname or 'localhost'
        #if host:
        #    (code, msg) = self.connect(host, port)
        #    if code != 220:
        #        raise SMTPConnectError(code, msg)

    def set_debuglevel(self, debuglevel):
        """Set the debug output level.

        A non-false value results in debug messages for connection and for all
        messages sent to and received from the server.

        """
        self.debuglevel = debuglevel
                    
    def _get_socket(self, port, host, timeout, callback):
        # This makes it simpler for SMTP_SSL to use the SMTP connect code
        # and just alter the socket connection bit.

        if hasattr(self, '__get_socket'):
            callback(self.__get_socket)
            return
        if self.debuglevel > 0: print>>stderr, 'connect:', (host, port)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        stream = iostream.IOStream(s)
        callback = partial(callback, socket=stream)
        stream.connect((host, port))
        self.__get_socket = stream
        callback(stream)

    def _get_ssl_socket(self, stream, **kwargs):
        # This makes it simpler for SMTP_SSL to use the SMTP connect code
        # and just alter the socket connection bit.
        callback = kwargs.pop('callback')
        if hasattr(self, '__get_ssl_socket'):
            callback(self.__get_ssl_socket)
            return
        s = ssl.wrap_socket(stream.socket, do_handshake_on_connect=False, **kwargs)
        stream.close()
        stream = iostream.SSLIOStream(s)
        self.__get_ssl_socket = stream
        callback(stream)

    @gen.engine
    def connect(self, host='localhost', port = 0, callback=None):
        """Connect to a host on a given port.

        If the hostname ends with a colon (`:') followed by a number, and
        there is no port specified, that suffix will be stripped off and the
        number interpreted as the port number to use.

        Note: This method is automatically invoked by __init__, if a host is
        specified during instantiation.

        """
        if not port and (host.find(':') == host.rfind(':')):
            i = host.rfind(':')
            if i >= 0:
                host, port = host[:i], host[i+1:]
                try: port = int(port)
                except ValueError:
                    raise socket.error, "nonnumeric port"
        if not port: port = self.default_port
        result = yield gen.Task(
            self._get_socket, port, host, self.timeout
        )
        self.sock = result.kwargs['socket']
        if self.debuglevel > 0: print>>stderr, 'connect:', (host, port)
        result = yield gen.Task(self.getreply)
        (code, msg) = result.args
        if self.debuglevel > 0: print>>stderr, "connect:", msg
        if callback:
            callback(code, msg)

    def send(self, str, callback):
        """Send `str' to the server."""
        if self.debuglevel > 0: print>>stderr, 'send:', repr(str)
        if hasattr(self, 'sock') and self.sock:
            try:
                self.sock.write(str, callback)
            except socket.error:
                self.close()
                raise SMTPServerDisconnected('Server not connected')
        else:
            raise SMTPServerDisconnected('please run connect() first')

    def putcmd(self, cmd, args="", callback=None):
        """Send a command to the server."""
        if args == "":
            str = '%s%s' % (cmd, CRLF)
        else:
            str = '%s %s%s' % (cmd, args, CRLF)
        self.send(str, callback=callback)

    @gen.engine
    def getreply(self, callback):
        """Get a reply from the server.

        Returns a tuple consisting of:

          - server response code (e.g. '250', or such, if all goes well)
            Note: returns -1 if it can't read response code.

          - server response string corresponding to response code (multiline
            responses are converted to a single, multiline string).

        Raises SMTPServerDisconnected if end-of-file is reached.
        """
        resp=[]
        while 1:
            try:
                line = yield gen.Task(self.sock.read_until, '\n')
            except socket.error:
                line = ''
            if line == '':
                self.close()
                raise SMTPServerDisconnected("Connection unexpectedly closed")
            if self.debuglevel > 0: print>>stderr, 'reply:', repr(line)
            resp.append(line[4:].strip())
            code=line[:3]
            # Check that the error code is syntactically correct.
            # Don't attempt to read a continuation line if it is broken.
            try:
                errcode = int(code)
            except ValueError:
                errcode = -1
                break
            # Check if multiline response.
            if line[3:4]!="-":
                break

        errmsg = "\n".join(resp)
        if self.debuglevel > 0:
            print>>stderr, 'reply: retcode (%s); Msg: %s' % (errcode,errmsg)
        callback(errcode, errmsg)

    @gen.engine
    def docmd(self, cmd, args="", callback=None):
        """Send a command, and return its response code."""
        yield gen.Task(self.putcmd, cmd, args)
        self.getreply(callback)

    # std smtp commands
    @gen.engine
    def helo(self, name='', callback=None):
        """SMTP 'helo' command.
        Hostname to send for this command defaults to the FQDN of the local
        host.
        """
        yield gen.Task(self.putcmd, "helo", name or self.local_hostname)
        result = yield gen.Task(self.getreply)
        (code, msg) = result.args
        self.helo_resp = msg
        if callback:
            callback(code, msg)

    @gen.engine
    def ehlo(self, name='', callback=None):
        """ SMTP 'ehlo' command.
        Hostname to send for this command defaults to the FQDN of the local
        host.
        """
        self.esmtp_features = {}
        yield gen.Task(self.putcmd, self.ehlo_msg, name or self.local_hostname)
        result = yield gen.Task(self.getreply)
        (code, msg) = result.args
        # According to RFC1869 some (badly written)
        # MTA's will disconnect on an ehlo. Toss an exception if
        # that happens -ddm
        if code == -1 and len(msg) == 0:
            self.close()
            raise SMTPServerDisconnected("Server not connected")
        self.ehlo_resp=msg
        if code != 250:
            if callback:
                callback(code, msg)
            return
        self.does_esmtp=1
        #parse the ehlo response -ddm
        resp=self.ehlo_resp.split('\n')
        del resp[0]
        for each in resp:
            # To be able to communicate with as many SMTP servers as possible,
            # we have to take the old-style auth advertisement into account,
            # because:
            # 1) Else our SMTP feature parser gets confused.
            # 2) There are some servers that only advertise the auth methods we
            #    support using the old style.
            auth_match = OLDSTYLE_AUTH.match(each)
            if auth_match:
                # This doesn't remove duplicates, but that's no problem
                self.esmtp_features["auth"] = self.esmtp_features.get("auth", "") \
                        + " " + auth_match.groups(0)[0]
                continue

            # RFC 1869 requires a space between ehlo keyword and parameters.
            # It's actually stricter, in that only spaces are allowed between
            # parameters, but were not going to check for that here.  Note
            # that the space isn't present if there are no parameters.
            m=re.match(r'(?P<feature>[A-Za-z0-9][A-Za-z0-9\-]*) ?',each)
            if m:
                feature=m.group("feature").lower()
                params=m.string[m.end("feature"):].strip()
                if feature == "auth":
                    self.esmtp_features[feature] = self.esmtp_features.get(feature, "") \
                            + " " + params
                else:
                    self.esmtp_features[feature]=params
        if callback:
            callback(code, msg)

    def has_extn(self, opt):
        """Does the server support a given SMTP service extension?"""
        return opt.lower() in self.esmtp_features

    @gen.engine
    def help(self, args='', callback=None):
        """SMTP 'help' command.
        Returns help text from server."""
        yield self.putcmd("help", args)
        result = yield gen.Task(self.getreply)
        (code, msg) = result.args
        if callback:
            callback(msg)

    @gen.engine
    def rset(self, callback):
        """SMTP 'rset' command -- resets session."""
        result = yield gen.Task(self.docmd, "rset")
        callback(*result.args, **result.kwargs)

    @gen.engine
    def noop(self, callback):
        """SMTP 'noop' command -- doesn't do anything :>"""
        result = yield gen.Task(self.docmd, "noop")
        callback(*result.args, **result.kwargs)

    @gen.engine
    def mail(self, sender, options=[], callback=None):
        """SMTP 'mail' command -- begins mail xfer session."""
        optionlist = ''
        if options and self.does_esmtp:
            optionlist = ' ' + ' '.join(options)
        yield gen.Task(self.putcmd, "mail", "FROM:%s%s" % (quoteaddr(sender) ,optionlist))
        self.getreply(callback)

    @gen.engine
    def rcpt(self,recip,options=[], callback=None):
        """SMTP 'rcpt' command -- indicates 1 recipient for this mail."""
        optionlist = ''
        if options and self.does_esmtp:
            optionlist = ' ' + ' '.join(options)
        yield gen.Task(self.putcmd, "rcpt", "TO:%s%s" % (quoteaddr(recip),optionlist))
        self.getreply(callback)

    @gen.engine
    def data(self, msg, callback=None):
        """SMTP 'DATA' command -- sends message data to server.

        Automatically quotes lines beginning with a period per rfc821.
        Raises SMTPDataError if there is an unexpected reply to the
        DATA command; the return value from this method is the final
        response code received when the all data is sent.
        """
        yield gen.Task(self.putcmd, "data")
        result = yield gen.Task(self.getreply)
        (code, repl) = result.args
        if self.debuglevel >0 : print>>stderr, "data:", (code,repl)
        if code != 354:
            raise SMTPDataError(code,repl)
        else:
            q = quotedata(msg)
            if q[-2:] != CRLF:
                q = q + CRLF
            q = q + "." + CRLF
            yield gen.Task(self.send, q)
            result = yield gen.Task(self.getreply)
            (code, msg) = result.args
            if self.debuglevel >0 : print>>stderr, "data:", (code,msg)
            if callback:
                callback(code, msg)

    def verify(self, address, callback):
        """SMTP 'verify' command -- checks for address validity."""
        self.putcmd("vrfy", quoteaddr(address), partial(self.getreply, callback=callback))
    # a.k.a.
    vrfy=verify

    def expn(self, address, callback):
        """SMTP 'expn' command -- expands a mailing list."""
        self.putcmd("expn", quoteaddr(address), partial(self.getreply, callback=callback))

    # some useful methods

    @gen.engine
    def ehlo_or_helo_if_needed(self, callback):
        """Call self.ehlo() and/or self.helo() if needed.

        If there has been no previous EHLO or HELO command this session, this
        method tries ESMTP EHLO first.

        This method may raise the following exceptions:

         SMTPHeloError            The server didn't reply properly to
                                  the helo greeting.
        """
        if self.helo_resp is None and self.ehlo_resp is None:
            result = yield gen.Task(self.ehlo)
            code = result.args[0]
            if not (200 <= code <= 299):
                result = yield gen.Task(self.helo)
                (code, resp) = result.args
                if not (200 <= code <= 299):
                    raise SMTPHeloError(code, resp)
        callback()


    @gen.engine
    def login(self, user, password, callback=None):
        """Log in on an SMTP server that requires authentication.

        The arguments are:
            - user:     The user name to authenticate with.
            - password: The password for the authentication.

        If there has been no previous EHLO or HELO command this session, this
        method tries ESMTP EHLO first.

        This method will return normally if the authentication was successful.

        This method may raise the following exceptions:

         SMTPHeloError            The server didn't reply properly to
                                  the helo greeting.
         SMTPAuthenticationError  The server didn't accept the username/
                                  password combination.
         SMTPException            No suitable authentication method was
                                  found.
        """

        def encode_cram_md5(challenge, user, password):
            challenge = base64.decodestring(challenge)
            response = user + " " + hmac.HMAC(password, challenge).hexdigest()
            return encode_base64(response, eol="")

        def encode_plain(user, password):
            return encode_base64("\0%s\0%s" % (user, password), eol="")


        AUTH_PLAIN = "PLAIN"
        AUTH_CRAM_MD5 = "CRAM-MD5"
        AUTH_LOGIN = "LOGIN"

        yield gen.Task(self.ehlo_or_helo_if_needed)

        if not self.has_extn("auth"):
            raise SMTPException("SMTP AUTH extension not supported by server.")

        # Authentication methods the server supports:
        authlist = self.esmtp_features["auth"].split()

        # List of authentication methods we support: from preferred to
        # less preferred methods. Except for the purpose of testing the weaker
        # ones, we prefer stronger methods like CRAM-MD5:
        preferred_auths = [AUTH_CRAM_MD5, AUTH_PLAIN, AUTH_LOGIN]

        # Determine the authentication method we'll use
        authmethod = None
        for method in preferred_auths:
            if method in authlist:
                authmethod = method
                break

        if authmethod == AUTH_CRAM_MD5:
            result = yield gen.Task(self.docmd, "AUTH", AUTH_CRAM_MD5)
            (code, resp) = result.args
            if code == 503:
                # 503 == 'Error: already authenticated'
                if callback:
                    callback(code, resp)
            result = yield gen.Task(self.docmd, encode_cram_md5(resp, user, password))
            (code, resp) = result.args
        elif authmethod == AUTH_PLAIN:
            result = yield gen.Task(self.docmd, "AUTH",
                AUTH_PLAIN + " " + encode_plain(user, password)
            )
            (code, resp) = result.args
        elif authmethod == AUTH_LOGIN:
            result = yield gen.Task(self.docmd, "AUTH",
                "%s %s" % (AUTH_LOGIN, encode_base64(user, eol="")))
            (code, resp) = result.args
            if code != 334:
                raise SMTPAuthenticationError(code, resp)
            result = yield gen.Task(self.docmd, encode_base64(password, eol=""))
            (code, resp) = result.args
        elif authmethod is None:
            raise SMTPException("No suitable authentication method found.")
        if code not in (235, 503):
            # 235 == 'Authentication successful'
            # 503 == 'Error: already authenticated'
            raise SMTPAuthenticationError(code, resp)
        if callback:
            callback(code, resp)

    @gen.engine
    def starttls(self, keyfile=None, certfile=None, callback=None):
        """Puts the connection to the SMTP server into TLS mode.

        If there has been no previous EHLO or HELO command this session, this
        method tries ESMTP EHLO first.

        If the server supports TLS, this will encrypt the rest of the SMTP
        session. If you provide the keyfile and certfile parameters,
        the identity of the SMTP server and client can be checked. This,
        however, depends on whether the socket module really checks the
        certificates.

        This method may raise the following exceptions:

         SMTPHeloError            The server didn't reply properly to
                                  the helo greeting.
        """
        yield gen.Task(self.ehlo_or_helo_if_needed)
        if not self.has_extn("starttls"):
            raise SMTPException("STARTTLS extension not supported by server.")
        result = yield gen.Task(self.docmd, "STARTTLS")
        (resp, reply) = result.args
        if resp == 220:
            if not _have_ssl:
                raise RuntimeError("No SSL support included in this Python")
            self.sock = yield gen.Task(
                self._get_ssl_socket, self.sock,
                keyfile=keyfile, certfile=certfile
            )
            # RFC 3207:
            # The client MUST discard any knowledge obtained from
            # the server, such as the list of SMTP service extensions,
            # which was not obtained from the TLS negotiation itself.
            self.helo_resp = None
            self.ehlo_resp = None
            self.esmtp_features = {}
            self.does_esmtp = 0
        if callback:
            callback(resp, reply)

    @gen.engine
    def sendmail(self, from_addr, to_addrs, msg, mail_options=[],
                 rcpt_options=[], callback=None):
        """This command performs an entire mail transaction.

        The arguments are:
            - from_addr    : The address sending this mail.
            - to_addrs     : A list of addresses to send this mail to.  A bare
                             string will be treated as a list with 1 address.
            - msg          : The message to send.
            - mail_options : List of ESMTP options (such as 8bitmime) for the
                             mail command.
            - rcpt_options : List of ESMTP options (such as DSN commands) for
                             all the rcpt commands.

        If there has been no previous EHLO or HELO command this session, this
        method tries ESMTP EHLO first.  If the server does ESMTP, message size
        and each of the specified options will be passed to it.  If EHLO
        fails, HELO will be tried and ESMTP options suppressed.

        This method will return normally if the mail is accepted for at least
        one recipient.  It returns a dictionary, with one entry for each
        recipient that was refused.  Each entry contains a tuple of the SMTP
        error code and the accompanying error message sent by the server.

        This method may raise the following exceptions:

         SMTPHeloError          The server didn't reply properly to
                                the helo greeting.
         SMTPRecipientsRefused  The server rejected ALL recipients
                                (no mail was sent).
         SMTPSenderRefused      The server didn't accept the from_addr.
         SMTPDataError          The server replied with an unexpected
                                error code (other than a refusal of
                                a recipient).

        Note: the connection will be open even after an exception is raised.

        Example:

         >>> import smtplib
         >>> s=smtplib.SMTP("localhost")
         >>> tolist=["one@one.org","two@two.org","three@three.org","four@four.org"]
         >>> msg = '''\\
         ... From: Me@my.org
         ... Subject: testin'...
         ...
         ... This is a test '''
         >>> s.sendmail("me@my.org",tolist,msg)
         { "three@three.org" : ( 550 ,"User unknown" ) }
         >>> s.quit()

        In the above example, the message was accepted for delivery to three
        of the four addresses, and one was rejected, with the error code
        550.  If all addresses are accepted, then the method will return an
        empty dictionary.

        """
        yield gen.Task(self.ehlo_or_helo_if_needed)
        esmtp_opts = []
        if self.does_esmtp:
            # Hmmm? what's this? -ddm
            # self.esmtp_features['7bit']=""
            if self.has_extn('size'):
                esmtp_opts.append("size=%d" % len(msg))
            for option in mail_options:
                esmtp_opts.append(option)

        result = yield gen.Task(self.mail, from_addr, esmtp_opts)
        (code, resp) = result.args
        if code != 250:
            yield gen.Task(self.rset)
            raise SMTPSenderRefused(code, resp, from_addr)
        senderrs={}
        if isinstance(to_addrs, basestring):
            to_addrs = [to_addrs]
        for each in to_addrs:
            result = yield gen.Task(self.rcpt, each, rcpt_options)
            (code, resp) = result.args
            if (code != 250) and (code != 251):
                senderrs[each]=(code, resp)
        if len(senderrs)==len(to_addrs):
            # the server refused all our recipients
            yield gen.Task(self.rset)
            raise SMTPRecipientsRefused(senderrs)
        result = yield gen.Task(self.data, msg)
        (code, resp) = result.args
        if code != 250:
            yield gen.Task(self.rset)
            raise SMTPDataError(code, resp)
        #if we got here then somebody got our mail
        if callback:
            callback(senderrs)


    def close(self):
        """Close the connection to the SMTP server."""
        if self.sock:
            self.sock.close()
        self.sock = None

    @gen.engine
    def quit(self, callback=None):
        """Terminate the SMTP session."""
        res = yield gen.Task(self.docmd, "quit")
        self.close()
        if callback:
            callback(res)

# if _have_ssl:
# 
#     class SMTP_SSL(SMTP):
#         """ This is a subclass derived from SMTP that connects over an SSL encrypted
#         socket (to use this class you need a socket module that was compiled with SSL
#         support). If host is not specified, '' (the local host) is used. If port is
#         omitted, the standard SMTP-over-SSL port (465) is used. keyfile and certfile
#         are also optional - they can contain a PEM formatted private key and
#         certificate chain file for the SSL connection.
#         """
#         def __init__(self, host='', port=0, local_hostname=None,
#                      keyfile=None, certfile=None,
#                      timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
#             self.keyfile = keyfile
#             self.certfile = certfile
#             SMTP.__init__(self, host, port, local_hostname, timeout)
#             self.default_port = SMTP_SSL_PORT
# 
#         def _get_socket(self, host, port, timeout):
#             if self.debuglevel > 0: print>>stderr, 'connect:', (host, port)
#             new_socket = socket.create_connection((host, port), timeout)
#             new_socket = ssl.wrap_socket(new_socket, self.keyfile, self.certfile)
#             self.file = SSLFakeFile(new_socket)
#             return new_socket
# 
#     __all__.append("SMTP_SSL")
# 
# #
# # LMTP extension
# #
# LMTP_PORT = 2003
# 
# class LMTP(SMTP):
#     """LMTP - Local Mail Transfer Protocol
# 
#     The LMTP protocol, which is very similar to ESMTP, is heavily based
#     on the standard SMTP client. It's common to use Unix sockets for LMTP,
#     so our connect() method must support that as well as a regular
#     host:port server. To specify a Unix socket, you must use an absolute
#     path as the host, starting with a '/'.
# 
#     Authentication is supported, using the regular SMTP mechanism. When
#     using a Unix socket, LMTP generally don't support or require any
#     authentication, but your mileage might vary."""
# 
#     ehlo_msg = "lhlo"
# 
#     def __init__(self, host = '', port = LMTP_PORT, local_hostname = None):
#         """Initialize a new instance."""
#         SMTP.__init__(self, host, port, local_hostname)
# 
#     def connect(self, host = 'localhost', port = 0):
#         """Connect to the LMTP daemon, on either a Unix or a TCP socket."""
#         if host[0] != '/':
#             return SMTP.connect(self, host, port)
# 
#         # Handle Unix-domain sockets.
#         try:
#             self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
#             self.sock.connect(host)
#         except socket.error, msg:
#             if self.debuglevel > 0: print>>stderr, 'connect fail:', host
#             if self.sock:
#                 self.sock.close()
#             self.sock = None
#             raise socket.error, msg
#         (code, msg) = self.getreply()
#         if self.debuglevel > 0: print>>stderr, "connect:", msg
#         return (code, msg)

########NEW FILE########
__FILENAME__ = utils
"""
Email message and email sending related helper functions.
"""

import socket


# Cache the hostname, but do it lazily: socket.getfqdn() can take a couple of
# seconds, which slows down the restart of the server.
class CachedDnsName(object):
    def __str__(self):
        return self.get_fqdn()

    def get_fqdn(self):
        if not hasattr(self, '_fqdn'):
            self._fqdn = socket.getfqdn()
        return self._fqdn

DNS_NAME = CachedDnsName()

########NEW FILE########
