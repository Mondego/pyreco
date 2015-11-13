__FILENAME__ = cache
"""
Utility methods for cache clear.
Used to somehow partially backport http://code.djangoproject.com/ticket/12671
to Django < 1.2
"""

###### clear functions

def clear_db(cache):
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute('DELETE FROM %s' % cache._table)

def clear_filebased(cache):
    tmp_freq, tmp_max = cache._cull_frequency, cache._max_entries
    cache._cull_frequency, cache._max_entries = 1, 0
    cache._cull()
    cache._cull_frequency, cache._max_entries = tmp_freq, tmp_max

def clear_memcached(cache):
    cache._cache.flush_all()

def clear_locmem(cache):
    cache._cache.clear()
    cache._expire_info.clear()

###### end of clear functions


# map

BACKEND_CLEAR_MAP = {
    'db' : clear_db,
    'dummy' : lambda x: x,
    'filebased' : clear_filebased,
    'memcached' : clear_memcached,
    'locmem' : clear_locmem,
}

# utility methods

def get_cache_class():
    return ''

def flush_django_cache(cache_instance=None):
    cache_instance = cache_instance
    if not cache_instance:
        from django.core.cache import cache
        cache_instance = cache

    try:
        cache_instance.clear()
    except AttributeError:
        # Django < 1.2, backport
        backend_name = cache_instance.__module__.split(".")[-1:][0]

        if backend_name not in BACKEND_CLEAR_MAP:
            raise ValueError("Don't know how to clear cache for %s backend" % backend_name)

        BACKEND_CLEAR_MAP[backend_name](cache_instance)

########NEW FILE########
__FILENAME__ = cases
import re
import sys
import urllib2

from django.template import Context, Template, TemplateSyntaxError
from nose.tools import (
                assert_equals,
                assert_almost_equals,
                assert_not_equals,
                assert_raises,
                assert_true,
                assert_false,
)
from nose import SkipTest

from djangosanetesting.utils import twill_patched_go, twill_xpath_go, extract_django_traceback, get_live_server_path

try:
    from django.db import DEFAULT_DB_ALIAS
    MULTIDB_SUPPORT = True
except ImportError:
    DEFAULT_DB_ALIAS = 'default'
    MULTIDB_SUPPORT = False

__all__ = ("UnitTestCase", "DatabaseTestCase", "DestructiveDatabaseTestCase",
           "HttpTestCase", "SeleniumTestCase", "TemplateTagTestCase")

class SaneTestCase(object):
    """ Common ancestor we're using our own hierarchy """
    start_live_server = False
    database_single_transaction = False
    database_flush = False
    selenium_start = False
    no_database_interaction = False
    make_translations = True
    
    SkipTest = SkipTest

    failureException = AssertionError

    def __new__(type, *args, **kwargs):
        """
        When constructing class, add assert* methods from unittest(2),
        both camelCase and pep8-ify style.
        
        """
        obj = super(SaneTestCase, type).__new__(type, *args, **kwargs)

        caps = re.compile('([A-Z])')
        
        from django.test import TestCase
        
        ##########
        ### Scraping heavily inspired by nose testing framework, (C) by Jason Pellerin
        ### and respective authors.
        ##########
        
        class Dummy(TestCase):
            def att():
                pass
        t = Dummy('att')
        
        def pepify(name):
            return caps.sub(lambda m: '_' + m.groups()[0].lower(), name)
        
        def scrape(t):
            for a in [at for at in dir(t) if at.startswith('assert') and not '_' in at]:
                v = getattr(t, a)
                setattr(obj, a, v)
                setattr(obj, pepify(a), v)
        
        scrape(t)
        
        try:
            from unittest2 import TestCase
        except ImportError:
            pass
        else:
            class Dummy(TestCase):
                def att():
                    pass
            t = Dummy('att')
            scrape(t)
                
        return obj

    
    def _check_plugins(self):
        if getattr(self, 'required_sane_plugins', False):
            for plugin in self.required_sane_plugins:
                if not getattr(self, "%s_plugin_started" % plugin, False):
                    raise self.SkipTest("Plugin %s from django-sane-testing required, skipping" % plugin)

    def _check_skipped(self):
        if getattr(self, "skipped", False):
            raise self.SkipTest("I've been marked to skip myself")

    def setUp(self):
        self._check_skipped()
        self._check_plugins()
        if getattr(self, 'multi_db', False) and not MULTIDB_SUPPORT:
            raise self.SkipTest("I need multi db support to run, skipping..")
    
    def is_skipped(self):
        if getattr(self, 'multi_db', False) and not MULTIDB_SUPPORT:
            return True
        try:
            self._check_skipped()
            self._check_plugins()
        except self.SkipTest, e:
            return True
        else:
            return False

    def fail(self, *args, **kwargs):
        raise self.failureException(*args, **kwargs)

    def tearDown(self):
        pass

class UnitTestCase(SaneTestCase):
    """
    This class is a unittest, i.e. do not interact with database et al
    and thus not need any special treatment.
    """
    no_database_interaction = True
    test_type = "unit"


    # undocumented client: can be only used for views that are *guaranteed*
    # not to interact with models
    def get_django_client(self):
        from django.test import Client
        if not getattr(self, '_django_client', False):
            self._django_client = Client()
        return self._django_client

    def set_django_client(self, value):
        self._django_client = value

    client = property(fget=get_django_client, fset=set_django_client)


class DatabaseTestCase(SaneTestCase):
    """
    Tests using database for models in simple: rollback on teardown and we're out.
    
    However, we must check for fixture difference, if we're using another fixture, we must flush database anyway.
    """
    database_single_transaction = True
    database_flush = False
    required_sane_plugins = ["django"]
    django_plugin_started = False
    test_type = "database"

    def get_django_client(self):
        from django.test import Client
        if not getattr(self, '_django_client', False):
            self._django_client = Client()
        return self._django_client
    
    def set_django_client(self, value):
        self._django_client = value
    
    client = property(fget=get_django_client, fset=set_django_client)


class NoCleanupDatabaseTestCase(DatabaseTestCase):
    ''' 
    Initiates test database but have no cleanup utility at all (no rollback, no flush).
    Useful for example when cleanup is done by module-level attribute or pure read-only tests.
    '''
    database_single_transaction = False


class DestructiveDatabaseTestCase(DatabaseTestCase):
    """
    Test behaving so destructively that it needs database to be flushed.
    """
    database_single_transaction = False
    database_flush = True
    test_type = "destructivedatabase"


class NonIsolatedDatabaseTestCase(DatabaseTestCase):
    """
    Like DatabaseTestCase, but rollback transaction only once - after test case. 
    That means tests in test case are not isolated but run faster.
    """
    database_single_transaction = False
    database_flush = False
    database_single_transaction_alfter_case = True


class NonIsolatedDestructiveDatabaseTestCase(DestructiveDatabaseTestCase):
    """
    Like DestructiveDatabaseTestCase, but flushing db only once - after test case. 
    That means tests in test case are not isolated but run much faster.
    """
    database_single_transaction = False
    database_flush = False
    database_flush_alfter_case = True


class HttpTestCase(DestructiveDatabaseTestCase):
    """
    If it is not running, our plugin should start HTTP server
    so we can use it with urllib2 or some webtester.
    """
    start_live_server = True
    required_sane_plugins = ["django", "http"]
    http_plugin_started = False
    test_type = "http"

    def __init__(self, *args, **kwargs):
        super(HttpTestCase, self).__init__(*args, **kwargs)

        self._twill = None
        self._spynner = None

    def get_twill(self):
        if not self._twill:
            try:
                import twill
            except ImportError:
                raise SkipTest("Twill must be installed if you want to use it")

            from twill import get_browser

            self._twill = get_browser()
            self._twill.go = twill_patched_go(browser=self._twill, original_go=self._twill.go)
            self._twill.go_xpath = twill_xpath_go(browser=self._twill, original_go=self._twill.go)

            from twill import commands
            self._twill.commands = commands

        return self._twill

    twill = property(fget=get_twill)

    def get_spynner(self):
        if not self._spynner:
            try:
                import spynner
            except ImportError:
                raise SkipTest("Spynner must be installed if you want to use it")

            self._spynner = spynner.Browser()

        return self._spynner

    spynner = property(fget=get_spynner)


    def assert_code(self, code):
        self.assert_equals(int(code), self.twill.get_code())

    def urlopen(self, *args, **kwargs):
        """
        Wrap for the urlopen function from urllib2
        prints django's traceback if server responds with 500
        """
        try:
            return urllib2.urlopen(*args, **kwargs)
        except urllib2.HTTPError, err:
            if err.code == 500:
                raise extract_django_traceback(http_error=err)
            else:
                raise err

    def tearDown(self):
        if self._spynner:
            self._spynner.close()

        super(HttpTestCase, self).tearDown()

class SeleniumTestCase(HttpTestCase):
    """
    Connect to selenium RC and provide it as instance attribute.
    Configuration in settings:
      * SELENIUM_HOST (default to localhost)
      * SELENIUM_PORT (default to 4444)
      * SELENIUM_BROWSER_COMMAND (default to *opera)
      * SELENIUM_URL_ROOT (default to URL_ROOT default to /)
    """
    selenium_start = True
    start_live_server = True
    required_sane_plugins = ["django", "selenium", "http"]
    selenium_plugin_started = False
    test_type = "selenium"


class TemplateTagTestCase(UnitTestCase):
    """
    Allow for sane and comfortable template tag unit-testing.

    Attributes:
    * `preload' defines which template tag libraries are to be loaded
      before rendering the actual template string
    * `TemplateSyntaxError' is bundled within this class, so that nothing
      from django.template must be imported in most cases of template
      tag testing
    """

    TemplateSyntaxError = TemplateSyntaxError
    preload = ()

    def render_template(self, template, **kwargs):
        """
        Render the given template string with user-defined tag modules
        pre-loaded (according to the class attribute `preload').
        """

        loads = u''
        for load in self.preload:
            loads = u''.join([loads, '{% load ', load, ' %}'])

        template = u''.join([loads, template])
        return Template(template).render(Context(kwargs))

########NEW FILE########
__FILENAME__ = test
"""
Add extra options from the test runner to the ``test`` command, so that you can
browse all the nose options from the command line.
"""
# Taken from django_nose project

from django.conf import settings
from django.test.utils import get_runner


if 'south' in settings.INSTALLED_APPS:
    from south.management.commands.test import Command
else:
    from django.core.management.commands.test import Command

TestRunner = get_runner(settings)

if hasattr(TestRunner, 'options'):
    extra_options = TestRunner.options
else:
    extra_options = []


class Command(Command):
    option_list = Command.option_list + tuple(extra_options)

########NEW FILE########
__FILENAME__ = noseplugins
"""
Various plugins for nose, that let us do our magic.
"""
import socket
import threading
import os
from BaseHTTPServer import HTTPServer
from SocketServer import ThreadingMixIn
from time import sleep
from inspect import ismodule, isclass
import unittest

from django.core.management import call_command
from django.core.servers.basehttp import  WSGIRequestHandler, WSGIServerException
from django.core.urlresolvers import clear_url_caches
from django.test import TestCase as DjangoTestCase

import nose
from nose import SkipTest
from nose.plugins import Plugin

import djangosanetesting
from djangosanetesting import MULTIDB_SUPPORT, DEFAULT_DB_ALIAS
from djangosanetesting.cache import flush_django_cache

#from djagnosanetesting.cache import flush_django_cache
from djangosanetesting.selenium.driver import selenium
from djangosanetesting.utils import (
    get_databases, get_live_server_path, test_databases_exist,
    get_server_handler,
    DEFAULT_LIVE_SERVER_ADDRESS, DEFAULT_LIVE_SERVER_PORT,
)
TEST_CASE_CLASSES = (djangosanetesting.cases.SaneTestCase, unittest.TestCase)

__all__ = ("CherryPyLiveServerPlugin", "DjangoLiveServerPlugin", "DjangoPlugin", "SeleniumPlugin", "SaneTestSelectionPlugin", "ResultPlugin")



def flush_cache(test=None):
    from django.contrib.contenttypes.models import ContentType
    ContentType.objects.clear_cache()

    from django.conf import settings

    if (test and getattr_test(test, "flush_django_cache", False)) \
        or (not hasattr_test(test, "flush_django_cache") and getattr(settings, "DST_FLUSH_DJANGO_CACHE", False)):
        flush_django_cache()

def is_test_case_class(nose_test):
    if isclass(nose_test) and issubclass(nose_test, TEST_CASE_CLASSES):
        return True
    else:
        return False

def get_test_case_class(nose_test):
    if ismodule(nose_test) or is_test_case_class(nose_test):
        return nose_test 
    if isinstance(nose_test.test, nose.case.MethodTestCase):
        return nose_test.test.test.im_class
    else:
        return nose_test.test.__class__

def get_test_case_method(nose_test):
    if not hasattr(nose_test, 'test'): # not test method/functoin, probably test module or test class (from startContext)
        return None
    if isinstance(nose_test.test, (nose.case.MethodTestCase, nose.case.FunctionTestCase)):
        return nose_test.test.test
    else:
        return getattr(nose_test.test, nose_test.test._testMethodName)

def get_test_case_instance(nose_test):
    if ismodule(nose_test) or is_test_case_class(nose_test):
        return nose_test 
    if getattr(nose_test, 'test') and not isinstance(nose_test.test, (nose.case.FunctionTestCase)):
        return get_test_case_method(nose_test).im_self

def hasattr_test(nose_test, attr_name):
    ''' hasattr from test method or test_case.
    '''

    if nose_test is None:
        return False
    elif ismodule(nose_test) or is_test_case_class(nose_test):
        return hasattr(nose_test, attr_name)
    elif hasattr(get_test_case_method(nose_test), attr_name) or hasattr(get_test_case_instance(nose_test), attr_name):
        return True
    else:
        return False

def getattr_test(nose_test, attr_name, default = False):
    ''' Get attribute from test method, if not found then form it's test_case instance
        (meaning that test method have higher priority). If not found even
        in test_case then return default.
    '''
    test_attr = getattr(get_test_case_method(nose_test), attr_name, None)
    if test_attr is not None:
        return test_attr
    else:
        return getattr(get_test_case_instance(nose_test), attr_name, default)

def enable_test(test_case, plugin_attribute):
    if not getattr(test_case, plugin_attribute, False):
        setattr(test_case, plugin_attribute, True)

def flush_database(test_case, database=DEFAULT_DB_ALIAS):
    call_command('flush', verbosity=0, interactive=False, database=database)


#####
### Okey, this is hack because of #14, or Django's #3357
### We could runtimely patch basehttp.WSGIServer to inherit from our HTTPServer,
### but we'd like to have our own modifications anyway, so part of it is cut & paste
### from basehttp.WSGIServer.
### Credits & Kudos to Django authors and Rob Hudson et al from #3357
#####

class StoppableWSGIServer(ThreadingMixIn, HTTPServer):
    """WSGIServer with short timeout, so that server thread can stop this server."""
    application = None
    
    def __init__(self, server_address, RequestHandlerClass=None):
        HTTPServer.__init__(self, server_address, RequestHandlerClass) 
    
    def server_bind(self):
        """ Bind server to socket. Overrided to store server name & set timeout"""
        try:
            HTTPServer.server_bind(self)
        except Exception, e:
            raise WSGIServerException, e
        self.setup_environ()
        self.socket.settimeout(1)

    def get_request(self):
        """Checks for timeout when getting request."""
        try:
            sock, address = self.socket.accept()
#            sock.settimeout(None)
            return (sock, address)
        except socket.timeout:
            raise

    #####
    ### Code from basehttp.WSGIServer follows
    #####
    def setup_environ(self):
        # Set up base environment
        env = self.base_environ = {}
        env['SERVER_NAME'] = self.server_name
        env['GATEWAY_INTERFACE'] = 'CGI/1.1'
        env['SERVER_PORT'] = str(self.server_port)
        env['REMOTE_HOST']=''
        env['CONTENT_LENGTH']=''
        env['SCRIPT_NAME'] = ''

    def get_app(self):
        return self.application

    def set_app(self,application):
        self.application = application


class TestServerThread(threading.Thread):
    """Thread for running a http server while tests are running."""

    def __init__(self, address, port):
        self.address = address
        self.port = port
        self._stopevent = threading.Event()
        self.started = threading.Event()
        self.error = None
        super(TestServerThread, self).__init__()

    def run(self):
        """Sets up test server and loops over handling http requests."""
        try:
            handler = get_server_handler()
            server_address = (self.address, self.port)
            httpd = StoppableWSGIServer(server_address, WSGIRequestHandler)
            #httpd = basehttp.WSGIServer(server_address, basehttp.WSGIRequestHandler)
            httpd.set_app(handler)
            self.started.set()
        except WSGIServerException, e:
            self.error = e
            self.started.set()
            return

        # Loop until we get a stop event.
        while not self._stopevent.isSet():
            httpd.handle_request()

    def join(self, timeout=None):
        """Stop the thread and wait for it to finish."""
        self._stopevent.set()
        threading.Thread.join(self, timeout)


class AbstractLiveServerPlugin(Plugin):
    def __init__(self):
        Plugin.__init__(self)
        self.server_started = False
        self.server_thread = None

    def options(self, parser, env=os.environ):
        Plugin.options(self, parser, env)

    def configure(self, options, config):
        Plugin.configure(self, options, config)

    def start_server(self):
        raise NotImplementedError()

    def stop_server(self):
        raise NotImplementedError()

    def check_database_multithread_compilant(self):
        # When using memory database, complain as we'd use indepenent databases
        connections = get_databases()
        for alias in connections:
            database = connections[alias]
            if database.settings_dict['NAME'] == ':memory:' and database.settings_dict['ENGINE'] in ('django.db.backends.sqlite3', 'sqlite3'):
                self.skipped = True
                return False
        return True

    def startTest(self, test):
        from django.conf import settings
        test_case = get_test_case_class(test)
        test_case_instance = get_test_case_instance(test)
        if not self.server_started and getattr_test(test, "start_live_server", False):
            if not self.check_database_multithread_compilant():
                raise SkipTest("You're running database in memory, but trying to use live server in another thread. Skipping.")
            self.start_server(
                address=getattr(settings, "LIVE_SERVER_ADDRESS", DEFAULT_LIVE_SERVER_ADDRESS),
                port=int(getattr(settings, "LIVE_SERVER_PORT", DEFAULT_LIVE_SERVER_PORT))
            )
            self.server_started = True
            
        enable_test(test_case, 'http_plugin_started')
        
        # clear test client for test isolation
        if test_case_instance:
            test_case_instance.client = None

    def stopTest(self, test):
        test_case_instance = get_test_case_instance(test)
        if getattr_test(test, "_twill", None):
            from twill.commands import reset_browser
            reset_browser()
            test_case_instance._twill = None

    def finalize(self, result):
        self.stop_test_server()


