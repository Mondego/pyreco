__FILENAME__ = rethink
from functools import wraps

import rethinkdb
# from rethinkdb.errors import RqlDriverError

from gistio.utils import get_setting


RETHINK_CONNARGS = get_setting('RETHINK_CONNARGS')

def get_connection():
    conn = rethinkdb.connect(**RETHINK_CONNARGS)
    return conn

def rethinkdb_connect(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        request.rdbconn = get_connection()
        retval = view(request, *args, **kwargs)
        try:
            request.rdbconn.close()
        except AttributeError:
            close
        finally:
            return retval
    return wrapper
########NEW FILE########
__FILENAME__ = base
import os
import urlparse

from unipath import FSPath as Path

from django.core.exceptions import ImproperlyConfigured

PROJECT_DIR = Path(__file__).absolute().ancestor(3)

def get_env_variable(var_name):
    """ Get the environment variable or return an exception """
    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = "Set the {} environment variable".format(var_name)
        raise ImproperlyConfigured(error_msg)


DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Idan Gazit', 'idan@gazit.me'),
)

DATABASES = {}


RETHINKDB_URL = urlparse.urlparse(get_env_variable('RETHINKDB_URL'))
urlparse.uses_netloc.append('rethinkdb')
RETHINK_CONNARGS = {}
rethink_argmap = {'hostname': 'host',
                  'port': 'port',
                  'username': 'db',
                  'password': 'auth_key'}
for k,v in rethink_argmap.items():
    p = getattr(RETHINKDB_URL, k, None)
    if p is not None:
        RETHINK_CONNARGS[v] = p


MANAGERS = ADMINS


ALLOWED_HOSTS = []
TIME_ZONE = 'Etc/UTC'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = False
USE_L10N = True
USE_TZ = True


MEDIA_ROOT = PROJECT_DIR.child('media')
# the following line is a total lie except in production
# MEDIA_URL = 'http://{}.s3.amazonaws.com/media/'.format(AWS_STORAGE_BUCKET_NAME)

STATIC_ROOT = 'staticfiles'
STATIC_URL = '/static/'
STATICFILES_ROOT = PROJECT_DIR.child('static')
STATICFILES_DIRS = [
    (subdir, str(STATICFILES_ROOT.child(subdir))) for subdir in
    ['css', 'fonts', 'img', 'js']]
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

SECRET_KEY = get_env_variable('APP_SECRET_KEY')

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
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'gistio.urls'
WSGI_APPLICATION = 'gistio.wsgi.application'
TEMPLATE_DIRS = (
    PROJECT_DIR.child('templates')
)

INSTALLED_APPS = (
    # 'django.contrib.auth',
    # 'django.contrib.contenttypes',
    'django.contrib.sessions',
    # 'django.contrib.sites',
    # 'django.contrib.messages',
    'django.contrib.staticfiles',
    'publicsite',
    'githubauth',
    'gists',
)

SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}


GITHUB_CLIENT_ID = get_env_variable('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = get_env_variable('GITHUB_CLIENT_SECRET')
GITHUB_AUTH_PARAMS = {'client_id': GITHUB_CLIENT_ID,
               'client_secret': GITHUB_CLIENT_SECRET}

GIST_PUBLIC_CACHE_SECONDS = 60

########NEW FILE########
__FILENAME__ = heroku
from .base import *

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Allow all host headers
ALLOWED_HOSTS = ['*']

########NEW FILE########
__FILENAME__ = local
from .base import *

DEBUG = True
TEMPLATE_DEBUG = DEBUG


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
        },
        'null': {
            'class': 'logging.NullHandler',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'py.warnings': {
            'handlers': ['console'],
        },
        'gistio': {
            'handlers': ['console'],
        },
        'gists': {
            'handlers': ['console'],
        },
        'githubauth': {
            'handlers': ['console'],
        },
        'publicsite': {
            'handlers': ['console'],
        },
    }
}
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^', include('gists.urls')),
    # url(r'^', include('githubauth.urls')),
    url(r'^', include('publicsite.urls')),
)

########NEW FILE########
__FILENAME__ = utils
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def get_setting(setting):
    try:
        return getattr(settings, setting)
    except AttributeError:
        raise ImproperlyConfigured('No setting named "{0}" was found in settings.py.'.format(setting))

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for gistio project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "gistio.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gistio.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
from django.core.wsgi import get_wsgi_application
from dj_static import Cling
application = Cling(get_wsgi_application())

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = gistio
import os
import json
import urlparse

import rethinkdb as r
from rethinkdb.errors import RqlRuntimeError, RqlDriverError
from redis import StrictRedis
import requests
import iso8601
import smartypants
from docutils.core import publish_parts as render_rst

from flask import Flask, g, render_template, make_response, abort, request
app = Flask(__name__)

HEROKU = 'HEROKU' in os.environ

GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')

AUTH_PARAMS = {'client_id': GITHUB_CLIENT_ID,
               'client_secret': GITHUB_CLIENT_SECRET}

