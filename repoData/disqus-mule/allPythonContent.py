__FILENAME__ = base
import os, os.path
import logging
import multiprocessing
import re
import sys
import time
import unittest
import uuid

from celery.task.control import inspect, broadcast
from celery.task.sets import TaskSet
from fnmatch import fnmatch
from mule import conf
from mule.tasks import run_test
from mule.utils.multithreading import ThreadPool

class FailFastInterrupt(KeyboardInterrupt):
    pass

def load_script(workspace, name):
    if workspace not in conf.WORKSPACES:
        return

    settings = conf.WORKSPACES[workspace]

    script_setting = settings.get(name)
    if not script_setting:
        return

    if script_setting.startswith('/'):
        with open(script_setting, 'r') as fp:
            script = fp.read()
    else:
        script = script_setting
    
    return script

class Mule(object):
    loglevel = logging.INFO
    
    def __init__(self, workspace=None, build_id=None, max_workers=None):
        if not build_id:
            build_id = uuid.uuid4().hex
        
        self.build_id = build_id
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.logger = logging.getLogger('mule')
        self.workspace = workspace
    
    def process(self, jobs, runner='unit2 $TEST', callback=None):
        """
        ``jobs`` is a list of path.to.TestCase strings to process.
        
        ``runner`` should be defined as command exectuable in bash, where $TEST is
        the current job.
        
        ``callback`` will execute a callback after each result is returned, in
        addition to return the aggregate of all results after completion.
        """
        self.logger.info("Processing build %s", self.build_id)

        self.logger.info("Provisioning (up to) %d worker(s)", self.max_workers)
        
        actual = None
        
        while not actual:
            # We need to determine which queues are available to use
            i = inspect()
            active_queues = i.active_queues() or {}
        
            if not active_queues:
                self.logger.error('No queue workers available, retrying in 1s')
                time.sleep(1)
                continue
            
            available = [host for host, queues in active_queues.iteritems() if conf.DEFAULT_QUEUE in [q['name'] for q in queues]]
        
            if not available:
                # TODO: we should probably sleep/retry (assuming there were *any* workers)
                self.logger.info('All workers are busy, retrying in 1s')
                time.sleep(1)
                continue
        
            # Attempt to provision workers which reported as available
            actual = []
            for su_response in broadcast('mule_setup',
                             arguments={'build_id': self.build_id,
                                        'workspace': self.workspace,
                                        'script': load_script(self.workspace, 'setup')},
                             destination=available[:self.max_workers],
                             reply=True,
                             timeout=0):
                for host, message in su_response.iteritems():
                    if message.get('error'):
                        self.logger.error('%s failed to setup: %s', host, message['error'])
                    elif message.get('status') == 'ok':
                        actual.append(host)
                    if message.get('stdout'):
                        self.logger.info('stdout from %s: %s', host, message['stdout'])
                    if message.get('stderr'):
                        self.logger.info('stderr from %s: %s', host, message['stderr'])
        
            if not actual:
                # TODO: we should probably sleep/retry (assuming there were *any* workers)
                self.logger.info('Failed to provision workers (busy), retrying in 1s')
                time.sleep(1)
                continue
        
        if len(actual) != len(available):
            # We should begin running tests and possibly add more, but its not a big deal
            pass

        self.logger.info('%d worker(s) were provisioned', len(actual))
            
        self.logger.info("Building queue of %d test job(s)", len(jobs))
        
        try:
            taskset = TaskSet(run_test.subtask(
                build_id=self.build_id,
                runner=runner,
                workspace=self.workspace,
                job='%s.%s' % (job.__module__, job.__name__),
                options={
                    # 'routing_key': 'mule-%s' % self.build_id,
                    'queue': 'mule-%s' % self.build_id,
                    # 'exchange': 'mule-%s' % self.build_id,
                }) for job in jobs)
            
            result = taskset.apply_async()

            self.logger.info("Waiting for response...")
            # response = result.join()
            # propagate=False ensures we get *all* responses        
            response = []
            try:
                for task_response in result.iterate():
                    response.append(task_response)
                    if callback:
                        callback(task_response)
            except KeyboardInterrupt, e:
                print '\nReceived keyboard interrupt, closing workers.\n'
        
        finally:
            self.logger.info("Tearing down %d worker(s)", len(actual))

            # Send off teardown task to all workers in pool
            for td_response in broadcast('mule_teardown',
                                        arguments={'build_id': self.build_id,
                                                   'workspace': self.workspace,
                                                   'script': load_script(self.workspace, 'teardown')},
                                        destination=actual,
                                        reply=True
                                    ):
                for host, message in td_response.iteritems():
                    if message.get('error'):
                        self.logger.error('%s failed to teardown: %s', host, message['error'])
                    if message.get('stdout'):
                        self.logger.info('stdout from %s: %s', host, message['stdout'])
                    if message.get('stderr'):
                        self.logger.info('stderr from %s: %s', host, message['stderr'])
        
        self.logger.info('Finished')
        
        return response

    def _match_path(self, path, full_path, pattern):
        # override this method to use alternative matching strategy
        return fnmatch(path, pattern)

    def _get_name_from_path(self, path, top_level_dir):
        path = os.path.splitext(os.path.normpath(path))[0]

        _relpath = os.path.relpath(path, top_level_dir)
        assert not os.path.isabs(_relpath), "Path must be within the project"
        assert not _relpath.startswith('..'), "Path must be within the project"

        name = _relpath.replace(os.path.sep, '.')
        return name

    def _get_module_from_name(self, name):
        __import__(name)
        return sys.modules[name]

    def load_tests_from_module(self, module, use_load_tests=True):
        """Return a suite of all tests cases contained in the given module"""
        tests = []
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and issubclass(obj, unittest.TestCase):
                tests.append(obj)

        return tests

    def discover_tests(self, start_dir, pattern='test*.py', top_level_dir=None):
        """
        Used by discovery. Yields test suites it loads.

        (Source: unittest2)
        """
        start_dir = os.path.realpath(start_dir)

        if not top_level_dir:
            top_level_dir = os.path.abspath(os.path.join(start_dir, os.pardir))
            sys.path.insert(0, start_dir)

        VALID_MODULE_NAME = re.compile(r'[_a-z]\w*\.py$', re.IGNORECASE)

        paths = os.listdir(start_dir)

        for path in paths:
            full_path = os.path.join(start_dir, path)
            if os.path.isfile(full_path):
                if not VALID_MODULE_NAME.match(path):
                    # valid Python identifiers only
                    continue
                if not self._match_path(path, full_path, pattern):
                    continue
                # if the test file matches, load it
                name = self._get_name_from_path(full_path, top_level_dir)
                try:
                    module = self._get_module_from_name(name)
                except:
                    # TODO: should this be handled more gracefully?
                    # yield _make_failed_import_test(name, self.suiteClass)
                    raise
                else:
                    mod_file = os.path.abspath(getattr(module, '__file__', full_path))
                    realpath = os.path.splitext(mod_file)[0]
                    fullpath_noext = os.path.splitext(full_path)[0]
                    if realpath.lower() != fullpath_noext.lower():
                        module_dir = os.path.dirname(realpath)
                        mod_name = os.path.splitext(os.path.basename(full_path))[0]
                        expected_dir = os.path.dirname(full_path)
                        msg = ("%r module incorrectly imported from %r. Expected %r. "
                               "Is this module globally installed?")
                        raise ImportError(msg % (mod_name, module_dir, expected_dir))
                    for test in self.load_tests_from_module(module):
                        yield test
            elif os.path.isdir(full_path):
                if not os.path.isfile(os.path.join(full_path, '__init__.py')):
                    continue

                load_tests = None
                tests = None
                if fnmatch(path, pattern):
                    # only check load_tests if the package directory itself matches the filter
                    name = self._get_name_from_path(full_path, top_level_dir)
                    package = self._get_module_from_name(name)
                    load_tests = getattr(package, 'load_tests', None)
                    tests = self.load_tests_from_module(package, use_load_tests=False)

                if tests is not None:
                    # tests loaded from package file
                    yield tests
                # recurse into the package
                for test in self.discover_tests(full_path, pattern, top_level_dir):
                    yield test

