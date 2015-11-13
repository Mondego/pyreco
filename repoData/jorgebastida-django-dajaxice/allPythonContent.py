__FILENAME__ = Dajaxice
import logging

from django.utils.importlib import import_module

log = logging.getLogger('dajaxice')


class DajaxiceFunction(object):
    """ Basic representation of a dajaxice ajax function."""

    def __init__(self, function, name, method):
        self.function = function
        self.name = name
        self.method = method

    def call(self, *args, **kwargs):
        """ Call the function. """
        return self.function(*args, **kwargs)


class DajaxiceModule(object):
    """ Basic representation of a dajaxice module. """

    def __init__(self, name=None):
        self.name = name
        self.functions = {}
        self.submodules = {}

    def add(self, name, function):
        """ Add this function at the ``name`` deep. If the submodule already
        exists, recusively call the add method into the submodule. If not,
        create the module and call the add method."""

        # If this is not the final function name (there are more modules)
        # split the name again an register a new submodule.
        if '.' in name:
            module, extra = name.split('.', 1)
            if module not in self.submodules:
                self.submodules[module] = DajaxiceModule(module)
            self.submodules[module].add(extra, function)
        else:
            self.functions[name] = function


class Dajaxice(object):

    def __init__(self):
        self._registry = {}
        self._modules = None

    def register(self, function, name=None, method='POST'):
        """
        Register this function as a dajaxice function.

        If no name is provided, the module and the function name will be used.
        The final (customized or not) must be unique. """

        method = self.clean_method(method)

        # Generate a default name
        if not name:
            module = ''.join(str(function.__module__).rsplit('.ajax', 1))
            name = '.'.join((module, function.__name__))

        if ':' in name:
            log.error('Ivalid function name %s.' % name)
            return

        # Check for already registered functions
        if name in self._registry:
            log.error('%s was already registered.' % name)
            return

        # Create the dajaxice function.
        function = DajaxiceFunction(function=function,
                                    name=name,
                                    method=method)

        # Register this new ajax function
        self._registry[name] = function

    def is_callable(self, name, method):
        """ Return if the function callable or not. """
        return name in self._registry and self._registry[name].method == method

    def clean_method(self, method):
        """ Clean the http method. """
        method = method.upper()
        if method not in ['GET', 'POST']:
            method = 'POST'
        return method

    def get(self, name):
        """ Return the dajaxice function."""
        return self._registry[name]

    @property
    def modules(self):
        """ Return an easy to loop module hierarchy with all the functions."""
        if not self._modules:
            self._modules = DajaxiceModule()
            for name, function in self._registry.items():
                self._modules.add(name, function)
        return self._modules

LOADING_DAJAXICE = False


def dajaxice_autodiscover():
    """
    Auto-discover INSTALLED_APPS ajax.py modules and fail silently when
    not present. NOTE: dajaxice_autodiscover was inspired/copied from
    django.contrib.admin autodiscover
    """
    global LOADING_DAJAXICE
    if LOADING_DAJAXICE:
        return
    LOADING_DAJAXICE = True

    import imp
    from django.conf import settings

    for app in settings.INSTALLED_APPS:

        try:
            app_path = import_module(app).__path__
        except AttributeError:
            continue

        try:
            imp.find_module('ajax', app_path)
        except ImportError:
            continue

        import_module("%s.ajax" % app)

    LOADING_DAJAXICE = False

########NEW FILE########
__FILENAME__ = decorators
import functools

from dajaxice.core import dajaxice_functions


def dajaxice_register(*dargs, **dkwargs):
    """ Register some function as a dajaxice function

    For legacy purposes, if only a function is passed register it a simple
    single ajax function using POST, i.e:

    @dajaxice_register
    def ajax_function(request):
        ...

    After 0.5, dajaxice allow to customize the http method and the final name
    of the registered function. This decorator covers both the legacy and
    the new functionality, i.e:

    @dajaxice_register(method='GET')
    def ajax_function(request):
        ...

    @dajaxice_register(method='GET', name='my.custom.name')
    def ajax_function(request):
        ...

    You can also register the same function to use a different http method
    and/or use a different name.

    @dajaxice_register(method='GET', name='users.get')
    @dajaxice_register(method='POST', name='users.update')
    def ajax_function(request):
        ...
    """

    if len(dargs) and not dkwargs:
        function = dargs[0]
        dajaxice_functions.register(function)
        return function

    def decorator(function):
        @functools.wraps(function)
        def wrapper(request, *args, **kwargs):
            return function(request, *args, **kwargs)
        dajaxice_functions.register(function, *dargs, **dkwargs)
        return wrapper
    return decorator

########NEW FILE########
__FILENAME__ = exceptions
class DajaxiceError(Exception):
    pass


class FunctionNotCallableError(DajaxiceError):
    pass


class DajaxiceImportError(DajaxiceError):
    pass

########NEW FILE########
__FILENAME__ = finders
import os
import tempfile

