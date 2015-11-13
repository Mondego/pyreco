__FILENAME__ = settings
# Django settings for db_mock project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        #'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'db_mock',                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': '',
        'PASSWORD': '',
        'HOST': '',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                      # Set to empty string for default.
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
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
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
SECRET_KEY = 'n(1(2v7i^8mjw=(s64)t!q^@1%0)q8e1c3vk0$0d2%)heh3l@@'

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

ROOT_URLCONF = 'db_mock.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'db_mock.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'music',

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

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'db_mock.views.home', name='home'),
    # url(r'^db_mock/', include('db_mock.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for db_mock project.

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
# os.environ["DJANGO_SETTINGS_MODULE"] = "db_mock.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "db_mock.settings")

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
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "db_mock.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = factories
import factory

from .models import RecordLabel, Artist, Album, Track


class RecordLabelFactory(factory.Factory):
    FACTORY_FOR = RecordLabel
    name = 'Circus Music'


class ArtistFactory(factory.Factory):
    FACTORY_FOR = Artist
    name = 'Freddy the Clown'


class AlbumFactory(factory.Factory):
    FACTORY_FOR = Album
    name = 'All time circus classics'
    label = factory.SubFactory(RecordLabelFactory)
    artist = factory.SubFactory(ArtistFactory)


class TrackFactory(factory.Factory):
    FACTORY_FOR = Track
    number = 1
    name = 'Tears of a Clown'
    album = factory.SubFactory(AlbumFactory)


########NEW FILE########
__FILENAME__ = models
from django.db import models


class RecordLabel(models.Model):
    name = models.CharField(max_length=255)


class Artist(models.Model):
    name = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name


class Fan(models.Model):
    name = models.CharField(max_length=255)
    artist = models.ForeignKey(Artist)
    friends = models.ManyToManyField('self', symmetrical=False)

    def __unicode__(self):
        return self.name


class Album(models.Model):
    name = models.CharField(max_length=255)
    artist = models.ForeignKey(Artist)
    label = models.ForeignKey(RecordLabel)


class Track(models.Model):
    number = models.PositiveIntegerField()
    name = models.CharField(max_length=255)
    album = models.ForeignKey(Album)
    artist = models.ForeignKey(Artist, blank=True, null=True)
    collaborators = models.ManyToManyField(Artist, blank=True, related_name='collaborations')

    def track_details(self):
        return {
            'number': self.number,
            'name': self.name,
            'album': self.album.name,
            'artist': self.artist.name if self.artist else self.album.artist.name,
            'collaborators': [artist.name for artist in self.collaborators.all()],
            'label': self.album.label.name,
        }


########NEW FILE########
__FILENAME__ = tests
import time
import unittest

from django.test import TestCase
import mock

from test_db import QuerySet, data_store, get_related_queryset, add_items, clear_items, remove_items
from .factories import ArtistFactory, TrackFactory
from .models import RecordLabel, Artist, Fan, Album, Track


cursor_wrapper = mock.Mock()
cursor_wrapper.side_effect = RuntimeError("No touching the database!")
no_db_tests = mock.patch("django.db.backends.util.CursorWrapper", cursor_wrapper)


correct_details = {
    'number': 1,
    'name': 'Tears of a Clown',
    'album': 'All time circus classics',
    'artist': 'Freddy the Clown',
    'collaborators': ['Buttercup'],
    'label': 'Circus Music',
}


