__FILENAME__ = djangofb
#!/usr/bin/env python

if __name__ == '__main__':
    import sys, os, re

    def usage():
        sys.stderr.write('Usage: djangofb.py startapp <appname>\n')
        sys.exit(1)

    if len(sys.argv) not in (2, 3):
        usage()

    if sys.argv[1] != 'startapp':
        usage()

    app_name = len(sys.argv) == 3 and sys.argv[2] or 'fbapp'

    try:
        sys.path.insert(0, os.getcwd())
        import settings # Assumed to be in the same directory or current directory.
    except ImportError:
        sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r or in the current directory. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
        sys.exit(1)

    from django.core import management

    directory = management.setup_environ(settings)

    if hasattr(management, 'color'):
        # Current svn version of django
        from django.core.management.color import color_style
        style = color_style()
    else:
        # Compatibility with 0.96
        from django.core.management import style

    project_dir = os.path.normpath(os.path.join(directory, '..'))
    parent_dir = os.path.basename(project_dir)
    project_name = os.path.basename(directory)
    if app_name == project_name:
        sys.stderr.write(style.ERROR('Error: You cannot create an app with the same name (%r) as your project.\n' % app_name))
        sys.exit(1)
    if app_name == 'facebook':
        sys.stderr.write(style.ERROR('Error: You cannot name your app "facebook", since this can cause conflicts with imports in Python < 2.5.\n'))
        sys.exit(1)
    if not re.search(r'^\w+$', app_name):
        sys.stderr.write(style.ERROR('Error: %r is not a valid app name. Please use only numbers, letters and underscores.\n' % (app_name)))
        sys.exit(1)

    top_dir = os.path.join(directory, app_name)
    try:
        os.mkdir(top_dir)
    except OSError, e:
        sys.stderr.write(style.ERROR("Error: %s\n" % e))
        sys.exit(1)

    import facebook

    template_dir = os.path.join(facebook.__path__[0], 'djangofb', 'default_app')

    sys.stderr.write('Creating Facebook application %r...\n' % app_name)
    
    for d, subdirs, files in os.walk(template_dir):
        relative_dir = d[len(template_dir) + 1:]
        if relative_dir:
            os.mkdir(os.path.join(top_dir, relative_dir))
        subdirs[:] = [s for s in subdirs if not s.startswith('.')]
        for f in files:
            if f.endswith('.pyc'):
                continue
            path_old = os.path.join(d, f)
            path_new = os.path.join(top_dir, relative_dir, f)
            f_old = open(path_old, 'r')
            f_new = open(path_new, 'w')
            sys.stderr.write('Writing %s...\n' % path_new)
            f_new.write(f_old.read().replace('{{ project }}', project_name).replace('{{ app }}', app_name))
            f_new.close()
            f_old.close()

    sys.stderr.write('Done!\n\n')
    
    from django.conf import settings
    
    need_api_key = not hasattr(settings, 'FACEBOOK_API_KEY')
    need_middleware = not 'facebook.djangofb.FacebookMiddleware' in settings.MIDDLEWARE_CLASSES
    need_loader = not 'django.template.loaders.app_directories.load_template_source' in settings.TEMPLATE_LOADERS
    need_install_app = not '%s.%s' % (project_name, app_name) in settings.INSTALLED_APPS

    if need_api_key or need_middleware or need_loader or need_install_app:
        sys.stderr.write("""There are a couple of things you NEED to do before you can use this app:\n\n""")
        if need_api_key:
            sys.stderr.write(""" * Set FACEBOOK_API_KEY and FACEBOOK_SECRET_KEY to the appropriate values in settings.py\n\n""")
        if need_middleware:
            sys.stderr.write(""" * Add 'facebook.djangofb.FacebookMiddleware' to your MIDDLEWARE_CLASSES in settings.py\n\n""")
        if need_loader:
            sys.stderr.write(""" * Add 'django.template.loaders.app_directories.load_template_source' to your TEMPLATE_LOADERS in settings.py\n\n""")
        if need_install_app:
            sys.stderr.write(""" * Add '%s.%s' to your INSTALLED_APPS in settings.py\n\n""" % (project_name, app_name))

    sys.stderr.write("""The final step is to add (r'^%s/', include('%s.%s.urls')) to your urls.py, and then set your callback page in the application settings on Facebook to 'http://your.domain.com/%s/'.

Good luck!

""" % (project_name, project_name, app_name, project_name))

