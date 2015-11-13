__FILENAME__ = test_standard
import sys
import unittest


sys.path.append('../')


from unstdlib.standard.collections_ import RecentlyUsedContainer
from unstdlib.standard.exception_ import convert_exception


class TestRecentlyUsedContainer(unittest.TestCase):
    def test_maxsize(self):
        d = RecentlyUsedContainer(5)

        for i in range(5):
            d[i] = str(i)

        self.assertEqual(len(d), 5)

        for i in range(5):
            self.assertEqual(d[i], str(i))

        d[i+1] = str(i+1)

        self.assertEqual(len(d), 5)
        self.assertFalse(0 in d)
        self.assertTrue(i+1 in d)


class TestException_(unittest.TestCase):

    def test_convert_exception(self):

        class FooError(Exception):
            pass

        class BarError(Exception):
            def __init__(self, message):
                self.message = message

        @convert_exception(FooError, BarError, message='bar')
        def throw_foo():
            raise FooError('foo')

        try:
            throw_foo()
        except BarError as e:
            self.assertEqual(e.message, 'bar')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = formencode
def validate(d, key, validator):
    """
    Validate a single value in ``d`` using a formencode validator.

    Example::

        email = validate(request.params, 'email', validators.Email(not_empty=True))
    """
    return validator.to_python(d.get(key))


def validate_many(d, schema):
    """Validate a dictionary of data against the provided schema.

    Returns a list of values positioned in the same order as given in ``schema``, each
    value is validated with the corresponding validator. Raises formencode.Invalid if
    validation failed.

    Similar to get_many but using formencode validation.

    :param d: A dictionary of data to read values from.
    :param schema: A list of (key, validator) tuples. The key will be used to fetch
        a value from ``d`` and the validator will be applied to it.

    Example::

        from formencode import validators

        email, password, password_confirm = validate_many(request.params, [
            ('email', validators.Email(not_empty=True)),
            ('password', validators.String(min=4)),
            ('password_confirm', validators.String(min=4)),
        ])
    """
    return [validator.to_python(d.get(key), state=key) for key,validator in schema]

########NEW FILE########
__FILENAME__ = html
import os.path
import hashlib
import time

from unstdlib.standard.functools_ import memoized
from unstdlib.standard.list_ import iterate_items

try:
    import markupsafe
    MarkupType = markupsafe.Markup
except ImportError:
    MarkupType = unicode



__all__ = [
    'get_cache_buster', 'literal', 'tag', 'javascript_link', 'stylesheet_link',
]


@memoized
def _cache_key_by_md5(src_path, chunk_size=65536):
    hash = hashlib.md5()
    with open(src_path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), ''):
            hash.update(chunk)
    return hash.hexdigest()


@memoized
def _cache_key_by_mtime(src_path):
    return str(int(os.path.getmtime(src_path)))


_IMPORT_TIME = str(int(time.time()))

_BUST_METHODS = {
    'mtime': _cache_key_by_mtime,
    'md5': _cache_key_by_md5,
    'importtime': lambda src_path: _IMPORT_TIME,
}


def get_cache_buster(src_path, method='importtime'):
    """ Return a string that can be used as a parameter for cache-busting URLs
    for this asset.

    :param src_path:
        Filesystem path to the file we're generating a cache-busting value for.

    :param method:
        Method for cache-busting. Supported values: importtime, mtime, md5
        The default is 'importtime', because it requires the least processing.

    Note that the mtime and md5 cache busting methods' results are cached on
    the src_path.

    Example::

        >>> SRC_PATH = os.path.join(os.path.dirname(__file__), 'html.py')
        >>> get_cache_buster(SRC_PATH) is _IMPORT_TIME
        True
        >>> get_cache_buster(SRC_PATH, method='mtime') == _cache_key_by_mtime(SRC_PATH)
        True
        >>> get_cache_buster(SRC_PATH, method='md5') == _cache_key_by_md5(SRC_PATH)
        True
    """
    try:
        fn = _BUST_METHODS[method]
    except KeyError:
        raise KeyError('Unsupported busting method value: %s' % method)

    return fn(src_path)


def _generate_dom_attrs(attrs, allow_no_value=True):
    """ Yield compiled DOM attribute key-value strings.

    If the value is `True`, then it is treated as no-value."""
    for attr in iterate_items(attrs):
        if isinstance(attr, basestring):
            attr = (attr, True)
        key, value = attr
        if value is True and not allow_no_value:
            value = key  # E.g. <option checked="true" />
        if value is True:
            yield True  # E.g. <option checked />
        else:
            yield '%s="%s"' % (key, value.replace('"', '\\"'))


class literal(MarkupType):
    """ Wrapper type which represents an HTML literal that does not need to be
    escaped. Will use `MarkupSafe` if available, otherwise it's a dumb
    unicode-like object.
    """
    def __html__(self):
        return self


def tag(tagname, content='', attrs=None):
    """ Helper for programmatically building HTML tags.

    Note that this barely does any escaping, and will happily spit out
    dangerous user input if used as such.

    :param tagname:
        Tag name of the DOM element we want to return.

    :param content:
        Optional content of the DOM element. If `None`, then the element is
        self-closed. By default, the content is an empty string.

    :param attrs:
        Optional dictionary-like collection of attributes for the DOM element.

    Example::

        >>> tag('div', content='Hello, world.')
        u'<div>Hello, world.</div>'
        >>> tag('script', attrs={'src': '/static/js/core.js'})
        u'<script src="/static/js/core.js"></script>'
        >>> tag('script', attrs=[('src', '/static/js/core.js'), ('type', 'text/javascript')])
        u'<script src="/static/js/core.js" type="text/javascript"></script>'
        >>> tag('meta', content=None, attrs=dict(content='"quotedquotes"'))
        u'<meta content="\\\\"quotedquotes\\\\"" />'
    """
    attrs_str = attrs and ' '.join(_generate_dom_attrs(attrs))
    open_tag = tagname
    if attrs_str:
        open_tag += ' ' + attrs_str
    if content or isinstance(content, basestring):
        return literal('<%s>%s</%s>' % (open_tag, content, tagname))
    return literal('<%s />' % open_tag)


def javascript_link(src_url, src_path=None, cache_bust=None, content='', extra_attrs=None):
    """ Helper for programmatically building HTML JavaScript source include
    links, with optional cache busting.

    :param src_url:
        Goes into the `src` attribute of the `<script src="...">` tag.

    :param src_path:
        Optional filesystem path to the source file, used when `cache_bust` is
        enabled.

    :param content:
        Optional content of the DOM element. If `None`, then the element is
        self-closed.

    :param cache_bust:
        Optional method to use for cache busting. Can be one of: importtime,
        md5, or mtime. If the value is md5 or mtime, then `src_path` must be
        supplied.


    Example::

        >>> javascript_link('/static/js/core.js')
        u'<script src="/static/js/core.js" type="text/javascript"></script>'
    """
    if cache_bust:
        append_suffix = get_cache_buster(src_path=src_path, method=cache_bust)
        delim = '&' if '?' in src_url else '?'
        src_url += delim + append_suffix

    attrs = {
        'src': src_url,
        'type': 'text/javascript',
    }
    if extra_attrs:
        attrs.update(extra_attrs)

    return tag('script', content=content, attrs=attrs)


def stylesheet_link(src_url, src_path=None, cache_bust=None, content='', extra_attrs=None):
    """ Helper for programmatically building HTML StyleSheet source include
    links, with optional cache busting.

    :param src_url:
        Goes into the `src` attribute of the `<link src="...">` tag.

    :param src_path:
        Optional filesystem path to the source file, used when `cache_bust` is
        enabled.

    :param content:
        Optional content of the DOM element. If `None`, then the element is
        self-closed.

    :param cache_bust:
        Optional method to use for cache busting. Can be one of: importtime,
        md5, or mtime. If the value is md5 or mtime, then `src_path` must be
        supplied.


    Example::

        >>> stylesheet_link('/static/css/media.css')
        u'<link href="/static/css/media.css" rel="stylesheet"></link>'
    """
    if cache_bust:
        append_suffix = get_cache_buster(src_path=src_path, method=cache_bust)
        delim = '&' if '?' in src_url else '?'
        src_url += delim + append_suffix

    attrs = {
        'href': src_url,
        'rel': 'stylesheet',
    }
    if extra_attrs:
        attrs.update(extra_attrs)

    return tag('link', content=content, attrs=attrs)


