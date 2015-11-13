__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_name.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-
import datetime
from django.contrib import admin

########NEW FILE########
__FILENAME__ = models
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.template.loader import render_to_string
from feincms.module.page.models import Page
from feincms.content.richtext.models import RichTextContent
from feincms.content.medialibrary.models import MediaFileContent

Page.register_templates(
    {
    'key' : 'base',
    'title': _(u'Standard template'),
    'path': 'cms_base.html',
    'regions': (
        ('main', _(u'Main content area')),
    ),
    },
    )
Page.register_extensions('feincms.module.extensions.changedate', 'feincms.module.extensions.translations', )

Page.create_content_type(RichTextContent)
#MediaFileContent.default_create_content_type(Page)
Page.create_content_type(MediaFileContent, POSITION_CHOICES=(
    #('left', _(u'left')),
    ('right', _(u'right')),
    ('center', _(u'center')),
    ))

########NEW FILE########
__FILENAME__ = app
# use this as settings.py if you’re writing a reusable app and not a single project
# see http://djangopatterns.com/patterns/configuration/configure_app/
from django.conf import settings

SOME_SETTING = getattr(settings, '%s_SOME_SETTING' % settings.PROJECT_NAME.upper(), 'this')

#if API_KEY is None:
#    raise ImproperlyConfigured("You haven't set '%s_API_KEY'." % settings.PROJECT_NAME.upper())

########NEW FILE########
__FILENAME__ = base
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""
import os, sys
from django.core.exceptions import ImproperlyConfigured

_ = lambda s: s

def get_env_variable(var_name):
    """Get the environment variable or return exception."""
    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = _('Set the %s environment variable.') % var_name
        raise ImproperlyConfigured(error_msg)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
PROJECT_NAME = os.path.split(PROJECT_ROOT)[-1]

rel = lambda p: os.path.normpath(os.path.join(PROJECT_ROOT, p)) # this is release and virtualenv dependent
rootrel = lambda p: os.path.normpath(os.path.join('/var/www', PROJECT_NAME, p)) # this is not

sys.path += [PROJECT_ROOT, os.path.join(PROJECT_ROOT,'lib/python2.7/site-packages')]

# ==============================================================================
# debug settings
# ==============================================================================

DEBUG = False
TEMPLATE_DEBUG = DEBUG
INTERNAL_IPS = ('127.0.0.1',)
if DEBUG:
    TEMPLATE_STRING_IF_INVALID = _(u'STRING_NOT_SET')

# logging: see
# http://docs.djangoproject.com/en/dev/topics/logging/
# http://docs.python.org/library/logging.html

# import logging
# logger = logging.getLogger(__name__)


LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(message)s' # %(process)d %(thread)d 
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'filters': {
         'require_debug_false': {
             '()': 'django.utils.log.RequireDebugFalse'
         }
     },
    'handlers': {
        'null': {
            'level':'DEBUG',
            'class':'django.utils.log.NullHandler',
        },
        'console':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file':{
            'level':'INFO',
            'class':'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'verbose',
            'filename': rootrel('logs/info.log'),
            'when': 'D',
            'interval': 7,
            'backupCount': 4,
            # rotate every 7 days, keep 4 old copies
        },
        'error_file':{
            'level':'ERROR',
            'class':'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'verbose',
            'filename': rootrel('logs/error.log'),
            'when': 'D',
            'interval': 7,
            'backupCount': 4,
            # rotate every 7 days, keep 4 old copies
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        }
    },
    'loggers': {
        'django': { # django is the catch-all logger. No messages are posted directly to this logger.
            'handlers':['null', 'error_file'],
            'propagate': True,
            'level':'INFO',
        },
        'django.request': { # Log messages related to the handling of requests. 5XX responses are raised as ERROR messages; 4XX responses are raised as WARNING messages.
            'handlers': ['error_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        PROJECT_NAME: {
            'handlers': ['console', 'file', 'error_file', 'mail_admins'],
            'level': 'INFO',
            #'filters': ['special']
        }
    }
}