########NEW FILE########
__FILENAME__ = models
from django.db import models

# get_facebook_client lets us get the current Facebook object
# from outside of a view, which lets us have cleaner code
from facebook.djangofb import get_facebook_client


def _2int(d, k):
    try:
        d = d.__dict__
    except:
        pass
    
    t = d.get(k, '')
    if t == 'None':
        t = 0
    else:
        t = int(t)
    return t

class UserManager(models.Manager):
    """Custom manager for a Facebook User."""
    
    def get_current(self):
        """Gets a User object for the logged-in Facebook user."""
        facebook = get_facebook_client()
        user, created = self.get_or_create(id=_2int(facebook, 'uid'))
        if created:
            # we could do some custom actions for new users here...
            pass
        return user

class User(models.Model):
    """A simple User model for Facebook users."""

    # We use the user's UID as the primary key in our database.
    id = models.IntegerField(primary_key=True)

    # TODO: The data that you want to store for each user would go here.
    # For this sample, we let users let people know their favorite progamming
    # language, in the spirit of Extended Info.
    language = models.CharField(max_length=64, default='Python')

    # Add the custom manager
    objects = UserManager()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('fbsample.fbapp.views',
    (r'^$', 'canvas'),
    # Define other pages you want to create here
)


########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse
from django.views.generic.simple import direct_to_template
#uncomment the following two lines and the one below
#if you dont want to use a decorator instead of the middleware
#from django.utils.decorators import decorator_from_middleware
#from facebook.djangofb import FacebookMiddleware

# Import the Django helpers
import facebook.djangofb as facebook

# The User model defined in models.py
from models import User

# We'll require login for our canvas page. This
# isn't necessarily a good idea, as we might want
# to let users see the page without granting our app
# access to their info. See the wiki for details on how
# to do this.
#@decorator_from_middleware(FacebookMiddleware)
@facebook.require_login()
def canvas(request):
    # Get the User object for the currently logged in user
    user = User.objects.get_current()

    # Check if we were POSTed the user's new language of choice
    if 'language' in request.POST:
        user.language = request.POST['language'][:64]
        user.save()

    # User is guaranteed to be logged in, so pass canvas.fbml
    # an extra 'fbuser' parameter that is the User object for
    # the currently logged in user.
    return direct_to_template(request, 'canvas.fbml', extra_context={'fbuser': user})

@facebook.require_login()
def ajax(request):
    return HttpResponse('hello world')

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
# Django settings for fbsample project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'db.sqlite3'             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

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
SECRET_KEY = 'yg6zh@+u^w3agtjwy^da)#277d3j#a%3m@)pev8_j0ozztwe4+'

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
    
    'facebook.djangofb.FacebookMiddleware',
)

ROOT_URLCONF = 'fbsample.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    
    'fbsample.fbapp',
)

# get it from here 
# http://www.facebook.com/editapps.php?ref=mb
FACEBOOK_API_KEY = 'x'
FACEBOOK_SECRET_KEY = 'xx'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^fbsample/', include('fbsample.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
    
        (r'^fbsample/', include('fbsample.fbapp.urls')),
)

########NEW FILE########
__FILENAME__ = context_processors
def messages(request):
    """Returns messages similar to ``django.core.context_processors.auth``."""
    if hasattr(request, 'facebook') and request.facebook.uid is not None:
        from models import Message
        messages = Message.objects.get_and_delete_all(uid=request.facebook.uid)
    return {'messages': messages}
########NEW FILE########
__FILENAME__ = models
from django.db import models

# get_facebook_client lets us get the current Facebook object
# from outside of a view, which lets us have cleaner code
from facebook.djangofb import get_facebook_client


def _2int(d, k):
    try:
        d = d.__dict__
    except:
        pass
    
    t = d.get(k, '')
    if t == 'None':
        t = 0
    else:
        t = int(t)
    return t

class UserManager(models.Manager):
    """Custom manager for a Facebook User."""
    
    def get_current(self):
        """Gets a User object for the logged-in Facebook user."""
        facebook = get_facebook_client()
        user, created = self.get_or_create(id=_2int(facebook, 'uid'))
        if created:
            # we could do some custom actions for new users here...
            pass
        return user

