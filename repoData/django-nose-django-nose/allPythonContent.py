__FILENAME__ = fixture_tables
"""A copy of Django 1.3.0's stock loaddata.py, adapted so that, instead of
loading any data, it returns the tables referenced by a set of fixtures so we
can truncate them (and no others) quickly after we're finished with them."""

import os
import gzip
import zipfile
from itertools import product

from django.conf import settings
from django.core import serializers
from django.db import router, DEFAULT_DB_ALIAS
from django.db.models import get_apps

try:
    import bz2
    has_bz2 = True
except ImportError:
    has_bz2 = False


def tables_used_by_fixtures(fixture_labels, using=DEFAULT_DB_ALIAS):
    """Act like Django's stock loaddata command, but, instead of loading data,
    return an iterable of the names of the tables into which data would be
    loaded."""
    # Keep a count of the installed objects and fixtures
    fixture_count = 0
    loaded_object_count = 0
    fixture_object_count = 0
    tables = set()

    class SingleZipReader(zipfile.ZipFile):
        def __init__(self, *args, **kwargs):
            zipfile.ZipFile.__init__(self, *args, **kwargs)
            if settings.DEBUG:
                assert len(self.namelist()) == 1, "Zip-compressed fixtures must contain only one file."
        def read(self):
            return zipfile.ZipFile.read(self, self.namelist()[0])

    compression_types = {
        None:   file,
        'gz':   gzip.GzipFile,
        'zip':  SingleZipReader
    }
    if has_bz2:
        compression_types['bz2'] = bz2.BZ2File

    app_module_paths = []
    for app in get_apps():
        if hasattr(app, '__path__'):
            # It's a 'models/' subpackage
            for path in app.__path__:
                app_module_paths.append(path)
        else:
            # It's a models.py module
            app_module_paths.append(app.__file__)

    app_fixtures = [os.path.join(os.path.dirname(path), 'fixtures') for path in app_module_paths]
    for fixture_label in fixture_labels:
        parts = fixture_label.split('.')

        if len(parts) > 1 and parts[-1] in compression_types:
            compression_formats = [parts[-1]]
            parts = parts[:-1]
        else:
            compression_formats = list(compression_types.keys())

        if len(parts) == 1:
            fixture_name = parts[0]
            formats = serializers.get_public_serializer_formats()
        else:
            fixture_name, format = '.'.join(parts[:-1]), parts[-1]
            if format in serializers.get_public_serializer_formats():
                formats = [format]
            else:
                formats = []

        if not formats:
            # stderr.write(style.ERROR("Problem installing fixture '%s': %s is
            # not a known serialization format.\n" % (fixture_name, format)))
            return set()

        if os.path.isabs(fixture_name):
            fixture_dirs = [fixture_name]
        else:
            fixture_dirs = app_fixtures + list(settings.FIXTURE_DIRS) + ['']

        for fixture_dir in fixture_dirs:
            # stdout.write("Checking %s for fixtures...\n" %
            # humanize(fixture_dir))

            label_found = False
            for combo in product([using, None], formats, compression_formats):
                database, format, compression_format = combo
                file_name = '.'.join(
                    p for p in [
                        fixture_name, database, format, compression_format
                    ]
                    if p
                )

                # stdout.write("Trying %s for %s fixture '%s'...\n" % \
                # (humanize(fixture_dir), file_name, fixture_name))
                full_path = os.path.join(fixture_dir, file_name)
                open_method = compression_types[compression_format]
                try:
                    fixture = open_method(full_path, 'r')
                    if label_found:
                        fixture.close()
                        # stderr.write(style.ERROR("Multiple fixtures named
                        # '%s' in %s. Aborting.\n" % (fixture_name,
                        # humanize(fixture_dir))))
                        return set()
                    else:
                        fixture_count += 1
                        objects_in_fixture = 0
                        loaded_objects_in_fixture = 0
                        # stdout.write("Installing %s fixture '%s' from %s.\n"
                        # % (format, fixture_name, humanize(fixture_dir)))
                        try:
                            objects = serializers.deserialize(format, fixture, using=using)
                            for obj in objects:
                                objects_in_fixture += 1
                                if router.allow_syncdb(using, obj.object.__class__):
                                    loaded_objects_in_fixture += 1
                                    tables.add(
                                        obj.object.__class__._meta.db_table)
                            loaded_object_count += loaded_objects_in_fixture
                            fixture_object_count += objects_in_fixture
                            label_found = True
                        except (SystemExit, KeyboardInterrupt):
                            raise
                        except Exception:
                            fixture.close()
                            # stderr.write( style.ERROR("Problem installing
                            # fixture '%s': %s\n" % (full_path, ''.join(tra
                            # ceback.format_exception(sys.exc_type,
                            # sys.exc_value, sys.exc_traceback)))))
                            return set()
                        fixture.close()

                        # If the fixture we loaded contains 0 objects, assume that an
                        # error was encountered during fixture loading.
                        if objects_in_fixture == 0:
                            # stderr.write( style.ERROR("No fixture data found
                            # for '%s'. (File format may be invalid.)\n" %
                            # (fixture_name)))
                            return set()

                except Exception:
                    # stdout.write("No %s fixture '%s' in %s.\n" % \ (format,
                    # fixture_name, humanize(fixture_dir)))
                    pass

    return tables