if 'RETHINKDB_URL' in os.environ:
    urlparse.uses_netloc.append('rethinkdb')
    rethink_url = urlparse.urlparse(os.environ['RETHINKDB_URL'])
    RETHINK_CONNARGS = {}
    rethink_argmap = {'hostname': 'host',
                      'port': 'port',
                      'username': 'db',
                      'password': 'auth_key'}
    for k,v in rethink_argmap.items():
        p = getattr(rethink_url, k, None)
        if p is not None:
            RETHINK_CONNARGS[v] = p

if HEROKU:
    urlparse.uses_netloc.append('redis')
    redis_url = urlparse.urlparse(os.environ['REDISTOGO_URL'])
    cache = StrictRedis(host=redis_url.hostname,
                        port=redis_url.port,
                        password=redis_url.password)

    PORT = int(os.environ.get('PORT', 5000))
    STATIC_URL = '//static.gist.io/'
else:
    cache = StrictRedis()  # local development
    PORT = 5000
    STATIC_URL = '/static/'

CACHE_EXPIRATION = 60  # seconds

FORMAT_RST = 'rst'
FORMAT_MD = 'md'

RENDERABLE = {
                u'Text': FORMAT_MD,
                u'Markdown': FORMAT_MD,
                u'Literate CoffeeScript': FORMAT_MD,
                u'reStructuredText': FORMAT_RST,
                None: FORMAT_MD,
             }

class GistFetchError(Exception): pass

@app.before_request
def before_request():
    try:

        g.rethink = r.connect(**RETHINK_CONNARGS)
    except RqlDriverError:
        abort(503, "No database connection could be established.")

@app.teardown_request
def teardown_request(exception):
    try:
        g.rethink.close()
    except AttributeError:
        pass


@app.route('/oauth')
def oauth():
    app.logger.warning("Method: {}".format(request.method))
    app.logger.warning("Args: {}".format(request.args))
    return(u"oauth")

@app.route('/')
def homepage():
    return render_template('home.html', STATIC_URL=STATIC_URL)


@app.route('/<int:id>')
def render_gist(id):
    gist = r.table('gists').get(unicode(id)).run(g.rethink)
    if gist is None:
        try:
            user, gist = fetch_and_render(id)
        except GistFetchError:
            abort(404);
    else:
        user = r.table('users').get(gist['author_id']).run(g.rethink)

    ctx = {'user': user, 'gist': gist, 'STATIC_URL': STATIC_URL}
    app.logger.debug(ctx)
    return render_template('gist.html', **ctx)


@app.route('/<int:id>/content')
def gist_contents(id):
    cache_hit = True
    content = cache.get(id)
    if not content:
        cache_hit = False
        content = fetch_and_render(id)
    if content is None:
        abort(404)
    resp = make_response(content, 200)
    resp.headers['Content-Type'] = 'application/json'
    resp.headers['X-Cache-Hit'] = cache_hit
    resp.headers['X-Expire-TTL-Seconds'] = cache.ttl(id)
    return resp


def fetch_and_render(id):
    """Fetch and render a post from the Github API"""
    req_gist = requests.get('https://api.github.com/gists/{}'.format(id),
                     params=AUTH_PARAMS)
    if req_gist.status_code != 200:
        app.logger.warning('Fetch {} failed: {}'.format(id, r.status_code))
        raise GistFetchError()

    try:
        raw = req_gist.json()
    except ValueError:
        app.logger.error('Fetch {} failed: unable to decode JSON response'.format(id))
        raise GistFetchError()

    user = {}
    for prop in ['id', 'login', 'avatar_url', 'html_url', 'type']:
        user[prop] = raw['user'][prop]
    user['fetched_at'] = r.now()
    r.table('users').insert(user, upsert=True).run(g.rethink)

    gist = {
        'id': raw['id'],
        'html_url': raw['html_url'],
        'public': raw['public'],
        'description': raw['description'],
        'created_at': iso8601.parse_date(raw['created_at']),
        'updated_at': iso8601.parse_date(raw['updated_at']),
        'author_id': user['id'],
        'author_login': user['login'],
        'files': [],
    }


    for gistfile in raw['files'].values():
        format = RENDERABLE.get(gistfile['language'], None)

        if format is None:
            continue

        output = None

        if format is FORMAT_MD:
            payload = {
                'mode': 'gfm',
                'text': gistfile['content'],
            }
            req_render = requests.post('https://api.github.com/markdown',
                                       params=AUTH_PARAMS,
                                       data=unicode(json.dumps(payload)))
            if req_render.status_code != 200:
                app.logger.warn('Render {} file {} failed: {}'.format(id, gistfile['filename'], req_render.status_code))
                continue
            else:
                output = smartypants.smartypants(req_render.text)

        if format is FORMAT_RST:
            rendered = render_rst(gistfile['content'], writer_name='html')['fragment']
            output = smartypants.smartypants(rendered)

        if output is not None:
                gistfile['rendered'] = output
                gist['files'].append(gistfile)


    r.table('gists').insert(gist, upsert=True).run(g.rethink)
    return user, gist