class User(models.Model):
    """A simple User model for Facebook users."""

    # We use the user's UID as the primary key in our database.
    id = models.IntegerField(primary_key=True)

    # TODO: The data that you want to store for each user would go here.
    # For this sample, we let users let people know their favorite progamming
    # language, in the spirit of Extended Info.
    language = models.CharField(max_length=64, default='Python')

    # Add the custom manager
    objects = UserManager()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('{{ project }}.{{ app }}.views',
    (r'^$', 'canvas'),
    # Define other pages you want to create here
)


########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse
from django.views.generic.simple import direct_to_template
#uncomment the following two lines and the one below
#if you dont want to use a decorator instead of the middleware
#from django.utils.decorators import decorator_from_middleware
#from facebook.djangofb import FacebookMiddleware

# Import the Django helpers
import facebook.djangofb as facebook

# The User model defined in models.py
from models import User

# We'll require login for our canvas page. This
# isn't necessarily a good idea, as we might want
# to let users see the page without granting our app
# access to their info. See the wiki for details on how
# to do this.
#@decorator_from_middleware(FacebookMiddleware)
@facebook.require_login()
def canvas(request):
    # Get the User object for the currently logged in user
    user = User.objects.get_current()

    # Check if we were POSTed the user's new language of choice
    if 'language' in request.POST:
        user.language = request.POST['language'][:64]
        user.save()

    # User is guaranteed to be logged in, so pass canvas.fbml
    # an extra 'fbuser' parameter that is the User object for
    # the currently logged in user.
    return direct_to_template(request, 'canvas.fbml', extra_context={'fbuser': user})

@facebook.require_login()
def ajax(request):
    return HttpResponse('hello world')

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.html import escape
from django.utils.safestring import mark_safe

FB_MESSAGE_STATUS = (
    (0, 'Explanation'),
    (1, 'Error'),
    (2, 'Success'),
)

class MessageManager(models.Manager):
    def get_and_delete_all(self, uid):
        messages = []
        for m in self.filter(uid=uid):
            messages.append(m)
            m.delete()
        return messages

class Message(models.Model):
    """Represents a message for a Facebook user."""
    uid = models.CharField(max_length=25)
    status = models.IntegerField(choices=FB_MESSAGE_STATUS)
    message = models.CharField(max_length=300)
    objects = MessageManager()

    def __unicode__(self):
        return self.message

    def _fb_tag(self):
        return self.get_status_display().lower()

    def as_fbml(self):
        return mark_safe(u'<fb:%s message="%s" />' % (
            self._fb_tag(),
            escape(self.message),
        ))

########NEW FILE########
__FILENAME__ = webappfb
#
# webappfb - Facebook tools for Google's AppEngine "webapp" Framework
#
# Copyright (c) 2009, Max Battcher
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the author nor the names of its contributors may
#       be used to endorse or promote products derived from this software
#       without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
from google.appengine.api import memcache
from google.appengine.ext.webapp import RequestHandler
from facebook import Facebook
import yaml

"""
Facebook tools for Google AppEngine's object-oriented "webapp" framework.
"""

# This global configuration dictionary is for configuration variables
# for Facebook requests such as the application's API key and secret
# key. Defaults to loading a 'facebook.yaml' YAML file. This should be
# useful and familiar for most AppEngine development.
FACEBOOK_CONFIG = yaml.load(file('facebook.yaml', 'r'))

