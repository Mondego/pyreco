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

import os
import shutil
import sys
import tempfile

from optparse import OptionParser

tmpeggs = tempfile.mkdtemp()

usage = '''\
[DESIRED PYTHON FOR BUILDOUT] bootstrap.py [options]

Bootstraps a buildout-based project.

Simply run this script in a directory containing a buildout.cfg, using the
Python that you want bin/buildout to use.

Note that by using --find-links to point to local resources, you can keep 
this script from going over the network.
'''

parser = OptionParser(usage=usage)
parser.add_option("-v", "--version", help="use a specific zc.buildout version")

parser.add_option("-t", "--accept-buildout-test-releases",
                  dest='accept_buildout_test_releases',
                  action="store_true", default=False,
                  help=("Normally, if you do not specify a --version, the "
                        "bootstrap script and buildout gets the newest "
                        "*final* versions of zc.buildout and its recipes and "
                        "extensions for you.  If you use this flag, "
                        "bootstrap and buildout will get the newest releases "
                        "even if they are alphas or betas."))
parser.add_option("-c", "--config-file",
                  help=("Specify the path to the buildout configuration "
                        "file to be used."))
parser.add_option("-f", "--find-links",
                  help=("Specify a URL to search for buildout releases"))


options, args = parser.parse_args()

######################################################################
# load/install setuptools

to_reload = False
try:
    import pkg_resources
    import setuptools
except ImportError:
    ez = {}

    try:
        from urllib.request import urlopen
    except ImportError:
        from urllib2 import urlopen

    # XXX use a more permanent ez_setup.py URL when available.
    exec(urlopen('https://bitbucket.org/pypa/setuptools/raw/0.7.2/ez_setup.py'
                ).read(), ez)
    setup_args = dict(to_dir=tmpeggs, download_delay=0)
    ez['use_setuptools'](**setup_args)

    if to_reload:
        reload(pkg_resources)
    import pkg_resources
    # This does not (always?) update the default working set.  We will
    # do it.
    for path in sys.path:
        if path not in pkg_resources.working_set.entries:
            pkg_resources.working_set.add_entry(path)

######################################################################
# Install buildout

ws = pkg_resources.working_set

cmd = [sys.executable, '-c',
       'from setuptools.command.easy_install import main; main()',
       '-mZqNxd', tmpeggs]

find_links = os.environ.get(
    'bootstrap-testing-find-links',
    options.find_links or
    ('http://downloads.buildout.org/'
     if options.accept_buildout_test_releases else None)
    )
if find_links:
    cmd.extend(['-f', find_links])

setuptools_path = ws.find(
    pkg_resources.Requirement.parse('setuptools')).location

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
        search_path=[setuptools_path])
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

import subprocess
if subprocess.call(cmd, env=dict(os.environ, PYTHONPATH=setuptools_path)) != 0:
    raise Exception(
        "Failed to execute command:\n%s",
        repr(cmd)[1:-1])

######################################################################
# Import and run buildout

ws.add_entry(tmpeggs)
ws.require(requirement)
import zc.buildout.buildout

if not [a for a in args if '=' not in a]:
    args.append('bootstrap')

# if -c was provided, we push it back into args for buildout' main function
if options.config_file is not None:
    args[0:0] = ['-c', options.config_file]

zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = boilerplate
script_template = {
    'wsgi': """

%(relative_paths_setup)s
import sys
sys.path[0:0] = [
  %(path)s,
  ]
%(initialization)s
import %(module_name)s

application = %(module_name)s.%(attrs)s(%(arguments)s)
""",
}

production_settings = """
from %(project)s.settings import *
"""

development_settings = """
from %(project)s.settings import *
DEBUG=True
TEMPLATE_DEBUG=DEBUG
"""

urls_template = """
from django.conf.urls.defaults import *
from django.conf import settings

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^{{ project_name }}/', include('{{ project_name }}.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT}),
    )

"""

settings_template_1_2 = """
# Django settings for %(project)s project.

import os

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
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
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '%(secret)s'

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
)

ROOT_URLCONF = '%(urlconf)s'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.

    # Generic way to add templates paths.
    os.path.join(os.path.dirname(__file__), "templates"),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)
"""

