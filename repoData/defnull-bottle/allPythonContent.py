__FILENAME__ = bottle
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bottle is a fast and simple micro-framework for small web applications. It
offers request dispatching (Routes) with url parameter support, templates,
a built-in HTTP Server and adapters for many third party WSGI/HTTP-server and
template engines - all in a single file and with no dependencies other than the
Python Standard Library.

Homepage and documentation: http://bottlepy.org/

Copyright (c) 2014, Marcel Hellkamp.
License: MIT (see LICENSE for details)
"""

from __future__ import with_statement

__author__ = 'Marcel Hellkamp'
__version__ = '0.13-dev'
__license__ = 'MIT'

# The gevent and eventlet server adapters need to patch some modules before
# they are imported. This is why we parse the commandline parameters here but
# handle them later
if __name__ == '__main__':
    from optparse import OptionParser
    _cmd_parser = OptionParser(usage="usage: %prog [options] package.module:app")
    _opt = _cmd_parser.add_option
    _opt("--version", action="store_true", help="show version number.")
    _opt("-b", "--bind", metavar="ADDRESS", help="bind socket to ADDRESS.")
    _opt("-s", "--server", default='wsgiref', help="use SERVER as backend.")
    _opt("-p", "--plugin", action="append", help="install additional plugin/s.")
    _opt("--debug", action="store_true", help="start server in debug mode.")
    _opt("--reload", action="store_true", help="auto-reload on file changes.")
    _cmd_options, _cmd_args = _cmd_parser.parse_args()
    if _cmd_options.server:
        if _cmd_options.server.startswith('gevent'):
            import gevent.monkey; gevent.monkey.patch_all()
        elif _cmd_options.server.startswith('eventlet'):
            import eventlet; eventlet.monkey_patch()

import base64, cgi, email.utils, functools, hmac, imp, itertools, mimetypes,\
        os, re, subprocess, sys, tempfile, threading, time, warnings

from datetime import date as datedate, datetime, timedelta
from tempfile import TemporaryFile
from traceback import format_exc, print_exc
from inspect import getargspec
from unicodedata import normalize


try: from simplejson import dumps as json_dumps, loads as json_lds
except ImportError: # pragma: no cover
    try: from json import dumps as json_dumps, loads as json_lds
    except ImportError:
        try: from django.utils.simplejson import dumps as json_dumps, loads as json_lds
        except ImportError:
            def json_dumps(data):
                raise ImportError("JSON support requires Python 2.6 or simplejson.")
            json_lds = json_dumps



# We now try to fix 2.5/2.6/3.1/3.2 incompatibilities.
# It ain't pretty but it works... Sorry for the mess.

py   = sys.version_info
py3k = py >= (3, 0, 0)
py25 = py <  (2, 6, 0)
py31 = (3, 1, 0) <= py < (3, 2, 0)

# Workaround for the missing "as" keyword in py3k.
def _e(): return sys.exc_info()[1]

# Workaround for the "print is a keyword/function" Python 2/3 dilemma
# and a fallback for mod_wsgi (resticts stdout/err attribute access)
try:
    _stdout, _stderr = sys.stdout.write, sys.stderr.write
except IOError:
    _stdout = lambda x: sys.stdout.write(x)
    _stderr = lambda x: sys.stderr.write(x)

# Lots of stdlib and builtin differences.
if py3k:
    import http.client as httplib
    import _thread as thread
    from urllib.parse import urljoin, SplitResult as UrlSplitResult
    from urllib.parse import urlencode, quote as urlquote, unquote as urlunquote
    urlunquote = functools.partial(urlunquote, encoding='latin1')
    from http.cookies import SimpleCookie
    from collections import MutableMapping as DictMixin
    import pickle
    from io import BytesIO
    from configparser import ConfigParser
    basestring = str
    unicode = str
    json_loads = lambda s: json_lds(touni(s))
    callable = lambda x: hasattr(x, '__call__')
    imap = map
    def _raise(*a): raise a[0](a[1]).with_traceback(a[2])
else: # 2.x
    import httplib
    import thread
    from urlparse import urljoin, SplitResult as UrlSplitResult
    from urllib import urlencode, quote as urlquote, unquote as urlunquote
    from Cookie import SimpleCookie
    from itertools import imap
    import cPickle as pickle
    from StringIO import StringIO as BytesIO
    from ConfigParser import SafeConfigParser as ConfigParser
    if py25:
        msg  = "Python 2.5 support may be dropped in future versions of Bottle."
        warnings.warn(msg, DeprecationWarning)
        from UserDict import DictMixin
        def next(it): return it.next()
        bytes = str
    else: # 2.6, 2.7
        from collections import MutableMapping as DictMixin
    unicode = unicode
    json_loads = json_lds
    eval(compile('def _raise(*a): raise a[0], a[1], a[2]', '<py3fix>', 'exec'))


# Some helpers for string/byte handling
def tob(s, enc='utf8'):
    return s.encode(enc) if isinstance(s, unicode) else bytes(s)


def touni(s, enc='utf8', err='strict'):
    if isinstance(s, bytes):
        return s.decode(enc, err)
    else:
        return unicode(s or ("" if s is None else s))

tonat = touni if py3k else tob

# 3.2 fixes cgi.FieldStorage to accept bytes (which makes a lot of sense).
# 3.1 needs a workaround.
if py31:
    from io import TextIOWrapper

    class NCTextIOWrapper(TextIOWrapper):
        def close(self): pass # Keep wrapped buffer open.


# A bug in functools causes it to break if the wrapper is an instance method
def update_wrapper(wrapper, wrapped, *a, **ka):
    try:
        functools.update_wrapper(wrapper, wrapped, *a, **ka)
    except AttributeError:
        pass


# These helpers are used at module level and need to be defined first.
# And yes, I know PEP-8, but sometimes a lower-case classname makes more sense.

def depr(message, strict=False):
    warnings.warn(message, DeprecationWarning, stacklevel=3)

def makelist(data): # This is just to handy
    if isinstance(data, (tuple, list, set, dict)):
        return list(data)
    elif data:
        return [data]
    else:
        return []


class DictProperty(object):
    """ Property that maps to a key in a local dict-like attribute. """
    def __init__(self, attr, key=None, read_only=False):
        self.attr, self.key, self.read_only = attr, key, read_only

    def __call__(self, func):
        functools.update_wrapper(self, func, updated=[])
        self.getter, self.key = func, self.key or func.__name__
        return self

    def __get__(self, obj, cls):
        if obj is None: return self
        key, storage = self.key, getattr(obj, self.attr)
        if key not in storage: storage[key] = self.getter(obj)
        return storage[key]

    def __set__(self, obj, value):
        if self.read_only: raise AttributeError("Read-Only property.")
        getattr(obj, self.attr)[self.key] = value

    def __delete__(self, obj):
        if self.read_only: raise AttributeError("Read-Only property.")
        del getattr(obj, self.attr)[self.key]


class cached_property(object):
    """ A property that is only computed once per instance and then replaces
        itself with an ordinary attribute. Deleting the attribute resets the
        property. """

    def __init__(self, func):
        self.__doc__ = getattr(func, '__doc__')
        self.func = func

    def __get__(self, obj, cls):
        if obj is None: return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


class lazy_attribute(object):
    """ A property that caches itself to the class object. """
    def __init__(self, func):
        functools.update_wrapper(self, func, updated=[])
        self.getter = func

    def __get__(self, obj, cls):
        value = self.getter(cls)
        setattr(cls, self.__name__, value)
        return value






###############################################################################
# Exceptions and Events ########################################################
###############################################################################


class BottleException(Exception):
    """ A base class for exceptions used by bottle. """
    pass






###############################################################################
# Routing ######################################################################
###############################################################################


class RouteError(BottleException):
    """ This is a base class for all routing related exceptions """


class RouteReset(BottleException):
    """ If raised by a plugin or request handler, the route is reset and all
        plugins are re-applied. """

class RouterUnknownModeError(RouteError): pass


class RouteSyntaxError(RouteError):
    """ The route parser found something not supported by this router. """


class RouteBuildError(RouteError):
    """ The route could not be built. """


def _re_flatten(p):
    """ Turn all capturing groups in a regular expression pattern into
        non-capturing groups. """
    if '(' not in p:
        return p
    return re.sub(r'(\\*)(\(\?P<[^>]+>|\((?!\?))',
        lambda m: m.group(0) if len(m.group(1)) % 2 else m.group(1) + '(?:', p)


class Router(object):
    """ A Router is an ordered collection of route->target pairs. It is used to
        efficiently match WSGI requests against a number of routes and return
        the first target that satisfies the request. The target may be anything,
        usually a string, ID or callable object. A route consists of a path-rule
        and a HTTP method.

        The path-rule is either a static path (e.g. `/contact`) or a dynamic
        path that contains wildcards (e.g. `/wiki/<page>`). The wildcard syntax
        and details on the matching order are described in docs:`routing`.
    """

    default_pattern = '[^/]+'
    default_filter  = 're'

    #: The current CPython regexp implementation does not allow more
    #: than 99 matching groups per regular expression.
    _MAX_GROUPS_PER_PATTERN = 99

    def __init__(self, strict=False):
        self.rules    = [] # All rules in order
        self._groups  = {} # index of regexes to find them in dyna_routes
        self.builder  = {} # Data structure for the url builder
        self.static   = {} # Search structure for static routes
        self.dyna_routes   = {}
        self.dyna_regexes  = {} # Search structure for dynamic routes
        #: If true, static routes are no longer checked first.
        self.strict_order = strict
        self.filters = {
            're':    lambda conf:
                (_re_flatten(conf or self.default_pattern), None, None),
            'int':   lambda conf: (r'-?\d+', int, lambda x: str(int(x))),
            'float': lambda conf: (r'-?[\d.]+', float, lambda x: str(float(x))),
            'path':  lambda conf: (r'.+?', None, None)}

    def add_filter(self, name, func):
        """ Add a filter. The provided function is called with the configuration
        string as parameter and must return a (regexp, to_python, to_url) tuple.
        The first element is a string, the last two are callables or None. """
        self.filters[name] = func

    rule_syntax = re.compile('(\\\\*)'
        '(?:(?::([a-zA-Z_][a-zA-Z_0-9]*)?()(?:#(.*?)#)?)'
          '|(?:<([a-zA-Z_][a-zA-Z_0-9]*)?(?::([a-zA-Z_]*)'
            '(?::((?:\\\\.|[^\\\\>]+)+)?)?)?>))')

    def _itertokens(self, rule):
        offset, prefix = 0, ''
        for match in self.rule_syntax.finditer(rule):
            prefix += rule[offset:match.start()]
            g = match.groups()
            if len(g[0])%2: # Escaped wildcard
                prefix += match.group(0)[len(g[0]):]
                offset = match.end()
                continue
            if prefix:
                yield prefix, None, None
            name, filtr, conf = g[4:7] if g[2] is None else g[1:4]
            yield name, filtr or 'default', conf or None
            offset, prefix = match.end(), ''
        if offset <= len(rule) or prefix:
            yield prefix+rule[offset:], None, None

    def add(self, rule, method, target, name=None):
        """ Add a new rule or replace the target for an existing rule. """
        anons     = 0    # Number of anonymous wildcards found
        keys      = []   # Names of keys
        pattern   = ''   # Regular expression pattern with named groups
        filters   = []   # Lists of wildcard input filters
        builder   = []   # Data structure for the URL builder
        is_static = True

        for key, mode, conf in self._itertokens(rule):
            if mode:
                is_static = False
                if mode == 'default': mode = self.default_filter
                mask, in_filter, out_filter = self.filters[mode](conf)
                if not key:
                    pattern += '(?:%s)' % mask
                    key = 'anon%d' % anons
                    anons += 1
                else:
                    pattern += '(?P<%s>%s)' % (key, mask)
                    keys.append(key)
                if in_filter: filters.append((key, in_filter))
                builder.append((key, out_filter or str))
            elif key:
                pattern += re.escape(key)
                builder.append((None, key))

        self.builder[rule] = builder
        if name: self.builder[name] = builder

        if is_static and not self.strict_order:
            self.static.setdefault(method, {})
            self.static[method][self.build(rule)] = (target, None)
            return

        try:
            re_pattern = re.compile('^(%s)$' % pattern)
            re_match = re_pattern.match
        except re.error:
            raise RouteSyntaxError("Could not add Route: %s (%s)" % (rule, _e()))

        if filters:
            def getargs(path):
                url_args = re_match(path).groupdict()
                for name, wildcard_filter in filters:
                    try:
                        url_args[name] = wildcard_filter(url_args[name])
                    except ValueError:
                        raise HTTPError(400, 'Path has wrong format.')
                return url_args
        elif re_pattern.groupindex:
            def getargs(path):
                return re_match(path).groupdict()
        else:
            getargs = None

        flatpat = _re_flatten(pattern)
        whole_rule = (rule, flatpat, target, getargs)

        if (flatpat, method) in self._groups:
            if DEBUG:
                msg = 'Route <%s %s> overwrites a previously defined route'
                warnings.warn(msg % (method, rule), RuntimeWarning)
            self.dyna_routes[method][self._groups[flatpat, method]] = whole_rule
        else:
            self.dyna_routes.setdefault(method, []).append(whole_rule)
            self._groups[flatpat, method] = len(self.dyna_routes[method]) - 1

        self._compile(method)

    def _compile(self, method):
        all_rules = self.dyna_routes[method]
        comborules = self.dyna_regexes[method] = []
        maxgroups = self._MAX_GROUPS_PER_PATTERN
        for x in range(0, len(all_rules), maxgroups):
            some = all_rules[x:x+maxgroups]
            combined = (flatpat for (_, flatpat, _, _) in some)
            combined = '|'.join('(^%s$)' % flatpat for flatpat in combined)
            combined = re.compile(combined).match
            rules = [(target, getargs) for (_, _, target, getargs) in some]
            comborules.append((combined, rules))

    def build(self, _name, *anons, **query):
        """ Build an URL by filling the wildcards in a rule. """
        builder = self.builder.get(_name)
        if not builder: raise RouteBuildError("No route with that name.", _name)
        try:
            for i, value in enumerate(anons): query['anon%d'%i] = value
            url = ''.join([f(query.pop(n)) if n else f for (n,f) in builder])
            return url if not query else url+'?'+urlencode(query)
        except KeyError:
            raise RouteBuildError('Missing URL argument: %r' % _e().args[0])

    def match(self, environ):
        """ Return a (target, url_agrs) tuple or raise HTTPError(400/404/405). """
        verb = environ['REQUEST_METHOD'].upper()
        path = environ['PATH_INFO'] or '/'

        if verb == 'HEAD':
            methods = ['PROXY', verb, 'GET', 'ANY']
        else:
            methods = ['PROXY', verb, 'ANY']

        for method in methods:
            if method in self.static and path in self.static[method]:
                target, getargs = self.static[method][path]
                return target, getargs(path) if getargs else {}
            elif method in self.dyna_regexes:
                for combined, rules in self.dyna_regexes[method]:
                    match = combined(path)
                    if match:
                        target, getargs = rules[match.lastindex - 1]
                        return target, getargs(path) if getargs else {}

        # No matching route found. Collect alternative methods for 405 response
        allowed = set([])
        nocheck = set(methods)
        for method in set(self.static) - nocheck:
            if path in self.static[method]:
                allowed.add(verb)
        for method in set(self.dyna_regexes) - allowed - nocheck:
            for combined, rules in self.dyna_regexes[method]:
                match = combined(path)
                if match:
                    allowed.add(method)
        if allowed:
            allow_header = ",".join(sorted(allowed))
            raise HTTPError(405, "Method not allowed.", Allow=allow_header)

        # No matching route and no alternative method found. We give up
        raise HTTPError(404, "Not found: " + repr(path))






class Route(object):
    """ This class wraps a route callback along with route specific metadata and
        configuration and applies Plugins on demand. It is also responsible for
        turing an URL path rule into a regular expression usable by the Router.
    """

    def __init__(self, app, rule, method, callback, name=None,
                 plugins=None, skiplist=None, **config):
        #: The application this route is installed to.
        self.app = app
        #: The path-rule string (e.g. ``/wiki/:page``).
        self.rule = rule
        #: The HTTP method as a string (e.g. ``GET``).
        self.method = method
        #: The original callback with no plugins applied. Useful for introspection.
        self.callback = callback
        #: The name of the route (if specified) or ``None``.
        self.name = name or None
        #: A list of route-specific plugins (see :meth:`Bottle.route`).
        self.plugins = plugins or []
        #: A list of plugins to not apply to this route (see :meth:`Bottle.route`).
        self.skiplist = skiplist or []
        #: Additional keyword arguments passed to the :meth:`Bottle.route`
        #: decorator are stored in this dictionary. Used for route-specific
        #: plugin configuration and meta-data.
        self.config = ConfigDict().load_dict(config)

    @cached_property
    def call(self):
        """ The route callback with all plugins applied. This property is
            created on demand and then cached to speed up subsequent requests."""
        return self._make_callback()

    def reset(self):
        """ Forget any cached values. The next time :attr:`call` is accessed,
            all plugins are re-applied. """
        self.__dict__.pop('call', None)

    def prepare(self):
        """ Do all on-demand work immediately (useful for debugging)."""
        self.call

    def all_plugins(self):
        """ Yield all Plugins affecting this route. """
        unique = set()
        for p in reversed(self.app.plugins + self.plugins):
            if True in self.skiplist: break
            name = getattr(p, 'name', False)
            if name and (name in self.skiplist or name in unique): continue
            if p in self.skiplist or type(p) in self.skiplist: continue
            if name: unique.add(name)
            yield p

    def _make_callback(self):
        callback = self.callback
        for plugin in self.all_plugins():
            try:
                if hasattr(plugin, 'apply'):
                    callback = plugin.apply(callback, self)
                else:
                    callback = plugin(callback)
            except RouteReset: # Try again with changed configuration.
                return self._make_callback()
            if not callback is self.callback:
                update_wrapper(callback, self.callback)
        return callback

    def get_undecorated_callback(self):
        """ Return the callback. If the callback is a decorated function, try to
            recover the original function. """
        func = self.callback
        func = getattr(func, '__func__' if py3k else 'im_func', func)
        closure_attr = '__closure__' if py3k else 'func_closure'
        while hasattr(func, closure_attr) and getattr(func, closure_attr):
            func = getattr(func, closure_attr)[0].cell_contents
        return func

    def get_callback_args(self):
        """ Return a list of argument names the callback (most likely) accepts
            as keyword arguments. If the callback is a decorated function, try
            to recover the original function before inspection. """
        return getargspec(self.get_undecorated_callback())[0]

    def get_config(self, key, default=None):
        """ Lookup a config field and return its value, first checking the
            route.config, then route.app.config."""
        for conf in (self.config, self.app.conifg):
            if key in conf: return conf[key]
        return default

    def __repr__(self):
        cb = self.get_undecorated_callback()
        return '<%s %r %r>' % (self.method, self.rule, cb)






###############################################################################
# Application Object ###########################################################
###############################################################################


class Bottle(object):
    """ Each Bottle object represents a single, distinct web application and
        consists of routes, callbacks, plugins, resources and configuration.
        Instances are callable WSGI applications.

        :param catchall: If true (default), handle all exceptions. Turn off to
                         let debugging middleware handle exceptions.
    """

    def __init__(self, catchall=True, autojson=True):

        #: A :class:`ConfigDict` for app specific configuration.
        self.config = ConfigDict()
        self.config._on_change = functools.partial(self.trigger_hook, 'config')
        self.config.meta_set('autojson', 'validate', bool)
        self.config.meta_set('catchall', 'validate', bool)
        self.config['catchall'] = catchall
        self.config['autojson'] = autojson

        #: A :class:`ResourceManager` for application files
        self.resources = ResourceManager()

        self.routes = [] # List of installed :class:`Route` instances.
        self.router = Router() # Maps requests to :class:`Route` instances.
        self.error_handler = {}

        # Core plugins
        self.plugins = [] # List of installed plugins.
        if self.config['autojson']:
            self.install(JSONPlugin())
        self.install(TemplatePlugin())

    #: If true, most exceptions are caught and returned as :exc:`HTTPError`
    catchall = DictProperty('config', 'catchall')

    __hook_names = 'before_request', 'after_request', 'app_reset', 'config'
    __hook_reversed = 'after_request'

    @cached_property
    def _hooks(self):
        return dict((name, []) for name in self.__hook_names)

    def add_hook(self, name, func):
        """ Attach a callback to a hook. Three hooks are currently implemented:

            before_request
                Executed once before each request. The request context is
                available, but no routing has happened yet.
            after_request
                Executed once after each request regardless of its outcome.
            app_reset
                Called whenever :meth:`Bottle.reset` is called.
        """
        if name in self.__hook_reversed:
            self._hooks[name].insert(0, func)
        else:
            self._hooks[name].append(func)

    def remove_hook(self, name, func):
        """ Remove a callback from a hook. """
        if name in self._hooks and func in self._hooks[name]:
            self._hooks[name].remove(func)
            return True

    def trigger_hook(self, __name, *args, **kwargs):
        """ Trigger a hook and return a list of results. """
        return [hook(*args, **kwargs) for hook in self._hooks[__name][:]]

    def hook(self, name):
        """ Return a decorator that attaches a callback to a hook. See
            :meth:`add_hook` for details."""
        def decorator(func):
            self.add_hook(name, func)
            return func
        return decorator

    def mount(self, prefix, app, **options):
        """ Mount an application (:class:`Bottle` or plain WSGI) to a specific
            URL prefix. Example::

                root_app.mount('/admin/', admin_app)

            :param prefix: path prefix or `mount-point`. If it ends in a slash,
                that slash is mandatory.
            :param app: an instance of :class:`Bottle` or a WSGI application.

            All other parameters are passed to the underlying :meth:`route` call.
        """

        segments = [p for p in prefix.split('/') if p]
        if not segments: raise ValueError('Empty path prefix.')
        path_depth = len(segments)

        def mountpoint_wrapper():
            try:
                request.path_shift(path_depth)
                rs = HTTPResponse([])
                def start_response(status, headerlist, exc_info=None):
                    if exc_info:
                        _raise(*exc_info)
                    rs.status = status
                    for name, value in headerlist: rs.add_header(name, value)
                    return rs.body.append
                body = app(request.environ, start_response)
                if body and rs.body: body = itertools.chain(rs.body, body)
                rs.body = body or rs.body
                return rs
            finally:
                request.path_shift(-path_depth)

        options.setdefault('skip', True)
        options.setdefault('method', 'PROXY')
        options.setdefault('mountpoint', {'prefix': prefix, 'target': app})
        options['callback'] = mountpoint_wrapper

        self.route('/%s/<:re:.*>' % '/'.join(segments), **options)
        if not prefix.endswith('/'):
            self.route('/' + '/'.join(segments), **options)

    def merge(self, routes):
        """ Merge the routes of another :class:`Bottle` application or a list of
            :class:`Route` objects into this application. The routes keep their
            'owner', meaning that the :data:`Route.app` attribute is not
            changed. """
        if isinstance(routes, Bottle):
            routes = routes.routes
        for route in routes:
            self.add_route(route)

    def install(self, plugin):
        """ Add a plugin to the list of plugins and prepare it for being
            applied to all routes of this application. A plugin may be a simple
            decorator or an object that implements the :class:`Plugin` API.
        """
        if hasattr(plugin, 'setup'): plugin.setup(self)
        if not callable(plugin) and not hasattr(plugin, 'apply'):
            raise TypeError("Plugins must be callable or implement .apply()")
        self.plugins.append(plugin)
        self.reset()
        return plugin

    def uninstall(self, plugin):
        """ Uninstall plugins. Pass an instance to remove a specific plugin, a type
            object to remove all plugins that match that type, a string to remove
            all plugins with a matching ``name`` attribute or ``True`` to remove all
            plugins. Return the list of removed plugins. """
        removed, remove = [], plugin
        for i, plugin in list(enumerate(self.plugins))[::-1]:
            if remove is True or remove is plugin or remove is type(plugin) \
            or getattr(plugin, 'name', True) == remove:
                removed.append(plugin)
                del self.plugins[i]
                if hasattr(plugin, 'close'): plugin.close()
        if removed: self.reset()
        return removed

    def reset(self, route=None):
        """ Reset all routes (force plugins to be re-applied) and clear all
            caches. If an ID or route object is given, only that specific route
            is affected. """
        if route is None: routes = self.routes
        elif isinstance(route, Route): routes = [route]
        else: routes = [self.routes[route]]
        for route in routes: route.reset()
        if DEBUG:
            for route in routes: route.prepare()
        self.trigger_hook('app_reset')

    def close(self):
        """ Close the application and all installed plugins. """
        for plugin in self.plugins:
            if hasattr(plugin, 'close'): plugin.close()

    def run(self, **kwargs):
        """ Calls :func:`run` with the same parameters. """
        run(self, **kwargs)

    def match(self, environ):
        """ Search for a matching route and return a (:class:`Route` , urlargs)
            tuple. The second value is a dictionary with parameters extracted
            from the URL. Raise :exc:`HTTPError` (404/405) on a non-match."""
        return self.router.match(environ)

    def get_url(self, routename, **kargs):
        """ Return a string that matches a named route """
        scriptname = request.environ.get('SCRIPT_NAME', '').strip('/') + '/'
        location = self.router.build(routename, **kargs).lstrip('/')
        return urljoin(urljoin('/', scriptname), location)

    def add_route(self, route):
        """ Add a route object, but do not change the :data:`Route.app`
            attribute."""
        self.routes.append(route)
        self.router.add(route.rule, route.method, route, name=route.name)
        if DEBUG: route.prepare()

    def route(self, path=None, method='GET', callback=None, name=None,
              apply=None, skip=None, **config):
        """ A decorator to bind a function to a request URL. Example::

                @app.route('/hello/:name')
                def hello(name):
                    return 'Hello %s' % name

            The ``:name`` part is a wildcard. See :class:`Router` for syntax
            details.

            :param path: Request path or a list of paths to listen to. If no
              path is specified, it is automatically generated from the
              signature of the function.
            :param method: HTTP method (`GET`, `POST`, `PUT`, ...) or a list of
              methods to listen to. (default: `GET`)
            :param callback: An optional shortcut to avoid the decorator
              syntax. ``route(..., callback=func)`` equals ``route(...)(func)``
            :param name: The name for this route. (default: None)
            :param apply: A decorator or plugin or a list of plugins. These are
              applied to the route callback in addition to installed plugins.
            :param skip: A list of plugins, plugin classes or names. Matching
              plugins are not installed to this route. ``True`` skips all.

            Any additional keyword arguments are stored as route-specific
            configuration and passed to plugins (see :meth:`Plugin.apply`).
        """
        if callable(path): path, callback = None, path
        plugins = makelist(apply)
        skiplist = makelist(skip)
        def decorator(callback):
            if isinstance(callback, basestring): callback = load(callback)
            for rule in makelist(path) or yieldroutes(callback):
                for verb in makelist(method):
                    verb = verb.upper()
                    route = Route(self, rule, verb, callback, name=name,
                                  plugins=plugins, skiplist=skiplist, **config)
                    self.add_route(route)
            return callback
        return decorator(callback) if callback else decorator

    def get(self, path=None, method='GET', **options):
        """ Equals :meth:`route`. """
        return self.route(path, method, **options)

    def post(self, path=None, method='POST', **options):
        """ Equals :meth:`route` with a ``POST`` method parameter. """
        return self.route(path, method, **options)

    def put(self, path=None, method='PUT', **options):
        """ Equals :meth:`route` with a ``PUT`` method parameter. """
        return self.route(path, method, **options)

    def delete(self, path=None, method='DELETE', **options):
        """ Equals :meth:`route` with a ``DELETE`` method parameter. """
        return self.route(path, method, **options)

    def patch(self, path=None, method='PATCH', **options):
        """ Equals :meth:`route` with a ``PATCH`` method parameter. """
        return self.route(path, method, **options)

    def error(self, code=500):
        """ Decorator: Register an output handler for a HTTP error code"""
        def wrapper(handler):
            self.error_handler[int(code)] = handler
            return handler
        return wrapper

    def default_error_handler(self, res):
        return tob(template(ERROR_PAGE_TEMPLATE, e=res))

    def _handle(self, environ):
        path = environ['bottle.raw_path'] = environ['PATH_INFO']
        if py3k:
            try:
                environ['PATH_INFO'] = path.encode('latin1').decode('utf8')
            except UnicodeError:
                return HTTPError(400, 'Invalid path string. Expected UTF-8')

        try:
            environ['bottle.app'] = self
            request.bind(environ)
            response.bind()
            try:
                self.trigger_hook('before_request')
                route, args = self.router.match(environ)
                environ['route.handle'] = route
                environ['bottle.route'] = route
                environ['route.url_args'] = args
                return route.call(**args)
            finally:
                self.trigger_hook('after_request')
        except HTTPResponse:
            return _e()
        except RouteReset:
            route.reset()
            return self._handle(environ)
        except (KeyboardInterrupt, SystemExit, MemoryError):
            raise
        except Exception:
            if not self.catchall: raise
            stacktrace = format_exc()
            environ['wsgi.errors'].write(stacktrace)
            return HTTPError(500, "Internal Server Error", _e(), stacktrace)

    def _cast(self, out, peek=None):
        """ Try to convert the parameter into something WSGI compatible and set
        correct HTTP headers when possible.
        Support: False, str, unicode, dict, HTTPResponse, HTTPError, file-like,
        iterable of strings and iterable of unicodes
        """

        # Empty output is done here
        if not out:
            if 'Content-Length' not in response:
                response['Content-Length'] = 0
            return []
        # Join lists of byte or unicode strings. Mixed lists are NOT supported
        if isinstance(out, (tuple, list))\
        and isinstance(out[0], (bytes, unicode)):
            out = out[0][0:0].join(out) # b'abc'[0:0] -> b''
        # Encode unicode strings
        if isinstance(out, unicode):
            out = out.encode(response.charset)
        # Byte Strings are just returned
        if isinstance(out, bytes):
            if 'Content-Length' not in response:
                response['Content-Length'] = len(out)
            return [out]
        # HTTPError or HTTPException (recursive, because they may wrap anything)
        # TODO: Handle these explicitly in handle() or make them iterable.
        if isinstance(out, HTTPError):
            out.apply(response)
            out = self.error_handler.get(out.status_code, self.default_error_handler)(out)
            return self._cast(out)
        if isinstance(out, HTTPResponse):
            out.apply(response)
            return self._cast(out.body)

        # File-like objects.
        if hasattr(out, 'read'):
            if 'wsgi.file_wrapper' in request.environ:
                return request.environ['wsgi.file_wrapper'](out)
            elif hasattr(out, 'close') or not hasattr(out, '__iter__'):
                return WSGIFileWrapper(out)

        # Handle Iterables. We peek into them to detect their inner type.
        try:
            iout = iter(out)
            first = next(iout)
            while not first:
                first = next(iout)
        except StopIteration:
            return self._cast('')
        except HTTPResponse:
            first = _e()
        except (KeyboardInterrupt, SystemExit, MemoryError):
            raise
        except:
            if not self.catchall: raise
            first = HTTPError(500, 'Unhandled exception', _e(), format_exc())

        # These are the inner types allowed in iterator or generator objects.
        if isinstance(first, HTTPResponse):
            return self._cast(first)
        elif isinstance(first, bytes):
            new_iter = itertools.chain([first], iout)
        elif isinstance(first, unicode):
            encoder = lambda x: x.encode(response.charset)
            new_iter = imap(encoder, itertools.chain([first], iout))
        else:
            msg = 'Unsupported response type: %s' % type(first)
            return self._cast(HTTPError(500, msg))
        if hasattr(out, 'close'):
            new_iter = _closeiter(new_iter, out.close)
        return new_iter

    def wsgi(self, environ, start_response):
        """ The bottle WSGI-interface. """
        try:
            out = self._cast(self._handle(environ))
            # rfc2616 section 4.3
            if response._status_code in (100, 101, 204, 304)\
            or environ['REQUEST_METHOD'] == 'HEAD':
                if hasattr(out, 'close'): out.close()
                out = []
            start_response(response._status_line, response.headerlist)
            return out
        except (KeyboardInterrupt, SystemExit, MemoryError):
            raise
        except:
            if not self.catchall: raise
            err = '<h1>Critical error while processing request: %s</h1>' \
                  % html_escape(environ.get('PATH_INFO', '/'))
            if DEBUG:
                err += '<h2>Error:</h2>\n<pre>\n%s\n</pre>\n' \
                       '<h2>Traceback:</h2>\n<pre>\n%s\n</pre>\n' \
                       % (html_escape(repr(_e())), html_escape(format_exc()))
            environ['wsgi.errors'].write(err)
            headers = [('Content-Type', 'text/html; charset=UTF-8')]
            start_response('500 INTERNAL SERVER ERROR', headers, sys.exc_info())
            return [tob(err)]

    def __call__(self, environ, start_response):
        """ Each instance of :class:'Bottle' is a WSGI application. """
        return self.wsgi(environ, start_response)

    def __enter__(self):
        """ Use this application as default for all module-level shortcuts. """
        default_app.push(self)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        default_app.pop()





###############################################################################
# HTTP and WSGI Tools ##########################################################
###############################################################################

class BaseRequest(object):
    """ A wrapper for WSGI environment dictionaries that adds a lot of
        convenient access methods and properties. Most of them are read-only.

        Adding new attributes to a request actually adds them to the environ
        dictionary (as 'bottle.request.ext.<name>'). This is the recommended
        way to store and access request-specific data.
    """

    __slots__ = ('environ', )

    #: Maximum size of memory buffer for :attr:`body` in bytes.
    MEMFILE_MAX = 102400

    def __init__(self, environ=None):
        """ Wrap a WSGI environ dictionary. """
        #: The wrapped WSGI environ dictionary. This is the only real attribute.
        #: All other attributes actually are read-only properties.
        self.environ = {} if environ is None else environ
        self.environ['bottle.request'] = self

    @DictProperty('environ', 'bottle.app', read_only=True)
    def app(self):
        """ Bottle application handling this request. """
        raise RuntimeError('This request is not connected to an application.')

    @DictProperty('environ', 'bottle.route', read_only=True)
    def route(self):
        """ The bottle :class:`Route` object that matches this request. """
        raise RuntimeError('This request is not connected to a route.')

    @DictProperty('environ', 'route.url_args', read_only=True)
    def url_args(self):
        """ The arguments extracted from the URL. """
        raise RuntimeError('This request is not connected to a route.')

    @property
    def path(self):
        """ The value of ``PATH_INFO`` with exactly one prefixed slash (to fix
            broken clients and avoid the "empty path" edge case). """
        return '/' + self.environ.get('PATH_INFO','').lstrip('/')

    @property
    def method(self):
        """ The ``REQUEST_METHOD`` value as an uppercase string. """
        return self.environ.get('REQUEST_METHOD', 'GET').upper()

    @DictProperty('environ', 'bottle.request.headers', read_only=True)
    def headers(self):
        """ A :class:`WSGIHeaderDict` that provides case-insensitive access to
            HTTP request headers. """
        return WSGIHeaderDict(self.environ)

    def get_header(self, name, default=None):
        """ Return the value of a request header, or a given default value. """
        return self.headers.get(name, default)

    @DictProperty('environ', 'bottle.request.cookies', read_only=True)
    def cookies(self):
        """ Cookies parsed into a :class:`FormsDict`. Signed cookies are NOT
            decoded. Use :meth:`get_cookie` if you expect signed cookies. """
        cookies = SimpleCookie(self.environ.get('HTTP_COOKIE','')).values()
        return FormsDict((c.key, c.value) for c in cookies)

    def get_cookie(self, key, default=None, secret=None):
        """ Return the content of a cookie. To read a `Signed Cookie`, the
            `secret` must match the one used to create the cookie (see
            :meth:`BaseResponse.set_cookie`). If anything goes wrong (missing
            cookie or wrong signature), return a default value. """
        value = self.cookies.get(key)
        if secret and value:
            dec = cookie_decode(value, secret) # (key, value) tuple or None
            return dec[1] if dec and dec[0] == key else default
        return value or default

    @DictProperty('environ', 'bottle.request.query', read_only=True)
    def query(self):
        """ The :attr:`query_string` parsed into a :class:`FormsDict`. These
            values are sometimes called "URL arguments" or "GET parameters", but
            not to be confused with "URL wildcards" as they are provided by the
            :class:`Router`. """
        get = self.environ['bottle.get'] = FormsDict()
        pairs = _parse_qsl(self.environ.get('QUERY_STRING', ''))
        for key, value in pairs:
            get[key] = value
        return get

    @DictProperty('environ', 'bottle.request.forms', read_only=True)
    def forms(self):
        """ Form values parsed from an `url-encoded` or `multipart/form-data`
            encoded POST or PUT request body. The result is returned as a
            :class:`FormsDict`. All keys and values are strings. File uploads
            are stored separately in :attr:`files`. """
        forms = FormsDict()
        for name, item in self.POST.allitems():
            if not isinstance(item, FileUpload):
                forms[name] = item
        return forms

    @DictProperty('environ', 'bottle.request.params', read_only=True)
    def params(self):
        """ A :class:`FormsDict` with the combined values of :attr:`query` and
            :attr:`forms`. File uploads are stored in :attr:`files`. """
        params = FormsDict()
        for key, value in self.query.allitems():
            params[key] = value
        for key, value in self.forms.allitems():
            params[key] = value
        return params

    @DictProperty('environ', 'bottle.request.files', read_only=True)
    def files(self):
        """ File uploads parsed from `multipart/form-data` encoded POST or PUT
            request body. The values are instances of :class:`FileUpload`.

        """
        files = FormsDict()
        for name, item in self.POST.allitems():
            if isinstance(item, FileUpload):
                files[name] = item
        return files

    @DictProperty('environ', 'bottle.request.json', read_only=True)
    def json(self):
        """ If the ``Content-Type`` header is ``application/json``, this
            property holds the parsed content of the request body. Only requests
            smaller than :attr:`MEMFILE_MAX` are processed to avoid memory
            exhaustion. """
        ctype = self.environ.get('CONTENT_TYPE', '').lower().split(';')[0]
        if ctype == 'application/json':
            b = self._get_body_string()
            if not b:
                return None
            return json_loads(b)
        return None

    def _iter_body(self, read, bufsize):
        maxread = max(0, self.content_length)
        while maxread:
            part = read(min(maxread, bufsize))
            if not part: break
            yield part
            maxread -= len(part)

    @staticmethod
    def _iter_chunked(read, bufsize):
        err = HTTPError(400, 'Error while parsing chunked transfer body.')
        rn, sem, bs = tob('\r\n'), tob(';'), tob('')
        while True:
            header = read(1)
            while header[-2:] != rn:
                c = read(1)
                header += c
                if not c: raise err
                if len(header) > bufsize: raise err
            size, _, _ = header.partition(sem)
            try:
                maxread = int(tonat(size.strip()), 16)
            except ValueError:
                raise err
            if maxread == 0: break
            buff = bs
            while maxread > 0:
                if not buff:
                    buff = read(min(maxread, bufsize))
                part, buff = buff[:maxread], buff[maxread:]
                if not part: raise err
                yield part
                maxread -= len(part)
            if read(2) != rn:
                raise err
            
    @DictProperty('environ', 'bottle.request.body', read_only=True)
    def _body(self):
        body_iter = self._iter_chunked if self.chunked else self._iter_body
        read_func = self.environ['wsgi.input'].read
        body, body_size, is_temp_file = BytesIO(), 0, False
        for part in body_iter(read_func, self.MEMFILE_MAX):
            body.write(part)
            body_size += len(part)
            if not is_temp_file and body_size > self.MEMFILE_MAX:
                body, tmp = TemporaryFile(mode='w+b'), body
                body.write(tmp.getvalue())
                del tmp
                is_temp_file = True
        self.environ['wsgi.input'] = body
        body.seek(0)
        return body

    def _get_body_string(self):
        """ read body until content-length or MEMFILE_MAX into a string. Raise
            HTTPError(413) on requests that are to large. """
        clen = self.content_length
        if clen > self.MEMFILE_MAX:
            raise HTTPError(413, 'Request to large')
        if clen < 0: clen = self.MEMFILE_MAX + 1
        data = self.body.read(clen)
        if len(data) > self.MEMFILE_MAX: # Fail fast
            raise HTTPError(413, 'Request to large')
        return data

    @property
    def body(self):
        """ The HTTP request body as a seek-able file-like object. Depending on
            :attr:`MEMFILE_MAX`, this is either a temporary file or a
            :class:`io.BytesIO` instance. Accessing this property for the first
            time reads and replaces the ``wsgi.input`` environ variable.
            Subsequent accesses just do a `seek(0)` on the file object. """
        self._body.seek(0)
        return self._body

    @property
    def chunked(self):
        """ True if Chunked transfer encoding was. """
        return 'chunked' in self.environ.get('HTTP_TRANSFER_ENCODING', '').lower()

    #: An alias for :attr:`query`.
    GET = query

    @DictProperty('environ', 'bottle.request.post', read_only=True)
    def POST(self):
        """ The values of :attr:`forms` and :attr:`files` combined into a single
            :class:`FormsDict`. Values are either strings (form values) or
            instances of :class:`cgi.FieldStorage` (file uploads).
        """
        post = FormsDict()
        # We default to application/x-www-form-urlencoded for everything that
        # is not multipart and take the fast path (also: 3.1 workaround)
        if not self.content_type.startswith('multipart/'):
            pairs = _parse_qsl(tonat(self._get_body_string(), 'latin1'))
            for key, value in pairs:
                post[key] = value
            return post

        safe_env = {'QUERY_STRING':''} # Build a safe environment for cgi
        for key in ('REQUEST_METHOD', 'CONTENT_TYPE', 'CONTENT_LENGTH'):
            if key in self.environ: safe_env[key] = self.environ[key]
        args = dict(fp=self.body, environ=safe_env, keep_blank_values=True)
        if py31:
            args['fp'] = NCTextIOWrapper(args['fp'], encoding='utf8',
                                         newline='\n')
        elif py3k:
            args['encoding'] = 'utf8'
        data = cgi.FieldStorage(**args)
        self['_cgi.FieldStorage'] = data #http://bugs.python.org/issue18394#msg207958
        data = data.list or []
        for item in data:
            if item.filename:
                post[item.name] = FileUpload(item.file, item.name,
                                             item.filename, item.headers)
            else:
                post[item.name] = item.value
        return post

    @property
    def url(self):
        """ The full request URI including hostname and scheme. If your app
            lives behind a reverse proxy or load balancer and you get confusing
            results, make sure that the ``X-Forwarded-Host`` header is set
            correctly. """
        return self.urlparts.geturl()

    @DictProperty('environ', 'bottle.request.urlparts', read_only=True)
    def urlparts(self):
        """ The :attr:`url` string as an :class:`urlparse.SplitResult` tuple.
            The tuple contains (scheme, host, path, query_string and fragment),
            but the fragment is always empty because it is not visible to the
            server. """
        env = self.environ
        http = env.get('HTTP_X_FORWARDED_PROTO') or env.get('wsgi.url_scheme', 'http')
        host = env.get('HTTP_X_FORWARDED_HOST') or env.get('HTTP_HOST')
        if not host:
            # HTTP 1.1 requires a Host-header. This is for HTTP/1.0 clients.
            host = env.get('SERVER_NAME', '127.0.0.1')
            port = env.get('SERVER_PORT')
            if port and port != ('80' if http == 'http' else '443'):
                host += ':' + port
        path = urlquote(self.fullpath)
        return UrlSplitResult(http, host, path, env.get('QUERY_STRING'), '')

    @property
    def fullpath(self):
        """ Request path including :attr:`script_name` (if present). """
        return urljoin(self.script_name, self.path.lstrip('/'))

    @property
    def query_string(self):
        """ The raw :attr:`query` part of the URL (everything in between ``?``
            and ``#``) as a string. """
        return self.environ.get('QUERY_STRING', '')

    @property
    def script_name(self):
        """ The initial portion of the URL's `path` that was removed by a higher
            level (server or routing middleware) before the application was
            called. This script path is returned with leading and tailing
            slashes. """
        script_name = self.environ.get('SCRIPT_NAME', '').strip('/')
        return '/' + script_name + '/' if script_name else '/'

    def path_shift(self, shift=1):
        """ Shift path segments from :attr:`path` to :attr:`script_name` and
            vice versa.

           :param shift: The number of path segments to shift. May be negative
                         to change the shift direction. (default: 1)
        """
        script = self.environ.get('SCRIPT_NAME','/')
        self['SCRIPT_NAME'], self['PATH_INFO'] = path_shift(script, self.path, shift)

    @property
    def content_length(self):
        """ The request body length as an integer. The client is responsible to
            set this header. Otherwise, the real length of the body is unknown
            and -1 is returned. In this case, :attr:`body` will be empty. """
        return int(self.environ.get('CONTENT_LENGTH') or -1)

    @property
    def content_type(self):
        """ The Content-Type header as a lowercase-string (default: empty). """
        return self.environ.get('CONTENT_TYPE', '').lower()

    @property
    def is_xhr(self):
        """ True if the request was triggered by a XMLHttpRequest. This only
            works with JavaScript libraries that support the `X-Requested-With`
            header (most of the popular libraries do). """
        requested_with = self.environ.get('HTTP_X_REQUESTED_WITH','')
        return requested_with.lower() == 'xmlhttprequest'

    @property
    def is_ajax(self):
        """ Alias for :attr:`is_xhr`. "Ajax" is not the right term. """
        return self.is_xhr

    @property
    def auth(self):
        """ HTTP authentication data as a (user, password) tuple. This
            implementation currently supports basic (not digest) authentication
            only. If the authentication happened at a higher level (e.g. in the
            front web-server or a middleware), the password field is None, but
            the user field is looked up from the ``REMOTE_USER`` environ
            variable. On any errors, None is returned. """
        basic = parse_auth(self.environ.get('HTTP_AUTHORIZATION',''))
        if basic: return basic
        ruser = self.environ.get('REMOTE_USER')
        if ruser: return (ruser, None)
        return None

    @property
    def remote_route(self):
        """ A list of all IPs that were involved in this request, starting with
            the client IP and followed by zero or more proxies. This does only
            work if all proxies support the ```X-Forwarded-For`` header. Note
            that this information can be forged by malicious clients. """
        proxy = self.environ.get('HTTP_X_FORWARDED_FOR')
        if proxy: return [ip.strip() for ip in proxy.split(',')]
        remote = self.environ.get('REMOTE_ADDR')
        return [remote] if remote else []

    @property
    def remote_addr(self):
        """ The client IP as a string. Note that this information can be forged
            by malicious clients. """
        route = self.remote_route
        return route[0] if route else None

    def copy(self):
        """ Return a new :class:`Request` with a shallow :attr:`environ` copy. """
        return Request(self.environ.copy())

    def get(self, value, default=None): return self.environ.get(value, default)
    def __getitem__(self, key): return self.environ[key]
    def __delitem__(self, key): self[key] = ""; del(self.environ[key])
    def __iter__(self): return iter(self.environ)
    def __len__(self): return len(self.environ)
    def keys(self): return self.environ.keys()
    def __setitem__(self, key, value):
        """ Change an environ value and clear all caches that depend on it. """

        if self.environ.get('bottle.request.readonly'):
            raise KeyError('The environ dictionary is read-only.')

        self.environ[key] = value
        todelete = ()

        if key == 'wsgi.input':
            todelete = ('body', 'forms', 'files', 'params', 'post', 'json')
        elif key == 'QUERY_STRING':
            todelete = ('query', 'params')
        elif key.startswith('HTTP_'):
            todelete = ('headers', 'cookies')

        for key in todelete:
            self.environ.pop('bottle.request.'+key, None)

    def __repr__(self):
        return '<%s: %s %s>' % (self.__class__.__name__, self.method, self.url)

    def __getattr__(self, name):
        """ Search in self.environ for additional user defined attributes. """
        try:
            var = self.environ['bottle.request.ext.%s'%name]
            return var.__get__(self) if hasattr(var, '__get__') else var
        except KeyError:
            raise AttributeError('Attribute %r not defined.' % name)

    def __setattr__(self, name, value):
        if name == 'environ': return object.__setattr__(self, name, value)
        self.environ['bottle.request.ext.%s'%name] = value




def _hkey(s):
    return s.title().replace('_','-')


class HeaderProperty(object):
    def __init__(self, name, reader=None, writer=str, default=''):
        self.name, self.default = name, default
        self.reader, self.writer = reader, writer
        self.__doc__ = 'Current value of the %r header.' % name.title()

    def __get__(self, obj, _):
        if obj is None: return self
        value = obj.headers.get(self.name, self.default)
        return self.reader(value) if self.reader else value

    def __set__(self, obj, value):
        obj.headers[self.name] = self.writer(value)

    def __delete__(self, obj):
        del obj.headers[self.name]


class BaseResponse(object):
    """ Storage class for a response body as well as headers and cookies.

        This class does support dict-like case-insensitive item-access to
        headers, but is NOT a dict. Most notably, iterating over a response
        yields parts of the body and not the headers.

        :param body: The response body as one of the supported types.
        :param status: Either an HTTP status code (e.g. 200) or a status line
                       including the reason phrase (e.g. '200 OK').
        :param headers: A dictionary or a list of name-value pairs.

        Additional keyword arguments are added to the list of headers.
        Underscores in the header name are replaced with dashes.
    """

    default_status = 200
    default_content_type = 'text/html; charset=UTF-8'

    # Header blacklist for specific response codes
    # (rfc2616 section 10.2.3 and 10.3.5)
    bad_headers = {
        204: set(('Content-Type',)),
        304: set(('Allow', 'Content-Encoding', 'Content-Language',
                  'Content-Length', 'Content-Range', 'Content-Type',
                  'Content-Md5', 'Last-Modified'))}

    def __init__(self, body='', status=None, headers=None, **more_headers):
        self._cookies = None
        self._headers = {}
        self.body = body
        self.status = status or self.default_status
        if headers:
            if isinstance(headers, dict):
                headers = headers.items()
            for name, value in headers:
                self.add_header(name, value)
        if more_headers:
            for name, value in more_headers.items():
                self.add_header(name, value)

    def copy(self, cls=None):
        """ Returns a copy of self. """
        cls = cls or BaseResponse
        assert issubclass(cls, BaseResponse)
        copy = cls()
        copy.status = self.status
        copy._headers = dict((k, v[:]) for (k, v) in self._headers.items())
        if self._cookies:
            copy._cookies = SimpleCookie()
            copy._cookies.load(self._cookies.output())
        return copy

    def __iter__(self):
        return iter(self.body)

    def close(self):
        if hasattr(self.body, 'close'):
            self.body.close()

    @property
    def status_line(self):
        """ The HTTP status line as a string (e.g. ``404 Not Found``)."""
        return self._status_line

    @property
    def status_code(self):
        """ The HTTP status code as an integer (e.g. 404)."""
        return self._status_code

    def _set_status(self, status):
        if isinstance(status, int):
            code, status = status, _HTTP_STATUS_LINES.get(status)
        elif ' ' in status:
            status = status.strip()
            code   = int(status.split()[0])
        else:
            raise ValueError('String status line without a reason phrase.')
        if not 100 <= code <= 999: raise ValueError('Status code out of range.')
        self._status_code = code
        self._status_line = str(status or ('%d Unknown' % code))

    def _get_status(self):
        return self._status_line

    status = property(_get_status, _set_status, None,
        ''' A writeable property to change the HTTP response status. It accepts
            either a numeric code (100-999) or a string with a custom reason
            phrase (e.g. "404 Brain not found"). Both :data:`status_line` and
            :data:`status_code` are updated accordingly. The return value is
            always a status string. ''')
    del _get_status, _set_status

    @property
    def headers(self):
        """ An instance of :class:`HeaderDict`, a case-insensitive dict-like
            view on the response headers. """
        hdict = HeaderDict()
        hdict.dict = self._headers
        return hdict

    def __contains__(self, name): return _hkey(name) in self._headers
    def __delitem__(self, name):  del self._headers[_hkey(name)]
    def __getitem__(self, name):  return self._headers[_hkey(name)][-1]
    def __setitem__(self, name, value): self._headers[_hkey(name)] = [str(value)]

    def get_header(self, name, default=None):
        """ Return the value of a previously defined header. If there is no
            header with that name, return a default value. """
        return self._headers.get(_hkey(name), [default])[-1]

    def set_header(self, name, value):
        """ Create a new response header, replacing any previously defined
            headers with the same name. """
        self._headers[_hkey(name)] = [str(value)]

    def add_header(self, name, value):
        """ Add an additional response header, not removing duplicates. """
        self._headers.setdefault(_hkey(name), []).append(str(value))

    def iter_headers(self):
        """ Yield (header, value) tuples, skipping headers that are not
            allowed with the current response status code. """
        return self.headerlist

    @property
    def headerlist(self):
        """ WSGI conform list of (header, value) tuples. """
        out = []
        headers = list(self._headers.items())
        if 'Content-Type' not in self._headers:
            headers.append(('Content-Type', [self.default_content_type]))
        if self._status_code in self.bad_headers:
            bad_headers = self.bad_headers[self._status_code]
            headers = [h for h in headers if h[0] not in bad_headers]
        out += [(name, val) for name, vals in headers for val in vals]
        if self._cookies:
            for c in self._cookies.values():
                out.append(('Set-Cookie', c.OutputString()))
        return out

    content_type = HeaderProperty('Content-Type')
    content_length = HeaderProperty('Content-Length', reader=int)
    expires = HeaderProperty('Expires',
        reader=lambda x: datetime.utcfromtimestamp(parse_date(x)),
        writer=lambda x: http_date(x))

    @property
    def charset(self, default='UTF-8'):
        """ Return the charset specified in the content-type header (default: utf8). """
        if 'charset=' in self.content_type:
            return self.content_type.split('charset=')[-1].split(';')[0].strip()
        return default

    def set_cookie(self, name, value, secret=None, **options):
        """ Create a new cookie or replace an old one. If the `secret` parameter is
            set, create a `Signed Cookie` (described below).

            :param name: the name of the cookie.
            :param value: the value of the cookie.
            :param secret: a signature key required for signed cookies.

            Additionally, this method accepts all RFC 2109 attributes that are
            supported by :class:`cookie.Morsel`, including:

            :param max_age: maximum age in seconds. (default: None)
            :param expires: a datetime object or UNIX timestamp. (default: None)
            :param domain: the domain that is allowed to read the cookie.
              (default: current domain)
            :param path: limits the cookie to a given path (default: current path)
            :param secure: limit the cookie to HTTPS connections (default: off).
            :param httponly: prevents client-side javascript to read this cookie
              (default: off, requires Python 2.6 or newer).

            If neither `expires` nor `max_age` is set (default), the cookie will
            expire at the end of the browser session (as soon as the browser
            window is closed).

            Signed cookies may store any pickle-able object and are
            cryptographically signed to prevent manipulation. Keep in mind that
            cookies are limited to 4kb in most browsers.

            Warning: Signed cookies are not encrypted (the client can still see
            the content) and not copy-protected (the client can restore an old
            cookie). The main intention is to make pickling and unpickling
            save, not to store secret information at client side.
        """
        if not self._cookies:
            self._cookies = SimpleCookie()

        if secret:
            value = touni(cookie_encode((name, value), secret))
        elif not isinstance(value, basestring):
            raise TypeError('Secret key missing for non-string Cookie.')

        if len(value) > 4096: raise ValueError('Cookie value to long.')
        self._cookies[name] = value

        for key, value in options.items():
            if key == 'max_age':
                if isinstance(value, timedelta):
                    value = value.seconds + value.days * 24 * 3600
            if key == 'expires':
                if isinstance(value, (datedate, datetime)):
                    value = value.timetuple()
                elif isinstance(value, (int, float)):
                    value = time.gmtime(value)
                value = time.strftime("%a, %d %b %Y %H:%M:%S GMT", value)
            self._cookies[name][key.replace('_', '-')] = value

    def delete_cookie(self, key, **kwargs):
        """ Delete a cookie. Be sure to use the same `domain` and `path`
            settings as used to create the cookie. """
        kwargs['max_age'] = -1
        kwargs['expires'] = 0
        self.set_cookie(key, '', **kwargs)

    def __repr__(self):
        out = ''
        for name, value in self.headerlist:
            out += '%s: %s\n' % (name.title(), value.strip())
        return out


def _local_property():
    ls = threading.local()
    def fget(_):
        try: return ls.var
        except AttributeError:
            raise RuntimeError("Request context not initialized.")
    def fset(_, value): ls.var = value
    def fdel(_): del ls.var
    return property(fget, fset, fdel, 'Thread-local property')


class LocalRequest(BaseRequest):
    """ A thread-local subclass of :class:`BaseRequest` with a different
        set of attributes for each thread. There is usually only one global
        instance of this class (:data:`request`). If accessed during a
        request/response cycle, this instance always refers to the *current*
        request (even on a multithreaded server). """
    bind = BaseRequest.__init__
    environ = _local_property()


class LocalResponse(BaseResponse):
    """ A thread-local subclass of :class:`BaseResponse` with a different
        set of attributes for each thread. There is usually only one global
        instance of this class (:data:`response`). Its attributes are used
        to build the HTTP response at the end of the request/response cycle.
    """
    bind = BaseResponse.__init__
    _status_line = _local_property()
    _status_code = _local_property()
    _cookies     = _local_property()
    _headers     = _local_property()
    body         = _local_property()


Request = BaseRequest
Response = BaseResponse


class HTTPResponse(Response, BottleException):
    def __init__(self, body='', status=None, headers=None, **more_headers):
        super(HTTPResponse, self).__init__(body, status, headers, **more_headers)

    def apply(self, other):
        other._status_code = self._status_code
        other._status_line = self._status_line
        other._headers = self._headers
        other._cookies = self._cookies
        other.body = self.body


class HTTPError(HTTPResponse):
    default_status = 500
    def __init__(self, status=None, body=None, exception=None, traceback=None,
                 **options):
        self.exception = exception
        self.traceback = traceback
        super(HTTPError, self).__init__(body, status, **options)





###############################################################################
# Plugins ######################################################################
###############################################################################

class PluginError(BottleException): pass


class JSONPlugin(object):
    name = 'json'
    api  = 2

    def __init__(self, json_dumps=json_dumps):
        self.json_dumps = json_dumps

    def apply(self, callback, _):
        dumps = self.json_dumps
        if not dumps: return callback
        def wrapper(*a, **ka):
            try:
                rv = callback(*a, **ka)
            except HTTPError:
                rv = _e()

            if isinstance(rv, dict):
                #Attempt to serialize, raises exception on failure
                json_response = dumps(rv)
                #Set content type only if serialization successful
                response.content_type = 'application/json'
                return json_response
            elif isinstance(rv, HTTPResponse) and isinstance(rv.body, dict):
                rv.body = dumps(rv.body)
                rv.content_type = 'application/json'
            return rv

        return wrapper


class TemplatePlugin(object):
    """ This plugin applies the :func:`view` decorator to all routes with a
        `template` config parameter. If the parameter is a tuple, the second
        element must be a dict with additional options (e.g. `template_engine`)
        or default variables for the template. """
    name = 'template'
    api  = 2

    def apply(self, callback, route):
        conf = route.config.get('template')
        if isinstance(conf, (tuple, list)) and len(conf) == 2:
            return view(conf[0], **conf[1])(callback)
        elif isinstance(conf, str):
            return view(conf)(callback)
        else:
            return callback


#: Not a plugin, but part of the plugin API. TODO: Find a better place.
class _ImportRedirect(object):
    def __init__(self, name, impmask):
        """ Create a virtual package that redirects imports (see PEP 302). """
        self.name = name
        self.impmask = impmask
        self.module = sys.modules.setdefault(name, imp.new_module(name))
        self.module.__dict__.update({'__file__': __file__, '__path__': [],
                                    '__all__': [], '__loader__': self})
        sys.meta_path.append(self)

    def find_module(self, fullname, path=None):
        if '.' not in fullname: return
        packname = fullname.rsplit('.', 1)[0]
        if packname != self.name: return
        return self

    def load_module(self, fullname):
        if fullname in sys.modules: return sys.modules[fullname]
        modname = fullname.rsplit('.', 1)[1]
        realname = self.impmask % modname
        __import__(realname)
        module = sys.modules[fullname] = sys.modules[realname]
        setattr(self.module, modname, module)
        module.__loader__ = self
        return module






###############################################################################
# Common Utilities #############################################################
###############################################################################


class MultiDict(DictMixin):
    """ This dict stores multiple values per key, but behaves exactly like a
        normal dict in that it returns only the newest value for any given key.
        There are special methods available to access the full list of values.
    """

    def __init__(self, *a, **k):
        self.dict = dict((k, [v]) for (k, v) in dict(*a, **k).items())

    def __len__(self): return len(self.dict)
    def __iter__(self): return iter(self.dict)
    def __contains__(self, key): return key in self.dict
    def __delitem__(self, key): del self.dict[key]
    def __getitem__(self, key): return self.dict[key][-1]
    def __setitem__(self, key, value): self.append(key, value)
    def keys(self): return self.dict.keys()

    if py3k:
        def values(self): return (v[-1] for v in self.dict.values())
        def items(self): return ((k, v[-1]) for k, v in self.dict.items())
        def allitems(self):
            return ((k, v) for k, vl in self.dict.items() for v in vl)
        iterkeys = keys
        itervalues = values
        iteritems = items
        iterallitems = allitems

    else:
        def values(self): return [v[-1] for v in self.dict.values()]
        def items(self): return [(k, v[-1]) for k, v in self.dict.items()]
        def iterkeys(self): return self.dict.iterkeys()
        def itervalues(self): return (v[-1] for v in self.dict.itervalues())
        def iteritems(self):
            return ((k, v[-1]) for k, v in self.dict.iteritems())
        def iterallitems(self):
            return ((k, v) for k, vl in self.dict.iteritems() for v in vl)
        def allitems(self):
            return [(k, v) for k, vl in self.dict.iteritems() for v in vl]

    def get(self, key, default=None, index=-1, type=None):
        """ Return the most recent value for a key.

            :param default: The default value to be returned if the key is not
                   present or the type conversion fails.
            :param index: An index for the list of available values.
            :param type: If defined, this callable is used to cast the value
                    into a specific type. Exception are suppressed and result in
                    the default value to be returned.
        """
        try:
            val = self.dict[key][index]
            return type(val) if type else val
        except Exception:
            pass
        return default

    def append(self, key, value):
        """ Add a new value to the list of values for this key. """
        self.dict.setdefault(key, []).append(value)

    def replace(self, key, value):
        """ Replace the list of values with a single value. """
        self.dict[key] = [value]

    def getall(self, key):
        """ Return a (possibly empty) list of values for a key. """
        return self.dict.get(key) or []

    #: Aliases for WTForms to mimic other multi-dict APIs (Django)
    getone = get
    getlist = getall


class FormsDict(MultiDict):
    """ This :class:`MultiDict` subclass is used to store request form data.
        Additionally to the normal dict-like item access methods (which return
        unmodified data as native strings), this container also supports
        attribute-like access to its values. Attributes are automatically de-
        or recoded to match :attr:`input_encoding` (default: 'utf8'). Missing
        attributes default to an empty string. """

    #: Encoding used for attribute values.
    input_encoding = 'utf8'
    #: If true (default), unicode strings are first encoded with `latin1`
    #: and then decoded to match :attr:`input_encoding`.
    recode_unicode = True

    def _fix(self, s, encoding=None):
        if isinstance(s, unicode) and self.recode_unicode: # Python 3 WSGI
            return s.encode('latin1').decode(encoding or self.input_encoding)
        elif isinstance(s, bytes): # Python 2 WSGI
            return s.decode(encoding or self.input_encoding)
        else:
            return s

    def decode(self, encoding=None):
        """ Returns a copy with all keys and values de- or recoded to match
            :attr:`input_encoding`. Some libraries (e.g. WTForms) want a
            unicode dictionary. """
        copy = FormsDict()
        enc = copy.input_encoding = encoding or self.input_encoding
        copy.recode_unicode = False
        for key, value in self.allitems():
            copy.append(self._fix(key, enc), self._fix(value, enc))
        return copy

    def getunicode(self, name, default=None, encoding=None):
        """ Return the value as a unicode string, or the default. """
        try:
            return self._fix(self[name], encoding)
        except (UnicodeError, KeyError):
            return default

    def __getattr__(self, name, default=unicode()):
        # Without this guard, pickle generates a cryptic TypeError:
        if name.startswith('__') and name.endswith('__'):
            return super(FormsDict, self).__getattr__(name)
        return self.getunicode(name, default=default)


class HeaderDict(MultiDict):
    """ A case-insensitive version of :class:`MultiDict` that defaults to
        replace the old value instead of appending it. """

    def __init__(self, *a, **ka):
        self.dict = {}
        if a or ka: self.update(*a, **ka)

    def __contains__(self, key): return _hkey(key) in self.dict
    def __delitem__(self, key): del self.dict[_hkey(key)]
    def __getitem__(self, key): return self.dict[_hkey(key)][-1]
    def __setitem__(self, key, value): self.dict[_hkey(key)] = [str(value)]
    def append(self, key, value):
        self.dict.setdefault(_hkey(key), []).append(str(value))
    def replace(self, key, value): self.dict[_hkey(key)] = [str(value)]
    def getall(self, key): return self.dict.get(_hkey(key)) or []
    def get(self, key, default=None, index=-1):
        return MultiDict.get(self, _hkey(key), default, index)
    def filter(self, names):
        for name in [_hkey(n) for n in names]:
            if name in self.dict:
                del self.dict[name]


class WSGIHeaderDict(DictMixin):
    """ This dict-like class wraps a WSGI environ dict and provides convenient
        access to HTTP_* fields. Keys and values are native strings
        (2.x bytes or 3.x unicode) and keys are case-insensitive. If the WSGI
        environment contains non-native string values, these are de- or encoded
        using a lossless 'latin1' character set.

        The API will remain stable even on changes to the relevant PEPs.
        Currently PEP 333, 444 and 3333 are supported. (PEP 444 is the only one
        that uses non-native strings.)
    """
    #: List of keys that do not have a ``HTTP_`` prefix.
    cgikeys = ('CONTENT_TYPE', 'CONTENT_LENGTH')

    def __init__(self, environ):
        self.environ = environ

    def _ekey(self, key):
        """ Translate header field name to CGI/WSGI environ key. """
        key = key.replace('-','_').upper()
        if key in self.cgikeys:
            return key
        return 'HTTP_' + key

    def raw(self, key, default=None):
        """ Return the header value as is (may be bytes or unicode). """
        return self.environ.get(self._ekey(key), default)

    def __getitem__(self, key):
        return tonat(self.environ[self._ekey(key)], 'latin1')

    def __setitem__(self, key, value):
        raise TypeError("%s is read-only." % self.__class__)

    def __delitem__(self, key):
        raise TypeError("%s is read-only." % self.__class__)

    def __iter__(self):
        for key in self.environ:
            if key[:5] == 'HTTP_':
                yield key[5:].replace('_', '-').title()
            elif key in self.cgikeys:
                yield key.replace('_', '-').title()

    def keys(self): return [x for x in self]
    def __len__(self): return len(self.keys())
    def __contains__(self, key): return self._ekey(key) in self.environ



class ConfigDict(dict):
    """ A dict-like configuration storage with additional support for
        namespaces, validators, meta-data, on_change listeners and more.
    """

    __slots__ = ('_meta', '_on_change')

    def __init__(self):
        self._meta = {}
        self._on_change = lambda name, value: None

    def load_config(self, filename):
        """ Load values from an ``*.ini`` style config file.

            If the config file contains sections, their names are used as
            namespaces for the values within. The two special sections
            ``DEFAULT`` and ``bottle`` refer to the root namespace (no prefix).
        """
        conf = ConfigParser()
        conf.read(filename)
        for section in conf.sections():
            for key, value in conf.items(section):
                if section not in ('DEFAULT', 'bottle'):
                    key = section + '.' + key
                self[key] = value
        return self

    def load_dict(self, source, namespace=''):
        """ Load values from a dictionary structure. Nesting can be used to
            represent namespaces.

            >>> c = ConfigDict()
            >>> c.load_dict({'some': {'namespace': {'key': 'value'} } })
            {'some.namespace.key': 'value'}
        """
        for key, value in source.items():
            if isinstance(key, str):
                nskey = (namespace + '.' + key).strip('.')
                if isinstance(value, dict):
                    self.load_dict(value, namespace=nskey)
                else:
                    self[nskey] = value
            else:
                raise TypeError('Key has type %r (not a string)' % type(key))
        return self

    def update(self, *a, **ka):
        """ If the first parameter is a string, all keys are prefixed with this
            namespace. Apart from that it works just as the usual dict.update().
            Example: ``update('some.namespace', key='value')`` """
        prefix = ''
        if a and isinstance(a[0], str):
            prefix = a[0].strip('.') + '.'
            a = a[1:]
        for key, value in dict(*a, **ka).items():
            self[prefix+key] = value

    def setdefault(self, key, value):
        if key not in self:
            self[key] = value

    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise TypeError('Key has type %r (not a string)' % type(key))
        value = self.meta_get(key, 'filter', lambda x: x)(value)
        if key in self and self[key] is value:
            return
        self._on_change(key, value)
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        self._on_change(key, None)
        dict.__delitem__(self, key)

    def meta_get(self, key, metafield, default=None):
        """ Return the value of a meta field for a key. """
        return self._meta.get(key, {}).get(metafield, default)

    def meta_set(self, key, metafield, value):
        """ Set the meta field for a key to a new value. This triggers the
            on-change handler for existing keys. """
        self._meta.setdefault(key, {})[metafield] = value
        if key in self:
            self[key] = self[key]

    def meta_list(self, key):
        """ Return an iterable of meta field names defined for a key. """
        return self._meta.get(key, {}).keys()


class AppStack(list):
    """ A stack-like list. Calling it returns the head of the stack. """

    def __call__(self):
        """ Return the current default application. """
        return self[-1]

    def push(self, value=None):
        """ Add a new :class:`Bottle` instance to the stack """
        if not isinstance(value, Bottle):
            value = Bottle()
        self.append(value)
        return value


class WSGIFileWrapper(object):

    def __init__(self, fp, buffer_size=1024*64):
        self.fp, self.buffer_size = fp, buffer_size
        for attr in ('fileno', 'close', 'read', 'readlines', 'tell', 'seek'):
            if hasattr(fp, attr): setattr(self, attr, getattr(fp, attr))

    def __iter__(self):
        buff, read = self.buffer_size, self.read
        while True:
            part = read(buff)
            if not part: return
            yield part


class _closeiter(object):
    """ This only exists to be able to attach a .close method to iterators that
        do not support attribute assignment (most of itertools). """

    def __init__(self, iterator, close=None):
        self.iterator = iterator
        self.close_callbacks = makelist(close)

    def __iter__(self):
        return iter(self.iterator)

    def close(self):
        for func in self.close_callbacks:
            func()


class ResourceManager(object):
    """ This class manages a list of search paths and helps to find and open
        application-bound resources (files).

        :param base: default value for :meth:`add_path` calls.
        :param opener: callable used to open resources.
        :param cachemode: controls which lookups are cached. One of 'all',
                         'found' or 'none'.
    """

    def __init__(self, base='./', opener=open, cachemode='all'):
        self.opener = opener
        self.base = base
        self.cachemode = cachemode

        #: A list of search paths. See :meth:`add_path` for details.
        self.path = []
        #: A cache for resolved paths. ``res.cache.clear()`` clears the cache.
        self.cache = {}

    def add_path(self, path, base=None, index=None, create=False):
        """ Add a new path to the list of search paths. Return False if the
            path does not exist.

            :param path: The new search path. Relative paths are turned into
                an absolute and normalized form. If the path looks like a file
                (not ending in `/`), the filename is stripped off.
            :param base: Path used to absolutize relative search paths.
                Defaults to :attr:`base` which defaults to ``os.getcwd()``.
            :param index: Position within the list of search paths. Defaults
                to last index (appends to the list).

            The `base` parameter makes it easy to reference files installed
            along with a python module or package::

                res.add_path('./resources/', __file__)
        """
        base = os.path.abspath(os.path.dirname(base or self.base))
        path = os.path.abspath(os.path.join(base, os.path.dirname(path)))
        path += os.sep
        if path in self.path:
            self.path.remove(path)
        if create and not os.path.isdir(path):
            os.makedirs(path)
        if index is None:
            self.path.append(path)
        else:
            self.path.insert(index, path)
        self.cache.clear()
        return os.path.exists(path)

    def __iter__(self):
        """ Iterate over all existing files in all registered paths. """
        search = self.path[:]
        while search:
            path = search.pop()
            if not os.path.isdir(path): continue
            for name in os.listdir(path):
                full = os.path.join(path, name)
                if os.path.isdir(full): search.append(full)
                else: yield full

    def lookup(self, name):
        """ Search for a resource and return an absolute file path, or `None`.

            The :attr:`path` list is searched in order. The first match is
            returend. Symlinks are followed. The result is cached to speed up
            future lookups. """
        if name not in self.cache or DEBUG:
            for path in self.path:
                fpath = os.path.join(path, name)
                if os.path.isfile(fpath):
                    if self.cachemode in ('all', 'found'):
                        self.cache[name] = fpath
                    return fpath
            if self.cachemode == 'all':
                self.cache[name] = None
        return self.cache[name]

    def open(self, name, mode='r', *args, **kwargs):
        """ Find a resource and return a file object, or raise IOError. """
        fname = self.lookup(name)
        if not fname: raise IOError("Resource %r not found." % name)
        return self.opener(fname, mode=mode, *args, **kwargs)


class FileUpload(object):

    def __init__(self, fileobj, name, filename, headers=None):
        """ Wrapper for file uploads. """
        #: Open file(-like) object (BytesIO buffer or temporary file)
        self.file = fileobj
        #: Name of the upload form field
        self.name = name
        #: Raw filename as sent by the client (may contain unsafe characters)
        self.raw_filename = filename
        #: A :class:`HeaderDict` with additional headers (e.g. content-type)
        self.headers = HeaderDict(headers) if headers else HeaderDict()

    content_type = HeaderProperty('Content-Type')
    content_length = HeaderProperty('Content-Length', reader=int, default=-1)

    @cached_property
    def filename(self):
        """ Name of the file on the client file system, but normalized to ensure
            file system compatibility. An empty filename is returned as 'empty'.

            Only ASCII letters, digits, dashes, underscores and dots are
            allowed in the final filename. Accents are removed, if possible.
            Whitespace is replaced by a single dash. Leading or tailing dots
            or dashes are removed. The filename is limited to 255 characters.
        """
        fname = self.raw_filename
        if not isinstance(fname, unicode):
            fname = fname.decode('utf8', 'ignore')
        fname = normalize('NFKD', fname).encode('ASCII', 'ignore').decode('ASCII')
        fname = os.path.basename(fname.replace('\\', os.path.sep))
        fname = re.sub(r'[^a-zA-Z0-9-_.\s]', '', fname).strip()
        fname = re.sub(r'[-\s]+', '-', fname).strip('.-')
        return fname[:255] or 'empty'

    def _copy_file(self, fp, chunk_size=2**16):
        read, write, offset = self.file.read, fp.write, self.file.tell()
        while 1:
            buf = read(chunk_size)
            if not buf: break
            write(buf)
        self.file.seek(offset)

    def save(self, destination, overwrite=False, chunk_size=2**16):
        """ Save file to disk or copy its content to an open file(-like) object.
            If *destination* is a directory, :attr:`filename` is added to the
            path. Existing files are not overwritten by default (IOError).

            :param destination: File path, directory or file(-like) object.
            :param overwrite: If True, replace existing files. (default: False)
            :param chunk_size: Bytes to read at a time. (default: 64kb)
        """
        if isinstance(destination, basestring): # Except file-likes here
            if os.path.isdir(destination):
                destination = os.path.join(destination, self.filename)
            if not overwrite and os.path.exists(destination):
                raise IOError('File exists.')
            with open(destination, 'wb') as fp:
                self._copy_file(fp, chunk_size)
        else:
            self._copy_file(destination, chunk_size)






###############################################################################
# Application Helper ###########################################################
###############################################################################


def abort(code=500, text='Unknown Error.'):
    """ Aborts execution and causes a HTTP error. """
    raise HTTPError(code, text)


def redirect(url, code=None):
    """ Aborts execution and causes a 303 or 302 redirect, depending on
        the HTTP protocol version. """
    if not code:
        code = 303 if request.get('SERVER_PROTOCOL') == "HTTP/1.1" else 302
    res = response.copy(cls=HTTPResponse)
    res.status = code
    res.body = ""
    res.set_header('Location', urljoin(request.url, url))
    raise res


def _file_iter_range(fp, offset, bytes, maxread=1024*1024):
    """ Yield chunks from a range in a file. No chunk is bigger than maxread."""
    fp.seek(offset)
    while bytes > 0:
        part = fp.read(min(bytes, maxread))
        if not part: break
        bytes -= len(part)
        yield part


def static_file(filename, root, mimetype='auto', download=False, charset='UTF-8'):
    """ Open a file in a safe way and return :exc:`HTTPResponse` with status
        code 200, 305, 403 or 404. The ``Content-Type``, ``Content-Encoding``,
        ``Content-Length`` and ``Last-Modified`` headers are set if possible.
        Special support for ``If-Modified-Since``, ``Range`` and ``HEAD``
        requests.

        :param filename: Name or path of the file to send.
        :param root: Root path for file lookups. Should be an absolute directory
            path.
        :param mimetype: Defines the content-type header (default: guess from
            file extension)
        :param download: If True, ask the browser to open a `Save as...` dialog
            instead of opening the file with the associated program. You can
            specify a custom filename as a string. If not specified, the
            original filename is used (default: False).
        :param charset: The charset to use for files with a ``text/*``
            mime-type. (default: UTF-8)
    """

    root = os.path.abspath(root) + os.sep
    filename = os.path.abspath(os.path.join(root, filename.strip('/\\')))
    headers = dict()

    if not filename.startswith(root):
        return HTTPError(403, "Access denied.")
    if not os.path.exists(filename) or not os.path.isfile(filename):
        return HTTPError(404, "File does not exist.")
    if not os.access(filename, os.R_OK):
        return HTTPError(403, "You do not have permission to access this file.")

    if mimetype == 'auto':
        mimetype, encoding = mimetypes.guess_type(filename)
        if encoding: headers['Content-Encoding'] = encoding

    if mimetype:
        if mimetype[:5] == 'text/' and charset and 'charset' not in mimetype:
            mimetype += '; charset=%s' % charset
        headers['Content-Type'] = mimetype

    if download:
        download = os.path.basename(filename if download == True else download)
        headers['Content-Disposition'] = 'attachment; filename="%s"' % download

    stats = os.stat(filename)
    headers['Content-Length'] = clen = stats.st_size
    lm = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(stats.st_mtime))
    headers['Last-Modified'] = lm

    ims = request.environ.get('HTTP_IF_MODIFIED_SINCE')
    if ims:
        ims = parse_date(ims.split(";")[0].strip())
    if ims is not None and ims >= int(stats.st_mtime):
        headers['Date'] = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        return HTTPResponse(status=304, **headers)

    body = '' if request.method == 'HEAD' else open(filename, 'rb')

    headers["Accept-Ranges"] = "bytes"
    ranges = request.environ.get('HTTP_RANGE')
    if 'HTTP_RANGE' in request.environ:
        ranges = list(parse_range_header(request.environ['HTTP_RANGE'], clen))
        if not ranges:
            return HTTPError(416, "Requested Range Not Satisfiable")
        offset, end = ranges[0]
        headers["Content-Range"] = "bytes %d-%d/%d" % (offset, end-1, clen)
        headers["Content-Length"] = str(end-offset)
        if body: body = _file_iter_range(body, offset, end-offset)
        return HTTPResponse(body, status=206, **headers)
    return HTTPResponse(body, **headers)






