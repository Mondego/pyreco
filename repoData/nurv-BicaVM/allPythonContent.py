__FILENAME__ = app
#! /usr/bin/python

# -*- Mode: Python -*-
# -*- coding: UTF-8 -*-
# Copyright (C) 2009 by Artur Ventura
#
# File: app.py
# Time-stamp: Sun Aug  9 16:30:18 2009
#
# Author: Artur Ventura
#


import web
import commands

urls = (
    '/(.*)', 'index',
    
)
app = web.application(urls, globals())

class index:
    def GET(self,filename):
        if filename.endswith("favicon.ico"):
            web.webapi.notfound()
            return ""
        if filename == "jvm.js":
            web.header('Content-Type', 'text/javascript')
            return commands.getstatusoutput("cat ../src/*.js | cpp -DDEBUG -DDEBUG_INTRP -I../src/ -P -undef -CC -Wundef -std=c99 -nostdinc -Wtrigraphs -fdollars-in-identifiers")[1]
        if "testRuntime" in filename:
            alphex = filename[filename.rfind("/") + 1:];
            return file("../runtime/" + alphex.replace(".","/") + ".class").read();
        if filename == "":
            return file("index.html").read()
        try:
            return file(filename).read()
        except:
            web.webapi.notfound()
            return ""
                
        

if __name__ == "__main__":
    app.run()

########NEW FILE########
__FILENAME__ = application
#!/usr/bin/python
"""
Web application
(from web.py)
"""
import webapi as web
import webapi, wsgi, utils
import debugerror
from utils import lstrips, safeunicode
import sys

import urllib
import traceback
import itertools
import os
import re
import types

try:
    import wsgiref.handlers
except ImportError:
    pass # don't break people with old Pythons

__all__ = [
    "application", "auto_application",
    "subdir_application", "subdomain_application", 
    "loadhook", "unloadhook",
    "autodelegate"
]

class application:
    """
    Application to delegate requests based on path.
    
        >>> urls = ("/hello", "hello")
        >>> app = application(urls, globals())
        >>> class hello:
        ...     def GET(self): return "hello"
        >>>
        >>> app.request("/hello").data
        'hello'
    """
    def __init__(self, mapping=(), fvars={}, autoreload=None):
        if autoreload is None:
            autoreload = web.config.get('debug', False)
        self.mapping = mapping
        self.fvars = fvars
        self.processors = []

        if autoreload:
            def main_module_name():
                mod = sys.modules['__main__']
                file = getattr(mod, '__file__', None) # make sure this works even from python interpreter
                return file and os.path.splitext(os.path.basename(file))[0]

            def modname(fvars):
                """find name of the module name from fvars."""
                file, name = fvars.get('__file__'), fvars.get('__name__')
                if file is None or name is None:
                    return None

                if name == '__main__':
                    # Since the __main__ module can't be reloaded, the module has 
                    # to be imported using its file name.                    
                    name = main_module_name()
                return name
                
            mapping_name = utils.dictfind(fvars, mapping)
            module_name = modname(fvars)
            
            def reload_mapping():
                """loadhook to reload mapping and fvars."""
                mod = __import__(module_name)
                mapping = getattr(mod, mapping_name, None)
                if mapping:
                    self.fvars = mod.__dict__
                    self.mapping = mapping

            self.add_processor(loadhook(Reloader()))
            if mapping_name and module_name:
                self.add_processor(loadhook(reload_mapping))

            # load __main__ module usings its filename, so that it can be reloaded.
            if main_module_name() and '__main__' in sys.argv:
                try:
                    __import__(main_module_name())
                except ImportError:
                    pass

    def add_mapping(self, pattern, classname):
        self.mapping += (pattern, classname)
        
    def add_processor(self, processor):
        """
        Adds a processor to the application. 
        
            >>> urls = ("/(.*)", "echo")
            >>> app = application(urls, globals())
            >>> class echo:
            ...     def GET(self, name): return name
            ...
            >>>
            >>> def hello(handler): return "hello, " +  handler()
            >>> app.add_processor(hello)
            >>> app.request("/web.py").data
            'hello, web.py'
        """
        self.processors.append(processor)

    def request(self, localpart='/', method='GET', data=None,
                host="0.0.0.0:8080", headers=None, https=False, **kw):
        """Makes request to this application for the specified path and method.
        Response will be a storage object with data, status and headers.

            >>> urls = ("/hello", "hello")
            >>> app = application(urls, globals())
            >>> class hello:
            ...     def GET(self): 
            ...         web.header('Content-Type', 'text/plain')
            ...         return "hello"
            ...
            >>> response = app.request("/hello")
            >>> response.data
            'hello'
            >>> response.status
            '200 OK'
            >>> response.headers['Content-Type']
            'text/plain'

        To use https, use https=True.

            >>> urls = ("/redirect", "redirect")
            >>> app = application(urls, globals())
            >>> class redirect:
            ...     def GET(self): raise web.seeother("/foo")
            ...
            >>> response = app.request("/redirect")
            >>> response.headers['Location']
            'http://0.0.0.0:8080/foo'
            >>> response = app.request("/redirect", https=True)
            >>> response.headers['Location']
            'https://0.0.0.0:8080/foo'

        The headers argument specifies HTTP headers as a mapping object
        such as a dict.

            >>> urls = ('/ua', 'uaprinter')
            >>> class uaprinter:
            ...     def GET(self):
            ...         return 'your user-agent is ' + web.ctx.env['HTTP_USER_AGENT']
            ... 
            >>> app = application(urls, globals())
            >>> app.request('/ua', headers = {
            ...      'User-Agent': 'a small jumping bean/1.0 (compatible)'
            ... }).data
            'your user-agent is a small jumping bean/1.0 (compatible)'

        """
        path, maybe_query = urllib.splitquery(localpart)
        query = maybe_query or ""
        
        if 'env' in kw:
            env = kw['env']
        else:
            env = {}
        env = dict(env, HTTP_HOST=host, REQUEST_METHOD=method, PATH_INFO=path, QUERY_STRING=query, HTTPS=str(https))
        headers = headers or {}

        for k, v in headers.items():
            env['HTTP_' + k.upper().replace('-', '_')] = v

        if 'HTTP_CONTENT_LENGTH' in env:
            env['CONTENT_LENGTH'] = env.pop('HTTP_CONTENT_LENGTH')

        if 'HTTP_CONTENT_TYPE' in env:
            env['CONTENT_TYPE'] = env.pop('HTTP_CONTENT_TYPE')

        if data:
            import StringIO
            if isinstance(data, dict):
                q = urllib.urlencode(data)
            else:
                q = data
            env['wsgi.input'] = StringIO.StringIO(q)
            if not env.get('CONTENT_TYPE', '').lower().startswith('multipart/') and 'CONTENT_LENGTH' not in env:
                env['CONTENT_LENGTH'] = len(q)
        response = web.storage()
        def start_response(status, headers):
            response.status = status
            response.headers = dict(headers)
            response.header_items = headers
        response.data = "".join(self.wsgifunc(cleanup_threadlocal=False)(env, start_response))
        return response

    def browser(self):
        import browser
        return browser.AppBrowser(self)

    def handle(self):
        fn, args = self._match(self.mapping, web.ctx.path)
        return self._delegate(fn, self.fvars, args)
        
    def handle_with_processors(self):
        def process(processors):
            try:
                web.ctx.app_stack.append(self)
                if processors:
                    p, processors = processors[0], processors[1:]
                    return p(lambda: process(processors))
                else:
                    return self.handle()
            except web.HTTPError:
                raise
            except:
                print >> web.debug, traceback.format_exc()
                raise self.internalerror()
                    
        try:
            # processors must be applied in the resvere order. (??)
            return process(self.processors)
        finally:
            web.ctx.app_stack = web.ctx.app_stack[:-1]
                        
    def wsgifunc(self, *middleware, **kw):
        """Returns a WSGI-compatible function for this application."""
        def peep(iterator):
            """Peeps into an iterator by doing an iteration
            and returns an equivalent iterator.
            """
            # wsgi requires the headers first
            # so we need to do an iteration
            # and save the result for later
            try:
                firstchunk = iterator.next()
            except StopIteration:
                firstchunk = ''
            
            return itertools.chain([firstchunk], iterator)    
                                
        def is_generator(x): return x and hasattr(x, 'next')
        
        def wsgi(env, start_resp):
            self.load(env)

            try:
                # allow uppercase methods only
                if web.ctx.method.upper() != web.ctx.method:
                    raise web.nomethod()

                result = self.handle_with_processors()
            except web.HTTPError, e:
                result = e.data

            if is_generator(result):
                result = peep(result)
            else:
                result = [utils.utf8(result)]

            status, headers = web.ctx.status, web.ctx.headers
            start_resp(status, headers)

            #@@@
            # Since the CherryPy Webserver uses thread pool, the thread-local state is never cleared.
            # This interferes with the other requests. 
            # clearing the thread-local storage to avoid that.
            # see utils.ThreadedDict for details
            import threading
            t = threading.currentThread()
            if kw.get('cleanup_threadlocal', True) and hasattr(t, '_d'):
                del t._d
        
            return result

        for m in middleware: 
            wsgi = m(wsgi)

        return wsgi

    def run(self, *middleware):
        """
        Starts handling requests. If called in a CGI or FastCGI context, it will follow
        that protocol. If called from the command line, it will start an HTTP
        server on the port named in the first command line argument, or, if there
        is no argument, on port 8080.
        
        `middleware` is a list of WSGI middleware which is applied to the resulting WSGI
        function.
        """
        return wsgi.runwsgi(self.wsgifunc(*middleware))
    
    def cgirun(self, *middleware):
        """
        Return a CGI handler. This is mostly useful with Google App Engine.
        There you can just do:
        
            main = app.cgirun()
        """
        wsgiapp = self.wsgifunc(*middleware)

        try:
            from google.appengine.ext.webapp.util import run_wsgi_app
            return run_wsgi_app(wsgiapp)
        except ImportError:
            # we're not running from within Google App Engine
            return wsgiref.handlers.CGIHandler().run(wsgiapp)
    
    def load(self, env):
        """Initializes ctx using env."""
        ctx = web.ctx
        ctx.clear()
        ctx.status = '200 OK'
        ctx.headers = []
        ctx.output = ''
        ctx.environ = ctx.env = env
        ctx.host = env.get('HTTP_HOST')

        if env.get('wsgi.url_scheme') in ['http', 'https']:
            ctx.protocol = env['wsgi.url_scheme']
        elif env.get('HTTPS', '').lower() in ['on', 'true', '1']:
            ctx.protocol = 'https'
        else:
            ctx.protocol = 'http'
        ctx.homedomain = ctx.protocol + '://' + env.get('HTTP_HOST', '[unknown]')
        ctx.homepath = os.environ.get('REAL_SCRIPT_NAME', env.get('SCRIPT_NAME', ''))
        ctx.home = ctx.homedomain + ctx.homepath
        #@@ home is changed when the request is handled to a sub-application.
        #@@ but the real home is required for doing absolute redirects.
        ctx.realhome = ctx.home
        ctx.ip = env.get('REMOTE_ADDR')
        ctx.method = env.get('REQUEST_METHOD')
        ctx.path = env.get('PATH_INFO')
        # http://trac.lighttpd.net/trac/ticket/406 requires:
        if env.get('SERVER_SOFTWARE', '').startswith('lighttpd/'):
            ctx.path = lstrips(env.get('REQUEST_URI').split('?')[0], ctx.homepath)

        if env.get('QUERY_STRING'):
            ctx.query = '?' + env.get('QUERY_STRING', '')
        else:
            ctx.query = ''

        ctx.fullpath = ctx.path + ctx.query
        
        for k, v in ctx.iteritems():
            if isinstance(v, str):
                ctx[k] = safeunicode(v)

        # status must always be str
        ctx.status = '200 OK'
        
        ctx.app_stack = []

    def _delegate(self, f, fvars, args=[]):
        def handle_class(cls):
            meth = web.ctx.method
            if meth == 'HEAD' and not hasattr(cls, meth):
                meth = 'GET'
            if not hasattr(cls, meth):
                raise web.nomethod(cls)
            tocall = getattr(cls(), meth)
            return tocall(*args)
            
        def is_class(o): return isinstance(o, (types.ClassType, type))
            
        if f is None:
            raise web.notfound()
        elif isinstance(f, application):
            return f.handle_with_processors()
        elif is_class(f):
            return handle_class(f)
        elif isinstance(f, basestring):
            if f.startswith('redirect '):
                url = f.split(' ', 1)[1]
                if web.ctx.method == "GET":
                    x = web.ctx.env.get('QUERY_STRING', '')
                    if x:
                        url += '?' + x
                raise web.redirect(url)
            elif '.' in f:
                x = f.split('.')
                mod, cls = '.'.join(x[:-1]), x[-1]
                mod = __import__(mod, globals(), locals(), [""])
                cls = getattr(mod, cls)
            else:
                cls = fvars[f]
            return handle_class(cls)
        elif hasattr(f, '__call__'):
            return f()
        else:
            return web.notfound()

    def _match(self, mapping, value):
        for pat, what in utils.group(mapping, 2):
            if isinstance(what, application):
                if value.startswith(pat):
                    f = lambda: self._delegate_sub_application(pat, what)
                    return f, None
                else:
                    continue
            elif isinstance(what, basestring):
                what, result = utils.re_subm('^' + pat + '$', what, value)
            else:
                result = utils.re_compile('^' + pat + '$').match(value)
                
            if result: # it's a match
                return what, [x and urllib.unquote(x) for x in result.groups()]
        return None, None
        
    def _delegate_sub_application(self, dir, app):
        """Deletes request to sub application `app` rooted at the directory `dir`.
        The home, homepath, path and fullpath values in web.ctx are updated to mimic request
        to the subapp and are restored after it is handled. 
        
        @@Any issues with when used with yield?
        """
        try:
            oldctx = web.storage(web.ctx)
            web.ctx.home += dir
            web.ctx.homepath += dir
            web.ctx.path = web.ctx.path[len(dir):]
            web.ctx.fullpath = web.ctx.fullpath[len(dir):]
            return app.handle_with_processors()
        finally:
            web.ctx.home = oldctx.home
            web.ctx.homepath = oldctx.homepath
            web.ctx.path = oldctx.path
            web.ctx.fullpath = oldctx.fullpath
            
    def get_parent_app(self):
        if self in web.ctx.app_stack:
            index = web.ctx.app_stack.index(self)
            if index > 0:
                return web.ctx.app_stack[index-1]
        
    def notfound(self):
        """Returns HTTPError with '404 not found' message"""
        parent = self.get_parent_app()
        if parent:
            return parent.notfound()
        else:
            return web._NotFound()
            
    def internalerror(self):
        """Returns HTTPError with '500 internal error' message"""
        parent = self.get_parent_app()
        if parent:
            return parent.internalerror()
        elif web.config.get('debug'):
            import debugerror
            return debugerror.debugerror()
        else:
            return web._InternalError()

class auto_application(application):
    """Application similar to `application` but urls are constructed 
    automatiacally using metaclass.

        >>> app = auto_application()
        >>> class hello(app.page):
        ...     def GET(self): return "hello, world"
        ...
        >>> class foo(app.page):
        ...     path = '/foo/.*'
        ...     def GET(self): return "foo"
        >>> app.request("/hello").data
        'hello, world'
        >>> app.request('/foo/bar').data
        'foo'
    """
    def __init__(self):
        application.__init__(self)

        class metapage(type):
            def __init__(klass, name, bases, attrs):
                type.__init__(klass, name, bases, attrs)
                path = attrs.get('path', '/' + name)

                # path can be specified as None to ignore that class
                # typically required to create a abstract base class.
                if path is not None:
                    self.add_mapping(path, klass)

        class page:
            path = None
            __metaclass__ = metapage

        self.page = page

# The application class already has the required functionality of subdir_application
subdir_application = application
                
class subdomain_application(application):
    """
    Application to delegate requests based on the host.

        >>> urls = ("/hello", "hello")
        >>> app = application(urls, globals())
        >>> class hello:
        ...     def GET(self): return "hello"
        >>>
        >>> mapping = ("hello.example.com", app)
        >>> app2 = subdomain_application(mapping)
        >>> app2.request("/hello", host="hello.example.com").data
        'hello'
        >>> response = app2.request("/hello", host="something.example.com")
        >>> response.status
        '404 Not Found'
        >>> response.data
        'not found'
    """
    def handle(self):
        host = web.ctx.host.split(':')[0] #strip port
        fn, args = self._match(self.mapping, host)
        return self._delegate(fn, self.fvars, args)
        
    def _match(self, mapping, value):
        for pat, what in utils.group(mapping, 2):
            if isinstance(what, basestring):
                what, result = utils.re_subm('^' + pat + '$', what, value)
            else:
                result = utils.re_compile('^' + pat + '$').match(value)

            if result: # it's a match
                return what, [x and urllib.unquote(x) for x in result.groups()]
        return None, None
        
def loadhook(h):
    """
    Converts a load hook into an application processor.
    
        >>> app = auto_application()
        >>> def f(): "something done before handling request"
        ...
        >>> app.add_processor(loadhook(f))
    """
    def processor(handler):
        h()
        return handler()
        
    return processor
    
def unloadhook(h):
    """
    Converts an unload hook into an application processor.
    
        >>> app = auto_application()
        >>> def f(): "something done after handling request"
        ...
        >>> app.add_processor(unloadhook(f))    
    """
    def processor(handler):
        try:
            return handler()
        finally:
            h()
            
    return processor

def autodelegate(prefix=''):
    """
    Returns a method that takes one argument and calls the method named prefix+arg,
    calling `notfound()` if there isn't one. Example:

        urls = ('/prefs/(.*)', 'prefs')

        class prefs:
            GET = autodelegate('GET_')
            def GET_password(self): pass
            def GET_privacy(self): pass

    `GET_password` would get called for `/prefs/password` while `GET_privacy` for 
    `GET_privacy` gets called for `/prefs/privacy`.
    
    If a user visits `/prefs/password/change` then `GET_password(self, '/change')`
    is called.
    """
    def internal(self, arg):
        if '/' in arg:
            first, rest = arg.split('/', 1)
            func = prefix + first
            args = ['/' + rest]
        else:
            func = prefix + arg
            args = []
        
        if hasattr(self, func):
            try:
                return getattr(self, func)(*args)
            except TypeError:
                return web.notfound()
        else:
            return web.notfound()
    return internal

class Reloader:
    """Checks to see if any loaded modules have changed on disk and, 
    if so, reloads them.
    """
    def __init__(self):
        self.mtimes = {}

    def __call__(self):
        for mod in sys.modules.values():
            self.check(mod)
            
    def check(self, mod):
        try: 
            mtime = os.stat(mod.__file__).st_mtime
        except (AttributeError, OSError, IOError):
            return
        if mod.__file__.endswith('.pyc') and os.path.exists(mod.__file__[:-1]):
            mtime = max(os.stat(mod.__file__[:-1]).st_mtime, mtime)
            
        if mod not in self.mtimes:
            self.mtimes[mod] = mtime
        elif self.mtimes[mod] < mtime:
            try: 
                reload(mod)
                self.mtimes[mod] = mtime
            except ImportError: 
                pass

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = browser
"""Browser to test web applications.
(from web.py)
"""
from utils import re_compile
from net import htmlunquote

import httplib, urllib, urllib2
import cookielib
import copy
from StringIO import StringIO

DEBUG = False

__all__ = [
    "BrowserError",
    "Browser", "AppBrowser",
    "AppHandler"
]

class BrowserError(Exception):
    pass

class Browser:
    def __init__(self):
        self.cookiejar = cookielib.CookieJar()
        self._cookie_processor = urllib2.HTTPCookieProcessor(self.cookiejar)
        self.form = None

        self.url = "http://0.0.0.0:8080/"
        self.path = "/"
        
        self.status = None
        self.data = None
        self._response = None
        self._forms = None

    def reset(self):
        """Clears all cookies and history."""
        self.cookiejar.clear()

    def build_opener(self):
        """Builds the opener using urllib2.build_opener. 
        Subclasses can override this function to prodive custom openers.
        """
        return urllib2.build_opener()

    def do_request(self, req):
        if DEBUG:
            print 'requesting', req.get_method(), req.get_full_url()
        opener = self.build_opener()
        opener.add_handler(self._cookie_processor)
        try:
            self._response = opener.open(req)
        except urllib2.HTTPError, e:
            self._response = e

        self.url = self._response.geturl()
        self.path = urllib2.Request(self.url).get_selector()
        self.data = self._response.read()
        self.status = self._response.code
        self._forms = None
        self.form = None
        return self.get_response()

    def open(self, url, data=None, headers={}):
        """Opens the specified url."""
        url = urllib.basejoin(self.url, url)
        req = urllib2.Request(url, data, headers)
        return self.do_request(req)

    def show(self):
        """Opens the current page in real web browser."""
        f = open('page.html', 'w')
        f.write(self.data)
        f.close()

        import webbrowser, os
        url = 'file://' + os.path.abspath('page.html')
        webbrowser.open(url)

    def get_response(self):
        """Returns a copy of the current response."""
        return urllib.addinfourl(StringIO(self.data), self._response.info(), self._response.geturl())

    def get_soup(self):
        """Returns beautiful soup of the current document."""
        import BeautifulSoup
        return BeautifulSoup.BeautifulSoup(self.data)

    def get_text(self, e=None):
        """Returns content of e or the current document as plain text."""
        e = e or self.get_soup()
        return ''.join([htmlunquote(c) for c in e.recursiveChildGenerator() if isinstance(c, unicode)])

    def _get_links(self):
        soup = self.get_soup()
        return [a for a in soup.findAll(name='a')]
        
    def get_links(self, text=None, text_regex=None, url=None, url_regex=None, predicate=None):
        """Returns all links in the document."""
        return self._filter_links(self._get_links(),
            text=text, text_regex=text_regex, url=url, url_regex=url_regex, predicate=predicate)

    def follow_link(self, link=None, text=None, text_regex=None, url=None, url_regex=None, predicate=None):
        if link is None:
            links = self._filter_links(self.get_links(),
                text=text, text_regex=text_regex, url=url, url_regex=url_regex, predicate=predicate)
            link = links and links[0]
            
        if link:
            return self.open(link['href'])
        else:
            raise BrowserError("No link found")
            
    def find_link(self, text=None, text_regex=None, url=None, url_regex=None, predicate=None):
        links = self._filter_links(self.get_links(), 
            text=text, text_regex=text_regex, url=url, url_regex=url_regex, predicate=predicate)
        return links and links[0] or None
            
    def _filter_links(self, links, 
            text=None, text_regex=None,
            url=None, url_regex=None,
            predicate=None):
        predicates = []
        if text is not None:
            predicates.append(lambda link: link.string == text)
        if text_regex is not None:
            predicates.append(lambda link: re_compile(text_regex).search(link.string or ''))
        if url is not None:
            predicates.append(lambda link: link.get('href') == url)
        if url_regex is not None:
            predicates.append(lambda link: re_compile(url_regex).search(link.get('href', '')))
        if predicate:
            predicate.append(predicate)

        def f(link):
            for p in predicates:
                if not p(link):
                    return False
            return True

        return [link for link in links if f(link)]

    def get_forms(self):
        """Returns all forms in the current document.
        The returned form objects implement the ClientForm.HTMLForm interface.
        """
        if self._forms is None:
            import ClientForm
            self._forms = ClientForm.ParseResponse(self.get_response(), backwards_compat=False)
        return self._forms

    def select_form(self, name=None, predicate=None, index=0):
        """Selects the specified form."""
        forms = self.get_forms()

        if name is not None:
            forms = [f for f in forms if f.name == name]
        if predicate:
            forms = [f for f in forms if predicate(f)]
            
        if forms:
            self.form = forms[index]
            return self.form
        else:
            raise BrowserError("No form selected.")
        
    def submit(self):
        """submits the currently selected form."""
        if self.form is None:
            raise BrowserError("No form selected.")
        req = self.form.click()
        return self.do_request(req)

    def __getitem__(self, key):
        return self.form[key]

    def __setitem__(self, key, value):
        self.form[key] = value