settings_template_1_3 = """
# Django settings for %(project)s project.

import os

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
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
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

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
SECRET_KEY = '%(secret)s'

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
)

ROOT_URLCONF = '%(urlconf)s'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(os.path.dirname(__file__), "templates"),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
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
"""

versions = {
    '1.2': {
        'settings': settings_template_1_2,
        'urls': urls_template,
        'production_settings': production_settings,
        'development_settings': development_settings,
        },
    '1.3': {
        'settings': settings_template_1_3,
        'urls': urls_template,
        'production_settings': production_settings,
        'development_settings': development_settings,
        },
    }

# Easy way to specify the newest Django version.
versions['Newest'] = versions['1.3']

########NEW FILE########
__FILENAME__ = manage
import os
import sys

from django.core import management


def main(settings_file):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_file)
    management.execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = recipe
from random import choice
import os
import logging
import re
import sys

from zc.buildout import UserError
import zc.recipe.egg

from djangorecipe.boilerplate import script_template, versions


class Recipe(object):
    def __init__(self, buildout, name, options):
        # The use of version is deprecated.
        if 'version' in options:
            raise UserError('The version option is deprecated. '
                            'Read about the change on '
                            'http://pypi.python.org/pypi/djangorecipe/0.99')
        self.log = logging.getLogger(name)
        self.egg = zc.recipe.egg.Egg(buildout, options['recipe'], options)

        self.buildout, self.name, self.options = buildout, name, options
        options['location'] = os.path.join(
            buildout['buildout']['parts-directory'], name)
        options['bin-directory'] = buildout['buildout']['bin-directory']

        options.setdefault('project', 'project')
        options.setdefault('settings', 'development')

        options.setdefault('urlconf', options['project'] + '.urls')
        options.setdefault(
            'media_root',
            "os.path.join(os.path.dirname(__file__), 'media')")
        # Set this so the rest of the recipe can expect the values to be
        # there. We need to make sure that both pythonpath and extra-paths are
        # set for BBB.
        if 'extra-paths' in options:
            options['pythonpath'] = options['extra-paths']
        else:
            options.setdefault('extra-paths', options.get('pythonpath', ''))

        options.setdefault('initialization', '')
        options.setdefault('deploy_script_extra', '')

        # mod_wsgi support script
        options.setdefault('wsgi', 'false')
        options.setdefault('wsgilog', '')
        options.setdefault('logfile', '')

        # respect relative-paths (from zc.recipe.egg)
        relative_paths = options.get(
            'relative-paths', buildout['buildout'].get('relative-paths', 'false'))
        if relative_paths == 'true':
            options['buildout-directory'] = buildout['buildout']['directory']
            self._relative_paths = options['buildout-directory']
        else:
            self._relative_paths = ''
            assert relative_paths == 'false'

    def install(self):
        base_dir = self.buildout['buildout']['directory']

        project_dir = os.path.join(base_dir, self.options['project'])

        extra_paths = self.get_extra_paths()
        requirements, ws = self.egg.working_set(['djangorecipe'])

        script_paths = []
        # Create the Django management script
        script_paths.extend(self.create_manage_script(extra_paths, ws))

        # Create the test runner
        script_paths.extend(self.create_test_runner(extra_paths, ws))

        # Make the wsgi and fastcgi scripts if enabled
        script_paths.extend(self.make_scripts(extra_paths, ws))

        # Create default settings if we haven't got a project
        # egg specified, and if it doesn't already exist
        if not self.options.get('projectegg'):
            if not os.path.exists(project_dir):
                self.create_project(project_dir)
            else:
                self.log.info(
                    'Skipping creating of project: %(project)s since '
                    'it exists' % self.options)

        return script_paths

    def create_manage_script(self, extra_paths, ws):
        project = self.options.get('projectegg', self.options['project'])
        return zc.buildout.easy_install.scripts(
            [(self.options.get('control-script', self.name),
              'djangorecipe.manage', 'main')],
            ws, sys.executable, self.options['bin-directory'],
            extra_paths=extra_paths,
            relative_paths=self._relative_paths,
            arguments="'%s.%s'" % (project, self.options['settings']),
            initialization=self.options['initialization'])

    def create_test_runner(self, extra_paths, working_set):
        apps = self.options.get('test', '').split()
        # Only create the testrunner if the user requests it
        if apps:
            return zc.buildout.easy_install.scripts(
                [(self.options.get('testrunner', 'test'),
                  'djangorecipe.test', 'main')],
                working_set, sys.executable,
                self.options['bin-directory'],
                extra_paths=extra_paths,
                relative_paths=self._relative_paths,
                arguments="'%s.%s', %s" % (
                    self.options['project'],
                    self.options['settings'],
                    ', '.join(["'%s'" % app for app in apps])),
                initialization=self.options['initialization'])
        else:
            return []

    def create_project(self, project_dir):
        os.makedirs(project_dir)

        # Find the current Django versions in the buildout versions.
        # Assume the newest Django when no version is found.
        version = None
        b_versions = self.buildout.get('versions')
        if b_versions:
            django_version = (
                b_versions.get('django') or
                b_versions.get('Django')
            )
            if django_version:
                version_re = re.compile("\d+\.\d+")
                match = version_re.match(django_version)
                version = match and match.group()

        config = versions.get(version, versions['Newest'])

        template_vars = {'secret': self.generate_secret()}
        template_vars.update(self.options)

        self.create_file(
            os.path.join(project_dir, 'development.py'),
            config['development_settings'], template_vars)

        self.create_file(
            os.path.join(project_dir, 'production.py'),
            config['production_settings'], template_vars)

        self.create_file(
            os.path.join(project_dir, 'urls.py'),
            config['urls'], template_vars)

        self.create_file(
            os.path.join(project_dir, 'settings.py'),
            config['settings'], template_vars)

        # Create the media and templates directories for our
        # project
        os.mkdir(os.path.join(project_dir, 'media'))
        os.mkdir(os.path.join(project_dir, 'templates'))

        # Make the settings dir a Python package so that Django
        # can load the settings from it. It will act like the
        # project dir.
        open(os.path.join(project_dir, '__init__.py'), 'w').close()

    def make_scripts(self, extra_paths, ws):
        scripts = []
        _script_template = zc.buildout.easy_install.script_template
        protocol = 'wsgi'
        zc.buildout.easy_install.script_template = (
            zc.buildout.easy_install.script_header +
            script_template[protocol] +
            self.options['deploy_script_extra']
        )
        if self.options.get(protocol, '').lower() == 'true':
            project = self.options.get('projectegg',
                                       self.options['project'])
            scripts.extend(
                zc.buildout.easy_install.scripts(
                    [(self.options.get('wsgi-script') or
                      '%s.%s' % (self.options.get('control-script',
                                                  self.name),
                                 protocol),
                      'djangorecipe.%s' % protocol, 'main')],
                    ws,
                    sys.executable,
                    self.options['bin-directory'],
                    extra_paths=extra_paths,
                    relative_paths=self._relative_paths,
                    arguments="'%s.%s', logfile='%s'" % (
                        project, self.options['settings'],
                        self.options.get('logfile')),
                    initialization=self.options['initialization'],
                ))
        zc.buildout.easy_install.script_template = _script_template
        return scripts

    def get_extra_paths(self):
        extra_paths = [self.buildout['buildout']['directory']]

        # Add libraries found by a site .pth files to our extra-paths.
        if 'pth-files' in self.options:
            import site
            for pth_file in self.options['pth-files'].splitlines():
                pth_libs = site.addsitedir(pth_file, set())
                if not pth_libs:
                    self.log.warning(
                        "No site *.pth libraries found for pth_file=%s" % (
                            pth_file,))
                else:
                    self.log.info("Adding *.pth libraries=%s" % pth_libs)
                    self.options['extra-paths'] += '\n' + '\n'.join(pth_libs)

        pythonpath = [p.replace('/', os.path.sep) for p in
                      self.options['extra-paths'].splitlines() if p.strip()]

        extra_paths.extend(pythonpath)
        return extra_paths

    def update(self):
        extra_paths = self.get_extra_paths()
        requirements, ws = self.egg.working_set(['djangorecipe'])
        # Create the Django management script
        self.create_manage_script(extra_paths, ws)

        # Create the test runner
        self.create_test_runner(extra_paths, ws)

        # Make the wsgi and fastcgi scripts if enabled
        self.make_scripts(extra_paths, ws)

    def create_file(self, file, template, options):
        if os.path.exists(file):
            return

        f = open(file, 'w')
        f.write(template % options)
        f.close()

    def generate_secret(self):
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
        return ''.join([choice(chars) for i in range(50)])