if __name__ == '__main__':
    if HEROKU:
        app.run(host='0.0.0.0', port=PORT)
    else:
        cache.flushall()
        app.run(host='0.0.0.0', debug=True, port=PORT)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^(?P<id>\d+)$', 'gists.views.gist', name='gist'),
    url(r'^(?P<user>[a-zA-Z0-9]+)/(?P<id>\d+)$', 'gists.views.usergist', name='gist'),
)
########NEW FILE########
__FILENAME__ = views
import logging
import json


import iso8601
import requests
import smartypants
from docutils.core import publish_parts as render_rst
import rethinkdb as rdb

from django.shortcuts import render, redirect
from django.http import Http404
from django.utils.timezone import now as tz_now

from gistio.rethink import rethinkdb_connect
from gistio.utils import get_setting

logger =  logging.getLogger(__name__)

FORMAT_RST = 'rst'
FORMAT_MD = 'md'

RENDERABLE = {
                u'Text': FORMAT_MD,
                u'Markdown': FORMAT_MD,
                u'Literate CoffeeScript': FORMAT_MD,
                u'reStructuredText': FORMAT_RST,
                None: FORMAT_MD,
             }

GITHUB_AUTH_PARAMS = get_setting('GITHUB_AUTH_PARAMS')

GIST_PUBLIC_CACHE_SECONDS = get_setting('GIST_PUBLIC_CACHE_SECONDS')

class GistFetchError(Exception): pass

@rethinkdb_connect
def gist(request, id):
    now = tz_now()
    gist = rdb.table('gists').get(unicode(id)).run(request.rdbconn)
    if gist is None:
        # it's a new gist for us
        user, gist = fetch_and_render_gist(request, id)
    else:
        # we already have the gist, check to see if it's still cached
        delta = now - gist['fetched_at']
        if delta.seconds > GIST_PUBLIC_CACHE_SECONDS:
            raw = fetch_gist(request, id)
            if gist['updated_at'] != iso8601.parse_date(raw['updated_at']):
                # gist has changed, rerender it
                gist = render_gist(request, id, raw)
        user = rdb.table('users').get(gist['author_id']).run(request.rdbconn)
    return render(request, 'gist.html', {'user': user, 'gist': gist})


@rethinkdb_connect
def usergist(request, user, id):
    print('rendered {} / {}'.format(user, id))
    return gist(request, id)


def fetch_and_render_gist(request, id):
    try:
        raw = fetch_gist(request, id)
    except GistFetchError:
        raise Http404()
    user = capture_user(request, id, raw)
    gist = render_gist(request, id, raw)
    return user, gist

def fetch_gist(request, id):
    """Fetch a gist from the github API"""
    req_gist = requests.get('https://api.github.com/gists/{}'.format(id),
                     params=GITHUB_AUTH_PARAMS)
    if req_gist.status_code != 200:
        logger.warning('Fetch {} failed: {}'.format(id, req_gist.status_code))
        raise GistFetchError()

    try:
        return req_gist.json()
    except ValueError:
        logger.error('Fetch {} failed: unable to decode JSON response'.format(id))
        raise GistFetchError()

def capture_user(request, id, raw):
    user = {}
    for prop in ['id', 'login', 'avatar_url', 'html_url', 'type']:
        user[prop] = raw['user'][prop]
    user['fetched_at'] = rdb.now()
    rdb.table('users').insert(user, upsert=True).run(request.rdbconn)
    return user

def render_gist(request, id, raw):
    """Render a raw gist and store it"""
    gist = {
        'id': raw['id'],
        'html_url': raw['html_url'],
        'public': raw['public'],
        'description': raw['description'],
        'created_at': iso8601.parse_date(raw['created_at']),
        'updated_at': iso8601.parse_date(raw['updated_at']),
        'fetched_at': rdb.now(),
        'author_id': raw['user']['id'],
        'author_login': raw['user']['login'],
        'files': [],
    }

    for gistfile in raw['files'].values():
        format = RENDERABLE.get(gistfile['language'], None)

        if format is None:
            continue

        output = None

        if format is FORMAT_MD:
            payload = {
                'mode': 'gfm',
                'text': gistfile['content'],
            }
            req_render = requests.post('https://api.github.com/markdown',
                                       params=GITHUB_AUTH_PARAMS,
                                       data=unicode(json.dumps(payload)))
            if req_render.status_code != 200:
                logger.warn('Render {} file {} failed: {}'.format(id, gistfile['filename'], req_render.status_code))
                continue
            else:
                output = smartypants.smartypants(req_render.text)

        if format is FORMAT_RST:
            rendered = render_rst(gistfile['content'], writer_name='html')['fragment']
            output = smartypants.smartypants(rendered)

        if output is not None:
                gistfile['rendered'] = output
                gist['files'].append(gistfile)


    rdb.table('gists').insert(gist, upsert=True).run(request.rdbconn)
    return gist
########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = urls

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gistio.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^$', 'publicsite.views.home', name='home'),
)
########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render

def home(request):
    return render(request, 'home.html')
########NEW FILE########