########NEW FILE########
__FILENAME__ = test
"""
Add extra options from the test runner to the ``test`` command, so that you can
browse all the nose options from the command line.
"""
from django.conf import settings
from django.test.utils import get_runner


if 'south' in settings.INSTALLED_APPS:
    from south.management.commands.test import Command
else:
    from django.core.management.commands.test import Command


# Django < 1.2 compatibility
test_runner = settings.TEST_RUNNER
if test_runner.endswith('run_tests') or test_runner.endswith('run_gis_tests'):
    import warnings
    warnings.warn(
        'Use `django_nose.NoseTestSuiteRunner` instead of `%s`' % test_runner,
        DeprecationWarning)


TestRunner = get_runner(settings)

if hasattr(TestRunner, 'options'):
    extra_options = TestRunner.options
else:
    extra_options = []


class Command(Command):
    option_list = Command.option_list + tuple(extra_options)

########NEW FILE########
__FILENAME__ = plugin
import sys

from nose.plugins.base import Plugin
from nose.suite import ContextSuite

from django.test.testcases import TransactionTestCase, TestCase

from django_nose.testcases import FastFixtureTestCase
from django_nose.utils import process_tests, is_subclass_at_all


class AlwaysOnPlugin(Plugin):
    """A plugin that takes no options and is always enabled"""

    def options(self, parser, env):
        """Avoid adding a ``--with`` option for this plugin.

        We don't have any options, and this plugin is always enabled, so we
        don't want to use superclass's ``options()`` method which would add a
        ``--with-*`` option.

        """

    def configure(self, *args, **kw_args):
        super(AlwaysOnPlugin, self).configure(*args, **kw_args)
        self.enabled = True  # Force this plugin to be always enabled.


class ResultPlugin(AlwaysOnPlugin):
    """Captures the TestResult object for later inspection

    nose doesn't return the full test result object from any of its runner
    methods.  Pass an instance of this plugin to the TestProgram and use
    ``result`` after running the tests to get the TestResult object.

    """
    name = 'result'

    def finalize(self, result):
        self.result = result


class DjangoSetUpPlugin(AlwaysOnPlugin):
    """Configures Django to set up and tear down the environment

    This allows coverage to report on all code imported and used during the
    initialization of the test runner.

    """
    name = 'django setup'

    def __init__(self, runner):
        super(DjangoSetUpPlugin, self).__init__()
        self.runner = runner
        self.sys_stdout = sys.stdout

    def prepareTest(self, test):
        """Create the Django DB and model tables, and do other setup.

        This isn't done in begin() because that's too early--the DB has to be
        set up *after* the tests are imported so the model registry contains
        models defined in tests.py modules. Models are registered at
        declaration time by their metaclass.

        prepareTestRunner() might also have been a sane choice, except that, if
        some plugin returns something from it, none of the other ones get
        called. I'd rather not dink with scores if I don't have to.

        """
        # What is this stdout switcheroo for?
        sys_stdout = sys.stdout
        sys.stdout = self.sys_stdout

        self.runner.setup_test_environment()
        self.old_names = self.runner.setup_databases()

        sys.stdout = sys_stdout

    def finalize(self, result):
        self.runner.teardown_databases(self.old_names)
        self.runner.teardown_test_environment()


class Bucketer(object):
    def __init__(self):
        # { (frozenset(['users.json']), True):
        #      [ContextSuite(...), ContextSuite(...)] }
        self.buckets = {}

        # All the non-FastFixtureTestCase tests we saw, in the order they came
        # in:
        self.remainder = []

    def add(self, test):
        """Put a test into a bucket according to its set of fixtures and the
        value of its exempt_from_fixture_bundling attr."""
        if is_subclass_at_all(test.context, FastFixtureTestCase):
            # We bucket even FFTCs that don't have any fixtures, but it
            # shouldn't matter.
            key = (frozenset(getattr(test.context, 'fixtures', [])),
                   getattr(test.context,
                           'exempt_from_fixture_bundling',
                           False))
            self.buckets.setdefault(key, []).append(test)
        else:
            self.remainder.append(test)


