__FILENAME__ = ast
from __future__ import absolute_import

import sys
from ast import *

from .version_info import PY2

if PY2 or sys.version_info[1] <= 2:
    Try = TryExcept
else:
    TryFinally = ()

if PY2:
    def argument_names(node):
        return [isinstance(arg, Name) and arg.id or None for arg in node.args.args]

    def kw_only_argument_names(node):
        return []

    def kw_only_default_count(node):
        return 0
else:
    def argument_names(node):
        return [arg.arg for arg in node.args.args]

    def kw_only_argument_names(node):
        return [arg.arg for arg in node.args.kwonlyargs]

    def kw_only_default_count(node):
        return sum(1 for n in node.args.kw_defaults if n is not None)

########NEW FILE########
__FILENAME__ = collections
from __future__ import absolute_import

from collections import *

from .version_info import PY2

if PY2:
    from UserString import *
    from UserList import *

    import sys
    if sys.version_info < (2, 7):
        from ordereddict import OrderedDict

########NEW FILE########
__FILENAME__ = dumb
from __future__ import absolute_import

from ..version_info import PY3

if PY3:
    from dbm.dumb import *
else:
    from dumb import *

########NEW FILE########
__FILENAME__ = gnu
from __future__ import absolute_import

from ..version_info import PY3

if PY3:
    from dbm.gnu import *
else:
    from gdbm import *

########NEW FILE########
__FILENAME__ = ndbm
from __future__ import absolute_import

from ..version_info import PY3

if PY3:
    from dbm.ndbm import *
else:
    from dbm import *

########NEW FILE########
__FILENAME__ = functools
from __future__ import absolute_import

import sys
from functools import *

from .version_info import PY2

if PY2:
    reduce = reduce

if sys.version_info < (3, 2):
    try:
        from threading import Lock
    except ImportError:
        from dummy_threading import Lock

    from .collections import OrderedDict

    def lru_cache(maxsize=100):
        """Least-recently-used cache decorator.

        Taking from: https://github.com/MiCHiLU/python-functools32/blob/master/functools32/functools32.py
        with slight modifications.

        If *maxsize* is set to None, the LRU features are disabled and the cache
        can grow without bound.

        Arguments to the cached function must be hashable.

        View the cache statistics named tuple (hits, misses, maxsize, currsize) with
        f.cache_info().  Clear the cache and statistics with f.cache_clear().
        Access the underlying function with f.__wrapped__.

        See:  http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used
        
        """
        def decorating_function(user_function, tuple=tuple, sorted=sorted, len=len, KeyError=KeyError):
            hits, misses = [0], [0]
            kwd_mark = (object(),)          # separates positional and keyword args
            lock = Lock()

            if maxsize is None:
                CACHE = dict()

                @wraps(user_function)
                def wrapper(*args, **kwds):
                    key = args
                    if kwds:
                        key += kwd_mark + tuple(sorted(kwds.items()))
                    try:
                        result = CACHE[key]
                        hits[0] += 1
                        return result
                    except KeyError:
                        pass
                    result = user_function(*args, **kwds)
                    CACHE[key] = result
                    misses[0] += 1
                    return result
            else:
                CACHE = OrderedDict()

                @wraps(user_function)
                def wrapper(*args, **kwds):
                    key = args
                    if kwds:
                        key += kwd_mark + tuple(sorted(kwds.items()))
                    with lock:
                        cached = CACHE.get(key, None)
                        if cached:
                            del CACHE[key]
                            CACHE[key] = cached
                            hits[0] += 1
                            return cached
                    result = user_function(*args, **kwds)
                    with lock:
                        CACHE[key] = result     # record recent use of this key
                        misses[0] += 1
                        while len(CACHE) > maxsize:
                            CACHE.popitem(last=False)
                    return result

            def cache_info():
                """Report CACHE statistics."""
                with lock:
                    return _CacheInfo(hits[0], misses[0], maxsize, len(CACHE))

            def cache_clear():
                """Clear the CACHE and CACHE statistics."""
                with lock:
                    CACHE.clear()
                    hits[0] = misses[0] = 0

            wrapper.cache_info = cache_info
            wrapper.cache_clear = cache_clear
            return wrapper

        return decorating_function

########NEW FILE########
__FILENAME__ = client
from __future__ import absolute_import

from ..version_info import PY3

if PY3:
    from http.client import *
else:
    from httplib import *

########NEW FILE########
__FILENAME__ = cookies
from __future__ import absolute_import

from ..version_info import PY3

if PY3:
    from http.cookies import *
else:
    from Cookie import *

########NEW FILE########
__FILENAME__ = server
from __future__ import absolute_import

