__FILENAME__ = middleware
from django.http import HttpResponseRedirect
from django.conf import settings
from re import compile


EXEMPT_URLS = [compile(settings.LOGIN_URL.lstrip('/'))]
if hasattr(settings, 'LOGIN_EXEMPT_URLS'):
    EXEMPT_URLS += [compile(expr) for expr in settings.LOGIN_EXEMPT_URLS]


class LoginRequiredMiddleware(object):
    """
    Middleware that requires a user to be authenticated to view any page other
    than LOGIN_URL. Exemptions to this requirement can optionally be specified
    in settings via a list of regular expressions in LOGIN_EXEMPT_URLS (which
    you can copy from your urls.py).

    Requires authentication middleware and template context processors to be
    loaded. You'll get an error if they aren't.
    """
    def process_request(self, request):
        assert hasattr(request, 'user')
        if not request.user.is_authenticated():
            path = request.path_info.lstrip('/')
            if not any(m.match(path) for m in EXEMPT_URLS):
                return HttpResponseRedirect(settings.LOGIN_URL)

########NEW FILE########
__FILENAME__ = base
"""Common settings and globals."""


from os.path import abspath, basename, dirname, join, normpath
from sys import path
import os

#url to login
LOGIN_REDIRECT_URL = '/accounts/%(username)s/'
LOGIN_URL = "/accounts/signin/"
LOGOUT_URL = "/accounts/signout/"

LOGIN_EXEMPT_URLS = (
    r'^accounts/',  # allow any URL under /account/*
)

#tracker config
TRACKERURL = os.environ.get('TRACKERURL', 'http://test.com/announce')

########## PATH CONFIGURATION
# Absolute filesystem path to the Django project directory:
DJANGO_ROOT = dirname(dirname(abspath(__file__)))

# Absolute filesystem path to the top-level project folder:
SITE_ROOT = dirname(DJANGO_ROOT)

# Site name:
SITE_NAME = basename(DJANGO_ROOT)

# Add our project to our pythonpath, this way we don't need to type our project
# name in our dotted import paths:
path.append(DJANGO_ROOT)
########## END PATH CONFIGURATION


########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = False

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
TEMPLATE_DEBUG = DEBUG
########## END DEBUG CONFIGURATION


########## MANAGER CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = (
    ('Your Name', 'your_email@example.com'),
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS
########## END MANAGER CONFIGURATION


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}
########## END DATABASE CONFIGURATION


########## GENERAL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#time-zone
TIME_ZONE = 'America/Los_Angeles'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = 'en-us'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
########## END GENERAL CONFIGURATION


########## MEDIA CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = normpath(join(SITE_ROOT, 'media'))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = '/media/'
########## END MEDIA CONFIGURATION


########## STATIC FILE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = normpath(join(SITE_ROOT, 'assets'))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = '/static/'

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/
#      #std:setting-STATICFILES_DIRS
STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, 'static')),
)

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/
#      #staticfiles-finders
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
########## END STATIC FILE CONFIGURATION


########## SECRET CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key only used for development and testing.
SECRET_KEY = r"9ledr(hq#a#r-sa8$l)5+3nila(h3pe5)+jvwdh8bbk%a+=!@-"
########## END SECRET CONFIGURATION


########## FIXTURE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/
#      #std:setting-FIXTURE_DIRS
FIXTURE_DIRS = (
    normpath(join(SITE_ROOT, 'fixtures')),
)
########## END FIXTURE CONFIGURATION


########## TEMPLATE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/
#      #template-context-processors
TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.request',
    'notifications.context_processors.notifications',
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
TEMPLATE_LOADERS = (
    'hamlpy.template.loaders.HamlPyFilesystemLoader',
    'hamlpy.template.loaders.HamlPyAppDirectoriesLoader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
TEMPLATE_DIRS = (
    normpath(join(SITE_ROOT, 'templates')),
)
########## END TEMPLATE CONFIGURATION


########## MIDDLEWARE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#middleware-classes
MIDDLEWARE_CLASSES = (
    # Default Django middleware.
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',

    'userena.middleware.UserenaLocaleMiddleware',

    'batter.middleware.LoginRequiredMiddleware',
)
########## END MIDDLEWARE CONFIGURATION


########## URL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = '%s.urls' % SITE_NAME
########## END URL CONFIGURATION


########## APP CONFIGURATION
DJANGO_APPS = (
    # Default Django apps:
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Useful template tags:
    'django.contrib.humanize',

    # Third-party app, but needs to be declared before d.c.admin.
    # See https://django-grappelli.readthedocs.org/en/2.4.5/quickstart.html
    'grappelli',

    # Admin panel and documentation:
    'django.contrib.admin',
    # 'django.contrib.admindocs',
)

THIRD_PARTY_APPS = (
    'django_extensions',
    'django_forms_bootstrap',
    'notification',
    'south',
    'haystack',
    'widget_tweaks',
    # Per-object permission system
    'guardian',
    'easy_thumbnails',
    'userena'
)

# Apps specific for this project go here.
LOCAL_APPS = (
    'batter',
    'core',
    'music',
    'notifications',
    'profiles',
    'torrents',
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
########## END APP CONFIGURATION


AUTH_PROFILE_MODULE = 'core.UserProfile'


AUTHENTICATION_BACKENDS = (
    'userena.backends.UserenaAuthenticationBackend',
    'guardian.backends.ObjectPermissionBackend',
    'django.contrib.auth.backends.ModelBackend',
)


ANONYMOUS_USER_ID = -1


########## LOGGING CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#logging
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
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}
########## END LOGGING CONFIGURATION


########## WSGI CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = 'wsgi.application'
########## END WSGI CONFIGURATION

########## django-notification CONFIGURATION
NOTIFICATION_BACKENDS = [
    ("email", "notification.backends.email.EmailBackend"),
    ("model", "notifications.backend.ModelBackend"),
]
########## END django-notification CONFIGURATION

########NEW FILE########
__FILENAME__ = local
"""Development settings and globals."""


from os.path import join, normpath

from base import *

########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
TEMPLATE_DEBUG = DEBUG
########## END DEBUG CONFIGURATION


########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
########## END EMAIL CONFIGURATION


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': normpath(join(DJANGO_ROOT, 'dev.db')),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}
########## END DATABASE CONFIGURATION


########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
########## END CACHE CONFIGURATION


########## TOOLBAR CONFIGURATION
# See: https://github.com/django-debug-toolbar/django-debug-toolbar
#      #installation
INSTALLED_APPS += (
    'debug_toolbar',
)

# See: https://github.com/django-debug-toolbar/django-debug-toolbar
#      #installation
INTERNAL_IPS = ('127.0.0.1',)

# See: https://github.com/django-debug-toolbar/django-debug-toolbar
#      #installation
MIDDLEWARE_CLASSES += (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False
}
########## END TOOLBAR CONFIGURATION

## Tracker CONFIGURATION
TRACKER_ANNOUNCE = 'http://localhost:7070/announce/'
##

########## HAYSTACK SEARCH CONFIGURATION
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine',  # noqa
        'URL': 'http://127.0.0.1:9200/',
        'INDEX_NAME': 'haystack',
    },
}
########## END HAYSTACK SEARCH CONFIGURATION

########NEW FILE########
__FILENAME__ = production
"""Production settings and globals."""


from os import environ

from base import *

# Normally you should not import ANYTHING from Django directly
# into your settings, but ImproperlyConfigured is an exception.
from django.core.exceptions import ImproperlyConfigured


def get_env_setting(setting):
    """ Get the environment setting or return exception """
    try:
        return environ[setting]
    except KeyError:
        error_msg = "Set the %s env variable" % setting
        raise ImproperlyConfigured(error_msg)

INSTALLED_APPS += ('gunicorn',)

########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host
EMAIL_HOST = environ.get('EMAIL_HOST', 'smtp.gmail.com')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host-password
EMAIL_HOST_PASSWORD = environ.get('EMAIL_HOST_PASSWORD', '')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host-user
EMAIL_HOST_USER = environ.get('EMAIL_HOST_USER', 'your_email@example.com')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-port
EMAIL_PORT = environ.get('EMAIL_PORT', 587)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = '[%s] ' % SITE_NAME

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-use-tls
EMAIL_USE_TLS = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = EMAIL_HOST_USER
########## END EMAIL CONFIGURATION


########## DATABASE CONFIGURATION
DATABASES = {}
########## END DATABASE CONFIGURATION


########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {}
########## END CACHE CONFIGURATION


