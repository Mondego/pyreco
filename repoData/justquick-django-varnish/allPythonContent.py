__FILENAME__ = varnishmgt
from django.core.management.base import BaseCommand
from varnishapp.manager import manager
from pprint import pprint

class Command(BaseCommand):
    def handle(self, *args, **options):
        if args:
            pprint(manager.run(*args))
        else:
            print manager.help()

########NEW FILE########
__FILENAME__ = manager
from varnish import VarnishManager
from django.conf import settings
from atexit import register

manager = VarnishManager(getattr(settings, 'VARNISH_MANAGEMENT_ADDRS', ()))
register(manager.close)
########NEW FILE########
__FILENAME__ = settings

########NEW FILE########
__FILENAME__ = signals
from django.db.models.signals import post_save
from django.db.models import get_model
from django.conf import settings
from manager import manager


def absolute_url_purge_handler(sender, **kwargs):
    manager.run('purge.url', r'^%s$' % kwargs['instance'].get_absolute_url())

for model in getattr(settings, 'VARNISH_WATCHED_MODELS', ()):
    post_save.connect(absolute_url_purge_handler, sender=get_model(*model.split('.')))
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.conf import settings
from manager import VarnishManager


urlpatterns = patterns('varnishapp.views',
    (r'', 'management'),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponseRedirect
from manager import manager
from django.views.generic.simple import direct_to_template
from django.conf import settings

def get_stats():
    stats = [x[0] for x in manager.run('stats')]
    return zip(getattr(settings, 'VARNISH_MANAGEMENT_ADDRS', ()), stats)
    
def management(request): 
    if not request.user.is_superuser:
        return HttpResponseRedirect('/admin/')
    if 'command' in request.REQUEST:
        kwargs = dict(request.REQUEST.items())
        manager.run(*str(kwargs.pop('command')).split(), **kwargs)
        return HttpResponseRedirect(request.path)
    try:
        stats = get_stats()
        errors = {}
    except:
        stats = None
        errors = {"stats":"Impossible to access the stats for server : %s" \
                  %getattr(settings, 'VARNISH_MANAGEMENT_ADDRS', ())}
        
    extra_context = {'stats':stats,
                     'errors':errors}
    return direct_to_template(request, template='varnish/report.html',
                              extra_context=extra_context)

########NEW FILE########
