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
# Django settings for demo project.
import os
DIRNAME = os.path.abspath(os.path.dirname(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'demo.db',                      # Or path to database file if using sqlite3.
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

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(DIRNAME, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/static/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '#!t86#t9)m6zhx$3&3ke1o2gsog6zhj5b+w9g&uf^@rp-_6z4m'

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
    'tracking.middleware.VisitorTrackingMiddleware',
    'tracking.middleware.VisitorCleanUpMiddleware',
    'tracking.middleware.BannedIPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'demo.urls'

TEMPLATE_DIRS = (
    os.path.join(DIRNAME, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'tracking'
)

GOOGLE_MAPS_KEY = 'ABQIAAAAaP6spDi8OofHsLmWK8bZEhQCULP4XOMyhPd8d_NrQQEO8sT8XBQD-q-healg6KF2Fcm1SDbZ8VG7sw'
TRACKING_USE_GEOIP = True
GEOIP_PATH = os.path.join(DIRNAME, 'GeoLiteCity.dat')
TRACKING_TIMEOUT = 5 # in minutes
TRACKING_CLEANUP_TIMEOUT = 5 # in hours
NO_TRACKING_PREFIXES = [
    '/media/',
    '/admin/',
]

import logging
logging.basicConfig(filename='tracking.log', level=logging.DEBUG)

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    (r'^tracking/', include('tracking.urls')),
    (r'^admin/', include(admin.site.urls)),
)

if settings.DEBUG:
    urlpatterns += patterns('django.views.static',
        (r'static/(?P<path>.*)$', 'serve', {'document_root': settings.MEDIA_ROOT}),
    )

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from tracking.models import BannedIP, UntrackedUserAgent

admin.site.register(BannedIP)
admin.site.register(UntrackedUserAgent)
########NEW FILE########
__FILENAME__ = listeners
import logging

log = logging.getLogger('tracking.listeners')

try:
    from django.core.cache import cache
    from django.db.models.signals import post_save, post_delete

    from tracking.models import UntrackedUserAgent, BannedIP
except ImportError:
    pass
else:

    def refresh_untracked_user_agents(sender, instance, created=False, **kwargs):
        """Updates the cache of user agents that we don't track"""

        log.debug('Updating untracked user agents cache')
        cache.set('_tracking_untracked_uas',
            UntrackedUserAgent.objects.all(),
            3600)

    def refresh_banned_ips(sender, instance, created=False, **kwargs):
        """Updates the cache of banned IP addresses"""

        log.debug('Updating banned IP cache')
        cache.set('_tracking_banned_ips',
            [b.ip_address for b in BannedIP.objects.all()],
            3600)

    post_save.connect(refresh_untracked_user_agents, sender=UntrackedUserAgent)
    post_delete.connect(refresh_untracked_user_agents, sender=UntrackedUserAgent)

    post_save.connect(refresh_banned_ips, sender=BannedIP)
    post_delete.connect(refresh_banned_ips, sender=BannedIP)

########NEW FILE########
__FILENAME__ = middleware
from datetime import datetime, timedelta
import logging
import re
import traceback

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.urlresolvers import reverse, NoReverseMatch
from django.db.utils import DatabaseError
from django.http import Http404

from tracking import utils
from tracking.models import Visitor, UntrackedUserAgent, BannedIP

title_re = re.compile('<title>(.*?)</title>')
log = logging.getLogger('tracking.middleware')

class VisitorTrackingMiddleware(object):
    """
    Keeps track of your active users.  Anytime a visitor accesses a valid URL,
    their unique record will be updated with the page they're on and the last
    time they requested a page.

    Records are considered to be unique when the session key and IP address
    are unique together.  Sometimes the same user used to have two different
    records, so I added a check to see if the session key had changed for the
    same IP and user agent in the last 5 minutes
    """

    @property
    def prefixes(self):
        """Returns a list of URL prefixes that we should not track"""

        if not hasattr(self, '_prefixes'):
            self._prefixes = getattr(settings, 'NO_TRACKING_PREFIXES', [])

            if not getattr(settings, '_FREEZE_TRACKING_PREFIXES', False):
                for name in ('MEDIA_URL', 'STATIC_URL'):
                    url = getattr(settings, name)
                    if url and url != '/':
                        self._prefixes.append(url)

                try:
                    # finally, don't track requests to the tracker update pages
                    self._prefixes.append(reverse('tracking-refresh-active-users'))
                except NoReverseMatch:
                    # django-tracking hasn't been included in the URLconf if we
                    # get here, which is not a bad thing
                    pass

                settings.NO_TRACKING_PREFIXES = self._prefixes
                settings._FREEZE_TRACKING_PREFIXES = True

        return self._prefixes

    def process_request(self, request):
        # don't process AJAX requests
        if request.is_ajax(): return

        # create some useful variables
        ip_address = utils.get_ip(request)
        user_agent = unicode(request.META.get('HTTP_USER_AGENT', '')[:255], errors='ignore')

        # retrieve untracked user agents from cache
        ua_key = '_tracking_untracked_uas'
        untracked = cache.get(ua_key)
        if untracked is None:
            log.info('Updating untracked user agent cache')
            untracked = UntrackedUserAgent.objects.all()
            cache.set(ua_key, untracked, 3600)

        # see if the user agent is not supposed to be tracked
        for ua in untracked:
            # if the keyword is found in the user agent, stop tracking
            if user_agent.find(ua.keyword) != -1:
                log.debug('Not tracking UA "%s" because of keyword: %s' % (user_agent, ua.keyword))
                return

        if hasattr(request, 'session') and request.session.session_key:
            # use the current session key if we can
            session_key = request.session.session_key
        else:
            # otherwise just fake a session key
            session_key = '%s:%s' % (ip_address, user_agent)
            session_key = session_key[:40]

        # ensure that the request.path does not begin with any of the prefixes
        for prefix in self.prefixes:
            if request.path.startswith(prefix):
                log.debug('Not tracking request to: %s' % request.path)
                return

        # if we get here, the URL needs to be tracked
        # determine what time it is
        now = datetime.now()

        attrs = {
            'session_key': session_key,
            'ip_address': ip_address
        }

        # for some reason, Visitor.objects.get_or_create was not working here
        try:
            visitor = Visitor.objects.get(**attrs)
        except Visitor.DoesNotExist:
            # see if there's a visitor with the same IP and user agent
            # within the last 5 minutes
            cutoff = now - timedelta(minutes=5)
            visitors = Visitor.objects.filter(
                ip_address=ip_address,
                user_agent=user_agent,
                last_update__gte=cutoff
            )

            if len(visitors):
                visitor = visitors[0]
                visitor.session_key = session_key
                log.debug('Using existing visitor for IP %s / UA %s: %s' % (ip_address, user_agent, visitor.id))
            else:
                # it's probably safe to assume that the visitor is brand new
                visitor = Visitor(**attrs)
                log.debug('Created a new visitor: %s' % attrs)
        except:
            return

        # determine whether or not the user is logged in
        user = request.user
        if isinstance(user, AnonymousUser):
            user = None

        # update the tracking information
        visitor.user = user
        visitor.user_agent = user_agent

        # if the visitor record is new, or the visitor hasn't been here for
        # at least an hour, update their referrer URL
        one_hour_ago = now - timedelta(hours=1)
        if not visitor.last_update or visitor.last_update <= one_hour_ago:
            visitor.referrer = utils.u_clean(request.META.get('HTTP_REFERER', 'unknown')[:255])

            # reset the number of pages they've been to
            visitor.page_views = 0
            visitor.session_start = now

        visitor.url = request.path
        visitor.page_views += 1
        visitor.last_update = now
        try:
            visitor.save()
        except DatabaseError:
            log.error('There was a problem saving visitor information:\n%s\n\n%s' % (traceback.format_exc(), locals()))

class VisitorCleanUpMiddleware:
    """Clean up old visitor tracking records in the database"""

    def process_request(self, request):
        timeout = utils.get_cleanup_timeout()

        if str(timeout).isdigit():
            log.debug('Cleaning up visitors older than %s hours' % timeout)
            timeout = datetime.now() - timedelta(hours=int(timeout))
            Visitor.objects.filter(last_update__lte=timeout).delete()

class BannedIPMiddleware:
    """
    Raises an Http404 error for any page request from a banned IP.  IP addresses
    may be added to the list of banned IPs via the Django admin.

    The banned users do not actually receive the 404 error--instead they get
    an "Internal Server Error", effectively eliminating any access to the site.
    """

    def process_request(self, request):
        key = '_tracking_banned_ips'
        ips = cache.get(key)
        if ips is None:
            # compile a list of all banned IP addresses
            log.info('Updating banned IPs cache')
            ips = [b.ip_address for b in BannedIP.objects.all()]
            cache.set(key, ips, 3600)

        # check to see if the current user's IP address is in that list
        if utils.get_ip(request) in ips:
            raise Http404

########NEW FILE########
__FILENAME__ = models
from datetime import datetime, timedelta
import logging
import traceback

from django.contrib.gis.utils import HAS_GEOIP

if HAS_GEOIP:
    from django.contrib.gis.utils import GeoIP, GeoIPException

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _
from tracking import utils

USE_GEOIP = getattr(settings, 'TRACKING_USE_GEOIP', False)
CACHE_TYPE = getattr(settings, 'GEOIP_CACHE_TYPE', 4)

log = logging.getLogger('tracking.models')

class VisitorManager(models.Manager):
    def active(self, timeout=None):
        """
        Retrieves only visitors who have been active within the timeout
        period.
        """
        if not timeout:
            timeout = utils.get_timeout()

        now = datetime.now()
        cutoff = now - timedelta(minutes=timeout)

        return self.get_query_set().filter(last_update__gte=cutoff)

class Visitor(models.Model):
    session_key = models.CharField(max_length=40)
    ip_address = models.CharField(max_length=20)
    user = models.ForeignKey(User, null=True)
    user_agent = models.CharField(max_length=255)
    referrer = models.CharField(max_length=255)
    url = models.CharField(max_length=255)
    page_views = models.PositiveIntegerField(default=0)
    session_start = models.DateTimeField()
    last_update = models.DateTimeField()

    objects = VisitorManager()

    def _time_on_site(self):
        """
        Attempts to determine the amount of time a visitor has spent on the
        site based upon their information that's in the database.
        """
        if self.session_start:
            seconds = (self.last_update - self.session_start).seconds

            hours = seconds / 3600
            seconds -= hours * 3600
            minutes = seconds / 60
            seconds -= minutes * 60

            return u'%i:%02i:%02i' % (hours, minutes, seconds)
        else:
            return ugettext(u'unknown')
    time_on_site = property(_time_on_site)

    def _get_geoip_data(self):
        """
        Attempts to retrieve MaxMind GeoIP data based upon the visitor's IP
        """

        if not HAS_GEOIP or not USE_GEOIP:
            # go no further when we don't need to
            log.debug('Bailing out.  HAS_GEOIP: %s; TRACKING_USE_GEOIP: %s' % (HAS_GEOIP, USE_GEOIP))
            return None

        if not hasattr(self, '_geoip_data'):
            self._geoip_data = None
            try:
                gip = GeoIP(cache=CACHE_TYPE)
                self._geoip_data = gip.city(self.ip_address)
            except GeoIPException:
                # don't even bother...
                log.error('Error getting GeoIP data for IP "%s": %s' % (self.ip_address, traceback.format_exc()))

        return self._geoip_data

    geoip_data = property(_get_geoip_data)

    def _get_geoip_data_json(self):
        """
        Cleans out any dirty unicode characters to make the geoip data safe for
        JSON encoding.
        """
        clean = {}
        if not self.geoip_data: return {}

        for key,value in self.geoip_data.items():
            clean[key] = utils.u_clean(value)
        return clean

    geoip_data_json = property(_get_geoip_data_json)

    class Meta:
        ordering = ('-last_update',)
        unique_together = ('session_key', 'ip_address',)

class UntrackedUserAgent(models.Model):
    keyword = models.CharField(_('keyword'), max_length=100, help_text=_('Part or all of a user-agent string.  For example, "Googlebot" here will be found in "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)" and that visitor will not be tracked.'))

    def __unicode__(self):
        return self.keyword

    class Meta:
        ordering = ('keyword',)
        verbose_name = _('Untracked User-Agent')
        verbose_name_plural = _('Untracked User-Agents')

class BannedIP(models.Model):
    ip_address = models.IPAddressField('IP Address', help_text=_('The IP address that should be banned'))

    def __unicode__(self):
        return self.ip_address

    class Meta:
        ordering = ('ip_address',)
        verbose_name = _('Banned IP')
        verbose_name_plural = _('Banned IPs')

########NEW FILE########
__FILENAME__ = tracking_tags
from django import template
from tracking.models import Visitor

register = template.Library()

class VisitorsOnSite(template.Node):
    """
    Injects the number of active users on your site as an integer into the context
    """
    def __init__(self, varname, same_page=False):
        self.varname = varname
        self.same_page = same_page

    def render(self, context):
        if self.same_page:
            try:
                request = context['request']
                count = Visitor.objects.active().filter(url=request.path).count()
            except KeyError:
                raise template.TemplateSyntaxError("Please add 'django.core.context_processors.request' to your TEMPLATE_CONTEXT_PROCESSORS if you want to see how many users are on the same page.")
        else:
            count = Visitor.objects.active().count()

        context[self.varname] = count
        return ''

def visitors_on_site(parser, token):
    """
    Determines the number of active users on your site and puts it into the context
    """
    try:
        tag, a, varname = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError('visitors_on_site usage: {% visitors_on_site as visitors %}')

    return VisitorsOnSite(varname)
register.tag(visitors_on_site)

def visitors_on_page(parser, token):
    """
    Determines the number of active users on the same page and puts it into the context
    """
    try:
        tag, a, varname = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError('visitors_on_page usage: {% visitors_on_page as visitors %}')

    return VisitorsOnSite(varname, same_page=True)
register.tag(visitors_on_page)


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.conf import settings
from tracking import views

urlpatterns = patterns('',
    url(r'^refresh/$', views.update_active_users, name='tracking-refresh-active-users'),
    url(r'^refresh/json/$', views.get_active_users, name='tracking-get-active-users'),
)

if getattr(settings, 'TRACKING_USE_GEOIP', False):
    urlpatterns += patterns('',
        url(r'^map/$', views.display_map, name='tracking-visitor-map'),
    )

########NEW FILE########
__FILENAME__ = utils
from django.conf import settings
import re
import unicodedata

# this is not intended to be an all-knowing IP address regex
IP_RE = re.compile('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')

def get_ip(request):
    """
    Retrieves the remote IP address from the request data.  If the user is
    behind a proxy, they may have a comma-separated list of IP addresses, so
    we need to account for that.  In such a case, only the first IP in the
    list will be retrieved.  Also, some hosts that use a proxy will put the
    REMOTE_ADDR into HTTP_X_FORWARDED_FOR.  This will handle pulling back the
    IP from the proper place.
    """

    # if neither header contain a value, just use local loopback
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR',
                                  request.META.get('REMOTE_ADDR', '127.0.0.1'))
    if ip_address:
        # make sure we have one and only one IP
        try:
            ip_address = IP_RE.match(ip_address)
            if ip_address:
                ip_address = ip_address.group(0)
            else:
                # no IP, probably from some dirty proxy or other device
                # throw in some bogus IP
                ip_address = '10.0.0.1'
        except IndexError:
            pass

    return ip_address

def get_timeout():
    """
    Gets any specified timeout from the settings file, or use 10 minutes by
    default
    """
    return getattr(settings, 'TRACKING_TIMEOUT', 10)

def get_cleanup_timeout():
    """
    Gets any specified visitor clean-up timeout from the settings file, or
    use 24 hours by default
    """
    return getattr(settings, 'TRACKING_CLEANUP_TIMEOUT', 24)

def u_clean(s):
    """A strange attempt at cleaning up unicode"""

    uni = ''
    try:
        # try this first
        uni = str(s).decode('iso-8859-1')
    except UnicodeDecodeError:
        try:
            # try utf-8 next
            uni = str(s).decode('utf-8')
        except UnicodeDecodeError:
            # last resort method... one character at a time (ugh)
            if s and type(s) in (str, unicode):
                for c in s:
                    try:
                        uni += unicodedata.normalize('NFKC', unicode(c))
                    except UnicodeDecodeError:
                        uni += '-'

    return uni.encode('ascii', 'xmlcharrefreplace')


########NEW FILE########
__FILENAME__ = views
from datetime import datetime
import logging
import traceback

from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext, Context, loader
from django.utils.simplejson import JSONEncoder
from django.utils.translation import ungettext
from django.views.decorators.cache import never_cache
from tracking.models import Visitor
from tracking.utils import u_clean as uc

DEFAULT_TRACKING_TEMPLATE = getattr(settings, 'DEFAULT_TRACKING_TEMPLATE',
                                    'tracking/visitor_map.html')
log = logging.getLogger('tracking.views')

def update_active_users(request):
    """
    Returns a list of all active users
    """
    if request.is_ajax():
        active = Visitor.objects.active()
        user = getattr(request, 'user', None)

        info = {
            'active': active,
            'registered': active.filter(user__isnull=False),
            'guests': active.filter(user__isnull=True),
            'user': user
        }

        # render the list of active users
        t = loader.get_template('tracking/_active_users.html')
        c = Context(info)
        users = {'users': t.render(c)}

        return HttpResponse(content=JSONEncoder().encode(users))

    # if the request was not made via AJAX, raise a 404
    raise Http404

@never_cache
def get_active_users(request):
    """
    Retrieves a list of active users which is returned as plain JSON for
    easier manipulation with JavaScript.
    """
    if request.is_ajax():
        active = Visitor.objects.active().reverse()
        now = datetime.now()

        # we don't put the session key or IP address here for security reasons
        try:
            data = {'users': [{
                    'id': v.id,
                    #'user': uc(v.user),
                    'user_agent': uc(v.user_agent),
                    'referrer': uc(v.referrer),
                    'url': uc(v.url),
                    'page_views': v.page_views,
                    'geoip': v.geoip_data_json,
                    'last_update': (now - v.last_update).seconds,
                    'friendly_time': ', '.join(friendly_time((now - v.last_update).seconds)),
                } for v in active]}
        except:
            log.error('There was a problem putting all of the visitor data together:\n%s\n\n%s' % (traceback.format_exc(), locals()))
            return HttpResponse(content='{}', mimetype='text/javascript')

        response = HttpResponse(content=JSONEncoder().encode(data),
                                mimetype='text/javascript')
        response['Content-Length'] = len(response.content)

        return response

    # if the request was not made via AJAX, raise a 404
    raise Http404

def friendly_time(last_update):
    minutes = last_update / 60
    seconds = last_update % 60

    friendly_time = []
    if minutes > 0:
        friendly_time.append(ungettext(
                '%(minutes)i minute',
                '%(minutes)i minutes',
                minutes
        ) % {'minutes': minutes })
    if seconds > 0:
        friendly_time.append(ungettext(
                '%(seconds)i second',
                '%(seconds)i seconds',
                seconds
        ) % {'seconds': seconds })

    return friendly_time or 0

def display_map(request, template_name=DEFAULT_TRACKING_TEMPLATE,
        extends_template='base.html'):
    """
    Displays a map of recently active users.  Requires a Google Maps API key
    and GeoIP in order to be most effective.
    """

    GOOGLE_MAPS_KEY = getattr(settings, 'GOOGLE_MAPS_KEY', None)

    return render_to_response(template_name,
                              {'GOOGLE_MAPS_KEY': GOOGLE_MAPS_KEY,
                               'template': extends_template},
                              context_instance=RequestContext(request))

########NEW FILE########