class TestReorderer(AlwaysOnPlugin):
    """Reorder tests for various reasons."""
    name = 'django-nose-test-reorderer'

    def options(self, parser, env):
        super(TestReorderer, self).options(parser, env)  # pointless
        parser.add_option('--with-fixture-bundling',
                          action='store_true',
                          dest='with_fixture_bundling',
                          default=env.get('NOSE_WITH_FIXTURE_BUNDLING', False),
                          help='Load a unique set of fixtures only once, even '
                               'across test classes. '
                               '[NOSE_WITH_FIXTURE_BUNDLING]')

    def configure(self, options, conf):
        super(TestReorderer, self).configure(options, conf)
        self.should_bundle = options.with_fixture_bundling

    def _put_transaction_test_cases_last(self, test):
        """Reorder tests in the suite so TransactionTestCase-based tests come
        last.

        Django has a weird design decision wherein TransactionTestCase doesn't
        clean up after itself. Instead, it resets the DB to a clean state only
        at the *beginning* of each test:
        https://docs.djangoproject.com/en/dev/topics/testing/?from=olddocs#
        django. test.TransactionTestCase. Thus, Django reorders tests so
        TransactionTestCases all come last. Here we do the same.

        "I think it's historical. We used to have doctests also, adding cleanup
        after each unit test wouldn't necessarily clean up after doctests, so
        you'd have to clean on entry to a test anyway." was once uttered on
        #django-dev.

        """

        def filthiness(test):
            """Return a comparand based on whether a test is guessed to clean
            up after itself.

            Django's TransactionTestCase doesn't clean up the DB on teardown,
            but it's hard to guess whether subclasses (other than TestCase) do.
            We will assume they don't, unless they have a
            ``cleans_up_after_itself`` attr set to True. This is reasonable
            because the odd behavior of TransactionTestCase is documented, so
            subclasses should by default be assumed to preserve it.

            Thus, things will get these comparands (and run in this order):

            * 1: TestCase subclasses. These clean up after themselves.
            * 1: TransactionTestCase subclasses with
                 cleans_up_after_itself=True. These include
                 FastFixtureTestCases. If you're using the
                 FixtureBundlingPlugin, it will pull the FFTCs out, reorder
                 them, and run them first of all.
            * 2: TransactionTestCase subclasses. These leave a mess.
            * 2: Anything else (including doctests, I hope). These don't care
                 about the mess you left, because they don't hit the DB or, if
                 they do, are responsible for ensuring that it's clean (as per
                 https://docs.djangoproject.com/en/dev/topics/testing/?from=
                 olddocs#writing-doctests)

            """
            test_class = test.context
            if (is_subclass_at_all(test_class, TestCase) or
                (is_subclass_at_all(test_class, TransactionTestCase) and
                  getattr(test_class, 'cleans_up_after_itself', False))):
                return 1
            return 2

        flattened = []
        process_tests(test, flattened.append)
        flattened.sort(key=filthiness)
        return ContextSuite(flattened)

    def _bundle_fixtures(self, test):
        """Reorder the tests in the suite so classes using identical
        sets of fixtures are contiguous.

        I reorder FastFixtureTestCases so ones using identical sets
        of fixtures run adjacently. I then put attributes on them
        to advise them to not reload the fixtures for each class.

        This takes support.mozilla.com's suite from 123s down to 94s.

        FastFixtureTestCases are the only ones we care about, because
        nobody else, in practice, pays attention to the ``_fb`` advisory
        bits. We return those first, then any remaining tests in the
        order they were received.

        """
        def suite_sorted_by_fixtures(suite):
            """Flatten and sort a tree of Suites by the ``fixtures`` members of
            their contexts.

            Add ``_fb_should_setup_fixtures`` and
            ``_fb_should_teardown_fixtures`` attrs to each test class to advise
            it whether to set up or tear down (respectively) the fixtures.

            Return a Suite.

            """
            bucketer = Bucketer()
            process_tests(suite, bucketer.add)

            # Lay the bundles of common-fixture-having test classes end to end
            # in a single list so we can make a test suite out of them:
            flattened = []
            for ((fixtures, is_exempt), fixture_bundle) in bucketer.buckets.items():
                # Advise first and last test classes in each bundle to set up
                # and tear down fixtures and the rest not to:
                if fixtures and not is_exempt:
                    # Ones with fixtures are sure to be classes, which means
                    # they're sure to be ContextSuites with contexts.

                    # First class with this set of fixtures sets up:
                    first = fixture_bundle[0].context
                    first._fb_should_setup_fixtures = True

                    # Set all classes' 1..n should_setup to False:
                    for cls in fixture_bundle[1:]:
                        cls.context._fb_should_setup_fixtures = False

                    # Last class tears down:
                    last = fixture_bundle[-1].context
                    last._fb_should_teardown_fixtures = True

                    # Set all classes' 0..(n-1) should_teardown to False:
                    for cls in fixture_bundle[:-1]:
                        cls.context._fb_should_teardown_fixtures = False

                flattened.extend(fixture_bundle)
            flattened.extend(bucketer.remainder)

            return ContextSuite(flattened)

        return suite_sorted_by_fixtures(test)

    def prepareTest(self, test):
        """Reorder the tests."""
        test = self._put_transaction_test_cases_last(test)
        if self.should_bundle:
            test = self._bundle_fixtures(test)
        return test

########NEW FILE########
__FILENAME__ = runner
"""Django test runner that invokes nose.

You can use... ::

    NOSE_ARGS = ['list', 'of', 'args']

in settings.py for arguments that you want always passed to nose.

"""
from __future__ import print_function
import os
import sys
from optparse import make_option
from types import MethodType

from django.conf import settings
from django.core import exceptions
from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.core.management.commands.loaddata import Command
from django.db import connections, transaction, DEFAULT_DB_ALIAS, models
from django.db.backends.creation import BaseDatabaseCreation
from django.test.simple import DjangoTestSuiteRunner
from django.utils.importlib import import_module

import nose.core

from django_nose.plugin import DjangoSetUpPlugin, ResultPlugin, TestReorderer
from django_nose.utils import uses_mysql

try:
    any
except NameError:
    def any(iterable):
        for element in iterable:
            if element:
                return True
        return False


__all__ = ['BasicNoseRunner', 'NoseTestSuiteRunner']