# ==============================================================================
# cache settings
# ==============================================================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/var/tmp/django_cache/%s' % PROJECT_NAME,
        'TIMEOUT': 600,
    }
}

USE_ETAGS = True

# ==============================================================================
# email and error-notify settings
# ==============================================================================

YOUR_DOMAIN = 'example.com' # since I'm getting error messages from stupid cloners...

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.6/ref/settings/#allowed-hosts
ALLOWED_HOSTS = [
                 '.'+YOUR_DOMAIN, # wildcard: all servers on your domain
                 '.'+YOUR_DOMAIN+'.', # wildcard plus FQDN (see above doc link)
                 #'www.'+YOUR_DOMAIN,
                 ] + list(INTERNAL_IPS)

ADMINS = (
    #('Henning Hraban Ramm', 'hraban@fiee.net'), # don't send your errors to me!
    ('You', 'root@%s' % YOUR_DOMAIN),
)

MANAGERS = ADMINS

DEFAULT_FROM_EMAIL = '%s@%s' % (PROJECT_NAME, YOUR_DOMAIN)
SERVER_EMAIL = 'error-notify@%s' % YOUR_DOMAIN

EMAIL_SUBJECT_PREFIX = '[%s] ' % PROJECT_NAME
EMAIL_HOST = 'mail.%s' % YOUR_DOMAIN
EMAIL_PORT = 25
EMAIL_HOST_USER = '%s@%s' % (PROJECT_NAME, YOUR_DOMAIN)
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
EMAIL_HOST_PASSWORD = get_env_variable('EMAIL_PASSWORD')
EMAIL_USE_TLS = False

# ==============================================================================
# database settings
# ==============================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': PROJECT_NAME,                      # Or path to database file if using sqlite3.
        'USER': PROJECT_NAME,                      # Not used with sqlite3.
        'PASSWORD': get_env_variable('DATABASE_PASSWORD'),                  # Not used with sqlite3.
        'HOST': 'localhost',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                               # Set to empty string for default. Not used with sqlite3.
        'ATOMIC_REQUESTS': True,                  # Wrap everything in transactions.
    }
}

#import dj_database_url
#DATABASES = {}
#DATABASES['default'] = dj_database_url.config()


# ==============================================================================
# i18n and url settings
# ==============================================================================

TIME_ZONE = 'Europe/Berlin'
LANGUAGE_CODE = 'de' # 'en-us'
LANGUAGES = (('en', _(u'English')),
             ('de', _(u'German')))
USE_I18N = True
USE_L10N = True
# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

LOCALE_PATHS = (
    rel('locale/'),
)

SITE_ID = 1

ROOT_URLCONF = '%s.urls' % PROJECT_NAME

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = '%s.wsgi.application' % PROJECT_NAME

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
# don’t use /media/! FeinCMS’ media library uses MEDIA_ROOT/medialibrary
MEDIA_ROOT = rootrel('')
# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/'

# setup Django 1.3+ staticfiles
# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'
STATIC_ROOT = rel('static_collection')
STATICFILES_DIRS = (
    rel('static'), 
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
) #'.../feincms/media',
# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

ADMIN_MEDIA_PREFIX = '%sadmin/' % STATIC_URL # Don’t know if that’s still used

# ==============================================================================
# application and middleware settings
# ==============================================================================

DJANGO_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    #'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    #'django.contrib.sitemaps',
    #'django.contrib.humanize',
)

THIRD_PARTY_APPS = (
    'djangosecure',
    #'admin_tools',
    #'admin_tools.theming',
    #'admin_tools.menu',
    #'admin_tools.dashboard',
    'gunicorn', # not with fcgi
    'mptt',
    'south',
    #'tagging',
    'feincms',
    'feincms.module.page',
    'feincms.module.medialibrary',
)

LOCAL_APPS = (
    PROJECT_NAME,
)

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


