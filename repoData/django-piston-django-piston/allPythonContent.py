__FILENAME__ = handlers
from piston.handler import BaseHandler, AnonymousBaseHandler
from piston.utils import rc, require_mime, require_extended

from blogserver.blog.models import Blogpost

class BlogpostHandler(BaseHandler):
    """
    Authenticated entrypoint for blogposts.
    """
    model = Blogpost
    anonymous = 'AnonymousBlogpostHandler'
    fields = ('title', 'content', ('author', ('username',)), 
              'created_on', 'content_length')

    @classmethod
    def content_length(cls, blogpost):
        return len(blogpost.content)

    @classmethod
    def resource_uri(cls, blogpost):
        return ('blogposts', [ 'json', ])

    def read(self, request, title=None):
        """
        Returns a blogpost, if `title` is given,
        otherwise all the posts.
        
        Parameters:
         - `title`: The title of the post to retrieve.
        """
        base = Blogpost.objects
        
        if title:
            return base.get(title=title)
        else:
            return base.all()

    def create(self, request):
        """
        Creates a new blogpost.
        """
        attrs = self.flatten_dict(request.POST)

        if self.exists(**attrs):
            return rc.DUPLICATE_ENTRY
        else:
            post = Blogpost(title=attrs['title'], 
                            content=attrs['content'],
                            author=request.user)
            post.save()
            
            return post

class AnonymousBlogpostHandler(BlogpostHandler, AnonymousBaseHandler):
    """
    Anonymous entrypoint for blogposts.
    """
    fields = ('id', 'title', 'content', 'created_on')

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from piston.resource import Resource
from piston.authentication import HttpBasicAuthentication
from piston.doc import documentation_view

from blogserver.api.handlers import BlogpostHandler

auth = HttpBasicAuthentication(realm='My sample API')

blogposts = Resource(handler=BlogpostHandler, authentication=auth)

urlpatterns = patterns('',
    url(r'^posts/$', blogposts),
    url(r'^posts/(?P<emitter_format>.+)/$', blogposts),
    url(r'^posts\.(?P<emitter_format>.+)', blogposts, name='blogposts'),

    # automated documentation
    url(r'^$', documentation_view),
)
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.auth.models import User
from django.contrib import admin

class Blogpost(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    author = models.ForeignKey(User, related_name='posts')
    created_on = models.DateTimeField(auto_now_add=True)
    
    def __unicode__(self):
        return self.title

admin.site.register(Blogpost)
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('blogserver.blog.views',
    url(r'^$', 'posts', name='posts'),
    url(r'^js$', 'test_js'),
)
########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from blogserver.blog.models import Blogpost

def posts(request):
    posts = Blogpost.objects.all()

    return render_to_response("posts.html", {
        'posts': posts },
        RequestContext(request))
    
def test_js(request):
    return render_to_response('test_js.html', {}, RequestContext(request))

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
__FILENAME__ = settings
import os, sys

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Fix up piston imports here. We would normally place piston in 
# a directory accessible via the Django app, but this is an
# example and we ship it a couple of directories up.
sys.path.insert(0, os.path.join(BASE_DIR, '../../'))

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = os.path.join(BASE_DIR, 'db')             # Or path to database file if using sqlite3.
#DATABASE_USER = ''             # Not used with sqlite3.
#DATABASE_PASSWORD = ''         # Not used with sqlite3.
#DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
#DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'f@vhy8vuq7w70v=cnynm(am1__*zt##i2--i2p-021@-qgws%g'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'blogserver.urls'

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'templates'),
    os.path.join(BASE_DIR, '../../piston/templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.markup',
    'blogserver.blog',
    'blogserver.api',
)

FIXTURE_DIRS = (
    os.path.join(BASE_DIR, 'fixtures'),
)

APPEND_SLASH = False

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    (r'^', include('blogserver.blog.urls')),
    (r'^api/', include('blogserver.api.urls')),
    (r'^admin/(.*)', admin.site.root),
)

########NEW FILE########
__FILENAME__ = authentication
import binascii

import oauth
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.auth.decorators import login_required
from django.template import loader
from django.contrib.auth import authenticate
from django.conf import settings
from django.core.urlresolvers import get_callable
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import render_to_response
from django.template import RequestContext

from piston import forms

class NoAuthentication(object):
    """
    Authentication handler that always returns
    True, so no authentication is needed, nor
    initiated (`challenge` is missing.)
    """
    def is_authenticated(self, request):
        return True

class HttpBasicAuthentication(object):
    """
    Basic HTTP authenticater. Synopsis:
    
    Authentication handlers must implement two methods:
     - `is_authenticated`: Will be called when checking for
        authentication. Receives a `request` object, please
        set your `User` object on `request.user`, otherwise
        return False (or something that evaluates to False.)
     - `challenge`: In cases where `is_authenticated` returns
        False, the result of this method will be returned.
        This will usually be a `HttpResponse` object with
        some kind of challenge headers and 401 code on it.
    """
    def __init__(self, auth_func=authenticate, realm='API'):
        self.auth_func = auth_func
        self.realm = realm

    def is_authenticated(self, request):
        auth_string = request.META.get('HTTP_AUTHORIZATION', None)

        if not auth_string:
            return False
            
        try:
            (authmeth, auth) = auth_string.split(" ", 1)

            if not authmeth.lower() == 'basic':
                return False

            auth = auth.strip().decode('base64')
            (username, password) = auth.split(':', 1)
        except (ValueError, binascii.Error):
            return False
        
        request.user = self.auth_func(username=username, password=password) \
            or AnonymousUser()
                
        return not request.user in (False, None, AnonymousUser())
        
    def challenge(self):
        resp = HttpResponse("Authorization Required")
        resp['WWW-Authenticate'] = 'Basic realm="%s"' % self.realm
        resp.status_code = 401
        return resp

    def __repr__(self):
        return u'<HTTPBasic: realm=%s>' % self.realm

class HttpBasicSimple(HttpBasicAuthentication):
    def __init__(self, realm, username, password):
        self.user = User.objects.get(username=username)
        self.password = password

        super(HttpBasicSimple, self).__init__(auth_func=self.hash, realm=realm)
    
    def hash(self, username, password):
        if username == self.user.username and password == self.password:
            return self.user

def load_data_store():
    '''Load data store for OAuth Consumers, Tokens, Nonces and Resources
    '''
    path = getattr(settings, 'OAUTH_DATA_STORE', 'piston.store.DataStore')

    # stolen from django.contrib.auth.load_backend
    i = path.rfind('.')
    module, attr = path[:i], path[i+1:]

    try:
        mod = __import__(module, {}, {}, attr)
    except ImportError, e:
        raise ImproperlyConfigured, 'Error importing OAuth data store %s: "%s"' % (module, e)

    try:
        cls = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured, 'Module %s does not define a "%s" OAuth data store' % (module, attr)

    return cls

# Set the datastore here.
oauth_datastore = load_data_store()

def initialize_server_request(request):
    """
    Shortcut for initialization.
    """
    if request.method == "POST": #and \
#       request.META['CONTENT_TYPE'] == "application/x-www-form-urlencoded":
        params = dict(request.REQUEST.items())
    else:
        params = { }

    # Seems that we want to put HTTP_AUTHORIZATION into 'Authorization'
    # for oauth.py to understand. Lovely.
    request.META['Authorization'] = request.META.get('HTTP_AUTHORIZATION', '')

    oauth_request = oauth.OAuthRequest.from_request(
        request.method, request.build_absolute_uri(), 
        headers=request.META, parameters=params,
        query_string=request.environ.get('QUERY_STRING', ''))
        
    if oauth_request:
        oauth_server = oauth.OAuthServer(oauth_datastore(oauth_request))
        oauth_server.add_signature_method(oauth.OAuthSignatureMethod_PLAINTEXT())
        oauth_server.add_signature_method(oauth.OAuthSignatureMethod_HMAC_SHA1())
    else:
        oauth_server = None
        
    return oauth_server, oauth_request

def send_oauth_error(err=None):
    """
    Shortcut for sending an error.
    """
    response = HttpResponse(err.message.encode('utf-8'))
    response.status_code = 401

    realm = 'OAuth'
    header = oauth.build_authenticate_header(realm=realm)

    for k, v in header.iteritems():
        response[k] = v

    return response

def oauth_request_token(request):
    oauth_server, oauth_request = initialize_server_request(request)
    
    if oauth_server is None:
        return INVALID_PARAMS_RESPONSE
    try:
        token = oauth_server.fetch_request_token(oauth_request)

        response = HttpResponse(token.to_string())
    except oauth.OAuthError, err:
        response = send_oauth_error(err)

    return response

def oauth_auth_view(request, token, callback, params):
    form = forms.OAuthAuthenticationForm(initial={
        'oauth_token': token.key,
        'oauth_callback': token.get_callback_url() or callback,
      })

    return render_to_response('piston/authorize_token.html',
            { 'form': form }, RequestContext(request))

@login_required
def oauth_user_auth(request):
    oauth_server, oauth_request = initialize_server_request(request)
    
    if oauth_request is None:
        return INVALID_PARAMS_RESPONSE
        
    try:
        token = oauth_server.fetch_request_token(oauth_request)
    except oauth.OAuthError, err:
        return send_oauth_error(err)
        
    try:
        callback = oauth_server.get_callback(oauth_request)
    except:
        callback = None
    
    if request.method == "GET":
        params = oauth_request.get_normalized_parameters()

        oauth_view = getattr(settings, 'OAUTH_AUTH_VIEW', None)
        if oauth_view is None:
            return oauth_auth_view(request, token, callback, params)
        else:
            return get_callable(oauth_view)(request, token, callback, params)
    elif request.method == "POST":
        try:
            form = forms.OAuthAuthenticationForm(request.POST)
            if form.is_valid():
                token = oauth_server.authorize_token(token, request.user)
                args = '?'+token.to_string(only_key=True)
            else:
                args = '?error=%s' % 'Access not granted by user.'
                print "FORM ERROR", form.errors
            
            if not callback:
                callback = getattr(settings, 'OAUTH_CALLBACK_VIEW')
                return get_callable(callback)(request, token)
                
            response = HttpResponseRedirect(callback+args)
                
        except oauth.OAuthError, err:
            response = send_oauth_error(err)
    else:
        response = HttpResponse('Action not allowed.')
            
    return response

def oauth_access_token(request):
    oauth_server, oauth_request = initialize_server_request(request)
    
    if oauth_request is None:
        return INVALID_PARAMS_RESPONSE
        
    try:
        token = oauth_server.fetch_access_token(oauth_request)
        return HttpResponse(token.to_string())
    except oauth.OAuthError, err:
        return send_oauth_error(err)

INVALID_PARAMS_RESPONSE = send_oauth_error(oauth.OAuthError('Invalid request parameters.'))
                
class OAuthAuthentication(object):
    """
    OAuth authentication. Based on work by Leah Culver.
    """
    def __init__(self, realm='API'):
        self.realm = realm
        self.builder = oauth.build_authenticate_header
    
    def is_authenticated(self, request):
        """
        Checks whether a means of specifying authentication
        is provided, and if so, if it is a valid token.
        
        Read the documentation on `HttpBasicAuthentication`
        for more information about what goes on here.
        """
        if self.is_valid_request(request):
            try:
                consumer, token, parameters = self.validate_token(request)
            except oauth.OAuthError, err:
                print send_oauth_error(err)
                return False

            if consumer and token:
                request.user = token.user
                request.consumer = consumer
                request.throttle_extra = token.consumer.id
                return True
            
        return False
        
    def challenge(self):
        """
        Returns a 401 response with a small bit on
        what OAuth is, and where to learn more about it.
        
        When this was written, browsers did not understand
        OAuth authentication on the browser side, and hence
        the helpful template we render. Maybe some day in the
        future, browsers will take care of this stuff for us
        and understand the 401 with the realm we give it.
        """
        response = HttpResponse()
        response.status_code = 401
        realm = 'API'

        for k, v in self.builder(realm=realm).iteritems():
            response[k] = v

        tmpl = loader.render_to_string('oauth/challenge.html',
            { 'MEDIA_URL': settings.MEDIA_URL })

        response.content = tmpl

        return response
        
    @staticmethod
    def is_valid_request(request):
        """
        Checks whether the required parameters are either in
        the http-authorization header sent by some clients,
        which is by the way the preferred method according to
        OAuth spec, but otherwise fall back to `GET` and `POST`.
        """
        must_have = [ 'oauth_'+s for s in [
            'consumer_key', 'token', 'signature',
            'signature_method', 'timestamp', 'nonce' ] ]
        
        is_in = lambda l: all([ (p in l) for p in must_have ])

        auth_params = request.META.get("HTTP_AUTHORIZATION", "")
        req_params = request.REQUEST
             
        return is_in(auth_params) or is_in(req_params)
        
    @staticmethod
    def validate_token(request, check_timestamp=True, check_nonce=True):
        oauth_server, oauth_request = initialize_server_request(request)
        return oauth_server.verify_request(oauth_request)


########NEW FILE########
__FILENAME__ = decorator
"""
Decorator module, see
http://www.phyast.pitt.edu/~micheles/python/documentation.html
for the documentation and below for the licence.
"""

## The basic trick is to generate the source code for the decorated function
## with the right signature and to evaluate it.
## Uncomment the statement 'print >> sys.stderr, func_src'  in _decorator
## to understand what is going on.

__all__ = ["decorator", "new_wrapper", "getinfo"]

import inspect, sys

try:
    set
except NameError:
    from sets import Set as set

def getinfo(func):
    """
    Returns an info dictionary containing:
    - name (the name of the function : str)
    - argnames (the names of the arguments : list)
    - defaults (the values of the default arguments : tuple)
    - signature (the signature : str)
    - doc (the docstring : str)
    - module (the module name : str)
    - dict (the function __dict__ : str)
    
    >>> def f(self, x=1, y=2, *args, **kw): pass

    >>> info = getinfo(f)

    >>> info["name"]
    'f'
    >>> info["argnames"]
    ['self', 'x', 'y', 'args', 'kw']
    
    >>> info["defaults"]
    (1, 2)

    >>> info["signature"]
    'self, x, y, *args, **kw'
    """
    assert inspect.ismethod(func) or inspect.isfunction(func)
    regargs, varargs, varkwargs, defaults = inspect.getargspec(func)
    argnames = list(regargs)
    if varargs:
        argnames.append(varargs)
    if varkwargs:
        argnames.append(varkwargs)
    signature = inspect.formatargspec(regargs, varargs, varkwargs, defaults,
                                      formatvalue=lambda value: "")[1:-1]
    return dict(name=func.__name__, argnames=argnames, signature=signature,
                defaults = func.func_defaults, doc=func.__doc__,
                module=func.__module__, dict=func.__dict__,
                globals=func.func_globals, closure=func.func_closure)

# akin to functools.update_wrapper
def update_wrapper(wrapper, model, infodict=None):
    infodict = infodict or getinfo(model)
    try:
        wrapper.__name__ = infodict['name']
    except: # Python version < 2.4
        pass
    wrapper.__doc__ = infodict['doc']
    wrapper.__module__ = infodict['module']
    wrapper.__dict__.update(infodict['dict'])
    wrapper.func_defaults = infodict['defaults']
    wrapper.undecorated = model
    return wrapper

def new_wrapper(wrapper, model):
    """
    An improvement over functools.update_wrapper. The wrapper is a generic
    callable object. It works by generating a copy of the wrapper with the 
    right signature and by updating the copy, not the original.
    Moreovoer, 'model' can be a dictionary with keys 'name', 'doc', 'module',
    'dict', 'defaults'.
    """
    if isinstance(model, dict):
        infodict = model
    else: # assume model is a function
        infodict = getinfo(model)
    assert not '_wrapper_' in infodict["argnames"], (
        '"_wrapper_" is a reserved argument name!')
    src = "lambda %(signature)s: _wrapper_(%(signature)s)" % infodict
    funcopy = eval(src, dict(_wrapper_=wrapper))
    return update_wrapper(funcopy, model, infodict)

# helper used in decorator_factory
def __call__(self, func):
    infodict = getinfo(func)
    for name in ('_func_', '_self_'):
        assert not name in infodict["argnames"], (
           '%s is a reserved argument name!' % name)
    src = "lambda %(signature)s: _self_.call(_func_, %(signature)s)"
    new = eval(src % infodict, dict(_func_=func, _self_=self))
    return update_wrapper(new, func, infodict)

def decorator_factory(cls):
    """
    Take a class with a ``.caller`` method and return a callable decorator
    object. It works by adding a suitable __call__ method to the class;
    it raises a TypeError if the class already has a nontrivial __call__
    method.
    """
    attrs = set(dir(cls))
    if '__call__' in attrs:
        raise TypeError('You cannot decorate a class with a nontrivial '
                        '__call__ method')
    if 'call' not in attrs:
        raise TypeError('You cannot decorate a class without a '
                        '.call method')
    cls.__call__ = __call__
    return cls

