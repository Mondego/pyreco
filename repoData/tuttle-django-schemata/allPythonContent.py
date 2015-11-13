__FILENAME__ = manage_schemata
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, transaction

from django_schemata.postgresql_backend.base import _check_identifier

class Command(BaseCommand):
    help = "Manages the postgresql schemata."
    
    def handle(self, *unused_args, **unused_options):
        self.create_schemata()

    def create_schemata(self):
        """
        Go through settings.SCHEMATA_DOMAINS and create all schemata that
        do not already exist in the database. 
        """
        # operate in the public schema
        connection.set_schemata_off()
        cursor = connection.cursor()
        cursor.execute('SELECT schema_name FROM information_schema.schemata')
        existing_schemata = [ row[0] for row in cursor.fetchall() ]

        for sd in settings.SCHEMATA_DOMAINS.values():
            schema_name = str(sd['schema_name'])
            _check_identifier(schema_name)
        
            if schema_name not in existing_schemata:
                sql = 'CREATE SCHEMA %s' % schema_name
                print sql
                cursor.execute(sql)
                transaction.commit_unless_managed()

########NEW FILE########
__FILENAME__ = migrate_schemata
from django_schemata.management.commands.sync_schemata import BaseSchemataCommand

# Uses the twin command base code for the actual iteration.

class Command(BaseSchemataCommand):
    COMMAND_NAME = 'migrate'

########NEW FILE########
__FILENAME__ = sync_schemata
from django.conf import settings
from django.core.management import call_command, get_commands, load_command_class
from django.core.management.base import BaseCommand
from django.db import connection

class BaseSchemataCommand(BaseCommand):
    """
    Generic command class useful for iterating any existing command
    over all schemata. The actual command name is expected in the
    class variable COMMAND_NAME of the subclass.
    """ 
    def __new__(cls, *args, **kwargs):
        """
        Sets option_list and help dynamically.
        """
        # instantiate
        obj = super(BaseSchemataCommand, cls).__new__(cls, *args, **kwargs)
        # load the command class
        cmdclass = load_command_class(get_commands()[obj.COMMAND_NAME], obj.COMMAND_NAME) 
        # inherit the options from the original command
        obj.option_list = cmdclass.option_list
        # prepend the command's original help with the info about schemata iteration
        obj.help = "Calls %s for all registered schemata. You can use regular %s options. " \
                   "Original help for %s: %s" \
                   % (obj.COMMAND_NAME, obj.COMMAND_NAME, obj.COMMAND_NAME, \
                      getattr(cmdclass, 'help', 'none'))
        return obj

    def handle(self, *args, **options):
        """
        Iterates a command over all registered schemata.
        """
        for domain_name in settings.SCHEMATA_DOMAINS:

            print
            print self.style.NOTICE("=== Switching to domain ") \
                + self.style.SQL_TABLE(domain_name) \
                + self.style.NOTICE(" then calling %s:" % self.COMMAND_NAME)

            # sets the schema for the connection
            connection.set_schemata_domain(domain_name)

            # call the original command with the args it knows
            call_command(self.COMMAND_NAME, *args, **options)


class Command(BaseSchemataCommand):
    COMMAND_NAME = 'syncdb'

########NEW FILE########
__FILENAME__ = middleware
from django.db import connection

class SchemataMiddleware(object):
    """
    This middleware should be placed at the very top of the middleware stack.
    Selects the proper database schema using the request host. Can fail in
    various ways which is better than corrupting or revealing data...
    """
    def process_request(self, request):
        hostname_without_port = request.get_host().split(':')[0]
        request.schema_domain_name = hostname_without_port
        request.schema_domain = connection.set_schemata_domain(request.schema_domain_name)

    # The question remains whether it's necessary to unset the schema
    # when the request finishes...

########NEW FILE########
__FILENAME__ = models
# Placeholder to allow tests to be found
########NEW FILE########
__FILENAME__ = base
import os, re

from django.conf import settings
from django.utils.importlib import import_module
from django.core.exceptions import ImproperlyConfigured

ORIGINAL_BACKEND = getattr(settings, 'ORIGINAL_BACKEND', 'django.db.backends.oracle')

original_backend = import_module('.base', ORIGINAL_BACKEND)

SQL_IDENTIFIER_RE = re.compile('^[_a-zA-Z][_a-zA-Z0-9]{,30}$')

def _check_identifier(identifier):
    if not SQL_IDENTIFIER_RE.match(identifier):
        raise RuntimeError("Invalid string used for the schema name.")

