__FILENAME__ = admin
from django.contrib import admin

admin.site.index_template = 'memcache_status/index.html'
########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = memcache_status_tags
from django import template
from django.conf import settings
from django.core.cache import get_cache

if get_cache.__module__.startswith('debug_toolbar'):
    from debug_toolbar.panels.cache import base_get_cache as get_cache

register = template.Library()

class CacheStats(template.Node):
    """
    Reads the cache stats out of the memcached cache backend. Returns `None`
    if no cache stats supported.
    """
    def render(self, context):
        cache_stats = []
        for cache_backend_nm, cache_backend_attrs in settings.CACHES.iteritems():
            try:
                cache_backend = get_cache(cache_backend_nm)
                this_backend_stats = cache_backend._cache.get_stats()
                # returns list of (name, stats) tuples
                for server_name, server_stats in this_backend_stats:
                    cache_stats.append(("%s: %s" % (
                        cache_backend_nm, server_name), server_stats))
            except AttributeError: # this backend probably doesn't support that
                continue
        context['cache_stats'] = cache_stats
        return ''

@register.tag
def get_cache_stats(parser, token):
    return CacheStats()

@register.filter
def prettyname(name):
    return ' '.join([word.capitalize() for word in name.split('_')])

@register.filter
def prettyvalue(value, key):
    return PrettyValue().format(key, value)

class PrettyValue(object):
    """
    Helper class that reformats the value. Looks for a method named
    ``format_<key>_value`` and returns that value. Returns the value
    as is, if no format method is found.
    """

    def format(self, key, value):
        try:
            func = getattr(self, 'format_%s_value' % key.lower())
            return func(value)
        except AttributeError:
            return value

    def format_limit_maxbytes_value(self, value):
        return "%s (%s)" % (value, self.human_bytes(value))

    def format_bytes_read_value(self, value):
        return "%s (%s)" % (value, self.human_bytes(value))

    def format_bytes_written_value(self, value):
        return "%s (%s)" % (value, self.human_bytes(value))

    def format_uptime_value(self, value):
        return self.fract_timestamp(int(value))

    def format_time_value(self, value):
        from datetime import datetime
        return datetime.fromtimestamp(int(value)).strftime('%x %X')

    def fract_timestamp(self, s):
        years, s = divmod(s, 31556952)
        min, s = divmod(s, 60)
        h, min = divmod(min, 60)
        d, h = divmod(h, 24)
        return '%sy, %sd, %sh, %sm, %ss' % (years, d, h, min, s)

    def human_bytes(self, bytes):
        bytes = float(bytes)
        if bytes >= 1073741824:
            gigabytes = bytes / 1073741824
            size = '%.2fGB' % gigabytes
        elif bytes >= 1048576:
            megabytes = bytes / 1048576
            size = '%.2fMB' % megabytes
        elif bytes >= 1024:
            kilobytes = bytes / 1024
            size = '%.2fKB' % kilobytes
        else:
            size = '%.2fB' % bytes
        return size

########NEW FILE########
__FILENAME__ = test_admin
from django.contrib.auth.models import User
from django.test import TestCase


class MemcacheStatusSanityTests(TestCase):
    urls = 'memcache_status.tests.test_urls'

    def setUp(self):
        self.user = User.objects.create_superuser('test', 'test@test.com', 'password')
        self.client.login(username=self.user.username, password='password')

    def test_admin_accessible(self):
        response = self.client.get('/admin/')
        self.assertEqual(200, response.status_code)

    def test_cache_stats_included(self):
        response = self.client.get('/admin/')
        self.assertIn('class="cache_stats"', response.content)


class MemcacheStatusPermissionsTests(TestCase):
    urls = 'memcache_status.tests.test_urls'

    def test_non_superuser_cant_see_stats(self):
        self.user = User.objects.create_user('test', 'test@test.com', 'password')
        self.client.login(username=self.user.username, password='password')
        response = self.client.get('/admin/')
        self.assertNotIn('class="cache_stats"', response.content)

########NEW FILE########
__FILENAME__ = test_urls
try:
    from django.conf.urls import patterns, include, url
except ImportError:
    from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import sys
from django.conf import settings
from django.core.management import execute_from_command_line

if not settings.configured:
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            },
        },
        INSTALLED_APPS=(
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'memcache_status',
        ),
        ROOT_URLCONF=None,
        SECRET_KEY='foobar',
        CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
                'LOCATION': '127.0.0.1:11211',
            }
        }
    )


def runtests():
    argv = sys.argv[:1] + ['test'] + sys.argv[1:] + ['memcache_status']
    execute_from_command_line(argv)


if __name__ == '__main__':
    runtests()
########NEW FILE########