MIDDLEWARE_CLASSES = [
    'django.middleware.cache.UpdateCacheMiddleware', # first
    'django.middleware.gzip.GZipMiddleware', # second after UpdateCache
    'djangosecure.middleware.SecurityMiddleware', # as first as possible
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.http.ConditionalGetMiddleware',
    'django.middleware.doc.XViewMiddleware', # for local IPs
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware', # last
]

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth', # Django 1.3+
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'django.core.context_processors.static', # Django 1.3+ staticfiles
    'django.contrib.messages.context_processors.messages',
)

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates'),
)

TEMPLATE_LOADERS = (
    ('django.template.loaders.cached.Loader', (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
#       'django.template.loaders.eggs.Loader',
    )),
)

# ==============================================================================
# the secret key
# ==============================================================================

try:
    SECRET_KEY
except NameError:
    if DEBUG:
        SECRET_FILE = rel('secret.txt')
    else:
        SECRET_FILE = rootrel('secret.txt')
    try:
        SECRET_KEY = open(SECRET_FILE).read().strip()
    except IOError:
        try:
            from random import choice
            SECRET_KEY = ''.join([choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(50)])
            secret = file(SECRET_FILE, 'w')
            secret.write(SECRET_KEY)
            secret.close()
        except IOError:
            Exception(_(u'Please create a %s file with random characters to generate your secret key!' % SECRET_FILE))

# ==============================================================================
# third party
# ==============================================================================

# ..third party app settings here

# auth/registration
LOGIN_URL = '/accounts/login/'
LOGOUT_URL = '/accounts/logout/'
LOGIN_REDIRECT_URL = '/'

# feincms
FEINCMS_ADMIN_MEDIA = '%sfeincms/' % STATIC_URL
FEINCMS_ADMIN_MEDIA_HOTLINKING = True
#FEINCMS_MEDIALIBRARY_UPLOAD_TO
# obsolete with FeinCMS 1.4
#FEINCMS_MEDIALIBRARY_ROOT = rootrel('') #'/var/www/project_name/medialibrary/'
#FEINCMS_MEDIALIBRARY_URL = '/' #'/medialibrary/'

# schedule
FIRST_DAY_OF_WEEK = 1

# admin_tools
ADMIN_TOOLS_MENU = '%s.menu.CustomMenu' % PROJECT_NAME
ADMIN_TOOLS_INDEX_DASHBOARD = '%s.dashboard.CustomIndexDashboard' % PROJECT_NAME
ADMIN_TOOLS_APP_INDEX_DASHBOARD = '%s.dashboard.CustomAppIndexDashboard' % PROJECT_NAME

# django-secure
SECURE_SSL_REDIRECT=True # if all non-SSL requests should be permanently redirected to SSL.
SECURE_HSTS_SECONDS=10 # integer number of seconds, if you want to use HTTP Strict Transport Security
SECURE_HSTS_INCLUDE_SUBDOMAINS=True # if you want to use HTTP Strict Transport Security
SECURE_FRAME_DENY=True # if you want to prevent framing of your pages and protect them from clickjacking.
SECURE_CONTENT_TYPE_NOSNIFF=True # if you want to prevent the browser from guessing asset content types.
SECURE_BROWSER_XSS_FILTER=True # if you want to enable the browser's XSS filtering protections.
SESSION_COOKIE_SECURE=True # if you are using django.contrib.sessions
SESSION_COOKIE_HTTPONLY=True # if you are using django.contrib.sessions

########NEW FILE########
__FILENAME__ = local
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from .base import *

#PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
#PROJECT_NAME = os.path.split(PROJECT_ROOT)[-1]

rootrel = lambda p: os.path.join(PROJECT_ROOT, '../..', p)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

CACHE_BACKEND = 'locmem://'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': rel('dev_db.sqlite3'),          # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': get_env_variable('DATABASE_PASSWORD'),                  # Not used with sqlite3.
        'HOST': 'localhost',             # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
        'ATOMIC_REQUESTS': True,                  # Wrap everything in transactions.
    }
}