class MultiProcessMule(Mule):
    def process(self, jobs, runner='unit2 $TEST', callback=None):
        self.logger.info("Processing build %s", self.build_id)

        self.logger.info("Provisioning %d worker(s)", self.max_workers)
        
        pool = ThreadPool(self.max_workers)

        self.logger.info("Building queue of %d test job(s)", len(jobs))

        for job in jobs:
            pool.add(run_test,
                build_id=self.build_id,
                runner=runner,
                job='%s.%s' % (job.__module__, job.__name__),
                workspace=self.workspace,
                callback=callback,
            )

        self.logger.info("Waiting for response...")

        response = [r['result'] for r in pool.join()]

        self.logger.info("Tearing down %d worker(s)", self.max_workers)

        # TODO
        
        self.logger.info('Finished')
        
        return response
########NEW FILE########
__FILENAME__ = celeryconfig
# This is just an example configuration file

CELERY_RESULT_BACKEND = 'redis'
CELERY_IMPORTS = ('mule.tasks', )

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

BROKER_BACKEND = 'redis'

BROKER_HOST = 'localhost'  # Maps to redis host.
BROKER_PORT = 6379         # Maps to redis port.
BROKER_VHOST = '0'         # Maps to database number.

########NEW FILE########
__FILENAME__ = conf
"""
Default configuration values for Mule.

These can be overrriden (in bulk) using:

>>> mule.utils.conf.configure(**settings)
"""


DEFAULT_QUEUE = 'default'
BUILD_QUEUE_PREFIX = 'mule'

# TODO: this should be some kind of absolute system path, and a sane default
ROOT = 'mule'

WORKSPACES = {
    'default': {
        # setup/teardown should either be an absolute path to a bash script (/foo/bar.sh)
        # or a string containing bash commands
        #
        # global env variables made available:
        # - $BUILD_ID
        # - $WORKSPACE (full path to workspace directory)
        'setup': None,
        'teardown': None,
    }
}
########NEW FILE########
__FILENAME__ = contextmanager
# XXX: Must be an ordered list
context_managers = list()

def register_context_manager(cls):
    if cls not in context_managers:
        context_managers.append(cls)

def get_context_managers():
    return context_managers

class BaseTestContextManager(object):
    # XXX: All context managers MUST handle **kwargs in __init__
    def __init__(self, build_id, suite, **kwargs):
        self.suite = suite
        self.build_id = build_id

    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        pass
########NEW FILE########
__FILENAME__ = contextmanager
from __future__ import absolute_import

from django.conf import settings
from django.core.management import call_command
from django.db import connections, router
from django.db.backends import DatabaseProxy
from django.db.models import get_apps, get_models, signals

from mule.contextmanager import BaseTestContextManager
from mule.contrib.django.loader import get_test_module
from mule.utils import import_string
from mule.utils.locking import get_setting_lock, release_setting_lock

class EnvContextManager(BaseTestContextManager):
    def __enter__(self):
        self.suite.setup_test_environment()
    
    def __exit__(self, type, value, traceback):
        self.suite.teardown_test_environment()

class DatabaseContextManager(BaseTestContextManager):
    def __enter__(self):
        suite = self.suite

        self.db_num = get_setting_lock('db', self.build_id)

        db_prefix = '%s_%s_%s_' % (suite.db_prefix, self.build_id, self.db_num)

        for k, v in settings.DATABASES.iteritems():
            # If TEST_NAME wasnt set, or we've set a non-default prefix
            if not v.get('TEST_NAME') or self.auto_bootstrap:
                settings.DATABASES[k]['TEST_NAME'] = db_prefix + settings.DATABASES[k]['NAME']

        suite.db_prefix = db_prefix
        
        # We only need to setup databases if we need to bootstrap
        if suite.auto_bootstrap:
            bootstrap = False
            for alias in connections:
                connection = connections[alias]

                if connection.settings_dict['TEST_MIRROR']:
                    continue

                qn = connection.ops.quote_name
                test_database_name = connection.settings_dict['TEST_NAME']
                cursor = connection.cursor()
                suffix = connection.creation.sql_table_creation_suffix()
                connection.creation.set_autocommit()

                # HACK: this isnt an accurate check
                try:
                    cursor.execute("CREATE DATABASE %s %s" % (qn(test_database_name), suffix))
                except Exception, e:
                    pass
                else:
                    cursor.execute("DROP DATABASE %s" % (qn(test_database_name),))
                    bootstrap = True
                    break
                finally:
                    cursor.close()

                connection.close()
        else:
            bootstrap = True

        # Ensure we import all tests that could possibly be executed so that tables get created
        # and all signals get registered
        for app in get_apps():
            get_test_module(app)

            # Import the 'management' module within each installed app, to register
            # dispatcher events.
            try:
                import_string('%s.management' % app.__name__.rsplit('.', 1)[0])
            except (ImportError, AttributeError):
                pass

        # HACK: We need to kill post_syncdb receivers to stop them from sending when the databases
        #       arent fully ready.
        post_syncdb_receivers = signals.post_syncdb.receivers
        signals.post_syncdb.receivers = []

        if not bootstrap:
            old_names = []
            mirrors = []
            for alias in connections:
                connection = connections[alias]

                if connection.settings_dict['TEST_MIRROR']:
                    mirrors.append((alias, connection))
                    mirror_alias = connection.settings_dict['TEST_MIRROR']
                    connections._connections[alias] = DatabaseProxy(connections[mirror_alias], alias)
                else:
                    old_names.append((connection, connection.settings_dict['NAME']))

                    # Ensure NAME is now set to TEST_NAME
                    connection.settings_dict['NAME'] = settings.DATABASES[alias]['TEST_NAME']

                    can_rollback = connection.creation._rollback_works()
                    # Ensure we setup ``SUPPORTS_TRANSACTIONS``
                    connection.settings_dict['SUPPORTS_TRANSACTIONS'] = can_rollback

                    # Get a cursor (even though we don't need one yet). This has
                    # the side effect of initializing the test database.
                    cursor = connection.cursor()

                    # Ensure our database is clean
                    call_command('flush', verbosity=0, interactive=False, database=alias)

                # XXX: do we need to flush the cache db?

                # if settings.CACHE_BACKEND.startswith('db://'):
                #     from django.core.cache import parse_backend_uri
                #     _, cache_name, _ = parse_backend_uri(settings.CACHE_BACKEND)
                #     call_command('createcachetable', cache_name)
        else:
            old_names, mirrors = suite.setup_databases()

        signals.post_syncdb.receivers = post_syncdb_receivers

        # XXX: we could truncate all tables in the teardown phase and
        #      run the syncdb steps on each iteration (to ensure compatibility w/ transactions)
        for app in get_apps():
            app_models = list(get_models(app, include_auto_created=True))
            for alias in connections:
                connection = connections[alias]
                
                # Get a cursor (even though we don't need one yet). This has
                # the side effect of initializing the test database.
                cursor = connection.cursor()
                
                all_models = [m for m in app_models if router.allow_syncdb(alias, m)]
                if not all_models:
                    continue
                signals.post_syncdb.send(app=app, created_models=all_models, verbosity=suite.verbosity,
                                         db=alias, sender=app, interactive=False)

        self.old_config = old_names, mirrors

    def __exit__(self, type, value, traceback):
        suite = self.suite
        
        # If we were bootstrapping we dont tear down databases
        if suite.auto_bootstrap:
            return

        suite.teardown_databases(self.old_config)
        
        release_setting_lock('db', self.build_id, self.db_num)
########NEW FILE########
__FILENAME__ = loader
from __future__ import absolute_import

from django.test.simple import TEST_MODULE
from imp import find_module
from mule.utils import import_string
from mule.suite import defaultTestLoader

import os, os.path
import types
import unittest

def get_test_module(module):
    try:
        test_module = __import__('%s.%s' % (module.__name__.rsplit('.', 1)[0], TEST_MODULE), {}, {}, TEST_MODULE)
    except ImportError, e:
        # Couldn't import tests.py. Was it due to a missing file, or
        # due to an import error in a tests.py that actually exists?
        try:
            mod = find_module(TEST_MODULE, [os.path.dirname(module.__file__)])
        except ImportError:
            # 'tests' module doesn't exist. Move on.
            test_module = None
        else:
            # The module exists, so there must be an import error in the
            # test module itself. We don't need the module; so if the
            # module was a single file module (i.e., tests.py), close the file
            # handle returned by find_module. Otherwise, the test module
            # is a directory, and there is nothing to close.
            if mod[0]:
                mod[0].close()
            raise
    return test_module