########NEW FILE########
__FILENAME__ = test
import os
import sys

from django.core import management


def main(settings_file, *apps):
    optional_arguments = sys.argv[1:]
    sys.argv[1:] = ['test'] + list(apps) + optional_arguments
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_file)
    management.execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = tests
import copy
import os
import shutil
import sys
import tempfile
import unittest

import mock

from djangorecipe.recipe import Recipe


class BaseTestRecipe(unittest.TestCase):

    def setUp(self):
        # Create a directory for our buildout files created by the recipe
        self.buildout_dir = tempfile.mkdtemp('djangorecipe')

        self.bin_dir = os.path.join(self.buildout_dir, 'bin')
        self.develop_eggs_dir = os.path.join(self.buildout_dir,
                                             'develop-eggs')
        self.eggs_dir = os.path.join(self.buildout_dir, 'eggs')
        self.parts_dir = os.path.join(self.buildout_dir, 'parts')

        # We need to create the bin dir since the recipe should be able to
        # expect it exists
        os.mkdir(self.bin_dir)

        self.recipe_initialisation = [
            {'buildout': {
                'eggs-directory': self.eggs_dir,
                'develop-eggs-directory': self.develop_eggs_dir,
                'bin-directory': self.bin_dir,
                'parts-directory': self.parts_dir,
                'directory': self.buildout_dir,
                'python': 'buildout',
                'executable': sys.executable,
                'find-links': '',
                'allow-hosts': ''},
             },
            'django',
            {'recipe': 'djangorecipe'}]

        self.recipe = Recipe(*self.recipe_initialisation)

    def tearDown(self):
        # Remove our test dir
        shutil.rmtree(self.buildout_dir)