class AppBrowser(Browser):
    """Browser interface to test web.py apps.
    
        b = AppBrowser(app)
        b.open('/')
        b.follow_link(text='Login')
        
        b.select_form(name='login')
        b['username'] = 'joe'
        b['password'] = 'secret'
        b.submit()

        assert b.path == '/'
        assert 'Welcome joe' in b.get_text()
    """
    def __init__(self, app):
        Browser.__init__(self)
        self.app = app

    def build_opener(self):
        return urllib2.build_opener(AppHandler(self.app))

class AppHandler(urllib2.HTTPHandler):
    """urllib2 handler to handle requests using web.py application."""
    handler_order = 100

    def __init__(self, app):
        self.app = app

    def http_open(self, req):
        result = self.app.request(
            localpart=req.get_selector(),
            method=req.get_method(),
            host=req.get_host(),
            data=req.get_data(),
            headers=dict(req.header_items()),
            https=req.get_type() == "https"
        )
        return self._make_response(result, req.get_full_url())

    def https_open(self, req):
        return self.http_open(req)

    https_request = urllib2.HTTPHandler.do_request_

    def _make_response(self, result, url):
        data = "\r\n".join(["%s: %s" % (k, v) for k, v in result.header_items])
        headers = httplib.HTTPMessage(StringIO(data))
        response = urllib.addinfourl(StringIO(result.data), headers, url)
        code, msg = result.status.split(None, 1)
        response.code, response.msg = int(code), msg
        return response

########NEW FILE########
__FILENAME__ = template
"""
Interface to various templating engines.
"""
import os.path

__all__ = [
    "render_cheetah", "render_genshi", "render_mako",
    "cache", 
]

class render_cheetah:
    """Rendering interface to Cheetah Templates.

    Example:

        render = render_cheetah('templates')
        render.hello(name="cheetah")
    """
    def __init__(self, path):
        # give error if Chetah is not installed
        from Cheetah.Template import Template
        self.path = path

    def __getattr__(self, name):
        from Cheetah.Template import Template
        path = os.path.join(self.path, name + ".html")
        
        def template(**kw):
            t = Template(file=path, searchList=[kw])
            return t.respond()

        return template
    
class render_genshi:
    """Rendering interface genshi templates.
    Example:

    for xml/html templates.

        render = render_genshi(['templates/'])
        render.hello(name='genshi')

    For text templates:

        render = render_genshi(['templates/'], type='text')
        render.hello(name='genshi')
    """

    def __init__(self, *a, **kwargs):
        from genshi.template import TemplateLoader

        self._type = kwargs.pop('type', None)
        self._loader = TemplateLoader(*a, **kwargs)

    def __getattr__(self, name):
        # Assuming all templates are html
        path = name + ".html"

        if self._type == "text":
            from genshi.template import TextTemplate
            cls = TextTemplate
            type = "text"
        else:
            cls = None
            type = None

        t = self._loader.load(path, cls=cls)
        def template(**kw):
            stream = t.generate(**kw)
            if type:
                return stream.render(type)
            else:
                return stream.render()
        return template

class render_jinja:
    """Rendering interface to Jinja2 Templates
    
    Example:

        render= render_jinja('templates')
        render.hello(name='jinja2')
    """
    def __init__(self, *a, **kwargs):
        from jinja2 import Environment,FileSystemLoader
        self._lookup = Environment(loader=FileSystemLoader(*a, **kwargs))
        
    def __getattr__(self, name):
        # Assuming all templates end with .html
        path = name + '.html'
        t = self._lookup.get_template(path)
        return t.render
        
class render_mako:
    """Rendering interface to Mako Templates.

    Example:

        render = render_mako(directories=['templates'])
        render.hello(name="mako")
    """
    def __init__(self, *a, **kwargs):
        from mako.lookup import TemplateLookup
        self._lookup = TemplateLookup(*a, **kwargs)

    def __getattr__(self, name):
        # Assuming all templates are html
        path = name + ".html"
        t = self._lookup.get_template(path)
        return t.render

class cache:
    """Cache for any rendering interface.
    
    Example:

        render = cache(render_cheetah("templates/"))
        render.hello(name='cache')
    """
    def __init__(self, render):
        self._render = render
        self._cache = {}

    def __getattr__(self, name):
        if name not in self._cache:
            self._cache[name] = getattr(self._render, name)
        return self._cache[name]

########NEW FILE########
__FILENAME__ = db
"""
Database API
(part of web.py)
"""

__all__ = [
  "UnknownParamstyle", "UnknownDB", "TransactionError", 
  "sqllist", "sqlors", "reparam", "sqlquote",
  "SQLQuery", "SQLParam", "sqlparam",
  "SQLLiteral", "sqlliteral",
  "database", 'DB',
]

import time
try:
    import datetime
except ImportError:
    datetime = None

from utils import threadeddict, storage, iters, iterbetter

try:
    # db module can work independent of web.py
    from webapi import debug, config
except:
    import sys
    debug = sys.stderr
    config = storage()

class UnknownDB(Exception):
    """raised for unsupported dbms"""
    pass

class _ItplError(ValueError): 
    def __init__(self, text, pos):
        ValueError.__init__(self)
        self.text = text
        self.pos = pos
    def __str__(self):
        return "unfinished expression in %s at char %d" % (
            repr(self.text), self.pos)

class TransactionError(Exception): pass

class UnknownParamstyle(Exception): 
    """
    raised for unsupported db paramstyles

    (currently supported: qmark, numeric, format, pyformat)
    """
    pass
    
class SQLParam:
    """
    Parameter in SQLQuery.
    
        >>> q = SQLQuery(["SELECT * FROM test WHERE name=", SQLParam("joe")])
        >>> q
        <sql: "SELECT * FROM test WHERE name='joe'">
        >>> q.query()
        'SELECT * FROM test WHERE name=%s'
        >>> q.values()
        ['joe']
    """
    def __init__(self, value):
        self.value = value
        
    def get_marker(self, paramstyle='pyformat'):
        if paramstyle == 'qmark':
            return '?'
        elif paramstyle == 'numeric':
            return ':1'
        elif paramstyle is None or paramstyle in ['format', 'pyformat']:
            return '%s'
        raise UnknownParamstyle, paramstyle
        
    def sqlquery(self): 
        return SQLQuery([self])
        
    def __add__(self, other):
        return self.sqlquery() + other
        
    def __radd__(self, other):
        return other + self.sqlquery() 
            
    def __str__(self): 
        return str(self.value)
    
    def __repr__(self):
        return '<param: %s>' % repr(self.value)

sqlparam =  SQLParam

class SQLQuery:
    """
    You can pass this sort of thing as a clause in any db function.
    Otherwise, you can pass a dictionary to the keyword argument `vars`
    and the function will call reparam for you.

    Internally, consists of `items`, which is a list of strings and
    SQLParams, which get concatenated to produce the actual query.
    """
    # tested in sqlquote's docstring
    def __init__(self, items=[]):
        """Creates a new SQLQuery.
        
            >>> SQLQuery("x")
            <sql: 'x'>
            >>> q = SQLQuery(['SELECT * FROM ', 'test', ' WHERE x=', SQLParam(1)])
            >>> q
            <sql: 'SELECT * FROM test WHERE x=1'>
            >>> q.query(), q.values()
            ('SELECT * FROM test WHERE x=%s', [1])
            >>> SQLQuery(SQLParam(1))
            <sql: '1'>
        """
        if isinstance(items, list):
            self.items = items
        elif isinstance(items, SQLParam):
            self.items = [items]
        elif isinstance(items, SQLQuery):
            self.items = list(items.items)
        else:
            self.items = [str(items)]
            
        # Take care of SQLLiterals
        for i, item in enumerate(self.items):
            if isinstance(item, SQLParam) and isinstance(item.value, SQLLiteral):
                self.items[i] = item.value.v

    def __add__(self, other):
        if isinstance(other, basestring):
            items = [other]
        elif isinstance(other, SQLQuery):
            items = other.items
        else:
            return NotImplemented
        return SQLQuery(self.items + items)

    def __radd__(self, other):
        if isinstance(other, basestring):
            items = [other]
        else:
            return NotImplemented
            
        return SQLQuery(items + self.items)

    def __iadd__(self, other):
        if isinstance(other, basestring):
            items = [other]
        elif isinstance(other, SQLQuery):
            items = other.items
        else:
            return NotImplemented
        self.items.extend(items)
        return self

    def __len__(self):
        return len(self.query())
        
    def query(self, paramstyle=None):
        """
        Returns the query part of the sql query.
            >>> q = SQLQuery(["SELECT * FROM test WHERE name=", SQLParam('joe')])
            >>> q.query()
            'SELECT * FROM test WHERE name=%s'
            >>> q.query(paramstyle='qmark')
            'SELECT * FROM test WHERE name=?'
        """
        s = ''
        for x in self.items:
            if isinstance(x, SQLParam):
                x = x.get_marker(paramstyle)
            s += x
        return s
    
    def values(self):
        """
        Returns the values of the parameters used in the sql query.
            >>> q = SQLQuery(["SELECT * FROM test WHERE name=", SQLParam('joe')])
            >>> q.values()
            ['joe']
        """
        return [i.value for i in self.items if isinstance(i, SQLParam)]
        
    def join(items, sep=' '):
        """
        Joins multiple queries.
        
        >>> SQLQuery.join(['a', 'b'], ', ')
        <sql: 'a, b'>
        """
        if len(items) == 0:
            return SQLQuery("")

        q = SQLQuery(items[0])
        for item in items[1:]:
            q += sep
            q += item
        return q
    
    join = staticmethod(join)

    def __str__(self):
        try:
            return self.query() % tuple([sqlify(x) for x in self.values()])
        except (ValueError, TypeError):
            return self.query()

    def __repr__(self):
        return '<sql: %s>' % repr(str(self))

class SQLLiteral: 
    """
    Protects a string from `sqlquote`.

        >>> sqlquote('NOW()')
        <sql: "'NOW()'">
        >>> sqlquote(SQLLiteral('NOW()'))
        <sql: 'NOW()'>
    """
    def __init__(self, v): 
        self.v = v

    def __repr__(self): 
        return self.v

sqlliteral = SQLLiteral

def reparam(string_, dictionary): 
    """
    Takes a string and a dictionary and interpolates the string
    using values from the dictionary. Returns an `SQLQuery` for the result.

        >>> reparam("s = $s", dict(s=True))
        <sql: "s = 't'">
    """
    dictionary = dictionary.copy() # eval mucks with it
    vals = []
    result = []
    for live, chunk in _interpolate(string_):
        if live:
            v = eval(chunk, dictionary)
            result.append(sqlparam(v))
        else: 
            result.append(chunk)
    return SQLQuery.join(result, '')

def sqlify(obj): 
    """
    converts `obj` to its proper SQL version

        >>> sqlify(None)
        'NULL'
        >>> sqlify(True)
        "'t'"
        >>> sqlify(3)
        '3'
    """
    # because `1 == True and hash(1) == hash(True)`
    # we have to do this the hard way...

    if obj is None:
        return 'NULL'
    elif obj is True:
        return "'t'"
    elif obj is False:
        return "'f'"
    elif datetime and isinstance(obj, datetime.datetime):
        return repr(obj.isoformat())
    else:
        return repr(obj)

def sqllist(lst): 
    """
    Converts the arguments for use in something like a WHERE clause.
    
        >>> sqllist(['a', 'b'])
        'a, b'
        >>> sqllist('a')
        'a'
        >>> sqllist(u'abc')
        u'abc'
    """
    if isinstance(lst, basestring): 
        return lst
    else:
        return ', '.join(lst)

def sqlors(left, lst):
    """
    `left is a SQL clause like `tablename.arg = ` 
    and `lst` is a list of values. Returns a reparam-style
    pair featuring the SQL that ORs together the clause
    for each item in the lst.

        >>> sqlors('foo = ', [])
        <sql: '1=2'>
        >>> sqlors('foo = ', [1])
        <sql: 'foo = 1'>
        >>> sqlors('foo = ', 1)
        <sql: 'foo = 1'>
        >>> sqlors('foo = ', [1,2,3])
        <sql: '(foo = 1 OR foo = 2 OR foo = 3 OR 1=2)'>
    """
    if isinstance(lst, iters):
        lst = list(lst)
        ln = len(lst)
        if ln == 0:
            return SQLQuery("1=2")
        if ln == 1:
            lst = lst[0]

    if isinstance(lst, iters):
        return SQLQuery(['('] + 
          sum([[left, sqlparam(x), ' OR '] for x in lst], []) +
          ['1=2)']
        )
    else:
        return left + sqlparam(lst)
        
def sqlwhere(dictionary, grouping=' AND '): 
    """
    Converts a `dictionary` to an SQL WHERE clause `SQLQuery`.
    
        >>> sqlwhere({'cust_id': 2, 'order_id':3})
        <sql: 'order_id = 3 AND cust_id = 2'>
        >>> sqlwhere({'cust_id': 2, 'order_id':3}, grouping=', ')
        <sql: 'order_id = 3, cust_id = 2'>
        >>> sqlwhere({'a': 'a', 'b': 'b'}).query()
        'a = %s AND b = %s'
    """
    return SQLQuery.join([k + ' = ' + sqlparam(v) for k, v in dictionary.items()], grouping)

def sqlquote(a): 
    """
    Ensures `a` is quoted properly for use in a SQL query.

        >>> 'WHERE x = ' + sqlquote(True) + ' AND y = ' + sqlquote(3)
        <sql: "WHERE x = 't' AND y = 3">
    """
    return sqlparam(a).sqlquery()

class Transaction:
    """Database transaction."""
    def __init__(self, ctx):
        self.ctx = ctx
        self.transaction_count = transaction_count = len(ctx.transactions)

        class transaction_engine:
            """Transaction Engine used in top level transactions."""
            def do_transact(self):
                ctx.commit(unload=False)

            def do_commit(self):
                ctx.commit()

            def do_rollback(self):
                ctx.rollback()

        class subtransaction_engine:
            """Transaction Engine used in sub transactions."""
            def query(self, q):
                db_cursor = ctx.db.cursor()
                ctx.db_execute(db_cursor, SQLQuery(q % transaction_count))

            def do_transact(self):
                self.query('SAVEPOINT webpy_sp_%s')

            def do_commit(self):
                self.query('RELEASE SAVEPOINT webpy_sp_%s')

            def do_rollback(self):
                self.query('ROLLBACK TO SAVEPOINT webpy_sp_%s')

        class dummy_engine:
            """Transaction Engine used instead of subtransaction_engine 
            when sub transactions are not supported."""
            do_transact = do_commit = do_rollback = lambda self: None

        if self.transaction_count:
            # nested transactions are not supported in some databases
            if self.ctx.get('ignore_nested_transactions'):
                self.engine = dummy_engine()
            else:
                self.engine = subtransaction_engine()
        else:
            self.engine = transaction_engine()

        self.engine.do_transact()
        self.ctx.transactions.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exctype, excvalue, traceback):
        if exctype is not None:
            self.rollback()
        else:
            self.commit()

    def commit(self):
        if len(self.ctx.transactions) > self.transaction_count:
            self.engine.do_commit()
            self.ctx.transactions = self.ctx.transactions[:self.transaction_count]

    def rollback(self):
        if len(self.ctx.transactions) > self.transaction_count:
            self.engine.do_rollback()
            self.ctx.transactions = self.ctx.transactions[:self.transaction_count]

class DB: 
    """Database"""
    def __init__(self, db_module, keywords):
        """Creates a database.
        """
        self.db_module = db_module
        self.keywords = keywords
        
        self._ctx = threadeddict()
        # flag to enable/disable printing queries
        self.printing = config.get('debug', False)
        self.supports_multiple_insert = False
        
        try:
            import DBUtils
            # enable pooling if DBUtils module is available.
            self.has_pooling = True
        except ImportError:
            self.has_pooling = False
            
        # Pooling can be disabled by passing pooling=False in the keywords.
        self.has_pooling = self.keywords.pop('pooling', True) and self.has_pooling
            
    def _getctx(self): 
        if not self._ctx.get('db'):
            self._load_context(self._ctx)
        return self._ctx
    ctx = property(_getctx)
    
    def _load_context(self, ctx):
        ctx.dbq_count = 0
        ctx.transactions = [] # stack of transactions
        
        if self.has_pooling:
            ctx.db = self._connect_with_pooling(self.keywords)
        else:
            ctx.db = self._connect(self.keywords)
        ctx.db_execute = self._db_execute
        
        if not hasattr(ctx.db, 'commit'):
            ctx.db.commit = lambda: None

        if not hasattr(ctx.db, 'rollback'):
            ctx.db.rollback = lambda: None
            
        def commit(unload=True):
            # do db commit and release the connection if pooling is enabled.            
            ctx.db.commit()
            if unload and self.has_pooling:
                self._unload_context(self._ctx)
                
        def rollback():
            # do db rollback and release the connection if pooling is enabled.
            ctx.db.rollback()
            if self.has_pooling:
                self._unload_context(self._ctx)
                
        ctx.commit = commit
        ctx.rollback = rollback
            
    def _unload_context(self, ctx):
        del ctx.db
            
    def _connect(self, keywords):
        return self.db_module.connect(**keywords)
        
    def _connect_with_pooling(self, keywords):
        def get_pooled_db():
            from DBUtils import PooledDB

            # In DBUtils 0.9.3, `dbapi` argument is renamed as `creator`
            # see Bug#122112
            
            if PooledDB.__version__.split('.') < '0.9.3'.split('.'):
                return PooledDB.PooledDB(dbapi=self.db_module, **keywords)
            else:
                return PooledDB.PooledDB(creator=self.db_module, **keywords)
        
        if getattr(self, '_pooleddb', None) is None:
            self._pooleddb = get_pooled_db()
        
        return self._pooleddb.connection()
        
    def _db_cursor(self):
        return self.ctx.db.cursor()

    def _param_marker(self):
        """Returns parameter marker based on paramstyle attribute if this database."""
        style = getattr(self, 'paramstyle', 'pyformat')

        if style == 'qmark':
            return '?'
        elif style == 'numeric':
            return ':1'
        elif style in ['format', 'pyformat']:
            return '%s'
        raise UnknownParamstyle, style

    def _py2sql(self, val):
        """
        Transforms a Python value into a value to pass to cursor.execute.

        This exists specifically for a workaround in SqliteDB.

        """
        if isinstance(val, unicode):
            val = val.encode('UTF-8')
        return val

    def _db_execute(self, cur, sql_query): 
        """executes an sql query"""
        self.ctx.dbq_count += 1
        
        try:
            a = time.time()
            paramstyle = getattr(self, 'paramstyle', 'pyformat')
            out = cur.execute(sql_query.query(paramstyle),
                              [self._py2sql(x)
                               for x in sql_query.values()])
            b = time.time()
        except:
            if self.printing:
                print >> debug, 'ERR:', str(sql_query)
            if self.ctx.transactions:
                self.ctx.transactions[-1].rollback()
            else:
                self.ctx.rollback()
            raise

        if self.printing:
            print >> debug, '%s (%s): %s' % (round(b-a, 2), self.ctx.dbq_count, str(sql_query))
        return out
    
    def _where(self, where, vars): 
        if isinstance(where, (int, long)):
            where = "id = " + sqlparam(where)
        #@@@ for backward-compatibility
        elif isinstance(where, (list, tuple)) and len(where) == 2:
            where = SQLQuery(where[0], where[1])
        elif isinstance(where, SQLQuery):
            pass
        else:
            where = reparam(where, vars)        
        return where
    
    def query(self, sql_query, vars=None, processed=False, _test=False): 
        """
        Execute SQL query `sql_query` using dictionary `vars` to interpolate it.
        If `processed=True`, `vars` is a `reparam`-style list to use 
        instead of interpolating.
        
            >>> db = DB(None, {})
            >>> db.query("SELECT * FROM foo", _test=True)
            <sql: 'SELECT * FROM foo'>
            >>> db.query("SELECT * FROM foo WHERE x = $x", vars=dict(x='f'), _test=True)
            <sql: "SELECT * FROM foo WHERE x = 'f'">
            >>> db.query("SELECT * FROM foo WHERE x = " + sqlquote('f'), _test=True)
            <sql: "SELECT * FROM foo WHERE x = 'f'">
        """
        if vars is None: vars = {}
        
        if not processed and not isinstance(sql_query, SQLQuery):
            sql_query = reparam(sql_query, vars)
        
        if _test: return sql_query
        
        db_cursor = self._db_cursor()
        self._db_execute(db_cursor, sql_query)
        
        if db_cursor.description:
            names = [x[0] for x in db_cursor.description]
            def iterwrapper():
                row = db_cursor.fetchone()
                while row:
                    yield storage(dict(zip(names, row)))
                    row = db_cursor.fetchone()
            out = iterbetter(iterwrapper())
            out.__len__ = lambda: int(db_cursor.rowcount)
            out.list = lambda: [storage(dict(zip(names, x))) \
                               for x in db_cursor.fetchall()]
        else:
            out = db_cursor.rowcount
        
        if not self.ctx.transactions: 
            self.ctx.commit()
        return out
    
    def select(self, tables, vars=None, what='*', where=None, order=None, group=None, 
               limit=None, offset=None, _test=False): 
        """
        Selects `what` from `tables` with clauses `where`, `order`, 
        `group`, `limit`, and `offset`. Uses vars to interpolate. 
        Otherwise, each clause can be a SQLQuery.
        
            >>> db = DB(None, {})
            >>> db.select('foo', _test=True)
            <sql: 'SELECT * FROM foo'>
            >>> db.select(['foo', 'bar'], where="foo.bar_id = bar.id", limit=5, _test=True)
            <sql: 'SELECT * FROM foo, bar WHERE foo.bar_id = bar.id LIMIT 5'>
        """
        if vars is None: vars = {}
        sql_clauses = self.sql_clauses(what, tables, where, group, order, limit, offset)
        clauses = [self.gen_clause(sql, val, vars) for sql, val in sql_clauses if val is not None]
        qout = SQLQuery.join(clauses)
        if _test: return qout
        return self.query(qout, processed=True)
    
    def where(self, table, what='*', order=None, group=None, limit=None, 
              offset=None, _test=False, **kwargs):
        """
        Selects from `table` where keys are equal to values in `kwargs`.
        
            >>> db = DB(None, {})
            >>> db.where('foo', bar_id=3, _test=True)
            <sql: 'SELECT * FROM foo WHERE bar_id = 3'>
            >>> db.where('foo', source=2, crust='dewey', _test=True)
            <sql: "SELECT * FROM foo WHERE source = 2 AND crust = 'dewey'">
        """
        where = []
        for k, v in kwargs.iteritems():
            where.append(k + ' = ' + sqlquote(v))
        return self.select(table, what=what, order=order, 
               group=group, limit=limit, offset=offset, _test=_test, 
               where=SQLQuery.join(where, ' AND '))
    
    def sql_clauses(self, what, tables, where, group, order, limit, offset): 
        return (
            ('SELECT', what),
            ('FROM', sqllist(tables)),
            ('WHERE', where),
            ('GROUP BY', group),
            ('ORDER BY', order),
            ('LIMIT', limit),
            ('OFFSET', offset))
    
    def gen_clause(self, sql, val, vars): 
        if isinstance(val, (int, long)):
            if sql == 'WHERE':
                nout = 'id = ' + sqlquote(val)
            else:
                nout = SQLQuery(val)
        #@@@
        elif isinstance(val, (list, tuple)) and len(val) == 2:
            nout = SQLQuery(val[0], val[1]) # backwards-compatibility
        elif isinstance(val, SQLQuery):
            nout = val
        else:
            nout = reparam(val, vars)

        def xjoin(a, b):
            if a and b: return a + ' ' + b
            else: return a or b

        return xjoin(sql, nout)

    def insert(self, tablename, seqname=None, _test=False, **values): 
        """
        Inserts `values` into `tablename`. Returns current sequence ID.
        Set `seqname` to the ID if it's not the default, or to `False`
        if there isn't one.
        
            >>> db = DB(None, {})
            >>> q = db.insert('foo', name='bob', age=2, created=SQLLiteral('NOW()'), _test=True)
            >>> q
            <sql: "INSERT INTO foo (age, name, created) VALUES (2, 'bob', NOW())">
            >>> q.query()
            'INSERT INTO foo (age, name, created) VALUES (%s, %s, NOW())'
            >>> q.values()
            [2, 'bob']
        """
        def q(x): return "(" + x + ")"
        
        if values:
            _keys = SQLQuery.join(values.keys(), ', ')
            _values = SQLQuery.join([sqlparam(v) for v in values.values()], ', ')
            sql_query = "INSERT INTO %s " % tablename + q(_keys) + ' VALUES ' + q(_values)
        else:
            sql_query = SQLQuery("INSERT INTO %s DEFAULT VALUES" % tablename)

        if _test: return sql_query
        
        db_cursor = self._db_cursor()
        if seqname is not False: 
            sql_query = self._process_insert_query(sql_query, tablename, seqname)

        if isinstance(sql_query, tuple):
            # for some databases, a separate query has to be made to find 
            # the id of the inserted row.
            q1, q2 = sql_query
            self._db_execute(db_cursor, q1)
            self._db_execute(db_cursor, q2)
        else:
            self._db_execute(db_cursor, sql_query)

        try: 
            out = db_cursor.fetchone()[0]
        except Exception: 
            out = None
        
        if not self.ctx.transactions: 
            self.ctx.commit()
        return out
        
    def multiple_insert(self, tablename, values, seqname=None, _test=False):
        """
        Inserts multiple rows into `tablename`. The `values` must be a list of dictioanries, 
        one for each row to be inserted, each with the same set of keys.
        Returns the list of ids of the inserted rows.        
        Set `seqname` to the ID if it's not the default, or to `False`
        if there isn't one.
        
            >>> db = DB(None, {})
            >>> db.supports_multiple_insert = True
            >>> values = [{"name": "foo", "email": "foo@example.com"}, {"name": "bar", "email": "bar@example.com"}]
            >>> db.multiple_insert('person', values=values, _test=True)
            <sql: "INSERT INTO person (name, email) VALUES ('foo', 'foo@example.com'), ('bar', 'bar@example.com')">
        """        
        if not values:
            return []
            
        if not self.supports_multiple_insert:
            out = [self.insert(tablename, seqname=seqname, _test=_test, **v) for v in values]
            if seqname is False:
                return None
            else:
                return out
                
        keys = values[0].keys()
        #@@ make sure all keys are valid

        # make sure all rows have same keys.
        for v in values:
            if v.keys() != keys:
                raise ValueError, 'Bad data'

        sql_query = SQLQuery('INSERT INTO %s (%s) VALUES ' % (tablename, ', '.join(keys))) 

        data = []
        for row in values:
            d = SQLQuery.join([SQLParam(row[k]) for k in keys], ', ')
            data.append('(' + d + ')')
        sql_query += SQLQuery.join(data, ', ')

        if _test: return sql_query

        db_cursor = self._db_cursor()
        if seqname is not False: 
            sql_query = self._process_insert_query(sql_query, tablename, seqname)

        if isinstance(sql_query, tuple):
            # for some databases, a separate query has to be made to find 
            # the id of the inserted row.
            q1, q2 = sql_query
            self._db_execute(db_cursor, q1)
            self._db_execute(db_cursor, q2)
        else:
            self._db_execute(db_cursor, sql_query)

        try: 
            out = db_cursor.fetchone()[0]
            out = range(out-len(values)+1, out+1)        
        except Exception: 
            out = None

        if not self.ctx.transactions: 
            self.ctx.commit()
        return out

    
    def update(self, tables, where, vars=None, _test=False, **values): 
        """
        Update `tables` with clause `where` (interpolated using `vars`)
        and setting `values`.

            >>> db = DB(None, {})
            >>> name = 'Joseph'
            >>> q = db.update('foo', where='name = $name', name='bob', age=2,
            ...     created=SQLLiteral('NOW()'), vars=locals(), _test=True)
            >>> q
            <sql: "UPDATE foo SET age = 2, name = 'bob', created = NOW() WHERE name = 'Joseph'">
            >>> q.query()
            'UPDATE foo SET age = %s, name = %s, created = NOW() WHERE name = %s'
            >>> q.values()
            [2, 'bob', 'Joseph']
        """
        if vars is None: vars = {}
        where = self._where(where, vars)

        query = (
          "UPDATE " + sqllist(tables) + 
          " SET " + sqlwhere(values, ', ') + 
          " WHERE " + where)

        if _test: return query
        
        db_cursor = self._db_cursor()
        self._db_execute(db_cursor, query)
        if not self.ctx.transactions: 
            self.ctx.commit()
        return db_cursor.rowcount
    
    def delete(self, table, where, using=None, vars=None, _test=False): 
        """
        Deletes from `table` with clauses `where` and `using`.

            >>> db = DB(None, {})
            >>> name = 'Joe'
            >>> db.delete('foo', where='name = $name', vars=locals(), _test=True)
            <sql: "DELETE FROM foo WHERE name = 'Joe'">
        """
        if vars is None: vars = {}
        where = self._where(where, vars)

        q = 'DELETE FROM ' + table
        if where: q += ' WHERE ' + where
        if using: q += ' USING ' + sqllist(using)

        if _test: return q

        db_cursor = self._db_cursor()
        self._db_execute(db_cursor, q)
        if not self.ctx.transactions: 
            self.ctx.commit()
        return db_cursor.rowcount

    def _process_insert_query(self, query, tablename, seqname):
        return query

    def transaction(self): 
        """Start a transaction."""
        return Transaction(self.ctx)
    