def get_test_by_name(label, loader=defaultTestLoader):
    """Construct a test case with the specified label. Label should be of the
    form model.TestClass or model.TestClass.test_method. Returns an
    instantiated test or test suite corresponding to the label provided.
    """
    # TODO: Refactor this as the code sucks

    try:
        imp = import_string(label)
    except AttributeError:
        # XXX: Handle base_module.TestCase shortcut (assumption)
        module_name, class_name = label.rsplit('.', 1)
        imp = import_string(module_name)
        imp = import_string('%s.%s' % (get_test_module(imp).__name__, class_name))
    
    if isinstance(imp, types.ModuleType):
        return loader.loadTestsFromModule(imp)
    elif issubclass(imp, unittest.TestCase):
        return loader.loadTestsFromTestCase(imp)
    elif issubclass(imp.__class__, unittest.TestCase):
        return imp.__class__(imp.__name__)

    # If no tests were found, then we were given a bad test label.
    raise ValueError("Test label '%s' does not refer to a test" % label)
########NEW FILE########
__FILENAME__ = mule
from __future__ import absolute_import

from django.conf import settings
from mule.contrib.django.suite import DjangoTestSuiteRunner
from mule.utils.conf import configure
from optparse import make_option

if 'south' in settings.INSTALLED_APPS:
    from south.management.commands.test import Command as TestCommand
    from south.management.commands import patch_for_test_db_setup
else:
    from django.core.management.commands.test import Command as TestCommand

import sys

class Command(TestCommand):
    option_list = TestCommand.option_list + (
        make_option('--auto-bootstrap', dest='auto_bootstrap', action='store_true',
                    help='Bootstrap a new database automatically.'),
        make_option('--id', dest='build_id', help='Identifies this build within a distributed model.',
                    default='default'),
        make_option('--db-prefix', type='string', dest='db_prefix', default='test',
                    help='Prefix to use for test databases. Default is ``test``.'),
        make_option('--distributed', dest='distributed', action='store_true',
                    help='Fire test jobs off to Celery queue and collect results.'),
        make_option('--multiprocess', dest='multiprocess', action='store_true',
                    help='Spawns multiple processes (controlled within threads) to test concurrently.'),
        make_option('--max-workers', dest='max_workers', type='int', metavar="NUM",
                    help='Number of workers to consume. With multi-process this is the number of processes to spawn. With distributed this is the number of Celeryd servers to consume.'),
        make_option('--worker', dest='worker', action='store_true',
                    help='Identifies this runner as a worker of a distributed test runner.'),
        make_option('--xunit', dest='xunit', action='store_true',
                    help='Outputs results in XUnit format.'),
        make_option('--xunit-output', dest='xunit_output', default="./xunit/", metavar="PATH",
                    help='Specifies the output directory for XUnit results.'),
        make_option('--include', dest='include', default='', metavar="CLASSNAMES",
                    help='Specifies inclusion cases (TestCaseClassName) for the job detection.'),
        make_option('--exclude', dest='exclude', default='', metavar="CLASSNAMES",
                    help='Specifies exclusion cases (TestCaseClassName) for the job detection.'),
        make_option('--workspace', dest='workspace', metavar="WORKSPACE",
                    help='Specifies the workspace for this build.'),
        make_option('--runner', dest='runner', metavar="RUNNER",
                    help='Specify the test suite runner (use $TEST for path.to.TestCase substitution).'),
    )
    
    def handle(self, *test_labels, **options):
        # HACK: ensure Django configuratio is read in
        configure(**getattr(settings, 'MULE_CONFIG', {}))
        
        settings.TEST = True
        settings.DEBUG = False

        if 'south' in settings.INSTALLED_APPS:
            patch_for_test_db_setup()

        test_runner = DjangoTestSuiteRunner(**options)
        result = test_runner.run_tests(test_labels)

        if result:
            sys.exit(bool(result))
########NEW FILE########
__FILENAME__ = models
from __future__ import absolute_import
########NEW FILE########
__FILENAME__ = signals
from __future__ import absolute_import

from django.dispatch.dispatcher import Signal

# Sent after our test suite is fully initialized
post_test_setup = Signal()

########NEW FILE########
__FILENAME__ = suite
from __future__ import absolute_import

from django.db.models import get_app, get_apps
from django.test.simple import DjangoTestSuiteRunner, build_suite
from django.test._doctest import DocTestCase
from mule import conf
from mule.contextmanager import register_context_manager
from mule.contrib.django.contextmanager import DatabaseContextManager, EnvContextManager
from mule.contrib.django.signals import post_test_setup
from mule.contrib.django.loader import get_test_by_name
from mule.suite import MuleTestLoader
from mule.loader import reorder_suite

import unittest
import unittest2

DEFAULT_RUNNER = 'python manage.py mule --auto-bootstrap --worker --id=$BUILD_ID $TEST'

def mule_suite_runner(parent):
    class new(MuleTestLoader, parent):
        def __init__(self, auto_bootstrap=False, db_prefix='test', runner=DEFAULT_RUNNER,
                     *args, **kwargs):
            MuleTestLoader.__init__(self, *args, **kwargs)
            parent.__init__(self,
                verbosity=int(kwargs['verbosity']),
                failfast=kwargs['failfast'],
                interactive=kwargs['interactive'],
            )
            self.auto_bootstrap = auto_bootstrap

            if self.auto_bootstrap:
                self.interactive = False

            self.db_prefix = db_prefix

            if not runner and self.workspace:
                runner = conf.WORKSPACES[self.workspace].get('runner') or DEFAULT_RUNNER

            self.base_cmd = runner or DEFAULT_RUNNER

            if self.failfast:
                self.base_cmd += ' --failfast'
            
        def run_suite(self, suite, **kwargs):
            run_callback = lambda x: post_test_setup.send(sender=type(x), runner=x)

            return MuleTestLoader.run_suite(self, suite, run_callback=run_callback, **kwargs)

        def build_suite(self, test_labels, extra_tests=None, **kwargs):
            # XXX: We shouldn't need to hook this if Mule can handle the shortname.TestCase format
            suite = unittest2.TestSuite()

            if test_labels:
                for label in test_labels:
                    if '.' in label:
                        suite.addTest(get_test_by_name(label, self.loader))
                    else:
                        app = get_app(label)
                        suite.addTest(build_suite(app))
            else:
                for app in get_apps():
                    suite.addTest(build_suite(app))

            if extra_tests:
                for test in extra_tests:
                    suite.addTest(test)
            
            new_suite = unittest2.TestSuite()
            
            for test in reorder_suite(suite, (unittest.TestCase,)):
                # XXX: Doctests (the way we do it currently) do not work
                if isinstance(test, DocTestCase):
                    continue
                if self.include_testcases and not any(isinstance(test, c) for c in self.include_testcases):
                    continue
                if self.exclude_testcases and any(isinstance(test, c) for c in self.exclude_testcases):
                    continue
                new_suite.addTest(test)

            return reorder_suite(new_suite, (unittest.TestCase,))

        def run_tests(self, *args, **kwargs):
            register_context_manager(EnvContextManager)
            
            # Ensure our db setup/teardown manager is registered
            if not (self.distributed or self.multiprocess):
                register_context_manager(DatabaseContextManager)
            
            return MuleTestLoader.run_tests(self, *args, **kwargs)
    new.__name__ = parent.__name__
    return new

DjangoTestSuiteRunner = mule_suite_runner(DjangoTestSuiteRunner)
########NEW FILE########
__FILENAME__ = tasks
from __future__ import absolute_import

from django.conf import settings
from mule.tasks import *
from mule.utils.conf import configure

# HACK: ensure Django configuratio is read in
configure(**getattr(settings, 'MULE_CONFIG', {}))

########NEW FILE########
__FILENAME__ = loader
import unittest

# Source: Django [http://djangoproject.com]
def partition_suite(suite, classes, bins):
    """
    Partitions a test suite by test type.

    classes is a sequence of types
    bins is a sequence of TestSuites, one more than classes

    Tests of type classes[i] are added to bins[i],
    tests with no match found in classes are place in bins[-1]
    """
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            partition_suite(test, classes, bins)
        else:
            for i in range(len(classes)):
                if isinstance(test, classes[i]):
                    bins[i].addTest(test)
                    break
            else:
                bins[-1].addTest(test)