def decorator(caller):
    """
    General purpose decorator factory: takes a caller function as
    input and returns a decorator with the same attributes.
    A caller function is any function like this::

     def caller(func, *args, **kw):
         # do something
         return func(*args, **kw)
    
    Here is an example of usage:

    >>> @decorator
    ... def chatty(f, *args, **kw):
    ...     print "Calling %r" % f.__name__
    ...     return f(*args, **kw)

    >>> chatty.__name__
    'chatty'
    
    >>> @chatty
    ... def f(): pass
    ...
    >>> f()
    Calling 'f'

    decorator can also take in input a class with a .caller method; in this
    case it converts the class into a factory of callable decorator objects.
    See the documentation for an example.
    """
    if inspect.isclass(caller):
        return decorator_factory(caller)
    def _decorator(func): # the real meat is here
        infodict = getinfo(func)
        argnames = infodict['argnames']
        assert not ('_call_' in argnames or '_func_' in argnames), (
            'You cannot use _call_ or _func_ as argument names!')
        src = "lambda %(signature)s: _call_(_func_, %(signature)s)" % infodict
        # import sys; print >> sys.stderr, src # for debugging purposes
        dec_func = eval(src, dict(_func_=func, _call_=caller))
        return update_wrapper(dec_func, func, infodict)
    return update_wrapper(_decorator, caller)

if __name__ == "__main__":
    import doctest; doctest.testmod()

##########################     LEGALESE    ###############################
      
##   Redistributions of source code must retain the above copyright 
##   notice, this list of conditions and the following disclaimer.
##   Redistributions in bytecode form must reproduce the above copyright
##   notice, this list of conditions and the following disclaimer in
##   the documentation and/or other materials provided with the
##   distribution. 

##   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
##   "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
##   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
##   A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
##   HOLDERS OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
##   INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
##   BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
##   OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
##   ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
##   TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
##   USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
##   DAMAGE.

########NEW FILE########
__FILENAME__ = doc
import inspect, handler

from piston.handler import typemapper
from piston.handler import handler_tracker

from django.core.urlresolvers import get_resolver, get_callable, get_script_prefix
from django.shortcuts import render_to_response
from django.template import RequestContext

def generate_doc(handler_cls):
    """
    Returns a `HandlerDocumentation` object
    for the given handler. Use this to generate
    documentation for your API.
    """
    if isinstance(type(handler_cls), handler.HandlerMetaClass):
        raise ValueError("Give me handler, not %s" % type(handler_cls))
        
    return HandlerDocumentation(handler_cls)
    
class HandlerMethod(object):
    def __init__(self, method, stale=False):
        self.method = method
        self.stale = stale
        
    def iter_args(self):
        args, _, _, defaults = inspect.getargspec(self.method)

        for idx, arg in enumerate(args):
            if arg in ('self', 'request', 'form'):
                continue

            didx = len(args)-idx

            if defaults and len(defaults) >= didx:
                yield (arg, str(defaults[-didx]))
            else:
                yield (arg, None)
        
    @property
    def signature(self, parse_optional=True):
        spec = ""

        for argn, argdef in self.iter_args():
            spec += argn
            
            if argdef:
                spec += '=%s' % argdef
            
            spec += ', '
            
        spec = spec.rstrip(", ")
        
        if parse_optional:
            return spec.replace("=None", "=<optional>")
            
        return spec
        
    @property
    def doc(self):
        return inspect.getdoc(self.method)
    
    @property
    def name(self):
        return self.method.__name__
    
    @property
    def http_name(self):
        if self.name == 'read':
            return 'GET'
        elif self.name == 'create':
            return 'POST'
        elif self.name == 'delete':
            return 'DELETE'
        elif self.name == 'update':
            return 'PUT'
    
    def __repr__(self):
        return "<Method: %s>" % self.name
    
class HandlerDocumentation(object):
    def __init__(self, handler):
        self.handler = handler
        
    def get_methods(self, include_default=False):
        for method in "read create update delete".split():
            met = getattr(self.handler, method, None)

            if not met:
                continue
                
            stale = inspect.getmodule(met.im_func) is not inspect.getmodule(self.handler)

            if not self.handler.is_anonymous:
                if met and (not stale or include_default):
                    yield HandlerMethod(met, stale)
            else:
                if not stale or met.__name__ == "read" \
                    and 'GET' in self.allowed_methods:
                    
                    yield HandlerMethod(met, stale)
        
    def get_all_methods(self):
        return self.get_methods(include_default=True)
        
    @property
    def is_anonymous(self):
        return self.handler.is_anonymous

    def get_model(self):
        return getattr(self, 'model', None)
            
    @property
    def has_anonymous(self):
        return self.handler.anonymous
            
    @property
    def anonymous(self):
        if self.has_anonymous:
            return HandlerDocumentation(self.handler.anonymous)
            
    @property
    def doc(self):
        return self.handler.__doc__
    
    @property
    def name(self):
        return self.handler.__name__
    
    @property
    def allowed_methods(self):
        return self.handler.allowed_methods
    
    def get_resource_uri_template(self):
        """
        URI template processor.
        
        See http://bitworking.org/projects/URI-Templates/
        """
        def _convert(template, params=[]):
            """URI template converter"""
            paths = template % dict([p, "{%s}" % p] for p in params)
            return u'%s%s' % (get_script_prefix(), paths)
        
        try:
            resource_uri = self.handler.resource_uri()
            
            components = [None, [], {}]

            for i, value in enumerate(resource_uri):
                components[i] = value
        
            lookup_view, args, kwargs = components
            lookup_view = get_callable(lookup_view, True)

            possibilities = get_resolver(None).reverse_dict.getlist(lookup_view)
            
            for possibility, pattern in possibilities:
                for result, params in possibility:
                    if args:
                        if len(args) != len(params):
                            continue
                        return _convert(result, params)
                    else:
                        if set(kwargs.keys()) != set(params):
                            continue
                        return _convert(result, params)
        except:
            return None
        
    resource_uri_template = property(get_resource_uri_template)
    
    def __repr__(self):
        return u'<Documentation for "%s">' % self.name

def documentation_view(request):
    """
    Generic documentation view. Generates documentation
    from the handlers you've defined.
    """
    docs = [ ]

    for handler in handler_tracker: 
        docs.append(generate_doc(handler))

    def _compare(doc1, doc2): 
       #handlers and their anonymous counterparts are put next to each other.
       name1 = doc1.name.replace("Anonymous", "")
       name2 = doc2.name.replace("Anonymous", "")
       return cmp(name1, name2)    
 
    docs.sort(_compare)
       
    return render_to_response('documentation.html', 
        { 'docs': docs }, RequestContext(request))

########NEW FILE########
__FILENAME__ = emitters
from __future__ import generators

import decimal, re, inspect
import copy

try:
    # yaml isn't standard with python.  It shouldn't be required if it
    # isn't used.
    import yaml
except ImportError:
    yaml = None

# Fallback since `any` isn't in Python <2.5
try:
    any
except NameError:
    def any(iterable):
        for element in iterable:
            if element:
                return True
        return False

from django.db.models.query import QuerySet
from django.db.models import Model, permalink
from django.utils import simplejson
from django.utils.xmlutils import SimplerXMLGenerator
from django.utils.encoding import smart_unicode
from django.core.urlresolvers import reverse, NoReverseMatch
from django.core.serializers.json import DateTimeAwareJSONEncoder
from django.http import HttpResponse
from django.core import serializers

from utils import HttpStatusCode, Mimer
from validate_jsonp import is_valid_jsonp_callback_value

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

try:
    import cPickle as pickle
except ImportError:
    import pickle

# Allow people to change the reverser (default `permalink`).
reverser = permalink

class Emitter(object):
    """
    Super emitter. All other emitters should subclass
    this one. It has the `construct` method which
    conveniently returns a serialized `dict`. This is
    usually the only method you want to use in your
    emitter. See below for examples.

    `RESERVED_FIELDS` was introduced when better resource
    method detection came, and we accidentially caught these
    as the methods on the handler. Issue58 says that's no good.
    """
    EMITTERS = { }
    RESERVED_FIELDS = set([ 'read', 'update', 'create',
                            'delete', 'model', 'anonymous',
                            'allowed_methods', 'fields', 'exclude' ])

    def __init__(self, payload, typemapper, handler, fields=(), anonymous=True):
        self.typemapper = typemapper
        self.data = payload
        self.handler = handler
        self.fields = fields
        self.anonymous = anonymous

        if isinstance(self.data, Exception):
            raise

    def method_fields(self, handler, fields):
        if not handler:
            return { }

        ret = dict()

        for field in fields - Emitter.RESERVED_FIELDS:
            t = getattr(handler, str(field), None)

            if t and callable(t):
                ret[field] = t

        return ret

    def construct(self):
        """
        Recursively serialize a lot of types, and
        in cases where it doesn't recognize the type,
        it will fall back to Django's `smart_unicode`.

        Returns `dict`.
        """
        def _any(thing, fields=None):
            """
            Dispatch, all types are routed through here.
            """
            ret = None

            # return anything we've already seen as a string only
            # this prevents infinite recursion in the case of recursive relationships
            if thing in self.stack:
                return None

            self.stack.append(thing)

            if isinstance(thing, QuerySet):
                ret = _qs(thing, fields)
            elif isinstance(thing, (tuple, list, set)):
                ret = _list(thing, fields)
            elif isinstance(thing, dict):
                ret = _dict(thing, fields)
            elif isinstance(thing, decimal.Decimal):
                ret = str(thing)
            elif isinstance(thing, Model):
                ret = _model(thing, fields)
            elif isinstance(thing, HttpResponse):
                raise HttpStatusCode(thing)
            elif inspect.isfunction(thing):
                if not inspect.getargspec(thing)[0]:
                    ret = _any(thing())
            elif hasattr(thing, '__emittable__'):
                f = thing.__emittable__
                if inspect.ismethod(f) and len(inspect.getargspec(f)[0]) == 1:
                    ret = _any(f())
            elif repr(thing).startswith("<django.db.models.fields.related.RelatedManager"):
                ret = _any(thing.all())
            else:
                ret = smart_unicode(thing, strings_only=True)

            self.stack.pop()

            return ret

        def _fk(data, field):
            """
            Foreign keys.
            """
            return _any(getattr(data, field.name))

        def _related(data, fields=None):
            """
            Foreign keys.
            """
            return [ _model(m, fields) for m in data.iterator() ]

        def _m2m(data, field, fields=None):
            """
            Many to many (re-route to `_model`.)
            """
            return [ _model(m, fields) for m in getattr(data, field.name).iterator() ]

        def _model(data, fields=None):
            """
            Models. Will respect the `fields` and/or
            `exclude` on the handler (see `typemapper`.)
            """
            ret = { }
            handler = self.in_typemapper(type(data), self.anonymous)
            get_absolute_uri = False

            if handler or fields:
                v = lambda f: getattr(data, f.attname)

                if handler:
                    fields = getattr(handler, 'fields')    
                
                if not fields or hasattr(handler, 'fields'):
                    """
                    Fields was not specified, try to find teh correct
                    version in the typemapper we were sent.
                    """
                    mapped = self.in_typemapper(type(data), self.anonymous)
                    get_fields = set(mapped.fields)
                    exclude_fields = set(mapped.exclude).difference(get_fields)

                    if 'absolute_uri' in get_fields:
                        get_absolute_uri = True

                    if not get_fields:
                        get_fields = set([ f.attname.replace("_id", "", 1)
                            for f in data._meta.fields + data._meta.virtual_fields])
                    
                    if hasattr(mapped, 'extra_fields'):
                        get_fields.update(mapped.extra_fields)

                    # sets can be negated.
                    for exclude in exclude_fields:
                        if isinstance(exclude, basestring):
                            get_fields.discard(exclude)

                        elif isinstance(exclude, re._pattern_type):
                            for field in get_fields.copy():
                                if exclude.match(field):
                                    get_fields.discard(field)

                else:
                    get_fields = set(fields)

                met_fields = self.method_fields(handler, get_fields)

                for f in data._meta.local_fields + data._meta.virtual_fields:
                    if f.serialize and not any([ p in met_fields for p in [ f.attname, f.name ]]):
                        if not f.rel:
                            if f.attname in get_fields:
                                ret[f.attname] = _any(v(f))
                                get_fields.remove(f.attname)
                        else:
                            if f.attname[:-3] in get_fields:
                                ret[f.name] = _fk(data, f)
                                get_fields.remove(f.name)

                for mf in data._meta.many_to_many:
                    if mf.serialize and mf.attname not in met_fields:
                        if mf.attname in get_fields:
                            ret[mf.name] = _m2m(data, mf)
                            get_fields.remove(mf.name)

                # try to get the remainder of fields
                for maybe_field in get_fields:
                    if isinstance(maybe_field, (list, tuple)):
                        model, fields = maybe_field
                        inst = getattr(data, model, None)

                        if inst:
                            if hasattr(inst, 'all'):
                                ret[model] = _related(inst, fields)
                            elif callable(inst):
                                if len(inspect.getargspec(inst)[0]) == 1:
                                    ret[model] = _any(inst(), fields)
                            else:
                                ret[model] = _model(inst, fields)

                    elif maybe_field in met_fields:
                        # Overriding normal field which has a "resource method"
                        # so you can alter the contents of certain fields without
                        # using different names.
                        ret[maybe_field] = _any(met_fields[maybe_field](data))

                    else:
                        maybe = getattr(data, maybe_field, None)
                        if maybe is not None:
                            if callable(maybe):
                                if len(inspect.getargspec(maybe)[0]) <= 1:
                                    ret[maybe_field] = _any(maybe())
                            else:
                                ret[maybe_field] = _any(maybe)
                        else:
                            handler_f = getattr(handler or self.handler, maybe_field, None)

                            if handler_f:
                                ret[maybe_field] = _any(handler_f(data))

            else:
                for f in data._meta.fields:
                    ret[f.attname] = _any(getattr(data, f.attname))

                fields = dir(data.__class__) + ret.keys()
                add_ons = [k for k in dir(data) if k not in fields]

                for k in add_ons:
                    ret[k] = _any(getattr(data, k))

            # resouce uri
            if self.in_typemapper(type(data), self.anonymous):
                handler = self.in_typemapper(type(data), self.anonymous)
                if hasattr(handler, 'resource_uri'):
                    url_id, fields = handler.resource_uri(data)

                    try:
                        ret['resource_uri'] = reverser( lambda: (url_id, fields) )()
                    except NoReverseMatch, e:
                        pass

            if hasattr(data, 'get_api_url') and 'resource_uri' not in ret:
                try: ret['resource_uri'] = data.get_api_url()
                except: pass

            # absolute uri
            if hasattr(data, 'get_absolute_url') and get_absolute_uri:
                try: ret['absolute_uri'] = data.get_absolute_url()
                except: pass

            return ret

        def _qs(data, fields=None):
            """
            Querysets.
            """
            return [ _any(v, fields) for v in data ]

        def _list(data, fields=None):
            """
            Lists.
            """
            return [ _any(v, fields) for v in data ]

        def _dict(data, fields=None):
            """
            Dictionaries.
            """
            return dict([ (k, _any(v, fields)) for k, v in data.iteritems() ])

        # Kickstart the seralizin'.
        self.stack = [];
        return _any(self.data, self.fields)

    def in_typemapper(self, model, anonymous):
        for klass, (km, is_anon) in self.typemapper.iteritems():
            if model is km and is_anon is anonymous:
                return klass

    def render(self):
        """
        This super emitter does not implement `render`,
        this is a job for the specific emitter below.
        """
        raise NotImplementedError("Please implement render.")

    def stream_render(self, request, stream=True):
        """
        Tells our patched middleware not to look
        at the contents, and returns a generator
        rather than the buffered string. Should be
        more memory friendly for large datasets.
        """
        yield self.render(request)

    @classmethod
    def get(cls, format):
        """
        Gets an emitter, returns the class and a content-type.
        """
        if cls.EMITTERS.has_key(format):
            return cls.EMITTERS.get(format)

        raise ValueError("No emitters found for type %s" % format)

    @classmethod
    def register(cls, name, klass, content_type='text/plain'):
        """
        Register an emitter.

        Parameters::
         - `name`: The name of the emitter ('json', 'xml', 'yaml', ...)
         - `klass`: The emitter class.
         - `content_type`: The content type to serve response as.
        """
        cls.EMITTERS[name] = (klass, content_type)

    @classmethod
    def unregister(cls, name):
        """
        Remove an emitter from the registry. Useful if you don't
        want to provide output in one of the built-in emitters.
        """
        return cls.EMITTERS.pop(name, None)

class XMLEmitter(Emitter):
    def _to_xml(self, xml, data):
        if isinstance(data, (list, tuple)):
            for item in data:
                xml.startElement("resource", {})
                self._to_xml(xml, item)
                xml.endElement("resource")
        elif isinstance(data, dict):
            for key, value in data.iteritems():
                xml.startElement(key, {})
                self._to_xml(xml, value)
                xml.endElement(key)
        else:
            xml.characters(smart_unicode(data))

    def render(self, request):
        stream = StringIO.StringIO()

        xml = SimplerXMLGenerator(stream, "utf-8")
        xml.startDocument()
        xml.startElement("response", {})

        self._to_xml(xml, self.construct())

        xml.endElement("response")
        xml.endDocument()

        return stream.getvalue()

Emitter.register('xml', XMLEmitter, 'text/xml; charset=utf-8')
Mimer.register(lambda *a: None, ('text/xml',))

class JSONEmitter(Emitter):
    """
    JSON emitter, understands timestamps.
    """
    def render(self, request):
        cb = request.GET.get('callback', None)
        seria = simplejson.dumps(self.construct(), cls=DateTimeAwareJSONEncoder, ensure_ascii=False, indent=4)

        # Callback
        if cb and is_valid_jsonp_callback_value(cb):
            return '%s(%s)' % (cb, seria)

        return seria

