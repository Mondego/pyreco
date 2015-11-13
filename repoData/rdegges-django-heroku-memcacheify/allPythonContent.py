__FILENAME__ = memcacheify
from os import environ


# Memcache addon environment variables.
# See: https://addons.heroku.com/memcache
MEMCACHE_ENV_VARS = (
    'MEMCACHE_PASSWORD',
    'MEMCACHE_SERVERS',
    'MEMCACHE_USERNAME',
)


# MemCachier addon environment variables.
# See: https://addons.heroku.com/memcachier
MEMCACHIER_ENV_VARS = (
    'MEMCACHIER_PASSWORD',
    'MEMCACHIER_SERVERS',
    'MEMCACHIER_USERNAME',
)


def memcacheify(timeout=500):
    """Return a fully configured Django ``CACHES`` setting. We do this by
    analyzing all environment variables on Heorku, scanning for an available
    memcache addon, and then building the settings dict properly.

    If no memcache servers can be found, we'll revert to building a local
    memory cache.

    Returns a fully configured caches dict.
    """
    caches = {}

    if all((environ.get(e, '') for e in MEMCACHE_ENV_VARS)):
        caches['default'] = {
            'BACKEND': 'django_pylibmc.memcached.PyLibMCCache',
            'BINARY': True,
            'LOCATION': 'localhost:11211',
            'OPTIONS': {
                'ketama': True,
                'tcp_nodelay': True,
            },
            'TIMEOUT': timeout,
        }
    elif all((environ.get(e, '') for e in MEMCACHIER_ENV_VARS)):
        environ['MEMCACHE_SERVERS'] = environ.get('MEMCACHIER_SERVERS').replace(',', ';')
        environ['MEMCACHE_USERNAME'] = environ.get('MEMCACHIER_USERNAME')
        environ['MEMCACHE_PASSWORD'] = environ.get('MEMCACHIER_PASSWORD')
        caches['default'] = {
            'BACKEND': 'django_pylibmc.memcached.PyLibMCCache',
            'BINARY': True,
            'LOCATION': environ.get('MEMCACHIER_SERVERS').replace(',', ';'),
            'OPTIONS': {
                'ketama': True,
                'tcp_nodelay': True,
            },
            'TIMEOUT': timeout,
        }
    elif environ.get('MEMCACHEIFY_USE_LOCAL', False):
        caches['default'] = {
            'BACKEND': 'django_pylibmc.memcached.PyLibMCCache',
        }
    else:
        caches['default'] = {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }

    return caches

########NEW FILE########
__FILENAME__ = tests
from os import environ
from unittest import TestCase

from memcacheify import memcacheify


class Memcacheify(TestCase):

    def test_uses_local_memory_backend_if_no_memcache_addon_is_available(self):
        self.assertEqual(memcacheify(), {'default':
            {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}
        })

    def tests_uses_local_memory_backend_if_one_of_the_memcache_env_vars_is_missing(self):
        environ['MEMCACHE_PASSWORD'] = 'GCnQ9DhfEJqNDlo1'
        environ['MEMCACHE_SERVERS'] = 'mc3.ec2.northscale.net'
        self.assertEqual(memcacheify(), {'default':
            {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}
        })
        del environ['MEMCACHE_PASSWORD']
        del environ['MEMCACHE_SERVERS']

    def test_sets_proper_backend_when_memcache_addon_is_available(self):
        environ['MEMCACHE_PASSWORD'] = 'GCnQ9DhfEJqNDlo1'
        environ['MEMCACHE_SERVERS'] = 'mc3.ec2.northscale.net'
        environ['MEMCACHE_USERNAME'] = 'appxxxxx%40heroku.com'
        self.assertEqual(memcacheify()['default']['BACKEND'],
                'django_pylibmc.memcached.PyLibMCCache')
        del environ['MEMCACHE_PASSWORD']
        del environ['MEMCACHE_SERVERS']
        del environ['MEMCACHE_USERNAME']

    def test_uses_local_memory_backend_if_no_memcachier_addon_is_available(self):
        environ['MEMCACHIER_PASSWORD'] = 'xxx'
        environ['MEMCACHIER_SERVERS'] = 'mc1.ec2.memcachier.com'
        self.assertEqual(memcacheify(), {'default':
            {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}
        })
        del environ['MEMCACHIER_PASSWORD']
        del environ['MEMCACHIER_SERVERS']

    def test_sets_proper_backend_when_memcachier_addon_is_available(self):
        environ['MEMCACHIER_PASSWORD'] = 'xxx'
        environ['MEMCACHIER_SERVERS'] = 'mc1.ec2.memcachier.com'
        environ['MEMCACHIER_USERNAME'] = 'xxx'

        caches = memcacheify()
        self.assertEqual(caches['default']['BACKEND'], 'django_pylibmc.memcached.PyLibMCCache')
        self.assertEqual(environ['MEMCACHE_SERVERS'], environ['MEMCACHIER_SERVERS'])
        self.assertEqual(environ['MEMCACHE_USERNAME'], environ['MEMCACHIER_USERNAME'])
        self.assertEqual(environ['MEMCACHE_PASSWORD'], environ['MEMCACHIER_PASSWORD'])

        del environ['MEMCACHIER_PASSWORD']
        del environ['MEMCACHIER_SERVERS']
        del environ['MEMCACHIER_USERNAME']
        del environ['MEMCACHE_PASSWORD']
        del environ['MEMCACHE_SERVERS']
        del environ['MEMCACHE_USERNAME']

########NEW FILE########
