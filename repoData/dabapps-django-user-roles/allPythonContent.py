__FILENAME__ = manage
#!/usr/bin/env python
import os, sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testproject.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': os.path.join(PROJECT_DIR, 'sqlite3.db'),                      # Or path to database file if using sqlite3.
        'NAME': os.path.join(PROJECT_DIR, 'database/sqlite3.db'),   # Or path to database file if using sqlite3.
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
STATIC_ROOT = ''

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
SECRET_KEY = 'nakhgsa+jf2bk(^g$#v(j21d^s#=h4m*4+e7x8&amp;#_t^3v6emt#'

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

ROOT_URLCONF = 'testproject.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'testproject.wsgi.application'

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
    'userroles',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url


# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'testproject.views.home', name='home'),
    # url(r'^testproject/', include('testproject.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for testproject project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testproject.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = decorators
from django.contrib.auth.decorators import user_passes_test
from userroles.models import UserRole

def role_required(*roles):
    """
    Decorator for views that checks whether a user has a particular role,
    redirecting to the log-in page if neccesary.
    Follows same style as django.contrib.auth.decorators.login_required,
    and django.contrib.auth.decorators.permission_required.
    """
    def check_role(user):
        try:
            return getattr(user, 'role', None) in roles
        except UserRole.DoesNotExist:
            return False
    return user_passes_test(check_role)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'UserRole'
        db.create_table('userroles_userrole', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='role', unique=True, to=orm['auth.User'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('child', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
        ))
        db.send_create_signal('userroles', ['UserRole'])


    def backwards(self, orm):
        
        # Deleting model 'UserRole'
        db.delete_table('userroles_userrole')


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
        'userroles.userrole': {
            'Meta': {'object_name': 'UserRole'},
            'child': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'role'", 'unique': 'True', 'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['userroles']

########NEW FILE########
__FILENAME__ = models
from django.contrib.auth.models import User
from django.db import models
from userroles import roles


class UserRole(models.Model):
    user = models.OneToOneField(User, related_name='role')
    name = models.CharField(max_length=100, choices=roles.choices)
    child = models.CharField(max_length=100, blank=True)
    _valid_roles = roles

    @property
    def profile(self):
        if not self.child:
            return None
        return getattr(self, self.child)

    def __eq__(self, other):
        return self.name == other.name

    def __getattr__(self, name):
        if name.startswith('is_'):
            role = getattr(self._valid_roles, name[3:], None)
            if role:
                return self == role

        raise AttributeError("'%s' object has no attribute '%s'" %
                              (self.__class__.__name__, name))

    def __unicode__(self):
        return self.name


def set_user_role(user, role, profile=None):
    if profile:
        try:
            UserRole.objects.get(user=user).delete()
        except UserRole.DoesNotExist:
            pass
        profile.user = user
        profile.name = role.name
        profile.child = str(profile.__class__.__name__).lower()

    else:
        try:
            profile = UserRole.objects.get(user=user)
        except UserRole.DoesNotExist:
            profile = UserRole(user=user, name=role.name)
        else:
            profile.name = role.name

    profile.save()

########NEW FILE########
__FILENAME__ = models
from django.db import models
from userroles.models import UserRole


class TestModeratorProfile(UserRole):
    stars = models.IntegerField()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns

urlpatterns = patterns('userroles.testapp.views',
    (r'^manager_or_moderator$', 'manager_or_moderator'),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse
from userroles.tests import roles
from userroles.decorators import role_required

# Note that we play nicely with project we're installed into, by using our
# custom test roles ('userroles.tests.roles'), rather than the default global
# roles, loaded from the project settings ('userroles.roles').


@role_required(roles.manager, roles.moderator)
def manager_or_moderator(request):
    """
    View to test the @role_required decorator.
    """
    return HttpResponse('ok')

########NEW FILE########
__FILENAME__ = tests
"""
"""

from django.conf import settings
from django.contrib.auth.models import User
from milkman.dairy import milkman
from userroles.models import set_user_role, UserRole
from userroles.testapp.models import TestModeratorProfile
from userroles.utils import SettingsTestCase
from userroles import Roles

# Test setup

roles_config = (
    'manager',
    'moderator',
    'client',
)

installed_apps_config = list(settings.INSTALLED_APPS)
installed_apps_config.append('userroles.testapp')

roles = Roles(roles_config)


class TestCase(SettingsTestCase):
    def setUp(self):
        super(TestCase, self).setUp()
        self.settings(
            INSTALLED_APPS=installed_apps_config,
            ROOT_URLCONF='userroles.testapp.urls',
            USER_ROLES=roles_config
        )
        self.restore_roles = UserRole._valid_roles
        UserRole._valid_roles = roles

    def tearDown(self):
        UserRole._valid_roles = self.restore_roles


class DummyClass(object):
    pass


# Basic user role tests

class RoleTests(TestCase):
    """
    Test operations on role object.
    """

    def test_existing_role_propery(self):
        """
        Ensure that we can get a valid role.
        """
        self.assertTrue(roles.manager)

    def test_non_existing_role_propery(self):
        """
        Ensure that trying to get an invalid role raises an attribute error.
        """
        self.assertRaises(AttributeError, getattr, roles, 'foobar')


class UserRoleTests(TestCase):
    """
    Test basic user.role operations.
    """

    def setUp(self):
        super(UserRoleTests, self).setUp()
        self.user = milkman.deliver(User)
        set_user_role(self.user, roles.manager)

    def test_role_comparison(self):
        """
        Ensure that we can test if a user role has a given value.
        """
        self.assertEquals(self.user.role, roles.manager)

    def test_role_in_set(self):
        """
        Ensure that we can test if a user role exists in a given set.
        """
        self.assertIn(self.user.role, (roles.manager,))

    def test_is_role(self):
        """
        Test `user.role.is_something` style.
        """
        self.assertTrue(self.user.role.is_manager)

    def test_is_not_role(self):
        """
        Test `user.role.is_not_something` style.
        """
        self.assertFalse(self.user.role.is_moderator)

    def test_is_invalid_role(self):
        """
        Test `user.role.is_invalid` raises an AttributeError.
        """
        self.assertRaises(AttributeError, getattr, self.user.role, 'is_foobar')

    def test_set_role_without_profile(self):
        """
        Set a role that does not take a profile.
        """
        set_user_role(self.user, roles.client)
        self.assertTrue(self.user.role.is_client)

    def test_set_role_with_profile(self):
        """
        Set a role that takes a profile.
        """
        set_user_role(self.user, roles.moderator, TestModeratorProfile(stars=5))
        self.assertTrue(self.user.role.is_moderator)
        self.assertEquals(self.user.role.profile.stars, 5)

    # def test_set_role_without_profile_incorrectly(self):
    #     """
    #     Attempt to set a profile on a role that does not take a profile.
    #     """
    #     args = (self.user, roles.client, ModeratorProfile())
    #     self.assertRaises(ValueError, set_user_role, *args)

    # def test_set_role_with_profile_incorrectly(self):
    #     """
    #     Attempt to set a role that uses profiles, without setting a profile.
    #     """
    #     args = (self.user, roles.moderator, )
    #     self.assertRaises(ValueError, set_user_role, *args)

    # def test_set_role_with_profile_using_wrong_profile(self):
    #     """
    #     Attempt to set a role that uses profiles, without setting a profile.
    #     """
    #     args = (self.user, roles.moderator, DummyClass())
    #     self.assertRaises(ValueError, set_user_role, *args)


# Tests for user role view decorators

class ViewTests(TestCase):
    def setUp(self):
        super(ViewTests, self).setUp()
        self.user = milkman.deliver(User)
        self.user.set_password('password')
        self.user.save()
        self.client.login(username=self.user.username, password='password')

    def test_get_allowed_view(self):
        set_user_role(self.user, roles.manager)
        resp = self.client.get('/manager_or_moderator')
        self.assertEquals(resp.status_code, 200)

    def test_get_disallowed_view(self):
        set_user_role(self.user, roles.client)
        resp = self.client.get('/manager_or_moderator')
        self.assertEquals(resp.status_code, 302)


# Tests for using a custom UserRole class

# class UserRoleClassSettingTests(TestCase):
#     def setUp(self):
#         super(UserRoleClassSettingTests, self).setUp()
#         self.user = milkman.deliver(User)
#         set_user_role(self.user, roles.moderator)

#     def test_role_has_custom_property(self):
#         self.assertTrue(self.user.role.can_moderate_discussions)

########NEW FILE########
__FILENAME__ = utils
# http://djangosnippets.org/snippets/1011/
# Note: If we move to Django 1.4, we can use proper test settings instead.

from django.conf import settings
from django.db.models import loading
from django.test import TestCase
from django.core.management.commands import syncdb

NO_SETTING = ('!', None)


class TestSettingsManager(object):
    """
    A class which can modify some Django settings temporarily for a
    test and then revert them to their original values later.

    Automatically handles resyncing the DB if INSTALLED_APPS is
    modified.
    """
    def __init__(self):
        self._original_settings = {}

    def set(self, **kwargs):
        for k, v in kwargs.iteritems():
            self._original_settings.setdefault(k, getattr(settings, k,
                                                          NO_SETTING))
            setattr(settings, k, v)
        if 'INSTALLED_APPS' in kwargs:
            self.syncdb()

    def syncdb(self):
        loading.cache.loaded = False
        # Use this, rather than call_command, or 'south' will screw with us.
        syncdb.Command().execute(verbosity=0)

    def revert(self):
        for k, v in self._original_settings.iteritems():
            if v == NO_SETTING:
                delattr(settings, k)
            else:
                setattr(settings, k, v)
        if 'INSTALLED_APPS' in self._original_settings:
            self.syncdb()
        self._original_settings = {}


class SettingsTestCase(TestCase):
    """
    A subclass of the Django TestCase with a settings_manager
    attribute which is an instance of TestSettingsManager.

    Comes with a tearDown() method that calls
    self.settings_manager.revert().
    """
    def __init__(self, *args, **kwargs):
        super(SettingsTestCase, self).__init__(*args, **kwargs)
        self.settings_manager = TestSettingsManager()

    def tearDown(self):
        self.settings_manager.revert()

    def settings(self, **kwargs):
        self.settings_manager.set(**kwargs)

########NEW FILE########
