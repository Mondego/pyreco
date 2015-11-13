__FILENAME__ = ui
# Initialize Django
from djangoappengine import main

from google.appengine.ext.appstats.ui import app as application, main


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = boot
import logging
import os
import sys

def find_project_dir():
    """
        Go through the path, and look for app.yaml
    """
    for path in sys.path:
        abs_path = os.path.join(os.path.abspath(path), "app.yaml")
        if os.path.exists(abs_path):
            return os.path.dirname(abs_path)

    raise RuntimeError("Unable to locate app.yaml on sys.path")

PROJECT_DIR = find_project_dir()
DATA_ROOT = os.path.join(PROJECT_DIR, '.gaedata')

# Overrides for os.environ.
env_ext = {}
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    env_ext['DJANGO_SETTINGS_MODULE'] = 'settings'


def setup_env():
    """Configures GAE environment for command-line apps."""

    # Try to import the appengine code from the system path.
    try:
        from google.appengine.api import apiproxy_stub_map
    except ImportError:
        for k in [k for k in sys.modules if k.startswith('google')]:
            del sys.modules[k]

        # Not on the system path. Build a list of alternative paths
        # where it may be. First look within the project for a local
        # copy, then look for where the Mac OS SDK installs it.
        paths = [os.path.join(PROJECT_DIR, 'google_appengine'),
                 os.environ.get('APP_ENGINE_SDK'),
                 '/usr/local/google_appengine',
                 '/usr/local/opt/google-app-engine/share/google-app-engine',
                 '/Applications/GoogleAppEngineLauncher.app/Contents/Resources/GoogleAppEngine-default.bundle/Contents/Resources/google_appengine']
        for path in os.environ.get('PATH', '').split(os.pathsep):
            path = path.rstrip(os.sep)
            if path.endswith('google_appengine'):
                paths.append(path)
        if os.name in ('nt', 'dos'):
            path = r'%(PROGRAMFILES)s\Google\google_appengine' % os.environ
            paths.append(path)

        # Loop through all possible paths and look for the SDK dir.
        sdk_path = None
        for path in paths:
            if not path:
                continue
            path = os.path.expanduser(path)
            path = os.path.realpath(path)
            if os.path.exists(path):
                sdk_path = path
                break

        # The SDK could not be found in any known location.
        if sdk_path is None:
            sys.stderr.write("The Google App Engine SDK could not be found!\n"
                             "Make sure it's accessible via your PATH "
                             "environment and called google_appengine.\n")
            sys.exit(1)

        # First add the found SDK to the path
        sys.path = [ sdk_path ] + sys.path

        # Then call fix_sys_path from the SDK
        try:
            from dev_appserver import fix_sys_path
        except ImportError:
            from old_dev_appserver import fix_sys_path
        fix_sys_path()

    setup_project()
    from .utils import have_appserver
    if have_appserver:
        # App Engine's threading.local is broken.
        setup_threading()
    elif not os.path.exists(DATA_ROOT):
        os.mkdir(DATA_ROOT)
    setup_logging()

    if not have_appserver:
        # Patch Django to support loading management commands from zip
        # files.
        from django.core import management
        management.find_commands = find_commands


def find_commands(management_dir):
    """
    Given a path to a management directory, returns a list of all the
    command names that are available.
    This version works for django deployments which are file based or
    contained in a ZIP (in sys.path).

    Returns an empty list if no commands are defined.
    """
    import pkgutil
    return [modname for importer, modname, ispkg in pkgutil.iter_modules(
                [os.path.join(management_dir, 'commands')]) if not ispkg]


def setup_threading():
    if sys.version_info >= (2, 7):
        return
    # XXX: On Python 2.5 GAE's threading.local doesn't work correctly
    #      with subclassing.
    try:
        from django.utils._threading_local import local
        import threading
        threading.local = local
    except ImportError:
        pass


def setup_logging():
    # Fix Python 2.6 logging module.
    logging.logMultiprocessing = 0

    # Enable logging.
    level = logging.DEBUG
    from .utils import have_appserver
    if have_appserver:
        # We can't import settings at this point when running a normal
        # manage.py command because this module gets imported from
        # settings.py.
        from django.conf import settings
        if not settings.DEBUG:
            level = logging.INFO
    logging.getLogger().setLevel(level)


def setup_project():
    from .utils import have_appserver, on_production_server
    if have_appserver:
        # This fixes a pwd import bug for os.path.expanduser().
        env_ext['HOME'] = PROJECT_DIR

    # The dev_appserver creates a sandbox which restricts access to
    # certain modules and builtins in order to emulate the production
    # environment. Here we get the subprocess module back into the
    # dev_appserver sandbox.This module is just too important for
    # development. Also we add the compiler/parser module back and
    # enable https connections (seem to be broken on Windows because
    # the _ssl module is disallowed).
    if not have_appserver:
        try:
            from google.appengine.tools import dev_appserver
        except ImportError:
            from google.appengine.tools import old_dev_appserver as dev_appserver

        try:
            # Backup os.environ. It gets overwritten by the
            # dev_appserver, but it's needed by the subprocess module.
            env = dev_appserver.DEFAULT_ENV
            dev_appserver.DEFAULT_ENV = os.environ.copy()
            dev_appserver.DEFAULT_ENV.update(env)
            # Backup the buffer() builtin. The subprocess in Python 2.5
            # on Linux and OS X uses needs it, but the dev_appserver
            # removes it.
            dev_appserver.buffer = buffer
        except AttributeError:
            logging.warn("Could not patch the default environment. "
                         "The subprocess module will not work correctly.")

        try:
            # Allow importing compiler/parser, _ssl (for https),
            # _io for Python 2.7 io support on OS X
            dev_appserver.HardenedModulesHook._WHITE_LIST_C_MODULES.extend(
                ('parser', '_ssl', '_io'))
        except AttributeError:
            logging.warn("Could not patch modules whitelist. the compiler "
                         "and parser modules will not work and SSL support "
                         "is disabled.")
    elif not on_production_server:
        try:
            try:
                from google.appengine.tools import dev_appserver
            except ImportError:
                from google.appengine.tools import old_dev_appserver as dev_appserver

            # Restore the real subprocess module.
            from google.appengine.api.mail_stub import subprocess
            sys.modules['subprocess'] = subprocess
            # Re-inject the buffer() builtin into the subprocess module.
            subprocess.buffer = dev_appserver.buffer
        except Exception, e:
            logging.warn("Could not add the subprocess module to the "
                         "sandbox: %s" % e)

    os.environ.update(env_ext)

    extra_paths = [PROJECT_DIR, os.path.join(os.path.dirname(__file__), 'lib')]
    zip_packages_dir = os.path.join(PROJECT_DIR, 'zip-packages')

    # We support zipped packages in the common and project folders.
    if os.path.isdir(zip_packages_dir):
        for zip_package in os.listdir(zip_packages_dir):
            extra_paths.append(os.path.join(zip_packages_dir, zip_package))

    # App Engine causes main.py to be reloaded if an exception gets
    # raised on the first request of a main.py instance, so don't call
    # setup_project() multiple times. We ensure this indirectly by
    # checking if we've already modified sys.path, already.
    if len(sys.path) < len(extra_paths) or \
            sys.path[:len(extra_paths)] != extra_paths:
        for path in extra_paths:
            while path in sys.path:
                sys.path.remove(path)
        sys.path = extra_paths + sys.path

########NEW FILE########
__FILENAME__ = indexes
from dbindexer import autodiscover
autodiscover()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{{ project_name }}.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
# Django settings for {{ project_name }} project.

# Initialize App Engine and import the default settings (DB backend, etc.).
# If you want to use a different backend you have to remove all occurences
# of "djangoappengine" from this file.
from djangoappengine.settings_base import *

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

# Activate django-dbindexer for the default database
DATABASES['default'] = {'ENGINE': 'dbindexer', 'TARGET': DATABASES['default']}

AUTOLOAD_SITECONF = 'indexes'

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
USE_TZ = False

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
SECRET_KEY = '{{ secret_key }}'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    # This loads the index definitions, so it has to come first
    'autoload.middleware.AutoloadMiddleware',

    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = '{{ project_name }}.urls'

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
    'djangotoolbox',
    'autoload',
    'dbindexer',

    # djangoappengine should come last, so it can override a few manage.py commands
    'djangoappengine',
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
    # url(r'^$', '{{ project_name }}.views.home', name='home'),
    # url(r'^{{ project_name }}/', include('{{ project_name }}.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = settings
from {{ project_name }}.settings import *

########NEW FILE########
__FILENAME__ = base
import datetime
import decimal
import logging
import os
import shutil

from django.db.utils import DatabaseError

from google.appengine.api.datastore import Delete, Query
from google.appengine.api.datastore_errors import BadArgumentError, \
    BadValueError
from google.appengine.api.datastore_types import Blob, Key, Text, \
    ValidateInteger
from google.appengine.api.namespace_manager import set_namespace
from google.appengine.ext.db.metadata import get_kinds, get_namespaces

from djangotoolbox.db.base import (
    NonrelDatabaseClient,
    NonrelDatabaseFeatures,
    NonrelDatabaseIntrospection,
    NonrelDatabaseOperations,
    NonrelDatabaseValidation,
    NonrelDatabaseWrapper)
from djangotoolbox.db.utils import decimal_to_string

from ..boot import DATA_ROOT
from ..utils import appid, on_production_server
from .creation import DatabaseCreation
from .stubs import stub_manager


DATASTORE_PATHS = {
    'datastore_path': os.path.join(DATA_ROOT, 'datastore'),
    'blobstore_path': os.path.join(DATA_ROOT, 'blobstore'),
    #'rdbms_sqlite_path': os.path.join(DATA_ROOT, 'rdbms'),
    'prospective_search_path': os.path.join(DATA_ROOT, 'prospective-search'),
}


def key_from_path(db_table, value):
    """
    Workaround for GAE choosing not to validate integer ids when
    creating keys.

    TODO: Should be removed if it gets fixed.
    """
    if isinstance(value, (int, long)):
        ValidateInteger(value, 'id')
    return Key.from_path(db_table, value)


def get_datastore_paths(options):
    paths = {}
    for key, path in DATASTORE_PATHS.items():
        paths[key] = options.get(key, path)
    return paths


def destroy_datastore(paths):
    """Destroys the appengine datastore at the specified paths."""
    for path in paths.values():
        if not path:
            continue
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except OSError, error:
            if error.errno != 2:
                logging.error("Failed to clear datastore: %s" % error)


class DatabaseFeatures(NonrelDatabaseFeatures):

    # GAE only allow strictly positive integers (and strings) to be
    # used as key values.
    allows_primary_key_0 = False

    # Anything that results in a something different than a positive
    # integer or a string cannot be directly used as a key on GAE.
    # Note that DecimalField values are encoded as strings, so can be
    # used as keys.
    # With some encoding, we could allow most fields to be used as a
    # primary key, but for now only mark what can and what cannot be
    # safely used.
    supports_primary_key_on = \
        NonrelDatabaseFeatures.supports_primary_key_on - set((
        'FloatField', 'DateField', 'DateTimeField', 'TimeField',
        'BooleanField', 'NullBooleanField', 'TextField', 'XMLField'))


class DatabaseOperations(NonrelDatabaseOperations):
    compiler_module = __name__.rsplit('.', 1)[0] + '.compiler'

    # Date used to store times as datetimes.
    # TODO: Use just date()?
    DEFAULT_DATE = datetime.date(1970, 1, 1)

    # Time used to store dates as datetimes.
    DEFAULT_TIME = datetime.time()

    def sql_flush(self, style, tables, sequences, allow_cascade=False):
        self.connection.flush()
        return []

    def value_to_db_auto(self, value):
        """
        New keys generated by the GAE datastore hold longs.
        """
        if value is None:
            return None
        return long(value)

    def value_for_db(self, value, field, lookup=None):
        """
        We'll simulate `startswith` lookups with two inequalities:

            property >= value and property <= value + u'\ufffd',

        and need to "double" the value before passing it through the
        actual datastore conversions.
        """
        super_value_for_db = super(DatabaseOperations, self).value_for_db
        if lookup == 'startswith':
            return [super_value_for_db(value, field, lookup),
                    super_value_for_db(value + u'\ufffd', field, lookup)]
        return super_value_for_db(value, field, lookup)

    def _value_for_db(self, value, field, field_kind, db_type, lookup):
        """
        GAE database may store a restricted set of Python types, for
        some cases it has its own types like Key, Text or Blob.

        TODO: Consider moving empty list handling here (from insert).
        """

        # Store Nones as Nones to handle nullable fields, even keys.
        if value is None:
            return None

        # Parent can handle iterable fields and Django wrappers.
        value = super(DatabaseOperations, self)._value_for_db(
            value, field, field_kind, db_type, lookup)

        # Convert decimals to strings preserving order.
        if field_kind == 'DecimalField':
            value = decimal_to_string(
                value, field.max_digits, field.decimal_places)

        # Create GAE db.Keys from Django keys.
        # We use model's table name as key kind (the table of the model
        # of the instance that the key identifies, for ForeignKeys and
        # other relations).
        if db_type == 'key':
#            value = self._value_for_db_key(value, field_kind)
            try:
                value = key_from_path(field.model._meta.db_table, value)
            except (BadArgumentError, BadValueError,):
                raise DatabaseError("Only strings and positive integers "
                                    "may be used as keys on GAE.")

        # Store all strings as unicode, use db.Text for longer content.
        elif db_type == 'string' or db_type == 'text':
            if isinstance(value, str):
                value = value.decode('utf-8')
            if db_type == 'text':
                value = Text(value)

        # Store all date / time values as datetimes, by using some
        # default time or date.
        elif db_type == 'date':
            value = datetime.datetime.combine(value, self.DEFAULT_TIME)
        elif db_type == 'time':
            value = datetime.datetime.combine(self.DEFAULT_DATE, value)

        # Store BlobField, DictField and EmbeddedModelField values as Blobs.
        elif db_type == 'bytes':
            value = Blob(value)

        return value

    def _value_from_db(self, value, field, field_kind, db_type):
        """
        Undoes conversions done in value_for_db.
        """

        # We could have stored None for a null field.
        if value is None:
            return None

        # All keys were converted to the Key class.
        if db_type == 'key':
            assert isinstance(value, Key), \
                "GAE db.Key expected! Try changing to old storage, " \
                "dumping data, changing to new storage and reloading."
            assert value.parent() is None, "Parents are not yet supported!"
            value = value.id_or_name()
#            value = self._value_from_db_key(value, field_kind)

        # Always retrieve strings as unicode (old datasets may
        # contain non-unicode strings).
        elif db_type == 'string' or db_type == 'text':
            if isinstance(value, str):
                value = value.decode('utf-8')
            else:
                value = unicode(value)

        # Dates and times are stored as datetimes, drop the added part.
        elif db_type == 'date':
            value = value.date()
        elif db_type == 'time':
            value = value.time()

        # Convert GAE Blobs to plain strings for Django.
        elif db_type == 'bytes':
            value = str(value)

        # Revert the decimal-to-string encoding.
        if field_kind == 'DecimalField':
            value = decimal.Decimal(value)

        return super(DatabaseOperations, self)._value_from_db(
            value, field, field_kind, db_type)

#    def _value_for_db_key(self, value, field_kind):
#        """
#        Converts values to be used as entity keys to strings,
#        trying (but not fully succeeding) to preserve comparisons.
#        """

#        # Bools as positive integers.
#        if field_kind == 'BooleanField':
#            value = int(value) + 1

#        # Encode floats as strings.
#        elif field_kind == 'FloatField':
#            value = self.value_to_db_decimal(
#                decimal.Decimal(value), None, None)

#        # Integers as strings (string keys sort after int keys, so
#        # all need to be encoded to preserve comparisons).
#        elif field_kind in ('IntegerField', 'BigIntegerField',
#           'PositiveIntegerField', 'PositiveSmallIntegerField',
#           'SmallIntegerField'):
#            value = self.value_to_db_decimal(
#                decimal.Decimal(value), None, 0)

#        return value

#    def value_from_db_key(self, value, field_kind):
#        """
#        Decodes value previously encoded in a key.
#        """
#        if field_kind == 'BooleanField':
#            value = bool(value - 1)
#        elif field_kind == 'FloatField':
#            value = float(value)
#        elif field_kind in ('IntegerField', 'BigIntegerField',
#           'PositiveIntegerField', 'PositiveSmallIntegerField',
#           'SmallIntegerField'):
#            value = int(value)

#        return value


class DatabaseClient(NonrelDatabaseClient):
    pass


class DatabaseValidation(NonrelDatabaseValidation):
    pass