# Source: Django [http://djangoproject.com]
def reorder_suite(suite, classes):
    """
    Reorders a test suite by test type.

    classes is a sequence of types

    All tests of type clases[0] are placed first, then tests of type classes[1], etc.
    Tests with no match in classes are placed last.
    """
    class_count = len(classes)
    bins = [unittest.TestSuite() for i in range(class_count+1)]
    partition_suite(suite, classes, bins)
    for i in range(class_count):
        bins[0].addTests(bins[i+1])
    return bins[0]
########NEW FILE########
__FILENAME__ = text
# -*- coding: utf-8 -*-

from __future__ import absolute_import

import sys
import time
import traceback

from cStringIO import StringIO
from unittest import TestResult, _TextTestResult, TextTestRunner
from mule.utils.streamer import Streamer

class _TestInfo(object):
    """This class is used to keep useful information about the execution of a
    test method.
    """
    
    # Possible test outcomes
    (SUCCESS, FAILURE, ERROR, SKIPPED) = range(4)
    
    def __init__(self, test_result, test_method, outcome=SUCCESS, err=None):
        "Create a new instance of _TestInfo."
        self.test_result = test_result
        self.test_method = test_method
        self.outcome = outcome
        self.err = err
        self.stdout = StringIO()
        self.stderr = StringIO()
    
    def get_elapsed_time(self):
        """Return the time that shows how long the test method took to
        execute.
        """
        if getattr(self.test_result, 'stop_time', None):
            return self.test_result.stop_time - self.test_result.start_time
        return 0
    
    def get_description(self):
        "Return a text representation of the test method."
        if hasattr(self.test_method, '_dt_test'):
            print self.test_method._dt_test
            print dir(self.test_method)
        return self.test_result.getDescription(self.test_method)
    
    def get_error_info(self):
        """Return a text representation of an exception thrown by a test
        method.
        """
        if not self.err:
            return ''
        return self.test_result._exc_info_to_string(self.err, \
            self.test_method)


class _TextTestResult(_TextTestResult):
    def __init__(self, stream=sys.stderr, descriptions=1, verbosity=1, \
        elapsed_times=True, pdb=False):
        super(_TextTestResult, self).__init__(stream, descriptions, verbosity)
        self.successes = []
        self.skipped = []
        self.callback = None
        self.elapsed_times = elapsed_times
    
    def _prepare_callback(self, test_info, target_list, verbose_str,
        short_str):
        """Append a _TestInfo to the given target list and sets a callback
        method to be called by stopTest method.
        """
        target_list.append(test_info)

        def callback():
            """This callback prints the test method outcome to the stream,
            as well as the elapsed time.
            """
            # Ignore the elapsed times for a more reliable unit testing
            if not self.elapsed_times:
                self.start_time = self.stop_time = 0
            
            if self.showAll:
                self.stream.writeln('%s (%.3fs)' % \
                    (verbose_str, test_info.get_elapsed_time()))
            elif self.dots:
                self.stream.write(short_str)
        self.callback = callback
    
    def startTest(self, test):
        "Called before execute each test method."
        self._patch_standard_output(test)
        self.start_time = time.time()
        TestResult.startTest(self, test)

        if self.showAll:
            self.stream.write('  ' + self.getDescription(test))
            self.stream.write(" ... ")
    
    def stopTest(self, test):
        "Called after execute each test method."
        super(_TextTestResult, self).stopTest(test)
        self.stop_time = time.time()
        
        if self.callback and callable(self.callback):
            self.callback()
            self.callback = None
        self._restore_standard_output(test)

    def addSuccess(self, test):
        "Called when a test executes successfully."
        self._prepare_callback(_TestInfo(self, test), \
            self.successes, 'OK', '.')
    
    def addFailure(self, test, err):
        "Called when a test method fails."
        self._prepare_callback(_TestInfo(self, test, _TestInfo.FAILURE, err), \
            self.failures, 'FAIL', 'F')
    
    def addError(self, test, err):
        "Called when a test method raises an error."
        tracebacks = traceback.extract_tb(err[2])
        if tracebacks[-1][-1] and tracebacks[-1][-1].startswith('raise SkippedTest'):
            self._prepare_callback(_TestInfo(self, test, _TestInfo.SKIPPED, err), \
                self.skipped, 'SKIP', 'S')
        else:
            self._prepare_callback(_TestInfo(self, test, _TestInfo.ERROR, err), \
                self.errors, 'ERROR', 'E')

    def printErrorList(self, flavour, errors):
        "Write some information about the FAIL or ERROR to the stream."
        for test_info in errors:
            self.stream.writeln(self.separator1)
            self.stream.writeln('%s [%.3fs]: %s' % \
                (flavour, test_info.get_elapsed_time(), \
                test_info.get_description()))
            self.stream.writeln(self.separator2)
            self.stream.writeln('%s' % test_info.get_error_info())

    def _patch_standard_output(self, test):
        """Replace the stdout and stderr streams with string-based streams
        in order to capture the tests' output.
        """
        test.stdout = Streamer(sys.stdout)
        test.stderr = Streamer(sys.stderr)
        
        (self.old_stdout, self.old_stderr) = (sys.stdout, sys.stderr)
        (sys.stdout, sys.stderr) = (test.stdout, test.stderr)
    
    def _restore_standard_output(self, test):
        "Restore the stdout and stderr streams."
        
        (sys.stdout, sys.stderr) = (self.old_stdout, self.old_stderr)

class TextTestRunner(TextTestRunner):
    def __init__(self, elapsed_times=True, pdb=False, **kwargs):
        super(TextTestRunner, self).__init__(**kwargs)
        self.elapsed_times = elapsed_times
    
    def _makeResult(self):
        """Create the TestResult object which will be used to store
        information about the executed tests.
        """
        return _TextTestResult(self.stream, self.descriptions, \
            self.verbosity, self.elapsed_times)
    
    def run(self, test):
        "Run the given test case or test suite."
        
        # Prepare the test execution
        result = self._makeResult()
        
        # Print a nice header
        if self.verbosity > 0:
            self.stream.writeln()
            self.stream.writeln('Running tests...')
            self.stream.writeln(result.separator2)
        
        # Execute tests
        start_time = time.time()
        test(result)
        stop_time = time.time()
        time_taken = stop_time - start_time
        
        # Print results
        if self.verbosity > 0:
            result.printErrors()
            self.stream.writeln(result.separator2)
            run = result.testsRun
            self.stream.writeln("Ran %d test%s in %.3fs" %
                (run, run != 1 and "s" or "", time_taken))
            self.stream.writeln()
        
            # Error traces
            if not result.wasSuccessful():
                self.stream.write("FAILED (")
                failed, errored, skipped = (len(result.failures), len(result.errors), len(result.skipped))
                if failed:
                    self.stream.write("failures=%d" % failed)
                if errored:
                    if failed:
                        self.stream.write(", ")
                    self.stream.write("errors=%d" % errored)
                if skipped:
                    if failed or errored:
                        self.stream.write(", ")
                    self.stream.write("skipped=%d" % skipped)
                self.stream.writeln(")")
            else:
                self.stream.writeln("OK")
        
            self.stream.writeln()
        
        return result

########NEW FILE########
__FILENAME__ = xml
# -*- coding: utf-8 -*-

from __future__ import absolute_import

"""unittest-xml-reporting is a PyUnit-based TestRunner that can export test
results to XML files that can be consumed by a wide range of tools, such as
build systems, IDEs and Continuous Integration servers.

This module provides the XMLTestRunner class, which is heavily based on the
default TextTestRunner. This makes the XMLTestRunner very simple to use.

The script below, adapted from the unittest documentation, shows how to use
XMLTestRunner in a very simple way. In fact, the only difference between this
script and the original one is the last line:

import random
import unittest
import xmlrunner

class TestSequenceFunctions(unittest.TestCase):
    def setUp(self):
        self.seq = range(10)

    def test_shuffle(self):
        # make sure the shuffled sequence does not lose any elements
        random.shuffle(self.seq)
        self.seq.sort()
        self.assertEqual(self.seq, range(10))

    def test_choice(self):
        element = random.choice(self.seq)
        self.assert_(element in self.seq)

    def test_sample(self):
        self.assertRaises(ValueError, random.sample, self.seq, 20)
        for element in random.sample(self.seq, 5):
            self.assert_(element in self.seq)

if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
"""

import os

from mule.runners.text import _TextTestResult, TextTestRunner, _TestInfo