class TestRecipe(BaseTestRecipe):

    def test_consistent_options(self):
        # Buildout is pretty clever in detecting changing options. If
        # the recipe modifies it's options during initialisation it
        # will store this to determine wheter it needs to update or do
        # a uninstall & install. We need to make sure that we normally
        # do not trigger this. That means running the recipe with the
        # same options should give us the same results.
        self.assertEqual(Recipe(*self.recipe_initialisation).options,
                         Recipe(*self.recipe_initialisation).options)

    def test_create_file(self):
        # The create file helper should create a file at a certain
        # location unless it already exists. We will need a
        # non-existing file first.
        f, name = tempfile.mkstemp()
        # To show the function in action we need to delete the file
        # before testing.
        os.remove(name)
        # The method accepts a template argument which it will use
        # with the options argument for string substitution.
        self.recipe.create_file(name, 'Spam %s', 'eggs')
        # Let's check the contents of the file
        self.assertEqual(open(name).read(), 'Spam eggs')
        # If we try to write it again it will just ignore our request
        self.recipe.create_file(name, 'Spam spam spam %s', 'eggs')
        # The content of the file should therefore be the same
        self.assertEqual(open(name).read(), 'Spam eggs')
        # Now remove our temp file
        os.remove(name)

    def test_generate_secret(self):
        # To create a basic skeleton the recipe also generates a
        # random secret for the settings file. Since it should very
        # unlikely that it will generate the same key a few times in a
        # row we will test it with letting it generate a few keys.
        self.assertEqual(
            10, len(set(self.recipe.generate_secret() for i in range(10))))

    def test_version_option_deprecation(self):
        from zc.buildout import UserError
        options = {'recipe': 'djangorecipe',
                   'version': 'trunk',
                   'wsgi': 'true'}
        self.assertRaises(UserError, Recipe, *('buildout', 'test', options))

    @mock.patch('zc.recipe.egg.egg.Scripts.working_set',
                return_value=(None, []))
    @mock.patch('djangorecipe.recipe.Recipe.create_manage_script')
    def test_extra_paths(self, manage, working_set):

        # The recipe allows extra-paths to be specified. It uses these to
        # extend the Python path within it's generated scripts.
        self.recipe.options['version'] = '1.0'
        self.recipe.options['extra-paths'] = 'somepackage\nanotherpackage'

        self.recipe.install()
        self.assertEqual(manage.call_args[0][0][-2:],
                         ['somepackage', 'anotherpackage'])

    @mock.patch('zc.recipe.egg.egg.Scripts.working_set',
                return_value=(None, []))
    @mock.patch('site.addsitedir', return_value=['extra', 'dirs'])
    def test_pth_files(self, addsitedir, working_set):

        # When a pth-files option is set the recipe will use that to add more
        # paths to extra-paths.
        self.recipe.options['version'] = '1.0'

        # The mock values needed to demonstrate the pth-files option.
        self.recipe.options['pth-files'] = 'somedir'
        self.recipe.install()

        self.assertEqual(addsitedir.call_args, (('somedir', set([])), {}))
        # The extra-paths option has been extended.
        self.assertEqual(self.recipe.options['extra-paths'], '\nextra\ndirs')

    def test_settings_option(self):
        # The settings option can be used to specify the settings file
        # for Django to use. By default it uses `development`.
        self.assertEqual(self.recipe.options['settings'], 'development')
        # When we change it an generate a manage script it will use
        # this var.
        self.recipe.options['settings'] = 'spameggs'
        self.recipe.create_manage_script([], [])
        manage = os.path.join(self.bin_dir, 'django')
        self.assertTrue("djangorecipe.manage.main('project.spameggs')"
                        in open(manage).read())

    def test_create_project(self):
        # If a project does not exist already the recipe will create
        # one.
        project_dir = os.path.join(self.buildout_dir, 'project')
        self.recipe.create_project(project_dir)

        # This should have create a project directory
        self.assertTrue(os.path.exists(project_dir))
        # With this directory we should have a list of files.
        for f in ('settings.py', 'development.py', 'production.py',
                  '__init__.py', 'urls.py', 'media', 'templates'):
            self.assertTrue(
                os.path.exists(os.path.join(project_dir, f)))