class DatabaseIntrospection(NonrelDatabaseIntrospection):

    def table_names(self, cursor=None):
        """
        Returns a list of names of all tables that exist in the
        database.
        """
        return [kind.key().name() for kind in Query(kind='__kind__').Run()]


class DatabaseWrapper(NonrelDatabaseWrapper):

    def __init__(self, *args, **kwds):
        super(DatabaseWrapper, self).__init__(*args, **kwds)
        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.validation = DatabaseValidation(self)
        self.introspection = DatabaseIntrospection(self)
        options = self.settings_dict
        self.remote_app_id = options.get('REMOTE_APP_ID', appid)
        self.domain = options.get('DOMAIN', 'appspot.com')
        self.remote_api_path = options.get('REMOTE_API_PATH', None)
        self.secure_remote_api = options.get('SECURE_REMOTE_API', True)

        remote = options.get('REMOTE', False)
        if on_production_server:
            remote = False
        if remote:
            stub_manager.setup_remote_stubs(self)
        else:
            stub_manager.setup_stubs(self)

    def flush(self):
        """
        Helper function to remove the current datastore and re-open the
        stubs.
        """
        if stub_manager.active_stubs == 'remote':
            import random
            import string
            code = ''.join([random.choice(string.ascii_letters)
                            for x in range(4)])
            print "\n\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            print "Warning! You're about to delete the *production* datastore!"
            print "Only models defined in your INSTALLED_APPS can be removed!"
            print "If you want to clear the whole datastore you have to use " \
                  "the datastore viewer in the dashboard. Also, in order to " \
                  "delete all unneeded indexes you have to run appcfg.py " \
                  "vacuum_indexes."
            print "In order to proceed you have to enter the following code:"
            print code
            response = raw_input("Repeat: ")
            if code == response:
                print "Deleting..."
                delete_all_entities()
                print "Datastore flushed! Please check your dashboard's " \
                      "datastore viewer for any remaining entities and " \
                      "remove all unneeded indexes with appcfg.py " \
                      "vacuum_indexes."
            else:
                print "Aborting."
                exit()
        elif stub_manager.active_stubs == 'test':
            stub_manager.deactivate_test_stubs()
            stub_manager.activate_test_stubs(self)
        else:
            destroy_datastore(get_datastore_paths(self.settings_dict))
            stub_manager.setup_local_stubs(self)


def delete_all_entities():
    for namespace in get_namespaces():
        set_namespace(namespace)
        for kind in get_kinds():
            if kind.startswith('__'):
                continue
            while True:
                data = Query(kind=kind, keys_only=True).Get(200)
                if not data:
                    break
                Delete(data)

########NEW FILE########
__FILENAME__ = compiler
from functools import wraps
import sys

from django.db.models.fields import AutoField
from django.db.models.sql import aggregates as sqlaggregates
from django.db.models.sql.constants import MULTI, SINGLE
from django.db.models.sql.where import AND, OR
from django.db.utils import DatabaseError, IntegrityError
from django.utils.tree import Node

from google.appengine.api.datastore import Entity, Query, MultiQuery, \
    Put, Get, Delete
from google.appengine.api.datastore_errors import Error as GAEError
from google.appengine.api.datastore_types import Key, Text
from google.appengine.datastore.datastore_query import Cursor

from djangotoolbox.db.basecompiler import (
    NonrelQuery,
    NonrelCompiler,
    NonrelInsertCompiler,
    NonrelUpdateCompiler,
    NonrelDeleteCompiler,
    NonrelAggregateCompiler,
    NonrelDateCompiler,
    NonrelDateTimeCompiler)

from .db_settings import get_model_indexes
from .expressions import ExpressionEvaluator
from .utils import commit_locked


# Valid query types (a dictionary is used for speedy lookups).
OPERATORS_MAP = {
    'exact': '=',
    'gt': '>',
    'gte': '>=',
    'lt': '<',
    'lte': '<=',

    # The following operators are supported with special code below.
    'isnull': None,
    'in': None,
    'startswith': None,
    'range': None,
    'year': None,
}

# GAE filters used for negated Django lookups.
NEGATION_MAP = {
    'gt': '<=',
    'gte': '<',
    'lt': '>=',
    'lte': '>',
    # TODO: Support: "'exact': '!='" (it might actually become
    #       individual '<' and '>' queries).
}

# In some places None is an allowed value, and we need to distinguish
# it from the lack of value.
NOT_PROVIDED = object()


def safe_call(func):
    """
    Causes the decorated function to reraise GAE datastore errors as
    Django DatabaseErrors.
    """

    @wraps(func)
    def _func(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except GAEError, e:
            raise DatabaseError, DatabaseError(str(e)), sys.exc_info()[2]
    return _func


class GAEQuery(NonrelQuery):
    """
    A simple App Engine query: no joins, no distinct, etc.
    """

    # ----------------------------------------------
    # Public API
    # ----------------------------------------------

    def __init__(self, compiler, fields):
        super(GAEQuery, self).__init__(compiler, fields)
        self.inequality_field = None
        self.included_pks = None
        self.excluded_pks = ()
        self.has_negated_exact_filter = False
        self.ordering = []
        self.db_table = self.query.get_meta().db_table
        self.pks_only = (len(fields) == 1 and fields[0].primary_key)
        start_cursor = getattr(self.query, '_gae_start_cursor', None)
        end_cursor = getattr(self.query, '_gae_end_cursor', None)
        self.config = getattr(self.query, '_gae_config', {})
        self.gae_query = [Query(self.db_table, keys_only=self.pks_only,
                                cursor=start_cursor, end_cursor=end_cursor)]

    # This is needed for debugging.
    def __repr__(self):
        return '<GAEQuery: %r ORDER %r>' % (self.gae_query, self.ordering)

    @safe_call
    def fetch(self, low_mark=0, high_mark=None):
        query = self._build_query()
        executed = False
        if self.excluded_pks and high_mark is not None:
            high_mark += len(self.excluded_pks)
        if self.included_pks is not None:
            results = self.get_matching_pk(low_mark, high_mark)
        else:
            if high_mark is None or high_mark > low_mark:
                kw = {}
                if self.config:
                    kw.update(self.config)

                if low_mark:
                    kw['offset'] = low_mark
                else:
                    low_mark = 0

                if high_mark:
                    kw['limit'] = high_mark - low_mark

                results = query.Run(**kw)
                executed = True
            else:
                results = ()

        if executed and not isinstance(query, MultiQuery):
            def get_cursor():
                return query.GetCursor()
            self.query._gae_cursor = get_cursor

        for entity in results:
            if isinstance(entity, Key):
                key = entity
            else:
                key = entity.key()
            if key in self.excluded_pks:
                continue
            yield self._make_entity(entity)

    @safe_call
    def count(self, limit=NOT_PROVIDED):
        if self.included_pks is not None:
            return len(self.get_matching_pk(0, limit))
        if self.excluded_pks:
            return len(list(self.fetch(0, 2000)))
        # The datastore's Count() method has a 'limit' kwarg, which has
        # a default value (obviously).  This value can be overridden to
        # anything you like, and importantly can be overridden to
        # unlimited by passing a value of None.  Hence *this* method
        # has a default value of NOT_PROVIDED, rather than a default
        # value of None
        kw = {}
        if limit is not NOT_PROVIDED:
            kw['limit'] = limit
        return self._build_query().Count(**kw)

    @safe_call
    def delete(self):
        if self.included_pks is not None:
            keys = [key for key in self.included_pks if key is not None]
        else:
            keys = [key_dict[self.query.get_meta().pk.column] for key_dict in self.fetch()]
        if keys:
            Delete(keys)

    @safe_call
    def order_by(self, ordering):

        # GAE doesn't have any kind of natural ordering?
        if not isinstance(ordering, bool):
            for field, ascending in ordering:
                column = '__key__' if field.primary_key else field.column
                direction = Query.ASCENDING if ascending else Query.DESCENDING
                self.ordering.append((column, direction))


    @safe_call
    def add_filter(self, field, lookup_type, negated, value):
        """
        This function is used by the default add_filters()
        implementation.
        """
        if lookup_type not in OPERATORS_MAP:
            raise DatabaseError("Lookup type %r isn't supported." %
                                lookup_type)

        # GAE does not let you store empty lists, so we can tell
        # upfront that queriying for one will return nothing.
        if value in ([], ()):
            self.included_pks = []
            return

        # Optimization: batch-get by key; this is only suitable for
        # primary keys, not for anything that uses the key type.
        if field.primary_key and lookup_type in ('exact', 'in'):
            if self.included_pks is not None:
                raise DatabaseError("You can't apply multiple AND "
                                    "filters on the primary key. "
                                    "Did you mean __in=[...]?")
            if not isinstance(value, (tuple, list)):
                value = [value]
            pks = [pk for pk in value if pk is not None]
            if negated:
                self.excluded_pks = pks
            else:
                self.included_pks = pks
            return

        # We check for negation after lookup_type isnull because it
        # simplifies the code. All following lookup_type checks assume
        # that they're not negated.
        if lookup_type == 'isnull':
            if (negated and value) or not value:
                # TODO/XXX: Is everything greater than None?
                op = '>'
            else:
                op = '='
            value = None
        elif negated and lookup_type == 'exact':
            if self.has_negated_exact_filter:
                raise DatabaseError("You can't exclude more than one __exact "
                                    "filter.")
            self.has_negated_exact_filter = True
            self._combine_filters(field, (('<', value), ('>', value)))
            return
        elif negated:
            try:
                op = NEGATION_MAP[lookup_type]
            except KeyError:
                raise DatabaseError("Lookup type %r can't be negated." %
                                    lookup_type)
            if self.inequality_field and field != self.inequality_field:
                raise DatabaseError("Can't have inequality filters on "
                                    "multiple fields (here: %r and %r)." %
                                    (field, self.inequality_field))
            self.inequality_field = field
        elif lookup_type == 'in':
            # Create sub-query combinations, one for each value.
            if len(self.gae_query) * len(value) > 30:
                raise DatabaseError("You can't query against more than "
                                    "30 __in filter value combinations.")
            op_values = [('=', v) for v in value]
            self._combine_filters(field, op_values)
            return
        elif lookup_type == 'startswith':
            # Lookup argument was converted to [arg, arg + u'\ufffd'].
            self._add_filter(field, '>=', value[0])
            self._add_filter(field, '<=', value[1])
            return
        elif lookup_type in ('range', 'year'):
            self._add_filter(field, '>=', value[0])
            op = '<=' if lookup_type == 'range' else '<'
            self._add_filter(field, op, value[1])
            return
        else:
            op = OPERATORS_MAP[lookup_type]

        self._add_filter(field, op, value)

    # ----------------------------------------------
    # Internal API
    # ----------------------------------------------

    def _add_filter(self, field, op, value):
        for query in self.gae_query:

            # GAE uses a special property name for primary key filters.
            if field.primary_key:
                column = '__key__'
            else:
                column = field.column
            key = '%s %s' % (column, op)

            if isinstance(value, Text):
                raise DatabaseError("TextField is not indexed, by default, "
                                    "so you can't filter on it. Please add "
                                    "an index definition for the field %s "
                                    "on the model %s.%s as described here:\n"
                                    "http://www.allbuttonspressed.com/blog/django/2010/07/Managing-per-field-indexes-on-App-Engine" %
                                    (column, self.query.model.__module__,
                                     self.query.model.__name__))
            if key in query:
                existing_value = query[key]
                if isinstance(existing_value, list):
                    existing_value.append(value)
                else:
                    query[key] = [existing_value, value]
            else:
                query[key] = value

    def _combine_filters(self, field, op_values):
        gae_query = self.gae_query
        combined = []
        for query in gae_query:
            for op, value in op_values:
                self.gae_query = [Query(self.db_table,
                                        keys_only=self.pks_only)]
                self.gae_query[0].update(query)
                self._add_filter(field, op, value)
                combined.append(self.gae_query[0])
        self.gae_query = combined

    def _make_entity(self, entity):
        if isinstance(entity, Key):
            key = entity
            entity = {}
        else:
            key = entity.key()

        entity[self.query.get_meta().pk.column] = key
        return entity

    @safe_call
    def _build_query(self):
        for query in self.gae_query:
            query.Order(*self.ordering)
        if len(self.gae_query) > 1:
            return MultiQuery(self.gae_query, self.ordering)
        return self.gae_query[0]

    def get_matching_pk(self, low_mark=0, high_mark=None):
        if not self.included_pks:
            return []

        config = self.config.copy()

        # batch_size is not allowed for Gets
        if 'batch_size' in config:
            del config['batch_size']

        results = [result for result in Get(self.included_pks, **config)
                   if result is not None and
                       self.matches_filters(result)]
        if self.ordering:
            results.sort(cmp=self.order_pk_filtered)
        if high_mark is not None and high_mark < len(results) - 1:
            results = results[:high_mark]
        if low_mark:
            results = results[low_mark:]
        return results

    def order_pk_filtered(self, lhs, rhs):
        left = dict(lhs)
        left[self.query.get_meta().pk.column] = lhs.key().to_path()
        right = dict(rhs)
        right[self.query.get_meta().pk.column] = rhs.key().to_path()
        return self._order_in_memory(left, right)

    def matches_filters(self, entity):
        """
        Checks if the GAE entity fetched from the database satisfies
        the current query's constraints.
        """
        item = dict(entity)
        item[self.query.get_meta().pk.column] = entity.key()
        return self._matches_filters(item, self.query.where)


class SQLCompiler(NonrelCompiler):
    """
    Base class for all GAE compilers.
    """
    query_class = GAEQuery

    def as_sql(self, *args, **kwargs):
        sql, params = super(SQLCompiler, self).as_sql(*args, **kwargs)

        start_cursor = getattr(self.query, '_gae_start_cursor', None)
        end_cursor = getattr(self.query, '_gae_end_cursor', None)

        start_cursor_str = ''
        end_cursor_str = ''

        if start_cursor:
            start_cursor_str = Cursor.to_websafe_string(start_cursor)
        if end_cursor:
            end_cursor_str = Cursor.to_websafe_string(end_cursor)

        return '%s --cursor:%s,%s' % (sql, start_cursor_str, end_cursor_str), params

class SQLInsertCompiler(NonrelInsertCompiler, SQLCompiler):

    @safe_call
    def insert(self, data_list, return_id=False):
        opts = self.query.get_meta()
        unindexed_fields = get_model_indexes(self.query.model)['unindexed']
        unindexed_cols = [opts.get_field(name).column
                          for name in unindexed_fields]

        entity_list = []
        for data in data_list:
            properties = {}
            kwds = {'unindexed_properties': unindexed_cols}
            for column, value in data.items():
                # The value will already be a db.Key, but the Entity
                # constructor takes a name or id of the key, and will
                # automatically create a new key if neither is given.
                if column == opts.pk.column:
                    if value is not None:
                        kwds['id'] = value.id()
                        kwds['name'] = value.name()

                # GAE does not store empty lists (and even does not allow
                # passing empty lists to Entity.update) so skip them.
                elif isinstance(value, (tuple, list)) and not len(value):
                    continue

                # Use column names as property names.
                else:
                    properties[column] = value

            entity = Entity(opts.db_table, **kwds)
            entity.update(properties)
            entity_list.append(entity)

        keys = Put(entity_list)
        return keys[0] if isinstance(keys, list) else keys


class SQLUpdateCompiler(NonrelUpdateCompiler, SQLCompiler):

    def execute_sql(self, result_type=MULTI):
        # Modify query to fetch pks only and then execute the query
        # to get all pks.
        pk_field = self.query.model._meta.pk
        self.query.add_immediate_loading([pk_field.name])
        pks = [row for row in self.results_iter()]
        self.update_entities(pks, pk_field)
        return len(pks)

    def update_entities(self, pks, pk_field):
        for pk in pks:
            self.update_entity(pk[0], pk_field)

    @commit_locked
    def update_entity(self, pk, pk_field):
        gae_query = self.build_query()
        entity = Get(self.ops.value_for_db(pk, pk_field))

        if not gae_query.matches_filters(entity):
            return

        for field, _, value in self.query.values:
            if hasattr(value, 'prepare_database_save'):
                value = value.prepare_database_save(field)
            else:
                value = field.get_db_prep_save(value,
                                               connection=self.connection)

            if hasattr(value, 'evaluate'):
                assert not value.negated
                value = ExpressionEvaluator(value, self.query, entity,
                                            allow_joins=False)

            if hasattr(value, 'as_sql'):
                value = value.as_sql(lambda n: n, self.connection)

            entity[field.column] = self.ops.value_for_db(value, field)

        Put(entity)


class SQLDeleteCompiler(NonrelDeleteCompiler, SQLCompiler):
    pass


class SQLAggregateCompiler(NonrelAggregateCompiler, SQLCompiler):
    pass

class SQLDateCompiler(NonrelDateCompiler, SQLCompiler):
    pass

class SQLDateTimeCompiler(NonrelDateTimeCompiler, SQLCompiler):
    pass

########NEW FILE########
__FILENAME__ = creation
from djangotoolbox.db.creation import NonrelDatabaseCreation

from .db_settings import get_model_indexes
from .stubs import stub_manager


class DatabaseCreation(NonrelDatabaseCreation):

    # For TextFields and XMLFields we'll default to the unindexable,
    # but not length-limited, db.Text (db_type of "string" fields is
    # overriden indexed / unindexed fields).
    # GAE datastore cannot process sets directly, so we'll store them
    # as lists, it also can't handle dicts so we'll store DictField and
    # EmbeddedModelFields pickled as Blobs (pickled using the binary
    # protocol 2, even though they used to be serialized with the ascii
    # protocol 0 -- the deconversion is the same for both).
    data_types = dict(NonrelDatabaseCreation.data_types, **{
        'TextField':          'text',
        'XMLField':           'text',
        'SetField':           'list',
        'DictField':          'bytes',
        'EmbeddedModelField': 'bytes',
    })

    def db_type(self, field):
        """
        Provides a choice to continue using db.Key just for primary key
        storage or to use it for all references (ForeignKeys and other
        relations).

        We also force the "string" db_type (plain string storage) if a
        field is to be indexed, and the "text" db_type (db.Text) if
        it's registered as unindexed.
        """
        if self.connection.settings_dict.get('STORE_RELATIONS_AS_DB_KEYS'):
            if field.primary_key or field.rel is not None:
                return 'key'

        # Primary keys were processed as db.Keys; for related fields
        # the db_type of primary key of the referenced model was used,
        # but RelatedAutoField type was not defined and resulted in
        # "integer" being used for relations to models with AutoFields.
        # TODO: Check with Positive/SmallIntegerField primary keys.
        else:
            if field.primary_key:
                return 'key'
            if field.rel is not None:
                related_field = field.rel.get_related_field()
                if related_field.get_internal_type() == 'AutoField':
                    return 'integer'
                else:
                    return related_field.db_type(connection=self.connection)

        db_type = field.db_type(connection=self.connection)

        # Override db_type of "string" fields according to indexing.
        if db_type in ('string', 'text'):
            indexes = get_model_indexes(field.model)
            if field.attname in indexes['indexed']:
                return 'string'
            elif field.attname in indexes['unindexed']:
                return 'text'

        return db_type


    def _create_test_db(self, *args, **kw):
        self._had_test_stubs = stub_manager.active_stubs != 'test'
        if self._had_test_stubs:
            stub_manager.activate_test_stubs(self.connection)

    def _destroy_test_db(self, *args, **kw):
        if getattr(self, '_had_test_stubs', False):
            stub_manager.deactivate_test_stubs()
            stub_manager.setup_stubs(self.connection)
            del self._had_test_stubs

########NEW FILE########
__FILENAME__ = db_settings
from django.conf import settings
from django.utils.importlib import import_module

# TODO: Add autodiscover() and make API more like dbindexer's
#       register_index.

# TODO: Add support for eventual consistency setting on specific
#       models.


_MODULE_NAMES = getattr(settings, 'GAE_SETTINGS_MODULES', ())

FIELD_INDEXES = None


def get_model_indexes(model):
    indexes = get_indexes()
    model_index = {'indexed': [], 'unindexed': []}
    for item in reversed(model.mro()):
        config = indexes.get(item, {})
        model_index['indexed'].extend(config.get('indexed', ()))
        model_index['unindexed'].extend(config.get('unindexed', ()))
    return model_index


def get_indexes():
    global FIELD_INDEXES
    if FIELD_INDEXES is None:
        field_indexes = {}
        for name in _MODULE_NAMES:
            field_indexes.update(import_module(name).FIELD_INDEXES)
        FIELD_INDEXES = field_indexes
    return FIELD_INDEXES

########NEW FILE########
__FILENAME__ = expressions
import django
from django.db.models.sql.expressions import SQLEvaluator
from django.db.models.expressions import ExpressionNode

if django.VERSION >= (1, 5):
    ExpressionNode_BITAND = ExpressionNode.BITAND
    ExpressionNode_BITOR = ExpressionNode.BITOR

    def find_col_by_node(cols, node):
        col = None
        for n, c in cols:
            if n is node:
                col = c
                break
        return col

else:
    ExpressionNode_BITAND = ExpressionNode.AND
    ExpressionNode_BITOR = ExpressionNode.OR

    def find_col_by_node(cols, node):
        return cols[node]

OPERATION_MAP = {
    ExpressionNode.ADD: lambda x, y: x + y,
    ExpressionNode.SUB: lambda x, y: x - y,
    ExpressionNode.MUL: lambda x, y: x * y,
    ExpressionNode.DIV: lambda x, y: x / y,
    ExpressionNode.MOD: lambda x, y: x % y,
    ExpressionNode_BITAND: lambda x, y: x & y,
    ExpressionNode_BITOR:  lambda x, y: x | y,
}


class ExpressionEvaluator(SQLEvaluator):

    def __init__(self, expression, query, entity, allow_joins=True):
        super(ExpressionEvaluator, self).__init__(expression, query,
                                                  allow_joins)
        self.entity = entity

    ##################################################
    # Vistor methods for final expression evaluation #
    ##################################################

    def evaluate_node(self, node, qn, connection):
        values = []
        for child in node.children:
            if hasattr(child, 'evaluate'):
                value = child.evaluate(self, qn, connection)
            else:
                value = child

            if value is not None:
                values.append(value)

        return OPERATION_MAP[node.connector](*values)

    def evaluate_leaf(self, node, qn, connection):
        col = find_col_by_node(self.cols, node)
        if col is None:
            raise ValueError("Given node not found")
        return self.entity[qn(col[1])]

########NEW FILE########
__FILENAME__ = stubs
import logging
import os
import time
from urllib2 import HTTPError, URLError

from djangoappengine.boot import PROJECT_DIR
from djangoappengine.utils import appid, have_appserver


REMOTE_API_SCRIPTS = (
    '$PYTHON_LIB/google/appengine/ext/remote_api/handler.py',
    'google.appengine.ext.remote_api.handler.application',
)


def auth_func():
    import getpass
    return raw_input("Login via Google Account (see note above if login fails): "), getpass.getpass("Password: ")


def rpc_server_factory(*args, ** kwargs):
    from google.appengine.tools import appengine_rpc
    kwargs['save_cookies'] = True
    return appengine_rpc.HttpRpcServer(*args, ** kwargs)


class StubManager(object):

    def __init__(self):
        self.testbed = None
        self.active_stubs = None
        self.pre_test_stubs = None

    def setup_stubs(self, connection):
        if self.active_stubs is not None:
            return
        if not have_appserver:
            self.setup_local_stubs(connection)

    def activate_test_stubs(self, connection):
        if self.active_stubs == 'test':
            return

        os.environ['HTTP_HOST'] = "%s.appspot.com" % appid

        appserver_opts = connection.settings_dict.get('DEV_APPSERVER_OPTIONS', {})
        high_replication = appserver_opts.get('high_replication', False)
        require_indexes = appserver_opts.get('require_indexes', False)

        datastore_opts = {'require_indexes': require_indexes}

        if high_replication:
            from google.appengine.datastore import datastore_stub_util
            datastore_opts['consistency_policy'] = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=1)

        if self.testbed is None:
            from google.appengine.ext.testbed import Testbed
            self.testbed = Testbed()

        self.testbed.activate()
        self.pre_test_stubs = self.active_stubs
        self.active_stubs = 'test'
        self.testbed.init_datastore_v3_stub(root_path=PROJECT_DIR, **datastore_opts)
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub(auto_task_running=True, root_path=PROJECT_DIR)
        self.testbed.init_urlfetch_stub()
        self.testbed.init_user_stub()
        self.testbed.init_xmpp_stub()
        self.testbed.init_channel_stub()

    def deactivate_test_stubs(self):
        if self.active_stubs == 'test':
            self.testbed.deactivate()
            self.active_stubs = self.pre_test_stubs

    def setup_local_stubs(self, connection):
        if self.active_stubs == 'local':
            return
        from .base import get_datastore_paths
        from google.appengine.tools import dev_appserver_main
        args = dev_appserver_main.DEFAULT_ARGS.copy()
        args.update(get_datastore_paths(connection.settings_dict))
        args.update(connection.settings_dict.get('DEV_APPSERVER_OPTIONS', {}))
        log_level = logging.getLogger().getEffectiveLevel()
        logging.getLogger().setLevel(logging.WARNING)

        try:
            from google.appengine.tools import dev_appserver
        except ImportError:
            from google.appengine.tools import old_dev_appserver as dev_appserver
        dev_appserver.SetupStubs('dev~' + appid, **args)
        logging.getLogger().setLevel(log_level)
        self.active_stubs = 'local'

    def setup_remote_stubs(self, connection):
        if self.active_stubs == 'remote':
            return
        if not connection.remote_api_path:
            from ..utils import appconfig
            for handler in appconfig.handlers:
                if handler.script in REMOTE_API_SCRIPTS:
                    connection.remote_api_path = handler.url.split('(', 1)[0]
                    break
        server = '%s.%s' % (connection.remote_app_id, connection.domain)
        remote_url = 'https://%s%s' % (server, connection.remote_api_path)
        logging.info("Setting up remote_api for '%s' at %s." %
                     (connection.remote_app_id, remote_url))
        if not have_appserver:
            logging.info(
                "Connecting to remote_api handler.\n\n"
                "IMPORTANT: Check your login method settings in the "
                "App Engine Dashboard if you have problems logging in. "
                "Login is only supported for Google Accounts.")
        from google.appengine.ext.remote_api import remote_api_stub
        remote_api_stub.ConfigureRemoteApi(None,
            connection.remote_api_path, auth_func, servername=server,
            secure=connection.secure_remote_api,
            rpc_server_factory=rpc_server_factory)
        retry_delay = 1
        while retry_delay <= 16:
            try:
                remote_api_stub.MaybeInvokeAuthentication()
            except HTTPError, e:
                if not have_appserver:
                    logging.info("Retrying in %d seconds..." % retry_delay)
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                break
        else:
            try:
                remote_api_stub.MaybeInvokeAuthentication()
            except HTTPError, e:
                raise URLError("%s\n"
                               "Couldn't reach remote_api handler at %s.\n"
                               "Make sure you've deployed your project and "
                               "installed a remote_api handler in app.yaml. "
                               "Note that login is only supported for "
                               "Google Accounts. Make sure you've configured "
                               "the correct authentication method in the "
                               "App Engine Dashboard." % (e, remote_url))
        logging.info("Now using the remote datastore for '%s' at %s." %
                     (connection.remote_app_id, remote_url))
        self.active_stubs = 'remote'