### Backwards compatibility (will be removed in v1.6):
__all__ += ['html_tag', 'html_javascript_link', 'html_stylesheet_link']

import warnings

def html_tag(*args, **kw):
    '''
    This function has been renamed to `tag`. Use that instead.
    Backwards-compatibility will be removed in v1.6.
    '''
    warnings.warn("Renamed to `tag`", DeprecationWarning)
    return tag(*args, **kw)


def html_javascript_link(*args, **kw):
    '''
    This function has been renamed to `javascript_link`. Use that instead.
    Backwards-compatibility will be removed in v1.6.
    '''
    warnings.warn("Renamed to `javascript_link`", DeprecationWarning)
    return javascript_link(*args, **kw)


def html_stylesheet_link(*args, **kw):
    '''
    This function has been renamed to `stylesheet_link`. Use that instead.
    Backwards-compatibility will be removed in v1.6.
    '''
    warnings.warn("Renamed to `stylesheet_link`", DeprecationWarning)
    return stylesheet_link(*args, **kw)


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)

########NEW FILE########
__FILENAME__ = six
"""Utilities for writing code that runs on Python 2 and 3"""

# Copyright (c) 2010-2013 Benjamin Peterson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import operator
import sys
import types

__author__ = "Benjamin Peterson <benjamin@python.org>"
__version__ = "1.4.1"


# Useful for very coarse version differentiation.
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str

    if sys.platform.startswith("java"):
        # Jython always uses 32 bits.
        MAXSIZE = int((1 << 31) - 1)
    else:
        # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
        class X(object):
            def __len__(self):
                return 1 << 31
        try:
            len(X())
        except OverflowError:
            # 32-bit
            MAXSIZE = int((1 << 31) - 1)
        else:
            # 64-bit
            MAXSIZE = int((1 << 63) - 1)
        del X


def _add_doc(func, doc):
    """Add documentation to a function."""
    func.__doc__ = doc


def _import_module(name):
    """Import module, returning the module after the last dot."""
    __import__(name)
    return sys.modules[name]


class _LazyDescr(object):

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, tp):
        result = self._resolve()
        setattr(obj, self.name, result)
        # This is a bit ugly, but it avoids running this again.
        delattr(tp, self.name)
        return result


class MovedModule(_LazyDescr):

    def __init__(self, name, old, new=None):
        super(MovedModule, self).__init__(name)
        if PY3:
            if new is None:
                new = name
            self.mod = new
        else:
            self.mod = old

    def _resolve(self):
        return _import_module(self.mod)


class MovedAttribute(_LazyDescr):

    def __init__(self, name, old_mod, new_mod, old_attr=None, new_attr=None):
        super(MovedAttribute, self).__init__(name)
        if PY3:
            if new_mod is None:
                new_mod = name
            self.mod = new_mod
            if new_attr is None:
                if old_attr is None:
                    new_attr = name
                else:
                    new_attr = old_attr
            self.attr = new_attr
        else:
            self.mod = old_mod
            if old_attr is None:
                old_attr = name
            self.attr = old_attr

    def _resolve(self):
        module = _import_module(self.mod)
        return getattr(module, self.attr)



class _MovedItems(types.ModuleType):
    """Lazy loading of moved objects"""