class DjangoLiveServerPlugin(AbstractLiveServerPlugin):
    """
    Patch Django on fly and start live HTTP server, if TestCase is inherited
    from HttpTestCase or start_live_server attribute is set to True.
    
    Taken from Michael Rogers implementation from http://trac.getwindmill.com/browser/trunk/windmill/authoring/djangotest.py
    """
    name = 'djangoliveserver'
    activation_parameter = '--with-djangoliveserver'
    
    def start_server(self, address='0.0.0.0', port=8000):
        self.server_thread = TestServerThread(address, port)
        self.server_thread.start()
        self.server_thread.started.wait()
        if self.server_thread.error:
            raise self.server_thread.error
         
    def stop_test_server(self):
        if self.server_thread:
            self.server_thread.join()
        self.server_started = False

#####
### It was a nice try with Django server being threaded.
### It still sucks for some cases (did I mentioned urllib2?),
### so provide cherrypy as working alternative.
### Do imports in method to avoid CP as dependency
### Code originally written by Mikeal Rogers under Apache License.
#####

class CherryPyLiveServerPlugin(AbstractLiveServerPlugin):
    name = 'cherrypyliveserver'
    activation_parameter = '--with-cherrypyliveserver'

    def start_server(self, address='0.0.0.0', port=8000):
        handler = get_server_handler()
 
        def application(environ, start_response):
            environ['PATH_INFO'] = environ['SCRIPT_NAME'] + environ['PATH_INFO']
            return handler(environ, start_response)
        
        from cherrypy.wsgiserver import CherryPyWSGIServer
        from threading import Thread
        self.httpd = CherryPyWSGIServer((address, port), application, server_name='django-test-http')
        self.httpd_thread = Thread(target=self.httpd.start)
        self.httpd_thread.start()
        #FIXME: This could be avoided by passing self to thread class starting django
        # and waiting for Event lock
        sleep(.5)
   
    def stop_test_server(self):
        if self.server_started:
            self.httpd.stop()
            self.server_started = False


class DjangoPlugin(Plugin):
    """
    Setup and teardown django test environment
    """
    activation_parameter = '--with-django'
    name = 'django'
    env_opt = 'DST_PERSIST_TEST_DATABASE'

    def startContext(self, context):
        if ismodule(context) or is_test_case_class(context):
            if ismodule(context):
                attr_suffix = ''
            else:
                attr_suffix = '_after_all_tests'
            if getattr(context, 'database_single_transaction' + attr_suffix, False):
                #TODO: When no test case in this module needing database is run (for example 
                #      user selected only one unitTestCase), database should not be initialized.
                #      So it would be best if db is initialized when first test case needing 
                #      database is run. 
                
                # create test database if not already created
                if not self.test_database_created:
                    self._create_test_databases()

                if getattr(context, 'database_single_transaction' + attr_suffix, False):
                    from django.db import transaction
                    transaction.enter_transaction_management()
                    transaction.managed(True)

                # when used from startTest, nose-wrapped testcase is provided -- while now,
                # we have 'bare' test case.

                self._prepare_tests_fixtures(context)

    def stopContext(self, context):
        if ismodule(context) or is_test_case_class(context):
            from django.conf import settings
            from django.db import transaction

            if ismodule(context):
                attr_suffix = ''
            else:
                attr_suffix = '_after_all_tests'

            if self.test_database_created:
                if getattr(context, 'database_single_transaction' + attr_suffix, False):
                    transaction.rollback()
                    transaction.leave_transaction_management()

                if getattr(context, "database_flush" + attr_suffix, None):
                    for db in self._get_tests_databases(getattr(context, 'multidb', False)):
                        getattr(settings, "TEST_DATABASE_FLUSH_COMMAND", flush_database)(self, database=db)

    def options(self, parser, env=os.environ):
        Plugin.options(self, parser, env)
        
        parser.add_option(
            "", "--persist-test-database", action="store_true",
            default=env.get(self.env_opt), dest="persist_test_database",
            help="Do not flush database unless neccessary [%s]" % self.env_opt)

    def configure(self, options, config):
        Plugin.configure(self, options, config)
        self.persist_test_database = options.persist_test_database

    def setup_databases(self, verbosity, autoclobber, **kwargs):
        # Taken from Django 1.2 code, (C) respective Django authors. Modified for backward compatibility by me
        connections = get_databases()
        old_names = []
        mirrors = []

        from django.conf import settings
        if 'south' in settings.INSTALLED_APPS:
            from south.management.commands import patch_for_test_db_setup

            settings.SOUTH_TESTS_MIGRATE = getattr(settings, 'DST_RUN_SOUTH_MIGRATIONS', True)
            patch_for_test_db_setup()

        for alias in connections:
            connection = connections[alias]
            # If the database is a test mirror, redirect it's connection
            # instead of creating a test database.
            if 'TEST_MIRROR' in connection.settings_dict and connection.settings_dict['TEST_MIRROR']:
                mirrors.append((alias, connection))
                mirror_alias = connection.settings_dict['TEST_MIRROR']
                connections._connections[alias] = connections[mirror_alias]
            else:
                if 'NAME' in connection.settings_dict:
                    old_names.append((connection, connection.settings_dict['NAME']))
                else:
                    old_names.append((connection, connection.settings_dict['DATABASE_NAME']))
                connection.creation.create_test_db(verbosity=verbosity, autoclobber=autoclobber)
        return old_names, mirrors

    def teardown_databases(self, old_config, verbosity, **kwargs):
        # Taken from Django 1.2 code, (C) respective Django authors
        connections = get_databases()
        old_names, mirrors = old_config
        # Point all the mirrors back to the originals
        for alias, connection in mirrors:
            connections._connections[alias] = connection
        # Destroy all the non-mirror databases
        for connection, old_name in old_names:
            connection.creation.destroy_test_db(old_name, verbosity)
        
        self.test_database_created = False

    def begin(self):
        from django.test.utils import setup_test_environment
        setup_test_environment()
        self.test_database_created = False

    def prepareTestRunner(self, runner):
        """
        Before running tests, initialize database et al, so noone will complain
        """
        # FIXME: this should be lazy for tests that do not need test
        # database at all
        
        flush_cache()

    def finalize(self, result):
        """
        At the end, tear down our testbed
        """
        from django.test.utils import teardown_test_environment
        teardown_test_environment()
        
        if not self.persist_test_database and getattr(self, 'test_database_created', None):
            self.teardown_databases(self.old_config, verbosity=False)
#            from django.db import connection
#            connection.creation.destroy_test_db(self.old_name, verbosity=False)
    
    
    def startTest(self, test):
        """
        When preparing test, check whether to make our database fresh
        """

        test_case = get_test_case_class(test)
        if issubclass(test_case, DjangoTestCase):
            return

        #####
        ### FIXME: It would be nice to separate handlings as plugins et al...but what 
        ### about the context?
        #####
        
        from django.core import mail
        from django.conf import settings
        from django.db import transaction
        
        test_case = get_test_case_class(test)
        test_case_instance = get_test_case_instance(test)

        mail.outbox = []
        enable_test(test_case, 'django_plugin_started')
        
        if hasattr(test_case_instance, 'is_skipped') and test_case_instance.is_skipped():
            return
        
        # clear URLs if needed
        if hasattr(test_case, 'urls'):
            test_case._old_root_urlconf = settings.ROOT_URLCONF
            settings.ROOT_URLCONF = test_case.urls
            clear_url_caches()
        
        #####
        ### Database handling follows
        #####
        if getattr_test(test, 'no_database_interaction', False):
            # for true unittests, we can leave database handling for later,
            # as unittests by definition do not interacts with database
            return
        
        # create test database if not already created
        if not self.test_database_created:
            self._create_test_databases()
        
        # make self.transaction available
        test_case.transaction = transaction
        
        if getattr_test(test, 'database_single_transaction'):
            transaction.enter_transaction_management()
            transaction.managed(True)
        
        self._prepare_tests_fixtures(test)
        
    def stopTest(self, test):
        """
        After test is run, clear urlconf, caches and database
        """

        test_case = get_test_case_class(test)
        if issubclass(test_case, DjangoTestCase):
            return

        from django.db import transaction
        from django.conf import settings

        test_case = get_test_case_class(test)
        test_case_instance = get_test_case_instance(test)

        if hasattr(test_case_instance, 'is_skipped') and test_case_instance.is_skipped():
            return

        if hasattr(test_case, '_old_root_urlconf'):
            settings.ROOT_URLCONF = test_case._old_root_urlconf
            clear_url_caches()
        flush_cache(test)

        if getattr_test(test, 'no_database_interaction', False):
            # for true unittests, we can leave database handling for later,
            # as unittests by definition do not interacts with database
            return
        
        if getattr_test(test, 'database_single_transaction'):
            transaction.rollback()
            transaction.leave_transaction_management()

        if getattr_test(test, "database_flush", True):
            for db in self._get_tests_databases(getattr_test(test, 'multi_db')):
                getattr(settings, "TEST_DATABASE_FLUSH_COMMAND", flush_database)(self, database=db)

    def _get_databases(self):
        try:
            from django.db import connections
        except ImportError:
            from django.db import connection
            connections = {DEFAULT_DB_ALIAS : connection}
        return connections

    def _get_tests_databases(self, multi_db):
        ''' Get databases for flush: according to test's multi_db attribute
            only defuault db or all databases will be flushed.
        '''
        connections = self._get_databases()
        if multi_db:
            if not MULTIDB_SUPPORT:
                raise RuntimeError('This test should be skipped but for a reason it is not')
            else:
                databases = connections
        else:
            if MULTIDB_SUPPORT:
                databases = [DEFAULT_DB_ALIAS]
            else:
                databases = connections
        return databases
    
    def _prepare_tests_fixtures(self, test):
        # fixtures are loaded inside transaction, thus we don't need to flush
        # between database_single_transaction tests when their fixtures differ
        if hasattr_test(test, 'fixtures'):
            if getattr_test(test, "database_flush", True):
                # commits are allowed during tests
                commit = True
            else:
                commit = False
            for db in self._get_tests_databases(getattr_test(test, 'multi_db')):
                call_command('loaddata', *getattr_test(test, 'fixtures'), **{'verbosity': 0, 'commit' : commit, 'database' : db})

    def _create_test_databases(self):
        from django.conf import settings
        connections = self._get_databases()

        database_created = False
        if not self.persist_test_database:
            self.old_config = self.setup_databases(verbosity=False, autoclobber=True)
            database_created = self.test_database_created = True
        else:
            # switch to test database, find out whether it exists, if so, use it, otherwise create a new:
            for connection in connections.all():
                connection.close()
                old_db_name = connection.settings_dict["NAME"]
                connection.settings_dict["NAME"] = connection.creation._get_test_db_name()
                try:
                    connection.cursor()
                except Exception:
                    # test database doesn't exist, create it as normally:
                    connection.settings_dict["NAME"] = old_db_name # return original db name
                    connection.creation.create_test_db()
                    database_created = True

                connection.features.confirm()
                self.test_database_created = True

        if database_created:
            for db in connections:
                if 'south' in settings.INSTALLED_APPS and getattr(settings, 'DST_RUN_SOUTH_MIGRATIONS', True):
                    call_command('migrate', database=db)
                
                if getattr(settings, "FLUSH_TEST_DATABASE_AFTER_INITIAL_SYNCDB", False):
                    getattr(settings, "TEST_DATABASE_FLUSH_COMMAND", flush_database)(self, database=db)

class DjangoTranslationPlugin(Plugin):
    """
    For testcases with selenium_start set to True, connect to Selenium RC.
    """
    activation_parameter = '--with-djangotranslations'
    name = 'djangotranslations'

    score = 70

    def options(self, parser, env=os.environ):
        Plugin.options(self, parser, env)

    def configure(self, options, config):
        Plugin.configure(self, options, config)

    def startTest(self, test):
        # set translation, if allowed
        if getattr_test(test, "make_translations", None):
            from django.conf import settings
            from django.utils import translation
            lang = getattr_test(test, "translation_language_code", None)
            if not lang:
                lang = getattr(settings, "LANGUAGE_CODE", 'en-us')
            translation.activate(lang)

    def stopTest(self, test):
        from django.utils import translation
        translation.deactivate()


class SeleniumPlugin(Plugin):
    """
    For testcases with selenium_start set to True, connect to Selenium RC.
    """
    activation_parameter = '--with-selenium'
    name = 'selenium'
    
    score = 80
    
    def options(self, parser, env=os.environ):
        Plugin.options(self, parser, env)

    def configure(self, options, config):
        Plugin.configure(self, options, config)

    def startTest(self, test):
        """
        When preparing test, check whether to make our database fresh
        """

        from django.conf import settings
        from django.utils.importlib import import_module

        test_case = get_test_case_class(test)

        enable_test(test_case, 'selenium_plugin_started')

        # import selenium class to use
        selenium_import = getattr(settings, "DST_SELENIUM_DRIVER",
                            "djangosanetesting.selenium.driver.selenium").split(".")
        selenium_module, selenium_cls = ".".join(selenium_import[:-1]), selenium_import[-1]
        selenium = getattr(import_module(selenium_module), selenium_cls)
        
        if getattr_test(test, "selenium_start", False):
            browser = getattr(test_case, 'selenium_browser_command', None)
            if browser is None:
                browser = getattr(settings, "SELENIUM_BROWSER_COMMAND", '*opera')

            sel = selenium(
                      getattr(settings, "SELENIUM_HOST", 'localhost'),
                      int(getattr(settings, "SELENIUM_PORT", 4444)),
                      browser,
                      getattr(settings, "SELENIUM_URL_ROOT", get_live_server_path()),
                  )
            try:
                sel.start()
                test_case.selenium_started = True
            except Exception, err:
                # we must catch it all as there is untyped socket exception on Windows :-]]]
                if getattr(settings, "FORCE_SELENIUM_TESTS", False):
                    raise
                else:
                    test_case.skipped = True
                    #raise SkipTest(err)
            else:
                if isinstance(test.test, nose.case.MethodTestCase):
                    test.test.test.im_self.selenium = sel
                else:
                    test_case.skipped = True
                    #raise SkipTest("I can only assign selenium to TestCase instance; argument passing will be implemented later")

    def stopTest(self, test):
        if getattr_test(test, "selenium_started", False):
            test.test.test.im_self.selenium.stop()
            test.test.test.im_self.selenium = None


class SaneTestSelectionPlugin(Plugin):
    """ Accept additional options, so we can filter out test we don't want """
    RECOGNIZED_TESTS = ["unit", "database", "destructivedatabase", "http", "selenium"]
    score = 150
    
    def options(self, parser, env=os.environ):
        Plugin.options(self, parser, env)
        parser.add_option(
            "-u", "--select-unittests", action="store_true",
            default=False, dest="select_unittests",
            help="Run all unittests"
        )
        parser.add_option(
            "--select-databasetests", action="store_true",
            default=False, dest="select_databasetests",
            help="Run all database tests"
        )
        parser.add_option(
            "--select-destructivedatabasetests", action="store_true",
            default=False, dest="select_destructivedatabasetests",
            help="Run all destructive database tests"
        )
        parser.add_option(
            "--select-httptests", action="store_true",
            default=False, dest="select_httptests",
            help="Run all HTTP tests"
        )
        parser.add_option(
            "--select-seleniumtests", action="store_true",
            default=False, dest="select_seleniumtests",
            help="Run all Selenium tests"
        )

    def configure(self, options, config):
        Plugin.configure(self, options, config)
        self.enabled_tests = [i for i in self.RECOGNIZED_TESTS if getattr(options, "select_%stests" % i, False)]
    
    def startTest(self, test):
        test_case = get_test_case_class(test)
        if getattr_test(test, "test_type", "unit") not in self.enabled_tests:
            test_case.skipped = True
            #raise SkipTest(u"Test type %s not enabled" % getattr(test_case, "test_type", "unit"))

##########
### Result plugin is used when using Django test runner
### Taken from django-nose project.
### (C) Jeff Balogh and contributors, released under BSD license.
##########

class ResultPlugin(Plugin):
    """
    Captures the TestResult object for later inspection.

    nose doesn't return the full test result object from any of its runner
    methods.  Pass an instance of this plugin to the TestProgram and use
    ``result`` after running the tests to get the TestResult object.
    """

    name = "djangoresult"
    activation_parameter = '--with-djangoresult'
    enabled = True

    def configure(self, options, config):
        Plugin.configure(self, options, config)

    def finalize(self, result):
        self.result = result


########NEW FILE########
__FILENAME__ = runnercompat
import sys
import signal
import unittest

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

#This module was taken from Django 1.2.4 source code and embedded for backward
#compatibility.
#
#Copyright (c) Django Software Foundation
#Distributed under BSD license

try:
    all
except NameError:
    from django.utils.itercompat import all

# The module name for tests outside models.py
TEST_MODULE = 'tests'

class DjangoTestRunner(unittest.TextTestRunner):

    def run(self, *args, **kwargs):
        """
        Runs the test suite after registering a custom signal handler
        that triggers a graceful exit when Ctrl-C is pressed.
        """
        self._default_keyboard_interrupt_handler = signal.signal(signal.SIGINT,
            self._keyboard_interrupt_handler)
        try:
            result = super(DjangoTestRunner, self).run(*args, **kwargs)
        finally:
            signal.signal(signal.SIGINT, self._default_keyboard_interrupt_handler)
        return result

    def _keyboard_interrupt_handler(self, signal_number, stack_frame):
        """
        Handles Ctrl-C by setting a flag that will stop the test run when
        the currently running test completes.
        """
        self._keyboard_interrupt_intercepted = True
        sys.stderr.write(" <Test run halted by Ctrl-C> ")
        # Set the interrupt handler back to the default handler, so that
        # another Ctrl-C press will trigger immediate exit.
        signal.signal(signal.SIGINT, self._default_keyboard_interrupt_handler)

    def _makeResult(self):
        result = super(DjangoTestRunner, self)._makeResult()
        failfast = self.failfast

        def stoptest_override(func):
            def stoptest(test):
                # If we were set to failfast and the unit test failed,
                # or if the user has typed Ctrl-C, report and quit
                if (failfast and not result.wasSuccessful()) or \
                    self._keyboard_interrupt_intercepted:
                    result.stop()
                func(test)
            return stoptest

        setattr(result, 'stopTest', stoptest_override(result.stopTest))
        return result

def get_tests(app_module):
    try:
        app_path = app_module.__name__.split('.')[:-1]
        test_module = __import__('.'.join(app_path + [TEST_MODULE]), {}, {}, TEST_MODULE)
    except ImportError, e:
        # Couldn't import tests.py. Was it due to a missing file, or
        # due to an import error in a tests.py that actually exists?
        import os.path
        from imp import find_module
        try:
            mod = find_module(TEST_MODULE, [os.path.dirname(app_module.__file__)])
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