class _XMLTestResult(_TextTestResult):
    "A test result class that can express test results in a XML report."

    def _get_info_by_testcase(self):
        """This method organizes test results by TestCase module. This
        information is used during the report generation, where a XML report
        will be generated for each TestCase.
        """
        tests_by_testcase = {}
        
        for tests in (self.successes, self.failures, self.errors, self.skipped):
            for test_info in tests:
                testcase = type(test_info.test_method)
                
                # Ignore module name if it is '__main__'
                module = testcase.__module__ + '.'
                if module == '__main__.':
                    module = ''
                testcase_name = module + testcase.__name__
                
                if not tests_by_testcase.has_key(testcase_name):
                    tests_by_testcase[testcase_name] = []
                tests_by_testcase[testcase_name].append(test_info)
        
        return tests_by_testcase
    
    @classmethod
    def _report_testsuite(cls, suite_name, tests, xml_document):
        "Appends the testsuite section to the XML document."
        testsuite = xml_document.createElement('testsuite')
        xml_document.appendChild(testsuite)
        
        testsuite.setAttribute('name', suite_name)
        testsuite.setAttribute('tests', str(len(tests)))
        
        testsuite.setAttribute('time', '%.3f' % \
            sum(map(lambda e: e.get_elapsed_time(), tests)))
        
        failures = filter(lambda e: e.outcome==_TestInfo.FAILURE, tests)
        testsuite.setAttribute('failures', str(len(failures)))
        
        errors = filter(lambda e: e.outcome==_TestInfo.ERROR, tests)
        testsuite.setAttribute('errors', str(len(errors)))

        skipped = filter(lambda e: e.outcome==_TestInfo.SKIPPED, tests)
        testsuite.setAttribute('skips', str(len(skipped)))

        
        return testsuite
    
    @classmethod
    def _report_testcase(cls, suite_name, test_result, xml_testsuite, xml_document):
        "Appends a testcase section to the XML document."
        testcase = xml_document.createElement('testcase')
        xml_testsuite.appendChild(testcase)
        
        testcase.setAttribute('classname', suite_name)
        testcase.setAttribute('name', test_result.test_method._testMethodName)
        testcase.setAttribute('time', '%.3f' % test_result.get_elapsed_time())
        
        if (test_result.outcome != _TestInfo.SUCCESS):
            elem_name = ('failure', 'error', 'skip')[test_result.outcome-1]
            failure = xml_document.createElement(elem_name)
            testcase.appendChild(failure)
            
            failure.setAttribute('type', test_result.err[0].__name__)
            failure.setAttribute('message', str(test_result.err[1]))
            
            error_info = test_result.get_error_info()
            failureText = xml_document.createCDATASection(error_info)
            failure.appendChild(failureText)
    
    @classmethod
    def _report_output(cls, suite, tests, test_runner, xml_testsuite, xml_document):
        "Appends the system-out and system-err sections to the XML document."
        systemout = xml_document.createElement('system-out')
        xml_testsuite.appendChild(systemout)
        
        stdout = '\n'.join(filter(None, (t.test_method.stdout.getvalue() for t in tests))).strip()
        systemout_text = xml_document.createCDATASection(stdout)
        systemout.appendChild(systemout_text)
        
        systemerr = xml_document.createElement('system-err')
        xml_testsuite.appendChild(systemerr)
        
        stderr = '\n'.join(filter(None, (t.test_method.stderr.getvalue() for t in tests))).strip()
        systemerr_text = xml_document.createCDATASection(stderr)
        systemerr.appendChild(systemerr_text)
    
    def generate_reports(self, test_runner):
        "Generates the XML reports to a given XMLTestRunner object."
        from xml.dom.minidom import Document
        all_results = self._get_info_by_testcase()
        
        if type(test_runner.output) == str and not \
            os.path.exists(test_runner.output):
            os.makedirs(test_runner.output)
        
        for suite, tests in all_results.items():
            doc = Document()
            
            # Build the XML file
            testsuite = _XMLTestResult._report_testsuite(suite, tests, doc)
            for test in tests:
                _XMLTestResult._report_testcase(suite, test, testsuite, doc)
            _XMLTestResult._report_output(suite, tests, test_runner, testsuite, doc)
            xml_content = doc.toprettyxml(indent='\t')
            
            if type(test_runner.output) is str:
                report_file = open(os.path.join(test_runner.output, '%s.xml' % (suite,)), 'w')
                try:
                    report_file.write(xml_content)
                finally:
                    report_file.close()
            else:
                # Assume that test_runner.output is a stream
                test_runner.output.write(xml_content)

class XMLTestRunner(TextTestRunner):
    """A test runner class that outputs the results in JUnit like XML files."""
    def __init__(self, output='xunit', **kwargs):
        super(XMLTestRunner, self).__init__(**kwargs)
        self.output = output

    def _makeResult(self):
        """Create the TestResult object which will be used to store
        information about the executed tests.
        """
        return _XMLTestResult(self.stream, self.descriptions, \
            self.verbosity, self.elapsed_times)

    def run(self, test):
        "Run the given test case or test suite."
        result = super(XMLTestRunner, self).run(test)

        # self.stream.writeln('Generating XML reports...')
        result.generate_reports(self)
        return result
########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python

from celery import current_app
from os.path import dirname, abspath
from unittest2.loader import defaultTestLoader

class TestConf:
    CELERY_RESULT_BACKEND = 'redis'
    CELERY_IMPORTS = ('mule.tasks', )

    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379
    REDIS_DB = 0

    BROKER_BACKEND = 'redis'

    BROKER_HOST = 'localhost'  # Maps to redis host.
    BROKER_PORT = 6379         # Maps to redis port.
    BROKER_VHOST = '0'         # Maps to database number.

def runtests():
    parent = dirname(abspath(__file__))
    #sys.path.insert(0, parent)
    current_app.config_from_object(TestConf)
    return defaultTestLoader.discover(parent)

if __name__ == '__main__':
    runtests()
########NEW FILE########
__FILENAME__ = runner
#!/usr/bin/env python
from optparse import OptionParser
from mule import VERSION
from mule.base import Mule, MultiProcessMule

import sys

def main():
    args = sys.argv
    if len(args) < 2:
        print "usage: mule [command] [options]"
        print
        print "Available subcommands:"
        print "  test"
        sys.exit(1)

    parser = OptionParser(version="%%prog %s" % VERSION)
    if args[1] == 'test':
        parser.add_option('--basedir', default='.', metavar='PATH',
                          help='Specify the directory to discover tests from.')
        parser.add_option('--runner', default='unit2 $TEST', metavar='RUNNER',
                          help='Specify the test suite runner (use $TEST for path.to.TestCase substitution).')
        parser.add_option('--max-workers', dest='max_workers', type='int', metavar="NUM",
                          help='Number of workers to consume. With multi-process this is the number of processes to spawn. With distributed this is the number of Celeryd servers to consume.')
        parser.add_option('--multiprocess', dest='multiprocess', action='store_true',
                          help='Use multi-process on the same machine instead of the Celery distributed system.')
        parser.add_option('--workspace', dest='workspace', metavar="WORKSPACE",
                          help='Specifies the workspace for this build.')

    (options, args) = parser.parse_args()
    if args[0] == "test":
        if options.multiprocess:
            cls = MultiProcessMule
        else:
            cls = Mule
        mule = cls(max_workers=options.max_workers, workspace=options.workspace)
        jobs = mule.discover_tests(options.basedir)
        print '\n'.join(mule.process(jobs, options.runner))

    sys.exit(0)

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = suite
# TODO: TransactionTestCase should be ordered last, and they need to completely tear down
#       all data in all tables and re-run syncdb (initial fixtures) each time.
#       This same (bad) behavior needs to happen on every TestCase if not connections_support_transactions()

from __future__ import absolute_import

from cStringIO import StringIO
from mule.contextmanager import get_context_managers
from mule.base import Mule, MultiProcessMule, FailFastInterrupt
from mule.loader import reorder_suite
from mule.runners import make_test_runner
from mule.runners.xml import XMLTestRunner
from mule.runners.text import TextTestRunner, _TextTestResult
from mule.utils import import_string
from xml.dom.minidom import parseString

import logging
import os, os.path
import re
import sys
import time
import uuid
import unittest
import unittest2

defaultTestLoader = unittest2.defaultTestLoader