_moved_attributes = [
    MovedAttribute("cStringIO", "cStringIO", "io", "StringIO"),
    MovedAttribute("filter", "itertools", "builtins", "ifilter", "filter"),
    MovedAttribute("filterfalse", "itertools", "itertools", "ifilterfalse", "filterfalse"),
    MovedAttribute("input", "__builtin__", "builtins", "raw_input", "input"),
    MovedAttribute("map", "itertools", "builtins", "imap", "map"),
    MovedAttribute("range", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("reload_module", "__builtin__", "imp", "reload"),
    MovedAttribute("reduce", "__builtin__", "functools"),
    MovedAttribute("StringIO", "StringIO", "io"),
    MovedAttribute("UserString", "UserString", "collections"),
    MovedAttribute("xrange", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("zip", "itertools", "builtins", "izip", "zip"),
    MovedAttribute("zip_longest", "itertools", "itertools", "izip_longest", "zip_longest"),

    MovedModule("builtins", "__builtin__"),
    MovedModule("configparser", "ConfigParser"),
    MovedModule("copyreg", "copy_reg"),
    MovedModule("http_cookiejar", "cookielib", "http.cookiejar"),
    MovedModule("http_cookies", "Cookie", "http.cookies"),
    MovedModule("html_entities", "htmlentitydefs", "html.entities"),
    MovedModule("html_parser", "HTMLParser", "html.parser"),
    MovedModule("http_client", "httplib", "http.client"),
    MovedModule("email_mime_multipart", "email.MIMEMultipart", "email.mime.multipart"),
    MovedModule("email_mime_text", "email.MIMEText", "email.mime.text"),
    MovedModule("email_mime_base", "email.MIMEBase", "email.mime.base"),
    MovedModule("BaseHTTPServer", "BaseHTTPServer", "http.server"),
    MovedModule("CGIHTTPServer", "CGIHTTPServer", "http.server"),
    MovedModule("SimpleHTTPServer", "SimpleHTTPServer", "http.server"),
    MovedModule("cPickle", "cPickle", "pickle"),
    MovedModule("queue", "Queue"),
    MovedModule("reprlib", "repr"),
    MovedModule("socketserver", "SocketServer"),
    MovedModule("tkinter", "Tkinter"),
    MovedModule("tkinter_dialog", "Dialog", "tkinter.dialog"),
    MovedModule("tkinter_filedialog", "FileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_scrolledtext", "ScrolledText", "tkinter.scrolledtext"),
    MovedModule("tkinter_simpledialog", "SimpleDialog", "tkinter.simpledialog"),
    MovedModule("tkinter_tix", "Tix", "tkinter.tix"),
    MovedModule("tkinter_constants", "Tkconstants", "tkinter.constants"),
    MovedModule("tkinter_dnd", "Tkdnd", "tkinter.dnd"),
    MovedModule("tkinter_colorchooser", "tkColorChooser",
                "tkinter.colorchooser"),
    MovedModule("tkinter_commondialog", "tkCommonDialog",
                "tkinter.commondialog"),
    MovedModule("tkinter_tkfiledialog", "tkFileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_font", "tkFont", "tkinter.font"),
    MovedModule("tkinter_messagebox", "tkMessageBox", "tkinter.messagebox"),
    MovedModule("tkinter_tksimpledialog", "tkSimpleDialog",
                "tkinter.simpledialog"),
    MovedModule("urllib_parse", __name__ + ".moves.urllib_parse", "urllib.parse"),
    MovedModule("urllib_error", __name__ + ".moves.urllib_error", "urllib.error"),
    MovedModule("urllib", __name__ + ".moves.urllib", __name__ + ".moves.urllib"),
    MovedModule("urllib_robotparser", "robotparser", "urllib.robotparser"),
    MovedModule("winreg", "_winreg"),
]
for attr in _moved_attributes:
    setattr(_MovedItems, attr.name, attr)
del attr

moves = sys.modules[__name__ + ".moves"] = _MovedItems(__name__ + ".moves")



class Module_six_moves_urllib_parse(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_parse"""


_urllib_parse_moved_attributes = [
    MovedAttribute("ParseResult", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qs", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qsl", "urlparse", "urllib.parse"),
    MovedAttribute("urldefrag", "urlparse", "urllib.parse"),
    MovedAttribute("urljoin", "urlparse", "urllib.parse"),
    MovedAttribute("urlparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlsplit", "urlparse", "urllib.parse"),
    MovedAttribute("urlunparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlunsplit", "urlparse", "urllib.parse"),
    MovedAttribute("quote", "urllib", "urllib.parse"),
    MovedAttribute("quote_plus", "urllib", "urllib.parse"),
    MovedAttribute("unquote", "urllib", "urllib.parse"),
    MovedAttribute("unquote_plus", "urllib", "urllib.parse"),
    MovedAttribute("urlencode", "urllib", "urllib.parse"),
]
for attr in _urllib_parse_moved_attributes:
    setattr(Module_six_moves_urllib_parse, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_parse"] = Module_six_moves_urllib_parse(__name__ + ".moves.urllib_parse")
sys.modules[__name__ + ".moves.urllib.parse"] = Module_six_moves_urllib_parse(__name__ + ".moves.urllib.parse")


class Module_six_moves_urllib_error(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_error"""


_urllib_error_moved_attributes = [
    MovedAttribute("URLError", "urllib2", "urllib.error"),
    MovedAttribute("HTTPError", "urllib2", "urllib.error"),
    MovedAttribute("ContentTooShortError", "urllib", "urllib.error"),
]
for attr in _urllib_error_moved_attributes:
    setattr(Module_six_moves_urllib_error, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_error"] = Module_six_moves_urllib_error(__name__ + ".moves.urllib_error")
sys.modules[__name__ + ".moves.urllib.error"] = Module_six_moves_urllib_error(__name__ + ".moves.urllib.error")


class Module_six_moves_urllib_request(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_request"""


_urllib_request_moved_attributes = [
    MovedAttribute("urlopen", "urllib2", "urllib.request"),
    MovedAttribute("install_opener", "urllib2", "urllib.request"),
    MovedAttribute("build_opener", "urllib2", "urllib.request"),
    MovedAttribute("pathname2url", "urllib", "urllib.request"),
    MovedAttribute("url2pathname", "urllib", "urllib.request"),
    MovedAttribute("getproxies", "urllib", "urllib.request"),
    MovedAttribute("Request", "urllib2", "urllib.request"),
    MovedAttribute("OpenerDirector", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDefaultErrorHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPRedirectHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPCookieProcessor", "urllib2", "urllib.request"),
    MovedAttribute("ProxyHandler", "urllib2", "urllib.request"),
    MovedAttribute("BaseHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgr", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgrWithDefaultRealm", "urllib2", "urllib.request"),
    MovedAttribute("AbstractBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("AbstractDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPSHandler", "urllib2", "urllib.request"),
    MovedAttribute("FileHandler", "urllib2", "urllib.request"),
    MovedAttribute("FTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("CacheFTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("UnknownHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPErrorProcessor", "urllib2", "urllib.request"),
    MovedAttribute("urlretrieve", "urllib", "urllib.request"),
    MovedAttribute("urlcleanup", "urllib", "urllib.request"),
    MovedAttribute("URLopener", "urllib", "urllib.request"),
    MovedAttribute("FancyURLopener", "urllib", "urllib.request"),
]
for attr in _urllib_request_moved_attributes:
    setattr(Module_six_moves_urllib_request, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_request"] = Module_six_moves_urllib_request(__name__ + ".moves.urllib_request")
sys.modules[__name__ + ".moves.urllib.request"] = Module_six_moves_urllib_request(__name__ + ".moves.urllib.request")


class Module_six_moves_urllib_response(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_response"""


_urllib_response_moved_attributes = [
    MovedAttribute("addbase", "urllib", "urllib.response"),
    MovedAttribute("addclosehook", "urllib", "urllib.response"),
    MovedAttribute("addinfo", "urllib", "urllib.response"),
    MovedAttribute("addinfourl", "urllib", "urllib.response"),
]
for attr in _urllib_response_moved_attributes:
    setattr(Module_six_moves_urllib_response, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_response"] = Module_six_moves_urllib_response(__name__ + ".moves.urllib_response")
sys.modules[__name__ + ".moves.urllib.response"] = Module_six_moves_urllib_response(__name__ + ".moves.urllib.response")


class Module_six_moves_urllib_robotparser(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_robotparser"""


_urllib_robotparser_moved_attributes = [
    MovedAttribute("RobotFileParser", "robotparser", "urllib.robotparser"),
]
for attr in _urllib_robotparser_moved_attributes:
    setattr(Module_six_moves_urllib_robotparser, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_robotparser"] = Module_six_moves_urllib_robotparser(__name__ + ".moves.urllib_robotparser")
sys.modules[__name__ + ".moves.urllib.robotparser"] = Module_six_moves_urllib_robotparser(__name__ + ".moves.urllib.robotparser")


class Module_six_moves_urllib(types.ModuleType):
    """Create a six.moves.urllib namespace that resembles the Python 3 namespace"""
    parse = sys.modules[__name__ + ".moves.urllib_parse"]
    error = sys.modules[__name__ + ".moves.urllib_error"]
    request = sys.modules[__name__ + ".moves.urllib_request"]
    response = sys.modules[__name__ + ".moves.urllib_response"]
    robotparser = sys.modules[__name__ + ".moves.urllib_robotparser"]


sys.modules[__name__ + ".moves.urllib"] = Module_six_moves_urllib(__name__ + ".moves.urllib")


def add_move(move):
    """Add an item to six.moves."""
    setattr(_MovedItems, move.name, move)


def remove_move(name):
    """Remove item from six.moves."""
    try:
        delattr(_MovedItems, name)
    except AttributeError:
        try:
            del moves.__dict__[name]
        except KeyError:
            raise AttributeError("no such move, %r" % (name,))


if PY3:
    _meth_func = "__func__"
    _meth_self = "__self__"

    _func_closure = "__closure__"
    _func_code = "__code__"
    _func_defaults = "__defaults__"
    _func_globals = "__globals__"

    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"
    _iterlists = "lists"
else:
    _meth_func = "im_func"
    _meth_self = "im_self"

    _func_closure = "func_closure"
    _func_code = "func_code"
    _func_defaults = "func_defaults"
    _func_globals = "func_globals"

    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"
    _iterlists = "iterlists"


try:
    advance_iterator = next
except NameError:
    def advance_iterator(it):
        return it.next()
next = advance_iterator


try:
    callable = callable
except NameError:
    def callable(obj):
        return any("__call__" in klass.__dict__ for klass in type(obj).__mro__)


if PY3:
    def get_unbound_function(unbound):
        return unbound

    create_bound_method = types.MethodType

    Iterator = object
else:
    def get_unbound_function(unbound):
        return unbound.im_func

    def create_bound_method(func, obj):
        return types.MethodType(func, obj, obj.__class__)

    class Iterator(object):

        def next(self):
            return type(self).__next__(self)

    callable = callable
_add_doc(get_unbound_function,
         """Get the function out of a possibly unbound function""")


get_method_function = operator.attrgetter(_meth_func)
get_method_self = operator.attrgetter(_meth_self)
get_function_closure = operator.attrgetter(_func_closure)
get_function_code = operator.attrgetter(_func_code)
get_function_defaults = operator.attrgetter(_func_defaults)
get_function_globals = operator.attrgetter(_func_globals)


def iterkeys(d, **kw):
    """Return an iterator over the keys of a dictionary."""
    return iter(getattr(d, _iterkeys)(**kw))

def itervalues(d, **kw):
    """Return an iterator over the values of a dictionary."""
    return iter(getattr(d, _itervalues)(**kw))

def iteritems(d, **kw):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)(**kw))

def iterlists(d, **kw):
    """Return an iterator over the (key, [values]) pairs of a dictionary."""
    return iter(getattr(d, _iterlists)(**kw))


if PY3:
    def b(s):
        return s.encode("latin-1")
    def u(s):
        return s
    unichr = chr
    if sys.version_info[1] <= 1:
        def int2byte(i):
            return bytes((i,))
    else:
        # This is about 2x faster than the implementation above on 3.2+
        int2byte = operator.methodcaller("to_bytes", 1, "big")
    byte2int = operator.itemgetter(0)
    indexbytes = operator.getitem
    iterbytes = iter
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    def b(s):
        return s
    def u(s):
        return unicode(s, "unicode_escape")
    unichr = unichr
    int2byte = chr
    def byte2int(bs):
        return ord(bs[0])
    def indexbytes(buf, i):
        return ord(buf[i])
    def iterbytes(buf):
        return (ord(byte) for byte in buf)
    import StringIO
    StringIO = BytesIO = StringIO.StringIO
_add_doc(b, """Byte literal""")
_add_doc(u, """Text literal""")


if PY3:
    import builtins
    exec_ = getattr(builtins, "exec")


    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value


    print_ = getattr(builtins, "print")
    del builtins

else:
    def exec_(_code_, _globs_=None, _locs_=None):
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


    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")


    def print_(*args, **kwargs):
        """The new-style print function."""
        fp = kwargs.pop("file", sys.stdout)
        if fp is None:
            return
        def write(data):
            if not isinstance(data, basestring):
                data = str(data)
            fp.write(data)
        want_unicode = False
        sep = kwargs.pop("sep", None)
        if sep is not None:
            if isinstance(sep, unicode):
                want_unicode = True
            elif not isinstance(sep, str):
                raise TypeError("sep must be None or a string")
        end = kwargs.pop("end", None)
        if end is not None:
            if isinstance(end, unicode):
                want_unicode = True
            elif not isinstance(end, str):
                raise TypeError("end must be None or a string")
        if kwargs:
            raise TypeError("invalid keyword arguments to print()")
        if not want_unicode:
            for arg in args:
                if isinstance(arg, unicode):
                    want_unicode = True
                    break
        if want_unicode:
            newline = unicode("\n")
            space = unicode(" ")
        else:
            newline = "\n"
            space = " "
        if sep is None:
            sep = space
        if end is None:
            end = newline
        for i, arg in enumerate(args):
            if i:
                write(sep)
            write(arg)
        write(end)

_add_doc(reraise, """Reraise an exception.""")


def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    return meta("NewBase", bases, {})

def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        for slots_var in orig_vars.get('__slots__', ()):
            orig_vars.pop(slots_var)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper

########NEW FILE########
__FILENAME__ = sqlalchemy
from itertools import count


__all__ = ['enumerate_query_by_limit']


def enumerate_query_by_limit(q, limit=1000):
    """
    Enumerate over SQLAlchemy query object ``q`` and yield individual results
    fetched in batches of size ``limit`` using SQL LIMIT and OFFSET.
    """
    for offset in count(0, limit):
        r = q.offset(offset).limit(limit).all()

        for row in r:
            yield row

        if len(r) < limit:
            break

########NEW FILE########
__FILENAME__ = collections_
from collections import MutableMapping, OrderedDict
from threading import Lock


__all__ = ['RecentlyUsedContainer']


_Null = object()


# This object is maintained under the urllib3 codebase.
class RecentlyUsedContainer(MutableMapping):
    """
    Provides a thread-safe dict-like container which maintains up to
    ``maxsize`` keys while throwing away the least-recently-used keys beyond
    ``maxsize``.

    :param maxsize:
        Maximum number of recent elements to retain.

    :param dispose_func:
        Every time an item is evicted from the container,
        ``dispose_func(value)`` is called.  Callback which will get called
    """

    ContainerCls = OrderedDict

    def __init__(self, maxsize=10, dispose_func=None):
        self._maxsize = maxsize
        self.dispose_func = dispose_func

        self._container = self.ContainerCls()
        self._lock = Lock()

    def __getitem__(self, key):
        # Re-insert the item, moving it to the end of the eviction line.
        with self._lock:
            item = self._container.pop(key)
            self._container[key] = item
            return item

    def __setitem__(self, key, value):
        evicted_value = _Null
        with self._lock:
            # Possibly evict the existing value of 'key'
            evicted_value = self._container.get(key, _Null)
            self._container[key] = value

            # If we didn't evict an existing value, we might have to evict the
            # least recently used item from the beginning of the container.
            if len(self._container) > self._maxsize:
                _key, evicted_value = self._container.popitem(last=False)

        if self.dispose_func and evicted_value is not _Null:
            self.dispose_func(evicted_value)

    def __delitem__(self, key):
        with self._lock:
            value = self._container.pop(key)

        if self.dispose_func:
            self.dispose_func(value)

    def __len__(self):
        with self._lock:
            return len(self._container)

    def __iter__(self):
        raise NotImplementedError('Iteration over this class is unlikely to be threadsafe.')

    def clear(self):
        with self._lock:
            # Copy pointers to all values, then wipe the mapping
            # under Python 2, this copies the list of values twice :-|
            values = list(self._container.values())
            self._container.clear()

        if self.dispose_func:
            for value in values:
                self.dispose_func(value)

    def keys(self):
        with self._lock:
            return self._container.keys()

########NEW FILE########
__FILENAME__ = contextlib_
import os

try:
    replace_func = os.replace
except AttributeError:
    replace_func = os.rename

def _doctest_setup():
    try:
        os.remove("/tmp/open_atomic-example.txt")
    except OSError:
        pass

class open_atomic(object):
    """
    Opens a file for atomic writing by writing to a temporary file, then moving
    the temporary file into place once writing has finished.

    When ``close()`` is called, the temporary file is moved into place,
    overwriting any file which may already exist (except on Windows, see note
    below). If moving the temporary file fails, ``abort()`` will be called *and
    an exception will be raised*.

    If ``abort()`` is called the temporary file will be removed and the
    ``aborted`` attribute will be set to ``True``. No exception will be raised
    if an error is encountered while removing the temporary file; instead, the
    ``abort_error`` attribute will be set to the exception raised by
    ``os.remove`` (note: on Windows, if ``file.close()`` raises an exception,
    ``abort_error`` will be set to that exception; see implementation of
    ``abort()`` for details).

    By default, ``open_atomic`` will put the temporary file in the same
    directory as the target file:
    ``${dirname(target_file)}/.${basename(target_file)}.temp``. See also the
    ``prefix``, ``suffix``, and ``dir`` arguments to ``open_atomic()``. When
    changing these options, remember:

        * The source and the destination must be on the same filesystem,
          otherwise the call to ``os.replace()``/``os.rename()`` may fail (and
          it *will* be much slower than necessary).
        * Using a random temporary name is likely a poor idea, as random names
          will mean it's more likely that temporary files will be left
          abandoned if a process is killed and re-started.
        * The temporary file will be blindly overwritten.

    The ``temp_name`` and ``target_name`` attributes store the temporary
    and target file names, and the ``name`` attribute stores the "current"
    name: if the file is still being written it will store the ``temp_name``,
    and if the temporary file has been moved into place it will store the
    ``target_name``.

    .. note::

        ``open_atomic`` will not work correctly on Windows with Python 2.X or
        Python <= 3.2: the call to ``open_atomic.close()`` will fail when the
        destination file exists (since ``os.rename`` will not overwrite the
        destination file; an exception will be raised and ``abort()`` will be
        called). On Python 3.3 and up ``os.replace`` will be used, which
        will be safe and atomic on both Windows and Unix.

    Example::

        >>> _doctest_setup()
        >>> f = open_atomic("/tmp/open_atomic-example.txt")
        >>> f.temp_name
        '/tmp/.open_atomic-example.txt.temp'
        >>> f.write("Hello, world!") and None
        >>> (os.path.exists(f.target_name), os.path.exists(f.temp_name))
        (False, True)
        >>> f.close()
        >>> os.path.exists("/tmp/open_atomic-example.txt")
        True

    By default, ``open_atomic`` uses the ``open`` builtin, but this behaviour
    can be changed using the ``opener`` argument::

        >>> import io
        >>> f = open_atomic("/tmp/open_atomic-example.txt",
        ...                opener=io.open,
        ...                mode="w+",
        ...                encoding="utf-8")
        >>> some_text = u"\u1234"
        >>> f.write(some_text) and None
        >>> f.seek(0)
        0
        >>> f.read() == some_text
        True
        >>> f.close()

    """

    def __init__(self, name, prefix=".", suffix=".temp", dir=None, mode="w",
                 opener=open, **open_args):
        self.target_name = name
        self.temp_name = self._get_temp_name(name, prefix, suffix, dir)
        self.file = opener(self.temp_name, mode, **open_args)
        self.name = self.temp_name
        self.closed = False
        self.aborted = False
        self.abort_error = None

    def _get_temp_name(self, target, prefix, suffix, dir):
        if dir is None:
            dir = os.path.dirname(target)
        return os.path.join(dir, "%s%s%s" %(
            prefix, os.path.basename(target), suffix,
        ))

    def close(self):
        if self.closed:
            return
        try:
            self.file.close()
            replace_func(self.temp_name, self.target_name)
            self.name = self.target_name
        except:
            try:
                self.abort()
            except:
                pass
            raise
        self.closed = True

    def abort(self):
        try:
            if os.name == "nt":
                # Note: Windows can't remove an open file, so sacrifice some
                # safety and close it before deleting it here. This is only a
                # problem if ``.close()`` raises an exception, which it really
                # shouldn't... But it's probably a better idea to be safe.
                self.file.close()
            os.remove(self.temp_name)
        except OSError as e:
            self.abort_error = e
        self.file.close()
        self.closed = True
        self.aborted = True

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        if exc_info[0] is None:
            self.close()
        else:
            self.abort()

    def __getattr__(self, attr):
        return getattr(self.file, attr)

########NEW FILE########
__FILENAME__ = datetime_
import calendar
import datetime


__all__ = ['iterate_date', 'iterate_date_values', 'isoformat_as_datetime',
           'truncate_datetime', 'now', 'datetime_from_timestamp',
           'timestamp_from_datetime']


def iterate_date(start, stop=None, step=datetime.timedelta(days=1)):
    while not stop or start <= stop:
        yield start
        start += step


def iterate_date_values(d, start_date=None, stop_date=None, default=0):
    """
    Convert (date, value) sorted lists into contiguous value-per-day data sets. Great for sparklines.

    Example::

        [(datetime.date(2011, 1, 1), 1), (datetime.date(2011, 1, 4), 2)] -> [1, 0, 0, 2]

    """
    dataiter = iter(d)
    cur_day, cur_val = next(dataiter)

    start_date = start_date or cur_day

    while cur_day < start_date:
        cur_day, cur_val = next(dataiter)

    for d in iterate_date(start_date, stop_date):
        if d != cur_day:
            yield default
            continue

        yield cur_val
        try:
            cur_day, cur_val = next(dataiter)
        except StopIteration:
            if not stop_date:
                raise


def isoformat_as_datetime(s):
    """
    Convert a datetime.datetime.isoformat() string to a datetime.datetime() object.
    """
    return datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ')


def truncate_datetime(t, resolution):
    """
    Given a datetime ``t`` and a ``resolution``, flatten the precision beyond the given resolution.

    ``resolution`` can be one of: year, month, day, hour, minute, second, microsecond

    Example::

        >>> t = datetime.datetime(2000, 1, 2, 3, 4, 5, 6000) # Or, 2000-01-02 03:04:05.006000

        >>> truncate_datetime(t, 'day')
        datetime.datetime(2000, 1, 2, 0, 0)
        >>> _.isoformat()
        '2000-01-02T00:00:00'

        >>> truncate_datetime(t, 'minute')
        datetime.datetime(2000, 1, 2, 3, 4)
        >>> _.isoformat()
        '2000-01-02T03:04:00'

    """

    resolutions = ['year', 'month', 'day', 'hour', 'minute', 'second', 'microsecond']
    if resolution not in resolutions:
        raise KeyError("Resolution is not valid: {0}".format(resolution))

    args = []
    for r in resolutions:
        args += [getattr(t, r)]
        if r == resolution:
            break

    return datetime.datetime(*args)

def to_timezone(dt, timezone):
    """
    Return an aware datetime which is ``dt`` converted to ``timezone``.

    If ``dt`` is naive, it is assumed to be UTC.

    For example, if ``dt`` is "06:00 UTC+0000" and ``timezone`` is "EDT-0400",
    then the result will be "02:00 EDT-0400".

    This method follows the guidelines in http://pytz.sourceforge.net/
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_UTC)
    return timezone.normalize(dt.astimezone(timezone))

def now(timezone=None):
    """
    Return a naive datetime object for the given ``timezone``. A ``timezone``
    is any pytz- like or datetime.tzinfo-like timezone object. If no timezone
    is given, then UTC is assumed.

    This method is best used with pytz installed::

        pip install pytz
    """
    d = datetime.datetime.utcnow()
    if not timezone:
        return d

    return to_timezone(d, timezone).replace(tzinfo=None)

def datetime_from_timestamp(timestamp):
    """
    Returns a naive datetime from ``timestamp``.

    >>> datetime_from_timestamp(1234.5)
    datetime.datetime(1970, 1, 1, 0, 20, 34, 500000)
    """
    return datetime.datetime.utcfromtimestamp(timestamp)

def timestamp_from_datetime(dt):
    """
    Returns a timestamp from datetime ``dt``.

    Note that timestamps are always UTC. If ``dt`` is aware, the resulting
    timestamp will correspond to the correct UTC time.

    >>> timestamp_from_datetime(datetime.datetime(1970, 1, 1, 0, 20, 34, 500000))
    1234.5
    """
    return calendar.timegm(dt.utctimetuple()) + (dt.microsecond / 1000000.0)

# Built-in timezone for when pytz isn't available:

_ZERO = datetime.timedelta(0)

class _UTC(datetime.tzinfo):
    """
    UTC implementation taken from Python's docs.

    Use only when pytz isn't available.
    """

    def __repr__(self):
        return "<UTC>"

    def utcoffset(self, dt):
        return _ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return _ZERO


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)

########NEW FILE########
__FILENAME__ = dict_
__all__ = [
    'get_many', 'pop_many',
]


def get_many(d, required=[], optional=[], one_of=[]):
    """
    Returns a predictable number of elements out of ``d`` in a list for auto-expanding.

    Keys in ``required`` will raise KeyError if not found in ``d``.
    Keys in ``optional`` will return None if not found in ``d``.
    Keys in ``one_of`` will raise KeyError if none exist, otherwise return the first in ``d``.

    Example::

        uid, action, limit, offset = get_many(request.params, required=['uid', 'action'], optional=['limit', 'offset'])

    Note: This function has been added to the webhelpers package.
    """
    d = d or {}
    r = [d[k] for k in required]
    r += [d.get(k)for k in optional]

    if one_of:
        for k in (k for k in one_of if k in d):
            return r + [d[k]]

        raise KeyError("Missing a one_of value.")

    return r


def pop_many(d, keys, default=None):
    return [d.pop(k, default) for k in keys]


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)

########NEW FILE########
__FILENAME__ = exception_
import sys

from unstdlib.six import reraise, PY3


__all__ = ['convert_exception']


def convert_exception(from_exception, to_exception, *to_args, **to_kw):
    """
    Decorator: Catch exception ``from_exception`` and instead raise ``to_exception(*to_args, **to_kw)``.

    Useful when modules you're using in a method throw their own errors that you want to
    convert to your own exceptions that you handle higher in the stack.

    Example: ::

        class FooError(Exception):
            pass

        class BarError(Exception):
            def __init__(self, message):
                self.message = message

        @convert_exception(FooError, BarError, message='bar')
        def throw_foo():
            raise FooError('foo')

        try:
            throw_foo()
        except BarError as e:
            assert e.message == 'bar'
    """
    def wrapper(fn):

        def fn_new(*args, **kw):
            try:
                return fn(*args, **kw)
            except from_exception:
                new_exception = to_exception(*to_args, **to_kw)
                traceback = sys.exc_info()[2]
                if PY3:
                    value = new_exception
                else:
                    value = None
                reraise(new_exception, value, traceback)

        fn_new.__doc__ = fn.__doc__
        return fn_new

    return wrapper


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)

########NEW FILE########
__FILENAME__ = functools_
from functools import wraps, partial
import warnings

from .list_ import iterate_items


__all__ = [
    'memoized', 'memoized_property', 'assert_hashable', 'deprecated',
]


def assert_hashable(*args, **kw):
    """ Verify that each argument is hashable.

    Passes silently if successful. Raises descriptive TypeError otherwise.

    Example::

        >>> assert_hashable(1, 'foo', bar='baz')
        >>> assert_hashable(1, [], baz='baz')
        Traceback (most recent call last):
          ...
        TypeError: Argument in position 1 is not hashable: []
        >>> assert_hashable(1, 'foo', bar=[])
        Traceback (most recent call last):
          ...
        TypeError: Keyword argument 'bar' is not hashable: []
    """
    try:
        for i, arg in enumerate(args):
            hash(arg)
    except TypeError:
        raise TypeError('Argument in position %d is not hashable: %r' % (i, arg))
    try:
        for key, val in iterate_items(kw):
            hash(val)
    except TypeError:
        raise TypeError('Keyword argument %r is not hashable: %r' % (key, val))


def _memoized_call(fn, cache, *args, **kw):
    key = (args, tuple(sorted(kw.items())))

    try:
        is_cached = key in cache
    except TypeError as e:
        # Re-raise a more descriptive error if it's a hashing problem.
        assert_hashable(*args, **kw)
        # If it hasn't raised by now, then something else is going on,
        # raise it. (This shouldn't happen.)
        raise e

    if not is_cached:
        cache[key] = fn(*args, **kw)
    return cache[key]


def memoized(fn=None, cache=None):
    """ Memoize a function into an optionally-specificed cache container.

    If the `cache` container is not specified, then the instance container is
    accessible from the wrapped function's `memoize_cache` property.

    Example::

        >>> @memoized
        ... def foo(bar):
        ...   print("Not cached.")
        >>> foo(1)
        Not cached.
        >>> foo(1)
        >>> foo(2)
        Not cached.

    Example with a specific cache container (in this case, the
    ``RecentlyUsedContainer``, which will only store the ``maxsize`` most
    recently accessed items)::

        >>> from unstdlib.standard.collections_ import RecentlyUsedContainer
        >>> lru_container = RecentlyUsedContainer(maxsize=2)
        >>> @memoized(cache=lru_container)
        ... def baz(x):
        ...   print("Not cached.")
        >>> baz(1)
        Not cached.
        >>> baz(1)
        >>> baz(2)
        Not cached.
        >>> baz(3)
        Not cached.
        >>> baz(2)
        >>> baz(1)
        Not cached.
        >>> # Notice that the '2' key remains, but the '1' key was evicted from
        >>> # the cache.
    """
    if fn:
        # This is a hack to support both @memoize and @memoize(...)
        return memoized(cache=cache)(fn)

    if cache is None:
        cache = {}

    def decorator(fn):
        wrapped = wraps(fn)(partial(_memoized_call, fn, cache))
        wrapped.memoize_cache = cache
        return wrapped

    return decorator


# `memoized_property` is lovingly borrowed from @zzzeek, with permission:
#   https://twitter.com/zzzeek/status/310503354268790784
class memoized_property(object):
    """ A read-only @property that is only evaluated once. """
    def __init__(self, fget, doc=None, name=None):
        self.fget = fget
        self.__doc__ = doc or fget.__doc__
        self.__name__ = name or fget.__name__

    def __get__(self, obj, cls):
        if obj is None:
            return self
        obj.__dict__[self.__name__] = result = self.fget(obj)
        return result


def memoized_method(method=None, cache_factory=None):
    """ Memoize a class's method.

    Arguments are similar to to `memoized`, except that the cache container is
    specified with `cache_factory`: a function called with no arguments to
    create the caching container for the instance.

    Note that, unlike `memoized`, the result cache will be stored on the
    instance, so cached results will be deallocated along with the instance.

    Example::

        >>> class Person(object):
        ...     def __init__(self, name):
        ...         self._name = name
        ...     @memoized_method
        ...     def get_name(self):
        ...         print("Calling get_name on %r" %(self._name, ))
        ...         return self._name
        >>> shazow = Person("shazow")
        >>> shazow.get_name()
        Calling get_name on 'shazow'
        'shazow'
        >>> shazow.get_name()
        'shazow'
        >>> shazow._get_name_cache
        {((), ()): 'shazow'}

    Example with a specific cache container::

        >>> from unstdlib.standard.collections_ import RecentlyUsedContainer
        >>> class Foo(object):
        ...     @memoized_method(cache_factory=lambda: RecentlyUsedContainer(maxsize=2))
        ...     def add(self, a, b):
        ...         print("Calling add with %r and %r" %(a, b))
        ...         return a + b
        >>> foo = Foo()
        >>> foo.add(1, 1)
        Calling add with 1 and 1
        2
        >>> foo.add(1, 1)
        2
        >>> foo.add(2, 2)
        Calling add with 2 and 2
        4
        >>> foo.add(3, 3)
        Calling add with 3 and 3
        6
        >>> foo.add(1, 1)
        Calling add with 1 and 1
        2
    """

    if method is None:
        return lambda f: memoized_method(f, cache_factory=cache_factory)

    cache_factory = cache_factory or dict

    @wraps(method)
    def memoized_method_property(self):
        cache = cache_factory()
        cache_attr = "_%s_cache" %(method.__name__, )
        setattr(self, cache_attr, cache)
        result = partial(
            _memoized_call,
            partial(method, self),
            cache
        )
        result.memoize_cache = cache
        return result
    return memoized_property(memoized_method_property)


def deprecated(message, exception=PendingDeprecationWarning):
    """Throw a warning when a function/method will be soon deprecated

    Supports passing a ``message`` and an ``exception`` class
    (uses ``PendingDeprecationWarning`` by default). This is useful if you
    want to alternatively pass a ``DeprecationWarning`` exception for already
    deprecated functions/methods.

    Example::

        >>> import warnings
        >>> from functools import wraps
        >>> message = "this function will be deprecated in the near future"
        >>> @deprecated(message)
        ... def foo(n):
        ...     return n+n
        >>> with warnings.catch_warnings(record=True) as w:
        ...     warnings.simplefilter("always")
        ...     foo(4)
        ...     assert len(w) == 1
        ...     assert issubclass(w[-1].category, PendingDeprecationWarning)
        ...     assert message == str(w[-1].message)
        8
    """
    def decorator(func):
        wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(message, exception, stacklevel=2)
            return func(*args, **kwargs)
        return wrapper
    return decorator


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)

########NEW FILE########
__FILENAME__ = list_
from itertools import chain
from functools import wraps
from collections import defaultdict

from unstdlib.six import string_types
from unstdlib.six.moves import xrange


__all__ = [
    'groupby_count',
    'iterate', 'is_iterable', 'iterate_chunks', 'iterate_items', 'iterate_flatten',
    'listify',
]


def groupby_count(i, key=None, force_keys=None):
    """ Aggregate iterator values into buckets based on how frequently the
    values appear.

    Example::

        >>> list(groupby_count([1, 1, 1, 2, 3]))
        [(1, 3), (2, 1), (3, 1)]
    """
    counter = defaultdict(lambda: 0)
    if not key:
        key = lambda o: o

    for k in i:
        counter[key(k)] += 1

    if force_keys:
        for k in force_keys:
            counter[k] += 0

    return counter.items()


def is_iterable(maybe_iter, unless=(string_types, dict)):
    """ Return whether ``maybe_iter`` is an iterable, unless it's an instance of one
    of the base class, or tuple of base classes, given in ``unless``.

    Example::

        >>> is_iterable('foo')
        False
        >>> is_iterable(['foo'])
        True
        >>> is_iterable(['foo'], unless=list)
        False
        >>> is_iterable(xrange(5))
        True
    """
    try:
        iter(maybe_iter)
    except TypeError:
        return False
    return not isinstance(maybe_iter, unless)


def iterate(maybe_iter, unless=(string_types, dict)):
    """ Always return an iterable.

    Returns ``maybe_iter`` if it is an iterable, otherwise it returns a single
    element iterable containing ``maybe_iter``. By default, strings and dicts
    are treated as non-iterable. This can be overridden by passing in a type
    or tuple of types for ``unless``.

    :param maybe_iter:
        A value to return as an iterable.

    :param unless:
        A type or tuple of types (same as ``isinstance``) to be treated as
        non-iterable.

    Example::

        >>> iterate('foo')
        ['foo']
        >>> iterate(['foo'])
        ['foo']
        >>> iterate(['foo'], unless=list)
        [['foo']]
        >>> list(iterate(xrange(5)))
        [0, 1, 2, 3, 4]
    """
    if is_iterable(maybe_iter, unless=unless):
        return maybe_iter
    return [maybe_iter]


def iterate_items(dictish):
    """ Return a consistent (key, value) iterable on dict-like objects,
    including lists of tuple pairs.

    Example:

        >>> list(iterate_items({'a': 1}))
        [('a', 1)]
        >>> list(iterate_items([('a', 1), ('b', 2)]))
        [('a', 1), ('b', 2)]
    """
    if hasattr(dictish, 'iteritems'):
        return dictish.iteritems()
    if hasattr(dictish, 'items'):
        return dictish.items()
    return dictish


def iterate_chunks(i, size=10):
    """
    Iterate over an iterator ``i`` in ``size`` chunks, yield chunks.
    Similar to pagination.

    Example::

        >>> list(iterate_chunks([1, 2, 3, 4], size=2))
        [[1, 2], [3, 4]]
    """
    accumulator = []

    for n, i in enumerate(i):
        accumulator.append(i)
        if (n+1) % size == 0:
            yield accumulator
            accumulator = []

    if accumulator:
        yield accumulator


def iterate_flatten(q):
    """
    Flatten nested lists.

    Useful for flattening one-value tuple rows returned from a database query.

    Example::

        [("foo",), ("bar",)] -> ["foo", "bar"]

        [[1,2,3],[4,5,6]] -> [1,2,3,4,5,6]

    """

    return chain.from_iterable(q)


def listify(fn=None, wrapper=list):
    """
    A decorator which wraps a function's return value in ``list(...)``.

    Useful when an algorithm can be expressed more cleanly as a generator but
    the function should return an list.

    Example::

        >>> @listify
        ... def get_lengths(iterable):
        ...     for i in iterable:
        ...         yield len(i)
        >>> get_lengths(["spam", "eggs"])
        [4, 4]
        >>>
        >>> @listify(wrapper=tuple)
        ... def get_lengths_tuple(iterable):
        ...     for i in iterable:
        ...         yield len(i)
        >>> get_lengths_tuple(["foo", "bar"])
        (3, 3)
    """
    def listify_return(fn):
        @wraps(fn)
        def listify_helper(*args, **kw):
            return wrapper(fn(*args, **kw))
        return listify_helper
    if fn is None:
        return listify_return
    return listify_return(fn)


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)

########NEW FILE########
__FILENAME__ = os_
import os

class chdir(object):
    """ A drop-in replacement for ``os.chdir`` which can also be used as a
    context manager.

    Example::

        >>> old_cwd = os.getcwd()
        >>> with chdir("/usr/"):
        ...     print("current dir: {0}".format(os.getcwd()))
        ...
        current dir: /usr
        >>> os.getcwd() == old_cwd
        True
        >>> x = chdir("/usr/")
        >>> os.getcwd()
        '/usr'
        >>> x.unchdir()
        >>> os.getcwd() == old_cwd
        True
    """

    def __init__(self, new_path, old_path=None):
        self.old_path = old_path or os.getcwd()
        self.new_path = new_path
        self.chdir()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.unchdir()

    def chdir(self):
        os.chdir(self.new_path)

    def unchdir(self):
        os.chdir(self.old_path)

    def __repr__(self):
        return "%s(%r, old_path=%r)" %(
            type(self).__name__, self.new_path, self.old_path,
        )

if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)