class TestRecipeScripts(BaseTestRecipe):

    def test_make_protocol_script_wsgi(self):
        # To ease deployment a WSGI script can be generated. The
        # script adds any paths from the `extra_paths` option to the
        # Python path.
        self.recipe.options['wsgi'] = 'true'
        self.recipe.make_scripts([], [])
        # This should have created a script in the bin dir

        wsgi_script = os.path.join(self.bin_dir, 'django.wsgi')
        self.assertTrue(os.path.exists(wsgi_script))

    def test_contents_protocol_script_wsgi(self):
        self.recipe.options['wsgi'] = 'true'
        self.recipe.make_scripts([], [])
        wsgi_script = os.path.join(self.bin_dir, 'django.wsgi')

        # The contents should list our paths
        contents = open(wsgi_script).read()
         # It should also have a reference to our settings module
        self.assertTrue('project.development' in contents)
         # and a line which set's up the WSGI app
        self.assertTrue("application = "
                        "djangorecipe.wsgi.main('project.development', "
                        "logfile='')"
                        in contents)
        self.assertTrue("class logger(object)" not in contents)

    def test_contents_protocol_script_wsgi_with_initialization(self):
        self.recipe.options['wsgi'] = 'true'
        self.recipe.options['initialization'] = 'import os\nassert True'
        self.recipe.make_scripts([], [])
        wsgi_script = os.path.join(self.bin_dir, 'django.wsgi')
        self.assertTrue('import os\nassert True\n\nimport djangorecipe'
                        in open(wsgi_script).read())

    def test_contents_log_protocol_script_wsgi(self):
        self.recipe.options['wsgi'] = 'true'
        self.recipe.options['logfile'] = '/foo'
        self.recipe.make_scripts([], [])

        wsgi_script = os.path.join(self.bin_dir, 'django.wsgi')
        contents = open(wsgi_script).read()

        self.assertTrue("logfile='/foo'" in contents)

    def test_make_protocol_named_script_wsgi(self):
        # A wsgi-script name option is specified
        self.recipe.options['wsgi'] = 'true'
        self.recipe.options['wsgi-script'] = 'foo-wsgi.py'
        self.recipe.make_scripts([], [])
        wsgi_script = os.path.join(self.bin_dir, 'foo-wsgi.py')
        self.assertTrue(os.path.exists(wsgi_script))

    def test_deploy_script_extra(self):
        extra_val = '#--deploy_script_extra--'
        self.recipe.options['wsgi'] = 'true'
        self.recipe.options['deploy_script_extra'] = extra_val
        self.recipe.make_scripts([], [])
        wsgi_script = os.path.join(self.bin_dir, 'django.wsgi')
        contents = open(wsgi_script).read()
        self.assertTrue(extra_val in contents)

    @mock.patch('zc.buildout.easy_install.scripts',
                return_value=['some-path'])
    def test_make_protocol_scripts_return_value(self, scripts):
        # The return value of make scripts lists the generated scripts.
        self.recipe.options['wsgi'] = 'true'
        self.assertEqual(self.recipe.make_scripts([], []),
                         ['some-path'])

    def test_create_manage_script(self):
        # This buildout recipe creates a alternative for the standard
        # manage.py script. It has all the same functionality as the
        # original one but it sits in the bin dir instead of within
        # the project.
        manage = os.path.join(self.bin_dir, 'django')
        self.recipe.create_manage_script([], [])
        self.assertTrue(os.path.exists(manage))

    def test_create_manage_script_projectegg(self):
        # When a projectegg is specified, then the egg specified
        # should get used as the project file.
        manage = os.path.join(self.bin_dir, 'django')
        self.recipe.options['projectegg'] = 'spameggs'
        self.recipe.create_manage_script([], [])
        self.assertTrue(os.path.exists(manage))
        # Check that we have 'spameggs' as the project
        self.assertTrue("djangorecipe.manage.main('spameggs.development')"
                        in open(manage).read())

    def test_create_manage_script_with_initialization(self):
        manage = os.path.join(self.bin_dir, 'django')
        self.recipe.options['initialization'] = 'import os\nassert True'
        self.recipe.create_manage_script([], [])
        self.assertTrue('import os\nassert True\n\nimport djangorecipe'
                        in open(manage).read())

    def test_create_wsgi_script_projectegg(self):
        # When a projectegg is specified, then the egg specified
        # should get used as the project in the wsgi script.
        wsgi = os.path.join(self.bin_dir, 'django.wsgi')
        recipe_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..'))
        self.recipe.options['projectegg'] = 'spameggs'
        self.recipe.options['wsgi'] = 'true'
        self.recipe.make_scripts([recipe_dir], [])

        self.assertTrue(os.path.exists(wsgi))
        # Check that we have 'spameggs' as the project
        self.assertTrue('spameggs.development' in open(wsgi).read())