stub_manager = StubManager()

########NEW FILE########
__FILENAME__ = utils
from django.db import DEFAULT_DB_ALIAS

from google.appengine.datastore.datastore_query import Cursor

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.3, 2.4 fallback.

class CursorQueryMixin(object):
    def clone(self, *args, **kwargs):
        kwargs['_gae_start_cursor'] = getattr(self, '_gae_start_cursor', None)
        kwargs['_gae_end_cursor'] = getattr(self, '_gae_end_cursor', None)
        kwargs['_gae_config'] = getattr(self, '_gae_config', None)
        return super(CursorQueryMixin, self).clone(*args, **kwargs)

def _add_mixin(queryset):
    if isinstance(queryset.query, CursorQueryMixin):
        return queryset

    queryset = queryset.all()

    class CursorQuery(CursorQueryMixin, queryset.query.__class__):
        pass

    queryset.query = queryset.query.clone(klass=CursorQuery)
    return queryset

def get_cursor(queryset):
    if not hasattr(queryset.query, '_gae_cursor'):
        # evaluate QuerySet only if there's no cursor set
        # this ensures that the query isn't run twice
        if queryset._result_cache is None:
            len(queryset)

    cursor = None
    if hasattr(queryset.query, '_gae_cursor'):
        cursor = queryset.query._gae_cursor()
    return Cursor.to_websafe_string(cursor) if cursor else None

def set_cursor(queryset, start=None, end=None):
    queryset = _add_mixin(queryset)

    if start is not None:
        start = Cursor.from_websafe_string(start)
        setattr(queryset.query, '_gae_start_cursor', start)
    if end is not None:
        end = Cursor.from_websafe_string(end)
        setattr(queryset.query, '_gae_end_cursor', end)

    return queryset

def get_config(queryset):
    return getattr(queryset.query, '_gae_config', None)

def set_config(queryset, **kwargs):
    queryset = _add_mixin(queryset)
    setattr(queryset.query, '_gae_config', kwargs)
    return queryset

def commit_locked(func_or_using=None, retries=None, xg=False, propagation=None):
    """
    Decorator that locks rows on DB reads.
    """

    def inner_commit_locked(func, using=None):

        def _commit_locked(*args, **kw):
            from google.appengine.api.datastore import RunInTransactionOptions
            from google.appengine.datastore.datastore_rpc import TransactionOptions

            option_dict = {}

            if retries:
                option_dict['retries'] = retries

            if xg:
                option_dict['xg'] = True

            if propagation:
                option_dict['propagation'] = propagation

            options = TransactionOptions(**option_dict)
            return RunInTransactionOptions(options, func, *args, **kw)

        return wraps(func)(_commit_locked)

    if func_or_using is None:
        func_or_using = DEFAULT_DB_ALIAS
    if callable(func_or_using):
        return inner_commit_locked(func_or_using, DEFAULT_DB_ALIAS)
    return lambda func: inner_commit_locked(func, func_or_using)

########NEW FILE########
__FILENAME__ = dbindexes
from django.conf import settings


if 'django.contrib.auth' in settings.INSTALLED_APPS:
    from dbindexer.api import register_index
    from django.contrib.auth.models import User

    register_index(User, {
        'username': 'iexact',
        'email': 'iexact',
    })

if 'django.contrib.admin' in settings.INSTALLED_APPS:
    from dbindexer.api import register_index
    from django.contrib.admin.models import LogEntry

    register_index(LogEntry, {
        'object_id': 'exact',
    })

########NEW FILE########
__FILENAME__ = handler
# Initialize Django.
from djangoappengine import main

from django.utils.importlib import import_module
from django.conf import settings


# Load all models.py to ensure signal handling installation or index
# loading of some apps
for app in settings.INSTALLED_APPS:
    try:
        import_module('%s.models' % (app))
    except ImportError:
        pass


from google.appengine.ext.deferred.handler import main
from google.appengine.ext.deferred.deferred import application


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = memcache
from google.appengine.api.memcache import *

########NEW FILE########
__FILENAME__ = mail
from email.MIMEBase import MIMEBase

from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail import EmailMultiAlternatives
from django.core.exceptions import ImproperlyConfigured

from google.appengine.api import mail as aeemail
from google.appengine.runtime import apiproxy_errors


def _send_deferred(message, fail_silently=False):
    try:
        message.send()
    except (aeemail.Error, apiproxy_errors.Error):
        if not fail_silently:
            raise


class EmailBackend(BaseEmailBackend):
    can_defer = False

    def send_messages(self, email_messages):
        num_sent = 0
        for message in email_messages:
            if self._send(message):
                num_sent += 1
        return num_sent

    def _copy_message(self, message):
        """
        Creates and returns App Engine EmailMessage class from message.
        """
        gmsg = aeemail.EmailMessage(sender=message.from_email,
                                    to=message.to,
                                    subject=message.subject,
                                    body=message.body)
        if message.extra_headers.get('Reply-To', None):
            gmsg.reply_to = message.extra_headers['Reply-To']
        if message.cc:
            gmsg.cc = list(message.cc)
        if message.bcc:
            gmsg.bcc = list(message.bcc)
        if message.attachments:
            # Must be populated with (filename, filecontents) tuples.
            attachments = []
            for attachment in message.attachments:
                if isinstance(attachment, MIMEBase):
                    attachments.append((attachment.get_filename(),
                                        attachment.get_payload(decode=True)))
                else:
                    attachments.append((attachment[0], attachment[1]))
            gmsg.attachments = attachments
        # Look for HTML alternative content.
        if isinstance(message, EmailMultiAlternatives):
            for content, mimetype in message.alternatives:
                if mimetype == 'text/html':
                    gmsg.html = content
                    break
        return gmsg

    def _send(self, message):
        try:
            message = self._copy_message(message)
        except (ValueError, aeemail.InvalidEmailError), err:
            import logging
            logging.warn(err)
            if not self.fail_silently:
                raise
            return False
        if self.can_defer:
            self._defer_message(message)
            return True
        try:
            message.send()
        except (aeemail.Error, apiproxy_errors.Error):
            if not self.fail_silently:
                raise
            return False
        return True

    def _defer_message(self, message):
        from google.appengine.ext import deferred
        from django.conf import settings
        queue_name = getattr(settings, 'EMAIL_QUEUE_NAME', 'default')
        deferred.defer(_send_deferred,
                       message,
                       fail_silently=self.fail_silently,
                       _queue=queue_name)


