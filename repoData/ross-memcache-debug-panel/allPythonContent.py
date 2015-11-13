__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^$', 'demo.views.index', {}, 'index'),
    url(r'^cached$', 'demo.views.cached', {}, 'cached'),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
from django.views.decorators.cache import cache_page
from django.core.cache import cache

def index(request, **kwargs):
    cache.get('key')
    cache.get('key2')
    try:
        cache.incr('hello')
    except:
        pass
    return render_to_response('demo/index.html')

@cache_page(60 * 15, key_prefix='demo')
def cached(request, **kwargs):
    return index(request, **kwargs)

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
# Django settings for examples project.

import sys
from os.path import dirname, join
import logging
logging.basicConfig(level=logging.DEBUG)

# add our parent directory to the path so that we can find memcache_toolbar
sys.path.append('../')

# in order to track django's caching we need to import the panels code now
# so that it can swap out the client with one that tracks usage.
import memcache_toolbar.panels.memcache
# if you're using pylibmc use the following instead
#import memcache_toolbar.panels.pylibmc

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'examples.sqlite3',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

CACHE_BACKEND = 'memcached://127.0.0.1:11211/'

TIME_ZONE = 'UTC'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True
USE_L10N = True
SECRET_KEY = 'rfca2x2s3465+3+=-6m!(!f3%nvy^d@g0_ykgawt*%6exoe3ti'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

ROOT_URLCONF = 'examples.urls'

TEMPLATE_DIRS = (
        join(dirname(__file__), 'templates')
)

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    # external app
    'debug_toolbar',
    'memcache_toolbar',
    # apps
    'demo',
)

DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.version.VersionDebugPanel',
    'debug_toolbar.panels.timer.TimerDebugPanel',
    'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
    'debug_toolbar.panels.headers.HeaderDebugPanel',
    'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
    'debug_toolbar.panels.template.TemplateDebugPanel',
    'debug_toolbar.panels.sql.SQLDebugPanel',
    'debug_toolbar.panels.signals.SignalDebugPanel',
    'debug_toolbar.panels.logger.LoggingPanel',
    'memcache_toolbar.panels.memcache.MemcachePanel',
    # if you use pyibmc you'd include it's panel instead
    #'memcache_toolbar.panels.pylibmc.PylibmcPanel',
)

DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: True
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^', include('examples.demo.urls')),
)

########NEW FILE########
__FILENAME__ = memcache
# work around modules with the same name
from __future__ import absolute_import

from memcache_toolbar.panels import BasePanel, record
import logging

DEBUG = False

logger = logging.getLogger(__name__)
try:
    import memcache as memc

    origClient = None

    class TrackingMemcacheClient(memc.Client):

        @record
        def flush_all(self, *args, **kwargs):
            return origClient.flush_all(self, *args, **kwargs)

        @record
        def delete_multi(self, *args, **kwargs):
            return origClient.delete_multi(self, *args, **kwargs)

        @record
        def delete(self, *args, **kwargs):
            return origClient.delete(self, *args, **kwargs)

        @record
        def incr(self, *args, **kwargs):
            return origClient.incr(self, *args, **kwargs)

        @record
        def decr(self, *args, **kwargs):
            return origClient.decr(self, *args, **kwargs)

        @record
        def add(self, *args, **kwargs):
            return origClient.add(self, *args, **kwargs)

        @record
        def append(self, *args, **kwargs):
            return origClient.append(self, *args, **kwargs)

        @record
        def prepend(self, *args, **kwargs):
            return origClient.prepend(self, *args, **kwargs)

        @record
        def replace(self, *args, **kwargs):
            return origClient.replace(self, *args, **kwargs)

        @record
        def set(self, *args, **kwargs):
            return origClient.set(self, *args, **kwargs)

        @record
        def cas(self, *args, **kwargs):
            return origClient.cas(self, *args, **kwargs)

        @record
        def set_multi(self, *args, **kwargs):
            return origClient.set_multi(self, *args, **kwargs)

        @record
        def get(self, *args, **kwargs):
            return origClient.get(self, *args, **kwargs)

        @record
        def gets(self, *args, **kwargs):
            return origClient.gets(self, *args, **kwargs)

        @record
        def get_multi(self, *args, **kwargs):
            return origClient.get_multi(self, *args, **kwargs)

    # NOTE issubclass is true of both are the same class
    if not issubclass(memc.Client, TrackingMemcacheClient):
        logger.debug('installing memcache.Client with tracking')
        origClient = memc.Client
        memc.Client = TrackingMemcacheClient

except:
    if DEBUG:
        logger.exception('unable to install memcache.Client with tracking')
    else:
        logger.debug('unable to install memcache.Client with tracking')


class MemcachePanel(BasePanel):
    pass

########NEW FILE########
__FILENAME__ = pylibmc
# work around modules with the same name
from __future__ import absolute_import

from memcache_toolbar.panels import BasePanel, record
import logging

DEBUG = False