from django.contrib.staticfiles import finders
from django.template import Context
from django.template.loader import get_template
from django.core.exceptions import SuspiciousOperation


class VirtualStorage(finders.FileSystemStorage):
    """" Mock a FileSystemStorage to build tmp files on demand."""

    def __init__(self, *args, **kwargs):
        self._files_cache = {}
        super(VirtualStorage, self).__init__(*args, **kwargs)

    def get_or_create_file(self, path):
        if path not in self.files:
            return ''

        data = getattr(self, self.files[path])()

        try:
            current_file = open(self._files_cache[path])
            current_data = current_file.read()
            current_file.close()
            if current_data != data:
                os.remove(path)
                raise Exception("Invalid data")
        except Exception:
            handle, tmp_path = tempfile.mkstemp()
            tmp_file = open(tmp_path, 'w')
            tmp_file.write(data)
            tmp_file.close()
            self._files_cache[path] = tmp_path

        return self._files_cache[path]

    def exists(self, name):
        return name in self.files

    def listdir(self, path):
        folders, files = [], []
        for f in self.files:
            if f.startswith(path):
                f = f.replace(path, '', 1)
                if os.sep in f:
                    folders.append(f.split(os.sep, 1)[0])
                else:
                    files.append(f)
        return folders, files

    def path(self, name):
        try:
            path = self.get_or_create_file(name)
        except ValueError:
            raise SuspiciousOperation("Attempted access to '%s' denied." % name)
        return os.path.normpath(path)


class DajaxiceStorage(VirtualStorage):

    files = {os.path.join('dajaxice', 'dajaxice.core.js'): 'dajaxice_core_js'}

    def dajaxice_core_js(self):
        from dajaxice.core import dajaxice_autodiscover, dajaxice_config

        dajaxice_autodiscover()

        c = Context({'dajaxice_config': dajaxice_config})
        return get_template(os.path.join('dajaxice', 'dajaxice.core.js')).render(c)


class DajaxiceFinder(finders.BaseStorageFinder):
    storage = DajaxiceStorage()

########NEW FILE########
__FILENAME__ = models
# Don't delete me

########NEW FILE########
__FILENAME__ = dajaxice_templatetags
import logging

from django import template
from django.middleware.csrf import get_token
from django.conf import settings
from django.core.files.storage import get_storage_class

staticfiles_storage = get_storage_class(settings.STATICFILES_STORAGE)()

register = template.Library()

log = logging.getLogger('dajaxice')


@register.simple_tag(takes_context=True)
def dajaxice_js_import(context, csrf=True):
    """ Return the js script tag for the dajaxice.core.js file
    If the csrf argument is present and it's ``nocsrf`` dajaxice will not
    try to mark the request as if it need the csrf token. By default use
    the dajaxice_js_import template tag will make django set the csrftoken
    cookie on the current request."""

    csrf = csrf != 'nocsrf'
    request = context.get('request')

    if request and csrf:
        get_token(request)
    elif csrf:
        log.warning("The 'request' object must be accesible within the "
                    "context. You must add 'django.contrib.messages.context"
                    "_processors.request' to your TEMPLATE_CONTEXT_PROCESSORS "
                    "and render your views using a RequestContext.")

    url = staticfiles_storage.url('dajaxice/dajaxice.core.js')
    return '<script src="%s" type="text/javascript" charset="utf-8"></script>' % url

########NEW FILE########
__FILENAME__ = ajax
from django.utils import simplejson
from dajaxice.decorators import dajaxice_register


@dajaxice_register
def test_registered_function(request):
    return ""


@dajaxice_register
def test_string(request):
    return simplejson.dumps({'string': 'hello world'})


@dajaxice_register
def test_ajax_exception(request):
    raise Exception()


@dajaxice_register
def test_foo(request):
    return simplejson.dumps({'foo': 'bar'})


@dajaxice_register
def test_foo_with_params(request, param1):
    return simplejson.dumps({'param1': param1})


@dajaxice_register(method='GET')
def test_get_register(request):
    return simplejson.dumps({'foo': 'user'})


@dajaxice_register(method='GET', name="get_user_data")
def test_get_with_name_register(request):
    return simplejson.dumps({'bar': 'user'})


@dajaxice_register(method='GET', name="get_multi")
@dajaxice_register(name="post_multi")
def test_multi_register(request):
    return simplejson.dumps({'foo': 'multi'})

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from dajaxice.core import dajaxice_autodiscover, dajaxice_config

dajaxice_autodiscover()

urlpatterns = patterns('',
    #Dajaxice URLS
    url(dajaxice_config.dajaxice_url, include('dajaxice.urls')),
)

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url

from .views import DajaxiceRequest

urlpatterns = patterns('dajaxice.views',
    url(r'^(.+)/$', DajaxiceRequest.as_view(), name='dajaxice-call-endpoint'),
    url(r'', DajaxiceRequest.as_view(), name='dajaxice-endpoint'),
)

########NEW FILE########
__FILENAME__ = utils
from django.http import QueryDict


