__FILENAME__ = core
from django.db import connection
from django.conf import settings
from sqlalchemy import MetaData, create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.pool import _ConnectionRecord as _ConnectionRecordBase

from .table import generate_tables
from .wrapper import Wrapper
from .sqlite import SqliteWrapper


__all__ = ['get_engine', 'get_meta', 'get_tables']


class Cache(object):
    """Module level cache"""
    pass


SQLALCHEMY_ENGINES = {
    'sqlite3': 'sqlite',
    'mysql': 'mysql',
    'postgresql': 'postgresql',
    'postgresql_psycopg2': 'postgresql+psycopg2',
    'oracle': 'oracle',
}
SQLALCHEMY_ENGINES.update(getattr(settings, 'ALDJEMY_ENGINES', {}))


def get_engine_string():
    sett = connection.settings_dict
    return sett['ENGINE'].rsplit('.')[-1]


def get_connection_string():
    engine = SQLALCHEMY_ENGINES[get_engine_string()]
    options = '?charset=utf8' if engine == 'mysql' else ''
    return engine + '://' + options


def get_engine():
    if not getattr(Cache, 'engine', None):
        engine_string = get_engine_string()
        # we have to use autocommit=True, because SQLAlchemy
        # is not aware of Django transactions
        kw = {}
        if engine_string == 'sqlite3':
            kw['native_datetime'] = True
        Cache.engine = create_engine(get_connection_string(),
                                   pool=DjangoPool(creator=None), **kw)
    return Cache.engine


def get_meta():
    if not getattr(Cache, 'meta', None):
        Cache.meta = MetaData()
    return Cache.meta


def get_tables():
    if not getattr(Cache, 'tables_loaded', False):
        generate_tables(get_meta())
        Cache.tables_loaded = True
    return get_meta().tables


class DjangoPool(NullPool):
    def status(self):
        return "DjangoPool"

    def _create_connection(self):
        return _ConnectionRecord(self)

    def recreate(self):
        self.logger.info("Pool recreating")

        return DjangoPool(self._creator,
            recycle=self._recycle,
            echo=self.echo,
            logging_name=self._orig_logging_name,
            use_threadlocal=self._use_threadlocal)


class _ConnectionRecord(_ConnectionRecordBase):
    def __init__(self, pool):
        self.__pool = pool
        self.info = {}

        self.wrap = False
        #pool.dispatch.first_connect.exec_once(self.connection, self)
        pool.dispatch.connect(self.connection, self)
        self.wrap = True

    @property
    def connection(self):
        if connection.connection is None:
            connection._cursor()
        if connection.vendor == 'sqlite':
            return SqliteWrapper(connection.connection)
        if self.wrap:
            return Wrapper(connection.connection)
        return connection.connection

    def close(self):
        pass

    def invalidate(self, e=None):
        pass

    def get_connection(self):
        return self.connection

########NEW FILE########
__FILENAME__ = models
# In this file we import all django models and patch them
from .orm import prepare_models

prepare_models()

########NEW FILE########
__FILENAME__ = orm
from sqlalchemy import orm
from django.db.models.fields.related import (ForeignKey, OneToOneField,
        ManyToManyField)
from django.db import connection
from django.core import signals

from .core import get_tables, get_engine, Cache
from .table import get_django_models


def get_session():
    if not hasattr(connection, 'sa_session'):
        session = orm.create_session()
        session.bind = get_engine()
        connection.sa_session = session
    return connection.sa_session


def new_session(**kw):
    get_session()
signals.request_started.connect(new_session)