class AsyncEmailBackend(EmailBackend):
    can_defer = True

########NEW FILE########
__FILENAME__ = main
# Python 2.5 CGI handler.
import os
import sys

from djangoappengine.main import application
from google.appengine.ext.webapp.util import run_wsgi_app

from djangoappengine.boot import setup_logging, env_ext
from django.conf import settings


path_backup = None

def real_main():
    # Reset path and environment variables.
    global path_backup
    try:
        sys.path = path_backup[:]
    except:
        path_backup = sys.path[:]
    os.environ.update(env_ext)
    setup_logging()

    # Run the WSGI CGI handler with that application.
    run_wsgi_app(application)


def profile_main(func):
    from cStringIO import StringIO
    import cProfile
    import logging
    import pstats
    import random
    only_forced_profile = getattr(settings, 'ONLY_FORCED_PROFILE', False)
    profile_percentage = getattr(settings, 'PROFILE_PERCENTAGE', None)
    if (only_forced_profile and
                'profile=forced' not in os.environ.get('QUERY_STRING')) or \
            (not only_forced_profile and profile_percentage and
                float(profile_percentage) / 100.0 <= random.random()):
        return func()

    prof = cProfile.Profile()
    prof = prof.runctx('func()', globals(), locals())
    stream = StringIO()
    stats = pstats.Stats(prof, stream=stream)
    sort_by = getattr(settings, 'SORT_PROFILE_RESULTS_BY', 'time')
    if not isinstance(sort_by, (list, tuple)):
        sort_by = (sort_by,)
    stats.sort_stats(*sort_by)

    restrictions = []
    profile_pattern = getattr(settings, 'PROFILE_PATTERN', None)
    if profile_pattern:
        restrictions.append(profile_pattern)
    max_results = getattr(settings, 'MAX_PROFILE_RESULTS', 80)
    if max_results and max_results != 'all':
        restrictions.append(max_results)
    stats.print_stats(*restrictions)
    extra_output = getattr(settings, 'EXTRA_PROFILE_OUTPUT', None) or ()
    if not isinstance(sort_by, (list, tuple)):
        extra_output = (extra_output,)
    if 'callees' in extra_output:
        stats.print_callees()
    if 'callers' in extra_output:
        stats.print_callers()
    logging.info("Profile data:\n%s.", stream.getvalue())


def make_profileable(func):
    if getattr(settings, 'ENABLE_PROFILER', False):
        return lambda: profile_main(func)
    return func

main = make_profileable(real_main)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = deploy
import logging
import time
import sys

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from ...boot import PROJECT_DIR
from ...utils import appconfig


PRE_DEPLOY_COMMANDS = ()
if 'mediagenerator' in settings.INSTALLED_APPS:
    PRE_DEPLOY_COMMANDS += ('generatemedia',)
PRE_DEPLOY_COMMANDS = getattr(settings, 'PRE_DEPLOY_COMMANDS',
                              PRE_DEPLOY_COMMANDS)
POST_DEPLOY_COMMANDS = getattr(settings, 'POST_DEPLOY_COMMANDS', ())


def run_appcfg(argv):
    # We don't really want to use that one though, it just executes
    # this one.
    from google.appengine.tools import appcfg

    # Reset the logging level to WARN as appcfg will spew tons of logs
    # on INFO.
    logging.getLogger().setLevel(logging.WARN)

    new_args = argv[:]
    new_args[1] = 'update'
    if appconfig.runtime != 'python':
        new_args.insert(1, '-R')
    new_args.append(PROJECT_DIR)
    syncdb = True
    if '--nosyncdb' in new_args:
        syncdb = False
        new_args.remove('--nosyncdb')
    appcfg.main(new_args)

    if syncdb:
        print "Running syncdb."
        # Wait a little bit for deployment to finish.
        for countdown in range(9, 0, -1):
            sys.stdout.write('%s\r' % countdown)
            time.sleep(1)
        from django.db import connections
        for connection in connections.all():
            if hasattr(connection, 'setup_remote'):
                connection.setup_remote()
        call_command('syncdb', remote=True, interactive=True)

    if getattr(settings, 'ENABLE_PROFILER', False):
        print "--------------------------\n" \
              "WARNING: PROFILER ENABLED!\n" \
              "--------------------------"


class Command(BaseCommand):
    """
    Deploys the website to the production server.

    Any additional arguments are passed directly to appcfg.py update.
    """
    help = "Calls appcfg.py update for the current project."
    args = "[any appcfg.py options]"

    def run_from_argv(self, argv):
        for command in PRE_DEPLOY_COMMANDS:
            call_command(command)
        try:
            run_appcfg(argv)
        finally:
            for command in POST_DEPLOY_COMMANDS:
                call_command(command)

########NEW FILE########
__FILENAME__ = remote
from django.core.management import execute_from_command_line
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Runs a command with access to the remote App Engine production " \
           "server (e.g. manage.py remote shell)."
    args = "remotecommand"

    def run_from_argv(self, argv):
        from django.db import connections
        from ...db.base import DatabaseWrapper
        from ...db.stubs import stub_manager
        for connection in connections.all():
            if isinstance(connection, DatabaseWrapper):
                stub_manager.setup_remote_stubs(connection)
                break
        argv = argv[:1] + argv[2:]
        execute_from_command_line(argv)

########NEW FILE########
__FILENAME__ = runserver
import logging
from optparse import make_option
import sys

from django.db import connections
from django.core.management.base import BaseCommand
from django.core.management.commands.runserver import BaseRunserverCommand
from django.core.exceptions import ImproperlyConfigured

from google.appengine.tools import dev_appserver_main

from ...boot import PROJECT_DIR
from ...db.base import DatabaseWrapper, get_datastore_paths


class Command(BaseRunserverCommand):
    """
    Overrides the default Django runserver command.

    Instead of starting the default Django development server this
    command fires up a copy of the full fledged App Engine
    dev_appserver that emulates the live environment your application
    will be deployed to.
    """

    option_list = BaseCommand.option_list + (
        make_option(
            '--debug', action='store_true', default=False,
            help="Prints verbose debugging messages to the console while " \
                 "running."),
        make_option(
            '--debug_imports', action='store_true', default=False,
            help="Prints debugging messages related to importing modules, " \
                 "including search paths and errors."),
        make_option(
            '-c', '--clear_datastore', action='store_true', default=False,
            help="Clears the datastore data and history files before " \
                 "starting the web server."),
        make_option(
            '--high_replication', action='store_true', default=False,
            help='Use the high replication datastore consistency model.'),
        make_option(
            '--require_indexes', action='store_true', default=False,
            help="Disables automatic generation of entries in the " \
                 "index.yaml file. Instead, when the application makes a " \
                 "query that requires that its index be defined in the file " \
                 "and the index definition is not found, an exception will " \
                 "be raised, similar to what would happen when running on " \
                 "App Engine."),
        make_option(
            '--enable_sendmail', action='store_true', default=False,
            help="Uses the local computer's Sendmail installation for " \
                 "sending email messages."),
        make_option(
            '--datastore_path',
            help="The path to use for the local datastore data file. " \
                 "The server creates this file if it does not exist."),
        make_option(
            '--blobstore_path',
            help="The path to use for the local blob data directory. " \
                 "The server creates this directory if it does not exist."),
        make_option(
            '--history_path',
            help="The path to use for the local datastore history file. " \
                 "The server uses the query history file to generate " \
                 "entries for index.yaml."),
        make_option(
            '--login_url',
            help="The relative URL to use for the Users sign-in page. " \
                 "Default is /_ah/login."),
        make_option(
            '--smtp_host',
            help="The hostname of the SMTP server to use for sending email " \
                 "messages."),
        make_option(
            '--smtp_port',
            help="The port number of the SMTP server to use for sending " \
                 "email messages."),
        make_option(
            '--smtp_user',
            help="The username to use with the SMTP server for sending " \
                 "email messages."),
        make_option(
            '--smtp_password',
            help="The password to use with the SMTP server for sending " \
                 "email messages."),
        make_option(
            '--use_sqlite', action='store_true', default=False,
            help="Use the new, SQLite datastore stub."),
        make_option(
            '--allow_skipped_files', action='store_true', default=False,
            help="Allow access to files listed in skip_files."),
        make_option(
            '--disable_task_running', action='store_true', default=False,
            help="When supplied, tasks will not be automatically run after " \
                 "submission and must be run manually in the local admin " \
                 "console."),
    )

    help = "Runs a copy of the App Engine development server."
    args = "[optional port number, or ipaddr:port]"

    def create_parser(self, prog_name, subcommand):
        """
        Creates and returns the ``OptionParser`` which will be used to
        parse the arguments to this command.
        """
        # Hack __main__ so --help in dev_appserver_main works OK.
        sys.modules['__main__'] = dev_appserver_main
        return super(Command, self).create_parser(prog_name, subcommand)

    def run_from_argv(self, argv):
        """
        Captures the program name, usually "manage.py".
        """
        self.progname = argv[0]
        super(Command, self).run_from_argv(argv)

    def run(self, *args, **options):
        """
        Starts the App Engine dev_appserver program for the Django
        project. The appserver is run with default parameters. If you
        need to pass any special parameters to the dev_appserver you
        will have to invoke it manually.

        Unlike the normal devserver, does not use the autoreloader as
        App Engine dev_appserver needs to be run from the main thread
        """

        args = []
        # Set bind ip/port if specified.
        if self.addr:
            args.extend(['--address', self.addr])
        if self.port:
            args.extend(['--port', self.port])

        # If runserver is called using handle(), progname will not be
        # set.
        if not hasattr(self, 'progname'):
            self.progname = 'manage.py'

        # Add email settings.
        from django.conf import settings
        if not options.get('smtp_host', None) and \
           not options.get('enable_sendmail', None):
            args.extend(['--smtp_host', settings.EMAIL_HOST,
                         '--smtp_port', str(settings.EMAIL_PORT),
                         '--smtp_user', settings.EMAIL_HOST_USER,
                         '--smtp_password', settings.EMAIL_HOST_PASSWORD])

        # Pass the application specific datastore location to the
        # server.
        preset_options = {}
        for name in connections:
            connection = connections[name]
            if isinstance(connection, DatabaseWrapper):
                for key, path in get_datastore_paths(
                        connection.settings_dict).items():
                    # XXX/TODO: Remove this when SDK 1.4.3 is released.
                    if key == 'prospective_search_path':
                        continue

                    arg = '--' + key
                    if arg not in args:
                        args.extend([arg, path])
                # Get dev_appserver option presets, to be applied below.
                preset_options = connection.settings_dict.get(
                    'DEV_APPSERVER_OPTIONS', {})
                break

        # Process the rest of the options here.
        bool_options = [
            'debug', 'debug_imports', 'clear_datastore', 'require_indexes',
            'high_replication', 'enable_sendmail', 'use_sqlite',
            'allow_skipped_files', 'disable_task_running', ]
        for opt in bool_options:
            if options[opt] != False:
                args.append('--%s' % opt)

        str_options = [
            'datastore_path', 'blobstore_path', 'history_path', 'login_url', 'smtp_host',
            'smtp_port', 'smtp_user', 'smtp_password', ]
        for opt in str_options:
            if options.get(opt, None) != None:
                args.extend(['--%s' % opt, options[opt]])

        # Fill any non-overridden options with presets from settings.
        for opt, value in preset_options.items():
            arg = '--%s' % opt
            if arg not in args:
                if value and opt in bool_options:
                    args.append(arg)
                elif opt in str_options:
                    args.extend([arg, value])
                # TODO: Issue warning about bogus option key(s)?

        # Reset logging level to INFO as dev_appserver will spew tons
        # of debug logs.
        logging.getLogger().setLevel(logging.INFO)

        # Append the current working directory to the arguments.
        dev_appserver_main.main([self.progname] + args + [PROJECT_DIR])

########NEW FILE########
__FILENAME__ = testserver
from django.core.management.base import BaseCommand

from google.appengine.api import apiproxy_stub_map
from google.appengine.datastore import datastore_stub_util

from optparse import make_option

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help='Tells Django to NOT prompt the user for input of any kind.'),
        make_option('--addrport', action='store', dest='addrport',
            type='string', default='',
            help='port number or ipaddr:port to run the server on'),
        make_option('--ipv6', '-6', action='store_true', dest='use_ipv6', default=False,
            help='Tells Django to use a IPv6 address.'),
    )
    help = 'Runs a development server with data from the given fixture(s).'
    args = '[fixture ...]'

    requires_model_validation = False

    def handle(self, *fixture_labels, **options):
        from django.core.management import call_command
        from django import db
        from ...db.base import get_datastore_paths, DatabaseWrapper
        from ...db.stubs import stub_manager

        verbosity = int(options.get('verbosity'))
        interactive = options.get('interactive')
        addrport = options.get('addrport')

        db_name = None

        for name in db.connections:
            conn = db.connections[name]
            if isinstance(conn, DatabaseWrapper):
                settings = conn.settings_dict
                for key, path in get_datastore_paths(settings).items():
                    settings[key] = "%s-testdb" % path
                conn.flush()

                # reset stub manager
                stub_manager.active_stubs = None
                stub_manager.setup_local_stubs(conn)

                db_name = name
                break

        # Temporarily change consistency policy to force apply loaded data
        datastore = apiproxy_stub_map.apiproxy.GetStub('datastore_v3')

        orig_consistency_policy = datastore._consistency_policy
        datastore.SetConsistencyPolicy(datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=1))

        # Import the fixture data into the test database.
        call_command('loaddata', *fixture_labels, **{'verbosity': verbosity})

        # reset original policy
        datastore.SetConsistencyPolicy(orig_consistency_policy)

        # Run the development server. Turn off auto-reloading because it causes
        # a strange error -- it causes this handle() method to be called
        # multiple times.
        shutdown_message = '\nServer stopped.\nNote that the test database, %r, has not been deleted. You can explore it on your own.' % db_name
        call_command('runserver', addrport=addrport, shutdown_message=shutdown_message, use_reloader=False, use_ipv6=options['use_ipv6'])

########NEW FILE########
__FILENAME__ = handler
# Initialize Django.
from djangoappengine import main
from django.utils.importlib import import_module
from django.conf import settings

# Load all models.py to ensure signal handling installation or index
# loading of some apps.
for app in settings.INSTALLED_APPS:
    try:
        import_module('%s.models' % app)
    except ImportError:
        pass

try:
    from mapreduce.main import APP as application, main
except ImportError:
    from google.appengine.ext.mapreduce.main import APP as application, main


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = input_readers
from djangoappengine.db.utils import get_cursor, set_cursor, set_config

from google.appengine.api.datastore import Key

from mapreduce.datastore_range_iterators import AbstractKeyRangeIterator, _KEY_RANGE_ITERATORS
from mapreduce.input_readers import AbstractDatastoreInputReader, _get_params, BadReaderParamsError
from mapreduce import util

class DjangoModelIterator(AbstractKeyRangeIterator):
    def __iter__(self):
        k_range = self._key_range

        # Namespaces are not supported by djangoappengine
        if k_range.namespace:
            return

        model_class = util.for_name(self._query_spec.model_class_path)

        q = model_class.objects.all()

        if k_range.key_start:
            if k_range.include_start:
                q = q.filter(pk__gte=k_range.key_start.id_or_name())
            else:
                q = q.filter(pk__gt=k_range.key_start.id_or_name())

        if k_range.key_end:
            if k_range.include_end:
                q = q.filter(pk__lte=k_range.key_end.id_or_name())
            else:
                q = q.filter(pk__lt=k_range.key_end.id_or_name())

        q = q.order_by('pk')

        q = set_config(q, batch_size=self._query_spec.batch_size)

        if self._cursor:
            q = set_cursor(q, self._cursor)

        self._query = q

        for entity in self._query.iterator():
            yield entity

    def _get_cursor(self):
        if self._query is not None:
            return get_cursor(self._query)