def build_suite(app_module):
    "Create a complete Django test suite for the provided application module"
    from django.test import _doctest as doctest
    from django.test.testcases import OutputChecker, DocTestRunner
    doctestOutputChecker = OutputChecker()

    suite = unittest.TestSuite()

    # Load unit and doctests in the models.py module. If module has
    # a suite() method, use it. Otherwise build the test suite ourselves.
    if hasattr(app_module, 'suite'):
        suite.addTest(app_module.suite())
    else:
        suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(app_module))
        try:
            suite.addTest(doctest.DocTestSuite(app_module,
                                               checker=doctestOutputChecker,
                                               runner=DocTestRunner))
        except ValueError:
            # No doc tests in models.py
            pass

    # Check to see if a separate 'tests' module exists parallel to the
    # models module
    test_module = get_tests(app_module)
    if test_module:
        # Load unit and doctests in the tests.py module. If module has
        # a suite() method, use it. Otherwise build the test suite ourselves.
        if hasattr(test_module, 'suite'):
            suite.addTest(test_module.suite())
        else:
            suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_module))
            try:
                suite.addTest(doctest.DocTestSuite(test_module,
                                                   checker=doctestOutputChecker,
                                                   runner=DocTestRunner))
            except ValueError:
                # No doc tests in tests.py
                pass
    return suite

def build_test(label):
    """Construct a test case with the specified label. Label should be of the
    form model.TestClass or model.TestClass.test_method. Returns an
    instantiated test or test suite corresponding to the label provided.

    """
    parts = label.split('.')
    if len(parts) < 2 or len(parts) > 3:
        raise ValueError("Test label '%s' should be of the form app.TestCase or app.TestCase.test_method" % label)

    #
    # First, look for TestCase instances with a name that matches
    #
    from django.db.models import get_app
    app_module = get_app(parts[0])
    test_module = get_tests(app_module)
    TestClass = getattr(app_module, parts[1], None)

    # Couldn't find the test class in models.py; look in tests.py
    if TestClass is None:
        if test_module:
            TestClass = getattr(test_module, parts[1], None)

    try:
        if issubclass(TestClass, unittest.TestCase):
            if len(parts) == 2: # label is app.TestClass
                try:
                    return unittest.TestLoader().loadTestsFromTestCase(TestClass)
                except TypeError:
                    raise ValueError("Test label '%s' does not refer to a test class" % label)
            else: # label is app.TestClass.test_method
                return TestClass(parts[2])
    except TypeError:
        # TestClass isn't a TestClass - it must be a method or normal class
        pass

    #
    # If there isn't a TestCase, look for a doctest that matches
    #
    from django.test import _doctest as doctest
    from django.test.testcases import OutputChecker, DocTestRunner
    doctestOutputChecker = OutputChecker()
    tests = []
    for module in app_module, test_module:
        try:
            doctests = doctest.DocTestSuite(module,
                                            checker=doctestOutputChecker,
                                            runner=DocTestRunner)
            # Now iterate over the suite, looking for doctests whose name
            # matches the pattern that was given
            for test in doctests:
                if test._dt_test.name in (
                        '%s.%s' % (module.__name__, '.'.join(parts[1:])),
                        '%s.__test__.%s' % (module.__name__, '.'.join(parts[1:]))):
                    tests.append(test)
        except ValueError:
            # No doctests found.
            pass

    # If no tests were found, then we were given a bad test label.
    if not tests:
        raise ValueError("Test label '%s' does not refer to a test" % label)

    # Construct a suite out of the tests that matched.
    return unittest.TestSuite(tests)

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

def dependency_ordered(test_databases, dependencies):
    """Reorder test_databases into an order that honors the dependencies
    described in TEST_DEPENDENCIES.
    """
    ordered_test_databases = []
    resolved_databases = set()
    while test_databases:
        changed = False
        deferred = []

        while test_databases:
            signature, (db_name, aliases) = test_databases.pop()
            dependencies_satisfied = True
            for alias in aliases:
                if alias in dependencies:
                    if all(a in resolved_databases for a in dependencies[alias]):
                        # all dependencies for this alias are satisfied
                        dependencies.pop(alias)
                        resolved_databases.add(alias)
                    else:
                        dependencies_satisfied = False
                else:
                    resolved_databases.add(alias)

            if dependencies_satisfied:
                ordered_test_databases.append((signature, (db_name, aliases)))
                changed = True
            else:
                deferred.append((signature, (db_name, aliases)))

        if not changed:
            raise ImproperlyConfigured("Circular dependency in TEST_DEPENDENCIES")
        test_databases = deferred
    return ordered_test_databases

class DjangoTestSuiteRunner(object):
    def __init__(self, verbosity=1, interactive=True, failfast=True, **kwargs):
        self.verbosity = verbosity
        self.interactive = interactive
        self.failfast = failfast

    def setup_test_environment(self, **kwargs):
        from django.test.utils import setup_test_environment
        setup_test_environment()
        settings.DEBUG = False

    def build_suite(self, test_labels, extra_tests=None, **kwargs):
        from django.db.models import get_apps
        from django.test.testcases import TestCase

        suite = unittest.TestSuite()

        if test_labels:
            for label in test_labels:
                if '.' in label:
                    suite.addTest(build_test(label))
                else:
                    app = get_app(label)
                    suite.addTest(build_suite(app))
        else:
            for app in get_apps():
                suite.addTest(build_suite(app))

        if extra_tests:
            for test in extra_tests:
                suite.addTest(test)

        return reorder_suite(suite, (TestCase,))

    def setup_databases(self, **kwargs):
        from django.db import connections, DEFAULT_DB_ALIAS

        # First pass -- work out which databases actually need to be created,
        # and which ones are test mirrors or duplicate entries in DATABASES
        mirrored_aliases = {}
        test_databases = {}
        dependencies = {}
        for alias in connections:
            connection = connections[alias]
            if connection.settings_dict['TEST_MIRROR']:
                # If the database is marked as a test mirror, save
                # the alias.
                mirrored_aliases[alias] = connection.settings_dict['TEST_MIRROR']
            else:
                # Store a tuple with DB parameters that uniquely identify it.
                # If we have two aliases with the same values for that tuple,
                # we only need to create the test database once.
                item = test_databases.setdefault(
                    connection.creation.test_db_signature(),
                    (connection.settings_dict['NAME'], [])
                )
                item[1].append(alias)

                if 'TEST_DEPENDENCIES' in connection.settings_dict:
                    dependencies[alias] = connection.settings_dict['TEST_DEPENDENCIES']
                else:
                    if alias != DEFAULT_DB_ALIAS:
                        dependencies[alias] = connection.settings_dict.get('TEST_DEPENDENCIES', [DEFAULT_DB_ALIAS])

        # Second pass -- actually create the databases.
        old_names = []
        mirrors = []
        for signature, (db_name, aliases) in dependency_ordered(test_databases.items(), dependencies):
            # Actually create the database for the first connection
            connection = connections[aliases[0]]
            old_names.append((connection, db_name, True))
            test_db_name = connection.creation.create_test_db(self.verbosity, autoclobber=not self.interactive)
            for alias in aliases[1:]:
                connection = connections[alias]
                if db_name:
                    old_names.append((connection, db_name, False))
                    connection.settings_dict['NAME'] = test_db_name
                else:
                    # If settings_dict['NAME'] isn't defined, we have a backend where
                    # the name isn't important -- e.g., SQLite, which uses :memory:.
                    # Force create the database instead of assuming it's a duplicate.
                    old_names.append((connection, db_name, True))
                    connection.creation.create_test_db(self.verbosity, autoclobber=not self.interactive)

        for alias, mirror_alias in mirrored_aliases.items():
            mirrors.append((alias, connections[alias].settings_dict['NAME']))
            connections[alias].settings_dict['NAME'] = connections[mirror_alias].settings_dict['NAME']

        return old_names, mirrors

    def run_suite(self, suite, **kwargs):
        return DjangoTestRunner(verbosity=self.verbosity, failfast=self.failfast).run(suite)

    def teardown_databases(self, old_config, **kwargs):
        from django.db import connections
        old_names, mirrors = old_config
        # Point all the mirrors back to the originals
        for alias, old_name in mirrors:
            connections[alias].settings_dict['NAME'] = old_name
        # Destroy all the non-mirror databases
        for connection, old_name, destroy in old_names:
            if destroy:
                connection.creation.destroy_test_db(old_name, self.verbosity)
            else:
                connection.settings_dict['NAME'] = old_name

    def teardown_test_environment(self, **kwargs):
        from django.test.utils import teardown_test_environment
        teardown_test_environment()

    def suite_result(self, suite, result, **kwargs):
        return len(result.failures) + len(result.errors)

    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        """
        Run the unit tests for all the test labels in the provided list.
        Labels must be of the form:
         - app.TestClass.test_method
            Run a single specific test method
         - app.TestClass
            Run all the test methods in a given class
         - app
            Search for doctests and unittests in the named application.

        When looking for tests, the test runner will look in the models and
        tests modules for the application.

        A list of 'extra' tests may also be provided; these tests
        will be added to the test suite.

        Returns the number of tests that failed.
        """
        from django.test.utils import (
            setup_test_environment, teardown_test_environment)
        self.setup_test_environment()
        suite = self.build_suite(test_labels, extra_tests)
        old_config = self.setup_databases()
        result = self.run_suite(suite)
        self.teardown_databases(old_config)
        self.teardown_test_environment()
        return self.suite_result(suite, result)