class MuleTestLoader(object):
    def __init__(self, build_id='default', distributed=False, worker=False,
                 multiprocess=False, xunit=False, xunit_output='./xunit/',
                 include='', exclude='', max_workers=None, start_dir=None,
                 loader=defaultTestLoader, base_cmd='unit2 $TEST', 
                 workspace=None, log_level=logging.DEBUG, *args, **kwargs):

        assert not (distributed and worker and multiprocess), "You cannot combine --distributed, --worker, and --multiprocess"
        
        self.build_id = build_id
        
        self.distributed = distributed
        self.worker = worker
        self.multiprocess = multiprocess

        self.xunit = xunit
        self.xunit_output = os.path.realpath(xunit_output)
        if include:
            self.include_testcases = [import_string(i) for i in include.split(',')]
        else:
            self.include_testcases = []
        if exclude:
            self.exclude_testcases = [import_string(i) for i in exclude.split(',')]
        else:
            self.exclude_testcases = []
        self.max_workers = max_workers
        self.start_dir = start_dir
        self.loader = loader
        self.logger = logging.getLogger('mule')
        self.logger.setLevel(log_level)
        
        self.base_cmd = base_cmd
        self.workspace = workspace
    
    def run_suite(self, suite, output=None, run_callback=None):
        kwargs = {
            'verbosity': self.verbosity,
            'failfast': self.failfast,
        }
        if self.worker or self.xunit:
            cls = XMLTestRunner
            kwargs['output'] = output
        else:
            cls = TextTestRunner

        if self.worker:
            # We dont output anything
            kwargs['verbosity'] = 0
        
        cls = make_test_runner(cls)
    
        result = cls(run_callback=run_callback, **kwargs).run(suite)

        return result

    def build_suite(self, test_labels, extra_tests=None, **kwargs):
        suite = unittest2.TestSuite()

        if test_labels:
            for label in test_labels:
                self.loader.loadTestsFromNames(test_labels)
        else:
            self.loader.discover(self.start_dir)

        if extra_tests:
            for test in extra_tests:
                suite.addTest(test)
        
        new_suite = unittest2.TestSuite()
        
        for test in reorder_suite(suite, (unittest.TestCase,)):
            # XXX: Doctests (the way we do it currently) do not work
            if self.include_testcases and not any(isinstance(test, c) for c in self.include_testcases):
                continue
            if self.exclude_testcases and any(isinstance(test, c) for c in self.exclude_testcases):
                continue
            new_suite.addTest(test)

        return reorder_suite(new_suite, (unittest2.TestCase,))

    def run_distributed_tests(self, test_labels, extra_tests=None, in_process=False, **kwargs):
        if in_process:
            cls = MultiProcessMule
        else:
            cls = Mule
        build_id = uuid.uuid4().hex
        mule = cls(build_id=build_id, max_workers=self.max_workers, workspace=self.workspace)
        result = mule.process(test_labels, runner=self.base_cmd,
                              callback=self.report_result)
        # result should now be some parseable text
        return result
    
    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        # We need to swap stdout/stderr so that the task only captures what is needed,
        # and everything else goes to our logs
        if self.worker:
            stdout = StringIO()
            sys_stdout = sys.stdout
            sys.stdout = stdout
            output = sys_stdout
        else:
            if self.xunit:
                output = self.xunit_output
            else:
                output = sys.stdout
        
        cms = list()
        for cls in get_context_managers():
            self.logger.info('Entering context for [%r]', cls)
            start = time.time()
            cm = cls(build_id=self.build_id, suite=self)
            cm.__enter__()
            stop = time.time()
            self.logger.info('Context manager opened in %.3fs', stop - start)
            cms.append(cm)

        try:
            suite = self.build_suite(test_labels, extra_tests)

            start = time.time()

            if self.distributed or self.multiprocess:
                # we can only test whole TestCase's currently
                jobs = set(t.__class__ for t in suite._tests)
                result = self.run_distributed_tests(jobs, extra_tests=None, in_process=self.multiprocess, **kwargs)
            else:
                result = self.run_suite(suite, output=output)

            stop = time.time()

            result = self.suite_result(suite, result, stop-start)

        finally:
            if self.worker:
                sys.stdout = sys_stdout
            
            for cm in reversed(cms):
                self.logger.info('Exiting context for [%r]', cls)
                start = time.time()
                cm.__exit__(None, None, None)
                stop = time.time()
                self.logger.info('Context manager closed in %.3fs', stop - start)
                
        
        return result

    def report_result(self, result):
        if result['stdout']:
            match = re.search(r'errors="(\d+)".*failures="(\d+)".*skips="(\d+)".*tests="(\d+)"', result['stdout'])
            if match:
                errors = int(match.group(1))
                failures = int(match.group(2))
                skips = int(match.group(3))
                tests = int(match.group(4))
        else:
            errors = 1
            tests = 1
            failures = 0
            skips = 0
        
        if self.failfast and (errors or failures):
            raise FailFastInterrupt(result)
    
    def suite_result(self, suite, result, total_time, **kwargs):
        if self.distributed or self.multiprocess:
            # Bootstrap our xunit output path
            if self.xunit and not os.path.exists(self.xunit_output):
                os.makedirs(self.xunit_output)
            
            failures, errors = 0, 0
            skips, tests = 0, 0

            had_res = False
            res_type = None
            
            for r in result:
                if isinstance(r, dict):
                    # XXX: stdout (which is our result) is in XML, which sucks life is easier with regexp
                    match = re.search(r'errors="(\d+)".*failures="(\d+)".*skips="(\d+)".*tests="(\d+)"', r['stdout'])
                    if match:
                        errors += int(match.group(1))
                        failures += int(match.group(2))
                        skips += int(match.group(3))
                        tests += int(match.group(4))
                else:
                    # Handles cases when our runners dont return correct output
                    had_res = True
                    res_type = 'error'
                    sys.stdout.write(_TextTestResult.separator1 + '\n')
                    sys.stdout.write('EXCEPTION: unknown exception\n')
                    if r:
                        sys.stdout.write(_TextTestResult.separator1 + '\n')
                        sys.stdout.write(str(r).strip() + '\n')
                    errors += 1
                    tests += 1
                    continue
                    
                if self.xunit:
                    # Since we already get xunit results back, let's just write them to disk
                    if r['stdout']:
                        fp = open(os.path.join(self.xunit_output, r['job'] + '.xml'), 'w')
                        try:
                            fp.write(r['stdout'])
                        finally:
                            fp.close()
                    elif r['stderr']:
                        sys.stderr.write(r['stderr'])
                        # Need to track this for the builds
                        errors += 1
                        tests += 1
                elif r['stdout']:
                    # HACK: Ideally we would let our default text runner represent us here, but that'd require
                    #       reconstructing the original objects which is even more of a hack
                    try:
                        xml = parseString(r['stdout'])
                    except Exception, e:
                        had_res = True
                        res_type = 'error'
                        sys.stdout.write(_TextTestResult.separator1 + '\n')
                        sys.stdout.write('EXCEPTION: %s (%s)\n' % (e, r['job']))
                        if r['stdout']:
                            sys.stdout.write(_TextTestResult.separator1 + '\n')
                            sys.stdout.write(r['stdout'].strip() + '\n')
                        if r['stderr']:
                            sys.stdout.write(_TextTestResult.separator1 + '\n')
                            sys.stdout.write(r['stdout'].strip() + '\n')
                        errors += 1
                        tests += 1
                        continue

                    for xml_test in xml.getElementsByTagName('testcase'):
                        for xml_test_res in xml_test.childNodes:
                            if xml_test_res.nodeName not in ('failure', 'skip', 'error'):
                                continue
                            had_res = True
                            res_type = xml_test.getAttribute('name')
                            desc = '%s (%s)' % (xml_test.getAttribute('name'), xml_test.getAttribute('classname'))
                            sys.stdout.write(_TextTestResult.separator1 + '\n')
                            sys.stdout.write('%s [%.3fs]: %s\n' % \
                                (xml_test_res.nodeName.upper(), float(xml_test.getAttribute('time') or '0.0'), desc))
                            sys.stdout.write('(Job was %s)\n' % r['job'])
                            error_msg = (''.join(c.wholeText for c in xml_test_res.childNodes if c.nodeType == c.CDATA_SECTION_NODE)).strip()
                            if error_msg:
                                sys.stdout.write(_TextTestResult.separator2 + '\n')
                                sys.stdout.write('%s\n' % error_msg)

                    if res_type in ('failure', 'error'):
                        syserr = (''.join(c.wholeText for c in xml.getElementsByTagName('system-err')[0].childNodes if c.nodeType == c.CDATA_SECTION_NODE)).strip()
                        if syserr:
                            sys.stdout.write(_TextTestResult.separator2 + '\n')
                            sys.stdout.write('%s\n' % r['stderr'].strip())
                        # if r['stderr']:
                        #     sys.stdout.write(_TextTestResult.separator2 + '\n')
                        #     sys.stdout.write('%s\n' % r['stderr'].strip())
                elif r['stderr']:
                    had_res = True
                    sys.stdout.write(_TextTestResult.separator1 + '\n')
                    sys.stdout.write('EXCEPTION: %s\n' % r['job'])
                    sys.stdout.write(_TextTestResult.separator1 + '\n')
                    sys.stdout.write(r['stderr'].strip() + '\n')
                    errors += 1
                    tests += 1

            if had_res:
                sys.stdout.write(_TextTestResult.separator2 + '\n')

            run = tests - skips
            sys.stdout.write("\nRan %d test%s in %.3fs\n\n" % (run, run != 1 and "s" or "", total_time))
            
            if errors or failures:
                sys.stdout.write("FAILED (")
                if failures:
                    sys.stdout.write("failures=%d" % failures)
                if errors:
                    if failures:
                        sys.stdout.write(", ")
                    sys.stdout.write("errors=%d" % errors)
                if skips:
                    if failures or errors:
                        sys.stdout.write(", ")
                    sys.stdout.write("skipped=%d" % skips)
                sys.stdout.write(")")
            else:
                sys.stdout.write("OK")
                if skips:
                    sys.stdout.write(" (skipped=%d)" % skips)

            sys.stdout.write('\n\n')
            return failures + errors
        return super(MuleTestLoader, self).suite_result(suite, result, **kwargs)
