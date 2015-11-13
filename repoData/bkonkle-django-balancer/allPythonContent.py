__FILENAME__ = middleware
from datetime import datetime, timedelta

from django.conf import settings

from balancer import pinning


# The name of the session variable or cookie used by the middleware
PINNING_KEY = getattr(settings, 'MASTER_PINNING_KEY', 'master_db_pinned')

# The number of seconds to direct reads to the master database after a write
PINNING_SECONDS = int(getattr(settings, 'MASTER_PINNING_SECONDS', 5))


class PinningSessionMiddleware(object):
    """
    Middleware to support the PinningMixin.  Sets a session variable if
    there was a database write, which will direct that user's subsequent reads
    to the master database.
    """
    
    def process_request(self, request):
        """
        Set the thread's pinning flag according to the presence of the session
        variable.
        """
        pinned_until = request.session.get(PINNING_KEY, False)
        if pinned_until and pinned_until > datetime.now():
            pinning.pin_thread()
        
    def process_response(self, request, response):
        """
        If there was a write to the db, set the session variable to enable
        pinning.  If the variable already exists, the time will be reset.
        """
        if pinning.db_was_written():
            pinned_until = datetime.now() + timedelta(seconds=PINNING_SECONDS)
            request.session[PINNING_KEY] = pinned_until
            pinning.clear_db_write()
        pinning.unpin_thread()
        return response


class PinningCookieMiddleware(object):
    """
    Middleware to support the PinningMixin.  Sets a cookie if there was a
    database write, which will direct that user's subsequent reads to the
    master database.
    """
    
    def process_request(self, request):
        """
        Set the thread's pinning flag according to the presence of the cookie.
        """
        if PINNING_KEY in request.COOKIES:
            pinning.pin_thread()
    
    def process_response(self, request, response):
        """
        If this is a POST request and there was a write to the db, set the
        cookie to enable pinning.  If the cookie already exists, the time will
        be reset.
        """
        if request.method == 'POST' and pinning.db_was_written():
            response.set_cookie(PINNING_KEY,
                                value='y',
                                max_age=PINNING_SECONDS)
            pinning.clear_db_write()
        pinning.unpin_thread()
        return response

########NEW FILE########
__FILENAME__ = mixins
from balancer import pinning