Emitter.register('json', JSONEmitter, 'application/json; charset=utf-8')
Mimer.register(simplejson.loads, ('application/json',))

class YAMLEmitter(Emitter):
    """
    YAML emitter, uses `safe_dump` to omit the
    specific types when outputting to non-Python.
    """
    def render(self, request):
        return yaml.safe_dump(self.construct())

if yaml:  # Only register yaml if it was import successfully.
    Emitter.register('yaml', YAMLEmitter, 'application/x-yaml; charset=utf-8')
    Mimer.register(lambda s: dict(yaml.load(s)), ('application/x-yaml',))

class PickleEmitter(Emitter):
    """
    Emitter that returns Python pickled.
    """
    def render(self, request):
        return pickle.dumps(self.construct())

Emitter.register('pickle', PickleEmitter, 'application/python-pickle')

"""
WARNING: Accepting arbitrary pickled data is a huge security concern.
The unpickler has been disabled by default now, and if you want to use
it, please be aware of what implications it will have.

Read more: http://nadiana.com/python-pickle-insecure

Uncomment the line below to enable it. You're doing so at your own risk.
"""
# Mimer.register(pickle.loads, ('application/python-pickle',))

class DjangoEmitter(Emitter):
    """
    Emitter for the Django serialized format.
    """
    def render(self, request, format='xml'):
        if isinstance(self.data, HttpResponse):
            return self.data
        elif isinstance(self.data, (int, str)):
            response = self.data
        else:
            response = serializers.serialize(format, self.data, indent=True)

        return response

Emitter.register('django', DjangoEmitter, 'text/xml; charset=utf-8')

########NEW FILE########
__FILENAME__ = forms
import hmac, base64

from django import forms
from django.conf import settings

class Form(forms.Form):
    pass
    
class ModelForm(forms.ModelForm):
    """
    Subclass of `forms.ModelForm` which makes sure
    that the initial values are present in the form
    data, so you don't have to send all old values
    for the form to actually validate. Django does not
    do this on its own, which is really annoying.
    """
    def merge_from_initial(self):
        self.data._mutable = True
        filt = lambda v: v not in self.data.keys()
        for field in filter(filt, getattr(self.Meta, 'fields', ())):
            self.data[field] = self.initial.get(field, None)


class OAuthAuthenticationForm(forms.Form):
    oauth_token = forms.CharField(widget=forms.HiddenInput)
    oauth_callback = forms.CharField(widget=forms.HiddenInput, required=False)
    authorize_access = forms.BooleanField(required=True)
    csrf_signature = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)

        self.fields['csrf_signature'].initial = self.initial_csrf_signature

    def clean_csrf_signature(self):
        sig = self.cleaned_data['csrf_signature']
        token = self.cleaned_data['oauth_token']

        sig1 = OAuthAuthenticationForm.get_csrf_signature(settings.SECRET_KEY, token)

        if sig != sig1:
            raise forms.ValidationError("CSRF signature is not valid")

        return sig

    def initial_csrf_signature(self):
        token = self.initial['oauth_token']
        return OAuthAuthenticationForm.get_csrf_signature(settings.SECRET_KEY, token)

    @staticmethod
    def get_csrf_signature(key, token):
        # Check signature...
        try:
            import hashlib # 2.5
            hashed = hmac.new(key, token, hashlib.sha1)
        except:
            import sha # deprecated
            hashed = hmac.new(key, token, sha)

        # calculate the digest base 64
        return base64.b64encode(hashed.digest())


########NEW FILE########
__FILENAME__ = handler
import warnings

from utils import rc
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.conf import settings

typemapper = { }
handler_tracker = [ ]

class HandlerMetaClass(type):
    """
    Metaclass that keeps a registry of class -> handler
    mappings.
    """
    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)

        def already_registered(model, anon):
            for k, (m, a) in typemapper.iteritems():
                if model == m and anon == a:
                    return k

        if hasattr(new_cls, 'model'):
            if already_registered(new_cls.model, new_cls.is_anonymous):
                if not getattr(settings, 'PISTON_IGNORE_DUPE_MODELS', False):
                    warnings.warn("Handler already registered for model %s, "
                        "you may experience inconsistent results." % new_cls.model.__name__)

            typemapper[new_cls] = (new_cls.model, new_cls.is_anonymous)
        else:
            typemapper[new_cls] = (None, new_cls.is_anonymous)

        if name not in ('BaseHandler', 'AnonymousBaseHandler'):
            handler_tracker.append(new_cls)

        return new_cls

class BaseHandler(object):
    """
    Basehandler that gives you CRUD for free.
    You are supposed to subclass this for specific
    functionality.

    All CRUD methods (`read`/`update`/`create`/`delete`)
    receive a request as the first argument from the
    resource. Use this for checking `request.user`, etc.
    """
    __metaclass__ = HandlerMetaClass

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    anonymous = is_anonymous = False
    exclude = ( 'id', )
    fields =  ( )

    def flatten_dict(self, dct):
        return dict([ (str(k), dct.get(k)) for k in dct.keys() ])

    def has_model(self):
        return hasattr(self, 'model') or hasattr(self, 'queryset')

    def queryset(self, request):
        return self.model.objects.all()

    def value_from_tuple(tu, name):
        for int_, n in tu:
            if n == name:
                return int_
        return None

    def exists(self, **kwargs):
        if not self.has_model():
            raise NotImplementedError

        try:
            self.model.objects.get(**kwargs)
            return True
        except self.model.DoesNotExist:
            return False

    def read(self, request, *args, **kwargs):
        if not self.has_model():
            return rc.NOT_IMPLEMENTED

        pkfield = self.model._meta.pk.name

        if pkfield in kwargs:
            try:
                return self.queryset(request).get(pk=kwargs.get(pkfield))
            except ObjectDoesNotExist:
                return rc.NOT_FOUND
            except MultipleObjectsReturned: # should never happen, since we're using a PK
                return rc.BAD_REQUEST
        else:
            return self.queryset(request).filter(*args, **kwargs)

    def create(self, request, *args, **kwargs):
        if not self.has_model():
            return rc.NOT_IMPLEMENTED

        attrs = self.flatten_dict(request.data)

        try:
            inst = self.queryset(request).get(**attrs)
            return rc.DUPLICATE_ENTRY
        except self.model.DoesNotExist:
            inst = self.model(**attrs)
            inst.save()
            return inst
        except self.model.MultipleObjectsReturned:
            return rc.DUPLICATE_ENTRY

    def update(self, request, *args, **kwargs):
        if not self.has_model():
            return rc.NOT_IMPLEMENTED

        pkfield = self.model._meta.pk.name

        if pkfield not in kwargs:
            # No pk was specified
            return rc.BAD_REQUEST

        try:
            inst = self.queryset(request).get(pk=kwargs.get(pkfield))
        except ObjectDoesNotExist:
            return rc.NOT_FOUND
        except MultipleObjectsReturned: # should never happen, since we're using a PK
            return rc.BAD_REQUEST

        attrs = self.flatten_dict(request.data)
        for k,v in attrs.iteritems():
            setattr( inst, k, v )

        inst.save()
        return rc.ALL_OK

    def delete(self, request, *args, **kwargs):
        if not self.has_model():
            raise NotImplementedError

        try:
            inst = self.queryset(request).get(*args, **kwargs)

            inst.delete()

            return rc.DELETED
        except self.model.MultipleObjectsReturned:
            return rc.DUPLICATE_ENTRY
        except self.model.DoesNotExist:
            return rc.NOT_HERE

class AnonymousBaseHandler(BaseHandler):
    """
    Anonymous handler.
    """
    is_anonymous = True
    allowed_methods = ('GET',)

########NEW FILE########
__FILENAME__ = handlers_doc
from piston.doc import generate_doc
from piston.handler import handler_tracker
import re

def generate_piston_documentation(app, docname, source):
    e = re.compile(r"^\.\. piston_handlers:: ([\w\.]+)$")
    old_source = source[0].split("\n")
    new_source = old_source[:]
    for line_nr, line in enumerate(old_source):
        m = e.match(line)
        if m:
            module = m.groups()[0]
            try:
                __import__(module)
            except ImportError:
                pass
            else:
                new_lines = []
                for handler in handler_tracker:
                    doc = generate_doc(handler)
                    new_lines.append(doc.name)
                    new_lines.append("-" * len(doc.name))
                    new_lines.append('::\n')
                    new_lines.append('\t' + doc.get_resource_uri_template() + '\n')
                    new_lines.append('Accepted methods:')
                    for method in doc.allowed_methods:
                        new_lines.append('\t* ' + method)
                    new_lines.append('')
                    if doc.doc:
                        new_lines.append(doc.doc)
                new_source[line_nr:line_nr+1] = new_lines

    source[0] = "\n".join(new_source)
    return source

def setup(app):
    app.connect('source-read', generate_piston_documentation)

########NEW FILE########
__FILENAME__ = managers
from django.db import models
from django.contrib.auth.models import User

KEY_SIZE = 18
SECRET_SIZE = 32

class KeyManager(models.Manager):
    '''Add support for random key/secret generation
    '''
    def generate_random_codes(self):
        key = User.objects.make_random_password(length=KEY_SIZE)
        secret = User.objects.make_random_password(length=SECRET_SIZE)

        while self.filter(key__exact=key, secret__exact=secret).count():
            secret = User.objects.make_random_password(length=SECRET_SIZE)

        return key, secret


class ConsumerManager(KeyManager):
    def create_consumer(self, name, description=None, user=None):
        """
        Shortcut to create a consumer with random key/secret.
        """
        consumer, created = self.get_or_create(name=name)

        if user:
            consumer.user = user

        if description:
            consumer.description = description

        if created:
            consumer.key, consumer.secret = self.generate_random_codes()
            consumer.save()

        return consumer

    _default_consumer = None

class ResourceManager(models.Manager):
    _default_resource = None

    def get_default_resource(self, name):
        """
        Add cache if you use a default resource.
        """
        if not self._default_resource:
            self._default_resource = self.get(name=name)

        return self._default_resource        

class TokenManager(KeyManager):
    def create_token(self, consumer, token_type, timestamp, user=None):
        """
        Shortcut to create a token with random key/secret.
        """
        token, created = self.get_or_create(consumer=consumer, 
                                            token_type=token_type, 
                                            timestamp=timestamp,
                                            user=user)

        if created:
            token.key, token.secret = self.generate_random_codes()
            token.save()

        return token
        

########NEW FILE########
__FILENAME__ = middleware
from django.middleware.http import ConditionalGetMiddleware
from django.middleware.common import CommonMiddleware

def compat_middleware_factory(klass):
    """
    Class wrapper that only executes `process_response`
    if `streaming` is not set on the `HttpResponse` object.
    Django has a bad habbit of looking at the content,
    which will prematurely exhaust the data source if we're
    using generators or buffers.
    """
    class compatwrapper(klass):
        def process_response(self, req, resp):
            if not hasattr(resp, 'streaming'):
                return klass.process_response(self, req, resp)
            return resp
    return compatwrapper

ConditionalMiddlewareCompatProxy = compat_middleware_factory(ConditionalGetMiddleware)
CommonMiddlewareCompatProxy = compat_middleware_factory(CommonMiddleware)

########NEW FILE########
__FILENAME__ = models
import urllib, time, urlparse

# Django imports
from django.db.models.signals import post_save, post_delete
from django.db import models
from django.contrib.auth.models import User
from django.core.mail import send_mail, mail_admins

# Piston imports
from managers import TokenManager, ConsumerManager, ResourceManager
from signals import consumer_post_save, consumer_post_delete

KEY_SIZE = 18
SECRET_SIZE = 32
VERIFIER_SIZE = 10

CONSUMER_STATES = (
    ('pending', 'Pending'),
    ('accepted', 'Accepted'),
    ('canceled', 'Canceled'),
    ('rejected', 'Rejected')
)

def generate_random(length=SECRET_SIZE):
    return User.objects.make_random_password(length=length)

class Nonce(models.Model):
    token_key = models.CharField(max_length=KEY_SIZE)
    consumer_key = models.CharField(max_length=KEY_SIZE)
    key = models.CharField(max_length=255)
    
    def __unicode__(self):
        return u"Nonce %s for %s" % (self.key, self.consumer_key)