########NEW FILE########
__FILENAME__ = random_
import logging
import random as _random

log = logging.getLogger(__name__)

try:
    random = _random.SystemRandom()
except NotImplementedError:
    log.warn('random.SystemRandom() is not available. Using random.Random() '
             'instead, this means that things will be less random.')
    random = _random.Random()


__all__ = ['random']

########NEW FILE########
__FILENAME__ = string_
import re
import string
import unicodedata

from unstdlib.six import text_type, PY3, string_types, binary_type, u
from unstdlib.six.moves import xrange

if PY3:
    text_type_magicmethod = "__str__"
else:
    text_type_magicmethod = "__unicode__"

from .random_ import random


__all__ = [
    'random_string',
    'number_to_string', 'string_to_number', 'number_to_bytes', 'bytes_to_number',
    'dollars_to_cents',
    'to_str', 'to_unicode', 'to_int', 'to_float',
    'format_int',
    'slugify',
]

class r(object):
    """
    A normalized repr for bytes/unicode between Python2 and Python3.
    """
    def __init__(self, val):
        self.val = val

    def __repr__(self):
        if PY3:
            if isinstance(self.val, text_type):
                return 'u' + repr(self.val)
        else:
            if isinstance(self.val, str):
                return 'b' + repr(self.val)
        return repr(self.val)