logger = logging.getLogger(__name__)
try:
    import pylibmc
    import _pylibmc

    # duplicating the client code sucks so hard, but it's necessary since the
    # original uses super and we'd need to inherit from it and then replace it
    # resulting in a class that inherits from itself :( see
    # http://fuhm.net/super-harmful/ anyway, see the bottom of this class for
    # the methods we're installing tracking on
    class TrackingPylibmcClient(_pylibmc.client):
        def __init__(self, servers, binary=False):
            """Initialize a memcached client instance.

            This connects to the servers in *servers*, which will default to being
            TCP servers. If it looks like a filesystem path, a UNIX socket. If
            prefixed with `udp:`, a UDP connection.

            If *binary* is True, the binary memcached protocol is used.
            """
            self.binary = binary
            self.addresses = list(servers)
            addr_tups = []
            for server in servers:
                addr = server
                port = 11211
                if server.startswith("udp:"):
                    stype = _pylibmc.server_type_udp
                    addr = addr[4:]
                    if ":" in server:
                        (addr, port) = addr.split(":", 1)
                        port = int(port)
                elif ":" in server:
                    stype = _pylibmc.server_type_tcp
                    (addr, port) = server.split(":", 1)
                    port = int(port)
                elif "/" in server:
                    stype = _pylibmc.server_type_unix
                    port = 0
                else:
                    stype = _pylibmc.server_type_tcp
                addr_tups.append((stype, addr, port))
            _pylibmc.client.__init__(self, servers=addr_tups, binary=binary)

        def __repr__(self):
            return "%s(%r, binary=%r)" % (self.__class__.__name__,
                                          self.addresses, self.binary)

        def __str__(self):
            addrs = ", ".join(map(str, self.addresses))
            return "<%s for %s, binary=%r>" % (self.__class__.__name__,
                                               addrs, self.binary)

        def get_behaviors(self):
            """Gets the behaviors from the underlying C client instance.

            Reverses the integer constants for `hash` and `distribution` into more
            understandable string values. See *set_behaviors* for info.
            """
            bvrs = _pylibmc.client.get_behaviors(self)
            bvrs["hash"] = hashers_rvs[bvrs["hash"]]
            bvrs["distribution"] = distributions_rvs[bvrs["distribution"]]
            return BehaviorDict(self, bvrs)

        def set_behaviors(self, behaviors):
            """Sets the behaviors on the underlying C client instance.

            Takes care of morphing the `hash` key, if specified, into the
            corresponding integer constant (which the C client expects.) If,
            however, an unknown value is specified, it's passed on to the C client
            (where it most surely will error out.)

            This also happens for `distribution`.
            """
            behaviors = behaviors.copy()
            if behaviors.get("hash") is not None:
                behaviors["hash"] = hashers[behaviors["hash"]]
            if behaviors.get("ketama_hash") is not None:
                behaviors["ketama_hash"] = hashers[behaviors["ketama_hash"]]
            if behaviors.get("distribution") is not None:
                behaviors["distribution"] = distributions[behaviors["distribution"]]
            return _pylibmc.client.set_behaviors(self, behaviors)

        behaviors = property(get_behaviors, set_behaviors)
        @property
        def behaviours(self):
            raise AttributeError("nobody uses british spellings")

        # methods we're adding tracking to

        @record
        def get(self, *args, **kwargs):
            return _pylibmc.client.get(self, *args, **kwargs)

        @record
        def get_multi(self, *args, **kwargs):
            return _pylibmc.client.get_multi(self, *args, **kwargs)

        @record
        def set(self, *args, **kwargs):
            return _pylibmc.client.set(self, *args, **kwargs)

        @record
        def set_multi(self, *args, **kwargs):
            return _pylibmc.client.set_multi(self, *args, **kwargs)

        @record
        def add(self, *args, **kwargs):
            return _pylibmc.client.add(self, *args, **kwargs)

        @record
        def replace(self, *args, **kwargs):
            return _pylibmc.client.replace(self, *args, **kwargs)

        @record
        def append(self, *args, **kwargs):
            return _pylibmc.client.append(self, *args, **kwargs)

        @record
        def prepend(self, *args, **kwargs):
            return _pylibmc.client.prepend(self, *args, **kwargs)

        @record
        def incr(self, *args, **kwargs):
            return _pylibmc.client.incr(self, *args, **kwargs)

        @record
        def decr(self, *args, **kwargs):
            return _pylibmc.client.decr(self, *args, **kwargs)

        @record
        def delete(self, *args, **kwargs):
            return _pylibmc.client.delete(self, *args, **kwargs)

        # NOTE delete_multi is implemented by iterative over args calling delete
        # for each one. i could probably hide that here, but i actually think
        # it's best to show it since each one will be a seperate network
        # round-trip.
        @record
        def delete_multi(self, *args, **kwargs):
            return _pylibmc.client.delete_multi(self, *args, **kwargs)

        @record
        def flush_all(self, *args, **kwargs):
            return _pylibmc.client.flush_all(self, *args, **kwargs)

    # NOTE issubclass is true of both are the same class
    if not issubclass(pylibmc.Client, TrackingPylibmcClient):
        logger.debug('installing pylibmc.Client with tracking')
        pylibmc.Client = TrackingPylibmcClient

except:
    if DEBUG:
        logger.exception('unable to install pylibmc.Client with tracking')
    else:
        logger.debug('unable to install pylibmc.Client with tracking')


class PylibmcPanel(BasePanel):
    pass

########NEW FILE########