class TestTesTRunner(BaseTestRecipe):

    def test_create_test_runner(self):
        # An executable script can be generated which will make it
        # possible to execute the Django test runner. This options
        # only works if we specify one or apps to test.
        testrunner = os.path.join(self.bin_dir, 'test')

        # This first argument sets extra_paths, we will use this to
        # make sure the script can find this recipe
        recipe_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..'))

        # When we specify an app to test it should create the the
        # testrunner
        self.recipe.options['test'] = 'knight'
        self.recipe.create_test_runner([recipe_dir], [])
        self.assertTrue(os.path.exists(testrunner))

    def test_not_create_test_runner(self):
        recipe_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..'))
        self.recipe.create_test_runner([recipe_dir], [])

        testrunner = os.path.join(self.bin_dir, 'test')

        # Show it does not create a test runner by default
        self.assertFalse(os.path.exists(testrunner))

    def test_create_test_runner_with_initialization(self):
        recipe_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..'))
        testrunner = os.path.join(self.bin_dir, 'test')

        # When we specify an app to test it should create the the
        # testrunner
        self.recipe.options['test'] = 'knight'
        self.recipe.options['initialization'] = 'import os\nassert True'
        self.recipe.create_test_runner([recipe_dir], [])
        self.assertTrue('import os\nassert True\n\nimport djangorecipe'
                        in open(testrunner).read())

    def test_relative_paths_default(self):
        self.recipe.options['wsgi'] = 'true'

        self.recipe.make_scripts([], [])
        self.recipe.create_manage_script([], [])

        manage = os.path.join(self.bin_dir, 'django')
        wsgi_script = os.path.join(self.bin_dir, 'django.wsgi')

        expected = base = 'base = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))'
        self.assertFalse(expected in open(manage).read())
        self.assertFalse(expected in open(wsgi_script).read())

    def test_relative_paths_true(self):
        recipe = Recipe({
                'buildout': {
                    'eggs-directory': self.eggs_dir,
                    'develop-eggs-directory': self.develop_eggs_dir,
                    'python': 'python-version',
                    'bin-directory': self.bin_dir,
                    'parts-directory': self.parts_dir,
                    'directory': self.buildout_dir,
                    'find-links': '',
                    'allow-hosts': '',
                    'develop': '.',
                    'relative-paths': 'true'
                    },
                'python-version': {'executable': sys.executable}},
                             'django',
                             {'recipe': 'djangorecipe',
                              'wsgi': 'true'})
        recipe.make_scripts([], [])
        recipe.create_manage_script([], [])

        manage = os.path.join(self.bin_dir, 'django')
        wsgi_script = os.path.join(self.bin_dir, 'django.wsgi')

        expected = base = 'base = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))'
        self.assertTrue(expected in open(manage).read())
        self.assertTrue(expected in open(wsgi_script).read())