# This is a table of Django's "manage.py test" options which
# correspond to nosetests options with a different name:
OPTION_TRANSLATION = {'--failfast': '-x',
                      '--nose-verbosity': '--verbosity'}


def translate_option(opt):
    if '=' in opt:
        long_opt, value = opt.split('=', 1)
        return '%s=%s' % (translate_option(long_opt), value)
    return OPTION_TRANSLATION.get(opt, opt)


# Django v1.2 does not have a _get_test_db_name() function.
if not hasattr(BaseDatabaseCreation, '_get_test_db_name'):
    def _get_test_db_name(self):
        TEST_DATABASE_PREFIX = 'test_'

        if self.connection.settings_dict['TEST_NAME']:
            return self.connection.settings_dict['TEST_NAME']
        return TEST_DATABASE_PREFIX + self.connection.settings_dict['NAME']

    BaseDatabaseCreation._get_test_db_name = _get_test_db_name


def _get_plugins_from_settings():
    plugins = (list(getattr(settings, 'NOSE_PLUGINS', [])) +
               ['django_nose.plugin.TestReorderer'])
    for plug_path in plugins:
        try:
            dot = plug_path.rindex('.')
        except ValueError:
            raise exceptions.ImproperlyConfigured(
                    "%s isn't a Nose plugin module" % plug_path)
        p_mod, p_classname = plug_path[:dot], plug_path[dot + 1:]

        try:
            mod = import_module(p_mod)
        except ImportError as e:
            raise exceptions.ImproperlyConfigured(
                    'Error importing Nose plugin module %s: "%s"' % (p_mod, e))

        try:
            p_class = getattr(mod, p_classname)
        except AttributeError:
            raise exceptions.ImproperlyConfigured(
                    'Nose plugin module "%s" does not define a "%s"' %
                    (p_mod, p_classname))

        yield p_class()


def _get_options():
    """Return all nose options that don't conflict with django options."""
    cfg_files = nose.core.all_config_files()
    manager = nose.core.DefaultPluginManager()
    config = nose.core.Config(env=os.environ, files=cfg_files, plugins=manager)
    config.plugins.addPlugins(list(_get_plugins_from_settings()))
    options = config.getParser()._get_all_options()

    # copy nose's --verbosity option and rename to --nose-verbosity
    verbosity = [o for o in options if o.get_opt_string() == '--verbosity'][0]
    verbosity_attrs = dict((attr, getattr(verbosity, attr))
                           for attr in verbosity.ATTRS
                           if attr not in ('dest', 'metavar'))
    options.append(make_option('--nose-verbosity',
                               dest='nose_verbosity',
                               metavar='NOSE_VERBOSITY',
                               **verbosity_attrs))

    # Django 1.6 introduces a "--pattern" option, which is shortened into "-p"
    # do not allow "-p" to collide with nose's "--plugins" option.
    plugins_option = [o for o in options if o.get_opt_string() == '--plugins'][0]
    plugins_option._short_opts.remove('-p')

    django_opts = [opt.dest for opt in BaseCommand.option_list] + ['version']
    return tuple(o for o in options if o.dest not in django_opts and
                                       o.action != 'help')


class BasicNoseRunner(DjangoTestSuiteRunner):
    """Facade that implements a nose runner in the guise of a Django runner

    You shouldn't have to use this directly unless the additions made by
    ``NoseTestSuiteRunner`` really bother you. They shouldn't, because they're
    all off by default.

    """
    __test__ = False

    # Replace the builtin command options with the merged django/nose options:
    options = _get_options()

    def run_suite(self, nose_argv):
        result_plugin = ResultPlugin()
        plugins_to_add = [DjangoSetUpPlugin(self),
                          result_plugin,
                          TestReorderer()]

        for plugin in _get_plugins_from_settings():
            plugins_to_add.append(plugin)

        nose.core.TestProgram(argv=nose_argv, exit=False,
                              addplugins=plugins_to_add)
        return result_plugin.result

    def run_tests(self, test_labels, extra_tests=None):
        """Run the unit tests for all the test names in the provided list.

        Test names specified may be file or module names, and may optionally
        indicate the test case to run by separating the module or file name
        from the test case name with a colon. Filenames may be relative or
        absolute.

        N.B.: The test_labels argument *MUST* be a sequence of
        strings, *NOT* just a string object.  (Or you will be
        specifying tests for for each character in your string, and
        not the whole string.

        Examples:

        runner.run_tests( ('test.module',) )
        runner.run_tests(['another.test:TestCase.test_method'])
        runner.run_tests(['a.test:TestCase'])
        runner.run_tests(['/path/to/test/file.py:test_function'])
        runner.run_tests( ('test.module', 'a.test:TestCase') )

        Note: the extra_tests argument is currently ignored.  You can
        run old non-nose code that uses it without totally breaking,
        but the extra tests will not be run.  Maybe later.

        Returns the number of tests that failed.

        """
        nose_argv = (['nosetests'] + list(test_labels))
        if hasattr(settings, 'NOSE_ARGS'):
            nose_argv.extend(settings.NOSE_ARGS)

        # Skip over 'manage.py test' and any arguments handled by django.
        django_opts = ['--noinput', '--liveserver', '-p', '--pattern']
        for opt in BaseCommand.option_list:
            django_opts.extend(opt._long_opts)
            django_opts.extend(opt._short_opts)

        nose_argv.extend(translate_option(opt) for opt in sys.argv[1:]
        if opt.startswith('-')
           and not any(opt.startswith(d) for d in django_opts))

        # if --nose-verbosity was omitted, pass Django verbosity to nose
        if ('--verbosity' not in nose_argv and
                not any(opt.startswith('--verbosity=') for opt in nose_argv)):
            nose_argv.append('--verbosity=%s' % str(self.verbosity))

        if self.verbosity >= 1:
            print(' '.join(nose_argv))

        result = self.run_suite(nose_argv)
        # suite_result expects the suite as the first argument.  Fake it.
        return self.suite_result({}, result)