class TrackUnicodeTests(TestCase):
    def test_naive(self):
        with self.assertNumQueries(8):
            label = RecordLabel.objects.create(name='Circus Music')
            artist = Artist.objects.create(name='Freddy the Clown')
            album = Album.objects.create(name='All time circus classics', label=label, artist=artist)
            track = Track.objects.create(number=1, name='Tears of a Clown', album=album)
            other_artist = Artist.objects.create(name='Buttercup')
            track.collaborators.add(other_artist)
            self.assertEqual(track.track_details(), correct_details)

    def test_factories(self):
        with self.assertNumQueries(8):
            track = TrackFactory.create(number=1)
            other_artist = ArtistFactory(name='Buttercup')
            track.collaborators.add(other_artist)
            self.assertEqual(track.track_details(), correct_details)

    def test_factories_build_m2m_problem(self):
        with self.assertNumQueries(4):
            track = TrackFactory.build()
            track.pk = 1
            other_artist = ArtistFactory.create(name='Buttercup')
            track.collaborators.add(other_artist)
            self.assertEqual(track.track_details(), correct_details)

    def test_factories_build_prefetch(self):
        # this one will get even better/easier with #17001
        with self.assertNumQueries(0):
            track = TrackFactory.build()
            track.pk = 1
            other_artist = ArtistFactory.build(name='Buttercup')
            collaborators = track.collaborators.all()
            collaborators._result_cache = [other_artist]
            track._prefetched_objects_cache = {'collaborators': collaborators}
            self.assertEqual(track.track_details(), correct_details)

    def test_factories_build_mock(self):
        with self.assertNumQueries(0):
            other_artist = ArtistFactory.build(name='Buttercup')
            collaborators_mock = mock.MagicMock()
            collaborators_mock.all.return_value = [other_artist]
            with mock.patch('music.factories.Track.collaborators', collaborators_mock):
                track = TrackFactory.build()
                track.pk = 1
                self.assertEqual(track.track_details(), correct_details)

    @no_db_tests
    @mock.patch.object(RecordLabel.objects, 'get_queryset', lambda: QuerySet(RecordLabel))
    @mock.patch.object(Artist.objects, 'get_queryset', lambda: QuerySet(Artist))
    @mock.patch.object(Album.objects, 'get_queryset', lambda: QuerySet(Album))
    @mock.patch.object(Track.objects, 'get_queryset', lambda: QuerySet(Track))
    @mock.patch.object(Artist.collaborations.related_manager_cls, 'get_queryset', lambda instance: QuerySet(Artist))
    @mock.patch.object(Track.collaborators.related_manager_cls, 'get_queryset', get_related_queryset)
    @mock.patch.object(Track.collaborators.related_manager_cls, '_add_items', add_items)
    def test_using_test_db(self):
        # Exactly the same code as the naive version
        with self.assertNumQueries(0):
            label = RecordLabel.objects.create(name='Circus Music')
            artist = Artist.objects.create(name='Freddy the Clown')
            album = Album.objects.create(name='All time circus classics', label=label, artist=artist)
            track = Track.objects.create(number=1, name='Tears of a Clown', album=album)
            other_artist = Artist.objects.create(name='Buttercup')
            track.collaborators.add(other_artist)
            self.assertEqual(track.track_details(), correct_details)
        data_store.clear()

    @unittest.skip('Skip!')
    def test_performance_difference(self):
        for test in [self.test_naive, self.test_factories, self.test_factories_build_prefetch, self.test_factories_build_mock, self.test_using_test_db]:
            start = time.time()
            for i in range(1000):
                test()
            elapsed = (time.time() - start)
            print test.__name__, elapsed


