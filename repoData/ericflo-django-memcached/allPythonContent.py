__FILENAME__ = models
# None :)
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^$', 'django_memcached.views.server_list'),
    (r'^(\d+)/$', 'django_memcached.views.server_status'),
)

########NEW FILE########
__FILENAME__ = util
import datetime

try:
    import memcache
    memcache_installed = True
except ImportError:
    memcache_installed = False

def get_memcached_stats(server):
    if not memcache_installed:
        return {}
    host = memcache._Host(server)
    host.connect()
    host.send_cmd("stats")
    
    stats = {}
    
    while True:
        try:
            stat, key, value = host.readline().split(None, 2)
        except ValueError:
            break
        try:
            # Convert to native type, if possible
            value = int(value)
            if key == "uptime":
                value = datetime.timedelta(seconds=value)
            elif key == "time":
                value = datetime.datetime.fromtimestamp(value)
        except ValueError:
            pass
        stats[key] = value

    host.close_socket()
    
    try:
        stats['hit_rate'] = 100 * stats['get_hits'] / stats['cmd_get']
    except ZeroDivisionError:
        stats['hit_rate'] = stats['get_hits']
    
    return stats
########NEW FILE########
__FILENAME__ = views
from django.http import Http404
from django.shortcuts import render_to_response
from django.conf import settings
from django.template import RequestContext
from django.core.cache import parse_backend_uri

from django_memcached.util import get_memcached_stats
from django.contrib.auth.decorators import user_passes_test

_, hosts, _ = parse_backend_uri(settings.CACHE_BACKEND)
SERVERS = hosts.split(';')

def server_list(request):
    statuses = zip(range(len(SERVERS)), SERVERS, map(get_memcached_stats, SERVERS))
    context = {
        'statuses': statuses,
    }
    return render_to_response(
        'memcached/server_list.html',
        context,
        context_instance=RequestContext(request)
    )

def server_status(request, index):
    try:
        index = int(index)
    except ValueError:
        raise Http404
    if 'memcached' not in settings.CACHE_BACKEND:
        raise Http404
    if not SERVERS:
        raise Http404
    try:
        server = SERVERS[index]
    except IndexError:
        raise Http404
    stats = get_memcached_stats(server)
    if not stats:
        raise Http404
    context = {
        'server': server,
        'stats': stats.items(),
    }
    return render_to_response(
        'memcached/server_status.html',
        context,
        context_instance=RequestContext(request)
    )

if getattr(settings, 'DJANGO_MEMCACHED_REQUIRE_STAFF', False):
    server_list = user_passes_test(lambda u: u.is_staff)(server_list)
    server_status = user_passes_test(lambda u: u.is_staff)(server_status)

########NEW FILE########