_Default = object()

def random_string(length=6, alphabet=string.ascii_letters+string.digits):
    """
    Return a random string of given length and alphabet.

    Default alphabet is url-friendly (base62).
    """
    return ''.join([random.choice(alphabet) for i in xrange(length)])


def number_to_string(n, alphabet):
    """
    Given an non-negative integer ``n``, convert it to a string composed of
    the given ``alphabet`` mapping, where the position of each element in
    ``alphabet`` is its radix value.

    Examples::

        >>> number_to_string(12345678, '01')
        '101111000110000101001110'

        >>> number_to_string(12345678, 'ab')
        'babbbbaaabbaaaababaabbba'

        >>> number_to_string(12345678, string.ascii_letters + string.digits)
        'ZXP0'

        >>> number_to_string(12345, ['zero ', 'one ', 'two ', 'three ', 'four ', 'five ', 'six ', 'seven ', 'eight ', 'nine '])
        'one two three four five '

    """
    result = ''
    base = len(alphabet)
    current = int(n)
    if current < 0:
        raise ValueError("invalid n (must be non-negative): %s", n)
    while current:
        result = alphabet[current % base] + result
        current = current // base

    return result


def string_to_number(s, alphabet):
    """
    Given a string ``s``, convert it to an integer composed of the given
    ``alphabet`` mapping, where the position of each element in ``alphabet`` is
    its radix value.

    Examples::

        >>> string_to_number('101111000110000101001110', '01')
        12345678

        >>> string_to_number('babbbbaaabbaaaababaabbba', 'ab')
        12345678

        >>> string_to_number('ZXP0', string.ascii_letters + string.digits)
        12345678

    """
    base = len(alphabet)
    inverse_alphabet = dict(zip(alphabet, xrange(0, base)))
    n = 0
    exp = 0
    for i in reversed(s):
        n += inverse_alphabet[i] * (base ** exp)
        exp += 1

    return n


