__FILENAME__ = tutorial
from behave import *

@given('we have behave installed')
def step(context):
    pass

@when('we implement a test')
def step(context):
    assert True is not False

@then('behave will test it for us!')
def step(context):
    assert context.failed is False

########NEW FILE########
__FILENAME__ = test_bdd
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    args = '<app  ...>'
    help = 'Runs the BDD tests on the specified apps'

    def handle(self, *args, **options):
        for app in args:
            self.stdout.write('TODO: Run BDD test on app "%s"\n' % app)

# eof            

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = runner
"""Django test runner which uses behave for BDD tests.
"""

from optparse import make_option
from os.path import dirname, abspath, basename, join, isdir

try:
    from django.test.runner import DiscoverRunner as BaseRunner
except ImportError:
    from django.test.simple import DjangoTestSuiteRunner as BaseRunner
from django.test import LiveServerTestCase
from django.db.models import get_app

from behave.configuration import Configuration, ConfigError, options
from behave.runner import Runner as BehaveRunner
from behave.parser import ParserError
from behave.formatter.ansi_escapes import escapes

import sys


def get_app_dir(app_module):
    app_dir = dirname(app_module.__file__)
    if basename(app_dir) == 'models':
        app_dir = abspath(join(app_dir, '..'))
    return app_dir


def get_features(app_module):
    app_dir = get_app_dir(app_module)
    features_dir = abspath(join(app_dir, 'features'))
    if isdir(features_dir):
        return features_dir
    else:
        return None


# Get Behave command line options and add our own
def get_options():
    option_list = (
        make_option("--behave_browser",
            action="store",
            dest="browser",
            help="Specify the browser to use for testing",
        ),
    )

    option_info = {"--behave_browser": True}

    for fixed, keywords in options:
        # Look for the long version of this option
        long_option = None
        for option in fixed:
            if option.startswith("--"):
                long_option = option
                break

        # Only deal with those options that have a long version
        if long_option:
            # remove function types, as they are not compatible with optparse
            if hasattr(keywords.get('type'), '__call__'):
                del keywords['type']

            # Remove 'config_help' as that's not a valid optparse keyword
            if keywords.has_key("config_help"):
                keywords.pop("config_help")

            name = "--behave_" + long_option[2:]

            option_list = option_list + \
                (make_option(name, **keywords),)

            # Need to store a little info about the Behave option so that we
            # can deal with it later.  'has_arg' refers to if the option has
            # an argument.  A boolean option, for example, would NOT have an
            # argument.
            action = keywords.get("action", "store")
            if action == "store" or action == "append":
                has_arg = True
            else:
                has_arg = False

            option_info.update({name: has_arg})

    return (option_list, option_info)


# Parse options that came in.  Deal with ours, create an ARGV for Behave with
# it's options
def parse_argv(argv, option_info):
    behave_options = option_info.keys()
    new_argv = ["behave",]
    our_opts = {"browser": None}

    for index in xrange(len(argv)):
        # If it's a behave option AND is the long version (starts with '--'),
        # then proceed to save the information.  If it's not a behave option
        # (which means it's most likely a Django test option), we ignore it.
        if argv[index] in behave_options and argv[index].startswith("--"):
            if argv[index] == "--behave_browser":
                our_opts["browser"] = argv[index + 1]
                index += 1  # Skip past browser option arg
            else:
                # Convert to Behave option
                new_argv.append("--" + argv[index][9:])

                # Add option argument if there is one
                if option_info[argv[index]] == True:
                    new_argv.append(argv[index+1])
                    index += 1  # Skip past option arg

    return (new_argv, our_opts)