########## SECRET CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = get_env_setting('SECRET_KEY')
########## END SECRET CONFIGURATION

########NEW FILE########
__FILENAME__ = test
from base import *

########## TEST SETTINGS
TEST_RUNNER = 'discover_runner.DiscoverRunner'
TEST_DISCOVER_TOP_LEVEL = SITE_ROOT
TEST_DISCOVER_ROOT = SITE_ROOT
TEST_DISCOVER_PATTERN = "test_*.py"
########## IN-MEMORY TEST DATABASE
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    },
}

########## HAYSTACK SEARCH CONFIGURATION
# "Simple" backend to avoid configuration for tests.
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
    },
}
########## END HAYSTACK SEARCH CONFIGURATION

########NEW FILE########
__FILENAME__ = test
from django.test import TestCase
from django.contrib.auth.models import User


class LoggedInTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'samantha',
            'samantha@example.com',
            'soliloquy'
        )
        self.client.login(username='samantha', password='soliloquy')

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.views.generic import TemplateView

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^$', TemplateView.as_view(template_name='index.html'), name="home"),

    # Examples:
    # url(r'^$', 'batter.views.home', name='home'),
    # url(r'^batter/', include('batter.foo.urls')),
    url(r'^accounts/', include('userena.urls')),
    url(r"^notifications/", include("notifications.urls")),
    url(r'^torrents/', include("torrents.urls")),
    url(r'^music/', include("music.urls")),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^grappelli/', include('grappelli.urls')),
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for batter project.

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
from os.path import abspath, dirname
from sys import path

