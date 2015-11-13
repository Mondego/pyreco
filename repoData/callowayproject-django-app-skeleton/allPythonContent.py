__FILENAME__ = create_pkg
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ConfigParser
import os
import random
import sys
import subprocess

import platform


IS_WINDOWS = False
win32api = None
if platform.system() == 'Windows':
    IS_WINDOWS = True
    try:
        import win32api
    except (ImportError, ):
        pass


CONFIG_FILE = os.path.expanduser('~/.djas')
CHARS = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
BLACKLIST = (
    'jquery',
    '.tar.gz',
    'admin/css',
    'admin/img',
    'admin/js',
    '.git/',
    '.svn',
    '.hg',
    '.DS_Store',
)


def write_config(config):
    """Writes the config to a file"""
    with open(CONFIG_FILE, 'wb') as conf:
        config.write(conf)


def get_config_value(config, sec, opt, default):
    """Get a config value.

    If the value was not found, write out the default value to the config.

    """
    try:
        return config.get(sec, opt)
    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
        # Ensure the config has the `main` section
        if not config.has_section('main'):
            config.add_section('main')
        config.set(sec, opt, default)
        write_config(config)
        return default


def set_config_value(sec, opt, value):
    """Set a config value.

    Only sets the value if the value is not founc of empty.

    """
    config = ConfigParser.RawConfigParser()
    config.read(CONFIG_FILE)

    if not config.has_option(sec, opt):
        config.set(sec, opt, value)
    elif config.get(sec, opt) == '':
        config.set(sec, opt, value)
    write_config(config)


def get_config():
    """Gets the configuration file, creates one if it does not exist"""

    defaults = (
        ('author', 'PKG_AUTHOR', ''),
        ('author_email', 'PKG_AUTHOR_EMAIL', ''),
        ('destintation_dir', 'DEST_DIR',  os.getcwd()),
        ('template_dir', 'TMPL_DIR', os.path.abspath(
            os.path.join(os.path.dirname(__file__), 'skel'))),
        ('use_venv', 'USE_VENV', 'n'),
    )

    config = ConfigParser.RawConfigParser()

    if not config.read(CONFIG_FILE):
        config.add_section('main')
        for default in defaults:
            key, var, value = default
            config.set('main', key, value)
        write_config(config)

    return dict([
        (default[1], get_config_value(
            config, 'main', default[0], default[2])) for default in defaults])


def ensure_venv():
    """Ensure virtualenv and virtuelenv wrapper is installed"""
    has_venv = bool(subprocess.Popen(
        ['which', 'virtualenv'],
        stdout=subprocess.PIPE).communicate()[0])

    if not has_venv:
        print 'virtualenv is required to run this script. Please install it ' \
              'with\n  easy_install virtualenv\n\nor\n\n  pip virtualenv'
        sys.exit(1)

    has_venv_wrapper = bool(subprocess.Popen(
        ['which', 'virtualenvwrapper.sh'],
        stdout=subprocess.PIPE).communicate()[0])

    if not has_venv_wrapper:
        print 'virtualenvwrapper is required to run this script. Please' \
              'install it with\n  easy_install virtualenvwrapper\n\nor\n\n' \
              'pip virtualenvwrapper'
        sys.exit(1)


def mk_virtual_env(name, dest):
    """Creates a virtualenv using virtualenv wrapper"""
    print 'Making the virtual environment (%s)...' % name
    create_env_cmds = [
        'source virtualenvwrapper.sh',
        'cd %s' % dest,
        'mkvirtualenv --no-site-packages --distribute %s' % name,
        'easy_install pip'
    ]
    create_pa_cmd = [
        'source virtualenvwrapper.sh',
        'cat > $WORKON_HOME/%s/bin/postactivate'\
        '<<END\n#!/bin/bash/\ncd %s\nEND\n'\
        'chmod +x $WORKON_HOME/%s/bin/postactivate' % (name,
                                                       dest,
                                                       name)
    ]
    subprocess.call([';'.join(create_env_cmds)], env=os.environ,
                    executable='/bin/bash', shell=True)
    subprocess.call([';'.join(create_pa_cmd)], env=os.environ,
                    executable='/bin/bash', shell=True)

    print 'Virtualenv created, type workon %s' % name