class DjangoBehaveTestCase(LiveServerTestCase):
    def __init__(self, **kwargs):
        self.features_dir = kwargs.pop('features_dir')
        self.option_info = kwargs.pop('option_info')
        super(DjangoBehaveTestCase, self).__init__(**kwargs)

    def get_features_dir(self):
        if isinstance(self.features_dir, basestring):
            return [self.features_dir]
        return self.features_dir

    def setUp(self):
        self.setupBehave()

    def setupBehave(self):
        # Create a sys.argv suitable for Behave to parse
        old_argv = sys.argv
        (sys.argv, our_opts) = parse_argv(old_argv, self.option_info)
        self.behave_config = Configuration()
        sys.argv = old_argv
        self.behave_config.browser = our_opts["browser"]

        self.behave_config.server_url = self.live_server_url  # property of LiveServerTestCase
        self.behave_config.paths = self.get_features_dir()
        self.behave_config.format = self.behave_config.format if self.behave_config.format else ['pretty']
        # disable these in case you want to add set_trace in the tests you're developing
        self.behave_config.stdout_capture = False
        self.behave_config.stderr_capture = False

    def runTest(self, result=None):
        # run behave on a single directory

        # from behave/__main__.py
        #stream = self.behave_config.output
        runner = BehaveRunner(self.behave_config)
        try:
            failed = runner.run()
        except ParserError, e:
            sys.exit(str(e))
        except ConfigError, e:
            sys.exit(str(e))

        try:
            undefined_steps = runner.undefined_steps
        except AttributeError:
            undefined_steps = runner.undefined

        if self.behave_config.show_snippets and undefined_steps:
            msg = u"\nYou can implement step definitions for undefined steps with "
            msg += u"these snippets:\n\n"
            printed = set()

            if sys.version_info[0] == 3:
                string_prefix = "('"
            else:
                string_prefix = u"(u'"

            for step in set(undefined_steps):
                if step in printed:
                    continue
                printed.add(step)

                msg += u"@" + step.step_type + string_prefix + step.name + u"')\n"
                msg += u"def impl(context):\n"
                msg += u"    assert False\n\n"

            sys.stderr.write(escapes['undefined'] + msg + escapes['reset'])
            sys.stderr.flush()

        if failed:
            sys.exit(1)
        # end of from behave/__main__.py


class DjangoBehaveTestSuiteRunner(BaseRunner):
    # Set up to accept all of Behave's command line options and our own.  In
    # order to NOT conflict with Django's test command, we'll start all options
    # with the prefix "--behave_" (we'll only do the long version of an option).
    (option_list, option_info) = get_options()

    def make_bdd_test_suite(self, features_dir):
        return DjangoBehaveTestCase(features_dir=features_dir, option_info=self.option_info)

    def build_suite(self, test_labels, extra_tests=None, **kwargs):
        extra_tests = extra_tests or []
        #
        # Add BDD tests to the extra_tests
        #

        # always get all features for given apps (for convenience)
        for label in test_labels:
            if '.' in label:
                print "Ignoring label with dot in: %s" % label
                continue
            app = get_app(label)

            # Check to see if a separate 'features' module exists,
            # parallel to the models module
            features_dir = get_features(app)
            if features_dir is not None:
                # build a test suite for this directory
                extra_tests.append(self.make_bdd_test_suite(features_dir))

        return super(DjangoBehaveTestSuiteRunner, self
                     ).build_suite(test_labels, extra_tests, **kwargs)
# eof:

########NEW FILE########
__FILENAME__ = splinter.steps_library
from urlparse import urljoin

from behave import *

"""
This file contains some useful generic steps for use with
the splinter web automation library.

http://splinter.cobrateam.info/

The following user roles are used:
'the user': a user without admin privileges
'the adminuser': a user with admin privileges

This is a Work-In-Progress
"""


@given(u'any startpoint')
def any_startpoint(context):
    assert True


@given(u'the user accesses the url "{url}"')
def the_user_accesses_the_url(context, url):
    full_url = urljoin(context.config.server_url, url)
    context.browser.visit(full_url)


@then(u'the url is "{url}"')
def the_url_is(context, url):
    path_info = context.browser.url.replace(context.config.server_url, '')
    assert path_info == url


@then(u'the page contains the h1 "{h1}"')
def the_page_contains_the_h1(context, h1):
    page_h1 = context.browser.find_by_tag('h1').first
    assert h1 == page_h1.text, "Page should contain h1 '%s', has '%s'" % (h1, page_h1.text)


