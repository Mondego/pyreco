__FILENAME__ = errors
from django.http import Http404
from response import Response

class ErrorWrapper(object):
    def __init__(self, app, custom_404 = None, custom_500 = None):
        self.app = app
        self.error_404 = custom_404 or self.default_error_404
        self.error_500 = custom_500 or self.default_error_404
    
    def __call__(self, request):
        try:
            response = self.app(request)
        except Http404, e:
            return self.error_404(request)
        except Exception, e:
            return self.error_500(request, e)
        return response
    
    def default_error_404(self, request):
        return Response('A 404 error occurred', status=404)
    
    def default_error_500(self, request, e):
        return Response('A 500 error occurred: %r' % e, status=505)

########NEW FILE########
__FILENAME__ = middleware
from django.utils.decorators import decorator_from_middleware
from django.middleware.gzip import GZipMiddleware

GZip = decorator_from_middleware(GZipMiddleware)
del GZipMiddleware
########NEW FILE########
__FILENAME__ = response
from django.http import HttpResponse as HttpResponseOld
from Cookie import SimpleCookie

class Response(HttpResponseOld):
    _charset = 'utf8'
    def __init__(self, content='', status=None, content_type=None):
        if not content_type:
            content_type = 'text/html; charset=%s' % self._charset
        if not isinstance(content, basestring) and\
                hasattr(content, '__iter__'):
            self._container = content
            self._is_string = False
        else:
            self._container = [content]
            self._is_string = True
        self.cookies = SimpleCookie()
        if status:
            self.status_code = status
        self._headers = {'content-type': ('Content-Type', content_type)}

########NEW FILE########
__FILENAME__ = router
from django.conf.urls.defaults import patterns
from django.core import urlresolvers

class Router(object):
    """
    Convenient wrapper around Django's urlresolvers, allowing them to be used 
    from normal application code.

    from django.http import HttpResponse
    from django_openid.request_factory import RequestFactory
    from django.conf.urls.defaults import url
    router = Router(
        url('^foo/$', lambda r: HttpResponse('foo'), name='foo'),
        url('^bar/$', lambda r: HttpResponse('bar'), name='bar')
    )
    rf = RequestFactory()
    print router(rf.get('/bar/'))
    """
    def __init__(self, *urlpairs):
        self.urlpatterns = patterns('', *urlpairs)
        # for 1.0 compatibility we pass in None for urlconf_name and then
        # modify the _urlconf_module to make self hack as if its the module.
        self.resolver = urlresolvers.RegexURLResolver(r'^/', None)
        self.resolver._urlconf_module = self
    
    def handle(self, request):
        path = request.path_info
        callback, callback_args, callback_kwargs = self.resolver.resolve(path)
        return callback(request, *callback_args, **callback_kwargs)
    
    def __call__(self, request):
        return self.handle(request)
########NEW FILE########
__FILENAME__ = base
from manager import ServiceManager

class ServiceConfigurationError(Exception):
    pass


def proxy(methodname, servicemanager):
    def method(self, *args, **kwargs):
        return getattr(servicemanager.current(), methodname)(*args, **kwargs)
    return method

class ServiceMeta(type):
    def __new__(cls, name, bases, attrs):
        # First add service manager instance to attrs
        attrs['service'] = ServiceManager()
        # All attrs methods are converted in to proxies
        for key, value in attrs.items():
            if callable(value):
                # TODO: inspect funcargs, copy them and the docstring so that 
                # introspection tools will tell us correct arguments
                attrs[key] = proxy(key, attrs['service'])
        return super(ServiceMeta, cls).__new__(cls, name, bases, attrs)

class Service(object):
    __metaclass__ = ServiceMeta

########NEW FILE########
__FILENAME__ = configure
class Configure(object):
    def __init__(self, next, **kwargs):
        """
        **kwargs should have keys that are names of services and value that 
        are implementations of those services.
        """
        for name, impl in kwargs.items():
            self.get_service(name).push(impl)
    
    def get_service(self, name):
        # TODO: implement this
        pass

        
########NEW FILE########
__FILENAME__ = manager
import threading

class ServiceNotConfigured(Exception):
    # TODO: This needs to indicate WHICH service is not configured
    pass