@no_db_tests
@mock.patch.object(Artist.objects, 'get_queryset', lambda: QuerySet(Artist))
class MemoryManagerSingleModelTests(TestCase):
    def tearDown(self):
        # clear out the data store
        data_store.clear()

    def test_create(self):
        artist = Artist.objects.create(name='Bob')
        self.assertEqual(Artist.objects.get_queryset().query.data_store, [artist])
        self.assertEqual(artist.pk, 1)
        self.assertEqual(artist.id, 1)

    def test_all(self):
        artist = Artist.objects.create(name='Bob')
        artists = Artist.objects.all()
        self.assertSequenceEqual(artists, [artist])
        self.assertTrue(artist is artists[0])

    def test_get(self):
        artist = Artist.objects.create(name='Bob')
        loaded = Artist.objects.get()
        self.assertTrue(artist is loaded)

    def test_get_multiple_objects(self):
        Artist.objects.create(name='Bob')
        Artist.objects.create(name='Bob the second')
        with self.assertRaises(Artist.MultipleObjectsReturned):
            Artist.objects.get()

    def test_get_no_objects(self):
        with self.assertRaises(Artist.DoesNotExist):
            Artist.objects.get()

    def test_filter(self):
        bob = Artist.objects.create(name='Bob')
        Artist.objects.create(name='Bob the second')
        artists = Artist.objects.filter(name='Bob')
        self.assertSequenceEqual(artists, [bob])

    def test_multi_filter(self):
        bob = Artist.objects.create(name='Bob')
        bob2 = Artist.objects.create(name='Bob')
        self.assertEqual(bob.pk, 1)
        self.assertEqual(bob2.pk, 2)
        artists = Artist.objects.filter(name='Bob', pk=2)
        self.assertSequenceEqual(artists, [bob2])

    def test_simple_exclude(self):
        Artist.objects.create(name='Bob')
        bob2 = Artist.objects.create(name='Bob the second')
        artists = Artist.objects.exclude(name='Bob')
        self.assertSequenceEqual(artists, [bob2])

    def test_filter_and_exclude(self):
        bob = Artist.objects.create(name='Bob')
        bob2 = Artist.objects.create(name='Bob')
        self.assertEqual(bob.pk, 1)
        self.assertEqual(bob2.pk, 2)
        artists = Artist.objects.filter(name='Bob').exclude(pk=1)
        self.assertSequenceEqual(artists, [bob2])

    def test_filter_exact(self):
        bob = Artist.objects.create(name='Bob')
        Artist.objects.create(name='Bob the second')
        artists = Artist.objects.filter(name__exact='Bob')
        self.assertSequenceEqual(artists, [bob])

    def test_count(self):
        Artist.objects.create(name='Bob')
        count = Artist.objects.count()
        self.assertEqual(count, 1)

    def test_slice(self):
        bob1 = Artist.objects.create(name='Bob1')
        bob2 = Artist.objects.create(name='Bob2')
        bob3 = Artist.objects.create(name='Bob3')
        self.assertSequenceEqual(Artist.objects.all()[:2], [bob1, bob2])
        self.assertSequenceEqual(Artist.objects.all()[1:2], [bob2])
        self.assertSequenceEqual(Artist.objects.all()[1:], [bob2, bob3])
        self.assertSequenceEqual(Artist.objects.all()[::2], [bob1, bob3])

    def test_get_or_create(self):
        artist, created = Artist.objects.get_or_create(name='Bob')
        self.assertTrue(created)
        artist, created = Artist.objects.get_or_create(name='Bob')
        self.assertFalse(created)
        self.assertEqual(Artist.objects.count(), 1)

    def test_delete(self):
        Artist.objects.create(name='Bob')
        Artist.objects.all().delete()
        self.assertEqual(Artist.objects.count(), 0)

    def test_delete_with_filter(self):
        Artist.objects.create(name='Bob')
        Artist.objects.create(name='Dave')
        Artist.objects.filter(name='Dave').delete()
        self.assertEqual(Artist.objects.count(), 1)

    def test_exists(self):
        Artist.objects.create(name='Bob')
        self.assertTrue(Artist.objects.exists())

    def test_update(self):
        Artist.objects.create(name='Bob')
        updated = Artist.objects.update(name='Dave')
        self.assertEqual(Artist.objects.get().name, 'Dave')
        self.assertEqual(updated, 1)

    def test_none(self):
        self.assertSequenceEqual(Artist.objects.none(), [])

    def test_order_by(self):
        bob = Artist.objects.create(name='Bob')
        adam = Artist.objects.create(name='Adam')
        by_pk = Artist.objects.order_by('pk')
        by_name = Artist.objects.order_by('name')
        self.assertSequenceEqual(by_pk, [bob, adam])
        self.assertSequenceEqual(by_name, [adam, bob])

    def test_complex_order_by(self):
        bob = Artist.objects.create(name='Bob')
        bob2 = Artist.objects.create(name='Bob')
        adam = Artist.objects.create(name='Adam')
        ordered = Artist.objects.order_by('name', '-pk')
        self.assertSequenceEqual(ordered, [adam, bob2, bob])

    def test_contains_lookup(self):
        bob = Artist.objects.create(name='Bob')
        bobby = Artist.objects.create(name='Bobby')
        Artist.objects.create(name='Adam')
        self.assertSequenceEqual(Artist.objects.filter(name__contains='ob'), [bob, bobby])

    def test_in_lookup(self):
        bob = Artist.objects.create(name='Bob')
        bobby = Artist.objects.create(name='Bobby')
        Artist.objects.create(name='Adam')
        self.assertSequenceEqual(Artist.objects.filter(name__in=['Bob', 'Bobby', 'Fred']), [bob, bobby])

    def test_iexact_lookup(self):
        bob = Artist.objects.create(name='Bob')
        Artist.objects.create(name='Adam')
        self.assertSequenceEqual(Artist.objects.filter(name__iexact='bob'), [bob])

    def test_icontains_lookup(self):
        bob = Artist.objects.create(name='Bob')
        bobby = Artist.objects.create(name='Bobby')
        Artist.objects.create(name='Adam')
        self.assertSequenceEqual(Artist.objects.filter(name__icontains='bo'), [bob, bobby])

    def test_save_existing_object(self):
        bob = Artist.objects.create(name='Bob')
        bob.name = 'bob'
        bob.save()
        self.assertSequenceEqual(Artist.objects.all(), [bob])

    @unittest.expectedFailure
    def test_save_new_object(self):
        # This is difficult to implement - it never hits the queryset.
        bob = Artist(name='Bob')
        bob.save()
        self.assertSequenceEqual(Artist.objects.all(), [bob])

    @unittest.expectedFailure
    def test_delete_object(self):
        # This is difficult to implement - it never hits the queryset.
        bob = Artist.objects.create(name='Bob')
        bob.delete()
        self.assertSequenceEqual(Artist.objects.all(), [])