_old_handle = Command.handle


def _foreign_key_ignoring_handle(self, *fixture_labels, **options):
    """Wrap the the stock loaddata to ignore foreign key
    checks so we can load circular references from fixtures.

    This is monkeypatched into place in setup_databases().

    """
    using = options.get('database', DEFAULT_DB_ALIAS)
    commit = options.get('commit', True)
    connection = connections[using]

    # MySQL stinks at loading circular references:
    if uses_mysql(connection):
        cursor = connection.cursor()
        cursor.execute('SET foreign_key_checks = 0')

    _old_handle(self, *fixture_labels, **options)

    if uses_mysql(connection):
        cursor = connection.cursor()
        cursor.execute('SET foreign_key_checks = 1')

        if commit:
            connection.close()


def _skip_create_test_db(self, verbosity=1, autoclobber=False):
    """``create_test_db`` implementation that skips both creation and flushing

    The idea is to re-use the perfectly good test DB already created by an
    earlier test run, cutting the time spent before any tests run from 5-13s
    (depending on your I/O luck) down to 3.

    """
    # Notice that the DB supports transactions. Originally, this was done in
    # the method this overrides. The confirm method was added in Django v1.3
    # (https://code.djangoproject.com/ticket/12991) but removed in Django v1.5
    # (https://code.djangoproject.com/ticket/17760). In Django v1.5
    # supports_transactions is a cached property evaluated on access.
    if callable(getattr(self.connection.features, 'confirm', None)):
        # Django v1.3-4
        self.connection.features.confirm()
    elif hasattr(self, "_rollback_works"):
        # Django v1.2 and lower
        can_rollback = self._rollback_works()
        self.connection.settings_dict['SUPPORTS_TRANSACTIONS'] = can_rollback

    return self._get_test_db_name()


def _reusing_db():
    """Return whether the ``REUSE_DB`` flag was passed"""
    return os.getenv('REUSE_DB', 'false').lower() in ('true', '1', '')


def _can_support_reuse_db(connection):
    """Return whether it makes any sense to
    use REUSE_DB with the backend of a connection."""
    # Perhaps this is a SQLite in-memory DB. Those are created implicitly when
    # you try to connect to them, so our usual test doesn't work.
    return not connection.creation._get_test_db_name() == ':memory:'


def _should_create_database(connection):
    """Return whether we should recreate the given DB.

    This is true if the DB doesn't exist or the REUSE_DB env var isn't truthy.

    """
    # TODO: Notice when the Model classes change and return True. Worst case,
    # we can generate sqlall and hash it, though it's a bit slow (2 secs) and
    # hits the DB for no good reason. Until we find a faster way, I'm inclined
    # to keep making people explicitly saying REUSE_DB if they want to reuse
    # the DB.

    if not _can_support_reuse_db(connection):
        return True

    # Notice whether the DB exists, and create it if it doesn't:
    try:
        connection.cursor()
    except Exception:  # TODO: Be more discerning but still DB agnostic.
        return True
    return not _reusing_db()


def _mysql_reset_sequences(style, connection):
    """Return a list of SQL statements needed to
    reset all sequences for Django tables."""
    tables = connection.introspection.django_table_names(only_existing=True)
    flush_statements = connection.ops.sql_flush(
            style, tables, connection.introspection.sequence_list())

    # connection.ops.sequence_reset_sql() is not implemented for MySQL,
    # and the base class just returns []. TODO: Implement it by pulling
    # the relevant bits out of sql_flush().
    return [s for s in flush_statements if s.startswith('ALTER')]
    # Being overzealous and resetting the sequences on non-empty tables
    # like django_content_type seems to be fine in MySQL: adding a row
    # afterward does find the correct sequence number rather than
    # crashing into an existing row.