class FacebookRequestHandler(RequestHandler):
    """
    Base class for request handlers for Facebook apps, providing useful
    Facebook-related tools: a local 
    """

    def _fbconfig_value(self, name, default=None):
        """
        Checks the global config dictionary and then for a class/instance
        variable, using a provided default if no value is found.
        """
        if name in FACEBOOK_CONFIG:
            default = FACEBOOK_CONFIG[name]
            
        return getattr(self, name, default)

    def initialize(self, request, response):
        """
        Initialize's this request's Facebook client.
        """
        super(FacebookRequestHandler, self).initialize(request, response)

        app_name = self._fbconfig_value('app_name', '')
        api_key = self._fbconfig_value('api_key', None)
        secret_key = self._fbconfig_value('secret_key', None)

        self.facebook = Facebook(api_key, secret_key,
            app_name=app_name)

        require_app = self._fbconfig_value('require_app', False)
        require_login = self._fbconfig_value('require_login', False)
        need_session = self._fbconfig_value('need_session', False)
        check_session = self._fbconfig_value('check_session', True)

        self._messages = None
        self.redirecting = False

        if require_app or require_login:
            if not self.facebook.check_session(request):
                self.redirect(self.facebook.get_login_url(next=request.url))
                self.redirecting = True
                return
        elif check_session:
            self.facebook.check_session(request) # ignore response

        # NOTE: require_app is deprecated according to modern Facebook login
        #       policies. Included for completeness, but unnecessary.
        if require_app and not self.facebook.added:
            self.redirect(self.facebook.get_add_url(next=request.url))
            self.redirecting = True
            return

        if not (require_app or require_login) and need_session:
            self.facebook.auth.getSession()

    def redirect(self, url, **kwargs):
        """
        For Facebook canvas pages we should use <fb:redirect /> instead of
        a normal redirect.
        """
        if self.facebook.in_canvas:
            self.response.clear()
            self.response.out.write('<fb:redirect url="%s" />' % (url, ))
        else:
            super(FacebookRequestHandler, self).redirect(url, **kwargs)

    def add_user_message(self, kind, msg, detail='', time=15 * 60):
        """
        Add a message to the current user to memcache.
        """
        if self.facebook.uid:
            key = 'messages:%s' % self.facebook.uid
            self._messages = memcache.get(key)
            message = {
                'kind': kind,
                'message': msg,
                'detail': detail,
            }
            if self._messages is not None:
                self._messages.append(message)
            else:
                self._messages = [message]
            memcache.set(key, self._messages, time=time)

    def get_and_delete_user_messages(self):
        """
        Get all of the messages for the current user; removing them.
        """
        if self.facebook.uid:
            key = 'messages:%s' % self.facebook.uid
            if not hasattr(self, '_messages') or self._messages is None:
                self._messages = memcache.get(key)
            memcache.delete(key)
            return self._messages
        return None

class FacebookCanvasHandler(FacebookRequestHandler):
    """
    Request handler for Facebook canvas (FBML application) requests.
    """

    def canvas(self, *args, **kwargs):
        """
        This will be your handler to deal with Canvas requests.
        """
        raise NotImplementedError()

    def get(self, *args):
        """
        All valid canvas views are POSTS.
        """
        # TODO: Attempt to auto-redirect to Facebook canvas?
        self.error(404)

    def post(self, *args, **kwargs):
        """
        Check a couple of simple safety checks and then call the canvas
        handler.
        """
        if self.redirecting: return

        if not self.facebook.in_canvas:
            self.error(404)
            return

        self.canvas(*args, **kwargs)

# vim: ai et ts=4 sts=4 sw=4

########NEW FILE########
__FILENAME__ = wsgi
"""This is some simple helper code to bridge the Pylons / PyFacebook gap.

There's some generic WSGI middleware, some Paste stuff, and some Pylons
stuff.  Once you put FacebookWSGIMiddleware into your middleware stack,
you'll have access to ``environ["pyfacebook.facebook"]``, which is a
``facebook.Facebook`` object.  If you're using Paste (which includes
Pylons users), you can also access this directly using the facebook
global in this module.

"""

# Be careful what you import.  Don't expect everyone to have Pylons,
# Paste, etc. installed.  Degrade gracefully.

from facebook import Facebook

__docformat__ = "restructuredtext"


# Setup Paste, if available.  This needs to stay in the same module as
# FacebookWSGIMiddleware below.

try:
    from paste.registry import StackedObjectProxy
    from webob.exc import _HTTPMove
    try:
        from string import Template
    except ImportError:
        from webob.util.stringtemplate import Template
    from webob import html_escape

except ImportError:
    pass
else:
    facebook = StackedObjectProxy(name="PyFacebook Facebook Connection")

    class CanvasRedirect(_HTTPMove):
        """This is for canvas redirects."""

        title = "See Other"
        code = 200
        html_template_obj = Template('<fb:redirect url="${location}" />')

        def html_body(self, environ):
            return self.html_template_obj.substitute(location=self.detail)