class MasterSlaveMixin(object):
    """
    A mixin that randomly selects from a weighted pool of slave databases
    for read operations, but uses the default database for writes.
    """

    def __init__(self):
        super(MasterSlaveMixin, self).__init__()
        from django.conf import settings
        self.master = settings.MASTER_DATABASE

    def db_for_write(self, model, **hints):
        """Send all writes to the master"""
        return self.master

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow any relation between two objects in the slave pool or the master.
        """
        pool = self.pool + [self.master]
        if obj1._state.db in pool and obj2._state.db in pool:
            return True
        return None

    def allow_syncdb(self, db, model):
        """Only allow syncdb on the master"""
        return db == self.master


class PinningMixin(object):
    """
    A mixin that pins reads to the database defined in the MASTER_DATABASE
    setting for a pre-determined period of time after a write.  Requires the
    PinningRouterMiddleware.
    """
    
    def db_for_read(self, model, **hints):
        from django.conf import settings
        if pinning.thread_is_pinned():
            return settings.MASTER_DATABASE
        return super(PinningMixin, self).db_for_read(model, **hints)
    
    def db_for_write(self, model, **hints):
        pinning.set_db_write()
        pinning.pin_thread()
        return super(PinningMixin, self).db_for_write(model, **hints)

########NEW FILE########
__FILENAME__ = models
# Yes, Django, I am actually an app. That means you really do want to run
# my tests.

########NEW FILE########
__FILENAME__ = pinning
import threading

_locals = threading.local()


def pin_thread():
    """
    Mark this thread as 'pinned', so that future reads will temporarily go
    to the master database for the current user.  
    """
    _locals.pinned = True


def unpin_thread():
    """
    Clear the 'pinned' flag so that future reads are distributed normally.
    """
    if getattr(_locals, 'pinned', False):
        del _locals.pinned


def thread_is_pinned():
    """Check whether the current thread is pinned."""
    return getattr(_locals, 'pinned', False)


def set_db_write():
    """Indicate that the database was written to."""
    _locals.db_write = True


def clear_db_write():
    if getattr(_locals, 'db_write', False):
        del _locals.db_write


def db_was_written():
    """Check whether a database write was performed."""
    return getattr(_locals, 'db_write', False)

########NEW FILE########
__FILENAME__ = routers
import bisect
import itertools
import random
import warnings

from balancer.mixins import MasterSlaveMixin, PinningMixin


class BasePoolRouter(object):
    """
    A base class for routers that use a pool of databases defined by the
    DATABASE_POOL setting.
    """

    def __init__(self):
        from django.conf import settings
        if isinstance(settings.DATABASE_POOL, dict):
            self.pool = settings.DATABASE_POOL.keys()
        else:
            self.pool = list(settings.DATABASE_POOL)

    def allow_relation(self, obj1, obj2, **hints):
        """Allow any relation between two objects in the pool"""
        if obj1._state.db in self.pool and obj2._state.db in self.pool:
            return True
        return None

    def allow_syncdb(self, db, model):
        """Explicitly put all models on all databases"""
        return True


class RandomRouter(BasePoolRouter):
    """A router that randomly selects from a pool of databases."""

    def db_for_read(self, model, **hints):
        return self.get_random_db()

    def db_for_write(self, model, **hints):
        return self.get_random_db()

    def get_random_db(self):
        return random.choice(self.pool)


class WeightedRandomRouter(RandomRouter):
    """
    A router that randomly selects from a weighted pool of databases, useful
    for replication configurations where all nodes act as masters.
    """

    def __init__(self):
        from django.conf import settings
        self.pool = settings.DATABASE_POOL.keys()
        self.totals = []

        weights = settings.DATABASE_POOL.values()
        running_total = 0

        for w in weights:
            running_total += w
            self.totals.append(running_total)

    def get_random_db(self):
        """Use binary search to find the index of the database to use"""
        rnd = random.random() * self.totals[-1]
        pool_index = bisect.bisect_right(self.totals, rnd)
        return self.pool[pool_index]


class RoundRobinRouter(BasePoolRouter):
    """
    A router that cycles over a pool of databases in order, evenly distributing
    the load.
    """

    def __init__(self):
        super(RoundRobinRouter, self).__init__()

        # Shuffle the pool so the first database isn't slammed during startup.
        random.shuffle(self.pool)

        self.pool_cycle = itertools.cycle(self.pool)

    def db_for_read(self, model, **hints):
        return self.get_next_db()

    def db_for_write(self, model, **hints):
        return self.get_next_db()

    def get_next_db(self):
        return self.pool_cycle.next()


class WeightedMasterSlaveRouter(MasterSlaveMixin, WeightedRandomRouter):
    pass


class RoundRobinMasterSlaveRouter(MasterSlaveMixin, RoundRobinRouter):
    pass


class PinningWMSRouter(PinningMixin, WeightedMasterSlaveRouter):
    """A weighted master/slave router that uses the pinning mixin."""
    pass


class PinningRRMSRouter(PinningMixin, RoundRobinMasterSlaveRouter):
    """A round-robin master/slave router that uses the pinning mixin."""
    pass

########NEW FILE########
__FILENAME__ = tests
import unittest
from datetime import datetime, timedelta

from django.conf import settings
from django.test import TestCase

import balancer
from balancer import pinning
from balancer.routers import RandomRouter, RoundRobinRouter, \
                             WeightedRandomRouter, \
                             WeightedMasterSlaveRouter, \
                             RoundRobinMasterSlaveRouter, \
                             PinningWMSRouter, PinningRRMSRouter
from balancer.middleware import PINNING_KEY, PINNING_SECONDS, \
                                PinningSessionMiddleware, \
                                PinningCookieMiddleware

class BalancerTestCase(TestCase):

    def setUp(self):
        self.original_databases = settings.DATABASES
        settings.DATABASES = balancer.TEST_DATABASES

        self.original_master = getattr(settings, 'MASTER_DATABASE', None)
        settings.MASTER_DATABASE = balancer.TEST_MASTER_DATABASE

        self.original_pool = getattr(settings, 'DATABASE_POOL', None)
        settings.DATABASE_POOL = balancer.TEST_DATABASE_POOL

        class MockObj(object):
            class _state:
                db = None

        self.obj1 = MockObj()
        self.obj2 = MockObj()

    def tearDown(self):
        settings.DATABASES = self.original_databases
        settings.MASTER_DATABASE = self.original_master
        settings.DATABASE_POOL = self.original_pool


class RandomRouterTestCase(BalancerTestCase):

    def setUp(self):
        super(RandomRouterTestCase, self).setUp()
        self.router = RandomRouter()

    def test_random_db_selection(self):
        """Simple test to make sure that random database selection works."""
        for i in range(10):
            self.assertTrue(self.router.get_random_db() in
                            settings.DATABASE_POOL.keys(),
                            "The database selected is not in the pool.")

    def test_relations(self):
        """Relations should only be allowed for databases in the pool."""
        self.obj1._state.db = 'default'
        self.obj2._state.db = 'other'
        self.assertTrue(self.router.allow_relation(self.obj1, self.obj2))

        self.obj1._state.db = 'other'
        self.obj2._state.db = 'utility'
        self.assertFalse(self.router.allow_relation(self.obj1, self.obj2))


class RoundRobinRouterTestCase(BalancerTestCase):

    def setUp(self):
        super(RoundRobinRouterTestCase, self).setUp()
        settings.DATABASE_POOL = ['default', 'other', 'utility']
        self.router = RoundRobinRouter()
    
    def test_sequential_db_selection(self):
        """Databases should cycle in order."""
        for i in range(10):
            self.assertEqual(self.router.get_next_db(), self.router.pool[0])
            self.assertEqual(self.router.get_next_db(), self.router.pool[1])
            self.assertEqual(self.router.get_next_db(), self.router.pool[2])


class WeightedRandomRouterTestCase(BalancerTestCase):

    def setUp(self):
        super(WeightedRandomRouterTestCase, self).setUp()
        self.router = WeightedRandomRouter()

    def test_weighted_db_selection(self):
        """
        Make sure that the weights are being applied correctly by checking to
        see if the rate that 'default' is selected is within 0.15 of the target
        rate.
        """
        def check_rate(target):
            hits = {'default': 0, 'other': 0}
            for i in range(1000):
                hits[self.router.get_random_db()] += 1
            rate = round(float(hits['default']) / float(hits['other']), 2)

            self.assertTrue((target - 0.15) <= rate <= (target + 0.15),
                            "The 'default' rate of %s was not close enough to "
                            "the target rate." % rate)

        # The initial target rate is 0.5, because 'default' has a weight of 1
        # and 'other' has a rate of 2 - 'default' should be selected roughly
        # half as much as 'other'.
        check_rate(target=0.5)

        settings.DATABASE_POOL = {
            'default': 1,
            'other': 4,
        }
        # Reinitialize the router with new weights
        self.router = WeightedRandomRouter()
        check_rate(target=0.25)


class MasterSlaveTestMixin(object):
    """A mixin for testing routers that use the MasterSlaveMixin."""
    
    def test_writes(self):
        """Writes should always go to master."""
        self.assertEqual(self.router.db_for_write(self.obj1), 'default')

    def test_relations(self):
        """
        Relations should be allowed for databases in the pool and the master.
        """
        settings.DATABASE_POOL = {
            'other': 1,
            'utility': 1,
        }
        self.router = WeightedRandomRouter()

        # Even though default isn't in the database pool, it is the master so
        # the relation should be allowed.
        self.obj1._state.db = 'default'
        self.obj2._state.db = 'other'
        self.assertTrue(self.router.allow_relation(self.obj1, self.obj2))


class WMSRouterTestCase(MasterSlaveTestMixin, BalancerTestCase):
    """Tests for the WeightedMasterSlaveRouter."""

    def setUp(self):
        super(WMSRouterTestCase, self).setUp()
        self.router = WeightedMasterSlaveRouter()


class RRMSRouterTestCase(MasterSlaveTestMixin, BalancerTestCase):
    """Tests for the RoundRobinMasterSlaveRouter."""
    
    def setUp(self):
        super(RRMSRouterTestCase, self).setUp()
        self.router = RoundRobinMasterSlaveRouter()


class PinningRouterTestMixin(object):
    """A mixin for testing routers that use the pinning mixin."""

    def setUp(self):
        super(PinningRouterTestMixin, self).setUp()
        
        class MockRequest(object):
            COOKIES = []
            method = 'GET'
            session = {}
            
        
        self.mock_request = MockRequest()
        
        class MockResponse(object):
            cookie = None
            
            def set_cookie(self, key, value, max_age):
                self.cookie = key
        
        self.mock_response = MockResponse()

    def test_pinning(self):
        # Check to make sure the 'other' database shows in in reads first
        success = False
        for i in range(100):
            db = self.router.db_for_read(self.obj1)
            if db == 'other':
                success = True
                break
        self.assertTrue(success, "The 'other' database was not offered.")
        
        # Simulate a write
        self.router.db_for_write(self.obj1)
        
        # Check to make sure that only the master database shows up in reads,
        # since the thread should now be pinned
        success = True
        for i in range(100):
            db = self.router.db_for_read(self.obj1)
            if db == 'other':
                success = False
                break
        self.assertTrue(success, "The 'other' database was offered in error.")
        
        pinning.unpin_thread()
        pinning.clear_db_write()
    
    def test_middleware(self):
        for middleware, vehicle in [(PinningSessionMiddleware(), 'session'),
                                    (PinningCookieMiddleware(), 'cookie')]:
            # The first request shouldn't pin the database
            middleware.process_request(self.mock_request)
            self.assertFalse(pinning.thread_is_pinned())
            
            # A simulated write also shouldn't, if the request isn't a POST
            pinning.set_db_write()
            middleware.process_request(self.mock_request)
            self.assertFalse(pinning.thread_is_pinned())
            
            # This response should set the session variable and clear the pin
            pinning.set_db_write()
            self.mock_request.method = 'POST'
            response = middleware.process_response(self.mock_request,
                                                   self.mock_response)
            self.assertFalse(pinning.thread_is_pinned())
            self.assertFalse(pinning.db_was_written())
            if vehicle == 'session':
                self.assertTrue(
                    self.mock_request.session.get(PINNING_KEY, False)
                )
            else:
                self.assertEqual(response.cookie, PINNING_KEY)
                self.mock_request.COOKIES = [response.cookie]
            
            # The subsequent request should then pin the database
            middleware.process_request(self.mock_request)
            self.assertTrue(pinning.thread_is_pinned())
            
            pinning.unpin_thread()
            
            if vehicle == 'session':
                # After the pinning period has expired, the request should no
                # longer pin the thread
                exp = timedelta(seconds=PINNING_SECONDS - 5)
                self.mock_request.session[PINNING_KEY] = datetime.now() - exp
                middleware.process_request(self.mock_request)
                self.assertFalse(pinning.thread_is_pinned())
                
                pinning.unpin_thread()


class PinningWMSRouterTestCase(PinningRouterTestMixin, BalancerTestCase):
    
    def setUp(self):
        super(PinningWMSRouterTestCase, self).setUp()
        self.router = PinningWMSRouter()


class PinningRRMSRouterTestCase(PinningRouterTestMixin, BalancerTestCase):
    
    def setUp(self):
        super(PinningRRMSRouterTestCase, self).setUp()
        self.router = PinningRRMSRouter()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-balancer documentation build configuration file, created by
# sphinx-quickstart on Mon Oct 18 10:17:32 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

DOCS_BASE = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(DOCS_BASE, '..')))

import balancer

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
project = u'django-balancer'
copyright = u'2010, Brandon Konkle'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = balancer.get_version(short=True)
# The full version, including alpha/beta/rc tags.
release = balancer.__version__

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
htmlhelp_basename = 'django-balancerdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-balancer.tex', u'django-balancer Documentation',
   u'Brandon Konkle', 'manual'),
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

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'django-balancer', u'django-balancer Documentation',
     [u'Brandon Konkle'], 1)
]

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
__FILENAME__ = models
from django.db import models

class Test(models.Model):
    name = models.CharField(max_length=100)

class Related(models.Model):
    test = models.ForeignKey(Test)

########NEW FILE########
__FILENAME__ = settings
# Django settings for test_project project.
import os, sys

PROJECT_BASE = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(PROJECT_BASE, '..')))

import balancer

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = balancer.TEST_DATABASES

MASTER_DATABASE = balancer.TEST_MASTER_DATABASE
DATABASE_POOL = balancer.TEST_DATABASE_POOL

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
SECRET_KEY = 'pfiq=i68iilugnk*0c=tc89y188*ha_ut6=)res2#a!h59f_gu'

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

ROOT_URLCONF = 'test_project.urls'

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
    'balancer',
    'test_project',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^test_project/', include('test_project.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