class NoseTestSuiteRunner(BasicNoseRunner):
    """A runner that optionally skips DB creation

    Monkeypatches connection.creation to let you skip creating databases if
    they already exist. Your tests will start up much faster.

    To opt into this behavior, set the environment variable ``REUSE_DB`` to
    something that isn't "0" or "false" (case insensitive).

    """

    def _get_models_for_connection(self, connection):
        """Return a list of models for a connection."""
        tables = connection.introspection.get_table_list(connection.cursor())
        return [m for m in models.loading.cache.get_models() if
                m._meta.db_table in tables]

    def setup_databases(self):
        for alias in connections:
            connection = connections[alias]
            creation = connection.creation
            test_db_name = creation._get_test_db_name()

            # Mess with the DB name so other things operate on a test DB
            # rather than the real one. This is done in create_test_db when
            # we don't monkeypatch it away with _skip_create_test_db.
            orig_db_name = connection.settings_dict['NAME']
            connection.settings_dict['NAME'] = test_db_name

            if _should_create_database(connection):
                # We're not using _skip_create_test_db, so put the DB name
                # back:
                connection.settings_dict['NAME'] = orig_db_name

                # Since we replaced the connection with the test DB, closing
                # the connection will avoid pooling issues with SQLAlchemy. The
                # issue is trying to CREATE/DROP the test database using a
                # connection to a DB that was established with that test DB.
                # MySQLdb doesn't allow it, and SQLAlchemy attempts to reuse
                # the existing connection from its pool.
                connection.close()
            else:
                # Reset auto-increment sequences. Apparently, SUMO's tests are
                # horrid and coupled to certain numbers.
                cursor = connection.cursor()
                style = no_style()

                if uses_mysql(connection):
                    reset_statements = _mysql_reset_sequences(
                        style, connection)
                else:
                    reset_statements = connection.ops.sequence_reset_sql(
                            style, self._get_models_for_connection(connection))

                for reset_statement in reset_statements:
                    cursor.execute(reset_statement)

                # Django v1.3 (https://code.djangoproject.com/ticket/9964)
                # starts using commit_unless_managed() for individual
                # connections. Backwards compatibility for Django 1.2 is to use
                # the generic transaction function.
                transaction.commit_unless_managed(using=connection.alias)

                # Each connection has its own creation object, so this affects
                # only a single connection:
                creation.create_test_db = MethodType(
                        _skip_create_test_db, creation, creation.__class__)

        Command.handle = _foreign_key_ignoring_handle

        # With our class patch, does nothing but return some connection
        # objects:
        return super(NoseTestSuiteRunner, self).setup_databases()

    def teardown_databases(self, *args, **kwargs):
        """Leave those poor, reusable databases alone if REUSE_DB is true."""
        if not _reusing_db():
            return super(NoseTestSuiteRunner, self).teardown_databases(
                    *args, **kwargs)
        # else skip tearing down the DB so we can reuse it next time

########NEW FILE########
__FILENAME__ = testcases
from django import test
from django.conf import settings
from django.core import cache, mail
from django.core.management import call_command
from django.db import connections, DEFAULT_DB_ALIAS, transaction

from django_nose.fixture_tables import tables_used_by_fixtures
from django_nose.utils import uses_mysql


__all__ = ['FastFixtureTestCase']


