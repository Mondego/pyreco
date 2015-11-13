__FILENAME__ = gen-crons
#!/usr/bin/env python
import os
from optparse import OptionParser

from jinja2 import Template


HEADER = '!!AUTO-GENERATED!! Edit bin/crontab/crontab.tpl instead.'
TEMPLATE = open(os.path.join(os.path.dirname(__file__), 'crontab.tpl')).read()


def main():
    parser = OptionParser()
    parser.add_option('-w', '--webapp',
                      help='Location of web app (required)')
    parser.add_option('-u', '--user',
                      help=('Prefix cron with this user. '
                            'Only define for cron.d style crontabs.'))
    parser.add_option('-p', '--python', default='/usr/bin/python2.6',
                      help='Python interpreter to use.')

    (opts, args) = parser.parse_args()

    if not opts.webapp:
        parser.error('-w must be defined')

    ctx = {'django': 'cd %s; %s manage.py' % (opts.webapp, opts.python)}
    ctx['cron'] = '%s cron' % ctx['django']

    if opts.user:
        for k, v in ctx.iteritems():
            ctx[k] = '%s %s' % (opts.user, v)

    # Needs to stay below the opts.user injection.
    ctx['python'] = opts.python
    ctx['header'] = HEADER

    print Template(TEMPLATE).render(**ctx)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = deploy
"""
Deploy this project in dev/stage/production.

Requires commander_ which is installed on the systems that need it.

.. _commander: https://github.com/oremj/commander
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from commander.deploy import task, hostgroups
import commander_settings as settings


@task
def update_code(ctx, tag):
    """Update the code to a specific git reference (tag/sha/etc)."""
    with ctx.lcd(settings.SRC_DIR):
        ctx.local('git fetch')
        ctx.local('git checkout -f %s' % tag)
        ctx.local('git submodule sync')
        ctx.local('git submodule update --init --recursive')


@task
def update_locales(ctx):
    """Update a locale directory from SVN.

    Assumes localizations 1) exist, 2) are in SVN, 3) are in SRC_DIR/locale and
    4) have a compile-mo.sh script. This should all be pretty standard, but
    change it if you need to.

    """
    with ctx.lcd(os.path.join(settings.SRC_DIR, 'locale')):
        ctx.local('svn up')
        ctx.local('./compile-mo.sh .')


@task
def update_assets(ctx):
    with ctx.lcd(settings.SRC_DIR):
        ctx.local("python2.6 manage.py collectstatic --noinput")
        # un-comment if you haven't moved to django-compressor yet
        ## LANG=en_US.UTF-8 is sometimes necessary for the YUICompressor.
        #ctx.local('LANG=en_US.UTF8 python2.6 manage.py compress_assets')


@task
def update_db(ctx):
    """Update the database schema, if necessary.

    Uses schematic by default. Change to south if you need to.

    """
    with ctx.lcd(settings.SRC_DIR):
        ctx.local('python2.6 ./vendor/src/schematic/schematic migrations')


@task
def install_cron(ctx):
    """Use gen-crons.py method to install new crontab.

    Ops will need to adjust this to put it in the right place.

    """
    with ctx.lcd(settings.SRC_DIR):
        ctx.local('python2.6 ./bin/crontab/gen-crons.py -w %s -u apache > '
                  '/etc/cron.d/.%' % (settings.WWW_DIR, settings.CRON_NAME))
        ctx.local('mv /etc/cron.d/.%s /etc/cron.d/%s' %
                  (settings.CRON_NAME,  settings.CRON_NAME))


@task
def checkin_changes(ctx):
    """Use the local, IT-written deploy script to check in changes."""
    ctx.local(settings.DEPLOY_SCRIPT)


@hostgroups(settings.WEB_HOSTGROUP, remote_kwargs={'ssh_key': settings.SSH_KEY})
def deploy_app(ctx):
    """Call the remote update script to push changes to webheads."""
    ctx.remote(settings.REMOTE_UPDATE_SCRIPT)
    ctx.remote('/bin/touch %s' % settings.REMOTE_WSGI)


@hostgroups(settings.CELERY_HOSTGROUP, remote_kwargs={'ssh_key': settings.SSH_KEY})
def update_celery(ctx):
    """Update and restart Celery."""
    ctx.remote(settings.REMOTE_UPDATE_SCRIPT)
    ctx.remote('/sbin/service %s restart' % settings.CELERY_SERVICE)


@task
def update_info(ctx):
    """Write info about the current state to a publicly visible file."""
    with ctx.lcd(settings.SRC_DIR):
        ctx.local('date')
        ctx.local('git branch')
        ctx.local('git log -3')
        ctx.local('git status')
        ctx.local('git submodule status')
        ctx.local('python2.6 ./vendor/src/schematic/schematic -v migrations/')
        with ctx.lcd('locale'):
            ctx.local('svn info')
            ctx.local('svn status')

        ctx.local('git rev-parse HEAD > media/revision.txt')


@task
def pre_update(ctx, ref=settings.UPDATE_REF):
    """Update code to pick up changes to this file."""
    update_code(ref)
    update_info()


@task
def update(ctx):
    update_assets()
    update_locales()
    update_db()


@task
def deploy(ctx):
    install_cron()
    checkin_changes()
    deploy_app()
    update_celery()


@task
def update_site(ctx, tag):
    """Update the app to prep for deployment."""
    pre_update(tag)
    update()

########NEW FILE########
__FILENAME__ = update_site
#!/usr/bin/env python
"""
Usage: update_site.py [options]
Updates a server's sources, vendor libraries, packages CSS/JS
assets, migrates the database, and other nifty deployment tasks.