class DatabaseWrapper(original_backend.DatabaseWrapper):
    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        # By default the schema is not set
        self.schema_name = None

        # but one can change the default using the environment variable.
        force_domain = os.getenv('DJANGO_SCHEMATA_DOMAIN')
        if force_domain:
            self.schema_name = self._resolve_schema_domain(force_domain)['schema_name']

    def _resolve_schema_domain(self, domain_name):
        try:
            sd = settings.SCHEMATA_DOMAINS[domain_name]
        except KeyError, er:
            print er
            raise ImproperlyConfigured("Domain '%s' is not supported by "
                                       "settings.SCHEMATA_DOMAINS" % domain_name)
        return sd

    def _set_oracle_default_schema(self, cursor):
        '''
        this is somewhat the equivalent of postgresql_backend ``_set_pg_search_path``

        .. note::

            ORACLE does not allow a fallback to the current USER schema like in
            PostgreSQL with the ``public`` schema
        '''
        if self.schema_name is None:
            if settings.DEBUG:
                full_info = " Choices are: %s." \
                            % ', '.join(settings.SCHEMATA_DOMAINS.keys())
            else:
                full_info = ""
            raise ImproperlyConfigured("Database schema not set (you can pick "
                                       "one of the supported domains by setting "
                                       "then DJANGO_SCHEMATA_DOMAIN environment "
                                       "variable.%s)" % full_info)

        base_sql_command = 'ALTER SESSION SET current_schema = '

        if self.schema_name == '':
            # set the current_schema to a current USER
            cursor.execute("""begin
                    EXECUTE IMMEDIATE '%s' || USER; 
                    end;
                    /""" % base_sql_command)
        else:
            _check_identifier(self.schema_name)
            sql_command = base_sql_command + self.schema_name
            cursor.execute(sql_command)

    def set_schemata_domain(self, domain_name):
        """
        Main API method to current database schema,
        but it does not actually modify the db connection.
        Returns the particular domain dict from settings.SCHEMATA_DOMAINS. 
        """
        sd = self._resolve_schema_domain(domain_name)
        self.schema_name = sd['schema_name']
        return sd

    def set_schemata_off(self):
        """
        Instructs to stay in the common 'public' schema.
        """
        self.schema_name = ''

    def _cursor(self):
        """
        Here it happens. We hope every Django db operation using Oracle
        must go through this to get the cursor handle.
        """ 
        cursor = super(DatabaseWrapper, self)._cursor()
        self._set_oracle_default_schema(cursor)
        return cursor

DatabaseError = original_backend.DatabaseError
IntegrityError = original_backend.IntegrityError

########NEW FILE########
__FILENAME__ = base
import os, re

from django.conf import settings
from django.utils.importlib import import_module
from django.core.exceptions import ImproperlyConfigured

ORIGINAL_BACKEND = getattr(settings, 'ORIGINAL_BACKEND', 'django.db.backends.postgresql_psycopg2')

original_backend = import_module('.base', ORIGINAL_BACKEND)

# from the postgresql doc
SQL_IDENTIFIER_RE = re.compile('^[_a-zA-Z][_a-zA-Z0-9]{,62}$')

def _check_identifier(identifier):
    if not SQL_IDENTIFIER_RE.match(identifier):
        raise RuntimeError("Invalid string used for the schema name.")

class DatabaseWrapper(original_backend.DatabaseWrapper):
    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        # By default the schema is not set
        self.schema_name = None

        # but one can change the default using the environment variable.
        force_domain = os.getenv('DJANGO_SCHEMATA_DOMAIN')
        if force_domain:
            self.schema_name = self._resolve_schema_domain(force_domain)['schema_name']

    def _resolve_schema_domain(self, domain_name):
        try:
            sd = settings.SCHEMATA_DOMAINS[domain_name]
        except KeyError:
            raise ImproperlyConfigured("Domain '%s' is not supported by "
                                       "settings.SCHEMATA_DOMAINS" % domain_name)
        return sd

    def _set_pg_search_path(self, cursor):
        """
        Actual search_path modification for the cursor. Database will
        search schemata from left to right when looking for the object
        (table, index, sequence, etc.).
        """
        if self.schema_name is None:
            if settings.DEBUG:
                full_info = " Choices are: %s." \
                            % ', '.join(settings.SCHEMATA_DOMAINS.keys())
            else:
                full_info = ""
            raise ImproperlyConfigured("Database schema not set (you can pick "
                                       "one of the supported domains by setting "
                                       "then DJANGO_SCHEMATA_DOMAIN environment "
                                       "variable.%s)" % full_info)

        _check_identifier(self.schema_name)
        if self.schema_name == 'public':
            cursor.execute('SET search_path = public')
        else:
            cursor.execute('SET search_path = %s, public', [self.schema_name])

    def set_schemata_domain(self, domain_name):
        """
        Main API method to current database schema,
        but it does not actually modify the db connection.
        Returns the particular domain dict from settings.SCHEMATA_DOMAINS. 
        """
        sd = self._resolve_schema_domain(domain_name)
        self.schema_name = sd['schema_name']
        return sd

    def set_schemata_off(self):
        """
        Instructs to stay in the common 'public' schema.
        """
        self.schema_name = 'public'

    def _cursor(self):
        """
        Here it happens. We hope every Django db operation using PostgreSQL
        must go through this to get the cursor handle. We change the path.
        """ 
        cursor = super(DatabaseWrapper, self)._cursor()
        self._set_pg_search_path(cursor)
        return cursor

