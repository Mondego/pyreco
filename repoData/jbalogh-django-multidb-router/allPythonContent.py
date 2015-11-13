__FILENAME__ = conf
import sys
import os

sys.path.append(os.path.abspath('..'))

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

extensions = ['sphinx.ext.autodoc']

# General information about the project.
project = u'multidb-router'
copyright = u'2010, The Zamboni Collective'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.2'
# The full version, including alpha/beta/rc tags.
release = '0.2'

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

# The name of the Pygments (syntax highlighting) style to use.
#pygments_style = 'sphinx'

########NEW FILE########
__FILENAME__ = middleware
from django.conf import settings

from .pinning import pin_this_thread, unpin_this_thread


# The name of the cookie that directs a request's reads to the master DB
PINNING_COOKIE = getattr(settings, 'MULTIDB_PINNING_COOKIE',
                         'multidb_pin_writes')


# The number of seconds for which reads are directed to the master DB after a
# write
PINNING_SECONDS = int(getattr(settings, 'MULTIDB_PINNING_SECONDS', 15))


READ_ONLY_METHODS = ('GET', 'TRACE', 'HEAD', 'OPTIONS')


class PinningRouterMiddleware(object):
    """Middleware to support the PinningMasterSlaveRouter

    Attaches a cookie to a user agent who has just written, causing subsequent
    DB reads (for some period of time, hopefully exceeding replication lag)
    to be handled by the master.

    When the cookie is detected on a request, sets a thread-local to alert the
    DB router.

    """
    def process_request(self, request):
        """Set the thread's pinning flag according to the presence of the
        incoming cookie."""
        if (PINNING_COOKIE in request.COOKIES or
                request.method not in READ_ONLY_METHODS):
            pin_this_thread()
        else:
            # In case the last request this thread served was pinned:
            unpin_this_thread()

    def process_response(self, request, response):
        """For some HTTP methods, assume there was a DB write and set the
        cookie.

        Even if it was already set, reset its expiration time.

        """
        if (request.method not in READ_ONLY_METHODS or
                getattr(response, '_db_write', False)):
            response.set_cookie(PINNING_COOKIE, value='y',
                                max_age=PINNING_SECONDS)
        return response

########NEW FILE########
__FILENAME__ = pinning
"""An encapsulated thread-local variable that indicates whether future DB
writes should be "stuck" to the master."""

from functools import wraps
import threading


__all__ = ['this_thread_is_pinned', 'pin_this_thread', 'unpin_this_thread',
           'use_master', 'db_write']


_locals = threading.local()


def this_thread_is_pinned():
    """Return whether the current thread should send all its reads to the
    master DB."""
    return getattr(_locals, 'pinned', False)


def pin_this_thread():
    """Mark this thread as "stuck" to the master for all DB access."""
    _locals.pinned = True


def unpin_this_thread():
    """Unmark this thread as "stuck" to the master for all DB access.

    If the thread wasn't marked, do nothing.

    """
    _locals.pinned = False


class UseMaster(object):
    """A contextmanager/decorator to use the master database."""
    old = False

    def __call__(self, func):
        @wraps(func)
        def decorator(*args, **kw):
            with self:
                return func(*args, **kw)
        return decorator

    def __enter__(self):
        self.old = this_thread_is_pinned()
        pin_this_thread()

    def __exit__(self, type, value, tb):
        if not self.old:
            unpin_this_thread()

use_master = UseMaster()


def mark_as_write(response):
    """Mark a response as having done a DB write."""
    response._db_write = True
    return response


def db_write(fn):
    @wraps(fn)
    def _wrapped(*args, **kw):
        with use_master:
            response = fn(*args, **kw)
        return mark_as_write(response)
    return _wrapped

########NEW FILE########
__FILENAME__ = tests
from django.http import HttpRequest, HttpResponse
from django.test import TestCase

from nose.tools import eq_

from multidb import (DEFAULT_DB_ALIAS, MasterSlaveRouter,
                     PinningMasterSlaveRouter, get_slave)
from multidb.middleware import (PINNING_COOKIE, PINNING_SECONDS,
                                PinningRouterMiddleware)
from multidb.pinning import (this_thread_is_pinned, pin_this_thread,
                             unpin_this_thread, use_master, db_write)


class UnpinningTestCase(TestCase):
    """Test case that unpins the thread on tearDown"""

    def tearDown(self):
        unpin_this_thread()


class MasterSlaveRouterTests(TestCase):
    """Tests for MasterSlaveRouter"""

    def test_db_for_read(self):
        eq_(MasterSlaveRouter().db_for_read(None), get_slave())
        # TODO: Test the round-robin functionality.

    def test_db_for_write(self):
        eq_(MasterSlaveRouter().db_for_write(None), DEFAULT_DB_ALIAS)

    def test_allow_syncdb(self):
        """Make sure allow_syncdb() does the right thing for both masters and
        slaves"""
        router = MasterSlaveRouter()
        assert router.allow_syncdb(DEFAULT_DB_ALIAS, None)
        assert not router.allow_syncdb(get_slave(), None)


class SettingsTests(TestCase):
    """Tests for settings defaults"""

    def test_cookie_default(self):
        """Check that the cookie name has the right default."""
        eq_(PINNING_COOKIE, 'multidb_pin_writes')

    def test_pinning_seconds_default(self):
        """Make sure the cookie age has the right default."""
        eq_(PINNING_SECONDS, 15)