class PostgresDB(DB): 
    """Postgres driver."""
    def __init__(self, **keywords):
        if 'pw' in keywords:
            keywords['password'] = keywords['pw']
            del keywords['pw']
            
        db_module = self.get_db_module()
        keywords['database'] = keywords.pop('db')
        self.dbname = "postgres"
        self.paramstyle = db_module.paramstyle
        DB.__init__(self, db_module, keywords)
        self.supports_multiple_insert = True
        
    def get_db_module(self):
        try: 
            import psycopg2 as db
            import psycopg2.extensions
            psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
        except ImportError: 
            try: 
                import psycopg as db
            except ImportError: 
                import pgdb as db
        return db

    def _process_insert_query(self, query, tablename, seqname):
        if seqname is None: 
            seqname = tablename + "_id_seq"
        return query + "; SELECT currval('%s')" % seqname

    def _connect(self, keywords):
        conn = DB._connect(self, keywords)
        conn.set_client_encoding('UTF8')
        return conn
        
    def _connect_with_pooling(self, keywords):
        conn = DB._connect_with_pooling(self, keywords)
        conn._con._con.set_client_encoding('UTF8')
        return conn

class MySQLDB(DB): 
    def __init__(self, **keywords):
        import MySQLdb as db
        if 'pw' in keywords:
            keywords['passwd'] = keywords['pw']
            del keywords['pw']

        if 'charset' not in keywords:
            keywords['charset'] = 'utf8'
        elif keywords['charset'] is None:
            del keywords['charset']

        self.paramstyle = db.paramstyle = 'pyformat' # it's both, like psycopg
        self.dbname = "mysql"
        DB.__init__(self, db, keywords)
        self.supports_multiple_insert = True
        
    def _process_insert_query(self, query, tablename, seqname):
        return query, SQLQuery('SELECT last_insert_id();')

class SqliteDB(DB): 
    def __init__(self, **keywords):
        try:
            import sqlite3 as db
            db.paramstyle = 'qmark'
        except ImportError:
            try:
                from pysqlite2 import dbapi2 as db
                db.paramstyle = 'qmark'
            except ImportError:
                import sqlite as db
        self.paramstyle = db.paramstyle
        keywords['database'] = keywords.pop('db')
        self.dbname = "sqlite"        
        DB.__init__(self, db, keywords)

    def _process_insert_query(self, query, tablename, seqname):
        return query, SQLQuery('SELECT last_insert_rowid();')
    
    def query(self, *a, **kw):
        out = DB.query(self, *a, **kw)
        if isinstance(out, iterbetter):
            # rowcount is not provided by sqlite
            del out.__len__
        return out

    # as with PostgresDB, the database is assumed to be in UTF-8.
    # This doesn't mean we turn byte-strings coming out of it into
    # Unicode objects, but we avoid trying to put Unicode objects into
    # it.
    encoding = 'UTF-8'

    def _py2sql(self, val):
        r"""
        Work around a couple of problems in SQLite that maybe pysqlite
        should take care of: give it True and False and it thinks
        they're column names; give it Unicode and it tries to insert
        it in, possibly, ASCII.

            >>> meth = SqliteDB(db='nonexistent')._py2sql
            >>> [meth(x) for x in [True, False, 1, 2, 'foo', u'souffl\xe9']]
            [1, 0, 1, 2, 'foo', 'souffl\xc3\xa9']

        """
        if val is True: return 1
        elif val is False: return 0
        elif isinstance(val, unicode): return val.encode(self.encoding)
        else: return val

class FirebirdDB(DB):
    """Firebird Database.
    """
    def __init__(self, **keywords):
        try:
            import kinterbasdb as db
        except Exception:
            db = None
            pass
        if 'pw' in keywords:
            keywords['passwd'] = keywords['pw']
            del keywords['pw']
        keywords['database'] = keywords['db']
        del keywords['db']
        DB.__init__(self, db, keywords)
        
    def delete(self, table, where=None, using=None, vars=None, _test=False):
        # firebird doesn't support using clause
        using=None
        return DB.delete(self, table, where, using, vars, _test)

    def sql_clauses(self, what, tables, where, group, order, limit, offset):
        return (
            ('SELECT', ''),
            ('FIRST', limit),
            ('SKIP', offset),
            ('', what),
            ('FROM', sqllist(tables)),
            ('WHERE', where),
            ('GROUP BY', group),
            ('ORDER BY', order)
        )

class MSSQLDB(DB):
    def __init__(self, **keywords):
        import pymssql as db    
        if 'pw' in keywords:
            keywords['password'] = keywords.pop('kw')
        keywords['database'] = keywords.pop('db')
        self.dbname = "mssql"
        DB.__init__(self, db, keywords)

class OracleDB(DB): 
    def __init__(self, **keywords): 
        import cx_Oracle as db 
        if 'pw' in keywords: 
            keywords['password'] = keywords.pop('pw') 

        #@@ TODO: use db.makedsn if host, port is specified 
        keywords['dsn'] = keywords.pop('db') 
        self.dbname = 'oracle' 
        db.paramstyle = 'numeric' 
        self.paramstyle = db.paramstyle

        # oracle doesn't support pooling 
        keywords.pop('pooling', None) 
        DB.__init__(self, db, keywords) 

    def _process_insert_query(self, query, tablename, seqname): 
        if seqname is None: 
            # It is not possible to get seq name from table name in Oracle
            return query
        else:
            return query + "; SELECT %s.currval FROM dual" % seqname 

_databases = {}
def database(dburl=None, **params):
    """Creates appropriate database using params.
    
    Pooling will be enabled if DBUtils module is available. 
    Pooling can be disabled by passing pooling=False in params.
    """
    dbn = params.pop('dbn')
    if dbn in _databases:
        return _databases[dbn](**params)
    else:
        raise UnknownDB, dbn

def register_database(name, clazz):
    """
    Register a database.

        >>> class LegacyDB(DB): 
        ...     def __init__(self, **params): 
        ...        pass 
        ...
        >>> register_database('legacy', LegacyDB)
        >>> db = database(dbn='legacy', db='test', user='joe', passwd='secret') 
    """
    _databases[name] = clazz

register_database('mysql', MySQLDB)
register_database('postgres', PostgresDB)
register_database('sqlite', SqliteDB)
register_database('firebird', FirebirdDB)
register_database('mssql', MSSQLDB)
register_database('oracle', OracleDB)

def _interpolate(format): 
    """
    Takes a format string and returns a list of 2-tuples of the form
    (boolean, string) where boolean says whether string should be evaled
    or not.

    from <http://lfw.org/python/Itpl.py> (public domain, Ka-Ping Yee)
    """
    from tokenize import tokenprog

    def matchorfail(text, pos):
        match = tokenprog.match(text, pos)
        if match is None:
            raise _ItplError(text, pos)
        return match, match.end()

    namechars = "abcdefghijklmnopqrstuvwxyz" \
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_";
    chunks = []
    pos = 0

    while 1:
        dollar = format.find("$", pos)
        if dollar < 0: 
            break
        nextchar = format[dollar + 1]

        if nextchar == "{":
            chunks.append((0, format[pos:dollar]))
            pos, level = dollar + 2, 1
            while level:
                match, pos = matchorfail(format, pos)
                tstart, tend = match.regs[3]
                token = format[tstart:tend]
                if token == "{": 
                    level = level + 1
                elif token == "}":  
                    level = level - 1
            chunks.append((1, format[dollar + 2:pos - 1]))

        elif nextchar in namechars:
            chunks.append((0, format[pos:dollar]))
            match, pos = matchorfail(format, dollar + 1)
            while pos < len(format):
                if format[pos] == "." and \
                    pos + 1 < len(format) and format[pos + 1] in namechars:
                    match, pos = matchorfail(format, pos + 1)
                elif format[pos] in "([":
                    pos, level = pos + 1, 1
                    while level:
                        match, pos = matchorfail(format, pos)
                        tstart, tend = match.regs[3]
                        token = format[tstart:tend]
                        if token[0] in "([": 
                            level = level + 1
                        elif token[0] in ")]":  
                            level = level - 1
                else: 
                    break
            chunks.append((1, format[dollar + 1:pos]))
        else:
            chunks.append((0, format[pos:dollar + 1]))
            pos = dollar + 1 + (nextchar == "$")

    if pos < len(format): 
        chunks.append((0, format[pos:]))
    return chunks

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = debugerror
"""
pretty debug errors
(part of web.py)

portions adapted from Django <djangoproject.com> 
Copyright (c) 2005, the Lawrence Journal-World
Used under the modified BSD license:
http://www.xfree86.org/3.3.6/COPYRIGHT2.html#5
"""

__all__ = ["debugerror", "djangoerror", "emailerrors"]

import sys, urlparse, pprint, traceback
from net import websafe
from template import Template
from utils import sendmail
import webapi as web

import os, os.path
whereami = os.path.join(os.getcwd(), __file__)
whereami = os.path.sep.join(whereami.split(os.path.sep)[:-1])
djangoerror_t = """\
$def with (exception_type, exception_value, frames)
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html lang="en">
<head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8" />
  <meta name="robots" content="NONE,NOARCHIVE" />
  <title>$exception_type at $ctx.path</title>
  <style type="text/css">
    html * { padding:0; margin:0; }
    body * { padding:10px 20px; }
    body * * { padding:0; }
    body { font:small sans-serif; }
    body>div { border-bottom:1px solid #ddd; }
    h1 { font-weight:normal; }
    h2 { margin-bottom:.8em; }
    h2 span { font-size:80%; color:#666; font-weight:normal; }
    h3 { margin:1em 0 .5em 0; }
    h4 { margin:0 0 .5em 0; font-weight: normal; }
    table { 
        border:1px solid #ccc; border-collapse: collapse; background:white; }
    tbody td, tbody th { vertical-align:top; padding:2px 3px; }
    thead th { 
        padding:1px 6px 1px 3px; background:#fefefe; text-align:left; 
        font-weight:normal; font-size:11px; border:1px solid #ddd; }
    tbody th { text-align:right; color:#666; padding-right:.5em; }
    table.vars { margin:5px 0 2px 40px; }
    table.vars td, table.req td { font-family:monospace; }
    table td.code { width:100%;}
    table td.code div { overflow:hidden; }
    table.source th { color:#666; }
    table.source td { 
        font-family:monospace; white-space:pre; border-bottom:1px solid #eee; }
    ul.traceback { list-style-type:none; }
    ul.traceback li.frame { margin-bottom:1em; }
    div.context { margin: 10px 0; }
    div.context ol { 
        padding-left:30px; margin:0 10px; list-style-position: inside; }
    div.context ol li { 
        font-family:monospace; white-space:pre; color:#666; cursor:pointer; }
    div.context ol.context-line li { color:black; background-color:#ccc; }
    div.context ol.context-line li span { float: right; }
    div.commands { margin-left: 40px; }
    div.commands a { color:black; text-decoration:none; }
    #summary { background: #ffc; }
    #summary h2 { font-weight: normal; color: #666; }
    #explanation { background:#eee; }
    #template, #template-not-exist { background:#f6f6f6; }
    #template-not-exist ul { margin: 0 0 0 20px; }
    #traceback { background:#eee; }
    #requestinfo { background:#f6f6f6; padding-left:120px; }
    #summary table { border:none; background:transparent; }
    #requestinfo h2, #requestinfo h3 { position:relative; margin-left:-100px; }
    #requestinfo h3 { margin-bottom:-1em; }
    .error { background: #ffc; }
    .specific { color:#cc3300; font-weight:bold; }
  </style>
  <script type="text/javascript">
  //<!--
    function getElementsByClassName(oElm, strTagName, strClassName){
        // Written by Jonathan Snook, http://www.snook.ca/jon; 
        // Add-ons by Robert Nyman, http://www.robertnyman.com
        var arrElements = (strTagName == "*" && document.all)? document.all :
        oElm.getElementsByTagName(strTagName);
        var arrReturnElements = new Array();
        strClassName = strClassName.replace(/\-/g, "\\-");
        var oRegExp = new RegExp("(^|\\s)" + strClassName + "(\\s|$$)");
        var oElement;
        for(var i=0; i<arrElements.length; i++){
            oElement = arrElements[i];
            if(oRegExp.test(oElement.className)){
                arrReturnElements.push(oElement);
            }
        }
        return (arrReturnElements)
    }
    function hideAll(elems) {
      for (var e = 0; e < elems.length; e++) {
        elems[e].style.display = 'none';
      }
    }
    window.onload = function() {
      hideAll(getElementsByClassName(document, 'table', 'vars'));
      hideAll(getElementsByClassName(document, 'ol', 'pre-context'));
      hideAll(getElementsByClassName(document, 'ol', 'post-context'));
    }
    function toggle() {
      for (var i = 0; i < arguments.length; i++) {
        var e = document.getElementById(arguments[i]);
        if (e) {
          e.style.display = e.style.display == 'none' ? 'block' : 'none';
        }
      }
      return false;
    }
    function varToggle(link, id) {
      toggle('v' + id);
      var s = link.getElementsByTagName('span')[0];
      var uarr = String.fromCharCode(0x25b6);
      var darr = String.fromCharCode(0x25bc);
      s.innerHTML = s.innerHTML == uarr ? darr : uarr;
      return false;
    }
    //-->
  </script>
</head>
<body>

$def dicttable (d, kls='req', id=None):
    $ items = d and d.items() or []
    $items.sort()
    $:dicttable_items(items, kls, id)
        
$def dicttable_items(items, kls='req', id=None):
    $if items:
        <table class="$kls"
        $if id: id="$id"
        ><thead><tr><th>Variable</th><th>Value</th></tr></thead>
        <tbody>
        $for k, v in items:
            <tr><td>$k</td><td class="code"><div>$prettify(v)</div></td></tr>
        </tbody>
        </table>
    $else:
        <p>No data.</p>

<div id="summary">
  <h1>$exception_type at $ctx.path</h1>
  <h2>$exception_value</h2>
  <table><tr>
    <th>Python</th>
    <td>$frames[0].filename in $frames[0].function, line $frames[0].lineno</td>
  </tr><tr>
    <th>Web</th>
    <td>$ctx.method $ctx.home$ctx.path</td>
  </tr></table>
</div>
<div id="traceback">
<h2>Traceback <span>(innermost first)</span></h2>
<ul class="traceback">
$for frame in frames:
    <li class="frame">
    <code>$frame.filename</code> in <code>$frame.function</code>
    $if frame.context_line:
        <div class="context" id="c$frame.id">
        $if frame.pre_context:
            <ol start="$frame.pre_context_lineno" class="pre-context" id="pre$frame.id">
            $for line in frame.pre_context:
                <li onclick="toggle('pre$frame.id', 'post$frame.id')">$line</li>
            </ol>
            <ol start="$frame.lineno" class="context-line"><li onclick="toggle('pre$frame.id', 'post$frame.id')">$frame.context_line <span>...</span></li></ol>
        $if frame.post_context:
            <ol start='${frame.lineno + 1}' class="post-context" id="post$frame.id">
            $for line in frame.post_context:
                <li onclick="toggle('pre$frame.id', 'post$frame.id')">$line</li>
            </ol>
      </div>
    
    $if frame.vars:
        <div class="commands">
        <a href='#' onclick="return varToggle(this, '$frame.id')"><span>&#x25b6;</span> Local vars</a>
        $# $inspect.formatargvalues(*inspect.getargvalues(frame['tb'].tb_frame))
        </div>
        $:dicttable(frame.vars, kls='vars', id=('v' + str(frame.id)))
      </li>
  </ul>
</div>

<div id="requestinfo">
$if ctx.output or ctx.headers:
    <h2>Response so far</h2>
    <h3>HEADERS</h3>
    $:dicttable_items(ctx.headers)

    <h3>BODY</h3>
    <p class="req" style="padding-bottom: 2em"><code>
    $ctx.output
    </code></p>
  
<h2>Request information</h2>

<h3>INPUT</h3>
$:dicttable(web.input())

<h3 id="cookie-info">COOKIES</h3>
$:dicttable(web.cookies())

<h3 id="meta-info">META</h3>
$ newctx = [(k, v) for (k, v) in ctx.iteritems() if not k.startswith('_') and not isinstance(v, dict)]
$:dicttable(dict(newctx))

<h3 id="meta-info">ENVIRONMENT</h3>
$:dicttable(ctx.env)
</div>

<div id="explanation">
  <p>
    You're seeing this error because you have <code>web.config.debug</code>
    set to <code>True</code>. Set that to <code>False</code> if you don't to see this.
  </p>
</div>

</body>
</html>
"""

djangoerror_r = None