DatabaseError = original_backend.DatabaseError
IntegrityError = original_backend.IntegrityError

########NEW FILE########
__FILENAME__ = tests
from django import test
from django.db import connection
from django.core.exceptions import ImproperlyConfigured
from django_schemata.postgresql_backend.base import DatabaseError
from django.db.utils import DatabaseError
from django.conf import settings
from django.core.management import call_command
from django.contrib.sites.models import Site

# only run this test if the custom database wrapper is in use.
if hasattr(connection, 'schema_name'):

    # This will fail with Django==1.3.1 AND psycopg2==2.4.2
    # See https://code.djangoproject.com/ticket/16250
    # Either upgrade Django to trunk or use psycopg2==2.4.1
    connection.set_schemata_off()


    def set_schematas(domain):
        settings.SCHEMATA_DOMAINS = {
            domain: {
                'schema_name': domain,
            }
        }


    def add_schemata(domain):
        settings.SCHEMATA_DOMAINS.update({
            domain: {
                'schema_name': domain,
            }
        })


    class SchemataTestCase(test.TestCase):
        def setUp(self):
            set_schematas('blank')
            self.c = test.client.Client()

        def tearDown(self):
            connection.set_schemata_off()

        def test_unconfigured_domain(self):
            self.assertRaises(ImproperlyConfigured, self.c.get, '/')

        def test_unmanaged_domain(self):
            add_schemata('not_in_db')
            self.assertRaises(DatabaseError, self.c.get, '/', HTTP_HOST='not_in_db')

        def test_domain_switch(self):
            add_schemata('test1')
            add_schemata('test2')
            call_command('manage_schemata')

            self.c.get('/', HTTP_HOST='test1')
            test1 = Site.objects.get(id=1)
            test1.domain = 'test1'
            test1.save()

            self.c.get('/', HTTP_HOST='test2')
            test2 = Site.objects.get(id=1)
            test2.domain = 'test2'
            test2.save()

            self.c.get('/', HTTP_HOST='test1')
            test = Site.objects.get_current()
            self.assertEqual(test.domain, 'test1', 'Current site should be "test1", not "%s"' % test.domain)

########NEW FILE########
__FILENAME__ = version
# -*- coding: utf-8 -*-
# Author: Douglas Creager <dcreager@dcreager.net>
# This file is placed into the public domain.

# Calculates the current version number.  If possible, this is the
# output of “git describe”, modified to conform to the versioning
# scheme that setuptools uses.  If “git describe” returns an error
# (most likely because we're in an unpacked copy of a release tarball,
# rather than in a git working copy), then we fall back on reading the
# contents of the VERSION file.
#
# To use this script, simply import it your setup.py file, and use the
# results of get_git_version() as your package version:
#
# from version import *
#
# setup(
#     version=get_git_version(),
#     .
#     .
#     .
# )
#
# This will automatically update the VERSION file, if
# necessary.  Note that the VERSION file should *not* be
# checked into git; please add it to your top-level .gitignore file.
#
# You'll probably want to distribute the VERSION file in your
# sdist tarballs; to do this, just create a MANIFEST.in file that
# contains the following line:
#
#   include VERSION

__all__ = ("get_git_version")

from subprocess import Popen, PIPE


def call_git_describe():
    try:
        p = Popen(['git', 'describe', '--tags', '--always'],
                  stdout=PIPE, stderr=PIPE)
        p.stderr.close()
        line = p.stdout.readlines()[0]
        return line.strip()

    except:
        return None


def read_release_version():
    try:
        f = open("VERSION", "r")

        try:
            version = f.readlines()[0]
            return version.strip()

        finally:
            f.close()

    except:
        return None


def write_release_version(version):
    f = open("VERSION", "w")
    f.write("%s\n" % version)
    f.close()


def get_git_version():
    # Read in the version that's currently in VERSION.

    release_version = read_release_version()

    # First try to get the current version using “git describe”.

    version = call_git_describe()

    # If that doesn't work, fall back on the value that's in
    # VERSION.

    if version is None:
        version = release_version

    # If we still don't have anything, that's an error.

    if version is None:
        raise ValueError("Cannot find the version number!")

    # If the current version is different from what's in the
    # VERSION file, update the file to be current.

    if version != release_version:
        write_release_version(version)

    # Finally, return the current version.

    return version


if __name__ == "__main__":
    print get_git_version()

########NEW FILE########
