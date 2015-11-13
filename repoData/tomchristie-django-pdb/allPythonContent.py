__FILENAME__ = runserver
import sys
import pdb

from django_pdb.management import load_parent_command
from django_pdb.middleware import PdbMiddleware

from optparse import make_option
from django_pdb.utils import has_ipdb
from django.views import debug


RunServerCommand = load_parent_command('runserver')


class Command(RunServerCommand):
    """
    Identical to Django's standard 'runserver' management command,
    except that it also adds support for a '--pdb' option.
    """
    option_list = RunServerCommand.option_list + (
        make_option('--pdb', action='store_true', dest='pdb', default=False,
            help='Drop into pdb shell on at the start of any view.'),
        make_option('--ipdb', action='store_true', dest='ipdb', default=False,
            help='Drop into ipdb shell on at the start of any view.'),
        make_option('--pm', action='store_true', dest='pm', default=False,
            help='Drop into ipdb shell if an exception is raised in a view.'),
    )

    def handle(self, *args, **options):
        # Add pdb middleware, if --pdb is specified, or if we're in DEBUG mode
        from django.conf import settings

        pdb_option = options.pop('pdb')
        ipdb_option = options.pop('ipdb')

        middleware = 'django_pdb.middleware.PdbMiddleware'
        if ((pdb_option or settings.DEBUG)
            and middleware not in settings.MIDDLEWARE_CLASSES):
            settings.MIDDLEWARE_CLASSES += (middleware,)

        self.pm = options.pop('pm')
        if self.pm:
            debug.technical_500_response = self.reraise

        # If --pdb is specified then always break at the start of views.
        # Otherwise break only if a 'pdb' query parameter is set in the url.
        if pdb_option:
            PdbMiddleware.always_break = 'pdb'
        elif ipdb_option:
            PdbMiddleware.always_break = 'ipdb'

        super(Command, self).handle(*args, **options)

    def reraise(self, request, exc_type, exc_value, tb):
        if has_ipdb():
            import ipdb
            p = ipdb
        else:
            p = pdb
        if self.pm:
            print >>sys.stderr, "Exception occured: %s, %s" % (exc_type, exc_value)
            p.post_mortem(tb)
        else:
            raise

########NEW FILE########
__FILENAME__ = test
from optparse import make_option
import sys

from django.core.management.commands import test

from django_pdb.management import load_parent_command
from django_pdb.testrunners import make_suite_runner


# Provide a Command class so that Django knows what will handle
# things. This module does not override it, so it just needs to find
# the parent Command.
Command = load_parent_command('test')


def patch_test_command(Command):
    """
    Monkeypatches Django's TestCommand so that it chooses to use
    ipdb or pdb, allowing subclasses to inherit from it and wrap its
    behaviour.
    """
    Command.option_list += type(Command.option_list)([
        make_option('--pdb', action='store_true', dest='pdb', default=False,
                    help='Drop into pdb shell on test errors or failures.'),
        make_option('--ipdb', action='store_true', dest='ipdb', default=False,
                    help='Drop into ipdb shell on test errors or failures.'),
    ])

    def handle(self, *test_labels, **options):
        """
        If --pdb is set on the command line ignore the default test runner
        use the pdb test runner instead.
        """
        pdb = options.pop('pdb')
        ipdb = options.pop('ipdb')

        if pdb or ipdb:
            options['verbosity'] = int(options.get('verbosity', 1))
            options['interactive'] = options.get('interactive', True)
            options['failfast'] = options.get('failfast', False)

            TestRunner = self.get_runner(use_ipdb=ipdb)
            test_runner = TestRunner(**options)
            failures = test_runner.run_tests(test_labels)

            if failures:
                sys.exit(bool(failures))

        else:
            self._handle(*test_labels, **options)

    Command._handle = Command.handle
    Command.handle = handle

    def get_runner(self, use_ipdb, suite_runner=None):
        return make_suite_runner(use_ipdb=use_ipdb, suite_runner=suite_runner)

    Command.get_runner = get_runner

patch_test_command(test.Command)

########NEW FILE########
__FILENAME__ = middleware
import inspect
import os
import pdb
import sys

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed

from django_pdb.utils import get_ipdb, has_ipdb