########NEW FILE########
__FILENAME__ = tasks
from celery.task import task
from celery.worker.control import Panel
from mule import conf

import os
import subprocess
import shlex
import tempfile
import time
import traceback

__all__ = ('mule_setup', 'mule_teardown', 'run_test')

def join_queue(cset, name, **kwargs):
    queue = cset.add_consumer_from_dict(queue=name, **kwargs)
    # XXX: There's currently a bug in Celery 2.2.5 which doesn't declare the queue automatically
    channel = cset.channel
    queue(channel).declare()

    # start consuming from default
    cset.consume()

def execute_bash(name, script, workspace=None, logger=None, **env_kwargs):
    (h, script_path) = tempfile.mkstemp(prefix=name)
    
    if logger:
        logger.info('Executing %s in %s', name, script_path)

    if workspace:
        assert conf.ROOT
        work_path = os.path.join(conf.ROOT, 'workspaces', workspace)
    else:
        work_path = os.getcwd()

    with open(script_path, 'w') as fp:
        fp.write(unicode(script).encode('utf-8'))

    cmd = '/bin/bash %s' % script_path.encode('utf-8')

    # Setup our environment variables
    env = os.environ.copy()
    for k, v in env_kwargs.iteritems():
        env[unicode(k).encode('utf-8')] = unicode(v).encode('utf-8')
    env['WORKSPACE'] = work_path
    
    start = time.time()
    
    try:
        proc = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=env, cwd=work_path)
        (stdout, stderr) = map(lambda x: x.strip(), proc.communicate())
    except KeyboardInterrupt:
        # Ensure we propagate up the exception
        raise
    except Exception, e:
        (stdout, stderr, returncode) =  ('', 'Error running command [%s]: %s' % (cmd, traceback.format_exc()), 1)
    else:
        returncode = proc.returncode
    
    stop = time.time()
    
    if logger:
        logger.info('Script execution completed in %.3fs', stop - start)
    
    return (stdout, stderr, returncode)

@Panel.register
def mule_setup(panel, build_id, workspace=None, script=None):
    """
    This task has two jobs:

    1. Leaves the default Mule queue, and joins a new build-specific queue.

    2. Ensure that we're bootstrapped for this build.

       This includes:
         - Doing a git fetch
         - Setting up a virtualenv
         - Building our DB
    """
    assert not script or workspace, "Cannot pass scripts without a workspace"
    
    queue_name = '%s-%s' % (conf.BUILD_QUEUE_PREFIX, build_id)

    cset = panel.consumer.task_consumer
    
    if conf.DEFAULT_QUEUE not in [q.name for q in cset.queues]:
        return {
            "status": "fail",
            "reason": "worker is already in use"
        }
    
    cset.cancel_by_queue(conf.DEFAULT_QUEUE)
    
    script_result = ('', '', 0)
    
    if script:
        try:
            script_result = execute_bash(
                name='setup.sh',
                script=script,
                workspace=workspace,
                logger=panel.logger,
                BUILD_ID=build_id,
            )
        except:
            # If our teardown fails we need to ensure we rejoin the queue
            join_queue(cset, name=conf.DEFAULT_QUEUE)
            raise
    
    join_queue(cset, name=queue_name, exchange_type='direct')

    panel.logger.info("Started consuming from %s", queue_name)

    return {
        "status": "ok",
        "build_id": build_id,
        "stdout": script_result[0],
        "stderr": script_result[1],
        "retcode": script_result[2],
    }

@Panel.register
def mule_teardown(panel, build_id, workspace=None, script=None):
    """
    This task has two jobs:
    
    1. Run any bootstrap teardown

    2. Leaves the build-specific queue, and joins the default Mule queue.
    """
    assert not script or workspace, "Cannot pass scripts without a workspace"
    
    queue_name = '%s-%s' % (conf.BUILD_QUEUE_PREFIX, build_id)

    cset = panel.consumer.task_consumer
    channel = cset.channel
    # kill all jobs in queue
    channel.queue_purge(queue=queue_name)
    # stop consuming from queue
    cset.cancel_by_queue(queue_name)
    
    script_result = ('', '', 0)
    
    if script:
        try:
            script_result = execute_bash(
                name='teardown.sh',
                script=script,
                workspace=workspace,
                logger=panel.logger,
                BUILD_ID=build_id,
            )
        except:
            # If our teardown fails we need to ensure we rejoin the queue
            join_queue(cset, name=conf.DEFAULT_QUEUE)
            raise
    
    join_queue(cset, name=conf.DEFAULT_QUEUE)

    panel.logger.info("Rejoined default queue")

    return {
        "status": "ok",
        "build_id": build_id,
        "stdout": script_result[0],
        "stderr": script_result[1],
        "retcode": script_result[2],
    }


@task(ignore_result=False)
def run_test(build_id, runner, job, callback=None, workspace=None):
    """
    Spawns a test runner and reports the result.
    """
    start = time.time()

    script_result = execute_bash(
        name='test.sh',
        script=runner,
        workspace=workspace,
        logger=run_test.get_logger(),
        BUILD_ID=build_id,
        TEST=job,
    )

    stop = time.time()

    result = {
        "timeStarted": start,
        "timeFinished": stop,
        "build_id": build_id,
        "job": job,
        "stdout": script_result[0],
        "stderr": script_result[1],
        "retcode": script_result[2],
    }

    if callback:
        callback(result)

    return result
########NEW FILE########
__FILENAME__ = tests
import os.path
from unittest2 import TestCase
from dingus import Dingus
from mule.base import Mule
from mule import conf
from mule.tasks import run_test, mule_setup, mule_teardown

def dingus_calls_to_dict(obj):
    # remap dingus calls into a useable dict
    calls = {}
    for name, args, kwargs, obj in obj:
        if name not in calls:
            calls[name] = []
        calls[name].append((args, kwargs, obj))
    return calls

