__FILENAME__ = appengine_console
#!/usr/bin/python

""" Usage
python2.5 appengine_console.py <app-id>

for more information please read: http://code.google.com/appengine/articles/remote_api.html
"""
import code
import getpass
import sys
import os

root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(root_dir, 'lib'))
from gaePath.util import gae_sdk_path, add_gae_sdk_path

add_gae_sdk_path()
sys.path.append(gae_sdk_path() + "/lib/yaml/lib")
sys.path.append(gae_sdk_path() + "/lib/fancy_urllib")
sys.path.append(gae_sdk_path() + '/lib/webob')
sys.path.append(gae_sdk_path() + '/lib/simplejson')

from google.appengine.ext.remote_api import remote_api_stub
from google.appengine.ext import db

def auth_func():
    return raw_input('Username:'), getpass.getpass('Password:')

if len(sys.argv) < 2:
    print "Usage: %s app_id [host]" % (sys.argv[0],)
app_id = sys.argv[1]
if len(sys.argv) > 2:
    host = sys.argv[2]
else:
    host = '%s.appspot.com' % app_id

remote_api_stub.ConfigureRemoteDatastore(app_id, '/_ah/remote_api', auth_func, host)

code.interact('App Engine interactive console for %s' % (app_id,), None, locals())

########NEW FILE########
__FILENAME__ = boot
from wsgiref.handlers import CGIHandler
from google.appengine.ext.appstats import recording
import sys, os

root_dir = os.path.dirname(os.path.abspath(__file__))
lib_dir = os.path.join(root_dir, 'lib')
if lib_dir not in sys.path:
    sys.path.insert(0, lib_dir)

from main import app

if 'SERVER_SOFTWARE' in os.environ and os.environ['SERVER_SOFTWARE'].startswith('Dev'):
    # use our debug.utils with Jinja2 templates
    import debug.utils
    sys.modules['werkzeug.debug.utils'] = debug.utils

    # don't use inspect.getsourcefile because the imp module is empty
    import inspect
    inspect.getsourcefile = inspect.getfile

    # wrap the application
    from werkzeug import DebuggedApplication
    app = DebuggedApplication(app, evalex=True)

CGIHandler().run(recording.appstats_wsgi_middleware(app))

########NEW FILE########
__FILENAME__ = decorators
# coding: UTF-8

from flask import g
from flask import redirect
from flask import url_for

from functools import wraps

from werkzeug.contrib.cache import GAEMemcachedCache
cache = GAEMemcachedCache()

def login_required(f):
    """
    redirects to the index page if the user has no session
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def cache_page(timeout=5 * 60, key='view/%s'):
    """
    caches a full page in memcache, takes a timeout in seconds
    which specifies how long the cache should be valid.
    also allows a formatstring to be used as memcache key prefix.

    source:
    http://flask.pocoo.org/docs/patterns/viewdecorators/#caching-decorator
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            cache_key = key % request.path
            rv = cache.get(cache_key)
            if rv is not None:
                return rv
            rv = f(*args, **kwargs)
            cache.set(cache_key, rv, timeout=timeout)
            return rv
        return decorated_function
    return decorator

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
"""
    werkzeug.debug.utils
    ~~~~~~~~~~~~~~~~~~~~

    Various other utilities.

    :copyright: Copyright 2008 by Armin Ronacher.
    :license: BSD.
"""
from os.path import join, dirname
from jinja2 import Environment, FileSystemLoader

env = Environment(loader = FileSystemLoader([join(dirname(__file__), 'templates')]))

def get_template(filename):
    return env.get_template(filename)

def render_template(template_filename, **context):
    return get_template(template_filename).render(**context)

########NEW FILE########
__FILENAME__ = main
# coding: UTF-8

import settings

from flask import Flask
app = Flask(__name__)
app.config.from_object('settings')

from flask import g
from flask import redirect
from flask import url_for
from flask import session
from flask import request
from flask import render_template
from flask import abort
from flask import flash
from flask import get_flashed_messages
from flask import json

from decorators import login_required, cache_page

from models import User

from gaeUtils.util import generate_key
from google.appengine.api.labs import taskqueue

@app.before_request
def before_request():
    """
    if the session includes a user_key it will also try to fetch
    the user's object from memcache (or the datastore).
    if this succeeds, the user object is also added to g.
    """
    if 'user_key' in session:
        user = cache.get(session['user_key'])

        if user is None:
            # if the user is not available in memcache we fetch
            # it from the datastore
            user = User.get_by_key_name(session['user_key'])

            if user:
                # add the user object to memcache so we
                # don't need to hit the datastore next time
                cache.set(session['user_key'], user)

        g.user = user
    else:
        g.user = None

@app.route('/')
def index():
    """
    renders the index page template
    """
    return render_template('index.html')

########NEW FILE########
__FILENAME__ = models
# coding: UTF-8
from google.appengine.ext import db

class User(db.Model):
    name = db.StringProperty()

########NEW FILE########
__FILENAME__ = settings
import os
DEBUG = os.environ.get('SERVER_SOFTWARE', 'Dev').startswith('Dev')
SECRET_KEY = 'j;wD=R#2]07l65r+J)9,%)D[f:1,VS.+RQ+5VY.]lP]\wY:K'

# CSRF_ENABLED=True
# CSRF_SESSION_LKEY=''

########NEW FILE########
__FILENAME__ = test_views_static
# -*- coding: utf-8 -*-
import os
import signal
from subprocess import Popen
from selenium.firefox.webdriver import WebDriver

import unittest

from main import app
import settings


class TestStaticPages(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_index(self):
        "Should have an index page with a welcome message"
        response = self.client.get('/')
        assert 'Welcome to Flask-Gae-Skeleton!' in response.data

class TestStaticPagesWithJs(unittest.TestCase):

    def setUp(self):
        self.server = Popen("dev_appserver.py . --port=80", shell=True)
        self.browser = WebDriver()

    def tearDown(self):
        self.browser.quit()
        # same as in python2.6 subprocess for posix systems (so currently no windows support)
        os.kill(self.server.pid, signal.SIGTERM)

    def test_index_with_js(self):
        self.browser.get('http://localhost')
        assert 'Welcome to Flask-Gae-Skeleton!' in self.browser.get_page_source()

########NEW FILE########