class ServiceManager(threading.local):
    """
    A ServiceManager keeps track of the available implementations for a 
    given service, and which implementation is currently the default. It 
    provides methods for registering new implementations and pushing and 
    popping a stack representing the default implementation.
    """
    def __init__(self, default_implementation=None):
        self.clear_stack()
        if default_implementation is not None:
            self.push(default_implementation)
        
    def clear_stack(self):
        self._stack = []
    
    def push(self, impl):
        self._stack.insert(0, impl)
    
    def pop(self):
        return self._stack.pop(0)
    
    def current(self):
        if not self._stack:
            raise ServiceNotConfigured
        return self._stack[0]

########NEW FILE########
__FILENAME__ = template_response
from djng.response import Response
from django.template import loader, RequestContext

class TemplateResponse(Response):
    def __init__(self, request, template, context = None):
        self.context = context or {}
        self.template = template
        self.request = request
        super(TemplateResponse, self).__init__()
    
    def get_container(self):
        return [
            loader.get_template(self.template).render(
                RequestContext(self.request, self.context)
            )
        ]
    
    def set_container(self, *args):
        pass # ignore
    
    _container = property(get_container, set_container)

########NEW FILE########
__FILENAME__ = wsgi
# First we have to monkey-patch django.core.handlers.base because 
# get_script_name in that module has a dependency on settings which bubbles 
# up to affect WSGIRequest and WSGIHandler
from django.utils.encoding import force_unicode
def get_script_name(environ):
    script_url = environ.get('SCRIPT_URL', u'')
    if not script_url:
        script_url = environ.get('REDIRECT_URL', u'')
    if script_url:
        return force_unicode(script_url[:-len(environ.get('PATH_INFO', ''))])
    return force_unicode(environ.get('SCRIPT_NAME', u''))
from django.core.handlers import base
base.get_script_name = get_script_name

# Now on with the real code...
from django import http
from django.core.handlers.wsgi import STATUS_CODE_TEXT
from django.core.handlers.wsgi import WSGIRequest as WSGIRequestOld
import sys

class WSGIRequest(WSGIRequestOld):
    def __init__(self, environ):
        super(WSGIRequest, self).__init__(environ)
        # Setting self._encoding prevents fallback to django.conf.settings
        self._encoding = 'utf8'

class WSGIWrapper(object):
    # Changes that are always applied to a response (in this order).
    response_fixes = [
        http.fix_location_header,
        http.conditional_content_removal,
        http.fix_IE_for_attach,
        http.fix_IE_for_vary,
    ]
    def __init__(self, view):
        self.view = view
    
    def __call__(self, environ, start_response):
        request = WSGIRequest(environ)
        response = self.view(request)
        response = self.apply_response_fixes(request, response)
        try:
            status_text = STATUS_CODE_TEXT[response.status_code]
        except KeyError:
            status_text = 'UNKNOWN STATUS CODE'
        status = '%s %s' % (response.status_code, status_text)
        response_headers = [(str(k), str(v)) for k, v in response.items()]
        for c in response.cookies.values():
            response_headers.append(('Set-Cookie', str(c.output(header=''))))
        start_response(status, response_headers)
        return response
    
    def apply_response_fixes(self, request, response):
        """
        Applies each of the functions in self.response_fixes to the request 
        and response, modifying the response in the process. Returns the new
        response.
        """
        for func in self.response_fixes:
            response = func(request, response)
        return response

from django.core.servers.basehttp import \
    WSGIRequestHandler as WSGIRequestHandlerOld, \
    BaseHTTPRequestHandler, WSGIServer

class WSGIRequestHandler(WSGIRequestHandlerOld):
    # Just enough to get rid of settings.py dependencies
    def __init__(self, *args, **kwargs):
        self.path = ''
        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)
    
    def log_message(self, format, *args):
        sys.stderr.write(
            "[%s] %s\n" % (self.log_date_time_string(), format % args)
        )

def serve(view, host='localhost', port=6789):
    httpd = WSGIServer((host, port), WSGIRequestHandler)
    httpd.set_app(WSGIWrapper(view))
    httpd.serve_forever()

########NEW FILE########
__FILENAME__ = djng_old
"""
Just some sketched out ideas at the moment, this code has never been executed.
"""

from django import http
from django.core import signals
from django.utils.encoding import force_unicode
from django.utils.importlib import import_module

from django.core.handlers.wsgi import STATUS_CODE_TEXT, WSGIRequest

import sys