def deserialize_form(data):
    """
    Create a new QueryDict from a serialized form.
    """
    return QueryDict(query_string=unicode(data).encode('utf-8'))

########NEW FILE########
__FILENAME__ = views
import logging

from django.conf import settings
from django.utils import simplejson
from django.views.generic.base import View
from django.http import HttpResponse, Http404

from dajaxice.exceptions import FunctionNotCallableError
from dajaxice.core import dajaxice_functions, dajaxice_config

log = logging.getLogger('dajaxice')


def safe_dict(d):
    """
    Recursively clone json structure with UTF-8 dictionary keys
    http://www.gossamer-threads.com/lists/python/bugs/684379
    """
    if isinstance(d, dict):
        return dict([(k.encode('utf-8'), safe_dict(v)) for k, v in d.iteritems()])
    elif isinstance(d, list):
        return [safe_dict(x) for x in d]
    else:
        return d


class DajaxiceRequest(View):
    """ Handle all the dajaxice xhr requests. """

    def dispatch(self, request, name=None):

        if not name:
            raise Http404

        # Check if the function is callable
        if dajaxice_functions.is_callable(name, request.method):

            function = dajaxice_functions.get(name)
            data = getattr(request, function.method).get('argv', '')

            # Clean the argv
            if data != 'undefined':
                try:
                    data = safe_dict(simplejson.loads(data))
                except Exception:
                    data = {}
            else:
                data = {}

            # Call the function. If something goes wrong, handle the Exception
            try:
                response = function.call(request, **data)
            except Exception:
                if settings.DEBUG:
                    raise
                response = dajaxice_config.DAJAXICE_EXCEPTION

            return HttpResponse(response, mimetype="application/x-json")
        else:
            raise FunctionNotCallableError(name)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-dajaxice documentation build configuration file, created by
# sphinx-quickstart on Fri May 25 08:02:23 2012.
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
#sys.path.insert(0, os.path.abspath('.'))

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
project = u'django-dajaxice'
copyright = u'2012, Jorge Bastida'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
import pkg_resources
try:
    release = pkg_resources.get_distribution('django-dajaxice').version
except pkg_resources.DistributionNotFound:
    print 'To build the documentation, The distribution information of django-dajaxice'
    print 'Has to be available.  Either install the package into your'
    print 'development environment or run "setup.py develop" to setup the'
    print 'metadata.  A virtualenv is recommended!'
    sys.exit(1)
del pkg_resources

version = '.'.join(release.split('.')[:2])

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
exclude_patterns = ['_build']

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
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'nature'

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

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-dajaxicedoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-dajaxice.tex', u'django-dajaxice Documentation',
   u'Jorge Bastida', 'manual'),
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
    ('index', 'django-dajaxice', u'django-dajaxice Documentation',
     [u'Jorge Bastida'], 1)
]

########NEW FILE########
__FILENAME__ = settings
# Django settings for examples project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
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
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = 'static'

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '$zr@-0lstgzehu)k(-pbg7wz=mv8%n%o7+j_@h&amp;-yy&amp;sx)pyau'

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
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'examples.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'examples.wsgi.application'

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
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dajaxice',
    'simple'
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'dajaxice': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    }
}

STATICFILES_FINDERS = ("django.contrib.staticfiles.finders.FileSystemFinder",
                       "django.contrib.staticfiles.finders.AppDirectoriesFinder",
                       "dajaxice.finders.DajaxiceFinder")

TEMPLATE_CONTEXT_PROCESSORS = ("django.contrib.auth.context_processors.auth",
                               "django.core.context_processors.debug",
                               "django.core.context_processors.i18n",
                               "django.core.context_processors.media",
                               "django.core.context_processors.static",
                               "django.core.context_processors.request",
                               "django.contrib.messages.context_processors.messages")

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from dajaxice.core import dajaxice_autodiscover, dajaxice_config
dajaxice_autodiscover()

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'examples.views.home', name='home'),
    # url(r'^examples/', include('examples.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
    (dajaxice_config.dajaxice_url, include('dajaxice.urls')),
    url(r'', 'simple.views.index')
)

urlpatterns += staticfiles_urlpatterns()

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for examples project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "examples.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "examples.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = ajax
import simplejson

from dajaxice.decorators import dajaxice_register


@dajaxice_register(method='GET')
@dajaxice_register(method='POST', name='other_post')
def hello(request):
    return simplejson.dumps({'message': 'hello'})


@dajaxice_register(method='GET')
@dajaxice_register(method='POST', name="more.complex.bye")
def bye(request):
    raise Exception("PUMMMM")
    return simplejson.dumps({'message': 'bye'})


@dajaxice_register
def lol(request):
    return simplejson.dumps({'message': 'lol'})


@dajaxice_register(method='GET')
def get_args(request, foo):
    return simplejson.dumps({'message': 'hello get args %s' % foo})

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
# Create your views here.
from django.shortcuts import render

from dajaxice.core import dajaxice_functions


def index(request):

    return render(request, 'simple/index.html')

########NEW FILE########