class FacebookWSGIMiddleware(object):

    """This is WSGI middleware for Facebook."""

    def __init__(self, app, config, facebook_class=Facebook):
        """Initialize the Facebook middleware.

        ``app``
            This is the WSGI application being wrapped.

        ``config``
            This is a dict containing the keys "pyfacebook.apikey" and
            "pyfacebook.secret".

        ``facebook_class``
            If you want to subclass the Facebook class, you can pass in
            your replacement here.  Pylons users will want to use
            PylonsFacebook.

        """
        self.app = app
        self.config = config
        self.facebook_class = facebook_class

    def __call__(self, environ, start_response):
        config = self.config
        real_facebook = self.facebook_class(config["pyfacebook.apikey"],
                                            config["pyfacebook.secret"])
        registry = environ.get('paste.registry')
        if registry:
            registry.register(facebook, real_facebook)
        environ['pyfacebook.facebook'] = real_facebook
        return self.app(environ, start_response)


# The remainder is Pylons specific.

try:
    import pylons
    from pylons.controllers.util import redirect_to as pylons_redirect_to
    from routes import url_for
except ImportError:
    pass
else:


    class PylonsFacebook(Facebook):

        """Subclass Facebook to add Pylons goodies."""

        def check_session(self, request=None):
            """The request parameter is now optional."""
            if request is None:
                request = pylons.request
            return Facebook.check_session(self, request)

        # The Django request object is similar enough to the Paste
        # request object that check_session and validate_signature
        # should *just work*.

        def redirect_to(self, url):
            """Wrap Pylons' redirect_to function so that it works in_canvas.

            By the way, this won't work until after you call
            check_session().

            """
            if self.in_canvas:
                raise CanvasRedirect(url)
            pylons_redirect_to(url)

        def apps_url_for(self, *args, **kargs):
            """Like url_for, but starts with "http://apps.facebook.com"."""
            return "http://apps.facebook.com" + url_for(*args, **kargs)


    def create_pylons_facebook_middleware(app, config):
        """This is a simple wrapper for FacebookWSGIMiddleware.

        It passes the correct facebook_class.

        """
        return FacebookWSGIMiddleware(app, config,
                                      facebook_class=PylonsFacebook)

########NEW FILE########
__FILENAME__ = test
import unittest
import sys
import os
import facebook
import urllib2
try:
    from hashlib import md5
    md5_constructor = md5
except ImportError:
    import md5
    md5_constructor = md5.new
try:
    import simplejson
except ImportError:
    from django.utils import simplejson
import httplib
from minimock import Mock

my_api_key = "e1e9cfeb5e0d7a52e4fbd5d09e1b873e"
my_secret_key = "1bebae7283f5b79aaf9b851addd55b90"
#'{"error_code":100,\
                 #"error_msg":"Invalid parameter",\
                 #"request_args":[{"key":"format","value":"JSON"},\
                                 #{"key":"auth_token","value":"24626e24bb12919f2f142145070542e8"},\
                                 #{"key":"sig","value":"36af2af3b93da784149301e77cb1621a"},\
                                 #{"key":"v","value":"1.0"},\
                                 #{"key":"api_key","value":"e1e9cfeb5e0d7a52e4fbd5d09e1b873e"},\
                                 #{"key":"method","value":"facebook.auth.getSession"}]}'
response_str = '{"stuff":"abcd"}'
class MyUrlOpen:
    def __init__(self,*args,**kwargs):
        pass
    
    def read(self):
        global response_str
        return response_str
    