@no_db_tests
@mock.patch.object(Fan.objects, 'get_queryset', lambda: QuerySet(Fan))
@mock.patch.object(Fan.artist, 'get_queryset', lambda instance: QuerySet(Artist))
@mock.patch.object(Artist.objects, 'get_queryset', lambda: QuerySet(Artist))
@mock.patch.object(Artist.fan_set.related_manager_cls, 'get_queryset', get_related_queryset)
@mock.patch.object(Fan.fan_set.related_manager_cls, 'get_queryset', lambda instance: QuerySet(Fan))
@mock.patch.object(Fan.friends.related_manager_cls, 'get_queryset', get_related_queryset)
@mock.patch.object(Fan.friends.related_manager_cls, '_add_items', add_items)
@mock.patch.object(Fan.friends.related_manager_cls, '_remove_items', remove_items)
@mock.patch.object(Fan.friends.related_manager_cls, '_clear_items', clear_items)
class MemoryManagerFKTests(TestCase):
    def tearDown(self):
        # clear out the data store
        data_store.clear()

    def test_creating_with_fk(self):
        artist = Artist.objects.create(name='Bob')
        Fan.objects.create(name='Annie', artist=artist)
        self.assertEqual(Fan.objects.get().artist, artist)

    def test_creating_with_id(self):
        artist = Artist.objects.create(name='Bob')
        Fan.objects.create(name='Annie', artist_id = artist.pk)
        self.assertEqual(Fan.objects.get().artist, artist)

    def test_reverse_lookup(self):
        artist = Artist.objects.create(name='Bob')
        fan = Fan.objects.create(name='Annie', artist=artist)
        self.assertSequenceEqual(artist.fan_set.all(), [fan])

    def test_reverse_lookup_multiple_objects(self):
        bob = Artist.objects.create(name='Bob')
        annie = Fan.objects.create(name='Annie', artist=bob)
        dave = Artist.objects.create(name='Dave')
        Fan.objects.create(name='Lottie', artist=dave)
        self.assertSequenceEqual(bob.fan_set.all(), [annie])

    def test_lookups_passed_through(self):
        bob = Artist.objects.create(name='Bob')
        annie = Fan.objects.create(name='Annie', artist=bob)
        dave = Artist.objects.create(name='Dave')
        Fan.objects.create(name='Lottie', artist=dave)
        self.assertSequenceEqual(Fan.objects.filter(artist__name='Bob'), [annie])

    def test_m2m_get_empty(self):
        bob = Artist.objects.create(name='Bob')
        annie = Fan.objects.create(name='Annie', artist=bob)
        self.assertSequenceEqual(annie.friends.all(), [])

    def test_m2m_create(self):
        bob = Artist.objects.create(name='Bob')
        annie = Fan.objects.create(name='Annie', artist=bob)
        lottie = annie.friends.create(name='Lottie', artist=bob)
        self.assertSequenceEqual(annie.friends.all(), [lottie])
        self.assertSequenceEqual(Fan.objects.all(), [annie, lottie])

    def test_m2m_add(self):
        bob = Artist.objects.create(name='Bob')
        annie = Fan.objects.create(name='Annie', artist=bob)
        lottie = Fan.objects.create(name='Lottie', artist=bob)
        annie.friends.add(lottie)
        self.assertSequenceEqual(annie.friends.all(), [lottie])

    def test_m2m_set(self):
        bob = Artist.objects.create(name='Bob')
        annie = Fan.objects.create(name='Annie', artist=bob)
        lottie = Fan.objects.create(name='Lottie', artist=bob)
        annie.friends = [lottie]
        self.assertSequenceEqual(annie.friends.all(), [lottie])
        annie.friends = []
        self.assertSequenceEqual(annie.friends.all(), [])

    def test_m2m_remove(self):
        bob = Artist.objects.create(name='Bob')
        annie = Fan.objects.create(name='Annie', artist=bob)
        lottie = Fan.objects.create(name='Lottie', artist=bob)
        annie.friends = [lottie]
        self.assertSequenceEqual(annie.friends.all(), [lottie])
        annie.friends.remove(lottie)
        self.assertSequenceEqual(annie.friends.all(), [])