def bytes_to_number(b, endian='big'):
    """
    Convert a string to an integer.

    :param b:
        String or bytearray to convert.

    :param endian:
        Byte order to convert into ('big' or 'little' endian-ness, default
        'big')

    Assumes bytes are 8 bits.

    This is a special-case version of string_to_number with a full base-256
    ASCII alphabet. It is the reverse of ``number_to_bytes(n)``.

    Examples::

        >>> bytes_to_number(b'*')
        42
        >>> bytes_to_number(b'\\xff')
        255
        >>> bytes_to_number(b'\\x01\\x00')
        256
        >>> bytes_to_number(b'\\x00\\x01', endian='little')
        256
    """
    if endian == 'big':
        b = reversed(b)

    n = 0
    for i, ch in enumerate(bytearray(b)):
        n ^= ch << i * 8

    return n


def number_to_bytes(n, endian='big'):
    """
    Convert an integer to a corresponding string of bytes..

    :param n:
        Integer to convert.

    :param endian:
        Byte order to convert into ('big' or 'little' endian-ness, default
        'big')

    Assumes bytes are 8 bits.

    This is a special-case version of number_to_string with a full base-256
    ASCII alphabet. It is the reverse of ``bytes_to_number(b)``.

    Examples::

        >>> r(number_to_bytes(42))
        b'*'
        >>> r(number_to_bytes(255))
        b'\\xff'
        >>> r(number_to_bytes(256))
        b'\\x01\\x00'
        >>> r(number_to_bytes(256, endian='little'))
        b'\\x00\\x01'
    """
    res = []
    while n:
        n, ch = divmod(n, 256)
        if PY3:
            res.append(ch)
        else:
            res.append(chr(ch))

    if endian == 'big':
        res.reverse()

    if PY3:
        return bytes(res)
    else:
        return ''.join(res)