########NEW FILE########
__FILENAME__ = driver
"""
Copyright 2006 ThoughtWorks, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
__docformat__ = "restructuredtext en"

# This file has been automatically generated via XSL

# Alterations has been added by Almad <bugs at almad.net> for some sane
# testing consistency goodies, like wait_for_element_present support
# and it's usage before clicking et al

import httplib
import urllib
import re

class selenium:
    """
    Defines an object that runs Selenium commands.
    
    Element Locators
    ~~~~~~~~~~~~~~~~
    
    Element Locators tell Selenium which HTML element a command refers to.
    The format of a locator is:
    
    \ *locatorType*\ **=**\ \ *argument*
    
    
    We support the following strategies for locating elements:
    
    
    *   \ **identifier**\ =\ *id*: 
        Select the element with the specified @id attribute. If no match is
        found, select the first element whose @name attribute is \ *id*.
        (This is normally the default; see below.)
    *   \ **id**\ =\ *id*:
        Select the element with the specified @id attribute.
    *   \ **name**\ =\ *name*:
        Select the first element with the specified @name attribute.
        
        *   username
        *   name=username
        
        
        The name may optionally be followed by one or more \ *element-filters*, separated from the name by whitespace.  If the \ *filterType* is not specified, \ **value**\  is assumed.
        
        *   name=flavour value=chocolate
        
        
    *   \ **dom**\ =\ *javascriptExpression*: 
        
        Find an element by evaluating the specified string.  This allows you to traverse the HTML Document Object
        Model using JavaScript.  Note that you must not return a value in this string; simply make it the last expression in the block.
        
        *   dom=document.forms['myForm'].myDropdown
        *   dom=document.images[56]
        *   dom=function foo() { return document.links[1]; }; foo();
        
        
    *   \ **xpath**\ =\ *xpathExpression*: 
        Locate an element using an XPath expression.
        
        *   xpath=//img[@alt='The image alt text']
        *   xpath=//table[@id='table1']//tr[4]/td[2]
        *   xpath=//a[contains(@href,'#id1')]
        *   xpath=//a[contains(@href,'#id1')]/@class
        *   xpath=(//table[@class='stylee'])//th[text()='theHeaderText']/../td
        *   xpath=//input[@name='name2' and @value='yes']
        *   xpath=//\*[text()="right"]
        
        
    *   \ **link**\ =\ *textPattern*:
        Select the link (anchor) element which contains text matching the
        specified \ *pattern*.
        
        *   link=The link text
        
        
    *   \ **css**\ =\ *cssSelectorSyntax*:
        Select the element using css selectors. Please refer to CSS2 selectors, CSS3 selectors for more information. You can also check the TestCssLocators test in the selenium test suite for an example of usage, which is included in the downloaded selenium core package.
        
        *   css=a[href="#id3"]
        *   css=span#firstChild + span
        
        
        Currently the css selector locator supports all css1, css2 and css3 selectors except namespace in css3, some pseudo classes(:nth-of-type, :nth-last-of-type, :first-of-type, :last-of-type, :only-of-type, :visited, :hover, :active, :focus, :indeterminate) and pseudo elements(::first-line, ::first-letter, ::selection, ::before, ::after). 
        
    *   \ **ui**\ =\ *uiSpecifierString*:
        Locate an element by resolving the UI specifier string to another locator, and evaluating it. See the Selenium UI-Element Reference for more details.
        
        *   ui=loginPages::loginButton()
        *   ui=settingsPages::toggle(label=Hide Email)
        *   ui=forumPages::postBody(index=2)//a[2]
        
        
    
    
    
    Without an explicit locator prefix, Selenium uses the following default
    strategies:
    
    
    *   \ **dom**\ , for locators starting with "document."
    *   \ **xpath**\ , for locators starting with "//"
    *   \ **identifier**\ , otherwise
    
    Element Filters
    ~~~~~~~~~~~~~~~
    
    Element filters can be used with a locator to refine a list of candidate elements.  They are currently used only in the 'name' element-locator.
    
    Filters look much like locators, ie.
    
    \ *filterType*\ **=**\ \ *argument*
    
    Supported element-filters are:
    
    \ **value=**\ \ *valuePattern*
    
    
    Matches elements based on their values.  This is particularly useful for refining a list of similarly-named toggle-buttons.
    
    \ **index=**\ \ *index*
    
    
    Selects a single element based on its position in the list (offset from zero).
    
    String-match Patterns
    ~~~~~~~~~~~~~~~~~~~~~
    
    Various Pattern syntaxes are available for matching string values:
    
    
    *   \ **glob:**\ \ *pattern*:
        Match a string against a "glob" (aka "wildmat") pattern. "Glob" is a
        kind of limited regular-expression syntax typically used in command-line
        shells. In a glob pattern, "\*" represents any sequence of characters, and "?"
        represents any single character. Glob patterns match against the entire
        string.
    *   \ **regexp:**\ \ *regexp*:
        Match a string using a regular-expression. The full power of JavaScript
        regular-expressions is available.
    *   \ **regexpi:**\ \ *regexpi*:
        Match a string using a case-insensitive regular-expression.
    *   \ **exact:**\ \ *string*:
        
        Match a string exactly, verbatim, without any of that fancy wildcard
        stuff.
    
    
    
    If no pattern prefix is specified, Selenium assumes that it's a "glob"
    pattern.
    
    
    
    For commands that return multiple values (such as verifySelectOptions),
    the string being matched is a comma-separated list of the return values,
    where both commas and backslashes in the values are backslash-escaped.
    When providing a pattern, the optional matching syntax (i.e. glob,
    regexp, etc.) is specified once, as usual, at the beginning of the
    pattern.
    
    
    """

### This part is hard-coded in the XSL
    def __init__(self, host, port, browserStartCommand, browserURL):
        self.host = host
        self.port = port
        self.browserStartCommand = browserStartCommand
        self.browserURL = browserURL
        self.sessionId = None
        self.extensionJs = ""

    def setExtensionJs(self, extensionJs):
        self.extensionJs = extensionJs
        
    def start(self):
        result = self.get_string("getNewBrowserSession", [self.browserStartCommand, self.browserURL, self.extensionJs])
        try:
            self.sessionId = result
        except ValueError:
            raise Exception, result
        
    def stop(self):
        self.do_command("testComplete", [])
        self.sessionId = None

    def do_command(self, verb, args):
        conn = httplib.HTTPConnection(self.host, self.port)
        body = u'cmd=' + urllib.quote_plus(unicode(verb).encode('utf-8'))
        for i in range(len(args)):
            body += '&' + unicode(i+1) + '=' + urllib.quote_plus(unicode(args[i]).encode('utf-8'))
        if (None != self.sessionId):
            body += "&sessionId=" + unicode(self.sessionId)
        headers = {"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"}
        conn.request("POST", "/selenium-server/driver/", body, headers)
    
        response = conn.getresponse()
        #print response.status, response.reason
        data = unicode(response.read(), "UTF-8")
        result = response.reason
        #print "Selenium Result: " + repr(data) + "\n\n"
        if (not data.startswith('OK')):
            raise Exception, data
        return data
    
    def get_string(self, verb, args):
        result = self.do_command(verb, args)
        return result[3:]
    
    def get_string_array(self, verb, args):
        csv = self.get_string(verb, args)
        token = ""
        tokens = []
        escape = False
        for i in range(len(csv)):
            letter = csv[i]
            if (escape):
                token = token + letter
                escape = False
                continue
            if (letter == '\\'):
                escape = True
            elif (letter == ','):
                tokens.append(token)
                token = ""
            else:
                token = token + letter
        tokens.append(token)
        return tokens

    def get_number(self, verb, args):
        # Is there something I need to do here?
        return self.get_string(verb, args)
    
    def get_number_array(self, verb, args):
        # Is there something I need to do here?
        return self.get_string_array(verb, args)

    def get_boolean(self, verb, args):
        boolstr = self.get_string(verb, args)
        if ("true" == boolstr):
            return True
        if ("false" == boolstr):
            return False
        raise ValueError, "result is neither 'true' nor 'false': " + boolstr
    
    def get_boolean_array(self, verb, args):
        boolarr = self.get_string_array(verb, args)
        for i in range(len(boolarr)):
            if ("true" == boolstr):
                boolarr[i] = True
                continue
            if ("false" == boolstr):
                boolarr[i] = False
                continue
            raise ValueError, "result is neither 'true' nor 'false': " + boolarr[i]
        return boolarr
    
    

### From here on, everything's auto-generated from XML


    def click(self,locator):
        """
        Clicks on a link, button, checkbox or radio button. If the click action
        causes a new page to load (like a link usually does), call
        waitForPageToLoad.
        
        'locator' is an element locator
        """
        self.wait_for_element_present(locator)
        self.do_command("click", [locator,])


    def double_click(self,locator):
        """
        Double clicks on a link, button, checkbox or radio button. If the double click action
        causes a new page to load (like a link usually does), call
        waitForPageToLoad.
        
        'locator' is an element locator
        """
        self.wait_for_element_present(locator)
        self.do_command("doubleClick", [locator,])


    def context_menu(self,locator):
        """
        Simulates opening the context menu for the specified element (as might happen if the user "right-clicked" on the element).
        
        'locator' is an element locator
        """
        self.do_command("contextMenu", [locator,])


    def click_at(self,locator,coordString):
        """
        Clicks on a link, button, checkbox or radio button. If the click action
        causes a new page to load (like a link usually does), call
        waitForPageToLoad.
        
        'locator' is an element locator
        'coordString' is specifies the x,y position (i.e. - 10,20) of the mouse      event relative to the element returned by the locator.
        """
        self.wait_for_element_present(locator)
        self.do_command("clickAt", [locator,coordString,])


    def double_click_at(self,locator,coordString):
        """
        Doubleclicks on a link, button, checkbox or radio button. If the action
        causes a new page to load (like a link usually does), call
        waitForPageToLoad.
        
        'locator' is an element locator
        'coordString' is specifies the x,y position (i.e. - 10,20) of the mouse      event relative to the element returned by the locator.
        """
        self.do_command("doubleClickAt", [locator,coordString,])


    def context_menu_at(self,locator,coordString):
        """
        Simulates opening the context menu for the specified element (as might happen if the user "right-clicked" on the element).
        
        'locator' is an element locator
        'coordString' is specifies the x,y position (i.e. - 10,20) of the mouse      event relative to the element returned by the locator.
        """
        self.do_command("contextMenuAt", [locator,coordString,])


    def fire_event(self,locator,eventName):
        """
        Explicitly simulate an event, to trigger the corresponding "on\ *event*"
        handler.
        
        'locator' is an element locator
        'eventName' is the event name, e.g. "focus" or "blur"
        """
        self.do_command("fireEvent", [locator,eventName,])


    def focus(self,locator):
        """
        Move the focus to the specified element; for example, if the element is an input field, move the cursor to that field.
        
        'locator' is an element locator
        """
        self.do_command("focus", [locator,])


    def key_press(self,locator,keySequence):
        """
        Simulates a user pressing and releasing a key.
        
        'locator' is an element locator
        'keySequence' is Either be a string("\" followed by the numeric keycode  of the key to be pressed, normally the ASCII value of that key), or a single  character. For example: "w", "\119".
        """
        self.do_command("keyPress", [locator,keySequence,])


    def shift_key_down(self):
        """
        Press the shift key and hold it down until doShiftUp() is called or a new page is loaded.
        
        """
        self.do_command("shiftKeyDown", [])


    def shift_key_up(self):
        """
        Release the shift key.
        
        """
        self.do_command("shiftKeyUp", [])


    def meta_key_down(self):
        """
        Press the meta key and hold it down until doMetaUp() is called or a new page is loaded.
        
        """
        self.do_command("metaKeyDown", [])


    def meta_key_up(self):
        """
        Release the meta key.
        
        """
        self.do_command("metaKeyUp", [])


    def alt_key_down(self):
        """
        Press the alt key and hold it down until doAltUp() is called or a new page is loaded.
        
        """
        self.do_command("altKeyDown", [])


    def alt_key_up(self):
        """
        Release the alt key.
        
        """
        self.do_command("altKeyUp", [])


    def control_key_down(self):
        """
        Press the control key and hold it down until doControlUp() is called or a new page is loaded.
        
        """
        self.do_command("controlKeyDown", [])


    def control_key_up(self):
        """
        Release the control key.
        
        """
        self.do_command("controlKeyUp", [])


    def key_down(self,locator,keySequence):
        """
        Simulates a user pressing a key (without releasing it yet).
        
        'locator' is an element locator
        'keySequence' is Either be a string("\" followed by the numeric keycode  of the key to be pressed, normally the ASCII value of that key), or a single  character. For example: "w", "\119".
        """
        self.do_command("keyDown", [locator,keySequence,])


    def key_up(self,locator,keySequence):
        """
        Simulates a user releasing a key.
        
        'locator' is an element locator
        'keySequence' is Either be a string("\" followed by the numeric keycode  of the key to be pressed, normally the ASCII value of that key), or a single  character. For example: "w", "\119".
        """
        self.do_command("keyUp", [locator,keySequence,])


    def mouse_over(self,locator):
        """
        Simulates a user hovering a mouse over the specified element.
        
        'locator' is an element locator
        """
        self.do_command("mouseOver", [locator,])


    def mouse_out(self,locator):
        """
        Simulates a user moving the mouse pointer away from the specified element.
        
        'locator' is an element locator
        """
        self.do_command("mouseOut", [locator,])


    def mouse_down(self,locator):
        """
        Simulates a user pressing the left mouse button (without releasing it yet) on
        the specified element.
        
        'locator' is an element locator
        """
        self.do_command("mouseDown", [locator,])


    def mouse_down_right(self,locator):
        """
        Simulates a user pressing the right mouse button (without releasing it yet) on
        the specified element.
        
        'locator' is an element locator
        """
        self.do_command("mouseDownRight", [locator,])


    def mouse_down_at(self,locator,coordString):
        """
        Simulates a user pressing the left mouse button (without releasing it yet) at
        the specified location.
        
        'locator' is an element locator
        'coordString' is specifies the x,y position (i.e. - 10,20) of the mouse      event relative to the element returned by the locator.
        """
        self.do_command("mouseDownAt", [locator,coordString,])


    def mouse_down_right_at(self,locator,coordString):
        """
        Simulates a user pressing the right mouse button (without releasing it yet) at
        the specified location.
        
        'locator' is an element locator
        'coordString' is specifies the x,y position (i.e. - 10,20) of the mouse      event relative to the element returned by the locator.
        """
        self.do_command("mouseDownRightAt", [locator,coordString,])


    def mouse_up(self,locator):
        """
        Simulates the event that occurs when the user releases the mouse button (i.e., stops
        holding the button down) on the specified element.
        
        'locator' is an element locator
        """
        self.do_command("mouseUp", [locator,])


    def mouse_up_right(self,locator):
        """
        Simulates the event that occurs when the user releases the right mouse button (i.e., stops
        holding the button down) on the specified element.
        
        'locator' is an element locator
        """
        self.do_command("mouseUpRight", [locator,])


    def mouse_up_at(self,locator,coordString):
        """
        Simulates the event that occurs when the user releases the mouse button (i.e., stops
        holding the button down) at the specified location.
        
        'locator' is an element locator
        'coordString' is specifies the x,y position (i.e. - 10,20) of the mouse      event relative to the element returned by the locator.
        """
        self.do_command("mouseUpAt", [locator,coordString,])


    def mouse_up_right_at(self,locator,coordString):
        """
        Simulates the event that occurs when the user releases the right mouse button (i.e., stops
        holding the button down) at the specified location.
        
        'locator' is an element locator
        'coordString' is specifies the x,y position (i.e. - 10,20) of the mouse      event relative to the element returned by the locator.
        """
        self.do_command("mouseUpRightAt", [locator,coordString,])


    def mouse_move(self,locator):
        """
        Simulates a user pressing the mouse button (without releasing it yet) on
        the specified element.
        
        'locator' is an element locator
        """
        self.do_command("mouseMove", [locator,])


    def mouse_move_at(self,locator,coordString):
        """
        Simulates a user pressing the mouse button (without releasing it yet) on
        the specified element.
        
        'locator' is an element locator
        'coordString' is specifies the x,y position (i.e. - 10,20) of the mouse      event relative to the element returned by the locator.
        """
        self.do_command("mouseMoveAt", [locator,coordString,])


    def type(self,locator,value):
        """
        Sets the value of an input field, as though you typed it in.
        
        
        Can also be used to set the value of combo boxes, check boxes, etc. In these cases,
        value should be the value of the option selected, not the visible text.
        
        
        'locator' is an element locator
        'value' is the value to type
        """
        self.wait_for_element_present(locator)
        self.do_command("type", [locator,value,])


    def type_keys(self,locator,value):
        """
        Simulates keystroke events on the specified element, as though you typed the value key-by-key.
        
        
        This is a convenience method for calling keyDown, keyUp, keyPress for every character in the specified string;
        this is useful for dynamic UI widgets (like auto-completing combo boxes) that require explicit key events.
        
        Unlike the simple "type" command, which forces the specified value into the page directly, this command
        may or may not have any visible effect, even in cases where typing keys would normally have a visible effect.
        For example, if you use "typeKeys" on a form element, you may or may not see the results of what you typed in
        the field.
        
        In some cases, you may need to use the simple "type" command to set the value of the field and then the "typeKeys" command to
        send the keystroke events corresponding to what you just typed.
        
        
        'locator' is an element locator
        'value' is the value to type
        """
        self.wait_for_element_present(locator)
        self.do_command("typeKeys", [locator,value,])


    def set_speed(self,value):
        """
        Set execution speed (i.e., set the millisecond length of a delay which will follow each selenium operation).  By default, there is no such delay, i.e.,
        the delay is 0 milliseconds.
        
        'value' is the number of milliseconds to pause after operation
        """
        self.do_command("setSpeed", [value,])


    def get_speed(self):
        """
        Get execution speed (i.e., get the millisecond length of the delay following each selenium operation).  By default, there is no such delay, i.e.,
        the delay is 0 milliseconds.
        
        See also setSpeed.
        
        """
        return self.get_string("getSpeed", [])


    def check(self,locator):
        """
        Check a toggle-button (checkbox/radio)
        
        'locator' is an element locator
        """
        self.do_command("check", [locator,])


    def uncheck(self,locator):
        """
        Uncheck a toggle-button (checkbox/radio)
        
        'locator' is an element locator
        """
        self.do_command("uncheck", [locator,])


    def select(self,selectLocator,optionLocator):
        """
        Select an option from a drop-down using an option locator.
        
        
        
        Option locators provide different ways of specifying options of an HTML
        Select element (e.g. for selecting a specific option, or for asserting
        that the selected option satisfies a specification). There are several
        forms of Select Option Locator.
        
        
        *   \ **label**\ =\ *labelPattern*:
            matches options based on their labels, i.e. the visible text. (This
            is the default.)
            
            *   label=regexp:^[Oo]ther
            
            
        *   \ **value**\ =\ *valuePattern*:
            matches options based on their values.
            
            *   value=other
            
            
        *   \ **id**\ =\ *id*:
            
            matches options based on their ids.
            
            *   id=option1
            
            
        *   \ **index**\ =\ *index*:
            matches an option based on its index (offset from zero).
            
            *   index=2
            
            
        
        
        
        If no option locator prefix is provided, the default behaviour is to match on \ **label**\ .
        
        
        
        'selectLocator' is an element locator identifying a drop-down menu
        'optionLocator' is an option locator (a label by default)
        """
        self.do_command("select", [selectLocator,optionLocator,])


    def add_selection(self,locator,optionLocator):
        """
        Add a selection to the set of selected options in a multi-select element using an option locator.
        
        @see #doSelect for details of option locators
        
        'locator' is an element locator identifying a multi-select box
        'optionLocator' is an option locator (a label by default)
        """
        self.do_command("addSelection", [locator,optionLocator,])


    def remove_selection(self,locator,optionLocator):
        """
        Remove a selection from the set of selected options in a multi-select element using an option locator.
        
        @see #doSelect for details of option locators
        
        'locator' is an element locator identifying a multi-select box
        'optionLocator' is an option locator (a label by default)
        """
        self.do_command("removeSelection", [locator,optionLocator,])


    def remove_all_selections(self,locator):
        """
        Unselects all of the selected options in a multi-select element.
        
        'locator' is an element locator identifying a multi-select box
        """
        self.do_command("removeAllSelections", [locator,])


    def submit(self,formLocator):
        """
        Submit the specified form. This is particularly useful for forms without
        submit buttons, e.g. single-input "Search" forms.
        
        'formLocator' is an element locator for the form you want to submit
        """
        self.do_command("submit", [formLocator,])


    def open(self,url):
        """
        Opens an URL in the test frame. This accepts both relative and absolute
        URLs.
        
        The "open" command waits for the page to load before proceeding,
        ie. the "AndWait" suffix is implicit.
        
        \ *Note*: The URL must be on the same domain as the runner HTML
        due to security restrictions in the browser (Same Origin Policy). If you
        need to open an URL on another domain, use the Selenium Server to start a
        new browser session on that domain.
        
        'url' is the URL to open; may be relative or absolute
        """
        self.do_command("open", [url,])


    def open_window(self,url,windowID):
        """
        Opens a popup window (if a window with that ID isn't already open).
        After opening the window, you'll need to select it using the selectWindow
        command.
        
        
        This command can also be a useful workaround for bug SEL-339.  In some cases, Selenium will be unable to intercept a call to window.open (if the call occurs during or before the "onLoad" event, for example).
        In those cases, you can force Selenium to notice the open window's name by using the Selenium openWindow command, using
        an empty (blank) url, like this: openWindow("", "myFunnyWindow").
        
        
        'url' is the URL to open, which can be blank
        'windowID' is the JavaScript window ID of the window to select
        """
        self.do_command("openWindow", [url,windowID,])


    def select_window(self,windowID):
        """
        Selects a popup window using a window locator; once a popup window has been selected, all
        commands go to that window. To select the main window again, use null
        as the target.
        
        
        
        
        Window locators provide different ways of specifying the window object:
        by title, by internal JavaScript "name," or by JavaScript variable.
        
        
        *   \ **title**\ =\ *My Special Window*:
            Finds the window using the text that appears in the title bar.  Be careful;
            two windows can share the same title.  If that happens, this locator will
            just pick one.
            
        *   \ **name**\ =\ *myWindow*:
            Finds the window using its internal JavaScript "name" property.  This is the second 
            parameter "windowName" passed to the JavaScript method window.open(url, windowName, windowFeatures, replaceFlag)
            (which Selenium intercepts).
            
        *   \ **var**\ =\ *variableName*:
            Some pop-up windows are unnamed (anonymous), but are associated with a JavaScript variable name in the current
            application window, e.g. "window.foo = window.open(url);".  In those cases, you can open the window using
            "var=foo".
            
        
        
        
        If no window locator prefix is provided, we'll try to guess what you mean like this:
        
        1.) if windowID is null, (or the string "null") then it is assumed the user is referring to the original window instantiated by the browser).
        
        2.) if the value of the "windowID" parameter is a JavaScript variable name in the current application window, then it is assumed
        that this variable contains the return value from a call to the JavaScript window.open() method.
        
        3.) Otherwise, selenium looks in a hash it maintains that maps string names to window "names".
        
        4.) If \ *that* fails, we'll try looping over all of the known windows to try to find the appropriate "title".
        Since "title" is not necessarily unique, this may have unexpected behavior.
        
        If you're having trouble figuring out the name of a window that you want to manipulate, look at the Selenium log messages
        which identify the names of windows created via window.open (and therefore intercepted by Selenium).  You will see messages
        like the following for each window as it is opened:
        
        ``debug: window.open call intercepted; window ID (which you can use with selectWindow()) is "myNewWindow"``
        
        In some cases, Selenium will be unable to intercept a call to window.open (if the call occurs during or before the "onLoad" event, for example).
        (This is bug SEL-339.)  In those cases, you can force Selenium to notice the open window's name by using the Selenium openWindow command, using
        an empty (blank) url, like this: openWindow("", "myFunnyWindow").
        
        
        'windowID' is the JavaScript window ID of the window to select
        """
        self.do_command("selectWindow", [windowID,])

    def select_pop_up(self,windowID):
        """
        Simplifies the process of selecting a popup window (and does not offer
        functionality beyond what ``selectWindow()`` already provides).

        *   If ``windowID`` is either not specified, or specified as
            "null", the first non-top window is selected. The top window is the one
            that would be selected by ``selectWindow()`` without providing a
            ``windowID`` . This should not be used when more than one popup
            window is in play.
        *   Otherwise, the window will be looked up considering
            ``windowID`` as the following in order: 1) the "name" of the
            window, as specified to ``window.open()``; 2) a javascript
            variable which is a reference to a window; and 3) the title of the
            window. This is the same ordered lookup performed by
            ``selectWindow`` .



        'windowID' is an identifier for the popup window, which can take on a                  number of different meanings
        """
        self.do_command("selectPopUp", [windowID,])


    def deselect_pop_up(self):
        """
        Selects the main window. Functionally equivalent to using
        ``selectWindow()`` and specifying no value for
        ``windowID``.

        """
        self.do_command("deselectPopUp", [])


    def select_frame(self,locator):
        """
        Selects a frame within the current window.  (You may invoke this command
        multiple times to select nested frames.)  To select the parent frame, use
        "relative=parent" as a locator; to select the top frame, use "relative=top".
        You can also select a frame by its 0-based index number; select the first frame with
        "index=0", or the third frame with "index=2".
        
        
        You may also use a DOM expression to identify the frame you want directly,
        like this: ``dom=frames["main"].frames["subframe"]``
        
        
        'locator' is an element locator identifying a frame or iframe
        """
        self.do_command("selectFrame", [locator,])


    def get_whether_this_frame_match_frame_expression(self,currentFrameString,target):
        """
        Determine whether current/locator identify the frame containing this running code.
        
        
        This is useful in proxy injection mode, where this code runs in every
        browser frame and window, and sometimes the selenium server needs to identify
        the "current" frame.  In this case, when the test calls selectFrame, this
        routine is called for each frame to figure out which one has been selected.
        The selected frame will return true, while all others will return false.
        
        
        'currentFrameString' is starting frame
        'target' is new frame (which might be relative to the current one)
        """
        return self.get_boolean("getWhetherThisFrameMatchFrameExpression", [currentFrameString,target,])


    def get_whether_this_window_match_window_expression(self,currentWindowString,target):
        """
        Determine whether currentWindowString plus target identify the window containing this running code.
        
        
        This is useful in proxy injection mode, where this code runs in every
        browser frame and window, and sometimes the selenium server needs to identify
        the "current" window.  In this case, when the test calls selectWindow, this
        routine is called for each window to figure out which one has been selected.
        The selected window will return true, while all others will return false.
        
        
        'currentWindowString' is starting window
        'target' is new window (which might be relative to the current one, e.g., "_parent")
        """
        return self.get_boolean("getWhetherThisWindowMatchWindowExpression", [currentWindowString,target,])


    def wait_for_pop_up(self,windowID,timeout):
        """
        Waits for a popup window to appear and load up.
        
        'windowID' is the JavaScript window "name" of the window that will appear (not the text of the title bar)
        'timeout' is a timeout in milliseconds, after which the action will return with an error
        """
        self.do_command("waitForPopUp", [windowID,timeout,])


    def choose_cancel_on_next_confirmation(self):
        """
        
        
        By default, Selenium's overridden window.confirm() function will
        return true, as if the user had manually clicked OK; after running
        this command, the next call to confirm() will return false, as if
        the user had clicked Cancel.  Selenium will then resume using the
        default behavior for future confirmations, automatically returning 
        true (OK) unless/until you explicitly call this command for each
        confirmation.
        
        
        
        Take note - every time a confirmation comes up, you must
        consume it with a corresponding getConfirmation, or else
        the next selenium operation will fail.
        
        
        
        """
        self.do_command("chooseCancelOnNextConfirmation", [])


    def choose_ok_on_next_confirmation(self):
        """
        
        
        Undo the effect of calling chooseCancelOnNextConfirmation.  Note
        that Selenium's overridden window.confirm() function will normally automatically
        return true, as if the user had manually clicked OK, so you shouldn't
        need to use this command unless for some reason you need to change
        your mind prior to the next confirmation.  After any confirmation, Selenium will resume using the
        default behavior for future confirmations, automatically returning 
        true (OK) unless/until you explicitly call chooseCancelOnNextConfirmation for each
        confirmation.
        
        
        
        Take note - every time a confirmation comes up, you must
        consume it with a corresponding getConfirmation, or else
        the next selenium operation will fail.
        
        
        
        """
        self.do_command("chooseOkOnNextConfirmation", [])


    def answer_on_next_prompt(self,answer):
        """
        Instructs Selenium to return the specified answer string in response to
        the next JavaScript prompt [window.prompt()].
        
        'answer' is the answer to give in response to the prompt pop-up
        """
        self.do_command("answerOnNextPrompt", [answer,])


    def go_back(self):
        """
        Simulates the user clicking the "back" button on their browser.
        
        """
        self.do_command("goBack", [])


    def refresh(self):
        """
        Simulates the user clicking the "Refresh" button on their browser.
        
        """
        self.do_command("refresh", [])


    def close(self):
        """
        Simulates the user clicking the "close" button in the titlebar of a popup
        window or tab.
        
        """
        self.do_command("close", [])


    def is_alert_present(self):
        """
        Has an alert occurred?
        
        
        
        This function never throws an exception
        
        
        
        """
        return self.get_boolean("isAlertPresent", [])


    def is_prompt_present(self):
        """
        Has a prompt occurred?
        
        
        
        This function never throws an exception
        
        
        
        """
        return self.get_boolean("isPromptPresent", [])


    def is_confirmation_present(self):
        """
        Has confirm() been called?
        
        
        
        This function never throws an exception
        
        
        
        """
        return self.get_boolean("isConfirmationPresent", [])


    def get_alert(self):
        """
        Retrieves the message of a JavaScript alert generated during the previous action, or fail if there were no alerts.
        
        
        Getting an alert has the same effect as manually clicking OK. If an
        alert is generated but you do not consume it with getAlert, the next Selenium action
        will fail.
        
        Under Selenium, JavaScript alerts will NOT pop up a visible alert
        dialog.
        
        Selenium does NOT support JavaScript alerts that are generated in a
        page's onload() event handler. In this case a visible dialog WILL be
        generated and Selenium will hang until someone manually clicks OK.
        
        
        """
        return self.get_string("getAlert", [])


    def get_confirmation(self):
        """
        Retrieves the message of a JavaScript confirmation dialog generated during
        the previous action.
        
        
        
        By default, the confirm function will return true, having the same effect
        as manually clicking OK. This can be changed by prior execution of the
        chooseCancelOnNextConfirmation command. 
        
        
        
        If an confirmation is generated but you do not consume it with getConfirmation,
        the next Selenium action will fail.
        
        
        
        NOTE: under Selenium, JavaScript confirmations will NOT pop up a visible
        dialog.
        
        
        
        NOTE: Selenium does NOT support JavaScript confirmations that are
        generated in a page's onload() event handler. In this case a visible
        dialog WILL be generated and Selenium will hang until you manually click
        OK.
        
        
        
        """
        return self.get_string("getConfirmation", [])


    def get_prompt(self):
        """
        Retrieves the message of a JavaScript question prompt dialog generated during
        the previous action.
        
        
        Successful handling of the prompt requires prior execution of the
        answerOnNextPrompt command. If a prompt is generated but you
        do not get/verify it, the next Selenium action will fail.
        
        NOTE: under Selenium, JavaScript prompts will NOT pop up a visible
        dialog.
        
        NOTE: Selenium does NOT support JavaScript prompts that are generated in a
        page's onload() event handler. In this case a visible dialog WILL be
        generated and Selenium will hang until someone manually clicks OK.
        
        
        """
        return self.get_string("getPrompt", [])


    def get_location(self):
        """
        Gets the absolute URL of the current page.
        
        """
        return self.get_string("getLocation", [])


    def get_title(self):
        """
        Gets the title of the current page.
        
        """
        return self.get_string("getTitle", [])


    def get_body_text(self):
        """
        Gets the entire text of the page.
        
        """
        return self.get_string("getBodyText", [])


    def get_value(self,locator):
        """
        Gets the (whitespace-trimmed) value of an input field (or anything else with a value parameter).
        For checkbox/radio elements, the value will be "on" or "off" depending on
        whether the element is checked or not.
        
        'locator' is an element locator
        """
        self.wait_for_element_present(locator)
        return self.get_string("getValue", [locator,])


    def get_text(self,locator):
        """
        Gets the text of an element. This works for any element that contains
        text. This command uses either the textContent (Mozilla-like browsers) or
        the innerText (IE-like browsers) of the element, which is the rendered
        text shown to the user.
        
        'locator' is an element locator
        """
        self.wait_for_element_present(locator)
        return self.get_string("getText", [locator,])


    def highlight(self,locator):
        """
        Briefly changes the backgroundColor of the specified element yellow.  Useful for debugging.
        
        'locator' is an element locator
        """
        self.do_command("highlight", [locator,])


    def get_eval(self,script):
        """
        Gets the result of evaluating the specified JavaScript snippet.  The snippet may
        have multiple lines, but only the result of the last line will be returned.
        
        
        Note that, by default, the snippet will run in the context of the "selenium"
        object itself, so ``this`` will refer to the Selenium object.  Use ``window`` to
        refer to the window of your application, e.g. ``window.document.getElementById('foo')``
        
        If you need to use
        a locator to refer to a single element in your application page, you can
        use ``this.browserbot.findElement("id=foo")`` where "id=foo" is your locator.
        
        
        'script' is the JavaScript snippet to run
        """
        return self.get_string("getEval", [script,])


    def is_checked(self,locator):
        """
        Gets whether a toggle-button (checkbox/radio) is checked.  Fails if the specified element doesn't exist or isn't a toggle-button.
        
        'locator' is an element locator pointing to a checkbox or radio button
        """
        return self.get_boolean("isChecked", [locator,])


    def get_table(self,tableCellAddress):
        """
        Gets the text from a cell of a table. The cellAddress syntax
        tableLocator.row.column, where row and column start at 0.
        
        'tableCellAddress' is a cell address, e.g. "foo.1.4"
        """
        return self.get_string("getTable", [tableCellAddress,])


    def get_selected_labels(self,selectLocator):
        """
        Gets all option labels (visible text) for selected options in the specified select or multi-select element.
        
        'selectLocator' is an element locator identifying a drop-down menu
        """
        return self.get_string_array("getSelectedLabels", [selectLocator,])


    def get_selected_label(self,selectLocator):
        """
        Gets option label (visible text) for selected option in the specified select element.
        
        'selectLocator' is an element locator identifying a drop-down menu
        """
        return self.get_string("getSelectedLabel", [selectLocator,])


    def get_selected_values(self,selectLocator):
        """
        Gets all option values (value attributes) for selected options in the specified select or multi-select element.
        
        'selectLocator' is an element locator identifying a drop-down menu
        """
        return self.get_string_array("getSelectedValues", [selectLocator,])


    def get_selected_value(self,selectLocator):
        """
        Gets option value (value attribute) for selected option in the specified select element.
        
        'selectLocator' is an element locator identifying a drop-down menu
        """
        return self.get_string("getSelectedValue", [selectLocator,])


    def get_selected_indexes(self,selectLocator):
        """
        Gets all option indexes (option number, starting at 0) for selected options in the specified select or multi-select element.
        
        'selectLocator' is an element locator identifying a drop-down menu
        """
        return self.get_string_array("getSelectedIndexes", [selectLocator,])


    def get_selected_index(self,selectLocator):
        """
        Gets option index (option number, starting at 0) for selected option in the specified select element.
        
        'selectLocator' is an element locator identifying a drop-down menu
        """
        return self.get_string("getSelectedIndex", [selectLocator,])


    def get_selected_ids(self,selectLocator):
        """
        Gets all option element IDs for selected options in the specified select or multi-select element.
        
        'selectLocator' is an element locator identifying a drop-down menu
        """
        return self.get_string_array("getSelectedIds", [selectLocator,])


    def get_selected_id(self,selectLocator):
        """
        Gets option element ID for selected option in the specified select element.
        
        'selectLocator' is an element locator identifying a drop-down menu
        """
        return self.get_string("getSelectedId", [selectLocator,])


    def is_something_selected(self,selectLocator):
        """
        Determines whether some option in a drop-down menu is selected.
        
        'selectLocator' is an element locator identifying a drop-down menu
        """
        return self.get_boolean("isSomethingSelected", [selectLocator,])


    def get_select_options(self,selectLocator):
        """
        Gets all option labels in the specified select drop-down.
        
        'selectLocator' is an element locator identifying a drop-down menu
        """
        return self.get_string_array("getSelectOptions", [selectLocator,])


    def get_attribute(self,attributeLocator):
        """
        Gets the value of an element attribute. The value of the attribute may
        differ across browsers (this is the case for the "style" attribute, for
        example).
        
        'attributeLocator' is an element locator followed by an @ sign and then the name of the attribute, e.g. "foo@bar"
        """
        return self.get_string("getAttribute", [attributeLocator,])


    def is_text_present(self,pattern):
        """
        Verifies that the specified text pattern appears somewhere on the rendered page shown to the user.
        
        'pattern' is a pattern to match with the text of the page
        """
        return self.get_boolean("isTextPresent", [pattern,])


    def is_element_present(self,locator):
        """
        Verifies that the specified element is somewhere on the page.
        
        'locator' is an element locator
        """
        return self.get_boolean("isElementPresent", [locator,])


    def is_visible(self,locator):
        """
        Determines if the specified element is visible. An
        element can be rendered invisible by setting the CSS "visibility"
        property to "hidden", or the "display" property to "none", either for the
        element itself or one if its ancestors.  This method will fail if
        the element is not present.
        
        'locator' is an element locator
        """
        return self.get_boolean("isVisible", [locator,])


    def is_editable(self,locator):
        """
        Determines whether the specified input element is editable, ie hasn't been disabled.
        This method will fail if the specified element isn't an input element.
        
        'locator' is an element locator
        """
        return self.get_boolean("isEditable", [locator,])


    def get_all_buttons(self):
        """
        Returns the IDs of all buttons on the page.
        
        
        If a given button has no ID, it will appear as "" in this array.
        
        
        """
        return self.get_string_array("getAllButtons", [])


    def get_all_links(self):
        """
        Returns the IDs of all links on the page.
        
        
        If a given link has no ID, it will appear as "" in this array.
        
        
        """
        return self.get_string_array("getAllLinks", [])


    def get_all_fields(self):
        """
        Returns the IDs of all input fields on the page.
        
        
        If a given field has no ID, it will appear as "" in this array.
        
        
        """
        return self.get_string_array("getAllFields", [])


    def get_attribute_from_all_windows(self,attributeName):
        """
        Returns every instance of some attribute from all known windows.
        
        'attributeName' is name of an attribute on the windows
        """
        return self.get_string_array("getAttributeFromAllWindows", [attributeName,])


    def dragdrop(self,locator,movementsString):
        """
        deprecated - use dragAndDrop instead
        
        'locator' is an element locator
        'movementsString' is offset in pixels from the current location to which the element should be moved, e.g., "+70,-300"
        """
        self.do_command("dragdrop", [locator,movementsString,])


    def set_mouse_speed(self,pixels):
        """
        Configure the number of pixels between "mousemove" events during dragAndDrop commands (default=10).
        
        Setting this value to 0 means that we'll send a "mousemove" event to every single pixel
        in between the start location and the end location; that can be very slow, and may
        cause some browsers to force the JavaScript to timeout.
        
        If the mouse speed is greater than the distance between the two dragged objects, we'll
        just send one "mousemove" at the start location and then one final one at the end location.
        
        
        'pixels' is the number of pixels between "mousemove" events
        """
        self.do_command("setMouseSpeed", [pixels,])


    def get_mouse_speed(self):
        """
        Returns the number of pixels between "mousemove" events during dragAndDrop commands (default=10).
        
        """
        return self.get_number("getMouseSpeed", [])


    def drag_and_drop(self,locator,movementsString):
        """
        Drags an element a certain distance and then drops it
        
        'locator' is an element locator
        'movementsString' is offset in pixels from the current location to which the element should be moved, e.g., "+70,-300"
        """
        self.wait_for_element_present(locator)
        self.do_command("dragAndDrop", [locator,movementsString,])


    def drag_and_drop_to_object(self,locatorOfObjectToBeDragged,locatorOfDragDestinationObject):
        """
        Drags an element and drops it on another element
        
        'locatorOfObjectToBeDragged' is an element to be dragged
        'locatorOfDragDestinationObject' is an element whose location (i.e., whose center-most pixel) will be the point where locatorOfObjectToBeDragged  is dropped
        """
        self.do_command("dragAndDropToObject", [locatorOfObjectToBeDragged,locatorOfDragDestinationObject,])


    def window_focus(self):
        """
        Gives focus to the currently selected window
        
        """
        self.do_command("windowFocus", [])


    def window_maximize(self):
        """
        Resize currently selected window to take up the entire screen
        
        """
        self.do_command("windowMaximize", [])


    def get_all_window_ids(self):
        """
        Returns the IDs of all windows that the browser knows about.
        
        """
        return self.get_string_array("getAllWindowIds", [])


    def get_all_window_names(self):
        """
        Returns the names of all windows that the browser knows about.
        
        """
        return self.get_string_array("getAllWindowNames", [])


    def get_all_window_titles(self):
        """
        Returns the titles of all windows that the browser knows about.
        
        """
        return self.get_string_array("getAllWindowTitles", [])


    def get_html_source(self):
        """
        Returns the entire HTML source between the opening and
        closing "html" tags.
        
        """
        return self.get_string("getHtmlSource", [])


    def set_cursor_position(self,locator,position):
        """
        Moves the text cursor to the specified position in the given input element or textarea.
        This method will fail if the specified element isn't an input element or textarea.
        
        'locator' is an element locator pointing to an input element or textarea
        'position' is the numerical position of the cursor in the field; position should be 0 to move the position to the beginning of the field.  You can also set the cursor to -1 to move it to the end of the field.
        """
        self.do_command("setCursorPosition", [locator,position,])


    def get_element_index(self,locator):
        """
        Get the relative index of an element to its parent (starting from 0). The comment node and empty text node
        will be ignored.
        
        'locator' is an element locator pointing to an element
        """
        return self.get_number("getElementIndex", [locator,])


    def is_ordered(self,locator1,locator2):
        """
        Check if these two elements have same parent and are ordered siblings in the DOM. Two same elements will
        not be considered ordered.
        
        'locator1' is an element locator pointing to the first element
        'locator2' is an element locator pointing to the second element
        """
        return self.get_boolean("isOrdered", [locator1,locator2,])


    def get_element_position_left(self,locator):
        """
        Retrieves the horizontal position of an element
        
        'locator' is an element locator pointing to an element OR an element itself
        """
        return self.get_number("getElementPositionLeft", [locator,])


    def get_element_position_top(self,locator):
        """
        Retrieves the vertical position of an element
        
        'locator' is an element locator pointing to an element OR an element itself
        """
        return self.get_number("getElementPositionTop", [locator,])


    def get_element_width(self,locator):
        """
        Retrieves the width of an element
        
        'locator' is an element locator pointing to an element
        """
        return self.get_number("getElementWidth", [locator,])


    def get_element_height(self,locator):
        """
        Retrieves the height of an element
        
        'locator' is an element locator pointing to an element
        """
        return self.get_number("getElementHeight", [locator,])


    def get_cursor_position(self,locator):
        """
        Retrieves the text cursor position in the given input element or textarea; beware, this may not work perfectly on all browsers.
        
        
        Specifically, if the cursor/selection has been cleared by JavaScript, this command will tend to
        return the position of the last location of the cursor, even though the cursor is now gone from the page.  This is filed as SEL-243.
        
        This method will fail if the specified element isn't an input element or textarea, or there is no cursor in the element.
        
        'locator' is an element locator pointing to an input element or textarea
        """
        return self.get_number("getCursorPosition", [locator,])


    def get_expression(self,expression):
        """
        Returns the specified expression.
        
        
        This is useful because of JavaScript preprocessing.
        It is used to generate commands like assertExpression and waitForExpression.
        
        
        'expression' is the value to return
        """
        return self.get_string("getExpression", [expression,])


    def get_xpath_count(self,xpath):
        """
        Returns the number of nodes that match the specified xpath, eg. "//table" would give
        the number of tables.
        
        'xpath' is the xpath expression to evaluate. do NOT wrap this expression in a 'count()' function; we will do that for you.
        """
        return self.get_number("getXpathCount", [xpath,])


    def assign_id(self,locator,identifier):
        """
        Temporarily sets the "id" attribute of the specified element, so you can locate it in the future
        using its ID rather than a slow/complicated XPath.  This ID will disappear once the page is
        reloaded.
        
        'locator' is an element locator pointing to an element
        'identifier' is a string to be used as the ID of the specified element
        """
        self.do_command("assignId", [locator,identifier,])


    def allow_native_xpath(self,allow):
        """
        Specifies whether Selenium should use the native in-browser implementation
        of XPath (if any native version is available); if you pass "false" to
        this function, we will always use our pure-JavaScript xpath library.
        Using the pure-JS xpath library can improve the consistency of xpath
        element locators between different browser vendors, but the pure-JS
        version is much slower than the native implementations.
        
        'allow' is boolean, true means we'll prefer to use native XPath; false means we'll only use JS XPath
        """
        self.do_command("allowNativeXpath", [allow,])


    def ignore_attributes_without_value(self,ignore):
        """
        Specifies whether Selenium will ignore xpath attributes that have no
        value, i.e. are the empty string, when using the non-native xpath
        evaluation engine. You'd want to do this for performance reasons in IE.
        However, this could break certain xpaths, for example an xpath that looks
        for an attribute whose value is NOT the empty string.
        
        The hope is that such xpaths are relatively rare, but the user should
        have the option of using them. Note that this only influences xpath
        evaluation when using the ajaxslt engine (i.e. not "javascript-xpath").
        
        'ignore' is boolean, true means we'll ignore attributes without value                        at the expense of xpath "correctness"; false means                        we'll sacrifice speed for correctness.
        """
        self.do_command("ignoreAttributesWithoutValue", [ignore,])


    def wait_for_condition(self,script,timeout):
        """
        Runs the specified JavaScript snippet repeatedly until it evaluates to "true".
        The snippet may have multiple lines, but only the result of the last line
        will be considered.
        
        
        Note that, by default, the snippet will be run in the runner's test window, not in the window
        of your application.  To get the window of your application, you can use
        the JavaScript snippet ``selenium.browserbot.getCurrentWindow()``, and then
        run your JavaScript in there
        
        
        'script' is the JavaScript snippet to run
        'timeout' is a timeout in milliseconds, after which this command will return with an error
        """
        self.do_command("waitForCondition", [script,timeout,])


    def set_timeout(self,timeout):
        """
        Specifies the amount of time that Selenium will wait for actions to complete.
        
        
        Actions that require waiting include "open" and the "waitFor\*" actions.
        
        The default timeout is 30 seconds.
        
        'timeout' is a timeout in milliseconds, after which the action will return with an error
        """
        self.do_command("setTimeout", [timeout,])


    def wait_for_page_to_load(self,timeout):
        """
        Waits for a new page to load.
        
        
        You can use this command instead of the "AndWait" suffixes, "clickAndWait", "selectAndWait", "typeAndWait" etc.
        (which are only available in the JS API).
        
        Selenium constantly keeps track of new pages loading, and sets a "newPageLoaded"
        flag when it first notices a page load.  Running any other Selenium command after
        turns the flag to false.  Hence, if you want to wait for a page to load, you must
        wait immediately after a Selenium command that caused a page-load.
        
        
        'timeout' is a timeout in milliseconds, after which this command will return with an error
        """
        self.do_command("waitForPageToLoad", [timeout,])


    def wait_for_frame_to_load(self,frameAddress,timeout):
        """
        Waits for a new frame to load.
        
        
        Selenium constantly keeps track of new pages and frames loading, 
        and sets a "newPageLoaded" flag when it first notices a page load.
        
        
        See waitForPageToLoad for more information.
        
        'frameAddress' is FrameAddress from the server side
        'timeout' is a timeout in milliseconds, after which this command will return with an error
        """
        self.do_command("waitForFrameToLoad", [frameAddress,timeout,])


    def get_cookie(self):
        """
        Return all cookies of the current page under test.
        
        """
        return self.get_string("getCookie", [])


    def get_cookie_by_name(self,name):
        """
        Returns the value of the cookie with the specified name, or throws an error if the cookie is not present.
        
        'name' is the name of the cookie
        """
        return self.get_string("getCookieByName", [name,])


    def is_cookie_present(self,name):
        """
        Returns true if a cookie with the specified name is present, or false otherwise.
        
        'name' is the name of the cookie
        """
        return self.get_boolean("isCookiePresent", [name,])


    def create_cookie(self,nameValuePair,optionsString):
        """
        Create a new cookie whose path and domain are same with those of current page
        under test, unless you specified a path for this cookie explicitly.
        
        'nameValuePair' is name and value of the cookie in a format "name=value"
        'optionsString' is options for the cookie. Currently supported options include 'path', 'max_age' and 'domain'.      the optionsString's format is "path=/path/, max_age=60, domain=.foo.com". The order of options are irrelevant, the unit      of the value of 'max_age' is second.  Note that specifying a domain that isn't a subset of the current domain will      usually fail.
        """
        self.do_command("createCookie", [nameValuePair,optionsString,])


    def delete_cookie(self,name,optionsString):
        """
        Delete a named cookie with specified path and domain.  Be careful; to delete a cookie, you
        need to delete it using the exact same path and domain that were used to create the cookie.
        If the path is wrong, or the domain is wrong, the cookie simply won't be deleted.  Also
        note that specifying a domain that isn't a subset of the current domain will usually fail.
        
        Since there's no way to discover at runtime the original path and domain of a given cookie,
        we've added an option called 'recurse' to try all sub-domains of the current domain with
        all paths that are a subset of the current path.  Beware; this option can be slow.  In
        big-O notation, it operates in O(n\*m) time, where n is the number of dots in the domain
        name and m is the number of slashes in the path.
        
        'name' is the name of the cookie to be deleted
        'optionsString' is options for the cookie. Currently supported options include 'path', 'domain'      and 'recurse.' The optionsString's format is "path=/path/, domain=.foo.com, recurse=true".      The order of options are irrelevant. Note that specifying a domain that isn't a subset of      the current domain will usually fail.
        """
        self.do_command("deleteCookie", [name,optionsString,])


    def delete_all_visible_cookies(self):
        """
        Calls deleteCookie with recurse=true on all cookies visible to the current page.
        As noted on the documentation for deleteCookie, recurse=true can be much slower
        than simply deleting the cookies using a known domain/path.
        
        """
        self.do_command("deleteAllVisibleCookies", [])


    def set_browser_log_level(self,logLevel):
        """
        Sets the threshold for browser-side logging messages; log messages beneath this threshold will be discarded.
        Valid logLevel strings are: "debug", "info", "warn", "error" or "off".
        To see the browser logs, you need to
        either show the log window in GUI mode, or enable browser-side logging in Selenium RC.
        
        'logLevel' is one of the following: "debug", "info", "warn", "error" or "off"
        """
        self.do_command("setBrowserLogLevel", [logLevel,])


    def run_script(self,script):
        """
        Creates a new "script" tag in the body of the current test window, and 
        adds the specified text into the body of the command.  Scripts run in
        this way can often be debugged more easily than scripts executed using
        Selenium's "getEval" command.  Beware that JS exceptions thrown in these script
        tags aren't managed by Selenium, so you should probably wrap your script
        in try/catch blocks if there is any chance that the script will throw
        an exception.
        
        'script' is the JavaScript snippet to run
        """
        self.do_command("runScript", [script,])


    def add_location_strategy(self,strategyName,functionDefinition):
        """
        Defines a new function for Selenium to locate elements on the page.
        For example,
        if you define the strategy "foo", and someone runs click("foo=blah"), we'll
        run your function, passing you the string "blah", and click on the element 
        that your function
        returns, or throw an "Element not found" error if your function returns null.
        
        We'll pass three arguments to your function:
        
        *   locator: the string the user passed in
        *   inWindow: the currently selected window
        *   inDocument: the currently selected document
        
        
        The function must return null if the element can't be found.
        
        'strategyName' is the name of the strategy to define; this should use only   letters [a-zA-Z] with no spaces or other punctuation.
        'functionDefinition' is a string defining the body of a function in JavaScript.   For example: ``return inDocument.getElementById(locator);``
        """
        self.do_command("addLocationStrategy", [strategyName,functionDefinition,])


    def capture_entire_page_screenshot(self,filename,kwargs):
        """
        Saves the entire contents of the current window canvas to a PNG file.
        Contrast this with the captureScreenshot command, which captures the
        contents of the OS viewport (i.e. whatever is currently being displayed
        on the monitor), and is implemented in the RC only. Currently this only
        works in Firefox when running in chrome mode, and in IE non-HTA using
        the EXPERIMENTAL "Snapsie" utility. The Firefox implementation is mostly
        borrowed from the Screengrab! Firefox extension. Please see
        http://www.screengrab.org and http://snapsie.sourceforge.net/ for
        details.
        
        'filename' is the path to the file to persist the screenshot as. No                  filename extension will be appended by default.                  Directories will not be created if they do not exist,                    and an exception will be thrown, possibly by native                  code.
        'kwargs' is a kwargs string that modifies the way the screenshot                  is captured. Example: "background=#CCFFDD" .                  Currently valid options:                  
        *    background
            the background CSS for the HTML document. This                     may be useful to set for capturing screenshots of                     less-than-ideal layouts, for example where absolute                     positioning causes the calculation of the canvas                     dimension to fail and a black background is exposed                     (possibly obscuring black text).
        
        
        """
        self.do_command("captureEntirePageScreenshot", [filename,kwargs,])


    def rollup(self,rollupName,kwargs):
        """
        Executes a command rollup, which is a series of commands with a unique
        name, and optionally arguments that control the generation of the set of
        commands. If any one of the rolled-up commands fails, the rollup is
        considered to have failed. Rollups may also contain nested rollups.
        
        'rollupName' is the name of the rollup command
        'kwargs' is keyword arguments string that influences how the                    rollup expands into commands
        """
        self.do_command("rollup", [rollupName,kwargs,])


    def add_script(self,scriptContent,scriptTagId):
        """
        Loads script content into a new script tag in the Selenium document. This
        differs from the runScript command in that runScript adds the script tag
        to the document of the AUT, not the Selenium document. The following
        entities in the script content are replaced by the characters they
        represent:
        
            &lt;
            &gt;
            &amp;
        
        The corresponding remove command is removeScript.
        
        'scriptContent' is the Javascript content of the script to add
        'scriptTagId' is (optional) the id of the new script tag. If                       specified, and an element with this id already                       exists, this operation will fail.
        """
        self.do_command("addScript", [scriptContent,scriptTagId,])


    def remove_script(self,scriptTagId):
        """
        Removes a script tag from the Selenium document identified by the given
        id. Does nothing if the referenced tag doesn't exist.
        
        'scriptTagId' is the id of the script element to remove.
        """
        self.do_command("removeScript", [scriptTagId,])


    def use_xpath_library(self,libraryName):
        """
        Allows choice of one of the available libraries.

        'libraryName' is name of the desired library Only the following three can be chosen:
        *   "ajaxslt" - Google's library
        *   "javascript-xpath" - Cybozu Labs' faster library
        *   "default" - The default library.  Currently the default library is "ajaxslt" .

         If libraryName isn't one of these three, then  no change will be made.
        """
        self.do_command("useXpathLibrary", [libraryName,])


    def set_context(self,context):
        """
        Writes a message to the status bar and adds a note to the browser-side
        log.
        
        'context' is the message to be sent to the browser
        """
        self.do_command("setContext", [context,])


    def attach_file(self,fieldLocator,fileLocator):
        """
        Sets a file input (upload) field to the file listed in fileLocator
        
        'fieldLocator' is an element locator
        'fileLocator' is a URL pointing to the specified file. Before the file  can be set in the input field (fieldLocator), Selenium RC may need to transfer the file    to the local machine before attaching the file in a web page form. This is common in selenium  grid configurations where the RC server driving the browser is not the same  machine that started the test.   Supported Browsers: Firefox ("\*chrome") only.
        """
        self.do_command("attachFile", [fieldLocator,fileLocator,])


    def capture_screenshot(self,filename):
        """
        Captures a PNG screenshot to the specified file.
        
        'filename' is the absolute path to the file to be written, e.g. "c:\blah\screenshot.png"
        """
        self.do_command("captureScreenshot", [filename,])


    def capture_screenshot_to_string(self):
        """
        Capture a PNG screenshot.  It then returns the file as a base 64 encoded string.
        
        """
        return self.get_string("captureScreenshotToString", [])

    def captureNetworkTraffic(self, type):
        """
        Returns the network traffic seen by the browser, including headers, AJAX requests, status codes, and timings. When this function is called, the traffic log is cleared, so the returned content is only the traffic seen since the last call.

        'type' is The type of data to return the network traffic as. Valid values are: json, xml, or plain.
        """
        return self.get_string("captureNetworkTraffic", [type,])

    def addCustomRequestHeader(self, key, value):
        """
        Tells the Selenium server to add the specificed key and value as a custom outgoing request header. This only works if the browser is configured to use the built in Selenium proxy.

        'key' the header name.
        'value' the header value.
        """
        return self.do_command("addCustomRequestHeader", [key,value,])

    # PEP8 compat
    capture_network_traffic = captureNetworkTraffic
    add_custom_request_header = addCustomRequestHeader

    def capture_entire_page_screenshot_to_string(self,kwargs):
        """
        Downloads a screenshot of the browser current window canvas to a 
        based 64 encoded PNG file. The \ *entire* windows canvas is captured,
        including parts rendered outside of the current view port.
        
        Currently this only works in Mozilla and when running in chrome mode.
        
        'kwargs' is A kwargs string that modifies the way the screenshot is captured. Example: "background=#CCFFDD". This may be useful to set for capturing screenshots of less-than-ideal layouts, for example where absolute positioning causes the calculation of the canvas dimension to fail and a black background is exposed  (possibly obscuring black text).
        """
        return self.get_string("captureEntirePageScreenshotToString", [kwargs,])


    def shut_down_selenium_server(self):
        """
        Kills the running Selenium Server and all browser sessions.  After you run this command, you will no longer be able to send
        commands to the server; you can't remotely start the server once it has been stopped.  Normally
        you should prefer to run the "stop" command, which terminates the current browser session, rather than 
        shutting down the entire server.
        
        """
        self.do_command("shutDownSeleniumServer", [])


    def retrieve_last_remote_control_logs(self):
        """
        Retrieve the last messages logged on a specific remote control. Useful for error reports, especially
        when running multiple remote controls in a distributed environment. The maximum number of log messages
        that can be retrieve is configured on remote control startup.
        
        """
        return self.get_string("retrieveLastRemoteControlLogs", [])


    def key_down_native(self,keycode):
        """
        Simulates a user pressing a key (without releasing it yet) by sending a native operating system keystroke.
        This function uses the java.awt.Robot class to send a keystroke; this more accurately simulates typing
        a key on the keyboard.  It does not honor settings from the shiftKeyDown, controlKeyDown, altKeyDown and
        metaKeyDown commands, and does not target any particular HTML element.  To send a keystroke to a particular
        element, focus on the element first before running this command.
        
        'keycode' is an integer keycode number corresponding to a java.awt.event.KeyEvent; note that Java keycodes are NOT the same thing as JavaScript keycodes!
        """
        self.do_command("keyDownNative", [keycode,])


    def key_up_native(self,keycode):
        """
        Simulates a user releasing a key by sending a native operating system keystroke.
        This function uses the java.awt.Robot class to send a keystroke; this more accurately simulates typing
        a key on the keyboard.  It does not honor settings from the shiftKeyDown, controlKeyDown, altKeyDown and
        metaKeyDown commands, and does not target any particular HTML element.  To send a keystroke to a particular
        element, focus on the element first before running this command.
        
        'keycode' is an integer keycode number corresponding to a java.awt.event.KeyEvent; note that Java keycodes are NOT the same thing as JavaScript keycodes!
        """
        self.do_command("keyUpNative", [keycode,])


    def key_press_native(self,keycode):
        """
        Simulates a user pressing and releasing a key by sending a native operating system keystroke.
        This function uses the java.awt.Robot class to send a keystroke; this more accurately simulates typing
        a key on the keyboard.  It does not honor settings from the shiftKeyDown, controlKeyDown, altKeyDown and
        metaKeyDown commands, and does not target any particular HTML element.  To send a keystroke to a particular
        element, focus on the element first before running this command.
        
        'keycode' is an integer keycode number corresponding to a java.awt.event.KeyEvent; note that Java keycodes are NOT the same thing as JavaScript keycodes!
        """
        self.do_command("keyPressNative", [keycode,])
        
    def wait_for_element_present(self,locator):
        self.do_command("waitForElementPresent", [locator,])



########NEW FILE########
__FILENAME__ = testrunner
import os
import sys

import nose
from nose.config import Config, all_config_files
from nose.plugins.manager import DefaultPluginManager

from django.core.management.base import BaseCommand
try:
    from django.test.simple import DjangoTestSuiteRunner
except ImportError:
    from djangosanetesting.runnercompat import DjangoTestSuiteRunner

from djangosanetesting.noseplugins import (
    DjangoPlugin,
    DjangoLiveServerPlugin, SeleniumPlugin, CherryPyLiveServerPlugin,
    DjangoTranslationPlugin,
    ResultPlugin,
)

__all__ = ("DstNoseTestSuiteRunner",)

# This file doen't contain tests
__test__ = False

"""
Act as Django test runner, but use nose. Enable common django-sane-testing
plugins by default.