def _extract_model_attrs(model, sa_models):
    tables = get_tables()

    name = model._meta.db_table
    table = tables[name]
    fks = [t for t in model._meta.fields
             if isinstance(t, (ForeignKey, OneToOneField))]
    attrs = {}
    rel_fields = fks + model._meta.many_to_many
    for fk in rel_fields:
        if not fk.column in table.c and not isinstance(fk, ManyToManyField):
            continue
        parent_model = fk.related.parent_model._meta
        p_table = tables[parent_model.db_table]
        p_name = parent_model.pk.column

        backref = (fk.rel.related_name.lower().strip('+')
                   if fk.rel.related_name else None)
        if not backref:
            backref = model._meta.object_name.lower()
            if not isinstance(fk, OneToOneField):
                backref = backref + '_set'

        kw = {}
        if isinstance(fk, ManyToManyField):
            model_pk = model._meta.pk.column
            sec_table = tables[fk.related.field.m2m_db_table()]
            sec_column = fk.m2m_column_name()
            p_sec_column = fk.m2m_reverse_name()
            kw.update(
                secondary=sec_table,
                primaryjoin=(sec_table.c[sec_column] == table.c[model_pk]),
                secondaryjoin=(sec_table.c[p_sec_column] == p_table.c[p_name])
                )
            if fk.model() != model:
                backref = None
        else:
            kw.update(
                foreign_keys=[table.c[fk.column]],
                primaryjoin=(table.c[fk.column] == p_table.c[p_name]),
                remote_side=p_table.c[p_name],
                )
        attrs[fk.name] = orm.relationship(
                sa_models[parent_model.db_table],
                backref=backref,
                **kw
                )
    return attrs


def prepare_models():
    tables = get_tables()
    models = get_django_models()
    sa_models = getattr(Cache, 'models', {})

    for model in models:
        name = model._meta.db_table
        mixin = getattr(model, 'aldjemy_mixin', None)
        bases = (mixin, BaseSQLAModel) if mixin else (BaseSQLAModel, )
        table = tables[name]
        sa_models[name] = type(model._meta.object_name, bases,
                               {'table': table})

    for model in models:
        name = model._meta.db_table
        if 'id' not in  sa_models[name].__dict__:
            table = tables[name]
            attrs = _extract_model_attrs(model, sa_models)
            name = model._meta.db_table
            orm.mapper(sa_models[name], table, attrs)
        model.sa = sa_models[name]

    Cache.models = sa_models


class BaseSQLAModel(object):
    @classmethod
    def query(cls, *a, **kw):
        if a or kw:
            return get_session().query(*a, **kw)
        return get_session().query(cls)

########NEW FILE########
__FILENAME__ = sqlite
from .wrapper import Wrapper


class SqliteWrapper(Wrapper):

    def wrapper(self, obj):
        return sqlite_wrapper(obj)


def sqlite_wrapper(func):
    from django.db.backends.sqlite3.base import Database

    def null_converter(s):
        return s

    def wrapper(*a, **kw):
        converter = Database.converters.pop('DATETIME')
        Database.register_converter("datetime", null_converter)
        res = func(*a, **kw)
        Database.register_converter("DATETIME", converter)
        return res

    return wrapper

########NEW FILE########
__FILENAME__ = table
#! /usr/bin/env python

from sqlalchemy import types, Column, Table
from django.db.models.loading import AppCache
from aldjemy.types import simple, foreign_key, varchar
from django.conf import settings


DATA_TYPES = {
    'AutoField':         simple(types.Integer),
    'BooleanField':      simple(types.Boolean),
    'CharField':         varchar,
    'CommaSeparatedIntegerField': varchar,
    'DateField':         simple(types.Date),
    'DateTimeField':     simple(types.DateTime),
    'DecimalField':      lambda x: types.Numeric(scale=x.decimal_places,
                                                 precision=x.max_digits),
    'FileField':         varchar,
    'FilePathField':     varchar,
    'FloatField':        simple(types.Float),
    'IntegerField':      simple(types.Integer),
    'BigIntegerField':   simple(types.BigInteger),
    'IPAddressField':    lambda field: types.CHAR(length=15),
    'NullBooleanField':  simple(types.Boolean),
    'OneToOneField':     foreign_key,
    'ForeignKey':        foreign_key,
    'PositiveIntegerField': simple(types.Integer),
    'PositiveSmallIntegerField': simple(types.SmallInteger),
    'SlugField':         varchar,
    'SmallIntegerField': simple(types.SmallInteger),
    'TextField':         simple(types.Text),
    'TimeField':         simple(types.Time),
}