Options:
  -h, --help            show this help message and exit
  -e ENVIRONMENT, --environment=ENVIRONMENT
                        Type of environment. One of (prod|dev|stage) Example:
                        update_site.py -e stage
  -v, --verbose         Echo actions before taking them.
"""

import os
import sys
from textwrap import dedent
from optparse import  OptionParser
from hashlib import md5

# Constants
PROJECT = 0
VENDOR  = 1

ENV_BRANCH = {
    # 'environment': [PROJECT_BRANCH, VENDOR_BRANCH],
    'dev':   ['base',   'master'],
    'stage': ['master', 'master'],
    'prod':  ['prod',   'master'],
}

# The URL of the SVN repository with the localization files (*.po). If you set
# it to a non-empty value, remember to `git rm --cached -r locale` in the root
# of the project.  Example:
# LOCALE_REPO_URL = 'https://svn.mozilla.org/projects/l10n-misc/trunk/playdoh/locale'
LOCALE_REPO_URL = ''

GIT_PULL = "git pull -q origin %(branch)s"
GIT_SUBMODULE = "git submodule update --init"
SVN_CO = "svn checkout --force %(url)s locale"
SVN_UP = "svn update"
COMPILE_MO = "./bin/compile-mo.sh %(localedir)s %(unique)s"

EXEC = 'exec'
CHDIR = 'chdir'


def update_site(env, debug):
    """Run through commands to update this site."""
    error_updating = False
    here = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    locale = os.path.join(here, 'locale')
    unique = md5(locale).hexdigest()
    project_branch = {'branch': ENV_BRANCH[env][PROJECT]}
    vendor_branch = {'branch': ENV_BRANCH[env][VENDOR]}

    commands = [
        (CHDIR, here),
        (EXEC,  GIT_PULL % project_branch),
        (EXEC,  GIT_SUBMODULE),
    ]

    # Checkout the locale repo into locale/ if the URL is known
    if LOCALE_REPO_URL and not os.path.exists(os.path.join(locale, '.svn')):
        commands += [
            (EXEC, SVN_CO % {'url': LOCALE_REPO_URL}),
            (EXEC, COMPILE_MO % {'localedir': locale, 'unique': unique}),
        ]

    # Update locale dir if applicable
    if os.path.exists(os.path.join(locale, '.svn')):
        commands += [
            (CHDIR, locale),
            (EXEC, SVN_UP),
            (CHDIR, here),
            (EXEC, COMPILE_MO % {'localedir': locale, 'unique': unique}),
        ]
    elif os.path.exists(os.path.join(locale, '.git')):
        commands += [
            (CHDIR, locale),
            (EXEC, GIT_PULL % 'master'),
            (CHDIR, here),
        ]

    commands += [
        (CHDIR, os.path.join(here, 'vendor')),
        (EXEC,  GIT_PULL % vendor_branch),
        (EXEC,  GIT_SUBMODULE),
        (CHDIR, os.path.join(here)),
        (EXEC, 'python2.6 vendor/src/schematic/schematic migrations/'),
        (EXEC, 'python2.6 manage.py collectstatic --noinput'),
        # un-comment if you haven't moved to django-compressor yet
        #(EXEC, 'python2.6 manage.py compress_assets'),
    ]

    for cmd, cmd_args in commands:
        if CHDIR == cmd:
            if debug:
                sys.stdout.write("cd %s\n" % cmd_args)
            os.chdir(cmd_args)
        elif EXEC == cmd:
            if debug:
                sys.stdout.write("%s\n" % cmd_args)
            if not 0 == os.system(cmd_args):
                error_updating = True
                break
        else:
            raise Exception("Unknown type of command %s" % cmd)

    if error_updating:
        sys.stderr.write("There was an error while updating. Please try again "
                         "later. Aborting.\n")


def main():
    """ Handels command line args. """
    debug = False
    usage = dedent("""\
        %prog [options]
        Updates a server's sources, vendor libraries, packages CSS/JS
        assets, migrates the database, and other nifty deployment tasks.
        """.rstrip())

    options = OptionParser(usage=usage)
    e_help = "Type of environment. One of (%s) Example: update_site.py \
        -e stage" % '|'.join(ENV_BRANCH.keys())
    options.add_option("-e", "--environment", help=e_help)
    options.add_option("-v", "--verbose",
                       help="Echo actions before taking them.",
                       action="store_true", dest="verbose")
    (opts, _) = options.parse_args()

    if opts.verbose:
        debug = True
    if opts.environment in ENV_BRANCH.keys():
        update_site(opts.environment, debug)
    else:
        sys.stderr.write("Invalid environment!\n")
        options.print_help(sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# playdoh documentation build configuration file, created by
# sphinx-quickstart on Tue Jan  4 15:11:09 2011.
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
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.intersphinx', 'sphinx.ext.todo', 'sphinx.ext.coverage']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'a playdoh-based project'
copyright = u'2012, the authors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.0'
# The full version, including alpha/beta/rc tags.
release = '1.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

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
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

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
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

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

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'playdohdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'playdoh.tex', u'playdoh Documentation',
   u'Mozilla', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'a-playdoh-app', u"a-playdoh-app's Documentation",
     [u'the authors'], 1)
]


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

# Edit this if necessary or override the variable in your environment.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

# Add a temporary path so that we can import the funfactory
tmp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'vendor', 'src', 'funfactory')
# Comment out to load funfactory from your site packages instead
sys.path.insert(0, tmp_path)

from funfactory import manage

# Let the path magic happen in setup_environ() !
sys.path.remove(tmp_path)


manage.setup_environ(__file__, more_pythonic=True)

if __name__ == "__main__":
    manage.main()

########NEW FILE########
__FILENAME__ = schematic_settings
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up playdoh.
import manage
from django.conf import settings

config = settings.DATABASES['default']
config['HOST'] = config.get('HOST', 'localhost')
config['PORT'] = config.get('PORT', '3306')

if not config['HOST'] or config['HOST'].endswith('.sock'):
    """Oh, you meant 'localhost'!"""
    config['HOST'] = 'localhost'

s = 'mysql --silent {NAME} -h{HOST} -u{USER}'

if config['PASSWORD']:
    s += ' -p{PASSWORD}'
else:
    del config['PASSWORD']
if config['PORT']:
    s += ' -P{PORT}'
else:
    del config['PORT']

db = s.format(**config)
table = 'schema_version'

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = models
from django.contrib.auth.models import User


# User class extensions
def user_unicode(self):
    """Use email address for string representation of user."""
    return self.email
User.add_to_class('__unicode__', user_unicode)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from . import views


urlpatterns = patterns('',
    url(r'^$', views.home, name='examples.home'),
    url(r'^browserid/', include('django_browserid.urls')),
    url(r'^logout/?$', 'django.contrib.auth.views.logout', {'next_page': '/'},
        name='examples.logout'),
    url(r'^bleach/?$', views.bleach_test, name='examples.bleach'),
)

########NEW FILE########
__FILENAME__ = views
"""Example views. Feel free to delete this app."""

import logging

from django.shortcuts import render

import bleach
import commonware
from funfactory.log import log_cef
from mobility.decorators import mobile_template
from session_csrf import anonymous_csrf


log = commonware.log.getLogger('playdoh')


@mobile_template('examples/{mobile/}home.html')
def home(request, template=None):
    """Main example view."""
    data = {}  # You'd add data here that you're sending to the template.
    log.debug("I'm alive!")
    return render(request, template, data)


@anonymous_csrf
def bleach_test(request):
    """A view outlining bleach's HTML sanitization."""
    allowed_tags = ('strong', 'em')

    data = {}

    if request.method == 'POST':
        bleachme = request.POST.get('bleachme', None)
        data['bleachme'] = bleachme
        if bleachme:
            data['bleached'] = bleach.clean(bleachme, tags=allowed_tags)

        # CEF logging: Log user input that needed to be "bleached".
        if data['bleached'] != bleachme:
            log_cef('Bleach Alert', logging.INFO, request,
                    username='anonymous', signature='BLEACHED',
                    msg='User data needed to be bleached: %s' % bleachme)

    return render(request, 'examples/bleach.html', data)