from ..version_info import PY3

if PY3:
    from http.server import *
else:
    from BaseHTTPServer import *
    from CGIHTTPServer import *
    from SimpleHTTPServer import *

########NEW FILE########
__FILENAME__ = imp
from __future__ import absolute_import

from imp import *

from .version_info import PY2

if PY2:
    reload = reload

########NEW FILE########
__FILENAME__ = itertools
from __future__ import absolute_import

from itertools import *

from .version_info import PY2

if PY2:
    filterfalse = ifilterfalse

########NEW FILE########
__FILENAME__ = overrides
"""pies/overrides.py.

Overrides Python syntax to conform to the Python3 version as much as possible using a '*' import

Copyright (C) 2013  Timothy Edmund Crosley

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

"""
from __future__ import absolute_import

import abc
import functools
import sys
from numbers import Integral

from ._utils import unmodified_isinstance, with_metaclass
from .version_info import PY2, PY3, VERSION

native_dict = dict
native_round = round
native_filter = filter
native_map = map
native_zip = zip
native_range = range
native_str = str
native_chr = chr
native_input = input
native_next = next
native_object = object

common = ['native_dict', 'native_round', 'native_filter', 'native_map', 'native_range', 'native_str', 'native_chr',
          'native_input', 'PY2', 'PY3', 'u', 'itemsview', 'valuesview', 'keysview', 'execute', 'integer_types',
          'native_next', 'native_object', 'with_metaclass']

if PY3:
    import urllib
    import builtins
    from urllib import parse

    from collections import OrderedDict

    integer_types = (int, )

    def u(string):
        return string

    def itemsview(collection):
        return collection.items()

    def valuesview(collection):
        return collection.values()

    def keysview(collection):
        return collection.keys()

    urllib.quote = parse.quote
    urllib.quote_plus = parse.quote_plus
    urllib.unquote = parse.unquote
    urllib.unquote_plus = parse.unquote_plus
    urllib.urlencode = parse.urlencode
    execute = getattr(builtins, 'exec')
    if VERSION[1] < 2:
        def callable(entity):
            return hasattr(entity, '__call__')
        common.append('callable')

    __all__ = common + ['OrderedDict', 'urllib']
else:
    from itertools import ifilter as filter
    from itertools import imap as map
    from itertools import izip as zip
    from decimal import Decimal, ROUND_HALF_EVEN


    try:
        from collections import OrderedDict
    except ImportError:
        from ordereddict import OrderedDict

    import codecs
    str = unicode
    chr = unichr
    input = raw_input
    range = xrange
    integer_types = (int, long)

    import sys
    reload(sys)
    sys.setdefaultencoding('utf-8')

    def _create_not_allowed(name):
        def _not_allow(*args, **kwargs):
            raise NameError("name '{0}' is not defined".format(name))
        _not_allow.__name__ = name
        return _not_allow

    for removed in ('apply', 'cmp', 'coerce', 'execfile', 'raw_input', 'unpacks'):
        globals()[removed] = _create_not_allowed(removed)

    def u(s):
        if isinstance(s, unicode):
            return s
        else:
            return unicode(s.replace(r'\\', r'\\\\'), "unicode_escape")

    def execute(_code_, _globs_=None, _locs_=None):
        """Execute code in a namespace."""
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec("""exec _code_ in _globs_, _locs_""")

    class _dict_view_base(object):
        __slots__ = ('_dictionary', )

        def __init__(self, dictionary):
            self._dictionary = dictionary

        def __repr__(self):
            return "{0}({1})".format(self.__class__.__name__, str(list(self.__iter__())))

        def __unicode__(self):
            return str(self.__repr__())

        def __str__(self):
            return str(self.__unicode__())

    class dict_keys(_dict_view_base):
        __slots__ = ()

        def __iter__(self):
            return self._dictionary.iterkeys()

    class dict_values(_dict_view_base):
        __slots__ = ()

        def __iter__(self):
            return self._dictionary.itervalues()

    class dict_items(_dict_view_base):
        __slots__ = ()

        def __iter__(self):
            return self._dictionary.iteritems()

    def itemsview(collection):
        return dict_items(collection)

    def valuesview(collection):
        return dict_values(collection)

    def keysview(collection):
        return dict_keys(collection)

    class dict(unmodified_isinstance(native_dict)):
        def has_key(self, *args, **kwargs):
            return AttributeError("'dict' object has no attribute 'has_key'")

        def items(self):
            return dict_items(self)

        def keys(self):
            return dict_keys(self)

        def values(self):
            return dict_values(self)

    def round(number, ndigits=None):
        return_int = False
        if ndigits is None:
            return_int = True
            ndigits = 0
        if hasattr(number, '__round__'):
            return number.__round__(ndigits)

        if ndigits < 0:
            raise NotImplementedError('negative ndigits not supported yet')
        exponent = Decimal('10') ** (-ndigits)
        d = Decimal.from_float(number).quantize(exponent,
                                                rounding=ROUND_HALF_EVEN)
        if return_int:
            return int(d)
        else:
            return float(d)

    def next(iterator):
        try:
            iterator.__next__()
        except Exception:
            native_next(iterator)

    class FixStr(type):
        def __new__(cls, name, bases, dct):
            if '__str__' in dct:
                dct['__unicode__'] = dct['__str__']
            dct['__str__'] = lambda self: self.__unicode__().encode('utf-8')
            return type.__new__(cls, name, bases, dct)

        if sys.version_info[1] <= 6:
            def __instancecheck__(cls, instance):
                if cls.__name__ == "object":
                    return isinstance(instance, native_object)

                subclass = getattr(instance, '__class__', None)
                subtype = type(instance)
                instance_type = getattr(abc, '_InstanceType', None)
                if not instance_type:
                    class test_object:
                        pass
                    instance_type = type(test_object)
                if subtype is instance_type:
                    subtype = subclass
                if subtype is subclass or subclass is None:
                    return cls.__subclasscheck__(subtype)
                return (cls.__subclasscheck__(subclass) or cls.__subclasscheck__(subtype))
        else:
            def __instancecheck__(cls, instance):
                if cls.__name__ == "object":
                    return isinstance(instance, native_object)
                return type.__instancecheck__(cls, instance)

    class object(with_metaclass(FixStr, object)):
        pass

    __all__ = common + ['round', 'dict', 'apply', 'cmp', 'coerce', 'execfile', 'raw_input', 'unpacks', 'str', 'chr',
                        'input', 'range', 'filter', 'map', 'zip', 'object']