def replace(opts, text):
    """Replace certain strings will the supplied text

    `opts` is a dictionary of variables that will be replaced. Similar to
    django, it will look for {{..}} and replace it with the variable value

    Since we want to maintance compatibility with django's `startapp` command
    we need to also replaced `app_name` folders with the supplied value.

    """
    if IS_WINDOWS:
        text = text.replace('\\app_name', '\\{0}'.format(opts['APP_NAME']))
        text = text.replace('\\gitignore', '\\.gitignore')
    else:
        text = text.replace('/app_name', '/{0}'.format(opts['APP_NAME']))
        text = text.replace('/gitignore', '/.gitignore')

    for key, value in opts.iteritems():
        if not value:
            continue
        text = text.replace('{{%s}}' % (key.lower(),), value)
    return text


def mk_pkg(opts, dest, templ_dir):
    """Creates the package file/folder structure"""
    try:
        os.makedirs(dest)
    except OSError:
        pass

    for root, dirs, files in os.walk(templ_dir):
        for filename in files:
            source_fn = os.path.join(root, filename)

            dest_fn = replace(opts, os.path.join(
                dest, root.replace(templ_dir, ''), replace(opts, filename)))

            try:
                os.makedirs(os.path.dirname(dest_fn))
            except OSError:
                pass

            print 'Copying %s to %s' % (source_fn, dest_fn)
            should_replace = True
            for bl_item in BLACKLIST:
                if bl_item in dest_fn:
                    should_replace = False
            data = open(source_fn, 'r').read()
            if should_replace:
                data = replace(opts, data)
            open(dest_fn, 'w').write(data)
            os.chmod(dest_fn, os.stat(source_fn)[0])
    print 'Package created'


def main(options):
    config = get_config()

    cur_user = ''
    if IS_WINDOWS and win32api:
        cur_user = win32api.GetUserName()
    elif not IS_WINDOWS:
        cur_user = os.getlogin()

    # Default options
    opts = {
        'APP_NAME': None,
        'PKG_NAME': None,
        'PKG_AUTHOR': None,
        'PKG_AUTHOR_EMAIL': None,
        'PKG_URL': None,
        'VENV': None,
        'SECRET_KEY': ''.join([random.choice(CHARS) for i in xrange(50)]),
        'DEST_DIR': None,
        'TMPL_DIR': None,
        'USE_VENV': None
    }

    # Update the default options wiht the config values
    opts.update(config)

    def prompt(attr, text, default=None):
        """Prompt the user for certain values"""
        if hasattr(options, attr):
            if getattr(options, attr):
                return getattr(options, attr)

        default_text = default and ' [%s]: ' % default or ': '
        new_val = None
        while not new_val:
            new_val = raw_input(text + default_text) or default
        return new_val

    # Package/App Information
    opts['PKG_NAME'] = prompt('pkg_name', 'Package Name')
    opts['APP_NAME'] = prompt(
        'app_name', 'App Name', opts['PKG_NAME'].replace('django-', ''))
    opts['PKG_URL'] = prompt('pkg_url', 'Project URL')

    # Author Information
    opts['PKG_AUTHOR'] = prompt(
        'pkg_author', 'Author Name', opts['PKG_AUTHOR'] or cur_user)
    opts['PKG_AUTHOR_EMAIL'] = prompt(
        'pkg_author_email', 'Author Email', opts['PKG_AUTHOR_EMAIL'])

    set_config_value('main', 'author', opts['PKG_AUTHOR'])
    set_config_value('main', 'author_email', opts['PKG_AUTHOR_EMAIL'])

    # Destination and template directories
    opts['DEST_DIR'] = prompt(
        'destination', 'Destination DIR', opts['DEST_DIR'])
    opts['DEST_DIR'] = os.path.join(opts['DEST_DIR'], opts['PKG_NAME'])

    opts['TMPL_DIR'] = prompt('template', 'Template DIR', opts['TMPL_DIR'])

    tmpl_dir = os.path.realpath(os.path.expanduser(opts['TMPL_DIR']))
    if tmpl_dir[-1] != '/':
        tmpl_dir = tmpl_dir + "/"
    opts['TMPL_DIR'] = tmpl_dir

    # Copy the template and replace the proper values
    mk_pkg(opts, opts['DEST_DIR'], opts['TMPL_DIR'])

    # Virtualenv
    opts['USE_VENV'] = prompt('use_venv', 'Use Virtualenv', 'n')
    if opts['USE_VENV'].lower() in ['y', 'yes', '1']:
        opts['VENV'] = prompt('venv', 'Virtualenv Name', opts['PKG_NAME'])
        mk_virtual_env(opts['VENV'], opts['DEST_DIR'])