_KEY_RANGE_ITERATORS[DjangoModelIterator.__name__] = DjangoModelIterator

class DjangoModelInputReader(AbstractDatastoreInputReader):
    """
    An input reader that takes a Django model ('app.models.Model')
    and yields Django model instances

    Note: This ignores all entities not in the default namespace.
    """

    _KEY_RANGE_ITER_CLS = DjangoModelIterator

    @classmethod
    def _get_raw_entity_kind(cls, entity_kind):
        """Returns an datastore entity kind from a Django model."""
        model_class = util.for_name(entity_kind)
        return model_class._meta.db_table

    @classmethod
    def validate(cls, mapper_spec):
        super(DjangoModelInputReader, cls).validate(mapper_spec)

        params = _get_params(mapper_spec)

        if cls.NAMESPACE_PARAM in params:
            raise BadReaderParamsError("Namespaces are not supported.")

        entity_kind_name = params[cls.ENTITY_KIND_PARAM]
        try:
            util.for_name(entity_kind_name)
        except ImportError, e:
            raise BadReaderParamsError("Bad entity kind: %s" % e)

########NEW FILE########
__FILENAME__ = pipeline
from mapreduce import mapper_pipeline
from mapreduce import mapreduce_pipeline

def _convert_func_to_string(func):
    return '%s.%s' % (func.__module__, func.__name__)

def _convert_model_to_string(model):
    return '%s.%s' % (model.__module__, model.__name__)

def DjangoModelMapreduce(model,
                         mapper,
                         reducer,
                         keys_only=False,
                         output_writer="mapreduce.output_writers.BlobstoreOutputWriter",
                         extra_mapper_params=None,
                         extra_reducer_params=None,
                         shards=None):
    """
    A simple wrapper function for creating mapreduce jobs over a Django model.

    Args:
        model:  A Django model class
        mapper: A top-level function that takes a single argument,
            and yields zero or many two-tuples strings
        reducer: A top-level function that takes two arguments
            and yields zero or more values
        output_writer: An optional OutputWriter subclass name,
            defaults to 'mapreduce.output_writers.BlobstoreOutputWriter'
        extra_mapper_params: An optional dictionary of values to pass to the Mapper
        extra_reducer_params: An optional dictionary of values to pass to the Reducer
    """

    if keys_only:
        input_reader_spec = "mapreduce.input_readers.DatastoreKeyInputReader"
        mapper_params = { "entity_kind": model._meta.db_table }
    else:
        input_reader_spec = "djangoappengine.mapreduce.input_readers.DjangoModelInputReader"
        mapper_params = { "entity_kind": _convert_model_to_string(model) }

    if extra_mapper_params:
        mapper_params.update(extra_mapper_params)

    reducer_params = { "mime_type": "text/plain" }
    if extra_reducer_params:
        reducer_params.update(extra_reducer_params)

    mapper_spec = _convert_func_to_string(mapper)
    reducer_spec = _convert_func_to_string(reducer)

    return mapreduce_pipeline.MapreducePipeline(
        "%s-%s-%s-mapreduce" % (model._meta.object_name, mapper_spec, reducer_spec),
        mapper_spec,
        reducer_spec,
        input_reader_spec,
        output_writer,
        mapper_params=mapper_params,
        reducer_params=reducer_params,
        shards=shards)

def DjangoModelMap(model,
                   mapper_func,
                   keys_only=False,
                   output_writer="mapreduce.output_writers.BlobstoreOutputWriter",
                   params=None):
    """
    A simple wrapper function for running a mapper function over Django model instances.

    Args:
        model:  A Django model class
        mapper: A top-level function that takes a single argument,
            and yields zero or many two-tuples strings
        keys_only: Selects which input reader to use
            if True, then we use 'mapreduce.input_readers.DatastoreKeyInputReader',
            if False, then 'djangoappengine.mapreduce.input_readers.DjangoModelInputReader',
            defaults to False
        params: An optional dictionary of values to pass to the Mapper
    """

    if keys_only:
        input_reader_spec = "mapreduce.input_readers.DatastoreKeyInputReader"
        mapper_params = { "entity_kind": model._meta.db_table, "mime_type": "text/plain" }
    else:
        input_reader_spec = "djangoappengine.mapreduce.input_readers.DjangoModelInputReader"
        mapper_params = { "entity_kind": _convert_model_to_string(model), "mime_type": "text/plain" }

    if params:
        mapper_params.update(params)

    mapper_spec = _convert_func_to_string(mapper_func)

    return mapper_pipeline.MapperPipeline(
        "%s-%s-mapper" % (model._meta.object_name, mapper_spec),
        mapper_spec,
        input_reader_spec,
        output_writer_spec=output_writer,
        params=mapper_params)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = settings_base
# Initialize App Engine SDK if necessary.
try:
    from google.appengine.api import apiproxy_stub_map
except ImportError:
    from .boot import setup_env
    setup_env()

from djangoappengine.utils import on_production_server, have_appserver


DEBUG = not on_production_server
TEMPLATE_DEBUG = DEBUG

ROOT_URLCONF = 'urls'

DATABASES = {
    'default': {
        'ENGINE': 'djangoappengine.db',

        # Other settings which you might want to override in your
        # settings.py.

        # Activates high-replication support for remote_api.
        # 'HIGH_REPLICATION': True,

        # Switch to the App Engine for Business domain.
        # 'DOMAIN': 'googleplex.com',

        # Store db.Keys as values of ForeignKey or other related
        # fields. Warning: dump your data before, and reload it after
        # changing! Defaults to False if not set.
        # 'STORE_RELATIONS_AS_DB_KEYS': True,

        'DEV_APPSERVER_OPTIONS': {
            'use_sqlite': True,

            # Optional parameters for development environment.

            # Emulate the high-replication datastore locally.
            # TODO: Likely to break loaddata (some records missing).
            # 'high_replication' : True,

            # Setting to True will trigger exceptions if a needed index is missing
            # Setting to False will auto-generated index.yaml file
            # 'require_indexes': True,
        },
    },
}

if on_production_server:
    EMAIL_BACKEND = 'djangoappengine.mail.AsyncEmailBackend'
else:
    EMAIL_BACKEND = 'djangoappengine.mail.EmailBackend'

# Specify a queue name for the async. email backend.
EMAIL_QUEUE_NAME = 'default'

