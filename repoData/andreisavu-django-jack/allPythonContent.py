__FILENAME__ = abspath

import os

def abspath(*args):
    current_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(current_dir, *args)



########NEW FILE########
__FILENAME__ = buried
""" Basic check for buried jobs

The max number for buried jobs should not exced 3 and
the max age of buried job should not exced 120 seconds.
"""


def do_check(client):
    current_buried = client.stats()['current-jobs-buried']
    if current_buried >= 3:
        return 'found %d jobs buried.' % current_buried

    max_age, max_jid = 0, 0
    for tube in client.tubes():
        client.use(tube)

        job = client.peek_buried()
        if job is not None:
            age = int(job.stats()['age'])
            if age > max_age:
                max_age, max_jid = age, job.jid

    if max_jid and max_age > 120:
        return 'found old buried job #%d' % max_jid
            


########NEW FILE########
__FILENAME__ = client

from django.conf import settings

from beanstalkc import Connection, CommandFailed
from beanstalkc import SocketError as ConnectionError

class Client(object):
    """ A simple proxy object over the default client """

    def __init__(self, request):
        if hasattr(request, 'connection'):
            self.conn = Connection(request.connection[0], request.connection[1])
        elif settings.BEANSTALK_SERVERS:
            server = settings.BEANSTALK_SERVERS[0]
            self.conn = Connection(server[0], server[1])
        else:
            raise Exception("No servers defined.")

    def __getattr__(self, name):
        return getattr(self.conn, name) 



########NEW FILE########
__FILENAME__ = forms

from django import forms

class PutForm(forms.Form):
    body = forms.CharField(widget=forms.Textarea())
    tube = forms.CharField(initial='default')
    priority = forms.IntegerField(initial=2147483648)
    delay = forms.IntegerField(initial=0)
    ttr = forms.IntegerField(initial=120)


########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = multiple_beanstalk
from django.conf import settings

class Middleware(object):
    def process_request(self, request):
        if 'conn' not in request.COOKIES:
            return

        conn_id = int(request.COOKIES['conn'])
        request.connection = settings.BEANSTALK_SERVERS[conn_id]

def ContextProcessor(request):
    if 'conn' not in request.COOKIES:
        conn_id = None
    else:
        conn_id = int(request.COOKIES['conn'])
    return {'connections':settings.BEANSTALK_SERVERS,'conn_id':conn_id}


########NEW FILE########
__FILENAME__ = shortcuts

from django.shortcuts import render_to_response

def render_unavailable():
    return render_to_response('beanstalk/unavailable.html')


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

import views

urlpatterns = patterns('',
    (r'^$', views.index),
    (r'^stats/$', views.stats),
    (r'^stats_table/$', views.stats_table),
    (r'^put/$', views.put),
    (r'^ready/(?P<tube>[\w-]*)$', views.ready),
    (r'^delayed/(?P<tube>[\w-]*)$', views.delayed),
    (r'^buried/(?P<tube>[\w-]*)$', views.buried),
    (r'^inspect/(?P<id>\d*)$', views.inspect),
    (r'^tube/(?P<tube>[\w-]+)/stats/$', views.tube_stats),
    (r'^job/(?P<id>\d+)/delete/$', views.job_delete),
    (r'^job/(?P<id>\d+)/kick/$', views.job_kick),
)

########NEW FILE########
__FILENAME__ = views

from django.shortcuts import render_to_response, redirect
from django.contrib.auth.decorators import login_required

from django.http import Http404
from django.template import RequestContext

from beanstalk.client import Client, CommandFailed, ConnectionError
from beanstalk.forms import PutForm
from beanstalk.shortcuts import render_unavailable
from beanstalk import checks

from urlparse import urlsplit

def _multiget(data, keys, default=None):
    ret = {}
    for key in keys:
        ret[key] = data.get(key, default)
    return ret

@login_required
def index(request):
    try:
        client = Client(request)
    except ConnectionError:
        return render_unavailable()

    checks_errors = checks.run_all(client)

    stats = _multiget(client.stats(), [
        'current-connections', 
        'uptime', 
        'job-timeouts',
        'version',
        'current-jobs-buried',
        'total-jobs',])

    if 'uptime' in stats:
        days = float(stats['uptime']) / 60.0 / 60.0 / 24.0
        stats['uptime'] = '%s (%.2f days)' % (stats['uptime'], days)

    tube_stats = []
    for tube in client.tubes():
        tube_stats.append(_multiget(client.stats_tube(tube),
            ['name', 'pause', 'current-jobs-buried', \
             'current-waiting', 'total-jobs']))

    return render_to_response('beanstalk/index.html', 
        {'stats' : stats, 
         'tube_stats' : tube_stats,
         'checks_errors' : checks_errors},
        context_instance=RequestContext(request))

@login_required
def stats(request):
    return tube_stats(request)

@login_required
def stats_table(request):
    return tube_stats_table(request)

@login_required
def tube_stats(request, tube=None):
    try:
        client = Client(request)
    except ConnectionError:
        return render_unavailable()

    if tube is None:
        stats = client.stats().items()
    else:
        try:
            stats = client.stats_tube(tube).items()
        except CommandFailed:
            raise Http404
 
    tubes = client.tubes()

    return render_to_response('beanstalk/stats.html', 
        {'stats': stats,
         'tubes': tubes,
         'current_tube': tube
        }, context_instance=RequestContext(request))