class TestBoilerplate(BaseTestRecipe):

    def test_boilerplate_newest(self):
        """Test the default boilerplate."""

        project_dir = os.path.join(self.buildout_dir, 'project')

        secret = '$55upfci7a#gi@&e9o1-hb*k+f$3+(&b$j=cn67h#22*0%-bj0'
        self.recipe.generate_secret = lambda: secret

        self.recipe.create_project(project_dir)
        settings = open(os.path.join(project_dir, 'settings.py')).read()
        settings_dict = {'project': self.recipe.options['project'],
                         'secret': secret,
                         'urlconf': self.recipe.options['urlconf'],
                         }
        from djangorecipe.boilerplate import versions
        self.assertEqual(versions['Newest']['settings'] % settings_dict,
                          settings)

    def test_boilerplate_1_2(self):
        """Test the boilerplate for django 1.2."""

        recipe_args = copy.deepcopy(self.recipe_initialisation)

        recipe_args[0]['versions'] = {'django': '1.2.5'}
        recipe = Recipe(*recipe_args)

        secret = '$55upfci7a#gi@&e9o1-hb*k+f$3+(&b$j=cn67h#22*0%-bj0'
        recipe.generate_secret = lambda: secret

        project_dir = os.path.join(self.buildout_dir, 'project')
        recipe.create_project(project_dir)
        settings = open(os.path.join(project_dir, 'settings.py')).read()
        settings_dict = {'project': self.recipe.options['project'],
                         'secret': secret,
                         'urlconf': self.recipe.options['urlconf'],
                         }
        from djangorecipe.boilerplate import versions

        self.assertEqual(versions['1.2']['settings'] % settings_dict,
                          settings)

########NEW FILE########
__FILENAME__ = test_scripts
import os
import sys
import unittest

import mock


class ScriptTestCase(unittest.TestCase):

    def setUp(self):
        # We will also need to fake the settings file's module
        self.settings = mock.sentinel.Settings
        self.settings.SECRET_KEY = 'I mock your secret key'
        sys.modules['cheeseshop'] = mock.sentinel.CheeseShop
        sys.modules['cheeseshop.development'] = self.settings
        sys.modules['cheeseshop'].development = self.settings
        print("DJANGO ENV: %s" % os.environ.get('DJANGO_SETTINGS_MODULE'))

    def tearDown(self):
        # We will clear out sys.modules again to clean up
        for m in ['cheeseshop', 'cheeseshop.development']:
            del sys.modules[m]