########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = test_db
from django.db.models.constants import LOOKUP_SEP
from django.db.models.query import QuerySet as DjangoQuerySet
from django.utils.tree import Node


data_store = {}


class Query(object):
    """A replacement for Django's sql.Query object.

    Shares a similar API to django.db.models.sql.Query. It has its own data store.
    """
    def __init__(self, model, where=None):
        self.model = model
        data_store.setdefault(model, [])
        self.data_store = data_store[model]
        self.counter = len(self.data_store) + 1
        self.high_mark = None
        self.low_mark = 0
        self.where = []
        self.ordering = None
        self._empty = False

    def execute(self):
        """Execute a query against the data store.

        Work on a copy of the list so we don't accidentally change the store.
        """
        data = self.data_store[:]
        for func in self.where:
            data = filter(func, data)
        if self.ordering:
            data = sorted(data, cmp=self.ordering)
        if self.low_mark and not self.high_mark:
            data = data[self.low_mark:]
        elif self.high_mark:
            data = data[self.low_mark:self.high_mark]
        return data

    def clone(self, *args, **kwargs):
        """Trivial clone method."""
        return self

    def assign_pk(self, obj):
        """Simple counter based "primary key" allocation."""
        obj.pk = self.counter
        self.counter += 1

    def create(self, obj):
        """Creates an object by adding it to the data store.

        Will allocate a PK if one does not exist, but currently does nothing to
        ensure uniqueness of your PKs if you've set one already.
        """
        if not obj.pk:
            self.assign_pk(obj)
        self.data_store.append(obj)

    def delete(self):
        """Removes objects from the data store."""
        items = self.execute()
        for item in items:
            self.data_store.remove(item)

    def update(self, **kwargs):
        """Updates the objects in the data store.

        The correct values may well already have been assigned, espically if
        this triggered by instance.save() rather than queryset.update(), but
        we'll do it again anyway just to be sure.

        Should models be faffing with setattr then this is likely to break
        things.
        """
        data = self.execute()
        for instance in data:
            for key, value in kwargs.items():
                setattr(instance, key, value)
        return len(data)

    def has_results(self, using=None):
        """Find out whether there's anything that matches the current query state."""
        return bool(self.execute())

    def get_count(self, using=None):
        """Find how many objects match the current query state."""
        return len(self.execute())

    def set_limits(self, low=None, high=None):
        """Set limits for query slicing.

        This code is almost identical to Django's code."""
        if high is not None:
            if self.high_mark is not None:
                self.high_mark = min(self.high_mark, self.low_mark + high)
            else:
                self.high_mark = self.low_mark + high
        if low is not None:
            if self.high_mark is not None:
                self.low_mark = min(self.high_mark, self.low_mark + low)
            else:
                self.low_mark = self.low_mark + low

    def can_filter(self):
        """Yeah, we can always filter. Even if Django can't.

        This is probably lies actually, filter + slice is likely broken/weird."""
        return True

    def clear_ordering(self, force_empty=False):
        self.ordering = None

    def set_empty(self):
        self._empty = True

    def is_empty(self):
        return self._empty

    def add_ordering(self, *fields):
        """Create a compare function we can pass to `sorted` when we execute
        the query."""

        def compare(x, y):
            for field in fields:
                reverse = field.startswith('-')
                if reverse:
                    field = field[1:]
                current = cmp(getattr(x, field), getattr(y, field))
                if current is not 0:
                    if reverse:
                        return -current
                    return current
            return 0

        self.ordering = compare

    def add_q(self, q_object):
        """Add filter functions to be used in execute."""
        for child in q_object.children:
            if isinstance(child, Node):
                self.add_q(child)
            else:
                self.where.append(self._get_filter_func(*child, negated=q_object.negated))

    def _get_filter_func(self, key, value, negated=False):
        func = None
        if LOOKUP_SEP in key:
            # This is horribly naive
            key, lookup = key.split(LOOKUP_SEP, 1)
            if lookup == 'exact':
                pass
            elif lookup == 'iexact':
                func = lambda o: value.lower() == getattr(o, key).lower()
            elif lookup == 'contains':
                func = lambda o: value in getattr(o, key)
            elif lookup == 'icontains':
                func = lambda o: value.lower() in getattr(o, key).lower()
            elif lookup == 'in':
                func = lambda o: getattr(o, key) in value
            else:
                next_level_func = self._get_filter_func(lookup, value)
                func = lambda o: next_level_func(getattr(o, key))
        # FIXME: blatantly broken
        if key == 'fan' or key == 'collaborations':
            def func(o):
                try:
                    store = data_store[(self.model, key)]
                except KeyError:
                    return False
                try:
                    list = store[value]
                except KeyError:
                    return False
                return o in list
        if not func:
            func = lambda o: getattr(o, key) == value
        if negated:
            return lambda o: not func(o)
        return func


