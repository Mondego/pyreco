__FILENAME__ = bower
from . import conf, shortcuts, exceptions
import os
import subprocess
import sys
import json


class BowerAdapter(object):
    """Adapter for working with bower"""

    def __init__(self, bower_path, components_root):
        self._bower_path = bower_path
        self._components_root = components_root

    def is_bower_exists(self):
        """Check is bower exists"""
        if shortcuts.is_executable(self._bower_path)\
                or shortcuts.which(self._bower_path):
            return True
        else:
            return False

    def create_components_root(self):
        """Create components root if need"""
        if not os.path.exists(self._components_root):
            os.mkdir(self._components_root)

    def call_bower(self, args):
        """Call bower with a list of args"""
        proc = subprocess.Popen(
            [self._bower_path] + list(args),
            cwd=self._components_root)
        proc.wait()

    def install(self, packages, *options):
        """Install packages from bower"""
        self.call_bower(['install'] + list(options) + list(packages))

    def _accumulate_dependencies(self, data):
        """Accumulate dependencies"""
        for name, params in data['dependencies'].items():
            meta = params.get('pkgMeta', {})
            version = meta.get(
                'version', meta.get('_resolution', {}).get('commit', ''),
            )

            if version:
                full_name = '{}#{}'.format(name, version)
            else:
                full_name = name

            self._packages.append(full_name)
            self._accumulate_dependencies(params)

    def _parse_package_names(self, output):
        """Get package names in bower >= 1.0"""
        data = json.loads(output)
        self._packages = []
        self._accumulate_dependencies(data)
        return self._packages

    def freeze(self):
        """Yield packages with versions list"""
        proc = subprocess.Popen(
            [self._bower_path, 'list', '--json', '--offline', '--no-color'],
            cwd=conf.COMPONENTS_ROOT,
            stdout=subprocess.PIPE,
        )
        proc.wait()

        output = proc.stdout.read().decode(
            sys.getfilesystemencoding(),
        )

        try:
            packages = self._parse_package_names(output)
        except ValueError:
            raise exceptions.LegacyBowerVersionNotSupported()

        return iter(set(packages))


bower_adapter = BowerAdapter(conf.BOWER_PATH, conf.COMPONENTS_ROOT)

########NEW FILE########
__FILENAME__ = conf
from django.conf import settings


COMPONENTS_ROOT = getattr(settings, 'BOWER_COMPONENTS_ROOT')
BOWER_PATH = getattr(settings, 'BOWER_PATH', 'bower')

########NEW FILE########
__FILENAME__ = exceptions
from django.core.management.base import CommandError


class BowerNotInstalled(CommandError):
    """Custom command error"""

    def __init__(self):
        super(BowerNotInstalled, self).__init__(
            "Bower not installed, read instruction here - http://bower.io/",
        )


class LegacyBowerVersionNotSupported(CommandError):
    """Custom command error"""

    def __init__(self):
        super(LegacyBowerVersionNotSupported, self).__init__(
            "Legacy bower versions not supported, please install bower 1.0+",
        )

########NEW FILE########
__FILENAME__ = finders
from django.contrib.staticfiles.finders import FileSystemFinder
from django.core.files.storage import FileSystemStorage
from django.utils.datastructures import SortedDict
from . import conf
import os


class BowerFinder(FileSystemFinder):
    """Find static files installed with bower"""

    def __init__(self, apps=None, *args, **kwargs):
        self.locations = [
            ('', self._get_bower_components_location()),
        ]
        self.storages = SortedDict()

        filesystem_storage = FileSystemStorage(location=self.locations[0][1])
        filesystem_storage.prefix = self.locations[0][0]
        self.storages[self.locations[0][1]] = filesystem_storage

    def _get_bower_components_location(self):
        """Get bower components location"""
        path = os.path.join(conf.COMPONENTS_ROOT, 'bower_components')

        # for old bower versions:
        if not os.path.exists(path):
            path = os.path.join(conf.COMPONENTS_ROOT, 'components')
        return path

########NEW FILE########
__FILENAME__ = base
from pprint import pformat
from django.core.management.base import BaseCommand
from django.conf import settings
from ..bower import bower_adapter
from ..exceptions import BowerNotInstalled


class BaseBowerCommand(BaseCommand):
    """Base management command with bower support"""

    def handle(self, *args, **options):
        self._check_bower_exists()
        bower_adapter.create_components_root()

    def _check_bower_exists(self):
        """Check bower exists or raise exception"""
        if not bower_adapter.is_bower_exists():
            raise BowerNotInstalled()

    def _install(self, args):
        bower_adapter.install(settings.BOWER_INSTALLED_APPS, *args)

    def _freeze(self):
        packages = tuple(bower_adapter.freeze())
        output = 'BOWER_INSTALLED_APPS = {}'.format(
            pformat(packages),
        )
        self.stdout.write(output)

########NEW FILE########
__FILENAME__ = bower
from ...bower import bower_adapter
from ..base import BaseBowerCommand