########NEW FILE########
__FILENAME__ = base
# This is your project's main settings file that can be committed to your
# repo. If you need to override a setting locally, use settings_local.py

from funfactory.settings_base import *

# Name of the top-level module where you put all your apps.
# If you did not install Playdoh with the funfactory installer script
# you may need to edit this value. See the docs about installing from a
# clone.
PROJECT_MODULE = 'project'

# Defines the views served for root URLs.
ROOT_URLCONF = '%s.urls' % PROJECT_MODULE

INSTALLED_APPS = list(INSTALLED_APPS) + [
    # Application base, containing global templates.
    '%s.base' % PROJECT_MODULE,
    # Example code. Can (and should) be removed for actual projects.
    '%s.examples' % PROJECT_MODULE,
]

# Note! If you intend to add `south` to INSTALLED_APPS,
# make sure it comes BEFORE `django_nose`.
#INSTALLED_APPS.remove('django_nose')
#INSTALLED_APPS.append('django_nose')


LOCALE_PATHS = (
    os.path.join(ROOT, PROJECT_MODULE, 'locale'),
)

# Because Jinja2 is the default template loader, add any non-Jinja templated
# apps here:
JINGO_EXCLUDE_APPS = (
    'admin',
    'registration',
    'browserid',
)

# BrowserID configuration
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'django_browserid.auth.BrowserIDBackend',
)