class pyfacebook_UnitTests(unittest.TestCase):
    def setUp(self):
        facebook.urllib2.urlopen = Mock('urllib2.urlopen')
        facebook.urllib2.urlopen.mock_returns_func = MyUrlOpen
        pass

    def tearDown(self):
        pass
    
    def login(self):
        pass
                
    def test1(self):
        f = facebook.Facebook(api_key=my_api_key, secret_key=my_secret_key)
        f.login = self.login
        self.assertEquals(f.api_key,my_api_key)
        self.assertEquals(f.secret_key,my_secret_key)
        self.assertEquals(f.auth_token,None)
        self.assertEquals(f.app_name,None)
        self.assertEquals(f.callback_path,None)
        self.assertEquals(f.internal,None)
        
    def test2(self):
        args = {"arg1":"a","arg2":"b","arg3":"c"}
        hasher = md5_constructor(''.join(['%s=%s' % (x, args[x]) for x in sorted(args.keys())]))
        hasher.update("acdnj")
        f = facebook.Facebook(api_key="abcdf", secret_key="acdnj")
        f.login = self.login
        digest = f._hash_args(args)
        self.assertEquals(hasher.hexdigest(),digest)
        hasher = md5_constructor(''.join(['%s=%s' % (x, args[x]) for x in sorted(args.keys())]))
        hasher.update("klmn")
        # trunk code has error hash.updated instead of hash.update
        digest = f._hash_args(args,secret="klmn")
        self.assertEquals(hasher.hexdigest(),digest)
        
        hasher = md5_constructor(''.join(['%s=%s' % (x, args[x]) for x in sorted(args.keys())]))
        f.secret = "klmn"
        hasher.update(f.secret)
        # trunk code has error hash.updated instead of hash.update
        digest = f._hash_args(args)
        self.assertEquals(hasher.hexdigest(),digest)
        
    def test3(self):
        global response_str
        response = {'stuff':'abcd'}
        response_str = simplejson.dumps(response)
        fb = facebook.Facebook(my_api_key, my_secret_key)
        fb.login = self.login
        fb.auth.createToken()
        self.assertEquals(str(fb.auth_token['stuff']),"abcd")
        fb.login()
        response = {"session_key":"key","uid":"my_uid","secret":"my_secret","expires":"my_expires"}
        response_str = simplejson.dumps(response)
        res = fb.auth.getSession()
        self.assertEquals(str(res["expires"]),response["expires"])
        self.assertEquals(str(res["secret"]),response["secret"])
        self.assertEquals(str(res["session_key"]),response["session_key"])
        self.assertEquals(str(res["uid"]),response["uid"])
        
    def test4(self):
        global response_str
        response = 'abcdef'
        response_str = simplejson.dumps(response)
        fb = facebook.Facebook(my_api_key, my_secret_key)
        fb.login = self.login
        fb.auth.createToken()
        self.assertEquals(str(fb.auth_token),"abcdef")
        url = fb.get_login_url(next="nowhere", popup=True, canvas=True)
        self.assertEquals(url,
                          'http://www.facebook.com/login.php?canvas=1&popup=1&auth_token=abcdef&next=nowhere&v=1.0&api_key=%s'%(my_api_key,))
        
    def test5(self):
        class Request:
            def __init__(self,post,get,method):
                self.POST = post
                self.GET = get
                self.method = method
                
        req = Request({'fb_sig_in_canvas':1},{},'POST')
        fb = facebook.Facebook(my_api_key, my_secret_key)
        fb.login = self.login
        res = fb.check_session(req)
        self.assertFalse(res)
        req = Request({'fb_sig':1},{},'POST')
        res = fb.check_session(req)
        self.assertFalse(res)
        req = Request({'fb_sig':fb._hash_args({'in_canvas':'1',
                                               'added':'1',
                                               'expires':'1',
                                               'friends':'joe,mary',
                                               'session_key':'abc',
                                               'user':'bob'}),
                                               'fb_sig_in_canvas':'1',
                                               'fb_sig_added':'1',
                                               'fb_sig_expires':'1',
                                               'fb_sig_friends':'joe,mary',
                                               'fb_sig_session_key':'abc',
                                               'fb_sig_user':'bob'},
                                               {},'POST')
        res = fb.check_session(req)
        self.assertTrue(res)
        fb = facebook.Facebook(my_api_key, my_secret_key)
        fb.login = self.login
        req = Request({'fb_sig':fb._hash_args({'in_canvas':'1',
                                               'added':'1',
                                               'expires':'1',
                                               'friends':'',
                                               'session_key':'abc',
                                               'user':'bob'}),
                                               'fb_sig_in_canvas':'1',
                                               'fb_sig_added':'1',
                                               'fb_sig_expires':'1',
                                               'fb_sig_friends':'',
                                               'fb_sig_session_key':'abc',
                                               'fb_sig_user':'bob'},
                                               {},'POST')
        res = fb.check_session(req)
        self.assertTrue(res)
        fb = facebook.Facebook(my_api_key, my_secret_key)
        fb.login = self.login
        req = Request({'fb_sig':fb._hash_args({'in_canvas':'1',
                                               'added':'1',
                                               'expires':'1',
                                               'friends':'',
                                               'session_key':'abc',
                                               'page_id':'id'}),
                                               'fb_sig_in_canvas':'1',
                                               'fb_sig_added':'1',
                                               'fb_sig_expires':'1',
                                               'fb_sig_friends':'',
                                               'fb_sig_session_key':'abc',
                                               'fb_sig_page_id':'id'},
                                               {},'POST')
        res = fb.check_session(req)
        self.assertTrue(res)
        
    def test6(self):
        global response_str
        response = 'abcdef'
        response_str = simplejson.dumps(response)
        fb = facebook.Facebook(my_api_key, my_secret_key)
        fb.login = self.login
        fb.auth.createToken()