def djangoerror():
    def _get_lines_from_file(filename, lineno, context_lines):
        """
        Returns context_lines before and after lineno from file.
        Returns (pre_context_lineno, pre_context, context_line, post_context).
        """
        try:
            source = open(filename).readlines()
            lower_bound = max(0, lineno - context_lines)
            upper_bound = lineno + context_lines

            pre_context = \
                [line.strip('\n') for line in source[lower_bound:lineno]]
            context_line = source[lineno].strip('\n')
            post_context = \
                [line.strip('\n') for line in source[lineno + 1:upper_bound]]

            return lower_bound, pre_context, context_line, post_context
        except (OSError, IOError):
            return None, [], None, []    
    
    exception_type, exception_value, tback = sys.exc_info()
    frames = []
    while tback is not None:
        filename = tback.tb_frame.f_code.co_filename
        function = tback.tb_frame.f_code.co_name
        lineno = tback.tb_lineno - 1
        pre_context_lineno, pre_context, context_line, post_context = \
            _get_lines_from_file(filename, lineno, 7)
        frames.append(web.storage({
            'tback': tback,
            'filename': filename,
            'function': function,
            'lineno': lineno,
            'vars': tback.tb_frame.f_locals,
            'id': id(tback),
            'pre_context': pre_context,
            'context_line': context_line,
            'post_context': post_context,
            'pre_context_lineno': pre_context_lineno,
        }))
        tback = tback.tb_next
    frames.reverse()
    urljoin = urlparse.urljoin
    def prettify(x):
        try: 
            out = pprint.pformat(x)
        except Exception, e: 
            out = '[could not display: <' + e.__class__.__name__ + \
                  ': '+str(e)+'>]'
        return out
        
    global djangoerror_r
    if djangoerror_r is None:
        djangoerror_r = Template(djangoerror_t, filename=__file__, filter=websafe)
        
    t = djangoerror_r
    globals = {'ctx': web.ctx, 'web':web, 'dict':dict, 'str':str, 'prettify': prettify}
    t.t.func_globals.update(globals)
    return t(exception_type, exception_value, frames)

def debugerror():
    """
    A replacement for `internalerror` that presents a nice page with lots
    of debug information for the programmer.

    (Based on the beautiful 500 page from [Django](http://djangoproject.com/), 
    designed by [Wilson Miner](http://wilsonminer.com/).)
    """
    return web._InternalError(djangoerror())

def emailerrors(email_address, olderror):
    """
    Wraps the old `internalerror` handler (pass as `olderror`) to 
    additionally email all errors to `email_address`, to aid in 
    debugging production websites.
    
    Emails contain a normal text traceback as well as an
    attachment containing the nice `debugerror` page.
    """
    def emailerrors_internal():
        error = olderror()
        tb = sys.exc_info()
        error_name = tb[0]
        error_value = tb[1]
        tb_txt = ''.join(traceback.format_exception(*tb))
        path = web.ctx.path
        request = web.ctx.method+' '+web.ctx.home+web.ctx.fullpath
        eaddr = email_address
        text = ("""\
------here----
Content-Type: text/plain
Content-Disposition: inline

%(request)s

%(tb_txt)s

------here----
Content-Type: text/html; name="bug.html"
Content-Disposition: attachment; filename="bug.html"

""" % locals()) + str(djangoerror())
        sendmail(
          "your buggy site <%s>" % eaddr,
          "the bugfixer <%s>" % eaddr,
          "bug: %(error_name)s: %(error_value)s (%(path)s)" % locals(),
          text, 
          headers={'Content-Type': 'multipart/mixed; boundary="----here----"'})
        return error
    
    return emailerrors_internal

if __name__ == "__main__":
    urls = (
        '/', 'index'
    )
    from application import application
    app = application(urls, globals())
    app.internalerror = debugerror
    
    class index:
        def GET(self):
            thisdoesnotexist

    app.run()

########NEW FILE########
__FILENAME__ = form
"""
HTML forms
(part of web.py)
"""

import copy, re
import webapi as web
import utils, net

def attrget(obj, attr, value=None):
    if hasattr(obj, 'has_key') and obj.has_key(attr): return obj[attr]
    if hasattr(obj, attr): return getattr(obj, attr)
    return value

class Form:
    r"""
    HTML form.
    
        >>> f = Form(Textbox("x"))
        >>> f.render()
        '<table>\n    <tr><th><label for="x">x</label></th><td><input type="text" name="x" id="x" /></td></tr>\n</table>'
    """
    def __init__(self, *inputs, **kw):
        self.inputs = inputs
        self.valid = True
        self.note = None
        self.validators = kw.pop('validators', [])

    def __call__(self, x=None):
        o = copy.deepcopy(self)
        if x: o.validates(x)
        return o
    
    def render(self):
        out = ''
        out += self.rendernote(self.note)
        out += '<table>\n'
        for i in self.inputs:
            out += '    <tr><th><label for="%s">%s</label></th>' % (i.id, net.websafe(i.description))
            out += "<td>"+i.pre+i.render()+i.post+"</td></tr>\n"
        out += "</table>"
        return out
        
    def render_css(self): 
        out = [] 
        out.append(self.rendernote(self.note)) 
        for i in self.inputs: 
            out.append('<label for="%s">%s</label>' % (i.id, net.websafe(i.description))) 
            out.append(i.pre) 
            out.append(i.render()) 
            out.append(i.post) 
            out.append('\n') 
        return ''.join(out) 
        
    def rendernote(self, note):
        if note: return '<strong class="wrong">%s</strong>' % net.websafe(note)
        else: return ""
    
    def validates(self, source=None, _validate=True, **kw):
        source = source or kw or web.input()
        out = True
        for i in self.inputs:
            v = attrget(source, i.name)
            if _validate:
                out = i.validate(v) and out
            else:
                i.value = v
        if _validate:
            out = out and self._validate(source)
            self.valid = out
        return out

    def _validate(self, value):
        self.value = value
        for v in self.validators:
            if not v.valid(value):
                self.note = v.msg
                return False
        return True

    def fill(self, source=None, **kw):
        return self.validates(source, _validate=False, **kw)
    
    def __getitem__(self, i):
        for x in self.inputs:
            if x.name == i: return x
        raise KeyError, i

    def __getattr__(self, name):
        # don't interfere with deepcopy
        inputs = self.__dict__.get('inputs') or []
        for x in inputs:
            if x.name == name: return x
        raise AttributeError, name
    
    def get(self, i, default=None):
        try:
            return self[i]
        except KeyError:
            return default
            
    def _get_d(self): #@@ should really be form.attr, no?
        return utils.storage([(i.name, i.value) for i in self.inputs])
    d = property(_get_d)

class Input(object):
    def __init__(self, name, *validators, **attrs):
        self.description = attrs.pop('description', name)
        self.value = attrs.pop('value', None)
        self.pre = attrs.pop('pre', "")
        self.post = attrs.pop('post', "")
        self.id = attrs.setdefault('id', name)
        if 'class_' in attrs:
            attrs['class'] = attrs['class_']
            del attrs['class_']
        self.name, self.validators, self.attrs, self.note = name, validators, attrs, None

    def validate(self, value):
        self.value = value
        for v in self.validators:
            if not v.valid(value):
                self.note = v.msg
                return False
        return True

    def render(self): raise NotImplementedError

    def rendernote(self, note):
        if note: return '<strong class="wrong">%s</strong>' % net.websafe(note)
        else: return ""
        
    def addatts(self):
        str = ""
        for (n, v) in self.attrs.items():
            str += ' %s="%s"' % (n, net.websafe(v))
        return str
    
#@@ quoting

class Textbox(Input):
    def render(self, shownote=True):
        x = '<input type="text" name="%s"' % net.websafe(self.name)
        if self.value: x += ' value="%s"' % net.websafe(self.value)
        x += self.addatts()
        x += ' />'
        if shownote:
            x += self.rendernote(self.note)
        return x

class Password(Input):
    def render(self):
        x = '<input type="password" name="%s"' % net.websafe(self.name)
        if self.value: x += ' value="%s"' % net.websafe(self.value)
        x += self.addatts()
        x += ' />'
        x += self.rendernote(self.note)
        return x

class Textarea(Input):
    def render(self):
        x = '<textarea name="%s"' % net.websafe(self.name)
        x += self.addatts()
        x += '>'
        if self.value is not None: x += net.websafe(self.value)
        x += '</textarea>'
        x += self.rendernote(self.note)
        return x

class Dropdown(Input):
    def __init__(self, name, args, *validators, **attrs):
        self.args = args
        super(Dropdown, self).__init__(name, *validators, **attrs)

    def render(self):
        x = '<select name="%s"%s>\n' % (net.websafe(self.name), self.addatts())
        for arg in self.args:
            if type(arg) == tuple:
                value, desc= arg
            else:
                value, desc = arg, arg 

            if self.value == value: select_p = ' selected="selected"'
            else: select_p = ''
            x += '  <option %s value="%s">%s</option>\n' % (select_p, net.websafe(value), net.websafe(desc))
        x += '</select>\n'
        x += self.rendernote(self.note)
        return x

class Radio(Input):
    def __init__(self, name, args, *validators, **attrs):
        self.args = args
        super(Radio, self).__init__(name, *validators, **attrs)

    def render(self):
        x = '<span>'
        for arg in self.args:
            if self.value == arg: select_p = ' checked="checked"'
            else: select_p = ''
            x += '<input type="radio" name="%s" value="%s"%s%s /> %s ' % (net.websafe(self.name), net.websafe(arg), select_p, self.addatts(), net.websafe(arg))
            x += '</span>'
            x += self.rendernote(self.note)    
        return x

class Checkbox(Input):
    def render(self):
        x = '<input name="%s" type="checkbox"' % net.websafe(self.name)
        if self.value: x += ' checked="checked"'
        x += self.addatts()
        x += ' />'
        x += self.rendernote(self.note)
        return x

class Button(Input):
    def __init__(self, name, *validators, **attrs):
        super(Button, self).__init__(name, *validators, **attrs)
        self.description = ""

    def render(self):
        safename = net.websafe(self.name)
        x = '<button name="%s"%s>%s</button>' % (safename, self.addatts(), safename)
        x += self.rendernote(self.note)
        return x

class Hidden(Input):
    def __init__(self, name, *validators, **attrs):
        super(Hidden, self).__init__(name, *validators, **attrs)
        # it doesnt make sence for a hidden field to have description
        self.description = ""

    def render(self):
        x = '<input type="hidden" name="%s"' % net.websafe(self.name)
        if self.value: x += ' value="%s"' % net.websafe(self.value)
        x += self.addatts()
        x += ' />'
        return x

class File(Input):
    def render(self):
        x = '<input type="file" name="%s"' % net.websafe(self.name)
        x += self.addatts()
        x += ' />'
        x += self.rendernote(self.note)
        return x
    
class Validator:
    def __deepcopy__(self, memo): return copy.copy(self)
    def __init__(self, msg, test, jstest=None): utils.autoassign(self, locals())
    def valid(self, value): 
        try: return self.test(value)
        except: return False

notnull = Validator("Required", bool)

class regexp(Validator):
    def __init__(self, rexp, msg):
        self.rexp = re.compile(rexp)
        self.msg = msg
    
    def valid(self, value):
        return bool(self.rexp.match(value))

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = http
"""
HTTP Utilities
(from web.py)
"""

__all__ = [
  "expires", "lastmodified", 
  "prefixurl", "modified", 
  "write",
  "changequery", "url",
  "profiler",
]

import sys, os, threading, urllib, urlparse
try: import datetime
except ImportError: pass
import net, utils, webapi as web

def prefixurl(base=''):
    """
    Sorry, this function is really difficult to explain.
    Maybe some other time.
    """
    url = web.ctx.path.lstrip('/')
    for i in xrange(url.count('/')): 
        base += '../'
    if not base: 
        base = './'
    return base

def expires(delta):
    """
    Outputs an `Expires` header for `delta` from now. 
    `delta` is a `timedelta` object or a number of seconds.
    """
    if isinstance(delta, (int, long)):
        delta = datetime.timedelta(seconds=delta)
    date_obj = datetime.datetime.utcnow() + delta
    web.header('Expires', net.httpdate(date_obj))

def lastmodified(date_obj):
    """Outputs a `Last-Modified` header for `datetime`."""
    web.header('Last-Modified', net.httpdate(date_obj))

def modified(date=None, etag=None):
    n = set(x.strip('" ') for x in web.ctx.env.get('HTTP_IF_NONE_MATCH', '').split(','))
    m = net.parsehttpdate(web.ctx.env.get('HTTP_IF_MODIFIED_SINCE', '').split(';')[0])
    validate = False
    if etag:
        if '*' in n or etag in n:
            validate = True
    if date and m:
        # we subtract a second because 
        # HTTP dates don't have sub-second precision
        if date-datetime.timedelta(seconds=1) <= m:
            validate = True

    if validate: web.ctx.status = '304 Not Modified'
    return not validate

def write(cgi_response):
    """
    Converts a standard CGI-style string response into `header` and 
    `output` calls.
    """
    cgi_response = str(cgi_response)
    cgi_response.replace('\r\n', '\n')
    head, body = cgi_response.split('\n\n', 1)
    lines = head.split('\n')

    for line in lines:
        if line.isspace(): 
            continue
        hdr, value = line.split(":", 1)
        value = value.strip()
        if hdr.lower() == "status": 
            web.ctx.status = value
        else: 
            web.header(hdr, value)

    web.output(body)

def urlencode(query):
    """
    Same as urllib.urlencode, but supports unicode strings.
    
        >>> urlencode({'text':'foo bar'})
        'text=foo+bar'
    """
    query = dict([(k, utils.utf8(v)) for k, v in query.items()])
    return urllib.urlencode(query)

def changequery(query=None, **kw):
    """
    Imagine you're at `/foo?a=1&b=2`. Then `changequery(a=3)` will return
    `/foo?a=3&b=2` -- the same URL but with the arguments you requested
    changed.
    """
    if query is None:
        query = web.input(_method='get')
    for k, v in kw.iteritems():
        if v is None:
            query.pop(k, None)
        else:
            query[k] = v
    out = web.ctx.path
    if query:
        out += '?' + urlencode(query)
    return out

def url(path=None, **kw):
    """
    Makes url by concatinating web.ctx.homepath and path and the 
    query string created using the arguments.
    """
    if path is None:
        path = web.ctx.path
    if path.startswith("/"):
        out = web.ctx.homepath + path
    else:
        out = path

    if kw:
        out += '?' + urlencode(kw)
    
    return out

def profiler(app):
    """Outputs basic profiling information at the bottom of each response."""
    from utils import profile
    def profile_internal(e, o):
        out, result = profile(app)(e, o)
        return out + ['<pre>' + net.websafe(result) + '</pre>']
    return profile_internal

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = httpserver
__all__ = ["runsimple"]

import sys, os
import webapi as web
import net
import utils

def runbasic(func, server_address=("0.0.0.0", 8080)):
    """
    Runs a simple HTTP server hosting WSGI app `func`. The directory `static/` 
    is hosted statically.

    Based on [WsgiServer][ws] from [Colin Stewart][cs].
    
  [ws]: http://www.owlfish.com/software/wsgiutils/documentation/wsgi-server-api.html
  [cs]: http://www.owlfish.com/
    """
    # Copyright (c) 2004 Colin Stewart (http://www.owlfish.com/)
    # Modified somewhat for simplicity
    # Used under the modified BSD license:
    # http://www.xfree86.org/3.3.6/COPYRIGHT2.html#5

    import SimpleHTTPServer, SocketServer, BaseHTTPServer, urlparse
    import socket, errno
    import traceback

    class WSGIHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
        def run_wsgi_app(self):
            protocol, host, path, parameters, query, fragment = \
                urlparse.urlparse('http://dummyhost%s' % self.path)

            # we only use path, query
            env = {'wsgi.version': (1, 0)
                   ,'wsgi.url_scheme': 'http'
                   ,'wsgi.input': self.rfile
                   ,'wsgi.errors': sys.stderr
                   ,'wsgi.multithread': 1
                   ,'wsgi.multiprocess': 0
                   ,'wsgi.run_once': 0
                   ,'REQUEST_METHOD': self.command
                   ,'REQUEST_URI': self.path
                   ,'PATH_INFO': path
                   ,'QUERY_STRING': query
                   ,'CONTENT_TYPE': self.headers.get('Content-Type', '')
                   ,'CONTENT_LENGTH': self.headers.get('Content-Length', '')
                   ,'REMOTE_ADDR': self.client_address[0]
                   ,'SERVER_NAME': self.server.server_address[0]
                   ,'SERVER_PORT': str(self.server.server_address[1])
                   ,'SERVER_PROTOCOL': self.request_version
                   }

            for http_header, http_value in self.headers.items():
                env ['HTTP_%s' % http_header.replace('-', '_').upper()] = \
                    http_value

            # Setup the state
            self.wsgi_sent_headers = 0
            self.wsgi_headers = []

            try:
                # We have there environment, now invoke the application
                result = self.server.app(env, self.wsgi_start_response)
                try:
                    try:
                        for data in result:
                            if data: 
                                self.wsgi_write_data(data)
                    finally:
                        if hasattr(result, 'close'): 
                            result.close()
                except socket.error, socket_err:
                    # Catch common network errors and suppress them
                    if (socket_err.args[0] in \
                       (errno.ECONNABORTED, errno.EPIPE)): 
                        return
                except socket.timeout, socket_timeout: 
                    return
            except:
                print >> web.debug, traceback.format_exc(),

            if (not self.wsgi_sent_headers):
                # We must write out something!
                self.wsgi_write_data(" ")
            return

        do_POST = run_wsgi_app
        do_PUT = run_wsgi_app
        do_DELETE = run_wsgi_app

        def do_GET(self):
            if self.path.startswith('/static/'):
                SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)
            else:
                self.run_wsgi_app()

        def wsgi_start_response(self, response_status, response_headers, 
                              exc_info=None):
            if (self.wsgi_sent_headers):
                raise Exception \
                      ("Headers already sent and start_response called again!")
            # Should really take a copy to avoid changes in the application....
            self.wsgi_headers = (response_status, response_headers)
            return self.wsgi_write_data

        def wsgi_write_data(self, data):
            if (not self.wsgi_sent_headers):
                status, headers = self.wsgi_headers
                # Need to send header prior to data
                status_code = status[:status.find(' ')]
                status_msg = status[status.find(' ') + 1:]
                self.send_response(int(status_code), status_msg)
                for header, value in headers:
                    self.send_header(header, value)
                self.end_headers()
                self.wsgi_sent_headers = 1
            # Send the data
            self.wfile.write(data)

    class WSGIServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
        def __init__(self, func, server_address):
            BaseHTTPServer.HTTPServer.__init__(self, 
                                               server_address, 
                                               WSGIHandler)
            self.app = func
            self.serverShuttingDown = 0

    print "http://%s:%d/" % server_address
    WSGIServer(func, server_address).serve_forever()

def runsimple(func, server_address=("0.0.0.0", 8080)):
    """
    Runs [CherryPy][cp] WSGI server hosting WSGI app `func`. 
    The directory `static/` is hosted statically.

    [cp]: http://www.cherrypy.org
    """
    from wsgiserver import CherryPyWSGIServer
    from SimpleHTTPServer import SimpleHTTPRequestHandler
    from BaseHTTPServer import BaseHTTPRequestHandler

    class StaticApp(SimpleHTTPRequestHandler):
        """WSGI application for serving static files."""
        def __init__(self, environ, start_response):
            self.headers = []
            self.environ = environ
            self.start_response = start_response

        def send_response(self, status, msg=""):
            self.status = str(status) + " " + msg

        def send_header(self, name, value):
            self.headers.append((name, value))

        def end_headers(self):
            pass

        def log_message(*a): pass

        def __iter__(self):
            environ = self.environ

            self.path = environ.get('PATH_INFO', '')
            self.client_address = environ.get('REMOTE_ADDR','-'), \
                                  environ.get('REMOTE_PORT','-')
            self.command = environ.get('REQUEST_METHOD', '-')

            from cStringIO import StringIO
            self.wfile = StringIO() # for capturing error

            f = self.send_head()
            self.start_response(self.status, self.headers)

            if f:
                block_size = 16 * 1024
                while True:
                    buf = f.read(block_size)
                    if not buf:
                        break
                    yield buf
                f.close()
            else:
                value = self.wfile.getvalue()
                yield value
                    
    class WSGIWrapper(BaseHTTPRequestHandler):
        """WSGI wrapper for logging the status and serving static files."""
        def __init__(self, app):
            self.app = app
            self.format = '%s - - [%s] "%s %s %s" - %s'

        def __call__(self, environ, start_response):
            def xstart_response(status, response_headers, *args):
                write = start_response(status, response_headers, *args)
                self.log(status, environ)
                return write

            path = environ.get('PATH_INFO', '')
            if path.startswith('/static/'):
                return StaticApp(environ, xstart_response)
            else:
                return self.app(environ, xstart_response)

        def log(self, status, environ):
            outfile = environ.get('wsgi.errors', web.debug)
            req = environ.get('PATH_INFO', '_')
            protocol = environ.get('ACTUAL_SERVER_PROTOCOL', '-')
            method = environ.get('REQUEST_METHOD', '-')
            host = "%s:%s" % (environ.get('REMOTE_ADDR','-'), 
                              environ.get('REMOTE_PORT','-'))

            #@@ It is really bad to extend from 
            #@@ BaseHTTPRequestHandler just for this method
            time = self.log_date_time_string()

            msg = self.format % (host, time, protocol, method, req, status)
            print >> outfile, utils.safestr(msg)
            
    func = WSGIWrapper(func)
    server = CherryPyWSGIServer(server_address, func, server_name="localhost")

    print "http://%s:%d/" % server_address
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()

########NEW FILE########
__FILENAME__ = net
"""
Network Utilities
(from web.py)
"""

__all__ = [
  "validipaddr", "validipport", "validip", "validaddr", 
  "urlquote",
  "httpdate", "parsehttpdate", 
  "htmlquote", "htmlunquote", "websafe",
]

import urllib, time
try: import datetime
except ImportError: pass

def validipaddr(address):
    """
    Returns True if `address` is a valid IPv4 address.
    
        >>> validipaddr('192.168.1.1')
        True
        >>> validipaddr('192.168.1.800')
        False
        >>> validipaddr('192.168.1')
        False
    """
    try:
        octets = address.split('.')
        if len(octets) != 4:
            return False
        for x in octets:
            if not (0 <= int(x) <= 255):
                return False
    except ValueError:
        return False
    return True

def validipport(port):
    """
    Returns True if `port` is a valid IPv4 port.
    
        >>> validipport('9000')
        True
        >>> validipport('foo')
        False
        >>> validipport('1000000')
        False
    """
    try:
        if not (0 <= int(port) <= 65535):
            return False
    except ValueError:
        return False
    return True

def validip(ip, defaultaddr="0.0.0.0", defaultport=8080):
    """Returns `(ip_address, port)` from string `ip_addr_port`"""
    addr = defaultaddr
    port = defaultport
    
    ip = ip.split(":", 1)
    if len(ip) == 1:
        if not ip[0]:
            pass
        elif validipaddr(ip[0]):
            addr = ip[0]
        elif validipport(ip[0]):
            port = int(ip[0])
        else:
            raise ValueError, ':'.join(ip) + ' is not a valid IP address/port'
    elif len(ip) == 2:
        addr, port = ip
        if not validipaddr(addr) and validipport(port):
            raise ValueError, ':'.join(ip) + ' is not a valid IP address/port'
        port = int(port)
    else:
        raise ValueError, ':'.join(ip) + ' is not a valid IP address/port'
    return (addr, port)