def to_str(obj, encoding='utf-8', **encode_args):
    r"""
    Returns a ``str`` of ``obj``, encoding using ``encoding`` if necessary. For
    example::

        >>> some_str = b"\xff"
        >>> some_unicode = u"\u1234"
        >>> some_exception = Exception(u'Error: ' + some_unicode)
        >>> r(to_str(some_str))
        b'\xff'
        >>> r(to_str(some_unicode))
        b'\xe1\x88\xb4'
        >>> r(to_str(some_exception))
        b'Error: \xe1\x88\xb4'
        >>> r(to_str([42]))
        b'[42]'

    See source code for detailed semantics.
    """
    # Note: On py3, ``b'x'.__str__()`` returns ``"b'x'"``, so we need to do the
    # explicit check first.
    if isinstance(obj, binary_type):
        return obj

    # We coerce to unicode if '__unicode__' is available because there is no
    # way to specify encoding when calling ``str(obj)``, so, eg,
    # ``str(Exception(u'\u1234'))`` will explode.
    if isinstance(obj, text_type) or hasattr(obj, text_type_magicmethod):
        # Note: unicode(u'foo') is O(1) (by experimentation)
        return text_type(obj).encode(encoding, **encode_args)

    return binary_type(obj)


def to_unicode(obj, encoding='utf-8', fallback='latin1', **decode_args):
    r"""
    Returns a ``unicode`` of ``obj``, decoding using ``encoding`` if necessary.
    If decoding fails, the ``fallback`` encoding (default ``latin1``) is used.

    Examples::

        >>> r(to_unicode(b'\xe1\x88\xb4'))
        u'\u1234'
        >>> r(to_unicode(b'\xff'))
        u'\xff'
        >>> r(to_unicode(u'\u1234'))
        u'\u1234'
        >>> r(to_unicode(Exception(u'\u1234')))
        u'\u1234'
        >>> r(to_unicode([42]))
        u'[42]'

    See source code for detailed semantics.
    """

    # Note: on py3, the `bytes` type defines an unhelpful "__str__" function,
    # so we need to do this check (see comments in ``to_str``).
    if not isinstance(obj, binary_type):
        if isinstance(obj, text_type) or hasattr(obj, text_type_magicmethod):
            return text_type(obj)

        obj_str = binary_type(obj)
    else:
        obj_str = obj

    try:
        return text_type(obj_str, encoding, **decode_args)
    except UnicodeDecodeError:
        return text_type(obj_str, fallback, **decode_args)


