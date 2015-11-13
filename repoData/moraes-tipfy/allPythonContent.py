__FILENAME__ = config
# -*- coding: utf-8 -*-
"""App configuration."""
config = {}

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-
"""WSGI app setup."""
import os
import sys

if 'lib' not in sys.path:
    # Add lib as primary libraries directory, with fallback to lib/dist
    # and optionally to lib/dist.zip, loaded using zipimport.
    sys.path[0:0] = ['lib', 'lib/dist', 'lib/dist.zip']

from tipfy import Tipfy
from config import config
from urls import rules


def enable_appstats(app):
    """Enables appstats middleware."""
    if debug:
        return

    from google.appengine.ext.appstats.recording import appstats_wsgi_middleware
    app.wsgi_app = appstats_wsgi_middleware(app.wsgi_app)


def enable_jinja2_debugging():
    """Enables blacklisted modules that help Jinja2 debugging."""
    if not debug:
        return

    # This enables better debugging info for errors in Jinja2 templates.
    from google.appengine.tools.dev_appserver import HardenedModulesHook
    HardenedModulesHook._WHITE_LIST_C_MODULES += ['_ctypes', 'gestalt']


# Is this the development server?
debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

# Instantiate the application.
app = Tipfy(rules=rules, config=config, debug=debug)
enable_appstats(app)
enable_jinja2_debugging()


def main():
    # Run the app.
    app.run()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
"""URL definitions."""
from tipfy import Rule

rules = [
    Rule('/', name='hello-world', handler='hello_world.handlers.HelloWorldHandler'),
    Rule('/pretty', name='hello-world-pretty', handler='hello_world.handlers.PrettyHelloWorldHandler'),
]

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

import os, shutil, sys, tempfile, textwrap, urllib, urllib2, subprocess
from optparse import OptionParser

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
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
import site
sys.path[:] = clean_path
for k, v in sys.modules.items():
    if k in ('setuptools', 'pkg_resources') or (
        hasattr(v, '__path__') and
        len(v.__path__)==1 and
        not os.path.exists(os.path.join(v.__path__[0],'__init__.py'))):
        # This is a namespace package.  Remove it.
        sys.modules.pop(k)

is_jython = sys.platform.startswith('java')

setuptools_source = 'http://peak.telecommunity.com/dist/ez_setup.py'
distribute_source = 'http://python-distribute.org/distribute_setup.py'

# parsing arguments
def normalize_to_url(option, opt_str, value, parser):
    if value:
        if '://' not in value: # It doesn't smell like a URL.
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
                   action="store_true", dest="use_distribute", default=True,
                   help="Use Distribute rather than Setuptools.")
parser.add_option("--setup-source", action="callback", dest="setup_source",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or file location for the setup file. "
                        "If you use Setuptools, this will default to " +
                        setuptools_source + "; if you use Distribute, this "
                        "will default to " + distribute_source +"."))
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

# if -c was provided, we push it back into args for buildout's main function
if options.config_file is not None:
    args += ['-c', options.config_file]

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
    args.append('buildout:accept-buildout-test-releases=true')
args.append('bootstrap')

try:
    import pkg_resources
    import setuptools # A flag.  Sometimes pkg_resources is installed alone.
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
    requirement = '=='.join((requirement, version))
cmd.append(requirement)

if is_jython:
    import subprocess
    exitcode = subprocess.Popen(cmd, env=env).wait()
else: # Windows prefers this, apparently; otherwise we would prefer subprocess
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
zc.buildout.buildout.main(args)
if not options.eggs: # clean up temporary egg directory
    shutil.rmtree(eggs_dir)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Tipfy documentation build configuration file, created by
# sphinx-quickstart on Tue Nov 10 20:33:43 2009.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
curr_path = os.path.abspath(os.path.dirname(__file__))
project_path = os.path.join(curr_path, '..', 'project')

# SDK
sdk_path = os.path.join(project_path, 'var', 'parts', 'google_appengine')
sys.path.insert(0, os.path.join(sdk_path, 'lib', 'django'))
sys.path.insert(0, os.path.join(sdk_path, 'lib', 'webob'))
sys.path.insert(0, os.path.join(sdk_path, 'lib', 'yaml', 'lib'))
sys.path.insert(0, sdk_path)

# App libs.
sys.path.insert(0, os.path.join(project_path, 'app', 'lib', 'dist'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.coverage']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Tipfy'
copyright = u'2010, Tipfy Group'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.6.3'
# The full version, including alpha/beta/rc tags.
release = '0.6.3'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = []

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'manni'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'tipfy'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    #'rightsidebar': 'true',
}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['./_theme']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
html_sidebars = {
    '**': [
        'localtoc.html',
        #'relations.html',
        'globaltoc.html',
        #'searchbox.html',
        'sourcelink.html',
    ],
}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Tipfydoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Tipfy.tex', u'Tipfy Documentation',
   u'Rodrigo Moraes', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-
"""App configuration."""
config = {}

# Configurations for the 'tipfy' module.
config['tipfy'] = {
    'auth_store_class': 'tipfy.auth.MultiAuthStore',
}

config['tipfy.sessions'] = {
    'secret_key': 'XXXXXXXXXXXXXXX',
}

config['tipfy.auth.facebook'] = {
    'api_key':    'XXXXXXXXXXXXXXX',
    'app_secret': 'XXXXXXXXXXXXXXX',
}

config['tipfy.auth.friendfeed'] = {
    'consumer_key':    'XXXXXXXXXXXXXXX',
    'consumer_secret': 'XXXXXXXXXXXXXXX',
}

config['tipfy.auth.twitter'] = {
    'consumer_key':    'XXXXXXXXXXXXXXX',
    'consumer_secret': 'XXXXXXXXXXXXXXX',
}

config['tipfyext.jinja2'] = {
    'environment_args': {
        'autoescape': True,
        'extensions': [
            'jinja2.ext.autoescape',
            'jinja2.ext.i18n',
            'jinja2.ext.with_'
        ],
    },
}

########NEW FILE########
__FILENAME__ = handlers
from werkzeug import cached_property

from tipfy import RequestHandler
from tipfy.auth import (login_required, user_required,
    UserRequiredIfAuthenticatedMiddleware)
from tipfy.auth.facebook import FacebookMixin
from tipfy.auth.friendfeed import FriendFeedMixin
from tipfy.auth.google import GoogleMixin
from tipfy.auth.twitter import TwitterMixin
from tipfy.sessions import SessionMiddleware
from tipfy.utils import json_encode

from tipfyext.jinja2 import Jinja2Mixin
from tipfyext.wtforms import Form, fields, validators

# ----- Forms -----

REQUIRED = validators.required()

class LoginForm(Form):
    username = fields.TextField('Username', validators=[REQUIRED])
    password = fields.PasswordField('Password', validators=[REQUIRED])
    remember = fields.BooleanField('Keep me signed in')


class SignupForm(Form):
    nickname = fields.TextField('Nickname', validators=[REQUIRED])


class RegistrationForm(Form):
    username = fields.TextField('Username', validators=[REQUIRED])
    password = fields.PasswordField('Password', validators=[REQUIRED])
    password_confirm = fields.PasswordField('Confirm the password', validators=[REQUIRED])


# ----- Handlers -----

class BaseHandler(RequestHandler, Jinja2Mixin):
    middleware = [SessionMiddleware(), UserRequiredIfAuthenticatedMiddleware()]

    @cached_property
    def messages(self):
        """A list of status messages to be displayed to the user."""
        return self.session.get_flashes(key='_messages')

    def render_response(self, filename, **kwargs):
        auth_session = None
        if self.auth.session:
            auth_session = self.auth.session

        kwargs.update({
            'auth_session': auth_session,
            'current_user': self.auth.user,
            'login_url':    self.auth.login_url(),
            'logout_url':   self.auth.logout_url(),
            'current_url':  self.request.url,
        })
        if self.messages:
            kwargs['messages'] = json_encode([dict(body=body, level=level)
                for body, level in self.messages])

        return super(BaseHandler, self).render_response(filename, **kwargs)

    def redirect_path(self, default='/'):
        if '_continue' in self.session:
            url = self.session.pop('_continue')
        else:
            url = self.request.args.get('continue', '/')

        if not url.startswith('/'):
            url = default

        return url

    def _on_auth_redirect(self):
        """Redirects after successful authentication using third party
        services.
        """
        if '_continue' in self.session:
            url = self.session.pop('_continue')
        else:
            url = '/'

        if not self.auth.user:
            url = self.auth.signup_url()

        return self.redirect(url)


class HomeHandler(BaseHandler):
    def get(self, **kwargs):
        return self.render_response('home.html', section='home')


class ContentHandler(BaseHandler):
    @user_required
    def get(self, **kwargs):
        return self.render_response('content.html', section='content')


class LoginHandler(BaseHandler):
    def get(self, **kwargs):
        redirect_url = self.redirect_path()

        if self.auth.user:
            # User is already registered, so don't display the signup form.
            return self.redirect(redirect_url)

        opts = {'continue': self.redirect_path()}
        context = {
            'form':                 self.form,
            'facebook_login_url':   self.url_for('auth/facebook', **opts),
            'friendfeed_login_url': self.url_for('auth/friendfeed', **opts),
            'google_login_url':     self.url_for('auth/google', **opts),
            'twitter_login_url':    self.url_for('auth/twitter', **opts),
            'yahoo_login_url':      self.url_for('auth/yahoo', **opts),
        }
        return self.render_response('login.html', **context)

    def post(self, **kwargs):
        redirect_url = self.redirect_path()

        if self.auth.user:
            # User is already registered, so don't display the signup form.
            return self.redirect(redirect_url)

        if self.form.validate():
            username = self.form.username.data
            password = self.form.password.data
            remember = self.form.remember.data

            res = self.auth.login_with_form(username, password, remember)
            if res:
                self.session.add_flash('Welcome back!', 'success', '_messages')
                return self.redirect(redirect_url)

        self.messages.append(('Authentication failed. Please try again.',
            'error'))
        return self.get(**kwargs)

    @cached_property
    def form(self):
        return LoginForm(self.request)


class LogoutHandler(BaseHandler):
    def get(self, **kwargs):
        self.auth.logout()
        return self.redirect(self.redirect_path())


class SignupHandler(BaseHandler):
    @login_required
    def get(self, **kwargs):
        if self.auth.user:
            # User is already registered, so don't display the signup form.
            return self.redirect(self.redirect_path())

        return self.render_response('signup.html', form=self.form)

    @login_required
    def post(self, **kwargs):
        redirect_url = self.redirect_path()

        if self.auth.user:
            # User is already registered, so don't process the signup form.
            return self.redirect(redirect_url)

        if self.form.validate():
            auth_id = self.auth.session.get('id')
            user = self.auth.create_user(self.form.nickname.data, auth_id)
            if user:
                self.auth.login_with_auth_id(user.auth_id, True)
                self.session.add_flash('You are now registered. Welcome!',
                    'success', '_messages')
                return self.redirect(redirect_url)
            else:
                self.messages.append(('This nickname is already registered.',
                    'error'))
                return self.get(**kwargs)

        self.messages.append(('A problem occurred. Please correct the '
            'errors listed in the form.', 'error'))
        return self.get(**kwargs)

    @cached_property
    def form(self):
        return SignupForm(self.request)


class RegisterHandler(BaseHandler):
    def get(self, **kwargs):
        redirect_url = self.redirect_path()

        if self.auth.user:
            # User is already registered, so don't display the registration form.
            return self.redirect(redirect_url)

        return self.render_response('register.html', form=self.form)

    def post(self, **kwargs):
        redirect_url = self.redirect_path()

        if self.auth.user:
            # User is already registered, so don't process the signup form.
            return self.redirect(redirect_url)

        if self.form.validate():
            username = self.form.username.data
            password = self.form.password.data
            password_confirm = self.form.password_confirm.data

            if password != password_confirm:
                self.messages.append(("Password confirmation didn't match.",
                    'error'))
                return self.get(**kwargs)

            auth_id = 'own|%s' % username
            user = self.auth.create_user(username, auth_id, password=password)
            if user:
                self.auth.login_with_auth_id(user.auth_id, True)
                self.session.add_flash('You are now registered. Welcome!',
                    'success', '_messages')
                return self.redirect(redirect_url)
            else:
                self.messages.append(('This nickname is already registered.',
                    'error'))
                return self.get(**kwargs)

        self.messages.append(('A problem occurred. Please correct the '
            'errors listed in the form.', 'error'))
        return self.get(**kwargs)

    @cached_property
    def form(self):
        return RegistrationForm(self.request)


class FacebookAuthHandler(BaseHandler, FacebookMixin):
    def head(self, **kwargs):
        """Facebook will make a HEAD request before returning a callback."""
        return self.app.response_class('')

    def get(self):
        url = self.redirect_path()

        if self.auth.session:
            # User is already signed in, so redirect back.
            return self.redirect(url)

        self.session['_continue'] = url

        if self.request.args.get('session', None):
            return self.get_authenticated_user(self._on_auth)

        return self.authenticate_redirect()

    def _on_auth(self, user):
        """
        """
        if not user:
            self.abort(403)

        # try user name, fallback to uid.
        username = user.pop('username', None)
        if not username:
            username = user.pop('uid', '')

        auth_id = 'facebook|%s' % username
        self.auth.login_with_auth_id(auth_id, remember=True,
            session_key=user.get('session_key'))
        return self._on_auth_redirect()


class FriendFeedAuthHandler(BaseHandler, FriendFeedMixin):
    """
    """
    def get(self):
        url = self.redirect_path()

        if self.auth.session:
            # User is already signed in, so redirect back.
            return self.redirect(url)

        self.session['_continue'] = url

        if self.request.args.get('oauth_token', None):
            return self.get_authenticated_user(self._on_auth)

        return self.authorize_redirect()

    def _on_auth(self, user):
        if not user:
            self.abort(403)

        auth_id = 'friendfeed|%s' % user.pop('username', '')
        self.auth.login_with_auth_id(auth_id, remember=True,
            access_token=user.get('access_token'))
        return self._on_auth_redirect()


class TwitterAuthHandler(BaseHandler, TwitterMixin):
    def get(self):
        url = self.redirect_path()

        if self.auth.user:
            # User is already signed in, so redirect back.
            return self.redirect(url)

        self.session['_continue'] = url

        if self.request.args.get('oauth_token', None):
            return self.get_authenticated_user(self._on_auth)

        return self.authorize_redirect(callback_uri='/auth/twitter/')

    def _on_auth(self, user):
        if not user:
            self.abort(403)

        auth_id = 'twitter|%s' % user.pop('username', '')
        self.auth.login_with_auth_id(auth_id, remember=True,
            access_token=user.get('access_token'))
        return self._on_auth_redirect()


class GoogleAuthHandler(BaseHandler, GoogleMixin):
    def get(self):
        url = self.redirect_path()

        if self.auth.session:
            # User is already signed in, so redirect back.
            return self.redirect(url)

        self.session['_continue'] = url

        if self.request.args.get('openid.mode', None):
            return self.get_authenticated_user(self._on_auth)

        return self.authenticate_redirect()

    def _on_auth(self, user):
        if not user:
            self.abort(403)

        auth_id = 'google|%s' % user.pop('email', '')
        self.auth.login_with_auth_id(auth_id, remember=True)
        return self._on_auth_redirect()

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-
"""WSGI app setup."""
import os
import sys

if 'lib' not in sys.path:
    # Add lib as primary libraries directory, with fallback to lib/dist
    # and optionally to lib/dist.zip, loaded using zipimport.
    sys.path[0:0] = ['lib', 'lib/dist', 'lib/dist.zip']

from tipfy import Tipfy
from config import config
from urls import rules


def enable_appstats(app):
    """Enables appstats middleware."""
    from google.appengine.ext.appstats.recording import \
        appstats_wsgi_middleware
    app.wsgi_app = appstats_wsgi_middleware(app.wsgi_app)


def enable_jinja2_debugging():
    """Enables blacklisted modules that help Jinja2 debugging."""
    if not debug:
        return

    # This enables better debugging info for errors in Jinja2 templates.
    from google.appengine.tools.dev_appserver import HardenedModulesHook
    HardenedModulesHook._WHITE_LIST_C_MODULES += ['_ctypes', 'gestalt']


# Is this the development server?
debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

# Instantiate the application.
app = Tipfy(rules=rules, config=config, debug=debug)
enable_appstats(app)
enable_jinja2_debugging()


def main():
    # Run the app.
    app.run()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
"""URL definitions."""
from tipfy import Rule

rules = [
    Rule('/', endpoint='home', handler='handlers.HomeHandler'),
    Rule('/auth/login', endpoint='auth/login', handler='handlers.LoginHandler'),
    Rule('/auth/logout', endpoint='auth/logout', handler='handlers.LogoutHandler'),
    Rule('/auth/signup', endpoint='auth/signup', handler='handlers.SignupHandler'),
    Rule('/auth/register', endpoint='auth/register', handler='handlers.RegisterHandler'),

    Rule('/auth/facebook/', endpoint='auth/facebook', handler='handlers.FacebookAuthHandler'),
    Rule('/auth/friendfeed/', endpoint='auth/friendfeed', handler='handlers.FriendFeedAuthHandler'),
    Rule('/auth/google/', endpoint='auth/google', handler='handlers.GoogleAuthHandler'),
    Rule('/auth/twitter/', endpoint='auth/twitter', handler='handlers.TwitterAuthHandler'),
    Rule('/auth/yahoo/', endpoint='auth/yahoo', handler='handlers.YahooAuthHandler'),

    Rule('/content', endpoint='content/index', handler='handlers.ContentHandler'),
]

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

import os, shutil, sys, tempfile, textwrap, urllib, urllib2, subprocess
from optparse import OptionParser

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
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
import site
sys.path[:] = clean_path
for k, v in sys.modules.items():
    if k in ('setuptools', 'pkg_resources') or (
        hasattr(v, '__path__') and
        len(v.__path__)==1 and
        not os.path.exists(os.path.join(v.__path__[0],'__init__.py'))):
        # This is a namespace package.  Remove it.
        sys.modules.pop(k)

is_jython = sys.platform.startswith('java')

setuptools_source = 'http://peak.telecommunity.com/dist/ez_setup.py'
distribute_source = 'http://python-distribute.org/distribute_setup.py'

# parsing arguments
def normalize_to_url(option, opt_str, value, parser):
    if value:
        if '://' not in value: # It doesn't smell like a URL.
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
                   action="store_true", dest="use_distribute", default=True,
                   help="Use Distribute rather than Setuptools.")
parser.add_option("--setup-source", action="callback", dest="setup_source",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or file location for the setup file. "
                        "If you use Setuptools, this will default to " +
                        setuptools_source + "; if you use Distribute, this "
                        "will default to " + distribute_source +"."))
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

# if -c was provided, we push it back into args for buildout's main function
if options.config_file is not None:
    args += ['-c', options.config_file]

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
    args.append('buildout:accept-buildout-test-releases=true')
args.append('bootstrap')

try:
    import pkg_resources
    import setuptools # A flag.  Sometimes pkg_resources is installed alone.
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
    requirement = '=='.join((requirement, version))
cmd.append(requirement)

if is_jython:
    import subprocess
    exitcode = subprocess.Popen(cmd, env=env).wait()
else: # Windows prefers this, apparently; otherwise we would prefer subprocess
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
zc.buildout.buildout.main(args)
if not options.eggs: # clean up temporary egg directory
    shutil.rmtree(eggs_dir)

########NEW FILE########
__FILENAME__ = action_install_packages
# -*- coding: utf-8 -*-
import datetime
import logging
import os
import shutil
import tempfile
import uuid

from z3c.recipe.scripts.scripts import Scripts

from appfy.recipe import (copytree, ignore_patterns, include_patterns,
    rmfiles, zipdir)


LIB_README = """Warning!
========

This directory is removed every time the buildout tool runs, so don't place
or edit things here because any changes will be lost!

Use a different directory for extra libraries instead of this one."""


class Recipe(Scripts):
    def __init__(self, buildout, name, opts):
        # Set a logger with the section name.
        self.logger = logging.getLogger(name)

        # Unzip eggs by default or we can't use some.
        opts.setdefault('unzip', 'true')

        self.eggs_dir = buildout['buildout']['eggs-directory']
        self.parts_dir = buildout['buildout']['parts-directory']
        self.temp_dir = os.path.join(self.parts_dir, 'temp')

        lib_dir = opts.get('lib-directory', 'distlib')
        self.lib_path = os.path.abspath(lib_dir)

        self.use_zip = opts.get('use-zipimport', 'false') == 'true'
        if self.use_zip:
            self.lib_path += '.zip'

        # Set list of globs and packages to be ignored.
        self.ignore_globs = [i for i in opts.get('ignore-globs', '') \
            .splitlines() if i.strip()]
        self.ignore_packages = [i for i in opts.get('ignore-packages', '') \
            .splitlines() if i.strip()]

        self.delete_safe = opts.get('delete-safe', 'true') != 'false'
        opts.setdefault('eggs', '')
        super(Recipe, self).__init__(buildout, name, opts)

    def install(self):
        # Get all installed packages.
        reqs, ws = self.working_set()
        paths = self.get_package_paths(ws)

        # For now we only support installing them in the app dir.
        # In the future we may support installing libraries in the parts dir.
        self.install_in_app_dir(paths)

        return super(Recipe, self).install()

    update = install

    def install_in_app_dir(self, paths):
        # Delete old libs.
        self.delete_libs()

        if self.use_zip:
            # Create temporary directory for the zip files.
            tmp_dir = os.path.join(tempfile.gettempdir(), uuid.uuid4().hex)
        else:
            tmp_dir = self.lib_path

        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)

        # Copy all files.
        for name, src in paths:
            if name in self.ignore_packages:
                # This package or module must be ignored.
                continue

            dst = os.path.join(tmp_dir, name)
            if not os.path.isdir(src):
                # Try single files listed as modules.
                src += '.py'
                dst += '.py'
                if not os.path.isfile(src) or os.path.isfile(dst):
                    continue

            self.logger.info('Copying %r...' % src)

            copytree(src, dst, os.path.dirname(src) + os.sep,
                ignore=ignore_patterns(*self.ignore_globs),
                logger=self.logger)

        # Save README.
        f = open(os.path.join(tmp_dir, 'README.txt'), 'w')
        f.write(LIB_README)
        f.close()

        if self.use_zip:
            # Zip file and remove temporary dir.
            zipdir(tmp_dir, self.lib_path)
            if os.path.isdir(tmp_dir):
                shutil.rmtree(tmp_dir)

    def get_package_paths(self, ws):
        """Returns the list of package paths to be copied."""
        pkgs = []
        for path in ws.entries:
            lib_paths = self.get_lib_paths(path)
            if not lib_paths:
                self.logger.info('Library not installed: missing egg info for '
                    '%r.' % path)
                continue

            for lib_path in lib_paths:
                pkgs.append((lib_path, os.path.join(path, lib_path)))

        return pkgs

    def get_top_level_libs(self, egg_path):
        top_path = os.path.join(egg_path, 'top_level.txt')
        if not os.path.isfile(top_path):
            return None

        f = open(top_path, 'r')
        libs = f.read().strip()
        f.close()

        # One lib per line.
        return [l.strip() for l in libs.splitlines() if l.strip()]

    def get_lib_paths(self, path):
        """Returns the 'EGG-INFO' or '.egg-info' directory."""
        egg_path = os.path.join(path, 'EGG-INFO')
        if os.path.isdir(egg_path):
            # Unzipped egg metadata.
            return self.get_top_level_libs(egg_path)

        if os.path.isfile(path):
            # Zipped egg? Should we try to unpack it?
            # unpack_archive(path, self.eggs_dir)
            return None

        # Last try: develop eggs.
        elif os.path.isdir(path):
            files = os.listdir(path)
            for filename in files:
                if filename.endswith('.egg-info'):
                    egg_path = os.path.join(path, filename)
                    return self.get_top_level_libs(egg_path)

    def delete_libs(self):
        """If the `delete-safe` option is set to true, move the old libraries
        directory to a temporary directory inside the parts dir instead of
        deleting it.
        """
        if not os.path.exists(self.lib_path):
            # Nothing to delete, so it is safe.
            return

        if self.delete_safe is True:
            # Move directory or zip to temporary backup directory.
            if not os.path.exists(self.temp_dir):
                os.makedirs(self.temp_dir)

            date = datetime.datetime.now().strftime('_%Y_%m_%d_%H_%M_%S')
            filename = os.path.basename(self.lib_path.rstrip(os.sep))
            if self.use_zip:
                filename = filename[:-4] + date + '.zip'
            else:
                filename += date

            dst = os.path.join(self.temp_dir, filename)
            shutil.move(self.lib_path, dst)
            self.logger.info('Saved libraries backup in %r.' % dst)
        else:
            # Simply delete the directory or zip.
            if self.use_zip:
                os.remove(self.lib_path)
                self.logger.info('Removed lib-zip %r.' % self.lib_path)
            else:
                # Delete the directory.
                shutil.rmtree(self.lib_path)
                self.logger.info('Removed lib-directory %r.' % self.lib_path)

########NEW FILE########
__FILENAME__ = argparse
# Author: Steven J. Bethard <steven.bethard@gmail.com>.

"""Command-line parsing library

This module is an optparse-inspired command-line parsing library that:

    - handles both optional and positional arguments
    - produces highly informative usage messages
    - supports parsers that dispatch to sub-parsers

The following is a simple usage example that sums integers from the
command-line and writes the result to a file::

    parser = argparse.ArgumentParser(
        description='sum the integers at the command line')
    parser.add_argument(
        'integers', metavar='int', nargs='+', type=int,
        help='an integer to be summed')
    parser.add_argument(
        '--log', default=sys.stdout, type=argparse.FileType('w'),
        help='the file where the sum should be written')
    args = parser.parse_args()
    args.log.write('%s' % sum(args.integers))
    args.log.close()

The module contains the following public classes:

    - ArgumentParser -- The main entry point for command-line parsing. As the
        example above shows, the add_argument() method is used to populate
        the parser with actions for optional and positional arguments. Then
        the parse_args() method is invoked to convert the args at the
        command-line into an object with attributes.

    - ArgumentError -- The exception raised by ArgumentParser objects when
        there are errors with the parser's actions. Errors raised while
        parsing the command-line are caught by ArgumentParser and emitted
        as command-line messages.

    - FileType -- A factory for defining types of files to be created. As the
        example above shows, instances of FileType are typically passed as
        the type= argument of add_argument() calls.

    - Action -- The base class for parser actions. Typically actions are
        selected by passing strings like 'store_true' or 'append_const' to
        the action= argument of add_argument(). However, for greater
        customization of ArgumentParser actions, subclasses of Action may
        be defined and passed as the action= argument.

    - HelpFormatter, RawDescriptionHelpFormatter, RawTextHelpFormatter,
        ArgumentDefaultsHelpFormatter -- Formatter classes which
        may be passed as the formatter_class= argument to the
        ArgumentParser constructor. HelpFormatter is the default,
        RawDescriptionHelpFormatter and RawTextHelpFormatter tell the parser
        not to change the formatting for help text, and
        ArgumentDefaultsHelpFormatter adds information about argument defaults
        to the help.

All other classes in this module are considered implementation details.
(Also note that HelpFormatter and RawDescriptionHelpFormatter are only
considered public as object names -- the API of the formatter objects is
still considered an implementation detail.)
"""

__version__ = '1.1'
__all__ = [
    'ArgumentParser',
    'ArgumentError',
    'ArgumentTypeError',
    'FileType',
    'HelpFormatter',
    'ArgumentDefaultsHelpFormatter',
    'RawDescriptionHelpFormatter',
    'RawTextHelpFormatter',
    'Namespace',
    'Action',
    'ONE_OR_MORE',
    'OPTIONAL',
    'PARSER',
    'REMAINDER',
    'SUPPRESS',
    'ZERO_OR_MORE',
]


import copy as _copy
import os as _os
import re as _re
import sys as _sys
import textwrap as _textwrap

from gettext import gettext as _


def _callable(obj):
    return hasattr(obj, '__call__') or hasattr(obj, '__bases__')


SUPPRESS = '==SUPPRESS=='

OPTIONAL = '?'
ZERO_OR_MORE = '*'
ONE_OR_MORE = '+'
PARSER = 'A...'
REMAINDER = '...'
_UNRECOGNIZED_ARGS_ATTR = '_unrecognized_args'

# =============================
# Utility functions and classes
# =============================

class _AttributeHolder(object):
    """Abstract base class that provides __repr__.

    The __repr__ method returns a string in the format::
        ClassName(attr=name, attr=name, ...)
    The attributes are determined either by a class-level attribute,
    '_kwarg_names', or by inspecting the instance __dict__.
    """

    def __repr__(self):
        type_name = type(self).__name__
        arg_strings = []
        for arg in self._get_args():
            arg_strings.append(repr(arg))
        for name, value in self._get_kwargs():
            arg_strings.append('%s=%r' % (name, value))
        return '%s(%s)' % (type_name, ', '.join(arg_strings))

    def _get_kwargs(self):
        return sorted(self.__dict__.items())

    def _get_args(self):
        return []


def _ensure_value(namespace, name, value):
    if getattr(namespace, name, None) is None:
        setattr(namespace, name, value)
    return getattr(namespace, name)


# ===============
# Formatting Help
# ===============

class HelpFormatter(object):
    """Formatter for generating usage messages and argument help strings.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def __init__(self,
                 prog,
                 indent_increment=2,
                 max_help_position=24,
                 width=None):

        # default setting for width
        if width is None:
            try:
                width = int(_os.environ['COLUMNS'])
            except (KeyError, ValueError):
                width = 80
            width -= 2

        self._prog = prog
        self._indent_increment = indent_increment
        self._max_help_position = max_help_position
        self._width = width

        self._current_indent = 0
        self._level = 0
        self._action_max_length = 0

        self._root_section = self._Section(self, None)
        self._current_section = self._root_section

        self._whitespace_matcher = _re.compile(r'\s+')
        self._long_break_matcher = _re.compile(r'\n\n\n+')

    # ===============================
    # Section and indentation methods
    # ===============================
    def _indent(self):
        self._current_indent += self._indent_increment
        self._level += 1

    def _dedent(self):
        self._current_indent -= self._indent_increment
        assert self._current_indent >= 0, 'Indent decreased below 0.'
        self._level -= 1

    class _Section(object):

        def __init__(self, formatter, parent, heading=None):
            self.formatter = formatter
            self.parent = parent
            self.heading = heading
            self.items = []

        def format_help(self):
            # format the indented section
            if self.parent is not None:
                self.formatter._indent()
            join = self.formatter._join_parts
            for func, args in self.items:
                func(*args)
            item_help = join([func(*args) for func, args in self.items])
            if self.parent is not None:
                self.formatter._dedent()

            # return nothing if the section was empty
            if not item_help:
                return ''

            # add the heading if the section was non-empty
            if self.heading is not SUPPRESS and self.heading is not None:
                current_indent = self.formatter._current_indent
                heading = '%*s%s:\n' % (current_indent, '', self.heading)
            else:
                heading = ''

            # join the section-initial newline, the heading and the help
            return join(['\n', heading, item_help, '\n'])

    def _add_item(self, func, args):
        self._current_section.items.append((func, args))

    # ========================
    # Message building methods
    # ========================
    def start_section(self, heading):
        self._indent()
        section = self._Section(self, self._current_section, heading)
        self._add_item(section.format_help, [])
        self._current_section = section

    def end_section(self):
        self._current_section = self._current_section.parent
        self._dedent()

    def add_text(self, text):
        if text is not SUPPRESS and text is not None:
            self._add_item(self._format_text, [text])

    def add_usage(self, usage, actions, groups, prefix=None):
        if usage is not SUPPRESS:
            args = usage, actions, groups, prefix
            self._add_item(self._format_usage, args)

    def add_argument(self, action):
        if action.help is not SUPPRESS:

            # find all invocations
            get_invocation = self._format_action_invocation
            invocations = [get_invocation(action)]
            for subaction in self._iter_indented_subactions(action):
                invocations.append(get_invocation(subaction))

            # update the maximum item length
            invocation_length = max([len(s) for s in invocations])
            action_length = invocation_length + self._current_indent
            self._action_max_length = max(self._action_max_length,
                                          action_length)

            # add the item to the list
            self._add_item(self._format_action, [action])

    def add_arguments(self, actions):
        for action in actions:
            self.add_argument(action)

    # =======================
    # Help-formatting methods
    # =======================
    def format_help(self):
        help = self._root_section.format_help()
        if help:
            help = self._long_break_matcher.sub('\n\n', help)
            help = help.strip('\n') + '\n'
        return help

    def _join_parts(self, part_strings):
        return ''.join([part
                        for part in part_strings
                        if part and part is not SUPPRESS])

    def _format_usage(self, usage, actions, groups, prefix):
        if prefix is None:
            prefix = _('usage: ')

        # if usage is specified, use that
        if usage is not None:
            usage = usage % dict(prog=self._prog)

        # if no optionals or positionals are available, usage is just prog
        elif usage is None and not actions:
            usage = '%(prog)s' % dict(prog=self._prog)

        # if optionals and positionals are available, calculate usage
        elif usage is None:
            prog = '%(prog)s' % dict(prog=self._prog)

            # split optionals from positionals
            optionals = []
            positionals = []
            for action in actions:
                if action.option_strings:
                    optionals.append(action)
                else:
                    positionals.append(action)

            # build full usage string
            format = self._format_actions_usage
            action_usage = format(optionals + positionals, groups)
            usage = ' '.join([s for s in [prog, action_usage] if s])

            # wrap the usage parts if it's too long
            text_width = self._width - self._current_indent
            if len(prefix) + len(usage) > text_width:

                # break usage into wrappable parts
                part_regexp = r'\(.*?\)+|\[.*?\]+|\S+'
                opt_usage = format(optionals, groups)
                pos_usage = format(positionals, groups)
                opt_parts = _re.findall(part_regexp, opt_usage)
                pos_parts = _re.findall(part_regexp, pos_usage)
                assert ' '.join(opt_parts) == opt_usage
                assert ' '.join(pos_parts) == pos_usage

                # helper for wrapping lines
                def get_lines(parts, indent, prefix=None):
                    lines = []
                    line = []
                    if prefix is not None:
                        line_len = len(prefix) - 1
                    else:
                        line_len = len(indent) - 1
                    for part in parts:
                        if line_len + 1 + len(part) > text_width:
                            lines.append(indent + ' '.join(line))
                            line = []
                            line_len = len(indent) - 1
                        line.append(part)
                        line_len += len(part) + 1
                    if line:
                        lines.append(indent + ' '.join(line))
                    if prefix is not None:
                        lines[0] = lines[0][len(indent):]
                    return lines

                # if prog is short, follow it with optionals or positionals
                if len(prefix) + len(prog) <= 0.75 * text_width:
                    indent = ' ' * (len(prefix) + len(prog) + 1)
                    if opt_parts:
                        lines = get_lines([prog] + opt_parts, indent, prefix)
                        lines.extend(get_lines(pos_parts, indent))
                    elif pos_parts:
                        lines = get_lines([prog] + pos_parts, indent, prefix)
                    else:
                        lines = [prog]

                # if prog is long, put it on its own line
                else:
                    indent = ' ' * len(prefix)
                    parts = opt_parts + pos_parts
                    lines = get_lines(parts, indent)
                    if len(lines) > 1:
                        lines = []
                        lines.extend(get_lines(opt_parts, indent))
                        lines.extend(get_lines(pos_parts, indent))
                    lines = [prog] + lines

                # join lines into usage
                usage = '\n'.join(lines)

        # prefix with 'usage:'
        return '%s%s\n\n' % (prefix, usage)

    def _format_actions_usage(self, actions, groups):
        # find group indices and identify actions in groups
        group_actions = set()
        inserts = {}
        for group in groups:
            try:
                start = actions.index(group._group_actions[0])
            except ValueError:
                continue
            else:
                end = start + len(group._group_actions)
                if actions[start:end] == group._group_actions:
                    for action in group._group_actions:
                        group_actions.add(action)
                    if not group.required:
                        if start in inserts:
                            inserts[start] += ' ['
                        else:
                            inserts[start] = '['
                        inserts[end] = ']'
                    else:
                        if start in inserts:
                            inserts[start] += ' ('
                        else:
                            inserts[start] = '('
                        inserts[end] = ')'
                    for i in range(start + 1, end):
                        inserts[i] = '|'

        # collect all actions format strings
        parts = []
        for i, action in enumerate(actions):

            # suppressed arguments are marked with None
            # remove | separators for suppressed arguments
            if action.help is SUPPRESS:
                parts.append(None)
                if inserts.get(i) == '|':
                    inserts.pop(i)
                elif inserts.get(i + 1) == '|':
                    inserts.pop(i + 1)

            # produce all arg strings
            elif not action.option_strings:
                part = self._format_args(action, action.dest)

                # if it's in a group, strip the outer []
                if action in group_actions:
                    if part[0] == '[' and part[-1] == ']':
                        part = part[1:-1]

                # add the action string to the list
                parts.append(part)

            # produce the first way to invoke the option in brackets
            else:
                option_string = action.option_strings[0]

                # if the Optional doesn't take a value, format is:
                #    -s or --long
                if action.nargs == 0:
                    part = '%s' % option_string

                # if the Optional takes a value, format is:
                #    -s ARGS or --long ARGS
                else:
                    default = action.dest.upper()
                    args_string = self._format_args(action, default)
                    part = '%s %s' % (option_string, args_string)

                # make it look optional if it's not required or in a group
                if not action.required and action not in group_actions:
                    part = '[%s]' % part

                # add the action string to the list
                parts.append(part)

        # insert things at the necessary indices
        for i in sorted(inserts, reverse=True):
            parts[i:i] = [inserts[i]]

        # join all the action items with spaces
        text = ' '.join([item for item in parts if item is not None])

        # clean up separators for mutually exclusive groups
        open = r'[\[(]'
        close = r'[\])]'
        text = _re.sub(r'(%s) ' % open, r'\1', text)
        text = _re.sub(r' (%s)' % close, r'\1', text)
        text = _re.sub(r'%s *%s' % (open, close), r'', text)
        text = _re.sub(r'\(([^|]*)\)', r'\1', text)
        text = text.strip()

        # return the text
        return text

    def _format_text(self, text):
        if '%(prog)' in text:
            text = text % dict(prog=self._prog)
        text_width = self._width - self._current_indent
        indent = ' ' * self._current_indent
        return self._fill_text(text, text_width, indent) + '\n\n'

    def _format_action(self, action):
        # determine the required width and the entry label
        help_position = min(self._action_max_length + 2,
                            self._max_help_position)
        help_width = self._width - help_position
        action_width = help_position - self._current_indent - 2
        action_header = self._format_action_invocation(action)

        # ho nelp; start on same line and add a final newline
        if not action.help:
            tup = self._current_indent, '', action_header
            action_header = '%*s%s\n' % tup

        # short action name; start on the same line and pad two spaces
        elif len(action_header) <= action_width:
            tup = self._current_indent, '', action_width, action_header
            action_header = '%*s%-*s  ' % tup
            indent_first = 0

        # long action name; start on the next line
        else:
            tup = self._current_indent, '', action_header
            action_header = '%*s%s\n' % tup
            indent_first = help_position

        # collect the pieces of the action help
        parts = [action_header]

        # if there was help for the action, add lines of help text
        if action.help:
            help_text = self._expand_help(action)
            help_lines = self._split_lines(help_text, help_width)
            parts.append('%*s%s\n' % (indent_first, '', help_lines[0]))
            for line in help_lines[1:]:
                parts.append('%*s%s\n' % (help_position, '', line))

        # or add a newline if the description doesn't end with one
        elif not action_header.endswith('\n'):
            parts.append('\n')

        # if there are any sub-actions, add their help as well
        for subaction in self._iter_indented_subactions(action):
            parts.append(self._format_action(subaction))

        # return a single string
        return self._join_parts(parts)

    def _format_action_invocation(self, action):
        if not action.option_strings:
            metavar, = self._metavar_formatter(action, action.dest)(1)
            return metavar

        else:
            parts = []

            # if the Optional doesn't take a value, format is:
            #    -s, --long
            if action.nargs == 0:
                parts.extend(action.option_strings)

            # if the Optional takes a value, format is:
            #    -s ARGS, --long ARGS
            else:
                default = action.dest.upper()
                args_string = self._format_args(action, default)
                for option_string in action.option_strings:
                    parts.append('%s %s' % (option_string, args_string))

            return ', '.join(parts)

    def _metavar_formatter(self, action, default_metavar):
        if action.metavar is not None:
            result = action.metavar
        elif action.choices is not None:
            choice_strs = [str(choice) for choice in action.choices]
            result = '{%s}' % ','.join(choice_strs)
        else:
            result = default_metavar

        def format(tuple_size):
            if isinstance(result, tuple):
                return result
            else:
                return (result, ) * tuple_size
        return format

    def _format_args(self, action, default_metavar):
        get_metavar = self._metavar_formatter(action, default_metavar)
        if action.nargs is None:
            result = '%s' % get_metavar(1)
        elif action.nargs == OPTIONAL:
            result = '[%s]' % get_metavar(1)
        elif action.nargs == ZERO_OR_MORE:
            result = '[%s [%s ...]]' % get_metavar(2)
        elif action.nargs == ONE_OR_MORE:
            result = '%s [%s ...]' % get_metavar(2)
        elif action.nargs == REMAINDER:
            result = '...'
        elif action.nargs == PARSER:
            result = '%s ...' % get_metavar(1)
        else:
            formats = ['%s' for _ in range(action.nargs)]
            result = ' '.join(formats) % get_metavar(action.nargs)
        return result

    def _expand_help(self, action):
        params = dict(vars(action), prog=self._prog)
        for name in list(params):
            if params[name] is SUPPRESS:
                del params[name]
        for name in list(params):
            if hasattr(params[name], '__name__'):
                params[name] = params[name].__name__
        if params.get('choices') is not None:
            choices_str = ', '.join([str(c) for c in params['choices']])
            params['choices'] = choices_str
        return self._get_help_string(action) % params

    def _iter_indented_subactions(self, action):
        try:
            get_subactions = action._get_subactions
        except AttributeError:
            pass
        else:
            self._indent()
            for subaction in get_subactions():
                yield subaction
            self._dedent()

    def _split_lines(self, text, width):
        text = self._whitespace_matcher.sub(' ', text).strip()
        return _textwrap.wrap(text, width)

    def _fill_text(self, text, width, indent):
        text = self._whitespace_matcher.sub(' ', text).strip()
        return _textwrap.fill(text, width, initial_indent=indent,
                                           subsequent_indent=indent)

    def _get_help_string(self, action):
        return action.help


class RawDescriptionHelpFormatter(HelpFormatter):
    """Help message formatter which retains any formatting in descriptions.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _fill_text(self, text, width, indent):
        return ''.join([indent + line for line in text.splitlines(True)])


class RawTextHelpFormatter(RawDescriptionHelpFormatter):
    """Help message formatter which retains formatting of all help text.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _split_lines(self, text, width):
        return text.splitlines()


class ArgumentDefaultsHelpFormatter(HelpFormatter):
    """Help message formatter which adds default values to argument help.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _get_help_string(self, action):
        help = action.help
        if '%(default)' not in action.help:
            if action.default is not SUPPRESS:
                defaulting_nargs = [OPTIONAL, ZERO_OR_MORE]
                if action.option_strings or action.nargs in defaulting_nargs:
                    help += ' (default: %(default)s)'
        return help


# =====================
# Options and Arguments
# =====================

def _get_action_name(argument):
    if argument is None:
        return None
    elif argument.option_strings:
        return  '/'.join(argument.option_strings)
    elif argument.metavar not in (None, SUPPRESS):
        return argument.metavar
    elif argument.dest not in (None, SUPPRESS):
        return argument.dest
    else:
        return None


class ArgumentError(Exception):
    """An error from creating or using an argument (optional or positional).

    The string value of this exception is the message, augmented with
    information about the argument that caused it.
    """

    def __init__(self, argument, message):
        self.argument_name = _get_action_name(argument)
        self.message = message

    def __str__(self):
        if self.argument_name is None:
            format = '%(message)s'
        else:
            format = 'argument %(argument_name)s: %(message)s'
        return format % dict(message=self.message,
                             argument_name=self.argument_name)


class ArgumentTypeError(Exception):
    """An error from trying to convert a command line string to a type."""
    pass


# ==============
# Action classes
# ==============

class Action(_AttributeHolder):
    """Information about how to convert command line strings to Python objects.

    Action objects are used by an ArgumentParser to represent the information
    needed to parse a single argument from one or more strings from the
    command line. The keyword arguments to the Action constructor are also
    all attributes of Action instances.

    Keyword Arguments:

        - option_strings -- A list of command-line option strings which
            should be associated with this action.

        - dest -- The name of the attribute to hold the created object(s)

        - nargs -- The number of command-line arguments that should be
            consumed. By default, one argument will be consumed and a single
            value will be produced.  Other values include:
                - N (an integer) consumes N arguments (and produces a list)
                - '?' consumes zero or one arguments
                - '*' consumes zero or more arguments (and produces a list)
                - '+' consumes one or more arguments (and produces a list)
            Note that the difference between the default and nargs=1 is that
            with the default, a single value will be produced, while with
            nargs=1, a list containing a single value will be produced.

        - const -- The value to be produced if the option is specified and the
            option uses an action that takes no values.

        - default -- The value to be produced if the option is not specified.

        - type -- The type which the command-line arguments should be converted
            to, should be one of 'string', 'int', 'float', 'complex' or a
            callable object that accepts a single string argument. If None,
            'string' is assumed.

        - choices -- A container of values that should be allowed. If not None,
            after a command-line argument has been converted to the appropriate
            type, an exception will be raised if it is not a member of this
            collection.

        - required -- True if the action must always be specified at the
            command line. This is only meaningful for optional command-line
            arguments.

        - help -- The help string describing the argument.

        - metavar -- The name to be used for the option's argument with the
            help string. If None, the 'dest' value will be used as the name.
    """

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):
        self.option_strings = option_strings
        self.dest = dest
        self.nargs = nargs
        self.const = const
        self.default = default
        self.type = type
        self.choices = choices
        self.required = required
        self.help = help
        self.metavar = metavar

    def _get_kwargs(self):
        names = [
            'option_strings',
            'dest',
            'nargs',
            'const',
            'default',
            'type',
            'choices',
            'help',
            'metavar',
        ]
        return [(name, getattr(self, name)) for name in names]

    def __call__(self, parser, namespace, values, option_string=None):
        raise NotImplementedError(_('.__call__() not defined'))


class _StoreAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):
        if nargs == 0:
            raise ValueError('nargs for store actions must be > 0; if you '
                             'have nothing to store, actions such as store '
                             'true or store const may be more appropriate')
        if const is not None and nargs != OPTIONAL:
            raise ValueError('nargs must be %r to supply const' % OPTIONAL)
        super(_StoreAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)


class _StoreConstAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 const,
                 default=None,
                 required=False,
                 help=None,
                 metavar=None):
        super(_StoreConstAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            const=const,
            default=default,
            required=required,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, self.const)


class _StoreTrueAction(_StoreConstAction):

    def __init__(self,
                 option_strings,
                 dest,
                 default=False,
                 required=False,
                 help=None):
        super(_StoreTrueAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            const=True,
            default=default,
            required=required,
            help=help)


class _StoreFalseAction(_StoreConstAction):

    def __init__(self,
                 option_strings,
                 dest,
                 default=True,
                 required=False,
                 help=None):
        super(_StoreFalseAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            const=False,
            default=default,
            required=required,
            help=help)


class _AppendAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):
        if nargs == 0:
            raise ValueError('nargs for append actions must be > 0; if arg '
                             'strings are not supplying the value to append, '
                             'the append const action may be more appropriate')
        if const is not None and nargs != OPTIONAL:
            raise ValueError('nargs must be %r to supply const' % OPTIONAL)
        super(_AppendAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        items = _copy.copy(_ensure_value(namespace, self.dest, []))
        items.append(values)
        setattr(namespace, self.dest, items)


class _AppendConstAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 const,
                 default=None,
                 required=False,
                 help=None,
                 metavar=None):
        super(_AppendConstAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            const=const,
            default=default,
            required=required,
            help=help,
            metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        items = _copy.copy(_ensure_value(namespace, self.dest, []))
        items.append(self.const)
        setattr(namespace, self.dest, items)


class _CountAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 default=None,
                 required=False,
                 help=None):
        super(_CountAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            default=default,
            required=required,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        new_count = _ensure_value(namespace, self.dest, 0) + 1
        setattr(namespace, self.dest, new_count)


class _HelpAction(Action):

    def __init__(self,
                 option_strings,
                 dest=SUPPRESS,
                 default=SUPPRESS,
                 help=None):
        super(_HelpAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_help()
        parser.exit()


class _VersionAction(Action):

    def __init__(self,
                 option_strings,
                 version=None,
                 dest=SUPPRESS,
                 default=SUPPRESS,
                 help="show program's version number and exit"):
        super(_VersionAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)
        self.version = version

    def __call__(self, parser, namespace, values, option_string=None):
        version = self.version
        if version is None:
            version = parser.version
        formatter = parser._get_formatter()
        formatter.add_text(version)
        parser.exit(message=formatter.format_help())


class _SubParsersAction(Action):

    class _ChoicesPseudoAction(Action):

        def __init__(self, name, help):
            sup = super(_SubParsersAction._ChoicesPseudoAction, self)
            sup.__init__(option_strings=[], dest=name, help=help)

    def __init__(self,
                 option_strings,
                 prog,
                 parser_class,
                 dest=SUPPRESS,
                 help=None,
                 metavar=None):

        self._prog_prefix = prog
        self._parser_class = parser_class
        self._name_parser_map = {}
        self._choices_actions = []

        super(_SubParsersAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=PARSER,
            choices=self._name_parser_map,
            help=help,
            metavar=metavar)

    def add_parser(self, name, **kwargs):
        # set prog from the existing prefix
        if kwargs.get('prog') is None:
            kwargs['prog'] = '%s %s' % (self._prog_prefix, name)

        # create a pseudo-action to hold the choice help
        if 'help' in kwargs:
            help = kwargs.pop('help')
            choice_action = self._ChoicesPseudoAction(name, help)
            self._choices_actions.append(choice_action)

        # create the parser and add it to the map
        parser = self._parser_class(**kwargs)
        self._name_parser_map[name] = parser
        return parser

    def _get_subactions(self):
        return self._choices_actions

    def __call__(self, parser, namespace, values, option_string=None):
        parser_name = values[0]
        arg_strings = values[1:]

        # set the parser name if requested
        if self.dest is not SUPPRESS:
            setattr(namespace, self.dest, parser_name)

        # select the parser
        try:
            parser = self._name_parser_map[parser_name]
        except KeyError:
            tup = parser_name, ', '.join(self._name_parser_map)
            msg = _('unknown parser %r (choices: %s)' % tup)
            raise ArgumentError(self, msg)

        # parse all the remaining options into the namespace
        # store any unrecognized options on the object, so that the top
        # level parser can decide what to do with them
        namespace, arg_strings = parser.parse_known_args(arg_strings, namespace)
        if arg_strings:
            vars(namespace).setdefault(_UNRECOGNIZED_ARGS_ATTR, [])
            getattr(namespace, _UNRECOGNIZED_ARGS_ATTR).extend(arg_strings)


# ==============
# Type classes
# ==============

class FileType(object):
    """Factory for creating file object types

    Instances of FileType are typically passed as type= arguments to the
    ArgumentParser add_argument() method.

    Keyword Arguments:
        - mode -- A string indicating how the file is to be opened. Accepts the
            same values as the builtin open() function.
        - bufsize -- The file's desired buffer size. Accepts the same values as
            the builtin open() function.
    """

    def __init__(self, mode='r', bufsize=None):
        self._mode = mode
        self._bufsize = bufsize

    def __call__(self, string):
        # the special argument "-" means sys.std{in,out}
        if string == '-':
            if 'r' in self._mode:
                return _sys.stdin
            elif 'w' in self._mode:
                return _sys.stdout
            else:
                msg = _('argument "-" with mode %r' % self._mode)
                raise ValueError(msg)

        # all other arguments are used as file names
        if self._bufsize:
            return open(string, self._mode, self._bufsize)
        else:
            return open(string, self._mode)

    def __repr__(self):
        args = [self._mode, self._bufsize]
        args_str = ', '.join([repr(arg) for arg in args if arg is not None])
        return '%s(%s)' % (type(self).__name__, args_str)

# ===========================
# Optional and Positional Parsing
# ===========================

class Namespace(_AttributeHolder):
    """Simple object for storing attributes.

    Implements equality by attribute names and values, and provides a simple
    string representation.
    """

    def __init__(self, **kwargs):
        for name in kwargs:
            setattr(self, name, kwargs[name])

    __hash__ = None

    def __eq__(self, other):
        return vars(self) == vars(other)

    def __ne__(self, other):
        return not (self == other)

    def __contains__(self, key):
        return key in self.__dict__


class _ActionsContainer(object):

    def __init__(self,
                 description,
                 prefix_chars,
                 argument_default,
                 conflict_handler):
        super(_ActionsContainer, self).__init__()

        self.description = description
        self.argument_default = argument_default
        self.prefix_chars = prefix_chars
        self.conflict_handler = conflict_handler

        # set up registries
        self._registries = {}

        # register actions
        self.register('action', None, _StoreAction)
        self.register('action', 'store', _StoreAction)
        self.register('action', 'store_const', _StoreConstAction)
        self.register('action', 'store_true', _StoreTrueAction)
        self.register('action', 'store_false', _StoreFalseAction)
        self.register('action', 'append', _AppendAction)
        self.register('action', 'append_const', _AppendConstAction)
        self.register('action', 'count', _CountAction)
        self.register('action', 'help', _HelpAction)
        self.register('action', 'version', _VersionAction)
        self.register('action', 'parsers', _SubParsersAction)

        # raise an exception if the conflict handler is invalid
        self._get_handler()

        # action storage
        self._actions = []
        self._option_string_actions = {}

        # groups
        self._action_groups = []
        self._mutually_exclusive_groups = []

        # defaults storage
        self._defaults = {}

        # determines whether an "option" looks like a negative number
        self._negative_number_matcher = _re.compile(r'^-\d+$|^-\d*\.\d+$')

        # whether or not there are any optionals that look like negative
        # numbers -- uses a list so it can be shared and edited
        self._has_negative_number_optionals = []

    # ====================
    # Registration methods
    # ====================
    def register(self, registry_name, value, object):
        registry = self._registries.setdefault(registry_name, {})
        registry[value] = object

    def _registry_get(self, registry_name, value, default=None):
        return self._registries[registry_name].get(value, default)

    # ==================================
    # Namespace default accessor methods
    # ==================================
    def set_defaults(self, **kwargs):
        self._defaults.update(kwargs)

        # if these defaults match any existing arguments, replace
        # the previous default on the object with the new one
        for action in self._actions:
            if action.dest in kwargs:
                action.default = kwargs[action.dest]

    def get_default(self, dest):
        for action in self._actions:
            if action.dest == dest and action.default is not None:
                return action.default
        return self._defaults.get(dest, None)


    # =======================
    # Adding argument actions
    # =======================
    def add_argument(self, *args, **kwargs):
        """
        add_argument(dest, ..., name=value, ...)
        add_argument(option_string, option_string, ..., name=value, ...)
        """

        # if no positional args are supplied or only one is supplied and
        # it doesn't look like an option string, parse a positional
        # argument
        chars = self.prefix_chars
        if not args or len(args) == 1 and args[0][0] not in chars:
            if args and 'dest' in kwargs:
                raise ValueError('dest supplied twice for positional argument')
            kwargs = self._get_positional_kwargs(*args, **kwargs)

        # otherwise, we're adding an optional argument
        else:
            kwargs = self._get_optional_kwargs(*args, **kwargs)

        # if no default was supplied, use the parser-level default
        if 'default' not in kwargs:
            dest = kwargs['dest']
            if dest in self._defaults:
                kwargs['default'] = self._defaults[dest]
            elif self.argument_default is not None:
                kwargs['default'] = self.argument_default

        # create the action object, and add it to the parser
        action_class = self._pop_action_class(kwargs)
        if not _callable(action_class):
            raise ValueError('unknown action "%s"' % action_class)
        action = action_class(**kwargs)

        # raise an error if the action type is not callable
        type_func = self._registry_get('type', action.type, action.type)
        if not _callable(type_func):
            raise ValueError('%r is not callable' % type_func)

        return self._add_action(action)

    def add_argument_group(self, *args, **kwargs):
        group = _ArgumentGroup(self, *args, **kwargs)
        self._action_groups.append(group)
        return group

    def add_mutually_exclusive_group(self, **kwargs):
        group = _MutuallyExclusiveGroup(self, **kwargs)
        self._mutually_exclusive_groups.append(group)
        return group

    def _add_action(self, action):
        # resolve any conflicts
        self._check_conflict(action)

        # add to actions list
        self._actions.append(action)
        action.container = self

        # index the action by any option strings it has
        for option_string in action.option_strings:
            self._option_string_actions[option_string] = action

        # set the flag if any option strings look like negative numbers
        for option_string in action.option_strings:
            if self._negative_number_matcher.match(option_string):
                if not self._has_negative_number_optionals:
                    self._has_negative_number_optionals.append(True)

        # return the created action
        return action

    def _remove_action(self, action):
        self._actions.remove(action)

    def _add_container_actions(self, container):
        # collect groups by titles
        title_group_map = {}
        for group in self._action_groups:
            if group.title in title_group_map:
                msg = _('cannot merge actions - two groups are named %r')
                raise ValueError(msg % (group.title))
            title_group_map[group.title] = group

        # map each action to its group
        group_map = {}
        for group in container._action_groups:

            # if a group with the title exists, use that, otherwise
            # create a new group matching the container's group
            if group.title not in title_group_map:
                title_group_map[group.title] = self.add_argument_group(
                    title=group.title,
                    description=group.description,
                    conflict_handler=group.conflict_handler)

            # map the actions to their new group
            for action in group._group_actions:
                group_map[action] = title_group_map[group.title]

        # add container's mutually exclusive groups
        # NOTE: if add_mutually_exclusive_group ever gains title= and
        # description= then this code will need to be expanded as above
        for group in container._mutually_exclusive_groups:
            mutex_group = self.add_mutually_exclusive_group(
                required=group.required)

            # map the actions to their new mutex group
            for action in group._group_actions:
                group_map[action] = mutex_group

        # add all actions to this container or their group
        for action in container._actions:
            group_map.get(action, self)._add_action(action)

    def _get_positional_kwargs(self, dest, **kwargs):
        # make sure required is not specified
        if 'required' in kwargs:
            msg = _("'required' is an invalid argument for positionals")
            raise TypeError(msg)

        # mark positional arguments as required if at least one is
        # always required
        if kwargs.get('nargs') not in [OPTIONAL, ZERO_OR_MORE]:
            kwargs['required'] = True
        if kwargs.get('nargs') == ZERO_OR_MORE and 'default' not in kwargs:
            kwargs['required'] = True

        # return the keyword arguments with no option strings
        return dict(kwargs, dest=dest, option_strings=[])

    def _get_optional_kwargs(self, *args, **kwargs):
        # determine short and long option strings
        option_strings = []
        long_option_strings = []
        for option_string in args:
            # error on strings that don't start with an appropriate prefix
            if not option_string[0] in self.prefix_chars:
                msg = _('invalid option string %r: '
                        'must start with a character %r')
                tup = option_string, self.prefix_chars
                raise ValueError(msg % tup)

            # strings starting with two prefix characters are long options
            option_strings.append(option_string)
            if option_string[0] in self.prefix_chars:
                if len(option_string) > 1:
                    if option_string[1] in self.prefix_chars:
                        long_option_strings.append(option_string)

        # infer destination, '--foo-bar' -> 'foo_bar' and '-x' -> 'x'
        dest = kwargs.pop('dest', None)
        if dest is None:
            if long_option_strings:
                dest_option_string = long_option_strings[0]
            else:
                dest_option_string = option_strings[0]
            dest = dest_option_string.lstrip(self.prefix_chars)
            if not dest:
                msg = _('dest= is required for options like %r')
                raise ValueError(msg % option_string)
            dest = dest.replace('-', '_')

        # return the updated keyword arguments
        return dict(kwargs, dest=dest, option_strings=option_strings)

    def _pop_action_class(self, kwargs, default=None):
        action = kwargs.pop('action', default)
        return self._registry_get('action', action, action)

    def _get_handler(self):
        # determine function from conflict handler string
        handler_func_name = '_handle_conflict_%s' % self.conflict_handler
        try:
            return getattr(self, handler_func_name)
        except AttributeError:
            msg = _('invalid conflict_resolution value: %r')
            raise ValueError(msg % self.conflict_handler)

    def _check_conflict(self, action):

        # find all options that conflict with this option
        confl_optionals = []
        for option_string in action.option_strings:
            if option_string in self._option_string_actions:
                confl_optional = self._option_string_actions[option_string]
                confl_optionals.append((option_string, confl_optional))

        # resolve any conflicts
        if confl_optionals:
            conflict_handler = self._get_handler()
            conflict_handler(action, confl_optionals)

    def _handle_conflict_error(self, action, conflicting_actions):
        message = _('conflicting option string(s): %s')
        conflict_string = ', '.join([option_string
                                     for option_string, action
                                     in conflicting_actions])
        raise ArgumentError(action, message % conflict_string)

    def _handle_conflict_resolve(self, action, conflicting_actions):

        # remove all conflicting options
        for option_string, action in conflicting_actions:

            # remove the conflicting option
            action.option_strings.remove(option_string)
            self._option_string_actions.pop(option_string, None)

            # if the option now has no option string, remove it from the
            # container holding it
            if not action.option_strings:
                action.container._remove_action(action)


class _ArgumentGroup(_ActionsContainer):

    def __init__(self, container, title=None, description=None, **kwargs):
        # add any missing keyword arguments by checking the container
        update = kwargs.setdefault
        update('conflict_handler', container.conflict_handler)
        update('prefix_chars', container.prefix_chars)
        update('argument_default', container.argument_default)
        super_init = super(_ArgumentGroup, self).__init__
        super_init(description=description, **kwargs)

        # group attributes
        self.title = title
        self._group_actions = []

        # share most attributes with the container
        self._registries = container._registries
        self._actions = container._actions
        self._option_string_actions = container._option_string_actions
        self._defaults = container._defaults
        self._has_negative_number_optionals = \
            container._has_negative_number_optionals

    def _add_action(self, action):
        action = super(_ArgumentGroup, self)._add_action(action)
        self._group_actions.append(action)
        return action

    def _remove_action(self, action):
        super(_ArgumentGroup, self)._remove_action(action)
        self._group_actions.remove(action)


class _MutuallyExclusiveGroup(_ArgumentGroup):

    def __init__(self, container, required=False):
        super(_MutuallyExclusiveGroup, self).__init__(container)
        self.required = required
        self._container = container

    def _add_action(self, action):
        if action.required:
            msg = _('mutually exclusive arguments must be optional')
            raise ValueError(msg)
        action = self._container._add_action(action)
        self._group_actions.append(action)
        return action

    def _remove_action(self, action):
        self._container._remove_action(action)
        self._group_actions.remove(action)


class ArgumentParser(_AttributeHolder, _ActionsContainer):
    """Object for parsing command line strings into Python objects.

    Keyword Arguments:
        - prog -- The name of the program (default: sys.argv[0])
        - usage -- A usage message (default: auto-generated from arguments)
        - description -- A description of what the program does
        - epilog -- Text following the argument descriptions
        - parents -- Parsers whose arguments should be copied into this one
        - formatter_class -- HelpFormatter class for printing help messages
        - prefix_chars -- Characters that prefix optional arguments
        - fromfile_prefix_chars -- Characters that prefix files containing
            additional arguments
        - argument_default -- The default value for all arguments
        - conflict_handler -- String indicating how to handle conflicts
        - add_help -- Add a -h/-help option
    """

    def __init__(self,
                 prog=None,
                 usage=None,
                 description=None,
                 epilog=None,
                 version=None,
                 parents=[],
                 formatter_class=HelpFormatter,
                 prefix_chars='-',
                 fromfile_prefix_chars=None,
                 argument_default=None,
                 conflict_handler='error',
                 add_help=True):

        if version is not None:
            import warnings
            warnings.warn(
                """The "version" argument to ArgumentParser is deprecated. """
                """Please use """
                """"add_argument(..., action='version', version="N", ...)" """
                """instead""", DeprecationWarning)

        superinit = super(ArgumentParser, self).__init__
        superinit(description=description,
                  prefix_chars=prefix_chars,
                  argument_default=argument_default,
                  conflict_handler=conflict_handler)

        # default setting for prog
        if prog is None:
            prog = _os.path.basename(_sys.argv[0])

        self.prog = prog
        self.usage = usage
        self.epilog = epilog
        self.version = version
        self.formatter_class = formatter_class
        self.fromfile_prefix_chars = fromfile_prefix_chars
        self.add_help = add_help

        add_group = self.add_argument_group
        self._positionals = add_group(_('positional arguments'))
        self._optionals = add_group(_('optional arguments'))
        self._subparsers = None

        # register types
        def identity(string):
            return string
        self.register('type', None, identity)

        # add help and version arguments if necessary
        # (using explicit default to override global argument_default)
        default_prefix = '-' if '-' in prefix_chars else prefix_chars[0]
        if self.add_help:
            self.add_argument(
                default_prefix+'h', default_prefix*2+'help',
                action='help', default=SUPPRESS,
                help=_('show this help message and exit'))
        if self.version:
            self.add_argument(
                default_prefix+'v', default_prefix*2+'version',
                action='version', default=SUPPRESS,
                version=self.version,
                help=_("show program's version number and exit"))

        # add parent arguments and defaults
        for parent in parents:
            self._add_container_actions(parent)
            try:
                defaults = parent._defaults
            except AttributeError:
                pass
            else:
                self._defaults.update(defaults)

    # =======================
    # Pretty __repr__ methods
    # =======================
    def _get_kwargs(self):
        names = [
            'prog',
            'usage',
            'description',
            'version',
            'formatter_class',
            'conflict_handler',
            'add_help',
        ]
        return [(name, getattr(self, name)) for name in names]

    # ==================================
    # Optional/Positional adding methods
    # ==================================
    def add_subparsers(self, **kwargs):
        if self._subparsers is not None:
            self.error(_('cannot have multiple subparser arguments'))

        # add the parser class to the arguments if it's not present
        kwargs.setdefault('parser_class', type(self))

        if 'title' in kwargs or 'description' in kwargs:
            title = _(kwargs.pop('title', 'subcommands'))
            description = _(kwargs.pop('description', None))
            self._subparsers = self.add_argument_group(title, description)
        else:
            self._subparsers = self._positionals

        # prog defaults to the usage message of this parser, skipping
        # optional arguments and with no "usage:" prefix
        if kwargs.get('prog') is None:
            formatter = self._get_formatter()
            positionals = self._get_positional_actions()
            groups = self._mutually_exclusive_groups
            formatter.add_usage(self.usage, positionals, groups, '')
            kwargs['prog'] = formatter.format_help().strip()

        # create the parsers action and add it to the positionals list
        parsers_class = self._pop_action_class(kwargs, 'parsers')
        action = parsers_class(option_strings=[], **kwargs)
        self._subparsers._add_action(action)

        # return the created parsers action
        return action

    def _add_action(self, action):
        if action.option_strings:
            self._optionals._add_action(action)
        else:
            self._positionals._add_action(action)
        return action

    def _get_optional_actions(self):
        return [action
                for action in self._actions
                if action.option_strings]

    def _get_positional_actions(self):
        return [action
                for action in self._actions
                if not action.option_strings]

    # =====================================
    # Command line argument parsing methods
    # =====================================
    def parse_args(self, args=None, namespace=None):
        args, argv = self.parse_known_args(args, namespace)
        if argv:
            msg = _('unrecognized arguments: %s')
            self.error(msg % ' '.join(argv))
        return args

    def parse_known_args(self, args=None, namespace=None):
        # args default to the system args
        if args is None:
            args = _sys.argv[1:]

        # default Namespace built from parser defaults
        if namespace is None:
            namespace = Namespace()

        # add any action defaults that aren't present
        for action in self._actions:
            if action.dest is not SUPPRESS:
                if not hasattr(namespace, action.dest):
                    if action.default is not SUPPRESS:
                        default = action.default
                        if isinstance(action.default, basestring):
                            default = self._get_value(action, default)
                        setattr(namespace, action.dest, default)

        # add any parser defaults that aren't present
        for dest in self._defaults:
            if not hasattr(namespace, dest):
                setattr(namespace, dest, self._defaults[dest])

        # parse the arguments and exit if there are any errors
        try:
            namespace, args = self._parse_known_args(args, namespace)
            if hasattr(namespace, _UNRECOGNIZED_ARGS_ATTR):
                args.extend(getattr(namespace, _UNRECOGNIZED_ARGS_ATTR))
                delattr(namespace, _UNRECOGNIZED_ARGS_ATTR)
            return namespace, args
        except ArgumentError:
            err = _sys.exc_info()[1]
            self.error(str(err))

    def _parse_known_args(self, arg_strings, namespace):
        # replace arg strings that are file references
        if self.fromfile_prefix_chars is not None:
            arg_strings = self._read_args_from_files(arg_strings)

        # map all mutually exclusive arguments to the other arguments
        # they can't occur with
        action_conflicts = {}
        for mutex_group in self._mutually_exclusive_groups:
            group_actions = mutex_group._group_actions
            for i, mutex_action in enumerate(mutex_group._group_actions):
                conflicts = action_conflicts.setdefault(mutex_action, [])
                conflicts.extend(group_actions[:i])
                conflicts.extend(group_actions[i + 1:])

        # find all option indices, and determine the arg_string_pattern
        # which has an 'O' if there is an option at an index,
        # an 'A' if there is an argument, or a '-' if there is a '--'
        option_string_indices = {}
        arg_string_pattern_parts = []
        arg_strings_iter = iter(arg_strings)
        for i, arg_string in enumerate(arg_strings_iter):

            # all args after -- are non-options
            if arg_string == '--':
                arg_string_pattern_parts.append('-')
                for arg_string in arg_strings_iter:
                    arg_string_pattern_parts.append('A')

            # otherwise, add the arg to the arg strings
            # and note the index if it was an option
            else:
                option_tuple = self._parse_optional(arg_string)
                if option_tuple is None:
                    pattern = 'A'
                else:
                    option_string_indices[i] = option_tuple
                    pattern = 'O'
                arg_string_pattern_parts.append(pattern)

        # join the pieces together to form the pattern
        arg_strings_pattern = ''.join(arg_string_pattern_parts)

        # converts arg strings to the appropriate and then takes the action
        seen_actions = set()
        seen_non_default_actions = set()

        def take_action(action, argument_strings, option_string=None):
            seen_actions.add(action)
            argument_values = self._get_values(action, argument_strings)

            # error if this argument is not allowed with other previously
            # seen arguments, assuming that actions that use the default
            # value don't really count as "present"
            if argument_values is not action.default:
                seen_non_default_actions.add(action)
                for conflict_action in action_conflicts.get(action, []):
                    if conflict_action in seen_non_default_actions:
                        msg = _('not allowed with argument %s')
                        action_name = _get_action_name(conflict_action)
                        raise ArgumentError(action, msg % action_name)

            # take the action if we didn't receive a SUPPRESS value
            # (e.g. from a default)
            if argument_values is not SUPPRESS:
                action(self, namespace, argument_values, option_string)

        # function to convert arg_strings into an optional action
        def consume_optional(start_index):

            # get the optional identified at this index
            option_tuple = option_string_indices[start_index]
            action, option_string, explicit_arg = option_tuple

            # identify additional optionals in the same arg string
            # (e.g. -xyz is the same as -x -y -z if no args are required)
            match_argument = self._match_argument
            action_tuples = []
            while True:

                # if we found no optional action, skip it
                if action is None:
                    extras.append(arg_strings[start_index])
                    return start_index + 1

                # if there is an explicit argument, try to match the
                # optional's string arguments to only this
                if explicit_arg is not None:
                    arg_count = match_argument(action, 'A')

                    # if the action is a single-dash option and takes no
                    # arguments, try to parse more single-dash options out
                    # of the tail of the option string
                    chars = self.prefix_chars
                    if arg_count == 0 and option_string[1] not in chars:
                        action_tuples.append((action, [], option_string))
                        char = option_string[0]
                        option_string = char + explicit_arg[0]
                        new_explicit_arg = explicit_arg[1:] or None
                        optionals_map = self._option_string_actions
                        if option_string in optionals_map:
                            action = optionals_map[option_string]
                            explicit_arg = new_explicit_arg
                        else:
                            msg = _('ignored explicit argument %r')
                            raise ArgumentError(action, msg % explicit_arg)

                    # if the action expect exactly one argument, we've
                    # successfully matched the option; exit the loop
                    elif arg_count == 1:
                        stop = start_index + 1
                        args = [explicit_arg]
                        action_tuples.append((action, args, option_string))
                        break

                    # error if a double-dash option did not use the
                    # explicit argument
                    else:
                        msg = _('ignored explicit argument %r')
                        raise ArgumentError(action, msg % explicit_arg)

                # if there is no explicit argument, try to match the
                # optional's string arguments with the following strings
                # if successful, exit the loop
                else:
                    start = start_index + 1
                    selected_patterns = arg_strings_pattern[start:]
                    arg_count = match_argument(action, selected_patterns)
                    stop = start + arg_count
                    args = arg_strings[start:stop]
                    action_tuples.append((action, args, option_string))
                    break

            # add the Optional to the list and return the index at which
            # the Optional's string args stopped
            assert action_tuples
            for action, args, option_string in action_tuples:
                take_action(action, args, option_string)
            return stop

        # the list of Positionals left to be parsed; this is modified
        # by consume_positionals()
        positionals = self._get_positional_actions()

        # function to convert arg_strings into positional actions
        def consume_positionals(start_index):
            # match as many Positionals as possible
            match_partial = self._match_arguments_partial
            selected_pattern = arg_strings_pattern[start_index:]
            arg_counts = match_partial(positionals, selected_pattern)

            # slice off the appropriate arg strings for each Positional
            # and add the Positional and its args to the list
            for action, arg_count in zip(positionals, arg_counts):
                args = arg_strings[start_index: start_index + arg_count]
                start_index += arg_count
                take_action(action, args)

            # slice off the Positionals that we just parsed and return the
            # index at which the Positionals' string args stopped
            positionals[:] = positionals[len(arg_counts):]
            return start_index

        # consume Positionals and Optionals alternately, until we have
        # passed the last option string
        extras = []
        start_index = 0
        if option_string_indices:
            max_option_string_index = max(option_string_indices)
        else:
            max_option_string_index = -1
        while start_index <= max_option_string_index:

            # consume any Positionals preceding the next option
            next_option_string_index = min([
                index
                for index in option_string_indices
                if index >= start_index])
            if start_index != next_option_string_index:
                positionals_end_index = consume_positionals(start_index)

                # only try to parse the next optional if we didn't consume
                # the option string during the positionals parsing
                if positionals_end_index > start_index:
                    start_index = positionals_end_index
                    continue
                else:
                    start_index = positionals_end_index

            # if we consumed all the positionals we could and we're not
            # at the index of an option string, there were extra arguments
            if start_index not in option_string_indices:
                strings = arg_strings[start_index:next_option_string_index]
                extras.extend(strings)
                start_index = next_option_string_index

            # consume the next optional and any arguments for it
            start_index = consume_optional(start_index)

        # consume any positionals following the last Optional
        stop_index = consume_positionals(start_index)

        # if we didn't consume all the argument strings, there were extras
        extras.extend(arg_strings[stop_index:])

        # if we didn't use all the Positional objects, there were too few
        # arg strings supplied.
        if positionals:
            self.error(_('too few arguments'))

        # make sure all required actions were present
        for action in self._actions:
            if action.required:
                if action not in seen_actions:
                    name = _get_action_name(action)
                    self.error(_('argument %s is required') % name)

        # make sure all required groups had one option present
        for group in self._mutually_exclusive_groups:
            if group.required:
                for action in group._group_actions:
                    if action in seen_non_default_actions:
                        break

                # if no actions were used, report the error
                else:
                    names = [_get_action_name(action)
                             for action in group._group_actions
                             if action.help is not SUPPRESS]
                    msg = _('one of the arguments %s is required')
                    self.error(msg % ' '.join(names))

        # return the updated namespace and the extra arguments
        return namespace, extras

    def _read_args_from_files(self, arg_strings):
        # expand arguments referencing files
        new_arg_strings = []
        for arg_string in arg_strings:

            # for regular arguments, just add them back into the list
            if arg_string[0] not in self.fromfile_prefix_chars:
                new_arg_strings.append(arg_string)

            # replace arguments referencing files with the file content
            else:
                try:
                    args_file = open(arg_string[1:])
                    try:
                        arg_strings = []
                        for arg_line in args_file.read().splitlines():
                            for arg in self.convert_arg_line_to_args(arg_line):
                                arg_strings.append(arg)
                        arg_strings = self._read_args_from_files(arg_strings)
                        new_arg_strings.extend(arg_strings)
                    finally:
                        args_file.close()
                except IOError:
                    err = _sys.exc_info()[1]
                    self.error(str(err))

        # return the modified argument list
        return new_arg_strings

    def convert_arg_line_to_args(self, arg_line):
        return [arg_line]

    def _match_argument(self, action, arg_strings_pattern):
        # match the pattern for this action to the arg strings
        nargs_pattern = self._get_nargs_pattern(action)
        match = _re.match(nargs_pattern, arg_strings_pattern)

        # raise an exception if we weren't able to find a match
        if match is None:
            nargs_errors = {
                None: _('expected one argument'),
                OPTIONAL: _('expected at most one argument'),
                ONE_OR_MORE: _('expected at least one argument'),
            }
            default = _('expected %s argument(s)') % action.nargs
            msg = nargs_errors.get(action.nargs, default)
            raise ArgumentError(action, msg)

        # return the number of arguments matched
        return len(match.group(1))

    def _match_arguments_partial(self, actions, arg_strings_pattern):
        # progressively shorten the actions list by slicing off the
        # final actions until we find a match
        result = []
        for i in range(len(actions), 0, -1):
            actions_slice = actions[:i]
            pattern = ''.join([self._get_nargs_pattern(action)
                               for action in actions_slice])
            match = _re.match(pattern, arg_strings_pattern)
            if match is not None:
                result.extend([len(string) for string in match.groups()])
                break

        # return the list of arg string counts
        return result

    def _parse_optional(self, arg_string):
        # if it's an empty string, it was meant to be a positional
        if not arg_string:
            return None

        # if it doesn't start with a prefix, it was meant to be positional
        if not arg_string[0] in self.prefix_chars:
            return None

        # if the option string is present in the parser, return the action
        if arg_string in self._option_string_actions:
            action = self._option_string_actions[arg_string]
            return action, arg_string, None

        # if it's just a single character, it was meant to be positional
        if len(arg_string) == 1:
            return None

        # if the option string before the "=" is present, return the action
        if '=' in arg_string:
            option_string, explicit_arg = arg_string.split('=', 1)
            if option_string in self._option_string_actions:
                action = self._option_string_actions[option_string]
                return action, option_string, explicit_arg

        # search through all possible prefixes of the option string
        # and all actions in the parser for possible interpretations
        option_tuples = self._get_option_tuples(arg_string)

        # if multiple actions match, the option string was ambiguous
        if len(option_tuples) > 1:
            options = ', '.join([option_string
                for action, option_string, explicit_arg in option_tuples])
            tup = arg_string, options
            self.error(_('ambiguous option: %s could match %s') % tup)

        # if exactly one action matched, this segmentation is good,
        # so return the parsed action
        elif len(option_tuples) == 1:
            option_tuple, = option_tuples
            return option_tuple

        # if it was not found as an option, but it looks like a negative
        # number, it was meant to be positional
        # unless there are negative-number-like options
        if self._negative_number_matcher.match(arg_string):
            if not self._has_negative_number_optionals:
                return None

        # if it contains a space, it was meant to be a positional
        if ' ' in arg_string:
            return None

        # it was meant to be an optional but there is no such option
        # in this parser (though it might be a valid option in a subparser)
        return None, arg_string, None

    def _get_option_tuples(self, option_string):
        result = []

        # option strings starting with two prefix characters are only
        # split at the '='
        chars = self.prefix_chars
        if option_string[0] in chars and option_string[1] in chars:
            if '=' in option_string:
                option_prefix, explicit_arg = option_string.split('=', 1)
            else:
                option_prefix = option_string
                explicit_arg = None
            for option_string in self._option_string_actions:
                if option_string.startswith(option_prefix):
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, explicit_arg
                    result.append(tup)

        # single character options can be concatenated with their arguments
        # but multiple character options always have to have their argument
        # separate
        elif option_string[0] in chars and option_string[1] not in chars:
            option_prefix = option_string
            explicit_arg = None
            short_option_prefix = option_string[:2]
            short_explicit_arg = option_string[2:]

            for option_string in self._option_string_actions:
                if option_string == short_option_prefix:
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, short_explicit_arg
                    result.append(tup)
                elif option_string.startswith(option_prefix):
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, explicit_arg
                    result.append(tup)

        # shouldn't ever get here
        else:
            self.error(_('unexpected option string: %s') % option_string)

        # return the collected option tuples
        return result

    def _get_nargs_pattern(self, action):
        # in all examples below, we have to allow for '--' args
        # which are represented as '-' in the pattern
        nargs = action.nargs

        # the default (None) is assumed to be a single argument
        if nargs is None:
            nargs_pattern = '(-*A-*)'

        # allow zero or one arguments
        elif nargs == OPTIONAL:
            nargs_pattern = '(-*A?-*)'

        # allow zero or more arguments
        elif nargs == ZERO_OR_MORE:
            nargs_pattern = '(-*[A-]*)'

        # allow one or more arguments
        elif nargs == ONE_OR_MORE:
            nargs_pattern = '(-*A[A-]*)'

        # allow any number of options or arguments
        elif nargs == REMAINDER:
            nargs_pattern = '([-AO]*)'

        # allow one argument followed by any number of options or arguments
        elif nargs == PARSER:
            nargs_pattern = '(-*A[-AO]*)'

        # all others should be integers
        else:
            nargs_pattern = '(-*%s-*)' % '-*'.join('A' * nargs)

        # if this is an optional action, -- is not allowed
        if action.option_strings:
            nargs_pattern = nargs_pattern.replace('-*', '')
            nargs_pattern = nargs_pattern.replace('-', '')

        # return the pattern
        return nargs_pattern

    # ========================
    # Value conversion methods
    # ========================
    def _get_values(self, action, arg_strings):
        # for everything but PARSER args, strip out '--'
        if action.nargs not in [PARSER, REMAINDER]:
            arg_strings = [s for s in arg_strings if s != '--']

        # optional argument produces a default when not present
        if not arg_strings and action.nargs == OPTIONAL:
            if action.option_strings:
                value = action.const
            else:
                value = action.default
            if isinstance(value, basestring):
                value = self._get_value(action, value)
                self._check_value(action, value)

        # when nargs='*' on a positional, if there were no command-line
        # args, use the default if it is anything other than None
        elif (not arg_strings and action.nargs == ZERO_OR_MORE and
              not action.option_strings):
            if action.default is not None:
                value = action.default
            else:
                value = arg_strings
            self._check_value(action, value)

        # single argument or optional argument produces a single value
        elif len(arg_strings) == 1 and action.nargs in [None, OPTIONAL]:
            arg_string, = arg_strings
            value = self._get_value(action, arg_string)
            self._check_value(action, value)

        # REMAINDER arguments convert all values, checking none
        elif action.nargs == REMAINDER:
            value = [self._get_value(action, v) for v in arg_strings]

        # PARSER arguments convert all values, but check only the first
        elif action.nargs == PARSER:
            value = [self._get_value(action, v) for v in arg_strings]
            self._check_value(action, value[0])

        # all other types of nargs produce a list
        else:
            value = [self._get_value(action, v) for v in arg_strings]
            for v in value:
                self._check_value(action, v)

        # return the converted value
        return value

    def _get_value(self, action, arg_string):
        type_func = self._registry_get('type', action.type, action.type)
        if not _callable(type_func):
            msg = _('%r is not callable')
            raise ArgumentError(action, msg % type_func)

        # convert the value to the appropriate type
        try:
            result = type_func(arg_string)

        # ArgumentTypeErrors indicate errors
        except ArgumentTypeError:
            name = getattr(action.type, '__name__', repr(action.type))
            msg = str(_sys.exc_info()[1])
            raise ArgumentError(action, msg)

        # TypeErrors or ValueErrors also indicate errors
        except (TypeError, ValueError):
            name = getattr(action.type, '__name__', repr(action.type))
            msg = _('invalid %s value: %r')
            raise ArgumentError(action, msg % (name, arg_string))

        # return the converted value
        return result

    def _check_value(self, action, value):
        # converted value must be one of the choices (if specified)
        if action.choices is not None and value not in action.choices:
            tup = value, ', '.join(map(repr, action.choices))
            msg = _('invalid choice: %r (choose from %s)') % tup
            raise ArgumentError(action, msg)

    # =======================
    # Help-formatting methods
    # =======================
    def format_usage(self):
        formatter = self._get_formatter()
        formatter.add_usage(self.usage, self._actions,
                            self._mutually_exclusive_groups)
        return formatter.format_help()

    def format_help(self):
        formatter = self._get_formatter()

        # usage
        formatter.add_usage(self.usage, self._actions,
                            self._mutually_exclusive_groups)

        # description
        formatter.add_text(self.description)

        # positionals, optionals and user-defined groups
        for action_group in self._action_groups:
            formatter.start_section(action_group.title)
            formatter.add_text(action_group.description)
            formatter.add_arguments(action_group._group_actions)
            formatter.end_section()

        # epilog
        formatter.add_text(self.epilog)

        # determine help from format above
        return formatter.format_help()

    def format_version(self):
        import warnings
        warnings.warn(
            'The format_version method is deprecated -- the "version" '
            'argument to ArgumentParser is no longer supported.',
            DeprecationWarning)
        formatter = self._get_formatter()
        formatter.add_text(self.version)
        return formatter.format_help()

    def _get_formatter(self):
        return self.formatter_class(prog=self.prog)

    # =====================
    # Help-printing methods
    # =====================
    def print_usage(self, file=None):
        if file is None:
            file = _sys.stdout
        self._print_message(self.format_usage(), file)

    def print_help(self, file=None):
        if file is None:
            file = _sys.stdout
        self._print_message(self.format_help(), file)

    def print_version(self, file=None):
        import warnings
        warnings.warn(
            'The print_version method is deprecated -- the "version" '
            'argument to ArgumentParser is no longer supported.',
            DeprecationWarning)
        self._print_message(self.format_version(), file)

    def _print_message(self, message, file=None):
        if message:
            if file is None:
                file = _sys.stderr
            file.write(message)

    # ===============
    # Exiting methods
    # ===============
    def exit(self, status=0, message=None):
        if message:
            self._print_message(message, _sys.stderr)
        _sys.exit(status)

    def error(self, message):
        """error(message: string)

        Prints a usage message incorporating the message to stderr and
        exits.

        If you override this in a subclass, it should not return -- it
        should either exit or raise an exception.
        """
        self.print_usage(_sys.stderr)
        self.exit(2, _('%s: error: %s\n') % (self.prog, message))

########NEW FILE########
__FILENAME__ = config
import ConfigParser
import re


class Converter(object):
    """Converts config values to several types.

    Supported types are boolean, float, int, list and unicode.
    """
    _boolean_states = {
        '1':     True,
        'yes':   True,
        'true':  True,
        'on':    True,
        '0':     False,
        'no':    False,
        'false': False,
        'off':   False,
    }

    def to_boolean(self, value):
        key = value.lower()
        if key not in self._boolean_states:
            raise ValueError('Not a boolean: %r. Booleans must be '
                'one of %s.' % (value, ', '.join(self._boolean_states.keys())))

        return self._boolean_states[key]

    def to_float(self, value):
        return float(value)

    def to_int(self, value):
        return int(value)

    def to_list(self, value):
        value = [line.strip() for line in value.splitlines()]
        return [v for v in value if v]

    def to_unicode(self, value):
        return unicode(value)


class Config(ConfigParser.RawConfigParser):
    """Extended RawConfigParser with the following extra features:

    - All `get*()` functions allow a default to be returned. Instead
      of throwing errors when no section or option is found, it returns the
      default value or None.

    - The `get*()` functions can receive a list of sections to be searched in
      order.

    - A `getlist()` method splits multi-line values into a list.

    - It also implements the magical interpolation behavior similar to the one
      from `SafeConfigParser`, but also supports references to sections.
      This means that values can contain format strings which refer to other
      values in the config file. These variables are replaced on the fly.

    An example of variable substituition is::

        [my_section]
        app_name = my_app
        path = path/to/%(app_name)s

    Here, calling `get('my_section', 'path')` will automatically replace
    variables, resulting in `path/to/my_app`. To get the raw value without
    substitutions, use `get('my_section', 'path', raw=True)`.

    To reference a different section, separate the section and option
    names using a pipe::

        [my_section]
        app_name = my_app

        [my_other_section]
        path = path/to/%(my_section|app_name)s

    If any variables aren't found, a `ConfigParser.InterpolationError`is
    raised.

    Variables are case sensitive, differently from the interpolation behavior
    in `SafeConfigParser`.
    """
    converter = Converter()

    _interpolate_re = re.compile(r"%\(([^)]*)\)s")

    def get(self, sections, option, default=None, raw=False):
        """Returns a config value from a given section, converted to unicode.

        :param sections:
            The config section name, or a list of config section names to be
            searched in order.
        :param option:
            The config option name.
        :param default:
            A default value to return in case the section or option are not
            found. Default is None.
        :param raw:
            If True, doesn't perform variable substitution if the value
            has placeholders. Default is False.
        :returns:
            A config value.
        """
        converter = self.converter.to_unicode
        return self._get_wrapper(sections, option, converter, default, raw)

    def getboolean(self, sections, option, default=None, raw=False):
        """Returns a config value from a given section, converted to boolean.

        See :methd:`get` for a description of the parameters.
        """
        converter = self.converter.to_boolean
        return self._get_wrapper(sections, option, converter, default, raw)

    def getfloat(self, sections, option, default=None, raw=False):
        """Returns a config value from a given section, converted to float.

        See :methd:`get` for a description of the parameters.
        """
        converter = self.converter.to_float
        return self._get_wrapper(sections, option, converter, default, raw)

    def getint(self, sections, option, default=None, raw=False):
        """Returns a config value from a given section, converted to int.

        See :methd:`get` for a description of the parameters.
        """
        converter = self.converter.to_int
        return self._get_wrapper(sections, option, converter, default, raw)

    def getlist(self, sections, option, default=None, raw=False):
        """Returns a config value from a given section, converted to boolean.

        See :methd:`get` for a description of the parameters.
        """
        converter = self.converter.to_list
        return self._get_wrapper(sections, option, converter, default, raw)

    def _get(self, section, option):
        """Wrapper for `RawConfigParser.get`."""
        return ConfigParser.RawConfigParser.get(self, section, option)

    def _get_wrapper(self, sections, option, converter, default, raw):
        """Wraps get functions allowing default values and a list of sections
        looked up in order until a value is found.
        """
        if isinstance(sections, basestring):
            sections = [sections]

        for section in sections:
            try:
                value = self._get(section, option)
                if not raw:
                    value = self._interpolate(section, option, value)

                return converter(value)
            except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
                pass

        return default

    def _interpolate(self, section, option, raw_value, tried=None):
        """Performs variable substituition in a config value."""
        variables = self._get_variable_names(section, option, raw_value)
        if not variables:
            return raw_value

        if tried is None:
            tried = [(section, option)]

        values = {}
        for var in variables:
            parts = var.split('|', 1)
            if len(parts) == 1:
                new_section, new_option = section, var
            else:
                new_section, new_option = parts

            if parts in tried:
                continue

            try:
                found = self._get(new_section, new_option)
            except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
                raise ConfigParser.InterpolationError(section, option,
                    'Could not find section %r and option %r.' %
                    (new_section, new_option))

            tried.append((new_section, new_option))
            if not self.has_option(new_section, new_option):
                tried.append(('DEFAULT', new_option))
            values[var] = self._interpolate(new_section, new_option,
                found, tried)

        try:
            return raw_value % values
        except KeyError, e:
            raise ConfigParser.InterpolationError(section, option,
                'Cound not replace %r: variable %r is missing.' %
                (raw_value, e.args[0]))

    def _get_variable_names(self, section, option, raw_value):
        """Returns a list of placeholder names in a config value, if any.

        Adapted from SafeConfigParser._interpolate_some().
        """
        result = set()
        while raw_value:
            pos = raw_value.find('%')
            if pos < 0:
                return result
            if pos > 0:
                raw_value = raw_value[pos:]

            char = raw_value[1:2]
            if char == '%':
                raw_value = raw_value[2:]
            elif char == '(':
                match = self._interpolate_re.match(raw_value)
                if match is None:
                    raise ConfigParser.InterpolationSyntaxError(option,
                        section, 'Bad interpolation variable reference: %r.' %
                        raw_value)

                result.add(match.group(1))
                raw_value = raw_value[match.end():]
            else:
                raise ConfigParser.InterpolationSyntaxError(
                    option, section,
                    "'%%' must be followed by '%%' or '(', "
                    "found: %r." % raw_value)

        return result

########NEW FILE########
__FILENAME__ = easy_install
#############################################################################
#
# Copyright (c) 2005 Zope Corporation and Contributors.
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
"""Python easy_install API

This module provides a high-level Python API for installing packages.
It doesn't install scripts.  It uses setuptools and requires it to be
installed.
"""

import distutils.errors
import fnmatch
import glob
import logging
import os
import pkg_resources
import py_compile
import re
import setuptools.archive_util
import setuptools.command.setopt
import setuptools.package_index
import shutil
import subprocess
import sys
import tempfile
import warnings
#import zc.buildout
import zipimport

_oprp = getattr(os.path, 'realpath', lambda path: path)
def realpath(path):
    return os.path.normcase(os.path.abspath(_oprp(path)))

default_index_url = os.environ.get(
    'buildout-testing-index-url',
    'http://pypi.python.org/simple',
    )

logger = logging.getLogger('easy_install')

url_match = re.compile('[a-z0-9+.-]+://').match

is_win32 = sys.platform == 'win32'
is_jython = sys.platform.startswith('java')
is_distribute = (
    pkg_resources.Requirement.parse('setuptools').key=='distribute')

BROKEN_DASH_S_WARNING = (
    'Buildout has been asked to exclude or limit site-packages so that '
    'builds can be repeatable when using a system Python.  However, '
    'the chosen Python executable has a broken implementation of -S (see '
    'https://bugs.launchpad.net/virtualenv/+bug/572545 for an example '
    "problem) and this breaks buildout's ability to isolate site-packages.  "
    "If the executable already has a clean site-packages (e.g., "
    "using virtualenv's ``--no-site-packages`` option) you may be getting "
    'equivalent repeatability.  To silence this warning, use the -s argument '
    'to the buildout script.  Alternatively, use a Python executable with a '
    'working -S (such as a standard Python binary).')

if is_jython:
    import java.lang.System
    jython_os_name = (java.lang.System.getProperties()['os.name']).lower()

setuptools_loc = pkg_resources.working_set.find(
    pkg_resources.Requirement.parse('setuptools')
    ).location

# Include buildout and setuptools eggs in paths.  We prevent dupes just to
# keep from duplicating any log messages about them.
#buildout_loc = pkg_resources.working_set.find(
#    pkg_resources.Requirement.parse('zc.buildout')).location
buildout_and_setuptools_path = [setuptools_loc]
if os.path.normpath(setuptools_loc) != os.path.normpath(buildout_loc):
    buildout_and_setuptools_path.append(buildout_loc)

def _has_broken_dash_S(executable):
    """Detect https://bugs.launchpad.net/virtualenv/+bug/572545 ."""
    # The first attempt here was to simply have the executable attempt to import
    # ConfigParser and return the return code. That worked except for tests on
    # Windows, where the return code was wrong for the fake Python executable
    # generated by the virtualenv.txt test, apparently because setuptools' .exe
    # file does not pass the -script.py's returncode back properly, at least in
    # some circumstances. Therefore...print statements.
    stdout, stderr = subprocess.Popen(
        [executable, '-Sc',
         'try:\n'
         '    import ConfigParser\n'
         'except ImportError:\n'
         '    print 1\n'
         'else:\n'
         '    print 0\n'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    return bool(int(stdout.strip()))

def _get_system_paths(executable):
    """Return lists of standard lib and site paths for executable.
    """
    # We want to get a list of the site packages, which is not easy.
    # The canonical way to do this is to use
    # distutils.sysconfig.get_python_lib(), but that only returns a
    # single path, which does not reflect reality for many system
    # Pythons, which have multiple additions.  Instead, we start Python
    # with -S, which does not import site.py and set up the extra paths
    # like site-packages or (Ubuntu/Debian) dist-packages and
    # python-support. We then compare that sys.path with the normal one
    # (minus user packages if this is Python 2.6, because we don't
    # support those (yet?).  The set of the normal one minus the set of
    # the ones in ``python -S`` is the set of packages that are
    # effectively site-packages.
    #
    # The given executable might not be the current executable, so it is
    # appropriate to do another subprocess to figure out what the
    # additional site-package paths are. Moreover, even if this
    # executable *is* the current executable, this code might be run in
    # the context of code that has manipulated the sys.path--for
    # instance, to add local zc.buildout or setuptools eggs.
    def get_sys_path(*args, **kwargs):
        cmd = [executable]
        cmd.extend(args)
        cmd.extend([
            "-c", "import sys, os;"
            "print repr([os.path.normpath(p) for p in sys.path if p])"])
        # Windows needs some (as yet to be determined) part of the real env.
        env = os.environ.copy()
        # We need to make sure that PYTHONPATH, which will often be set
        # to include a custom buildout-generated site.py, is not set, or
        # else we will not get an accurate sys.path for the executable.
        env.pop('PYTHONPATH', None)
        env.update(kwargs)
        _proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        stdout, stderr = _proc.communicate();
        if _proc.returncode:
            raise RuntimeError(
                'error trying to get system packages:\n%s' % (stderr,))
        res = eval(stdout.strip())
        try:
            res.remove('.')
        except ValueError:
            pass
        return res
    stdlib = get_sys_path('-S') # stdlib only
    no_user_paths = get_sys_path(PYTHONNOUSERSITE='x')
    site_paths = [p for p in no_user_paths if p not in stdlib]
    return (stdlib, site_paths)

def _get_version_info(executable):
    cmd = [executable, '-Sc',
           'import sys; print(repr(tuple(x for x in sys.version_info)))']
    _proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = _proc.communicate();
    if _proc.returncode:
        raise RuntimeError(
            'error trying to get system packages:\n%s' % (stderr,))
    return eval(stdout.strip())


_versions = {sys.executable: '%d.%d' % sys.version_info[:2]}
def _get_version(executable):
    try:
        return _versions[executable]
    except KeyError:
        cmd = _safe_arg(executable) + ' -V'
        p = subprocess.Popen(cmd,
                             shell=True,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             close_fds=not is_win32)
        i, o = (p.stdin, p.stdout)
        i.close()
        version = o.read().strip()
        o.close()
        pystring, version = version.split()
        assert pystring == 'Python'
        version = re.match('(\d[.]\d)([.].*\d)?$', version).group(1)
        _versions[executable] = version
        return version

FILE_SCHEME = re.compile('file://', re.I).match


class AllowHostsPackageIndex(setuptools.package_index.PackageIndex):
    """Will allow urls that are local to the system.

    No matter what is allow_hosts.
    """
    def url_ok(self, url, fatal=False):
        if FILE_SCHEME(url):
            return True
        return setuptools.package_index.PackageIndex.url_ok(self, url, False)


_indexes = {}
def _get_index(executable, index_url, find_links, allow_hosts=('*',),
               path=None):
    # If path is None, the index will use sys.path.  If you provide an empty
    # path ([]), it will complain uselessly about missing index pages for
    # packages found in the paths that you expect to use.  Therefore, this path
    # is always the same as the _env path in the Installer.
    key = executable, index_url, tuple(find_links)
    index = _indexes.get(key)
    if index is not None:
        return index

    if index_url is None:
        index_url = default_index_url
    index = AllowHostsPackageIndex(
        index_url, hosts=allow_hosts, search_path=path,
        python=_get_version(executable)
        )

    if find_links:
        index.add_find_links(find_links)

    _indexes[key] = index
    return index

clear_index_cache = _indexes.clear

if is_win32:
    # work around spawn lamosity on windows
    # XXX need safe quoting (see the subprocess.list2cmdline) and test
    def _safe_arg(arg):
        return '"%s"' % arg
else:
    _safe_arg = str

# The following string is used to run easy_install in
# Installer._call_easy_install.  It is usually started with python -S
# (that is, don't import site at start).  That flag, and all of the code
# in this snippet above the last two lines, exist to work around a
# relatively rare problem.  If
#
# - your buildout configuration is trying to install a package that is within
#   a namespace package, and
#
# - you use a Python that has a different version of this package
#   installed in in its site-packages using
#   --single-version-externally-managed (that is, using the mechanism
#   sometimes used by system packagers:
#   http://peak.telecommunity.com/DevCenter/setuptools#install-command ), and
#
# - the new package tries to do sys.path tricks in the setup.py to get a
#   __version__,
#
# then the older package will be loaded first, making the setup version
# the wrong number. While very arguably packages simply shouldn't do
# the sys.path tricks, some do, and we don't want buildout to fall over
# when they do.
#
# The namespace packages installed in site-packages with
# --single-version-externally-managed use a mechanism that cause them to
# be processed when site.py is imported  (see
# http://mail.python.org/pipermail/distutils-sig/2009-May/011730.html
# for another description of the problem).  Simply starting Python with
# -S addresses the problem in Python 2.4 and 2.5, but Python 2.6's
# distutils imports a value from the site module, so we unfortunately
# have to do more drastic surgery in the _easy_install_preface code below.
#
# Here's an example of the .pth files created by setuptools when using that
# flag:
#
# import sys,new,os;
# p = os.path.join(sys._getframe(1).f_locals['sitedir'], *('<NAMESPACE>',));
# ie = os.path.exists(os.path.join(p,'__init__.py'));
# m = not ie and sys.modules.setdefault('<NAMESPACE>',new.module('<NAMESPACE>'));
# mp = (m or []) and m.__dict__.setdefault('__path__',[]);
# (p not in mp) and mp.append(p)
#
# The code, below, then, runs under -S, indicating that site.py should
# not be loaded initially.  It gets the initial sys.path under these
# circumstances, and then imports site (because Python 2.6's distutils
# will want it, as mentioned above). It then reinstates the old sys.path
# value. Then it removes namespace packages (created by the setuptools
# code above) from sys.modules.  It identifies namespace packages by
# iterating over every loaded module.  It first looks if there is a
# __path__, so it is a package; and then it sees if that __path__ does
# not have an __init__.py.  (Note that PEP 382,
# http://www.python.org/dev/peps/pep-0382, makes it possible to have a
# namespace package that has an __init__.py, but also should make it
# unnecessary for site.py to preprocess these packages, so it should be
# fine, as far as can be guessed as of this writing.)  Finally, it
# imports easy_install and runs it.
_easy_install_preface = '''\
import sys,os;\
p = sys.path[:];\
import site;\
sys.path[:] = p;\
[sys.modules.pop(k) for k, v in sys.modules.items()\
 if hasattr(v, '__path__') and len(v.__path__)==1 and\
 not os.path.exists(os.path.join(v.__path__[0],'__init__.py'))];'''
_easy_install_cmd = (
    'from setuptools.command.easy_install import main;main()')


class Installer:

    _versions = {}
    _download_cache = None
    _install_from_cache = False
    _prefer_final = True
    _use_dependency_links = True
    _allow_picked_versions = True
    _always_unzip = False
    _include_site_packages = True
    _allowed_eggs_from_site_packages = ('*',)

    def __init__(self,
                 dest=None,
                 links=(),
                 index=None,
                 executable=sys.executable,
                 always_unzip=None,
                 path=None,
                 newest=True,
                 versions=None,
                 use_dependency_links=None,
                 allow_hosts=('*',),
                 include_site_packages=None,
                 allowed_eggs_from_site_packages=None,
                 prefer_final=None,
                 ):
        self._dest = dest
        self._allow_hosts = allow_hosts

        if self._install_from_cache:
            if not self._download_cache:
                raise ValueError("install_from_cache set to true with no"
                                 " download cache")
            links = ()
            index = 'file://' + self._download_cache

        if use_dependency_links is not None:
            self._use_dependency_links = use_dependency_links
        if prefer_final is not None:
            self._prefer_final = prefer_final
        self._links = links = list(_fix_file_links(links))
        if self._download_cache and (self._download_cache not in links):
            links.insert(0, self._download_cache)

        self._index_url = index
        self._executable = executable
        self._has_broken_dash_S = _has_broken_dash_S(self._executable)
        if always_unzip is not None:
            self._always_unzip = always_unzip
        path = (path and path[:] or [])
        if include_site_packages is not None:
            self._include_site_packages = include_site_packages
        if allowed_eggs_from_site_packages is not None:
            self._allowed_eggs_from_site_packages = tuple(
                allowed_eggs_from_site_packages)
        if self._has_broken_dash_S:
            if (not self._include_site_packages or
                self._allowed_eggs_from_site_packages != ('*',)):
                # We can't do this if the executable has a broken -S.
                warnings.warn(BROKEN_DASH_S_WARNING)
                self._include_site_packages = True
                self._allowed_eggs_from_site_packages = ('*',)
            self._easy_install_cmd = _easy_install_cmd
        else:
            self._easy_install_cmd = _easy_install_preface + _easy_install_cmd
        self._easy_install_cmd = _safe_arg(self._easy_install_cmd)
        stdlib, self._site_packages = _get_system_paths(executable)
        version_info = _get_version_info(executable)
        if version_info == sys.version_info:
            # Maybe we can add the buildout and setuptools path.  If we
            # are including site_packages, we only have to include the extra
            # bits here, so we don't duplicate.  On the other hand, if we
            # are not including site_packages, we only want to include the
            # parts that are not in site_packages, so the code is the same.
            path.extend(
                set(buildout_and_setuptools_path).difference(
                    self._site_packages))
        if self._include_site_packages:
            path.extend(self._site_packages)
        if dest is not None and dest not in path:
            path.insert(0, dest)
        self._path = path
        if self._dest is None:
            newest = False
        self._newest = newest
        self._env = pkg_resources.Environment(path,
                                              python=_get_version(executable))
        self._index = _get_index(executable, index, links, self._allow_hosts,
                                 self._path)

        if versions is not None:
            self._versions = versions

    _allowed_eggs_from_site_packages_regex = None
    def allow_site_package_egg(self, name):
        if (not self._include_site_packages or
            not self._allowed_eggs_from_site_packages):
            # If the answer is a blanket "no," perform a shortcut.
            return False
        if self._allowed_eggs_from_site_packages_regex is None:
            pattern = '(%s)' % (
                '|'.join(
                    fnmatch.translate(name)
                    for name in self._allowed_eggs_from_site_packages),
                )
            self._allowed_eggs_from_site_packages_regex = re.compile(pattern)
        return bool(self._allowed_eggs_from_site_packages_regex.match(name))

    def _satisfied(self, req, source=None):
        # We get all distributions that match the given requirement.  If we are
        # not supposed to include site-packages for the given egg, we also
        # filter those out. Even if include_site_packages is False and so we
        # have excluded site packages from the _env's paths (see
        # Installer.__init__), we need to do the filtering here because an
        # .egg-link, such as one for setuptools or zc.buildout installed by
        # zc.buildout.buildout.Buildout.bootstrap, can indirectly include a
        # path in our _site_packages.
        dists = [dist for dist in self._env[req.project_name] if (
                    dist in req and (
                        dist.location not in self._site_packages or
                        self.allow_site_package_egg(dist.project_name))
                    )
                ]
        if not dists:
            logger.debug('We have no distributions for %s that satisfies %r.',
                         req.project_name, str(req))

            return None, self._obtain(req, source)

        # Note that dists are sorted from best to worst, as promised by
        # env.__getitem__

        for dist in dists:
            if (dist.precedence == pkg_resources.DEVELOP_DIST and
                dist.location not in self._site_packages):
                # System eggs are sometimes installed as develop eggs.
                # Those are not the kind of develop eggs we are looking for
                # here: we want ones that the buildout itself has locally as
                # develop eggs.
                logger.debug('We have a develop egg: %s', dist)
                return dist, None

        # Special common case, we have a specification for a single version:
        specs = req.specs
        if len(specs) == 1 and specs[0][0] == '==':
            logger.debug('We have the distribution that satisfies %r.',
                         str(req))
            return dists[0], None

        if self._prefer_final:
            fdists = [dist for dist in dists
                      if _final_version(dist.parsed_version)
                      ]
            if fdists:
                # There are final dists, so only use those
                dists = fdists

        if not self._newest:
            # We don't need the newest, so we'll use the newest one we
            # find, which is the first returned by
            # Environment.__getitem__.
            return dists[0], None

        best_we_have = dists[0] # Because dists are sorted from best to worst

        # We have some installed distros.  There might, theoretically, be
        # newer ones.  Let's find out which ones are available and see if
        # any are newer.  We only do this if we're willing to install
        # something, which is only true if dest is not None:

        if self._dest is not None:
            best_available = self._obtain(req, source)
        else:
            best_available = None

        if best_available is None:
            # That's a bit odd.  There aren't any distros available.
            # We should use the best one we have that meets the requirement.
            logger.debug(
                'There are no distros available that meet %r.\n'
                'Using our best, %s.',
                str(req), best_available)
            return best_we_have, None

        if self._prefer_final:
            if _final_version(best_available.parsed_version):
                if _final_version(best_we_have.parsed_version):
                    if (best_we_have.parsed_version
                        <
                        best_available.parsed_version
                        ):
                        return None, best_available
                else:
                    return None, best_available
            else:
                if (not _final_version(best_we_have.parsed_version)
                    and
                    (best_we_have.parsed_version
                     <
                     best_available.parsed_version
                     )
                    ):
                    return None, best_available
        else:
            if (best_we_have.parsed_version
                <
                best_available.parsed_version
                ):
                return None, best_available

        logger.debug(
            'We have the best distribution that satisfies %r.',
            str(req))
        return best_we_have, None

    def _load_dist(self, dist):
        dists = pkg_resources.Environment(
            dist.location,
            python=_get_version(self._executable),
            )[dist.project_name]
        assert len(dists) == 1
        return dists[0]

    def _call_easy_install(self, spec, ws, dest, dist):

        tmp = tempfile.mkdtemp(dir=dest)
        try:
            path = setuptools_loc

            args = ('-c', self._easy_install_cmd, '-mUNxd', _safe_arg(tmp))
            if not self._has_broken_dash_S:
                args = ('-S',) + args
            if self._always_unzip:
                args += ('-Z', )
            level = logger.getEffectiveLevel()
            if level > 0:
                args += ('-q', )
            elif level < 0:
                args += ('-v', )

            args += (_safe_arg(spec), )

            if level <= logging.DEBUG:
                logger.debug('Running easy_install:\n%s "%s"\npath=%s\n',
                             self._executable, '" "'.join(args), path)

            if is_jython:
                extra_env = dict(os.environ, PYTHONPATH=path)
            else:
                args += (dict(os.environ, PYTHONPATH=path), )

            sys.stdout.flush() # We want any pending output first

            if is_jython:
                exit_code = subprocess.Popen(
                [_safe_arg(self._executable)] + list(args),
                env=extra_env).wait()
            else:
                exit_code = os.spawnle(
                    os.P_WAIT, self._executable, _safe_arg (self._executable),
                    *args)

            dists = []
            env = pkg_resources.Environment(
                [tmp],
                python=_get_version(self._executable),
                )
            for project in env:
                dists.extend(env[project])

            if exit_code:
                logger.error(
                    "An error occurred when trying to install %s. "
                    "Look above this message for any errors that "
                    "were output by easy_install.",
                    dist)

            if not dists:
                raise UserError("Couldn't install: %s" % dist)

            if len(dists) > 1:
                logger.warn("Installing %s\n"
                            "caused multiple distributions to be installed:\n"
                            "%s\n",
                            dist, '\n'.join(map(str, dists)))
            else:
                d = dists[0]
                if d.project_name != dist.project_name:
                    logger.warn("Installing %s\n"
                                "Caused installation of a distribution:\n"
                                "%s\n"
                                "with a different project name.",
                                dist, d)
                if d.version != dist.version:
                    logger.warn("Installing %s\n"
                                "Caused installation of a distribution:\n"
                                "%s\n"
                                "with a different version.",
                                dist, d)

            result = []
            for d in dists:
                newloc = os.path.join(dest, os.path.basename(d.location))
                if os.path.exists(newloc):
                    if os.path.isdir(newloc):
                        shutil.rmtree(newloc)
                    else:
                        os.remove(newloc)
                os.rename(d.location, newloc)

                [d] = pkg_resources.Environment(
                    [newloc],
                    python=_get_version(self._executable),
                    )[d.project_name]

                result.append(d)

            return result

        finally:
            shutil.rmtree(tmp)

    def _obtain(self, requirement, source=None):
        # initialize out index for this project:
        index = self._index

        if index.obtain(requirement) is None:
            # Nothing is available.
            return None

        # Filter the available dists for the requirement and source flag.  If
        # we are not supposed to include site-packages for the given egg, we
        # also filter those out. Even if include_site_packages is False and so
        # we have excluded site packages from the _env's paths (see
        # Installer.__init__), we need to do the filtering here because an
        # .egg-link, such as one for setuptools or zc.buildout installed by
        # zc.buildout.buildout.Buildout.bootstrap, can indirectly include a
        # path in our _site_packages.
        dists = [dist for dist in index[requirement.project_name] if (
                    dist in requirement and (
                        dist.location not in self._site_packages or
                        self.allow_site_package_egg(dist.project_name))
                    and (
                        (not source) or
                        (dist.precedence == pkg_resources.SOURCE_DIST))
                    )
                 ]

        # If we prefer final dists, filter for final and use the
        # result if it is non empty.
        if self._prefer_final:
            fdists = [dist for dist in dists
                      if _final_version(dist.parsed_version)
                      ]
            if fdists:
                # There are final dists, so only use those
                dists = fdists

        # Now find the best one:
        best = []
        bestv = ()
        for dist in dists:
            distv = dist.parsed_version
            if distv > bestv:
                best = [dist]
                bestv = distv
            elif distv == bestv:
                best.append(dist)

        if not best:
            return None

        if len(best) == 1:
            return best[0]

        if self._download_cache:
            for dist in best:
                if (realpath(os.path.dirname(dist.location))
                    ==
                    self._download_cache
                    ):
                    return dist

        best.sort()
        return best[-1]

    def _fetch(self, dist, tmp, download_cache):
        if (download_cache
            and (realpath(os.path.dirname(dist.location)) == download_cache)
            ):
            return dist

        new_location = self._index.download(dist.location, tmp)
        if (download_cache
            and (realpath(new_location) == realpath(dist.location))
            and os.path.isfile(new_location)
            ):
            # setuptools avoids making extra copies, but we want to copy
            # to the download cache
            shutil.copy2(new_location, tmp)
            new_location = os.path.join(tmp, os.path.basename(new_location))

        return dist.clone(location=new_location)

    def _get_dist(self, requirement, ws, always_unzip):

        __doing__ = 'Getting distribution for %r.', str(requirement)

        # Maybe an existing dist is already the best dist that satisfies the
        # requirement
        dist, avail = self._satisfied(requirement)

        if dist is None:
            if self._dest is not None:
                logger.info(*__doing__)

            # Retrieve the dist:
            if avail is None:
                raise MissingDistribution(requirement, ws)

            # We may overwrite distributions, so clear importer
            # cache.
            sys.path_importer_cache.clear()

            tmp = self._download_cache
            if tmp is None:
                tmp = tempfile.mkdtemp('get_dist')

            try:
                dist = self._fetch(avail, tmp, self._download_cache)

                if dist is None:
                    raise UserError(
                        "Couldn't download distribution %s." % avail)

                if dist.precedence == pkg_resources.EGG_DIST:
                    # It's already an egg, just fetch it into the dest

                    newloc = os.path.join(
                        self._dest, os.path.basename(dist.location))

                    if os.path.isdir(dist.location):
                        # we got a directory. It must have been
                        # obtained locally.  Just copy it.
                        shutil.copytree(dist.location, newloc)
                    else:

                        if self._always_unzip:
                            should_unzip = True
                        else:
                            metadata = pkg_resources.EggMetadata(
                                zipimport.zipimporter(dist.location)
                                )
                            should_unzip = (
                                metadata.has_metadata('not-zip-safe')
                                or
                                not metadata.has_metadata('zip-safe')
                                )

                        if should_unzip:
                            setuptools.archive_util.unpack_archive(
                                dist.location, newloc)
                        else:
                            shutil.copyfile(dist.location, newloc)

                    redo_pyc(newloc)

                    # Getting the dist from the environment causes the
                    # distribution meta data to be read.  Cloning isn't
                    # good enough.
                    dists = pkg_resources.Environment(
                        [newloc],
                        python=_get_version(self._executable),
                        )[dist.project_name]
                else:
                    # It's some other kind of dist.  We'll let easy_install
                    # deal with it:
                    dists = self._call_easy_install(
                        dist.location, ws, self._dest, dist)
                    for dist in dists:
                        redo_pyc(dist.location)

            finally:
                if tmp != self._download_cache:
                    shutil.rmtree(tmp)

            self._env.scan([self._dest])
            dist = self._env.best_match(requirement, ws)
            logger.info("Got %s.", dist)

        else:
            dists = [dist]

        for dist in dists:
            if (dist.has_metadata('dependency_links.txt')
                and not self._install_from_cache
                and self._use_dependency_links
                ):
                for link in dist.get_metadata_lines('dependency_links.txt'):
                    link = link.strip()
                    if link not in self._links:
                        logger.debug('Adding find link %r from %s', link, dist)
                        self._links.append(link)
                        self._index = _get_index(self._executable,
                                                 self._index_url, self._links,
                                                 self._allow_hosts, self._path)

        for dist in dists:
            # Check whether we picked a version and, if we did, report it:
            if not (
                dist.precedence == pkg_resources.DEVELOP_DIST
                or
                (len(requirement.specs) == 1
                 and
                 requirement.specs[0][0] == '==')
                ):
                logger.debug('Picked: %s = %s',
                             dist.project_name, dist.version)
                if not self._allow_picked_versions:
                    raise UserError(
                        'Picked: %s = %s' % (dist.project_name, dist.version)
                        )

        return dists

    def _maybe_add_setuptools(self, ws, dist):
        if dist.has_metadata('namespace_packages.txt'):
            for r in dist.requires():
                if r.project_name in ('setuptools', 'distribute'):
                    break
            else:
                # We have a namespace package but no requirement for setuptools
                if dist.precedence == pkg_resources.DEVELOP_DIST:
                    logger.warn(
                        "Develop distribution: %s\n"
                        "uses namespace packages but the distribution "
                        "does not require setuptools.",
                        dist)
                requirement = self._constrain(
                    pkg_resources.Requirement.parse('setuptools')
                    )
                if ws.find(requirement) is None:
                    for dist in self._get_dist(requirement, ws, False):
                        ws.add(dist)


    def _constrain(self, requirement):
        if is_distribute and requirement.key == 'setuptools':
            requirement = pkg_resources.Requirement.parse('distribute')
        version = self._versions.get(requirement.project_name)
        if version:
            if version not in requirement:
                logger.error("The version, %s, is not consistent with the "
                             "requirement, %r.", version, str(requirement))
                raise IncompatibleVersionError("Bad version", version)

            requirement = pkg_resources.Requirement.parse(
                "%s[%s] ==%s" % (requirement.project_name,
                               ','.join(requirement.extras),
                               version))

        return requirement

    def install(self, specs, working_set=None):

        logger.debug('Installing %s.', repr(specs)[1:-1])

        path = self._path
        destination = self._dest
        if destination is not None and destination not in path:
            path.insert(0, destination)

        requirements = [self._constrain(pkg_resources.Requirement.parse(spec))
                        for spec in specs]



        if working_set is None:
            ws = pkg_resources.WorkingSet([])
        else:
            ws = working_set

        for requirement in requirements:
            for dist in self._get_dist(requirement, ws, self._always_unzip):
                ws.add(dist)
                self._maybe_add_setuptools(ws, dist)

        # OK, we have the requested distributions and they're in the working
        # set, but they may have unmet requirements.  We'll resolve these
        # requirements. This is code modified from
        # pkg_resources.WorkingSet.resolve.  We can't reuse that code directly
        # because we have to constrain our requirements (see
        # versions_section_ignored_for_dependency_in_favor_of_site_packages in
        # zc.buildout.tests).
        requirements.reverse() # Set up the stack.
        processed = {}  # This is a set of processed requirements.
        best = {}  # This is a mapping of key -> dist.
        # Note that we don't use the existing environment, because we want
        # to look for new eggs unless what we have is the best that
        # matches the requirement.
        env = pkg_resources.Environment(ws.entries)
        while requirements:
            # Process dependencies breadth-first.
            req = self._constrain(requirements.pop(0))
            if req in processed:
                # Ignore cyclic or redundant dependencies.
                continue
            dist = best.get(req.key)
            if dist is None:
                # Find the best distribution and add it to the map.
                dist = ws.by_key.get(req.key)
                if dist is None:
                    try:
                        dist = best[req.key] = env.best_match(req, ws)
                    except pkg_resources.VersionConflict, err:
                        raise VersionConflict(err, ws)
                    if dist is None or (
                        dist.location in self._site_packages and not
                        self.allow_site_package_egg(dist.project_name)):
                        # If we didn't find a distribution in the
                        # environment, or what we found is from site
                        # packages and not allowed to be there, try
                        # again.
                        if destination:
                            logger.debug('Getting required %r', str(req))
                        else:
                            logger.debug('Adding required %r', str(req))
                        _log_requirement(ws, req)
                        for dist in self._get_dist(req,
                                                   ws, self._always_unzip):
                            ws.add(dist)
                            self._maybe_add_setuptools(ws, dist)
            if dist not in req:
                # Oops, the "best" so far conflicts with a dependency.
                raise VersionConflict(
                    pkg_resources.VersionConflict(dist, req), ws)
            requirements.extend(dist.requires(req.extras)[::-1])
            processed[req] = True
            if dist.location in self._site_packages:
                logger.debug('Egg from site-packages: %s', dist)
        return ws

    def build(self, spec, build_ext):

        requirement = self._constrain(pkg_resources.Requirement.parse(spec))

        dist, avail = self._satisfied(requirement, 1)
        if dist is not None:
            return [dist.location]

        # Retrieve the dist:
        if avail is None:
            raise UserError(
                "Couldn't find a source distribution for %r."
                % str(requirement))

        logger.debug('Building %r', spec)

        tmp = self._download_cache
        if tmp is None:
            tmp = tempfile.mkdtemp('get_dist')

        try:
            dist = self._fetch(avail, tmp, self._download_cache)

            build_tmp = tempfile.mkdtemp('build')
            try:
                setuptools.archive_util.unpack_archive(dist.location,
                                                       build_tmp)
                if os.path.exists(os.path.join(build_tmp, 'setup.py')):
                    base = build_tmp
                else:
                    setups = glob.glob(
                        os.path.join(build_tmp, '*', 'setup.py'))
                    if not setups:
                        raise distutils.errors.DistutilsError(
                            "Couldn't find a setup script in %s"
                            % os.path.basename(dist.location)
                            )
                    if len(setups) > 1:
                        raise distutils.errors.DistutilsError(
                            "Multiple setup scripts in %s"
                            % os.path.basename(dist.location)
                            )
                    base = os.path.dirname(setups[0])

                setup_cfg = os.path.join(base, 'setup.cfg')
                if not os.path.exists(setup_cfg):
                    f = open(setup_cfg, 'w')
                    f.close()
                setuptools.command.setopt.edit_config(
                    setup_cfg, dict(build_ext=build_ext))

                dists = self._call_easy_install(
                    base, pkg_resources.WorkingSet(),
                    self._dest, dist)

                for dist in dists:
                    redo_pyc(dist.location)

                return [dist.location for dist in dists]
            finally:
                shutil.rmtree(build_tmp)

        finally:
            if tmp != self._download_cache:
                shutil.rmtree(tmp)

def default_versions(versions=None):
    old = Installer._versions
    if versions is not None:
        Installer._versions = versions
    return old

def download_cache(path=-1):
    old = Installer._download_cache
    if path != -1:
        if path:
            path = realpath(path)
        Installer._download_cache = path
    return old

def install_from_cache(setting=None):
    old = Installer._install_from_cache
    if setting is not None:
        Installer._install_from_cache = bool(setting)
    return old

def prefer_final(setting=None):
    old = Installer._prefer_final
    if setting is not None:
        Installer._prefer_final = bool(setting)
    return old

def include_site_packages(setting=None):
    old = Installer._include_site_packages
    if setting is not None:
        Installer._include_site_packages = bool(setting)
    return old

def allowed_eggs_from_site_packages(setting=None):
    old = Installer._allowed_eggs_from_site_packages
    if setting is not None:
        Installer._allowed_eggs_from_site_packages = tuple(setting)
    return old

def use_dependency_links(setting=None):
    old = Installer._use_dependency_links
    if setting is not None:
        Installer._use_dependency_links = bool(setting)
    return old

def allow_picked_versions(setting=None):
    old = Installer._allow_picked_versions
    if setting is not None:
        Installer._allow_picked_versions = bool(setting)
    return old

def always_unzip(setting=None):
    old = Installer._always_unzip
    if setting is not None:
        Installer._always_unzip = bool(setting)
    return old

def install(specs, dest,
            links=(), index=None,
            executable=sys.executable, always_unzip=None,
            path=None, working_set=None, newest=True, versions=None,
            use_dependency_links=None, allow_hosts=('*',),
            include_site_packages=None, allowed_eggs_from_site_packages=None,
            prefer_final=None):
    installer = Installer(
        dest, links, index, executable, always_unzip, path, newest,
        versions, use_dependency_links, allow_hosts=allow_hosts,
        include_site_packages=include_site_packages,
        allowed_eggs_from_site_packages=allowed_eggs_from_site_packages,
        prefer_final=prefer_final)
    return installer.install(specs, working_set)


def build(spec, dest, build_ext,
          links=(), index=None,
          executable=sys.executable,
          path=None, newest=True, versions=None, allow_hosts=('*',),
          include_site_packages=None, allowed_eggs_from_site_packages=None):
    installer = Installer(
        dest, links, index, executable, True, path, newest, versions,
        allow_hosts=allow_hosts,
        include_site_packages=include_site_packages,
        allowed_eggs_from_site_packages=allowed_eggs_from_site_packages)
    return installer.build(spec, build_ext)



def _rm(*paths):
    for path in paths:
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.exists(path):
            os.remove(path)

def _copyeggs(src, dest, suffix, undo):
    result = []
    undo.append(lambda : _rm(*result))
    for name in os.listdir(src):
        if name.endswith(suffix):
            new = os.path.join(dest, name)
            _rm(new)
            os.rename(os.path.join(src, name), new)
            result.append(new)

    assert len(result) == 1, str(result)
    undo.pop()

    return result[0]

def develop(setup, dest,
            build_ext=None,
            executable=sys.executable):

    if os.path.isdir(setup):
        directory = setup
        setup = os.path.join(directory, 'setup.py')
    else:
        directory = os.path.dirname(setup)

    undo = []
    try:
        if build_ext:
            setup_cfg = os.path.join(directory, 'setup.cfg')
            if os.path.exists(setup_cfg):
                os.rename(setup_cfg, setup_cfg+'-develop-aside')
                def restore_old_setup():
                    if os.path.exists(setup_cfg):
                        os.remove(setup_cfg)
                    os.rename(setup_cfg+'-develop-aside', setup_cfg)
                undo.append(restore_old_setup)
            else:
                open(setup_cfg, 'w')
                undo.append(lambda: os.remove(setup_cfg))
            setuptools.command.setopt.edit_config(
                setup_cfg, dict(build_ext=build_ext))

        fd, tsetup = tempfile.mkstemp()
        undo.append(lambda: os.remove(tsetup))
        undo.append(lambda: os.close(fd))

        os.write(fd, runsetup_template % dict(
            setuptools=setuptools_loc,
            setupdir=directory,
            setup=setup,
            __file__ = setup,
            ))

        tmp3 = tempfile.mkdtemp('build', dir=dest)
        undo.append(lambda : shutil.rmtree(tmp3))

        args = [
            _safe_arg(tsetup),
            '-q', 'develop', '-mxN',
            '-d', _safe_arg(tmp3),
            ]

        log_level = logger.getEffectiveLevel()
        if log_level <= 0:
            if log_level == 0:
                del args[1]
            else:
                args[1] == '-v'
        if log_level < logging.DEBUG:
            logger.debug("in: %r\n%s", directory, ' '.join(args))

        if is_jython:
            assert subprocess.Popen([_safe_arg(executable)] + args).wait() == 0
        else:
            assert os.spawnl(os.P_WAIT, executable, _safe_arg(executable),
                             *args) == 0

        return _copyeggs(tmp3, dest, '.egg-link', undo)

    finally:
        undo.reverse()
        [f() for f in undo]

def working_set(specs, executable, path, include_site_packages=None,
                allowed_eggs_from_site_packages=None, prefer_final=None):
    return install(
        specs, None, executable=executable, path=path,
        include_site_packages=include_site_packages,
        allowed_eggs_from_site_packages=allowed_eggs_from_site_packages,
        prefer_final=prefer_final)

############################################################################
# Script generation functions

def scripts(
    reqs, working_set, executable, dest,
    scripts=None,
    extra_paths=(),
    arguments='',
    interpreter=None,
    initialization='',
    relative_paths=False,
    ):
    """Generate scripts and/or an interpreter.

    See sitepackage_safe_scripts for a version that can be used with a Python
    that has code installed in site-packages. It has more options and a
    different approach.
    """
    path = _get_path(working_set, extra_paths)
    if initialization:
        initialization = '\n'+initialization+'\n'
    generated = _generate_scripts(
        reqs, working_set, dest, path, scripts, relative_paths,
        initialization, executable, arguments)
    if interpreter:
        sname = os.path.join(dest, interpreter)
        spath, rpsetup = _relative_path_and_setup(sname, path, relative_paths)
        generated.extend(
            _pyscript(spath, sname, executable, rpsetup))
    return generated

# We need to give an alternate name to the ``scripts`` function so that it
# can be referenced within sitepackage_safe_scripts, which uses ``scripts``
# as an argument name.
_original_scripts_function = scripts

def sitepackage_safe_scripts(
    dest, working_set, executable, site_py_dest,
    reqs=(),
    scripts=None,
    interpreter=None,
    extra_paths=(),
    initialization='',
    include_site_packages=False,
    exec_sitecustomize=False,
    relative_paths=False,
    script_arguments='',
    script_initialization='',
    ):
    """Generate scripts and/or an interpreter from a system Python.

    This accomplishes the same job as the ``scripts`` function, above,
    but it does so in an alternative way that allows safely including
    Python site packages, if desired, and  choosing to execute the Python's
    sitecustomize.
    """
    if _has_broken_dash_S(executable):
        if not include_site_packages:
            warnings.warn(BROKEN_DASH_S_WARNING)
        return _original_scripts_function(
            reqs, working_set, executable, dest, scripts, extra_paths,
            script_arguments, interpreter, initialization, relative_paths)
    generated = []
    generated.append(_generate_sitecustomize(
        site_py_dest, executable, initialization, exec_sitecustomize))
    generated.append(_generate_site(
        site_py_dest, working_set, executable, extra_paths,
        include_site_packages, relative_paths))
    script_initialization = _script_initialization_template % dict(
        site_py_dest=site_py_dest,
        script_initialization=script_initialization)
    if not script_initialization.endswith('\n'):
        script_initialization += '\n'
    generated.extend(_generate_scripts(
        reqs, working_set, dest, [site_py_dest], scripts, relative_paths,
        script_initialization, executable, script_arguments, block_site=True))
    if interpreter:
        generated.extend(_generate_interpreter(
            interpreter, dest, executable, site_py_dest, relative_paths))
    return generated

_script_initialization_template = '''
import os
path = sys.path[0]
if os.environ.get('PYTHONPATH'):
    path = os.pathsep.join([path, os.environ['PYTHONPATH']])
os.environ['BUILDOUT_ORIGINAL_PYTHONPATH'] = os.environ.get('PYTHONPATH', '')
os.environ['PYTHONPATH'] = path
import site # imports custom buildout-generated site.py
%(script_initialization)s'''

# Utilities for the script generation functions.

# These are shared by both ``scripts`` and ``sitepackage_safe_scripts``

def _get_path(working_set, extra_paths=()):
    """Given working set and extra paths, return a normalized path list."""
    path = [dist.location for dist in working_set]
    path.extend(extra_paths)
    return map(realpath, path)

def _generate_scripts(reqs, working_set, dest, path, scripts, relative_paths,
                      initialization, executable, arguments,
                      block_site=False):
    """Generate scripts for the given requirements.

    - reqs is an iterable of string requirements or entry points.
    - The requirements must be findable in the given working_set.
    - The dest is the directory in which the scripts should be created.
    - The path is a list of paths that should be added to sys.path.
    - The scripts is an optional dictionary.  If included, the keys should be
      the names of the scripts that should be created, as identified in their
      entry points; and the values should be the name the script should
      actually be created with.
    - relative_paths, if given, should be the path that is the root of the
      buildout (the common path that should be the root of what is relative).
    """
    if isinstance(reqs, str):
        raise TypeError('Expected iterable of requirements or entry points,'
                        ' got string.')
    generated = []
    entry_points = []
    for req in reqs:
        if isinstance(req, str):
            req = pkg_resources.Requirement.parse(req)
            dist = working_set.find(req)
            for name in pkg_resources.get_entry_map(dist, 'console_scripts'):
                entry_point = dist.get_entry_info('console_scripts', name)
                entry_points.append(
                    (name, entry_point.module_name,
                     '.'.join(entry_point.attrs))
                    )
        else:
            entry_points.append(req)
    for name, module_name, attrs in entry_points:
        if scripts is not None:
            sname = scripts.get(name)
            if sname is None:
                continue
        else:
            sname = name
        sname = os.path.join(dest, sname)
        spath, rpsetup = _relative_path_and_setup(sname, path, relative_paths)
        generated.extend(
            _script(sname, executable, rpsetup, spath, initialization,
                    module_name, attrs, arguments, block_site=block_site))
    return generated

def _relative_path_and_setup(sname, path,
                             relative_paths=False, indent_level=1,
                             omit_os_import=False):
    """Return a string of code of paths and of setup if appropriate.

    - sname is the full path to the script name to be created.
    - path is the list of paths to be added to sys.path.
    - relative_paths, if given, should be the path that is the root of the
      buildout (the common path that should be the root of what is relative).
    - indent_level is the number of four-space indents that the path should
      insert before each element of the path.
    """
    if relative_paths:
        relative_paths = os.path.normcase(relative_paths)
        sname = os.path.normcase(os.path.abspath(sname))
        spath = _format_paths(
            [_relativitize(os.path.normcase(path_item), sname, relative_paths)
             for path_item in path], indent_level=indent_level)
        rpsetup = relative_paths_setup
        if not omit_os_import:
            rpsetup = '\n\nimport os\n' + rpsetup
        for i in range(_relative_depth(relative_paths, sname)):
            rpsetup += "\nbase = os.path.dirname(base)"
    else:
        spath = _format_paths((repr(p) for p in path),
                              indent_level=indent_level)
        rpsetup = ''
    return spath, rpsetup

def _relative_depth(common, path):
    """Return number of dirs separating ``path`` from ancestor, ``common``.

    For instance, if path is /foo/bar/baz/bing, and common is /foo, this will
    return 2--in UNIX, the number of ".." to get from bing's directory
    to foo.

    This is a helper for _relative_path_and_setup.
    """
    n = 0
    while 1:
        dirname = os.path.dirname(path)
        if dirname == path:
            raise AssertionError("dirname of %s is the same" % dirname)
        if dirname == common:
            break
        n += 1
        path = dirname
    return n

def _relative_path(common, path):
    """Return the relative path from ``common`` to ``path``.

    This is a helper for _relativitize, which is a helper to
    _relative_path_and_setup.
    """
    r = []
    while 1:
        dirname, basename = os.path.split(path)
        r.append(basename)
        if dirname == common:
            break
        if dirname == path:
            raise AssertionError("dirname of %s is the same" % dirname)
        path = dirname
    r.reverse()
    return os.path.join(*r)

def _relativitize(path, script, relative_paths):
    """Return a code string for the given path.

    Path is relative to the base path ``relative_paths``if the common prefix
    between ``path`` and ``script`` starts with ``relative_paths``.
    """
    if path == script:
        raise AssertionError("path == script")
    common = os.path.dirname(os.path.commonprefix([path, script]))
    if (common == relative_paths or
        common.startswith(os.path.join(relative_paths, ''))
        ):
        return "join(base, %r)" % _relative_path(common, path)
    else:
        return repr(path)

relative_paths_setup = """
join = os.path.join
base = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))"""

def _write_script(full_name, contents, logged_type):
    """Write contents of script in full_name, logging the action.

    The only tricky bit in this function is that it supports Windows by
    creating exe files using a pkg_resources helper.
    """
    generated = []
    script_name = full_name
    if is_win32:
        script_name += '-script.py'
        # Generate exe file and give the script a magic name.
        exe = full_name + '.exe'
        new_data = pkg_resources.resource_string('setuptools', 'cli.exe')
        if not os.path.exists(exe) or (open(exe, 'rb').read() != new_data):
            # Only write it if it's different.
            open(exe, 'wb').write(new_data)
        generated.append(exe)
    changed = not (os.path.exists(script_name) and
                   open(script_name).read() == contents)
    if changed:
        open(script_name, 'w').write(contents)
        try:
            os.chmod(script_name, 0755)
        except (AttributeError, os.error):
            pass
        logger.info("Generated %s %r.", logged_type, full_name)
    generated.append(script_name)
    return generated

def _format_paths(paths, indent_level=1):
    """Format paths for inclusion in a script."""
    separator = ',\n' + indent_level * '    '
    return separator.join(paths)

def _script(dest, executable, relative_paths_setup, path, initialization,
            module_name, attrs, arguments, block_site=False):
    if block_site:
        dash_S = ' -S'
    else:
        dash_S = ''
    contents = script_template % dict(
        python=_safe_arg(executable),
        dash_S=dash_S,
        path=path,
        module_name=module_name,
        attrs=attrs,
        arguments=arguments,
        initialization=initialization,
        relative_paths_setup=relative_paths_setup,
        )
    return _write_script(dest, contents, 'script')

if is_jython and jython_os_name == 'linux':
    script_header = '#!/usr/bin/env %(python)s%(dash_S)s'
else:
    script_header = '#!%(python)s%(dash_S)s'

sys_path_template = '''\
import sys
sys.path[0:0] = [
    %s,
    ]
'''

script_template = script_header + '''\
%(relative_paths_setup)s

import sys
sys.path[0:0] = [
    %(path)s,
    ]

%(initialization)s
import %(module_name)s

if __name__ == '__main__':
    %(module_name)s.%(attrs)s(%(arguments)s)
'''

# These are used only by the older ``scripts`` function.

def _pyscript(path, dest, executable, rsetup):
    contents = py_script_template % dict(
        python=_safe_arg(executable),
        dash_S='',
        path=path,
        relative_paths_setup=rsetup,
        )
    return _write_script(dest, contents, 'interpreter')

py_script_template = script_header + '''\
%(relative_paths_setup)s

import sys

sys.path[0:0] = [
    %(path)s,
    ]

_interactive = True
if len(sys.argv) > 1:
    _options, _args = __import__("getopt").getopt(sys.argv[1:], 'ic:m:')
    _interactive = False
    for (_opt, _val) in _options:
        if _opt == '-i':
            _interactive = True
        elif _opt == '-c':
            exec _val
        elif _opt == '-m':
            sys.argv[1:] = _args
            _args = []
            __import__("runpy").run_module(
                 _val, {}, "__main__", alter_sys=True)

    if _args:
        sys.argv[:] = _args
        __file__ = _args[0]
        del _options, _args
        execfile(__file__)

if _interactive:
    del _interactive
    __import__("code").interact(banner="", local=globals())
'''

# These are used only by the newer ``sitepackage_safe_scripts`` function.

def _get_module_file(executable, name, silent=False):
    """Return a module's file path.

    - executable is a path to the desired Python executable.
    - name is the name of the (pure, not C) Python module.
    """
    cmd = [executable, "-Sc",
           "import imp; "
           "fp, path, desc = imp.find_module(%r); "
           "fp.close(); "
           "print path" % (name,)]
    env = os.environ.copy()
    # We need to make sure that PYTHONPATH, which will often be set to
    # include a custom buildout-generated site.py, is not set, or else
    # we will not get an accurate value for the "real" site.py and
    # sitecustomize.py.
    env.pop('PYTHONPATH', None)
    _proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    stdout, stderr = _proc.communicate();
    if _proc.returncode:
        if not silent:
            logger.info(
                'Could not find file for module %s:\n%s', name, stderr)
        return None
    # else: ...
    res = stdout.strip()
    if res.endswith('.pyc') or res.endswith('.pyo'):
        raise RuntimeError('Cannot find uncompiled version of %s' % (name,))
    if not os.path.exists(res):
        raise RuntimeError(
            'File does not exist for module %s:\n%s' % (name, res))
    return res

def _generate_sitecustomize(dest, executable, initialization='',
                            exec_sitecustomize=False):
    """Write a sitecustomize file with optional custom initialization.

    The created script will execute the underlying Python's
    sitecustomize if exec_sitecustomize is True.
    """
    sitecustomize_path = os.path.join(dest, 'sitecustomize.py')
    sitecustomize = open(sitecustomize_path, 'w')
    if initialization:
        sitecustomize.write(initialization + '\n')
    if exec_sitecustomize:
        real_sitecustomize_path = _get_module_file(
            executable, 'sitecustomize', silent=True)
        if real_sitecustomize_path:
            real_sitecustomize = open(real_sitecustomize_path, 'r')
            sitecustomize.write(
                '\n# The following is from\n# %s\n' %
                (real_sitecustomize_path,))
            sitecustomize.write(real_sitecustomize.read())
            real_sitecustomize.close()
    sitecustomize.close()
    return sitecustomize_path

def _generate_site(dest, working_set, executable, extra_paths=(),
                   include_site_packages=False, relative_paths=False):
    """Write a site.py file with eggs from working_set.

    extra_paths will be added to the path.  If include_site_packages is True,
    paths from the underlying Python will be added.
    """
    path = _get_path(working_set, extra_paths)
    site_path = os.path.join(dest, 'site.py')
    original_path_setup = preamble = ''
    if include_site_packages:
        stdlib, site_paths = _get_system_paths(executable)
        # We want to make sure that paths from site-packages, such as those
        # allowed by allowed_eggs_from_site_packages, always come last, or
        # else site-packages paths may include packages that mask the eggs we
        # really want.
        path = [p for p in path if p not in site_paths]
        # Now we set up the code we need.
        original_path_setup = original_path_snippet % (
            _format_paths((repr(p) for p in site_paths), 2),)
        distribution = working_set.find(
            pkg_resources.Requirement.parse('setuptools'))
        if distribution is not None:
            # We need to worry about namespace packages.
            if relative_paths:
                location = _relativitize(
                    distribution.location,
                    os.path.normcase(os.path.abspath(site_path)),
                    relative_paths)
            else:
                location = repr(distribution.location)
            preamble = namespace_include_site_packages_setup % (location,)
            original_path_setup = (
                addsitedir_namespace_originalpackages_snippet +
                original_path_setup)
        else:
            preamble = '\n    setuptools_path = None'
    egg_path_string, relative_preamble = _relative_path_and_setup(
        site_path, path, relative_paths, indent_level=2, omit_os_import=True)
    if relative_preamble:
        relative_preamble = '\n'.join(
            [(line and '    %s' % (line,) or line)
             for line in relative_preamble.split('\n')])
        preamble = relative_preamble + preamble
    addsitepackages_marker = 'def addsitepackages('
    enableusersite_marker = 'ENABLE_USER_SITE = '
    successful_rewrite = False
    real_site_path = _get_module_file(executable, 'site')
    real_site = open(real_site_path, 'r')
    site = open(site_path, 'w')
    try:
        for line in real_site.readlines():
            if line.startswith(enableusersite_marker):
                site.write(enableusersite_marker)
                site.write('False # buildout does not support user sites.\n')
            elif line.startswith(addsitepackages_marker):
                site.write(addsitepackages_script % (
                    preamble, egg_path_string, original_path_setup))
                site.write(line[len(addsitepackages_marker):])
                successful_rewrite = True
            else:
                site.write(line)
    finally:
        site.close()
        real_site.close()
    if not successful_rewrite:
        raise RuntimeError(
            'Buildout did not successfully rewrite %s to %s' %
            (real_site_path, site_path))
    return site_path

namespace_include_site_packages_setup = '''
    setuptools_path = %s
    sys.path.append(setuptools_path)
    known_paths.add(os.path.normcase(setuptools_path))
    import pkg_resources'''

addsitedir_namespace_originalpackages_snippet = '''
            pkg_resources.working_set.add_entry(sitedir)'''

original_path_snippet = '''
    sys.__egginsert = len(buildout_paths) # Support distribute.
    original_paths = [
        %s
        ]
    for path in original_paths:
        if path == setuptools_path or path not in known_paths:
            addsitedir(path, known_paths)'''

addsitepackages_script = '''\
def addsitepackages(known_paths):
    """Add site packages, as determined by zc.buildout.

    See original_addsitepackages, below, for the original version."""%s
    buildout_paths = [
        %s
        ]
    for path in buildout_paths:
        sitedir, sitedircase = makepath(path)
        if not sitedircase in known_paths and os.path.exists(sitedir):
            sys.path.append(sitedir)
            known_paths.add(sitedircase)%s
    return known_paths

def original_addsitepackages('''

def _generate_interpreter(name, dest, executable, site_py_dest,
                          relative_paths=False):
    """Write an interpreter script, using the site.py approach."""
    full_name = os.path.join(dest, name)
    site_py_dest_string, rpsetup = _relative_path_and_setup(
        full_name, [site_py_dest], relative_paths, omit_os_import=True)
    if rpsetup:
        rpsetup += "\n"
    if sys.platform == 'win32':
        windows_import = '\nimport subprocess'
        # os.exec* is a mess on Windows, particularly if the path
        # to the executable has spaces and the Python is using MSVCRT.
        # The standard fix is to surround the executable's path with quotes,
        # but that has been unreliable in testing.
        #
        # Here's a demonstration of the problem.  Given a Python
        # compiled with a MSVCRT-based compiler, such as the free Visual
        # C++ 2008 Express Edition, and an executable path with spaces
        # in it such as the below, we see the following.
        #
        # >>> import os
        # >>> p0 = 'C:\\Documents and Settings\\Administrator\\My Documents\\Downloads\\Python-2.6.4\\PCbuild\\python.exe'
        # >>> os.path.exists(p0)
        # True
        # >>> os.execv(p0, [])
        # Traceback (most recent call last):
        #  File "<stdin>", line 1, in <module>
        # OSError: [Errno 22] Invalid argument
        #
        # That seems like a standard problem.  The standard solution is
        # to quote the path (see, for instance
        # http://bugs.python.org/issue436259).  However, this solution,
        # and other variations, fail:
        #
        # >>> p1 = '"C:\\Documents and Settings\\Administrator\\My Documents\\Downloads\\Python-2.6.4\\PCbuild\\python.exe"'
        # >>> os.execv(p1, [])
        # Traceback (most recent call last):
        #   File "<stdin>", line 1, in <module>
        # OSError: [Errno 22] Invalid argument
        #
        # We simply use subprocess instead, since it handles everything
        # nicely, and the transparency of exec* (that is, not running,
        # perhaps unexpectedly, in a subprocess) is arguably not a
        # necessity, at least for many use cases.
        execute = 'subprocess.call(argv, env=environ)'
    else:
        windows_import = ''
        execute = 'os.execve(sys.executable, argv, environ)'
    contents = interpreter_template % dict(
        python=_safe_arg(executable),
        dash_S=' -S',
        site_dest=site_py_dest_string,
        relative_paths_setup=rpsetup,
        windows_import=windows_import,
        execute=execute,
        )
    return _write_script(full_name, contents, 'interpreter')

interpreter_template = script_header + '''
import os
import sys%(windows_import)s
%(relative_paths_setup)s
argv = [sys.executable] + sys.argv[1:]
environ = os.environ.copy()
path = %(site_dest)s
if environ.get('PYTHONPATH'):
    path = os.pathsep.join([path, environ['PYTHONPATH']])
environ['PYTHONPATH'] = path
%(execute)s
'''

# End of script generation code.
############################################################################

runsetup_template = """
import sys
sys.path.insert(0, %(setupdir)r)
sys.path.insert(0, %(setuptools)r)
import os, setuptools

__file__ = %(__file__)r

os.chdir(%(setupdir)r)
sys.argv[0] = %(setup)r
execfile(%(setup)r)
"""

def _log_requirement(ws, req):
    ws = list(ws)
    ws.sort()
    for dist in ws:
        if req in dist.requires():
            logger.debug("  required by %s." % dist)

def _fix_file_links(links):
    for link in links:
        if link.startswith('file://') and link[-1] != '/':
            if os.path.isdir(link[7:]):
                # work around excessive restriction in setuptools:
                link += '/'
        yield link

_final_parts = '*final-', '*final'
def _final_version(parsed_version):
    for part in parsed_version:
        if (part[:1] == '*') and (part not in _final_parts):
            return False
    return True

def redo_pyc(egg):
    if not os.path.isdir(egg):
        return
    for dirpath, dirnames, filenames in os.walk(egg):
        for filename in filenames:
            if not filename.endswith('.py'):
                continue
            filepath = os.path.join(dirpath, filename)
            if not (os.path.exists(filepath+'c')
                    or os.path.exists(filepath+'o')):
                # If it wasn't compiled, it may not be compilable
                continue

            # OK, it looks like we should try to compile.

            # Remove old files.
            for suffix in 'co':
                if os.path.exists(filepath+suffix):
                    os.remove(filepath+suffix)

            # Compile under current optimization
            try:
                py_compile.compile(filepath)
            except py_compile.PyCompileError:
                logger.warning("Couldn't compile %s", filepath)
            else:
                # Recompile under other optimization. :)
                args = [_safe_arg(sys.executable)]
                if __debug__:
                    args.append('-O')
                args.extend(['-m', 'py_compile', _safe_arg(filepath)])

                if is_jython:
                    subprocess.call([sys.executable, args])
                else:
                    os.spawnv(os.P_WAIT, sys.executable, args)


class UserError(Exception):
    pass


class IncompatibleVersionError(UserError):
    """A specified version is incompatible with a given requirement.
    """


class VersionConflict(UserError):

    def __init__(self, err, ws):
        ws = list(ws)
        ws.sort()
        self.err, self.ws = err, ws

    def __str__(self):
        existing_dist, req = self.err
        result = ["There is a version conflict.",
                  "We already have: %s" % existing_dist,
                  ]
        for dist in self.ws:
            if req in dist.requires():
                result.append("but %s requires %r." % (dist, str(req)))
        return '\n'.join(result)


class MissingDistribution(UserError):

    def __init__(self, req, ws):
        ws = list(ws)
        ws.sort()
        self.data = req, ws

    def __str__(self):
        req, ws = self.data
        return "Couldn't find a distribution for %r." % str(req)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import runpy
import shutil
import sys
import textwrap

import argparse

from config import Config


# Be a good neighbour.
if sys.platform == 'win32':
    GLOBAL_CONFIG_FILE = 'tipfy.cfg'
else:
    GLOBAL_CONFIG_FILE = '.tipfy.cfg'

MISSING_GAE_SDK_MSG = "%(script)r wasn't found. Add the App Engine SDK to " \
    "sys.path or configure sys.path in tipfy.cfg."


def get_unique_sequence(seq):
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]


def import_string(import_name, silent=False):
    """Imports an object based on a string. If *silent* is True the return
    value will be None if the import fails.

    Simplified version of the function with same name from `Werkzeug`_. We
    duplicate it here because this file should not depend on external packages.

    :param import_name:
        The dotted name for the object to import.
    :param silent:
        If True, import errors are ignored and None is returned instead.
    :returns:
        The imported object.
    """
    if isinstance(import_name, unicode):
        return import_name.encode('utf-8')

    try:
        if '.' in import_name:
            module, obj = import_name.rsplit('.', 1)
            return getattr(__import__(module, None, None, [obj]), obj)
        else:
            return __import__(import_name)
    except (ImportError, AttributeError):
        if not silent:
            raise


class Action(object):
    """Base interface for custom actions."""
    #: Action name.
    name = None

    #: ArgumentParser description.
    description = None

    #: ArgumentParser epilog.
    epilog = None

    def __init__(self, manager, name):
        self.manager = manager
        self.name = name

    def __call__(self, argv):
        raise NotImplementedError()

    def get_config_section(self):
        sections = ['tipfy:%s' % self.name]
        if self.manager.app:
            sections.insert(0, '%s:%s' % (self.manager.app, self.name))

        return sections

    def error(self, message, status=1):
        """Displays an error message and exits."""
        self.log(message)
        sys.exit(status)

    def log(self, message):
        """Displays a message."""
        sys.stderr.write(message + '\n')

    def run_hooks(self, import_names, args):
        """Executes a list of functions defined as strings. They are imported
        dynamically so their modules must be in sys.path. If any of the
        functions isn't found, none will be executed.
        """
        # Import all first.
        hooks = []
        for import_name in import_names:
            hook = import_string(import_name, True)
            if hook is None:
                self.error('Could not import %r.' % import_name)

            hooks.append(hook)

        # Execute all.
        for hook in hooks:
            hook(self.manager, args)


class CreateAppAction(Action):
    """Creates a directory for a new tipfy app."""
    description = 'Creates a directory for a new App Engine app.'

    def get_parser(self):
        parser = argparse.ArgumentParser(description=self.description)
        parser.add_argument('app_dir', help='App directory '
            'or directories.', nargs='+')
        parser.add_argument('-t', '--template', dest='template',
            help='App template, copied to the new project directory. '
            'If not defined, the default app skeleton is used.')
        return parser

    def __call__(self, argv):
        manager = self.manager
        section = self.get_config_section()
        parser = self.get_parser()
        args = parser.parse_args(args=argv)

        template_dir = args.template
        if not template_dir:
            # Try getting the template set in config.
            template_dir = manager.config.get(section, 'appengine_stub')

        if not template_dir:
            # Use default template.
            curr_dir = os.path.dirname(os.path.realpath(__file__))
            template_dir = os.path.join(curr_dir, 'stubs', 'appengine')

        template_dir = os.path.abspath(template_dir)
        if not os.path.exists(template_dir):
            self.error('Template directory not found: %r.' % template_dir)

        for app_dir in args.app_dir:
            app_dir = os.path.abspath(app_dir)
            self.create_app(app_dir, template_dir)

    def create_app(self, app_dir, template_dir):
        if os.path.exists(app_dir):
            self.error('Project directory already exists: %r.' % app_dir)

        shutil.copytree(template_dir, app_dir)


class GaeSdkAction(Action):
    """This is just a wrapper for tools found in the Google App Engine SDK.
    It delegates all arguments to the SDK script and no additional arguments
    are parsed.
    """
    def __call__(self, argv):
        sys.argv = [self.name] + argv
        try:
            runpy.run_module(self.name, run_name='__main__', alter_sys=True)
        except ImportError:
            self.error(MISSING_GAE_SDK_MSG % dict(script=self.name))


class GaeSdkExtendedAction(Action):
    """Base class for actions that wrap the App Engine SDK scripts to make
    them configurable or to add before/after hooks. It accepts all options
    from the correspondent SDK scripts, but they can be configured in
    tipfy.cfg.
    """
    options = []

    def get_base_gae_argv(self):
        raise NotImplementedError()

    def get_getopt_options(self):
        for option in self.options:
            if isinstance(option, tuple):
                long_option, short_option = option
            else:
                long_option = option
                short_option = None

            is_bool = not long_option.endswith('=')
            long_option = long_option.strip('=')

            yield long_option, short_option, is_bool

    def get_parser_from_getopt_options(self):
        manager = self.manager
        section = self.get_config_section()

        usage = '%%(prog)s %(action)s [--config CONFIG] [--app APP] ' \
            '[options]' % dict(action=self.name)

        parser = argparse.ArgumentParser(
            description=self.description,
            usage=usage,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            add_help=False
        )

        for long_option, short_option, is_bool in self.get_getopt_options():
            args = ['--%s' % long_option]
            kwargs = {}

            if short_option:
                args.append('-%s' % short_option)

            if is_bool:
                kwargs['action'] = 'store_true'
                kwargs['default'] = manager.config.getboolean(section,
                    long_option)
            else:
                kwargs['default'] = manager.config.get(section, long_option)

            parser.add_argument(*args, **kwargs)

        # Add app path.
        app_path = manager.config.get(section, 'path', '')
        parser.add_argument('app', nargs='?', default=app_path)

        return parser

    def get_gae_argv(self, argv):
        manager = self.manager
        parser = self.get_parser_from_getopt_options()
        args, extras = parser.parse_known_args(args=argv)

        if args.help:
            parser.print_help()
            sys.exit(1)

        gae_argv = self.get_base_gae_argv()
        for long_option, short_option, is_bool in self.get_getopt_options():
            value = getattr(args, long_option)
            if value is not None:
                if is_bool and value:
                    value = '--%s' % long_option
                elif not is_bool:
                    value = '--%s=%s' % (long_option, value)

                if value:
                    gae_argv.append(value)

        # Add app path.
        gae_argv.append(os.path.abspath(args.app))

        return gae_argv


class GaeRunserverAction(GaeSdkExtendedAction):
    """
    A convenient wrapper for "dev_appserver": starts the Google App Engine
    development server using before and after hooks and allowing configurable
    defaults.

    Default values for each option can be defined in tipfy.cfg in the
    "tipfy:runserver" section or for the current app, sufixed by ":runserver".
    A special variable "app" is replaced by the value from the "--app"
    argument:

        [tipfy]
        path = /path/to/%(app)s

        [tipfy:runserver]
        debug = true
        datastore_path = /path/to/%(app)s.datastore

        [my_app:runserver]
        port = 8081

    In this case, executing:

        tipfy runserver --app=my_app

    ...will expand to:

        dev_appserver --datastore_path=/path/to/my_app.datastore --debug --port=8081 /path/to/my_app

    Define in "before" and "after" a list of functions to run before and after
    the server executes. These functions are imported so they must be in
    sys.path. For example:

        [tipfy:runserver]
        before =
            hooks.before_runserver_1
            hooks.before_runserver_2

        after =
            hooks.after_runserver_1
            hooks.after_runserver_2

    Then define in the module "hooks.py" some functions to be executed:

        def before_runserver_1(manager, args):
            print 'before_runserver_1!'

        def after_runserver_1(manager, args):
            print 'after_runserver_1!'

        # ...

    Use "tipfy dev_appserver --help" for a description of each option.
    """
    description = textwrap.dedent(__doc__)

    # All options from dev_appserver in a modified getopt style.
    options = [
        ('address=', 'a'),
        'admin_console_server=',
        'admin_console_host=',
        'allow_skipped_files',
        'auth_domain=',
        ('clear_datastore', 'c'),
        'blobstore_path=',
        'datastore_path=',
        'use_sqlite',
        ('debug', 'd'),
        'debug_imports',
        'enable_sendmail',
        'disable_static_caching',
        'show_mail_body',
        ('help', 'h'),
        'history_path=',
        'mysql_host=',
        'mysql_port=',
        'mysql_user=',
        'mysql_password=',
        ('port=', 'p'),
        'require_indexes',
        'smtp_host=',
        'smtp_password=',
        'smtp_port=',
        'smtp_user=',
        'disable_task_running',
        'task_retry_seconds=',
        'template_dir=',
        'trusted',
    ]

    def get_base_gae_argv(self):
        return ['dev_appserver']

    def __call__(self, argv):
        manager = self.manager
        section = self.get_config_section()
        before_hooks = manager.config.getlist(section, 'before', [])
        after_hooks = manager.config.getlist(section, 'after', [])

        # Assemble arguments.
        sys.argv = self.get_gae_argv(argv)

        # Execute before scripts.
        self.run_hooks(before_hooks, argv)

        script = 'dev_appserver'
        try:
            self.log('Executing: %s' % ' '.join(sys.argv))
            runpy.run_module(script, run_name='__main__', alter_sys=True)
        except ImportError:
            self.error(MISSING_GAE_SDK_MSG % dict(script=script))
        finally:
            # Execute after scripts.
            self.run_hooks(after_hooks, argv)


class GaeDeployAction(GaeSdkExtendedAction):
    """
    A convenient wrapper for "appcfg update": deploys to Google App Engine
    using before and after hooks and allowing configurable defaults.

    Default values for each option can be defined in tipfy.cfg in the
    "tipfy:deploy" section or for the current app, sufixed by ":deploy".
    A special variable "app" is replaced by the value from the "--app"
    argument:

        [tipfy]
        path = /path/to/%(app)s

        [tipfy:deploy]
        verbose = true

        [my_app:deploy]
        email = user@gmail.com
        no_cookies = true

    In this case, executing:

        tipfy deploy --app=my_app

    ...will expand to:

        appcfg update --verbose --email=user@gmail.com --no_cookies /path/to/my_app

    Define in "before" and "after" a list of functions to run before and after
    deployment. These functions are imported so they must be in sys.path.
    For example:

        [tipfy:deploy]
        before =
            hooks.before_deploy_1
            hooks.before_deploy_2

        after =
            hooks.after_deploy_1
            hooks.after_deploy_2

    Then define in the module "hooks.py" some functions to be executed:

        def before_deploy_1(manager, args):
            print 'before_deploy_1!'

        def after_deploy_1(manager, args):
            print 'after_deploy_1!'

        # ...

    Use "tipfy appcfg update --help" for a description of each option.
    """
    description = textwrap.dedent(__doc__)

    # All options from appcfg update in a modified getopt style.
    options = [
        ('help', 'h'),
        ('quiet', 'q'),
        ('verbose', 'v'),
        'noisy',
        ('server=', 's'),
        'insecure',
        ('email=', 'e'),
        ('host=', 'H'),
        'no_cookies',
        'passin',
        ('application=', 'A'),
        ('version=', 'V'),
        ('max_size=', 'S'),
        'no_precompilation',
    ]

    def get_base_gae_argv(self):
        return ['appcfg', 'update']

    def __call__(self, argv):
        manager = self.manager
        section = self.get_config_section()
        before_hooks = manager.config.getlist(section, 'before', [])
        after_hooks = manager.config.getlist(section, 'after', [])

        # Assemble arguments.
        sys.argv = self.get_gae_argv(argv)

        # Execute before scripts.
        self.run_hooks(before_hooks, argv)

        script = 'appcfg'
        try:
            self.log('Executing: %s' % ' '.join(sys.argv))
            runpy.run_module(script, run_name='__main__', alter_sys=True)
        except ImportError:
            self.error(MISSING_GAE_SDK_MSG % dict(script=script))
        finally:
            # Execute after scripts.
            self.run_hooks(after_hooks, argv)


class BuildAction(Action):
    description = 'Installs packages in the app directory.'

    cache_path = 'var/cache/packages'
    pin_file = 'var/%(app)s_pinned_versions.txt'

    def get_parser(self):
        manager = self.manager
        # XXX cache option
        # XXX symlinks option
        section = self.get_config_section()

        parser = argparse.ArgumentParser(description=self.description)

        parser.add_argument('--from_pin_file',
            help='Install package versions defined in this pin file.',
            default=manager.config.get(section, 'from_pin_file')
        )
        parser.add_argument('--pin_file',
            help='Name of the file to save pinned versions.',
            default=manager.config.get(section, 'pin_file', self.pin_file)
        )
        parser.add_argument('--no_pin_file',
            help="Don't create a pin file after installing the packages.",
            action='store_true',
            default=manager.config.getboolean(section, 'no_pin_file', False)
        )

        parser.add_argument('--cache_path',
            help='Directory to store package cache.',
            default=manager.config.get(section, 'cache_path', self.cache_path)
        )
        parser.add_argument('--no_cache',
            help="Don't use package cache.",
            action='store_true',
            default=manager.config.getboolean(section, 'no_cache', False)
        )

        parser.add_argument('--no_symlink',
            help="Move packages to app directory instead of creating "
                "symlinks. Always active on Windows.",
            action='store_true',
            default=manager.config.getboolean(section, 'no_symlink', False)
        )

        return parser

    def __call__(self, argv):
        manager = self.manager
        if not manager.app:
            self.error('Missing app. Use --app=APP_NAME to define the current '
                'app.')

        parser = self.get_parser()
        args = parser.parse_args(args=argv)

        if args.from_pin_file:
            packages_to_install = self.read_pin_file(args.from_pin_file)
        else:
            packages_to_install = manager.config.getlist(section, 'packages',
                [])

        if not packages_to_install:
            self.error('Missing list of packages to install.')

        if sys.platform == 'win32':
            args.no_symlink = True

        packages = []

        if not args.no_pin_file:
            pin_file = args.pin_file % dict(app=manager.app)
            self.save_pin_file(pin_file, packages)

    def save_pin_file(self, pin_file, packages):
        # XXX catch errors
        f = open(pin_file, 'w+')
        f.write('\n'.join(packages))
        f.close()

    def read_pin_file(self, pin_file):
        # XXX catch errors
        f = open(pin_file, 'r')
        contents = f.read()
        f.close()

        packages = [line.strip() for line in contents.splitlines()]
        return [line for line in packages if line]

    def _get_package_finder(self):
        # XXX make mirrors configurable
        from pip.index import PackageFinder

        find_links = []
        use_mirrors = False
        mirrors = []
        index_urls = ['http://pypi.python.org/simple/']

        return PackageFinder(find_links=find_links, index_urls=index_urls,
            use_mirrors=use_mirrors, mirrors=mirrors)



class InstallAppengineSdkAction(Action):
    """Not implemented yet."""
    description = 'Downloads and unzips the App Engine SDK.'

    def get_parser(self):
        parser = argparse.ArgumentParser(description=self.description)
        parser.add_argument('--version', '-v', help='SDK version. '
            'If not defined, downloads the latest stable one.')
        return parser

    def __call__(self, argv):
        manager = self.manager
        parser = self.get_parser()
        raise NotImplementedError()


class TestAction(Action):
    """Testing stuff."""
    def __call__(self, argv):
        manager = self.manager
        print manager.app


class TipfyManager(object):
    description = 'Tipfy Management Utilities.'
    epilog = 'Use "%(prog)s action --help" for help on specific actions.'

    # XXX Allow users to hook in custom actions.
    actions = {
        # Wrappers for App Engine SDK tools.
        'appcfg':           GaeSdkAction,
        'bulkload_client':  GaeSdkAction,
        'bulkloader':       GaeSdkAction,
        'dev_appserver':    GaeSdkAction,
        'remote_api_shell': GaeSdkAction,
        # For now these are App Engine specific.
        'runserver':        GaeRunserverAction,
        'deploy':           GaeDeployAction,
        # Extra ones.
        #'install_gae_sdk': InstallAppengineSdkAction(),
        'create_app':       CreateAppAction,
        'build':            BuildAction,
        'test':             TestAction,
    }

    def __init__(self):
        pass

    def __call__(self, argv):
        parser = self.get_parser()
        args, extras = parser.parse_known_args(args=argv)

        # Load configuration.
        self.parse_config(args.config)

        # Load config fom a specific app, if defined, or use default one.
        self.app = args.app or self.config.get('tipfy', 'app')

        # Fallback to the tipfy section.
        self.config_section = ['tipfy']
        if self.app:
            self.config_section.insert(0, self.app)

        # If app is set, an 'app' value can be used in expansions.
        if self.app:
            self.config.set('DEFAULT', 'app', self.app)

        # Prepend configured paths to sys.path, if any.
        sys.path[:0] = self.config.getlist(self.config_section, 'sys.path', [])

        if args.action not in self.actions:
            # Unknown action or --help.
            return parser.print_help()

        if args.help:
            # Delegate help to action.
            extras.append('--help')

        return self.actions[args.action](self, args.action)(extras)

    def get_parser(self):
        actions = ', '.join(sorted(self.actions.keys()))
        parser = argparse.ArgumentParser(description=self.description,
            epilog=self.epilog, add_help=False)
        parser.add_argument('action', help='Action to perform. '
            'Available actions are: %s.' % actions, nargs='?')
        parser.add_argument('--config', default='tipfy.cfg',
            help='Configuration file. If not provided, uses tipfy.cfg from '
            'the current directory.')
        parser.add_argument('--app', help='App configuration to use.')
        parser.add_argument('-h', '--help', help='Show this help message '
            'and exit.', action='store_true')
        return parser

    def parse_config(self, config_file):
        """Load configuration. If files are not specified, try 'tipfy.cfg'
        in the current dir.
        """
        self.config_files = {
            'global': os.path.realpath(os.path.join(os.path.expanduser('~'),
                GLOBAL_CONFIG_FILE)),
            'project': os.path.realpath(os.path.abspath(config_file)),
        }

        self.config = Config()
        self.config_loaded = self.config.read([
            self.config_files['global'],
            self.config_files['project'],
        ])


def main():
    manager = TipfyManager()
    manager(sys.argv[1:])


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = newaction
import logging


class InstallPackagesAction(Action):
    def __init__(self, manager, name):
        super(InstallPackagesAction, self).__init__(manager, name)

        self.logger = logging.getLogger(name)

        section = self.get_config_section()

        get = manager.config.get
        getboolean = manager.config.getboolean
        getlist = manager.config.getlist

        self.opt_packages = getlist(section, 'packages', [])
        self.opt_offline = getboolean(section, 'offline', False)

        self.opt_executable = get(section, 'executable')
        self.opt_eggs_dir = get(section, 'eggs-directory')
        self.opt_develop_eggs_dir = get(section, 'develop-eggs-directory')

        # Set list of globs and packages to be ignored.
        self.opt_ignore_globs = getlist(section, 'ignore-globs', [])
        self.opt_ignore_packages = getlist(section, 'ignore-packages', [])

        self.opt_delete_safe = getboolean(section, 'delete-safe', True)

        self.opt_use_zip = getboolean(section, 'use-zipimport', False)
        if self.opt_use_zip:
            self.lib_path += '.zip'

    def __init__(self, buildout, name, opts):
        # Set a logger with the section name.


        # Unzip eggs by default or we can't use some.
        opts.setdefault('unzip', 'true')


        self.parts_dir = buildout['buildout']['parts-directory']
        self.temp_dir = os.path.join(self.parts_dir, 'temp')

        lib_dir = opts.get('lib-directory', 'distlib')
        self.lib_path = os.path.abspath(lib_dir)






        opts.setdefault('eggs', '')
        super(Recipe, self).__init__(buildout, name, opts)

    def working_set(self, extra=()):
        """Separate method to just get the working set

        This is intended for reuse by similar recipes.
        """
        options = self.options
        b_options = self.buildout['buildout']



        packages = self.opt_packages[:]
        orig_packages = packages[:]
        packages.extend(extra)

        if self.opt_offline:
            ws = easy_install.working_set(
                     packages,
                     self.opt_executable,
                     [
                         self.opt_develop_eggs_dir,
                         self.opt_eggs_dir
                     ],
                     include_site_packages=self.include_site_packages,
                     allowed_eggs_from_site_packages=self.allowed_eggs,
                )
        else:
            kw = {}
            if 'unzip' in options:
                kw['always_unzip'] = options.query_bool('unzip', None)
            ws = zc.buildout.easy_install.install(
                     packages,
                     self.opt_eggs_dir,
                     links=self.links,
                     index=self.index,
                     executable=self.opt_executable,
                     path=[self.opt_develop_eggs_dir],
                     newest=b_options.get('newest') == 'true',
                     include_site_packages=self.include_site_packages,
                     allowed_eggs_from_site_packages=self.allowed_eggs,
                     allow_hosts=self.allow_hosts,
                     **kw
                 )

        return orig_packages, ws

    def install(self):
        # Get all installed packages.
        reqs, ws = self.working_set()
        paths = self.get_package_paths(ws)

        # For now we only support installing them in the app dir.
        # In the future we may support installing libraries in the parts dir.
        self.install_in_app_dir(paths)

        return super(Recipe, self).install()

    def install_in_app_dir(self, paths):
        # Delete old libs.
        self.delete_libs()

        if self.opt_use_zip:
            # Create temporary directory for the zip files.
            tmp_dir = os.path.join(tempfile.gettempdir(), uuid.uuid4().hex)
        else:
            tmp_dir = self.lib_path

        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)

        # Copy all files.
        for name, src in paths:
            if name in self.opt_ignore_packages:
                # This package or module must be ignored.
                continue

            dst = os.path.join(tmp_dir, name)
            if not os.path.isdir(src):
                # Try single files listed as modules.
                src += '.py'
                dst += '.py'
                if not os.path.isfile(src) or os.path.isfile(dst):
                    continue

            self.logger.info('Copying %r...' % src)

            copytree(src, dst, os.path.dirname(src) + os.sep,
                ignore=ignore_patterns(*self.opt_ignore_globs),
                logger=self.logger)

        # Save README.
        f = open(os.path.join(tmp_dir, 'README.txt'), 'w')
        f.write(LIB_README)
        f.close()

        if self.opt_use_zip:
            # Zip file and remove temporary dir.
            zipdir(tmp_dir, self.lib_path)
            if os.path.isdir(tmp_dir):
                shutil.rmtree(tmp_dir)

    def get_package_paths(self, ws):
        """Returns the list of package paths to be copied."""
        pkgs = []
        for path in ws.entries:
            lib_paths = self.get_lib_paths(path)
            if not lib_paths:
                self.logger.info('Library not installed: missing egg info for '
                    '%r.' % path)
                continue

            for lib_path in lib_paths:
                pkgs.append((lib_path, os.path.join(path, lib_path)))

        return pkgs

    def get_top_level_libs(self, egg_path):
        top_path = os.path.join(egg_path, 'top_level.txt')
        if not os.path.isfile(top_path):
            return None

        f = open(top_path, 'r')
        libs = f.read().strip()
        f.close()

        # One lib per line.
        return [l.strip() for l in libs.splitlines() if l.strip()]

    def get_lib_paths(self, path):
        """Returns the 'EGG-INFO' or '.egg-info' directory."""
        egg_path = os.path.join(path, 'EGG-INFO')
        if os.path.isdir(egg_path):
            # Unzipped egg metadata.
            return self.get_top_level_libs(egg_path)

        if os.path.isfile(path):
            # Zipped egg? Should we try to unpack it?
            # unpack_archive(path, self.opt_eggs_dir)
            return None

        # Last try: develop eggs.
        elif os.path.isdir(path):
            files = os.listdir(path)
            for filename in files:
                if filename.endswith('.egg-info'):
                    egg_path = os.path.join(path, filename)
                    return self.get_top_level_libs(egg_path)

    def delete_libs(self):
        """If the `delete-safe` option is set to true, move the old libraries
        directory to a temporary directory inside the parts dir instead of
        deleting it.
        """
        if not os.path.exists(self.lib_path):
            # Nothing to delete, so it is safe.
            return

        if self.opt_delete_safe is True:
            # Move directory or zip to temporary backup directory.
            if not os.path.exists(self.temp_dir):
                os.makedirs(self.temp_dir)

            date = datetime.datetime.now().strftime('_%Y_%m_%d_%H_%M_%S')
            filename = os.path.basename(self.lib_path.rstrip(os.sep))
            if self.opt_use_zip:
                filename = filename[:-4] + date + '.zip'
            else:
                filename += date

            dst = os.path.join(self.temp_dir, filename)
            shutil.move(self.lib_path, dst)
            self.logger.info('Saved libraries backup in %r.' % dst)
        else:
            # Simply delete the directory or zip.
            if self.opt_use_zip:
                os.remove(self.lib_path)
                self.logger.info('Removed lib-zip %r.' % self.lib_path)
            else:
                # Delete the directory.
                shutil.rmtree(self.lib_path)
                self.logger.info('Removed lib-directory %r.' % self.lib_path)

########NEW FILE########
__FILENAME__ = path
""" path.py - An object representing a path to a file or directory.

Example:

from path import path
d = path('/home/guido/bin')
for f in d.files('*.py'):
    f.chmod(0755)

This module requires Python 2.2 or later.


URL:     http://www.jorendorff.com/articles/python/path
Author:  Jason Orendorff <jason.orendorff\x40gmail\x2ecom> (and others - see the url!)
Date:    9 Mar 2007
"""


# TODO
#   - Tree-walking functions don't avoid symlink loops.  Matt Harrison
#     sent me a patch for this.
#   - Bug in write_text().  It doesn't support Universal newline mode.
#   - Better error message in listdir() when self isn't a
#     directory. (On Windows, the error message really sucks.)
#   - Make sure everything has a good docstring.
#   - Add methods for regex find and replace.
#   - guess_content_type() method?
#   - Perhaps support arguments to touch().

from __future__ import generators

import sys, warnings, os, fnmatch, glob, shutil, codecs

__version__ = '2.2'
__all__ = ['path']

# Avoid the deprecation warning.
try:
    import hashlib
    md5 = hashlib.md5
except ImportError:
    import md5

# Platform-specific support for path.owner
if os.name == 'nt':
    try:
        import win32security
    except ImportError:
        win32security = None
else:
    try:
        import pwd
    except ImportError:
        pwd = None

# Pre-2.3 support.  Are unicode filenames supported?
_base = str
_getcwd = os.getcwd
try:
    if os.path.supports_unicode_filenames:
        _base = unicode
        _getcwd = os.getcwdu
except AttributeError:
    pass

# Pre-2.3 workaround for booleans
try:
    True, False
except NameError:
    True, False = 1, 0

# Pre-2.3 workaround for basestring.
try:
    basestring
except NameError:
    basestring = (str, unicode)

# Universal newline support
_textmode = 'r'
if hasattr(file, 'newlines'):
    _textmode = 'U'


class TreeWalkWarning(Warning):
    pass

class path(_base):
    """ Represents a filesystem path.

    For documentation on individual methods, consult their
    counterparts in os.path.
    """

    # --- Special Python methods.

    def __repr__(self):
        return 'path(%s)' % _base.__repr__(self)

    # Adding a path and a string yields a path.
    def __add__(self, more):
        try:
            resultStr = _base.__add__(self, more)
        except TypeError:  #Python bug
            resultStr = NotImplemented
        if resultStr is NotImplemented:
            return resultStr
        return self.__class__(resultStr)

    def __radd__(self, other):
        if isinstance(other, basestring):
            return self.__class__(other.__add__(self))
        else:
            return NotImplemented

    # The / operator joins paths.
    def __div__(self, rel):
        """ fp.__div__(rel) == fp / rel == fp.joinpath(rel)

        Join two path components, adding a separator character if
        needed.
        """
        return self.__class__(os.path.join(self, rel))

    # Make the / operator work even when true division is enabled.
    __truediv__ = __div__

    def getcwd(cls):
        """ Return the current working directory as a path object. """
        return cls(_getcwd())
    getcwd = classmethod(getcwd)


    # --- Operations on path strings.

    isabs = os.path.isabs
    def abspath(self):       return self.__class__(os.path.abspath(self))
    def normcase(self):      return self.__class__(os.path.normcase(self))
    def normpath(self):      return self.__class__(os.path.normpath(self))
    def realpath(self):      return self.__class__(os.path.realpath(self))
    def expanduser(self):    return self.__class__(os.path.expanduser(self))
    def expandvars(self):    return self.__class__(os.path.expandvars(self))
    def dirname(self):       return self.__class__(os.path.dirname(self))
    basename = os.path.basename

    def expand(self):
        """ Clean up a filename by calling expandvars(),
        expanduser(), and normpath() on it.

        This is commonly everything needed to clean up a filename
        read from a configuration file, for example.
        """
        return self.expandvars().expanduser().normpath()

    def _get_namebase(self):
        base, ext = os.path.splitext(self.name)
        return base

    def _get_ext(self):
        f, ext = os.path.splitext(_base(self))
        return ext

    def _get_drive(self):
        drive, r = os.path.splitdrive(self)
        return self.__class__(drive)

    parent = property(
        dirname, None, None,
        """ This path's parent directory, as a new path object.

        For example, path('/usr/local/lib/libpython.so').parent == path('/usr/local/lib')
        """)

    name = property(
        basename, None, None,
        """ The name of this file or directory without the full path.

        For example, path('/usr/local/lib/libpython.so').name == 'libpython.so'
        """)

    namebase = property(
        _get_namebase, None, None,
        """ The same as path.name, but with one file extension stripped off.

        For example, path('/home/guido/python.tar.gz').name     == 'python.tar.gz',
        but          path('/home/guido/python.tar.gz').namebase == 'python.tar'
        """)

    ext = property(
        _get_ext, None, None,
        """ The file extension, for example '.py'. """)

    drive = property(
        _get_drive, None, None,
        """ The drive specifier, for example 'C:'.
        This is always empty on systems that don't use drive specifiers.
        """)

    def splitpath(self):
        """ p.splitpath() -> Return (p.parent, p.name). """
        parent, child = os.path.split(self)
        return self.__class__(parent), child

    def splitdrive(self):
        """ p.splitdrive() -> Return (p.drive, <the rest of p>).

        Split the drive specifier from this path.  If there is
        no drive specifier, p.drive is empty, so the return value
        is simply (path(''), p).  This is always the case on Unix.
        """
        drive, rel = os.path.splitdrive(self)
        return self.__class__(drive), rel

    def splitext(self):
        """ p.splitext() -> Return (p.stripext(), p.ext).

        Split the filename extension from this path and return
        the two parts.  Either part may be empty.

        The extension is everything from '.' to the end of the
        last path segment.  This has the property that if
        (a, b) == p.splitext(), then a + b == p.
        """
        filename, ext = os.path.splitext(self)
        return self.__class__(filename), ext

    def stripext(self):
        """ p.stripext() -> Remove one file extension from the path.

        For example, path('/home/guido/python.tar.gz').stripext()
        returns path('/home/guido/python.tar').
        """
        return self.splitext()[0]

    if hasattr(os.path, 'splitunc'):
        def splitunc(self):
            unc, rest = os.path.splitunc(self)
            return self.__class__(unc), rest

        def _get_uncshare(self):
            unc, r = os.path.splitunc(self)
            return self.__class__(unc)

        uncshare = property(
            _get_uncshare, None, None,
            """ The UNC mount point for this path.
            This is empty for paths on local drives. """)

    def joinpath(self, *args):
        """ Join two or more path components, adding a separator
        character (os.sep) if needed.  Returns a new path
        object.
        """
        return self.__class__(os.path.join(self, *args))

    def splitall(self):
        r""" Return a list of the path components in this path.

        The first item in the list will be a path.  Its value will be
        either os.curdir, os.pardir, empty, or the root directory of
        this path (for example, '/' or 'C:\\').  The other items in
        the list will be strings.

        path.path.joinpath(*result) will yield the original path.
        """
        parts = []
        loc = self
        while loc != os.curdir and loc != os.pardir:
            prev = loc
            loc, child = prev.splitpath()
            if loc == prev:
                break
            parts.append(child)
        parts.append(loc)
        parts.reverse()
        return parts

    def relpath(self):
        """ Return this path as a relative path,
        based from the current working directory.
        """
        cwd = self.__class__(os.getcwd())
        return cwd.relpathto(self)

    def relpathto(self, dest):
        """ Return a relative path from self to dest.

        If there is no relative path from self to dest, for example if
        they reside on different drives in Windows, then this returns
        dest.abspath().
        """
        origin = self.abspath()
        dest = self.__class__(dest).abspath()

        orig_list = origin.normcase().splitall()
        # Don't normcase dest!  We want to preserve the case.
        dest_list = dest.splitall()

        if orig_list[0] != os.path.normcase(dest_list[0]):
            # Can't get here from there.
            return dest

        # Find the location where the two paths start to differ.
        i = 0
        for start_seg, dest_seg in zip(orig_list, dest_list):
            if start_seg != os.path.normcase(dest_seg):
                break
            i += 1

        # Now i is the point where the two paths diverge.
        # Need a certain number of "os.pardir"s to work up
        # from the origin to the point of divergence.
        segments = [os.pardir] * (len(orig_list) - i)
        # Need to add the diverging part of dest_list.
        segments += dest_list[i:]
        if len(segments) == 0:
            # If they happen to be identical, use os.curdir.
            relpath = os.curdir
        else:
            relpath = os.path.join(*segments)
        return self.__class__(relpath)

    # --- Listing, searching, walking, and matching

    def listdir(self, pattern=None):
        """ D.listdir() -> List of items in this directory.

        Use D.files() or D.dirs() instead if you want a listing
        of just files or just subdirectories.

        The elements of the list are path objects.

        With the optional 'pattern' argument, this only lists
        items whose names match the given pattern.
        """
        names = os.listdir(self)
        if pattern is not None:
            names = fnmatch.filter(names, pattern)
        return [self / child for child in names]

    def dirs(self, pattern=None):
        """ D.dirs() -> List of this directory's subdirectories.

        The elements of the list are path objects.
        This does not walk recursively into subdirectories
        (but see path.walkdirs).

        With the optional 'pattern' argument, this only lists
        directories whose names match the given pattern.  For
        example, d.dirs('build-*').
        """
        return [p for p in self.listdir(pattern) if p.isdir()]

    def files(self, pattern=None):
        """ D.files() -> List of the files in this directory.

        The elements of the list are path objects.
        This does not walk into subdirectories (see path.walkfiles).

        With the optional 'pattern' argument, this only lists files
        whose names match the given pattern.  For example,
        d.files('*.pyc').
        """

        return [p for p in self.listdir(pattern) if p.isfile()]

    def walk(self, pattern=None, errors='strict'):
        """ D.walk() -> iterator over files and subdirs, recursively.

        The iterator yields path objects naming each child item of
        this directory and its descendants.  This requires that
        D.isdir().

        This performs a depth-first traversal of the directory tree.
        Each directory is returned just before all its children.

        The errors= keyword argument controls behavior when an
        error occurs.  The default is 'strict', which causes an
        exception.  The other allowed values are 'warn', which
        reports the error via warnings.warn(), and 'ignore'.
        """
        if errors not in ('strict', 'warn', 'ignore'):
            raise ValueError("invalid errors parameter")

        try:
            childList = self.listdir()
        except Exception:
            if errors == 'ignore':
                return
            elif errors == 'warn':
                warnings.warn(
                    "Unable to list directory '%s': %s"
                    % (self, sys.exc_info()[1]),
                    TreeWalkWarning)
                return
            else:
                raise

        for child in childList:
            if pattern is None or child.fnmatch(pattern):
                yield child
            try:
                isdir = child.isdir()
            except Exception:
                if errors == 'ignore':
                    isdir = False
                elif errors == 'warn':
                    warnings.warn(
                        "Unable to access '%s': %s"
                        % (child, sys.exc_info()[1]),
                        TreeWalkWarning)
                    isdir = False
                else:
                    raise

            if isdir:
                for item in child.walk(pattern, errors):
                    yield item

    def walkdirs(self, pattern=None, errors='strict'):
        """ D.walkdirs() -> iterator over subdirs, recursively.

        With the optional 'pattern' argument, this yields only
        directories whose names match the given pattern.  For
        example, mydir.walkdirs('*test') yields only directories
        with names ending in 'test'.

        The errors= keyword argument controls behavior when an
        error occurs.  The default is 'strict', which causes an
        exception.  The other allowed values are 'warn', which
        reports the error via warnings.warn(), and 'ignore'.
        """
        if errors not in ('strict', 'warn', 'ignore'):
            raise ValueError("invalid errors parameter")

        try:
            dirs = self.dirs()
        except Exception:
            if errors == 'ignore':
                return
            elif errors == 'warn':
                warnings.warn(
                    "Unable to list directory '%s': %s"
                    % (self, sys.exc_info()[1]),
                    TreeWalkWarning)
                return
            else:
                raise

        for child in dirs:
            if pattern is None or child.fnmatch(pattern):
                yield child
            for subsubdir in child.walkdirs(pattern, errors):
                yield subsubdir

    def walkfiles(self, pattern=None, errors='strict'):
        """ D.walkfiles() -> iterator over files in D, recursively.

        The optional argument, pattern, limits the results to files
        with names that match the pattern.  For example,
        mydir.walkfiles('*.tmp') yields only files with the .tmp
        extension.
        """
        if errors not in ('strict', 'warn', 'ignore'):
            raise ValueError("invalid errors parameter")

        try:
            childList = self.listdir()
        except Exception:
            if errors == 'ignore':
                return
            elif errors == 'warn':
                warnings.warn(
                    "Unable to list directory '%s': %s"
                    % (self, sys.exc_info()[1]),
                    TreeWalkWarning)
                return
            else:
                raise

        for child in childList:
            try:
                isfile = child.isfile()
                isdir = not isfile and child.isdir()
            except:
                if errors == 'ignore':
                    continue
                elif errors == 'warn':
                    warnings.warn(
                        "Unable to access '%s': %s"
                        % (self, sys.exc_info()[1]),
                        TreeWalkWarning)
                    continue
                else:
                    raise

            if isfile:
                if pattern is None or child.fnmatch(pattern):
                    yield child
            elif isdir:
                for f in child.walkfiles(pattern, errors):
                    yield f

    def fnmatch(self, pattern):
        """ Return True if self.name matches the given pattern.

        pattern - A filename pattern with wildcards,
            for example '*.py'.
        """
        return fnmatch.fnmatch(self.name, pattern)

    def glob(self, pattern):
        """ Return a list of path objects that match the pattern.

        pattern - a path relative to this directory, with wildcards.

        For example, path('/users').glob('*/bin/*') returns a list
        of all the files users have in their bin directories.
        """
        cls = self.__class__
        return [cls(s) for s in glob.glob(_base(self / pattern))]


    # --- Reading or writing an entire file at once.

    def open(self, mode='r'):
        """ Open this file.  Return a file object. """
        return file(self, mode)

    def bytes(self):
        """ Open this file, read all bytes, return them as a string. """
        f = self.open('rb')
        try:
            return f.read()
        finally:
            f.close()

    def write_bytes(self, bytes, append=False):
        """ Open this file and write the given bytes to it.

        Default behavior is to overwrite any existing file.
        Call p.write_bytes(bytes, append=True) to append instead.
        """
        if append:
            mode = 'ab'
        else:
            mode = 'wb'
        f = self.open(mode)
        try:
            f.write(bytes)
        finally:
            f.close()

    def text(self, encoding=None, errors='strict'):
        r""" Open this file, read it in, return the content as a string.

        This uses 'U' mode in Python 2.3 and later, so '\r\n' and '\r'
        are automatically translated to '\n'.

        Optional arguments:

        encoding - The Unicode encoding (or character set) of
            the file.  If present, the content of the file is
            decoded and returned as a unicode object; otherwise
            it is returned as an 8-bit str.
        errors - How to handle Unicode errors; see help(str.decode)
            for the options.  Default is 'strict'.
        """
        if encoding is None:
            # 8-bit
            f = self.open(_textmode)
            try:
                return f.read()
            finally:
                f.close()
        else:
            # Unicode
            f = codecs.open(self, 'r', encoding, errors)
            # (Note - Can't use 'U' mode here, since codecs.open
            # doesn't support 'U' mode, even in Python 2.3.)
            try:
                t = f.read()
            finally:
                f.close()
            return (t.replace(u'\r\n', u'\n')
                     .replace(u'\r\x85', u'\n')
                     .replace(u'\r', u'\n')
                     .replace(u'\x85', u'\n')
                     .replace(u'\u2028', u'\n'))

    def write_text(self, text, encoding=None, errors='strict', linesep=os.linesep, append=False):
        r""" Write the given text to this file.

        The default behavior is to overwrite any existing file;
        to append instead, use the 'append=True' keyword argument.

        There are two differences between path.write_text() and
        path.write_bytes(): newline handling and Unicode handling.
        See below.

        Parameters:

          - text - str/unicode - The text to be written.

          - encoding - str - The Unicode encoding that will be used.
            This is ignored if 'text' isn't a Unicode string.

          - errors - str - How to handle Unicode encoding errors.
            Default is 'strict'.  See help(unicode.encode) for the
            options.  This is ignored if 'text' isn't a Unicode
            string.

          - linesep - keyword argument - str/unicode - The sequence of
            characters to be used to mark end-of-line.  The default is
            os.linesep.  You can also specify None; this means to
            leave all newlines as they are in 'text'.

          - append - keyword argument - bool - Specifies what to do if
            the file already exists (True: append to the end of it;
            False: overwrite it.)  The default is False.


        --- Newline handling.

        write_text() converts all standard end-of-line sequences
        ('\n', '\r', and '\r\n') to your platform's default end-of-line
        sequence (see os.linesep; on Windows, for example, the
        end-of-line marker is '\r\n').

        If you don't like your platform's default, you can override it
        using the 'linesep=' keyword argument.  If you specifically want
        write_text() to preserve the newlines as-is, use 'linesep=None'.

        This applies to Unicode text the same as to 8-bit text, except
        there are three additional standard Unicode end-of-line sequences:
        u'\x85', u'\r\x85', and u'\u2028'.

        (This is slightly different from when you open a file for
        writing with fopen(filename, "w") in C or file(filename, 'w')
        in Python.)


        --- Unicode

        If 'text' isn't Unicode, then apart from newline handling, the
        bytes are written verbatim to the file.  The 'encoding' and
        'errors' arguments are not used and must be omitted.

        If 'text' is Unicode, it is first converted to bytes using the
        specified 'encoding' (or the default encoding if 'encoding'
        isn't specified).  The 'errors' argument applies only to this
        conversion.

        """
        if isinstance(text, unicode):
            if linesep is not None:
                # Convert all standard end-of-line sequences to
                # ordinary newline characters.
                text = (text.replace(u'\r\n', u'\n')
                            .replace(u'\r\x85', u'\n')
                            .replace(u'\r', u'\n')
                            .replace(u'\x85', u'\n')
                            .replace(u'\u2028', u'\n'))
                text = text.replace(u'\n', linesep)
            if encoding is None:
                encoding = sys.getdefaultencoding()
            bytes = text.encode(encoding, errors)
        else:
            # It is an error to specify an encoding if 'text' is
            # an 8-bit string.
            assert encoding is None

            if linesep is not None:
                text = (text.replace('\r\n', '\n')
                            .replace('\r', '\n'))
                bytes = text.replace('\n', linesep)

        self.write_bytes(bytes, append)

    def lines(self, encoding=None, errors='strict', retain=True):
        r""" Open this file, read all lines, return them in a list.

        Optional arguments:
            encoding - The Unicode encoding (or character set) of
                the file.  The default is None, meaning the content
                of the file is read as 8-bit characters and returned
                as a list of (non-Unicode) str objects.
            errors - How to handle Unicode errors; see help(str.decode)
                for the options.  Default is 'strict'
            retain - If true, retain newline characters; but all newline
                character combinations ('\r', '\n', '\r\n') are
                translated to '\n'.  If false, newline characters are
                stripped off.  Default is True.

        This uses 'U' mode in Python 2.3 and later.
        """
        if encoding is None and retain:
            f = self.open(_textmode)
            try:
                return f.readlines()
            finally:
                f.close()
        else:
            return self.text(encoding, errors).splitlines(retain)

    def write_lines(self, lines, encoding=None, errors='strict',
                    linesep=os.linesep, append=False):
        r""" Write the given lines of text to this file.

        By default this overwrites any existing file at this path.

        This puts a platform-specific newline sequence on every line.
        See 'linesep' below.

        lines - A list of strings.

        encoding - A Unicode encoding to use.  This applies only if
            'lines' contains any Unicode strings.

        errors - How to handle errors in Unicode encoding.  This
            also applies only to Unicode strings.

        linesep - The desired line-ending.  This line-ending is
            applied to every line.  If a line already has any
            standard line ending ('\r', '\n', '\r\n', u'\x85',
            u'\r\x85', u'\u2028'), that will be stripped off and
            this will be used instead.  The default is os.linesep,
            which is platform-dependent ('\r\n' on Windows, '\n' on
            Unix, etc.)  Specify None to write the lines as-is,
            like file.writelines().

        Use the keyword argument append=True to append lines to the
        file.  The default is to overwrite the file.  Warning:
        When you use this with Unicode data, if the encoding of the
        existing data in the file is different from the encoding
        you specify with the encoding= parameter, the result is
        mixed-encoding data, which can really confuse someone trying
        to read the file later.
        """
        if append:
            mode = 'ab'
        else:
            mode = 'wb'
        f = self.open(mode)
        try:
            for line in lines:
                isUnicode = isinstance(line, unicode)
                if linesep is not None:
                    # Strip off any existing line-end and add the
                    # specified linesep string.
                    if isUnicode:
                        if line[-2:] in (u'\r\n', u'\x0d\x85'):
                            line = line[:-2]
                        elif line[-1:] in (u'\r', u'\n',
                                           u'\x85', u'\u2028'):
                            line = line[:-1]
                    else:
                        if line[-2:] == '\r\n':
                            line = line[:-2]
                        elif line[-1:] in ('\r', '\n'):
                            line = line[:-1]
                    line += linesep
                if isUnicode:
                    if encoding is None:
                        encoding = sys.getdefaultencoding()
                    line = line.encode(encoding, errors)
                f.write(line)
        finally:
            f.close()

    def read_md5(self):
        """ Calculate the md5 hash for this file.

        This reads through the entire file.
        """
        f = self.open('rb')
        try:
            m = md5.new()
            while True:
                d = f.read(8192)
                if not d:
                    break
                m.update(d)
        finally:
            f.close()
        return m.digest()

    # --- Methods for querying the filesystem.

    exists = os.path.exists
    isdir = os.path.isdir
    isfile = os.path.isfile
    islink = os.path.islink
    ismount = os.path.ismount

    if hasattr(os.path, 'samefile'):
        samefile = os.path.samefile

    getatime = os.path.getatime
    atime = property(
        getatime, None, None,
        """ Last access time of the file. """)

    getmtime = os.path.getmtime
    mtime = property(
        getmtime, None, None,
        """ Last-modified time of the file. """)

    if hasattr(os.path, 'getctime'):
        getctime = os.path.getctime
        ctime = property(
            getctime, None, None,
            """ Creation time of the file. """)

    getsize = os.path.getsize
    size = property(
        getsize, None, None,
        """ Size of the file, in bytes. """)

    if hasattr(os, 'access'):
        def access(self, mode):
            """ Return true if current user has access to this path.

            mode - One of the constants os.F_OK, os.R_OK, os.W_OK, os.X_OK
            """
            return os.access(self, mode)

    def stat(self):
        """ Perform a stat() system call on this path. """
        return os.stat(self)

    def lstat(self):
        """ Like path.stat(), but do not follow symbolic links. """
        return os.lstat(self)

    def get_owner(self):
        r""" Return the name of the owner of this file or directory.

        This follows symbolic links.

        On Windows, this returns a name of the form ur'DOMAIN\User Name'.
        On Windows, a group can own a file or directory.
        """
        if os.name == 'nt':
            if win32security is None:
                raise Exception("path.owner requires win32all to be installed")
            desc = win32security.GetFileSecurity(
                self, win32security.OWNER_SECURITY_INFORMATION)
            sid = desc.GetSecurityDescriptorOwner()
            account, domain, typecode = win32security.LookupAccountSid(None, sid)
            return domain + u'\\' + account
        else:
            if pwd is None:
                raise NotImplementedError("path.owner is not implemented on this platform.")
            st = self.stat()
            return pwd.getpwuid(st.st_uid).pw_name

    owner = property(
        get_owner, None, None,
        """ Name of the owner of this file or directory. """)

    if hasattr(os, 'statvfs'):
        def statvfs(self):
            """ Perform a statvfs() system call on this path. """
            return os.statvfs(self)

    if hasattr(os, 'pathconf'):
        def pathconf(self, name):
            return os.pathconf(self, name)


    # --- Modifying operations on files and directories

    def utime(self, times):
        """ Set the access and modified times of this file. """
        os.utime(self, times)

    def chmod(self, mode):
        os.chmod(self, mode)

    if hasattr(os, 'chown'):
        def chown(self, uid, gid):
            os.chown(self, uid, gid)

    def rename(self, new):
        os.rename(self, new)

    def renames(self, new):
        os.renames(self, new)


    # --- Create/delete operations on directories

    def mkdir(self, mode=0777):
        os.mkdir(self, mode)

    def makedirs(self, mode=0777):
        os.makedirs(self, mode)

    def rmdir(self):
        os.rmdir(self)

    def removedirs(self):
        os.removedirs(self)


    # --- Modifying operations on files

    def touch(self):
        """ Set the access/modified times of this file to the current time.
        Create the file if it does not exist.
        """
        fd = os.open(self, os.O_WRONLY | os.O_CREAT, 0666)
        os.close(fd)
        os.utime(self, None)

    def remove(self):
        os.remove(self)

    def unlink(self):
        os.unlink(self)


    # --- Links

    if hasattr(os, 'link'):
        def link(self, newpath):
            """ Create a hard link at 'newpath', pointing to this file. """
            os.link(self, newpath)

    if hasattr(os, 'symlink'):
        def symlink(self, newlink):
            """ Create a symbolic link at 'newlink', pointing here. """
            os.symlink(self, newlink)

    if hasattr(os, 'readlink'):
        def readlink(self):
            """ Return the path to which this symbolic link points.

            The result may be an absolute or a relative path.
            """
            return self.__class__(os.readlink(self))

        def readlinkabs(self):
            """ Return the path to which this symbolic link points.

            The result is always an absolute path.
            """
            p = self.readlink()
            if p.isabs():
                return p
            else:
                return (self.parent / p).abspath()


    # --- High-level functions from shutil

    copyfile = shutil.copyfile
    copymode = shutil.copymode
    copystat = shutil.copystat
    copy = shutil.copy
    copy2 = shutil.copy2
    copytree = shutil.copytree
    if hasattr(shutil, 'move'):
        move = shutil.move
    rmtree = shutil.rmtree


    # --- Special stuff from os

    if hasattr(os, 'chroot'):
        def chroot(self):
            os.chroot(self)

    if hasattr(os, 'startfile'):
        def startfile(self):
            os.startfile(self)


########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-
"""App configuration."""
config = {}

########NEW FILE########
__FILENAME__ = handlers
# -*- coding: utf-8 -*-
"""
    hello_world.handlers
    ~~~~~~~~~~~~~~~~~~~~

    Hello, World!: the simplest tipfy app.

    :copyright: 2009 by tipfy.org.
    :license: BSD, see LICENSE for more details.
"""
from tipfy import RequestHandler, Response
from tipfyext.jinja2 import Jinja2Mixin


class HelloWorldHandler(RequestHandler):
    def get(self):
        """Simply returns a Response object with an enigmatic salutation."""
        return Response('Hello, World!')


class PrettyHelloWorldHandler(RequestHandler, Jinja2Mixin):
    def get(self):
        """Simply returns a rendered template with an enigmatic salutation."""
        context = {
            'message': 'Hello, World!',
        }
        return self.render_response('hello_world.html', **context)

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-
"""WSGI app setup."""
import os
import sys

if 'lib' not in sys.path:
    # Add lib as primary libraries directory, with fallback to lib/dist
    # and optionally to lib/dist.zip, loaded using zipimport.
    sys.path[0:0] = ['lib', 'lib/dist', 'lib/dist.zip']

from tipfy import Tipfy
from config import config
from urls import rules


def enable_appstats(app):
    """Enables appstats middleware."""
    if debug:
        return

    from google.appengine.ext.appstats.recording import appstats_wsgi_middleware
    app.wsgi_app = appstats_wsgi_middleware(app.wsgi_app)


def enable_jinja2_debugging():
    """Enables blacklisted modules that help Jinja2 debugging."""
    if not debug:
        return

    # This enables better debugging info for errors in Jinja2 templates.
    from google.appengine.tools.dev_appserver import HardenedModulesHook
    HardenedModulesHook._WHITE_LIST_C_MODULES += ['_ctypes', 'gestalt']


# Is this the development server?
debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

# Instantiate the application.
app = Tipfy(rules=rules, config=config, debug=debug)
enable_appstats(app)
enable_jinja2_debugging()


def main():
    # Run the app.
    app.run()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
"""URL definitions."""
from tipfy import Rule

rules = [
    Rule('/', name='hello-world', handler='hello_world.handlers.HelloWorldHandler'),
    Rule('/pretty', name='hello-world-pretty', handler='hello_world.handlers.PrettyHelloWorldHandler'),
]

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-
"""App configuration."""
config = {}

########NEW FILE########
__FILENAME__ = handlers
# -*- coding: utf-8 -*-
"""
    hello_world.handlers
    ~~~~~~~~~~~~~~~~~~~~

    Hello, World!: the simplest tipfy app.

    :copyright: 2009 by tipfy.org.
    :license: BSD, see LICENSE for more details.
"""
from tipfy.app import Response
from tipfy.handler import RequestHandler
from tipfyext.jinja2 import Jinja2Mixin


class HelloWorldHandler(RequestHandler):
    def get(self):
        """Simply returns a Response object with an enigmatic salutation."""
        return Response('Hello, World!')


class PrettyHelloWorldHandler(RequestHandler, Jinja2Mixin):
    def get(self):
        """Simply returns a rendered template with an enigmatic salutation."""
        context = {
            'message': 'Hello, World!',
        }
        return self.render_response('hello_world.html', **context)

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-
"""WSGI app setup."""
import os
import sys

# Add lib as primary libraries directory, with fallback to lib/dist
# and optionally to lib/dist.zip, loaded using zipimport.
lib_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'lib')
if lib_path not in sys.path:
    sys.path[0:0] = [
        lib_path,
        os.path.join(lib_path, 'dist'),
        os.path.join(lib_path, 'dist.zip'),
    ]


from tipfy.app import App
from config import config
from urls import rules

def enable_appstats(app):
    """Enables appstats middleware."""
    from google.appengine.ext.appstats.recording import \
        appstats_wsgi_middleware
    app.dispatch = appstats_wsgi_middleware(app.dispatch)

def enable_jinja2_debugging():
    """Enables blacklisted modules that help Jinja2 debugging."""
    if not debug:
        return
    from google.appengine.tools.dev_appserver import HardenedModulesHook
    HardenedModulesHook._WHITE_LIST_C_MODULES += ['_ctypes', 'gestalt']

# Is this the development server?
debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

# Instantiate the application.
app = App(rules=rules, config=config, debug=debug)
enable_appstats(app)
enable_jinja2_debugging()

def main():
    app.run()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
"""URL definitions."""
from tipfy.routing import Rule

rules = [
    Rule('/', name='hello-world', handler='hello_world.handlers.HelloWorldHandler'),
    Rule('/pretty', name='hello-world-pretty', handler='hello_world.handlers.PrettyHelloWorldHandler'),
]

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

import os, shutil, sys, tempfile, textwrap, urllib, urllib2, subprocess
from optparse import OptionParser

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
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
import site
sys.path[:] = clean_path
for k, v in sys.modules.items():
    if k in ('setuptools', 'pkg_resources') or (
        hasattr(v, '__path__') and
        len(v.__path__)==1 and
        not os.path.exists(os.path.join(v.__path__[0],'__init__.py'))):
        # This is a namespace package.  Remove it.
        sys.modules.pop(k)

is_jython = sys.platform.startswith('java')

setuptools_source = 'http://peak.telecommunity.com/dist/ez_setup.py'
distribute_source = 'http://python-distribute.org/distribute_setup.py'

# parsing arguments
def normalize_to_url(option, opt_str, value, parser):
    if value:
        if '://' not in value: # It doesn't smell like a URL.
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
                   action="store_true", dest="use_distribute", default=True,
                   help="Use Distribute rather than Setuptools.")
parser.add_option("--setup-source", action="callback", dest="setup_source",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or file location for the setup file. "
                        "If you use Setuptools, this will default to " +
                        setuptools_source + "; if you use Distribute, this "
                        "will default to " + distribute_source +"."))
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

# if -c was provided, we push it back into args for buildout's main function
if options.config_file is not None:
    args += ['-c', options.config_file]

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
    args.append('buildout:accept-buildout-test-releases=true')
args.append('bootstrap')

try:
    import pkg_resources
    import setuptools # A flag.  Sometimes pkg_resources is installed alone.
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
    requirement = '=='.join((requirement, version))
cmd.append(requirement)

if is_jython:
    import subprocess
    exitcode = subprocess.Popen(cmd, env=env).wait()
else: # Windows prefers this, apparently; otherwise we would prefer subprocess
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
zc.buildout.buildout.main(args)
if not options.eggs: # clean up temporary egg directory
    shutil.rmtree(eggs_dir)

########NEW FILE########
__FILENAME__ = run_tests
import os
import sys
import unittest

gae_path = '/usr/local/google_appengine'

current_path = os.path.abspath(os.path.dirname(__file__))
tests_path = os.path.join(current_path, 'tests')
sys.path[0:0] = [
    tests_path,
    gae_path,
    os.path.join(gae_path, 'lib', 'django_0_96'),
    os.path.join(gae_path, 'lib', 'webob'),
    os.path.join(gae_path, 'lib', 'yaml', 'lib'),
]

all_tests = [f[:-8] for f in os.listdir(tests_path) if f.endswith('_test.py')]

def get_suite(tests):
    tests = sorted(tests)
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    for test in tests:
        suite.addTest(loader.loadTestsFromName(test))
    return suite

if __name__ == '__main__':
    # To run all tests:
    #     $ python run_tests.py
    # To run a single test:
    #     $ python run_tests.py app
    # To run a couple of tests:
    #     $ python run_tests.py app config sessions
    tests = sys.argv[1:]
    if not tests:
        tests = all_tests
    tests = ['%s_test' % t for t in tests]
    suite = get_suite(tests)
    unittest.TextTestRunner(verbosity=2).run(suite)


########NEW FILE########
__FILENAME__ = app_test
# -*- coding: utf-8 -*-
"""
    Tests for tipfy.app
"""
from __future__ import with_statement

import os
import sys
import StringIO
import unittest

import tipfy
from tipfy import Request, RequestHandler, Response, Rule, Tipfy
from tipfy.utils import json_encode
from tipfy.local import local

#from tipfy.app import Request, Response, Tipfy
#from tipfy.handler import RequestHandler
#from tipfy.json import json_encode
#from tipfy.routing import Rule

import test_utils

class BaseTestCase(test_utils.BaseTestCase):
    def setUp(self):
        self.appengine = tipfy.app.APPENGINE
        self.dev_appserver = tipfy.app.DEV_APPSERVER
        test_utils.BaseTestCase.setUp(self)

    def tearDown(self):
        tipfy.app.APPENGINE = self.appengine
        tipfy.app.DEV_APPSERVER = self.dev_appserver
        test_utils.BaseTestCase.tearDown(self)

    def _set_dev_server_flag(self, flag):
        tipfy.app.APPENGINE = flag
        tipfy.app.DEV_APPSERVER = flag


class AllMethodsHandler(RequestHandler):
    def get(self, **kwargs):
        return Response('Method: %s' % self.request.method)

    delete = head = options = post = put = trace = get


class BrokenHandler(RequestHandler):
    def get(self, **kwargs):
        raise ValueError('booo!')


class BrokenButFixedHandler(BrokenHandler):
    def handle_exception(self, exception=None):
        # Let's fix it.
        return Response('That was close!', status=200)


class Handle404(RequestHandler):
    def handle_exception(self, exception=None):
        return Response('404 custom handler', status=404)


class Handle405(RequestHandler):
    def handle_exception(self, exception=None):
        response = Response('405 custom handler', status=405)
        response.headers['Allow'] = 'GET'
        return response


class Handle500(RequestHandler):
    def handle_exception(self, exception=None):
        return Response('500 custom handler', status=500)


class TestRequestHandler(BaseTestCase):
    def test_200(self):
        app = Tipfy(rules=[Rule('/', name='home', handler=AllMethodsHandler)])
        client = app.get_test_client()

        for method in app.allowed_methods:
            response = client.open('/', method=method)
            self.assertEqual(response.status_code, 200, method)
            if method == 'HEAD':
                self.assertEqual(response.data, '')
            else:
                self.assertEqual(response.data, 'Method: %s' % method)

        # App Engine mode.
        self._set_dev_server_flag(True)
        response = client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 'Method: GET')

    def test_404(self):
        """No URL rules defined."""
        app = Tipfy()
        client = app.get_test_client()

        # Normal mode.
        response = client.get('/')
        self.assertEqual(response.status_code, 404)

        # Debug mode.
        app.debug = True
        response = client.get('/')
        self.assertEqual(response.status_code, 404)

    def test_500(self):
        """Handler import will fail."""
        app = Tipfy(rules=[Rule('/', name='home', handler='non.existent.handler')])
        client = app.get_test_client()

        # Normal mode.
        response = client.get('/')
        self.assertEqual(response.status_code, 500)

        # Debug mode.
        app.debug = True
        app.config['tipfy']['enable_debugger'] = False
        self.assertRaises(ImportError, client.get, '/')

    def test_501(self):
        """Method is not in app.allowed_methods."""
        app = Tipfy()
        client = app.get_test_client()

        # Normal mode.
        response = client.open('/', method='CONNECT')
        self.assertEqual(response.status_code, 501)

        # Debug mode.
        app.debug = True
        response = client.open('/', method='CONNECT')
        self.assertEqual(response.status_code, 501)

    def test_abort(self):
        class HandlerWithAbort(RequestHandler):
            def get(self, **kwargs):
                self.abort(kwargs.get('status_code'))

        app = Tipfy(rules=[
            Rule('/<int:status_code>', name='abort-me', handler=HandlerWithAbort),
        ])
        client = app.get_test_client()

        response = client.get('/400')
        self.assertEqual(response.status_code, 400)

        response = client.get('/403')
        self.assertEqual(response.status_code, 403)

        response = client.get('/404')
        self.assertEqual(response.status_code, 404)

    def test_get_config(self):
        app = Tipfy(rules=[
            Rule('/', name='home', handler=AllMethodsHandler),
        ], config = {
            'foo': {
                'bar': 'baz',
            }
        })
        with app.get_test_handler('/') as handler:
            self.assertEqual(handler.get_config('foo', 'bar'), 'baz')

    def test_handle_exception(self):
        app = Tipfy([
            Rule('/', handler=AllMethodsHandler, name='home'),
            Rule('/broken', handler=BrokenHandler, name='broken'),
            Rule('/broken-but-fixed', handler=BrokenButFixedHandler, name='broken-but-fixed'),
        ], debug=False)
        client = app.get_test_client()

        response = client.get('/broken')
        self.assertEqual(response.status_code, 500)

        response = client.get('/broken-but-fixed')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 'That was close!')

    def test_redirect(self):
        class HandlerWithRedirect(RequestHandler):
            def get(self, **kwargs):
                return self.redirect('/')

        app = Tipfy(rules=[
            Rule('/', name='home', handler=AllMethodsHandler),
            Rule('/redirect-me', name='redirect', handler=HandlerWithRedirect),
        ])

        client = app.get_test_client()
        response = client.get('/redirect-me', follow_redirects=True)
        self.assertEqual(response.data, 'Method: GET')

    def test_redirect_empty(self):
        class HandlerWithRedirect(RequestHandler):
            def get(self, **kwargs):
                return self.redirect('/', empty=True)

        app = Tipfy(rules=[
            Rule('/', name='home', handler=AllMethodsHandler),
            Rule('/redirect-me', name='redirect', handler=HandlerWithRedirect),
        ])

        client = app.get_test_client()
        response = client.get('/redirect-me', follow_redirects=False)
        self.assertEqual(response.data, '')

    def test_redirect_to(self):
        class HandlerWithRedirectTo(RequestHandler):
            def get(self, **kwargs):
                return self.redirect_to('home')

        app = Tipfy(rules=[
            Rule('/', name='home', handler=AllMethodsHandler),
            Rule('/redirect-me', name='redirect', handler=HandlerWithRedirectTo),
        ])

        client = app.get_test_client()
        response = client.get('/redirect-me', follow_redirects=True)
        self.assertEqual(response.data, 'Method: GET')

    def test_redirect_to_empty(self):
        class HandlerWithRedirectTo(RequestHandler):
            def get(self, **kwargs):
                return self.redirect_to('home', _empty=True)

        app = Tipfy(rules=[
            Rule('/', name='home', handler=AllMethodsHandler),
            Rule('/redirect-me', name='redirect', handler=HandlerWithRedirectTo),
        ])

        client = app.get_test_client()
        response = client.get('/redirect-me', follow_redirects=False)
        self.assertEqual(response.data, '')

    def test_redirect_relative_uris(self):
        class MyHandler(RequestHandler):
            def get(self):
                return self.redirect(self.request.args.get('redirect'))

        app = Tipfy(rules=[
            Rule('/foo/bar', name='test1', handler=MyHandler),
            Rule('/foo/bar/', name='test2', handler=MyHandler),
        ])
        client = app.get_test_client()

        response = client.get('/foo/bar/', query_string={'redirect': '/baz'})
        self.assertEqual(response.headers['Location'], 'http://localhost/baz')

        response = client.get('/foo/bar/', query_string={'redirect': './baz'})
        self.assertEqual(response.headers['Location'], 'http://localhost/foo/bar/baz')

        response = client.get('/foo/bar/', query_string={'redirect': '../baz'})
        self.assertEqual(response.headers['Location'], 'http://localhost/foo/baz')

        response = client.get('/foo/bar', query_string={'redirect': '/baz'})
        self.assertEqual(response.headers['Location'], 'http://localhost/baz')

        response = client.get('/foo/bar', query_string={'redirect': './baz'})
        self.assertEqual(response.headers['Location'], 'http://localhost/foo/baz')

        response = client.get('/foo/bar', query_string={'redirect': '../baz'})
        self.assertEqual(response.headers['Location'], 'http://localhost/baz')

    def test_url_for(self):
        app = Tipfy(rules=[
            Rule('/', name='home', handler=AllMethodsHandler),
            Rule('/about', name='about', handler='handlers.About'),
            Rule('/contact', name='contact', handler='handlers.Contact'),
        ])
        with app.get_test_handler('/') as handler:
            self.assertEqual(handler.url_for('home'), '/')
            self.assertEqual(handler.url_for('about'), '/about')
            self.assertEqual(handler.url_for('contact'), '/contact')

            # Extras
            self.assertEqual(handler.url_for('about', _anchor='history'), '/about#history')
            self.assertEqual(handler.url_for('about', _full=True), 'http://localhost/about')
            self.assertEqual(handler.url_for('about', _netloc='www.google.com'), 'http://www.google.com/about')
            self.assertEqual(handler.url_for('about', _scheme='https'), 'https://localhost/about')

    def test_store_instances(self):
        from tipfy.appengine.auth import AuthStore
        from tipfy.i18n import I18nStore
        from tipfy.sessions import SecureCookieSession

        app = Tipfy(rules=[
            Rule('/', name='home', handler=AllMethodsHandler),
        ], config={
            'tipfy.sessions': {
                'secret_key': 'secret',
            },
        })
        with app.get_test_handler('/') as handler:
            self.assertEqual(isinstance(handler.session, SecureCookieSession), True)
            self.assertEqual(isinstance(handler.auth, AuthStore), True)
            self.assertEqual(isinstance(handler.i18n, I18nStore), True)


class TestHandlerMiddleware(BaseTestCase):
    def test_before_dispatch(self):
        res = 'Intercepted!'

        class MyMiddleware(object):
            def before_dispatch(self, handler):
                return Response(res)

        class MyHandler(RequestHandler):
            middleware = [MyMiddleware()]

            def get(self, **kwargs):
                return Response('default')

        app = Tipfy(rules=[
            Rule('/', name='home', handler=MyHandler),
        ])
        client = app.get_test_client()
        response = client.get('/')
        self.assertEqual(response.data, res)

    def test_after_dispatch(self):
        res = 'Intercepted!'

        class MyMiddleware(object):
            def after_dispatch(self, handler, response):
                response.data += res
                return response

        class MyHandler(RequestHandler):
            middleware = [MyMiddleware()]

            def get(self, **kwargs):
                return Response('default')

        app = Tipfy(rules=[
            Rule('/', name='home', handler=MyHandler),
        ])
        client = app.get_test_client()
        response = client.get('/')
        self.assertEqual(response.data, 'default' + res)

    def test_handle_exception(self):
        res = 'Catched!'

        class MyMiddleware(object):
            def handle_exception(self, handler, exception):
                return Response(res)

        class MyHandler(RequestHandler):
            middleware = [MyMiddleware()]

            def get(self, **kwargs):
                raise ValueError()

        app = Tipfy(rules=[
            Rule('/', name='home', handler=MyHandler),
        ])
        client = app.get_test_client()
        response = client.get('/')
        self.assertEqual(response.data, res)

    def test_handle_exception_2(self):
        res = 'I fixed it!'

        class MyMiddleware(object):
            def handle_exception(self, handler, exception):
                raise ValueError()

        class MyHandler(RequestHandler):
            middleware = [MyMiddleware()]

            def get(self, **kwargs):
                raise ValueError()

        class ErrorHandler(RequestHandler):
            def handle_exception(self, exception):
                return Response(res)

        app = Tipfy(rules=[
            Rule('/', name='home', handler=MyHandler),
        ], debug=False)
        app.error_handlers[500] = ErrorHandler

        client = app.get_test_client()
        response = client.get('/')
        self.assertEqual(response.data, res)

    def test_handle_exception_3(self):
        class MyMiddleware(object):
            def handle_exception(self, handler, exception):
                pass

        class MyHandler(RequestHandler):
            middleware = [MyMiddleware()]

            def get(self, **kwargs):
                raise ValueError()

        app = Tipfy(rules=[
            Rule('/', name='home', handler=MyHandler),
        ])
        client = app.get_test_client()
        response = client.get('/')
        self.assertEqual(response.status_code, 500)

    def test_handle_exception_with_app_error_handler(self):
        class MyMiddleware(object):
            def handle_exception(self, handler, exception):
                raise ValueError()

        class MyHandler(RequestHandler):
            middleware = [MyMiddleware()]

            def get(self, **kwargs):
                raise ValueError()

        class ErrorHandler(RequestHandler):
            def handle_exception(self, exception):
                raise ValueError()

        app = Tipfy(rules=[
            Rule('/', name='home', handler=MyHandler),
        ], debug=False)
        app.error_handlers[500] = ErrorHandler

        client = app.get_test_client()
        response = client.get('/')
        self.assertEqual(response.status_code, 500)


class TestTipfy(BaseTestCase):
    def test_custom_error_handlers(self):
        app = Tipfy([
            Rule('/', handler=AllMethodsHandler, name='home'),
            Rule('/broken', handler=BrokenHandler, name='broken'),
        ], debug=False)
        app.error_handlers = {
            404: Handle404,
            405: Handle405,
            500: Handle500,
        }
        client = app.get_test_client()

        res = client.get('/nowhere')
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.data, '404 custom handler')

        res = client.put('/broken')
        self.assertEqual(res.status_code, 405)
        self.assertEqual(res.data, '405 custom handler')
        self.assertEqual(res.headers.get('Allow'), 'GET')

        res = client.get('/broken')
        self.assertEqual(res.status_code, 500)
        self.assertEqual(res.data, '500 custom handler')

    def test_store_classes(self):
        from tipfy.appengine.auth import AuthStore
        from tipfy.i18n import I18nStore
        from tipfy.sessions import SessionStore

        app = Tipfy()
        self.assertEqual(app.auth_store_class, AuthStore)
        self.assertEqual(app.i18n_store_class, I18nStore)
        self.assertEqual(app.session_store_class, SessionStore)

    def test_make_response(self):
        app = Tipfy()
        request = Request.from_values()

        # Empty.
        response = app.make_response(request)
        self.assertEqual(isinstance(response, app.response_class), True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, '')

        # From Response.
        response = app.make_response(request, Response('Hello, World!'))
        self.assertEqual(isinstance(response, app.response_class), True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 'Hello, World!')

        # From string.
        response = app.make_response(request, 'Hello, World!')
        self.assertEqual(isinstance(response, app.response_class), True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 'Hello, World!')

        # From tuple.
        response = app.make_response(request, 'Hello, World!', 404)
        self.assertEqual(isinstance(response, app.response_class), True)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, 'Hello, World!')

        # From None.
        self.assertRaises(ValueError, app.make_response, request, None)

    def test_dev_run(self):
        self._set_dev_server_flag(True)

        sys.stdout = StringIO.StringIO()

        os.environ['APPLICATION_ID'] = 'my-app'
        os.environ['SERVER_SOFTWARE'] = 'Development'
        os.environ['SERVER_NAME'] = 'localhost'
        os.environ['SERVER_PORT'] = '8080'
        os.environ['REQUEST_METHOD'] = 'GET'

        app = Tipfy(rules=[
            Rule('/', name='home', handler=AllMethodsHandler),
        ], debug=True)

        app.run()
        self.assertEqual(sys.stdout.getvalue(), 'Status: 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: 11\r\n\r\nMethod: GET')

    def test_get_config(self):
        app = Tipfy(config={'tipfy': {'foo': 'bar'}})
        self.assertEqual(app.get_config('tipfy', 'foo'), 'bar')


class TestRequest(BaseTestCase):
    def test_json(self):
        class JsonHandler(RequestHandler):
            def get(self, **kwargs):
                return Response(self.request.json['foo'])

        app = Tipfy(rules=[
            Rule('/', name='home', handler=JsonHandler),
        ], debug=True)

        data = json_encode({'foo': 'bar'})
        client = app.get_test_client()
        response = client.get('/', content_type='application/json', data=data)
        self.assertEqual(response.data, 'bar')


if __name__ == '__main__':
    test_utils.main()

########NEW FILE########
__FILENAME__ = auth_test
from __future__ import with_statement

import os
import unittest

from tipfy import Request, RequestHandler, Response, Rule, Tipfy
from tipfy.app import local

import tipfy.auth
from tipfy.auth import (AdminRequiredMiddleware, LoginRequiredMiddleware,
    UserRequiredMiddleware, UserRequiredIfAuthenticatedMiddleware,
    admin_required, login_required, user_required,
    user_required_if_authenticated, check_password_hash, generate_password_hash,
    create_session_id, MultiAuthStore)
from tipfy.appengine.auth import AuthStore, MixedAuthStore
from tipfy.appengine.auth.model import User

import test_utils


class LoginHandler(RequestHandler):
    def get(self, **kwargs):
        return Response('login')


class LogoutHandler(RequestHandler):
    def get(self, **kwargs):
        return Response('logout')


class SignupHandler(RequestHandler):
    def get(self, **kwargs):
        return Response('signup')


class HomeHandler(RequestHandler):
    def get(self, **kwargs):
        return Response('home sweet home')


def get_app():
    app = Tipfy(rules=[
        Rule('/login', name='auth/login', handler=LoginHandler),
        Rule('/logout', name='auth/logout', handler=LogoutHandler),
        Rule('/signup', name='auth/signup', handler=SignupHandler),
    ])
    return app


class TestAuthStore(test_utils.BaseTestCase):
    def test_user_model(self):
        app = get_app()
        app.router.add(Rule('/', name='home', handler=HomeHandler))

        request = Request.from_values('/')
        local.current_handler = RequestHandler(app, request)

        store = AuthStore(local.current_handler)
        self.assertEqual(store.user_model, User)

    def test_login_url(self):
        app = get_app()
        app.router.add(Rule('/', name='home', handler=HomeHandler))

        with app.get_test_context() as request:
            request.app.router.match(request)

            store = AuthStore(request)
            self.assertEqual(store.login_url(), request.app.router.url_for(request, 'auth/login', dict(redirect='/')))

            tipfy.auth.DEV_APPSERVER_APPSERVER = False
            store.config['secure_urls'] = True
            self.assertEqual(store.login_url(), request.app.router.url_for(request, 'auth/login', dict(redirect='/', _scheme='https')))
            tipfy.auth.DEV_APPSERVER_APPSERVER = True

    def test_logout_url(self):
        app = get_app()
        app.router.add(Rule('/', name='home', handler=HomeHandler))

        with app.get_test_context() as request:
            request.app.router.match(request)
            store = AuthStore(request)
            self.assertEqual(store.logout_url(), request.app.router.url_for(request, 'auth/logout', dict(redirect='/')))

    def test_signup_url(self):
        app = get_app()
        app.router.add(Rule('/', name='home', handler=HomeHandler))

        with app.get_test_context() as request:
            request.app.router.match(request)
            store = AuthStore(request)
            self.assertEqual(store.signup_url(), request.app.router.url_for(request, 'auth/signup', dict(redirect='/')))


class TestMiddleware(test_utils.BaseTestCase):
    def tearDown(self):
        os.environ.pop('USER_EMAIL', None)
        os.environ.pop('USER_ID', None)
        os.environ.pop('USER_IS_ADMIN', None)
        test_utils.BaseTestCase.tearDown(self)

    def test_login_required_middleware_invalid(self):
        class MyHandler(HomeHandler):
            middleware = [LoginRequiredMiddleware()]

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], 'http://localhost/login?redirect=%2F')

    def test_login_required_decorator_invalid(self):
        class MyHandler(HomeHandler):
            @login_required
            def get(self, **kwargs):
                return Response('home sweet home')

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], 'http://localhost/login?redirect=%2F')

    def test_login_required_middleware(self):
        os.environ['USER_EMAIL'] = 'me@myself.com'
        os.environ['USER_ID'] = 'me'

        class MyHandler(HomeHandler):
            middleware = [LoginRequiredMiddleware()]

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 'home sweet home')

    def test_login_required_decorator(self):
        os.environ['USER_EMAIL'] = 'me@myself.com'
        os.environ['USER_ID'] = 'me'

        class MyHandler(HomeHandler):
            @login_required
            def get(self, **kwargs):
                return Response('home sweet home')

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 'home sweet home')

    def test_user_required_middleware_invalid(self):
        class MyHandler(HomeHandler):
            middleware = [UserRequiredMiddleware()]

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], 'http://localhost/login?redirect=%2F')

    def test_user_required_decorator_invalid(self):
        class MyHandler(HomeHandler):
            @user_required
            def get(self, **kwargs):
                return Response('home sweet home')

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], 'http://localhost/login?redirect=%2F')

    def test_user_required_middleware_logged_in(self):
        os.environ['USER_EMAIL'] = 'me@myself.com'
        os.environ['USER_ID'] = 'me'

        class MyHandler(HomeHandler):
            middleware = [UserRequiredMiddleware()]

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], 'http://localhost/signup?redirect=%2F')

    def test_user_required_decorator_logged_in(self):
        os.environ['USER_EMAIL'] = 'me@myself.com'
        os.environ['USER_ID'] = 'me'

        class MyHandler(HomeHandler):
            @user_required
            def get(self, **kwargs):
                return Response('home sweet home')

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], 'http://localhost/signup?redirect=%2F')

    def test_user_required_middleware_with_user(self):
        os.environ['USER_EMAIL'] = 'me@myself.com'
        os.environ['USER_ID'] = 'me'

        User.create('me', 'gae|me')

        class MyHandler(HomeHandler):
            middleware = [UserRequiredMiddleware()]

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 'home sweet home')

    def test_user_required_decorator_with_user(self):
        os.environ['USER_EMAIL'] = 'me@myself.com'
        os.environ['USER_ID'] = 'me'

        User.create('me', 'gae|me')

        class MyHandler(HomeHandler):
            @user_required
            def get(self, **kwargs):
                return Response('home sweet home')

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 'home sweet home')

    def test_user_required_if_authenticated_middleware(self):
        class MyHandler(HomeHandler):
            middleware = [UserRequiredIfAuthenticatedMiddleware()]

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 'home sweet home')

    def test_user_required_if_authenticate_decorator(self):
        class MyHandler(HomeHandler):
            @user_required_if_authenticated
            def get(self, **kwargs):
                return Response('home sweet home')

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 'home sweet home')

    def test_user_required_if_authenticated_middleware_logged_in(self):
        os.environ['USER_EMAIL'] = 'me@myself.com'
        os.environ['USER_ID'] = 'me'

        class MyHandler(HomeHandler):
            middleware = [UserRequiredIfAuthenticatedMiddleware()]

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], 'http://localhost/signup?redirect=%2F')

    def test_user_required_if_authenticate_decorator_logged_in(self):
        os.environ['USER_EMAIL'] = 'me@myself.com'
        os.environ['USER_ID'] = 'me'

        class MyHandler(HomeHandler):
            @user_required_if_authenticated
            def get(self, **kwargs):
                return Response('home sweet home')

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], 'http://localhost/signup?redirect=%2F')

    def test_user_required_if_authenticated_middleware_with_user(self):
        os.environ['USER_EMAIL'] = 'me@myself.com'
        os.environ['USER_ID'] = 'me'

        User.create('me', 'gae|me')

        class MyHandler(HomeHandler):
            middleware = [UserRequiredIfAuthenticatedMiddleware()]

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 'home sweet home')

    def test_user_required_if_authenticate_decorator_with_user(self):
        os.environ['USER_EMAIL'] = 'me@myself.com'
        os.environ['USER_ID'] = 'me'

        User.create('me', 'gae|me')

        class MyHandler(HomeHandler):
            @user_required_if_authenticated
            def get(self, **kwargs):
                return Response('home sweet home')

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 'home sweet home')

    def test_admin_required_middleware(self):
        class MyHandler(HomeHandler):
            middleware = [AdminRequiredMiddleware()]

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], 'http://localhost/login?redirect=%2F')

    def test_admin_required_decorator(self):
        class MyHandler(HomeHandler):
            @admin_required
            def get(self, **kwargs):
                return Response('home sweet home')

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], 'http://localhost/login?redirect=%2F')

    def test_admin_required_middleware_logged_in(self):
        os.environ['USER_EMAIL'] = 'me@myself.com'
        os.environ['USER_ID'] = 'me'

        class MyHandler(HomeHandler):
            middleware = [AdminRequiredMiddleware()]

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 403)

    def test_admin_required_decorator_logged_in(self):
        os.environ['USER_EMAIL'] = 'me@myself.com'
        os.environ['USER_ID'] = 'me'

        class MyHandler(HomeHandler):
            @admin_required
            def get(self, **kwargs):
                return Response('home sweet home')

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 403)

    def test_admin_required_middleware_with_user(self):
        os.environ['USER_EMAIL'] = 'me@myself.com'
        os.environ['USER_ID'] = 'me'

        User.create('me', 'gae|me')

        class MyHandler(HomeHandler):
            middleware = [AdminRequiredMiddleware()]

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 403)

    def test_admin_required_decorator_withd_user(self):
        os.environ['USER_EMAIL'] = 'me@myself.com'
        os.environ['USER_ID'] = 'me'

        User.create('me', 'gae|me')

        class MyHandler(HomeHandler):
            @admin_required
            def get(self, **kwargs):
                return Response('home sweet home')

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 403)

    def test_admin_required_middleware_with_admin(self):
        os.environ['USER_EMAIL'] = 'me@myself.com'
        os.environ['USER_ID'] = 'me'

        User.create('me', 'gae|me', is_admin=True)

        class MyHandler(HomeHandler):
            middleware = [AdminRequiredMiddleware()]

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 'home sweet home')

    def test_admin_required_decorator_with_admin(self):
        os.environ['USER_EMAIL'] = 'me@myself.com'
        os.environ['USER_ID'] = 'me'

        User.create('me', 'gae|me', is_admin=True)

        class MyHandler(HomeHandler):
            @admin_required
            def get(self, **kwargs):
                return Response('home sweet home')

        app = get_app()
        app.router.add(Rule('/', name='home', handler=MyHandler))
        client = app.get_test_client()

        response = client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 'home sweet home')


class TestUserModel(test_utils.BaseTestCase):
    def test_create(self):
        user = User.create('my_username', 'my_id')
        self.assertEqual(isinstance(user, User), True)

        # Second one will fail to be created.
        user = User.create('my_username', 'my_id')
        self.assertEqual(user, None)

    def test_create_with_password_hash(self):
        user = User.create('my_username', 'my_id', password_hash='foo')

        self.assertEqual(isinstance(user, User), True)
        self.assertEqual(user.password, 'foo')

    def test_create_with_password(self):
        user = User.create('my_username', 'my_id', password='foo')

        self.assertEqual(isinstance(user, User), True)
        self.assertNotEqual(user.password, 'foo')
        self.assertEqual(len(user.password.split('$')), 3)

    def test_set_password(self):
        user = User.create('my_username', 'my_id', password='foo')
        self.assertEqual(isinstance(user, User), True)

        password = user.password

        user.set_password('bar')
        self.assertNotEqual(user.password, password)

        self.assertNotEqual(user.password, 'bar')
        self.assertEqual(len(user.password.split('$')), 3)

    def test_check_password(self):
        app = Tipfy()
        request = Request.from_values('/')
        local.current_handler = RequestHandler(app, request)

        user = User.create('my_username', 'my_id', password='foo')

        self.assertEqual(user.check_password('foo'), True)
        self.assertEqual(user.check_password('bar'), False)

    def test_check_session(self):
        app = Tipfy()
        request = Request.from_values('/')
        local.current_handler = RequestHandler(app, request)

        user = User.create('my_username', 'my_id', password='foo')

        session_id = user.session_id
        self.assertEqual(user.check_session(session_id), True)
        self.assertEqual(user.check_session('bar'), False)

    def test_get_by_username(self):
        user = User.create('my_username', 'my_id')
        user_1 = User.get_by_username('my_username')

        self.assertEqual(isinstance(user, User), True)
        self.assertEqual(isinstance(user_1, User), True)
        self.assertEqual(str(user.key()), str(user_1.key()))

    def test_get_by_auth_id(self):
        user = User.create('my_username', 'my_id')
        user_1 = User.get_by_auth_id('my_id')

        self.assertEqual(isinstance(user, User), True)
        self.assertEqual(isinstance(user_1, User), True)
        self.assertEqual(str(user.key()), str(user_1.key()))

    def test_unicode(self):
        user_1 = User(username='Calvin', auth_id='test', session_id='test')
        self.assertEqual(unicode(user_1), u'Calvin')

    def test_str(self):
        user_1 = User(username='Hobbes', auth_id='test', session_id='test')
        self.assertEqual(str(user_1), u'Hobbes')

    def test_eq(self):
        user_1 = User(key_name='test', username='Calvin', auth_id='test', session_id='test')
        user_2 = User(key_name='test', username='Calvin', auth_id='test', session_id='test')

        self.assertEqual(user_1, user_2)
        self.assertNotEqual(user_1, '')

    def test_ne(self):
        user_1 = User(key_name='test', username='Calvin', auth_id='test', session_id='test')
        user_2 = User(key_name='test_2', username='Calvin', auth_id='test', session_id='test')

        self.assertEqual((user_1 != user_2), True)

    def test_renew_session(self):
        app = Tipfy()
        request = Request.from_values('/')
        local.current_handler = RequestHandler(app, request)

        user = User.create('my_username', 'my_id')
        user.renew_session(max_age=86400)

    def test_renew_session_force(self):
        app = Tipfy()
        user = User.create('my_username', 'my_id')
        user.renew_session(force=True, max_age=86400)


class TestMiscelaneous(test_utils.BaseTestCase):
    def test_create_session_id(self):
        self.assertEqual(len(create_session_id()), 32)


class TestMultiAuthStore(test_utils.BaseTestCase):
    def get_app(self):
        app = Tipfy(config={'tipfy.sessions': {
            'secret_key': 'secret',
        }})
        return app

    def test_login_with_form_invalid(self):
        with self.get_app().get_test_context() as request:
            store = MultiAuthStore(request)
            res = store.login_with_form('foo', 'bar', remember=True)
            self.assertEqual(res, False)

    def test_login_with_form(self):
        user = User.create('foo', 'foo_id', password='bar')
        with self.get_app().get_test_context() as request:
            store = MultiAuthStore(request)
            res = store.login_with_form('foo', 'bar', remember=True)
            self.assertEqual(res, True)

            res = store.login_with_form('foo', 'bar', remember=False)
            self.assertEqual(res, True)

    def test_login_with_auth_id(self):
        with self.get_app().get_test_context() as request:
            store = MultiAuthStore(request)
            store.login_with_auth_id('foo_id', remember=False)

            user = User.create('foo', 'foo_id', password='bar')
            app = self.get_app()
            store.login_with_auth_id('foo_id', remember=True)

    def test_real_login(self):
        user = User.create('foo', 'foo_id', auth_remember=True)
        with self.get_app().get_test_context() as request:
            store = MultiAuthStore(request)
            store.login_with_auth_id('foo_id', remember=False)

            response = Response()
            request.session_store.save(response)

        with self.get_app().get_test_context('/', headers={
            'Cookie': '\n'.join(response.headers.getlist('Set-Cookie')),
        }) as request:
            store = MultiAuthStore(request)
            self.assertNotEqual(store.user, None)
            self.assertEqual(store.user.username, 'foo')
            self.assertEqual(store.user.auth_id, 'foo_id')

    def test_real_logout(self):
        user = User.create('foo', 'foo_id', auth_remember=True)
        with self.get_app().get_test_context() as request:
            store = MultiAuthStore(request)
            store.login_with_auth_id('foo_id', remember=False)

            response = Response()
            request.session_store.save(response)

        with self.get_app().get_test_context('/', headers={
            'Cookie': '\n'.join(response.headers.getlist('Set-Cookie')),
        }) as request:
            store = MultiAuthStore(request)
            self.assertNotEqual(store.user, None)
            self.assertEqual(store.user.username, 'foo')
            store.logout()

            response = Response()
            request.session_store.save(response)

        with self.get_app().get_test_context('/', headers={
            'Cookie': '\n'.join(response.headers.getlist('Set-Cookie')),
        }) as request:
            store = MultiAuthStore(request)
            self.assertEqual(store.session, None)

    def test_real_login_no_user(self):
        with self.get_app().get_test_context() as request:
            store = MultiAuthStore(request)
            user = store.create_user('foo', 'foo_id')
            store.login_with_auth_id('foo_id', remember=False)

            response = Response()
            request.session_store.save(response)
            user.delete()

        with self.get_app().get_test_context('/', headers={
            'Cookie': '\n'.join(response.headers.getlist('Set-Cookie')),
        }) as request:
            store = MultiAuthStore(request)
            self.assertEqual(store.session['id'], 'foo_id')
            self.assertEqual(store.user, None)

    def test_real_login_invalid(self):
        with self.get_app().get_test_context() as request:
            store = MultiAuthStore(request)
            self.assertEqual(store.user, None)
            self.assertEqual(store.session, None)


if __name__ == '__main__':
    test_utils.main()

########NEW FILE########
__FILENAME__ = config_test
# -*- coding: utf-8 -*-
"""
Tests for tipfy config
"""
from __future__ import with_statement

import unittest

from tipfy import Tipfy, RequestHandler, REQUIRED_VALUE
from tipfy.app import local
from tipfy.config import Config

import test_utils


class TestConfig(test_utils.BaseTestCase):
    def test_get(self):
        config = Config({'foo': {
            'bar': 'baz',
            'doo': 'ding',
        }})

        self.assertEqual(config.get('foo'), {
            'bar': 'baz',
            'doo': 'ding',
        })

        self.assertEqual(config.get('bar'), {})

    def test_get_existing_keys(self):
        config = Config({'foo': {
            'bar': 'baz',
            'doo': 'ding',
        }})

        self.assertEqual(config.get_config('foo', 'bar'), 'baz')
        self.assertEqual(config.get_config('foo', 'doo'), 'ding')

    def test_get_existing_keys_from_default(self):
        config = Config({}, {'foo': {
            'bar': 'baz',
            'doo': 'ding',
        }})

        self.assertEqual(config.get_config('foo', 'bar'), 'baz')
        self.assertEqual(config.get_config('foo', 'doo'), 'ding')

    def test_get_non_existing_keys(self):
        config = Config()

        self.assertRaises(KeyError, config.get_config, 'foo', 'bar')

    def test_get_dict_existing_keys(self):
        config = Config({'foo': {
            'bar': 'baz',
            'doo': 'ding',
        }})

        self.assertEqual(config.get_config('foo'), {
            'bar': 'baz',
            'doo': 'ding',
        })

    def test_get_dict_non_existing_keys(self):
        config = Config()

        self.assertRaises(KeyError, config.get_config, 'bar')

    def test_get_with_default(self):
        config = Config()

        self.assertRaises(KeyError, config.get_config, 'foo', 'bar', 'ooops')
        self.assertRaises(KeyError, config.get_config, 'foo', 'doo', 'wooo')

    def test_get_with_default_and_none(self):
        config = Config({'foo': {
            'bar': None,
        }})

        self.assertEqual(config.get_config('foo', 'bar', 'ooops'), None)

    def test_update(self):
        config = Config({'foo': {
            'bar': 'baz',
            'doo': 'ding',
        }})

        self.assertEqual(config.get_config('foo', 'bar'), 'baz')
        self.assertEqual(config.get_config('foo', 'doo'), 'ding')

        config.update('foo', {'bar': 'other'})

        self.assertEqual(config.get_config('foo', 'bar'), 'other')
        self.assertEqual(config.get_config('foo', 'doo'), 'ding')

    def test_setdefault(self):
        config = Config()

        self.assertRaises(KeyError, config.get_config, 'foo')

        config.setdefault('foo', {
            'bar': 'baz',
            'doo': 'ding',
        })

        self.assertEqual(config.get_config('foo', 'bar'), 'baz')
        self.assertEqual(config.get_config('foo', 'doo'), 'ding')

    def test_setdefault2(self):
        config = Config({'foo': {
            'bar': 'baz',
        }})

        self.assertEqual(config.get_config('foo'), {
            'bar': 'baz',
        })

        config.setdefault('foo', {
            'bar': 'wooo',
            'doo': 'ding',
        })

        self.assertEqual(config.get_config('foo', 'bar'), 'baz')
        self.assertEqual(config.get_config('foo', 'doo'), 'ding')

    def test_setitem(self):
        config = Config()
        config['foo'] = {'bar': 'baz'}

        self.assertEqual(config, {'foo': {'bar': 'baz'}})
        self.assertEqual(config['foo'], {'bar': 'baz'})

    def test_init_no_dict_values(self):
        self.assertRaises(AssertionError, Config, {'foo': 'bar'})
        self.assertRaises(AssertionError, Config, {'foo': None})
        self.assertRaises(AssertionError, Config, 'foo')

    def test_init_no_dict_default(self):
        self.assertRaises(AssertionError, Config, {}, {'foo': 'bar'})
        self.assertRaises(AssertionError, Config, {}, {'foo': None})
        self.assertRaises(AssertionError, Config, {}, 'foo')

    def test_update_no_dict_values(self):
        config = Config()

        self.assertRaises(AssertionError, config.update, {'foo': 'bar'}, 'baz')
        self.assertRaises(AssertionError, config.update, {'foo': None}, 'baz')
        self.assertRaises(AssertionError, config.update, 'foo', 'bar')

    def test_setdefault_no_dict_values(self):
        config = Config()

        self.assertRaises(AssertionError, config.setdefault, 'foo', 'bar')
        self.assertRaises(AssertionError, config.setdefault, 'foo', None)

    def test_setitem_no_dict_values(self):
        config = Config()

        def setitem(key, value):
            config[key] = value
            return config

        self.assertRaises(AssertionError, setitem, 'foo', 'bar')
        self.assertRaises(AssertionError, setitem, 'foo', None)


class TestLoadConfig(test_utils.BaseTestCase):
    def test_default_config(self):
        config = Config()

        from resources.template import default_config as template_config
        from resources.i18n import default_config as i18n_config

        self.assertEqual(config.get_config('resources.template', 'templates_dir'), template_config['templates_dir'])
        self.assertEqual(config.get_config('resources.i18n', 'locale'), i18n_config['locale'])
        self.assertEqual(config.get_config('resources.i18n', 'timezone'), i18n_config['timezone'])

    def test_default_config_with_non_existing_key(self):
        config = Config()

        from resources.i18n import default_config as i18n_config

        # In the first time the module config will be loaded normally.
        self.assertEqual(config.get_config('resources.i18n', 'locale'), i18n_config['locale'])

        # In the second time it won't be loaded, but won't find the value and then use the default.
        self.assertEqual(config.get_config('resources.i18n', 'i_dont_exist', 'foo'), 'foo')

    def test_override_config(self):
        config = Config({
            'resources.template': {
                'templates_dir': 'apps/templates'
            },
            'resources.i18n': {
                'locale': 'pt_BR',
                'timezone': 'America/Sao_Paulo',
            },
        })

        self.assertEqual(config.get_config('resources.template', 'templates_dir'), 'apps/templates')
        self.assertEqual(config.get_config('resources.i18n', 'locale'), 'pt_BR')
        self.assertEqual(config.get_config('resources.i18n', 'timezone'), 'America/Sao_Paulo')

    def test_override_config2(self):
        config = Config({
            'resources.i18n': {
                'timezone': 'America/Sao_Paulo',
            },
        })

        self.assertEqual(config.get_config('resources.i18n', 'locale'), 'en_US')
        self.assertEqual(config.get_config('resources.i18n', 'timezone'), 'America/Sao_Paulo')

    def test_get(self):
        config = Config({'foo': {
            'bar': 'baz',
        }})

        self.assertEqual(config.get_config('foo', 'bar'), 'baz')

    def test_get_with_default(self):
        config = Config()

        self.assertEqual(config.get_config('resources.i18n', 'bar', 'baz'), 'baz')

    def test_get_with_default_and_none(self):
        config = Config({'foo': {
            'bar': None,
        }})

        self.assertEqual(config.get_config('foo', 'bar', 'ooops'), None)

    def test_get_with_default_and_module_load(self):
        config = Config()
        self.assertEqual(config.get_config('resources.i18n', 'locale'), 'en_US')
        self.assertEqual(config.get_config('resources.i18n', 'locale', 'foo'), 'en_US')

    def test_required_config(self):
        config = Config()
        self.assertRaises(KeyError, config.get_config, 'resources.i18n', 'foo')

    def test_missing_module(self):
        config = Config()
        self.assertRaises(KeyError, config.get_config, 'i_dont_exist', 'i_dont_exist')

    def test_missing_module2(self):
        config = Config()
        self.assertRaises(KeyError, config.get_config, 'i_dont_exist')

    def test_missing_key(self):
        config = Config()
        self.assertRaises(KeyError, config.get_config, 'resources.i18n', 'i_dont_exist')

    def test_missing_default_config(self):
        config = Config()
        self.assertRaises(KeyError, config.get_config, 'tipfy', 'foo')

    def test_request_handler_get_config(self):
        app = Tipfy()
        with app.get_test_context() as request:
            handler = RequestHandler(request)

            self.assertEqual(handler.get_config('resources.i18n', 'locale'), 'en_US')
            self.assertEqual(handler.get_config('resources.i18n', 'locale', 'foo'), 'en_US')
            self.assertEqual(handler.get_config('resources.i18n'), {
                'locale': 'en_US',
                'timezone': 'America/Chicago',
                'required': REQUIRED_VALUE,
            })


class TestLoadConfigGetItem(test_utils.BaseTestCase):
    def test_default_config(self):
        config = Config()

        from resources.template import default_config as template_config
        from resources.i18n import default_config as i18n_config

        self.assertEqual(config['resources.template']['templates_dir'], template_config['templates_dir'])
        self.assertEqual(config['resources.i18n']['locale'], i18n_config['locale'])
        self.assertEqual(config['resources.i18n']['timezone'], i18n_config['timezone'])

    def test_default_config_with_non_existing_key(self):
        config = Config()

        from resources.i18n import default_config as i18n_config

        # In the first time the module config will be loaded normally.
        self.assertEqual(config['resources.i18n']['locale'], i18n_config['locale'])

        # In the second time it won't be loaded, but won't find the value and then use the default.
        self.assertEqual(config['resources.i18n'].get('i_dont_exist', 'foo'), 'foo')

    def test_override_config(self):
        config = Config({
            'resources.template': {
                'templates_dir': 'apps/templates'
            },
            'resources.i18n': {
                'locale': 'pt_BR',
                'timezone': 'America/Sao_Paulo',
            },
        })

        self.assertEqual(config['resources.template']['templates_dir'], 'apps/templates')
        self.assertEqual(config['resources.i18n']['locale'], 'pt_BR')
        self.assertEqual(config['resources.i18n']['timezone'], 'America/Sao_Paulo')

    def test_override_config2(self):
        config = Config({
            'resources.i18n': {
                'timezone': 'America/Sao_Paulo',
            },
        })

        self.assertEqual(config['resources.i18n']['locale'], 'en_US')
        self.assertEqual(config['resources.i18n']['timezone'], 'America/Sao_Paulo')

    def test_get(self):
        config = Config({'foo': {
            'bar': 'baz',
        }})

        self.assertEqual(config['foo']['bar'], 'baz')

    def test_get_with_default(self):
        config = Config()

        self.assertEqual(config['resources.i18n'].get('bar', 'baz'), 'baz')

    def test_get_with_default_and_none(self):
        config = Config({'foo': {
            'bar': None,
        }})

        self.assertEqual(config['foo'].get('bar', 'ooops'), None)

    def test_get_with_default_and_module_load(self):
        config = Config()
        self.assertEqual(config['resources.i18n']['locale'], 'en_US')
        self.assertEqual(config['resources.i18n'].get('locale', 'foo'), 'en_US')

    def test_required_config(self):
        config = Config()
        self.assertRaises(KeyError, config['resources.i18n'].__getitem__, 'foo')
        self.assertRaises(KeyError, config['resources.i18n'].__getitem__, 'required')

    def test_missing_module(self):
        config = Config()
        self.assertRaises(KeyError, config.__getitem__, 'i_dont_exist')

    def test_missing_key(self):
        config = Config()
        self.assertRaises(KeyError, config['resources.i18n'].__getitem__, 'i_dont_exist')

    def test_missing_default_config(self):
        config = Config()
        self.assertRaises(KeyError, config['tipfy'].__getitem__, 'foo')


class TestGetConfig(test_utils.BaseTestCase):
    '''
    def test_get_config(self):
        app = Tipfy()
        self.assertEqual(get_config('resources.i18n', 'locale'), 'en_US')
    '''


if __name__ == '__main__':
    test_utils.main()

########NEW FILE########
__FILENAME__ = ext_jinja2_test
# -*- coding: utf-8 -*-
"""
    Tests for tipfyext.jinja2
"""
import os
import sys
import unittest

from jinja2 import FileSystemLoader, Environment

from tipfy import RequestHandler, Request, Response, Tipfy
from tipfy.app import local
from tipfyext.jinja2 import Jinja2, Jinja2Mixin

import test_utils

current_dir = os.path.abspath(os.path.dirname(__file__))
templates_dir = os.path.join(current_dir, 'resources', 'templates')
templates_compiled_target = os.path.join(current_dir, 'resources', 'templates_compiled')


class TestJinja2(test_utils.BaseTestCase):
    def test_render_template(self):
        app = Tipfy(config={'tipfyext.jinja2': {'templates_dir': templates_dir}})
        local.request = Request.from_values()
        local.request.app = app
        handler = RequestHandler(local.request)
        jinja2 = Jinja2(app)

        message = 'Hello, World!'
        res = jinja2.render_template(handler, 'template1.html', message=message)
        self.assertEqual(res, message)

    def test_render_template_with_i18n(self):
        app = Tipfy(config={
            'tipfyext.jinja2': {
                'templates_dir': templates_dir,
                'environment_args': dict(
                    autoescape=True,
                    extensions=['jinja2.ext.autoescape', 'jinja2.ext.with_', 'jinja2.ext.i18n'],
                ),
            },
            'tipfy.sessions': {
                'secret_key': 'secret',
            },
        })
        local.request = Request.from_values()
        local.request.app = app
        handler = RequestHandler(local.request)
        jinja2 = Jinja2(app)

        message = 'Hello, i18n World!'
        res = jinja2.render_template(handler, 'template2.html', message=message)
        self.assertEqual(res, message)

    def test_render_response(self):
        app = Tipfy(config={'tipfyext.jinja2': {'templates_dir': templates_dir}})
        local.request = Request.from_values()
        local.request.app = app
        handler = RequestHandler(local.request)
        jinja2 = Jinja2(app)

        message = 'Hello, World!'
        response = jinja2.render_response(handler, 'template1.html', message=message)
        self.assertEqual(isinstance(response, Response), True)
        self.assertEqual(response.mimetype, 'text/html')
        self.assertEqual(response.data, message)

    def test_render_response_force_compiled(self):
        app = Tipfy(config={
            'tipfyext.jinja2': {
                'templates_compiled_target': templates_compiled_target,
                'force_use_compiled': True,
            }
        }, debug=False)
        local.request = Request.from_values()
        local.request.app = app
        handler = RequestHandler(local.request)
        jinja2 = Jinja2(app)

        message = 'Hello, World!'
        response = jinja2.render_response(handler, 'template1.html', message=message)
        self.assertEqual(isinstance(response, Response), True)
        self.assertEqual(response.mimetype, 'text/html')
        self.assertEqual(response.data, message)

    def test_jinja2_mixin_render_template(self):
        class MyHandler(RequestHandler, Jinja2Mixin):
            pass

        app = Tipfy(config={'tipfyext.jinja2': {'templates_dir': templates_dir}})
        local.request = Request.from_values()
        local.request.app = app
        handler = MyHandler(local.request)
        jinja2 = Jinja2(app)
        message = 'Hello, World!'

        response = handler.render_template('template1.html', message=message)
        self.assertEqual(response, message)

    def test_jinja2_mixin_render_response(self):
        class MyHandler(RequestHandler, Jinja2Mixin):
            pass

        app = Tipfy(config={'tipfyext.jinja2': {'templates_dir': templates_dir}})
        local.request = Request.from_values()
        local.request.app = app
        handler = MyHandler(local.request)
        jinja2 = Jinja2(app)
        message = 'Hello, World!'

        response = handler.render_response('template1.html', message=message)
        self.assertEqual(isinstance(response, Response), True)
        self.assertEqual(response.mimetype, 'text/html')
        self.assertEqual(response.data, message)

    def test_get_template_attribute(self):
        app = Tipfy(config={'tipfyext.jinja2': {'templates_dir': templates_dir}})
        local.request = Request.from_values()
        local.request.app = app
        handler = RequestHandler(local.request)
        jinja2 = Jinja2(app)

        hello = jinja2.get_template_attribute('hello.html', 'hello')
        self.assertEqual(hello('World'), 'Hello, World!')

    def test_engine_factory(self):
        def get_jinja2_env():
            app = handler.app
            cfg = app.get_config('tipfyext.jinja2')

            loader = FileSystemLoader(cfg.get( 'templates_dir'))

            return Environment(loader=loader)

        app = Tipfy(config={'tipfyext.jinja2': {
            'templates_dir': templates_dir,
            'engine_factory': get_jinja2_env,
        }})
        local.request = Request.from_values()
        local.request.app = app
        handler = RequestHandler(local.request)
        jinja2 = Jinja2(app)

        message = 'Hello, World!'
        res = jinja2.render_template(handler, 'template1.html', message=message)
        self.assertEqual(res, message)

    def test_engine_factory2(self):
        old_sys_path = sys.path[:]
        sys.path.insert(0, current_dir)

        app = Tipfy(config={'tipfyext.jinja2': {
            'templates_dir': templates_dir,
            'engine_factory': 'resources.get_jinja2_env',
        }})
        local.request = Request.from_values()
        local.request.app = app
        handler = RequestHandler(local.request)
        jinja2 = Jinja2(app)

        message = 'Hello, World!'
        res = jinja2.render_template(handler, 'template1.html', message=message)
        self.assertEqual(res, message)

        sys.path = old_sys_path

    def test_engine_factory3(self):
        app = Tipfy()
        local.request = Request.from_values()
        local.request.app = app
        handler = RequestHandler(local.request)
        _globals = {'message': 'Hey there!'}
        filters = {'ho': lambda e: e + ' Ho!'}
        jinja2 = Jinja2(app, _globals=_globals, filters=filters)

        template = jinja2.environment.from_string("""{{ message|ho }}""")

        self.assertEqual(template.render(), 'Hey there! Ho!')

    def test_after_environment_created(self):
        def after_creation(environment):
            environment.filters['ho'] = lambda x: x + ', Ho!'

        app = Tipfy(config={'tipfyext.jinja2': {'after_environment_created': after_creation}})
        local.request = Request.from_values()
        local.request.app = app
        handler = RequestHandler(local.request)
        jinja2 = Jinja2(app)

        template = jinja2.environment.from_string("""{{ 'Hey'|ho }}""")
        self.assertEqual(template.render(), 'Hey, Ho!')

    def test_after_environment_created_using_string(self):
        app = Tipfy(config={'tipfyext.jinja2': {'after_environment_created': 'resources.jinja2_after_environment_created.after_creation'}})
        local.request = Request.from_values()
        local.request.app = app
        handler = RequestHandler(local.request)
        jinja2 = Jinja2(app)

        template = jinja2.environment.from_string("""{{ 'Hey'|ho }}""")
        self.assertEqual(template.render(), 'Hey, Ho!')

    def test_translations(self):
        app = Tipfy(config={
            'tipfyext.jinja2': {
                'environment_args': {
                    'extensions': ['jinja2.ext.i18n',],
                },
            },
            'tipfy.sessions': {
                'secret_key': 'foo',
            },
        })
        local.request = Request.from_values()
        local.request.app = app
        handler = RequestHandler(local.request)
        jinja2 = Jinja2(app)

        template = jinja2.environment.from_string("""{{ _('foo = %(bar)s', bar='foo') }}""")
        self.assertEqual(template.render(), 'foo = foo')


if __name__ == '__main__':
    test_utils.main()

########NEW FILE########
__FILENAME__ = ext_mako_test
# -*- coding: utf-8 -*-
"""
    Tests for tipfyext.mako
"""
import os
import sys
import unittest

from tipfy import RequestHandler, Request, Response, Tipfy
from tipfy.app import local
from tipfyext.mako import Mako, MakoMixin

import test_utils

current_dir = os.path.abspath(os.path.dirname(__file__))
templates_dir = os.path.join(current_dir, 'resources', 'mako_templates')


class TestMako(test_utils.BaseTestCase):
    def test_render_template(self):
        app = Tipfy(config={'tipfyext.mako': {'templates_dir': templates_dir}})
        request = Request.from_values()
        handler = RequestHandler(app, request)
        mako = Mako(app)

        message = 'Hello, World!'
        res = mako.render_template(handler, 'template1.html', message=message)
        self.assertEqual(res, message + '\n')

    def test_render_response(self):
        app = Tipfy(config={'tipfyext.mako': {'templates_dir': templates_dir}})
        request = Request.from_values()
        handler = RequestHandler(app, request)
        mako = Mako(app)

        message = 'Hello, World!'
        response = mako.render_response(handler, 'template1.html', message=message)
        self.assertEqual(isinstance(response, Response), True)
        self.assertEqual(response.mimetype, 'text/html')
        self.assertEqual(response.data, message + '\n')

    def test_mako_mixin_render_template(self):
        class MyHandler(RequestHandler, MakoMixin):
            def __init__(self, app, request):
                self.app = app
                self.request = request
                self.context = {}

        app = Tipfy(config={'tipfyext.mako': {'templates_dir': templates_dir}})
        request = Request.from_values()
        handler = MyHandler(app, request)
        mako = Mako(app)
        message = 'Hello, World!'

        response = handler.render_template('template1.html', message=message)
        self.assertEqual(response, message + '\n')

    def test_mako_mixin_render_response(self):
        class MyHandler(RequestHandler, MakoMixin):
            def __init__(self, app, request):
                self.app = app
                self.request = request
                self.context = {}

        app = Tipfy(config={'tipfyext.mako': {'templates_dir': templates_dir}})
        request = Request.from_values()
        handler = MyHandler(app, request)
        mako = Mako(app)
        message = 'Hello, World!'

        response = handler.render_response('template1.html', message=message)
        self.assertEqual(isinstance(response, Response), True)
        self.assertEqual(response.mimetype, 'text/html')
        self.assertEqual(response.data, message + '\n')


if __name__ == '__main__':
    test_utils.main()

########NEW FILE########
__FILENAME__ = gae_acl_test
# -*- coding: utf-8 -*-
"""
    Tests for tipfy.appengine.acl
"""
import unittest

from google.appengine.api import memcache

from tipfy import Tipfy, Request, RequestHandler, CURRENT_VERSION_ID
from tipfy.app import local
from tipfy.appengine.acl import Acl, AclRules, _rules_map, AclMixin

from tipfy.app import local

import test_utils


class TestAcl(test_utils.BaseTestCase):
    def setUp(self):
        # Clean up datastore.
        super(TestAcl, self).setUp()

        self.app = Tipfy()
        self.app.config['tipfy']['dev'] = False
        local.request = Request.from_values()
        local.request.app = self.app

        Acl.roles_map = {}
        Acl.roles_lock = CURRENT_VERSION_ID
        _rules_map.clear()
        test_utils.BaseTestCase.setUp(self)

    def tearDown(self):
        self.app.config['tipfy']['dev'] = True

        Acl.roles_map = {}
        Acl.roles_lock = CURRENT_VERSION_ID
        _rules_map.clear()
        test_utils.BaseTestCase.tearDown(self)

    def test_test_insert_or_update(self):
        user_acl = AclRules.get_by_area_and_user('test', 'test')
        self.assertEqual(user_acl, None)

        # Set empty rules.
        user_acl = AclRules.insert_or_update(area='test', user='test')
        user_acl = AclRules.get_by_area_and_user('test', 'test')
        self.assertNotEqual(user_acl, None)
        self.assertEqual(user_acl.rules, [])
        self.assertEqual(user_acl.roles, [])

        rules = [
            ('topic_1', 'name_1', True),
            ('topic_1', 'name_2', True),
            ('topic_2', 'name_1', False),
        ]

        user_acl = AclRules.insert_or_update(area='test', user='test', rules=rules)
        user_acl = AclRules.get_by_area_and_user('test', 'test')
        self.assertNotEqual(user_acl, None)
        self.assertEqual(user_acl.rules, rules)
        self.assertEqual(user_acl.roles, [])

        extra_rule = ('topic_3', 'name_3', True)
        rules.append(extra_rule)

        user_acl = AclRules.insert_or_update(area='test', user='test', rules=rules, roles=['foo', 'bar', 'baz'])
        user_acl = AclRules.get_by_area_and_user('test', 'test')
        self.assertNotEqual(user_acl, None)
        self.assertEqual(user_acl.rules, rules)
        self.assertEqual(user_acl.roles, ['foo', 'bar', 'baz'])

    def test_set_rules(self):
        """Test setting and appending rules."""
        rules = [
            ('topic_1', 'name_1', True),
            ('topic_1', 'name_2', True),
            ('topic_2', 'name_1', False),
        ]
        extra_rule = ('topic_3', 'name_3', True)

        # Set empty rules.
        user_acl = AclRules.insert_or_update(area='test', user='test')

        # Set rules and save the record.
        user_acl = AclRules.insert_or_update(area='test', user='test', rules=rules)

        # Fetch the record again, and compare.
        user_acl = AclRules.get_by_area_and_user('test', 'test')
        self.assertEqual(user_acl.rules, rules)

        # Append more rules.
        user_acl.rules.append(extra_rule)
        user_acl.put()
        rules.append(extra_rule)

        # Fetch the record again, and compare.
        user_acl = AclRules.get_by_area_and_user('test', 'test')
        self.assertEqual(user_acl.rules, rules)

    def test_delete_rules(self):
        rules = [
            ('topic_1', 'name_1', True),
            ('topic_1', 'name_2', True),
            ('topic_2', 'name_1', False),
        ]
        user_acl = AclRules.insert_or_update(area='test', user='test', rules=rules)

        # Fetch the record again, and compare.
        user_acl = AclRules.get_by_area_and_user('test', 'test')
        self.assertEqual(user_acl.rules, rules)

        key_name = AclRules.get_key_name('test', 'test')
        acl = Acl('test', 'test')

        cached = memcache.get(key_name, namespace=AclRules.__name__)
        self.assertEqual(key_name in _rules_map, True)
        self.assertEqual(cached, _rules_map[key_name])

        user_acl.delete()
        user_acl2 = AclRules.get_by_area_and_user('test', 'test')

        cached = memcache.get(key_name, namespace=AclRules.__name__)
        self.assertEqual(user_acl2, None)
        self.assertEqual(key_name not in _rules_map, True)
        self.assertEqual(cached, None)

    def test_is_rule_set(self):
        rules = [
            ('topic_1', 'name_1', True),
            ('topic_1', 'name_2', True),
            ('topic_2', 'name_1', False),
        ]
        user_acl = AclRules.insert_or_update(area='test', user='test', rules=rules)

        # Fetch the record again, and compare.
        user_acl = AclRules.get_by_area_and_user('test', 'test')

        self.assertEqual(user_acl.is_rule_set(*rules[0]), True)
        self.assertEqual(user_acl.is_rule_set(*rules[1]), True)
        self.assertEqual(user_acl.is_rule_set(*rules[2]), True)
        self.assertEqual(user_acl.is_rule_set('topic_1', 'name_3', True), False)

    def test_no_area_or_no_user(self):
        acl1 = Acl('foo', None)
        acl2 = Acl(None, 'foo')

        self.assertEqual(acl1.has_any_access(), False)
        self.assertEqual(acl2.has_any_access(), False)

    def test_default_roles_lock(self):
        Acl.roles_lock = None
        acl2 = Acl('foo', 'foo')

        self.assertEqual(acl2.roles_lock, CURRENT_VERSION_ID)

    def test_set_invalid_rules(self):
        rules = {}
        self.assertRaises(AssertionError, AclRules.insert_or_update, area='test', user='test', rules=rules)

        rules = ['foo', 'bar', True]
        self.assertRaises(AssertionError, AclRules.insert_or_update, area='test', user='test', rules=rules)

        rules = [('foo',)]
        self.assertRaises(AssertionError, AclRules.insert_or_update, area='test', user='test', rules=rules)

        rules = [('foo', 'bar')]
        self.assertRaises(AssertionError, AclRules.insert_or_update, area='test', user='test', rules=rules)

        rules = [(1, 2, 3)]
        self.assertRaises(AssertionError, AclRules.insert_or_update, area='test', user='test', rules=rules)

        rules = [('foo', 'bar', True)]
        AclRules.insert_or_update(area='test', user='test', rules=rules)
        user_acl = AclRules.get_by_area_and_user('test', 'test')
        user_acl.rules.append((1, 2, 3))
        self.assertRaises(AssertionError, user_acl.put)

    def test_example(self):
        """Tests the example set in the acl module."""
        # Set a dict of roles with an 'admin' role that has full access and assign
        # users to it. Each role maps to a list of rules. Each rule, a tuple
        # (topic, name, flag), where flag, as bool to allow or disallow access.
        # Wildcard '*' can be used to match all topics and/or names.
        Acl.roles_map = {
            'admin': [
                ('*', '*', True),
            ],
        }

        # Assign users 'user_1' and 'user_2' to the 'admin' role.
        AclRules.insert_or_update(area='my_area', user='user_1', roles=['admin'])
        AclRules.insert_or_update(area='my_area', user='user_2', roles=['admin'])

        # Restrict 'user_2' from accessing a specific resource, adding a new rule
        # with flag set to False. Now this user has access to everything except this
        # resource.
        user_acl = AclRules.get_by_area_and_user('my_area', 'user_2')
        user_acl.rules.append(('UserAdmin', '*', False))
        user_acl.put()

        # Check 'user_2' permission.
        acl = Acl(area='my_area', user='user_2')
        self.assertEqual(acl.has_access(topic='UserAdmin', name='save'), False)
        self.assertEqual(acl.has_access(topic='UserAdmin', name='get'), False)
        self.assertEqual(acl.has_access(topic='AnythingElse', name='put'), True)

    def test_is_one(self):
        AclRules.insert_or_update(area='my_area', user='user_1', roles=['editor', 'designer'])

        acl = Acl(area='my_area', user='user_1')
        self.assertEqual(acl.is_one('editor'), True)
        self.assertEqual(acl.is_one('designer'), True)
        self.assertEqual(acl.is_one('admin'), False)

    def test_is_any(self):
        AclRules.insert_or_update(area='my_area', user='user_1', roles=['editor', 'designer'])

        acl = Acl(area='my_area', user='user_1')
        self.assertEqual(acl.is_any(['editor', 'admin']), True)
        self.assertEqual(acl.is_any(['admin', 'designer']), True)
        self.assertEqual(acl.is_any(['admin', 'user']), False)

    def test_is_all(self):
        AclRules.insert_or_update(area='my_area', user='user_1', roles=['editor', 'designer'])

        acl = Acl(area='my_area', user='user_1')
        self.assertEqual(acl.is_all(['editor', 'admin']), False)
        self.assertEqual(acl.is_all(['admin', 'designer']), False)
        self.assertEqual(acl.is_all(['admin', 'user']), False)
        self.assertEqual(acl.is_all(['editor', 'designer']), True)

    def test_non_existent_user(self):
        acl = Acl(area='my_area', user='user_3')
        self.assertEqual(acl.has_any_access(), False)

    def test_has_any_access(self):
        AclRules.insert_or_update(area='my_area', user='user_1', roles=['editor', 'designer'])
        AclRules.insert_or_update(area='my_area', user='user_2', rules=[('*', '*', True)])
        AclRules.insert_or_update(area='my_area', user='user_3')

        acl = Acl(area='my_area', user='user_1')
        self.assertEqual(acl.has_any_access(), True)

        acl = Acl(area='my_area', user='user_2')
        self.assertEqual(acl.has_any_access(), True)

        acl = Acl(area='my_area', user='user_3')
        self.assertEqual(acl.has_any_access(), False)
        self.assertEqual(acl._rules, [])
        self.assertEqual(acl._roles, [])

    def test_has_access_invalid_parameters(self):
        AclRules.insert_or_update(area='my_area', user='user_1', rules=[('*', '*', True)])

        acl1 = Acl(area='my_area', user='user_1')

        self.assertRaises(ValueError, acl1.has_access, 'content', '*')
        self.assertRaises(ValueError, acl1.has_access, '*', 'content')

    def test_has_access(self):
        AclRules.insert_or_update(area='my_area', user='user_1', rules=[('*', '*', True)])
        AclRules.insert_or_update(area='my_area', user='user_2', rules=[('content', '*', True), ('content', 'delete', False)])
        AclRules.insert_or_update(area='my_area', user='user_3', rules=[('content', 'read', True)])

        acl1 = Acl(area='my_area', user='user_1')
        acl2 = Acl(area='my_area', user='user_2')
        acl3 = Acl(area='my_area', user='user_3')

        self.assertEqual(acl1.has_access('content', 'read'), True)
        self.assertEqual(acl1.has_access('content', 'update'), True)
        self.assertEqual(acl1.has_access('content', 'delete'), True)

        self.assertEqual(acl2.has_access('content', 'read'), True)
        self.assertEqual(acl2.has_access('content', 'update'), True)
        self.assertEqual(acl2.has_access('content', 'delete'), False)

        self.assertEqual(acl3.has_access('content', 'read'), True)
        self.assertEqual(acl3.has_access('content', 'update'), False)
        self.assertEqual(acl3.has_access('content', 'delete'), False)

    def test_has_access_with_roles(self):
        Acl.roles_map = {
            'admin':       [('*', '*', True),],
            'editor':      [('content', '*', True),],
            'contributor': [('content', '*', True), ('content', 'delete', False)],
            'designer':    [('design', '*', True),],
        }

        AclRules.insert_or_update(area='my_area', user='user_1', roles=['admin'])
        acl1 = Acl(area='my_area', user='user_1')

        AclRules.insert_or_update(area='my_area', user='user_2', roles=['admin'], rules=[('ManageUsers', '*', False)])
        acl2 = Acl(area='my_area', user='user_2')

        AclRules.insert_or_update(area='my_area', user='user_3', roles=['editor'])
        acl3 = Acl(area='my_area', user='user_3')

        AclRules.insert_or_update(area='my_area', user='user_4', roles=['contributor'], rules=[('design', '*', True),])
        acl4 = Acl(area='my_area', user='user_4')

        self.assertEqual(acl1.has_access('ApproveUsers', 'save'), True)
        self.assertEqual(acl1.has_access('ManageUsers', 'edit'), True)
        self.assertEqual(acl1.has_access('ManageUsers', 'delete'), True)

        self.assertEqual(acl1.has_access('ApproveUsers', 'save'), True)
        self.assertEqual(acl2.has_access('ManageUsers', 'edit'), False)
        self.assertEqual(acl2.has_access('ManageUsers', 'delete'), False)

        self.assertEqual(acl3.has_access('ApproveUsers', 'save'), False)
        self.assertEqual(acl3.has_access('ManageUsers', 'edit'), False)
        self.assertEqual(acl3.has_access('ManageUsers', 'delete'), False)
        self.assertEqual(acl3.has_access('content', 'edit'), True)
        self.assertEqual(acl3.has_access('content', 'delete'), True)
        self.assertEqual(acl3.has_access('content', 'save'), True)
        self.assertEqual(acl3.has_access('design', 'edit'), False)
        self.assertEqual(acl3.has_access('design', 'delete'), False)

        self.assertEqual(acl4.has_access('ApproveUsers', 'save'), False)
        self.assertEqual(acl4.has_access('ManageUsers', 'edit'), False)
        self.assertEqual(acl4.has_access('ManageUsers', 'delete'), False)
        self.assertEqual(acl4.has_access('content', 'edit'), True)
        self.assertEqual(acl4.has_access('content', 'delete'), False)
        self.assertEqual(acl4.has_access('content', 'save'), True)
        self.assertEqual(acl4.has_access('design', 'edit'), True)
        self.assertEqual(acl4.has_access('design', 'delete'), True)

    def test_roles_lock_unchanged(self):
        roles_map1 = {
            'editor':      [('content', '*', True),],
            'contributor': [('content', '*', True), ('content', 'delete', False)],
        }
        Acl.roles_map = roles_map1
        Acl.roles_lock = 'initial'

        AclRules.insert_or_update(area='my_area', user='user_1', roles=['editor'])
        acl1 = Acl(area='my_area', user='user_1')

        AclRules.insert_or_update(area='my_area', user='user_2', roles=['contributor'])
        acl2 = Acl(area='my_area', user='user_2')

        self.assertEqual(acl1.has_access('content', 'add'), True)
        self.assertEqual(acl1.has_access('content', 'edit'), True)
        self.assertEqual(acl1.has_access('content', 'delete'), True)

        self.assertEqual(acl2.has_access('content', 'add'), True)
        self.assertEqual(acl2.has_access('content', 'edit'), True)
        self.assertEqual(acl2.has_access('content', 'delete'), False)

        roles_map2 = {
            'editor':      [('content', '*', True),],
            'contributor': [('content', '*', True), ('content', 'delete', False), ('content', 'add', False)],
        }
        Acl.roles_map = roles_map2
        # Don't change the lock to check that the cache will be kept.
        # Acl.roles_lock = 'changed'

        acl1 = Acl(area='my_area', user='user_1')
        acl2 = Acl(area='my_area', user='user_2')

        self.assertEqual(acl1.has_access('content', 'add'), True)
        self.assertEqual(acl1.has_access('content', 'edit'), True)
        self.assertEqual(acl1.has_access('content', 'delete'), True)

        self.assertEqual(acl2.has_access('content', 'add'), True)
        self.assertEqual(acl2.has_access('content', 'edit'), True)
        self.assertEqual(acl2.has_access('content', 'delete'), False)

    def test_roles_lock_changed(self):
        roles_map1 = {
            'editor':      [('content', '*', True),],
            'contributor': [('content', '*', True), ('content', 'delete', False)],
        }
        Acl.roles_map = roles_map1
        Acl.roles_lock = 'initial'

        AclRules.insert_or_update(area='my_area', user='user_1', roles=['editor'])
        acl1 = Acl(area='my_area', user='user_1')

        AclRules.insert_or_update(area='my_area', user='user_2', roles=['contributor'])
        acl2 = Acl(area='my_area', user='user_2')

        self.assertEqual(acl1.has_access('content', 'add'), True)
        self.assertEqual(acl1.has_access('content', 'edit'), True)
        self.assertEqual(acl1.has_access('content', 'delete'), True)

        self.assertEqual(acl2.has_access('content', 'add'), True)
        self.assertEqual(acl2.has_access('content', 'edit'), True)
        self.assertEqual(acl2.has_access('content', 'delete'), False)

        roles_map2 = {
            'editor':      [('content', '*', True),],
            'contributor': [('content', '*', True), ('content', 'delete', False), ('content', 'add', False)],
        }
        Acl.roles_map = roles_map2
        Acl.roles_lock = 'changed'

        acl1 = Acl(area='my_area', user='user_1')
        acl2 = Acl(area='my_area', user='user_2')

        self.assertEqual(acl1.has_access('content', 'add'), True)
        self.assertEqual(acl1.has_access('content', 'edit'), True)
        self.assertEqual(acl1.has_access('content', 'delete'), True)

        self.assertEqual(acl2.has_access('content', 'add'), False)
        self.assertEqual(acl2.has_access('content', 'edit'), True)
        self.assertEqual(acl2.has_access('content', 'delete'), False)

    def test_acl_mixin(self):
        roles_map1 = {
            'editor':      [('content', '*', True),],
            'contributor': [('content', '*', True), ('content', 'delete', False)],
        }
        AclRules.insert_or_update(area='my_area', user='user_1', roles=['editor'])

        class Area(object):
            def key(self):
                return 'my_area'

        class User(object):
            def key(self):
                return 'user_1'

        class MyHandler(AclMixin):
            roles_map = roles_map1
            roles_lock = 'foo'

            def __init__(self):
                self.area = Area()
                self.current_user = User()

        handler = MyHandler()
        self.assertEqual(handler.acl.has_access('content', 'add'), True)
        self.assertEqual(handler.acl.has_access('content', 'edit'), True)
        self.assertEqual(handler.acl.has_access('content', 'delete'), True)
        self.assertEqual(handler.acl.has_access('foo', 'delete'), False)


if __name__ == '__main__':
    test_utils.main()

########NEW FILE########
__FILENAME__ = gae_blobstore_test
# -*- coding: utf-8 -*-
"""
    Tests for tipfy.appengine.blobstore
"""
import datetime
import decimal
import email
import StringIO
import time
import unittest

from google.appengine.ext import blobstore

from tipfy.appengine.blobstore import (CreationFormatError, parse_blob_info,
    parse_creation)

from werkzeug import FileStorage

import test_utils


class TestParseCreation(test_utils.BaseTestCase):
    """YYYY-mm-dd HH:MM:SS.ffffff"""
    def test_invalid_format(self):
        self.assertRaises(CreationFormatError, parse_creation, '2010-05-20 6:20:35', 'my_field_name')

    def test_invalid_format2(self):
        self.assertRaises(CreationFormatError, parse_creation, '2010-05-20 6:20:35.1234.5678', 'my_field_name')

    def test_invalid_format3(self):
        self.assertRaises(CreationFormatError, parse_creation, 'youcannot.parseme', 'my_field_name')

    def test_parse(self):
        timestamp = time.time()
        parts = str(timestamp).split('.', 1)
        ms = parts[1][:4]
        timestamp = decimal.Decimal(parts[0] + '.' + ms)
        curr_date = datetime.datetime.fromtimestamp(timestamp)

        to_convert = '%s.%s' % (curr_date.strftime('%Y-%m-%d %H:%M:%S'), ms)

        res = parse_creation(to_convert, 'my_field_name')

        self.assertEqual(res.timetuple(), curr_date.timetuple())



class TestParseBlobInfo(test_utils.BaseTestCase):
    def test_none(self):
        self.assertEqual(parse_blob_info(None, 'my_field_name'), None)

    def test_file(self):
        stream = StringIO.StringIO()
        stream.write("""\
Content-Type: application/octet-stream
Content-Length: 1
X-AppEngine-Upload-Creation: 2010-10-01 05:34:00.000000
""")
        stream.seek(0)
        headers = {}
        headers['Content-Type'] = 'image/png; blob-key=foo'

        f = FileStorage(stream=stream, headers=headers)
        self.assertNotEqual(parse_blob_info(f, 'my_field_name'), None)

    def test_invalid_size(self):
        stream = StringIO.StringIO()
        stream.write("""\
Content-Type: application/octet-stream
Content-Length: zzz
X-AppEngine-Upload-Creation: 2010-10-01 05:34:00.000000
""")
        stream.seek(0)
        headers = {}
        headers['Content-Type'] = 'image/png; blob-key=foo'

        f = FileStorage(stream=stream, headers=headers)
        self.assertRaises(blobstore.BlobInfoParseError, parse_blob_info,f, 'my_field_name')

    def test_invalid_CREATION(self):
        stream = StringIO.StringIO()
        stream.write("""\
Content-Type: application/octet-stream
Content-Length: 1
X-AppEngine-Upload-Creation: XXX
""")
        stream.seek(0)
        headers = {}
        headers['Content-Type'] = 'image/png; blob-key=foo'

        f = FileStorage(stream=stream, headers=headers)
        self.assertRaises(blobstore.BlobInfoParseError, parse_blob_info,f, 'my_field_name')


if __name__ == '__main__':
    test_utils.main()

########NEW FILE########
__FILENAME__ = gae_db_test
# -*- coding: utf-8 -*-
"""
    Tests for tipfy.appengine.db
"""
import unittest
import hashlib

from google.appengine.ext import db
from google.appengine.api import datastore_errors

from werkzeug.exceptions import NotFound

from tipfy.appengine import db as ext_db

import test_utils


class FooModel(db.Model):
    name = db.StringProperty(required=True)
    name2 = db.StringProperty()
    age = db.IntegerProperty()
    married = db.BooleanProperty()
    data = ext_db.PickleProperty()
    slug = ext_db.SlugProperty(name)
    slug2 = ext_db.SlugProperty(name2, default='some-default-value', max_length=20)
    etag = ext_db.EtagProperty(name)
    etag2 = ext_db.EtagProperty(name2)
    somekey = ext_db.KeyProperty()


class FooExpandoModel(db.Expando):
    pass


class BarModel(db.Model):
    foo = db.ReferenceProperty(FooModel)


class JsonModel(db.Model):
    data = ext_db.JsonProperty()


class TimezoneModel(db.Model):
    data = ext_db.TimezoneProperty()


@ext_db.retry_on_timeout(retries=3, interval=0.1)
def test_timeout_1(**kwargs):
    counter = kwargs.get('counter')

    # Let it pass only in the last attempt
    if counter[0] < 3:
        counter[0] += 1
        raise db.Timeout()


@ext_db.retry_on_timeout(retries=5, interval=0.1)
def test_timeout_2(**kwargs):
    counter = kwargs.get('counter')

    # Let it pass only in the last attempt
    if counter[0] < 5:
        counter[0] += 1
        raise db.Timeout()

    raise ValueError()


@ext_db.retry_on_timeout(retries=2, interval=0.1)
def test_timeout_3(**kwargs):
    # Never let it pass.
    counter = kwargs.get('counter')
    counter[0] += 1
    raise db.Timeout()


class TestModel(test_utils.BaseTestCase):
    def test_no_protobuf_from_entity(self):
        res_1 = ext_db.get_entity_from_protobuf([])
        self.assertEqual(res_1, None)
        res_2 = ext_db.get_protobuf_from_entity(None)
        self.assertEqual(res_2, None)

    def test_no_entity_from_protobuf(self):
        res_1 = ext_db.get_entity_from_protobuf([])
        self.assertEqual(res_1, None)

    def test_one_model_to_and_from_protobuf(self):
        entity_1 = FooModel(name='foo', age=15, married=False)
        entity_1.put()

        pb_1 = ext_db.get_protobuf_from_entity(entity_1)

        entity_1 = ext_db.get_entity_from_protobuf(pb_1)
        self.assertEqual(isinstance(entity_1, FooModel), True)
        self.assertEqual(entity_1.name, 'foo')
        self.assertEqual(entity_1.age, 15)
        self.assertEqual(entity_1.married, False)

    def test_many_models_to_and_from_protobuf(self):
        entity_1 = FooModel(name='foo', age=15, married=False)
        entity_1.put()
        entity_2 = FooModel(name='bar', age=30, married=True)
        entity_2.put()
        entity_3 = FooModel(name='baz', age=45, married=False)
        entity_3.put()

        pbs = ext_db.get_protobuf_from_entity([entity_1, entity_2, entity_3])
        self.assertEqual(len(pbs), 3)

        entity_1, entity_2, entity_3 = ext_db.get_entity_from_protobuf(pbs)
        self.assertEqual(isinstance(entity_1, FooModel), True)
        self.assertEqual(entity_1.name, 'foo')
        self.assertEqual(entity_1.age, 15)
        self.assertEqual(entity_1.married, False)

        self.assertEqual(isinstance(entity_2, FooModel), True)
        self.assertEqual(entity_2.name, 'bar')
        self.assertEqual(entity_2.age, 30)
        self.assertEqual(entity_2.married, True)

        self.assertEqual(isinstance(entity_3, FooModel), True)
        self.assertEqual(entity_3.name, 'baz')
        self.assertEqual(entity_3.age, 45)
        self.assertEqual(entity_3.married, False)

    def test_get_protobuf_from_entity_using_dict(self):
        entity_1 = FooModel(name='foo', age=15, married=False)
        entity_1.put()
        entity_2 = FooModel(name='bar', age=30, married=True)
        entity_2.put()
        entity_3 = FooModel(name='baz', age=45, married=False)
        entity_3.put()

        entity_dict = {'entity_1': entity_1, 'entity_2': entity_2, 'entity_3': entity_3,}

        pbs = ext_db.get_protobuf_from_entity(entity_dict)

        entities = ext_db.get_entity_from_protobuf(pbs)
        entity_1 = entities['entity_1']
        entity_2 = entities['entity_2']
        entity_3 = entities['entity_3']

        self.assertEqual(isinstance(entity_1, FooModel), True)
        self.assertEqual(entity_1.name, 'foo')
        self.assertEqual(entity_1.age, 15)
        self.assertEqual(entity_1.married, False)

        self.assertEqual(isinstance(entity_2, FooModel), True)
        self.assertEqual(entity_2.name, 'bar')
        self.assertEqual(entity_2.age, 30)
        self.assertEqual(entity_2.married, True)

        self.assertEqual(isinstance(entity_3, FooModel), True)
        self.assertEqual(entity_3.name, 'baz')
        self.assertEqual(entity_3.age, 45)
        self.assertEqual(entity_3.married, False)

    def test_get_or_insert_with_flag(self):
        entity, flag = ext_db.get_or_insert_with_flag(FooModel, 'foo', name='foo', age=15, married=False)
        self.assertEqual(flag, True)
        self.assertEqual(entity.name, 'foo')
        self.assertEqual(entity.age, 15)
        self.assertEqual(entity.married, False)

        entity, flag = ext_db.get_or_insert_with_flag(FooModel, 'foo', name='bar', age=30, married=True)
        self.assertEqual(flag, False)
        self.assertEqual(entity.name, 'foo')
        self.assertEqual(entity.age, 15)
        self.assertEqual(entity.married, False)

    def test_get_reference_key(self):
        entity_1 = FooModel(name='foo', age=15, married=False)
        entity_1.put()
        entity_1_key = str(entity_1.key())

        entity_2 = BarModel(key_name='first_bar', foo=entity_1)
        entity_2.put()

        entity_1.delete()
        entity_3 = BarModel.get_by_key_name('first_bar')
        # Won't resolve, but we can still get the key value.
        self.assertRaises(db.Error, getattr, entity_3, 'foo')
        self.assertEqual(str(ext_db.get_reference_key(entity_3, 'foo')), entity_1_key)

    def test_get_reference_key_2(self):
        # Set a book entity with an author reference.
        class Author(db.Model):
            name = db.StringProperty()

        class Book(db.Model):
            title = db.StringProperty()
            author = db.ReferenceProperty(Author)

        author = Author(name='Stephen King')
        author.put()

        book = Book(key_name='the-shining', title='The Shining', author=author)
        book.put()

        # Now let's fetch the book and get the author key without fetching it.
        fetched_book = Book.get_by_key_name('the-shining')
        self.assertEqual(str(ext_db.get_reference_key(fetched_book, 'author')), str(author.key()))

    #===========================================================================
    # db.populate_entity
    #===========================================================================
    def test_populate_entity(self):
        entity_1 = FooModel(name='foo', age=15, married=False)
        entity_1.put()

        self.assertEqual(entity_1.name, 'foo')
        self.assertEqual(entity_1.age, 15)
        self.assertEqual(entity_1.married, False)

        ext_db.populate_entity(entity_1, name='bar', age=20, married=True, city='Yukon')
        entity_1.put()

        self.assertEqual(entity_1.name, 'bar')
        self.assertEqual(entity_1.age, 20)
        self.assertEqual(entity_1.married, True)

    def test_populate_entity_2(self):
        entity_1 = FooModel(name='foo', age=15, married=False)
        entity_1.put()

        self.assertEqual(entity_1.name, 'foo')
        self.assertEqual(entity_1.age, 15)
        self.assertEqual(entity_1.married, False)

        ext_db.populate_entity(entity_1, name='bar', age=20, married=True, city='Yukon')
        entity_1.put()

        self.assertRaises(AttributeError, getattr, entity_1, 'city')

    def test_populate_expando_entity(self):
        entity_1 = FooExpandoModel(name='foo', age=15, married=False)
        entity_1.put()

        self.assertEqual(entity_1.name, 'foo')
        self.assertEqual(entity_1.age, 15)
        self.assertEqual(entity_1.married, False)

        ext_db.populate_entity(entity_1, name='bar', age=20, married=True, city='Yukon')
        entity_1.put()

        self.assertEqual(entity_1.name, 'bar')
        self.assertEqual(entity_1.age, 20)
        self.assertEqual(entity_1.married, True)

    def test_populate_expando_entity_2(self):
        entity_1 = FooExpandoModel(name='foo', age=15, married=False)
        entity_1.put()

        self.assertEqual(entity_1.name, 'foo')
        self.assertEqual(entity_1.age, 15)
        self.assertEqual(entity_1.married, False)

        ext_db.populate_entity(entity_1, name='bar', age=20, married=True, city='Yukon')
        entity_1.put()

        self.assertRaises(AttributeError, getattr, entity_1, 'city')


    #===========================================================================
    # db.get_entity_dict
    #===========================================================================
    def test_get_entity_dict(self):
        class MyModel(db.Model):
            animal = db.StringProperty()
            species = db.IntegerProperty()
            description = db.TextProperty()

        entity = MyModel(animal='duck', species=12,
            description='A duck, a bird that swims well.')
        values = ext_db.get_entity_dict(entity)

        self.assertEqual(values, {
            'animal': 'duck',
            'species': 12,
            'description': 'A duck, a bird that swims well.',
        })

    def test_get_entity_dict_multiple(self):
        class MyModel(db.Model):
            animal = db.StringProperty()
            species = db.IntegerProperty()
            description = db.TextProperty()

        entity = MyModel(animal='duck', species=12,
            description='A duck, a bird that swims well.')
        entity2 = MyModel(animal='bird', species=7,
            description='A bird, an animal that flies well.')
        values = ext_db.get_entity_dict([entity, entity2])

        self.assertEqual(values, [
            {
                'animal': 'duck',
                'species': 12,
                'description': 'A duck, a bird that swims well.',
            },
            {
                'animal': 'bird',
                'species': 7,
                'description': 'A bird, an animal that flies well.',
            }
        ])

    def test_get_entity_dict_with_expando(self):
        class MyModel(db.Expando):
            animal = db.StringProperty()
            species = db.IntegerProperty()
            description = db.TextProperty()

        entity = MyModel(animal='duck', species=12,
            description='A duck, a bird that swims well.',
            most_famous='Daffy Duck')
        values = ext_db.get_entity_dict(entity)

        self.assertEqual(values, {
            'animal': 'duck',
            'species': 12,
            'description': 'A duck, a bird that swims well.',
            'most_famous': 'Daffy Duck',
        })

    #===========================================================================
    # get..._or_404
    #===========================================================================
    def test_get_by_key_name_or_404(self):
        entity_1 = FooModel(key_name='foo', name='foo', age=15, married=False)
        entity_1.put()

        entity = ext_db.get_by_key_name_or_404(FooModel, 'foo')
        self.assertEqual(str(entity.key()), str(entity_1.key()))

    def test_get_by_key_name_or_404_2(self):
        self.assertRaises(NotFound, ext_db.get_by_key_name_or_404, FooModel, 'bar')

    def test_get_by_id_or_404(self):
        entity_1 = FooModel(name='foo', age=15, married=False)
        entity_1.put()

        entity = ext_db.get_by_id_or_404(FooModel, entity_1.key().id())
        self.assertEqual(str(entity.key()), str(entity_1.key()))

    def test_get_by_id_or_404_2(self):
        self.assertRaises(NotFound, ext_db.get_by_id_or_404, FooModel, -1)

    def test_get_or_404(self):
        entity_1 = FooModel(name='foo', age=15, married=False)
        entity_1.put()

        entity = ext_db.get_or_404(entity_1.key())
        self.assertEqual(str(entity.key()), str(entity_1.key()))

    def test_get_or_404_2(self):
        self.assertRaises(NotFound, ext_db.get_or_404, db.Key.from_path('FooModel', 'bar'))

    def test_get_or_404_3(self):
        self.assertRaises(NotFound, ext_db.get_or_404, 'this, not a valid key')

    #===========================================================================
    # db.Property
    #===========================================================================
    def test_pickle_property(self):
        data_1 = {'foo': 'bar'}
        entity_1 = FooModel(key_name='foo', name='foo', data=data_1)
        entity_1.put()

        data_2 = [1, 2, 3, 'baz']
        entity_2 = FooModel(key_name='bar', name='bar', data=data_2)
        entity_2.put()

        entity_1 = FooModel.get_by_key_name('foo')
        self.assertEqual(entity_1.data, data_1)

        entity_2 = FooModel.get_by_key_name('bar')
        self.assertEqual(entity_2.data, data_2)

    def test_slug_property(self):
        entity_1 = FooModel(key_name='foo', name=u'Mary Björk')
        entity_1.put()

        entity_2 = FooModel(key_name='bar', name=u'Tião Macalé')
        entity_2.put()

        entity_1 = FooModel.get_by_key_name('foo')
        entity_2 = FooModel.get_by_key_name('bar')
        self.assertEqual(entity_1.slug, 'mary-bjork')
        self.assertEqual(entity_2.slug, 'tiao-macale')

    def test_slug_property2(self):
        entity_1 = FooModel(key_name='foo', name=u'---')
        entity_1.put()

        entity_2 = FooModel(key_name='bar', name=u'___')
        entity_2.put()

        entity_1 = FooModel.get_by_key_name('foo')
        entity_2 = FooModel.get_by_key_name('bar')
        self.assertEqual(entity_1.slug, None)
        self.assertEqual(entity_2.slug, None)

    def test_slug_property3(self):
        entity_1 = FooModel(key_name='foo', name=u'---', name2=u'---')
        entity_1.put()

        entity_2 = FooModel(key_name='bar', name=u'___', name2=u'___')
        entity_2.put()

        entity_1 = FooModel.get_by_key_name('foo')
        entity_2 = FooModel.get_by_key_name('bar')
        self.assertEqual(entity_1.slug2, 'some-default-value')
        self.assertEqual(entity_2.slug2, 'some-default-value')

    def test_slug_property4(self):
        entity_1 = FooModel(key_name='foo', name=u'---', name2=u'Some really very big and maybe enormous string')
        entity_1.put()

        entity_2 = FooModel(key_name='bar', name=u'___', name2=u'abcdefghijklmnopqrstuwxyz')
        entity_2.put()

        entity_1 = FooModel.get_by_key_name('foo')
        entity_2 = FooModel.get_by_key_name('bar')
        self.assertEqual(entity_1.slug2, 'some-really-very-big')
        self.assertEqual(entity_2.slug2, 'abcdefghijklmnopqrst')

    def test_etag_property(self):
        entity_1 = FooModel(key_name='foo', name=u'Mary Björk')
        entity_1.put()

        entity_2 = FooModel(key_name='bar', name=u'Tião Macalé')
        entity_2.put()

        entity_1 = FooModel.get_by_key_name('foo')
        entity_2 = FooModel.get_by_key_name('bar')
        self.assertEqual(entity_1.etag, hashlib.sha1(entity_1.name.encode('utf8')).hexdigest())
        self.assertEqual(entity_2.etag, hashlib.sha1(entity_2.name.encode('utf8')).hexdigest())

    def test_etag_property2(self):
        entity_1 = FooModel(key_name='foo', name=u'Mary Björk')
        entity_1.put()

        entity_2 = FooModel(key_name='bar', name=u'Tião Macalé')
        entity_2.put()

        entity_1 = FooModel.get_by_key_name('foo')
        entity_2 = FooModel.get_by_key_name('bar')
        self.assertEqual(entity_1.etag2, None)
        self.assertEqual(entity_2.etag2, None)

    def test_json_property(self):
        entity_1 = JsonModel(key_name='foo', data={'foo': 'bar'})
        entity_1.put()

        entity_1 = JsonModel.get_by_key_name('foo')
        self.assertEqual(entity_1.data, {'foo': 'bar'})

    def test_json_property2(self):
        self.assertRaises(db.BadValueError, JsonModel, key_name='foo', data='foo')

    def test_timezone_property(self):
        zone = 'America/Chicago'
        entity_1 = TimezoneModel(key_name='foo', data=zone)
        entity_1.put()

        entity_1 = TimezoneModel.get_by_key_name('foo')
        self.assertEqual(entity_1.data, ext_db.pytz.timezone(zone))

    def test_timezone_property2(self):
        self.assertRaises(db.BadValueError, TimezoneModel, key_name='foo', data=[])

    def test_timezone_property3(self):
        self.assertRaises(ext_db.pytz.UnknownTimeZoneError, TimezoneModel, key_name='foo', data='foo')

    def test_key_property(self):
        key = db.Key.from_path('Bar', 'bar-key')
        entity_1 = FooModel(name='foo', key_name='foo', somekey=key)
        entity_1.put()

        entity_1 = FooModel.get_by_key_name('foo')
        self.assertEqual(entity_1.somekey, key)

    def test_key_property2(self):
        key = db.Key.from_path('Bar', 'bar-key')
        entity_1 = FooModel(name='foo', key_name='foo', somekey=str(key))
        entity_1.put()

        entity_1 = FooModel.get_by_key_name('foo')
        self.assertEqual(entity_1.somekey, key)

    def test_key_property3(self):
        key = db.Key.from_path('Bar', 'bar-key')
        entity_1 = FooModel(name='foo', key_name='foo', somekey=str(key))
        entity_1.put()

        entity_2 = FooModel(name='bar', key_name='bar', somekey=entity_1)
        entity_2.put()

        entity_2 = FooModel.get_by_key_name('bar')
        self.assertEqual(entity_2.somekey, entity_1.key())

    def test_key_property4(self):
        key = db.Key.from_path('Bar', 'bar-key')
        entity_1 = FooModel(name='foo', somekey=str(key))
        self.assertRaises(db.BadValueError, FooModel, name='bar', key_name='bar', somekey=entity_1)

    def test_key_property5(self):
        self.assertRaises(TypeError, FooModel, name='foo', key_name='foo', somekey=['foo'])

    def test_key_property6(self):
        self.assertRaises(datastore_errors.BadKeyError, FooModel, name='foo', key_name='foo', somekey='foo')

    #===========================================================================
    # @db.retry_on_timeout
    #===========================================================================
    def test_retry_on_timeout_1(self):
        counter = [0]
        test_timeout_1(counter=counter)
        self.assertEqual(counter[0], 3)

    def test_retry_on_timeout_2(self):
        counter = [0]
        self.assertRaises(ValueError, test_timeout_2, counter=counter)
        self.assertEqual(counter[0], 5)

    def test_retry_on_timeout_3(self):
        counter = [0]
        self.assertRaises(db.Timeout, test_timeout_3, counter=counter)
        self.assertEqual(counter[0], 3)

    #===========================================================================
    # @db.load_entity
    #===========================================================================
    def test_load_entity_with_key(self):
        @ext_db.load_entity(FooModel, 'foo_key', 'foo', 'key')
        def get(*args, **kwargs):
            return kwargs['foo']

        foo = FooModel(name='foo')
        foo.put()

        loaded_foo = get(foo_key=str(foo.key()))
        self.assertEqual(str(loaded_foo.key()), str(foo.key()))
        self.assertEqual(get(foo_key=None), None)

    def test_load_entity_with_key_2(self):
        @ext_db.load_entity(FooModel, 'foo_key', 'foo', 'key')
        def get(*args, **kwargs):
            return kwargs['foo']

        self.assertRaises(NotFound, get, foo_key=str(db.Key.from_path('FooModel', 'bar')))

    def test_load_entity_with_id(self):
        @ext_db.load_entity(FooModel, 'foo_id', 'foo', 'id')
        def get(*args, **kwargs):
            return kwargs['foo']

        foo = FooModel(name='foo')
        foo.put()

        loaded_foo = get(foo_id=foo.key().id())
        self.assertEqual(str(loaded_foo.key()), str(foo.key()))

    def test_load_entity_with_id_2(self):
        @ext_db.load_entity(FooModel, 'foo_id', 'foo', 'id')
        def get(*args, **kwargs):
            return kwargs['foo']

        self.assertRaises(NotFound, get, foo_id=-1)

    def test_load_entity_with_key_name(self):
        @ext_db.load_entity(FooModel, 'foo_key_name', 'foo', 'key_name')
        def get(*args, **kwargs):
            return kwargs['foo']

        foo = FooModel(key_name='foo', name='foo')
        foo.put()

        loaded_foo = get(foo_key_name='foo')
        self.assertEqual(str(loaded_foo.key()), str(foo.key()))

    def test_load_entity_with_key_name_2(self):
        @ext_db.load_entity(FooModel, 'foo_key_name', 'foo', 'key_name')
        def get(*args, **kwargs):
            return kwargs['foo']

        self.assertRaises(NotFound, get, foo_key_name='bar')

    def test_load_entity_with_key_with_guessed_fetch_mode(self):
        @ext_db.load_entity(FooModel, 'foo_key')
        def get(*args, **kwargs):
            return kwargs['foo']

        foo = FooModel(name='foo')
        foo.put()

        loaded_foo = get(foo_key=str(foo.key()))
        self.assertEqual(str(loaded_foo.key()), str(foo.key()))
        self.assertEqual(get(foo_key=None), None)

    def test_load_entity_with_key_with_impossible_fetch_mode(self):
        def test():
            @ext_db.load_entity(FooModel, 'foo_bar')
            def get(*args, **kwargs):
                return kwargs['foo']

        self.assertRaises(NotImplementedError, test)

    #===========================================================================
    # db.run_in_namespace
    #===========================================================================
    def test_run_in_namespace(self):
        class MyModel(db.Model):
            name = db.StringProperty()

        def create_entity(name):
            entity = MyModel(key_name=name, name=name)
            entity.put()

        def get_entity(name):
            return MyModel.get_by_key_name(name)

        entity = ext_db.run_in_namespace('ns1', get_entity, 'foo')
        self.assertEqual(entity, None)

        ext_db.run_in_namespace('ns1', create_entity, 'foo')

        entity = ext_db.run_in_namespace('ns1', get_entity, 'foo')
        self.assertNotEqual(entity, None)

        entity = ext_db.run_in_namespace('ns2', get_entity, 'foo')
        self.assertEqual(entity, None)

    #===========================================================================
    # db.to_key
    #===========================================================================
    def test_to_key(self):
        class MyModel(db.Model):
            pass

        # None.
        self.assertEqual(ext_db.to_key(None), None)
        # Model without key.
        self.assertEqual(ext_db.to_key(MyModel()), None)
        # Model with key.
        self.assertEqual(ext_db.to_key(MyModel(key_name='foo')), db.Key.from_path('MyModel', 'foo'))
        # Key.
        self.assertEqual(ext_db.to_key(db.Key.from_path('MyModel', 'foo')), db.Key.from_path('MyModel', 'foo'))
        # Key as string.
        self.assertEqual(ext_db.to_key(str(db.Key.from_path('MyModel', 'foo'))), db.Key.from_path('MyModel', 'foo'))
        # All mixed.
        keys = [None, MyModel(), MyModel(key_name='foo'), db.Key.from_path('MyModel', 'foo'), str(db.Key.from_path('MyModel', 'foo'))]
        result = [None, None, db.Key.from_path('MyModel', 'foo'), db.Key.from_path('MyModel', 'foo'), db.Key.from_path('MyModel', 'foo')]
        self.assertEqual(ext_db.to_key(keys), result)

        self.assertRaises(datastore_errors.BadArgumentError, ext_db.to_key, {})


if __name__ == '__main__':
    test_utils.main()

########NEW FILE########
__FILENAME__ = gae_mail_test
# -*- coding: utf-8 -*-
"""
    Tests for tipfy.appengine.mail
"""
import os
import sys
import unittest

from tipfy import Rule, Tipfy
from tipfy.app import local

from google.appengine.api.xmpp import Message as ApiMessage

import test_utils

MESSAGE = """Subject: Hello there!
From: Me <me@myself.com>
To: You <you@yourself.com>
Content-Type: text/plain; charset=ISO-8859-1

Test message!"""


def get_app():
    return Tipfy(rules=[
        Rule('/', name='xmpp-test', handler='resources.mail_handlers.MailHandler'),
        Rule('/test2', name='xmpp-test', handler='resources.mail_handlers.MailHandler2'),
    ], debug=True)


class TestInboundMailHandler(test_utils.BaseTestCase):
    def test_mail(self):
        app = get_app()
        client = app.get_test_client()

        response = client.open(method='POST', path='/', data=MESSAGE, content_type='text/plain')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 'Test message!')

    def test_not_implemented(self):
        app = get_app()
        app.config['tipfy']['enable_debugger'] = False
        client = app.get_test_client()

        self.assertRaises(NotImplementedError, client.open, method='POST', path='/test2', data=MESSAGE, content_type='text/plain')


if __name__ == '__main__':
    test_utils.main()

########NEW FILE########
__FILENAME__ = gae_sharded_counter_test
# -*- coding: utf-8 -*-
"""
    Tests for tipfy.appengine.sharded_counter
"""
from datetime import datetime, timedelta
import unittest

from google.appengine.api import memcache
from google.appengine.ext import db

from tipfy import Request, RequestHandler, Tipfy
from tipfy.app import local
from tipfy.appengine.sharded_counter import Counter

import test_utils


class TestCounter(test_utils.BaseTestCase):
    def setUp(self):
        app = Tipfy()
        local.request = Request.from_values()
        local.request.app = app
        test_utils.BaseTestCase.setUp(self)

    def test_counter(self):
        # Build a new counter that uses the unique key name 'hits'.
        hits = Counter('hits')

        self.assertEqual(hits.count, 0)

        # Increment by 1.
        hits.increment()
        # Increment by 10.
        hits.increment(10)
        # Decrement by 3.
        hits.increment(-3)
        # This is the current count.
        self.assertEqual(hits.count, 8)

        # Forces fetching a non-cached count of all shards.
        self.assertEqual(hits.get_count(nocache=True), 8)

        # Set the counter to an arbitrary value.
        hits.count = 6

        self.assertEqual(hits.get_count(nocache=True), 6)

    def test_cache(self):
        # Build a new counter that uses the unique key name 'hits'.
        hits = Counter('hits')

        self.assertEqual(hits.count, 0)

        # Increment by 1.
        hits.increment()
        # Increment by 10.
        hits.increment(10)
        # Decrement by 3.
        hits.increment(-3)
        # This is the current count.
        self.assertEqual(hits.count, 8)

        # Forces fetching a non-cached count of all shards.
        self.assertEqual(hits.get_count(nocache=True), 8)

        # Set the counter to an arbitrary value.
        hits.delete()

        self.assertEqual(hits.get_count(), 8)
        self.assertEqual(hits.get_count(nocache=True), 0)

        hits.memcached.delete_count()

        self.assertEqual(hits.get_count(), 0)


if __name__ == '__main__':
    test_utils.main()

########NEW FILE########
__FILENAME__ = gae_taskqueue_test
# -*- coding: utf-8 -*-
"""
    Tests for tipfyext.appenginetaskqueue
"""
import time
import unittest

from google.appengine.ext import deferred

from google.appengine.api import taskqueue
from google.appengine.ext import db

from tipfy import Rule, Tipfy
from tipfy.app import local

import test_utils


def get_rules():
    # Fake get_rules() for testing.
    return [
        Rule('/_tasks/process-mymodel/', name='tasks/process-mymodel',
            handler='%s.TaskTestModelEntityTaskHandler' % __name__),
        Rule('/_tasks/process-mymodel/<string:key>', name='tasks/process-mymodel',
            handler='%s.TaskTestModelEntityTaskHandler' % __name__),
    ]


def get_url_rules():
    # Fake get_rules() for testing.
    rules = [
        Rule('/_ah/queue/deferred', name='tasks/deferred', handler='tipfy.appengine.taskqueue.DeferredHandler'),
    ]

    return Map(rules)


def get_app():
    return Tipfy({
        'tipfy': {
            'dev': True,
        },
    }, rules=get_url_rules())


class TaskTestModel(db.Model):
    number = db.IntegerProperty()


def save_entities(numbers):
    entities = []
    for number in numbers:
        entities.append(TaskTestModel(key_name=str(number), number=number))

    res = db.put(entities)

    import sys
    sys.exit(res)


class TestDeferredHandler(test_utils.BaseTestCase):
    """TODO"""

    def test_simple_deferred(self):
        numbers = [1234, 1577, 988]
        keys = [db.Key.from_path('TaskTestModel', str(number)) for number in numbers]
        entities = db.get(keys)
        self.assertEqual(entities, [None, None, None])

        deferred.defer(save_entities, numbers)


class TestTasks(test_utils.BaseTestCase):
    """TODO"""


if __name__ == '__main__':
    test_utils.main()

########NEW FILE########
__FILENAME__ = gae_xmpp_test
# -*- coding: utf-8 -*-
"""
    Tests for tipfy.appengine.xmpp
"""
import os
import sys
import unittest

from tipfy import Rule, Tipfy
from tipfy.app import local

from google.appengine.api.xmpp import Message as ApiMessage

import test_utils

fake_local = {}


def get_app():
    return Tipfy(rules=[
        Rule('/', name='xmpp-test', handler='resources.xmpp_handlers.XmppHandler'),
        Rule('/test2', name='xmpp-test', handler='resources.xmpp_handlers.XmppHandler2'),
    ], debug=True)


def send_message(jids, body, from_jid=None, message_type='chat',
                 raw_xml=False):
    fake_local['message'] = {
        'body': body,
    }


class InvalidMessageError(Exception):
    pass


class Message(ApiMessage):
    """Encapsulates an XMPP message received by the application."""
    def __init__(self, vars):
        """Constructs a new XMPP Message from an HTTP request.

        Args:
          vars: A dict-like object to extract message arguments from.
        """
        try:
            self.__sender = vars["from"]
            self.__to = vars["to"]
            self.__body = vars["body"]
        except KeyError, e:
            raise InvalidMessageError(e[0])

        self.__command = None
        self.__arg = None

    def reply(self, body, message_type='chat', raw_xml=False,
            send_message=send_message):
        """Convenience function to reply to a message.

        Args:
          body: str: The body of the message
          message_type, raw_xml: As per send_message.
          send_message: Used for testing.

        Returns:
          A status code as per send_message.

        Raises:
          See send_message.
        """
        return send_message([self.sender], body, from_jid=self.to,
                        message_type=message_type, raw_xml=raw_xml)


class TestCommandHandler(test_utils.BaseTestCase):
    def setUp(self):
        from tipfy.appengine import xmpp
        self.xmpp_module = xmpp.xmpp
        xmpp.xmpp = sys.modules[__name__]
        test_utils.BaseTestCase.setUp(self)

    def tearDown(self):
        fake_local.clear()

        from tipfy.appengine import xmpp
        xmpp.xmpp = self.xmpp_module
        test_utils.BaseTestCase.tearDown(self)

    def test_no_command(self):
        app = get_app()
        client = app.get_test_client()

        data = {}
        client.open(method='POST', data=data)

        self.assertEqual(fake_local.get('message', None), None)

    def test_not_implemented(self):
        app = get_app()
        app.config['tipfy']['enable_debugger'] = False
        client = app.get_test_client()

        data = {
            'from': 'me@myself.com',
            'to':   'you@yourself.com',
            'body': '/inexistent_command foo bar',
        }
        self.assertRaises(NotImplementedError, client.post, path='/test2', data=data)

    def test_unknown_command(self):
        app = get_app()
        client = app.get_test_client()

        data = {
            'from': 'me@myself.com',
            'to':   'you@yourself.com',
            'body': '/inexistent_command foo bar',
        }
        client.open(method='POST', data=data)

        self.assertEqual(fake_local.get('message', None), {'body': 'Unknown command'})

    def test_command(self):
        app = get_app()
        client = app.get_test_client()

        data = {
            'from': 'me@myself.com',
            'to':   'you@yourself.com',
            'body': '/foo foo bar',
        }
        client.open(method='POST', data=data)

        self.assertEqual(fake_local.get('message', None), {'body': 'Foo command!'})

        data = {
            'from': 'me@myself.com',
            'to':   'you@yourself.com',
            'body': '/bar foo bar',
        }
        client.open(method='POST', data=data)

        self.assertEqual(fake_local.get('message', None), {'body': 'Bar command!'})

    def test_text_message(self):
        app = get_app()
        client = app.get_test_client()

        data = {
            'from': 'me@myself.com',
            'to':   'you@yourself.com',
            'body': 'Hello, text message!',
        }
        client.open(method='POST', data=data)

        self.assertEqual(fake_local.get('message', None), {'body': 'Hello, text message!'})


if __name__ == '__main__':
    test_utils.main()

########NEW FILE########
__FILENAME__ = i18n_test
# -*- coding: utf-8 -*-
"""
    Tests for tipfy.i18n
"""
from __future__ import with_statement

import datetime
import gettext as gettext_stdlib
import os
import unittest

from babel.numbers import NumberFormatError

from pytz.gae import pytz

from tipfy.app import App, Request, Response
from tipfy.handler import RequestHandler
from tipfy.routing import Rule
from tipfy.local import local, get_request
from tipfy.sessions import SessionMiddleware
import tipfy.i18n as i18n

import test_utils


class BaseTestCase(test_utils.BaseTestCase):
    def setUp(self):
        app = App(rules=[
            Rule('/', name='home', handler=RequestHandler)
        ], config={
            'tipfy.sessions': {
                'secret_key': 'secret',
            },
            'tipfy.i18n': {
                'timezone': 'UTC'
            },
        })
        local.request = request = Request.from_values('/')
        request.app = app
        test_utils.BaseTestCase.setUp(self)

    #==========================================================================
    # I18nMiddleware
    #==========================================================================

    def test_middleware_multiple_changes(self):
        class MyHandler(RequestHandler):
            middleware = [SessionMiddleware(), i18n.I18nMiddleware()]

            def get(self, **kwargs):
                locale = self.i18n.locale
                return Response(locale)

        app = App(rules=[
            Rule('/', name='home', handler=MyHandler)
        ], config={
            'tipfy.sessions': {
                'secret_key': 'secret',
            },
            'tipfy.i18n': {
                'locale_request_lookup': [('args', 'lang'), ('session', '_locale')],
            }
        })

        client = app.get_test_client()
        response = client.get('/')
        self.assertEqual(response.data, 'en_US')

        response = client.get('/?lang=pt_BR')
        self.assertEqual(response.data, 'pt_BR')

        response = client.get('/')
        self.assertEqual(response.data, 'pt_BR')

        response = client.get('/?lang=en_US')
        self.assertEqual(response.data, 'en_US')

        response = client.get('/')
        self.assertEqual(response.data, 'en_US')

    #==========================================================================
    # _(), gettext(), ngettext(), lazy_gettext(), lazy_ngettext()
    #==========================================================================

    def test_translations_not_set(self):
        # We release it here because it is set on setUp()
        local.__release_local__()
        self.assertRaises(AttributeError, i18n.gettext, 'foo')

    def test_gettext(self):
        self.assertEqual(i18n.gettext('foo'), u'foo')

    def test_gettext_(self):
        self.assertEqual(i18n._('foo'), u'foo')

    def test_gettext_with_variables(self):
        self.assertEqual(i18n.gettext('foo %(foo)s'), u'foo %(foo)s')
        self.assertEqual(i18n.gettext('foo %(foo)s') % {'foo': 'bar'}, u'foo bar')
        self.assertEqual(i18n.gettext('foo %(foo)s', foo='bar'), u'foo bar')

    def test_ngettext(self):
        self.assertEqual(i18n.ngettext('One foo', 'Many foos', 1), u'One foo')
        self.assertEqual(i18n.ngettext('One foo', 'Many foos', 2), u'Many foos')

    def test_ngettext_with_variables(self):
        self.assertEqual(i18n.ngettext('One foo %(foo)s', 'Many foos %(foo)s', 1), u'One foo %(foo)s')
        self.assertEqual(i18n.ngettext('One foo %(foo)s', 'Many foos %(foo)s', 2), u'Many foos %(foo)s')
        self.assertEqual(i18n.ngettext('One foo %(foo)s', 'Many foos %(foo)s', 1, foo='bar'), u'One foo bar')
        self.assertEqual(i18n.ngettext('One foo %(foo)s', 'Many foos %(foo)s', 2, foo='bar'), u'Many foos bar')
        self.assertEqual(i18n.ngettext('One foo %(foo)s', 'Many foos %(foo)s', 1) % {'foo': 'bar'}, u'One foo bar')
        self.assertEqual(i18n.ngettext('One foo %(foo)s', 'Many foos %(foo)s', 2) % {'foo': 'bar'}, u'Many foos bar')

    def test_lazy_gettext(self):
        self.assertEqual(i18n.lazy_gettext('foo'), u'foo')

    def test_lazy_ngettext(self):
        self.assertEqual(i18n.lazy_ngettext('One foo', 'Many foos', 1), u'One foo')
        self.assertEqual(i18n.lazy_ngettext('One foo', 'Many foos', 2), u'Many foos')

    #==========================================================================
    # I18nStore.get_store_for_request()
    #==========================================================================

    def get_app(self):
        return App(rules=[
            Rule('/', name='home', handler=RequestHandler)
        ], config={
            'tipfy.sessions': {
                'secret_key': 'secret',
            },
            'tipfy.i18n': {
                'timezone': 'UTC'
            },
        })

    def test_get_store_for_request(self):
        app = self.get_app()
        app.config['tipfy.i18n']['locale'] = 'jp_JP'

        with app.get_test_handler('/') as handler:
            self.assertEqual(handler.i18n.locale, 'jp_JP')

    def test_get_store_for_request_args(self):
        app = self.get_app()
        app.config['tipfy.i18n']['locale_request_lookup'] = [('args', 'language')]

        with app.get_test_handler('/', query_string={'language': 'es_ES'}) as handler:
            self.assertEqual(handler.i18n.locale, 'es_ES')

    def test_get_store_for_request_form(self):
        app = self.get_app()
        app.config['tipfy.i18n']['locale_request_lookup'] = [('form', 'language')]

        with app.get_test_handler('/', data={'language': 'es_ES'}, method='POST') as handler:
            self.assertEqual(handler.i18n.locale, 'es_ES')

    def test_get_store_for_request_cookies(self):
        app = self.get_app()
        app.config['tipfy.i18n']['locale_request_lookup'] = [('cookies', 'language')]

        with app.get_test_handler('/', headers=[('Cookie', 'language="es_ES"; Path=/')]) as handler:
            self.assertEqual(handler.i18n.locale, 'es_ES')

    def test_get_store_for_request_args_cookies(self):
        app = self.get_app()
        app.config['tipfy.i18n']['locale_request_lookup'] = [
            ('args', 'foo'),
            ('cookies', 'language')
        ]

        with app.get_test_handler('/', headers=[('Cookie', 'language="es_ES"; Path=/')]) as handler:
            self.assertEqual(handler.i18n.locale, 'es_ES')

    def test_get_store_for_request_rule_args(self):
        app = self.get_app()
        app.config['tipfy.i18n']['locale_request_lookup'] = [('rule_args', 'locale'),]

        with app.get_test_handler('/') as handler:
            handler.request.rule_args = {'locale': 'es_ES'}
            self.assertEqual(handler.i18n.locale, 'es_ES')

    #==========================================================================
    # Date formatting
    #==========================================================================

    def test_format_date(self):
        value = datetime.datetime(2009, 11, 10, 16, 36, 05)

        self.assertEqual(i18n.format_date(value, format='short'), u'11/10/09')
        self.assertEqual(i18n.format_date(value, format='medium'), u'Nov 10, 2009')
        self.assertEqual(i18n.format_date(value, format='long'), u'November 10, 2009')
        self.assertEqual(i18n.format_date(value, format='full'), u'Tuesday, November 10, 2009')

    def test_format_date_no_format(self):
        value = datetime.datetime(2009, 11, 10, 16, 36, 05)
        self.assertEqual(i18n.format_date(value), u'Nov 10, 2009')

    def test_format_date_no_format_but_configured(self):
        app = App(config={
            'tipfy.sessions': {
                'secret_key': 'secret',
            },
            'tipfy.i18n': {
                'timezone': 'UTC',
                'date_formats': {
                    'time':             'medium',
                    'date':             'medium',
                    'datetime':         'medium',
                    'time.short':       None,
                    'time.medium':      None,
                    'time.full':        None,
                    'time.long':        None,
                    'date.short':       None,
                    'date.medium':      'full',
                    'date.full':        None,
                    'date.long':        None,
                    'datetime.short':   None,
                    'datetime.medium':  None,
                    'datetime.full':    None,
                    'datetime.long':    None,
                }
            }
        })
        local.request = request = Request.from_values('/')
        request.app = app

        value = datetime.datetime(2009, 11, 10, 16, 36, 05)
        self.assertEqual(i18n.format_date(value), u'Tuesday, November 10, 2009')

    def test_format_date_pt_BR(self):
        i18n.set_locale('pt_BR')
        value = datetime.datetime(2009, 11, 10, 16, 36, 05)

        self.assertEqual(i18n.format_date(value, format='short'), u'10/11/09')
        self.assertEqual(i18n.format_date(value, format='medium'), u'10/11/2009')
        self.assertEqual(i18n.format_date(value, format='long'), u'10 de novembro de 2009')
        self.assertEqual(i18n.format_date(value, format='full'), u'terça-feira, 10 de novembro de 2009')

    def test_format_datetime(self):
        value = datetime.datetime(2009, 11, 10, 16, 36, 05)

        self.assertEqual(i18n.format_datetime(value, format='short'), u'11/10/09 4:36 PM')
        self.assertEqual(i18n.format_datetime(value, format='medium'), u'Nov 10, 2009 4:36:05 PM')
        self.assertEqual(i18n.format_datetime(value, format='long'), u'November 10, 2009 4:36:05 PM +0000')
        #self.assertEqual(i18n.format_datetime(value, format='full'), u'Tuesday, November 10, 2009 4:36:05 PM World (GMT) Time')
        self.assertEqual(i18n.format_datetime(value, format='full'), u'Tuesday, November 10, 2009 4:36:05 PM GMT+00:00')

        i18n.set_timezone('America/Chicago')
        self.assertEqual(i18n.format_datetime(value, format='short'), u'11/10/09 10:36 AM')

    def test_format_datetime_no_format(self):
        value = datetime.datetime(2009, 11, 10, 16, 36, 05)
        self.assertEqual(i18n.format_datetime(value), u'Nov 10, 2009 4:36:05 PM')

    def test_format_datetime_pt_BR(self):
        i18n.set_locale('pt_BR')
        value = datetime.datetime(2009, 11, 10, 16, 36, 05)

        self.assertEqual(i18n.format_datetime(value, format='short'), u'10/11/09 16:36')
        self.assertEqual(i18n.format_datetime(value, format='medium'), u'10/11/2009 16:36:05')
        #self.assertEqual(i18n.format_datetime(value, format='long'), u'10 de novembro de 2009 16:36:05 +0000')
        self.assertEqual(i18n.format_datetime(value, format='long'), u'10 de novembro de 2009 16h36min05s +0000')
        #self.assertEqual(i18n.format_datetime(value, format='full'), u'terça-feira, 10 de novembro de 2009 16h36min05s Horário Mundo (GMT)')
        self.assertEqual(i18n.format_datetime(value, format='full'), u'ter\xe7a-feira, 10 de novembro de 2009 16h36min05s GMT+00:00')

    def test_format_time(self):
        value = datetime.datetime(2009, 11, 10, 16, 36, 05)

        self.assertEqual(i18n.format_time(value, format='short'), u'4:36 PM')
        self.assertEqual(i18n.format_time(value, format='medium'), u'4:36:05 PM')
        self.assertEqual(i18n.format_time(value, format='long'), u'4:36:05 PM +0000')
        #self.assertEqual(i18n.format_time(value, format='full'), u'4:36:05 PM World (GMT) Time')
        self.assertEqual(i18n.format_time(value, format='full'), u'4:36:05 PM GMT+00:00')

    def test_format_time_no_format(self):
        value = datetime.datetime(2009, 11, 10, 16, 36, 05)
        self.assertEqual(i18n.format_time(value), u'4:36:05 PM')

    def test_format_time_pt_BR(self):
        i18n.set_locale('pt_BR')
        value = datetime.datetime(2009, 11, 10, 16, 36, 05)

        self.assertEqual(i18n.format_time(value, format='short'), u'16:36')
        self.assertEqual(i18n.format_time(value, format='medium'), u'16:36:05')
        #self.assertEqual(i18n.format_time(value, format='long'), u'16:36:05 +0000')
        self.assertEqual(i18n.format_time(value, format='long'), u'16h36min05s +0000')
        #self.assertEqual(i18n.format_time(value, format='full'), u'16h36min05s Horário Mundo (GMT)')
        self.assertEqual(i18n.format_time(value, format='full'), u'16h36min05s GMT+00:00')

        i18n.set_timezone('America/Chicago')
        self.assertEqual(i18n.format_time(value, format='short'), u'10:36')

    def test_parse_date(self):
        i18n.set_locale('en_US')
        self.assertEqual(i18n.parse_date('4/1/04'), datetime.date(2004, 4, 1))
        i18n.set_locale('de_DE')
        self.assertEqual(i18n.parse_date('01.04.2004'), datetime.date(2004, 4, 1))

    def test_parse_datetime(self):
        i18n.set_locale('en_US')
        self.assertRaises(NotImplementedError, i18n.parse_datetime, '4/1/04 16:08:09')

    def test_parse_time(self):
        i18n.set_locale('en_US')
        self.assertEqual(i18n.parse_time('18:08:09'), datetime.time(18, 8, 9))
        i18n.set_locale('de_DE')
        self.assertEqual(i18n.parse_time('18:08:09'), datetime.time(18, 8, 9))

    def test_format_timedelta(self):
        # This is only present in Babel dev, so skip if not available.
        if not getattr(i18n, 'format_timedelta', None):
            return

        i18n.set_locale('en_US')
        # ???
        # self.assertEqual(i18n.format_timedelta(datetime.timedelta(weeks=12)), u'3 months')
        self.assertEqual(i18n.format_timedelta(datetime.timedelta(weeks=12)), u'3 mths')
        i18n.set_locale('es')
        # self.assertEqual(i18n.format_timedelta(datetime.timedelta(seconds=1)), u'1 segundo')
        self.assertEqual(i18n.format_timedelta(datetime.timedelta(seconds=1)), u'1 s')
        i18n.set_locale('en_US')
        self.assertEqual(i18n.format_timedelta(datetime.timedelta(hours=3), granularity='day'), u'1 day')
        self.assertEqual(i18n.format_timedelta(datetime.timedelta(hours=23), threshold=0.9), u'1 day')
        # self.assertEqual(i18n.format_timedelta(datetime.timedelta(hours=23), threshold=1.1), u'23 hours')
        self.assertEqual(i18n.format_timedelta(datetime.timedelta(hours=23), threshold=1.1), u'23 hrs')
        self.assertEqual(i18n.format_timedelta(datetime.datetime.now() - datetime.timedelta(days=5)), u'5 days')

    def test_format_iso(self):
        value = datetime.datetime(2009, 11, 10, 16, 36, 05)

        self.assertEqual(i18n.format_date(value, format='iso'), u'2009-11-10')
        self.assertEqual(i18n.format_time(value, format='iso'), u'16:36:05')
        self.assertEqual(i18n.format_datetime(value, format='iso'), u'2009-11-10T16:36:05+0000')

    #==========================================================================
    # Timezones
    #==========================================================================

    def test_set_timezone(self):
        request = get_request()
        request.i18n.set_timezone('UTC')
        self.assertEqual(request.i18n.tzinfo.zone, 'UTC')

        request.i18n.set_timezone('America/Chicago')
        self.assertEqual(request.i18n.tzinfo.zone, 'America/Chicago')

        request.i18n.set_timezone('America/Sao_Paulo')
        self.assertEqual(request.i18n.tzinfo.zone, 'America/Sao_Paulo')

    def test_to_local_timezone(self):
        request = get_request()
        request.i18n.set_timezone('US/Eastern')

        format = '%Y-%m-%d %H:%M:%S %Z%z'

        # Test datetime with timezone set
        base = datetime.datetime(2002, 10, 27, 6, 0, 0, tzinfo=pytz.UTC)
        localtime = i18n.to_local_timezone(base)
        result = localtime.strftime(format)
        self.assertEqual(result, '2002-10-27 01:00:00 EST-0500')

        # Test naive datetime - no timezone set
        base = datetime.datetime(2002, 10, 27, 6, 0, 0)
        localtime = i18n.to_local_timezone(base)
        result = localtime.strftime(format)
        self.assertEqual(result, '2002-10-27 01:00:00 EST-0500')

    def test_to_utc(self):
        request = get_request()
        request.i18n.set_timezone('US/Eastern')

        format = '%Y-%m-%d %H:%M:%S'

        # Test datetime with timezone set
        base = datetime.datetime(2002, 10, 27, 6, 0, 0, tzinfo=pytz.UTC)
        localtime = i18n.to_utc(base)
        result = localtime.strftime(format)

        self.assertEqual(result, '2002-10-27 06:00:00')

        # Test naive datetime - no timezone set
        base = datetime.datetime(2002, 10, 27, 6, 0, 0)
        localtime = i18n.to_utc(base)
        result = localtime.strftime(format)
        self.assertEqual(result, '2002-10-27 11:00:00')

    def test_get_timezone_location(self):
        i18n.set_locale('de_DE')
        self.assertEqual(i18n.get_timezone_location(pytz.timezone('America/St_Johns')), u'Kanada (St. John\'s)')
        i18n.set_locale('de_DE')
        self.assertEqual(i18n.get_timezone_location(pytz.timezone('America/Mexico_City')), u'Mexiko (Mexiko-Stadt)')
        i18n.set_locale('de_DE')
        self.assertEqual(i18n.get_timezone_location(pytz.timezone('Europe/Berlin')), u'Deutschland')

    #==========================================================================
    # Number formatting
    #==========================================================================

    def test_format_number(self):
        i18n.set_locale('en_US')
        self.assertEqual(i18n.format_number(1099), u'1,099')

    def test_format_decimal(self):
        i18n.set_locale('en_US')
        self.assertEqual(i18n.format_decimal(1.2345), u'1.234')
        self.assertEqual(i18n.format_decimal(1.2346), u'1.235')
        self.assertEqual(i18n.format_decimal(-1.2346), u'-1.235')
        self.assertEqual(i18n.format_decimal(12345.5), u'12,345.5')

        i18n.set_locale('sv_SE')
        self.assertEqual(i18n.format_decimal(1.2345), u'1,234')

        i18n.set_locale('de')
        self.assertEqual(i18n.format_decimal(12345), u'12.345')

    def test_format_currency(self):
        i18n.set_locale('en_US')
        self.assertEqual(i18n.format_currency(1099.98, 'USD'), u'$1,099.98')
        self.assertEqual(i18n.format_currency(1099.98, 'EUR', u'\xa4\xa4 #,##0.00'), u'EUR 1,099.98')

        i18n.set_locale('es_CO')
        self.assertEqual(i18n.format_currency(1099.98, 'USD'), u'US$\xa01.099,98')

        i18n.set_locale('de_DE')
        self.assertEqual(i18n.format_currency(1099.98, 'EUR'), u'1.099,98\xa0\u20ac')

    def test_format_percent(self):
        i18n.set_locale('en_US')
        self.assertEqual(i18n.format_percent(0.34), u'34%')
        self.assertEqual(i18n.format_percent(25.1234), u'2,512%')
        self.assertEqual(i18n.format_percent(25.1234, u'#,##0\u2030'), u'25,123\u2030')

        i18n.set_locale('sv_SE')
        self.assertEqual(i18n.format_percent(25.1234), u'2\xa0512\xa0%')

    def test_format_scientific(self):
        i18n.set_locale('en_US')
        self.assertEqual(i18n.format_scientific(10000), u'1E4')
        self.assertEqual(i18n.format_scientific(1234567, u'##0E00'), u'1.23E06')

    def test_parse_number(self):
        i18n.set_locale('en_US')
        self.assertEqual(i18n.parse_number('1,099'), 1099L)

        i18n.set_locale('de_DE')
        self.assertEqual(i18n.parse_number('1.099'), 1099L)

    def test_parse_number2(self):
        i18n.set_locale('de')
        self.assertRaises(NumberFormatError, i18n.parse_number, '1.099,98')

    def test_parse_decimal(self):
        i18n.set_locale('en_US')
        self.assertEqual(i18n.parse_decimal('1,099.98'), 1099.98)

        i18n.set_locale('de')
        self.assertEqual(i18n.parse_decimal('1.099,98'), 1099.98)

    def test_parse_decimal_error(self):
        i18n.set_locale('de')
        self.assertRaises(NumberFormatError, i18n.parse_decimal, '2,109,998')

    #==========================================================================
    # Miscelaneous
    #==========================================================================

    def test_list_translations(self):
        cwd = os.getcwd()
        os.chdir(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'resources'))

        translations = i18n.list_translations()

        self.assertEqual(len(translations), 2)
        self.assertEqual(translations[0].language, 'en')
        self.assertEqual(translations[0].territory, 'US')
        self.assertEqual(translations[1].language, 'pt')
        self.assertEqual(translations[1].territory, 'BR')

        os.chdir(cwd)

    def test_list_translations_no_locale_dir(self):
        cwd = os.getcwd()
        os.chdir(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'resources', 'locale'))

        self.assertEqual(i18n.list_translations(), [])

        os.chdir(cwd)


if __name__ == '__main__':
    test_utils.main()

########NEW FILE########
__FILENAME__ = manage_test
# -*- coding: utf-8 -*-
"""
    Tests for tipfy.scripts.manage
"""
from __future__ import with_statement

import ConfigParser
import os
import textwrap
import StringIO
import sys
import unittest
import StringIO

import test_utils
'''
from tipfy.manage.config import Config


class TestConfig(test_utils.BaseTestCase):
    def get_fp(self, config):
        return StringIO.StringIO(textwrap.dedent(config))

    def test_get(self):
        fp = self.get_fp("""\
        [DEFAULT]
        foo = bar

        [section_1]
        baz = ding
        """)
        config = Config()
        config.readfp(fp)

        self.assertEqual(config.get('section_1', 'foo'), 'bar')
        self.assertEqual(config.get('section_1', 'baz'), 'ding')

        # Invalid key.
        self.assertEqual(config.get('section_1', 'invalid'), None)

    def test_getboolean(self):
        fp = self.get_fp("""\
        [DEFAULT]
        true_1 = 1
        true_2 = yes
        false_1 = 0
        false_2 = no

        [section_1]
        true_3 = on
        true_4 = true
        false_3 = off
        false_4 = false
        invalid = bar
        """)
        config = Config()
        config.readfp(fp)

        self.assertEqual(config.getboolean('section_1', 'true_1'), True)
        self.assertEqual(config.getboolean('section_1', 'true_2'), True)
        self.assertEqual(config.getboolean('section_1', 'true_3'), True)
        self.assertEqual(config.getboolean('section_1', 'true_4'), True)
        self.assertEqual(config.getboolean('section_1', 'false_1'), False)
        self.assertEqual(config.getboolean('section_1', 'false_2'), False)
        self.assertEqual(config.getboolean('section_1', 'false_3'), False)
        self.assertEqual(config.getboolean('section_1', 'false_4'), False)

        # Invalid boolean.
        self.assertEqual(config.getboolean('section_1', 'invalid'), None)

    def test_getfloat(self):
        fp = self.get_fp("""\
        [DEFAULT]
        foo = 0.1

        [section_1]
        baz = 0.2
        invalid = bar
        """)
        config = Config()
        config.readfp(fp)

        self.assertEqual(config.getfloat('section_1', 'foo'), 0.1)
        self.assertEqual(config.getfloat('section_1', 'baz'), 0.2)

        # Invalid float.
        self.assertEqual(config.getboolean('section_1', 'invalid'), None)

    def test_getint(self):
        fp = self.get_fp("""\
        [DEFAULT]
        foo = 999

        [section_1]
        baz = 1999
        invalid = bar
        """)
        config = Config()
        config.readfp(fp)

        self.assertEqual(config.getint('section_1', 'foo'), 999)
        self.assertEqual(config.getint('section_1', 'baz'), 1999)

        # Invalid int.
        self.assertEqual(config.getboolean('section_1', 'invalid'), None)

    def test_getlist(self):
        fp = self.get_fp("""\
        [DEFAULT]
        animals =
            rhino
            rhino
            hamster
            hamster
            goat
            goat

        [section_1]
        fruits =
            orange
            watermellow
            grape
        """)
        config = Config()
        config.readfp(fp)

        # Non-unique values.
        self.assertEqual(config.getlist('section_1', 'animals'), [
            'rhino',
            'rhino',
            'hamster',
            'hamster',
            'goat',
            'goat',
        ])
        self.assertEqual(config.getlist('section_1', 'fruits'), [
            'orange',
            'watermellow',
            'grape',
        ])

        # Unique values.
        self.assertEqual(config.getlist('section_1', 'animals', unique=True), [
            'rhino',
            'hamster',
            'goat',
        ])

    def test_interpolation(self):
        fp = self.get_fp("""\
        [DEFAULT]
        path = /path/to/%(path_name)s

        [section_1]
        path_name = foo
        path_1 = /special%(path)s
        path_2 = /special/%(path_name)s

        [section_2]
        path_name = bar

        [section_3]
        path_1 = /path/to/%(section_1|path_name)s
        path_2 = /path/to/%(section_2|path_name)s
        path_3 = /%(section_1|path_name)s/%(section_2|path_name)s/%(section_1|path_name)s/%(section_2|path_name)s
        path_error_1 = /path/to/%(section_3|path_error_1)s
        path_error_2 = /path/to/%(section_3|path_error_3)s
        path_error_3 = /path/to/%(section_3|path_error_2)s
        path_not_really = /path/to/%(foo
        """)
        config = Config()
        config.readfp(fp)

        self.assertEqual(config.get('section_1', 'path'), '/path/to/foo')
        self.assertEqual(config.get('section_1', 'path_1'), '/special/path/to/foo')
        self.assertEqual(config.get('section_1', 'path_2'), '/special/foo')
        self.assertEqual(config.get('section_2', 'path'), '/path/to/bar')

        self.assertEqual(config.get('section_3', 'path_1'), '/path/to/foo')
        self.assertEqual(config.get('section_3', 'path_2'), '/path/to/bar')
        self.assertEqual(config.get('section_3', 'path_3'), '/foo/bar/foo/bar')

        # Failed interpolation (recursive)
        self.assertRaises(ConfigParser.InterpolationError, config.get,
            'section_3', 'path_error_1')
        self.assertRaises(ConfigParser.InterpolationError, config.get,
            'section_3', 'path_error_2')
        self.assertRaises(ConfigParser.InterpolationError, config.get,
            'section_3', 'path_error_3')

        self.assertEqual(config.get('section_3', 'path_not_really'), '/path/to/%(foo')
'''


if __name__ == '__main__':
    test_utils.main()

########NEW FILE########
__FILENAME__ = alternative_routing
from tipfy import RequestHandler, Response

class HomeHandler(RequestHandler):
    def get(self, **kwargs):
        return Response('home-get')

    def foo(self, **kwargs):
        return Response('home-foo')

    def bar(self, **kwargs):
        return Response('home-bar')


class OtherHandler(RequestHandler):
    def foo(self, **kwargs):
        return Response('other-foo')

    def bar(self, **kwargs):
        return Response('other-bar')


def home(request):
    return 'home'


def foo(request):
    return 'foo'


def bar(request):
    return 'bar'

########NEW FILE########
__FILENAME__ = handlers
from tipfy import RequestHandler, Response


class HomeHandler(RequestHandler):
    def get(self, **kwargs):
        return Response('Hello, World!')

class HandlerWithRuleDefaults(RequestHandler):
    def get(self, **kwargs):
        return Response(kwargs.get('foo'))


class HandlerWithException(RequestHandler):
    def get(self, **kwargs):
        raise ValueError('ooops!')


########NEW FILE########
__FILENAME__ = i18n
from tipfy import REQUIRED_VALUE

default_config = {
    'locale': 'en_US',
    'timezone': 'America/Chicago',
    'required': REQUIRED_VALUE,
}

########NEW FILE########
__FILENAME__ = jinja2_after_environment_created
def after_creation(environment):
    environment.filters['ho'] = lambda x: x + ', Ho!'

########NEW FILE########
__FILENAME__ = mail_handlers
from tipfy import Response

from tipfy.appengine.mail import InboundMailHandler


class MailHandler(InboundMailHandler):
    def receive(self, mail_message, **kwargs):
        for content_type, body in mail_message.bodies('text/plain'):
            decoded = body.decode()
            if decoded:
                return Response(decoded)

        return Response('')


class MailHandler2(InboundMailHandler):
    pass

########NEW FILE########
__FILENAME__ = template
default_config = {
    'templates_dir': 'templates',
}

########NEW FILE########
__FILENAME__ = tmpl_3a79873b1b49be244fd5444b1258ce348be26de8
from __future__ import division
from jinja2.runtime import LoopContext, TemplateReference, Macro, Markup, TemplateRuntimeError, missing, concat, escape, markup_join, unicode_join, to_string, TemplateNotFound
name = 'template1.html'

def root(context):
    l_message = context.resolve('message')
    if 0: yield None
    yield to_string(l_message)

blocks = {}
debug_info = '1=8'
########NEW FILE########
__FILENAME__ = xmpp_handlers
from tipfy.appengine.xmpp import BaseHandler, CommandHandler


class XmppHandler(CommandHandler):
    def foo_command(self, message):
        message.reply('Foo command!')

    def bar_command(self, message):
        message.reply('Bar command!')

    def text_message(self, message):
        super(XmppHandler, self).text_message(message)
        message.reply(message.body)


class XmppHandler2(BaseHandler):
    pass

########NEW FILE########
__FILENAME__ = routing_test
from __future__ import with_statement

from tipfy import Tipfy, RequestHandler, Response
from tipfy.routing import HandlerPrefix, NamePrefix, Router, Rule
from tipfy.utils import url_for

import test_utils


class TestRouter(test_utils.BaseTestCase):
    def test_add(self):
        app = Tipfy()
        router = Router(app)
        self.assertEqual(len(list(router.map.iter_rules())), 0)

        router.add(Rule('/', name='home', handler='HomeHandler'))
        self.assertEqual(len(list(router.map.iter_rules())), 1)

        router.add([
            Rule('/about', name='about', handler='AboutHandler'),
            Rule('/contact', name='contact', handler='ContactHandler'),
        ])
        self.assertEqual(len(list(router.map.iter_rules())), 3)


class TestRouting(test_utils.BaseTestCase):
    #==========================================================================
    # HandlerPrefix
    #==========================================================================
    def test_handler_prefix(self):
        rules = [
            HandlerPrefix('resources.handlers.', [
                Rule('/', name='home', handler='HomeHandler'),
                Rule('/defaults', name='defaults', handler='HandlerWithRuleDefaults', defaults={'foo': 'bar'}),
            ])
        ]

        app = Tipfy(rules)
        client = app.get_test_client()

        response = client.get('/')
        self.assertEqual(response.data, 'Hello, World!')

        response = client.get('/defaults')
        self.assertEqual(response.data, 'bar')

    #==========================================================================
    # NamePrefix
    #==========================================================================
    def test_name_prefix(self):
        class DummyHandler(RequestHandler):
            def get(self, **kwargs):
                return ''

        rules = [
            NamePrefix('company-', [
                Rule('/', name='home', handler=DummyHandler),
                Rule('/about', name='about', handler=DummyHandler),
                Rule('/contact', name='contact', handler=DummyHandler),
            ]),
        ]

        app = Tipfy(rules)

        with app.get_test_handler('/') as handler:
            self.assertEqual(handler.url_for('company-home'), '/')
            self.assertEqual(handler.url_for('company-about'), '/about')
            self.assertEqual(handler.url_for('company-contact'), '/contact')

        with app.get_test_handler('/') as handler:
            self.assertEqual(handler.request.rule.name, 'company-home')

        with app.get_test_handler('/about') as handler:
            self.assertEqual(handler.request.rule.name, 'company-about')

        with app.get_test_handler('/contact') as handler:
            self.assertEqual(handler.request.rule.name, 'company-contact')

    #==========================================================================
    # RegexConverter
    #==========================================================================
    def test_regex_converter(self):
        class TestHandler(RequestHandler):
            def get(self, **kwargs):
                return Response(kwargs.get('path'))

        app = Tipfy([
            Rule('/<regex(".*"):path>', name='home', handler=TestHandler),
        ])
        client = app.get_test_client()

        response = client.get('/foo')
        self.assertEqual(response.data, 'foo')

        response = client.get('/foo/bar')
        self.assertEqual(response.data, 'foo/bar')

        response = client.get('/foo/bar/baz')
        self.assertEqual(response.data, 'foo/bar/baz')

    def test_url_for(self):
        class DummyHandler(RequestHandler):
            def get(self, **kwargs):
                return ''

        rules = [
            NamePrefix('company-', [
                Rule('/', name='home', handler=DummyHandler),
                Rule('/about', name='about', handler=DummyHandler),
                Rule('/contact', name='contact', handler=DummyHandler),
            ]),
        ]

        app = Tipfy(rules)

        with app.get_test_handler('/') as handler:
            self.assertEqual(url_for('company-home'), '/')
            self.assertEqual(url_for('company-about'), '/about')
            self.assertEqual(url_for('company-contact'), '/contact')


class TestAlternativeRouting(test_utils.BaseTestCase):
    def test_handler(self):
        rules = [
            HandlerPrefix('resources.alternative_routing.', [
                Rule('/', name='home', handler='HomeHandler'),
                Rule('/foo', name='home/foo', handler='HomeHandler:foo'),
                Rule('/bar', name='home/bar', handler='HomeHandler:bar'),
                Rule('/other/foo', name='other/foo', handler='OtherHandler:foo'),
                Rule('/other/bar', name='other/bar', handler='OtherHandler:bar'),
            ])
        ]

        app = Tipfy(rules)
        client = app.get_test_client()

        response = client.get('/')
        self.assertEqual(response.data, 'home-get')
        response = client.get('/foo')
        self.assertEqual(response.data, 'home-foo')
        response = client.get('/bar')
        self.assertEqual(response.data, 'home-bar')
        response = client.get('/other/foo')
        self.assertEqual(response.data, 'other-foo')
        response = client.get('/other/bar')
        self.assertEqual(response.data, 'other-bar')

    def test_function_handler(self):
        rules = [
            HandlerPrefix('resources.alternative_routing.', [
                Rule('/', name='home', handler='home'),
                Rule('/foo', name='home/foo', handler='foo'),
                Rule('/bar', name='home/bar', handler='bar'),
            ])
        ]

        app = Tipfy(rules)
        client = app.get_test_client()

        response = client.get('/')
        self.assertEqual(response.data, 'home')
        response = client.get('/foo')
        self.assertEqual(response.data, 'foo')
        response = client.get('/bar')
        self.assertEqual(response.data, 'bar')


if __name__ == '__main__':
    test_utils.main()

########NEW FILE########
__FILENAME__ = secure_cookie_test
import time
import unittest

from tipfy import Tipfy, Request, Response
from tipfy.sessions import SessionStore, SecureCookieStore, SecureCookieSession

import test_utils


class TestSecureCookie(test_utils.BaseTestCase):
    def _get_app(self):
        return Tipfy(config={
            'tipfy.sessions': {
                'secret_key': 'something very secret',
            }
        })

    def test_get_cookie_no_cookie(self):
        store = SecureCookieStore('secret')
        request = Request.from_values('/')
        self.assertEqual(store.get_cookie(request, 'session'), None)

    def test_get_cookie_invalid_parts(self):
        store = SecureCookieStore('secret')
        request = Request.from_values('/', headers=[('Cookie', 'session="invalid"; Path=/')])
        self.assertEqual(store.get_cookie(request, 'session'), None)

    def test_get_cookie_invalid_signature(self):
        store = SecureCookieStore('secret')
        request = Request.from_values('/', headers=[('Cookie', 'session="foo|bar|baz"; Path=/')])
        self.assertEqual(store.get_cookie(request, 'session'), None)

    def test_get_cookie_expired(self):
        store = SecureCookieStore('secret')
        request = Request.from_values('/', headers=[('Cookie', 'session="eyJmb28iOiJiYXIifQ==|1284849476|847b472f2fabbf1efef55748a394b6f182acd8be"; Path=/')])
        self.assertEqual(store.get_cookie(request, 'session', max_age=-86400), None)

    def test_get_cookie_badly_encoded(self):
        store = SecureCookieStore('secret')
        timestamp = str(int(time.time()))
        value = 'foo'
        signature = store._get_signature('session', value, timestamp)
        cookie_value = '|'.join([value, timestamp, signature])

        request = Request.from_values('/', headers=[('Cookie', 'session="%s"; Path=/' % cookie_value)])
        self.assertEqual(store.get_cookie(request, 'session'), None)

    def test_get_cookie_valid(self):
        store = SecureCookieStore('secret')
        request = Request.from_values('/', headers=[('Cookie', 'session="eyJmb28iOiJiYXIifQ==|1284849476|847b472f2fabbf1efef55748a394b6f182acd8be"; Path=/')])
        self.assertEqual(store.get_cookie(request, 'session'), {'foo': 'bar'})


if __name__ == '__main__':
    test_utils.main()

########NEW FILE########
__FILENAME__ = sessions_test
from __future__ import with_statement

import os
import unittest

from werkzeug import cached_property

from tipfy.app import App, Request, Response
from tipfy.handler import RequestHandler
from tipfy.json import json_b64decode
from tipfy.local import local
from tipfy.routing import Rule
from tipfy.sessions import (SecureCookieSession, SecureCookieStore,
    SessionMiddleware, SessionStore)
from tipfy.appengine.sessions import (DatastoreSession, MemcacheSession,
    SessionModel)

import test_utils


class BaseHandler(RequestHandler):
    middleware = [SessionMiddleware()]


class TestSessionStoreBase(test_utils.BaseTestCase):
    def _get_app(self):
        return App(config={
            'tipfy.sessions': {
                'secret_key': 'secret',
            }
        })

    def test_secure_cookie_store(self):
        with self._get_app().get_test_context() as request:
            store = request.session_store
            self.assertEqual(isinstance(store.secure_cookie_store, SecureCookieStore), True)

    def test_secure_cookie_store_no_secret_key(self):
        with App().get_test_context() as request:
            store = request.session_store
            self.assertRaises(KeyError, getattr, store, 'secure_cookie_store')

    def test_get_cookie_args(self):
        with self._get_app().get_test_context() as request:
            store = request.session_store

            self.assertEqual(store.get_cookie_args(), {
                'max_age':     None,
                'domain':      None,
                'path':        '/',
                'secure':      None,
                'httponly':    False,
            })

            self.assertEqual(store.get_cookie_args(max_age=86400, domain='.foo.com'), {
                'max_age':     86400,
                'domain':      '.foo.com',
                'path':        '/',
                'secure':      None,
                'httponly':    False,
            })

    def test_get_save_session(self):
        with self._get_app().get_test_context() as request:
            store = request.session_store

            session = store.get_session()
            self.assertEqual(isinstance(session, SecureCookieSession), True)
            self.assertEqual(session, {})

            session['foo'] = 'bar'

            response = Response()
            store.save(response)

        with self._get_app().get_test_context('/', headers={'Cookie': '\n'.join(response.headers.getlist('Set-Cookie'))}) as request:
            store = request.session_store

            session = store.get_session()
            self.assertEqual(isinstance(session, SecureCookieSession), True)
            self.assertEqual(session, {'foo': 'bar'})

    def test_set_delete_cookie(self):
        with self._get_app().get_test_context() as request:
            store = request.session_store

            store.set_cookie('foo', 'bar')
            store.set_cookie('baz', 'ding')

            response = Response()
            store.save(response)

        headers = {'Cookie': '\n'.join(response.headers.getlist('Set-Cookie'))}
        with self._get_app().get_test_context('/', headers=headers) as request:
            store = request.session_store

            self.assertEqual(request.cookies.get('foo'), 'bar')
            self.assertEqual(request.cookies.get('baz'), 'ding')

            store.delete_cookie('foo')
            store.save(response)

        headers = {'Cookie': '\n'.join(response.headers.getlist('Set-Cookie'))}
        with self._get_app().get_test_context('/', headers=headers) as request:
            self.assertEqual(request.cookies.get('foo', None), '')
            self.assertEqual(request.cookies['baz'], 'ding')

    def test_set_cookie_encoded(self):
        with self._get_app().get_test_context() as request:
            store = request.session_store

            store.set_cookie('foo', 'bar', format='json')
            store.set_cookie('baz', 'ding', format='json')

            response = Response()
            store.save(response)

        headers = {'Cookie': '\n'.join(response.headers.getlist('Set-Cookie'))}
        with self._get_app().get_test_context('/', headers=headers) as request:
            store = request.session_store

            self.assertEqual(json_b64decode(request.cookies.get('foo')), 'bar')
            self.assertEqual(json_b64decode(request.cookies.get('baz')), 'ding')


class TestSessionStore(test_utils.BaseTestCase):
    def setUp(self):
        SessionStore.default_backends.update({
            'datastore':    DatastoreSession,
            'memcache':     MemcacheSession,
            'securecookie': SecureCookieSession,
        })
        test_utils.BaseTestCase.setUp(self)

    def _get_app(self, *args, **kwargs):
        app = App(config={
            'tipfy.sessions': {
                'secret_key': 'secret',
            },
        })
        return app

    def test_set_session(self):
        class MyHandler(BaseHandler):
            def get(self):
                res = self.session.get('key')
                if not res:
                    res = 'undefined'
                    session = SecureCookieSession()
                    session['key'] = 'a session value'
                    self.session_store.set_session(self.session_store.config['cookie_name'], session)

                return Response(res)

        rules = [Rule('/', name='test', handler=MyHandler)]

        app = self._get_app('/')
        app.router.add(rules)
        client = app.get_test_client()

        response = client.get('/')
        self.assertEqual(response.data, 'undefined')

        response = client.get('/', headers={
            'Cookie': '\n'.join(response.headers.getlist('Set-Cookie')),
        })
        self.assertEqual(response.data, 'a session value')

    def test_set_session_datastore(self):
        class MyHandler(BaseHandler):
            def get(self):
                session = self.session_store.get_session(backend='datastore')
                res = session.get('key')
                if not res:
                    res = 'undefined'
                    session = DatastoreSession(None, 'a_random_session_id')
                    session['key'] = 'a session value'
                    self.session_store.set_session(self.session_store.config['cookie_name'], session, backend='datastore')

                return Response(res)

        rules = [Rule('/', name='test', handler=MyHandler)]

        app = self._get_app('/')
        app.router.add(rules)
        client = app.get_test_client()

        response = client.get('/')
        self.assertEqual(response.data, 'undefined')

        response = client.get('/', headers={
            'Cookie': '\n'.join(response.headers.getlist('Set-Cookie')),
        })
        self.assertEqual(response.data, 'a session value')

    def test_get_memcache_session(self):
        class MyHandler(BaseHandler):
            def get(self):
                session = self.session_store.get_session(backend='memcache')
                res = session.get('test')
                if not res:
                    res = 'undefined'
                    session['test'] = 'a memcache session value'

                return Response(res)

        rules = [Rule('/', name='test', handler=MyHandler)]

        app = self._get_app('/')
        app.router.add(rules)
        client = app.get_test_client()

        response = client.get('/')
        self.assertEqual(response.data, 'undefined')

        response = client.get('/', headers={
            'Cookie': '\n'.join(response.headers.getlist('Set-Cookie')),
        })
        self.assertEqual(response.data, 'a memcache session value')

    def test_get_datastore_session(self):
        class MyHandler(BaseHandler):
            def get(self):
                session = self.session_store.get_session(backend='datastore')
                res = session.get('test')
                if not res:
                    res = 'undefined'
                    session['test'] = 'a datastore session value'

                return Response(res)

        rules = [Rule('/', name='test', handler=MyHandler)]

        app = self._get_app('/')
        app.router.add(rules)
        client = app.get_test_client()

        response = client.get('/')
        self.assertEqual(response.data, 'undefined')

        response = client.get('/', headers={
            'Cookie': '\n'.join(response.headers.getlist('Set-Cookie')),
        })
        self.assertEqual(response.data, 'a datastore session value')

    def test_set_delete_cookie(self):
        class MyHandler(BaseHandler):
            def get(self):
                res = self.request.cookies.get('test')
                if not res:
                    res = 'undefined'
                    self.session_store.set_cookie('test', 'a cookie value')
                else:
                    self.session_store.delete_cookie('test')

                return Response(res)

        rules = [Rule('/', name='test', handler=MyHandler)]

        app = self._get_app('/')
        app.router.add(rules)
        client = app.get_test_client()

        response = client.get('/')
        self.assertEqual(response.data, 'undefined')

        response = client.get('/', headers={
            'Cookie': '\n'.join(response.headers.getlist('Set-Cookie')),
        })
        self.assertEqual(response.data, 'a cookie value')

        response = client.get('/', headers={
            'Cookie': '\n'.join(response.headers.getlist('Set-Cookie')),
        })
        self.assertEqual(response.data, 'undefined')

        response = client.get('/', headers={
            'Cookie': '\n'.join(response.headers.getlist('Set-Cookie')),
        })
        self.assertEqual(response.data, 'a cookie value')

    def test_set_unset_cookie(self):
        class MyHandler(BaseHandler):
            def get(self):
                res = self.request.cookies.get('test')
                if not res:
                    res = 'undefined'
                    self.session_store.set_cookie('test', 'a cookie value')

                self.session_store.unset_cookie('test')
                return Response(res)

        rules = [Rule('/', name='test', handler=MyHandler)]

        app = self._get_app('/')
        app.router.add(rules)
        client = app.get_test_client()

        response = client.get('/')
        self.assertEqual(response.data, 'undefined')

        response = client.get('/', headers={
            'Cookie': '\n'.join(response.headers.getlist('Set-Cookie')),
        })
        self.assertEqual(response.data, 'undefined')

    def test_set_get_secure_cookie(self):
        class MyHandler(BaseHandler):
            def get(self):
                response = Response()

                cookie = self.session_store.get_secure_cookie('test') or {}
                res = cookie.get('test')
                if not res:
                    res = 'undefined'
                    self.session_store.set_secure_cookie(response, 'test', {'test': 'a secure cookie value'})

                response.data = res
                return response

        rules = [Rule('/', name='test', handler=MyHandler)]

        app = self._get_app('/')
        app.router.add(rules)
        client = app.get_test_client()

        response = client.get('/')
        self.assertEqual(response.data, 'undefined')

        response = client.get('/', headers={
            'Cookie': '\n'.join(response.headers.getlist('Set-Cookie')),
        })
        self.assertEqual(response.data, 'a secure cookie value')

    def test_set_get_flashes(self):
        class MyHandler(BaseHandler):
            def get(self):
                res = [msg for msg, level in self.session.get_flashes()]
                if not res:
                    res = [{'body': 'undefined'}]
                    self.session.flash({'body': 'a flash value'})

                return Response(res[0]['body'])

        rules = [Rule('/', name='test', handler=MyHandler)]

        app = self._get_app('/')
        app.router.add(rules)
        client = app.get_test_client()

        response = client.get('/')
        self.assertEqual(response.data, 'undefined')

        response = client.get('/', headers={
            'Cookie': '\n'.join(response.headers.getlist('Set-Cookie')),
        })
        self.assertEqual(response.data, 'a flash value')

    def test_set_get_messages(self):
        class MyHandler(BaseHandler):
            @cached_property
            def messages(self):
                """A list of status messages to be displayed to the user."""
                messages = []
                flashes = self.session.get_flashes(key='_messages')
                for msg, level in flashes:
                    msg['level'] = level
                    messages.append(msg)

                return messages

            def set_message(self, level, body, title=None, life=None, flash=False):
                """Adds a status message.

                :param level:
                    Message level. Common values are "success", "error", "info" or
                    "alert".
                :param body:
                    Message contents.
                :param title:
                    Optional message title.
                :param life:
                    Message life time in seconds. User interface can implement
                    a mechanism to make the message disappear after the elapsed time.
                    If not set, the message is permanent.
                :returns:
                    None.
                """
                message = {'title': title, 'body': body, 'life': life}
                if flash is True:
                    self.session.flash(message, level, '_messages')
                else:
                    self.messages.append(message)

            def get(self):
                self.set_message('success', 'a normal message value')
                self.set_message('success', 'a flash message value', flash=True)
                return Response('|'.join(msg['body'] for msg in self.messages))

        rules = [Rule('/', name='test', handler=MyHandler)]

        app = self._get_app('/')
        app.router.add(rules)
        client = app.get_test_client()

        response = client.get('/')
        self.assertEqual(response.data, 'a normal message value')

        response = client.get('/', headers={
            'Cookie': '\n'.join(response.headers.getlist('Set-Cookie')),
        })
        self.assertEqual(response.data, 'a flash message value|a normal message value')


class TestSessionModel(test_utils.BaseTestCase):
    def setUp(self):
        self.app = App()
        test_utils.BaseTestCase.setUp(self)

    def test_get_by_sid_without_cache(self):
        sid = 'test'
        entity = SessionModel.create(sid, {'foo': 'bar', 'baz': 'ding'})
        entity.put()

        cached_data = SessionModel.get_cache(sid)
        self.assertNotEqual(cached_data, None)

        entity.delete_cache()
        cached_data = SessionModel.get_cache(sid)
        self.assertEqual(cached_data, None)

        entity = SessionModel.get_by_sid(sid)
        self.assertNotEqual(entity, None)

        # Now will fetch cache.
        entity = SessionModel.get_by_sid(sid)
        self.assertNotEqual(entity, None)

        self.assertEqual('foo' in entity.data, True)
        self.assertEqual('baz' in entity.data, True)
        self.assertEqual(entity.data['foo'], 'bar')
        self.assertEqual(entity.data['baz'], 'ding')

        entity.delete()
        entity = SessionModel.get_by_sid(sid)
        self.assertEqual(entity, None)


if __name__ == '__main__':
    test_utils.main()

########NEW FILE########
__FILENAME__ = template_test
import os
import unittest

from tipfy import template

import test_utils

TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
    'resources', 'templates'))
TEMPLATES_ZIP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
    'resources', 'templates.zip'))


class TestTemplate(test_utils.BaseTestCase):
    def test_generate(self):
        t = template.Template('<html>{{ myvalue }}</html>')
        self.assertEqual(t.generate(myvalue='XXX'), '<html>XXX</html>')

    def test_loader(self):
        loader = template.Loader(TEMPLATES_DIR)
        t = loader.load('template_tornado1.html')
        self.assertEqual(t.generate(students=['calvin', 'hobbes', 'moe']), '\n\ncalvin\n\n\n\nhobbes\n\n\n\nmoe\n\n\n')

    def test_loader2(self):
        loader = template.ZipLoader(TEMPLATES_ZIP_DIR, 'templates')
        t = loader.load('template1.html')
        self.assertEqual(t.generate(message='Hello, World!'), 'Hello, World!\n')


if __name__ == '__main__':
    test_utils.main()

########NEW FILE########
__FILENAME__ = test_utils
"""Test utlities for writing NDB tests.

Useful set of utilities for correctly setting up the appengine testing
environment.  Functions and test-case base classes that configure stubs
and other environment variables.

Borrowed from http://code.google.com/p/appengine-ndb-experiment/
"""
import os
import unittest

from google.appengine.api import apiproxy_stub_map
from google.appengine.api import datastore_file_stub
from google.appengine.api.memcache import memcache_stub
from google.appengine.api import memcache
from google.appengine.api.taskqueue import taskqueue_stub
from google.appengine.api import user_service_stub

from tipfy.local import local


def main():
    unittest.main()


def set_up_basic_stubs(app_id):
    """Set up a basic set of stubs.

    Configures datastore and memcache stubs for testing.

    Args:
    app_id: Application ID to configure stubs with.

    Returns:
    Dictionary mapping stub name to stub.
    """
    apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap()

    ds_stub = datastore_file_stub.DatastoreFileStub(app_id, None)
    apiproxy_stub_map.apiproxy.RegisterStub('datastore_v3', ds_stub)

    mc_stub = memcache_stub.MemcacheServiceStub()
    apiproxy_stub_map.apiproxy.RegisterStub('memcache', mc_stub)

    tq_stub = taskqueue_stub.TaskQueueServiceStub()
    apiproxy_stub_map.apiproxy.RegisterStub('taskqueue', tq_stub)

    user_stub = user_service_stub.UserServiceStub()
    apiproxy_stub_map.apiproxy.RegisterStub('user', user_stub)

    return {
        'datastore': ds_stub,
        'memcache': mc_stub,
        'taskqueue': tq_stub,
        'user': user_stub,
    }


class BaseTestCase(unittest.TestCase):
    """Base class for tests that actually interact with the (stub) Datastore.

    NOTE: Care must be used when working with model classes using this test
    class.  The kind-map is reset on each iteration.  The general practice
    should be to declare test models in the sub-classes setUp method AFTER
    calling this classes setUp method.
    """

    # Override this in sub-classes to configure alternate application ids.
    APP_ID = '_'

    def setUp(self):
        """Set up test framework.

        Configures basic environment variables, stubs and creates a default
        connection.
        """
        os.environ['APPLICATION_ID'] = self.APP_ID
        self.set_up_stubs()

    def tearDown(self):
        """Tear down test framework."""
        self.datastore_stub.Clear()
        self.memcache_stub.MakeSyncCall('memcache', 'FlushAll',
                                        memcache.MemcacheFlushRequest(),
                                        memcache.MemcacheFlushResponse())
        local.__release_local__()

    def set_up_stubs(self):
        """Set up basic stubs using classes default application id.

        Set attributes on tests for each stub created.
        """
        for name, value in set_up_basic_stubs(self.APP_ID).iteritems():
            setattr(self, name + '_stub', value)

########NEW FILE########
__FILENAME__ = utils_test
# -*- coding: utf-8 -*-
"""
    Tests for tipfy utils
"""
from __future__ import with_statement

import unittest

import werkzeug

from tipfy import RequestHandler, Request, Response, Rule, Tipfy
from tipfy.app import local

from tipfy.utils import (xhtml_escape, xhtml_unescape, json_encode,
    json_decode, render_json_response, url_escape, url_unescape, utf8,
    _unicode)

import test_utils


class HomeHandler(RequestHandler):
    def get(self, **kwargs):
        return 'Hello, World!'


class ProfileHandler(RequestHandler):
    def get(self, **kwargs):
        return 'Username: %s' % kwargs.get('username')


class RedirectToHandler(RequestHandler):
    def get(self, **kwargs):
        username = kwargs.get('username', None)
        if username:
            return redirect_to('profile', username=username)
        else:
            return redirect_to('home')


class RedirectTo301Handler(RequestHandler):
    def get(self, **kwargs):
        username = kwargs.get('username', None)
        if username:
            return redirect_to('profile', username=username, _code=301)
        else:
            return redirect_to('home', _code=301)


class RedirectToInvalidCodeHandler(RequestHandler):
    def get(self, **kwargs):
        return redirect_to('home', _code=405)


def get_app():
    return Tipfy(rules=[
        Rule('/', name='home', handler=HomeHandler),
        Rule('/people/<string:username>', name='profile', handler=ProfileHandler),
        Rule('/redirect_to/', name='redirect_to', handler=RedirectToHandler),
        Rule('/redirect_to/<string:username>', name='redirect_to', handler=RedirectToHandler),
        Rule('/redirect_to_301/', name='redirect_to', handler=RedirectTo301Handler),
        Rule('/redirect_to_301/<string:username>', name='redirect_to', handler=RedirectTo301Handler),
        Rule('/redirect_to_invalid', name='redirect_to_invalid', handler=RedirectToInvalidCodeHandler),
    ])


class TestRedirect(test_utils.BaseTestCase):
    '''
    #===========================================================================
    # redirect()
    #===========================================================================
    def test_redirect(self):
        response = redirect('http://www.google.com/')

        self.assertEqual(response.headers['location'], 'http://www.google.com/')
        self.assertEqual(response.status_code, 302)

    def test_redirect_301(self):
        response = redirect('http://www.google.com/', 301)

        self.assertEqual(response.headers['location'], 'http://www.google.com/')
        self.assertEqual(response.status_code, 301)

    def test_redirect_no_response(self):
        response = redirect('http://www.google.com/')

        self.assertEqual(isinstance(response, werkzeug.BaseResponse), True)
        self.assertEqual(response.headers['location'], 'http://www.google.com/')
        self.assertEqual(response.status_code, 302)

    def test_redirect_no_response_301(self):
        response = redirect('http://www.google.com/', 301)

        self.assertEqual(isinstance(response, werkzeug.BaseResponse), True)
        self.assertEqual(response.headers['location'], 'http://www.google.com/')
        self.assertEqual(response.status_code, 301)

    def test_redirect_invalid_code(self):
        self.assertRaises(AssertionError, redirect, 'http://www.google.com/', 404)

    #===========================================================================
    # redirect_to()
    #===========================================================================
    def test_redirect_to(self):
        app = get_app()
        client = app.get_test_client()

        response = client.get('/redirect_to/', base_url='http://foo.com')
        self.assertEqual(response.headers['location'], 'http://foo.com/')
        self.assertEqual(response.status_code, 302)


    def test_redirect_to2(self):
        app = get_app()
        client = app.get_test_client()

        response = client.get('/redirect_to/calvin', base_url='http://foo.com')
        self.assertEqual(response.headers['location'], 'http://foo.com/people/calvin')
        self.assertEqual(response.status_code, 302)

        response = client.get('/redirect_to/hobbes', base_url='http://foo.com')
        self.assertEqual(response.headers['location'], 'http://foo.com/people/hobbes')
        self.assertEqual(response.status_code, 302)

        response = client.get('/redirect_to/moe', base_url='http://foo.com')
        self.assertEqual(response.headers['location'], 'http://foo.com/people/moe')
        self.assertEqual(response.status_code, 302)

    def test_redirect_to_301(self):
        app = get_app()
        client = app.get_test_client()

        response = client.get('/redirect_to_301/calvin', base_url='http://foo.com')
        self.assertEqual(response.headers['location'], 'http://foo.com/people/calvin')
        self.assertEqual(response.status_code, 301)

        response = client.get('/redirect_to_301/hobbes', base_url='http://foo.com')
        self.assertEqual(response.headers['location'], 'http://foo.com/people/hobbes')
        self.assertEqual(response.status_code, 301)

        response = client.get('/redirect_to_301/moe', base_url='http://foo.com')
        self.assertEqual(response.headers['location'], 'http://foo.com/people/moe')
        self.assertEqual(response.status_code, 301)

    def test_redirect_to_invalid_code(self):
        app = get_app()
        client = app.get_test_client()

        response = client.get('/redirect_to_invalid', base_url='http://foo.com')
        self.assertEqual(response.status_code, 500)
    '''

class TestRenderJson(test_utils.BaseTestCase):
    #===========================================================================
    # render_json_response()
    #===========================================================================
    def test_render_json_response(self):
        with Tipfy().get_test_context() as request:
            response = render_json_response({'foo': 'bar'})

            self.assertEqual(isinstance(response, Response), True)
            self.assertEqual(response.mimetype, 'application/json')
            self.assertEqual(response.data, '{"foo":"bar"}')


class TestUtils(test_utils.BaseTestCase):
    def test_xhtml_escape(self):
        self.assertEqual(xhtml_escape('"foo"'), '&quot;foo&quot;')

    def test_xhtml_unescape(self):
        self.assertEqual(xhtml_unescape('&quot;foo&quot;'), '"foo"')

    def test_json_encode(self):
        self.assertEqual(json_encode('<script>alert("hello")</script>'), '"<script>alert(\\"hello\\")<\\/script>"')

    def test_json_decode(self):
        self.assertEqual(json_decode('"<script>alert(\\"hello\\")<\\/script>"'), '<script>alert("hello")</script>')

    def test_url_escape(self):
        self.assertEqual(url_escape('somewords&some more words'), 'somewords%26some+more+words')

    def test_url_unescape(self):
        self.assertEqual(url_unescape('somewords%26some+more+words'), 'somewords&some more words')

    def test_utf8(self):
        self.assertEqual(isinstance(utf8(u'ááá'), str), True)
        self.assertEqual(isinstance(utf8('ááá'), str), True)

    def test_unicode(self):
        self.assertEqual(isinstance(_unicode(u'ááá'), unicode), True)
        self.assertEqual(isinstance(_unicode('ááá'), unicode), True)


if __name__ == '__main__':
    test_utils.main()

########NEW FILE########
__FILENAME__ = app
# -*- coding: utf-8 -*-
"""
    tipfy.app
    ~~~~~~~~~

    WSGI Application.

    :copyright: 2011 by tipfy.org.
    :license: BSD, see LICENSE.txt for more details.
"""
from __future__ import with_statement

import logging
import os
import urlparse
import wsgiref.handlers

# Werkzeug Swiss knife.
# Need to import werkzeug first otherwise py_zipimport fails.
import werkzeug
import werkzeug.exceptions
import werkzeug.urls
import werkzeug.utils
import werkzeug.wrappers

from . import default_config
from .config import Config, REQUIRED_VALUE
from .local import current_app, current_handler, get_request, local
from .routing import Router

#: Public interface.
HTTPException = werkzeug.exceptions.HTTPException
abort = werkzeug.exceptions.abort

#: TODO: remove from here.
from tipfy.appengine import (APPENGINE, APPLICATION_ID, CURRENT_VERSION_ID,
    DEV_APPSERVER)


class Request(werkzeug.wrappers.Request):
    """Provides all environment variables for the current request: GET, POST,
    FILES, cookies and headers.
    """
    #: The WSGI app.
    app = None
    #: Exception caught by the WSGI app during dispatch().
    exception = None
    #: URL adapter.
    rule_adapter = None
    #: Matched :class:`tipfy.routing.Rule`.
    rule = None
    #: Keyword arguments from the matched rule.
    rule_args = None
    #: A dictionary for request variables.
    registry = None

    def __init__(self, *args, **kwargs):
        super(Request, self).__init__(*args, **kwargs)
        self.registry = {}

    @werkzeug.utils.cached_property
    def auth(self):
        """The auth store which provides access to the authenticated user and
        auth related functions.

        :returns:
            An auth store instance.
        """
        return self.app.auth_store_class(self)

    @werkzeug.utils.cached_property
    def json(self):
        """If the mimetype is `application/json` this will contain the
        parsed JSON data.

        This function is borrowed from `Flask`_.

        :returns:
            The decoded JSON request data.
        """
        if self.mimetype == 'application/json':
            from tipfy.json import json_decode
            return json_decode(self.data)

    @werkzeug.utils.cached_property
    def i18n(self):
        """The internationalization store which provides access to several
        translation and localization utilities.

        :returns:
            An i18n store instance.
        """
        return self.app.i18n_store_class(self)

    @werkzeug.utils.cached_property
    def session(self):
        """A session dictionary using the default session configuration.

        :returns:
            A dictionary-like object with the current session data.
        """
        return self.session_store.get_session()

    @werkzeug.utils.cached_property
    def session_store(self):
        """The session store, responsible for managing sessions and flashes.

        :returns:
            A session store instance.
        """
        return self.app.session_store_class(self)

    def _get_rule_adapter(self):
        from warnings import warn
        warn(DeprecationWarning("Request.url_adapter: this attribute "
          "is deprecated. Use Request.rule_adapter instead."))
        return self.rule_adapter

    def _set_rule_adapter(self, adapter):
        from warnings import warn
        warn(DeprecationWarning("Request.url_adapter: this attribute "
          "is deprecated. Use Request.rule_adapter instead."))
        self.rule_adapter = adapter

    # Old name
    url_adapter = property(_get_rule_adapter, _set_rule_adapter)


class Response(werkzeug.wrappers.Response):
    """A response object with default mimetype set to ``text/html``."""
    default_mimetype = 'text/html'


class RequestContext(object):
    """Sets and releases the context locals used during a request.

    User meth:`App.get_test_context` to build a `RequestContext` for
    testing purposes.
    """
    def __init__(self, app, environ):
        """Initializes the request context.

        :param app:
            An :class:`App` instance.
        :param environ:
            A WSGI environment.
        """
        self.app = app
        self.environ = environ

    def __enter__(self):
        """Enters the request context.

        :returns:
            A :class:`Request` instance.
        """
        local.request = request = self.app.request_class(self.environ)
        local.app = request.app = self.app
        return request

    def __exit__(self, exc_type, exc_value, traceback):
        """Exits the request context.

        This will release the context locals except if an exception is caught
        in debug mode. In this case the locals are kept to be inspected.
        """
        if exc_type is None or not self.app.debug:
            local.__release_local__()


class App(object):
    """The WSGI application."""
    # Allowed request methods.
    allowed_methods = frozenset(['DELETE', 'GET', 'HEAD', 'OPTIONS', 'POST',
        'PUT', 'TRACE'])
    #: Default class for requests.
    request_class = Request
    #: Default class for responses.
    response_class = Response
    #: Default class for the configuration object.
    config_class = Config
    #: Default class for the configuration object.
    router_class = Router
    #: Context class used when a request comes in.
    request_context_class = RequestContext

    def __init__(self, rules=None, config=None, debug=False):
        """Initializes the application.

        :param rules:
            URL rules definitions for the application.
        :param config:
            Dictionary with configuration for the application modules.
        :param debug:
            True if this is debug mode, False otherwise.
        """
        local.current_app = self
        self.debug = debug
        self.registry = {}
        self.error_handlers = {}
        self.config = self.config_class(config, {'tipfy': default_config})
        self.router = self.router_class(self, rules)

        if debug:
            logging.getLogger().setLevel(logging.DEBUG)

    def __call__(self, environ, start_response):
        """Called when a request comes in."""
        if self.debug and self.config['tipfy']['enable_debugger']:
            return self._debugged_wsgi_app(environ, start_response)

        return self.dispatch(environ, start_response)

    def dispatch(self, environ, start_response):
        """This is the actual WSGI application.  This is not implemented in
        :meth:`__call__` so that middlewares can be applied without losing a
        reference to the class. So instead of doing this::

            app = MyMiddleware(app)

        It's a better idea to do this instead::

            app.dispatch = MyMiddleware(app.dispatch)

        Then you still have the original application object around and
        can continue to call methods on it.

        This idea comes from `Flask`_.

        :param environ:
            A WSGI environment.
        :param start_response:
            A callable accepting a status code, a list of headers and an
            optional exception context to start the response.
        """
        with self.request_context_class(self, environ) as request:
            try:
                if request.method not in self.allowed_methods:
                    abort(501)

                rv = self.router.dispatch(request)
                response = self.make_response(request, rv)
            except Exception, e:
                try:
                    rv = self.handle_exception(request, e)
                    response = self.make_response(request, rv)
                except HTTPException, e:
                    response = self.make_response(request, e)
                except Exception, e:
                    if self.debug:
                        raise

                    logging.exception(e)
                    rv = werkzeug.exceptions.InternalServerError()
                    response = self.make_response(request, rv)

            return response(environ, start_response)

    def handle_exception(self, request, exception):
        """Handles an exception. To set app-wide error handlers, define them
        using the corresponent HTTP status code in the ``error_handlers``
        dictionary of :class:`App`. For example, to set a custom
        `Not Found` page::

            class Handle404(RequestHandler):
                def __call__(self):
                    logging.exception(self.request.exception)
                    return Response('Oops! I could swear this page was here!',
                        status=404)

            app = App([
                Rule('/', handler=MyHandler, name='home'),
            ])
            app.error_handlers[404] = Handle404

        When an ``HTTPException`` is raised using :func:`abort` or because the
        app could not fulfill the request, the error handler defined for the
        exception HTTP status code will be called. If it is not set, the
        exception is reraised.

        .. note::
           The exception is stored in the request object and accessible
           through `request.exception`.

           The error handler is responsible for setting the response
           status code and logging the exception, as shown in the example
           above.

        :param request:
            A :attr:`request_class` instance.
        :param exception:
            The raised exception.
        """
        if isinstance(exception, HTTPException):
            code = exception.code
        else:
            code = 500

        handler = self.error_handlers.get(code)
        if not handler:
            raise

        request.exception = exception
        rv = handler(request)
        if not isinstance(rv, werkzeug.wrappers.BaseResponse):
            if hasattr(rv, '__call__'):
                # If it is a callable but not a response, we call it again.
                rv = rv()

        return rv

    def make_response(self, request, *rv):
        """Converts the returned value from a :class:`RequestHandler` to a
        response object that is an instance of :attr:`response_class`.

        This function is borrowed from `Flask`_.

        :param rv:
            - If no arguments are passed, returns an empty response.
            - If a single argument is passed, the returned value varies
              according to its type:

              - :attr:`response_class`: the response is returned unchanged.
              - :class:`str`: a response is created with the string as body.
              - :class:`unicode`: a response is created with the string
                encoded to utf-8 as body.
              - a WSGI function: the function is called as WSGI application
                and buffered as response object.
              - None: a ValueError exception is raised.

            - If multiple arguments are passed, a response is created using
              the arguments.

        :returns:
            A :attr:`response_class` instance.
        """
        if not rv:
            return self.response_class()

        if len(rv) == 1:
            rv = rv[0]

            if isinstance(rv, self.response_class):
                return rv

            if isinstance(rv, basestring):
                return self.response_class(rv)

            if rv is None:
                raise ValueError('RequestHandler did not return a response.')

            return self.response_class.force_type(rv, request.environ)

        return self.response_class(*rv)

    def get_config(self, module, key=None, default=REQUIRED_VALUE):
        """Returns a configuration value for a module.

        .. seealso:: :meth:`Config.get_config`.
        """
        from warnings import warn
        warn(DeprecationWarning("App.get_config(): this method "
            "is deprecated. Use App.config['module']['key'] instead."))
        return self.config.get_config(module, key=key, default=default)

    def get_test_client(self):
        """Creates a test client for this application.

        :returns:
            A ``werkzeug.Client`` with the WSGI application wrapped for tests.
        """
        from werkzeug.test import Client
        return Client(self, self.response_class, use_cookies=True)

    def get_test_context(self, *args, **kwargs):
        """Creates a test client for this application.

        :param args:
            Positional arguments to construct a `werkzeug.test.EnvironBuilder`.
        :param kwargs:
            Keyword arguments to construct a `werkzeug.test.EnvironBuilder`.
        :returns:
            A :class:``RequestContext`` instance.
        """
        from werkzeug.test import EnvironBuilder
        builder = EnvironBuilder(*args, **kwargs)
        try:
            return self.request_context_class(self, builder.get_environ())
        finally:
            builder.close()

    def get_test_handler(self, *args, **kwargs):
        """Returns a handler set as a current handler for testing purposes.

        .. seealso:: :class:`tipfy.testing.CurrentHandlerContext`.

        :returns:
            A :class:`tipfy.testing.CurrentHandlerContext` instance.
        """
        from tipfy.testing import CurrentHandlerContext
        return CurrentHandlerContext(self, *args, **kwargs)

    def run(self):
        """Runs the app using ``CGIHandler``. This must be called inside a
        ``main()`` function in the file defined in *app.yaml* to run the
        application::

            # ...

            app = App(rules=[
                Rule('/', name='home', handler=HelloWorldHandler),
            ])

            def main():
                app.run()

            if __name__ == '__main__':
                main()

        """
        wsgiref.handlers.CGIHandler().run(self)

    @werkzeug.utils.cached_property
    def _debugged_wsgi_app(self):
        """Returns the WSGI app wrapped by an interactive debugger."""
        from tipfy.debugger import DebuggedApplication
        return DebuggedApplication(self.dispatch, evalex=True)

    @werkzeug.utils.cached_property
    def auth_store_class(self):
        """Returns the configured auth store class.

        :returns:
            An auth store class.
        """
        cls = self.config['tipfy']['auth_store_class']
        return werkzeug.utils.import_string(cls)

    @werkzeug.utils.cached_property
    def i18n_store_class(self):
        """Returns the configured i18n store class.

        :returns:
            An i18n store class.
        """
        cls = self.config['tipfy']['i18n_store_class']
        return werkzeug.utils.import_string(cls)

    @werkzeug.utils.cached_property
    def session_store_class(self):
        """Returns the configured session store class.

        :returns:
            A session store class.
        """
        cls = self.config['tipfy']['session_store_class']
        return werkzeug.utils.import_string(cls)

    # Old names
    wsgi_app = dispatch


def redirect(location, code=302, response_class=Response, body=None):
    """Returns a response object that redirects to the given location.

    Supported codes are 301, 302, 303, 305, and 307. 300 is not supported
    because it's not a real redirect and 304 because it's the answer for a
    request with a request with defined If-Modified-Since headers.

    :param location:
        A relative or absolute URI (e.g., '/contact'). If relative, it
        will be merged to the current request URL to form an absolute URL.
    :param code:
        The HTTP status code for the redirect. Default is 302.
    :param response_class:
        The class used to build the response. Default is :class:`Response`.
    :body:
        The response body. If not set uses a body with a standard message.
    :returns:
        A :class:`Response` object with headers set for redirection.
    """
    assert code in (301, 302, 303, 305, 307), 'invalid code'

    if location.startswith(('.', '/')):
        # Make it absolute.
        location = urlparse.urljoin(get_request().url, location)

    display_location = location
    if isinstance(location, unicode):
        location = werkzeug.urls.iri_to_uri(location)

    if body is None:
        body = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n' \
            '<title>Redirecting...</title>\n<h1>Redirecting...</h1>\n' \
            '<p>You should be redirected automatically to target URL: ' \
            '<a href="%s">%s</a>. If not click the link.' % \
            (location, display_location)

    response = response_class(body, code, mimetype='text/html')
    response.headers['Location'] = location
    return response


# Old names.
Tipfy = App

########NEW FILE########
__FILENAME__ = acl
# -*- coding: utf-8 -*-
"""
	tipfy.appengine.acl
	~~~~~~~~~~~~~~~~~~~

	Simple Access Control List

	This module provides utilities to manage permissions for anything that
	requires some level of restriction, such as datastore models or handlers.

	Access permissions can be grouped into roles for convenience, so that a new
	user can be assigned to a role directly instead of having all
	permissions defined manually. Individual access permissions can then
	override or extend the role permissions.

	.. note::

	   Roles are optional, so this module doesn't define a roles model (to keep
	   things simple and fast). Role definitions are set directly in the Acl
	   class. The strategy to load roles is open to the implementation; for
	   best performance, define them statically in a module.

	Usage example::

		# Set a dict of roles with an 'admin' role that has full access and
		# assign users to it. Each role maps to a list of rules. Each rule is a
		# tuple (topic, name, flag), where flag is as bool to allow or disallow
		# access. Wildcard '*' can be used to match all topics and/or names.
		Acl.roles_map = {
			'admin': [
				('*', '*', True),
			],
		}

		# Assign users 'user_1' and 'user_2' to the 'admin' role.
		AclRules.insert_or_update(area='my_area', user='user_1',
			roles=['admin'])
		AclRules.insert_or_update(area='my_area', user='user_2',
			roles=['admin'])

		# Restrict 'user_2' from accessing a specific resource, adding a new
		# rule with flag set to False. Now this user has access to everything
		# except this resource.
		user_acl = AclRules.get_by_area_and_user('my_area', 'user_2')
		user_acl.rules.append(('UserAdmin', '*', False))
		user_acl.put()

		# Check that 'user_2' permissions are correct.
		acl = Acl(area='my_area', user='user_2')
		assert acl.has_access(topic='UserAdmin', name='save') is False
		assert acl.has_access(topic='AnythingElse', name='put') is True

	The Acl object should be created once after a user is loaded, so that
	it becomes available for the app to do all necessary permissions checkings.

	Based on concept from `Solar <http://solarphp.com>`_ Access and Role
	classes.

	:copyright: 2011 by tipfy.org.
	:license: BSD, see LICENSE.txt for more details.
"""
from google.appengine.ext import db
from google.appengine.api import memcache

from werkzeug import cached_property

from tipfy.appengine import CURRENT_VERSION_ID
from tipfy.appengine.db import PickleProperty
from tipfy.local import get_request

#: Cache for loaded rules.
_rules_map = {}


class AclMixin(object):
	"""A mixin that adds an acl property to a ``tipfy.RequestHandler``.

	The handler *must* have the properties area and current_user set for
	it to work.
	"""
	roles_map = None
	roles_lock = None

	@cached_property
	def acl(self):
		"""Loads and returns the access permission for the currently logged in
		user. This requires the handler to have the area and
		current_user attributes. Casted to a string they must return the
		object identifiers.
		"""
		return Acl(str(self.area.key()), str(self.current_user.key()),
			self.roles_map, self.roles_lock)


def validate_rules(rules):
	"""Ensures that the list of rule tuples is set correctly."""
	assert isinstance(rules, list), 'Rules must be a list'

	for rule in rules:
		assert isinstance(rule, tuple), 'Each rule must be tuple'
		assert len(rule) == 3, 'Each rule must have three elements'
		assert isinstance(rule[0], basestring), 'Rule topic must be a string'
		assert isinstance(rule[1], basestring), 'Rule name must be a string'
		assert isinstance(rule[2], bool), 'Rule flag must be a bool'


class AclRules(db.Model):
	"""Stores roles and rules for a user in a given area."""
	#: Creation date.
	created = db.DateTimeProperty(auto_now_add=True)
	#: Modification date.
	updated = db.DateTimeProperty(auto_now=True)
	#: Area to which this role is related.
	area = db.StringProperty(required=True)
	#: User identifier.
	user = db.StringProperty(required=True)
	#: List of role names.
	roles = db.StringListProperty()
	#: Lists of rules. Each rule is a tuple (topic, name, flag).
	rules = PickleProperty(validator=validate_rules)

	@classmethod
	def get_key_name(cls, area, user):
		"""Returns this entity's key name, also used as memcache key.

		:param area:
			Area string identifier.
		:param user:
			User string identifier.
		:returns:
			The key name.
		"""
		return '%s:%s' % (str(area), str(user))

	@classmethod
	def get_by_area_and_user(cls, area, user):
		"""Returns an AclRules entity for a given user in a given area.

		:param area:
			Area string identifier.
		:param user:
			User string identifier.
		:returns:
			An AclRules entity.
		"""
		return cls.get_by_key_name(cls.get_key_name(area, user))

	@classmethod
	def insert_or_update(cls, area, user, roles=None, rules=None):
		"""Inserts or updates ACL rules and roles for a given user. This will
		reset roles and rules if the user exists and the values are not passed.

		:param area:
			Area string identifier.
		:param user:
			User string identifier.
		:param roles:
			List of the roles for the user.
		:param rules:
			List of the rules for the user.
		:returns:
			An AclRules entity.
		"""
		if roles is None:
			roles = []

		if rules is None:
			rules = []

		user_acl = cls(key_name=cls.get_key_name(area, user), area=area,
			user=user, roles=roles, rules=rules)
		user_acl.put()
		return user_acl

	@classmethod
	def get_roles_and_rules(cls, area, user, roles_map, roles_lock):
		"""Returns a tuple (roles, rules) for a given user in a given area.

		:param area:
			Area string identifier.
		:param user:
			User string identifier.
		:param roles_map:
			Dictionary of available role names mapping to list of rules.
		:param roles_lock:
			Lock for the roles map: a unique identifier to track changes.
		:returns:
			A tuple of (roles, rules) for the given user in the given area.
		"""
		res = None
		cache_key = cls.get_key_name(area, user)
		if cache_key in _rules_map:
			res = _rules_map[cache_key]
		else:
			res = memcache.get(cache_key, namespace=cls.__name__)

		if res is not None:
			lock, roles, rules = res

		if res is None or lock != roles_lock or get_request().app.debug:
			entity = cls.get_by_key_name(cache_key)
			if entity is None:
				res = (roles_lock, [], [])
			else:
				rules = []
				# Apply role rules.
				for role in entity.roles:
					rules.extend(roles_map.get(role, []))

				# Extend with rules, eventually overriding some role rules.
				rules.extend(entity.rules)

				# Reverse everything, as rules are checked from last to first.
				rules.reverse()

				# Set results for cache, applying current roles_lock.
				res = (roles_lock, entity.roles, rules)

			cls.set_cache(cache_key, res)

		return (res[1], res[2])

	@classmethod
	def set_cache(cls, cache_key, spec):
		"""Sets a memcache value.

		:param cache_key:
			The Cache key.
		:param spec:
			Value to be saved.
		"""
		_rules_map[cache_key] = spec
		memcache.set(cache_key, spec, namespace=cls.__name__)

	@classmethod
	def delete_cache(cls, cache_key):
		"""Deletes a memcache value.

		:param cache_key:
			The Cache key.
		"""
		if cache_key in _rules_map:
			del _rules_map[cache_key]

		memcache.delete(cache_key, namespace=cls.__name__)

	def put(self):
		"""Saves the entity and clears the cache."""
		self.delete_cache(self.get_key_name(self.area, self.user))
		super(AclRules, self).put()

	def delete(self):
		"""Deletes the entity and clears the cache."""
		self.delete_cache(self.get_key_name(self.area, self.user))
		super(AclRules, self).delete()

	def is_rule_set(self, topic, name, flag):
		"""Checks if a given rule is set.

		:param topic:
			A rule topic, as a string.
		:param roles:
			A rule name, as a string.
		:param flag:
			A rule flag, a boolean.
		:returns:
			True if the rule already exists, False otherwise.
		"""
		for rule_topic, rule_name, rule_flag in self.rules:
			if rule_topic == topic and rule_name == name and rule_flag == flag:
				return True

		return False


class Acl(object):
	"""Loads access rules and roles for a given user in a given area and
	provides a centralized interface to check permissions. Each Acl object
	checks the permissions for a single user. For example::

		from tipfy.appengine.acl import Acl

		# Build an Acl object for user 'John' in the 'code-reviews' area.
		acl = Acl('code-reviews', 'John')

		# Check if 'John' is 'admin' in the 'code-reviews' area.
		is_admin = acl.is_one('admin')

		# Check if 'John' can approve new reviews.
		can_edit = acl.has_access('EditReview', 'approve')
	"""
	#: Dictionary of available role names mapping to list of rules.
	roles_map = {}

	#: Lock for role changes. This is needed because if role definitions change
	#: we must invalidate existing cache that applied the previous definitions.
	roles_lock = None

	def __init__(self, area, user, roles_map=None, roles_lock=None):
		"""Loads access privileges and roles for a given user in a given area.

		:param area:
			An area identifier, as a string.
		:param user:
			A user identifier, as a string.
		:param roles_map:
			A dictionary of roles mapping to a list of rule tuples.
		:param roles_lock:
			Roles lock string to validate cache. If not set, uses
			the application version id.
		"""
		if roles_map is not None:
			self.roles_map = roles_map

		if roles_lock is not None:
			self.roles_lock = roles_lock
		elif self.roles_lock is None:
			# Set roles_lock default.
			self.roles_lock = CURRENT_VERSION_ID

		if area and user:
			self._roles, self._rules = AclRules.get_roles_and_rules(area, user,
				self.roles_map, self.roles_lock)
		else:
			self.reset()

	def reset(self):
		"""Resets the currently loaded access rules and user roles."""
		self._rules = []
		self._roles = []

	def is_one(self, role):
		"""Check to see if a user is in a role group.

		:param role:
			A role name, as a string.
		:returns:
			True if the user is in this role group, False otherwise.
		"""
		return role in self._roles

	def is_any(self, roles):
		"""Check to see if a user is in any of the listed role groups.

		:param roles:
			An iterable of role names.
		:returns:
			True if the user is in any of the role groups, False otherwise.
		"""
		for role in roles:
			if role in self._roles:
				return True

		return False

	def is_all(self, roles):
		"""Check to see if a user is in all of the listed role groups.

		:param roles:
			An iterable of role names.
		:returns:
			True if the user is in all of the role groups, False otherwise.
		"""
		for role in roles:
			if role not in self._roles:
				return False

		return True

	def has_any_access(self):
		"""Checks if the user has any access or roles.

		:returns:
			True if the user has any access rule or role set, False otherwise.
		"""
		if self._rules or self._roles:
			return True

		return False

	def has_access(self, topic, name):
		"""Checks if the user has access to a topic/name combination.

		:param topic:
			A rule topic, as a string.
		:param roles:
			A rule name, as a string.
		:returns:
			True if the user has access to this rule, False otherwise.
		"""
		if topic == '*' or name == '*':
			raise ValueError("has_access() can't be called passing '*'")

		for rule_topic, rule_name, rule_flag in self._rules:
			if (rule_topic == topic or rule_topic == '*') and \
				(rule_name == name or rule_name == '*'):
				# Topic and name matched, so return the flag.
				return rule_flag

		# No match.
		return False

########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-
"""
    tipfy.appengine.auth.model
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Base model for authenticated users.

    :copyright: 2011 by tipfy.org.
    :license: BSD, see LICENSE.txt for more details.
"""
from __future__ import absolute_import

import datetime

from google.appengine.ext import db

from werkzeug import check_password_hash, generate_password_hash

from tipfy.auth import create_session_id


class User(db.Model):
    """Universal user model. Can be used with App Engine's default users API,
    own auth or third party authentication methods (OpenId, OAuth etc).
    """
    #: Creation date.
    created = db.DateTimeProperty(auto_now_add=True)
    #: Modification date.
    updated = db.DateTimeProperty(auto_now=True)
    #: User defined unique name, also used as key_name.
    username = db.StringProperty(required=True)
    #: Password, only set for own authentication.
    password = db.StringProperty(required=False)
    #: User email
    email = db.EmailProperty()
    # Admin flag.
    is_admin = db.BooleanProperty(required=True, default=False)
    #: Authentication identifier according to the auth method in use. Examples:
    #: * own|username
    #: * gae|user_id
    #: * openid|identifier
    #: * twitter|username
    #: * facebook|username
    auth_id = db.StringProperty(required=True)
    # Flag to persist the auth accross sessions for thirdy party auth.
    auth_remember = db.BooleanProperty(default=False)
    # Auth token, renewed periodically for improved security.
    session_id = db.StringProperty(required=True)
    # Auth token last renewal date.
    session_updated = db.DateTimeProperty(auto_now_add=True)

    @classmethod
    def get_by_username(cls, username):
        return cls.get_by_key_name(username)

    @classmethod
    def get_by_auth_id(cls, auth_id):
        return cls.all().filter('auth_id =', auth_id).get()

    @classmethod
    def create(cls, username, auth_id, **kwargs):
        """Creates a new user and returns it. If the username already exists,
        returns None.

        :param username:
            Unique username.
        :param auth_id:
            Authentication id, according the the authentication method used.
        :param kwargs:
            Additional entity attributes.
        :returns:
            The newly created user or None if the username already exists.
        """
        kwargs['username'] = username
        kwargs['key_name'] = username
        kwargs['auth_id'] = auth_id
        # Generate an initial session id.
        kwargs['session_id'] = create_session_id()

        if 'password_hash' in kwargs:
            # Password is already hashed.
            kwargs['password'] = kwargs.pop('password_hash')
        elif 'password' in kwargs:
            # Password is not hashed: generate a hash.
            kwargs['password'] = generate_password_hash(kwargs['password'])

        def txn():
            if cls.get_by_username(username) is not None:
                # Username already exists.
                return None

            user = cls(**kwargs)
            user.put()
            return user

        return db.run_in_transaction(txn)

    def set_password(self, new_password):
        """Sets a new, plain password.

        :param new_password:
            A plain, not yet hashed password.
        :returns:
            None.
        """
        self.password = generate_password_hash(new_password)

    def check_password(self, password):
        """Checks if a password is valid. This is done with form login

        :param password:
            Password to be checked.
        :returns:
            True is the password is valid, False otherwise.
        """
        if check_password_hash(self.password, password):
            return True

        return False

    def check_session(self, session_id):
        """Checks if an auth token is valid.

        :param session_id:
            Token to be checked.
        :returns:
            True is the token id is valid, False otherwise.
        """
        if self.session_id == session_id:
            return True

        return False

    def renew_session(self, force=False, max_age=None):
        """Renews the session id if its expiration time has passed.

        :param force:
            True to force the session id to be renewed, False to check
            if the expiration time has passed.
        :returns:
            None.
        """
        if not force:
            # Only renew the session id if it is too old.
            expires = datetime.timedelta(seconds=max_age)
            force = (self.session_updated + expires < datetime.datetime.now())

        if force:
            self.session_id = create_session_id()
            self.session_updated = datetime.datetime.now()
            self.put()

    def __unicode__(self):
        """Returns this entity's username.

        :returns:
            Username, as unicode.
        """
        return unicode(self.username)

    def __str__(self):
        """Returns this entity's username.

        :returns:
            Username, as unicode.
        """
        return self.__unicode__()

    def __eq__(self, obj):
        """Compares this user entity with another one.

        :returns:
            True if both entities have same key, False otherwise.
        """
        if not obj:
            return False

        return str(self.key()) == str(obj.key())

    def __ne__(self, obj):
        """Compares this user entity with another one.

        :returns:
            True if both entities don't have same key, False otherwise.
        """
        return not self.__eq__(obj)

########NEW FILE########
__FILENAME__ = blobstore
# -*- coding: utf-8 -*-
"""
    tipfy.appengine.blobstore
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Handler library for Blobstore API.

    Contains handler mixins to help with uploading and downloading blobs.

    BlobstoreDownloadMixin: Has helper method for easily sending blobs
    to client.

    BlobstoreUploadMixin: mixin for receiving upload notification requests.

    Based on the original App Engine library and the adaptation to Werkzeug
    from Kay framework.

    :copyright: 2007 Google Inc.
    :copyright: 2009 Accense Technology, Inc. All rights reserved.
    :copyright: 2011 tipfy.org.
    :license: Apache 2.0 License, see LICENSE.txt for more details.
"""
import cgi
import cStringIO
import datetime
import email
import logging
import re
import sys
import time

from google.appengine.ext import blobstore
from google.appengine.api import blobstore as api_blobstore

from webob import byterange

from werkzeug import FileStorage, Response

_BASE_CREATION_HEADER_FORMAT = '%Y-%m-%d %H:%M:%S'
_CONTENT_DISPOSITION_FORMAT = 'attachment; filename="%s"'

_SEND_BLOB_PARAMETERS = frozenset(['use_range'])

_RANGE_NUMERIC_FORMAT = r'([0-9]*)-([0-9]*)'
_RANGE_FORMAT = r'([a-zA-Z]+)=%s' % _RANGE_NUMERIC_FORMAT
_RANGE_FORMAT_REGEX = re.compile('^%s$' % _RANGE_FORMAT)
_UNSUPPORTED_RANGE_FORMAT_REGEX = re.compile(
    '^%s(?:,%s)+$' % (_RANGE_FORMAT, _RANGE_NUMERIC_FORMAT))
_BYTES_UNIT = 'bytes'


class CreationFormatError(api_blobstore.Error):
  """Raised when attempting to parse bad creation date format."""


class Error(Exception):
  """Base class for all errors in blobstore handlers module."""


class RangeFormatError(Error):
  """Raised when Range header incorrectly formatted."""


class UnsupportedRangeFormatError(RangeFormatError):
  """Raised when Range format is correct, but not supported."""


def _check_ranges(start, end, use_range_set, use_range, range_header):
    """Set the range header.

    Args:
        start: As passed in from send_blob.
        end: As passed in from send_blob.
        use_range_set: Use range was explcilty set during call to send_blob.
        use_range: As passed in from send blob.
        range_header: Range header as received in HTTP request.

    Returns:
        Range header appropriate for placing in blobstore.BLOB_RANGE_HEADER.

    Raises:
        ValueError if parameters are incorrect.  This happens:
          - start > end.
          - start < 0 and end is also provided.
          - end < 0
          - If index provided AND using the HTTP header, they don't match.
            This is a safeguard.
    """
    if end is not None and start is None:
        raise ValueError('May not specify end value without start.')

    use_indexes = start is not None
    if use_indexes:
        if end is not None:
            if start > end:
                raise ValueError('start must be < end.')

        range_indexes = byterange.Range.serialize_bytes(_BYTES_UNIT, [(start,
            end)])

    if use_range_set and use_range and use_indexes:
        if range_header != range_indexes:
            raise ValueError('May not provide non-equivalent range indexes '
                       'and range headers: (header) %s != (indexes) %s'
                       % (range_header, range_indexes))

    if use_range and range_header is not None:
        return range_header
    elif use_indexes:
        return range_indexes
    else:
        return None


class BlobstoreDownloadMixin(object):
    """Mixin for handlers that may send blobs to users."""
    __use_range_unset = object()

    def send_blob(self, blob_key_or_info, content_type=None, save_as=None,
        start=None, end=None, **kwargs):
        """Sends a blob-response based on a blob_key.

        Sets the correct response header for serving a blob.  If BlobInfo
        is provided and no content_type specified, will set request content type
        to BlobInfo's content type.

        :param blob_key_or_info:
            BlobKey or BlobInfo record to serve.
        :param content_type:
            Content-type to override when known.
        :param save_as:
            If True, and BlobInfo record is provided, use BlobInfos filename
            to save-as. If string is provided, use string as filename. If
            None or False, do not send as attachment.
        :returns:
            A :class:`tipfy.app.Response` object.
        :raises:
            ``ValueError`` on invalid save_as parameter.
        """
        # Response headers.
        headers = {}

        if set(kwargs) - _SEND_BLOB_PARAMETERS:
            invalid_keywords = []
            for keyword in kwargs:
                if keyword not in _SEND_BLOB_PARAMETERS:
                    invalid_keywords.append(keyword)

            if len(invalid_keywords) == 1:
                raise TypeError('send_blob got unexpected keyword argument '
                    '%s.' % invalid_keywords[0])
            else:
                raise TypeError('send_blob got unexpected keyword arguments: '
                    '%s.' % sorted(invalid_keywords))

        use_range = kwargs.get('use_range', self.__use_range_unset)
        use_range_set = use_range is not self.__use_range_unset

        if use_range:
            self.get_range()

        range_header = _check_ranges(start,
                                     end,
                                     use_range_set,
                                     use_range,
                                     self.request.headers.get('range', None))

        if range_header is not None:
            headers[blobstore.BLOB_RANGE_HEADER] = range_header

        if isinstance(blob_key_or_info, blobstore.BlobInfo):
            blob_key = blob_key_or_info.key()
            blob_info = blob_key_or_info
        else:
            blob_key = blob_key_or_info
            blob_info = None

        headers[blobstore.BLOB_KEY_HEADER] = str(blob_key)

        if content_type:
            if isinstance(content_type, unicode):
                content_type = content_type.encode('utf-8')

            headers['Content-Type'] = content_type
        else:
            headers['Content-Type'] = ''

        def send_attachment(filename):
            if isinstance(filename, unicode):
                filename = filename.encode('utf-8')

            headers['Content-Disposition'] = (
                _CONTENT_DISPOSITION_FORMAT % filename)

        if save_as:
            if isinstance(save_as, basestring):
                send_attachment(save_as)
            elif blob_info and save_as is True:
                send_attachment(blob_info.filename)
            else:
                if not blob_info:
                    raise ValueError('Expected BlobInfo value for '
                        'blob_key_or_info.')
                else:
                    raise ValueError('Unexpected value for save_as')

        return Response('', headers=headers)

    def get_range(self):
        """Get range from header if it exists.

        Returns:
          Tuple (start, end):
            start: Start index.  None if there is None.
            end: End index.  None if there is None.
          None if there is no request header.

        Raises:
          UnsupportedRangeFormatError: If the range format in the header is
            valid, but not supported.
          RangeFormatError: If the range format in the header is not valid.
        """
        range_header = self.request.headers.get('range', None)
        if range_header is None:
            return None

        try:
            original_stdout = sys.stdout
            sys.stdout = cStringIO.StringIO()
            try:
                parsed_range = byterange.Range.parse_bytes(range_header)
            finally:
                sys.stdout = original_stdout
        except TypeError, err:
            raise RangeFormatError('Invalid range header: %s' % err)

        if parsed_range is None:
            raise RangeFormatError('Invalid range header: %s' % range_header)

        units, ranges = parsed_range
        if len(ranges) != 1:
            raise UnsupportedRangeFormatError(
                'Unable to support multiple range values in Range header.')

        if units != _BYTES_UNIT:
            raise UnsupportedRangeFormatError(
                'Invalid unit in range header type: %s', range_header)

        return ranges[0]


class BlobstoreUploadMixin(object):
    """Mixin for blob upload handlers."""
    def get_uploads(self, field_name=None):
        """Returns uploads sent to this handler.

        :param field_name:
            Only select uploads that were sent as a specific field.
        :returns:
            A list of BlobInfo records corresponding to each upload. Empty list
            if there are no blob-info records for field_name.
        """
        if getattr(self, '_BlobstoreUploadMixin__uploads', None) is None:
            self.__uploads = {}
            for key, value in self.request.files.items():
                if isinstance(value, FileStorage):
                    for option in value.headers['Content-Type'].split(';'):
                        if 'blob-key' in option:
                            self.__uploads.setdefault(key, []).append(
                                parse_blob_info(value, key))

        if field_name:
            try:
                return list(self.__uploads[field_name])
            except KeyError:
                return []
        else:
            results = []
            for uploads in self.__uploads.itervalues():
                results += uploads

        return results


def parse_blob_info(file_storage, field_name=None):
    """Parse a BlobInfo record from file upload field_storage.

    :param file_storage:
        ``werkzeug.FileStorage`` that represents uploaded blob.
    :returns:
        BlobInfo record as parsed from the field-storage instance.
        None if there was no field_storage.
    :raises:
        BlobInfoParseError when provided field_storage does not contain enough
        information to construct a BlobInfo object.
    """
    if file_storage is None:
        return None

    field_name = field_name or file_storage.name

    def get_value(dict, name):
        value = dict.get(name, None)
        if value is None:
            raise blobstore.BlobInfoParseError('Field %s has no %s.' %
                (field_name, name))

        return value

    filename = file_storage.filename
    content_type, cdict = cgi.parse_header(file_storage.headers['Content-Type'])
    blob_key = blobstore.BlobKey(get_value(cdict, 'blob-key'))

    upload_content = email.message_from_file(file_storage.stream)
    content_type = get_value(upload_content, 'content-type')
    size = get_value(upload_content, 'content-length')
    creation_string = get_value(upload_content,
        blobstore.UPLOAD_INFO_CREATION_HEADER)

    try:
        size = int(size)
    except (TypeError, ValueError):
        raise blobstore.BlobInfoParseError(
            '%s is not a valid value for %s size.' % (size, field_name))

    try:
        creation = parse_creation(creation_string, field_name)
    except CreationFormatError, e:
        raise blobstore.BlobInfoParseError(
            'Could not parse creation for %s: %s' % (field_name, str(e)))

    return blobstore.BlobInfo(blob_key, {
        'content_type': content_type,
        'creation': creation,
        'filename': filename,
        'size': size,
    })


def parse_creation(creation_string, field_name):
    """Parses upload creation string from header format.

    Parse creation date of the format:

      YYYY-mm-dd HH:MM:SS.ffffff

      Y: Year
      m: Month (01-12)
      d: Day (01-31)
      H: Hour (00-24)
      M: Minute (00-59)
      S: Second (00-59)
      f: Microsecond

    Args:
      creation_string: String creation date format.

    Returns:
      datetime object parsed from creation_string.

    Raises:
      _CreationFormatError when the creation string is formatted incorrectly.
    """
    split_creation_string = creation_string.split('.', 1)
    if len(split_creation_string) != 2:
        raise CreationFormatError(
            'Could not parse creation %s in field %s.' % (creation_string,
                                                            field_name))
    timestamp_string, microsecond = split_creation_string

    try:
        timestamp = time.strptime(timestamp_string,
                                  _BASE_CREATION_HEADER_FORMAT)
        microsecond = int(microsecond)
    except ValueError:
        raise CreationFormatError('Could not parse creation %s in field %s.'
                                  % (creation_string, field_name))

    return datetime.datetime(*timestamp[:6] + tuple([microsecond]))

########NEW FILE########
__FILENAME__ = properties
# -*- coding: utf-8 -*-
"""
    tipfy.appengine.db.properties
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Extra db.Model property classes.

    :copyright: 2011 by tipfy.org.
    :license: BSD, see LICENSE.txt for more details.
"""
import hashlib
import pickle
import decimal

from google.appengine.ext import db

from tipfy.utils import json_decode, json_encode, slugify

try:
    # This is optional, only required by TimezoneProperty.
    from pytz.gae import pytz
except ImportError, e:
    pass


class EtagProperty(db.Property):
    """Automatically creates an ETag based on the value of another property.

    Note: the ETag is only set or updated after the entity is saved.
    Example::

        from google.appengine.ext import db
        from tipfy.appengine.db import EtagProperty

        class StaticContent(db.Model):
            data = db.BlobProperty()
            etag = EtagProperty(data)

    This class derives from `aetycoon <http://github.com/Arachnid/aetycoon>`_.
    """
    def __init__(self, prop, *args, **kwargs):
        self.prop = prop
        super(EtagProperty, self).__init__(*args, **kwargs)

    def get_value_for_datastore(self, model_instance):
        v = self.prop.__get__(model_instance, type(model_instance))
        if not v:
            return None

        if isinstance(v, unicode):
            v = v.encode('utf-8')

        return hashlib.sha1(v).hexdigest()


class KeyProperty(db.Property):
    """A property that stores a key, without automatically dereferencing it.

    Example usage:

    >>> class SampleModel(db.Model):
    ...   sample_key = KeyProperty()

    >>> model = SampleModel()
    >>> model.sample_key = db.Key.from_path("Foo", "bar")
    >>> model.put() # doctest: +ELLIPSIS
    datastore_types.Key.from_path(u'SampleModel', ...)

    >>> model.sample_key # doctest: +ELLIPSIS
    datastore_types.Key.from_path(u'Foo', u'bar', ...)

    Adapted from aetycoon: http://github.com/Arachnid/aetycoon/
    Added possibility to set it using a db.Model instance.
    """
    def validate(self, value):
        """Validate the value.

        Args:
          value: The value to validate.
        Returns:
          A valid key.
        """
        if isinstance(value, basestring):
            value = db.Key(value)
        elif isinstance(value, db.Model):
            if not value.has_key():
                raise db.BadValueError('%s instance must have a complete key to '
                    'be stored.' % value.__class__.kind())

            value = value.key()

        if value is not None:
            if not isinstance(value, db.Key):
                raise TypeError('Property %s must be an instance of db.Key'
                    % self.name)

        return super(KeyProperty, self).validate(value)


class JsonProperty(db.Property):
    """Stores a value automatically encoding to JSON on set and decoding
    on get.
    """
    data_type = db.Text

    def get_value_for_datastore(self, model_instance):
        """Encodes the value to JSON."""
        value = super(JsonProperty, self).get_value_for_datastore(
            model_instance)
        if value is not None:
            return db.Text(json_encode(value, separators=(',', ':')))

    def make_value_from_datastore(self, value):
        """Decodes the value from JSON."""
        if value is not None:
            return json_decode(value)

    def validate(self, value):
        if value is not None and not isinstance(value, (dict, list, tuple)):
            raise db.BadValueError('Property %s must be a dict, list or '
                'tuple.' % self.name)

        return value


class PickleProperty(db.Property):
    """A property for storing complex objects in the datastore in pickled form.
    Example::

        >>> class PickleModel(db.Model):
        ... data = PickleProperty()
        >>> model = PickleModel()
        >>> model.data = {"foo": "bar"}
        >>> model.data
        {'foo': 'bar'}
        >>> model.put() # doctest: +ELLIPSIS
        datastore_types.Key.from_path(u'PickleModel', ...)
        >>> model2 = PickleModel.all().get()
        >>> model2.data
        {'foo': 'bar'}

    This class derives from `aetycoon <http://github.com/Arachnid/aetycoon>`_.
    """
    data_type = db.Blob

    def get_value_for_datastore(self, model_instance):
        value = self.__get__(model_instance, model_instance.__class__)
        value = self.validate(value)

        if value is not None:
            return db.Blob(pickle.dumps(value, pickle.HIGHEST_PROTOCOL))

    def make_value_from_datastore(self, value):
        if value is not None:
            return pickle.loads(str(value))


class SlugProperty(db.Property):
    """Automatically creates a slug (a lowercase string with words separated by
    dashes) based on the value of another property.

    Note: the slug is only set or updated after the entity is saved. Example::

        from google.appengine.ext import db
        from tipfy.appengine.db import SlugProperty

        class BlogPost(db.Model):
            title = db.StringProperty()
            slug = SlugProperty(title)

    This class derives from `aetycoon <http://github.com/Arachnid/aetycoon>`_.
    """
    def __init__(self, prop, max_length=None, *args, **kwargs):
        self.prop = prop
        self.max_length = max_length
        super(SlugProperty, self).__init__(*args, **kwargs)

    def get_value_for_datastore(self, model_instance):
        v = self.prop.__get__(model_instance, type(model_instance))
        if not v:
            return self.default

        return slugify(v, max_length=self.max_length, default=self.default)


class TimezoneProperty(db.Property):
    """Stores a timezone value."""
    data_type = str

    def get_value_for_datastore(self, model_instance):
        value = super(TimezoneProperty, self).get_value_for_datastore(
            model_instance)
        value = self.validate(value)
        return value.zone

    def make_value_from_datastore(self, value):
        return pytz.timezone(value)

    def validate(self, value):
        value = super(TimezoneProperty, self).validate(value)
        if value is None or hasattr(value, 'zone'):
            return value
        elif isinstance(value, basestring):
            return pytz.timezone(value)

        raise db.BadValueError("Property %s must be a pytz timezone or string."
            % self.name)


class DecimalProperty(db.Property):
    """Stores a decimal value."""
    data_type = decimal.Decimal

    def get_value_for_datastore(self, model_instance):
        return str(super(DecimalProperty, self).get_value_for_datastore(
            model_instance))

    def make_value_from_datastore(self, value):
        return decimal.Decimal(value)

    def validate(self, value):
        value = super(DecimalProperty, self).validate(value)

        if value is None or isinstance(value, decimal.Decimal):
            return value
        elif isinstance(value, basestring):
            return decimal.Decimal(value)
        raise db.BadValueError("Property %s must be a Decimal or string"
            % self.name)

########NEW FILE########
__FILENAME__ = mail
# -*- coding: utf-8 -*-
"""
    tipfy.appengine.mail
    ~~~~~~~~~~~~~~~~~~~~

    A simple RequestHandler to help with receiving mail.

    Ported from the original App Engine library:
    http://code.google.com/appengine/docs/python/mail/receivingmail.html

    :copyright: 2011 by tipfy.org.
    :license: Apache Software License, see LICENSE.txt for more details.
"""
from google.appengine.api import mail

from tipfy import RequestHandler


class InboundMailHandler(RequestHandler):
    """Base class for inbound mail handlers. Example::

        # Sub-class overrides receive method.
        class HelloReceiver(InboundMailHandler):

            def receive(self, mail_message):
                logging.info('Received greeting from %s: %s' % (
                    mail_message.sender, mail_message.body))
    """
    def post(self, **kwargs):
        """Transforms body to email request.

        :param kwargs:
            Keyword arguments from the matched URL rule.
        """
        return self.receive(mail.InboundEmailMessage(self.request.data),
            **kwargs)

    def receive(self, mail_message, **kwargs):
        """Receive an email message.

        Override this method to implement an email receiver.

        :param mail_message:
            InboundEmailMessage instance representing received email.
        :param kwargs:
            Keyword arguments from the matched URL rule.
        """
        raise NotImplementedError()

########NEW FILE########
__FILENAME__ = matcher
# -*- coding: utf-8 -*-
"""
    tipfy.appengine.matcher
    ~~~~~~~~~~~~~~~~~~~~~~~

    A RequestHandler for the `google.appengine.api.matcher`API.

    :copyright: 2011 by tipfy.org.
    :license: Apache Software License, see LICENSE.txt for more details.
"""
from google.appengine.api import matcher

from tipfy import RequestHandler


class MatcherHandler(RequestHandler):
    """A simple test to feed the matcher::

        class Index(RequestHandler):
            def get(self):
                schema = {str:['symbol'], float:['price']}
                matcher.subscribe(dict, 'symbol:GOOG AND price > 500', 'ikai:GOOG',
                    schema=schema, topic='Stock')
                matcher.match({'symbol': 'GOOG', 'price': 515.0}, topic='Stock')
                return "Queued"

    """
    def post(self, **kwargs):
        """Parses all the fields out of a match and pass along."""
        form = self.request.form
        result = self.match(
            sub_ids=form.getlist('id'),
            key=form.get('key'),
            topic=form['topic'],
            results_count=int(form['results_count']),
            results_offset=int(form['results_offset']),
            doc=matcher.get_document(form),
            **kwargs
        )
        return result

    def match(self, sub_ids, topic, results_count, results_offset, key, doc):
        """Receives a match document.

        Override this method to implement a match handler.

        :param sub_ids:
            A list of subscription ID's (strings) which matched the document.
        :param topic:
            The topic or model name, e.g. "StockOptions"
        :param results_count:
            The total number of subscription ids matched across all batches.
        :param results_offset:
            The offset of the current batch into the results_count.
        :param key:
            The result_key provided by the user in the Match call.
        :param doc:
            The matched document itself. May be an Entity, db.Model
            instance, or dict.
        """
        raise NotImplementedError()

########NEW FILE########
__FILENAME__ = sessions
# -*- coding: utf-8 -*-
"""
    tipfy.appengine.sessions
    ~~~~~~~~~~~~~~~~~~~~~~~~

    App Engine session backends.

    :copyright: 2011 by tipfy.org.
    :license: BSD, see LICENSE.txt for more details.
"""
import re
import uuid

from google.appengine.api import memcache
from google.appengine.ext import db

from tipfy.sessions import BaseSession

from tipfy.appengine.db import (PickleProperty, get_protobuf_from_entity,
    get_entity_from_protobuf)

# Validate session keys.
_UUID_RE = re.compile(r'^[a-f0-9]{32}$')


class SessionModel(db.Model):
    """Stores session data."""
    kind_name = 'Session'

    #: Creation date.
    created = db.DateTimeProperty(auto_now_add=True)
    #: Modification date.
    updated = db.DateTimeProperty(auto_now=True)
    #: Session data, pickled.
    data = PickleProperty()

    @property
    def sid(self):
        """Returns the session id, which is the same as the key name.

        :returns:
            A session unique id.
        """
        return self.key().name()

    @classmethod
    def kind(cls):
        """Returns the datastore kind we use for this model."""
        return cls.kind_name

    @classmethod
    def get_by_sid(cls, sid):
        """Returns a ``Session`` instance by session id.

        :param sid:
            A session id.
        :returns:
            An existing ``Session`` entity.
        """
        session = cls.get_cache(sid)
        if not session:
            session = SessionModel.get_by_key_name(sid)
            if session:
                session.set_cache()

        return session

    @classmethod
    def create(cls, sid, data=None):
        """Returns a new, empty session entity.

        :param sid:
            A session id.
        :returns:
            A new and not saved session entity.
        """
        return cls(key_name=sid, data=data or {})

    @classmethod
    def get_cache(cls, sid):
        data = memcache.get(sid)
        if data:
            return get_entity_from_protobuf(data)

    def set_cache(self):
        """Saves a new cache for this entity."""
        memcache.set(self.sid, get_protobuf_from_entity(self))

    def delete_cache(self):
        """Saves a new cache for this entity."""
        memcache.delete(self.sid)

    def put(self):
        """Saves the session and updates the memcache entry."""
        self.set_cache()
        db.put(self)

    def delete(self):
        """Deletes the session and the memcache entry."""
        self.delete_cache()
        db.delete(self)


class AppEngineBaseSession(BaseSession):
    __slots__ = BaseSession.__slots__ + ('sid',)

    def __init__(self, data=None, sid=None, new=False):
        BaseSession.__init__(self, data, new)
        if new:
            self.sid = self.__class__._get_new_sid()
        elif sid is None:
            raise ValueError('A session id is required for existing sessions.')
        else:
            self.sid = sid

    @classmethod
    def _get_new_sid(cls):
        # Force a namespace in the key, to not pollute the namespace in case
        # global namespaces are in use.
        return cls.__module__ + '.' + cls.__name__ + '.' + uuid.uuid4().hex

    @classmethod
    def get_session(cls, store, name=None, **kwargs):
        if name:
            cookie = store.get_secure_cookie(name)
            if cookie is not None:
                sid = cookie.get('_sid')
                if sid and _is_valid_key(sid):
                    return cls._get_by_sid(sid, **kwargs)

        return cls(new=True)


class DatastoreSession(AppEngineBaseSession):
    """A session that stores data serialized in the datastore."""
    model_class = SessionModel

    @classmethod
    def _get_by_sid(cls, sid, **kwargs):
        """Returns a session given a session id."""
        entity = cls.model_class.get_by_sid(sid)
        if entity is not None:
            return cls(entity.data, sid)

        return cls(new=True)

    def save_session(self, response, store, name, **kwargs):
        if not self.modified:
            return

        self.model_class.create(self.sid, dict(self)).put()
        store.set_secure_cookie(response, name, {'_sid': self.sid}, **kwargs)


class MemcacheSession(AppEngineBaseSession):
    """A session that stores data serialized in memcache."""
    @classmethod
    def _get_by_sid(cls, sid, **kwargs):
        """Returns a session given a session id."""
        data = memcache.get(sid)
        if data is not None:
            return cls(data, sid)

        return cls(new=True)

    def save_session(self, response, store, name, **kwargs):
        if not self.modified:
            return

        memcache.set(self.sid, dict(self))
        store.set_secure_cookie(response, name, {'_sid': self.sid}, **kwargs)


def _is_valid_key(key):
    """Check if a session key has the correct format."""
    return _UUID_RE.match(key.split('.')[-1]) is not None

########NEW FILE########
__FILENAME__ = sharded_counter
# -*- coding: utf-8 -*-
"""
	tipfy.appengine.sharded_counter
	~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

	A general purpose sharded counter implementation for the datastore.

	:copyright: 2011 by tipfy.org.
	:license: Apache Software License, see LICENSE.txt for more details.
"""
import string
import random
import logging

from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.runtime import apiproxy_errors

from tipfy.local import get_request

#: Default configuration values for this module. Keys are:
#:
#: shards
#:     The amount of shards to use.
default_config = {
	'shards': 10,
}


class MemcachedCount(object):
	# Allows negative numbers in unsigned memcache
	DELTA_ZERO = 500000

	@property
	def namespace(self):
		return __name__ + '.' + self.__class__.__name__

	def __init__(self, name):
		self.key = 'MemcachedCount' + name

	def get_count(self):
		value = memcache.get(self.key, namespace=self.namespace)
		if value is None:
			return 0
		else:
			return string.atoi(value) - MemcachedCount.DELTA_ZERO

	def set_count(self, value):
		memcache.set(self.key, str(MemcachedCount.DELTA_ZERO + value),
			namespace=self.namespace)

	def delete_count(self):
		memcache.delete(self.key)

	count = property(get_count, set_count, delete_count)

	def increment(self, incr=1):
		value = memcache.get(self.key, namespace=self.namespace)
		if value is None:
			self.count = incr
		elif incr > 0:
			memcache.incr(self.key, incr, namespace=self.namespace)
		elif incr < 0:
			memcache.decr(self.key, -incr, namespace=self.namespace)


class Counter(object):
	"""A counter using sharded writes to prevent contentions.

	Should be used for counters that handle a lot of concurrent use.
	Follows the pattern described in the Google I/O talk:
	http://sites.google.com/site/io/building-scalable-web-applications-with-google-app-engine

	Memcache is used for caching counts and if a cached count is available,
	it is the most correct. If there are datastore put issues, we store the
	un-put values into a delayed_incr memcache that will be applied as soon
	as the next shard put is successful. Changes will only be lost if we lose
	memcache before a successful datastore shard put or there's a
	failure/error in memcache.

	Example::

		# Build a new counter that uses the unique key name 'hits'.
		hits = Counter('hits')
		# Increment by 1.
		hits.increment()
		# Increment by 10.
		hits.increment(10)
		# Decrement by 3.
		hits.increment(-3)
		# This is the current count.
		my_hits = hits.count
		# Forces fetching a non-cached count of all shards.
		hits.get_count(nocache=True)
		# Set the counter to an arbitrary value.
		hits.count = 6
	"""
	#: Number of shards to use.
	shards = None

	def __init__(self, name):
		self.name = name
		self.memcached = MemcachedCount('counter:' + name)
		self.delayed_incr = MemcachedCount('delayed:' + name)

	@property
	def number_of_shards(self):
		return self.shards or get_request().app.config[__name__]['shards']

	def delete(self):
		q = db.Query(CounterShard).filter('name =', self.name)
		shards = q.fetch(limit=self.number_of_shards)
		db.delete(shards)

	def get_count_and_cache(self):
		q = db.Query(CounterShard).filter('name =', self.name)
		shards = q.fetch(limit=self.number_of_shards)
		datastore_count = 0
		for shard in shards:
			datastore_count += shard.count

		count = datastore_count + self.delayed_incr.count
		self.memcached.count = count
		return count

	def get_count(self, nocache=False):
		total = self.memcached.count
		if nocache or total is None:
			return self.get_count_and_cache()
		else:
			return int(total)

	def set_count(self, value):
		cur_value = self.get_count()
		self.memcached.count = value
		delta = value - cur_value
		if delta != 0:
			CounterShard.increment(self, incr=delta)

	count = property(get_count, set_count)

	def increment(self, incr=1, refresh=False):
		CounterShard.increment(self, incr)
		self.memcached.increment(incr)


class CounterShard(db.Model):
	name = db.StringProperty(required=True)
	count = db.IntegerProperty(default=0)

	@classmethod
	def increment(cls, counter, incr=1):
		index = random.randint(1, counter.number_of_shards)
		counter_name = counter.name
		delayed_incr = counter.delayed_incr.count
		shard_key_name = 'Shard' + counter_name + str(index)
		def get_or_create_shard():
			shard = CounterShard.get_by_key_name(shard_key_name)
			if shard is None:
				shard = CounterShard(key_name=shard_key_name, name=counter_name)
			shard.count += incr + delayed_incr
			key = shard.put()

		try:
			db.run_in_transaction(get_or_create_shard)
		except (db.Error, apiproxy_errors.Error), e:
			counter.delayed_incr.increment(incr)
			logging.error('CounterShard (%s) delayed increment %d: %s',
						  counter_name, incr, e)
			return False

		if delayed_incr:
			counter.delayed_incr.count = 0

		return True
########NEW FILE########
__FILENAME__ = taskqueue
# -*- coding: utf-8 -*-
"""
    tipfy.appengine.taskqueue
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Task queue utilities extension.

    :copyright: 2011 by tipfy.org.
    :license: BSD, see LICENSE.txt for more details.
"""
import logging
from google.appengine.ext import db

from google.appengine.ext.deferred import defer, run, PermanentTaskFailure
from google.appengine.runtime import DeadlineExceededError

from tipfy import RequestHandler


class DeferredHandler(RequestHandler):
    """A handler class that processes deferred tasks invocations, mirrored
    from ``google.appengine.ext.deferred``. Map to this handler if you want
    to use the deferred package running on the same WSGI application as other
    handlers. Tipfy utilities will then be available to be used in the
    deferred function.

    The setup for *app.yaml* is:

    .. code-block:: yaml

       - url: /_ah/queue/deferred
         script: main.py
         login: admin

    The URL rule for urls.py is::

        Rule('/_ah/queue/deferred', name='tasks/deferred',
             handler='tipfy.appengine.taskqueue.DeferredHandler')
    """
    def post(self):
        headers = ['%s:%s' % (k, v) for k, v in self.request.headers.items()
               if k.lower().startswith('x-appengine-')]
        logging.info(', '.join(headers))

        try:
            run(self.request.data)
        except PermanentTaskFailure, e:
            logging.exception('Permanent failure attempting to execute task')

        return ''


class Mapper(object):
    """A base class to process all entities in single datastore kind, using
    the task queue. On each request, a batch of entities is processed and a new
    task is added to process the next batch.

    For example, to delete all ``MyModel`` records::

        from tipfy.appengine.taskqueue import Mapper
        from mymodels import myModel

        class MyModelMapper(Mapper):
            model = MyModel

            def map(self, entity):
                # Add the entity to the list of entities to be deleted.
                return ([], [entity])

        mapper = MyModelMapper()
        deferred.defer(mapper.run)

    The setup for app.yaml is:

    .. code-block:: yaml

       - url: /_ah/queue/deferred
         script: main.py
         login: admin

    The URL rule for urls.py is::

        Rule('/_ah/queue/deferred', name='tasks/deferred',
            handler='tipfy.appengine.taskqueue.DeferredHandler')

    This class derives from `deffered article <http://code.google.com/appengine/articles/deferred.html>`_.
    """
    # Subclasses should replace this with a model class (eg, model.Person).
    model = None

    # Subclasses can replace this with a list of (property, value) tuples
    # to filter by.
    filters = []

    def __init__(self):
        self.to_put = []
        self.to_delete = []

    def map(self, entity):
        """Updates a single entity.

        Implementers should return a tuple containing two iterables
        (to_update, to_delete).
        """
        return ([], [])

    def finish(self):
        """Called when the mapper has finished, to allow for any final work to
        be done.
        """
        pass

    def get_query(self):
        """Returns a query over the specified kind, with any appropriate
        filters applied.
        """
        q = self.model.all()
        for prop, value in self.filters:
            q.filter('%s =' % prop, value)

        q.order('__key__')
        return q

    def run(self, batch_size=20):
        """Starts the mapper running."""
        self._continue(None, batch_size)

    def _batch_write(self):
        """Writes updates and deletes entities in a batch."""
        if self.to_put:
            db.put(self.to_put)
            self.to_put = []

        if self.to_delete:
            db.delete(self.to_delete)
            self.to_delete = []

    def _continue(self, start_key, batch_size):
        """Processes a batch of entities."""
        q = self.get_query()
        # If we're resuming, pick up where we left off last time.
        if start_key:
            q.filter('__key__ >', start_key)

        # Keep updating records until we run out of time.
        try:
            # Steps over the results, returning each entity and its index.
            for i, entity in enumerate(q):
                map_updates, map_deletes = self.map(entity)
                self.to_put.extend(map_updates)
                self.to_delete.extend(map_deletes)

                # Record the last entity we processed.
                start_key = entity.key()

                # Do updates and deletes in batches.
                if (i + 1) % batch_size == 0:
                    self._batch_write()

        except DeadlineExceededError:
            # Write any unfinished updates to the datastore.
            self._batch_write()
            # Queue a new task to pick up where we left off.
            defer(self._continue, start_key, batch_size)
            return

        # Write any updates to the datastore, since it may not have happened
        # otherwise
        self._batch_write()

        self.finish()

########NEW FILE########
__FILENAME__ = xmpp
# -*- coding: utf-8 -*-
"""
    tipfy.appengine.xmpp
    ~~~~~~~~~~~~~~~~~~~~

    XMPP webapp handler classes.

    This module provides handler classes for XMPP bots, including both basic
    messaging functionality and a command handler for commands such as:
    "/foo bar".

    Ported from the original
    `App Engine library <http://code.google.com/appengine/docs/python/xmpp/>`_.
"""
import logging

from google.appengine.api import xmpp

from tipfy import RequestHandler


class BaseHandler(RequestHandler):
    """A webapp baseclass for XMPP handlers.

    Implements a straightforward message delivery pattern. When a message is
    received, :meth:`message_received` is called with a ``Message`` object that
    encapsulates the relevant details. Users can reply using the standard XMPP
    API, or the convenient ``reply()`` method on the ``Message`` object.
    """
    def message_received(self, message):
        """Called when a message is sent to the XMPP bot.

        :param message:
            The message that was sent by the user.
        """
        raise NotImplementedError()

    def post(self, **kwargs):
        try:
            self.xmpp_message = xmpp.Message(self.request.form)
        except xmpp.InvalidMessageError, e:
            logging.error('Invalid XMPP request: Missing required field %s',
                e[0])
            return self.app.response_class('')

        return self.message_received(self.xmpp_message)


class CommandHandlerMixin(object):
    """A command handler for XMPP bots.

    Implements a command handler pattern. XMPP messages are processed by
    calling message_received. ``Message`` objects handled by this class are
    annotated with *command* and *arg* fields.

    On receipt of a message starting with a forward or backward slash, the
    handler calls a method named after the command - e.g., if the user sends
    ``/foo bar``, the handler will call ``foo_command(message)``.

    If no handler method matches, :meth:`unhandled_command` is called. The
    default behaviour of :meth:`unhandled_command` is to send the message
    "Unknown command" back to the sender.

    If the user sends a message not prefixed with a slash,
    ``text_message(message)`` is called.
    """
    def unhandled_command(self, message):
        """Called when an unknown command is sent to the XMPP bot.

        :param message:
            The message that was sent by the user.
        """
        message.reply('Unknown command')

    def text_message(self, message):
        """Called when a message not prefixed by a `/command` is sent to the
        XMPP bot.

        :param message:
            The message that was sent by the user.
        """
        pass

    def message_received(self, message):
        """Called when a message is sent to the XMPP bot.

        :param message:
            The message that was sent by the user.
        """
        if message.command:
            handler_name = '%s_command' % (message.command,)
            handler = getattr(self, handler_name, None)
            if handler:
                handler(message)
            else:
                self.unhandled_command(message)
        else:
            self.text_message(message)

        return self.app.response_class('')


class CommandHandler(CommandHandlerMixin, BaseHandler):
    """A implementation of :class:`CommandHandlerMixin`."""
    pass

########NEW FILE########
__FILENAME__ = facebook
# -*- coding: utf-8 -*-
"""
    tipfy.auth.facebook
    ~~~~~~~~~~~~~~~~~~~

    Implementation of Facebook authentication scheme.

    Ported from `tornado.auth`_.

    :copyright: 2009 Facebook.
    :copyright: 2011 tipfy.org.
    :license: Apache License Version 2.0, see LICENSE.txt for more details.
"""
from __future__ import absolute_import
import functools
import hashlib
import logging
import time
import urlparse
import urllib

from google.appengine.api import urlfetch

from tipfy import REQUIRED_VALUE
from tipfy.utils import json_decode, json_encode

#: Default configuration values for this module. Keys are:
#:
#: - ``api_key``: Key provided when you register an application with
#:   Facebook.
#: - ``app_secret``: Secret provided when you register an application
#:   with Facebook.
default_config = {
    'api_key':    REQUIRED_VALUE,
    'app_secret': REQUIRED_VALUE,
}


class FacebookMixin(object):
    """A :class:`tipfy.RequestHandler` mixin that implements Facebook Connect
    authentication.

    To authenticate with Facebook, register your application with
    Facebook at http://www.facebook.com/developers/apps.php. Then
    copy your API Key and Application Secret to config.py::

        config['tipfy.auth.twitter'] = {
            'api_key':    'XXXXXXXXXXXXXXX',
            'app_secret': 'XXXXXXXXXXXXXXX',
        }

    When your application is set up, you can use the FacebookMixin like this
    to authenticate the user with Facebook::

        from tipfy import RequestHandler
        from tipfy.auth.facebook import FacebookMixin

        class FacebookHandler(RequestHandler, FacebookMixin):
            def get(self):
                if self.request.args.get('session', None):
                    return self.get_authenticated_user(self._on_auth)

                return self.authenticate_redirect()

            def _on_auth(self, user):
                if not user:
                    self.abort(403)

                # Set the user in the session.

    The user object returned by get_authenticated_user() includes the
    attributes 'facebook_uid' and 'name' in addition to session attributes
    like 'session_key'. You should save the session key with the user; it is
    required to make requests on behalf of the user later with
    facebook_request().
    """
    @property
    def _facebook_api_key(self):
        return self.app.config[__name__]['api_key']

    @property
    def _facebook_secret(self):
        return self.app.config[__name__]['app_secret']

    def authenticate_redirect(self, callback_uri=None, cancel_uri=None,
                              extended_permissions=None):
        """Authenticates/installs this app for the current user."""
        callback_uri = callback_uri or self.request.path
        args = {
            'api_key':        self._facebook_api_key,
            'v':              '1.0',
            'fbconnect':      'true',
            'display':        'page',
            'next':           urlparse.urljoin(self.request.url, callback_uri),
            'return_session': 'true',
        }
        if cancel_uri:
            args['cancel_url'] = urlparse.urljoin(self.request.url, cancel_uri)

        if extended_permissions:
            if isinstance(extended_permissions, basestring):
                extended_permissions = [extended_permissions]

            args['req_perms'] = ','.join(extended_permissions)

        return self.redirect('http://www.facebook.com/login.php?' +
                        urllib.urlencode(args))

    def authorize_redirect(self, extended_permissions, callback_uri=None,
                           cancel_uri=None):
        """Redirects to an authorization request for the given FB resource.

        The available resource names are listed at
        http://wiki.developers.facebook.com/index.php/Extended_permission.
        The most common resource types include:

            publish_stream
            read_stream
            email
            sms

        extended_permissions can be a single permission name or a list of
        names. To get the session secret and session key, call
        get_authenticated_user() just as you would with
        authenticate_redirect().
        """
        return self.authenticate_redirect(callback_uri, cancel_uri,
                                          extended_permissions)

    def get_authenticated_user(self, callback):
        """Fetches the authenticated Facebook user.

        The authenticated user includes the special Facebook attributes
        'session_key' and 'facebook_uid' in addition to the standard
        user attributes like 'name'.
        """
        session = json_decode(self.request.args.get('session'))
        return self.facebook_request(
            method='facebook.users.getInfo',
            callback=functools.partial(
                self._on_get_user_info, callback, session),
            session_key=session['session_key'],
            uids=session['uid'],
            fields='uid,first_name,last_name,name,locale,pic_square,' \
                   'profile_url,username')

    def facebook_request(self, method, callback=None, **kwargs):
        """Makes a Facebook API REST request.

        We automatically include the Facebook API key and signature, but
        it is the callers responsibility to include 'session_key' and any
        other required arguments to the method.

        The available Facebook methods are documented here:
        http://wiki.developers.facebook.com/index.php/API

        Here is an example for the stream.get() method::

            from tipfy import RequestHandler
            from tipfy.auth.facebook import FacebookMixin
            from tipfyext.jinja2 import Jinja2Mixin

            class MainHandler(RequestHandler, Jinja2Mixin, FacebookMixin):
                def get(self):
                    self.facebook_request(
                        method='stream.get',
                        callback=self._on_stream,
                        session_key=self.current_user['session_key'])

                def _on_stream(self, stream):
                    if stream is None:
                       # Not authorized to read the stream yet?
                       return self.redirect(self.authorize_redirect('read_stream'))

                    return self.render_response('stream.html', stream=stream)
        """
        if not method.startswith('facebook.'):
            method = 'facebook.' + method

        kwargs.update({
            'api_key': self._facebook_api_key,
            'v':       '1.0',
            'method':  method,
            'call_id': str(long(time.time() * 1e6)),
            'format':  'json',
        })

        kwargs['sig'] = self._signature(kwargs)
        url = 'http://api.facebook.com/restserver.php?' + \
            urllib.urlencode(kwargs)

        try:
            response = urlfetch.fetch(url, deadline=10)
        except urlfetch.DownloadError, e:
            logging.exception(e)
            response = None

        if not callback:
            # Don't preprocess the response, just return a bare one.
            return response

        return self._parse_response(callback, response)

    def _on_get_user_info(self, callback, session, users):
        if users is None:
            return callback(None)

        user = users[0]
        return callback({
            'name':            user['name'],
            'first_name':      user['first_name'],
            'last_name':       user['last_name'],
            'uid':             user['uid'],
            'locale':          user['locale'],
            'pic_square':      user['pic_square'],
            'profile_url':     user['profile_url'],
            'username':        user.get('username'),
            'session_key':     session['session_key'],
            'session_expires': session.get('expires'),
        })

    def _parse_response(self, callback, response):
        if not response:
            logging.warning('Missing Facebook response.')
            return callback(None)
        elif response.status_code < 200 or response.status_code >= 300:
            logging.warning('HTTP error from Facebook (%d): %s',
                response.status_code, response.content)
            return callback(None)

        try:
            json = json_decode(response.content)
        except:
            logging.warning('Invalid JSON from Facebook: %r', response.content)
            return callback(None)

        if isinstance(json, dict) and json.get('error_code'):
            logging.warning('Facebook error: %d: %r', json['error_code'],
                            json.get('error_msg'))
            return callback(None)

        return callback(json)

    def _signature(self, kwargs):
        parts = ['%s=%s' % (n, kwargs[n]) for n in sorted(kwargs.keys())]
        body = ''.join(parts) + self._facebook_secret
        if isinstance(body, unicode):
            body = body.encode('utf-8')

        return hashlib.md5(body).hexdigest()

########NEW FILE########
__FILENAME__ = friendfeed
# -*- coding: utf-8 -*-
"""
    tipfy.auth.friendfeed
    ~~~~~~~~~~~~~~~~~~~~~

    Implementation of FriendFeed authentication scheme.

    Ported from `tornado.auth`_.

    :copyright: 2009 Facebook.
    :copyright: 2011 tipfy.org.
    :license: Apache License Version 2.0, see LICENSE.txt for more details.
"""
from __future__ import absolute_import
import functools
import logging
import urllib

from google.appengine.api import urlfetch

from tipfy import REQUIRED_VALUE
from tipfy.utils import json_decode, json_encode
from tipfy.auth.oauth import OAuthMixin

#: Default configuration values for this module. Keys are:
#:
#: consumer_key
#:     Key provided when you register an application with FriendFeed.
#:
#: consumer_secret
#:     Secret provided when you register an application with FriendFeed.
default_config = {
    'consumer_key':    REQUIRED_VALUE,
    'consumer_secret': REQUIRED_VALUE,
}


class FriendFeedMixin(OAuthMixin):
    """A :class:`tipfy.RequestHandler` mixin that implements FriendFeed OAuth
    authentication.

    To authenticate with FriendFeed, register your application with
    FriendFeed at http://friendfeed.com/api/applications. Then
    copy your Consumer Key and Consumer Secret to config.py::

        config['tipfy.auth.friendfeed'] = {
            'consumer_key':    'XXXXXXXXXXXXXXX',
            'consumer_secret': 'XXXXXXXXXXXXXXX',
        }

    When your application is set up, you can use the FriendFeedMixin to
    authenticate the user with FriendFeed and get access to their stream.
    You must use the mixin on the handler for the URL you registered as your
    application's Callback URL. For example::

        from tipfy import RequestHandler
        from tipfy.auth.friendfeed import FriendFeedMixin
        from tipfy.sessions SessionMiddleware

        class FriendFeedHandler(RequestHandler, FriendFeedMixin):
            middleware = [SessionMiddleware()]

            def get(self):
                if self.request.args.get('oauth_token', None):
                    return self.get_authenticated_user(self._on_auth)

                return self.authorize_redirect()

            def _on_auth(self, user):
                if not user:
                    self.abort(403)

                # Set the user in the session.
                # ...

    The user object returned by get_authenticated_user() includes the
    attributes 'username', 'name', and 'description' in addition to
    'access_token'. You should save the access token with the user;
    it is required to make requests on behalf of the user later with
    friendfeed_request().
    """
    _OAUTH_REQUEST_TOKEN_URL = 'https://friendfeed.com/account/oauth/request_token'
    _OAUTH_ACCESS_TOKEN_URL = 'https://friendfeed.com/account/oauth/access_token'
    _OAUTH_AUTHORIZE_URL = 'https://friendfeed.com/account/oauth/authorize'
    _OAUTH_NO_CALLBACKS = True
    _OAUTH_VERSION = '1.0'

    @property
    def _friendfeed_consumer_key(self):
        return self.app.config[__name__]['consumer_key']

    @property
    def _friendfeed_consumer_secret(self):
        return self.app.config[__name__]['consumer_secret']

    def _oauth_consumer_token(self):
        return dict(
            key=self._friendfeed_consumer_key,
            secret=self._friendfeed_consumer_secret)

    def friendfeed_request(self, path, callback=None, access_token=None,
                           post_args=None, **args):
        """Fetches the given relative API path, e.g., '/bret/friends'

        If the request is a POST, post_args should be provided. Query
        string arguments should be given as keyword arguments.

        All the FriendFeed methods are documented at
        http://friendfeed.com/api/documentation.

        Many methods require an OAuth access token which you can obtain
        through authorize_redirect() and get_authenticated_user(). The
        user returned through that process includes an 'access_token'
        attribute that can be used to make authenticated requests via
        this method. Example usage::

            from tipfy import RequestHandler, Response
            from tipfy.auth.friendfeed import FriendFeedMixin
            from tipfy.sessions import SessionMiddleware

            class MainHandler(RequestHandler, FriendFeedMixin):
                middleware = [SessionMiddleware()]

                def get(self):
                    return self.friendfeed_request('/entry',
                        post_args={'body': 'Testing Tornado Web Server'},
                        access_token=self.current_user['access_token'],
                        callback=self._on_post)

                def _on_post(self, new_entry):
                    if not new_entry:
                        # Call failed; perhaps missing permission?
                        return self.authorize_redirect()

                    return Response('Posted a message!')
        """
        # Add the OAuth resource request signature if we have credentials
        url = 'http://friendfeed-api.com/v2' + path
        if access_token:
            all_args = {}
            all_args.update(args)
            all_args.update(post_args or {})
            consumer_token = self._oauth_consumer_token()
            method = 'POST' if post_args is not None else 'GET'
            oauth = self._oauth_request_parameters(
                url, access_token, all_args, method=method)
            args.update(oauth)

        if args:
            url += '?' + urllib.urlencode(args)

        try:
            if post_args is not None:
                response = urlfetch.fetch(url, method='POST',
                    payload=urllib.urlencode(post_args), deadline=10)
            else:
                response = urlfetch.fetch(url, deadline=10)
        except urlfetch.DownloadError, e:
            logging.exception(e)
            response = None

        if not callback:
            # Don't preprocess the response, just return a bare one.
            return response

        return self._on_friendfeed_request(callback, response)

    def _on_friendfeed_request(self, callback, response):
        if not response:
            logging.warning('Could not get a FriendFeed response.')
            return callback(None)
        elif response.status_code < 200 or response.status_code >= 300:
            logging.warning('Invalid FriendFeed response (%d): %s',
                response.status_code, response.content)
            return callback(None)

        return callback(json_decode(response.content))

    def _oauth_get_user(self, access_token, callback):
        callback = functools.partial(self._parse_user_response, callback)
        return self.friendfeed_request(
            '/feedinfo/' + access_token['username'],
            include='id,name,description', access_token=access_token,
            callback=callback)

    def _parse_user_response(self, callback, user):
        if user:
            user['username'] = user['id']

        return callback(user)

########NEW FILE########
__FILENAME__ = google
# -*- coding: utf-8 -*-
"""
    tipfy.auth.google
    ~~~~~~~~~~~~~~~~~

    Implementation of Google authentication scheme.

    Ported from `tornado.auth`_.

    :copyright: 2009 Facebook.
    :copyright: 2011 tipfy.org.
    :license: Apache License Version 2.0, see LICENSE.txt for more details.
"""
from __future__ import absolute_import
import logging
import urllib

from google.appengine.api import urlfetch

from tipfy import REQUIRED_VALUE
from tipfy.auth.oauth import OAuthMixin
from tipfy.auth.openid import OpenIdMixin

#: Default configuration values for this module. Keys are:
#:
#: google_consumer_key
#:
#:
#: google_consumer_secret
#:
default_config = {
    'google_consumer_key':    REQUIRED_VALUE,
    'google_consumer_secret': REQUIRED_VALUE,
}


class GoogleMixin(OpenIdMixin, OAuthMixin):
    """A :class:`tipfy.RequestHandler` mixin that implements Google OpenId /
    OAuth authentication.

    No application registration is necessary to use Google for authentication
    or to access Google resources on behalf of a user. To authenticate with
    Google, redirect with authenticate_redirect(). On return, parse the
    response with get_authenticated_user(). We send a dict containing the
    values for the user, including 'email', 'name', and 'locale'.
    Example usage::

        from tipfy import RequestHandler
        from tipfy.auth.google import GoogleMixin

        class GoogleHandler(RequestHandler, GoogleMixin):
            def get(self):
                if self.request.args.get('openid.mode', None):
                    return self.get_authenticated_user(self._on_auth)

                return self.authenticate_redirect()

            def _on_auth(self, user):
                if not user:
                    self.abort(403)

                # Set the user in the session.
    """
    _OPENID_ENDPOINT = 'https://www.google.com/accounts/o8/ud'
    _OAUTH_ACCESS_TOKEN_URL = 'https://www.google.com/accounts/OAuthGetAccessToken'

    @property
    def _google_consumer_key(self):
        return self.app.config[__name__]['google_consumer_key']

    @property
    def _google_consumer_secret(self):
        return self.app.config[__name__]['google_consumer_secret']

    def _oauth_consumer_token(self):
        return dict(
            key=self._google_consumer_key,
            secret=self._google_consumer_secret)

    def authorize_redirect(self, oauth_scope, callback_uri=None,
        ax_attrs=None):
        """Authenticates and authorizes for the given Google resource.

        Some of the available resources are:

           Gmail Contacts - http://www.google.com/m8/feeds/
           Calendar - http://www.google.com/calendar/feeds/
           Finance - http://finance.google.com/finance/feeds/

        You can authorize multiple resources by separating the resource
        URLs with a space.
        """
        callback_uri = callback_uri or self.request.path
        ax_attrs = ax_attrs or ['name', 'email', 'language', 'username']
        args = self._openid_args(callback_uri, ax_attrs=ax_attrs,
                                 oauth_scope=oauth_scope)
        return self.redirect(self._OPENID_ENDPOINT + '?' + urllib.urlencode(args))

    def get_authenticated_user(self, callback):
        """Fetches the authenticated user data upon redirect."""
        # Look to see if we are doing combined OpenID/OAuth
        oauth_ns = ''
        for name, values in self.request.args.iterlists():
            if name.startswith('openid.ns.') and \
                values[-1] == u'http://specs.openid.net/extensions/oauth/1.0':
                oauth_ns = name[10:]
                break

        token = self.request.args.get('openid.' + oauth_ns + '.request_token',
            '')
        if token:
            try:
                token = dict(key=token, secret='')
                url = self._oauth_access_token_url(token)
                response = urlfetch.fetch(url, deadline=10)
            except urlfetch.DownloadError, e:
                logging.exception(e)
                response = None

            return self._on_access_token(callback, response)
        else:
            return OpenIdMixin.get_authenticated_user(self, callback)

    def _oauth_get_user(self, access_token, callback):
        return OpenIdMixin.get_authenticated_user(self, callback)

########NEW FILE########
__FILENAME__ = oauth
# -*- coding: utf-8 -*-
"""
    tipfy.auth.oauth
    ~~~~~~~~~~~~~~~~

    Implementation of OAuth authentication scheme.

    Ported from `tornado.auth`_ and python-oauth2.

    :copyright: 2007 Leah Culver.
    :copyright: 2009 Facebook.
    :copyright: 2011 tipfy.org.
    :license: MIT License / Apache License Version 2.0, see LICENSE.txt for
        more details.
"""
from __future__ import absolute_import

import base64
import binascii
import cgi
import functools
import hashlib
import hmac
import logging
import time
import urllib
import urlparse
import uuid

from google.appengine.api import urlfetch


class OAuthMixin(object):
    """A :class:`tipfy.RequestHandler` mixin that implements OAuth
    authentication.
    """
    _OAUTH_VERSION = '1.0a'
    _OAUTH_NO_CALLBACKS = False

    def authorize_redirect(self, callback_uri=None, extra_params=None):
        """Redirects the user to obtain OAuth authorization for this service.

        Twitter and FriendFeed both require that you register a Callback
        URL with your application. You should call this method to log the
        user in, and then call get_authenticated_user() in the handler
        you registered as your Callback URL to complete the authorization
        process.

        This method sets a cookie called _oauth_request_token which is
        subsequently used (and cleared) in get_authenticated_user for
        security purposes.

        :param callback_uri:
        :param oauth_authorize_url:
            OAuth authorization URL. If not set, uses the value set in
            :attr:`_OAUTH_AUTHORIZE_URL`.
        :returns:
        """
        if callback_uri and self._OAUTH_NO_CALLBACKS:
            raise Exception('This service does not support oauth_callback.')

        if self._OAUTH_VERSION == '1.0a':
            url = self._oauth_request_token_url(callback_uri=callback_uri,
                extra_params=extra_params)
        else:
            url = self._oauth_request_token_url()

        try:
            response = urlfetch.fetch(url, deadline=10)
        except urlfetch.DownloadError, e:
            logging.exception(e)
            response = None

        return self._on_request_token(self._OAUTH_AUTHORIZE_URL, callback_uri,
            response)

    def get_authenticated_user(self, callback):
        """Gets the OAuth authorized user and access token on callback.

        This method should be called from the handler for your registered
        OAuth Callback URL to complete the registration process. We call
        callback with the authenticated user, which in addition to standard
        attributes like 'name' includes the 'access_key' attribute, which
        contains the OAuth access you can use to make authorized requests
        to this service on behalf of the user.

        :param callback:
        :returns:
        """
        request_key = self.request.args.get('oauth_token')
        oauth_verifier = self.request.args.get('oauth_verifier', None)
        request_cookie = self.request.cookies.get('_oauth_request_token')

        if request_cookie:
            parts = request_cookie.split('|')
            if len(parts) == 2:
                try:
                    cookie_key = base64.b64decode(parts[0])
                    cookie_secret = base64.b64decode(parts[1])
                except TypeError, e:
                    # TypeError: Incorrect padding
                    logging.exception(e)
                    request_cookie = None
            else:
                request_cookie = None

        if not request_cookie:
            return callback(None)

        self.session_store.delete_cookie('_oauth_request_token')

        if cookie_key != request_key:
            return callback(None)

        token = dict(key=cookie_key, secret=cookie_secret)
        if oauth_verifier:
            token['verifier'] = oauth_verifier

        try:
            url = self._oauth_access_token_url(token)
            response = urlfetch.fetch(url, deadline=10)
        except urlfetch.DownloadError, e:
            logging.exception(e)
            response = None

        return self._on_access_token(callback, response)

    def _oauth_request_token_url(self, callback_uri=None, extra_params=None):
        """

        :returns:
        """
        consumer_token = self._oauth_consumer_token()
        url = self._OAUTH_REQUEST_TOKEN_URL
        args = dict(
            oauth_consumer_key=consumer_token['key'],
            oauth_signature_method='HMAC-SHA1',
            oauth_timestamp=str(int(time.time())),
            oauth_nonce=binascii.b2a_hex(uuid.uuid4().bytes),
            oauth_version=self._OAUTH_VERSION
        )

        if self._OAUTH_VERSION == '1.0a':
            if callback_uri:
                args['oauth_callback'] = urlparse.urljoin(self.request.url,
                    callback_uri)

            if extra_params:
                args.update(extra_params)

        signature = _oauth_signature(consumer_token, 'GET', url, args)
        args['oauth_signature'] = signature
        return url + '?' + urllib.urlencode(args)

    def _on_request_token(self, authorize_url, callback_uri, response):
        """
        :param authorize_url:
        :param callback_uri:
        :param response:
        :returns:
        """
        if not response:
            logging.warning('Could not get OAuth request token.')
            self.abort(500)
        elif response.status_code < 200 or response.status_code >= 300:
            logging.warning('Bad OAuth response when requesting a token '
                '(%d): %s', response.status_code, response.content)
            self.abort(500)

        request_token = _oauth_parse_response(response.content)
        data = '|'.join([base64.b64encode(request_token['key']),
            base64.b64encode(request_token['secret'])])
        self.session_store.set_cookie('_oauth_request_token', data)
        args = dict(oauth_token=request_token['key'])

        if callback_uri:
            args['oauth_callback'] = urlparse.urljoin(
                self.request.url, callback_uri)

        return self.redirect(authorize_url + '?' + urllib.urlencode(args))

    def _oauth_access_token_url(self, request_token):
        """
        :param request_token:
        :returns:
        """
        consumer_token = self._oauth_consumer_token()
        url = self._OAUTH_ACCESS_TOKEN_URL
        args = dict(
            oauth_consumer_key=consumer_token['key'],
            oauth_token=request_token['key'],
            oauth_signature_method='HMAC-SHA1',
            oauth_timestamp=str(int(time.time())),
            oauth_nonce=binascii.b2a_hex(uuid.uuid4().bytes),
            oauth_version=self._OAUTH_VERSION,
        )
        if 'verifier' in request_token:
            args['oauth_verifier']=request_token['verifier']

        signature = _oauth_signature(consumer_token, 'GET', url, args,
            request_token)
        args['oauth_signature'] = signature
        return url + '?' + urllib.urlencode(args)

    def _on_access_token(self, callback, response):
        """
        :param callback:
        :param response:
        :returns:
        """
        if not response:
            logging.warning('Could not get OAuth access token.')
            self.abort(500)
        elif response.status_code < 200 or response.status_code >= 300:
            logging.warning('Bad OAuth response trying to get access token '
                '(%d): %s', response.status_code, response.content)
            self.abort(500)

        access_token = _oauth_parse_response(response.content)
        return self._oauth_get_user(access_token, functools.partial(
             self._on_oauth_get_user, access_token, callback))

    def _oauth_get_user(self, access_token, callback):
        """
        :param access_token:
        :param callback:
        :returns:
        """
        raise NotImplementedError()

    def _on_oauth_get_user(self, access_token, callback, user):
        """
        :param access_token:
        :param callback:
        :param user:
        :returns:
        """
        if not user:
            return callback(None)

        user['access_token'] = access_token
        return callback(user)

    def _oauth_request_parameters(self, url, access_token, parameters={},
                                  method='GET'):
        """Returns the OAuth parameters as a dict for the given request.

        parameters should include all POST arguments and query string arguments
        that will be sent with the request.

        :param url:
        :param access_token:
        :param parameters:
        :param method:
        :returns:
        """
        consumer_token = self._oauth_consumer_token()
        base_args = dict(
            oauth_consumer_key=consumer_token['key'],
            oauth_token=access_token['key'],
            oauth_signature_method='HMAC-SHA1',
            oauth_timestamp=str(int(time.time())),
            oauth_nonce=binascii.b2a_hex(uuid.uuid4().bytes),
            oauth_version=self._OAUTH_VERSION,
        )
        args = {}
        args.update(base_args)
        args.update(parameters)
        signature = _oauth_signature(consumer_token, method, url, args,
            access_token)
        base_args['oauth_signature'] = signature
        return base_args


class OAuth2Mixin(object):
    """Abstract implementation of OAuth v 2."""

    def authorize_redirect(self, redirect_uri=None, client_id=None,
        client_secret=None, extra_params=None):
        """Redirects the user to obtain OAuth authorization for this service.

        Some providers require that you register a Callback
        URL with your application. You should call this method to log the
        user in, and then call get_authenticated_user() in the handler
        you registered as your Callback URL to complete the authorization
        process.
        """
        args = {
            'redirect_uri': redirect_uri,
            'client_id': client_id
        }
        if extra_params:
            args.update(extra_params)

        return self.redirect(self._OAUTH_AUTHORIZE_URL +
            urllib.urlencode(args))

    def _oauth_request_token_url(self, redirect_uri= None, client_id = None,
        client_secret=None, code=None, extra_params=None):
        url = self._OAUTH_ACCESS_TOKEN_URL
        args = dict(
            redirect_uri=redirect_uri,
            code=code,
            client_id=client_id,
            client_secret=client_secret,
        )
        if extra_params:
            args.update(extra_params)

        return url + urllib.urlencode(args)


def _to_utf8(s):
    if isinstance(s, unicode):
        return s.encode('utf-8')

    return s


def _split_url_string(param_str):
    """Turn URL string into parameters."""
    parameters = cgi.parse_qs(param_str.encode('utf-8'), keep_blank_values=True)
    res = {}
    for k, v in parameters.iteritems():
        res[k] = urllib.unquote(v[0])

    return res


def _get_normalized_parameters(parameters, query):
    """Return a string that contains the parameters that must be signed."""
    items = []
    for key, value in parameters.iteritems():
        if key == 'oauth_signature':
            continue
        # 1.0a/9.1.1 states that kvp must be sorted by key, then by value,
        # so we unpack sequence values into multiple items for sorting.
        if isinstance(value, basestring):
            items.append((_to_utf8(key), _to_utf8(value)))
        else:
            try:
                value = list(value)
            except TypeError, e:
                assert 'is not iterable' in str(e)
                items.append((_to_utf8(key), _to_utf8(value)))
            else:
                items.extend((_to_utf8(key), _to_utf8(item)) for item in value)

    url_items = _split_url_string(query).items()
    url_items = [(_to_utf8(k), _to_utf8(v))
        for k, v in url_items if k != 'oauth_signature']
    items.extend(url_items)
    items.sort()
    encoded_str = urllib.urlencode(items)
    # Encode signature parameters per Oauth Core 1.0 protocol
    # spec draft 7, section 3.6
    # (http://tools.ietf.org/html/draft-hammer-oauth-07#section-3.6)
    # Spaces must be encoded with "%20" instead of "+"
    return encoded_str.replace('+', '%20').replace('%7E', '~')


def _oauth_signature(consumer_token, method, url, parameters={}, token=None):
    """Calculates the HMAC-SHA1 OAuth signature for the given request.

    See http://oauth.net/core/1.0/#signing_process

    :param consumer_token:
    :param method:
    :param url:
    :param parameters:
    :param token:
    :returns:
    """
    parts = urlparse.urlparse(url)
    scheme, netloc, path = parts[:3]
    query = parts[4]
    normalized_url = scheme.lower() + '://' + netloc.lower() + path

    sig = (
        _oauth_escape(method),
        _oauth_escape(normalized_url),
        _oauth_escape(_get_normalized_parameters(parameters, query)),
    )

    key = '%s&' % _oauth_escape(consumer_token['secret'])
    if token:
        key += _oauth_escape(token['secret'])

    base_string = '&'.join(sig)
    hashed = hmac.new(key, base_string, hashlib.sha1)
    return binascii.b2a_base64(hashed.digest())[:-1]


def _oauth_escape(val):
    """
    :param val:
    :returns:
    """
    if isinstance(val, unicode):
        val = val.encode('utf-8')

    return urllib.quote(val, safe='~')


def _oauth_parse_response(body):
    """
    :param body:
    :returns:
    """
    p = cgi.parse_qs(body, keep_blank_values=False)
    token = dict(key=p['oauth_token'][0], secret=p['oauth_token_secret'][0])

    # Add the extra parameters the Provider included to the token
    special = ('oauth_token', 'oauth_token_secret')
    token.update((k, p[k][0]) for k in p if k not in special)
    return token

########NEW FILE########
__FILENAME__ = openid
# -*- coding: utf-8 -*-
"""
    tipfy.auth.openid
    ~~~~~~~~~~~~~~~~~

    Implementation of OpenId authentication scheme.

    Ported from `tornado.auth`_.

    :copyright: 2009 Facebook.
    :copyright: 2011 tipfy.org.
    :license: Apache License Version 2.0, see LICENSE.txt for more details.
"""

from __future__ import absolute_import
import logging
import urllib
import urlparse

from google.appengine.api import urlfetch


class OpenIdMixin(object):
    """A :class:`tipfy.RequestHandler` mixin that implements OpenID
    authentication with Attribute Exchange.
    """
    #: OpenId provider endpoint. For example,
    #: 'https://www.google.com/accounts/o8/ud'
    _OPENID_ENDPOINT = None

    def authenticate_redirect(self, callback_uri=None, ax_attrs=None,
        openid_endpoint=None):
        """Returns the authentication URL for this service.

        After authentication, the service will redirect back to the given
        callback URI.

        We request the given attributes for the authenticated user by
        default (name, email, language, and username). If you don't need
        all those attributes for your app, you can request fewer with
        the ax_attrs keyword argument.

        :param callback_uri:
            The URL to redirect to after authentication.
        :param ax_attrs:
            List of Attribute Exchange attributes to be fetched.
        :param openid_endpoint:
            OpenId provider endpoint. If not set, uses the value set in
            :attr:`_OPENID_ENDPOINT`.
        :returns:
            None.
        """
        callback_uri = callback_uri or self.request.path
        ax_attrs = ax_attrs or ('name', 'email', 'language', 'username')
        openid_endpoint = openid_endpoint or self._OPENID_ENDPOINT
        args = self._openid_args(callback_uri, ax_attrs=ax_attrs)
        return self.redirect(make_full_url(openid_endpoint, args))

    def get_authenticated_user(self, callback, openid_endpoint=None):
        """Fetches the authenticated user data upon redirect.

        This method should be called by the handler that receives the
        redirect from the authenticate_redirect() or authorize_redirect()
        methods.

        :param callback:
            A function that is called after the authentication attempt. It
            is called passing a dictionary with the requested user attributes
            or None if the authentication failed.
        :param openid_endpoint:
            OpenId provider endpoint. For example,
            'https://www.google.com/accounts/o8/ud'.
        :returns:
            The result from the callback function.
        """
        # Changed method to POST. See:
        # https://github.com/facebook/tornado/commit/e5bd0c066afee37609156d1ac465057a726afcd4

        # Verify the OpenID response via direct request to the OP
        url = openid_endpoint or self._OPENID_ENDPOINT
        args = dict((k, v[-1].encode('utf8')) for k, v in self.request.args.lists())
        args['openid.mode'] = u'check_authentication'

        try:
            response = urlfetch.fetch(url, deadline=10, method=urlfetch.POST,
                payload=urllib.urlencode(args))
            if response.status_code < 200 or response.status_code >= 300:
                logging.warning('Invalid OpenID response: %s',
                    response.content)
            else:
                return self._on_authentication_verified(callback, response)
        except urlfetch.DownloadError, e:
            logging.exception(e)

        return self._on_authentication_verified(callback, None)


    def _openid_args(self, callback_uri, ax_attrs=None, oauth_scope=None):
        """Builds and returns the OpenId arguments used in the authentication
        request.

        :param callback_uri:
            The URL to redirect to after authentication.
        :param ax_attrs:
            List of Attribute Exchange attributes to be fetched.
        :param oauth_scope:
        :returns:
            A dictionary of arguments for the authentication URL.
        """
        url = urlparse.urljoin(self.request.url, callback_uri)
        args = {
            'openid.ns': 'http://specs.openid.net/auth/2.0',
            'openid.claimed_id':
                'http://specs.openid.net/auth/2.0/identifier_select',
            'openid.identity':
                'http://specs.openid.net/auth/2.0/identifier_select',
            'openid.return_to': url,
            'openid.realm': self.request.environ['wsgi.url_scheme'] + \
                '://' + self.request.host + '/',
            'openid.mode': 'checkid_setup',
        }
        if ax_attrs:
            args.update({
                'openid.ns.ax': 'http://openid.net/srv/ax/1.0',
                'openid.ax.mode': 'fetch_request',
            })
            ax_attrs = set(ax_attrs)
            required = []
            if 'name' in ax_attrs:
                ax_attrs -= set(['name', 'firstname', 'fullname', 'lastname'])
                required += ['firstname', 'fullname', 'lastname']
                args.update({
                    'openid.ax.type.firstname':
                        'http://axschema.org/namePerson/first',
                    'openid.ax.type.fullname':
                        'http://axschema.org/namePerson',
                    'openid.ax.type.lastname':
                        'http://axschema.org/namePerson/last',
                })

            known_attrs = {
                'email': 'http://axschema.org/contact/email',
                'language': 'http://axschema.org/pref/language',
                'username': 'http://axschema.org/namePerson/friendly',
            }

            for name in ax_attrs:
                args['openid.ax.type.' + name] = known_attrs[name]
                required.append(name)

            args['openid.ax.required'] = ','.join(required)

        if oauth_scope:
            args.update({
                'openid.ns.oauth':
                    'http://specs.openid.net/extensions/oauth/1.0',
                'openid.oauth.consumer': self.request.host.split(':')[0],
                'openid.oauth.scope': oauth_scope,
            })

        return args

    def _on_authentication_verified(self, callback, response):
        """Called after the authentication attempt. It calls the callback
        function set when the authentication process started, passing a
        dictionary of user data if the authentication was successful or
        None if it failed.

        :param callback:
            A function that is called after the authentication attempt. It
            is called passing a dictionary with the requested user attributes
            or None if the authentication failed.
        :param response:
            The response returned from the urlfetch call after the
            authentication attempt.
        :returns:
            The result from the callback function.
        """
        if not response:
            logging.warning('Missing OpenID response.')
            return callback(None)
        elif response.status_code < 200 or response.status_code >= 300:
            logging.warning('Invalid OpenID response (%d): %s',
                response.status_code, response.content)
            return callback(None)

        # Make sure we got back at least an email from Attribute Exchange.
        ax_ns = None
        for name, values in self.request.args.iterlists():
            if name.startswith('openid.ns.') and \
                values[-1] == u'http://openid.net/srv/ax/1.0':
                ax_ns = name[10:]
                break

        _ax_args = [
            ('email',      'http://axschema.org/contact/email'),
            ('name',       'http://axschema.org/namePerson'),
            ('first_name', 'http://axschema.org/namePerson/first'),
            ('last_name',  'http://axschema.org/namePerson/last'),
            ('username',   'http://axschema.org/namePerson/friendly'),
            ('locale',     'http://axschema.org/pref/language'),
        ]

        user = {}
        name_parts = []
        
        openid_signed_params = self.request.args.get("openid.signed", u'').split(',')
        
        for name, uri in _ax_args:
            value = self._get_ax_arg(uri, ax_ns, openid_signed_params)
            if value:
                user[name] = value
                if name in ('first_name', 'last_name'):
                    name_parts.append(value)

        if not user.get('name'):
            if name_parts:
                user['name'] = u' '.join(name_parts)
            elif user.get('email'):
                user['name'] = user.get('email').split('@', 1)[0]

        # get the claimed_id
        user['claimed_id'] = self.request.args.get('openid.claimed_id', u'')

        return callback(user)

    def _get_ax_arg(self, uri, ax_ns, openid_signed_params):
        """Returns an Attribute Exchange value from request.

        :param uri:
            Attribute Exchange URI.
        :param ax_ns:
            Attribute Exchange namespace.
        :returns:
            The Attribute Exchange value, if found in request.
        """
        if not ax_ns:
            return u''

        prefix = 'openid.' + ax_ns + '.type.'
        ax_name = None
        for name, values in self.request.args.iterlists():
            if not name[len("openid."):] in openid_signed_params:
                continue
            if values[-1] == uri and name.startswith(prefix):
                part = name[len(prefix):]
                ax_name = 'openid.' + ax_ns + '.value.' + part
                break

        if not ax_name:
            return u''
        
        if not ax_name[len("openid."):] in openid_signed_params: 
            return u''

        return self.request.args.get(ax_name, u'')


def make_full_url(base, args):
    if "?" in base:
        delimiter = "&"
    else:
        delimiter = "?"

    return base + delimiter + urllib.urlencode(args)

########NEW FILE########
__FILENAME__ = twitter
# -*- coding: utf-8 -*-
"""
    tipfy.auth.twitter
    ~~~~~~~~~~~~~~~~~~

    Implementation of Twitter authentication scheme.

    Ported from `tornado.auth`_.

    :copyright: 2009 Facebook.
    :copyright: 2011 tipfy.org.
    :license: Apache License Version 2.0, see LICENSE.txt for more details.
"""
from __future__ import absolute_import
import functools
import logging
import urllib

from google.appengine.api import urlfetch

from tipfy import REQUIRED_VALUE
from tipfy.utils import json_decode, json_encode
from tipfy.auth.oauth import OAuthMixin

#: Default configuration values for this module. Keys are:
#:
#: consumer_key
#:     Key provided when you register an application with Twitter.
#:
#: consumer_secret
#:     Secret provided when you register an application with Twitter.
default_config = {
    'consumer_key':    REQUIRED_VALUE,
    'consumer_secret': REQUIRED_VALUE,
}


class TwitterMixin(OAuthMixin):
    """Twitter OAuth authentication.

    To authenticate with Twitter, register your application with
    Twitter at http://twitter.com/apps. Then copy your Consumer Key and
    Consumer Secret to the application settings 'twitter_consumer_key' and
    'twitter_consumer_secret'. Use this Mixin on the handler for the URL
    you registered as your application's Callback URL.

    When your application is set up, you can use this Mixin like this
    to authenticate the user with Twitter and get access to their stream:

    class TwitterHandler(tornado.web.RequestHandler,
                         tornado.auth.TwitterMixin):
        @tornado.web.asynchronous
        def get(self):
            if self.get_argument("oauth_token", None):
                self.get_authenticated_user(self.async_callback(self._on_auth))
                return
            self.authorize_redirect()

        def _on_auth(self, user):
            if not user:
                raise tornado.web.HTTPError(500, "Twitter auth failed")
            # Save the user using, e.g., set_secure_cookie()

    The user object returned by get_authenticated_user() includes the
    attributes 'username', 'name', and all of the custom Twitter user
    attributes describe at
    http://apiwiki.twitter.com/Twitter-REST-API-Method%3A-users%C2%A0show
    in addition to 'access_token'. You should save the access token with
    the user; it is required to make requests on behalf of the user later
    with twitter_request().
    """
    _OAUTH_REQUEST_TOKEN_URL = 'http://api.twitter.com/oauth/request_token'
    _OAUTH_ACCESS_TOKEN_URL = 'http://api.twitter.com/oauth/access_token'
    _OAUTH_AUTHORIZE_URL = 'http://api.twitter.com/oauth/authorize'
    _OAUTH_AUTHENTICATE_URL = 'http://api.twitter.com/oauth/authenticate'

    def authenticate_redirect(self):
        """Just like authorize_redirect(), but auto-redirects if authorized.

        This is generally the right interface to use if you are using
        Twitter for single-sign on.
        """
        url = self._oauth_request_token_url()
        try:
            response = urlfetch.fetch(url, deadline=10)
        except urlfetch.DownloadError, e:
            logging.exception(e)
            response = None

        return self._on_request_token(self._OAUTH_AUTHENTICATE_URL, None,
            response)

    def twitter_request(self, path, callback, access_token=None,
        post_args=None, **args):
        """Fetches the given API path, e.g., "/statuses/user_timeline/btaylor"

        The path should not include the format (we automatically append
        ".json" and parse the JSON output).

        If the request is a POST, post_args should be provided. Query
        string arguments should be given as keyword arguments.

        All the Twitter methods are documented at
        http://apiwiki.twitter.com/Twitter-API-Documentation.

        Many methods require an OAuth access token which you can obtain
        through authorize_redirect() and get_authenticated_user(). The
        user returned through that process includes an 'access_token'
        attribute that can be used to make authenticated requests via
        this method. Example usage:

        class MainHandler(tornado.web.RequestHandler,
                          tornado.auth.TwitterMixin):
            @tornado.web.authenticated
            @tornado.web.asynchronous
            def get(self):
                self.twitter_request(
                    "/statuses/update",
                    post_args={"status": "Testing Tornado Web Server"},
                    access_token=user["access_token"],
                    callback=self.async_callback(self._on_post))

            def _on_post(self, new_entry):
                if not new_entry:
                    # Call failed; perhaps missing permission?
                    self.authorize_redirect()
                    return
                self.finish("Posted a message!")

        """
        # Add the OAuth resource request signature if we have credentials
        url = 'http://api.twitter.com/1' + path + '.json'
        if access_token:
            all_args = {}
            all_args.update(args)
            all_args.update(post_args or {})
            consumer_token = self._oauth_consumer_token()
            if post_args is not None:
                method = 'POST'
            else:
                method = 'GET'

            oauth = self._oauth_request_parameters(url, access_token,
                all_args, method=method)

            args.update(oauth)

        if args:
            url += '?' + urllib.urlencode(args)

        try:
            if post_args is not None:
                response = urlfetch.fetch(url, method='POST',
                    payload=urllib.urlencode(post_args), deadline=10)
            else:
                response = urlfetch.fetch(url, deadline=10)
        except urlfetch.DownloadError, e:
            logging.exception(e)
            response = None

        return self._on_twitter_request(callback, response)

    def _on_twitter_request(self, callback, response):
        if not response:
            logging.warning('Could not get Twitter request token.')
            return callback(None)
        elif response.status_code < 200 or response.status_code >= 300:
            logging.warning('Invalid Twitter response (%d): %s',
                response.status_code, response.content)
            return callback(None)

        return callback(json_decode(response.content))

    def _twitter_consumer_key(self):
        return self.app.config[__name__]['consumer_key']

    def _twitter_consumer_secret(self):
        return self.app.config[__name__]['consumer_secret']

    def _oauth_consumer_token(self):
        return dict(
            key=self._twitter_consumer_key(),
            secret=self._twitter_consumer_secret())

    def _oauth_get_user(self, access_token, callback):
        callback = functools.partial(self._parse_user_response, callback)
        return self.twitter_request(
            '/users/show/' + access_token['screen_name'],
            access_token=access_token, callback=callback)

    def _parse_user_response(self, callback, user):
        if user:
            user['username'] = user['screen_name']

        return callback(user)

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-
"""
    tipfy.config
    ~~~~~~~~~~~~

    Configuration object.

    :copyright: 2011 by tipfy.org.
    :license: BSD, see LICENSE.txt for more details.
"""
from werkzeug import import_string

__all__ = [
    'DEFAULT_VALUE', 'REQUIRED_VALUE',
]

#: Value used for missing default values.
DEFAULT_VALUE = object()
#: Value used for required values.
REQUIRED_VALUE = object()


class Config(dict):
    """A simple configuration dictionary keyed by module name. This is a
    dictionary of dictionaries. It requires all values to be dictionaries
    and applies updates and default values to the inner dictionaries instead
    of the first level one.

    The configuration object is available as a ``config`` attribute of
    :class:`tipfy.app.App`. If is instantiated and populated when the app
    is built::

        config = {}

        config['my.module'] = {
            'foo': 'bar',
        }

        app = App(rules=[Rule('/', name='home', handler=MyHandler)],
            config=config)

    Then to read configuration values, use :meth:`RequestHandler.get_config`::

        class MyHandler(RequestHandler):
            def get(self):
                foo = self.get_config('my.module', 'foo')

                # ...
    """
    #: Loaded module configurations.
    loaded = None

    def __init__(self, values=None, defaults=None):
        """Initializes the configuration object.

        :param values:
            A dictionary of configuration dictionaries for modules.
        :param defaults:
            A dictionary of configuration dictionaries for initial default
            values. These modules are marked as loaded.
        """
        self.loaded = []
        if values is not None:
            assert isinstance(values, dict)
            for module, config in values.iteritems():
                self.update(module, config)

        if defaults is not None:
            assert isinstance(defaults, dict)
            for module, config in defaults.iteritems():
                self.setdefault(module, config)
                self.loaded.append(module)

    def __getitem__(self, module):
        """Returns the configuration for a module. If it is not already
        set, loads a ``default_config`` variable from the given module and
        updates the configuration with those default values

        Every module that allows some kind of configuration sets a
        ``default_config`` global variable that is loaded by this function,
        cached and used in case the requested configuration was not defined
        by the user.

        :param module:
            The module name.
        :returns:
            A configuration value.
        """
        if module not in self.loaded:
            # Load default configuration and update config.
            values = import_string(module + '.default_config', silent=True)
            if values:
                self.setdefault(module, values)

            self.loaded.append(module)

        try:
            return dict.__getitem__(self, module)
        except KeyError:
            raise KeyError('Module %r is not configured.' % module)

    def __setitem__(self, module, values):
        """Sets a configuration for a module, requiring it to be a dictionary.

        :param module:
            A module name for the configuration, e.g.: `tipfy.i18n`.
        :param values:
            A dictionary of configurations for the module.
        """
        assert isinstance(values, dict), 'Module configuration must be a dict.'
        dict.__setitem__(self, module, SubConfig(module, values))

    def get(self, module, default=DEFAULT_VALUE):
        """Returns a configuration for a module. If default is not provided,
        returns an empty dict if the module is not configured.

        :param module:
            The module name.
        :params default:
            Default value to return if the module is not configured. If not
            set, returns an empty dict.
        :returns:
            A module configuration.
        """
        if default is DEFAULT_VALUE:
            default = {}

        return dict.get(self, module, default)

    def setdefault(self, module, values):
        """Sets a default configuration dictionary for a module.

        :param module:
            The module to set default configuration, e.g.: `tipfy.i18n`.
        :param values:
            A dictionary of configurations for the module.
        :returns:
            The module configuration dictionary.
        """
        assert isinstance(values, dict), 'Module configuration must be a dict.'
        if module not in self:
            module_dict = SubConfig(module)
            dict.__setitem__(self, module, module_dict)
        else:
            module_dict = dict.__getitem__(self, module)

        for key, value in values.iteritems():
            module_dict.setdefault(key, value)

        return module_dict

    def update(self, module, values):
        """Updates the configuration dictionary for a module.

        :param module:
            The module to update the configuration, e.g.: `tipfy.i18n`.
        :param values:
            A dictionary of configurations for the module.
        """
        assert isinstance(values, dict), 'Module configuration must be a dict.'
        if module not in self:
            module_dict = SubConfig(module)
            dict.__setitem__(self, module, module_dict)
        else:
            module_dict = dict.__getitem__(self, module)

        module_dict.update(values)

    def get_config(self, module, key=None, default=REQUIRED_VALUE):
        """Returns a configuration value for a module and optionally a key.
        Will raise a KeyError if they the module is not configured or the key
        doesn't exist and a default is not provided.

        :param module:
            The module name.
        :params key:
            The configuration key.
        :param default:
            Default value to return if the key doesn't exist.
        :returns:
            A module configuration.
        """
        module_dict = self.__getitem__(module)

        if key is None:
            return module_dict

        return module_dict.get(key, default)


class SubConfig(dict):
    def __init__(self, module, values=None):
        dict.__init__(self, values or ())
        self.module = module

    def __getitem__(self, key):
        if key not in self:
            raise KeyError('Module %r does not have the config key %r' %
                (self.module, key))

        return self.get(key)

    def get(self, key, default=None):
        value = dict.get(self, key, default)

        if value is REQUIRED_VALUE:
            raise KeyError('Module %r requires the config key %r to be '
                'set.' % (self.module, key))

        return value

########NEW FILE########
__FILENAME__ = handler
# -*- coding: utf-8 -*-
"""
    tipfy.handler
    ~~~~~~~~~~~~~

    Base request handler classes.

    :copyright: 2011 by tipfy.org.
    :license: BSD, see LICENSE.txt for more details.
"""
import urlparse

import werkzeug.utils

from .app import abort, redirect
from .config import REQUIRED_VALUE


class BaseRequestHandler(object):
    """Base class to handle requests. This is the central piece for an
    application and provides access to the current WSGI app and request.
    Additionally it provides lazy access to auth, i18n and session stores,
    and several utilities to handle a request.

    Although it is convenient to extend this class or :class:`RequestHandler`,
    the only interface required by the WSGI app is the following:

        class RequestHandler(object):
            def __init__(self, request):
                pass

            def __call__(self):
                return Response()

    A Tipfy-compatible handler can be implemented using only these two methods.
    """
    def __init__(self, request, app=None):
        """Initializes the handler.

        :param request:
            A :class:`Request` instance.
        """
        if app:
            # App argument is kept for backwards compatibility. Previously we
            # called passing (app, request) but because view functions are now
            # supported only request is passed and app is an attribute of the
            # request object.
            from warnings import warn
            warn(DeprecationWarning("BaseRequestHandler.__init__(): the "
                "'app' argument is deprecated. The constructor must receive "
                "only the Request object."))
            self.app = request
            self.request = app
        else:
            self.request = request

        # A context for shared data, e.g., template variables.
        self.context = {}

    def __call__(self):
        """Executes a handler method. This is called by :class:`tipfy.app.App`
        and must return a :attr:`response_class` object. If :attr:`middleware`
        are defined, use their hooks to process the request or handle
        exceptions.

        :returns:
            A :attr:`response_class` instance.
        """
        return self.dispatch()

    def dispatch(self):
        try:
            request = self.request
            method_name = request.rule and request.rule.handler_method
            if not method_name:
                method_name = request.method.lower()

            method = getattr(self, method_name, None)
            if not method:
                # 405 Method Not Allowed.
                # The response MUST include an Allow header containing a
                # list of valid methods for the requested resource.
                # http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.4.6
                self.abort(405, valid_methods=self.get_valid_methods())

            return self.make_response(method(**request.rule_args))
        except Exception, e:
            return self.handle_exception(exception=e)

    @werkzeug.utils.cached_property
    def app(self):
        """The current WSGI app instance.

        :returns:
            The current WSGI app instance.
        """
        return self.request.app

    @werkzeug.utils.cached_property
    def auth(self):
        """The auth store which provides access to the authenticated user and
        auth related functions.

        :returns:
            An auth store instance.
        """
        return self.request.auth

    @werkzeug.utils.cached_property
    def i18n(self):
        """The internationalization store which provides access to several
        translation and localization utilities.

        :returns:
            An i18n store instance.
        """
        return self.request.i18n

    @werkzeug.utils.cached_property
    def session(self):
        """A session dictionary using the default session configuration.

        :returns:
            A dictionary-like object with the current session data.
        """
        return self.session_store.get_session()

    @werkzeug.utils.cached_property
    def session_store(self):
        """The session store, responsible for managing sessions and flashes.

        :returns:
            A session store instance.
        """
        return self.request.session_store

    def abort(self, code, *args, **kwargs):
        """Raises an :class:`HTTPException`. This stops code execution,
        leaving the HTTP exception to be handled by an exception handler.

        :param code:
            HTTP status error code (e.g., 404).
        :param args:
            Positional arguments to be passed to the exception class.
        :param kwargs:
            Keyword arguments to be passed to the exception class.
        """
        abort(code, *args, **kwargs)

    def get_config(self, module, key=None, default=REQUIRED_VALUE):
        """Returns a configuration value for a module.

        .. warning: Deprecated. Use `self.app.config['module']['key']` instead.

        .. seealso:: :meth:`Config.get_config`.
        """
        from warnings import warn
        warn(DeprecationWarning("BaseRequestHandler.get_config(): this method "
            "is deprecated. Use self.app.config['module']['key'] instead."))
        return self.app.config.get_config(module, key=key, default=default)

    def get_valid_methods(self):
        """Returns a list of methods supported by this handler. By default it
        will look for HTTP methods this handler implements. For different
        routing schemes, override this.

        :returns:
            A list of methods supported by this handler.
        """
        return [method for method in self.app.allowed_methods if
            getattr(self, method.lower().replace('-', '_'), None)]

    def handle_exception(self, exception=None):
        """Handles an exception. The default behavior is to reraise the
        exception (no exception handling is implemented).

        :param exception:
            The exception that was raised.
        """
        raise

    def make_response(self, *rv):
        """Converts the returned value from a :class:`RequestHandler` to a
        response object that is an instance of
        :attr:`tipfy.app.App.response_class`.

        .. seealso:: :meth:`tipfy.app.App.make_response`.
        """
        return self.app.make_response(self.request, *rv)

    def redirect(self, location, code=302, response_class=None, body=None,
                 empty=False):
        """Returns a response object that redirects to the given location.

        This won't stop code execution, so you must return when calling it::

            return self.redirect('/some-path')

        :param location:
            A relative or absolute URI (e.g., '/contact'). If relative, it
            will be merged to the current request URL to form an absolute URL.
        :param code:
            The HTTP status code for the redirect. Default is 302.
        :param response_class:
            The class used to build the response. Default is
            :class:`tipfy.app.Response`.
        :param body:
            The response body. If not set uses a body with a standard message.
        :param empty:
            If True, returns a response with empty body.

            .. warning: Deprecated. Use `body=''` instead.
        :returns:
            A :class:`tipfy.app.Response` object with headers set for
            redirection.

        ..sealso:: :func:`tipfy.app.redirect`.
        """
        response_class = response_class or self.app.response_class

        if empty:
            from warnings import warn
            warn(DeprecationWarning("BaseRequestHandler.redirect(): the "
                "'empty' keyword argument is deprecated. Use body='' "
                "instead."))
            body = ''

        return redirect(location, code=code, response_class=response_class,
                        body=body)

    def redirect_to(self, _name, _code=302, _body=None, _empty=False,
                    **kwargs):
        """Returns a redirection response to a named URL rule.

        This is a convenience method that combines meth:`redirect` with
        meth:`url_for`.

        :param _name:
            The name of the :class:`tipfy.routing.Rule` to build a URL for.
        :param _code:
            The HTTP status code for the redirect. Default is 302.
        :param _body:
            The response body. If not set uses a body with a standard message.
        :param empty:
            If True, returns a response with empty body.

            .. warning: Deprecated. Use `body=''` instead.
        :param kwargs:
            Keyword arguments to build the URL.
        :returns:
            A :class:`tipfy.app.Response` object with headers set for
            redirection.
        """
        url = self.url_for(_name, _full=kwargs.pop('_full', True), **kwargs)
        return self.redirect(url, code=_code, body=_body, empty=_empty)

    def url_for(self, _name, **kwargs):
        """Returns a URL for a named :class:`Rule`.

        .. seealso:: :meth:`Router.url_for`.
        """
        return self.app.router.url_for(self.request, _name, kwargs)


class RequestHandler(BaseRequestHandler):
    #: A list of middleware instances. A middleware can implement three
    #: methods that are called before and after the current request method
    #: is executed, or if an exception occurs:
    #:
    #: before_dispatch(handler)
    #:     Called before the requested method is executed. If returns a
    #:     response, stops the middleware chain and uses that response, not
    #:     calling the requested method.
    #:
    #: after_dispatch(handler, response)
    #:     Called after the requested method is executed. Must always return
    #:     a response. These are executed in reverse order.
    #:
    #: handle_exception(handler, exception)
    #:     Called if an exception occurs while executing the requested method.
    #:     These are executed in reverse order.
    middleware = None

    def __call__(self):
        middleware = self.middleware or []

        # Execute before_dispatch middleware.
        for obj in middleware:
            func = getattr(obj, 'before_dispatch', None)
            if func:
                response = func(self)
                if response is not None:
                    break
        else:
            try:
                response = self.dispatch()
            except Exception, e:
                # Execute handle_exception middleware.
                for obj in reversed(middleware):
                    func = getattr(obj, 'handle_exception', None)
                    if func:
                        response = func(self, e)
                        if response is not None:
                            break
                else:
                    # If a middleware didn't return a response, reraise.
                    raise

        # Execute after_dispatch middleware.
        for obj in reversed(middleware):
            func = getattr(obj, 'after_dispatch', None)
            if func:
                response = func(self, response)

        # Done!
        return response


class RequestHandlerMiddleware(object):
    """Base class for :class:`RequestHandler` middleware."""
    def before_dispatch(self, handler):
        """Called before the handler method is executed.

        If the returned value is not None, stops the middleware chain and uses
        that value to create a response, and doesn't call the handler method.

        :param handler:
            A :class:`RequestHandler` instance.
        """

    def after_dispatch(self, handler, response):
        """Called after the handler method is executed.

        Must always return a response object.

        These are executed in reverse order.

        :param handler:
            A :class:`RequestHandler` instance.
        :param response:
            A :class:`tipfy.app.Response` instance.
        """
        return response

    def handle_exception(self, handler, exception):
        """Called if an exception occurs while executing the handler method.

        If the returned value is not None, stops the middleware chain and uses
        that value to create a response.

        These are executed in reverse order.

        :param handler:
            A :class:`RequestHandler` instance.
        :param exception:
            An exception.
        """

########NEW FILE########
__FILENAME__ = i18n
# -*- coding: utf-8 -*-
"""
    tipfy.i18n
    ~~~~~~~~~~

    Internationalization extension.

    This extension provides internationalization utilities: a translations
    store, hooks to set locale for the current request, functions to manipulate
    dates according to timezones or translate and localize strings and dates.

    It uses `Babel <http://babel.edgewall.org/>`_ to manage translations of
    strings and localization of dates and times, and
    `gae-pytz <http://code.google.com/p/gae-pytz/>`_ to handle timezones.

    Several ideas and code were borrowed from
    `Flask-Babel <http://pypi.python.org/pypi/Flask-Babel/>`_ and
    `Kay <http://code.google.com/p/kay-framework/>`_.

    :copyright: 2011 by tipfy.org.
    :license: BSD, see LICENSE.txt for more details.
"""
from datetime import datetime
import os

from babel import Locale, dates, numbers, support

try:
    from pytz.gae import pytz
except ImportError:
    try:
        import pytz
    except ImportError:
        raise RuntimeError('gaepytz or pytz are required.')

from tipfy.local import get_request

#: Default configuration values for this module. Keys are:
#:
#: locale
#:     The application default locale code. Default is ``en_US``.
#:
#: timezone
#:     The application default timezone according to the Olson
#:     database. Default is ``America/Chicago``.
#:
#: locale_session_key
#:     Session key used to save requested locale, if sessions are used.
#:
#: timezone_session_key
#:     Session key used to save requested timezone, if sessions are used.
#:
#: locale_request_lookup
#:     A list of tuples (method, key) to search
#:     for the locale to be loaded for the current request. The methods are
#:     searched in order until a locale is found. Available methods are:
#:
#:     - args: gets the locale code from ``GET`` arguments.
#:     - form: gets the locale code from ``POST`` arguments.
#:     - session: gets the locale code from the current session.
#:     - cookies: gets the locale code from a cookie.
#:     - rule_args: gets the locale code from the keywords in the current
#:       URL rule.
#:
#:     If none of the methods find a locale code, uses the default locale.
#:     Default is ``[('session', '_locale')]``: gets the locale from the
#:     session key ``_locale``.
#:
#: timezone_request_lookup
#:     Same as `locale_request_lookup`, but for the timezone.
#:
#: date_formats
#:     Default date formats for datetime, date and time.
default_config = {
    'locale':                  'en_US',
    'timezone':                'America/Chicago',
    'locale_session_key':      '_locale',
    'timezone_session_key':    '_timezone',
    'locale_request_lookup':   [('session', '_locale')],
    'timezone_request_lookup': [('session', '_timezone')],
    'date_formats': {
        'time':             'medium',
        'date':             'medium',
        'datetime':         'medium',
        'time.short':       None,
        'time.medium':      None,
        'time.full':        None,
        'time.long':        None,
        'time.iso':         "HH':'mm':'ss",
        'date.short':       None,
        'date.medium':      None,
        'date.full':        None,
        'date.long':        None,
        'date.iso':         "yyyy'-'MM'-'dd",
        'datetime.short':   None,
        'datetime.medium':  None,
        'datetime.full':    None,
        'datetime.long':    None,
        'datetime.iso':     "yyyy'-'MM'-'dd'T'HH':'mm':'ssZ",
    },
}


class I18nMiddleware(object):
    """Saves the current locale in the session at the end of request, if it
    differs from the current value stored in the session.
    """
    def after_dispatch(self, handler, response):
        """Called after the class:`tipfy.RequestHandler` method was executed.

        :param handler:
            A class:`tipfy.RequestHandler` instance.
        :param response:
            A class:`tipfy.Response` instance.
        :returns:
            A class:`tipfy.Response` instance.
        """
        session = handler.session
        i18n = handler.i18n
        locale_session_key = i18n.config['locale_session_key']
        timezone_session_key = i18n.config['timezone_session_key']

        # Only save if it differs from original session value.
        if i18n.locale != session.get(locale_session_key):
            session[locale_session_key] = i18n.locale

        if i18n.timezone != session.get(timezone_session_key):
            session[timezone_session_key] = i18n.timezone

        return response


class I18nStore(object):
    #: Loaded translations.
    loaded_translations = None
    #: Current locale.
    locale = None
    #: Current translations.
    translations = None
    #: Current timezone.
    timezone = None
    #: Current tzinfo.
    tzinfo = None

    def __init__(self, request):
        self.config = request.app.config[__name__]
        self.loaded_translations = request.app.registry.setdefault(
            'i18n.translations', {})
        self.set_locale_for_request(request)
        self.set_timezone_for_request(request)

    def set_locale_for_request(self, request):
        locale = _get_request_value(request,
            self.config['locale_request_lookup'], self.config['locale'])
        self.set_locale(locale)

    def set_timezone_for_request(self, request):
        timezone = _get_request_value(request,
            self.config['timezone_request_lookup'], self.config['timezone'])
        self.set_timezone(timezone)

    def set_locale(self, locale):
        """Sets the current locale and translations.

        :param locale:
            A locale code, e.g., ``pt_BR``.
        """
        self.locale = locale
        if locale not in self.loaded_translations:
            locales = [locale]
            if locale != self.config['locale']:
                locales.append(self.config['locale'])

            self.loaded_translations[locale] = self.load_translations(locales)

        self.translations = self.loaded_translations[locale]

    def set_timezone(self, timezone):
        """Sets the current timezone and tzinfo.

        :param timezone:
            The timezone name from the Olson database, e.g.:
            ``America/Chicago``.
        """
        self.timezone = timezone
        self.tzinfo = pytz.timezone(timezone)

    def load_translations(self, locales, dirname='locale', domain='messages'):
        return support.Translations.load(dirname, locales, domain)

    def gettext(self, string, **variables):
        """Translates a given string according to the current locale.

        :param string:
            The string to be translated.
        :param variables:
            Variables to format the returned string.
        :returns:
            The translated string.
        """
        if variables:
            return self.translations.ugettext(string) % variables

        return self.translations.ugettext(string)

    def ngettext(self, singular, plural, n, **variables):
        """Translates a possible pluralized string according to the current
        locale.

        :param singular:
            The singular for of the string to be translated.
        :param plural:
            The plural for of the string to be translated.
        :param n:
            An integer indicating if this is a singular or plural. If greater
            than 1, it is a plural.
        :param variables:
            Variables to format the returned string.
        :returns:
            The translated string.
        """
        if variables:
            return self.translations.ungettext(singular, plural, n) % variables

        return self.translations.ungettext(singular, plural, n)

    def to_local_timezone(self, datetime):
        """Returns a datetime object converted to the local timezone.

        :param datetime:
            A ``datetime`` object.
        :returns:
            A ``datetime`` object normalized to a timezone.
        """
        if datetime.tzinfo is None:
            datetime = datetime.replace(tzinfo=pytz.UTC)

        return self.tzinfo.normalize(datetime.astimezone(self.tzinfo))

    def to_utc(self, datetime):
        """Returns a datetime object converted to UTC and without tzinfo.

        :param datetime:
            A ``datetime`` object.
        :returns:
            A naive ``datetime`` object (no timezone), converted to UTC.
        """
        if datetime.tzinfo is None:
            datetime = self.tzinfo.localize(datetime)

        return datetime.astimezone(pytz.UTC).replace(tzinfo=None)

    def _get_format(self, key, format):
        """A helper for the datetime formatting functions. Returns a format
        name or pattern to be used by Babel date format functions.

        :param key:
            A format key to be get from config. Valid values are "date",
            "datetime" or "time".
        :param format:
            The format to be returned. Valid values are "short", "medium",
            "long", "full" or a custom date/time pattern.
        :returns:
            A format name or pattern to be used by Babel date format functions.
        """
        if format is None:
            format = self.config['date_formats'].get(key)

        if format in ('short', 'medium', 'full', 'long', 'iso'):
            rv = self.config['date_formats'].get('%s.%s' % (key, format))
            if rv is not None:
                format = rv

        return format

    def format_date(self, date=None, format=None, rebase=True):
        """Returns a date formatted according to the given pattern and
        following the current locale.

        :param date:
            A ``date`` or ``datetime`` object. If None, the current date in
            UTC is used.
        :param format:
            The format to be returned. Valid values are "short", "medium",
            "long", "full" or a custom date/time pattern. Example outputs:

            - short:  11/10/09
            - medium: Nov 10, 2009
            - long:   November 10, 2009
            - full:   Tuesday, November 10, 2009

        :param rebase:
            If True, converts the date to the current :attr:`timezone`.
        :returns:
            A formatted date in unicode.
        """
        format = self._get_format('date', format)

        if rebase and isinstance(date, datetime):
            date = self.to_local_timezone(date)

        return dates.format_date(date, format, locale=self.locale)

    def format_datetime(self, datetime=None, format=None, rebase=True):
        """Returns a date and time formatted according to the given pattern
        and following the current locale and timezone.

        :param datetime:
            A ``datetime`` object. If None, the current date and time in UTC
            is used.
        :param format:
            The format to be returned. Valid values are "short", "medium",
            "long", "full" or a custom date/time pattern. Example outputs:

            - short:  11/10/09 4:36 PM
            - medium: Nov 10, 2009 4:36:05 PM
            - long:   November 10, 2009 4:36:05 PM +0000
            - full:   Tuesday, November 10, 2009 4:36:05 PM World (GMT) Time

        :param rebase:
            If True, converts the datetime to the current :attr:`timezone`.
        :returns:
            A formatted date and time in unicode.
        """
        format = self._get_format('datetime', format)

        kwargs = {}
        if rebase:
            kwargs['tzinfo'] = self.tzinfo

        return dates.format_datetime(datetime, format, locale=self.locale,
            **kwargs)

    def format_time(self, time=None, format=None, rebase=True):
        """Returns a time formatted according to the given pattern and
        following the current locale and timezone.

        :param time:
            A ``time`` or ``datetime`` object. If None, the current
            time in UTC is used.
        :param format:
            The format to be returned. Valid values are "short", "medium",
            "long", "full" or a custom date/time pattern. Example outputs:

            - short:  4:36 PM
            - medium: 4:36:05 PM
            - long:   4:36:05 PM +0000
            - full:   4:36:05 PM World (GMT) Time

        :param rebase:
            If True, converts the time to the current :attr:`timezone`.
        :returns:
            A formatted time in unicode.
        """
        format = self._get_format('time', format)

        kwargs = {}
        if rebase:
            kwargs['tzinfo'] = self.tzinfo

        return dates.format_time(time, format, locale=self.locale, **kwargs)

    def format_timedelta(self, datetime_or_timedelta, granularity='second',
        threshold=.85):
        """Formats the elapsed time from the given date to now or the given
        timedelta. This currently requires an unreleased development version
        of Babel.

        :param datetime_or_timedelta:
            A ``timedelta`` object representing the time difference to format,
            or a ``datetime`` object in UTC.
        :param granularity:
            Determines the smallest unit that should be displayed, the value
            can be one of "year", "month", "week", "day", "hour", "minute" or
            "second".
        :param threshold:
            Factor that determines at which point the presentation switches to
            the next higher unit.
        :returns:
            A string with the elapsed time.
        """
        if isinstance(datetime_or_timedelta, datetime):
            datetime_or_timedelta = datetime.utcnow() - datetime_or_timedelta

        return dates.format_timedelta(datetime_or_timedelta, granularity,
            threshold=threshold, locale=self.locale)

    def format_number(self, number):
        """Returns the given number formatted for the current locale. Example::

            >>> format_number(1099, locale='en_US')
            u'1,099'

        :param number:
            The number to format.
        :returns:
            The formatted number.
        """
        return numbers.format_number(number, locale=self.locale)

    def format_decimal(self, number, format=None):
        """Returns the given decimal number formatted for the current locale.
        Example::

            >>> format_decimal(1.2345, locale='en_US')
            u'1.234'
            >>> format_decimal(1.2346, locale='en_US')
            u'1.235'
            >>> format_decimal(-1.2346, locale='en_US')
            u'-1.235'
            >>> format_decimal(1.2345, locale='sv_SE')
            u'1,234'
            >>> format_decimal(12345, locale='de')
            u'12.345'

        The appropriate thousands grouping and the decimal separator are used
        for each locale::

            >>> format_decimal(12345.5, locale='en_US')
            u'12,345.5'

        :param number:
            The number to format.
        :param format:
            Notation format.
        :returns:
            The formatted decimal number.
        """
        return numbers.format_decimal(number, format=format,
            locale=self.locale)

    def format_currency(self, number, currency, format=None):
        """Returns a formatted currency value. Example::

            >>> format_currency(1099.98, 'USD', locale='en_US')
            u'$1,099.98'
            >>> format_currency(1099.98, 'USD', locale='es_CO')
            u'US$\\xa01.099,98'
            >>> format_currency(1099.98, 'EUR', locale='de_DE')
            u'1.099,98\\xa0\\u20ac'

        The pattern can also be specified explicitly::

            >>> format_currency(1099.98, 'EUR', u'\\xa4\\xa4 #,##0.00', locale='en_US')
            u'EUR 1,099.98'

        :param number:
            The number to format.
        :param currency:
            The currency code.
        :param format:
            Notation format.
        :returns:
            The formatted currency value.
        """
        return numbers.format_currency(number, currency, format=format,
            locale=self.locale)

    def format_percent(self, number, format=None):
        """Returns formatted percent value for the current locale. Example::

            >>> format_percent(0.34, locale='en_US')
            u'34%'
            >>> format_percent(25.1234, locale='en_US')
            u'2,512%'
            >>> format_percent(25.1234, locale='sv_SE')
            u'2\\xa0512\\xa0%'

        The format pattern can also be specified explicitly::

            >>> format_percent(25.1234, u'#,##0\u2030', locale='en_US')
            u'25,123\u2030'

        :param number:
            The percent number to format
        :param format:
            Notation format.
        :returns:
            The formatted percent number.
        """
        return numbers.format_percent(number, format=format,
            locale=self.locale)

    def format_scientific(self, number, format=None):
        """Returns value formatted in scientific notation for the current
        locale. Example::

            >>> format_scientific(10000, locale='en_US')
            u'1E4'

        The format pattern can also be specified explicitly::

            >>> format_scientific(1234567, u'##0E00', locale='en_US')
            u'1.23E06'

        :param number:
            The number to format.
        :param format:
            Notation format.
        :returns:
            Value formatted in scientific notation.
        """
        return numbers.format_scientific(number, format=format,
            locale=self.locale)

    def parse_date(self, string):
        """Parses a date from a string.

        This function uses the date format for the locale as a hint to
        determine the order in which the date fields appear in the string.
        Example::

            >>> parse_date('4/1/04', locale='en_US')
            datetime.date(2004, 4, 1)
            >>> parse_date('01.04.2004', locale='de_DE')
            datetime.date(2004, 4, 1)

        :param string:
            The string containing the date.
        :returns:
            The parsed date object.
        """
        return dates.parse_date(string, locale=self.locale)

    def parse_datetime(self, string):
        """Parses a date and time from a string.

        This function uses the date and time formats for the locale as a hint
        to determine the order in which the time fields appear in the string.

        :param string:
            The string containing the date and time.
        :returns:
            The parsed datetime object.
        """
        return dates.parse_datetime(string, locale=self.locale)

    def parse_time(self, string):
        """Parses a time from a string.

        This function uses the time format for the locale as a hint to
        determine the order in which the time fields appear in the string.
        Example::

            >>> parse_time('15:30:00', locale='en_US')
            datetime.time(15, 30)

        :param string:
            The string containing the time.
        :returns:
            The parsed time object.
        """
        return dates.parse_time(string, locale=self.locale)

    def parse_number(self, string):
        """Parses localized number string into a long integer. Example::

            >>> parse_number('1,099', locale='en_US')
            1099L
            >>> parse_number('1.099', locale='de_DE')
            1099L

        When the given string cannot be parsed, an exception is raised::

            >>> parse_number('1.099,98', locale='de')
            Traceback (most recent call last):
               ...
            NumberFormatError: '1.099,98' is not a valid number

        :param string:
            The string to parse.
        :returns:
            The parsed number.
        :raises:
            ``NumberFormatError`` if the string can not be converted to a
            number.
        """
        return numbers.parse_number(string, locale=self.locale)

    def parse_decimal(self, string):
        """Parses localized decimal string into a float. Example::

            >>> parse_decimal('1,099.98', locale='en_US')
            1099.98
            >>> parse_decimal('1.099,98', locale='de')
            1099.98

        When the given string cannot be parsed, an exception is raised::

            >>> parse_decimal('2,109,998', locale='de')
            Traceback (most recent call last):
               ...
            NumberFormatError: '2,109,998' is not a valid decimal number

        :param string:
            The string to parse.
        :returns:
            The parsed decimal number.
        :raises:
            ``NumberFormatError`` if the string can not be converted to a
            decimal number.
        """
        return numbers.parse_decimal(string, locale=self.locale)

    def get_timezone_location(self, dt_or_tzinfo):
        """Returns a representation of the given timezone using "location
        format".

        The result depends on both the local display name of the country and
        the city assocaited with the time zone::

            >>> from pytz import timezone
            >>> tz = timezone('America/St_Johns')
            >>> get_timezone_location(tz, locale='de_DE')
            u"Kanada (St. John's)"
            >>> tz = timezone('America/Mexico_City')
            >>> get_timezone_location(tz, locale='de_DE')
            u'Mexiko (Mexiko-Stadt)'

        If the timezone is associated with a country that uses only a single
        timezone, just the localized country name is returned::

            >>> tz = timezone('Europe/Berlin')
            >>> get_timezone_name(tz, locale='de_DE')
            u'Deutschland'

        :param dt_or_tzinfo:
            The ``datetime`` or ``tzinfo`` object that determines
            the timezone; if None, the current date and time in UTC is assumed.
        :returns:
            The localized timezone name using location format.
        """
        return dates.get_timezone_name(dt_or_tzinfo, locale=self.locale)


def set_locale(locale):
    """See :meth:`I18nStore.set_locale`."""
    return get_request().i18n.set_locale(locale)


def set_timezone(timezone):
    """See :meth:`I18nStore.set_timezone`."""
    return get_request().i18n.set_timezone(timezone)


def gettext(string, **variables):
    """See :meth:`I18nStore.gettext`."""
    return get_request().i18n.gettext(string, **variables)


def ngettext(singular, plural, n, **variables):
    """See :meth:`I18nStore.ngettext`."""
    return get_request().i18n.ngettext(singular, plural, n, **variables)


def to_local_timezone(datetime):
    """See :meth:`I18nStore.to_local_timezone`."""
    return get_request().i18n.to_local_timezone(datetime)


def to_utc(datetime):
    """See :meth:`I18nStore.to_utc`."""
    return get_request().i18n.to_utc(datetime)


def format_date(date=None, format=None, rebase=True):
    """See :meth:`I18nStore.format_date`."""
    return get_request().i18n.format_date(date, format, rebase)


def format_datetime(datetime=None, format=None, rebase=True):
    """See :meth:`I18nStore.format_datetime`."""
    return get_request().i18n.format_datetime(datetime, format, rebase)


def format_time(time=None, format=None, rebase=True):
    """See :meth:`I18nStore.format_time`."""
    return get_request().i18n.format_time(time, format, rebase)


def format_timedelta(datetime_or_timedelta, granularity='second',
    threshold=.85):
    """See :meth:`I18nStore.format_timedelta`."""
    return get_request().i18n.format_timedelta(datetime_or_timedelta,
        granularity, threshold)


def format_number(number):
    """See :meth:`I18nStore.format_number`."""
    return get_request().i18n.format_number(number)


def format_decimal(number, format=None):
    """See :meth:`I18nStore.format_decimal`."""
    return get_request().i18n.format_decimal(number, format)


def format_currency(number, currency, format=None):
    """See :meth:`I18nStore.format_currency`."""
    return get_request().i18n.format_currency(number, currency, format)


def format_percent(number, format=None):
    """See :meth:`I18nStore.format_percent`."""
    return get_request().i18n.format_percent(number, format)


def format_scientific(number, format=None):
    """See :meth:`I18nStore.format_scientific`."""
    return get_request().i18n.format_scientific(number, format)


def parse_date(string):
    """See :meth:`I18nStore.parse_date`"""
    return get_request().i18n.parse_date(string)


def parse_datetime(string):
    """See :meth:`I18nStore.parse_datetime`."""
    return get_request().i18n.parse_datetime(string)


def parse_time(string):
    """See :meth:`I18nStore.parse_time`."""
    return get_request().i18n.parse_time(string)


def parse_number(string):
    """See :meth:`I18nStore.parse_number`."""
    return get_request().i18n.parse_number(string)


def parse_decimal(string):
    """See :meth:`I18nStore.parse_decimal`."""
    return get_request().i18n.parse_decimal(string)


def get_timezone_location(dt_or_tzinfo):
    """See :meth:`I18nStore.get_timezone_location`."""
    return get_request().i18n.get_timezone_location(dt_or_tzinfo)


def list_translations(dirname='locale'):
    """Returns a list of all the existing translations.  The list returned
    will be filled with actual locale objects and not just strings.

    :param dirname:
        Path to the translations directory.
    :returns:
        A list of ``babel.Locale`` objects.
    """
    if not os.path.isdir(dirname):
        return []

    result = []
    for folder in sorted(os.listdir(dirname)):
        if os.path.isdir(os.path.join(dirname, folder, 'LC_MESSAGES')):
            result.append(Locale.parse(folder))

    return result


def lazy_gettext(string, **variables):
    """A lazy version of :func:`gettext`.

    :param string:
        The string to be translated.
    :param variables:
        Variables to format the returned string.
    :returns:
        A ``babel.support.LazyProxy`` object that when accessed translates
        the string.
    """
    return support.LazyProxy(gettext, string, **variables)


def lazy_ngettext(singular, plural, n, **variables):
    """A lazy version of :func:`ngettext`.

    :param singular:
        The singular for of the string to be translated.
    :param plural:
        The plural for of the string to be translated.
    :param n:
        An integer indicating if this is a singular or plural. If greater
        than 1, it is a plural.
    :param variables:
        Variables to format the returned string.
    :returns:
        A ``babel.support.LazyProxy`` object that when accessed translates
        the string.
    """
    return support.LazyProxy(ngettext, singular, plural, n, **variables)


def _get_request_value(request, lookup_list, default=None):
    """Returns a locale code or timezone for the current request.

    It will use the configuration for ``locale_request_lookup`` or
    ``timezone_request_lookup`` to search for a key in ``GET``, ``POST``,
    session, cookie or keywords in the current URL rule. If no value is
    found, returns the default value.

    :param request:
        A :class:`tipfy.app.Request` instance.
    :param lookup_list:
        A list of `(attribute, key)` tuples to search in request, e.g.,
        ``[('args', 'lang'), ('session', 'locale')]``.
    :default:
        Default value to return in case none is found.
    :returns:
        A locale code or timezone setting.
    """
    value = None
    attrs = ('args', 'form', 'cookies', 'session', 'rule_args')
    for method, key in lookup_list:
        if method in attrs:
            # Get from GET, POST, cookies or rule_args.
            obj = getattr(request, method)
        else:
            obj = None

        if obj:
            value = obj.get(key, None)

        if value:
            break
    else:
        value = default

    return value


# Alias to gettext.
_ = gettext

########NEW FILE########
__FILENAME__ = json
# -*- coding: utf-8 -*-
"""
    tipfy.json
    ~~~~~~~~~~

    JSON encoder/decoder.

    :copyright: 2011 by tipfy.org.
    :license: BSD, see LICENSE.txt for more details.
"""
from __future__ import absolute_import

import base64

try:
    # Preference for installed library with updated fixes.
    import simplejson as json
except ImportError:
    try:
        # Standard library module in Python 2.6.
        import json
    except (ImportError, AssertionError):
        try:
            # Google App Engine.
            from django.utils import simplejson as json
        except ImportError:
            raise RuntimeError(
                'A JSON parser is required, e.g., simplejson at '
                'http://pypi.python.org/pypi/simplejson/')

assert hasattr(json, 'loads') and hasattr(json, 'dumps')


def json_encode(value, *args, **kwargs):
    """Serializes a value to JSON.

    :param value:
        A value to be serialized.
    :param args:
        Extra arguments to be passed to `json.dumps()`.
    :param kwargs:
        Extra keyword arguments to be passed to `json.dumps()`.
    :returns:
        The serialized value.
    """
    # JSON permits but does not require forward slashes to be escaped.
    # This is useful when json data is emitted in a <script> tag
    # in HTML, as it prevents </script> tags from prematurely terminating
    # the javscript.  Some json libraries do this escaping by default,
    # although python's standard library does not, so we do it here.
    # http://stackoverflow.com/questions/1580647/json-why-are-forward-slashes-escaped
    kwargs.setdefault('separators', (',', ':'))
    return json.dumps(value, *args, **kwargs).replace("</", "<\\/")


def json_decode(value, *args, **kwargs):
    """Deserializes a value from JSON.

    :param value:
        A value to be deserialized.
    :param args:
        Extra arguments to be passed to `json.loads()`.
    :param kwargs:
        Extra keyword arguments to be passed to `json.loads()`.
    :returns:
        The deserialized value.
    """
    if isinstance(value, str):
        value = value.decode('utf-8')

    assert isinstance(value, unicode)
    return json.loads(value, *args, **kwargs)


def json_b64encode(value):
    """Serializes a value to JSON and encodes it to base64.

    :param value:
        A value to be encoded.
    :returns:
        The encoded value.
    """
    return base64.b64encode(json_encode(value))


def json_b64decode(value):
    """Decodes a value from base64 and deserializes it from JSON.

    :param value:
        A value to be decoded.
    :returns:
        The decoded value.
    """
    return json_decode(base64.b64decode(value))

########NEW FILE########
__FILENAME__ = local
# -*- coding: utf-8 -*-
"""
    tipfy.local
    ~~~~~~~~~~~

    Context-local utilities.

    :copyright: 2011 by tipfy.org.
    :license: BSD, see LICENSE.txt for more details.
"""
import werkzeug.local

#: Context-local.
local = werkzeug.local.Local()


def get_app():
    """Returns the current WSGI app instance.

    :returns:
        The current :class:`tipfy.app.App` instance.
    """
    return local.app


def get_request():
    """Returns the current request instance.

    :returns:
        The current :class:`tipfy.app.Request` instance.
    """
    return local.request


#: A proxy to the active handler for a request. This is intended to be used by
#: functions called out of a handler context. Usage is generally discouraged:
#: it is preferable to pass the handler as argument when possible and only use
#: this as last alternative -- when a proxy is really needed.
#:
#: For example, the :func:`tipfy.utils.url_for` function requires the current
#: request to generate a URL. As its purpose is to be assigned to a template
#: context or other objects shared between requests, we use `current_handler`
#: there to dynamically get the currently active handler.
current_handler = local('current_handler')
#: Same as current_handler, only for the active WSGI app.
current_app = local('app')

########NEW FILE########
__FILENAME__ = middleware
# -*- coding: utf-8 -*-
"""
    tipfy.middleware
    ~~~~~~~~~~~~~~~~

    Miscelaneous handler middleware classes.

    :copyright: 2011 by tipfy.org.
    :license: BSD, see LICENSE.txt for more details.
"""
from werkzeug import ETagResponseMixin


class ETagMiddleware(object):
    """Adds an etag to all responses if they haven't already set one, and
    returns '304 Not Modified' if the request contains a matching etag.
    """
    def after_dispatch(self, handler, response):
        """Called after the class:`tipfy.RequestHandler` method was executed.

        :param handler:
            A class:`tipfy.RequestHandler` instance.
        :param response:
            A class:`tipfy.Response` instance.
        :returns:
            A class:`tipfy.Response` instance.
        """
        if not isinstance(response, ETagResponseMixin):
            return response

        response.add_etag()

        if handler.request.if_none_match.contains_raw(response.get_etag()[0]):
            return handler.app.response_class(status=304)

        return response

########NEW FILE########
__FILENAME__ = routing
# -*- coding: utf-8 -*-
"""
    tipfy.routing
    ~~~~~~~~~~~~~

    URL routing utilities.

    :copyright: 2011 by tipfy.org.
    :license: BSD, see LICENSE.txt for more details.
"""
from werkzeug import routing
from werkzeug import urls
from werkzeug import utils
from werkzeug import wrappers

from .local import get_request, local

# For export.
BaseConverter = routing.BaseConverter
EndpointPrefix = routing.EndpointPrefix
Map = routing.Map
RuleFactory = routing.RuleFactory
Subdomain = routing.Subdomain
Submount = routing.Submount


class Router(object):
    def __init__(self, app, rules=None):
        """Initializes the router.

        :param app:
            A :class:`tipfy.app.App` instance.
        :param rules:
            A list of initial :class:`Rule` instances.
        """
        self.app = app
        self.handlers = {}
        self.map = self.create_map(rules)

    def add(self, rule):
        """Adds a rule to the URL map.

        :param rule:
            A :class:`Rule` or rule factory instance or a list of rules
            to be added.
        """
        if isinstance(rule, list):
            for r in rule:
                self.map.add(r)
        else:
            self.map.add(rule)

    def match(self, request):
        """Matches registered :class:`Rule` definitions against the current
        request and returns the matched rule and rule arguments.

        The URL adapter, matched rule and rule arguments will be set in the
        :class:`tipfy.app.Request` instance.

        Three exceptions can occur when matching the rules: ``NotFound``,
        ``MethodNotAllowed`` or ``RequestRedirect``. The WSGI app will handle
        raised exceptions.

        :param request:
            A :class:`tipfy.app.Request` instance.
        :returns:
            A tuple ``(rule, rule_args)`` with the matched rule and rule
            arguments.
        """
        # Bind the URL map to the current request
        request.rule_adapter = self.map.bind_to_environ(request.environ,
            server_name=self.get_server_name(request))

        # Match the path against registered rules.
        match = request.rule_adapter.match(return_rule=True)
        request.rule, request.rule_args = match
        return match

    def dispatch(self, request):
        """Dispatches a request. This instantiates and calls a
        :class:`tipfy.RequestHandler` based on the matched :class:`Rule`.

        :param request:
            A :class:`tipfy.app.Request` instance.
        :param match:
            A tuple ``(rule, rule_args)`` with the matched rule and rule
            arguments.
        :param method:
            A method to be used instead of using the request or handler method.
        :returns:
            A :class:`tipfy.app.Response` instance.
        """
        rule, rule_args = self.match(request)
        handler = rule.handler
        if isinstance(handler, basestring):
            if handler not in self.handlers:
                self.handlers[handler] = utils.import_string(handler)

            rule.handler = handler = self.handlers[handler]

        rv = local.current_handler = handler(request)
        if not isinstance(rv, wrappers.BaseResponse) and \
            hasattr(rv, '__call__'):
            # If it is a callable but not a response, we call it again.
            rv = rv()

        return rv

    def url_for(self, request, name, kwargs):
        """Returns a URL for a named :class:`Rule`. This is the central place
        to build URLs for an app. It is used by :meth:`RequestHandler.url_for`,
        which conveniently pass the request object so you don't have to.

        :param request:
            The current request object.
        :param name:
            The rule name.
        :param kwargs:
            Values to build the URL. All variables not set in the rule
            default values must be passed and must conform to the format set
            in the rule. Extra keywords are appended as query arguments.

            A few keywords have special meaning:

            - **_full**: If True, builds an absolute URL.
            - **_method**: Uses a rule defined to handle specific request
              methods, if any are defined.
            - **_scheme**: URL scheme, e.g., `http` or `https`. If defined,
              an absolute URL is always returned.
            - **_netloc**: Network location, e.g., `www.google.com`. If
              defined, an absolute URL is always returned.
            - **_anchor**: If set, appends an anchor to generated URL.
        :returns:
            An absolute or relative URL.
        """
        method = kwargs.pop('_method', None)
        scheme = kwargs.pop('_scheme', None)
        netloc = kwargs.pop('_netloc', None)
        anchor = kwargs.pop('_anchor', None)
        full = kwargs.pop('_full', False) and not scheme and not netloc

        url = request.rule_adapter.build(name, values=kwargs, method=method,
                                        force_external=full)

        if scheme or netloc:
            url = '%s://%s%s' % (scheme or 'http', netloc or request.host, url)

        if anchor:
            url += '#%s' % urls.url_quote(anchor)

        return url

    def create_map(self, rules=None):
        """Returns a ``werkzeug.routing.Map`` instance with the given
        :class:`Rule` definitions.

        :param rules:
            A list of :class:`Rule` definitions.
        :returns:
            A ``werkzeug.routing.Map`` instance.
        """
        return Map(rules, default_subdomain=self.get_default_subdomain())

    def get_default_subdomain(self):
        """Returns the default subdomain for rules without a subdomain
        defined. By default it returns the configured default subdomain.

        :returns:
            The default subdomain to be used in the URL map.
        """
        return self.app.config['tipfy']['default_subdomain']

    def get_server_name(self, request):
        """Returns the server name used to bind the URL map. By default it
        returns the configured server name. Extend this if you want to
        calculate the server name dynamically (e.g., to match subdomains
        from multiple domains).

        :param request:
            A :class:`tipfy.app.Request` instance.
        :returns:
            The server name used to build the URL adapter.
        """
        return self.app.config['tipfy']['server_name']

    # Old name.
    build = url_for


class Rule(routing.Rule):
    """A Rule represents one URL pattern. Tipfy extends Werkzeug's Rule
    to support handler and name definitions. Handler is the
    :class:`tipfy.RequestHandler` class that will handle the request and name
    is a unique name used to build URL's. For example::

        Rule('/users', name='user-list', handler='my_app:UsersHandler')

    Access to the URL ``/users`` loads ``UsersHandler`` class from
    ``my_app`` module. To generate a URL to that page, use
    :meth:`RequestHandler.url_for` inside a handler::

        url = self.url_for('user-list')
    """
    def __init__(self, path, name=None, handler=None, handler_method=None,
                 **kwargs):
        """There are some options for `Rule` that change the way it behaves
        and are passed to the `Rule` constructor. Note that besides the
        rule-string all arguments *must* be keyword arguments in order to not
        break the application on upgrades.

        :param path:
            Rule strings basically are just normal URL paths with placeholders
            in the format ``<converter(arguments):name>`` where the converter
            and the arguments are optional. If no converter is defined the
            `default` converter is used which means `string` in the normal
            configuration.

            URL rules that end with a slash are branch URLs, others are leaves.
            If you have `strict_slashes` enabled (which is the default), all
            branch URLs that are matched without a trailing slash will trigger a
            redirect to the same URL with the missing slash appended.

            The converters are defined on the `Map`.
        :param name:
            The rule name used for URL generation.
        :param handler:
            The handler class or function used to handle requests when this
            rule matches. Can be defined as a string to be lazily imported.
        :param handler_method:
            The method to be executed from the handler class. If not defined,
            defaults to the current request method in lower case.
        :param defaults:
            An optional dict with defaults for other rules with the same
            endpoint. This is a bit tricky but useful if you want to have
            unique URLs::

                rules = [
                    Rule('/all/', name='pages', handler='handlers.PageHandler', defaults={'page': 1}),
                    Rule('/all/page/<int:page>', name='pages', handler='handlers.PageHandler'),
                ]

            If a user now visits ``http://example.com/all/page/1`` he will be
            redirected to ``http://example.com/all/``. If `redirect_defaults`
            is disabled on the `Map` instance this will only affect the URL
            generation.
        :param subdomain:
            The subdomain rule string for this rule. If not specified the rule
            only matches for the `default_subdomain` of the map. If the map is
            not bound to a subdomain this feature is disabled.

            Can be useful if you want to have user profiles on different
            subdomains and all subdomains are forwarded to your application.
        :param methods:
            A sequence of http methods this rule applies to. If not specified,
            all methods are allowed. For example this can be useful if you want
            different endpoints for `POST` and `GET`. If methods are defined
            and the path matches but the method matched against is not in this
            list or in the list of another rule for that path the error raised
            is of the type `MethodNotAllowed` rather than `NotFound`. If `GET`
            is present in the list of methods and `HEAD` is not, `HEAD` is
            added automatically.
        :param strict_slashes:
            Override the `Map` setting for `strict_slashes` only for this rule.
            If not specified the `Map` setting is used.
        :param build_only:
            Set this to True and the rule will never match but will create a
            URL that can be build. This is useful if you have resources on a
            subdomain or folder that are not handled by the WSGI application
            (like static data).
        :param redirect_to:
            If given this must be either a string or callable. In case of a
            callable it's called with the url adapter that triggered the match
            and the values of the URL as keyword arguments and has to return
            the target for the redirect, otherwise it has to be a string with
            placeholders in rule syntax::

                def foo_with_slug(adapter, id):
                    # ask the database for the slug for the old id. this of
                    # course has nothing to do with werkzeug.
                    return 'foo/' + Foo.get_slug_for_id(id)

                rules = [
                    Rule('/foo/<slug>', name='foo', handler='handlers.FooHandler'),
                    Rule('/some/old/url/<slug>', redirect_to='foo/<slug>'),
                    Rule('/other/old/url/<int:id>', redirect_to=foo_with_slug)
                ]

            When the rule is matched the routing system will raise a
            `RequestRedirect` exception with the target for the redirect.

            Keep in mind that the URL will be joined against the URL root of
            the script so don't use a leading slash on the target URL unless
            you really mean root of that domain.
        """
        # In werkzeug.routing, 'endpoint' defines the name or the callable
        # depending on the implementation, and an extra map is needed to map
        # named rules to their callables. We support werkzeug.routing's
        # 'endpoint' but favor a less ambiguous 'name' keyword, and accept an
        # extra 'handler' keyword that defines the callable to be executed.
        # This way a rule always carries both a name and a callable definition,
        # unambiguously, and no extra map is needed.
        self.name = kwargs.pop('endpoint', name)
        self.handler = handler = handler or self.name
        # If a handler string has a colon, we take it as the method from a
        # handler class, e.g., 'my_module.MyClass:my_method', and store it
        # in the rule as 'handler_method'. Not every rule mapping to a class
        # must define a method (the request method is used by default), and for
        # functions 'handler_method' is of course always None.
        self.handler_method = handler_method
        if isinstance(handler, basestring) and handler.rfind(':') != -1:
            if handler_method:
                raise BadArgumentError(
                    "If handler_method is defined in a Rule, handler "
                    "can't have a colon (got %r)." % handler)
            else:
                self.handler, self.handler_method = handler.rsplit(':', 1)

        super(Rule, self).__init__(path, endpoint=self.name, **kwargs)

    def empty(self):
        """Returns an unbound copy of this rule. This can be useful if you
        want to reuse an already bound URL for another map.
        """
        defaults = None
        if self.defaults is not None:
            defaults = dict(self.defaults)

        return Rule(self.rule, name=self.name, handler=self.handler,
            handler_method=self.handler_method, defaults=defaults,
            subdomain=self.subdomain, methods=self.methods,
            build_only=self.build_only, strict_slashes=self.strict_slashes,
            redirect_to=self.redirect_to)


class HandlerPrefix(RuleFactory):
    """Prefixes all handler values of nested rules with another string. For
    example, take these rules::

        rules = [
            Rule('/', name='index', handler='my_app.handlers.IndexHandler'),
            Rule('/entry/<entry_slug>', name='show',
                handler='my_app.handlers.ShowHandler'),
        ]

    You can wrap them by ``HandlerPrefix`` to define the handler module and
    avoid repetition. This is equivalent to the above::

        rules = [
            HandlerPrefix('my_app.handlers.', [
                Rule('/', name='index', handler='IndexHandler'),
                Rule('/entry/<entry_slug>', name='show',
                    handler='ShowHandler'),
            ]),
        ]
    """
    def __init__(self, prefix, rules):
        self.prefix = prefix
        self.rules = rules

    def get_rules(self, map):
        for rulefactory in self.rules:
            for rule in rulefactory.get_rules(map):
                rule = rule.empty()
                rule.handler = self.prefix + rule.handler
                yield rule


class NamePrefix(RuleFactory):
    """Prefixes all name values of nested rules with another string. For
    example, take these rules::

        rules = [
            Rule('/', name='company-home', handler='handlers.HomeHandler'),
            Rule('/about', name='company-about', handler='handlers.AboutHandler'),
            Rule('/contact', name='company-contact', handler='handlers.ContactHandler'),
        ]

    You can wrap them by ``NamePrefix`` to define the name avoid repetition.
    This is equivalent to the above::

        rules = [
            NamePrefix('company-', [
                Rule('/', name='home', handler='handlers.HomeHandler'),
                Rule('/about', name='about', handler='handlers.AboutHandler'),
                Rule('/contact', name='contact', handler='handlers.ContactHandler'),
            ]),
        ]
    """
    def __init__(self, prefix, rules):
        self.prefix = prefix
        self.rules = rules

    def get_rules(self, map):
        for rulefactory in self.rules:
            for rule in rulefactory.get_rules(map):
                rule = rule.empty()
                rule.name = rule.endpoint = self.prefix + rule.name
                yield rule


class RegexConverter(BaseConverter):
    """A :class:`Rule` converter that matches a regular expression::

        Rule(r'/<regex(".*$"):name>')

    This is mainly useful to match subdomains. Don't use it for normal rules.
    """
    def __init__(self, map, *items):
        BaseConverter.__init__(self, map)
        self.regex = items[0]


def url_for(_name, **kwargs):
    """A proxy to :meth:`Router.url_for`.

    .. seealso:: :meth:`Router.url_for`.
    """
    request = get_request()
    return request.app.router.url_for(request, _name, kwargs)


# Add regex converter to the list of converters.
Map.default_converters = dict(Map.default_converters)
Map.default_converters['regex'] = RegexConverter

########NEW FILE########
__FILENAME__ = scripting
# -*- coding: utf-8 -*-
"""
    tipfy.scripting
    ~~~~~~~~~~~~~~~

    Scripting utilities.

    :copyright: 2011 by tipfy.org.
    :license: BSD, see LICENSE.txt for more details.
"""
import os
import sys


def set_gae_sys_path():
    """Sets sys.path including App Engine SDK and requirements."""
    base_path = os.getcwd()
    app_path = os.path.join(base_path, 'app')
    gae_path = os.path.join(base_path, 'var/parts/google_appengine')

    extra_paths = [
        app_path,
        gae_path,
        # These paths are required by the SDK.
        os.path.join(gae_path, 'lib', 'antlr3'),
        os.path.join(gae_path, 'lib', 'django'),
        os.path.join(gae_path, 'lib', 'ipaddr'),
        os.path.join(gae_path, 'lib', 'webob'),
        os.path.join(gae_path, 'lib', 'yaml', 'lib'),
    ]

    sys.path = extra_paths + sys.path

########NEW FILE########
__FILENAME__ = sessions
# -*- coding: utf-8 -*-
"""
    tipfy.sessions
    ==============

    Lightweight sessions support for tipfy. Includes sessions using secure
    cookies and supports flash messages. For App Engine's datastore and
    memcache based sessions, see tipfy.appengine.sessions.

    :copyright: 2011 by tipfy.org.
    :license: Apache Sotware License, see LICENSE for details.
"""
import hashlib
import hmac
import logging
import time

from tipfy import APPENGINE, DEFAULT_VALUE, REQUIRED_VALUE
from tipfy.utils import json_b64encode, json_b64decode

from werkzeug import cached_property
from werkzeug.contrib.sessions import ModificationTrackingDict

#: Default configuration values for this module. Keys are:
#:
#: secret_key
#:     Secret key to generate session cookies. Set this to something random
#:     and unguessable. Default is :data:`tipfy.REQUIRED_VALUE` (an exception
#:     is raised if it is not set).
#:
#: default_backend
#:     The default backend to use when none is provided. Default is
#:     `securecookie`.
#:
#: cookie_name
#:     Name of the cookie to save a session or session id. Default is
#:     `session`.
#:
#: session_max_age:
#:     Default session expiration time in seconds. Limits the duration of the
#:     contents of a cookie, even if a session cookie exists. If None, the
#:     contents lasts as long as the cookie is valid. Default is None.
#:
#: cookie_args
#:     Default keyword arguments used to set a cookie. Keys are:
#:
#:     - max_age: Cookie max age in seconds. Limits the duration
#:       of a session cookie. If None, the cookie lasts until the client
#:       is closed. Default is None.
#:
#:     - domain: Domain of the cookie. To work accross subdomains the
#:       domain must be set to the main domain with a preceding dot, e.g.,
#:       cookies set for `.mydomain.org` will work in `foo.mydomain.org` and
#:       `bar.mydomain.org`. Default is None, which means that cookies will
#:       only work for the current subdomain.
#:
#:     - path: Path in which the authentication cookie is valid.
#:       Default is `/`.
#:
#:     - secure: Make the cookie only available via HTTPS.
#:
#:     - httponly: Disallow JavaScript to access the cookie.
default_config = {
    'secret_key':      REQUIRED_VALUE,
    'default_backend': 'securecookie',
    'cookie_name':     'session',
    'session_max_age': None,
    'cookie_args': {
        'max_age':     None,
        'domain':      None,
        'path':        '/',
        'secure':      None,
        'httponly':    False,
    }
}


class BaseSession(ModificationTrackingDict):
    __slots__ = ModificationTrackingDict.__slots__ + ('new',)

    def __init__(self, data=None, new=False):
        ModificationTrackingDict.__init__(self, data or ())
        self.new = new

    def get_flashes(self, key='_flash'):
        """Returns a flash message. Flash messages are deleted when first read.

        :param key:
            Name of the flash key stored in the session. Default is '_flash'.
        :returns:
            The data stored in the flash, or an empty list.
        """
        if key not in self:
            # Avoid popping if the key doesn't exist to not modify the session.
            return []

        return self.pop(key, [])

    def add_flash(self, value, level=None, key='_flash'):
        """Adds a flash message. Flash messages are deleted when first read.

        :param value:
            Value to be saved in the flash message.
        :param level:
            An optional level to set with the message. Default is `None`.
        :param key:
            Name of the flash key stored in the session. Default is '_flash'.
        """
        self.setdefault(key, []).append((value, level))

    #: Alias, Flask-like interface.
    flash = add_flash


class SecureCookieSession(BaseSession):
    """A session that stores data serialized in a signed cookie."""
    @classmethod
    def get_session(cls, store, name=None, **kwargs):
        if name:
            data = store.get_secure_cookie(name)
            if data is not None:
                return cls(data)

        return cls(new=True)

    def save_session(self, response, store, name, **kwargs):
        if not self.modified:
            return

        store.set_secure_cookie(response, name, dict(self), **kwargs)


class SecureCookieStore(object):
    """Encapsulates getting and setting secure cookies.

    Extracted from `Tornado`_ and modified.
    """
    def __init__(self, secret_key):
        """Initilizes this secure cookie store.

        :param secret_key:
            A long, random sequence of bytes to be used as the HMAC secret
            for the cookie signature.
        """
        self.secret_key = secret_key

    def get_cookie(self, request, name, max_age=None):
        """Returns the given signed cookie if it validates, or None.

        :param request:
            A :class:`tipfy.app.Request` object.
        :param name:
            Cookie name.
        :param max_age:
            Maximum age in seconds for a valid cookie. If the cookie is older
            than this, returns None.
        """
        value = request.cookies.get(name)

        if not value:
            return

        parts = value.split('|')
        if len(parts) != 3:
            return

        signature = self._get_signature(name, parts[0], parts[1])

        if not self._check_signature(parts[2], signature):
            logging.warning('Invalid cookie signature %r', value)
            return

        if max_age is not None and (int(parts[1]) < time.time() - max_age):
            logging.warning('Expired cookie %r', value)
            return

        try:
            return json_b64decode(parts[0])
        except:
            logging.warning('Cookie value failed to be decoded: %r', parts[0])
            return

    def set_cookie(self, response, name, value, **kwargs):
        """Signs and timestamps a cookie so it cannot be forged.

        To read a cookie set with this method, use get_cookie().

        :param response:
            A :class:`tipfy.app.Response` instance.
        :param name:
            Cookie name.
        :param value:
            Cookie value.
        :param kwargs:
            Options to save the cookie. See :meth:`SessionStore.get_session`.
        """
        response.set_cookie(name, self.get_signed_value(name, value), **kwargs)

    def get_signed_value(self, name, value):
        """Returns a signed value for a cookie.

        :param name:
            Cookie name.
        :param value:
            Cookie value.
        :returns:
            An signed value using HMAC.
        """
        timestamp = str(int(time.time()))
        value = json_b64encode(value)
        signature = self._get_signature(name, value, timestamp)
        return '|'.join([value, timestamp, signature])

    def _get_signature(self, *parts):
        """Generated an HMAC signatures."""
        hash = hmac.new(self.secret_key, digestmod=hashlib.sha1)
        hash.update('|'.join(parts))
        return hash.hexdigest()

    def _check_signature(self, a, b):
        """Checks if an HMAC signatures is valid."""
        if len(a) != len(b):
            return False

        result = 0
        for x, y in zip(a, b):
            result |= ord(x) ^ ord(y)

        return result == 0


class SessionStore(object):
    #: A dictionary with the default supported backends.
    default_backends = {
        'securecookie': SecureCookieSession,
    }

    def __init__(self, request, backends=None):
        self.request = request
        # Base configuration.
        self.config = request.app.config[__name__]
        # A dictionary of support backend classes.
        self.backends = backends or self.default_backends
        # The default backend to use when none is provided.
        self.default_backend = self.config['default_backend']
        # Tracked sessions.
        self._sessions = {}
        # Tracked cookies.
        self._cookies = {}

    @cached_property
    def secure_cookie_store(self):
        """Factory for secure cookies.

        :returns:
            A :class:`SecureCookieStore` instance.
        """
        return SecureCookieStore(self.config['secret_key'])

    def get_session(self, key=None, backend=None, **kwargs):
        """Returns a session for a given key. If the session doesn't exist, a
        new session is returned.

        :param key:
            Cookie name. If not provided, uses the ``cookie_name``
            value configured for this module.
        :param backend:
            Name of the session backend to be used. If not set, uses the
            default backend.
        :param kwargs:
            Options to set the session cookie. Keys are the same that can be
            passed to ``Response.set_cookie``, and override the ``cookie_args``
            values configured for this module. If not set, use the configured
            values.
        :returns:
            A dictionary-like session object.
        """
        key = key or self.config['cookie_name']
        backend = backend or self.default_backend
        sessions = self._sessions.setdefault(backend, {})

        if key not in sessions:
            kwargs = self.get_cookie_args(**kwargs)
            value = self.backends[backend].get_session(self, key, **kwargs)
            sessions[key] = (value, kwargs)

        return sessions[key][0]

    def set_session(self, key, value, backend=None, **kwargs):
        """Sets a session value. If a session with the same key exists, it
        will be overriden with the new value.

        :param key:
            Cookie name. See :meth:`get_session`.
        :param value:
            A dictionary of session values.
        :param backend:
            Name of the session backend. See :meth:`get_session`.
        :param kwargs:
            Options to save the cookie. See :meth:`get_session`.
        """
        assert isinstance(value, dict), 'Session value must be a dict.'
        backend = backend or self.default_backend
        sessions = self._sessions.setdefault(backend, {})
        session = self.backends[backend].get_session(self, **kwargs)
        session.update(value)
        kwargs = self.get_cookie_args(**kwargs)
        sessions[key] = (session, kwargs)

    def update_session_args(self, key, backend=None, **kwargs):
        """Updates the cookie options for a session.

        :param key:
            Cookie name. See :meth:`get_session`.
        :param backend:
            Name of the session backend. See :meth:`get_session`.
        :param kwargs:
            Options to save the cookie. See :meth:`get_session`.
        :returns:
            True if the session was updated, False otherwise.
        """
        backend = backend or self.default_backend
        sessions = self._sessions.setdefault(backend, {})
        if key in sessions:
            sessions[key][1].update(kwargs)
            return True

        return False

    def get_secure_cookie(self, name, max_age=DEFAULT_VALUE):
        """Returns a secure cookie from the request.

        :param name:
            Cookie name.
        :param max_age:
            Maximum age in seconds for a valid cookie. If the cookie is older
            than this, returns None.
        :returns:
            A secure cookie value or None if it is not set.
        """
        if max_age is DEFAULT_VALUE:
            max_age = self.config['session_max_age']

        return self.secure_cookie_store.get_cookie(self.request, name,
            max_age=max_age)

    def set_secure_cookie(self, response, name, value, **kwargs):
        """Sets a secure cookie in the response.

        :param response:
            A :class:`tipfy.app.Response` object.
        :param name:
            Cookie name.
        :param value:
            Cookie value. Must be a dictionary.
        :param kwargs:
            Options to save the cookie. See :meth:`get_session`.
        """
        assert isinstance(value, dict), 'Secure cookie value must be a dict.'
        kwargs = self.get_cookie_args(**kwargs)
        self.secure_cookie_store.set_cookie(response, name, value, **kwargs)

    def set_cookie(self, key, value, format=None, **kwargs):
        """Registers a cookie or secure cookie to be saved or deleted.

        :param key:
            Cookie name.
        :param value:
            Cookie value.
        :param format:
            If set to 'json', the value is serialized to JSON and encoded
            to base64.
        :param kwargs:
            Options to save the cookie. See :meth:`get_session`.
        """
        if format == 'json':
            value = json_b64encode(value)

        self._cookies[key] = (value, self.get_cookie_args(**kwargs))

    def unset_cookie(self, key):
        """Unsets a cookie previously set. This won't delete the cookie, it
        just won't be saved.

        :param key:
            Cookie name.
        """
        self._cookies.pop(key, None)

    def delete_cookie(self, key, **kwargs):
        """Registers a cookie or secure cookie to be deleted.

        :param key:
            Cookie name.
        :param kwargs:
            Options to delete the cookie. See :meth:`get_session`.
        """
        self._cookies[key] = (None, self.get_cookie_args(**kwargs))

    def save(self, response):
        """Saves all cookies and sessions to a response object.

        :param response:
            A ``tipfy.Response`` object.
        """
        if self._cookies:
            for key, (value, kwargs) in self._cookies.iteritems():
                if value is None:
                    response.delete_cookie(key, path=kwargs.get('path', '/'),
                        domain=kwargs.get('domain', None))
                else:
                    response.set_cookie(key, value, **kwargs)

        if self._sessions:
            for sessions in self._sessions.values():
                for key, (value, kwargs) in sessions.iteritems():
                    value.save_session(response, self, key, **kwargs)

    def get_cookie_args(self, **kwargs):
        """Returns a copy of the default cookie configuration updated with the
        passed arguments.

        :param kwargs:
            Keyword arguments to override in the cookie configuration.
        :returns:
            A dictionary with arguments for the session cookie.
        """
        _kwargs = self.config['cookie_args'].copy()
        _kwargs.update(kwargs)
        return _kwargs


class SessionMiddleware(object):
    """Saves sessions at the end of a request."""
    def after_dispatch(self, handler, response):
        """Called after the class:`tipfy.RequestHandler` method was executed.

        :param handler:
            A class:`tipfy.RequestHandler` instance.
        :param response:
            A class:`tipfy.Response` instance.
        :returns:
            A class:`tipfy.Response` instance.
        """
        handler.session_store.save(response)
        return response


if APPENGINE:
    from tipfy.appengine.sessions import DatastoreSession, MemcacheSession
    SessionStore.default_backends.update({
        'datastore': DatastoreSession,
        'memcache':  MemcacheSession,
    })

########NEW FILE########
__FILENAME__ = template
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A simple template system that compiles templates to Python code.

Basic usage looks like:

    t = template.Template("<html>{{ myvalue }}</html>")
    print t.generate(myvalue="XXX")

Loader is a class that loads templates from a root directory and caches
the compiled templates:

    loader = template.Loader("/home/btaylor")
    print loader.load("test.html").generate(myvalue="XXX")

We compile all templates to raw Python. Error-reporting is currently... uh,
interesting. Syntax for the templates

    ### base.html
    <html>
      <head>
        <title>{% block title %}Default title{% end %}</title>
      </head>
      <body>
        <ul>
          {% for student in students %}
            {% block student %}
              <li>{{ escape(student.name) }}</li>
            {% end %}
          {% end %}
        </ul>
      </body>
    </html>

    ### bold.html
    {% extends "base.html" %}

    {% block title %}A bolder title{% end %}

    {% block student %}
      <li><span style="bold">{{ escape(student.name) }}</span></li>
    {% block %}

Unlike most other template systems, we do not put any restrictions on the
expressions you can include in your statements. if and for blocks get
translated exactly into Python, do you can do complex expressions like:

   {% for student in [p for p in people if p.student and p.age > 23] %}
     <li>{{ escape(student.name) }}</li>
   {% end %}

Translating directly to Python means you can apply functions to expressions
easily, like the escape() function in the examples above. You can pass
functions in to your template just like any other variable:

   ### Python code
   def add(x, y):
      return x + y
   template.execute(add=add)

   ### The template
   {{ add(1, 2) }}

We provide the functions escape(), url_escape(), json_encode(), and squeeze()
to all templates by default.
"""

from __future__ import with_statement

import cStringIO
import datetime
import htmlentitydefs
import logging
import os.path
import re
import urllib
import xml.sax.saxutils
import zipfile

from .json import json_encode


def utf8(value):
    """Encodes a unicode value to UTF-8 if not yet encoded.

    :param value:
        Value to be encoded.
    :returns:
        An encoded string.
    """
    if isinstance(value, unicode):
        return value.encode("utf-8")

    assert isinstance(value, str)
    return value


def _unicode(value):
    """Encodes a string value to unicode if not yet decoded.

    :param value:
        Value to be decoded.
    :returns:
        A decoded string.
    """
    if isinstance(value, str):
        return value.decode("utf-8")

    assert isinstance(value, unicode)
    return value


def xhtml_escape(value):
    """Escapes a string so it is valid within XML or XHTML.

    :param value:
        The value to be escaped.
    :returns:
        The escaped value.
    """
    return utf8(xml.sax.saxutils.escape(value, {'"': "&quot;"}))


def xhtml_unescape(value):
    """Un-escapes an XML-escaped string.

    :param value:
        The value to be un-escaped.
    :returns:
        The un-escaped value.
    """
    return re.sub(r"&(#?)(\w+?);", _convert_entity, _unicode(value))


def squeeze(value):
    """Replace all sequences of whitespace chars with a single space."""
    return re.sub(r"[\x00-\x20]+", " ", value).strip()


def url_escape(value):
    """Returns a valid URL-encoded version of the given value."""
    return urllib.quote_plus(utf8(value))


def _convert_entity(m):
    if m.group(1) == "#":
        try:
            return unichr(int(m.group(2)))
        except ValueError:
            return "&#%s;" % m.group(2)
    try:
        return _HTML_UNICODE_MAP[m.group(2)]
    except KeyError:
        return "&%s;" % m.group(2)


def _build_unicode_map():
    return dict((name, unichr(value)) for \
        name, value in htmlentitydefs.name2codepoint.iteritems())


_HTML_UNICODE_MAP = _build_unicode_map()


class Template(object):
    """A compiled template.

    We compile into Python from the given template_string. You can generate
    the template from variables with generate().
    """
    def __init__(self, template_string, name="<string>", loader=None,
                 compress_whitespace=None):
        self.name = name
        if compress_whitespace is None:
            compress_whitespace = name.endswith(".html") or \
                name.endswith(".js")
        reader = _TemplateReader(name, template_string)
        self.file = _File(_parse(reader))
        self.code = self._generate_python(loader, compress_whitespace)
        try:
            self.compiled = compile(self.code, self.name, "exec")
        except:
            formatted_code = _format_code(self.code).rstrip()
            logging.error("%s code:\n%s", self.name, formatted_code)
            raise

    def generate(self, **kwargs):
        """Generate this template with the given arguments."""
        namespace = {
            "escape": xhtml_escape,
            "url_escape": url_escape,
            "json_encode": json_encode,
            "squeeze": squeeze,
            "datetime": datetime,
        }
        namespace.update(kwargs)
        exec self.compiled in namespace
        execute = namespace["_execute"]
        try:
            return execute()
        except:
            formatted_code = _format_code(self.code).rstrip()
            logging.error("%s code:\n%s", self.name, formatted_code)
            raise

    def _generate_python(self, loader, compress_whitespace):
        buffer = cStringIO.StringIO()
        try:
            named_blocks = {}
            ancestors = self._get_ancestors(loader)
            ancestors.reverse()
            for ancestor in ancestors:
                ancestor.find_named_blocks(loader, named_blocks)
            self.file.find_named_blocks(loader, named_blocks)
            writer = _CodeWriter(buffer, named_blocks, loader, self,
                                 compress_whitespace)
            ancestors[0].generate(writer)
            return buffer.getvalue()
        finally:
            buffer.close()

    def _get_ancestors(self, loader):
        ancestors = [self.file]
        for chunk in self.file.body.chunks:
            if isinstance(chunk, _ExtendsBlock):
                if not loader:
                    raise ParseError("{% extends %} block found, but no "
                                     "template loader")
                template = loader.load(chunk.name, self.name)
                ancestors.extend(template._get_ancestors(loader))
        return ancestors


class Loader(object):
    """A template loader that loads from a single root directory.

    You must use a template loader to use template constructs like
    {% extends %} and {% include %}. Loader caches all templates after
    they are loaded the first time.
    """
    def __init__(self, root_directory):
        self.root = os.path.abspath(root_directory)
        self.templates = {}

    def reset(self):
        self.templates = {}

    def resolve_path(self, name, parent_path=None):
        if parent_path and not parent_path.startswith("<") and \
           not parent_path.startswith("/") and \
           not name.startswith("/"):
            current_path = os.path.join(self.root, parent_path)
            file_dir = os.path.dirname(os.path.abspath(current_path))
            relative_path = os.path.abspath(os.path.join(file_dir, name))
            if relative_path.startswith(self.root):
                name = relative_path[len(self.root) + 1:]
        return name

    def load(self, name, parent_path=None):
        name = self.resolve_path(name, parent_path=parent_path)
        if name not in self.templates:
            path = os.path.join(self.root, name)
            f = open(path, "r")
            self.templates[name] = Template(f.read(), name=name, loader=self)
            f.close()
        return self.templates[name]


class ZipLoader(Loader):
    """A template loader that loads from a zip file and a root directory.

    You must use a template loader to use template constructs like
    {% extends %} and {% include %}. Loader caches all templates after
    they are loaded the first time.
    """
    def __init__(self, zip_path, root_directory):
        self.zipfile = zipfile.ZipFile(zip_path, 'r')
        self.root = os.path.join(root_directory)
        self.templates = {}

    def load(self, name, parent_path=None):
        name = self.resolve_path(name, parent_path=parent_path)
        if name not in self.templates:
            path = os.path.join(self.root, name)
            tpl = self.zipfile.read(path)
            self.templates[name] = Template(tpl, name=name, loader=self)
        return self.templates[name]


class _Node(object):
    def each_child(self):
        return ()

    def generate(self, writer):
        raise NotImplementedError()

    def find_named_blocks(self, loader, named_blocks):
        for child in self.each_child():
            child.find_named_blocks(loader, named_blocks)


class _File(_Node):
    def __init__(self, body):
        self.body = body

    def generate(self, writer):
        writer.write_line("def _execute():")
        with writer.indent():
            writer.write_line("_buffer = []")
            self.body.generate(writer)
            writer.write_line("return ''.join(_buffer)")

    def each_child(self):
        return (self.body,)


class _ChunkList(_Node):
    def __init__(self, chunks):
        self.chunks = chunks

    def generate(self, writer):
        for chunk in self.chunks:
            chunk.generate(writer)

    def each_child(self):
        return self.chunks


class _NamedBlock(_Node):
    def __init__(self, name, body=None):
        self.name = name
        self.body = body

    def each_child(self):
        return (self.body,)

    def generate(self, writer):
        writer.named_blocks[self.name].generate(writer)

    def find_named_blocks(self, loader, named_blocks):
        named_blocks[self.name] = self.body
        _Node.find_named_blocks(self, loader, named_blocks)


class _ExtendsBlock(_Node):
    def __init__(self, name):
        self.name = name


class _IncludeBlock(_Node):
    def __init__(self, name, reader):
        self.name = name
        self.template_name = reader.name

    def find_named_blocks(self, loader, named_blocks):
        included = loader.load(self.name, self.template_name)
        included.file.find_named_blocks(loader, named_blocks)

    def generate(self, writer):
        included = writer.loader.load(self.name, self.template_name)
        old = writer.current_template
        writer.current_template = included
        included.file.body.generate(writer)
        writer.current_template = old


class _ApplyBlock(_Node):
    def __init__(self, method, body=None):
        self.method = method
        self.body = body

    def each_child(self):
        return (self.body,)

    def generate(self, writer):
        method_name = "apply%d" % writer.apply_counter
        writer.apply_counter += 1
        writer.write_line("def %s():" % method_name)
        with writer.indent():
            writer.write_line("_buffer = []")
            self.body.generate(writer)
            writer.write_line("return ''.join(_buffer)")
        writer.write_line("_buffer.append(%s(%s()))" % (
            self.method, method_name))


class _ControlBlock(_Node):
    def __init__(self, statement, body=None):
        self.statement = statement
        self.body = body

    def each_child(self):
        return (self.body,)

    def generate(self, writer):
        writer.write_line("%s:" % self.statement)
        with writer.indent():
            self.body.generate(writer)


class _IntermediateControlBlock(_Node):
    def __init__(self, statement):
        self.statement = statement

    def generate(self, writer):
        writer.write_line("%s:" % self.statement, writer.indent_size() - 1)


class _Statement(_Node):
    def __init__(self, statement):
        self.statement = statement

    def generate(self, writer):
        writer.write_line(self.statement)


class _Expression(_Node):
    def __init__(self, expression):
        self.expression = expression

    def generate(self, writer):
        writer.write_line("_tmp = %s" % self.expression)
        writer.write_line("if isinstance(_tmp, str): _buffer.append(_tmp)")
        writer.write_line("elif isinstance(_tmp, unicode): "
                          "_buffer.append(_tmp.encode('utf-8'))")
        writer.write_line("else: _buffer.append(str(_tmp))")


class _Text(_Node):
    def __init__(self, value):
        self.value = value

    def generate(self, writer):
        value = self.value

        # Compress lots of white space to a single character. If the whitespace
        # breaks a line, have it continue to break a line, but just with a
        # single \n character
        if writer.compress_whitespace and "<pre>" not in value:
            value = re.sub(r"([\t ]+)", " ", value)
            value = re.sub(r"(\s*\n\s*)", "\n", value)

        if value:
            writer.write_line('_buffer.append(%r)' % value)


class ParseError(Exception):
    """Raised for template syntax errors."""
    pass


class _CodeWriter(object):
    def __init__(self, file, named_blocks, loader, current_template,
                 compress_whitespace):
        self.file = file
        self.named_blocks = named_blocks
        self.loader = loader
        self.current_template = current_template
        self.compress_whitespace = compress_whitespace
        self.apply_counter = 0
        self._indent = 0

    def indent(self):
        return self

    def indent_size(self):
        return self._indent

    def __enter__(self):
        self._indent += 1
        return self

    def __exit__(self, *args):
        assert self._indent > 0
        self._indent -= 1

    def write_line(self, line, indent=None):
        if indent == None:
            indent = self._indent
        for i in xrange(indent):
            self.file.write("    ")
        print >> self.file, line


class _TemplateReader(object):
    def __init__(self, name, text):
        self.name = name
        self.text = text
        self.line = 0
        self.pos = 0

    def find(self, needle, start=0, end=None):
        assert start >= 0, start
        pos = self.pos
        start += pos
        if end is None:
            index = self.text.find(needle, start)
        else:
            end += pos
            assert end >= start
            index = self.text.find(needle, start, end)
        if index != -1:
            index -= pos
        return index

    def consume(self, count=None):
        if count is None:
            count = len(self.text) - self.pos
        newpos = self.pos + count
        self.line += self.text.count("\n", self.pos, newpos)
        s = self.text[self.pos:newpos]
        self.pos = newpos
        return s

    def remaining(self):
        return len(self.text) - self.pos

    def __len__(self):
        return self.remaining()

    def __getitem__(self, key):
        if type(key) is slice:
            size = len(self)
            start, stop, step = key.indices(size)
            if start is None:
                start = self.pos
            else:
                start += self.pos

            if stop is not None:
                stop += self.pos

            return self.text[slice(start, stop, step)]
        elif key < 0:
            return self.text[key]
        else:
            return self.text[self.pos + key]

    def __str__(self):
        return self.text[self.pos:]


def _format_code(code):
    lines = code.splitlines()
    format = "%%%dd  %%s\n" % len(repr(len(lines) + 1))
    return "".join([format % (i + 1, line) for (i, line) in enumerate(lines)])


def _parse(reader, in_block=None):
    body = _ChunkList([])
    while True:
        # Find next template directive
        curly = 0
        while True:
            curly = reader.find("{", curly)
            if curly == -1 or curly + 1 == reader.remaining():
                # EOF
                if in_block:
                    raise ParseError("Missing {%% end %%} block for %s" %
                                     in_block)
                body.chunks.append(_Text(reader.consume()))
                return body
            # If the first curly brace is not the start of a special token,
            # start searching from the character after it
            if reader[curly + 1] not in ("{", "%"):
                curly += 1
                continue
            # When there are more than 2 curlies in a row, use the
            # innermost ones.  This is useful when generating languages
            # like latex where curlies are also meaningful
            if (curly + 2 < reader.remaining() and
                reader[curly + 1] == '{' and reader[curly + 2] == '{'):
                curly += 1
                continue
            break

        # Append any text before the special token
        if curly > 0:
            body.chunks.append(_Text(reader.consume(curly)))

        start_brace = reader.consume(2)
        line = reader.line

        # Expression
        if start_brace == "{{":
            end = reader.find("}}")
            if end == -1 or reader.find("\n", 0, end) != -1:
                raise ParseError("Missing end expression }} on line %d" % line)
            contents = reader.consume(end).strip()
            reader.consume(2)
            if not contents:
                raise ParseError("Empty expression on line %d" % line)
            body.chunks.append(_Expression(contents))
            continue

        # Block
        assert start_brace == "{%", start_brace
        end = reader.find("%}")
        if end == -1 or reader.find("\n", 0, end) != -1:
            raise ParseError("Missing end block %%} on line %d" % line)
        contents = reader.consume(end).strip()
        reader.consume(2)
        if not contents:
            raise ParseError("Empty block tag ({%% %%}) on line %d" % line)

        operator, space, suffix = contents.partition(" ")
        suffix = suffix.strip()

        # Intermediate ("else", "elif", etc) blocks
        intermediate_blocks = {
            "else": set(["if", "for", "while"]),
            "elif": set(["if"]),
            "except": set(["try"]),
            "finally": set(["try"]),
        }
        allowed_parents = intermediate_blocks.get(operator)
        if allowed_parents is not None:
            if not in_block:
                raise ParseError("%s outside %s block" %
                            (operator, allowed_parents))
            if in_block not in allowed_parents:
                raise ParseError("%s block cannot be attached to %s block" % \
                    (operator, in_block))
            body.chunks.append(_IntermediateControlBlock(contents))
            continue

        # End tag
        elif operator == "end":
            if not in_block:
                raise ParseError("Extra {%% end %%} block on line %d" % line)
            return body

        elif operator in ("extends", "include", "set", "import", "comment"):
            if operator == "comment":
                continue
            if operator == "extends":
                suffix = suffix.strip('"').strip("'")
                if not suffix:
                    raise ParseError("extends missing file path on line %d" % \
                        line)
                block = _ExtendsBlock(suffix)
            elif operator == "import":
                if not suffix:
                    raise ParseError("import missing statement on line %d" % \
                        line)
                block = _Statement(contents)
            elif operator == "include":
                suffix = suffix.strip('"').strip("'")
                if not suffix:
                    raise ParseError("include missing file path on line %d" % \
                        line)
                block = _IncludeBlock(suffix, reader)
            elif operator == "set":
                if not suffix:
                    raise ParseError("set missing statement on line %d" % line)
                block = _Statement(suffix)
            body.chunks.append(block)
            continue

        elif operator in ("apply", "block", "try", "if", "for", "while"):
            # parse inner body recursively
            block_body = _parse(reader, operator)
            if operator == "apply":
                if not suffix:
                    raise ParseError("apply missing method name on line %d" % \
                        line)
                block = _ApplyBlock(suffix, block_body)
            elif operator == "block":
                if not suffix:
                    raise ParseError("block missing name on line %d" % line)
                block = _NamedBlock(suffix, block_body)
            else:
                block = _ControlBlock(contents, block_body)
            body.chunks.append(block)
            continue

        else:
            raise ParseError("unknown operator: %r" % operator)

########NEW FILE########
__FILENAME__ = testing
# -*- coding: utf-8 -*-
"""
    tipfy.testing
    ~~~~~~~~~~~~~

    Unit test utilities.

    :copyright: 2011 by tipfy.org.
    :license: BSD, see LICENSE.txt for more details.
"""
from werkzeug.utils import import_string

from tipfy.app import local


class CurrentHandlerContext(object):
    """Returns a handler set as a current handler. The handler instance
    or class can be passed explicitly or request values can be passed to
    match a handler in the app router.

    This is intended to be used with a `with` statement::

        from __future__ import with_statement

        from tipfy import App, Rule

        app = App(rules=[
            Rule('/about', name='home', handler='handlers.AboutHandler'),
        ])

        with app.get_test_handler('/about') as handler:
            self.assertEqual(handler.url_for('/', _full=True),
                'http://localhost/about')

    The context will set the request and current_handler and clean it up
    after the execution.
    """
    def __init__(self, app, *args, **kwargs):
        """Initializes the handler context.

        :param app:
            A :class:`tipfy.app.App` instance.
        :param args:
            Arguments to build a :class:`tipfy.app.Request` instance if a
            request is not passed explicitly.
        :param kwargs:
            Keyword arguments to build a :class:`Request` instance if a request
            is not passed explicitly. A few keys have special meaning:

            - `request`: a :class:`Request` object. If not passed, a new
              request is built using the passed `args` and `kwargs`. If
              `handler` or `handler_class` are not passed, the request is used
              to match a handler in the app router.
            - `handler_class`: instantiate this handler class instead of
              matching one using the request object.
            - `handler`: a handler instance. If passed, the handler is simply
              set and reset as current_handler during the context execution.
        """
        from warnings import warn
        warn(DeprecationWarning("CurrentHandlerContext: this class "
            "is deprecated. Use tipfy.app.RequestContext instead."))
        self.app = app
        self.handler = kwargs.pop('handler', None)
        self.handler_class = kwargs.pop('handler_class', None)
        self.request = kwargs.pop('request', None)
        if self.request is None:
            self.request = app.request_class.from_values(*args, **kwargs)

    def __enter__(self):
        local.request = self.request
        local.app = self.request.app = self.app
        if self.handler is not None:
            local.current_handler = self.handler
        else:
            if self.handler_class is None:
                rule, rule_args = self.app.router.match(self.request)
                handler_class = rule.handler
                if isinstance(handler_class, basestring):
                    handler_class = import_string(handler_class)
            else:
                handler_class = self.handler_class

            local.current_handler = handler_class(self.request)

        return local.current_handler

    def __exit__(self, type, value, traceback):
        local.__release_local__()

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""Escaping/unescaping methods for HTML, JSON, URLs, and others."""
import base64
import htmlentitydefs
import re
import unicodedata
import urllib
import xml.sax.saxutils

# Imported here for compatibility.
from .json import json_encode, json_decode, json_b64encode, json_b64decode
from .local import get_request
from .routing import url_for


def xhtml_escape(value):
    """Escapes a string so it is valid within XML or XHTML.

    :param value:
        The value to be escaped.
    :returns:
        The escaped value.
    """
    return utf8(xml.sax.saxutils.escape(value, {'"': "&quot;"}))


def xhtml_unescape(value):
    """Un-escapes an XML-escaped string.

    :param value:
        The value to be un-escaped.
    :returns:
        The un-escaped value.
    """
    return re.sub(r"&(#?)(\w+?);", _convert_entity, _unicode(value))


def render_json_response(*args, **kwargs):
    """Renders a JSON response.

    :param args:
        Arguments to be passed to json_encode().
    :param kwargs:
        Keyword arguments to be passed to json_encode().
    :returns:
        A :class:`Response` object with a JSON string in the body and
        mimetype set to ``application/json``.
    """
    return get_request().app.response_class(json_encode(*args, **kwargs),
        mimetype='application/json')


def squeeze(value):
    """Replace all sequences of whitespace chars with a single space."""
    return re.sub(r"[\x00-\x20]+", " ", value).strip()


def url_escape(value):
    """Returns a valid URL-encoded version of the given value."""
    return urllib.quote_plus(utf8(value))


def url_unescape(value):
    """Decodes the given value from a URL."""
    return _unicode(urllib.unquote_plus(value))


def utf8(value):
    """Encodes a unicode value to UTF-8 if not yet encoded.

    :param value:
        Value to be encoded.
    :returns:
        An encoded string.
    """
    if isinstance(value, unicode):
        return value.encode("utf-8")

    assert isinstance(value, str)
    return value


def _unicode(value):
    """Encodes a string value to unicode if not yet decoded.

    :param value:
        Value to be decoded.
    :returns:
        A decoded string.
    """
    if isinstance(value, str):
        return value.decode("utf-8")

    assert isinstance(value, unicode)
    return value


def _convert_entity(m):
    if m.group(1) == "#":
        try:
            return unichr(int(m.group(2)))
        except ValueError:
            return "&#%s;" % m.group(2)
    try:
        return _HTML_UNICODE_MAP[m.group(2)]
    except KeyError:
        return "&%s;" % m.group(2)


def _build_unicode_map():
    return dict((name, unichr(value)) for \
        name, value in htmlentitydefs.name2codepoint.iteritems())


def slugify(value, max_length=None, default=None):
    """Converts a string to slug format (all lowercase, words separated by
    dashes).

    :param value:
        The string to be slugified.
    :param max_length:
        An integer to restrict the resulting string to a maximum length.
        Words are not broken when restricting length.
    :param default:
        A default value in case the resulting string is empty.
    :returns:
        A slugified string.
    """
    value = _unicode(value)
    s = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').lower()
    s = re.sub('-+', '-', re.sub('[^a-zA-Z0-9-]+', '-', s)).strip('-')
    if not s:
        return default

    if max_length:
        # Restrict length without breaking words.
        while len(s) > max_length:
            if s.find('-') == -1:
                s = s[:max_length]
            else:
                s = s.rsplit('-', 1)[0]

    return s


_HTML_UNICODE_MAP = _build_unicode_map()

########NEW FILE########
__FILENAME__ = scripts
# -*- coding: utf-8 -*-
"""
    tipfyext.jinja2.scripts
    ~~~~~~~~~~~~~~~~~~~~~~~

    Command line utilities for Jinja2.

    :copyright: 2011 by tipfy.org.
    :license: BSD, see LICENSE.txt for more details.
"""
import os
import sys

from jinja2 import FileSystemLoader

from tipfy import Tipfy
from tipfy.scripting import set_gae_sys_path
from tipfyext.jinja2 import Jinja2


def walk(top, topdown=True, onerror=None, followlinks=False):
    """Borrowed from Python 2.6.5 codebase. It is os.walk() with symlinks."""
    try:
        names = os.listdir(top)
    except os.error, err:
        if onerror is not None:
            onerror(err)
        return

    dirs, nondirs = [], []
    for name in names:
        if os.path.isdir(os.path.join(top, name)):
            dirs.append(name)
        else:
            nondirs.append(name)

    if topdown:
        yield top, dirs, nondirs
    for name in dirs:
        path = os.path.join(top, name)
        if followlinks or not os.path.islink(path):
            for x in walk(path, topdown, onerror, followlinks):
                yield x
    if not topdown:
        yield top, dirs, nondirs


def list_templates(self):
    """Monkeypatch for FileSystemLoader to follow symlinks when searching for
    templates.
    """
    found = set()
    for searchpath in self.searchpath:
        for dirpath, dirnames, filenames in walk(searchpath, followlinks=True):
            for filename in filenames:
                template = os.path.join(dirpath, filename) \
                    [len(searchpath):].strip(os.path.sep) \
                                      .replace(os.path.sep, '/')
                if template[:2] == './':
                    template = template[2:]
                if template not in found:
                    found.add(template)
    return sorted(found)


def logger(msg):
    sys.stderr.write('%s\n' % msg)


def filter_templates(tpl):
    # ignore templates that start with '.' and py files.
    if os.path.basename(tpl).startswith('.'):
        return False

    if os.path.basename(tpl).endswith(('.py', '.pyc', '.zip')):
        return False

    return True


def compile_templates(argv=None):
    """Compiles templates for better performance. This is a command line
    script. From the buildout directory, run:

        bin/jinja2_compile

    It will compile templates from the directory configured for 'templates_dir'
    to the one configured for 'templates_compiled_target'.

    At this time it doesn't accept any arguments.
    """
    if argv is None:
        argv = sys.argv

    base_path = os.getcwd()
    app_path = os.path.join(base_path, 'app')
    gae_path = os.path.join(base_path, 'var/parts/google_appengine')

    extra_paths = [
        app_path,
        os.path.join(app_path, 'lib'),
        os.path.join(app_path, 'lib', 'dist'),
        gae_path,
        # These paths are required by the SDK.
        os.path.join(gae_path, 'lib', 'antlr3'),
        os.path.join(gae_path, 'lib', 'django'),
        os.path.join(gae_path, 'lib', 'ipaddr'),
        os.path.join(gae_path, 'lib', 'webob'),
        os.path.join(gae_path, 'lib', 'yaml', 'lib'),
    ]

    sys.path = extra_paths + sys.path

    from config import config

    app = Tipfy(config=config)
    template_path = app.get_config('tipfyext.jinja2', 'templates_dir')
    compiled_path = app.get_config('tipfyext.jinja2',
        'templates_compiled_target')

    if compiled_path is None:
        raise ValueError('Missing configuration key to compile templates.')

    if isinstance(template_path, basestring):
        # A single path.
        source = os.path.join(app_path, template_path)
    else:
        # A list of paths.
        source = [os.path.join(app_path, p) for p in template_path]

    target = os.path.join(app_path, compiled_path)

    # Set templates dir and deactivate compiled dir to use normal loader to
    # find the templates to be compiled.
    app.config['tipfyext.jinja2']['templates_dir'] = source
    app.config['tipfyext.jinja2']['templates_compiled_target'] = None

    if target.endswith('.zip'):
        zip_cfg = 'deflated'
    else:
        zip_cfg = None

    old_list_templates = FileSystemLoader.list_templates
    FileSystemLoader.list_templates = list_templates

    env = Jinja2.factory(app, 'jinja2').environment
    env.compile_templates(target, extensions=None,
        filter_func=filter_templates, zip=zip_cfg, log_function=logger,
        ignore_errors=False, py_compile=False)

    FileSystemLoader.list_templates = old_list_templates

########NEW FILE########
__FILENAME__ = mako
# -*- coding: utf-8 -*-
"""
    tipfyext.mako
    ~~~~~~~~~~~~~

    Mako template support for Tipfy.

    Learn more about Mako at http://www.makotemplates.org/

    :copyright: 2011 by tipfy.org.
    :license: BSD, see LICENSE.txt for more details.
"""
from __future__ import absolute_import
from cStringIO import StringIO

from mako.lookup import TemplateLookup
from mako.runtime import Context

from werkzeug import cached_property

#: Default configuration values for this module. Keys are:
#:
#: templates_dir
#:     Directory for templates. Default is `templates`.
default_config = {
    'templates_dir': 'templates',
}


class Mako(object):
    def __init__(self, app, _globals=None, filters=None):
        self.app = app
        config = app.config[__name__]
        dirs = config.get('templates_dir')
        if isinstance(dirs, basestring):
            dirs = [dirs]

        self.environment = TemplateLookup(directories=dirs,
            output_encoding='utf-8', encoding_errors='replace')

    def render(self, _filename, **context):
        """Renders a template and returns a response object.

        :param _filename:
            The template filename, related to the templates directory.
        :param context:
            Keyword arguments used as variables in the rendered template.
            These will override values set in the request context.
       :returns:
            A rendered template.
        """
        template = self.environment.get_template(_filename)
        return template.render_unicode(**context)

    def render_template(self, _handler, _filename, **context):
        """Renders a template and returns a response object.

        :param _filename:
            The template filename, related to the templates directory.
        :param context:
            Keyword arguments used as variables in the rendered template.
            These will override values set in the request context.
       :returns:
            A rendered template.
        """
        ctx = _handler.context.copy()
        ctx.update(context)
        return self.render(_filename, **ctx)

    def render_response(self, _handler, _filename, **context):
        """Returns a response object with a rendered template.

        :param _filename:
            The template filename, related to the templates directory.
        :param context:
            Keyword arguments used as variables in the rendered template.
            These will override values set in the request context.
        """
        res = self.render_template(_handler, _filename, **context)
        return self.app.response_class(res)

    @classmethod
    def factory(cls, _app, _name, **kwargs):
        if _name not in _app.registry:
            _app.registry[_name] = cls(_app, **kwargs)

        return _app.registry[_name]


class MakoMixin(object):
    """Mixin that adds ``render_template`` and ``render_response`` methods
    to a :class:`tipfy.RequestHandler`. It will use the request context to
    render templates.
    """
    # The Mako creator.
    mako_class = Mako

    @cached_property
    def mako(self):
        return self.mako_class.factory(self.app, 'mako')

    def render_template(self, _filename, **context):
        return self.mako.render_template(self, _filename, **context)

    def render_response(self, _filename, **context):
        return self.mako.render_response(self, _filename, **context)

########NEW FILE########
__FILENAME__ = fields
# -*- coding: utf-8 -*-
"""
    tipfyext.wtforms.fields
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Form fields.

    :copyright: 2011 WTForms authors.
    :copyright: 2011 tipfy.org.
    :copyright: 2009 Plurk Inc.
    :license: BSD, see LICENSE.txt for more details.
"""
from wtforms.fields import (BooleanField, DecimalField, DateField,
    DateTimeField, Field, FieldList, FloatField, FormField, HiddenField,
    IntegerField, PasswordField, RadioField, SelectField, SelectMultipleField,
    SubmitField, TextField, TextAreaField)

from tipfyext.wtforms import widgets
from tipfyext.wtforms import validators


class CsrfTokenField(HiddenField):
    def __init__(self, *args, **kwargs):
        super(CsrfTokenField, self).__init__(*args, **kwargs)
        self.csrf_token = None
        self.type = 'HiddenField'

    def process_formdata(self, valuelist):
        """
        Process data received over the wire from a form.

        This will be called during form construction with data supplied
        through the `formdata` argument.

        :param valuelist: A list of strings to process.
        """
        if valuelist:
            self.csrf_token = valuelist[0]


class FileField(TextField):
    widget = widgets.FileInput()

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = valuelist[0]
        else:
            self.data = u''

    def _value(self):
        return u''


class RecaptchaField(Field):
    widget = widgets.RecaptchaWidget()

    #: Set if validation fails.
    recaptcha_error = None

    def __init__(self, *args, **kwargs):
        kwargs['validators'] = [validators.Recaptcha()]
        super(RecaptchaField, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = form
# -*- coding: utf-8 -*-
"""
    tipfyext.wtforms.form
    ~~~~~~~~~~~~~~~~~~~~~~

    Form object.

    :copyright: 2011 tipfy.org.
    :copyright: 2011 WTForms authors.
    :license: BSD, see LICENSE.txt for more details.
"""
import uuid

from wtforms import Form as BaseForm

from tipfy import Request, current_handler
from tipfyext.wtforms.fields import FileField, CsrfTokenField
from tipfyext.wtforms.validators import CsrfToken

try:
    from tipfy import i18n
except ImportError, e:
    i18n = None


class Form(BaseForm):
    csrf_protection = False
    csrf_token = CsrfTokenField()

    def __init__(self, *args, **kwargs):
        self.csrf_protection_enabled = kwargs.pop('csrf_protection',
            self.csrf_protection)

        super(Form, self).__init__(*args, **kwargs)

    def process(self, formdata=None, obj=None, **kwargs):
        """
        Take form, object data, and keyword arg input and have the fields
        process them.

        :param formdata:
            A :class:`tipfy.app.Request` object or a multidict of form data coming
            from the enduser, usually `request.form` or equivalent.
        :param obj:
            If `formdata` has no data for a field, the form will try to get it
            from the passed object.
        :param `**kwargs`:
            If neither `formdata` or `obj` contains a value for a field, the
            form will assign the value of a matching keyword argument to the
            field, if provided.
        """
        if not self.csrf_protection_enabled:
            self._fields.pop('csrf_token', None)

        if isinstance(formdata, Request):
            request = formdata
            filedata = request.files
            formdata = request.form

            if self.csrf_protection_enabled:
                kwargs['csrf_token'] = self._get_csrf_token(request)
        else:
            if self.csrf_protection_enabled:
                raise TypeError('You must pass a request object to the form '
                    'to use CSRF protection')

            filedata = None
            if formdata is not None and not hasattr(formdata, 'getlist'):
                raise TypeError("formdata should be a multidict-type wrapper "
                    "that supports the 'getlist' method")

        for name, field, in self._fields.iteritems():
            if isinstance(field, FileField):
                data = filedata
            else:
                data = formdata

            if obj is not None and hasattr(obj, name):
                field.process(data, getattr(obj, name))
            elif name in kwargs:
                field.process(data, kwargs[name])
            else:
                field.process(data)

    def _get_session(self):
        return current_handler.session_store.get_session()

    def _get_csrf_token(self, request):
        token = str(uuid.uuid4())
        token_list = self._get_session().setdefault('_csrf_token', [])
        token_list.append(token)
        # Store a maximum number of tokens.
        maximum_tokens = current_handler.get_config('tipfyext.wtforms',
            'csrf_tokens')
        while len(token_list) > maximum_tokens:
            token_list.pop(0)

        # Set the validation rule for the tokens.
        self._fields['csrf_token'].validators = [CsrfToken(token_list)]
        return token

    def _get_translations(self):
        """
        Override in subclasses to provide alternate translations factory.

        Must return an object that provides gettext() and ngettext() methods.
        """
        if i18n:
            return current_handler.i18n
        else:
            return None

########NEW FILE########
__FILENAME__ = validators
# -*- coding: utf-8 -*-
"""
    tipfyext.wtforms.validators
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Form validators.

    :copyright: 2011 WTForms authors.
    :copyright: 2011 tipfy.org.
    :copyright: 2009 Plurk Inc.
    :license: BSD, see LICENSE.txt for more details.
"""
from google.appengine.api import urlfetch

from werkzeug import url_encode

from wtforms.validators import *
from wtforms.validators import ValidationError

from tipfy import current_handler


RECAPTCHA_VERIFY_SERVER = 'http://api-verify.recaptcha.net/verify'


class CsrfToken(object):
    """
    Compares the incoming data to a sequence of valid inputs.

    :param values:
        A sequence of valid inputs.
    :param message:
        Error message to raise in case of a validation error.
    """
    def __init__(self, values, message=None):
        self.values = values
        self.message = message

    def __call__(self, form, field):
        if field.csrf_token:
            if field.csrf_token not in self.values:
                if self.message is None:
                    #self.message = field.gettext(u'The form expired.')
                    self.message = 'The form expired.'

                raise ValueError(self.message)
            else:
                self.values.remove(field.csrf_token)


class Recaptcha(object):
    """Validates a ReCaptcha."""
    _error_codes = {
        'invalid-site-public-key': 'The public key for reCAPTCHA is invalid',
        'invalid-site-private-key': 'The private key for reCAPTCHA is invalid',
        'invalid-referrer': 'The public key for reCAPTCHA is not valid for '
            'this domainin',
        'verify-params-incorrect': 'The parameters passed to reCAPTCHA '
            'verification are incorrect',
    }

    def __init__(self, message=u'Invalid word. Please try again.'):
        self.message = message

    def __call__(self, form, field):
        request = current_handler.request
        challenge = request.form.get('recaptcha_challenge_field', '')
        response = request.form.get('recaptcha_response_field', '')
        remote_ip = request.remote_addr

        if not challenge or not response:
            raise ValidationError('This field is required.')

        if not self._validate_recaptcha(challenge, response, remote_ip):
            field.recaptcha_error = 'incorrect-captcha-sol'
            raise ValidationError(self.message)

    def _validate_recaptcha(self, challenge, response, remote_addr):
        """Performs the actual validation."""
        private_key = current_handler.get_config('tipfyext.wtforms',
            'recaptcha_private_key')
        result = urlfetch.fetch(url=RECAPTCHA_VERIFY_SERVER,
            method=urlfetch.POST,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            payload=url_encode({
                'privatekey': private_key,
                'remoteip':   remote_addr,
                'challenge':  challenge,
                'response':   response
            }))

        if result.status_code != 200:
            return False

        rv = [l.strip() for l in result.content.splitlines()]

        if rv and rv[0] == 'true':
            return True

        if len(rv) > 1:
            error = rv[1]
            if error in self._error_codes:
                raise RuntimeError(self._error_codes[error])

        return False

########NEW FILE########
__FILENAME__ = widgets
# -*- coding: utf-8 -*-
"""
    tipfyext.wtforms.widgets
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Form widgets.

    :copyright: 2011 WTForms authors.
    :copyright: 2011 tipfy.org.
    :copyright: 2009 Plurk Inc.
    :license: BSD, see LICENSE.txt for more details.
"""
from werkzeug import url_encode

from wtforms.widgets import *

from tipfy import current_handler
from tipfy.i18n import _
from tipfy.utils import json_encode


RECAPTCHA_API_SERVER = 'http://api.recaptcha.net/'
RECAPTCHA_SSL_API_SERVER = 'https://api-secure.recaptcha.net/'
RECAPTCHA_HTML = u'''
<script type="text/javascript">var RecaptchaOptions = %(options)s;</script>
<script type="text/javascript" src="%(script_url)s"></script>
<noscript>
  <div><iframe src="%(frame_url)s" height="300" width="500"></iframe></div>
  <div><textarea name="recaptcha_challenge_field" rows="3" cols="40"></textarea>
  <input type="hidden" name="recaptcha_response_field" value="manual_challenge"></div>
</noscript>
'''

class RecaptchaWidget(object):
    def __call__(self, field, error=None, **kwargs):
        """Returns the recaptcha input HTML."""
        config = current_handler.get_config('tipfyext.wtforms')
        if config.get('recaptcha_use_ssl'):
            server = RECAPTCHA_SSL_API_SERVER
        else:
            server = RECAPTCHA_API_SERVER

        query_options = dict(k=config.get('recaptcha_public_key'))

        if field.recaptcha_error is not None:
            query_options['error'] = unicode(field.recaptcha_error)

        query = url_encode(query_options)

        # Widget default options.
        options = {
            'theme': 'clean',
            'custom_translations': {
                'visual_challenge':    _('Get a visual challenge'),
                'audio_challenge':     _('Get an audio challenge'),
                'refresh_btn':         _('Get a new challenge'),
                'instructions_visual': _('Type the two words:'),
                'instructions_audio':  _('Type what you hear:'),
                'help_btn':            _('Help'),
                'play_again':          _('Play sound again'),
                'cant_hear_this':      _('Download sound as MP3'),
                'incorrect_try_again': _('Incorrect. Try again.'),
            }
        }
        custom_options = config.get('recaptcha_options')
        if custom_options:
            options.update(custom_options)

        return RECAPTCHA_HTML % dict(
            script_url='%schallenge?%s' % (server, query),
            frame_url='%snoscript?%s' % (server, query),
            options=json_encode(options)
        )

########NEW FILE########