def validaddr(string_):
    """
    Returns either (ip_address, port) or "/path/to/socket" from string_
    
        >>> validaddr('/path/to/socket')
        '/path/to/socket'
        >>> validaddr('8000')
        ('0.0.0.0', 8000)
        >>> validaddr('127.0.0.1')
        ('127.0.0.1', 8080)
        >>> validaddr('127.0.0.1:8000')
        ('127.0.0.1', 8000)
        >>> validaddr('fff')
        Traceback (most recent call last):
            ...
        ValueError: fff is not a valid IP address/port
    """
    if '/' in string_:
        return string_
    else:
        return validip(string_)

def urlquote(val):
    """
    Quotes a string for use in a URL.
    
        >>> urlquote('://?f=1&j=1')
        '%3A//%3Ff%3D1%26j%3D1'
        >>> urlquote(None)
        ''
        >>> urlquote(u'\u203d')
        '%E2%80%BD'
    """
    if val is None: return ''
    if not isinstance(val, unicode): val = str(val)
    else: val = val.encode('utf-8')
    return urllib.quote(val)

def httpdate(date_obj):
    """
    Formats a datetime object for use in HTTP headers.
    
        >>> import datetime
        >>> httpdate(datetime.datetime(1970, 1, 1, 1, 1, 1))
        'Thu, 01 Jan 1970 01:01:01 GMT'
    """
    return date_obj.strftime("%a, %d %b %Y %H:%M:%S GMT")

def parsehttpdate(string_):
    """
    Parses an HTTP date into a datetime object.

        >>> parsehttpdate('Thu, 01 Jan 1970 01:01:01 GMT')
        datetime.datetime(1970, 1, 1, 1, 1, 1)
    """
    try:
        t = time.strptime(string_, "%a, %d %b %Y %H:%M:%S %Z")
    except ValueError:
        return None
    return datetime.datetime(*t[:6])

def htmlquote(text):
    """
    Encodes `text` for raw use in HTML.
    
        >>> htmlquote("<'&\\">")
        '&lt;&#39;&amp;&quot;&gt;'
    """
    text = text.replace("&", "&amp;") # Must be done first!
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace("'", "&#39;")
    text = text.replace('"', "&quot;")
    return text

def htmlunquote(text):
    """
    Decodes `text` that's HTML quoted.

        >>> htmlunquote('&lt;&#39;&amp;&quot;&gt;')
        '<\\'&">'
    """
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    text = text.replace("&gt;", ">")
    text = text.replace("&lt;", "<")
    text = text.replace("&amp;", "&") # Must be done last!
    return text

def websafe(val):
    """
    Converts `val` so that it's safe for use in UTF-8 HTML.
    
        >>> websafe("<'&\\">")
        '&lt;&#39;&amp;&quot;&gt;'
        >>> websafe(None)
        ''
        >>> websafe(u'\u203d')
        '\\xe2\\x80\\xbd'
    """
    if val is None:
        return ''
    if isinstance(val, unicode):
        val = val.encode('utf-8')
    val = str(val)
    return htmlquote(val)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = session
"""
Session Management
(from web.py)
"""

import os, time, datetime, random, base64
try:
    import cPickle as pickle
except ImportError:
    import pickle
try:
    import hashlib
    sha1 = hashlib.sha1
except ImportError:
    import sha
    sha1 = sha.new

import utils
import webapi as web

__all__ = [
    'Session', 'SessionExpired',
    'Store', 'DiskStore', 'DBStore',
]

web.config.session_parameters = utils.storage({
    'cookie_name': 'webpy_session_id',
    'cookie_domain': None,
    'timeout': 86400, #24 * 60 * 60, # 24 hours in seconds
    'ignore_expiry': True,
    'ignore_change_ip': True,
    'secret_key': 'fLjUfxqXtfNoIldA0A0J',
    'expired_message': 'Session expired',
})

class SessionExpired(web.HTTPError): 
    def __init__(self, message):
        web.HTTPError.__init__(self, '200 OK', {}, data=message)

class Session(utils.ThreadedDict):
    """Session management for web.py
    """

    def __init__(self, app, store, initializer=None):
        self.__dict__['store'] = store
        self.__dict__['_initializer'] = initializer
        self.__dict__['_last_cleanup_time'] = 0
        self.__dict__['_config'] = utils.storage(web.config.session_parameters)

        if app:
            app.add_processor(self._processor)

    def _processor(self, handler):
        """Application processor to setup session for every request"""
        self._cleanup()
        self._load()

        try:
            return handler()
        finally:
            self._save()

    def _load(self):
        """Load the session from the store, by the id from cookie"""
        cookie_name = self._config.cookie_name
        cookie_domain = self._config.cookie_domain
        self.session_id = web.cookies().get(cookie_name)

        # protection against session_id tampering
        if self.session_id and not self._valid_session_id(self.session_id):
            self.session_id = None

        self._check_expiry()
        if self.session_id:
            d = self.store[self.session_id]
            self.update(d)
            self._validate_ip()
        
        if not self.session_id:
            self.session_id = self._generate_session_id()

            if self._initializer:
                if isinstance(self._initializer, dict):
                    self.update(self._initializer)
                elif hasattr(self._initializer, '__call__'):
                    self._initializer()
 
        self.ip = web.ctx.ip

    def _check_expiry(self):
        # check for expiry
        if self.session_id and self.session_id not in self.store:
            if self._config.ignore_expiry:
                self.session_id = None
            else:
                return self.expired()

    def _validate_ip(self):
        # check for change of IP
        if self.session_id and self.get('ip', None) != web.ctx.ip:
            if not self._config.ignore_change_ip:
               return self.expired() 
    
    def _save(self):
        cookie_name = self._config.cookie_name
        cookie_domain = self._config.cookie_domain
        if not self.get('_killed'):
            web.setcookie(cookie_name, self.session_id, domain=cookie_domain)
            self.store[self.session_id] = dict(self)
        else:
            web.setcookie(cookie_name, self.session_id, expires=-1, domain=cookie_domain)
    
    def _generate_session_id(self):
        """Generate a random id for session"""

        while True:
            rand = os.urandom(16)
            now = time.time()
            secret_key = self._config.secret_key
            session_id = sha1("%s%s%s%s" %(rand, now, utils.safestr(web.ctx.ip), secret_key))
            session_id = session_id.hexdigest()
            if session_id not in self.store:
                break
        return session_id

    def _valid_session_id(self, session_id):
        rx = utils.re_compile('^[0-9a-fA-F]+$')
        return rx.match(session_id)
        
    def _cleanup(self):
        """Cleanup the stored sessions"""
        current_time = time.time()
        timeout = self._config.timeout
        if current_time - self._last_cleanup_time > timeout:
            self.store.cleanup(timeout)
            self.__dict__['_last_cleanup_time'] = current_time

    def expired(self):
        """Called when an expired session is atime"""
        raise SessionExpired(self._config.expired_message)
 
    def kill(self):
        """Kill the session, make it no longer available"""
        del self.store[self.session_id]
        self._killed = True

class Store:
    """Base class for session stores"""

    def __contains__(self, key):
        raise NotImplemented

    def __getitem__(self, key):
        raise NotImplemented

    def __setitem__(self, key, value):
        raise NotImplemented

    def cleanup(self, timeout):
        """removes all the expired sessions"""
        raise NotImplemented

    def encode(self, session_dict):
        """encodes session dict as a string"""
        pickled = pickle.dumps(session_dict)
        return base64.encodestring(pickled)

    def decode(self, session_data):
        """decodes the data to get back the session dict """
        pickled = base64.decodestring(session_data)
        return pickle.loads(pickled)

class DiskStore(Store):
    """
    Store for saving a session on disk.

        >>> import tempfile
        >>> root = tempfile.mkdtemp()
        >>> s = DiskStore(root)
        >>> s['a'] = 'foo'
        >>> s['a']
        'foo'
        >>> time.sleep(0.01)
        >>> s.cleanup(0.01)
        >>> s['a']
        Traceback (most recent call last):
            ...
        KeyError: 'a'
    """
    def __init__(self, root):
        # if the storage root doesn't exists, create it.
        if not os.path.exists(root):
            os.mkdir(root)
        self.root = root

    def _get_path(self, key):
        if os.path.sep in key: 
            raise ValueError, "Bad key: %s" % repr(key)
        return os.path.join(self.root, key)
    
    def __contains__(self, key):
        path = self._get_path(key)
        return os.path.exists(path)

    def __getitem__(self, key):
        path = self._get_path(key)
        if os.path.exists(path): 
            pickled = open(path).read()
            return self.decode(pickled)
        else:
            raise KeyError, key

    def __setitem__(self, key, value):
        path = self._get_path(key)
        pickled = self.encode(value)    
        try:
            f = open(path, 'w')
            try:
                f.write(pickled)
            finally: 
                f.close()
        except IOError:
            pass

    def __delitem__(self, key):
        path = self._get_path(key)
        if os.path.exists(path):
            os.remove(path)
    
    def cleanup(self, timeout):
        now = time.time()
        for f in os.listdir(self.root):
            path = self._get_path(f)
            atime = os.stat(path).st_atime
            if now - atime > timeout :
                os.remove(path)

class DBStore(Store):
    """Store for saving a session in database
    Needs a table with the following columns:

        session_id CHAR(128) UNIQUE NOT NULL,
        atime DATETIME NOT NULL default current_timestamp,
        data TEXT
    """
    def __init__(self, db, table_name):
        self.db = db
        self.table = table_name
    
    def __contains__(self, key):
        data = self.db.select(self.table, where="session_id=$key", vars=locals())
        return bool(list(data)) 

    def __getitem__(self, key):
        now = datetime.datetime.now()
        try:
            s = self.db.select(self.table, where="session_id=$key", vars=locals())[0]
            self.db.update(self.table, where="session_id=$key", atime=now, vars=locals())
        except IndexError:
            raise KeyError
        else:
            return self.decode(s.data)

    def __setitem__(self, key, value):
        pickled = self.encode(value)
        now = datetime.datetime.now()
        if key in self:
            self.db.update(self.table, where="session_id=$key", data=pickled, vars=locals())
        else:
            self.db.insert(self.table, False, session_id=key, data=pickled )
                
    def __delitem__(self, key):
        self.db.delete(self.table, where="session_id=$key", vars=locals())

    def cleanup(self, timeout):
        timeout = datetime.timedelta(timeout/(24.0*60*60)) #timedelta takes numdays as arg
        last_allowed_time = datetime.datetime.now() - timeout
        self.db.delete(self.table, where="$last_allowed_time > atime", vars=locals())

class ShelfStore:
    """Store for saving session using `shelve` module.

        import shelve
        store = ShelfStore(shelve.open('session.shelf'))

    XXX: is shelve thread-safe?
    """
    def __init__(self, shelf):
        self.shelf = shelf

    def __contains__(self, key):
        return key in self.shelf

    def __getitem__(self, key):
        atime, v = self.shelf[key]
        self[k] = v # update atime
        return v

    def __setitem__(self, key, value):
        self.shelf[key] = time.time(), value
        
    def __delitem__(self, key):
        try:
            del self.shelf[key]
        except KeyError:
            pass

    def cleanup(self, timeout):
        now = time.time()
        for k in self.shelf.keys():
            atime, v = self.shelf[k]
            if now - atime > timeout :
                del self[k]

if __name__ == '__main__' :
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = template
"""
simple, elegant templating
(part of web.py)

Template design:

Template string is split into tokens and the tokens are combined into nodes. 
Parse tree is a nodelist. TextNode and ExpressionNode are simple nodes and 
for-loop, if-loop etc are block nodes, which contain multiple child nodes. 

Each node can emit some python string. python string emitted by the 
root node is validated for safeeval and executed using python in the given environment.

Enough care is taken to make sure the generated code and the template has line to line match, 
so that the error messages can point to exact line number in template. (It doesn't work in some cases still.)

Grammar:

    template -> defwith sections 
    defwith -> '$def with (' arguments ')' | ''
    sections -> section*
    section -> block | assignment | line

    assignment -> '$ ' <assignment expression>
    line -> (text|expr)*
    text -> <any characters other than $>
    expr -> '$' pyexpr | '$(' pyexpr ')' | '${' pyexpr '}'
    pyexpr -> <python expression>

"""

__all__ = [
    "Template",
    "Render", "render", "frender",
    "ParseError", "SecurityError",
    "test"
]

import tokenize
import os
import glob
import re

from utils import storage, safeunicode, safestr, re_compile
from webapi import config
from net import websafe

def splitline(text):
    r"""
    Splits the given text at newline.
    
        >>> splitline('foo\nbar')
        ('foo\n', 'bar')
        >>> splitline('foo')
        ('foo', '')
        >>> splitline('')
        ('', '')
    """
    index = text.find('\n') + 1
    if index:
        return text[:index], text[index:]
    else:
        return text, ''

class Parser:
    """Parser Base.
    """
    def __init__(self, text, name="<template>"):
        self.text = text
        self.name = name

    def parse(self):
        text = self.text
        defwith, text = self.read_defwith(text)
        suite = self.read_suite(text)
        return DefwithNode(defwith, suite)

    def read_defwith(self, text):
        if text.startswith('$def with'):
            defwith, text = splitline(text)
            defwith = defwith[1:].strip() # strip $ and spaces
            return defwith, text
        else:
            return '', text
    
    def read_section(self, text):
        r"""Reads one section from the given text.
        
        section -> block | assignment | line
        
            >>> read_section = Parser('').read_section
            >>> read_section('foo\nbar\n')
            (<line: [t'foo\n']>, 'bar\n')
            >>> read_section('$ a = b + 1\nfoo\n')
            (<assignment: 'a = b + 1'>, 'foo\n')
            
        read_section('$for in range(10):\n    hello $i\nfoo)
        """
        if text.lstrip(' ').startswith('$'):
            index = text.index('$')
            begin_indent, text2 = text[:index], text[index+1:]
            ahead = self.python_lookahead(text2)
            
            if ahead == 'var':
                return self.read_var(text2)
            elif ahead in STATEMENT_NODES:
                return self.read_block_section(text2, begin_indent)
            elif ahead in KEYWORDS:
                return self.read_keyword(text2)
            elif ahead.strip() == '':
                # assignments starts with a space after $
                # ex: $ a = b + 2
                return self.read_assignment(text2)
        return self.readline(text)
        
    def read_var(self, text):
        r"""Reads a var statement.
        
            >>> read_var = Parser('').read_var
            >>> read_var('var x=10\nfoo')
            (<var: x = 10>, 'foo')
            >>> read_var('var x: hello $name\nfoo')
            (<var: x = join_('hello ', escape_(name, True))>, 'foo')
        """
        line, text = splitline(text)
        tokens = self.python_tokens(line)
        if len(tokens) < 4:
            raise SyntaxError('Invalid var statement')
            
        name = tokens[1]
        sep = tokens[2]
        value = line.split(sep, 1)[1].strip()
        
        if sep == '=':
            pass # no need to process value
        elif sep == ':': 
            #@@ Hack for backward-compatability
            if tokens[3] == '\n': # multi-line var statement
                block, text = self.read_indented_block(text, '    ')
                lines = [self.readline(x)[0] for x in block.splitlines()]
                nodes = []
                for x in lines:
                    nodes.extend(x.nodes)
                    nodes.append(TextNode('\n'))         
            else: # single-line var statement
                linenode, _ = self.readline(value)
                nodes = linenode.nodes                
            parts = [node.emit('') for node in nodes]
            value = "join_(%s)" % ", ".join(parts)
        else:
            raise SyntaxError('Invalid var statement')
        return VarNode(name, value), text
                    
    def read_suite(self, text):
        r"""Reads section by section till end of text.
        
            >>> read_suite = Parser('').read_suite
            >>> read_suite('hello $name\nfoo\n')
            [<line: [t'hello ', $name, t'\n']>, <line: [t'foo\n']>]
        """
        sections = []
        while text:
            section, text = self.read_section(text)
            sections.append(section)
        return SuiteNode(sections)
    
    def readline(self, text):
        r"""Reads one line from the text. Newline is supressed if the line ends with \.
        
            >>> readline = Parser('').readline
            >>> readline('hello $name!\nbye!')
            (<line: [t'hello ', $name, t'!\n']>, 'bye!')
            >>> readline('hello $name!\\\nbye!')
            (<line: [t'hello ', $name, t'!']>, 'bye!')
            >>> readline('$f()\n\n')
            (<line: [$f(), t'\n']>, '\n')
        """
        line, text = splitline(text)

        # supress new line if line ends with \
        if line.endswith('\\\n'):
            line = line[:-2]
                
        nodes = []
        while line:
            node, line = self.read_node(line)
            nodes.append(node)
            
        return LineNode(nodes), text

    def read_node(self, text):
        r"""Reads a node from the given text and returns the node and remaining text.

            >>> read_node = Parser('').read_node
            >>> read_node('hello $name')
            (t'hello ', '$name')
            >>> read_node('$name')
            ($name, '')
        """
        if text.startswith('$$'):
            return TextNode('$'), text[2:]
        elif text.startswith('$#'): # comment
            line, text = splitline(text)
            return TextNode('\n'), text
        elif text.startswith('$'):
            text = text[1:] # strip $
            if text.startswith(':'):
                escape = False
                text = text[1:] # strip :
            else:
                escape = True
            return self.read_expr(text, escape=escape)
        else:
            return self.read_text(text)
    
    def read_text(self, text):
        r"""Reads a text node from the given text.
        
            >>> read_text = Parser('').read_text
            >>> read_text('hello $name')
            (t'hello ', '$name')
        """
        index = text.find('$')
        if index < 0:
            return TextNode(text), ''
        else:
            return TextNode(text[:index]), text[index:]
            
    def read_keyword(self, text):
        line, text = splitline(text)
        return CodeNode(None, line.strip() + "\n"), text

    def read_expr(self, text, escape=True):
        """Reads a python expression from the text and returns the expression and remaining text.

        expr -> simple_expr | paren_expr
        simple_expr -> id extended_expr
        extended_expr -> attr_access | paren_expr extended_expr | ''
        attr_access -> dot id extended_expr
        paren_expr -> [ tokens ] | ( tokens ) | { tokens }
     
            >>> read_expr = Parser('').read_expr
            >>> read_expr("name")
            ($name, '')
            >>> read_expr("a.b and c")
            ($a.b, ' and c')
            >>> read_expr("a. b")
            ($a, '. b')
            >>> read_expr("name</h1>")
            ($name, '</h1>')
            >>> read_expr("(limit)ing")
            ($(limit), 'ing')
            >>> read_expr('a[1, 2][:3].f(1+2, "weird string[).", 3 + 4) done.')
            ($a[1, 2][:3].f(1+2, "weird string[).", 3 + 4), ' done.')
        """
        def simple_expr():
            identifier()
            extended_expr()
        
        def identifier():
            tokens.next()
        
        def extended_expr():
            lookahead = tokens.lookahead()
            if lookahead is None:
                return
            elif lookahead.value == '.':
                attr_access()
            elif lookahead.value in parens:
                paren_expr()
                extended_expr()
            else:
                return
        
        def attr_access():
            from token import NAME # python token constants
            dot = tokens.lookahead()
            if tokens.lookahead2().type == NAME:
                tokens.next() # consume dot
                identifier()
                extended_expr()
        
        def paren_expr():
            begin = tokens.next().value
            end = parens[begin]
            while True:
                if tokens.lookahead().value in parens:
                    paren_expr()
                else:
                    t = tokens.next()
                    if t.value == end:
                        break
            return

        parens = {
            "(": ")",
            "[": "]",
            "{": "}"
        }
        
        def get_tokens(text):
            """tokenize text using python tokenizer.
            Python tokenizer ignores spaces, but they might be important in some cases. 
            This function introduces dummy space tokens when it identifies any ignored space.
            Each token is a storage object containing type, value, begin and end.
            """
            readline = iter([text]).next
            end = None
            for t in tokenize.generate_tokens(readline):
                t = storage(type=t[0], value=t[1], begin=t[2], end=t[3])
                if end is not None and end != t.begin:
                    _, x1 = end
                    _, x2 = t.begin
                    yield storage(type=-1, value=text[x1:x2], begin=end, end=t.begin)
                end = t.end
                yield t
                
        class BetterIter:
            """Iterator like object with 2 support for 2 look aheads."""
            def __init__(self, items):
                self.iteritems = iter(items)
                self.items = []
                self.position = 0
                self.current_item = None
            
            def lookahead(self):
                if len(self.items) <= self.position:
                    self.items.append(self._next())
                return self.items[self.position]

            def _next(self):
                try:
                    return self.iteritems.next()
                except StopIteration:
                    return None
                
            def lookahead2(self):
                if len(self.items) <= self.position+1:
                    self.items.append(self._next())
                return self.items[self.position+1]
                    
            def next(self):
                self.current_item = self.lookahead()
                self.position += 1
                return self.current_item

        tokens = BetterIter(get_tokens(text))
                
        if tokens.lookahead().value in parens:
            paren_expr()
        else:
            simple_expr()
        row, col = tokens.current_item.end
        return ExpressionNode(text[:col], escape=escape), text[col:]    

    def read_assignment(self, text):
        r"""Reads assignment statement from text.
    
            >>> read_assignment = Parser('').read_assignment
            >>> read_assignment('a = b + 1\nfoo')
            (<assignment: 'a = b + 1'>, 'foo')
        """
        line, text = splitline(text)
        return AssignmentNode(line.strip()), text
    
    def python_lookahead(self, text):
        """Returns the first python token from the given text.
        
            >>> python_lookahead = Parser('').python_lookahead
            >>> python_lookahead('for i in range(10):')
            'for'
            >>> python_lookahead('else:')
            'else'
            >>> python_lookahead(' x = 1')
            ' '
        """
        readline = iter([text]).next
        tokens = tokenize.generate_tokens(readline)
        return tokens.next()[1]
        
    def python_tokens(self, text):
        readline = iter([text]).next
        tokens = tokenize.generate_tokens(readline)
        return [t[1] for t in tokens]
        
    def read_indented_block(self, text, indent):
        r"""Read a block of text. A block is what typically follows a for or it statement.
        It can be in the same line as that of the statement or an indented block.

            >>> read_indented_block = Parser('').read_indented_block
            >>> read_indented_block('  a\n  b\nc', '  ')
            ('a\nb\n', 'c')
            >>> read_indented_block('  a\n    b\n  c\nd', '  ')
            ('a\n  b\nc\n', 'd')
        """
        if indent == '':
            return '', text
            
        block = ""
        while True:
            if text.startswith(indent):
                line, text = splitline(text)
                block += line[len(indent):]
            else:
                break
        return block, text

    def read_statement(self, text):
        r"""Reads a python statement.
        
            >>> read_statement = Parser('').read_statement
            >>> read_statement('for i in range(10): hello $name')
            ('for i in range(10):', ' hello $name')
        """
        tok = PythonTokenizer(text)
        tok.consume_till(':')
        return text[:tok.index], text[tok.index:]
        
    def read_block_section(self, text, begin_indent=''):
        r"""
            >>> read_block_section = Parser('').read_block_section
            >>> read_block_section('for i in range(10): hello $i\nfoo')
            (<block: 'for i in range(10):', [<line: [t'hello ', $i, t'\n']>]>, 'foo')
            >>> read_block_section('for i in range(10):\n        hello $i\n    foo', begin_indent='    ')
            (<block: 'for i in range(10):', [<line: [t'hello ', $i, t'\n']>]>, '    foo')
            >>> read_block_section('for i in range(10):\n  hello $i\nfoo')
            (<block: 'for i in range(10):', [<line: [t'hello ', $i, t'\n']>]>, 'foo')
        """
        line, text = splitline(text)
        stmt, line = self.read_statement(line)
        keyword = self.python_lookahead(stmt)
        
        # if there is some thing left in the line
        if line.strip():
            block = line.lstrip()
        else:
            def find_indent(text):
                rx = re_compile('  +')
                match = rx.match(text)    
                first_indent = match and match.group(0)
                return first_indent or ""

            # find the indentation of the block by looking at the first line
            first_indent = find_indent(text)[len(begin_indent):]
            indent = begin_indent + min(first_indent, INDENT)
            
            block, text = self.read_indented_block(text, indent)
            
        return self.create_block_node(keyword, stmt, block, begin_indent), text
        
    def create_block_node(self, keyword, stmt, block, begin_indent):
        if keyword in STATEMENT_NODES:
            return STATEMENT_NODES[keyword](stmt, block, begin_indent)
        else:
            raise ParseError, 'Unknown statement: %s' % repr(keyword)
        