###############################################################################
# HTTP Utilities and MISC (TODO) ###############################################
###############################################################################


def debug(mode=True):
    """ Change the debug level.
    There is only one debug level supported at the moment."""
    global DEBUG
    if mode: warnings.simplefilter('default')
    DEBUG = bool(mode)

def http_date(value):
    if isinstance(value, (datedate, datetime)):
        value = value.utctimetuple()
    elif isinstance(value, (int, float)):
        value = time.gmtime(value)
    if not isinstance(value, basestring):
        value = time.strftime("%a, %d %b %Y %H:%M:%S GMT", value)
    return value

def parse_date(ims):
    """ Parse rfc1123, rfc850 and asctime timestamps and return UTC epoch. """
    try:
        ts = email.utils.parsedate_tz(ims)
        return time.mktime(ts[:8] + (0,)) - (ts[9] or 0) - time.timezone
    except (TypeError, ValueError, IndexError, OverflowError):
        return None

def parse_auth(header):
    """ Parse rfc2617 HTTP authentication header string (basic) and return (user,pass) tuple or None"""
    try:
        method, data = header.split(None, 1)
        if method.lower() == 'basic':
            user, pwd = touni(base64.b64decode(tob(data))).split(':',1)
            return user, pwd
    except (KeyError, ValueError):
        return None