class Command(BaseBowerCommand):
    help = 'Call bower in components root ({}).'.format(
        bower_adapter._components_root)

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)
        if self._is_single_command('install', args):
            self._install([])
        elif self._is_single_command('freeze', args):
            self._freeze()
        else:
            bower_adapter.call_bower(args)

    def _is_single_command(self, name, args):
        return len(args) == 1 and args[0] == name

########NEW FILE########
__FILENAME__ = bower_freeze
from ..base import BaseBowerCommand


class Command(BaseBowerCommand):
    help = 'Freeze bower apps'

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)
        self._freeze()

########NEW FILE########
__FILENAME__ = bower_install
from ..base import BaseBowerCommand


class Command(BaseBowerCommand):
    help = 'Install bower apps'

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)
        self._install(args)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = shortcuts
import os


def is_executable(path):
    """Check file is executable"""
    return os.path.isfile(path) and os.access(path, os.X_OK)


def which(program):
    """
    Find by path and check exists.
    Analog of unix `which` command.
    """
    path, name = os.path.split(program)
    if path:
        if is_executable(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_executable(exe_file):
                return exe_file

    return None

########NEW FILE########
__FILENAME__ = base
from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings
from ..bower import bower_adapter
import os
import shutil


try:
    TEST_COMPONENTS_ROOT = os.path.join(
        settings.TEST_PROJECT_ROOT, 'bower_components',
    )
except AttributeError:
    TEST_COMPONENTS_ROOT = '/tmp/bower_components/'


@override_settings(BOWER_COMPONENTS_ROOT=TEST_COMPONENTS_ROOT)
class BaseBowerCase(TestCase):
    """Base bower test case"""

    def setUp(self):
        bower_adapter.create_components_root()

    def tearDown(self):
        self._remove_components_root()

    def _remove_components_root(self):
        """Remove components root if exists"""
        if os.path.exists(TEST_COMPONENTS_ROOT):
            shutil.rmtree(TEST_COMPONENTS_ROOT)

    def assertCountEqual(self, *args, **kwargs):
        """Add python 2 support"""
        if hasattr(self, 'assertItemsEqual'):
            return self.assertItemsEqual(*args, **kwargs)
        else:
            return super(BaseBowerCase, self).assertCountEqual(*args, **kwargs)

########NEW FILE########
__FILENAME__ = test_bower
from django.core.management import call_command
from django.conf import settings
from six import StringIO
from mock import MagicMock
from ..bower import bower_adapter, BowerAdapter
from .. import conf
from .base import BaseBowerCase, TEST_COMPONENTS_ROOT
import os


class BowerInstallCase(BaseBowerCase):
    """Test case for bower_install management command"""

    def setUp(self):
        super(BowerInstallCase, self).setUp()
        self.apps = settings.BOWER_INSTALLED_APPS
        self._original_install = bower_adapter.install
        bower_adapter.install = MagicMock()

    def tearDown(self):
        super(BowerInstallCase, self).tearDown()
        bower_adapter.install = self._original_install

    def test_create_components_root(self):
        """Test create components root"""
        self._remove_components_root()
        call_command('bower_install')

        self.assertTrue(os.path.exists(TEST_COMPONENTS_ROOT))

    def test_install(self):
        """Test install bower packages"""
        call_command('bower_install')
        bower_adapter.install.assert_called_once_with(self.apps)


class BowerFreezeCase(BaseBowerCase):
    """Case for bower freeze"""

    def setUp(self):
        super(BowerFreezeCase, self).setUp()
        bower_adapter.install(['jquery#1.9'])
        bower_adapter.install(['backbone'])
        bower_adapter.install(['underscore'])
        bower_adapter.install(['typeahead.js'])
        bower_adapter.install(['backbone-tastypie'])

    def test_freeze(self):
        """Test freeze"""
        installed = [
            package.split('#')[0] for package in bower_adapter.freeze()
        ]
        self.assertCountEqual(installed, [
            'backbone', 'jquery',
            'typeahead.js', 'underscore',
            'backbone-tastypie',
        ])

    def test_no_newline_in_freeze(self):
        """Test no newline in freezee"""
        installed = bower_adapter.freeze()
        for package in installed:
            self.assertNotIn('\n', package)

    def test_management_command(self):
        """Test freeze management command"""
        stdout = StringIO()
        call_command('bower_freeze', stdout=stdout)
        stdout.seek(0)
        output = stdout.read()

        self.assertIn('BOWER_INSTALLED_APPS', output)
        self.assertIn('backbone', output)


class BowerExistsCase(BaseBowerCase):
    """
    Test bower exists checker.
    This case need bower to be installed.
    """

    def setUp(self):
        super(BowerExistsCase, self).setUp()
        self._original_exists = bower_adapter.is_bower_exists

    def tearDown(self):
        super(BowerExistsCase, self).tearDown()
        bower_adapter.is_bower_exists = self._original_exists

    def test_if_exists(self):
        """Test if bower exists"""
        self.assertTrue(bower_adapter.is_bower_exists())

    def test_if_not_exists(self):
        """Test if bower not exists"""
        adapter = BowerAdapter('/not/exists/path', TEST_COMPONENTS_ROOT)
        self.assertFalse(adapter.is_bower_exists())

    def _mock_exists_check(self):
        """Make exists check return false"""
        bower_adapter.is_bower_exists = MagicMock()
        bower_adapter.is_bower_exists.return_value = False


class BowerCommandCase(BaseBowerCase):
    """Test case for ./manage.py bower something command"""

    def setUp(self):
        super(BowerCommandCase, self).setUp()
        self.apps = settings.BOWER_INSTALLED_APPS
        self._mock_bower_adapter()

    def _mock_bower_adapter(self):
        self._original_install = bower_adapter.install
        bower_adapter.install = MagicMock()
        self._orig_call = bower_adapter.call_bower
        bower_adapter.call_bower = MagicMock()
        self._orig_freeze = bower_adapter.freeze
        bower_adapter.freeze = MagicMock()

    def tearDown(self):
        super(BowerCommandCase, self).tearDown()
        bower_adapter.install = self._original_install
        bower_adapter.call_bower = self._orig_call
        bower_adapter.freeze = self._orig_freeze

    def test_install_without_params(self):
        """Test that bower install without param identical
        with bower_install

        """
        call_command('bower', 'install')
        bower_adapter.install.assert_called_once_with(
            self.apps)

    def test_install_with_params(self):
        """Test bower install <something>"""
        call_command('bower', 'install', 'jquery')
        bower_adapter.call_bower.assert_called_once_with(
            ('install', 'jquery'))

    def test_freeze(self):
        """Test bower freeze command"""
        call_command('bower', 'freeze')
        bower_adapter.freeze.assert_called_once_with()

    def test_call_to_bower(self):
        """Test simple call to bower"""
        call_command('bower', 'update')
        bower_adapter.call_bower.assert_called_once_with(
            ('update',))

########NEW FILE########
__FILENAME__ = test_finders
from ..bower import bower_adapter
from ..finders import BowerFinder
from .. import conf
from .base import BaseBowerCase
import os


class BowerFinderCase(BaseBowerCase):
    """Test finding installed with bower files"""

    def setUp(self):
        super(BowerFinderCase, self).setUp()
        bower_adapter.install(['jquery#1.9'])
        self.finder = BowerFinder()

    def test_find(self):
        """Test staticfinder find"""
        path = self.finder.find('jquery/jquery.min.js')
        self.assertEqual(path, os.path.join(
            conf.COMPONENTS_ROOT, 'bower_components', 'jquery/jquery.min.js',
        ))

    def test_list(self):
        """Test staticfinder list"""
        result = self.finder.list([])
        matched = [
            part for part in result if part[0] == 'jquery/jquery.min.js'
        ]
        self.assertEqual(len(matched), 1)

########NEW FILE########
__FILENAME__ = test_settings
import os


TEST_PROJECT_ROOT = os.path.abspath(
    os.environ.get('TEST_PROJECT_ROOT', '/tmp/'),
)

BOWER_COMPONENTS_ROOT = os.path.join(TEST_PROJECT_ROOT, 'bower_components')

STATIC_ROOT = os.path.join(TEST_PROJECT_ROOT, 'bower_static')

STATIC_URL = '/static/'

BOWER_INSTALLED_APPS = (
    'jquery#1.9',
    'underscore',
)

SECRET_KEY = 'iamdjangobower'

INSTALLED_APPS = (
    'djangobower',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-bower documentation build configuration file, created by
# sphinx-quickstart on Tue Jul 16 16:38:23 2013.
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
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-bower'
copyright = u'2013, Vladimir Iakovlev'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '4.7'
# The full version, including alpha/beta/rc tags.
release = '4.8'

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
htmlhelp_basename = 'django-bowerdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-bower.tex', u'django-bower Documentation',
   u'Vladimir Iakovlev', 'manual'),
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

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'django-bower', u'django-bower Documentation',
     [u'Vladimir Iakovlev'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'django-bower', u'django-bower Documentation',
   u'Vladimir Iakovlev', 'django-bower', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = settings
import os


PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), ".."),
)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static')

STATIC_URL = '/static/'

BOWER_COMPONENTS_ROOT = os.path.join(PROJECT_ROOT, 'components')

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'djangobower.finders.BowerFinder',
)

SECRET_KEY = 'g^i##va1ewa5d-rw-mevzvx2^udt63@!xu$-&di^19t)5rbm!5'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'example.urls'

WSGI_APPLICATION = 'example.wsgi.application'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.staticfiles',
    'djangobower',
)

BOWER_INSTALLED_APPS = (
    'jquery',
    'underscore',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url
from django.views.generic import TemplateView


urlpatterns = patterns(
    '',
    url(r'^$', TemplateView.as_view(template_name='index.html')),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for example project.

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
# os.environ["DJANGO_SETTINGS_MODULE"] = "example.settings"
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
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", 'djangobower.test_settings',
    )

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