class PythonTokenizer:
    """Utility wrapper over python tokenizer."""
    def __init__(self, text):
        self.text = text
        readline = iter([text]).next
        self.tokens = tokenize.generate_tokens(readline)
        self.index = 0
        
    def consume_till(self, delim):        
        """Consumes tokens till colon.
        
            >>> tok = PythonTokenizer('for i in range(10): hello $i')
            >>> tok.consume_till(':')
            >>> tok.text[:tok.index]
            'for i in range(10):'
            >>> tok.text[tok.index:]
            ' hello $i'
        """
        try:
            while True:
                t = self.next()
                if t.value == delim:
                    break

                # if end of line is found, it is an exception.
                # Since there is no easy way to report the line number,
                # leave the error reporting to the python parser later  
                #@@ This should be fixed.
                if t.value == '\n':
                    break
        except:
            #raise ParseError, "Expected %s, found end of line." % repr(delim)

            # raising ParseError doesn't show the line number. 
            # if this error is ignored, then it will be caught when compiling the python code.
            return
    
    def next(self):
        type, t, begin, end, line = self.tokens.next()
        row, col = end
        self.index = col
        return storage(type=type, value=t, begin=begin, end=end)
        
class DefwithNode:
    def __init__(self, defwith, suite):
        if defwith:
            self.defwith = defwith.replace('with', '__template__') + ':'
        else:
            self.defwith = 'def __template__():'
        self.suite = suite

    def emit(self, indent):
        return self.defwith + self.suite.emit(indent + INDENT)

    def __repr__(self):
        return "<defwith: %s, %s>" % (self.defwith, self.nodes)

class TextNode:
    def __init__(self, value):
        self.value = value

    def emit(self, indent):
        return repr(self.value)
        
    def __repr__(self):
        return 't' + repr(self.value)
        
class ExpressionNode:
    def __init__(self, value, escape=True):
        self.value = value.strip()
        
        # convert ${...} to $(...)
        if value.startswith('{') and value.endswith('}'):
            self.value = '(' + self.value[1:-1] + ')'
            
        self.escape = escape

    def emit(self, indent):
        return 'escape_(%s, %s)' % (self.value, bool(self.escape))
        
    def __repr__(self):
        if self.escape:
            escape = ''
        else:
            escape = ':'
        return "$%s%s" % (escape, self.value)
        
class AssignmentNode:
    def __init__(self, code):
        self.code = code
        
    def emit(self, indent, begin_indent=''):
        return indent + self.code + "\n"
        
    def __repr__(self):
        return "<assignment: %s>" % repr(self.code)
        
class LineNode:
    def __init__(self, nodes):
        self.nodes = nodes
        
    def emit(self, indent, text_indent='', name=''):
        text = [node.emit('') for node in self.nodes]
        if text_indent:
            text = [repr(text_indent)] + text
        return indent + 'yield %s, join_(%s)\n' % (repr(name), ', '.join(text))
    
    def __repr__(self):
        return "<line: %s>" % repr(self.nodes)

INDENT = '    ' # 4 spaces
        
class BlockNode:
    def __init__(self, stmt, block, begin_indent=''):
        self.stmt = stmt
        self.suite = Parser('').read_suite(block)
        self.begin_indent = begin_indent

    def emit(self, indent, text_indent=''):
        text_indent = self.begin_indent + text_indent
        out = indent + self.stmt + self.suite.emit(indent + INDENT, text_indent)
        return out
        
    def text(self):
        return '${' + self.stmt + '}' + "".join([node.text(indent) for node in self.nodes])
        
    def __repr__(self):
        return "<block: %s, %s>" % (repr(self.stmt), repr(self.nodelist))

class ForNode(BlockNode):
    def __init__(self, stmt, block, begin_indent=''):
        self.original_stmt = stmt
        tok = PythonTokenizer(stmt)
        tok.consume_till('in')
        a = stmt[:tok.index] # for i in
        b = stmt[tok.index:-1] # rest of for stmt excluding :
        stmt = a + ' loop.setup(' + b.strip() + '):'
        BlockNode.__init__(self, stmt, block, begin_indent)
        
    def __repr__(self):
        return "<block: %s, %s>" % (repr(self.original_stmt), repr(self.suite))

class CodeNode:
    def __init__(self, stmt, block, begin_indent=''):
        self.code = block
        
    def emit(self, indent, text_indent=''):
        import re
        rx = re.compile('^', re.M)
        return rx.sub(indent, self.code).rstrip(' ')
        
    def __repr__(self):
        return "<code: %s>" % repr(self.code)
        
class IfNode(BlockNode):
    pass

class ElseNode(BlockNode):
    pass

class ElifNode(BlockNode):
    pass

class DefNode(BlockNode):
    pass

class VarNode:
    def __init__(self, name, value):
        self.name = name
        self.value = value
        
    def emit(self, indent, text_indent):
        return indent + 'yield %s, %s\n' % (repr(self.name), self.value)
        
    def __repr__(self):
        return "<var: %s = %s>" % (self.name, self.value)

class SuiteNode:
    """Suite is a list of sections."""
    def __init__(self, sections):
        self.sections = sections
        
    def emit(self, indent, text_indent=''):
        return "\n" + "".join([s.emit(indent, text_indent) for s in self.sections])
        
    def __repr__(self):
        return repr(self.sections)

STATEMENT_NODES = {
    'for': ForNode,
    'while': BlockNode,
    'if': IfNode,
    'elif': ElifNode,
    'else': ElseNode,
    'def': DefNode,
    'code': CodeNode
}

KEYWORDS = [
    "pass",
    "break",
    "continue",
    "return"
]

TEMPLATE_BUILTIN_NAMES = [
    "dict", "enumerate", "float", "int", "bool", "list", "long", "reversed", 
    "set", "slice", "tuple", "xrange",
    "abs", "all", "any", "callable", "chr", "cmp", "divmod", "filter", "hex", 
    "id", "isinstance", "iter", "len", "max", "min", "oct", "ord", "pow", "range",
    "True", "False"
]

import __builtin__
TEMPLATE_BUILTINS = dict([(name, getattr(__builtin__, name)) for name in TEMPLATE_BUILTIN_NAMES if name in __builtin__.__dict__])

class ForLoop:
    """
    Wrapper for expression in for stament to support loop.xxx helpers.
    
        >>> loop = ForLoop()
        >>> for x in loop.setup(['a', 'b', 'c']):
        ...     print loop.index, loop.revindex, loop.parity, x
        ...
        1 3 odd a
        2 2 even b
        3 1 odd c
        >>> loop.index
        Traceback (most recent call last):
            ...
        AttributeError: index
    """
    def __init__(self):
        self._ctx = None
        
    def __getattr__(self, name):
        if self._ctx is None:
            raise AttributeError, name
        else:
            return getattr(self._ctx, name)
        
    def setup(self, seq):        
        self._push()
        return self._ctx.setup(seq)
        
    def _push(self):
        self._ctx = ForLoopContext(self, self._ctx)
        
    def _pop(self):
        self._ctx = self._ctx.parent
                
class ForLoopContext:
    """Stackable context for ForLoop to support nested for loops.
    """
    def __init__(self, forloop, parent):
        self._forloop = forloop
        self.parent = parent
        
    def setup(self, seq):
        if hasattr(seq, '__len__'):
            n = len(seq)
        else:
            n = 0
            
        self.index = 0
        seq = iter(seq)
        
        # Pre python-2.5 does not support yield in try-except.
        # This is a work-around to overcome that limitation.
        def next(seq):
            try:
                return seq.next()
            except:
                self._forloop._pop()
                raise
        
        while True:
            self._next(self.index + 1, n)
            yield next(seq)
            
    def _next(self, i, n):
        self.index = i
        self.index0 = i - 1
        self.first = (i == 1)
        self.last = (i == n)
        self.odd = (i % 2 == 1)
        self.even = (i % 2 == 0)
        self.parity = ['odd', 'even'][self.even]
        if n:
            self.length = n
            self.revindex0 = n - i
            self.revindex = self.revindex0 + 1
        
class BaseTemplate:
    def __init__(self, code, filename, filter, globals, builtins):
        self.filename = filename
        self.filter = filter
        self._globals = globals
        self._builtins = builtins
        if code:
            self.t = self._compile(code)
        else:
            self.t = lambda: ''
        
    def _compile(self, code):
        env = self.make_env(self._globals or {}, self._builtins)
        exec(code, env)
        return env['__template__']

    def __call__(self, *a, **kw):
        out = self.t(*a, **kw)
        return self._join_output(out)
        
    def _join_output(self, out):
        d = TemplateResult()
        data = []
        
        for name, value in out:
            if name:
                d[name] = value
            else:
                data.append(value)
                            
        d.__body__ = u"".join(data)
        return d       

    def make_env(self, globals, builtins):
        return dict(globals,
            __builtins__=builtins, 
            loop=ForLoop(),
            escape_=self._escape,
            join_=self._join
        )
    
    def _join(self, *items):
        return u"".join([safeunicode(item) for item in items])
        
    def _escape(self, value, escape=False):
        import types
        if value is None: 
            value = ''
        elif isinstance(value, types.GeneratorType):
            value = self._join_output(value)
            
        value = safeunicode(value)
        if escape and self.filter:
            value = self.filter(value)
        return value

class Template(BaseTemplate):
    CONTENT_TYPES = {
        '.html' : 'text/html; charset=utf-8',
        '.xhtml' : 'application/xhtml+xml; charset=utf-8',
        '.txt' : 'text/plain',
    }
    FILTERS = {
        '.html': websafe,
        '.xhtml': websafe,
        '.xml': websafe
    }
    globals = {}
    
    def __init__(self, text, filename='<template>', filter=None, globals=None, builtins=None):
        text = text.replace('\r\n', '\n').replace('\r', '\n').expandtabs()
        if not text.endswith('\n'):
            text += '\n'

        # ignore BOM chars at the begining of template
        BOM = '\xef\xbb\xbf'
        if text.startswith(BOM):
            text = text[len(BOM):]
        
        # support fort \$ for backward-compatibility 
        text = text.replace(r'\$', '$$')
        
        code = self.compile_template(text, filename)
                
        _, ext = os.path.splitext(filename)
        filter = filter or self.FILTERS.get(ext, None)
        self.content_type = self.CONTENT_TYPES.get(ext, None)

        if globals is None:
            globals = self.globals
        if builtins is None:
            builtins = TEMPLATE_BUILTINS
                
        BaseTemplate.__init__(self, code=code, filename=filename, filter=filter, globals=globals, builtins=builtins)
        
    def __call__(self, *a, **kw):
        import webapi as web
        if 'headers' in web.ctx and self.content_type:
            web.header('Content-Type', self.content_type, unique=True)
            
        return BaseTemplate.__call__(self, *a, **kw)
        
    def generate_code(text, filename):
        # parse the text
        rootnode = Parser(text, filename).parse()
                
        # generate python code from the parse tree
        code = rootnode.emit(indent="").strip()
        return safestr(code)
        
    generate_code = staticmethod(generate_code)
        
    def compile_template(self, template_string, filename):
        code = Template.generate_code(template_string, filename)
    
        def get_source_line(filename, lineno):
            try:
                lines = open(filename).read().splitlines()
                return lines[lineno]
            except:
                return None
        
        try:
            # compile the code first to report the errors, if any, with the filename
            compiled_code = compile(code, filename, 'exec')
        except SyntaxError, e:
            # display template line that caused the error along with the traceback.
            try:
                e.msg += '\n\nTemplate traceback:\n    File %s, line %s\n        %s' % \
                    (repr(e.filename), e.lineno, get_source_line(e.filename, e.lineno-1))
            except: 
                pass
            raise
        
        # make sure code is safe
        import compiler
        ast = compiler.parse(code)
        SafeVisitor().walk(ast, filename)

        return compiled_code
        
class CompiledTemplate(Template):
    def __init__(self, f, filename):
        Template.__init__(self, '', filename)
        self.t = f
        
    def compile_template(self, *a):
        return None
    
    def _compile(self, *a):
        return None
                
class Render:
    """The most preferred way of using templates.
    
        render = web.template.render('templates')
        print render.foo()
        
    Optional parameter can be `base` can be used to pass output of 
    every template through the base template.
    
        render = web.template.render('templates', base='layout')
    """
    def __init__(self, loc='templates', cache=None, base=None, **keywords):
        self._loc = loc
        self._keywords = keywords

        if cache is None:
            cache = not config.get('debug', False)
        
        if cache:
            self._cache = {}
        else:
            self._cache = None
        
        if base and not hasattr(base, '__call__'):
            # make base a function, so that it can be passed to sub-renders
            self._base = lambda page: self._template(base)(page)
        else:
            self._base = base
            
    def _lookup(self, name):
        path = os.path.join(self._loc, name)
        if os.path.isdir(path):
            return 'dir', path
        else:
            path = self._findfile(path)
            if path:
                return 'file', path
            else:
                return 'none', None
        
    def _load_template(self, name):
        kind, path = self._lookup(name)
        
        if kind == 'dir':
            return Render(path, cache=self._cache is not None, base=self._base, **self._keywords)
        elif kind == 'file':
            return Template(open(path).read(), filename=path, **self._keywords)
        else:
            raise AttributeError, "No template named " + name            

    def _findfile(self, path_prefix): 
        p = [f for f in glob.glob(path_prefix + '.*') if not f.endswith('~')] # skip backup files
        return p and p[0]
            
    def _template(self, name):
        if self._cache is not None:
            if name not in self._cache:
                self._cache[name] = self._load_template(name)
            return self._cache[name]
        else:
            return self._load_template(name)
        
    def __getattr__(self, name):
        t = self._template(name)
        if self._base and isinstance(t, Template):
            def template(*a, **kw):
                return self._base(t(*a, **kw))
            return template
        else:
            return self._template(name)

class GAE_Render(Render):
    # Render gets over-written. make a copy here.
    super = Render
    def __init__(self, loc, *a, **kw):
        GAE_Render.super.__init__(self, loc, *a, **kw)
        
        import types
        if isinstance(loc, types.ModuleType):
            self.mod = loc
        else:
            name = loc.rstrip('/').replace('/', '.')
            self.mod = __import__(name, None, None, ['x'])

        self.mod.__dict__.update(kw.get('builtins', TEMPLATE_BUILTINS))
        self.mod.__dict__.update(Template.globals)
        self.mod.__dict__.update(kw.get('globals', {}))

    def _load_template(self, name):
        t = getattr(self.mod, name)
        import types
        if isinstance(t, types.ModuleType):
            return GAE_Render(t, cache=self._cache is not None, base=self._base, **self._keywords)
        else:
            return t

render = Render
# setup render for Google App Engine.
try:
    from google import appengine
    render = Render = GAE_Render
except ImportError:
    pass
        
def frender(path, **keywords):
    """Creates a template from the given file path.
    """
    return Template(open(path).read(), filename=path, **keywords)
    
def compile_templates(root):
    """Compiles templates to python code."""
    re_start = re_compile('^', re.M)
    
    for dirpath, dirnames, filenames in os.walk(root):
        filenames = [f for f in filenames if not f.startswith('.') and not f.endswith('~') and not f.startswith('__init__.py')]
        
        out = open(os.path.join(dirpath, '__init__.py'), 'w')
        out.write('from web.template import CompiledTemplate, ForLoop\n\n')
        if dirnames:
            out.write("import " + ", ".join(dirnames))

        for f in filenames:
            path = os.path.join(dirpath, f)

            # create template to make sure it compiles
            t = Template(open(path).read(), path)
            
            if '.' in f:
                name, _ = f.split('.', 1)
            else:
                name = f
            
            code = Template.generate_code(open(path).read(), path)
            code = re_start.sub('    ', code)
                        
            _gen = '' + \
            '\ndef %s():' + \
            '\n    loop = ForLoop()' + \
            '\n    _dummy  = CompiledTemplate(lambda: None, "dummy")' + \
            '\n    join_ = _dummy._join' + \
            '\n    escape_ = _dummy._escape' + \
            '\n' + \
            '\n%s' + \
            '\n    return __template__'
            
            gen_code = _gen % (name, code)
            out.write(gen_code)
            out.write('\n\n')
            out.write('%s = CompiledTemplate(%s(), %s)\n\n' % (name, name, repr(path)))
        out.close()
                
class ParseError(Exception):
    pass
    
class SecurityError(Exception):
    """The template seems to be trying to do something naughty."""
    pass

# Enumerate all the allowed AST nodes
ALLOWED_AST_NODES = [
    "Add", "And",
#   "AssAttr",
    "AssList", "AssName", "AssTuple",
#   "Assert",
    "Assign", "AugAssign",
#   "Backquote",
    "Bitand", "Bitor", "Bitxor", "Break",
    "CallFunc","Class", "Compare", "Const", "Continue",
    "Decorators", "Dict", "Discard", "Div",
    "Ellipsis", "EmptyNode",
#   "Exec",
    "Expression", "FloorDiv", "For",
#   "From",
    "Function", 
    "GenExpr", "GenExprFor", "GenExprIf", "GenExprInner",
    "Getattr", 
#   "Global", 
    "If", "IfExp",
#   "Import",
    "Invert", "Keyword", "Lambda", "LeftShift",
    "List", "ListComp", "ListCompFor", "ListCompIf", "Mod",
    "Module",
    "Mul", "Name", "Not", "Or", "Pass", "Power",
#   "Print", "Printnl", "Raise",
    "Return", "RightShift", "Slice", "Sliceobj",
    "Stmt", "Sub", "Subscript",
#   "TryExcept", "TryFinally",
    "Tuple", "UnaryAdd", "UnarySub",
    "While", "With", "Yield",
]

class SafeVisitor(object):
    """
    Make sure code is safe by walking through the AST.
    
    Code considered unsafe if:
        * it has restricted AST nodes
        * it is trying to access resricted attributes   
        
    Adopted from http://www.zafar.se/bkz/uploads/safe.txt (public domain, Babar K. Zafar)
    """
    def __init__(self):
        "Initialize visitor by generating callbacks for all AST node types."
        self.errors = []

    def walk(self, ast, filename):
        "Validate each node in AST and raise SecurityError if the code is not safe."
        self.filename = filename
        self.visit(ast)
        
        if self.errors:        
            raise SecurityError, '\n'.join([str(err) for err in self.errors])
        
    def visit(self, node, *args):
        "Recursively validate node and all of its children."
        def classname(obj):
            return obj.__class__.__name__
        nodename = classname(node)
        fn = getattr(self, 'visit' + nodename, None)
        
        if fn:
            fn(node, *args)
        else:
            if nodename not in ALLOWED_AST_NODES:
                self.fail(node, *args)
            
        for child in node.getChildNodes():
            self.visit(child, *args)

    def visitName(self, node, *args):
        "Disallow any attempts to access a restricted attr."
        #self.assert_attr(node.getChildren()[0], node)
        pass
        
    def visitGetattr(self, node, *args):
        "Disallow any attempts to access a restricted attribute."
        self.assert_attr(node.attrname, node)
            
    def assert_attr(self, attrname, node):
        if self.is_unallowed_attr(attrname):
            lineno = self.get_node_lineno(node)
            e = SecurityError("%s:%d - access to attribute '%s' is denied" % (self.filename, lineno, attrname))
            self.errors.append(e)

    def is_unallowed_attr(self, name):
        return name.startswith('_') \
            or name.startswith('func_') \
            or name.startswith('im_')
            
    def get_node_lineno(self, node):
        return (node.lineno) and node.lineno or 0
        
    def fail(self, node, *args):
        "Default callback for unallowed AST nodes."
        lineno = self.get_node_lineno(node)
        nodename = node.__class__.__name__
        e = SecurityError("%s:%d - execution of '%s' statements is denied" % (self.filename, lineno, nodename))
        self.errors.append(e)

class TemplateResult(storage):
    """Dictionary like object for storing template output.
    
    A template can specify key-value pairs in the output using 
    `var` statements. Each `var` statement adds a new key to the 
    template output and the main output is stored with key 
    __body__.
    
        >>> d = TemplateResult(__body__='hello, world', x='foo')
        >>> d
        <TemplateResult: {'__body__': 'hello, world', 'x': 'foo'}>
        >>> print d
        hello, world
    """
    def __unicode__(self): 
        return safeunicode(self.get('__body__', ''))
    
    def __str__(self):
        return safestr(self.get('__body__', ''))
        
    def __repr__(self):
        return "<TemplateResult: %s>" % dict.__repr__(self)
    