class Consumer(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()

    key = models.CharField(max_length=KEY_SIZE)
    secret = models.CharField(max_length=SECRET_SIZE)

    status = models.CharField(max_length=16, choices=CONSUMER_STATES, default='pending')
    user = models.ForeignKey(User, null=True, blank=True, related_name='consumers')

    objects = ConsumerManager()
        
    def __unicode__(self):
        return u"Consumer %s with key %s" % (self.name, self.key)

    def generate_random_codes(self):
        """
        Used to generate random key/secret pairings. Use this after you've
        added the other data in place of save(). 

        c = Consumer()
        c.name = "My consumer" 
        c.description = "An app that makes ponies from the API."
        c.user = some_user_object
        c.generate_random_codes()
        """
        key = User.objects.make_random_password(length=KEY_SIZE)
        secret = generate_random(SECRET_SIZE)

        while Consumer.objects.filter(key__exact=key, secret__exact=secret).count():
            secret = generate_random(SECRET_SIZE)

        self.key = key
        self.secret = secret
        self.save()


class Token(models.Model):
    REQUEST = 1
    ACCESS = 2
    TOKEN_TYPES = ((REQUEST, u'Request'), (ACCESS, u'Access'))
    
    key = models.CharField(max_length=KEY_SIZE)
    secret = models.CharField(max_length=SECRET_SIZE)
    verifier = models.CharField(max_length=VERIFIER_SIZE)
    token_type = models.IntegerField(choices=TOKEN_TYPES)
    timestamp = models.IntegerField(default=long(time.time()))
    is_approved = models.BooleanField(default=False)
    
    user = models.ForeignKey(User, null=True, blank=True, related_name='tokens')
    consumer = models.ForeignKey(Consumer)
    
    callback = models.CharField(max_length=255, null=True, blank=True)
    callback_confirmed = models.BooleanField(default=False)
    
    objects = TokenManager()
    
    def __unicode__(self):
        return u"%s Token %s for %s" % (self.get_token_type_display(), self.key, self.consumer)

    def to_string(self, only_key=False):
        token_dict = {
            'oauth_token': self.key, 
            'oauth_token_secret': self.secret,
            'oauth_callback_confirmed': 'true',
        }

        if self.verifier:
            token_dict.update({ 'oauth_verifier': self.verifier })

        if only_key:
            del token_dict['oauth_token_secret']

        return urllib.urlencode(token_dict)

    def generate_random_codes(self):
        key = User.objects.make_random_password(length=KEY_SIZE)
        secret = generate_random(SECRET_SIZE)

        while Token.objects.filter(key__exact=key, secret__exact=secret).count():
            secret = generate_random(SECRET_SIZE)

        self.key = key
        self.secret = secret
        self.save()
        
    # -- OAuth 1.0a stuff

    def get_callback_url(self):
        if self.callback and self.verifier:
            # Append the oauth_verifier.
            parts = urlparse.urlparse(self.callback)
            scheme, netloc, path, params, query, fragment = parts[:6]
            if query:
                query = '%s&oauth_verifier=%s' % (query, self.verifier)
            else:
                query = 'oauth_verifier=%s' % self.verifier
            return urlparse.urlunparse((scheme, netloc, path, params,
                query, fragment))
        return self.callback
    
    def set_callback(self, callback):
        if callback != "oob": # out of band, says "we can't do this!"
            self.callback = callback
            self.callback_confirmed = True
            self.save()


# Attach our signals
post_save.connect(consumer_post_save, sender=Consumer)
post_delete.connect(consumer_post_delete, sender=Consumer)

########NEW FILE########
__FILENAME__ = oauth
"""
The MIT License

Copyright (c) 2007 Leah Culver

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import cgi
import urllib
import time
import random
import urlparse
import hmac
import binascii


VERSION = '1.0' # Hi Blaine!
HTTP_METHOD = 'GET'
SIGNATURE_METHOD = 'PLAINTEXT'


class OAuthError(RuntimeError):
    """Generic exception class."""
    def __init__(self, message='OAuth error occured.'):
        self.message = message

def build_authenticate_header(realm=''):
    """Optional WWW-Authenticate header (401 error)"""
    return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

def escape(s):
    """Escape a URL including any /."""
    return urllib.quote(s, safe='~')

def _utf8_str(s):
    """Convert unicode to utf-8."""
    if isinstance(s, unicode):
        return s.encode("utf-8")
    else:
        return str(s)

def generate_timestamp():
    """Get seconds since epoch (UTC)."""
    return int(time.time())

def generate_nonce(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])

def generate_verifier(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


class OAuthConsumer(object):
    """Consumer of OAuth authentication.

    OAuthConsumer is a data type that represents the identity of the Consumer
    via its shared secret with the Service Provider.

    """
    key = None
    secret = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret


class OAuthToken(object):
    """OAuthToken is a data type that represents an End User via either an access
    or request token.
    
    key -- the token
    secret -- the token secret

    """
    key = None
    secret = None
    callback = None
    callback_confirmed = None
    verifier = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

    def set_callback(self, callback):
        self.callback = callback
        self.callback_confirmed = 'true'

    def set_verifier(self, verifier=None):
        if verifier is not None:
            self.verifier = verifier
        else:
            self.verifier = generate_verifier()

    def get_callback_url(self):
        if self.callback and self.verifier:
            # Append the oauth_verifier.
            parts = urlparse.urlparse(self.callback)
            scheme, netloc, path, params, query, fragment = parts[:6]
            if query:
                query = '%s&oauth_verifier=%s' % (query, self.verifier)
            else:
                query = 'oauth_verifier=%s' % self.verifier
            return urlparse.urlunparse((scheme, netloc, path, params,
                query, fragment))
        return self.callback

    def to_string(self):
        data = {
            'oauth_token': self.key,
            'oauth_token_secret': self.secret,
        }
        if self.callback_confirmed is not None:
            data['oauth_callback_confirmed'] = self.callback_confirmed
        return urllib.urlencode(data)
 
    def from_string(s):
        """ Returns a token from something like:
        oauth_token_secret=xxx&oauth_token=xxx
        """
        params = cgi.parse_qs(s, keep_blank_values=False)
        key = params['oauth_token'][0]
        secret = params['oauth_token_secret'][0]
        token = OAuthToken(key, secret)
        try:
            token.callback_confirmed = params['oauth_callback_confirmed'][0]
        except KeyError:
            pass # 1.0, no callback confirmed.
        return token
    from_string = staticmethod(from_string)

    def __str__(self):
        return self.to_string()


class OAuthRequest(object):
    """OAuthRequest represents the request and can be serialized.

    OAuth parameters:
        - oauth_consumer_key 
        - oauth_token
        - oauth_signature_method
        - oauth_signature 
        - oauth_timestamp 
        - oauth_nonce
        - oauth_version
        - oauth_verifier
        ... any additional parameters, as defined by the Service Provider.
    """
    parameters = None # OAuth parameters.
    http_method = HTTP_METHOD
    http_url = None
    version = VERSION

    def __init__(self, http_method=HTTP_METHOD, http_url=None, parameters=None):
        self.http_method = http_method
        self.http_url = http_url
        self.parameters = parameters or {}

    def set_parameter(self, parameter, value):
        self.parameters[parameter] = value

    def get_parameter(self, parameter):
        try:
            return self.parameters[parameter]
        except:
            raise OAuthError('Parameter not found: %s' % parameter)

    def _get_timestamp_nonce(self):
        return self.get_parameter('oauth_timestamp'), self.get_parameter(
            'oauth_nonce')

    def get_nonoauth_parameters(self):
        """Get any non-OAuth parameters."""
        parameters = {}
        for k, v in self.parameters.iteritems():
            # Ignore oauth parameters.
            if k.find('oauth_') < 0:
                parameters[k] = v
        return parameters

    def to_header(self, realm=''):
        """Serialize as a header for an HTTPAuth request."""
        auth_header = 'OAuth realm="%s"' % realm
        # Add the oauth parameters.
        if self.parameters:
            for k, v in self.parameters.iteritems():
                if k[:6] == 'oauth_':
                    auth_header += ', %s="%s"' % (k, escape(str(v)))
        return {'Authorization': auth_header}

    def to_postdata(self):
        """Serialize as post data for a POST request."""
        return '&'.join(['%s=%s' % (escape(str(k)), escape(str(v))) \
            for k, v in self.parameters.iteritems()])

    def to_url(self):
        """Serialize as a URL for a GET request."""
        return '%s?%s' % (self.get_normalized_http_url(), self.to_postdata())

    def get_normalized_parameters(self):
        """Return a string that contains the parameters that must be signed."""
        params = self.parameters
        try:
            # Exclude the signature if it exists.
            del params['oauth_signature']
        except:
            pass
        # Escape key values before sorting.
        key_values = [(escape(_utf8_str(k)), escape(_utf8_str(v))) \
            for k,v in params.items()]
        # Sort lexicographically, first after key, then after value.
        key_values.sort()
        # Combine key value pairs into a string.
        return '&'.join(['%s=%s' % (k, v) for k, v in key_values])

    def get_normalized_http_method(self):
        """Uppercases the http method."""
        return self.http_method.upper()

    def get_normalized_http_url(self):
        """Parses the URL and rebuilds it to be scheme://host/path."""
        parts = urlparse.urlparse(self.http_url)
        scheme, netloc, path = parts[:3]
        # Exclude default port numbers.
        if scheme == 'http' and netloc[-3:] == ':80':
            netloc = netloc[:-3]
        elif scheme == 'https' and netloc[-4:] == ':443':
            netloc = netloc[:-4]
        return '%s://%s%s' % (scheme, netloc, path)

    def sign_request(self, signature_method, consumer, token):
        """Set the signature parameter to the result of build_signature."""
        # Set the signature method.
        self.set_parameter('oauth_signature_method',
            signature_method.get_name())
        # Set the signature.
        self.set_parameter('oauth_signature',
            self.build_signature(signature_method, consumer, token))

    def build_signature(self, signature_method, consumer, token):
        """Calls the build signature method within the signature method."""
        return signature_method.build_signature(self, consumer, token)

    def from_request(http_method, http_url, headers=None, parameters=None,
            query_string=None):
        """Combines multiple parameter sources."""
        if parameters is None:
            parameters = {}

        # Headers
        if headers and 'Authorization' in headers:
            auth_header = headers['Authorization']
            # Check that the authorization header is OAuth.
            if auth_header[:6] == 'OAuth ':
                auth_header = auth_header[6:]
                try:
                    # Get the parameters from the header.
                    header_params = OAuthRequest._split_header(auth_header)
                    parameters.update(header_params)
                except:
                    raise OAuthError('Unable to parse OAuth parameters from '
                        'Authorization header.')

        # GET or POST query string.
        if query_string:
            query_params = OAuthRequest._split_url_string(query_string)
            parameters.update(query_params)

        # URL parameters.
        param_str = urlparse.urlparse(http_url)[4] # query
        url_params = OAuthRequest._split_url_string(param_str)
        parameters.update(url_params)

        if parameters:
            return OAuthRequest(http_method, http_url, parameters)

        return None
    from_request = staticmethod(from_request)

    def from_consumer_and_token(oauth_consumer, token=None,
            callback=None, verifier=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        defaults = {
            'oauth_consumer_key': oauth_consumer.key,
            'oauth_timestamp': generate_timestamp(),
            'oauth_nonce': generate_nonce(),
            'oauth_version': OAuthRequest.version,
        }

        defaults.update(parameters)
        parameters = defaults

        if token:
            parameters['oauth_token'] = token.key
            parameters['oauth_callback'] = token.callback
            # 1.0a support for verifier.
            parameters['oauth_verifier'] = verifier
        elif callback:
            # 1.0a support for callback in the request token request.
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_consumer_and_token = staticmethod(from_consumer_and_token)

    def from_token_and_callback(token, callback=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        parameters['oauth_token'] = token.key

        if callback:
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_token_and_callback = staticmethod(from_token_and_callback)

    def _split_header(header):
        """Turn Authorization: header into parameters."""
        params = {}
        parts = header.split(',')
        for param in parts:
            # Ignore realm parameter.
            if param.find('realm') > -1:
                continue
            # Remove whitespace.
            param = param.strip()
            # Split key-value.
            param_parts = param.split('=', 1)
            # Remove quotes and unescape the value.
            params[param_parts[0]] = urllib.unquote(param_parts[1].strip('\"'))
        return params
    _split_header = staticmethod(_split_header)

    def _split_url_string(param_str):
        """Turn URL string into parameters."""
        parameters = cgi.parse_qs(param_str, keep_blank_values=False)
        for k, v in parameters.iteritems():
            parameters[k] = urllib.unquote(v[0])
        return parameters
    _split_url_string = staticmethod(_split_url_string)

class OAuthServer(object):
    """A worker to check the validity of a request against a data store."""
    timestamp_threshold = 300 # In seconds, five minutes.
    version = VERSION
    signature_methods = None
    data_store = None

    def __init__(self, data_store=None, signature_methods=None):
        self.data_store = data_store
        self.signature_methods = signature_methods or {}

    def set_data_store(self, data_store):
        self.data_store = data_store

    def get_data_store(self):
        return self.data_store

    def add_signature_method(self, signature_method):
        self.signature_methods[signature_method.get_name()] = signature_method
        return self.signature_methods

    def fetch_request_token(self, oauth_request):
        """Processes a request_token request and returns the
        request token on success.
        """
        try:
            # Get the request token for authorization.
            token = self._get_token(oauth_request, 'request')
        except OAuthError:
            # No token required for the initial token request.
            version = self._get_version(oauth_request)
            consumer = self._get_consumer(oauth_request)
            try:
                callback = self.get_callback(oauth_request)
            except OAuthError:
                callback = None # 1.0, no callback specified.
            self._check_signature(oauth_request, consumer, None)
            # Fetch a new token.
            token = self.data_store.fetch_request_token(consumer, callback)
        return token

    def fetch_access_token(self, oauth_request):
        """Processes an access_token request and returns the
        access token on success.
        """
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        verifier = self._get_verifier(oauth_request)
        # Get the request token.
        token = self._get_token(oauth_request, 'request')
        self._check_signature(oauth_request, consumer, token)
        new_token = self.data_store.fetch_access_token(consumer, token, verifier)
        return new_token

    def verify_request(self, oauth_request):
        """Verifies an api call and checks all the parameters."""
        # -> consumer and token
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        # Get the access token.
        token = self._get_token(oauth_request, 'access')
        self._check_signature(oauth_request, consumer, token)
        parameters = oauth_request.get_nonoauth_parameters()
        return consumer, token, parameters

    def authorize_token(self, token, user):
        """Authorize a request token."""
        return self.data_store.authorize_request_token(token, user)

    def get_callback(self, oauth_request):
        """Get the callback URL."""
        return oauth_request.get_parameter('oauth_callback')
 
    def build_authenticate_header(self, realm=''):
        """Optional support for the authenticate header."""
        return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

    def _get_version(self, oauth_request):
        """Verify the correct version request for this server."""
        try:
            version = oauth_request.get_parameter('oauth_version')
        except:
            version = VERSION
        if version and version != self.version:
            raise OAuthError('OAuth version %s not supported.' % str(version))
        return version

    def _get_signature_method(self, oauth_request):
        """Figure out the signature with some defaults."""
        try:
            signature_method = oauth_request.get_parameter(
                'oauth_signature_method')
        except:
            signature_method = SIGNATURE_METHOD
        try:
            # Get the signature method object.
            signature_method = self.signature_methods[signature_method]
        except:
            signature_method_names = ', '.join(self.signature_methods.keys())
            raise OAuthError('Signature method %s not supported try one of the '
                'following: %s' % (signature_method, signature_method_names))

        return signature_method

    def _get_consumer(self, oauth_request):
        consumer_key = oauth_request.get_parameter('oauth_consumer_key')
        consumer = self.data_store.lookup_consumer(consumer_key)
        if not consumer:
            raise OAuthError('Invalid consumer.')
        return consumer

    def _get_token(self, oauth_request, token_type='access'):
        """Try to find the token for the provided request token key."""
        token_field = oauth_request.get_parameter('oauth_token')
        token = self.data_store.lookup_token(token_type, token_field)
        if not token:
            raise OAuthError('Invalid %s token: %s' % (token_type, token_field))
        return token
    
    def _get_verifier(self, oauth_request):
        return oauth_request.get_parameter('oauth_verifier')

    def _check_signature(self, oauth_request, consumer, token):
        timestamp, nonce = oauth_request._get_timestamp_nonce()
        self._check_timestamp(timestamp)
        self._check_nonce(consumer, token, nonce)
        signature_method = self._get_signature_method(oauth_request)
        try:
            signature = oauth_request.get_parameter('oauth_signature')
        except:
            raise OAuthError('Missing signature.')
        # Validate the signature.
        valid_sig = signature_method.check_signature(oauth_request, consumer,
            token, signature)
        if not valid_sig:
            key, base = signature_method.build_signature_base_string(
                oauth_request, consumer, token)
            raise OAuthError('Invalid signature. Expected signature base '
                'string: %s' % base)
        built = signature_method.build_signature(oauth_request, consumer, token)

    def _check_timestamp(self, timestamp):
        """Verify that timestamp is recentish."""
        timestamp = int(timestamp)
        now = int(time.time())
        lapsed = now - timestamp
        if lapsed > self.timestamp_threshold:
            raise OAuthError('Expired timestamp: given %d and now %s has a '
                'greater difference than threshold %d' %
                (timestamp, now, self.timestamp_threshold))

    def _check_nonce(self, consumer, token, nonce):
        """Verify that the nonce is uniqueish."""
        nonce = self.data_store.lookup_nonce(consumer, token, nonce)
        if nonce:
            raise OAuthError('Nonce already used: %s' % str(nonce))


class OAuthClient(object):
    """OAuthClient is a worker to attempt to execute a request."""
    consumer = None
    token = None

    def __init__(self, oauth_consumer, oauth_token):
        self.consumer = oauth_consumer
        self.token = oauth_token

    def get_consumer(self):
        return self.consumer

    def get_token(self):
        return self.token

    def fetch_request_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def access_resource(self, oauth_request):
        """-> Some protected resource."""
        raise NotImplementedError


class OAuthDataStore(object):
    """A database abstraction used to lookup consumers and tokens."""

    def lookup_consumer(self, key):
        """-> OAuthConsumer."""
        raise NotImplementedError

    def lookup_token(self, oauth_consumer, token_type, token_token):
        """-> OAuthToken."""
        raise NotImplementedError

    def lookup_nonce(self, oauth_consumer, oauth_token, nonce):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_request_token(self, oauth_consumer, oauth_callback):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_consumer, oauth_token, oauth_verifier):
        """-> OAuthToken."""
        raise NotImplementedError

    def authorize_request_token(self, oauth_token, user):
        """-> OAuthToken."""
        raise NotImplementedError


class OAuthSignatureMethod(object):
    """A strategy class that implements a signature method."""
    def get_name(self):
        """-> str."""
        raise NotImplementedError

    def build_signature_base_string(self, oauth_request, oauth_consumer, oauth_token):
        """-> str key, str raw."""
        raise NotImplementedError

    def build_signature(self, oauth_request, oauth_consumer, oauth_token):
        """-> str."""
        raise NotImplementedError

    def check_signature(self, oauth_request, consumer, token, signature):
        built = self.build_signature(oauth_request, consumer, token)
        return built == signature


class OAuthSignatureMethod_HMAC_SHA1(OAuthSignatureMethod):

    def get_name(self):
        return 'HMAC-SHA1'
        
    def build_signature_base_string(self, oauth_request, consumer, token):
        sig = (
            escape(oauth_request.get_normalized_http_method()),
            escape(oauth_request.get_normalized_http_url()),
            escape(oauth_request.get_normalized_parameters()),
        )

        key = '%s&' % escape(consumer.secret)
        if token:
            key += escape(token.secret)
        raw = '&'.join(sig)
        return key, raw

    def build_signature(self, oauth_request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)

        # HMAC object.
        try:
            import hashlib # 2.5
            hashed = hmac.new(key, raw, hashlib.sha1)
        except:
            import sha # Deprecated
            hashed = hmac.new(key, raw, sha)

        # Calculate the digest base 64.
        return binascii.b2a_base64(hashed.digest())[:-1]


class OAuthSignatureMethod_PLAINTEXT(OAuthSignatureMethod):

    def get_name(self):
        return 'PLAINTEXT'

    def build_signature_base_string(self, oauth_request, consumer, token):
        """Concatenates the consumer key and secret."""
        sig = '%s&' % escape(consumer.secret)
        if token:
            sig = sig + escape(token.secret)
        return sig, sig

    def build_signature(self, oauth_request, consumer, token):
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)
        return key
########NEW FILE########
__FILENAME__ = resource
import sys, inspect, re

from django.http import (HttpResponse, Http404, HttpResponseNotAllowed,
    HttpResponseForbidden, HttpResponseServerError)
from django.views.debug import ExceptionReporter
from django.views.decorators.vary import vary_on_headers
from django.conf import settings
from django.core.mail import send_mail, EmailMessage
from django.db.models.query import QuerySet
from django.http import Http404

from emitters import Emitter
from handler import typemapper
from doc import HandlerMethod
from authentication import NoAuthentication
from utils import coerce_put_post, FormValidationError, HttpStatusCode, BadRangeException
from utils import rc, format_error, translate_mime, MimerDataException

CHALLENGE = object()

class Resource(object):
    """
    Resource. Create one for your URL mappings, just
    like you would with Django. Takes one argument,
    the handler. The second argument is optional, and
    is an authentication handler. If not specified,
    `NoAuthentication` will be used by default.
    """
    callmap = { 'GET': 'read', 'POST': 'create',
                'PUT': 'update', 'DELETE': 'delete' }

    range_re = re.compile("^items=(\d*)-(\d*)$")

    def __init__(self, handler, authentication=None):
        if not callable(handler):
            raise AttributeError, "Handler not callable."

        self.handler = handler()
        self.csrf_exempt = getattr(self.handler, 'csrf_exempt', True)

        if not authentication:
            self.authentication = (NoAuthentication(),)
        elif isinstance(authentication, (list, tuple)):
            self.authentication = authentication
        else:
            self.authentication = (authentication,)

        # Erroring
        self.email_errors = getattr(settings, 'PISTON_EMAIL_ERRORS', True)
        self.display_errors = getattr(settings, 'PISTON_DISPLAY_ERRORS', True)
        self.stream = getattr(settings, 'PISTON_STREAM_OUTPUT', False)
        
        # Paging
        paging_params = getattr(settings, 'PISTON_PAGINATION_PARAMS', ('offset', 'limit'))
        self.paging_offset = paging_params[0]
        self.paging_limit = paging_params[1]

    def determine_emitter(self, request, *args, **kwargs):
        """
        Function for determening which emitter to use
        for output. It lives here so you can easily subclass
        `Resource` in order to change how emission is detected.

        You could also check for the `Accept` HTTP header here,
        since that pretty much makes sense. Refer to `Mimer` for
        that as well.
        """
        em = kwargs.pop('emitter_format', None)

        if not em:
            em = request.GET.get('format', 'json')

        return em

    def form_validation_response(self, e):
        """
        Method to return form validation error information. 
        You will probably want to override this in your own
        `Resource` subclass.
        """
        resp = rc.BAD_REQUEST
        resp.write(' '+str(e.form.errors))
        return resp

    @property
    def anonymous(self):
        """
        Gets the anonymous handler. Also tries to grab a class
        if the `anonymous` value is a string, so that we can define
        anonymous handlers that aren't defined yet (like, when
        you're subclassing your basehandler into an anonymous one.)
        """
        if hasattr(self.handler, 'anonymous'):
            anon = self.handler.anonymous

            if callable(anon):
                return anon

            for klass in typemapper.keys():
                if anon == klass.__name__:
                    return klass

        return None

    def authenticate(self, request, rm):
        actor, anonymous = False, True

        for authenticator in self.authentication:
            if not authenticator.is_authenticated(request):
                if self.anonymous and \
                    rm in self.anonymous.allowed_methods:

                    actor, anonymous = self.anonymous(), True
                else:
                    actor, anonymous = authenticator.challenge, CHALLENGE
            else:
                return self.handler, self.handler.is_anonymous

        return actor, anonymous

    @vary_on_headers('Authorization')
    def __call__(self, request, *args, **kwargs):
        """
        NB: Sends a `Vary` header so we don't cache requests
        that are different (OAuth stuff in `Authorization` header.)
        """
        rm = request.method.upper()

        # Django's internal mechanism doesn't pick up
        # PUT request, so we trick it a little here.
        if rm == "PUT":
            coerce_put_post(request)

        actor, anonymous = self.authenticate(request, rm)

        if anonymous is CHALLENGE:
            return actor()
        else:
            handler = actor

        # Translate nested datastructs into `request.data` here.
        if rm in ('POST', 'PUT'):
            try:
                translate_mime(request)
            except MimerDataException:
                return rc.BAD_REQUEST
            if not hasattr(request, 'data'):
                if rm == 'POST':
                    request.data = request.POST
                else:
                    request.data = request.PUT

        if not rm in handler.allowed_methods:
            return HttpResponseNotAllowed(handler.allowed_methods)

        meth = getattr(handler, self.callmap.get(rm, ''), None)
        if not meth:
            raise Http404

        # Support emitter both through (?P<emitter_format>) and ?format=emitter.
        em_format = self.determine_emitter(request, *args, **kwargs)

        kwargs.pop('emitter_format', None)

        # Clean up the request object a bit, since we might
        # very well have `oauth_`-headers in there, and we
        # don't want to pass these along to the handler.
        request = self.cleanup_request(request)

        try:
            result = meth(request, *args, **kwargs)
        except Exception, e:
            result = self.error_handler(e, request, meth, em_format)

        try:
            emitter, ct = Emitter.get(em_format)
            fields = handler.fields

            if hasattr(handler, 'list_fields') and isinstance(result, (list, tuple, QuerySet)):
                fields = handler.list_fields
        except ValueError:
            result = rc.BAD_REQUEST
            result.content = "Invalid output format specified '%s'." % em_format
            return result

        status_code = 200

        # If we're looking at a response object which contains non-string
        # content, then assume we should use the emitter to format that 
        # content
        if isinstance(result, HttpResponse) and not result._is_string:
            status_code = result.status_code
            # Note: We can't use result.content here because that method attempts
            # to convert the content into a string which we don't want. 
            # when _is_string is False _container is the raw data
            result = result._container
            if sig:
                msg += 'Signature should be: %s' % sig
     
        srl = emitter(result, typemapper, handler, fields, anonymous)

        try:
            """
            Decide whether or not we want a generator here,
            or we just want to buffer up the entire result
            before sending it to the client. Won't matter for
            smaller datasets, but larger will have an impact.
            """
            if self.stream: stream = srl.stream_render(request)
            else: stream = srl.render(request)

            if not isinstance(stream, HttpResponse):
                resp = HttpResponse(stream, mimetype=ct, status=status_code)
            else:
                resp = stream

            if self.display_errors:
                msg += '\n\nException was: %s' % str(e)
            resp.streaming = self.stream
            result.content = format_error(msg)
        except Http404:
            return rc.NOT_FOUND
        except HttpStatusCode, e:
            return e.response
        except Exception, e:
            """
            On errors (like code errors), we'd like to be able to
            give crash reports to both admins and also the calling
            user. There's two setting parameters for this:

            Parameters::
             - `PISTON_EMAIL_ERRORS`: Will send a Django formatted
               error email to people in `settings.ADMINS`.
             - `PISTON_DISPLAY_ERRORS`: Will return a simple traceback
               to the caller, so he can tell you what error they got.

            If `PISTON_DISPLAY_ERRORS` is not enabled, the caller will
            receive a basic "500 Internal Server Error" message.
            """
            exc_type, exc_value, tb = sys.exc_info()
            rep = ExceptionReporter(request, exc_type, exc_value, tb.tb_next)
            if self.email_errors:
                self.email_exception(rep)
            if self.display_errors:
                return HttpResponseServerError(
                    format_error('\n'.join(rep.format_exception())))
            else:
                raise

        content_range = None
        if isinstance(result, QuerySet):
            """
            Limit results based on requested items. This is a based on
            HTTP 1.1 Partial GET, RFC 2616 sec 14.35, but is intended to
            operate on the record level rather than the byte level.  We
            will still respond with code 206 and a range header.
            """

            request_range = None
            
            if 'HTTP_RANGE' in request.META:
                """
                Parse the reange request header. HTTP proper expects Range, 
                but since we are deviating from the bytes nature, we will use 
                a non-standard syntax. This is expected to be of the format:

                    "items" "=" start "-" end

                E.g.,

                    Range: items=7-45

                """
                h = request.META['HTTP_RANGE'].strip()
                if h.startswith('items='):
                    m = self.range_re.match(h)
                    if m:
                        s, e = None, None
                        if m.group(1) != '': s = int(m.group(1))
                        if m.group(2) != '': e = int(m.group(2))
                        request_range = (s, e)
                    else:
                        resp = rc.BAD_REQUEST
                        resp.write(' malformed range header')
                        return resp 

            elif self.paging_offset in request.GET and self.paging_limit in request.GET:
                """
                Alternatively, parse the query string for paging parameters. Here,
                we ask for an offset and a limit, so we need to convert this to a 
                fixed start and end to accomodate the slicing. Both parameters must 
                be specified, but either may be left empty, exclusively, to produce
                the following behaviors:

                    * ?offset=n&limit= -> tail of list, beginning at item n
                    * ?offset=&limit=n -> trailing n items of list

                """
                try: offset = int(request.GET[self.paging_offset])
                except (ValueError, TypeError): offset = None

                try: limit = int(request.GET[self.paging_limit])
                except (ValueError, TypeError): limit = None

                if offset != None and limit != None: request_range = (offset, offset + limit - 1)
                elif offset != None: request_range = (offset, None)
                elif limit != None: request_range = (None, limit)

            if request_range:
                def get_range(start, end, total):
                    """
                    Normalizes the range for queryset slicing and response
                    header generation.  Checks that constraints defined
                    by the RFC hold, or raises exceptions.
                    """
                    
                    if start != None and start < 0: raise BadRangeException('negative ranges not allowed')
                    if end != None and end < 0: raise BadRangeException('negative ranges not allowed')
                    
                    range_start = start
                    range_end = end
                    last = total - 1

                    if range_start != None and range_end != None:
                        """
                        Basic, well-formed range.  Make sure that requested range is
                        between 0 and last inclusive, and that start <= end. 
                        """
                        if range_start > last: raise BadRangeException("start gt last")
                        if range_start > range_end: raise BadRangeException("start lt end")
                        if range_end > last: range_end = last;

                    elif range_start != None:
                        """
                        Requsting range_start through last.  Make sure range_start is
                        valid and set range_end to last.
                        """
                        if range_start > last: raise BadRangeException("start gt last")
                        range_end = last

                    elif range_end != None:
                        """
                        Requesting range_end items from the tail of the result set.
                        If range_end > last, the entire resultset is returned.  otherwise
                        range_start must be last - range_end.
                        """
                        if range_end > last:
                            range_start = 0
                            range_end = last
                        else:
                            range_start = last - range_end + 1
                            range_end = last

                    else:
                        raise BadRangeException("no start or end")
                  
                    assert range_start != None
                    assert range_end != None 
                    return (range_start, range_end)


                try:
                    total = result.count()
                    start, end = get_range(request_range[0], request_range[1], total)
                    result = result[start:end + 1]
                    content_range = "items %i-%i/%i" % (start, end, total)
                except BadRangeException, e:
                    resp = rc.BAD_RANGE
                    resp.write("\n%s" % e.value)
                    return resp


        emitter, ct = Emitter.get(em_format)
        fields = handler.fields
        if hasattr(handler, 'list_fields') and (
                isinstance(result, list) or isinstance(result, QuerySet)):
            fields = handler.list_fields

>>>>>>> other
        srl = emitter(result, typemapper, handler, fields, anonymous)

        try:
            """
            Decide whether or not we want a generator here,
            or we just want to buffer up the entire result
            before sending it to the client. Won't matter for
            smaller datasets, but larger will have an impact.
            """
            if self.stream: stream = srl.stream_render(request)
            else: stream = srl.render(request)

            if not isinstance(stream, HttpResponse):
                resp = HttpResponse(stream, mimetype=ct, status=status_code)
            else:
                resp = stream

            resp.streaming = self.stream

            if content_range:
                resp.status_code = 206
                resp['Content-Range'] = content_range

            return resp
        except HttpStatusCode, e:
            return e.response

    @staticmethod
    def cleanup_request(request):
        """
        Removes `oauth_` keys from various dicts on the
        request object, and returns the sanitized version.
        """
        for method_type in ('GET', 'PUT', 'POST', 'DELETE'):
            block = getattr(request, method_type, { })

            if True in [ k.startswith("oauth_") for k in block.keys() ]:
                sanitized = block.copy()

                for k in sanitized.keys():
                    if k.startswith("oauth_"):
                        sanitized.pop(k)

                setattr(request, method_type, sanitized)

        return request

    # --

    def email_exception(self, reporter):
        subject = "Piston crash report"
        html = reporter.get_traceback_html()

        message = EmailMessage(settings.EMAIL_SUBJECT_PREFIX+subject,
                                html, settings.SERVER_EMAIL,
                                [ admin[1] for admin in settings.ADMINS ])

        message.content_subtype = 'html'
        message.send(fail_silently=True)


    def error_handler(self, e, request, meth, em_format):
        """
        Override this method to add handling of errors customized for your 
        needs
        """
        if isinstance(e, FormValidationError):
            return self.form_validation_response(e)

        elif isinstance(e, TypeError):
            result = rc.BAD_REQUEST
            hm = HandlerMethod(meth)
            sig = hm.signature

            msg = 'Method signature does not match.\n\n'

            if sig:
                msg += 'Signature should be: %s' % sig
            else:
                msg += 'Resource does not expect any parameters.'

            if self.display_errors:
                msg += '\n\nException was: %s' % str(e)

            result.content = format_error(msg)
            return result
        elif isinstance(e, Http404):
            return rc.NOT_FOUND

        elif isinstance(e, HttpStatusCode):
            return e.response
 
        else: 
            """
            On errors (like code errors), we'd like to be able to
            give crash reports to both admins and also the calling
            user. There's two setting parameters for this:

            Parameters::
             - `PISTON_EMAIL_ERRORS`: Will send a Django formatted
               error email to people in `settings.ADMINS`.
             - `PISTON_DISPLAY_ERRORS`: Will return a simple traceback
               to the caller, so he can tell you what error they got.

            If `PISTON_DISPLAY_ERRORS` is not enabled, the caller will
            receive a basic "500 Internal Server Error" message.
            """
            exc_type, exc_value, tb = sys.exc_info()
            rep = ExceptionReporter(request, exc_type, exc_value, tb.tb_next)
            if self.email_errors:
                self.email_exception(rep)
            if self.display_errors:
                return HttpResponseServerError(
                    format_error('\n'.join(rep.format_exception())))
            else:
                raise

########NEW FILE########
__FILENAME__ = signals
# Django imports
import django.dispatch 

# Piston imports
from utils import send_consumer_mail

def consumer_post_save(sender, instance, created, **kwargs):
    send_consumer_mail(instance)

def consumer_post_delete(sender, instance, **kwargs):
    instance.status = 'canceled'
    send_consumer_mail(instance)



########NEW FILE########
__FILENAME__ = store
import oauth

from models import Nonce, Token, Consumer
from models import generate_random, VERIFIER_SIZE

class DataStore(oauth.OAuthDataStore):
    """Layer between Python OAuth and Django database."""
    def __init__(self, oauth_request):
        self.signature = oauth_request.parameters.get('oauth_signature', None)
        self.timestamp = oauth_request.parameters.get('oauth_timestamp', None)
        self.scope = oauth_request.parameters.get('scope', 'all')

    def lookup_consumer(self, key):
        try:
            self.consumer = Consumer.objects.get(key=key)
            return self.consumer
        except Consumer.DoesNotExist:
            return None

    def lookup_token(self, token_type, token):
        if token_type == 'request':
            token_type = Token.REQUEST
        elif token_type == 'access':
            token_type = Token.ACCESS
        try:
            self.request_token = Token.objects.get(key=token, 
                                                   token_type=token_type)
            return self.request_token
        except Token.DoesNotExist:
            return None

    def lookup_nonce(self, oauth_consumer, oauth_token, nonce):
        if oauth_token is None:
            return None
        nonce, created = Nonce.objects.get_or_create(consumer_key=oauth_consumer.key, 
                                                     token_key=oauth_token.key,
                                                     key=nonce)
        if created:
            return None
        else:
            return nonce.key

    def fetch_request_token(self, oauth_consumer, oauth_callback):
        if oauth_consumer.key == self.consumer.key:
            self.request_token = Token.objects.create_token(consumer=self.consumer,
                                                            token_type=Token.REQUEST,
                                                            timestamp=self.timestamp)
            
            if oauth_callback:
                self.request_token.set_callback(oauth_callback)
            
            return self.request_token
        return None

    def fetch_access_token(self, oauth_consumer, oauth_token, oauth_verifier):
        if oauth_consumer.key == self.consumer.key \
        and oauth_token.key == self.request_token.key \
        and oauth_verifier == self.request_token.verifier \
        and self.request_token.is_approved:
            self.access_token = Token.objects.create_token(consumer=self.consumer,
                                                           token_type=Token.ACCESS,
                                                           timestamp=self.timestamp,
                                                           user=self.request_token.user)
            return self.access_token
        return None

    def authorize_request_token(self, oauth_token, user):
        if oauth_token.key == self.request_token.key:
            # authorize the request token in the store
            self.request_token.is_approved = True
            self.request_token.user = user
            self.request_token.verifier = generate_random(VERIFIER_SIZE)
            self.request_token.save()
            return self.request_token
        return None
########NEW FILE########
__FILENAME__ = test
# Django imports
import django.test.client as client
import django.test as test
from django.utils.http import urlencode

# Piston imports
from piston import oauth
from piston.models import Consumer, Token

# 3rd/Python party imports
import httplib2, urllib, cgi

URLENCODED_FORM_CONTENT = 'application/x-www-form-urlencoded'

class OAuthClient(client.Client):
    def __init__(self, consumer, token):
        self.token = oauth.OAuthToken(token.key, token.secret)
        self.consumer = oauth.OAuthConsumer(consumer.key, consumer.secret)
        self.signature = oauth.OAuthSignatureMethod_HMAC_SHA1()

        super(OAuthClient, self).__init__()

    def request(self, **request):
        # Figure out parameters from request['QUERY_STRING'] and FakePayload
        params = {}
        if request['REQUEST_METHOD'] in ('POST', 'PUT'):
            if request['CONTENT_TYPE'] == URLENCODED_FORM_CONTENT:
                payload = request['wsgi.input'].read()
                request['wsgi.input'] = client.FakePayload(payload)
                params = cgi.parse_qs(payload)

        url = "http://testserver" + request['PATH_INFO']

        req = oauth.OAuthRequest.from_consumer_and_token(
            self.consumer, token=self.token, 
            http_method=request['REQUEST_METHOD'], http_url=url, 
            parameters=params
        )

        req.sign_request(self.signature, self.consumer, self.token)
        headers = req.to_header()
        request['HTTP_AUTHORIZATION'] = headers['Authorization']

        return super(OAuthClient, self).request(**request)

    def post(self, path, data={}, content_type=None, follow=False, **extra):
        if content_type is None:
            content_type = URLENCODED_FORM_CONTENT

        if isinstance(data, dict):
            data = urlencode(data)
        
        return super(OAuthClient, self).post(path, data, content_type, follow, **extra)

class TestCase(test.TestCase):
    pass

class OAuthTestCase(TestCase):
    @property
    def oauth(self):
        return OAuthClient(self.consumer, self.token)


########NEW FILE########
__FILENAME__ = tests
# Django imports
from django.core import mail
from django.contrib.auth.models import User
from django.conf import settings
from django.template import loader, TemplateDoesNotExist
from django.http import HttpRequest, HttpResponse
from django.utils import simplejson

# Piston imports
from test import TestCase
from models import Consumer
from handler import BaseHandler
from utils import rc
from resource import Resource

class ConsumerTest(TestCase):
    fixtures = ['models.json']

    def setUp(self):
        self.consumer = Consumer()
        self.consumer.name = "Piston Test Consumer"
        self.consumer.description = "A test consumer for Piston."
        self.consumer.user = User.objects.get(pk=3)
        self.consumer.generate_random_codes()

    def _pre_test_email(self):
        template = "piston/mails/consumer_%s.txt" % self.consumer.status
        try:
            loader.render_to_string(template, {
                'consumer': self.consumer,
                'user': self.consumer.user
            })
            return True
        except TemplateDoesNotExist:
            """
            They haven't set up the templates, which means they might not want
            these emails sent.
            """
            return False

    def test_create_pending(self):
        """ Ensure creating a pending Consumer sends proper emails """
        # Verify if the emails can be sent
        if not self._pre_test_email():
            return

        # If it's pending we should have two messages in the outbox; one
        # to the consumer and one to the site admins.
        if len(settings.ADMINS):
            self.assertEquals(len(mail.outbox), 2)
        else:
            self.assertEquals(len(mail.outbox), 1)

        expected = "Your API Consumer for example.com is awaiting approval."
        self.assertEquals(mail.outbox[0].subject, expected)

    def test_delete_consumer(self):
        """ Ensure deleting a Consumer sends a cancel email """

        # Clear out the outbox before we test for the cancel email.
        mail.outbox = []

        # Delete the consumer, which should fire off the cancel email.
        self.consumer.delete()

        # Verify if the emails can be sent
        if not self._pre_test_email():
            return

        self.assertEquals(len(mail.outbox), 1)
        expected = "Your API Consumer for example.com has been canceled."
        self.assertEquals(mail.outbox[0].subject, expected)


class CustomResponseWithStatusCodeTest(TestCase):
     """
     Test returning content to be formatted and a custom response code from a 
     handler method. In this case we're returning 201 (created) and a dictionary 
     of data. This data will be formatted as json. 
     """

     def test_reponse_with_data_and_status_code(self):
         response_data = dict(complex_response=dict(something='good', 
             something_else='great'))

         class MyHandler(BaseHandler):
             """
             Handler which returns a response w/ both data and a status code (201)
             """
             allowed_methods = ('POST', )

             def create(self, request):
                 resp = rc.CREATED
                 resp.content = response_data
                 return resp

         resource = Resource(MyHandler)
         request = HttpRequest()
         request.method = 'POST'
         response = resource(request, emitter_format='json')

         self.assertEquals(201, response.status_code)
         self.assertTrue(response._is_string, "Expected response content to be a string")

         # compare the original data dict with the json response 
         # converted to a dict
         self.assertEquals(response_data, simplejson.loads(response.content))


class ErrorHandlerTest(TestCase):
    def test_customized_error_handler(self):
        """
        Throw a custom error from a handler method and catch (and format) it 
        in an overridden error_handler method on the associated Resource object
        """
        class GoAwayError(Exception):
            def __init__(self, name, reason):
                self.name = name
                self.reason = reason

        class MyHandler(BaseHandler):
            """
            Handler which raises a custom exception 
            """
            allowed_methods = ('GET',)

            def read(self, request):
                raise GoAwayError('Jerome', 'No one likes you')

        class MyResource(Resource):
            def error_handler(self, error, request, meth, em_format):
                # if the exception is our exeption then generate a 
                # custom response with embedded content that will be 
                # formatted as json 
                if isinstance(error, GoAwayError):
                    response = rc.FORBIDDEN
                    response.content = dict(error=dict(
                        name=error.name, 
                        message="Get out of here and dont come back", 
                        reason=error.reason
                    ))    

                    return response

                return super(MyResource, self).error_handler(error, request, meth)

        resource = MyResource(MyHandler)

        request = HttpRequest()
        request.method = 'GET'
        response = resource(request, emitter_format='json')

        self.assertEquals(401, response.status_code)

        # verify the content we got back can be converted back to json 
        # and examine the dictionary keys all exist as expected
        response_data = simplejson.loads(response.content)
        self.assertTrue('error' in response_data)
        self.assertTrue('name' in response_data['error'])
        self.assertTrue('message' in response_data['error'])
        self.assertTrue('reason' in response_data['error'])

    def test_type_error(self):
        """
        Verify that type errors thrown from a handler method result in a valid 
        HttpResonse object being returned from the error_handler method
        """
        class MyHandler(BaseHandler):
            def read(self, request):
                raise TypeError()

        request = HttpRequest()
        request.method = 'GET'
        response = Resource(MyHandler)(request)

        self.assertTrue(isinstance(response, HttpResponse), "Expected a response, not: %s" 
            % response)


    def test_other_error(self):
        """
        Verify that other exceptions thrown from a handler method result in a valid
        HttpResponse object being returned from the error_handler method
        """
        class MyHandler(BaseHandler):
            def read(self, request):
                raise Exception()

        resource = Resource(MyHandler)
        resource.display_errors = True
        resource.email_errors = False

        request = HttpRequest()
        request.method = 'GET'
        response = resource(request)

        self.assertTrue(isinstance(response, HttpResponse), "Expected a response, not: %s" 
            % response)

########NEW FILE########
__FILENAME__ = utils
import time
from django.http import HttpResponseNotAllowed, HttpResponseForbidden, HttpResponse, HttpResponseBadRequest
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django import get_version as django_version
from django.core.mail import send_mail, mail_admins
from django.conf import settings
from django.utils.translation import ugettext as _
from django.template import loader, TemplateDoesNotExist
from django.contrib.sites.models import Site
from decorator import decorator

from datetime import datetime, timedelta

__version__ = '0.2.3rc1'

def get_version():
    return __version__

def format_error(error):
    return u"Piston/%s (Django %s) crash report:\n\n%s" % \
        (get_version(), django_version(), error)

class rc_factory(object):
    """
    Status codes.
    """
    CODES = dict(ALL_OK = ('OK', 200),
                 CREATED = ('Created', 201),
                 DELETED = ('', 204), # 204 says "Don't send a body!"
                 BAD_REQUEST = ('Bad Request', 400),
                 FORBIDDEN = ('Forbidden', 401),
                 NOT_FOUND = ('Not Found', 404),
                 DUPLICATE_ENTRY = ('Conflict/Duplicate', 409),
                 NOT_HERE = ('Gone', 410),
                 BAD_RANGE = ('Unsatifiable Range', 416),
                 INTERNAL_ERROR = ('Internal Error', 500),
                 NOT_IMPLEMENTED = ('Not Implemented', 501),
                 THROTTLED = ('Throttled', 503))

    def __getattr__(self, attr):
        """
        Returns a fresh `HttpResponse` when getting 
        an "attribute". This is backwards compatible
        with 0.2, which is important.
        """
        try:
            (r, c) = self.CODES.get(attr)
        except TypeError:
            raise AttributeError(attr)

        class HttpResponseWrapper(HttpResponse):
            """
            Wrap HttpResponse and make sure that the internal _is_string 
            flag is updated when the _set_content method (via the content 
            property) is called
            """
            def _set_content(self, content):
                """
                Set the _container and _is_string properties based on the 
                type of the value parameter. This logic is in the construtor
                for HttpResponse, but doesn't get repeated when setting 
                HttpResponse.content although this bug report (feature request)
                suggests that it should: http://code.djangoproject.com/ticket/9403 
                """
                if not isinstance(content, basestring) and hasattr(content, '__iter__'):
                    self._container = content
                    self._is_string = False
                else:
                    self._container = [content]
                    self._is_string = True

            content = property(HttpResponse._get_content, _set_content)            

        return HttpResponseWrapper(r, content_type='text/plain', status=c)
    
rc = rc_factory()
    
class FormValidationError(Exception):
    def __init__(self, form):
        self.form = form

class HttpStatusCode(Exception):
    def __init__(self, response):
        self.response = response

def validate(v_form, operation='POST'):
    @decorator
    def wrap(f, self, request, *a, **kwa):
        form = v_form(getattr(request, operation))
    
        if form.is_valid():
            setattr(request, 'form', form)
            return f(self, request, *a, **kwa)
        else:
            raise FormValidationError(form)
    return wrap

def throttle(max_requests, timeout=60*60, extra=''):
    """
    Simple throttling decorator, caches
    the amount of requests made in cache.
    
    If used on a view where users are required to
    log in, the username is used, otherwise the
    IP address of the originating request is used.
    
    Parameters::
     - `max_requests`: The maximum number of requests
     - `timeout`: The timeout for the cache entry (default: 1 hour)
    """
    @decorator
    def wrap(f, self, request, *args, **kwargs):
        if request.user.is_authenticated():
            ident = request.user.username
        else:
            ident = request.META.get('REMOTE_ADDR', None)
    
        if hasattr(request, 'throttle_extra'):
            """
            Since we want to be able to throttle on a per-
            application basis, it's important that we realize
            that `throttle_extra` might be set on the request
            object. If so, append the identifier name with it.
            """
            ident += ':%s' % str(request.throttle_extra)
        
        if ident:
            """
            Preferrably we'd use incr/decr here, since they're
            atomic in memcached, but it's in django-trunk so we
            can't use it yet. If someone sees this after it's in
            stable, you can change it here.
            """
            ident += ':%s' % extra
    
            now = time.time()
            count, expiration = cache.get(ident, (1, None))

            if expiration is None:
                expiration = now + timeout

            if count >= max_requests and expiration > now:
                t = rc.THROTTLED
                wait = int(expiration - now)
                t.content = 'Throttled, wait %d seconds.' % wait
                t['Retry-After'] = wait
                return t

            cache.set(ident, (count+1, expiration), (expiration - now))
    
        return f(self, request, *args, **kwargs)
    return wrap

def coerce_put_post(request):
    """
    Django doesn't particularly understand REST.
    In case we send data over PUT, Django won't
    actually look at the data and load it. We need
    to twist its arm here.
    
    The try/except abominiation here is due to a bug
    in mod_python. This should fix it.
    """
    if request.method == "PUT":
        # Bug fix: if _load_post_and_files has already been called, for
        # example by middleware accessing request.POST, the below code to
        # pretend the request is a POST instead of a PUT will be too late
        # to make a difference. Also calling _load_post_and_files will result 
        # in the following exception:
        #   AttributeError: You cannot set the upload handlers after the upload has been processed.
        # The fix is to check for the presence of the _post field which is set 
        # the first time _load_post_and_files is called (both by wsgi.py and 
        # modpython.py). If it's set, the request has to be 'reset' to redo
        # the query value parsing in POST mode.
        if hasattr(request, '_post'):
            del request._post
            del request._files
        
        try:
            request.method = "POST"
            request._load_post_and_files()
            request.method = "PUT"
        except AttributeError:
            request.META['REQUEST_METHOD'] = 'POST'
            request._load_post_and_files()
            request.META['REQUEST_METHOD'] = 'PUT'
            
        request.PUT = request.POST


class MimerDataException(Exception):
    """
    Raised if the content_type and data don't match
    """
    pass

class Mimer(object):
    TYPES = dict()
    
    def __init__(self, request):
        self.request = request
        
    def is_multipart(self):
        content_type = self.content_type()

        if content_type is not None:
            return content_type.lstrip().startswith('multipart')

        return False

    def loader_for_type(self, ctype):
        """
        Gets a function ref to deserialize content
        for a certain mimetype.
        """
        for loadee, mimes in Mimer.TYPES.iteritems():
            for mime in mimes:
                if ctype.startswith(mime):
                    return loadee
                    
    def content_type(self):
        """
        Returns the content type of the request in all cases where it is
        different than a submitted form - application/x-www-form-urlencoded
        """
        type_formencoded = "application/x-www-form-urlencoded"

        ctype = self.request.META.get('CONTENT_TYPE', type_formencoded)
        
        if type_formencoded in ctype:
            return None
        
        return ctype

    def translate(self):
        """
        Will look at the `Content-type` sent by the client, and maybe
        deserialize the contents into the format they sent. This will
        work for JSON, YAML, XML and Pickle. Since the data is not just
        key-value (and maybe just a list), the data will be placed on
        `request.data` instead, and the handler will have to read from
        there.
        
        It will also set `request.content_type` so the handler has an easy
        way to tell what's going on. `request.content_type` will always be
        None for form-encoded and/or multipart form data (what your browser sends.)
        """    
        ctype = self.content_type()
        self.request.content_type = ctype
        
        if not self.is_multipart() and ctype:
            loadee = self.loader_for_type(ctype)
            
            if loadee:
                try:
                    self.request.data = loadee(self.request.raw_post_data)
                        
                    # Reset both POST and PUT from request, as its
                    # misleading having their presence around.
                    self.request.POST = self.request.PUT = dict()
                except (TypeError, ValueError):
                    # This also catches if loadee is None.
                    raise MimerDataException
            else:
                self.request.data = None

        return self.request
                
    @classmethod
    def register(cls, loadee, types):
        cls.TYPES[loadee] = types
        
    @classmethod
    def unregister(cls, loadee):
        return cls.TYPES.pop(loadee)

def translate_mime(request):
    request = Mimer(request).translate()
    
def require_mime(*mimes):
    """
    Decorator requiring a certain mimetype. There's a nifty
    helper called `require_extended` below which requires everything
    we support except for post-data via form.
    """
    @decorator
    def wrap(f, self, request, *args, **kwargs):
        m = Mimer(request)
        realmimes = set()

        rewrite = { 'json':   'application/json',
                    'yaml':   'application/x-yaml',
                    'xml':    'text/xml',
                    'pickle': 'application/python-pickle' }

        for idx, mime in enumerate(mimes):
            realmimes.add(rewrite.get(mime, mime))

        if not m.content_type() in realmimes:
            return rc.BAD_REQUEST

        return f(self, request, *args, **kwargs)
    return wrap

require_extended = require_mime('json', 'yaml', 'xml', 'pickle')
    
def send_consumer_mail(consumer):
    """
    Send a consumer an email depending on what their status is.
    """
    try:
        subject = settings.PISTON_OAUTH_EMAIL_SUBJECTS[consumer.status]
    except AttributeError:
        subject = "Your API Consumer for %s " % Site.objects.get_current().name
        if consumer.status == "accepted":
            subject += "was accepted!"
        elif consumer.status == "canceled":
            subject += "has been canceled."
        elif consumer.status == "rejected":
            subject += "has been rejected."
        else: 
            subject += "is awaiting approval."

    template = "piston/mails/consumer_%s.txt" % consumer.status    
    
    try:
        body = loader.render_to_string(template, 
            { 'consumer' : consumer, 'user' : consumer.user })
    except TemplateDoesNotExist:
        """ 
        They haven't set up the templates, which means they might not want
        these emails sent.
        """
        return 

    try:
        sender = settings.PISTON_FROM_EMAIL
    except AttributeError:
        sender = settings.DEFAULT_FROM_EMAIL

    if consumer.user:
        send_mail(_(subject), body, sender, [consumer.user.email], fail_silently=True)

    if consumer.status == 'pending' and len(settings.ADMINS):
        mail_admins(_(subject), body, fail_silently=True)

    if settings.DEBUG and consumer.user:
        print "Mail being sent, to=%s" % consumer.user.email
        print "Subject: %s" % _(subject)
        print body

class BadRangeException(Exception):
    """
    Raised when a partial get contains
    an unsatifiable range
    """
    def __init__(self, value):
        self.value = value


########NEW FILE########
__FILENAME__ = validate_jsonp
# -*- coding: utf-8 -*-

# Placed into the Public Domain by tav <tav@espians.com>

"""Validate Javascript Identifiers for use as JSON-P callback parameters."""

import re
from unicodedata import category

# ------------------------------------------------------------------------------
# javascript identifier unicode categories and "exceptional" chars
# ------------------------------------------------------------------------------

valid_jsid_categories_start = frozenset([
    'Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nl'
    ])

valid_jsid_categories = frozenset([
    'Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nl', 'Mn', 'Mc', 'Nd', 'Pc'
    ])

valid_jsid_chars = ('$', '_')

# ------------------------------------------------------------------------------
# regex to find array[index] patterns
# ------------------------------------------------------------------------------

array_index_regex = re.compile(r'\[[0-9]+\]$')

has_valid_array_index = array_index_regex.search
replace_array_index = array_index_regex.sub

# ------------------------------------------------------------------------------
# javascript reserved words -- including keywords and null/boolean literals
# ------------------------------------------------------------------------------

is_reserved_js_word = frozenset([

    'abstract', 'boolean', 'break', 'byte', 'case', 'catch', 'char', 'class',
    'const', 'continue', 'debugger', 'default', 'delete', 'do', 'double',
    'else', 'enum', 'export', 'extends', 'false', 'final', 'finally', 'float',
    'for', 'function', 'goto', 'if', 'implements', 'import', 'in', 'instanceof',
    'int', 'interface', 'long', 'native', 'new', 'null', 'package', 'private',
    'protected', 'public', 'return', 'short', 'static', 'super', 'switch',
    'synchronized', 'this', 'throw', 'throws', 'transient', 'true', 'try',
    'typeof', 'var', 'void', 'volatile', 'while', 'with',

    # potentially reserved in a future version of the ES5 standard
    # 'let', 'yield'
    
    ]).__contains__

# ------------------------------------------------------------------------------
# the core validation functions
# ------------------------------------------------------------------------------

def is_valid_javascript_identifier(identifier, escape=r'\u', ucd_cat=category):
    """Return whether the given ``id`` is a valid Javascript identifier."""

    if not identifier:
        return False

    if not isinstance(identifier, unicode):
        try:
            identifier = unicode(identifier, 'utf-8')
        except UnicodeDecodeError:
            return False

    if escape in identifier:

        new = []; add_char = new.append
        split_id = identifier.split(escape)
        add_char(split_id.pop(0))

        for segment in split_id:
            if len(segment) < 4:
                return False
            try:
                add_char(unichr(int('0x' + segment[:4], 16)))
            except Exception:
                return False
            add_char(segment[4:])
            
        identifier = u''.join(new)

    if is_reserved_js_word(identifier):
        return False

    first_char = identifier[0]

    if not ((first_char in valid_jsid_chars) or
            (ucd_cat(first_char) in valid_jsid_categories_start)):
        return False

    for char in identifier[1:]:
        if not ((char in valid_jsid_chars) or
                (ucd_cat(char) in valid_jsid_categories)):
            return False

    return True


def is_valid_jsonp_callback_value(value):
    """Return whether the given ``value`` can be used as a JSON-P callback."""

    for identifier in value.split(u'.'):
        while '[' in identifier:
            if not has_valid_array_index(identifier):
                return False
            identifier = replace_array_index(u'', identifier)
        if not is_valid_javascript_identifier(identifier):
            return False

    return True

# ------------------------------------------------------------------------------
# test
# ------------------------------------------------------------------------------

def test():
    """
    The function ``is_valid_javascript_identifier`` validates a given identifier
    according to the latest draft of the ECMAScript 5 Specification:

      >>> is_valid_javascript_identifier('hello')
      True

      >>> is_valid_javascript_identifier('alert()')
      False

      >>> is_valid_javascript_identifier('a-b')
      False

      >>> is_valid_javascript_identifier('23foo')
      False

      >>> is_valid_javascript_identifier('foo23')
      True

      >>> is_valid_javascript_identifier('$210')
      True

      >>> is_valid_javascript_identifier(u'Stra\u00dfe')
      True

      >>> is_valid_javascript_identifier(r'\u0062') # u'b'
      True

      >>> is_valid_javascript_identifier(r'\u62')
      False

      >>> is_valid_javascript_identifier(r'\u0020')
      False

      >>> is_valid_javascript_identifier('_bar')
      True

      >>> is_valid_javascript_identifier('some_var')
      True

      >>> is_valid_javascript_identifier('$')
      True

    But ``is_valid_jsonp_callback_value`` is the function you want to use for
    validating JSON-P callback parameter values:

      >>> is_valid_jsonp_callback_value('somevar')
      True

      >>> is_valid_jsonp_callback_value('function')
      False

      >>> is_valid_jsonp_callback_value(' somevar')
      False

    It supports the possibility of '.' being present in the callback name, e.g.

      >>> is_valid_jsonp_callback_value('$.ajaxHandler')
      True

      >>> is_valid_jsonp_callback_value('$.23')
      False

    As well as the pattern of providing an array index lookup, e.g.

      >>> is_valid_jsonp_callback_value('array_of_functions[42]')
      True

      >>> is_valid_jsonp_callback_value('array_of_functions[42][1]')
      True

      >>> is_valid_jsonp_callback_value('$.ajaxHandler[42][1].foo')
      True

      >>> is_valid_jsonp_callback_value('array_of_functions[42]foo[1]')
      False

      >>> is_valid_jsonp_callback_value('array_of_functions[]')
      False

      >>> is_valid_jsonp_callback_value('array_of_functions["key"]')
      False

    Enjoy!

    """

if __name__ == '__main__':
    import doctest
    doctest.testmod()
########NEW FILE########
__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.

$Id$
"""

import os, shutil, sys, tempfile, urllib2

tmpeggs = tempfile.mkdtemp()

is_jython = sys.platform.startswith('java')

try:
    import pkg_resources
except ImportError:
    ez = {}
    exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                         ).read() in ez
    ez['use_setuptools'](to_dir=tmpeggs, download_delay=0)

    import pkg_resources

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
        else:
            return c
else:
    def quote (c):
        return c

cmd = 'from setuptools.command.easy_install import main; main()'
ws  = pkg_resources.working_set

if len(sys.argv) > 2 and sys.argv[1] == '--version':
    VERSION = ' == %s' % sys.argv[2]
    args = sys.argv[3:] + ['bootstrap']
else:
    VERSION = ''
    args = sys.argv[1:] + ['bootstrap']

if is_jython:
    import subprocess

    assert subprocess.Popen([sys.executable] + ['-c', quote(cmd), '-mqNxd',
           quote(tmpeggs), 'zc.buildout' + VERSION],
           env=dict(os.environ,
               PYTHONPATH=
               ws.find(pkg_resources.Requirement.parse('setuptools')).location
               ),
           ).wait() == 0

else:
    assert os.spawnle(
        os.P_WAIT, sys.executable, quote (sys.executable),
        '-c', quote (cmd), '-mqNxd', quote (tmpeggs), 'zc.buildout' + VERSION,
        dict(os.environ,
            PYTHONPATH=
            ws.find(pkg_resources.Requirement.parse('setuptools')).location
            ),
        ) == 0

ws.add_entry(tmpeggs)
ws.require('zc.buildout' + VERSION)
import zc.buildout.buildout
zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = forms
from django import forms


class EchoForm(forms.Form):
    msg = forms.CharField(max_length=128)


########NEW FILE########
__FILENAME__ = handlers
from django.core.paginator import Paginator

from piston.handler import BaseHandler
from piston.utils import rc, validate

from models import TestModel, ExpressiveTestModel, Comment, InheritedModel, PlainOldObject, Issue58Model, ListFieldsModel
from forms import EchoForm
from test_project.apps.testapp import signals

class EntryHandler(BaseHandler):
    model = TestModel
    allowed_methods = ['GET', 'PUT', 'POST']

    def read(self, request, pk=None):
        signals.entry_request_started.send(sender=self, request=request)
        if pk is not None:
            return TestModel.objects.get(pk=int(pk))
        paginator = Paginator(TestModel.objects.all(), 25)
        return paginator.page(int(request.GET.get('page', 1))).object_list

    def update(self, request, pk):
        signals.entry_request_started.send(sender=self, request=request)

    def create(self, request):
        signals.entry_request_started.send(sender=self, request=request)

class ExpressiveHandler(BaseHandler):
    model = ExpressiveTestModel
    fields = ('title', 'content', ('comments', ('content',)))

    @classmethod
    def comments(cls, em):
        return em.comments.all()

    def read(self, request):
        inst = ExpressiveTestModel.objects.all()
        
        return inst
        
    def create(self, request):
        if request.content_type and request.data:
            data = request.data
            
            em = self.model(title=data['title'], content=data['content'])
            em.save()
            
            for comment in data['comments']:
                Comment(parent=em, content=comment['content']).save()
                
            return rc.CREATED
        else:
            super(ExpressiveHandler, self).create(request)
            
class AbstractHandler(BaseHandler):
    fields = ('id', 'some_other', 'some_field')
    model = InheritedModel
    
    def read(self, request, id_=None):
        if id_:
            return self.model.objects.get(pk=id_)
        else:
            return super(AbstractHandler, self).read(request)

class PlainOldObjectHandler(BaseHandler):
    allowed_methods = ('GET',)
    fields = ('type', 'field')
    model = PlainOldObject
    
    def read(self, request):
        return self.model()

class EchoHandler(BaseHandler):
    allowed_methods = ('GET', 'HEAD')

    @validate(EchoForm, 'GET')
    def read(self, request):
        return {'msg': request.form.cleaned_data['msg']}

class ListFieldsHandler(BaseHandler):
    model = ListFieldsModel
    fields = ('id','kind','variety','color')
    list_fields = ('id','variety')

class Issue58Handler(BaseHandler):
    model = Issue58Model

    def read(self, request):
        return Issue58Model.objects.all()
                
    def create(self, request):
        if request.content_type:
            data = request.data
            em = self.model(read=data['read'], model=data['model'])
            em.save()
            return rc.CREATED
        else:
            super(Issue58Model, self).create(request)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class TestModel(models.Model):
    test1 = models.CharField(max_length=1, blank=True, null=True)
    test2 = models.CharField(max_length=1, blank=True, null=True)
    
class ExpressiveTestModel(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    never_shown = models.TextField()
    
class Comment(models.Model):
    parent = models.ForeignKey(ExpressiveTestModel, related_name='comments')
    content = models.TextField()

class AbstractModel(models.Model):
    some_field = models.CharField(max_length=32, default='something here')
    
    class Meta:
        abstract = True
        
class InheritedModel(AbstractModel):
    some_other = models.CharField(max_length=32, default='something else')
    
    class Meta:
        db_table = 'testing_abstracts'

class PlainOldObject(object):
    def __emittable__(self):
        return {'type': 'plain',
                'field': 'a field'}

class ListFieldsModel(models.Model):
    kind = models.CharField(max_length=15)
    variety = models.CharField(max_length=15)
    color = models.CharField(max_length=15)

class Issue58Model(models.Model):
    read = models.BooleanField(default=False)
    model = models.CharField(max_length=1, blank=True, null=True)

########NEW FILE########
__FILENAME__ = signals
import django.dispatch

entry_request_started = django.dispatch.Signal(providing_args=['request'])

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import simplejson
from django.conf import settings

from piston import oauth
from piston.models import Consumer, Token
from piston.forms import OAuthAuthenticationForm

try:
    import yaml
except ImportError:
    print "Can't run YAML testsuite"
    yaml = None

import urllib, base64

from test_project.apps.testapp.models import TestModel, ExpressiveTestModel, Comment, InheritedModel, Issue58Model, ListFieldsModel
from test_project.apps.testapp import signals

class MainTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('admin', 'admin@world.com', 'admin')
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.is_active = True
        self.user.save()
        self.auth_string = 'Basic %s' % base64.encodestring('admin:admin').rstrip()

        if hasattr(self, 'init_delegate'):
            self.init_delegate()
        
    def tearDown(self):
        self.user.delete()



class OAuthTests(MainTests):
    signature_method = oauth.OAuthSignatureMethod_HMAC_SHA1()

    def setUp(self):
        super(OAuthTests, self).setUp()

        self.consumer = Consumer.objects.create_consumer('Test Consumer')
        self.consumer.status = 'accepted'
        self.consumer.save()

    def tearDown(self):
        super(OAuthTests, self).tearDown()
        self.consumer.delete()

    def test_handshake(self):
        '''Test the OAuth handshake procedure
        '''
        oaconsumer = oauth.OAuthConsumer(self.consumer.key, self.consumer.secret)

        # Get a request key...
        request = oauth.OAuthRequest.from_consumer_and_token(oaconsumer,
                http_url='http://testserver/api/oauth/request_token')
        request.sign_request(self.signature_method, oaconsumer, None)

        response = self.client.get('/api/oauth/request_token', request.parameters)
        oatoken = oauth.OAuthToken.from_string(response.content)

        token = Token.objects.get(key=oatoken.key, token_type=Token.REQUEST)
        self.assertEqual(token.secret, oatoken.secret)

        # Simulate user authentication...
        self.failUnless(self.client.login(username='admin', password='admin'))
        request = oauth.OAuthRequest.from_token_and_callback(token=oatoken,
                callback='http://printer.example.com/request_token_ready',
                http_url='http://testserver/api/oauth/authorize')
        request.sign_request(self.signature_method, oaconsumer, oatoken)

        # Request the login page
# TODO: Parse the response to make sure all the fields exist
#        response = self.client.get('/api/oauth/authorize', {
#            'oauth_token': oatoken.key,
#            'oauth_callback': 'http://printer.example.com/request_token_ready',
#            })

        response = self.client.post('/api/oauth/authorize', {
            'oauth_token': oatoken.key,
            'oauth_callback': 'http://printer.example.com/request_token_ready',
            'csrf_signature': OAuthAuthenticationForm.get_csrf_signature(settings.SECRET_KEY, oatoken.key),
            'authorize_access': 1,
            })

        # Response should be a redirect...
        self.assertEqual(302, response.status_code)
        self.failUnless(response['Location'].startswith("http://printer.example.com/request_token_ready?"))
        self.failUnless(('oauth_token='+oatoken.key in response['Location']))
        
        # Actually we can't test this last part, since it's 1.0a.
        # Obtain access token...
#        request = oauth.OAuthRequest.from_consumer_and_token(oaconsumer, token=oatoken,
#                http_url='http://testserver/api/oauth/access_token')
#        request.sign_request(self.signature_method, oaconsumer, oatoken)
#        response = self.client.get('/api/oauth/access_token', request.parameters)

#        oa_atoken = oauth.OAuthToken.from_string(response.content)
#        atoken = Token.objects.get(key=oa_atoken.key, token_type=Token.ACCESS)
#        self.assertEqual(atoken.secret, oa_atoken.secret)

class BasicAuthTest(MainTests):

    def test_invalid_auth_header(self):
        response = self.client.get('/api/entries/')
        self.assertEquals(response.status_code, 401)

        # no space
        bad_auth_string = 'Basic%s' % base64.encodestring('admin:admin').rstrip()
        response = self.client.get('/api/entries/',
            HTTP_AUTHORIZATION=bad_auth_string)
        self.assertEquals(response.status_code, 401)

        # no colon
        bad_auth_string = 'Basic %s' % base64.encodestring('adminadmin').rstrip()
        response = self.client.get('/api/entries/',
            HTTP_AUTHORIZATION=bad_auth_string)
        self.assertEquals(response.status_code, 401)

        # non base64 data
        bad_auth_string = 'Basic FOOBARQ!'
        response = self.client.get('/api/entries/',
            HTTP_AUTHORIZATION=bad_auth_string)
        self.assertEquals(response.status_code, 401)

class TestMultipleAuthenticators(MainTests):
    def test_both_authenticators(self):
        for username, password in (('admin', 'admin'), 
                                   ('admin', 'secr3t'),
                                   ('admin', 'user'),
                                   ('admin', 'allwork'),
                                   ('admin', 'thisisneat')):
            auth_string = 'Basic %s' % base64.encodestring('%s:%s' % (username, password)).rstrip()

            response = self.client.get('/api/multiauth/',
                HTTP_AUTHORIZATION=auth_string)

            self.assertEquals(response.status_code, 200, 'Failed with combo of %s:%s' % (username, password))

class MultiXMLTests(MainTests):
    def init_delegate(self):
        self.t1_data = TestModel()
        self.t1_data.save()
        self.t2_data = TestModel()
        self.t2_data.save()

    def test_multixml(self):
        expected = '<?xml version="1.0" encoding="utf-8"?>\n<response><resource><test1>None</test1><test2>None</test2></resource><resource><test1>None</test1><test2>None</test2></resource></response>'
        result = self.client.get('/api/entries.xml',
                HTTP_AUTHORIZATION=self.auth_string).content
        self.assertEquals(expected, result)

    def test_singlexml(self):
        obj = TestModel.objects.all()[0]
        expected = '<?xml version="1.0" encoding="utf-8"?>\n<response><test1>None</test1><test2>None</test2></response>'
        result = self.client.get('/api/entry-%d.xml' % (obj.pk,),
                HTTP_AUTHORIZATION=self.auth_string).content
        self.assertEquals(expected, result)

class AbstractBaseClassTests(MainTests):
    def init_delegate(self):
        self.ab1 = InheritedModel()
        self.ab1.save()
        self.ab2 = InheritedModel()
        self.ab2.save()
        
    def test_field_presence(self):
        result = self.client.get('/api/abstract.json',
                HTTP_AUTHORIZATION=self.auth_string).content
                
        expected = """[
    {
        "id": 1, 
        "some_other": "something else", 
        "some_field": "something here"
    }, 
    {
        "id": 2, 
        "some_other": "something else", 
        "some_field": "something here"
    }
]"""
        
        self.assertEquals(result, expected)

    def test_specific_id(self):
        ids = (1, 2)
        be = """{
    "id": %d, 
    "some_other": "something else", 
    "some_field": "something here"
}"""
        
        for id_ in ids:
            result = self.client.get('/api/abstract/%d.json' % id_,
                    HTTP_AUTHORIZATION=self.auth_string).content
                    
            expected = be % id_
            
            self.assertEquals(result, expected)

class IncomingExpressiveTests(MainTests):
    def init_delegate(self):
        e1 = ExpressiveTestModel(title="foo", content="bar")
        e1.save()
        e2 = ExpressiveTestModel(title="foo2", content="bar2")
        e2.save()

    def test_incoming_json(self):
        outgoing = simplejson.dumps({ 'title': 'test', 'content': 'test',
                                      'comments': [ { 'content': 'test1' },
                                                    { 'content': 'test2' } ] })
    
        expected = """[
    {
        "content": "bar", 
        "comments": [], 
        "title": "foo"
    }, 
    {
        "content": "bar2", 
        "comments": [], 
        "title": "foo2"
    }
]"""
    
        result = self.client.get('/api/expressive.json',
            HTTP_AUTHORIZATION=self.auth_string).content

        self.assertEquals(result, expected)
        
        resp = self.client.post('/api/expressive.json', outgoing, content_type='application/json',
            HTTP_AUTHORIZATION=self.auth_string)
            
        self.assertEquals(resp.status_code, 201)
        
        expected = """[
    {
        "content": "bar", 
        "comments": [], 
        "title": "foo"
    }, 
    {
        "content": "bar2", 
        "comments": [], 
        "title": "foo2"
    }, 
    {
        "content": "test", 
        "comments": [
            {
                "content": "test1"
            }, 
            {
                "content": "test2"
            }
        ], 
        "title": "test"
    }
]"""
        
        result = self.client.get('/api/expressive.json', 
            HTTP_AUTHORIZATION=self.auth_string).content
            
        self.assertEquals(result, expected)

    def test_incoming_invalid_json(self):
        resp = self.client.post('/api/expressive.json',
            'foo',
            HTTP_AUTHORIZATION=self.auth_string,
            content_type='application/json')
        self.assertEquals(resp.status_code, 400)

    def test_incoming_yaml(self):
        if not yaml:
            return
            
        expected = """- comments: []
  content: bar
  title: foo
- comments: []
  content: bar2
  title: foo2
"""
          
        self.assertEquals(self.client.get('/api/expressive.yaml',
            HTTP_AUTHORIZATION=self.auth_string).content, expected)

        outgoing = yaml.dump({ 'title': 'test', 'content': 'test',
                                      'comments': [ { 'content': 'test1' },
                                                    { 'content': 'test2' } ] })
            
        resp = self.client.post('/api/expressive.json', outgoing, content_type='application/x-yaml',
            HTTP_AUTHORIZATION=self.auth_string)
        
        self.assertEquals(resp.status_code, 201)
        
        expected = """- comments: []
  content: bar
  title: foo
- comments: []
  content: bar2
  title: foo2
- comments:
  - {content: test1}
  - {content: test2}
  content: test
  title: test
"""
        self.assertEquals(self.client.get('/api/expressive.yaml', 
            HTTP_AUTHORIZATION=self.auth_string).content, expected)

    def test_incoming_invalid_yaml(self):
        resp = self.client.post('/api/expressive.yaml',
            '  8**sad asj lja foo',
            HTTP_AUTHORIZATION=self.auth_string,
            content_type='application/x-yaml')
        self.assertEquals(resp.status_code, 400)

class Issue36RegressionTests(MainTests):
    """
    This testcase addresses #36 in django-piston where request.FILES is passed
    empty to the handler if the request.method is PUT.
    """
    def fetch_request(self, sender, request, *args, **kwargs):
        self.request = request

    def setUp(self):
        super(self.__class__, self).setUp()
        self.data = TestModel()
        self.data.save()
        # Register to the WSGIRequest signals to get the latest generated
        # request object.
        signals.entry_request_started.connect(self.fetch_request)

    def tearDown(self):
        super(self.__class__, self).tearDown()
        self.data.delete()
        signals.entry_request_started.disconnect(self.fetch_request)
    
    def test_simple(self):
        # First try it with POST to see if it works there
        if True:
            fp = open(__file__, 'r')
            try:
                response = self.client.post('/api/entries.xml',
                        {'file':fp}, HTTP_AUTHORIZATION=self.auth_string)
                self.assertEquals(1, len(self.request.FILES), 'request.FILES on POST is empty when it should contain 1 file')
            finally:
                fp.close()

        if not hasattr(self.client, 'put'):
            import warnings
            warnings.warn('Issue36RegressionTest partially requires Django 1.1 or newer. Skipped.')
            return

        # ... and then with PUT
        fp = open(__file__, 'r')
        try:
            response = self.client.put('/api/entry-%d.xml' % self.data.pk,
                    {'file': fp}, HTTP_AUTHORIZATION=self.auth_string)
            self.assertEquals(1, len(self.request.FILES), 'request.FILES on PUT is empty when it should contain 1 file')
        finally:
            fp.close()

class ValidationTest(MainTests):
    def test_basic_validation_fails(self):
        resp = self.client.get('/api/echo')
        self.assertEquals(resp.status_code, 400)
        self.assertEquals(resp.content, 'Bad Request <ul class="errorlist">'
            '<li>msg<ul class="errorlist"><li>This field is required.</li>'
            '</ul></li></ul>')

    def test_basic_validation_succeeds(self):
        data = {'msg': 'donuts!'}
        resp = self.client.get('/api/echo', data)
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(data, simplejson.loads(resp.content))

class PlainOldObject(MainTests):
    def test_plain_object_serialization(self):
        resp = self.client.get('/api/popo')
        self.assertEquals(resp.status_code, 200)
        self.assertEquals({'type': 'plain', 'field': 'a field'}, simplejson.loads(resp.content))

class ListFieldsTest(MainTests):
    def init_delegate(self):
        ListFieldsModel(kind='fruit', variety='apple', color='green').save()
        ListFieldsModel(kind='vegetable', variety='carrot', color='orange').save()
        ListFieldsModel(kind='animal', variety='dog', color='brown').save()

    def test_single_item(self):
        expect = '''{
    "color": "green", 
    "kind": "fruit", 
    "id": 1, 
    "variety": "apple"
}'''
        resp = self.client.get('/api/list_fields/1')
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp.content, expect)


    def test_multiple_items(self):
        expect = '''[
    {
        "id": 1, 
        "variety": "apple"
    }, 
    {
        "id": 2, 
        "variety": "carrot"
    }, 
    {
        "id": 3, 
        "variety": "dog"
    }
]'''
        resp = self.client.get('/api/list_fields')
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp.content, expect)
        
class ErrorHandlingTests(MainTests):
    """Test proper handling of errors by Resource"""

    def test_response_not_allowed(self):
        resp = self.client.post('/api/echo')
        self.assertEquals(resp.status_code, 405)
        self.assertEquals(resp['Allow'], 'GET, HEAD')

    def test_not_found_because_of_unexpected_http_method(self):
        # not using self.client.head because it is not present in Django 1.0
        resp = self.client.get('/api/echo', REQUEST_METHOD='HEAD')
        self.assertEquals(resp.status_code, 404)
        self.assertEquals(resp.content, '')


class Issue58ModelTests(MainTests):
    """
    This testcase addresses #58 in django-piston where if a model
    has one of the ['read','update','delete','create'] defined
    it make piston crash with a `TypeError`
    """
    def init_delegate(self):
        m1 = Issue58Model(read=True,model='t') 
        m1.save()
        m2 = Issue58Model(read=False,model='f')
        m2.save()

    def test_incoming_json(self):
        outgoing = simplejson.dumps({ 'read': True, 'model': 'T'})

        expected = """[
    {
        "read": true, 
        "model": "t"
    }, 
    {
        "read": false, 
        "model": "f"
    }
]"""

        # test GET
        result = self.client.get('/api/issue58.json',
                                HTTP_AUTHORIZATION=self.auth_string).content
        self.assertEquals(result, expected)

        # test POST
        resp = self.client.post('/api/issue58.json', outgoing, content_type='application/json',
                                HTTP_AUTHORIZATION=self.auth_string)
        self.assertEquals(resp.status_code, 201)
        
class PartialGetTests(MainTests):
    """
    This tests the partial GET feature
    """
    def init_delegate(self):
        ListFieldsModel(kind='fruit', variety='apple', color='green').save()
        ListFieldsModel(kind='vegetable', variety='carrot', color='orange').save()
        ListFieldsModel(kind='animal', variety='dog', color='brown').save()

    def assertRange(self, resp, start, end):
        self.assertEquals(resp.status_code, 206)
        self.assertEquals(resp._headers['content-range'][1], "items %d-%d/3" % (start, end))

    ##### Header Tests #####
    def test_nonitems_range(self):
        resp = self.client.get('/api/list_fields', {}, HTTP_RANGE='bytes=0-1023')
        self.assertTrue(resp.status_code != 400)

    def test_malformed_items_range(self):
        resp = self.client.get('/api/list_fields', {}, HTTP_RANGE='items=a-b')
        self.assertEquals(resp.status_code, 400)
        
    def test_unsatisfiable_range_start_gt_end(self):
        resp = self.client.get('/api/list_fields', {}, HTTP_RANGE='items=1-0')
        self.assertEquals(resp.status_code, 416)
        
    def test_unsatisfiable_range_start_gt_last(self):
        resp = self.client.get('/api/list_fields', {}, HTTP_RANGE='items=3-3')
        self.assertEquals(resp.status_code, 416)

    def test_0_0(self):
        expect = '''[
    {
        "id": 1, 
        "variety": "apple"
    }
]'''
        resp = self.client.get('/api/list_fields', {}, HTTP_RANGE='items=0-0')
        self.assertRange(resp, 0, 0)
        self.assertEquals(resp.content, expect)

    def test_0_1(self):
        expect = '''[
    {
        "id": 1, 
        "variety": "apple"
    }, 
    {
        "id": 2, 
        "variety": "carrot"
    }
]'''
        resp = self.client.get('/api/list_fields', {}, HTTP_RANGE='items=0-1')
        self.assertRange(resp, 0, 1)
        self.assertEquals(resp.content, expect)

    def test_1_2(self):
        expect = '''[
    {
        "id": 2, 
        "variety": "carrot"
    }, 
    {
        "id": 3, 
        "variety": "dog"
    }
]'''
        resp = self.client.get('/api/list_fields', {}, HTTP_RANGE='items=1-2')
        self.assertRange(resp, 1, 2)
        self.assertEquals(resp.content, expect)

    def test_1_none(self):
        expect = '''[
    {
        "id": 2, 
        "variety": "carrot"
    }, 
    {
        "id": 3, 
        "variety": "dog"
    }
]'''
        resp = self.client.get('/api/list_fields', {}, HTTP_RANGE='items=1-')
        self.assertRange(resp, 1, 2)
        self.assertEquals(resp.content, expect)


    def test_none_1(self):
        expect = '''[
    {
        "id": 3, 
        "variety": "dog"
    }
]'''
        resp = self.client.get('/api/list_fields', {}, HTTP_RANGE='items=-1')
        self.assertRange(resp, 2, 2)
        self.assertEquals(resp.content, expect)

    def test_none_2(self):
        expect = '''[
    {
        "id": 2, 
        "variety": "carrot"
    }, 
    {
        "id": 3, 
        "variety": "dog"
    }
]'''
        resp = self.client.get('/api/list_fields', {}, HTTP_RANGE='items=-2')
        self.assertRange(resp, 1, 2)
        self.assertEquals(resp.content, expect)

    def test_none_end_gt_last(self):
        expect = '''[
    {
        "id": 1, 
        "variety": "apple"
    }, 
    {
        "id": 2, 
        "variety": "carrot"
    }, 
    {
        "id": 3, 
        "variety": "dog"
    }
]'''
        resp = self.client.get('/api/list_fields', {}, HTTP_RANGE='items=-10000')
        self.assertRange(resp, 0, 2)
        self.assertEquals(resp.content, expect)

    ##### Parameter Tests #####
    def test_unsatisfiable_range_offset_gt_last(self):
        resp = self.client.get('/api/list_fields?offset=10000&limit=1')
        self.assertEquals(resp.status_code, 416)
        
    def test_p_0_1(self):
        expect = '''[
    {
        "id": 1, 
        "variety": "apple"
    }
]'''
        resp = self.client.get('/api/list_fields?offset=0&limit=1')
        self.assertRange(resp, 0, 0)
        self.assertEquals(resp.content, expect)

    def test_p_0_2(self):
        expect = '''[
    {
        "id": 1, 
        "variety": "apple"
    }, 
    {
        "id": 2, 
        "variety": "carrot"
    }
]'''
        resp = self.client.get('/api/list_fields?offset=0&limit=2')
        self.assertRange(resp, 0, 1)
        self.assertEquals(resp.content, expect)

    def test_p_1_2(self):
        expect = '''[
    {
        "id": 2, 
        "variety": "carrot"
    }, 
    {
        "id": 3, 
        "variety": "dog"
    }
]'''
        resp = self.client.get('/api/list_fields?offset=1&limit=2')
        self.assertRange(resp, 1, 2)
        self.assertEquals(resp.content, expect)

    def test_p_1_none(self):
        expect = '''[
    {
        "id": 2, 
        "variety": "carrot"
    }, 
    {
        "id": 3, 
        "variety": "dog"
    }
]'''
        resp = self.client.get('/api/list_fields?offset=1&limit=')
        self.assertRange(resp, 1, 2)
        self.assertEquals(resp.content, expect)


    def test_p_none_1(self):
        expect = '''[
    {
        "id": 3, 
        "variety": "dog"
    }
]'''
        resp = self.client.get('/api/list_fields?offset=&limit=1')
        self.assertRange(resp, 2, 2)
        self.assertEquals(resp.content, expect)

    def test_p_none_2(self):
        expect = '''[
    {
        "id": 2, 
        "variety": "carrot"
    }, 
    {
        "id": 3, 
        "variety": "dog"
    }
]'''
        resp = self.client.get('/api/list_fields?offset=&limit=2')
        self.assertRange(resp, 1, 2)
        self.assertEquals(resp.content, expect)

    def test_none_limit_gt_last(self):
        expect = '''[
    {
        "id": 1, 
        "variety": "apple"
    }, 
    {
        "id": 2, 
        "variety": "carrot"
    }, 
    {
        "id": 3, 
        "variety": "dog"
    }
]'''
        resp = self.client.get('/api/list_fields?offset=&limit=10000')
        self.assertRange(resp, 0, 2)
        self.assertEquals(resp.content, expect)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from piston.resource import Resource
from piston.authentication import HttpBasicAuthentication, HttpBasicSimple

from test_project.apps.testapp.handlers import EntryHandler, ExpressiveHandler, AbstractHandler, EchoHandler, PlainOldObjectHandler, Issue58Handler, ListFieldsHandler

auth = HttpBasicAuthentication(realm='TestApplication')

entries = Resource(handler=EntryHandler, authentication=auth)
expressive = Resource(handler=ExpressiveHandler, authentication=auth)
abstract = Resource(handler=AbstractHandler, authentication=auth)
echo = Resource(handler=EchoHandler)
popo = Resource(handler=PlainOldObjectHandler)
list_fields = Resource(handler=ListFieldsHandler)
issue58 = Resource(handler=Issue58Handler)

AUTHENTICATORS = [auth,]
SIMPLE_USERS = (('admin', 'secr3t'),
                ('admin', 'user'),
                ('admin', 'allwork'),
                ('admin', 'thisisneat'))

for username, password in SIMPLE_USERS:
    AUTHENTICATORS.append(HttpBasicSimple(realm='Test', 
                            username=username, password=password))

multiauth = Resource(handler=PlainOldObjectHandler, 
                        authentication=AUTHENTICATORS)

urlpatterns = patterns('',
    url(r'^entries/$', entries),
    url(r'^entries/(?P<pk>.+)/$', entries),
    url(r'^entries\.(?P<emitter_format>.+)', entries),
    url(r'^entry-(?P<pk>.+)\.(?P<emitter_format>.+)', entries),

    url(r'^issue58\.(?P<emitter_format>.+)$', issue58),

    url(r'^expressive\.(?P<emitter_format>.+)$', expressive),

    url(r'^abstract\.(?P<emitter_format>.+)$', abstract),
    url(r'^abstract/(?P<id_>\d+)\.(?P<emitter_format>.+)$', abstract),

    url(r'^echo$', echo),

    url(r'^multiauth/$', multiauth),

    # oauth entrypoints
    url(r'^oauth/request_token$', 'piston.authentication.oauth_request_token'),
    url(r'^oauth/authorize$', 'piston.authentication.oauth_user_auth'),
    url(r'^oauth/access_token$', 'piston.authentication.oauth_access_token'),

    url(r'^list_fields$', list_fields),
    url(r'^list_fields/(?P<id>.+)$', list_fields),
    
    url(r'^popo$', popo),
)



########NEW FILE########
__FILENAME__ = settings
import os
DEBUG = True
DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = '/tmp/piston.db'
INSTALLED_APPS = (
    'django.contrib.auth', 
    'django.contrib.contenttypes', 
    'django.contrib.sessions', 
    'django.contrib.sites',
    'piston',
    'test_project.apps.testapp',
)
TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), 'templates'),
)

SITE_ID = 1
ROOT_URLCONF = 'test_project.urls'

MIDDLEWARE_CLASSES = (
    'piston.middleware.ConditionalMiddlewareCompatProxy',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'piston.middleware.CommonMiddlewareCompatProxy',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *


urlpatterns = patterns('',
    url(r'api/', include('test_project.apps.testapp.urls'))
)

########NEW FILE########