MEDIA_ROOT = rel('media')

if DEBUG:
    #INSTALLED_APPS.append('django.contrib.admindocs')
    #INSTALLED_APPS.append('debug_toolbar')
    #MIDDLEWARE_CLASSES.append('debug_toolbar.middleware.DebugToolbarMiddleware') # see also http://github.com/robhudson/django-debug-toolbar/blob/master/README.rst
    LOGGING['handlers']['file'] = {
                'level':'INFO',
                'class':'logging.FileHandler',
                'formatter': 'verbose',
                'filename': rootrel('logs/info.log'),
            }
    LOGGING['handlers']['error_file'] = {
                'level':'ERROR',
                'class':'logging.FileHandler',
                'formatter': 'verbose',
                'filename': rootrel('logs/error.log'),
            }


########NEW FILE########
__FILENAME__ = production
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .base import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': PROJECT_NAME,                      # Or path to database file if using sqlite3.
        'USER': PROJECT_NAME,                      # Not used with sqlite3.
        'PASSWORD': get_env_variable('DATABASE_PASSWORD'),                  # Not used with sqlite3.
        'HOST': 'localhost',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
        'ATOMIC_REQUESTS': True,                  # Wrap everything in transactions.
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.sitemaps import GenericSitemap
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
#from feincms.module.page.models import Page
#from feincms.module.page.sitemap import PageSitemap
import os
from django.views.generic import TemplateView, ListView

admin.autodiscover()

#mysitemaps = {
#    'page' : GenericSitemap({
#        'queryset': Page.objects.all(),
#        'changefreq' : 'monthly',
#        'date_field': 'modification_date',
#    }, priority=0.6),
#}
## OR
# mysitemaps = {'pages' : PageSitemap}

urlpatterns = patterns('',
        (r'^/?$', TemplateView.as_view(template_name="root.html")),
)

# serve static content in debug mode
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.STATIC_ROOT,
            'show_indexes' : True
        }),
        (r'^(media/|static/)?medialibrary/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': '%s/medialibrary/' % settings.MEDIA_ROOT,
            'show_indexes' : True
        }),
        (r'^(?P<path>favicon.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
        }),
        (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    )