class FastFixtureTestCase(test.TransactionTestCase):
    """Test case that loads fixtures once and for all rather than once per test

    Using this can save huge swaths of time while still preserving test
    isolation. Fixture data is loaded at class setup time, and the transaction
    is committed. Commit and rollback methods are then monkeypatched away (like
    in Django's standard TestCase), and each test is run. After each test, the
    monkeypatching is temporarily undone, and a rollback is issued, returning
    the DB content to the pristine fixture state. Finally, upon class teardown,
    the DB is restored to a post-syncdb-like state by deleting the contents of
    any table that had been touched by a fixture (keeping infrastructure tables
    like django_content_type and auth_permission intact).

    Note that this is like Django's TestCase, not its TransactionTestCase, in
    that you cannot do your own commits or rollbacks from within tests.

    For best speed, group tests using the same fixtures into as few classes as
    possible. Better still, don't do that, and instead use the fixture-bundling
    plugin from django-nose, which does it dynamically at test time.

    """
    cleans_up_after_itself = True  # This is the good kind of puppy.

    @classmethod
    def setUpClass(cls):
        """Turn on manual commits. Load and commit the fixtures."""
        if not test.testcases.connections_support_transactions():
            raise NotImplementedError('%s supports only DBs with transaction '
                                      'capabilities.' % cls.__name__)
        for db in cls._databases():
            # These MUST be balanced with one leave_* each:
            transaction.enter_transaction_management(using=db)
            # Don't commit unless we say so:
            transaction.managed(True, using=db)

        cls._fixture_setup()

    @classmethod
    def tearDownClass(cls):
        """Truncate the world, and turn manual commit management back off."""
        cls._fixture_teardown()
        for db in cls._databases():
            # Finish off any transactions that may have happened in
            # tearDownClass in a child method.
            if transaction.is_dirty(using=db):
                transaction.commit(using=db)
            transaction.leave_transaction_management(using=db)

    @classmethod
    def _fixture_setup(cls):
        """Load fixture data, and commit."""
        for db in cls._databases():
            if (hasattr(cls, 'fixtures') and
                getattr(cls, '_fb_should_setup_fixtures', True)):
                # Iff the fixture-bundling test runner tells us we're the first
                # suite having these fixtures, set them up:
                call_command('loaddata', *cls.fixtures, **{'verbosity': 0,
                                                           'commit': False,
                                                           'database': db})
            # No matter what, to preserve the effect of cursor start-up
            # statements...
            transaction.commit(using=db)

    @classmethod
    def _fixture_teardown(cls):
        """Empty (only) the tables we loaded fixtures into, then commit."""
        if hasattr(cls, 'fixtures') and \
           getattr(cls, '_fb_should_teardown_fixtures', True):
            # If the fixture-bundling test runner advises us that the next test
            # suite is going to reuse these fixtures, don't tear them down.
            for db in cls._databases():
                tables = tables_used_by_fixtures(cls.fixtures, using=db)
                # TODO: Think about respecting _meta.db_tablespace, not just
                # db_table.
                if tables:
                    connection = connections[db]
                    cursor = connection.cursor()

                    # TODO: Rather than assuming that anything added to by a
                    # fixture can be emptied, remove only what the fixture
                    # added. This would probably solve input.mozilla.com's
                    # failures (since worked around) with Site objects; they
                    # were loading additional Sites with a fixture, and then
                    # the Django-provided example.com site was evaporating.
                    if uses_mysql(connection):
                        cursor.execute('SET FOREIGN_KEY_CHECKS=0')
                        for table in tables:
                            # Truncate implicitly commits.
                            cursor.execute('TRUNCATE `%s`' % table)
                        # TODO: necessary?
                        cursor.execute('SET FOREIGN_KEY_CHECKS=1')
                    else:
                        for table in tables:
                            cursor.execute('DELETE FROM %s' % table)

                transaction.commit(using=db)
                # cursor.close()  # Should be unnecessary, since we committed
                # any environment-setup statements that come with opening a new
                # cursor when we committed the fixtures.

    def _pre_setup(self):
        """Disable transaction methods, and clear some globals."""
        # Repeat stuff from TransactionTestCase, because I'm not calling its
        # _pre_setup, because that would load fixtures again.
        cache.cache.clear()
        settings.TEMPLATE_DEBUG = settings.DEBUG = False

        test.testcases.disable_transaction_methods()

        self.client = self.client_class()
        #self._fixture_setup()
        self._urlconf_setup()
        mail.outbox = []

        # Clear site cache in case somebody's mutated Site objects and then
        # cached the mutated stuff:
        from django.contrib.sites.models import Site
        Site.objects.clear_cache()

    def _post_teardown(self):
        """Re-enable transaction methods, and roll back any changes.

        Rollback clears any DB changes made by the test so the original fixture
        data is again visible.

        """
        # Rollback any mutations made by tests:
        test.testcases.restore_transaction_methods()
        for db in self._databases():
            transaction.rollback(using=db)

        self._urlconf_teardown()

        # We do not need to close the connection here to prevent
        # http://code.djangoproject.com/ticket/7572, since we commit, not
        # rollback, the test fixtures and thus any cursor startup statements.

        # Don't call through to superclass, because that would call
        # _fixture_teardown() and close the connection.

    @classmethod
    def _databases(cls):
        if getattr(cls, 'multi_db', False):
            return connections
        else:
            return [DEFAULT_DB_ALIAS]

########NEW FILE########
__FILENAME__ = tools
# vim: tabstop=4 expandtab autoindent shiftwidth=4 fileencoding=utf-8

"""
Provides Nose and Django test case assert functions
"""

from django.test.testcases import TransactionTestCase

from django.core import mail

import re

## Python

from nose import tools
for t in dir(tools):
    if t.startswith('assert_'):
        vars()[t] = getattr(tools, t)

## Django

caps = re.compile('([A-Z])')

def pep8(name):
    return caps.sub(lambda m: '_' + m.groups()[0].lower(), name)


class Dummy(TransactionTestCase):
    def nop():
        pass
_t = Dummy('nop')

for at in [ at for at in dir(_t)
            if at.startswith('assert') and not '_' in at ]:
    pepd = pep8(at)
    vars()[pepd] = getattr(_t, at)

del Dummy
del _t
del pep8

## New

def assert_code(response, status_code, msg_prefix=''):
    """Asserts the response was returned with the given status code
    """

    if msg_prefix:
        msg_prefix = '%s: ' % msg_prefix

    assert response.status_code == status_code, \
        'Response code was %d (expected %d)' % \
            (response.status_code, status_code)

def assert_ok(response, msg_prefix=''):
    """Asserts the response was returned with status 200 (OK)
    """

    return assert_code(response, 200, msg_prefix=msg_prefix)

def assert_mail_count(count, msg=None):
    """Assert the number of emails sent.
    The message here tends to be long, so allow for replacing the whole
    thing instead of prefixing.
    """

    if msg is None:
        msg = ', '.join([e.subject for e in mail.outbox])
        msg = '%d != %d %s' % (len(mail.outbox), count, msg)
    assert_equals(len(mail.outbox), count, msg)

# EOF



########NEW FILE########
__FILENAME__ = utils
def process_tests(suite, process):
    """Given a nested disaster of [Lazy]Suites, traverse to the first level
    that has setup or teardown, and do something to them.

    If we were to traverse all the way to the leaves (the Tests)
    indiscriminately and return them, when the runner later calls them, they'd
    run without reference to the suite that contained them, so they'd miss
    their class-, module-, and package-wide setup and teardown routines.

    The nested suites form basically a double-linked tree, and suites will call
    up to their containing suites to run their setups and teardowns, but it
    would be hubris to assume that something you saw fit to setup or teardown
    at the module level is less costly to repeat than DB fixtures. Also, those
    sorts of setups and teardowns are extremely rare in our code. Thus, we
    limit the granularity of bucketing to the first level that has setups or
    teardowns.

    :arg process: The thing to call once we get to a leaf or a test with setup
        or teardown

    """
    if (not hasattr(suite, '_tests') or
        (hasattr(suite, 'hasFixtures') and suite.hasFixtures())):
        # We hit a Test or something with setup, so do the thing. (Note that
        # "fixtures" here means setup or teardown routines, not Django
        # fixtures.)
        process(suite)
    else:
        for t in suite._tests:
            process_tests(t, process)