def parse_range_header(header, maxlen=0):
    """ Yield (start, end) ranges parsed from a HTTP Range header. Skip
        unsatisfiable ranges. The end index is non-inclusive."""
    if not header or header[:6] != 'bytes=': return
    ranges = [r.split('-', 1) for r in header[6:].split(',') if '-' in r]
    for start, end in ranges:
        try:
            if not start:  # bytes=-100    -> last 100 bytes
                start, end = max(0, maxlen-int(end)), maxlen
            elif not end:  # bytes=100-    -> all but the first 99 bytes
                start, end = int(start), maxlen
            else:          # bytes=100-200 -> bytes 100-200 (inclusive)
                start, end = int(start), min(int(end)+1, maxlen)
            if 0 <= start < end <= maxlen:
                yield start, end
        except ValueError:
            pass

def _parse_qsl(qs):
    r = []
    for pair in qs.replace(';','&').split('&'):
        if not pair: continue
        nv = pair.split('=', 1)
        if len(nv) != 2: nv.append('')
        key = urlunquote(nv[0].replace('+', ' '))
        value = urlunquote(nv[1].replace('+', ' '))
        r.append((key, value))
    return r

def _lscmp(a, b):
    """ Compares two strings in a cryptographically safe way:
        Runtime is not affected by length of common prefix. """
    return not sum(0 if x==y else 1 for x, y in zip(a, b)) and len(a) == len(b)


def cookie_encode(data, key):
    """ Encode and sign a pickle-able object. Return a (byte) string """
    msg = base64.b64encode(pickle.dumps(data, -1))
    sig = base64.b64encode(hmac.new(tob(key), msg).digest())
    return tob('!') + sig + tob('?') + msg


def cookie_decode(data, key):
    """ Verify and decode an encoded string. Return an object or None."""
    data = tob(data)
    if cookie_is_encoded(data):
        sig, msg = data.split(tob('?'), 1)
        if _lscmp(sig[1:], base64.b64encode(hmac.new(tob(key), msg).digest())):
            return pickle.loads(base64.b64decode(msg))
    return None


def cookie_is_encoded(data):
    """ Return True if the argument looks like a encoded cookie."""
    return bool(data.startswith(tob('!')) and tob('?') in data)


def html_escape(string):
    """ Escape HTML special characters ``&<>`` and quotes ``'"``. """
    return string.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')\
                 .replace('"','&quot;').replace("'",'&#039;')


def html_quote(string):
    """ Escape and quote a string to be used as an HTTP attribute."""
    return '"%s"' % html_escape(string).replace('\n','&#10;')\
                    .replace('\r','&#13;').replace('\t','&#9;')


def yieldroutes(func):
    """ Return a generator for routes that match the signature (name, args)
    of the func parameter. This may yield more than one route if the function
    takes optional keyword arguments. The output is best described by example::

        a()         -> '/a'
        b(x, y)     -> '/b/<x>/<y>'
        c(x, y=5)   -> '/c/<x>' and '/c/<x>/<y>'
        d(x=5, y=6) -> '/d' and '/d/<x>' and '/d/<x>/<y>'
    """
    path = '/' + func.__name__.replace('__','/').lstrip('/')
    spec = getargspec(func)
    argc = len(spec[0]) - len(spec[3] or [])
    path += ('/<%s>' * argc) % tuple(spec[0][:argc])
    yield path
    for arg in spec[0][argc:]:
        path += '/<%s>' % arg
        yield path


def path_shift(script_name, path_info, shift=1):
    """ Shift path fragments from PATH_INFO to SCRIPT_NAME and vice versa.

        :return: The modified paths.
        :param script_name: The SCRIPT_NAME path.
        :param script_name: The PATH_INFO path.
        :param shift: The number of path fragments to shift. May be negative to
          change the shift direction. (default: 1)
    """
    if shift == 0: return script_name, path_info
    pathlist = path_info.strip('/').split('/')
    scriptlist = script_name.strip('/').split('/')
    if pathlist and pathlist[0] == '': pathlist = []
    if scriptlist and scriptlist[0] == '': scriptlist = []
    if 0 < shift <= len(pathlist):
        moved = pathlist[:shift]
        scriptlist = scriptlist + moved
        pathlist = pathlist[shift:]
    elif 0 > shift >= -len(scriptlist):
        moved = scriptlist[shift:]
        pathlist = moved + pathlist
        scriptlist = scriptlist[:shift]
    else:
        empty = 'SCRIPT_NAME' if shift < 0 else 'PATH_INFO'
        raise AssertionError("Cannot shift. Nothing left from %s" % empty)
    new_script_name = '/' + '/'.join(scriptlist)
    new_path_info = '/' + '/'.join(pathlist)
    if path_info.endswith('/') and pathlist: new_path_info += '/'
    return new_script_name, new_path_info


def auth_basic(check, realm="private", text="Access denied"):
    """ Callback decorator to require HTTP auth (basic).
        TODO: Add route(check_auth=...) parameter. """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*a, **ka):
            user, password = request.auth or (None, None)
            if user is None or not check(user, password):
                err = HTTPError(401, text)
                err.add_header('WWW-Authenticate', 'Basic realm="%s"' % realm)
                return err
            return func(*a, **ka)
        return wrapper
    return decorator


# Shortcuts for common Bottle methods.
# They all refer to the current default application.

def make_default_app_wrapper(name):
    """ Return a callable that relays calls to the current default app. """
    @functools.wraps(getattr(Bottle, name))
    def wrapper(*a, **ka):
        return getattr(app(), name)(*a, **ka)
    return wrapper

route     = make_default_app_wrapper('route')
get       = make_default_app_wrapper('get')
post      = make_default_app_wrapper('post')
put       = make_default_app_wrapper('put')
delete    = make_default_app_wrapper('delete')
patch     = make_default_app_wrapper('patch')
error     = make_default_app_wrapper('error')
mount     = make_default_app_wrapper('mount')
hook      = make_default_app_wrapper('hook')
install   = make_default_app_wrapper('install')
uninstall = make_default_app_wrapper('uninstall')
url       = make_default_app_wrapper('get_url')







###############################################################################
# Server Adapter ###############################################################
###############################################################################


class ServerAdapter(object):
    quiet = False
    def __init__(self, host='127.0.0.1', port=8080, **options):
        self.options = options
        self.host = host
        self.port = int(port)

    def run(self, handler): # pragma: no cover
        pass

    def __repr__(self):
        args = ', '.join(['%s=%s'%(k,repr(v)) for k, v in self.options.items()])
        return "%s(%s)" % (self.__class__.__name__, args)


class CGIServer(ServerAdapter):
    quiet = True
    def run(self, handler): # pragma: no cover
        from wsgiref.handlers import CGIHandler
        def fixed_environ(environ, start_response):
            environ.setdefault('PATH_INFO', '')
            return handler(environ, start_response)
        CGIHandler().run(fixed_environ)


class FlupFCGIServer(ServerAdapter):
    def run(self, handler): # pragma: no cover
        import flup.server.fcgi
        self.options.setdefault('bindAddress', (self.host, self.port))
        flup.server.fcgi.WSGIServer(handler, **self.options).run()


class WSGIRefServer(ServerAdapter):
    def run(self, app): # pragma: no cover
        from wsgiref.simple_server import WSGIRequestHandler, WSGIServer
        from wsgiref.simple_server import make_server
        import socket

        class FixedHandler(WSGIRequestHandler):
            def address_string(self): # Prevent reverse DNS lookups please.
                return self.client_address[0]
            def log_request(*args, **kw):
                if not self.quiet:
                    return WSGIRequestHandler.log_request(*args, **kw)

        handler_cls = self.options.get('handler_class', FixedHandler)
        server_cls  = self.options.get('server_class', WSGIServer)

        if ':' in self.host: # Fix wsgiref for IPv6 addresses.
            if getattr(server_cls, 'address_family') == socket.AF_INET:
                class server_cls(server_cls):
                    address_family = socket.AF_INET6

        srv = make_server(self.host, self.port, app, server_cls, handler_cls)
        srv.serve_forever()


class CherryPyServer(ServerAdapter):
    def run(self, handler): # pragma: no cover
        from cherrypy import wsgiserver
        self.options['bind_addr'] = (self.host, self.port)
        self.options['wsgi_app'] = handler
        
        certfile = self.options.get('certfile')
        if certfile:
            del self.options['certfile']
        keyfile = self.options.get('keyfile')
        if keyfile:
            del self.options['keyfile']
        
        server = wsgiserver.CherryPyWSGIServer(**self.options)
        if certfile:
            server.ssl_certificate = certfile
        if keyfile:
            server.ssl_private_key = keyfile
        
        try:
            server.start()
        finally:
            server.stop()


class WaitressServer(ServerAdapter):
    def run(self, handler):
        from waitress import serve
        serve(handler, host=self.host, port=self.port)


class PasteServer(ServerAdapter):
    def run(self, handler): # pragma: no cover
        from paste import httpserver
        from paste.translogger import TransLogger
        handler = TransLogger(handler, setup_console_handler=(not self.quiet))
        httpserver.serve(handler, host=self.host, port=str(self.port),
                         **self.options)


class MeinheldServer(ServerAdapter):
    def run(self, handler):
        from meinheld import server
        server.listen((self.host, self.port))
        server.run(handler)


class FapwsServer(ServerAdapter):
    """ Extremely fast webserver using libev. See http://www.fapws.org/ """
    def run(self, handler): # pragma: no cover
        import fapws._evwsgi as evwsgi
        from fapws import base, config
        port = self.port
        if float(config.SERVER_IDENT[-2:]) > 0.4:
            # fapws3 silently changed its API in 0.5
            port = str(port)
        evwsgi.start(self.host, port)
        # fapws3 never releases the GIL. Complain upstream. I tried. No luck.
        if 'BOTTLE_CHILD' in os.environ and not self.quiet:
            _stderr("WARNING: Auto-reloading does not work with Fapws3.\n")
            _stderr("         (Fapws3 breaks python thread support)\n")
        evwsgi.set_base_module(base)
        def app(environ, start_response):
            environ['wsgi.multiprocess'] = False
            return handler(environ, start_response)
        evwsgi.wsgi_cb(('', app))
        evwsgi.run()


class TornadoServer(ServerAdapter):
    """ The super hyped asynchronous server by facebook. Untested. """
    def run(self, handler): # pragma: no cover
        import tornado.wsgi, tornado.httpserver, tornado.ioloop
        container = tornado.wsgi.WSGIContainer(handler)
        server = tornado.httpserver.HTTPServer(container)
        server.listen(port=self.port,address=self.host)
        tornado.ioloop.IOLoop.instance().start()


class AppEngineServer(ServerAdapter):
    """ Adapter for Google App Engine. """
    quiet = True
    def run(self, handler):
        from google.appengine.ext.webapp import util
        # A main() function in the handler script enables 'App Caching'.
        # Lets makes sure it is there. This _really_ improves performance.
        module = sys.modules.get('__main__')
        if module and not hasattr(module, 'main'):
            module.main = lambda: util.run_wsgi_app(handler)
        util.run_wsgi_app(handler)


