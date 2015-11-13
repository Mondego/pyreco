__FILENAME__ = cache
from django.core.cache import cache
from django.utils.encoding import smart_str
import inspect


# Check if the cache backend supports min_compress_len. If so, add it.
if 'min_compress_len' in inspect.getargspec(cache._cache.add)[0] and \
   'min_compress_len' in inspect.getargspec(cache._cache.set)[0]:
    class CacheClass(cache.__class__):
        def add(self, key, value, timeout=None, min_compress_len=150000):
            if isinstance(value, unicode):
                value = value.encode('utf-8')
            # Allow infinite timeouts
            if timeout is None:
                timeout = self.default_timeout
            return self._cache.add(smart_str(key), value, timeout, min_compress_len)
        
        def set(self, key, value, timeout=None, min_compress_len=150000):
            if isinstance(value, unicode):
                value = value.encode('utf-8')
            if timeout is None:
                timeout = self.default_timeout
            self._cache.set(smart_str(key), value, timeout, min_compress_len)

    cache.__class__ = CacheClass

########NEW FILE########
__FILENAME__ = fields
import functools
from django.db.models.fields.related import ManyToManyField, ReverseManyRelatedObjectsDescriptor, ManyRelatedObjectsDescriptor
from django.db.models.query import QuerySet
from django.db.models import signals
from cache import cache
from types import MethodType

CACHE_DURATION = 60 * 30

def invalidate_cache(obj, field):
    cache.set(obj._get_cache_key(field=field), None, 5)

def fix_where(where, modified=False):
    def wrap_add(f):
        @functools.wraps(f)
        def add(self, *args, **kwargs):
            """
            Wraps django.db.models.sql.where.add to indicate that a new
            'where' condition has been added.
            """
            self.modified = True
            return f(*args, **kwargs)
        return add
    where.modified = modified
    where.add = MethodType(wrap_add(where.add), where, where.__class__)
    return where


def get_pk_list_query_set(superclass):
    class PKListQuerySet(superclass):
        """
        QuerySet that, when unfiltered, fetches objects individually from
        the datastore by pk.

        The `pk_list` attribute is a list of primary keys for objects that
        should be fetched.

        """
        def __init__(self, pk_list=[], from_cache=False, *args, **kwargs):
            super(PKListQuerySet, self).__init__(*args, **kwargs)
            self.pk_list = pk_list
            self.from_cache = from_cache
            self.query.where = fix_where(self.query.where)

        def iterator(self):
            if not self.query.where.modified:
                for pk in self.pk_list:
                    yield self.model._default_manager.get(pk=pk)
            else:
                superiter = super(PKListQuerySet, self).iterator()
                while True:
                    yield superiter.next()

        def _clone(self, *args, **kwargs):
            c = super(PKListQuerySet, self)._clone(*args, **kwargs)
            c.query.where = fix_where(c.query.where, modified=self.query.where.modified)
            c.pk_list = self.pk_list
            c.from_cache = self.from_cache
            return c
    return PKListQuerySet


def get_caching_related_manager(superclass, instance, field_name, related_name):
    class CachingRelatedManager(superclass):
        def all(self):
            key = instance._get_cache_key(field=field_name)
            qs = super(CachingRelatedManager, self).get_query_set()
            PKListQuerySet = get_pk_list_query_set(qs.__class__)
            qs = qs._clone(klass=PKListQuerySet)
            pk_list = cache.get(key)
            if pk_list is None:
                pk_list = qs.values_list('pk', flat=True)
                cache.add(key, list(pk_list), CACHE_DURATION)
            else:
                qs.from_cache = True
            qs.pk_list = pk_list
            return qs

        def add(self, *objs):
            super(CachingRelatedManager, self).add(*objs)
            for obj in objs:
                invalidate_cache(obj, related_name)
            invalidate_cache(instance, field_name)

        def remove(self, *objs):
            super(CachingRelatedManager, self).remove(*objs)
            for obj in objs:
                invalidate_cache(obj, related_name)
            invalidate_cache(instance, field_name)

        def clear(self):
            objs = list(self.all())
            super(CachingRelatedManager, self).clear()
            for obj in objs:
                invalidate_cache(obj, related_name)
            invalidate_cache(instance, field_name)
    return CachingRelatedManager


class CachingReverseManyRelatedObjectsDescriptor(ReverseManyRelatedObjectsDescriptor):
    def __get__(self, instance, cls=None):
        manager = super(CachingReverseManyRelatedObjectsDescriptor, self).__get__(instance, cls)

        CachingRelatedManager = get_caching_related_manager(manager.__class__,
                                                            instance,
                                                            self.field.name,
                                                            self.field.rel.related_name)

        manager.__class__ = CachingRelatedManager
        return manager


class CachingManyRelatedObjectsDescriptor(ManyRelatedObjectsDescriptor):
    def __get__(self, instance, cls=None):
        manager = super(CachingManyRelatedObjectsDescriptor, self).__get__(instance, cls)

        CachingRelatedManager = get_caching_related_manager(manager.__class__,
                                                            instance,
                                                            self.related.get_accessor_name(),
                                                            self.related.field.name)

        manager.__class__ = CachingRelatedManager
        return manager