#        self.failUnlessRaises(RuntimeError,fb._add_session_args)
        response = {"session_key":"key","uid":"my_uid","secret":"my_secret","expires":"my_expires"}
        response_str = simplejson.dumps(response)
        fb.auth.getSession()
        args = fb._add_session_args()
        
    def test7(self):
        global response_str
        response = 'abcdef'
        response_str = simplejson.dumps(response)
        fb = facebook.Facebook(my_api_key, my_secret_key)
        fb.login = self.login
        fb.auth.createToken()
        self.assertEquals(str(fb.auth_token),"abcdef")
        url = fb.get_authorize_url(next="next",next_cancel="next_cancel")
        self.assertEquals(url,
                          'http://www.facebook.com/authorize.php?api_key=%s&next_cancel=next_cancel&v=1.0&next=next' % (my_api_key,))
        
    def test8(self):
        class Request:
            def __init__(self,post,get,method):
                self.POST = post
                self.GET = get
                self.method = method
                
        global response_str
        response = {"session_key":"abcdef","uid":"my_uid","secret":"my_secret","expires":"my_expires"}
        response_str = simplejson.dumps(response)
        req = Request({},{'installed':1,'fb_page_id':'id','auth_token':'abcdef'},'GET')
        fb = facebook.Facebook(my_api_key, my_secret_key)
        fb.login = self.login
        res = fb.check_session(req)
        self.assertTrue(res)

    def test9(self):
        global response_str
        response = 'abcdef'
        response_str = simplejson.dumps(response)
        fb = facebook.Facebook(my_api_key, my_secret_key)
        fb.login = self.login
        fb.auth.createToken()
        self.assertEquals(str(fb.auth_token),"abcdef")
        url = fb.get_add_url(next="next")
        self.assertEquals(url,
                          'http://www.facebook.com/install.php?api_key=%s&v=1.0&next=next' % (my_api_key,))

    def send(self,xml):
        self.xml = xml

    def test10(self):
        import Image
        image1 = Image.new("RGB", (400, 300), (255, 255, 255))
        filename = "image_file.jpg"
        image1.save(filename)
        global response_str
        fb = facebook.Facebook(my_api_key, my_secret_key)
        fb.login = self.login
        
        facebook.httplib.HTTP = Mock('httplib.HTTP')
        http_connection = Mock('http_connection')
        facebook.httplib.HTTP.mock_returns = http_connection
        http_connection.send.mock_returns_func = self.send
        def _http_passes():
            return [200,]
        http_connection.getreply.mock_returns_func = _http_passes

        def read():
            response = {"stuff":"stuff"}
            response_str = simplejson.dumps(response)
            return response_str
        http_connection.file.read.mock_returns_func = read
        
        response = {"session_key":"key","uid":"my_uid","secret":"my_secret","expires":"my_expires"}
        response_str = simplejson.dumps(response)
        res = fb.auth.getSession()
        result = fb.photos.upload(image=filename,aid="aid",caption="a caption")
        self.assertEquals(str(result["stuff"]),"stuff")
        os.remove(filename)
        
if __name__ == "__main__":

    # Build the test suite
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(pyfacebook_UnitTests))

    # Execute the test suite
    print("Testing Proxy class\n")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(len(result.errors) + len(result.failures))


########NEW FILE########