def to_int(s, default=0):
    """
    Return input converted into an integer. If failed, then return ``default``.

    Examples::

        >>> to_int('1')
        1
        >>> to_int(1)
        1
        >>> to_int('')
        0
        >>> to_int(None)
        0
        >>> to_int(0, default='Empty')
        0
        >>> to_int(None, default='Empty')
        'Empty'
    """
    try:
        return int(s)
    except (TypeError, ValueError):
        return default


_infs=set([float("inf"), float("-inf")])

def to_float(s, default=0.0, allow_nan=False):
    """
    Return input converted into a float. If failed, then return ``default``.

    Note that, by default, ``allow_nan=False``, so ``to_float`` will not return
    ``nan``, ``inf``, or ``-inf``.

    Examples::

        >>> to_float('1.5')
        1.5
        >>> to_float(1)
        1.0
        >>> to_float('')
        0.0
        >>> to_float('nan')
        0.0
        >>> to_float('inf')
        0.0
        >>> to_float('-inf', allow_nan=True)
        -inf
        >>> to_float(None)
        0.0
        >>> to_float(0, default='Empty')
        0.0
        >>> to_float(None, default='Empty')
        'Empty'
    """
    try:
        f = float(s)
    except (TypeError, ValueError):
        return default
    if not allow_nan:
        if f != f or f in _infs:
            return default
    return f


def format_int(n, singular=_Default, plural=_Default):
    """
    Return `singular.format(n)` if n is 1, or `plural.format(n)` otherwise. If
    plural is not specified, then it is assumed to be same as singular but
    suffixed with an 's'.

    :param n:
        Integer which determines pluralness.

    :param singular:
        String with a format() placeholder for n. (Default: `u"{:,}"`)

    :param plural:
        String with a format() placeholder for n. (Default: If singular is not
        default, then it's `singular + u"s"`. Otherwise it's same as singular.)

    Example: ::

        >>> r(format_int(1000))
        u'1,000'
        >>> r(format_int(1, u"{} day"))
        u'1 day'
        >>> r(format_int(2, u"{} day"))
        u'2 days'
        >>> r(format_int(2, u"{} box", u"{} boxen"))
        u'2 boxen'
        >>> r(format_int(20000, u"{:,} box", u"{:,} boxen"))
        u'20,000 boxen'
    """
    n = int(n)

    if singular in (None, _Default):
        if plural is _Default:
            plural = None

        singular = u'{:,}'

    elif plural is _Default:
        plural = singular + u's'

    if n == 1 or not plural:
        return singular.format(n)

    return plural.format(n)



RE_NUMBER = re.compile(r'[\d\.\-eE]+')

def dollars_to_cents(s, allow_negative=False):
    """
    Given a string or integer representing dollars, return an integer of
    equivalent cents, in an input-resilient way.
    
    This works by stripping any non-numeric characters before attempting to
    cast the value.

    Examples::

        >>> dollars_to_cents('$1')
        100
        >>> dollars_to_cents('1')
        100
        >>> dollars_to_cents(1)
        100
        >>> dollars_to_cents('1e2')
        10000
        >>> dollars_to_cents('-1$', allow_negative=True)
        -100
        >>> dollars_to_cents('1 dollar')
        100
    """
    # TODO: Implement cents_to_dollars
    if not s:
        return

    if isinstance(s, string_types):
        s = ''.join(RE_NUMBER.findall(s))

    dollars = int(round(float(s) * 100))
    if not allow_negative and dollars < 0:
        raise ValueError('Negative values not permitted.')

    return dollars


RE_SLUG = re.compile(r'\W+')

def slugify(s, delimiter='-'):
    """
    Normalize `s` into ASCII and replace non-word characters with `delimiter`.
    """
    s = unicodedata.normalize('NFKD', to_unicode(s)).encode('ascii', 'ignore').decode('ascii')
    return RE_SLUG.sub(delimiter, s).strip(delimiter).lower()


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)

########NEW FILE########
__FILENAME__ = type_
__all__ = ['is_subclass']


_issubclass = issubclass

def is_subclass(o, bases):
    """
    Similar to the ``issubclass`` builtin, but does not raise a ``TypeError``
    if either ``o`` or ``bases`` is not an instance of ``type``.

    Example::

        >>> is_subclass(IOError, Exception)
        True
        >>> is_subclass(Exception, None)
        False
        >>> is_subclass(None, Exception)
        False
        >>> is_subclass(IOError, (None, Exception))
        True
        >>> is_subclass(Exception, (None, 42))
        False
    """
    try:
        return _issubclass(o, bases)
    except TypeError:
        pass

    if not isinstance(o, type):
        return False
    if not isinstance(bases, tuple):
        return False

    bases = tuple(b for b in bases if isinstance(b, type))
    return _issubclass(o, bases)


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)

########NEW FILE########