class PdbMiddleware(object):
    """
    Middleware to break into pdb at the start of views.

    If `always_break` is set, due to `runserver --pdb` this will break
    into pdb at the start of every view.

    Otherwise it will break into pdb at the start of the view if
    a 'pdb' GET parameter is set on the request url.
    """

    always_break = False

    def __init__(self, debug_only=True):
        """
        If debug_only is True, this middleware removes itself
        unless settings.DEBUG is also True. Otherwise, this middleware
        is always active.
        """
        if debug_only and not settings.DEBUG:
            raise MiddlewareNotUsed()

    def get_type_pdb(self, request):
        type_pdb = None
        if self.always_break:
            type_pdb = self.always_break
        elif request.GET.get('pdb', None) is not None:
            type_pdb = 'pdb'
        elif request.GET.get('ipdb', None) is not None:
            type_pdb = 'ipdb'
        return type_pdb

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        If running with '--pdb', set a breakpoint at the start
        of each of each view before it gets called.
        """
        # Skip out unless using `runserver --pdb`,
        # or `pdb` is in the command line parameters
        type_pdb = self.get_type_pdb(request)
        if not type_pdb:
            return

        filename = inspect.getsourcefile(view_func)
        basename = os.path.basename(filename)
        dirname = os.path.basename(os.path.dirname(filename))
        lines, lineno = inspect.getsourcelines(view_func)
        temporary = True
        cond = None
        funcname = view_func.__name__

        print()
        print('{} {}'.format(request.method, request.get_full_path()))
        print('function "{}" in {}/{}:{}'.format(funcname,
            dirname, basename, lineno))
        print('args: {}'.format(view_args))
        print('kwargs: {}'.format(view_kwargs))
        print()

        if type_pdb == 'ipdb' and has_ipdb():
            p = get_ipdb()
        else:
            if not type_pdb == 'pdb':
                print('You do not install ipdb or ipython module')
            p = pdb.Pdb()
        p.reset()
        p.set_break(filename, lineno + 1, temporary, cond, funcname)
        sys.settrace(p.trace_dispatch)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = pdb
from django import template
from django_pdb.utils import has_ipdb


register = template.Library()

@register.filter
def pdb(element):
    from django_pdb.utils import get_pdb_set_trace
    get_pdb_set_trace()()
    return element


@register.filter
def ipdb(element):
    if has_ipdb():
        from ipdb import set_trace
    else:
        from django_pdb.utils import get_pdb_set_trace
        get_pdb_set_trace()()
    set_trace()
    return element

########NEW FILE########
__FILENAME__ = testrunners
import pdb

from django.test.utils import get_runner

try:
    # Django 1.3+
    from django.utils import unittest
    TextTestResult = unittest.TextTestResult
except ImportError:
    # Django 1.2
    import unittest
    TextTestResult = unittest._TextTestResult
    from django.test.simple import DjangoTestRunner
else:
    # Django 1.3+
    from django.utils.unittest import TextTestRunner as DjangoTestRunner

from django_pdb.utils import has_ipdb


class ExceptionTestResultMixin(object):
    """
    A mixin class that can be added to any test result class.
    Drops into pdb on test errors/failures.
    """
    pdb_type = 'pdb'

    def get_pdb(self):
        if self.pdb_type == 'ipdb' and has_ipdb():
            import ipdb
            return ipdb
        return pdb

    def addError(self, test, err):
        super(ExceptionTestResultMixin, self).addError(test, err)
        exctype, value, tb = err

        self.stream.writeln()
        self.stream.writeln(self.separator1)
        self.stream.writeln(">>> %s" % (self.getDescription(test)))
        self.stream.writeln(self.separator2)
        self.stream.writeln(self._exc_info_to_string(err, test).rstrip())
        self.stream.writeln(self.separator1)
        self.stream.writeln()

        # Skip test runner traceback levels
        #while tb and self._is_relevant_tb_level(tb):
        #    tb = tb.tb_next

        self.get_pdb().post_mortem(tb)

    def addFailure(self, test, err):
        super(ExceptionTestResultMixin, self).addFailure(test, err)
        exctype, value, tb = err

        self.stream.writeln()
        self.stream.writeln(self.separator1)
        self.stream.writeln(">>> %s" % (self.getDescription(test)))
        self.stream.writeln(self.separator2)
        self.stream.writeln(self._exc_info_to_string(err, test).rstrip())
        self.stream.writeln(self.separator1)
        self.stream.writeln()

        ## Skip test runner traceback levels
        #while tb and self._is_relevant_tb_level(tb):
        #    tb = tb.tb_next

        # Really hacky way to jump up a couple of frames.
        # I'm sure it's not that difficult to do properly,
        # but I havn't figured out how.
        #p = pdb.Pdb()
        #p.reset()
        #p.setup(None, tb)
        #p.do_up(None)
        #p.do_up(None)
        #p.cmdloop()

        # It would be good if we could make sure we're in the correct frame here
        self.get_pdb().post_mortem(tb)


class PdbTestResult(ExceptionTestResultMixin, TextTestResult):
    pass


class PdbTestRunner(DjangoTestRunner):
    """
    Override the standard DjangoTestRunner to instead drop into pdb on test errors/failures.
    """
    def _makeResult(self):
        return PdbTestResult(self.stream, self.descriptions, self.verbosity)


class IPdbTestResult(ExceptionTestResultMixin, TextTestResult):

    pdb_type = 'ipdb'


class IPdbTestRunner(DjangoTestRunner):
    """
    Override the standard DjangoTestRunner to instead drop into ipdb on test errors/failures.
    """
    def _makeResult(self):
        return IPdbTestResult(self.stream, self.descriptions, self.verbosity)


def make_suite_runner(use_ipdb, suite_runner=None):
    if use_ipdb:
        runner = IPdbTestRunner
    else:
        runner = PdbTestRunner

    if suite_runner is None:
        from django.conf import settings
        suite_runner = get_runner(settings)

    class PdbTestSuiteRunner(suite_runner):
        """
        Override the standard DjangoTestSuiteRunner to instead drop
        into the debugger on test errors/failures.
        """
        def run_suite(self, suite, **kwargs):
            return runner(verbosity=self.verbosity,
                          failfast=self.failfast).run(suite)

    return PdbTestSuiteRunner
########NEW FILE########
__FILENAME__ = utils
def has_ipdb():
    try:
        import ipdb
        import IPython
        return True
    except ImportError:
        return False


def get_ipdb():
    def_colors = get_def_colors()
    try:
        import ipdb
        from ipdb import __main__
        return ipdb.__main__.Pdb(def_colors)
    except ImportError:  # old versions of ipdb
        return ipdb.Pdb(def_colors)


def get_pdb_set_trace():
    # for the templatetags because the file is named 'pdb' and that cause an importation conflict
    from pdb import set_trace
    return set_trace


def get_def_colors():
    # Inspirated in https://github.com/gotcha/ipdb/blob/master/ipdb/__main__.py
    def_colors = 'Linux'
    import IPython
    if IPython.__version__ > '0.10.2':
        from IPython.core.debugger import Pdb
        try:
            get_ipython
        except NameError:
            from IPython.frontend.terminal.embed import InteractiveShellEmbed
            ipshell = InteractiveShellEmbed()
            def_colors = ipshell.colors
        else:
            try:
                def_colors = get_ipython.im_self.colors
            except AttributeError:
                def_colors = get_ipython.__self__.colors
    else:
        from IPython.Debugger import Pdb
        from IPython.Shell import IPShell
        from IPython import ipapi
        ip = ipapi.get()
        if ip is None:
            IPShell(argv=[''])
            ip = ipapi.get()
        def_colors = ip.options.colors
    return def_colors

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings  # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for testproject project.


def ABSOLUTE_PATH(relative_path):
    import os
    project_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(project_path, relative_path)

# Standard Django settings...

DEBUG = True
TEMPLATE_DEBUG = DEBUG
TESTING = False

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': ABSOLUTE_PATH('sqlite3.db'),    # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
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
SECRET_KEY = '#dg%i9y7=&ptwjv!m1+8lq9l1-27a0s5u85-i-u@-3+1oo2)w-'

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
    'django_pdb.middleware.PdbMiddleware',
)

ROOT_URLCONF = 'testproject.urls'

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
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'django_pdb',
    'testapp',
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase


class SimpleTest(TestCase):
    """
    A couple of dummy tests to demonstrate 'manage.py test --pdb'.
    """

    def test_error(self):
        """
        Tests that 1 + 1 always equals 4.
        """
        a = 1
        b = 2
        c = 3
        one_plus_one = four

    def test_failure(self):
        """
        Tests that 1 + 1 always equals 4.
        """
        a = 1
        b = 2
        c = 3
        self.assertEqual(1 + 1, 4)

########NEW FILE########
__FILENAME__ = views
"""
A dummy view to demonstrate using 'manage.py runserver --pdb'
"""
from django.http import HttpResponse
from django.shortcuts import render


def myview(request):
    a = 1
    b = 2
    c = 3
    return HttpResponse('Hello, you.', content_type='text/plain')

def filter_view(request):
    variable = "I'm the variable"
    return render(request, 'test.html', {"variable": variable})

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    (r'^$', 'testproject.testapp.views.myview'),
    (r'^filter/$', 'testproject.testapp.views.filter_view'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