class TwistedServer(ServerAdapter):
    """ Untested. """
    def run(self, handler):
        from twisted.web import server, wsgi
        from twisted.python.threadpool import ThreadPool
        from twisted.internet import reactor
        thread_pool = ThreadPool()
        thread_pool.start()
        reactor.addSystemEventTrigger('after', 'shutdown', thread_pool.stop)
        factory = server.Site(wsgi.WSGIResource(reactor, thread_pool, handler))
        reactor.listenTCP(self.port, factory, interface=self.host)
        if not reactor.running:
            reactor.run()


class DieselServer(ServerAdapter):
    """ Untested. """
    def run(self, handler):
        from diesel.protocols.wsgi import WSGIApplication
        app = WSGIApplication(handler, port=self.port)
        app.run()


class GeventServer(ServerAdapter):
    """ Untested. Options:

        * `fast` (default: False) uses libevent's http server, but has some
          issues: No streaming, no pipelining, no SSL.
        * See gevent.wsgi.WSGIServer() documentation for more options.
    """
    def run(self, handler):
        from gevent import wsgi, pywsgi, local
        if not isinstance(threading.local(), local.local):
            msg = "Bottle requires gevent.monkey.patch_all() (before import)"
            raise RuntimeError(msg)
        if not self.options.pop('fast', None): wsgi = pywsgi
        self.options['log'] = None if self.quiet else 'default'
        address = (self.host, self.port)
        server = wsgi.WSGIServer(address, handler, **self.options)
        if 'BOTTLE_CHILD' in os.environ:
            import signal
            signal.signal(signal.SIGINT, lambda s, f: server.stop())
        server.serve_forever()


class GeventSocketIOServer(ServerAdapter):
    def run(self,handler):
        from socketio import server
        address = (self.host, self.port)
        server.SocketIOServer(address, handler, **self.options).serve_forever()


class GunicornServer(ServerAdapter):
    """ Untested. See http://gunicorn.org/configure.html for options. """
    def run(self, handler):
        from gunicorn.app.base import Application

        config = {'bind': "%s:%d" % (self.host, int(self.port))}
        config.update(self.options)

        class GunicornApplication(Application):
            def init(self, parser, opts, args):
                return config

            def load(self):
                return handler

        GunicornApplication().run()


class EventletServer(ServerAdapter):
    """ Untested. Options:

        * `backlog` adjust the eventlet backlog parameter which is the maximum
          number of queued connections. Should be at least 1; the maximum
          value is system-dependent.
        * `family`: (default is 2) socket family, optional. See socket
          documentation for available families.
    """
    def run(self, handler):
        from eventlet import wsgi, listen, patcher
        if not patcher.is_monkey_patched(os):
            msg = "Bottle requires eventlet.monkey_patch() (before import)"
            raise RuntimeError(msg)
        socket_args = {}
        for arg in ('backlog', 'family'):
            try:
                socket_args[arg] = self.options.pop(arg)
            except KeyError:
                pass
        address = (self.host, self.port)
        try:
            wsgi.server(listen(address, **socket_args), handler,
                        log_output=(not self.quiet))
        except TypeError:
            # Fallback, if we have old version of eventlet
            wsgi.server(listen(address), handler)


class RocketServer(ServerAdapter):
    """ Untested. """
    def run(self, handler):
        from rocket import Rocket
        server = Rocket((self.host, self.port), 'wsgi', { 'wsgi_app' : handler })
        server.start()


class BjoernServer(ServerAdapter):
    """ Fast server written in C: https://github.com/jonashaag/bjoern """
    def run(self, handler):
        from bjoern import run
        run(handler, self.host, self.port)


class AutoServer(ServerAdapter):
    """ Untested. """
    adapters = [WaitressServer, PasteServer, TwistedServer, CherryPyServer, WSGIRefServer]
    def run(self, handler):
        for sa in self.adapters:
            try:
                return sa(self.host, self.port, **self.options).run(handler)
            except ImportError:
                pass

server_names = {
    'cgi': CGIServer,
    'flup': FlupFCGIServer,
    'wsgiref': WSGIRefServer,
    'waitress': WaitressServer,
    'cherrypy': CherryPyServer,
    'paste': PasteServer,
    'fapws3': FapwsServer,
    'tornado': TornadoServer,
    'gae': AppEngineServer,
    'twisted': TwistedServer,
    'diesel': DieselServer,
    'meinheld': MeinheldServer,
    'gunicorn': GunicornServer,
    'eventlet': EventletServer,
    'gevent': GeventServer,
    'geventSocketIO':GeventSocketIOServer,
    'rocket': RocketServer,
    'bjoern' : BjoernServer,
    'auto': AutoServer,
}






###############################################################################
# Application Control ##########################################################
###############################################################################


def load(target, **namespace):
    """ Import a module or fetch an object from a module.

        * ``package.module`` returns `module` as a module object.
        * ``pack.mod:name`` returns the module variable `name` from `pack.mod`.
        * ``pack.mod:func()`` calls `pack.mod.func()` and returns the result.

        The last form accepts not only function calls, but any type of
        expression. Keyword arguments passed to this function are available as
        local variables. Example: ``import_string('re:compile(x)', x='[a-z]')``
    """
    module, target = target.split(":", 1) if ':' in target else (target, None)
    if module not in sys.modules: __import__(module)
    if not target: return sys.modules[module]
    if target.isalnum(): return getattr(sys.modules[module], target)
    package_name = module.split('.')[0]
    namespace[package_name] = sys.modules[package_name]
    return eval('%s.%s' % (module, target), namespace)


def load_app(target):
    """ Load a bottle application from a module and make sure that the import
        does not affect the current default application, but returns a separate
        application object. See :func:`load` for the target parameter. """
    global NORUN; NORUN, nr_old = True, NORUN
    tmp = default_app.push() # Create a new "default application"
    try:
        rv = load(target) # Import the target module
        return rv if callable(rv) else tmp
    finally:
        default_app.remove(tmp) # Remove the temporary added default application
        NORUN = nr_old

_debug = debug
def run(app=None, server='wsgiref', host='127.0.0.1', port=8080,
        interval=1, reloader=False, quiet=False, plugins=None,
        debug=None, **kargs):
    """ Start a server instance. This method blocks until the server terminates.

        :param app: WSGI application or target string supported by
               :func:`load_app`. (default: :func:`default_app`)
        :param server: Server adapter to use. See :data:`server_names` keys
               for valid names or pass a :class:`ServerAdapter` subclass.
               (default: `wsgiref`)
        :param host: Server address to bind to. Pass ``0.0.0.0`` to listens on
               all interfaces including the external one. (default: 127.0.0.1)
        :param port: Server port to bind to. Values below 1024 require root
               privileges. (default: 8080)
        :param reloader: Start auto-reloading server? (default: False)
        :param interval: Auto-reloader interval in seconds (default: 1)
        :param quiet: Suppress output to stdout and stderr? (default: False)
        :param options: Options passed to the server adapter.
     """
    if NORUN: return
    if reloader and not os.environ.get('BOTTLE_CHILD'):
        lockfile = None
        try:
            fd, lockfile = tempfile.mkstemp(prefix='bottle.', suffix='.lock')
            os.close(fd) # We only need this file to exist. We never write to it
            while os.path.exists(lockfile):
                args = [sys.executable] + sys.argv
                environ = os.environ.copy()
                environ['BOTTLE_CHILD'] = 'true'
                environ['BOTTLE_LOCKFILE'] = lockfile
                p = subprocess.Popen(args, env=environ)
                while p.poll() is None: # Busy wait...
                    os.utime(lockfile, None) # I am alive!
                    time.sleep(interval)
                if p.poll() != 3:
                    if os.path.exists(lockfile): os.unlink(lockfile)
                    sys.exit(p.poll())
        except KeyboardInterrupt:
            pass
        finally:
            if os.path.exists(lockfile):
                os.unlink(lockfile)
        return

    try:
        if debug is not None: _debug(debug)
        app = app or default_app()
        if isinstance(app, basestring):
            app = load_app(app)
        if not callable(app):
            raise ValueError("Application is not callable: %r" % app)

        for plugin in plugins or []:
            if isinstance(plugin, basestring):
                plugin = load(plugin)
            app.install(plugin)

        if server in server_names:
            server = server_names.get(server)
        if isinstance(server, basestring):
            server = load(server)
        if isinstance(server, type):
            server = server(host=host, port=port, **kargs)
        if not isinstance(server, ServerAdapter):
            raise ValueError("Unknown or unsupported server: %r" % server)

        server.quiet = server.quiet or quiet
        if not server.quiet:
            _stderr("Bottle v%s server starting up (using %s)...\n" % (__version__, repr(server)))
            _stderr("Listening on http://%s:%d/\n" % (server.host, server.port))
            _stderr("Hit Ctrl-C to quit.\n\n")

        if reloader:
            lockfile = os.environ.get('BOTTLE_LOCKFILE')
            bgcheck = FileCheckerThread(lockfile, interval)
            with bgcheck:
                server.run(app)
            if bgcheck.status == 'reload':
                sys.exit(3)
        else:
            server.run(app)
    except KeyboardInterrupt:
        pass
    except (SystemExit, MemoryError):
        raise
    except:
        if not reloader: raise
        if not getattr(server, 'quiet', quiet):
            print_exc()
        time.sleep(interval)
        sys.exit(3)



class FileCheckerThread(threading.Thread):
    """ Interrupt main-thread as soon as a changed module file is detected,
        the lockfile gets deleted or gets to old. """

    def __init__(self, lockfile, interval):
        threading.Thread.__init__(self)
        self.daemon = True
        self.lockfile, self.interval = lockfile, interval
        #: Is one of 'reload', 'error' or 'exit'
        self.status = None

    def run(self):
        exists = os.path.exists
        mtime = lambda p: os.stat(p).st_mtime
        files = dict()

        for module in list(sys.modules.values()):
            path = getattr(module, '__file__', '')
            if path[-4:] in ('.pyo', '.pyc'): path = path[:-1]
            if path and exists(path): files[path] = mtime(path)

        while not self.status:
            if not exists(self.lockfile)\
            or mtime(self.lockfile) < time.time() - self.interval - 5:
                self.status = 'error'
                thread.interrupt_main()
            for path, lmtime in list(files.items()):
                if not exists(path) or mtime(path) > lmtime:
                    self.status = 'reload'
                    thread.interrupt_main()
                    break
            time.sleep(self.interval)

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, *_):
        if not self.status: self.status = 'exit' # silent exit
        self.join()
        return exc_type is not None and issubclass(exc_type, KeyboardInterrupt)





###############################################################################
# Template Adapters ############################################################
###############################################################################


class TemplateError(HTTPError):
    def __init__(self, message):
        HTTPError.__init__(self, 500, message)


class BaseTemplate(object):
    """ Base class and minimal API for template adapters """
    extensions = ['tpl','html','thtml','stpl']
    settings = {} #used in prepare()
    defaults = {} #used in render()

    def __init__(self, source=None, name=None, lookup=None, encoding='utf8', **settings):
        """ Create a new template.
        If the source parameter (str or buffer) is missing, the name argument
        is used to guess a template filename. Subclasses can assume that
        self.source and/or self.filename are set. Both are strings.
        The lookup, encoding and settings parameters are stored as instance
        variables.
        The lookup parameter stores a list containing directory paths.
        The encoding parameter should be used to decode byte strings or files.
        The settings parameter contains a dict for engine-specific settings.
        """
        self.name = name
        self.source = source.read() if hasattr(source, 'read') else source
        self.filename = source.filename if hasattr(source, 'filename') else None
        self.lookup = [os.path.abspath(x) for x in lookup] if lookup else []
        self.encoding = encoding
        self.settings = self.settings.copy() # Copy from class variable
        self.settings.update(settings) # Apply
        if not self.source and self.name:
            self.filename = self.search(self.name, self.lookup)
            if not self.filename:
                raise TemplateError('Template %s not found.' % repr(name))
        if not self.source and not self.filename:
            raise TemplateError('No template specified.')
        self.prepare(**self.settings)

    @classmethod
    def search(cls, name, lookup=None):
        """ Search name in all directories specified in lookup.
        First without, then with common extensions. Return first hit. """
        if not lookup:
            depr('The template lookup path list should not be empty.', True) #0.12
            lookup = ['.']

        if os.path.isabs(name) and os.path.isfile(name):
            depr('Absolute template path names are deprecated.', True) #0.12
            return os.path.abspath(name)

        for spath in lookup:
            spath = os.path.abspath(spath) + os.sep
            fname = os.path.abspath(os.path.join(spath, name))
            if not fname.startswith(spath): continue
            if os.path.isfile(fname): return fname
            for ext in cls.extensions:
                if os.path.isfile('%s.%s' % (fname, ext)):
                    return '%s.%s' % (fname, ext)

    @classmethod
    def global_config(cls, key, *args):
        """ This reads or sets the global settings stored in class.settings. """
        if args:
            cls.settings = cls.settings.copy() # Make settings local to class
            cls.settings[key] = args[0]
        else:
            return cls.settings[key]

    def prepare(self, **options):
        """ Run preparations (parsing, caching, ...).
        It should be possible to call this again to refresh a template or to
        update settings.
        """
        raise NotImplementedError

    def render(self, *args, **kwargs):
        """ Render the template with the specified local variables and return
        a single byte or unicode string. If it is a byte string, the encoding
        must match self.encoding. This method must be thread-safe!
        Local variables may be provided in dictionaries (args)
        or directly, as keywords (kwargs).
        """
        raise NotImplementedError


class MakoTemplate(BaseTemplate):
    def prepare(self, **options):
        from mako.template import Template
        from mako.lookup import TemplateLookup
        options.update({'input_encoding':self.encoding})
        options.setdefault('format_exceptions', bool(DEBUG))
        lookup = TemplateLookup(directories=self.lookup, **options)
        if self.source:
            self.tpl = Template(self.source, lookup=lookup, **options)
        else:
            self.tpl = Template(uri=self.name, filename=self.filename, lookup=lookup, **options)

    def render(self, *args, **kwargs):
        for dictarg in args: kwargs.update(dictarg)
        _defaults = self.defaults.copy()
        _defaults.update(kwargs)
        return self.tpl.render(**_defaults)


class CheetahTemplate(BaseTemplate):
    def prepare(self, **options):
        from Cheetah.Template import Template
        self.context = threading.local()
        self.context.vars = {}
        options['searchList'] = [self.context.vars]
        if self.source:
            self.tpl = Template(source=self.source, **options)
        else:
            self.tpl = Template(file=self.filename, **options)

    def render(self, *args, **kwargs):
        for dictarg in args: kwargs.update(dictarg)
        self.context.vars.update(self.defaults)
        self.context.vars.update(kwargs)
        out = str(self.tpl)
        self.context.vars.clear()
        return out


class Jinja2Template(BaseTemplate):
    def prepare(self, filters=None, tests=None, globals={}, **kwargs):
        from jinja2 import Environment, FunctionLoader
        self.env = Environment(loader=FunctionLoader(self.loader), **kwargs)
        if filters: self.env.filters.update(filters)
        if tests: self.env.tests.update(tests)
        if globals: self.env.globals.update(globals)
        if self.source:
            self.tpl = self.env.from_string(self.source)
        else:
            self.tpl = self.env.get_template(self.filename)

    def render(self, *args, **kwargs):
        for dictarg in args: kwargs.update(dictarg)
        _defaults = self.defaults.copy()
        _defaults.update(kwargs)
        return self.tpl.render(**_defaults)

    def loader(self, name):
        fname = self.search(name, self.lookup)
        if not fname: return
        with open(fname, "rb") as f:
            return f.read().decode(self.encoding)


class SimpleTemplate(BaseTemplate):

    def prepare(self, escape_func=html_escape, noescape=False, syntax=None, **ka):
        self.cache = {}
        enc = self.encoding
        self._str = lambda x: touni(x, enc)
        self._escape = lambda x: escape_func(touni(x, enc))
        self.syntax = syntax
        if noescape:
            self._str, self._escape = self._escape, self._str

    @cached_property
    def co(self):
        return compile(self.code, self.filename or '<string>', 'exec')

    @cached_property
    def code(self):
        source = self.source
        if not source:
            with open(self.filename, 'rb') as f:
                source = f.read()
        try:
            source, encoding = touni(source), 'utf8'
        except UnicodeError:
            depr('Template encodings other than utf8 are no longer supported.') #0.11
            source, encoding = touni(source, 'latin1'), 'latin1'
        parser = StplParser(source, encoding=encoding, syntax=self.syntax)
        code = parser.translate()
        self.encoding = parser.encoding
        return code

    def _rebase(self, _env, _name=None, **kwargs):
        _env['_rebase'] = (_name, kwargs)

    def _include(self, _env, _name=None, **kwargs):
        env = _env.copy()
        env.update(kwargs)
        if _name not in self.cache:
            self.cache[_name] = self.__class__(name=_name, lookup=self.lookup)
        return self.cache[_name].execute(env['_stdout'], env)

    def execute(self, _stdout, kwargs):
        env = self.defaults.copy()
        env.update(kwargs)
        env.update({'_stdout': _stdout, '_printlist': _stdout.extend,
            'include': functools.partial(self._include, env),
            'rebase': functools.partial(self._rebase, env), '_rebase': None,
            '_str': self._str, '_escape': self._escape, 'get': env.get,
            'setdefault': env.setdefault, 'defined': env.__contains__ })
        eval(self.co, env)
        if env.get('_rebase'):
            subtpl, rargs = env.pop('_rebase')
            rargs['base'] = ''.join(_stdout) #copy stdout
            del _stdout[:] # clear stdout
            return self._include(env, subtpl, **rargs)
        return env

    def render(self, *args, **kwargs):
        """ Render the template using keyword arguments as local variables. """
        env = {}; stdout = []
        for dictarg in args: env.update(dictarg)
        env.update(kwargs)
        self.execute(stdout, env)
        return ''.join(stdout)


class StplSyntaxError(TemplateError): pass


class StplParser(object):
    """ Parser for stpl templates. """
    _re_cache = {} #: Cache for compiled re patterns
    # This huge pile of voodoo magic splits python code into 8 different tokens.
    # 1: All kinds of python strings (trust me, it works)
    _re_tok = '((?m)[urbURB]?(?:\'\'(?!\')|""(?!")|\'{6}|"{6}' \
               '|\'(?:[^\\\\\']|\\\\.)+?\'|"(?:[^\\\\"]|\\\\.)+?"' \
               '|\'{3}(?:[^\\\\]|\\\\.|\\n)+?\'{3}' \
               '|"{3}(?:[^\\\\]|\\\\.|\\n)+?"{3}))'
    _re_inl = _re_tok.replace('|\\n','') # We re-use this string pattern later
    # 2: Comments (until end of line, but not the newline itself)
    _re_tok += '|(#.*)'
    # 3,4: Keywords that start or continue a python block (only start of line)
    _re_tok += '|^([ \\t]*(?:if|for|while|with|try|def|class)\\b)' \
               '|^([ \\t]*(?:elif|else|except|finally)\\b)'
    # 5: Our special 'end' keyword (but only if it stands alone)
    _re_tok += '|((?:^|;)[ \\t]*end[ \\t]*(?=(?:%(block_close)s[ \\t]*)?\\r?$|;|#))'
    # 6: A customizable end-of-code-block template token (only end of line)
    _re_tok += '|(%(block_close)s[ \\t]*(?=$))'
    # 7: And finally, a single newline. The 8th token is 'everything else'
    _re_tok += '|(\\r?\\n)'
    # Match the start tokens of code areas in a template
    _re_split = '(?m)^[ \t]*(\\\\?)((%(line_start)s)|(%(block_start)s))'
    # Match inline statements (may contain python strings)
    _re_inl = '%%(inline_start)s((?:%s|[^\'"\n]*?)+)%%(inline_end)s' % _re_inl

    default_syntax = '<% %> % {{ }}'

    def __init__(self, source, syntax=None, encoding='utf8'):
        self.source, self.encoding = touni(source, encoding), encoding
        self.set_syntax(syntax or self.default_syntax)
        self.code_buffer, self.text_buffer = [], []
        self.lineno, self.offset = 1, 0
        self.indent, self.indent_mod = 0, 0

    def get_syntax(self):
        """ Tokens as a space separated string (default: <% %> % {{ }}) """
        return self._syntax

    def set_syntax(self, syntax):
        self._syntax = syntax
        self._tokens = syntax.split()
        if not syntax in self._re_cache:
            names = 'block_start block_close line_start inline_start inline_end'
            etokens = map(re.escape, self._tokens)
            pattern_vars = dict(zip(names.split(), etokens))
            patterns = (self._re_split, self._re_tok, self._re_inl)
            patterns = [re.compile(p%pattern_vars) for p in patterns]
            self._re_cache[syntax] = patterns
        self.re_split, self.re_tok, self.re_inl = self._re_cache[syntax]

    syntax = property(get_syntax, set_syntax)

    def translate(self):
        if self.offset: raise RuntimeError('Parser is a one time instance.')
        while True:
            m = self.re_split.search(self.source[self.offset:])
            if m:
                text = self.source[self.offset:self.offset+m.start()]
                self.text_buffer.append(text)
                self.offset += m.end()
                if m.group(1): # Escape syntax
                    line, sep, _ = self.source[self.offset:].partition('\n')
                    self.text_buffer.append(m.group(2)+line+sep)
                    self.offset += len(line+sep)+1
                    continue
                self.flush_text()
                self.read_code(multiline=bool(m.group(4)))
            else: break
        self.text_buffer.append(self.source[self.offset:])
        self.flush_text()
        return ''.join(self.code_buffer)

    def read_code(self, multiline):
        code_line, comment = '', ''
        while True:
            m = self.re_tok.search(self.source[self.offset:])
            if not m:
                code_line += self.source[self.offset:]
                self.offset = len(self.source)
                self.write_code(code_line.strip(), comment)
                return
            code_line += self.source[self.offset:self.offset+m.start()]
            self.offset += m.end()
            _str, _com, _blk1, _blk2, _end, _cend, _nl = m.groups()
            if code_line and (_blk1 or _blk2): # a if b else c
                code_line += _blk1 or _blk2
                continue
            if _str:    # Python string
                code_line += _str
            elif _com:  # Python comment (up to EOL)
                comment = _com
                if multiline and _com.strip().endswith(self._tokens[1]):
                    multiline = False # Allow end-of-block in comments
            elif _blk1: # Start-block keyword (if/for/while/def/try/...)
                code_line, self.indent_mod = _blk1, -1
                self.indent += 1
            elif _blk2: # Continue-block keyword (else/elif/except/...)
                code_line, self.indent_mod = _blk2, -1
            elif _end:  # The non-standard 'end'-keyword (ends a block)
                self.indent -= 1
            elif _cend: # The end-code-block template token (usually '%>')
                if multiline: multiline = False
                else: code_line += _cend
            else: # \n
                self.write_code(code_line.strip(), comment)
                self.lineno += 1
                code_line, comment, self.indent_mod = '', '', 0
                if not multiline:
                    break

    def flush_text(self):
        text = ''.join(self.text_buffer)
        del self.text_buffer[:]
        if not text: return
        parts, pos, nl = [], 0, '\\\n'+'  '*self.indent
        for m in self.re_inl.finditer(text):
            prefix, pos = text[pos:m.start()], m.end()
            if prefix:
                parts.append(nl.join(map(repr, prefix.splitlines(True))))
            if prefix.endswith('\n'): parts[-1] += nl
            parts.append(self.process_inline(m.group(1).strip()))
        if pos < len(text):
            prefix = text[pos:]
            lines = prefix.splitlines(True)
            if lines[-1].endswith('\\\\\n'): lines[-1] = lines[-1][:-3]
            elif lines[-1].endswith('\\\\\r\n'): lines[-1] = lines[-1][:-4]
            parts.append(nl.join(map(repr, lines)))
        code = '_printlist((%s,))' % ', '.join(parts)
        self.lineno += code.count('\n')+1
        self.write_code(code)

    @staticmethod
    def process_inline(chunk):
        if chunk[0] == '!': return '_str(%s)' % chunk[1:]
        return '_escape(%s)' % chunk

    def write_code(self, line, comment=''):
        code  = '  ' * (self.indent+self.indent_mod)
        code += line.lstrip() + comment + '\n'
        self.code_buffer.append(code)


def template(*args, **kwargs):
    """
    Get a rendered template as a string iterator.
    You can use a name, a filename or a template string as first parameter.
    Template rendering arguments can be passed as dictionaries
    or directly (as keyword arguments).
    """
    tpl = args[0] if args else None
    adapter = kwargs.pop('template_adapter', SimpleTemplate)
    lookup = kwargs.pop('template_lookup', TEMPLATE_PATH)
    tplid = (id(lookup), tpl)
    if tplid not in TEMPLATES or DEBUG:
        settings = kwargs.pop('template_settings', {})
        if isinstance(tpl, adapter):
            TEMPLATES[tplid] = tpl
            if settings: TEMPLATES[tplid].prepare(**settings)
        elif "\n" in tpl or "{" in tpl or "%" in tpl or '$' in tpl:
            TEMPLATES[tplid] = adapter(source=tpl, lookup=lookup, **settings)
        else:
            TEMPLATES[tplid] = adapter(name=tpl, lookup=lookup, **settings)
    if not TEMPLATES[tplid]:
        abort(500, 'Template (%s) not found' % tpl)
    for dictarg in args[1:]: kwargs.update(dictarg)
    return TEMPLATES[tplid].render(kwargs)

mako_template = functools.partial(template, template_adapter=MakoTemplate)
cheetah_template = functools.partial(template, template_adapter=CheetahTemplate)
jinja2_template = functools.partial(template, template_adapter=Jinja2Template)