class Handler(object):
    # Changes that are always applied to a response (in this order).
    response_fixes = [
        http.fix_location_header,
        http.conditional_content_removal,
        http.fix_IE_for_attach,
        http.fix_IE_for_vary,
    ]
    request_middleware = []
    response_middleware = []
    exception_middleware = []
    
    debug = False
    propagate_exceptions = False
    
    def __init__(self, router):
        self.router = router
    
    def __call__(self, environ, start_response):
        try:
            request = WSGIRequest(environ)
        except UnicodeDecodeError:
            response = http.HttpResponseBadRequest()
        else:
            response = self.get_response(request)

            # Apply response middleware
            for middleware_method in self.response_middleware:
                response = middleware_method(request, response)
            response = self.apply_response_fixes(request, response)

        try:
            status_text = STATUS_CODE_TEXT[response.status_code]
        except KeyError:
            status_text = 'UNKNOWN STATUS CODE'
        status = '%s %s' % (response.status_code, status_text)
        response_headers = [(str(k), str(v)) for k, v in response.items()]
        for c in response.cookies.values():
            response_headers.append(('Set-Cookie', str(c.output(header=''))))
        start_response(status, response_headers)
        return response
    
    def get_response(self, request):
        "Returns an HttpResponse object for the given HttpRequest"
        from django.core import exceptions, urlresolvers

        # Apply request middleware
        for middleware_method in self.request_middleware:
            response = middleware_method(request)
            if response:
                return response
        
        # Resolve and execute the view, catching any errors
        try:
            response = self.router(request)
        except Exception, e:
            # If the view raised an exception, run it through exception
            # middleware, and if the exception middleware returns a
            # response, use that. Otherwise, reraise the exception.
            for middleware_method in self.exception_middleware:
                response = middleware_method(request, e)
                if response:
                    return response
            raise
        except http.Http404, e:
            return self.handle_404(request, e)
        except exceptions.PermissionDenied:
            return self.handle_permission_denied(request)
        except SystemExit:
            # Allow sys.exit() to actually exit. See tickets #1023 and #4701
            raise
        except: # Handle everything else, including SuspiciousOperation, etc.
            # Get exc_info now, in case another exception is thrown later
            exc_info = sys.exc_info()
            receivers = signals.got_request_exception.send(
                sender=self.__class__, request=request
            )
            return self.handle_uncaught_exception(request, exc_info)

    def handle_404(self, request, e):
        if self.debug:
            from django.views import debug
            return debug.technical_404_response(request, e)
        else:
            return http.HttpResponseNotFound('<h1>404</h1>')
    
    def handle_permission_denied(self, request):
        return http.HttpResponseForbidden('<h1>Permission denied</h1>')

    def handle_uncaught_exception(self, request, exc_info):
        """
        Processing for any otherwise uncaught exceptions (those that will
        generate HTTP 500 responses). Can be overridden by subclasses who want
        customised 500 handling.

        Be *very* careful when overriding this because the error could be
        caused by anything, so assuming something like the database is always
        available would be an error.
        """
        from django.core.mail import mail_admins

        if self.propagate_exceptions:
            raise

        if self.debug:
            from django.views import debug
            return debug.technical_500_response(request, *exc_info)

        # When DEBUG is False, send an error message to the admins.
        subject = 'Error: %s' % request.path
        try:
            request_repr = repr(request)
        except:
            request_repr = "Request repr() unavailable"
        message = "%s\n\n%s" % (self._get_traceback(exc_info), request_repr)
        mail_admins(subject, message, fail_silently=True)
        # Return an HttpResponse that displays a friendly error message.
        return self.handle_500(request, exc_info)

    def _get_traceback(self, exc_info=None):
        "Helper function to return the traceback as a string"
        import traceback
        return '\n'.join(
            traceback.format_exception(*(exc_info or sys.exc_info()))
        )

    def apply_response_fixes(self, request, response):
        """
        Applies each of the functions in self.response_fixes to the request 
        and response, modifying the response in the process. Returns the new
        response.
        """
        for func in self.response_fixes:
            response = func(request, response)
        return response

def serve(handler, host='localhost', port=6789):
    from django.core.servers.basehttp import run
    run(host, int(port), handler)

########NEW FILE########
__FILENAME__ = example_forms
import djng

def index(request):
    return djng.Response("""
    <h1>Forms demo</h1>
    <form action="/search/" method="get">
        <p>
            <input type="search" name="q">
            <input type="submit" value="Search">
        </p>
    </form>
    <form action="/submit/" method="post">
        <p><textarea name="text" rows="5" cols="30"></textarea></p>
        <p><input type="submit" value="Capitalise text"></p>
    </form>
    <a href="/validate/">Form validation demo</a>
    """)

