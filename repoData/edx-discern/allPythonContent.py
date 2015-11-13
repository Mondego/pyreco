__FILENAME__ = aws
"""
Deployment settings file
"""

from settings import *
import json

DEBUG=False

TIME_BETWEEN_INDEX_REBUILDS = 60 * 30 # seconds

#Tastypie throttle settings
THROTTLE_AT = 100 #Throttle requests after this number in below timeframe
THROTTLE_TIMEFRAME= 60 * 60 #Timeframe in which to throttle N requests, seconds
THROTTLE_EXPIRATION= 24 * 60 * 60 # When to remove throttle entries from cache, seconds

with open(os.path.join(ENV_ROOT,"env.json")) as env_file:
    ENV_TOKENS = json.load(env_file)

with open(os.path.join(ENV_ROOT, "auth.json")) as auth_file:
    AUTH_TOKENS = json.load(auth_file)

DATABASES = AUTH_TOKENS.get('DATABASES', DATABASES)
CACHES = AUTH_TOKENS.get('CACHES', CACHES)

AWS_ACCESS_KEY_ID = AUTH_TOKENS.get('AWS_ACCESS_KEY_ID', AWS_ACCESS_KEY_ID)
AWS_SECRET_ACCESS_KEY = AUTH_TOKENS.get('AWS_SECRET_ACCESS_KEY', AWS_SECRET_ACCESS_KEY)

USE_S3_TO_STORE_MODELS = ENV_TOKENS.get('USE_S3_TO_STORE_MODELS', USE_S3_TO_STORE_MODELS)
S3_BUCKETNAME = ENV_TOKENS.get('S3_BUCKETNAME', S3_BUCKETNAME)

BROKER_URL = AUTH_TOKENS.get('BROKER_URL', BROKER_URL)
CELERY_RESULT_BACKEND = AUTH_TOKENS.get('CELERY_RESULT_BACKEND', CELERY_RESULT_BACKEND)


ELB_HOSTNAME = ENV_TOKENS.get('ELB_HOSTNAME', None)

DNS_HOSTNAME = ENV_TOKENS.get('DNS_HOSTNAME', None)

if ELB_HOSTNAME is not None:
    ALLOWED_HOSTS += [ELB_HOSTNAME]

if DNS_HOSTNAME is not None:
    ALLOWED_HOSTS += [DNS_HOSTNAME]

EMAIL_BACKEND = ENV_TOKENS.get('EMAIL_BACKEND', EMAIL_BACKEND)

DEFAULT_FROM_EMAIL = ENV_TOKENS.get('DEFAULT_FROM_EMAIL')

ACCOUNT_EMAIL_VERIFICATION = ENV_TOKENS.get('ACCOUNT_EMAIL_VERIFICATION', ACCOUNT_EMAIL_VERIFICATION)

AWS_SES_REGION_NAME = ENV_TOKENS.get('AWS_SES_REGION_NAME', 'us-east-1')
if AWS_SES_REGION_NAME is not None:
    AWS_SES_REGION_ENDPOINT = 'email.{0}.amazonaws.com'.format(AWS_SES_REGION_NAME)

#Set this for django-analytical.  Because django-analytical enables the service if the key exists,
#ensure that the settings value is only created if the key exists in the deployment settings.
ga_key = AUTH_TOKENS.get("GOOGLE_ANALYTICS_PROPERTY_ID", "")
if len(ga_key)>1:
    GOOGLE_ANALYTICS_PROPERTY_ID = ga_key

#Try to set the domain for the current site
#Needed to get the right site name for email activation
#Comment out, as this is causing issues in deployment.
#TODO: Move to a fixture
"""
try:
    if DNS_HOSTNAME is not None:
        from django.contrib.sites.models import Site
        current_site = Site.objects.get(id=SITE_ID)

        current_site.domain = DNS_HOSTNAME
        current_site.name = DNS_HOSTNAME
        current_site.save()
except:
    log.info("Could not set site name and domain.  Not a problem if this is a dev/sandbox environment.  May cause confusion with email activation in production.")
"""
########NEW FILE########
__FILENAME__ = search_sites
import haystack
haystack.autodiscover()
########NEW FILE########
__FILENAME__ = settings
"""
Local settings file
"""
import sys
import os
from path import path
import logging
log = logging.getLogger(__name__)

#Initialize celery
import djcelery
djcelery.setup_loader()

# Django settings for ml_service_api project.
ROOT_PATH = path(__file__).dirname()
REPO_PATH = ROOT_PATH.dirname()
ENV_ROOT = REPO_PATH.dirname()

#ML Specific settings
ML_MODEL_PATH=os.path.join(REPO_PATH,"ml_models_api/") #Path to save and retrieve ML models from
TIME_BETWEEN_ML_CREATOR_CHECKS= 1 * 60 # seconds.  Time between ML creator checking to see if models need to be made.
TIME_BETWEEN_ML_GRADER_CHECKS= 10 # seconds.  Time between ML grader checking to see if models need to be made.
USE_S3_TO_STORE_MODELS= False #Determines whether or not models are placed in Amazon S3

#Credentials for the S3 bucket.  Do not edit here, but provide the right settings in env.json and auth.json, and then
#use aws.py as the settings file.
S3_BUCKETNAME="OpenEnded"
AWS_ACCESS_KEY_ID = None
AWS_SECRET_ACCESS_KEY = None

TIME_BEFORE_REMOVING_STARTED_MODEL = 10 * 60 * 60 # in seconds, time before removing an ml model that was started (assume it wont finish)
MODEL_CREATION_CACHE_LOCK_TIME = 5 * 60 * 60
GRADING_CACHE_LOCK_TIME = 60 * 60
INDEX_REFRESH_CACHE_LOCK_TIME = 24 * 60 * 60

LOGIN_REDIRECT_URL = "/frontend/"

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DB_PATH = "db/"

#Make the db path dir if it does not exist
if not os.path.isdir(DB_PATH):
    os.mkdir(DB_PATH)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': DB_PATH + 'service-api-db.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

#Need caching for API rate limiting
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'discern-cache'
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
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
STATIC_ROOT = os.path.abspath(REPO_PATH / "staticfiles")

#Make the static root dir if it does not exist
if not os.path.isdir(STATIC_ROOT):
    os.mkdir(STATIC_ROOT)

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.abspath(REPO_PATH / 'css_js_src/'),
)

STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

PIPELINE_JS = {
    'util' : {
        'source_filenames': [
            'js/jquery-1.9.1.js',
            'js/json2.js',
            'js/underscore.js',
            'js/bootstrap.js',
            'js/backbone.js',
            'js/backbone.validations.js',
            'js/backbone-tastypie.js',
            'js/backbone-schema.js',
            'js/setup-env.js',
            'js/api-views.js',
            'js/jquery.cookie.js',
            ],
        'output_filename': 'js/util.js',
    }
}
SESSION_COOKIE_NAME = "mlserviceapisessionid"
CSRF_COOKIE_NAME = "mlserviceapicsrftoken"

API_MODELS = ["userprofile", "user", "membership", "course", "organization", "problem", "essay", "essaygrade"]

for model in API_MODELS:
    PIPELINE_JS[model] = {
        'source_filenames': [
            'js/views/{0}.js'.format(model)
        ],
        'output_filename': 'js/{0}.js'.format(model),
    }

PIPELINE_CSS = {
    'bootstrap': {
        'source_filenames': [
            'css/bootstrap.css',
            'css/bootstrap-responsive.css',
            'css/bootstrap-extensions.css',
            ],
        'output_filename': 'css/bootstrap.css',
        },
    'util_css' : {
        'source_filenames': [
            'css/jquery-ui-1.10.2.custom.css',
            ],
        'output_filename': 'css/util_css.css',
        }
}


PIPELINE_DISABLE_WRAPPER = True
PIPELINE_YUI_BINARY = "yui-compressor"

PIPELINE_CSS_COMPRESSOR = None
PIPELINE_JS_COMPRESSOR = None

PIPELINE_COMPILE_INPLACE = True
PIPELINE = True

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'u)4v9b&amp;9jhsg-&amp;&amp;^*!jff&amp;t1e7$em0uh8^i^w!ojjvr&amp;8$ok6-'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
    "allauth.account.context_processors.account",
    "allauth.socialaccount.context_processors.socialaccount",
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'request_provider.middleware.RequestProvider',
)

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
    "allauth.account.auth_backends.AuthenticationBackend",
)

ANONYMOUS_USER_ID = -1

ROOT_URLCONF = 'discern.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'discern.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.abspath(REPO_PATH / "templates"),
    os.path.abspath(REPO_PATH / "freeform_data")
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    # remove django.contrib.sites to avoid this issue: https://github.com/edx/discern/issues/85
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'tastypie',
    'south',
    'djcelery',
    'pipeline',
    'guardian',
    'haystack',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'analytical',
    'freeform_data',
    'ml_grading',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.

syslog_format = ("[%(name)s][env:{logging_env}] %(levelname)s "
                 "[{hostname}  %(process)d] [%(filename)s:%(lineno)d] "
                 "- %(message)s").format(
    logging_env="", hostname="")

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s %(levelname)s %(process)d '
                      '[%(name)s] %(filename)s:%(lineno)d - %(message)s',
            },
        'syslog_format': {'format': syslog_format},
        'raw': {'format': '%(message)s'},
        },
    'handlers': {
        'console': {
#            'level': 'DEBUG' if DEBUG else 'INFO',
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'stream': sys.stdout,
            },
        'null': {
            'level': 'DEBUG',
            'class':'django.utils.log.NullHandler',
            },
        },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
            },
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False
            },
        'django.db.backends': {
            'handlers': ['null'],  # Quiet by default!
            'propagate': False,
            'level':'DEBUG',
            },
        }
}

AUTH_PROFILE_MODULE = 'freeform_data.UserProfile'

BROKER_URL = 'redis://localhost:6379/5'
BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 3600}
CELERY_RESULT_BACKEND = 'redis://localhost:6379/5'

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

#Haystack settings
HAYSTACK_SITECONF = 'discern.search_sites'
HAYSTACK_SEARCH_ENGINE = 'whoosh'
HAYSTACK_WHOOSH_PATH = os.path.join(REPO_PATH,"whoosh_api_index")
TIME_BETWEEN_INDEX_REBUILDS = 60 # seconds

#Check to see if the ml repo is available or not
FOUND_ML = False
try:
    import ease.grade
    FOUND_ML = True
except:
    pass

#Tastypie throttle settings
THROTTLE_AT = 10000 #Throttle requests after this number in below timeframe, dev settings, so high!
THROTTLE_TIMEFRAME= 60 * 60 #Timeframe in which to throttle N requests, seconds
THROTTLE_EXPIRATION= 24 * 60 * 60 # When to remove throttle entries from cache, seconds

#Model settings
MEMBERSHIP_LIMIT=1 #Currently users can only be in one organization

#Django-allauth settings
ACCOUNT_EMAIL_VERIFICATION = "none" #No email verification required locally
ACCOUNT_EMAIL_REQUIRED = True #Ask user to enter an email
ACCOUNT_AUTHENTICATION_METHOD="username_email" #Can enter username or email to login
ACCOUNT_PASSWORD_MIN_LENGTH = 3 #For testing, set password minimum low.

#Django email backend for local testing
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
########NEW FILE########
__FILENAME__ = test_settings
from settings import *
import logging

south_logger=logging.getLogger('south')
south_logger.setLevel(logging.INFO)

warning_logger=logging.getLogger('py.warnings')
warning_logger.setLevel(logging.ERROR)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME' : DB_PATH + 'service-api-test-db.db',
        }
}

# Nose Test Runner
INSTALLED_APPS += ('django_nose',)
NOSE_ARGS = [ '--with-xunit', '--with-coverage',
              '--cover-html-dir', 'cover',
             '--cover-package', 'freeform_data',
             '--cover-package', 'ml_grading',]
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

#Celery settings
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
CELERY_ALWAYS_EAGER = True
BROKER_BACKEND = 'memory'

#Haystack settings
HAYSTACK_WHOOSH_PATH = os.path.join(ENV_ROOT,"whoosh_api_index_test")

#Model settings
MEMBERSHIP_LIMIT=50 #For testing purposes, relax membership limits

#Some errors only pop up with debug as false
DEBUG=False
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^essay_site/', include('freeform_data.urls')),
    url(r'^frontend/', include('frontend.urls')),
    url(r'^$', include('frontend.urls')),
    url(r'^accounts/', include('allauth.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^status/', 'freeform_data.views.status')
)

if settings.DEBUG:
    #urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT, show_indexes=True)
    urlpatterns+= patterns('',
        url(r'^static/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.STATIC_ROOT,
            'show_indexes' : True,
            }),
        )

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for discern project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "discern.aws")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Discern documentation build configuration file, created by
# sphinx-quickstart on Fri Mar  1 09:51:10 2013.
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
sys.path.append(os.path.abspath('.'))
sys.path.append(os.path.abspath('../'))
sys.path.append(os.path.abspath('../discern'))
sys.path.append(os.path.abspath('../../'))
import settings
from django.core.management import setup_environ
setup_environ(settings)

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.todo', 'sphinx.ext.coverage', 'sphinx.ext.pngmath', 'sphinx.ext.mathjax', 'sphinx.ext.ifconfig', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Discern'
copyright = u'2013, edX'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '.01'
# The full version, including alpha/beta/rc tags.
release = '.01'

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
html_theme = 'default'

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
htmlhelp_basename = 'Discerndoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Discern.tex', u'Discern Documentation',
   u'edX', 'manual'),
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

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'discern', u'Discern Documentation',
     [u'edX'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Discern', u'Discern Documentation',
   u'edX', 'Discern', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = common_settings
"""
Define some constants and imports that we will use for all the examples.
"""

#Common imports.
#Requests allows us to make http GET/POST/PUT, etc requests.
#See http://docs.python-requests.org/en/latest/ for documentation
import requests
#JSON is a format for transferring data over the web.  This imports a json handling library.
#See http://en.wikipedia.org/wiki/JSON for information on JSON.
import json

from pprint import *

#This tells us where the API is running.
API_BASE_URL = "http://127.0.0.1:7999"

headers = {'content-type': 'application/json'}

# Most of the scripts will need to login, use this function to avoid repeating code. 
def login_to_discern(session, username='test', password='test'):
    login_url = API_BASE_URL + "/essay_site/login/"
    return session.post(
        login_url,
        json.dumps({
        'username': username,
        'password': password, }),
        headers=headers)

########NEW FILE########
__FILENAME__ = connect_to_api
"""
Example 1: In this example, we will try some basic API connections.
"""

from common_settings import *

#This queries the top level schema and gets all of the available models, and their associated endpoints and schema.
#The ?format=json is needed to let the API know how to return the data.
#Supported formats are 'json', 'jsonp', 'xml', 'yaml', 'plist'.
response = requests.get(API_BASE_URL + "/essay_site/api/v1/?format=json")

#This status code should be 200.  If it is not, verify that you are running the api server at the API_BASE_URL
#You can use python manage.py runserver 127.0.0.1:7999 --nostatic to accomplish this.
print("Status Code: {0}".format(response.status_code))

#Decode the json serialized response into a python object.
rj = response.json()
print(rj)

#Loop through the json object and print out the data.
for model in rj:
    print("Model: {0} Endpoint: {1} Schema: {2}".format(model, rj[model]['list_endpoint'], rj[model]['schema']))

#Now, let's try to get the schema for a single model.
response = requests.get(API_BASE_URL + rj['essay']['schema'] + "?format=json")

#This should get a 401 error if you are not logged in.
print("Status Code: {0}".format(response.status_code))



########NEW FILE########
__FILENAME__ = create_objects_for_tutorial
'''
Tutorial - Getting started - create a organization course objects
Here we create an institution(i.e., Reddit). Make a note of the resulting URIs.
We will use them with other example programs. 
'''

from common_settings import *

session = requests.session()
response = login_to_discern(session)

# create an organization
org_response = session.post(API_BASE_URL + "/essay_site/api/v1/organization/?format=json",
                            data=json.dumps({"organization_name": "Reddit"}),
                            headers=headers)

# get the URI for the organization 
#    Let's get the text of the response
organization_object = json.loads(org_response.text)
organization_resource_uri = organization_object['resource_uri']


# create a course and associate it with the organization
course_response = session.post(API_BASE_URL + "/essay_site/api/v1/course/?format=json",
                               data=json.dumps(
                                   {"course_name": "Discern Tutorial",
                                    "organizations": [organization_resource_uri]
                                   }),
                               headers=headers)

# Get the URI for the course
course_object = json.loads(course_response.text)

if course_response.status_code >= 400:
    pprint("status: {0} msg: {1}".format(
        course_response.status_code,
        course_response._content))
    pprint(vars(course_response.request))
    exit(1)

course_uri = course_object['resource_uri']

print ("We will be uses the URI for these objects in other scripts. Please make a note")
print ("org URI: {0} ".format(organization_resource_uri))
print ("course URI: {0} ".format(course_uri))

########NEW FILE########
__FILENAME__ = create_related_model
"""
Example 5: In this example, we will create a course object and relate it to our organization object we created earlier.
"""

from common_settings import *

#This is the same login code that we used previously
login_url = API_BASE_URL + "/essay_site/login/"
data = {
    'username' : 'test',
    'password' : 'test'
}
headers = {'content-type': 'application/json'}
session = requests.session()
response = session.post(login_url, data=json.dumps(data),headers=headers)

#We want to create a course object and relate it to our organization object.
# To do this, let's first find our organization object.
response = session.get(API_BASE_URL + "/essay_site/api/v1/organization/?format=json")

#Now, let's get the text of the response
response_text = json.loads(response.text)

#And then let's get the object that we created in the last example
organization_object = response_text["objects"][0]
organization_resource_uri = organization_object['resource_uri']

#The resource uri is how we identify objects and relate them to each other.
#We can see that the organization object has a resource uri field.
#We can also see that the users, memberships, and courses fields relate the object to other objects via uris.

#Now, let's get the schema for a course.
response = session.get(API_BASE_URL + "/essay_site/api/v1/course/schema/?format=json")
course_schema = json.loads(response.text)

#this will show us what data we need to provide for each field
for field in course_schema['fields'].keys():
    field_data = course_schema['fields'][field]
    print "Name: {0} || Can be blank: {1} || Type: {2} || Help Text: {3}".format(field,field_data['nullable'],field_data['type'],field_data['help_text'])

#The fields id, created, and modified are automatically generated and we do not need to provide them.
#Given this, we only need to provide the non-blank field course_name
#However, since we want to link to our organization, let's also add that in.
course = {'course_name' : 'Test Course', 'organizations' : [organization_resource_uri]}
headers = {'content-type': 'application/json'}

#This will create our new course object using our name and organizations
response = session.post(API_BASE_URL + "/essay_site/api/v1/course/?format=json", data=json.dumps(course), headers=headers)
print "Created object: {0}".format(response.text)

#We can now query the API to find our created course
#We will see that id, created, and modified fields were automatically generated, along with a resource_uri
response = session.get(API_BASE_URL + "/essay_site/api/v1/course/?format=json")
response_text = json.loads(response.text)
course_object = response_text["objects"][0]
print course_object


########NEW FILE########
__FILENAME__ = create_user
"""
Example 2: In this example, we will create a user.
"""


from common_settings import *

#In order to create a user, we need to define a username and a password
data = {
    'username' : 'test',
    'password' : 'test',
    'email' : 'test@test.com'
}

#We need to explicitly define the content type to let the API know how to decode the data we are sending.
headers = {'content-type': 'application/json'}

#Now, let's try to get the schema for the create user model.
create_user_url = API_BASE_URL + "/essay_site/api/v1/createuser/"
response = requests.post(create_user_url, data=json.dumps(data),headers=headers)

#This should have a status code of 201, indicating that the user was created correctly.
#If you already have a user with username 'test', you will get a 400 error.
print("Status Code: {0}".format(response.status_code))
########NEW FILE########
__FILENAME__ = delete_objects
'''
This isn't used in the tutorial directly but you may find it handy to clean up
if the repository gets messy. 
'''

from common_settings import *
from pprint import *

session = requests.session()
response = login_to_discern(session)

#  Exploring the discern APIs?  Want to delete all objects? Here you go.

# problems
problem_response = session.get(API_BASE_URL + "/essay_site/api/v1/problem/?offset=0&limit=200&f?format=json", 
        headers=headers)

for p in json.loads(problem_response.text)['objects']:
	print (u"Problem problem: {0}, URI: {1} ".format(p['prompt'], p['resource_uri']))
	session.delete(API_BASE_URL + p['resource_uri'] + "?format=json")

# problem_response = session.delete(API_BASE_URL + "/essay_site/api/v1/problem/1/?format=json", 
#  	headers=headers)

# courses 
course_response = session.delete(API_BASE_URL + "/essay_site/api/v1/course/1/?format=json", 
 	headers=headers)


# organizations. 
org_response = session.delete(API_BASE_URL + "/essay_site/api/v1/organization/1/?format=json", 
	headers=headers)

########NEW FILE########
__FILENAME__ = enumerate_first_objects
'''
This is not used in the tutorial but you might find it handy to examine the
status of the Discern Server. 
'''

from common_settings import *
from pprint import *

session = requests.session()
response = login_to_discern(session)

#  enumerate first 20 objects.

problem_response = session.get(API_BASE_URL + "/essay_site/api/v1/problem/?offset=0&limit=20&f?format=json", 
 	headers=headers)

for p in json.loads(problem_response.text)['objects']:
	print (u"Problem problem: {0}, URI: {1} ".format(p['prompt'], p['resource_uri']))

course_response = session.get(API_BASE_URL + "/essay_site/api/v1/course/?offset=0&limit=20&f?format=json", 
 	headers=headers)

for c in json.loads(course_response.text)['objects']:
	print (u"Course name: {0}, URI: {1} ".format(c['course_name'], c['resource_uri']))

org_response = session.get(API_BASE_URL + "/essay_site/api/v1/organization/?offset=0&limit=20&f?format=json", 
 	headers=headers)

for org in json.loads(org_response.text)['objects']:
	print (u"Organization name: {0}, URI: {1} ".format(org['organization_name'], org['resource_uri']))


########NEW FILE########
__FILENAME__ = enumerate_schema
'''
Tutorial - Getting started - the API
Enumates the schema API for course. 
'''

from common_settings import *

session = requests.session()
response = login_to_discern(session)

#Now, let's get the schema for a course.
response = session.get(API_BASE_URL + "/essay_site/api/v1/course/schema/?format=json")
course_schema = json.loads(response.text)

#this will show us what data we need to provide for each field
for field in sorted(course_schema['fields'].keys()):
    field_data = course_schema['fields'][field]
    print "Name: {0} \n\t Can be blank: {1} \n\t Type: {2} \n\t Help Text: {3}\n".format(field,field_data['nullable'],field_data['type'],field_data['help_text'])


########NEW FILE########
__FILENAME__ = login
"""
Example 3: In this example, we will login with our created user.
"""

from common_settings import *

#We can use api key authentication or django session authentication.  In this case, we will login with the django session.

login_url = API_BASE_URL + "/essay_site/login/"

#These are the credentials that we created in the previous example.
data = {
    'username' : 'test',
    'password' : 'test'
}

#We need to explicitly define the content type to let the API know how to decode the data we are sending.
headers = {'content-type': 'application/json'}

#Now, let's try to login with our credentials.
response = requests.post(login_url, json.dumps(data),headers=headers)

# If the user with username test and password test has been created, this should return a 200 code.
print("Status Code: {0}".format(response.status_code))
#This should show us a json dictionary with "message" : "Logged in."
print("Response from server: {0}".format(response.text))
########NEW FILE########
__FILENAME__ = monitor_essay_processing
'''
Tutorial - This script inspects ease's progress grading essays. 
The assumption is that the populate_essays.py script has been run.
'''

from common_settings import *

# boilerplate login code
session = requests.session()
response = login_to_discern(session)

# Given a resource_uri for an essaygrade, pretty print the values.
def enumerate_grades(essaygrades_uri):
	response = session.get(API_BASE_URL + essaygrades_uri + "?format=json")
	grade = json.loads(response.text)
	print("\t confidence: {0}, score: {1}, type: {2} ".format(grade['confidence'], grade['target_scores'], grade['grader_type']))
	return None
	
response = session.get(API_BASE_URL + "/essay_site/api/v1/essay/?format=json")
essays  = json.loads(response.text)
for e in essays['objects']:
	print ("Scores for essay {0}, problem {1}".format(e['resource_uri'], e['problem']))
	for uri in e['essaygrades']:
		enumerate_grades(uri)

########NEW FILE########
__FILENAME__ = populate_essays
'''
Tutorial - Getting started - create a organization, course and problem objects
Here we create an institution(i.e., Reddit). 
'''

from common_settings import *
import praw # Python Reddit API Wrapper

# boilerplate login code
session = requests.session()
response = login_to_discern(session)

# add a problem statement. For the reddit example, we will use the title. 
def add_problem(the_prompt, the_class):
    problem_response = session.post(API_BASE_URL + "/essay_site/api/v1/problem/?format=json",
                                    data=json.dumps({"name": "movie question", "courses": [the_class],
                                                     "prompt": the_prompt, "max_target_scores": json.dumps([10000])}),
                                    headers=headers)
    if problem_response.status_code >= 400:
        print ("Problem creation failure.")
        print("status: {0} msg: {1}".format(
            problem_response.status_code,
            problem_response._content))
        print(vars(problem_response.request))
    problem_object = json.loads(problem_response.text)
    return problem_object['resource_uri']

# Add essay grade objects that are instructor scored and associate each one with an essay.
def add_score(the_essay_uri, the_score):
    score_response = session.post(API_BASE_URL + "/essay_site/api/v1/essaygrade/?format=json",
                                  data=json.dumps({
                                  "essay": the_essay_uri,
                                  "grader_type": "IN",
                                  "success": "true",
                                  "target_scores": json.dumps([the_score])
                                  }),
                                  headers=headers)

    if score_response.status_code >= 400:
        print ("Score creation failure.")
        print("status: {0} msg: {1}".format(
            score_response.status_code,
            score_response._content))
        print(vars(score_response.request))
    # GradeEssay doesn't have a resource_uri field
    return None

# Add an essay objects and associate them with the problem.
# returns resource_uri for the new essay object. 
def add_essay(the_text, the_problem_uri):
    essay_response = session.post(API_BASE_URL + "/essay_site/api/v1/essay/?format=json",
                                  data=json.dumps({
                                  "essay_type": "train",
                                  "essay_text": the_text,
                                  "problem": the_problem_uri,
                                  }), headers=headers)
    if essay_response.status_code >= 400:
        print ("essay creation failure.")
        print("status: {0} msg: {1}".format(
            essay_response.status_code,
            essay_response._content))
        print(vars(essay_response.request))
    essay_object = json.loads(essay_response.text)
    return essay_object['resource_uri']

# use the movie title as problem statement. 
r = praw.Reddit(user_agent='Discern Tutorial')
# get a movie from Reddit
submissions = r.get_subreddit('movies').get_hot(limit=1)
movie = submissions.next()

# TODO: update these two varibles with your results from running create_objects_for_tutorial.py
org_uri = '/essay_site/api/v1/organization/6/'
course_uri = '/essay_site/api/v1/course/28/'

problem_uri = add_problem(movie.title, course_uri)

comment_count = 0
for comment in movie.comments:
    if comment_count > 10:
        break
    essay_uri = add_essay(comment.body, problem_uri)
    add_score(essay_uri, comment.ups - comment.downs)
    comment_count += 1

########NEW FILE########
__FILENAME__ = query_organization
"""
Example 4: In this example, we will query our models after logging in and create our own model object.
"""

from common_settings import *

login_url = API_BASE_URL + "/essay_site/login/"

#These are the credentials that we created in the previous example.
data = {
    'username' : 'test',
    'password' : 'test'
}

#We need to explicitly define the content type to let the API know how to decode the data we are sending.
headers = {'content-type': 'application/json'}

#A session allows us to store cookies and other persistent information.
#In this case, it lets the server keep us logged in and make requests as a logged in user.
session = requests.session()
response = session.post(login_url, data=json.dumps(data),headers=headers)
print("Status Code: {0}".format(response.status_code))

#Now, let's try to get all the organization models that we have access to.
response = session.get(API_BASE_URL + "/essay_site/api/v1/organization/?format=json")

#This should get a 401 error if you are not logged in, and a 200 if you are.
print("Status Code: {0}".format(response.status_code))

#At this point, we will get a response from the server that lists all of the organization objects that we have created.
print("Response from server: {0}".format(response.text))

#We have yet to create any organization objects, so we will need to add some in before they can be properly displayed back to us.
#First, let's see what fields the organization model will accept.
response = session.get(API_BASE_URL + "/essay_site/api/v1/organization/schema/?format=json")
#At this point, we will get a response from the server that lists details of how to interact with the organization model
print("Response from server: {0}".format(response.text))

#We should see something like this.  It tells us that we can get, post, put, delete, or patch to organization.  It also tells us the fields that the organization model has.
"""
u'{"allowed_detail_http_methods": ["get", "post", "put", "delete", "patch"], "allowed_list_http_methods": ["get", "post", "put", "delete", "patch"], "default_format": "application/json", "default_limit": 20, "fields": {"courses": {"blank": false, "default": "No default provided.", "help_text": "Many related resources. Can be either a list of URIs or list of individually nested resource data.", "nullable": true, "readonly": false, "related_type": "to_many", "type": "related", "unique": false}, "created": {"blank": true, "default": true, "help_text": "A date & time as a string. Ex: \\"2010-11-10T03:07:43\\"", "nullable": false, "readonly": false, "type": "datetime", "unique": false}, "essays": {"blank": false, "default": "No default provided.", "help_text": "Many related resources. Can be either a list of URIs or list of individually nested resource data.", "nullable": true, "readonly": false, "related_type": "to_many", "type": "related", "unique": false}, "id": {"blank": true, "default": "", "help_text": "Integer data. Ex: 2673", "nullable": false, "readonly": false, "type": "integer", "unique": true}, "memberships": {"blank": false, "default": "No default provided.", "help_text": "Many related resources. Can be either a list of URIs or list of individually nested resource data.", "nullable": true, "readonly": false, "related_type": "to_many", "type": "related", "unique": false}, "modified": {"blank": true, "default": true, "help_text": "A date & time as a string. Ex: \\"2010-11-10T03:07:43\\"", "nullable": false, "readonly": false, "type": "datetime", "unique": false}, "organization_name": {"blank": false, "default": "", "help_text": "Unicode string data. Ex: \\"Hello World\\"", "nullable": false, "readonly": false, "type": "string", "unique": false}, "organization_size": {"blank": false, "default": 0, "help_text": "Integer data. Ex: 2673", "nullable": false, "readonly": false, "type": "integer", "unique": false}, "premium_service_subscriptions": {"blank": false, "default": "[]", "help_text": "Unicode string data. Ex: \\"Hello World\\"", "nullable": false, "readonly": false, "type": "string", "unique": false}, "resource_uri": {"blank": false, "default": "No default provided.", "help_text": "Unicode string data. Ex: \\"Hello World\\"", "nullable": false, "readonly": true, "type": "string", "unique": false}, "users": {"blank": false, "default": "No default provided.", "help_text": "Many related resources. Can be either a list of URIs or list of individually nested resource data.", "nullable": true, "readonly": false, "related_type": "to_many", "type": "related", "unique": false}}}'
"""

#Let's filter this a bit so that we only see available field and their type
#First, the response is a json-encoded string, so let's convert it to a python object
response_json = json.loads(response.text)

#This will display a list of fields and their type
#The related type joins models together.  A url to a specific model will need to be passed to this field (we will
#walk through this later).  For now, let's focus on the string fields.
for field in response_json['fields']:
    print("{0} : {1}".format(field, response_json['fields'][field]['type']))

#This is the data that will be used to construct our organization
data = {
    'organization_name' : "Test",
    'organization_size' : 1,
}

#Let's create our object by posting to the server!
response = session.post(API_BASE_URL + "/essay_site/api/v1/organization/?format=json", data=json.dumps(data), headers=headers)

#We can now see our created object, which has been returned from the server
print "Created object: {0}".format(response.text)

#As before, we can load all responses from the API using json
json_object = json.loads(response.text)

#We can see that some fields were automatically created.  The created and modified fields tell us when the model was made and created.
#Some related fields were also automatically populated.  These will be explained better when related fields are explained.




########NEW FILE########
__FILENAME__ = helpers
import rubric_functions
import json
import logging
from django.conf import settings
from slumber_models import SlumberModelDiscovery

log=logging.getLogger(__name__)

def get_rubric_data(model, slumber_data):
    """
    Get the rubric data for a given data file and attach it.
    model - a model type, currently "problem" or "essay"
    slumber_data - a dict returned by slumber from the api
    """
    #Extract the problem id
    if model=="problem":
        problem_id = slumber_data['id']
    else:
        problem_id = slumber_data['problem'].split('/')[5]

    #Try to get the local rubric data matching the problem id
    rubric_data = []
    try:
        rubric_data = rubric_functions.get_rubric_data(problem_id)
    except:
        log.error("Could not find rubric for problem id {0}.".format(problem_id))

    return rubric_data

def construct_related_uri(id, model_type):
    """
    Given an integer id, construct a related model uri
    id - a string or integer model id
    model_type - the type of model to post (ie 'organization')
    """
    return "/{api_url}{model_type}/{id}/".format(api_url=settings.API_URL_INTERMEDIATE, model_type=model_type, id=id)

def get_essaygrade_data(slumber_data, essaygrades):
    """
    For a given essay, extract the rubric and essay grades
    slumber_data - the dict for the essay model retrieved by slumber from the api
    essaygrades - a list of all the essaygrade objects for the user
    """
    #Get the problem id from the essay
    problem_id = slumber_data['problem'].split('/')[5]
    essaygrade_data = []
    #Loop through all of the essaygrades attached to the essay
    for z in xrange(0,len(slumber_data['essaygrades'])):
        #Get the id of the essaygrade
        essaygrade_id = slumber_data['essaygrades'][z].split('/')[5]
        #Loop through the list of all the users's essaygrades to find a match
        for i in xrange(0,len(essaygrades)):
            #If there is a match, get the scored rubric data
            if int(essaygrade_id) == int(essaygrades[i]['id']):
                #Try to extract and parse the target scores
                target_scores = essaygrades[i]['target_scores']
                try:
                    target_scores = json.loads(target_scores)
                except:
                    pass
                #Retrieve the local rubric, and match with the target scores.
                rubric_data = rubric_functions.get_rubric_data(problem_id, target_scores)
                #Add the rubric data to the essaygrade
                essaygrades[i]['rubric'] = rubric_data
                essaygrade_data.append(essaygrades[i])
    return essaygrade_data

def setup_slumber_models(user, model_types=None):
    """
    Sets up the slumber API models for a given user.  See slumber_models for a description of slumber
    user - a django user object
    model_types - if you only want to setup certain types of models, pass them in
    """
    #Get the api authentication dictionary for the user
    api_auth = user.profile.get_api_auth()
    #Instantiate the slumber model discovery class for the api endpoint specified in settings
    slumber_discovery = SlumberModelDiscovery(settings.FULL_API_START, api_auth)
    #Generate all the models
    models = slumber_discovery.generate_models(model_types)
    return models
########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Rubric'
        db.create_table(u'grader_rubric', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('associated_problem', self.gf('django.db.models.fields.IntegerField')()),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal(u'grader', ['Rubric'])

        # Adding model 'RubricOption'
        db.create_table(u'grader_rubricoption', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('rubric', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grader.Rubric'])),
            ('option_points', self.gf('django.db.models.fields.IntegerField')()),
            ('option_text', self.gf('django.db.models.fields.TextField')()),
            ('selected', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'grader', ['RubricOption'])

        # Adding model 'UserProfile'
        db.create_table(u'grader_userprofile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True)),
            ('api_key', self.gf('django.db.models.fields.TextField')(default='')),
            ('api_user', self.gf('django.db.models.fields.TextField')(default='')),
            ('api_user_created', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'grader', ['UserProfile'])


    def backwards(self, orm):
        # Deleting model 'Rubric'
        db.delete_table(u'grader_rubric')

        # Deleting model 'RubricOption'
        db.delete_table(u'grader_rubricoption')

        # Deleting model 'UserProfile'
        db.delete_table(u'grader_userprofile')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'grader.rubric': {
            'Meta': {'object_name': 'Rubric'},
            'associated_problem': ('django.db.models.fields.IntegerField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'grader.rubricoption': {
            'Meta': {'object_name': 'RubricOption'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'option_points': ('django.db.models.fields.IntegerField', [], {}),
            'option_text': ('django.db.models.fields.TextField', [], {}),
            'rubric': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['grader.Rubric']"}),
            'selected': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'grader.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'api_key': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'api_user': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'api_user_created': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['grader']
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.auth.models import User
from django.forms.models import model_to_dict
from django.db.models.signals import post_save, pre_save
import random
import string
from django.conf import settings
import requests
import json
import logging

log= logging.getLogger(__name__)

class Rubric(models.Model):
    """
    The rubric object is a way to locally store data about rubric options.
    Each rubric is associated with a problem object stored on the API side.
    """

    #Each rubric is specific to a problem and a user.
    associated_problem = models.IntegerField()
    user = models.ForeignKey(User)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def get_scores(self):
        """
        Calculate the final score for a given rubric.
        """
        scores = []
        all_scores = []
        final_score=0
        max_score = 0
        options = self.get_rubric_dict()
        for option in options:
            #Add to all_scores for each of the scores
            all_scores.append(option['option_points'])
            #If the student was marked as correct for a given option, add it to the score
            if option['selected']:
                scores.append(option['option_points'])

        if len(scores)>0:
            final_score = sum(scores)

        if len(all_scores)>0:
            max_score = sum(all_scores)

        return {
            'score' : final_score,
            'max_score' : max_score
        }

    def get_rubric_dict(self):
        """
        Get the rubric in dictionary form.
        """
        options = []
        #Bundle up all of the rubric options
        option_set = self.rubricoption_set.all().order_by('id')
        for option in option_set:
            options.append(model_to_dict(option))
        return options

class RubricOption(models.Model):
    """
    Each rubric has multiple options
    """
    #Associate options with rubrics
    rubric = models.ForeignKey(Rubric)
    #Number of points the rubric option is worth
    option_points = models.IntegerField()
    #Text to show to users for this option
    option_text = models.TextField()
    #Whether or not this option is selected (ie marked correct)
    selected = models.BooleanField(default=False)

class UserProfile(models.Model):
    """
    Every user has a profile.  Used to store additional fields.
    """
    user = models.OneToOneField(User)
    #Api key
    api_key = models.TextField(default="")
    #Api username
    api_user = models.TextField(default="")
    #whether or not an api user has been created
    api_user_created = models.BooleanField(default=False)

    def get_api_auth(self):
        """
        Returns the api authentication dictionary for the given user
        """
        return {
            'username' : self.api_user,
            'api_key' : self.api_key
        }


def create_user_profile(sender, instance, created, **kwargs):
    """
    Creates a user profile based on a signal from User when it is created
    """
    #Create a userprofile if the user has just been created, don't if not.
    if created:
        profile, created = UserProfile.objects.get_or_create(user=instance)
    else:
        return

    #If a userprofile was not created (gotten instead), then don't make an api user
    if not created:
        return

    #Create a random password for the api user
    random_pass = ''.join([random.choice(string.digits + string.letters) for i in range(0, 15)])

    #Data we will post to the api to make a user
    data = {
        'username' : instance.username,
        'password' : random_pass,
        'email' : instance.email
        }

    headers = {'content-type': 'application/json'}

    #Now, let's try to get the schema for the create user model.
    create_user_url = settings.FULL_API_START + "createuser/"
    counter = 0
    status_code = 400

    #Try to create the user at the api
    while status_code==400 and counter<2 and not instance.profile.api_user_created:
        try:
            #Post our information to try to create a user
            response = requests.post(create_user_url, data=json.dumps(data),headers=headers)
            status_code = response.status_code
            #If a user has been created, store the api key locally
            if status_code==201:
                instance.profile.api_user_created = True
                response_data = json.loads(response.content)
                instance.profile.api_key = response_data['api_key']
                instance.profile.api_user = data['username']
                instance.profile.save()
        except:
            log.exception("Could not create an API user!")
            instance.profile.save()
        counter+=1
        #If we could not create a user in the first pass through the loop, add to the username to try to make it unique
        data['username'] += random.choice(string.digits + string.letters)

post_save.connect(create_user_profile, sender=User)

#Maps the get_profile() function of a user to an attribute profile
User.profile = property(lambda u: u.get_profile())

########NEW FILE########
__FILENAME__ = rubric_functions
from models import Rubric, RubricOption
import logging

log = logging.getLogger(__name__)

def get_rubric_data(problem_id, target_scores = None):
    """
    Retrieve the local rubric that is associated with a given api problem
    problem_id - the id of the problem object that the rubric is associated with
    target_scores - if we have recieved scores for the problem, pass them in
    """
    #Retrieve the local rubric object
    rubric = Rubric.objects.filter(associated_problem=int(problem_id))
    rubric_dict = []
    if rubric.count()>=1:
        rubric = rubric[0]
        #Get the dictionary representation of the rubric
        rubric_dict = rubric.get_rubric_dict()
    if target_scores is not None:
        #If we have recieved target scores, mark the given rubric options as selected (score of 1 means select, 0 means not selected)
        for i in xrange(0,len(rubric_dict)):
            if target_scores[i]==1:
                rubric_dict[i]['selected'] = True
    return rubric_dict

def create_rubric_objects(rubric_data, request):
    """
    For a given user and problem id, create a local rubric object
    rubric_data - the dictionary data associated with the rubric
    request - the request that the user has made
    """
    #Create the rubric
    rubric = Rubric(associated_problem = int(rubric_data['problem_id']), user = request.user)
    rubric.save()
    #Create each rubric option
    for option in rubric_data['options']:
        option = RubricOption(rubric=rubric, option_points =option['points'], option_text = option['text'])
        option.save()

def delete_rubric_data(problem_id):
    """
    When a problem is deleted, delete its local rubric object
    problem_id - int or string problem id
    """
    Rubric.objects.filter(associated_problem=int(problem_id)).delete()

########NEW FILE########
__FILENAME__ = slumber_models
import slumber
import logging
import requests
import json
import os

log = logging.getLogger(__name__)

def join_without_slash(path1, path2):
    """
    Join two paths and ensure that only one slash is used at the join point
    path1 - string path(ie '/base/')
    path2 -string path (ie '/home/')
    """
    if path1.endswith("/"):
        path1 = path1[0:-1]
    if not path2.startswith("/"):
        path2 = "/" + path2

    return path1 + path2

class InvalidValueException(Exception):
    """
    Exception for an invalid value
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class SlumberModel(object):
    """
    Wraps an API model, and provides abstractions for get/post/update/delete.  Used to simplify talking with the api.
    See https://github.com/KayEss/django-slumber for more details on slumber.
    """
    #These are not required fields, so don't advertise them as such
    excluded_fields = ['created', 'id', 'resource_uri', 'id', 'modified']
    def __init__(self,api_url, model_type, api_auth):
        """
        api_url - the base url for the api (settings.FULL_API_START)
        model_type - the type of model to encapsulate (ie 'organization')
        api_auth - the api auth dict for a given user (see UserProfile.get_api_auth)
        """
        self.api = slumber.API(api_url)
        self.api_url = api_url
        self.model_type = model_type
        self.api_auth = api_auth
        self.objects=[]

    def get_base_model(self, id = None):
        """
        Gets the start of the slumber model path for an api resource
        """
        #In slumber, the base slumber.API has attributes for each model at the endpoint
        ref = getattr(self.api,self.model_type)
        if id is not None:
            #If we are referencing a specific model id, add it into the base
            ref = ref(id)
        return ref

    def get(self, id = None, data = None, **kwargs):
        """
        Get an object or list of objects from the api
        id - int
        data - Not used
        """
        #Create the arguments to send to the api
        new_arguments = self.api_auth.copy()
        #limit=0 disables pagination
        new_arguments['limit'] = 0

        if id is not None:
            #Get a single object
            self.objects = self.get_base_model(id).get(**new_arguments)
            return self.objects
        else:
            #Get a list of objects
            return self.get_base_model().get(**new_arguments).get('objects', None)

    @property
    def schema(self):
        """
        The schema for the model.
        """
        schema = self.get_base_model().schema.get(**self.api_auth).get('fields', None)
        return schema

    @property
    def required_fields(self):
        """
        Required fields for the model.  These are needed to post to the api.
        """
        schema = self.schema
        required_fields = []
        for field in schema:
            if (not schema[field]['nullable'] or schema[field]['blank']) and field not in self.excluded_fields:
                required_fields.append(field)
        return required_fields

    def post(self, id = None, data = None, **kwargs):
        """
        Posts a new instance to the api
        id - Not used
        data - the data to post
        """
        #Check to see if all required fields are being filled in
        for field in self.required_fields:
            if field not in data:
               error_message = "Key {0} not present in post data, but is required.".format(field)
               log.info(error_message)
               raise InvalidValueException(error_message)
        #Add in the data to post
        new_arguments = self.api_auth.copy()
        new_arguments['data'] = data

        new = self.get_base_model().post(**new_arguments)
        #Add the object to the internal objects dict
        self.objects.append(new)
        return new

    def find_model_by_id(self,id):
        """
        Find a model given its id
        id - int
        """
        match = None
        for i in xrange(0,len(self.objects)):
            loop_obj = self.objects[i]
            if int(loop_obj['id']) == id:
                match = i
                break
        return match

    def delete(self,id = None, data = None, **kwargs):
        """
        Delete a given instance of a model
        id - int, instance to delete
        data - not used
        """
        #Delete the instance
        response = self.get_base_model(id=id).delete(**self.api_auth)

        #Find a match and remove the model from the internal list
        match = self.find_model_by_id(id)
        if match is not None:
            self.objects.pop(match)
        return response

    def update(self, id = None, data = None, **kwargs):
        """
        Update a given instance of a model
        id - int, instance to update
        data - data to update with
        """
        #Refresh the internal model list
        self.get()
        #Add the data to be posted
        new_arguments = self.api_auth.copy()
        new_arguments['data'] = data
        #Update
        response = self.get_base_model(id=id).update(**new_arguments)
        #Update in internal list
        match = self.find_model_by_id(id)
        self.objects[match] = response
        return response

    def action(self, action, id=None, data = None):
        """
        Perform a given action
        action - see the keys in action_dict for the values this can take
        id - integer id if needed for the action
        data - dict data if needed for the action
        """

        #Define the actions that are possible, and map them to functions
        action_dict = {
            'get' : self.get,
            'post' : self.post,
            'update' : self.update,
            'delete' : self.delete,
        }
        #Check to see if action is possible
        if action not in action_dict:
            error = "Could not find action {0} in registered actions.".format(action)
            log.info(error)
            raise InvalidValueException(error)

        #Check to see if id is provided for update and delete
        if action in ['update', 'delete'] and id is None:
            error = "Need to provide an id along with action {0}.".format(action)
            log.info(error)
            raise InvalidValueException(error)

        #check to see if data is provided for update and post
        if action in ['update', 'post'] and data is None:
            error = "Need to provide data along with action {0}.".format(action)
            log.info(error)
            raise InvalidValueException(error)

        #Perform the action
        result = action_dict[action](data=data, id=id)
        return result

class SlumberModelDiscovery(object):
    """
    A class the auto-discovers slumber models by checking the api
    """
    def __init__(self,api_url, api_auth):
        """
        api_url - the base url for the api.  See settings.FULL_API_START.
        api_auth - api auth dict.  See UserProfile.get_api_auth
        """
        self.api_url = api_url
        self.api_auth = api_auth
        #Append format=json to avoid error
        self.schema_url = join_without_slash(self.api_url, "?format=json")

    def get_schema(self):
        """
        Get and load the api schema
        """
        schema = requests.get(self.schema_url, params=self.api_auth)
        return json.loads(schema.content)

    def generate_models(self, model_names = None):
        """
        Using the schema, generate slumber models for each of the api models
        model_names - optional list of slumber models to generate
        """
        schema = self.get_schema()
        slumber_models = {}
        for field in schema:
            if model_names is not None and field not in model_names:
                continue
            field_model = SlumberModel(self.api_url, field, self.api_auth)
            slumber_models[field] = field_model
        return slumber_models




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
__FILENAME__ = urls
from django.conf.urls import *

urlpatterns=patterns('django.contrib.auth.views',
                     url(r'^login/$','login'),
                     url(r'^logout/$','logout'),
                     )

urlpatterns +=patterns('grader.views',
                       url(r'^register/$','register'),
                       url(r'^$','index'),
                       url(r'^course/$','course'),
                       url(r'^action/$','action'),
                       url(r'^problem/$','problem'),
                       url(r'^write_essays/$','write_essays'),
                       url(r'^grade_essays/$','grade_essays'),
                       )

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import ugettext, ugettext_lazy as _
from django.forms import EmailField
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
import logging
import json
import rubric_functions
import helpers

log = logging.getLogger(__name__)

class UserCreationEmailForm(UserCreationForm):
    email = EmailField(label=_("Email Address"), max_length=30,
                                help_text=_("Required. 30 characters or fewer. Letters, digits and "
                                            "@/./+/-/_ only."),
                                error_messages={
                                    'invalid': _("This value may contain only letters, numbers and "
                                                 "@/./+/-/_ characters.")})
    def save(self, commit=True):
        user = super(UserCreationEmailForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


def register(request):
    """
    Register a new user for a given request
    """
    if request.method == 'POST':
        form = UserCreationEmailForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect("/grader/")
    else:
        form = UserCreationEmailForm()
    return render_to_response("registration/register.html", RequestContext(request,{
        'form': form,
        }))

def index(request):
    """
    Index page for the site.
    """
    return render_to_response("index.html",RequestContext(request))

#Available types of actions
action_types = ["update", "delete", "get", "post"]

@login_required
def action(request):
    """
    Main handler function for actions.  Needs to be broken up down the line.
    """

    #Support get or post requests
    if request.method == 'POST':
        args = request.POST
    else:
        args = request.GET

    #Action is the type of action to do (see action_types above)
    action = args.get('action', 'get')
    #Model is the model to perform the given action on(ie 'organization')
    model = args.get('model', None)
    #If the action is on a per-instance level (ie delete and update), then get the id to perform the action on.
    id = args.get('id', None)

    #Grab the user
    user = request.user
    #Data is used when posting and updating
    data = args.get('data', None)

    #Data might be in json format, but it might not.  support both
    try:
        data = json.loads(data)
    except:
        pass

    #Check to see if the action is valid.
    if action is None or action not in action_types:
        error = "Action cannot be None, and must be a string in action_types: {0}".format(action_types)
        log.info(error)
        raise TypeError(error)

    #Define a base rubric
    rubric = {'options' : []}
    #If we are posting a problem, then there is additional processing to do before we can submit to the API
    if action=="post" and model=="problem":
        #Grab the rubric for later.
        rubric = data['rubric'].copy()
        #Add in two needed fields (the api requires them)
        data.update({
            'max_target_scores' : [1 for i in xrange(0,len(data['rubric']['options']))],
            'courses' : [helpers.construct_related_uri(data['course'], 'course')]
        })
        #Remove these keys (posting to the api will fail if they are still in)
        del data['rubric']
        del data['course']

    #We need to convert the integer id into a resource uri before posting to the API
    if action=="post" and model=="essay":
        data['problem'] = helpers.construct_related_uri(data['problem'], 'problem')

    #We need to convert the integer id into a resource uri before posting to the API
    if action=="post" and model=="essaygrade":
        data['essay'] = helpers.construct_related_uri(data['essay'], 'essay')

    #If we are deleting a problem, delete its local model uri
    if action=="delete" and model=="problem":
        rubric_functions.delete_rubric_data(id)

    #Setup all slumber models for the current user
    slumber_models = helpers.setup_slumber_models(user)

    #Check to see if the user requested model exists at the API endpoint
    if model not in slumber_models:
        error = "Invalid model specified :{0} .  Model does not appear to exist in list: {1}".format(model, slumber_models.keys())
        log.info(error)
        raise Exception(error)

    try:
        #Try to see if we can perform the given action on the given model
        slumber_data = slumber_models[model].action(action,id=id,data=data)
    except Exception as inst:
        #If we cannot, log the error information from slumber.  Will likely contain the error message recieved from the api
        error_message = "Could not perform action {action} on model type {model} with id {id} and data {data}.".format(action=action, model=model, id=id, data=data)
        error_information = "Recieved the following from the server.  Args: {args} , response: {response}, content: {content}".format(args=inst.args, response=inst.response, content=inst.content)
        log.error(error_message)
        log.error(error_information)
        raise

    #If we have posted a problem, we need to create a local rubric object to store our rubric (the api does not do this)
    if action=="post" and model=="problem":
        problem_id = slumber_data['id']
        rubric['problem_id'] = problem_id
        #Create the rubric object
        rubric_functions.create_rubric_objects(rubric, request)

    #Append rubric to problem and essay objects
    if (action in ["get", "post"] and model=="problem") or (action=="get" and model=="essay"):
        if isinstance(slumber_data,list):
            for i in xrange(0,len(slumber_data)):
                    slumber_data[i]['rubric'] = helpers.get_rubric_data(model, slumber_data[i])
        else:
            slumber_data['rubric'] = helpers.get_rubric_data(model, slumber_data)

    #append essaygrades to essay objects
    if action=="get" and model=="essay":
        essaygrades = slumber_models['essaygrade'].action('get')
        if isinstance(slumber_data,list):
            for i in xrange(0,len(slumber_data)):
                slumber_data[i]['essaygrades_full'] = helpers.get_essaygrade_data(slumber_data[i], essaygrades)
        else:
            slumber_data['essaygrades_full'] = helpers.get_essaygrade_data(slumber_data, essaygrades)

    json_data = json.dumps(slumber_data)
    return HttpResponse(json_data)

@login_required
def course(request):
    """
    Render the page for courses
    """
    return render_to_response('course.html', RequestContext(request, {'model' : 'course', 'api_url' : "/grader/action"}))

@login_required
def problem(request):
    """
    Render the page for problems.  This can take the argument course_id.
    """

    #Accept either get or post requests
    if request.method == 'POST':
        args = request.POST
    else:
        args = request.GET

    #If provided, get the course id argument
    matching_course_id = args.get('course_id', -1)
    match_course = False
    course_name = None

    #If a course to match problems to has been specified, grab the matching course and return it
    if matching_course_id!= -1:
        match_course = True
        user = request.user
        slumber_models = helpers.setup_slumber_models(user)
        course_object = slumber_models['course'].action('get',id=matching_course_id, data=None)
        course_name = course_object['course_name']

    matching_course_id = str(matching_course_id)


    return render_to_response('problem.html', RequestContext(request, {'model' : 'problem',
                                                                       'api_url' : "/grader/action",
                                                                       'matching_course_id' : matching_course_id,
                                                                       'match_course' : match_course,
                                                                       'course_name' : course_name,
    })
    )

@login_required
def write_essays(request):
    """
    Render the page for writing essays
    """
    return render_to_response('write_essay.html', RequestContext(request, {'api_url' : "/grader/action", 'model' : 'essay',}))

@login_required
def grade_essays(request):
    """
    Render the page for grading essays
    """
    return render_to_response('grade_essay.html', RequestContext(request, {'api_url' : "/grader/action", 'model' : 'essaygrade',}))



########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "problem_grader.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
import sys
import os
from path import path

# Django settings for problem_grader project.

ROOT_PATH = path(__file__).dirname()
REPO_PATH = ROOT_PATH.dirname()
ENV_ROOT = REPO_PATH.dirname()

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

LOGIN_REDIRECT_URL = '/grader'

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'db/grader.db',                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': '',
        'PASSWORD': '',
        'HOST': '',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                      # Set to empty string for default.
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'problem-grader'
    }
}

#Avoid clashes with api by changing these
SESSION_COOKIE_NAME = "problemgradersessionid"
CSRF_COOKIE_NAME = "problemgradercsrftoken"

#Figure out where the API is!
API_URL_BASE = "http://127.0.0.1:7999/"
API_URL_INTERMEDIATE = "essay_site/api/v1/"
FULL_API_START = API_URL_BASE + API_URL_INTERMEDIATE


# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
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
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

STATIC_ROOT = os.path.abspath(REPO_PATH / "staticfiles")

#Make the static root dir if it does not exist
if not os.path.isdir(STATIC_ROOT):
    os.mkdir(STATIC_ROOT)

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.abspath(REPO_PATH / 'css_js_src/'),
)

STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

PIPELINE_JS = {
    'util' : {
        'source_filenames': [
            'js/jquery-1.9.1.js',
            'js/json2.js',
            'js/bootstrap.js',
            'js/jquery.cookie.js',
            'js/underscore.js',
            ],
        'output_filename': 'js/util.js',
        },
    'course' : {
        'source_filenames': [
            'js/course.js',
        ],
        'output_filename': 'js/course.js',
    },
    'problem' : {
        'source_filenames': [
            'js/problem.js',
            ],
        'output_filename': 'js/problem.js',
    },
    'essay' : {
    'source_filenames': [
        'js/essay.js',
        'js/essay_nav.js'
        ],
    'output_filename': 'js/essay.js',
    },
    'essaygrade' : {
        'source_filenames': [
            'js/essaygrade.js',
            'js/essay_nav.js',
            ],
        'output_filename': 'js/essaygrade.js',
        },
}

PIPELINE_CSS = {
    'bootstrap': {
        'source_filenames': [
            'css/bootstrap.css',
            'css/bootstrap-responsive.css',
            'css/bootstrap-extensions.css',
            ],
        'output_filename': 'css/bootstrap.css',
        },
    'util_css' : {
        'source_filenames': [
            'css/jquery-ui-1.10.2.custom.css',
            ],
        'output_filename': 'css/util_css.css',
        }
}


PIPELINE_DISABLE_WRAPPER = True
PIPELINE_YUI_BINARY = "yui-compressor"

PIPELINE_CSS_COMPRESSOR = None
PIPELINE_JS_COMPRESSOR = None

PIPELINE_COMPILE_INPLACE = True
PIPELINE = True


# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'p*51#*%wyw^y3a@%s*ak+xb$o4sfsr#xkj@d-n^ammtelysp@@'

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

ROOT_URLCONF = 'problem_grader.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'problem_grader.wsgi.application'

AUTH_PROFILE_MODULE = 'grader.UserProfile'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.abspath(REPO_PATH / "templates"),
    os.path.abspath(REPO_PATH / "grader")
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'grader',
    'south',
    'pipeline',
)

syslog_format = ("[%(name)s][env:{logging_env}] %(levelname)s "
                 "[{hostname}  %(process)d] [%(filename)s:%(lineno)d] "
                 "- %(message)s").format(
    logging_env="", hostname="")

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s %(levelname)s %(process)d '
                      '[%(name)s] %(filename)s:%(lineno)d - %(message)s',
            },
        'syslog_format': {'format': syslog_format},
        'raw': {'format': '%(message)s'},
        },
    'handlers': {
        'console': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'stream': sys.stdout,
            },
        'null': {
            'level': 'DEBUG',
            'class':'django.utils.log.NullHandler',
            },
        },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
            },
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False
        },
        'django.db.backends': {
            'handlers': ['null'],  # Quiet by default!
            'propagate': False,
            'level':'DEBUG',
            },
        }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
                       url(r'^grader/', include('grader.urls')),
                       url(r'^$', include('grader.urls')),
                       )

if settings.DEBUG:
    #urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT, show_indexes=True)
    urlpatterns+= patterns('',
                           url(r'^static/(?P<path>.*)$', 'django.views.static.serve', {
                               'document_root': settings.STATIC_ROOT,
                               'show_indexes' : True,
                               }),
                           )

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for problem_grader project.

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

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "problem_grader.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "problem_grader.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = fabfile
"""
This fabfile currently works to deploy this repo and ease to a new server.
A lot of settings and names will need to be changed around for your specific config, so
look through carefully.
"""

from __future__ import with_statement
import sys
import os
import logging

from fabric.api import local, lcd, run, env, cd, settings, prefix, sudo, shell_env, task
from fabric.contrib.console import confirm
from fabric.operations import put
from fabric.contrib.files import exists
from fabric.contrib import django
from path import path

#Overall usage is fab sandbox deploy or fab vagrant deploy.
#Add in your own task instead of sandbox or vagrant to specify your own settings.

# Deploy to Vagrant with:
# fab  -i /Users/nateaune/.rvm/gems/ruby-1.9.3-p374/gems/vagrant-1.0.7/keys/vagrant deploy

# Usage:
# MacOSX: 
# fab -i /Applications/Vagrant/embedded/gems/gems/vagrant-1.0.3/keys/vagrant deploy
# On Nate's Mac using Homebrew:
# fab  -i /Users/nateaune/.rvm/gems/ruby-1.9.3-p374/gems/vagrant-1.0.7/keys/vagrant deploy         
# Debian/Ubuntu: 
# fab -i /opt/vagrant/embedded/gems/gems/vagrant-1.0.3/keys/vagrant deploy

#Define this path so that we can import the django settings
ROOT_PATH = path(__file__).dirname()
ENV_ROOT = ROOT_PATH.dirname()
sys.path.append(ROOT_PATH)
sys.path.append(ENV_ROOT)

#Disable annoyting log messages.
logging.basicConfig(level=logging.ERROR)

# Environment settings
env.forward_agent = True

#This makes the paramiko logger less verbose
para_log=logging.getLogger('paramiko.transport')
para_log.setLevel(logging.ERROR)

#Use the below setting to pick the remote host that you want to deploy to.

@task
def vagrant(debug=True):
    env.environment = 'vagrant'
    env.hosts = ['vagrant@33.33.33.10', ]
    env.branch = 'dev'
    env.remote_user = 'vagrant'
    env.debug = debug


@task
def sandbox():
    env.environment = 'sandbox'
    env.hosts = ['vik@sandbox-service-api-001.m.edx.org', ]
    env.branch = 'master'
    env.remote_user = 'vik'

@task
def prepare_deployment():
    """
    Make a commit and push it to github
    """
    #Make a local commit with latest changes if needed.
    local('git add -p && git commit')
    local("git push")

@task
def check_paths():
    """
    Ensure that the paths are correct.
    """
    log = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)
    log.info(ROOT_PATH)
    log.info(ENV_ROOT)

@task
def deploy():
    """
    Deploy to a server.
    """

    #Setup needed directory paths
    #May need to edit if you are using this for deployment
    up_one_level_dir = '/opt/wwc'
    code_dir = os.path.join(up_one_level_dir, "discern")
    ml_code_dir = os.path.join(up_one_level_dir, 'ease')
    database_dir = os.path.join(code_dir, "db")
    nltk_data_dir = '/usr/share/nltk_data'
    static_dir = os.path.join(code_dir, 'staticfiles')
    deployment_config_dir = os.path.join(ROOT_PATH, "deployment/configuration/")
    discern_repo_url = 'git@github.com:edx/discern.git'
    ease_repo_url = 'git@github.com:edx/ease.git'

    #this is needed for redis-server to function properly
    sudo('sysctl vm.overcommit_memory=1')

    with settings(warn_only=True):
        #Stop services
        sudo('service celery stop')
        sudo('service discern stop')
        static_dir_exists = exists(static_dir, use_sudo=True)
        if not static_dir_exists:
            sudo('mkdir -p {0}'.format(static_dir))
        repo_exists = exists(code_dir, use_sudo=True)
        #If the repo does not exist, then it needs to be cloned
        if not repo_exists:
            sudo('apt-get install git python')
            up_one_level_exists = exists(up_one_level_dir, use_sudo=True)
            if not up_one_level_exists:
                sudo('mkdir -p {0}'.format(up_one_level_dir))
            with cd(up_one_level_dir):
                #TODO: Insert repo name here
                run('git clone {0}'.format(discern_repo_url))

        sudo('chmod -R g+w {0}'.format(code_dir))

        #Check for the existence of the machine learning repo
        ml_repo_exists = exists(ml_code_dir, use_sudo=True)
        if not ml_repo_exists:
            with cd(up_one_level_dir):
                run('git clone {0}'.format(ease_repo_url))

        db_exists = exists(database_dir, use_sudo=True)
        if not db_exists:
            sudo('mkdir -p {0}'.format(database_dir))

        # TODO: should not be hardcoded to vik. For now, change to vagrant
        sudo('chown -R {0} {1}'.format(env.remote_user, up_one_level_dir))
        sudo('chmod -R g+w {0}'.format(ml_code_dir))

    with cd(ml_code_dir), settings(warn_only=True):
        #Update the ml repo
        run('git pull')

    with cd(code_dir), settings(warn_only=True):
        # With git...
        run('git pull')
        #Ensure that files are fixed
        run('sudo apt-get update')
        #This fixes an intermittent issue with compiling numpy
        run('sudo apt-get upgrade gcc')
        sudo('xargs -a apt-packages.txt apt-get install')
        #Activate your virtualenv for python
        result = run('source /opt/edx/bin/activate')
        if result.failed:
            #If you cannot activate the virtualenv, one does not exist, so make it
            sudo('apt-get install python-pip')
            sudo('pip install virtualenv')
            sudo('mkdir -p /opt/edx')
            sudo('virtualenv "/opt/edx"')
            sudo('chown -R {0} /opt/edx'.format(env.remote_user))

    with prefix('source /opt/edx/bin/activate'), settings(warn_only=True):
        with cd(code_dir):
            #Numpy and scipy are a bit special in terms of how they install, so we need pre-requirements.
            run('pip install -r pre-requirements.txt')
            run('pip install -r requirements.txt')
            # Sync django db and migrate it using south migrations
            run('python manage.py syncdb --noinput --settings=discern.aws --pythonpath={0}'.format(code_dir))
            run('python manage.py migrate --settings=discern.aws --pythonpath={0}'.format(code_dir))
            # TODO: check to see if there is a superuser already, and don't try to create it again
            #Comment this line out to avoid prompts when deploying
            #run('python manage.py createsuperuser --settings=discern.aws --pythonpath={0}'.format(code_dir))

            run('python manage.py collectstatic -c --noinput --settings=discern.aws --pythonpath={0}'.format(code_dir))
            run('python manage.py update_index --settings=discern.aws --pythonpath={0}'.format(code_dir))
            sudo('chown -R www-data {0}'.format(up_one_level_dir))

        with cd(ml_code_dir):
            sudo('xargs -a apt-packages.txt apt-get install')
            run('pip install -r pre-requirements.txt')
            run('pip install -r requirements.txt')

            #This is needed to support the ml algorithm
            sudo('mkdir -p {0}'.format(nltk_data_dir))
            if not exists(nltk_data_dir):
                sudo('python -m nltk.downloader -d {0} all'.format(nltk_data_dir))
                sudo('chown -R {0} {1}'.format(env.remote_user, nltk_data_dir))
            run('python setup.py install')

    with lcd(deployment_config_dir), settings(warn_only=True):
        sudo('mkdir -p /etc/nginx/sites-available')
        with cd(up_one_level_dir):
            #Move env and auth.json (read by aws.py if using it instead of settings)
            put('service-auth.json', 'auth.json', use_sudo=True)
            put('service-env.json', 'env.json', use_sudo=True)
        with cd('/etc/init'):
            #Upstart tasks that start and stop the needed services
            put('service-celery.conf', 'celery.conf', use_sudo=True)
            put('service-discern.conf', 'discern.conf', use_sudo=True)
        with cd('/etc/nginx/sites-available'):
            #Modify nginx settings to pass through discern
            put('service-nginx', 'default', use_sudo=True)

    with settings(warn_only=True):
        #Start all services back up
        sudo('service celery start')
        sudo('service discern start')
        sudo('service nginx restart')
########NEW FILE########
__FILENAME__ = api
import logging

from django.contrib.auth.models import User
from django.conf.urls import url
from django.conf import settings
from django.core.paginator import Paginator, InvalidPage
from django.db import IntegrityError
from django.http import Http404

from tastypie.resources import ModelResource
from tastypie.authorization import Authorization
from tastypie.authentication import Authentication, ApiKeyAuthentication, MultiAuthentication

from tastypie import fields
from tastypie.utils import trailing_slash
from tastypie.serializers import Serializer
from tastypie.exceptions import BadRequest
from tastypie_validators import CustomFormValidation

from guardian_auth import GuardianAuthorization
from haystack.query import SearchQuerySet

from freeform_data.models import Organization, UserProfile, Course, Problem, Essay, EssayGrade, Membership, UserRoles

from collections import Iterator
from throttle import UserAccessThrottle
from forms import ProblemForm, EssayForm, EssayGradeForm, UserForm

from django.forms.util import ErrorDict

from allauth.account.forms import SignupForm
from allauth.account.views import complete_signup

log = logging.getLogger(__name__)


class SessionAuthentication(Authentication):
    """
    Override session auth to always return the auth status
    """
    def is_authenticated(self, request, **kwargs):
        """
        Checks to make sure the user is logged in & has a Django session.
        """
        return request.user.is_authenticated()

    def get_identifier(self, request):
        """
        Provides a unique string identifier for the requestor.
        This implementation returns the user's username.
        """
        return request.user.username

def default_authorization():
    """
    Used to ensure that changing authorization can be done on a sitewide level easily.
    """
    return GuardianAuthorization()

def default_authentication():
    """
    Ensures that authentication can easily be changed on a sitewide level.
    """
    return MultiAuthentication(SessionAuthentication(), ApiKeyAuthentication())

def default_serialization():
    """
    Current serialization formats.  HTML is not supported for now.
    """
    return Serializer(formats=['json', 'jsonp', 'xml', 'yaml', 'html', 'plist'])

def default_throttling():
    """
    Default throttling for models.  Currently only affects essay model.
    """
    return UserAccessThrottle(throttle_at=settings.THROTTLE_AT, timeframe=settings.THROTTLE_TIMEFRAME, expiration= settings.THROTTLE_EXPIRATION)

def run_search(request,obj):
    """
    Runs a search via haystack.
    request - user search request object
    obj - the model for which search is being done
    """
    sqs = SearchQuerySet().models(obj).load_all().auto_query(request.GET.get('q', ''))
    paginator = Paginator(sqs, 20)

    try:
        page = paginator.page(int(request.GET.get('page', 1)))
    except InvalidPage:
        raise Http404("Sorry, no results on that page.")

    return page.object_list

class MockQuerySet(Iterator):
    """
    Mock a query set so that it can be used with default authorization
    """
    def __init__(self, model,data):
        """
        model - a model class
        data - list of data to hold in the mock query set
        """
        self.data = data
        self.model = model
        self.current_elem = 0

    def next(self):
        """
        Fetches the next element in the mock query set
        """
        if self.current_elem>=len(self.data):
            self.current_elem=0
            raise StopIteration
        dat = self.data[self.current_elem]
        self.current_elem+=1
        return dat

class SearchModelResource(ModelResource):
    """
    Extends model resource to add search capabilities
    """
    def prepend_urls(self):
        """
        Adds in a search url for each model that accepts query terms and pages.
        """
        return [
            url(r"^(?P<resource_name>%s)/search%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('get_search'), name="api_get_search"),
            ]

    def get_search(self, request, **kwargs):
        """
        Gets search results for each of the models that inherit from this class
        request - user request object
        """
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        #Run search via haystack and get list of objects
        object_list = run_search(request,self._meta.model_type)
        objects = []

        #Create bundle and authorization
        auth = default_authorization()
        bundle = None

        #Convert search result list into a list of django models
        object_list = [result.object for result in object_list if result is not None]

        #If there is more than one object, then apply authorization limits to the list
        if len(object_list)>0:
            #Mock a bundle, needed to apply auth limits
            bundle = self.build_bundle(obj=object_list[0], request=request)
            bundle = self.full_dehydrate(bundle)

            #Apply authorization limits via auth object that we previously created
            object_list = auth.read_list(MockQuerySet(self._meta.model_type, object_list),bundle)

        for result in object_list:
            bundle = self.build_bundle(obj=result, request=request)
            bundle = self.full_dehydrate(bundle)
            objects.append(bundle)

        object_list = {
            'objects': objects,
            }

        self.log_throttled_access(request)
        return self.create_response(request, object_list)

class CreateUserResource(ModelResource):
    """
    Creates a user with the specified username and password.  This is needed because of permissions restrictions
    on the normal user resource.
    """
    class Meta:
        allowed_methods = ['post']
        object_class = User
        #No authentication for create user, or authorization.  Anyone can create.
        authentication = Authentication()
        authorization = Authorization()
        fields = ['username', 'email']
        resource_name = "createuser"
        always_return_data = True
        throttle = default_throttling()

    def obj_create(self, bundle, **kwargs):
        #Validate that the needed fields exist
        validator = CustomFormValidation(form_class=UserForm, model_type=self._meta.resource_name)
        errors = validator.is_valid(bundle)
        if isinstance(errors, ErrorDict):
            raise BadRequest(errors.as_text())
        #Extract needed fields
        username, password, email = bundle.data['username'], bundle.data['password'], bundle.data['email']
        data_dict = {'username' : username, 'email' : email, 'password' : password, 'password1' : password, 'password2' : password}
        #Pass the fields to django-allauth.  We want to use its email verification setup.
        signup_form = SignupForm()
        signup_form.cleaned_data = data_dict
        try:
            try:
                user = signup_form.save(bundle.request)
                profile, created = UserProfile.objects.get_or_create(user=user)
            except AssertionError:
                #If this fails, the user has a non-unique email address.
                user = User.objects.get(username=username)
                user.delete()
                raise BadRequest("Email address has already been used, try another.")

            #Need this so that the object is added to the bundle and exists during the dehydrate cycle.
            html = complete_signup(bundle.request, user, "")
            bundle.obj = user
        except IntegrityError:
            raise BadRequest("Username is already taken, try another.")

        return bundle

    def dehydrate(self, bundle):
        username = bundle.data.get('username', None)
        if username is not None:
            user = User.objects.get(username=username)
            api_key = user.api_key
            bundle.data['api_key'] = api_key.key
        return bundle

class OrganizationResource(SearchModelResource):
    """
    Preserves appropriate many to many relationships, and encapsulates the Organization model.
    """
    courses = fields.ToManyField('freeform_data.api.CourseResource', 'course_set', null=True)
    essays = fields.ToManyField('freeform_data.api.EssayResource', 'essay_set', null=True)
    #This maps the organization users to the users model via membership
    user_query = lambda bundle: bundle.obj.users.through.objects.all() or bundle.obj.users
    users = fields.ToManyField("freeform_data.api.MembershipResource", attribute=user_query, null=True)
    #Also show members in the organization (useful for getting role)
    memberships = fields.ToManyField("freeform_data.api.MembershipResource", 'membership_set', null=True)
    class Meta:
        queryset = Organization.objects.all()
        resource_name = 'organization'

        serializer = default_serialization()
        authorization= default_authorization()
        authentication = default_authentication()
        always_return_data = True
        model_type = Organization
        throttle = default_throttling()

    def obj_create(self, bundle, **kwargs):
        bundle = super(OrganizationResource, self).obj_create(bundle)
        return bundle

    def save_m2m(self,bundle):
        """
        Save_m2m saves many to many models.  This hack adds a membership object, which is needed, as membership
        is the relation through which organization is connected to user.
        """
        add_membership(bundle.request.user, bundle.obj)
        bundle.obj.save()

    def dehydrate_users(self, bundle):
        """
        Tastypie will currently show memberships instead of users due to the through relation.
        This hacks the relation to show users.
        """
        resource_uris = []
        user_resource = UserResource()
        if bundle.data.get('users'):
            l_users = bundle.obj.users.all()
            for l_user in l_users:
                resource_uris.append(user_resource.get_resource_uri(bundle_or_obj=l_user))
        return resource_uris

class UserProfileResource(SearchModelResource):
    """
    Encapsulates the UserProfile module
    """
    user = fields.ToOneField('freeform_data.api.UserResource', 'user', related_name='userprofile')
    class Meta:
        queryset = UserProfile.objects.all()
        resource_name = 'userprofile'

        serializer = default_serialization()
        authorization= default_authorization()
        authentication = default_authentication()
        always_return_data = True
        model_type = UserProfile
        excludes = ['throttle_at']
        throttle = default_throttling()

    def obj_create(self, bundle, request=None, **kwargs):
        return super(UserProfileResource, self).obj_create(bundle,user=bundle.request.user)

class UserResource(SearchModelResource):
    """
    Encapsulates the User Model
    """
    essaygrades = fields.ToManyField('freeform_data.api.EssayGradeResource', 'essaygrade_set', null=True, related_name='user')
    essays = fields.ToManyField('freeform_data.api.EssayResource', 'essay_set', null=True, related_name='user')
    courses = fields.ToManyField('freeform_data.api.CourseResource', 'course_set', null=True)
    userprofile = fields.ToOneField('freeform_data.api.UserProfileResource', 'userprofile', related_name='user')
    organizations = fields.ToManyField('freeform_data.api.OrganizationResource', 'organization_set', null=True)
    memberships = fields.ToManyField("freeform_data.api.MembershipResource", 'membership_set', null=True)
    class Meta:
        queryset = User.objects.all()
        resource_name = 'user'

        serializer = default_serialization()
        authorization= default_authorization()
        authentication = default_authentication()
        always_return_data = True
        model_type = User
        excludes = ['password']
        throttle = default_throttling()

    def obj_create(self, bundle, **kwargs):
        return super(UserResource, self).obj_create(bundle)

    def dehydrate(self, bundle):
        bundle.data['api_key'] = bundle.obj.api_key.key
        return bundle

class MembershipResource(SearchModelResource):
    """
    Encapsulates the Membership Model
    """
    user = fields.ToOneField('freeform_data.api.UserResource', 'user')
    organization = fields.ToOneField('freeform_data.api.OrganizationResource', 'organization')
    class Meta:
        queryset = Membership.objects.all()
        resource_name = 'membership'

        serializer = default_serialization()
        authorization= default_authorization()
        authentication = default_authentication()
        always_return_data = True
        model_type = Membership
        throttle = default_throttling()

    def obj_create(self, bundle, request=None, **kwargs):
        return super(MembershipResource, self).obj_create(bundle,user=bundle.request.user)

class CourseResource(SearchModelResource):
    """
    Encapsulates the Course Model
    """
    organizations = fields.ToManyField(OrganizationResource, 'organizations', null=True)
    users = fields.ToManyField(UserResource, 'users', null=True)
    problems = fields.ToManyField('freeform_data.api.ProblemResource', 'problem_set', null=True)
    class Meta:
        queryset = Course.objects.all()
        resource_name = 'course'

        serializer = default_serialization()
        authorization= default_authorization()
        authentication = default_authentication()
        always_return_data = True
        model_type = Course
        throttle = default_throttling()

    def obj_create(self, bundle, **kwargs):
        return super(CourseResource, self).obj_create(bundle, user=bundle.request.user)

class ProblemResource(SearchModelResource):
    """
    Encapsulates the problem Model
    """
    essays = fields.ToManyField('freeform_data.api.EssayResource', 'essay_set', null=True, related_name='problem')
    courses = fields.ToManyField('freeform_data.api.CourseResource', 'courses')
    class Meta:
        queryset = Problem.objects.all()
        resource_name = 'problem'

        serializer = default_serialization()
        authorization= default_authorization()
        authentication = default_authentication()
        always_return_data = True
        model_type = Problem
        throttle = default_throttling()
        validation = CustomFormValidation(form_class=ProblemForm, model_type=resource_name)

    def obj_create(self, bundle, **kwargs):
        return super(ProblemResource, self).obj_create(bundle)

class EssayResource(SearchModelResource):
    """
    Encapsulates the essay Model
    """
    essaygrades = fields.ToManyField('freeform_data.api.EssayGradeResource', 'essaygrade_set', null=True, related_name='essay')
    user = fields.ToOneField(UserResource, 'user', null=True)
    organization = fields.ToOneField(OrganizationResource, 'organization', null=True)
    problem = fields.ToOneField(ProblemResource, 'problem')
    class Meta:
        queryset = Essay.objects.all()
        resource_name = 'essay'

        serializer = default_serialization()
        authorization= default_authorization()
        authentication = default_authentication()
        always_return_data = True
        model_type = Essay
        throttle = default_throttling()
        validation = CustomFormValidation(form_class=EssayForm, model_type=resource_name)

    def obj_create(self, bundle, **kwargs):
        bundle = super(EssayResource, self).obj_create(bundle, user=bundle.request.user)
        bundle.obj.user = bundle.request.user
        bundle.obj.save()
        return bundle

class EssayGradeResource(SearchModelResource):
    """
    Encapsulates the EssayGrade Model
    """
    user = fields.ToOneField(UserResource, 'user', null=True)
    essay = fields.ToOneField(EssayResource, 'essay')
    class Meta:
        queryset = EssayGrade.objects.all()
        resource_name = 'essaygrade'

        serializer = default_serialization()
        authorization= default_authorization()
        authentication = default_authentication()
        always_return_data = True
        model_type = EssayGrade
        throttle = default_throttling()
        validation = CustomFormValidation(form_class=EssayGradeForm, model_type=resource_name)

    def obj_create(self, bundle, **kwargs):
        bundle = super(EssayGradeResource, self).obj_create(bundle, user=bundle.request.user)
        bundle.obj.user = bundle.request.user
        bundle.obj.save()
        return bundle

def add_membership(user,organization):
    """
    Adds a membership object.  Required because membership defines the relation between user and organization,
    and tastypie does not automatically create through relations.
    """
    users = organization.users.all()
    membership_count = Membership.objects.filter(user=user).count()
    if membership_count>=settings.MEMBERSHIP_LIMIT:
        error_message = "All users, including user {0} can only have a maximum of 1 organizations.  This will hopefully be fixed in a future release.".format(user)
        log.info(error_message)
        raise BadRequest(error_message)
    membership = Membership(
        user = user,
        organization = organization,
    )
    if users.count()==0:
        #If a user is the first one in an organization, make them the administrator.
        membership.role = UserRoles.administrator
        membership.save()
    else:
        membership.role = UserRoles.student
    membership.save()


########NEW FILE########
__FILENAME__ = django_validators
import json
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _, ungettext_lazy
import logging
log = logging.getLogger(__name__)

class JSONListValidator(object):
    """
    A validator for json lists that are entered into the API
    """
    message = _('Invalid Json List.')

    def __init__(self, matching_list=None, message=None, matching_list_len = None):
        """
        matching_list - the list to match the input values with.  For example, if we are comparing input target values with max target values from the problem object.
        matching_list_len - Used when we only want to match length.
        message- custom error message if desired.
        """
        self.matching_list = matching_list
        self.matching_list_len = None
        if message is not None:
            self.message = message

        #If we have a matching_list_len, use it
        if matching_list_len is not None and isinstance(matching_list_len, int):
            self.matching_list_len = matching_list_len

        #If we have a matching_list, use it.
        if self.matching_list is not None:
            try:
                self.matching_list = json.loads(self.matching_list)
            except Exception:
                pass

            self.matching_list_len = len(self.matching_list)

    def __call__(self, value):
        """
        Validates that the input is valid json and matches other input criteria
        value - A python list or json encoded list
        """

        #Try to load the json
        try:
            value = json.loads(value)
        except Exception:
            pass

        #Value must be a list!
        if not isinstance(value,list):
            error_message = "You entered a non-list entry for value, or entered bad json. {0}".format(value)
            raise ValidationError(error_message)

        value_len = len(value)

        #Each value must be an integer
        for val in value:
            if not isinstance(val,int):
                error_message="You entered a non-integer value in your score list. {0}".format(value)
                raise ValidationError(error_message)

        #Validate the lengths to ensure they match
        if self.matching_list_len is not None:
            if self.matching_list_len!=value_len:
                error_message = "You entered more target scores than exist in the corresponding maximum list in the problem.  {0} vs {1}".format(value_len, self.matching_list_len)
                raise ValidationError(error_message)

        #Validate each value to make sure it is less than the max allowed.
        if self.matching_list is not None:
            for i in xrange(0,self.matching_list_len):
                if value[i]>self.matching_list[i]:
                    error_message = "Value {i} in provided scores greater than max defined in problem. {value} : {matching}".format(i=i, value=value, matching=self.matching_list)
                    raise ValidationError(error_message)




########NEW FILE########
__FILENAME__ = fields
from django.forms import Field
import logging
log = logging.getLogger(__name__)

class JSONListField(Field):
    """
    A stub field for now.  May add in some custom attributes later.
    """
    pass
########NEW FILE########
__FILENAME__ = forms
from django import forms
import fields
import django_validators
import logging
from django.forms.fields import Field, FileField, IntegerField, CharField, ChoiceField, BooleanField, DecimalField, EmailField
from django.core.exceptions import ValidationError
from models import ESSAY_TYPES, GRADER_TYPES

log = logging.getLogger(__name__)

class ProblemForm(forms.Form):
    """
    A form to validate Problem resources
    """
    number_of_additional_predictors = IntegerField(min_value=0, required=False)
    prompt = CharField(min_length=0, required=True)
    name = CharField(min_length=0, required=False)
    def __init__(self, problem_object= None, **kwargs):
        super(ProblemForm, self).__init__(**kwargs)
        validator = django_validators.JSONListValidator()
        self.fields['max_target_scores'] = fields.JSONListField(required=True, validators=[validator])

class EssayForm(forms.Form):
    """
    A form to validate Essay resources
    """
    essay_text = CharField(min_length=0, required=True)
    essay_type = ChoiceField(choices=ESSAY_TYPES, required=True)
    def __init__(self, problem_object=None, **kwargs):
        super(EssayForm, self).__init__(**kwargs)
        if problem_object is not None:
            self.add_pred_length = problem_object.get('number_of_additional_predictors',0)
        else:
            self.add_pred_length = 0

        validator = django_validators.JSONListValidator(matching_list_len=self.add_pred_length)

        self.fields['additional_predictors'] = fields.JSONListField(required = False, validators=[validator])

class EssayGradeForm(forms.Form):
    """
    A form to validate essaygrade resources
    """
    grader_type = ChoiceField(choices=GRADER_TYPES, required=True)
    feedback = CharField(min_length=0, required=False)
    annotated_text = CharField(min_length=0, required=False)
    success = BooleanField(required=True)
    confidence = DecimalField(required=False, max_value=1, max_digits=10)
    def __init__(self, problem_object = None, **kwargs):
        super(EssayGradeForm, self).__init__(**kwargs)
        self.max_target_scores = None
        if problem_object is not None:
            self.max_target_scores = problem_object.get('max_target_scores',None)

        validator = django_validators.JSONListValidator(matching_list=self.max_target_scores)

        self.fields['target_scores'] = fields.JSONListField(required = True, validators=[validator])

class UserForm(forms.Form):
    """
    A form to validate User resources
    """
    username = CharField(min_length=3, required=True)
    email = EmailField(min_length=3, required=True)
    password = CharField(widget=forms.PasswordInput())
    def __init__(self, user_object= None, **kwargs):
        super(UserForm, self).__init__(**kwargs)
########NEW FILE########
__FILENAME__ = guardian_auth
from tastypie.authorization import Authorization
from tastypie.exceptions import TastypieError, Unauthorized
from guardian.core import ObjectPermissionChecker
import logging
log = logging.getLogger(__name__)

def check_permissions(permission_type,user,obj):
    checker = ObjectPermissionChecker(user)
    class_lower_name = obj.__class__.__name__.lower()
    perm = '{0}_{1}'.format(permission_type, class_lower_name)
    return checker.has_perm(perm,obj)

class GuardianAuthorization(Authorization):
    """
      Uses permission checking from ``django.contrib.auth`` to map
      ``POST / PUT / DELETE / PATCH`` to their equivalent Django auth
      permissions.

      Both the list & detail variants simply check the model they're based
      on, as that's all the more granular Django's permission setup gets.
      """
    def base_checks(self, request, model_klass):

        # If it doesn't look like a model, we can't check permissions.
        if not model_klass or not getattr(model_klass, '_meta', None):
            raise Unauthorized("Improper model class defined.")

        # User must be logged in to check permissions.
        if not hasattr(request, 'user'):
            raise Unauthorized("You must be logged in.")

        return model_klass

    #Delete and update permissions can be consolidated into this function
    def check_permissions(self, object_list,bundle, permission_name):
        klass = self.base_checks(bundle.request, object_list.model)
        update_list=[]

        if klass is False:
            return []

        for obj in object_list:
            if check_permissions(permission_name, bundle.request.user, obj):
                update_list.append(obj)

        return update_list

    def check_detail_permissions(self, object_list, bundle, permission_name):
        update_list = self.check_permissions(object_list,bundle, permission_name)
        if len(update_list)==0:
            raise Unauthorized("You are not allowed to access that resource.")
        return True

    def read_list(self, object_list, bundle):
        klass = self.base_checks(bundle.request, object_list.model)
        read_list=[]

        if klass is False:
            return []

        for obj in object_list:
            if check_permissions("view", bundle.request.user, obj):
                read_list.append(obj)
            #Permissions cannot be created for user models, so hack the permissions to show users their own info
            if getattr(klass,'__name__')=="User" and bundle.request.user.id == obj.id:
                read_list.append(obj)
        # GET-style methods are always allowed.
        return read_list

    def read_detail(self, object_list, bundle):
        klass = self.base_checks(bundle.request, bundle.obj.__class__)
        read_list=[]

        #Users don't exist when their own User model is created, so hack to display user info to people
        #This circumvents the normal permissions model and just shows users their own info
        if getattr(klass,'__name__')=="User":
            if bundle.request.user.id == object_list[0].id:
                return True

        read_list = self.check_permissions(object_list,bundle, "view")

        #For some reason, checking if the user has access to the schema calls this function.
        #Handle the case where the user has no objects available to show, but should be able to see the schema.
        if "schema" in bundle.request.path:
            return True

        if len(read_list)==0:
            raise Unauthorized("You are not allowed to access that resource.")

        return True

    def create_list(self, object_list, bundle):
        klass = self.base_checks(bundle.request, object_list.model)
        create_list=[]

        if klass is False:
            return []

        for obj in object_list:
            create_list.append(obj)

        return create_list

    def create_detail(self, object_list, bundle):
        klass = self.base_checks(bundle.request, bundle.obj.__class__)
        create_list=[]

        if klass is False:
            raise Unauthorized("You are not allowed to access that resource.")

        for obj in object_list:
            create_list.append(obj)

        #If the user cannot view the object list that was passed in, then they are unauthorized.
        if len(create_list) != len(object_list):
            raise Unauthorized("You are not allowed to access that resource.")

        return True

    def update_list(self, object_list, bundle):
        return self.check_permissions(object_list,bundle, "change")

    def update_detail(self, object_list, bundle):
        return self.check_detail_permissions(object_list,bundle, "change")

    def delete_list(self, object_list, bundle):
        return self.check_permissions(object_list,bundle, "delete")

    def delete_detail(self, object_list, bundle):
        return self.check_detail_permissions(object_list,bundle, "delete")
########NEW FILE########
__FILENAME__ = helpers
from django.contrib.contenttypes.models import ContentType
from guardian.models import UserObjectPermission
from django.contrib.auth.models import Permission
import re
import logging
import functools
from django.core.cache import cache

log = logging.getLogger(__name__)

def get_content_type(model):
    content_type = ContentType.objects.get_for_model(model)
    return content_type

def get_object_permissions(instance, model):
    content_type = get_content_type(model)
    content_id = content_type.id
    permissions = UserObjectPermission.objects.filter(content_type=content_id, object_pk = instance.pk)
    return permissions

def copy_permissions(base_instance, base_model, new_instance, new_model):
    base_permissions = get_object_permissions(base_instance, base_model)
    new_content_type = get_content_type(new_model)
    for permission in  base_permissions:
        content_type = new_content_type
        object_pk = new_instance.pk
        new_permission_name = generate_new_permission(permission.permission.codename, new_content_type.name)
        django_permission = Permission.objects.get(codename=new_permission_name)
        permission_obj = django_permission
        perm_dict = {
            'user' : permission.user,
            'content_type' : content_type,
            'permission' : permission_obj,
            'object_pk' : object_pk,
            }
        perm, created = UserObjectPermission.objects.get_or_create(**perm_dict)

def generate_new_permission(permission_name, new_model_name):
    new_model_name = re.sub(r"[_\W]", "", new_model_name).lower()
    permission_list = permission_name.split("_")
    permission_list = permission_list[0:(len(permission_list)-1)]
    permission_list += [new_model_name]
    new_permission = "_".join(permission_list)
    return new_permission

def single_instance_task(timeout):
    def task_exc(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            lock_id = "celery-single-instance-" + func.__name__
            acquire_lock = lambda: cache.add(lock_id, "true", timeout)
            release_lock = lambda: cache.delete(lock_id)
            if acquire_lock():
                try:
                    func(*args, **kwargs)
                finally:
                    release_lock()
        return wrapper
    return task_exc
########NEW FILE########
__FILENAME__ = import_test_data
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

#from http://jamesmckay.net/2009/03/django-custom-managepy-commands-not-committing-transactions/
#Fix issue where db data in manage.py commands is not refreshed at all once they start running
from django.db import transaction
transaction.commit_unless_managed()

import requests
import urlparse
import time
import json
import logging
import sys
import json
from ConfigParser import SafeConfigParser
from datetime import datetime

from freeform_data.models import Organization, Course, UserProfile, Problem, Essay, EssayGrade
from django.contrib.auth.models import User

log = logging.getLogger(__name__)

class Command(BaseCommand):
    args = "<filename>"
    help = "Poll grading controller and send items to be graded to ml"


    def handle(self, *args, **options):
        """
        Read from file
        """

        parser = SafeConfigParser()
        parser.read(args[0])


        print("Starting import...")
        print("Reading config from file {0}".format(args[0]))

        header_name = "importdata"

        prompt = parser.get(header_name, 'prompt')
        essay_file = parser.get(header_name, 'essay_file')
        essay_limit = int(parser.get(header_name, 'essay_limit'))
        name = parser.get(header_name, "name")
        add_score = parser.get(header_name, "add_grader_object") == "True"
        max_target_scores = json.loads(parser.get(header_name, "max_target_scores"))
        grader_type = parser.get(header_name, "grader_type")

        try:
            User.objects.create_user('vik', 'vik@edx.org', 'vik')
        except:
            #User already exists, but doesn't matter to us
            pass

        user = User.objects.get(username='vik')
        organization, created = Organization.objects.get_or_create(
            organization_name = "edX"
        )

        course, created = Course.objects.get_or_create(
            course_name = "edX101",
        )
        if created:
            course.organizations.add(organization)

        user.profile.organization = organization
        user.save()
        course.users.add(user)
        course.save()

        problem, created = Problem.objects.get_or_create(
            prompt = prompt,
            name = name,
        )
        problem.courses.add(course)
        problem.save()

        grades, text = [], []
        combined_raw = open(settings.REPO_PATH / essay_file).read()
        raw_lines = combined_raw.splitlines()
        for row in xrange(1, len(raw_lines)):
            line_split = raw_lines[row].strip().split("\t")
            text.append(line_split[0])
            grades.append(line_split[1:])

        max_scores = []
        for i in xrange(0,len(grades[0])):
            scores_at_point = [g[i] for g in grades]
            max_scores.append(max(scores_at_point))
        problem.max_target_scores = json.dumps(max_scores)
        problem.save()
        for i in range(0, min(essay_limit, len(text))):
            essay = Essay(
                problem = problem,
                user =user,
                essay_type = "train",
                essay_text = text[i],
            )

            essay.save()
            score = EssayGrade(
                target_scores=json.dumps(grades[i]),
                feedback="",
                grader_type = grader_type,
                essay = essay,
                success = True,
            )
            score.save()

        print ("Successfully imported {0} essays using configuration in file {1}.".format(
            min(essay_limit, len(text)),
            args[0],
        ))
########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Organization'
        db.create_table('freeform_data_organization', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('organization_size', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('organization_name', self.gf('django.db.models.fields.TextField')(default='')),
            ('premium_service_subscriptions', self.gf('django.db.models.fields.TextField')(default='[]')),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('freeform_data', ['Organization'])

        # Adding model 'UserProfile'
        db.create_table('freeform_data_userprofile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], unique=True, null=True, blank=True)),
            ('organization', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['freeform_data.Organization'], null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('role', self.gf('django.db.models.fields.CharField')(max_length=20, null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
        ))
        db.send_create_signal('freeform_data', ['UserProfile'])

        # Adding model 'Course'
        db.create_table('freeform_data_course', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('organization', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['freeform_data.Organization'])),
            ('course_name', self.gf('django.db.models.fields.TextField')()),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('freeform_data', ['Course'])

        # Adding M2M table for field users on 'Course'
        db.create_table('freeform_data_course_users', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('course', models.ForeignKey(orm['freeform_data.course'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('freeform_data_course_users', ['course_id', 'user_id'])

        # Adding model 'Problem'
        db.create_table('freeform_data_problem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('max_target_scores', self.gf('django.db.models.fields.TextField')(default='[1]')),
            ('number_of_additional_predictors', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('prompt', self.gf('django.db.models.fields.TextField')(default='')),
            ('premium_feedback_models', self.gf('django.db.models.fields.TextField')(default='[]')),
            ('name', self.gf('django.db.models.fields.TextField')(default='')),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('freeform_data', ['Problem'])

        # Adding M2M table for field courses on 'Problem'
        db.create_table('freeform_data_problem_courses', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('problem', models.ForeignKey(orm['freeform_data.problem'], null=False)),
            ('course', models.ForeignKey(orm['freeform_data.course'], null=False))
        ))
        db.create_unique('freeform_data_problem_courses', ['problem_id', 'course_id'])

        # Adding model 'Essay'
        db.create_table('freeform_data_essay', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('problem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['freeform_data.Problem'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('essay_text', self.gf('django.db.models.fields.TextField')()),
            ('additional_predictors', self.gf('django.db.models.fields.TextField')(default='[]')),
            ('essay_type', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('has_been_ml_graded', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('freeform_data', ['Essay'])

        # Adding model 'EssayGrade'
        db.create_table('freeform_data_essaygrade', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('essay', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['freeform_data.Essay'])),
            ('target_scores', self.gf('django.db.models.fields.TextField')()),
            ('grader_type', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('feedback', self.gf('django.db.models.fields.TextField')()),
            ('annotated_text', self.gf('django.db.models.fields.TextField')(default='')),
            ('premium_feedback_scores', self.gf('django.db.models.fields.TextField')(default='[]')),
            ('success', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('confidence', self.gf('django.db.models.fields.DecimalField')(default=1, max_digits=10, decimal_places=9)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('freeform_data', ['EssayGrade'])

        # Adding model 'StudentGroup'
        db.create_table('freeform_data_studentgroup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('userprofile', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['freeform_data.UserProfile'])),
        ))
        db.send_create_signal('freeform_data', ['StudentGroup'])

        # Adding model 'TeacherGroup'
        db.create_table('freeform_data_teachergroup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('userprofile', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['freeform_data.UserProfile'])),
        ))
        db.send_create_signal('freeform_data', ['TeacherGroup'])

        # Adding model 'AdministratorGroup'
        db.create_table('freeform_data_administratorgroup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('userprofile', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['freeform_data.UserProfile'])),
        ))
        db.send_create_signal('freeform_data', ['AdministratorGroup'])

        # Adding model 'GraderGroup'
        db.create_table('freeform_data_gradergroup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('userprofile', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['freeform_data.UserProfile'])),
        ))
        db.send_create_signal('freeform_data', ['GraderGroup'])


    def backwards(self, orm):
        # Deleting model 'Organization'
        db.delete_table('freeform_data_organization')

        # Deleting model 'UserProfile'
        db.delete_table('freeform_data_userprofile')

        # Deleting model 'Course'
        db.delete_table('freeform_data_course')

        # Removing M2M table for field users on 'Course'
        db.delete_table('freeform_data_course_users')

        # Deleting model 'Problem'
        db.delete_table('freeform_data_problem')

        # Removing M2M table for field courses on 'Problem'
        db.delete_table('freeform_data_problem_courses')

        # Deleting model 'Essay'
        db.delete_table('freeform_data_essay')

        # Deleting model 'EssayGrade'
        db.delete_table('freeform_data_essaygrade')

        # Deleting model 'StudentGroup'
        db.delete_table('freeform_data_studentgroup')

        # Deleting model 'TeacherGroup'
        db.delete_table('freeform_data_teachergroup')

        # Deleting model 'AdministratorGroup'
        db.delete_table('freeform_data_administratorgroup')

        # Deleting model 'GraderGroup'
        db.delete_table('freeform_data_gradergroup')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'freeform_data.administratorgroup': {
            'Meta': {'object_name': 'AdministratorGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'userprofile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.UserProfile']"})
        },
        'freeform_data.course': {
            'Meta': {'object_name': 'Course'},
            'course_name': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.Organization']"}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'})
        },
        'freeform_data.essay': {
            'Meta': {'object_name': 'Essay'},
            'additional_predictors': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'essay_text': ('django.db.models.fields.TextField', [], {}),
            'essay_type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'has_been_ml_graded': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.Problem']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'freeform_data.essaygrade': {
            'Meta': {'object_name': 'EssayGrade'},
            'annotated_text': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'confidence': ('django.db.models.fields.DecimalField', [], {'default': '1', 'max_digits': '10', 'decimal_places': '9'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'essay': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.Essay']"}),
            'feedback': ('django.db.models.fields.TextField', [], {}),
            'grader_type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'premium_feedback_scores': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'target_scores': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'freeform_data.gradergroup': {
            'Meta': {'object_name': 'GraderGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'userprofile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.UserProfile']"})
        },
        'freeform_data.organization': {
            'Meta': {'object_name': 'Organization'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'organization_name': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'organization_size': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'premium_service_subscriptions': ('django.db.models.fields.TextField', [], {'default': "'[]'"})
        },
        'freeform_data.problem': {
            'Meta': {'object_name': 'Problem'},
            'courses': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['freeform_data.Course']", 'symmetrical': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_target_scores': ('django.db.models.fields.TextField', [], {'default': "'[1]'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'number_of_additional_predictors': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'premium_feedback_models': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'prompt': ('django.db.models.fields.TextField', [], {'default': "''"})
        },
        'freeform_data.studentgroup': {
            'Meta': {'object_name': 'StudentGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'userprofile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.UserProfile']"})
        },
        'freeform_data.teachergroup': {
            'Meta': {'object_name': 'TeacherGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'userprofile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.UserProfile']"})
        },
        'freeform_data.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.Organization']", 'null': 'True', 'blank': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['freeform_data']
########NEW FILE########
__FILENAME__ = 0002_auto__chg_field_essay_user
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Essay.user'
        db.alter_column('freeform_data_essay', 'user_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True))

    def backwards(self, orm):

        # Changing field 'Essay.user'
        db.alter_column('freeform_data_essay', 'user_id', self.gf('django.db.models.fields.related.ForeignKey')(default=1, to=orm['auth.User']))

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'freeform_data.administratorgroup': {
            'Meta': {'object_name': 'AdministratorGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'userprofile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.UserProfile']"})
        },
        'freeform_data.course': {
            'Meta': {'object_name': 'Course'},
            'course_name': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.Organization']"}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'})
        },
        'freeform_data.essay': {
            'Meta': {'object_name': 'Essay'},
            'additional_predictors': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'essay_text': ('django.db.models.fields.TextField', [], {}),
            'essay_type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'has_been_ml_graded': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.Problem']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'})
        },
        'freeform_data.essaygrade': {
            'Meta': {'object_name': 'EssayGrade'},
            'annotated_text': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'confidence': ('django.db.models.fields.DecimalField', [], {'default': '1', 'max_digits': '10', 'decimal_places': '9'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'essay': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.Essay']"}),
            'feedback': ('django.db.models.fields.TextField', [], {}),
            'grader_type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'premium_feedback_scores': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'target_scores': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'freeform_data.gradergroup': {
            'Meta': {'object_name': 'GraderGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'userprofile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.UserProfile']"})
        },
        'freeform_data.organization': {
            'Meta': {'object_name': 'Organization'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'organization_name': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'organization_size': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'premium_service_subscriptions': ('django.db.models.fields.TextField', [], {'default': "'[]'"})
        },
        'freeform_data.problem': {
            'Meta': {'object_name': 'Problem'},
            'courses': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['freeform_data.Course']", 'symmetrical': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_target_scores': ('django.db.models.fields.TextField', [], {'default': "'[1]'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'number_of_additional_predictors': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'premium_feedback_models': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'prompt': ('django.db.models.fields.TextField', [], {'default': "''"})
        },
        'freeform_data.studentgroup': {
            'Meta': {'object_name': 'StudentGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'userprofile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.UserProfile']"})
        },
        'freeform_data.teachergroup': {
            'Meta': {'object_name': 'TeacherGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'userprofile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.UserProfile']"})
        },
        'freeform_data.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.Organization']", 'null': 'True', 'blank': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['freeform_data']
########NEW FILE########
__FILENAME__ = 0003_auto__del_field_course_organization__del_field_userprofile_organizatio
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Course.organization'
        db.delete_column('freeform_data_course', 'organization_id')

        # Adding M2M table for field organizations on 'Course'
        db.create_table('freeform_data_course_organizations', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('course', models.ForeignKey(orm['freeform_data.course'], null=False)),
            ('organization', models.ForeignKey(orm['freeform_data.organization'], null=False))
        ))
        db.create_unique('freeform_data_course_organizations', ['course_id', 'organization_id'])

        # Deleting field 'UserProfile.organization'
        db.delete_column('freeform_data_userprofile', 'organization_id')


        # Changing field 'UserProfile.user'
        db.alter_column('freeform_data_userprofile', 'user_id', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True, null=True))
        # Adding M2M table for field users on 'Organization'
        db.create_table('freeform_data_organization_users', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('organization', models.ForeignKey(orm['freeform_data.organization'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('freeform_data_organization_users', ['organization_id', 'user_id'])


    def backwards(self, orm):
        # Adding field 'Course.organization'
        db.add_column('freeform_data_course', 'organization',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=1, to=orm['freeform_data.Organization']),
                      keep_default=False)

        # Removing M2M table for field organizations on 'Course'
        db.delete_table('freeform_data_course_organizations')

        # Adding field 'UserProfile.organization'
        db.add_column('freeform_data_userprofile', 'organization',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['freeform_data.Organization'], null=True, blank=True),
                      keep_default=False)


        # Changing field 'UserProfile.user'
        db.alter_column('freeform_data_userprofile', 'user_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], unique=True, null=True))
        # Removing M2M table for field users on 'Organization'
        db.delete_table('freeform_data_organization_users')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'freeform_data.administratorgroup': {
            'Meta': {'object_name': 'AdministratorGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'userprofile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.UserProfile']"})
        },
        'freeform_data.course': {
            'Meta': {'object_name': 'Course'},
            'course_name': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'organizations': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['freeform_data.Organization']", 'symmetrical': 'False'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'})
        },
        'freeform_data.essay': {
            'Meta': {'object_name': 'Essay'},
            'additional_predictors': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'essay_text': ('django.db.models.fields.TextField', [], {}),
            'essay_type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'has_been_ml_graded': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.Problem']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'})
        },
        'freeform_data.essaygrade': {
            'Meta': {'object_name': 'EssayGrade'},
            'annotated_text': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'confidence': ('django.db.models.fields.DecimalField', [], {'default': '1', 'max_digits': '10', 'decimal_places': '9'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'essay': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.Essay']"}),
            'feedback': ('django.db.models.fields.TextField', [], {}),
            'grader_type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'premium_feedback_scores': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'target_scores': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'freeform_data.gradergroup': {
            'Meta': {'object_name': 'GraderGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'userprofile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.UserProfile']"})
        },
        'freeform_data.organization': {
            'Meta': {'object_name': 'Organization'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'organization_name': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'organization_size': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'premium_service_subscriptions': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'freeform_data.problem': {
            'Meta': {'object_name': 'Problem'},
            'courses': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['freeform_data.Course']", 'symmetrical': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_target_scores': ('django.db.models.fields.TextField', [], {'default': "'[1]'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'number_of_additional_predictors': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'premium_feedback_models': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'prompt': ('django.db.models.fields.TextField', [], {'default': "''"})
        },
        'freeform_data.studentgroup': {
            'Meta': {'object_name': 'StudentGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'userprofile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.UserProfile']"})
        },
        'freeform_data.teachergroup': {
            'Meta': {'object_name': 'TeacherGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'userprofile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.UserProfile']"})
        },
        'freeform_data.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['freeform_data']
########NEW FILE########
__FILENAME__ = 0004_auto__del_gradergroup__del_teachergroup__del_studentgroup__del_adminis
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'GraderGroup'
        db.delete_table('freeform_data_gradergroup')

        # Deleting model 'TeacherGroup'
        db.delete_table('freeform_data_teachergroup')

        # Deleting model 'StudentGroup'
        db.delete_table('freeform_data_studentgroup')

        # Deleting model 'AdministratorGroup'
        db.delete_table('freeform_data_administratorgroup')

        # Adding model 'Membership'
        db.create_table('freeform_data_membership', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('role', self.gf('django.db.models.fields.CharField')(default='student', max_length=20)),
            ('organization', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['freeform_data.Organization'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal('freeform_data', ['Membership'])

        # Removing M2M table for field users on 'Organization'
        db.delete_table('freeform_data_organization_users')


    def backwards(self, orm):
        # Adding model 'GraderGroup'
        db.create_table('freeform_data_gradergroup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('userprofile', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['freeform_data.UserProfile'])),
        ))
        db.send_create_signal('freeform_data', ['GraderGroup'])

        # Adding model 'TeacherGroup'
        db.create_table('freeform_data_teachergroup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('userprofile', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['freeform_data.UserProfile'])),
        ))
        db.send_create_signal('freeform_data', ['TeacherGroup'])

        # Adding model 'StudentGroup'
        db.create_table('freeform_data_studentgroup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('userprofile', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['freeform_data.UserProfile'])),
        ))
        db.send_create_signal('freeform_data', ['StudentGroup'])

        # Adding model 'AdministratorGroup'
        db.create_table('freeform_data_administratorgroup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('userprofile', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['freeform_data.UserProfile'])),
        ))
        db.send_create_signal('freeform_data', ['AdministratorGroup'])

        # Deleting model 'Membership'
        db.delete_table('freeform_data_membership')

        # Adding M2M table for field users on 'Organization'
        db.create_table('freeform_data_organization_users', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('organization', models.ForeignKey(orm['freeform_data.organization'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('freeform_data_organization_users', ['organization_id', 'user_id'])


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'freeform_data.course': {
            'Meta': {'object_name': 'Course'},
            'course_name': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'organizations': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['freeform_data.Organization']", 'symmetrical': 'False'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'})
        },
        'freeform_data.essay': {
            'Meta': {'object_name': 'Essay'},
            'additional_predictors': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'essay_text': ('django.db.models.fields.TextField', [], {}),
            'essay_type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'has_been_ml_graded': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.Problem']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'})
        },
        'freeform_data.essaygrade': {
            'Meta': {'object_name': 'EssayGrade'},
            'annotated_text': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'confidence': ('django.db.models.fields.DecimalField', [], {'default': '1', 'max_digits': '10', 'decimal_places': '9'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'essay': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.Essay']"}),
            'feedback': ('django.db.models.fields.TextField', [], {}),
            'grader_type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'premium_feedback_scores': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'target_scores': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'freeform_data.membership': {
            'Meta': {'object_name': 'Membership'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.Organization']"}),
            'role': ('django.db.models.fields.CharField', [], {'default': "'student'", 'max_length': '20'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'freeform_data.organization': {
            'Meta': {'object_name': 'Organization'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'organization_name': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'organization_size': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'premium_service_subscriptions': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.User']", 'null': 'True', 'through': "orm['freeform_data.Membership']", 'blank': 'True'})
        },
        'freeform_data.problem': {
            'Meta': {'object_name': 'Problem'},
            'courses': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['freeform_data.Course']", 'symmetrical': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_target_scores': ('django.db.models.fields.TextField', [], {'default': "'[1]'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'number_of_additional_predictors': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'premium_feedback_models': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'prompt': ('django.db.models.fields.TextField', [], {'default': "''"})
        },
        'freeform_data.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['freeform_data']
########NEW FILE########
__FILENAME__ = 0005_auto__add_field_essay_organization
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Essay.organization'
        db.add_column(u'freeform_data_essay', 'organization',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['freeform_data.Organization'], null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Essay.organization'
        db.delete_column(u'freeform_data_essay', 'organization_id')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'freeform_data.course': {
            'Meta': {'object_name': 'Course'},
            'course_name': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'organizations': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['freeform_data.Organization']", 'symmetrical': 'False'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.User']", 'symmetrical': 'False'})
        },
        u'freeform_data.essay': {
            'Meta': {'object_name': 'Essay'},
            'additional_predictors': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'essay_text': ('django.db.models.fields.TextField', [], {}),
            'essay_type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'has_been_ml_graded': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['freeform_data.Organization']", 'null': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['freeform_data.Problem']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'})
        },
        u'freeform_data.essaygrade': {
            'Meta': {'object_name': 'EssayGrade'},
            'annotated_text': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'confidence': ('django.db.models.fields.DecimalField', [], {'default': '1', 'max_digits': '10', 'decimal_places': '9'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'essay': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['freeform_data.Essay']"}),
            'feedback': ('django.db.models.fields.TextField', [], {}),
            'grader_type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'premium_feedback_scores': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'target_scores': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'freeform_data.membership': {
            'Meta': {'object_name': 'Membership'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['freeform_data.Organization']"}),
            'role': ('django.db.models.fields.CharField', [], {'default': "'student'", 'max_length': '20'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'freeform_data.organization': {
            'Meta': {'object_name': 'Organization'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'organization_name': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'organization_size': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'premium_service_subscriptions': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['auth.User']", 'null': 'True', 'through': u"orm['freeform_data.Membership']", 'blank': 'True'})
        },
        u'freeform_data.problem': {
            'Meta': {'object_name': 'Problem'},
            'courses': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['freeform_data.Course']", 'symmetrical': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_target_scores': ('django.db.models.fields.TextField', [], {'default': "'[1]'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'number_of_additional_predictors': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'premium_feedback_models': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'prompt': ('django.db.models.fields.TextField', [], {'default': "''"})
        },
        u'freeform_data.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['freeform_data']
########NEW FILE########
__FILENAME__ = 0006_auto__add_field_userprofile_throttle_at
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'UserProfile.throttle_at'
        db.add_column(u'freeform_data_userprofile', 'throttle_at',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'UserProfile.throttle_at'
        db.delete_column(u'freeform_data_userprofile', 'throttle_at')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'freeform_data.course': {
            'Meta': {'object_name': 'Course'},
            'course_name': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'organizations': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['freeform_data.Organization']", 'symmetrical': 'False'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.User']", 'symmetrical': 'False'})
        },
        u'freeform_data.essay': {
            'Meta': {'object_name': 'Essay'},
            'additional_predictors': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'essay_text': ('django.db.models.fields.TextField', [], {}),
            'essay_type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'has_been_ml_graded': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['freeform_data.Organization']", 'null': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['freeform_data.Problem']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'})
        },
        u'freeform_data.essaygrade': {
            'Meta': {'object_name': 'EssayGrade'},
            'annotated_text': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'confidence': ('django.db.models.fields.DecimalField', [], {'default': '1', 'max_digits': '10', 'decimal_places': '9'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'essay': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['freeform_data.Essay']"}),
            'feedback': ('django.db.models.fields.TextField', [], {}),
            'grader_type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'premium_feedback_scores': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'target_scores': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'freeform_data.membership': {
            'Meta': {'object_name': 'Membership'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['freeform_data.Organization']"}),
            'role': ('django.db.models.fields.CharField', [], {'default': "'student'", 'max_length': '20'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'freeform_data.organization': {
            'Meta': {'object_name': 'Organization'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'organization_name': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'organization_size': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'premium_service_subscriptions': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['auth.User']", 'null': 'True', 'through': u"orm['freeform_data.Membership']", 'blank': 'True'})
        },
        u'freeform_data.problem': {
            'Meta': {'object_name': 'Problem'},
            'courses': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['freeform_data.Course']", 'symmetrical': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_target_scores': ('django.db.models.fields.TextField', [], {'default': "'[1]'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'number_of_additional_predictors': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'premium_feedback_models': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'prompt': ('django.db.models.fields.TextField', [], {'default': "''"})
        },
        u'freeform_data.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'throttle_at': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['freeform_data']
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.auth.models import User, Group, Permission
from tastypie.models import create_api_key
import json
from django.db.models.signals import pre_delete, pre_save, post_save, post_delete
from request_provider.signals import get_request
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import SiteProfileNotAvailable
from guardian.shortcuts import assign_perm

import logging
log=logging.getLogger(__name__)

#CLASSES THAT WRAP CONSTANTS

class UserRoles(object):
    student = "student"
    teacher = "teacher"
    administrator = "administrator"
    grader = "grader"
    creator = "creator"

class EssayTypes(object):
    test = "test"
    train = "train"

class GraderTypes(object):
    machine = "ML"
    instructor = "IN"
    peer = "PE"
    self = "SE"

ESSAY_TYPES = (
    (EssayTypes.test, EssayTypes.test),
    (EssayTypes.train, EssayTypes.train)
)

GRADER_TYPES = (
    (GraderTypes.machine, GraderTypes.machine),
    (GraderTypes.instructor, GraderTypes.instructor),
    (GraderTypes.peer, GraderTypes.peer),
    (GraderTypes.self, GraderTypes.self),
)


PERMISSIONS = ["view", "add", "delete", "change"]
PERMISSION_MODELS = ["organization", "membership", "userprofile", "course", "problem", "essay", "essaygrade"]

#MODELS

class Organization(models.Model):
    #TODO: Add in address info, etc later on
    organization_size = models.IntegerField(default=0)
    organization_name = models.TextField(default="")
    #TODO: Add in billing details, etc later, along with rules on when to ask
    premium_service_subscriptions = models.TextField(default=json.dumps([]))
    #Each organization can have many users, and a user can be in multiple organizations
    users = models.ManyToManyField(User, blank=True,null=True, through="freeform_data.Membership")
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = (
            ("view_organization", "Can view organization"),
        )

class Membership(models.Model):
    role = models.CharField(max_length=20, default=UserRoles.student)
    organization = models.ForeignKey(Organization)
    user = models.ForeignKey(User)

    class Meta:
        permissions = (
            ("view_membership", "Can view membership"),
        )

    def save(self, *args, **kwargs):
        members_count = Membership.objects.filter(user = self.user).exclude(id=self.id).count()
        if members_count>=settings.MEMBERSHIP_LIMIT:
            error_message = "You can currently only be a member of a single organization.  This will hopefully be changed in the future.  Generated for user {0}.".format(self.user)
            log.info(error_message)
            return error_message
        super(Membership, self).save(*args, **kwargs) # Call the "real" save() method.

class UserProfile(models.Model):
    #TODO: Add in a callback where if user identifies as "administrator", then they can create an organization
    #Each userprofile has one user, and vice versa
    user = models.OneToOneField(User, unique=True, blank=True,null=True)
    #TODO: Potentially support users being in multiple orgs, but will be complicated
    #Add in userinfo here.  Location, etc
    name = models.TextField(blank=True,null=True)
    #User role in their organization
    role = models.CharField(max_length=20,blank=True,null=True)
    throttle_at = models.IntegerField(default=0)

    created = models.DateTimeField(auto_now_add=True,blank=True, null=True)
    modified = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        permissions = (
            ("view_userprofile", "Can view userprofile"),
        )

class Course(models.Model):
    #A user can have many courses, and a course can have many users
    users = models.ManyToManyField(User)
    #A course can be shared between organizations
    organizations = models.ManyToManyField(Organization)
    #Each course has a name!
    course_name = models.TextField()

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = (
            ("view_course", "Can view course"),
        )

class Problem(models.Model):
    #A course has many problems, and a problem can be used in many courses
    courses = models.ManyToManyField(Course)
    #Max scores for one or many targets
    max_target_scores = models.TextField(default=json.dumps([1]))
    #If additional numeric predictors are being sent, the count of them
    number_of_additional_predictors = models.IntegerField(default=0)
    #Prompt of the problem
    prompt = models.TextField(default="")
    #If org has subscriptions to premium feedback models
    premium_feedback_models = models.TextField(default=json.dumps([]))
    name = models.TextField(default="")

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = (
            ("view_problem", "Can view problem"),
        )

class Essay(models.Model):
    #Each essay is written for a specific problem
    problem = models.ForeignKey(Problem)
    #Each essay is written by a specified user
    user = models.ForeignKey(User, null=True)
    #Each essay is associated with an organization
    organization = models.ForeignKey(Organization, null=True)
    #Each user writes text (their essay)
    essay_text = models.TextField()
    #Schools may wish to send additional predictors (student grade level, etc)
    additional_predictors = models.TextField(default=json.dumps([]))
    #The type of essay (train or test)  see EssayTypes class
    essay_type = models.CharField(max_length=20)
    has_been_ml_graded = models.BooleanField(default=False)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def get_instructor_scored(self):
        return self.essaygrade_set.filter(grader_type=GraderTypes.instructor).order_by("-modified")[:1]

    class Meta:
        permissions = (
            ("view_essay", "Can view essay"),
        )

class EssayGrade(models.Model):
    #Each essaygrade is for a specific essay
    essay = models.ForeignKey(Essay)
    #How the essay was scored for numerous targets
    target_scores = models.TextField()
    #What type of grader graded it
    grader_type = models.CharField(max_length=20)
    #Feedback from the grader
    feedback = models.TextField()
    #Annotated text from the grader
    annotated_text = models.TextField(default="")
    #Scores on premium feedback model, if any
    premium_feedback_scores = models.TextField(default=json.dumps([]))
    #whether or not the grader succeeded
    success = models.BooleanField()
    #For peer grading and staff grading, we will use this
    user = models.ForeignKey(User,blank=True,null=True)
    #Confidence value from the grader
    confidence = models.DecimalField(max_digits=10,decimal_places=9, default=1)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = (
            ("view_essaygrade", "Can view essaygrade"),
        )


#MODEL SIGNAL CALLBACKS

def create_user_profile(sender, instance, created, **kwargs):
    """
    Creates a user profile based on a signal from User when it is created
    """
    if created:
        profile, created = UserProfile.objects.get_or_create(user=instance)


def pre_delete_problem(sender, instance, **kwargs):
    """
    Deletes essays associated with a problem when it is deleted
    """
    essays = Essay.objects.filter(problem=instance)
    essays.delete()

def pre_delete_essay(sender, instance, **kwargs):
    """
    Deletes essay grades associated with an essay when it is deleted
    """
    essay_grades = EssayGrade.objects.filter(essay=instance)
    essay_grades.delete()

def pre_delete_essaygrade(sender,instance, **kwargs):
    """
    Ensures that an ML model will be retrained if an old ML scored grade is removed for some reason
    """
    essay = instance.essay
    ml_graded_count = essay.essaygrade_set.filter(grader_type=GraderTypes.machine).count()
    if ml_graded_count<=1:
        essay.has_been_ml_graded=False
        essay.save()

def pre_delete_user(sender,instance,**kwargs):
    """
    Removes the user's profile and removes foreign key relations from objects
    """
    try:
        user_profile = instance.profile
    except SiteProfileNotAvailable:
        log.error("Could not get profile for user {0}".format(instance.username))
        return
    essays = instance.essay_set.all()
    essay_grades = instance.essaygrade_set.all()
    user_profile.delete()
    essays.update(user=None)
    essay_grades.update(user=None)

def add_user_to_groups(sender,instance,**kwargs):
    user = instance.user
    org = instance.organization
    group_name = get_group_name(instance)
    if not Group.objects.filter(name=group_name).exists():
        group = Group.objects.create(name=group_name)
        group.save()
    else:
        group = Group.objects.get(name=group_name)
    user.groups.add(group)
    user.save()

def remove_user_from_groups(sender,instance,**kwargs):
    user = instance.user
    org = instance.organization
    group_name = get_group_name(instance)
    user.groups.filter(name=group_name).delete()
    user.save()

def get_group_name(membership):
    group_name = "{0}_{1}".format(membership.organization.id,membership.role)
    return group_name

def add_creator_permissions(sender, instance, **kwargs):
    try:
        instance_name = instance.__class__.__name__.lower()
        if isinstance(instance, User):
            user = instance
        elif isinstance(instance, UserProfile):
            user=instance.user
        else:
            user = get_request().user
        if instance_name in PERMISSION_MODELS:
            for perm in PERMISSIONS:
                assign_perm('{0}_{1}'.format(perm, instance_name), user, instance)
    except:
        log.debug("Cannot generate perms.  This is probably okay.")

#Django signals called after models are handled
pre_save.connect(remove_user_from_groups, sender=Membership)

post_save.connect(create_user_profile, sender=User)
post_save.connect(create_api_key, sender=User)
post_save.connect(add_user_to_groups, sender=Membership)
post_save.connect(add_creator_permissions)

pre_delete.connect(pre_delete_problem,sender=Problem)
pre_delete.connect(pre_delete_essay,sender=Essay)
pre_delete.connect(pre_delete_essaygrade,sender=EssayGrade)
pre_delete.connect(pre_delete_user, sender=User)
pre_delete.connect(remove_user_from_groups, sender=Membership)

#Maps the get_profile() function of a user to an attribute profile
User.profile = property(lambda u: u.get_profile())

#Register models with the django admin
admin.site.register(Organization)
admin.site.register(Course)
admin.site.register(Problem)
admin.site.register(Essay)
admin.site.register(EssayGrade)
admin.site.register(Membership)











########NEW FILE########
__FILENAME__ = search_indexes
import datetime
from haystack.indexes import SearchIndex, CharField, DateTimeField, BooleanField, DecimalField
from haystack import site
from models import Organization, Course, Problem, Essay, EssayGrade

class BaseIndex(SearchIndex):
    """
    Define a base search index class for all models.  Fields text, created, and modified are generic across all models.
    See haystack documentation for what the text field and document=True mean.  Templates have to be added to
    templates/search/indexes/freeform_data.
    """
    text = CharField(document=True, use_template=True)
    created = DateTimeField(model_attr='created')
    modified = DateTimeField(model_attr='modified')
    model_type = None

    def get_model(self):
        return self.model_type

    def index_queryset(self, using=None):
        """
        Used when the entire index for model is updated.
        """
        return self.get_model().objects.all()

class OrganizationIndex(BaseIndex):
    model_type = Organization

class CourseIndex(BaseIndex):
    model_type = Course

class ProblemIndex(BaseIndex):
    model_type = Problem

class EssayIndex(BaseIndex):
    type = CharField(model_attr="essay_type")
    ml_graded = BooleanField(model_attr="has_been_ml_graded")
    model_type = Essay

class EssayGradeIndex(BaseIndex):
    success = BooleanField(model_attr="success")
    confidence = DecimalField(model_attr="confidence")
    model_type = EssayGrade

#Register all of the search indexes.  Must be done in pairs.
site.register(Organization, OrganizationIndex)
site.register(Course, CourseIndex)
site.register(Problem, ProblemIndex)
site.register(Essay, EssayIndex)
site.register(EssayGrade, EssayGradeIndex)
########NEW FILE########
__FILENAME__ = serializers
import time
import django
from django.utils import simplejson
from django.core.serializers import json
from tastypie.serializers import Serializer

class CustomJSONSerializer(Serializer):
    def to_json(self, data, options=None):
        """
        Given some Python data, produces JSON output.
        """
        options = options or {}
        data = self.to_simple(data, options)

        if django.get_version() >= '1.5':
            return json.json.dumps(data, cls=json.DjangoJSONEncoder, sort_keys=True, ensure_ascii=False)
        else:
            return simplejson.dumps(data, cls=json.DjangoJSONEncoder, sort_keys=True, ensure_ascii=False)

    def from_json(self, content):
        """
        Given some JSON data, returns a Python dictionary of the decoded data.
        """
        return simplejson.loads(content)
########NEW FILE########
__FILENAME__ = tasks
"""
Used by celery to decide what tasks it needs to do
"""

from celery import task
import logging
from celery.task import periodic_task
from datetime import timedelta
from django.conf import settings
from django.core.management import call_command
from helpers import single_instance_task

log = logging.getLogger(__name__)

@periodic_task(run_every=timedelta(seconds=settings.TIME_BETWEEN_INDEX_REBUILDS))
@single_instance_task(settings.INDEX_REFRESH_CACHE_LOCK_TIME)
def refresh_search_index():
    """
    A task that will periodically update the search index
    """
    call_command('update_index', interactive=False)
########NEW FILE########
__FILENAME__ = tastypie_validators
from tastypie.validation import FormValidation
from django.core.exceptions import ImproperlyConfigured
from django.forms import ModelForm
from django.forms.models import model_to_dict
from models import Problem, Essay
import logging
log = logging.getLogger(__name__)

class CustomFormValidation(FormValidation):
    """
    A validation class that uses a Django ``Form`` to validate the data.

    This class **DOES NOT** alter the data sent, only verifies it. If you
    want to alter the data, please use the ``CleanedDataFormValidation`` class
    instead.

    This class requires a ``form_class`` argument, which should be a Django
    ``Form`` (or ``ModelForm``, though ``save`` will never be called) class.
    This form will be used to validate the data in ``bundle.data``.
    """
    def __init__(self, **kwargs):
        """
        model_type - the type of model that is being validated (resource_name in tastypie api)
        form_class - the class of the django form used to validate the input data
        """
        for key in ['form_class', 'model_type']:
            if not key in kwargs:
                raise ImproperlyConfigured("You must provide a {0} to 'FormValidation' classes.".format(key))

        self.form_class = kwargs.pop('form_class')
        self.model_type = kwargs.pop('model_type')

    def is_valid(self, bundle, request=None):
        """
        Performs a check on ``bundle.data``to ensure it is valid.

        If the form is valid, an empty list (all valid) will be returned. If
        not, a list of errors will be returned.
        """

        #Get a problem object and the form data from the bundle
        form_data, problem_obj = self.form_args(bundle)

        #Ensure that the validation is being done only on the object that the user just manipulated
        request_path = bundle.request.get_full_path()
        request_model_type = (request_path.split('/')[-3])

        #Don't append the problem object if we are doing secondary validations
        if self.model_type in request_model_type:
            form_data['problem_object'] = problem_obj

        form = self.form_class(**form_data)
        if form.is_valid():
            return {}

        # The data is invalid. Let's collect all the error messages & return
        # them.
        return form.errors

    def uri_to_pk(self, uri):
        """
        Returns the integer PK part of a URI.

        Assumes ``/api/v1/resource/123/`` format. If conversion fails, this just
        returns the URI unmodified.

        Also handles lists of URIs
        """

        if uri is None:
            return None

        # convert everything to lists
        multiple = not isinstance(uri, basestring)
        uris = uri if multiple else [uri]

        # handle all passed URIs
        converted = []
        for one_uri in uris:
            try:
                # hopefully /api/v1/<resource_name>/<pk>/
                converted.append(int(one_uri.split('/')[-2]))
            except (IndexError, ValueError):
                raise ValueError(
                    "URI %s could not be converted to PK integer." % one_uri)

        # convert back to original format
        return converted if multiple else converted[0]

    def form_args(self, bundle):
        kwargs = super(CustomFormValidation, self).form_args(bundle)

        #Try to find the problem object corresponding to the primary key values if needed
        problem_obj = None
        for field in kwargs['data']:
            #Essays have problem fields that can be scraped to get a problem object
            if field=="problem" and self.model_type=="essay":
                problem_id = self.uri_to_pk(kwargs['data'][field])
                problem_obj = model_to_dict(Problem.objects.get(id=problem_id))
            #Essaygrades have essay fields that can be scraped to get a problem object
            elif field=="essay" and self.model_type=="essaygrade":
                essay_id = self.uri_to_pk(kwargs['data'][field])
                essay_obj = Essay.objects.get(id=essay_id)
                problem_obj = model_to_dict(essay_obj.problem)

        return kwargs, problem_obj

########NEW FILE########
__FILENAME__ = tests
"""
Run me with:
    python manage.py test
"""
import json
import unittest
from datetime import datetime
import logging
import urlparse

from django.contrib.auth.models import User
from django.test.client import Client
import requests
from django.conf import settings
from django.utils import timezone
from models import Organization, Course, Problem, Essay, EssayGrade, UserProfile, Membership
from django.core.urlresolvers import reverse
from django.core.management import call_command
from ml_grading import ml_model_creation, ml_grader
import sys

log = logging.getLogger(__name__)

def run_setup():
    """
    Setup function
    """
    #Check to see if test user is created and create if not.
    if(User.objects.filter(username='test').count() == 0):
        user = User.objects.create_user('test', 'test@test.com', 'test')
        user.save()

def delete_all():
    """
    Teardown function to delete everything in DB
    """
    Organization.objects.all().delete()
    Course.objects.all().delete()
    #This should cascade down and delete all associated essays and essaygrades
    Problem.objects.all().delete()
    Membership.objects.all().delete()

def get_urls(resource_name):
    """
    Get endpoint and schema urls through url reverse
    resource_name - The name of an api resource.  ie "organization"
    """
    endpoint = reverse("api_dispatch_list", kwargs={'api_name': 'v1','resource_name': resource_name})
    schema = reverse("api_get_schema", kwargs={'api_name': 'v1','resource_name': resource_name})
    return endpoint,schema

def get_first_resource_uri(obj_type):
    """
    Get the first resource uri of an object of a given type
    type - the type of resource as defined in the api, ie "organization"
    """
    #Create a client and login
    c = login()
    #Get the urls needed
    endpoint, schema = get_urls(obj_type)
    #Get the data on all models from the endpoint
    data = c.get(endpoint, data={'format' : 'json'})
    #Grab a single object, and get the resource uri from it
    obj = json.loads(data.content)['objects'][0]
    resource_uri = obj['resource_uri']
    return resource_uri

def create_object(obj_type, obj):
    """
    Create an object of a given type if the data is given
    type - the type of resource as defined in the api, ie "organization"
    object - the data to post to the server to create the object of type
    """
    c = login()
    endpoint, schema = get_urls(obj_type)
    result = c.post(endpoint, json.dumps(obj), "application/json")
    return result

def login():
    """
    Creates a client, logs in as the test user, and returns the client
    """
    c = Client()
    c.login(username='test', password='test')
    return c

def create_organization():
    """
    Create an organization
    """
    Membership.objects.all().delete()
    organization_object =  {"name" : "edX"}
    result = create_object("organization", organization_object)
    organization_resource_uri = json.loads(result.content)['resource_uri']
    return organization_resource_uri

def create_course():
    """
    Create a course
    """
    course_object = {'course_name' : "edx_test"}
    result = create_object("course", course_object)
    course_resource_uri = json.loads(result.content)['resource_uri']
    return course_resource_uri

def create_problem():
    """
    Create a problem
    """
    course_resource_uri = create_course()
    problem_object = {'courses' : [course_resource_uri], 'max_target_scores' : json.dumps([1,1]), 'prompt' : "blah"}
    result = create_object("problem", problem_object)
    problem_resource_uri = json.loads(result.content)['resource_uri']
    return problem_resource_uri

def create_essay():
    """
    Create an essay
    """
    problem_resource_uri = create_problem()
    essay_object = {'problem' : problem_resource_uri, 'essay_text' : "This is a test essay!", 'essay_type' : 'train'}
    result = create_object("essay", essay_object)
    essay_resource_uri = json.loads(result.content)['resource_uri']
    return essay_resource_uri

def create_essaygrade():
    """
    Create an essaygrade
    """
    essay_resource_uri = create_essay()
    essaygrade_object = {'essay' : essay_resource_uri, 'target_scores' : json.dumps([1,1]), 'grader_type' : "IN", 'feedback' : "Was ok.", 'success' : True}
    result = create_object("essaygrade", essaygrade_object)
    essaygrade_resource_uri = json.loads(result.content)['resource_uri']
    return essaygrade_resource_uri

model_registry = {
    'course' : create_course,
    'problem' : create_problem,
    'essay' : create_essay,
    'organization' : create_organization,
    'essaygrade' : create_essaygrade,
}

def create_ml_problem_and_essays(obj_type, count):
    problem_resource_uri = create_problem()
    create_ml_essays_only(obj_type,count,problem_resource_uri)
    return problem_resource_uri

def create_ml_essays_only(obj_type,count,problem_resource_uri):
    essay_list = []
    for i in xrange(0,count):
        essay_object = {'problem' : problem_resource_uri, 'essay_text' : "This is a test essay!", 'essay_type' : obj_type}
        result = create_object("essay", essay_object)
        essay_resource_uri = json.loads(result.content)['resource_uri']
        essay_list.append(essay_resource_uri)
        essaygrade_object = {'essay' : essay_resource_uri, 'target_scores' : json.dumps([1,1]), 'grader_type' : "IN", 'feedback' : "Was ok.", 'success' : True}
        create_object("essaygrade", essaygrade_object)
    return essay_list

def lookup_object(resource_uri):
    c = login()
    result = c.get(resource_uri,
                        data={'format' : 'json'}
    )
    return json.loads(result.content)

class GenericTest(object):
    """
    Base class that other model tests inherit from.
    """
    obj_type = "generic"
    obj = {'hello' : 'world'}

    def generic_setup(self):
        """
        Setup function that runs tasks common to all modules
        """
        run_setup()
        self.c = login()
        self.endpoint, self.schema = get_urls(self.obj_type)

    def test_schema(self):
        """
        See if the schema can be downloaded
        """
        result = self.c.get(self.schema,
                            data={'format' : 'json'}
        )

        self.assertEqual(result.status_code,200)

    def test_endpoint(self):
        """
        See if the GET method can be used with the endpoint
        """
        result = self.c.get(self.endpoint,
                            data={'format' : 'json'}
        )

        self.assertEqual(result.status_code,200)

    def test_create(self):
        """
        See if POST can be used with the endpoint
        """
        result = self.c.post(self.endpoint, json.dumps(self.obj), "application/json")
        self.assertEqual(result.status_code,201)

    def test_update(self):
        """
        See if an object can be created and then updated
        """
        obj = model_registry[self.obj_type]()
        result = self.c.put(obj, json.dumps(self.obj), "application/json")
        self.assertEqual(result.status_code,202)

    def test_delete(self):
        """
        See if an object can be created and then deleted
        """
        obj = model_registry[self.obj_type]()
        result = self.c.delete(obj)
        self.assertEqual(result.status_code,204)

    def test_view_single(self):
        """
        See if the detail view works for an object
        """
        obj = model_registry[self.obj_type]()
        result = self.c.get(obj,
                            data={'format' : 'json'}
        )
        self.assertEqual(result.status_code,200)

    def test_search(self):
        """
        Test if we can search in a given endpoint
        """
        #Refresh haystack index
        call_command('update_index', interactive=False)
        obj = model_registry[self.obj_type]()
        result = self.c.get(self.endpoint + "search/",
                            data={'format' : 'json'}
        )
        self.assertEqual(result.status_code,200)

class OrganizationTest(unittest.TestCase, GenericTest):
    obj_type="organization"
    obj = {"name" : "edX"}

    def setUp(self):
        Membership.objects.all().delete()
        self.generic_setup()

class CourseTest(unittest.TestCase, GenericTest):
    obj_type="course"
    obj = {'course_name' : "edx_test"}
    def setUp(self):
        self.generic_setup()

class ProblemTest(unittest.TestCase, GenericTest):
    obj_type="problem"

    def setUp(self):
        self.generic_setup()
        self.create_object()

    def create_object(self):
        course_resource_uri = create_course()
        self.obj = {'courses' : [course_resource_uri], 'max_target_scores' : json.dumps([1,1]), 'prompt' : "blah"}

class EssayTest(unittest.TestCase, GenericTest):
    obj_type="essay"
    def setUp(self):
        self.generic_setup()
        self.create_object()

    def create_object(self):
        problem_resource_uri = create_problem()
        self.obj = {'problem' : problem_resource_uri, 'essay_text' : "This is a test essay!", 'essay_type' : 'train'}

class EssayGradeTest(unittest.TestCase, GenericTest):
    obj_type="essaygrade"
    def setUp(self):
        self.generic_setup()
        self.create_object()

    def create_object(self):
        essay_resource_uri = create_essay()
        self.obj = {'essay' : essay_resource_uri, 'target_scores' : json.dumps([1,1]), 'grader_type' : "IN", 'feedback' : "Was ok.", 'success' : True}

class CreateUserTest(unittest.TestCase):
    obj_type = "createuser"
    def setUp(self):
        """
        This is a special model to create users, so it doesn't inherit from generic
        """
        self.c = login()
        self.endpoint, self.schema = get_urls(self.obj_type)
        self.post_data = {
            'username' : 'test1',
            'password' : 'test1',
            'email' : 'test1@test1.com'
        }

    def test_create(self):
        """
        See if POST can be used with the endpoint
        """
        result = self.c.post(self.endpoint, json.dumps(self.post_data), "application/json")
        self.assertEqual(result.status_code,201)

class MLTest(unittest.TestCase):
    def test_ml_creation(self):
        """
        Test to see if an ml model can be created and then if essays can be graded
        """
        #Create 10 training essays that are scored
        problem_resource_uri = create_ml_problem_and_essays("train",10)

        #Get the problem so that we can pass it to ml model generation engine
        problem = lookup_object(problem_resource_uri)
        problem_id = problem['id']
        problem_model = Problem.objects.get(id=problem_id)

        #Create the ml model
        creator_success, message = ml_model_creation.handle_single_problem(problem_model)

        #Create some test essays and see if the model can score them
        essay_list = create_ml_essays_only("test",10, problem_resource_uri)

        #Lookup the first essay and try to score it
        essay = lookup_object(essay_list[0])
        essay_id = essay['id']
        essay_model = Essay.objects.get(id=essay_id)

        #Try to score the essay
        grader_success, message = ml_grader.handle_single_essay(essay_model)

        self.assertEqual(creator_success, settings.FOUND_ML)
        self.assertEqual(grader_success, settings.FOUND_ML)

class ViewTest(unittest.TestCase):
    def setUp(self):
        run_setup()
        self.c = Client()

    def test_login(self):
        """
        Test the login view
        """
        login_url = reverse('freeform_data.views.login')
        response = self.c.post(login_url,{'username' : 'test', 'password' : 'test'})
        log.debug(json.loads(response.content))
        response_code = json.loads(response.content)['success']
        self.assertEqual(response_code,True)

    def test_logout(self):
        """
        Test the logout view
        """
        logout_url = reverse('freeform_data.views.logout')
        response = self.c.post(logout_url)
        response_code = json.loads(response.content)['success']
        self.assertEqual(response_code,True)

class FinalTest(unittest.TestCase):
    def test_delete(self):
        """
        Test to see if we can delete all models properly.
        """
        c = login()
        delete_all()
        endpoint, schema = get_urls("organization")
        data = c.get(endpoint, data={'format' : 'json'})
        self.assertEqual(len(json.loads(data.content)['objects']),0)

        endpoint, schema = get_urls("essaygrade")
        data = c.get(endpoint, data={'format' : 'json'})
        self.assertEqual(len(json.loads(data.content)['objects']),0)






########NEW FILE########
__FILENAME__ = throttle
from tastypie.throttle import CacheDBThrottle
import time
from django.core.cache import cache
from django.contrib.auth.models import User, SiteProfileNotAvailable

import logging
log = logging.getLogger(__name__)

class UserAccessThrottle(CacheDBThrottle):
    """
    A throttling mechanism that uses the cache for actual throttling but
    writes-through to the database.

    This is useful for tracking/aggregating usage through time, to possibly
    build a statistics interface or a billing mechanism.
    """
    def __init__(self, throttle_at=150, timeframe=3600, expiration=None, model_type=None):
        super(UserAccessThrottle, self).__init__(throttle_at,timeframe,expiration)
        self.model_type = model_type

    def should_be_throttled(self, identifier, **kwargs):
        """
        Returns whether or not the user has exceeded their throttle limit.

        Maintains a list of timestamps when the user accessed the api within
        the cache.

        Returns ``False`` if the user should NOT be throttled or ``True`` if
        the user should be throttled.
        """

        #Generate a more granular id
        new_id, url, request_method = self.get_new_id(identifier, **kwargs)
        key = self.convert_identifier_to_key(new_id)

        #See if we can get a user and adjust throttle limit
        user = self.get_user(identifier)
        throttle_at = self.get_rate_limit_for_user(user)

        # Make sure something is there.
        cache.add(key, [])

        # Weed out anything older than the timeframe.
        minimum_time = int(time.time()) - int(self.timeframe)
        times_accessed = [access for access in cache.get(key) if access >= minimum_time]
        cache.set(key, times_accessed, self.expiration)

        if len(times_accessed) >= int(throttle_at):
            # Throttle them.
            return True

        # Let them through.
        return False

    def accessed(self, identifier, **kwargs):
        """
        Handles recording the user's access.
        identifier - whatever identifier is passed into the class.  Generally the username
        kwargs - can contain request method and url
        """

        #Generate a new id
        new_id, url, request_method = self.get_new_id(identifier, **kwargs)
        key = self.convert_identifier_to_key(new_id)

        #Get times accessed and increment
        times_accessed = cache.get(key, [])
        times_accessed.append(int(time.time()))
        cache.set(key, times_accessed, self.expiration)

        # Write out the access to the DB for logging purposes.
        # Do the import here, instead of top-level, so that the model is
        # only required when using this throttling mechanism.
        from tastypie.models import ApiAccess
        ApiAccess.objects.create(
            identifier=identifier,
            url=url,
            request_method=request_method,
        )

    def get_new_id(self, identifier, **kwargs):
        """
        Generates a new, more granular, identifier, and parses request method and url from kwargs
        identifier - whatever identifier is passed into the class.  Generally the username
        kwargs - can contain request method and url
        """
        url = kwargs.get('url', '')
        request_method = kwargs.get('request_method', '')
        new_id = "{0}.{1}.{2}".format(identifier,url,request_method)
        return new_id, url, request_method

    def get_user(self, identifier):
        """
        Try to get a user object from the identifier
        identifier - whatever identifier is passed into the class.  Generally the username
        """
        try:
            user = User.objects.get(username=identifier)
        except:
            user = None

        return user

    def get_rate_limit_for_user(self, user):
        """
        See if the user has a higher rate limit than the global throttle setting
        user - a user object
        """
        throttle_at = self.throttle_at
        if user is not None:
            try:
                profile = user.profile
            except SiteProfileNotAvailable:
                log.warn("No user profile available for {0}".format(user.username))
                return throttle_at
            if user.profile.throttle_at > throttle_at:
                throttle_at = user.throttle_at
        return throttle_at

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from api import OrganizationResource, UserProfileResource, CourseResource, ProblemResource, EssayResource, EssayGradeResource, UserResource, CreateUserResource, MembershipResource
from tastypie.api import Api

v1_api = Api(api_name='v1')
v1_api.register(OrganizationResource())
v1_api.register(UserProfileResource())
v1_api.register(CourseResource())
v1_api.register(ProblemResource())
v1_api.register(EssayResource())
v1_api.register(EssayGradeResource())
v1_api.register(UserResource())
v1_api.register(CreateUserResource())
v1_api.register(MembershipResource())

urlpatterns = patterns('',
    (r'^api/', include(v1_api.urls)),
)

urlpatterns+=patterns('freeform_data.views',
      url(r'^login/$','login'),
      url(r'^logout/$','logout'),
)
########NEW FILE########
__FILENAME__ = views
import django.contrib.auth
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import HttpResponse
import logging

log=logging.getLogger(__name__)

@csrf_exempt
def login(request):
    """
    Handles external login request.
    """
    if request.method != 'POST':
        return error_response('Must query using HTTP POST.')

    p = dict(request.POST.copy())
    if p == {}:
        p = request.body

    try:
        p = json.loads(p)
    except:
        pass

    if not p.has_key('username') or not p.has_key('password'):
        return error_response('Insufficient login info')
    if isinstance(p['username'], list):
        p['username'] = p['username'][0]

    if isinstance(p['password'], list):
        p['password'] = p['password'][0]
    user = django.contrib.auth.authenticate(username=p['username'], password=p['password'])
    if user is not None:
        django.contrib.auth.login(request, user)
        return success_response('Logged in.')
    else:
        return error_response('Incorrect login credentials.')

def logout(request):
    """
    Uses django auth to handle a logout request
    """
    django.contrib.auth.logout(request)
    return success_response('Goodbye')

def success_response(message):
    return generic_response(message, True)

def error_response(message):
    return generic_response(message, False)

def generic_response(message, success):
    message = {'success' : success, 'message' : message}
    return HttpResponse(json.dumps(message))

def status(request):
    """
    Returns a simple status update
    """
    return success_response("Status: OK")
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
__FILENAME__ = urls
from django.conf.urls import patterns, url

urlpatterns =patterns('frontend.views',
    url(r'^course/$','course'),
    url(r'^user/$','user'),
    url(r'^problem/$','problem'),
    url(r'^essay/$','essay'),
    url(r'^essaygrade/$','essaygrade'),
    url(r'^membership/$','membership'),
    url(r'^userprofile/$','userprofile'),
    url(r'^organization/$','organization'),
    url(r'^$','index'),
)




########NEW FILE########
__FILENAME__ = views
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
import logging
log = logging.getLogger(__name__)

def index(request):
    return render_to_response("index.html",RequestContext(request))

def userprofile(request):
    return render_to_response("models/userprofile.html", RequestContext(request))

def course(request):
    return render_to_response("models/course.html", RequestContext(request))

def problem(request):
    return render_to_response("models/problem.html", RequestContext(request))

def organization(request):
    return render_to_response("models/organization.html", RequestContext(request))

def essay(request):
    return render_to_response("models/essay.html", RequestContext(request))

def essaygrade(request):
    return render_to_response("models/essaygrade.html", RequestContext(request))

def user(request):
    return render_to_response("models/user.html", RequestContext(request))

def membership(request):
    return render_to_response("models/membership.html", RequestContext(request))
########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "discern.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'CreatedModel'
        db.create_table('ml_grading_createdmodel', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('max_score', self.gf('django.db.models.fields.IntegerField')()),
            ('prompt', self.gf('django.db.models.fields.TextField')()),
            ('problem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['freeform_data.Problem'])),
            ('target_number', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('model_relative_path', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('model_full_path', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('number_of_essays', self.gf('django.db.models.fields.IntegerField')()),
            ('cv_kappa', self.gf('django.db.models.fields.DecimalField')(default=1, max_digits=10, decimal_places=9)),
            ('cv_mean_absolute_error', self.gf('django.db.models.fields.DecimalField')(default=1, max_digits=15, decimal_places=10)),
            ('creation_succeeded', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('creation_started', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('model_stored_in_s3', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('s3_public_url', self.gf('django.db.models.fields.TextField')(default='')),
            ('s3_bucketname', self.gf('django.db.models.fields.TextField')(default='')),
        ))
        db.send_create_signal('ml_grading', ['CreatedModel'])


    def backwards(self, orm):
        # Deleting model 'CreatedModel'
        db.delete_table('ml_grading_createdmodel')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'freeform_data.course': {
            'Meta': {'object_name': 'Course'},
            'course_name': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.Organization']"}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'})
        },
        'freeform_data.organization': {
            'Meta': {'object_name': 'Organization'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'organization_name': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'organization_size': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'premium_service_subscriptions': ('django.db.models.fields.TextField', [], {'default': "'[]'"})
        },
        'freeform_data.problem': {
            'Meta': {'object_name': 'Problem'},
            'courses': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['freeform_data.Course']", 'symmetrical': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_target_scores': ('django.db.models.fields.TextField', [], {'default': "'[1]'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'number_of_additional_predictors': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'premium_feedback_models': ('django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'prompt': ('django.db.models.fields.TextField', [], {'default': "''"})
        },
        'ml_grading.createdmodel': {
            'Meta': {'object_name': 'CreatedModel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creation_started': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'creation_succeeded': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'cv_kappa': ('django.db.models.fields.DecimalField', [], {'default': '1', 'max_digits': '10', 'decimal_places': '9'}),
            'cv_mean_absolute_error': ('django.db.models.fields.DecimalField', [], {'default': '1', 'max_digits': '15', 'decimal_places': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_score': ('django.db.models.fields.IntegerField', [], {}),
            'model_full_path': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'model_relative_path': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'model_stored_in_s3': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'number_of_essays': ('django.db.models.fields.IntegerField', [], {}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['freeform_data.Problem']"}),
            'prompt': ('django.db.models.fields.TextField', [], {}),
            's3_bucketname': ('django.db.models.fields.TextField', [], {'default': "''"}),
            's3_public_url': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'target_number': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['ml_grading']
########NEW FILE########
__FILENAME__ = ml_grader
"""
The ML grader calls on the machine learning algorithm to grade a given essay
"""

from django.conf import settings
from django.db import transaction
from django.utils import timezone
import requests
import urlparse
import time
import json
import logging
import sys
import os
from path import path
import pickle
from mock import Mock
from freeform_data import helpers

log=logging.getLogger(__name__)

from freeform_data.models import Problem, Essay, EssayGrade, GraderTypes

from ml_grading.models import CreatedModel

from ml_grading import ml_grading_util
log = logging.getLogger(__name__)

if settings.FOUND_ML:
    from ease import grade
else:
    log.info("Could not find ML grading package (EASE).")
    import mock_ml_grading
    grade = Mock(grade=mock_ml_grading.grade)

#this is returned if the ML algorithm fails
RESULT_FAILURE_DICT={'success' : False, 'errors' : 'Errors!', 'confidence' : 0, 'feedback' : "", 'score' : 0}

@transaction.commit_manually
def handle_single_essay(essay):
    #Needed to ensure that the DB is not wrapped in a transaction and pulls old data
    transaction.commit()

    #strip out unicode and other characters in student response
    #Needed, or grader may potentially fail
    #TODO: Handle unicode in student responses properly
    student_response = essay.essay_text.encode('ascii', 'ignore')

    #Gets both the max scores for each target and the number of targets
    target_max_scores = json.loads(essay.problem.max_target_scores)
    target_counts = len(target_max_scores)

    target_scores=[]
    for m in xrange(0,target_counts):
        #Gets latest model for a given problem and target
        success, created_model=ml_grading_util.get_latest_created_model(essay.problem,m)

        if not success:
            results= RESULT_FAILURE_DICT
            formatted_feedback="error"
            transaction.commit()
            return False, formatted_feedback

        #Try to load the model file
        success, grader_data=load_model_file(created_model,use_full_path=False)
        if success:
            #Send to ML grading algorithm to be graded
            results = grade.grade(grader_data, student_response)
        else:
            results=RESULT_FAILURE_DICT

        #If the above fails, try using the full path in the created_model object
        if not results['success'] and not created_model.model_stored_in_s3:
            try:
                success, grader_data=load_model_file(created_model,use_full_path=True)
                if success:
                    results = grade.grade(grader_data, student_response)
                else:
                    results=RESULT_FAILURE_DICT
            except:
                error_message="Could not find a valid model file."
                log.exception(error_message)
                results=RESULT_FAILURE_DICT

        if m==0:
            final_results=results
        if results['success'] == False:
            error_message = "Unsuccessful grading: {0}".format(results)
            log.exception(error_message)
            transaction.commit()
            return False, error_message
        target_scores.append(int(results['score']))

    grader_dict = {
        'essay' : essay,
        'target_scores' : json.dumps(target_scores),
        'grader_type' : GraderTypes.machine,
        'feedback' : '',
        'annotated_text' : '',
        'premium_feedback_scores' : json.dumps([]),
        'success' :final_results['success'],
        'confidence' : final_results['confidence'],
        }

    # Create grader object in controller by posting back results
    essay_grade = EssayGrade(**grader_dict)
    essay_grade.save()
    #Update the essay so that it doesn't keep trying to re-grade
    essay.has_been_ml_graded = True
    essay.save()
    #copy permissions from the essay to the essaygrade
    helpers.copy_permissions(essay, Essay, essay_grade, EssayGrade)
    transaction.commit()
    return True, "Successfully scored!"

def load_model_file(created_model,use_full_path):
    """
    Tries to load a model file
    created_model - instance of CreatedModel (django model)
    use_full_path - boolean, indicates whether or not to use the full model path
    """
    try:
        #Uses pickle to load a local file
        if use_full_path:
            grader_data=pickle.load(file(created_model.model_full_path,"r"))
        else:
            grader_data=pickle.load(file(os.path.join(settings.ML_MODEL_PATH,created_model.model_relative_path),"r"))
        return True, grader_data
    except:
        log.exception("Could not load model file.  This is okay.")
        #Move on to trying S3
        pass

    #If we cannot load the local file, look to the cloud
    try:
        r = requests.get(created_model.s3_public_url, timeout=2)
        grader_data=pickle.loads(r.text)
    except:
        log.exception("Problem with S3 connection.")
        return False, "Could not load."

    #If we pulled down a file from the cloud, then store it locally for the future
    try:
        store_model_locally(created_model,grader_data)
    except:
        log.exception("Could not save model.  This is not a show-stopping error.")
        #This is okay if it isn't possible to save locally
        pass

    return True, grader_data

def store_model_locally(created_model,results):
    """
    Saves a model to a local file.
    created_model - instance of CreatedModel (django model)
    results - result dictionary to save
    """
    relative_model_path= created_model.model_relative_path
    full_model_path = os.path.join(settings.ML_MODEL_PATH,relative_model_path)
    try:
        ml_grading_util.dump_model_to_file(results['prompt'], results['extractor'],
            results['model'], results['text'],results['score'],full_model_path)
    except:
        error_message="Could not save model to file."
        log.exception(error_message)
        return False, error_message

    return True, "Saved file."



########NEW FILE########
__FILENAME__ = ml_grading_util
import os
from path import path
from django.conf import settings
import re
from django.utils import timezone
from django.db import transaction
import pickle
import logging

from models import CreatedModel

from boto.s3.connection import S3Connection
from boto.s3.key import Key

log=logging.getLogger(__name__)

def create_directory(model_path):
    """
    Creates a directory for a file if it does not exist
    model_path - path to a file
    """
    directory=path(model_path).dirname()
    if not os.path.exists(directory):
        os.makedirs(directory)

    return True

def get_model_path(problem, target_number=0):
    """
    Generate a path from a problem and a target number
    problem - a Problem (django model) instance
    target_number - integer, the number of the target that we are creating a model for
    """
    problem_id = problem.id

    base_path=settings.ML_MODEL_PATH
    #Ensure that directory exists, create if it doesn't
    create_directory(base_path)

    #Create a filepath from the problem id and target number that is unique across problems
    fixed_location="{0}_{1}".format(problem_id,target_number)
    #Add a time to make it unique within the scope of this problem
    fixed_location+="_"+timezone.now().strftime("%Y%m%d%H%M%S")
    full_path=os.path.join(base_path,fixed_location)
    #return relative and full path because this model may be sent to S3 and to other machines
    return fixed_location,full_path


def get_latest_created_model(problem, target_number=0):
    """
    Gets the current model file for a given problem and target
    problem - a Problem (django model) instance
    target_number - integer, the number of the target that we are looking up
    """

    #Find the latest model that meets the criteria
    created_models=CreatedModel.objects.filter(
        problem=problem,
        creation_succeeded=True,
        target_number = target_number,
    ).order_by("-created")[:1]

    if created_models.count()==0:
        return False, "No valid models for location."

    return True, created_models[0]


def check_if_model_started(problem, target_number=0):
    """
    Gets the currently active model file for a given problem and target number
    problem - a Problem (django model) instance
    target_number - integer, the number of the target that we are looking up
    """
    model_started = False
    created_models=CreatedModel.objects.filter(
        problem=problem,
        target_number=target_number,
    ).order_by("-created")[:1]

    if created_models.count()==0:
        return True, model_started, ""

    created_model = created_models[0]
    if created_model.creation_succeeded==False and created_model.creation_started==True:
        model_started = True

    return True, model_started, created_model

def upload_to_s3(string_to_upload, keyname, bucketname):
    '''
    Upload file to S3 using provided keyname.

    string_to_upload - Usually pickled data to upload
    keyname - A unique key to use for the file
    bucketname - the name of the AWS bucket to upload to
    '''
    try:
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        bucketname = str(bucketname)
        bucket = conn.create_bucket(bucketname.lower())

        k = Key(bucket)
        k.key = keyname
        k.set_contents_from_string(string_to_upload)
        public_url = k.generate_url(60*60*24*365) # URL timeout in seconds.

        return True, public_url
    except:
        return False, "Could not connect to S3."

def get_pickle_data(prompt_string, feature_ext, classifier, text, score):
    """
    Dumps data to a pickle string
    prompt string is a string containing the prompt
    feature_ext is a trained FeatureExtractor object (found in ease repo)
    classifier is a trained classifier
    model_path is the path of write out the model file to
    """
    model_file = {'prompt': prompt_string, 'extractor': feature_ext, 'model': classifier, 'text' : text, 'score' : score}
    return pickle.dumps(model_file)

def dump_model_to_file(prompt_string, feature_ext, classifier, text, score,model_path):
    """
    Dumps input data to a file.  See get_pickle_data for argument types.
    """
    model_file = {'prompt': prompt_string, 'extractor': feature_ext, 'model': classifier, 'text' : text, 'score' : score}
    pickle.dump(model_file, file=open(model_path, "w"))
########NEW FILE########
__FILENAME__ = ml_model_creation
"""
Scripts to generate a machine learning model from input data
"""

from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.utils import timezone
from django.db import transaction
import urlparse
import time
import json
import logging
import sys
import pickle
from ml_grading.models import CreatedModel
from ml_grading import ml_grading_util
from mock import Mock

log = logging.getLogger(__name__)

if settings.FOUND_ML:
    from ease import create
else:
    import mock_ml_grading
    log.warn("Could not find ML grading package (EASE). Using mock interface.")
    create = Mock(create=mock_ml_grading.create)

MAX_ESSAYS_TO_TRAIN_WITH = 1000
MIN_ESSAYS_TO_TRAIN_WITH = 10

@transaction.commit_manually
def handle_single_problem(problem):
    """
    Creates a machine learning model for a given problem.
    problem - A Problem instance (django model)
    """
    overall_success = False
    #This function is called by celery.  This ensures that the database is not stuck in an old transaction
    transaction.commit()
    #Get prompt and essays from problem (needed to train a model)
    prompt = problem.prompt
    essays = problem.essay_set.filter(essay_type="train")

    #Now, try to decode the grades from the essaygrade objects
    essay_text = []
    essay_grades = []
    essay_text_vals = essays.values('essay_text')
    for i in xrange(0,len(essays)):
        try:
            #Get an instructor score for a given essay (stored as a json string in DB) and convert to a list.  Looks like [1,1]
            #where each number denotes a score for a given target number
            essay_grades.append(json.loads(essays[i].get_instructor_scored()[0].target_scores))
            #If a grade could successfully be found, then add the essay text.  Both lists need to be in sync.
            essay_text.append(essay_text_vals[i]['essay_text'])
        except:
            log.error("Could not get latest instructor scored for {0}".format(essays[i].id))

    try:
        #This is needed to remove stray characters that could break the machine learning code
        essay_text = [et.encode('ascii', 'ignore') for et in essay_text]
    except:
        error_message = "Could not correctly encode some submissions: {0}".format(essay_text)
        log.error(error_message)
        transaction.commit()
        return False, error_message

    #Get the maximum target scores from the problem
    first_len = len(json.loads(problem.max_target_scores))
    bad_list = []
    for i in xrange(0,len(essay_grades)):
        #All of the lists within the essay grade list (ie [[[1,1],[2,2]]) need to be the same length
        if len(essay_grades[i])!=first_len:
            error_message = "Problem with an instructor scored essay! {0}".format(essay_grades)
            log.info(error_message)
            bad_list.append(i)

    essay_text = [essay_text[t] for t in xrange(0,len(essay_text)) if t not in bad_list]
    essay_grades = [essay_grades[t] for t in xrange(0,len(essay_grades)) if t not in bad_list]

    #Too many essays can take a very long time to train and eat up system resources.  Enforce a max.
    # Accuracy increases logarithmically, anyways, so you dont lose much here.
    if len(essay_text)>MAX_ESSAYS_TO_TRAIN_WITH:
        essay_text = essay_text[:MAX_ESSAYS_TO_TRAIN_WITH]
        essay_grades = essay_grades[:MAX_ESSAYS_TO_TRAIN_WITH]

    graded_sub_count = len(essay_text)
    #If there are too few essays, then don't train a model.  Need a minimum to get any kind of accuracy.
    if graded_sub_count < MIN_ESSAYS_TO_TRAIN_WITH:
        error_message = "Too few too create a model for problem {0}  need {1} only have {2}".format(problem, MIN_ESSAYS_TO_TRAIN_WITH, graded_sub_count)
        log.error(error_message)
        transaction.commit()
        return False, error_message

    #Loops through each potential target
    for m in xrange(0,first_len):
        #Gets all of the scores for this particular target
        scores = [s[m] for s in essay_grades]
        max_score = max(scores)
        log.debug("Currently on location {0} in problem {1}".format(m, problem.id))
        #Get paths to ml model from database
        relative_model_path, full_model_path= ml_grading_util.get_model_path(problem,m)
        #Get last created model for given location
        transaction.commit()
        success, latest_created_model=ml_grading_util.get_latest_created_model(problem,m)

        if success:
            sub_count_diff=graded_sub_count-latest_created_model.number_of_essays
        else:
            sub_count_diff = graded_sub_count

        #Retrain if no model exists, or every 10 graded essays.
        if not success or sub_count_diff>=10:
            log.info("Starting to create a model because none exists or it is time to retrain.")
            #Checks to see if another model creator process has started amodel for this location
            success, model_started, created_model = ml_grading_util.check_if_model_started(problem)

            #Checks to see if model was started a long time ago, and removes and retries if it was.
            if model_started:
                log.info("A model was started previously.")
                now = timezone.now()
                second_difference = (now - created_model.modified).total_seconds()
                if second_difference > settings.TIME_BEFORE_REMOVING_STARTED_MODEL:
                    log.info("Model for problem {0} started over {1} seconds ago, removing and re-attempting.".format(
                        problem.id, settings.TIME_BEFORE_REMOVING_STARTED_MODEL))
                    created_model.delete()
                    model_started = False
            #If a model has not been started, then initialize an entry in the database to prevent other threads from duplicating work
            if not model_started:
                created_model_dict_initial={
                    'max_score' : max_score,
                    'prompt' : prompt,
                    'problem' : problem,
                    'model_relative_path' : relative_model_path,
                    'model_full_path' : full_model_path,
                    'number_of_essays' : graded_sub_count,
                    'creation_succeeded': False,
                    'creation_started' : True,
                    'target_number' : m,
                    }
                created_model = CreatedModel(**created_model_dict_initial)
                created_model.save()
                transaction.commit()

                if not isinstance(prompt, basestring):
                    try:
                        prompt = str(prompt)
                    except:
                        prompt = ""
                prompt = prompt.encode('ascii', 'ignore')

                #Call on the ease repo to create a model
                results = create.create(essay_text, scores, prompt)

                scores = [int(score_item) for score_item in scores]
                #Add in needed stuff that ml creator does not pass back
                results.update({
                    'model_path' : full_model_path,
                    'relative_model_path' : relative_model_path
                })

                #Try to create model if ml model creator was successful
                overall_success = results['success']
                if results['success']:
                    try:
                        success, s3_public_url = save_model_file(results,settings.USE_S3_TO_STORE_MODELS)
                        results.update({'s3_public_url' : s3_public_url, 'success' : success})
                        if not success:
                            results['errors'].append("Could not save model.")
                    except:
                        results['errors'].append("Could not save model.")
                        results['s3_public_url'] = ""
                        log.exception("Problem saving ML model.")

                created_model_dict_final={
                    'cv_kappa' : results['cv_kappa'],
                    'cv_mean_absolute_error' : results['cv_mean_absolute_error'],
                    'creation_succeeded': results['success'],
                    'creation_started' : False,
                    's3_public_url' : results['s3_public_url'],
                    'model_stored_in_s3' : settings.USE_S3_TO_STORE_MODELS,
                    's3_bucketname' : str(settings.S3_BUCKETNAME),
                    'model_relative_path' : relative_model_path,
                    'model_full_path' : full_model_path,
                    }

                transaction.commit()
                try:
                    CreatedModel.objects.filter(pk=created_model.pk).update(**created_model_dict_final)
                except:
                    log.error("ModelCreator creation failed.  Error: {0}".format(id))

                log.debug("Location: {0} Creation Status: {1} Errors: {2}".format(
                    full_model_path,
                    results['success'],
                    results['errors'],
                ))
    transaction.commit()
    return overall_success, "Creation succeeded."

def save_model_file(results, save_to_s3):
    """
    Saves a machine learning model to file or uploads to S3 as needed
    results - Dictionary of results from ML
    save_to_s3 - Boolean indicating whether or not to upload results
    """
    success=False
    if save_to_s3:
        pickled_model=ml_grading_util.get_pickle_data(results['prompt'], results['feature_ext'],
            results['classifier'], results['text'],
            results['score'])
        success, s3_public_url=ml_grading_util.upload_to_s3(pickled_model, results['relative_model_path'], str(settings.S3_BUCKETNAME))

    try:
        ml_grading_util.dump_model_to_file(results['prompt'], results['feature_ext'],
            results['classifier'], results['text'],results['score'],results['model_path'])
        if success:
            return True, s3_public_url
        else:
            return True, "Saved model to file."
    except:
        return False, "Could not save model."
########NEW FILE########
__FILENAME__ = mock_ml_grading
def grade(grader_data,student_response):
    result_dict = {'errors': [],'tests': [],'score': 0, 'feedback' : "", 'success' : False, 'confidence' : 1}
    return result_dict

def create(essay_text, scores, prompt):
    result_dict = {'errors': [],'success' : False, 'cv_kappa' : 0, 'cv_mean_absolute_error': 0,
     'feature_ext' : "", 'classifier' : "", 'algorithm' : "C",
     'score' : scores, 'text' : essay_text, 'prompt' : prompt, 's3_public_url' : 'blah'}
    return result_dict
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils import timezone
import json

CHARFIELD_LEN_SMALL=128
CHARFIELD_LEN_LONG = 1024

class CreatedModel(models.Model):
    #When it was created/modified
    modified=models.DateTimeField(auto_now=True)
    created=models.DateTimeField(auto_now_add=True)

    #Properties of the problem the model was created with
    max_score=models.IntegerField()
    prompt=models.TextField()
    problem = models.ForeignKey("freeform_data.Problem")
    target_number = models.IntegerField(default=0)

    #Properties of the model file
    model_relative_path=models.CharField(max_length=CHARFIELD_LEN_LONG)
    model_full_path=models.CharField(max_length=CHARFIELD_LEN_LONG)

    #Properties of the model itself
    number_of_essays=models.IntegerField()

    #CV is cross-validation, which is a statistical technique that ensures that
    #the models are trained on one part of the data and predicted on another.
    #so the kappa and error measurements are not biased by the data that was used to create the models
    #being used to also evaluate them. (ie, this is "True" error)
    #Kappa is interrater agreement-closer to 1 is better.
    #If the actual scores and the predicted scores perfectly agree, kappa will be 1.
    cv_kappa=models.DecimalField(max_digits=10,decimal_places=9, default=1)

    #Mean absolute error is mean(abs(actual_score-predicted_score))
    #A mean absolute error of .5 means that, on average, the predicted score is +/- .5 points from the actual score
    cv_mean_absolute_error=models.DecimalField(max_digits=15,decimal_places=10, default=1)

    creation_succeeded=models.BooleanField(default=False)
    creation_started =models.BooleanField(default=False)

    #Amazon S3 stuff if we do use it
    model_stored_in_s3=models.BooleanField(default=False)
    s3_public_url=models.TextField(default="")
    s3_bucketname=models.TextField(default="")

    def get_submission_ids_used(self):
        """
        Returns a list of submission ids of essays used to create the model.
        Output:
            Boolean success, list of ids/error message as appropriate
        """

        try:
            submission_id_list=json.loads(self.submission_ids_used)
        except:
            return False, "No essays used or not in json format."

        return True, submission_id_list
########NEW FILE########
__FILENAME__ = tasks
"""
Used by celery to decide what tasks it needs to do
"""

from celery import task
import logging
from celery.task import periodic_task
from freeform_data.models import Problem, Essay
from datetime import timedelta
from django.conf import settings
from ml_grading.ml_model_creation import handle_single_problem, MIN_ESSAYS_TO_TRAIN_WITH
from ml_grading.ml_grader import handle_single_essay
from django.db.models import Q, Count
from django.db import transaction
from freeform_data.tasks import single_instance_task
from django.core.cache import cache

log=logging.getLogger(__name__)

@periodic_task(run_every=timedelta(seconds=settings.TIME_BETWEEN_ML_CREATOR_CHECKS))
@single_instance_task(settings.MODEL_CREATION_CACHE_LOCK_TIME)
def create_ml_models():
    """
    Called periodically by celery.  Loops through each problem and tries to create a model for it.
    """
    transaction.commit_unless_managed()
    problems = Problem.objects.all()
    for problem in problems:
        create_ml_models_single_problem(problem)

@task()
def create_ml_models_single_problem(problem):
    """
    Celery task called by create_ml_models to create a single model
    """
    transaction.commit_unless_managed()
    lock_id = "celery-model-creation-{0}".format(problem.id)
    acquire_lock = lambda: cache.add(lock_id, "true", settings.MODEL_CREATION_CACHE_LOCK_TIME)
    release_lock = lambda: cache.delete(lock_id)
    if acquire_lock():
        try:
            handle_single_problem(problem)
        finally:
            release_lock()

@periodic_task(run_every=timedelta(seconds=settings.TIME_BETWEEN_ML_GRADER_CHECKS))
@single_instance_task(settings.GRADING_CACHE_LOCK_TIME)
def grade_ml():
    """
    Called periodically by celery.  Loops through each problem, sees if there are enough essays for ML grading to work,
    and then calls the ml grader if there are.
    """
    transaction.commit_unless_managed()
    #TODO: Add in some checking to ensure that count is of instructor graded essays only
    problems = Problem.objects.all().annotate(essay_count=Count('essay')).filter(essay_count__gt=(MIN_ESSAYS_TO_TRAIN_WITH-1))
    for problem in problems:
        grade_ml_essays(problem)

@task()
def grade_ml_essays(problem):
    """
    Called by grade_ml.  Handles a single grading task for a single essay.
    """
    transaction.commit_unless_managed()
    lock_id = "celery-essay-grading-{0}".format(problem.id)
    acquire_lock = lambda: cache.add(lock_id, "true", settings.GRADING_CACHE_LOCK_TIME)
    release_lock = lambda: cache.delete(lock_id)
    if acquire_lock():
        try:
            essays = Essay.objects.filter(problem=problem, has_been_ml_graded=False)
            #TODO: Grade essays in batches so ml model doesn't have to be loaded every single time (or cache the model files)
            for essay in essays:
                handle_single_essay(essay)
        finally:
            release_lock()
########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import unittest


class SimpleTest(unittest.TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = admin
from django.conf import settings
from django.contrib import admin


if 'django.contrib.auth' in settings.INSTALLED_APPS:
    from tastypie.models import ApiKey

    class ApiKeyInline(admin.StackedInline):
        model = ApiKey
        extra = 0

    ABSTRACT_APIKEY = getattr(settings, 'TASTYPIE_ABSTRACT_APIKEY', False)

    if ABSTRACT_APIKEY and not isinstance(ABSTRACT_APIKEY, bool):
        raise TypeError("'TASTYPIE_ABSTRACT_APIKEY' must be either 'True' "
                        "or 'False'.")
            
    if not ABSTRACT_APIKEY:
        admin.site.register(ApiKey)

########NEW FILE########
__FILENAME__ = api
import warnings
try:
    from django.conf.urls import url, patterns, include
except ImportError: # Django < 1.4
    from django.conf.urls.defaults import url, patterns, include
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseBadRequest
from tastypie.exceptions import NotRegistered, BadRequest
from tastypie.serializers import Serializer
from tastypie.utils import trailing_slash, is_valid_jsonp_callback_value
from tastypie.utils.mime import determine_format, build_content_type


class Api(object):
    """
    Implements a registry to tie together the various resources that make up
    an API.

    Especially useful for navigation, HATEOAS and for providing multiple
    versions of your API.

    Optionally supplying ``api_name`` allows you to name the API. Generally,
    this is done with version numbers (i.e. ``v1``, ``v2``, etc.) but can
    be named any string.
    """
    def __init__(self, api_name="v1", serializer_class=Serializer):
        self.api_name = api_name
        self._registry = {}
        self._canonicals = {}
        self.serializer = serializer_class()

    def register(self, resource, canonical=True):
        """
        Registers an instance of a ``Resource`` subclass with the API.

        Optionally accept a ``canonical`` argument, which indicates that the
        resource being registered is the canonical variant. Defaults to
        ``True``.
        """
        resource_name = getattr(resource._meta, 'resource_name', None)

        if resource_name is None:
            raise ImproperlyConfigured("Resource %r must define a 'resource_name'." % resource)

        self._registry[resource_name] = resource

        if canonical is True:
            if resource_name in self._canonicals:
                warnings.warn("A new resource '%r' is replacing the existing canonical URL for '%s'." % (resource, resource_name), Warning, stacklevel=2)

            self._canonicals[resource_name] = resource
            # TODO: This is messy, but makes URI resolution on FK/M2M fields
            #       work consistently.
            resource._meta.api_name = self.api_name
            resource.__class__.Meta.api_name = self.api_name

    def unregister(self, resource_name):
        """
        If present, unregisters a resource from the API.
        """
        if resource_name in self._registry:
            del(self._registry[resource_name])

        if resource_name in self._canonicals:
            del(self._canonicals[resource_name])

    def canonical_resource_for(self, resource_name):
        """
        Returns the canonical resource for a given ``resource_name``.
        """
        if resource_name in self._canonicals:
            return self._canonicals[resource_name]

        raise NotRegistered("No resource was registered as canonical for '%s'." % resource_name)

    def wrap_view(self, view):
        def wrapper(request, *args, **kwargs):
            try:
                return getattr(self, view)(request, *args, **kwargs)
            except BadRequest:
                return HttpResponseBadRequest()
        return wrapper

    def override_urls(self):
        """
        Deprecated. Will be removed by v1.0.0. Please use ``prepend_urls`` instead.
        """
        return []

    def prepend_urls(self):
        """
        A hook for adding your own URLs or matching before the default URLs.
        """
        return []

    @property
    def urls(self):
        """
        Provides URLconf details for the ``Api`` and all registered
        ``Resources`` beneath it.
        """
        pattern_list = [
            url(r"^(?P<api_name>%s)%s$" % (self.api_name, trailing_slash()), self.wrap_view('top_level'), name="api_%s_top_level" % self.api_name),
        ]

        for name in sorted(self._registry.keys()):
            self._registry[name].api_name = self.api_name
            pattern_list.append((r"^(?P<api_name>%s)/" % self.api_name, include(self._registry[name].urls)))

        urlpatterns = self.prepend_urls()

        overridden_urls = self.override_urls()
        if overridden_urls:
            warnings.warn("'override_urls' is a deprecated method & will be removed by v1.0.0. Please rename your method to ``prepend_urls``.")
            urlpatterns += overridden_urls

        urlpatterns += patterns('',
            *pattern_list
        )
        return urlpatterns

    def top_level(self, request, api_name=None):
        """
        A view that returns a serialized list of all resources registers
        to the ``Api``. Useful for discovery.
        """
        available_resources = {}

        if api_name is None:
            api_name = self.api_name

        for name in sorted(self._registry.keys()):
            available_resources[name] = {
                'list_endpoint': self._build_reverse_url("api_dispatch_list", kwargs={
                    'api_name': api_name,
                    'resource_name': name,
                }),
                'schema': self._build_reverse_url("api_get_schema", kwargs={
                    'api_name': api_name,
                    'resource_name': name,
                }),
            }

        desired_format = determine_format(request, self.serializer)

        options = {}

        if 'text/javascript' in desired_format:
            callback = request.GET.get('callback', 'callback')

            if not is_valid_jsonp_callback_value(callback):
                raise BadRequest('JSONP callback name is invalid.')

            options['callback'] = callback

        serialized = self.serializer.serialize(available_resources, desired_format, options)
        return HttpResponse(content=serialized, content_type=build_content_type(desired_format))

    def _build_reverse_url(self, name, args=None, kwargs=None):
        """
        A convenience hook for overriding how URLs are built.

        See ``NamespacedApi._build_reverse_url`` for an example.
        """
        return reverse(name, args=args, kwargs=kwargs)


class NamespacedApi(Api):
    """
    An API subclass that respects Django namespaces.
    """
    def __init__(self, api_name="v1", urlconf_namespace=None, **kwargs):
        super(NamespacedApi, self).__init__(api_name=api_name, **kwargs)
        self.urlconf_namespace = urlconf_namespace

    def register(self, resource, canonical=True):
        super(NamespacedApi, self).register(resource, canonical=canonical)

        if canonical is True:
            # Plop in the namespace here as well.
            resource._meta.urlconf_namespace = self.urlconf_namespace

    def _build_reverse_url(self, name, args=None, kwargs=None):
        namespaced = "%s:%s" % (self.urlconf_namespace, name)
        return reverse(namespaced, args=args, kwargs=kwargs)

########NEW FILE########
__FILENAME__ = authentication
import base64
import hmac
import time
import uuid

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.exceptions import ImproperlyConfigured
from django.middleware.csrf import _sanitize_token, constant_time_compare
from django.utils.http import same_origin
from django.utils.translation import ugettext as _
from tastypie.http import HttpUnauthorized
from tastypie.compat import User, username_field

try:
    from hashlib import sha1
except ImportError:
    import sha
    sha1 = sha.sha

try:
    import python_digest
except ImportError:
    python_digest = None

try:
    import oauth2
except ImportError:
    oauth2 = None

try:
    import oauth_provider
except ImportError:
    oauth_provider = None


class Authentication(object):
    """
    A simple base class to establish the protocol for auth.

    By default, this indicates the user is always authenticated.
    """
    def __init__(self, require_active=True):
        self.require_active = require_active

    def is_authenticated(self, request, **kwargs):
        """
        Identifies if the user is authenticated to continue or not.

        Should return either ``True`` if allowed, ``False`` if not or an
        ``HttpResponse`` if you need something custom.
        """
        return True

    def get_identifier(self, request):
        """
        Provides a unique string identifier for the requestor.

        This implementation returns a combination of IP address and hostname.
        """
        return "%s_%s" % (request.META.get('REMOTE_ADDR', 'noaddr'), request.META.get('REMOTE_HOST', 'nohost'))

    def check_active(self, user):
        """
        Ensures the user has an active account.

        Optimized for the ``django.contrib.auth.models.User`` case.
        """
        if not self.require_active:
            # Ignore & move on.
            return True

        return user.is_active


class BasicAuthentication(Authentication):
    """
    Handles HTTP Basic auth against a specific auth backend if provided,
    or against all configured authentication backends using the
    ``authenticate`` method from ``django.contrib.auth``.

    Optional keyword arguments:

    ``backend``
        If specified, use a specific ``django.contrib.auth`` backend instead
        of checking all backends specified in the ``AUTHENTICATION_BACKENDS``
        setting.
    ``realm``
        The realm to use in the ``HttpUnauthorized`` response.  Default:
        ``django-tastypie``.
    """
    def __init__(self, backend=None, realm='django-tastypie', **kwargs):
        super(BasicAuthentication, self).__init__(**kwargs)
        self.backend = backend
        self.realm = realm

    def _unauthorized(self):
        response = HttpUnauthorized()
        # FIXME: Sanitize realm.
        response['WWW-Authenticate'] = 'Basic Realm="%s"' % self.realm
        return response

    def is_authenticated(self, request, **kwargs):
        """
        Checks a user's basic auth credentials against the current
        Django auth backend.

        Should return either ``True`` if allowed, ``False`` if not or an
        ``HttpResponse`` if you need something custom.
        """
        if not request.META.get('HTTP_AUTHORIZATION'):
            return self._unauthorized()

        try:
            (auth_type, data) = request.META['HTTP_AUTHORIZATION'].split()
            if auth_type.lower() != 'basic':
                return self._unauthorized()
            user_pass = base64.b64decode(data)
        except:
            return self._unauthorized()

        bits = user_pass.split(':', 1)

        if len(bits) != 2:
            return self._unauthorized()

        if self.backend:
            user = self.backend.authenticate(username=bits[0], password=bits[1])
        else:
            user = authenticate(username=bits[0], password=bits[1])

        if user is None:
            return self._unauthorized()

        if not self.check_active(user):
            return False

        request.user = user
        return True

    def get_identifier(self, request):
        """
        Provides a unique string identifier for the requestor.

        This implementation returns the user's basic auth username.
        """
        return request.META.get('REMOTE_USER', 'nouser')


class ApiKeyAuthentication(Authentication):
    """
    Handles API key auth, in which a user provides a username & API key.

    Uses the ``ApiKey`` model that ships with tastypie. If you wish to use
    a different model, override the ``get_key`` method to perform the key check
    as suits your needs.
    """
    def _unauthorized(self):
        return HttpUnauthorized()

    def extract_credentials(self, request):
        if request.META.get('HTTP_AUTHORIZATION') and request.META['HTTP_AUTHORIZATION'].lower().startswith('apikey '):
            (auth_type, data) = request.META['HTTP_AUTHORIZATION'].split()

            if auth_type.lower() != 'apikey':
                raise ValueError("Incorrect authorization header.")

            username, api_key = data.split(':', 1)
        else:
            username = request.GET.get('username') or request.POST.get('username')
            api_key = request.GET.get('api_key') or request.POST.get('api_key')

        return username, api_key

    def is_authenticated(self, request, **kwargs):
        """
        Finds the user and checks their API key.

        Should return either ``True`` if allowed, ``False`` if not or an
        ``HttpResponse`` if you need something custom.
        """
        from tastypie.compat import User

        try:
            username, api_key = self.extract_credentials(request)
        except ValueError:
            return self._unauthorized()

        if not username or not api_key:
            return self._unauthorized()

        try:
            lookup_kwargs = {username_field: username}
            user = User.objects.get(**lookup_kwargs)
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            return self._unauthorized()

        if not self.check_active(user):
            return False

        key_auth_check = self.get_key(user, api_key)
        if key_auth_check and not isinstance(key_auth_check, HttpUnauthorized):
            request.user = user

        return key_auth_check

    def get_key(self, user, api_key):
        """
        Attempts to find the API key for the user. Uses ``ApiKey`` by default
        but can be overridden.
        """
        from tastypie.models import ApiKey

        try:
            ApiKey.objects.get(user=user, key=api_key)
        except ApiKey.DoesNotExist:
            return self._unauthorized()

        return True

    def get_identifier(self, request):
        """
        Provides a unique string identifier for the requestor.

        This implementation returns the user's username.
        """
        username, api_key = self.extract_credentials(request)
        return username or 'nouser'


class SessionAuthentication(Authentication):
    """
    An authentication mechanism that piggy-backs on Django sessions.

    This is useful when the API is talking to Javascript on the same site.
    Relies on the user being logged in through the standard Django login
    setup.

    Requires a valid CSRF token.
    """
    def is_authenticated(self, request, **kwargs):
        """
        Checks to make sure the user is logged in & has a Django session.
        """
        # Cargo-culted from Django 1.3/1.4's ``django/middleware/csrf.py``.
        # We can't just use what's there, since the return values will be
        # wrong.
        # We also can't risk accessing ``request.POST``, which will break with
        # the serialized bodies.
        if request.method in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            return request.user.is_authenticated()

        if getattr(request, '_dont_enforce_csrf_checks', False):
            return request.user.is_authenticated()

        csrf_token = _sanitize_token(request.COOKIES.get(settings.CSRF_COOKIE_NAME, ''))

        if request.is_secure():
            referer = request.META.get('HTTP_REFERER')

            if referer is None:
                return False

            good_referer = 'https://%s/' % request.get_host()

            if not same_origin(referer, good_referer):
                return False

        request_csrf_token = request.META.get('HTTP_X_CSRFTOKEN', '')

        if not constant_time_compare(request_csrf_token, csrf_token):
            return False

        return request.user.is_authenticated()

    def get_identifier(self, request):
        """
        Provides a unique string identifier for the requestor.

        This implementation returns the user's username.
        """
        return getattr(request.user, username_field)


class DigestAuthentication(Authentication):
    """
    Handles HTTP Digest auth against a specific auth backend if provided,
    or against all configured authentication backends using the
    ``authenticate`` method from ``django.contrib.auth``. However, instead of
    the user's password, their API key should be used.

    Optional keyword arguments:

    ``backend``
        If specified, use a specific ``django.contrib.auth`` backend instead
        of checking all backends specified in the ``AUTHENTICATION_BACKENDS``
        setting.
    ``realm``
        The realm to use in the ``HttpUnauthorized`` response.  Default:
        ``django-tastypie``.
    """
    def __init__(self, backend=None, realm='django-tastypie', **kwargs):
        super(DigestAuthentication, self).__init__(**kwargs)
        self.backend = backend
        self.realm = realm

        if python_digest is None:
            raise ImproperlyConfigured("The 'python_digest' package could not be imported. It is required for use with the 'DigestAuthentication' class.")

    def _unauthorized(self):
        response = HttpUnauthorized()
        new_uuid = uuid.uuid4()
        opaque = hmac.new(str(new_uuid), digestmod=sha1).hexdigest()
        response['WWW-Authenticate'] = python_digest.build_digest_challenge(time.time(), getattr(settings, 'SECRET_KEY', ''), self.realm, opaque, False)
        return response

    def is_authenticated(self, request, **kwargs):
        """
        Finds the user and checks their API key.

        Should return either ``True`` if allowed, ``False`` if not or an
        ``HttpResponse`` if you need something custom.
        """
        if not request.META.get('HTTP_AUTHORIZATION'):
            return self._unauthorized()

        try:
            (auth_type, data) = request.META['HTTP_AUTHORIZATION'].split(' ', 1)

            if auth_type.lower() != 'digest':
                return self._unauthorized()
        except:
            return self._unauthorized()

        digest_response = python_digest.parse_digest_credentials(request.META['HTTP_AUTHORIZATION'])

        # FIXME: Should the nonce be per-user?
        if not python_digest.validate_nonce(digest_response.nonce, getattr(settings, 'SECRET_KEY', '')):
            return self._unauthorized()

        user = self.get_user(digest_response.username)
        api_key = self.get_key(user)

        if user is False or api_key is False:
            return self._unauthorized()

        expected = python_digest.calculate_request_digest(
            request.method,
            python_digest.calculate_partial_digest(digest_response.username, self.realm, api_key),
            digest_response)

        if not digest_response.response == expected:
            return self._unauthorized()

        if not self.check_active(user):
            return False

        request.user = user
        return True

    def get_user(self, username):
        try:
            lookup_kwargs = {username_field: username}
            user = User.objects.get(**lookup_kwargs)
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            return False

        return user

    def get_key(self, user):
        """
        Attempts to find the API key for the user. Uses ``ApiKey`` by default
        but can be overridden.

        Note that this behaves differently than the ``ApiKeyAuthentication``
        method of the same name.
        """
        from tastypie.models import ApiKey

        try:
            key = ApiKey.objects.get(user=user)
        except ApiKey.DoesNotExist:
            return False

        return key.key

    def get_identifier(self, request):
        """
        Provides a unique string identifier for the requestor.

        This implementation returns the user's username.
        """
        if hasattr(request, 'user'):
            if hasattr(request.user, 'username'):
                return request.user.username

        return 'nouser'


class OAuthAuthentication(Authentication):
    """
    Handles OAuth, which checks a user's credentials against a separate service.
    Currently verifies against OAuth 1.0a services.

    This does *NOT* provide OAuth authentication in your API, strictly
    consumption.
    """
    def __init__(self, **kwargs):
        super(OAuthAuthentication, self).__init__(**kwargs)

        if oauth2 is None:
            raise ImproperlyConfigured("The 'python-oauth2' package could not be imported. It is required for use with the 'OAuthAuthentication' class.")

        if oauth_provider is None:
            raise ImproperlyConfigured("The 'django-oauth-plus' package could not be imported. It is required for use with the 'OAuthAuthentication' class.")

    def is_authenticated(self, request, **kwargs):
        from oauth_provider.store import store, InvalidTokenError

        if self.is_valid_request(request):
            oauth_request = oauth_provider.utils.get_oauth_request(request)
            consumer = store.get_consumer(request, oauth_request, oauth_request.get_parameter('oauth_consumer_key'))

            try:
                token = store.get_access_token(request, oauth_request, consumer, oauth_request.get_parameter('oauth_token'))
            except oauth_provider.store.InvalidTokenError:
                return oauth_provider.utils.send_oauth_error(oauth2.Error(_('Invalid access token: %s') % oauth_request.get_parameter('oauth_token')))

            try:
                self.validate_token(request, consumer, token)
            except oauth2.Error, e:
                return oauth_provider.utils.send_oauth_error(e)

            if consumer and token:
                if not self.check_active(token.user):
                    return False

                request.user = token.user
                return True

            return oauth_provider.utils.send_oauth_error(oauth2.Error(_('You are not allowed to access this resource.')))

        return oauth_provider.utils.send_oauth_error(oauth2.Error(_('Invalid request parameters.')))

    def is_in(self, params):
        """
        Checks to ensure that all the OAuth parameter names are in the
        provided ``params``.
        """
        from oauth_provider.consts import OAUTH_PARAMETERS_NAMES

        for param_name in OAUTH_PARAMETERS_NAMES:
            if param_name not in params:
                return False

        return True

    def is_valid_request(self, request):
        """
        Checks whether the required parameters are either in the HTTP
        ``Authorization`` header sent by some clients (the preferred method
        according to OAuth spec) or fall back to ``GET/POST``.
        """
        auth_params = request.META.get("HTTP_AUTHORIZATION", [])
        return self.is_in(auth_params) or self.is_in(request.REQUEST)

    def validate_token(self, request, consumer, token):
        oauth_server, oauth_request = oauth_provider.utils.initialize_server_request(request)
        return oauth_server.verify_request(oauth_request, consumer, token)


class MultiAuthentication(object):
    """
    An authentication backend that tries a number of backends in order.
    """
    def __init__(self, *backends, **kwargs):
        super(MultiAuthentication, self).__init__(**kwargs)
        self.backends = backends

    def is_authenticated(self, request, **kwargs):
        """
        Identifies if the user is authenticated to continue or not.

        Should return either ``True`` if allowed, ``False`` if not or an
        ``HttpResponse`` if you need something custom.
        """
        unauthorized = False

        for backend in self.backends:
            check = backend.is_authenticated(request, **kwargs)

            if check:
                if isinstance(check, HttpUnauthorized):
                    unauthorized = unauthorized or check
                else:
                    request._authentication_backend = backend
                    return check

        return unauthorized

    def get_identifier(self, request):
        """
        Provides a unique string identifier for the requestor.

        This implementation returns a combination of IP address and hostname.
        """
        try:
            return request._authentication_backend.get_identifier(request)
        except AttributeError:
            return 'nouser'

########NEW FILE########
__FILENAME__ = authorization
from tastypie.exceptions import TastypieError, Unauthorized


class Authorization(object):
    """
    A base class that provides no permissions checking.
    """
    def __get__(self, instance, owner):
        """
        Makes ``Authorization`` a descriptor of ``ResourceOptions`` and creates
        a reference to the ``ResourceOptions`` object that may be used by
        methods of ``Authorization``.
        """
        self.resource_meta = instance
        return self

    def apply_limits(self, request, object_list):
        """
        Deprecated.

        FIXME: REMOVE BEFORE 1.0
        """
        raise TastypieError("Authorization classes no longer support `apply_limits`. Please update to using `read_list`.")

    def read_list(self, object_list, bundle):
        """
        Returns a list of all the objects a user is allowed to read.

        Should return an empty list if none are allowed.

        Returns the entire list by default.
        """
        return object_list

    def read_detail(self, object_list, bundle):
        """
        Returns either ``True`` if the user is allowed to read the object in
        question or throw ``Unauthorized`` if they are not.

        Returns ``True`` by default.
        """
        return True

    def create_list(self, object_list, bundle):
        """
        Unimplemented, as Tastypie never creates entire new lists, but
        present for consistency & possible extension.
        """
        raise NotImplementedError("Tastypie has no way to determine if all objects should be allowed to be created.")

    def create_detail(self, object_list, bundle):
        """
        Returns either ``True`` if the user is allowed to create the object in
        question or throw ``Unauthorized`` if they are not.

        Returns ``True`` by default.
        """
        return True

    def update_list(self, object_list, bundle):
        """
        Returns a list of all the objects a user is allowed to update.

        Should return an empty list if none are allowed.

        Returns the entire list by default.
        """
        return object_list

    def update_detail(self, object_list, bundle):
        """
        Returns either ``True`` if the user is allowed to update the object in
        question or throw ``Unauthorized`` if they are not.

        Returns ``True`` by default.
        """
        return True

    def delete_list(self, object_list, bundle):
        """
        Returns a list of all the objects a user is allowed to delete.

        Should return an empty list if none are allowed.

        Returns the entire list by default.
        """
        return object_list

    def delete_detail(self, object_list, bundle):
        """
        Returns either ``True`` if the user is allowed to delete the object in
        question or throw ``Unauthorized`` if they are not.

        Returns ``True`` by default.
        """
        return True


class ReadOnlyAuthorization(Authorization):
    """
    Default Authentication class for ``Resource`` objects.

    Only allows ``GET`` requests.
    """
    def read_list(self, object_list, bundle):
        return object_list

    def read_detail(self, object_list, bundle):
        return True

    def create_list(self, object_list, bundle):
        return []

    def create_detail(self, object_list, bundle):
        raise Unauthorized("You are not allowed to access that resource.")

    def update_list(self, object_list, bundle):
        return []

    def update_detail(self, object_list, bundle):
        raise Unauthorized("You are not allowed to access that resource.")

    def delete_list(self, object_list, bundle):
        return []

    def delete_detail(self, object_list, bundle):
        raise Unauthorized("You are not allowed to access that resource.")


class DjangoAuthorization(Authorization):
    """
    Uses permission checking from ``django.contrib.auth`` to map
    ``POST / PUT / DELETE / PATCH`` to their equivalent Django auth
    permissions.

    Both the list & detail variants simply check the model they're based
    on, as that's all the more granular Django's permission setup gets.
    """
    def base_checks(self, request, model_klass):
        # If it doesn't look like a model, we can't check permissions.
        if not model_klass or not getattr(model_klass, '_meta', None):
            return False

        # User must be logged in to check permissions.
        if not hasattr(request, 'user'):
            return False

        return model_klass

    def read_list(self, object_list, bundle):
        klass = self.base_checks(bundle.request, object_list.model)

        if klass is False:
            return []

        # GET-style methods are always allowed.
        return object_list

    def read_detail(self, object_list, bundle):
        klass = self.base_checks(bundle.request, bundle.obj.__class__)

        if klass is False:
            raise Unauthorized("You are not allowed to access that resource.")

        # GET-style methods are always allowed.
        return True

    def create_list(self, object_list, bundle):
        klass = self.base_checks(bundle.request, object_list.model)

        if klass is False:
            return []

        permission = '%s.add_%s' % (klass._meta.app_label, klass._meta.module_name)

        if not bundle.request.user.has_perm(permission):
            return []

        return object_list

    def create_detail(self, object_list, bundle):
        klass = self.base_checks(bundle.request, bundle.obj.__class__)

        if klass is False:
            raise Unauthorized("You are not allowed to access that resource.")

        permission = '%s.add_%s' % (klass._meta.app_label, klass._meta.module_name)

        if not bundle.request.user.has_perm(permission):
            raise Unauthorized("You are not allowed to access that resource.")

        return True

    def update_list(self, object_list, bundle):
        klass = self.base_checks(bundle.request, object_list.model)

        if klass is False:
            return []

        permission = '%s.change_%s' % (klass._meta.app_label, klass._meta.module_name)

        if not bundle.request.user.has_perm(permission):
            return []

        return object_list

    def update_detail(self, object_list, bundle):
        klass = self.base_checks(bundle.request, bundle.obj.__class__)

        if klass is False:
            raise Unauthorized("You are not allowed to access that resource.")

        permission = '%s.change_%s' % (klass._meta.app_label, klass._meta.module_name)

        if not bundle.request.user.has_perm(permission):
            raise Unauthorized("You are not allowed to access that resource.")

        return True

    def delete_list(self, object_list, bundle):
        klass = self.base_checks(bundle.request, object_list.model)

        if klass is False:
            return []

        permission = '%s.delete_%s' % (klass._meta.app_label, klass._meta.module_name)

        if not bundle.request.user.has_perm(permission):
            return []

        return object_list

    def delete_detail(self, object_list, bundle):
        klass = self.base_checks(bundle.request, bundle.obj.__class__)

        if klass is False:
            raise Unauthorized("You are not allowed to access that resource.")

        permission = '%s.delete_%s' % (klass._meta.app_label, klass._meta.module_name)

        if not bundle.request.user.has_perm(permission):
            raise Unauthorized("You are not allowed to access that resource.")

        return True

########NEW FILE########
__FILENAME__ = bundle
from django.http import HttpRequest


# In a separate file to avoid circular imports...
class Bundle(object):
    """
    A small container for instances and converted data for the
    ``dehydrate/hydrate`` cycle.

    Necessary because the ``dehydrate/hydrate`` cycle needs to access data at
    different points.
    """
    def __init__(self,
                 obj=None,
                 data=None,
                 request=None,
                 related_obj=None,
                 related_name=None,
                 objects_saved=None,
                 related_objects_to_save=None,
                 ):
        self.obj = obj
        self.data = data or {}
        self.request = request or HttpRequest()
        self.related_obj = related_obj
        self.related_name = related_name
        self.errors = {}
        self.objects_saved = objects_saved or set()
        self.related_objects_to_save = related_objects_to_save or {}

    def __repr__(self):
        return "<Bundle for obj: '%s' and with data: '%s'>" % (self.obj, self.data)

########NEW FILE########
__FILENAME__ = cache
from django.core.cache import cache


class NoCache(object):
    """
    A simplified, swappable base class for caching.

    Does nothing save for simulating the cache API.
    """
    def __init__(self, varies=None, *args, **kwargs):
        """
        Optionally accepts a ``varies`` list that will be used in the
        Vary header. Defaults to ["Accept"].
        """
        super(NoCache, self).__init__(*args, **kwargs)
        self.varies = varies

        if self.varies is None:
            self.varies = ["Accept"]

    def get(self, key):
        """
        Always returns ``None``.
        """
        return None

    def set(self, key, value, timeout=60):
        """
        No-op for setting values in the cache.
        """
        pass

    def cacheable(self, request, response):
        """
        Returns True or False if the request -> response is capable of being
        cached.
        """
        return bool(request.method == "GET" and response.status_code == 200)

    def cache_control(self):
        """
        No-op for returning values for cache-control
        """
        return {
            'no_cache': True,
        }


class SimpleCache(NoCache):
    """
    Uses Django's current ``CACHE_BACKEND`` to store cached data.
    """

    def __init__(self, timeout=60, public=None, private=None, *args, **kwargs):
        """
        Optionally accepts a ``timeout`` in seconds for the resource's cache.
        Defaults to ``60`` seconds.
        """
        super(SimpleCache, self).__init__(*args, **kwargs)
        self.timeout = timeout
        self.public = public
        self.private = private

    def get(self, key):
        """
        Gets a key from the cache. Returns ``None`` if the key is not found.
        """
        return cache.get(key)

    def set(self, key, value, timeout=None):
        """
        Sets a key-value in the cache.

        Optionally accepts a ``timeout`` in seconds. Defaults to ``None`` which
        uses the resource's default timeout.
        """

        if timeout == None:
            timeout = self.timeout

        cache.set(key, value, timeout)

    def cache_control(self):
        control = {
            'max_age': self.timeout,
            's_maxage': self.timeout,
        }

        if self.public is not None:
            control["public"] = self.public

        if self.private is not None:
            control["private"] = self.private

        return control

########NEW FILE########
__FILENAME__ = compat
AUTH_USER_MODEL = 'auth.User'
from django.contrib.auth.models import User
username_field = 'username'

########NEW FILE########
__FILENAME__ = constants
# Enable all basic ORM filters but do not allow filtering across relationships.
ALL = 1
# Enable all ORM filters, including across relationships
ALL_WITH_RELATIONS = 2

########NEW FILE########
__FILENAME__ = fields
from functools import partial
from tastypie import fields
from tastypie.resources import Resource
from tastypie.exceptions import ApiFieldError
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from .resources import GenericResource


class GenericForeignKeyField(fields.ToOneField):
    """
    Provides access to GenericForeignKey objects from the django content_types
    framework.
    """

    def __init__(self, to, attribute, **kwargs):
        if not isinstance(to, dict):
            raise ValueError('to field must be a dictionary in GenericForeignKeyField')

        if len(to) <= 0:
            raise ValueError('to field must have some values')

        for k, v in to.iteritems():
            if not issubclass(k, models.Model) or not issubclass(v, Resource):
                raise ValueError('to field must map django models to tastypie resources')

        super(GenericForeignKeyField, self).__init__(to, attribute, **kwargs)

    def get_related_resource(self, related_instance):
        self._to_class = self.to.get(type(related_instance), None)

        if self._to_class is None:
            raise TypeError('no resource for model %s' % type(related_instance))

        return super(GenericForeignKeyField, self).get_related_resource(related_instance)

    @property
    def to_class(self):
        if self._to_class and not issubclass(GenericResource, self._to_class):
            return self._to_class

        return partial(GenericResource, resources=self.to.values())

    def resource_from_uri(self, fk_resource, uri, request=None, related_obj=None, related_name=None):
        try:
            obj = fk_resource.get_via_uri(uri, request=request)
            fk_resource = self.get_related_resource(obj)
            return super(GenericForeignKeyField, self).resource_from_uri(fk_resource, uri, request, related_obj, related_name)
        except ObjectDoesNotExist:
            raise ApiFieldError("Could not find the provided object via resource URI '%s'." % uri)

    def build_related_resource(self, *args, **kwargs):
        self._to_class = None
        return super(GenericForeignKeyField, self).build_related_resource(*args, **kwargs)

########NEW FILE########
__FILENAME__ = resources
from tastypie.bundle import Bundle
from tastypie.resources import ModelResource
from tastypie.exceptions import NotFound
from django.core.urlresolvers import resolve, Resolver404, get_script_prefix


class GenericResource(ModelResource):
    """
    Provides a stand-in resource for GFK relations.
    """
    def __init__(self, resources, *args, **kwargs):
        self.resource_mapping = dict((r._meta.resource_name, r) for r in resources)
        return super(GenericResource, self).__init__(*args, **kwargs)

    def get_via_uri(self, uri, request=None):
        """
        This pulls apart the salient bits of the URI and populates the
        resource via a ``obj_get``.

        Optionally accepts a ``request``.

        If you need custom behavior based on other portions of the URI,
        simply override this method.
        """
        prefix = get_script_prefix()
        chomped_uri = uri

        if prefix and chomped_uri.startswith(prefix):
            chomped_uri = chomped_uri[len(prefix)-1:]

        try:
            view, args, kwargs = resolve(chomped_uri)
            resource_name = kwargs['resource_name']
            resource_class = self.resource_mapping[resource_name]
        except (Resolver404, KeyError):
            raise NotFound("The URL provided '%s' was not a link to a valid resource." % uri)

        parent_resource = resource_class(api_name=self._meta.api_name)
        kwargs = parent_resource.remove_api_resource_names(kwargs)
        bundle = Bundle(request=request)
        return parent_resource.obj_get(bundle, **kwargs)

########NEW FILE########
__FILENAME__ = resources
# See COPYING file in this directory.
# Some code originally from django-boundaryservice

from urllib import unquote

from django.contrib.gis.db.models import GeometryField
try:
    import json as simplejson
except ImportError: # < Python 2.6
    from django.utils import simplejson
from django.contrib.gis.geos import GEOSGeometry

from tastypie.fields import ApiField, CharField
from tastypie import resources


class GeometryApiField(ApiField):
    """
    Custom ApiField for dealing with data from GeometryFields (by serializing
    them as GeoJSON).
    """
    dehydrated_type = 'geometry'
    help_text = 'Geometry data.'

    def hydrate(self, bundle):
        value = super(GeometryApiField, self).hydrate(bundle)
        if value is None:
            return value
        return simplejson.dumps(value)

    def dehydrate(self, obj):
        return self.convert(super(GeometryApiField, self).dehydrate(obj))

    def convert(self, value):
        if value is None:
            return None

        if isinstance(value, dict):
            return value

        # Get ready-made geojson serialization and then convert it _back_ to
        # a Python object so that tastypie can serialize it as part of the
        # bundle.
        return simplejson.loads(value.geojson)


class ModelResource(resources.ModelResource):
    """
    ModelResource subclass that handles geometry fields as GeoJSON.
    """
    @classmethod
    def api_field_from_django_field(cls, f, default=CharField):
        """
        Overrides default field handling to support custom GeometryApiField.
        """
        if isinstance(f, GeometryField):
            return GeometryApiField

        return super(ModelResource, cls).api_field_from_django_field(f, default)

    def filter_value_to_python(self, value, field_name, filters, filter_expr,
            filter_type):
        value = super(ModelResource, self).filter_value_to_python(
            value, field_name, filters, filter_expr, filter_type)

        # If we are filtering on a GeometryApiField then we should try
        # and convert this to a GEOSGeometry object.  The conversion
        # will fail if we don't have value JSON, so in that case we'll
        # just return ``value`` as normal.
        if isinstance(self.fields[field_name], GeometryApiField):
            try:
                value = GEOSGeometry(unquote(value))
            except ValueError:
                pass
        return value

########NEW FILE########
__FILENAME__ = exceptions
from django.http import HttpResponse


class TastypieError(Exception):
    """A base exception for other tastypie-related errors."""
    pass


class HydrationError(TastypieError):
    """Raised when there is an error hydrating data."""
    pass


class NotRegistered(TastypieError):
    """
    Raised when the requested resource isn't registered with the ``Api`` class.
    """
    pass


class NotFound(TastypieError):
    """
    Raised when the resource/object in question can't be found.
    """
    pass


class Unauthorized(TastypieError):
    """
    Raised when the request object is not accessible to the user.

    This is different than the ``tastypie.http.HttpUnauthorized`` & is handled
    differently internally.
    """
    pass


class ApiFieldError(TastypieError):
    """
    Raised when there is a configuration error with a ``ApiField``.
    """
    pass


class UnsupportedFormat(TastypieError):
    """
    Raised when an unsupported serialization format is requested.
    """
    pass


class BadRequest(TastypieError):
    """
    A generalized exception for indicating incorrect request parameters.

    Handled specially in that the message tossed by this exception will be
    presented to the end user.
    """
    pass


class BlueberryFillingFound(TastypieError):
    pass


class InvalidFilterError(BadRequest):
    """
    Raised when the end user attempts to use a filter that has not be
    explicitly allowed.
    """
    pass


class InvalidSortError(BadRequest):
    """
    Raised when the end user attempts to sort on a field that has not be
    explicitly allowed.
    """
    pass


class ImmediateHttpResponse(TastypieError):
    """
    This exception is used to interrupt the flow of processing to immediately
    return a custom HttpResponse.

    Common uses include::

        * for authentication (like digest/OAuth)
        * for throttling

    """
    _response = HttpResponse("Nothing provided.")

    def __init__(self, response):
        self._response = response

    @property
    def response(self):
        return self._response

########NEW FILE########
__FILENAME__ = fields
import datetime
from dateutil.parser import parse
from decimal import Decimal
import re
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.utils import datetime_safe, importlib
from django.core.urlresolvers import resolve
from tastypie.bundle import Bundle
from tastypie.exceptions import ApiFieldError, NotFound
from tastypie.utils import dict_strip_unicode_keys, make_aware


class NOT_PROVIDED:
    def __str__(self):
        return 'No default provided.'


DATE_REGEX = re.compile('^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2}).*?$')
DATETIME_REGEX = re.compile('^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})(T|\s+)(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2}).*?$')


# All the ApiField variants.

class ApiField(object):
    """The base implementation of a field used by the resources."""
    dehydrated_type = 'string'
    help_text = ''

    def __init__(self, attribute=None, default=NOT_PROVIDED, null=False, blank=False, readonly=False, unique=False, help_text=None, use_in='all'):
        """
        Sets up the field. This is generally called when the containing
        ``Resource`` is initialized.

        Optionally accepts an ``attribute``, which should be a string of
        either an instance attribute or callable off the object during the
        ``dehydrate`` or push data onto an object during the ``hydrate``.
        Defaults to ``None``, meaning data will be manually accessed.

        Optionally accepts a ``default``, which provides default data when the
        object being ``dehydrated``/``hydrated`` has no data on the field.
        Defaults to ``NOT_PROVIDED``.

        Optionally accepts a ``null``, which indicated whether or not a
        ``None`` is allowable data on the field. Defaults to ``False``.

        Optionally accepts a ``blank``, which indicated whether or not
        data may be omitted on the field. Defaults to ``False``.

        Optionally accepts a ``readonly``, which indicates whether the field
        is used during the ``hydrate`` or not. Defaults to ``False``.

        Optionally accepts a ``unique``, which indicates if the field is a
        unique identifier for the object.

        Optionally accepts ``help_text``, which lets you provide a
        human-readable description of the field exposed at the schema level.
        Defaults to the per-Field definition.

        Optionally accepts ``use_in``. This may be one of ``list``, ``detail``
        ``all`` or a callable which accepts a ``bundle`` and returns
        ``True`` or ``False``. Indicates wheather this field will be included
        during dehydration of a list of objects or a single object. If ``use_in``
        is a callable, and returns ``True``, the field will be included during
        dehydration.
        Defaults to ``all``.
        """
        # Track what the index thinks this field is called.
        self.instance_name = None
        self._resource = None
        self.attribute = attribute
        self._default = default
        self.null = null
        self.blank = blank
        self.readonly = readonly
        self.value = None
        self.unique = unique
        self.use_in = 'all'

        if use_in in ['all', 'detail', 'list'] or callable(use_in):
            self.use_in = use_in

        if help_text:
            self.help_text = help_text

    def contribute_to_class(self, cls, name):
        # Do the least we can here so that we don't hate ourselves in the
        # morning.
        self.instance_name = name
        self._resource = cls

    def has_default(self):
        """Returns a boolean of whether this field has a default value."""
        return self._default is not NOT_PROVIDED

    @property
    def default(self):
        """Returns the default value for the field."""
        if callable(self._default):
            return self._default()

        return self._default

    def dehydrate(self, bundle, for_list=True):
        """
        Takes data from the provided object and prepares it for the
        resource.
        """
        if self.attribute is not None:
            # Check for `__` in the field for looking through the relation.
            attrs = self.attribute.split('__')
            current_object = bundle.obj

            for attr in attrs:
                previous_object = current_object
                current_object = getattr(current_object, attr, None)

                if current_object is None:
                    if self.has_default():
                        current_object = self._default
                        # Fall out of the loop, given any further attempts at
                        # accesses will fail miserably.
                        break
                    elif self.null:
                        current_object = None
                        # Fall out of the loop, given any further attempts at
                        # accesses will fail miserably.
                        break
                    else:
                        raise ApiFieldError("The object '%r' has an empty attribute '%s' and doesn't allow a default or null value." % (previous_object, attr))

            if callable(current_object):
                current_object = current_object()

            return self.convert(current_object)

        if self.has_default():
            return self.convert(self.default)
        else:
            return None

    def convert(self, value):
        """
        Handles conversion between the data found and the type of the field.

        Extending classes should override this method and provide correct
        data coercion.
        """
        return value

    def hydrate(self, bundle):
        """
        Takes data stored in the bundle for the field and returns it. Used for
        taking simple data and building a instance object.
        """
        if self.readonly:
            return None
        if not bundle.data.has_key(self.instance_name):
            if getattr(self, 'is_related', False) and not getattr(self, 'is_m2m', False):
                # We've got an FK (or alike field) & a possible parent object.
                # Check for it.
                if bundle.related_obj and bundle.related_name in (self.attribute, self.instance_name):
                    return bundle.related_obj
            if self.blank:
                return None
            elif self.attribute and getattr(bundle.obj, self.attribute, None):
                return getattr(bundle.obj, self.attribute)
            elif self.instance_name and hasattr(bundle.obj, self.instance_name):
                return getattr(bundle.obj, self.instance_name)
            elif self.has_default():
                if callable(self._default):
                    return self._default()

                return self._default
            elif self.null:
                return None
            else:
                raise ApiFieldError("The '%s' field has no data and doesn't allow a default or null value." % self.instance_name)

        return bundle.data[self.instance_name]


class CharField(ApiField):
    """
    A text field of arbitrary length.

    Covers both ``models.CharField`` and ``models.TextField``.
    """
    dehydrated_type = 'string'
    help_text = 'Unicode string data. Ex: "Hello World"'

    def convert(self, value):
        if value is None:
            return None

        return unicode(value)


class FileField(ApiField):
    """
    A file-related field.

    Covers both ``models.FileField`` and ``models.ImageField``.
    """
    dehydrated_type = 'string'
    help_text = 'A file URL as a string. Ex: "http://media.example.com/media/photos/my_photo.jpg"'

    def convert(self, value):
        if value is None:
            return None

        try:
            # Try to return the URL if it's a ``File``, falling back to the string
            # itself if it's been overridden or is a default.
            return getattr(value, 'url', value)
        except ValueError:
            return None


class IntegerField(ApiField):
    """
    An integer field.

    Covers ``models.IntegerField``, ``models.PositiveIntegerField``,
    ``models.PositiveSmallIntegerField`` and ``models.SmallIntegerField``.
    """
    dehydrated_type = 'integer'
    help_text = 'Integer data. Ex: 2673'

    def convert(self, value):
        if value is None:
            return None

        return int(value)


class FloatField(ApiField):
    """
    A floating point field.
    """
    dehydrated_type = 'float'
    help_text = 'Floating point numeric data. Ex: 26.73'

    def convert(self, value):
        if value is None:
            return None

        return float(value)


class DecimalField(ApiField):
    """
    A decimal field.
    """
    dehydrated_type = 'decimal'
    help_text = 'Fixed precision numeric data. Ex: 26.73'

    def convert(self, value):
        if value is None:
            return None

        return Decimal(value)

    def hydrate(self, bundle):
        value = super(DecimalField, self).hydrate(bundle)

        if value and not isinstance(value, Decimal):
            value = Decimal(value)

        return value


class BooleanField(ApiField):
    """
    A boolean field.

    Covers both ``models.BooleanField`` and ``models.NullBooleanField``.
    """
    dehydrated_type = 'boolean'
    help_text = 'Boolean data. Ex: True'

    def convert(self, value):
        if value is None:
            return None

        return bool(value)


class ListField(ApiField):
    """
    A list field.
    """
    dehydrated_type = 'list'
    help_text = "A list of data. Ex: ['abc', 26.73, 8]"

    def convert(self, value):
        if value is None:
            return None

        return list(value)


class DictField(ApiField):
    """
    A dictionary field.
    """
    dehydrated_type = 'dict'
    help_text = "A dictionary of data. Ex: {'price': 26.73, 'name': 'Daniel'}"

    def convert(self, value):
        if value is None:
            return None

        return dict(value)


class DateField(ApiField):
    """
    A date field.
    """
    dehydrated_type = 'date'
    help_text = 'A date as a string. Ex: "2010-11-10"'

    def convert(self, value):
        if value is None:
            return None

        if isinstance(value, basestring):
            match = DATE_REGEX.search(value)

            if match:
                data = match.groupdict()
                return datetime_safe.date(int(data['year']), int(data['month']), int(data['day']))
            else:
                raise ApiFieldError("Date provided to '%s' field doesn't appear to be a valid date string: '%s'" % (self.instance_name, value))

        return value

    def hydrate(self, bundle):
        value = super(DateField, self).hydrate(bundle)

        if value and not hasattr(value, 'year'):
            try:
                # Try to rip a date/datetime out of it.
                value = make_aware(parse(value))

                if hasattr(value, 'hour'):
                    value = value.date()
            except ValueError:
                pass

        return value


class DateTimeField(ApiField):
    """
    A datetime field.
    """
    dehydrated_type = 'datetime'
    help_text = 'A date & time as a string. Ex: "2010-11-10T03:07:43"'

    def convert(self, value):
        if value is None:
            return None

        if isinstance(value, basestring):
            match = DATETIME_REGEX.search(value)

            if match:
                data = match.groupdict()
                return make_aware(datetime_safe.datetime(int(data['year']), int(data['month']), int(data['day']), int(data['hour']), int(data['minute']), int(data['second'])))
            else:
                raise ApiFieldError("Datetime provided to '%s' field doesn't appear to be a valid datetime string: '%s'" % (self.instance_name, value))

        return value

    def hydrate(self, bundle):
        value = super(DateTimeField, self).hydrate(bundle)

        if value and not hasattr(value, 'year'):
            try:
                # Try to rip a date/datetime out of it.
                value = make_aware(parse(value))
            except ValueError:
                pass

        return value


class RelatedField(ApiField):
    """
    Provides access to data that is related within the database.

    The ``RelatedField`` base class is not intended for direct use but provides
    functionality that ``ToOneField`` and ``ToManyField`` build upon.

    The contents of this field actually point to another ``Resource``,
    rather than the related object. This allows the field to represent its data
    in different ways.

    The abstractions based around this are "leaky" in that, unlike the other
    fields provided by ``tastypie``, these fields don't handle arbitrary objects
    very well. The subclasses use Django's ORM layer to make things go, though
    there is no ORM-specific code at this level.
    """
    dehydrated_type = 'related'
    is_related = True
    self_referential = False
    help_text = 'A related resource. Can be either a URI or set of nested resource data.'

    def __init__(self, to, attribute, related_name=None, default=NOT_PROVIDED, null=False, blank=False, readonly=False, full=False, unique=False, help_text=None, use_in='all', full_list=True, full_detail=True):
        """
        Builds the field and prepares it to access to related data.

        The ``to`` argument should point to a ``Resource`` class, NOT
        to a ``Model``. Required.

        The ``attribute`` argument should specify what field/callable points to
        the related data on the instance object. Required.

        Optionally accepts a ``related_name`` argument. Currently unused, as
        unlike Django's ORM layer, reverse relations between ``Resource``
        classes are not automatically created. Defaults to ``None``.

        Optionally accepts a ``null``, which indicated whether or not a
        ``None`` is allowable data on the field. Defaults to ``False``.

        Optionally accepts a ``blank``, which indicated whether or not
        data may be omitted on the field. Defaults to ``False``.

        Optionally accepts a ``readonly``, which indicates whether the field
        is used during the ``hydrate`` or not. Defaults to ``False``.

        Optionally accepts a ``full``, which indicates how the related
        ``Resource`` will appear post-``dehydrate``. If ``False``, the
        related ``Resource`` will appear as a URL to the endpoint of that
        resource. If ``True``, the result of the sub-resource's
        ``dehydrate`` will be included in full.

        Optionally accepts a ``unique``, which indicates if the field is a
        unique identifier for the object.

        Optionally accepts ``help_text``, which lets you provide a
        human-readable description of the field exposed at the schema level.
        Defaults to the per-Field definition.

        Optionally accepts ``use_in``. This may be one of ``list``, ``detail``
        ``all`` or a callable which accepts a ``bundle`` and returns
        ``True`` or ``False``. Indicates wheather this field will be included
        during dehydration of a list of objects or a single object. If ``use_in``
        is a callable, and returns ``True``, the field will be included during
        dehydration.
        Defaults to ``all``.
        
        Optionally accepts a ``full_list``, which indicated whether or not
        data should be fully dehydrated when the request is for a list of
        resources. Accepts ``True``, ``False`` or a callable that accepts
        a bundle and returns ``True`` or ``False``. Depends on ``full``
        being ``True``. Defaults to ``True``.

        Optionally accepts a ``full_detail``, which indicated whether or not
        data should be fully dehydrated when then request is for a single
        resource. Accepts ``True``, ``False`` or a callable that accepts a
        bundle and returns ``True`` or ``False``.Depends on ``full``
        being ``True``. Defaults to ``True``.
        """
        self.instance_name = None
        self._resource = None
        self.to = to
        self.attribute = attribute
        self.related_name = related_name
        self._default = default
        self.null = null
        self.blank = blank
        self.readonly = readonly
        self.full = full
        self.api_name = None
        self.resource_name = None
        self.unique = unique
        self._to_class = None
        self.use_in = 'all'
        self.full_list = full_list
        self.full_detail = full_detail

        if use_in in ['all', 'detail', 'list'] or callable(use_in):
            self.use_in = use_in

        if self.to == 'self':
            self.self_referential = True
            self._to_class = self.__class__

        if help_text:
            self.help_text = help_text

    def contribute_to_class(self, cls, name):
        super(RelatedField, self).contribute_to_class(cls, name)

        # Check if we're self-referential and hook it up.
        # We can't do this quite like Django because there's no ``AppCache``
        # here (which I think we should avoid as long as possible).
        if self.self_referential or self.to == 'self':
            self._to_class = cls

    def get_related_resource(self, related_instance):
        """
        Instaniates the related resource.
        """
        related_resource = self.to_class()

        # Fix the ``api_name`` if it's not present.
        if related_resource._meta.api_name is None:
            if self._resource and not self._resource._meta.api_name is None:
                related_resource._meta.api_name = self._resource._meta.api_name

        # Try to be efficient about DB queries.
        related_resource.instance = related_instance
        return related_resource

    @property
    def to_class(self):
        # We need to be lazy here, because when the metaclass constructs the
        # Resources, other classes may not exist yet.
        # That said, memoize this so we never have to relookup/reimport.
        if self._to_class:
            return self._to_class

        if not isinstance(self.to, basestring):
            self._to_class = self.to
            return self._to_class

        # It's a string. Let's figure it out.
        if '.' in self.to:
            # Try to import.
            module_bits = self.to.split('.')
            module_path, class_name = '.'.join(module_bits[:-1]), module_bits[-1]
            module = importlib.import_module(module_path)
        else:
            # We've got a bare class name here, which won't work (No AppCache
            # to rely on). Try to throw a useful error.
            raise ImportError("Tastypie requires a Python-style path (<module.module.Class>) to lazy load related resources. Only given '%s'." % self.to)

        self._to_class = getattr(module, class_name, None)

        if self._to_class is None:
            raise ImportError("Module '%s' does not appear to have a class called '%s'." % (module_path, class_name))

        return self._to_class

    def dehydrate_related(self, bundle, related_resource, for_list=True):
        """
        Based on the ``full_resource``, returns either the endpoint or the data
        from ``full_dehydrate`` for the related resource.
        """
        should_dehydrate_full_resource = self.should_full_dehydrate(bundle, for_list=for_list)

        if not should_dehydrate_full_resource:
            # Be a good netizen.
            return related_resource.get_resource_uri(bundle)
        else:
            # ZOMG extra data and big payloads.
            bundle = related_resource.build_bundle(
                obj=related_resource.instance,
                request=bundle.request,
                objects_saved=bundle.objects_saved
            )
            return related_resource.full_dehydrate(bundle)

    def resource_from_uri(self, fk_resource, uri, request=None, related_obj=None, related_name=None):
        """
        Given a URI is provided, the related resource is attempted to be
        loaded based on the identifiers in the URI.
        """
        try:
            obj = fk_resource.get_via_uri(uri, request=request)
            bundle = fk_resource.build_bundle(
                obj=obj,
                request=request
            )
            return fk_resource.full_dehydrate(bundle)
        except ObjectDoesNotExist:
            raise ApiFieldError("Could not find the provided object via resource URI '%s'." % uri)

    def resource_from_data(self, fk_resource, data, request=None, related_obj=None, related_name=None):
        """
        Given a dictionary-like structure is provided, a fresh related
        resource is created using that data.
        """
        # Try to hydrate the data provided.
        data = dict_strip_unicode_keys(data)
        fk_bundle = fk_resource.build_bundle(
            data=data,
            request=request
        )

        if related_obj:
            fk_bundle.related_obj = related_obj
            fk_bundle.related_name = related_name

        # We need to check to see if updates are allowed on the FK
        # resource. If not, we'll just return a populated bundle instead
        # of mistakenly updating something that should be read-only.
        if not fk_resource.can_update():
            return fk_resource.full_hydrate(fk_bundle)

        try:
            return fk_resource.obj_update(fk_bundle, skip_errors=True, **data)
        except (NotFound, TypeError):
            try:
                # Attempt lookup by primary key
                lookup_kwargs = dict((k, v) for k, v in data.iteritems() if getattr(fk_resource, k).unique)

                if not lookup_kwargs:
                    raise NotFound()

                return fk_resource.obj_update(fk_bundle, skip_errors=True, **lookup_kwargs)
            except NotFound:
                fk_bundle = fk_resource.full_hydrate(fk_bundle)
                fk_resource.is_valid(fk_bundle)
                return fk_bundle
        except MultipleObjectsReturned:
            return fk_resource.full_hydrate(fk_bundle)

    def resource_from_pk(self, fk_resource, obj, request=None, related_obj=None, related_name=None):
        """
        Given an object with a ``pk`` attribute, the related resource
        is attempted to be loaded via that PK.
        """
        bundle = fk_resource.build_bundle(
            obj=obj,
            request=request
        )
        return fk_resource.full_dehydrate(bundle)

    def build_related_resource(self, value, request=None, related_obj=None, related_name=None):
        """
        Returns a bundle of data built by the related resource, usually via
        ``hydrate`` with the data provided.

        Accepts either a URI, a data dictionary (or dictionary-like structure)
        or an object with a ``pk``.
        """
        self.fk_resource = self.to_class()
        kwargs = {
            'request': request,
            'related_obj': related_obj,
            'related_name': related_name,
        }

        if isinstance(value, Bundle):
            # Already hydrated, probably nested bundles. Just return.
            return value
        elif isinstance(value, basestring):
            # We got a URI. Load the object and assign it.
            return self.resource_from_uri(self.fk_resource, value, **kwargs)
        elif isinstance(value, Bundle):
            # We got a valid bundle object, the RelatedField had full=True
            return value
        elif hasattr(value, 'items'):
            # We've got a data dictionary.
            # Since this leads to creation, this is the only one of these
            # methods that might care about "parent" data.
            return self.resource_from_data(self.fk_resource, value, **kwargs)
        elif hasattr(value, 'pk'):
            # We've got an object with a primary key.
            return self.resource_from_pk(self.fk_resource, value, **kwargs)
        else:
            raise ApiFieldError("The '%s' field was given data that was not a URI, not a dictionary-alike and does not have a 'pk' attribute: %s." % (self.instance_name, value))

    def should_full_dehydrate(self, bundle, for_list):
        """
        Based on the ``full``, ``list_full`` and ``detail_full`` returns ``True`` or ``False``
        indicating weather the resource should be fully dehydrated.
        """
        should_dehydrate_full_resource = False
        if self.full:
            is_details_view = not for_list
            if is_details_view:
                if (not callable(self.full_detail) and self.full_detail) or (callable(self.full_detail) and self.full_detail(bundle)):
                    should_dehydrate_full_resource = True
            else:
                if (not callable(self.full_list) and self.full_list) or (callable(self.full_list) and self.full_list(bundle)):
                    should_dehydrate_full_resource = True

        return should_dehydrate_full_resource


class ToOneField(RelatedField):
    """
    Provides access to related data via foreign key.

    This subclass requires Django's ORM layer to work properly.
    """
    help_text = 'A single related resource. Can be either a URI or set of nested resource data.'

    def __init__(self, to, attribute, related_name=None, default=NOT_PROVIDED,
                 null=False, blank=False, readonly=False, full=False,
                 unique=False, help_text=None, use_in='all', full_list=True, full_detail=True):
        super(ToOneField, self).__init__(
            to, attribute, related_name=related_name, default=default,
            null=null, blank=blank, readonly=readonly, full=full,
            unique=unique, help_text=help_text, use_in=use_in,
            full_list=full_list, full_detail=full_detail
        )
        self.fk_resource = None

    def dehydrate(self, bundle, for_list=True):
        foreign_obj = None

        if isinstance(self.attribute, basestring):
            attrs = self.attribute.split('__')
            foreign_obj = bundle.obj

            for attr in attrs:
                previous_obj = foreign_obj
                try:
                    foreign_obj = getattr(foreign_obj, attr, None)
                except ObjectDoesNotExist:
                    foreign_obj = None
        elif callable(self.attribute):
            foreign_obj = self.attribute(bundle)

        if not foreign_obj:
            if not self.null:
                raise ApiFieldError("The model '%r' has an empty attribute '%s' and doesn't allow a null value." % (previous_obj, attr))

            return None

        self.fk_resource = self.get_related_resource(foreign_obj)
        fk_bundle = Bundle(obj=foreign_obj, request=bundle.request)
        return self.dehydrate_related(fk_bundle, self.fk_resource, for_list=for_list)

    def hydrate(self, bundle):
        value = super(ToOneField, self).hydrate(bundle)

        if value is None:
            return value

        return self.build_related_resource(value, request=bundle.request)

class ForeignKey(ToOneField):
    """
    A convenience subclass for those who prefer to mirror ``django.db.models``.
    """
    pass


class OneToOneField(ToOneField):
    """
    A convenience subclass for those who prefer to mirror ``django.db.models``.
    """
    pass


class ToManyField(RelatedField):
    """
    Provides access to related data via a join table.

    This subclass requires Django's ORM layer to work properly.

    Note that the ``hydrate`` portions of this field are quite different than
    any other field. ``hydrate_m2m`` actually handles the data and relations.
    This is due to the way Django implements M2M relationships.
    """
    is_m2m = True
    help_text = 'Many related resources. Can be either a list of URIs or list of individually nested resource data.'

    def __init__(self, to, attribute, related_name=None, default=NOT_PROVIDED,
                 null=False, blank=False, readonly=False, full=False,
                 unique=False, help_text=None, use_in='all', full_list=True, full_detail=True):
        super(ToManyField, self).__init__(
            to, attribute, related_name=related_name, default=default,
            null=null, blank=blank, readonly=readonly, full=full,
            unique=unique, help_text=help_text, use_in=use_in,
            full_list=full_list, full_detail=full_detail
        )
        self.m2m_bundles = []

    def dehydrate(self, bundle, for_list=True):
        if not bundle.obj or not bundle.obj.pk:
            if not self.null:
                raise ApiFieldError("The model '%r' does not have a primary key and can not be used in a ToMany context." % bundle.obj)

            return []

        the_m2ms = None
        previous_obj = bundle.obj
        attr = self.attribute

        if isinstance(self.attribute, basestring):
            attrs = self.attribute.split('__')
            the_m2ms = bundle.obj

            for attr in attrs:
                previous_obj = the_m2ms
                try:
                    the_m2ms = getattr(the_m2ms, attr, None)
                except ObjectDoesNotExist:
                    the_m2ms = None

                if not the_m2ms:
                    break

        elif callable(self.attribute):
            the_m2ms = self.attribute(bundle)

        if not the_m2ms:
            if not self.null:
                raise ApiFieldError("The model '%r' has an empty attribute '%s' and doesn't allow a null value." % (previous_obj, attr))

            return []

        self.m2m_resources = []
        m2m_dehydrated = []

        # TODO: Also model-specific and leaky. Relies on there being a
        #       ``Manager`` there.
        for m2m in the_m2ms.all():
            m2m_resource = self.get_related_resource(m2m)
            m2m_bundle = Bundle(obj=m2m, request=bundle.request)
            self.m2m_resources.append(m2m_resource)
            m2m_dehydrated.append(self.dehydrate_related(m2m_bundle, m2m_resource, for_list=for_list))

        return m2m_dehydrated

    def hydrate(self, bundle):
        pass

    def hydrate_m2m(self, bundle):
        if self.readonly:
            return None

        if bundle.data.get(self.instance_name) is None:
            if self.blank:
                return []
            elif self.null:
                return []
            else:
                raise ApiFieldError("The '%s' field has no data and doesn't allow a null value." % self.instance_name)

        m2m_hydrated = []

        for value in bundle.data.get(self.instance_name):
            if value is None:
                continue

            kwargs = {
                'request': bundle.request,
            }

            if self.related_name:
                kwargs['related_obj'] = bundle.obj
                kwargs['related_name'] = self.related_name

            m2m_hydrated.append(self.build_related_resource(value, **kwargs))

        return m2m_hydrated


class ManyToManyField(ToManyField):
    """
    A convenience subclass for those who prefer to mirror ``django.db.models``.
    """
    pass


class OneToManyField(ToManyField):
    """
    A convenience subclass for those who prefer to mirror ``django.db.models``.
    """
    pass


class TimeField(ApiField):
    dehydrated_type = 'time'
    help_text = 'A time as string. Ex: "20:05:23"'

    def dehydrate(self, obj, for_list=True):
        return self.convert(super(TimeField, self).dehydrate(obj))

    def convert(self, value):
        if isinstance(value, basestring):
            return self.to_time(value)
        return value

    def to_time(self, s):
        try:
            dt = parse(s)
        except ValueError, e:
            raise ApiFieldError(str(e))
        else:
            return datetime.time(dt.hour, dt.minute, dt.second)

    def hydrate(self, bundle):
        value = super(TimeField, self).hydrate(bundle)

        if value and not isinstance(value, datetime.time):
            value = self.to_time(value)

        return value

########NEW FILE########
__FILENAME__ = http
"""
The various HTTP responses for use in returning proper HTTP codes.
"""
from django.http import HttpResponse


class HttpCreated(HttpResponse):
    status_code = 201

    def __init__(self, *args, **kwargs):
        location = kwargs.pop('location', '')

        super(HttpCreated, self).__init__(*args, **kwargs)
        self['Location'] = location


class HttpAccepted(HttpResponse):
    status_code = 202


class HttpNoContent(HttpResponse):
    status_code = 204


class HttpMultipleChoices(HttpResponse):
    status_code = 300


class HttpSeeOther(HttpResponse):
    status_code = 303


class HttpNotModified(HttpResponse):
    status_code = 304


class HttpBadRequest(HttpResponse):
    status_code = 400


class HttpUnauthorized(HttpResponse):
    status_code = 401


class HttpForbidden(HttpResponse):
    status_code = 403


class HttpNotFound(HttpResponse):
    status_code = 404


class HttpMethodNotAllowed(HttpResponse):
    status_code = 405


class HttpConflict(HttpResponse):
    status_code = 409


class HttpGone(HttpResponse):
    status_code = 410


class HttpTooManyRequests(HttpResponse):
    status_code = 429


class HttpApplicationError(HttpResponse):
    status_code = 500


class HttpNotImplemented(HttpResponse):
    status_code = 501


########NEW FILE########
__FILENAME__ = backfill_api_keys
from django.core.management.base import NoArgsCommand
from tastypie.compat import User
from tastypie.models import ApiKey


class Command(NoArgsCommand):
    help = "Goes through all users and adds API keys for any that don't have one."
    
    def handle_noargs(self, **options):
        """Goes through all users and adds API keys for any that don't have one."""
        self.verbosity = int(options.get('verbosity', 1))
        
        for user in User.objects.all().iterator():
            try:
                api_key = ApiKey.objects.get(user=user)
                
                if not api_key.key:
                    # Autogenerate the key.
                    api_key.save()
                    
                    if self.verbosity >= 1:
                        print u"Generated a new key for '%s'" % user.username
            except ApiKey.DoesNotExist:
                api_key = ApiKey.objects.create(user=user)
                
                if self.verbosity >= 1:
                    print u"Created a new key for '%s'" % user.username

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from tastypie.compat import AUTH_USER_MODEL


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'ApiAccess'
        db.create_table('tastypie_apiaccess', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('identifier', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('url', self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True)),
            ('request_method', self.gf('django.db.models.fields.CharField')(default='', max_length=10, blank=True)),
            ('accessed', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('tastypie', ['ApiAccess'])

        # Adding model 'ApiKey'
        db.create_table('tastypie_apikey', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='api_key', unique=True, to=orm[AUTH_USER_MODEL])),
            ('key', self.gf('django.db.models.fields.CharField')(default='', max_length=256, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal('tastypie', ['ApiKey'])


    def backwards(self, orm):

        # Deleting model 'ApiAccess'
        db.delete_table('tastypie_apiaccess')

        # Deleting model 'ApiKey'
        db.delete_table('tastypie_apikey')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        AUTH_USER_MODEL: {
            'Meta': {'object_name': AUTH_USER_MODEL.split('.')[-1]},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'tastypie.apiaccess': {
            'Meta': {'object_name': 'ApiAccess'},
            'accessed': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'request_method': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '10', 'blank': 'True'}),
            'url': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'})
        },
        'tastypie.apikey': {
            'Meta': {'object_name': 'ApiKey'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '256', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'api_key'", 'unique': 'True', 'to': "orm['%s']" % AUTH_USER_MODEL})
        }
    }

    complete_apps = ['tastypie']

########NEW FILE########
__FILENAME__ = 0002_add_apikey_index
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from tastypie.compat import AUTH_USER_MODEL


class Migration(SchemaMigration):

    def forwards(self, orm):
        if not db.backend_name in ('mysql', 'sqlite'):
            # Adding index on 'ApiKey', fields ['key']
            db.create_index('tastypie_apikey', ['key'])

    def backwards(self, orm):
        if not db.backend_name in ('mysql', 'sqlite'):
            # Removing index on 'ApiKey', fields ['key']
            db.delete_index('tastypie_apikey', ['key'])

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        AUTH_USER_MODEL: {
            'Meta': {'object_name': AUTH_USER_MODEL.split('.')[-1]},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'tastypie.apiaccess': {
            'Meta': {'object_name': 'ApiAccess'},
            'accessed': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'request_method': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '10', 'blank': 'True'}),
            'url': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'})
        },
        'tastypie.apikey': {
            'Meta': {'object_name': 'ApiKey'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 11, 5, 0, 0)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '256', 'db_index': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'api_key'", 'unique': 'True', 'to': "orm['%s']" % AUTH_USER_MODEL})
        }
    }

    complete_apps = ['tastypie']
########NEW FILE########
__FILENAME__ = models
import hmac
import time
from django.conf import settings
from django.db import models
from tastypie.utils import now

try:
    from hashlib import sha1
except ImportError:
    import sha
    sha1 = sha.sha


class ApiAccess(models.Model):
    """A simple model for use with the ``CacheDBThrottle`` behaviors."""
    identifier = models.CharField(max_length=255)
    url = models.CharField(max_length=255, blank=True, default='')
    request_method = models.CharField(max_length=10, blank=True, default='')
    accessed = models.PositiveIntegerField()
    
    def __unicode__(self):
        return u"%s @ %s" % (self.identifier, self.accessed)
    
    def save(self, *args, **kwargs):
        self.accessed = int(time.time())
        return super(ApiAccess, self).save(*args, **kwargs)


if 'django.contrib.auth' in settings.INSTALLED_APPS:
    import uuid
    from tastypie.compat import AUTH_USER_MODEL
    class ApiKey(models.Model):
        user = models.OneToOneField(AUTH_USER_MODEL, related_name='api_key')
        key = models.CharField(max_length=256, blank=True, default='', db_index=True)
        created = models.DateTimeField(default=now)

        def __unicode__(self):
            return u"%s for %s" % (self.key, self.user)
        
        def save(self, *args, **kwargs):
            if not self.key:
                self.key = self.generate_key()
            
            return super(ApiKey, self).save(*args, **kwargs)
        
        def generate_key(self):
            # Get a random UUID.
            new_uuid = uuid.uuid4()
            # Hmac that beast.
            return hmac.new(str(new_uuid), digestmod=sha1).hexdigest()

        class Meta:
            abstract = getattr(settings, 'TASTYPIE_ABSTRACT_APIKEY', False)
    
    
    def create_api_key(sender, **kwargs):
        """
        A signal for hooking up automatic ``ApiKey`` creation.
        """
        if kwargs.get('created') is True:
            ApiKey.objects.create(user=kwargs.get('instance'))

########NEW FILE########
__FILENAME__ = paginator
from django.conf import settings
from tastypie.exceptions import BadRequest
from urllib import urlencode


class Paginator(object):
    """
    Limits result sets down to sane amounts for passing to the client.

    This is used in place of Django's ``Paginator`` due to the way pagination
    works. ``limit`` & ``offset`` (tastypie) are used in place of ``page``
    (Django) so none of the page-related calculations are necessary.

    This implementation also provides additional details like the
    ``total_count`` of resources seen and convenience links to the
    ``previous``/``next`` pages of data as available.
    """
    def __init__(self, request_data, objects, resource_uri=None, limit=None, offset=0, max_limit=1000, collection_name='objects'):
        """
        Instantiates the ``Paginator`` and allows for some configuration.

        The ``request_data`` argument ought to be a dictionary-like object.
        May provide ``limit`` and/or ``offset`` to override the defaults.
        Commonly provided ``request.GET``. Required.

        The ``objects`` should be a list-like object of ``Resources``.
        This is typically a ``QuerySet`` but can be anything that
        implements slicing. Required.

        Optionally accepts a ``limit`` argument, which specifies how many
        items to show at a time. Defaults to ``None``, which is no limit.

        Optionally accepts an ``offset`` argument, which specifies where in
        the ``objects`` to start displaying results from. Defaults to 0.

        Optionally accepts a ``max_limit`` argument, which the upper bound
        limit. Defaults to ``1000``. If you set it to 0 or ``None``, no upper
        bound will be enforced.
        """
        self.request_data = request_data
        self.objects = objects
        self.limit = limit
        self.max_limit = max_limit
        self.offset = offset
        self.resource_uri = resource_uri
        self.collection_name = collection_name

    def get_limit(self):
        """
        Determines the proper maximum number of results to return.

        In order of importance, it will use:

            * The user-requested ``limit`` from the GET parameters, if specified.
            * The object-level ``limit`` if specified.
            * ``settings.API_LIMIT_PER_PAGE`` if specified.

        Default is 20 per page.
        """

        limit = self.request_data.get('limit', self.limit)
        if limit is None:
            limit = getattr(settings, 'API_LIMIT_PER_PAGE', 20)

        try:
            limit = int(limit)
        except ValueError:
            raise BadRequest("Invalid limit '%s' provided. Please provide a positive integer." % limit)

        if limit < 0:
            raise BadRequest("Invalid limit '%s' provided. Please provide a positive integer >= 0." % limit)

        if self.max_limit and (not limit or limit > self.max_limit):
            # If it's more than the max, we're only going to return the max.
            # This is to prevent excessive DB (or other) load.
            return self.max_limit

        return limit

    def get_offset(self):
        """
        Determines the proper starting offset of results to return.

        It attempts to use the user-provided ``offset`` from the GET parameters,
        if specified. Otherwise, it falls back to the object-level ``offset``.

        Default is 0.
        """
        offset = self.offset

        if 'offset' in self.request_data:
            offset = self.request_data['offset']

        try:
            offset = int(offset)
        except ValueError:
            raise BadRequest("Invalid offset '%s' provided. Please provide an integer." % offset)

        if offset < 0:
            raise BadRequest("Invalid offset '%s' provided. Please provide a positive integer >= 0." % offset)

        return offset

    def get_slice(self, limit, offset):
        """
        Slices the result set to the specified ``limit`` & ``offset``.
        """
        if limit == 0:
            return self.objects[offset:]

        return self.objects[offset:offset + limit]

    def get_count(self):
        """
        Returns a count of the total number of objects seen.
        """
        try:
            return self.objects.count()
        except (AttributeError, TypeError):
            # If it's not a QuerySet (or it's ilk), fallback to ``len``.
            return len(self.objects)

    def get_previous(self, limit, offset):
        """
        If a previous page is available, will generate a URL to request that
        page. If not available, this returns ``None``.
        """
        if offset - limit < 0:
            return None

        return self._generate_uri(limit, offset-limit)

    def get_next(self, limit, offset, count):
        """
        If a next page is available, will generate a URL to request that
        page. If not available, this returns ``None``.
        """
        if offset + limit >= count:
            return None

        return self._generate_uri(limit, offset+limit)

    def _generate_uri(self, limit, offset):
        if self.resource_uri is None:
            return None

        try:
            # QueryDict has a urlencode method that can handle multiple values for the same key
            request_params = self.request_data.copy()
            if 'limit' in request_params:
                del request_params['limit']
            if 'offset' in request_params:
                del request_params['offset']
            request_params.update({'limit': limit, 'offset': offset})
            encoded_params = request_params.urlencode()
        except AttributeError:
            request_params = {}

            for k, v in self.request_data.items():
                if isinstance(v, unicode):
                    request_params[k] = v.encode('utf-8')
                else:
                    request_params[k] = v

            if 'limit' in request_params:
                del request_params['limit']
            if 'offset' in request_params:
                del request_params['offset']
            request_params.update({'limit': limit, 'offset': offset})
            encoded_params = urlencode(request_params)

        return '%s?%s' % (
            self.resource_uri,
            encoded_params
        )

    def page(self):
        """
        Generates all pertinent data about the requested page.

        Handles getting the correct ``limit`` & ``offset``, then slices off
        the correct set of results and returns all pertinent metadata.
        """
        limit = self.get_limit()
        offset = self.get_offset()
        count = self.get_count()
        objects = self.get_slice(limit, offset)
        meta = {
            'offset': offset,
            'limit': limit,
            'total_count': count,
        }

        if limit:
            meta['previous'] = self.get_previous(limit, offset)
            meta['next'] = self.get_next(limit, offset, count)

        return {
            self.collection_name: objects,
            'meta': meta,
        }

########NEW FILE########
__FILENAME__ = resources
from __future__ import with_statement
import sys
import logging
import warnings
import django
from django.conf import settings
try:
    from django.conf.urls import patterns, url
except ImportError: # Django < 1.4
    from django.conf.urls.defaults import patterns, url
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, ValidationError
from django.core.urlresolvers import NoReverseMatch, reverse, resolve, Resolver404, get_script_prefix
from django.core.signals import got_request_exception
from django.db import transaction
from django.db.models.sql.constants import QUERY_TERMS
from django.http import HttpResponse, HttpResponseNotFound, Http404
from django.utils.cache import patch_cache_control, patch_vary_headers
from tastypie.authentication import Authentication
from tastypie.authorization import ReadOnlyAuthorization
from tastypie.bundle import Bundle
from tastypie.cache import NoCache
from tastypie.constants import ALL, ALL_WITH_RELATIONS
from tastypie.exceptions import NotFound, BadRequest, InvalidFilterError, HydrationError, InvalidSortError, ImmediateHttpResponse, Unauthorized
from tastypie import fields
from tastypie import http
from tastypie.paginator import Paginator
from tastypie.serializers import Serializer
from tastypie.throttle import BaseThrottle
from tastypie.utils import is_valid_jsonp_callback_value, dict_strip_unicode_keys, trailing_slash
from tastypie.utils.mime import determine_format, build_content_type
from tastypie.validation import Validation
try:
    set
except NameError:
    from sets import Set as set
# copycompat deprecated in Django 1.5.  If python version is at least 2.5, it
# is safe to use the native python copy module.
# The ``copy`` module became function-friendly in Python 2.5 and
# ``copycompat`` was added in post 1.1.1 Django (r11901)..
if sys.version_info >= (2,5):
    try:
        from copy import deepcopy
    except ImportError:
        from django.utils.copycompat import deepcopy
else:
    # For python older than 2.5, we must be running a version of Django before
    # copycompat was deprecated.
    try:
        from django.utils.copycompat import deepcopy
    except ImportError:
        from copy import deepcopy
# If ``csrf_exempt`` isn't present, stub it.
try:
    from django.views.decorators.csrf import csrf_exempt
except ImportError:
    def csrf_exempt(func):
        return func

# Django 1.5 has moved this constant up one level.
try:
    from django.db.models.constants import LOOKUP_SEP
except ImportError:
    from django.db.models.sql.constants import LOOKUP_SEP


class NOT_AVAILABLE:
    def __str__(self):
        return 'No such data is available.'


class ResourceOptions(object):
    """
    A configuration class for ``Resource``.

    Provides sane defaults and the logic needed to augment these settings with
    the internal ``class Meta`` used on ``Resource`` subclasses.
    """
    serializer = Serializer()
    authentication = Authentication()
    authorization = ReadOnlyAuthorization()
    cache = NoCache()
    throttle = BaseThrottle()
    validation = Validation()
    paginator_class = Paginator
    allowed_methods = ['get', 'post', 'put', 'delete', 'patch']
    list_allowed_methods = None
    detail_allowed_methods = None
    limit = getattr(settings, 'API_LIMIT_PER_PAGE', 20)
    max_limit = 1000
    api_name = None
    resource_name = None
    urlconf_namespace = None
    default_format = 'application/json'
    filtering = {}
    ordering = []
    object_class = None
    queryset = None
    fields = []
    excludes = []
    include_resource_uri = True
    include_absolute_url = False
    always_return_data = False
    collection_name = 'objects'
    detail_uri_name = 'pk'

    def __new__(cls, meta=None):
        overrides = {}

        # Handle overrides.
        if meta:
            for override_name in dir(meta):
                # No internals please.
                if not override_name.startswith('_'):
                    overrides[override_name] = getattr(meta, override_name)

        allowed_methods = overrides.get('allowed_methods', ['get', 'post', 'put', 'delete', 'patch'])

        if overrides.get('list_allowed_methods', None) is None:
            overrides['list_allowed_methods'] = allowed_methods

        if overrides.get('detail_allowed_methods', None) is None:
            overrides['detail_allowed_methods'] = allowed_methods

        return object.__new__(type('ResourceOptions', (cls,), overrides))


class DeclarativeMetaclass(type):
    def __new__(cls, name, bases, attrs):
        attrs['base_fields'] = {}
        declared_fields = {}

        # Inherit any fields from parent(s).
        try:
            parents = [b for b in bases if issubclass(b, Resource)]
            # Simulate the MRO.
            parents.reverse()

            for p in parents:
                parent_fields = getattr(p, 'base_fields', {})

                for field_name, field_object in parent_fields.items():
                    attrs['base_fields'][field_name] = deepcopy(field_object)
        except NameError:
            pass

        for field_name, obj in attrs.items():
            # Look for ``dehydrated_type`` instead of doing ``isinstance``,
            # which can break down if Tastypie is re-namespaced as something
            # else.
            if hasattr(obj, 'dehydrated_type'):
                field = attrs.pop(field_name)
                declared_fields[field_name] = field

        attrs['base_fields'].update(declared_fields)
        attrs['declared_fields'] = declared_fields
        new_class = super(DeclarativeMetaclass, cls).__new__(cls, name, bases, attrs)
        opts = getattr(new_class, 'Meta', None)
        new_class._meta = ResourceOptions(opts)

        if not getattr(new_class._meta, 'resource_name', None):
            # No ``resource_name`` provided. Attempt to auto-name the resource.
            class_name = new_class.__name__
            name_bits = [bit for bit in class_name.split('Resource') if bit]
            resource_name = ''.join(name_bits).lower()
            new_class._meta.resource_name = resource_name

        if getattr(new_class._meta, 'include_resource_uri', True):
            if not 'resource_uri' in new_class.base_fields:
                new_class.base_fields['resource_uri'] = fields.CharField(readonly=True)
        elif 'resource_uri' in new_class.base_fields and not 'resource_uri' in attrs:
            del(new_class.base_fields['resource_uri'])

        for field_name, field_object in new_class.base_fields.items():
            if hasattr(field_object, 'contribute_to_class'):
                field_object.contribute_to_class(new_class, field_name)

        return new_class


class Resource(object):
    """
    Handles the data, request dispatch and responding to requests.

    Serialization/deserialization is handled "at the edges" (i.e. at the
    beginning/end of the request/response cycle) so that everything internally
    is Python data structures.

    This class tries to be non-model specific, so it can be hooked up to other
    data sources, such as search results, files, other data, etc.
    """
    __metaclass__ = DeclarativeMetaclass

    def __init__(self, api_name=None):
        self.fields = deepcopy(self.base_fields)

        if not api_name is None:
            self._meta.api_name = api_name

    def __getattr__(self, name):
        if name in self.fields:
            return self.fields[name]
        raise AttributeError(name)

    def wrap_view(self, view):
        """
        Wraps methods so they can be called in a more functional way as well
        as handling exceptions better.

        Note that if ``BadRequest`` or an exception with a ``response`` attr
        are seen, there is special handling to either present a message back
        to the user or return the response traveling with the exception.
        """
        @csrf_exempt
        def wrapper(request, *args, **kwargs):
            try:
                callback = getattr(self, view)
                response = callback(request, *args, **kwargs)

                # Our response can vary based on a number of factors, use
                # the cache class to determine what we should ``Vary`` on so
                # caches won't return the wrong (cached) version.
                varies = getattr(self._meta.cache, "varies", [])

                if varies:
                    patch_vary_headers(response, varies)

                if self._meta.cache.cacheable(request, response):
                    if self._meta.cache.cache_control():
                        # If the request is cacheable and we have a
                        # ``Cache-Control`` available then patch the header.
                        patch_cache_control(response, **self._meta.cache.cache_control())

                if request.is_ajax() and not response.has_header("Cache-Control"):
                    # IE excessively caches XMLHttpRequests, so we're disabling
                    # the browser cache here.
                    # See http://www.enhanceie.com/ie/bugs.asp for details.
                    patch_cache_control(response, no_cache=True)

                return response
            except (BadRequest, fields.ApiFieldError), e:
                data = {"error": e.args[0] if getattr(e, 'args') else ''}
                return self.error_response(request, data, response_class=http.HttpBadRequest)
            except ValidationError, e:
                data = {"error": e.messages}
                return self.error_response(request, data, response_class=http.HttpBadRequest)
            except Exception, e:
                if hasattr(e, 'response'):
                    return e.response

                # A real, non-expected exception.
                # Handle the case where the full traceback is more helpful
                # than the serialized error.
                if settings.DEBUG and getattr(settings, 'TASTYPIE_FULL_DEBUG', False):
                    raise

                # Re-raise the error to get a proper traceback when the error
                # happend during a test case
                if request.META.get('SERVER_NAME') == 'testserver':
                    raise

                # Rather than re-raising, we're going to things similar to
                # what Django does. The difference is returning a serialized
                # error message.
                return self._handle_500(request, e)

        return wrapper

    def _handle_500(self, request, exception):
        import traceback
        import sys
        the_trace = '\n'.join(traceback.format_exception(*(sys.exc_info())))
        response_class = http.HttpApplicationError
        response_code = 500

        NOT_FOUND_EXCEPTIONS = (NotFound, ObjectDoesNotExist, Http404)

        if isinstance(exception, NOT_FOUND_EXCEPTIONS):
            response_class = HttpResponseNotFound
            response_code = 404

        if settings.DEBUG:
            data = {
                "error_message": unicode(exception),
                "traceback": the_trace,
            }
            return self.error_response(request, data, response_class=response_class)

        # When DEBUG is False, send an error message to the admins (unless it's
        # a 404, in which case we check the setting).
        send_broken_links = getattr(settings, 'SEND_BROKEN_LINK_EMAILS', False)

        if not response_code == 404 or send_broken_links:
            log = logging.getLogger('django.request.tastypie')
            log.error('Internal Server Error: %s' % request.path, exc_info=True,
                      extra={'status_code': response_code, 'request': request})

            if django.VERSION < (1, 3, 0):
                from django.core.mail import mail_admins
                subject = 'Error (%s IP): %s' % ((request.META.get('REMOTE_ADDR') in settings.INTERNAL_IPS and 'internal' or 'EXTERNAL'), request.path)
                try:
                    request_repr = repr(request)
                except:
                    request_repr = "Request repr() unavailable"

                message = "%s\n\n%s" % (the_trace, request_repr)
                mail_admins(subject, message, fail_silently=True)

        # Send the signal so other apps are aware of the exception.
        got_request_exception.send(self.__class__, request=request)

        # Prep the data going out.
        data = {
            "error_message": getattr(settings, 'TASTYPIE_CANNED_ERROR', "Sorry, this request could not be processed. Please try again later."),
            "traceback": the_trace,
        }
        return self.error_response(request, data, response_class=response_class)

    def _build_reverse_url(self, name, args=None, kwargs=None):
        """
        A convenience hook for overriding how URLs are built.

        See ``NamespacedModelResource._build_reverse_url`` for an example.
        """
        return reverse(name, args=args, kwargs=kwargs)

    def base_urls(self):
        """
        The standard URLs this ``Resource`` should respond to.
        """
        return [
            url(r"^(?P<resource_name>%s)%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('dispatch_list'), name="api_dispatch_list"),
            url(r"^(?P<resource_name>%s)/schema%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('get_schema'), name="api_get_schema"),
            url(r"^(?P<resource_name>%s)/set/(?P<%s_list>\w[\w/;-]*)%s$" % (self._meta.resource_name, self._meta.detail_uri_name, trailing_slash()), self.wrap_view('get_multiple'), name="api_get_multiple"),
            url(r"^(?P<resource_name>%s)/(?P<%s>\w[\w/-]*)%s$" % (self._meta.resource_name, self._meta.detail_uri_name, trailing_slash()), self.wrap_view('dispatch_detail'), name="api_dispatch_detail"),
        ]

    def override_urls(self):
        """
        Deprecated. Will be removed by v1.0.0. Please use ``prepend_urls`` instead.
        """
        return []

    def prepend_urls(self):
        """
        A hook for adding your own URLs or matching before the default URLs.
        """
        return []

    @property
    def urls(self):
        """
        The endpoints this ``Resource`` responds to.

        Mostly a standard URLconf, this is suitable for either automatic use
        when registered with an ``Api`` class or for including directly in
        a URLconf should you choose to.
        """
        urls = self.prepend_urls()

        overridden_urls = self.override_urls()
        if overridden_urls:
            warnings.warn("'override_urls' is a deprecated method & will be removed by v1.0.0. Please rename your method to ``prepend_urls``.")
            urls += overridden_urls

        urls += self.base_urls()
        urlpatterns = patterns('',
            *urls
        )
        return urlpatterns

    def determine_format(self, request):
        """
        Used to determine the desired format.

        Largely relies on ``tastypie.utils.mime.determine_format`` but here
        as a point of extension.
        """
        return determine_format(request, self._meta.serializer, default_format=self._meta.default_format)

    def serialize(self, request, data, format, options=None):
        """
        Given a request, data and a desired format, produces a serialized
        version suitable for transfer over the wire.

        Mostly a hook, this uses the ``Serializer`` from ``Resource._meta``.
        """
        options = options or {}

        if 'text/javascript' in format:
            # get JSONP callback name. default to "callback"
            callback = request.GET.get('callback', 'callback')

            if not is_valid_jsonp_callback_value(callback):
                raise BadRequest('JSONP callback name is invalid.')

            options['callback'] = callback

        return self._meta.serializer.serialize(data, format, options)

    def deserialize(self, request, data, format='application/json'):
        """
        Given a request, data and a format, deserializes the given data.

        It relies on the request properly sending a ``CONTENT_TYPE`` header,
        falling back to ``application/json`` if not provided.

        Mostly a hook, this uses the ``Serializer`` from ``Resource._meta``.
        """
        deserialized = self._meta.serializer.deserialize(data, format=request.META.get('CONTENT_TYPE', 'application/json'))
        return deserialized

    def alter_list_data_to_serialize(self, request, data):
        """
        A hook to alter list data just before it gets serialized & sent to the user.

        Useful for restructuring/renaming aspects of the what's going to be
        sent.

        Should accommodate for a list of objects, generally also including
        meta data.
        """
        return data

    def alter_detail_data_to_serialize(self, request, data):
        """
        A hook to alter detail data just before it gets serialized & sent to the user.

        Useful for restructuring/renaming aspects of the what's going to be
        sent.

        Should accommodate for receiving a single bundle of data.
        """
        return data

    def alter_deserialized_list_data(self, request, data):
        """
        A hook to alter list data just after it has been received from the user &
        gets deserialized.

        Useful for altering the user data before any hydration is applied.
        """
        return data

    def alter_deserialized_detail_data(self, request, data):
        """
        A hook to alter detail data just after it has been received from the user &
        gets deserialized.

        Useful for altering the user data before any hydration is applied.
        """
        return data

    def dispatch_list(self, request, **kwargs):
        """
        A view for handling the various HTTP methods (GET/POST/PUT/DELETE) over
        the entire list of resources.

        Relies on ``Resource.dispatch`` for the heavy-lifting.
        """
        return self.dispatch('list', request, **kwargs)

    def dispatch_detail(self, request, **kwargs):
        """
        A view for handling the various HTTP methods (GET/POST/PUT/DELETE) on
        a single resource.

        Relies on ``Resource.dispatch`` for the heavy-lifting.
        """
        return self.dispatch('detail', request, **kwargs)

    def dispatch(self, request_type, request, **kwargs):
        """
        Handles the common operations (allowed HTTP method, authentication,
        throttling, method lookup) surrounding most CRUD interactions.
        """
        allowed_methods = getattr(self._meta, "%s_allowed_methods" % request_type, None)

        if 'HTTP_X_HTTP_METHOD_OVERRIDE' in request.META:
            request.method = request.META['HTTP_X_HTTP_METHOD_OVERRIDE']

        request_method = self.method_check(request, allowed=allowed_methods)
        method = getattr(self, "%s_%s" % (request_method, request_type), None)

        if method is None:
            raise ImmediateHttpResponse(response=http.HttpNotImplemented())

        self.is_authenticated(request)
        self.throttle_check(request)

        # All clear. Process the request.
        request = convert_post_to_put(request)
        response = method(request, **kwargs)

        # Add the throttled request.
        self.log_throttled_access(request)

        # If what comes back isn't a ``HttpResponse``, assume that the
        # request was accepted and that some action occurred. This also
        # prevents Django from freaking out.
        if not isinstance(response, HttpResponse):
            return http.HttpNoContent()

        return response

    def remove_api_resource_names(self, url_dict):
        """
        Given a dictionary of regex matches from a URLconf, removes
        ``api_name`` and/or ``resource_name`` if found.

        This is useful for converting URLconf matches into something suitable
        for data lookup. For example::

            Model.objects.filter(**self.remove_api_resource_names(matches))
        """
        kwargs_subset = url_dict.copy()

        for key in ['api_name', 'resource_name']:
            try:
                del(kwargs_subset[key])
            except KeyError:
                pass

        return kwargs_subset

    def method_check(self, request, allowed=None):
        """
        Ensures that the HTTP method used on the request is allowed to be
        handled by the resource.

        Takes an ``allowed`` parameter, which should be a list of lowercase
        HTTP methods to check against. Usually, this looks like::

            # The most generic lookup.
            self.method_check(request, self._meta.allowed_methods)

            # A lookup against what's allowed for list-type methods.
            self.method_check(request, self._meta.list_allowed_methods)

            # A useful check when creating a new endpoint that only handles
            # GET.
            self.method_check(request, ['get'])
        """
        if allowed is None:
            allowed = []

        request_method = request.method.lower()
        allows = ','.join(map(str.upper, allowed))

        if request_method == "options":
            response = HttpResponse(allows)
            response['Allow'] = allows
            raise ImmediateHttpResponse(response=response)

        if not request_method in allowed:
            response = http.HttpMethodNotAllowed(allows)
            response['Allow'] = allows
            raise ImmediateHttpResponse(response=response)

        return request_method

    def is_authenticated(self, request):
        """
        Handles checking if the user is authenticated and dealing with
        unauthenticated users.

        Mostly a hook, this uses class assigned to ``authentication`` from
        ``Resource._meta``.
        """
        # Authenticate the request as needed.
        auth_result = self._meta.authentication.is_authenticated(request)

        if isinstance(auth_result, HttpResponse):
            raise ImmediateHttpResponse(response=auth_result)

        if not auth_result is True:
            raise ImmediateHttpResponse(response=http.HttpUnauthorized())

    def throttle_check(self, request):
        """
        Handles checking if the user should be throttled.

        Mostly a hook, this uses class assigned to ``throttle`` from
        ``Resource._meta``.
        """
        request_method = request.method.lower()
        identifier = self._meta.authentication.get_identifier(request)

        # Check to see if they should be throttled.
        if self._meta.throttle.should_be_throttled(identifier, url=request.get_full_path(), request_method=request_method):
            # Throttle limit exceeded.
            raise ImmediateHttpResponse(response=http.HttpTooManyRequests())

    def log_throttled_access(self, request):
        """
        Handles the recording of the user's access for throttling purposes.

        Mostly a hook, this uses class assigned to ``throttle`` from
        ``Resource._meta``.
        """
        request_method = request.method.lower()
        self._meta.throttle.accessed(self._meta.authentication.get_identifier(request), url=request.get_full_path(), request_method=request_method)

    def unauthorized_result(self, exception):
        raise ImmediateHttpResponse(response=http.HttpUnauthorized())

    def authorized_read_list(self, object_list, bundle):
        """
        Handles checking of permissions to see if the user has authorization
        to GET this resource.
        """
        try:
            auth_result = self._meta.authorization.read_list(object_list, bundle)
        except Unauthorized, e:
            self.unauthorized_result(e)

        return auth_result

    def authorized_read_detail(self, object_list, bundle):
        """
        Handles checking of permissions to see if the user has authorization
        to GET this resource.
        """
        try:
            auth_result = self._meta.authorization.read_detail(object_list, bundle)
            if not auth_result is True:
                raise Unauthorized()
        except Unauthorized, e:
            self.unauthorized_result(e)

        return auth_result

    def authorized_create_list(self, object_list, bundle):
        """
        Handles checking of permissions to see if the user has authorization
        to POST this resource.
        """
        try:
            auth_result = self._meta.authorization.create_list(object_list, bundle)
        except Unauthorized, e:
            self.unauthorized_result(e)

        return auth_result

    def authorized_create_detail(self, object_list, bundle):
        """
        Handles checking of permissions to see if the user has authorization
        to POST this resource.
        """
        try:
            auth_result = self._meta.authorization.create_detail(object_list, bundle)
            if not auth_result is True:
                raise Unauthorized()
        except Unauthorized, e:
            self.unauthorized_result(e)

        return auth_result

    def authorized_update_list(self, object_list, bundle):
        """
        Handles checking of permissions to see if the user has authorization
        to PUT this resource.
        """
        try:
            auth_result = self._meta.authorization.update_list(object_list, bundle)
        except Unauthorized, e:
            self.unauthorized_result(e)

        return auth_result

    def authorized_update_detail(self, object_list, bundle):
        """
        Handles checking of permissions to see if the user has authorization
        to PUT this resource.
        """
        try:
            auth_result = self._meta.authorization.update_detail(object_list, bundle)
            if not auth_result is True:
                raise Unauthorized()
        except Unauthorized, e:
            self.unauthorized_result(e)

        return auth_result

    def authorized_delete_list(self, object_list, bundle):
        """
        Handles checking of permissions to see if the user has authorization
        to DELETE this resource.
        """
        try:
            auth_result = self._meta.authorization.delete_list(object_list, bundle)
        except Unauthorized, e:
            self.unauthorized_result(e)

        return auth_result

    def authorized_delete_detail(self, object_list, bundle):
        """
        Handles checking of permissions to see if the user has authorization
        to DELETE this resource.
        """
        try:
            auth_result = self._meta.authorization.delete_detail(object_list, bundle)
            if not auth_result:
                raise Unauthorized()
        except Unauthorized, e:
            self.unauthorized_result(e)

        return auth_result

    def build_bundle(self, obj=None, data=None, request=None, objects_saved=None):
        """
        Given either an object, a data dictionary or both, builds a ``Bundle``
        for use throughout the ``dehydrate/hydrate`` cycle.

        If no object is provided, an empty object from
        ``Resource._meta.object_class`` is created so that attempts to access
        ``bundle.obj`` do not fail.
        """
        if obj is None:
            obj = self._meta.object_class()

        return Bundle(
            obj=obj,
            data=data,
            request=request,
            objects_saved=objects_saved
        )

    def build_filters(self, filters=None):
        """
        Allows for the filtering of applicable objects.

        This needs to be implemented at the user level.'

        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        return filters

    def apply_sorting(self, obj_list, options=None):
        """
        Allows for the sorting of objects being returned.

        This needs to be implemented at the user level.

        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        return obj_list

    def get_bundle_detail_data(self, bundle):
        """
        Convenience method to return the ``detail_uri_name`` attribute off
        ``bundle.obj``.

        Usually just accesses ``bundle.obj.pk`` by default.
        """
        return getattr(bundle.obj, self._meta.detail_uri_name)

    # URL-related methods.

    def detail_uri_kwargs(self, bundle_or_obj):
        """
        This needs to be implemented at the user level.

        Given a ``Bundle`` or an object, it returns the extra kwargs needed to
        generate a detail URI.

        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        raise NotImplementedError()

    def resource_uri_kwargs(self, bundle_or_obj=None):
        """
        Builds a dictionary of kwargs to help generate URIs.

        Automatically provides the ``Resource.Meta.resource_name`` (and
        optionally the ``Resource.Meta.api_name`` if populated by an ``Api``
        object).

        If the ``bundle_or_obj`` argument is provided, it calls
        ``Resource.detail_uri_kwargs`` for additional bits to create
        """
        kwargs = {
            'resource_name': self._meta.resource_name,
        }

        if self._meta.api_name is not None:
            kwargs['api_name'] = self._meta.api_name

        if bundle_or_obj is not None:
            kwargs.update(self.detail_uri_kwargs(bundle_or_obj))

        return kwargs

    def get_resource_uri(self, bundle_or_obj=None, url_name='api_dispatch_list'):
        """
        Handles generating a resource URI.

        If the ``bundle_or_obj`` argument is not provided, it builds the URI
        for the list endpoint.

        If the ``bundle_or_obj`` argument is provided, it builds the URI for
        the detail endpoint.

        Return the generated URI. If that URI can not be reversed (not found
        in the URLconf), it will return an empty string.
        """
        if bundle_or_obj is not None:
            url_name = 'api_dispatch_detail'

        try:
            return self._build_reverse_url(url_name, kwargs=self.resource_uri_kwargs(bundle_or_obj))
        except NoReverseMatch:
            return ''

    def get_via_uri(self, uri, request=None):
        """
        This pulls apart the salient bits of the URI and populates the
        resource via a ``obj_get``.

        Optionally accepts a ``request``.

        If you need custom behavior based on other portions of the URI,
        simply override this method.
        """
        prefix = get_script_prefix()
        chomped_uri = uri

        if prefix and chomped_uri.startswith(prefix):
            chomped_uri = chomped_uri[len(prefix)-1:]

        try:
            view, args, kwargs = resolve(chomped_uri)
        except Resolver404:
            raise NotFound("The URL provided '%s' was not a link to a valid resource." % uri)

        bundle = self.build_bundle(request=request)
        return self.obj_get(bundle=bundle, **self.remove_api_resource_names(kwargs))

    # Data preparation.

    def full_dehydrate(self, bundle, for_list=False):
        """
        Given a bundle with an object instance, extract the information from it
        to populate the resource.
        """
        use_in = ['all', 'list' if for_list else 'detail']

        # Dehydrate each field.
        for field_name, field_object in self.fields.items():
            # If it's not for use in this mode, skip
            field_use_in = getattr(field_object, 'use_in', 'all')
            if callable(field_use_in):
                if not field_use_in(bundle):
                    continue
            else:
                if field_use_in not in use_in:
                    continue

            # A touch leaky but it makes URI resolution work.
            if getattr(field_object, 'dehydrated_type', None) == 'related':
                field_object.api_name = self._meta.api_name
                field_object.resource_name = self._meta.resource_name

            bundle.data[field_name] = field_object.dehydrate(bundle, for_list=for_list)

            # Check for an optional method to do further dehydration.
            method = getattr(self, "dehydrate_%s" % field_name, None)

            if method:
                bundle.data[field_name] = method(bundle)

        bundle = self.dehydrate(bundle)
        return bundle

    def dehydrate(self, bundle):
        """
        A hook to allow a final manipulation of data once all fields/methods
        have built out the dehydrated data.

        Useful if you need to access more than one dehydrated field or want
        to annotate on additional data.

        Must return the modified bundle.
        """
        return bundle

    def full_hydrate(self, bundle):
        """
        Given a populated bundle, distill it and turn it back into
        a full-fledged object instance.
        """
        if bundle.obj is None:
            bundle.obj = self._meta.object_class()

        bundle = self.hydrate(bundle)

        for field_name, field_object in self.fields.items():
            if field_object.readonly is True:
                continue

            # Check for an optional method to do further hydration.
            method = getattr(self, "hydrate_%s" % field_name, None)

            if method:
                bundle = method(bundle)

            if field_object.attribute:
                value = field_object.hydrate(bundle)

                # NOTE: We only get back a bundle when it is related field.
                if isinstance(value, Bundle) and value.errors.get(field_name):
                    bundle.errors[field_name] = value.errors[field_name]

                if value is not None or field_object.null:
                    # We need to avoid populating M2M data here as that will
                    # cause things to blow up.
                    if not getattr(field_object, 'is_related', False):
                        setattr(bundle.obj, field_object.attribute, value)
                    elif not getattr(field_object, 'is_m2m', False):
                        if value is not None:
                            # NOTE: A bug fix in Django (ticket #18153) fixes incorrect behavior
                            # which Tastypie was relying on.  To fix this, we store value.obj to
                            # be saved later in save_related.
                            try:
                                setattr(bundle.obj, field_object.attribute, value.obj)
                            except (ValueError, ObjectDoesNotExist):
                                bundle.related_objects_to_save[field_object.attribute] = value.obj
                        elif field_object.blank:
                            continue
                        elif field_object.null:
                            setattr(bundle.obj, field_object.attribute, value)

        return bundle

    def hydrate(self, bundle):
        """
        A hook to allow an initial manipulation of data before all methods/fields
        have built out the hydrated data.

        Useful if you need to access more than one hydrated field or want
        to annotate on additional data.

        Must return the modified bundle.
        """
        return bundle

    def hydrate_m2m(self, bundle):
        """
        Populate the ManyToMany data on the instance.
        """
        if bundle.obj is None:
            raise HydrationError("You must call 'full_hydrate' before attempting to run 'hydrate_m2m' on %r." % self)

        for field_name, field_object in self.fields.items():
            if not getattr(field_object, 'is_m2m', False):
                continue

            if field_object.attribute:
                # Note that we only hydrate the data, leaving the instance
                # unmodified. It's up to the user's code to handle this.
                # The ``ModelResource`` provides a working baseline
                # in this regard.
                bundle.data[field_name] = field_object.hydrate_m2m(bundle)

        for field_name, field_object in self.fields.items():
            if not getattr(field_object, 'is_m2m', False):
                continue

            method = getattr(self, "hydrate_%s" % field_name, None)

            if method:
                method(bundle)

        return bundle

    def build_schema(self):
        """
        Returns a dictionary of all the fields on the resource and some
        properties about those fields.

        Used by the ``schema/`` endpoint to describe what will be available.
        """
        data = {
            'fields': {},
            'default_format': self._meta.default_format,
            'allowed_list_http_methods': self._meta.list_allowed_methods,
            'allowed_detail_http_methods': self._meta.detail_allowed_methods,
            'default_limit': self._meta.limit,
        }

        if self._meta.ordering:
            data['ordering'] = self._meta.ordering

        if self._meta.filtering:
            data['filtering'] = self._meta.filtering

        for field_name, field_object in self.fields.items():
            data['fields'][field_name] = {
                'default': field_object.default,
                'type': field_object.dehydrated_type,
                'nullable': field_object.null,
                'blank': field_object.blank,
                'readonly': field_object.readonly,
                'help_text': field_object.help_text,
                'unique': field_object.unique,
            }
            if field_object.dehydrated_type == 'related':
                if getattr(field_object, 'is_m2m', False):
                    related_type = 'to_many'
                else:
                    related_type = 'to_one'
                data['fields'][field_name]['related_type'] = related_type

        return data

    def dehydrate_resource_uri(self, bundle):
        """
        For the automatically included ``resource_uri`` field, dehydrate
        the URI for the given bundle.

        Returns empty string if no URI can be generated.
        """
        try:
            return self.get_resource_uri(bundle)
        except NotImplementedError:
            return ''
        except NoReverseMatch:
            return ''

    def generate_cache_key(self, *args, **kwargs):
        """
        Creates a unique-enough cache key.

        This is based off the current api_name/resource_name/args/kwargs.
        """
        smooshed = []

        for key, value in kwargs.items():
            smooshed.append("%s=%s" % (key, value))

        # Use a list plus a ``.join()`` because it's faster than concatenation.
        return "%s:%s:%s:%s" % (self._meta.api_name, self._meta.resource_name, ':'.join(args), ':'.join(smooshed))

    # Data access methods.

    def get_object_list(self, request):
        """
        A hook to allow making returning the list of available objects.

        This needs to be implemented at the user level.

        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        raise NotImplementedError()

    def apply_authorization_limits(self, request, object_list):
        """
        Deprecated.

        FIXME: REMOVE BEFORE 1.0
        """
        return self._meta.authorization.apply_limits(request, object_list)

    def can_create(self):
        """
        Checks to ensure ``post`` is within ``allowed_methods``.
        """
        allowed = set(self._meta.list_allowed_methods + self._meta.detail_allowed_methods)
        return 'post' in allowed

    def can_update(self):
        """
        Checks to ensure ``put`` is within ``allowed_methods``.

        Used when hydrating related data.
        """
        allowed = set(self._meta.list_allowed_methods + self._meta.detail_allowed_methods)
        return 'put' in allowed

    def can_delete(self):
        """
        Checks to ensure ``delete`` is within ``allowed_methods``.
        """
        allowed = set(self._meta.list_allowed_methods + self._meta.detail_allowed_methods)
        return 'delete' in allowed

    def apply_filters(self, request, applicable_filters):
        """
        A hook to alter how the filters are applied to the object list.

        This needs to be implemented at the user level.

        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        raise NotImplementedError()

    def obj_get_list(self, bundle, **kwargs):
        """
        Fetches the list of objects available on the resource.

        This needs to be implemented at the user level.

        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        raise NotImplementedError()

    def cached_obj_get_list(self, bundle, **kwargs):
        """
        A version of ``obj_get_list`` that uses the cache as a means to get
        commonly-accessed data faster.
        """
        cache_key = self.generate_cache_key('list', **kwargs)
        obj_list = self._meta.cache.get(cache_key)

        if obj_list is None:
            obj_list = self.obj_get_list(bundle=bundle, **kwargs)
            self._meta.cache.set(cache_key, obj_list)

        return obj_list

    def obj_get(self, bundle, **kwargs):
        """
        Fetches an individual object on the resource.

        This needs to be implemented at the user level. If the object can not
        be found, this should raise a ``NotFound`` exception.

        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        raise NotImplementedError()

    def cached_obj_get(self, bundle, **kwargs):
        """
        A version of ``obj_get`` that uses the cache as a means to get
        commonly-accessed data faster.
        """
        cache_key = self.generate_cache_key('detail', **kwargs)
        cached_bundle = self._meta.cache.get(cache_key)

        if cached_bundle is None:
            cached_bundle = self.obj_get(bundle=bundle, **kwargs)
            self._meta.cache.set(cache_key, cached_bundle)

        return cached_bundle

    def obj_create(self, bundle, **kwargs):
        """
        Creates a new object based on the provided data.

        This needs to be implemented at the user level.

        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        raise NotImplementedError()

    def obj_update(self, bundle, **kwargs):
        """
        Updates an existing object (or creates a new object) based on the
        provided data.

        This needs to be implemented at the user level.

        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        raise NotImplementedError()

    def obj_delete_list(self, bundle, **kwargs):
        """
        Deletes an entire list of objects.

        This needs to be implemented at the user level.

        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        raise NotImplementedError()

    def obj_delete_list_for_update(self, bundle, **kwargs):
        """
        Deletes an entire list of objects, specific to PUT list.

        This needs to be implemented at the user level.

        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        raise NotImplementedError()

    def obj_delete(self, bundle, **kwargs):
        """
        Deletes a single object.

        This needs to be implemented at the user level.

        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        raise NotImplementedError()

    def create_response(self, request, data, response_class=HttpResponse, **response_kwargs):
        """
        Extracts the common "which-format/serialize/return-response" cycle.

        Mostly a useful shortcut/hook.
        """
        desired_format = self.determine_format(request)
        serialized = self.serialize(request, data, desired_format)
        return response_class(content=serialized, content_type=build_content_type(desired_format), **response_kwargs)

    def error_response(self, request, errors, response_class=None):
        """
        Extracts the common "which-format/serialize/return-error-response"
        cycle.

        Should be used as much as possible to return errors.
        """
        if response_class is None:
            response_class = http.HttpBadRequest

        desired_format = None

        if request:
            if request.GET.get('callback', None) is None:
                try:
                    desired_format = self.determine_format(request)
                except BadRequest:
                    pass  # Fall through to default handler below
            else:
                # JSONP can cause extra breakage.
                desired_format = 'application/json'

        if not desired_format:
            desired_format = self._meta.default_format

        try:
            serialized = self.serialize(request, errors, desired_format)
        except BadRequest, e:
            error = "Additional errors occurred, but serialization of those errors failed."

            if settings.DEBUG:
                error += " %s" % e

            return response_class(content=error, content_type='text/plain')

        return response_class(content=serialized, content_type=build_content_type(desired_format))

    def is_valid(self, bundle):
        """
        Handles checking if the data provided by the user is valid.

        Mostly a hook, this uses class assigned to ``validation`` from
        ``Resource._meta``.

        If validation fails, an error is raised with the error messages
        serialized inside it.
        """
        errors = self._meta.validation.is_valid(bundle, bundle.request)

        if errors:
            bundle.errors[self._meta.resource_name] = errors
            return False

        return True

    def rollback(self, bundles):
        """
        Given the list of bundles, delete all objects pertaining to those
        bundles.

        This needs to be implemented at the user level. No exceptions should
        be raised if possible.

        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        raise NotImplementedError()

    # Views.

    def get_list(self, request, **kwargs):
        """
        Returns a serialized list of resources.

        Calls ``obj_get_list`` to provide the data, then handles that result
        set and serializes it.

        Should return a HttpResponse (200 OK).
        """
        # TODO: Uncached for now. Invalidation that works for everyone may be
        #       impossible.
        base_bundle = self.build_bundle(request=request)
        objects = self.obj_get_list(bundle=base_bundle, **self.remove_api_resource_names(kwargs))
        sorted_objects = self.apply_sorting(objects, options=request.GET)

        paginator = self._meta.paginator_class(request.GET, sorted_objects, resource_uri=self.get_resource_uri(), limit=self._meta.limit, max_limit=self._meta.max_limit, collection_name=self._meta.collection_name)
        to_be_serialized = paginator.page()

        # Dehydrate the bundles in preparation for serialization.
        bundles = []

        for obj in to_be_serialized[self._meta.collection_name]:
            bundle = self.build_bundle(obj=obj, request=request)
            bundles.append(self.full_dehydrate(bundle, for_list=True))

        to_be_serialized[self._meta.collection_name] = bundles
        to_be_serialized = self.alter_list_data_to_serialize(request, to_be_serialized)
        return self.create_response(request, to_be_serialized)

    def get_detail(self, request, **kwargs):
        """
        Returns a single serialized resource.

        Calls ``cached_obj_get/obj_get`` to provide the data, then handles that result
        set and serializes it.

        Should return a HttpResponse (200 OK).
        """
        basic_bundle = self.build_bundle(request=request)

        try:
            obj = self.cached_obj_get(bundle=basic_bundle, **self.remove_api_resource_names(kwargs))
        except ObjectDoesNotExist:
            return http.HttpNotFound()
        except MultipleObjectsReturned:
            return http.HttpMultipleChoices("More than one resource is found at this URI.")

        bundle = self.build_bundle(obj=obj, request=request)
        bundle = self.full_dehydrate(bundle)
        bundle = self.alter_detail_data_to_serialize(request, bundle)
        return self.create_response(request, bundle)

    def post_list(self, request, **kwargs):
        """
        Creates a new resource/object with the provided data.

        Calls ``obj_create`` with the provided data and returns a response
        with the new resource's location.

        If a new resource is created, return ``HttpCreated`` (201 Created).
        If ``Meta.always_return_data = True``, there will be a populated body
        of serialized data.
        """
        if django.VERSION >= (1, 4):
            body = request.body
        else:
            body = request.raw_post_data
        deserialized = self.deserialize(request, body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        deserialized = self.alter_deserialized_detail_data(request, deserialized)
        bundle = self.build_bundle(data=dict_strip_unicode_keys(deserialized), request=request)
        updated_bundle = self.obj_create(bundle, **self.remove_api_resource_names(kwargs))
        location = self.get_resource_uri(updated_bundle)

        if not self._meta.always_return_data:
            return http.HttpCreated(location=location)
        else:
            updated_bundle = self.full_dehydrate(updated_bundle)
            updated_bundle = self.alter_detail_data_to_serialize(request, updated_bundle)
            return self.create_response(request, updated_bundle, response_class=http.HttpCreated, location=location)

    def post_detail(self, request, **kwargs):
        """
        Creates a new subcollection of the resource under a resource.

        This is not implemented by default because most people's data models
        aren't self-referential.

        If a new resource is created, return ``HttpCreated`` (201 Created).
        """
        return http.HttpNotImplemented()

    def put_list(self, request, **kwargs):
        """
        Replaces a collection of resources with another collection.

        Calls ``delete_list`` to clear out the collection then ``obj_create``
        with the provided the data to create the new collection.

        Return ``HttpNoContent`` (204 No Content) if
        ``Meta.always_return_data = False`` (default).

        Return ``HttpAccepted`` (202 Accepted) if
        ``Meta.always_return_data = True``.
        """
        if django.VERSION >= (1, 4):
            body = request.body
        else:
            body = request.raw_post_data
        deserialized = self.deserialize(request, body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        deserialized = self.alter_deserialized_list_data(request, deserialized)

        if not self._meta.collection_name in deserialized:
            raise BadRequest("Invalid data sent.")

        basic_bundle = self.build_bundle(request=request)
        self.obj_delete_list_for_update(bundle=basic_bundle, **self.remove_api_resource_names(kwargs))
        bundles_seen = []

        for object_data in deserialized[self._meta.collection_name]:
            bundle = self.build_bundle(data=dict_strip_unicode_keys(object_data), request=request)

            # Attempt to be transactional, deleting any previously created
            # objects if validation fails.
            try:
                self.obj_create(bundle=bundle, **self.remove_api_resource_names(kwargs))
                bundles_seen.append(bundle)
            except ImmediateHttpResponse:
                self.rollback(bundles_seen)
                raise

        if not self._meta.always_return_data:
            return http.HttpNoContent()
        else:
            to_be_serialized = {}
            to_be_serialized[self._meta.collection_name] = [self.full_dehydrate(bundle, for_list=True) for bundle in bundles_seen]
            to_be_serialized = self.alter_list_data_to_serialize(request, to_be_serialized)
            return self.create_response(request, to_be_serialized, response_class=http.HttpAccepted)

    def put_detail(self, request, **kwargs):
        """
        Either updates an existing resource or creates a new one with the
        provided data.

        Calls ``obj_update`` with the provided data first, but falls back to
        ``obj_create`` if the object does not already exist.

        If a new resource is created, return ``HttpCreated`` (201 Created).
        If ``Meta.always_return_data = True``, there will be a populated body
        of serialized data.

        If an existing resource is modified and
        ``Meta.always_return_data = False`` (default), return ``HttpNoContent``
        (204 No Content).
        If an existing resource is modified and
        ``Meta.always_return_data = True``, return ``HttpAccepted`` (202
        Accepted).
        """
        if django.VERSION >= (1, 4):
            body = request.body
        else:
            body = request.raw_post_data
        deserialized = self.deserialize(request, body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        deserialized = self.alter_deserialized_detail_data(request, deserialized)
        bundle = self.build_bundle(data=dict_strip_unicode_keys(deserialized), request=request)

        try:
            updated_bundle = self.obj_update(bundle=bundle, **self.remove_api_resource_names(kwargs))

            if not self._meta.always_return_data:
                return http.HttpNoContent()
            else:
                updated_bundle = self.full_dehydrate(updated_bundle)
                updated_bundle = self.alter_detail_data_to_serialize(request, updated_bundle)
                return self.create_response(request, updated_bundle, response_class=http.HttpAccepted)
        except (NotFound, MultipleObjectsReturned):
            updated_bundle = self.obj_create(bundle=bundle, **self.remove_api_resource_names(kwargs))
            location = self.get_resource_uri(updated_bundle)

            if not self._meta.always_return_data:
                return http.HttpCreated(location=location)
            else:
                updated_bundle = self.full_dehydrate(updated_bundle)
                updated_bundle = self.alter_detail_data_to_serialize(request, updated_bundle)
                return self.create_response(request, updated_bundle, response_class=http.HttpCreated, location=location)

    def delete_list(self, request, **kwargs):
        """
        Destroys a collection of resources/objects.

        Calls ``obj_delete_list``.

        If the resources are deleted, return ``HttpNoContent`` (204 No Content).
        """
        bundle = self.build_bundle(request=request)
        self.obj_delete_list(bundle=bundle, request=request, **self.remove_api_resource_names(kwargs))
        return http.HttpNoContent()

    def delete_detail(self, request, **kwargs):
        """
        Destroys a single resource/object.

        Calls ``obj_delete``.

        If the resource is deleted, return ``HttpNoContent`` (204 No Content).
        If the resource did not exist, return ``Http404`` (404 Not Found).
        """
        # Manually construct the bundle here, since we don't want to try to
        # delete an empty instance.
        bundle = Bundle(request=request)

        try:
            self.obj_delete(bundle=bundle, **self.remove_api_resource_names(kwargs))
            return http.HttpNoContent()
        except NotFound:
            return http.HttpNotFound()

    def patch_list(self, request, **kwargs):
        """
        Updates a collection in-place.

        The exact behavior of ``PATCH`` to a list resource is still the matter of
        some debate in REST circles, and the ``PATCH`` RFC isn't standard. So the
        behavior this method implements (described below) is something of a
        stab in the dark. It's mostly cribbed from GData, with a smattering
        of ActiveResource-isms and maybe even an original idea or two.

        The ``PATCH`` format is one that's similar to the response returned from
        a ``GET`` on a list resource::

            {
              "objects": [{object}, {object}, ...],
              "deleted_objects": ["URI", "URI", "URI", ...],
            }

        For each object in ``objects``:

            * If the dict does not have a ``resource_uri`` key then the item is
              considered "new" and is handled like a ``POST`` to the resource list.

            * If the dict has a ``resource_uri`` key and the ``resource_uri`` refers
              to an existing resource then the item is a update; it's treated
              like a ``PATCH`` to the corresponding resource detail.

            * If the dict has a ``resource_uri`` but the resource *doesn't* exist,
              then this is considered to be a create-via-``PUT``.

        Each entry in ``deleted_objects`` referes to a resource URI of an existing
        resource to be deleted; each is handled like a ``DELETE`` to the relevent
        resource.

        In any case:

            * If there's a resource URI it *must* refer to a resource of this
              type. It's an error to include a URI of a different resource.

            * ``PATCH`` is all or nothing. If a single sub-operation fails, the
              entire request will fail and all resources will be rolled back.

          * For ``PATCH`` to work, you **must** have ``put`` in your
            :ref:`detail-allowed-methods` setting.

          * To delete objects via ``deleted_objects`` in a ``PATCH`` request you
            **must** have ``delete`` in your :ref:`detail-allowed-methods`
            setting.

        Substitute appropriate names for ``objects`` and
        ``deleted_objects`` if ``Meta.collection_name`` is set to something
        other than ``objects`` (default).
        """
        request = convert_post_to_patch(request)
        if django.VERSION >= (1, 4):
            body = request.body
        else:
            body = request.raw_post_data
        deserialized = self.deserialize(request, body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        collection_name = self._meta.collection_name
        deleted_collection_name = 'deleted_%s' % collection_name
        if collection_name not in deserialized:
            raise BadRequest("Invalid data sent: missing '%s'" % collection_name)

        if len(deserialized[collection_name]) and 'put' not in self._meta.detail_allowed_methods:
            raise ImmediateHttpResponse(response=http.HttpMethodNotAllowed())

        bundles_seen = []

        for data in deserialized[collection_name]:
            # If there's a resource_uri then this is either an
            # update-in-place or a create-via-PUT.
            if "resource_uri" in data:
                uri = data.pop('resource_uri')

                try:
                    obj = self.get_via_uri(uri, request=request)

                    # The object does exist, so this is an update-in-place.
                    bundle = self.build_bundle(obj=obj, request=request)
                    bundle = self.full_dehydrate(bundle, for_list=True)
                    bundle = self.alter_detail_data_to_serialize(request, bundle)
                    self.update_in_place(request, bundle, data)
                except (ObjectDoesNotExist, MultipleObjectsReturned):
                    # The object referenced by resource_uri doesn't exist,
                    # so this is a create-by-PUT equivalent.
                    data = self.alter_deserialized_detail_data(request, data)
                    bundle = self.build_bundle(data=dict_strip_unicode_keys(data), request=request)
                    self.obj_create(bundle=bundle)
            else:
                # There's no resource URI, so this is a create call just
                # like a POST to the list resource.
                data = self.alter_deserialized_detail_data(request, data)
                bundle = self.build_bundle(data=dict_strip_unicode_keys(data), request=request)
                self.obj_create(bundle=bundle)

            bundles_seen.append(bundle)

        deleted_collection = deserialized.get(deleted_collection_name, [])

        if deleted_collection:
            if 'delete' not in self._meta.detail_allowed_methods:
                raise ImmediateHttpResponse(response=http.HttpMethodNotAllowed())

            for uri in deleted_collection:
                obj = self.get_via_uri(uri, request=request)
                bundle = self.build_bundle(obj=obj, request=request)
                self.obj_delete(bundle=bundle)

        if not self._meta.always_return_data:
            return http.HttpAccepted()
        else:
            to_be_serialized = {}
            to_be_serialized['objects'] = [self.full_dehydrate(bundle, for_list=True) for bundle in bundles_seen]
            to_be_serialized = self.alter_list_data_to_serialize(request, to_be_serialized)
            return self.create_response(request, to_be_serialized, response_class=http.HttpAccepted)

    def patch_detail(self, request, **kwargs):
        """
        Updates a resource in-place.

        Calls ``obj_update``.

        If the resource is updated, return ``HttpAccepted`` (202 Accepted).
        If the resource did not exist, return ``HttpNotFound`` (404 Not Found).
        """
        request = convert_post_to_patch(request)
        basic_bundle = self.build_bundle(request=request)

        # We want to be able to validate the update, but we can't just pass
        # the partial data into the validator since all data needs to be
        # present. Instead, we basically simulate a PUT by pulling out the
        # original data and updating it in-place.
        # So first pull out the original object. This is essentially
        # ``get_detail``.
        try:
            obj = self.cached_obj_get(bundle=basic_bundle, **self.remove_api_resource_names(kwargs))
        except ObjectDoesNotExist:
            return http.HttpNotFound()
        except MultipleObjectsReturned:
            return http.HttpMultipleChoices("More than one resource is found at this URI.")

        bundle = self.build_bundle(obj=obj, request=request)
        bundle = self.full_dehydrate(bundle)
        bundle = self.alter_detail_data_to_serialize(request, bundle)

        # Now update the bundle in-place.
        if django.VERSION >= (1, 4):
            body = request.body
        else:
            body = request.raw_post_data
        deserialized = self.deserialize(request, body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        self.update_in_place(request, bundle, deserialized)

        if not self._meta.always_return_data:
            return http.HttpAccepted()
        else:
            bundle = self.full_dehydrate(bundle)
            bundle = self.alter_detail_data_to_serialize(request, bundle)
            return self.create_response(request, bundle, response_class=http.HttpAccepted)

    def update_in_place(self, request, original_bundle, new_data):
        """
        Update the object in original_bundle in-place using new_data.
        """
        original_bundle.data.update(**dict_strip_unicode_keys(new_data))

        # Now we've got a bundle with the new data sitting in it and we're
        # we're basically in the same spot as a PUT request. SO the rest of this
        # function is cribbed from put_detail.
        self.alter_deserialized_detail_data(request, original_bundle.data)
        kwargs = {
            self._meta.detail_uri_name: self.get_bundle_detail_data(original_bundle),
            'request': request,
        }
        return self.obj_update(bundle=original_bundle, **kwargs)

    def get_schema(self, request, **kwargs):
        """
        Returns a serialized form of the schema of the resource.

        Calls ``build_schema`` to generate the data. This method only responds
        to HTTP GET.

        Should return a HttpResponse (200 OK).
        """
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)
        self.log_throttled_access(request)
        bundle = self.build_bundle(request=request)
        self.authorized_read_detail(self.get_object_list(bundle.request), bundle)
        return self.create_response(request, self.build_schema())

    def get_multiple(self, request, **kwargs):
        """
        Returns a serialized list of resources based on the identifiers
        from the URL.

        Calls ``obj_get`` to fetch only the objects requested. This method
        only responds to HTTP GET.

        Should return a HttpResponse (200 OK).
        """
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        # Rip apart the list then iterate.
        kwarg_name = '%s_list' % self._meta.detail_uri_name
        obj_identifiers = kwargs.get(kwarg_name, '').split(';')
        objects = []
        not_found = []
        base_bundle = self.build_bundle(request=request)

        for identifier in obj_identifiers:
            try:
                obj = self.obj_get(bundle=base_bundle, **{self._meta.detail_uri_name: identifier})
                bundle = self.build_bundle(obj=obj, request=request)
                bundle = self.full_dehydrate(bundle, for_list=True)
                objects.append(bundle)
            except (ObjectDoesNotExist, Unauthorized):
                not_found.append(identifier)

        object_list = {
            self._meta.collection_name: objects,
        }

        if len(not_found):
            object_list['not_found'] = not_found

        self.log_throttled_access(request)
        return self.create_response(request, object_list)


class ModelDeclarativeMetaclass(DeclarativeMetaclass):
    def __new__(cls, name, bases, attrs):
        meta = attrs.get('Meta')

        if meta and hasattr(meta, 'queryset'):
            setattr(meta, 'object_class', meta.queryset.model)

        new_class = super(ModelDeclarativeMetaclass, cls).__new__(cls, name, bases, attrs)
        include_fields = getattr(new_class._meta, 'fields', [])
        excludes = getattr(new_class._meta, 'excludes', [])
        field_names = new_class.base_fields.keys()

        for field_name in field_names:
            if field_name == 'resource_uri':
                continue
            if field_name in new_class.declared_fields:
                continue
            if len(include_fields) and not field_name in include_fields:
                del(new_class.base_fields[field_name])
            if len(excludes) and field_name in excludes:
                del(new_class.base_fields[field_name])

        # Add in the new fields.
        new_class.base_fields.update(new_class.get_fields(include_fields, excludes))

        if getattr(new_class._meta, 'include_absolute_url', True):
            if not 'absolute_url' in new_class.base_fields:
                new_class.base_fields['absolute_url'] = fields.CharField(attribute='get_absolute_url', readonly=True)
        elif 'absolute_url' in new_class.base_fields and not 'absolute_url' in attrs:
            del(new_class.base_fields['absolute_url'])

        return new_class


class ModelResource(Resource):
    """
    A subclass of ``Resource`` designed to work with Django's ``Models``.

    This class will introspect a given ``Model`` and build a field list based
    on the fields found on the model (excluding relational fields).

    Given that it is aware of Django's ORM, it also handles the CRUD data
    operations of the resource.
    """
    __metaclass__ = ModelDeclarativeMetaclass

    @classmethod
    def should_skip_field(cls, field):
        """
        Given a Django model field, return if it should be included in the
        contributed ApiFields.
        """
        # Ignore certain fields (related fields).
        if getattr(field, 'rel'):
            return True

        return False

    @classmethod
    def api_field_from_django_field(cls, f, default=fields.CharField):
        """
        Returns the field type that would likely be associated with each
        Django type.
        """
        result = default
        internal_type = f.get_internal_type()

        if internal_type in ('DateField', 'DateTimeField'):
            result = fields.DateTimeField
        elif internal_type in ('BooleanField', 'NullBooleanField'):
            result = fields.BooleanField
        elif internal_type in ('FloatField',):
            result = fields.FloatField
        elif internal_type in ('DecimalField',):
            result = fields.DecimalField
        elif internal_type in ('IntegerField', 'PositiveIntegerField', 'PositiveSmallIntegerField', 'SmallIntegerField', 'AutoField'):
            result = fields.IntegerField
        elif internal_type in ('FileField', 'ImageField'):
            result = fields.FileField
        elif internal_type == 'TimeField':
            result = fields.TimeField
        # TODO: Perhaps enable these via introspection. The reason they're not enabled
        #       by default is the very different ``__init__`` they have over
        #       the other fields.
        # elif internal_type == 'ForeignKey':
        #     result = ForeignKey
        # elif internal_type == 'ManyToManyField':
        #     result = ManyToManyField

        return result

    @classmethod
    def get_fields(cls, fields=None, excludes=None):
        """
        Given any explicit fields to include and fields to exclude, add
        additional fields based on the associated model.
        """
        final_fields = {}
        fields = fields or []
        excludes = excludes or []

        if not cls._meta.object_class:
            return final_fields

        for f in cls._meta.object_class._meta.fields:
            # If the field name is already present, skip
            if f.name in cls.base_fields:
                continue

            # If field is not present in explicit field listing, skip
            if fields and f.name not in fields:
                continue

            # If field is in exclude list, skip
            if excludes and f.name in excludes:
                continue

            if cls.should_skip_field(f):
                continue

            api_field_class = cls.api_field_from_django_field(f)

            kwargs = {
                'attribute': f.name,
                'help_text': f.help_text,
            }

            if f.null is True:
                kwargs['null'] = True

            kwargs['unique'] = f.unique

            if not f.null and f.blank is True:
                kwargs['default'] = ''
                kwargs['blank'] = True

            if f.get_internal_type() == 'TextField':
                kwargs['default'] = ''

            if f.has_default():
                kwargs['default'] = f.default

            if getattr(f, 'auto_now', False):
                kwargs['default'] = f.auto_now

            if getattr(f, 'auto_now_add', False):
                kwargs['default'] = f.auto_now_add

            final_fields[f.name] = api_field_class(**kwargs)
            final_fields[f.name].instance_name = f.name

        return final_fields

    def check_filtering(self, field_name, filter_type='exact', filter_bits=None):
        """
        Given a field name, a optional filter type and an optional list of
        additional relations, determine if a field can be filtered on.

        If a filter does not meet the needed conditions, it should raise an
        ``InvalidFilterError``.

        If the filter meets the conditions, a list of attribute names (not
        field names) will be returned.
        """
        if filter_bits is None:
            filter_bits = []

        if not field_name in self._meta.filtering:
            raise InvalidFilterError("The '%s' field does not allow filtering." % field_name)

        # Check to see if it's an allowed lookup type.
        if not self._meta.filtering[field_name] in (ALL, ALL_WITH_RELATIONS):
            # Must be an explicit whitelist.
            if not filter_type in self._meta.filtering[field_name]:
                raise InvalidFilterError("'%s' is not an allowed filter on the '%s' field." % (filter_type, field_name))

        if self.fields[field_name].attribute is None:
            raise InvalidFilterError("The '%s' field has no 'attribute' for searching with." % field_name)

        # Check to see if it's a relational lookup and if that's allowed.
        if len(filter_bits):
            if not getattr(self.fields[field_name], 'is_related', False):
                raise InvalidFilterError("The '%s' field does not support relations." % field_name)

            if not self._meta.filtering[field_name] == ALL_WITH_RELATIONS:
                raise InvalidFilterError("Lookups are not allowed more than one level deep on the '%s' field." % field_name)

            # Recursively descend through the remaining lookups in the filter,
            # if any. We should ensure that all along the way, we're allowed
            # to filter on that field by the related resource.
            related_resource = self.fields[field_name].get_related_resource(None)
            return [self.fields[field_name].attribute] + related_resource.check_filtering(filter_bits[0], filter_type, filter_bits[1:])

        return [self.fields[field_name].attribute]

    def filter_value_to_python(self, value, field_name, filters, filter_expr,
            filter_type):
        """
        Turn the string ``value`` into a python object.
        """
        # Simple values
        if value in ['true', 'True', True]:
            value = True
        elif value in ['false', 'False', False]:
            value = False
        elif value in ('nil', 'none', 'None', None):
            value = None

        # Split on ',' if not empty string and either an in or range filter.
        if filter_type in ('in', 'range') and len(value):
            if hasattr(filters, 'getlist'):
                value = []

                for part in filters.getlist(filter_expr):
                    value.extend(part.split(','))
            else:
                value = value.split(',')

        return value

    def build_filters(self, filters=None):
        """
        Given a dictionary of filters, create the necessary ORM-level filters.

        Keys should be resource fields, **NOT** model fields.

        Valid values are either a list of Django filter types (i.e.
        ``['startswith', 'exact', 'lte']``), the ``ALL`` constant or the
        ``ALL_WITH_RELATIONS`` constant.
        """
        # At the declarative level:
        #     filtering = {
        #         'resource_field_name': ['exact', 'startswith', 'endswith', 'contains'],
        #         'resource_field_name_2': ['exact', 'gt', 'gte', 'lt', 'lte', 'range'],
        #         'resource_field_name_3': ALL,
        #         'resource_field_name_4': ALL_WITH_RELATIONS,
        #         ...
        #     }
        # Accepts the filters as a dict. None by default, meaning no filters.
        if filters is None:
            filters = {}

        qs_filters = {}

        if getattr(self._meta, 'queryset', None) is not None:
            # Get the possible query terms from the current QuerySet.
            if hasattr(self._meta.queryset.query.query_terms, 'keys'):
                # Django 1.4 & below compatibility.
                query_terms = self._meta.queryset.query.query_terms.keys()
            else:
                # Django 1.5+.
                query_terms = self._meta.queryset.query.query_terms
        else:
            if hasattr(QUERY_TERMS, 'keys'):
                # Django 1.4 & below compatibility.
                query_terms = QUERY_TERMS.keys()
            else:
                # Django 1.5+.
                query_terms = QUERY_TERMS

        for filter_expr, value in filters.items():
            filter_bits = filter_expr.split(LOOKUP_SEP)
            field_name = filter_bits.pop(0)
            filter_type = 'exact'

            if not field_name in self.fields:
                # It's not a field we know about. Move along citizen.
                continue

            if len(filter_bits) and filter_bits[-1] in query_terms:
                filter_type = filter_bits.pop()

            lookup_bits = self.check_filtering(field_name, filter_type, filter_bits)
            value = self.filter_value_to_python(value, field_name, filters, filter_expr, filter_type)

            db_field_name = LOOKUP_SEP.join(lookup_bits)
            qs_filter = "%s%s%s" % (db_field_name, LOOKUP_SEP, filter_type)
            qs_filters[qs_filter] = value

        return dict_strip_unicode_keys(qs_filters)

    def apply_sorting(self, obj_list, options=None):
        """
        Given a dictionary of options, apply some ORM-level sorting to the
        provided ``QuerySet``.

        Looks for the ``order_by`` key and handles either ascending (just the
        field name) or descending (the field name with a ``-`` in front).

        The field name should be the resource field, **NOT** model field.
        """
        if options is None:
            options = {}

        parameter_name = 'order_by'

        if not 'order_by' in options:
            if not 'sort_by' in options:
                # Nothing to alter the order. Return what we've got.
                return obj_list
            else:
                warnings.warn("'sort_by' is a deprecated parameter. Please use 'order_by' instead.")
                parameter_name = 'sort_by'

        order_by_args = []

        if hasattr(options, 'getlist'):
            order_bits = options.getlist(parameter_name)
        else:
            order_bits = options.get(parameter_name)

            if not isinstance(order_bits, (list, tuple)):
                order_bits = [order_bits]

        for order_by in order_bits:
            order_by_bits = order_by.split(LOOKUP_SEP)

            field_name = order_by_bits[0]
            order = ''

            if order_by_bits[0].startswith('-'):
                field_name = order_by_bits[0][1:]
                order = '-'

            if not field_name in self.fields:
                # It's not a field we know about. Move along citizen.
                raise InvalidSortError("No matching '%s' field for ordering on." % field_name)

            if not field_name in self._meta.ordering:
                raise InvalidSortError("The '%s' field does not allow ordering." % field_name)

            if self.fields[field_name].attribute is None:
                raise InvalidSortError("The '%s' field has no 'attribute' for ordering with." % field_name)

            order_by_args.append("%s%s" % (order, LOOKUP_SEP.join([self.fields[field_name].attribute] + order_by_bits[1:])))

        return obj_list.order_by(*order_by_args)

    def apply_filters(self, request, applicable_filters):
        """
        An ORM-specific implementation of ``apply_filters``.

        The default simply applies the ``applicable_filters`` as ``**kwargs``,
        but should make it possible to do more advanced things.
        """
        return self.get_object_list(request).filter(**applicable_filters)

    def get_object_list(self, request):
        """
        An ORM-specific implementation of ``get_object_list``.

        Returns a queryset that may have been limited by other overrides.
        """
        return self._meta.queryset._clone()

    def obj_get_list(self, bundle, **kwargs):
        """
        A ORM-specific implementation of ``obj_get_list``.

        Takes an optional ``request`` object, whose ``GET`` dictionary can be
        used to narrow the query.
        """
        filters = {}

        if hasattr(bundle.request, 'GET'):
            # Grab a mutable copy.
            filters = bundle.request.GET.copy()

        # Update with the provided kwargs.
        filters.update(kwargs)
        applicable_filters = self.build_filters(filters=filters)

        try:
            objects = self.apply_filters(bundle.request, applicable_filters)
            return self.authorized_read_list(objects, bundle)
        except ValueError:
            raise BadRequest("Invalid resource lookup data provided (mismatched type).")

    def obj_get(self, bundle, **kwargs):
        """
        A ORM-specific implementation of ``obj_get``.

        Takes optional ``kwargs``, which are used to narrow the query to find
        the instance.
        """
        try:
            object_list = self.get_object_list(bundle.request).filter(**kwargs)
            stringified_kwargs = ', '.join(["%s=%s" % (k, v) for k, v in kwargs.items()])

            if len(object_list) <= 0:
                raise self._meta.object_class.DoesNotExist("Couldn't find an instance of '%s' which matched '%s'." % (self._meta.object_class.__name__, stringified_kwargs))
            elif len(object_list) > 1:
                raise MultipleObjectsReturned("More than '%s' matched '%s'." % (self._meta.object_class.__name__, stringified_kwargs))

            bundle.obj = object_list[0]
            self.authorized_read_detail(object_list, bundle)
            return bundle.obj
        except ValueError:
            raise NotFound("Invalid resource lookup data provided (mismatched type).")

    def obj_create(self, bundle, **kwargs):
        """
        A ORM-specific implementation of ``obj_create``.
        """
        bundle.obj = self._meta.object_class()

        for key, value in kwargs.items():
            setattr(bundle.obj, key, value)

        self.authorized_create_detail(self.get_object_list(bundle.request), bundle)
        bundle = self.full_hydrate(bundle)
        return self.save(bundle)

    def lookup_kwargs_with_identifiers(self, bundle, kwargs):
        """
        Kwargs here represent uri identifiers Ex: /repos/<user_id>/<repo_name>/
        We need to turn those identifiers into Python objects for generating
        lookup parameters that can find them in the DB
        """
        lookup_kwargs = {}
        bundle.obj = self.get_object_list(bundle.request).model()
        # Override data values, we rely on uri identifiers
        bundle.data.update(kwargs)
        # We're going to manually hydrate, as opposed to calling
        # ``full_hydrate``, to ensure we don't try to flesh out related
        # resources & keep things speedy.
        bundle = self.hydrate(bundle)

        for identifier in kwargs:
            if identifier == self._meta.detail_uri_name:
                lookup_kwargs[identifier] = kwargs[identifier]
                continue

            field_object = self.fields[identifier]

            # Skip readonly or related fields.
            if field_object.readonly is True or getattr(field_object, 'is_related', False):
                continue

            # Check for an optional method to do further hydration.
            method = getattr(self, "hydrate_%s" % identifier, None)

            if method:
                bundle = method(bundle)

            if field_object.attribute:
                value = field_object.hydrate(bundle)

            lookup_kwargs[identifier] = value

        return lookup_kwargs

    def obj_update(self, bundle, skip_errors=False, **kwargs):
        """
        A ORM-specific implementation of ``obj_update``.
        """
        if not bundle.obj or not self.get_bundle_detail_data(bundle):
            try:
                lookup_kwargs = self.lookup_kwargs_with_identifiers(bundle, kwargs)
            except:
                # if there is trouble hydrating the data, fall back to just
                # using kwargs by itself (usually it only contains a "pk" key
                # and this will work fine.
                lookup_kwargs = kwargs

            try:
                bundle.obj = self.obj_get(bundle=bundle, **lookup_kwargs)
            except ObjectDoesNotExist:
                raise NotFound("A model instance matching the provided arguments could not be found.")

        bundle = self.full_hydrate(bundle)
        return self.save(bundle, skip_errors=skip_errors)

    def obj_delete_list(self, bundle, **kwargs):
        """
        A ORM-specific implementation of ``obj_delete_list``.
        """
        objects_to_delete = self.obj_get_list(bundle=bundle, **kwargs)
        deletable_objects = self.authorized_delete_list(objects_to_delete, bundle)

        if hasattr(deletable_objects, 'delete'):
            # It's likely a ``QuerySet``. Call ``.delete()`` for efficiency.
            deletable_objects.delete()
        else:
            for authed_obj in deletable_objects:
                authed_obj.delete()

    def obj_delete_list_for_update(self, bundle, **kwargs):
        """
        A ORM-specific implementation of ``obj_delete_list_for_update``.
        """
        objects_to_delete = self.obj_get_list(bundle=bundle, **kwargs)
        deletable_objects = self.authorized_update_list(objects_to_delete, bundle)

        if hasattr(deletable_objects, 'delete'):
            # It's likely a ``QuerySet``. Call ``.delete()`` for efficiency.
            deletable_objects.delete()
        else:
            for authed_obj in deletable_objects:
                authed_obj.delete()

    def obj_delete(self, bundle, **kwargs):
        """
        A ORM-specific implementation of ``obj_delete``.

        Takes optional ``kwargs``, which are used to narrow the query to find
        the instance.
        """
        if not hasattr(bundle.obj, 'delete'):
            try:
                bundle.obj = self.obj_get(bundle=bundle, **kwargs)
            except ObjectDoesNotExist:
                raise NotFound("A model instance matching the provided arguments could not be found.")

        self.authorized_delete_detail(self.get_object_list(bundle.request), bundle)
        bundle.obj.delete()

    @transaction.commit_on_success()
    def patch_list(self, request, **kwargs):
        """
        An ORM-specific implementation of ``patch_list``.

        Necessary because PATCH should be atomic (all-success or all-fail)
        and the only way to do this neatly is at the database level.
        """
        return super(ModelResource, self).patch_list(request, **kwargs)

    def rollback(self, bundles):
        """
        A ORM-specific implementation of ``rollback``.

        Given the list of bundles, delete all models pertaining to those
        bundles.
        """
        for bundle in bundles:
            if bundle.obj and self.get_bundle_detail_data(bundle):
                bundle.obj.delete()

    def create_identifier(self, obj):
        return u"%s.%s.%s" % (obj._meta.app_label, obj._meta.module_name, obj.pk)

    def save(self, bundle, skip_errors=False):
        self.is_valid(bundle)

        if bundle.errors and not skip_errors:
            raise ImmediateHttpResponse(response=self.error_response(bundle.request, bundle.errors))

        # Check if they're authorized.
        if bundle.obj.pk:
            self.authorized_update_detail(self.get_object_list(bundle.request), bundle)
        else:
            self.authorized_create_detail(self.get_object_list(bundle.request), bundle)

        # Save FKs just in case.
        self.save_related(bundle)

        # Save the main object.
        bundle.obj.save()
        bundle.objects_saved.add(self.create_identifier(bundle.obj))

        # Now pick up the M2M bits.
        m2m_bundle = self.hydrate_m2m(bundle)
        self.save_m2m(m2m_bundle)
        return bundle

    def save_related(self, bundle):
        """
        Handles the saving of related non-M2M data.

        Calling assigning ``child.parent = parent`` & then calling
        ``Child.save`` isn't good enough to make sure the ``parent``
        is saved.

        To get around this, we go through all our related fields &
        call ``save`` on them if they have related, non-M2M data.
        M2M data is handled by the ``ModelResource.save_m2m`` method.
        """
        for field_name, field_object in self.fields.items():
            if not getattr(field_object, 'is_related', False):
                continue

            if getattr(field_object, 'is_m2m', False):
                continue

            if not field_object.attribute:
                continue

            if field_object.readonly:
                continue

            if field_object.blank and not bundle.data.has_key(field_name):
                continue

            # Get the object.
            try:
                related_obj = getattr(bundle.obj, field_object.attribute)
            except ObjectDoesNotExist:
                related_obj = bundle.related_objects_to_save.get(field_object.attribute, None)

            # Because sometimes it's ``None`` & that's OK.
            if related_obj:
                if field_object.related_name:
                    if not self.get_bundle_detail_data(bundle):
                        bundle.obj.save()

                    setattr(related_obj, field_object.related_name, bundle.obj)

                related_resource = field_object.get_related_resource(related_obj)

                # Before we build the bundle & try saving it, let's make sure we
                # haven't already saved it.
                obj_id = self.create_identifier(related_obj)

                if obj_id in bundle.objects_saved:
                    # It's already been saved. We're done here.
                    continue

                if bundle.data.get(field_name) and hasattr(bundle.data[field_name], 'keys'):
                    # Only build & save if there's data, not just a URI.
                    related_bundle = related_resource.build_bundle(
                        obj=related_obj,
                        data=bundle.data.get(field_name),
                        request=bundle.request,
                        objects_saved=bundle.objects_saved
                    )
                    related_resource.save(related_bundle)

                setattr(bundle.obj, field_object.attribute, related_obj)

    def save_m2m(self, bundle):
        """
        Handles the saving of related M2M data.

        Due to the way Django works, the M2M data must be handled after the
        main instance, which is why this isn't a part of the main ``save`` bits.

        Currently slightly inefficient in that it will clear out the whole
        relation and recreate the related data as needed.
        """
        for field_name, field_object in self.fields.items():
            if not getattr(field_object, 'is_m2m', False):
                continue

            if not field_object.attribute:
                continue

            if field_object.readonly:
                continue

            # Get the manager.
            related_mngr = None

            if isinstance(field_object.attribute, basestring):
                related_mngr = getattr(bundle.obj, field_object.attribute)
            elif callable(field_object.attribute):
                related_mngr = field_object.attribute(bundle)

            if not related_mngr:
                continue

            if hasattr(related_mngr, 'clear'):
                # FIXME: Dupe the original bundle, copy in the new object &
                #        check the perms on that (using the related resource)?

                # Clear it out, just to be safe.
                related_mngr.clear()

            related_objs = []

            for related_bundle in bundle.data[field_name]:
                related_resource = field_object.get_related_resource(bundle.obj)

                # Before we build the bundle & try saving it, let's make sure we
                # haven't already saved it.
                obj_id = self.create_identifier(related_bundle.obj)

                if obj_id in bundle.objects_saved:
                    # It's already been saved. We're done here.
                    continue

                # Only build & save if there's data, not just a URI.
                updated_related_bundle = related_resource.build_bundle(
                    obj=related_bundle.obj,
                    data=related_bundle.data,
                    request=bundle.request,
                    objects_saved=bundle.objects_saved
                )
                
                #Only save related models if they're newly added.
                if updated_related_bundle.obj._state.adding:
                    related_resource.save(updated_related_bundle)
                related_objs.append(updated_related_bundle.obj)

            related_mngr.add(*related_objs)

    def detail_uri_kwargs(self, bundle_or_obj):
        """
        Given a ``Bundle`` or an object (typically a ``Model`` instance),
        it returns the extra kwargs needed to generate a detail URI.

        By default, it uses the model's ``pk`` in order to create the URI.
        """
        kwargs = {}

        if isinstance(bundle_or_obj, Bundle):
            kwargs[self._meta.detail_uri_name] = getattr(bundle_or_obj.obj, self._meta.detail_uri_name)
        else:
            kwargs[self._meta.detail_uri_name] = getattr(bundle_or_obj, self._meta.detail_uri_name)

        return kwargs


class NamespacedModelResource(ModelResource):
    """
    A ModelResource subclass that respects Django namespaces.
    """
    def _build_reverse_url(self, name, args=None, kwargs=None):
        namespaced = "%s:%s" % (self._meta.urlconf_namespace, name)
        return reverse(namespaced, args=args, kwargs=kwargs)


# Based off of ``piston.utils.coerce_put_post``. Similarly BSD-licensed.
# And no, the irony is not lost on me.
def convert_post_to_VERB(request, verb):
    """
    Force Django to process the VERB.
    """
    if request.method == verb:
        if hasattr(request, '_post'):
            del(request._post)
            del(request._files)

        try:
            request.method = "POST"
            request._load_post_and_files()
            request.method = verb
        except AttributeError:
            request.META['REQUEST_METHOD'] = 'POST'
            request._load_post_and_files()
            request.META['REQUEST_METHOD'] = verb
        setattr(request, verb, request.POST)

    return request


def convert_post_to_put(request):
    return convert_post_to_VERB(request, verb='PUT')


def convert_post_to_patch(request):
    return convert_post_to_VERB(request, verb='PATCH')

########NEW FILE########
__FILENAME__ = serializers
import datetime
from StringIO import StringIO
import django
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.serializers import json
try:
    import json as simplejson
except ImportError: # < Python 2.6
    from django.utils import simplejson
from django.utils.encoding import force_unicode
from tastypie.bundle import Bundle
from tastypie.exceptions import BadRequest, UnsupportedFormat
from tastypie.utils import format_datetime, format_date, format_time, make_naive
try:
    import defusedxml.lxml as lxml
    from defusedxml.common import DefusedXmlException
    from defusedxml.lxml import parse as parse_xml
    from lxml.etree import Element, tostring, LxmlError
except ImportError:
    lxml = None
try:
    import yaml
    from django.core.serializers import pyyaml
except ImportError:
    yaml = None
try:
    import biplist
except ImportError:
    biplist = None


# Ugh & blah.
# So doing a regular dump is generally fine, since Tastypie doesn't usually
# serialize advanced types. *HOWEVER*, it will dump out Python Unicode strings
# as a custom YAML tag, which of course ``yaml.safe_load`` can't handle.
if yaml is not None:
    from yaml.constructor import SafeConstructor
    from yaml.loader import Reader, Scanner, Parser, Composer, Resolver

    class TastypieConstructor(SafeConstructor):
        def construct_yaml_unicode_dammit(self, node):
            value = self.construct_scalar(node)
            try:
                return value.encode('ascii')
            except UnicodeEncodeError:
                return value

    TastypieConstructor.add_constructor(u'tag:yaml.org,2002:python/unicode', TastypieConstructor.construct_yaml_unicode_dammit)

    class TastypieLoader(Reader, Scanner, Parser, Composer, TastypieConstructor, Resolver):
        def __init__(self, stream):
            Reader.__init__(self, stream)
            Scanner.__init__(self)
            Parser.__init__(self)
            Composer.__init__(self)
            TastypieConstructor.__init__(self)
            Resolver.__init__(self)


class Serializer(object):
    """
    A swappable class for serialization.

    This handles most types of data as well as the following output formats::

        * json
        * jsonp (Disabled by default)
        * xml
        * yaml
        * html
        * plist (see http://explorapp.com/biplist/)

    It was designed to make changing behavior easy, either by overridding the
    various format methods (i.e. ``to_json``), by changing the
    ``formats/content_types`` options or by altering the other hook methods.
    """

    formats = ['json', 'xml', 'yaml', 'html', 'plist']

    content_types = {'json': 'application/json',
                     'jsonp': 'text/javascript',
                     'xml': 'application/xml',
                     'yaml': 'text/yaml',
                     'html': 'text/html',
                     'plist': 'application/x-plist'}

    def __init__(self, formats=None, content_types=None, datetime_formatting=None):
        if datetime_formatting is not None:
            self.datetime_formatting = datetime_formatting
        else:
            self.datetime_formatting = getattr(settings, 'TASTYPIE_DATETIME_FORMATTING', 'iso-8601')

        self.supported_formats = []

        if content_types is not None:
            self.content_types = content_types

        if formats is not None:
            self.formats = formats

        if self.formats is Serializer.formats and hasattr(settings, 'TASTYPIE_DEFAULT_FORMATS'):
            # We want TASTYPIE_DEFAULT_FORMATS to override unmodified defaults but not intentational changes
            # on Serializer subclasses:
            self.formats = settings.TASTYPIE_DEFAULT_FORMATS

        if not isinstance(self.formats, (list, tuple)):
            raise ImproperlyConfigured('Formats should be a list or tuple, not %r' % self.formats)

        for format in self.formats:
            try:
                self.supported_formats.append(self.content_types[format])
            except KeyError:
                raise ImproperlyConfigured("Content type for specified type '%s' not found. Please provide it at either the class level or via the arguments." % format)

    def get_mime_for_format(self, format):
        """
        Given a format, attempts to determine the correct MIME type.

        If not available on the current ``Serializer``, returns
        ``application/json`` by default.
        """
        try:
            return self.content_types[format]
        except KeyError:
            return 'application/json'

    def format_datetime(self, data):
        """
        A hook to control how datetimes are formatted.

        Can be overridden at the ``Serializer`` level (``datetime_formatting``)
        or globally (via ``settings.TASTYPIE_DATETIME_FORMATTING``).

        Default is ``iso-8601``, which looks like "2010-12-16T03:02:14".
        """
        data = make_naive(data)
        if self.datetime_formatting == 'rfc-2822':
            return format_datetime(data)

        return data.isoformat()

    def format_date(self, data):
        """
        A hook to control how dates are formatted.

        Can be overridden at the ``Serializer`` level (``datetime_formatting``)
        or globally (via ``settings.TASTYPIE_DATETIME_FORMATTING``).

        Default is ``iso-8601``, which looks like "2010-12-16".
        """
        if self.datetime_formatting == 'rfc-2822':
            return format_date(data)

        return data.isoformat()

    def format_time(self, data):
        """
        A hook to control how times are formatted.

        Can be overridden at the ``Serializer`` level (``datetime_formatting``)
        or globally (via ``settings.TASTYPIE_DATETIME_FORMATTING``).

        Default is ``iso-8601``, which looks like "03:02:14".
        """
        if self.datetime_formatting == 'rfc-2822':
            return format_time(data)

        return data.isoformat()

    def serialize(self, bundle, format='application/json', options={}):
        """
        Given some data and a format, calls the correct method to serialize
        the data and returns the result.
        """
        desired_format = None

        for short_format, long_format in self.content_types.items():
            if format == long_format:
                if hasattr(self, "to_%s" % short_format):
                    desired_format = short_format
                    break

        if desired_format is None:
            raise UnsupportedFormat("The format indicated '%s' had no available serialization method. Please check your ``formats`` and ``content_types`` on your Serializer." % format)

        serialized = getattr(self, "to_%s" % desired_format)(bundle, options)
        return serialized

    def deserialize(self, content, format='application/json'):
        """
        Given some data and a format, calls the correct method to deserialize
        the data and returns the result.
        """
        desired_format = None

        format = format.split(';')[0]

        for short_format, long_format in self.content_types.items():
            if format == long_format:
                if hasattr(self, "from_%s" % short_format):
                    desired_format = short_format
                    break

        if desired_format is None:
            raise UnsupportedFormat("The format indicated '%s' had no available deserialization method. Please check your ``formats`` and ``content_types`` on your Serializer." % format)

        deserialized = getattr(self, "from_%s" % desired_format)(content)
        return deserialized

    def to_simple(self, data, options):
        """
        For a piece of data, attempts to recognize it and provide a simplified
        form of something complex.

        This brings complex Python data structures down to native types of the
        serialization format(s).
        """
        if isinstance(data, (list, tuple)):
            return [self.to_simple(item, options) for item in data]
        if isinstance(data, dict):
            return dict((key, self.to_simple(val, options)) for (key, val) in data.iteritems())
        elif isinstance(data, Bundle):
            return dict((key, self.to_simple(val, options)) for (key, val) in data.data.iteritems())
        elif hasattr(data, 'dehydrated_type'):
            if getattr(data, 'dehydrated_type', None) == 'related' and data.is_m2m == False:
                if data.full:
                    return self.to_simple(data.fk_resource, options)
                else:
                    return self.to_simple(data.value, options)
            elif getattr(data, 'dehydrated_type', None) == 'related' and data.is_m2m == True:
                if data.full:
                    return [self.to_simple(bundle, options) for bundle in data.m2m_bundles]
                else:
                    return [self.to_simple(val, options) for val in data.value]
            else:
                return self.to_simple(data.value, options)
        elif isinstance(data, datetime.datetime):
            return self.format_datetime(data)
        elif isinstance(data, datetime.date):
            return self.format_date(data)
        elif isinstance(data, datetime.time):
            return self.format_time(data)
        elif isinstance(data, bool):
            return data
        elif type(data) in (long, int, float):
            return data
        elif data is None:
            return None
        else:
            return force_unicode(data)

    def to_etree(self, data, options=None, name=None, depth=0):
        """
        Given some data, converts that data to an ``etree.Element`` suitable
        for use in the XML output.
        """
        if isinstance(data, (list, tuple)):
            element = Element(name or 'objects')
            if name:
                element = Element(name)
                element.set('type', 'list')
            else:
                element = Element('objects')
            for item in data:
                element.append(self.to_etree(item, options, depth=depth+1))
        elif isinstance(data, dict):
            if depth == 0:
                element = Element(name or 'response')
            else:
                element = Element(name or 'object')
                element.set('type', 'hash')
            for (key, value) in data.iteritems():
                element.append(self.to_etree(value, options, name=key, depth=depth+1))
        elif isinstance(data, Bundle):
            element = Element(name or 'object')
            for field_name, field_object in data.data.items():
                element.append(self.to_etree(field_object, options, name=field_name, depth=depth+1))
        elif hasattr(data, 'dehydrated_type'):
            if getattr(data, 'dehydrated_type', None) == 'related' and data.is_m2m == False:
                if data.full:
                    return self.to_etree(data.fk_resource, options, name, depth+1)
                else:
                    return self.to_etree(data.value, options, name, depth+1)
            elif getattr(data, 'dehydrated_type', None) == 'related' and data.is_m2m == True:
                if data.full:
                    element = Element(name or 'objects')
                    for bundle in data.m2m_bundles:
                        element.append(self.to_etree(bundle, options, bundle.resource_name, depth+1))
                else:
                    element = Element(name or 'objects')
                    for value in data.value:
                        element.append(self.to_etree(value, options, name, depth=depth+1))
            else:
                return self.to_etree(data.value, options, name)
        else:
            element = Element(name or 'value')
            simple_data = self.to_simple(data, options)
            data_type = get_type_string(simple_data)

            if data_type != 'string':
                element.set('type', get_type_string(simple_data))

            if data_type != 'null':
                if isinstance(simple_data, unicode):
                    element.text = simple_data
                else:
                    element.text = force_unicode(simple_data)

        return element

    def from_etree(self, data):
        """
        Not the smartest deserializer on the planet. At the request level,
        it first tries to output the deserialized subelement called "object"
        or "objects" and falls back to deserializing based on hinted types in
        the XML element attribute "type".
        """
        if data.tag == 'request':
            # if "object" or "objects" exists, return deserialized forms.
            elements = data.getchildren()
            for element in elements:
                if element.tag in ('object', 'objects'):
                    return self.from_etree(element)
            return dict((element.tag, self.from_etree(element)) for element in elements)
        elif data.tag == 'object' or data.get('type') == 'hash':
            return dict((element.tag, self.from_etree(element)) for element in data.getchildren())
        elif data.tag == 'objects' or data.get('type') == 'list':
            return [self.from_etree(element) for element in data.getchildren()]
        else:
            type_string = data.get('type')
            if type_string in ('string', None):
                return data.text
            elif type_string == 'integer':
                return int(data.text)
            elif type_string == 'float':
                return float(data.text)
            elif type_string == 'boolean':
                if data.text == 'True':
                    return True
                else:
                    return False
            else:
                return None

    def to_json(self, data, options=None):
        """
        Given some Python data, produces JSON output.
        """
        options = options or {}
        data = self.to_simple(data, options)

        if django.get_version() >= '1.5':
            return json.json.dumps(data, cls=json.DjangoJSONEncoder, sort_keys=True, ensure_ascii=False)
        else:
            return simplejson.dumps(data, cls=json.DjangoJSONEncoder, sort_keys=True, ensure_ascii=False)

    def from_json(self, content):
        """
        Given some JSON data, returns a Python dictionary of the decoded data.
        """
        return simplejson.loads(content)

    def to_jsonp(self, data, options=None):
        """
        Given some Python data, produces JSON output wrapped in the provided
        callback.

        Due to a difference between JSON and Javascript, two
        newline characters, \u2028 and \u2029, need to be escaped.
        See http://timelessrepo.com/json-isnt-a-javascript-subset for
        details.
        """
        options = options or {}
        json = self.to_json(data, options)
        json = json.replace(u'\u2028', u'\\u2028').replace(u'\u2029', u'\\u2029')
        return u'%s(%s)' % (options['callback'], json)

    def to_xml(self, data, options=None):
        """
        Given some Python data, produces XML output.
        """
        options = options or {}

        if lxml is None:
            raise ImproperlyConfigured("Usage of the XML aspects requires lxml and defusedxml.")

        return tostring(self.to_etree(data, options), xml_declaration=True, encoding='utf-8')

    def from_xml(self, content, forbid_dtd=True, forbid_entities=True):
        """
        Given some XML data, returns a Python dictionary of the decoded data.

        By default XML entity declarations and DTDs will raise a BadRequest
        exception content but subclasses may choose to override this if
        necessary.
        """
        if lxml is None:
            raise ImproperlyConfigured("Usage of the XML aspects requires lxml and defusedxml.")

        try:
            parsed = parse_xml(StringIO(content), forbid_dtd=forbid_dtd,
                               forbid_entities=forbid_entities)
        except (LxmlError, DefusedXmlException):
            raise BadRequest

        return self.from_etree(parsed.getroot())

    def to_yaml(self, data, options=None):
        """
        Given some Python data, produces YAML output.
        """
        options = options or {}

        if yaml is None:
            raise ImproperlyConfigured("Usage of the YAML aspects requires yaml.")

        return yaml.dump(self.to_simple(data, options))

    def from_yaml(self, content):
        """
        Given some YAML data, returns a Python dictionary of the decoded data.
        """
        if yaml is None:
            raise ImproperlyConfigured("Usage of the YAML aspects requires yaml.")

        return yaml.load(content, Loader=TastypieLoader)

    def to_plist(self, data, options=None):
        """
        Given some Python data, produces binary plist output.
        """
        options = options or {}

        if biplist is None:
            raise ImproperlyConfigured("Usage of the plist aspects requires biplist.")

        return biplist.writePlistToString(self.to_simple(data, options))

    def from_plist(self, content):
        """
        Given some binary plist data, returns a Python dictionary of the decoded data.
        """
        if biplist is None:
            raise ImproperlyConfigured("Usage of the plist aspects requires biplist.")

        return biplist.readPlistFromString(content)

    def to_html(self, data, options=None):
        """
        Reserved for future usage.

        The desire is to provide HTML output of a resource, making an API
        available to a browser. This is on the TODO list but not currently
        implemented.
        """
        options = options or {}
        return 'Sorry, not implemented yet. Please append "?format=json" to your URL.'

    def from_html(self, content):
        """
        Reserved for future usage.

        The desire is to handle form-based (maybe Javascript?) input, making an
        API available to a browser. This is on the TODO list but not currently
        implemented.
        """
        pass

def get_type_string(data):
    """
    Translates a Python data type into a string format.
    """
    data_type = type(data)

    if data_type in (int, long):
        return 'integer'
    elif data_type == float:
        return 'float'
    elif data_type == bool:
        return 'boolean'
    elif data_type in (list, tuple):
        return 'list'
    elif data_type == dict:
        return 'hash'
    elif data is None:
        return 'null'
    elif isinstance(data, basestring):
        return 'string'

########NEW FILE########
__FILENAME__ = test
import time
from urlparse import urlparse
from django.conf import settings
from django.test import TestCase
from django.test.client import FakePayload, Client
from tastypie.serializers import Serializer


class TestApiClient(object):
    def __init__(self, serializer=None):
        """
        Sets up a fresh ``TestApiClient`` instance.

        If you are employing a custom serializer, you can pass the class to the
        ``serializer=`` kwarg.
        """
        self.client = Client()
        self.serializer = serializer

        if not self.serializer:
            self.serializer = Serializer()

    def get_content_type(self, short_format):
        """
        Given a short name (such as ``json`` or ``xml``), returns the full content-type
        for it (``application/json`` or ``application/xml`` in this case).
        """
        return self.serializer.content_types.get(short_format, 'json')

    def get(self, uri, format='json', data=None, authentication=None, **kwargs):
        """
        Performs a simulated ``GET`` request to the provided URI.

        Optionally accepts a ``data`` kwarg, which in the case of ``GET``, lets you
        send along ``GET`` parameters. This is useful when testing filtering or other
        things that read off the ``GET`` params. Example::

            from tastypie.test import TestApiClient
            client = TestApiClient()

            response = client.get('/api/v1/entry/1/', data={'format': 'json', 'title__startswith': 'a', 'limit': 20, 'offset': 60})

        Optionally accepts an ``authentication`` kwarg, which should be an HTTP header
        with the correct authentication data already setup.

        All other ``**kwargs`` passed in get passed through to the Django
        ``TestClient``. See https://docs.djangoproject.com/en/dev/topics/testing/#module-django.test.client
        for details.
        """
        content_type = self.get_content_type(format)
        kwargs['HTTP_ACCEPT'] = content_type

        # GET & DELETE are the only times we don't serialize the data.
        if data is not None:
            kwargs['data'] = data

        if authentication is not None:
            kwargs['HTTP_AUTHORIZATION'] = authentication

        return self.client.get(uri, **kwargs)

    def post(self, uri, format='json', data=None, authentication=None, **kwargs):
        """
        Performs a simulated ``POST`` request to the provided URI.

        Optionally accepts a ``data`` kwarg. **Unlike** ``GET``, in ``POST`` the
        ``data`` gets serialized & sent as the body instead of becoming part of the URI.
        Example::

            from tastypie.test import TestApiClient
            client = TestApiClient()

            response = client.post('/api/v1/entry/', data={
                'created': '2012-05-01T20:02:36',
                'slug': 'another-post',
                'title': 'Another Post',
                'user': '/api/v1/user/1/',
            })

        Optionally accepts an ``authentication`` kwarg, which should be an HTTP header
        with the correct authentication data already setup.

        All other ``**kwargs`` passed in get passed through to the Django
        ``TestClient``. See https://docs.djangoproject.com/en/dev/topics/testing/#module-django.test.client
        for details.
        """
        content_type = self.get_content_type(format)
        kwargs['content_type'] = content_type

        if data is not None:
            kwargs['data'] = self.serializer.serialize(data, format=content_type)

        if authentication is not None:
            kwargs['HTTP_AUTHORIZATION'] = authentication

        return self.client.post(uri, **kwargs)

    def put(self, uri, format='json', data=None, authentication=None, **kwargs):
        """
        Performs a simulated ``PUT`` request to the provided URI.

        Optionally accepts a ``data`` kwarg. **Unlike** ``GET``, in ``PUT`` the
        ``data`` gets serialized & sent as the body instead of becoming part of the URI.
        Example::

            from tastypie.test import TestApiClient
            client = TestApiClient()

            response = client.put('/api/v1/entry/1/', data={
                'created': '2012-05-01T20:02:36',
                'slug': 'another-post',
                'title': 'Another Post',
                'user': '/api/v1/user/1/',
            })

        Optionally accepts an ``authentication`` kwarg, which should be an HTTP header
        with the correct authentication data already setup.

        All other ``**kwargs`` passed in get passed through to the Django
        ``TestClient``. See https://docs.djangoproject.com/en/dev/topics/testing/#module-django.test.client
        for details.
        """
        content_type = self.get_content_type(format)
        kwargs['content_type'] = content_type

        if data is not None:
            kwargs['data'] = self.serializer.serialize(data, format=content_type)

        if authentication is not None:
            kwargs['HTTP_AUTHORIZATION'] = authentication

        return self.client.put(uri, **kwargs)

    def patch(self, uri, format='json', data=None, authentication=None, **kwargs):
        """
        Performs a simulated ``PATCH`` request to the provided URI.

        Optionally accepts a ``data`` kwarg. **Unlike** ``GET``, in ``PATCH`` the
        ``data`` gets serialized & sent as the body instead of becoming part of the URI.
        Example::

            from tastypie.test import TestApiClient
            client = TestApiClient()

            response = client.patch('/api/v1/entry/1/', data={
                'created': '2012-05-01T20:02:36',
                'slug': 'another-post',
                'title': 'Another Post',
                'user': '/api/v1/user/1/',
            })

        Optionally accepts an ``authentication`` kwarg, which should be an HTTP header
        with the correct authentication data already setup.

        All other ``**kwargs`` passed in get passed through to the Django
        ``TestClient``. See https://docs.djangoproject.com/en/dev/topics/testing/#module-django.test.client
        for details.
        """
        content_type = self.get_content_type(format)
        kwargs['content_type'] = content_type

        if data is not None:
            kwargs['data'] = self.serializer.serialize(data, format=content_type)

        if authentication is not None:
            kwargs['HTTP_AUTHORIZATION'] = authentication

        # This hurts because Django doesn't support PATCH natively.
        parsed = urlparse(uri)
        r = {
            'CONTENT_LENGTH': len(kwargs['data']),
            'CONTENT_TYPE': content_type,
            'PATH_INFO': self.client._get_path(parsed),
            'QUERY_STRING': parsed[4],
            'REQUEST_METHOD': 'PATCH',
            'wsgi.input': FakePayload(kwargs['data']),
        }
        r.update(kwargs)
        return self.client.request(**r)

    def delete(self, uri, format='json', data=None, authentication=None, **kwargs):
        """
        Performs a simulated ``DELETE`` request to the provided URI.

        Optionally accepts a ``data`` kwarg, which in the case of ``DELETE``, lets you
        send along ``DELETE`` parameters. This is useful when testing filtering or other
        things that read off the ``DELETE`` params. Example::

            from tastypie.test import TestApiClient
            client = TestApiClient()

            response = client.delete('/api/v1/entry/1/', data={'format': 'json'})

        Optionally accepts an ``authentication`` kwarg, which should be an HTTP header
        with the correct authentication data already setup.

        All other ``**kwargs`` passed in get passed through to the Django
        ``TestClient``. See https://docs.djangoproject.com/en/dev/topics/testing/#module-django.test.client
        for details.
        """
        content_type = self.get_content_type(format)
        kwargs['content_type'] = content_type

        # GET & DELETE are the only times we don't serialize the data.
        if data is not None:
            kwargs['data'] = data

        if authentication is not None:
            kwargs['HTTP_AUTHORIZATION'] = authentication

        return self.client.delete(uri, **kwargs)


class ResourceTestCase(TestCase):
    """
    A useful base class for the start of testing Tastypie APIs.
    """
    def setUp(self):
        super(ResourceTestCase, self).setUp()
        self.serializer = Serializer()
        self.api_client = TestApiClient()

    def get_credentials(self):
        """
        A convenience method for the user as a way to shorten up the
        often repetitious calls to create the same authentication.

        Raises ``NotImplementedError`` by default.

        Usage::

            class MyResourceTestCase(ResourceTestCase):
                def get_credentials(self):
                    return self.create_basic('daniel', 'pass')

                # Then the usual tests...

        """
        raise NotImplementedError("You must return the class for your Resource to test.")

    def create_basic(self, username, password):
        """
        Creates & returns the HTTP ``Authorization`` header for use with BASIC
        Auth.
        """
        import base64
        return 'Basic %s' % base64.b64encode(':'.join([username, password]))

    def create_apikey(self, username, api_key):
        """
        Creates & returns the HTTP ``Authorization`` header for use with
        ``ApiKeyAuthentication``.
        """
        return 'ApiKey %s:%s' % (username, api_key)

    def create_digest(self, username, api_key, method, uri):
        """
        Creates & returns the HTTP ``Authorization`` header for use with Digest
        Auth.
        """
        from tastypie.authentication import hmac, sha1, uuid, python_digest

        new_uuid = uuid.uuid4()
        opaque = hmac.new(str(new_uuid), digestmod=sha1).hexdigest()
        return python_digest.build_authorization_request(
            username,
            method.upper(),
            uri,
            1, # nonce_count
            digest_challenge=python_digest.build_digest_challenge(time.time(), getattr(settings, 'SECRET_KEY', ''), 'django-tastypie', opaque, False),
            password=api_key
        )

    def create_oauth(self, user):
        """
        Creates & returns the HTTP ``Authorization`` header for use with Oauth.
        """
        from oauth_provider.models import Consumer, Token, Resource

        # Necessary setup for ``oauth_provider``.
        resource, _ = Resource.objects.get_or_create(url='test', defaults={
            'name': 'Test Resource'
        })
        consumer, _ = Consumer.objects.get_or_create(key='123', defaults={
            'name': 'Test',
            'description': 'Testing...'
        })
        token, _ = Token.objects.get_or_create(key='foo', token_type=Token.ACCESS, defaults={
            'consumer': consumer,
            'resource': resource,
            'secret': '',
            'user': user,
        })

        # Then generate the header.
        oauth_data = {
            'oauth_consumer_key': '123',
            'oauth_nonce': 'abc',
            'oauth_signature': '&',
            'oauth_signature_method': 'PLAINTEXT',
            'oauth_timestamp': str(int(time.time())),
            'oauth_token': 'foo',
        }
        return 'OAuth %s' % ','.join([key+'='+value for key, value in oauth_data.items()])

    def assertHttpOK(self, resp):
        """
        Ensures the response is returning a HTTP 200.
        """
        return self.assertEqual(resp.status_code, 200)

    def assertHttpCreated(self, resp):
        """
        Ensures the response is returning a HTTP 201.
        """
        return self.assertEqual(resp.status_code, 201)

    def assertHttpAccepted(self, resp):
        """
        Ensures the response is returning either a HTTP 202 or a HTTP 204.
        """
        return self.assertTrue(resp.status_code in [202, 204])

    def assertHttpMultipleChoices(self, resp):
        """
        Ensures the response is returning a HTTP 300.
        """
        return self.assertEqual(resp.status_code, 300)

    def assertHttpSeeOther(self, resp):
        """
        Ensures the response is returning a HTTP 303.
        """
        return self.assertEqual(resp.status_code, 303)

    def assertHttpNotModified(self, resp):
        """
        Ensures the response is returning a HTTP 304.
        """
        return self.assertEqual(resp.status_code, 304)

    def assertHttpBadRequest(self, resp):
        """
        Ensures the response is returning a HTTP 400.
        """
        return self.assertEqual(resp.status_code, 400)

    def assertHttpUnauthorized(self, resp):
        """
        Ensures the response is returning a HTTP 401.
        """
        return self.assertEqual(resp.status_code, 401)

    def assertHttpForbidden(self, resp):
        """
        Ensures the response is returning a HTTP 403.
        """
        return self.assertEqual(resp.status_code, 403)

    def assertHttpNotFound(self, resp):
        """
        Ensures the response is returning a HTTP 404.
        """
        return self.assertEqual(resp.status_code, 404)

    def assertHttpMethodNotAllowed(self, resp):
        """
        Ensures the response is returning a HTTP 405.
        """
        return self.assertEqual(resp.status_code, 405)

    def assertHttpConflict(self, resp):
        """
        Ensures the response is returning a HTTP 409.
        """
        return self.assertEqual(resp.status_code, 409)

    def assertHttpGone(self, resp):
        """
        Ensures the response is returning a HTTP 410.
        """
        return self.assertEqual(resp.status_code, 410)

    def assertHttpTooManyRequests(self, resp):
        """
        Ensures the response is returning a HTTP 429.
        """
        return self.assertEqual(resp.status_code, 429)

    def assertHttpApplicationError(self, resp):
        """
        Ensures the response is returning a HTTP 500.
        """
        return self.assertEqual(resp.status_code, 500)

    def assertHttpNotImplemented(self, resp):
        """
        Ensures the response is returning a HTTP 501.
        """
        return self.assertEqual(resp.status_code, 501)

    def assertValidJSON(self, data):
        """
        Given the provided ``data`` as a string, ensures that it is valid JSON &
        can be loaded properly.
        """
        # Just try the load. If it throws an exception, the test case will fail.
        self.serializer.from_json(data)

    def assertValidXML(self, data):
        """
        Given the provided ``data`` as a string, ensures that it is valid XML &
        can be loaded properly.
        """
        # Just try the load. If it throws an exception, the test case will fail.
        self.serializer.from_xml(data)

    def assertValidYAML(self, data):
        """
        Given the provided ``data`` as a string, ensures that it is valid YAML &
        can be loaded properly.
        """
        # Just try the load. If it throws an exception, the test case will fail.
        self.serializer.from_yaml(data)

    def assertValidPlist(self, data):
        """
        Given the provided ``data`` as a string, ensures that it is valid
        binary plist & can be loaded properly.
        """
        # Just try the load. If it throws an exception, the test case will fail.
        self.serializer.from_plist(data)

    def assertValidJSONResponse(self, resp):
        """
        Given a ``HttpResponse`` coming back from using the ``client``, assert that
        you get back:

        * An HTTP 200
        * The correct content-type (``application/json``)
        * The content is valid JSON
        """
        self.assertHttpOK(resp)
        self.assertTrue(resp['Content-Type'].startswith('application/json'))
        self.assertValidJSON(resp.content)

    def assertValidXMLResponse(self, resp):
        """
        Given a ``HttpResponse`` coming back from using the ``client``, assert that
        you get back:

        * An HTTP 200
        * The correct content-type (``application/xml``)
        * The content is valid XML
        """
        self.assertHttpOK(resp)
        self.assertTrue(resp['Content-Type'].startswith('application/xml'))
        self.assertValidXML(resp.content)

    def assertValidYAMLResponse(self, resp):
        """
        Given a ``HttpResponse`` coming back from using the ``client``, assert that
        you get back:

        * An HTTP 200
        * The correct content-type (``text/yaml``)
        * The content is valid YAML
        """
        self.assertHttpOK(resp)
        self.assertTrue(resp['Content-Type'].startswith('text/yaml'))
        self.assertValidYAML(resp.content)

    def assertValidPlistResponse(self, resp):
        """
        Given a ``HttpResponse`` coming back from using the ``client``, assert that
        you get back:

        * An HTTP 200
        * The correct content-type (``application/x-plist``)
        * The content is valid binary plist data
        """
        self.assertHttpOK(resp)
        self.assertTrue(resp['Content-Type'].startswith('application/x-plist'))
        self.assertValidPlist(resp.content)

    def deserialize(self, resp):
        """
        Given a ``HttpResponse`` coming back from using the ``client``, this method
        checks the ``Content-Type`` header & attempts to deserialize the data based on
        that.

        It returns a Python datastructure (typically a ``dict``) of the serialized data.
        """
        return self.serializer.deserialize(resp.content, format=resp['Content-Type'])

    def serialize(self, data, format='application/json'):
        """
        Given a Python datastructure (typically a ``dict``) & a desired content-type,
        this method will return a serialized string of that data.
        """
        return self.serializer.serialize(data, format=format)

    def assertKeys(self, data, expected):
        """
        This method ensures that the keys of the ``data`` match up to the keys of
        ``expected``.

        It covers the (extremely) common case where you want to make sure the keys of
        a response match up to what is expected. This is typically less fragile than
        testing the full structure, which can be prone to data changes.
        """
        self.assertEqual(sorted(data.keys()), sorted(expected))

########NEW FILE########
__FILENAME__ = throttle
import time
from django.core.cache import cache


class BaseThrottle(object):
    """
    A simplified, swappable base class for throttling.
    
    Does nothing save for simulating the throttling API and implementing
    some common bits for the subclasses.
    
    Accepts a number of optional kwargs::
    
        * ``throttle_at`` - the number of requests at which the user should
          be throttled. Default is 150 requests.
        * ``timeframe`` - the length of time (in seconds) in which the user
          make up to the ``throttle_at`` requests. Default is 3600 seconds (
          1 hour).
        * ``expiration`` - the length of time to retain the times the user
          has accessed the api in the cache. Default is 604800 (1 week).
    """
    def __init__(self, throttle_at=150, timeframe=3600, expiration=None):
        self.throttle_at = throttle_at
        # In seconds, please.
        self.timeframe = timeframe
        
        if expiration is None:
            # Expire in a week.
            expiration = 604800
        
        self.expiration = int(expiration)
    
    def convert_identifier_to_key(self, identifier):
        """
        Takes an identifier (like a username or IP address) and converts it
        into a key usable by the cache system.
        """
        bits = []
        
        for char in identifier:
            if char.isalnum() or char in ['_', '.', '-']:
                bits.append(char)
        
        safe_string = ''.join(bits)
        return "%s_accesses" % safe_string
    
    def should_be_throttled(self, identifier, **kwargs):
        """
        Returns whether or not the user has exceeded their throttle limit.
        
        Always returns ``False``, as this implementation does not actually
        throttle the user.
        """
        return False
    
    def accessed(self, identifier, **kwargs):
        """
        Handles recording the user's access.
        
        Does nothing in this implementation.
        """
        pass


class CacheThrottle(BaseThrottle):
    """
    A throttling mechanism that uses just the cache.
    """
    def should_be_throttled(self, identifier, **kwargs):
        """
        Returns whether or not the user has exceeded their throttle limit.
        
        Maintains a list of timestamps when the user accessed the api within
        the cache.
        
        Returns ``False`` if the user should NOT be throttled or ``True`` if
        the user should be throttled.
        """
        key = self.convert_identifier_to_key(identifier)
        
        # Make sure something is there.
        cache.add(key, [])
        
        # Weed out anything older than the timeframe.
        minimum_time = int(time.time()) - int(self.timeframe)
        times_accessed = [access for access in cache.get(key) if access >= minimum_time]
        cache.set(key, times_accessed, self.expiration)
        
        if len(times_accessed) >= int(self.throttle_at):
            # Throttle them.
            return True
        
        # Let them through.
        return False
    
    def accessed(self, identifier, **kwargs):
        """
        Handles recording the user's access.
        
        Stores the current timestamp in the "accesses" list within the cache.
        """
        key = self.convert_identifier_to_key(identifier)
        times_accessed = cache.get(key, [])
        times_accessed.append(int(time.time()))
        cache.set(key, times_accessed, self.expiration)


class CacheDBThrottle(CacheThrottle):
    """
    A throttling mechanism that uses the cache for actual throttling but
    writes-through to the database.
    
    This is useful for tracking/aggregating usage through time, to possibly
    build a statistics interface or a billing mechanism.
    """
    def accessed(self, identifier, **kwargs):
        """
        Handles recording the user's access.
        
        Does everything the ``CacheThrottle`` class does, plus logs the
        access within the database using the ``ApiAccess`` model.
        """
        # Do the import here, instead of top-level, so that the model is
        # only required when using this throttling mechanism.
        from tastypie.models import ApiAccess
        super(CacheDBThrottle, self).accessed(identifier, **kwargs)
        # Write out the access to the DB for logging purposes.
        ApiAccess.objects.create(
            identifier=identifier,
            url=kwargs.get('url', ''),
            request_method=kwargs.get('request_method', '')
        )

########NEW FILE########
__FILENAME__ = dict
def dict_strip_unicode_keys(uni_dict):
    """
    Converts a dict of unicode keys into a dict of ascii keys.
    
    Useful for converting a dict to a kwarg-able format.
    """
    data = {}
    
    for key, value in uni_dict.items():
        data[str(key)] = value
    
    return data

########NEW FILE########
__FILENAME__ = formatting
import email
import datetime
import time
from django.utils import dateformat
from tastypie.utils.timezone import make_aware, make_naive, aware_datetime

# Try to use dateutil for maximum date-parsing niceness. Fall back to
# hard-coded RFC2822 parsing if that's not possible.
try:
    from dateutil.parser import parse as mk_datetime
except ImportError:
    def mk_datetime(string):
        return make_aware(datetime.datetime.fromtimestamp(time.mktime(email.utils.parsedate(string))))

def format_datetime(dt):
    """
    RFC 2822 datetime formatter
    """
    return dateformat.format(make_naive(dt), 'r')

def format_date(d):
    """
    RFC 2822 date formatter
    """
    # workaround because Django's dateformat utility requires a datetime
    # object (not just date)
    dt = aware_datetime(d.year, d.month, d.day, 0, 0, 0)
    return dateformat.format(dt, 'j M Y')

def format_time(t):
    """
    RFC 2822 time formatter
    """
    # again, workaround dateformat input requirement
    dt = aware_datetime(2000, 1, 1, t.hour, t.minute, t.second)
    return dateformat.format(dt, 'H:i:s O')

########NEW FILE########
__FILENAME__ = mime
import mimeparse

from tastypie.exceptions import BadRequest


def determine_format(request, serializer, default_format='application/json'):
    """
    Tries to "smartly" determine which output format is desired.

    First attempts to find a ``format`` override from the request and supplies
    that if found.

    If no request format was demanded, it falls back to ``mimeparse`` and the
    ``Accepts`` header, allowing specification that way.

    If still no format is found, returns the ``default_format`` (which defaults
    to ``application/json`` if not provided).

    NOTE: callers *must* be prepared to handle BadRequest exceptions due to
          malformed HTTP request headers!
    """
    # First, check if they forced the format.
    if request.GET.get('format'):
        if request.GET['format'] in serializer.formats:
            return serializer.get_mime_for_format(request.GET['format'])

    # If callback parameter is present, use JSONP.
    if 'callback' in request.GET:
        return serializer.get_mime_for_format('jsonp')

    # Try to fallback on the Accepts header.
    if request.META.get('HTTP_ACCEPT', '*/*') != '*/*':
        formats = list(serializer.supported_formats) or []
        # Reverse the list, because mimeparse is weird like that. See also
        # https://github.com/toastdriven/django-tastypie/issues#issue/12 for
        # more information.
        formats.reverse()

        try:
            best_format = mimeparse.best_match(formats, request.META['HTTP_ACCEPT'])
        except ValueError:
            raise BadRequest('Invalid Accept header')

        if best_format:
            return best_format

    # No valid 'Accept' header/formats. Sane default.
    return default_format


def build_content_type(format, encoding='utf-8'):
    """
    Appends character encoding to the provided format if not already present.
    """
    if 'charset' in format:
        return format

    if format in ('application/json', 'text/javascript'):
        return format

    return "%s; charset=%s" % (format, encoding)

########NEW FILE########
__FILENAME__ = timezone
import datetime
from django.conf import settings

try:
    from django.utils import timezone

    def make_aware(value):
        if getattr(settings, "USE_TZ", False) and timezone.is_naive(value):
            default_tz = timezone.get_default_timezone()
            value = timezone.make_aware(value, default_tz)
        return value

    def make_naive(value):
        if getattr(settings, "USE_TZ", False) and timezone.is_aware(value):
            default_tz = timezone.get_default_timezone()
            value = timezone.make_naive(value, default_tz)
        return value

    def now():
        return timezone.localtime(timezone.now())

except ImportError:
    now = datetime.datetime.now
    make_aware = make_naive = lambda x: x

def aware_date(*args, **kwargs):
    return make_aware(datetime.date(*args, **kwargs))

def aware_datetime(*args, **kwargs):
    return make_aware(datetime.datetime(*args, **kwargs))

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings


def trailing_slash():
    if getattr(settings, 'TASTYPIE_ALLOW_MISSING_SLASH', False):
        return '/?'
    
    return '/'

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
__FILENAME__ = validation
from django.core.exceptions import ImproperlyConfigured
from django.forms import ModelForm
from django.forms.models import model_to_dict


class Validation(object):
    """
    A basic validation stub that does no validation.
    """
    def __init__(self, **kwargs):
        pass

    def is_valid(self, bundle, request=None):
        """
        Performs a check on the data within the bundle (and optionally the
        request) to ensure it is valid.

        Should return a dictionary of error messages. If the dictionary has
        zero items, the data is considered valid. If there are errors, keys
        in the dictionary should be field names and the values should be a list
        of errors, even if there is only one.
        """
        return {}


class FormValidation(Validation):
    """
    A validation class that uses a Django ``Form`` to validate the data.

    This class **DOES NOT** alter the data sent, only verifies it. If you
    want to alter the data, please use the ``CleanedDataFormValidation`` class
    instead.

    This class requires a ``form_class`` argument, which should be a Django
    ``Form`` (or ``ModelForm``, though ``save`` will never be called) class.
    This form will be used to validate the data in ``bundle.data``.
    """
    def __init__(self, **kwargs):
        if not 'form_class' in kwargs:
            raise ImproperlyConfigured("You must provide a 'form_class' to 'FormValidation' classes.")

        self.form_class = kwargs.pop('form_class')
        super(FormValidation, self).__init__(**kwargs)

    def form_args(self, bundle):
        data = bundle.data

        # Ensure we get a bound Form, regardless of the state of the bundle.
        if data is None:
            data = {}

        kwargs = {'data': {}}

        if hasattr(bundle.obj, 'pk'):
            if issubclass(self.form_class, ModelForm):
                kwargs['instance'] = bundle.obj

            kwargs['data'] = model_to_dict(bundle.obj)

        kwargs['data'].update(data)
        return kwargs

    def is_valid(self, bundle, request=None):
        """
        Performs a check on ``bundle.data``to ensure it is valid.

        If the form is valid, an empty list (all valid) will be returned. If
        not, a list of errors will be returned.
        """

        form = self.form_class(**self.form_args(bundle))

        if form.is_valid():
            return {}

        # The data is invalid. Let's collect all the error messages & return
        # them.
        return form.errors


class CleanedDataFormValidation(FormValidation):
    """
    A validation class that uses a Django ``Form`` to validate the data.

    This class **ALTERS** data sent by the user!!!

    This class requires a ``form_class`` argument, which should be a Django
    ``Form`` (or ``ModelForm``, though ``save`` will never be called) class.
    This form will be used to validate the data in ``bundle.data``.
    """
    def is_valid(self, bundle, request=None):
        """
        Checks ``bundle.data``to ensure it is valid & replaces it with the
        cleaned results.

        If the form is valid, an empty list (all valid) will be returned. If
        not, a list of errors will be returned.
        """
        form = self.form_class(**self.form_args(bundle))

        if form.is_valid():
            # We're different here & relying on having a reference to the same
            # bundle the rest of the process is using.
            bundle.data = form.cleaned_data
            return {}

        # The data is invalid. Let's collect all the error messages & return
        # them.
        return form.errors

########NEW FILE########