def is_subclass_at_all(cls, class_info):
    """Return whether ``cls`` is a subclass of ``class_info``.

    Even if ``cls`` is not a class, don't crash. Return False instead.

    """
    try:
        return issubclass(cls, class_info)
    except TypeError:
        return False


def uses_mysql(connection):
    """Return whether the connection represents a MySQL DB."""
    return 'mysql' in connection.settings_dict['ENGINE']

########NEW FILE########
__FILENAME__ = plugins
from nose.plugins import Plugin


plugin_began = False

class SanityCheckPlugin(Plugin):
    enabled = True

    def options(self, parser, env):
        """Register commandline options."""

    def configure(self, options, conf):
        """Configure plugin."""

    def begin(self):
        global plugin_began
        plugin_began = True

########NEW FILE########
__FILENAME__ = test_with_plugins
from nose.tools import eq_


def test_one():
    from testapp import plugins
    eq_(plugins.plugin_began, True)

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import sys

from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3'}},
        INSTALLED_APPS=[
            'django_nose',
        ],
    )

from django_nose import NoseTestSuiteRunner

def runtests(*test_labels):
    runner = NoseTestSuiteRunner(verbosity=1, interactive=True)
    failures = runner.run_tests(test_labels)
    sys.exit(failures)


if __name__ == '__main__':
    runtests(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = settings
DATABASES = {
    'default': {
        'NAME': 'django_master',
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

INSTALLED_APPS = (
    'django_nose',
)

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

SECRET_KEY = 'ssshhhh'

########NEW FILE########
__FILENAME__ = settings_old_style
DATABASES = {
    'default': {
        'NAME': 'django_master',
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

INSTALLED_APPS = (
    'django_nose',
)

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
TEST_RUNNER = 'django_nose.run_tests'

SECRET_KEY = 'sssshhh'

########NEW FILE########
__FILENAME__ = settings_with_plugins
from .settings import *


NOSE_PLUGINS = [
    'testapp.plugins.SanityCheckPlugin'
]

########NEW FILE########
__FILENAME__ = settings_with_south
from .settings import *


INSTALLED_APPS = ('south',) + INSTALLED_APPS

########NEW FILE########
__FILENAME__ = test_for_nose
"""Django's test runner won't find this, but nose will."""


def test_addition():
    assert 1 + 1 == 2

########NEW FILE########
__FILENAME__ = test_only_this
"""Django's test runner won't find this, but nose will."""


def test_multiplication():
    assert 2 * 2 == 4

########NEW FILE########
__FILENAME__ = test_databases
from contextlib import contextmanager
from unittest import TestCase

from django.db.models.loading import cache

from django_nose.runner import NoseTestSuiteRunner


class GetModelsForConnectionTests(TestCase):
    tables = ['test_table%d' % i for i in range(5)]

    def _connection_mock(self, tables):
        class FakeIntrospection(object):
            def get_table_list(*args, **kwargs):
                return tables

        class FakeConnection(object):
            introspection = FakeIntrospection()
            cursor = lambda x: None

        return FakeConnection()

    def _model_mock(self, db_table):
        class FakeModel(object):
            _meta = type('meta', (object,), {'db_table': db_table})()

        return FakeModel()

    @contextmanager
    def _cache_mock(self, tables=[]):
        def get_models(*args, **kwargs):
            return [self._model_mock(t) for t in tables]

        old = cache.get_models
        cache.get_models = get_models
        yield
        cache.get_models = old

    def setUp(self):
        self.runner = NoseTestSuiteRunner()

    def test_no_models(self):
        """For a DB with no tables, return nothing."""
        connection = self._connection_mock([])
        with self._cache_mock(['table1', 'table2']):
            self.assertEqual(
                self.runner._get_models_for_connection(connection), [])

    def test_wrong_models(self):
        """If no tables exists for models, return nothing."""
        connection = self._connection_mock(self.tables)
        with self._cache_mock(['table1', 'table2']):
            self.assertEqual(
                self.runner._get_models_for_connection(connection), [])

    def test_some_models(self):
        """If some of the models has appropriate table in the DB, return matching models."""
        connection = self._connection_mock(self.tables)
        with self._cache_mock(self.tables[1:3]):
            result_tables = [m._meta.db_table for m in
                             self.runner._get_models_for_connection(connection)]
        self.assertEqual(result_tables, self.tables[1:3])

    def test_all_models(self):
        """If all the models have appropriate tables in the DB, return them all."""
        connection = self._connection_mock(self.tables)
        with self._cache_mock(self.tables):
            result_tables = [m._meta.db_table for m in
                             self.runner._get_models_for_connection(connection)]
        self.assertEqual(result_tables, self.tables)

########NEW FILE########