SITE_ROOT = dirname(dirname(abspath(__file__)))
path.append(SITE_ROOT)

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "jajaja.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "batter.settings.production")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'UserProfile'
        db.create_table(u'core_userprofile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('mugshot', self.gf('django.db.models.fields.files.ImageField')(max_length=100, blank=True)),
            ('privacy', self.gf('django.db.models.fields.CharField')(default='registered', max_length=15)),
            ('language', self.gf('django.db.models.fields.CharField')(default='en', max_length=5)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='user_profile', unique=True, to=orm['auth.User'])),
        ))
        db.send_create_signal(u'core', ['UserProfile'])


    def backwards(self, orm):
        # Deleting model 'UserProfile'
        db.delete_table(u'core_userprofile')


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
        u'core.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'default': "'en'", 'max_length': '5'}),
            'mugshot': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'privacy': ('django.db.models.fields.CharField', [], {'default': "'registered'", 'max_length': '15'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'user_profile'", 'unique': 'True', 'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['core']
########NEW FILE########
__FILENAME__ = models
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _
from userena.models import UserenaLanguageBaseProfile


class UserProfile(UserenaLanguageBaseProfile):
    user = models.OneToOneField(User,
                                unique=True,
                                verbose_name=_('user'),
                                related_name='user_profile')

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

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "batter.settings.local")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from music.models import Artist, Label, Master, MusicUpload, Release


admin.site.register(Artist)
admin.site.register(Label)
admin.site.register(Master)
admin.site.register(MusicUpload)
admin.site.register(Release)

########NEW FILE########
__FILENAME__ = forms
from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext as _

from torrents.forms import TorrentUploadForm

from .types import UPLOAD_TYPES, FORMAT_TYPES, BITRATE_TYPES, RELEASE_TYPES
from .types import MEDIA_TYPES


class TorrentTypeForm(TorrentUploadForm):
    type = forms.ChoiceField(UPLOAD_TYPES)


class ReleaseInfoForm(forms.Form):
    artist = forms.CharField()
    album = forms.CharField()
    year = forms.CharField()


class FileInfoForm(forms.Form):
    format = forms.ChoiceField(FORMAT_TYPES)
    bitrate = forms.ChoiceField(BITRATE_TYPES)
    release = forms.ChoiceField(RELEASE_TYPES)
    media = forms.ChoiceField(MEDIA_TYPES)

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Artist'
        db.create_table(u'music_artist', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('name', self.gf('django.db.models.fields.TextField')()),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=255)),
        ))
        db.send_create_signal(u'music', ['Artist'])

        # Adding model 'Master'
        db.create_table(u'music_master', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('name', self.gf('django.db.models.fields.TextField')()),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=255)),
            ('main', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name=u'+', null=True, to=orm['music.Release'])),
        ))
        db.send_create_signal(u'music', ['Master'])

        # Adding M2M table for field artists on 'Master'
        db.create_table(u'music_master_artists', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('master', models.ForeignKey(orm[u'music.master'], null=False)),
            ('artist', models.ForeignKey(orm[u'music.artist'], null=False))
        ))
        db.create_unique(u'music_master_artists', ['master_id', 'artist_id'])

        # Adding model 'Release'
        db.create_table(u'music_release', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('name', self.gf('django.db.models.fields.TextField')()),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=255)),
            ('master', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['music.Master'], null=True, blank=True)),
        ))
        db.send_create_signal(u'music', ['Release'])


    def backwards(self, orm):
        # Deleting model 'Artist'
        db.delete_table(u'music_artist')

        # Deleting model 'Master'
        db.delete_table(u'music_master')

        # Removing M2M table for field artists on 'Master'
        db.delete_table('music_master_artists')

        # Deleting model 'Release'
        db.delete_table(u'music_release')


    models = {
        u'music.artist': {
            'Meta': {'object_name': 'Artist'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'})
        },
        u'music.master': {
            'Meta': {'object_name': 'Master'},
            'artists': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['music.Artist']", 'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'main': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'+'", 'null': 'True', 'to': u"orm['music.Release']"}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'})
        },
        u'music.release': {
            'Meta': {'object_name': 'Release'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'master': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['music.Master']", 'null': 'True', 'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['music']
########NEW FILE########
__FILENAME__ = 0002_auto__add_musicupload
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'MusicUpload'
        db.create_table(u'music_musicupload', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['music.Release'])),
            ('torrent', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['torrents.Torrent'], unique=True)),
        ))
        db.send_create_signal(u'music', ['MusicUpload'])


    def backwards(self, orm):
        # Deleting model 'MusicUpload'
        db.delete_table(u'music_musicupload')


    models = {
        u'music.artist': {
            'Meta': {'object_name': 'Artist'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'})
        },
        u'music.master': {
            'Meta': {'object_name': 'Master'},
            'artists': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['music.Artist']", 'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'main': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'+'", 'null': 'True', 'to': u"orm['music.Release']"}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'})
        },
        u'music.musicupload': {
            'Meta': {'object_name': 'MusicUpload'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['music.Release']"}),
            'torrent': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['torrents.Torrent']", 'unique': 'True'})
        },
        u'music.release': {
            'Meta': {'object_name': 'Release'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'master': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['music.Master']", 'null': 'True', 'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'})
        },
        u'torrents.torrent': {
            'Meta': {'object_name': 'Torrent'},
            'announce': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'announce_list': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'creation_date': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'encoding': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'files': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'length': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'md5sum': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'piece_length': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'pieces': ('django.db.models.fields.TextField', [], {'unique': 'True'})
        }
    }

    complete_apps = ['music']
########NEW FILE########
__FILENAME__ = 0003_auto__add_label__add_field_artist_image__add_field_artist_summary__add
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Label'
        db.create_table(u'music_label', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('name', self.gf('django.db.models.fields.TextField')()),
            ('parent_label', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['music.Label'], null=True, blank=True)),
        ))
        db.send_create_signal(u'music', ['Label'])

        # Adding field 'Artist.image'
        db.add_column(u'music_artist', 'image',
                      self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Artist.summary'
        db.add_column(u'music_artist', 'summary',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)

        # Adding field 'Artist.url'
        db.add_column(u'music_artist', 'url',
                      self.gf('django.db.models.fields.URLField')(default='', max_length=200, blank=True),
                      keep_default=False)

        # Adding field 'Master.image'
        db.add_column(u'music_master', 'image',
                      self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Master.label'
        db.add_column(u'music_master', 'label',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['music.Label'], null=True, blank=True),
                      keep_default=False)

        # Deleting field 'Release.slug'
        db.delete_column(u'music_release', 'slug')

        # Adding field 'Release.label'
        db.add_column(u'music_release', 'label',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['music.Label'], null=True, blank=True),
                      keep_default=False)

        # Adding field 'Release.year'
        db.add_column(u'music_release', 'year',
                      self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Release.catalog_num'
        db.add_column(u'music_release', 'catalog_num',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)

        # Adding field 'Release.scene'
        db.add_column(u'music_release', 'scene',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


        # Changing field 'Release.master'
        db.alter_column(u'music_release', 'master_id', self.gf('django.db.models.fields.related.ForeignKey')(default=1, to=orm['music.Master']))

    def backwards(self, orm):
        # Deleting model 'Label'
        db.delete_table(u'music_label')

        # Deleting field 'Artist.image'
        db.delete_column(u'music_artist', 'image')

        # Deleting field 'Artist.summary'
        db.delete_column(u'music_artist', 'summary')

        # Deleting field 'Artist.url'
        db.delete_column(u'music_artist', 'url')

        # Deleting field 'Master.image'
        db.delete_column(u'music_master', 'image')

        # Deleting field 'Master.label'
        db.delete_column(u'music_master', 'label_id')

        # Adding field 'Release.slug'
        db.add_column(u'music_release', 'slug',
                      self.gf('django.db.models.fields.SlugField')(default='release', max_length=255),
                      keep_default=False)

        # Deleting field 'Release.label'
        db.delete_column(u'music_release', 'label_id')

        # Deleting field 'Release.year'
        db.delete_column(u'music_release', 'year')

        # Deleting field 'Release.catalog_num'
        db.delete_column(u'music_release', 'catalog_num')

        # Deleting field 'Release.scene'
        db.delete_column(u'music_release', 'scene')


        # Changing field 'Release.master'
        db.alter_column(u'music_release', 'master_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['music.Master'], null=True))

    models = {
        u'music.artist': {
            'Meta': {'object_name': 'Artist'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        u'music.label': {
            'Meta': {'object_name': 'Label'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'parent_label': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['music.Label']", 'null': 'True', 'blank': 'True'})
        },
        u'music.master': {
            'Meta': {'object_name': 'Master'},
            'artists': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['music.Artist']", 'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'label': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['music.Label']", 'null': 'True', 'blank': 'True'}),
            'main': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'+'", 'null': 'True', 'to': u"orm['music.Release']"}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'})
        },
        u'music.musicupload': {
            'Meta': {'object_name': 'MusicUpload'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['music.Release']"}),
            'torrent': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['torrents.Torrent']", 'unique': 'True'})
        },
        u'music.release': {
            'Meta': {'object_name': 'Release'},
            'catalog_num': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['music.Label']", 'null': 'True', 'blank': 'True'}),
            'master': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['music.Master']"}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'scene': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'year': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'torrents.torrent': {
            'Meta': {'object_name': 'Torrent'},
            'announce': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'announce_list': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'creation_date': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'encoding': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'files': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'length': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'md5sum': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'piece_length': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'pieces': ('django.db.models.fields.TextField', [], {'unique': 'True'})
        }
    }

    complete_apps = ['music']
########NEW FILE########
__FILENAME__ = 0004_auto__del_field_master_label
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Master.label'
        db.delete_column(u'music_master', 'label_id')


    def backwards(self, orm):
        # Adding field 'Master.label'
        db.add_column(u'music_master', 'label',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['music.Label'], null=True, blank=True),
                      keep_default=False)


    models = {
        u'music.artist': {
            'Meta': {'object_name': 'Artist'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        u'music.label': {
            'Meta': {'object_name': 'Label'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'parent_label': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['music.Label']", 'null': 'True', 'blank': 'True'})
        },
        u'music.master': {
            'Meta': {'object_name': 'Master'},
            'artists': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['music.Artist']", 'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'main': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'+'", 'null': 'True', 'to': u"orm['music.Release']"}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'})
        },
        u'music.musicupload': {
            'Meta': {'object_name': 'MusicUpload'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['music.Release']"}),
            'torrent': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['torrents.Torrent']", 'unique': 'True'})
        },
        u'music.release': {
            'Meta': {'object_name': 'Release'},
            'catalog_num': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['music.Label']", 'null': 'True', 'blank': 'True'}),
            'master': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['music.Master']"}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'scene': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'year': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'torrents.torrent': {
            'Meta': {'object_name': 'Torrent'},
            'announce': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'announce_list': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'creation_date': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'encoding': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'files': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'length': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'md5sum': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'piece_length': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'pieces': ('django.db.models.fields.TextField', [], {'unique': 'True'})
        }
    }

    complete_apps = ['music']
########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices
from model_utils.models import TimeStampedModel

optional = {'blank': True, 'null': True}


@python_2_unicode_compatible
class MusicBaseModel(TimeStampedModel):
    name = models.TextField()
    slug = models.SlugField(max_length=255)
    image = models.ImageField(upload_to="music_image", **optional)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class MusicUpload(TimeStampedModel):
    release = models.ForeignKey('Release')
    torrent = models.OneToOneField('torrents.Torrent')
    format = Choices(('mp3', _('MP3')),
                     ('flac', _('FLAC')),
                     ('aac', _('AAC')),
                     ('ac3', _('AC3')),
                     ('dts', _('DTS')))
    bitrate = Choices(('192', _('192')),
                      ('apsvbr', _('APS (VBR)')),
                      ('v2vbr', _('V2 (VBR)')),
                      ('v1vbr', _('V1 (VBR)')),
                      ('256', _('256')),
                      ('apxvbr', _('APX (VBR)')),
                      ('v0vbr', _('V0 (VBR)')),
                      ('320', _('320')),
                      ('lossless', _('Lossless')),
                      ('24bitlossless', _('24bit Lossless')),
                      ('v8vbr', _('V8 (VBR)')),
                      ('other', _('Other')))

    class Meta:
        verbose_name = _('Music Upload')
        verbose_name_plural = _('Music Uploads')

    def __str__(self):
        return "{} - {}".format(self.release, self.torrent)


class Artist(MusicBaseModel):
    summary = models.TextField(blank=True)
    # TODO: Add more types of url (last.fm, spotify, etc)?
    url = models.URLField(blank=True)

    class Meta:
        verbose_name = _('Artist')
        verbose_name_plural = _('Artists')

    def get_absolute_url(self):
        return reverse('music_artist_detail',
                       kwargs={'pk': self.pk, 'slug': self.slug})


@python_2_unicode_compatible
class Master(MusicBaseModel):
    artists = models.ManyToManyField('Artist', **optional)
    main = models.ForeignKey('Release', related_name='+', **optional)

    class Meta:
        verbose_name = _('Master')
        verbose_name_plural = _('Masters')

    def get_absolute_url(self):
        return reverse('music_master_detail',
                       kwargs={'pk': self.pk, 'slug': self.slug})

    def __str__(self):
        return "{} - {}".format(", ".join(artist.name
                                          for artist
                                          in self.artists.all()),
                                self.name)


@python_2_unicode_compatible
class Release(TimeStampedModel):
    master = models.ForeignKey('Master')
    label = models.ForeignKey('Label', **optional)
    release_type = Choices(('album', _('Album')),
                           ('soundtrack', _('Soundtrack')),
                           ('ep', _('EP')),
                           ('anthology', _('Anthology')),
                           ('compilation', _('Compilation')),
                           ('djmix', _('DJ Mix')),
                           ('single', _('Single')),
                           ('livealbum', _('Live Album')),
                           ('remix', _('Remix')),
                           ('bootleg', _('Bootleg')),
                           ('interview', _('Interview')),
                           ('mixtape', _('Mixtape')),
                           ('concertrecording', _('Concert Recording')),
                           ('demo', _('Demo')),
                           ('unknown', _('Unknown')))
    year = models.PositiveIntegerField(**optional)
    catalog_num = models.TextField(blank=True)
    name = models.TextField(blank=True)
    scene = models.BooleanField()

    class Meta:
        verbose_name = _('Release')
        verbose_name_plural = _('Releases')

    def __str__(self):
        return "{} ({})".format(self.master, self.name)


@python_2_unicode_compatible
class Label(TimeStampedModel):
    name = models.TextField()
    parent_label = models.ForeignKey('self', **optional)

    class Meta:
        verbose_name = _('Label')
        verbose_name_plural = _('Labels')

    def __str__(self):
        return "{}".format(self.name)

########NEW FILE########
__FILENAME__ = search_indexes
from haystack import indexes

from .models import Artist, Master


class ArtistIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True, use_template=True)

    def get_model(self):
        return Artist

    def index_queryset(self, using=None):
        return self.get_model().objects.all()


class MasterIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True, use_template=True)

    def get_model(self):
        return Master

    def index_queryset(self, using=None):
        return self.get_model().objects.all()

########NEW FILE########
__FILENAME__ = test_models
from __future__ import absolute_import, unicode_literals

import hashlib

from django.test import TestCase

from ..models import Artist, Master, Release


class ArtistTests(TestCase):
    def test_absolute_url(self):
        # Just poke it
        artist = Artist(name="Okkervil River", slug="Okkervil-River")
        artist.save()
        artist.get_absolute_url()


class MasterTests(TestCase):
    def test_absolute_url(self):
        # Just poke it
        master = Master(name="Black Sheep Boy", slug="Black-Sheep-Boy")
        master.save()
        master.get_absolute_url()

########NEW FILE########
__FILENAME__ = test_search_indexes
from __future__ import absolute_import, unicode_literals

from django.test import TestCase

from ..models import Artist, Master
from ..search_indexes import ArtistIndex, MasterIndex


class ArtistIndexTests(TestCase):
    def setUp(self):
        self.index = ArtistIndex()

    def test_get_model(self):
        self.assertEquals(self.index.get_model(), Artist)

    def test_index_queryset(self):
        # Querysets are covered by Django tests, so just make sure that the QS
        # model is the same as the index model.
        self.assertEquals(self.index.index_queryset().model,
                          self.index.get_model())


class MasterIndexTests(TestCase):
    def setUp(self):
        self.index = MasterIndex()

    def test_get_model(self):
        self.assertEquals(self.index.get_model(), Master)

    def test_index_queryset(self):
        # Querysets are covered by Django tests, so just make sure that the QS
        # model is the same as the index model.
        self.assertEquals(self.index.index_queryset().model,
                          self.index.get_model())

########NEW FILE########
__FILENAME__ = test_views
from __future__ import absolute_import, unicode_literals

from django.core.urlresolvers import reverse

from batter.test import LoggedInTestCase
from ..models import Artist, Master, Release


class ArtistDetailTests(LoggedInTestCase):
    def setUp(self):
        self.artist = Artist(name="Okkervil River", slug="Okkervil-River")
        self.artist.save()
        self.url = reverse("music_artist_detail",
                           kwargs={'pk': self.artist.pk,
                                   'slug': self.artist.slug})
        super(ArtistDetailTests, self).setUp()

    def test_get(self):
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)

    def test_slug_redirect(self):
        response = self.client.get(reverse("music_artist_detail",
                                           kwargs={'pk': self.artist.pk,
                                                   'slug': 'wrong-slug'}))
        self.assertEquals(response.status_code, 301)


class MasterDetailTests(LoggedInTestCase):
    def setUp(self):
        self.artist = Artist(name="Okkervil River",
                             slug="Okkervil-River")
        self.artist.save()
        self.master = Master(name="Black Sheep Boy",
                             slug="Black-Sheep-Boy")
        self.master.save()
        self.release = Release(name="Original",
                               master=self.master)
        self.release.save()
        self.master.artists.add(self.artist)
        self.master.main = self.release
        self.master.save()
        self.url = reverse("music_master_detail",
                           kwargs={'pk': self.master.pk,
                                   'slug': self.master.slug})
        super(MasterDetailTests, self).setUp()

    def test_get(self):
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)

########NEW FILE########
__FILENAME__ = types
from django.utils.translation import ugettext as _

UPLOAD_TYPES = (
    ('music', _('Music')),
    ('applications', _('Applications')),
    ('ebooks', _('E-Books')),
    ('audiobooks', _('Audiobooks')),
    ('comedy', _('Comedy / Spoken Word')),
    ('comics', _('Comics')),
)

FORMAT_TYPES = (
    ('mp3', 'MP3'),
    ('flac', 'FLAC'),
    ('aac', 'AAC'),
    ('ac3', 'AC3'),
    ('dts', 'DTS'),
)

BITRATE_TYPES = (
    ('192', '192'),
    ('apsvbr', 'APS (VBR)'),
    ('v2vbr', 'V2 (VBR)'),
    ('v1vbr', 'V1 (VBR)'),
    ('256', '256'),
    ('apxvbr', 'APX (VBR)'),
    ('v0vbr', 'V0 (VBR)'),
    ('320', '320'),
    ('lossless', _('Lossless')),
    ('24bitlossless', _('24Bit Lossless')),
    ('v8vbr', 'V8 (VBR)'),
    ('other', _('Other')),
)

MEDIA_TYPES = (
    ('cd', 'CD'),
    ('dvd', 'DVD'),
    ('vinyl', _('Vinyl')),
    ('soundboard', _('Soundboard')),
    ('sacd', 'SACD'),
    ('dat', 'DAT'),
    ('cassette', _('Cassette')),
    ('web', 'WEB'),
    ('bluray', 'Blu-Ray'),
)

RELEASE_TYPES = (
    ('album', _('Album')),
    ('soundtrack', _('Soundtrack')),
    ('ep', _('EP')),
    ('anthology', _('Anthology')),
    ('compilation', _('Compilation')),
    ('djmix', _('DJ Mix')),
    ('single', _('Single')),
    ('livealbum', _('Live Album')),
    ('remix', _('Remix')),
    ('bootleg', _('Bootleg')),
    ('interview', _('Interview')),
    ('mixtape', _('Mixtape')),
    ('unknown', _('Unknown'))
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from .views import SearchView, ArtistView, MasterView
from .views.upload import MusicUploadWizard, FORMS, CONDITIONS

urlpatterns = patterns(
    '',
    url(r'^search/$',
        SearchView(),
        name='music_search'),
    url(r'^upload/$',
        # TODO: use form_list (see MusicUploadWizard definition)
        MusicUploadWizard.as_view(FORMS, condition_dict=CONDITIONS),
        name="upload_music"),
    url(r'^(?P<slug>[-\w]+)-(?P<pk>\d+)/$',
        ArtistView.as_view(),
        name="music_artist_detail"),
    url(r'^album/(?P<slug>[-\w]+)-(?P<pk>\d+)/$',
        MasterView.as_view(),
        name="music_master_detail"),
)

########NEW FILE########
__FILENAME__ = generic
from django.core.urlresolvers import resolve
from django.shortcuts import redirect
from django.views.generic.detail import DetailView


class EnforcingSlugDetailView(DetailView):
    """
    A DetailView that looks up by pk but enforces a valid slug in the url.
    """
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        slug = self.kwargs.get(self.slug_url_kwarg, None)
        current_url = resolve(request.path_info).url_name

        if self.get_object().slug != slug:
            return redirect(current_url,
                            pk=self.object.pk,
                            slug=self.object.slug,
                            permanent=True)

        return super(EnforcingSlugDetailView, self).dispatch(request,
                                                             *args,
                                                             **kwargs)

########NEW FILE########
__FILENAME__ = music
from ..models import Artist, Master
from .generic import EnforcingSlugDetailView


class ArtistView(EnforcingSlugDetailView):
    model = Artist


class MasterView(EnforcingSlugDetailView):
    model = Master

########NEW FILE########
__FILENAME__ = search
from haystack.query import SearchQuerySet
from haystack.views import FacetedSearchView


class SearchView(FacetedSearchView):
    def __init__(self, *args, **kwargs):
        sqs = SearchQuerySet()
        kwargs.update({
            'searchqueryset': sqs
        })
        super(SearchView, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = upload
from __future__ import absolute_import, unicode_literals

import os

from django.conf import settings
from django.contrib.formtools.wizard.views import CookieWizardView
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.defaultfilters import slugify

from ..forms import TorrentTypeForm, ReleaseInfoForm, FileInfoForm


def torrent_is_type(torrent_type):
    def check(wizard):
        cleaned_data = (wizard.get_cleaned_data_for_step('torrent_type')
                        or {'type': 'none'})
        return cleaned_data['type'] == torrent_type
    return check

FORMS = [
    ("torrent_type", TorrentTypeForm),
    ("release", ReleaseInfoForm),
    ("file", FileInfoForm)
]

TEMPLATES = {
    "default": "music/upload/base.html",
    "release": "music/upload/release.html",
}

CONDITIONS = {
    "release": torrent_is_type('music'),
    "file": torrent_is_type('music')
}


class MusicUploadWizard(CookieWizardView):
#    TODO: use form_list once support for this gets released
#          (currently in django dev version)
#    form_list = [MusicUploadForm]
    file_storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT,
                                                           'tmp'))

    def get_template_names(self):
        try:
            return [TEMPLATES[self.steps.current]]
        except:
            return [TEMPLATES["default"]]

    def get_context_data(self, form, **kwargs):
        context = super(MusicUploadWizard, self).get_context_data(form=form,
                                                                  **kwargs)
        cleaned_data = (self.get_cleaned_data_for_step("torrent_type")
                        or {'torrent_file': None})
        if cleaned_data["torrent_file"]:
            context.update({'torrent_name': cleaned_data["torrent_file"].name})
        return context

    def done(self, form_list, **kwargs):
        return HttpResponse('done')

########NEW FILE########
__FILENAME__ = backend
from django.utils.translation import ugettext

from notification import backends

from . import models


class ModelBackend(backends.BaseBackend):
    spam_sensitivity = 1

    def deliver(self, recipient, sender, notice_type, extra_context):
        context = self.default_context()
        context.update({
            "recipient": recipient,
            "notice": ugettext(notice_type.display)
        })
        context.update(extra_context)

        messages = self.get_formatted_messages((
            "short.txt",
            "full.txt",
            "short.html",
            "full.html"
        ), notice_type.label, context)

        notification = models.Notification()
        notification.recipient = recipient

        notification.title = messages["short.html"]
        notification.body = messages["full.html"]
        notification.title_text = messages["short.txt"]
        notification.body_text = messages["full.txt"]

        notification.save()

########NEW FILE########
__FILENAME__ = context_processors
from . import models


def notifications(request):
    """
    Context processor for notifications

    This is required because I don't want to override Django's
    RelatedManager, so it's easier to attack this problem in reverse.
    """
    user = request.user
    if user.is_authenticated():
        notifications = models.Notification.objects.by_user(user).unseen()
        return {
            'unseen_notifications': notifications
        }
    else:
        return {}

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Notification'
        db.create_table(u'notifications_notification', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('recipient', self.gf('django.db.models.fields.related.ForeignKey')(related_name='notifications', to=orm['auth.User'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('body', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('sent_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('seen_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
        ))
        db.send_create_signal(u'notifications', ['Notification'])


    def backwards(self, orm):
        # Deleting model 'Notification'
        db.delete_table(u'notifications_notification')


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
        u'notifications.notification': {
            'Meta': {'object_name': 'Notification'},
            'body': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'recipient': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'notifications'", 'to': u"orm['auth.User']"}),
            'seen_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'sent_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        }
    }

    complete_apps = ['notifications']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_notification_seen
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Notification.seen'
        db.add_column(u'notifications_notification', 'seen',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Notification.seen'
        db.delete_column(u'notifications_notification', 'seen')


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
        u'notifications.notification': {
            'Meta': {'object_name': 'Notification'},
            'body': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'recipient': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'notifications'", 'to': u"orm['auth.User']"}),
            'seen': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'seen_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'sent_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        }
    }

    complete_apps = ['notifications']
########NEW FILE########
__FILENAME__ = 0003_auto__add_field_notification_title_text__add_field_notification_body_t
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Notification.title_text'
        db.add_column(u'notifications_notification', 'title_text',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)

        # Adding field 'Notification.body_text'
        db.add_column(u'notifications_notification', 'body_text',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)


        # Changing field 'Notification.body'
        db.alter_column(u'notifications_notification', 'body', self.gf('django.db.models.fields.TextField')())

        # Changing field 'Notification.title'
        db.alter_column(u'notifications_notification', 'title', self.gf('django.db.models.fields.TextField')())

    def backwards(self, orm):
        # Deleting field 'Notification.title_text'
        db.delete_column(u'notifications_notification', 'title_text')

        # Deleting field 'Notification.body_text'
        db.delete_column(u'notifications_notification', 'body_text')


        # Changing field 'Notification.body'
        db.alter_column(u'notifications_notification', 'body', self.gf('django.db.models.fields.CharField')(max_length=512))

        # Changing field 'Notification.title'
        db.alter_column(u'notifications_notification', 'title', self.gf('django.db.models.fields.CharField')(max_length=64))

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
        u'notifications.notification': {
            'Meta': {'object_name': 'Notification'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'body_text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'recipient': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'notifications'", 'to': u"orm['auth.User']"}),
            'seen': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'seen_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'sent_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.TextField', [], {}),
            'title_text': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        }
    }

    complete_apps = ['notifications']
########NEW FILE########
__FILENAME__ = 0004_auto__del_field_notification_seen
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Notification.seen'
        db.delete_column(u'notifications_notification', 'seen')


    def backwards(self, orm):
        # Adding field 'Notification.seen'
        db.add_column(u'notifications_notification', 'seen',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


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
        u'notifications.notification': {
            'Meta': {'ordering': "['-sent_at']", 'object_name': 'Notification'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'body_text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'recipient': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'notifications'", 'to': u"orm['auth.User']"}),
            'seen_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'sent_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.TextField', [], {}),
            'title_text': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        }
    }

    complete_apps = ['notifications']
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.db.models.query import QuerySet
from django.conf import settings
from django.utils.timezone import now


class NotificationQuerySet(QuerySet):
    def mark_seen(self):
        return self.update(seen_at=now())

    def unseen(self):
        return self.filter(seen_at=None)


class NotificationManager(models.Manager):
    def get_queryset(self):
        return NotificationQuerySet(self.model)

    def by_user(self, user):
        return self.get_queryset().filter(recipient=user)


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='notifications'
    )

    title = models.TextField(blank=False, null=False)
    body = models.TextField(blank=False, null=False)
    title_text = models.TextField(blank=True, null=False)
    body_text = models.TextField(blank=True, null=False)

    sent_at = models.DateTimeField(auto_now_add=True)
    seen_at = models.DateTimeField(null=True)

    objects = NotificationManager()

    def mark_seen(self):
        """ Mark a Notification as having been seen """
        self.seen_at = now()
        return self

    def as_dict(self):
        """ Prepare a Notification for display, via e.g. JSON """
        return {
            "text": {
                "title": self.title_text,
                "body": self.body_text,
            },
            "html": {
                "title": self.title,
                "body": self.body,
            },
            "seen": self.seen,
            "sent_at": self.sent_at,
        }

    @property
    def seen(self):
        return self.seen_at is not None

    class Meta:
        ordering = ['-sent_at']

########NEW FILE########
__FILENAME__ = test_backend
from django.test import TestCase
from django.contrib.auth.models import User

from notification.models import NoticeType

from ..backend import ModelBackend
from ..models import Notification


class StubbedModelBackend(ModelBackend):
    def get_formatted_messages(self, templates, label, context):
        return dict(zip(templates, ['message'] * len(templates)))


class ModelBackendTests(TestCase):
    def setUp(self):
        self.backend = StubbedModelBackend('stubmodel')
        self.samantha = User.objects.create_user(
            'samantha',
            'samantha@example.com',
            'soliloquy'
        )
        self.new_message, _ = NoticeType.objects.get_or_create(
            label='mail',
            display='New Private Message',
            description='Notification when you receive a private message',
            default=1
        )

    def test_deliver(self):
        self.backend.deliver(
            recipient=self.samantha,
            sender=None,
            notice_type=self.new_message,
            extra_context={}
        )
        results = Notification.objects.by_user(self.samantha).unseen()
        self.assertEquals(len(results), 1)

        notification = results.get()
        self.assertEquals(notification.title, 'message')
        self.assertEquals(notification.body, 'message')
        self.assertEquals(notification.title_text, 'message')
        self.assertEquals(notification.body_text, 'message')

########NEW FILE########
__FILENAME__ = test_context_processors
import json

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.contrib.auth.models import User

from ..models import Notification


class NotificationsContextProcessorTests(TestCase):
    def setUp(self):
        self.samantha = User.objects.create_user(
            'samantha',
            'samantha@example.com',
            'soliloquy'
        )
        self.samantha_mail, _ = Notification.objects.get_or_create(
            recipient=self.samantha,
            title='You\'ve got mail!',
            body='joe sent you a message',
            title_text='You\'ve got mail!',
            body_text='joe sent you a message'
        )

    def test_authenticated(self):
        self.client.login(username='samantha', password='soliloquy')
        response = self.client.get('/')
        self.assertEquals(response.status_code, 200)
        self.assertIn('unseen_notifications', response.context)

    def test_unauthenticated(self):
        response = self.client.get('/', follow=True)
        self.assertEquals(response.status_code, 200)
        self.assertNotIn('unseen_notifications', response.context)

########NEW FILE########
__FILENAME__ = test_models
from django.test import TestCase
from django.contrib.auth.models import User

from ..models import Notification


class NotificationTests(TestCase):
    def setUp(self):
        self.samantha = User.objects.create_user(
            'samantha',
            'samantha@example.com',
            'soliloquy'
        )
        self.joe = User.objects.create_user(
            'joe',
            'joe@example.com',
            'antiphony'
        )
        self.samantha_mail, _ = Notification.objects.get_or_create(
            recipient=self.samantha,
            title='You\'ve got mail!',
            body='joe sent you a message',
            title_text='You\'ve got mail!',
            body_text='joe sent you a message'
        )

    def test_model_mark_seen(self):
        self.assertEquals(self.samantha_mail.seen, False)
        self.assertIsNone(self.samantha_mail.seen_at)

        self.samantha_mail.mark_seen().save()

        self.assertEquals(self.samantha_mail.seen, True)
        self.assertIsNotNone(self.samantha_mail.seen_at)

    def test_manager_by_user(self):
        results = Notification.objects.by_user(self.samantha)

        self.assertIn(self.samantha_mail, results)
        self.assertEqual(len(results), 1)

    def test_manager_by_other_user(self):
        results = Notification.objects.by_user(self.joe)

        self.assertEqual(len(results), 0)

    def test_queryset_unseen(self):
        results = Notification.objects.by_user(self.samantha).unseen()

        self.assertIn(self.samantha_mail, results)

        self.samantha_mail.mark_seen().save()

        results = Notification.objects.by_user(self.samantha).unseen()

        self.assertNotIn(self.samantha_mail, results)

    def test_queryset_mark_seen(self):
        self.assertEquals(self.samantha_mail.seen, False)

        results = Notification.objects.by_user(self.samantha).unseen()
        results.mark_seen()

        self.samantha_mail = Notification.objects.get(
            pk=self.samantha_mail.pk
        )

        self.assertEquals(self.samantha_mail.seen, True)

    def test_model_as_dict(self):
        obj = self.samantha_mail.as_dict()
        self.assertIn("text", obj)
        self.assertIn("html", obj)
        self.assertIn("seen", obj)
        self.assertEquals(obj['seen'], False)
        self.assertIsNotNone(obj['sent_at'])
        self.assertEquals(obj['text']['title'], "You've got mail!")
        self.assertEquals(obj['text']['body'], "joe sent you a message")
        self.assertEquals(obj['html']['title'], "You've got mail!")
        self.assertEquals(obj['html']['body'], "joe sent you a message")

########NEW FILE########
__FILENAME__ = test_views
import json

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.contrib.auth.models import User

from ..models import Notification


class BaseNotificationTests(TestCase):
    def setUp(self):
        self.samantha = User.objects.create_user(
            'samantha',
            'samantha@example.com',
            'soliloquy'
        )
        self.samantha_mail, _ = Notification.objects.get_or_create(
            recipient=self.samantha,
            title='You\'ve got mail!',
            body='joe sent you a message',
            title_text='You\'ve got mail!',
            body_text='joe sent you a message'
        )

    def generate_bunk(self, num):
        bunk = []
        for i in range(num):
            n, _ = Notification.objects.get_or_create(
                recipient=self.samantha,
                title='You\'ve got mail! ' + str(i),
                body='joe sent you a message',
                title_text='You\'ve got mail!' + str(i),
                body_text='joe sent you a message'
            )
            bunk.append(n)
        return bunk

    def login(self):
        self.client.login(username='samantha', password='soliloquy')


class NotificationAPITests(BaseNotificationTests):
    def fetch_list_response(self):
        url = reverse('notifications_list')
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        return response

    def fetch_list(self):
        self.login()
        response = self.fetch_list_response()
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        return data

    def test_list_authentication(self):
        response = self.fetch_list_response()
        self.assertEquals(response.status_code, 302)
        self.assertIn('signin', response['Location'])

    def test_list_pagination(self):
        self.generate_bunk(60)
        data = self.fetch_list()
        self.assertIn('total', data)
        self.assertEquals(data['total'], 61)
        self.assertIn('pages', data)
        self.assertIn('count', data['pages'])
        self.assertEquals(len(data['results']), 10)
        self.assertEquals(data['pages']['count'], 7)

    def test_list_single(self):
        data = self.fetch_list()
        self.assertEquals(len(data['results']), 1)
        result = data['results'][0]
        self.assertEquals(result['seen'], False)


class NotificationHTMLTests(BaseNotificationTests):
    def fetch_list_response(self, data={}):
        url = reverse('notifications_list')
        response = self.client.get(url, data=data)
        return response

    def fetch_list(self, data={}):
        self.login()
        response = self.fetch_list_response(data)
        self.assertEquals(response.status_code, 200)
        return response

    def test_list_authentication(self):
        response = self.fetch_list_response()
        self.assertEquals(response.status_code, 302)
        self.assertIn('signin', response['Location'])

    def test_list_pagination(self):
        self.generate_bunk(60)
        response = self.fetch_list()
        self.assertEquals(len(response.context['object_list']), 20)
        self.assertIsNotNone(response.context['paginator'])
        self.assertEquals(response.context['is_paginated'], True)

    def test_list_pagination_page_2(self):
        self.generate_bunk(60)
        response = self.fetch_list(data={'page': 2})
        self.assertEquals(len(response.context['object_list']), 20)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

from . import views

urlpatterns = patterns(
    '',
    url(
        r'^list/$',
        views.NotificationList.as_view(),
        name="notifications_list"
    ),
)

########NEW FILE########
__FILENAME__ = views
from django.views.generic.list import ListView

from braces.views import LoginRequiredMixin, JSONResponseMixin, \
    AjaxResponseMixin

from . import models


class NotificationList(
    LoginRequiredMixin,
    JSONResponseMixin,
    AjaxResponseMixin,
    ListView
):
    http_method_names = ['get']  # get only
    allow_empty = True
    template_name = "notifications/list.html"
    ajax_show_on_page = 10
    paginate_by = 20
    content_type = 'text/html'

    def get_queryset(self):
        return models.Notification.objects.by_user(self.request.user)

    def get_ajax(self, request):
        self.object_list = self.get_queryset()
        self.content_type = 'application/json'

        paginator, page, object_list, more_pages = self.paginate_queryset(
            self.object_list,
            self.ajax_show_on_page
        )

        next_p = page.next_page_number() if page.has_next() else None
        prev_p = page.previous_page_number() if page.has_previous() else None
        object_list = [o.as_dict() for o in object_list]
        return self.render_json_response({
            'total': paginator.count,
            'pages': {
                'count': paginator.num_pages,
                'next': next_p,
                'previous': prev_p,
            },
            'results': object_list,
        })

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

########NEW FILE########
__FILENAME__ = models
import uuid

from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    user = models.ForeignKey(User, unique=True)
    trackerid = models.CharField(max_length=32, blank=True, null=True)

    def save(self, *args, **kwargs):
        """
        override save method to generate a trackerid
        for torrent tracker url generation
        """

        if not self.trackerid:
            self.trackerid = generate_trackerid()
        super(Profile, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.user.username


# helpers
def generate_trackerid():
    """
    generate a uuid and check if it already exists in a profile
    """

    trackerid = None
    while trackerid is None or \
            Profile.objects.filter(trackerid=trackerid).exists():
        trackerid = uuid.uuid4().hex
    return trackerid

########NEW FILE########
__FILENAME__ = test_models
from django.test import TestCase
from django.contrib.auth.models import User

from .. import models


class ProfileTests(TestCase):
    def setUp(self):
        self.samantha = User.objects.create_user(
            'samantha',
            'samantha@example.com',
            'soliloquy'
        )
        self.profile = models.Profile(user=self.samantha)

    def test_trackerid_generation(self):
        profile = self.profile
        self.assertIsNone(profile.trackerid)
        profile.save()
        self.assertEquals(len(profile.trackerid), 32)

    def test_unicode(self):
        self.assertEquals(unicode(self.profile), "samantha")


class HelperTests(TestCase):
    def test_generate_trackerid(self):
        trackerid = models.generate_trackerid()
        self.assertEquals(len(trackerid), 32)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from torrents.models import Torrent

admin.site.register(Torrent)

########NEW FILE########
__FILENAME__ = fields
from BTL import BTFailure
from django import forms
from django.core.exceptions import ValidationError

from .models import Torrent


class TorrentField(forms.FileField):
    def to_python(self, data):
        data = super(TorrentField, self).to_python(data)
        if data is None:
            raise ValidationError(self.error_messages['empty'])

        try:
            return Torrent.from_torrent_file(data)
        except BTFailure as e:
            raise ValidationError(str(e))

########NEW FILE########
__FILENAME__ = forms
from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext as _

from .fields import TorrentField


class TorrentUploadForm(forms.Form):
    torrent_file = TorrentField(label=_("torrent file"))

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Torrent'
        db.create_table(u'torrents_torrent', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('announce', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('announce_list', self.gf('jsonfield.fields.JSONField')(null=True, blank=True)),
            ('creation_date', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('comment', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('created_by', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('encoding', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('piece_length', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('pieces', self.gf('django.db.models.fields.TextField')(unique=True)),
            ('is_private', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('name', self.gf('django.db.models.fields.TextField')()),
            ('length', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('md5sum', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('files', self.gf('jsonfield.fields.JSONField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'torrents', ['Torrent'])

        # Adding model 'Upload'
        db.create_table(u'torrents_upload', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('_subclass_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('torrent', self.gf('django.db.models.fields.related.OneToOneField')(related_name=u'upload', unique=True, to=orm['torrents.Torrent'])),
            ('uploader', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('parent_content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('parent_object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('upload_group', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'uploads', to=orm['torrents.UploadGroup'])),
        ))
        db.send_create_signal(u'torrents', ['Upload'])

        # Adding model 'UploadGroup'
        db.create_table(u'torrents_uploadgroup', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('_subclass_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal(u'torrents', ['UploadGroup'])


    def backwards(self, orm):
        # Deleting model 'Torrent'
        db.delete_table(u'torrents_torrent')

        # Deleting model 'Upload'
        db.delete_table(u'torrents_upload')

        # Deleting model 'UploadGroup'
        db.delete_table(u'torrents_uploadgroup')


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
        u'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        u'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'taggit_taggeditem_tagged_items'", 'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'taggit_taggeditem_items'", 'to': u"orm['taggit.Tag']"})
        },
        u'torrents.torrent': {
            'Meta': {'object_name': 'Torrent'},
            'announce': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'announce_list': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'creation_date': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'encoding': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'files': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'length': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'md5sum': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'piece_length': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'pieces': ('django.db.models.fields.TextField', [], {'unique': 'True'})
        },
        u'torrents.upload': {
            'Meta': {'object_name': 'Upload'},
            '_subclass_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'parent_content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            'parent_object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'torrent': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "u'upload'", 'unique': 'True', 'to': u"orm['torrents.Torrent']"}),
            'upload_group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'uploads'", 'to': u"orm['torrents.UploadGroup']"}),
            'uploader': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'torrents.uploadgroup': {
            'Meta': {'object_name': 'UploadGroup'},
            '_subclass_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'})
        }
    }

    complete_apps = ['torrents']
########NEW FILE########
__FILENAME__ = models
from __future__ import absolute_import, unicode_literals

import bencode
import binascii
from jsonfield import JSONField

from django.db import models
from django.core.urlresolvers import reverse
from django.utils.encoding import python_2_unicode_compatible, force_bytes
from django.utils.translation import ugettext as _


@python_2_unicode_compatible
class Torrent(models.Model):
    announce = models.URLField(help_text=_("The announce URL of the tracker."))
    announce_list = JSONField(blank=True, null=True)
    creation_date = models.PositiveIntegerField(
        blank=True, null=True,
        help_text=_("Torrent creation time in UNIX epoch format."))
    comment = models.TextField(
        blank=True, null=True,
        help_text=_("Free-form textual comment of the torrent author."))
    created_by = models.TextField(
        blank=True, null=True,
        help_text=_("Name and version of the program used to create the "
                    "torrent."))
    encoding = models.TextField(
        blank=True, null=True,
        help_text=_("Encoding used to generate the pieces part of the info "
                    "dictionary in the torrent metadata"))
    piece_length = models.PositiveIntegerField(
        blank=True, null=True,
        help_text=_("Number of bytes in each piece"))
    pieces = models.TextField(
        unique=True,
        help_text=_("A concatenation of all 20-byte SHA1 hash values of the "
                    "torrent's pieces"))
    is_private = models.BooleanField(
        help_text=_("Whether or not the client may obtain peer data from "
                    "other sources (PEX, DHT)."))
    name = models.TextField(
        help_text=_("The suggested name of the torrent file, if single-file "
                    "torrent, otherwise, the suggest name of the directory "
                    "in which to put the files"))
    length = models.PositiveIntegerField(
        blank=True, null=True,
        help_text=_("Length of the file contents in bytes, missing for "
                    "multi-file torrents."))
    md5sum = models.CharField(
        blank=True, null=True, max_length=32,
        help_text=_("MD5 hash of the file contents (single-file torrent "
                    " only)."))
    files = JSONField(
        blank=True, null=True,
        help_text=_("A list of {name, length, md5sum} dicts corresponding to "
                    "the files tracked by the torrent"))

    def get_absolute_url(self):
        return reverse('torrents_torrent_download', args=[self.pk])

    @classmethod
    def from_torrent_file(cls, torrent_file, *args, **kwargs):
        torrent_dict = bencode.bdecode(torrent_file.read())
        return cls.from_torrent_dict(torrent_dict, *args, **kwargs)

    @classmethod
    def from_torrent_dict(cls, torrent_dict, *args, **kwargs):
        info_dict = torrent_dict[b'info']
        return cls(
            announce=torrent_dict[b'announce'],
            announce_list=torrent_dict.get(b'announce-list'),
            creation_date=torrent_dict.get(b'creation date'),
            created_by=torrent_dict.get(b'created by'),
            comment=torrent_dict.get(b'comment'),
            encoding=torrent_dict.get(b'encoding'),
            piece_length=info_dict.get(b'piece length'),
            pieces=binascii.hexlify(info_dict.get(b'pieces')),
            is_private=info_dict.get(b'private', 0) == 1,
            name=info_dict.get(b'name'),
            length=info_dict.get(b'length'),
            md5sum=info_dict.get(b'md5sum'),
            files=info_dict.get(b'files'))

    @property
    def is_single_file(self):
        return self.files is None or len(self.files) <= 1

    def as_bencoded_string(self, *args, **kwargs):
        torrent = {
            'announce': self.announce,
            'announce-list': self.announce_list,
            'creation date': self.creation_date,
            'comment': self.comment,
            'created by': self.created_by,
            'encoding': self.encoding,
        }

        torrent['info'] = info_dict = {
            'piece length': self.piece_length,
            'pieces': binascii.unhexlify(self.pieces),
            'private': int(self.is_private),
            'name': self.name
        }
        if self.is_single_file:
            info_dict['length'] = self.length
            info_dict['md5sum'] = self.md5sum
        else:
            info_dict['files'] = self.files

        return bencode.bencode(
            recursive_force_bytes(recursive_drop_falsy(torrent)))

    def __str__(self):
        return self.name


def recursive_drop_falsy(d):
    """Recursively drops falsy values from a given data structure."""
    if isinstance(d, dict):
        return dict((k, recursive_drop_falsy(v)) for k, v in d.items() if v)
    elif isinstance(d, list):
        return map(recursive_drop_falsy, d)
    elif isinstance(d, basestring):
        return force_bytes(d)
    else:
        return d


def recursive_force_bytes(d):
    """Recursively walks a given data structure and coerces all string-like
    values to :class:`bytes`."""
    if isinstance(d, dict):
        # Note(superbobry): 'bencode' forces us to use byte keys.
        return dict((force_bytes(k), recursive_force_bytes(v))
                    for k, v in d.items() if v)
    elif isinstance(d, list):
        return map(recursive_force_bytes, d)
    elif isinstance(d, basestring):
        return force_bytes(d)
    else:
        return d

########NEW FILE########
__FILENAME__ = local_settings
from __future__ import unicode_literals

import os.path

TEST_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'archlinux-2013.04.01-dual.iso.torrent')

########NEW FILE########
__FILENAME__ = test_fields
from __future__ import absolute_import, unicode_literals

from cStringIO import StringIO

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.core.files import File

from .local_settings import TEST_FILE_PATH
from ..fields import TorrentField


class TorrentFieldTests(TestCase):
    def test_empty(self):
        field = TorrentField()
        self.assertRaises(ValidationError, field.clean, False)

    def test_creates_torrent(self):
        torrent_file_raw = open(TEST_FILE_PATH, 'rb')
        torrent_data = torrent_file_raw.read()
        torrent_file_raw.seek(0)

        torrent_file = File(torrent_file_raw)
        field = TorrentField()
        torrent = field.clean(torrent_file)

        self.assertEquals(torrent_data, torrent.as_bencoded_string())

    def test_invalid_torrent(self):
        field = TorrentField()
        not_a_torrent = File(StringIO("this is clearly an invalid torrent"))
        not_a_torrent.name = "invalid.torrent"
        self.assertRaises(ValidationError, field.clean, not_a_torrent)

########NEW FILE########
__FILENAME__ = test_models
from __future__ import absolute_import, unicode_literals

import hashlib

from django.test import TestCase

from .local_settings import TEST_FILE_PATH
from ..models import Torrent


sha1 = lambda data: hashlib.sha1(data).hexdigest()


class TorrentTests(TestCase):
    def test_from_torrent_file(self):
        with open(TEST_FILE_PATH, 'rb') as test_file:
            torrent = Torrent.from_torrent_file(test_file)
            test_file.seek(0)
            orig_torrent_str = test_file.read()

        self.assertEquals(torrent.name, "archlinux-2013.04.01-dual.iso")
        self.assertEquals(torrent.as_bencoded_string(), orig_torrent_str)
        # note that the torrent file is slightly modified
        # I've removed the url-list dictionary element
        # since we have no support for that

    def test_to_torrent_singlefile(self):
        torrent = Torrent()
        torrent.name = "my.little.pwnie.zip"
        torrent.announce = "http://example.com/announce"
        torrent.piece_length = 32768
        torrent.pieces = "09bc090d67579eaed539c883b956d265a7975096"
        torrent.is_private = True
        torrent.length = 32768
        torrent_str = torrent.as_bencoded_string()  # this shouldn't throw
        self.assertEquals(
            sha1(torrent_str), b"4d9e46d46fcbd23d89c7e1366646a1ca7052a2bb")

    def test_to_torrent_singlefile_with_md5sum(self):
        torrent = Torrent()
        torrent.name = "my.little.pwnie.zip"
        torrent.announce = "http://example.com/announce"
        torrent.piece_length = 32768
        torrent.pieces = "09bc090d67579eaed539c883b956d265a7975096"
        torrent.is_private = True
        torrent.length = 32768
        torrent.md5sum = "0b784b963828308665f509173676bbcd"
        torrent_str = torrent.as_bencoded_string()  # this shouldn't throw
        self.assertEquals(
            sha1(torrent_str), b"fe1fcf4a3c635445d6f998b0fdfab652465099f0")

    def test_to_torrent_multifile(self):
        torrent = Torrent()
        torrent.name = "my.little.pwnies"
        torrent.announce = "http://example.com/announce"
        torrent.announce_list = [
            u'http://example.com/announce',
            u'http://backup1.example.com/announce'
        ]
        torrent.piece_length = 32768
        torrent.pieces = b"09bc090d67579eaed539c883b956d265a7975096"
        torrent.is_private = False
        torrent.length = None
        torrent.encoding = 'hex'
        torrent.files = [
            {
                'length': 235,
                'md5sum': b"0b784b963828308665f509173676bbcd",
                'path': ['dir1', 'dir2', 'file.ext'],
            },
            {
                'length': 435,
                'md5sum': b"784b0b963828308665f509173676bbcd",
                'path': ['moop.dir'],
            }
        ]
        torrent_str = torrent.as_bencoded_string()  # this shouldn't throw
        self.assertEquals(
            sha1(torrent_str), b"41c49ebb8d4aa7a977b9642da9512331a9abfe10")

    def test_torrent_unicode(self):
        torrent = Torrent()
        torrent.name = "hi"
        self.assertEquals(unicode(torrent), torrent.name)

    def test_absolute_url(self):
        # just poke it
        torrent = Torrent()
        torrent.id = 9
        torrent.get_absolute_url()

########NEW FILE########
__FILENAME__ = test_views
from __future__ import absolute_import, unicode_literals

from django.core.urlresolvers import reverse

from batter.test import LoggedInTestCase

from .local_settings import TEST_FILE_PATH
from ..models import Torrent


class UploadTorrentTests(LoggedInTestCase):
    def setUp(self):
        self.url = reverse("torrents_torrent_upload")
        super(UploadTorrentTests, self).setUp()

    def test_get(self):
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)

    def test_post_valid_torrent(self):
        with open(TEST_FILE_PATH, 'rb') as fp:
            response = self.client.post(self.url, {'torrent_file': fp})

        self.assertEquals(response.status_code, 302)
        self.assertEquals(Torrent.objects.count(), 1)

    def test_post_duplicate_torrent(self):
        with open(TEST_FILE_PATH, 'rb') as fp:
            self.client.post(self.url, {'torrent_file': fp})
            fp.seek(0)
            response = self.client.post(self.url, {'torrent_file': fp})

        self.assertEquals(response.status_code, 409)
        self.assertEquals(Torrent.objects.count(), 1)

    def test_logged_out(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 302)


class ViewTorrentTests(LoggedInTestCase):
    def setUp(self):
        with open(TEST_FILE_PATH, 'rb') as test_file:
            self.torrent = Torrent.from_torrent_file(test_file)

        self.torrent.save()
        self.torrent_url = reverse("torrents_torrent_view", kwargs={
            'pk': self.torrent.pk
        })
        super(ViewTorrentTests, self).setUp()

    def test_existing_torrent(self):
        response = self.client.get(self.torrent_url)
        self.assertEquals(response.status_code, 200)

    def test_nonexisting_torrent(self):
        response = self.client.get(reverse("torrents_torrent_view", kwargs={
            'pk': 42
        }))
        self.assertEquals(response.status_code, 404)


class DownloadTorrentTests(LoggedInTestCase):
    def setUp(self):
        with open(TEST_FILE_PATH, 'rb') as test_file:
            self.torrent = Torrent.from_torrent_file(test_file)
            self.torrent_size = test_file.tell()
            test_file.seek(0)
            self.raw_torrent = test_file.read()
        self.torrent.save()
        self.torrent_url = reverse("torrents_torrent_download",
                                   kwargs={'pk': self.torrent.pk})
        super(DownloadTorrentTests, self).setUp()

    def test_existing_torrent(self):
        response = self.client.get(self.torrent_url)
        self.assertEquals(
            int(response['Content-Length']),
            int(self.torrent_size)
        )
        self.assertEquals(
            response['Content-Disposition'],
            'attachment; filename=archlinux-20130401-dualiso.torrent'
        )
        self.assertEquals(response.content, self.raw_torrent)

    def test_nonexisting_torrent(self):
        response = self.client.get(reverse("torrents_torrent_download",
                                           kwargs={'pk': 42}))
        self.assertEquals(response.status_code, 404)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from .views import DownloadView, TorrentView

urlpatterns = patterns(
    '',
    url(r'(?P<pk>\d+)/$', TorrentView.as_view(),
        name="torrents_torrent_view"),
    url(r'upload/$', "torrents.views.upload_torrent",
        name="torrents_torrent_upload"),
    url(r'(?P<pk>\d+)/download/$', DownloadView.as_view(),
        name="torrents_torrent_download"),
)

########NEW FILE########
__FILENAME__ = views
from __future__ import absolute_import, unicode_literals

import cStringIO as StringIO

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template.defaultfilters import slugify
from django.views.generic.detail import DetailView

from .forms import TorrentUploadForm
from .models import Torrent


def upload_torrent(request):
    form = TorrentUploadForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        torrent = form.cleaned_data['torrent_file']
        try:
            torrent.save()
            return redirect(torrent)
        except Exception:
            resp = HttpResponse()
            resp.status_code = 409
            return resp

    return render(request, 'torrents/upload.html', {'form': form})


class TorrentView(DetailView):
    model = Torrent


class DownloadView(DetailView):
    model = Torrent

    def get(self, request, *args, **kwargs):
        torrent = self.get_object()
        torrent_file = StringIO.StringIO(torrent.as_bencoded_string())

        response = HttpResponse(
            torrent_file.read(), content_type='application/x-bittorrent')
        response['Content-Length'] = torrent_file.tell()
        response['Content-Disposition'] = \
            'attachment; filename={0}.torrent'.format(slugify(torrent.name))
        return response

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# batter documentation build configuration file, created by
# sphinx-quickstart on Sun Feb 17 11:46:20 2013.
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
project = u'batter'
copyright = u'2013, ChangeMyName'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = '0.1'

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
htmlhelp_basename = 'batterdoc'


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
  ('index', 'batter.tex', u'batter Documentation',
   u'ChangeToMyName', 'manual'),
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
    ('index', 'batter', u'batter Documentation',
     [u'ChangeToMyName'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'batter', u'batter Documentation',
   u'ChangeToMyName', 'batter', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