if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('-a', '--author', dest='pkg_author',
                      help='The name of the author.')
    parser.add_option('-e', '--author-email', dest='pkg_author_email',
                      help='The email of the author.')
    parser.add_option('-u', '--url', dest='pkg_url',
                      help='The URL of the project page.')
    parser.add_option('-n', '--name', dest='app_name',
                      help='The name of the application, i.e. django-myapp')
    parser.add_option('-p', '--package', dest='pkg_name',
                      help='The name of the installed package, i.e. myapp')
    parser.add_option('-v', '--virtenv', dest='venv',
                      help='The name of the virtualenv.')
    parser.add_option('-d', '--dest', dest='destination',
                      help='Where to put the new application.')
    parser.add_option('-t', '--template', dest='template',
                      help='The application template to use as a basis for '\
                           'the new application.')
    parser.add_option('-i', '--use-venv', dest='use_venv',
                      help='Wheater or not to create the virtuelenv')
    (options, args) = parser.parse_args()

    sys.exit(main(options))

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-
from django.contrib import admin

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
from django import forms

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings as site_settings
from django.utils.translation import ugettext, ugettext_lazy as _

from {{app_name}} import settings

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
from django.conf import settings as site_settings


DEFAULT_SETTINGS = {

}

USER_SETTINGS = DEFAULT_SETTINGS.copy()
USER_SETTINGS.update(getattr(site_settings, '{{app_name}}_SETTINGS', {}))

globals().update(USER_SETTINGS)

########NEW FILE########
__FILENAME__ = app_name_tags
# -*- coding: utf-8 -*-
from django import template

register = template.Library()

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from django.test import TestCase


class {{app_name}}Test(TestCase):
    """
    Tests for {{app_name}}
    """
    def test_{{app_name}}(self):
        pass

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('',
    url(r'^$', 'views.index', name='index'),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache, cache_page
from django.views.decorators.http import require_http_methods

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# app documentation build configuration file, created by
# sphinx-quickstart on Wed Oct 21 13:18:22 2009.
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
sys.path.append(os.path.abspath('..'))
import {{app_name}}
os.environ['DJANGO_SETTINGS_MODULE'] = 'example.settings'

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'{{pkg_name}}'
copyright = u'2013, {{pkg_author}}'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = {{app_name}}.get_version(short=True)
# The full version, including alpha/beta/rc tags.
release = {{app_name}}.get_version()

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
exclude_trees = ['_build']

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

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = '{{pkg_name}}doc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'app.tex', u'{{pkg_name}} Documentation',
   u'{{pkg_author}}', 'manual'),
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
# -*- coding: utf-8 -*-
# Django settings for example project.
import os
import sys


DEBUG = True
TEMPLATE_DEBUG = DEBUG

APP = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
PROJ_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.append(APP)

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'dev.db',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

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

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.abspath(os.path.join(PROJ_ROOT, 'media', 'uploads'))

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/uploads/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.abspath(os.path.join(PROJ_ROOT, 'media', 'static'))

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)


# Make this unique, and don't share it with anybody.
SECRET_KEY = '{{secret_key}}'

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
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'example.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'example.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or
    # "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJ_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.admin',
    # 'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    '{{app_name}}',
    'simpleapp',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    # 'filters': {
    #     'require_debug_false': {
    #         '()': 'django.utils.log.RequireDebugFalse'
    #     }
    # },
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

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import SimpleModel


class SimpleModelAdmin(admin.ModelAdmin):
    list_display = ('name', )
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

admin.site.register(SimpleModel, SimpleModelAdmin)

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models


class SimpleModel(models.Model):
    """
    (SimpleModel description)
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('simplemodel_detail_view_name', [str(self.id)])

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls.defaults import url, patterns

from .models import SimpleModel


urlpatterns = patterns('django.views.generic.list_detail',
    url(r'^$',
        'object_list',
        {'queryset': SimpleModel.objects.all()},
        name="simplemodel_list"
    ),
    url(r'^(?P<slug>[\w-]+)/',
        'object_detail',
        {'queryset': SimpleModel.objects.all()},
        name='simplemode_detail',
    ),
)

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, include, url
from django.conf import settings

from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'example.views.home', name='home'),
    # url(r'^example/', include('example.foo.urls')),

    url(r'^admin/', include(admin.site.urls)),
    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
)

urlpatterns = urlpatterns + patterns('',
    (r'^static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT}),
    ) if settings.DEBUG else urlpatterns

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for newproj project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