class CachingManyToManyField(ManyToManyField):
    def contribute_to_class(self, cls, name):
        super(CachingManyToManyField, self).contribute_to_class(cls, name)
        setattr(cls, self.name, CachingReverseManyRelatedObjectsDescriptor(self))

    def contribute_to_related_class(self, cls, related):
        super(CachingManyToManyField, self).contribute_to_related_class(cls, related)
        setattr(cls, related.get_accessor_name(), CachingManyRelatedObjectsDescriptor(related))


########NEW FILE########
__FILENAME__ = managers
from django.db import models
from django.db.models import signals
from cache import cache
from django.db.models.query import QuerySet

CACHE_DURATION = 60 * 30

def _cache_key(model, pk, field=None):
    if field:
        return "%s:%s.%s:%s" % (field, model._meta.app_label, model._meta.module_name, pk)
    else:
        return "%s.%s:%s" % (model._meta.app_label, model._meta.module_name, pk)

def _get_cache_key(self, field=None):
    return self._cache_key(self.pk, field)


class CachingManager(models.Manager):
    def __init__(self, use_for_related_fields=True, *args, **kwargs):
        self.use_for_related_fields = use_for_related_fields
        super(CachingManager, self).__init__(*args, **kwargs)

    def get_query_set(self):
        return CachingQuerySet(self.model)

    def contribute_to_class(self, model, name):
        signals.post_save.connect(self._post_save, sender=model)
        signals.post_delete.connect(self._post_delete, sender=model)
        setattr(model, '_cache_key', classmethod(_cache_key))
        setattr(model, '_get_cache_key', _get_cache_key)
        setattr(model, 'cache_key', property(_get_cache_key))
        return super(CachingManager, self).contribute_to_class(model, name)

    def _invalidate_cache(self, instance):
        """
        Explicitly set a None value instead of just deleting so we don't have any race
        conditions where:
            Thread 1 -> Cache miss, get object from DB
            Thread 2 -> Object saved, deleted from cache
            Thread 1 -> Store (stale) object fetched from DB in cache
        Five second should be more than enough time to prevent this from happening for
        a web app.
        """
        cache.set(instance.cache_key, None, 5)

    def _post_save(self, instance, **kwargs):
        self._invalidate_cache(instance)

    def _post_delete(self, instance, **kwargs):
        self._invalidate_cache(instance)


class CachingQuerySet(QuerySet):
    def iterator(self):
        superiter = super(CachingQuerySet, self).iterator()
        while True:
            obj = superiter.next()
            # Use cache.add instead of cache.set to prevent race conditions (see CachingManager)
            cache.add(obj.cache_key, obj, CACHE_DURATION)
            yield obj

    def get(self, *args, **kwargs):
        """
        Checks the cache to see if there's a cached entry for this pk. If not, fetches 
        using super then stores the result in cache.

        Most of the logic here was gathered from a careful reading of 
        ``django.db.models.sql.query.add_filter``
        """
        if self.query.where:
            # If there is any other ``where`` filter on this QuerySet just call
            # super. There will be a where clause if this QuerySet has already
            # been filtered/cloned.
            return super(CachingQuerySet, self).get(*args, **kwargs)

        # Punt on anything more complicated than get by pk/id only...
        if len(kwargs) == 1:
            k = kwargs.keys()[0]
            if k in ('pk', 'pk__exact', '%s' % self.model._meta.pk.attname, 
                     '%s__exact' % self.model._meta.pk.attname):
                obj = cache.get(self.model._cache_key(pk=kwargs.values()[0]))
                if obj is not None:
                    obj.from_cache = True
                    return obj

        # Calls self.iterator to fetch objects, storing object in cache.
        return super(CachingQuerySet, self).get(*args, **kwargs)

########NEW FILE########
__FILENAME__ = models
import managers
import fields
from django.db import models

class CachedModel(models.Model):
    from_cache = False
    class Meta:
        abstract = True

class Author(CachedModel):
    name = models.CharField(max_length=32)
    objects = managers.CachingManager()

    def __unicode__(self):
        return self.name

class Site(CachedModel):
    name = models.CharField(max_length=32)
    objects = managers.CachingManager()

    def __unicode__(self):
        return self.name

class Article(CachedModel):
    name = models.CharField(max_length=32)
    author = models.ForeignKey('Author')
    sites = fields.CachingManyToManyField(Site, related_name='articles')
    objects = managers.CachingManager()

    def __unicode__(self):
        return self.name

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from models import *

class CacheTest(TestCase):
    fixtures = ['test']

    def test_cache_get_by_pk(self):
        self.assertFalse(Article.objects.get(pk=1).from_cache)
        self.assertTrue(Article.objects.get(pk=1).from_cache)

    def test_cache_get_not_pk(self):
        # Prime cache
        self.assertFalse(Article.objects.get(pk=1).from_cache)
        self.assertTrue(Article.objects.get(pk=1).from_cache)

        # Not from cache b/c it's not a simple get by pk
        self.assertFalse(Article.objects.get(pk=1, name='Mike Malone').from_cache)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

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
# Django settings for caching project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'app.db'             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

CACHE_BACKEND = "memcached://127.0.0.1:11211/?timeout=60"

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
SECRET_KEY = '4&q_8qhs!!es1!1$8+b^@h(z7&9)u)1-j5yl_n11%d$r#owxty'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
)

ROOT_URLCONF = 'caching.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'app',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^caching/', include('caching.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