You can use

    DST_NOSE_ARGS = ['list', 'of', 'args']

in settings.py for arguments that you always want passed to nose.

Test runners themselves are basically copypasted from django-nose project.
(C) Jeff Balogh and contributors, released under BSD license.

Thanks and kudos.

Modified for django-sane-testing by Almad.
"""

def activate_plugin(plugin, argv=None):
    argv = argv or sys.argv
    if plugin.activation_parameter not in argv:
        argv.append(plugin.activation_parameter)

try:
    any
except NameError:
    def any(iterable):
        for element in iterable:
            if element:
                return True
        return False

OPTION_TRANSLATION = {'--failfast': '-x'}

class DstNoseTestSuiteRunner(DjangoTestSuiteRunner):

    def run_suite(self, nose_argv=None):
        """Test runner that invokes nose."""
        # Prepare django for testing.
        from django.conf import settings
    
        from django.test import utils
        utils.setup_test_environment()
    
        result_plugin = ResultPlugin()
        plugins = [DjangoPlugin(), SeleniumPlugin(), DjangoTranslationPlugin(), result_plugin]
        
        if getattr(settings, 'CHERRYPY_TEST_SERVER', False):
            plugins.append(CherryPyLiveServerPlugin())
        else:
            plugins.append(DjangoLiveServerPlugin())
        
        # Do not pretend it's a production environment.
        # settings.DEBUG = False
    
        # We pass nose a list of arguments that looks like sys.argv, but customize
        # to avoid unknown django arguments.

        for plugin in _get_plugins_from_settings():
            plugins_to_add.append(plugin)
        # activate all required plugins
        activate_plugin(DjangoPlugin, nose_argv)
        activate_plugin(SeleniumPlugin, nose_argv)
        activate_plugin(DjangoTranslationPlugin, nose_argv)
    #    activate_plugin(ResultPlugin, nose_argv)
    
        if getattr(settings, 'CHERRYPY_TEST_SERVER', False):
            activate_plugin(CherryPyLiveServerPlugin, nose_argv)
        else:
            activate_plugin(DjangoLiveServerPlugin, nose_argv)
    
        # Skip over 'manage.py test' and any arguments handled by django.
        django_opts = ['--noinput']
        for opt in BaseCommand.option_list:
            django_opts.extend(opt._long_opts)
            django_opts.extend(opt._short_opts)
    
        nose_argv.extend(OPTION_TRANSLATION.get(opt, opt)
                         for opt in sys.argv[1:]
                         if opt.startswith('-') and not any(opt.startswith(d) for d in django_opts))
    
        if self.verbosity >= 2:
            print ' '.join(nose_argv)
    
        test_program = nose.core.TestProgram(argv=nose_argv, exit=False,
                                                    addplugins=plugins)
        
        # FIXME: ResultPlugin is working not exactly as advertised in django-nose
        # multiple instance problem, find workaround
    #    result = result_plugin.result
    #    return len(result.failures) + len(result.errors)
        return not test_program.success

    def run_tests(self, test_labels, extra_tests=None):
        """
        Run the unit tests for all the test names in the provided list.

        Test names specified may be file or module names, and may optionally
        indicate the test case to run by separating the module or file name
        from the test case name with a colon. Filenames may be relative or
        absolute.  Examples:

        runner.run_tests('test.module')
        runner.run_tests('another.test:TestCase.test_method')
        runner.run_tests('a.test:TestCase')
        runner.run_tests('/path/to/test/file.py:test_function')

        Returns the number of tests that failed.
        """
        
        from django.conf import settings
        
        nose_argv = ['nosetests', '--verbosity', str(self.verbosity)] + list(test_labels)
        if hasattr(settings, 'NOSE_ARGS'):
            nose_argv.extend(settings.NOSE_ARGS)

        # Skip over 'manage.py test' and any arguments handled by django.
        django_opts = ['--noinput']
        for opt in BaseCommand.option_list:
            django_opts.extend(opt._long_opts)
            django_opts.extend(opt._short_opts)

        nose_argv.extend(OPTION_TRANSLATION.get(opt, opt)
                         for opt in sys.argv[1:]
                         if opt.startswith('-') and not any(opt.startswith(d) for d in django_opts))

        if self.verbosity >= 2:
            print ' '.join(nose_argv)

        result = self.run_suite(nose_argv)
        ### FIXME
        class SimpleResult(object): pass
        res = SimpleResult()
        res.failures = ['1'] if result else []
        res.errors = []
        # suite_result expects the suite as the first argument.  Fake it.
        return self.suite_result({}, res)


def _get_options():
    """Return all nose options that don't conflict with django options."""
    cfg_files = nose.core.all_config_files()
    manager = nose.core.DefaultPluginManager()
    config = nose.core.Config(env=os.environ, files=cfg_files, plugins=manager)
    options = config.getParser().option_list
    django_opts = [opt.dest for opt in BaseCommand.option_list] + ['version']
    return tuple(o for o in options if o.dest not in django_opts and
                                       o.action != 'help')