########NEW FILE########
__FILENAME__ = pickle
from __future__ import absolute_import

from .version_info import PY3

if PY3:
    from pickle import *
else:
    try:
        from cPickle import *
    except ImportError:
        from pickle import *

########NEW FILE########
__FILENAME__ = StringIO
from __future__ import absolute_import

from .version_info import PY3

if PY3:
    from io.StringIO import *
else:
    try:
        from cStringIO import *
    except ImportError:
        from StringIO import *

########NEW FILE########
__FILENAME__ = sys
from __future__ import absolute_import

from sys import *

if version_info[0] == 2:
    intern = intern

########NEW FILE########
__FILENAME__ = unittest
from __future__ import absolute_import

import sys
from unittest import *

from ._utils import unmodified_isinstance

NativeTestCase = TestCase

if sys.version_info < (2, 7):
    skip = lambda why: (lambda func: 'skip')
    skipIf = lambda cond, why: (skip(why) if cond else lambda func: func)

    class TestCase(unmodified_isinstance(TestCase)):
        def assertIs(self, expr1, expr2, msg=None):
            if expr1 is not expr2:
                self.fail(msg or '%r is not %r' % (expr1, expr2))

########NEW FILE########
__FILENAME__ = error
from __future__ import absolute_import

from ..version_info import PY3

if PY3:
    from urllib.error import *
else:
    from urllib import ContentTooShortError
    from urllib2 import HTTPError, URLError

########NEW FILE########
__FILENAME__ = parse
from __future__ import absolute_import

from ..version_info import PY3

if PY3:
    from urllib.parse import *
else:
    from urllib import quote, unquote, quote_plus, unquote_plus, urlencode

########NEW FILE########
__FILENAME__ = request
from __future__ import absolute_import

from ..version_info import PY3

if PY3:
    from urllib.request import *
else:
    from urllib import FancyURLopener, getproxies, pathname2url, url2pathname, urlcleanup, URLopener, urlretrieve
    from urllib2 import (AbstractBasicAuthHandler, AbstractDigestAuthHandler, BaseHandler, build_opener,
                         CacheFTPHandler, FileHandler, FTPHandler, HTTPBasicAuthHandler, HTTPCookieProcessor,
                         HTTPDefaultErrorHandler, HTTPDigestAuthHandler, HTTPHandler, HTTPPasswordMgr,
                         HTTPPasswordMgrWithDefaultRealm, HTTPRedirectHandler, HTTPSHandler, install_opener,
                         OpenerDirector, ProxyBasicAuthHandler, ProxyDigestAuthHandler, ProxyHandler, Request,
                         UnknownHandler, urlopen)

