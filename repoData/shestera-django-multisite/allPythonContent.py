__FILENAME__ = middleware
# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.sites.models import Site

HOST_CACHE = {}

class DynamicSiteMiddleware(object):
    def process_request(self, request):
        host = request.get_host()
        shost = host.rsplit(':', 1)[0] # only host, without port

        try:
            settings.SITE_ID.set(HOST_CACHE[host])
            return
        except KeyError:
            pass

        try: # get by whole hostname
            site = Site.objects.get(domain=host)
            HOST_CACHE[host] = site.pk
            settings.SITE_ID.set(site.pk)
            return
        except Site.DoesNotExist:
            pass

        if shost != host: # get by hostname without port
            try:
                site = Site.objects.get(domain=shost)
                HOST_CACHE[host] = site.pk
                settings.SITE_ID.set(site.pk)
                return
            except Site.DoesNotExist:
                pass

        try: # get by settings.SITE_ID
            site = Site.objects.get(pk=settings.SITE_ID)
            HOST_CACHE[host] = site.pk
            return
        except Site.DoesNotExist:
            pass

        try: # misconfigured settings?
            site = Site.objects.all()[0]
            HOST_CACHE[host] = site.pk
            settings.SITE_ID.set(site.pk)
            return
        except IndexError: # no sites in db
            pass

########NEW FILE########
__FILENAME__ = template_loader
from django.template import TemplateDoesNotExist
from django.utils._os import safe_join
import os.path
from django.contrib.sites.models import Site
from django.conf import settings

def get_template_sources(template_name, template_dirs=None):
    template_dir = os.path.join(settings.TEMPLATE_DIRS[0], Site.objects.get_current().domain)
    try:
        yield safe_join(template_dir, template_name)
    except UnicodeDecodeError:
        raise
    except ValueError:
        pass

def load_template_source(template_name, template_dirs=None):
    tried = []
    for filepath in get_template_sources(template_name, template_dirs):
        try:
            return (open(filepath).read().decode(settings.FILE_CHARSET), filepath)
        except IOError:
            tried.append(filepath)
    if tried:
        error_msg = "Tried %s" % tried
    else:
        error_msg = "Your TEMPLATE_DIRS setting is empty. Change it to point to at least one template directory."
    raise TemplateDoesNotExist, error_msg
load_template_source.is_usable = True

########NEW FILE########
__FILENAME__ = threadlocals
# -*- coding: utf-8 -*

try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local

_thread_locals = local()

def get_request():
    return getattr(_thread_locals, 'request', None)

class ThreadLocalsMiddleware(object):
    """Middleware that saves request in thread local starage"""
    def process_request(self, request):
        _thread_locals.request = request


class SiteIDHook(object):
    def __repr__(self):
        return str(self.__int__())

    def __int__(self):
        try:
            return _thread_locals.SITE_ID
        except AttributeError:
            _thread_locals.SITE_ID = 1
            return _thread_locals.SITE_ID

    def __hash__(self):
        return self.__int__()

    def set(self, value):
        _thread_locals.SITE_ID = value

########NEW FILE########