def _get_plugins_from_settings():
    from django.conf import settings
    if hasattr(settings, 'NOSE_PLUGINS'):
        for plg_path in settings.NOSE_PLUGINS:
            try:
                dot = plg_path.rindex('.')
            except ValueError:
                raise exceptions.ImproperlyConfigured(
                                    '%s isn\'t a Nose plugin module' % plg_path)
            p_mod, p_classname = plg_path[:dot], plg_path[dot+1:]
            try:
                mod = import_module(p_mod)
            except ImportError, e:
                raise exceptions.ImproperlyConfigured(
                        'Error importing Nose plugin module %s: "%s"' % (p_mod, e))
            try:
                p_class = getattr(mod, p_classname)
            except AttributeError:
                raise exceptions.ImproperlyConfigured(
                        'Nose plugin module "%s" does not define a "%s" class' % (
                                                                p_mod, p_classname))
            yield p_class()

# Replace the builtin command options with the merged django/nose options.
DstNoseTestSuiteRunner.options = _get_options()
DstNoseTestSuiteRunner.__test__ = False

def run_tests(test_labels, verbosity=1, interactive=True, failfast=False, extra_tests=None):
    test_runner = DstNoseTestSuiteRunner(verbosity=verbosity, interactive=interactive, failfast=failfast)
    return test_runner.run_tests(test_labels, extra_tests=extra_tests)

