__FILENAME__ = config
appname = ""
client_id = ""
client_secret = ""

########NEW FILE########
__FILENAME__ = main
import os
import sys

# add dist to path for buildout-managed dependencies
sys.path.insert(0, os.path.join(os.path.abspath(os.path.dirname(__file__)), 'dist'))

import glass
import config
import logging
from flask import session, render_template, redirect

app = glass.Application(
    name=config.appname,
    client_id=config.client_id,
    client_secret=config.client_secret)

# Set the secret key for flask session.  keep this really secret: (but here it's not ;) )
app.web.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

app.prepare(port=8765)

@app.web.route("/")
def index():
    configured = config.appname and config.client_id and config.client_secret
    user = None
    if 'token' in session:
        user = glass.User(app=app, token=session['token'])
    return render_template("index.html", user=user, configured=configured)

@app.subscriptions.login
def login(user):
    session['token'] = user.token
    user.timeline.post(text="Hello from App Engine!")
    return redirect('/')

########NEW FILE########
__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.
"""

import os, shutil, sys, tempfile, urllib, urllib2, subprocess
from optparse import OptionParser

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c  # work around spawn lamosity on windows
        else:
            return c
else:
    quote = str

# See zc.buildout.easy_install._has_broken_dash_S for motivation and comments.
stdout, stderr = subprocess.Popen(
    [sys.executable, '-Sc',
     'try:\n'
     '    import ConfigParser\n'
     'except ImportError:\n'
     '    print 1\n'
     'else:\n'
     '    print 0\n'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
has_broken_dash_S = bool(int(stdout.strip()))

# In order to be more robust in the face of system Pythons, we want to
# run without site-packages loaded.  This is somewhat tricky, in
# particular because Python 2.6's distutils imports site, so starting
# with the -S flag is not sufficient.  However, we'll start with that:
if not has_broken_dash_S and 'site' in sys.modules:
    # We will restart with python -S.
    args = sys.argv[:]
    args[0:0] = [sys.executable, '-S']
    args = map(quote, args)
    os.execv(sys.executable, args)
# Now we are running with -S.  We'll get the clean sys.path, import site
# because distutils will do it later, and then reset the path and clean
# out any namespace packages from site-packages that might have been
# loaded by .pth files.
clean_path = sys.path[:]
import site  # imported because of its side effects
sys.path[:] = clean_path
for k, v in sys.modules.items():
    if k in ('setuptools', 'pkg_resources') or (
        hasattr(v, '__path__') and
        len(v.__path__) == 1 and
        not os.path.exists(os.path.join(v.__path__[0], '__init__.py'))):
        # This is a namespace package.  Remove it.
        sys.modules.pop(k)

is_jython = sys.platform.startswith('java')

setuptools_source = 'http://peak.telecommunity.com/dist/ez_setup.py'
distribute_source = 'http://python-distribute.org/distribute_setup.py'


# parsing arguments
def normalize_to_url(option, opt_str, value, parser):
    if value:
        if '://' not in value:  # It doesn't smell like a URL.
            value = 'file://%s' % (
                urllib.pathname2url(
                    os.path.abspath(os.path.expanduser(value))),)
        if opt_str == '--download-base' and not value.endswith('/'):
            # Download base needs a trailing slash to make the world happy.
            value += '/'
    else:
        value = None
    name = opt_str[2:].replace('-', '_')
    setattr(parser.values, name, value)

usage = '''\
[DESIRED PYTHON FOR BUILDOUT] bootstrap.py [options]

Bootstraps a buildout-based project.

Simply run this script in a directory containing a buildout.cfg, using the
Python that you want bin/buildout to use.

Note that by using --setup-source and --download-base to point to
local resources, you can keep this script from going over the network.
'''

parser = OptionParser(usage=usage)
parser.add_option("-v", "--version", dest="version",
                          help="use a specific zc.buildout version")
parser.add_option("-d", "--distribute",
                   action="store_true", dest="use_distribute", default=False,
                   help="Use Distribute rather than Setuptools.")
parser.add_option("--setup-source", action="callback", dest="setup_source",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or file location for the setup file. "
                        "If you use Setuptools, this will default to " +
                        setuptools_source + "; if you use Distribute, this "
                        "will default to " + distribute_source + "."))
parser.add_option("--download-base", action="callback", dest="download_base",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or directory for downloading "
                        "zc.buildout and either Setuptools or Distribute. "
                        "Defaults to PyPI."))
parser.add_option("--eggs",
                  help=("Specify a directory for storing eggs.  Defaults to "
                        "a temporary directory that is deleted when the "
                        "bootstrap script completes."))
parser.add_option("-t", "--accept-buildout-test-releases",
                  dest='accept_buildout_test_releases',
                  action="store_true", default=False,
                  help=("Normally, if you do not specify a --version, the "
                        "bootstrap script and buildout gets the newest "
                        "*final* versions of zc.buildout and its recipes and "
                        "extensions for you.  If you use this flag, "
                        "bootstrap and buildout will get the newest releases "
                        "even if they are alphas or betas."))
parser.add_option("-c", None, action="store", dest="config_file",
                   help=("Specify the path to the buildout configuration "
                         "file to be used."))

options, args = parser.parse_args()

if options.eggs:
    eggs_dir = os.path.abspath(os.path.expanduser(options.eggs))
else:
    eggs_dir = tempfile.mkdtemp()

if options.setup_source is None:
    if options.use_distribute:
        options.setup_source = distribute_source
    else:
        options.setup_source = setuptools_source

if options.accept_buildout_test_releases:
    args.insert(0, 'buildout:accept-buildout-test-releases=true')

try:
    import pkg_resources
    import setuptools  # A flag.  Sometimes pkg_resources is installed alone.
    if not hasattr(pkg_resources, '_distribute'):
        raise ImportError
except ImportError:
    ez_code = urllib2.urlopen(
        options.setup_source).read().replace('\r\n', '\n')
    ez = {}
    exec ez_code in ez
    setup_args = dict(to_dir=eggs_dir, download_delay=0)
    if options.download_base:
        setup_args['download_base'] = options.download_base
    if options.use_distribute:
        setup_args['no_fake'] = True
        if sys.version_info[:2] == (2, 4):
            setup_args['version'] = '0.6.32'
    ez['use_setuptools'](**setup_args)
    if 'pkg_resources' in sys.modules:
        reload(sys.modules['pkg_resources'])
    import pkg_resources
    # This does not (always?) update the default working set.  We will
    # do it.
    for path in sys.path:
        if path not in pkg_resources.working_set.entries:
            pkg_resources.working_set.add_entry(path)

cmd = [quote(sys.executable),
       '-c',
       quote('from setuptools.command.easy_install import main; main()'),
       '-mqNxd',
       quote(eggs_dir)]

if not has_broken_dash_S:
    cmd.insert(1, '-S')

find_links = options.download_base
if not find_links:
    find_links = os.environ.get('bootstrap-testing-find-links')
if not find_links and options.accept_buildout_test_releases:
    find_links = 'http://downloads.buildout.org/'
if find_links:
    cmd.extend(['-f', quote(find_links)])

if options.use_distribute:
    setup_requirement = 'distribute'
else:
    setup_requirement = 'setuptools'
ws = pkg_resources.working_set
setup_requirement_path = ws.find(
    pkg_resources.Requirement.parse(setup_requirement)).location
env = dict(
    os.environ,
    PYTHONPATH=setup_requirement_path)

requirement = 'zc.buildout'
version = options.version
if version is None and not options.accept_buildout_test_releases:
    # Figure out the most recent final version of zc.buildout.
    import setuptools.package_index
    _final_parts = '*final-', '*final'

    def _final_version(parsed_version):
        for part in parsed_version:
            if (part[:1] == '*') and (part not in _final_parts):
                return False
        return True
    index = setuptools.package_index.PackageIndex(
        search_path=[setup_requirement_path])
    if find_links:
        index.add_find_links((find_links,))
    req = pkg_resources.Requirement.parse(requirement)
    if index.obtain(req) is not None:
        best = []
        bestv = None
        for dist in index[req.project_name]:
            distv = dist.parsed_version
            if distv >= pkg_resources.parse_version('2dev'):
                continue
            if _final_version(distv):
                if bestv is None or distv > bestv:
                    best = [dist]
                    bestv = distv
                elif distv == bestv:
                    best.append(dist)
        if best:
            best.sort()
            version = best[-1].version

if version:
    requirement += '=='+version
else:
    requirement += '<2dev'

cmd.append(requirement)

if is_jython:
    import subprocess
    exitcode = subprocess.Popen(cmd, env=env).wait()
else:  # Windows prefers this, apparently; otherwise we would prefer subprocess
    exitcode = os.spawnle(*([os.P_WAIT, sys.executable] + cmd + [env]))
if exitcode != 0:
    sys.stdout.flush()
    sys.stderr.flush()
    print ("An error occurred when trying to install zc.buildout. "
           "Look above this message for any errors that "
           "were output by easy_install.")
    sys.exit(exitcode)

ws.add_entry(eggs_dir)
ws.require(requirement)
import zc.buildout.buildout

# If there isn't already a command in the args, add bootstrap
if not [a for a in args if '=' not in a]:
    args.append('bootstrap')


# if -c was provided, we push it back into args for buildout's main function
if options.config_file is not None:
    args[0:0] = ['-c', options.config_file]

zc.buildout.buildout.main(args)
if not options.eggs:  # clean up temporary egg directory
    shutil.rmtree(eggs_dir)

########NEW FILE########
__FILENAME__ = configs
CLIENT_ID = ""
CLIENT_SECRET = ""
########NEW FILE########
__FILENAME__ = app
# Python imports
from flask import request, session, render_template, redirect, url_for

# Import glass library
import glass

# Import foursquare library
import foursquare

# Config imports
import config

app = glass.Application(
    client_id=config.GOOGLE_CLIENT_ID,
    client_secret=config.GOOGLE_CLIENT_SECRET,
    scopes=config.GOOGLE_SCOPES,
    template_folder="templates",
    static_url_path='/static',
    static_folder='static')

# Set the secret key for flask session.  keep this really secret: (but here it's not ;) )
app.web.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

# map of userGoogleToken -> userFoursquareToken
FOURSQUARE_TOKENS = {}

# Return basic foursquare client
def foursquare_client():
    return foursquare.Foursquare(client_id=config.FOURSQUARE_CLIENT_ID, client_secret=config.FOURSQUARE_CLIENT_SECRET, redirect_uri=config.FOURSQUARE_CLIENT_REDIRECT)

@app.web.route("/")
def index():
    return render_template("index.html", auth=False)

@app.subscriptions.login
def login(user):
    print "google user: %s" % (user.token)
    session['token'] = user.token
    return redirect("/foursquare/authorize")

@app.subscriptions.location
def change_location(user):
    # Get last known location
    location = user.location()
    llat = location.get('latitude')
    llong = location.get('longitude')

    # Get foursquare client
    client = foursquare.Foursquare(access_token=FOURSQUARE_TOKENS[user.token])

    # Search venues on Foursquare
    venues = client.venues.search(params={'ll': llat+','+llong, 'llAcc': location.get('accuracy')})
    if len(venues['venues']) > 0:
    	# Post card with result
    	user.timeline.post_template("venue.html", venue=venues['venues'][0], llat=llat, llong=llong)


@app.web.route("/foursquare/authorize")
def foursquare_authorize():
    client = foursquare_client()
    return redirect(client.oauth.auth_url())

@app.web.route("/foursquare/callback")
def foursquare_callback():
    code = request.args.get('code', None)
    client = foursquare_client()

    if code is None or not 'token' in session:
        return render_template("index.html", auth=False)

    # Interrogate foursquare's servers to get the user's access_token
    access_token = client.oauth.get_token(code)

    # Add token to the map
    FOURSQUARE_TOKENS[session['token']] = access_token

    # Apply the returned access token to the client
    client.set_access_token(access_token)

    # Get the user's data
    user = client.users()
    username = user['user']['firstName']

    print "foursquare user: %s" % (access_token), username

    # Send a welcome message to the glass
    userglass = glass.User(app=app, token=session['token'])
    userglass.timeline.post(text="Welcome %s!" % username)
    
    return render_template("index.html", auth=True)


if __name__ == '__main__':
    print "Starting application at %s:%i" % (config.HOST, config.PORT)
    app.run(port=config.PORT, host=config.HOST)
    
########NEW FILE########
__FILENAME__ = config
# Application
HOST = "localhost"
PORT = 5000

# Google
GOOGLE_CLIENT_ID = ""
GOOGLE_CLIENT_SECRET = ""
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/glass.location',
    'https://www.googleapis.com/auth/glass.timeline',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email'
]

# Foursquare
FOURSQUARE_CLIENT_ID = ""
FOURSQUARE_CLIENT_SECRET = ""
FOURSQUARE_CLIENT_REDIRECT = "http://%s:%i/foursquare/callback" % (HOST, PORT)

########NEW FILE########
__FILENAME__ = hello
# Import glass library
import glass

# Import app configs
import configs

app = glass.Application(
    name="Hello",
    client_id=configs.CLIENT_ID,
    client_secret=configs.CLIENT_SECRET
)

@app.subscriptions.login
def login(user):
    print "user : %s" % user.token
    user.timeline.post(text="Hello World!")

if __name__ == '__main__':
    app.run(port=8080)
    
########NEW FILE########
__FILENAME__ = html
# Import glass library
import glass

# Import app configs
import configs

app = glass.Application(
    name="Hello",
    client_id=configs.CLIENT_ID,
    client_secret=configs.CLIENT_SECRET
)

@app.subscriptions.login
def login(user):
    print "user : %s" % user.token
    user.timeline.post(html="Hello <b>World</b>")

if __name__ == '__main__':
    app.run(port=8080)
    
########NEW FILE########
__FILENAME__ = location
# Import glass library
import glass

# Import app configs
import configs

app = glass.Application(
    name="Hello",
    client_id=configs.CLIENT_ID,
    client_secret=configs.CLIENT_SECRET
)

@app.subscriptions.login
def login(user):
    profile = user.profile()
    print "user : %s" % profile.get("given_name")
    user.timeline.post(text="Hello %s!" % profile.get("given_name"))

@app.subscriptions.location
def change_location(user):
    # Get last known location
    location = user.location()

    # Post card with location infos
    user.timeline.post(text="You move to (Lat: %s, Long: %s) (Accuracy: %s meters)" % (
        location.get('latitude'),
        location.get('longitude'),
        location.get('accuracy')
    ))

if __name__ == '__main__':
    app.run(port=8080)
    
########NEW FILE########
__FILENAME__ = template
# Import glass library
import glass

# Import app configs
import configs

app = glass.Application(
    name="Hello",
    client_id=configs.CLIENT_ID,
    client_secret=configs.CLIENT_SECRET,
    template_folder="templates"
)

@app.subscriptions.login
def login(user):
    print "user : %s" % user.token
    profile = user.profile()
    user.timeline.post_template("hello.html", name=profile.get("given_name"))

if __name__ == '__main__':
    app.run(port=8080)
    
########NEW FILE########
__FILENAME__ = userinfos
# Import glass library
import glass

# Import app configs
import configs

app = glass.Application(
    name="Hello",
    client_id=configs.CLIENT_ID,
    client_secret=configs.CLIENT_SECRET
)

@app.subscriptions.login
def login(user):
    profile = user.profile()
    print "user : %s" % profile.get("given_name")
    user.timeline.post(text="Hello %s!" % profile.get("given_name"))

if __name__ == '__main__':
    app.run(port=8080)
    
########NEW FILE########
__FILENAME__ = web
# Import glass library
import glass

# Import app configs
import configs

app = glass.Application(
    name="Hello",
    client_id=configs.CLIENT_ID,
    client_secret=configs.CLIENT_SECRET
)

@app.subscriptions.login
def login(user):
    print "user : %s" % user.token
    user.timeline.post(text="Hello World!")

@app.web.route("/")
def index():
    return "Welcome on my Glass Application website !"

if __name__ == '__main__':
    app.run(port=8080)
    
########NEW FILE########
__FILENAME__ = app
# Libs imports
import flask
import rauth
import json
import os

# Local imports
from user import User
from subscriptions import Subscriptions

OAUTH_ACCESS_TOKEN_URL = "https://accounts.google.com/o/oauth2/token"
OAUTH_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/auth"
OAUTH_REDIRECT_URI = "authentification/google"
OAUTH_API_BASE_URL = "https://www.googleapis.com/"
OAUTH_SCOPES = [
    'https://www.googleapis.com/auth/glass.location',
    'https://www.googleapis.com/auth/glass.timeline',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email'
]

class Application(object):
    def __init__(self, 
                name="",
                client_id=None,
                client_secret=None,
                scopes=OAUTH_SCOPES,
                debug=True,
                template_folder='templates',
                **flaskargs):
        self.name = name
        self.debug = debug
        self.web = flask.Flask(self.name, **flaskargs)
        self.template_folder = template_folder
        self.logger = self.web.logger
        self.scopes = scopes
        self.subscriptions = Subscriptions(app=self)
        self.oauth = rauth.OAuth2Service(name=self.name,
                                  client_id=client_id,
                                  client_secret=client_secret,
                                  access_token_url=OAUTH_ACCESS_TOKEN_URL,
                                  authorize_url=OAUTH_AUTHORIZE_URL,
                                  base_url=OAUTH_API_BASE_URL)

    @property
    def oauth_redirect_uri(self):
        return "%s://%s/glass/oauth/callback" % ("https" if self.secure else "http", self.host)

    def _oauth_authorize(self):
        """
        (view) Display the authorization window for Google Glass
        """
        params = {
            'scope': " ".join(self.scopes),
            'state': '/profile',
            'redirect_uri': self.oauth_redirect_uri,
            'response_type': 'code',
            'access_type': 'offline',
            'approval_prompt': 'force'
        }
        url = self.oauth.get_authorize_url(**params)
        return flask.redirect(url)

    def _oauth_callback(self):
        """
        (view) Callback for the oauth
        """
        tokens = self.oauth.get_raw_access_token(data={
            'code': flask.request.args.get('code', ''),
            'redirect_uri': self.oauth_redirect_uri,
            'grant_type': 'authorization_code'
        }).json()
        user = User(tokens=tokens, app=self)

        # Add subscriptions
        self.subscriptions.init_user(user)

        # Call endpoint for user login
        return self.subscriptions.call_endpoint("login", user) or ""

    def prepare(self, host="localhost", port=8080, debug=None, secure=False, public=False):
        """
        Prepare the application server
        """
        self.port = port
        self.host = host
        self.secure = secure
        self.public = public

        if port != 80:
            self.host = "%s:%i" % (self.host, self.port)

        # OAUTH
        self.web.add_url_rule('/glass/oauth/authorize', 'oauth_authorize', self._oauth_authorize)
        self.web.add_url_rule('/glass/oauth/callback', 'oauth_callback', self._oauth_callback)

        self.web.debug = debug or self.debug

    def run(self, **kwargs):
        self.prepare(**kwargs)
        self.web.run(port=self.port, host=("0.0.0.0" if self.public else "127.0.0.1"))



########NEW FILE########
__FILENAME__ = contacts
# Python imports
import os
import json

# Local imports
import exceptions

class Contacts(object):
    """
    Represent contacts for a user
    """

    def __init__(self, user):
        self.user = user
        self.app = user.app

    def get(self, contactid):
        """
        Get a contact
        ref: https://developers.google.com/glass/v1/reference/contacts/get
        """
        r = self.user.request("GET", "/mirror/v1/contacts/%s" % (contactid))
        contact = r.json()
        
        if (contact is None or not "id" in contact):
            raise exceptions.ContactException("Error getting contact ", contact)
        return contact

    def delete(self, contactid):
        """
        Delete a contact
        ref: https://developers.google.com/glass/v1/reference/contacts/delete
        """
        r = self.user.request("DELETE", "/mirror/v1/contacts/%s" % (contactid))

    def patch(self, contactid, **kwargs):
        """
        Patch a contact
        ref: https://developers.google.com/glass/v1/reference/contacts/patch
        """
        r = self.user.request("PATCH", "/mirror/v1/contacts/%s" % (contactid), data=json.dumps(kwargs))
        contact = r.json()
        
        if (contact is None or not "id" in contact):
            raise exceptions.ContactException("Error patching contact ", contact)
        return contact

    def list(self, **kwargs):
        """
        List contacts
        ref: https://developers.google.com/glass/v1/reference/contacts/list
        """
        r = self.user.request("GET", "/mirror/v1/contacts", data=kwargs)
        contacts = r.json()
        
        if (contacts is None or not "items" in contacts):
            raise exceptions.ContactException("Error listing contacts ", contacts)
        return contacts["items"]

    def insert(self, **kwargs):
        """
        Insert a new contact
        ref: https://developers.google.com/glass/v1/reference/contacts/insert
        """
        r = self.user.request("POST", "/mirror/v1/contacts", data=json.dumps(kwargs))
        contact = r.json()
        
        if (contact is None or not "id" in contact):
            raise exceptions.ContactException("Error inserting contact", contact)
        return contact

########NEW FILE########
__FILENAME__ = exceptions

class GlassException(RuntimeError):
    """Base excpetion for glass"""
    pass

class RefreshTokenException(GlassException):
    """user need a new access_token."""

class UserException(GlassException):
    """error with user data."""

class SubscriptionException(GlassException):
    """error posting user subscription."""

class ContactException(GlassException):
    """error with user contacts."""

class TimelineException(GlassException):
    """error with user timeline."""

########NEW FILE########
__FILENAME__ = subscriptions
# Python imports
import hashlib
import json
import flask
from uuid import uuid4

# Local imports
import exceptions
from user import User


class Subscriptions(object):
    """
    Subscriptions repressent subscriptions from the app to glasses notifications
    """

    def __init__(self, app):
        self.app = app
        self.subscriptions = {} # Map of subscriptions to send to google api
        self.endpoints = {}    # map of endpoint -> callback function
        self.tokens = {} # map of userToken -> tokens dict

    def add_subscription(self, collection, operations=[]):
        """
        Add a subscription for glasses

        :param collection: Collection to subscribe to (ex: "timeline")
        :param operations: (list or string) operation to subscribe to (ex: "UPDATE")
        """
        m = hashlib.md5()

        if isinstance(operations, basestring):
            operations = [operations]
        operations.sort()
        m.update("%s:%s" % (collection, "-".join(operations)))
        subscription_id = m.hexdigest()
        if subscription_id in self.subscriptions:
            return False

        # Add subscription to map
        self.subscriptions[subscription_id] = {
            "id": subscription_id,
            "collection": collection,
            "operations": operations
        }

        # Add view for subscription
        def handler():
            data = json.loads(request.data)
            userid = data["userToken"]
            if not userid in self.tokens:
                raise Exception("Callback for a non-existant user")
            user = User(app=self.app, tokens=self.tokens[userid])
            if data["collection"] == "timeline":
                for action in data["actions"]:
                    self.call_endpoint("action."+action["type"], user)
            elif data["collection"] == "locations":
                self.call_endpoint("location", user)

        self.app.web.add_url_rule('/glass/callback/%s' % subscription_id, 'callback_%s' % subscription_id, handler)


    def add_endpoint(self, endpoint, callback):
        """
        Add a function to an endpoint

        :param endpoint: the endpoint name (ex: "login")
        :param callback: the endpoint callback to add 
        """
        if not endpoint in self.endpoints:
            self.endpoints[endpoint] = []
        self.app.logger.debug("Add callback to endpoint %s" % endpoint)
        self.endpoints[endpoint].append(callback)

    def call_endpoint(self, endpoint, *args, **kwargs):
        """
        Call callbacks for and endpoint

        :param endpoint: the endpoint name (ex: "login")
        :param *args, **kwargs: params for the callback
        """
        back = None

        if not endpoint in self.endpoints:
            return back

        self.app.logger.debug("Call endpoint %s" % endpoint)
        for callback in self.endpoints[endpoint]:
            back = callback(*args, **kwargs)
        return back

    def init_user(self, user):
        """
        Connect to the user notifications using registred subscriptions
        """
        userUniqueId = [k for k, v in self.tokens.iteritems() if v == user.token]
        if len(userUniqueId) == 0:
            userUniqueId = str(uuid4())
            if userUniqueId in self.tokens:
                # random id alredy used
                return self.subscribe_user(user)

        # Set user token to the map
        self.tokens[userUniqueId] = user.tokens

        # Subscribe
        for sid, subscription in self.subscriptions.items():
            callback_url = "%s/glass/callback/%s" % (self.app.host, subscription["id"])
            result = user.request("POST", "/mirror/v1/subscriptions", data=json.dumps({
                "collection": subscription["collection"],
                "userToken": userUniqueId,
                "operation": subscription["operations"],
                "callbackUrl": callback_url
            })).json()
            if (result is None or not "id" in result):
                raise exceptions.SubscriptionException("Error posting subscription ", result)
        return True

    def login(self, f):
        """
        A decorator that is used to register a function for when an user login
        """
        self.add_endpoint("login", f)
        return f

    def location(self, f):
        """
        A decorator that is used to register a function for when an user location changed
        """
        self.add_subscription("locations")
        self.add_endpoint("location", f)
        return f

    def action(self, action, **options):
        """
        A decorator that is used to register a function for an user action
        """
        def decorator(f):
            self.add_subscription("timeline", "UPDATE")
            self.add_endpoint("action.%s" % action, f)
        return decorator

########NEW FILE########
__FILENAME__ = timeline
# Python imports
import os
import json
from jinja2 import Template

# Local imports
import exceptions

class Timeline(object):
    """
    Represent an user timeline

    Post to timeline using : timeline.post
    examples :
        timeline.post(text="Hello World")
    """

    def __init__(self, user):
        self.user = user
        self.app = user.app

    def get(self, cardid):
        """
        Get a card from the timeline
        ref: https://developers.google.com/glass/v1/reference/timeline/get
        """
        r = self.user.request("GET", "/mirror/v1/timeline/%s" % (cardid))
        card = r.json()
        
        if (card is None or not "id" in card):
            raise exceptions.TimelineException("Error getting card from timeline ", card)
        return card

    def delete(self, cardid):
        """
        Delete a card from the timeline
        ref: https://developers.google.com/glass/v1/reference/timeline/get
        """
        r = self.user.request("DELETE", "/mirror/v1/timeline/%s" % (cardid))

    def patch(self, cardid, **kwargs):
        """
        Patch a card in the timeline
        ref: https://developers.google.com/glass/v1/reference/timeline/get
        """
        r = self.user.request("PATCH", "/mirror/v1/timeline/%s" % (cardid), data=json.dumps(kwargs))
        card = r.json()
        
        if (card is None or not "id" in card):
            raise exceptions.TimelineException("Error patching card in timeline ", card)
        return card

    def list(self, **kwargs):
        """
        List cards in the timeline
        ref: https://developers.google.com/glass/v1/reference/timeline/list
        """
        r = self.user.request("GET", "/mirror/v1/timeline", data=kwargs)
        cards = r.json()
        
        if (cards is None or not "items" in cards):
            raise exceptions.TimelineException("Error listing cards in timeline ", cards)
        return cards["items"]

    def post(self, **kwargs):
        """
        Post a card to glass timeline
        ref: https://developers.google.com/glass/v1/reference/timeline/insert

        :param text: text content for the card
        :param html : html content for the card
        """
        r = self.user.request("POST", "/mirror/v1/timeline", data=json.dumps(kwargs))
        card = r.json()
        
        if (card is None or not "id" in card):
            raise exceptions.TimelineException("Error posting card to timeline ", card)
        return card

    def post_template(self, template, **kwargs):
        """
        Post a card with an html template

        :param template: name of the template
        """
        path = os.path.join(self.app.template_folder, template)
        with open(path, "r") as templatefile:
            template = Template(templatefile.read())
            output = template.render(**kwargs)
            print output
            return self.post(html=output)

########NEW FILE########
__FILENAME__ = user
# Python imports
import requests

# Local imports
import exceptions
from timeline import Timeline
from contacts import Contacts

class User(object):
    """
    Represent an user for an application

    Access Google Glass timeline using : user.timeline
    Each user is defined by unique token : user.token
    """

    def __init__(self, app=None, token=None, refresh_token=None, tokens=None):

        if tokens:
            token = tokens["access_token"]
            refresh_token = tokens["refresh_token"]

        self.app = app
        self.token = token
        self.refresh_token = refresh_token
        
        self.session = self.app.oauth.get_session(token=self.token)
        self.session.headers.update({'Content-Type': 'application/json'})

        self.timeline = Timeline(self)
        self.contacts = Contacts(self)

    def refresh_token(self):
        """
        Refresh user token and return tokens dict
        """
        if not self.refresh_token:
            raise Exception("No refresh token for this user")
        tokens = self.app.oauth.get_raw_access_token(data={
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token'
        }).json()
        self.token = tokens["access_token"]
        return self.tokens

    def request(self, *args, **kwargs):
        """
        Return a request with the user session
        """
        r = self.session.request(*args, **kwargs)
        try:
            r.raise_for_status()
        except requests.HTTPError, e:
            if e.response.status_code == 401:
                raise exceptions.RefreshTokenException()
            else:
                raise e
        return r

    @property
    def tokens(self):
        """
        Return tokens in a dict
        """
        return {
            "access_token": self.token,
            "refresh_token": self.refresh_token
        }

    def profile(self):
        """
        Return profile informations about this user
        """
        r = self.request("GET", "oauth2/v1/userinfo", params={'alt': 'json'})
        profile = r.json()
        
        if (profile is None
        or not "given_name" in profile
        or not "email" in profile
        or not "name" in profile):
            raise exceptions.UserException("Invalid user profile")
        return profile

    def location(self, lid="latest"):
        """
        Return the last known location or a specific location

        :param lid: location id ("latest" for the last known location)
        """
        r = self.request("GET", "mirror/v1/locations/%s" % (lid))
        location = r.json()
        
        if (location is None
        or not "latitude" in location
        or not "longitude" in location):
            raise exceptions.UserException("Invalid user location")
        return location

########NEW FILE########
__FILENAME__ = sitecustomize
import sys
sys.setdefaultencoding('latin-1')
########NEW FILE########