class QuerySet(DjangoQuerySet):
    """Subclass of Django's QuerySet to simplify some methods.
    
    Generally speaking we try to use Django's qs for most methods, but some
    things are rather more complex than they need to be for our use cases.
    Consequently we simplify the execution functions to just call our Query
    object in a more simple fashion.
    """
    def __init__(self, model=None, query=None, using=None, instance=None):
        query = query or Query(model)
        super(QuerySet, self).__init__(model=model, query=query, using=None)

    def create(self, **kwargs):
        obj = self.model(**kwargs)
        self.query.create(obj)
        return obj

    def get_or_create(self, **kwargs):
        try:
            return self.get(**kwargs), False
        except self.model.DoesNotExist:
            return self.create(**kwargs), True

    def delete(self):
        self.query.delete()

    def update(self, **kwargs):
        return self.query.update(**kwargs)

    def _update(self, values):
        return True

    def iterator(self):
        return iter(self.query.execute())


def get_related_queryset(self):
    """Related querysets are defined funny."""
    return QuerySet(self.model).filter(**self.core_filters)


def add_items(self, source_field_name, target_field_name, *objs):
    """Descriptor method we can attach to the generated RelatedObjectQuerySets."""
    data_store.setdefault((self.model, self.query_field_name), {})
    store = data_store[(self.model, self.query_field_name)]
    store.setdefault(self.instance.id, [])
    store[self.instance.id] += objs


def remove_items(self, source_field_name, target_field_name, *objs):
    """Descriptor method we can attach to the generated RelatedObjectQuerySets."""
    data_store.setdefault((self.model, self.query_field_name), {})
    store = data_store[(self.model, self.query_field_name)]
    store.setdefault(self.instance.id, [])
    for o in objs:
        store[self.instance.id].remove(o)


def clear_items(self, source_field_name):
    """Descriptor method we can attach to the generated RelatedObjectQuerySets."""
    data_store[(self.model, self.query_field_name)] = {}

########NEW FILE########