########NEW FILE########
__FILENAME__ = utils
import os
from functools import wraps
import urllib2

from django.core.servers.basehttp import AdminMediaHandler
from django.core.handlers.wsgi import WSGIHandler

DEFAULT_LIVE_SERVER_PROTOCOL = "http"
DEFAULT_LIVE_SERVER_PORT = 8000
DEFAULT_LIVE_SERVER_ADDRESS = '0.0.0.0'
DEFAULT_URL_ROOT_SERVER_ADDRESS = 'localhost'


def extract_django_traceback(twill=None, http_error=None, lines=None):
    record = False
    traceback = ''

    if not lines and http_error:
        lines = http_error.readlines()
    elif twill:
        http_error = urllib2.HTTPError(url=twill.get_url(), code=500, msg=None, hdrs=None, fp=None)
        if not lines:
            lines = twill.result.get_page().split("\n")
    
    lines = lines or []

    for one in lines:
        if one.strip().startswith('<textarea ') and one.find('id="traceback_area"'):
            record = True
            continue
        if record and one.strip() == '</textarea>':
            break
        elif record:
            traceback += one.rstrip() + "\n"

    if record:
        http_error.msg = traceback
    else:
        http_error.msg = "500 Server error, traceback not found"

    return http_error

def is_test_database():
    """
    Return whether we're using test database. Can be used to determine if we're
    running tests.
    """
    from django.conf import settings

    # This is hacky, but fact we're running tests is determined by _create_test_db call.
    # We'll assume usage of it if assigned to settings.DATABASE_NAME

    if settings.TEST_DATABASE_NAME:
        test_database_name = settings.TEST_DATABASE_NAME
    else:
        from django.db import TEST_DATABASE_PREFIX
        test_database_name = TEST_DATABASE_PREFIX + settings.DATABASE_NAME

    return settings.DATABASE_NAME == test_database_name


def get_databases():
    try:
        from django.db import connections
    except ImportError:
        from django.conf import settings
        from django.db import connection

        if settings.TEST_DATABASE_NAME:
            connection['TEST_NAME'] = settings.TEST_DATABASE_NAME

        connections = {
            DEFAULT_DB_ALIAS : connection
        }

    return connections


def test_databases_exist():
    from django.db import DatabaseError

    connections = get_databases()
    try:
        for connection in connections:
            if connection.settings_dict['NAME'] == 'sqlite3':
                if not os.path.exists(connection.settings_dict['DATABASE_NAME']):
                    raise DatabaseError()
            connection.cursor()

        return True
    except DatabaseError, err:
        return False

def get_live_server_path():
    from django.conf import settings

    return getattr(settings, "URL_ROOT", "%s://%s:%s/" % (
        getattr(settings, "LIVE_SERVER_PROTOCOL", DEFAULT_LIVE_SERVER_PROTOCOL),
        getattr(settings, "URL_ROOT_SERVER_ADDRESS", DEFAULT_URL_ROOT_SERVER_ADDRESS),
        getattr(settings, "LIVE_SERVER_PORT", DEFAULT_LIVE_SERVER_PORT)
    ))

def twill_patched_go(browser, original_go):
    """
    If call is not beginning with http, prepent it with get_live_server_path
    to allow relative calls
    """
    def twill_go_with_relative_paths(uri, *args, **kwargs):
        if not uri.startswith("http"):
            base = get_live_server_path()
            if uri.startswith("/"):
                base = base.rstrip("/")
            uri = "%s%s" % (base, uri)
        response = original_go(uri, *args, **kwargs)
        if browser.result.get_http_code() == 500:
            raise extract_django_traceback(twill=browser)
        else:
            return response
    return twill_go_with_relative_paths

def twill_xpath_go(browser, original_go):
    """
    If call is not beginning with http, prepent it with get_live_server_path
    to allow relative calls
    """

    from lxml.etree import XPathEvalError
    from lxml.html import document_fromstring

    from twill.errors import TwillException


    def visit_with_xpath(xpath):
        tree = document_fromstring(browser.get_html())

        try:
            result = tree.xpath(xpath)
        except XPathEvalError:
            raise TwillException("Bad xpath" % xpath)

        if len(result) == 0:
            raise TwillException("No match")
        elif len(result) > 1:
            raise TwillException("xpath returned multiple hits! Cannot visit.")

        if not result[0].get("href"):
            raise TwillException("xpath match do not have 'href' attribute")

        response = original_go(result[0].get("href"))
        if browser.result.get_http_code() == 500:
            raise extract_django_traceback(twill=browser)
        else:
            return response
    return visit_with_xpath

def mock_settings(settings_attribute, value):
    from django.conf import settings
    
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not hasattr(settings, settings_attribute):
                delete = True
            else:
                delete = False
                original_value = getattr(settings, settings_attribute)

            setattr(settings, settings_attribute, value)

            try:
                retval = f(*args, **kwargs)
            finally:
                if delete:
                    # could not delete directly as LazyObject does not implement
                    # __delattr__ properly
                    if settings._wrapped:
                        delattr(settings._wrapped, settings_attribute)
                else:
                    setattr(settings, settings_attribute, original_value)

            return retval
        return wrapped
    return wrapper


def get_server_handler():
    handler = AdminMediaHandler(WSGIHandler())
    try:
        from django.contrib.staticfiles.handlers import StaticFilesHandler
        handler = StaticFilesHandler(handler)
    except:
        pass

    return handler



########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Django: Sane Testing documentation build configuration file, created by
# sphinx-quickstart on Mon Jan 26 12:07:29 2009.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Django: Sane Testing'
copyright = u'2011, Almad'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.5'
# The full version, including alpha/beta/rc tags.
release = '0.5.11'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['.build']

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


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

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
html_static_path = ['.static']

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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'DjangoSaneTestingdoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'DjangoSaneTesting.tex', ur'Django: Sane Testing Documentation',
   ur'Almad', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = pavement
#!/usr/bin/env python2

from paver.easy import *
from paver.setuputils import setup

VERSION = '0.5.11'
name = 'djangosanetesting'

setup(
    name = name,
    version = VERSION,
    url = 'http://devel.almad.net/trac/django-sane-testing/',
    author = 'Lukas Linhart',
    author_email = 'bugs@almad.net',
    description = 'Integrate Django with nose, Selenium, Twill and more. ''',
    long_description = u'''
======================
Django: Sane testing
======================

django-sane-testing integrates Django with Nose testing framework. Goal is to provide nose goodies to Django testing and to support feasible integration or functional testing of Django applications, for example by providing more control over transaction/database handling.

Thus, there is a way to start HTTP server for non-WSGI testing - like using Selenium or Windmill.

Selenium has also been made super easy - just start --with-selenium, inherit from SeleniumTestCase and use self.selenium.

Package is documented - see docs/ or http://readthedocs.org/projects/Almad/django-sane-testing/docs/index.html .
''',
    packages = ['djangosanetesting', 'djangosanetesting.selenium'],
    requires = ['Django (>=1.1)', 'nose (>=0.10)'],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    entry_points = {
        'nose.plugins.0.10': [
            'djangoliveserver = %s.noseplugins:DjangoLiveServerPlugin' % name,
            'cherrypyliveserver = %s.noseplugins:CherryPyLiveServerPlugin' % name,
            'django = %s.noseplugins:DjangoPlugin' % name,
            'selenium = %s.noseplugins:SeleniumPlugin' % name,
            'sanetestselection = %s.noseplugins:SaneTestSelectionPlugin' % name,
            'djangotranslations = %s.noseplugins:DjangoTranslationPlugin' % name,
	    'djangoresultplugin = %s.noseplugins:ResultPlugin' % name,
        ]
    }
)

options(
    sphinx=Bunch(
        builddir="build",
        sourcedir="source"
    ),
    virtualenv=Bunch(
        packages_to_install=["nose", "Django>=1.1"],
        install_paver=False,
        script_name='bootstrap.py',
        paver_command_line=None,
        dest_dir="virtualenv"
    ),
)

@task
@consume_args
def unit(args, nose_run_kwargs=None):
    """ Run unittests """
    import os, sys
    from os.path import join, dirname, abspath
    
    test_project_module = "testproject"
    
    sys.path.insert(0, abspath(join(dirname(__file__), test_project_module)))
    sys.path.insert(0, abspath(dirname(__file__)))
    
    os.environ['DJANGO_SETTINGS_MODULE'] = "%s.settings" % test_project_module
    
    import nose

    os.chdir(test_project_module)

    argv = ["--with-django", "--with-cherrypyliveserver", "--with-selenium", '--with-djangotranslations'] + args

    nose_run_kwargs = nose_run_kwargs or {}

    nose.run_exit(
        argv = ["nosetests"] + argv,
        defaultTest = test_project_module,
        **nose_run_kwargs
    )

@task
@consume_args
@needs('unit')
def test(args):
    pass

########NEW FILE########
__FILENAME__ = config.example

WINDMILL_BROWSER = 'firefox'

### Django settings


DEBUG = True
TEMPLATE_DEBUG = DEBUG


ADMINS = (
     # ('Almad', 'bugs at almad.net'),
)

URL_ROOT="http://localhost:8000/"

SITE_ID =1

MANAGERS = ADMINS

DATABASES = {
    'default' : {
        'ENGINE' : 'django.db.backends.sqlite3',
        'NAME' : "/tmp/dst.db",
        'TEST_NAME' : "/tmp/test_dst.db",
    },
    'users' : {
        'ENGINE' : 'django.db.backends.sqlite3',
        'NAME' : "/tmp/udst.db",
        'TEST_NAME' : "/tmp/test_udst.db",
    },
}

TIME_ZONE = 'Europe/Prague'

LANGUAGE_CODE = 'cs'
FILE_CHARSET = 'utf-8'
DEFAULT_CHARSET = 'utf-8'

USE_I18N = True

MEDIA_ROOT = "/home/almad/project/libkeykeeper/keykeeper/media/"
MEDIA_URL = "/media/"

ADMIN_MEDIA_PREFIX = "/adminmedia/"
SECRET_KEY = 'qjgj741513+cjj9lb+46&f3gyvh@0jgou-rx-tqbziw6f$bt59xxx!'

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

# insert parent directory on first place of sys.path, so it's prefferred over installed version
import sys, os, os.path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))


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
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-

from os import path

working_dir = path.dirname(path.abspath(__file__))

APPLICATION_ROOT=path.join(path.dirname(path.abspath(__file__)))

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
    'django.template.loaders.eggs.load_template_source',
)

# AUTHENTICATION_BACKENDS = ('keykeeper.libopenid.OpenidBackend',)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
#    'django.contrib.sessions.middleware.SessionMiddleware',
#    'django.contrib.auth.middleware.AuthenticationMiddleware',
#    'django.middleware.transaction.TransactionMiddleware',
#    'django.middleware.http.SetRemoteAddrFromForwardedFor',
)

ROOT_URLCONF = 'testproject.urls'

SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_NAME = 'testproject_id'

TEMPLATE_DIRS = (
    path.join(APPLICATION_ROOT, 'template/')
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.auth",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'testapp',
)

TEST_RUNNER='djangosanetesting.testrunner.DstNoseTestSuiteRunner'

TEST_DATABASE_CHARSET="utf8"

CHERRYPY_TEST_SERVER = True

LANGUAGE_CODE = 'cs'

CACHE_BACKEND = 'locmem://'

DST_FLUSH_DJANGO_CACHE = True
NONSENSICAL_SETTING_ATTRIBUTE_FOR_MOCK_TESTING = "owned"

SITE_ID=1

from config import *


########NEW FILE########
__FILENAME__ = test_database
import urllib2

from djangosanetesting.cases import DatabaseTestCase, DestructiveDatabaseTestCase, HttpTestCase
from djangosanetesting.utils import mock_settings

from testapp.models import ExampleModel

import django

class TestDjangoOneTwoMultipleDatabases(DestructiveDatabaseTestCase):
    """
    Test we're flushing multiple databases
    i.e. that all databases are flushed between tests

    We rely on fact that cases are invoked after each other, which is bad :-]

    This is antipattern and should not be used, but it's hard to test
    framework from within :-] Better solution would be greatly appreciated.
    """
    multi_db = True

    def setUp(self):
        super(TestDjangoOneTwoMultipleDatabases, self).setUp()

        if django.VERSION[0] < 1 or (django.VERSION[0] == 1 and django.VERSION[1] < 2):
            raise self.SkipTest("This case is only for Django 1.2+")

    def test_aaa_multiple_databases_flushed(self):
        self.assert_equals(0, ExampleModel.objects.count())
        self.assert_equals(0, ExampleModel.objects.using('users').count())

        ExampleModel.objects.create(name="test1")
        ExampleModel.objects.using('users').create(name="test1")

        self.transaction.commit()
        self.transaction.commit(using='users')

        self.assert_equals(1, ExampleModel.objects.count())
        self.assert_equals(1, ExampleModel.objects.using('users').count())

    def test_bbb_multiple_databases_flushed(self):
        self.assert_equals(0, ExampleModel.objects.count())
        self.assert_equals(0, ExampleModel.objects.using('users').count())

        ExampleModel.objects.create(name="test1")
        ExampleModel.objects.using('users').create(name="test1")

        self.transaction.commit()
        self.transaction.commit(using='users')

        self.assert_equals(1, ExampleModel.objects.count())
        self.assert_equals(1, ExampleModel.objects.using('users').count())

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy as _

class ExampleModel(models.Model):
    name = models.CharField(max_length=50)

    @staticmethod
    def get_translated_string():
        return _(u"Translatable string")

    def __unicode__(self):
        return u"ExampleModel %s" % self.name
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from views import *

urlpatterns = patterns('',
    (r'^testtwohundred/$', twohundred),
    (r'^assert_two_example_models/$', assert_two_example_models),
    (r'^return_not_authorized/$', return_not_authorized),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse
from testapp.models import ExampleModel

def twohundred(request):
    return HttpResponse(content='200 OK')

########NEW FILE########
__FILENAME__ = config.example

WINDMILL_BROWSER = 'firefox'

### Django settings


DEBUG = True
TEMPLATE_DEBUG = DEBUG


ADMINS = (
     # ('Almad', 'bugs at almad.net'),
)

URL_ROOT="http://localhost:8000/"

SITE_ID =1

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'NAME': 'main',
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME' : '/tmp/test_dst_main.db'
    },
    'users': {
        'NAME': 'user',
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME' : '/tmp/test_dst_user.db'
    }
}

#DATABASE_OPTIONS = {"init_command": "SET storage_engine=INNODB" } 


TIME_ZONE = 'Europe/Prague'

LANGUAGE_CODE = 'cs'
FILE_CHARSET = 'utf-8'
DEFAULT_CHARSET = 'utf-8'

USE_I18N = True

MEDIA_ROOT = "/home/almad/project/libkeykeeper/keykeeper/media/"
MEDIA_URL = "/media/"

ADMIN_MEDIA_PREFIX = "/adminmedia/"
SECRET_KEY = 'qjgj741513+cjj9lb+46&f3gyvh@0jgou-rx-tqbziw6f$bt59xxx!'

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python2

# insert parent directory on first place of sys.path, so it's prefferred over installed version
import sys, os, os.path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))


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
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-

from os import path

working_dir = path.dirname(path.abspath(__file__))

APPLICATION_ROOT=path.join(path.dirname(path.abspath(__file__)))

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
    'django.template.loaders.eggs.load_template_source',
)

# AUTHENTICATION_BACKENDS = ('keykeeper.libopenid.OpenidBackend',)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
#    'django.contrib.sessions.middleware.SessionMiddleware',
#    'django.contrib.auth.middleware.AuthenticationMiddleware',
#    'django.middleware.transaction.TransactionMiddleware',
#    'django.middleware.http.SetRemoteAddrFromForwardedFor',
)

ROOT_URLCONF = 'testproject.urls'

SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_NAME = 'testproject_id'

TEMPLATE_DIRS = (
    path.join(APPLICATION_ROOT, 'template/')
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.auth",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'testapp',
    
    'djangosanetesting',
)

TEST_RUNNER='djangosanetesting.testrunner.DstNoseTestSuiteRunner'

TEST_DATABASE_CHARSET="utf8"

CHERRYPY_TEST_SERVER = True

LANGUAGE_CODE = 'cs'

CACHE_BACKEND = 'locmem://'

DST_FLUSH_DJANGO_CACHE = True
NONSENSICAL_SETTING_ATTRIBUTE_FOR_MOCK_TESTING = "owned"

DEBUG = True

SITE_ID=1

from config import *


########NEW FILE########
__FILENAME__ = test_database
import urllib2

from djangosanetesting.cases import DatabaseTestCase, DestructiveDatabaseTestCase, HttpTestCase
from djangosanetesting.utils import mock_settings, get_live_server_path

from testapp.models import ExampleModel

import django

class TestDatabaseRollbackCase(DatabaseTestCase):
    """
    Check we got proper rollback when trying to play with models.
    """
    def test_inserting_two(self):
        # guard assertion
        self.assert_equals(0, len(ExampleModel.objects.all()))
        ExampleModel.objects.create(name="test1")
        ExampleModel.objects.create(name="test2")

        # check we got stored properly
        self.assert_equals(2, len(ExampleModel.objects.all()))

    def test_inserting_two_again(self):
        # guard assertion, will fail if previous not rolled back properly
        self.assert_equals(0, len(ExampleModel.objects.all()))

        ExampleModel.objects.create(name="test3")
        ExampleModel.objects.create(name="test4")

        # check we got stored properly
        self.assert_equals(2, len(ExampleModel.objects.all()))
    
    def test_client_available(self):
        res = self.client.get('/testtwohundred/')
        self.assert_equals(200, res.status_code)