def test():
    r"""Doctest for testing template module.

    Define a utility function to run template test.
    
        >>> class TestResult(TemplateResult):
        ...     def __repr__(self): return repr(unicode(self))
        ...
        >>> def t(code, **keywords):
        ...     tmpl = Template(code, **keywords)
        ...     return lambda *a, **kw: TestResult(tmpl(*a, **kw))
        ...
    
    Simple tests.
    
        >>> t('1')()
        u'1\n'
        >>> t('$def with ()\n1')()
        u'1\n'
        >>> t('$def with (a)\n$a')(1)
        u'1\n'
        >>> t('$def with (a=0)\n$a')(1)
        u'1\n'
        >>> t('$def with (a=0)\n$a')(a=1)
        u'1\n'
    
    Test complicated expressions.
        
        >>> t('$def with (x)\n$x.upper()')('hello')
        u'HELLO\n'
        >>> t('$(2 * 3 + 4 * 5)')()
        u'26\n'
        >>> t('${2 * 3 + 4 * 5}')()
        u'26\n'
        >>> t('$def with (limit)\nkeep $(limit)ing.')('go')
        u'keep going.\n'
        >>> t('$def with (a)\n$a.b[0]')(storage(b=[1]))
        u'1\n'
        
    Test html escaping.
    
        >>> t('$def with (x)\n$x', filename='a.html')('<html>')
        u'&lt;html&gt;\n'
        >>> t('$def with (x)\n$x', filename='a.txt')('<html>')
        u'<html>\n'
                
    Test if, for and while.
    
        >>> t('$if 1: 1')()
        u'1\n'
        >>> t('$if 1:\n    1')()
        u'1\n'
        >>> t('$if 1:\n    1\\')()
        u'1'
        >>> t('$if 0: 0\n$elif 1: 1')()
        u'1\n'
        >>> t('$if 0: 0\n$elif None: 0\n$else: 1')()
        u'1\n'
        >>> t('$if 0 < 1 and 1 < 2: 1')()
        u'1\n'
        >>> t('$for x in [1, 2, 3]: $x')()
        u'1\n2\n3\n'
        >>> t('$def with (d)\n$for k, v in d.iteritems(): $k')({1: 1})
        u'1\n'
        >>> t('$for x in [1, 2, 3]:\n\t$x')()
        u'    1\n    2\n    3\n'
        >>> t('$def with (a)\n$while a and a.pop():1')([1, 2, 3])
        u'1\n1\n1\n'

    The space after : must be ignored.
    
        >>> t('$if True: foo')()
        u'foo\n'
    
    Test loop.xxx.

        >>> t("$for i in range(5):$loop.index, $loop.parity")()
        u'1, odd\n2, even\n3, odd\n4, even\n5, odd\n'
        >>> t("$for i in range(2):\n    $for j in range(2):$loop.parent.parity $loop.parity")()
        u'odd odd\nodd even\neven odd\neven even\n'
        
    Test assignment.
    
        >>> t('$ a = 1\n$a')()
        u'1\n'
        >>> t('$ a = [1]\n$a[0]')()
        u'1\n'
        >>> t('$ a = {1: 1}\n$a.keys()[0]')()
        u'1\n'
        >>> t('$ a = []\n$if not a: 1')()
        u'1\n'
        >>> t('$ a = {}\n$if not a: 1')()
        u'1\n'
        >>> t('$ a = -1\n$a')()
        u'-1\n'
        >>> t('$ a = "1"\n$a')()
        u'1\n'

    Test comments.
    
        >>> t('$# 0')()
        u'\n'
        >>> t('hello$#comment1\nhello$#comment2')()
        u'hello\nhello\n'
        >>> t('$#comment0\nhello$#comment1\nhello$#comment2')()
        u'\nhello\nhello\n'
        
    Test unicode.
    
        >>> t('$def with (a)\n$a')(u'\u203d')
        u'\u203d\n'
        >>> t('$def with (a)\n$a')(u'\u203d'.encode('utf-8'))
        u'\u203d\n'
        >>> t(u'$def with (a)\n$a $:a')(u'\u203d')
        u'\u203d \u203d\n'
        >>> t(u'$def with ()\nfoo')()
        u'foo\n'
        >>> def f(x): return x
        ...
        >>> t(u'$def with (f)\n$:f("x")')(f)
        u'x\n'
        >>> t('$def with (f)\n$:f("x")')(f)
        u'x\n'
    
    Test dollar escaping.
    
        >>> t("Stop, $$money isn't evaluated.")()
        u"Stop, $money isn't evaluated.\n"
        >>> t("Stop, \$money isn't evaluated.")()
        u"Stop, $money isn't evaluated.\n"
        
    Test space sensitivity.
    
        >>> t('$def with (x)\n$x')(1)
        u'1\n'
        >>> t('$def with(x ,y)\n$x')(1, 1)
        u'1\n'
        >>> t('$(1 + 2*3 + 4)')()
        u'11\n'
        
    Make sure globals are working.
            
        >>> t('$x')()
        Traceback (most recent call last):
            ...
        NameError: global name 'x' is not defined
        >>> t('$x', globals={'x': 1})()
        u'1\n'
        
    Can't change globals.
    
        >>> t('$ x = 2\n$x', globals={'x': 1})()
        u'2\n'
        >>> t('$ x = x + 1\n$x', globals={'x': 1})()
        Traceback (most recent call last):
            ...
        UnboundLocalError: local variable 'x' referenced before assignment
    
    Make sure builtins are customizable.
    
        >>> t('$min(1, 2)')()
        u'1\n'
        >>> t('$min(1, 2)', builtins={})()
        Traceback (most recent call last):
            ...
        NameError: global name 'min' is not defined
        
    Test vars.
    
        >>> x = t('$var x: 1')()
        >>> x.x
        u'1'
        >>> x = t('$var x = 1')()
        >>> x.x
        1
        >>> x = t('$var x:  \n    foo\n    bar')()
        >>> x.x
        u'foo\nbar\n'

    Test BOM chars.

        >>> t('\xef\xbb\xbf$def with(x)\n$x')('foo')
        u'foo\n'
    """
    pass
            
if __name__ == "__main__":
    import sys
    if '--compile' in sys.argv:
        compile_templates(sys.argv[2])
    else:
        import doctest
        doctest.testmod()

########NEW FILE########
__FILENAME__ = test
"""test utilities
(part of web.py)
"""
import unittest
import sys, os
import web

TestCase = unittest.TestCase
TestSuite = unittest.TestSuite

def load_modules(names):
    return [__import__(name, None, None, "x") for name in names]

def module_suite(module, classnames=None):
    """Makes a suite from a module."""
    if classnames:
        return unittest.TestLoader().loadTestsFromNames(classnames, module)
    elif hasattr(module, 'suite'):
        return module.suite()
    else:
        return unittest.TestLoader().loadTestsFromModule(module)

def doctest_suite(module_names):
    """Makes a test suite from doctests."""
    import doctest
    suite = TestSuite()
    for mod in load_modules(module_names):
        suite.addTest(doctest.DocTestSuite(mod))
    return suite
    
def suite(module_names):
    """Creates a suite from multiple modules."""
    suite = TestSuite()
    for mod in load_modules(module_names):
        suite.addTest(module_suite(mod))
    return suite

def runTests(suite):
    runner = unittest.TextTestRunner()
    return runner.run(suite)

def main(suite=None):
    if not suite:
        main_module = __import__('__main__')
        # allow command line switches
        args = [a for a in sys.argv[1:] if not a.startswith('-')]
        suite = module_suite(main_module, args or None)

    result = runTests(suite)
    sys.exit(not result.wasSuccessful())


########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
"""
General Utilities
(part of web.py)
"""

__all__ = [
  "Storage", "storage", "storify", 
  "iters", 
  "rstrips", "lstrips", "strips", 
  "safeunicode", "safestr", "utf8",
  "TimeoutError", "timelimit",
  "Memoize", "memoize",
  "re_compile", "re_subm",
  "group",
  "IterBetter", "iterbetter",
  "dictreverse", "dictfind", "dictfindall", "dictincr", "dictadd",
  "listget", "intget", "datestr",
  "numify", "denumify", "commify", "dateify",
  "nthstr",
  "CaptureStdout", "capturestdout", "Profile", "profile",
  "tryall",
  "ThreadedDict", "threadeddict",
  "autoassign",
  "to36",
  "safemarkdown",
  "sendmail"
]

import re, sys, time, threading

try:
    import subprocess
except ImportError: 
    subprocess = None

try: import datetime
except ImportError: pass

class Storage(dict):
    """
    A Storage object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`.
    
        >>> o = storage(a=1)
        >>> o.a
        1
        >>> o['a']
        1
        >>> o.a = 2
        >>> o['a']
        2
        >>> del o.a
        >>> o.a
        Traceback (most recent call last):
            ...
        AttributeError: 'a'
    
    """
    def __getattr__(self, key): 
        try:
            return self[key]
        except KeyError, k:
            raise AttributeError, k
    
    def __setattr__(self, key, value): 
        self[key] = value
    
    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, k:
            raise AttributeError, k
    
    def __repr__(self):     
        return '<Storage ' + dict.__repr__(self) + '>'

storage = Storage

def storify(mapping, *requireds, **defaults):
    """
    Creates a `storage` object from dictionary `mapping`, raising `KeyError` if
    d doesn't have all of the keys in `requireds` and using the default 
    values for keys found in `defaults`.

    For example, `storify({'a':1, 'c':3}, b=2, c=0)` will return the equivalent of
    `storage({'a':1, 'b':2, 'c':3})`.
    
    If a `storify` value is a list (e.g. multiple values in a form submission), 
    `storify` returns the last element of the list, unless the key appears in 
    `defaults` as a list. Thus:
    
        >>> storify({'a':[1, 2]}).a
        2
        >>> storify({'a':[1, 2]}, a=[]).a
        [1, 2]
        >>> storify({'a':1}, a=[]).a
        [1]
        >>> storify({}, a=[]).a
        []
    
    Similarly, if the value has a `value` attribute, `storify will return _its_
    value, unless the key appears in `defaults` as a dictionary.
    
        >>> storify({'a':storage(value=1)}).a
        1
        >>> storify({'a':storage(value=1)}, a={}).a
        <Storage {'value': 1}>
        >>> storify({}, a={}).a
        {}
        
    Optionally, keyword parameter `_unicode` can be passed to convert all values to unicode.
    
        >>> storify({'x': 'a'}, _unicode=True)
        <Storage {'x': u'a'}>
        >>> storify({'x': storage(value='a')}, x={}, _unicode=True)
        <Storage {'x': <Storage {'value': 'a'}>}>
        >>> storify({'x': storage(value='a')}, _unicode=True)
        <Storage {'x': u'a'}>
    """
    _unicode = defaults.pop('_unicode', False)
    def unicodify(s):
        if _unicode and isinstance(s, str): return safeunicode(s)
        else: return s
        
    def getvalue(x):
        if hasattr(x, 'value'):
            return unicodify(x.value)
        else:
            return unicodify(x)
    
    stor = Storage()
    for key in requireds + tuple(mapping.keys()):
        value = mapping[key]
        if isinstance(value, list):
            if isinstance(defaults.get(key), list):
                value = [getvalue(x) for x in value]
            else:
                value = value[-1]
        if not isinstance(defaults.get(key), dict):
            value = getvalue(value)
        if isinstance(defaults.get(key), list) and not isinstance(value, list):
            value = [value]
        setattr(stor, key, value)

    for (key, value) in defaults.iteritems():
        result = value
        if hasattr(stor, key): 
            result = stor[key]
        if value == () and not isinstance(result, tuple): 
            result = (result,)
        setattr(stor, key, result)
    
    return stor

iters = [list, tuple]
import __builtin__
if hasattr(__builtin__, 'set'):
    iters.append(set)
if hasattr(__builtin__, 'frozenset'):
    iters.append(set)
if sys.version_info < (2,6): # sets module deprecated in 2.6
    try:
        from sets import Set
        iters.append(Set)
    except ImportError: 
        pass
    
class _hack(tuple): pass
iters = _hack(iters)
iters.__doc__ = """
A list of iterable items (like lists, but not strings). Includes whichever
of lists, tuples, sets, and Sets are available in this version of Python.
"""

def _strips(direction, text, remove):
    if direction == 'l': 
        if text.startswith(remove): 
            return text[len(remove):]
    elif direction == 'r':
        if text.endswith(remove):   
            return text[:-len(remove)]
    else: 
        raise ValueError, "Direction needs to be r or l."
    return text

def rstrips(text, remove):
    """
    removes the string `remove` from the right of `text`

        >>> rstrips("foobar", "bar")
        'foo'
    
    """
    return _strips('r', text, remove)

def lstrips(text, remove):
    """
    removes the string `remove` from the left of `text`
    
        >>> lstrips("foobar", "foo")
        'bar'
    
    """
    return _strips('l', text, remove)

def strips(text, remove):
    """
    removes the string `remove` from the both sides of `text`

        >>> strips("foobarfoo", "foo")
        'bar'
    
    """
    return rstrips(lstrips(text, remove), remove)

def safeunicode(obj, encoding='utf-8'):
    r"""
    Converts any given object to unicode string.
    
        >>> safeunicode('hello')
        u'hello'
        >>> safeunicode(2)
        u'2'
        >>> safeunicode('\xe1\x88\xb4')
        u'\u1234'
    """
    if isinstance(obj, unicode):
        return obj
    elif isinstance(obj, str):
        return obj.decode(encoding)
    else:
        if hasattr(obj, '__unicode__'):
            return unicode(obj)
        else:
            return str(obj).decode(encoding)
    
def safestr(obj, encoding='utf-8'):
    r"""
    Converts any given object to utf-8 encoded string. 
    
        >>> safestr('hello')
        'hello'
        >>> safestr(u'\u1234')
        '\xe1\x88\xb4'
        >>> safestr(2)
        '2'
    """
    if isinstance(obj, unicode):
        return obj.encode('utf-8')
    elif isinstance(obj, str):
        return obj
    else:
        return str(obj)

# for backward-compatibility
utf8 = safestr
    
class TimeoutError(Exception): pass
def timelimit(timeout):
    """
    A decorator to limit a function to `timeout` seconds, raising `TimeoutError`
    if it takes longer.
    
        >>> import time
        >>> def meaningoflife():
        ...     time.sleep(.2)
        ...     return 42
        >>> 
        >>> timelimit(.1)(meaningoflife)()
        Traceback (most recent call last):
            ...
        TimeoutError: took too long
        >>> timelimit(1)(meaningoflife)()
        42

    _Caveat:_ The function isn't stopped after `timeout` seconds but continues 
    executing in a separate thread. (There seems to be no way to kill a thread.)

    inspired by <http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/473878>
    """
    def _1(function):
        def _2(*args, **kw):
            class Dispatch(threading.Thread):
                def __init__(self):
                    threading.Thread.__init__(self)
                    self.result = None
                    self.error = None

                    self.setDaemon(True)
                    self.start()

                def run(self):
                    try:
                        self.result = function(*args, **kw)
                    except:
                        self.error = sys.exc_info()

            c = Dispatch()
            c.join(timeout)
            if c.isAlive():
                raise TimeoutError, 'took too long'
            if c.error:
                raise c.error[0], c.error[1]
            return c.result
        return _2
    return _1

class Memoize:
    """
    'Memoizes' a function, caching its return values for each input.
    
        >>> import time
        >>> def meaningoflife():
        ...     time.sleep(.2)
        ...     return 42
        >>> fastlife = memoize(meaningoflife)
        >>> meaningoflife()
        42
        >>> timelimit(.1)(meaningoflife)()
        Traceback (most recent call last):
            ...
        TimeoutError: took too long
        >>> fastlife()
        42
        >>> timelimit(.1)(fastlife)()
        42
    
    """
    def __init__(self, func): 
        self.func = func
        self.cache = {}
    def __call__(self, *args, **keywords):
        key = (args, tuple(keywords.items()))
        if key not in self.cache: 
            self.cache[key] = self.func(*args, **keywords)
        return self.cache[key]

memoize = Memoize

re_compile = memoize(re.compile) #@@ threadsafe?
re_compile.__doc__ = """
A memoized version of re.compile.
"""

class _re_subm_proxy:
    def __init__(self): 
        self.match = None
    def __call__(self, match): 
        self.match = match
        return ''

def re_subm(pat, repl, string):
    """
    Like re.sub, but returns the replacement _and_ the match object.
    
        >>> t, m = re_subm('g(oo+)fball', r'f\\1lish', 'goooooofball')
        >>> t
        'foooooolish'
        >>> m.groups()
        ('oooooo',)
    """
    compiled_pat = re_compile(pat)
    proxy = _re_subm_proxy()
    compiled_pat.sub(proxy.__call__, string)
    return compiled_pat.sub(repl, string), proxy.match

def group(seq, size): 
    """
    Returns an iterator over a series of lists of length size from iterable.

        >>> list(group([1,2,3,4], 2))
        [[1, 2], [3, 4]]
    """
    if not hasattr(seq, 'next'):  
        seq = iter(seq)
    while True: 
        yield [seq.next() for i in xrange(size)]

class IterBetter:
    """
    Returns an object that can be used as an iterator 
    but can also be used via __getitem__ (although it 
    cannot go backwards -- that is, you cannot request 
    `iterbetter[0]` after requesting `iterbetter[1]`).
    
        >>> import itertools
        >>> c = iterbetter(itertools.count())
        >>> c[1]
        1
        >>> c[5]
        5
        >>> c[3]
        Traceback (most recent call last):
            ...
        IndexError: already passed 3
    """
    def __init__(self, iterator): 
        self.i, self.c = iterator, 0
    def __iter__(self): 
        while 1:    
            yield self.i.next()
            self.c += 1
    def __getitem__(self, i):
        #todo: slices
        if i < self.c: 
            raise IndexError, "already passed "+str(i)
        try:
            while i > self.c: 
                self.i.next()
                self.c += 1
            # now self.c == i
            self.c += 1
            return self.i.next()
        except StopIteration: 
            raise IndexError, str(i)
iterbetter = IterBetter

def dictreverse(mapping):
    """
    Returns a new dictionary with keys and values swapped.
    
        >>> dictreverse({1: 2, 3: 4})
        {2: 1, 4: 3}
    """
    return dict([(value, key) for (key, value) in mapping.iteritems()])

def dictfind(dictionary, element):
    """
    Returns a key whose value in `dictionary` is `element` 
    or, if none exists, None.
    
        >>> d = {1:2, 3:4}
        >>> dictfind(d, 4)
        3
        >>> dictfind(d, 5)
    """
    for (key, value) in dictionary.iteritems():
        if element is value: 
            return key

def dictfindall(dictionary, element):
    """
    Returns the keys whose values in `dictionary` are `element`
    or, if none exists, [].
    
        >>> d = {1:4, 3:4}
        >>> dictfindall(d, 4)
        [1, 3]
        >>> dictfindall(d, 5)
        []
    """
    res = []
    for (key, value) in dictionary.iteritems():
        if element is value:
            res.append(key)
    return res

def dictincr(dictionary, element):
    """
    Increments `element` in `dictionary`, 
    setting it to one if it doesn't exist.
    
        >>> d = {1:2, 3:4}
        >>> dictincr(d, 1)
        3
        >>> d[1]
        3
        >>> dictincr(d, 5)
        1
        >>> d[5]
        1
    """
    dictionary.setdefault(element, 0)
    dictionary[element] += 1
    return dictionary[element]

def dictadd(*dicts):
    """
    Returns a dictionary consisting of the keys in the argument dictionaries.
    If they share a key, the value from the last argument is used.
    
        >>> dictadd({1: 0, 2: 0}, {2: 1, 3: 1})
        {1: 0, 2: 1, 3: 1}
    """
    result = {}
    for dct in dicts:
        result.update(dct)
    return result

def listget(lst, ind, default=None):
    """
    Returns `lst[ind]` if it exists, `default` otherwise.
    
        >>> listget(['a'], 0)
        'a'
        >>> listget(['a'], 1)
        >>> listget(['a'], 1, 'b')
        'b'
    """
    if len(lst)-1 < ind: 
        return default
    return lst[ind]

def intget(integer, default=None):
    """
    Returns `integer` as an int or `default` if it can't.
    
        >>> intget('3')
        3
        >>> intget('3a')
        >>> intget('3a', 0)
        0
    """
    try:
        return int(integer)
    except (TypeError, ValueError):
        return default

def datestr(then, now=None):
    """
    Converts a (UTC) datetime object to a nice string representation.
    
        >>> from datetime import datetime, timedelta
        >>> d = datetime(1970, 5, 1)
        >>> datestr(d, now=d)
        '0 microseconds ago'
        >>> for t, v in {
        ...   timedelta(microseconds=1): '1 microsecond ago',
        ...   timedelta(microseconds=2): '2 microseconds ago',
        ...   -timedelta(microseconds=1): '1 microsecond from now',
        ...   -timedelta(microseconds=2): '2 microseconds from now',
        ...   timedelta(microseconds=2000): '2 milliseconds ago',
        ...   timedelta(seconds=2): '2 seconds ago',
        ...   timedelta(seconds=2*60): '2 minutes ago',
        ...   timedelta(seconds=2*60*60): '2 hours ago',
        ...   timedelta(days=2): '2 days ago',
        ... }.iteritems():
        ...     assert datestr(d, now=d+t) == v
        >>> datestr(datetime(1970, 1, 1), now=d)
        'January  1'
        >>> datestr(datetime(1969, 1, 1), now=d)
        'January  1, 1969'
        >>> datestr(datetime(1970, 6, 1), now=d)
        'June  1, 1970'
    """
    def agohence(n, what, divisor=None):
        if divisor: n = n // divisor

        out = str(abs(n)) + ' ' + what       # '2 day'
        if abs(n) != 1: out += 's'           # '2 days'
        out += ' '                           # '2 days '
        if n < 0:
            out += 'from now'
        else:
            out += 'ago'
        return out                           # '2 days ago'

    oneday = 24 * 60 * 60

    if not now: now = datetime.datetime.utcnow()
    if type(now).__name__ == "DateTime":
        now = datetime.datetime.fromtimestamp(now)
    if type(then).__name__ == "DateTime":
        then = datetime.datetime.fromtimestamp(then)
    delta = now - then
    deltaseconds = int(delta.days * oneday + delta.seconds + delta.microseconds * 1e-06)
    deltadays = abs(deltaseconds) // oneday
    if deltaseconds < 0: deltadays *= -1 # fix for oddity of floor

    if deltadays:
        if abs(deltadays) < 4:
            return agohence(deltadays, 'day')

        out = then.strftime('%B %e') # e.g. 'June 13'
        if then.year != now.year or deltadays < 0:
            out += ', %s' % then.year
        return out

    if int(deltaseconds):
        if abs(deltaseconds) > (60 * 60):
            return agohence(deltaseconds, 'hour', 60 * 60)
        elif abs(deltaseconds) > 60:
            return agohence(deltaseconds, 'minute', 60)
        else:
            return agohence(deltaseconds, 'second')

    deltamicroseconds = delta.microseconds
    if delta.days: deltamicroseconds = int(delta.microseconds - 1e6) # datetime oddity
    if abs(deltamicroseconds) > 1000:
        return agohence(deltamicroseconds, 'millisecond', 1000)

    return agohence(deltamicroseconds, 'microsecond')

def numify(string):
    """
    Removes all non-digit characters from `string`.
    
        >>> numify('800-555-1212')
        '8005551212'
        >>> numify('800.555.1212')
        '8005551212'
    
    """
    return ''.join([c for c in str(string) if c.isdigit()])

def denumify(string, pattern):
    """
    Formats `string` according to `pattern`, where the letter X gets replaced
    by characters from `string`.
    
        >>> denumify("8005551212", "(XXX) XXX-XXXX")
        '(800) 555-1212'
    
    """
    out = []
    for c in pattern:
        if c == "X":
            out.append(string[0])
            string = string[1:]
        else:
            out.append(c)
    return ''.join(out)

def commify(n):
    """
    Add commas to an integer `n`.

        >>> commify(1)
        '1'
        >>> commify(123)
        '123'
        >>> commify(1234)
        '1,234'
        >>> commify(1234567890)
        '1,234,567,890'
        >>> commify(None)
        >>>
    
    """
    if n is None: return None
    r = []
    for i, c in enumerate(reversed(str(n))):
        if i and (not (i % 3)):
            r.insert(0, ',')
        r.insert(0, c)
    return ''.join(r)

def dateify(datestring):
    """
    Formats a numified `datestring` properly.
    """
    return denumify(datestring, "XXXX-XX-XX XX:XX:XX")


def nthstr(n):
    """
    Formats an ordinal.
    Doesn't handle negative numbers.

        >>> nthstr(1)
        '1st'
        >>> nthstr(0)
        '0th'
        >>> [nthstr(x) for x in [2, 3, 4, 5, 10, 11, 12, 13, 14, 15]]
        ['2nd', '3rd', '4th', '5th', '10th', '11th', '12th', '13th', '14th', '15th']
        >>> [nthstr(x) for x in [91, 92, 93, 94, 99, 100, 101, 102]]
        ['91st', '92nd', '93rd', '94th', '99th', '100th', '101st', '102nd']
        >>> [nthstr(x) for x in [111, 112, 113, 114, 115]]
        ['111th', '112th', '113th', '114th', '115th']

    """
    
    assert n >= 0
    if n % 100 in [11, 12, 13]: return '%sth' % n
    return {1: '%sst', 2: '%snd', 3: '%srd'}.get(n % 10, '%sth') % n