PREPARE_UPLOAD_BACKEND = 'djangoappengine.storage.prepare_upload'
SERVE_FILE_BACKEND = 'djangoappengine.storage.serve_file'
DEFAULT_FILE_STORAGE = 'djangoappengine.storage.BlobstoreStorage'
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
FILE_UPLOAD_HANDLERS = (
    'djangoappengine.storage.BlobstoreFileUploadHandler',
    'django.core.files.uploadhandler.MemoryFileUploadHandler',
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'TIMEOUT': 0,
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

if not on_production_server:
    INTERNAL_IPS = ('127.0.0.1',)

########NEW FILE########
__FILENAME__ = storage
import mimetypes
import os
import urlparse

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import Storage
from django.core.files.uploadedfile import UploadedFile
from django.core.files.uploadhandler import FileUploadHandler, \
    StopFutureHandlers
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.utils.encoding import smart_str, force_unicode, filepath_to_uri

from google.appengine.api import files
from google.appengine.api.images import get_serving_url, NotImageError, \
    TransformationError, BlobKeyRequiredError
from google.appengine.ext.blobstore import BlobInfo, BlobKey, delete, \
    create_upload_url, BLOB_KEY_HEADER, BLOB_RANGE_HEADER, BlobReader


def prepare_upload(request, url, **kwargs):
    return create_upload_url(url), {}


def serve_file(request, file, save_as, content_type, **kwargs):
    if hasattr(file, 'file') and hasattr(file.file, 'blobstore_info'):
        blobkey = file.file.blobstore_info.key()
    elif hasattr(file, 'blobstore_info'):
        blobkey = file.blobstore_info.key()
    else:
        raise ValueError("The provided file can't be served via the "
                         "Google App Engine Blobstore.")
    response = HttpResponse(content_type=content_type)
    response[BLOB_KEY_HEADER] = str(blobkey)
    response['Accept-Ranges'] = 'bytes'
    http_range = request.META.get('HTTP_RANGE')
    if http_range is not None:
        response[BLOB_RANGE_HEADER] = http_range
    if save_as:
        response['Content-Disposition'] = smart_str(
            u'attachment; filename=%s' % save_as)
    if file.size is not None:
        response['Content-Length'] = file.size
    return response


class BlobstoreStorage(Storage):
    """Google App Engine Blobstore storage backend."""

    def _open(self, name, mode='rb'):
        return BlobstoreFile(name, mode, self)

    def _save(self, name, content):
        name = name.replace('\\', '/')
        if hasattr(content, 'file') and \
           hasattr(content.file, 'blobstore_info'):
            data = content.file.blobstore_info
        elif hasattr(content, 'blobstore_info'):
            data = content.blobstore_info
        elif isinstance(content, File):
            guessed_type = mimetypes.guess_type(name)[0]
            file_name = files.blobstore.create(mime_type=guessed_type or 'application/octet-stream',
                                               _blobinfo_uploaded_filename=name)

            with files.open(file_name, 'a') as f:
                for chunk in content.chunks():
                    f.write(chunk)

            files.finalize(file_name)

            data = files.blobstore.get_blob_key(file_name)
        else:
            raise ValueError("The App Engine storage backend only supports "
                             "BlobstoreFile instances or File instances.")

        if isinstance(data, (BlobInfo, BlobKey)):
            # We change the file name to the BlobKey's str() value.
            if isinstance(data, BlobInfo):
                data = data.key()
            return '%s/%s' % (data, name.lstrip('/'))
        else:
            raise ValueError("The App Engine Blobstore only supports "
                             "BlobInfo values. Data can't be uploaded "
                             "directly. You have to use the file upload "
                             "handler.")

    def delete(self, name):
        delete(self._get_key(name))

    def exists(self, name):
        return self._get_blobinfo(name) is not None

    def size(self, name):
        return self._get_blobinfo(name).size

    def url(self, name):
        try:
            return get_serving_url(self._get_blobinfo(name))
        except (NotImageError, TransformationError):
            return None

    def created_time(self, name):
        return self._get_blobinfo(name).creation

    def get_valid_name(self, name):
        return force_unicode(name).strip().replace('\\', '/')

    def get_available_name(self, name):
        return name.replace('\\', '/')

    def _get_key(self, name):
        return BlobKey(name.split('/', 1)[0])

    def _get_blobinfo(self, name):
        return BlobInfo.get(self._get_key(name))

class DevBlobstoreStorage(BlobstoreStorage):
    def url(self, name):
        try:
            return super(DevBlobstoreStorage, self).url(name)
        except BlobKeyRequiredError:
            return urlparse.urljoin(settings.MEDIA_URL, filepath_to_uri(name))

class BlobstoreFile(File):

    def __init__(self, name, mode, storage):
        self.name = name
        self._storage = storage
        self._mode = mode
        self.blobstore_info = storage._get_blobinfo(name)

    @property
    def size(self):
        return self.blobstore_info.size

    def write(self, content):
        raise NotImplementedError()

    @property
    def file(self):
        if not hasattr(self, '_file'):
            self._file = BlobReader(self.blobstore_info.key())
        return self._file


class BlobstoreFileUploadHandler(FileUploadHandler):
    """
    File upload handler for the Google App Engine Blobstore.
    """

    def new_file(self, *args, **kwargs):
        super(BlobstoreFileUploadHandler, self).new_file(*args, **kwargs)
        blobkey = self.content_type_extra.get('blob-key')
        self.active = blobkey is not None
        if self.active:
            self.blobkey = BlobKey(blobkey)
            raise StopFutureHandlers()

    def receive_data_chunk(self, raw_data, start):
        """
        Add the data to the StringIO file.
        """
        if not self.active:
            return raw_data

    def file_complete(self, file_size):
        """
        Return a file object if we're activated.
        """
        if not self.active:
            return

        return BlobstoreUploadedFile(
            blobinfo=BlobInfo(self.blobkey),
            charset=self.charset)


class BlobstoreUploadedFile(UploadedFile):
    """
    A file uploaded into memory (i.e. stream-to-memory).
    """

    def __init__(self, blobinfo, charset):
        super(BlobstoreUploadedFile, self).__init__(
            BlobReader(blobinfo.key()), blobinfo.filename,
            blobinfo.content_type, blobinfo.size, charset)
        self.blobstore_info = blobinfo

    def open(self, mode=None):
        pass

    def chunks(self, chunk_size=1024 * 128):
        self.file.seek(0)
        while True:
            content = self.read(chunk_size)
            if not content:
                break
            yield content

    def multiple_chunks(self, chunk_size=1024 * 128):
        return True

########NEW FILE########
__FILENAME__ = models
from django.db import models

from djangotoolbox.fields import BlobField

from ..db.db_settings import get_indexes


class EmailModel(models.Model):
    email = models.EmailField()
    number = models.IntegerField(null=True)


class DateTimeModel(models.Model):
    datetime = models.DateTimeField()
    datetime_auto_now = models.DateTimeField(auto_now=True)
    datetime_auto_now_add = models.DateTimeField(auto_now_add=True)


class FieldsWithoutOptionsModel(models.Model):
    datetime = models.DateTimeField()
    date = models.DateField()
    time = models.TimeField()
    floating_point = models.FloatField()
    boolean = models.BooleanField(default=False)
    null_boolean = models.NullBooleanField()
    text = models.CharField(max_length=32)
    email = models.EmailField()
    comma_seperated_integer = models.CommaSeparatedIntegerField(max_length=10)
    ip_address = models.IPAddressField()
    slug = models.SlugField()
    url = models.URLField()
#    file = models.FileField()
#    file_path = models.FilePathField()
    long_text = models.TextField()
    indexed_text = models.TextField()
    integer = models.IntegerField()
    small_integer = models.SmallIntegerField()
    positive_integer = models.PositiveIntegerField()
    positive_small_integer = models.PositiveSmallIntegerField()
#    foreign_key = models.ForeignKey('FieldsWithOptionsModel')
#    foreign_key = models.ForeignKey('OrderedModel')
#    one_to_one = models.OneToOneField()
#    decimal = models.DecimalField() # can be None
#    image = models.ImageField()

get_indexes()[FieldsWithoutOptionsModel] = {'indexed': ('indexed_text',)}


class FieldsWithOptionsModel(models.Model):
    # Any type of unique (unique_data, ...) is not supported on GAE,
    # instead you can use primary_key=True for some special cases. But
    # be carefull: changing the  primary_key of an entity will not
    # result in an updated entity, instead a new entity will be putted
    # into the datastore. The old one will not be deleted and all
    # references pointing to the old entitiy will not point to the new
    # one either.
    datetime = models.DateTimeField(auto_now=True, db_column='birthday')
    date = models.DateField(auto_now_add=True)
    time = models.TimeField()
    floating_point = models.FloatField(null=True)
    boolean = models.BooleanField(default=False)
    null_boolean = models.NullBooleanField(default=True)
    text = models.CharField(default='Hallo', max_length=10)
    email = models.EmailField(default='app-engine@scholardocs.com',
                              primary_key=True)
    comma_seperated_integer = models.CommaSeparatedIntegerField(max_length=10)
    ip_address = models.IPAddressField(default='192.168.0.2')
    slug = models.SlugField(default='GAGAA', null=True)
    url = models.URLField(default='http://www.scholardocs.com')
#    file = FileField()
#    file_path = FilePathField()
    long_text = models.TextField(default=1000 * 'A')
    integer = models.IntegerField(default=100)
    small_integer = models.SmallIntegerField(default=-5)
    positive_integer = models.PositiveIntegerField(default=80)
    positive_small_integer = models.PositiveSmallIntegerField(default=3,
                                                              null=True)
    foreign_key = models.ForeignKey('OrderedModel', null=True,
                                    related_name='keys')
#    one_to_one = OneToOneField()
#    decimal = DecimalField()
#    image = ImageField()


class OrderedModel(models.Model):
    id = models.IntegerField(primary_key=True)
    priority = models.IntegerField()

    class Meta:
        ordering = ('-priority',)


class BlobModel(models.Model):
    data = BlobField()


class SelfReferenceModel(models.Model):
    ref = models.ForeignKey('self', null=True)


class NullableTextModel(models.Model):
    text = models.TextField(null=True)

########NEW FILE########
__FILENAME__ = test_backend
from django.db import models
from django.db.utils import DatabaseError
from django.test import TestCase


class A(models.Model):
    value = models.IntegerField()


class B(A):
    other = models.IntegerField()


class BackendTest(TestCase):

    def test_model_forms(self):
        from django import forms

        class F(forms.ModelForm):

            class Meta:
                model = A

        F({'value': '3'}).save()

    def test_multi_table_inheritance(self):
        B(value=3, other=5).save()
        self.assertEqual(A.objects.count(), 1)
        self.assertEqual(A.objects.all()[0].value, 3)
        self.assertRaises(DatabaseError, B.objects.count)
        self.assertRaises(DatabaseError, lambda: B.objects.all()[0])

########NEW FILE########
__FILENAME__ = test_field_db_conversion
import datetime

from django.test import TestCase

from google.appengine.api.datastore import Get
from google.appengine.api.datastore_types import Text, Category, Email, \
    Link, PhoneNumber, PostalAddress, Text, Blob, ByteString, GeoPt, IM, \
    Key, Rating, BlobKey

from .models import FieldsWithoutOptionsModel

# TODO: Add field conversions for ForeignKeys?


class FieldDBConversionTest(TestCase):

    def test_db_conversion(self):
        actual_datetime = datetime.datetime.now()
        entity = FieldsWithoutOptionsModel(
            datetime=actual_datetime, date=actual_datetime.date(),
            time=actual_datetime.time(), floating_point=5.97, boolean=True,
            null_boolean=False, text='Hallo', email='hallo@hallo.com',
            comma_seperated_integer='5,4,3,2',
            ip_address='194.167.1.1', slug='you slugy slut :)',
            url='http://www.scholardocs.com', long_text=1000 * 'A',
            indexed_text='hello',
            integer=-400, small_integer=-4, positive_integer=400,
            positive_small_integer=4)
        entity.save()

        # Get the gae entity (not the django model instance) and test
        # if the fields have been converted right to the corresponding
        # GAE database types.
        gae_entity = Get(
            Key.from_path(FieldsWithoutOptionsModel._meta.db_table,
            entity.pk))
        opts = FieldsWithoutOptionsModel._meta
        for name, types in [('long_text', Text),
                ('indexed_text', unicode),
                ('text', unicode), ('ip_address', unicode), ('slug', unicode),
                ('email', unicode), ('comma_seperated_integer', unicode),
                ('url', unicode), ('time', datetime.datetime),
                ('datetime', datetime.datetime), ('date', datetime.datetime),
                ('floating_point', float), ('boolean', bool),
                ('null_boolean', bool), ('integer', (int, long)),
                ('small_integer', (int, long)),
                ('positive_integer', (int, long)),
                ('positive_small_integer', (int, long))]:
            column = opts.get_field_by_name(name)[0].column
            if not isinstance(types, (list, tuple)):
                types = (types, )
            self.assertTrue(type(gae_entity[column]) in types)

        # Get the model instance and check if the fields convert back
        # to the right types.
        model = FieldsWithoutOptionsModel.objects.get()
        for name, types in [
                ('long_text', unicode),
                ('indexed_text', unicode),
                ('text', unicode), ('ip_address', unicode),
                ('slug', unicode),
                ('email', unicode), ('comma_seperated_integer', unicode),
                ('url', unicode), ('datetime', datetime.datetime),
                ('date', datetime.date), ('time', datetime.time),
                ('floating_point', float), ('boolean', bool),
                ('null_boolean', bool), ('integer', (int, long)),
                ('small_integer', (int, long)),
                ('positive_integer', (int, long)),
                ('positive_small_integer', (int, long))]:
            if not isinstance(types, (list, tuple)):
                types = (types, )
            self.assertTrue(type(getattr(model, name)) in types)

########NEW FILE########
__FILENAME__ = test_field_options
import datetime

from django.test import TestCase
from django.db.utils import DatabaseError
from django.db.models.fields import NOT_PROVIDED

from google.appengine.api import users
from google.appengine.api.datastore import Get
from google.appengine.api.datastore_types import Text, Category, Email, Link, \
    PhoneNumber, PostalAddress, Text, Blob, ByteString, GeoPt, IM, Key, \
    Rating, BlobKey
from google.appengine.ext.db import Key

from .models import FieldsWithOptionsModel, NullableTextModel


class FieldOptionsTest(TestCase):

    def test_options(self):
        entity = FieldsWithOptionsModel()
        # Try to save the entity with non-nullable field time set to
        # None, should raise an exception.
        self.assertRaises(DatabaseError, entity.save)

        time = datetime.datetime.now().time()
        entity.time = time
        entity.save()

        # Check if primary_key=True is set correctly for the saved entity.
        self.assertEquals(entity.pk, u'app-engine@scholardocs.com')
        gae_entity = Get(
            Key.from_path(FieldsWithOptionsModel._meta.db_table, entity.pk))
        self.assertTrue(gae_entity is not None)
        self.assertEquals(gae_entity.key().name(),
                          u'app-engine@scholardocs.com')

        # Check if default values are set correctly on the db level,
        # primary_key field is not stored at the db level.
        for field in FieldsWithOptionsModel._meta.local_fields:
            if field.default and field.default != NOT_PROVIDED and \
                    not field.primary_key:
                self.assertEquals(gae_entity[field.column], field.default)
            elif field.column == 'time':
                self.assertEquals(
                    gae_entity[field.column],
                    datetime.datetime(1970, 1, 1,
                                      time.hour, time.minute, time.second,
                                      time.microsecond))
            elif field.null and field.editable:
                self.assertEquals(gae_entity[field.column], None)

        # Check if default values are set correct on the model instance
        # level.
        entity = FieldsWithOptionsModel.objects.get()
        for field in FieldsWithOptionsModel._meta.local_fields:
            if field.default and field.default != NOT_PROVIDED:
                self.assertEquals(getattr(entity, field.column), field.default)
            elif field.column == 'time':
                self.assertEquals(getattr(entity, field.column), time)
            elif field.null and field.editable:
                self.assertEquals(getattr(entity, field.column), None)

        # Check if nullable field with default values can be set to
        # None.
        entity.slug = None
        entity.positive_small_integer = None
        try:
            entity.save()
        except:
            self.fail()

        # Check if slug and positive_small_integer will be retrieved
        # with values set to None (on db level and model instance
        # level).
        gae_entity = Get(Key.from_path(
            FieldsWithOptionsModel._meta.db_table, entity.pk))
        opts = FieldsWithOptionsModel._meta
        self.assertEquals(
            gae_entity[opts.get_field_by_name('slug')[0].column],
            None)
        self.assertEquals(
            gae_entity[opts.get_field_by_name(
                'positive_small_integer')[0].column],
            None)

        # On the model instance level.
        entity = FieldsWithOptionsModel.objects.get()
        self.assertEquals(
            getattr(entity, opts.get_field_by_name('slug')[0].column),
            None)
        self.assertEquals(
            getattr(entity, opts.get_field_by_name(
                'positive_small_integer')[0].column),
            None)

        # TODO: Check db_column option.
        # TODO: Change the primary key and check if a new instance with
        #       the changed primary key will be saved (not in this test
        #       class).

    def test_nullable_text(self):
        """
        Regression test for #48 (in old BitBucket repository).
        """
        entity = NullableTextModel(text=None)
        entity.save()

        db_entity = NullableTextModel.objects.get()
        self.assertEquals(db_entity.text, None)

########NEW FILE########
__FILENAME__ = test_filter
import datetime
import time

from django.db import models
from django.db.models import Q
from django.db.utils import DatabaseError
from django.test import TestCase
from django.utils import unittest

from google.appengine.api.datastore import Get, Key

from ..db.utils import get_cursor, set_cursor
from .models import FieldsWithOptionsModel, EmailModel, DateTimeModel, \
    OrderedModel, BlobModel


class FilterTest(TestCase):
    floats = [5.3, 2.6, 9.1, 1.58]
    emails = ['app-engine@scholardocs.com', 'sharingan@uchias.com',
              'rinnengan@sage.de', 'rasengan@naruto.com']
    datetimes = [datetime.datetime(2010, 1, 1, 0, 0, 0, 0),
                 datetime.datetime(2010, 12, 31, 23, 59, 59, 999999),
                 datetime.datetime(2011, 1, 1, 0, 0, 0, 0),
                 datetime.datetime(2013, 7, 28, 22, 30, 20, 50)]

    def setUp(self):
        for index, (float, email, datetime_value) in enumerate(zip(
                FilterTest.floats, FilterTest.emails, FilterTest.datetimes)):
            # Ensure distinct times when saving entities.
            time.sleep(0.01)
            self.last_save_datetime = datetime.datetime.now()
            self.last_save_time = self.last_save_datetime.time()

            ordered_instance = OrderedModel(priority=index, pk=index + 1)
            ordered_instance.save()
            FieldsWithOptionsModel(floating_point=float,
                                   integer=int(float), email=email,
                                   time=self.last_save_time,
                                   foreign_key=ordered_instance).save()
            EmailModel(email=email).save()
            DateTimeModel(datetime=datetime_value).save()

    def test_startswith(self):
        self.assertEquals(
            [entity.email for entity in FieldsWithOptionsModel.objects
                .filter(email__startswith='r').order_by('email')],
            ['rasengan@naruto.com', 'rinnengan@sage.de'])
        self.assertEquals(
            [entity.email for entity in EmailModel.objects
                .filter(email__startswith='r').order_by('email')],
            ['rasengan@naruto.com', 'rinnengan@sage.de'])

    def test_pk_and_startswith(self):
        self.assertEquals(
            [entity.email for entity in FieldsWithOptionsModel.objects
                .filter(text__startswith='Ha', pk='rinnengan@sage.de').order_by('text')],
            ['rinnengan@sage.de'])

    def test_gt(self):
        # Test gt on float.
        self.assertEquals(
            [entity.floating_point
             for entity in FieldsWithOptionsModel.objects
                .filter(floating_point__gt=3.1).order_by('floating_point')],
            [5.3, 9.1])

        # Test gt on integer.
        self.assertEquals(
            [entity.integer for entity in FieldsWithOptionsModel.objects
                .filter(integer__gt=3).order_by('integer')],
            [5, 9])

        # Test filter on primary_key field.
        self.assertEquals(
            [entity.email for entity in FieldsWithOptionsModel.objects
                .filter(email__gt='as').order_by('email')],
            ['rasengan@naruto.com', 'rinnengan@sage.de',
             'sharingan@uchias.com', ])

        # Test ForeignKeys with id.
        self.assertEquals(
            sorted([entity.email for entity in FieldsWithOptionsModel.objects
                .filter(foreign_key__gt=2)]),
            ['rasengan@naruto.com', 'rinnengan@sage.de'])

        # And with instance.
        ordered_instance = OrderedModel.objects.get(priority=1)
        self.assertEquals(
            sorted([entity.email for entity in FieldsWithOptionsModel.objects
                .filter(foreign_key__gt=ordered_instance)]),
            ['rasengan@naruto.com', 'rinnengan@sage.de'])

    def test_lt(self):
        # Test lt on float.
        self.assertEquals(
            [entity.floating_point
             for entity in FieldsWithOptionsModel.objects
                .filter(floating_point__lt=3.1).order_by('floating_point')],
            [1.58, 2.6])

        # Test lt on integer.
        self.assertEquals(
            [entity.integer for entity in FieldsWithOptionsModel.objects
                .filter(integer__lt=3).order_by('integer')],
            [1, 2])

        # Test filter on primary_key field.
        self.assertEquals(
            [entity.email for entity in FieldsWithOptionsModel.objects
                .filter(email__lt='as').order_by('email')],
            ['app-engine@scholardocs.com', ])

         # Filter on datetime.
        self.assertEquals(
            [entity.email for entity in FieldsWithOptionsModel.objects
                .filter(time__lt=self.last_save_time).order_by('time')],
            ['app-engine@scholardocs.com', 'sharingan@uchias.com',
             'rinnengan@sage.de'])

        # Test ForeignKeys with id.
        self.assertEquals(
            sorted([entity.email for entity in FieldsWithOptionsModel.objects
                .filter(foreign_key__lt=3)]),
            ['app-engine@scholardocs.com', 'sharingan@uchias.com'])

        # And with instance.
        ordered_instance = OrderedModel.objects.get(priority=2)
        self.assertEquals(
            sorted([entity.email for entity in FieldsWithOptionsModel.objects
                .filter(foreign_key__lt=ordered_instance)]),
            ['app-engine@scholardocs.com', 'sharingan@uchias.com'])

    def test_gte(self):
        # Test gte on float.
        self.assertEquals(
            [entity.floating_point
             for entity in FieldsWithOptionsModel.objects
                .filter(floating_point__gte=2.6).order_by('floating_point')],
            [2.6, 5.3, 9.1])

        # Test gte on integer.
        self.assertEquals(
            [entity.integer for entity in FieldsWithOptionsModel.objects
                .filter(integer__gte=2).order_by('integer')],
            [2, 5, 9])

        # Test filter on primary_key field.
        self.assertEquals(
            [entity.email for entity in FieldsWithOptionsModel.objects
                .filter(email__gte='rinnengan@sage.de').order_by('email')],
            ['rinnengan@sage.de', 'sharingan@uchias.com', ])

    def test_lte(self):
        # Test lte on float.
        self.assertEquals(
            [entity.floating_point
             for entity in FieldsWithOptionsModel.objects
                .filter(floating_point__lte=5.3).order_by('floating_point')],
            [1.58, 2.6, 5.3])

        # Test lte on integer.
        self.assertEquals(
            [entity.integer for entity in FieldsWithOptionsModel.objects
                .filter(integer__lte=5).order_by('integer')],
            [1, 2, 5])

        # Test filter on primary_key field.
        self.assertEquals(
            [entity.email for entity in FieldsWithOptionsModel.objects
                .filter(email__lte='rinnengan@sage.de').order_by('email')],
            ['app-engine@scholardocs.com', 'rasengan@naruto.com',
             'rinnengan@sage.de'])

    def test_equals(self):
        # Test equality filter on primary_key field.
        self.assertEquals(
            [entity.email for entity in FieldsWithOptionsModel.objects
                .filter(email='rinnengan@sage.de').order_by('email')],
            ['rinnengan@sage.de'])

    def test_is_null(self):
        self.assertEquals(FieldsWithOptionsModel.objects.filter(
            floating_point__isnull=True).count(), 0)

        FieldsWithOptionsModel(
            integer=5.4, email='shinra.tensai@sixpaths.com',
            time=datetime.datetime.now().time()).save()

        self.assertEquals(FieldsWithOptionsModel.objects.filter(
            floating_point__isnull=True).count(), 1)

        # XXX: These filters will not work because of a Django bug.
#        self.assertEquals(FieldsWithOptionsModel.objects.filter(
#            foreign_key=None).count(), 1)

        # (it uses left outer joins if checked against isnull)
#        self.assertEquals(FieldsWithOptionsModel.objects.filter(
#            foreign_key__isnull=True).count(), 1)

    def test_exclude(self):
        self.assertEquals(
            [entity.email for entity in FieldsWithOptionsModel.objects
                .all().exclude(floating_point__lt=9.1)
                .order_by('floating_point')],
            ['rinnengan@sage.de', ])

        # Test exclude with ForeignKey.
        ordered_instance = OrderedModel.objects.get(priority=1)
        self.assertEquals(
            sorted([entity.email for entity in FieldsWithOptionsModel.objects
                .all().exclude(foreign_key__gt=ordered_instance)]),
            ['app-engine@scholardocs.com', 'sharingan@uchias.com'])

    def test_exclude_pk(self):
        self.assertEquals(
            [entity.pk for entity in OrderedModel.objects
                .exclude(pk__in=[2, 3]).order_by('pk')],
            [1, 4])

    def test_chained_filter(self):
        # Additionally tests count :)
        self.assertEquals(FieldsWithOptionsModel.objects.filter(
            floating_point__lt=5.3, floating_point__gt=2.6).count(), 0)

        # Test across multiple columns. On App Engine only one filter
        # is allowed to be an inequality filter.
        self.assertEquals(
            [(entity.floating_point, entity.integer)
             for entity in FieldsWithOptionsModel.objects
                .filter(floating_point__lte=5.3, integer=2)
                .order_by('floating_point')],
            [(2.6, 2), ])

        # Test multiple filters including the primary_key field.
        self.assertEquals(
            [entity.email for entity in FieldsWithOptionsModel.objects
                .filter(email__gte='rinnengan@sage.de', integer=2)
                .order_by('email')],
            ['sharingan@uchias.com', ])

        # Test in filter on primary key with another arbitrary filter.
        self.assertEquals(
            [entity.email for entity in FieldsWithOptionsModel.objects
                .filter(email__in=['rinnengan@sage.de',
                                   'sharingan@uchias.com'],
                        integer__gt=2)
                .order_by('integer')],
            ['rinnengan@sage.de', ])

        # Test exceptions.

        # Test multiple filters exception when filtered and not ordered
        # against the first filter.
        self.assertRaises(
            DatabaseError,
            lambda: FieldsWithOptionsModel.objects
                .filter(email__gte='rinnengan@sage.de', floating_point=5.3)
                .order_by('floating_point')[0])

        # Test exception if filtered across multiple columns with
        # inequality filter.
        self.assertRaises(
            DatabaseError,
            FieldsWithOptionsModel.objects
                .filter(floating_point__lte=5.3, integer__gte=2)
                .order_by('floating_point').get)

        # Test exception if filtered across multiple columns with
        # inequality filter with exclude.
        self.assertRaises(
            DatabaseError,
            FieldsWithOptionsModel.objects
                .filter(email__lte='rinnengan@sage.de')
                .exclude(floating_point__lt=9.1).order_by('email').get)

        self.assertRaises(
            DatabaseError,
            lambda: FieldsWithOptionsModel.objects
                .all().exclude(floating_point__lt=9.1).order_by('email')[0])

        # TODO: Maybe check all possible exceptions.

    def test_slicing(self):
        # Test slicing on filter with primary_key.
        self.assertEquals(
            [entity.email for entity in FieldsWithOptionsModel.objects
                .filter(email__lte='rinnengan@sage.de')
                .order_by('email')[:2]],
            ['app-engine@scholardocs.com', 'rasengan@naruto.com', ])

        self.assertEquals(
            [entity.email for entity in FieldsWithOptionsModel.objects
                .filter(email__lte='rinnengan@sage.de')
                .order_by('email')[1:2]],
            ['rasengan@naruto.com', ])

        # Test on non pk field.
        self.assertEquals(
            [entity.integer for entity in FieldsWithOptionsModel.objects
                .all().order_by('integer')[:2]],
            [1, 2, ])

        self.assertEquals(
            [entity.email for entity in FieldsWithOptionsModel.objects
                .all().order_by('email')[::2]],
            ['app-engine@scholardocs.com', 'rinnengan@sage.de'])

    def test_cursor(self):
        results = list(FieldsWithOptionsModel.objects.all())
        cursor = None
        for item in results:
            query = FieldsWithOptionsModel.objects.all()[:1]
            if cursor is not None:
                query = set_cursor(query, cursor)
            next = query[0]
            self.assertEqual(next.pk, item.pk)
            cursor = get_cursor(query)
            self.assertIsNotNone(cursor)
        query = set_cursor(FieldsWithOptionsModel.objects.all(), cursor)
        self.assertEqual(list(query[:1]), [])

    def test_Q_objects(self):
        self.assertEquals(
            [entity.email for entity in FieldsWithOptionsModel.objects
                .filter(Q(email__lte='rinnengan@sage.de'))
                .order_by('email')][:2],
            ['app-engine@scholardocs.com', 'rasengan@naruto.com', ])

        self.assertEquals(
            [entity.integer for entity in FieldsWithOptionsModel.objects
                .exclude(Q(integer__lt=5) | Q(integer__gte=9))
                .order_by('integer')],
            [5, ])

        self.assertRaises(
            TypeError,
            FieldsWithOptionsModel.objects
                .filter(Q(floating_point=9.1), Q(integer=9) | Q(integer=2)))

    def test_pk_in(self):
        # Test pk__in with field name email.
        self.assertEquals(
            [entity.email for entity in FieldsWithOptionsModel.objects
                .filter(email__in=['app-engine@scholardocs.com',
                                   'rasengan@naruto.com'])],
            ['app-engine@scholardocs.com', 'rasengan@naruto.com'])

    def test_in(self):
        self.assertEquals(
            [entity.email for entity in FieldsWithOptionsModel.objects
                .filter(floating_point__in=[5.3, 2.6, 1.58])
                .filter(integer__in=[1, 5, 9])],
            ['app-engine@scholardocs.com', 'rasengan@naruto.com'])

    def test_in_with_pk_in(self):
        self.assertEquals(
            [entity.email for entity in FieldsWithOptionsModel.objects
                .filter(floating_point__in=[5.3, 2.6, 1.58])
                .filter(email__in=['app-engine@scholardocs.com',
                                   'rasengan@naruto.com'])],
            ['app-engine@scholardocs.com', 'rasengan@naruto.com'])

    def test_in_with_order_by(self):

        class Post(models.Model):
            writer = models.IntegerField()
            order = models.IntegerField()

        Post(writer=1, order=1).save()
        Post(writer=1, order=2).save()
        Post(writer=1, order=3).save()
        Post(writer=2, order=4).save()
        Post(writer=2, order=5).save()
        posts = Post.objects.filter(writer__in=[1, 2]).order_by('order')
        orders = [post.order for post in posts]
        self.assertEqual(orders, range(1, 6))
        posts = Post.objects.filter(writer__in=[1, 2]).order_by('-order')
        orders = [post.order for post in posts]
        self.assertEqual(orders, range(5, 0, -1))

    def test_inequality(self):
        self.assertEquals(
            [entity.email for entity in FieldsWithOptionsModel.objects
                .exclude(floating_point=5.3).filter(integer__in=[1, 5, 9])],
            ['rasengan@naruto.com', 'rinnengan@sage.de'])

    def test_values(self):
        # Test values().
        self.assertEquals(
            [entity['pk'] for entity in FieldsWithOptionsModel.objects
                .filter(integer__gt=3).order_by('integer').values('pk')],
            ['app-engine@scholardocs.com', 'rinnengan@sage.de'])

        self.assertEquals(FieldsWithOptionsModel.objects
            .filter(integer__gt=3).order_by('integer').values('pk').count(), 2)

        # These queries first fetch the whole entity and then only
        # return the desired fields selected in .values.
        self.assertEquals(
            [entity['integer'] for entity in FieldsWithOptionsModel.objects
                .filter(email__startswith='r')
                .order_by('email').values('integer')],
            [1, 9])

        self.assertEquals(
            [entity['floating_point']
             for entity in FieldsWithOptionsModel.objects
                .filter(integer__gt=3)
                .order_by('integer').values('floating_point')],
            [5.3, 9.1])

        # Test values_list.
        self.assertEquals(
            [entity[0] for entity in FieldsWithOptionsModel.objects
                .filter(integer__gt=3).order_by('integer').values_list('pk')],
            ['app-engine@scholardocs.com', 'rinnengan@sage.de'])

    def test_range(self):
        # Test range on float.
        self.assertEquals(
            [entity.floating_point
             for entity in FieldsWithOptionsModel.objects
                .filter(floating_point__range=(2.6, 9.1))
                .order_by('floating_point')],
            [2.6, 5.3, 9.1])

        # Test range on pk.
        self.assertEquals(
            [entity.pk for entity in FieldsWithOptionsModel.objects
                .filter(pk__range=('app-engine@scholardocs.com',
                                  'rinnengan@sage.de'))
                .order_by('pk')],
            ['app-engine@scholardocs.com', 'rasengan@naruto.com',
             'rinnengan@sage.de'])

        # Test range on date/datetime objects.
        start_time = self.last_save_datetime - datetime.timedelta(minutes=1)
        self.assertEquals(
            [entity.email for entity in FieldsWithOptionsModel.objects
                .filter(time__range=(start_time, self.last_save_time))
                .order_by('time')],
            ['app-engine@scholardocs.com', 'sharingan@uchias.com',
             'rinnengan@sage.de', 'rasengan@naruto.com'])

    def test_date(self):
        # Test year on date range boundaries.
        self.assertEquals(
            [entity.datetime for entity in DateTimeModel.objects
                .filter(datetime__year=2010).order_by('datetime')],
            [datetime.datetime(2010, 1, 1, 0, 0, 0, 0),
             datetime.datetime(2010, 12, 31, 23, 59, 59, 999999)])

        # Test year on non boundary date.
        self.assertEquals(
            [entity.datetime for entity in DateTimeModel.objects
                .filter(datetime__year=2013).order_by('datetime')],
            [datetime.datetime(2013, 7, 28, 22, 30, 20, 50)])

    def test_auto_now(self):
        time.sleep(0.1)
        entity = DateTimeModel.objects.all()[0]
        auto_now = entity.datetime_auto_now
        entity.save()
        entity = DateTimeModel.objects.get(pk=entity.pk)
        self.assertNotEqual(auto_now, entity.datetime_auto_now)

    def test_auto_now_add(self):
        time.sleep(0.1)
        entity = DateTimeModel.objects.all()[0]
        auto_now_add = entity.datetime_auto_now_add
        entity.save()
        entity = DateTimeModel.objects.get(pk=entity.pk)
        self.assertEqual(auto_now_add, entity.datetime_auto_now_add)

    def test_latest(self):
        self.assertEquals(FieldsWithOptionsModel.objects
            .latest('time').floating_point, 1.58)

    def test_blob(self):
        x = BlobModel(data='lalala')
        x.full_clean()
        x.save()
        e = Get(Key.from_path(BlobModel._meta.db_table, x.pk))
        self.assertEqual(e['data'], x.data)
        x = BlobModel.objects.all()[0]
        self.assertEqual(e['data'], x.data)

########NEW FILE########
__FILENAME__ = test_keys
from __future__ import with_statement

from django.db import connection, models
from django.db.utils import DatabaseError
from django.test import TestCase
from django.utils import unittest

from djangotoolbox.fields import ListField


class AutoKey(models.Model):
    pass


class CharKey(models.Model):
    id = models.CharField(primary_key=True, max_length=10)


class IntegerKey(models.Model):
    id = models.IntegerField(primary_key=True)


class Parent(models.Model):
    pass


class Child(models.Model):
    parent = models.ForeignKey(Parent, null=True)


class CharParent(models.Model):
    id = models.CharField(primary_key=True, max_length=10)


class CharChild(models.Model):
    parent = models.ForeignKey(CharParent)


class IntegerParent(models.Model):
    id = models.IntegerField(primary_key=True)


class IntegerChild(models.Model):
    parent = models.ForeignKey(IntegerParent)


class ParentKind(models.Model):
    pass


class ChildKind(models.Model):
    parent = models.ForeignKey(ParentKind)
    parents = ListField(models.ForeignKey(ParentKind))


class KeysTest(TestCase):
    """
    GAE requires that keys are strings or positive integers,
    keys also play a role in defining entity groups.

    Note: len() is a way of forcing evaluation of a QuerySet -- we
    depend on the back-end to do some checks, so sometimes there is no
    way to raise an exception earlier.
    """

    def test_auto_field(self):
        """
        GAE keys may hold either strings or positive integers, however
        Django uses integers as well as their string representations
        for lookups, expecting both to be considered equivalent, so we
        limit AutoFields to just ints and check that int or string(int)
        may be used interchangably.

        Nonpositive keys are not allowed, and trying to use them to
        create or look up objects should raise a database exception.

        See: http://code.google.com/appengine/docs/python/datastore/keyclass.html.
        """
        AutoKey.objects.create()
        o1 = AutoKey.objects.create(pk=1)
        o2 = AutoKey.objects.create(pk='1')
#        self.assertEqual(o1, o2) TODO: Not same for Django, same for the database.
        with self.assertRaises(ValueError):
            AutoKey.objects.create(pk='a')
        self.assertEqual(AutoKey.objects.get(pk=1), o1)
        self.assertEqual(AutoKey.objects.get(pk='1'), o1)
        with self.assertRaises(ValueError):
            AutoKey.objects.get(pk='a')

        with self.assertRaises(DatabaseError):
            AutoKey.objects.create(id=-1)
        with self.assertRaises(DatabaseError):
            AutoKey.objects.create(id=0)
        with self.assertRaises(DatabaseError):
            AutoKey.objects.get(id=-1)
        with self.assertRaises(DatabaseError):
            AutoKey.objects.get(id__gt=-1)
        with self.assertRaises(DatabaseError):
            AutoKey.objects.get(id=0)
        with self.assertRaises(DatabaseError):
            AutoKey.objects.get(id__gt=0)
        with self.assertRaises(DatabaseError):
            len(AutoKey.objects.filter(id__gt=-1))
        with self.assertRaises(DatabaseError):
            len(AutoKey.objects.filter(id__gt=0))

    def test_primary_key(self):
        """
        Specifying a field as primary_key should work as long as the
        field values (after get_db_prep_*/value_to_db_* layer) can be
        represented by the back-end key type. In case a value can be
        represented, but lossy conversions, unexpected sorting, range
        limitation or potential future ramifications are possible it
        should warn the user (as early as possible).

        TODO: It may be even better to raise exceptions / issue
              warnings during model validation. And make use of the new
              supports_primary_key_on to prevent validation of models
              using unsupported primary keys.
        """

        # This should just work.
        class AutoFieldKey(models.Model):
            key = models.AutoField(primary_key=True)
        AutoFieldKey.objects.create()

        # This one can be exactly represented.
        class CharKey(models.Model):
            id = models.CharField(primary_key=True, max_length=10)
        CharKey.objects.create(id='a')

        # Some rely on unstable assumptions or have other quirks and
        # should warn.

#        # TODO: Warning with a range limitation.
#        with self.assertRaises(Warning):
#
#            class IntegerKey(models.Model):
#                id = models.IntegerField(primary_key=True)
#            IntegerKey.objects.create(id=1)

#        # TODO: date/times could be resonably encoded / decoded as
#        #       strings (in a reversible manner) for key usage, but
#        #       would need special handling and continue to raise an
#        #       exception for now
#        with self.assertRaises(Warning):
#
#            class DateKey(models.Model):
#                id = models.DateField(primary_key=True, auto_now=True)
#            DateKey.objects.create()

#        # TODO: There is a db.Email field that would be better to
#        #       store emails, but that may prevent them from being
#        #       used as keys.
#        with self.assertRaises(Warning):
#
#            class EmailKey(models.Model):
#               id = models.EmailField(primary_key=True)
#            EmailKey.objects.create(id='aaa@example.com')

#        # TODO: Warn that changing field parameters breaks sorting.
#        #       This applies to any DecimalField, so should belong to
#        #       the docs.
#        with self.assertRaises(Warning):
#
#           class DecimalKey(models.Model):
#              id = models.DecimalField(primary_key=True, decimal_places=2,
#                                       max_digits=5)
#           DecimalKey.objects.create(id=1)

        # Some cannot be reasonably represented (e.g. binary or string
        # encoding would prevent comparisons to work as expected).
        with self.assertRaises(DatabaseError):

            class FloatKey(models.Model):
                id = models.FloatField(primary_key=True)
            FloatKey.objects.create(id=1.0)

        # TODO: Better fail during validation or creation than
        # sometimes when filtering (False = 0 is a wrong key value).
        with self.assertRaises(DatabaseError):

            class BooleanKey(models.Model):
                id = models.BooleanField(primary_key=True)
            BooleanKey.objects.create(id=True)
            len(BooleanKey.objects.filter(id=False))

    def test_primary_key_coercing(self):
        """
        Creation and lookups should use the same type casting as
        vanilla Django does, so CharField used as a key should cast
        everything to a string, while IntegerField should cast to int.
        """
        CharKey.objects.create(id=1)
        CharKey.objects.create(id='a')
        CharKey.objects.create(id=1.1)
        CharKey.objects.get(id='1')
        CharKey.objects.get(id='a')
        CharKey.objects.get(id='1.1')

        IntegerKey.objects.create(id=1)
        with self.assertRaises(ValueError):
            IntegerKey.objects.create(id='a')
        IntegerKey.objects.create(id=1.1)
        IntegerKey.objects.get(id='1')
        with self.assertRaises(ValueError):
            IntegerKey.objects.get(id='a')
        IntegerKey.objects.get(id=1.1)

    def test_foreign_key(self):
        """
        Foreign key lookups may use parent instance or parent key value.
        Using null foreign keys needs some special attention.

        TODO: In 1.4 one may also add _id suffix and use the key value.
        """
        parent1 = Parent.objects.create(pk=1)
        child1 = Child.objects.create(parent=parent1)
        child2 = Child.objects.create(parent=None)
        self.assertEqual(child1.parent, parent1)
        self.assertEqual(child2.parent, None)
        self.assertEqual(Child.objects.get(parent=parent1), child1)
        self.assertEqual(Child.objects.get(parent=1), child1)
        self.assertEqual(Child.objects.get(parent='1'), child1)
        with self.assertRaises(ValueError):
            Child.objects.get(parent='a')
        self.assertEqual(Child.objects.get(parent=None), child2)

    def test_foreign_key_backwards(self):
        """
        Following relationships backwards (_set syntax) with typed
        parent key causes a unique problem for the legacy key storage.
        """
        parent = CharParent.objects.create(id=1)
        child = CharChild.objects.create(parent=parent)
        self.assertEqual(list(parent.charchild_set.all()), [child])

        parent = IntegerParent.objects.create(id=1)
        child = IntegerChild.objects.create(parent=parent)
        self.assertEqual(list(parent.integerchild_set.all()), [child])

    @unittest.skipIf(
         not connection.settings_dict.get('STORE_RELATIONS_AS_DB_KEYS'),
         "No key kinds to check with the string/int foreign key storage.")
    def test_key_kind(self):
        """
        Checks that db.Keys stored in the database use proper kinds.

        Key kind should be the name of the table (db_table) of a model
        for primary keys of entities, but for foreign keys, references
        in general, it should be the db_table of the model the field
        refers to.

        Note that Django hides the underlying db.Key objects well, and
        it does work even with wrong kinds, but keeping the data
        consistent may be significant for external tools.

        TODO: Add DictField / EmbeddedModelField and nesting checks.
        """
        parent = ParentKind.objects.create(pk=1)
        child = ChildKind.objects.create(
            pk=2, parent=parent, parents=[parent.pk])
        self.assertEqual(child.parent.pk, parent.pk)
        self.assertEqual(child.parents[0], parent.pk)

        from google.appengine.api.datastore import Get
        from google.appengine.api.datastore_types import Key
        parent_key = Key.from_path(parent._meta.db_table, 1)
        child_key = Key.from_path(child._meta.db_table, 2)
        parent_entity = Get(parent_key)
        child_entity = Get(child_key)
        parent_column = child._meta.get_field('parent').column
        parents_column = child._meta.get_field('parents').column
        self.assertEqual(child_entity[parent_column], parent_key)
        self.assertEqual(child_entity[parents_column][0], parent_key)

########NEW FILE########
__FILENAME__ = test_mapreduce
from django.db import models
from django.test import TestCase
from django.utils import unittest

from google.appengine.api.datastore import Key

try:
    from djangoappengine.mapreduce.input_readers import DjangoModelInputReader, DjangoModelIterator

    import mapreduce

    from mapreduce import input_readers
    from mapreduce.lib import key_range
    from mapreduce import model
except ImportError:
    mapreduce = None

class TestModel(models.Model):
    test_property = models.IntegerField(default=0)

    def __unicode__(self):
        return str(self.test_property)

ENTITY_KIND = '%s.%s' % (TestModel.__module__, TestModel.__name__)

def key(entity_id, kind=TestModel):
    return Key.from_path(kind._meta.db_table, entity_id)

@unittest.skipUnless(mapreduce, 'mapreduce not installed')
class DjangoModelInputReaderTest(TestCase):
    """Test DjangoModelInputReader class."""

    def testValidate_Passes(self):
        """Test validate function accepts valid parameters."""
        params = {
            "entity_kind": ENTITY_KIND,
            }
        mapper_spec = model.MapperSpec(
                "FooHandler",
                "djangoappengine.mapreduce.input_readers.DjangoModelInputReader",
                params, 1)
        DjangoModelInputReader.validate(mapper_spec)

    def testValidate_NoEntityFails(self):
        """Test validate function raises exception with no entity parameter."""
        params = {}
        mapper_spec = model.MapperSpec(
            "FooHandler",
            "djangoappengine.mapreduce.input_readers.DjangoModelInputReader",
            params, 1)
        self.assertRaises(input_readers.BadReaderParamsError,
                            DjangoModelInputReader.validate,
                            mapper_spec)

    def testValidate_BadEntityKind(self):
        """Test validate function with bad entity kind."""
        params = {
            "entity_kind": "foo",
            }
        mapper_spec = model.MapperSpec(
            "FooHandler",
            "djangoappengine.mapreduce.input_readers.DjangoModelInputReader",
            params, 1)
        self.assertRaises(input_readers.BadReaderParamsError,
                            DjangoModelInputReader.validate,
                            mapper_spec)

    def testValidate_BadNamespace(self):
        """Test validate function with bad namespace."""
        params = {
            "entity_kind": ENTITY_KIND,
            "namespace": 'namespace',
            }
        mapper_spec = model.MapperSpec(
            "FooHandler",
            "djangoappengine.mapreduce.input_readers.DjangoModelInputReader",
            params, 1)
        self.assertRaises(input_readers.BadReaderParamsError,
                            DjangoModelInputReader.validate,
                            mapper_spec)

    def testGeneratorWithKeyRange(self):
        """Test DjangoModelInputReader as generator using KeyRanges."""
        expected_entities = []
        for i in range(0, 100):
            entity = TestModel(test_property=i)
            entity.save()
            expected_entities.append(entity)

        params = {
            "entity_kind": ENTITY_KIND,
            }
        mapper_spec = model.MapperSpec(
            "FooHandler",
            "djangoappengine.mapreduce.input_readers.DjangoModelInputReader",
            params, 1)

        input_ranges = DjangoModelInputReader.split_input(mapper_spec)

        entities = []
        for query_range in input_ranges:
            for entity in query_range:
                entities.append(entity)

        self.assertEquals(100, len(entities))
        self.assertEquals(expected_entities, entities)

@unittest.skipUnless(mapreduce, 'mapreduce not installed')
class DjangoModelIteratorTest(TestCase):
    def setUp(self):
        expected_entities = []
        for i in range(0, 100):
            entity = TestModel(test_property=i)
            entity.save()
            expected_entities.append(entity)

        self.expected_entities = expected_entities

    def testCursors(self):
        qs = model.QuerySpec(TestModel, model_class_path=ENTITY_KIND)
        kr = key_range.KeyRange(key_start=key(1), key_end=key(10000), direction="ASC")

        json = { 'key_range': kr.to_json(), 'query_spec': qs.to_json(), 'cursor': None }

        entities = []
        while True:
            model_iter = DjangoModelIterator.from_json(json)

            c = False
            count = 0
            for entity in model_iter:
                count += 1
                entities.append(entity)
                if count == 10:
                    c = True
                    break

            if c:
                json = model_iter.to_json()
            else:
                break

        self.assertEquals(100, len(entities))
        self.assertEquals(self.expected_entities, entities)

########NEW FILE########
__FILENAME__ = test_not_return_sets
import datetime

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.test import TestCase

from .models import FieldsWithOptionsModel, OrderedModel, \
    SelfReferenceModel


class NonReturnSetsTest(TestCase):
    floats = [5.3, 2.6, 9.1, 1.58, 2.4]
    emails = ['app-engine@scholardocs.com', 'sharingan@uchias.com',
              'rinnengan@sage.de', 'rasengan@naruto.com', 'itachi@uchia.com']

    def setUp(self):
        for index, (float, email) in enumerate(zip(NonReturnSetsTest.floats,
                NonReturnSetsTest.emails)):
            self.last_save_time = datetime.datetime.now().time()
            ordered_instance = OrderedModel(priority=index, pk=index + 1)
            ordered_instance.save()
            model = FieldsWithOptionsModel(floating_point=float,
                                           integer=int(float), email=email,
                                           time=self.last_save_time,
                                           foreign_key=ordered_instance)
            model.save()

    def test_get(self):
        self.assertEquals(
            FieldsWithOptionsModel.objects.get(
                email='itachi@uchia.com').email,
            'itachi@uchia.com')

        # Test exception when matching multiple entities.
        self.assertRaises(MultipleObjectsReturned,
                          FieldsWithOptionsModel.objects.get,
                          integer=2)

        # Test exception when entity does not exist.
        self.assertRaises(ObjectDoesNotExist,
                          FieldsWithOptionsModel.objects.get,
                          floating_point=5.2)

        # TODO: Test create when djangos model.save_base is refactored.
        # TODO: Test get_or_create when refactored.

    def test_count(self):
        self.assertEquals(
            FieldsWithOptionsModel.objects.filter(integer=2).count(), 2)

    def test_in_bulk(self):
        self.assertEquals(
            [key in ['sharingan@uchias.com', 'itachi@uchia.com']
             for key in FieldsWithOptionsModel.objects.in_bulk(
                ['sharingan@uchias.com', 'itachi@uchia.com']).keys()],
            [True, ] * 2)

    def test_latest(self):
        self.assertEquals(
            FieldsWithOptionsModel.objects.latest('time').email,
            'itachi@uchia.com')

    def test_exists(self):
        self.assertEquals(FieldsWithOptionsModel.objects.exists(), True)

    def test_deletion(self):
        # TODO: ForeignKeys will not be deleted! This has to be done
        #       via background tasks.
        self.assertEquals(FieldsWithOptionsModel.objects.count(), 5)

        FieldsWithOptionsModel.objects.get(email='itachi@uchia.com').delete()
        self.assertEquals(FieldsWithOptionsModel.objects.count(), 4)

        FieldsWithOptionsModel.objects.filter(email__in=[
            'sharingan@uchias.com', 'itachi@uchia.com',
            'rasengan@naruto.com', ]).delete()
        self.assertEquals(FieldsWithOptionsModel.objects.count(), 2)

    def test_selfref_deletion(self):
        entity = SelfReferenceModel()
        entity.save()
        entity.delete()

    def test_foreign_key_fetch(self):
        # Test fetching the ForeignKey.
        ordered_instance = OrderedModel.objects.get(priority=2)
        self.assertEquals(
            FieldsWithOptionsModel.objects.get(integer=9).foreign_key,
            ordered_instance)

    def test_foreign_key_backward(self):
        entity = OrderedModel.objects.all()[0]
        self.assertEquals(entity.keys.count(), 1)
        # TODO: Add should save the added instance transactional via for
        #       example force_insert.
        new_foreign_key = FieldsWithOptionsModel(
            floating_point=5.6, integer=3,
            email='temp@temp.com', time=datetime.datetime.now())
        entity.keys.add(new_foreign_key)
        self.assertEquals(entity.keys.count(), 2)
        # TODO: Add test for create.
        entity.keys.remove(new_foreign_key)
        self.assertEquals(entity.keys.count(), 1)
        entity.keys.clear()
        self.assertTrue(not entity.keys.exists())
        entity.keys = [new_foreign_key, new_foreign_key]
        self.assertEquals(entity.keys.count(), 1)
        self.assertEquals(entity.keys.all()[0].integer, 3)

########NEW FILE########
__FILENAME__ = test_order
from django.test import TestCase

from .models import OrderedModel


class OrderTest(TestCase):

    def create_ordered_model_items(self):
        pks = []
        priorities = [5, 2, 9, 1]
        for pk, priority in enumerate(priorities):
            pk += 1
            model = OrderedModel(pk=pk, priority=priority)
            model.save()
            pks.append(model.pk)
        return pks, priorities

    def test_default_order(self):
        pks, priorities = self.create_ordered_model_items()
        self.assertEquals(
            [item.priority for item in OrderedModel.objects.all()],
            sorted(priorities, reverse=True))

    def test_override_default_order(self):
        pks, priorities = self.create_ordered_model_items()
        self.assertEquals(
            [item.priority for item in
                OrderedModel.objects.all().order_by('priority')],
            sorted(priorities))

    def test_remove_default_order(self):
        pks, priorities = self.create_ordered_model_items()
        self.assertEquals(
            [item.pk for item in OrderedModel.objects.all().order_by()],
            sorted(pks))

    def test_order_with_pk_filter(self):
        pks, priorities = self.create_ordered_model_items()
        self.assertEquals(
            [item.priority for item in
                OrderedModel.objects.filter(pk__in=pks)],
            sorted(priorities, reverse=True))

        # Test with id__in.
        self.assertEquals(
            [item.priority for item in
                OrderedModel.objects.filter(id__in=pks)],
            sorted(priorities, reverse=True))

        # Test reverse.
        self.assertEquals(
            [item.priority for item in
                OrderedModel.objects.filter(pk__in=pks).reverse()],
            sorted(priorities, reverse=False))

    def test_remove_default_order_with_pk_filter(self):
        pks, priorities = self.create_ordered_model_items()
        self.assertEquals(
            [item.priority for item in
                OrderedModel.objects.filter(pk__in=pks).order_by()],
            priorities)

    # TODO: Test multiple orders.

########NEW FILE########
__FILENAME__ = test_transactions
from django.db.models import F
from django.test import TestCase

from .models import EmailModel


class TransactionTest(TestCase):
    emails = ['app-engine@scholardocs.com', 'sharingan@uchias.com',
              'rinnengan@sage.de', 'rasengan@naruto.com']

    def setUp(self):
        EmailModel(email=self.emails[0], number=1).save()
        EmailModel(email=self.emails[0], number=2).save()
        EmailModel(email=self.emails[1], number=3).save()

    def test_update(self):
        self.assertEqual(2, len(EmailModel.objects.all().filter(
            email=self.emails[0])))

        self.assertEqual(1, len(EmailModel.objects.all().filter(
            email=self.emails[1])))

        EmailModel.objects.all().filter(email=self.emails[0]).update(
            email=self.emails[1])

        self.assertEqual(0, len(EmailModel.objects.all().filter(
            email=self.emails[0])))
        self.assertEqual(3, len(EmailModel.objects.all().filter(
            email=self.emails[1])))

    def test_f_object_updates(self):
        self.assertEqual(1, len(EmailModel.objects.all().filter(
            number=1)))
        self.assertEqual(1, len(EmailModel.objects.all().filter(
            number=2)))

        # Test add.
        EmailModel.objects.all().filter(email=self.emails[0]).update(
            number=F('number') + F('number'))

        self.assertEqual(1, len(EmailModel.objects.all().filter(
            number=2)))
        self.assertEqual(1, len(EmailModel.objects.all().filter(
            number=4)))

        EmailModel.objects.all().filter(email=self.emails[1]).update(
            number=F('number') + 10, email=self.emails[0])

        self.assertEqual(1, len(EmailModel.objects.all().filter(number=13)))
        self.assertEqual(self.emails[0],
                         EmailModel.objects.all().get(number=13).email)

        # Complex expression test.
        EmailModel.objects.all().filter(number=13).update(
            number=F('number') * (F('number') + 10) - 5, email=self.emails[0])
        self.assertEqual(1, len(EmailModel.objects.all().filter(number=294)))

       # TODO: Tests for: sub, muld, div, mod, ....

########NEW FILE########
__FILENAME__ = utils
import os

from google.appengine.api import apiproxy_stub_map
from google.appengine.api.app_identity import get_application_id


have_appserver = bool(apiproxy_stub_map.apiproxy.GetStub('datastore_v3'))

if have_appserver:
    appid = get_application_id()
else:
    try:
        try:
            from google.appengine.tools import dev_appserver
        except ImportError:
            from google.appengine.tools import old_dev_appserver as dev_appserver

        from .boot import PROJECT_DIR
        appconfig = dev_appserver.LoadAppConfig(PROJECT_DIR, {},
                                                default_partition='dev')[0]
        appid = appconfig.application.split('~', 1)[-1]
    except ImportError, e:
        raise Exception("Could not get appid. Is your app.yaml file missing? "
                        "Error was: %s" % e)

on_production_server = have_appserver and \
    not os.environ.get('SERVER_SOFTWARE', '').lower().startswith('devel')

########NEW FILE########
__FILENAME__ = views
from django.conf import settings
from django.http import HttpResponse
from django.utils.importlib import import_module


def warmup(request):
    """
    Provides default procedure for handling warmup requests on App
    Engine. Just add this view to your main urls.py.
    """
    for app in settings.INSTALLED_APPS:
        for name in ('urls', 'views', 'models'):
            try:
                import_module('%s.%s' % (app, name))
            except ImportError:
                pass
    content_type = 'text/plain; charset=%s' % settings.DEFAULT_CHARSET
    return HttpResponse("Warmup done.", content_type=content_type)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Django App Engine documentation build configuration file, created by
# sphinx-quickstart on Tue Dec 20 20:01:39 2011.
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
project = u'Django App Engine'
copyright = u'2011, AllButtonsPressed, Potato London, Wilfred Hughes'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.6.0'
# The full version, including alpha/beta/rc tags.
release = '1.6.0'

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
htmlhelp_basename = 'DjangoAppEnginedoc'


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
  ('index', 'DjangoAppEngine.tex', u'Django App Engine Documentation',
   u'AllButtonsPressed, Potato London, Wilfred Hughes', 'manual'),
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
    ('index', 'djangoappengine', u'Django App Engine Documentation',
     [u'AllButtonsPressed, Potato London, Wilfred Hughes'], 1),
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'DjangoAppEngine', u'Django App Engine Documentation',
   u'AllButtonsPressed, Potato London, Wilfred Hughes', 'DjangoAppEngine',
   'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