DATA_TYPES.update(getattr(settings, 'ALDJEMY_DATA_TYPES', {}))


def get_django_models():
    ac = AppCache()
    return ac.get_models()


def get_all_django_models():
    models = get_django_models()
    # Get M2M models
    new_models = []
    for model in models:
        for field in model._meta.many_to_many:
            new_model = field.rel.through
            if new_model:
                new_models.append(new_model)
    return models + new_models


def generate_tables(metadata):
    models = get_all_django_models()
    for model in  models:
        name = model._meta.db_table
        if name in metadata.tables or model._meta.proxy:
            continue
        columns = []
        for field, parent_model in model._meta.get_fields_with_model():
            if parent_model:
                continue
            typ = DATA_TYPES[field.get_internal_type()](field)
            if not isinstance(typ, (list, tuple)):
                typ = [typ]
            columns.append(Column(field.column,
                    *typ, primary_key=field.primary_key))
        Table(name, metadata, *columns)

########NEW FILE########
__FILENAME__ = types
#coding: utf-8

from sqlalchemy import types, ForeignKey


def simple(typ):
    return lambda field: typ()


def varchar(field):
    return types.String(length=field.max_length)


def foreign_key(field):
    target = field.related.parent_model._meta
    target_table = target.db_table
    target_pk = target.pk.column
    return types.Integer, ForeignKey('%s.%s' % (target_table, target_pk))

########NEW FILE########
__FILENAME__ = wrapper
"Wrapper to disable commit in sqla"


class Wrapper(object):
    def __init__(self, obj):
        self.obj = obj

    def __getattr__(self, attr):
        if attr in ['commit', 'rollback']:
            return nullop
        obj = getattr(self.obj, attr)
        if attr not in ['cursor', 'execute']:
            return obj
        if attr == 'cursor':
            return type(self)(obj)
        return self.wrapper(obj)

    def wrapper(self, obj):
        "Implement if you need to make your customized wrapper"
        return obj

    def __call__(self, *a, **kw):
        self.obj = self.obj(*a, **kw)
        return self


def nullop(*a, **kw):
    return

########NEW FILE########
__FILENAME__ = models
from sample.models import Book


class BookProxy(Book):
    class Meta:
        proxy = True

########NEW FILE########
__FILENAME__ = views

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = models
from django.db import models


class Chapter(models.Model):
    title = models.CharField(max_length=200)
    book = models.ForeignKey('Book')


class Book(models.Model):
    title = models.CharField(max_length=200)


class Author(models.Model):
    name = models.CharField(max_length=200)
    biography = models.TextField()

    books = models.ManyToManyField(Book, related_name='books')


class StaffAuthor(Author):
    role = models.TextField()


class Review(models.Model):
    book = models.ForeignKey('a_sample.BookProxy')

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from sample.models import Chapter, Book, Author, StaffAuthor, Review
from a_sample.models import BookProxy


class SimpleTest(TestCase):
    def test_aldjemy_initialization(self):
        self.assertTrue(Chapter.sa)
        self.assertTrue(Book.sa)
        self.assertTrue(Author.sa)
        self.assertTrue(StaffAuthor.sa)
        self.assertTrue(Review.sa)
        self.assertTrue(BookProxy.sa)

    def test_engine_override_test(self):
        from aldjemy import core
        self.assertEquals(core.get_connection_string(), 'sqlite+pysqlite://')

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = settings
# Django settings for test1 project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'db.sq',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

ALDJEMY_ENGINES = {
    'sqlite3': 'sqlite+pysqlite'
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
# calendars according to the current locale
USE_L10N = True

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

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

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
SECRET_KEY = 'h2co6ww9u2)^a6ja@@@s*f!ddc+-is7+(=d8d4btunbpp8)f(a'

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

ROOT_URLCONF = 'test1.urls'

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
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'django_extensions',
    'a_sample',
    'sample',
    'aldjemy',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
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
__FILENAME__ = test
from sample.models import StaffAuthor

print StaffAuthor.sa.query().all()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'test1.views.home', name='home'),
    # url(r'^test1/', include('test1.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