def cond(predicate, consequence, alternative=None):
    """
    Function replacement for if-else to use in expressions.
        
        >>> x = 2
        >>> cond(x % 2 == 0, "even", "odd")
        'even'
        >>> cond(x % 2 == 0, "even", "odd") + '_row'
        'even_row'
    """
    if predicate:
        return consequence
    else:
        return alternative

class CaptureStdout:
    """
    Captures everything `func` prints to stdout and returns it instead.
    
        >>> def idiot():
        ...     print "foo"
        >>> capturestdout(idiot)()
        'foo\\n'
    
    **WARNING:** Not threadsafe!
    """
    def __init__(self, func): 
        self.func = func
    def __call__(self, *args, **keywords):
        from cStringIO import StringIO
        # Not threadsafe!
        out = StringIO()
        oldstdout = sys.stdout
        sys.stdout = out
        try: 
            self.func(*args, **keywords)
        finally: 
            sys.stdout = oldstdout
        return out.getvalue()

capturestdout = CaptureStdout

class Profile:
    """
    Profiles `func` and returns a tuple containing its output
    and a string with human-readable profiling information.
        
        >>> import time
        >>> out, inf = profile(time.sleep)(.001)
        >>> out
        >>> inf[:10].strip()
        'took 0.0'
    """
    def __init__(self, func): 
        self.func = func
    def __call__(self, *args): ##, **kw):   kw unused
        import hotshot, hotshot.stats, tempfile ##, time already imported
        temp = tempfile.NamedTemporaryFile()
        prof = hotshot.Profile(temp.name)

        stime = time.time()
        result = prof.runcall(self.func, *args)
        stime = time.time() - stime
        prof.close()

        import cStringIO
        out = cStringIO.StringIO()
        stats = hotshot.stats.load(temp.name)
        stats.stream = out
        stats.strip_dirs()
        stats.sort_stats('time', 'calls')
        stats.print_stats(40)
        stats.print_callers()

        x =  '\n\ntook '+ str(stime) + ' seconds\n'
        x += out.getvalue()

        return result, x

profile = Profile


import traceback
# hack for compatibility with Python 2.3:
if not hasattr(traceback, 'format_exc'):
    from cStringIO import StringIO
    def format_exc(limit=None):
        strbuf = StringIO()
        traceback.print_exc(limit, strbuf)
        return strbuf.getvalue()
    traceback.format_exc = format_exc

def tryall(context, prefix=None):
    """
    Tries a series of functions and prints their results. 
    `context` is a dictionary mapping names to values; 
    the value will only be tried if it's callable.
    
        >>> tryall(dict(j=lambda: True))
        j: True
        ----------------------------------------
        results:
           True: 1

    For example, you might have a file `test/stuff.py` 
    with a series of functions testing various things in it. 
    At the bottom, have a line:

        if __name__ == "__main__": tryall(globals())

    Then you can run `python test/stuff.py` and get the results of 
    all the tests.
    """
    context = context.copy() # vars() would update
    results = {}
    for (key, value) in context.iteritems():
        if not hasattr(value, '__call__'): 
            continue
        if prefix and not key.startswith(prefix): 
            continue
        print key + ':',
        try:
            r = value()
            dictincr(results, r)
            print r
        except:
            print 'ERROR'
            dictincr(results, 'ERROR')
            print '   ' + '\n   '.join(traceback.format_exc().split('\n'))
        
    print '-'*40
    print 'results:'
    for (key, value) in results.iteritems():
        print ' '*2, str(key)+':', value
        
class ThreadedDict:
    """
    Thread local storage.
    
        >>> d = ThreadedDict()
        >>> d.x = 1
        >>> d.x
        1
        >>> import threading
        >>> def f(): d.x = 2
        >>> t = threading.Thread(target=f)
        >>> t.start()
        >>> t.join()
        >>> d.x
        1
    """
    def __getattr__(self, key):
        return getattr(self._getd(), key)

    def __setattr__(self, key, value):
        return setattr(self._getd(), key, value)

    def __delattr__(self, key):
        return delattr(self._getd(), key)

    def __hash__(self): 
        return id(self)

    def _getd(self):
        t = threading.currentThread()
        if not hasattr(t, '_d'):
            # using __dict__ of thread as thread local storage
            t._d = {}

        # there could be multiple instances of ThreadedDict.
        # use self as key
        if self not in t._d:
            t._d[self] = storage()
        return t._d[self]

threadeddict = ThreadedDict

def autoassign(self, locals):
    """
    Automatically assigns local variables to `self`.
    
        >>> self = storage()
        >>> autoassign(self, dict(a=1, b=2))
        >>> self
        <Storage {'a': 1, 'b': 2}>
    
    Generally used in `__init__` methods, as in:

        def __init__(self, foo, bar, baz=1): autoassign(self, locals())
    """
    for (key, value) in locals.iteritems():
        if key == 'self': 
            continue
        setattr(self, key, value)

def to36(q):
    """
    Converts an integer to base 36 (a useful scheme for human-sayable IDs).
    
        >>> to36(35)
        'z'
        >>> to36(119292)
        '2k1o'
        >>> int(to36(939387374), 36)
        939387374
        >>> to36(0)
        '0'
        >>> to36(-393)
        Traceback (most recent call last):
            ... 
        ValueError: must supply a positive integer
    
    """
    if q < 0: raise ValueError, "must supply a positive integer"
    letters = "0123456789abcdefghijklmnopqrstuvwxyz"
    converted = []
    while q != 0:
        q, r = divmod(q, 36)
        converted.insert(0, letters[r])
    return "".join(converted) or '0'


r_url = re_compile('(?<!\()(http://(\S+))')
def safemarkdown(text):
    """
    Converts text to HTML following the rules of Markdown, but blocking any
    outside HTML input, so that only the things supported by Markdown
    can be used. Also converts raw URLs to links.

    (requires [markdown.py](http://webpy.org/markdown.py))
    """
    from markdown import markdown
    if text:
        text = text.replace('<', '&lt;')
        # TODO: automatically get page title?
        text = r_url.sub(r'<\1>', text)
        text = markdown(text)
        return text

def sendmail(from_address, to_address, subject, message, headers=None, **kw):
    """
    Sends the email message `message` with mail and envelope headers
    for from `from_address_` to `to_address` with `subject`. 
    Additional email headers can be specified with the dictionary 
    `headers.

    If `web.config.smtp_server` is set, it will send the message
    to that SMTP server. Otherwise it will look for 
    `/usr/sbin/sendmail`, the typical location for the sendmail-style
    binary. To use sendmail from a different path, set `web.config.sendmail_path`.
    """
    try:
        import webapi
    except ImportError:
        webapi = Storage(config=Storage())
    
    if headers is None: headers = {}
    
    cc = kw.get('cc', [])
    bcc = kw.get('bcc', [])
    
    def listify(x):
        if not isinstance(x, list):
            return [safestr(x)]
        else:
            return [safestr(a) for a in x]

    from_address = safestr(from_address)

    to_address = listify(to_address)
    cc = listify(cc)
    bcc = listify(bcc)

    recipients = to_address + cc + bcc
    
    headers = dictadd({
      'MIME-Version': '1.0',
      'Content-Type': 'text/plain; charset=UTF-8',
      'Content-Disposition': 'inline',
      'From': from_address,
      'To': ", ".join(to_address),
      'Subject': subject
    }, headers)

    if cc:
        headers['Cc'] = ", ".join(cc)
    
    import email.Utils
    from_address = email.Utils.parseaddr(from_address)[1]
    recipients = [email.Utils.parseaddr(r)[1] for r in recipients]
    message = ('\n'.join([safestr('%s: %s' % x) for x in headers.iteritems()])
      + "\n\n" +  safestr(message))

    if webapi.config.get('smtp_server'):
        server = webapi.config.get('smtp_server')
        port = webapi.config.get('smtp_port', 0)
        username = webapi.config.get('smtp_username') 
        password = webapi.config.get('smtp_password')
        debug_level = webapi.config.get('smtp_debuglevel', None)
        starttls = webapi.config.get('smtp_starttls', False)

        import smtplib
        smtpserver = smtplib.SMTP(server, port)

        if debug_level:
            smtpserver.set_debuglevel(debug_level)

        if starttls:
            smtpserver.ehlo()
            smtpserver.starttls()
            smtpserver.ehlo()

        if username and password:
            smtpserver.login(username, password)

        smtpserver.sendmail(from_address, recipients, message)
        smtpserver.quit()
    else:
        sendmail = webapi.config.get('sendmail_path', '/usr/sbin/sendmail')
        
        assert not from_address.startswith('-'), 'security'
        for r in recipients:
            assert not r.startswith('-'), 'security'
                

        if subprocess:
            p = subprocess.Popen(['/usr/sbin/sendmail', '-f', from_address] + recipients, stdin=subprocess.PIPE)
            p.stdin.write(message)
            p.stdin.close()
            p.wait()
        else:
            i, o = os.popen2(["/usr/lib/sendmail", '-f', from_address] + recipients)
            i.write(message)
            i.close()
            o.close()
            del i, o

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = webapi
"""
Web API (wrapper around WSGI)
(from web.py)
"""

__all__ = [
    "config",
    "header", "debug",
    "input", "data",
    "setcookie", "cookies",
    "ctx", 
    "HTTPError", 
    "BadRequest", "NotFound", "Gone", "InternalError",
    "badrequest", "notfound", "gone", "internalerror",
    "Redirect", "Found", "SeeOther", "TempRedirect",
    "redirect", "found", "seeother", "tempredirect", 
    "NoMethod", "nomethod",
]

import sys, cgi, Cookie, pprint, urlparse, urllib
from utils import storage, storify, threadeddict, dictadd, intget, utf8

config = storage()
config.__doc__ = """
A configuration object for various aspects of web.py.

`debug`
   : when True, enables reloading, disabled template caching and sets internalerror to debugerror.
"""

class HTTPError(Exception):
    def __init__(self, status, headers, data=""):
        ctx.status = status
        for k, v in headers.items():
            header(k, v)
        self.data = data
        Exception.__init__(self, status)

class BadRequest(HTTPError):
    """`400 Bad Request` error."""
    message = "bad request"
    def __init__(self):
        status = "400 Bad Request"
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, self.message)

badrequest = BadRequest

class _NotFound(HTTPError):
    """`404 Not Found` error."""
    message = "not found"
    def __init__(self, message=None):
        status = '404 Not Found'
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, message or self.message)

def NotFound(message=None):
    """Returns HTTPError with '404 Not Found' error from the active application.
    """
    if message:
        return _NotFound(message)
    elif ctx.get('app_stack'):
        return ctx.app_stack[-1].notfound()
    else:
        return _NotFound()

notfound = NotFound

class Gone(HTTPError):
    """`410 Gone` error."""
    message = "gone"
    def __init__(self):
        status = '410 Gone'
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, self.message)

gone = Gone

class Redirect(HTTPError):
    """A `301 Moved Permanently` redirect."""
    def __init__(self, url, status='301 Moved Permanently', absolute=False):
        """
        Returns a `status` redirect to the new URL. 
        `url` is joined with the base URL so that things like 
        `redirect("about") will work properly.
        """
        newloc = urlparse.urljoin(ctx.path, url)

        if newloc.startswith('/'):
            if absolute:
                home = ctx.realhome
            else:
                home = ctx.home
            newloc = home + newloc

        headers = {
            'Content-Type': 'text/html',
            'Location': newloc
        }
        HTTPError.__init__(self, status, headers, "")

redirect = Redirect

class Found(Redirect):
    """A `302 Found` redirect."""
    def __init__(self, url, absolute=False):
        Redirect.__init__(self, url, '302 Found', absolute=absolute)

found = Found

class SeeOther(Redirect):
    """A `303 See Other` redirect."""
    def __init__(self, url, absolute=False):
        Redirect.__init__(self, url, '303 See Other', absolute=absolute)
    
seeother = SeeOther

class TempRedirect(Redirect):
    """A `307 Temporary Redirect` redirect."""
    def __init__(self, url, absolute=False):
        Redirect.__init__(self, url, '307 Temporary Redirect', absolute=absolute)

tempredirect = TempRedirect

class NoMethod(HTTPError):
    """A `405 Method Not Allowed` error."""
    def __init__(self, cls=None):
        status = '405 Method Not Allowed'
        headers = {}
        headers['Content-Type'] = 'text/html'
        
        methods = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE']
        if cls:
            methods = [method for method in methods if hasattr(cls, method)]

        headers['Allow'] = ', '.join(methods)
        data = None
        HTTPError.__init__(self, status, headers, data)
        
nomethod = NoMethod

class _InternalError(HTTPError):
    """500 Internal Server Error`."""
    message = "internal server error"
    
    def __init__(self, message=None):
        status = '500 Internal Server Error'
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, message or self.message)

def InternalError(message=None):
    """Returns HTTPError with '500 internal error' error from the active application.
    """
    if message:
        return _InternalError(message)
    elif ctx.get('app_stack'):
        return ctx.app_stack[-1].internalerror()
    else:
        return _InternalError()

internalerror = InternalError

def header(hdr, value, unique=False):
    """
    Adds the header `hdr: value` with the response.
    
    If `unique` is True and a header with that name already exists,
    it doesn't add a new one. 
    """
    hdr, value = utf8(hdr), utf8(value)
    # protection against HTTP response splitting attack
    if '\n' in hdr or '\r' in hdr or '\n' in value or '\r' in value:
        raise ValueError, 'invalid characters in header'
        
    if unique is True:
        for h, v in ctx.headers:
            if h.lower() == hdr.lower(): return
    
    ctx.headers.append((hdr, value))

def input(*requireds, **defaults):
    """
    Returns a `storage` object with the GET and POST arguments. 
    See `storify` for how `requireds` and `defaults` work.
    """
    from cStringIO import StringIO
    def dictify(fs): 
        # hack to make web.input work with enctype='text/plain.
        if fs.list is None:
            fs.list = [] 

        return dict([(k, fs[k]) for k in fs.keys()])
    
    _method = defaults.pop('_method', 'both')
    
    e = ctx.env.copy()
    a = b = {}
    
    if _method.lower() in ['both', 'post', 'put']:
        if e['REQUEST_METHOD'] in ['POST', 'PUT']:
            if e.get('CONTENT_TYPE', '').lower().startswith('multipart/'):
                # since wsgi.input is directly passed to cgi.FieldStorage, 
                # it can not be called multiple times. Saving the FieldStorage
                # object in ctx to allow calling web.input multiple times.
                a = ctx.get('_fieldstorage')
                if not a:
                    fp = e['wsgi.input']
                    a = cgi.FieldStorage(fp=fp, environ=e, keep_blank_values=1)
                    ctx._fieldstorage = a
            else:
                fp = StringIO(data())
                a = cgi.FieldStorage(fp=fp, environ=e, keep_blank_values=1)
            a = dictify(a)

    if _method.lower() in ['both', 'get']:
        e['REQUEST_METHOD'] = 'GET'
        b = dictify(cgi.FieldStorage(environ=e, keep_blank_values=1))

    out = dictadd(b, a)
    try:
        defaults.setdefault('_unicode', True) # force unicode conversion by default.
        return storify(out, *requireds, **defaults)
    except KeyError:
        raise badrequest()

def data():
    """Returns the data sent with the request."""
    if 'data' not in ctx:
        cl = intget(ctx.env.get('CONTENT_LENGTH'), 0)
        ctx.data = ctx.env['wsgi.input'].read(cl)
    return ctx.data

def setcookie(name, value, expires="", domain=None, secure=False):
    """Sets a cookie."""
    if expires < 0: 
        expires = -1000000000 
    kargs = {'expires': expires, 'path':'/'}
    if domain: 
        kargs['domain'] = domain
    if secure:
        kargs['secure'] = secure
    # @@ should we limit cookies to a different path?
    cookie = Cookie.SimpleCookie()
    cookie[name] = urllib.quote(utf8(value))
    for key, val in kargs.iteritems(): 
        cookie[name][key] = val
    header('Set-Cookie', cookie.items()[0][1].OutputString())

def cookies(*requireds, **defaults):
    """
    Returns a `storage` object with all the cookies in it.
    See `storify` for how `requireds` and `defaults` work.
    """
    cookie = Cookie.SimpleCookie()
    cookie.load(ctx.env.get('HTTP_COOKIE', ''))
    try:
        d = storify(cookie, *requireds, **defaults)
        for k, v in d.items():
            d[k] = v and urllib.unquote(v)
        return d
    except KeyError:
        badrequest()
        raise StopIteration

def debug(*args):
    """
    Prints a prettyprinted version of `args` to stderr.
    """
    try: 
        out = ctx.environ['wsgi.errors']
    except: 
        out = sys.stderr
    for arg in args:
        print >> out, pprint.pformat(arg)
    return ''

def _debugwrite(x):
    try: 
        out = ctx.environ['wsgi.errors']
    except: 
        out = sys.stderr
    out.write(x)
debug.write = _debugwrite

ctx = context = threadeddict()

ctx.__doc__ = """
A `storage` object containing various information about the request:
  
`environ` (aka `env`)
   : A dictionary containing the standard WSGI environment variables.

`host`
   : The domain (`Host` header) requested by the user.

`home`
   : The base path for the application.

`ip`
   : The IP address of the requester.

`method`
   : The HTTP method used.

`path`
   : The path request.
   
`query`
   : If there are no query arguments, the empty string. Otherwise, a `?` followed
     by the query string.

`fullpath`
   : The full path requested, including query arguments (`== path + query`).

### Response Data

`status` (default: "200 OK")
   : The status code to be used in the response.

`headers`
   : A list of 2-tuples to be used in the response.

`output`
   : A string to be used as the response.
"""

########NEW FILE########
__FILENAME__ = webopenid
"""openid.py: an openid library for web.py

Notes:

 - This will create a file called .openid_secret_key in the 
   current directory with your secret key in it. If someone 
   has access to this file they can log in as any user. And 
   if the app can't find this file for any reason (e.g. you 
   moved the app somewhere else) then each currently logged 
   in user will get logged out.

 - State must be maintained through the entire auth process 
   -- this means that if you have multiple web.py processes 
   serving one set of URLs or if you restart your app often 
   then log ins will fail. You have to replace sessions and 
   store for things to work.

 - We set cookies starting with "openid_".

"""

import os
import random
import hmac
import __init__ as web
import openid.consumer.consumer
import openid.store.memstore

sessions = {}
store = openid.store.memstore.MemoryStore()

def _secret():
    try:
        secret = file('.openid_secret_key').read()
    except IOError:
        # file doesn't exist
        secret = os.urandom(20)
        file('.openid_secret_key', 'w').write(secret)
    return secret

def _hmac(identity_url):
    return hmac.new(_secret(), identity_url).hexdigest()

def _random_session():
    n = random.random()
    while n in sessions:
        n = random.random()
    n = str(n)
    return n

def status():
    oid_hash = web.cookies().get('openid_identity_hash', '').split(',', 1)
    if len(oid_hash) > 1:
        oid_hash, identity_url = oid_hash
        if oid_hash == _hmac(identity_url):
            return identity_url
    return None

def form(openid_loc):
    oid = status()
    if oid:
        return '''
        <form method="post" action="%s">
          <img src="http://openid.net/login-bg.gif" alt="OpenID" />
          <strong>%s</strong>
          <input type="hidden" name="action" value="logout" />
          <input type="hidden" name="return_to" value="%s" />
          <button type="submit">log out</button>
        </form>''' % (openid_loc, oid, web.ctx.fullpath)
    else:
        return '''
        <form method="post" action="%s">
          <input type="text" name="openid" value="" 
            style="background: url(http://openid.net/login-bg.gif) no-repeat; padding-left: 18px; background-position: 0 50%%;" />
          <input type="hidden" name="return_to" value="%s" />
          <button type="submit">log in</button>
        </form>''' % (openid_loc, web.ctx.fullpath)

def logout():
    web.setcookie('openid_identity_hash', '', expires=-1)

class host:
    def POST(self):
        # unlike the usual scheme of things, the POST is actually called
        # first here
        i = web.input(return_to='/')
        if i.get('action') == 'logout':
            logout()
            return web.redirect(i.return_to)

        i = web.input('openid', return_to='/')

        n = _random_session()
        sessions[n] = {'webpy_return_to': i.return_to}
        
        c = openid.consumer.consumer.Consumer(sessions[n], store)
        a = c.begin(i.openid)
        f = a.redirectURL(web.ctx.home, web.ctx.home + web.ctx.fullpath)

        web.setcookie('openid_session_id', n)
        return web.redirect(f)

    def GET(self):
        n = web.cookies('openid_session_id').openid_session_id
        web.setcookie('openid_session_id', '', expires=-1)
        return_to = sessions[n]['webpy_return_to']

        c = openid.consumer.consumer.Consumer(sessions[n], store)
        a = c.complete(web.input(), web.ctx.home + web.ctx.fullpath)

        if a.status.lower() == 'success':
            web.setcookie('openid_identity_hash', _hmac(a.identity_url) + ',' + a.identity_url)

        del sessions[n]
        return web.redirect(return_to)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI Utilities
(from web.py)
"""

import os, sys

import http
import webapi as web
from utils import listget
from net import validaddr, validip
import httpserver
    
def runfcgi(func, addr=('localhost', 8000)):
    """Runs a WSGI function as a FastCGI server."""
    import flup.server.fcgi as flups
    return flups.WSGIServer(func, multiplexed=True, bindAddress=addr).run()

def runscgi(func, addr=('localhost', 4000)):
    """Runs a WSGI function as an SCGI server."""
    import flup.server.scgi as flups
    return flups.WSGIServer(func, bindAddress=addr).run()

def runwsgi(func):
    """
    Runs a WSGI-compatible `func` using FCGI, SCGI, or a simple web server,
    as appropriate based on context and `sys.argv`.
    """
    
    if os.environ.has_key('SERVER_SOFTWARE'): # cgi
        os.environ['FCGI_FORCE_CGI'] = 'Y'

    if (os.environ.has_key('PHP_FCGI_CHILDREN') #lighttpd fastcgi
      or os.environ.has_key('SERVER_SOFTWARE')):
        return runfcgi(func, None)
    
    if 'fcgi' in sys.argv or 'fastcgi' in sys.argv:
        args = sys.argv[1:]
        if 'fastcgi' in args: args.remove('fastcgi')
        elif 'fcgi' in args: args.remove('fcgi')
        if args:
            return runfcgi(func, validaddr(args[0]))
        else:
            return runfcgi(func, None)
    
    if 'scgi' in sys.argv:
        args = sys.argv[1:]
        args.remove('scgi')
        if args:
            return runscgi(func, validaddr(args[0]))
        else:
            return runscgi(func)
    
    return httpserver.runsimple(func, validip(listget(sys.argv, 1, '')))
    
def _is_dev_mode():
    # quick hack to check if the program is running in dev mode.
    if os.environ.has_key('SERVER_SOFTWARE') \
        or os.environ.has_key('PHP_FCGI_CHILDREN') \
        or 'fcgi' in sys.argv or 'fastcgi' in sys.argv:
            return False
    return True

# When running the builtin-server, enable debug mode if not already set.
web.config.setdefault('debug', _is_dev_mode())
########NEW FILE########