class TestTestScript(ScriptTestCase):

    @mock.patch('django.core.management.execute_from_command_line')
    @mock.patch('os.environ.setdefault')
    def test_script(self, mock_setdefault, execute_from_command_line):
        with mock.patch.object(sys, 'argv', ['bin/test']):
            # The test script should execute the standard Django test command
            # with any apps configured in djangorecipe given as its arguments.
            from djangorecipe import test
            test.main('cheeseshop.development',  'spamm', 'eggs')
            self.assertTrue(execute_from_command_line.called)
            self.assertEqual(execute_from_command_line.call_args[0],
                             (['bin/test', 'test', 'spamm', 'eggs'],))
            self.assertEqual(mock_setdefault.call_args[0],
                             ('DJANGO_SETTINGS_MODULE', 'cheeseshop.development'))

    @mock.patch('django.core.management.execute_from_command_line')
    @mock.patch('os.environ.setdefault')
    def test_script_with_args(self, mock_setdefault, execute_from_command_line):
        with mock.patch.object(sys, 'argv', ['bin/test', '--verbose']):
            # The test script should execute the standard Django test command
            # with any apps given as its arguments. It should also pass along
            # command line arguments so that the actual test machinery can
            # pick them up (like '--verbose' or '--tests=xyz').
            from djangorecipe import test
            test.main('cheeseshop.development',  'spamm', 'eggs')
            self.assertEqual(execute_from_command_line.call_args[0],
                             (['bin/test', 'test', 'spamm', 'eggs', '--verbose'],))
            self.assertEqual(mock_setdefault.call_args[0],
                             ('DJANGO_SETTINGS_MODULE', 'cheeseshop.development'))

    @mock.patch('django.core.management.execute_from_command_line')
    @mock.patch('os.environ.setdefault')
    def test_deeply_nested_settings(self, mock_setdefault, execute_from_command_line):
        # Settings files can be more than two levels deep. We need to
        # make sure the test script can properly import those. To
        # demonstrate this we need to add another level to our
        # sys.modules entries.
        settings = mock.sentinel.SettingsModule
        settings.SECRET_KEY = 'I mock your secret key'
        nce = mock.sentinel.NCE
        nce.development = settings
        sys.modules['cheeseshop'].nce = nce
        sys.modules['cheeseshop.nce'] = nce
        sys.modules['cheeseshop.nce.development'] = settings
        from djangorecipe import test
        test.main('cheeseshop.nce.development',  'tilsit', 'stilton')
        self.assertEqual(mock_setdefault.call_args[0],
                         ('DJANGO_SETTINGS_MODULE', 'cheeseshop.nce.development'))


class TestManageScript(ScriptTestCase):

    @mock.patch('django.core.management.execute_from_command_line')
    @mock.patch('os.environ.setdefault')
    def test_script(self, mock_setdefault, mock_execute):
        # The manage script is a replacement for the default manage.py
        # script. It has all the same bells and whistles since all it
        # does is call the normal Django stuff.
        from djangorecipe import manage
        manage.main('cheeseshop.development')
        self.assertEqual(mock_execute.call_args,
                         ((sys.argv,), {}))
        self.assertEqual(
            mock_setdefault.call_args,
            (('DJANGO_SETTINGS_MODULE', 'cheeseshop.development'), {}))


class TestWSGIScript(ScriptTestCase):

    def test_script(self):
        settings_dotted_path = 'cheeseshop.development'
        # ^^^ Our regular os.environ.setdefault patching doesn't help.
        # Patching get_wsgi_application already imports the DB layer, so the
        # settings are already needed there!
        with mock.patch('os.environ',
                        {'DJANGO_SETTINGS_MODULE': settings_dotted_path}):
            with mock.patch('django.core.wsgi.get_wsgi_application') \
                 as patched_method:
                from djangorecipe import wsgi
                wsgi.main(settings_dotted_path, logfile=None)
                self.assertTrue(patched_method.called)

########NEW FILE########
__FILENAME__ = wsgi
import os
import sys


def main(settings_file, logfile=None):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_file)
    if logfile:
        import datetime

        class logger(object):
            def __init__(self, logfile):
                self.logfile = logfile

            def write(self, data):
                self.log(data)

            def writeline(self, data):
                self.log(data)

            def log(self, msg):
                line = '%s - %s\n' % (
                    datetime.datetime.now().strftime('%Y%m%d %H:%M:%S'), msg)
                fp = open(self.logfile, 'a')
                try:
                    fp.write(line)
                finally:
                    fp.close()
        sys.stdout = sys.stderr = logger(logfile)

    # Run WSGI handler for the application
    from django.core.wsgi import get_wsgi_application
    return get_wsgi_application()

########NEW FILE########