LOGIN_URL = '/'
LOGIN_REDIRECT_URL = '/'
LOGIN_REDIRECT_URL_FAILURE = '/'

TEMPLATE_CONTEXT_PROCESSORS += (
    # other possible context processors here...
)

# Should robots.txt deny everything or disallow a calculated list of URLs we
# don't want to be crawled?  Default is false, disallow everything.
# Also see http://www.google.com/support/webmasters/bin/answer.py?answer=93710
ENGAGE_ROBOTS = False

# Always generate a CSRF token for anonymous users.
ANON_ALWAYS = True

# Tells the extract script what files to look for L10n in and what function
# handles the extraction. The Tower library expects this.
DOMAIN_METHODS['messages'] = [
    ('%s/**.py' % PROJECT_MODULE,
        'tower.management.commands.extract.extract_tower_python'),
    ('%s/**/templates/**.html' % PROJECT_MODULE,
        'tower.management.commands.extract.extract_tower_template'),
    ('templates/**.html',
        'tower.management.commands.extract.extract_tower_template'),
]

# # Use this if you have localizable HTML files:
# DOMAIN_METHODS['lhtml'] = [
#    ('**/templates/**.lhtml',
#        'tower.management.commands.extract.extract_tower_template'),
# ]

# # Use this if you have localizable JS files:
# DOMAIN_METHODS['javascript'] = [
#    # Make sure that this won't pull in strings from external libraries you
#    # may use.
#    ('media/js/**.js', 'javascript'),
# ]

LOGGING = {
    'loggers': {
        'playdoh': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'django_browserid': {
            'handlers': ['console'],
            'level': 'DEBUG',
        }
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls.defaults import patterns, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from .examples import urls

from funfactory.monkeypatches import patch
patch()

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    (r'', include(urls)),
    (r'^browserid/', include('django_browserid.urls')),

    # Generate a robots.txt
    (r'^robots\.txt$',
        lambda r: HttpResponse(
            "User-agent: *\n%s: /" % 'Allow' if settings.ENGAGE_ROBOTS else 'Disallow' ,
            mimetype="text/plain"
        )
    )

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)

## In DEBUG mode, serve media files through Django.
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()

########NEW FILE########
__FILENAME__ = settings_test
# These settings will always be overriding for all test runs

# this bypasses bcrypt to speed up test fixtures
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

########NEW FILE########