class PinningTests(UnpinningTestCase):
    """Tests for "pinning" functionality, above and beyond what's inherited
    from MasterSlaveRouter"""

    def test_pinning_encapsulation(self):
        """Check the pinning getters and setters."""
        assert not this_thread_is_pinned(), \
            "Thread started out pinned or this_thread_is_pinned() is broken."

        pin_this_thread()
        assert this_thread_is_pinned(), \
            "pin_this_thread() didn't pin the thread."

        unpin_this_thread()
        assert not this_thread_is_pinned(), \
            "Thread remained pinned after unpin_this_thread()."

    def test_pinned_reads(self):
        """Test PinningMasterSlaveRouter.db_for_read() when pinned and when
        not."""
        router = PinningMasterSlaveRouter()

        eq_(router.db_for_read(None), get_slave())

        pin_this_thread()
        eq_(router.db_for_read(None), DEFAULT_DB_ALIAS)

    def test_db_write_decorator(self):

        def read_view(req):
            eq_(router.db_for_read(None), get_slave())
            return HttpResponse()

        @db_write
        def write_view(req):
            eq_(router.db_for_read(None), DEFAULT_DB_ALIAS)
            return HttpResponse()

        router = PinningMasterSlaveRouter()
        eq_(router.db_for_read(None), get_slave())
        write_view(HttpRequest())
        read_view(HttpRequest())


class MiddlewareTests(UnpinningTestCase):
    """Tests for the middleware that supports pinning"""

    def setUp(self):
        super(MiddlewareTests, self).setUp()

        # Every test uses these, so they're okay as attrs.
        self.request = HttpRequest()
        self.middleware = PinningRouterMiddleware()

    def test_pin_on_cookie(self):
        """Thread should pin when the cookie is set."""
        self.request.COOKIES[PINNING_COOKIE] = 'y'
        self.middleware.process_request(self.request)
        assert this_thread_is_pinned()

    def test_unpin_on_no_cookie(self):
        """Thread should unpin when cookie is absent and method is GET."""
        pin_this_thread()
        self.request.method = 'GET'
        self.middleware.process_request(self.request)
        assert not this_thread_is_pinned()

    def test_pin_on_post(self):
        """Thread should pin when method is POST."""
        self.request.method = 'POST'
        self.middleware.process_request(self.request)
        assert this_thread_is_pinned()

    def test_process_response(self):
        """Make sure the cookie gets set on POSTs but not GETs."""

        self.request.method = 'GET'
        response = self.middleware.process_response(
            self.request, HttpResponse())
        assert PINNING_COOKIE not in response.cookies

        self.request.method = 'POST'
        response = self.middleware.process_response(
            self.request, HttpResponse())
        assert PINNING_COOKIE in response.cookies
        eq_(response.cookies[PINNING_COOKIE]['max-age'],
            PINNING_SECONDS)

    def test_attribute(self):
        """The cookie should get set if the _db_write attribute is True."""
        res = HttpResponse()
        res._db_write = True
        response = self.middleware.process_response(self.request, res)
        assert PINNING_COOKIE in response.cookies

    def test_db_write_decorator(self):
        """The @db_write decorator should make any view set the cookie."""
        req = self.request
        req.method = 'GET'

        def view(req):
            return HttpResponse()
        response = self.middleware.process_response(req, view(req))
        assert PINNING_COOKIE not in response.cookies

        @db_write
        def write_view(req):
            return HttpResponse()
        response = self.middleware.process_response(req, write_view(req))
        assert PINNING_COOKIE in response.cookies


class ContextDecoratorTests(TestCase):
    def test_decorator(self):
        @use_master
        def check():
            assert this_thread_is_pinned()
        unpin_this_thread()
        assert not this_thread_is_pinned()
        check()
        assert not this_thread_is_pinned()

    def test_decorator_resets(self):
        @use_master
        def check():
            assert this_thread_is_pinned()
        pin_this_thread()
        assert this_thread_is_pinned()
        check()
        assert this_thread_is_pinned()

    def test_context_manager(self):
        unpin_this_thread()
        assert not this_thread_is_pinned()
        with use_master:
            assert this_thread_is_pinned()
        assert not this_thread_is_pinned()

    def text_context_manager_resets(self):
        pin_this_thread()
        assert this_thread_is_pinned()
        with use_master:
            assert this_thread_is_pinned()
        assert this_thread_is_pinned()

    def test_context_manager_exception(self):
        unpin_this_thread()
        assert not this_thread_is_pinned()
        with self.assertRaises(ValueError):
            with use_master:
                assert this_thread_is_pinned()
                raise ValueError
        assert not this_thread_is_pinned()

########NEW FILE########
__FILENAME__ = test_settings
# A Django settings module to support the tests

SECRET_KEY = 'dummy'
TEST_RUNNER = 'django_nose.runner.NoseTestSuiteRunner'

# The default database should point to the master.
DATABASES = {
    'default': {
        'NAME': 'master',
        'ENGINE': 'django.db.backends.sqlite3',
    },
    'slave': {
        'NAME': 'slave',
        'ENGINE': 'django.db.backends.sqlite3',
    },
}

# Put the aliases for slave databases in this list.
SLAVE_DATABASES = ['slave']

# If you use PinningMasterSlaveRouter and its associated middleware, you can
# customize the cookie name and its lifetime like so:
# MULTIDB_PINNING_COOKIE = 'multidb_pin_writes"
# MULTIDB_PINNING_SECONDS = 15

########NEW FILE########