@login_required
def tube_stats_table(request, tube=None):
    try:
        client = Client(request)
    except ConnectionError:
        return render_unavailable()

    tubes = client.tubes()
    stats = {'all':client.stats().items()}

    for tube in tubes:
        stats[tube] = client.stats_tube(tube).items()

    return render_to_response('beanstalk/stats_table.html', 
        {'stats': stats,
         'tubes': tubes
        }, context_instance=RequestContext(request))

@login_required
def put(request):
    if request.method == 'POST':
        form = PutForm(request.POST)
        if form.is_valid():

            try:
                client = Client(request)
            except ConnectionError:
                return render_unavailable()

            client.use(form.cleaned_data['tube'])

            id = client.put(str(form.cleaned_data['body']), form.cleaned_data['priority'], \
                form.cleaned_data['delay'], form.cleaned_data['ttr'])
 
            request.flash.put(notice='job submited to queue with id #%d' % id)
            return redirect('/beanstalk/put/')
    else:
        form = PutForm()

    return render_to_response('beanstalk/put.html', 
        {'form':form}, context_instance=RequestContext(request))   

@login_required
def inspect(request, id=None, tube_prefix='', tube=''):
    if request.method == 'POST':
        id = request.POST['id']
    
    try:
        id = int(id)
    except (ValueError, TypeError):
        id = None

    try:
        client = Client(request)
    except ConnectionError:
        return render_unavailable()

    if id:
        job = client.peek(id)
        if job is None:
            request.flash.put(notice='no job found with id #%d' % id)
            stats = []
            buried = False
        else:
            buried = job.stats()['state'] == 'buried'
            stats = job.stats().items()
    else:
        job = None
        stats = []
        buried = False

    tubes = client.tubes()

    return render_to_response('beanstalk/inspect.html',
        {'job': job, 'stats': stats, 'buried': buried, 'tubes': tubes,
         'tube_prefix': tube_prefix, 'current_tube': tube},
        context_instance=RequestContext(request))

def _peek_if(request, status, tube):
    try:
        client = Client(request)
    except ConnectionError:
        return render_unavailable()

    if not tube: tube = 'default'
    client.use(tube)

    job = getattr(client, "peek_%s" % status)()
    if job is not None:
        return inspect(request, job.jid, tube_prefix='/beanstalk/%s/' % status, tube=tube)

    request.flash.put(notice='no job found')
    return inspect(request, tube_prefix='/beanstalk/%s/' % status, tube=tube)


@login_required
def ready(request, tube):
    return _peek_if(request, 'ready', tube)

@login_required
def delayed(request, tube):
    return _peek_if(request, 'delayed', tube)

@login_required
def buried(request, tube):
    return _peek_if(request, 'buried', tube)


def _redirect_to_referer_or(request, dest):
    referer = request.META.get('HTTP_REFERER', None)
    if referer is None:
        return redirect(dest)

    try:
        redirect_to = urlsplit(referer, 'http', False)[2]
    except IndexError:
        redirect_to = dest

    return redirect(redirect_to)

@login_required
def job_delete(request, id):
    try:
        client = Client(request)
        job = client.peek(int(id))

        if job is not None:
            job.delete()
    
        return _redirect_to_referer_or(request, '/beanstalk/inspect/')

    except ConnectionError:
        return render_unavailable()

@login_required
def job_kick(request, id):
    try:
        client = Client(request)
        client.use(request.POST['tube'])
        # The argument to kick is number of jobs not jobId, by default one job
        # is kicked.
        client.kick()

        return redirect('/beanstalk/buried/')

    except ConnectionError:
        return render_unavailable()
    

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
# Django settings for jack project.

from abspath import abspath

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': abspath('database.db'),                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

LOGIN_REDIRECT_URL = '/'

FLASH_IGNORE_MEDIA = True
FLASH_STORAGE = 'session'
FLASH_CODEC = 'json'

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
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

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = abspath('media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '8wv3d_4@^=blqi)@ev*v4m=hphqgl6c5av-tbw$pl)2x37_2+-'

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    'djangoflash.context_processors.flash',
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'djangoflash.middleware.FlashMiddleware',
)

ROOT_URLCONF = 'jack.urls'

TEMPLATE_DIRS = (
    abspath('templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'beanstalk',
)

### MULTIPLE BEANSTALKD SUPPORT
BEANSTALK_SERVERS = (
)
from django.conf import global_settings
MIDDLEWARE_CLASSES += ('beanstalk.multiple_beanstalk.Middleware',)
TEMPLATE_CONTEXT_PROCESSORS = global_settings.TEMPLATE_CONTEXT_PROCESSORS + (
    'beanstalk.multiple_beanstalk.ContextProcessor',
)

try:
    from local_settings import *
except ImportError:
    pass



########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.shortcuts import redirect
from abspath import abspath

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^$', lambda req:redirect('/beanstalk/')),
    (r'^beanstalk/', include('beanstalk.urls')),

    (r'^accounts/login/$', 'django.contrib.auth.views.login', 
        {'template_name':'accounts/login.html'}),
    (r'^accounts/logout/$', 'django.contrib.auth.views.logout_then_login'),

    (r'^media/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': abspath('media')}),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