class TestRunnerTestCase(TestCase):
    def test_discovery(self):
        mule = Mule()
        jobs = list(mule.discover_tests(os.path.dirname(__file__)))
        self.assertGreater(len(jobs), 0)
        self.assertTrue('mule.tests.TestRunnerTestCase' in ['%s.%s' % (j.__module__, j.__name__) for j in jobs])

    # def test_process(self):
    #     # TODO: process() needs broken down so it can be better tested
    #     mule = Mule()
    #     result = mule.process([self.__class__], 'echo $TEST')
    #     self.assertEquals(len(result), 1)
    #     result = result[0]
    #     self.assertTrue('retcode' in result)
    #     self.assertTrue('timeStarted' in result)
    #     self.assertTrue('timeFinished' in result)
    #     self.assertTrue('build_id' in result)
    #     self.assertTrue('stdout' in result)
    #     self.assertTrue('stderr' in result)
    #     self.assertTrue('job' in result)
    #     self.assertEquals(result['job'], 'tests.TestRunnerTestCase')
    #     self.assertEquals(result['stdout'], 'tests.TestRunnerTestCase')
    #     self.assertGreater(result['timeFinished'], result['timeStarted'])

class RunTestTestCase(TestCase):
    def test_subprocess(self):
        result = run_test('build_id', 'echo $TEST', 'job')
        self.assertTrue('retcode' in result)
        self.assertTrue('timeStarted' in result)
        self.assertTrue('timeFinished' in result)
        self.assertTrue('build_id' in result)
        self.assertTrue('stdout' in result)
        self.assertTrue('stderr' in result)
        self.assertTrue('job' in result)
        self.assertEquals(result['job'], 'job')
        self.assertEquals(result['stdout'], 'job')
        self.assertGreater(result['timeFinished'], result['timeStarted'])

    def test_callback(self):
        bar = []
        def foo(result):
            bar.append(result)
        
        result = run_test('build_id', 'echo $TEST', 'job', foo)
        self.assertEquals(len(bar), 1)
        result = bar[0]
        self.assertTrue('retcode' in result)
        self.assertTrue('timeStarted' in result)
        self.assertTrue('timeFinished' in result)
        self.assertTrue('build_id' in result)
        self.assertTrue('stdout' in result)
        self.assertTrue('stderr' in result)
        self.assertTrue('job' in result)
        self.assertEquals(result['job'], 'job')
        self.assertEquals(result['stdout'], 'job')
        self.assertGreater(result['timeFinished'], result['timeStarted'])

class PanelTestCase(TestCase):
    def test_provision(self):
        panel = Dingus('Panel')
        result = mule_setup(panel, 1)

        self.assertEquals(result, {
            "status": "fail",
            "reason": "worker is already in use"
        })

        # Ensure we're now in the default queue
        queue = Dingus('Queue')
        queue.name = conf.DEFAULT_QUEUE
        panel.consumer.task_consumer.queues = [queue]
        result = mule_setup(panel, 1)

        self.assertTrue('build_id' in result)
        self.assertEquals(result['build_id'], 1)

        self.assertTrue('status' in result)
        self.assertEquals(result['status'], 'ok')
        
        calls = dingus_calls_to_dict(panel.consumer.task_consumer.calls)
                
        self.assertTrue('cancel_by_queue' in calls)
        self.assertTrue(len(calls['cancel_by_queue']), 1)
        call = calls['cancel_by_queue'][0]
        self.assertTrue(len(call[0]), 1)
        self.assertTrue(call[0][0], conf.DEFAULT_QUEUE)

        self.assertTrue('consume' in calls)
        self.assertTrue(len(calls['consume']), 1)
        
        self.assertTrue('add_consumer_from_dict' in calls)
        self.assertTrue(len(calls['add_consumer_from_dict']), 1)
        call = calls['add_consumer_from_dict'][0]
        self.assertTrue('queue' in call[1])
        self.assertEquals(call[1]['queue'], '%s-1' % conf.BUILD_QUEUE_PREFIX)

    def test_teardown(self):
        panel = Dingus('Panel')
        result = mule_teardown(panel, 1)

        self.assertTrue('build_id' in result)
        self.assertEquals(result['build_id'], 1)

        self.assertTrue('status' in result)
        self.assertEquals(result['status'], 'ok')
        
        calls = dingus_calls_to_dict(panel.consumer.task_consumer.calls)
                
        self.assertTrue('cancel_by_queue' in calls)
        self.assertTrue(len(calls['cancel_by_queue']), 1)
        call = calls['cancel_by_queue'][0]
        self.assertTrue(len(call[0]), 1)
        self.assertTrue(call[0][0], '%s-1' % conf.BUILD_QUEUE_PREFIX)

        self.assertTrue('consume' in calls)
        self.assertTrue(len(calls['consume']), 1)
        
        self.assertTrue('add_consumer_from_dict' in calls)
        self.assertTrue(len(calls['add_consumer_from_dict']), 1)
        call = calls['add_consumer_from_dict'][0]
        self.assertTrue('queue' in call[1])
        self.assertEquals(call[1]['queue'], conf.DEFAULT_QUEUE)
########NEW FILE########
__FILENAME__ = conf
from mule import conf

import warnings

def configure(**kwargs):
    for k, v in kwargs.iteritems():
        if not hasattr(conf, k):
            warnings.warn('Setting %k which is not defined by Mule' % k)
        setattr(conf, k, v)
########NEW FILE########
__FILENAME__ = locking
import fcntl
import os

LOCK_DIR = '/var/tmp'

locks = {}

def acquire_lock(lock):
    fd = open(lock, 'w')
    fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB) # NB = non-blocking (raise IOError instead)
    fd.write(str(os.getpid()))
    locks[lock] = fd

def release_lock(lock):
    fd = locks.pop(lock)
    if not fd:
        return
    fcntl.lockf(fd, fcntl.LOCK_UN)
    fd.close()
    os.remove(lock)
    fd = None
    
def get_setting_lock(setting, build_id, max_locks=None):
    # XXX: Pretty sure this needs try/except to stop race condition
    num = 0
    while not max_locks or num < max_locks:
        lock_file = lock_for_setting(setting, build_id, num)
        try:
            acquire_lock(lock_file)
        except IOError:
            # lock unavailable
            num += 1
        else:
            break
    if num == max_locks:
        raise OSError
    return num

def release_setting_lock(setting, build_id, num):
    lock_file = lock_for_setting(setting, build_id, num)
    release_lock(lock_file)

def lock_for_setting(setting, build_id, num=0):
    return os.path.join(LOCK_DIR, 'mule:%s_%s_%s' % (setting, build_id, num))
########NEW FILE########
__FILENAME__ = multithreading
from collections import defaultdict
from Queue import Queue
from threading import Thread

import traceback

_results = defaultdict(list)

class Worker(Thread):
    """Thread executing tasks from a given tasks queue"""
    def __init__(self, tasks):
        Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.start()
    
    def run(self):
        interrupt = False
        while True:
            func, args, kwargs, ident = self.tasks.get()

            if interrupt:
                self.tasks.task_done()
                continue
            
            try:
                _results[ident].append({
                    'func': func,
                    'args': args,
                    'kwargs': kwargs,
                    'result': func(*args, **kwargs),
                })
            except KeyboardInterrupt, e:
                _results[ident].append({
                    'func': func,
                    'args': args,
                    'kwargs': kwargs,
                    'result': e.args[0],
                })
                interrupt = True
            except Exception, e:
                _results[ident].append({
                    'func': func,
                    'args': args,
                    'kwargs': kwargs,
                    'result': traceback.format_exc(),
                })
            finally:
                self.tasks.task_done()

class ThreadPool:
    """Pool of threads consuming tasks from a queue"""
    def __init__(self, num_threads):
        self.tasks = Queue()
        self.workers = []
        for _ in xrange(num_threads):
            self.workers.append(Worker(self.tasks))
    
    def add(self, func, *args, **kwargs):
        """Add a task to the queue"""
        self.tasks.put((func, args, kwargs, id(self)), False)

    def join(self):
        """Wait for completion of all the tasks in the queue"""
        try:
            self.tasks.join()
            return _results[id(self)]
        except KeyboardInterrupt:
            print '\nReceived keyboard interrupt, closing workers.\n'
            return _results[id(self)]
        finally:
            del _results[id(self)]
########NEW FILE########
__FILENAME__ = streamer
from cStringIO import StringIO

class Streamer(object):
    def __init__(self, fp, *args, **kwargs):
        self.fp = fp
        self.stringio = StringIO()
    
    def write(self, *args, **kwargs):
        self.fp.write(*args, **kwargs)
        self.stringio.write(*args, **kwargs)
    
    def getvalue(self, *args, **kwargs):
        return self.stringio.getvalue(*args, **kwargs)
    
    def read(self, *args, **kwargs):
        return self.stringio.read(*args, **kwargs)

    def flush(self):
        return self.stringio.flush()
########NEW FILE########