########NEW FILE########
__FILENAME__ = robotparser
from __future__ import absolute_import

from ..version_info import PY3

if PY3:
    from urllib.parse import *
else:
    from robotparser import *

########NEW FILE########
__FILENAME__ = version_info
from __future__ import absolute_import

import sys

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
VERSION = sys.version_info

########NEW FILE########
__FILENAME__ = _utils
"""pies/_utils.py.

Utils internal to the pies library and not meant for direct external usage.

Copyright (C) 2013  Timothy Edmund Crosley

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

"""
import abc
import sys


def with_metaclass(meta, *bases):
    """Enables use of meta classes across Python Versions. taken from jinja2/_compat.py.

    Use it like this::

        class BaseForm(object):
            pass

        class FormType(type):
            pass

        class Form(with_metaclass(FormType, BaseForm)):
            pass

    """
    class metaclass(meta):
        __call__ = type.__call__
        __init__ = type.__init__
        def __new__(cls, name, this_bases, d):
            if this_bases is None:
                return type.__new__(cls, name, (), d)
            return meta(name, bases, d)
    return metaclass('temporary_class', None, {})


def unmodified_isinstance(*bases):
    """When called in the form

    MyOverrideClass(unmodified_isinstance(BuiltInClass))

    it allows calls against passed in built in instances to pass even if there not a subclass

    """
    class UnmodifiedIsInstance(type):
        if sys.version_info[0] == 2 and sys.version_info[1] <= 6:

            @classmethod
            def __instancecheck__(cls, instance):
                if cls.__name__ in (str(base.__name__) for base in bases):
                    return isinstance(instance, bases)

                subclass = getattr(instance, '__class__', None)
                subtype = type(instance)
                instance_type = getattr(abc, '_InstanceType', None)
                if not instance_type:
                    class test_object:
                        pass
                    instance_type = type(test_object)
                if subtype is instance_type:
                    subtype = subclass
                if subtype is subclass or subclass is None:
                    return cls.__subclasscheck__(subtype)
                return (cls.__subclasscheck__(subclass) or cls.__subclasscheck__(subtype))
        else:
            @classmethod
            def __instancecheck__(cls, instance):
                if cls.__name__ in (str(base.__name__) for base in bases):
                    return isinstance(instance, bases)

                return type.__instancecheck__(cls, instance)

    return with_metaclass(UnmodifiedIsInstance, *bases)


########NEW FILE########
__FILENAME__ = builtins
from __future__ import absolute_import

from __builtin__ import *

########NEW FILE########
__FILENAME__ = configparser
from __future__ import absolute_import

from ConfigParser import *

########NEW FILE########
__FILENAME__ = copyreg
from __future__ import absolute_import

from copy_reg import *

########NEW FILE########
__FILENAME__ = entities
from __future__ import absolute_import

from htmlentitydefs import *

########NEW FILE########
__FILENAME__ = parser
from __future__ import absolute_import

from HTMLParser import *

########NEW FILE########
__FILENAME__ = client
from __future__ import absolute_import

from httplib import *

########NEW FILE########
__FILENAME__ = cookiejar
from __future__ import absolute_import

from cookielib import *

########NEW FILE########
__FILENAME__ = cookies
from __future__ import absolute_import

from Cookie import *

########NEW FILE########
__FILENAME__ = server
from __future__ import absolute_import

from BaseHTTPServer import *
from CGIHTTPServer import *
from SimpleHTTPServer import *

########NEW FILE########
__FILENAME__ = queue
from __future__ import absolute_import

from Queue import *

########NEW FILE########
__FILENAME__ = reprlib
from __future__ import absolute_import

from repr import *

########NEW FILE########
__FILENAME__ = socketserver
from __future__ import absolute_import

from SocketServer import *

########NEW FILE########
__FILENAME__ = client
from __future__ import absolute_import

from xmlrpclib import *

########NEW FILE########
__FILENAME__ = _thread
from __future__ import absolute_import

from _thread import *

########NEW FILE########
__FILENAME__ = tests
from __future__ import absolute_import, division, print_function, unicode_literals

from pies.overrides import *


def test_u():
    assert u('Bj\xf6rk Gu\xf0mundsd\xf3ttir') == 'Bj\xf6rk Gu\xf0mundsd\xf3ttir'

########NEW FILE########
__FILENAME__ = test_pies
from __future__ import absolute_import, division, print_function, unicode_literals

from pies.overrides import *


def test_u():
    assert u('Bj\xf6rk Gu\xf0mundsd\xf3ttir') == 'Bj\xf6rk Gu\xf0mundsd\xf3ttir'

########NEW FILE########