def view(tpl_name, **defaults):
    """ Decorator: renders a template for a handler.
        The handler can control its behavior like that:

          - return a dict of template vars to fill out the template
          - return something other than a dict and the view decorator will not
            process the template, but return the handler result as is.
            This includes returning a HTTPResponse(dict) to get,
            for instance, JSON with autojson or other castfilters.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if isinstance(result, (dict, DictMixin)):
                tplvars = defaults.copy()
                tplvars.update(result)
                return template(tpl_name, **tplvars)
            elif result is None:
                return template(tpl_name, defaults)
            return result
        return wrapper
    return decorator

mako_view = functools.partial(view, template_adapter=MakoTemplate)
cheetah_view = functools.partial(view, template_adapter=CheetahTemplate)
jinja2_view = functools.partial(view, template_adapter=Jinja2Template)






###############################################################################
# Constants and Globals ########################################################
###############################################################################


TEMPLATE_PATH = ['./', './views/']
TEMPLATES = {}
DEBUG = False
NORUN = False # If set, run() does nothing. Used by load_app()

#: A dict to map HTTP status codes (e.g. 404) to phrases (e.g. 'Not Found')
HTTP_CODES = httplib.responses
HTTP_CODES[418] = "I'm a teapot" # RFC 2324
HTTP_CODES[428] = "Precondition Required"
HTTP_CODES[429] = "Too Many Requests"
HTTP_CODES[431] = "Request Header Fields Too Large"
HTTP_CODES[511] = "Network Authentication Required"
_HTTP_STATUS_LINES = dict((k, '%d %s'%(k,v)) for (k,v) in HTTP_CODES.items())

#: The default template used for error pages. Override with @error()
ERROR_PAGE_TEMPLATE = """
%%try:
    %%from %s import DEBUG, request
    <!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
    <html>
        <head>
            <title>Error: {{e.status}}</title>
            <style type="text/css">
              html {background-color: #eee; font-family: sans-serif;}
              body {background-color: #fff; border: 1px solid #ddd;
                    padding: 15px; margin: 15px;}
              pre {background-color: #eee; border: 1px solid #ddd; padding: 5px;}
            </style>
        </head>
        <body>
            <h1>Error: {{e.status}}</h1>
            <p>Sorry, the requested URL <tt>{{repr(request.url)}}</tt>
               caused an error:</p>
            <pre>{{e.body}}</pre>
            %%if DEBUG and e.exception:
              <h2>Exception:</h2>
              <pre>{{repr(e.exception)}}</pre>
            %%end
            %%if DEBUG and e.traceback:
              <h2>Traceback:</h2>
              <pre>{{e.traceback}}</pre>
            %%end
        </body>
    </html>
%%except ImportError:
    <b>ImportError:</b> Could not generate the error page. Please add bottle to
    the import path.
%%end
""" % __name__

#: A thread-safe instance of :class:`LocalRequest`. If accessed from within a
#: request callback, this instance always refers to the *current* request
#: (even on a multithreaded server).
request = LocalRequest()

#: A thread-safe instance of :class:`LocalResponse`. It is used to change the
#: HTTP response for the *current* request.
response = LocalResponse()

#: A thread-safe namespace. Not used by Bottle.
local = threading.local()

# Initialize app stack (create first empty Bottle app)
# BC: 0.6.4 and needed for run()
app = default_app = AppStack()
app.push()

#: A virtual package that redirects import statements.
#: Example: ``import bottle.ext.sqlite`` actually imports `bottle_sqlite`.
ext = _ImportRedirect('bottle.ext' if __name__ == '__main__' else __name__+".ext", 'bottle_%s').module

if __name__ == '__main__':
    opt, args, parser = _cmd_options, _cmd_args, _cmd_parser
    if opt.version:
        _stdout('Bottle %s\n'%__version__)
        sys.exit(0)
    if not args:
        parser.print_help()
        _stderr('\nError: No application entry point specified.\n')
        sys.exit(1)

    sys.path.insert(0, '.')
    sys.modules.setdefault('bottle', sys.modules['__main__'])

    host, port = (opt.bind or 'localhost'), 8080
    if ':' in host and host.rfind(']') < host.rfind(':'):
        host, port = host.rsplit(':', 1)
    host = host.strip('[]')

    run(args[0], host=host, port=int(port), server=opt.server,
        reloader=opt.reload, plugins=opt.plugin, debug=opt.debug)




# THE END

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-

import sys, os, time

bottle_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),'../'))
sys.path.insert(0, bottle_dir)
import bottle

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.viewcode']
master_doc = 'index'
project = u'Bottle'
copyright = u'2009-%s, %s' % (time.strftime('%Y'), bottle.__author__)
version = ".".join(bottle.__version__.split(".")[:2])
release = bottle.__version__
add_function_parentheses = True
add_module_names = False
pygments_style = 'sphinx'
intersphinx_mapping = {'python': ('http://docs.python.org/', None),
                       'werkzeug': ('http://werkzeug.pocoo.org/docs/', None)}

autodoc_member_order = 'bysource'


########NEW FILE########
__FILENAME__ = servertest
if __name__ != '__main__':
    raise ImportError('This is not a module, but a script.')

try:
    import coverage
    coverage.process_startup()
except ImportError:
    pass

import sys, os, socket
test_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(test_root)
sys.path.insert(0, os.path.dirname(test_root))
sys.path.insert(0, test_root)

try:
    server = sys.argv[1]
    port   = int(sys.argv[2])

    if server == 'gevent':
        from gevent import monkey
        monkey.patch_all()
    elif server == 'eventlet':
        import eventlet
        eventlet.monkey_patch()

    from bottle import route, run
    route('/test', callback=lambda: 'OK')
    run(port=port, server=server, quiet=True)

except socket.error:
    sys.exit(3)
except ImportError:
    sys.exit(128)
except KeyboardInterrupt:
    pass


########NEW FILE########
__FILENAME__ = testall
#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    import coverage
    coverage.process_startup()
except ImportError:
    pass

import unittest
import sys, os, glob

test_root = os.path.dirname(os.path.abspath(__file__))
test_files = glob.glob(os.path.join(test_root, 'test_*.py'))

os.chdir(test_root)
sys.path.insert(0, os.path.dirname(test_root))
sys.path.insert(0, test_root)
test_names = [os.path.basename(name)[:-3] for name in test_files]

if 'help' in sys.argv or '-h' in sys.argv:
    sys.stdout.write('''Command line arguments:
    fast: Skip server adapter tests.
    verbose: Print tests even if they pass.
    ''')
    sys.exit(0)

if 'fast' in sys.argv:
    sys.stderr.write("Warning: The 'fast' keyword skipps server tests.\n")
    test_names.remove('test_server')

suite = unittest.defaultTestLoader.loadTestsFromNames(test_names)

def run():
    import bottle

    bottle.debug(True)
    vlevel = 2 if 'verbose' in sys.argv else 0
    result = unittest.TextTestRunner(verbosity=vlevel).run(suite)

    sys.exit((result.errors or result.failures) and 1 or 0)

if __name__ == '__main__':
    run()


########NEW FILE########
__FILENAME__ = test_auth
# -*- coding: utf-8 -*-
import bottle
from tools import ServerTestBase

class TestBasicAuth(ServerTestBase):

    def test__header(self):
        @bottle.route('/')
        @bottle.auth_basic(lambda x, y: False)
        def test(): return {}
        self.assertStatus(401)
        self.assertHeader('Www-Authenticate', 'Basic realm="private"')

########NEW FILE########
__FILENAME__ = test_config
import unittest
from bottle import ConfigDict

class TestConfDict(unittest.TestCase):
    def test_write(self):
        c = ConfigDict()
        c['key'] = 'value'
        self.assertEqual(c['key'], 'value')
        self.assertTrue('key' in c)
        c['key'] = 'value2'
        self.assertEqual(c['key'], 'value2')

    def test_update(self):
        c = ConfigDict()
        c['key'] = 'value'
        c.update(key='value2', key2='value3')
        self.assertEqual(c['key'], 'value2')
        self.assertEqual(c['key2'], 'value3')

    def test_namespaces(self):
        c = ConfigDict()
        c.update('a.b', key='value')
        self.assertEqual(c['a.b.key'], 'value')

    def test_meta(self):
        c = ConfigDict()
        c.meta_set('bool', 'filter', bool)
        c.meta_set('int', 'filter', int)
        c['bool'] = 'I am so true!'
        c['int']  = '6'
        self.assertTrue(c['bool'] is True)
        self.assertEqual(c['int'], 6)
        self.assertRaises(ValueError, lambda: c.update(int='not an int'))

    def test_load_dict(self):
        c = ConfigDict()
        d = dict(a=dict(b=dict(foo=5, bar=6), baz=7))
        c.load_dict(d)
        self.assertEqual(c['a.b.foo'], 5)
        self.assertEqual(c['a.b.bar'], 6)
        self.assertEqual(c['a.baz'], 7)
   
if __name__ == '__main__': #pragma: no cover
    unittest.main()


########NEW FILE########
__FILENAME__ = test_configdict
import unittest
from bottle import ConfigDict

class TestConfigDict(unittest.TestCase):
    def test_isadict(self):
        """ ConfigDict should behaves like a normal dict. """
        # It is a dict-subclass, so this kind of pointless, but it doen't hurt.
        d, m = dict(), ConfigDict()
        d['key'], m['key'] = 'value', 'value'
        d['k2'], m['k2'] = 'v1', 'v1'
        d['k2'], m['k2'] = 'v2', 'v2'
        self.assertEqual(d.keys(), m.keys())
        self.assertEqual(list(d.values()), list(m.values()))
        self.assertEqual(d.get('key'), m.get('key'))
        self.assertEqual(d.get('cay'), m.get('cay'))
        self.assertEqual(list(iter(d)), list(iter(m)))
        self.assertEqual([k for k in d], [k for k in m])
        self.assertEqual(len(d), len(m))
        self.assertEqual('key' in d, 'key' in m)
        self.assertEqual('cay' in d, 'cay' in m)
        self.assertRaises(KeyError, lambda: m['cay'])


   
if __name__ == '__main__': #pragma: no cover
    unittest.main()


########NEW FILE########
__FILENAME__ = test_contextlocals
# -*- coding: utf-8 -*-
'''
Some objects are context-local, meaning that they have different values depending on the context they are accessed from. A context is currently defined as a thread.
'''

import unittest
import bottle
import threading


def run_thread(func):
    t = threading.Thread(target=func)
    t.start()
    t.join()

class TestThreadLocals(unittest.TestCase):
    def test_request(self):
        e1 = {'PATH_INFO': '/t1'}
        e2 = {'PATH_INFO': '/t2'}

        def run():
            bottle.request.bind(e2)
            self.assertEqual(bottle.request.path, '/t2')

        bottle.request.bind(e1)
        self.assertEqual(bottle.request.path, '/t1')
        run_thread(run)
        self.assertEqual(bottle.request.path, '/t1')

    def test_response(self):

        def run():
            bottle.response.bind()
            bottle.response.content_type='test/thread'
            self.assertEqual(bottle.response.headers['Content-Type'], 'test/thread')

        bottle.response.bind()
        bottle.response.content_type='test/main'
        self.assertEqual(bottle.response.headers['Content-Type'], 'test/main')
        run_thread(run)
        self.assertEqual(bottle.response.headers['Content-Type'], 'test/main')


if __name__ == '__main__': #pragma: no cover
    unittest.main()

########NEW FILE########
__FILENAME__ = test_environ
# -*- coding: utf-8 -*-
''' Tests for the BaseRequest and BaseResponse objects and their subclasses. '''

import unittest
import sys
import bottle
from bottle import request, tob, touni, tonat, json_dumps, _e, HTTPError, parse_date
import tools
import wsgiref.util
import base64

from bottle import BaseRequest, BaseResponse, LocalRequest

class TestRequest(unittest.TestCase):

    def test_app_property(self):
        e = {}
        r = BaseRequest(e)
        self.assertRaises(RuntimeError, lambda: r.app)
        e.update({'bottle.app': 5})
        self.assertEqual(r.app, 5)

    def test_route_property(self):
        e = {'bottle.route': 5}
        r = BaseRequest(e)
        self.assertEqual(r.route, 5)

    def test_url_for_property(self):
        e = {}
        r = BaseRequest(e)
        self.assertRaises(RuntimeError, lambda: r.url_args)
        e.update({'route.url_args': {'a': 5}})
        self.assertEqual(r.url_args, {'a': 5})

    def test_path(self):
        """ PATH_INFO normalization. """
        # Legal paths
        tests = [('', '/'), ('x','/x'), ('x/', '/x/'), ('/x', '/x'), ('/x/', '/x/')]
        for raw, norm in tests:
            self.assertEqual(norm, BaseRequest({'PATH_INFO': raw}).path)
        # Strange paths
        tests = [('///', '/'), ('//x','/x')]
        for raw, norm in tests:
            self.assertEqual(norm, BaseRequest({'PATH_INFO': raw}).path)
        # No path at all
        self.assertEqual('/', BaseRequest({}).path)

    def test_method(self):
        self.assertEqual(BaseRequest({}).method, 'GET')
        self.assertEqual(BaseRequest({'REQUEST_METHOD':'GET'}).method, 'GET')
        self.assertEqual(BaseRequest({'REQUEST_METHOD':'GeT'}).method, 'GET')
        self.assertEqual(BaseRequest({'REQUEST_METHOD':'get'}).method, 'GET')
        self.assertEqual(BaseRequest({'REQUEST_METHOD':'POst'}).method, 'POST')
        self.assertEqual(BaseRequest({'REQUEST_METHOD':'FanTASY'}).method, 'FANTASY')

    def test_script_name(self):
        """ SCRIPT_NAME normalization. """
        # Legal paths
        tests = [('', '/'), ('x','/x/'), ('x/', '/x/'), ('/x', '/x/'), ('/x/', '/x/')]
        for raw, norm in tests:
            self.assertEqual(norm, BaseRequest({'SCRIPT_NAME': raw}).script_name)
        # Strange paths
        tests = [('///', '/'), ('///x///','/x/')]
        for raw, norm in tests:
            self.assertEqual(norm, BaseRequest({'SCRIPT_NAME': raw}).script_name)
        # No path at all
        self.assertEqual('/', BaseRequest({}).script_name)

    def test_pathshift(self):
        """ Request.path_shift() """
        def test_shift(s, p, c):
            request = BaseRequest({'SCRIPT_NAME': s, 'PATH_INFO': p})
            request.path_shift(c)
            return [request['SCRIPT_NAME'], request.path]
        self.assertEqual(['/a/b', '/c/d'], test_shift('/a/b', '/c/d', 0))
        self.assertEqual(['/a/b', '/c/d/'], test_shift('/a/b', '/c/d/', 0))
        self.assertEqual(['/a/b/c', '/d'], test_shift('/a/b', '/c/d', 1))
        self.assertEqual(['/a', '/b/c/d'], test_shift('/a/b', '/c/d', -1))
        self.assertEqual(['/a/b/c', '/d/'], test_shift('/a/b', '/c/d/', 1))
        self.assertEqual(['/a', '/b/c/d/'], test_shift('/a/b', '/c/d/', -1))
        self.assertEqual(['/a/b/c', '/d/'], test_shift('/a/b/', '/c/d/', 1))
        self.assertEqual(['/a', '/b/c/d/'], test_shift('/a/b/', '/c/d/', -1))
        self.assertEqual(['/a/b/c/d', '/'], test_shift('/', '/a/b/c/d', 4))
        self.assertEqual(['/', '/a/b/c/d/'], test_shift('/a/b/c/d', '/', -4))
        self.assertRaises(AssertionError, test_shift, '/a/b', '/c/d', 3)
        self.assertRaises(AssertionError, test_shift, '/a/b', '/c/d', -3)

    def test_url(self):
        """ Environ: URL building """
        request = BaseRequest({'HTTP_HOST':'example.com'})
        self.assertEqual('http://example.com/', request.url)
        request = BaseRequest({'SERVER_NAME':'example.com'})
        self.assertEqual('http://example.com/', request.url)
        request = BaseRequest({'SERVER_NAME':'example.com', 'SERVER_PORT':'81'})
        self.assertEqual('http://example.com:81/', request.url)
        request = BaseRequest({'wsgi.url_scheme':'https', 'SERVER_NAME':'example.com'})
        self.assertEqual('https://example.com/', request.url)
        request = BaseRequest({'HTTP_HOST':'example.com', 'PATH_INFO':'/path',
                               'QUERY_STRING':'1=b&c=d', 'SCRIPT_NAME':'/sp'})
        self.assertEqual('http://example.com/sp/path?1=b&c=d', request.url)
        request = BaseRequest({'HTTP_HOST':'example.com', 'PATH_INFO':'/pa th',
                               'SCRIPT_NAME':'/s p'})
        self.assertEqual('http://example.com/s%20p/pa%20th', request.url)

    def test_dict_access(self):
        """ Environ: request objects are environment dicts """
        e = {}
        wsgiref.util.setup_testing_defaults(e)
        request = BaseRequest(e)
        self.assertEqual(list(request), list(e.keys()))
        self.assertEqual(len(request), len(e))
        for k, v in e.items():
            self.assertTrue(k in request)
            self.assertEqual(request[k], v)
            request[k] = 'test'
            self.assertEqual(request[k], 'test')
        del request['PATH_INFO']
        self.assertTrue('PATH_INFO' not in request)

    def test_readonly_environ(self):
        request = BaseRequest({'bottle.request.readonly':True})
        def test(): request['x']='y'
        self.assertRaises(KeyError, test)

    def test_header_access(self):
        """ Environ: Request objects decode headers """
        e = {}
        wsgiref.util.setup_testing_defaults(e)
        e['HTTP_SOME_HEADER'] = 'some value'
        request = BaseRequest(e)
        request['HTTP_SOME_OTHER_HEADER'] = 'some other value'
        self.assertTrue('Some-Header' in request.headers)
        self.assertTrue(request.headers['Some-Header'] == 'some value')
        self.assertTrue(request.headers['Some-Other-Header'] == 'some other value')

    def test_header_access_special(self):
        e = {}
        wsgiref.util.setup_testing_defaults(e)
        request = BaseRequest(e)
        request['CONTENT_TYPE'] = 'test'
        request['CONTENT_LENGTH'] = '123'
        self.assertEqual(request.headers['Content-Type'], 'test')
        self.assertEqual(request.headers['Content-Length'], '123')

    def test_cookie_dict(self):
        """ Environ: Cookie dict """
        t = dict()
        t['a=a']      = {'a': 'a'}
        t['a=a; b=b'] = {'a': 'a', 'b':'b'}
        t['a=a; a=b'] = {'a': 'b'}
        for k, v in t.items():
            request = BaseRequest({'HTTP_COOKIE': k})
            for n in v:
                self.assertEqual(v[n], request.cookies[n])
                self.assertEqual(v[n], request.get_cookie(n))

    def test_get(self):
        """ Environ: GET data """
        qs = tonat(tob('a=a&a=1&b=b&c=c&cn=%e7%93%b6'), 'latin1')
        request = BaseRequest({'QUERY_STRING':qs})
        self.assertTrue('a' in request.query)
        self.assertTrue('b' in request.query)
        self.assertEqual(['a','1'], request.query.getall('a'))
        self.assertEqual(['b'], request.query.getall('b'))
        self.assertEqual('1', request.query['a'])
        self.assertEqual('b', request.query['b'])
        self.assertEqual(tonat(tob('瓶'), 'latin1'), request.query['cn'])
        self.assertEqual(touni('瓶'), request.query.cn)

    def test_post(self):
        """ Environ: POST data """
        sq = tob('a=a&a=1&b=b&c=&d&cn=%e7%93%b6')
        e = {}
        wsgiref.util.setup_testing_defaults(e)
        e['wsgi.input'].write(sq)
        e['wsgi.input'].seek(0)
        e['CONTENT_LENGTH'] = str(len(sq))
        e['REQUEST_METHOD'] = "POST"
        request = BaseRequest(e)
        self.assertTrue('a' in request.POST)
        self.assertTrue('b' in request.POST)
        self.assertEqual(['a','1'], request.POST.getall('a'))
        self.assertEqual(['b'], request.POST.getall('b'))
        self.assertEqual('1', request.POST['a'])
        self.assertEqual('b', request.POST['b'])
        self.assertEqual('', request.POST['c'])
        self.assertEqual('', request.POST['d'])
        self.assertEqual(tonat(tob('瓶'), 'latin1'), request.POST['cn'])
        self.assertEqual(touni('瓶'), request.POST.cn)

    def test_bodypost(self):
        sq = tob('foobar')
        e = {}
        wsgiref.util.setup_testing_defaults(e)
        e['wsgi.input'].write(sq)
        e['wsgi.input'].seek(0)
        e['CONTENT_LENGTH'] = str(len(sq))
        e['REQUEST_METHOD'] = "POST"
        request = BaseRequest(e)
        self.assertEqual('', request.POST['foobar'])

    def test_body_noclose(self):
        """ Test that the body file handler is not closed after request.POST """
        sq = tob('a=a&a=1&b=b&c=&d')
        e = {}
        wsgiref.util.setup_testing_defaults(e)
        e['wsgi.input'].write(sq)
        e['wsgi.input'].seek(0)
        e['CONTENT_LENGTH'] = str(len(sq))
        e['REQUEST_METHOD'] = "POST"
        request = BaseRequest(e)
        self.assertEqual(sq, request.body.read())
        request.POST # This caused a body.close() with Python 3.x
        self.assertEqual(sq, request.body.read())

    def test_params(self):
        """ Environ: GET and POST are combined in request.param """
        e = {}
        wsgiref.util.setup_testing_defaults(e)
        e['wsgi.input'].write(tob('b=b&c=p'))
        e['wsgi.input'].seek(0)
        e['CONTENT_LENGTH'] = '7'
        e['QUERY_STRING'] = 'a=a&c=g'
        e['REQUEST_METHOD'] = "POST"
        request = BaseRequest(e)
        self.assertEqual(['a','b','c'], sorted(request.params.keys()))
        self.assertEqual('p', request.params['c'])

    def test_getpostleak(self):
        """ Environ: GET and POST should not leak into each other """
        e = {}
        wsgiref.util.setup_testing_defaults(e)
        e['wsgi.input'].write(tob('b=b'))
        e['wsgi.input'].seek(0)
        e['CONTENT_LENGTH'] = '3'
        e['QUERY_STRING'] = 'a=a'
        e['REQUEST_METHOD'] = "POST"
        request = BaseRequest(e)
        self.assertEqual(['a'], list(request.GET.keys()))
        self.assertEqual(['b'], list(request.POST.keys()))

    def test_body(self):
        """ Environ: Request.body should behave like a file object factory """
        e = {}
        wsgiref.util.setup_testing_defaults(e)
        e['wsgi.input'].write(tob('abc'))
        e['wsgi.input'].seek(0)
        e['CONTENT_LENGTH'] = str(3)
        request = BaseRequest(e)
        self.assertEqual(tob('abc'), request.body.read())
        self.assertEqual(tob('abc'), request.body.read(3))
        self.assertEqual(tob('abc'), request.body.readline())
        self.assertEqual(tob('abc'), request.body.readline(3))

    def test_bigbody(self):
        """ Environ: Request.body should handle big uploads using files """
        e = {}
        wsgiref.util.setup_testing_defaults(e)
        e['wsgi.input'].write(tob('x')*1024*1000)
        e['wsgi.input'].seek(0)
        e['CONTENT_LENGTH'] = str(1024*1000)
        request = BaseRequest(e)
        self.assertTrue(hasattr(request.body, 'fileno'))
        self.assertEqual(1024*1000, len(request.body.read()))
        self.assertEqual(1024, len(request.body.read(1024)))
        self.assertEqual(1024*1000, len(request.body.readline()))
        self.assertEqual(1024, len(request.body.readline(1024)))

    def test_tobigbody(self):
        """ Environ: Request.body should truncate to Content-Length bytes """
        e = {}
        wsgiref.util.setup_testing_defaults(e)
        e['wsgi.input'].write(tob('x')*1024)
        e['wsgi.input'].seek(0)
        e['CONTENT_LENGTH'] = '42'
        request = BaseRequest(e)
        self.assertEqual(42, len(request.body.read()))
        self.assertEqual(42, len(request.body.read(1024)))
        self.assertEqual(42, len(request.body.readline()))
        self.assertEqual(42, len(request.body.readline(1024)))

    def _test_chunked(self, body, expect):
        e = {}
        wsgiref.util.setup_testing_defaults(e)
        e['wsgi.input'].write(tob(body))
        e['wsgi.input'].seek(0)
        e['HTTP_TRANSFER_ENCODING'] = 'chunked'
        if isinstance(expect, str):
            self.assertEqual(tob(expect), BaseRequest(e).body.read())
        else:
            self.assertRaises(expect, lambda: BaseRequest(e).body)

    def test_chunked(self):
        self._test_chunked('1\r\nx\r\nff\r\n' + 'y'*255 + '\r\n0\r\n',
                           'x' + 'y'*255)
        self._test_chunked('8\r\nxxxxxxxx\r\n0\r\n','xxxxxxxx')
        self._test_chunked('0\r\n', '')

    def test_chunked_meta_fields(self):
        self._test_chunked('8 ; foo\r\nxxxxxxxx\r\n0\r\n','xxxxxxxx')
        self._test_chunked('8;foo\r\nxxxxxxxx\r\n0\r\n','xxxxxxxx')
        self._test_chunked('8;foo=bar\r\nxxxxxxxx\r\n0\r\n','xxxxxxxx')

    def test_chunked_not_terminated(self):
        self._test_chunked('1\r\nx\r\n', HTTPError)

    def test_chunked_wrong_size(self):
        self._test_chunked('2\r\nx\r\n', HTTPError)

    def test_chunked_illegal_size(self):
        self._test_chunked('x\r\nx\r\n', HTTPError)

    def test_chunked_not_chunked_at_all(self):
        self._test_chunked('abcdef', HTTPError)

    def test_multipart(self):
        """ Environ: POST (multipart files and multible values per key) """
        fields = [('field1','value1'), ('field2','value2'), ('field2','value3')]
        files = [('file1','filename1.txt','content1'), ('万难','万难foo.py', 'ä\nö\rü')]
        e = tools.multipart_environ(fields=fields, files=files)
        request = BaseRequest(e)
        # File content
        self.assertTrue('file1' in request.POST)
        self.assertTrue('file1' in request.files)
        self.assertTrue('file1' not in request.forms)
        cmp = tob('content1') if sys.version_info >= (3,2,0) else 'content1'
        self.assertEqual(cmp, request.POST['file1'].file.read())
        # File name and meta data
        self.assertTrue('万难' in request.POST)
        self.assertTrue('万难' in request.files)
        self.assertTrue('万难' not in request.forms)
        self.assertEqual('foo.py', request.POST['万难'].filename)
        self.assertTrue(request.files['万难'])
        self.assertFalse(request.files.file77)
        # UTF-8 files
        x = request.POST['万难'].file.read()
        if (3,2,0) > sys.version_info >= (3,0,0):
            x = x.encode('utf8')
        self.assertEqual(tob('ä\nö\rü'), x)
        # No file
        self.assertTrue('file3' not in request.POST)
        self.assertTrue('file3' not in request.files)
        self.assertTrue('file3' not in request.forms)
        # Field (single)
        self.assertEqual('value1', request.POST['field1'])
        self.assertTrue('field1' not in request.files)
        self.assertEqual('value1', request.forms['field1'])
        # Field (multi)
        self.assertEqual(2, len(request.POST.getall('field2')))
        self.assertEqual(['value2', 'value3'], request.POST.getall('field2'))
        self.assertEqual(['value2', 'value3'], request.forms.getall('field2'))
        self.assertTrue('field2' not in request.files)

    def test_json_empty(self):
        """ Environ: Request.json property with empty body. """
        self.assertEqual(BaseRequest({}).json, None)

    def test_json_noheader(self):
        """ Environ: Request.json property with missing content-type header. """
        test = dict(a=5, b='test', c=[1,2,3])
        e = {}
        wsgiref.util.setup_testing_defaults(e)
        e['wsgi.input'].write(tob(json_dumps(test)))
        e['wsgi.input'].seek(0)
        e['CONTENT_LENGTH'] = str(len(json_dumps(test)))
        self.assertEqual(BaseRequest(e).json, None)

    def test_json_tobig(self):
        """ Environ: Request.json property with huge body. """
        test = dict(a=5, tobig='x' * bottle.BaseRequest.MEMFILE_MAX)
        e = {'CONTENT_TYPE': 'application/json'}
        wsgiref.util.setup_testing_defaults(e)
        e['wsgi.input'].write(tob(json_dumps(test)))
        e['wsgi.input'].seek(0)
        e['CONTENT_LENGTH'] = str(len(json_dumps(test)))
        self.assertRaises(HTTPError, lambda: BaseRequest(e).json)

    def test_json_valid(self):
        """ Environ: Request.json property. """
        test = dict(a=5, b='test', c=[1,2,3])
        e = {'CONTENT_TYPE': 'application/json; charset=UTF-8'}
        wsgiref.util.setup_testing_defaults(e)
        e['wsgi.input'].write(tob(json_dumps(test)))
        e['wsgi.input'].seek(0)
        e['CONTENT_LENGTH'] = str(len(json_dumps(test)))
        self.assertEqual(BaseRequest(e).json, test)

    def test_json_forged_header_issue616(self):
        test = dict(a=5, b='test', c=[1,2,3])
        e = {'CONTENT_TYPE': 'text/plain;application/json'}
        wsgiref.util.setup_testing_defaults(e)
        e['wsgi.input'].write(tob(json_dumps(test)))
        e['wsgi.input'].seek(0)
        e['CONTENT_LENGTH'] = str(len(json_dumps(test)))
        self.assertEqual(BaseRequest(e).json, None)

    def test_json_header_empty_body(self):
        """Request Content-Type is application/json but body is empty"""
        e = {'CONTENT_TYPE': 'application/json'}
        wsgiref.util.setup_testing_defaults(e)
        wsgiref.util.setup_testing_defaults(e)
        e['CONTENT_LENGTH'] = "0"
        self.assertEqual(BaseRequest(e).json, None)

    def test_isajax(self):
        e = {}
        wsgiref.util.setup_testing_defaults(e)
        self.assertFalse(BaseRequest(e.copy()).is_ajax)
        e['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
        self.assertTrue(BaseRequest(e.copy()).is_ajax)

    def test_auth(self):
        user, pwd = 'marc', 'secret'
        basic = touni(base64.b64encode(tob('%s:%s' % (user, pwd))))
        r = BaseRequest({})
        self.assertEqual(r.auth, None)
        r.environ['HTTP_AUTHORIZATION'] = 'basic %s' % basic
        self.assertEqual(r.auth, (user, pwd))
        r.environ['REMOTE_USER'] = user
        self.assertEqual(r.auth, (user, pwd))
        del r.environ['HTTP_AUTHORIZATION']
        self.assertEqual(r.auth, (user, None))

    def test_remote_route(self):
        ips = ['1.2.3.4', '2.3.4.5', '3.4.5.6']
        r = BaseRequest({})
        self.assertEqual(r.remote_route, [])
        r.environ['HTTP_X_FORWARDED_FOR'] = ', '.join(ips)
        self.assertEqual(r.remote_route, ips)
        r.environ['REMOTE_ADDR'] = ips[1]
        self.assertEqual(r.remote_route, ips)
        del r.environ['HTTP_X_FORWARDED_FOR']
        self.assertEqual(r.remote_route, [ips[1]])

    def test_remote_addr(self):
        ips = ['1.2.3.4', '2.3.4.5', '3.4.5.6']
        r = BaseRequest({})
        self.assertEqual(r.remote_addr, None)
        r.environ['HTTP_X_FORWARDED_FOR'] = ', '.join(ips)
        self.assertEqual(r.remote_addr, ips[0])
        r.environ['REMOTE_ADDR'] = ips[1]
        self.assertEqual(r.remote_addr, ips[0])
        del r.environ['HTTP_X_FORWARDED_FOR']
        self.assertEqual(r.remote_addr, ips[1])

    def test_user_defined_attributes(self):
        for cls in (BaseRequest, LocalRequest):
            r = cls()

            # New attributes go to the environ dict.
            r.foo = 'somevalue'
            self.assertEqual(r.foo, 'somevalue')
            self.assertTrue('somevalue' in r.environ.values())

            # Unknown attributes raise AttributeError.
            self.assertRaises(AttributeError, getattr, r, 'somevalue')



class TestResponse(unittest.TestCase):

    def test_constructor_body(self):
        self.assertEqual('',
            BaseResponse('').body)

        self.assertEqual('YAY',
            BaseResponse('YAY').body)

    def test_constructor_status(self):
        self.assertEqual(200,
            BaseResponse('YAY', 200).status_code)

        self.assertEqual('200 OK',
            BaseResponse('YAY', 200).status_line)

        self.assertEqual('200 YAY',
            BaseResponse('YAY', '200 YAY').status_line)

        self.assertEqual('200 YAY',
            BaseResponse('YAY', '200 YAY').status_line)

    def test_constructor_headerlist(self):
        from functools import partial
        make_res = partial(BaseResponse, '', 200)

        self.assertTrue('yay',
            make_res([('x-test','yay')])['x-test'])

    def test_constructor_headerlist(self):
        from functools import partial
        make_res = partial(BaseResponse, '', 200)

        self.assertTrue('yay', make_res(x_test='yay')['x-test'])


    def test_set_status(self):
        rs = BaseResponse()

        rs.status = 200
        self.assertEqual(rs.status, rs.status_line)
        self.assertEqual(rs.status_code, 200)
        self.assertEqual(rs.status_line, '200 OK')

        rs.status = 999
        self.assertEqual(rs.status, rs.status_line)
        self.assertEqual(rs.status_code, 999)
        self.assertEqual(rs.status_line, '999 Unknown')

        rs.status = 404
        self.assertEqual(rs.status, rs.status_line)
        self.assertEqual(rs.status_code, 404)
        self.assertEqual(rs.status_line, '404 Not Found')

        def test(): rs.status = -200
        self.assertRaises(ValueError, test)
        self.assertEqual(rs.status, rs.status_line) # last value
        self.assertEqual(rs.status_code, 404) # last value
        self.assertEqual(rs.status_line, '404 Not Found') # last value

        def test(): rs.status = 5
        self.assertRaises(ValueError, test)
        self.assertEqual(rs.status, rs.status_line) # last value
        self.assertEqual(rs.status_code, 404) # last value
        self.assertEqual(rs.status_line, '404 Not Found') # last value

        rs.status = '999 Who knows?' # Illegal, but acceptable three digit code
        self.assertEqual(rs.status, rs.status_line)
        self.assertEqual(rs.status_code, 999)
        self.assertEqual(rs.status_line, '999 Who knows?')

        rs.status = 555 # Strange code
        self.assertEqual(rs.status, rs.status_line)
        self.assertEqual(rs.status_code, 555)
        self.assertEqual(rs.status_line, '555 Unknown')

        rs.status = '404 Brain not Found' # Custom reason
        self.assertEqual(rs.status, rs.status_line)
        self.assertEqual(rs.status_code, 404)
        self.assertEqual(rs.status_line, '404 Brain not Found')

        def test(): rs.status = '5 Illegal Code'
        self.assertRaises(ValueError, test)
        self.assertEqual(rs.status, rs.status_line) # last value
        self.assertEqual(rs.status_code, 404) # last value
        self.assertEqual(rs.status_line, '404 Brain not Found') # last value

        def test(): rs.status = '-99 Illegal Code'
        self.assertRaises(ValueError, test)
        self.assertEqual(rs.status, rs.status_line) # last value
        self.assertEqual(rs.status_code, 404) # last value
        self.assertEqual(rs.status_line, '404 Brain not Found') # last value

        def test(): rs.status = '1000 Illegal Code'
        self.assertRaises(ValueError, test)
        self.assertEqual(rs.status, rs.status_line) # last value
        self.assertEqual(rs.status_code, 404) # last value
        self.assertEqual(rs.status_line, '404 Brain not Found') # last value

        def test(): rs.status = '555' # No reason
        self.assertRaises(ValueError, test)
        self.assertEqual(rs.status, rs.status_line) # last value
        self.assertEqual(rs.status_code, 404) # last value
        self.assertEqual(rs.status_line, '404 Brain not Found') # last value

    def test_content_type(self):
        rs = BaseResponse()
        rs.content_type = 'test/some'
        self.assertEqual('test/some', rs.headers.get('Content-Type'))

    def test_charset(self):
        rs = BaseResponse()
        self.assertEqual(rs.charset, 'UTF-8')
        rs.content_type = 'text/html; charset=latin9'
        self.assertEqual(rs.charset, 'latin9')
        rs.content_type = 'text/html'
        self.assertEqual(rs.charset, 'UTF-8')

    def test_set_cookie(self):
        r = BaseResponse()
        r.set_cookie('name1', 'value', max_age=5)
        r.set_cookie('name2', 'value 2', path='/foo')
        cookies = [value for name, value in r.headerlist
                   if name.title() == 'Set-Cookie']
        cookies.sort()
        self.assertEqual(cookies[0], 'name1=value; Max-Age=5')
        self.assertEqual(cookies[1], 'name2="value 2"; Path=/foo')

    def test_set_cookie_maxage(self):
        import datetime
        r = BaseResponse()
        r.set_cookie('name1', 'value', max_age=5)
        r.set_cookie('name2', 'value', max_age=datetime.timedelta(days=1))
        cookies = sorted([value for name, value in r.headerlist
                   if name.title() == 'Set-Cookie'])
        self.assertEqual(cookies[0], 'name1=value; Max-Age=5')
        self.assertEqual(cookies[1], 'name2=value; Max-Age=86400')

    def test_set_cookie_expires(self):
        import datetime
        r = BaseResponse()
        r.set_cookie('name1', 'value', expires=42)
        r.set_cookie('name2', 'value', expires=datetime.datetime(1970,1,1,0,0,43))
        cookies = sorted([value for name, value in r.headerlist
                   if name.title() == 'Set-Cookie'])
        self.assertEqual(cookies[0], 'name1=value; expires=Thu, 01 Jan 1970 00:00:42 GMT')
        self.assertEqual(cookies[1], 'name2=value; expires=Thu, 01 Jan 1970 00:00:43 GMT')

    def test_delete_cookie(self):
        response = BaseResponse()
        response.set_cookie('name', 'value')
        response.delete_cookie('name')
        cookies = [value for name, value in response.headerlist
                   if name.title() == 'Set-Cookie']
        self.assertTrue('name=;' in cookies[0])

    def test_set_header(self):
        response = BaseResponse()
        response['x-test'] = 'foo'
        headers = [value for name, value in response.headerlist
                   if name.title() == 'X-Test']
        self.assertEqual(['foo'], headers)
        self.assertEqual('foo', response['x-test'])

        response['X-Test'] = 'bar'
        headers = [value for name, value in response.headerlist
                   if name.title() == 'X-Test']
        self.assertEqual(['bar'], headers)
        self.assertEqual('bar', response['x-test'])

    def test_append_header(self):
        response = BaseResponse()
        response.set_header('x-test', 'foo')
        headers = [value for name, value in response.headerlist
                   if name.title() == 'X-Test']
        self.assertEqual(['foo'], headers)
        self.assertEqual('foo', response['x-test'])

        response.add_header('X-Test', 'bar')
        headers = [value for name, value in response.headerlist
                   if name.title() == 'X-Test']
        self.assertEqual(['foo', 'bar'], headers)
        self.assertEqual('bar', response['x-test'])

    def test_delete_header(self):
        response = BaseResponse()
        response['x-test'] = 'foo'
        self.assertEqual('foo', response['x-test'])
        del response['X-tESt']
        self.assertRaises(KeyError, lambda: response['x-test'])

    def test_non_string_header(self):
        response = BaseResponse()
        response['x-test'] = 5
        self.assertEqual('5', response['x-test'])
        response['x-test'] = None
        self.assertEqual('None', response['x-test'])

    def test_expires_header(self):
        import datetime
        response = BaseResponse()
        now = datetime.datetime.now()
        response.expires = now
        
        def seconds(a, b):
            td = max(a,b) - min(a,b)
            return td.days*360*24 + td.seconds
        
        self.assertEqual(0, seconds(response.expires, now))
        now2 = datetime.datetime.utcfromtimestamp(
            parse_date(response.headers['Expires']))
        self.assertEqual(0, seconds(now, now2))

class TestRedirect(unittest.TestCase):

    def assertRedirect(self, target, result, query=None, status=303, **args):
        env = {'SERVER_PROTOCOL':'HTTP/1.1'}
        for key in list(args):
            if key.startswith('wsgi'):
                args[key.replace('_', '.', 1)] = args[key]
                del args[key]
        env.update(args)
        request.bind(env)
        bottle.response.bind()
        try:
            bottle.redirect(target, **(query or {}))
        except bottle.HTTPResponse:
            r = _e()
            self.assertEqual(status, r.status_code)
            self.assertTrue(r.headers)
            self.assertEqual(result, r.headers['Location'])

    def test_absolute_path(self):
        self.assertRedirect('/', 'http://127.0.0.1/')
        self.assertRedirect('/test.html', 'http://127.0.0.1/test.html')
        self.assertRedirect('/test.html', 'http://127.0.0.1/test.html',
                            PATH_INFO='/some/sub/path/')
        self.assertRedirect('/test.html', 'http://127.0.0.1/test.html',
                            PATH_INFO='/some/sub/file.html')
        self.assertRedirect('/test.html', 'http://127.0.0.1/test.html',
                            SCRIPT_NAME='/some/sub/path/')
        self.assertRedirect('/foo/test.html', 'http://127.0.0.1/foo/test.html')
        self.assertRedirect('/foo/test.html', 'http://127.0.0.1/foo/test.html',
                            PATH_INFO='/some/sub/file.html')

    def test_relative_path(self):
        self.assertRedirect('./', 'http://127.0.0.1/')
        self.assertRedirect('./test.html', 'http://127.0.0.1/test.html')
        self.assertRedirect('./test.html', 'http://127.0.0.1/foo/test.html',
                            PATH_INFO='/foo/')
        self.assertRedirect('./test.html', 'http://127.0.0.1/foo/test.html',
                            PATH_INFO='/foo/bar.html')
        self.assertRedirect('./test.html', 'http://127.0.0.1/foo/test.html',
                            SCRIPT_NAME='/foo/')
        self.assertRedirect('./test.html', 'http://127.0.0.1/foo/bar/test.html',
                            SCRIPT_NAME='/foo/', PATH_INFO='/bar/baz.html')
        self.assertRedirect('./foo/test.html', 'http://127.0.0.1/foo/test.html')
        self.assertRedirect('./foo/test.html', 'http://127.0.0.1/bar/foo/test.html',
                            PATH_INFO='/bar/file.html')
        self.assertRedirect('../test.html', 'http://127.0.0.1/test.html',
                            PATH_INFO='/foo/')
        self.assertRedirect('../test.html', 'http://127.0.0.1/foo/test.html',
                            PATH_INFO='/foo/bar/')
        self.assertRedirect('../test.html', 'http://127.0.0.1/test.html',
                            PATH_INFO='/foo/bar.html')
        self.assertRedirect('../test.html', 'http://127.0.0.1/test.html',
                            SCRIPT_NAME='/foo/')
        self.assertRedirect('../test.html', 'http://127.0.0.1/foo/test.html',
                            SCRIPT_NAME='/foo/', PATH_INFO='/bar/baz.html')
        self.assertRedirect('../baz/../test.html', 'http://127.0.0.1/foo/test.html',
                            PATH_INFO='/foo/bar/')

    def test_sheme(self):
        self.assertRedirect('./test.html', 'https://127.0.0.1/test.html',
                            wsgi_url_scheme='https')
        self.assertRedirect('./test.html', 'https://127.0.0.1:80/test.html',
                            wsgi_url_scheme='https', SERVER_PORT='80')

    def test_host_http_1_0(self):
        # No HTTP_HOST, just SERVER_NAME and SERVER_PORT.
        self.assertRedirect('./test.html', 'http://example.com/test.html',
                            SERVER_NAME='example.com',
                            SERVER_PROTOCOL='HTTP/1.0', status=302)
        self.assertRedirect('./test.html', 'http://127.0.0.1:81/test.html',
                            SERVER_PORT='81',
                            SERVER_PROTOCOL='HTTP/1.0', status=302)

    def test_host_http_1_1(self):
        self.assertRedirect('./test.html', 'http://example.com/test.html',
                            HTTP_HOST='example.com')
        self.assertRedirect('./test.html', 'http://example.com:81/test.html',
                            HTTP_HOST='example.com:81')
        # Trust HTTP_HOST over SERVER_NAME and PORT.
        self.assertRedirect('./test.html', 'http://example.com:81/test.html',
                            HTTP_HOST='example.com:81', SERVER_NAME='foobar')
        self.assertRedirect('./test.html', 'http://example.com:81/test.html',
                            HTTP_HOST='example.com:81', SERVER_PORT='80')

    def test_host_http_proxy(self):
        # Trust proxy headers over original header.
        self.assertRedirect('./test.html', 'http://example.com/test.html',
                            HTTP_X_FORWARDED_HOST='example.com',
                            HTTP_HOST='127.0.0.1')

    def test_specialchars(self):
        ''' The target URL is not quoted automatically. '''
        self.assertRedirect('./te st.html',
                            'http://example.com/a%20a/b%20b/te st.html',
                            HTTP_HOST='example.com', SCRIPT_NAME='/a a/', PATH_INFO='/b b/')

    def test_redirect_preserve_cookies(self):
        env = {'SERVER_PROTOCOL':'HTTP/1.1'}
        request.bind(env)
        bottle.response.bind()
        try:
            bottle.response.set_cookie('xxx', 'yyy')
            bottle.redirect('...')
        except bottle.HTTPResponse:
            h = [v for (k, v) in _e().headerlist if k == 'Set-Cookie']
            self.assertEqual(h, ['xxx=yyy'])

class TestWSGIHeaderDict(unittest.TestCase):
    def setUp(self):
        self.env = {}
        self.headers = bottle.WSGIHeaderDict(self.env)

    def test_empty(self):
        self.assertEqual(0, len(bottle.WSGIHeaderDict({})))

    def test_native(self):
        self.env['HTTP_TEST_HEADER'] = 'foobar'
        self.assertEqual(self.headers['Test-header'], 'foobar')

    def test_bytes(self):
        self.env['HTTP_TEST_HEADER'] = tob('foobar')
        self.assertEqual(self.headers['Test-Header'], 'foobar')

    def test_unicode(self):
        self.env['HTTP_TEST_HEADER'] = touni('foobar')
        self.assertEqual(self.headers['Test-Header'], 'foobar')

    def test_dict(self):
        for key in 'foo-bar Foo-Bar foo-Bar FOO-BAR'.split():
            self.assertTrue(key not in self.headers)
            self.assertEqual(self.headers.get(key), None)
            self.assertEqual(self.headers.get(key, 5), 5)
            self.assertRaises(KeyError, lambda x: self.headers[x], key)
        self.env['HTTP_FOO_BAR'] = 'test'
        for key in 'foo-bar Foo-Bar foo-Bar FOO-BAR'.split():
            self.assertTrue(key in self.headers)
            self.assertEqual(self.headers.get(key), 'test')
            self.assertEqual(self.headers.get(key, 5), 'test')



if __name__ == '__main__': #pragma: no cover
    unittest.main()

########NEW FILE########
__FILENAME__ = test_fileupload
# -*- coding: utf-8 -*-
''' Tests for the FileUpload wrapper. '''

import unittest
import sys, os.path
import bottle
from bottle import FileUpload, BytesIO
import tempfile

class TestFileUpload(unittest.TestCase):
    def test_name(self):
        self.assertEqual(FileUpload(None, 'abc', None).name, 'abc')

    def test_raw_filename(self):
        self.assertEqual(FileUpload(None, None, 'x/x').raw_filename, 'x/x')

    def assertFilename(self, bad, good):
        fu = FileUpload(None, None, bad)
        self.assertEqual(fu.filename, good)
        
    def test_filename(self):
        self.assertFilename('with space', 'with-space')
        self.assertFilename('with more  \t\n\r space', 'with-more-space')
        self.assertFilename('with/path', 'path')
        self.assertFilename('../path', 'path')
        self.assertFilename('..\\path', 'path')
        self.assertFilename('..', 'empty')
        self.assertFilename('.name.', 'name')
        self.assertFilename('.name.cfg', 'name.cfg')
        self.assertFilename(' . na me . ', 'na-me')
        self.assertFilename('path/', 'empty')
        self.assertFilename(bottle.tob('ümläüts$'), 'umlauts')
        self.assertFilename(bottle.touni('ümläüts$'), 'umlauts')
        self.assertFilename('', 'empty')
        self.assertFilename('a'+'b'*1337+'c', 'a'+'b'*254)

    def test_preserve_case_issue_582(self):
        self.assertFilename('UpperCase', 'UpperCase')

    def test_save_buffer(self):
        fu = FileUpload(open(__file__, 'rb'), 'testfile', __file__)
        buff = BytesIO()
        fu.save(buff)
        buff.seek(0)
        self.assertEqual(fu.file.read(), buff.read())

    def test_save_file(self):
        fu = FileUpload(open(__file__, 'rb'), 'testfile', __file__)
        buff = tempfile.TemporaryFile()
        fu.save(buff)
        buff.seek(0)
        self.assertEqual(fu.file.read(), buff.read())

    def test_save_overwrite_lock(self):
        fu = FileUpload(open(__file__, 'rb'), 'testfile', __file__)
        self.assertRaises(IOError, fu.save, __file__)

    def test_save_dir(self):
        fu = FileUpload(open(__file__, 'rb'), 'testfile', __file__)
        dirpath = tempfile.mkdtemp()
        filepath = os.path.join(dirpath, fu.filename)
        fu.save(dirpath)
        self.assertEqual(fu.file.read(), open(filepath, 'rb').read())
        os.unlink(filepath)
        os.rmdir(dirpath)
                

########NEW FILE########
__FILENAME__ = test_formsdict
# -*- coding: utf-8 -*-
# '瓶' means "Bottle"

import unittest
from bottle import FormsDict, touni, tob

class TestFormsDict(unittest.TestCase):
    def test_attr_access(self):
        """ FomsDict.attribute returs string values as unicode. """
        d = FormsDict(py2=tob('瓶'), py3=tob('瓶').decode('latin1'))
        self.assertEqual(touni('瓶'), d.py2)
        self.assertEqual(touni('瓶'), d.py3)

    def test_attr_missing(self):
        """ FomsDict.attribute returs u'' on missing keys. """
        d = FormsDict()
        self.assertEqual(touni(''), d.missing)

    def test_attr_unicode_error(self):
        """ FomsDict.attribute returs u'' on UnicodeError. """
        d = FormsDict(latin=touni('öäüß').encode('latin1'))
        self.assertEqual(touni(''), d.latin)
        d.input_encoding = 'latin1'
        self.assertEqual(touni('öäüß'), d.latin)

    def test_decode_method(self):
        d = FormsDict(py2=tob('瓶'), py3=tob('瓶').decode('latin1'))
        d = d.decode()
        self.assertFalse(d.recode_unicode)
        self.assertTrue(hasattr(list(d.keys())[0], 'encode'))
        self.assertTrue(hasattr(list(d.values())[0], 'encode'))

if __name__ == '__main__': #pragma: no cover
    unittest.main()


########NEW FILE########
__FILENAME__ = test_importhook
# -*- coding: utf-8 -*-
import unittest
import sys, os
import imp

class TestImportHooks(unittest.TestCase):

    def make_module(self, name, **args):
        mod = sys.modules.setdefault(name, imp.new_module(name))
        mod.__file__ = '<virtual %s>' % name
        mod.__dict__.update(**args)
        return mod

    def test_direkt_import(self):
        mod = self.make_module('bottle_test')
        import bottle.ext.test
        self.assertEqual(bottle.ext.test, mod)

    def test_from_import(self):
        mod = self.make_module('bottle_test')
        from bottle.ext import test
        self.assertEqual(test, mod)

    def test_data_import(self):
        mod = self.make_module('bottle_test', item='value')
        from bottle.ext.test import item
        self.assertEqual(item, 'value')

    def test_import_fail(self):
        ''' Test a simple static page with this server adapter. '''
        def test():
            import bottle.ext.doesnotexist
        self.assertRaises(ImportError, test)

    def test_ext_isfile(self):
        ''' The virtual module needs a valid __file__ attribute.
            If not, the Google app engine development server crashes on windows.
        '''
        from bottle import ext
        self.assertTrue(os.path.isfile(ext.__file__))
        
if __name__ == '__main__': #pragma: no cover
    unittest.main()

########NEW FILE########
__FILENAME__ = test_jinja2
# -*- coding: utf-8 -*-
import unittest
from bottle import Jinja2Template, jinja2_template, jinja2_view, touni
from tools import warn


class TestJinja2Template(unittest.TestCase):

    def test_string(self):
        """ Templates: Jinja2 string"""
        t = Jinja2Template('start {{var}} end').render(var='var')
        self.assertEqual('start var end', ''.join(t))

    def test_file(self):
        """ Templates: Jinja2 file"""
        t = Jinja2Template(name='./views/jinja2_simple.tpl').render(var='var')
        self.assertEqual('start var end', ''.join(t))

    def test_name(self):
        """ Templates: Jinja2 lookup by name """
        t = Jinja2Template(name='jinja2_simple', lookup=['./views/']).render(var='var')
        self.assertEqual('start var end', ''.join(t))

    def test_notfound(self):
        """ Templates: Unavailable templates"""
        self.assertRaises(Exception, Jinja2Template, name="abcdef")

    def test_error(self):
        """ Templates: Exceptions"""
        self.assertRaises(Exception, Jinja2Template, '{% for badsyntax')

    def test_inherit(self):
        """ Templates: Jinja2 lookup and inherience """
        t = Jinja2Template(name='jinja2_inherit', lookup=['./views/']).render()
        self.assertEqual('begin abc end', ''.join(t))

    def test_custom_filters(self):
        """Templates: jinja2 custom filters """
        from bottle import jinja2_template as template
        settings = dict(filters = {"star": lambda var: touni("").join((touni('*'), var, touni('*')))})
        t = Jinja2Template("start {{var|star}} end", **settings)
        self.assertEqual("start *var* end", t.render(var="var"))

    def test_custom_tests(self):
        """Templates: jinja2 custom tests """
        from bottle import jinja2_template as template
        TEMPL = touni("{% if var is even %}gerade{% else %}ungerade{% endif %}")
        settings = dict(tests={"even": lambda x: False if x % 2 else True})
        t = Jinja2Template(TEMPL, **settings)
        self.assertEqual("gerade", t.render(var=2))
        self.assertEqual("ungerade", t.render(var=1))

    def test_template_shortcut(self):
        result = jinja2_template('start {{var}} end', var='middle')
        self.assertEqual(touni('start middle end'), result)

    def test_view_decorator(self):
        @jinja2_view('start {{var}} end')
        def test():
            return dict(var='middle')
        self.assertEqual(touni('start middle end'), test())


try:
  import jinja2
except ImportError:
  warn("No Jinja2 template support. Skipping tests.")
  del TestJinja2Template

if __name__ == '__main__': #pragma: no cover
    unittest.main()


########NEW FILE########
__FILENAME__ = test_mako
import unittest
from tools import warn
from bottle import MakoTemplate, mako_template, mako_view, touni

class TestMakoTemplate(unittest.TestCase):
    def test_string(self):
        """ Templates: Mako string"""
        t = MakoTemplate('start ${var} end').render(var='var')
        self.assertEqual('start var end', t)

    def test_file(self):
        """ Templates: Mako file"""
        t = MakoTemplate(name='./views/mako_simple.tpl').render(var='var')
        self.assertEqual('start var end\n', t)

    def test_name(self):
        """ Templates: Mako lookup by name """
        t = MakoTemplate(name='mako_simple', lookup=['./views/']).render(var='var')
        self.assertEqual('start var end\n', t)

    def test_notfound(self):
        """ Templates: Unavailable templates"""
        self.assertRaises(Exception, MakoTemplate, name="abcdef")

    def test_error(self):
        """ Templates: Exceptions"""
        self.assertRaises(Exception, MakoTemplate, '%for badsyntax')

    def test_inherit(self):
        """ Templates: Mako lookup and inherience """
        t = MakoTemplate(name='mako_inherit', lookup=['./views/']).render(var='v')
        self.assertEqual('o\ncvc\no\n', t)
        t = MakoTemplate('<%inherit file="mako_base.tpl"/>\nc${var}c\n', lookup=['./views/']).render(var='v')
        self.assertEqual('o\ncvc\no\n', t)
        t = MakoTemplate('<%inherit file="views/mako_base.tpl"/>\nc${var}c\n', lookup=['./']).render(var='v')
        self.assertEqual('o\ncvc\no\n', t)

    def test_template_shortcut(self):
        result = mako_template('start ${var} end', var='middle')
        self.assertEqual(touni('start middle end'), result)

    def test_view_decorator(self):
        @mako_view('start ${var} end')
        def test():
            return dict(var='middle')
        self.assertEqual(touni('start middle end'), test())


try:
  import mako
except ImportError:
  warn("No Mako template support. Skipping tests.")
  del TestMakoTemplate

if __name__ == '__main__': #pragma: no cover
    unittest.main()


########NEW FILE########
__FILENAME__ = test_mdict
import unittest
from bottle import MultiDict, HeaderDict

class TestMultiDict(unittest.TestCase):
    def test_isadict(self):
        """ MultiDict should behaves like a normal dict """
        d, m = dict(a=5), MultiDict(a=5)
        d['key'], m['key'] = 'value', 'value'
        d['k2'], m['k2'] = 'v1', 'v1'
        d['k2'], m['k2'] = 'v2', 'v2'
        self.assertEqual(list(d.keys()), list(m.keys()))
        self.assertEqual(list(d.values()), list(m.values()))
        self.assertEqual(list(d.keys()), list(m.iterkeys()))
        self.assertEqual(list(d.values()), list(m.itervalues()))
        self.assertEqual(d.get('key'), m.get('key'))
        self.assertEqual(d.get('cay'), m.get('cay'))
        self.assertEqual(list(iter(d)), list(iter(m)))
        self.assertEqual([k for k in d], [k for k in m])
        self.assertEqual(len(d), len(m))
        self.assertEqual('key' in d, 'key' in m)
        self.assertEqual('cay' in d, 'cay' in m)
        self.assertRaises(KeyError, lambda: m['cay'])
       
    def test_ismulti(self):
        """ MultiDict has some special features """
        m = MultiDict(a=5)
        m['a'] = 6
        self.assertEqual([5, 6], m.getall('a'))
        self.assertEqual([], m.getall('b'))
        self.assertEqual([('a', 5), ('a', 6)], list(m.iterallitems()))
   
    def test_isheader(self):
        """ HeaderDict replaces by default and title()s its keys """
        m = HeaderDict(abc_def=5)
        m['abc_def'] = 6
        self.assertEqual(['6'], m.getall('abc_def'))
        m.append('abc_def', 7)
        self.assertEqual(['6', '7'], m.getall('abc_def'))
        self.assertEqual([('Abc-Def', '6'), ('Abc-Def', '7')], list(m.iterallitems()))
    
    def test_headergetbug(self):
        ''' Assure HeaderDict.get() to be case insensitive '''
        d = HeaderDict()
        d['UPPER'] = 'UPPER'
        d['lower'] = 'lower'
        self.assertEqual(d.get('upper'), 'UPPER')
        self.assertEqual(d.get('LOWER'), 'lower')


   
if __name__ == '__main__': #pragma: no cover
    unittest.main()


########NEW FILE########
__FILENAME__ = test_mount
import bottle
from tools import ServerTestBase
from bottle import response

class TestAppMounting(ServerTestBase):
    def setUp(self):
        ServerTestBase.setUp(self)
        self.subapp = bottle.Bottle()
        @self.subapp.route('/')
        @self.subapp.route('/test/:test')
        def test(test='foo'):
            return test


    def test_mount_order_bug581(self):
        self.app.mount('/test/', self.subapp)

        # This should not match
        self.app.route('/<test:path>', callback=lambda test: test)

        self.assertStatus(200, '/test/')
        self.assertBody('foo', '/test/')

    def test_mount(self):
        self.app.mount('/test/', self.subapp)
        self.assertStatus(404, '/')
        self.assertStatus(404, '/test')
        self.assertStatus(200, '/test/')
        self.assertBody('foo', '/test/')
        self.assertStatus(200, '/test/test/bar')
        self.assertBody('bar', '/test/test/bar')

    def test_mount_meta(self):
        self.app.mount('/test/', self.subapp)
        self.assertEqual(
            self.app.routes[0].config['mountpoint.prefix'],
            '/test/')
        self.assertEqual(
            self.app.routes[0].config['mountpoint.target'],
            self.subapp)

    def test_no_slash_prefix(self):
        self.app.mount('/test', self.subapp)
        self.assertStatus(404, '/')
        self.assertStatus(200, '/test')
        self.assertBody('foo', '/test')
        self.assertStatus(200, '/test/')
        self.assertBody('foo', '/test/')
        self.assertStatus(200, '/test/test/bar')
        self.assertBody('bar', '/test/test/bar')

    def test_mount_no_plugins(self):
        def plugin(func):
            def wrapper(*a, **ka):
                return 'Plugin'
            return wrapper
        self.app.install(plugin)
        self.app.route('/foo', callback=lambda: 'baz')
        self.app.mount('/test/', self.subapp)
        self.assertBody('Plugin', '/foo')
        self.assertBody('foo', '/test/')

    def test_mount_wsgi(self):
        status = {}
        def app(environ, start_response):
            start_response('200 OK', [('X-Test', 'WSGI')])
            return 'WSGI ' + environ['PATH_INFO']
        self.app.mount('/test', app)
        self.assertStatus(200, '/test/')
        self.assertBody('WSGI /', '/test')
        self.assertBody('WSGI /', '/test/')
        self.assertHeader('X-Test', 'WSGI', '/test/')
        self.assertBody('WSGI /test/bar', '/test/test/bar')
            
    def test_mount_wsgi(self):
        @self.subapp.route('/cookie')
        def test_cookie():
            response.set_cookie('a', 'a')
            response.set_cookie('b', 'b')
        self.app.mount('/test', self.subapp)
        c = self.urlopen('/test/cookie')['header']['Set-Cookie']
        self.assertEqual(['a=a', 'b=b'], list(sorted(c.split(', '))))

    def test_mount_wsgi_ctype_bug(self):
        status = {}
        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'test/test')])
            return 'WSGI ' + environ['PATH_INFO']
        self.app.mount('/test', app)
        self.assertHeader('Content-Type', 'test/test', '/test/')

    def test_mount_json_bug(self):
        @self.subapp.route('/json')
        def test_cookie():
            return {'a':5}
        self.app.mount('/test', self.subapp)
        self.assertHeader('Content-Type', 'application/json', '/test/json')

class TestAppMerging(ServerTestBase):
    def setUp(self):
        ServerTestBase.setUp(self)
        self.subapp = bottle.Bottle()
        @self.subapp.route('/')
        @self.subapp.route('/test/:test')
        def test(test='foo'):
            return test

    def test_merge(self):
        self.app.merge(self.subapp)
        self.assertStatus(200, '/')
        self.assertBody('foo', '/')
        self.assertStatus(200, '/test/bar')
        self.assertBody('bar', '/test/bar')



if __name__ == '__main__': #pragma: no cover
    unittest.main()

########NEW FILE########
__FILENAME__ = test_outputfilter
# -*- coding: utf-8 -*-
'''Everything returned by Bottle()._cast() MUST be WSGI compatiple.'''

import unittest
import bottle
from bottle import tob, touni
from tools import ServerTestBase, tobs, warn

class TestOutputFilter(ServerTestBase):
    ''' Tests for WSGI functionality, routing and output casting (decorators) '''

    def test_bytes(self):
        self.app.route('/')(lambda: tob('test'))
        self.assertBody('test')

    def test_bytearray(self):
        self.app.route('/')(lambda: map(tob, ['t', 'e', 'st']))
        self.assertBody('test')

    def test_tuple(self):
        self.app.route('/')(lambda: ('t', 'e', 'st'))
        self.assertBody('test')

    def test_emptylist(self):
        self.app.route('/')(lambda: [])
        self.assertBody('')

    def test_none(self):
        self.app.route('/')(lambda: None)
        self.assertBody('')

    def test_illegal(self):
        self.app.route('/')(lambda: 1234)
        self.assertStatus(500)
        self.assertInBody('Unhandled exception')

    def test_error(self):
        self.app.route('/')(lambda: 1/0)
        self.assertStatus(500)
        self.assertInBody('ZeroDivisionError')

    def test_fatal_error(self):
        @self.app.route('/')
        def test(): raise KeyboardInterrupt()
        self.assertRaises(KeyboardInterrupt, self.assertStatus, 500)

    def test_file(self):
        self.app.route('/')(lambda: tobs('test'))
        self.assertBody('test')

    def test_unicode(self):
        self.app.route('/')(lambda: touni('äöüß'))
        self.assertBody(touni('äöüß').encode('utf8'))

        self.app.route('/')(lambda: [touni('äö'), touni('üß')])
        self.assertBody(touni('äöüß').encode('utf8'))

        @self.app.route('/')
        def test5():
            bottle.response.content_type='text/html; charset=iso-8859-15'
            return touni('äöüß')
        self.assertBody(touni('äöüß').encode('iso-8859-15'))

        @self.app.route('/')
        def test5():
            bottle.response.content_type='text/html'
            return touni('äöüß')
        self.assertBody(touni('äöüß').encode('utf8'))

    def test_json(self):
        self.app.route('/')(lambda: {'a': 1})
        try:
            self.assertBody(bottle.json_dumps({'a': 1}))
            self.assertHeader('Content-Type','application/json')
        except ImportError:
            warn("Skipping JSON tests.")

    def test_json_serialization_error(self):
        """
        Verify that 500 errors serializing dictionaries don't return
        content-type application/json
        """
        self.app.route('/')(lambda: {'a': set()})
        try:
            self.assertStatus(500)
            self.assertHeader('Content-Type','text/html; charset=UTF-8')
        except ImportError:
            warn("Skipping JSON tests.")

    def test_json_HTTPResponse(self):
        self.app.route('/')(lambda: bottle.HTTPResponse({'a': 1}, 500))
        try:
            self.assertBody(bottle.json_dumps({'a': 1}))
            self.assertHeader('Content-Type','application/json')
        except ImportError:
            warn("Skipping JSON tests.")

    def test_json_HTTPError(self):
        self.app.error(400)(lambda e: e.body)
        self.app.route('/')(lambda: bottle.HTTPError(400, {'a': 1}))
        try:
            self.assertBody(bottle.json_dumps({'a': 1}))
            self.assertHeader('Content-Type','application/json')
        except ImportError:
            warn("Skipping JSON tests.")

    def test_generator_callback(self):
        @self.app.route('/')
        def test():
            bottle.response.headers['Test-Header'] = 'test'
            yield 'foo'
        self.assertBody('foo')
        self.assertHeader('Test-Header', 'test')

    def test_empty_generator_callback(self):
        @self.app.route('/')
        def test():
            yield
            bottle.response.headers['Test-Header'] = 'test'
        self.assertBody('')
        self.assertHeader('Test-Header', 'test')

    def test_error_in_generator_callback(self):
        @self.app.route('/')
        def test():
            yield 1/0
        self.assertStatus(500)
        self.assertInBody('ZeroDivisionError')

    def test_fatal_error_in_generator_callback(self):
        @self.app.route('/')
        def test():
            yield
            raise KeyboardInterrupt()
        self.assertRaises(KeyboardInterrupt, self.assertStatus, 500)

    def test_httperror_in_generator_callback(self):
        @self.app.route('/')
        def test():
            yield
            bottle.abort(404, 'teststring')
        self.assertInBody('teststring')
        self.assertInBody('404 Not Found')
        self.assertStatus(404)

    def test_httpresponse_in_generator_callback(self):
        @self.app.route('/')
        def test():
            yield bottle.HTTPResponse('test')
        self.assertBody('test')

    def test_unicode_generator_callback(self):
        @self.app.route('/')
        def test():
            yield touni('äöüß')
        self.assertBody(touni('äöüß').encode('utf8'))

    def test_invalid_generator_callback(self):
        @self.app.route('/')
        def test():
            yield 1234
        self.assertStatus(500)
        self.assertInBody('Unsupported response type')

    def test_iterator_with_close(self):
        class MyIter(object):
            def __init__(self, data):
                self.data = data
                self.closed = False
            def close(self):    self.closed = True
            def __iter__(self): return iter(self.data)

        byte_iter = MyIter([tob('abc'), tob('def')])
        unicode_iter = MyIter([touni('abc'), touni('def')])

        for test_iter in (byte_iter, unicode_iter):
            @self.app.route('/')
            def test(): return test_iter
            self.assertInBody('abcdef')
            self.assertTrue(byte_iter.closed)

    def test_cookie(self):
        """ WSGI: Cookies """
        @bottle.route('/cookie')
        def test():
            bottle.response.set_cookie('b', 'b')
            bottle.response.set_cookie('c', 'c', path='/')
            return 'hello'
        try:
            c = self.urlopen('/cookie')['header'].get_all('Set-Cookie', '')
        except:
            c = self.urlopen('/cookie')['header'].get('Set-Cookie', '').split(',')
            c = [x.strip() for x in c]
        self.assertTrue('b=b' in c)
        self.assertTrue('c=c; Path=/' in c)

if __name__ == '__main__': #pragma: no cover
    unittest.main()

########NEW FILE########
__FILENAME__ = test_plugins
# -*- coding: utf-8 -*-
import unittest
import tools


class MyPlugin(object):
    def __init__(self):
        self.app = None
        self.add_args = {}
        self.add_content = ''

    def setup(self, app):
        self.app = app

    def apply(self, func, config):
        def wrapper(*a, **ka):
            ka.update(self.add_args)
            self.lastcall = func, a, ka
            return ''.join(func(*a, **ka)) + self.add_content
        return wrapper


def my_decorator(func):
    def wrapper(*a, **ka):
        return list(func(*a, **ka))[-1]



class TestPluginManagement(tools.ServerTestBase):

    def verify_installed(self, plugin, otype, **config):
        self.assertEqual(type(plugin), otype)
        self.assertEqual(plugin.config, config)
        self.assertEqual(plugin.app, self.app)
        self.assertTrue(plugin in self.app.plugins)

    def test_install_plugin(self):
        plugin = MyPlugin()
        installed = self.app.install(plugin)
        self.assertEqual(plugin, installed)
        self.assertTrue(plugin in self.app.plugins)

    def test_install_decorator(self):
        installed = self.app.install(my_decorator)
        self.assertEqual(my_decorator, installed)
        self.assertTrue(my_decorator in self.app.plugins)

    def test_install_non_plugin(self):
        self.assertRaises(TypeError, self.app.install, 'I am not a plugin')

    def test_uninstall_by_instance(self):
        plugin  = self.app.install(MyPlugin())
        plugin2 = self.app.install(MyPlugin())
        self.app.uninstall(plugin)
        self.assertTrue(plugin not in self.app.plugins)
        self.assertTrue(plugin2 in self.app.plugins)

    def test_uninstall_by_type(self):
        plugin = self.app.install(MyPlugin())
        plugin2 = self.app.install(MyPlugin())
        self.app.uninstall(MyPlugin)
        self.assertTrue(plugin not in self.app.plugins)
        self.assertTrue(plugin2 not in self.app.plugins)

    def test_uninstall_by_name(self):
        plugin = self.app.install(MyPlugin())
        plugin2 = self.app.install(MyPlugin())
        plugin.name = 'myplugin'
        self.app.uninstall('myplugin')
        self.assertTrue(plugin not in self.app.plugins)
        self.assertTrue(plugin2 in self.app.plugins)

    def test_uninstall_all(self):
        plugin = self.app.install(MyPlugin())
        plugin2 = self.app.install(MyPlugin())
        self.app.uninstall(True)
        self.assertFalse(self.app.plugins)

    def test_route_plugin(self):
        plugin = MyPlugin()
        plugin.add_content = ';foo'
        @self.app.route('/a')
        @self.app.route('/b', apply=[plugin])
        def a(): return 'plugin'
        self.assertBody('plugin', '/a')
        self.assertBody('plugin;foo', '/b')

    def test_plugin_oder(self):
        self.app.install(MyPlugin()).add_content = ';global-1'
        self.app.install(MyPlugin()).add_content = ';global-2'
        l1 = MyPlugin()
        l1.add_content = ';local-1'
        l2 = MyPlugin()
        l2.add_content = ';local-2'
        @self.app.route('/a')
        @self.app.route('/b', apply=[l1, l2])
        def a(): return 'plugin'
        self.assertBody('plugin;global-2;global-1', '/a')
        self.assertBody('plugin;local-2;local-1;global-2;global-1', '/b')

    def test_skip_by_instance(self):
        g1 = self.app.install(MyPlugin())
        g1.add_content = ';global-1'
        g2 = self.app.install(MyPlugin())
        g2.add_content = ';global-2'
        l1 = MyPlugin()
        l1.add_content = ';local-1'
        l2 = MyPlugin()
        l2.add_content = ';local-2'
        @self.app.route('/a', skip=[g2, l2])
        @self.app.route('/b', apply=[l1, l2], skip=[g2, l2])
        def a(): return 'plugin'
        self.assertBody('plugin;global-1', '/a')
        self.assertBody('plugin;local-1;global-1', '/b')

    def test_skip_by_class(self):
        g1 = self.app.install(MyPlugin())
        g1.add_content = ';global-1'
        @self.app.route('/a')
        @self.app.route('/b', skip=[MyPlugin])
        def a(): return 'plugin'
        self.assertBody('plugin;global-1', '/a')
        self.assertBody('plugin', '/b')

    def test_skip_by_name(self):
        g1 = self.app.install(MyPlugin())
        g1.add_content = ';global-1'
        g1.name = 'test'
        @self.app.route('/a')
        @self.app.route('/b', skip=['test'])
        def a(): return 'plugin'
        self.assertBody('plugin;global-1', '/a')
        self.assertBody('plugin', '/b')

    def test_skip_all(self):
        g1 = self.app.install(MyPlugin())
        g1.add_content = ';global-1'
        @self.app.route('/a')
        @self.app.route('/b', skip=[True])
        def a(): return 'plugin'
        self.assertBody('plugin;global-1', '/a')
        self.assertBody('plugin', '/b')

    def test_skip_nonlist(self):
        g1 = self.app.install(MyPlugin())
        g1.add_content = ';global-1'
        @self.app.route('/a')
        @self.app.route('/b', skip=g1)
        def a(): return 'plugin'
        self.assertBody('plugin;global-1', '/a')
        self.assertBody('plugin', '/b')



class TestPluginAPI(tools.ServerTestBase):

    def setUp(self):
        super(TestPluginAPI, self).setUp()
        @self.app.route('/', test='plugin.cfg')
        def test(**args):
            return ', '.join('%s:%s' % (k,v) for k,v in args.items())

    def test_callable(self):
        def plugin(func):
            def wrapper(*a, **ka):
                return func(test='me', *a, **ka) + '; tail'
            return wrapper
        self.app.install(plugin)
        self.assertBody('test:me; tail', '/')


    def test_apply(self):
        class Plugin(object):
            def apply(self, func, route):
                def wrapper(*a, **ka):
                    return func(test=route.config['test'], *a, **ka) + '; tail'
                return wrapper
            def __call__(self, func):
                raise AssertionError("Plugins must not be called "\
                                     "if they implement 'apply'")
        self.app.install(Plugin())
        self.assertBody('test:plugin.cfg; tail', '/')

    def test_instance_method_wrapper(self):
        class Plugin(object):
            api=2
            def apply(self, callback, route):
                return self.b
            def b(self): return "Hello"
        self.app.install(Plugin())
        self.assertBody('Hello', '/')

    def test_setup(self):
        class Plugin(object):
            def __call__(self, func): return func
            def setup(self, app): self.app = app
        plugin = self.app.install(Plugin())
        self.assertEqual(getattr(plugin, 'app', None), self.app)

    def test_close(self):
        class Plugin(object):
            def __call__(self, func): return func
            def close(self): self.closed = True
        plugin = self.app.install(Plugin())
        plugin2 = self.app.install(Plugin())
        self.app.uninstall(plugin)
        self.assertTrue(getattr(plugin, 'closed', False))
        self.app.close()
        self.assertTrue(getattr(plugin2, 'closed', False))


if __name__ == '__main__': #pragma: no cover
    unittest.main()

########NEW FILE########
__FILENAME__ = test_resources
from bottle import ResourceManager
import os.path
import unittest

class TestResourceManager(unittest.TestCase):

    def test_path_normalize(self):
        tests = ('/foo/bar/', '/foo/bar/baz', '/foo/baz/../bar/blub')
        for test in tests:
            rm = ResourceManager()
            rm.add_path(test)
            self.assertEqual(rm.path, ['/foo/bar/'])

    def test_path_create(self):
        import tempfile, shutil
        tempdir = tempfile.mkdtemp()
        try:
            rm = ResourceManager()
            exists = rm.add_path('./test/', base=tempdir)
            self.assertEqual(exists, False)
            exists = rm.add_path('./test2/', base=tempdir, create=True)
            self.assertEqual(exists, True)
        finally:
            shutil.rmtree(tempdir)

    def test_path_absolutize(self):
        tests = ('./foo/bar/', './foo/bar/baz', './foo/baz/../bar/blub')
        abspath = os.path.abspath('./foo/bar/') + os.sep
        for test in tests:
            rm = ResourceManager()
            rm.add_path(test)
            self.assertEqual(rm.path, [abspath])

        for test in tests:
            rm = ResourceManager()
            rm.add_path(test[2:])
            self.assertEqual(rm.path, [abspath])

    def test_path_unique(self):
        tests = ('/foo/bar/', '/foo/bar/baz', '/foo/baz/../bar/blub')
        rm = ResourceManager()
        [rm.add_path(test) for test in tests]
        self.assertEqual(rm.path, ['/foo/bar/'])

    def test_root_path(self):
        tests = ('/foo/bar/', '/foo/bar/baz', '/foo/baz/../bar/blub')
        for test in tests:
            rm = ResourceManager()
            rm.add_path('./baz/', test)
            self.assertEqual(rm.path, ['/foo/bar/baz/'])

        for test in tests:
            rm = ResourceManager()
            rm.add_path('baz/', test)
            self.assertEqual(rm.path, ['/foo/bar/baz/'])

    def test_path_order(self):
        rm = ResourceManager()
        rm.add_path('/middle/')
        rm.add_path('/first/', index=0)
        rm.add_path('/last/')
        self.assertEqual(rm.path, ['/first/', '/middle/', '/last/'])

    def test_get(self):
        rm = ResourceManager()
        rm.add_path('/first/')
        rm.add_path(__file__)
        rm.add_path('/last/')
        self.assertEqual(None, rm.lookup('notexist.txt'))
        self.assertEqual(__file__, rm.lookup(os.path.basename(__file__)))

    def test_open(self):
        rm = ResourceManager()
        rm.add_path(__file__)
        fp = rm.open(__file__)
        self.assertEqual(fp.read(), open(__file__).read())


if __name__ == '__main__': #pragma: no cover
    unittest.main()

########NEW FILE########
__FILENAME__ = test_route
import unittest
import bottle
from tools import api


class TestRoute(unittest.TestCase):

    @api('0.12')
    def test_callback_inspection(self):
        def x(a, b): pass
        def d(f):
            def w():
                return f()
            return w
        
        route = bottle.Route(None, None, None, d(x))
        self.assertEqual(route.get_undecorated_callback(), x)
        self.assertEqual(set(route.get_callback_args()), set(['a', 'b']))

        def d2(foo):
            def d(f):
                def w():
                    return f()
                return w
            return d

        route = bottle.Route(None, None, None, d2('foo')(x))
        self.assertEqual(route.get_undecorated_callback(), x)
        self.assertEqual(set(route.get_callback_args()), set(['a', 'b']))


########NEW FILE########
__FILENAME__ = test_router
# -*- coding: utf-8 -*-

import unittest
import bottle


class TestRouter(unittest.TestCase):
    CGI = False
    
    def setUp(self):
        self.r = bottle.Router()
    
    def add(self, path, target, method='GET', **ka):
        self.r.add(path, method, target, **ka)

    def match(self, path, method='GET'):
        env = {'PATH_INFO': path, 'REQUEST_METHOD': method}
        if self.CGI:
            env['wsgi.run_once'] = 'true'
        return self.r.match(env)

    def assertMatches(self, rule, url, method='GET', **args):
        self.add(rule, rule, method)
        target, urlargs = self.match(url, method)
        self.assertEqual(rule, target)
        self.assertEqual(args, urlargs)

    def testBasic(self):
        self.assertMatches('/static', '/static')
        self.assertMatches('/\\:its/:#.+#/:test/:name#[a-z]+#/',
                           '/:its/a/cruel/world/',
                           test='cruel', name='world')
        self.assertMatches('/:test', '/test', test='test') # No tail
        self.assertMatches(':test/', 'test/', test='test') # No head
        self.assertMatches('/:test/', '/test/', test='test') # Middle
        self.assertMatches(':test', 'test', test='test') # Full wildcard
        self.assertMatches('/:#anon#/match', '/anon/match') # Anon wildcards
        self.assertRaises(bottle.HTTPError, self.match, '//no/m/at/ch/')

    def testNewSyntax(self):
        self.assertMatches('/static', '/static')
        self.assertMatches('/\\<its>/<:re:.+>/<test>/<name:re:[a-z]+>/',
                           '/<its>/a/cruel/world/',
                           test='cruel', name='world')
        self.assertMatches('/<test>', '/test', test='test') # No tail
        self.assertMatches('<test>/', 'test/', test='test') # No head
        self.assertMatches('/<test>/', '/test/', test='test') # Middle
        self.assertMatches('<test>', 'test', test='test') # Full wildcard
        self.assertMatches('/<:re:anon>/match', '/anon/match') # Anon wildcards
        self.assertRaises(bottle.HTTPError, self.match, '//no/m/at/ch/')

    def testUnicode(self):
        self.assertMatches('/uni/<x>', '/uni/瓶', x='瓶')

    def testValueErrorInFilter(self):
        self.r.add_filter('test', lambda x: ('.*', int, int))

        self.assertMatches('/int/<i:test>', '/int/5', i=5) # No tail
        self.assertRaises(bottle.HTTPError, self.match, '/int/noint')

    def testIntFilter(self):
        self.assertMatches('/object/<id:int>', '/object/567', id=567)
        self.assertRaises(bottle.HTTPError, self.match, '/object/abc')

    def testFloatFilter(self):
        self.assertMatches('/object/<id:float>', '/object/1', id=1)
        self.assertMatches('/object/<id:float>', '/object/1.1', id=1.1)
        self.assertMatches('/object/<id:float>', '/object/.1', id=0.1)
        self.assertMatches('/object/<id:float>', '/object/1.', id=1)
        self.assertRaises(bottle.HTTPError, self.match, '/object/abc')
        self.assertRaises(bottle.HTTPError, self.match, '/object/')
        self.assertRaises(bottle.HTTPError, self.match, '/object/.')

    def testPathFilter(self):
        self.assertMatches('/<id:path>/:f', '/a/b', id='a', f='b')
        self.assertMatches('/<id:path>', '/a', id='a')

    def testWildcardNames(self):
        self.assertMatches('/alpha/:abc', '/alpha/alpha', abc='alpha')
        self.assertMatches('/alnum/:md5', '/alnum/sha1', md5='sha1')

    def testParentheses(self):
        self.assertMatches('/func(:param)', '/func(foo)', param='foo')
        self.assertMatches('/func2(:param#(foo|bar)#)', '/func2(foo)', param='foo')
        self.assertMatches('/func2(:param#(foo|bar)#)', '/func2(bar)', param='bar')
        self.assertRaises(bottle.HTTPError, self.match, '/func2(baz)')

    def testErrorInPattern(self):
        self.assertRaises(Exception, self.assertMatches, '/:bug#(#/', '/foo/')
        self.assertRaises(Exception, self.assertMatches, '/<:re:(>/', '/foo/')

    def testBuild(self):
        add, build = self.add, self.r.build
        add('/:test/:name#[a-z]+#/', 'handler', name='testroute')

        url = build('testroute', test='hello', name='world')
        self.assertEqual('/hello/world/', url)

        url = build('testroute', test='hello', name='world', q='value')
        self.assertEqual('/hello/world/?q=value', url)

        # RouteBuildError: Missing URL argument: 'test'
        self.assertRaises(bottle.RouteBuildError, build, 'test')

    def testBuildAnon(self):
        add, build = self.add, self.r.build
        add('/anon/:#.#', 'handler', name='anonroute')

        url = build('anonroute', 'hello')
        self.assertEqual('/anon/hello', url)

        url = build('anonroute', 'hello', q='value')
        self.assertEqual('/anon/hello?q=value', url)

        # RouteBuildError: Missing URL argument: anon0.
        self.assertRaises(bottle.RouteBuildError, build, 'anonroute')

    def testBuildFilter(self):
        add, build = self.add, self.r.build
        add('/int/<:int>', 'handler', name='introute')

        url = build('introute', '5')
        self.assertEqual('/int/5', url)

        # RouteBuildError: Missing URL argument: anon0.
        self.assertRaises(ValueError, build, 'introute', 'hello')

    def test_dynamic_before_static_any(self):
        ''' Static ANY routes have lower priority than dynamic GET routes. '''
        self.add('/foo', 'foo', 'ANY')
        self.assertEqual(self.match('/foo')[0], 'foo')
        self.add('/<:>', 'bar', 'GET')
        self.assertEqual(self.match('/foo')[0], 'bar')

    def test_any_static_before_dynamic(self):
        ''' Static ANY routes have higher priority than dynamic ANY routes. '''
        self.add('/<:>', 'bar', 'ANY')
        self.assertEqual(self.match('/foo')[0], 'bar')
        self.add('/foo', 'foo', 'ANY')
        self.assertEqual(self.match('/foo')[0], 'foo')

    def test_dynamic_any_if_method_exists(self):
        ''' Check dynamic ANY routes if the matching method is known,
            but not matched.'''
        self.add('/bar<:>', 'bar', 'GET')
        self.assertEqual(self.match('/barx')[0], 'bar')
        self.add('/foo<:>', 'foo', 'ANY')
        self.assertEqual(self.match('/foox')[0], 'foo')

    def test_lots_of_routes(self):
        n = bottle.Router._MAX_GROUPS_PER_PATTERN+10
        for i in range(n):        
            self.add('/<:>/'+str(i), str(i), 'GET')
        self.assertEqual(self.match('/foo/'+str(n-1))[0], str(n-1))

class TestRouterInCGIMode(TestRouter):
    ''' Makes no sense since the default route does not optimize CGI anymore.'''
    CGI = True


if __name__ == '__main__':  # pragma: no cover
    unittest.main()

########NEW FILE########
__FILENAME__ = test_securecookies
#coding: utf-8
import unittest

import bottle
from bottle import tob, touni

class TestSecureCookies(unittest.TestCase):
    def setUp(self):
        self.data = dict(a=5, b=touni('υηι¢σ∂є'), c=[1,2,3,4,tob('bytestring')])
        self.key = tob('secret')

    def testDeEncode(self):
        cookie = bottle.cookie_encode(self.data, self.key)
        decoded = bottle.cookie_decode(cookie, self.key)
        self.assertEqual(self.data, decoded)
        decoded = bottle.cookie_decode(cookie+tob('x'), self.key)
        self.assertEqual(None, decoded)

    def testIsEncoded(self):
        cookie = bottle.cookie_encode(self.data, self.key)
        self.assertTrue(bottle.cookie_is_encoded(cookie))
        self.assertFalse(bottle.cookie_is_encoded(tob('some string')))

class TestSecureCookiesInBottle(unittest.TestCase):
    def setUp(self):
        self.data = dict(a=5, b=touni('υηι¢σ∂є'), c=[1,2,3,4,tob('bytestring')])
        self.secret = tob('secret')
        bottle.app.push()
        bottle.response.bind()

    def tear_down(self):
        bottle.app.pop()

    def get_pairs(self):
        for k, v in bottle.response.headerlist:
            if k == 'Set-Cookie':
                key, value = v.split(';')[0].split('=', 1)
                yield key.lower().strip(), value.strip()
    
    def set_pairs(self, pairs):
        header = ','.join(['%s=%s' % (k, v) for k, v in pairs])
        bottle.request.bind({'HTTP_COOKIE': header})

    def testValid(self):
        bottle.response.set_cookie('key', self.data, secret=self.secret)
        pairs = self.get_pairs()
        self.set_pairs(pairs)
        result = bottle.request.get_cookie('key', secret=self.secret)
        self.assertEqual(self.data, result)

    def testWrongKey(self):
        bottle.response.set_cookie('key', self.data, secret=self.secret)
        pairs = self.get_pairs()
        self.set_pairs([(k+'xxx', v) for (k, v) in pairs])
        result = bottle.request.get_cookie('key', secret=self.secret)
        self.assertEqual(None, result)


if __name__ == '__main__': #pragma: no cover
    unittest.main()

########NEW FILE########
__FILENAME__ = test_sendfile
import unittest
from bottle import static_file, request, response, parse_date, parse_range_header, Bottle, tob
import wsgiref.util
import os
import tempfile
import time

class TestDateParser(unittest.TestCase):
    def test_rfc1123(self):
        """DateParser: RFC 1123 format"""
        ts = time.time()
        rs = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(ts))
        self.assertEqual(int(ts), int(parse_date(rs)))

    def test_rfc850(self):
        """DateParser: RFC 850 format"""
        ts = time.time()
        rs = time.strftime("%A, %d-%b-%y %H:%M:%S GMT", time.gmtime(ts))
        self.assertEqual(int(ts), int(parse_date(rs)))

    def test_asctime(self):
        """DateParser: asctime format"""
        ts = time.time()
        rs = time.strftime("%a %b %d %H:%M:%S %Y", time.gmtime(ts))
        self.assertEqual(int(ts), int(parse_date(rs)))

    def test_bad(self):
        """DateParser: Bad format"""
        self.assertEqual(None, parse_date('Bad 123'))


class TestSendFile(unittest.TestCase):
    def setUp(self):
        e = dict()
        wsgiref.util.setup_testing_defaults(e)
        b = Bottle()
        request.bind(e)
        response.bind()

    def test_valid(self):
        """ SendFile: Valid requests"""
        out = static_file(os.path.basename(__file__), root='./')
        self.assertEqual(open(__file__,'rb').read(), out.body.read())

    def test_invalid(self):
        """ SendFile: Invalid requests"""
        self.assertEqual(404, static_file('not/a/file', root='./').status_code)
        f = static_file(os.path.join('./../', os.path.basename(__file__)), root='./views/')
        self.assertEqual(403, f.status_code)
        try:
            fp, fn = tempfile.mkstemp()
            os.chmod(fn, 0)
            self.assertEqual(403, static_file(fn, root='/').status_code)
        finally:
            os.close(fp)
            os.unlink(fn)

    def test_mime(self):
        """ SendFile: Mime Guessing"""
        f = static_file(os.path.basename(__file__), root='./')
        self.assertTrue(f.headers['Content-Type'].split(';')[0] in ('application/x-python-code', 'text/x-python'))
        f = static_file(os.path.basename(__file__), root='./', mimetype='some/type')
        self.assertEqual('some/type', f.headers['Content-Type'])
        f = static_file(os.path.basename(__file__), root='./', mimetype='text/foo')
        self.assertEqual('text/foo; charset=UTF-8', f.headers['Content-Type'])
        f = static_file(os.path.basename(__file__), root='./', mimetype='text/foo', charset='latin1')
        self.assertEqual('text/foo; charset=latin1', f.headers['Content-Type'])

    def test_ims(self):
        """ SendFile: If-Modified-Since"""
        request.environ['HTTP_IF_MODIFIED_SINCE'] = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        res = static_file(os.path.basename(__file__), root='./')
        self.assertEqual(304, res.status_code)
        self.assertEqual(int(os.stat(__file__).st_mtime), parse_date(res.headers['Last-Modified']))
        self.assertAlmostEqual(int(time.time()), parse_date(res.headers['Date']))
        request.environ['HTTP_IF_MODIFIED_SINCE'] = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(100))
        self.assertEqual(open(__file__,'rb').read(), static_file(os.path.basename(__file__), root='./').body.read())

    def test_download(self):
        """ SendFile: Download as attachment """
        basename = os.path.basename(__file__)
        f = static_file(basename, root='./', download=True)
        self.assertEqual('attachment; filename="%s"' % basename, f.headers['Content-Disposition'])
        request.environ['HTTP_IF_MODIFIED_SINCE'] = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(100))
        f = static_file(os.path.basename(__file__), root='./')
        self.assertEqual(open(__file__,'rb').read(), f.body.read())

    def test_range(self):
        basename = os.path.basename(__file__)
        request.environ['HTTP_RANGE'] = 'bytes=10-25,-80'
        f = static_file(basename, root='./')
        c = open(basename, 'rb'); c.seek(10)
        self.assertEqual(c.read(16), tob('').join(f.body))
        self.assertEqual('bytes 10-25/%d' % len(open(basename, 'rb').read()),
                         f.headers['Content-Range'])
        self.assertEqual('bytes', f.headers['Accept-Ranges'])

    def test_range_parser(self):
        r = lambda rs: list(parse_range_header(rs, 100))
        self.assertEqual([(90, 100)], r('bytes=-10'))
        self.assertEqual([(10, 100)], r('bytes=10-'))
        self.assertEqual([(5, 11)],  r('bytes=5-10'))
        self.assertEqual([(10, 100), (90, 100), (5, 11)],  r('bytes=10-,-10,5-10'))


if __name__ == '__main__': #pragma: no cover
    unittest.main()


########NEW FILE########
__FILENAME__ = test_server
# -*- coding: utf-8 -*-
import unittest
import time
from tools import tob
import sys
import os
import signal
import socket
from subprocess import Popen, PIPE
import tools
from bottle import _e

try:
    from urllib.request import urlopen
except:
    from urllib2 import urlopen

serverscript = os.path.join(os.path.dirname(__file__), 'servertest.py')

def ping(server, port):
    ''' Check if a server accepts connections on a specific TCP port '''
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((server, port))
        return True
    except socket.error:
        return False
    finally:
        s.close()


class TestServer(unittest.TestCase):
    server = 'wsgiref'
    skip   = False

    def setUp(self):
        if self.skip: return
        # Find a free port
        for port in range(8800, 8900):
            self.port = port
            # Start servertest.py in a subprocess
            cmd = [sys.executable, serverscript, self.server, str(port)]
            cmd += sys.argv[1:] # pass cmdline arguments to subprocesses
            self.p = Popen(cmd, stdout=PIPE, stderr=PIPE)
            # Wait for the socket to accept connections
            for i in range(100):
                time.sleep(0.1)
                # Accepts connections?
                if ping('127.0.0.1', port): return
                # Server died for some reason...
                if not self.p.poll() is None: break
            rv = self.p.poll()
            if rv is None:
                raise AssertionError("Server took too long to start up.")
            if rv is 128: # Import error
                tools.warn("Skipping %r test (ImportError)." % self.server)
                self.skip = True
                return
            if rv is 3: # Port in use
                continue
            raise AssertionError("Server exited with error code %d" % rv)
        raise AssertionError("Could not find a free port to test server.")

    def tearDown(self):
        if self.skip: return

        if self.p.poll() == None:
            os.kill(self.p.pid, signal.SIGINT)
            time.sleep(0.5)
        while self.p.poll() == None:
            os.kill(self.p.pid, signal.SIGTERM)
            time.sleep(1)

        for stream in (self.p.stdout, self.p.stderr):
            for line in stream:
                if tob('warning') in line.lower():
                    tools.warn(line.strip().decode('utf8'))
                elif tob('error') in line.lower():
                    raise AssertionError(line.strip().decode('utf8'))

    def fetch(self, url):
        try:
            return urlopen('http://127.0.0.1:%d/%s' % (self.port, url)).read()
        except Exception:
            return repr(_e())

    def test_simple(self):
        ''' Test a simple static page with this server adapter. '''
        if self.skip: return
        self.assertEqual(tob('OK'), self.fetch('test'))



class TestCherryPyServer(TestServer):
    server = 'cherrypy'

class TestPasteServer(TestServer):
    server = 'paste'

class TestTornadoServer(TestServer):
    server = 'tornado'

class TestTwistedServer(TestServer):
    server = 'twisted'

class TestDieselServer(TestServer):
    server = 'diesel'

class TestGunicornServer(TestServer):
    server = 'gunicorn'

class TestGeventServer(TestServer):
    server = 'gevent'

class TestEventletServer(TestServer):
    server = 'eventlet'

class TestRocketServer(TestServer):
    server = 'rocket'

class TestFapwsServer(TestServer):
    server = 'fapws3'

class MeinheldServer(TestServer):
    server = 'meinheld'

class TestBjoernServer(TestServer):
    server = 'bjoern'

if __name__ == '__main__': #pragma: no cover
    unittest.main()

########NEW FILE########
__FILENAME__ = test_stpl
# -*- coding: utf-8 -*-
import unittest
from bottle import SimpleTemplate, TemplateError, view, template, touni, tob, html_quote
import re
import traceback

class TestSimpleTemplate(unittest.TestCase):
    def assertRenders(self, tpl, to, *args, **vars):
        if isinstance(tpl, str):
            tpl = SimpleTemplate(tpl)
        self.assertEqual(touni(to), tpl.render(*args, **vars))

    def test_string(self):
        """ Templates: Parse string"""
        self.assertRenders('start {{var}} end', 'start var end', var='var')

    def test_self_as_variable_name(self):
        self.assertRenders('start {{self}} end', 'start var end', {'self':'var'})

    def test_file(self):
        t = SimpleTemplate(name='./views/stpl_simple.tpl')
        self.assertRenders(t, 'start var end\n', var='var')

    def test_name(self):
        t = SimpleTemplate(name='stpl_simple', lookup=['./views/'])
        self.assertRenders(t, 'start var end\n', var='var')

    def test_unicode(self):
        self.assertRenders('start {{var}} end', 'start äöü end', var=touni('äöü'))
        self.assertRenders('start {{var}} end', 'start äöü end', var=tob('äöü'))

    def test_unicode_code(self):
        """ Templates: utf8 code in file"""
        t = SimpleTemplate(name='./views/stpl_unicode.tpl')
        self.assertRenders(t, 'start ñç äöü end\n', var=touni('äöü'))

    def test_import(self):
        """ Templates: import statement"""
        t = '%from base64 import b64encode\nstart {{b64encode(var.encode("ascii") if hasattr(var, "encode") else var)}} end'
        self.assertRenders(t, 'start dmFy end', var='var')

    def test_data(self):
        """ Templates: Data representation """
        t = SimpleTemplate('<{{var}}>')
        self.assertRenders('<{{var}}>', '<True>', var=True)
        self.assertRenders('<{{var}}>', '<False>', var=False)
        self.assertRenders('<{{var}}>', '<>', var=None)
        self.assertRenders('<{{var}}>', '<0>', var=0)
        self.assertRenders('<{{var}}>', '<5>', var=5)
        self.assertRenders('<{{var}}>', '<b>', var=tob('b'))
        self.assertRenders('<{{var}}>', '<1.0>', var=1.0)
        self.assertRenders('<{{var}}>', '<[1, 2]>', var=[1,2])

    def test_htmlutils_quote(self):
        self.assertEqual('"&lt;&#039;&#13;&#10;&#9;&quot;\\&gt;"', html_quote('<\'\r\n\t"\\>'));

    def test_escape(self):
        self.assertRenders('<{{var}}>', '<b>', var='b')
        self.assertRenders('<{{var}}>', '<&lt;&amp;&gt;>',var='<&>')

    def test_noescape(self):
        self.assertRenders('<{{!var}}>', '<b>',   var='b')
        self.assertRenders('<{{!var}}>', '<<&>>', var='<&>')

    def test_noescape_setting(self):
        t = SimpleTemplate('<{{var}}>', noescape=True)
        self.assertRenders(t, '<b>', var='b')
        self.assertRenders(t, '<<&>>', var='<&>')
        t = SimpleTemplate('<{{!var}}>', noescape=True)
        self.assertRenders(t, '<b>', var='b')
        self.assertRenders(t, '<&lt;&amp;&gt;>', var='<&>')

    def test_blocks(self):
        """ Templates: Code blocks and loops """
        t = "start\n%for i in l:\n{{i}} \n%end\nend"
        self.assertRenders(t, 'start\n1 \n2 \n3 \nend', l=[1,2,3])
        self.assertRenders(t, 'start\nend', l=[])
        t = "start\n%if i:\n{{i}} \n%end\nend"
        self.assertRenders(t, 'start\nTrue \nend', i=True)
        self.assertRenders(t, 'start\nend', i=False)

    def test_elsebug(self):
        ''' Whirespace between block keyword and colon is allowed '''
        self.assertRenders("%if 1:\nyes\n%else:\nno\n%end\n", "yes\n")
        self.assertRenders("%if 1:\nyes\n%else     :\nno\n%end\n", "yes\n")

    def test_commentbug(self):
        ''' A "#" sign within an string is not a comment '''
        self.assertRenders("%if '#':\nyes\n%end\n", "yes\n")

    def test_multiline(self):
        ''' Block statements with non-terminating newlines '''
        self.assertRenders("%if 1\\\n%and 1:\nyes\n%end\n", "yes\n")

    def test_newline_in_parameterlist(self):
        ''' Block statements with non-terminating newlines in list '''
        self.assertRenders("%a=[1,\n%2]\n{{len(a)}}", "2")

    def test_dedentbug(self):
        ''' One-Line dednet blocks should not change indention '''
        t = '%if x: a="if"\n%else: a="else"\n%end\n{{a}}'
        self.assertRenders(t, "if", x=True)
        self.assertRenders(t, "else", x=False)
        t = '%if x:\n%a="if"\n%else: a="else"\n%end\n{{a}}'
        self.assertRenders(t, "if", x=True)
        self.assertRenders(t, "else", x=False)
        t = SimpleTemplate('%if x: a="if"\n%else: a="else"\n%end')
        self.assertRaises(NameError, t.render)

    def test_onelinebugs(self):
        ''' One-Line blocks should not change indention '''
        t = '%if x:\n%a=1\n%end\n{{a}}'
        self.assertRenders(t, "1", x=True)
        t = '%if x: a=1; end\n{{a}}'
        self.assertRenders(t, "1", x=True)
        t = '%if x:\n%a=1\n%else:\n%a=2\n%end\n{{a}}'
        self.assertRenders(t, "1", x=True)
        self.assertRenders(t, "2", x=False)
        t = '%if x:   a=1\n%else:\n%a=2\n%end\n{{a}}'
        self.assertRenders(t, "1", x=True)
        self.assertRenders(t, "2", x=False)
        t = '%if x:\n%a=1\n%else:   a=2; end\n{{a}}'
        self.assertRenders(t, "1", x=True)
        self.assertRenders(t, "2", x=False)
        t = '%if x:   a=1\n%else:   a=2; end\n{{a}}'
        self.assertRenders(t, "1", x=True)
        self.assertRenders(t, "2", x=False)

    def test_onelineblocks(self):
        """ Templates: one line code blocks """
        t = "start\n%a=''\n%for i in l: a += str(i); end\n{{a}}\nend"
        self.assertRenders(t, 'start\n123\nend', l=[1,2,3])
        self.assertRenders(t, 'start\n\nend', l=[])

    def test_escaped_codelines(self):
        self.assertRenders('\\% test', '% test')
        self.assertRenders('\\%% test', '%% test')

    def test_nobreak(self):
        """ Templates: Nobreak statements"""
        self.assertRenders("start\\\\\n%pass\nend", 'startend')

    def test_nonobreak(self):
        """ Templates: Escaped nobreak statements"""
        self.assertRenders("start\\\\\n\\\\\n%pass\nend", 'start\\\\\nend')

    def test_include(self):
        """ Templates: Include statements"""
        t = SimpleTemplate(name='stpl_include', lookup=['./views/'])
        self.assertRenders(t, 'before\nstart var end\nafter\n', var='var')

    def test_rebase(self):
        """ Templates: %rebase and method passing """
        t = SimpleTemplate(name='stpl_t2main', lookup=['./views/'])
        result='+base+\n+main+\n!1234!\n+include+\n-main-\n+include+\n-base-\n'
        self.assertRenders(t, result, content='1234')

    def test_get(self):
        self.assertRenders('{{get("x", "default")}}', '1234', x='1234')
        self.assertRenders('{{get("x", "default")}}', 'default')

    def test_setdefault(self):
        t = '%setdefault("x", "default")\n{{x}}'
        self.assertRenders(t, '1234', x='1234')
        self.assertRenders(t, 'default')

    def test_defnied(self):
        self.assertRenders('{{x if defined("x") else "no"}}', 'yes', x='yes')
        self.assertRenders('{{x if defined("x") else "no"}}', 'no')

    def test_notfound(self):
        """ Templates: Unavailable templates"""
        self.assertRaises(TemplateError, SimpleTemplate, name="abcdef")

    def test_error(self):
        """ Templates: Exceptions"""
        self.assertRaises(SyntaxError, lambda: SimpleTemplate('%for badsyntax').co)
        self.assertRaises(IndexError, SimpleTemplate('{{i[5]}}').render, i=[0])

    def test_winbreaks(self):
        """ Templates: Test windows line breaks """
        self.assertRenders('%var+=1\r\n{{var}}\r\n', '6\r\n', var=5)

    def test_winbreaks_end_bug(self):
        d = { 'test': [ 1, 2, 3 ] }
        self.assertRenders('%for i in test:\n{{i}}\n%end\n', '1\n2\n3\n', **d)
        self.assertRenders('%for i in test:\n{{i}}\r\n%end\n', '1\r\n2\r\n3\r\n', **d)
        self.assertRenders('%for i in test:\r\n{{i}}\n%end\r\n', '1\n2\n3\n', **d)
        self.assertRenders('%for i in test:\r\n{{i}}\r\n%end\r\n', '1\r\n2\r\n3\r\n', **d)

    def test_commentonly(self):
        """ Templates: Commentd should behave like code-lines (e.g. flush text-lines) """
        t = SimpleTemplate('...\n%#test\n...')
        self.assertNotEqual('#test', t.code.splitlines()[0])

    def test_template_shortcut(self):
        result = template('start {{var}} end', var='middle')
        self.assertEqual(touni('start middle end'), result)

    def test_view_decorator(self):
        @view('start {{var}} end')
        def test():
            return dict(var='middle')
        self.assertEqual(touni('start middle end'), test())

    def test_view_decorator_issue_407(self):
        @view('stpl_no_vars')
        def test():
            pass
        self.assertEqual(touni('hihi'), test())
        @view('aaa {{x}}', x='bbb')
        def test2():
            pass
        self.assertEqual(touni('aaa bbb'), test2())

    def test_global_config(self):
        SimpleTemplate.global_config('meh', 1)
        t = SimpleTemplate('anything')
        self.assertEqual(touni('anything'), t.render())

    def test_bug_no_whitespace_before_stmt(self):
        self.assertRenders('\n{{var}}', '\nx', var='x')

    def test_bug_block_keywords_eat_prefixed_code(self):
        ''' #595: Everything before an 'if' statement is removed, resulting in
            SyntaxError. '''
        tpl = "% m = 'x' if True else 'y'\n{{m}}"
        self.assertRenders(tpl, 'x')


class TestSTPLDir(unittest.TestCase):
    def fix_ident(self, string):
        lines = string.splitlines(True)
        if not lines: return string
        if not lines[0].strip(): lines.pop(0)
        whitespace = re.match('([ \t]*)', lines[0]).group(0)
        if not whitespace: return string
        for i in range(len(lines)):
            lines[i] = lines[i][len(whitespace):]
        return lines[0][:0].join(lines)

    def assertRenders(self, source, result, syntax=None, *args, **vars):
        source = self.fix_ident(source)
        result = self.fix_ident(result)
        tpl = SimpleTemplate(source, syntax=syntax)
        try:
            tpl.co
            self.assertEqual(touni(result), tpl.render(*args, **vars))
        except SyntaxError:
            self.fail('Syntax error in template:\n%s\n\nTemplate code:\n##########\n%s\n##########' %
                     (traceback.format_exc(), tpl.code))

    def test_multiline_block(self):
        source = '''
            <% a = 5
            b = 6
            c = 7 %>
            {{a+b+c}}
        '''; result = '''
            18
        '''
        self.assertRenders(source, result)

    def test_multiline_ignore_eob_in_string(self):
        source = '''
            <% x=5 # a comment
               y = '%>' # a string
               # this is still code
               # lets end this %>
            {{x}}{{!y}}
        '''; result = '''
            5%>
        '''
        self.assertRenders(source, result)

    def test_multiline_find_eob_in_comments(self):
        source = '''
            <% # a comment
               # %> ignore because not end of line
               # this is still code
               x=5
               # lets end this here %>
            {{x}}
        '''; result = '''
            5
        '''
        self.assertRenders(source, result)

    def test_multiline_indention(self):
        source = '''
            <%   if True:
                   a = 2
                     else:
                       a = 0
                         end
            %>
            {{a}}
        '''; result = '''
            2
        '''
        self.assertRenders(source, result)

    def test_multiline_eob_after_end(self):
        source = '''
            <%   if True:
                   a = 2
                 end %>
            {{a}}
        '''; result = '''
            2
        '''
        self.assertRenders(source, result)

    def test_multiline_eob_in_single_line_code(self):
        # eob must be a valid python expression to allow this test.
        source = '''
            cline eob=5; eob
            xxx
        '''; result = '''
            xxx
        '''
        self.assertRenders(source, result, syntax='sob eob cline foo bar')

    def test_multiline_strings_in_code_line(self):
        source = '''
            % a = """line 1
                  line 2"""
            {{a}}
        '''; result = '''
            line 1
                  line 2
        '''
        self.assertRenders(source, result)

if __name__ == '__main__': #pragma: no cover
    unittest.main()


########NEW FILE########
__FILENAME__ = test_wsgi
# -*- coding: utf-8 -*-
from __future__ import with_statement
import unittest
import bottle
from tools import ServerTestBase
from bottle import tob

class TestWsgi(ServerTestBase):
    ''' Tests for WSGI functionality, routing and output casting (decorators) '''

    def test_get(self):
        """ WSGI: GET routes"""
        @bottle.route('/')
        def test(): return 'test'
        self.assertStatus(404, '/not/found')
        self.assertStatus(405, '/', post="var=value")
        self.assertBody('test', '/')

    def test_post(self):
        """ WSGI: POST routes"""
        @bottle.route('/', method='POST')
        def test(): return 'test'
        self.assertStatus(404, '/not/found')
        self.assertStatus(405, '/')
        self.assertBody('test', '/', post="var=value")

    def test_headget(self):
        """ WSGI: HEAD routes and GET fallback"""
        @bottle.route('/get')
        def test(): return 'test'
        @bottle.route('/head', method='HEAD')
        def test2(): return 'test'
        # GET -> HEAD
        self.assertStatus(405, '/head')
        # HEAD -> HEAD
        self.assertStatus(200, '/head', method='HEAD')
        self.assertBody('', '/head', method='HEAD')
        # HEAD -> GET
        self.assertStatus(200, '/get', method='HEAD')
        self.assertBody('', '/get', method='HEAD')

    def test_request_attrs(self):
        """ WSGI: POST routes"""
        @bottle.route('/')
        def test():
            self.assertEqual(bottle.request.app,
                             bottle.default_app())
            self.assertEqual(bottle.request.route,
                             bottle.default_app().routes[0])
            return 'foo'
        self.assertBody('foo', '/')

    def get304(self):
        """ 304 responses must not return entity headers """
        bad = ('allow', 'content-encoding', 'content-language',
               'content-length', 'content-md5', 'content-range',
               'content-type', 'last-modified') # + c-location, expires?
        for h in bad:
            bottle.response.set_header(h, 'foo')
        bottle.status = 304
        for h, v in bottle.response.headerlist:
            self.assertFalse(h.lower() in bad, "Header %s not deleted" % h)

    def test_anymethod(self):
        self.assertStatus(404, '/any')
        @bottle.route('/any', method='ANY')
        def test2(): return 'test'
        self.assertStatus(200, '/any', method='HEAD')
        self.assertBody('test', '/any', method='GET')
        self.assertBody('test', '/any', method='POST')
        self.assertBody('test', '/any', method='DELETE')
        @bottle.route('/any', method='GET')
        def test2(): return 'test2'
        self.assertBody('test2', '/any', method='GET')
        @bottle.route('/any', method='POST')
        def test2(): return 'test3'
        self.assertBody('test3', '/any', method='POST')
        self.assertBody('test', '/any', method='DELETE')

    def test_500(self):
        """ WSGI: Exceptions within handler code (HTTP 500) """
        @bottle.route('/')
        def test(): return 1/0
        self.assertStatus(500, '/')

    def test_500_unicode(self):
        @bottle.route('/')
        def test(): raise Exception(touni('Unicode äöüß message.'))
        self.assertStatus(500, '/')

    def test_utf8_url(self):
        """ WSGI: UTF-8 Characters in the URL """
        @bottle.route('/my-öäü/:string')
        def test(string): return string
        self.assertBody(tob('urf8-öäü'), '/my-öäü/urf8-öäü')

    def test_utf8_404(self):
        self.assertStatus(404, '/not-found/urf8-öäü')

    def test_401(self):
        """ WSGI: abort(401, '') (HTTP 401) """
        @bottle.route('/')
        def test(): bottle.abort(401)
        self.assertStatus(401, '/')
        @bottle.error(401)
        def err(e):
            bottle.response.status = 200
            return str(type(e))
        self.assertStatus(200, '/')
        self.assertBody("<class 'bottle.HTTPError'>",'/')

    def test_303(self):
        """ WSGI: redirect (HTTP 303) """
        @bottle.route('/')
        def test(): bottle.redirect('/yes')
        @bottle.route('/one')
        def test2(): bottle.redirect('/yes',305)
        env = {'SERVER_PROTOCOL':'HTTP/1.1'}
        self.assertStatus(303, '/', env=env)
        self.assertHeader('Location', 'http://127.0.0.1/yes', '/', env=env)
        env = {'SERVER_PROTOCOL':'HTTP/1.0'}
        self.assertStatus(302, '/', env=env)
        self.assertHeader('Location', 'http://127.0.0.1/yes', '/', env=env)
        self.assertStatus(305, '/one', env=env)
        self.assertHeader('Location', 'http://127.0.0.1/yes', '/one', env=env)

    def test_generator_callback(self):
        @bottle.route('/yield')
        def test():
            bottle.response.headers['Test-Header'] = 'test'
            yield 'foo'
        @bottle.route('/yield_nothing')
        def test2():
            yield
            bottle.response.headers['Test-Header'] = 'test'
        self.assertBody('foo', '/yield')
        self.assertHeader('Test-Header', 'test', '/yield')
        self.assertBody('', '/yield_nothing')
        self.assertHeader('Test-Header', 'test', '/yield_nothing')

    def test_cookie(self):
        """ WSGI: Cookies """
        @bottle.route('/cookie')
        def test():
            bottle.response.set_cookie('b', 'b')
            bottle.response.set_cookie('c', 'c', path='/')
            return 'hello'
        try:
            c = self.urlopen('/cookie')['header'].get_all('Set-Cookie', '')
        except:
            c = self.urlopen('/cookie')['header'].get('Set-Cookie', '').split(',')
            c = [x.strip() for x in c]
        self.assertTrue('b=b' in c)
        self.assertTrue('c=c; Path=/' in c)


class TestRouteDecorator(ServerTestBase):
    def test_decorators(self):
        def foo(): return bottle.request.method
        bottle.get('/')(foo)
        bottle.post('/')(foo)
        bottle.put('/')(foo)
        bottle.delete('/')(foo)
        for verb in 'GET POST PUT DELETE'.split():
            self.assertBody(verb, '/', method=verb)

    def test_single_path(self):
        @bottle.route('/a')
        def test(): return 'ok'
        self.assertBody('ok', '/a')
        self.assertStatus(404, '/b')

    def test_path_list(self):
        @bottle.route(['/a','/b'])
        def test(): return 'ok'
        self.assertBody('ok', '/a')
        self.assertBody('ok', '/b')
        self.assertStatus(404, '/c')

    def test_no_path(self):
        @bottle.route()
        def test(x=5): return str(x)
        self.assertBody('5', '/test')
        self.assertBody('6', '/test/6')

    def test_no_params_at_all(self):
        @bottle.route
        def test(x=5): return str(x)
        self.assertBody('5', '/test')
        self.assertBody('6', '/test/6')

    def test_method(self):
        @bottle.route(method='gEt')
        def test(): return 'ok'
        self.assertBody('ok', '/test', method='GET')
        self.assertStatus(200, '/test', method='HEAD')
        self.assertStatus(405, '/test', method='PUT')

    def test_method_list(self):
        @bottle.route(method=['GET','post'])
        def test(): return 'ok'
        self.assertBody('ok', '/test', method='GET')
        self.assertBody('ok', '/test', method='POST')
        self.assertStatus(405, '/test', method='PUT')

    def test_apply(self):
        def revdec(func):
            def wrapper(*a, **ka):
                return reversed(func(*a, **ka))
            return wrapper

        @bottle.route('/nodec')
        @bottle.route('/dec', apply=revdec)
        def test(): return '1', '2'
        self.assertBody('21', '/dec')
        self.assertBody('12', '/nodec')

    def test_apply_list(self):
        def revdec(func):
            def wrapper(*a, **ka):
                return reversed(func(*a, **ka))
            return wrapper
        def titledec(func):
            def wrapper(*a, **ka):
                return ''.join(func(*a, **ka)).title()
            return wrapper

        @bottle.route('/revtitle', apply=[revdec, titledec])
        @bottle.route('/titlerev', apply=[titledec, revdec])
        def test(): return 'a', 'b', 'c'
        self.assertBody('cbA', '/revtitle')
        self.assertBody('Cba', '/titlerev')

    def test_hooks(self):
        @bottle.route()
        def test():
            return bottle.request.environ.get('hooktest','nohooks')
        @bottle.hook('before_request')
        def hook():
            bottle.request.environ['hooktest'] = 'before'
        @bottle.hook('after_request')
        def hook():
            bottle.response.headers['X-Hook'] = 'after'
        self.assertBody('before', '/test')
        self.assertHeader('X-Hook', 'after', '/test')

    def test_template(self):
        @bottle.route(template='test {{a}} {{b}}')
        def test(): return dict(a=5, b=6)
        self.assertBody('test 5 6', '/test')

    def test_template_opts(self):
        @bottle.route(template=('test {{a}} {{b}}', {'b': 6}))
        def test(): return dict(a=5)
        self.assertBody('test 5 6', '/test')

    def test_name(self):
        @bottle.route(name='foo')
        def test(x=5): return 'ok'
        self.assertEqual('/test/6', bottle.url('foo', x=6))

    def test_callback(self):
        def test(x=5): return str(x)
        rv = bottle.route(callback=test)
        self.assertBody('5', '/test')
        self.assertBody('6', '/test/6')
        self.assertEqual(rv, test)




class TestDecorators(ServerTestBase):
    ''' Tests Decorators '''

    def test_view(self):
        """ WSGI: Test view-decorator (should override autojson) """
        @bottle.route('/tpl')
        @bottle.view('stpl_t2main')
        def test():
            return dict(content='1234')
        result = '+base+\n+main+\n!1234!\n+include+\n-main-\n+include+\n-base-\n'
        self.assertHeader('Content-Type', 'text/html; charset=UTF-8', '/tpl')
        self.assertBody(result, '/tpl')

    def test_view_error(self):
        """ WSGI: Test if view-decorator reacts on non-dict return values correctly."""
        @bottle.route('/tpl')
        @bottle.view('stpl_t2main')
        def test():
            return bottle.HTTPError(401, 'The cake is a lie!')
        self.assertInBody('The cake is a lie!', '/tpl')
        self.assertInBody('401 Unauthorized', '/tpl')
        self.assertStatus(401, '/tpl')

    def test_truncate_body(self):
        """ WSGI: Some HTTP status codes must not be used with a response-body """
        @bottle.route('/test/:code')
        def test(code):
            bottle.response.status = int(code)
            return 'Some body content'
        self.assertBody('Some body content', '/test/200')
        self.assertBody('', '/test/100')
        self.assertBody('', '/test/101')
        self.assertBody('', '/test/204')
        self.assertBody('', '/test/304')

    def test_routebuild(self):
        """ WSGI: Test route builder """
        def foo(): pass
        bottle.route('/a/:b/c', name='named')(foo)
        bottle.request.environ['SCRIPT_NAME'] = ''
        self.assertEqual('/a/xxx/c', bottle.url('named', b='xxx'))
        self.assertEqual('/a/xxx/c', bottle.app().get_url('named', b='xxx'))
        bottle.request.environ['SCRIPT_NAME'] = '/app'
        self.assertEqual('/app/a/xxx/c', bottle.url('named', b='xxx'))
        bottle.request.environ['SCRIPT_NAME'] = '/app/'
        self.assertEqual('/app/a/xxx/c', bottle.url('named', b='xxx'))
        bottle.request.environ['SCRIPT_NAME'] = 'app/'
        self.assertEqual('/app/a/xxx/c', bottle.url('named', b='xxx'))

    def test_autoroute(self):
        app = bottle.Bottle()
        def a(): pass
        def b(x): pass
        def c(x, y): pass
        def d(x, y=5): pass
        def e(x=5, y=6): pass
        self.assertEqual(['/a'],list(bottle.yieldroutes(a)))
        self.assertEqual(['/b/<x>'],list(bottle.yieldroutes(b)))
        self.assertEqual(['/c/<x>/<y>'],list(bottle.yieldroutes(c)))
        self.assertEqual(['/d/<x>','/d/<x>/<y>'],list(bottle.yieldroutes(d)))
        self.assertEqual(['/e','/e/<x>','/e/<x>/<y>'],list(bottle.yieldroutes(e)))



class TestAppShortcuts(ServerTestBase):
    def setUp(self):
        ServerTestBase.setUp(self)
        
    def testWithStatement(self):
        default = bottle.default_app()
        inner_app = bottle.Bottle()
        self.assertEqual(default, bottle.default_app())
        with inner_app:
            self.assertEqual(inner_app, bottle.default_app())
        self.assertEqual(default, bottle.default_app())

    def assertWraps(self, test, other):
        self.assertEqual(test.__doc__, other.__doc__)

    def test_module_shortcuts(self):
        for name in '''route get post put delete error mount
                       hook install uninstall'''.split():
            short = getattr(bottle, name)
            original = getattr(bottle.app(), name)
            self.assertWraps(short, original)

    def test_module_shortcuts_with_different_name(self):
        self.assertWraps(bottle.url, bottle.app().get_url)





if __name__ == '__main__': #pragma: no cover
    unittest.main()

########NEW FILE########
__FILENAME__ = tools
# -*- coding: utf-8 -*-
import bottle
import sys
import unittest
import wsgiref
import wsgiref.util
import wsgiref.validate

import mimetypes
import uuid

from bottle import tob, tonat, BytesIO, py3k, unicode

def warn(msg):
    sys.stderr.write('WARNING: %s\n' % msg.strip())

def tobs(data):
    ''' Transforms bytes or unicode into a byte stream. '''
    return BytesIO(tob(data))

def api(introduced, deprecated=None, removed=None):
    current    = tuple(map(int, bottle.__version__.split('-')[0].split('.')))
    introduced = tuple(map(int, introduced.split('.')))
    deprecated = tuple(map(int, deprecated.split('.'))) if deprecated else (99,99)
    removed    = tuple(map(int, removed.split('.')))    if removed    else (99,100)
    assert introduced < deprecated < removed

    def decorator(func):
        if   current < introduced:
            return None
        elif current < deprecated:
            return func
        elif current < removed:
            func.__doc__ = '(deprecated) ' + (func.__doc__ or '')
            return func
        else:
            return None
    return decorator


def wsgistr(s):
    if py3k:
        return s.encode('utf8').decode('latin1')
    else:
        return s

class ServerTestBase(unittest.TestCase):
    def setUp(self):
        ''' Create a new Bottle app set it as default_app '''
        self.port = 8080
        self.host = 'localhost'
        self.app = bottle.app.push()
        self.wsgiapp = wsgiref.validate.validator(self.app)

    def urlopen(self, path, method='GET', post='', env=None):
        result = {'code':0, 'status':'error', 'header':{}, 'body':tob('')}
        def start_response(status, header):
            result['code'] = int(status.split()[0])
            result['status'] = status.split(None, 1)[-1]
            for name, value in header:
                name = name.title()
                if name in result['header']:
                    result['header'][name] += ', ' + value
                else:
                    result['header'][name] = value
        env = env if env else {}
        wsgiref.util.setup_testing_defaults(env)
        env['REQUEST_METHOD'] = wsgistr(method.upper().strip())
        env['PATH_INFO'] = wsgistr(path)
        env['QUERY_STRING'] = wsgistr('')
        if post:
            env['REQUEST_METHOD'] = 'POST'
            env['CONTENT_LENGTH'] = str(len(tob(post)))
            env['wsgi.input'].write(tob(post))
            env['wsgi.input'].seek(0)
        response = self.wsgiapp(env, start_response)
        for part in response:
            try:
                result['body'] += part
            except TypeError:
                raise TypeError('WSGI app yielded non-byte object %s', type(part))
        if hasattr(response, 'close'):
            response.close()
            del response
        return result

    def postmultipart(self, path, fields, files):
        env = multipart_environ(fields, files)
        return self.urlopen(path, method='POST', env=env)

    def tearDown(self):
        bottle.app.pop()

    def assertStatus(self, code, route='/', **kargs):
        self.assertEqual(code, self.urlopen(route, **kargs)['code'])

    def assertBody(self, body, route='/', **kargs):
        self.assertEqual(tob(body), self.urlopen(route, **kargs)['body'])

    def assertInBody(self, body, route='/', **kargs):
        result = self.urlopen(route, **kargs)['body']
        if tob(body) not in result:
            self.fail('The search pattern "%s" is not included in body:\n%s' % (body, result))

    def assertHeader(self, name, value, route='/', **kargs):
        self.assertEqual(value, self.urlopen(route, **kargs)['header'].get(name))

    def assertHeaderAny(self, name, route='/', **kargs):
        self.assertTrue(self.urlopen(route, **kargs)['header'].get(name, None))

    def assertInError(self, search, route='/', **kargs):
        bottle.request.environ['wsgi.errors'].errors.seek(0)
        err = bottle.request.environ['wsgi.errors'].errors.read()
        if search not in err:
            self.fail('The search pattern "%s" is not included in wsgi.error: %s' % (search, err))

def multipart_environ(fields, files):
    boundary = str(uuid.uuid1())
    env = {'REQUEST_METHOD':'POST',
           'CONTENT_TYPE':  'multipart/form-data; boundary='+boundary}
    wsgiref.util.setup_testing_defaults(env)
    boundary = '--' + boundary
    body = ''
    for name, value in fields:
        body += boundary + '\n'
        body += 'Content-Disposition: form-data; name="%s"\n\n' % name
        body += value + '\n'
    for name, filename, content in files:
        mimetype = str(mimetypes.guess_type(filename)[0]) or 'application/octet-stream'
        body += boundary + '\n'
        body += 'Content-Disposition: file; name="%s"; filename="%s"\n' % \
             (name, filename)
        body += 'Content-Type: %s\n\n' % mimetype
        body += content + '\n'
    body += boundary + '--\n'
    if isinstance(body, unicode):
        body = body.encode('utf8')
    env['CONTENT_LENGTH'] = str(len(body))
    env['wsgi.input'].write(body)
    env['wsgi.input'].seek(0)
    return env

########NEW FILE########
