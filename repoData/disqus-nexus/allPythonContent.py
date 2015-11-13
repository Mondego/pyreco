__FILENAME__ = models

########NEW FILE########
__FILENAME__ = nexus_modules
import nexus

class HelloWorldModule(nexus.NexusModule):
    home_url = 'index'
    name = 'hello-world'

    def get_title(self):
        return 'Hello World'

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url

        urlpatterns = patterns('',
            url(r'^$', self.as_view(self.index), name='index'),
        )

        return urlpatterns

    def render_on_dashboard(self, request):
        return self.render_to_string('nexus/example/dashboard.html', {
            'title': 'Hello World',
        })

    def index(self, request):
        return self.render_to_response("nexus/example/index.html", {
            'title': 'Hello World',
        }, request)
nexus.site.register(HelloWorldModule, 'hello-world')
# optionally you may specify a category
# nexus.site.register(HelloWorldModule, 'hello-world', category='cache')
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
import os.path
import sys
# Django settings for example_project project.

DEBUG = True
TEMPLATE_DEBUG = True

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

INTERNAL_IPS = ('127.0.0.1',)

MANAGERS = ADMINS

PROJECT_ROOT = os.path.dirname(__file__)

NEXUS_MEDIA_PREFIX = '/media/'

sys.path.insert(0, os.path.abspath(os.path.join(PROJECT_ROOT, '..')))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'nexus',                      # Or path to database file if using sqlite3.
        'USER': 'postgres',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Los_Angeles'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

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
ADMIN_MEDIA_PREFIX = '/admin/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = ')*)&8a36)6%74e@-ne5(-!8a(vv#tkv)(eyg&@0=zd^pl!7=y@'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'example_project.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'nexus',
    'south',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
)

SENTRY_THRASHING_TIMEOUT = 0
SENTRY_TESTING = True
SENTRY_SITE = 'example'
SENTRY_PUBLIC = False

# just to test
HAYSTACK_SEARCH_ENGINE = 'whoosh'

SENTRY_SEARCH_ENGINE = 'whoosh'
SENTRY_SEARCH_OPTIONS = {
    'path': os.path.join(PROJECT_ROOT, 'sentry_index'),
}

# TODO: fix gargoyle
for mod in ('paging', 'indexer', 'nexus_memcache', 'sentry', 'sentry.client',
            'sentry.plugins.sentry_urls', 'sentry.plugins.sentry_sites', 'sentry.plugins.sentry_servers',
            'gargoyle'):
    try:
        __import__(mod)
    except Exception, e:
        pass
    else:
        INSTALLED_APPS = INSTALLED_APPS + (mod,)

try:
    from local_settings import *
except ImportError, e:
    print e
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

from django.contrib import admin

import nexus

admin.autodiscover()
nexus.autodiscover()

urlpatterns = patterns('',
    url(r'', include(nexus.site.urls)),
)

########NEW FILE########
__FILENAME__ = conf
from django.conf import settings

MEDIA_PREFIX = getattr(settings, 'NEXUS_MEDIA_PREFIX', '/nexus/media/')

if getattr(settings, 'NEXUS_USE_DJANGO_MEDIA_URL', False):
    MEDIA_PREFIX = getattr(settings, 'MEDIA_URL', MEDIA_PREFIX)

########NEW FILE########
__FILENAME__ = models
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

_reqs = ('django.contrib.auth', 'django.contrib.sessions')
if getattr(settings, 'NEXUS_SKIP_INSTALLED_APPS_REQUIREMENTS', False):
    _reqs = ()
for r in _reqs:
    if r not in settings.INSTALLED_APPS:
        raise ImproperlyConfigured("Put '%s' in your "
            "INSTALLED_APPS setting in order to use the nexus application." % r)


########NEW FILE########
__FILENAME__ = modules
from django.core.urlresolvers import reverse
from django.http import HttpRequest

import hashlib
import inspect
import logging
import os
import thread


class NexusModule(object):
    # base url (pattern name) to show in navigation
    home_url = None

    # generic permission required
    permission = None

    media_root = None

    logger_name = None

    # list of active sites within process
    _globals = {}

    def __init__(self, site, category=None, name=None, app_name=None):
        self.category = category
        self.site = site
        self.name = name
        self.app_name = app_name

        # Set up default logging for this module
        if not self.logger_name:
            self.logger_name = 'nexus.%s' % (self.name)
        self.logger = logging.getLogger(self.logger_name)

        if not self.media_root:
            mod = __import__(self.__class__.__module__)
            self.media_root = os.path.normpath(os.path.join(os.path.dirname(mod.__file__), 'media'))

    def __getattribute__(self, name):
        NexusModule.set_global('site', object.__getattribute__(self, 'site'))
        return object.__getattribute__(self, name)

    @classmethod
    def set_global(cls, key, value):
        ident = thread.get_ident()
        if ident not in cls._globals:
            cls._globals[ident] = {}
        cls._globals[ident][key] = value

    @classmethod
    def get_global(cls, key):
        return cls._globals.get(thread.get_ident(), {}).get(key)

    @classmethod
    def get_request(cls):
        """
        Get the HTTPRequest object from thread storage or from a callee by searching
        each frame in the call stack.
        """
        request = cls.get_global('request')
        if request:
            return request
        try:
            stack = inspect.stack()
        except IndexError:
            # in some cases this may return an index error
            # (pyc files dont match py files for example)
            return
        for frame, _, _, _, _, _ in stack:
            if 'request' in frame.f_locals:
                if isinstance(frame.f_locals['request'], HttpRequest):
                    request = frame.f_locals['request']
                    cls.set_global('request', request)
                    return request

    def render_to_string(self, template, context={}, request=None):
        context.update(self.get_context(request))
        return self.site.render_to_string(template, context, request, current_app=self.name)

    def render_to_response(self, template, context={}, request=None):
        context.update(self.get_context(request))
        return self.site.render_to_response(template, context, request, current_app=self.name)

    def as_view(self, *args, **kwargs):
        if 'extra_permission' not in kwargs:
            kwargs['extra_permission'] = self.permission
        return self.site.as_view(*args, **kwargs)

    def get_context(self, request):
        title = self.get_title()
        return {
            'title': title,
            'module_title': title,
            'trail_bits': self.get_trail(request),
        }

    def get_namespace(self):
        return hashlib.md5(self.__class__.__module__ + '.' + self.__class__.__name__).hexdigest()

    def get_title(self):
        return self.__class__.__name__

    def get_dashboard_title(self):
        return self.get_title()

    def get_urls(self):
        try:
            from django.conf.urls import patterns
        except ImportError:  # Django<=1.4
            from django.conf.urls.defaults import patterns

        return patterns('')

    def urls(self):
        if self.app_name and self.name:
            return self.get_urls(), self.app_name, self.name
        return self.get_urls()

    urls = property(urls)


    def get_trail(self, request):
        return [
            (self.get_title(), self.get_home_url(request)),
        ]

    def get_home_url(self, request):
        if self.home_url:
            if self.app_name:
                home_url_name = '%s:%s' % (self.app_name, self.home_url)
            else:
                home_url_name = self.home_url

            home_url = reverse(home_url_name, current_app=self.name)
        else:
            home_url = None

        return home_url



########NEW FILE########
__FILENAME__ = nexus_modules
import nexus

from django.conf import settings
from django.contrib import admin
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

def make_nexus_model_admin(model_admin):
    class NexusModelAdmin(model_admin.__class__):
        delete_selected_confirmation_template = 'nexus/admin/delete_selected_confirmation.html'

        def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
            opts = self.model._meta
            app_label = opts.app_label

            self.add_form_template = self.change_form_template = (
                'nexus/admin/%s/%s/change_form.html' % (app_label, opts.object_name.lower()),
                'nexus/admin/%s/change_form.html' % app_label,
                'nexus/admin/change_form.html',
            )

            extra_context = self.admin_site.get_context(request)
            del extra_context['title']

            context.update(extra_context)
            return super(NexusModelAdmin, self).render_change_form(request, context, add, change, form_url, obj)

        def changelist_view(self, request, extra_context=None):
            opts = self.model._meta
            app_label = opts.app_label
            
            self.change_list_template = (
                'nexus/admin/%s/%s/change_list.html' % (app_label, opts.object_name.lower()),
                'nexus/admin/%s/change_list.html' % app_label,
                'nexus/admin/change_list.html'
            )

            if not extra_context:
                extra_context = self.admin_site.get_context(request)
            else:
                extra_context.update(self.admin_site.get_context(request))
            
            del extra_context['title']
            return super(NexusModelAdmin, self).changelist_view(request, extra_context)

        def delete_view(self, request, object_id, extra_context=None):
            opts = self.model._meta
            app_label = opts.app_label
            
            self.delete_confirmation_template = (
                'nexus/admin/%s/%s/delete_confirmation.html' % (app_label, opts.object_name.lower()),
                'nexus/admin/%s/delete_confirmation.html' % app_label,
                'nexus/admin/delete_confirmation.html'
            )

            if not extra_context:
                extra_context = self.admin_site.get_context(request)
            else:
                extra_context.update(self.admin_site.get_context(request))
            
            del extra_context['title']
            return super(NexusModelAdmin, self).delete_view(request, object_id, extra_context)

        def history_view(self, request, object_id, extra_context=None):
            opts = self.model._meta
            app_label = opts.app_label
            
            self.object_history_template = (
                'nexus/admin/%s/%s/object_history.html' % (app_label, opts.object_name.lower()),
                'nexus/admin/%s/object_history.html' % app_label,
                'nexus/admin/object_history.html'
            )

            if not extra_context:
                extra_context = self.admin_site.get_context(request)
            else:
                extra_context.update(self.admin_site.get_context(request))
            
            del extra_context['title']
            return super(NexusModelAdmin, self).history_view(request, object_id, extra_context)
    return NexusModelAdmin

def make_nexus_admin_site(admin_site):
    class NexusAdminSite(admin_site.__class__):
        index_template = 'nexus/admin/index.html'
        app_index_template = None
        password_change_template = 'nexus/admin/password_change_form.html'
        password_change_done_template = 'nexus/admin/password_change_done.html'
        
        def has_permission(self, request):
            return self.module.site.has_permission(request)

        def get_context(self, request):
            context = self.module.get_context(request)
            context.update(self.module.site.get_context(request))
            return context

        def index(self, request, extra_context=None):
            return super(NexusAdminSite, self).index(request, self.get_context(request))

        def app_index(self, request, app_label, extra_context=None):
            self.app_index_template = (
               'nexus/admin/%s/app_index.html' % app_label,
               'nexus/admin/app_index.html'
            )
            return super(NexusAdminSite, self).app_index(request, app_label, self.get_context(request))

        def password_change(self, request):
            from django.contrib.auth.forms import PasswordChangeForm
            if self.root_path is not None:
                post_change_redirect = '%spassword_change/done/' % self.root_path
            else:
                post_change_redirect = reverse('admin:password_change_done', current_app=self.name)

            if request.method == "POST":
                form = PasswordChangeForm(user=request.user, data=request.POST)
                if form.is_valid():
                    form.save()
                    return HttpResponseRedirect(post_change_redirect)
            else:
                form = PasswordChangeForm(user=request.user)

            return self.module.render_to_response(self.password_change_template, {
                'form': form,
            }, request)

        def password_change_done(self, request):
            return self.module.render_to_response(self.password_change_done_template, {}, request)
    return NexusAdminSite


def make_admin_module(admin_site, name=None, app_name='admin'):
    # XXX: might be a better API so we dont need to do this?
    new_site = make_nexus_admin_site(admin_site)(name, app_name)
    for model, admin in admin_site._registry.iteritems():
        new_site.register(model, make_nexus_model_admin(admin))

    class AdminModule(nexus.NexusModule):
        home_url = 'index'
        admin_site = new_site

        def __init__(self, *args, **kwargs):
            super(AdminModule, self).__init__(*args, **kwargs)
            self.app_name = new_site.app_name
            self.name = new_site.name
            new_site.module = self
            # new_site.name = self.site.name

        def get_urls(self):
            return self.admin_site.get_urls()

        def urls(self):
            return self.admin_site.urls[0], self.app_name, self.name

        urls = property(urls)

        def get_title(self):
            return 'Model Admin'

        def render_on_dashboard(self, request):
            return self.render_to_string('nexus/admin/dashboard/index.html', {
                'base_url': './' + self.app_name + '/'
            }, request)
    return AdminModule

if 'django.contrib.admin' in settings.INSTALLED_APPS:
    nexus.site.register(make_admin_module(admin.site, admin.site.name, admin.site.app_name), admin.site.app_name)
########NEW FILE########
__FILENAME__ = sites
# Core site concept heavily inspired by django.contrib.sites

from django.core.context_processors import csrf
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotModified, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.datastructures import SortedDict
from django.utils.http import http_date
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.static import was_modified_since

try:
    from django.utils.functional import update_wrapper
except ImportError:  # Django>=1.6
    from functools import update_wrapper

from nexus import conf

import mimetypes
import os
import os.path
import posixpath
import stat
import urllib

NEXUS_ROOT = os.path.normpath(os.path.dirname(__file__))


try:
    from django.views.decorators.csrf import ensure_csrf_cookie
except ImportError:  # must be < Django 1.3
    from django.views.decorators.csrf import CsrfViewMiddleware
    from django.middleware.csrf import get_token
    from django.utils.decorators import decorator_from_middleware

    class _EnsureCsrfCookie(CsrfViewMiddleware):
        def _reject(self, request, reason):
            return None

        def process_view(self, request, callback, callback_args, callback_kwargs):
            retval = super(_EnsureCsrfCookie, self).process_view(request, callback, callback_args, callback_kwargs)
            # Forces process_response to send the cookie
            get_token(request)
            return retval


    ensure_csrf_cookie = decorator_from_middleware(_EnsureCsrfCookie)
    ensure_csrf_cookie.__name__ = 'ensure_csrf_cookie'
    ensure_csrf_cookie.__doc__ = """
    Use this decorator to ensure that a view sets a CSRF cookie, whether or not it
    uses the csrf_token template tag, or the CsrfViewMiddleware is used.
    """


class NexusSite(object):
    def __init__(self, name=None, app_name='nexus'):
        self._registry = {}
        self._categories = SortedDict()
        if name is None:
            self.name = 'nexus'
        else:
            self.name = name
        self.app_name = app_name

    def register_category(self, category, label, index=None):
        if index:
            self._categories.insert(index, category, label)
        else:
            self._categories[category] = label

    def register(self, module, namespace=None, category=None):
        module = module(self, category)
        if not namespace:
            namespace = module.get_namespace()
        if namespace:
            module.app_name = module.name = namespace
        self._registry[namespace] = (module, category)
        return module

    def unregister(self, namespace):
        if namespace in self._registry:
            del self._registry[namespace]

    def get_urls(self):
        try:
            from django.conf.urls import patterns, url, include
        except ImportError:  # Django<=1.4
            from django.conf.urls.defaults import patterns, url, include

        base_urls = patterns('',
            url(r'^media/(?P<module>[^/]+)/(?P<path>.+)$', self.media, name='media'),

            url(r'^$', self.as_view(self.dashboard), name='index'),
            url(r'^login/$', self.login, name='login'),
            url(r'^logout/$', self.as_view(self.logout), name='logout'),
        ), self.app_name, self.name

        urlpatterns = patterns('',
            url(r'^', include(base_urls)),
        )
        for namespace, module in self.get_modules():
            urlpatterns += patterns('',
                url(r'^%s/' % namespace, include(module.urls)),
            )

        return urlpatterns

    def urls(self):
        return self.get_urls()

    urls = property(urls)

    def has_permission(self, request, extra_permission=None):
        """
        Returns True if the given HttpRequest has permission to view
        *at least one* page in the admin site.
        """
        permission = request.user.is_active and request.user.is_staff
        if extra_permission:
            permission = permission and request.user.has_perm(extra_permission)
        return permission

    def as_view(self, view, cacheable=False, extra_permission=None):
        """
        Wraps a view in authentication/caching logic

        extra_permission can be used to require an extra permission for this view, such as a module permission
        """
        def inner(request, *args, **kwargs):
            if not self.has_permission(request, extra_permission):
                # show login pane
                return self.login(request)
            return view(request, *args, **kwargs)

        # Mark it as never_cache
        if not cacheable:
            inner = never_cache(inner)

        # We add csrf_protect here so this function can be used as a utility
        # function for any view, without having to repeat 'csrf_protect'.
        if not getattr(view, 'csrf_exempt', False):
            inner = csrf_protect(inner)

        inner = ensure_csrf_cookie(inner)

        return update_wrapper(inner, view)

    def get_context(self, request):
        context = csrf(request)
        context.update({
            'request': request,
            'nexus_site': self,
            'nexus_media_prefix': conf.MEDIA_PREFIX.rstrip('/'),
        })
        return context

    def get_modules(self):
        for k, v in self._registry.iteritems():
            yield k, v[0]

    def get_module(self, module):
        return self._registry[module][0]

    def get_categories(self):
        for k, v in self._categories.iteritems():
            yield k, v

    def get_category_label(self, category):
        return self._categories.get(category, category.title().replace('_', ' '))

    def render_to_string(self, template, context, request, current_app=None):
        if not current_app:
            current_app = self.name
        else:
            current_app = '%s:%s' % (self.name, current_app)

        if request:
            context_instance = RequestContext(request, current_app=current_app)
        else:
            context_instance = None

        context.update(self.get_context(request))

        return render_to_string(template, context,
            context_instance=context_instance
        )

    def render_to_response(self, template, context, request, current_app=None):
        "Shortcut for rendering to response and default context instances"
        if not current_app:
            current_app = self.name
        else:
            current_app = '%s:%s' % (self.name, current_app)

        if request:
            context_instance = RequestContext(request, current_app=current_app)
        else:
            context_instance = None

        context.update(self.get_context(request))

        return render_to_response(template, context,
            context_instance=context_instance
        )

    ## Our views

    def media(self, request, module, path):
        """
        Serve static files below a given point in the directory structure.
        """
        if module == 'nexus':
            document_root = os.path.join(NEXUS_ROOT, 'media')
        else:
            document_root = self.get_module(module).media_root

        path = posixpath.normpath(urllib.unquote(path))
        path = path.lstrip('/')
        newpath = ''
        for part in path.split('/'):
            if not part:
                # Strip empty path components.
                continue
            drive, part = os.path.splitdrive(part)
            head, part = os.path.split(part)
            if part in (os.curdir, os.pardir):
                # Strip '.' and '..' in path.
                continue
            newpath = os.path.join(newpath, part).replace('\\', '/')
        if newpath and path != newpath:
            return HttpResponseRedirect(newpath)
        fullpath = os.path.join(document_root, newpath)
        if os.path.isdir(fullpath):
            raise Http404("Directory indexes are not allowed here.")
        if not os.path.exists(fullpath):
            raise Http404('"%s" does not exist' % fullpath)
        # Respect the If-Modified-Since header.
        statobj = os.stat(fullpath)
        mimetype = mimetypes.guess_type(fullpath)[0] or 'application/octet-stream'
        if not was_modified_since(request.META.get('HTTP_IF_MODIFIED_SINCE'),
                                  statobj[stat.ST_MTIME], statobj[stat.ST_SIZE]):
            return HttpResponseNotModified(mimetype=mimetype)
        contents = open(fullpath, 'rb').read()
        response = HttpResponse(contents, mimetype=mimetype)
        response["Last-Modified"] = http_date(statobj[stat.ST_MTIME])
        response["Content-Length"] = len(contents)
        return response

    def login(self, request, form_class=None):
        "Login form"
        from django.contrib.auth import login as login_
        from django.contrib.auth.forms import AuthenticationForm

        if form_class is None:
            form_class = AuthenticationForm

        if request.POST:
            form = form_class(request, request.POST)
            if form.is_valid():
                login_(request, form.get_user())
                request.session.save()
                return HttpResponseRedirect(request.POST.get('next') or reverse('nexus:index', current_app=self.name))
            else:
                request.session.set_test_cookie()
        else:
            form = form_class(request)
            request.session.set_test_cookie()

        return self.render_to_response('nexus/login.html', {
            'form': form,
        }, request)
    login = never_cache(login)

    def logout(self, request):
        "Logs out user and redirects them to Nexus home"
        from django.contrib.auth import logout

        logout(request)

        return HttpResponseRedirect(reverse('nexus:index', current_app=self.name))

    def dashboard(self, request):
        "Basic dashboard panel"
        # TODO: these should be ajax
        module_set = []
        for namespace, module in self.get_modules():
            home_url = module.get_home_url(request)

            if hasattr(module, 'render_on_dashboard'):
                # Show by default, unless a permission is required
                if not module.permission or request.user.has_perm(module.permission):
                    module_set.append((module.get_dashboard_title(), module.render_on_dashboard(request), home_url))

        return self.render_to_response('nexus/dashboard.html', {
            'module_set': module_set,
        }, request)

# setup the default site

site = NexusSite()


########NEW FILE########
__FILENAME__ = nexus_admin
from django import template

register = template.Library()

def submit_row(context):
    """
    Displays the row of buttons for delete and save. 
    """
    opts = context['opts']
    change = context['change']
    is_popup = context['is_popup']
    save_as = context['save_as']
    return {
        'onclick_attrib': (opts.get_ordered_objects() and change
                            and 'onclick="submitOrderForm();"' or ''),
        'show_delete_link': (not is_popup and context['has_delete_permission']
                              and (change or context['show_delete'])),
        'show_save_as_new': not is_popup and change and save_as,
        'show_save_and_add_another': context['has_add_permission'] and 
                            not is_popup and (not save_as or context['add']),
        'show_save_and_continue': not is_popup and context['has_change_permission'],
        'is_popup': is_popup,
        'show_save': True,
    }
submit_row = register.inclusion_tag('nexus/admin/submit_line.html', takes_context=True)(submit_row)

########NEW FILE########
__FILENAME__ = nexus_helpers
from django import template
from django.utils.datastructures import SortedDict

import nexus
from nexus import conf
from nexus.modules import NexusModule

register = template.Library()


def nexus_media_prefix():
    return conf.MEDIA_PREFIX.rstrip('/')
register.simple_tag(nexus_media_prefix)


def nexus_version():
    return nexus.VERSION
register.simple_tag(nexus_version)


def show_navigation(context):
    site = context.get('nexus_site', NexusModule.get_global('site'))
    request = NexusModule.get_request()

    category_link_set = SortedDict([(k, {
        'label': v,
        'links': [],
    }) for k, v in site.get_categories()])

    for namespace, module in site._registry.iteritems():
        module, category = module

        if module.permission and not request.user.has_perm(module.permission):
            continue

        home_url = None
        if 'request' in context:
            home_url = module.get_home_url(context['request'])

        if not home_url:
            continue

        active = request.path.startswith(home_url)

        if category not in category_link_set:
            if category:
                label = site.get_category_label(category)
            else:
                label = None
            category_link_set[category] = {
                'label': label,
                'links': []
            }

        category_link_set[category]['links'].append((module.get_title(), home_url, active))

        category_link_set[category]['active'] = active

    return {
        'nexus_site': site,
        'category_link_set': category_link_set.itervalues(),
    }
register.inclusion_tag('nexus/navigation.html', takes_context=True)(show_navigation)

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import sys
from os.path import dirname, abspath

from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASE_ENGINE='sqlite3',
        # HACK: this fixes our threaded runserver remote tests
        # TEST_DATABASE_NAME='test_sentry',
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.admin',
            'django.contrib.sessions',
            'django.contrib.sites',

            # Included to fix Disqus' test Django which solves IntegrityMessage case
            'django.contrib.contenttypes',
            'nexus',
        ],
        ROOT_URLCONF='',
        DEBUG=False,
    )


from django.test.simple import DjangoTestSuiteRunner
test_runner = DjangoTestSuiteRunner(verbosity=2, interactive=True)


# from south.management.commands import patch_for_test_db_setup
# patch_for_test_db_setup()

def runtests(*test_args):
    if not test_args:
        test_args = ['nexus']

    parent = dirname(abspath(__file__))
    sys.path.insert(0, parent)

    failures = test_runner.run_tests(test_args)

    if failures:
        sys.exit(failures)

if __name__ == '__main__':
    runtests(*sys.argv[1:])

########NEW FILE########