urlpatterns += patterns('',
    #(r'^admin_tools/', include('admin_tools.urls')),
    (r'^admin/', include(admin.site.urls)),    
    #(r'sitemap\.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': mysitemaps}),
    #url(r'', include('feincms.urls')),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for project_name project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_name.settings")

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
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
fabfile for Django:
derived from http://morethanseven.net/2009/07/27/fabric-django-git-apache-mod_wsgi-virtualenv-and-p/
"""
import time
from fabric.api import *

# globals
env.prj_name = 'project_name' # no spaces!
env.prj_dir = 'django_project' # subdir under git root that contains the deployable part
env.sudoers_group = 'wheel'
env.use_photologue = False # django-photologue gallery module
env.use_feincms = True
env.use_medialibrary = True # feincms.medialibrary or similar
env.use_daemontools = False
env.use_supervisor = True
env.use_celery = False
env.use_memcached = False
env.webserver = 'nginx' # nginx (directory name below /etc!), nothing else ATM
env.dbserver = 'mysql' # mysql or postgresql

# environments

def localhost():
    "Use the local virtual server"
    env.hosts = ['localhost']
    env.requirements = 'local'
    env.user = 'hraban' # You must create and sudo-enable the user first!
    env.path = '/Users/%(user)s/workspace/%(prj_name)s' % env # User home on OSX, TODO: check local OS
    env.virtualhost_path = env.path
    env.pysp = '%(virtualhost_path)s/lib/python2.7/site-packages' % env
    env.tmppath = '/var/tmp/django_cache/%(prj_name)s' % env


def webserver():
    "Use the actual webserver"
    env.hosts = ['webserver.example.com'] # Change to your server name!
    env.requirements = 'webserver'
    env.user = env.prj_name
    env.path = '/var/www/%(prj_name)s' % env
    env.virtualhost_path = env.path
    env.pysp = '%(virtualhost_path)s/lib/python2.7/site-packages' % env
    env.tmppath = '/var/tmp/django_cache/%(prj_name)s' % env
   
   
# tasks

def test():
    "Run the test suite and bail out if it fails"
    local("cd %(path)s; python manage.py test" % env) #, fail="abort")
    
    
def setup():
    """
    Setup a fresh virtualenv as well as a few useful directories, then run
    a full deployment
    """
    require('hosts', provided_by=[localhost,webserver])
    require('path')
    # install Python environment
    sudo('apt-get install -y build-essential python-dev python-setuptools python-imaging python-virtualenv python-yaml')
    # install some version control systems, since we need Django modules in development
    sudo('apt-get install -y git-core') # subversion git-core mercurial
        
    # install more Python stuff
    # Don't install setuptools or virtualenv on Ubuntu with easy_install or pip! Only Ubuntu packages work!
    sudo('easy_install pip')

    if env.use_daemontools:
        sudo('apt-get install -y daemontools daemontools-run')
        sudo('mkdir -p /etc/service/%(prj_name)s' % env, pty=True)
    if env.use_supervisor:
        sudo('pip install supervisor')
        #sudo('echo; if [ ! -f /etc/supervisord.conf ]; then echo_supervisord_conf > /etc/supervisord.conf; fi', pty=True) # configure that!
        sudo('echo; if [ ! -d /etc/supervisor ]; then mkdir /etc/supervisor; fi', pty=True)
    if env.use_celery:
        sudo('apt-get install -y rabbitmq-server') # needs additional deb-repository, see tools/README.rst!
        if env.use_daemontools:
            sudo('mkdir -p /etc/service/%(prj_name)s-celery' % env, pty=True)
        elif env.use_supervisor:
            print "CHECK: You want to use celery under supervisor. Please check your celery configuration in supervisor-celery.ini!"
    if env.use_memcached:
        sudo('apt-get install -y memcached python-memcache', pty=True)
    
    # install webserver and database server
    sudo('apt-get remove -y apache2 apache2-mpm-prefork apache2-utils') # is mostly pre-installed
    if env.webserver=='nginx':
        sudo('apt-get install -y nginx')
    else:
        print "WARNING: Your webserver '%s' is not suppoerted!" % env.webserver # other webservers?
    if env.dbserver=='mysql':
        sudo('apt-get install -y mysql-server python-mysqldb')
    elif env.dbserver=='postgresql':
        sudo('apt-get install -y postgresql python-psycopg2')
        
    # disable default site
    with settings(warn_only=True):
        sudo('cd /etc/%(webserver)s/sites-enabled/; rm default;' % env, pty=True)
    
    # new project setup
    sudo('mkdir -p %(path)s; chown %(user)s:%(user)s %(path)s;' % env, pty=True)
    sudo('mkdir -p %(tmppath)s; chown %(user)s:%(user)s %(tmppath)s;' % env, pty=True)
    with settings(warn_only=True):
        run('cd ~; ln -s %(path)s www;' % env, pty=True) # symlink web dir in home
    with cd(env.path):
        run('virtualenv .') # activate with 'source ~/www/bin/activate', perhaps add that to your .bashrc or .profile
        with settings(warn_only=True):
            run('mkdir -m a+w logs; mkdir releases; mkdir shared; mkdir packages; mkdir backup;', pty=True)
            if env.use_photologue:
                run('mkdir photologue', pty=True)
                #run('pip install -U django-photologue' % env, pty=True)
            if env.use_medialibrary:
                run('mkdir medialibrary', pty=True)
            run('cd releases; ln -s . current; ln -s . previous;', pty=True)
    # FeinCMS is now installable via pip (requirements/base.txt)
    #if env.use_feincms:
    #    with cd(env.pysp):
    #        run('git clone git://github.com/django-mptt/django-mptt.git; echo django-mptt > mptt.pth;', pty=True)
    #        run('git clone git://github.com/feincms/feincms.git; echo feincms > feincms.pth;', pty=True)
    setup_user()
    deploy('first')
    
def setup_user():
    require('hosts', provided_by=[webserver])
    sudo('adduser "%(prj_name)s"' % env, pty=True)
    sudo('adduser "%(prj_name)s" %(sudoers_group)s' % env, pty=True)
    # cd to web dir and activate virtualenv on login
    #run('echo "\ncd %(path)s && source bin/activate\n" >> /home/%(prj_name)s/.profile\n' % env, pty=True)
    if env.dbserver=='mysql':
        env.dbuserscript = '/home/%(prj_name)s/userscript.sql' % env
        run('''echo "\ncreate user '%(prj_name)s'@'localhost' identified by '${PASS}';
create database %(prj_name)s character set 'utf8';\n
grant all privileges on %(prj_name)s.* to '%(prj_name)s'@'localhost';\n
flush privileges;\n" > %(dbuserscript)s''' % env, pty=True)
        run('echo "Setting up %(prj_name)s in MySQL. Please enter password for root:"; mysql -u root -p -D mysql < %(dbuserscript)s' % env, pty=True)
        run('rm %(dbuserscript)s' % env, pty=True)
        del env.dbuserscript
    # TODO: create key pair for SSH!
    
def deploy(param=''):
    """
    Deploy the latest version of the site to the servers, install any
    required third party modules, install the virtual host and 
    then restart the webserver
    """
    require('hosts', provided_by=[localhost,webserver])
    require('path')
    env.release = time.strftime('%Y%m%d%H%M%S')
    upload_tar_from_git()
    if param=='first': install_requirements()
    install_site()
    symlink_current_release()
    migrate(param)
    restart_webserver()
    
def deploy_version(version):
    "Specify a specific version to be made live"
    require('hosts', provided_by=[localhost,webserver])
    require('path')
    env.version = version
    with cd(env.path):
        run('rm -rf releases/previous; mv releases/current releases/previous;', pty=True)
        run('ln -s %(version)s releases/current' % env, pty=True)
    restart_webserver()
    
def rollback():
    """
    Limited rollback capability. Simply loads the previously current
    version of the code. Rolling back again will swap between the two.
    """
    require('hosts', provided_by=[localhost,webserver])
    require('path')
    with cd(env.path):
        run('mv releases/current releases/_previous;', pty=True)
        run('mv releases/previous releases/current;', pty=True)
        run('mv releases/_previous releases/previous;', pty=True)
        # TODO: use South to migrate back
    restart_webserver()    
    
# Helpers. These are called by other functions rather than directly

def upload_tar_from_git():
    "Create an archive from the current Git master branch and upload it"
    require('release', provided_by=[deploy, setup])
    local('git archive --format=tar master | gzip > %(release)s.tar.gz' % env)
    run('mkdir -p %(path)s/releases/%(release)s' % env) #, pty=True)
    put('%(release)s.tar.gz' % env, '%(path)s/packages/' % env)
    run('cd %(path)s/releases/%(release)s && tar zxf ../../packages/%(release)s.tar.gz' % env, pty=True)
    local('rm %(release)s.tar.gz' % env)
    
def install_site():
    "Add the virtualhost config file to the webserver's config, activate logrotate"
    require('release', provided_by=[deploy, setup])
    with cd('%(path)s/releases/%(release)s' % env):
        sudo('cp server-setup/%(webserver)s.conf /etc/%(webserver)s/sites-available/%(prj_name)s' % env, pty=True)
        if env.use_daemontools: # activate new service runner
            sudo('cp server-setup/service-run.sh /etc/service/%(prj_name)s/run; chmod a+x /etc/service/%(prj_name)s/run;' % env, pty=True)
        else: # delete old service dir
            sudo('echo; if [ -d /etc/service/%(prj_name)s ]; then rm -rf /etc/service/%(prj_name)s; fi' % env, pty=True)
        if env.use_supervisor: # activate new supervisor.ini
            sudo('cp server-setup/supervisor.ini /etc/supervisor/%(prj_name)s.ini' % env, pty=True)
            if env.use_celery:
                sudo('cp server-setup/supervisor-celery.ini /etc/supervisor/%(prj_name)s-celery.ini' % env, pty=True)
        else: # delete old config file
            sudo('echo; if [ -f /etc/supervisor/%(prj_name)s.ini ]; then supervisorctl %(prj_name)s:appserver stop rm /etc/supervisor/%(prj_name)s.ini; fi' % env, pty=True)
            if env.use_celery:
                sudo('echo; if [ -f /etc/supervisor/%(prj_name)s-celery.ini ]; then supervisorctl celery celerybeat stop rm /etc/supervisor/%(prj_name)s-celery.ini; fi' % env, pty=True)
        if env.use_celery and env.use_daemontools:
            sudo('cp server-setup/service-run-celeryd.sh /etc/service/%(prj_name)s-celery/run; chmod a+x /etc/service/%(prj_name)s-celery/run;' % env, pty=True)
        # try logrotate
        with settings(warn_only=True):        
            sudo('cp server-setup/logrotate.conf /etc/logrotate.d/website-%(prj_name)s' % env, pty=True)
    with settings(warn_only=True):        
        sudo('cd /etc/%(webserver)s/sites-enabled/; ln -s ../sites-available/%(prj_name)s %(prj_name)s' % env, pty=True)
    
def install_requirements():
    "Install the required packages from the requirements file using pip"
    require('release', provided_by=[deploy, setup])
    run('cd %(path)s; pip install -U -r ./releases/%(release)s/requirements/%(requirements).txt' % env, pty=True)
    
def symlink_current_release():
    "Symlink our current release"
    require('release', provided_by=[deploy, setup])
    with cd(env.path):
        run('rm releases/previous; mv releases/current releases/previous;', pty=True)
        run('ln -s %(release)s releases/current' % env, pty=True)
        # copy South migrations from previous release, if there are any
        run('cd releases/previous/%(prj_name)s; if [ -d migrations ]; then cp -r migrations ../../current/%(prj_name)s/; fi' % env, pty=True)
        # collect static files
        with cd('releases/current/%(prj_path)s' % env):
            run('%(path)s/bin/python manage.py collectstatic -v0 --noinput' % env, pty=True)
            if env.use_photologue:
                run('cd %(prj_name)s/static; rm -rf photologue; ln -s %(path)s/photologue photologue;' % env, pty=True)
    
def migrate(param=''):
    "Update the database"
    require('prj_name')
    require('path')
    env.southparam = '--auto'
    if param=='first':
        run('cd %(path)s/releases/current/%(prj_path)s; %(path)s/bin/python manage.py syncdb --noinput' % env, pty=True)
        env.southparam = '--initial'
    #with cd('%(path)s/releases/current/%(prj_path)s' % env):
    #    run('%(path)s/bin/python manage.py schemamigration %(prj_name)s %(southparam)s && %(path)s/bin/python manage.py migrate %(prj_name)s' % env)
    #    # TODO: should also migrate other apps! get migrations from previous releases
    
def restart_webserver():
    "Restart the web server"
    require('webserver')
    env.webport = '8'+run('id -u', pty=True)[1:]
    with settings(warn_only=True):
        if env.webserver=='nginx':
            require('path')
            if env.use_daemontools:
                sudo('kill `cat %(path)s/logs/django.pid`' % env, pty=True) # kill process, daemontools will start it again, see service-run.sh
            if env.use_supervisor:
                if env.use_celery:
                    sudo('supervisorctl restart %(prj_name)s:appserver celery celerybeat' % env, pty=True)
                else:
                    sudo('supervisorctl restart %(prj_name)s:appserver' % env, pty=True)
            #require('prj_name')
            #run('cd %(path)s; bin/python releases/current/manage.py runfcgi method=threaded maxchildren=6 maxspare=4 minspare=2 host=127.0.0.1 port=%(webport)s pidfile=./logs/django.pid' % env)
        sudo('/etc/init.d/%(webserver)s reload' % env, pty=True)

########NEW FILE########
__FILENAME__ = gunicorn-settings
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from project_name import settings

bind = '127.0.0.1:8'+str(os.getuid())[1:]
workers = 2
#worker_class = 'eventlet'
#max_requests = 2048
pidfile = settings.rootrel('logs/django.pid')
user = settings.PROJECT_NAME
group = settings.PROJECT_NAME
logfile = settings.rootrel('logs/gunicorn.log')
#loglevel = 'info'
proc_name = 'gunicorn-'+settings.PROJECT_NAME

########NEW FILE########
__FILENAME__ = makeproject
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Configurator for new Django project, based on fiee's "generic_django_project".

Uses `urwid` (ncurses wrapper/replacement) from http://excess.org/urwid/
"""
import os, sys
import urwid

def _(text):
    return text

palette = [
    ('header', 'dark green', 'black', 'standout'),
    ('footer', 'white', 'dark green', 'standout'),
    ('button', 'white', 'dark cyan', 'underline'),
    ('question', 'default,bold', 'default', 'bold'),
    ('answer', 'dark green', 'default', 'default'),
    ('bg', 'black', 'light gray'),
]

questions = [
    ('project_name', _(u'Name of the project? (same as user on webserver and database!)'), 'project_name'),
    ('project_root', _(u'Local project root?'), '~/workspace/'),
    ('server_domain', _(u'Name of your domain? (without server name)'), 'example.com'),
    ('server_name', _(u'Name of your web server? (without domain name)'), 'www'),
    ('database_type', _(u'Database on server? (mysql, postgresql, sqlite)'), 'mysql'),
    ('webserver', _(u'Webserver software? (apache+mod_wsgi, nginx+gunicorn, nginx+fcgi)'), 'nginx+gunicorn'),
    ('processcontrol', _(u'Process supervision? (daemontools, supervisord'), 'supervisord'),
    ('messagequeue', _(u'Message queue? (celery)'), ''),
    ('modules', _(u'Use special modules? (feincms, medialibrary, photologue, south)'), 'feincms,medialibrary,south'),
    ('server_root_user', _(u'Name of server admin user?'), 'root'),
]

# make directory below workspace
# copy (or git clone) generic_django_project
# replace "project_name" in files...
# git init

# use feincms, medialibrary, photologue, daemontools, supervisord, celery, nginx/apache, mysql/postgresql ?

# get server name
# get server root account
# get server db root account
# make user account
# make db user account

answers = {}

widgets = [
]
offset = len(widgets) # number of widgets in front of questions
for key, text, default in questions:
    answers[key] = default
    widgets.append(urwid.Edit(('question', u'%s\n' % text), default))

content = urwid.SimpleListWalker(widgets)
listbox = urwid.ListBox(content)

def update(input):
    focus_widget, position = listbox.get_focus()
    if not hasattr(focus_widget, 'edit_text'):
        return
    if input == 'ctrl x': # delete input
        focus_widget.edit_text = ''
    if input in ('ctrl q', 'ctrl s', 'esc'):
        raise urwid.ExitMainLoop()
    key = questions[position-offset][0]
    answers[key] = focus_widget.edit_text
    listbox.set_focus(position+1)

header = urwid.Padding(urwid.Text(('header', _(u' Configure your project. Have fun! '))))
footer = urwid.Padding(urwid.Text(('footer', _(u' Abort with Ctrl-C, exit with Esc, delete a line with Ctrl-X. '))))

frame = urwid.Frame(listbox, header, footer)

loop = urwid.MainLoop(frame, palette, unhandled_input=update)
loop.run()

print answers
# STILL DOES NOTHING!

########NEW FILE########