# TODO
# @given(u'a non-logged-in user accesses the url "{url}"')
# def a_non_logged_in_user_accesses_the_url(context, url):
#     full_url = ''.join(['http://localhost:8081', url])
#     context.browser.visit(full_url)


@given(u'the user is shown the login page')
def the_user_is_shown_the_login_page(context):
    return the_url_is(context, '/accounts/login/')


@then(u'the user is shown the home page')
def the_user_is_shown_the_home_page(context):
    return the_url_is(context, '/')


# TODO
# @given(u'the user logins as an admin user')
# def impl(context):
#     assert False

# eof

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase

from django.core.management import call_command

## class CommandText(TestCase):
##     def test_command_exists(self):
## 	call_command('test_bdd')
        
from django.test import LiveServerTestCase
from selenium.webdriver.firefox.webdriver import WebDriver

## class BDD_TestCase(LiveServerTestCase):

##     @classmethod
##     def setUpClass(cls):
##         cls.selenium = WebDriver()
##         super(BDD_TestCase, cls).setUpClass()

##     @classmethod
##     def tearDownClass(cls):
##         super(BDD_TestCase, cls).tearDownClass()
##         cls.selenium.quit()

# eof

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

# Register your models here.

########NEW FILE########
__FILENAME__ = tutorial
from behave import *

@given('we have behave installed')
def step_impl(context):
    pass

@when('we implement a test')
def step_impl(context):
    assert True is not False

@then('behave will test it for us')
def step_impl(context):
    assert context.failed is False


########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase

# Create your tests here.

class ExampleTest(TestCase):
    def test_failing(self):
        """ This is a failing unit test """
        self.assertTrue(False)

    def test_passing(self):
        """ This is a passing unit test """
        self.assertTrue(True)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render

# Create your views here.

########NEW FILE########
__FILENAME__ = runner
from django_behave.runner import DjangoBehaveTestCase, DjangoBehaveTestSuiteRunner


class ChromeTestCase(DjangoBehaveTestCase):
    def get_browser(self):
        return webdriver.Chrome()


class ChromeRunner(DjangoBehaveTestSuiteRunner):
    def make_bdd_test_suite(self, features_dir):
        return ChromeTestCase(features_dir=features_dir)

########NEW FILE########
__FILENAME__ = settings
# Django settings for proj project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'django_behave',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
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
SECRET_KEY = 'g^00(m$+_dc$coxkj$3n4*79s_t=bm-*qc%&amp;i_-j_2iei7pj#w'

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

ROOT_URLCONF = 'proj.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'proj.wsgi.application'

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
    'example_app',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',

    'django_behave',
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

TEST_RUNNER = 'django_behave.runner.DjangoBehaveTestSuiteRunner'
# eof

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_proj.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = tests
try:
    import unittest2 as unittest  # import unittest2 for 2.6
except ImportError:
    import unittest

import subprocess

class BehaveTest(unittest.TestCase):
    def run_test(self, app='example_app', settings='example_proj.settings', *args, **kwargs):
        """
        test the given app with the given args and kwargs passed to manage.py. kwargs are converted from
        {'a': 'b'} to --a b

        returns a tuple: (stdout, stderr)
        """
        args = list(args)
        kwargs['settings'] = settings
        for k, v in kwargs.items():
            args += ['--%s' % k, v]
        p = subprocess.Popen(['./manage.py', 'test', app] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return p.communicate()

    def test_runner_with_default_args_expect_bdd_tests_run(self):
        actual = self.run_test()

        self.assertIn('scenario passed', actual[0])

    def test_runner_with_failfast_and_failing_unittest_expect_bdd_tests_not_run(self):
        actual = self.run_test('--failfast')

        self.assertNotIn('scenario passed', actual[0])

    def test_runner_with_old_tag_specified_expect_only_old_bdd_test_run(self):
        actual = self.run_test(behave_tags='@old')

        self.assertIn('1 scenario passed, 0 failed, 1 skipped', actual[0])

    def test_runner_with_undefined_steps_expect_display_undefined_steps(self):
        actual = self.run_test()        

        self.assertIn('You can implement step definitions for undefined steps with', actual[1])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