class TestProperClashing(DatabaseTestCase):
    """
    Test we're getting expected failures when working with db,
    i.e. that database is not purged between tests, only rolled back.
    We rely that test suite executed methods in this order:
      (1) test_aaa_commit_object
      (2) test_bbb_object_present
      (3) test_ccc_object_still_present
      
    This is antipattern and should not be used, but it's hard to test
    framework from within ;) Better solution would be greatly appreciated.  
    """
    
    def test_aaa_commit_object(self):
        ExampleModel.objects.create(name="test1")
        self.transaction.commit()

    def test_bbb_object_present(self):
        self.assert_equals(1, len(ExampleModel.objects.all()))

    def test_ccc_object_still_present(self):
        self.assert_equals(1, len(ExampleModel.objects.all()))
        ExampleModel.objects.all()[0].delete()
        self.transaction.commit()


class TestFixturesLoadedProperly(HttpTestCase):
    fixtures = ["random_model_for_testing"]

    def test_model_loaded(self):
        self.assert_equals(2, len(ExampleModel.objects.all()))

    def test_available_in_another_thread(self):
        self.assertEquals(u'OKidoki', self.urlopen('%sassert_two_example_models/' % get_live_server_path()).read())

class TestDjangoOneTwoMultipleDatabases(DestructiveDatabaseTestCase):
    """
    Test we're flushing multiple databases
    i.e. that all databases are flushed between tests

    We rely on fact that cases are invoked after each other, which is bad :-]

    This is antipattern and should not be used, but it's hard to test
    framework from within :-] Better solution would be greatly appreciated.
    """
    def setUp(self):
        super(TestDjangoOneTwoMultipleDatabases, self).setUp()

        if django.VERSION[0] < 1 or (django.VERSION[0] == 1 and django.VERSION[1] < 2):
            raise self.SkipTest("This case is only for Django 1.2+")

    @mock_settings("DATABASE_HOST", None)
    @mock_settings("DATABASES", {


    })
    def test_multiple_databases_flushed(self):
        pass

########NEW FILE########
__FILENAME__ = test_database_fixture_handling
"""
Test that DatabaseTestCases has properly handled fixtures,
i.e. database is flushed when fixtures are different.

This would normally be usual TestCase, but we need to check
inter-case behaviour, so we rely that those cases are executed
one after another.

This is kinda antipattern, mail me for better solution ;)

Covers #6
"""
from djangosanetesting.cases import DatabaseTestCase
from testapp.models import ExampleModel

class TestAAAFirstfixture(DatabaseTestCase):
    fixtures = ['random_model_for_testing']
    def test_fixture_loaded(self):
        self.assert_equals(ExampleModel, ExampleModel.objects.get(pk=1).__class__)
        self.assert_equals(ExampleModel, ExampleModel.objects.get(pk=2).__class__)
    
class TestBBBSecondFixture(DatabaseTestCase):
    fixtures = ['duplicate_model_for_testing']
    def test_fixture_loaded(self):
        self.assert_equals(ExampleModel, ExampleModel.objects.get(pk=3).__class__)
        self.assert_equals(ExampleModel, ExampleModel.objects.get(pk=4).__class__)
   
    def test_aaa_fixture_not_loaded(self):
        self.assert_raises(ExampleModel.DoesNotExist, lambda:ExampleModel.objects.get(pk=1))
        self.assert_raises(ExampleModel.DoesNotExist, lambda:ExampleModel.objects.get(pk=2))    


########NEW FILE########
__FILENAME__ = test_liveserver
# -*- coding: utf-8 -*-
from StringIO import StringIO
import urllib2

from djangosanetesting.cases import HttpTestCase, SeleniumTestCase
from djangosanetesting.utils import get_live_server_path

from testapp.models import ExampleModel

class TestLiveServerRunning(HttpTestCase):
    
    def get_ok(self):
        self.assertEquals(u'OKidoki', self.urlopen('%stesttwohundred/' % get_live_server_path()).read())

    def test_http_retrievable(self):
        return self.get_ok()
    
    def test_http_retrievable_repeatedly(self):
        return self.get_ok()
    
    def test_client_available(self):
        res = self.client.get('/testtwohundred/')
        self.assert_equals(200, res.status_code)
    
    def test_not_authorized_not_resetable(self):
        # This is lame, but condition is non-deterministic and reveals itself
        # when repeating request often...
        for i in xrange(1, 10):
            try:
                response = self.urlopen(url='%sreturn_not_authorized/' % get_live_server_path(), data='data')
                #response = opener.open(request)
            except urllib2.HTTPError, err:
                self.assert_equals(401, err.code)
            else:
                assert False, "401 expected"

    def test_server_error(self):
        try:
            self.urlopen(url='%sreturn_server_error/' % get_live_server_path())
        except urllib2.HTTPError, err:
            self.assert_equals(500, err.code)
            self.assert_equals("500 Server error, traceback not found", err.msg)
        else:
            assert False, "500 expected"

    def test_django_error_traceback(self):
        try:
            self.urlopen(url='%sreturn_django_error/' % get_live_server_path())
        except urllib2.HTTPError, err:
            self.assert_equals(500, err.code)
            self.assert_not_equals("500 Server error, traceback not found", err.msg)
        else:
            assert False, "500 expected"

class TestSelenium(SeleniumTestCase):
    translation_language_code = 'cs'

    def setUp(self):
        super(TestSelenium, self).setUp()
        from django.utils import translation
        translation.activate("cs")

    def test_ok(self):
        self.selenium.open("/testtwohundred/")
        self.assert_true(self.selenium.is_text_present("OKidoki"))

    def test_czech_string_acquired_even_with_selenium(self):
        self.assert_equals(u"Přeložitelný řetězec", unicode(ExampleModel.get_translated_string()))

# non-deterministic functionality, moved out
# might be ressurected with Selenium2

#    def test_selenium_server_error(self):
#        try:
#            self.selenium.open('/return_django_error/')
#        except Exception, err:
#            self.assert_not_equals("500 Server error, traceback not found", err.msg)
#        else:
#            self.fail("500 expected")
#
#    def test_selenium_django_error_traceback(self):
#        try:
#            self.selenium.open('/return_server_error/')
#        except Exception, err:
#            self.assert_equals("500 Server error, traceback not found", err.msg)
#        else:
#            self.fail("500 expected")


class TestTwill(HttpTestCase):

    def test_ok_retrieved(self):
        self.twill.go("%stesttwohundred/" % get_live_server_path())
        self.assert_equals(200, self.twill.get_code())

    def test_live_server_added_when_missing(self):
        self.twill.go("/testtwohundred/")
        self.assert_equals(200, self.twill.get_code())

    def test_missing_recognized(self):
        self.twill.go("/this/should/never/exist/")
        self.assert_equals(404, self.twill.get_code())

    def test_twill_server_error(self):
        try:
            self.twill.go('/return_django_error/')
        except urllib2.HTTPError, err:
            self.assert_equals(500, err.code)
            self.assert_not_equals("500 Server error, traceback not found", err.msg)
        else:
            self.fail("500 expected")

    def test_twill_django_error_traceback(self):
        try:
            self.twill.go('/return_server_error/')
        except urllib2.HTTPError, err:
            self.assert_equals(500, err.code)
            self.assert_equals("500 Server error, traceback not found", err.msg)
        else:
            self.fail("500 expected")

class TestSpynner(HttpTestCase):
    def test_ok_loaded(self):
        self.assert_true(True, self.spynner.load("%stesttwohundred/" % get_live_server_path()))

    def test_ok_prage_loaded(self):
        from lxml import etree
        self.spynner.load("%stesttwohundred/" % get_live_server_path())
        self.assert_equals('OKidoki', etree.parse(StringIO(self.spynner.html)).xpath("//body")[0].text)

########NEW FILE########
__FILENAME__ = test_templatetag
from djangosanetesting.cases import TemplateTagTestCase

class TestTagLib(TemplateTagTestCase):
    preload = ('dsttesttags',)

    def test_tag_error(self):
        self.assert_raises(self.TemplateSyntaxError, self.render_template,
                           '{% table %}')

    def test_tag_output(self):
        self.assert_equal(self.render_template('{% table x_y z %}'),
            u'<table><tr><td>x</td><td>y</td></tr><tr><td>z</td></tr></table>')

class TestFilterLib(TemplateTagTestCase):
    preload = ('dsttestfilters',)

    def test_filter_output(self):
        self.assert_equal(self.render_template('{{ a|ihatebs }}', a='abc'),
                         u'aac')

class TestBoth(TestTagLib, TestFilterLib):
    preload = ('dsttesttags', 'dsttestfilters')

    def _call_test_render(self):
        return self.render_template('{% table b %}{{ a|ihatebs }}',
                                     a='a_bb_d b')

    def test_both_output(self):
        self.assert_equal(self._call_test_render(), u'<table><tr><td>b</td></tr>'
                         '</table>a_aa_d a')

    def test_preload_none(self):
        self.preload = ()
        self.assert_raises(self.TemplateSyntaxError, self._call_test_render)

    def test_preload_tags_only(self):
        self.preload = ('dsttesttags',)
        self.assert_raises(self.TemplateSyntaxError, self._call_test_render)

    def test_preload_filters_only(self):
        self.preload = ('dsttestfilters',)
        self.assert_raises(self.TemplateSyntaxError, self._call_test_render)

class TestMisc(TemplateTagTestCase):
    def test_context(self):
        self.assert_equal(self.render_template('{{ cvar }}'), u'')
        self.assert_equal(self.render_template('{{ cvar }}', cvar=123), u'123')

    def test_nonexistent_taglib(self):
        self.preload = ('nonexistent',)
        self.assert_raises(self.TemplateSyntaxError, self.render_template,
                           'sthing')

########NEW FILE########
__FILENAME__ = test_unit
# -*- coding: utf-8 -*-
from djangosanetesting.cases import UnitTestCase
from djangosanetesting.utils import mock_settings

from django.core.cache import cache
from django.conf import settings

from testapp.models import ExampleModel

class TestUnitSimpleMetods(UnitTestCase):
    def test_true(self):
        self.assert_true(True)
    
    def test_true_false(self):
        self.assert_raises(AssertionError, lambda:self.assert_true(False))
    
    def raise_value_error(self):
        # lambda cannot do it, fix Python
        raise ValueError()
    
    def test_raises(self):
        self.assert_true(True, self.assert_raises(ValueError, lambda:self.raise_value_error()))
    
    def test_raises_raise_assertion(self):
        self.assert_raises(AssertionError, lambda: self.assert_raises(ValueError, lambda: "a"))
    
    def test_equals(self):
        self.assert_equals(1, 1)

    def test_equals_false(self):
        self.assert_raises(AssertionError, lambda:self.assert_equals(1, 2))

    def test_fail(self):
        try:
            self.fail()
        except AssertionError:
            pass
        else:
            raise AssertionError("self.fail should raise AssertionError")
    
    def test_new_unittest_methods_imported(self):
        try:
            import unittest2
        except ImportError:
            import sys
            if sys.version_info[0] == 2 and sys.version_info[1] < 7:
                raise self.SkipTest("Special assert functions not available")

        self.assert_in(1, [1])

    
class TestUnitAliases(UnitTestCase):
    
    def get_camel(self, name):
        """ Transform under_score_names to underScoreNames """
        if name.startswith("_") or name.endswith("_"):
            raise ValueError(u"Cannot ransform to CamelCase world when name begins or ends with _")
        
        camel = list(name)
        
        while "_" in camel:
            index = camel.index("_")
            del camel[index]
            if camel[index] is "_":
                raise ValueError(u"Double underscores are not allowed")
            camel[index] = camel[index].upper()
        return ''.join(camel)
    
    def test_camelcase_aliases(self):
        for i in ["assert_true", "assert_equals", "assert_false", "assert_almost_equals"]:
            #FIXME: yield tests after #12 is resolved
            #yield lambda x, y: self.assert_equals, getattr(self, i), getattr(self, self.get_camel(i))
            self.assert_equals(getattr(self, i), getattr(self, self.get_camel(i)))
    
    def test_get_camel(self):
        self.assert_equals("assertTrue", self.get_camel("assert_true"))
    
    def test_get_camel_invalid_trail(self):
        self.assert_raises(ValueError, lambda:self.get_camel("some_trailing_test_"))

    def test_get_camel_invalid_double_under(self):
        self.assert_raises(ValueError, lambda:self.get_camel("toomuchtrail__between"))
                           
    def test_get_camel_invalid_prefix(self):
        self.assert_raises(ValueError, lambda:self.get_camel("_prefix"))


class TestFeatures(UnitTestCase):

    def test_even_unit_can_access_views(self):
        self.assert_equals(200, self.client.get("/testtwohundred/").status_code)

class TestProperClashing(UnitTestCase):
    """
    Test we're getting expected failures when working with db,
    i.e. that database is not purged between tests.
    We rely that test suite executed methods in this order:
      (1) test_aaa_inserting_model
      (2) test_bbb_inserting_another
      
    This is antipattern and should not be used, but it's hard to test
    framework from within ;) Better solution would be greatly appreciated.  
    """
    
    def test_aaa_inserting_model(self):
        ExampleModel.objects.create(name="test1")
        self.assert_equals(1, len(ExampleModel.objects.all()))

    def test_bbb_inserting_another(self):
        ExampleModel.objects.create(name="test2")
        self.assert_equals(2, len(ExampleModel.objects.all()))


class TestProperCacheClearance(UnitTestCase):
    """
    Test cache is cleared, i.e. not preserved between tests
    We rely that test suite executed methods in this order:
      (1) test_aaa_inserting_cache
      (2) test_bbb_cache_retrieval

    This is antipattern and should not be used, but it's hard to test
    framework from within ;) Better solution would be greatly appreciated.
    """

    def test_aaa_inserting_model(self):
        cache.set("test", "pwned")
        self.assert_equals("pwned", cache.get("test"))

    def test_bbb_inserting_another(self):
        self.assert_equals(None, cache.get("test"))


class TestTranslations(UnitTestCase):
    def test_czech_string_acquired(self):
        """
        Test we're retrieving string translated to Czech.
        This is assuming we're using LANG="cs"
        """
        self.assert_equals(u"Přeložitelný řetězec", unicode(ExampleModel.get_translated_string()))


#TODO: This is not working, looks like once you cannot return to null translations
# once you have selected any. Patches welcomed.
#class TestSkippedTranslations(UnitTestCase):
#    make_translations=False
#
#    def test_english_string_acquired(self):
#        from django.utils import translation
#        translation.deactivate()
#        self.assert_equals(u"Translatable string", unicode(ExampleModel.get_translated_string()))

class TestNotDefaultTranslations(UnitTestCase):
    translation_language_code = 'de'
    def test_german_translated_string_acquired(self):
        self.assert_equals(u"Ersetzbare Zeichenkette", unicode(ExampleModel.get_translated_string()))


def function_test():
    # just to verify we work with them
    assert True is True

class TestMocking(UnitTestCase):

    def test_sanity_for_missing_setting_present(self):
        self.assert_false(hasattr(settings, "INSANE_ATTRIBUTE_THAT_SHOULD_NOT_BE_PRESENT"))
    
    def test_expected_setting_present(self):
        self.assert_equals("owned", settings.NONSENSICAL_SETTING_ATTRIBUTE_FOR_MOCK_TESTING)

    @mock_settings("INSANE_ATTRIBUTE_THAT_SHOULD_NOT_BE_PRESENT", "Cthulhed!")
    def test_setting_mocked(self):
        self.assert_equals("Cthulhed!", settings.INSANE_ATTRIBUTE_THAT_SHOULD_NOT_BE_PRESENT)

    @mock_settings("NONSENSICAL_SETTING_ATTRIBUTE_FOR_MOCK_TESTING", "pwned!")
    def test_existing_setting_mocked(self):
        self.assert_equals("pwned!", settings.NONSENSICAL_SETTING_ATTRIBUTE_FOR_MOCK_TESTING)

class TestMockingCleansAfterItself(UnitTestCase):
    @mock_settings("INSANE_ATTRIBUTE_THAT_SHOULD_NOT_BE_PRESENT", "Cthulhed!")
    def test_aaa_mocked(self):
        self.assert_equals("Cthulhed!", settings.INSANE_ATTRIBUTE_THAT_SHOULD_NOT_BE_PRESENT)

    def test_bbb_attribute_not_present(self):
        self.assert_false(hasattr(settings, "INSANE_ATTRIBUTE_THAT_SHOULD_NOT_BE_PRESENT"))
    
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy as _

class ExampleModel(models.Model):
    name = models.CharField(max_length=50)

    @staticmethod
    def get_translated_string():
        return _(u"Translatable string")

    def __unicode__(self):
        return u"ExampleModel %s" % self.name
########NEW FILE########
__FILENAME__ = dsttestfilters
from django import template

register = template.Library()

@register.filter
def ihatebs(value):
    return value.replace('b', 'a')

########NEW FILE########
__FILENAME__ = dsttesttags
from django import template

register = template.Library()

class TableNode(template.Node):
    root_tmpl = u'<table>%s</table>'
    row_tmpl = u'<tr>%s</tr>'
    cell_tmpl = u'<td>%s</td>'

    def __init__(self, data):
        self.data = data

    def render(self, context):
        row_res = []
        for row in self.data:
            cell_res = []
            for cell in row:
                cell_res.append(self.cell_tmpl % cell)
            row_res.append(self.row_tmpl % u''.join(cell_res))
        return self.root_tmpl % u''.join(row_res)

@register.tag
def table(parser, token):
    args = token.contents.split()[1:]
    if len(args) < 1:
        raise template.TemplateSyntaxError("Not enough arguments for 'table'")
    return TableNode([arg.split('_') for arg in args])

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from views import *

urlpatterns = patterns('',
    (r'^testtwohundred/$', twohundred),
    (r'^assert_two_example_models/$', assert_two_example_models),
    (r'^return_not_authorized/$', return_not_authorized),
    (r'^return_server_error/$', return_server_error),
    (r'^return_django_error/$', return_django_error),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse, HttpResponseServerError
from testapp.models import ExampleModel

class HttpResponseNotAuthorized(HttpResponse):
    status_code = 401

def twohundred(request):
    return HttpResponse(content='OKidoki')

def assert_two_example_models(request):
    assert 2 == len(ExampleModel.objects.all())
    return HttpResponse(content='OKidoki')

def return_not_authorized(request):
    return HttpResponseNotAuthorized("401 Not Authorized")

def return_server_error(request):
    return HttpResponseServerError("500 Server error")

def return_django_error(request):
    raise Exception('500 Django error')

########NEW FILE########