def search(request):
    return djng.Response(
        "This page would search for %s" % djng.escape(
            request.GET.get('q', 'no-search-term')
        )
    )

def submit(request):
    text = request.POST.get('text', 'no-text')
    return djng.Response(djng.escape(text.upper()))

class DemoForm(djng.forms.Form):
    name = djng.forms.CharField(max_length = 100)
    email = djng.forms.EmailField()
    optional_text = djng.forms.CharField(required = False)

def validate(request):
    if request.method == 'POST':
        form = DemoForm(request.POST)
        if form.is_valid():
            return djng.Response('Form was valid: %s' % djng.escape(
                repr(form.cleaned_data)
            ))
    else:
        form = DemoForm()
    return djng.Response("""
    <form action="/validate/" method="post">
    %s
    <p><input type="submit">
    </form>
    """ % form.as_p())

app = djng.Router(
    (r'^$', index),
    (r'^search/$', search),
    (r'^submit/$', submit),
    (r'^validate/$', validate),
)

if __name__ == '__main__':
    djng.serve(app, '0.0.0.0', 8888)

########NEW FILE########
__FILENAME__ = example_hello
import djng

def index(request):
    return djng.Response('Hello, world')

if __name__ == '__main__':
    djng.serve(index, '0.0.0.0', 8888)

########NEW FILE########
__FILENAME__ = example_middleware
import djng

def hello(request):
    return djng.Response('Hello, world ' * 100)

def goodbye(request):
    return djng.Response('Goodbye, world ' * 100)

app = djng.Router(
    (r'^hello$', hello),
    (r'^goodbye$', djng.middleware.GZip(goodbye)),
)

if __name__ == '__main__':
    djng.serve(app, '0.0.0.0', 8888)

########NEW FILE########
__FILENAME__ = example_rest_view
import djng

class RestView(object):
    def __call__(self, request, *args, **kwargs):
        method = request.method.upper()
        if hasattr(self, method):
            return getattr(self, method)(request, *args, **kwargs)
        return self.method_not_supported(request)
    
    @staticmethod
    def method_not_supported(request):
        return djng.Response('Method not supported')
    

class MyView(RestView):
    @staticmethod
    def GET(request):
        return djng.Response('This is a GET')
    
    @staticmethod
    def POST(request):
        return djng.Response('This is a POST')

if __name__ == '__main__':
    djng.serve(MyView(), '0.0.0.0', 8888)

########NEW FILE########
__FILENAME__ = example_services_incomplete
from djng import services
from djng.services.cache import CacheConfigure

# Default service configuration
services.configure('cache', CacheConfigure(
    in_memory = True,
))
# Or maybe this:
#     services.cache.configure(CacheConfigure(in_memory = True))
# Or even:
#     services.cache.configure(in_memory = True)
# Or...
#     services.default('cache', InMemoryCache())
# Or...
#     services.configure('cache', InMemoryCache())

def app(request):
    from djng.services.cache import cache
    counter = cache.get('counter')
    if not counter:
        counter = 1
    else:
        counter += 1
    cache.set('counter', counter)
    print counter

app(None)
app(None)

# Middleware that reconfigures service for the duration of the request
app = services.wrap(app, 'cache', InMemoryCache())

# Or...
app = services.wrap(app, 
    cache = InMemoryCache(),
)


app(None)
app(None)
app(None)
    
########NEW FILE########
__FILENAME__ = example_template
import djng, os, datetime

djng.template.configure(
    os.path.join(os.path.dirname(__file__), 'example_templates')
)

def index(request):
    return djng.TemplateResponse(request, 'example.html', {
        'time': str(datetime.datetime.now()),
    })

if __name__ == '__main__':
    djng.serve(index, '0.0.0.0', 8888)

########NEW FILE########
__FILENAME__ = example_urls
import djng

app = djng.ErrorWrapper(
    djng.Router(
        (r'^hello$', lambda request: djng.Response('Hello, world')),
        (r'^goodbye$', lambda request: djng.Response('Goodbye, world')),
    ),
    custom_404 = lambda request: djng.Response('404 error', status=404),
    custom_500 = lambda request: djng.Response('500 error', status=500)
)

if __name__ == '__main__':
    djng.serve(app, '0.0.0.0', 8888)

########NEW FILE########
