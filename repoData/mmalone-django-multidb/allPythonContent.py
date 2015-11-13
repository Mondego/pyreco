__FILENAME__ = models
from django.db import models
from django.contrib.auth.models import User
from multidb.db.models.manager import SlaveDatabaseManager

class Frob(models.Model):
    thing = models.CharField(max_length=32)
    owner = models.ForeignKey(User)

    objects = SlaveDatabaseManager()

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = manager
from django import db
from multidb.db import connection
from multidb.db.models.query import MultiDBQuerySet

class SlaveDatabaseManager(db.models.Manager):
    def get_query_set(self):
        """
        Return a MultiDBQuerySet objet with its query
        tied to a random slave database.
        """
        return MultiDBQuerySet(self.model, query=self.create_query())

    def create_query(self):
        """
        Returns a new Query object connected to a
        slave database.
        """
        return db.models.sql.Query(self.model, connection)

########NEW FILE########
__FILENAME__ = query
from django.db.models.query import QuerySet
from django.db import connection as default_connection

class MultiDBQuerySet(QuerySet):
    """
    QuerySet subclass that writes to the primary (Django default) database
    but reads from slave databases.
    
    We only have to override the `update` and `filter` methods. The `save`
    and `delete` methods import django.db.connection directly, so they'll
    operate on the default database regardless.
    """

    def filter(self, *args, **kwargs):
        """
        If we're filtering on the pk, make sure the query goes to the master.
        This is necessary because when you save() an object Django first
        calls filter(pk=<pk>) and in order to decide whether to insert or
        update. If we send these queries to the slave, a small amount of lag
        could result in double inserts and pk conflicts.
        """
        if 'pk' in kwargs:
            self.query.connection = default_connection
        return super(MultiDBQuerySet, self).filter(*args, **kwargs)

    def update(self, **kwargs):
        """
        Updates all elements in the current QuerySet, settinga ll given
        fields to the appropriate values. Gotta use the default (read/write)
        databases connection for this.
        """
        slave_conn = self.query.connection
        self.query.connection = default_connection
        super(MultiDBQuerySet, self).update(**kwargs)
        self.query.connection = slave_conn
    update.alters_data = True

    def _update(self, values):
        slave_conn = self.query.connection
        self.query.connection = default_connection
        super(MultiDBQuerySet, self)._update(values)
        self.query.connection = slave_conn
    _update.alters_data = True

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
# Django settings for multidb project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'mysql'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'app'             # Or path to database file if using sqlite3.
DATABASE_USER = 'root'             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

SLAVE_DATABASES = (
    (1, { 
            'host': 'localhost',
            'db': 'app',
            'user': 'slave',
        }
    ),
)

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
SECRET_KEY = '69m#u8#(0hlcihc76-hutqcy)+g5j1q)4&qty^d6xfjakhvyg$'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
)

ROOT_URLCONF = 'multidb.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.auth',
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
    # (r'^multidb/', include('multidb.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/(.*)', admin.site.root),
)

########NEW FILE########
